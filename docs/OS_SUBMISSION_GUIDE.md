# Organization Science reviewer guide

The research question is how to make exploratory use of text data systematic and transparent.
`discern` proposes interpretable differences between two groups, turns each into a measurement
question, and tests those differences on texts reserved before discovery. The output is a complete
candidate list with definitions, questions, estimates, and selection results. Researchers use this
evidence to develop and assess explanations.

The public demonstration uses CampaignView candidate biographies. It includes the source data,
preparation script, complete configurations, and every saved stage of a real-label run and a
placebo run. Reviewers can follow the entire procedure without access to private data.

The input retains one biography per linked candidate or duplicate-text group. The
[walkthrough](../examples/campaignview/README.md) documents the matching and inclusion rules.
An offline check verifies zero shared recorded candidate IDs, normalized names, or whole texts
across discovery and both measurement halves.

To inspect the results without running software, start with the [CampaignView example
output](../examples/sample-output/campaignview-unique.md) and [placebo
summary](../examples/campaignview/saved_unique/placebo_r0/05_summary.md). The [complete feature
table](../examples/campaignview/features.unique.real.csv) includes all 72 real-run candidates, their
definitions and questions, estimates, and selection results.

## Reproduce the CampaignView results

Use Python 3.10 or newer. Download the repository or extract the supplied reviewer archive, then
open a terminal in the folder containing `pyproject.toml`. The archive calls that folder
`discern-review`. Run:

```bash
python -m pip install -e .
python examples/campaignview/verify_unique_results.py
```

Installation downloads the software dependencies. The verification command needs no API keys or
network access and ends with `Both unique-biography runs verified. No API calls made.` It reconstructs the prepared data from the supplied source file,
checks the partitions and discovery/measurement separation, and recomputes every candidate's
effects, permutation p-value, and selection tier from the recorded classifications.

| Run | Candidates measured | Validated (5% FDR) | Suggestive only (10% FDR) | Uncorrected only |
| --- | ---: | ---: | ---: | ---: |
| Real party labels | 72 | 50 | 1 | 0 |
| Shuffled labels | 53 | 0 | 0 | 4 |

These are the CampaignView results reported in Section 3 and Appendix F. The
[walkthrough](../examples/campaignview/README.md) explains the data, selected findings, and commands
for a fresh model run. That full rerun requires OpenAI and Anthropic credentials and uses paid APIs;
it can produce different candidates or classifications. The offline check reproduces the statistics
conditional on the recorded answers. The smaller synthetic example remains in `examples/`.

## Follow one analysis from data to results

The table follows the saved real-label CampaignView run. The method is described in Section 2 and
Appendices A, C, and D; the procedure is the same for the saved placebo.

| Step | Saved input or output to inspect | Relevant code |
| --- | --- | --- |
| Prepare the data | [Source and inclusion rules](../examples/campaignview/DATA_SOURCE.md), [prepared biographies](../examples/campaignview/data/bio_party_unique.csv) | [prep_bio_party_unique.py](../examples/campaignview/prep_bio_party_unique.py) |
| Reserve measurement texts before discovery | [Partition and held-out IDs](../examples/campaignview/saved_unique/real_r1/00_partition.json) | [data.py](../src/discern/data.py) |
| Propose differences from balanced A/B samples | [Discovery calls and all proposals](../examples/campaignview/saved_unique/real_r1/01_discovery.json) | [discovery.py](../src/discern/discovery.py), P1 in [prompts.py](../src/discern/prompts.py) |
| Define distinct features and measurement questions | [Complete candidate definitions](../examples/campaignview/saved_unique/real_r1/02_consolidated.json) | [consolidate.py](../src/discern/consolidate.py), P2–P3c in [prompts.py](../src/discern/prompts.py) |
| Classify each held-out biography | [Per-text answers and actual classifiers](../examples/campaignview/saved_unique/real_r1/03_measured.json) | [measure.py](../src/discern/measure.py), `balanced_assignment` in [core.py](../src/discern/core.py) |
| Estimate differences and apply the selection rule | [All 72 feature results](../examples/campaignview/features.unique.real.csv), [full selection record](../examples/campaignview/saved_unique/real_r1/04_selected.json) | [select.py](../src/discern/select.py), `stage5` and `bh_pass` in [core.py](../src/discern/core.py) |
| Repeat the whole procedure with shuffled labels | [All 53 placebo results](../examples/campaignview/features.unique.placebo.csv), [placebo summary](../examples/campaignview/saved_unique/placebo_r0/05_summary.md) | Label shuffling in [data.py](../src/discern/data.py), stages in [pipeline.py](../src/discern/pipeline.py) |

The [saved settings and software record](REPRODUCIBILITY.md#public-example-campaignview) identifies
the exact configurations, model snapshots, software versions, and current package defaults.

## What to check in the output

Read a feature's definition and exact measurement question together. Its estimated difference is
positive when the feature is more prevalent among Republican biographies and negative when it is
more prevalent among Democratic biographies. The walkthrough explains how to join individual model
answers to the source texts so both positive and negative classifications can be inspected.

The primary selection rule requires nonzero effects with the same sign in the two held-out halves
and a permutation p-value passing Benjamini–Hochberg at 5% FDR across all successfully measured
candidates. A feature need not be significant in each half separately. Suggestive features pass only
the 10% threshold. Uncorrected tendencies pass neither FDR threshold and should not be called validated.

The full-pipeline placebo repeats discovery and measurement under shuffled labels. Its zero
validated features are evidence about this corpus and configuration, not a guarantee across all
settings. Statistical selection does not establish classification accuracy, construct validity,
or causal explanations. Human validation remains planned work. Party identity can be explicit in
the source text, and features can overlap. The input removes repeated recorded identities and
normalized duplicate texts before splitting; matching limits are described in the walkthrough.
The implemented permutations treat retained biographies as exchangeable within each measurement half.

## Supporting analyses with restricted data

Appendix B reports additional validation using the Hurst survey data, which cannot be shared.
The accompanying [manuscript records](submission/README.md) preserve settings, model records, and
aggregate feature results for transparency. Those analyses require the restricted source data and
cannot be reproduced from the public package alone. CampaignView is the public reproduction example.
Its current validation includes one full-pipeline placebo. Extending repeated placebos, stability
checks, and alternative-method comparisons to CampaignView is planned for Stage 2.

## Anonymous review copy

To create a submission copy without Git history, local manuscript drafts, private data, or contributor
metadata, run:

```bash
python scripts/build_reviewer_release.py --out /tmp/discern-review.zip
```

The builder uses an explicit file list, checks for identifying local paths and credential patterns,
and writes hashes for every included file. It preserves third-party citations and license notices,
and public candidate names in the dataset. These identify sources and subjects, not contributors.
Existing repository history and GitHub account information remain visible on the public repository;
the archive is the artifact prepared for anonymous review.
