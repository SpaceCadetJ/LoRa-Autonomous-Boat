"""Read only native footprint inspection; writes this packet's geometry record."""
from pathlib import Path
import hashlib,json
import pcbnew
P=Path(__file__).resolve().parent
paths=["inputs/C_2220_5750Metric.kicad_mod","footprints/LoRa_Power_Study.pretty/C_TDK_C5750X7S2A106K230KB.kicad_mod"]
def collect():
    entries=[]
    for rel in paths:
        p=P/rel;f=pcbnew.FootprintLoad(str(p.parent),p.stem);assert f
        pads=[]
        for pad in f.Pads():
            a=pad.GetPosition();s=pad.GetSize()
            pads.append(dict(number=pad.GetNumber(),x_mm=pcbnew.ToMM(a.x),y_mm=pcbnew.ToMM(a.y),length_mm=pcbnew.ToMM(s.x),width_mm=pcbnew.ToMM(s.y)))
        pads.sort(key=lambda x:x['number']);assert [x['number'] for x in pads]==['1','2']
        gap=round(pads[1]['x_mm']-pads[1]['length_mm']/2-pads[0]['x_mm']-pads[0]['length_mm']/2,6)
        match=4.1<=gap<=4.8 and all(1.2<=x['length_mm']<=1.4 and 4<=x['width_mm']<=5 for x in pads)
        entries.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pads=pads,gap_mm=gap,tdk_land_ranges_met=match))
    assert not entries[0]['tdk_land_ranges_met'] and entries[1]['tdk_land_ranges_met']
    return dict(schema=1,kicad_version=pcbnew.Version(),scope='Native library parsing and land dimensions only; no schematic ERC, PCB DRC, stencil, thermal, mechanical strain or assembly acceptance',entries=entries,proposed_courtyard_centerline_mm=[7.5,5.9],proposed_four_site_rectangle_area_mm2=177.0,whole_board_fit_verified=False,assembly_qualified=False)
if __name__=='__main__':
    (P/'native_geometry.json').write_text(json.dumps(collect(),indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Native footprint land inspection complete; no circuit/assembly qualification.')
