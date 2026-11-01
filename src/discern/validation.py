"""Offline Section 4 research tools. No LLM calls and no changes to production selection.

Results are pilots by default. Frozen-bank experiments are conditional diagnostics,
not end-to-end placebos. Legacy labels are never reconstructed without an explicit flag.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
from types import SimpleNamespace

import numpy as np

from .config import RunConfig
from .select import run_selection


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_interval(successes, trials):
    """Two-sided 95% Wilson binomial interval, including 0/n and n/n."""
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("need trials > 0 and 0 <= successes <= trials")
    z = 1.959963984540054
    p, z2 = successes / trials, z * z
    center = (p + z2 / (2 * trials)) / (1 + z2 / trials)
    radius = z * np.sqrt(p * (1 - p) / trials + z2 / (4 * trials**2)) / (1 + z2 / trials)
    return [max(0.0, float(center - radius)), min(1.0, float(center + radius))]


def summarize_null(rows):
    """All candidates must be null. q10 counts include primary and suggestive."""
    if not rows:
        raise ValueError("no completed replications")
    out = {}
    for name in ("q05", "q10", "uncorrected_only"):
        counts = np.array([r[name] for r in rows], dtype=int)
        events = int((counts > 0).sum())
        values, freq = np.unique(counts, return_counts=True)
        out[name] = {
            "any_selection_numerator": events, "replications": len(rows),
            "any_selection_rate": events / len(rows),
            "any_selection_wilson_95": wilson_interval(events, len(rows)),
            "mean_selected": float(counts.mean()), "max_selected": int(counts.max()),
            "selected_count_distribution": {str(int(k)): int(v) for k, v in zip(values, freq)},
        }
    return out


def evaluate(labels, split, scores, cfg):
    candidates = [{"candidate_id": k, "feature_name": k, "classification_question": k}
                  for k in scores]
    data = SimpleNamespace(measurement_labels=lambda: labels, m_split=split)
    selected = run_selection(cfg, data, {k: {"y": v} for k, v in scores.items()}, candidates)
    return {"q05": selected["n_validated"],
            "q10": selected["n_validated"] + selected["n_suggestive"],
            "uncorrected_only": selected["n_uncorrected"],
            "n_tested": selected["n_tested"], "permutations": selected["permutations"],
            "permutations_capped": selected["permutations_capped"]}


def null_scores(rng, n_units, n_candidates, scenario):
    """Independent/rare Bernoulli or shared-uniform mixture blocks under a true null.

    Block scenarios use a shared uniform draw with probability .75 and a private
    draw otherwise; marginal prevalences remain p while dependence is positive.
    Labels never enter generation. Blocks contain up to five candidates.
    """
    if scenario not in ("independent", "rare", "positive_blocks"):
        raise ValueError(f"unknown scenario: {scenario}")
    prevalence = rng.uniform(.005, .05, n_candidates) if scenario == "rare" else rng.uniform(.05, .5, n_candidates)
    uniforms = rng.random((n_units, n_candidates))
    if scenario == "positive_blocks":
        shared = rng.random((n_units, (n_candidates + 4) // 5))
        use_shared = rng.random((n_units, n_candidates)) < .75
        uniforms = np.where(use_shared, shared[:, np.arange(n_candidates) // 5], uniforms)
    return {f"f{k:04}": (uniforms[:, k] < p).astype(int) for k, p in enumerate(prevalence)}


def _simulation_rep(task):
    index, seed, n_per_group, n_candidates, scenario, permutations = task
    rng = np.random.default_rng(seed)
    labels = np.repeat([1, 0], n_per_group)
    # Same stratified split implementation as production; import avoids raw data loading.
    from .data import Dataset
    split = Dataset._stratified_split(labels, seed + 1)
    scores = null_scores(rng, len(labels), n_candidates, scenario)
    cfg = RunConfig(dataset="simulation", text_col="text", group_col="group", permutations=permutations)
    return {"replication": index, "seed": seed, **evaluate(labels, split, scores, cfg)}


def load_bank(run_dir, labels_path=None, reconstruct=False):
    """Validate saved matrices; require explicit labels or audited legacy ordering.

    Reproduction of all stored d1/d2 values is a necessary check, not independent
    verification of the original respondent labels or randomization blocks.
    """
    root = Path(run_dir).resolve()
    names = ["00_config.json", "00_partition.json", "02_consolidated.json",
             "03_measured.json", "04_selected.json", "00_runspec.json"]
    artifacts = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in names}
    cfg = RunConfig(**artifacts["00_config.json"]["config"])
    if cfg.condition != "real" or cfg.measurement_design != "rotate":
        raise ValueError("this frozen binary-bank tool requires a real balanced-rotation run")
    if cfg.fdr_q != .05 or cfg.fdr_q_exploratory != .10 or cfg.effect_floor is not None:
        raise ValueError("Section 4 summaries currently require q=.05/.10 and no effect floor")
    partition = artifacts["00_partition.json"]
    uids = [str(u) for u in partition["measurement_uids"]]
    split = np.asarray(partition["measurement_split"])
    if len(set(uids)) != len(uids) or len(split) != len(uids) or set(split) != {1, 2}:
        raise ValueError("invalid/duplicate UIDs or measurement halves")
    if bool(labels_path) == bool(reconstruct):
        raise ValueError("supply either a UID label table or explicit legacy reconstruction")
    if labels_path:
        with Path(labels_path).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows or not {"uid", "group"}.issubset(rows[0]):
            raise ValueError("label table needs uid,group columns")
        mapping = {}
        for row in rows:
            if row["uid"] in mapping or row["group"] not in {"0", "1"}:
                raise ValueError("duplicate UID or noncanonical group in label table")
            mapping[row["uid"]] = int(row["group"])
        if any(u not in mapping for u in uids):
            raise ValueError("label table is missing measurement UIDs")
        labels = np.array([mapping[u] for u in uids])
        provenance = {"kind": "explicit_uid_table", "path": str(Path(labels_path).resolve()),
                      "sha256": sha256(labels_path), "source_verification": "supplied by caller"}
    else:
        n = cfg.n_per_group
        if len(uids) != 2 * n:
            raise ValueError("legacy ordering needs exactly 2*n_per_group units")
        labels = np.repeat([1, 0], n)
        provenance = {"kind": "legacy_order_reconstruction", "independently_verified": False,
                      "assumption": "Dataset concatenates focal reservation then reference reservation",
                      "restriction": "engineering pilot only; obtain source-verified UID labels"}
    expected_cells = partition["group_sizes"]
    for half in (1, 2):
        for group in (0, 1):
            count = int(((split == half) & (labels == group)).sum())
            if count < 1 or count != expected_cells[f"split{half}_by_active_label"][str(group)]:
                raise ValueError("labels disagree with saved group-by-half counts")
    candidates = artifacts["02_consolidated.json"]["candidates"]
    candidate_ids = [c["candidate_id"] for c in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate candidate IDs")
    measured = artifacts["03_measured.json"]
    selected = artifacts["04_selected.json"]
    stored = {r["candidate_id"]: r for r in selected["results"]}
    if not measured or set(measured) != set(stored) or not set(measured).issubset(candidate_ids):
        raise ValueError("measured/selected candidate IDs disagree")
    if selected["n_tested"] != len(measured) or selected["n_candidates"] != len(candidates):
        raise ValueError("saved candidate counts disagree")
    scores = {}
    fallback_cells = {}
    for cid, item in measured.items():
        y = np.asarray(item["y"])
        assignment = np.asarray(item["model_assignment"])
        if y.shape != (len(uids),) or not np.isin(y, [0, 1]).all():
            raise ValueError(f"nonbinary, nonfinite or misaligned score vector: {cid}")
        if assignment.shape != y.shape or not set(assignment).issubset(cfg.rotation_pool):
            raise ValueError(f"invalid model assignments: {cid}")
        for half in (1, 2):
            actual = float(y[(split == half) & (labels == 1)].mean() -
                           y[(split == half) & (labels == 0)].mean())
            if not np.isclose(actual, stored[cid][f"d{half}"], atol=1e-12, rtol=0):
                raise ValueError(f"reconstructed effect mismatch: {cid}, half {half}")
        cell_counts = {}
        for half in (1, 2):
            for group in (0, 1):
                cell_counts[f"g{group}_half{half}"] = {
                    model: int(((split == half) & (labels == group) & (assignment == model)).sum())
                    for model in cfg.rotation_pool}
        fallback_cells[cid] = cell_counts
        scores[cid] = y.astype(int)
    skipped = sorted(set(candidate_ids) - set(scores))
    metadata = {
        "source_run": str(root), "source_dataset_path": cfg.dataset,
        "source_dataset_exists_locally": Path(cfg.dataset).is_file(),
        "dataset_fingerprint": partition["dataset_fingerprint"],
        "source_artifact_sha256": {name: sha256(root / name) for name in names},
        "labels": provenance, "all_saved_half_effects_reproduced": True,
        "n_units": len(uids), "n_proposed": len(candidates), "n_tested": len(scores),
        "skipped_candidate_ids": skipped,
        "saved_n_validated": selected["n_validated"],
        "saved_n_suggestive": selected["n_suggestive"],
        "model_counts_by_candidate_and_cell": fallback_cells,
        "saved_model_versions": artifacts["00_runspec.json"].get("model_versions"),
    }
    return cfg, labels, split, scores, metadata


_FROZEN_BANK = None


def _init_frozen(cfg_dict, labels, split, scores):
    global _FROZEN_BANK
    _FROZEN_BANK = (RunConfig(**cfg_dict), labels, split, scores)


def _frozen_rep(task):
    index, seed = task
    cfg, labels, split, scores = _FROZEN_BANK
    rng = np.random.default_rng(seed)
    shuffled = labels.copy()
    for half in (1, 2):
        mask = split == half
        shuffled[mask] = rng.permutation(labels[mask])
    return {"replication": index, "seed": seed, **evaluate(shuffled, split, scores, cfg)}


def provenance(args):
    here = Path(__file__).resolve()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here.parent,
                                         text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=here.parent, text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"created_utc": datetime.now(timezone.utc).isoformat(),
            "study_status": "engineering_pilot", "arguments": vars(args),
            "software_commit": commit, "working_tree_dirty": dirty,
            "source_sha256": {p.name: sha256(p) for p in
                              [here, here.with_name("select.py"), here.with_name("core.py"),
                               here.with_name("data.py"), here.with_name("config.py")]},
            "python_version": platform.python_version(), "numpy_version": np.__version__,
            "api_calls": 0,
            "selection_rng": "production stage5 default seed 7; no seed sweep or tuning",
            "limitations": ["Pilot evidence; no automatic calibration pass/fail claim.",
                            "Intervals quantify Monte Carlo uncertainty conditional on the design.",
                            "No assertion of FDR control under arbitrary feature dependence."]}


def write_results(out_dir, manifest, rows, summary):
    out = Path(out_dir)
    # Directory is reserved before work starts; individual files are created only once.
    for name, obj in [("manifest.json", manifest), ("summary.json", summary)]:
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(obj, stream, indent=2, allow_nan=False)
            stream.write("\n")
    if rows:
        with (out / "replications.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate", help="P1: production selection on global-null binary features")
    sim.add_argument("--scenario", choices=["independent", "rare", "positive_blocks"], required=True)
    sim.add_argument("--n-per-group", type=int, default=100)
    sim.add_argument("--candidates", type=int, default=12)
    sim.add_argument("--permutations", type=int, default=240, help="floor; production auto-scales")
    frozen = sub.add_parser("frozen", help="P2: conditional frozen-bank label shuffles")
    frozen.add_argument("--run", required=True)
    labels = frozen.add_mutually_exclusive_group(required=True)
    labels.add_argument("--labels", help="CSV with source-verified uid,group columns; group is 0/1")
    labels.add_argument("--reconstruct-legacy-order", action="store_true")
    for p in (sim, frozen):
        p.add_argument("--reps", type=int, default=100)
        p.add_argument("--seed", type=int, default=260_000)
        p.add_argument("--workers", type=int, default=1)
    inv = sub.add_parser("inventory", help="audit saved real binary-rotation runs without API calls")
    inv.add_argument("--root", required=True)
    for p in (sim, frozen, inv):
        p.add_argument("--out", required=True, help="new output directory; overwrite is forbidden")
    args = parser.parse_args(argv)
    if args.command != "inventory":
        if args.reps < 1 or args.workers < 1 or args.seed < 0:
            parser.error("reps/workers must be positive and seed nonnegative")
    if args.command == "simulate" and (args.n_per_group < 2 or args.candidates < 1 or args.permutations < 1):
        parser.error("need n_per_group >= 2, candidates >= 1, permutations >= 1")
    # Never touch the source artifacts. Refuse reused output IDs before starting work.
    Path(args.out).mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifest = provenance(args)
    rows = []
    if args.command == "simulate":
        tasks = [(i, args.seed + i, args.n_per_group, args.candidates, args.scenario, args.permutations)
                 for i in range(args.reps)]
        if args.workers == 1:
            rows = list(map(_simulation_rep, tasks))
        else:
            with ProcessPoolExecutor(max_workers=args.workers) as pool:
                rows = list(pool.map(_simulation_rep, tasks))
        summary = summarize_null(rows)
    elif args.command == "frozen":
        cfg, groups, split, scores, bank_meta = load_bank(args.run, args.labels, args.reconstruct_legacy_order)
        manifest["bank"] = bank_meta
        manifest["limitations"] += [
            "Frozen candidates/measurements; discovery and classification are not rerun.",
            "Labels shuffle within original halves; no experimental block metadata available."]
        tasks = [(i, args.seed + i) for i in range(args.reps)]
        initargs = (asdict(cfg), groups, split, scores)
        if args.workers == 1:
            _init_frozen(*initargs)
            rows = list(map(_frozen_rep, tasks))
        else:
            with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_frozen, initargs=initargs) as pool:
                rows = list(pool.map(_frozen_rep, tasks))
        summary = summarize_null(rows)
    else:
        runs = sorted(Path(args.root).resolve().rglob("04_selected.json"))
        if not runs:
            raise ValueError("no saved selection artifacts under root")
        audited = []
        for selected_path in runs:
            try:
                *_, meta = load_bank(selected_path.parent, reconstruct=True)
                audited.append({"status": "audited_legacy_order", **meta})
            except (ValueError, KeyError, TypeError, OSError) as exc:
                audited.append({"source_run": str(selected_path.parent), "status": "failed_audit", "error": str(exc)})
        summary = {"runs": audited, "n_runs": len(audited),
                   "n_failed_audit": sum(r["status"] == "failed_audit" for r in audited)}
    manifest["wall_seconds"] = round(time.monotonic() - started, 3)
    write_results(args.out, manifest, rows, summary)
    if args.command == "inventory":
        print(json.dumps({k: summary[k] for k in ["n_runs", "n_failed_audit"]}))
    else:
        print(json.dumps(summary, indent=2))
    print(f"Saved {Path(args.out).resolve()}")
    if args.command == "inventory" and summary["n_failed_audit"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
