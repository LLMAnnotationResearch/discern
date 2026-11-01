"""Guard common-sample alignment and honest reporting of baseline tiers."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_baseline_comparison import align_scores, analyze, exclusive_tier
from build_baseline_exhibits import table_tex, primary_summaries


class ComparisonTests(unittest.TestCase):
    def test_uid_alignment_is_explicit_and_rejects_missing_or_duplicate_units(self):
        frame=pd.DataFrame({'uid':['b','a'],'value':[20,10]})
        self.assertEqual(align_scores(frame,['a','b']).value.tolist(),[10,20])
        for invalid in [frame.iloc[:1],pd.concat([frame,frame.iloc[:1]])]:
            with self.assertRaises(ValueError):align_scores(invalid,['a','b'])

    def test_exclusive_tiers_keep_suggestive_separate_from_uncorrected(self):
        base={'d1_native':.1,'d2_native':.1,'perm_p':.04,'q05':False,'q10':False}
        self.assertEqual(exclusive_tier(base),'U')
        self.assertEqual(exclusive_tier({**base,'q10':True}),'S')
        self.assertEqual(exclusive_tier({**base,'q05':True,'q10':True}),'V')
        self.assertEqual(exclusive_tier({**base,'d2_native':-.1,'perm_p':1}),'N')

    def test_conventional_sensitivity_does_not_replace_production_replication_rule(self):
        groups=np.array([1,1,0,0]*2);halves=np.repeat([1,2],4)
        scores=pd.DataFrame({'one':[2.,3.,1.,2.]*2,'two':[3.,2.,2.,1.]*2})
        saved=[{'dimension':c,'d1_native':1.,'d2_native':1.,'perm_p':1.,'q05':False,'q10':False} for c in scores]
        with patch('run_baseline_comparison.test_scores',return_value=(saved,{'family':['one','two']})) as assess:
            rows,meta=analyze(scores,groups,halves,7)
        assess.assert_called_once()
        self.assertEqual([r['perm_p'] for r in rows],[1.,1.])
        self.assertEqual([r['tier'] for r in rows],['N','N'])
        self.assertTrue(all(0<=r['welch_p']<=1 for r in rows))
        self.assertEqual(meta['family'],['one','two'])

    def test_main_exhibit_includes_lda_sensitivity_survivors(self):
        summaries=[{'method':method,'model_id':'primary','sample':'common','dimensions':str(n),
                    'validated':'0','suggestive_only':'0','uncorrected_only':'0'}
                   for method,n in [('Sentiment',1),('LDA',5),('Discern',35)]]
        summaries.append({**summaries[1],'model_id':'sensitivity','dimensions':'20','validated':'1'})
        dimensions=[{'method':'Sentiment' if i==0 else 'LDA','dimension':'compound' if i==0 else f'topic_{i:02}',
                     'focal_mean_native':'.2','reference_mean_native':'.1',
                     'mean_half_difference_native':'.1','perm_p':'.04'} for i in range(6)]
        text=table_tex(summaries,dimensions,'primary',794)
        self.assertIn('LDA sensitivity (2 fits) & 5--20 & 0--1',text)
        self.assertIn('Pyramid and scheme metaphors',text)
        self.assertIn('Management levels and layers',text)

    def test_empath_primary_row_uses_frozen_categories_and_not_a_default_sensitivity(self):
        common={'sample':'common','dimensions':'194','validated':'0','suggestive_only':'0','uncorrected_only':'12'}
        rows=[{**common,'method':method,'model_id':'primary'} for method in ['Sentiment','LDA','Discern']]
        rows.insert(0,{**common,'method':'Empath','model_id':'empath_package_default','uncorrected_only':'5'})
        rows.append({**common,'method':'Empath','model_id':'empath_supplied'})
        primary=primary_summaries(rows,'primary')
        self.assertEqual([r['method'] for r in primary],['Sentiment','Empath','LDA','Discern'])
        self.assertEqual(primary[1]['model_id'],'empath_supplied')
        self.assertEqual(primary[1]['uncorrected_only'],'12')


if __name__=='__main__':unittest.main()
