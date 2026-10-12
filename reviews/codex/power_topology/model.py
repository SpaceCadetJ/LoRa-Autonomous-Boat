"""Transparent power arithmetic for proposed topologies; not circuit simulation."""
import json,math
from pathlib import Path
OUT=Path(__file__).resolve().parent

def budget(vin,logic_a,servo_a,aux5_a=0.02,eta3=0.85,eta5=0.85):
    vals=[vin,logic_a,servo_a,aux5_a,eta3,eta5]
    if not all(math.isfinite(v) for v in vals) or vin<=0 or min(logic_a,servo_a,aux5_a)<0 or not(0<eta3<=1 and 0<eta5<=1):raise ValueError('Invalid budget input')
    p3=3.3*logic_a;p5=5*(servo_a+aux5_a);pin=p3/eta3+p5/eta5
    return {'output_power_w':p3+p5,'converter_input_power_w':pin,'input_current_a':pin/vin,'current_5v_a':servo_a+aux5_a,'exceeds_1a_feed':pin/vin>1,'exceeds_2a_5v_converter':servo_a+aux5_a>2,'loss_3v3_w':p3*(1/eta3-1),'loss_5v_w':p5*(1/eta5-1),'max_servo_a_for_1a_feed':max(0,((vin-p3/eta3)*eta5/5)-aux5_a)}

def cutoff(rt=539000,rb=10000,tol=0.001,leak=10e-9):
    if not all(math.isfinite(v) for v in [rt,rb,tol,leak]) or rt<=0 or rb<=0 or not(0<=tol<1) or leak<0:raise ValueError('Invalid cutoff inputs')
    kmin=1+rt*(1-tol)/(rb*(1+tol));kmax=1+rt*(1+tol)/(rb*(1-tol))
    # Conservative independent extrema: pin leakage contributes I * Rtop.
    error=leak*rt*(1+tol)
    return {'ratio_nominal':1+rt/rb,'ratio_min':kmin,'ratio_max':kmax,'trip_min_v':.4925*kmin-error,'trip_max_v':.5075*kmax+error,'recovery_min_v':(.4925-.032)*kmin-error,'operating_margin_to_28v':28-(.5075*kmax+error),'normal_restart_margin_v':(.4925-.032)*kmin-error-25.2,'voltage_at_specified_50mv_overdrive_v':(.5075+.05)*kmax+error}

def study():
    cases={}
    for name,logic,servo in [('external_bec_logic_ceiling',1.2,0),('illustrative_mixed_load',.35,.5),('simultaneous_output_goals',1.2,2)]:
        cases[name]={str(v):budget(v,logic,servo) for v in [7,25.2]}
    return {'schema':1,'status':'analytical_planning_only','electrical_delta':0,'hardware_tested':False,'assumptions':{'normal_input_v':[7,25.2],'logic_rail_v':3.3,'servo_rail_v':5,'aux5_a':.02,'efficiency_each':.85,'efficiency_is_measured':False,'excluded':['frontend conduction losses','quiescent input currents','inrush and short circuits','ESC motor current, fed directly from battery','external BEC energy and servo wiring losses']},'cases':cases,'ideal_simultaneous_without_aux_at_7v':budget(7,1.2,2,0,1,1),'cutoff_0p1percent':cutoff(),'cutoff_1percent':cutoff(tol=.01),'charged_output_negative_pulse_differential_v':25.2+53.3,'lm74700_recommended_differential_limit_v':70,'lm74700_absolute_differential_limit_v':75}

if __name__=='__main__':
    import sys
    value=study();p=OUT/'comparison.json'
    if '--check' in sys.argv:assert json.loads(p.read_text())==value,'Study differs'
    else:p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(value,indent=2))
