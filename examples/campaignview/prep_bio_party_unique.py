"""Prepare one CampaignView biography per linked candidate or duplicate-text group.

The original preparation and saved runs are preserved. This input is for a fresh
analysis with no shared recorded identities or normalized texts across partitions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

import pandas as pd

HERE = Path(__file__).resolve().parent


def normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def normalize_name(value):
    return "".join(c for c in normalize_text(value) if c.isalnum())


def row_tokens(row):
    """Use all available links, including name matches across districts/states."""
    tokens = []
    for field, prefix in (("FECCandID", "fec"), ("BIOGUIDE_id", "bioguide")):
        value = row.get(field)
        if pd.notna(value) and str(value).strip():
            tokens.append((prefix, str(value).strip().upper()))
    name = normalize_name(row["candidate_webname"])
    if name:
        tokens.append(("name", name))
    text = normalize_text(row["biography_text"])
    if text:
        tokens.append(("text", hashlib.sha256(text.encode("utf-8")).hexdigest()))
    return tokens


def eligible_rows(source):
    frame = pd.read_csv(source)
    frame["source_row"] = range(1, len(frame) + 1)
    frame = frame[frame.cand_party.isin(["Republican", "Democrat"])].copy()
    frame["biography_text"] = frame.biography_text.fillna("").str.strip()
    frame = frame[(frame.biography_text.str.len() >= 100) & frame.win_primary.isin([0, 1])].copy()
    frame["id"] = (frame.candidate_webname.astype(str) + "_" + frame.state_postal.astype(str)
                   + "_" + frame.cd.astype(str) + "_" + frame.year.astype(str))
    frame = frame.drop_duplicates("id", keep="first").reset_index(drop=True)
    frame["group"] = (frame.cand_party == "Republican").astype(int)
    return frame


def select_unique(frame):
    """Link transitively, then select by year/source order without using results."""
    parent = list(range(len(frame)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    links = Counter()
    for i, row in enumerate(frame.to_dict("records")):
        for token in row_tokens(row):
            if token in seen:
                a, b = find(i), find(seen[token])
                if a != b:
                    parent[a] = b
                links[token[0]] += 1
            else:
                seen[token] = i
    components = {}
    for i in range(len(frame)):
        components.setdefault(find(i), []).append(i)

    keep, lineage = [], []
    mixed_components = mixed_rows = 0
    for indices in components.values():
        rows = frame.iloc[indices]
        component_id = hashlib.sha256("\n".join(sorted(rows.id)).encode("utf-8")).hexdigest()[:16]
        mixed = rows.group.nunique() > 1
        if mixed:
            # Avoid choosing the party label of a mixed-party identity/text group.
            chosen = None
            mixed_components += 1
            mixed_rows += len(rows)
        else:
            chosen = rows.sort_values(["year", "source_row"], kind="stable").index[0]
            keep.append(chosen)
        for i in indices:
            lineage.append({
                "source_row": int(frame.loc[i, "source_row"]),
                "component_id": component_id,
                "component_size": len(indices),
                "retained": i == chosen,
                "retained_source_row": int(frame.loc[chosen, "source_row"]) if chosen is not None else None,
                "reason": "mixed_party_component" if mixed else ("retained" if i == chosen else "linked_duplicate"),
            })
    retained = frame.loc[keep].sort_values("source_row").copy()
    # Independently check that no retained rows share any of the link tokens.
    retained_tokens = set()
    for row in retained.to_dict("records"):
        tokens = set(row_tokens(row))
        if retained_tokens.intersection(tokens):
            raise ValueError("Retained biographies still share an identity or text")
        retained_tokens.update(tokens)
    report = {
        "eligible_candidate_year_rows": len(frame),
        "linked_components": len(components),
        "mixed_party_components_excluded": mixed_components,
        "mixed_party_rows_excluded": mixed_rows,
        "other_linked_rows_removed": len(frame) - mixed_rows - len(retained),
        "retained_biographies": len(retained),
        "retained_by_party": {"Republican": int((retained.group == 1).sum()),
                              "Democrat": int((retained.group == 0).sum())},
        "repeated_link_tokens_by_type": dict(sorted(links.items())),
        "shared_retained_identity_or_text_tokens": 0,
    }
    return retained, pd.DataFrame(lineage).sort_values("source_row"), report


def prepare(source, out_path, lineage_path, report_path):
    retained, lineage, report = select_unique(eligible_rows(source))
    out_path, lineage_path, report_path = map(Path, (out_path, lineage_path, report_path))
    for path in (out_path, lineage_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id": retained.id, "text": retained.biography_text, "group": retained.group}).to_csv(
        out_path, index=False, encoding="utf-8", lineterminator="\n")
    lineage.to_csv(lineage_path, index=False, encoding="utf-8", lineterminator="\n")
    report.update({
        "rules": {
            "initial_inclusion": "Same party, text-length, primary-result and candidate-year rules as prep_bio_party.py",
            "links": ["FEC candidate ID", "BIOGUIDE ID", "normalized full name across all states and districts",
                      "normalized biography text"],
            "normalization": "Unicode NFKC, casefold and collapsed whitespace; names retain only alphanumeric characters",
            "transitive_links": True,
            "representative": "Earliest election year; ties use original source-row order",
            "mixed_party_components": "Exclude the entire component",
            "selection_uses_model_outputs": False,
            "identity_limit": "Recorded links are not an externally verified person registry. Name matches can conservatively merge different people; unknown aliases without shared identifiers may remain.",
        },
        "sha256": {"source": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                   "prepared_data": hashlib.sha256(out_path.read_bytes()).hexdigest(),
                   "lineage": hashlib.sha256(lineage_path.read_bytes()).hexdigest(),
                   "preparation_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    })
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HERE / "data/source/biographical_narratives.csv")
    parser.add_argument("--out", type=Path, default=HERE / "data/bio_party_unique.csv")
    parser.add_argument("--lineage", type=Path, default=HERE / "data/unique_biography_rows.csv")
    parser.add_argument("--report", type=Path, default=HERE / "data/unique_biography_preparation.json")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.out, args.lineage, args.report), indent=2))


if __name__ == "__main__":
    main()
