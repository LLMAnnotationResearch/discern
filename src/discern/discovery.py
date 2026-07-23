"""Stage 1-2: blinded, order-randomized hypothesis generation on the discovery pool.

For EVERY discovery call the audit trail records: the sampled unit IDs shown in each slot, the
coin-flip that decided which canonical group was rendered as "Group A", and the canonical group of
each slot — so a reader can verify measurement units were held out and reconstruct the remapping.
Returned hypotheses are re-mapped to canonical labels (focal group always "Group A") before storage.
"""
from __future__ import annotations

import re

import numpy as np

from .core import llm_json_call
from .prompts import p1_prompt

_DELIM = re.compile(r"<<<|>>>")


def _safe_item(text) -> str:
    """Neutralize a source text before it is inserted between the <<< >>> data markers: collapse it
    to one line (so it can't forge new list rows) and break any literal <<< / >>> tokens (so it can't
    forge the data boundary and smuggle instructions). Treats every row as untrusted data."""
    t = re.sub(r"\s+", " ", str(text)).strip()
    return _DELIM.sub(lambda m: " ".join(m.group(0)), t)


def _remap_to_canonical(text: str, focal_shown_as_A: bool) -> str:
    """If the focal group was shown as Group B, swap the labels back so canonical = focal is A."""
    if focal_shown_as_A:
        return text
    return text.replace("Group A", "\x00").replace("Group B", "Group A").replace("\x00", "Group B")


def run_discovery(cfg, data, audit) -> dict:
    """Returns {"split1": [hyps], "split2": [hyps], "calls": [...]} with full provenance.
    Discovery draws only from data.pool (measurement units are excluded upstream) and uses the
    condition-coherent labels from `data` (real, or the same null relabeling as measurement)."""
    pool = data.pool
    labels = data.pool_labels()  # coherent with measurement (real, or the shared placebo shuffle)

    # STRATIFIED disjoint halves of the discovery pool (each half gets ~half of each label group)
    rng = np.random.default_rng(cfg.discovery_seed + cfg.run_index)
    halves = {"split1": [], "split2": []}
    for g in np.unique(labels):
        idx = np.where(labels == g)[0]
        idx = idx[rng.permutation(len(idx))]
        cut = len(idx) // 2
        halves["split1"].extend(idx[:cut].tolist())
        halves["split2"].extend(idx[cut:].tolist())
    halves = {k: np.array(sorted(v)) for k, v in halves.items()}

    pool_uid = pool["uid"].tolist()
    pool_text = pool["text"].tolist()
    out = {"split1": [], "split2": [], "calls": []}
    call_i = [0]
    n_failed = [0]

    for split_name, rows in halves.items():
        sub_labels = labels[rows]
        i1 = rows[np.where(sub_labels == 1)[0]]
        i0 = rows[np.where(sub_labels == 0)[0]]
        # fail loudly if a half cannot supply the requested sample (no silent min() shrink)
        if len(i1) < cfg.items_per_group or len(i0) < cfg.items_per_group:
            raise ValueError(f"{split_name}: discovery half has focal={len(i1)}, reference={len(i0)} "
                             f"units < items_per_group={cfg.items_per_group}; lower items_per_group "
                             f"or n_iterations, or enlarge the discovery pool")
        drng = np.random.default_rng(((cfg.discovery_seed + cfg.run_index) * 10)
                                     + (1 if split_name == "split2" else 0))
        k = cfg.items_per_group
        # CYCLING / no-reuse sampler (Terra 2026-07-15): shuffle each canonical group ONCE and walk
        # it in successive non-overlapping blocks of k, reshuffling only after the group is
        # exhausted. This covers far more of the discovery pool at the same call budget than drawing
        # a fresh independent sample per call (which re-shows overlapping units).
        order1, order0, p1, p0 = drng.permutation(i1), drng.permutation(i0), 0, 0
        for it in range(cfg.n_iterations):
            if p1 + k > len(order1):
                order1, p1 = drng.permutation(i1), 0
            if p0 + k > len(order0):
                order0, p0 = drng.permutation(i0), 0
            sel1, p1 = order1[p1:p1 + k], p1 + k   # focal (canonical group 1) units
            sel0, p0 = order0[p0:p0 + k], p0 + k   # reference (canonical group 0) units
            focal_shown_as_A = bool(drng.random() < 0.5)  # coin flip
            if focal_shown_as_A:
                A_rows, B_rows = sel1, sel0
            else:
                A_rows, B_rows = sel0, sel1
            model = cfg.discovery_models[call_i[0] % len(cfg.discovery_models)]
            prompt = p1_prompt(cfg.discovery_prompt_variant, cfg.unit_label,
                               group_a_items="\n".join(f"- {_safe_item(pool_text[r])}" for r in A_rows),
                               group_b_items="\n".join(f"- {_safe_item(pool_text[r])}" for r in B_rows))
            call_rec = {"call": call_i[0], "split": split_name, "iter": it, "model": model,
                        "focal_shown_as_A": focal_shown_as_A,
                        "slotA_uids": [pool_uid[r] for r in A_rows],
                        "slotB_uids": [pool_uid[r] for r in B_rows],
                        "slotA_canonical_group": 1 if focal_shown_as_A else 0,
                        "slotB_canonical_group": 0 if focal_shown_as_A else 1}
            audit.event("discovery", "request", **call_rec)
            try:
                hyps = llm_json_call(prompt, model, "hypotheses",
                                     temperature=cfg.discovery_temperature,
                                     max_tokens=cfg.discovery_max_tokens,
                                     required=["hypothesis"])
            except Exception as ex:  # noqa: BLE001
                # Discovery is deliberately generous and redundant (n_iterations x 2 splits x pool),
                # so one flaky call must not abort the run: log it and move on. The fail-closed floor
                # after the loops still raises if the failures are systematic (an outage) rather than
                # isolated, so an outage can never masquerade as thin-but-valid discovery.
                audit.event("discovery", "failure", call=call_i[0], model=model,
                            split=split_name, error=str(ex))
                n_failed[0] += 1
                call_i[0] += 1
                continue
            audit.event("discovery", "response", call=call_i[0], n_hypotheses=len(hyps))
            for h in hyps:   # every h is a dict with a non-empty "hypothesis" (validated in the call)
                h = dict(h)
                h["hypothesis_raw"] = h["hypothesis"]
                h["hypothesis"] = _remap_to_canonical(h["hypothesis"], focal_shown_as_A)
                h["_discovery_model"] = model
                h["_split"] = split_name
                h["_iter"] = it          # for nested-prefix saturation diagnostics
                h["_focal_shown_as_A"] = focal_shown_as_A
                out[split_name].append(h)
            out["calls"].append(call_rec)
            call_i[0] += 1

    # Fail-closed floor: isolated call failures are tolerated above, but a wholesale failure (e.g. a
    # provider outage or a mispriced/unavailable model) must never masquerade as thin-but-valid
    # discovery. Raise if either split produced zero hypotheses, or if a majority of calls failed.
    n_calls = call_i[0]
    for sp in ("split1", "split2"):
        if not out[sp]:
            raise RuntimeError(f"discovery produced zero hypotheses for {sp} "
                               f"({n_failed[0]}/{n_calls} calls failed) — treating this as a systematic "
                               f"failure rather than a valid empty result")
    if n_calls and n_failed[0] > n_calls / 2:
        raise RuntimeError(f"{n_failed[0]}/{n_calls} discovery calls failed (>50%) — treating this as a "
                           f"systematic failure rather than a valid result")
    return out
