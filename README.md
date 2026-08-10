# discern

Identification and validation of text features that distinguish two groups.

`discern` accepts a CSV or Excel file containing a text column and a binary group column. Blinded LLM
discovery proposes candidate features that may distinguish the groups. A rotating pool of models then
measures each candidate on a held-out sample. The procedure retains features that pass same-sign
replication across two data halves, a permutation test, and Benjamini–Hochberg false discovery rate
(FDR) control. The method is not specific to a particular dataset or domain.

The design separates generation from measurement. Discovery proposes features but does not observe
the measurement sample. An independent, held-out stage estimates and validates the proposed features.

---

## Intended use

`discern` is intended for exploratory research, including hypothesis development, theory development,
mechanism discovery, and post hoc analysis of experiments. It applies when short texts are associated
with two groups and the objective is to estimate systematic differences between them. For example:

- An experiment collects open-ended survey responses from treatment and control participants, and the
  analysis seeks systematic differences in those responses.
- An exploratory dataset contains short texts associated with two groups, such as job descriptions
  for fully remote and hybrid positions.

It is intended for quantitative researchers working with medium-to-large samples and
short-to-medium texts, and has a deliberately narrow scope:

- It finds the differences between groups, not the general themes. Topic modeling surfaces what a
  corpus is about; `discern` surfaces what separates group A from group B, as yes/no properties.
- It is generative, not confirmatory. It proposes and statistically validates tendencies worth
  investigating. It is not a replacement for qualitative inductive work, and it is atheoretical and
  agnostic to causal structure. It provides no estimate of causal direction. Researchers must
  interpret findings within the relevant empirical setting and theory. It can be preregistered as an
  exploratory analysis, including for text collected as part of an experiment.
- Unlike classification using LLMs, keywords, or machine learning, it does not require constructs to
  be specified in advance. Discovery proposes them, and measurement validates them.

---

## Data requirements

`discern` is designed for the following data structure:

- Short-to-medium open-ended text: a phrase up to a few hundred words per row, such as open-ended survey
  responses, product or business descriptions, reviews, profiles, and abstracts. The method has also
  been validated on stories of approximately 300 words. Cost increases with text length, and text that
  exceeds a model's context window requires chunking (see `docs/GUIDANCE.md`). The method is not
  intended for single words, categorical codes, or book-length documents without a chunking strategy.
- Medium-to-large datasets: the held-out measurement sample and the discovery pool are disjoint,
  so each group needs approximately 150–300 or more rows. Approximately 500 rows per group are
  preferable for recovery of the full feature set. Below 100 rows per group, the method has sufficient
  power only for relatively large effects.
- Exactly two groups: a binary contrast (treated/control, A/B, or before/after). More than two
  groups is a user-built extension (one-vs-rest or all-pairs) with a global multiplicity correction.
- Descriptive rather than causal: it identifies textual differences between the two groups, expressed
  as binary properties that a model can classify from the text. It does not identify causal mechanisms,
  and the resulting features may be correlated.
- One language per run is recommended. If language correlates with group assignment, discovery can
  identify language itself as a distinguishing feature, which introduces confounding.

Typical applications include open-ended survey responses from treatment and control groups, listing
or description text from two categories, and posts or biographies from two communities.

---

## Examples

The following application compares abstracts published since 2023 in two management journals,
Organization Science and the Strategic Management Journal. The analysis reduces approximately 650
abstracts to 26 statistically validated features:

[Organization Science vs. Strategic Management Journal](examples/sample-output/orgsci-vs-smj.md)
(feature summary and themes)

A placebo run on the same abstracts with randomly permuted group labels validated 0 of 50 candidate
features. The pipeline measures held-out abstract text and does not observe journal names. The result
therefore cannot be attributed directly to the model reproducing journal-name associations.

The second application compares QJE and JPE abstracts published since 2020. It reduces 734 abstracts
to 21 validated features.

[Quarterly Journal of Economics vs. Journal of Political Economy](examples/sample-output/qje-vs-jpe.md)
(feature summary and themes)

---

## Install

Python 3.10 or newer is required. Download and install the package from a terminal:

