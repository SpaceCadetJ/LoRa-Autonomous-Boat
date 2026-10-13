"""Render ACT-06 calculation tables only; no native CAD or primary generators."""
from pathlib import Path
import argparse,json
HERE=Path(__file__).resolve().parent

def render():
    data=json.loads((HERE/'analysis.json').read_text(encoding='utf-8-sig'))
    lines=['# ACT-06 calculated comparison','',
           'Generated from [analysis.json](analysis.json) by [build_results.py](build_results.py). Values are conditional engineering screens; all dynamic/hardware acceptance remains false. See [assumptions and next task](README.md).','',
           '## Integrated TPS3703 windows','',
           'Nominal-trip hysteresis is the main screen; the data file retains actual-trip sensitivity. Positive static margins do not establish acceptable fault response.','',
           '| Part | UV assertion V | OV assertion V | Screened recovery interval V | Initial static screen |',
           '|---|---:|---:|---:|---|']
    pair=lambda x:f'{x[0]:.6f}–{x[1]:.6f}'
    for c in data['integrated_cases']:
        lines.append(f"| {c['part']} | {pair(c['assert_V']['UV'])} | {pair(c['assert_V']['OV'])} | {pair(c['screened_recovery_band_V'])} | {'Pass, conditional only' if c['static_screen_pass'] else 'Fails: '+', '.join(c['reasons'])} |")
    lines+=['','## Stated maximum-delay test amplitudes','',
            'Eq7 uses nominal threshold in the overdrive denominator: UV = latest low trip − 5% of nominal UV trip; OV = latest high trip + 5% of nominal OV trip. Negative corridor margin means the required test amplitude is already outside the corridor, before allocating any propagation time. This does not predict actual device failure.','',
            '| Part | UV test V | OV test V | UV corridor margin mV | OV corridor margin mV |',
            '|---|---:|---:|---:|---:|']
    for c in data['integrated_cases']:
        t=c['timing_step_screen'];lines.append(f"| {c['part']} | {t['UV_test_rail_V']:.6f} | {t['OV_test_rail_V']:.6f} | {1000*t['UV_corridor_margin_V']:.3f} | {1000*t['OV_corridor_margin_V']:.3f} |")
    lines+=['','## Adjustable TPS3700 divider comparison','',
            'Initial tolerance and the illustrative temperature budget apply independently to each resistor. Threshold-node bias applicability, selected resistor identities, aging and full converter behavior remain unqualified. Each recovery interval must contain the full recorded converter interval; each latest trip must remain inside its comparison corridor.','',
            '| Rail / budget | UV assertion V | OV assertion V | Recovery interval V | Lower recovery margin mV | Upper recovery margin mV | Late OV margin mV |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for c in data['divider_cases']:
        m=c['margins_V'];lines.append(f"| {c['rail_id']} / ±{100*c['resistor_tolerance_fraction']:.2f}% | {pair(c['assert_V']['UV'])} | {pair(c['assert_V']['OV'])} | {pair(c['screened_recovery_band_V'])} | {1000*m['recovery_lower']:.3f} | {1000*m['recovery_upper']:.3f} | {1000*m['late_OV']:.3f} |")
    lines+=['','## 3V3 overvoltage ratio feasibility','',
            'For a nominal 1k bottom resistor, arbitrary positive top resistance and the stated threshold/bias assumptions:','',
            '| Independent resistor budget | Required ratio greater than | Required ratio less than | Nonempty interval |',
            '|---|---:|---:|---|']
    f=data['resistor_feasibility']
    for c in f['3V3_OV_ratio_cases']:
        lines.append(f"| ±{100*c['resistor_tolerance_fraction']:.2f}% | {c['required_ratio_lower_exclusive']:.9f} | {c['allowed_ratio_upper_exclusive']:.9f} | {'Yes' if c['has_feasible_ratio'] else 'No'} |")
    lines+=['',f"The fixed 7.87k/1k proposal reaches zero static guard at approximately **{100*f['fixed_proposal_budget_suprema_fraction']['3V3_OV']:.6f}%** error per resistor. Optimizing the continuous ratio extends this to approximately **{100*f['any_3V3_OV_ratio_budget_supremum_fraction']:.6f}%**. These suprema are not acceptable component specifications: strict positive margin is required, with dynamic/aging budgets still unallocated.",'',
            'The four dividers also add load. The exact top/bottom branch-current intervals are retained in analysis.json; these are calculated currents, not bench readings.','',
            '**Disposition:** no part selection or qualification-driver connection. Continue with the bounded 3V3 observation subcell specified in README.md.','']
    return '\n'.join(lines)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();text=render();path=HERE/'RESULTS.md'
    if args.check:
        assert path.read_text(encoding='utf-8')==text,'Comparison tables stale';print('PASS ACT-06 tables reproduce')
    else:path.write_text(text,encoding='utf-8',newline='\n')
