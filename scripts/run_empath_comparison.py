"""Extend the locked Hurst baseline comparison with every supplied Empath category."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from discern.baselines import empath_lexicon, empath_scores
from discern.config import RunConfig
from discern.data import Dataset
from discern.validation import sha256
from run_baseline_comparison import align_scores, analyze, summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['config','base','out']:p.add_argument('--'+name,required=True)
    args=p.parse_args()
    base,out=Path(args.base).resolve(),Path(args.out).resolve()
    parent=json.loads((base/'manifest.json').read_text())
    for name,h in parent['output_sha256'].items():assert sha256(base/name)==h,name
    cfg,_=RunConfig.from_file(args.config);data=Dataset(cfg)
    assert cfg.condition=='real' and sha256(cfg.dataset)==parent['dataset_sha256']
    assert sha256(args.config)==parent['config_sha256']
    part=align_scores(pd.read_csv(base/'evaluation_partition.csv',dtype={'uid':str}),data.m_uid)
    assert part.group.tolist()==data.m_group.tolist() and part.half.tolist()==data.m_split.tolist()
    assert part.common_sample.dtype==bool
    common=part.common_sample.to_numpy();assert int(common.sum())==parent['primary_sample_n']==794
    lexicon,method=empath_lexicon()
    assert method['version']=='0.89' and method['category_count']==194
    # Preserve previous results exactly; no LDA fitting or other analysis is repeated.
    out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    for entry in base.iterdir():
        if entry.name=='manifest.json':continue
        if entry.is_dir():shutil.copytree(entry,out/entry.name)
        else:shutil.copy2(entry,out/entry.name)
    shutil.copy2(base/'manifest.json',out/'parent_analysis_manifest.json')
    shutil.copy2(base/'analysis_plan.json',out/'parent_analysis_plan.json')
    plan=json.loads((base/'analysis_plan.json').read_text())
    plan['empath_extension']={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
                             'method':method,'primary_preprocessing':'Unicode casefolded word tokens; internal apostrophes retained; no stemming',
                             'primary_token_pattern':r"[^\W_]+(?:['’][^\W_]+)*",
                             'sensitivity_preprocessing':'package default: original case and whitespace tokenization',
                             'samples':['same 794-response common sample','all 800 reserved responses'],
                             'family':'all 194 supplied categories for each sample/preprocessing',
                             'testing':'production same-sign permutation/BH; 5000 permutations; separate conventional Welch/BH sensitivity',
                             'no_filtering_on_frequency_or_group_differences':True,
                             'category_order':'lexicographically sorted before testing','api_calls':0,
                             'parent_manifest_sha256':sha256(base/'manifest.json')}
    (out/'analysis_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    shutil.copy2(method['dictionary_path'],out/'empath_categories.tsv')
    (out/'empath_category_manifest.json').write_text(json.dumps(method,indent=2)+'\n')
    counts=pd.DataFrame([{'category':cat,'terms':len(set(lexicon.cats[cat]))} for cat in method['categories']])
    counts.to_csv(out/'empath_category_sizes.csv',index=False)
    print('Empath specification saved: all 194 supplied categories; no category selection.',flush=True)
    all_summary=list(csv.DictReader((base/'method_summary.csv').open()))
    all_results=list(csv.DictReader((base/'all_dimension_results.csv').open()))
    original_results=[dict(r) for r in all_results]
    coverage_summary=[]
    for preprocessing in ['word_tokens','package_default']:
        # Block network calls even if a future package revision attempts one during scoring.
        with patch('requests.sessions.Session.request',side_effect=RuntimeError('Empath scoring must remain offline')):
            scores,coverage=empath_scores(data.m_text,lexicon,method['categories'],preprocessing)
        assert np.isfinite(scores.to_numpy()).all() and len(scores)==800
        output=pd.concat([part[['uid']],scores],axis=1)
        output.to_csv(out/f'empath_{preprocessing}_scores.csv',index=False)
        pd.concat([part,coverage],axis=1).to_csv(out/f'empath_{preprocessing}_coverage.csv',index=False)
        model_id='empath_supplied' if preprocessing=='word_tokens' else 'empath_package_default'
        for sample,mask in [('common',common),('full',np.ones(len(common),dtype=bool))]:
            frame=scores.loc[mask].reset_index(drop=True)
            rows,testing=analyze(frame,data.m_group[mask],data.m_split[mask],cfg.permutations)
            assert testing['permutations']==5000 and len(rows)==194
            stat=summary('Empath',model_id,sample,rows,int(mask.sum()),preprocessing=preprocessing,
                         primary=preprocessing=='word_tokens')
            all_summary.append(stat)
            all_results.extend({'method':'Empath','model_id':model_id,'sample':sample,**r} for r in rows)
            cover=coverage.loc[mask]
            coverage_summary.append({'model_id':model_id,'sample':sample,'n':int(mask.sum()),
                                     'tokens':int(cover.tokens.sum()),'matched_tokens':int(cover.dictionary_matched_tokens.sum()),
                                     'pooled_token_coverage':float(cover.dictionary_matched_tokens.sum()/cover.tokens.sum()),
                                     'responses_without_matches':int((~cover.any_dictionary_match).sum()),
                                     'constant_categories':int((frame.nunique()==1).sum())})
            print(json.dumps(stat),flush=True)
    pd.DataFrame(all_summary).to_csv(out/'method_summary.csv',index=False)
    pd.DataFrame(all_results).to_csv(out/'all_dimension_results.csv',index=False)
    reread=list(csv.DictReader((out/'all_dimension_results.csv').open()))
    assert reread[:len(original_results)]==original_results
    pd.DataFrame(coverage_summary).to_csv(out/'empath_coverage_summary.csv',index=False)
    manifest={**parent,'status':'completed_exploratory_comparison_with_empath',
              'parent_analysis_manifest_sha256':sha256(base/'manifest.json'),'parent_results_unchanged':True,
              'empath':method,'empath_tested_categories_per_family':194,
              'empath_model_ids':['empath_supplied','empath_package_default'],
              'empath_extension_wall_seconds':round(time.monotonic()-started,3),
              'empath_source_sha256':{str(f.relative_to(Path(__file__).resolve().parents[1])):sha256(f) for f in
                                      [Path(__file__).resolve(),Path(__file__).resolve().parents[1]/'src/discern/baselines.py',
                                       Path(__file__).resolve().with_name('run_baseline_comparison.py')]}}
    manifest['versions']={**parent['versions'],'empath':importlib.metadata.version('empath'),
                          'requests':importlib.metadata.version('requests')}
    manifest['limitations']=parent['limitations']+['Empath categories overlap; normalized scores are lexical match proportions, not construct prevalence.',
                                                  'Preprocessing variants are sensitivity checks; no choice based on outcomes.']
    manifest['output_sha256']={str(f.relative_to(out)):sha256(f) for f in out.rglob('*') if f.is_file() and f.name!='manifest.json'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'out':str(out),'dimensions_added':194*4,'api_calls':0},indent=2))


if __name__=='__main__':main()
