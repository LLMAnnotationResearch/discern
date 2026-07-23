"""OPTIONAL, label-free classifier check (not part of a normal run).

Purpose: a quick "can the models even read these constructs?" sanity check that needs NO hand-labeled
data. It samples rows from your dataset, classifies each under every pool model for a set of questions,
and reports INTER-MODEL AGREEMENT. High agreement = the models read the construct consistently, so
measurement on it is reliable; low agreement = the construct is ambiguous or a model can't read it
(reword it, or drop the weak model). This is a confidence check, not a validity gate — the
false-positive control is the placebo run, which needs no labels either.

Agreement is a PROXY for a hand-labeled check: it shows the models CONCUR, not that they are correct.

    discern check --dataset data.csv --group-col g --from-run runs/real_r0
    discern check --dataset data.csv --text-col text --questions my_questions.txt
    # (or standalone: python -m discern.classifier_check ...)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path

from .core import DEFAULT_POOL, MODELS, classify_one
from .keys import DEFAULT_ENV, check_or_raise, load_env, missing_keys

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def _load_questions(args) -> list[dict]:
    if args.from_run:
        rd = Path(args.from_run)
        sel, con = rd / "04_selected.json", rd / "02_consolidated.json"
        if sel.exists():
            res = json.loads(sel.read_text())["results"]
            src = [r for r in res if r.get("validated")] or res
            return [{"question": r["classification_question"], "definition": r.get("definition", "")}
                    for r in src]
        if con.exists():
            return [{"question": c["classification_question"], "definition": c.get("definition", "")}
                    for c in json.loads(con.read_text())["candidates"]]
        raise SystemExit(f"--from-run: no 04_selected.json or 02_consolidated.json in {rd}")
    if args.questions:
        txt = Path(args.questions).read_text()
        try:
            data = json.loads(txt)
            return [{"question": d["question"], "definition": d.get("definition", "")}
                    if isinstance(d, dict) else {"question": str(d), "definition": ""} for d in data]
        except json.JSONDecodeError:
            return [{"question": ln.strip(), "definition": ""} for ln in txt.splitlines() if ln.strip()]
    raise SystemExit("provide --from-run <run dir> or --questions <file> (nothing to check otherwise)")


def _sample_units(args) -> list[str]:
    from .data import read_table
    df = read_table(args.dataset)
    if args.text_col not in df.columns:
        raise SystemExit(f"text column {args.text_col!r} not in dataset columns {list(df.columns)}")
    rng = random.Random(args.seed)
    txt = df[args.text_col].astype(str)
    if args.group_col and args.group_col in df.columns:
        by: dict[str, list[str]] = {}
        for g, t in zip(df[args.group_col].astype(str), txt):
            if t.strip():
                by.setdefault(g, []).append(t)
        per = max(1, args.n // max(1, len(by)))
        out = []
        for texts in by.values():
            rng.shuffle(texts)
            out += texts[:per]
        return out
    texts = [t for t in txt if t.strip()]
    rng.shuffle(texts)
    return texts[:args.n]


def fleiss_kappa(units_counts: list[tuple[int, int]]) -> float | None:
    """Fleiss' kappa for binary ratings over units rated by all raters (constant n). Corrects for
    prevalence, so a 95%-'no' construct with trivially high raw agreement doesn't look reliable by luck."""
    if not units_counts:
        return None
    n = max(sum(c) for c in units_counts)
    units = [c for c in units_counts if sum(c) == n]
    N = len(units)
    if N == 0 or n < 2:
        return None
    p_j = [sum(c[j] for c in units) / (N * n) for j in (0, 1)]
    P_e = sum(p * p for p in p_j)
    if P_e >= 1.0:
        return 1.0
    P_bar = sum((c[0] ** 2 + c[1] ** 2 - n) / (n * (n - 1)) for c in units) / N
    return (P_bar - P_e) / (1 - P_e)


