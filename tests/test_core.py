"""Offline unit tests for discern.core primitives (fail-closed parsing, stable candidate IDs,
duplicate/schema handling, balanced rotation, pool registry). No API calls.
Run:  python3 tests/test_core.py
Ported 2026-07-15 from the legacy tests/test_hardening.py (which tested the now-archived
analysis/consolidation/measure_lib.py); discern.core is the canonical implementation."""
import sys
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from discern.core import (parse_answer, parse_json_list, candidate_id, register_candidates,
                              balanced_assignment, check_required, register_models, Provider,
                              MODELS, PROVIDERS, MAIN_POOL, DEFAULT_POOL, FLOATING)
from discern.measure import Cache

FAIL = []
def check(name, fn):
    try:
        fn(); print(f"  PASS {name}")
    except AssertionError as e:
        FAIL.append(name); print(f"  FAIL {name}: {e}")

def raises(fn):
    try: fn()
    except Exception: return True
    return False

# ---------- parse_answer: strict fail-closed ----------
def t_parse_valid():
    assert parse_answer('{"answer": 1}') == 1
    assert parse_answer('{"answer": 0}') == 0
    assert parse_answer('{"answer": true}') == 1
    assert parse_answer('{"answer": false}') == 0
    assert parse_answer('{"answer": "1"}') == 1
    assert parse_answer('{"answer": "0"}') == 0
    assert parse_answer('noise before {"answer": 1} noise after') == 1
def t_parse_rejects():
    bad = ['{}', '{"answer": null}', '{"answer": 2}', '{"answer": -1}', '{"answer": "yes"}',
           '{"answer": 0.5}', '{"answer": 0.0}', '{"answer": 1.0}', '{"other": 1}', 'plain text',
           '', '[1]', '{"answer": [1]}', '{"answer": "01"}']
    for b in bad:
        assert raises(lambda b=b: parse_answer(b)), f"accepted malformed: {b!r}"
check("parse: accepts exactly binary answers", t_parse_valid)
check("parse: rejects everything else incl. floats (fail closed, never coerces to 0)", t_parse_rejects)

# ---------- parse_json_list: fail-closed generation parsing ----------
def t_jsonlist_valid():
    assert parse_json_list('{"features": [{"a": 1}]}', "features") == [{"a": 1}]
    assert parse_json_list('{"features": []}', "features") == []  # explicit empty IS valid
    assert parse_json_list('pre {"features": [1]} post', "features") == [1]
def t_jsonlist_rejects():
    bad = ['{}', '{"features": null}', '{"features": "x"}', '{"other": []}', 'text', '',
           '{"features": {"a": 1}}', '[1,2]']
    for b in bad:
        assert raises(lambda b=b: parse_json_list(b, "features")), f"accepted malformed: {b!r}"
check("jsonlist: accepts well-formed (incl. explicit empty list)", t_jsonlist_valid)
check("jsonlist: rejects malformed (outage cannot masquerade as empty)", t_jsonlist_rejects)

# ---------- candidate IDs ----------
def t_id_deterministic():
    a = candidate_id("Food-related", "def", "Q?")
    assert a == candidate_id("Food-related", "def", "Q?")
    assert a == candidate_id(" Food-related ", " def ", " Q? ")  # whitespace-insensitive
    assert a != candidate_id("Food-related", "def2", "Q?")       # content-sensitive
def t_same_name_different_content():
    a = candidate_id("X"*80, "def A", "Q A?"); b = candidate_id("X"*80, "def B", "Q B?")
    assert a != b, "same long name with different content must get distinct IDs"
check("id: deterministic, whitespace-insensitive, content-sensitive", t_id_deterministic)
check("id: same 60-char name prefix but different content -> distinct IDs", t_same_name_different_content)

# ---------- register_candidates ----------
def t_register_ok():
    cands = [{"feature_name":"A","definition":"da","classification_question":"qa?"},
             {"feature_name":"B","definition":"db","classification_question":"qb?"}]
    out, dropped = register_candidates(cands)
    assert len(out) == 2 and not dropped
    assert all(c["candidate_id"].startswith("c_") for c in out)
def t_register_collapses_exact_dupes():
    c = {"feature_name":"A","definition":"d","classification_question":"q?"}
    out, dropped = register_candidates([dict(c), dict(c), dict(c)])
    assert len(out) == 1 and sum(dropped.values()) == 3
