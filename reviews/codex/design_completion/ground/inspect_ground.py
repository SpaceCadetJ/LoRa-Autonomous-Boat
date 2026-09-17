"""Read-only geometric localization of filled GND polygons; use KiCad Python 9."""
from pathlib import Path
import hashlib
import json
import pcbnew

ROOT = Path(__file__).resolve().parents[4]
BOARD = ROOT / 'reviews/codex/publication/native-review/inputs/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb'
OUT = Path(__file__).resolve().parent

def xy(v):
    return [round(pcbnew.ToMM(v.x), 6), round(pcbnew.ToMM(v.y), 6)]

def inspect(path=BOARD):
    board = pcbnew.LoadBoard(str(path))
    board.BuildConnectivity()
    code = board.GetNetcodeFromNetname('GND')
    polygons = {}
    nodes = {}
    parent = {}
    def find(x):
        if parent.setdefault(x, x) != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(items):
        for item in items[1:]:
            parent[find(item)] = find(items[0])
    for zone in board.Zones():
        if zone.GetNetCode() != code or zone.GetIsRuleArea():
            continue
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not zone.IsOnLayer(layer):
                continue
            poly = zone.GetFilledPolysList(layer)
            layer_name = board.GetLayerName(layer)
            for index in range(poly.OutlineCount()):
                key = (zone.m_Uuid.AsString(), layer, index)
                outline = poly.Outline(index)
                vertices = [xy(outline.CPoint(n)) for n in range(outline.PointCount())]
                xs, ys = zip(*vertices)
                nodes[key] = {'id': f'{layer_name}:{index}', 'zone_uuid': key[0], 'layer': layer_name,
                              'area_mm2': round(abs(outline.Area()) / 1e12, 6),
                              'bounds_mm': [min(xs), min(ys), max(xs), max(ys)], 'pads': [], 'vias': [],
                              'outline_mm': vertices}
                polygons[key] = poly
                find(key)
    def containing(pos, layers):
        return [key for key, poly in polygons.items() if key[1] in layers and poly.Contains(pos, key[2])]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != code:
                continue
            layers = [layer for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(layer)]
            contained = containing(pad.GetPosition(), layers)
            desc = {'ref': fp.GetReference(), 'pad': pad.GetNumber(), 'position_mm': xy(pad.GetPosition()),
                    'uuid': pad.m_Uuid.AsString()}
            for key in contained:
                nodes[key]['pads'].append(desc)
            union(contained)
    for track in board.GetTracks():
        if track.GetNetCode() != code:
            continue
        if track.GetClass() == 'PCB_VIA':
            contained = containing(track.GetPosition(), [pcbnew.F_Cu, pcbnew.B_Cu])
            desc = {'position_mm': xy(track.GetPosition()), 'uuid': track.m_Uuid.AsString()}
            for key in contained:
                nodes[key]['vias'].append(desc)
            union(contained)
        else:
            union(containing(track.GetStart(), [track.GetLayer()]) + containing(track.GetEnd(), [track.GetLayer()]))
    groups = {}
    for key in nodes:
        groups.setdefault(find(key), []).append(nodes[key])
    clusters = sorted(groups.values(), key=lambda group: sum(n['area_mm2'] for n in group), reverse=True)
    report = {'board': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'native_unconnected_count': board.GetConnectivity().GetUnconnectedCount(True),
              'method': 'Filled polygon center-containment joined by through vias, plated pads and GND track endpoints. '
                        'Geometric localization only; native DRC is authoritative. Polygon areas omit hole subtraction.',
              'clusters': [{'index': index, 'area_mm2': round(sum(n['area_mm2'] for n in group), 6),
                            'nodes': group} for index, group in enumerate(clusters)]}
    return report

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', type=Path, default=BOARD)
    parser.add_argument('--output', type=Path, default=OUT / 'ground_before.json')
    args = parser.parse_args()
    report = inspect(args.board.resolve())
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('native unconnected:', report['native_unconnected_count'])
    for cluster in report['clusters']:
        if cluster['index'] == 0:
            print('main:', len(cluster['nodes']), 'polygons; area', cluster['area_mm2'])
        else:
            print(json.dumps({**cluster, 'nodes': [{k: v for k, v in n.items() if k != 'outline_mm'} for n in cluster['nodes']]}))
