"""Build a compact Table 3 and review catalogue from audited baseline outputs."""
import argparse
import csv
from html import escape
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_validation_latex import tex
from discern.validation import sha256

TOPIC_LABELS = {
    'topic_01':'Management and red tape',
    'topic_02':'Pyramid and scheme metaphors',
    'topic_03':'Advancement and growth',
    'topic_04':'Chain of command and decisions',
    'topic_05':'Management levels and layers',
}


def read(path):return list(csv.DictReader(path.open()))


def number(value,sign=False):return f'{float(value):+.3f}' if sign else f'{float(value):.3f}'


def htable(rows,columns):
    return '<table><thead><tr>'+''.join('<th>'+escape(label)+'</th>' for _,label in columns)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(r.get(key,'')))+'</td>' for key,_ in columns)+'</tr>' for r in rows)+'</tbody></table>'


def primary_summaries(summaries,primary_model):
    methods=['Sentiment']+(['Empath'] if any(r['method']=='Empath' for r in summaries) else [])+['LDA','Discern']
    return [next(r for r in summaries if r['method']==method and r['sample']=='common' and
                 (method!='LDA' or r['model_id']==primary_model) and
                 (method!='Empath' or r['model_id']=='empath_supplied')) for method in methods]


def table_tex(summaries,dimensions,primary_model,n):
    selected=primary_summaries(summaries,primary_model)
    lines=[r'% Draft Table 3: audited conventional-method comparison. No additional packages required.',
           r'\begin{table}[!htbp]\centering',r'\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
           r'\caption{Comparison with conventional text methods}\label{tab:alternative-methods}',
           r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.18}',
           r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrr@{}}\hline',
           r'\multicolumn{5}{@{}l}{\textit{A. Outputs and validation tiers}}\\[3pt]',
           r'Method & \shortstack{Output\\dimensions} & \shortstack{Validated\\(5\% FDR)} & \shortstack{Suggestive only\\(10\% FDR)} & \shortstack{Uncorrected\\only}\\\hline']
    for row in selected:
        label={'Sentiment':'Sentiment (VADER)','Empath':'Empath (supplied categories)','LDA':'LDA (5 topics)','Discern':'Discern (main run)'}[row['method']]
        lines.append(tex(label)+' & '+' & '.join(row[k] for k in ['dimensions','validated','suggestive_only','uncorrected_only'])+r' \\')
        if row['method']=='LDA':
            sensitivity=[r for r in summaries if r['method']=='LDA']
            ranges=[]
            for key in ['dimensions','validated','suggestive_only','uncorrected_only']:
                values=[int(r[key]) for r in sensitivity]
                ranges.append(str(min(values))+'--'+str(max(values)))
            lines.append(f'LDA sensitivity ({len(sensitivity)} fits) & '+' & '.join(ranges)+r' \\')
    lines += [r'\hline\end{tabular*}\par\vspace{10pt}',
              r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrr@{}}\hline',
              r'\multicolumn{5}{@{}l}{\textit{B. All sentiment and primary LDA dimensions}}\\[3pt]',
              r'Dimension & Women & Men & Difference & \(p\)\\\hline']
    for row in dimensions:
        label='Sentiment (compound)' if row['method']=='Sentiment' else TOPIC_LABELS[row['dimension']]
        lines.append(tex(label)+' & '+' & '.join([number(row['focal_mean_native']),number(row['reference_mean_native']),
                                                    number(row['mean_half_difference_native'],True),number(row['perm_p'])])+r' \\')
    note=(f'Women versus men in tall hierarchies; N = {n}. Tiers use 5,000 same-sign permutations and within-method FDR. Differences average half-sample gaps in native units. Empath uses all supplied categories; LDA sensitivity varies topic count and seed. Counts do not rank measurement quality.')
    lines += [r'\hline\end{tabular*}\par\vspace{4pt}',
              r'\noindent\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{8}{9.6}\selectfont',
              r'\textit{Notes.} '+tex(note),r'\end{minipage}\end{table}']
    return '\n'.join(lines)+'\n'


def standalone(body,appendix=False):
    prefix=r'\documentclass[letterpaper,12pt]{article}'+'\n'
    if r'\begin{longtable}' in body:prefix+=r'\usepackage{longtable}'+'\n'
    prefix+=r'\begin{document}'+'\n'
    if appendix:prefix+=r'\appendix\setcounter{section}{4}\counterwithin{table}{section}\renewcommand{\thetable}{\thesection\arabic{table}}'+'\n'
    else:prefix+=r'\setcounter{table}{2}'+'\n'
    return prefix+body+'\n'+r'\end{document}'+'\n'


