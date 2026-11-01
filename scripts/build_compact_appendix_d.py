"""Consolidate Appendix D; retain every numerical result and a verbatim catalogue."""
import argparse
from collections import Counter
import csv
import hashlib
from html import escape
import json
from pathlib import Path
import shutil

from build_validation_latex import tex, TIER


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate_results_tex(rows, order, labels):
    """One numerical row per saved candidate, including all nonvalidated results."""
    ids=[r['exhibit_id'] for r in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate exhibit ID')
    if any(r['tier'] not in {'confirmed','suggestive','uncorrected','not_validated'} for r in rows):
        raise ValueError('Complete measurement is required for the compact appendix')
    lines=[r'\begingroup\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
           r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.04}',
           r'\begin{longtable}{@{}p{.06\linewidth}p{.49\linewidth}rrrrc@{}}',
           r'\caption{Complete candidate-level results}\label{tab:validation-all-candidates}\\',
           r'\hline ID & Candidate feature & \(d_1\) & \(d_2\) & Mean & \(p\) & Tier \\\hline\endfirsthead',
           r'\multicolumn{7}{l}{\textit{Complete candidate-level results (continued)}}\\\hline',
           r'ID & Candidate feature & \(d_1\) & \(d_2\) & Mean & \(p\) & Tier \\\hline\endhead',
           r'\hline\multicolumn{7}{r}{\footnotesize Continued on next page}\\\endfoot\hline\endlastfoot']
    emitted=[]
    for rid in order:
        group=[r for r in rows if r['run_id']==rid]
        lines.append(r'\multicolumn{7}{@{}l}{\textbf{'+tex(labels[rid])+r'}}\\*[2pt]')
        for row in group:
            values=[f'{100*float(row[k]):+.2f}' for k in ['d1','d2','mean_effect']]
            line=tex(row['exhibit_id'])+' & '+tex(row['feature_name'])+' & '+' & '.join(values+[f"{float(row['perm_p']):.4f}",TIER[row['tier']]])+r' \\'
            lines.append(line);emitted.append(row['exhibit_id'])
    if set(emitted)!=set(ids) or len(emitted)!=len(rows):raise ValueError('Candidate omission in consolidated results')
    return '\n'.join(lines+[r'\end{longtable}\endgroup'])+'\n'


def catalogue_html(rows, order, labels):
    parts=['''<!doctype html><html><head><meta charset="utf-8"><title>Validation feature catalogue</title>
<style>body{font:16px Georgia;line-height:1.5;max-width:1050px;margin:35px auto;padding:0 25px;color:#26332d}input{font:16px Georgia;padding:10px;width:95%;position:sticky;top:0;background:white;border:1px solid #aab5ae}article{border-top:1px solid #cbd2ce;padding:16px 0}h2{margin-top:35px}h3{font-size:18px;margin:0 0 12px}.stats,summary{font:13px Arial}.stats{background:#f1f4ef;padding:8px}p{margin:8px 0}nav a{margin-right:16px}details{font-size:14px;color:#46544c}</style></head><body>
<h1>Validation feature catalogue</h1><p>All saved candidates, including nonvalidated results. IDs match Appendix D. Definitions and questions are reproduced verbatim; statistics retain their saved precision in the accompanying CSV.</p>
<input id="search" type="search" placeholder="Search feature names, definitions, questions, or IDs" aria-label="Search feature catalogue"><nav>''']
    for rid in order:parts.append(f'<a href="#{escape(rid)}">{escape(labels[rid])}</a>')
    parts.append('</nav>')
    for rid in order:
        parts.append(f'<section><h2 id="{escape(rid)}">{escape(labels[rid])}</h2>')
        for r in rows:
            if r['run_id']!=rid:continue
            stats='; '.join(f'{name}: {100*float(r[key]):+.2f} pp' for name,key in [('Half 1','d1'),('Half 2','d2'),('Mean','mean_effect')])
            stats+=f"; p = {float(r['perm_p']):.6f}; tier {TIER[r['tier']]}"
            meta={k:r.get(k,'') for k in ['candidate_id','claimed_direction','measured_direction','source_splits','n_supporting_hypotheses','direction_conflict','same_sign']}
            parts.append(f'<article id="{escape(r["exhibit_id"])}"><h3>{escape(r["exhibit_id"]+". "+r["feature_name"])}</h3><p><b>Definition.</b> {escape(r["definition"])}</p><p><b>Classification question.</b> {escape(r["classification_question"])}</p><p class="stats">{escape(stats)}</p><details><summary>Discovery and measurement metadata</summary><pre>{escape(json.dumps(meta,indent=2))}</pre></details></article>')
        parts.append('</section>')
    parts.append('''<script>document.getElementById('search').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('article').forEach(a=>a.hidden=!a.textContent.toLowerCase().includes(q));});</script></body></html>''')
    return ''.join(parts)


