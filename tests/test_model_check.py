"""Offline tests for scripts/check_model_ids.py — the deprecated-model checker's state logic.

No network: the catalog listing and the live probe are monkeypatched. Verifies the three-state policy
(alive / retired / unknown) so a transient error, rate limit, or missing key becomes a WARN, never a
false DEAD, and that absence from an authoritative public catalog (OpenRouter) is still a hard fail.
Run:  python3 tests/test_model_check.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
import discern.core as core   # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "check_model_ids", HERE.parent / "scripts" / "check_model_ids.py")
cmi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmi)

FAIL = []
def check(name, fn):
    try:
        fn(); print(f"  PASS {name}")
    except AssertionError as e:
        FAIL.append(name); print(f"  FAIL {name}: {e}")
    except Exception as e:  # noqa: BLE001
        FAIL.append(name); print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ---------- probe_status: retired vs transient vs alive ----------
def t_probe_status():
    core.register_models(providers={"tstat": {"base_url": "https://t/v1", "api_key_env": None}},
                         models={"tm": {"provider": "tstat", "model_id": "z"}})
    orig = core.probe_model_version
    try:
        core.probe_model_version = lambda k: {"model": k, "resolved": "z"}                    # ok
        assert cmi.probe_status("tm") == "alive"
        core.probe_model_version = lambda k: {"model": k, "error": "404 - model `z` does not exist"}
        assert cmi.probe_status("tm") == "retired"
        core.probe_model_version = lambda k: {"model": k, "error": "429 rate limit exceeded"}
        assert cmi.probe_status("tm") == "unknown", "a rate limit must read as unknown, not retired"
        core.probe_model_version = lambda k: {"model": k, "error": "connection timed out"}
        assert cmi.probe_status("tm") == "unknown", "a network error must read as unknown, not retired"
    finally:
        core.probe_model_version = orig
check("check: probe_status distinguishes retired (model-not-found) from transient (unknown)", t_probe_status)


# ---------- run(): state -> exit code, with listing + probe patched ----------
def _run_with(listing_fn, probe_fn, models):
    orig_l, orig_p = cmi.provider_model_ids, cmi.probe_status
    cmi.provider_model_ids, cmi.probe_status = listing_fn, probe_fn
    try:
        return cmi.run(models)
    finally:
        cmi.provider_model_ids, cmi.probe_status = orig_l, orig_p

def t_run_warn_not_dead():
    # catalog fetched, model absent, probe can't confirm -> UNVERIFIED (warn) -> exit 0
    rc = _run_with(lambda prov: ({"other"}, "1 listed"), lambda k: "unknown",
                   {"warn1": ("pX", "m-warn")})
    assert rc == 0, "an unverified (absent-but-unconfirmable) model must NOT fail the run"
check("check: unverified alias is warn-only (exit 0), not a false DEAD", t_run_warn_not_dead)

def t_run_confirmed_retired_fails():
    rc = _run_with(lambda prov: ({"other"}, "1 listed"), lambda k: "retired",
                   {"gone": ("pX", "m-gone")})
    assert rc == 1, "a probe-confirmed retired model must fail the run"
check("check: confirmed-retired model exits 1", t_run_confirmed_retired_fails)

def t_run_authoritative_absence_is_dead():
    # OpenRouter catalog is authoritative: absence is a confirmed deprecation without a probe
    rc = _run_with(lambda prov: ({"other"}, "1 listed"), lambda k: "unknown",
                   {"orgone": ("openrouter", "m-x")})
    assert rc == 1, "absence from the authoritative OpenRouter catalog is a confirmed deprecation"
check("check: absence from authoritative (OpenRouter) catalog is DEAD even unprobed",
      t_run_authoritative_absence_is_dead)

def t_run_ok_and_alias_pass():
    rc = _run_with(lambda prov: ({"m-ok"}, "1 listed"), lambda k: "alive",
                   {"ok1": ("pX", "m-ok"), "alias1": ("pX", "m-alias")})
    assert rc == 0, "in-catalog + a working alias must pass"
check("check: in-catalog and working-alias pass (exit 0)", t_run_ok_and_alias_pass)


def test_model_check():   # pytest entry point (checks ran at import above)
    assert not FAIL, FAIL


if __name__ == "__main__":
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILURES: {FAIL}'}")
    if FAIL:
        raise SystemExit(1)
