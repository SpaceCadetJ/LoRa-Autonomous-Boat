"""Focused checks of ACT-11 topology and conditional arithmetic, not hardware."""
import copy, math, unittest
import build_packet as b
class PacketTests(unittest.TestCase):
    def test_captured_native_contract(self):
        b.validate(b.read('contract.json'))
    def test_supply_and_value_drift_rejected(self):
        for key in ['U4.3','C13.1','U4.7','C14.1','U4.6','R40.1']:
            c=copy.deepcopy(b.read('contract.json'));c['existing_memberships'][key]='WRONG'
            with self.subTest(pin=key),self.assertRaises(AssertionError):b.validate(c)
        c=copy.deepcopy(b.read('contract.json'));c['existing_values']['C13']='1nF'
        with self.assertRaises(AssertionError):b.validate(c)
    def test_unqualified_claims_rejected(self):
        for key in b.FALSE:
            c=copy.deepcopy(b.read('contract.json'));c[key]=True
            with self.subTest(key=key),self.assertRaises(AssertionError):b.validate(c)
        for key in b.DELTAS:
            c=copy.deepcopy(b.read('contract.json'));c[key]=1
            with self.subTest(key=key),self.assertRaises(AssertionError):b.validate(c)
    def test_illustration_drift_rejected(self):
        for key,value in [('nominal_C13_F',1e-9),('downstream_budget_s_allocated',1e-6),('feed_A_cases',[0]),('input_power_valid_assumed',False)]:
            c=copy.deepcopy(b.read('contract.json'));c['illustration'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):b.validate(c)
    def test_zero_feed_equation_independent(self):
        r=b.collect()['cases'][0]
        t=r['time_to_target_s_typical_model']
        self.assertAlmostEqual(3.6*math.exp(-t/(24*100e-9)),.08,places=14)
        self.assertAlmostEqual(t*1e6,9.135989975448767,places=10)
    def test_feed_sensitivity_and_guard_target(self):
        rows=b.collect()['cases'];self.assertLess(rows[0]['time_to_target_s_typical_model'],rows[1]['time_to_target_s_typical_model'])
        self.assertLess(rows[1]['time_to_target_s_typical_model'],rows[2]['time_to_target_s_typical_model'])
        self.assertIsNone(rows[3]['time_to_target_s_typical_model'])
        self.assertTrue(.08<rows[3]['floor_V_typical_model']<.1)
    def test_charge_and_time_budget(self):
        a=b.collect();self.assertAlmostEqual(a['charge_C_at_nominal_C13'],352e-9,places=18)
        self.assertAlmostEqual(a['average_net_sink_A_for_245ns']*245e-9,352e-9,places=18)
    def test_no_physical_acceptance_from_arithmetic(self):
        a=b.collect()
        for key in ['native_accepted','hardware_accepted','supply_collapse_timing_qualified']:self.assertIs(a[key],False)
if __name__=='__main__':unittest.main()
