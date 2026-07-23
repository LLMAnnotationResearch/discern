"""Post-validation theme crosswalk (code review 2026-07-13, Phase 4.2 / task #19).

A NON-SELECTIVE presentation layer. After Stage 5, a temperature-0 pinned model groups the already
validated features into navigation themes. It may NOT rename, merge, split, delete, add, or
re-direct any feature, and may NOT infer a mechanism — it only assigns each validated feature to
one or more theme labels. The count and statistics of validated features are never changed by this
step. Off by default in the pipeline (organize_themes is called explicitly, not by run_pipeline).

Outputs three linked tables (Terra's design):
  validated_features : one row per validated dimension, untouched by theming.
  feature_themes     : crosswalk feature -> theme. Each feature is assigned to EXACTLY ONE theme
                       (navigation design); a feature in two themes is a coverage failure.
  theme_summary      : presentation-only; NON-ADDITIVE effect ranges, never a pooled validated stat.
"""
from __future__ import annotations

import json

from .core import llm_json_call

THEME_MODEL = "gpt-4.1"  # capable, pinned; temperature 0 for reproducibility

THEME_PROMPT = (
    "You are given a list of features that have ALREADY been validated as distinguishing two "
    "groups. Your ONLY task is to group them into themes so a reader can navigate the list.\n\n"
    "Strict rules:\n"
    "- Do NOT rename, reword, merge, split, delete, or add any feature.\n"
    "- Do NOT change or infer the direction of any feature.\n"
    "- Do NOT infer or state any explanation or cause for any feature or theme.\n"
    "- Themes are navigation labels ONLY; a theme is not itself a validated finding.\n"
    "- Assign EVERY feature to EXACTLY ONE theme — its single best fit. Every feature number must "
    "appear in exactly one theme's member_features list.\n"
    "- Group features by what they describe — their shared subject matter — NEVER by the direction "
    'or sign of their effect. Do not create themes that amount to "features that go one way" '
    'versus "features that go the other way."\n'
    "- Keep distinct subjects in distinct themes, and keep a single subject in one theme: do not "
    "gather unrelated features under a broad catch-all, and do not scatter one subject across "
    "several themes. Use however many themes the features naturally require.\n\n"
    "FEATURES:\n{feature_list}\n\n"
    'Return a JSON object with a single key "themes" whose value is an array of objects, each with '
    "keys: theme_id (snake_case), theme_label (short human label), description (one sentence "
    "stating what the theme's features have in common, navigation only), member_features (array of "
    "the integer F-numbers belonging to this theme), rationale (why these belong together), "
    "needs_human_review (true if the grouping is uncertain)."
)


def organize_themes(records: list, model: str = THEME_MODEL, audit=None) -> dict:
    """records: list of validated-feature dicts (each must have feature_name, definition,
    measured_direction; may carry run/candidate_id/mean_effect/perm_p). Returns the crosswalk plus
    a coverage report. Fail-closed on coverage: if the model omits or invents feature numbers, the
    result is flagged needs_human_review and the discrepancy is reported (nothing is silently lost).
    """
    # number the features 1..N; the model maps by number, we map back by index (ids never mangled)
    lines = []
    for i, r in enumerate(records, 1):
        d = "focal-higher" if r.get("measured_direction", "").endswith("higher") else "focal-lower"
        lines.append(f"F{i}: {r['feature_name']} — {r.get('definition', '').strip()} [{d}]")
    prompt = THEME_PROMPT.format(feature_list="\n".join(lines))

    if audit:
        audit.event("themes", "request", n_features=len(records), model=model)
    themes = llm_json_call(prompt, model, "themes", temperature=0, max_tokens=8000)
    if audit:
        audit.event("themes", "response", n_themes=len(themes))

    # schema validation (fail closed on a malformed-but-JSON-valid response)
    for t in themes:
        if not isinstance(t, dict):
            raise ValueError(f"theme is not an object: {t!r}")
        for k in ("theme_id", "theme_label", "member_features"):
            if k not in t:
                raise ValueError(f"theme missing required key {k!r}: {t!r}")
        if not isinstance(t["member_features"], list):
            raise ValueError(f"member_features must be a list: {t!r}")
        t.setdefault("description", "")
        t.setdefault("needs_human_review", False)

    # validate coverage: 1..N assigned EXACTLY ONCE. Flag omissions, inventions, AND duplicates
    # (a feature in two themes violates the one-theme contract).
    assigned, invented = {}, []
    for t in themes:
        for f in t["member_features"]:
            if isinstance(f, str) and f.lstrip("F").isdigit():
                f = int(f.lstrip("F"))
            if not isinstance(f, int) or not (1 <= f <= len(records)):
                invented.append(f)
                continue
            assigned.setdefault(f, []).append(t["theme_id"])
    missing = [i for i in range(1, len(records) + 1) if i not in assigned]
    duplicated = {i: tids for i, tids in assigned.items() if len(tids) > 1}
    coverage_ok = not missing and not invented and not duplicated
    if not coverage_ok and themes:
        for t in themes:
            t["needs_human_review"] = True

    # attach theme ids back onto each record (by number -> index)
    feature_themes = []
    for i, r in enumerate(records, 1):
        for tid in assigned.get(i, []):
            feature_themes.append({"candidate_id": r.get("candidate_id"), "run": r.get("run"),
                                   "feature_name": r["feature_name"], "theme_id": tid})
    return {"themes": themes, "feature_themes": feature_themes,
            "coverage_ok": coverage_ok, "missing_feature_numbers": missing,
            "invented_feature_numbers": invented,
            "duplicated_feature_numbers": sorted(duplicated),
            "prompt": prompt, "model": model, "n_features": len(records)}


