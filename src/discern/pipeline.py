"""Orchestrator: run one end-to-end v2 run from a RunConfig, persisting every stage atomically as
it completes (resumable) and emitting a human-readable summary. No work happens on import.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import core
from .audit import Audit
from .config import RunConfig
from .consolidate import run_consolidation
from .data import Dataset
from .discovery import run_discovery
from .measure import Cache, run_measurement
from .select import run_selection


def run_pipeline(cfg: RunConfig, base_dir: Path, run_name: str | None = None,
                 resume: bool = True, log=print) -> dict:
    """Execute discovery -> consolidate -> measure -> select. Returns the selection artifact.
    Each stage is written under output_dir/<run_name>/ the moment it finishes."""
    t0 = time.time()
    cfg = cfg.resolve(base_dir)
    cfg.validate()
    note = cfg.unpinned_pool_note()
    if note:
        log(f"[note] {note}")

    run_name = run_name or f"{cfg.condition}_r{cfg.run_index}"
    run_dir = Path(cfg.output_dir) / run_name
    audit = Audit(run_dir)

    data = Dataset(cfg)
    # run-spec guard (Terra P0-a): before loading ANY cached stage, verify a resumed run's identity
    # matches the current config + dataset. A mismatch means the run name was reused under a changed
    # configuration -> raise rather than silently blend old artifacts with a new config.
    spec = cfg.spec_hash(data.fingerprint)
    prev = audit.load_stage("00_runspec")
    if resume and prev is not None and prev.get("spec_hash") != spec:
        raise ValueError(
            f"run '{run_name}' already exists under a DIFFERENT configuration "
            f"(stored spec {prev.get('spec_hash')} != current {spec}). Use a new run name, or delete "
            f"{run_dir} to restart fresh — refusing to blend artifacts across configs.")
    from . import __version__ as pkg_version   # release identifier: config hash alone can't
    # record the runtime-resolved version of every model this run will use — provenance for the
    # unpinned aliases (whose snapshot can drift) so a completed run is fully auditable. cfg.active_models()
    # is the single source of truth for the ACTIVE set (discovery + consolidation + the measurement design
    # in force + the theme model iff theming is on) — shared with keys.py and the unpinned-alias note, so
    # we never probe a model the run won't call, or omit one it will.
    used_models = sorted(cfg.active_models())
    model_versions = [core.probe_model_version(m) for m in used_models]
    audit.write_stage("00_runspec", {"spec_hash": spec, "dataset_fingerprint": data.fingerprint,
                                     "prompt_version": cfg.prompt_version,
                                     "package_version": pkg_version,  # ...identify code changes
                                     "discovery_prompt_variant": cfg.discovery_prompt_variant,
                                     "model_versions": model_versions,
                                     "unpinned_pool_note": note})
    audit.write_stage("00_config", {"config": cfg.to_json(), "unpinned_pool_note": note})
    audit.write_stage("00_partition", {
        "dataset_fingerprint": data.fingerprint,
        "group_sizes": data.group_min_sizes(),
        "measurement_uids": data.m_uid,
        "measurement_split": [int(s) for s in data.m_split],
        "n_discovery_pool": len(data.pool)})
    log(f"[{run_name}] partition: {len(data.pool)} discovery-pool units, "
        f"{len(data.m_uid)} held-out measurement units ({cfg.n_per_group}/group)")

    # --- Stage 1-2: discovery ---
    disc = audit.load_stage("01_discovery") if resume else None
    if disc is None:
        disc = run_discovery(cfg, data, audit)
        audit.write_stage("01_discovery", disc)
    n_hyps = len(disc["split1"]) + len(disc["split2"])
    log(f"[{run_name}] discovery: {n_hyps} hypotheses ({len(disc['split1'])}+{len(disc['split2'])})")

    # --- Stage 3: consolidation ---
    cons = audit.load_stage("02_consolidated") if resume else None
    if cons is None:
        cons = run_consolidation(cfg, disc, audit)
        audit.write_stage("02_consolidated", cons)
    candidates = cons["candidates"]
    log(f"[{run_name}] consolidation: {len(candidates)} distinct candidates"
        + (f" (dedup merged {cons.get('dedup', {}).get('merged', 0)})" if cons.get("dedup") else ""))
    # cost guard (Terra P2-f): fail before measurement rather than silently billing a huge batch
    if len(candidates) > cfg.max_candidates:
        raise ValueError(f"{len(candidates)} candidates exceeds max_candidates={cfg.max_candidates}; "
                         f"raise the guard deliberately if intended, or inspect consolidation output")

    # --- Stage 4: measurement ---
    # unit_label is part of the rendered classifier prompt, so it is part of cache identity
    # (byte-identical for the default label, but a different label must never share answers)
    cache = Cache(Path(cfg.output_dir) / "class_cache.json", data.fingerprint,
                  cfg.prompt_version, f"design={cfg.measurement_design}|unit={cfg.unit_label}",
                  revisions=cfg.model_revision)
    meas = audit.load_stage("03_measured") if resume else None
    if meas is None:
        C = run_measurement(cfg, data, candidates, cache, audit)
        audit.write_stage("03_measured", C)
    else:
        C = meas
    # a candidate absent from C was dropped as unmeasurable (a persistently malformed answer);
    # surface the count so it is never silently lost (details are in events.jsonl).
    n_skipped = len(candidates) - len(C)
    _sk = f", {n_skipped} skipped (unmeasurable)" if n_skipped else ""
    log(f"[{run_name}] measured {len(C)} candidates on {len(data.m_uid)} units "
        f"({cfg.measurement_design}){_sk}")

    # --- Stage 5: selection ---
    sel = run_selection(cfg, data, C, candidates)
    sel["n_skipped_unmeasurable"] = n_skipped
    audit.write_stage("04_selected", sel)
    _write_summary(run_dir, cfg, run_name, n_hyps, sel)
    _sug = f" (+{sel.get('n_suggestive', 0)} suggestive)" if sel.get("fdr_q_exploratory") else ""
    log(f"[{run_name}] DONE: {sel['n_validated']}/{sel['n_candidates']} validated{_sug}{_sk} "
        f"-> {run_dir}")

    # --- Stage 6 (optional): post-validation theme grouping (navigation-only, non-selective) ---
    if cfg.organize_themes:
        from .themes import write_run_themes
        records = [{"candidate_id": r["candidate_id"], "feature_name": r["feature_name"],
                    "definition": r.get("definition", ""), "measured_direction": r["measured_direction"],
                    "mean_effect": r["mean_effect"], "perm_p": r["perm_p"],
                    "higher_group": r.get("higher_group")}
                   for r in sel["results"] if r["validated"]]
        art = write_run_themes(run_dir, records, audit=audit, model=cfg.theme_model,
                               legend=cfg.direction_legend())
        log(f"[{run_name}] themes: {art['n_themes']} groups over {art['n_validated']} features "
            f"(coverage_ok={art['coverage_ok']})")

    # wall-clock timing (native provenance for the cost/time recipe)
    dt = time.time() - t0
    audit.write_stage("07_timing", {"run": run_name, "wall_seconds": round(dt, 1),
                                    "minutes": round(dt / 60, 1), "n_candidates": sel["n_candidates"],
                                    "n_units": len(data.m_uid), "n_classifications": sel["n_candidates"] * len(data.m_uid),
                                    "measurement_design": cfg.measurement_design, "resumed": resume})
    sel["wall_seconds"] = round(dt, 1)
    log(f"[{run_name}] wall time: {dt/60:.1f} min")
    return sel


def _write_summary(run_dir, cfg, run_name, n_hyps, sel):
    confirmed = [r for r in sel["results"] if r["tier"] == "confirmed"]
    suggestive = [r for r in sel["results"] if r["tier"] == "suggestive"]
    n_sug = sel.get("n_suggestive", 0)
    q_exp = sel.get("fdr_q_exploratory")
    head = f"-> **{sel['n_validated']} validated** (FDR {cfg.fdr_q})"
    if q_exp:
        head += f" + **{n_sug} suggestive** (exploratory FDR {q_exp})"
    L = [f"# v2 run: {run_name}  ({cfg.condition})", "",
         f"- prompt_version: {cfg.prompt_version}",
         f"- measurement: {cfg.measurement_design}, n={2*cfg.n_per_group} "
         f"({cfg.n_per_group}/group), permutations={cfg.permutations}, FDR={cfg.fdr_q}",
         f"- discovery: {n_hyps} hypotheses -> {sel['n_candidates']} candidates {head}"]
    if sel.get("n_skipped_unmeasurable"):
        L.append(f"- note: {sel['n_skipped_unmeasurable']} candidate(s) dropped as unmeasurable "
                 f"(a persistently malformed classifier answer); see events.jsonl `candidate_skipped`.")
    L += [""]
    if cfg.effect_floor is not None:
        L.append(f"- effect floor (domain-specific, layered): |mean_effect| >= {cfg.effect_floor}")
        L.append("")
    L += [f"**Direction key:** {cfg.direction_legend()}.",
          "d1/d2 = the two independent data-half effects (validation requires the same sign in "
          "both). A positive pp value = the feature is more prevalent among "
          f"{cfg.focal_name()!r}; negative = more prevalent among {cfg.reference_name()!r}.", ""]

    def _block(r):
        return [f"### {r['feature_name']}  ({r['mean_effect']*100:+.0f} pp — more common among "
                f"{r['higher_group']}, p={r['perm_p']:.3f})",
                f"*{r['definition'].strip()}*",
                f"Q: {r['classification_question']}",
                f"d1={r['d1']*100:+.0f}pp  d2={r['d2']*100:+.0f}pp  id={r['candidate_id']}", ""]

    L += [f"## Validated features (FDR {cfg.fdr_q})", ""]
    for r in confirmed:
        L += _block(r)
    if q_exp:
        L += ["", f"## Suggestive features (exploratory — FDR {q_exp}, not {cfg.fdr_q})", "",
              "Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, "
              "not findings — the primary table above is the headline. Optionally sanity-check this "
              "tier with a placebo run.", ""]
        for r in suggestive:
            L += _block(r)
    n_none = sum(1 for r in sel["results"] if r["tier"] == "not_validated")
    L.append(f"## Not validated ({n_none})")
    for r in sel["results"]:
        if r["tier"] == "not_validated":
            L.append(f"- {r['feature_name']}  (d1={r['d1']*100:+.0f} d2={r['d2']*100:+.0f} pp, "
                     f"p={r['perm_p']:.3f}, same_sign={r['same_sign']})")
    (run_dir / "05_summary.md").write_text("\n".join(L))
