"""Find one local edge-to-main bridge; no rerouting or rule changes."""
import json
import math
import pcbnew
from inspect_ground import BOARD, OUT, inspect, xy

b = pcbnew.LoadBoard(str(BOARD))
report = inspect()
code = b.GetNetcodeFromNetname('GND')
main = report['clusters'][0]['nodes']
cluster = next(c for c in report['clusters'] if any(p['ref'] == 'U1' and p['pad'] == '12' for n in c['nodes'] for p in n['pads']))
polys = {b.GetLayerName(lay): z.GetFilledPolysList(lay) for z in b.Zones() if z.GetNetCode() == code and not z.GetIsRuleArea()
         for lay in (pcbnew.F_Cu, pcbnew.B_Cu) if z.IsOnLayer(lay)}
def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def inside(nodes, point, layer):
    return any(n['layer'] == layer and polys[layer].Contains(vec(*point), int(n['id'].split(':')[1])) for n in nodes)
other = {lay: [] for lay in (pcbnew.F_Cu, pcbnew.B_Cu)}
for item in list(b.GetTracks()) + [p for fp in b.GetFootprints() for p in fp.Pads()]:
    if item.GetNetCode() != code:
        for lay in other:
            if item.IsOnLayer(lay):
                other[lay].append(item.GetEffectiveShape(lay))
drills = [(item.GetPosition(), pcbnew.ToMM(item.GetDrill())) for item in b.GetTracks() if item.GetClass() == 'PCB_VIA']
drills += [(p.GetPosition(), max(pcbnew.ToMM(p.GetDrillSizeX()), pcbnew.ToMM(p.GetDrillSizeY())))
           for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSizeX() > 0]
solutions = []
for lay in other:
    layer = b.GetLayerName(lay)
    other_layer = 'B.Cu' if layer == 'F.Cu' else 'F.Cu'
    nodes = [n for n in cluster['nodes'] if n['layer'] == layer]
    xmin = min(n['bounds_mm'][0] for n in nodes); ymin = min(n['bounds_mm'][1] for n in nodes)
    xmax = max(n['bounds_mm'][2] for n in nodes); ymax = max(n['bounds_mm'][3] for n in nodes)
    starts = [[ix / 10, iy / 10] for ix in range(math.floor(xmin * 10), math.ceil(xmax * 10) + 1)
              for iy in range(math.floor(ymin * 10), math.ceil(ymax * 10) + 1)
              if inside(nodes, [ix / 10, iy / 10], layer)]
    for ix in range(math.floor((xmin - 1.5) * 10), math.ceil((xmax + 1.5) * 10) + 1):
        for iy in range(math.floor((ymin - 1.5) * 10), math.ceil((ymax + 1.5) * 10) + 1):
            end = [ix / 10, iy / 10]
            if not inside(main, end, other_layer) or inside(nodes, end, layer):
                continue
            nearby = sorted((s for s in starts if math.dist(s, end) <= 1.5), key=lambda s: math.dist(s, end))
            if not nearby:
                continue
            via = pcbnew.PCB_VIA(b)
            via.SetPosition(vec(*end)); via.SetWidth(pcbnew.FromMM(.6)); via.SetDrill(pcbnew.FromMM(.3)); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via_shape = via.GetEffectiveShape(pcbnew.F_Cu)
            if any(via_shape.Collide(shape, pcbnew.FromMM(.17)) for shapes in other.values() for shape in shapes):
                continue
            if any(math.dist(end, xy(pos)) < .15 + diameter / 2 + .27 for pos, diameter in drills):
                continue
            for start in nearby:
                tr = pcbnew.PCB_TRACK(b)
                tr.SetStart(vec(*start)); tr.SetEnd(vec(*end)); tr.SetLayer(lay); tr.SetWidth(pcbnew.FromMM(.15)); tr.SetNetCode(code)
                shape = tr.GetEffectiveShape(lay)
                if any(shape.Collide(obstacle, pcbnew.FromMM(.17)) for obstacle in other[lay]):
                    continue
                solutions.append({'start_mm': start, 'end_mm': end, 'layer': layer,
                                  'length_mm': round(math.dist(start, end), 6), 'width_mm': .15,
                                  'needs_via': True, 'source': 'inside pre-existing U1.12 island copper'})
                break
solutions.sort(key=lambda s: (s['length_mm'], s['layer'], s['end_mm']))
(OUT / 'edge_bridge_sites.json').write_text(json.dumps(solutions, indent=2) + '\n', encoding='utf-8')
print('edge bridges:', len(solutions), 'closest:', solutions[:8])
