"""Show native alternative-method outputs, optionally adding a BERTopic panel."""
import argparse
import csv
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discern.validation import sha256
from build_baseline_exhibits import htable, standalone
from build_validation_latex import tex


def select_differences(rows,method,criterion):
    if criterion not in {'nominal','bh'}:raise ValueError('Unknown significance criterion')
    eligible=[r for r in rows if r['method']==method and r['sample']=='common' and
              (method!='Empath' or r['model_id']=='empath_supplied')]
    return [r for r in eligible if (float(r['welch_p'])<.05 if criterion=='nominal' else str(r['welch_q05']).lower()=='true')]


def formatted_p(value):
    return '<.001' if float(value)<.001 else f'{float(value):.3f}'


def latex_p(value):
    return r'\(<.001\)' if float(value)<.001 else f'{float(value):.3f}'


def note_for(criterion,bertopic=None):
    rule='two-sided Welch p < .05, unadjusted' if criterion=='nominal' else 'two-sided Welch tests with 5% Benjamini–Hochberg correction within each fit/method'
    panels='Panels B–D' if bertopic else 'Panels B/C'
    note=('Women versus men; N = 794. '+panels+' use '+rule+'. LDA spans 12 fits (K: topic count; S: seed index; T: topic). None of the five topics in the first LDA run differed significantly between women and men. Topic/field means are percentages; VADER retains its native scale.')
    if bertopic:note+=f" BERTopic levels are assignment shares; denominators include {100*bertopic['common_outlier_count']/bertopic['common_n']:.1f}% unassigned responses."
    return note


def panel_tex(panels,criterion,bertopic=None):
    if 'D' in panels:return four_panel_tex(panels,criterion,bertopic)
    lines=[r'% Native method outputs only: no topic labels or representative responses.',
           r'\begin{table}[!htbp]\centering',r'\def\baselinestretch{1}\fontsize{8.5}{10}\selectfont',
           r'\caption{Group differences from alternative text methods}\label{tab:alternative-methods}',
           r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.08}',
           r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrr@{}}\hline',
           r'\multicolumn{4}{@{}l}{\textit{A. VADER sentiment levels}}\\[2pt]',
           r'Score & Women & Men & \(p\)\\\hline']
    for r in panels['A']:lines.append('Compound & '+f"{r['women']:.3f} & {r['men']:.3f} & "+latex_p(r['p'])+r' \\')
    lines += [r'\hline\end{tabular*}\par\vspace{7pt}',
              r'\edef\ModelWidth{\the\dimexpr.16\linewidth-2\tabcolsep\relax}',
              r'\edef\WordsWidth{\the\dimexpr\linewidth-\ModelWidth-100pt-8\tabcolsep\relax}',
              r'\begin{tabular}{@{}p{\ModelWidth}p{\WordsWidth}rrr@{}}\hline',
              r'\multicolumn{5}{@{}l}{\textit{B. LDA topics with significant group differences}}\\[2pt]',
              r'Model/topic & Top eight words & Women (\%) & Men (\%) & \(p\)\\\hline']
    for r in panels['B']:
        lines.append(tex(r['label'])+' & '+tex(r['display_words'])+' & '+f"{100*r['women']:.2f} & {100*r['men']:.2f} & "+latex_p(r['p'])+r' \\[1pt]')
    if not panels['B']:lines.append(r'\multicolumn{5}{l}{No topics meet the stated significance criterion.}\\')
    lines += [r'\hline\end{tabular}\par\vspace{7pt}',
              r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrr@{}}\hline',
              r'\multicolumn{4}{@{}l}{\textit{C. Empath lexical fields with significant group differences}}\\[2pt]',
              r'Lexical field & Women (\%) & Men (\%) & \(p\)\\\hline']
    for r in panels['C']:lines.append(tex(r['label'])+' & '+f"{100*r['women']:.3f} & {100*r['men']:.3f} & "+latex_p(r['p'])+r' \\')
    if not panels['C']:lines.append(r'\multicolumn{4}{l}{No fields meet the stated significance criterion.}\\')
    lines += [r'\hline\end{tabular*}\par\vspace{4pt}',
              r'\noindent\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{8}{9.4}\selectfont',
              r'\textit{Notes.} '+tex(note_for(criterion)).replace('p < .05',r'\(p<.05\)'),r'\end{minipage}\end{table}']
    return '\n'.join(lines)+'\n'


