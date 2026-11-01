"""Audit and extend the saved Hurst sentiment/LDA comparison, without API calls.

The primary specification is inherited from the saved engineering pilots. The
sensitivity grid is recorded before fitting and every fit is reported. Neither
topic selection nor the numerical topic descriptions use respondent gender.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import joblib
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from sklearn.decomposition import LatentDirichletAllocation
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from discern.baselines import test_scores
from discern.config import RunConfig
from discern.core import bh_pass
from discern.data import Dataset
from discern.validation import sha256


def exclusive_tier(row):
    if row['q05']:return 'V'
    if row['q10']:return 'S'
    if row['d1_native'] * row['d2_native'] > 0 and row['perm_p'] < .05:return 'U'
    return 'N'


def analyze(scores, groups, halves, permutations):
    """Production replication rule, plus a conventional Welch-test sensitivity."""
    rows, metadata = test_scores(scores, groups, halves, permutations)
    pvalues = {}
    for row in rows:
        column = row['dimension']
        p = float(ttest_ind(scores.loc[groups == 1, column],
                            scores.loc[groups == 0, column], equal_var=False).pvalue)
        # An exactly constant dimension supplies no group contrast evidence.
        if not np.isfinite(p):p = 1.0
        pvalues[column] = p
        row.update(tier=exclusive_tier(row), welch_p=p)
    accepted = bh_pass(pvalues, .05)
    for row in rows:row['welch_q05'] = row['dimension'] in accepted
    return rows, metadata


def summary(method, model_id, sample, rows, n, **extra):
    counts = Counter(r['tier'] for r in rows)
    return {'method': method, 'model_id': model_id, 'sample': sample,
            'n': n, 'dimensions': len(rows), 'validated': counts['V'],
            'suggestive_only': counts['S'], 'uncorrected_only': counts['U'],
            'none': counts['N'], 'welch_q05': sum(r['welch_q05'] for r in rows), **extra}


def align_scores(frame, uids):
    if frame.uid.duplicated().any() or set(frame.uid) != set(uids):
        raise ValueError('Saved scores must contain exactly the unique locked evaluation UIDs')
    return frame.set_index('uid').loc[uids].reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['config', 'reference-run', 'sentiment-pilot', 'lda-pilot', 'out']:
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve();out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    cfg, _ = RunConfig.from_file(args.config);data = Dataset(cfg)
    reference, sentiment_dir, lda_dir = map(Path, [args.reference_run, args.sentiment_pilot, args.lda_pilot])
    partition = json.loads((reference/'00_partition.json').read_text())
    assert cfg.condition == 'real'
    assert data.m_uid == partition['measurement_uids']
    assert data.m_split.tolist() == partition['measurement_split']
    assert not set(data.m_uid).intersection(data.pool.uid)
    assert len(data.m_uid) == 800 and len(data.pool) == 2032
    pilots = {'sentiment':sentiment_dir, 'lda':lda_dir}
    provenance = {}
    for name, path in pilots.items():
        manifest = json.loads((path/'manifest.json').read_text())
        assert manifest['dataset_sha256'] == sha256(cfg.dataset)
        assert manifest['reference_partition_sha256'] == sha256(reference/'00_partition.json')
        assert manifest['reference_measurement_sha256'] == sha256(reference/'03_measured.json')
        for filename, expected in manifest['output_sha256'].items():
            assert sha256(path/filename) == expected, filename
        provenance[name] = {'directory':str(path.resolve()), 'manifest_sha256':sha256(path/'manifest.json')}
    lda_manifest = json.loads((lda_dir/'manifest.json').read_text())
    primary_seed = lda_manifest['method']['seed']
    grid = lda_manifest['method']['topic_grid']
    primary_k = lda_manifest['method']['chosen_topics']
    assert primary_k == min(lda_manifest['method']['tuning'],
                            key=lambda r:(r['discovery_validation_perplexity'],r['topics']))['topics']
    plan = {'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'exploratory_extension_of_existing_pilots_not_preregistered',
            'primary_sentiment':'VADER compound; pos/neg/neu descriptive only',
            'primary_lda':{'seed':primary_seed,'K':primary_k,'selection':lda_manifest['method']['selection']},
            'lda_sensitivity':{'topic_counts':grid,'seeds':[primary_seed, primary_seed+1, primary_seed+2],
                               'max_iter':30,'learning_method':'batch','n_jobs':1,
                               'doc_topic_prior':'1/K','topic_word_prior':'1/K'},
            'topic_selection_uses_gender':False,'fit_uses_evaluation_texts':False,
            'primary_sample':'intersection of finite sentiment and primary LDA scores',
            'primary_test':'unchanged production same-sign permutation and BH; within method/model',
            'conventional_sensitivity':'two-sided unequal-variance Welch tests; BH within method/model',
            'permutations':cfg.permutations,'all_fits_reported':True,
            'no_selection_of_best_gender_contrast_model':True,'api_calls':0,
            'source_sha256':sha256(__file__),'pilot_provenance':provenance,
            'sources':{'VADER':'https://github.com/cjhutto/vaderSentiment',
                       'LDA':'https://www.jmlr.org/papers/v3/blei03a.html',
                       'implementation':'https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html'}}
    (out/'analysis_plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    print('Plan saved; verifying pilot measurements.', flush=True)
    # UID alignment is checked independently of file ordering.
    saved_sentiment = align_scores(pd.read_csv(sentiment_dir/'scores.csv', dtype={'uid':str}), data.m_uid)
    analyzer = SentimentIntensityAnalyzer()
    sentiment = pd.DataFrame([analyzer.polarity_scores(t) for t in data.m_text])
    np.testing.assert_allclose(sentiment.compound, saved_sentiment.compound, rtol=0, atol=1e-14)
    vocab, primary_model = joblib.load(lda_dir/'fitted_lda.joblib')
    evaluation = vocab.transform(data.m_text)
    retained = np.asarray(evaluation.sum(axis=1)).ravel()>0
    primary_values = primary_model.transform(evaluation);primary_values[~retained] = np.nan
    saved_lda = align_scores(pd.read_csv(lda_dir/'scores.csv', dtype={'uid':str}), data.m_uid)
    topic_names = [f'topic_{i+1:02}' for i in range(primary_k)]
    np.testing.assert_allclose(primary_values, saved_lda[topic_names], equal_nan=True, rtol=0, atol=1e-12)
    common = retained & np.isfinite(sentiment.compound)
    groups, halves = data.measurement_labels(), data.m_split
    partition_rows = pd.DataFrame({'uid':data.m_uid,'group':groups,'half':halves,'common_sample':common,
                                  'retained_LDA_token_count':np.asarray(evaluation.sum(axis=1)).ravel()})
    partition_rows.to_csv(out/'evaluation_partition.csv', index=False)
    summaries, detailed = [], []
    primary_outputs = {}
    def record(method, model_id, sample, scores, mask, **extra):
        rows, meta = analyze(scores.loc[mask].reset_index(drop=True), groups[mask], halves[mask], cfg.permutations)
        summaries.append(summary(method,model_id,sample,rows,int(mask.sum()),**extra))
        detailed.extend({'method':method,'model_id':model_id,'sample':sample,**r} for r in rows)
        return rows, meta
    all_rows = np.ones(len(common),dtype=bool)
    for sample,mask in [('common',common),('full',all_rows)]:
        record('Sentiment','vader_compound',sample,sentiment[['compound']],mask)
    # Read every measured Discern feature; keep the full 35-candidate family.
    measured = json.loads((reference/'03_measured.json').read_text())
    candidates = json.loads((reference/'02_consolidated.json').read_text())['candidates']
    by_id = {c['candidate_id']:c for c in candidates}
    assert set(by_id) == set(measured)
    discern = pd.DataFrame({cid:np.asarray(measured[cid]['y'],dtype=float) for cid in measured})
    for sample,mask in [('common',common),('full',all_rows)]:
        rows,_ = record('Discern','archived_main',sample,discern,mask)
        if sample == 'common':primary_outputs['discern'] = rows
    archived = json.loads((reference/'04_selected.json').read_text())
    full_discern = {r['dimension']:r for r in detailed if r['method']=='Discern' and r['sample']=='full'}
    for r in archived['results']:
        fresh = full_discern[r['candidate_id']]
        assert abs(fresh['d1_native']-r['d1'])<1e-12 and abs(fresh['d2_native']-r['d2'])<1e-12
        assert abs(fresh['perm_p']-r['perm_p'])<1e-12
        assert (fresh['tier']=='V') == r['validated']
    discovery = vocab.transform(data.pool.text.tolist())
    words = vocab.get_feature_names_out()
    fit_reports=[];topic_reports=[]
    for seed in plan['lda_sensitivity']['seeds']:
        for k in grid:
            model_id=f'lda_k{k:02}_seed{seed}'
            fit_started=time.monotonic()
            primary = seed==primary_seed and k==primary_k
            if primary:model,values = primary_model,primary_values
            else:
                model=LatentDirichletAllocation(n_components=k,learning_method='batch',max_iter=30,
                                                random_state=seed,n_jobs=1)
                model.fit(discovery)
                values=model.transform(evaluation);values[~retained]=np.nan
            names=[f'topic_{i+1:02}' for i in range(k)]
            scores=pd.DataFrame(values,columns=names)
            rows,_=record('LDA',model_id,'common',scores,common,K=k,seed=seed,primary=primary)
            fit_dir=out/'lda_models'/model_id;fit_dir.mkdir(parents=True)
            pd.concat([partition_rows[['uid']],scores],axis=1).to_csv(fit_dir/'scores.csv',index=False)
            joblib.dump((vocab,model),fit_dir/'fitted_lda.joblib')
            for i,weights in enumerate(model.components_):
                topic_reports.append({'model_id':model_id,'dimension':names[i],'primary':primary,
                                      'top_words':', '.join(words[weights.argsort()[-12:][::-1]])})
            fit_reports.append({'model_id':model_id,'K':k,'seed':seed,'primary':primary,
                                'iterations':int(model.n_iter_),'doc_topic_prior':float(model.doc_topic_prior_),
                                'topic_word_prior':float(model.topic_word_prior_),
                                'wall_seconds':round(time.monotonic()-fit_started,3)})
            if primary:primary_outputs['lda']=scores
            print(json.dumps(summaries[-1]),flush=True)
    # Descriptive associations make overlap inspectable without forcing semantic matches.
    baseline_scores=pd.concat([sentiment[['compound']],primary_outputs['lda']],axis=1)
    overlap=[]
    validated={r['dimension'] for r in primary_outputs['discern'] if r['tier']=='V'}
    for cid in discern:
        for dimension in baseline_scores:
            x=discern.loc[common,cid].to_numpy();y=baseline_scores.loc[common,dimension].to_numpy()
            corr=float(np.corrcoef(x,y)[0,1]) if x.std() and y.std() else None
            overlap.append({'candidate_id':cid,'feature_name':by_id[cid]['feature_name'],
                            'validated_common_sample':cid in validated,'baseline_dimension':dimension,
                            'pearson_r':corr,'n':int(common.sum()),'interpretation':'descriptive association; no fidelity or equivalence claim'})
    # No raw response text is copied into the review package.
    for filename,rows in [('method_summary.csv',summaries),('all_dimension_results.csv',detailed),
                          ('lda_topics.csv',topic_reports),('lda_fit_log.csv',fit_reports),
                          ('descriptive_overlap.csv',overlap)]:
        pd.DataFrame(rows).to_csv(out/filename,index=False)
    sentiment.insert(0,'uid',data.m_uid);sentiment.to_csv(out/'sentiment_components.csv',index=False)
    pd.DataFrame([{'candidate_id':cid,'feature_name':by_id[cid]['feature_name']} for cid in discern]).to_csv(out/'discern_feature_names.csv',index=False)
    cell_counts=partition_rows.loc[common].groupby(['group','half']).size()
    manifest={'status':'completed_exploratory_comparison','api_calls':0,'primary_sample_n':int(common.sum()),
              'full_sample_n':len(common),'discovery_n':len(data.pool),'primary_lda_K':primary_k,
              'common_sample_group_half_counts':{f'group{g}_half{h}':int(n) for (g,h),n in cell_counts.items()},
              'all_pilot_scores_reproduced':True,'archived_discern_full_selection_reproduced':True,
              'excluded_uids':[u for u,keep in zip(data.m_uid,common) if not keep],
              'dataset_sha256':sha256(cfg.dataset),'config_sha256':sha256(args.config),
              'reference_partition_sha256':sha256(reference/'00_partition.json'),
              'reference_measurements_sha256':sha256(reference/'03_measured.json'),
              'source_sha256':{str(p.relative_to(Path(__file__).resolve().parents[1])):sha256(p) for p in
                               [Path(__file__),Path(__file__).resolve().parents[1]/'src/discern/baselines.py',
                                Path(__file__).resolve().parents[1]/'src/discern/core.py']},
              'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','scipy','vaderSentiment','joblib']},
              'wall_seconds':round(time.monotonic()-started,3),
              'limitations':['Exploratory extension; original pilot results already observed.',
                             'Different feature types and dimensions; rejection counts do not rank substantive validity.',
                             'Within-method/model multiplicity, not pooled across LDA sensitivities.',
                             'No independent human fidelity or semantic-coverage assessment yet.',
                             'Sentiment and topic scores do not measure binary feature prevalence.',
                             'Replicates archived sample; original study exclusions unavailable.'],
              'output_sha256':{str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'out':str(out),'common_n':int(common.sum()),'models':len(fit_reports)},indent=2))


if __name__=='__main__':main()
