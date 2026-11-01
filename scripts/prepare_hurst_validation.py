"""Construct portable Hurst contrasts and verify them against saved run artifacts.

The supplied survey export has no respondent ID. Archived run IDs match the
physical spreadsheet row (zero-based data-row index + 2). This assumption must
reproduce reservation UID order, halves, and every recorded discovery group.
Source files are read only; all derived files stay under a new local directory.
"""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.config import RunConfig
from discern.data import Dataset
from discern.validation import load_bank, sha256


def prepare(source, runs_root, out):
    source, runs_root, out = Path(source).resolve(), Path(runs_root).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = pd.read_csv(source)
    required = {"sex", "treatment_structure", "treatment"}
    if not required.issubset(raw):
        raise ValueError(f"missing columns: {required - set(raw)}")
    columns = {}
    for arm in ("flat", "tall"):
        matches = [c for c in raw if c.startswith("What comes to mind when you see us") and f'as "{arm}"' in c]
        if len(matches) != 1:
            raise ValueError(f"ambiguous {arm} response column")
        columns[arm] = matches[0]
    raw["id"] = np.arange(len(raw)) + 2
    mapping = {"Flat": 1, "Tall": 2, "Control": 0}
    if not raw["treatment_structure"].map(mapping).eq(raw["treatment"]).all():
        raise ValueError("treatment code and structure label disagree")
    manifest = {
        "source": str(source), "source_sha256": sha256(source), "raw_rows": len(raw),
        "script_sha256": sha256(__file__), "raw_columns": list(raw.columns.drop("id")),
        "uid_rule": "zero-based raw CSV data-row index + 2; matches archived spreadsheet row IDs",
        "respondent_id_caveat": "The export has no original respondent ID; preserve this exact source order/hash.",
        "primary_contrast": "run3_tall_sex",
        "limitations": ["Mechanism scales, founder-gender blocks and attention-check fields are absent.",
                        "Raw export has 8692 rows; published attention-check sample has 8498. Do not assert identical inclusion rules.",
                        "Current construction reproduces archived Discern inclusion, not all published-paper exclusions."],
        "contrasts": [],
    }
    for name, arm in [("run3_tall_sex", "Tall"), ("run2_flat_sex", "Flat"), ("run1_flat_vs_tall", None)]:
        run_dir = runs_root / name / "real_r0"
        saved = json.loads((run_dir / "00_config.json").read_text())["config"]
        partition = json.loads((run_dir / "00_partition.json").read_text())
        discovery = json.loads((run_dir / "01_discovery.json").read_text())
        if arm:
            subset = raw[raw.treatment_structure.eq(arm) & raw.sex.isin(["Female", "Male"])].copy()
            subset["text"] = subset[columns[arm.lower()]]
            subset["group"] = subset.sex.eq("Female").astype(int)
        else:
            subset = raw[raw.treatment_structure.isin(["Flat", "Tall"])].copy()
            subset["text"] = subset[columns["flat"]].where(subset.treatment_structure.eq("Flat"), subset[columns["tall"]])
            subset["group"] = subset.treatment_structure.eq("Flat").astype(int)
        before_text_filter = len(subset)
        subset = subset[subset.text.notna() & subset.text.fillna("").str.strip().ne("")].copy()
        csv_path = out / f"{name}.csv"
        subset[["id", "text", "group"]].to_csv(csv_path, index=False, encoding="utf-8")
        labels_path = out / f"{name}_uid_groups.csv"
        subset[["id", "group"]].rename(columns={"id": "uid"}).to_csv(labels_path, index=False)
        cfg = RunConfig(**{**saved, "dataset": str(csv_path), "base_dir": str(out),
                           "output_dir": str(out.parent.parent / "02_placebo" / "live_runs" / name)})
        data = Dataset(cfg)
        if data.m_uid != partition["measurement_uids"] or data.m_split.tolist() != partition["measurement_split"]:
            raise ValueError(f"raw-source reconstruction does not reproduce saved partition: {name}")
        labels = dict(zip(subset.id.astype(str), subset.group))
        checked = 0
        for call in discovery["calls"]:
            for slot in ("A", "B"):
                for uid in call[f"slot{slot}_uids"]:
                    if labels.get(str(uid)) != call[f"slot{slot}_canonical_group"]:
                        raise ValueError(f"raw-source label disagrees with saved discovery: {name}, {uid}")
                    if str(uid) in data.meas_uids:
                        raise ValueError("discovery/measurement overlap")
                    checked += 1
        *_, bank_meta = load_bank(run_dir, labels_path=labels_path)
        # Explicit partition shared by conventional methods and Discern.
        with (out / f"{name}_partition.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["uid", "group", "role", "measurement_half"])
            half_by_uid = dict(zip(data.m_uid, data.m_split))
            for uid, group in labels.items():
                writer.writerow([uid, group, "evaluation" if uid in half_by_uid else "discovery",
                                 int(half_by_uid[uid]) if uid in half_by_uid else ""])
        (out / f"{name}.config.json").write_text(json.dumps(asdict(cfg), indent=2) + "\n")
        normalized = subset.text.str.strip().str.casefold()
        manifest["contrasts"].append({
            "run": name, "rows": len(subset), "dropped_empty_text": before_text_filter - len(subset),
            "counts_by_group": {str(k): int(v) for k, v in subset.group.value_counts().items()},
            "measurement_units": len(data.m_uid), "discovery_units": len(data.pool),
            "median_words": float(subset.text.str.split().str.len().median()),
            "duplicate_normalized_text_rows_after_first": int(normalized.duplicated().sum()),
            "derived_csv_sha256": sha256(csv_path), "labels_sha256": sha256(labels_path),
            "partition_sha256": sha256(out / f"{name}_partition.csv"),
            "source_discovery_group_checks": checked,
            "exact_saved_measurement_uid_order": True, "exact_saved_halves": True,
            "all_saved_half_effects_reproduced": bank_meta["all_saved_half_effects_reproduced"],
        })
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["contrasts"], indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    prepare(args.source, args.runs_root, args.out)
