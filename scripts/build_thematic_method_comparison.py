"""Interpret saved method outputs without imposing Discern selection tiers.

This is an editorial comparison with traceable source material, not a blinded
coverage assessment. All saved topics, categories, and Discern questions remain
available. Representative LDA passages are chosen without gender labels.
"""
import argparse
from collections import Counter
import csv
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import joblib
import numpy as np
import pandas as pd
from discern.baselines import empath_lexicon, empath_tokens
from discern.config import RunConfig
from discern.data import Dataset
from discern.validation import sha256
from build_validation_latex import tex
from build_baseline_exhibits import htable, standalone, TOPIC_LABELS


BRIDGES=[
    {'theme':'Management layers',
     'conventional':'LDA groups management, layers, and red tape. Its representative responses already describe both growth opportunities and managerial bloat.',
     'discern':'Layers as sources of support, oversight, or fairness; unnecessary or redundant management positions.',
     'ids':['A05','A06'],'topic':'topic_05'},
    {'theme':'Communication and voice',
     'conventional':'Empath counts communication-related words such as report, communication, and idea. An LDA representative response explicitly describes loss of voice; finer fits include communication and micromanagement.',
     'discern':'Barriers to reaching upper management or ideas being lost; employee voice, autonomy, and influence.',
     'ids':['A07','A16'],'topic':'topic_01'},
    {'theme':'Career advancement',
     'conventional':'LDA identifies advancement and growth; representative responses also discuss promotion politics. Empath achievement includes opportunity, promotion, and approval.',
     'discern':'Opportunities for promotion and growth; promotion barriers and gatekeeping; office politics and distrust.',
     'ids':['A29','A24','A11'],'topic':'topic_03'},
]


def representative_indices(weights, counts, texts, limit=3):
    """Top posterior among substantive-length discovery passages; ties by row order."""
    eligible=(counts>=5)&np.array([8<=len(t.split())<=100 for t in texts])
    return [int(i) for i in np.argsort(-weights,kind='stable') if eligible[i]][:limit]


def main_table(readings,bridges):
    lines=[r'% Descriptive thematic comparison; no common selection tiers are imposed on the alternatives.',
           r'\begin{table}[!htbp]\centering',r'\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
           r'\caption{Substantive insights from alternative text methods}\label{tab:alternative-methods}',
           r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.18}',
           r'\edef\MethodWidth{\the\dimexpr.16\linewidth-2\tabcolsep\relax}',
           r'\edef\ReadingWidth{\the\dimexpr.84\linewidth-2\tabcolsep\relax}',
           r'\begin{tabular}{@{}p{\MethodWidth}p{\ReadingWidth}@{}}\hline',
           r'\multicolumn{2}{@{}l}{\textit{A. What a researcher could glean from the conventional outputs}}\\[3pt]']
    for r in readings:lines.append(r'\textbf{'+tex(r['method'])+'} & '+tex(r['reading'])+r' \\[5pt]')
    lines += [r'\hline\end{tabular}\par\vspace{10pt}',
              r'\edef\ThemeWidth{\the\dimexpr.23\linewidth-2\tabcolsep\relax}',
              r'\edef\DetailWidth{\the\dimexpr.77\linewidth-2\tabcolsep\relax}',
              r'\begin{tabular}{@{}p{\ThemeWidth}p{\DetailWidth}@{}}\hline',
              r'\multicolumn{2}{@{}l}{\textit{B. Crosscutting distinctions made explicit by Discern}}\\[3pt]']
    for r in bridges:lines.append(r'\textbf{'+tex(r['theme'])+'} & '+tex(r['discern'])+r' \\[5pt]')
    lines += [r'\hline\end{tabular}\par\vspace{4pt}',
              r'\noindent\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{8}{9.6}\selectfont',
              r'\textit{Notes.} '+tex('Descriptive readings of saved outputs. Discern examples are discovered questions; Appendix D reports their statistical results. Representative LDA responses also contain several of these distinctions.'),
              r'\end{minipage}\end{table}']
    return '\n'.join(lines)+'\n'


