"""Render an explanatory planning map, not a PCB or manufacturing drawing."""
from pathlib import Path
import json,html
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
def render():
 d=json.loads((OUT/'evidence.json').read_text());g=json.loads((ROOT/'reviews/codex/imu_placement/geometry.json').read_text())['existing'];s=[]
 def add(t):s.append(t)
 def text(x,y,t,size=18,color='#24384b'):add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{html.escape(t)}</text>')
 def rect(a,color,stroke,dash=''):
  x,y,X,Y=a;add(f'<rect x="{40+(x-50)*12}" y="{175+(y-50)*12}" width="{(X-x)*12}" height="{(Y-y)*12}" fill="{color}" stroke="{stroke}" stroke-width="2" stroke-dasharray="{dash}"/>')
 add('<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900"><rect width="1440" height="900" fill="#f4f7fb"/><g font-family="Arial, sans-serif">')
 text(40,48,'6S power: define the boundary before routing',32)
 text(40,82,'REVIEW ONLY • Existing courtyards and proposed allowances • No copper or component changes',19)
 text(40,118,'Normal input: 7–25.2 V. Surge, source impedance, temperature and simultaneous loads still need bounds.',19)
 rect([50,50,130,96],'#fff','#36536b')
 for f in g:
  if f['courtyard_aabb_mm']:rect(f['courtyard_aabb_mm'],'#e8edf2','#ced7df')
 for f in g:
  if f['ref'] in ['C1','F1','Q1','D1','D2','U2','U3','U8','L1','L2','U1','U6']:
   rect(f['courtyard_aabb_mm'],'#d8e9f6','#3b7298');x,y=f['xy'];text(40+(x-50)*12-12,175+(y-50)*12+5,f['ref'],14)
 for a in d['package_studies']:rect(a['aabb_mm'],'none','#c36715' if a['ref']=='C1' else '#b33256','7 5')
 text(1040,203,'ORANGE / C1',18,'#a95812');text(1040,235,'8 mm body study',20)
 text(1040,264,'10.6 × 8.8 mm AABB',17);text(1040,292,'93.28 mm²; no AABB overlap',16)
 text(1040,325,'Not a qualified footprint swap.',16)
 text(1040,385,'RED / U2 AND U3',18,'#b33256');text(1040,417,'10 × 10 mm allowances',20)
 text(1040,446,'Proposed planning boxes only.',16)
 text(1040,474,'4 / 8 existing AABB overlaps.',16)
 text(1040,502,'No minimum-area claim.',16)
 text(1040,560,'GRAY / EXISTING',18);text(1040,590,'118 footprint courtyard bounds.',16)
 text(1040,620,'Copper and zones are not shown.',16)
 text(1040,677,'80 × 46 mm board outline',18)
 text(40,777,'ORDERING HOLDS',20,'#a95812')
 text(40,810,'C1: specified body does not match footprint. F1: 1206 slow-blow part assigned to fast-acting 1812 description.',19)
 text(40,843,'D2: 10 V schematic / 12 V PCB value. These identity conflicts must be resolved with the protection redesign.',19)
 text(40,877,'Source: power_envelope/evidence.json • Corrected live PCB remains unchanged • Fabrication and hardware gates open',16)
 add('</g></svg>');return '\n'.join(s)+'\n'
if __name__=='__main__':(OUT/'v2_power_envelope.svg').write_text(render(),encoding='utf-8',newline='\n')
