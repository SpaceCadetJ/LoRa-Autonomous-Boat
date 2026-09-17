"""Bounded search for one short bridge from the isolated U1 pad-12 cluster."""
import json
import math
import pcbnew
from inspect_ground import BOARD, OUT, inspect

b = pcbnew.LoadBoard(str(BOARD))
report = inspect()
code = b.GetNetcodeFromNetname('GND')
main = report['clusters'][0]['nodes']
cluster = next(c for c in report['clusters'] if any(p['ref'] == 'U1' and p['pad'] == '12' for n in c['nodes'] for p in n['pads']))
polys = {b.GetLayerName(lay): z.GetFilledPolysList(lay) for z in b.Zones() if z.GetNetCode() == code and not z.GetIsRuleArea()
         for lay in (pcbnew.F_Cu, pcbnew.B_Cu) if z.IsOnLayer(lay)}
def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def main_at(x, y, layer):
    return any(n['layer'] == layer and polys[layer].Contains(vec(x, y), int(n['id'].split(':')[1])) for n in main)

other = {lay: [] for lay in (pcbnew.F_Cu, pcbnew.B_Cu)}
for item in list(b.GetTracks()) + [p for fp in b.GetFootprints() for p in fp.Pads()]:
    if item.GetNetCode() != code:
        for lay in other:
            if item.IsOnLayer(lay):
                other[lay].append(item.GetEffectiveShape(lay))
drills = [(item.GetPosition(), pcbnew.ToMM(item.GetDrill())) for item in b.GetTracks() if item.GetClass() == 'PCB_VIA']
drills += [(p.GetPosition(), max(pcbnew.ToMM(p.GetDrillSizeX()), pcbnew.ToMM(p.GetDrillSizeY())))
           for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSizeX() > 0]

sources = []
for n in cluster['nodes']:
    lay = pcbnew.F_Cu if n['layer'] == 'F.Cu' else pcbnew.B_Cu
    for p in n['pads']:
        sources.append((p['position_mm'], lay, p['ref'] + '.' + p['pad']))
    for via in n['vias']:
        sources.append((via['position_mm'], lay, via['uuid']))

solutions = []
for start, lay, label in sources:
    layer = b.GetLayerName(lay)
    for ix in range(math.ceil((start[0] - 3) * 10), math.floor((start[0] + 3) * 10) + 1):
        for iy in range(math.ceil((start[1] - 3) * 10), math.floor((start[1] + 3) * 10) + 1):
            end = [ix / 10, iy / 10]
            length = math.dist(start, end)
            if length < .3 or length > 3:
                continue
            needs_via = not main_at(*end, layer)
            if needs_via:
                if not main_at(*end, 'B.Cu' if layer == 'F.Cu' else 'F.Cu'):
                    continue
                via = pcbnew.PCB_VIA(b)
                via.SetPosition(vec(*end)); via.SetWidth(pcbnew.FromMM(.6)); via.SetDrill(pcbnew.FromMM(.3)); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via_shape = via.GetEffectiveShape(pcbnew.F_Cu)
                if any(via_shape.Collide(shape, pcbnew.FromMM(.17)) for shapes in other.values() for shape in shapes):
                    continue
                if any(math.dist(end, [pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)]) < .15 + diameter / 2 + .27 for pos, diameter in drills):
                    continue
            tr = pcbnew.PCB_TRACK(b)
            tr.SetStart(vec(*start)); tr.SetEnd(vec(*end)); tr.SetLayer(lay); tr.SetWidth(pcbnew.FromMM(.25)); tr.SetNetCode(code)
            shape = tr.GetEffectiveShape(lay)
            if any(shape.Collide(obstacle, pcbnew.FromMM(.17)) for obstacle in other[lay]):
                continue
            solutions.append({'start_mm': start, 'end_mm': end, 'layer': layer, 'length_mm': round(length, 6),
                              'width_mm': .25, 'source': label, 'needs_via': needs_via})
solutions.sort(key=lambda x: (x['length_mm'], x['layer'], x['end_mm']))
(OUT / 'bridge_sites.json').write_text(json.dumps(solutions, indent=2) + '\n', encoding='utf-8')
print('clean bridges:', len(solutions), 'closest:', solutions[:5])