def build(source,out):
    source,out=Path(source),Path(out);out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['output_sha256'].items():assert sha256(source/name)==h,name
    plan=json.loads((source/'analysis_plan.json').read_text())
    summaries,dimensions,topics=map(lambda name:read(source/name),['method_summary.csv','all_dimension_results.csv','lda_topics.csv'])
    primary_model=f"lda_k{manifest['primary_lda_K']:02}_seed{plan['primary_lda']['seed']}"
    primary=[r for r in dimensions if r['sample']=='common' and
             (r['method']=='Sentiment' or (r['method']=='LDA' and r['model_id']==primary_model))]
    assert len(primary)==6 and manifest['primary_lda_K']==5
    assert len([r for r in summaries if r['method']=='LDA'])==12
    fragment=table_tex(summaries,primary,primary_model,manifest['primary_sample_n'])
    (out/'table_3_alternative_methods.tex').write_text(fragment)
    (out/'table_3_alternative_methods_preview.tex').write_text(standalone(fragment))
    primary_export=primary+[r for r in dimensions if r['method']=='Empath' and r['model_id']=='empath_supplied' and r['sample']=='common']
    with (out/'table_3_alternative_methods.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(primary[0]));w.writeheader();w.writerows(primary_export)
    primary_topics=[{**r,'label':TOPIC_LABELS[r['dimension']]} for r in topics if r['model_id']==primary_model]
    sensitivity=[r for r in summaries if r['method']=='LDA']
    has_empath='empath' in manifest
    appendix=[r'% Optional compact Appendix E; input after D if retained.',r'\section{Alternative text methods}\label{app:alternative-methods}',
              tex(('VADER compound, Empath category proportions, and LDA topic proportions' if has_empath else 'VADER compound scores and LDA topic proportions')+' are compared with the archived Discern run. LDA was fitted on 2,032 discovery responses, with vocabulary and topic-count selection excluding the evaluation sample. Discovery-only validation selected five topics from 5/10/15/20. The common evaluation sample has 794 responses with retained LDA vocabulary; full-sample sensitivity uses 800. Scores retain their native units: VADER compound spans -1 to 1; topic and lexical-category proportions span 0 to 1.'),
              '\n'+tex('All models use the saved halves and the production same-sign selection rule with 5,000 permutations and within-model BH correction. The additional conventional test uses two-sided Welch tests and within-model BH at 5%. This is an exploratory extension of observed pilots; sensitivity fits are all reported and are not selected by gender differences.'),
              r'\begin{table}[!htbp]\centering\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
              r'\caption{Primary LDA topic descriptions}\label{tab:lda-topic-descriptions}',
              r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}',
              r'\edef\TopicNameWidth{\the\dimexpr.34\linewidth-2\tabcolsep\relax}',
              r'\edef\TopicWordWidth{\the\dimexpr.66\linewidth-2\tabcolsep\relax}',
              r'\begin{tabular}{@{}p{\TopicNameWidth}p{\TopicWordWidth}@{}}\hline',r'Descriptive label & Highest-weight words\\\hline']
    for r in primary_topics:appendix.append(tex(r['label'])+' & '+tex(', '.join(r['top_words'].split(', ')[:8]))+r' \\')
    appendix += [r'\hline\end{tabular}\end{table}',
                 r'\begin{table}[!htbp]\centering\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
                 r'\caption{Complete LDA specification sensitivity}\label{tab:lda-sensitivity}',
                 r'\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.08}',
                 r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}rrrrrr@{}}\hline',
                 r'Topics & Seed & V & S & U & \shortstack{Conventional\\5\% BH}\\\hline']
    for r in sensitivity:appendix.append(' & '.join(str(int(float(r[k]))) for k in ['K','seed','validated','suggestive_only','uncorrected_only','welch_q05'])+r' \\')
    appendix += [r'\hline\end{tabular*}\par\vspace{4pt}',
                 r'\noindent\begin{minipage}{\linewidth}\fontsize{8}{9.6}\selectfont',
                 tex('V: validated at 5% FDR; S: 10% FDR only; U: same-sign p < .05 outside both FDR tiers. LDA uses batch fitting for 30 iterations, English stop words, min_df = 2, max_df = .95, and symmetric priors 1/K. Topic labels summarize top words; they are not independently validated constructs. Full results for every topic, scores, and descriptive associations are in the companion data.'),
                 r'\end{minipage}\end{table}']
    if has_empath:
        ec=manifest['empath']['category_count']
        appendix.insert(3,tex(f'Empath {manifest["empath"]["version"]} supplies all {ec} categories, including constant categories in the correction family. Primary matching uses casefolded Unicode word tokens with internal apostrophes retained; proportions divide category matches by all tokens. Original-case whitespace matching is a sensitivity check. Complete category results and dictionary coverage are in the companion data.'))
    appendix='\n\n'.join(appendix)+'\n'
    (out/'appendix_E_alternative_methods.tex').write_text(appendix)
    (out/'appendix_E_alternative_methods_preview.tex').write_text(standalone(appendix,True))
    # The HTML report retains every topic/feature, not only significant dimensions.
    name_map={r['candidate_id']:r['feature_name'] for r in read(source/'discern_feature_names.csv')}
    detail=[{**r,'description':name_map.get(r['dimension'],TOPIC_LABELS.get(r['dimension'],r['dimension'])) if r['method']!='LDA' or r['model_id']==primary_model else r['dimension']} for r in dimensions]
    overlap=read(source/'descriptive_overlap.csv')
    topic_map={(r['model_id'],r['dimension']):r['top_words'] for r in topics}
    sensitivity_findings=[{**r,'top_words':topic_map[(r['model_id'],r['dimension'])],
                          'effect':number(r['mean_half_difference_native'],True)} for r in dimensions if r['method']=='LDA' and r['tier'] in ['V','S']]
    overlap_summary=[]
    for cid,name in name_map.items():
        rows=[r for r in overlap if r['candidate_id']==cid]
        sent=next(r for r in rows if r['baseline_dimension']=='compound')
        topic=max((r for r in rows if r['baseline_dimension']!='compound'),key=lambda r:abs(float(r['pearson_r'] or 0)))
        overlap_summary.append({'feature':name,'validated':sent['validated_common_sample'],
                                'sentiment_r':number(sent['pearson_r'],True),
                                'closest_topic':TOPIC_LABELS[topic['baseline_dimension']],
                                'topic_r':number(topic['pearson_r'],True)})
    css='body{font:16px Georgia;line-height:1.5;max-width:1200px;margin:30px auto;padding:0 24px;color:#26332d}table{border-collapse:collapse;width:100%;font:14px Arial;margin:20px 0}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccd2cc}th{background:#edf1ed}summary{cursor:pointer;font-weight:bold}h1,h2{line-height:1.2}a{color:#286251}.scroll{overflow:auto}input{padding:8px;font-size:16px;width:90%;position:sticky;top:0;background:white}'
    selected=primary_summaries(summaries,primary_model)
    displayed=[]
    for row in selected:
        displayed.append(row)
        if row['method']=='LDA':
            ranged={'method':f'LDA sensitivity ({len(sensitivity)} fits)','n':str(manifest['primary_sample_n'])}
            for key in ['dimensions','validated','suggestive_only','uncorrected_only']:
                values=[int(r[key]) for r in sensitivity];ranged[key]=f'{min(values)}–{max(values)}'
            displayed.append(ranged)
    html_fragment=('<!doctype html><html><head><meta charset="utf-8"><title>Table 3: Alternative text methods</title><style>'+css+'</style></head><body><h1>Table 3. Comparison with conventional text methods</h1><h2>A. Outputs and validation tiers</h2>'+htable(displayed,[('method','Method'),('n','N'),('dimensions','Output dimensions'),('validated','Validated (5% FDR)'),('suggestive_only','Suggestive only (10% FDR)'),('uncorrected_only','Uncorrected only')])+'<h2>B. All sentiment and primary LDA dimensions</h2>'+htable([{**r,'label':'Sentiment (compound)' if r['method']=='Sentiment' else TOPIC_LABELS[r['dimension']],**{k:number(r[k],k=='mean_half_difference_native') for k in ['focal_mean_native','reference_mean_native','mean_half_difference_native','perm_p']}} for r in primary],[('label','Dimension'),('focal_mean_native','Women'),('reference_mean_native','Men'),('mean_half_difference_native','Mean half-gap'),('perm_p','Same-sign p')])+f'<p>Women versus men in tall hierarchies; N={manifest["primary_sample_n"]}. Tiers use 5,000 same-sign permutations and within-method FDR. Differences average the two half-sample gaps in native units. Primary LDA uses discovery-only perplexity; sensitivity varies topic count and seed. Counts do not rank measurement quality.</p></body></html>')
    (out/'table_3_alternative_methods.html').write_text(html_fragment)
    html=['<!doctype html><html><head><meta charset="utf-8"><title>Alternative text methods: Hurst comparison</title><style>'+css+'</style></head><body>',
          '<h1>Alternative text methods: Hurst comparison</h1><p>Women versus men within tall hierarchies. This review draft extends existing pilots and retains every result. All primary comparisons use the same 794 evaluation responses; model fitting uses the disjoint 2,032-response discovery pool.</p>',
          '<h2>Primary comparison</h2><p>V: validated at 5% FDR; S: 10% FDR only; U: uncorrected only. Corrections apply within each method or model. Differences in output counts do not establish relative measurement quality.</p>',
          htable(selected,
                 [('method','Method'),('n','N'),('dimensions','Dimensions'),('validated','V'),('suggestive_only','S'),('uncorrected_only','U'),('welch_q05','Conventional 5% BH')]),
          '<h2>What the baselines measure</h2><p>Sentiment measures overall valence; Empath measures lexical proportions for predefined categories; LDA measures mixed membership in topics defined by word co-occurrence. A substantive subject appearing in a topic is distinct from detecting a gender difference in that topic. The labels below describe top words; they do not establish fidelity to the underlying constructs.</p>',
          htable(primary_topics,[('dimension','Topic'),('label','Descriptive label'),('top_words','Highest-weight words')]),
          htable([{**r,**{k:number(r[k],k in ['mean_half_difference_native','d1_native','d2_native']) for k in ['focal_mean_native','reference_mean_native','mean_half_difference_native','d1_native','d2_native','perm_p','welch_p']}} for r in primary],
                 [('dimension','Dimension'),('focal_mean_native','Women'),('reference_mean_native','Men'),('d1_native','Half 1'),('d2_native','Half 2'),('mean_half_difference_native','Mean difference'),('perm_p','Same-sign p'),('welch_p','Welch p'),('tier','Tier')]),
          '<h2>All LDA specifications</h2><p>The primary model is K=5, seed 260026, chosen in the original pilot using discovery-only validation perplexity. The grid below was recorded before these sensitivity fits. Every specification is shown; no model is selected for a stronger gender difference. These are correlated sensitivity analyses, not additional independent replications.</p>',
          htable(sensitivity,[('K','Topics'),('seed','Seed'),('primary','Primary'),('validated','V'),('suggestive_only','S'),('uncorrected_only','U'),('welch_q05','Conventional 5% BH')]),
          '<h3>Topics reaching either FDR tier in the sensitivity grid</h3><p>These are results from particular specifications, with correction within each fitted model. They are not discoveries from a pooled search across models.</p>',
          htable(sensitivity_findings,[('model_id','Specification'),('dimension','Topic'),('top_words','Highest-weight words'),('effect','Native mean half-gap'),('perm_p','Same-sign p'),('tier','Tier')]),
          '<h2>Full-sample sensitivity</h2>',htable([r for r in summaries if r['sample']=='full'],[('method','Method'),('n','N'),('dimensions','Dimensions'),('validated','V'),('suggestive_only','S'),('uncorrected_only','U'),('welch_q05','Conventional 5% BH')]),
          '<h2>Descriptive overlap with Discern</h2><p>These are correlations on the common sample. The closest topic is selected by absolute correlation among the five primary topics. This is an exploratory association summary; it is not an accuracy test, an equivalence test, or proof of incremental information. Both validated and nonvalidated Discern candidates are retained.</p>',
          '<details><summary>All 35 Discern features and their associations</summary>'+htable(overlap_summary,[('feature','Discern feature'),('validated','Validated on common sample'),('sentiment_r','Sentiment r'),('closest_topic','Closest topic'),('topic_r','Topic r')])+'</details>',
          '<h2>Complete numerical output</h2><input id="search" type="search" placeholder="Filter all dimensions" aria-label="Filter all dimensions"><div class="scroll" id="results">',
          htable(detail,[('method','Method'),('model_id','Specification'),('sample','Sample'),('description','Dimension'),('d1_native','Half 1'),('d2_native','Half 2'),('perm_p','Same-sign p'),('tier','Tier'),('welch_p','Welch p'),('welch_q05','Welch 5% BH')]),'</div>',
          '<details><summary>All LDA topic words</summary>'+htable(topics,[('model_id','Specification'),('dimension','Topic'),('top_words','Highest-weight words')])+'</details>',
          '<h2>Interpretation and next work</h2><p>This comparison evaluates the reported specifications on this contrast. It does not establish that a method cannot find useful distinctions in other settings. Independent textual-fidelity and substantive-coverage ratings remain to be done. Empath supplies its own predefined category system for the dictionary-based comparison.</p>',
          '<p>Method sources: <a href="https://github.com/cjhutto/vaderSentiment">VADER authors</a>; <a href="https://www.jmlr.org/papers/v3/blei03a.html">Blei, Ng and Jordan (2003)</a>; <a href="https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html">LDA implementation</a>.</p>',
          '<script>document.getElementById("search").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("#results tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></body></html>']
    if has_empath:
        empath_rows=[r for r in dimensions if r['method']=='Empath' and r['model_id']=='empath_supplied' and r['sample']=='common']
        assert len(empath_rows)==manifest['empath']['category_count']
        positive=[r for r in empath_rows if r['tier'] in ['V','S','U']]
        positive.sort(key=lambda r:float(r['perm_p']))
        new_section=['<h2>Empath: predefined lexical categories</h2>',
                     '<p>All '+str(len(empath_rows))+' supplied categories enter each correction family, including constant categories. Primary matching casefolds Unicode word tokens and retains internal apostrophes. Each score divides category matches by all tokens, and categories can overlap. The package-default sensitivity preserves original case and whitespace tokenization. Both variants and both sample sizes are reported.</p>',
                     htable([r for r in summaries if r['method']=='Empath'],[('model_id','Preprocessing'),('sample','Sample'),('n','N'),('dimensions','Categories'),('validated','V'),('suggestive_only','S'),('uncorrected_only','U'),('welch_q05','Conventional 5% BH')]),
                     '<h3>Dictionary coverage</h3>',htable(read(source/'empath_coverage_summary.csv'),[('model_id','Preprocessing'),('sample','Sample'),('pooled_token_coverage','Fraction of tokens matched'),('responses_without_matches','Responses without matches'),('constant_categories','Constant categories retained')]),
                     '<h3>Primary category results reaching a reported tier</h3><p>U is nominal and uncorrected; it is not validation. Every category, including the remaining nonsignificant categories, appears in the complete numerical output.</p>',
                     htable(positive,[('dimension','Category'),('focal_mean_native','Women'),('reference_mean_native','Men'),('mean_half_difference_native','Mean half-gap'),('perm_p','Same-sign p'),('tier','Tier')]),
                     '<details><summary>All supplied categories and their dictionary sizes</summary>'+htable(read(source/'empath_category_sizes.csv'),[('category','Category'),('terms','Terms')])+'</details>',
                     '<p>Source: <a href="https://github.com/Ejhfast/empath-client">Empath software</a>; <a href="https://arxiv.org/abs/1602.06979">Fast, Chen and Bernstein (2016)</a>.</p>']
        html.insert(next(i for i,item in enumerate(html) if item.startswith('<h2>All LDA specifications')),''.join(new_section))
    (out/'alternative_methods_review.html').write_text(''.join(html))
    data=out/'data';data.mkdir()
    # Aggregate outputs and provenance are portable; raw response text is excluded.
    for name in ['analysis_plan.json','manifest.json','method_summary.csv','all_dimension_results.csv',
                 'lda_topics.csv','lda_fit_log.csv','descriptive_overlap.csv','discern_feature_names.csv']:
        shutil.copy2(source/name,data/name)
    if has_empath:
        for name in ['empath_categories.tsv','empath_category_manifest.json','empath_category_sizes.csv',
                     'empath_coverage_summary.csv','parent_analysis_manifest.json','parent_analysis_plan.json']:
            shutil.copy2(source/name,data/name)
        shutil.copy2(Path(__file__).resolve().parents[1]/'docs/licenses/empath-LICENSE.txt',data/'Empath_LICENSE.txt')
    report={'source':str(source.resolve()),'analysis_manifest_sha256':sha256(source/'manifest.json'),
            'builder_sha256':sha256(__file__),'primary_dimensions':len(primary),'primary_dimensions_exported':len(primary_export),
            'all_dimension_rows':len(dimensions),'LDA_sensitivity_models':len(sensitivity),
            'native_units_preserved':True,'all_results_retained':True,
            'files_sha256':{str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()}}
    (out/'exhibit_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();build(a.source,a.out)
