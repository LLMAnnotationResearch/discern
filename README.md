# discern

**Find and validate the text features that distinguish two groups.**

Point `discern` at a CSV or Excel file with a text column and a binary group column. It uses blinded LLM discovery
to propose candidate features that separate the groups, then *measures every candidate* on a held-out
sample with a rotating pool of models and keeps only the ones that survive a strict statistical gate
(same-sign replication across two data halves + a permutation null + Benjamini–Hochberg FDR). Nothing
in the method is specific to any dataset or domain — you supply the data and the labels.

It is a **generate-then-measure** design: discovery is generous and only proposes; an independent,
held-out measurement decides what is real. Discovery never sees the measurement sample.

---

## What it's for

`discern` is a tool for the **exploratory phases of research** — hypothesis and theory development,
mechanism discovery, post-hoc analysis of experiments — when you have short texts attached to two
groups and want to know, systematically, how they differ. For example:

- You ran an experiment and collected open-ended survey responses from treatment and control
  participants, and want to know whether they differ in any systematic way.
- You are in the exploratory phase of looking at a dataset that contains short texts and want to
  surface differences between groups (e.g., how do job descriptions differ for fully-remote versus
  hybrid roles?).

It is aimed at **quantitative researchers** working with medium-to-large N and short-to-medium texts,
and it is deliberately narrow about what it does:

- **It finds the differences *between* groups — not the general themes.** Topic modeling surfaces what
  a corpus is about; `discern` surfaces what separates group A from group B, as yes/no properties.
- **It is generative, not confirmatory.** It proposes and statistically validates *tendencies worth
  investigating*. It is **not** a replacement for qualitative inductive work, and it is atheoretical
  and agnostic to causal structure — it says nothing about causal direction, so it is on you to situate
  a finding in your setting and theory. (It *can*, however, be pre-registered as an exploratory
  analysis — e.g. for text collected as part of an experiment.)
- **Unlike classification** (via LLMs, keywords, or ML), it does **not** require you to name the
  constructs of interest in advance — discovery proposes them, and measurement validates them.

---

## When to use it

`discern` is built for a particular shape of problem — check your data against this before running:

- **Short-to-medium open-ended text** — a phrase up to a few hundred words per row: open-ended survey
  responses, product or business descriptions, reviews, profiles, abstracts. It also handles longer
  documents (validated on ~300-word stories), but cost scales with length and text beyond a model's
  context window needs chunking (see `docs/GUIDANCE.md`). It is *not* meant for single words or
  categorical codes (nothing to discover), or book-length documents without a chunking strategy.
- **Medium-to-large datasets** — the held-out measurement sample and the discovery pool are disjoint,
  so each group needs roughly **150–300+ rows** (ideally ~500) to recover the full feature set. Below
  ~100/group the method is underpowered for anything but the largest effects.
- **Exactly two groups** — a binary contrast (treated/control, A/B, before/after). More than two
  groups is a user-built extension (one-vs-rest or all-pairs) with a global multiplicity correction.
- **Descriptive, not causal** — it surfaces *what textually distinguishes* the two groups, expressed
  as yes/no properties a model can read from the text. It does not tell you why, and the features can
  correlate with one another.
- **Avoid mixing languages in one run** (if language correlates with the group, discovery can latch
  onto the language itself as the "distinguishing feature" — a confound; pick one language per run).

Typical fit: open-ended survey responses across treatment vs. control (or any two subpopulations),
listing/description text across two categories, or posts/bios across two communities.

---

## See it in action

Here's `discern` on real data, distinguishing the abstracts of two management journals —
**Organization Science** vs. the **Strategic Management Journal** — narrowing ~650 abstracts
down to **26 statistically validated features**, grouped into readable themes:

**→ [Organization Science vs. Strategic Management Journal](examples/sample-output/orgsci-vs-smj.md)** (feature summary + themes)

*Placebo test:* rerun the same abstracts with the group labels randomly permuted and **0 of 50 candidate
features validate**. The pipeline measures text on held-out abstracts (never the journal name), so a real
result can't be the model just parroting what it "knows" about the journals.