```bash
# 1. Download the repository
git clone https://github.com/LLMAnnotationResearch/discern.git
cd discern

# 2. Install it; this makes the `discern` command available
pip install -e .
```

The `-e` option installs the package in editable mode. Subsequent updates obtained with `git pull`
therefore take effect without reinstallation, and the `discern` command is available from any folder.

Required Python packages (`openai`, `anthropic`, `numpy`, `pandas`, `openpyxl`) install
automatically. Your datasets may be `.csv`, `.tsv`, or Excel (`.xlsx`/`.xls`).

> Do not run `discern` inside a cloud-synced folder (Dropbox, OneDrive, iCloud Drive, or Google Drive).
> `discern` writes its audit log and classification cache continuously while a run is in progress,
> and concurrent access by a synchronization client can produce permission or file-in-use errors,
> particularly on Windows. Online-only or placeholder files can also cause read errors. Clone the
> repository to a local folder such as `~/projects/discern`, or place outputs outside the synchronized
> directory with `--output-dir ~/discern-runs`. On macOS, the terminal may require access to the folder
> (System Settings → Privacy & Security → Files and Folders).

## 1. Configure API keys

`discern` reads one environment variable per provider and requires variables only for the selected
models. Store keys in the environment or in a `.env` file outside the repository. Do not commit them.

```bash
discern setup-help        # prints step-by-step instructions
```

The recommended location is `~/.config/discern/.env` (chmod 600), loaded automatically:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

Include only the providers used in the analysis. Set `DISCERN_ENV` to use another location:
`export DISCERN_ENV=/path/to/your.env`.

