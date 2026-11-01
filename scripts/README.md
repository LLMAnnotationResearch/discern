# Script index

For the complete public example, start with the [CampaignView walkthrough](../examples/campaignview/README.md).
Its preparation, verification, and table-export scripts are in that example folder. The scripts
below support additional checks, manuscript tables, and packaging. Run them from the repository
root; each accepts `--help`.

## Run and audit analyses

| Script | Purpose and required input |
| --- | --- |
| [run_validation_batch.py](run_validation_batch.py) | Run saved configurations with separate caches; uses paid APIs |
| [check_model_ids.py](check_model_ids.py) | Check returned model identifiers; calls provider APIs |
| [audit_validation_runs.py](audit_validation_runs.py) | Audit saved runs for partitions, labels, measurements, and selection results |
| [validate_section4.py](validate_section4.py) | Run null simulations, fixed-candidate shuffles, or a saved-run inventory; no model API calls |
| [recover_classification_cache.py](recover_classification_cache.py) | Reconstruct a cache from existing run records; requires the original artifacts |

## Restricted-data preparation and comparisons

These scripts require authorized source data or saved restricted-run artifacts. The public
[manuscript records](../docs/submission/README.md) contain settings and aggregate results only.

| Script | Purpose |
| --- | --- |
| [prepare_hurst_validation.py](prepare_hurst_validation.py) | Prepare the survey contrast and validation configurations |
| [prepare_p03_operationalization_repair.py](prepare_p03_operationalization_repair.py) | Version the Placebo 3 question correction from the initial discovery records |
| [prepare_stability_crosswalk.py](prepare_stability_crosswalk.py) | Prepare candidate records for comparisons across runs |
| [align_validation_features.py](align_validation_features.py) | Align features across runs; inspect its API requirements before running |
| [build_theme_crosswalk.py](build_theme_crosswalk.py) | Apply a supplied thematic mapping to candidate results |
| [run_text_baselines.py](run_text_baselines.py) | Fit sentiment and topic baselines |
| [run_baseline_comparison.py](run_baseline_comparison.py) | Compare VADER and LDA on matched evaluation responses |
| [run_empath_comparison.py](run_empath_comparison.py) | Add the full supplied Empath category family |
| [run_bertopic_comparison.py](run_bertopic_comparison.py) | Fit discovery-only BERTopic with a supplied local embedding model and score held-out assignments |

## Build tables and manuscript exhibits

These builders use saved analysis artifacts. They do not establish that an analysis can be
reproduced without its source data. Earlier exhibit formats remain available for audit; the
current tables use `build_paper_tables.py` and `build_three_panel_method_comparison.py`.

| Script | Purpose |
| --- | --- |
| [build_paper_tables.py](build_paper_tables.py) | Build placebo counts, theme recurrence, and complete candidate tables; use `--repair` for the final Placebo 3 version |
| [build_three_panel_method_comparison.py](build_three_panel_method_comparison.py) | Build native VADER/LDA/Empath outputs, with a fourth BERTopic panel when `--bertopic` is supplied |
| [build_compact_appendix_d.py](build_compact_appendix_d.py) | Build the compact settings, theme, and candidate appendix |
| [build_appendix_d.py](build_appendix_d.py) | Build the earlier detailed candidate appendix |
| [build_baseline_exhibits.py](build_baseline_exhibits.py) | Build earlier baseline tables and their review catalogue |
| [build_thematic_method_comparison.py](build_thematic_method_comparison.py) | Build the earlier thematic method comparison |
| [build_section4_exhibit.py](build_section4_exhibit.py) | Build validation exhibits from saved checks |
| [build_validation_latex.py](build_validation_latex.py) | Export validation tables to LaTeX |
| [build_validation_results.py](build_validation_results.py) | Collect validation results and crosswalks |

## Package and organize files

| Script | Purpose |
| --- | --- |
| [build_reviewer_release.py](build_reviewer_release.py) | Build and scan an archive of explicitly selected public files, without Git history or local analysis folders |
| [snapshot_paper_code.py](snapshot_paper_code.py) | Copy the same public files into a new `code/` folder and record content hashes; refuses to overwrite an existing snapshot |
| [organize_paper_folder.py](organize_paper_folder.py) | Organize a supplied manuscript folder; inspect its options before use |

The snapshot script now uses the public-file selection rather than copying local evidence
folders. Submitted aggregate records are maintained in `docs/submission/`.
