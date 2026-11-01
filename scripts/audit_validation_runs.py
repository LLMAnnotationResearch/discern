"""Verify completed compact-run artifacts and summarize measurement exceptions."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.config import RunConfig
from discern.data import Dataset
from discern.validation import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--artifacts", help="archived completed-run root")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows, cell_audit = [], {}
    for job in json.loads(Path(args.batch).read_text())["planned_jobs"]:
        cfg, _ = RunConfig.from_file(job["config_path"])
        data = Dataset(cfg)
        rid = job["run_id"]
        root = Path(args.artifacts).resolve() / rid if args.artifacts else Path(cfg.output_dir) / rid
        selected = json.loads((root / "04_selected.json").read_text())
        measured = json.loads((root / "03_measured.json").read_text())
        proposed = json.loads((root / "02_consolidated.json").read_text())["candidates"]
        partition = json.loads((root / "00_partition.json").read_text())
        discovery = json.loads((root / "01_discovery.json").read_text())
        if partition["measurement_uids"] != data.m_uid or partition["measurement_split"] != data.m_split.tolist():
            raise ValueError(f"{rid}: partition changed")
        if set(measured) != {r["candidate_id"] for r in selected["results"]}:
            raise ValueError(f"{rid}: selection is missing measured candidates")
        pool_labels = dict(zip(data.pool.uid, data.pool_labels()))
        for call in discovery["calls"]:
            for slot in ["A", "B"]:
                for uid in call[f"slot{slot}_uids"]:
                    if uid in data.meas_uids or pool_labels[uid] != call[f"slot{slot}_canonical_group"]:
                        raise ValueError(f"{rid}: discovery leakage/label inconsistency")
        fallback, failures = 0, 0
        with (root / "events.jsonl").open() as stream:
            for line in stream:
                event = json.loads(line)
                if event["stage"] == "measure":
                    fallback += event["kind"] == "fallback"
                    failures += event["kind"] == "failure"
        groups, halves = data.measurement_labels(), data.m_split
        altered = []
        cell_audit[rid] = {}
        for result in selected["results"]:
            cid = result["candidate_id"]
            y = np.asarray(measured[cid]["y"])
            models = np.asarray(measured[cid]["model_assignment"])
            if y.shape != (len(groups),) or not np.isin(y, [0, 1]).all():
                raise ValueError(f"{rid}: invalid binary measurement")
            max_gap = 0
            counts = {}
            for half in [1, 2]:
                effect = y[(halves == half) & (groups == 1)].mean() - y[(halves == half) & (groups == 0)].mean()
                if not np.isclose(effect, result[f"d{half}"], rtol=0, atol=1e-12):
                    raise ValueError(f"{rid}: saved effect disagrees with measurements")
                for group in [0, 1]:
                    tally = {model: int(((groups == group) & (halves == half) & (models == model)).sum())
                             for model in cfg.rotation_pool}
                    max_gap = max(max_gap, max(tally.values()) - min(tally.values()))
                    counts[f"group{group}_half{half}"] = tally
            cell_audit[rid][cid] = {"model_counts": counts, "max_within_cell_model_count_gap": max_gap}
            if max_gap > 1:
                altered.append(cid)
        row = {"run_id": rid, "condition": cfg.condition, "n_proposed": len(proposed), "n_measured": len(measured),
               "n_validated": selected["n_validated"], "n_suggestive": selected["n_suggestive"],
               "n_uncorrected": selected["n_uncorrected"],
               "n_skipped": len(proposed) - len(measured), "assigned_model_failures_logged": failures,
               "fallback_judgments_logged": fallback, "candidates_with_actual_assignment_imbalance": len(altered),
               "partition_and_discovery_checks": "pass", "binary_and_effect_checks": "pass",
               "selection_sha256": sha256(root / "04_selected.json")}
        rows.append(row)
    with (out / "measurement_audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out / "actual_model_balance.json").write_text(json.dumps(cell_audit, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