def _agreement(answers: dict[str, list]) -> dict:
    models = list(answers)
    n_units = len(next(iter(answers.values())))
    pair_hits = pair_tot = unan = unan_tot = 0
    counts = []
    for i in range(n_units):
        votes = [answers[m][i] for m in models if answers[m][i] is not None]
        if len(votes) < 2:
            continue
        for a, b in combinations(votes, 2):
            pair_tot += 1
            pair_hits += int(a == b)
        unan_tot += 1
        unan += int(len(set(votes)) == 1)
        counts.append((votes.count(0), votes.count(1)))
    return {
        "n_units_scored": unan_tot,
        "pairwise_agreement": round(pair_hits / pair_tot, 3) if pair_tot else None,
        "unanimous_frac": round(unan / unan_tot, 3) if unan_tot else None,
        "fleiss_kappa": (round(k, 3) if (k := fleiss_kappa(counts)) is not None else None),
    }


def run_check(args) -> None:
    load_env()
    models = [m.strip() for m in args.models.split(",")] if args.models else list(DEFAULT_POOL)
    for m in models:
        if m not in MODELS:
            raise SystemExit(f"unknown model {m!r}; known: {sorted(MODELS)}")
    # key check for exactly the providers these models use
    from types import SimpleNamespace
    probe = SimpleNamespace(discovery_models=models, rotation_pool=models, ensemble_pool=models,
                            consolidation_model=models[0], measurement_design="rotate",
                            organize_themes=False, theme_model=models[0])
    if missing_keys(probe):
        check_or_raise(probe)

    questions = _load_questions(args)[: args.max_questions]
    texts = _sample_units(args)
    if not questions or not texts:
        raise SystemExit("no questions or no sampled units")
    print(f"[check] {len(models)} models x {len(questions)} questions x {len(texts)} units "
          f"= {len(models)*len(questions)*len(texts)} calls (label-free agreement)", flush=True)

    per_q = []
    for qi, q in enumerate(questions):
        answers = {}
        for m in models:
            def one(t, _m=m, _q=q):
                try:
                    return classify_one(_q["question"], t, model=_m, definition=_q["definition"],
                                        unit_label=args.unit_label)
                except Exception:  # noqa: BLE001 — a failed call drops out of the agreement
                    return None
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                answers[m] = list(ex.map(one, texts))
        stats = _agreement(answers)
        per_q.append({"question": q["question"], **stats})
        print(f"  q{qi+1}: pairwise={stats['pairwise_agreement']} unanimous={stats['unanimous_frac']} "
              f"kappa={stats['fleiss_kappa']}  {q['question'][:56]}", flush=True)

    ok = [x["pairwise_agreement"] for x in per_q if x["pairwise_agreement"] is not None]
    ks = [x["fleiss_kappa"] for x in per_q if x["fleiss_kappa"] is not None]
    overall = {"mean_pairwise_agreement": round(sum(ok) / len(ok), 3) if ok else None,
               "mean_fleiss_kappa": round(sum(ks) / len(ks), 3) if ks else None,
               "models": models, "n_units": len(texts), "n_questions": len(questions)}
    print(f"\n[check] OVERALL mean pairwise agreement={overall['mean_pairwise_agreement']} "
          f"mean Fleiss kappa={overall['mean_fleiss_kappa']}")
    print("  reading: high agreement (pairwise >~0.85, kappa >~0.6) = models read the construct "
          "consistently; low = ambiguous construct or a weak model. A confidence check, not a validity "
          "gate — the placebo run is what controls false positives.")
    if args.out:
        Path(args.out).write_text(json.dumps({"overall": overall, "per_question": per_q}, indent=2))
        print(f"  wrote {args.out}")


def add_check_args(ap) -> None:
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--text-col", dest="text_col", default="text")
    ap.add_argument("--group-col", dest="group_col", default=None,
                    help="optional; if given, sampling is stratified by it")
    ap.add_argument("--from-run", dest="from_run", default=None,
                    help="pull questions from a completed run dir")
    ap.add_argument("--questions", default=None, help="questions file (one per line, or a JSON list)")
    ap.add_argument("--models", default=None, help="comma-separated model keys (default: the pool)")
    ap.add_argument("--unit-label", dest="unit_label", default="item")
    ap.add_argument("--n", type=int, default=40, help="units to sample")
    ap.add_argument("--max-questions", dest="max_questions", type=int, default=12)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--out", default=None, help="optional path to write the JSON report")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    add_check_args(ap)
    run_check(ap.parse_args())


if __name__ == "__main__":
    main()
