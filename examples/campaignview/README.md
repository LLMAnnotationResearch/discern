# Campaign biographies: how do candidates present their qualifications to lead?

This example compares campaign-website biographies of Republican and Democratic candidates for
the U.S. House in 2018, 2020, and 2022. What experience, achievements, and relationships do candidates
emphasize when introducing themselves to voters? It shows how `discern` moves from texts to explicit
features, measurement questions, and estimates of group differences.

These are the runs used in the proposal's CampaignView example and Appendix F. The input retains
one biography per linked candidate or duplicate-text group. The [original candidate-year runs](ORIGINAL_RUN.md)
are preserved for comparison.

The original analysis kept different election-year biographies for the same person. A split by
row could therefore put one of a person's biographies in discovery and another in measurement.
The new preparation retains one biography per linked candidate or duplicate-text group before
any discovery or measurement split. This also removes repeated identities and duplicate texts
between the two measurement halves.

## How biographies are selected

Start with the same 5,105 eligible candidate-year records as the original example. Link records
that share any of the following:

- FEC candidate ID;
- congressional BIOGUIDE ID;
- normalized full candidate name, across all states and districts;
- normalized biography text.

Links are transitive: if one row shares an FEC ID with a second row and that second row shares a
BIOGUIDE ID with a third, all three belong to the same group. Normalization uses Unicode NFKC,
case folding, and collapsed whitespace; name matching also removes punctuation and spaces.
This checks whole-text duplicates, not similarities in subject matter or short shared phrases.

Within each linked group, retain the earliest available election-year biography; ties use the
original source-row order. Exclude a linked group entirely if its records have different party
labels. These rules use source data only. They do not use model answers or statistical results.

The preparation yields 3,961 biographies: 2,049 Republican and 1,912 Democratic. It excludes
32 rows in 14 mixed-party groups and removes 1,112 other linked rows. The
[row-level record](data/unique_biography_rows.csv) gives the original source-row position
(counting data rows from 1, excluding the header),
linked-group ID, inclusion decision, and retained source row for every eligible record.
[The preparation record](data/unique_biography_preparation.json) includes counts, rules, and hashes.

Names are matched conservatively, so different people with the same normalized name can be
combined. Conversely, unrecorded aliases without a shared identifier may remain unrecognized.
The zero-overlap finding concerns the recorded identifiers, normalized names, and normalized
whole texts; it is not an independent verification of every candidate's identity.

## Settings

The [saved plan](unique_run_plan.json) fixes the comparison before the new model calls. The
model pool and pinned snapshots, prompts, seeds, eight discovery calls per half, 15 texts per
party per call, and statistical selection rules match the original runs. Each new run reserves
600 biographies for measurement, with 150 per active label in each measurement half; 3,361
biographies remain in discovery. The placebo shuffles labels and repeats discovery,
consolidation, and measurement.

This is a fresh end-to-end analysis. It does not reuse the original candidate list or model
classifications. Differences from the original results can reflect both the changed input and
variation in model responses.

## Inspect and reproduce the saved results

| Run | Hypotheses | Candidates measured | Validated (5% FDR) | Suggestive only (10% FDR) | Uncorrected only |
| --- | ---: | ---: | ---: | ---: | ---: |
| Real party labels | 193 | 72 | 50 | 1 | 0 |
| Shuffled labels | 180 | 53 | 0 | 0 | 4 |

All 125 candidates were measured. Selection used 1,440 permutations for the real run and 1,060
for the placebo after the pipeline's automatic resolution adjustment. Every effect, p-value,
selection tier, and feature-table row reproduces from the saved classifications. The overlap
audit finds zero shared FEC IDs, BIOGUIDE IDs, normalized names, or normalized whole texts
within or between discovery and the two measurement halves in either run.

The placebo is one full-pipeline check for this corpus and configuration. Its zero validated
features do not establish calibration across other settings. Statistical selection concerns
measured differences in text; it does not establish coding accuracy or causal explanations.

Read the [complete real-run summary](../sample-output/campaignview-unique.md) and
[placebo summary](saved_unique/placebo_r0/05_summary.md). The complete feature tables include
definitions, measurement questions, prevalence estimates, effects, p-values, and selection tiers
for the [real comparison](features.unique.real.csv) and [placebo](features.unique.placebo.csv).

