"""Version a discovery-grounded repair; never overwrite the initial P03 attempt.

This script reads discovery/consolidation, configuration and classification cache
only. It does not choose wording from effects, p-values, or group measurements.
The repair is post hoc to a nonbinary-answer failure and must be disclosed.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discern.audit import Audit
from discern.core import register_candidates
from discern.validation import sha256


def prepare(config,out):
    config,out=Path(config).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads(config.read_text());source=Path(cfg['output_dir'])/'P03'
    discovery=json.loads((source/'01_discovery.json').read_text())
    bank=json.loads((source/'02_consolidated.json').read_text())
    original=next(c for c in bank['candidates'] if c['candidate_id']=='c_c75a733a0e89c6a3')
    assert original['classification_question']=='Does the response associate a positive, negative, or neutral connotation with tall organizational structures?'
    supporting=[h for h in discovery['split2'] if 'connotation' in json.dumps(h).lower()]
    assert any(h['dimension']=='Connotation of Tall Structure' and 'negative connotations' in h['measurement_question'] for h in supporting)
    corrected=copy.deepcopy(original)
    corrected.update(feature_name='Negative Connotation of Tall Structure',
                     definition='Associates a tall organizational structure with a negative connotation.',
                     classification_question='Does the response associate a tall organizational structure with a negative connotation?')
    corrected=register_candidates([corrected])[0][0]
    bank['candidates']=[corrected if c['candidate_id']==original['candidate_id'] else c for c in bank['candidates']]
    assert len(bank['candidates'])==42
    # Unchanged questions retain their cache identities. The repaired question has
    # a new content ID and cache key, so every reserved response is measured anew.
    cfg['output_dir']=str(out/'outputs');newrun=Path(cfg['output_dir'])/'P03_REPAIRED'
    audit=Audit(newrun)
    audit.write_stage('01_discovery',discovery);audit.write_stage('02_consolidated',bank)
    repair={'status':'discovery_grounded_operationalization_repair','initial_run':str(source),
            'original':original,'corrected':corrected,'discovery_evidence':supporting,
            'reason':'Consolidation replaced the negative-connotation construct in discovery with an exhaustive positive/negative/neutral list, eliciting nonbinary answers.',
            'timing':'Repair made after measurement-format failure and inspection of the initial run; not preregistered.',
            'policy':'One negative-connotation property, chosen from original discovery evidence. No changes to data reservation, labels, halves, models, selection rules or the other 41 questions. Remeasure all 800 responses for the changed question, then rerun selection over all 42 candidates.',
            'source_sha256':{n:sha256(source/n) for n in ['01_discovery.json','02_consolidated.json']}}
    audit.write_stage('02b_operationalization_repair',repair)
    shutil.copy2(source.parent/'class_cache.json',Path(cfg['output_dir'])/'class_cache.json')
    path=out/'P03_REPAIRED.config.json';path.write_text(json.dumps(cfg,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'purpose':repair['policy'],'planned_jobs':[{'run_id':'P03_REPAIRED','config_path':str(path),'sha256':sha256(path),'condition':'placebo'}]},indent=2)+'\n')
    print(json.dumps({'new_run':str(newrun),'corrected_candidate_id':corrected['candidate_id'],'question':corrected['classification_question']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();prepare(a.config,a.out)
