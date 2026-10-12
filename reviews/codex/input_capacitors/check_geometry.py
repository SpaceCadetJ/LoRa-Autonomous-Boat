"""Portable independent pad/courtyard parse checked against captured native dimensions."""
from pathlib import Path
import importlib.util,json,hashlib,math
P=Path(__file__).resolve().parent
S=P.parent/'input_stage/inputs/hardware/kicad/tools/kicad_sym.py'
s=importlib.util.spec_from_file_location('captured_sexp',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def child(node,key):return next(x for x in node if isinstance(x,list) and x and x[0]==key)
def check():
    record=json.loads((P/'native_geometry.json').read_text())
    for e in record['entries']:
        p=P/e['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']
        root=m.parse(p.read_text())[0];pads=[]
        for pad in (x for x in root if isinstance(x,list) and x[0]=='pad'):
            at=child(pad,'at');sz=child(pad,'size')
            assert pad[2]=='smd' and len(at)==3
            pads.append(dict(number=str(pad[1]),x_mm=float(at[1]),y_mm=float(at[2]),length_mm=float(sz[1]),width_mm=float(sz[2])))
        pads.sort(key=lambda x:x['number']);assert pads==e['pads']
        gap=round(pads[1]['x_mm']-pads[1]['length_mm']/2-pads[0]['x_mm']-pads[0]['length_mm']/2,6)
        assert gap==e['gap_mm']
        assert e['tdk_land_ranges_met']==(4.1<=gap<=4.8 and all(1.2<=x['length_mm']<=1.4 and 4<=x['width_mm']<=5 for x in pads))
        if e['tdk_land_ranges_met']:
            rect=next(x for x in root if isinstance(x,list) and x[0]=='fp_rect' and child(x,'layer')[1]=='F.CrtYd')
            a=child(rect,'start');b=child(rect,'end');bounds=list(map(float,[a[1],a[2],b[1],b[2]]))
            assert bounds==[-3.75,-2.95,3.75,2.95]
            assert bounds[0]<=-3.05-.25 and bounds[2]>=3.05+.25 and bounds[1]<=-2.7-.25 and bounds[3]>=2.7+.25
            for x in pads:
                assert bounds[0]<=x['x_mm']-x['length_mm']/2-.25 and bounds[2]>=x['x_mm']+x['length_mm']/2+.25
            assert math.isclose((bounds[2]-bounds[0])*(bounds[3]-bounds[1])*4,record['proposed_four_site_rectangle_area_mm2'])
    assert record['assembly_qualified'] is False and record['whole_board_fit_verified'] is False
    return True
if __name__=='__main__':
    check();print('PASS native/portable footprint dimensions and source hashes; no assembly acceptance')
