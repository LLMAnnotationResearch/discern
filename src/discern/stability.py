"""Substantive feature crosswalks with explicit mapping and run-completion states.

Matching decisions are inputs, not an exact-name or significance-based algorithm.
Multiple features may map to a family; their estimates remain separate in cells.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


def _load_crosswalk(runs, memberships):
    run_ids = [run["run_id"] for run in runs]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate run IDs")
    families, links, seen = {}, {}, set()
    for row in memberships:
        family, rid, cid = row["family_id"], row["run_id"], row["candidate_id"]
        if rid not in run_ids or not family or not row["family_label"]:
            raise ValueError("unknown run or empty family")
        if family in families and families[family] != row["family_label"]:
            raise ValueError("inconsistent family label")
        if row["relation"] not in {"anchor", "equivalent", "broader", "narrower", "related"}:
            raise ValueError("unknown substantive relation")
        if row["mapping_status"] not in {"draft", "adjudicated"}:
            raise ValueError("unknown mapping status")
        if (family, rid, cid) in seen:
            raise ValueError("duplicate membership")
        seen.add((family, rid, cid))
        families[family] = row["family_label"]
        links.setdefault((rid, family), []).append(row)
    loaded = {}
    for run in runs:
        rid = run["run_id"]
        if run["status"] == "planned":
            if any(key[0] == rid for key in links):
                raise ValueError("planned run cannot have observed memberships")
            continue
        if run["status"] != "complete":
            raise ValueError("run status must be complete or planned")
        root = Path(run["artifact_path"])
        candidates = json.loads((root / "02_consolidated.json").read_text(encoding="utf-8"))["candidates"]
        selected = json.loads((root / "04_selected.json").read_text(encoding="utf-8"))["results"]
        by_id = {c["candidate_id"]: c for c in candidates}
        result = {c["candidate_id"]: c for c in selected}
        mapped = [row for row in memberships if row["run_id"] == rid]
        if not set(result).issubset(by_id) or any(row["candidate_id"] not in by_id for row in mapped):
            raise ValueError("membership/result references unknown candidate")
        all_adjudicated = (set(row["candidate_id"] for row in mapped) == set(by_id)
                           and all(row["mapping_status"] == "adjudicated" for row in mapped))
        loaded[rid] = (by_id, result, mapped, all_adjudicated)
    return families, links, loaded


def crosswalk(runs, memberships):
    """Detailed crosswalk: unresolved matching cannot establish family absence.

    A proposed but unmeasured candidate is SKIP, never NV or absent.
    """
    families, links, loaded = _load_crosswalk(runs, memberships)
    output = []
    tiers = {"confirmed": "V", "suggestive": "S", "uncorrected": "U", "not_validated": "NV"}
    for fid, label in families.items():
        out = {"family_id": fid, "substantive_family": label}
        for run in runs:
            rid = run["run_id"]
            if run["status"] == "planned":
                out[rid] = "NOT RUN"
                continue
            _, result, _, complete_mapping = loaded[rid]
            members = links.get((rid, fid), [])
            if not members:
                out[rid] = "ABSENT" if complete_mapping else "UNRESOLVED"
                continue
            entries = []
            for member in members:
                cid = member["candidate_id"]
                item = result.get(cid)
                prefix = "DRAFT " if member["mapping_status"] == "draft" else ""
                if item is None:
                    value = "SKIP"
                else:
                    value = f"{tiers[item['tier']]} {100 * item['mean_effect']:+.2f}pp"
                entries.append(f"{prefix}{value} ({member['relation']}; {cid})")
            out[rid] = " | ".join(entries)
        output.append(out)
    return output


def presence_table(runs, memberships, stage="validated"):
    """Combined real/placebo exhibit: counts above substantive check/dash rows.

    Check means at least one mapped member passed primary validation (or was
    proposed in the companion proposal table). Draft semantic mappings remain
    provisional. Unrun and unresolved cells must never masquerade as null results.
    """
    if stage not in {"validated", "proposed"}:
        raise ValueError("presence stage must be validated or proposed")
    families, links, loaded = _load_crosswalk(runs, memberships)
    counts = [
        ("n_proposed", "Candidates suggested"),
        ("n_measured", "Candidates measured"),
        ("n_validated", "Candidates validated (q=.05)"),
        ("n_suggestive", "Suggestive only (q=.10 tier)"),
        ("n_families", "Families with validated candidates (mapping provisional if draft)"),
    ]
    output = [{"family_id": key, "substantive_family": label} for key, label in counts]
    for run in runs:
        rid = run["run_id"]
        if run["status"] == "planned":
            for row in output:
                row[rid] = "NOT RUN"
            continue
        candidates, results, mapped, _ = loaded[rid]
        validated = {cid for cid, item in results.items() if item["tier"] == "confirmed"}
        mapped_ids = {member["candidate_id"] for member in mapped}
        # No unexpected placebo survivor may disappear because it is absent
        # from a real-run family registry. It must be mapped to a new/existing row.
        if validated - mapped_ids:
            raise ValueError(f"{rid}: map every validated candidate, including placebo-only features")
        values = [len(candidates), len(results), len(validated),
                  sum(item["tier"] == "suggestive" for item in results.values()),
                  len({member["family_id"] for member in mapped if member["candidate_id"] in validated})]
        for row, value in zip(output, values):
            row[rid] = value
    for fid, label in families.items():
        row = {"family_id": fid, "substantive_family": label}
        for run in runs:
            rid = run["run_id"]
            if run["status"] == "planned":
                row[rid] = "NOT RUN"
                continue
            candidates, results, mapped, adjudicated = loaded[rid]
            members = links.get((rid, fid), [])
            if stage == "validated":
                present = any(results.get(member["candidate_id"], {}).get("tier") == "confirmed"
                              for member in members)
                # Even an unmapped zero-survivor placebo is known to have no
                # validated member in any family; no semantic guess is needed.
                row[rid] = "✓" if present else "–"
            else:
                covered = {member["candidate_id"] for member in mapped} == set(candidates)
                row[rid] = "✓" if members else ("–" if adjudicated or covered else "?")
        output.append(row)
    return output


def write_crosswalk(runs, memberships, output):
    rows = crosswalk(runs, memberships)
    with Path(output).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["family_id", "substantive_family"] + [r["run_id"] for r in runs])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_presence_table(runs, memberships, output, stage="validated"):
    rows = presence_table(runs, memberships, stage=stage)
    with Path(output).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["family_id", "substantive_family"] + [r["run_id"] for r in runs])
        writer.writeheader()
        writer.writerows(rows)
    return rows
