"""Audit exclusive reporting tiers without assuming placebo runs yield zero."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_paper_tables import check_tiers, placebo_tex, require_complete_measurement, recurrence_rows
from build_validation_latex import run_tex


class PaperTableTests(unittest.TestCase):
    def test_recurrence_remains_visible_without_inheriting_composite_validation(self):
        rows=[{'theme_id':'T01','theme':'Old label'},{'theme_id':'T02','theme':'Second label'}]
        links=[{'theme_id':'T01','run_id':'ARCHIVE','candidate_id':'focused','link_type':'focused','tier':'not_validated'},
               {'theme_id':'T01','run_id':'ARCHIVE','candidate_id':'broad','link_type':'composite','tier':'confirmed'},
               {'theme_id':'T02','run_id':'ARCHIVE','candidate_id':'broad','link_type':'composite','tier':'confirmed'},
               {'theme_id':'T01','run_id':'R01','candidate_id':'replica','link_type':'focused','tier':'confirmed'}]
        result=recurrence_rows(rows,links)
        self.assertEqual(result[0]['ARCHIVE'],'proposed')
        self.assertEqual(result[0]['R01'],'validated')
        self.assertEqual(result[1]['ARCHIVE'],'broader')
        self.assertEqual(result[1]['E_OPENAI'],'absent')
        self.assertEqual(result[0]['theme'],'Slow procedures and approvals')
        links.append({'theme_id':'T02','run_id':'R01','candidate_id':'replica','link_type':'focused','tier':'confirmed'})
        with self.assertRaises(ValueError):recurrence_rows(rows,links)

    def test_incomplete_measurement_cannot_be_finalized_as_a_clean_placebo(self):
        with self.assertRaisesRegex(ValueError,'unmeasured candidates: P03'):
            require_complete_measurement([{'run_id':'P03','count':{'proposed':42,'measured':41}}])
        require_complete_measurement([{'run_id':'P03','count':{'proposed':42,'measured':42}}])

    def test_three_exclusive_tiers_and_placebo_survivor_remain_visible(self):
        rows=[]
        for i,(p,tier) in enumerate([(.002,'confirmed'),(.015,'suggestive'),(.04,'uncorrected')]+[(1.,'not_validated')]*7):
            rows.append({'candidate_id':str(i),'perm_p':p,'tier':tier,'d1':.1,'d2':.1,'mean_effect':.1,'same_sign':True})
        check_tiers(rows)
        table=placebo_tex([{'run':'Placebo 1','proposed':10,'measured':10,'validated':1,'suggestive_only':1,'uncorrected_only':1}])
        self.assertIn('Placebo 1 & 10 & 10 & 1 & 1 & 1',table)
        rows[1]['tier']='uncorrected'
        with self.assertRaises(AssertionError):check_tiers(rows)

    def test_unmeasurable_candidate_stays_in_catalogue_with_missing_statistics(self):
        cfg={'discovery_models':['test'],'rotation_pool':['test'],'consolidation_model':'test',
             'discovery_seed':100,'reservation_seed':1,'split_seed':2,'assignment_seed':3,'placebo_seed':4,'run_index':2}
        row={'exhibit_id':'G42','candidate_id':'c_missing','feature_name':'Ambiguous feature',
             'definition':'Exact definition','classification_question':'Exact question?',
             'tier':'unmeasurable','claimed_direction':'A_higher','source_splits':['split1'],
             'n_supporting_hypotheses':1,'direction_conflict':False,'same_sign':'not assessed',
             'measured_direction':'not assessed','measurement_issue':'Non-binary answers after retries'}
        result=run_tex({'run_id':'P03','label':'Placebo 3','cfg':cfg,'rows':[row]})
        self.assertIn('-- & -- & -- & -- & M',result)
        self.assertIn('Exact question?',result)
        self.assertIn('Non-binary answers after retries',result)


if __name__=='__main__':unittest.main()
