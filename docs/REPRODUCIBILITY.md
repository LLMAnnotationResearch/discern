# Settings and software record

CampaignView is the public reproduction example. Its data, configurations, model records, and
complete real and placebo outputs are included. The final section documents the proposal's
supporting Hurst analyses, whose restricted data are not included.

## Public example: CampaignView

From the repository root, after installation:

```bash
# Reconstruct the data and recompute both saved runs without API calls:
python examples/campaignview/verify_saved_results.py

# Check the settings and partitions for fresh runs without API calls:
discern run --config examples/campaignview/config.real.json --dry-run
discern run --config examples/campaignview/config.placebo.json --dry-run
```

Use [config.real.json](../examples/campaignview/config.real.json) and
[config.placebo.json](../examples/campaignview/config.placebo.json) for full model reruns. Each file
records all settings, including seeds, rather than relying on defaults. The original settings and
model responses are retained under [saved/](../examples/campaignview/saved/). Fresh runs write to
a separate folder. See the [walkthrough](../examples/campaignview/README.md) for instructions and
interpretation.

### Package defaults and CampaignView settings

| Setting | Package defaults | Saved CampaignView runs |
| --- | --- | --- |
| Discovery and rotation pool | Reference + DeepSeek | Reference |
| Consolidation | GPT-4.1 | GPT-4.1 |
| Discovery calls per half | 15 | 8 |
| Texts per group per discovery call | 15 | 15 |
| Reserved texts per group | 250 | 300 |
| Permutation floor | 2,000 | 1,000 |
| Primary / exploratory FDR | .05 / .10 | .05 / .10 |
| Prompt version | `discern-1` | `discern-1` |
| Theme organization | Off | Off |

The reference pool is GPT-4o-mini, Claude Haiku 4.5, and GPT-4.1-mini. Discovery uses the relaxed
prompt at temperature .7; consolidation and classification use temperature 0. Initial model
assignment is balanced within group and half. Recorded fallbacks can change the actual balance.
Gemini is outside these pools, and assignment is not cost weighted.

Selection uses 1,300 permutations for the 65 real candidates and 1,540 for the 77 placebo
candidates after automatic resolution adjustment. All candidates were measured in both runs.
Every measured candidate enters the multiple-testing correction. The real run retained 47 validated
and two suggestive features; the placebo retained neither tier and had three uncorrected tendencies.

### Exact model identifiers

| Package key | Requested snapshot | Role in CampaignView |
| --- | --- | --- |
| `gpt-4o-mini` | `gpt-4o-mini-2024-07-18` | Discovery and measurement |
| `claude-haiku` | `claude-haiku-4-5-20251001` | Discovery and measurement |
| `gpt-4.1-mini` | `gpt-4.1-mini-2025-04-14` | Discovery and measurement |
| `gpt-4.1` | `gpt-4.1-2025-04-14` | Consolidation |

The original [real model record](../examples/campaignview/saved/real_r1/00_runspec.json) and
[placebo model record](../examples/campaignview/saved/placebo_r0/00_runspec.json) preserve returned
identifiers and fingerprints. The package defaults additionally select `deepseek`, which requests
the floating alias `deepseek-chat`. That model was not used in these CampaignView runs.

Pinned snapshots still permit nondeterministic responses. Aliases, local tags, and gateways can
also change underneath the same name. Saved records describe completed runs; they do not establish
that providers still offer those models. The offline check needs no model availability probes.

### Software versions and the historical gap

The saved CampaignView runs record package `0.1.0`, prompt `discern-1`, exact model snapshots,
settings, and classifications. They do not record the original Python and dependency versions or
an exact source revision. Those missing versions have not been inferred from a later environment.

The environment used to verify the public example is recorded separately in
[verification_environment.json](submission/verification_environment.json). Source hashes identify
the package code used for that verification. This is the verification environment, not the original
empirical environment. The offline check reproduces both runs' saved statistics from their recorded
classifications; a fresh API rerun need not reproduce individual model answers.

## Recording future runs

New pipeline executions save Python, direct dependency versions, platform, and package source hashes
in `00_environment.json`. Each execution, including a resume, appends its environment to
`events.jsonl`; the first environment record is preserved. A legacy run first captured on resume
has `capture_context=resume`. Records omit user names, host names, executable paths, and credentials.
Retain a complete environment export separately when preparing new empirical results, including
model weights and serving software for local models.

The original `00_runspec.json` model record is also preserved on resume. New model-version probes
are appended as `execution_models` audit events, so a changed hosted alias does not replace the
original provenance. Resumed runs can contain classifications from multiple executions; retain
the audit and cache and use a new output directory for a clean rerun with changed models.

## Supporting manuscript analyses: restricted Hurst data

