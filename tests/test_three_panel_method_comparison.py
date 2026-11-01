"""Conventional differences are selected by their native test and shown without interpretation."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_three_panel_method_comparison import select_differences, panel_tex


class ThreePanelTests(unittest.TestCase):
    def test_selection_uses_conventional_test_and_keeps_every_eligible_fit(self):
        row={'method':'LDA','sample':'common','model_id':'model1','welch_p':'.01','welch_q05':'False','perm_p':'1','tier':'not_validated'}
        rows=[row,{**row,'model_id':'model2','welch_p':'.02','welch_q05':'True'},
              {**row,'model_id':'model3','welch_p':'.1','perm_p':'.001','tier':'confirmed'}]
        self.assertEqual([r['model_id'] for r in select_differences(rows,'LDA','nominal')],['model1','model2'])
        self.assertEqual([r['model_id'] for r in select_differences(rows,'LDA','bh')],['model2'])

    def test_empath_default_sensitivity_does_not_enter_the_primary_panel(self):
        row={'method':'Empath','sample':'common','model_id':'empath_supplied','welch_p':'.01','welch_q05':'False'}
        self.assertEqual(select_differences([row,{**row,'model_id':'empath_package_default'}],'Empath','nominal'),[row])

    def test_three_panels_reproduce_words_levels_and_fields_without_semantic_labels(self):
        panels={'A':[{'women':.175,'men':.173,'p':.959}],
                'B':[{'label':'K20/S2/T12','display_words':'bureaucracy, making, decision','women':.03,'men':.06,'p':.0003}],
                'C':[{'label':'positive emotion','women':.008,'men':.003,'p':.01}]}
        text=panel_tex(panels,'nominal')
        for term in ['A. VADER','B. LDA','C. Empath','bureaucracy, making, decision','positive emotion','unadjusted',r'\(<.001\)']:
            self.assertIn(term,text)
        for term in ['Representative','Gatekeeping','Supportive','Validated','Suggestive']:
            self.assertNotIn(term,text)

    def test_bertopic_adds_raw_word_panel_and_clarifies_first_lda_run(self):
        panels={'A':[{'women':.175,'men':.173,'p':.959}],'B':[],'C':[],
                'D':[{'label':'T4','display_words':'bureaucracy, tape, red tape','women':.028,'men':.065,'p':.012}]}
        text=panel_tex(panels,'nominal',{'common_outlier_count':297,'common_n':794})
        self.assertIn(r'\begin{longtable}',text)
        self.assertIn('D. BERTopic topics',text)
        self.assertIn('bureaucracy, tape, red tape',text)
        self.assertIn('None of the five topics in the first LDA run differed significantly between women and men',text)
        self.assertIn('37.4',text)


if __name__=='__main__':unittest.main()
