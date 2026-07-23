"""Offline end-to-end tests for the discern package. NO API calls: discovery/consolidation LLM
calls and the per-unit classifier are monkeypatched with deterministic mocks. A real signal (a
'food' token correlated with the focal group) is planted alongside a pure-null feature; the test
asserts the pipeline validates the real one, rejects the null, stays quiet under placebo, keeps
discovery disjoint from measurement, and writes the audit trail incrementally.

Run:  python3 tests/test_pipeline.py
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / "src"))

from discern import RunConfig, run_pipeline           # noqa: E402
from discern import config as cfgmod                  # noqa: E402
from discern import discovery, consolidate, measure, themes, core  # noqa: E402
from discern.data import Dataset                       # noqa: E402
from discern.prompts import p1_prompt                  # noqa: E402

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


# ---------- synthetic dataset with a planted signal ----------
def make_dataset(path, n_per_group=700, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for grp, p_food in ((1, 0.75), (0, 0.25)):          # focal firms carry 'food' more often
        for i in range(n_per_group):
            is_food = rng.random() < p_food
            head = "fresh food item" if is_food else "metal hardware item"
            rows.append({"group": grp,
                         "text": f"{head} u{grp}_{i}_{rng.integers(1e9)}"})
    pd.DataFrame(rows).sample(frac=1, random_state=seed).to_csv(path, index=False)


# ---------- deterministic mocks ----------
CANNED_HYPS = [{"hypothesis": "Group A involves food while Group B involves hardware.",
                "dimension": "food", "measurement_question": "Does it mention food?"}] * 6
CANNED_FEATS = [
    {"feature_name": "Food focus", "definition": "the item involves food",
     "classification_question": "Does the text mention food?",
     "claimed_direction": "A_higher", "parent_theme": None,
     "n_supporting_hypotheses": 6, "direction_conflict": False},
    {"feature_name": "Random null token", "definition": "an unrelated concept",
     "classification_question": "Does the text mention an unrelated concept?",
     "claimed_direction": "A_higher", "parent_theme": None,
     "n_supporting_hypotheses": 1, "direction_conflict": False},
]
def mock_llm_json_call(prompt, model, key, **kw):
    if key == "hypotheses":
        return [dict(h) for h in CANNED_HYPS]
    return [dict(f) for f in CANNED_FEATS]   # "features" (P2 per split + P3 unify)

def mock_classify_one(question, desc, model="gpt-4o-mini", definition="",
                      unit_label="item", max_retries=4):
    if "food" in question.lower():
        return 1 if "food" in desc.lower() else 0                     # real signal
    return int(hashlib.sha1(desc.encode()).digest()[0] % 2)          # null: independent of group

def install_mocks():
    discovery.llm_json_call = mock_llm_json_call
    consolidate.llm_json_call = mock_llm_json_call
    measure.classify_one = mock_classify_one
    core.probe_model_version = lambda m: {"model": m, "resolved": "mock", "pinned": True}


# ---------- tests ----------
def run_all():
    tmp = Path(tempfile.mkdtemp())
    ds = tmp / "synthetic.csv"
    make_dataset(ds)
    install_mocks()

    def base_cfg(**over):
        defaults = dict(dataset=str(ds), text_col="text", group_col="group",
                        output_dir=str(tmp / "runs"),
                        n_per_group=100, permutations=500, n_iterations=4, items_per_group=15)
        defaults.update(over)
        return RunConfig(**defaults)

    # --- data partition guarantees ---
    def t_partition():
        d = Dataset(base_cfg().resolve(BASE))
        assert len(d.m_uid) == 200, f"expected 200 measurement units, got {len(d.m_uid)}"
        assert len(set(d.m_uid)) == 200, "measurement uids not unique"
        assert not (set(d.m_uid) & set(d.pool["uid"])), "measurement leaks into discovery pool"
        assert d.m_group.sum() == 100, "measurement not 100/group stratified"
        assert d.group_min_sizes()["pool_focal"] > 0
    check("data: stratified 100/group, disjoint pool, unique stable uids", t_partition)

    def t_min_group_guard():
        try:
            Dataset(base_cfg(n_per_group=99999).resolve(BASE))
            assert False, "should have raised on too-large reservation"
        except ValueError:
            pass
    check("data: raises when reservation exceeds group size", t_min_group_guard)

    # --- real end-to-end run ---
    real = run_pipeline(base_cfg(condition="real"), BASE, resume=False, log=lambda *a: None)
    def t_real():
        by = {r["feature_name"]: r for r in real["results"]}
        assert by["Food focus"]["validated"], f"planted real feature not validated: {by['Food focus']}"
        assert by["Food focus"]["mean_effect"] > 0.2, "real effect should be large positive"
        assert not by["Random null token"]["validated"], "null feature should NOT validate"
        assert real["n_validated"] == 1, f"expected exactly 1 validated, got {real['n_validated']}"
    check("real run: planted signal validates, null rejected", t_real)

    # --- placebo run: the null must be quiet ---
    placebo = run_pipeline(base_cfg(condition="placebo"), BASE, resume=False, log=lambda *a: None)
    def t_placebo():
        by = {r["feature_name"]: r for r in placebo["results"]}
        # the KEY property: the planted REAL signal is destroyed under the null relabeling
        assert not by["Food focus"]["validated"], "planted signal must NOT validate under placebo"
        # a SINGLE placebo run may still show a rare FDR-permitted false positive on a pure-noise
        # feature; the calibration claim is estimated across many relabelings (the batch), not one run
        assert placebo["n_validated"] <= 1, f"placebo over-validated: {placebo['n_validated']}"
    check("placebo run: planted signal destroyed; <=1 chance FP tolerated", t_placebo)

    # --- discovery provenance is disjoint from measurement + fully recorded ---
    def t_disjoint_audit():
        run_dir = tmp / "runs" / "real_r0"
        disc = json.loads((run_dir / "01_discovery.json").read_text())
        d = Dataset(base_cfg().resolve(BASE))
        meas = set(d.m_uid)
        for call in disc["calls"]:
            shown = set(call["slotA_uids"]) | set(call["slotB_uids"])
            assert not (shown & meas), "a discovery call showed a held-out measurement unit"
            assert call["slotA_canonical_group"] != call["slotB_canonical_group"]
        # audit events written incrementally
        ev = (run_dir / "events.jsonl").read_text().strip().splitlines()
        kinds = {json.loads(l)["kind"] for l in ev}
        assert {"request", "response"} <= kinds, f"audit missing request/response: {kinds}"
        assert len(ev) > 50, f"expected many audit events, got {len(ev)}"
    check("provenance: discovery disjoint from measurement, audit trail written", t_disjoint_audit)

    # --- cache key is reproducibility-complete ---
    def t_cache_key():
        c = measure.Cache(tmp / "c.json", "FP1", "PVER1", "design=rotate")
        k1 = c.key("u1", "gpt-4o-mini", "Q?")
        c2 = measure.Cache(tmp / "c2.json", "FP2", "PVER1", "design=rotate")   # diff fingerprint
        c3 = measure.Cache(tmp / "c3.json", "FP1", "PVER2", "design=rotate")   # diff prompt version
        assert k1 != c2.key("u1", "gpt-4o-mini", "Q?"), "cache key ignores dataset fingerprint"
        assert k1 != c3.key("u1", "gpt-4o-mini", "Q?"), "cache key ignores prompt version"
        assert k1 != c.key("u1", "claude-haiku", "Q?"), "cache key ignores model snapshot"
    check("cache: key varies with fingerprint, prompt version, model", t_cache_key)

    # --- config validation ---
    def t_validate():
        for bad in [dict(condition="bogus"), dict(measurement_design="x"),
                    dict(focal_value=1, reference_value=1), dict(fdr_q=1.5),
                    dict(discovery_models=["not-a-model"])]:
            try:
                base_cfg(**bad).resolve(BASE).validate()
                assert False, f"validate accepted bad config {bad}"
            except ValueError:
                pass
    check("config: validate rejects malformed configs", t_validate)

    # --- custom providers/models: registry extension through a config ---
    def t_custom_registry():
        from discern import keys as keymod
        # define a keyless local provider + an open-weight model, then use it in the rotation
        cfg = base_cfg(providers={"myhost": {"base_url": "http://localhost:8000/v1", "api_key_env": None}},
                       models={"my-open": {"provider": "myhost", "model_id": "org/x"}},
                       rotation_pool=["gpt-4o-mini", "my-open"], discovery_models=["gpt-4o-mini"]
                       ).resolve(BASE)
        cfg.validate()                                             # registers + accepts the custom model
        assert core.MODELS["my-open"] == ("myhost", "org/x") and "my-open" in core.FLOATING
        provs = keymod.required_providers(cfg)
        assert "myhost" in provs and "openai" in provs
        assert not any("myhost" in m for m in keymod.missing_keys(cfg)), "keyless provider needs no key"
        # a custom provider WITH an api_key_env is required when its key is unset
        cfg2 = base_cfg(providers={"h2": {"base_url": "https://x/v1", "api_key_env": "H2_KEY_XYZ"}},
                        models={"m2": {"provider": "h2", "model_id": "m"}},
                        rotation_pool=["m2", "gpt-4o-mini"], discovery_models=["m2"]).resolve(BASE)
        cfg2.validate()
        assert "H2_KEY_XYZ" in keymod.missing_keys(cfg2)
        # a model naming an undefined provider is a validation ERROR, not a crash
        try:
            base_cfg(models={"z": {"provider": "ghost", "model_id": "m"}},
                     rotation_pool=["z"]).resolve(BASE).validate()
            assert False, "accepted model with unknown provider"
        except ValueError:
            pass
    check("config: custom providers/models register + validate; keyless local needs no key", t_custom_registry)

    # --- unpinned-alias note (informational; DeepSeek is a valid default pool member) ---
    def t_unpinned_note():
        # DeepSeek is in the DEFAULT pool now -> the note is informational (not None), names it
        n = base_cfg().resolve(BASE).unpinned_pool_note()
        assert n and "deepseek" in n and "runtime-resolved version" in n, n
        # an all-pinned pool -> no note
        assert base_cfg(rotation_pool=["gpt-4o-mini"], discovery_models=["gpt-4o-mini"]
                        ).resolve(BASE).unpinned_pool_note() is None
    check("config: unpinned pool members get an informational runtime-version note", t_unpinned_note)

    # --- rotate needs >= 2 distinct models (documented minimum) ---
    def t_rotate_min_two():
        assert raises(lambda: base_cfg(rotation_pool=["gpt-4o-mini"]).resolve(BASE).validate())
        assert raises(lambda: base_cfg(rotation_pool=["gpt-4o-mini", "gpt-4o-mini"]  # dup != 2 distinct
                                             ).resolve(BASE).validate())
        base_cfg(rotation_pool=["gpt-4o-mini", "claude-haiku"]).resolve(BASE).validate()      # 2 distinct: ok
        # a single model is fine under the ensemble design (rotation minimum doesn't apply)
        base_cfg(measurement_design="ensemble", ensemble_pool=["gpt-4o-mini"],
                 rotation_pool=["gpt-4o-mini"]).resolve(BASE).validate()
    check("config: rotate design requires >= 2 distinct models; ensemble allows one", t_rotate_min_two)

    # --- model_revision is validated at config time (typo/null/unused fails now, not at Stage 4) ---
    def t_model_revision_validation():
        base_cfg(model_revision={"gpt-4o-mini": "v1"}).resolve(BASE).validate()               # valid: ok
        assert raises(lambda: base_cfg(model_revision=["x"]).resolve(BASE).validate())  # not a dict
        assert raises(lambda: base_cfg(model_revision={"nope": "v1"}).resolve(BASE).validate())  # unknown/unused
        assert raises(lambda: base_cfg(model_revision={"gpt-4o-mini": ""}).resolve(BASE).validate())  # empty
        assert raises(lambda: base_cfg(model_revision={"gpt-4o-mini": None}).resolve(BASE).validate())  # null
    check("config: model_revision must be dict of active-model -> non-empty string", t_model_revision_validation)

    # --- the unpinned note covers a FLOATING consolidation / theme model, not just the pools ---
    def t_unpinned_covers_all_active():
        # all-pinned discovery + measurement, but a floating CONSOLIDATION model -> note must fire
        n = base_cfg(rotation_pool=["gpt-4o-mini", "gpt-4.1-mini"], discovery_models=["gpt-4o-mini"],
                     consolidation_model="deepseek").resolve(BASE).unpinned_pool_note()
        assert n and "deepseek" in n, f"consolidation model missing from unpinned note: {n}"
        # a floating THEME model (theming on) is likewise covered
        n2 = base_cfg(rotation_pool=["gpt-4o-mini", "gpt-4.1-mini"], discovery_models=["gpt-4o-mini"],
                      consolidation_model="gpt-4.1", organize_themes=True, theme_model="deepseek"
                      ).resolve(BASE).unpinned_pool_note()
        assert n2 and "deepseek" in n2, f"theme model missing from unpinned note: {n2}"
    check("config: unpinned note reflects EVERY active model (consolidation + theme, not just pools)",
          t_unpinned_covers_all_active)

    def t_direction_legend():
        c = base_cfg().resolve(BASE)  # no labels -> falls back to group_col=value
        assert "group=1" in c.focal_name() and "=0" in c.reference_name()
        assert "more prevalent among" in c.direction_legend()
        c2 = base_cfg(focal_label="women", reference_label="men").resolve(BASE)
        assert c2.focal_name() == "women" and "women" in c2.direction_legend()
        # cosmetic labels must NOT change the run-spec hash (display-only)
        assert c.spec_hash("fp") == c2.spec_hash("fp"), "labels must not affect spec_hash"
        # every validated result carries an explicit higher_group
        assert all("higher_group" in r for r in real["results"])
        hg = {r["higher_group"] for r in real["results"]}
        assert "group=1" in hg or "group=0" in hg
    check("output: direction legend + higher_group name signs; labels are cosmetic", t_direction_legend)

    # ===== Terra follow-up hardening (2026-07-14) =====
    def t_parse_floats():
        for bad in ['{"answer": 0.0}', '{"answer": 1.0}', '{"answer": 0.5}']:
            assert raises(lambda b=bad: core.parse_answer(b)), f"accepted float answer {bad!r}"
        assert core.parse_answer('{"answer": 1}') == 1 and core.parse_answer('{"answer": true}') == 1
    check("core: parse_answer rejects float 0.0/1.0 (explicit int check)", t_parse_floats)

    def t_cid_norm():
        assert core.candidate_id("Food  Focus", "d", "q") == core.candidate_id("Food Focus", "d", "q")
        assert core.candidate_id("A\tB", "d", "q") == core.candidate_id("A B", "d", "q")
    check("core: candidate_id normalizes internal whitespace", t_cid_norm)

    def t_p1_variants():
        g = p1_prompt("grounded", "widget", "- a", "- b")
        r = p1_prompt("relaxed", "widget", "- a", "- b")
        assert "concrete, observable" in g and "concrete, observable" not in r
        assert "abstraction" in r and "reasonably implies" in r
        assert "<<<" in g and "DATA to analyze" in g  # delimiter / injection hygiene
        assert "widget" in g and "business" not in r.lower()  # prompts carry no domain term
    check("prompts: grounded vs relaxed P1 differ, generic, delimited", t_p1_variants)

    def t_stratified_split():
        # split must be 50/50 per ACTIVE label in BOTH conditions (Terra 2026-07-15)
        for cond in ("real", "placebo"):
            gs = Dataset(base_cfg(condition=cond).resolve(BASE)).group_min_sizes()
            assert gs["split1_by_active_label"] == {0: 50, 1: 50}, (cond, gs["split1_by_active_label"])
            assert gs["split2_by_active_label"] == {0: 50, 1: 50}, (cond, gs["split2_by_active_label"])
    check("data: split stratified 50/50 per ACTIVE label (real AND placebo)", t_stratified_split)

    def t_coherent_placebo():
        d = Dataset(base_cfg(condition="placebo").resolve(BASE))
        # placebo permutes WITHIN each disjoint set, preserving group counts (balanced null)
        assert sorted(d.m_placebo.tolist()) == sorted(d.m_group.tolist()), \
            "measurement placebo must be a permutation of the real labels (250/250 preserved)"
        assert d.m_placebo.sum() == d.m_group.sum(), "placebo preserves focal count in measurement"
        pl = d.pool_labels()
        assert sorted(pl.tolist()) == sorted(d.pool["group"].values.tolist()), \
            "discovery-pool placebo must preserve the pool's group balance"
    check("data: placebo permutes within set, preserving group balance", t_coherent_placebo)

    def t_cache_definition():
        c = measure.Cache(tmp / "cd.json", "FP", "PV", "design=rotate")
        assert c.key("u1", "gpt-4o-mini", "Q?", "defA") != c.key("u1", "gpt-4o-mini", "Q?", "defB")
    check("cache: key varies with definition (same question, diff definition)", t_cache_definition)

    def t_spec_guard():
        # rerunning an existing run name under a CHANGED config must raise, not blend
        try:
            run_pipeline(base_cfg(condition="real", n_iterations=6), BASE, resume=True, log=lambda *a: None)
            assert False, "should have raised on changed config for existing run"
        except ValueError as e:
            assert "DIFFERENT configuration" in str(e)
    check("pipeline: run-spec guard raises on resumed config change", t_spec_guard)

    class _Cfg:  # minimal cfg for dedup
        unit_label = "x"; consolidation_model = "gpt-4.1"; consolidation_max_tokens = 8000
    class _A:
        def event(self, *a, **k): pass

    def _cands():
        return [{"candidate_id": "c1", "feature_name": "Food focus", "definition": "d",
                 "classification_question": "mentions food?", "source_splits": ["split1"],
                 "n_supporting_hypotheses": 3, "direction_conflict": False},
                {"candidate_id": "c2", "feature_name": "Food-related", "definition": "d2",
                 "classification_question": "about food?", "source_splits": ["split2"],
                 "n_supporting_hypotheses": 4, "direction_conflict": True},
                {"candidate_id": "c3", "feature_name": "Metal", "definition": "d3",
                 "classification_question": "metal?", "source_splits": ["split1"],
                 "n_supporting_hypotheses": 2, "direction_conflict": False}]

    def t_dedup_merges():
        orig = consolidate.llm_json_call
        consolidate.llm_json_call = lambda *a, **k: [{"members": [1, 2], "canonical": 1},
                                                     {"members": [3], "canonical": 3}]
        out, info = consolidate._residual_dedup(_Cfg(), _cands(), _A())
        consolidate.llm_json_call = orig
        assert len(out) == 2 and info["merged"] == 1
        food = [c for c in out if "Food" in c["feature_name"]][0]
        assert set(food["source_splits"]) == {"split1", "split2"}, "merged twin must union splits"
        assert food["n_supporting_hypotheses"] == 7, "must SUM support (3+4)"      # Terra fix
        assert food["direction_conflict"] is True, "must OR direction_conflict"    # Terra fix
        assert set(food["_merged_from"]) == {"c1", "c2"}, "must retain all source ids"
    check("consolidate: dedup aggregates support/conflict/splits across group", t_dedup_merges)

    def t_dedup_rejects_bad():
        # canonical not a member; incomplete coverage; non-dict -> skip dedup (keep as-is), never crash
        for bad in ([{"members": [1, 2], "canonical": 3}],          # canonical not in members
                    [{"members": [1], "canonical": 1}],             # incomplete coverage (3 cands)
                    [{"members": [1, 2], "canonical": 1}],          # missing c3
                    ["not a dict"]):
            orig = consolidate.llm_json_call
            consolidate.llm_json_call = lambda *a, b=bad, **k: b
            out, info = consolidate._residual_dedup(_Cfg(), _cands(), _A())
            consolidate.llm_json_call = orig
            assert info == {"merged": 0, "coverage_ok": False} and len(out) == 3, f"bad group {bad}"
    check("consolidate: dedup rejects malformed groups (skips, keeps as-is)", t_dedup_rejects_bad)

    def t_p4_generic():
        # the classifier prompt is fully generic — the unit_label is the only domain term
        p = core._classify_prompt("Q?", "some text", "a def")   # default label "item"
        assert p.startswith('item: "some text"')
        assert "Answer for this item based only on the text above" in p
        s = core._sys_prompt()
        assert s.startswith("You classify items.") and "Return only JSON." in s
        assert "DATA" in s and "instructions" in s   # data/instruction boundary asserted in system role
        # any label flows through cleanly with no leaked default
        g = core._classify_prompt("Q?", "some text", "a def", unit_label="court filing")
        assert g.startswith('court filing: "some text"') and "Answer for this court filing" in g
        assert "item" not in g.replace("court filing", "")
        assert "business" not in g
        assert core._sys_prompt("court filing").startswith("You classify court filings.")
    check("P4: generic classifier prompt + system-role data boundary for any label", t_p4_generic)

    def t_cycling_sampler():
        # (a) nested prefixes: with the same seed, the first k calls of a longer run are identical
        # to a k-call run; (b) no unit reused within (split, canonical group) before exhaustion;
        # (c) every hypothesis carries _iter (the saturation diagnostic depends on all three)
        from discern.audit import Audit
        import tempfile as _tf
        d8 = Dataset(base_cfg(n_iterations=8).resolve(BASE))
        a = Audit(Path(_tf.mkdtemp()))
        disc4 = discovery.run_discovery(base_cfg(n_iterations=4).resolve(BASE), d8, a)
        disc8 = discovery.run_discovery(base_cfg(n_iterations=8).resolve(BASE), d8, a)
        c4 = [c for c in disc4["calls"]]
        c8 = [c for c in disc8["calls"]]
        by_split4 = {s: [c for c in c4 if c["split"] == s] for s in ("split1", "split2")}
        by_split8 = {s: [c for c in c8 if c["split"] == s] for s in ("split1", "split2")}
        for s in ("split1", "split2"):
            for i in range(4):  # prefix property
                assert by_split8[s][i]["slotA_uids"] == by_split4[s][i]["slotA_uids"], \
                    f"{s} call {i}: 8-run is not a superset-prefix of 4-run"
            seen = {0: set(), 1: set()}
            for c in by_split8[s]:  # no reuse before exhaustion (pool >> 8*15 here)
                for slot in ("slotA", "slotB"):
                    g = c[f"{slot}_canonical_group"]
                    us = set(c[f"{slot}_uids"])
                    assert not (us & seen[g]), f"{s}: unit reused before exhaustion"
                    seen[g] |= us
        assert all("_iter" in h for h in disc8["split1"] + disc8["split2"]), "_iter missing"
        assert {h["_iter"] for h in disc8["split1"]} == set(range(8))
    check("discovery: cycling sampler — nested prefixes, no reuse, _iter tagged", t_cycling_sampler)

    def t_theme_dup_flagged():
        recs = [{"candidate_id": "c1", "feature_name": "A", "definition": "da",
                 "measured_direction": "focal_higher", "mean_effect": 0.2, "perm_p": 0.01},
                {"candidate_id": "c2", "feature_name": "B", "definition": "db",
                 "measured_direction": "focal_lower", "mean_effect": -0.2, "perm_p": 0.01}]
        orig = themes.llm_json_call
        themes.llm_json_call = lambda *a, **k: [
            {"theme_id": "t1", "theme_label": "T1", "member_features": [1, 2]},
            {"theme_id": "t2", "theme_label": "T2", "member_features": [1]}]  # F1 in two themes
        cross = themes.organize_themes(recs)
        themes.llm_json_call = orig
        assert cross["coverage_ok"] is False and 1 in cross["duplicated_feature_numbers"]
    check("themes: feature assigned to two themes is a coverage failure", t_theme_dup_flagged)

    # ===== Terra review follow-ups =====
    def t_infeasible_split():
        # after the held-out reservation, the discovery pool halves cannot supply items_per_group
        # -> Dataset raises at construction (so --dry-run catches it, not only a live run)
        assert raises(lambda: Dataset(base_cfg(items_per_group=100000).resolve(BASE)))
    check("data: infeasible discovery halves raise at preflight (dry-run safe)", t_infeasible_split)

    def t_preflight_reports():
        # blank-text rows are excluded and reported; a third group value is reported, not silently kept.
        # Sized so the run stays feasible (so we reach d.excluded rather than the feasibility guard).
        import pandas as pd, tempfile as _tf
        rows = ([{"group": 1, "text": f"food {i}"} for i in range(40)]
                + [{"group": 0, "text": f"hardware {i}"} for i in range(40)]
                + [{"group": 1, "text": "   "}, {"group": 0, "text": " \t "}]   # 2 whitespace-only texts
                + [{"group": 2, "text": "third a"}, {"group": 2, "text": "third b"}])  # 2 third-group
        p = Path(_tf.mkdtemp()) / "d.csv"
        pd.DataFrame(rows).to_csv(p, index=False)
        d = Dataset(base_cfg(dataset=str(p), n_per_group=10, items_per_group=3).resolve(BASE))
        assert d.excluded["dropped_blank_text"] == 2, d.excluded
        assert d.excluded["excluded_other_group"] == 2, d.excluded
        assert d.excluded["kept"] == 80, d.excluded
        # a missing column gives a helpful error naming the column, not a raw KeyError
        assert raises(lambda: Dataset(base_cfg(text_col="nope").resolve(BASE)))
    check("data: preflight excludes blanks, reports third-group rows, names missing columns", t_preflight_reports)

    def t_tiered_selection():
        from discern.select import run_selection
        d = Dataset(base_cfg().resolve(BASE))
        labels = d.m_group
        foc = np.where(labels == 1)[0]
        ref = np.where(labels == 0)[0]
        strong = np.zeros(len(labels)); strong[foc] = 1                     # perfect signal -> confirmed
        mod = np.zeros(len(labels))                                         # ~56/44 -> marginal
        mod[foc[:int(0.56 * len(foc))]] = 1
        mod[ref[:int(0.44 * len(ref))]] = 1
        rng = np.random.default_rng(0)
        null = rng.integers(0, 2, len(labels)).astype(float)               # noise -> not validated
        C = {"c_strong": {"y": strong.tolist()}, "c_mod": {"y": mod.tolist()},
             "c_null": {"y": null.tolist()}}
        cands = [{"candidate_id": k, "feature_name": k, "definition": "d",
                  "classification_question": "q"} for k in C]

        def sel(**over):
            return run_selection(base_cfg(permutations=1000, **over).resolve(BASE), d, C, cands)

        # loose exploratory tier: the marginal candidate should land 'suggestive', strong 'confirmed'
        s = sel(fdr_q=0.05, fdr_q_exploratory=0.9)
        tier = {r["candidate_id"]: r["tier"] for r in s["results"]}
        assert tier["c_strong"] == "confirmed", tier
        assert tier["c_mod"] == "suggestive", tier                          # in the 0.05-0.9 band
        # counts + flags are internally consistent
        assert s["n_validated"] == sum(r["tier"] == "confirmed" for r in s["results"])
        assert s["n_suggestive"] == sum(r["tier"] == "suggestive" for r in s["results"])
        assert all((r["validated"]) == (r["tier"] == "confirmed") for r in s["results"])
        assert all(r["tier"] in ("confirmed", "suggestive", "not_validated") for r in s["results"])
        # disabling the tier collapses everything to confirmed / not_validated
        s0 = sel(fdr_q=0.05, fdr_q_exploratory=None)
        assert s0["n_suggestive"] == 0 and not any(r["tier"] == "suggestive" for r in s0["results"])
    check("select: tiered confirmed/suggestive tiers, counts consistent, disablable", t_tiered_selection)

    def t_excel_input():
        # discern reads .xlsx/.tsv, not just .csv — same filtering + partition
        import pandas as pd, tempfile as _tf
        src = pd.read_csv(ds)
        xp = Path(_tf.mkdtemp()) / "d.xlsx"
        src.to_excel(xp, index=False)
        d = Dataset(base_cfg(dataset=str(xp)).resolve(BASE))
        assert len(d.m_uid) == 200 and d.excluded["kept"] == len(src)
    check("data: reads .xlsx datasets (not only .csv)", t_excel_input)

    def t_graceful_skip():
        import discern.measure as measure
        from discern.measure import run_measurement, Cache
        import tempfile as _tf

        class DummyAudit:
            def event(self, *a, **k):
                pass

        cfg = base_cfg().resolve(BASE)
        d = Dataset(cfg)
        tmp2 = Path(_tf.mkdtemp())
        cands = [{"candidate_id": f"c{i}", "feature_name": f"F{i}", "definition": "d",
                  "classification_question": ("BAD q" if i == 2 else f"good {i}")} for i in range(5)]

        def failing(question, desc, **kw):          # one question a model can never answer 0/1
            if question == "BAD q":
                raise RuntimeError("non-binary answer 3")
            return len(desc) % 2
        orig = measure.classify_one
        measure.classify_one = failing
        try:
            C = run_measurement(cfg, d, cands,
                                Cache(tmp2 / "c.json", d.fingerprint, cfg.prompt_version, "cs"), DummyAudit())
            assert "c2" not in C and len(C) == 4, list(C)   # bad candidate dropped, rest measured
            # systematic failure (all candidates fail) must still RAISE, not silently return {}
            allbad = [dict(c, candidate_id=f"x{i}", classification_question="BAD q")
                      for i, c in enumerate(cands)]
            assert raises(lambda: run_measurement(
                cfg, d, allbad, Cache(tmp2 / "c2.json", d.fingerprint, cfg.prompt_version, "cs"), DummyAudit()))
        finally:
            measure.classify_one = orig
    check("measure: unmeasurable candidate skipped; systematic failure still raises", t_graceful_skip)

    def t_cli_config_behavior():
        from types import SimpleNamespace
        from discern.cli import cmd_run

        def sysexit(fn):
            try:
                fn(); return False
            except BaseException:      # SystemExit is not a subclass of Exception
                return True

        def args(**over):
            base = dict(config=None, dataset=None, text_col=None, group_col=None, focal_value=None,
                        reference_value=None, focal_label=None, reference_label=None, unit_label=None,
                        models=None, n_per_group=None, discovery_variant=None, output_dir=None,
                        organize_themes=False, fresh_reservation=False, n_runs=1, run_index=0,
                        condition="real", dry_run=True, no_resume=False)
            base.update(over)
            return SimpleNamespace(**base)
        # --config combined with a content flag is rejected, not silently ignored
        assert sysexit(lambda: cmd_run(args(config="x.json", dataset="d.csv")))
        # flags path missing a required column errors clearly
        assert sysexit(lambda: cmd_run(args(dataset="d.csv")))   # no text_col/group_col
    check("cli: --config + content flag rejected; missing required flag errors", t_cli_config_behavior)


def test_end_to_end():        # pytest entry point
    run_all()
    assert not FAIL, FAIL


if __name__ == "__main__":
    run_all()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILURES: {FAIL}'}")
    if FAIL:
        raise SystemExit(1)
