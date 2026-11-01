"""Repeated candidate identities and texts must not survive the new preparation."""
import importlib.util
from pathlib import Path

import pandas as pd

SPEC = importlib.util.spec_from_file_location(
    "campaignview_unique", Path(__file__).resolve().parents[1] / "examples/campaignview/prep_bio_party_unique.py")
unique = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(unique)


def row(i, name, text, fec=None, bioguide=None, year=2022, group=1):
    return {"source_row": i, "id": f"row-{i}", "candidate_webname": name,
            "biography_text": text, "FECCandID": fec, "BIOGUIDE_id": bioguide,
            "year": year, "group": group}


def test_transitive_identities_and_normalized_texts_use_one_representative():
    frame = pd.DataFrame([
        row(1, "Alex Jones", "First text", fec="H0XX00001", year=2022),
        row(2, "A. Jones", "Second text", fec="H0XX00001", bioguide="J000001", year=2020),
        row(3, "Alexandra Jones", "Third text", bioguide="J000001", year=2018),
        row(4, "Different Name", "  THIRD\nTEXT  ", year=2020),
        row(5, "Independent Person", "Different biography"),
    ])
    retained, lineage, report = unique.select_unique(frame)
    assert retained.id.tolist() == ["row-3", "row-5"]
    assert lineage.loc[lineage.source_row <= 4, "component_id"].nunique() == 1
    assert report["other_linked_rows_removed"] == 3


def test_names_link_across_locations_and_mixed_party_components_are_excluded():
    frame = pd.DataFrame([
        row(1, "Jane A. Doe", "First biography", year=2018),
        row(2, "JANE A DOE", "Second biography", year=2022),
        row(3, "Sam Lee", "Third biography", fec="H0XX00002", group=0),
        row(4, "Samuel Lee", "Fourth biography", fec="H0XX00002", group=1),
    ])
    retained, lineage, report = unique.select_unique(frame)
    assert retained.id.tolist() == ["row-1"]
    assert report["mixed_party_components_excluded"] == 1
    assert report["mixed_party_rows_excluded"] == 2
    assert not lineage.loc[lineage.source_row.isin([3, 4]), "retained"].any()


def test_preparation_is_deterministic_and_keeps_the_old_inclusion_rules(tmp_path):
    rows = []
    for i, name, year, party, text, win in [
        (1, "First Person", 2022, "Democrat", "word " * 30, 1),
        (2, "First Person", 2018, "Democrat", "older " * 30, 0),
        (3, "Other Person", 2020, "Republican", "other " * 30, 1),
        (4, "Third Party", 2020, "Independent", "third " * 30, 1),
        (5, "No Primary", 2020, "Republican", "missing " * 30, None),
        (6, "Short Text", 2020, "Republican", "short", 1),
    ]:
        rows.append({"candidate_webname": name, "year": year, "cand_party": party,
                     "biography_text": text, "win_primary": win, "state_postal": "XX", "cd": i})
    source = tmp_path / "source.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    reports = []
    for suffix in ("a", "b"):
        reports.append(unique.prepare(source, tmp_path / f"{suffix}.csv", tmp_path / f"{suffix}-rows.csv",
                                      tmp_path / f"{suffix}.json"))
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()
    assert reports[0] == reports[1]
    assert reports[0]["eligible_candidate_year_rows"] == 3
    assert reports[0]["retained_biographies"] == 2
    assert pd.read_csv(tmp_path / "a.csv").id.tolist() == ["First Person_XX_2_2018", "Other Person_XX_3_2020"]