def build(source,config,discern_csv,out):
    source,out=Path(source).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['output_sha256'].items():assert sha256(source/name)==h,name
    cfg,_=RunConfig.from_file(config);data=Dataset(cfg)
    assert sha256(cfg.dataset)==manifest['dataset_sha256']
    part=pd.read_csv(source/'evaluation_partition.csv',dtype={'uid':str})
    assert part.uid.tolist()==data.m_uid and part.group.tolist()==data.m_group.tolist()
    mask=part.common_sample.to_numpy();assert int(mask.sum())==794
    sentiment=pd.read_csv(source/'sentiment_components.csv',dtype={'uid':str})
    assert sentiment.uid.tolist()==data.m_uid
    sm=[{'group':'Women' if g else 'Men','n':int((mask&(data.m_group==g)).sum()),
         'compound_mean':float(sentiment.loc[mask&(data.m_group==g),'compound'].mean())} for g in [1,0]]
    topic_rows=list(csv.DictReader((source/'lda_topics.csv').open()))
    primary_model='lda_k05_seed260026'
    topics=[r for r in topic_rows if r['model_id']==primary_model];assert len(topics)==5
    model_path=source/'lda_models'/primary_model/'fitted_lda.joblib'
    vectorizer,model=joblib.load(model_path)
    discovery=vectorizer.transform(data.pool.text.tolist());weights=model.transform(discovery)
    counts=np.asarray(discovery.sum(axis=1)).ravel()
    stored=pd.read_csv(source/'lda_models'/primary_model/'scores.csv',dtype={'uid':str})
    assert stored.uid.tolist()==data.m_uid
    for i,r in enumerate(topics):
        r['description']=TOPIC_LABELS[r['dimension']]
        r['women_mean_pct']=100*float(stored.loc[mask&(data.m_group==1),r['dimension']].mean())
        r['men_mean_pct']=100*float(stored.loc[mask&(data.m_group==0),r['dimension']].mean())
        chosen=representative_indices(weights[:,i],counts,data.pool.text.tolist())
        r['representatives']=[{'uid':str(data.pool.iloc[j].uid),'topic_weight':float(weights[j,i]),
                               'text':data.pool.iloc[j].text} for j in chosen]
    lexicon,lexmeta=empath_lexicon()
    assert lexmeta['dictionary_sha256']==manifest['empath']['dictionary_sha256']
    es=pd.read_csv(source/'empath_word_tokens_scores.csv',dtype={'uid':str})
    assert es.uid.tolist()==data.m_uid
    frequency=Counter(t for text,keep in zip(data.m_text,mask) if keep for t in empath_tokens(text))
    categories=[]
    for cat in lexmeta['categories']:
        terms=set(lexicon.cats[cat])
        matches=[{'word':t,'tokens':n} for t,n in sorted(frequency.items(),key=lambda item:(-item[1],item[0])) if t in terms]
        categories.append({'category':cat,'overall_mean_pct':100*float(es.loc[mask,cat].mean()),
                           'women_mean_pct':100*float(es.loc[mask&(data.m_group==1),cat].mean()),
                           'men_mean_pct':100*float(es.loc[mask&(data.m_group==0),cat].mean()),
                           'matching_words':', '.join(f"{r['word']} ({r['tokens']})" for r in matches[:8]),
                           'all_matching_words':matches})
    categories.sort(key=lambda r:(-r['overall_mean_pct'],r['category']))
    proposals=[r for r in csv.DictReader(Path(discern_csv).open()) if r['run_id']=='ARCHIVE']
    assert len(proposals)==35
    by_id={r['exhibit_id']:r for r in proposals}
    for b in BRIDGES:
        assert all(i in by_id for i in b['ids'])
    readings=[
        {'method':'Sentiment','reading':f"VADER gives similar overall valence for women and men (mean compound scores {sm[0]['compound_mean']:.3f} and {sm[1]['compound_mean']:.3f}). This summarizes tone across responses, without separate measures of the organizational concerns being expressed."},
        {'method':'LDA','reading':'The five-topic fit identifies management and red tape, pyramid/scheme imagery, advancement and growth, chain of command, and management layers. Representative responses already discuss managerial bloat, support, and loss of voice; finer fits also feature communication and micromanagement.'},
        {'method':'Empath','reading':'Prominent categories include business, work, achievement, and leader. Achievement is activated by opportunity, promotion, and approval; communication by report, communication, and idea. These outputs describe lexical fields, while the interpretation of opportunities, obstacles, or consequences requires reading the surrounding text.'},
    ]
    fragment=main_table(readings,BRIDGES)
    (out/'table_3_alternative_methods.tex').write_text(fragment)
    (out/'table_3_alternative_methods_preview.tex').write_text(standalone(fragment))
    export=[{'panel':'A','method_or_theme':r['method'],'interpretation':r['reading'],'source_ids':''} for r in readings]+[
        {'panel':'B','method_or_theme':r['theme'],'interpretation':r['discern'],'source_ids':';'.join(r['ids'])} for r in BRIDGES]
    with (out/'table_3_alternative_methods.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(export[0]));w.writeheader();w.writerows(export)
    css='body{font:17px Georgia;line-height:1.55;max-width:1120px;margin:35px auto;padding:0 24px;color:#25352c}h1,h2{line-height:1.2}table{border-collapse:collapse;width:100%;font:14px Arial;margin:20px 0}td,th{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid #cbd3cd}th{background:#edf2ed}blockquote{border-left:3px solid #a4bda9;margin:14px 0;padding:0 18px}small{font:12px Arial;color:#53625a}details{margin:16px 0}summary{cursor:pointer;font-weight:bold}a{color:#28634c}article{border-top:1px solid #cbd3cd;padding:16px 0}'
    start='<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style><title>What the text methods reveal</title></head><body>'
    end='</body></html>'
    thesis=('The substantive comparison is about how methods represent the material: overall tone, topical organization, predefined lexical categories, and explicit context-specific propositions. The LDA examples already contain many of the same ideas. Discern makes distinctions spanning those topics explicit and separately addressable; this descriptive comparison does not establish that an analyst using the other methods could not recover them.')
    compact=start+'<h1>Table 3. Substantive insights from alternative text methods</h1>'+htable(readings,[('method','Method'),('reading','What a researcher could glean')])+htable(BRIDGES,[('theme','Shared subject'),('discern','Distinctions made explicit by Discern')])+'<p>'+escape(thesis)+'</p>'+end
    (out/'table_3_alternative_methods.html').write_text(compact)
    html=[start,'<h1>What a researcher would learn from each method</h1><p>'+escape(thesis)+'</p>',
          '<p>Women versus men within tall hierarchies. Descriptive score summaries use the same 794 evaluation responses. The five-topic model was fitted on 2,032 disjoint discovery responses. Examples below are editorial readings of these saved outputs, with source questions and passages available for inspection.</p>',
          '<h2>Conventional-method takeaways</h2>',htable(readings,[('method','Method'),('reading','Substantive reading')]),
          '<h2>From shared subjects to explicit propositions</h2>']
    for b in BRIDGES:
        html+=['<article><h3>'+escape(b['theme'])+'</h3><p><b>Already visible in the conventional analysis.</b> '+escape(b['conventional'])+'</p><p><b>Discern makes explicit.</b> '+escape(b['discern'])+'</p><p>Source questions: '+', '.join('<a href="#'+i+'">'+i+'</a>' for i in b['ids'])+'</p></article>']
    html+=['<h2>Sentiment: the aggregate valence summary</h2>',htable([{'group':r['group'],'n':r['n'],'mean':f"{r['compound_mean']:.4f}"} for r in sm],[('group','Group'),('n','Responses'),('mean','Mean VADER compound')]),
           '<p>A similar average score is compatible with different reasons for favorable or unfavorable views. It does not imply equivalent opinions or an absence of substantive differences.</p>',
           '<h2>LDA: topics and what their representative responses actually say</h2>',
           '<p>Labels summarize top words. The three examples per topic are the highest-posterior discovery responses with at least five retained tokens and 8–100 whitespace words; ties use source row order. This selection does not use respondent gender, Discern scores, or statistical results. Passages are reproduced verbatim. They show why a researcher reading the topics can already recover fairly nuanced concerns.</p>']
    for r in topics:
        html+=['<article><h3>'+escape(r['dimension']+': '+r['description'])+'</h3><p><b>Highest-weight words:</b> '+escape(r['top_words'])+'</p><p>Mean topic share: women '+f"{r['women_mean_pct']:.2f}%"+'; men '+f"{r['men_mean_pct']:.2f}%"+'.</p>']
        for e in r['representatives']:html+=['<blockquote>'+escape(e['text'])+'</blockquote><small>Discovery row '+escape(e['uid'])+'; topic weight '+f"{e['topic_weight']:.3f}"+'</small>']
        html+=['</article>']
    html+=['<details><summary>All 150 topic-word lists across the twelve LDA fits</summary>'+htable(topic_rows,[('model_id','Fit'),('dimension','Topic'),('top_words','Highest-weight words')])+'</details>',
           '<h2>Empath: lexical fields and the words driving them</h2><p>Categories are ranked by mean category-match proportion across the common sample, irrespective of group differences. Scores are percentages of tokens averaged over responses; categories overlap. Parentheses after words give pooled token counts. The category name is a lexicon label, and its meaning in these responses should be checked against the words that activated it.</p>']
    formatted=[{**r,**{key:f'{r[key]:.3f}' for key in ['overall_mean_pct','women_mean_pct','men_mean_pct']}} for r in categories]
    cols=[('category','Category'),('overall_mean_pct','Overall mean %'),('women_mean_pct','Women %'),('men_mean_pct','Men %'),('matching_words','Most frequent matching words (tokens)')]
    html+=[htable(formatted[:15],cols),'<details><summary>All 194 categories and their matching words</summary>'+htable(formatted,cols)+'</details>',
           '<h2>Discern: the complete set of explicit candidate questions</h2><p>All 35 discovered questions are included, irrespective of their statistical results. The comparison here concerns what ideas the method formulates. Appendix D separately reports the numerical results.</p>']
    for r in proposals:
        html+=['<article id="'+escape(r['exhibit_id'])+'"><h3>'+escape(r['exhibit_id']+'. '+r['feature_name'])+'</h3><p>'+escape(r['classification_question'])+'</p></article>']
    html+=['<h2>Scope of the claim</h2><p>This is a descriptive, source-linked illustration of interpretive specificity. It is not an independent rating of novelty, completeness, or accuracy. LDA passage inspection already reveals several of the same ideas, and category dictionaries can be expanded by researchers. The useful distinction illustrated here is that Discern directly formulates crosscutting claims as separate questions.</p>',
           '<p>Method sources: <a href="https://github.com/cjhutto/vaderSentiment">VADER</a>; <a href="https://www.jmlr.org/papers/v3/blei03a.html">LDA</a>; <a href="https://arxiv.org/abs/1602.06979">Empath</a>.</p>',end]
    (out/'alternative_methods_review.html').write_text(''.join(html))
    # Compact optional Appendix E contains descriptive outputs, with no shared tiers.
    appendix=[r'\section{Descriptive outputs of alternative text methods}\label{app:alternative-methods}',
              tex('These outputs support the thematic comparison in Table 3. LDA topics summarize word co-occurrence; Empath categories summarize lexical matches. Descriptive percentages use the common 794-response sample. Full topic-word lists, representative discovery passages, all 194 lexical categories, and all 35 Discern questions are in the companion catalogue.'),
              r'\begin{table}[!htbp]\centering\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
              r'\caption{LDA topics and descriptive group means}',
              r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}',
              r'\edef\TopicTextWidth{\the\dimexpr\linewidth-83pt-6\tabcolsep\relax}',
              r'\begin{tabular}{@{}p{\TopicTextWidth}rr@{}}\hline',r'Topic and highest-weight words & Women (\%) & Men (\%)\\\hline']
    for r in topics:appendix.append(tex(r['description']+': '+r['top_words'])+' & '+f"{r['women_mean_pct']:.2f} & {r['men_mean_pct']:.2f}"+r' \\[3pt]')
    appendix+=[r'\hline\end{tabular}\end{table}',r'\begin{table}[!htbp]\centering\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont',
               r'\caption{Most prominent Empath categories and words}',
               r'\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.08}',
               r'\edef\CatWidth{\the\dimexpr.32\linewidth-2\tabcolsep\relax}',
               r'\edef\WordsWidth{\the\dimexpr.68\linewidth-2\tabcolsep\relax}',
               r'\begin{tabular}{@{}p{\CatWidth}p{\WordsWidth}@{}}\hline',r'Category & Most frequent matching words\\\hline']
    for r in categories[:10]:appendix.append(tex(r['category'])+' & '+tex(', '.join(x['word'] for x in r['all_matching_words'][:5]))+r' \\')
    appendix+=[r'\hline\end{tabular}\end{table}']
    appendix='\n'.join(appendix)+'\n'
    (out/'appendix_E_alternative_methods.tex').write_text(appendix)
    (out/'appendix_E_alternative_methods_preview.tex').write_text(standalone(appendix,True))
    evidence={'purpose':'descriptive thematic comparison; editorial interpretation, not independent semantic validation',
              'n':794,'readings':readings,'bridges':BRIDGES,'sentiment':sm,'primary_lda':topics,
              'all_lda_topic_words':topic_rows,'empath_categories':categories,
              'discern_questions':[{k:r[k] for k in ['exhibit_id','feature_name','definition','classification_question']} for r in proposals],
              'representative_selection':'highest posterior; >=5 retained tokens; 8--100 whitespace words; no group or statistical labels',
              'source_analysis_manifest_sha256':sha256(source/'manifest.json'),
              'source_discern_csv_sha256':sha256(discern_csv),'source_model_sha256':sha256(model_path),
              'builder_sha256':sha256(__file__),'api_calls':0}
    (out/'thematic_method_evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    report={'comparison':'descriptive_thematic','all_lda_topics':len(topic_rows),'all_empath_categories':len(categories),
            'all_discern_questions':len(proposals),'representative_discovery_passages':sum(len(r['representatives']) for r in topics),
            'reuses_saved_scores_and_models':True,'new_inference':False,'source':str(source),
            'files_sha256':{p.name:sha256(p) for p in out.iterdir() if p.is_file()}}
    (out/'exhibit_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','config','discern-csv','out']:p.add_argument('--'+name,required=True)
    a=p.parse_args();build(a.source,a.config,a.discern_csv,a.out)
