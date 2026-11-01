"""Check that compact exhibit generation preserves a novel placebo survivor."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.validation import sha256


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "optional PDF dependency unavailable")
class ExhibitTests(unittest.TestCase):
    def test_novel_placebo_survivor_is_displayed_and_other_real_features_remain_in_appendix(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            anchors, matches = base / "anchors", base / "matches"
            anchors.mkdir();matches.mkdir()
            jobs, novel_origin, novel_groups = [], {}, []
            for rid in ["ARCHIVE", "R01", "E_DEFAULTS", "E_OPENAI", "P01", "P02"]:
                root = base / rid / rid
                root.mkdir(parents=True)
                cid = f"candidate_{rid}"
                candidate = {"candidate_id": cid, "feature_name": f"Feature {rid}",
                             "definition": "Synthetic test construct", "classification_question": "Is it present?"}
                bank_path = root / "02_consolidated.json"
                bank_path.write_text(json.dumps({"candidates": [candidate]}))
                tier = "not_validated" if rid == "P02" else "confirmed"
                (root / "04_selected.json").write_text(json.dumps({"results": [
                    {"candidate_id": cid, "tier": tier, "mean_effect": .2, "perm_p": .001}]}))
                for name in ["00_config.json", "00_partition.json", "03_measured.json"]:
                    (root / name).write_text("{}")
                if rid == "ARCHIVE":
                    with (anchors / "runs.csv").open("w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=["run_id", "status", "artifact_path"])
                        w.writeheader();w.writerow({"run_id": rid, "status": "complete", "artifact_path": str(root)})
                    member = {"family_id": "F1", "family_label": "Reference construct", "run_id": rid,
                              "candidate_id": cid, "relation": "anchor", "mapping_status": "draft"}
                    with (anchors / "family_memberships.csv").open("w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=list(member));w.writeheader();w.writerow(member)
                    continue
                cfg = base / f"{rid}.config.json"
                cfg.write_text(json.dumps({"output_dir": str(base / rid), "condition": "placebo" if rid.startswith("P") else "real"}))
                jobs.append({"run_id": rid, "config_path": str(cfg)})
                fid = None if rid in ["E_DEFAULTS", "P01", "P02"] else "F1"
                if fid is None:
                    nid = f"N{len(novel_origin)+1}"
                    novel_origin[nid] = {"run_id": rid, "candidate_id": cid}
                    novel_groups.append({"members": [nid], "family_label": f"New construct {rid}"})
                (matches / f"{rid}.json").write_text(json.dumps({"candidate_bank_sha256": sha256(bank_path),
                    "matches": [{"candidate_id": cid, "family_id": fid, "family_label": "Reference construct",
                                 "relation": "equivalent"}]}))
            (matches / "novel_groups.json").write_text(json.dumps({"groups": novel_groups, "origin": novel_origin}))
            batch = base / "batch.json"
            batch.write_text(json.dumps({"planned_jobs": jobs}))
            script = Path(__file__).resolve().parents[1] / "scripts/build_validation_results.py"
            build = runpy.run_path(str(script))["build"]
            output = base / "exhibits"
            with contextlib.redirect_stdout(io.StringIO()):
                build(anchors, batch, matches, output)
            with (output / "table_4_crosswalk.csv").open() as f:
                rows = list(csv.DictReader(f))
            by_name = {r["substantive_family"]: r for r in rows}
            self.assertEqual(by_name["New construct P01"]["P01"], "✓")
            self.assertEqual(by_name["New construct P01"]["ARCHIVE"], "–")
            self.assertEqual(by_name["Additional validated families (appendix)"]["E_DEFAULTS"], "1")
            self.assertNotIn("New construct E_DEFAULTS", by_name)
            with (output / "appendix_full_crosswalk.csv").open() as f:
                appendix = list(csv.DictReader(f))
            self.assertTrue(any(r["substantive_family"] == "New construct E_DEFAULTS" for r in appendix))
            self.assertGreater((output / "table_4_crosswalk.pdf").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
