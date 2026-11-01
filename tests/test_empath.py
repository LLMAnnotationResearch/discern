"""Check lexical normalization, missingness, coverage, and the full category family."""
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discern.baselines import empath_lexicon, empath_scores, empath_tokens


class EmpathTests(unittest.TestCase):
    def test_case_and_punctuation_are_normalized_without_stemming(self):
        self.assertEqual(empath_tokens("WORK, Work! Don't work?"),['work','work',"don't",'work'])

    @unittest.skipUnless(importlib.util.find_spec('empath'),'optional Empath dependency not installed')
    def test_uses_package_matcher_retains_unmatched_words_in_denominator_and_all_categories(self):
        with patch('requests.sessions.Session.request',side_effect=AssertionError('network')):
            lexicon,meta=empath_lexicon()
            self.assertEqual(meta['category_count'],194)
            scores,cover=empath_scores(['WORK, xyznotaword','','xyznotaword'],lexicon,meta['categories'])
            raw,_=empath_scores(['WORK, xyznotaword'],lexicon,meta['categories'],'package_default')
        self.assertEqual(scores.shape,(3,194))
        self.assertAlmostEqual(scores.loc[0,'work'],.5)
        self.assertEqual(cover.loc[0,'dictionary_matched_tokens'],1)
        self.assertAlmostEqual(cover.loc[0,'dictionary_coverage'],.5)
        self.assertTrue(np.isnan(scores.iloc[1]).all())
        self.assertTrue((scores.iloc[2]==0).all())
        self.assertEqual(raw.loc[0,'work'],0)

    @unittest.skipUnless(importlib.util.find_spec('empath'),'optional Empath dependency not installed')
    def test_custom_categories_cannot_enter_the_supplied_family(self):
        from empath import Empath
        lexicon=Empath(backend_url=None);lexicon.cats['custom']=['work']
        with patch('empath.Empath',return_value=lexicon):
            with self.assertRaisesRegex(ValueError,'custom categories'):empath_lexicon()


if __name__=='__main__':unittest.main()
