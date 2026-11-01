"""Prepare a draft substantive crosswalk and prospective Hurst stability run recipes.

The generated recipes are plans; they do not execute APIs. Measurement-only and
discovery-only recipes must be run as isolated stages, not as full CLI pipelines.
"""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.config import RunConfig
from discern.core import DEFAULT_POOL
from discern.stability import write_crosswalk, write_presence_table
from discern.validation import sha256


def prepare(reference_run, portable_config, out, placebo_runs=20):
    if placebo_runs < 0:
        raise ValueError("placebo_runs must be nonnegative")
    reference_run, portable_config, out = Path(reference_run).resolve(), Path(portable_config).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = RunConfig(**json.loads(portable_config.read_text()))
    candidates = json.loads((reference_run / "02_consolidated.json").read_text())["candidates"]
    selected = json.loads((reference_run / "04_selected.json").read_text())["results"]
    order = {r["candidate_id"]: i for i, r in enumerate(selected)}
    candidates.sort(key=lambda c: order.get(c["candidate_id"], len(order)))
    runs = [{"run_id": "ARCHIVE", "status": "complete", "artifact_path": str(reference_run),
             "condition": "real",
             "design": "archived 3-model reference; descriptive anchor, not current defaults",
             "config_path": str(portable_config)}]
    recipes = []

    def recipe(rid, design, overrides, stage_mode):
        local = RunConfig(**{**asdict(cfg), **overrides,
                            "output_dir": str(out / "runs" / rid)})
        local.validate()
        path = out / f"{rid}.config.json"
        path.write_text(json.dumps(asdict(local), indent=2) + "\n")
        runs.append({"run_id": rid, "status": "planned", "artifact_path": "",
                     "condition": local.condition,
                     "design": design, "config_path": str(path)})
        recipes.append({"run_id": rid, "stage_mode": stage_mode, "config_sha256": sha256(path),
                        "fixed_reference_candidates": str(reference_run / "02_consolidated.json")
                        if stage_mode == "measurement_only" else None,
                        "notes": "For discovery-only runs, measure the adjudicated family union on the locked evaluation units with the reference pool."
                        if stage_mode == "discovery_only" else ""})

    for i in range(1, 11):
        recipe(f"R{i:02}", "same archived pool and partition; new discovery seed",
               {"discovery_seed": 1000 + i}, "full_pipeline")
    pools = {"DEFAULTS": list(DEFAULT_POOL), "OPENAI": ["gpt-4o-mini", "gpt-4.1-mini"],
             "NONOPENAI": ["claude-haiku", "deepseek"]}
    for label, pool in pools.items():
        recipe(f"M_{label}", "fixed candidate bank and evaluation units; measurement pool changes",
               {"rotation_pool": pool}, "measurement_only")
        recipe(f"D_{label}", "discovery pool changes; common reference measurement after alignment",
               {"discovery_models": pool}, "discovery_only")
    # A separate end-to-end defaults comparison is useful but changes two stages.
    recipe("E_DEFAULTS", "current default discovery+measurement pools; descriptive joint sensitivity",
           {"rotation_pool": list(DEFAULT_POOL), "discovery_models": list(DEFAULT_POOL)}, "full_pipeline")
    for i in range(1, placebo_runs + 1):
        recipe(f"P{i:02}", "full-pipeline label placebo; archived reference pool and fixed reservation",
               {"condition": "placebo", "run_index": i - 1}, "full_pipeline")
    memberships = []
    # Two deliberately transparent draft broad/narrow groupings; all decisions
    # require independent review, including the singleton anchors.
    merged = {"c_e8a8d66e75afbfd1": ("c_5e0c85b9b9f85fd8", "narrower"),
              "c_6df86b887be1ac03": ("c_bfb8aa998fb8a2af", "related")}
    by_id = {c["candidate_id"]: c for c in candidates}
    anchors = [c for c in candidates if c["candidate_id"] not in merged]
    family_ids = {c["candidate_id"]: f"F{i:02}" for i, c in enumerate(anchors, 1)}
    # Human matching input excludes effects, significance, group names and run identity.
    blind = []
    for c in candidates:
        cid = c["candidate_id"]
        anchor, relation = merged.get(cid, (cid, "anchor"))
        memberships.append({"family_id": family_ids[anchor], "family_label": by_id[anchor]["feature_name"],
                            "run_id": "ARCHIVE", "candidate_id": cid, "relation": relation,
                            "mapping_status": "draft"})
    blind_candidates = sorted(candidates, key=lambda c: c["candidate_id"])
    blind_candidates = [blind_candidates[i] for i in np.random.default_rng(260026).permutation(len(blind_candidates))]
    for i, c in enumerate(blind_candidates, 1):
        blind.append({"item_id": f"I{i:03}", "feature_name": c["feature_name"],
                      "definition": c["definition"], "classification_question": c["classification_question"],
                      "rater1_family": "", "rater1_relation": "", "rater2_family": "",
                      "rater2_relation": "", "adjudicated_family": "", "adjudicated_relation": ""})
    for name, records in [("runs.csv", runs), ("family_memberships.csv", memberships), ("blind_matching.csv", blind)]:
        with (out / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    (out / "matching_key.json").write_text(json.dumps({f"I{i:03}": c["candidate_id"]
                                                     for i, c in enumerate(blind_candidates, 1)}, indent=2) + "\n")
    write_crosswalk(runs, memberships, out / "crosswalk.csv")
    write_presence_table(runs, memberships, out / "combined_table.csv")
    write_presence_table(runs, memberships, out / "proposal_presence.csv", stage="proposed")
    (out / "TABLE_LEGEND.md").write_text(
        "# Combined real and placebo run table\n\n"
        "`combined_table.csv` is the main exhibit: one column per real or full-pipeline placebo run.\n"
        "The first rows give distinct consolidated candidates suggested, measured, validated at q=.05, "
        "and suggestive-only counts. Suggested means the candidate bank after consolidation, "
        "not the larger list of raw discovery hypotheses.\n\n"
        "Feature rows are substantive families: ✓ means at least one member was validated at q=.05; "
        "– means no validated member. Counts at the top are candidate counts, so multiple members "
        "of a family can yield fewer checks than validated candidates; the validated-family count "
        "is also shown. Family mappings are still draft.\n\n"
        "NOT RUN means no result yet. A placebo may propose many candidates and still have dashes "
        "in every feature row after validation. A surviving placebo-only construct must be added "
        "as a row; the table generator rejects unmapped validated features. Dashes are never forced.\n\n"
        "`proposal_presence.csv` shows which families were suggested, regardless of validation; "
        "? marks incomplete semantic matching. `crosswalk.csv` retains tiers, effects, mapping "
        "relations and unmeasurable status. Real and placebo features use the same matching rubric.\n\n"
        "P01–P20 are prospective full-pipeline placebos, not the already completed frozen-matrix "
        "shuffles. Those diagnostics hold candidate generation fixed and remain separately identified.\n",
        encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "status": "draft scaffold; only ARCHIVE has observed results",
        "source_run": str(reference_run), "portable_config_sha256": sha256(portable_config),
        "script_sha256": sha256(__file__),
        "crosswalk_code_sha256": sha256(Path(__file__).resolve().parents[1] / "src/discern/stability.py"),
        "n_reference_candidates": len(candidates), "n_draft_families": len(anchors), "recipes": recipes,
        "n_planned_full_pipeline_placebos": placebo_runs,
        "rules": ["DRAFT mappings are not adjudicated equivalence claims.",
                  "V/S/U/NV are candidate-level tiers; family membership is not a new significance test.",
                  "Keep multiple member estimates separate; do not select the largest effect as the family effect.",
                  "NOT RUN differs from ABSENT, UNRESOLVED, NV and SKIP.",
                  "Run-level matching complete and adjudicated is required before claiming absence.",
                  "R01-R10 share a fixed reservation and halves; do not treat them as independent corpora.",
                  "Current DEFAULTS is read from repository code; archived reference used only three models.",
                  "Model recipes require provider availability/version checks before live execution.",
                  "Combined-table checks mean validated presence; dashes mean no validated member, never an assumed placebo outcome.",
                  "All validated placebo-only candidates must be mapped and retained as rows.",
                  "Prospective blinded matching should randomize opaque item IDs after all comparison runs arrive; current file is a matching-form scaffold."]
    }, indent=2) + "\n")
    print(f"Prepared {len(anchors)} draft families, {len(runs)} run columns: {out / 'crosswalk.csv'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-run", required=True)
    parser.add_argument("--portable-config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--placebo-runs", type=int, default=20)
    args = parser.parse_args()
    prepare(args.reference_run, args.portable_config, args.out, args.placebo_runs)