def build(source, tex_path, preview_path):
    # Import at call time so the main exhibit builder can invoke this exporter.
    from build_paper_tables import ORDER, LABELS, REAL, crosswalk_tex, standalone
    source,tex_path,preview_path=Path(source),Path(tex_path),Path(preview_path)
    rows=list(csv.DictReader((source/'all_validation_results.csv').open()))
    counts={r['run_id']:r for r in csv.DictReader((source/'all_run_counts.csv').open())}
    settings={rid:json.loads((source/'validation_runs'/rid/'run_settings.json').read_text()) for rid in ORDER}
    assert set(counts)==set(ORDER) and len(rows)==317
    for rid in ORDER:
        group=[r for r in rows if r['run_id']==rid];s=settings[rid]
        assert len(group)==int(counts[rid]['proposed'])==int(counts[rid]['measured'])
        tally=Counter(r['tier'] for r in group)
        assert tally['confirmed']==int(counts[rid]['validated'])
        assert tally['suggestive']==int(counts[rid]['suggestive_only'])
        assert tally['uncorrected']==int(counts[rid]['uncorrected_only'])
        assert s['n_per_group']==400 and s['permutations']==5000
    themes=list(csv.DictReader((source/'appendix_all_themes.csv').open()))
    assert len(themes)==21
    summary=[r'\begin{table}[!htbp]\centering',r'\begingroup\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
             r'\caption{Validation runs and candidate counts}\label{tab:validation-run-designs}',
             r'\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.15}',
             r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}llrrrrr@{}}\hline',
             r'Run (ID prefix) & Pool & \shortstack{Discovery\\seed} & Candidates & V & S & U \\\hline']
    for i,rid in enumerate(ORDER):
        c=counts[rid];s=settings[rid];pool='Default' if rid=='E_DEFAULTS' else 'OpenAI' if rid=='E_OPENAI' else 'Reference'
        summary.append(tex(LABELS[rid]+f' ({chr(65+i)})')+' & '+pool+' & '+str(s['discovery_seed'])+' & '+' & '.join(c[k] for k in ['proposed','validated','suggestive_only','uncorrected_only'])+r' \\')
        if i==3:summary.append(r'\hline')
    summary += [r'\hline\end{tabular*}\par\vspace{4pt}',r'\noindent\begin{minipage}{\linewidth}\fontsize{8}{9.6}\selectfont',
                tex('Reference pool: gpt-4o-mini, claude-haiku, gpt-4.1-mini. Default adds DeepSeek; OpenAI excludes Claude. Pools apply to discovery and measurement; consolidation uses gpt-4.1. Each run reserves 800 responses (200 per group per half), uses 15 discovery calls per half with 15 texts per group, and 5,000 permutations. Reservation/split seed: 2027; model-assignment seed: 11. Placebo seed: 500; indices 0--4 for placebos 1--5. Default-pool measurement used 28 fallback judgments in two nonvalidated candidates.'),
                r'\end{minipage}\endgroup\end{table}']
    intro=('All 317 candidates from nine runs are reported below. Appendix C defines the selection rules. V denotes 5% FDR validation; S denotes 10% FDR only; U denotes the uncorrected-only tier; N denotes none. Exact definitions, questions, and generation metadata are in the accompanying feature catalogue (validation_feature_catalogue.csv).')
    results_note=('Effects are percentage points: women minus men for real runs, shuffled focal minus reference labels for placebos. Half-sample effects and their mean are shown. The reported p-values are replication-gated permutation p-values; p = 1 may reflect failure of the same-sign gate. Displayed values are rounded; selection uses full precision.')
    body=('% Drop-in consolidated Appendix D. Requires longtable.\n'+r'\section{Validation details}\label{app:validation}'+'\n'+tex(intro)+'\n'+'\n'.join(summary)+'\n'+
          r'\clearpage\subsection{Complete thematic crosswalk}'+'\n'+crosswalk_tex(themes,{rid:counts[rid] for rid in REAL},True).replace('Full questions: Appendix D.', 'Full questions: companion feature catalogue.')+'\n'+
          r'\clearpage\subsection{Complete candidate-level results}'+'\n'+r'{\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont '+tex(results_note)+r'\par}'+'\n'+candidate_results_tex(rows,ORDER,LABELS))
    assert body.count(r'\caption{')==3
    for r in rows:assert body.count(tex(r['exhibit_id'])+' & ')==1
    tex_path.parent.mkdir(parents=True,exist_ok=True);preview_path.parent.mkdir(parents=True,exist_ok=True)
    tex_path.write_text(body);preview_path.write_text(standalone(body,True))
    catalogue=source/'validation_feature_catalogue.csv';shutil.copy2(source/'all_validation_results.csv',catalogue)
    (source/'validation_feature_catalogue.html').write_text(catalogue_html(rows,ORDER,LABELS))
    report={'layout':'three_consolidated_tables','runs':len(ORDER),'candidates':len(rows),'tables':3,
            'all_candidates_retained':True,'catalogue_csv_sha256':digest(catalogue),
            'source_csv_sha256':digest(source/'all_validation_results.csv'),'appendix_tex_sha256':digest(tex_path),
            'builder_sha256':digest(__file__)}
    assert report['catalogue_csv_sha256']==report['source_csv_sha256']
    (source/'compact_appendix_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--tex',required=True);p.add_argument('--preview',required=True);a=p.parse_args()
    print(json.dumps(build(a.source,a.tex,a.preview),indent=2))
