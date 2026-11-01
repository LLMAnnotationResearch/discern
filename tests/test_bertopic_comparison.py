"""Native BERTopic assignment tests keep outliers and the complete topic family."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_bertopic_comparison import assignment_results


class BERTopicComparisonTests(unittest.TestCase):
    def test_outliers_stay_in_group_denominators_and_are_reported(self):
        groups=np.array([1,1,1,1,0,0,0,0])
        assignments=np.array([0,0,-1,1,0,1,-1,-1])
        rows={r['topic_id']:r for r in assignment_results(assignments,groups,[-1,0,1,2])}
        self.assertEqual(rows[0]['women'],.5)
        self.assertEqual(rows[0]['men'],.25)
        self.assertEqual(rows[-1]['women'],.25)
        self.assertEqual(rows[-1]['men'],.5)
        self.assertTrue(rows[-1]['is_outlier'])
        self.assertEqual(rows[2]['welch_p'],1.)
        self.assertEqual(len(rows),4)

    def test_unknown_topic_or_misaligned_labels_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError,'Every assignment'):
            assignment_results(np.array([0,-1,0,1]),np.array([1,1,0,0]),[0,1])
        with self.assertRaisesRegex(ValueError,'aligned'):
            assignment_results(np.array([0,0,1]),np.array([1,0]),[0,1])


if __name__=='__main__':unittest.main()
