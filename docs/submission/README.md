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
| `candidate_results/`, `unmeasurable_candidates.json` | Archived aggregate estimates and selection results; P03 retains its initial 41-measurement attempt |
| `baseline_settings.json` | Recorded Hurst VADER, LDA, and Empath settings |
| `requirements.*-recorded.txt` | Partial historical dependency records for the Hurst analyses |
| `verification_environment.json` | Current environment used to verify the public CampaignView example; separate from the historical Hurst records |

The supplement and catalog's P03 summary report 42 measurements after a question repair. The
initial question about "positive, negative, or neutral" connotations elicited nonbinary answers.
It was corrected to ask about negative connotations using the discovery questions. The repair
followed that failure and was not preregistered. All 800 responses were classified anew for the
changed question, the other 41 measurements were preserved, and selection was rerun across all
42 candidates. No feature passed any reported tier.

The public P03 candidate results, configuration, model record, and original hashes retain the
initial attempt with 41 measurements. The catalog labels these separately from the final reported
counts. Full repair artifacts remain local; CampaignView is the complete public reproduction example.
