"""Build data/bio_party.csv from the CampaignView biographical narratives.

Source: biographical_narratives.csv from the CampaignView dataset (Porter, Case & Treul, 2025,
Scientific Data), Harvard Dataverse doi:10.7910/DVN/JIEAPT, licence CC0 1.0. A copy is in
data/source/. Output: one row per candidate-year with three columns, id, text, group
(1 = Republican, 0 = Democrat), no missing values.

Rules, identical to the script used for the shipped runs:
  - keep Republican and Democrat candidates only;
  - drop biographies shorter than 100 characters (placeholder pages, fragments);
  - drop rows without a recorded primary result (win_primary not 0/1);
  - id = candidate name, state, district, year; keep the first row per id (a few duplicate scrapes).

    python prep_bio_party.py                      # writes data/bio_party.csv
    python prep_bio_party.py --out /tmp/check.csv # write elsewhere, e.g. to compare

Note: the shipped data/bio_party.csv was written on Windows and has CRLF line endings. Regenerating
it uses explicit CRLF record endings to reproduce the saved input bytes on every platform.
"""
import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
MIN_CHARS = 100


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(HERE / "data" / "source" / "biographical_narratives.csv"))
    ap.add_argument("--out", default=str(HERE / "data" / "bio_party.csv"))
    a = ap.parse_args()

    prepare(a.source, a.out)


def prepare(source, out_path):
    df = pd.read_csv(source)
    df = df[df["cand_party"].isin(["Republican", "Democrat"])].copy()
    df["biography_text"] = df["biography_text"].fillna("").str.strip()
    df = df[df["biography_text"].str.len() >= MIN_CHARS]
    df = df[df["win_primary"].isin([0, 1])]
    df["id"] = (df["candidate_webname"].astype(str) + "_" + df["state_postal"].astype(str)
                + "_" + df["cd"].astype(str) + "_" + df["year"].astype(str))
    df = df.drop_duplicates(subset="id", keep="first")

    out = pd.DataFrame({"id": df["id"], "text": df["biography_text"],
                        "group": (df["cand_party"] == "Republican").astype(int)}).dropna()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8", lineterminator="\r\n")
    counts = out["group"].value_counts().to_dict()
    print(f"wrote {out_path}: rows={len(out)} Republican={counts.get(1, 0)} Democrat={counts.get(0, 0)}")


if __name__ == "__main__":
    main()