```bash
python examples/campaignview/verify_unique_results.py
```

This makes no API calls. It rebuilds the input in a temporary directory, verifies hashes and
partitions, audits overlap, and recomputes every saved effect, permutation p-value, and selection
tier from the recorded classifications. It also checks every exported feature-table row.
The [verification record](verification.unique.json) reports the results of these checks.

Every saved stage is in [saved_unique/](saved_unique/). Each run records its original software
environment in `00_environment.json` and exact returned model IDs in `00_runspec.json`.
The [execution record](execution.unique.json) includes all installed package versions, operational
settings, and combined token usage. The production pipeline was run through
`scripts/run_validation_batch.py`, with separate caches for the two conditions.

Across both runs, recorded usage was 54.2 million input and 0.71 million output tokens. At standard
uncached API rates checked on November 1, 2026, that usage gives an illustrative estimate of
US$30.55 combined. The [cost record](cost.unique.json) gives each model's usage, rates, sources,
and calculation. It is not an invoice total: cached-input discounts, unrecorded or failed requests,
taxes, and local computing are not included.

This example currently includes one full-pipeline placebo. Extending repeated placebos,
stability checks, and alternative-method comparisons to these public data is planned for Stage 2.

Machine-specific locations in the archived `00_config.json` files were replaced with relative
paths. Their original run-spec hashes are preserved. All other copied run artifacts, including
the answers, candidates, selections, summaries, and audit logs, are unchanged. Use the portable
`config.unique.*.json` files below for fresh runs.

## Read the selected examples

The proposal's Figure 2 shows eight validated features about qualifications and self-presentation.
They are illustrative choices, rather than the eight largest effects. All 72 candidates are
included in Appendix F and the complete feature table.

| Feature | More common among | Difference (percentage points) |
| --- | --- | ---: |
| Listening to Community Members and Centering Their Voices | Democrats | 27.3 |
| Direct Personal Experience with Policy Problems | Democrats | 20.3 |
| Education as Personal Transformation | Democrats | 18.3 |
| Simultaneous Work and Study | Democrats | 10.7 |
| Religious Faith or Affiliation | Republicans | 27.0 |
| Business Ownership or Entrepreneurship | Republicans | 22.3 |
| Military or Law Enforcement Background | Republicans | 12.3 |
| Individual Achievement and Self-Made Success | Republicans | 7.7 |

These are rounded magnitudes in the named direction. Names, definitions, and measurement questions
in the saved results are unchanged. To inspect individual classifications, find a `feature_id` in
`features.unique.real.csv`, look it up in `saved_unique/real_r1/03_measured.json`, and join its answers
to the source biographies using `measurement_uids` in `00_partition.json` and `id` in
`data/bio_party_unique.csv`. Check both positive and negative classifications.

The placebo's directions describe shuffled groups, not party differences. Party names in its
summary are output labels. The original labels are not the labels tested.

[display_features.unique.json](display_features.unique.json) records the eight display choices.
To export the same LaTeX figure and full appendix from the saved results:

```bash
python examples/campaignview/export_proposal.py --out-dir /tmp/campaignview-tables
```

## Reproduce the preparation and check the split

From the repository root, after installing the package:

```bash
python examples/campaignview/prep_bio_party_unique.py
python examples/campaignview/verify_unique_results.py --preflight
discern run --config examples/campaignview/config.unique.real.json --dry-run
discern run --config examples/campaignview/config.unique.placebo.json --dry-run
```

The preflight check makes no API calls. It reconstructs the prepared input and row-level
inclusion record, then checks candidate identifiers, normalized names, and duplicate texts
within and between discovery and both measurement halves. Every overlap count must be zero.

## Run the models again

These commands require OpenAI and Anthropic credentials and use paid APIs:

```bash
discern run --config examples/campaignview/config.unique.real.json
discern run --config examples/campaignview/config.unique.placebo.json
```

The two configurations use separate output and cache directories under `fresh_runs/`.
Saved results are kept separately. A fresh API run can produce different features or labels.
Exact software versions and model responses are recorded with each completed run.
