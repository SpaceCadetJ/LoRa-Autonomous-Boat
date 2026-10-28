"""Native and portable C11 land inspection; no board is created or accepted."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,math
P=Path(__file__).resolve().parent; ROOT=P.parents[2]
NAME='CP_Panasonic_FK_D_6.3x5.8';LAND=P/('source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/'+NAME+'.kicad_mod')
PARSER=ROOT/'reviews/codex/actuator_latch/inspect_packages.py'
spec=importlib.util.spec_from_file_location('prior_geometry_parser',PARSER);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
sexpr,child,require=prior.sexpr,prior.child,prior.require
LAYERS=['F.Cu','F.Mask','F.Paste','F.SilkS','F.Fab','F.CrtYd']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x):return round(float(x),6)
def pad(n,x,y,sx,sy,angle,layers):return {'number':str(n),'x_mm':num(x),'y_mm':num(y),'size_x_mm':num(sx),'size_y_mm':num(sy),'rotation_deg':num(angle),'layers':sorted(layers),'type':'smd','shape':'rect'}
def line(layer,a,b,w):
    a,b=sorted([[num(x) for x in a],[num(x) for x in b]])
    return {'shape':'line','layer':layer,'start_mm':a,'end_mm':b,'width_mm':num(w)}
def circle(layer,c,e,w):return {'shape':'circle','layer':layer,'center_mm':[num(x) for x in c],'radius_mm':num(math.dist(c,e)),'width_mm':num(w)}
def order(d):return {'pads':sorted(d['pads'],key=lambda x:x['number']),'graphics':sorted(d['graphics'],key=lambda x:json.dumps(x,sort_keys=True))}
def portable(text=None):
    tree=sexpr(LAND.read_text(encoding='utf-8') if text is None else text);require(tree[:2]==['footprint',NAME],'Wrong footprint identity');require(child(tree,'attr')[1:]==['smd'],'Wrong attributes')
    d={'pads':[],'graphics':[]}
    for i in tree:
        if not isinstance(i,list):continue
        if i[0]=='pad':
            require(i[2:4]==['smd','rect'],'Wrong pad type/shape');at=child(i,'at');size=child(i,'size')
            d['pads'].append(pad(i[1],*at[1:3],*size[1:],at[3] if len(at)>3 else 0,child(i,'layers')[1:]))
            require(set(j[0] for j in i if isinstance(j,list))=={'at','size','layers'},'Unexpected pad override')
        elif i[0]=='fp_line':d['graphics'].append(line(child(i,'layer')[1],child(i,'start')[1:],child(i,'end')[1:],child(child(i,'stroke'),'width')[1]))
        elif i[0]=='fp_circle':d['graphics'].append(circle(child(i,'layer')[1],list(map(float,child(i,'center')[1:])),list(map(float,child(i,'end')[1:])),child(child(i,'stroke'),'width')[1]))
        else:require(i[0] in {'version','generator','layer','descr','tags','attr','property'},'Unexpected footprint feature: '+i[0])
    return order(d)
def expected():
    d={'pads':[pad(n,x,0,3.2,1.6,0,['F.Cu','F.Paste','F.Mask']) for n,x in [('1',-2.5),('2',2.5)]],'graphics':[circle('F.Fab',[0,0],[3.15,0],.1)]}
    groups=[('F.Fab',.1,[((-3.3,-3.3),(3.3,-3.3)),((3.3,-3.3),(3.3,3.3)),((3.3,3.3),(-3.3,3.3)),((-3.3,3.3),(-3.3,-3.3)),((-2.4,-1.5),(-1.6,-1.5)),((-2,-1.9),(-2,-1.1))]),
      ('F.SilkS',.12,[((-3.45,-1.1),(-3.45,-3.45)),((-3.45,-3.45),(3.45,-3.45)),((3.45,-3.45),(3.45,-1.1)),((3.45,1.1),(3.45,3.45)),((3.45,3.45),(-3.45,3.45)),((-3.45,3.45),(-3.45,1.1)),((-4.8,-1.5),(-4,-1.5)),((-4.4,-1.9),(-4.4,-1.1))]),
      ('F.CrtYd',.05,[((-5.1,-3.8),(4.6,-3.8)),((4.6,-3.8),(4.6,3.8)),((4.6,3.8),(-5.1,3.8)),((-5.1,3.8),(-5.1,-3.8))])]
    for layer,w,pairs in groups:d['graphics'] += [line(layer,a,b,w) for a,b in pairs]
    return order(d)
def validate(d):
    require(d==expected(),'C11 land, polarity artwork, nominal body or proposed courtyard differs')
    return {'pads':2,'manufacturer_recommended_land_dimensions_match':True,'pad1':'positive VSERVO','pad2':'negative GND','pad_centers_x_mm':[-2.5,2.5],'pad_size_mm':[3.2,1.6],'inner_gap_mm':1.8,'outer_span_mm':8.2,
      'nominal_body_diameter_mm':6.3,'maximum_body_diameter_mm':6.8,'nominal_base_xy_mm':[6.6,6.6],'maximum_base_xy_mm':[6.8,6.8],'maximum_terminal_span_mm':7.8,'nominal_height_mm':5.8,'maximum_height_mm':6.1,
      'proposal_only':['courtyard','silkscreen','fabrication artwork','default mask and paste openings'],
      'assembly_qualified':False,'stencil_qualified':False,'board_fit_verified':False,'pcb_drc_performed':False,'reservoir_qualified':False,'manufacturer_acceptance':False}
def hashes():return {p.relative_to(ROOT).as_posix():sha(p) for p in [LAND,P/'expected_contract.json',PARSER,Path(__file__)]}
def capture():
    import pcbnew
    h=hashes();fp=pcbnew.FootprintLoad(str(LAND.parent),NAME);require(fp is not None,'Native load failed')
    layers={getattr(pcbnew,n.replace('.','_')):n for n in LAYERS};d={'pads':[],'graphics':[]}
    for p in fp.Pads():
        require(p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD and p.GetShape()==pcbnew.PAD_SHAPE_RECT,'Unexpected native pad type')
        a,s=p.GetPosition(),p.GetSize();d['pads'].append(pad(p.GetNumber(),pcbnew.ToMM(a.x),pcbnew.ToMM(a.y),pcbnew.ToMM(s.x),pcbnew.ToMM(s.y),p.GetOrientationDegrees(),[layers[l] for l in p.GetLayerSet().Seq()]))
    for item in fp.GraphicalItems():
        if isinstance(item,pcbnew.PCB_TEXT):continue
        require(isinstance(item,pcbnew.PCB_SHAPE),'Unexpected native graphic');a,b=item.GetStart(),item.GetEnd();a=[pcbnew.ToMM(a.x),pcbnew.ToMM(a.y)];b=[pcbnew.ToMM(b.x),pcbnew.ToMM(b.y)]
        shape=item.GetShape();require(shape in [pcbnew.SHAPE_T_SEGMENT,pcbnew.SHAPE_T_CIRCLE],'Unexpected native graphic kind')
        d['graphics'].append((line if shape==pcbnew.SHAPE_T_SEGMENT else circle)(layers[item.GetLayer()],a,b,pcbnew.ToMM(item.GetWidth())))
    d=order(d);require(d==portable(),'Native/portable geometry mismatch');v=validate(d);require(hashes()==h,'Inputs changed during native inspection')
    result={'revision':'VSERVO-01','captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':pcbnew.Version(),'input_sha256':h,'native_geometry':d,'dimensional_check':v,'board_created':False,'source_modified':False}
    (P/'geometry_native.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print('PASS: native C11 footprint:2 pads,18 lines,1 circle; manufacturer/assembly acceptance held')
def check():
    r=json.loads((P/'geometry_native.json').read_text(encoding='utf-8'));d=portable();require(r['input_sha256']==hashes(),'Geometry input hashes changed');require(r['native_geometry']==d,'Geometry record differs');require(r['dimensional_check']==validate(d),'Geometry claims differ');require(r['board_created'] is False and r['source_modified'] is False,'Unexpected mutation claim');return r['dimensional_check']
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    if args.check:check();print('PASS: captured C11 native/portable geometry')
    else:capture()
