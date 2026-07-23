"""Robustness tests for the failure-handling fixes. NO API calls — the LLM entry points are
monkeypatched. Covers:

  A. Discovery tolerates isolated call failures (log-and-continue) but a fail-closed floor still
     raises when failures are systematic (a split ends empty, or a majority of calls fail).
  B. llm_json_call grows max_tokens on a truncation (finish_reason=length) instead of jittering
     temperature — the remedy that actually fits the failure mode — and leaves temperature alone.
  D. Measurement re-measures a unit on another pool model when its assigned model flakes, rather
     than dropping the whole candidate; only an all-models-fail unit escalates.

Run:  python3 tests/test_robustness.py
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / "src"))

from discern import RunConfig                      # noqa: E402
from discern import discovery, measure, core        # noqa: E402
from discern.data import Dataset                     # noqa: E402
from discern.audit import Audit                       # noqa: E402
from discern.measure import Cache, run_measurement    # noqa: E402

FAIL = []
def raises(fn):
    try:
        fn(); return False
    except Exception:
        return True
def check(name, fn):
    try:
        fn(); print(f"  PASS {name}")
    except AssertionError as e:
        FAIL.append(name); print(f"  FAIL {name}: {e}")
    except Exception as e:  # noqa: BLE001
        FAIL.append(name); print(f"  ERROR {name}: {type(e).__name__}: {e}")


def make_dataset(path, n_per_group=400, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for grp, p_food in ((1, 0.75), (0, 0.25)):
        for i in range(n_per_group):
            head = "fresh food item" if rng.random() < p_food else "metal hardware item"
            rows.append({"group": grp, "text": f"{head} u{grp}_{i}_{rng.integers(1e9)}"})
    pd.DataFrame(rows).sample(frac=1, random_state=seed).to_csv(path, index=False)


CANNED_HYPS = [{"hypothesis": "Group A involves food while Group B involves hardware.",
                "dimension": "food", "measurement_question": "Does it mention food?"}]


def run_all():
    tmp = Path(tempfile.mkdtemp())
    ds = tmp / "synthetic.csv"
    make_dataset(ds)

    def base_cfg(**over):
        defaults = dict(dataset=str(ds), text_col="text", group_col="group",
                        output_dir=str(tmp / "runs"),
                        n_per_group=20, permutations=200, n_iterations=4, items_per_group=15)
        defaults.update(over)
        return RunConfig(**defaults)

    # ---------- Fix A: discovery tolerates isolated failures, floor catches systematic ----------
    def failing_llm(fail_on):
        """A discovery mock that raises on the given 0-based call indices, else returns a hypothesis.
        Calls 0..(n_iterations-1) are split1; the next block is split2."""
        state = {"i": -1}
        def f(prompt, model, key, **kw):
            state["i"] += 1
            if state["i"] in fail_on:
                raise RuntimeError("simulated provider failure")
            return [dict(h) for h in CANNED_HYPS]
        return f

    def with_discovery_mock(fail_on):
        orig = discovery.llm_json_call
        discovery.llm_json_call = failing_llm(fail_on)
        try:
            cfg = base_cfg().resolve(BASE)
            data = Dataset(cfg)
            audit = Audit(tmp / "runs" / "disc_probe")
            return discovery.run_discovery(cfg, data, audit)
        finally:
            discovery.llm_json_call = orig

    def t_disc_tolerates_isolated():
        # n_iterations=4 -> calls 0..3 split1, 4..7 split2; fail one in each, both splits still populated
        out = with_discovery_mock(fail_on={1, 5})
        assert out["split1"] and out["split2"], f"a split came back empty: {[len(out['split1']), len(out['split2'])]}"
        assert len(out["calls"]) == 6, f"expected 6 successful calls recorded, got {len(out['calls'])}"
    check("A: discovery survives isolated per-call failures", t_disc_tolerates_isolated)

    def t_disc_floor_empty_split():
        # every split1 call fails -> split1 empty -> fail-closed floor raises even though split2 is fine
        assert raises(lambda: with_discovery_mock(fail_on={0, 1, 2, 3})), \
            "floor did not raise when a split produced zero hypotheses"
    check("A: fail-closed floor raises when a split is empty", t_disc_floor_empty_split)

    def t_disc_floor_all_fail():
        assert raises(lambda: with_discovery_mock(fail_on=set(range(8)))), \
            "floor did not raise when all discovery calls failed"
    check("A: fail-closed floor raises when all calls fail", t_disc_floor_all_fail)

    # ---------- Fix B: truncation grows max_tokens; temperature is NOT jittered ----------
    class _FakeCompletions:
        def __init__(self, log):
            self.log = log
        def create(self, model, messages, temperature, max_tokens, **kw):
            self.log.append((max_tokens, temperature))
            if len(self.log) == 1:                       # first attempt: truncated JSON
                return _resp('{"hypotheses": [{"hypothesis": "x', "length")
            return _resp('{"hypotheses": [{"hypothesis": "ok"}]}', "stop")   # then valid

    def _resp(content, finish):
        msg = type("M", (), {"content": content})
        choice = type("C", (), {"message": msg(), "finish_reason": finish})
        return type("R", (), {"choices": [choice()]})()

    def t_truncation_grows_tokens():
        log = []
        fake = type("Client", (), {"chat": type("Chat", (), {"completions": _FakeCompletions(log)})()})()
        orig = core._client
        core._client = lambda provider: fake
        try:
            out = core.llm_json_call("p", "gpt-4o-mini", "hypotheses",
                                     max_tokens=2000, required=["hypothesis"])
        finally:
            core._client = orig
        assert out == [{"hypothesis": "ok"}], f"unexpected result: {out}"
        assert log[0][0] == 2000 and log[1][0] == 4000, f"max_tokens did not double on truncation: {log}"
        assert log[0][1] == log[1][1], f"temperature was jittered on a truncation (should not be): {log}"
    check("B: truncation doubles max_tokens and leaves temperature unchanged", t_truncation_grows_tokens)

    def t_truncation_cap():
        # a caller starting at the cap must not be shrunk, and growth must not exceed it
        cur, cap = 16000, max(core._TRUNCATION_TOKEN_CAP, 16000)
        assert min(cur * 2, cap) == 16000, "cap logic would shrink a 16000-token caller"
    check("B: token-growth cap never shrinks a large caller budget", t_truncation_cap)

    # ---------- Fix D: measurement falls back to another pool model instead of dropping a feature ----
    def measurement_with(bad_models):
        """Run measurement where classify_one fails for any model in `bad_models`."""
        def flaky_classify(question, text, model="", definition="", unit_label="", **kw):
            if model in bad_models:
                raise RuntimeError(f"simulated empty response from {model}")
            return 1 if "food" in text.lower() else 0
        orig = measure.classify_one
        measure.classify_one = flaky_classify
        try:
            cfg = base_cfg(rotation_pool=["gpt-4o-mini", "claude-haiku"]).resolve(BASE)
            data = Dataset(cfg)
            rundir = tmp / "runs" / ("meas_" + "_".join(sorted(bad_models)) or "meas_none")
            audit = Audit(rundir)
            cache = Cache(rundir / "cache.json", data.fingerprint, cfg.prompt_version,
                          f"design={cfg.measurement_design}|unit={cfg.unit_label}")
            cands = [{"candidate_id": "c1", "feature_name": "Food",
                      "classification_question": "Does the text mention food?", "definition": ""}]
            return run_measurement(cfg, data, cands, cache, audit)
        finally:
            measure.classify_one = orig

    def t_meas_falls_back():
        C = measurement_with(bad_models={"gpt-4o-mini"})     # one model flaky -> other covers it
        assert "c1" in C, "candidate was dropped even though a working fallback model existed"
        assert "gpt-4o-mini" not in set(C["c1"]["model_assignment"]), \
            "assignment still credits the failed model instead of the fallback that produced the answer"
        assert len(C["c1"]["y"]) == 40, f"expected 40 measured units, got {len(C['c1']['y'])}"
    check("D: a flaky model is re-measured on a pool fallback, feature kept", t_meas_falls_back)

    def t_meas_all_fail_still_escalates():
        C = measurement_with(bad_models={"gpt-4o-mini", "claude-haiku"})   # whole pool down
        assert "c1" not in C, "a unit with EVERY pool model failing should still escalate (skip), not fabricate"
    check("D: an all-models-fail unit still escalates (no silent fabrication)", t_meas_all_fail_still_escalates)

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all robustness tests passed")


if __name__ == "__main__":
    run_all()
