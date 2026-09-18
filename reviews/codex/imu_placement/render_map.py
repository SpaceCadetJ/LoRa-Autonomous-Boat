"""Draw a dimensioned review map from native footprint geometry, not a routing claim."""
from pathlib import Path
import json,math,html,hashlib,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
native=json.loads((OUT/'drc_study.json').read_text());errors=sum(v['severity']=='error' for v in native['violations'])
g=json.loads((OUT/'geometry.json').read_text());items={v['ref']:v for v in g['existing']+g['added']}
def pin(ref,n):return next(p['xy'] for p in items[ref]['pads'] if p['pin']==str(n))
pairs=[('C40',1,'U6',8,'VDDIO bypass'),('C38',1,'U9',1,'LDO input bypass'),('C39',1,'U9',5,'LDO output bypass'),('C41',1,'U11',1,'IRQ translator VCCA bypass'),('C42',1,'U11',6,'IRQ translator VCCB bypass'),('U10',3,'U6',23,'Sensor SCL'),('U10',4,'U6',24,'Sensor SDA'),('U11',3,'U6',12,'Sensor INT1')]
distances=[{'from':f'{a}.{b}','to':f'{c}.{d}','role':e,'straight_line_pad_distance_mm':round(math.dist(pin(a,b),pin(c,d)),3)} for a,b,c,d,e in pairs]
(OUT/'routing_distances.json').write_text(json.dumps({'scope':'Euclidean pad-center distance only; a lower bound, not routed trace length or electrical qualification.','pairs':distances},indent=2)+'\n',encoding='utf-8')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100" viewBox="0 0 1600 1100">','<rect width="1600" height="1100" fill="#f3f6f9"/>','<style>text{font-family:Arial,sans-serif} .title{font-size:32px;font-weight:bold;fill:#16344a}.sub{font-size:18px;fill:#506679}.head{font-size:21px;font-weight:bold;fill:#16344a}.note{font-size:18px;fill:#30495b}</style>']
def text(x,y,s,cl='note'):svg.append(f'<text x="{x}" y="{y}" class="{cl}">{html.escape(s)}</text>')
text(40,52,'IMU placement study | existing 80 × 46 mm board','title')
text(40,84,'MECHANICAL STUDY ONLY • New pads have no assigned nets • Existing copper is preserved • No fabrication release','sub')
text(40,128,'01  Board context','head');text(940,128,'02  Interface and sensor detail','head')
def panel(x,y,scale,crop,detail=False):
 x0,y0,x1,y1=crop;wid=(x1-x0)*scale;hei=(y1-y0)*scale
 svg.append(f'<svg x="{x}" y="{y}" width="{wid}" height="{hei}" viewBox="{x0} {y0} {x1-x0} {y1-y0}">')
 svg.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="white"/>')
 svg.append('<rect x="50" y="50" width="80" height="46" fill="#fff" stroke="#30495b" stroke-width=".16"/>')
 if not detail:svg.append('<rect x="50.2" y="58" width="54" height="37.8" fill="#fff5e3"/>')
 for f in g['existing']+g['added']+g['reserved_only']:
  a,b,c,d=f['courtyard_aabb_mm'];ref=f['ref'];new=f in g['added'];reserve=f in g['reserved_only']
  color='#136f90' if new else '#aa720e' if reserve else '#2b8471' if ref=='U6' else '#aebbc5'
  fill='#d9eff7' if new else '#fff0c9' if reserve else '#d5eee7' if ref=='U6' else '#f0f3f5'
  svg.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" rx=".15" fill="{fill}" stroke="{color}" stroke-width=".07"'+(' stroke-dasharray=".25 .15"' if reserve else '')+'/>')
  if detail or (not new and (ref.startswith(('U','J','L','H')))):
   label='C43?' if reserve else ref
   svg.append(f'<text x="{(a+c)/2}" y="{(b+d)/2+.22}" text-anchor="middle" font-size="{.6 if reserve else .72 if detail else .9}" font-weight="bold" fill="{color if new or reserve else "#445c6e"}">{label}</text>')
  if ref.startswith('H'):
   cx,cy=f['xy'];svg.append(f'<circle cx="{cx}" cy="{cy}" r="1.6" fill="white" stroke="#778b9b" stroke-width=".08"/>')
 svg.append('</svg>')
panel(40,155,10.7,(49,48,131,97));panel(940,155,24,(103.5,63,128.5,96.5),True)
text(40,713,'Blue: 12 proposed additions   Green: existing U6   Dashed amber: C43 reserve','sub')
text(40,750,'Courtyard envelopes only. Copper, tracks and reference silkscreen are omitted.','sub')
text(40,802,'FIT CHECK','head');text(40,837,'12 additions + one reserved site fit without courtyard overlap.','note')
text(40,867,'All 118 existing placements, mounting holes and copper remain fixed.','note')
text(40,915,f'COPPER CHECK: {errors} ERRORS — INTEGRATION BLOCKED','head');text(40,950,'20 existing tracks/vias are affected across seven nets.','note')
text(40,980,'C40 overlaps existing REGOUT / 3.3 V vias; this site needs rework.','note')
text(40,1010,'Full 6S fit is unresolved; amber marks the existing power area.','note')
text(40,1070,'Source: corrected PCB SHA-256 49a8aa88…62c37b2 | Geometry captured with KiCad 9 | See packet README for checks and limits.','sub')
svg.append('</svg>');(OUT/'v2_imu_placement.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(distances))