These records document additional evidence reported in the supplement. They are not a public
reproduction example: the Hurst respondent texts and row-level survey scores cannot be shared.
The public files alone cannot reproduce those analyses.

### Run settings and results

The [run catalog](submission/run_catalog.json) maps the supplement's analyses to
[configs](submission/configs/), [model records](submission/model_versions/), and aggregate
[candidate results](submission/candidate_results/). `A_MAIN`, `B_REPEAT`, `C_DEFAULTS`, and
`D_OPENAI` are the main, same-pool, default-pool, and OpenAI-only columns. P01–P05 are full-pipeline
placebos. They use 15 discovery calls per half, 15 texts per group per call, 400 reserved texts
per group, and 5,000 permutations.

The reference pool matches CampaignView's three-model pool. The default-pool comparison adds
DeepSeek; OpenAI-only uses GPT-4o-mini and GPT-4.1-mini. Consolidation uses GPT-4.1. The default-pool
run changed both discovery and measurement pools, so differences cannot be attributed to either
stage alone. Its config retains the extra residual duplicate pass (`residual_dedup=true`).

The default-pool run resolved `deepseek-chat` to `deepseek-flash`, fingerprint
`e72d3c7f663d3e1383b00b3884cb4501`. This is a recorded provider response, not a pinned model ID.
All empirical runs record package `0.1.0` and prompt `discern-1`; those tags alone do not identify
every historical source edit.

Across the nine Hurst runs, 317 candidates were proposed and 316 measured. P03 proposed 42 and
measured 41; [unmeasurable_candidates.json](submission/unmeasurable_candidates.json) records the
missing candidate. A skipped candidate is not a nonsignificant result. Repeated real runs reuse
the held-out responses, and thematic matching is post hoc; these are sensitivity checks rather
than independent replications on new respondents.

Paths in the public configs were normalized, with original config hashes retained in the catalog.
They expect an authorized prepared CSV at `restricted/run3_tall_sex.csv` relative to the config
folder. That CSV is not included. These configs preserve the research specification for readers
who obtain authorized access; they are not commands for the public walkthrough.

### Recorded dependency versions

| Analysis | Recorded information | Missing information |
| --- | --- | --- |
| Archived Hurst main run | Package `0.1.0`, prompt, model snapshots, settings, classifications | Original Python and dependency versions; exact source revision |
| October Hurst repeats and placebos | NumPy `2.3.5`, pandas `2.2.3`, OpenAI SDK `3.38.0`, Anthropic SDK `0.125.0`, model records and batch source hashes | Full resolved dependency environment and Python version |
| Conventional-method comparison | NumPy `2.3.5`, pandas `2.2.3`, scikit-learn `1.9.1`, SciPy `1.18.1`, VADER `3.3.2`, joblib `1.6.0`, Empath `0.89`, requests `2.34.2`; dictionary and code hashes | Full resolved dependency environment and Python version |

The two `requirements.*-recorded.txt` files in [submission](submission/) preserve the observed
versions. They are partial records, not complete lockfiles or a claim that installing them recreates
an undocumented historical environment. Current install requirements remain in `pyproject.toml`.

### Conventional-method settings

[baseline_settings.json](submission/baseline_settings.json) preserves the Hurst analysis plan,
versions, LDA tuning results, VADER lexicon hashes, and Empath dictionary hashes. Paths to private
pilot folders were removed. The main comparison uses 794 common evaluable responses; six of the
800 held-out responses have no retained LDA vocabulary. Full-sample results are a separate
sensitivity analysis. Scores retain their native scales.

LDA selected K=5 from 5/10/15/20 by discovery-only validation perplexity. Vocabulary fitting and
model selection excluded held-out responses. Empath tests all 194 supplied categories, with
package-default tokenization as a sensitivity check. Empath is not LIWC. Human evaluation of
question fidelity and classification accuracy is separate from these comparisons. These are Hurst
results; equivalent stability and conventional-method comparisons have not been run on CampaignView.

### Restricted survey reconstruction

[prepare_hurst_validation.py](../scripts/prepare_hurst_validation.py) documents the source columns,
inclusion rules, and original row order. It requires the restricted source survey and archived runs.
The prepared primary contrast has 2,832 nonblank women/men responses on tall hierarchies: 800 held
out and 2,032 in discovery. Source IDs are spreadsheet row positions (data-row index + 2), not
original respondent identifiers. The prepared CSV SHA-256 is
`0bd4ad4118d898f56c37f735100f5c03c29a721b5aa69f08c0428b81ee5a0777`.

The source export contains 8,692 rows, while the published attention-check sample has 8,498.
The reconstruction matches archived Discern inclusion, not every published exclusion. Mechanism
scales, founder-gender blocks, and attention-check fields are absent from this export. No respondent
texts or row-level survey scores are included in the public package.