def t_register_rejects_bad_schema():
    for bad in [{"feature_name":"","definition":"d","classification_question":"q?"},
                {"feature_name":"A","definition":"d"},
                {"feature_name":"A","definition":None,"classification_question":"q?"},
                "not a dict"]:
        assert raises(lambda b=bad: register_candidates([b])), f"accepted bad candidate: {bad!r}"
def t_register_allows_name_collision_different_content():
    out, dropped = register_candidates([
        {"feature_name":"Same","definition":"d1","classification_question":"q1?"},
        {"feature_name":"Same","definition":"d2","classification_question":"q2?"}])
    assert len(out) == 2 and out[0]["candidate_id"] != out[1]["candidate_id"]
check("register: assigns IDs, no false drops", t_register_ok)
check("register: collapses exact-content duplicates, reports them", t_register_collapses_exact_dupes)
check("register: rejects empty/missing fields (fail closed)", t_register_rejects_bad_schema)
check("register: same display name w/ different content kept as distinct", t_register_allows_name_collision_different_content)

# ---------- balanced rotation assignment ----------
def t_balance_within_cells():
    rng = np.random.default_rng(3)
    n = 500; group = np.array([1]*250 + [0]*250); split = rng.integers(1, 3, n)
    pool = ["m1", "m2", "m3"]
    a = balanced_assignment(group, split, pool, seed=11)
    assert len(a) == n and set(a) == set(pool)
    for g in (0, 1):
        for s in (1, 2):
            cell = a[(group == g) & (split == s)]
            counts = [int((cell == m).sum()) for m in pool]
            assert max(counts) - min(counts) <= 1, f"cell g={g},s={s} unbalanced: {counts}"
def t_balance_deterministic_and_seed_sensitive():
    group = np.array([1]*30 + [0]*30); split = np.array(([1]*15 + [2]*15)*2)
    a1 = balanced_assignment(group, split, ["m1","m2"], seed=11)
    a2 = balanced_assignment(group, split, ["m1","m2"], seed=11)
    a3 = balanced_assignment(group, split, ["m1","m2"], seed=12)
    assert list(a1) == list(a2), "not deterministic in seed"
    assert list(a1) != list(a3), "seed has no effect"
def t_balance_no_group_confound():
    rng = np.random.default_rng(5)
    n = 400; group = np.array([1]*200 + [0]*200); split = rng.integers(1, 3, n)
    a = balanced_assignment(group, split, ["m1","m2","m3"], seed=7)
    for m in ("m1","m2","m3"):
        share = group[a == m].mean()
        assert abs(share - 0.5) < 0.03, f"model {m} group share {share:.3f} != 0.5"
check("rotation: balanced within every group x split cell (max diff 1)", t_balance_within_cells)
check("rotation: deterministic given seed, varies across seeds", t_balance_deterministic_and_seed_sensitive)
check("rotation: no model-group confound", t_balance_no_group_confound)

# ---------- pool registry sanity ----------
def t_pools():
    assert all(m in MODELS for m in MAIN_POOL)
    assert not (set(MAIN_POOL) & FLOATING), "floating alias in MAIN_POOL"
    assert all(m in MODELS for m in DEFAULT_POOL)
    # every model names a known provider; every provider has a valid request kind
    for k, (prov, mid) in MODELS.items():
        assert prov in PROVIDERS, f"model {k} names unknown provider {prov}"
        assert mid, f"model {k} has empty model_id"
    for name, sp in PROVIDERS.items():
        assert sp.kind in ("openai", "anthropic"), f"provider {name} bad kind {sp.kind}"
check("registry: MAIN_POOL pinned-only, models->known providers, provider kinds valid", t_pools)

# ---------- custom model / provider registration (the extensibility path) ----------
def t_register_custom():
    register_models(
        providers={"myhost": {"base_url": "http://localhost:9999/v1", "api_key_env": None}},
        models={"my-open-model": {"provider": "myhost", "model_id": "org/model-x"}})
    assert PROVIDERS["myhost"].kind == "openai"         # kind defaults to openai
    assert PROVIDERS["myhost"].api_key_env is None      # keyless local server
    assert MODELS["my-open-model"] == ("myhost", "org/model-x")
    assert "my-open-model" in FLOATING                  # custom models are unpinned
    # a registered custom model is usable in a rotation exactly like a built-in (>=2 per cell so both
    # pool members are assigned)
    a = balanced_assignment([1, 1, 1, 1, 0, 0, 0, 0], [1, 2, 1, 2, 1, 2, 1, 2],
                            ["gpt-4o-mini", "my-open-model"], seed=11)
    assert "my-open-model" in set(a)
    # tuple form + provider-kind override both work
    register_models(providers={"myanthropic": {"kind": "anthropic", "api_key_env": "X_KEY"}},
                    models={"m2": ("myanthropic", "some-model")})
    assert PROVIDERS["myanthropic"].kind == "anthropic" and MODELS["m2"][0] == "myanthropic"
