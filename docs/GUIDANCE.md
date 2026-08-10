# Guidance for using discern

This document provides guidance for applying the method. The numerical recommendations are based on
the validation study and should be treated as initial rules of thumb rather than universal constants.
Power depends on effect sizes, prevalence, and model classification accuracy.

## Placebo runs

A single real run already controls false positives: a feature survives only if it replicates in both
data halves and beats a permutation null at a controlled FDR. A placebo is therefore not required for
the validity of a single real run.

A placebo provides an empirical, end-to-end check for a specific dataset. It permutes the group labels
and reruns the same pipeline, so any detected structure is spurious by construction. A well-calibrated
placebo should validate approximately zero features. This label-free diagnostic is most informative
for public or potentially memorized text, small samples, or applications that require additional
evidence about the pipeline's false-positive behavior.

```bash
discern run --dataset mydata.csv --text-col text --group-col g --condition placebo --fresh-reservation
```

A single placebo may produce an FDR-permitted false positive. Repeated placebo survivors indicate a
potential problem, such as a confounded design, label leakage, or an insufficient sample size.

## Sample size

`discern` splits each group's data into a held-out measurement reservation (`n_per_group`, default
250) and a disjoint discovery pool containing the remaining observations. Each group therefore needs
approximately `n_per_group` plus a discovery pool. Rules of thumb from the validation study:

| goal | measurement / group | total / group (incl. discovery) |
|---|---|---|
| full feature set, incl. weak/abstract effects | ~250 | ~500 |
| strong, prevalent concepts only | ~100–150 | ~300 |
| underpowered floor (largest effects only) | ~100 | ~150 |

Small or abstract effects are the first to become undetectable as the sample decreases. Large and
prevalent effects remain detectable in smaller samples. A balanced design requires approximately twice
the per-group figure in total. In an imbalanced design, the smaller group determines effective sample
size.

## Text length

The method has been validated on text ranging from short phrases to documents of a few hundred words,
provided that each text and classification question fit within the model's context window. Cost is
approximately proportional to input tokens. Documents near or above the context limit require
chunking. The package does not specify a default aggregation rule because maximum or any-positive
aggregation changes the estimand and mechanically increases positive classifications for longer
documents. Any chunking and aggregation rule should be prespecified and appropriate to the construct.

## Non-English / translated text

Specify one analysis language per run. In validation, classifiers achieved greater than 90% agreement
across a machine translation, although agreement declined most for abstract constructs. Use a model
with documented capability in the analysis language or a recorded and versioned translation workflow.
Do not combine languages within a run without a documented methodological justification. The optional
`discern check` command reports cross-model agreement and can identify inconsistently classified constructs.

### Text encoding

`discern` reads and writes UTF-8 throughout, so accented characters, curly quotes, em dashes, and
non-Latin scripts pass through the source data into `05_summary.md` intact. Two
common sources of apparent encoding errors remain. A file saved from Excel as plain CSV often uses
Windows cp1252 rather than UTF-8. `discern` falls back to cp1252 and issues a warning, but resaving the
file as CSV UTF-8 is preferable. A viewer can also display valid text incorrectly if it infers the
wrong encoding. Verify the file in an editor configured for UTF-8 before concluding that it is damaged.

## More than two groups

`discern` is a pairwise method. For `k > 2` groups, conduct one-versus-rest or all-pairs comparisons.
Multiple comparisons create a larger family of tests, and per-run FDR does not control error across
that family. Prespecify a global correction, such as Benjamini–Hochberg applied to pooled p-values from
all contrasts, before interpreting the results.

## Multiplicity and permutation resolution

Every candidate is tested, so the number of candidates determines the number of comparisons. This has
two implications.

The permutation grid must be sufficiently fine for the correction. A permutation p-value cannot be
less than `1/(B+1)`, where `B` is the number of permutations. Benjamini–Hochberg accepts the candidate
at rank `i` when `p ≤ q·i/n`, so the most stringent threshold is `q/n` for the rank-1 candidate. If the
p-value floor exceeds this threshold, even a feature with a large effect cannot validate. With the
previous fixed values `B = 2000` and `q = 0.05`, this constraint applied above 100 candidates, within
the range permitted by `max_candidates`.

`discern` sets `B` automatically from `n_candidates / q`, with `permutations` treated as a lower bound
rather than a fixed value. The grid therefore covers the required threshold unless the internal cap of
50,000 permutations binds. The run log and `05_summary.md` report the value used. If the cap binds,
typically under an unusually stringent `fdr_q`, a null result does not constitute evidence of absence.

Power decreases as the candidate count increases, independently of permutation resolution. Because
`q·i/n` decreases with `n`, a broad discovery run reduces the probability that any individual feature
validates. When the number of validated features is lower than expected, examine `n_candidates` before
increasing `n_iterations`. Additional discovery can increase the candidate count and make the
multiplicity correction more stringent. A more narrowly specified contrast generally provides greater
power for each candidate.

## Reproducibility

Each run stores its configuration, partition, discovery calls, measurements, and audit log. These
artifacts support reproduction of the completed run's conclusions. LLMs are not
bit-for-bit deterministic even at temperature 0; the design targets conclusion-level
reproducibility. Pinned model snapshots name a fixed model version (they do not guarantee
byte-identical outputs); unpinned aliases (e.g. `deepseek-chat`) record their runtime-resolved
version per run in `00_runspec`.

## Cost & runtime

Measurement accounts for most computation: approximately `#candidates × 2 × n_per_group`
classification calls per run. For short text and small models, a run typically requires several
minutes and costs approximately one to two dollars. Cost for longer documents increases in proportion
to token count. Use `--dry-run` to inspect the partition and verify the configuration without API use.

## Classifier confidence (optional)

A hand-labeled set is not required for the primary procedure. A placebo provides evidence about
false-positive behavior. To assess whether models classify the constructs consistently, which is
relevant to false negatives, the optional `discern check` reports label-free inter-model agreement.
Low agreement may warrant revising the classification question or excluding a weak model.
