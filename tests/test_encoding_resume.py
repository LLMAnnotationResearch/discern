"""Offline tests for three fixes (2026-07-30, from external-user feedback):

  1. UTF-8 text I/O everywhere. Every read/write in the package must pin encoding="utf-8" rather
     than inheriting the platform default (cp1252 on Windows for Python < 3.15), which mangled
     non-ASCII characters in 05_summary.md. Delimited input additionally strips an Excel BOM.
  2. classify_workers is excluded from spec_hash. It is request concurrency and cannot change a
     result, so lowering it after a rate limit must RESUME the run, not be rejected as a new config.
  3. Permutation count auto-scales to the multiplicity being corrected. The p-value floor
     1/(B+1) must clear the strictest BH threshold q/n, or a single strong feature can never pass.

No API calls.  Run:  python3 tests/test_encoding_resume.py
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from discern.audit import Audit
from discern.config import RunConfig
from discern.data import read_table
from discern.select import MAX_PERMUTATIONS, _required_permutations

FAIL = []


def check(name, fn):
    try:
        fn(); print(f"  PASS {name}")
    except AssertionError as e:
        FAIL.append(name); print(f"  FAIL {name}: {e}")


NON_ASCII = "em—dash, acento í, ñ, “curly”, 中文, emoji ✅"


# ---------- 1. encoding ----------
def t_audit_roundtrip_non_ascii():
    """A stage artifact and an event line survive a write/read cycle with non-ASCII intact."""
    with tempfile.TemporaryDirectory() as d:
        a = Audit(d)
        a.write_stage("00_test", {"feature_name": NON_ASCII})
        a.event("measure", "response", answer=NON_ASCII)
        got = a.load_stage("00_test")
        assert got["feature_name"] == NON_ASCII, f"stage roundtrip mangled: {got}"
        # read the file back as explicit utf-8 — a cp1252-written file would fail to decode here
        raw = (Path(d) / "events.jsonl").read_text(encoding="utf-8")
        assert NON_ASCII in json.loads(raw.splitlines()[0])["answer"], "event roundtrip mangled"
        # and the counter must survive a resume over a non-ASCII event log
        assert Audit(d)._counter == 1, "event counter did not resume across non-ASCII log"


def t_no_unpinned_text_io():
    """No text-mode file I/O in the package may rely on the platform default encoding."""
    import re
    bad = []
    for p in sorted((HERE.parent / "src" / "discern").glob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            # read_text()/write_text(...) with no encoding=, or open() in text mode with no encoding=
            hit = (re.search(r"\.read_text\(\s*\)", s)
                   or (re.search(r"\.write_text\(", s) and "encoding=" not in s
                       and not s.rstrip().endswith((",", "(")))
                   or (re.search(r"\bopen\(", s) and "encoding=" not in s and '"rb"' not in s
                       and "'rb'" not in s))
            if hit:
                bad.append(f"{p.name}:{i}: {s}")
    assert not bad, "unpinned text I/O:\n    " + "\n    ".join(bad)


def t_csv_bom_stripped():
    """Excel's 'CSV UTF-8' export writes a BOM; it must not end up inside the first column name."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bom.csv"
        p.write_text("id,text\n1,caf\u00e9\n", encoding="utf-8-sig")
        df = read_table(p)
        assert list(df.columns) == ["id", "text"], f"BOM leaked into columns: {list(df.columns)!r}"
        assert df["text"][0] == "caf\u00e9", f"non-ASCII cell mangled: {df['text'][0]!r}"