**For the economists** — here's `discern` run on the abstracts of **QJE vs. JPE** since 2020, narrowing
734 abstracts to **21 validated features**.

**→ [Quarterly Journal of Economics vs. Journal of Political Economy](examples/sample-output/qje-vs-jpe.md)** (feature summary + themes)

---

## Install

You need Python 3.10 or newer. In a terminal, download the code and install it:

```bash
# 1. Download this repository to your computer
git clone https://github.com/LLMAnnotationResearch/discern.git
cd discern

# 2. Install it — this makes the `discern` command available
pip install -e .
```

That's it — you can now run `discern` from any folder. (The `-e` installs it "linked" to
this folder, so if you later download updates with `git pull`, they take effect without
reinstalling.)

Required Python packages (`openai`, `anthropic`, `numpy`, `pandas`, `openpyxl`) install
automatically. Your datasets may be `.csv`, `.tsv`, or Excel (`.xlsx`/`.xls`).

## 1. Store your API keys (once)

`discern` reads one environment variable per provider and only the ones your chosen models need. Keys
live in your environment or a `.env` **outside** the repo — never committed.

```bash
discern setup-help        # prints step-by-step instructions
```

The recommended location is `~/.config/discern/.env` (chmod 600), loaded automatically:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

Only include providers you'll use. Point elsewhere with `export DISCERN_ENV=/path/to/your.env`.

> **Privacy & data handling.** By default, running `discern` **sends your text data to the third-party
> model providers you select** (OpenAI, Anthropic, DeepSeek, …) for discovery and classification. For
> sensitive data you can instead point the whole pool at a **local model server** (the `local` provider,
> or your own — see *Choosing models*), which keeps text on your own machine. When using commercial
> APIs, do not run on data whose terms, consent, IRB approval, or regulations (e.g.
> PII/PHI, FERPA, GDPR) prohibit third-party transmission; check each provider's data-use and
> retention policy first, and consider de-identifying text beforehand. Run outputs under `output_dir/`
> contain your source text and model responses — store them accordingly. The bundled `.gitignore`
> already keeps `runs/` and `.env` out of version control.

## 2. Try the demo (synthetic data)

```bash
cd examples
python make_demo_data.py                       # writes demo.csv (400 toy product blurbs, 2 groups)
discern run --config config.real.json          # discover + validate the contrast
discern run --config config.placebo.json       # the null: same data, labels permuted (should find ~nothing)
```

## 3. Run on your own data

You give `discern` a table with a **text column** and a **binary group column**. It discovers candidate
features that might distinguish the groups, measures each one on a held-out sample, keeps only those
that survive the statistical gate, and writes them to a run folder. Invoke it two ways — quick flags,
or a config file you save and re-run:

```bash
# flags: point at your CSV, name the text column and the binary group column
discern run --dataset mydata.csv --text-col description --group-col treated \
    --unit-label "product review" --focal-label treated --reference-label control

# or generate a config, edit it, and run
discern init --out myrun.json
discern run --config myrun.json
```

