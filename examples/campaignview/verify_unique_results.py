"""Rebuild the unique-biography input, audit overlap, and replay saved results offline."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import itertools
import json
from pathlib import Path
import tempfile

import numpy as np

from discern.config import RunConfig
from discern.data import Dataset
from discern.select import run_selection
from prep_bio_party_unique import eligible_rows, prepare, row_tokens

HERE = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return Path(path).read_text(encoding="utf-8")


def check_preparation():
    report = json.loads(load(HERE / "data/unique_biography_preparation.json"))
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        rebuilt = prepare(HERE / "data/source/biographical_narratives.csv", folder / "data.csv",
                          folder / "rows.csv", folder / "preparation.json")
        require((folder / "data.csv").read_bytes() == (HERE / "data/bio_party_unique.csv").read_bytes(),
                "Prepared biographies differ from reconstruction")
        require((folder / "rows.csv").read_bytes() == (HERE / "data/unique_biography_rows.csv").read_bytes(),
                "Row-level inclusion record differs from reconstruction")
        require(rebuilt == report, "Preparation record differs from reconstruction")
    return report


def check_partition(condition):
    cfg, _ = RunConfig.from_file(HERE / f"config.unique.{condition}.json")
    cfg.validate()
    data = Dataset(cfg)
    source = {r["id"]: r for r in eligible_rows(HERE / "data/source/biographical_narratives.csv").to_dict("records")}
    partitions = {"discovery_pool": set(data.pool.uid),
                  "measurement_half_1": {u for u, h in zip(data.m_uid, data.m_split) if h == 1},
                  "measurement_half_2": {u for u, h in zip(data.m_uid, data.m_split) if h == 2}}
    tokens = {}
    for name, uids in partitions.items():
        values = []
        for uid in uids:
            require(uid in source, f"Unknown source biography: {uid}")
            values.extend(row_tokens(source[uid]))
        require(len(values) == len(set(values)), f"Repeated identities or texts within {name}")
        tokens[name] = set(values)
    overlap = {}
    for a, b in itertools.combinations(partitions, 2):
        require(not partitions[a].intersection(partitions[b]), f"Shared rows: {a}/{b}")
        shared = tokens[a].intersection(tokens[b])
        overlap[f"{a}__{b}"] = {kind: sum(t[0] == kind for t in shared)
                                for kind in ("fec", "bioguide", "name", "text")}
        require(not shared, f"Shared identities or texts: {a}/{b}")
    report = {"condition": condition, "dataset_fingerprint": data.fingerprint,
              "n_discovery_pool": len(data.pool), "n_measurement": len(data.m_uid),
              "group_sizes": data.group_min_sizes(), "shared_tokens_between_partitions": overlap,
              "repeated_tokens_within_partitions": 0}
    return cfg, data, report


def check_results(condition, run_dir, cfg, data):
    run_dir = Path(run_dir)
    artifact = lambda name: json.loads(load(run_dir / f"{name}.json"))
    partition, discovery = artifact("00_partition"), artifact("01_discovery")
    candidates = artifact("02_consolidated")["candidates"]
    measured, expected = artifact("03_measured"), artifact("04_selected")
    archived = artifact("00_config")["config"]
    for key, value in archived.items():
        if key not in {"base_dir", "dataset", "output_dir", "classify_workers"}:
            require(getattr(cfg, key) == value, f"{condition}: configuration field differs: {key}")
    require(partition["dataset_fingerprint"] == data.fingerprint, "Dataset fingerprint differs")
    require(partition["measurement_uids"] == data.m_uid, "Measurement order differs")
    require(partition["measurement_split"] == data.m_split.tolist(), "Measurement halves differ")
    require(partition["n_discovery_pool"] == len(data.pool), "Discovery pool size differs")
    pool_labels = dict(zip(data.pool.uid, data.pool_labels()))
    shown = set()
    for call in discovery["calls"]:
        for slot in ("A", "B"):
            uids = call[f"slot{slot}_uids"]
            require(not set(uids).intersection(data.m_uid), "Discovery includes a measurement row")
            require(all(pool_labels.get(uid) == call[f"slot{slot}_canonical_group"] for uid in uids),
                    "Discovery labels do not match the recorded condition")
            shown.update(uids)
    ids = {c["candidate_id"] for c in candidates}
    require(len(ids) == len(candidates) and set(measured).issubset(ids), "Candidate IDs disagree")
    assignments = Counter()
    for cid, values in measured.items():
        require(len(values["y"]) == len(data.m_uid) and set(values["y"]) <= {0, 1},
                f"Incomplete or nonbinary measurements: {cid}")
        require(len(values["model_assignment"]) == len(data.m_uid)
                and set(values["model_assignment"]) <= set(cfg.rotation_pool),
                f"Invalid classifier assignments: {cid}")
        assignments.update(values["model_assignment"])
    actual = run_selection(cfg, data, measured, candidates)
    by_id = {r["candidate_id"]: r for r in actual["results"]}
    require(set(by_id) == {r["candidate_id"] for r in expected["results"]}, "Selection coverage differs")
    for row in expected["results"]:
        result = by_id[row["candidate_id"]]
        for field in ("d1", "d2", "mean_effect", "perm_p"):
            require(np.isclose(result[field], row[field], rtol=0, atol=1e-12),
                    f"{row['feature_name']}: {field} differs")
        for field in ("same_sign", "validated", "validated_exploratory", "tier", "definition", "classification_question"):
            require(result[field] == row[field], f"{row['feature_name']}: {field} differs")
    for field in ("n_candidates", "n_tested", "n_validated", "n_suggestive", "n_uncorrected", "permutations"):
        require(actual[field] == expected[field], f"Run total differs: {field}")
    with (HERE / f"features.unique.{condition}.csv").open(encoding="utf-8", newline="") as stream:
        exported = list(csv.DictReader(stream))
    require(len(exported) == len(by_id) and {r["feature_id"] for r in exported} == set(by_id),
            "Feature table coverage differs")
    for row in exported:
        cid = row["feature_id"]
        result = by_id[cid]
        for field in ("feature_name", "definition", "classification_question", "tier"):
            require(row[field] == result[field], f"Feature table text differs: {cid}/{field}")
        y = np.asarray(measured[cid]["y"])
        numbers = {"focal_prevalence_percent": 100 * y[data.measurement_labels() == 1].mean(),
                   "reference_prevalence_percent": 100 * y[data.measurement_labels() == 0].mean(),
                   "half1_difference_pp": 100 * result["d1"], "half2_difference_pp": 100 * result["d2"],
                   "difference_pp": 100 * result["mean_effect"], "permutation_p": result["perm_p"]}
        for field, value in numbers.items():
            require(np.isclose(float(row[field]), value, rtol=0, atol=1e-12),
                    f"Feature table number differs: {cid}/{field}")
    return {"n_hypotheses": len(discovery["split1"]) + len(discovery["split2"]),
            **{field: actual[field] for field in ("n_candidates", "n_tested", "n_validated", "n_suggestive", "n_uncorrected", "permutations")},
            "n_skipped_unmeasurable": len(ids) - len(measured), "distinct_discovery_biographies_shown": len(shown),
            "actual_classifier_counts": dict(assignments), "all_saved_statistics_reproduced": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Check the input and partitions without loading completed runs")
    parser.add_argument("--real-run", type=Path, default=HERE / "saved_unique/real_r1")
    parser.add_argument("--placebo-run", type=Path, default=HERE / "saved_unique/placebo_r0")
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    if not args.preflight:
        checksums = json.loads(load(HERE / "checksums.unique.json"))
        for name, digest in checksums.items():
            require(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, f"Checksum differs: {name}")
    preparation = check_preparation()
    result = {"api_calls": 0, "retained_biographies": preparation["retained_biographies"], "runs": []}
    for condition, folder in (("real", args.real_run), ("placebo", args.placebo_run)):
        cfg, data, report = check_partition(condition)
        if not args.preflight:
            report.update(check_results(condition, folder, cfg, data))
        result["runs"].append(report)
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("Input and partitions verified. No API calls made." if args.preflight else
          "Both unique-biography runs verified. No API calls made.")


if __name__ == "__main__":
    main()
