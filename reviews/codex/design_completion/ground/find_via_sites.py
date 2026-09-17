"""Find narrowly scoped candidate vias within existing island/main copper overlap."""
from pathlib import Path
import json
import math
import pcbnew
from inspect_ground import BOARD, OUT, inspect, xy

b = pcbnew.LoadBoard(str(BOARD))
report = inspect()
lookup = {}
for z in b.Zones():
    if z.GetNetname() != 'GND' or z.GetIsRuleArea():
        continue
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        if z.IsOnLayer(lay):
            lookup[b.GetLayerName(lay)] = z.GetFilledPolysList(lay)

def contains(nodes, x, y, lay):
    p = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
    return any(n['layer'] == lay and lookup[lay].Contains(p, int(n['id'].split(':')[1])) for n in nodes)

main = report['clusters'][0]['nodes']
ground = b.GetNetcodeFromNetname('GND')
obstacles = [item.GetEffectiveShape(lay) for item in list(b.GetTracks()) + [p for f in b.GetFootprints() for p in f.Pads()]
             if item.GetNetCode() != ground for lay in (pcbnew.F_Cu, pcbnew.B_Cu) if item.IsOnLayer(lay)]
drills = [(item.GetPosition(), pcbnew.ToMM(item.GetDrill())) for item in b.GetTracks() if item.GetClass() == 'PCB_VIA']
drills += [(p.GetPosition(), max(pcbnew.ToMM(p.GetDrillSizeX()), pcbnew.ToMM(p.GetDrillSizeY())))
           for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSizeX() > 0]
result = []
for c in report['clusters'][1:]:
    pads = [p for n in c['nodes'] for p in n['pads']]
    if not pads:
        continue
    sites = []
    for n in c['nodes']:
        lay = n['layer']
        opposite = 'B.Cu' if lay == 'F.Cu' else 'F.Cu'
        xmin, ymin, xmax, ymax = n['bounds_mm']
        for ix in range(math.ceil(xmin * 10), math.floor(xmax * 10) + 1):
            for iy in range(math.ceil(ymin * 10), math.floor(ymax * 10) + 1):
                x, y = ix / 10, iy / 10
                if not contains([n], x, y, lay) or not contains(main, x, y, opposite):
                    continue
                via = pcbnew.PCB_VIA(b)
                via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                via.SetWidth(pcbnew.FromMM(.6)); via.SetDrill(pcbnew.FromMM(.3)); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                shape = via.GetEffectiveShape(pcbnew.F_Cu)
                if any(shape.Collide(obstacle, pcbnew.FromMM(.17)) for obstacle in obstacles):
                    continue
                if any(math.dist([x, y], xy(pos)) < .15 + diameter / 2 + .27 for pos, diameter in drills):
                    continue
                distance = min(math.dist([x, y], p['position_mm']) for p in pads)
                sites.append({'position_mm': [x, y], 'island_layer': lay, 'island_polygon': n['id'],
                              'pad_distance_mm': round(distance, 6)})
    sites.sort(key=lambda s: (s['pad_distance_mm'], s['position_mm']))
    result.append({'cluster': c['index'], 'pads': pads, 'candidate_sites': sites})
    print('cluster', c['index'], 'sites', len(sites), 'closest', sites[:5])
(OUT / 'via_sites.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
