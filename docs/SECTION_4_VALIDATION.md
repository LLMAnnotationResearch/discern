# Validation code

The [CampaignView walkthrough](../examples/campaignview/README.md) is the complete public example:
source data, preparation, discovery, measurement, statistical selection, and a full-pipeline placebo.
After installing the package, check both saved runs without API access:

```bash
python examples/campaignview/verify_unique_results.py
```

The walkthrough also gives the commands for fresh real-label and placebo model runs. The
[reviewer guide](OS_SUBMISSION_GUIDE.md) links each saved stage to its implementation. The tools
below support additional research checks; they are separate from that reproduction path.

## Reusable checks

| Question | Code | Interpretation |
| --- | --- | --- |
| Does the statistical rule stay quiet under null labels? | [validation.py](../src/discern/validation.py), [validate_section4.py](../scripts/validate_section4.py) | Simulations and fixed-candidate-bank shuffles assess selection under their specified null; they do not test model accuracy |
| Does the full procedure retain chance features? | `condition="placebo"` in a run configuration; [pipeline.py](../src/discern/pipeline.py) | Repeat discovery, measurement, and selection with shuffled labels, as in the CampaignView placebo |
| Do features recur across runs? | [stability.py](../src/discern/stability.py) | Compare definitions and questions, allowing broader/narrower relationships; requires completed runs and a feature crosswalk |
| How are conventional text scores tested? | [baselines.py](../src/discern/baselines.py) | Sentiment, topic, and dictionary scores retain their own scales; classification accuracy is a separate question |

Use `python scripts/validate_section4.py --help` for the `simulate`, `frozen`, and `inventory`
commands. They do not use model APIs. For example, a small engineering check is:

```bash
python scripts/validate_section4.py simulate --scenario independent --reps 100 \
    --n-per-group 100 --candidates 12 --permutations 240 --workers 4 \
    --out /tmp/discern-null-check
```

The output directory must be new. Production selection determines the actual permutation
resolution. Under a global null, FDR is the probability of any rejection, not the fraction of
candidates rejected. Report the number of replications, any-rejection rate, and its uncertainty.
A small engineering check is not the empirical evidence reported in the proposal.

For a frozen-bank check, supply source-verified `uid,group` labels when available. Legacy
focal-first ordering reconstruction is an explicit pilot assumption, not independent label
verification. A frozen-bank shuffle holds candidates and classifications fixed; a full-pipeline
placebo regenerates both.

## Supporting analyses using restricted data

The proposal's Hurst stability, repeated-placebo, and conventional-method analyses are documented
in the [manuscript records](submission/README.md). Their source respondent data cannot be shared;
those analyses cannot be reproduced from the public package alone. The relevant study-specific
scripts are `prepare_hurst_validation.py`, `run_validation_batch.py`, `build_theme_crosswalk.py`,
`run_baseline_comparison.py`, and `run_empath_comparison.py`. They preserve the implementation used
for that supporting evidence. Equivalent stability and conventional-method comparisons have not
been run on CampaignView.

The proposal identifies repeated placebos, stability checks, and alternative-method comparisons
on the public CampaignView data as Stage 2 work. The current example supplies one full-pipeline
placebo and the saved real-label analysis.

Optional conventional-method dependencies install with `python -m pip install -e '.[validation]'`.
The recorded Empath analysis uses all 194 supplied categories and preserves the package license
in `docs/licenses/`. LIWC was not used. BERTopic is included alongside VADER, LDA, and Empath in
the supplement's Table B3. Its recorded dependency versions are in
`BERTopic_requirements.txt`.

Repeated use of the same held-out texts measures sensitivity to discovery and model choices.
It is not a new-sample replication. Model agreement assesses consistency; human labels are needed
to assess accuracy. Preserve all proposed candidates and identify measurement failures separately.
