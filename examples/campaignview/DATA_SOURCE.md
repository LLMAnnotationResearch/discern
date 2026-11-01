# CampaignView data

Porter, R. A., Case, C. R., and Treul, S. A. (2025). CampaignView, a database of policy platforms
and biographical narratives for congressional candidates. Scientific Data.

- [Dataset: Harvard Dataverse, doi:10.7910/DVN/JIEAPT](https://doi.org/10.7910/DVN/JIEAPT)
- [Published documentation](https://doi.org/10.1038/s41597-025-05491-x)
- [CC0 1.0 Universal dedication](https://creativecommons.org/publicdomain/zero/1.0/)

The source file matches dataset version 1.1, released 19 August 2025, as verified
against the Dataverse metadata on 1 November 2026. The file
`data/source/biographical_narratives.csv` is supplied unchanged (15,750,112 bytes).
The release uses CC0 1.0; the source attribution is retained here. This data dedication is separate
from the MIT license for the software.

`prep_bio_party.py` keeps Republican and Democratic candidates with a recorded primary result
(`win_primary` equal to 0 or 1), trims surrounding whitespace, drops biographies shorter than
100 characters, and keeps the first row per candidate-year ID. The primary outcome is only an
inclusion rule. It is not the contrast tested. The ID combines candidate name, state, district,
and year. Names are public candidate identifiers from the source dataset.

The result contains 5,105 rows: 2,600 Republican and 2,505 Democratic biographies. The three
columns are `id`, `text`, and `group` (1=Republican; 0=Democrat). Candidate-year records can
repeat the same person in different elections. Texts retain explicit party references.

To reconstruct the exact prepared file without replacing it:

```bash
python examples/campaignview/prep_bio_party.py --out /tmp/rebuilt-bio-party.csv
```

The script explicitly writes CRLF record endings to match the saved Windows-generated input.
Embedded text and row order are preserved. The offline verifier checks equality of the rebuilt
file's bytes, in addition to the hashes in `checksums.json`. This matters because the data
fingerprint and cache identity depend on file bytes.

## Input used in the current proposal

The current walkthrough uses `data/bio_party_unique.csv`, reconstructed by
[prep_bio_party_unique.py](prep_bio_party_unique.py). It starts with the same 5,105 eligible
records described above, then links records that share an FEC candidate ID, BIOGUIDE ID,
normalized full name across all states and districts, or normalized whole biography text.
Links are transitive. Retain the earliest available biography per linked group; break ties
by original source-row order. Exclude a linked group if its records have different party labels.
These rules use source data only and were fixed before the new model calls.

The resulting input has 3,961 biographies: 2,049 Republican and 1,912 Democratic. The
[row-level inclusion record](data/unique_biography_rows.csv) and
[preparation record](data/unique_biography_preparation.json) document every exclusion and the
source and prepared-file hashes. The [walkthrough](README.md) explains normalization, matching
limits, the overlap checks, and how to reproduce both complete runs.

The original `data/bio_party.csv` and [original runs](ORIGINAL_RUN.md) remain available as
historical records. Their data and saved statistical results have not been changed.
