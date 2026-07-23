# Guidance — using discern well

Practical notes for applying the method to your own data. The specific numbers below come from the
validation study behind the method; treat them as starting rules of thumb, not universal constants —
power depends on your effect sizes, prevalence, and how cleanly your models read your constructs.

## The placebo run — a recommended check

A single real run already controls false positives: a feature survives only if it replicates in both
data halves *and* beats a permutation null at a controlled FDR. So your results are valid without a
placebo — it is **not** a required step.

What the placebo adds is an **empirical, end-to-end check on your own data**. It permutes the group
labels and re-runs the identical pipeline, so any structure it "finds" is spurious by construction; a
well-behaved placebo validates ~nothing. It's a cheap, label-free way to confirm the whole pipeline
(discovery included) isn't manufacturing signal on your specific dataset — most valuable for public or
possibly-memorized text (e.g. published abstracts), small samples, or convincing a skeptical reader.

```bash
discern run --dataset mydata.csv --text-col text --group-col g --condition placebo --fresh-reservation
```

A single placebo may show a rare, FDR-permitted false positive; a *pattern* of placebo survivors is the
red flag — it means something is wrong (a confounded design, a leaked label, too small a sample).

## Sample size

`discern` splits your data per group into a **held-out measurement reservation** (`n_per_group`,
default 250) and a **disjoint discovery pool** (the rest). So each group needs roughly
`n_per_group` + a discovery pool. Rules of thumb from the validation study:

| goal | measurement / group | total / group (incl. discovery) |
|---|---|---|
| full feature set, incl. weak/abstract effects | ~250 | ~500 |
| strong, prevalent concepts only | ~100–150 | ~300 |
| underpowered floor (largest effects only) | ~100 | ~150 |

Small-effect, abstract features are the first to disappear as the sample shrinks; strong, prevalent
ones survive much smaller samples. A balanced design needs ~2× the per-group figure in total; an
imbalanced one is limited by the **smaller** group.

## Text length

The method works on short phrases and on long documents alike (validated up to a few hundred words),
as long as each `text` + question fits the model's context window. Cost scales with input tokens. For
documents near or over the context window you must chunk — but there is **no default chunk-aggregation
rule**, because `max`/`any`-over-chunks changes what you're measuring and pushes long documents toward
1. If you chunk, pre-specify the rule and make it construct-appropriate.

## Non-English / translated text

Declare **one analysis language per run.** The classifiers apply constructs fairly consistently across
a machine translation (validated ~90%+ agreement), but abstract constructs lose the most in
translation. Use a model demonstrated to handle your language, or a recorded, versioned translation
workflow — and don't mix languages in one run without a documented reason. The optional
`discern check` (cross-model agreement) is a quick way to spot a construct your models read
inconsistently.

## More than two groups

`discern` is fundamentally **pairwise**. For k > 2 groups, run it multiple times (one-vs-rest, or
all-pairs) — but then you have a larger family of tests, and per-run FDR does **not** control error
across all of them. Pre-specify a global correction (e.g. Benjamini–Hochberg over the pooled p-values
of every contrast) before interpreting.

## Reproducibility

Each run stores everything it did (config, partition, every discovery call, every measurement, the
audit log), so a completed run's conclusions are reproducible from its artifacts. LLMs are not
bit-for-bit deterministic even at temperature 0; the design targets **conclusion-level**
reproducibility. Pinned model snapshots name a fixed model version (they do not guarantee
byte-identical outputs); unpinned aliases (e.g. `deepseek-v4-flash`) record their runtime-resolved
version per run in `00_runspec`.

## Cost & runtime

Measurement dominates: roughly `#candidates × 2 × n_per_group` classification calls per run. On short
text with small models this is typically a few minutes and a dollar or two per run; long documents
scale with the token ratio. Use `--dry-run` first to see the partition and confirm your setup with no
API spend.

## Classifier confidence (optional)

You do **not** need a hand-labeled set to get trustworthy results — the placebo carries that load. If
you want reassurance that the models can read your constructs (a guard against false *negatives*), the
optional `discern check` reports label-free inter-model agreement. Low agreement on a construct is a
sign to reword the question or drop a weak model.
