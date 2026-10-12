"""Export the arithmetic intervals with matplotlib. No circuit or source generation."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / 'analysis.json').read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.hashsalt': 'act05-2026-10-12'})
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
fig.set_facecolor('#f3f6f8')
colors = ['#177995', '#408077', '#84639e']
for ax, case in zip(axes.flat, DATA['cases']):
    rows = [case['converter_V'], case['guaranteed_no_new_fault_band_V'], case['guaranteed_recovery_band_V']]
    for y, limits, color in zip([2, 1, 0], rows, colors):
        ax.plot(limits, [y, y], linewidth=10, color=color, solid_capstyle='round')
        ax.text(limits[0], y+.21, f'{limits[0]:.4f}', ha='right', fontsize=9)
        ax.text(limits[1], y+.21, f'{limits[1]:.4f}', ha='left', fontsize=9)
    rail = case['nominal_rail_V']
    ax.set_xlim((2.9, 3.7) if rail == 3.3 else (4.4, 5.6))
    ax.set_ylim(-.6, 2.7)
    ax.set_yticks([2, 1, 0], ['Converter', 'No new fault', 'Recovery'])
    ax.set_xlabel('Voltage (V)')
    window = '4%' if case['SET'] == 'high' else '9%'
    ax.set_title(f'{rail:g} V rail | nominal +/-{window}', loc='left', fontweight='bold', pad=16)
    ax.grid(axis='x', alpha=.22)
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis='y', length=0)
fig.suptitle('ACT-05 | Rail supervision before circuit selection', x=.065, ha='left', fontsize=20, fontweight='bold')
fig.text(.065, .91, 'Conditional arithmetic only. Fixed-window choice remains held; ACT-04 qualification and ACK stay disabled.', fontsize=11)
fig.text(.065, .055, 'Main screen: TPS3702 section 6.3.3 rail-based accuracy; nominal-table union and recovery hysteresis.\nSource ambiguity sensitivity is separate in analysis.json. Dynamic/PFM, startup, edge and remote-ready limits remain open.', fontsize=10, color='#526975')
fig.subplots_adjust(left=.12, right=.97, top=.82, bottom=.16, wspace=.30, hspace=.7)
fig.savefig(HERE / 'v2_rail_qualification.svg', metadata={'Date': None})
fig.savefig(HERE / 'figure-preview.png', dpi=110)
print('Exported conditional interval SVG and preview; no CAD changes')
