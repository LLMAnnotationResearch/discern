# Manuscript records

For the runnable public example, start with the [CampaignView walkthrough](../../examples/campaignview/README.md).
Its data, complete saved runs, and offline verification script are included.

The Hurst files in this folder document supporting analyses in the proposal's technical supplement.
They preserve research settings and aggregate results for transparency. Hurst respondent texts and
row-level scores cannot be shared, so these analyses cannot be reproduced from the public package
alone. See [settings and limitations](../REPRODUCIBILITY.md#supporting-manuscript-analyses-restricted-hurst-data).

| Files | Purpose |
| --- | --- |
| `run_catalog.json` | Map the Hurst analyses to saved settings and candidate results |
| `configs/`, `model_versions/` | Specifications and recorded model identifiers for those analyses |
| `candidate_results/`, `unmeasurable_candidates.json` | Aggregate feature estimates, selection results, and the unmeasured candidate |
| `baseline_settings.json` | Recorded Hurst VADER, LDA, and Empath settings |
| `requirements.*-recorded.txt` | Partial historical dependency records for the Hurst analyses |
| `verification_environment.json` | Current environment used to verify the public CampaignView example; separate from the historical Hurst records |
