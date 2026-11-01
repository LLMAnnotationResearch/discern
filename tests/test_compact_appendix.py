"""Consolidation must retain nonvalidated candidates and their numerical results."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_compact_appendix_d import candidate_results_tex, catalogue_html


class CompactAppendixTests(unittest.TestCase):
    def test_every_tier_is_retained_with_exact_names_and_a_catalogue_question(self):
        rows=[]
        for i,tier in enumerate(['confirmed','suggestive','uncorrected','not_validated'],1):
            rows.append({'run_id':'R','exhibit_id':f'A{i:02}','feature_name':f'Feature {i}',
                         'definition':f'Definition {i}','classification_question':f'Question {i}?',
                         'd1':'.1','d2':'.12','mean_effect':'.11','perm_p':'.023456','tier':tier})
        text=candidate_results_tex(rows,['R'],{'R':'Run'})
        html=catalogue_html(rows,['R'],{'R':'Run'})
        for row,tag in zip(rows,['V','S','U','N']):
            self.assertEqual(text.count(row['exhibit_id']+' & '),1)
            self.assertIn(row['feature_name']+' & +10.00 & +12.00 & +11.00 & 0.0235 & '+tag,text)
            self.assertIn(row['classification_question'],html)
        self.assertNotIn('Definition 1',text)
        self.assertIn('Definition 1',html)

    def test_unknown_run_and_duplicate_ids_cannot_silently_remove_a_candidate(self):
        row={'run_id':'unknown','exhibit_id':'A01','tier':'not_validated'}
        with self.assertRaisesRegex(ValueError,'omission'):candidate_results_tex([row],[],{})
        with self.assertRaisesRegex(ValueError,'Duplicate'):candidate_results_tex([row,row],[],{})


if __name__=='__main__':unittest.main()
