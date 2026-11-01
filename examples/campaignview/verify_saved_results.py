"""Reconstruct both saved CampaignView runs and verify their statistics offline."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from discern.config import RunConfig
from discern.data import Dataset
from discern.select import run_selection
from prep_bio_party import prepare

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_run(condition):
    name = "real_r1" if condition == "real" else "placebo_r0"
    saved = ROOT / "saved" / name
    cfg, _ = RunConfig.from_file(ROOT / f"config.{condition}.json")
    cfg.validate()
    data = Dataset(cfg)
    partition = load(saved / "00_partition.json")
    discovery = load(saved / "01_discovery.json")
    candidates = load(saved / "02_consolidated.json")["candidates"]
    measurements = load(saved / "03_measured.json")
    expected = load(saved / "04_selected.json")
    archived_cfg = load(saved / "00_config.json")["config"]
    for key, value in archived_cfg.items():
        if key not in {"base_dir", "dataset", "output_dir"}:
            require(getattr(cfg, key) == value, f"{name}: changed configuration field {key}")
    require(data.fingerprint == partition["dataset_fingerprint"], f"{name}: input fingerprint differs")
    require(data.m_uid == partition["measurement_uids"], f"{name}: measurement order differs")
    require(data.m_split.tolist() == partition["measurement_split"], f"{name}: halves differ")
    require(len(data.pool) == partition["n_discovery_pool"], f"{name}: pool size differs")
    pool_labels = dict(zip(data.pool.uid, data.pool_labels()))
    for call in discovery["calls"]:
        for slot in ("A", "B"):
            uids = call[f"slot{slot}_uids"]
            require(not set(uids).intersection(data.m_uid), f"{name}: discovery overlaps measurement")
            require(all(pool_labels.get(uid) == call[f"slot{slot}_canonical_group"] for uid in uids),
                    f"{name}: discovery labels differ")
    ids = [c["candidate_id"] for c in candidates]
    require(len(ids) == len(set(ids)) and set(measurements) == set(ids), f"{name}: candidate coverage differs")
    for cid, values in measurements.items():
        require(len(values["y"]) == len(data.m_uid), f"{name}/{cid}: incomplete measurements")
        require(set(values["y"]) <= {0, 1}, f"{name}/{cid}: nonbinary measurement")
        require(len(values["model_assignment"]) == len(data.m_uid), f"{name}/{cid}: missing classifier")
        require(set(values["model_assignment"]) <= set(cfg.rotation_pool), f"{name}/{cid}: unknown classifier")
    actual = run_selection(cfg, data, measurements, candidates)
    lookup = {r["candidate_id"]: r for r in actual["results"]}
    require(set(lookup) == {r["candidate_id"] for r in expected["results"]}, f"{name}: selected row coverage differs")
    for row in expected["results"]:
        result = lookup[row["candidate_id"]]
        for field in ("d1", "d2", "mean_effect", "perm_p"):
            require(np.isclose(result[field], row[field], rtol=0, atol=1e-12), f"{name}: {row['feature_name']}: {field} differs")
        for field in ("same_sign", "validated", "validated_exploratory", "tier", "definition", "classification_question"):
            require(result[field] == row[field], f"{name}: {row['feature_name']}: {field} differs")
    for field in ("n_candidates", "n_tested", "n_validated", "n_suggestive", "n_uncorrected", "permutations"):
        require(actual[field] == expected[field], f"{name}: {field} differs")
    with (ROOT / f"features.{condition}.csv").open(encoding="utf-8", newline="") as stream:
        exported = list(csv.DictReader(stream))
    require(len(exported) == len(lookup) and {r['feature_id'] for r in exported} == set(lookup),
            f"{name}: incomplete feature CSV")
    for row in exported:
        cid = row["feature_id"]
        result = lookup[cid]
        y = np.asarray(measurements[cid]["y"])
        for field in ("feature_name", "definition", "classification_question", "tier"):
            require(row[field] == result[field], f"{name}/{cid}: exported {field} differs")
        values = {
            "focal_prevalence_percent": 100 * y[data.measurement_labels() == 1].mean(),
            "reference_prevalence_percent": 100 * y[data.measurement_labels() == 0].mean(),
            "half1_difference_pp": 100 * result["d1"], "half2_difference_pp": 100 * result["d2"],
            "difference_pp": 100 * result["mean_effect"], "permutation_p": result["perm_p"],
        }
        for field, value in values.items():
            require(np.isclose(float(row[field]), value, rtol=0, atol=1e-12), f"{name}/{cid}: exported {field} differs")
    assignments = Counter()
    for values in measurements.values():
        assignments.update(values["model_assignment"])
    print(f"{name}: {len(discovery['split1']) + len(discovery['split2'])} hypotheses; "
          f"all {actual['n_tested']} candidate effects, p-values, and exported rows match.")
    print(f"  {actual['n_validated']} validated; {actual['n_suggestive']} suggestive; "
          f"{actual['n_uncorrected']} uncorrected; {actual['permutations']} permutations.")
    print(f"  Actual classifier counts (including fallbacks): {dict(assignments)}")


def main():
    for name, expected in load(ROOT / "checksums.json").items():
        path = ROOT / name
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Checksum differs: {name}")
    # Rebuild in a temporary folder; leave the recorded data untouched.
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "bio_party.csv"
        prepare(ROOT / "data/source/biographical_narratives.csv", rebuilt)
        require(rebuilt.read_bytes() == (ROOT / "data/bio_party.csv").read_bytes(), "Reconstructed CSV bytes differ")
    counts = pd.read_csv(ROOT / "data/bio_party.csv")["group"].value_counts().to_dict()
    require(counts == {1: 2600, 0: 2505}, "Prepared group sizes differ")
    print("Data reconstruction and recorded file checksums match: 5,105 biographies.")
    for condition in ("real", "placebo"):
        check_run(condition)
    print("Both runs verified. No API calls made.")


if __name__ == "__main__":
    main()
