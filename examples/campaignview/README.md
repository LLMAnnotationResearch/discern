# Campaign biographies: how do candidates present their qualifications to lead?

This example compares campaign-website biographies of Republican and Democratic candidates for
the U.S. House in 2018, 2020, and 2022. What experience, achievements, and relationships do candidates
emphasize when introducing themselves to voters? It shows how `discern` moves from texts to explicit
features, measurement questions, and estimates of group differences.

The supplied runs are the ones used in the proposal's CampaignView example and Appendix F:

| Saved run | Hypotheses | Candidates measured | Validated (5% FDR) | Suggestive only (10% FDR) | Uncorrected only |
| --- | ---: | ---: | ---: | ---: | ---: |
| `real_r1` | 204 | 65 | 47 | 2 | 0 |
| `placebo_r0` | 182 | 77 | 0 | 0 | 3 |

## Reproduce the saved results

From the repository root, after `python -m pip install -e .`:

```bash
python examples/campaignview/verify_saved_results.py
```

No API keys or network access are needed. The script checks file hashes, rebuilds the prepared data
from the raw CSV, reconstructs both partitions, checks discovery/measurement separation and group
labels, and recomputes all effects, permutation p-values, and selection tiers from the saved
classifications. It also verifies every row of the two exported feature tables. It leaves the saved
files unchanged.

A successful check ends with `Both runs verified. No API calls made.` It checks the statistics
conditional on the recorded model answers. A fresh model run can produce different answers.
The [version record](../../docs/REPRODUCIBILITY.md) distinguishes recorded historical information
from the environment used to verify these files.

## Read the results

Start with [features.real.csv](features.real.csv). It contains all 65 candidates, including those
that failed validation, with full definitions, exact classification questions, prevalence in each
group, half-specific differences, and unadjusted permutation p-values. Positive differences mean
greater prevalence among Republicans. The proposal highlights eight of the validated features:

| Feature | More common among | Difference (percentage points) |
| --- | --- | ---: |
| Collaborative problem-solving and consensus-building | Democrats | 39.7 |
| Collective action and community empowerment | Democrats | 30.3 |
| Religious faith or motivation | Republicans | 29.0 |
| Business/entrepreneurial background | Republicans | 23.3 |
| Self-made achievement versus institutional support | Republicans | 18.7 |
| Personal adversity, minority, or immigrant background | Democrats | 18.7 |
| Military service | Republicans | 14.0 |
| Educational achievement from prestigious institutions | Democrats | 10.0 |

These are rounded magnitudes in the named direction. Definitions and questions in the CSV are
verbatim model outputs. Read the questions when assessing a feature: for example, self-made
achievement uses an A-versus-B question even though the requested answer is binary. Statistical
selection alone does not establish that such a question measures a single construct accurately.

To inspect individual classifications, find a `feature_id` in the CSV and look it up in
`saved/real_r1/03_measured.json`. Its `y` answers and `model_assignment` entries follow the
`measurement_uids` order in `00_partition.json`. Join these IDs to `id` in
[data/bio_party.csv](data/bio_party.csv) to read the texts. Check both positive and negative answers.
The complete summaries are in [saved/real_r1/05_summary.md](saved/real_r1/05_summary.md) and
[saved/placebo_r0/05_summary.md](saved/placebo_r0/05_summary.md).

The placebo uses shuffled group labels. Its [feature table](features.placebo.csv) describes the
artificial groups; its positive and negative directions are not party differences. The original
party names in its archived summary are output labels, not the labels tested.

## Data and design

CampaignView is an openly released dataset by Porter, Case, and Treul. The supplied raw file and
prepared input can be redistributed under CC0. [Data source, preparation, and citation](DATA_SOURCE.md)
describes the inclusion rules and links to the release.

The prepared file contains 5,105 candidate-year biographies: 2,600 Republican (`group=1`) and
2,505 Democratic (`group=0`). Each run reserves the same 300 biographies per party for measurement;
the remaining 4,505 form the discovery pool. Measurement is split into two halves with 150 texts
per active group in each half. The placebo halves are stratified on shuffled labels.

Both runs use eight discovery calls per half, with 15 texts per group per call. Discovery and
measurement use GPT-4o-mini, Claude Haiku 4.5, and GPT-4.1-mini; consolidation uses GPT-4.1.
The full settings and seeds are saved in `config.real.json` and `config.placebo.json`. The
1,000-permutation floor increases to 1,300 for the 65 real candidates and 1,540 for the 77 placebo
candidates. Selection requires nonzero same-sign differences and passes the multiple-testing
correction across all measured candidates.

Assignments are balanced by design. In the real run, 237 failed Claude classifications and one
failed GPT-4.1-mini classification were completed by another model. Thus actual assignments can
become unbalanced after fallback. The recorded measurements identify the classifier used, and
`events.jsonl` records the failures and fallbacks. No candidate was skipped in either run.

Party affiliation is often explicit in the text; A/B prompt labels do not hide that information.
Many large differences recover partisan identity. The other features describe sampled biographies,
which reflect both backgrounds and self-presentation. Candidates can recur across election cycles;
the candidate-year analysis does not account for clustering by person. Treat the inferential results
as a demonstration under the implemented exchangeability assumption, not a causal or clustered
population analysis. Human validation remains separate work.

## Run discovery and measurement again

```bash
# No API calls:
discern run --config examples/campaignview/config.real.json --dry-run
discern run --config examples/campaignview/config.placebo.json --dry-run

# Paid API calls, requiring OpenAI and Anthropic credentials:
discern run --config examples/campaignview/config.real.json
discern run --config examples/campaignview/config.placebo.json
```

The commands work from the repository root. Paths resolve relative to each config. New results go
to `examples/campaignview/fresh_runs/`; the supplied `saved/` folders are kept separate. Repeat the
same command to resume an interruption. Measurement needs 39,000 calls for the real run and 46,200
for the placebo before retries. Costs depend on biography length and provider prices. Recorded
model snapshots may eventually be retired; substituting models creates a new analysis.

## Files

| Path | Purpose |
| --- | --- |
| `data/source/biographical_narratives.csv` | Unchanged CampaignView source file |
| `data/bio_party.csv` | Exact prepared input for both runs |
| `prep_bio_party.py` | Reconstruct the input, including its recorded line endings |
| `config.real.json`, `config.placebo.json` | Complete portable settings for new runs |
| `saved/real_r1/`, `saved/placebo_r0/` | Configurations, partitions, model IDs, all stages, and audit logs |
| `features.real.csv`, `features.placebo.csv` | Complete candidate tables in reading order |
| `checksums.json` | SHA-256 hashes of data, settings, exports, and saved artifacts |
| `verify_saved_results.py` | Offline data and statistics check |

Archived `00_config.json` files had machine-specific locations replaced with relative paths before
this package was prepared. Their original `spec_hash` identifies the original run environment and
paths and is retained as provenance. Use the portable configs for a new run; do not try to resume
inside `saved/`. No answers, candidate definitions, or selections were changed for this release.