check("registry: register_models adds custom provider+model, usable + unpinned", t_register_custom)

def t_register_rejects_bad():
    assert raises(lambda: register_models(models={"bad": {"provider": "nope", "model_id": "x"}})), \
        "model naming unknown provider must raise"
    assert raises(lambda: register_models(models={"bad2": {"provider": "openai"}})), \
        "model missing model_id must raise"
    assert raises(lambda: register_models(models={"bad3": "not-a-dict"})), "bad model spec must raise"
check("registry: register_models fails loudly on unknown provider / missing fields", t_register_rejects_bad)

def t_register_collisions_and_validation():
    # a custom name colliding with a built-in is rejected (no silent shadowing) unless override
    assert raises(lambda: register_models(providers={"openai": {"base_url": "http://x/v1"}}))
    assert raises(lambda: register_models(models={"gpt-4o-mini": {"provider": "openai", "model_id": "x"}}))
    register_models(providers={"openai2": {"base_url": "https://x/v1", "api_key_env": None}})  # non-colliding ok
    # provider definitions are validated AT REGISTRATION (not at first paid call)
    assert raises(lambda: register_models(providers={"p1": {"kind": "bogus"}}))
    assert raises(lambda: register_models(providers={"p2": {"base_url": "ftp://x"}}))
    assert raises(lambda: register_models(providers={"p3": {"api_key_env": "bad name!"}}))
    assert raises(lambda: register_models(providers={"p4": {"json_mode": "yaml"}}))
    # unknown endpoints default to prompt_only (safe for servers that reject response_format)
    register_models(providers={"okhost": {"base_url": "https://ok/v1"}},
                    models={"okm": {"provider": "okhost", "model_id": "z"}})
    assert PROVIDERS["okhost"].json_mode == "prompt_only"
check("registry: rejects built-in collisions; validates kind/url/env/json_mode at registration",
      t_register_collisions_and_validation)

def t_register_evicts_client():
    import discern.core as core
    register_models(providers={"evh": {"base_url": "https://one/v1", "api_key_env": None}})
    core._clients["evh"] = "STALE"                       # simulate an already-built client
    register_models(providers={"evh": {"base_url": "https://two/v1", "api_key_env": None}})
    assert "evh" not in core._clients, "re-registering a provider must evict its cached client"
    assert core.PROVIDERS["evh"].base_url == "https://two/v1"
check("registry: re-registering a provider evicts its stale client + updates the endpoint",
      t_register_evicts_client)

def t_json_kwargs():
    from discern.core import _json_kwargs
    assert _json_kwargs("openai") == {"response_format": {"type": "json_object"}}
    assert _json_kwargs("local") == {}   # prompt_only -> no response_format sent
check("registry: json_mode controls whether response_format is sent (strict parse regardless)", t_json_kwargs)

def t_anthropic_base_url():
    # Terra #2: a custom Claude-compatible endpoint's base_url must reach the Anthropic client
    import types, sys as _sys, os as _os, discern.core as core
    captured = {}
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda api_key=None, base_url=None: captured.update(base_url=base_url) or object()
    _sys.modules["anthropic"] = fake
    core._clients.pop("myclaude", None)
    register_models(providers={"myclaude": {"kind": "anthropic", "base_url": "https://claude.mine/v1",
                                            "api_key_env": "MC_KEY_TEST"}},
                    models={"mc": {"provider": "myclaude", "model_id": "claude-x"}})
    _os.environ["MC_KEY_TEST"] = "k"
    try:
        core._client("myclaude")
        assert captured.get("base_url") == "https://claude.mine/v1", captured
    finally:
        _sys.modules.pop("anthropic", None); _os.environ.pop("MC_KEY_TEST", None)
        core._clients.pop("myclaude", None)
check("provider: custom anthropic endpoint passes base_url to the client (not Anthropic default)",
      t_anthropic_base_url)