def four_panel_tex(panels,criterion,bertopic):
    """A breakable table keeps all qualifying rows and never shrinks them to fit."""
    lines=[r'% Four native-output panels. Requires longtable in the manuscript preamble.',
           r'\begingroup\def\baselinestretch{1}\fontsize{8.5}{10}\selectfont',
           r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.08}',
           r'\edef\ModelWidth{\the\dimexpr.16\linewidth-2\tabcolsep\relax}',
           r'\edef\WordsWidth{\the\dimexpr\linewidth-\ModelWidth-100pt-8\tabcolsep\relax}',
           r'\begin{longtable}{@{}p{\ModelWidth}p{\WordsWidth}rrr@{}}',
           r'\caption{Group differences from alternative text methods}\label{tab:alternative-methods}\\',
           r'\endfirsthead',r'\multicolumn{5}{l}{\textit{Group differences from alternative text methods (continued)}}\\\hline\endhead',
           r'\hline\multicolumn{5}{r}{\footnotesize Continued on next page}\\\endfoot\hline\endlastfoot',
           r'\multicolumn{5}{@{}l}{\textit{A. VADER sentiment levels}}\\*[2pt]',
           r'\multicolumn{2}{@{}l}{Score} & Women & Men & \(p\)\\*\hline']
    for r in panels['A']:lines.append(r'\multicolumn{2}{@{}l}{Compound} & '+f"{r['women']:.3f} & {r['men']:.3f} & "+latex_p(r['p'])+r' \\')
    for key,title in [('B','LDA topics'),('C','Empath lexical fields'),('D','BERTopic topics')]:
        lines.append(r'\hline\multicolumn{5}{@{}l}{\textit{'+key+'. '+title+r' with significant group differences}}\\*[2pt]')
        if key=='C':lines.append(r'\multicolumn{2}{@{}l}{Lexical field} & Women (\%) & Men (\%) & \(p\)\\*\hline')
        else:lines.append(r'Model/topic & Top eight words & Women (\%) & Men (\%) & \(p\)\\*\hline')
        for r in panels[key]:
            prefix=(r'\multicolumn{2}{@{}l}{'+tex(r['label'])+'}' if key=='C' else tex(r['label'])+' & '+tex(r['display_words']))
            precision=3 if key=='C' else 2
            lines.append(prefix+' & '+f"{100*r['women']:.{precision}f} & {100*r['men']:.{precision}f} & "+latex_p(r['p'])+r' \\')
        if not panels[key]:lines.append(r'\multicolumn{5}{l}{None meet the stated significance criterion.}\\')
    lines += [r'\end{longtable}\noindent\begin{minipage}{\linewidth}\fontsize{8}{9.4}\selectfont',
              r'\textit{Notes.} '+tex(note_for(criterion,bertopic)).replace('p < .05',r'\(p<.05\)'),
              r'\end{minipage}\endgroup']
    return '\n'.join(lines)+'\n'