> Privacy and data handling. By default, running `discern` sends text data to the selected third-party
> model providers, including OpenAI, Anthropic, and DeepSeek, for discovery and classification. For
> sensitive data, the entire pool can instead use a local model server (the `local` provider or a
> custom server; see [Choosing models](#choosing-models)), which keeps text on the local machine. When
> using commercial
> APIs, do not run on data whose terms, consent, IRB approval, or regulations (e.g.
> PII/PHI, FERPA, GDPR) prohibit third-party transmission; check each provider's data-use and
> retention policy first, and consider de-identifying text beforehand. Run outputs under `output_dir/`
> contain source text and model responses and should be stored according to their sensitivity. The
> bundled `.gitignore`
> already keeps `runs/` and `.env` out of version control.

## 2. Try the demo (synthetic data)

```bash
cd examples
python make_demo_data.py                       # writes demo.csv (400 toy product blurbs, 2 groups)
discern run --config config.real.json          # discover + validate the contrast
discern run --config config.placebo.json       # the null: same data, labels permuted (should find ~nothing)
```

## 3. Run an analysis

The input table must contain a text column and a binary group column. `discern` discovers candidate
features, measures each candidate on a held-out sample, retains candidates that pass the statistical
criteria, and writes the results to a run folder. The command accepts either direct flags or a saved
configuration file:

```bash
# flags: specify the CSV, text column, and binary group column
discern run --dataset mydata.csv --text-col description --group-col treated \
    --unit-label "product review" --focal-label treated --reference-label control

# or generate a config, edit it, and run
discern init --out myrun.json
discern run --config myrun.json
```

`focal_value` and `reference_value` select the two values of the group column to compare when the
column is not already coded 0/1. The corresponding `*_label` and `--unit-label` settings affect only
the output labels. Each run writes to `runs/<name>/`. The primary output, `05_summary.md`, reports the
validated features, effect sizes, classification questions, suggestive features, and features that did
not validate. The `--dry-run` option checks the configuration and data partition without making API calls.

### Placebo run

A real run controls false discoveries by retaining a feature only if it replicates in both independent
data halves and passes a permutation test under a controlled FDR. A placebo is not a prerequisite for
the validity of a real run.

A placebo provides an end-to-end diagnostic for a specific dataset. It randomly permutes the group
labels and applies the same pipeline. Because the permutation removes systematic group differences, a
well-calibrated placebo should validate approximately zero features. It requires no hand labeling:

```bash
discern run --dataset mydata.csv --text-col description --group-col treated \
    --condition placebo --fresh-reservation
```

A placebo is particularly informative for public or potentially memorized text, small samples, and
applications that require additional evidence about false-positive behavior. It is a diagnostic rather
than a required calibration step.

### Choosing models

`--models` (or `discovery_models` and `rotation_pool` in a configuration file) accepts any
comma-separated subset of the model registry. A rotation-based design requires at least two models;
the default pool uses models from OpenAI, Anthropic, and DeepSeek. Balanced assignment, rather than
pool size, prevents a single model from being confounded with the group contrast. This property holds
with two models. A larger and more diverse pool provides a robustness or sensitivity check across
classifiers, but does not strengthen the no-confounding property. Adding a low-quality model can reduce
measurement quality.

```bash
discern models                       # list built-in models and providers, and configuration instructions
discern models --config myrun.json   # also show the custom models/providers a config defines
```

In addition to the OpenAI, Anthropic, and DeepSeek models, the registry includes models available
through OpenAI-compatible endpoints: `gemini-flash`, `llama-3.3-70b`, and `qwen-2.5-72b` through
OpenRouter, and `local-llama` through a keyless local Ollama server. A configuration file can define
additional models without code changes:

```json
{
  "providers": { "myhost": { "base_url": "http://localhost:8000/v1", "api_key_env": null, "json_mode": "prompt_only" } },
  "models":    { "llama-8b": { "provider": "myhost", "model_id": "meta-llama/Llama-3.1-8B-Instruct" } },
  "model_revision": { "llama-8b": "q4_K_M-2026-07" },
  "discovery_models": ["gpt-4o-mini", "llama-8b"],
  "rotation_pool":    ["gpt-4o-mini", "claude-haiku", "llama-8b"]
}
```

The `providers` entry specifies an OpenAI-compatible endpoint, such as a gateway or local server. The
`models` entry names a model available at that endpoint. The model key can then be included in the
discovery or rotation pool. Additional requirements follow:

- Config is strict JSON (no comments/trailing commas).
- `kind` defaults to `"openai"` (chat completions). Set `"anthropic"` for a Claude-compatible endpoint;
  its `base_url` is honored. `api_key_env: null` specifies a keyless local server. Names that conflict
  with a built-in are rejected.
- `json_mode` is `"json_object"` for hosted built-in models and `"prompt_only"` for local or custom
  endpoints. Many local servers reject `response_format`. Output is parsed strictly in either mode;
  change the setting if the endpoint rejects or ignores JSON mode.
- `local-llama` targets Ollama's default port (11434). For vLLM (`:8000`) or LM-Studio (`:1234`),
  or a remote box, define a custom provider with that `base_url` as shown above.
- `discern` requires API keys only for providers represented in the selected pool. A fully local pool
  requires no API key.

Provenance and reproducibility. Pinned snapshots, including the default OpenAI and Anthropic
classifiers, identify a fixed model version. They do not guarantee byte-identical API outputs. The
design therefore targets conclusion-level reproducibility rather than identical responses. For
floating hosted aliases and local models, `00_runspec` records the runtime-resolved identifier and
system fingerprint as provenance. An OpenRouter route may not expose the exact backend build, and a
local tag does not identify the quantization, weights, or serving engine. For these models, set
`model_revision` to a user-controlled string. The value is recorded as provenance and included in the
classification cache key, so a changed revision requires fresh classification.

Provider catalogs change as models are retired. `python scripts/check_model_ids.py` verifies that each
built-in `model_id` remains available from its provider and confirms unlisted aliases with a live call.
A scheduled GitHub Action (`.github/workflows/model-check.yml`) runs this check weekly.

### Cost & rate limits

A run makes one API call per candidate and held-out unit, plus a smaller number of discovery and
consolidation calls. A typical run with 40–50 candidates and 500 held-out units requires approximately
10,000–20,000 classification calls. A journal-abstract run with approximately 15,000 calls takes about
30 minutes and costs about $3 with the cost-weighted default pool. Cost increases with the number of
candidates, sample size, and text length. The default pool consequently assigns substantial weight to
lower-cost classifiers (`gpt-4o-mini`, `deepseek`, and `gemini-flash`).

A standard paid API account is generally sufficient. Two features make entry-level tiers usable:

- Automatic retries use backoff and honor `Retry-After`. A rate-limited (429) call waits for the
  interval specified by the provider and then retries, which increases runtime without terminating the run.
- The rotating pool spreads load across providers, so each sees only ~1/N of the calls.

Providers impose different request-per-minute limits on entry-level accounts. Among the default
providers, Anthropic generally has the most restrictive entry tier. A large run that includes Claude
may therefore take substantially longer on a new account. A small deposit may automatically raise the
account tier. OpenAI and DeepSeek generally provide higher entry-tier limits. Exhausting a daily quota
terminates the run with an explicit error rather than producing an incomplete measurement silently.

If rate limits bind:

- Reduce `--classify-workers N` from its default of 24 to lower concurrent request volume.
- Assign a smaller share of a large run to a rate-limited provider, or increase the API tier.
- Use a local model for an offline run subject to local hardware capacity rather than provider rate limits.

An interrupted run can resume when the same command is issued again. Completed stages are loaded from
the run folder, and classifications are retrieved from a persistent cache
(`output_dir/class_cache.json`) keyed by dataset, prompt version, model, unit, and question. Because
classification accounts for approximately 99% of API expenditure, a resumed run incurs charges only
for calls that did not complete. `--classify-workers` controls request concurrency and is not part of
the run identity, so it may change between attempts. Parameters that affect results, including
`n_per_group`, the model pool, and `fdr_q`, cannot change when resuming under the same run name.

## 4. Optional classifier agreement check

This optional command provides a label-free measure of whether models classify the constructs
consistently. It is separate from the primary run and is not a substitute for a hand-labeled
validation set:

```bash
discern check --dataset mydata.csv --group-col treated --from-run runs/real_r0
```

It reports mean pairwise agreement and Fleiss' κ. High agreement indicates model concurrence. Low
agreement may indicate an ambiguous construct or a weak classifier. Agreement measures consistency,
not correctness, and does not determine feature validation.

## Outputs

Each run writes a self-contained folder under `output_dir/<run_name>/`: the config and data partition,
every discovery call (with the shown units and the blinded A/B mapping), the consolidated candidates,
the per-unit measurements, the feature table with signed effects and a direction legend, and an
append-only `events.jsonl` audit of every LLM call. Runs resume if interrupted.

Results are reported in two tiers. The primary Validated tier uses `fdr_q=0.05`. The exploratory
Suggestive tier uses `fdr_q_exploratory=0.10` and should be interpreted as a set of candidates for
subsequent confirmation rather than established findings. False-positive control also requires
same-sign replication across two data halves. A placebo run can provide an additional diagnostic for
the exploratory tier.
Set `fdr_q_exploratory: null` to disable the second tier.

## Method summary

During discovery, a model observes small, balanced, blinded samples of Group A and Group B and proposes
distinguishing features. The true group represented by "A" is randomized for each call and subsequently
mapped to a canonical label, which prevents the group wording from revealing the hypothesis. Candidates
are consolidated within and across two data splits. Each candidate is then converted to a binary
classification question and measured on a held-out reservation, with 250 observations per group by
default, using a balanced rotation of models. A feature is retained only if
its effect replicates with the same sign in both halves and beats a permutation null at 5% FDR
(the permutation count scales automatically with the number of candidates, so the p-value grid is
never coarser than the multiplicity correction needs). See `docs/GUIDANCE.md` for sample-size,
long-text, multilingual, and multiplicity guidance.

## Tests

All offline (no API). Run the fast suites with pytest, or any file directly:

```bash
pytest tests/                     # test_core + test_pipeline + friends (fast, mocked)
python tests/test_pipeline.py     # offline end-to-end (mocked classifier)
python tests/test_core.py         # fail-closed parsing/schema, cache-key, ID, rotation
python tests/test_encoding_resume.py   # UTF-8 I/O, resume identity, permutation auto-scaling
python tests/test_null_fdr.py     # all-null FDR simulation (≤ 5%); heavy; run directly, not via pytest
```

## License

MIT (provisional; see `LICENSE`).