`focal_value` / `reference_value` pick which two values of the group column to contrast (if your column
isn't already 0/1); the `*_label` and `--unit-label` settings only make the output readable. Each run
writes to `runs/<name>/`, and the file you read is **`05_summary.md`** — the validated features, each
with its effect size and the yes/no question it was measured by, plus a looser "suggestive" tier and
everything that didn't validate. Add **`--dry-run`** to any `run` to check the config and data
partition (group sizes, held-out reservation) without spending a single API call.

### Checking for false positives (the placebo run)

The real run already guards against false positives on its own: a feature is kept only if it replicates
in **both** independent data halves *and* beats a **permutation null** at a controlled false-discovery
rate. So your results are valid from a single real run — the placebo is **not** a prerequisite.

What the placebo adds is an **end-to-end sanity check on your specific data**. It randomly permutes the
group labels and runs the identical pipeline, so there is no real difference to find; a well-behaved
placebo therefore validates **~nothing**. It needs no hand-labeling:

```bash
discern run --dataset mydata.csv --text-col description --group-col treated \
    --condition placebo --fresh-reservation
```

It's worth running — especially for public or possibly-memorized text (e.g. published abstracts), for
small samples, or to show a skeptical reader that the method isn't manufacturing signal — but treat it
as a confidence check, not a required calibration step.

### Choosing models

`--models` (or `discovery_models` / `rotation_pool` in a config) takes any comma-separated subset of
the model registry, so **you choose exactly which models rotate**. A rotation-based design needs **at
least two models**; the default pool rotates three providers (OpenAI, Anthropic, DeepSeek). The
balanced assignment — not the pool size — is what prevents any single model from being confounded with
the group contrast, so that guarantee already holds at two models. Treat a larger, more diverse pool as
a **robustness / sensitivity choice** (does the finding survive a different mix of readers?), not as a
strengthening of the no-confounding property — and note that adding a weak model can *lower*
measurement quality, so choose the pool deliberately.

```bash
discern models                       # list every built-in model + provider, and how to add your own
discern models --config myrun.json   # also show the custom models/providers a config defines
```

Beyond the OpenAI/Anthropic/DeepSeek built-ins, the registry ships **open-weight and additional
options** reachable through OpenAI-compatible endpoints — `gemini-flash`, `llama-3.3-70b` and
`qwen-2.5-72b` (via OpenRouter), and `local-llama` (a **keyless** local **Ollama** server). Add any
others in your config without touching the code:

```json
{
  "providers": { "myhost": { "base_url": "http://localhost:8000/v1", "api_key_env": null, "json_mode": "prompt_only" } },
  "models":    { "llama-8b": { "provider": "myhost", "model_id": "meta-llama/Llama-3.1-8B-Instruct" } },
  "model_revision": { "llama-8b": "q4_K_M-2026-07" },
  "discovery_models": ["gpt-4o-mini", "llama-8b"],
  "rotation_pool":    ["gpt-4o-mini", "claude-haiku", "llama-8b"]
}
```

The `providers` entry is an OpenAI-compatible endpoint (a gateway, or your own server); the `models`
entry names a model reachable there, whose key you then list in the pools. Notes:

- **Config is strict JSON** (no comments/trailing commas).
- `kind` defaults to `"openai"` (chat-completions); set `"anthropic"` for a Claude-compatible endpoint
  (its `base_url` is honored). `api_key_env: null` = keyless (local servers). Names that collide with a
  built-in are rejected.
- **`json_mode`** is `"json_object"` for the hosted built-ins and `"prompt_only"` for local/custom
  endpoints (many local servers reject `response_format`). Output is strict-parsed either way; flip it
  if your endpoint errors on, or ignores, JSON mode.
- **`local-llama` targets Ollama's default port (11434).** For vLLM (`:8000`) or LM-Studio (`:1234`),
  or a remote box, define a custom provider with that `base_url` as shown above.
- discern only requires an API key for the providers your chosen pool actually uses, so a **fully-local
  pool needs none**.

**Provenance vs. reproducibility.** Pinned snapshots (the default OpenAI/Anthropic classifiers) name a
**fixed model version** — but note that even a pinned snapshot doesn't guarantee byte-identical API
outputs, so the design targets *conclusion-level* reproducibility, not identical responses. Floating/
hosted aliases and local models are weaker still: `00_runspec` records the runtime-resolved id and
system fingerprint as *provenance*, but an OpenRouter route may not expose the exact backend build, and
a local tag says nothing about quantization, weights, or serving engine. For those, set **`model_revision`** to a string you control — it is recorded as provenance
**and** folded into the classification cache key, so a re-pulled local model or a bumped revision forces
fresh classification instead of silently reusing answers from the old model.

Provider catalogs drift (models get retired). `python scripts/check_model_ids.py` verifies every
built-in `model_id` still exists at its provider (confirming unlisted aliases with a live call), and a
scheduled GitHub Action (`.github/workflows/model-check.yml`) runs it weekly so a deprecation surfaces
as a failing check rather than a broken run.

### Cost & rate limits

A run makes one API call per (candidate × held-out unit), plus a small discovery/consolidation
overhead — on the order of **10k–20k classification calls** for a typical run (say 40–50 candidates ×
500 units). A journal-abstract run (~15k calls on the cost-tilted default pool) lands around **~30 min
and ~$3** in API spend; cost scales with candidates × N × text length, which is why the pool leans on
the cheap classifiers (`gpt-4o-mini`, `deepseek`, `gemini-flash`).

**Do you need a high API tier? No — a standard paid account is enough.** Two things keep entry tiers
workable without special access:

- **Automatic retries with backoff that honors `Retry-After`** — a rate-limited (429) call waits as
  long as the provider asks and retries, so hitting a limit *slows* a run, it doesn't fail it.
- **The rotating pool spreads load** across providers, so each sees only ~1/N of the calls.

Where an entry tier pinches: providers whose first tier caps requests-per-minute low. Among the
defaults, **Anthropic's entry tier is the tightest**, so a large run *including Claude* on a brand-new
account will crawl on the Claude share (a small deposit auto-upgrades the tier and removes it). OpenAI
and DeepSeek entry tiers are comfortable, and DeepSeek barely rate-limits. The only thing that *fails* a
run is a fully **exhausted daily quota** (a free-tier phenomenon) — and it fails loudly rather than
silently under-measuring.

Levers if you do hit limits:

- **`--classify-workers N`** (default 24) — lower it to ease pressure on a tight tier.
- Keep a tight-limit provider a small share of a large run, or bump your API tier.
- Run a **local** model (no rate limit; bounded by your own hardware) for a fully offline pass.

## 4. (Optional) Classifier confidence check

A quick, **label-free** look at whether the pool models actually read your constructs consistently —
a low-friction proxy for a hand-labeled validation set. Separate command, never part of a run:

```bash
discern check --dataset mydata.csv --group-col treated --from-run runs/real_r0
```

It reports inter-model agreement (mean pairwise + Fleiss' κ). High = models concur; low = an ambiguous
construct or a weak model. It shows concurrence, not correctness — a confidence check, not a gate.

## What you get

Each run writes a self-contained folder under `output_dir/<run_name>/`: the config and data partition,
every discovery call (with the shown units and the blinded A/B mapping), the consolidated candidates,
the per-unit measurements, the feature table with signed effects and a direction legend, and an
append-only `events.jsonl` audit of every LLM call. Runs resume if interrupted.

**Results are reported in two tiers** so real-but-marginal effects aren't hidden below one line:
**Validated** (primary, `fdr_q`=0.05 — the headline) and **Suggestive** (exploratory,
`fdr_q_exploratory`=0.10 — leads to confirm, not findings). The false-positive control rests on the
same-sign two-half replication gate, so verify the exploratory tier with a placebo run on your data.
Set `fdr_q_exploratory: null` to disable the second tier.

## How it works (one paragraph)

Discovery shows a model small, balanced, **blinded** samples of Group A vs Group B and asks what
distinguishes them; the true group behind "A" is randomized per call and remapped to a canonical label
afterward, so wording can't leak the hypothesis. Candidates are consolidated within and across two
data splits, then **every** candidate is turned into a yes/no classification question and measured on a
held-out reservation (250/group by default) by a balanced rotation of models. A feature is kept only if
its effect **replicates with the same sign in both halves** and beats a permutation null at 5% FDR. See
`docs/GUIDANCE.md` for sample-size, long-text, and multilingual guidance.

## Tests

All offline (no API). Run the fast suites with pytest, or any file directly:

```bash
pytest tests/                     # test_core + test_pipeline (fast, mocked)
python tests/test_pipeline.py     # offline end-to-end (mocked classifier)
python tests/test_core.py         # fail-closed parsing/schema, cache-key, ID, rotation
python tests/test_null_fdr.py     # all-null FDR simulation (≤ 5%); heavy — run directly, not via pytest
```

## License

MIT (provisional — see `LICENSE`).
