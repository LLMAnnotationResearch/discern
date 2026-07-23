"""Stage 3: within-split consolidation (P2) then cross-split unification (P3). Carries the full
v2 schema forward (claimed_direction, parent_theme, n_supporting_hypotheses, source_splits,
direction_conflict) and assigns every unified candidate a stable content-hash ID. Fail-closed:
a parse/schema failure raises (an outage can't masquerade as "zero candidates").
"""
from __future__ import annotations

import json

from .core import llm_json_call, register_candidates
from .prompts import P2, P3, P_DEDUP


def _hyp_payload(hyps):
    return json.dumps([{"hypothesis": h.get("hypothesis"), "dimension": h.get("dimension")}
                       for h in hyps])


def _residual_dedup(cfg, candidates, audit):
    """One temp-0 pass merging P3's own surviving exact semantic twins (Terra P1-i). Returns the
    deduped candidate list. Fail-closed on coverage: every input feature must appear in exactly one
    group; otherwise the dedup is skipped (kept as-is) and flagged, never silently dropping a
    feature. Merges union source_splits and carry the canonical member's fields."""
    if len(candidates) < 2:
        return candidates, {"merged": 0}
    lines = [f"F{i}: {c['feature_name']} — {c.get('definition','').strip()} "
             f"Q: {c['classification_question']}" for i, c in enumerate(candidates, 1)]
    prompt = P_DEDUP.format(unit_label=cfg.unit_label, feature_list="\n".join(lines))
    audit.event("dedup", "request", n_candidates=len(candidates), model=cfg.consolidation_model)
    groups = llm_json_call(prompt, cfg.consolidation_model, "groups",
                           temperature=0.0, max_tokens=cfg.consolidation_max_tokens)
    # STRICT validation (Terra 2026-07-15): reject a non-dict group, an empty group, a malformed
    # member number, a canonical that is not one of its members, a duplicate, or an out-of-range
    # number — and reject incomplete coverage. Any failure -> skip dedup (keep candidates as-is),
    # never silently accept a bad grouping.
    def _parse():
        seen, parsed = {}, []
        for g in groups:
            if not isinstance(g, dict):
                return None
            members = []
            for m in g.get("members", []):
                ms = str(m).lstrip("F")
                if not ms.isdigit():
                    return None
                members.append(int(ms))
            if not members:
                return None
            cs = str(g.get("canonical", "")).lstrip("F")
            if not cs.isdigit() or int(cs) not in members:
                return None
            for m in members:
                if m in seen or not (1 <= m <= len(candidates)):
                    return None
                seen[m] = True
            parsed.append((members, int(cs)))
        return parsed if len(seen) == len(candidates) else None

    parsed = _parse()
    if parsed is None:
        audit.event("dedup", "note", coverage_ok=False, skipped=True, n_candidates=len(candidates))
        return candidates, {"merged": 0, "coverage_ok": False}

    out = []
    for members, canon in parsed:
        base = dict(candidates[canon - 1])
        splits, n_supp, dconf, src_ids = [], 0, False, []
        for m in members:  # AGGREGATE provenance across the whole group, not just the canonical
            c = candidates[m - 1]
            for s in c.get("source_splits", []) or []:
                if s not in splits:
                    splits.append(s)
            n_supp += int(c.get("n_supporting_hypotheses") or 0)
            dconf = dconf or bool(c.get("direction_conflict"))
            src_ids.append(c.get("candidate_id"))
        base["source_splits"] = splits
        base["n_supporting_hypotheses"] = n_supp
        base["direction_conflict"] = dconf
        base["_merged_from"] = src_ids
        out.append(base)
    audit.event("dedup", "response", n_before=len(candidates), n_after=len(out),
                merged=len(candidates) - len(out))
    return out, {"merged": len(candidates) - len(out), "coverage_ok": True}


def run_consolidation(cfg, discovery, audit) -> dict:
    model = cfg.consolidation_model
    temp = cfg.consolidation_temperature

    mt = cfg.consolidation_max_tokens

    REQ = ["feature_name", "classification_question", "definition"]  # fields downstream depends on

    def consolidate_split(name, hyps):
        prompt = P2.format(unit_label=cfg.unit_label, hypotheses_json=_hyp_payload(hyps))
        audit.event("consolidate", "request", split=name, n_hypotheses=len(hyps), model=model)
        feats = llm_json_call(prompt, model, "features", temperature=temp, max_tokens=mt, required=REQ)
        audit.event("consolidate", "response", split=name, n_features=len(feats))
        for f in feats:   # every f is a dict with feature_name + classification_question (validated)
            f["source_splits"] = [name]
        return feats

    s1 = consolidate_split("split1", discovery["split1"])
    s2 = consolidate_split("split2", discovery["split2"])

    prompt = P3.format(unit_label=cfg.unit_label,
                       features_1_json=json.dumps(s1), features_2_json=json.dumps(s2))
    audit.event("unify", "request", n_split1=len(s1), n_split2=len(s2), model=model)
    uni = llm_json_call(prompt, model, "features", temperature=temp, max_tokens=mt, required=REQ)
    audit.event("unify", "response", n_unified=len(uni))
    # no silent filter here: llm_json_call already validated feature_name/classification_question/
    # definition are present and non-empty (a missing field raises, it is never dropped quietly).
    candidates, dropped = register_candidates(uni)
    if dropped:
        audit.event("unify", "note", dropped_exact_duplicates=dropped)

    dedup_info = {"merged": 0}
    if cfg.residual_dedup:
        candidates, dedup_info = _residual_dedup(cfg, candidates, audit)
        candidates, _ = register_candidates(candidates)  # re-ID canonical survivors

    return {"split1_features": s1, "split2_features": s2,
            "candidates": candidates, "dropped_duplicates": dropped, "dedup": dedup_info}
