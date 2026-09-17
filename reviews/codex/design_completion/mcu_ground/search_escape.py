"""Local geometric search only; native DRC decides candidate acceptability."""
import collections
import hashlib
import json
import math
from pathlib import Path
import pcbnew

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'ground/candidate/LoRa_Boat_Controller_V2.kicad_pcb'
STEP = .10
CLEAR = .17
WIDTH = .15
MINX, MAXX, MINY, MAXY = 84, 98, 61, 75
LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]

def xy(p): return [pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)]
def vec(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def point(p): return [MINX + p[0]*STEP, MINY + p[1]*STEP]

def main():
    b = pcbnew.LoadBoard(str(SOURCE))
    code = b.GetNetcodeFromNetname('GND')
    obstacles = [[], []]
    report = json.loads((OUT.parent/'ground/ground_after.json').read_text())
    island = next(c for c in report['clusters'] if any(p['ref']=='U1' and p['pad']=='12' for n in c['nodes'] for p in n['pads']))
    main = report['clusters'][0]['nodes']
    polys = {b.GetLayerName(l): z.GetFilledPolysList(l) for z in b.Zones() if z.GetNetCode()==code and not z.GetIsRuleArea() for l in LAYERS if z.IsOnLayer(l)}
    def inside(nodes, pt, layer):
        lname = b.GetLayerName(LAYERS[layer])
        return any(n['layer']==lname and polys[lname].Contains(vec(*pt), int(n['id'].split(':')[1])) for n in nodes)
    items = list(b.GetTracks()) + [p for fp in b.GetFootprints() for p in fp.Pads()]
    descs=[]
    for item in items:
        box=item.GetBoundingBox()
        if pcbnew.ToMM(box.GetRight()) < MINX-1 or pcbnew.ToMM(box.GetLeft()) > MAXX+1 or pcbnew.ToMM(box.GetBottom()) < MINY-1 or pcbnew.ToMM(box.GetTop()) > MAXY+1: continue
        desc={'class':item.GetClass(),'net':item.GetNetname(),'uuid':item.m_Uuid.AsString()}
        if item.GetClass()=='PAD': desc.update(ref=item.GetParentFootprint().GetReference(), pad=item.GetNumber(), pos=xy(item.GetPosition()), size=xy(item.GetSize()), angle=item.GetOrientationDegrees())
        elif item.GetClass()=='PCB_VIA':desc.update(pos=xy(item.GetPosition()),width=pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu)),drill=pcbnew.ToMM(item.GetDrill()))
        else:desc.update(start=xy(item.GetStart()),end=xy(item.GetEnd()),width=pcbnew.ToMM(item.GetWidth()))
        desc['layers']=[i for i,l in enumerate(LAYERS) if item.IsOnLayer(l)]
        descs.append(desc)
        if item.GetNetCode()!=code:
            for i,l in enumerate(LAYERS):
                if item.IsOnLayer(l): obstacles[i].append((item.GetEffectiveShape(l),desc))
    (OUT/'local_geometry.json').write_text(json.dumps({'bounds':[MINX,MINY,MAXX,MAXY],'items':descs,'island':island},indent=2))
    nx,ny=round((MAXX-MINX)/STEP)+1,round((MAXY-MINY)/STEP)+1
    valid=set(); goals=set(); starts=[]
    testvia=pcbnew.PCB_VIA(b); testvia.SetWidth(pcbnew.FromMM(WIDTH));testvia.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    for layer in range(2):
        for x in range(nx):
            for y in range(ny):
                p=(x,y,layer); pt=point(p)
                testvia.SetPosition(vec(*pt));circle=testvia.GetEffectiveShape(pcbnew.F_Cu)
                if any(circle.Collide(s,pcbnew.FromMM(CLEAR)) for s,d in obstacles[layer]):continue
                valid.add(p)
                if inside(main,pt,layer):goals.add(p)
                elif inside(island['nodes'],pt,layer):starts.append(p)
    print('valid',len(valid),'goals',len(goals),'starts',len(starts),flush=True)
    queue=collections.deque(starts); parents={p:None for p in starts}; found=None
    while queue:
        p=queue.popleft()
        if p in goals:found=p;break
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            q=(p[0]+dx,p[1]+dy,p[2])
            if q in parents or q not in valid: continue
            testtrack=pcbnew.PCB_TRACK(b);testtrack.SetStart(vec(*point(p)));testtrack.SetEnd(vec(*point(q)));testtrack.SetWidth(pcbnew.FromMM(WIDTH));testtrack.SetLayer(LAYERS[p[2]])
            seg=testtrack.GetEffectiveShape(LAYERS[p[2]])
            if any(seg.Collide(s,pcbnew.FromMM(CLEAR)) for s,d in obstacles[p[2]]):continue
            parents[q]=p;queue.append(q)
    path=[]
    while found is not None:path.append({'position_mm':point(found),'layer':b.GetLayerName(LAYERS[found[2]])});found=parents[found]
    result={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'grid_mm':STEP,'clearance_mm':CLEAR,'width_mm':WIDTH,'bounds_mm':[MINX,MINY,MAXX,MAXY],'valid_count':len(valid),'visited_count':len(parents),'starts_count':len(starts),'path':path[::-1]}
    (OUT/'escape_search.json').write_text(json.dumps(result,indent=2)+'\n')
    print('path',len(path),'visited',len(parents),flush=True)

if __name__=='__main__':main()
