"""Stage 5: replication gate + permutation null + Benjamini-Hochberg FDR, applied to ALL candidates
(no screen preselection). Direction is assigned by measurement. An optional, explicitly
domain-specific effect-size floor may be layered on top and is reported separately.
"""
from __future__ import annotations

import numpy as np

from .core import stage5, bh_pass


def run_selection(cfg, data, C, candidates) -> dict:
    labels = data.measurement_labels().astype(int)
    split = data.m_split
    arrays = {cid: np.array(v["y"], dtype=float) for cid, v in C.items()}
    r5 = stage5(labels.copy(), split, arrays, B=cfg.permutations)  # cid -> (d1, d2, perm_p)
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
            "effect_floor": cfg.effect_floor, "fdr_q": cfg.fdr_q,
            "fdr_q_exploratory": q_exp,
            "direction_legend": cfg.direction_legend(),
            "focal_group": cfg.focal_name(), "reference_group": cfg.reference_name()}
