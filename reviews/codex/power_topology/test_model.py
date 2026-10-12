import unittest,math
from model import budget,cutoff
class PowerConstraints(unittest.TestCase):
    def test_lossless_conservation(self):
        x=budget(7,1.2,2,0,1,1)
        self.assertAlmostEqual(x['input_current_a']*7,13.96)
        self.assertTrue(x['exceeds_1a_feed'])
    def test_external_bec_scope(self):
        x=budget(7,1.2,0)
        self.assertLess(x['input_current_a'],1)
        self.assertAlmostEqual(x['current_5v_a'],.02)
    def test_auxiliary_consumes_output_capacity(self):
        self.assertFalse(budget(25.2,1.2,1.98)['exceeds_2a_5v_converter'])
        self.assertTrue(budget(25.2,1.2,2)['exceeds_2a_5v_converter'])
    def test_efficiency_loss_changes_feed(self):
        self.assertGreater(budget(7,1.2,2)['input_current_a'],budget(7,1.2,2,eta3=1,eta5=1)['input_current_a'])
    def test_cutoff_tolerance_rejects_one_percent(self):
        self.assertGreater(cutoff()['normal_restart_margin_v'],0)
        self.assertGreater(cutoff()['operating_margin_to_28v'],0)
        self.assertLess(cutoff(tol=.01)['normal_restart_margin_v'],0)
        self.assertLess(cutoff(tol=.01)['operating_margin_to_28v'],0)
    def test_delay_condition_is_beyond_absolute_limit(self):
        self.assertGreater(cutoff()['voltage_at_specified_50mv_overdrive_v'],30)
    def test_invalid_cutoff(self):
        for name in ['rt','rb','tol','leak']:
            for value in [float('nan'),float('inf')]:
                with self.assertRaises(ValueError):cutoff(**{name:value})
        for values in [{'rt':0},{'rb':-1},{'tol':1},{'leak':-1}]:
            with self.assertRaises(ValueError):cutoff(**values)
    def test_invalid_budget(self):
        for values in [(0,1,1),(-7,1,1),(7,-1,1),(float('nan'),1,1)]:
            with self.assertRaises(ValueError):budget(*values)
        for eta in [0,-.1,1.01,float('inf')]:
            with self.assertRaises(ValueError):budget(7,1,1,eta3=eta)
if __name__=='__main__':unittest.main()
