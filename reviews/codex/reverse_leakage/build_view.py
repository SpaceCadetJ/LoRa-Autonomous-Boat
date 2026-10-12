"""Render a self-contained review UI from the tested analytical model."""
from pathlib import Path
import json,sys
import model
P=Path(__file__).resolve().parent

def render():
    analysis=json.loads((P/'analysis.json').read_text());assert analysis==model.study()
    curves=[[{'time_s':i/80,'voltage_v':model.rc_voltage(i/80,0,c['assumed_total_sink_a'],analysis['resistor']['maximum_ohm'],47e-6)} for i in range(81)] for c in analysis['dc_cases']]
    data=json.dumps({'analysis':analysis,'curves':curves},separators=(',',':')).replace('<','\\u003c')
    return (P/'view.template.html').read_text().replace('__DATA__',data)
if __name__=='__main__':
    text=render();out=P/'index.html'
    if '--check' in sys.argv:assert out.read_text()==text,'Saved review UI is stale'
    else:out.write_text(text,encoding='utf-8',newline='\n')
    print('Analytical viewer '+('checked' if '--check' in sys.argv else 'built')+'; no circuit qualification.')
