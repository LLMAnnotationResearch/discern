"""The alternative-method exhibit compares meanings and preserves rich LDA examples."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_thematic_method_comparison import main_table, representative_indices, BRIDGES


class ThematicComparisonTests(unittest.TestCase):
    def test_passages_follow_topic_rank_without_group_or_outcome_selection(self):
        texts=['too short','one two three four five six seven eight']*3
        scores=np.array([1.,.7,.9,.8,.95,.8]);counts=np.array([20,7,10,6,1,9])
        self.assertEqual(representative_indices(scores,counts,texts),[3,5,1])

    def test_table_uses_substantive_readings_and_acknowledges_existing_lda_insights(self):
        readings=[{'method':'Sentiment','reading':'Overall valence'},
                  {'method':'LDA','reading':'Representative responses already contain nuanced concerns'},
                  {'method':'Empath','reading':'Predefined lexical fields'}]
        text=main_table(readings,BRIDGES)
        self.assertIn('Representative responses already contain nuanced concerns',text)
        self.assertIn('Representative LDA responses also contain several of these distinctions',text)
        self.assertIn('support, oversight, or fairness',text)
        self.assertIn('promotion barriers and gatekeeping',text.lower())
        for term in ['FDR','Suggestive','Uncorrected','5,000','Validated']:
            self.assertNotIn(term,text)


if __name__=='__main__':unittest.main()
