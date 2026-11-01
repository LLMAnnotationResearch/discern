# discern

`discern` identifies interpretable features that distinguish texts associated with two groups.
It takes a table with a text column and a group column, proposes candidate differences, and
measures those candidates on data reserved before discovery. Each feature has a definition,
a yes/no measurement question, and an estimated group difference.

The language models generate candidates; held-out measurement and replication determine which
features are retained. The researcher interprets the findings and decides which explanations
or new questions warrant further study.

The [CampaignView walkthrough](examples/campaignview/README.md) includes openly licensed data,
complete saved real and placebo runs, and an offline check of the reported results.

## Intended use

Use `discern` when you have texts from two groups and want to learn how they differ without
specifying all the relevant dimensions in advance. Examples include open-ended responses from
treatment and control participants, job postings from two types of firms, and business descriptions.
The procedure can be specified in advance as an exploratory analysis.

The output supports hypothesis development and interpretation. Statistical validation concerns
measured differences in text. Explaining why those differences arise requires theory, context,
and additional evidence. It does not establish a causal mechanism or agreement with human coding.
Features can overlap and may need further work before becoming measures of theoretical constructs.

Use one language per run and one observation per row. Each group needs enough observations for
both discovery and measurement: the default reserves 250 per group, and each discovery half must
still contain at least 15 texts per group. Sample size affects power; these are design settings,
not a guarantee of recovery. Texts must fit the selected models' context windows. See
[guidance](docs/GUIDANCE.md) for sample size, text length, and comparisons involving more than two groups.

## Install

Use Python 3.10 or newer. From a terminal:

```bash
git clone https://github.com/LLMAnnotationResearch/discern.git
cd discern
python -m pip install -e .
```

If using a downloaded reviewer archive, extract it, enter its `discern-review` folder, and run
the install command above. Required dependencies install automatically. CSV, TSV, and Excel
files are accepted; older `.xls` files also require `xlrd`.

Use a local output folder while running. Cloud synchronization can interfere with the continuously
updated cache and audit log. Set `output_dir` in a saved configuration or use
`--output-dir /path/to/local/runs`.

## Start with a saved example

From the repository root, after installation:

```bash
# Check both saved CampaignView runs without API keys or network access.
python examples/campaignview/verify_saved_results.py

# Check the configuration and data partition for a new run, without API calls.
discern run --config examples/campaignview/config.real.json --dry-run
```

The walkthrough explains the data, the full candidate list, and how to rerun discovery and
measurement. The saved real run retained 47 of 65 candidates at 5% FDR, plus two suggestive
features. The matching placebo retained zero of 77 candidates at either FDR threshold.

The smaller synthetic example is also available:

```bash
python examples/make_demo_data.py
discern run --config examples/config.real.json --dry-run
# The following commands use paid model APIs.
discern run --config examples/config.real.json
discern run --config examples/config.placebo.json
```

Other saved illustrations compare [Organization Science and Strategic Management Journal
abstracts](examples/sample-output/orgsci-vs-smj.md) and [QJE and JPE
abstracts](examples/sample-output/qje-vs-jpe.md). They are reading examples; the CampaignView
folder supplies the data and recorded classifications needed for reproduction.

## Configure API keys for a new run

Only a full model run requires credentials. Use keys for the providers selected in your
configuration. `discern setup-help` prints instructions. The default location is
`~/.config/discern/.env`, loaded automatically:

```text
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
DEEPSEEK_API_KEY=your-key
```

Keep this file outside the repository and restrict its permissions (`chmod 600` on macOS/Linux).
Set `DISCERN_ENV=/path/to/your.env` to use a different location. CampaignView uses only OpenAI
and Anthropic. The package defaults also use DeepSeek.

A model run sends texts to the selected providers. Use data you are permitted to send to those
services. A fully local model pool can instead use a local server. Saved outputs include texts,
identifiers, and model responses; store and share them according to the data's permissions.

## Run your own analysis

```bash
discern run --dataset mydata.csv --text-col description --group-col treated \
    --unit-label "survey response" --focal-label treated --reference-label control

# Or save and edit a configuration:
discern init --out myrun.json
discern run --config myrun.json --dry-run
discern run --config myrun.json
```

The group column defaults to 1 for the focal group and 0 for the reference group. Set
`focal_value` and `reference_value` for other codes. Human-readable group labels affect the
output, while `unit_label` enters the prompts and should describe what each row represents.
Paths in a saved configuration resolve relative to that file.

Read `runs/<run_name>/05_summary.md` first. A positive difference means greater prevalence in
the focal group; a negative difference means greater prevalence in the reference group. Both
half-specific differences and their mean are reported. Multiply a difference by 100 to express
it in percentage points.

### How features are selected

1. Reserve the measurement sample before discovery. Divide the remaining texts into two
   discovery halves and compare repeated balanced samples. Prompts call the groups A and B,
   with the mapping randomized on each call. Group identity may still be evident in the texts.
2. Merge overlapping proposals into distinct candidates, each with a definition and a binary
   question. A candidate does not have to appear in both discovery halves to proceed.
3. Measure each candidate on the reserved texts, one text per call, without supplying its group
   label. Rotate models with assignments balanced within each group and measurement half.
4. Require nonzero differences in the same direction in both measurement halves. Test a combined
   statistic by permuting labels within halves, then apply Benjamini–Hochberg across all
   successfully measured candidates. Neither half needs to be significant on its own.

