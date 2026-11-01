"""Fit BERTopic on discovery responses and compare native held-out assignments.

Local MiniLM embeddings; no response text is transmitted. Settings are recorded
before fitting. No tuning, topic merging, generated labels, or representative
response interpretation is used in the exhibit.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from discern.config import RunConfig
from discern.core import bh_pass
from discern.data import Dataset
from discern.validation import sha256


def assignment_results(assignments,groups,topic_ids):
    """Compare native hard-assignment fractions; retain outliers in every denominator."""
    assignments,groups=np.asarray(assignments),np.asarray(groups)
    if len(assignments)!=len(groups) or set(np.unique(groups))!={0,1}:
        raise ValueError('Complete aligned binary groups are required')
    if not set(assignments).issubset(set(topic_ids)):
        raise ValueError('Every assignment, including outliers, must be represented')
    rows=[]
    for topic in topic_ids:
        values=(assignments==topic).astype(float)
        women,men=values[groups==1],values[groups==0]
        p=1. if np.ptp(values)==0 else float(ttest_ind(women,men,equal_var=False).pvalue)
        if not np.isfinite(p):p=1.
        rows.append({'topic_id':int(topic),'is_outlier':topic==-1,'n_women':len(women),'n_men':len(men),
                     'women_assigned':int(women.sum()),'men_assigned':int(men.sum()),
                     'women':float(women.mean()),'men':float(men.mean()),
                     'difference':float(women.mean()-men.mean()),'welch_p':p})
    passed=bh_pass({r['topic_id']:r['welch_p'] for r in rows},.05)
    for r in rows:r['welch_q05']=r['topic_id'] in passed
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['config','base','embedding-dir','out']:p.add_argument('--'+name,required=True)
    p.add_argument('--embedding-revision',required=True)
    args=p.parse_args();base,out=Path(args.base).resolve(),Path(args.out).resolve()
    manifest=json.loads((base/'manifest.json').read_text())
    for name,h in manifest['output_sha256'].items():assert sha256(base/name)==h,name
    cfg,_=RunConfig.from_file(args.config);data=Dataset(cfg)
    assert cfg.condition=='real' and sha256(cfg.dataset)==manifest['dataset_sha256']
    part=pd.read_csv(base/'evaluation_partition.csv',dtype={'uid':str})
    assert part.uid.tolist()==data.m_uid and part.group.tolist()==data.m_group.tolist()
    assert part.half.tolist()==data.m_split.tolist()
    mask=part.common_sample.to_numpy();assert int(mask.sum())==794 and len(data.pool)==2032
    assert not set(data.m_uid).intersection(data.pool.uid)
    out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    embedding_dir=Path(args.embedding_dir).resolve()
    model_files={str(f.relative_to(embedding_dir)):sha256(f) for f in embedding_dir.rglob('*') if f.is_file() and '.cache' not in f.parts}
    plan={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'method':'BERTopic',
          'embedding_model':'sentence-transformers/all-MiniLM-L6-v2','embedding_revision':args.embedding_revision,
          'embedding_files_sha256':model_files,'device':'cpu','normalize_embeddings':True,
          'discovery_n':2032,'evaluation_n':800,'common_sample_n':794,
          'fit_uses_gender':False,'fit_uses_evaluation_responses':False,
          'umap':{'n_neighbors':15,'n_components':5,'min_dist':0.,'metric':'cosine',
                  'random_state':260026,'transform_seed':42,'n_jobs':1},
          'hdbscan':{'min_cluster_size':10,'min_samples':None,'metric':'euclidean',
                     'cluster_selection_method':'eom','prediction_data':True},
          'vectorizer':{'stop_words':'english','ngram_range':[1,2],'min_df':1},
          'representation':'native c-TF-IDF; 12 terms saved; 8 shown; no LLM labels',
          'calculate_probabilities':True,'topic_reduction':None,'outlier_reassignment':False,
          'primary_score':'fraction assigned to each frozen topic; includes unassigned/outliers in denominator',
          'test':'two-sided unequal-variance Welch tests; p < .05 unadjusted for display; BH also saved',
          'outlier_handling':'-1 is retained as an explicit outcome and reported separately from substantive topics',
          'settings_selected_before_group_tests':True,'api_calls':0,'source_sha256':sha256(__file__),
          'source_analysis_manifest_sha256':sha256(base/'manifest.json'),
          'versions':{name:importlib.metadata.version(name) for name in
                      ['bertopic','sentence-transformers','transformers','torch','umap-learn','hdbscan','numpy','pandas','scipy','scikit-learn']}}
    (out/'analysis_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Specification frozen; encoding responses locally.',flush=True)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP
    import torch
    torch.set_num_threads(4)
    encoder=SentenceTransformer(str(embedding_dir),device='cpu',local_files_only=True,trust_remote_code=False)
    train_texts=data.pool.text.tolist()
    train_embeddings=encoder.encode(train_texts,batch_size=64,normalize_embeddings=True,show_progress_bar=False)
    eval_embeddings=encoder.encode(data.m_text,batch_size=64,normalize_embeddings=True,show_progress_bar=False)
    np.save(out/'discovery_embeddings.npy',train_embeddings);np.save(out/'evaluation_embeddings.npy',eval_embeddings)
    pd.DataFrame({'uid':data.pool.uid}).to_csv(out/'discovery_embedding_uids.csv',index=False)
    print('Embeddings complete; fitting topics on discovery responses only.',flush=True)
    model=BERTopic(embedding_model=encoder,umap_model=UMAP(**plan['umap']),
                   hdbscan_model=HDBSCAN(**plan['hdbscan']),
                   vectorizer_model=CountVectorizer(stop_words='english',ngram_range=(1,2)),
                   top_n_words=12,calculate_probabilities=True,nr_topics=None,verbose=True)
    training_topics,training_probabilities=model.fit_transform(train_texts,train_embeddings)
    predicted,probabilities=model.transform(data.m_text,eval_embeddings)
    predicted=np.asarray(predicted,dtype=int)
    ids=sorted(set(model.topics_));assert any(t>=0 for t in ids)
    if -1 not in ids:ids=[-1]+ids
    pd.DataFrame({'uid':data.pool.uid,'topic_id':training_topics}).to_csv(out/'discovery_assignments.csv',index=False)
    pd.DataFrame({'uid':data.m_uid,'group':data.m_group,'half':data.m_split,'common_sample':mask,
                  'topic_id':predicted}).to_csv(out/'evaluation_assignments.csv',index=False)
    if probabilities is not None:np.save(out/'evaluation_membership_probabilities.npy',probabilities)
    all_rows=[]
    for sample,keep in [('common',mask),('full',np.ones(len(mask),dtype=bool))]:
        rows=assignment_results(predicted[keep],data.m_group[keep],ids)
        all_rows.extend({'sample':sample,**r} for r in rows)
    topics=[]
    for topic in ids:
        terms=model.get_topic(topic) or []
        words=[str(w) for w,weight in terms if w]
        topics.append({'topic_id':int(topic),'is_outlier':topic==-1,'training_count':int(np.sum(np.asarray(training_topics)==topic)),
                       'words':', '.join(words),'word_weights':[[str(w),float(weight)] for w,weight in terms if w]})
    word_map={r['topic_id']:r['words'] for r in topics}
    for row in all_rows:row['words']=word_map[row['topic_id']]
    pd.DataFrame(all_rows).to_csv(out/'group_differences.csv',index=False)
    (out/'topics.json').write_text(json.dumps(topics,indent=2)+'\n')
    # Pickle remains in the private evidence folder because the fitted object contains representative texts.
    model.save(str(out/'fitted_bertopic'),serialization='pickle',save_embedding_model=False)
    common=[r for r in all_rows if r['sample']=='common']
    significant=[r for r in common if not r['is_outlier'] and r['welch_p']<.05]
    report={'status':'completed','plan_sha256':sha256(out/'analysis_plan.json'),'api_calls':0,
            'source_dataset_sha256':sha256(cfg.dataset),'source_config_sha256':sha256(args.config),
            'source_base_manifest_sha256':sha256(base/'manifest.json'),
            'source_sha256':sha256(__file__),'settings_frozen_before_fit':True,
            'topics':len([t for t in ids if t>=0]),'common_n':int(mask.sum()),
            'nominally_differential_topics':len(significant),
            'BH_differential_topics':sum(r['welch_q05'] for r in common if not r['is_outlier']),
            'common_outlier_count':int((predicted[mask]==-1).sum()),
            'fit_and_score_wall_seconds':round(time.monotonic()-started,3),
            'output_sha256':{f.name:sha256(f) for f in out.iterdir() if f.is_file()}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'},indent=2))


if __name__=='__main__':main()