def write_run_themes(run_dir, records: list, audit=None, model: str = THEME_MODEL,
                     legend: str = "") -> dict:
    """Group ONE run's validated features into navigation themes and write 06_themes.json/.md under
    run_dir. Non-selective: validated counts/statistics are untouched. Returns the artifact.
    `legend` is a one-line +/- direction key surfaced in the markdown so signs are never ambiguous.
    Shared by run_pipeline (optional final stage) and the standalone run_themes.py."""
    import json
    from pathlib import Path
    run_dir = Path(run_dir)
    if not records:
        art = {"run": run_dir.name, "n_validated": 0, "n_themes": 0, "coverage_ok": True, "themes": []}
        (run_dir / "06_themes.json").write_text(json.dumps(art, indent=2))
        return art
    cross = organize_themes(records, model=model, audit=audit)
    summary = theme_summary(records, cross)
    art = {"run": run_dir.name, "n_validated": len(records), "n_themes": len(cross["themes"]),
           "coverage_ok": cross["coverage_ok"], "missing": cross["missing_feature_numbers"],
           "invented": cross["invented_feature_numbers"],
           "duplicated": cross.get("duplicated_feature_numbers", []),
           "feature_themes": cross["feature_themes"],   # stable candidate_id -> theme_id crosswalk
           "themes": cross["themes"], "summary": summary,
           "model": cross["model"], "prompt": cross["prompt"]}
    (run_dir / "06_themes.json").write_text(json.dumps(art, indent=2))

    L = [f"# {run_dir.name} — validated features grouped into themes", "",
         f"{len(records)} validated features -> {len(cross['themes'])} navigation themes "
         f"(temperature-0 {cross['model']}). Themes are navigation labels only; grouping changes no "
         f"statistic. Coverage: {'OK' if cross['coverage_ok'] else 'REVIEW NEEDED'}."]
    if legend:
        L.append(f"\n**Direction key:** {legend}.")
    L.append("")
    for t in cross["themes"]:
        s = next((x for x in summary if x["theme_id"] == t["theme_id"]), {})
        dirn = ("all +" if s.get("direction_consistent") and (s.get("effect_mean_pp") or 0) >= 0
                else "all −" if s.get("direction_consistent") else "MIXED")
        L.append(f"## {t['theme_label']}  ({s.get('n_member_features','?')} feats, {dirn}, "
                 f"mean {s.get('effect_mean_pp',0):+.0f}pp)")
        L.append(f"*{t['description']}*")
        nums = sorted(int(str(f).lstrip('F')) for f in t.get("member_features", [])
                      if str(f).lstrip('F').isdigit())
        for n in nums:
            r = records[n - 1]
            grp = f" — more common among {r['higher_group']}" if r.get("higher_group") else ""
            L.append(f"- {r['feature_name']}  ({r['mean_effect']*100:+.0f}pp{grp}, p={r['perm_p']:.3f})")
        L.append("")
    (run_dir / "06_themes.md").write_text("\n".join(L))
    return art


def theme_summary(records: list, crosswalk: dict) -> list:
    """Presentation-only per-theme summary. Effects are reported as a NON-ADDITIVE range/mean of
    member features (never a pooled validated statistic — a theme was not measured as one question).
    For a multi-run input, also reports how many distinct runs contributed a validated member
    (the cross-run replication count)."""
    by_num = {i: r for i, r in enumerate(records, 1)}
    # rebuild number->record and theme->numbers from the crosswalk's assignment
    theme_members: dict = {}
    for t in crosswalk["themes"]:
        nums = []
        for f in t.get("member_features", []):
            if isinstance(f, str) and f.lstrip("F").isdigit():
                f = int(f.lstrip("F"))
            if isinstance(f, int) and f in by_num:
                nums.append(f)
        theme_members[t["theme_id"]] = (t, nums)

    out = []
    for tid, (t, nums) in theme_members.items():
        recs = [by_num[n] for n in nums]
        effects = [r.get("mean_effect") for r in recs if r.get("mean_effect") is not None]
        runs = sorted({r.get("run") for r in recs if r.get("run") is not None})
        signs = {("+" if (r.get("mean_effect") or 0) >= 0 else "-") for r in recs}
        out.append({
            "theme_id": tid, "theme_label": t.get("theme_label"),
            "description": t.get("description"),
            "n_member_features": len(recs),
            "n_runs_replicated": len(runs), "runs": runs,
            "direction_consistent": len(signs) == 1,
            "effect_min_pp": round(min(effects) * 100, 1) if effects else None,
            "effect_max_pp": round(max(effects) * 100, 1) if effects else None,
            "effect_mean_pp": round(sum(effects) / len(effects) * 100, 1) if effects else None,
            "needs_human_review": t.get("needs_human_review", False),
        })
    # sort by replication then by absolute mean effect (descriptive ordering)
    out.sort(key=lambda x: (-x["n_runs_replicated"], -abs(x["effect_mean_pp"] or 0)))
    return out
