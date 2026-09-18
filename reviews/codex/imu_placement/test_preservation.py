"""Reject changes outside the explicitly mechanical placement scope."""
from pathlib import Path
import unittest
from compare_study import compare
P=Path(__file__).resolve().parent
class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=(P/'inputs/normalized_baseline.kicad_pcb').read_text()
        cls.after=(P/'study/IMU_PLACEMENT_STUDY.kicad_pcb').read_text()
    def test_recorded_study(self):
        self.assertEqual(compare(self.before,self.after)['original_footprints_preserved_exactly'],118)
    def test_reject_original_pad_or_net_change(self):
        altered=self.after.replace('(net 1 ', '(net 999 ',1)
        self.assertNotEqual(altered,self.after)
        with self.assertRaises(ValueError):compare(self.before,altered)
    def test_reject_copper_change(self):
        index=self.after.index('(segment')
        altered=self.after[:index]+self.after[index:].replace('(width ', '(width 9',1)
        with self.assertRaises(ValueError):compare(self.before,altered)
    def test_reject_wrong_added_reference(self):
        altered=self.after.replace('(property "Reference" "U9"','(property "Reference" "U99"',1)
        self.assertNotEqual(altered,self.after)
        with self.assertRaises(ValueError):compare(self.before,altered)
    def test_reject_new_electrical_assignment(self):
        # Inserting a net into the new footprint must fail even though no original block changes.
        from compare_study import children
        addition=next(x for x in children(self.after) if '(property "Reference" "U9"' in x)
        altered=self.after.replace(addition,addition[:-1]+'(net 999 "UNREVIEWED"))',1)
        with self.assertRaises(ValueError):compare(self.before,altered)
    def test_reject_truncated_board(self):
        with self.assertRaises(ValueError):compare(self.before,self.after[:-3])
if __name__=='__main__':unittest.main()