def t_csv_cp1252_fallback():
    """A legacy Windows-encoded export is read (with a warning) rather than crashing the run."""
    import warnings
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "legacy.csv"
        p.write_bytes("id,text\n1,caf\u00e9 na\u00efve\n".encode("cp1252"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            df = read_table(p)
        assert df["text"][0] == "caf\u00e9 na\u00efve", f"cp1252 fallback wrong: {df['text'][0]!r}"
        assert any("cp1252" in str(x.message) for x in w), "fallback must warn, not decode silently"


# ---------- 2. spec_hash / resume ----------
def _cfg(**kw):
    return RunConfig(dataset="d.csv", text_col="t", group_col="g", **kw)


def t_workers_not_in_spec_hash():
    """Lowering classify_workers after a rate limit must keep the SAME run identity."""
    a = _cfg(classify_workers=24).spec_hash("fp")
    b = _cfg(classify_workers=4).spec_hash("fp")
    assert a == b, "classify_workers changed spec_hash -> resume would be refused as a new config"


def t_cosmetic_not_in_spec_hash():
    """The pre-existing exclusions still hold (guards against a careless edit to the exclude list)."""
    base = _cfg().spec_hash("fp")
    for kw in ({"output_dir": "elsewhere"}, {"focal_label": "X"}, {"reference_label": "Y"},
               {"base_dir": "/tmp"}):
        assert _cfg(**kw).spec_hash("fp") == base, f"{kw} must not change run identity"


def t_substantive_still_in_spec_hash():
    """Anything that CAN change a result must still change run identity."""
    base = _cfg().spec_hash("fp")
    for kw in ({"n_per_group": 100}, {"fdr_q": 0.10}, {"permutations": 5000},
               {"discovery_prompt_variant": "grounded"}, {"n_iterations": 5},
               {"measurement_design": "ensemble"}, {"condition": "placebo"}):
        assert _cfg(**kw).spec_hash("fp") != base, f"{kw} must change run identity"
    assert _cfg().spec_hash("fp2") != base, "dataset fingerprint must change run identity"


# ---------- 3. permutation auto-scaling ----------
def t_permutations_clear_bh_floor():
    """For every plausible candidate count, the p-floor must clear the rank-1 BH threshold q/n."""
    for n in (1, 10, 50, 100, 101, 250, 400):
        B, capped = _required_permutations(n, 0.05, 2000)
        assert not capped, f"n={n} should not hit the cap"
        assert 1.0 / (B + 1) <= 0.05 / n + 1e-15, \
            f"n={n}: p-floor {1/(B+1):.2} > strictest BH threshold {0.05/n:.2} (B={B})"


def t_permutations_floor_is_configured_value():
    """cfg.permutations is a FLOOR: small runs keep the configured 2000, never fewer."""
    B, _ = _required_permutations(10, 0.05, 2000)
    assert B == 2000, f"small run should keep the configured floor, got {B}"
    B, _ = _required_permutations(400, 0.05, 2000)
    assert B == 8000, f"400 candidates at q=.05 needs 8000, got {B}"
    # an explicitly raised floor is honored even when the requirement is lower
    B, _ = _required_permutations(10, 0.05, 20_000)
    assert B == 20_000, f"configured floor must win when higher, got {B}"


def t_permutations_capped_flag():
    """A pathological q reports the cap rather than silently running for hours."""
    B, capped = _required_permutations(400, 0.0001, 2000)
    assert capped and B == MAX_PERMUTATIONS, f"expected capped at {MAX_PERMUTATIONS}, got {B} {capped}"


def t_permutations_degenerate_inputs():
    """Zero candidates / missing q fall back to the configured value instead of dividing by zero."""
    assert _required_permutations(0, 0.05, 2000) == (2000, False)
    assert _required_permutations(10, 0, 2000) == (2000, False)


# ---------- run the checks at import (same convention as test_core.py) ----------
print("encoding:")
check("audit roundtrip preserves non-ASCII", t_audit_roundtrip_non_ascii)
check("no unpinned text I/O in package", t_no_unpinned_text_io)
check("CSV BOM stripped from column names", t_csv_bom_stripped)
check("cp1252 fallback reads + warns", t_csv_cp1252_fallback)
print("spec_hash / resume:")
check("classify_workers excluded", t_workers_not_in_spec_hash)
check("cosmetic fields excluded", t_cosmetic_not_in_spec_hash)
check("substantive fields included", t_substantive_still_in_spec_hash)
print("permutation auto-scaling:")
check("p-floor clears BH threshold", t_permutations_clear_bh_floor)
check("configured value is a floor", t_permutations_floor_is_configured_value)
check("cap is reported", t_permutations_capped_flag)
check("degenerate inputs safe", t_permutations_degenerate_inputs)


def test_encoding_and_resume():   # pytest entry point (checks ran at import above)
    assert not FAIL, FAIL


if __name__ == "__main__":
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILURES: {FAIL}'}")
    if FAIL:
        raise SystemExit(1)