The primary tier uses `fdr_q=0.05`. An additional suggestive tier contains features passing
`fdr_q_exploratory=0.10` only; set it to `null` to disable this tier. Uncorrected directional
tendencies have same-sign effects and an unadjusted permutation p-value below 0.05 but pass
neither FDR threshold. They are leads, with no multiple-testing control.

The default permutation floor is 2,000. Selection increases it when needed to resolve the
strictest multiple-testing threshold, up to 50,000. The saved results record the count actually
used. Permutation inference assumes labels are exchangeable within each measurement half;
repeated observations or clustered data need additional design decisions.

### Placebo check

Set `condition` to `"placebo"` in a copy of your saved configuration. This shuffles labels
separately within the discovery pool and the measurement sample and reruns the full procedure.
Keep the other settings fixed for a direct comparison. A placebo assesses false-positive behavior
for that corpus and configuration. A single run may retain a chance feature; it does not establish
calibration across all settings. Human coding is needed to assess classification accuracy.

### Models and defaults

The default discovery and measurement pool has four equally rotated models: `gpt-4o-mini`,
`claude-haiku`, `gpt-4.1-mini`, and `deepseek`. Consolidation uses `gpt-4.1`. The three-model
reference pool omits DeepSeek and is the pool used in the CampaignView walkthrough. The defaults
use 15 discovery calls per half, 15 texts per group per call, and 250 reserved texts per group.
Saved empirical configurations override those defaults. See the [settings and version
record](docs/REPRODUCIBILITY.md) for the reported runs and exact model IDs.

```bash
discern models                      # built-in models and providers
discern models --config myrun.json  # include custom entries
```

Set `discovery_models` and `rotation_pool` in JSON, or use `--models` to select a pool for both
stages. Rotation requires at least two models. Balancing assignment prevents a systematic
association between the assigned model and the group contrast; it does not remove classifier
error. A larger pool is a sensitivity choice, not an accuracy guarantee. Gemini and the
OpenRouter models are available options and are outside the default pool.

Additional models can use an OpenAI-compatible or Anthropic-compatible endpoint:

```json
{
  "providers": {"myhost": {"base_url": "http://localhost:8000/v1", "api_key_env": null, "json_mode": "prompt_only"}},
  "models": {"local-a": {"provider": "myhost", "model_id": "your-first-model"},
             "local-b": {"provider": "myhost", "model_id": "your-second-model"}},
  "model_revision": {"local-a": "recorded-weights-and-server-version", "local-b": "recorded-weights-and-server-version"},
  "discovery_models": ["local-a", "local-b"],
  "rotation_pool": ["local-a", "local-b"],
  "consolidation_model": "local-a"
}
```

Merge these entries into a complete run configuration. `api_key_env: null` permits a keyless
server; a custom provider defaults to OpenAI-compatible calls. Set `kind: "anthropic"` for an
Anthropic-compatible endpoint. `json_mode: "prompt_only"` supports servers that reject
`response_format`. Responses must still pass strict parsing. Custom names cannot shadow built-ins.
Record local weights, quantization, and serving software in `model_revision`; changing it also
changes the classification cache key.

Pinned model IDs identify a version but do not guarantee identical responses. Hosted aliases
can change, and a provider may retire a model. Fresh runs can therefore produce different features
or labels. The offline example reproduces statistics from the supplied classifications.

### Runtime and interrupted runs

Measurement requires approximately `candidates × 2 × n_per_group` classification calls, plus
discovery, consolidation, and retries. The CampaignView real run required 39,000 measurement
calls before retries. Cost depends on text length, model prices, and retries; runtime also depends
on provider rate limits.

Repeat the same command to resume an interrupted run. Completed stages and classifications are
cached. You may lower `--classify-workers` from its default of 24 to reduce concurrent requests.
Changes that affect results require a new run name or output directory.

## Saved outputs and further checks

Every run saves its configuration (`00_config.json`), model IDs (`00_runspec.json`), partition
(`00_partition.json`), discovery (`01_discovery.json`), consolidated candidates
(`02_consolidated.json`), measurements (`03_measured.json`), selections (`04_selected.json`),
and summary (`05_summary.md`). `events.jsonl` records requests, responses, failures, and fallbacks.
New executions also record software versions and source hashes in `00_environment.json`.

The optional `discern check --dataset mydata.csv --group-col treated --from-run runs/real_r0`
reports inter-model agreement and Fleiss' κ. Agreement measures consistency, not correctness,
and does not determine selection.

For research validation tools and conventional text-method comparisons, see
[validation code](docs/SECTION_4_VALIDATION.md). Optional dependencies install with
`python -m pip install -e '.[validation]'`.

## Tests

These checks make no API calls:

```bash
python -m pytest tests/
python tests/test_pipeline.py
python tests/test_core.py
python tests/test_encoding_resume.py
# Longer null simulation, run separately:
python tests/test_null_fdr.py
```

Some older suites use standalone test runners; run the three direct commands above as well as
pytest. The longer null simulation is separate from the saved empirical placebo evidence.

## License

Code: [MIT](LICENSE). CampaignView data: [CC0 1.0](examples/campaignview/DATA_SOURCE.md).
Third-party notices are retained in [docs/licenses](docs/licenses/).
