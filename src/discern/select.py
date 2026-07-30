"""Stage 5: replication gate + permutation null + Benjamini-Hochberg FDR, applied to ALL candidates
(no screen preselection). Direction is assigned by measurement. An optional, explicitly
domain-specific effect-size floor may be layered on top and is reported separately.
"""
from __future__ import annotations

import math

import numpy as np

from .core import stage5, bh_pass

# Ceiling on the auto-scaled permutation count. Runtime is linear in B x n_candidates (~42 ms per
# candidate per 2000 permutations), so this bounds the selection stage at a few minutes even in the
# worst case. If the cap binds, we say so rather than silently testing at insufficient resolution.
MAX_PERMUTATIONS = 50_000


def _required_permutations(n_candidates: int, q_min: float, floor: int) -> tuple[int, bool]:
    """Permutation count B such that the p-value floor cannot itself block BH.

    A permutation p-value cannot go below 1/(B+1). Benjamini-Hochberg accepts the rank-i candidate
    when p <= q*i/n, so the STRICTEST threshold any candidate faces is q/n (rank 1). If the floor
    exceeds it, a single genuinely strong feature can never validate no matter how large its effect
    — with B=2000 and q=0.05 that bites at n > 100 candidates, and n can reach max_candidates=400.

    Solving 1/(B+1) <= q_min/n gives B >= n/q_min - 1; we use ceil(n/q_min) for margin. Returns
    (B, capped) where `capped` is True if MAX_PERMUTATIONS clipped the requirement.
    """
    if n_candidates <= 0 or not q_min or q_min <= 0:
        return floor, False
    need = math.ceil(n_candidates / q_min)
    B = max(floor, need)
    return (MAX_PERMUTATIONS, True) if B > MAX_PERMUTATIONS else (B, False)


def run_selection(cfg, data, C, candidates) -> dict:
    labels = data.measurement_labels().astype(int)
    split = data.m_split
    arrays = {cid: np.array(v["y"], dtype=float) for cid, v in C.items()}
    # Auto-scale B to the multiplicity actually being corrected for, so the permutation grid is never
    # the binding constraint on what can validate. cfg.permutations acts as the FLOOR, not the value.
    q_min = min([cfg.fdr_q] + ([cfg.fdr_q_exploratory] if cfg.fdr_q_exploratory else []))
    B, B_capped = _required_permutations(len(arrays), q_min, cfg.permutations)
    r5 = stage5(labels.copy(), split, arrays, B=B)  # cid -> (d1, d2, perm_p)
    pmap = {cid: v[2] for cid, v in r5.items()}
    passed = bh_pass(pmap, q=cfg.fdr_q) if pmap else set()
    # secondary "suggestive" tier at a looser FDR (surfaces real-but-marginal effects rather than
    # hiding them below the primary line). Its own FP control still leans on the same-sign gate.
    q_exp = cfg.fdr_q_exploratory
    passed_exp = bh_pass(pmap, q=q_exp) if (pmap and q_exp and q_exp > cfg.fdr_q) else set(passed)

    by_id = {c["candidate_id"]: c for c in candidates}
    results = []
    for cid, (d1, d2, p) in r5.items():
        c = by_id[cid]
        mean_d = (d1 + d2) / 2
        floor_ok = True if cfg.effect_floor is None else abs(mean_d) >= cfg.effect_floor
        confirmed = bool(cid in passed and floor_ok)                     # primary tier (fdr_q)
        suggestive = bool(cid in passed_exp and floor_ok and not confirmed)  # secondary tier
        tier = "confirmed" if confirmed else ("suggestive" if suggestive else "not_validated")
        results.append({
            "candidate_id": cid,
            "feature_name": c["feature_name"],
            "definition": c.get("definition", ""),
            "classification_question": c["classification_question"],
            "claimed_direction": c.get("claimed_direction"),
            "measured_direction": "focal_higher" if mean_d >= 0 else "focal_lower",
            # explicit human-readable group so a sign is never ambiguous out of context
            "higher_group": cfg.focal_name() if mean_d >= 0 else cfg.reference_name(),
            "d1": d1, "d2": d2, "mean_effect": mean_d, "perm_p": p,
            "same_sign": bool(np.sign(d1) == np.sign(d2) and np.sign(d1) != 0),
            "validated_fdr": bool(cid in passed),
            "validated": confirmed,                     # unchanged meaning: passes the PRIMARY tier
            "validated_exploratory": suggestive,        # passes the looser tier but not the primary
            "tier": tier,                               # confirmed | suggestive | not_validated
            "passes_effect_floor": floor_ok,
            "parent_theme": c.get("parent_theme"),
            "n_supporting_hypotheses": c.get("n_supporting_hypotheses"),
            "source_splits": c.get("source_splits"),
            "direction_conflict": c.get("direction_conflict"),
        })
    _rank = {"confirmed": 0, "suggestive": 1, "not_validated": 2}
    results.sort(key=lambda r: (_rank[r["tier"]], r["perm_p"], -abs(r["mean_effect"])))
    return {"results": results,
            "n_candidates": len(candidates),
            "n_validated": sum(r["validated"] for r in results),
            "n_suggestive": sum(r["validated_exploratory"] for r in results),
            "permutations": B,                      # ACTUAL B used (auto-scaled; >= cfg.permutations)
            "permutations_configured": cfg.permutations,
            "permutations_capped": B_capped,        # True -> p-floor may still bind BH; see note
            "p_floor": 1.0 / (B + 1),
            "bh_strictest_threshold": (q_min / len(arrays)) if arrays else None,  # the rank-1 bar
            "n_tested": len(arrays),                # candidates actually entering BH (excl. skipped)
            "effect_floor": cfg.effect_floor, "fdr_q": cfg.fdr_q,
            "fdr_q_exploratory": q_exp,
            "direction_legend": cfg.direction_legend(),
            "focal_group": cfg.focal_name(), "reference_group": cfg.reference_name()}
