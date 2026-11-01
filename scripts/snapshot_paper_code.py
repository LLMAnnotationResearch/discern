"""Copy manuscript-support code, without credentials or response data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main(root):
    repo=Path(__file__).resolve().parents[1];root=Path(root).resolve();dest=root/'code'
    copied={}
    files=list((repo/'scripts').glob('*.py'))+list((repo/'src/discern').glob('*.py'))+list((repo/'docs').glob('*.md'))+list((repo/'docs').glob('*.txt'))+list((repo/'docs/licenses').glob('*.txt'))+list((repo/'tests').glob('*.py'))+[repo/'pyproject.toml',repo/'README.md',repo/'src/discern/py.typed']
    for p in files:
        target=dest/p.relative_to(repo);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        copied[str(target.relative_to(dest))]=hashlib.sha256(p.read_bytes()).hexdigest()
    evidence=repo/'test datasets (not to be made public)/paper_evidence'
    recipes=evidence/'07_run_manifests/2026-10-27_additional_placebo_configs'
    for p in recipes.glob('*.json'):
        target=dest/'configs/additional_placebos'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        copied[str(target.relative_to(dest))]=hashlib.sha256(p.read_bytes()).hexdigest()
    repair=evidence/'07_run_manifests/2026-10-27_P03_operationalization_repair'
    for p in list(repair.glob('*.json'))+list((repair/'outputs/P03_REPAIRED').glob('02b_operationalization_repair.json')):
        target=dest/'configs/measurement_repairs'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        copied[str(target.relative_to(dest))]=hashlib.sha256(p.read_bytes()).hexdigest()
    themes=evidence/'06_figures_tables/2026-10-26_theme_results_v2'
    for name in ['semantic_link_specification.json','appendix_candidate_links.csv','appendix_all_themes.csv']:
        p=themes/name
        if p.exists():
            target=dest/'configs/theme_grouping'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
            copied[str(target.relative_to(dest))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (dest/'source_manifest.json').write_text(json.dumps({'active_repository':str(repo),'files_sha256':copied},indent=2)+'\n')
    (dest/'REPRODUCIBILITY.md').write_text('''# Paper code

This is a source snapshot. Rerun this snapshot script from the development checkout after code changes. `scripts/build_figures.py` writes to the paper's `FigsTables/` folder. `src/discern/` contains the pipeline. The source manifest records content hashes.

`scripts/run_validation_batch.py` executes the full pipeline. `configs/additional_placebos/` records the three added runs (shuffle indices 2–4), including original private data and output paths. API credentials remain in `~/.config/discern/.env`, outside Dropbox. Install dependencies using `pyproject.toml`; the recorded runs use anthropic 0.125.0 and OpenAI 3.38.0. Credentials and raw response data are not bundled here.

`scripts/audit_validation_runs.py` checks discovery/measurement separation, label assignments, binary measurements, saved effects, and actual model balance. Candidate-level outputs and completed audits are under `../appendices/data/`.

`scripts/build_paper_tables.py` requires all five placebos to finish and then exports Tables 1–2 and Appendix D. Use its `--original`, `--theme`, `--extra-batch`, and `--out` arguments. For this paper those inputs are respectively `paper_evidence/06_figures_tables/2026-10-26_compact_results`, `paper_evidence/06_figures_tables/2026-10-26_theme_results_v2`, and `paper_evidence/07_run_manifests/2026-10-27_additional_placebo_configs/manifest.json`, beneath the active repository's private test datasets directory. Build into `working/scratch/` and review before promoting outputs.

`scripts/build_compact_appendix_d.py` consolidates Appendix D into a settings summary, the complete thematic crosswalk, and one numerical table retaining all 317 candidates. The companion `appendices/data/validation_feature_catalogue.html` is searchable; its CSV preserves the exact questions, definitions, metadata, and full-precision results. It can rebuild Appendix D alone using `--source`, `--tex`, and `--preview`, without rerunning the pipeline.

`scripts/run_baseline_comparison.py` audits saved sentiment/LDA pilots, matches all methods on 794 evaluable respondents, and reports the complete LDA sensitivity grid. `scripts/run_empath_comparison.py` adds all 194 supplied Empath 0.89 categories, recording dictionary/code hashes and the full family before testing, with normalized word matching and package-default sensitivity. It preserves all earlier numerical results and requires no API calls. `scripts/build_baseline_exhibits.py` builds draft Table 3 and the review catalogue. Aggregate outputs and the recorded analysis plan are under `../appendices/data/alternative_methods/`; the review HTML and optional compact Appendix E are under `../working/alternative_methods/`. Per-response scores and fitted models remain in the active repository's private `paper_evidence/04_benchmarks/2026-10-27_alternative_methods_empath/` folder, whose parent analysis is also preserved. The primary specifications inherit observed pilots; the extension is exploratory, not preregistered. Every specification is retained, including LDA survivors. The Empath dictionary and MIT attribution are included in the aggregate data.

Current Table 3 and the reader-facing review use `scripts/build_three_panel_method_comparison.py`. Panel A reports VADER levels, Panel B the actual top words of LDA topics with conventional group differences, and Panel C the Empath lexical fields with conventional group differences. No topic interpretation, Discern feature mapping, or representative responses are shown. The nominal version uses two-sided Welch p < .05, unadjusted, and includes every qualifying topic across all twelve existing fits; none of the five topics in the first LDA run differed significantly between women and men. The builder also supports `--criterion bh` for within-model/method 5% Benjamini-Hochberg correction. `three_panel_method_evidence.json` records the complete selection, source hashes and all 150 topic / 194 field results. Earlier thematic and tier-comparison exhibits are archived. The full numerical calculations remain unchanged for audit.

The optional `--bertopic` argument adds Panel D from `scripts/run_bertopic_comparison.py`. BERTopic 0.17.4 uses a pinned local all-MiniLM-L6-v2 embedding model, seeded UMAP, HDBSCAN, and c-TF-IDF word representations. It fits only the 2,032 discovery responses without gender labels, then assigns the held-out responses to frozen topics or outliers. All outliers stay in percentage denominators and are reported separately. The recorded primary run yields 45 topics and 4 nominally differential topics on the common N=794 sample. Model/source hashes, all group tests, and settings are under `../appendices/data/alternative_methods/bertopic/`; exact environment pins are in `docs/BERTopic_requirements.txt`. Per-response embeddings, assignments, and the fitted model remain in the private repository evidence folder. Four-panel LaTeX uses longtable to preserve every displayed row across page breaks.

The four real runs reuse the same 800 reserved evaluation responses. They assess sensitivity to discovery randomness and model pools; they are not independent data replications. The descriptive theme grouping is post hoc and frozen in `configs/theme_grouping/`. Placebo counts use separate full-pipeline label shuffles, not just shuffling the final measured labels.

Placebo 3 required a disclosed operationalization repair after consolidation turned a negative-connotation construct into an exhaustive positive/negative/neutral question. `scripts/prepare_p03_operationalization_repair.py` versions the correction from discovery evidence without reading effects or p-values. `configs/measurement_repairs/` records both wordings and the versioned configuration. All 800 responses were classified anew for the changed question; the other 41 measurements were preserved. Use `build_paper_tables.py --repair` with the completed P03_REPAIRED artifact directory to reproduce the final exhibits using the second version only; the initial attempt is retained in the working archive. The builder refuses to finalize main exhibits with any unmeasured candidate. The repair followed the failure and was not preregistered.
''')
    print(json.dumps({'copied_source_files':len(copied),'destination':str(dest)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');main(p.parse_args().root)