def build(source,out,criterion,bertopic_path=None):
    source,out=Path(source).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['output_sha256'].items():assert sha256(source/name)==h,name
    rows=list(csv.DictReader((source/'all_dimension_results.csv').open()))
    topics={(r['model_id'],r['dimension']):r['top_words'] for r in csv.DictReader((source/'lda_topics.csv').open())}
    models=sorted({r['model_id'] for r in rows if r['method']=='LDA'})
    seeds=sorted({int(m.rsplit('seed',1)[1]) for m in models});assert len(models)==12 and len(seeds)==3
    def native(r):
        result={'model_id':r['model_id'],'dimension':r['dimension'],'women':float(r['focal_mean_native']),
                'men':float(r['reference_mean_native']),'p':float(r['welch_p'])}
        if r['method']=='LDA':
            k=int(r['model_id'].split('_')[1][1:]);seed=int(r['model_id'].rsplit('seed',1)[1]);topic=int(r['dimension'].split('_')[1])
            words=topics[(r['model_id'],r['dimension'])]
            result.update(label=f'K{k}/S{seeds.index(seed)+1}/T{topic}',K=k,seed=seed,
                          words=words,display_words=', '.join(words.split(', ')[:8]))
        elif r['method']=='Empath':result['label']=r['dimension'].replace('_',' ')
        else:result['label']='VADER compound'
        return result
    vader=[native(r) for r in rows if r['method']=='Sentiment' and r['sample']=='common']
    lda=sorted([native(r) for r in select_differences(rows,'LDA',criterion)],key=lambda r:(r['K'],r['seed'],r['dimension']))
    empath=sorted([native(r) for r in select_differences(rows,'Empath',criterion)],key=lambda r:r['dimension'])
    panels={'A':vader,'B':lda,'C':empath};assert len(vader)==1
    bertopic=None;all_bertopic=[]
    if bertopic_path:
        bp=Path(bertopic_path).resolve();bertopic=json.loads((bp/'manifest.json').read_text())
        for name,h in bertopic['output_sha256'].items():assert sha256(bp/name)==h,name
        assert bertopic['source_base_manifest_sha256']==sha256(source/'manifest.json')
        for r in csv.DictReader((bp/'group_differences.csv').open()):
            if r['sample']!='common':continue
            topic=int(r['topic_id']);words=r['words']
            all_bertopic.append({'model_id':'BERTopic','dimension':str(topic),'label':f'T{topic}' if topic>=0 else 'Unassigned/outlier',
                                'women':float(r['women']),'men':float(r['men']),'p':float(r['welch_p']),
                                'words':words,'display_words':', '.join(words.split(', ')[:8]),
                                'is_outlier':topic==-1,'BH':r['welch_q05']=='True'})
        panels['D']=[r for r in all_bertopic if not r['is_outlier'] and (r['p']<.05 if criterion=='nominal' else r['BH'])]
    original=[r for r in rows if r['method']=='LDA' and r['model_id']=='lda_k05_seed260026' and r['sample']=='common']
    assert len(original)==5
    primary_passes=select_differences(original,'LDA',criterion);assert not primary_passes
    fragment=panel_tex(panels,criterion,bertopic)
    (out/'table_3_alternative_methods.tex').write_text(fragment)
    (out/'table_3_alternative_methods_preview.tex').write_text(standalone(fragment))
    export=[{'panel':key,**r} for key,group in panels.items() for r in group]
    columns=list(dict.fromkeys(key for r in export for key in r))
    with (out/'table_3_alternative_methods.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(export)
    def html_rows(group,percent=False):
        return [{**r,'women_display':f"{(100 if percent else 1)*r['women']:.3f}",
                 'men_display':f"{(100 if percent else 1)*r['men']:.3f}",'p_display':formatted_p(r['p'])} for r in group]
    css='body{font:16px Georgia;line-height:1.45;max-width:1120px;margin:30px auto;padding:0 24px;color:#25352c}h1,h2{line-height:1.2}table{border-collapse:collapse;width:100%;font:14px Arial;margin:18px 0}td,th{padding:8px;text-align:left;vertical-align:top;border-bottom:1px solid #cbd3cd}th{background:#edf2ed}small{font:13px Arial;color:#46564b}details{margin:24px 0}summary{cursor:pointer;font-weight:bold}'
    start='<!doctype html><html><head><meta charset="utf-8"><title>Group differences from alternative text methods</title><style>'+css+'</style></head><body>'
    html=[start,'<h1>Group differences from alternative text methods</h1>',
          '<h2>Panel A. VADER sentiment levels</h2>',htable(html_rows(vader),[('label','Score'),('women_display','Women'),('men_display','Men'),('p_display','p')]),
          '<h2>Panel B. LDA topics with significant group differences</h2>',
          '<p><small>We tried LDA with 5, 10, 15, and 20 topics, each with three initializations. None of the five topics in the first run differed significantly between women and men. Rows below show the qualifying topics from all twelve runs.</small></p>',
          htable(html_rows(lda,True),[('label','Model/topic'),('display_words','Top eight words'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]) if lda else '<p>No topics meet the stated significance criterion.</p>',
          '<h2>Panel C. Empath lexical fields with significant group differences</h2>',
          htable(html_rows(empath,True),[('label','Lexical field'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]) if empath else '<p>No fields meet the stated significance criterion.</p>',
          ]
    if bertopic:
        html+=['<h2>Panel D. BERTopic topics with significant group differences</h2>',
               htable(html_rows(panels['D'],True),[('label','Topic'),('display_words','Top eight words'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]) if panels['D'] else '<p>No topics meet the stated significance criterion.</p>']
    html+=['<p><small>'+escape(note_for(criterion,bertopic))+'</small></p>']
    compact=''.join(html)+ '</body></html>'
    (out/'table_3_alternative_methods.html').write_text(compact)
    all_lda=[native(r) for r in rows if r['method']=='LDA' and r['sample']=='common']
    all_empath=[native(r) for r in rows if r['method']=='Empath' and r['model_id']=='empath_supplied' and r['sample']=='common']
    assert len(all_lda)==150 and len(all_empath)==194
    html+=['<details><summary>All 150 LDA topics: full word lists and conventional tests</summary>',
           htable(html_rows(all_lda,True),[('label','Model/topic'),('words','Highest-weight words'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]),'</details>',
           '<details><summary>All 194 Empath lexical fields and conventional tests</summary>',
           htable(html_rows(all_empath,True),[('label','Lexical field'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]),'</details>',
           ]
    if bertopic:
        html+=['<details><summary>All BERTopic topics and unassigned responses</summary>',
               htable(html_rows(all_bertopic,True),[('label','Topic'),('words','Highest-weight words'),('women_display','Women (%)'),('men_display','Men (%)'),('p_display','p')]),'</details>',
               '<small>BERTopic was fitted on 2,032 discovery responses, then assigned the 794 common evaluation responses to frozen topics or the unassigned category. Words are the native c-TF-IDF representation, with no generated topic descriptions.</small>']
    html+=['<p><small>Seed indices: '+escape(', '.join(f'S{i+1}={s}' for i,s in enumerate(seeds)))+'. Full results include every topic and supplied field.</small></p></body></html>']
    (out/'alternative_methods_review.html').write_text(''.join(html))
    appendix=fragment.replace(r'\caption{Group differences from alternative text methods}',r'\caption{Differential outputs of alternative text methods}')
    appendix=r'\section{Alternative text-method outputs}\label{app:alternative-methods}'+'\n'+appendix
    (out/'appendix_E_alternative_methods.tex').write_text(appendix)
    (out/'appendix_E_alternative_methods_preview.tex').write_text(standalone(appendix,True))
    evidence={'criterion':criterion,'test':'two-sided Welch unequal-variance test','sample_n':794,
              'multiplicity':'unadjusted' if criterion=='nominal' else 'BH 5% within each LDA fit / full Empath family',
              'panels':panels,'all_lda':all_lda,'all_empath':all_empath,'seeds':seeds,
              'topic_words_displayed':8,'full_topic_words_available':12,
              'original_five_topic_fit_significant_count':0,'LDA_fits_included':12,
              'source_analysis_manifest_sha256':sha256(source/'manifest.json'),'builder_sha256':sha256(__file__),
              'no_topic_interpretations':True,'no_representative_responses':True,'all_bertopic':all_bertopic,
              'bertopic_manifest':bertopic,'new_BERTopic_fit':bool(bertopic),
              'bertopic_source_manifest_sha256':sha256(bp/'manifest.json') if bertopic else None}
    (out/'three_panel_method_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    report={'layout':'four_panels_native_outputs' if bertopic else 'three_panels_native_outputs','criterion':criterion,'test':'two-sided Welch',
            'panel_A_rows':len(vader),'panel_B_rows':len(lda),'panel_C_rows':len(empath),
            'panel_D_rows':len(panels.get('D',[])),
            'source':str(source),'files_sha256':{p.name:sha256(p) for p in out.iterdir() if p.is_file()}}
    (out/'exhibit_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','out']:p.add_argument('--'+name,required=True)
    p.add_argument('--criterion',choices=['nominal','bh'],default='nominal')
    p.add_argument('--bertopic',help='completed BERTopic comparison artifact folder')
    a=p.parse_args();build(a.source,a.out,a.criterion,a.bertopic)
