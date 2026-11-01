"""Recover successful binary judgments from a stopped run's audit log.

Only fills missing cache entries after checking the run identity. Never changes
an existing entry, a prompt, a candidate, or a judgment. Stop the writer first.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discern.config import RunConfig
from discern.data import Dataset
from discern.measure import Cache
from discern.validation import sha256


def recover(config,run,out):
    cfg,base=RunConfig.from_file(config);cfg=cfg.resolve(base);cfg.validate()
    run,out=Path(run),Path(out);out.mkdir(parents=True,exist_ok=False)
    data=Dataset(cfg);spec=json.loads((run/'00_runspec.json').read_text())
    assert spec['spec_hash']==cfg.spec_hash(data.fingerprint)
    bank={c['candidate_id']:c for c in json.loads((run/'02_consolidated.json').read_text())['candidates']}
    cache_path=Path(cfg.output_dir)/'class_cache.json'
    shutil.copy2(cache_path,out/'class_cache_before_recovery.json')
    cache=Cache(cache_path,data.fingerprint,cfg.prompt_version,f'design={cfg.measurement_design}|unit={cfg.unit_label}',revisions=cfg.model_revision)
    n=0;uids=set(data.m_uid)
    for e in map(json.loads,(run/'events.jsonl').open()):
        if e['stage']!='measure' or e['kind']!='response':continue
        assert e['uid'] in uids and e['model'] in cfg.rotation_pool and e['answer'] in [0,1]
        c=bank[e['candidate_id']];q,d=c['classification_question'],c.get('definition','')
        if cache.get(e['uid'],e['model'],q,d) is None:
            cache.put_many([(e['uid'],e['model'],q,d,e['answer'])]);n+=1
    (out/'recovery.json').write_text(json.dumps({'recovered_entries':n,'events_sha256':sha256(run/'events.jsonl'),'cache_before_sha256':sha256(out/'class_cache_before_recovery.json'),'cache_after_sha256':sha256(cache_path),'config_sha256':sha256(config),'run_spec':spec['spec_hash'],'policy':'Only missing entries; first successful binary audit response; no changes to existing entries or prompts.'},indent=2)+'\n')
    print(n,'binary judgments recovered')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--run',required=True);p.add_argument('--out',required=True);a=p.parse_args();recover(a.config,a.run,a.out)
