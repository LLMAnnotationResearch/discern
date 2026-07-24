#!/usr/bin/env python3
"""Check that every built-in model_id in the discern registry still exists at its provider.

A cheap guard against silent model deprecation (e.g. Google retiring `gemini-2.0-flash`). For each
provider used by the registry it fetches the provider's model list and checks membership:

  * OpenRouter          — public /models endpoint, no key needed (always checked).
  * key'd providers     — /models listed via the provider's endpoint IF its api_key_env is set.
  * no key / `local`    — SKIPPED (can't verify without a key / a running local server).

A model absent from its provider's catalog might still be a working, unlisted ALIAS (e.g. a provider's
floating model alias). Only two things count as DEPRECATED: an id absent from an
*authoritative* public catalog (OpenRouter), or one absent from a catalog whose live probe returns an
unambiguous "model not found". An id that is absent but merely *unconfirmable* — no key to probe, or a
transient error / rate limit — is reported as UNVERIFIED (warn), never dead, so the weekly action
doesn't flake on a network blip.

Exit status is 1 only on a confirmed deprecation, else 0 — so it works as a CI guard or a periodic
cron. Skips, working aliases, and unverified warnings never fail the run.

    python3 scripts/check_model_ids.py                 # check the shipped registry
    python3 scripts/check_model_ids.py --config x.json # also check that config's custom models

Uses only the standard library for HTTP, so it has no import-time dependency on any SDK version.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from discern.core import MODELS, PROVIDERS, FLOATING   # noqa: E402
from discern import keys as keymod                      # noqa: E402

TIMEOUT = 20


def _get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 (trusted provider URLs)
        return json.load(r)


def provider_model_ids(provider: str) -> tuple[set[str] | None, str]:
    """Return (set_of_known_ids, note), or (None, reason) when the provider can't be checked
    (no key, local server, or a network/HTTP error) — an unverifiable provider is skipped, never
    treated as a deprecation."""
    sp = PROVIDERS[provider]
    if provider == "local":
        return None, "local server — model is user-configured"
    key = os.environ.get(sp.api_key_env) if sp.api_key_env else None
    try:
        if sp.kind == "anthropic":
            if not key:
                return None, f"no {sp.api_key_env}"
            data = _get_json("https://api.anthropic.com/v1/models",
                             {"x-api-key": key, "anthropic-version": "2023-06-01"})
        else:  # openai-compatible: GET {base}/models  (OpenRouter's list is public)
            if not key and provider != "openrouter":
                return None, f"no {sp.api_key_env}"
            base = sp.base_url or "https://api.openai.com/v1"
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            data = _get_json(base.rstrip("/") + "/models", headers)
        ids = {m.get("id") for m in data.get("data", []) if isinstance(m, dict)}
        # some endpoints prefix ids (e.g. Gemini lists 'models/gemini-2.5-flash') — also index the tail
        ids |= {i.split("/")[-1] for i in ids if isinstance(i, str)}
        if not ids:   # unexpected empty catalog -> unverifiable, don't mass-flag as deprecated
            return None, "empty model list"
        return ids, f"{len(data.get('data', []))} listed"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}"


# Providers whose /models listing is complete and public, so ABSENCE is authoritative (a model not
# listed is genuinely gone) even without a probe. Other providers may omit working aliases, so absence
# there must be confirmed with a live call.
AUTHORITATIVE_CATALOG = {"openrouter"}

# error fragments that unambiguously mean "this model does not exist" (-> retired), as opposed to a
# transient failure (rate limit, timeout, connection) which must NOT be read as a deprecation.
_RETIRED_SIGNALS = ("not found", "does not exist", "no such model", "invalid model", "unknown model",
                    "model_not_found", "404", "decommission", "deprecat", "no longer available")


def probe_status(model_key: str) -> str:
    """Live-call status for a model absent from its catalog: 'alive' (an unlisted but working alias),
    'retired' (an unambiguous model-not-found error), or 'unknown' (no key to probe, or a TRANSIENT
    error such as a rate limit / timeout — never read as dead). Distinguishing retired from unknown is
    what keeps the weekly action from flaking on a network blip."""
    prov = PROVIDERS[MODELS[model_key][0]]
    if prov.api_key_env and not os.environ.get(prov.api_key_env):
        return "unknown"
    try:
        from discern import core   # SDK-backed; only invoked for the rare not-in-catalog case
        r = core.probe_model_version(model_key)
    except Exception:  # noqa: BLE001
        return "unknown"
    if "error" not in r:
        return "alive"
    err = str(r.get("error", "")).lower()
    return "retired" if any(s in err for s in _RETIRED_SIGNALS) else "unknown"


def run(models: dict) -> int:
    listing: dict[str, tuple[set[str] | None, str]] = {}
    for prov in sorted({p for p, _ in models.values()}):
        listing[prov] = provider_model_ids(prov)

    width = max((len(k) for k in models), default=8)
    deprecated, unverified, n_ok, n_skip, n_alias = [], [], 0, 0, 0
    for key, (prov, mid) in models.items():
        ids, note = listing[prov]
        if ids is None:
            mark, extra, n_skip = "skip", f"({note})", n_skip + 1
        elif mid in ids:
            mark, extra, n_ok = " ok ", "", n_ok + 1
        elif prov in AUTHORITATIVE_CATALOG:
            # complete public catalog: absence IS the answer, no probe needed
            mark, extra = "DEAD", "absent from authoritative catalog"
            deprecated.append((key, prov, mid))
        else:
            st = probe_status(key)   # confirm with a live call before declaring anything dead
            if st == "alive":
                mark, extra, n_alias = "alias", "unlisted alias (live call OK)", n_alias + 1
            elif st == "retired":
                mark, extra = "DEAD", "not in catalog; live call: model not found"
                deprecated.append((key, prov, mid))
            else:  # 'unknown': no key or a transient error -> WARN, never a hard failure
                mark, extra = "warn", "absent from catalog; UNVERIFIED (no key / transient error)"
                unverified.append((key, prov, mid))
        pin = "float" if key in FLOATING else "pin"
        print(f"[{mark}] {key:<{width}}  {pin:<5} {prov:<11} {mid:<42} {extra}")

    print()
    if deprecated:
        print(f"DEPRECATED ({len(deprecated)}): " +
              ", ".join(f"{k} -> {m}" for k, _, m in deprecated))
        print("Fix these model_ids in src/discern/core.py (MODELS), then re-run.")
        return 1
    if unverified:
        print(f"UNVERIFIED ({len(unverified)}): absent from the provider catalog but not confirmable — "
              f"set the provider API key to resolve: " + ", ".join(k for k, _, _ in unverified))
    print(f"No confirmed deprecations — {n_ok} ok, {n_alias} working alias(es), "
          f"{len(unverified)} unverified (warn), {n_skip} skipped.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="also register + check the custom providers/models in this config")
    args = ap.parse_args()
    keymod.load_env()  # pick up ~/.config/discern/.env (or $DISCERN_ENV) so keyed providers are checked
    if args.config:
        from discern.config import RunConfig
        from discern.core import register_models
        cfg, _ = RunConfig.from_file(args.config)
        register_models(cfg.models, cfg.providers)
    return run(dict(MODELS))


if __name__ == "__main__":
    sys.exit(main())
