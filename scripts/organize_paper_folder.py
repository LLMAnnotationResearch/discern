"""Reversibly organize the local manuscript; preserve a hash-indexed archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def organize(root):
    root=Path(root).resolve()
    archive=root/'working/archive/reorganization_2026-10-27'
    ledger=archive/'move_manifest.json'
    if ledger.exists():
        print('Already organized: '+str(ledger));return
    moves={
        'FigsTables/build_figures.py':'code/scripts/build_figures.py',
        'FigsTables/FIGURE_CAPTIONS.md':'code/docs/FIGURE_CAPTIONS.md',
        'FigsTables/README_FIGURE_2.md':'code/docs/README_FIGURE_2.md',
        'SECTION_3_IMPLEMENTATION_REFERENCE.md':'code/docs/SECTION_3_IMPLEMENTATION_REFERENCE.md',
        'APPENDIX_B_PROMPTS.md':'appendices/notes/APPENDIX_B_PROMPTS.md',
        'LATEX_APPENDICES_README.md':'appendices/README.md',
        'appendices_start.tex':'appendices/appendices_start.tex',
        'appendices_preamble.tex':'appendices/appendices_preamble.tex',
        'appendices_preview.tex':'working/previews/appendices_preview.tex',
        'appendices_text_check.tex':'working/previews/appendices_text_check.tex',
        'appendix_D_preview.tex':'working/previews/appendix_D_preview.tex',
        'FigsTables/figure_2_preview.tex':'working/previews/figure_2_preview.tex',
        'FigsTables/table_4_theme_crosswalk.tex':'working/archive/reorganization_2026-10-27/table_4_theme_crosswalk.tex',
        'FigsTables/archive':'working/archive/previous_figure_designs',
        'FigsTables/section4_validation':'working/archive/section4_validation_2026-10-26',
        'Discern.pdf':'FigsTables/Discern.pdf',
    }
    entries=[]
    for old,new in moves.items():
        src,dst=root/old,root/new
        if not src.exists():raise FileNotFoundError(src)
        if dst.exists():raise FileExistsError(dst)
        for p in ([src] if src.is_file() else sorted(src.rglob('*'))):
            if p.is_file():
                entries.append({'old':str(p.relative_to(root)),
                                'new':str((dst if src.is_file() else dst/p.relative_to(src)).relative_to(root)),
                                'sha256':sha(p)})
    archive.mkdir(parents=True,exist_ok=True)
    # Preserve originals of integration helpers before making path-only repairs.
    for rel in ['FigsTables/build_figures.py','appendices_start.tex','appendices_preview.tex','LATEX_APPENDICES_README.md','appendices/appendix_D.tex']:
        dest=archive/'originals'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,dest)
    ledger.write_text(json.dumps({'status':'planned','files':entries},indent=2)+'\n')
    for old,new in moves.items():
        dest=root/new;dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(root/old),dest)
    for e in entries:
        assert sha(root/e['new'])==e['sha256'],e
    p=root/'code/scripts/build_figures.py'
    p.write_text(p.read_text().replace('see FIGURE_CAPTIONS.md.','see code/docs/FIGURE_CAPTIONS.md.').replace('OUT = Path(__file__).resolve().parent','OUT = Path(__file__).resolve().parents[2] / "FigsTables"'))
    p=root/'working/previews/appendices_preview.tex'
    p.write_text(p.read_text().replace(r'\input{appendices_preamble}',r'\input{appendices/appendices_preamble}').replace(r'\input{appendices_start}',r'\input{appendices/appendices_start}'))
    p=root/'appendices/appendices_start.tex'
    p.write_text(p.read_text().replace('Place this file at your manuscript root.','Input this file from the manuscript root as appendices/appendices_start.'))
    (root/'working/scratch').mkdir(parents=True,exist_ok=True)
    (root/'README.md').write_text('''# Discern paper

- `code/`: code and reproducibility documentation copied from the development checkout.
- `FigsTables/`: finalized main-paper exhibits and manuscript PDF. Shared Figure A1 assets remain here so existing LaTeX figure paths work.
- `appendices/`: Appendix A–D source, integration helpers, and candidate-level validation results.
- `working/`: previews, trial exhibits, run logs, and preserved earlier versions. Use `working/scratch/` for new ideas before promoting them.

From the Overleaf manuscript root, input `FigsTables/table_1_placebos` and then `FigsTables/table_2_stability_crosswalk`. Captions number automatically. Input `appendices/appendices_start` after the main text to include all appendices, or input Appendix D after the existing A–C inputs. See `appendices/README.md`.

The reorganization ledger is `working/archive/reorganization_2026-10-27/move_manifest.json`. It records every moved file and its original content hash; path changes have original copies alongside it. Raw responses and API credentials are outside this folder.
''')
    (root/'appendices/README.md').write_text('''# Appendices

Keep these files in the manuscript's `appendices/` folder. The shared Figure A1 assets are in `FigsTables/`.

The preamble needs `graphicx`, `amsmath`, `longtable`, and `chngcntr` (modern LaTeX already supplies the counter commands). `appendices_preamble.tex` provides a package helper if needed.

To include A–D once, use `\\input{appendices/appendices_start}` from the manuscript root. If A–C and appendix counter setup already exist, add only `\\clearpage` and `\\input{appendices/appendix_D}` after Appendix C. Do not call `\\appendix` again before D.

Appendix D contains all proposed candidates from four real runs and five full-pipeline placebo runs, with definitions, questions, effects, p-values, and validation tiers. `data/` holds machine-readable results and audits. `notes/` holds supporting source documentation. Preview source is under `working/previews/`.
''')
    ledger.write_text(json.dumps({'status':'moved_and_hash_verified','files':entries,'path_repairs':['code/scripts/build_figures.py','working/previews/appendices_preview.tex','appendices/appendices_start.tex'],'rewritten_documentation':['appendices/README.md']},indent=2)+'\n')
    print(json.dumps({'moved_files':len(entries),'ledger':str(ledger)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');organize(p.parse_args().root)
