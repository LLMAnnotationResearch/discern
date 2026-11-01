"""Meaningful offline checks for Section 4 calibration and saved-bank alignment.

Run directly with Python (unittest); also collected by pytest when installed.
"""
import csv
from dataclasses import asdict
import itertools
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern import core
from discern.config import RunConfig
from discern.select import run_selection
from discern.stability import crosswalk, presence_table
from discern.baselines import test_scores as assess_baseline_scores, lda_scores
from discern.validation import (evaluate, load_bank, main, null_scores,
                                summarize_null, wilson_interval, _simulation_rep)


class ValidationTests(unittest.TestCase):
    def test_composite_null_matches_exhaustive_tiny_design(self):
        # All 6 balanced labelings in each four-unit half: 36 joint permutations.
        # A perfect positive observed feature has only two equally extreme joint
        # arrangements (both halves perfectly positive or perfectly negative).
        arrangements = []
        for pair in itertools.combinations(range(4), 2):
            a = np.zeros(4, dtype=int)
            a[list(pair)] = 1
            arrangements.append(a)
        draws = [part for joint in itertools.product(arrangements, repeat=2) for part in joint]

        class ExhaustiveRng:
            def __init__(self):
                self.draws = iter(draws)

            def permutation(self, array):
                return next(self.draws).copy()

        labels = np.array([1, 1, 0, 0] * 2)
        split = np.repeat([1, 2], 4)
        with patch.object(core.np.random, "default_rng", return_value=ExhaustiveRng()):
            d1, d2, p = core.stage5(labels, split, {"signal": labels}, B=36)["signal"]
        self.assertEqual((d1, d2), (1.0, 1.0))
        self.assertAlmostEqual(p, 3 / 37)  # two extreme permutations + plus-one correction

    def test_zero_or_conflicting_half_effects_cannot_validate(self):
        labels = np.array([1, 1, 0, 0] * 2)
        split = np.repeat([1, 2], 4)
        scores = {"conflict": np.concatenate([labels[:4], 1 - labels[4:]]),
                  "zero": np.zeros(8, dtype=int)}
        result = core.stage5(labels, split, scores, B=50)
        self.assertEqual(result["conflict"][2], 1)
        self.assertEqual(result["zero"][2], 1)

    def test_report_uses_entire_q10_rejection_set(self):
        cfg = RunConfig("fake", "text", "group", permutations=1)
        labels, split = np.array([1, 0] * 4), np.repeat([1, 2], 4)
        # Three tests: .001 passes .05, .05 passes only .10, .9 neither.
        with patch("discern.select.stage5", return_value={
            "a": (.1, .1, .001), "b": (.1, .1, .05), "c": (.1, .1, .9)}):
            counts = evaluate(labels, split, {k: labels for k in "abc"}, cfg)
        self.assertEqual(counts["q05"], 1)
        self.assertEqual(counts["q10"], 2)
        self.assertEqual(counts["n_tested"], 3)
        self.assertGreaterEqual(counts["permutations"], 60)

    def test_null_summary_is_family_event_rate_with_nonzero_uncertainty(self):
        rows = [{"q05": 0, "q10": 0, "uncorrected_only": 0}] * 20
        summary = summarize_null(rows)
        interval = summary["q05"]["any_selection_wilson_95"]
        self.assertEqual(summary["q05"]["any_selection_rate"], 0)
        self.assertGreater(interval[1], .15)
        rows = [{"q05": 3, "q10": 4, "uncorrected_only": 1},
                {"q05": 0, "q10": 0, "uncorrected_only": 0}]
        self.assertEqual(summarize_null(rows)["q05"]["any_selection_rate"], .5)
        self.assertEqual(summarize_null(rows)["q05"]["mean_selected"], 1.5)
        with self.assertRaises(ValueError):
            wilson_interval(0, 0)

    def test_generation_and_selection_are_reproducible(self):
        for scenario in ("independent", "rare", "positive_blocks"):
            a = null_scores(np.random.default_rng(5), 40, 7, scenario)
            b = null_scores(np.random.default_rng(5), 40, 7, scenario)
            for key in a:
                np.testing.assert_array_equal(a[key], b[key])
                self.assertTrue(np.isin(a[key], [0, 1]).all())
        task = (0, 6, 10, 2, "positive_blocks", 10)
        self.assertEqual(_simulation_rep(task), _simulation_rep(task))

    def make_bank(self, root):
        cfg = RunConfig("unavailable.csv", "text", "group", n_per_group=4,
                        permutations=100, rotation_pool=["gpt-4o-mini", "claude-haiku"])
        labels = np.repeat([1, 0], 4)
        split = np.array([1, 1, 2, 2] * 2)
        candidates = [{"candidate_id": "signal", "feature_name": "signal", "classification_question": "signal?"},
                      {"candidate_id": "skipped", "feature_name": "skipped", "classification_question": "skip?"}]
        measured = {"signal": {"y": labels.tolist(), "model_assignment": cfg.rotation_pool * 4}}
        data = SimpleNamespace(measurement_labels=lambda: labels, m_split=split)
        selected = run_selection(cfg, data, measured, candidates)
        partition = {"measurement_uids": [str(i) for i in range(8)],
                     "measurement_split": split.tolist(), "dataset_fingerprint": "fake",
                     "group_sizes": {f"split{h}_by_active_label": {"0": 2, "1": 2} for h in [1, 2]}}
        artifacts = {"00_config.json": {"config": asdict(cfg)}, "00_partition.json": partition,
                     "02_consolidated.json": {"candidates": candidates}, "03_measured.json": measured,
                     "04_selected.json": selected, "00_runspec.json": {"model_versions": []}}
        for name, obj in artifacts.items():
            (root / name).write_text(json.dumps(obj), encoding="utf-8")
        return artifacts

    def test_bank_requires_explicit_label_provenance_and_detects_misalignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = self.make_bank(root)
            with self.assertRaisesRegex(ValueError, "either"):
                load_bank(root)
            *_, meta = load_bank(root, reconstruct=True)
            self.assertEqual(meta["skipped_candidate_ids"], ["skipped"])
            self.assertFalse(meta["labels"]["independently_verified"])
            self.assertTrue(meta["all_saved_half_effects_reproduced"])
            scores = artifacts["03_measured.json"]
            scores["signal"]["y"] = scores["signal"]["y"][::-1]
            (root / "03_measured.json").write_text(json.dumps(scores))
            with self.assertRaisesRegex(ValueError, "effect mismatch"):
                load_bank(root, reconstruct=True)

    def test_explicit_uid_table_is_aligned_by_uid_not_row_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_bank(root)
            labels_path = root / "labels.csv"
            with labels_path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["uid", "group"])
                writer.writerows((str(i), int(i < 4)) for i in reversed(range(8)))
            _, labels, *_, meta = load_bank(root, labels_path=labels_path)
            np.testing.assert_array_equal(labels, np.repeat([1, 0], 4))
            self.assertEqual(meta["labels"]["kind"], "explicit_uid_table")
            with labels_path.open("a") as stream:
                stream.write("0,1\n")
            with self.assertRaisesRegex(ValueError, "duplicate UID"):
                load_bank(root, labels_path=labels_path)

    def test_bank_rejects_partial_or_nonbinary_measurements(self):
        for bad_scores in ([1, 0], [1, 1, 1, 1, 0, 0, 0, .5]):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                artifacts = self.make_bank(root)
                artifacts["03_measured.json"]["signal"]["y"] = bad_scores
                (root / "03_measured.json").write_text(json.dumps(artifacts["03_measured.json"]))
                with self.assertRaisesRegex(ValueError, "score vector"):
                    load_bank(root, reconstruct=True)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                main(["simulate", "--scenario", "rare", "--reps", "1", "--out", tmp])

    def test_crosswalk_distinguishes_missing_mapping_unrun_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_bank(root)
            runs = [{"run_id": "A", "status": "complete", "artifact_path": str(root)},
                    {"run_id": "B", "status": "planned"}]
            links = [{"family_id": "F1", "family_label": "Substantive construct", "run_id": "A",
                      "candidate_id": "signal", "relation": "anchor", "mapping_status": "draft"},
                     {"family_id": "F2", "family_label": "Unmeasurable construct", "run_id": "A",
                      "candidate_id": "skipped", "relation": "narrower", "mapping_status": "draft"}]
            result = crosswalk(runs, links)
            self.assertIn("+100.00pp", result[0]["A"])
            self.assertEqual(result[0]["B"], "NOT RUN")
            self.assertIn("SKIP", result[1]["A"])
            self.assertIn("DRAFT", result[0]["A"])

    def test_crosswalk_absence_requires_complete_adjudicated_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_bank(root)
            runs = [{"run_id": "A", "status": "complete", "artifact_path": str(root)},
                    {"run_id": "B", "status": "complete", "artifact_path": str(root)}]
            links = [dict(family_id="F1", family_label="First", run_id="A", candidate_id="signal",
                          relation="anchor", mapping_status="adjudicated"),
                     dict(family_id="F1", family_label="First", run_id="A", candidate_id="skipped",
                          relation="related", mapping_status="adjudicated"),
                     dict(family_id="F2", family_label="Second", run_id="B", candidate_id="signal",
                          relation="anchor", mapping_status="draft")]
            result = crosswalk(runs, links)
            self.assertEqual(result[0]["B"], "UNRESOLVED")
            self.assertEqual(result[1]["A"], "ABSENT")
            self.assertIn(" | ", result[0]["A"])  # separate member estimates, not an invented mean

    def test_crosswalk_rejects_unknown_feature_and_duplicate_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_bank(root)
            runs = [{"run_id": "A", "status": "complete", "artifact_path": str(root)}]
            link = dict(family_id="F1", family_label="First", run_id="A", candidate_id="unknown",
                        relation="anchor", mapping_status="draft")
            with self.assertRaisesRegex(ValueError, "unknown candidate"):
                crosswalk(runs, [link])
            link["candidate_id"] = "signal"
            with self.assertRaisesRegex(ValueError, "duplicate membership"):
                crosswalk(runs, [link, link])

    def test_combined_table_shows_proposals_then_quiet_placebo_without_inventing_pending_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            real, placebo = Path(tmp) / "real", Path(tmp) / "placebo"
            for root, tier in [(real, "confirmed"), (placebo, "not_validated")]:
                root.mkdir()
                artifacts = self.make_bank(root)
                artifacts["04_selected.json"]["results"][0]["tier"] = tier
                (root / "04_selected.json").write_text(json.dumps(artifacts["04_selected.json"]))
            runs = [{"run_id": "R", "status": "complete", "artifact_path": str(real), "condition": "real"},
                    {"run_id": "P", "status": "complete", "artifact_path": str(placebo), "condition": "placebo"},
                    {"run_id": "P_NEXT", "status": "planned", "condition": "placebo"}]
            links = [dict(family_id="F1", family_label="Substantive feature", run_id="R", candidate_id="signal",
                          relation="anchor", mapping_status="draft")]
            rows = {row["family_id"]: row for row in presence_table(runs, links)}
            self.assertEqual(rows["n_proposed"]["P"], 2)
            self.assertEqual(rows["n_measured"]["P"], 1)
            self.assertEqual(rows["n_validated"]["R"], 1)
            self.assertEqual(rows["n_validated"]["P"], 0)
            self.assertEqual(rows["F1"]["R"], "✓")
            self.assertEqual(rows["F1"]["P"], "–")
            self.assertEqual(rows["F1"]["P_NEXT"], "NOT RUN")
            self.assertEqual(rows["n_validated"]["P_NEXT"], "NOT RUN")
            proposals = {row["family_id"]: row for row in presence_table(runs, links, stage="proposed")}
            self.assertEqual(proposals["F1"]["P"], "?")  # no candidate-to-family matches supplied

    def test_placebo_survivors_require_rows_and_are_never_forced_to_dashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = self.make_bank(root)
            artifacts["04_selected.json"]["results"][0]["tier"] = "confirmed"
            (root / "04_selected.json").write_text(json.dumps(artifacts["04_selected.json"]))
            runs = [{"run_id": "P", "status": "complete", "artifact_path": str(root), "condition": "placebo"}]
            with self.assertRaisesRegex(ValueError, "including placebo-only"):
                presence_table(runs, [])
            links = [dict(family_id="P_ONLY", family_label="Unexpected placebo feature", run_id="P",
                          candidate_id="signal", relation="anchor", mapping_status="draft")]
            rows = {row["family_id"]: row for row in presence_table(runs, links)}
            self.assertEqual(rows["P_ONLY"]["P"], "✓")
            self.assertEqual(rows["n_validated"]["P"], 1)

    def test_combined_table_counts_candidates_separately_from_semantic_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = self.make_bank(root)
            result = artifacts["04_selected.json"]["results"][0]
            result["tier"] = "confirmed"
            artifacts["04_selected.json"]["results"].append({**result, "candidate_id": "skipped"})
            (root / "04_selected.json").write_text(json.dumps(artifacts["04_selected.json"]))
            runs = [{"run_id": "R", "status": "complete", "artifact_path": str(root)}]
            links = [dict(family_id="F1", family_label="Shared meaning", run_id="R", candidate_id=cid,
                          relation="anchor" if cid == "signal" else "narrower", mapping_status="draft")
                     for cid in ["signal", "skipped"]]
            rows = {row["family_id"]: row for row in presence_table(runs, links)}
            self.assertEqual(rows["n_validated"]["R"], 2)
            self.assertEqual(rows["n_families"]["R"], 1)
            self.assertEqual(rows["F1"]["R"], "✓")

    def test_baselines_keep_native_scales_and_complete_test_family(self):
        groups = np.array([1, 1, 0, 0] * 2)
        halves = np.repeat([1, 2], 4)
        import pandas as pd
        scores = pd.DataFrame({"sentiment": 2.0 * groups - 1, "constant": np.zeros(8)})
        rows, meta = assess_baseline_scores(scores, groups, halves, 50)
        self.assertEqual(rows[0]["mean_half_difference_native"], 2.0)
        self.assertEqual(rows[1]["perm_p"], 1)
        self.assertIsNone(rows[1]["standardized_overall_difference"])
        self.assertEqual(meta["multiplicity_family"], ["sentiment", "constant"])
        scores.loc[0, "sentiment"] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            assess_baseline_scores(scores, groups, halves, 50)

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "optional validation dependencies not installed")
    def test_lda_never_learns_evaluation_vocabulary_or_scores_empty_documents_as_evidence(self):
        training = (["apples market fruit farming orchard", "oranges fruit harvest market"] * 15 +
                    ["metal factory machinery production hardware", "hardware equipment industrial factory"] * 15)
        evaluation = ["apples oranges fruit market", "evaluationuniquetoken"]
        scores, meta, (vectorizer, _) = lda_scores(training, evaluation, [2], 21)
        self.assertNotIn("evaluationuniquetoken", vectorizer.vocabulary_)
        self.assertTrue(np.isfinite(scores.iloc[0]).all())
        self.assertTrue(scores.iloc[1].isna().all())
        self.assertEqual(meta["evaluation_zero_vocabulary_rows"], 1)


if __name__ == "__main__":
    unittest.main()