def t_cache_identity():
    import tempfile
    # two endpoints serving the SAME model_id must not collide in the cache
    register_models(providers={"h1": {"base_url": "https://one/v1", "api_key_env": None}},
                    models={"mx": {"provider": "h1", "model_id": "same-id"}})
    register_models(providers={"h2b": {"base_url": "https://two/v1", "api_key_env": None}},
                    models={"mx2": {"provider": "h2b", "model_id": "same-id"}})
    c = Cache(Path(tempfile.mkdtemp()) / "c.json", "fp", "pv", "cs")
    assert c.key("u", "mx", "Q?") != c.key("u", "mx2", "Q?"), "custom-endpoint cache collision on shared id"
    # a model_revision bump changes the key -> forces fresh classification (mutable-backend safety)
    c2 = Cache(Path(tempfile.mkdtemp()) / "c.json", "fp", "pv", "cs", revisions={"mx": "v2"})
    assert c.key("u", "mx", "Q?") != c2.key("u", "mx", "Q?"), "model_revision must invalidate the cache"
check("cache: identity keyed by provider+endpoint+id+revision (no cross-endpoint collision)", t_cache_identity)

def t_retry_wait():
    from discern.core import _retry_wait
    class Resp:
        def __init__(self, h): self.headers = h
    class Err(Exception):
        def __init__(self, h): self.response = Resp(h)
    assert _retry_wait(Err({"retry-after": "5"}), 0) == 5.0        # honor Retry-After seconds
    assert _retry_wait(Err({"retry-after": "999"}), 0) == 60.0     # capped at 60s
    assert _retry_wait(Err({"retry-after-ms": "2500"}), 0) == 2.5  # millisecond header
    assert _retry_wait(Exception("x"), 3) == 8.0                   # no response -> backoff min(30,2**3)
    assert _retry_wait(Err({}), 4) == 16.0                         # no header -> backoff
    assert _retry_wait(Err({"retry-after": "soon"}), 2) == 4.0     # unparseable -> backoff, never raises
check("retry: honors Retry-After (s / ms), caps at 60s, falls back to backoff on bad/absent header",
      t_retry_wait)

# ---------- strict schema validation (fail-closed on malformed generations) ----------
def t_check_required():
    good = [{"feature_name": "F", "classification_question": "Q?"}]
    assert check_required(good, ["feature_name", "classification_question"]) == good
    assert check_required(good, None) == good                    # no-op when nothing required
    # missing key, empty value, and non-dict each RAISE (not silently dropped)
    assert raises(lambda: check_required([{"feature_name": "F"}], ["classification_question"]))
    assert raises(lambda: check_required([{"feature_name": "F", "classification_question": ""}],
                                         ["classification_question"]))
    assert raises(lambda: check_required(["not a dict"], ["feature_name"]))
    # one bad object among good ones still raises (the whole response fails closed)
    assert raises(lambda: check_required(good + [{"x": 1}], ["feature_name"]))
check("core: check_required raises on missing/empty/non-dict (no silent filtering)", t_check_required)

# ---------- classification cache key: composition + invalidation ----------
def t_cache_key():
    import tempfile
    c = Cache(Path(tempfile.mkdtemp()) / "c.json", "fp0", "pv0", "cs0")
    base = c.key("u1", "gpt-4o-mini", "Q?", "def")
    # every component participates: change any one -> different key (no stale reuse)
    assert base != c.key("u2", "gpt-4o-mini", "Q?", "def"), "uid must be in key"
    assert base != c.key("u1", "claude-haiku", "Q?", "def"), "model snapshot must be in key"
    assert base != c.key("u1", "gpt-4o-mini", "Q2?", "def"), "question must be in key"
    assert base != c.key("u1", "gpt-4o-mini", "Q?", "def2"), "definition must be in key"
    # prompt_version and dataset fingerprint are the invalidation levers (incl. for floating aliases)
    assert base != Cache(c.path, "fp0", "pv1", "cs0").key("u1", "gpt-4o-mini", "Q?", "def"), \
        "prompt_version bump must invalidate"
    assert base != Cache(c.path, "fp1", "pv0", "cs0").key("u1", "gpt-4o-mini", "Q?", "def"), \
        "dataset fingerprint must invalidate"
    # a floating alias produces a stable, distinct key (its runtime version is recorded in 00_runspec)
    assert "deepseek" in FLOATING
    dk = c.key("u1", "deepseek", "Q?", "def")
    assert dk == c.key("u1", "deepseek", "Q?", "def") and dk != base
check("core: cache key covers uid/model/question/definition + version invalidation", t_cache_key)

def test_core_primitives():   # pytest entry point (checks ran at import above)
    assert not FAIL, FAIL


if __name__ == "__main__":
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILURES: {FAIL}'}")
    if FAIL:
        raise SystemExit(1)
