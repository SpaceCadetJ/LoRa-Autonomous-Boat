#!/usr/bin/env python3
"""route_v2.py - (KiCad python) autoroute the generated V2 board with freerouting and pull the result back into KiCad.
  "C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad_v2/tools/route_v2.py dsn|route|import|all [--passes N] [--timeout S]
  dsn    : export hardware/kicad_v2/_build/LoRa_Boat_Controller_V2.dsn (Specctra) from the generated (unrouted) board.
           --gnd-plane bcu (default) keeps only the B.Cu GND pour as a Specctra plane, so freerouting drops a via next to every
           top-side GND pad instead of assuming the F.Cu pour reaches it (it cannot inside the LQFP/QFN fan-out); both / none also accepted
  route  : run freerouting on the DSN -> _build/LoRa_Boat_Controller_V2.ses  (needs Java 21 and the freerouting 2.1.0 jar,
           default %LOCALAPPDATA%/freerouting/freerouting-2.1.0.jar, override with FREEROUTING_JAR;
           download: https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar)
  import : import the SES into the board, refill the GND pours, save hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb
  all    : dsn + route + import
Re-running gen_v2.py regenerates the unrouted board; run this again afterwards (the routing is not kept in the generator).
"""
import os, sys, time, subprocess, argparse, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
import v2_design as D
V2DIR = os.path.join(ROOT, 'hardware', 'kicad_v2')
BUILD = os.path.join(V2DIR, '_build')
PCB = os.path.join(V2DIR, D.PROJ + '.kicad_pcb')
DSN = os.path.join(BUILD, D.PROJ + '.dsn')
SES = os.path.join(BUILD, D.PROJ + '.ses')
KICAD_CLI = os.path.join(os.environ.get('KICAD_BIN', 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin'), 'kicad-cli.exe')
JAR = os.environ.get('FREEROUTING_JAR') or os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'freerouting', 'freerouting-2.1.0.jar')

def strip_planes(keep):
    """Remove '(plane GND (polygon <layer> ...))' blocks for layers not in keep from the exported DSN."""
    lines = open(DSN, encoding='utf-8').read().splitlines(); out = []; skip = False; removed = 0
    for ln in lines:
        st = ln.strip()
        if st.startswith('(plane ') and not any(('(polygon ' + lay) in st for lay in keep):
            skip = True; removed += 1
        if skip:
            if st.endswith('))'): skip = False
            continue
        out.append(ln)
    open(DSN, 'w', encoding='utf-8').write(chr(10).join(out) + chr(10))
    print('planes removed from DSN:', removed, '(kept:', ', '.join(keep) or 'none', ')')

def export_dsn(gnd_plane='bcu'):
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    assert b is not None, 'board failed to load: ' + PCB
    os.makedirs(BUILD, exist_ok=True)
    ok = pcbnew.ExportSpecctraDSN(b, DSN)
    if ok and gnd_plane != 'both':
        strip_planes({'bcu': ['B.Cu'], 'none': []}[gnd_plane])
    print('DSN export', 'ok' if ok else 'FAILED', DSN, os.path.getsize(DSN) if os.path.exists(DSN) else 0, 'bytes')
    return ok

def route(passes, timeout):
    assert os.path.exists(JAR), 'freerouting jar not found: ' + JAR
    if os.path.exists(SES):
        os.remove(SES)
    log = os.path.join(BUILD, 'freerouting.log')
    cmd = ['java', '-jar', JAR, '-de', DSN, '-do', SES, '-mp', str(passes), '-mt', str(max(1, (os.cpu_count() or 2) - 1)), '-oit', '0.5', '-da']
    print('running:', ' '.join(cmd)); t0 = time.time()
    with open(log, 'w') as lf:
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=BUILD)
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill(); rc = 'timeout'
    print('freerouting exit', rc, 'after %.0f s' % (time.time() - t0), '; SES', os.path.getsize(SES) if os.path.exists(SES) else 'MISSING', '; log', log)
    return os.path.exists(SES) and os.path.getsize(SES) > 1000


def _pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def _seg_seg(a, b, c, d):
    def orient(p, q, r): return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if (orient(a, b, c) > 0) != (orient(a, b, d) > 0) and (orient(c, d, a) > 0) != (orient(c, d, b) > 0):
        return 0.0
    return min(_pt_seg(c[0], c[1], a[0], a[1], b[0], b[1]), _pt_seg(d[0], d[1], a[0], a[1], b[0], b[1]),
               _pt_seg(a[0], a[1], c[0], c[1], d[0], d[1]), _pt_seg(b[0], b[1], c[0], c[1], d[0], d[1]))

def unconnected_gnd_pads(b):
    """(ref, pad number) of GND pads that kicad-cli DRC reports as unconnected (the python connectivity API does not expose
    zone-fill connections per pad, so the CLI report is the reliable source)."""
    import pcbnew
    tmp = os.path.join(BUILD, 'stitch_tmp.kicad_pcb'); rpt = os.path.join(BUILD, 'stitch_drc.rpt')
    pcbnew.SaveBoard(tmp, b)
    subprocess.run([KICAD_CLI, 'pcb', 'drc', '--severity-error', '-o', rpt, tmp], capture_output=True)
    pads = set(); head = ''
    for ln in open(rpt, encoding='utf-8', errors='replace'):
        if ln.startswith('['):
            head = ln.split(':', 1)[0]
        elif head == '[unconnected_items]' and '[GND]' in ln and ' of ' in ln and ('Pad ' in ln or 'PTH pad ' in ln):
            body = ln.split('): ', 1)[1] if '): ' in ln else ln
            words = body.split()
            num = words[2] if words[0] == 'PTH' else words[1]
            ref = body.split(' of ', 1)[1].split()[0]
            pads.add((ref, num))
    return sorted(pads)

def stitch_gnd(b):
    """Freerouting assumes every GND pad sits on the B.Cu plane; pads fenced in by tracks stay unreached by the pours.
    For each such pad add a 0.25 mm GND track to a 0.6/0.3 via at the nearest spot that clears every other-net item by the
    Default clearance (geometric pre-check), sits inside a filled GND pour, and lowers the board's unconnected count after a refill."""
    import pcbnew
    mm = pcbnew.ToMM; netcode = b.GetNetcodeFromNetname('GND'); ox, oy = D.BOARD_ORIGIN
    CLR, VIA_R, TW = 0.15, 0.3, 0.25
    tracks = [(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2, t.GetLayer(), t.GetNetCode())
              for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    vias = [(mm(v.GetPosition().x), mm(v.GetPosition().y), mm(v.GetWidth(pcbnew.F_Cu)) / 2, v.GetNetCode()) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append((mm(p.GetPosition().x), mm(p.GetPosition().y), math.hypot(mm(bb.GetWidth()), mm(bb.GetHeight())) / 2, p.GetNetCode(),
                         p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD, p.GetLayer(), mm(p.GetDrillSizeX()) / 2))
    def via_ok(x, y):
        for (ax, ay, bx, by, hw, lay, net) in tracks:
            if net != netcode and _pt_seg(x, y, ax, ay, bx, by) < VIA_R + CLR + hw + 0.02: return False
        for (vx, vy, vr, net) in vias:
            if math.hypot(x - vx, y - vy) < VIA_R + vr + (CLR if net != netcode else 0.3) + 0.02: return False
        for (px, py, pr, net, tht, lay, dr) in pads:
            dist = math.hypot(x - px, y - py)
            if net != netcode and dist < VIA_R + CLR + pr + 0.02: return False
            if tht and dist < VIA_R + dr + 0.3: return False
        return True
    def track_ok(x0, y0, x1, y1, lay):
        for (ax, ay, bx, by, hw, tl, net) in tracks:
            if net != netcode and tl == lay and _seg_seg((x0, y0), (x1, y1), (ax, ay), (bx, by)) < TW / 2 + CLR + hw + 0.02: return False
        for (vx, vy, vr, net) in vias:
            if net != netcode and _pt_seg(vx, vy, x0, y0, x1, y1) < TW / 2 + CLR + vr + 0.02: return False
        for (px, py, pr, net, tht, pl, dr) in pads:
            if net != netcode and (tht or pl == lay) and _pt_seg(px, py, x0, y0, x1, y1) < TW / 2 + CLR + pr + 0.02: return False
        return True
    pours = [z for z in b.Zones() if z.GetNetCode() == netcode and not z.GetIsRuleArea()]
    def in_pour(x, y, lay):
        pt = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
        return any(z.IsOnLayer(lay) and z.GetFilledPolysList(lay).Contains(pt) for z in pours)
    b.BuildConnectivity(); before = b.GetConnectivity().GetUnconnectedCount(True)
    todo = unconnected_gnd_pads(b) if before else []
    print('unconnected connections:', before, '; GND pads not reached by the pours:', todo)
    for ref, num in todo:
        fp = b.FindFootprintByReference(ref); pad = [q for q in fp.Pads() if q.GetNumber() == num][0]
        cx, cy = mm(pad.GetPosition().x), mm(pad.GetPosition().y); done = False; tried = 0
        layers = (pcbnew.B_Cu, pcbnew.F_Cu) if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD else (pad.GetLayer(),)
        for d in [1.4 + 0.2 * i for i in range(12)]:
            for k in range(24):
                ang = k * math.pi / 12; x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
                if not (0.8 <= x - ox <= D.BOARD_W - 0.8 and 0.8 <= y - oy <= D.BOARD_H - 0.8) or not via_ok(x, y):
                    continue
                if not (in_pour(x, y, pcbnew.B_Cu) or in_pour(x, y, pcbnew.F_Cu)):
                    continue
                for lay in layers:
                    if not track_ok(cx, cy, x, y, lay):
                        continue
                    via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))); via.SetViaType(pcbnew.VIATYPE_THROUGH)
                    via.SetDrill(pcbnew.FromMM(0.3)); via.SetWidth(pcbnew.FromMM(2 * VIA_R)); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNetCode(netcode)
                    tr = pcbnew.PCB_TRACK(b); tr.SetStart(pad.GetPosition()); tr.SetEnd(via.GetPosition()); tr.SetWidth(pcbnew.FromMM(TW)); tr.SetLayer(lay); tr.SetNetCode(netcode)
                    b.Add(via); b.Add(tr); tried += 1
                    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity()
                    after = b.GetConnectivity().GetUnconnectedCount(True)
                    if after < before:
                        before = after
                        tracks.append((cx, cy, x, y, TW / 2, lay, netcode)); vias.append((x, y, VIA_R, netcode))
                        print(f'  {ref}-{num}: stitched, via {d:.1f} mm at {k * 15} deg on {pcbnew.BOARD.GetStandardLayerName(lay)} (fills tried: {tried}); unconnected now {after}')
                        done = True; break
                    b.Remove(via); b.Remove(tr)
                    if tried >= 12: break
                if done or tried >= 12: break
            if done or tried >= 12: break
        if not done:
            print(f'  {ref}-{num}: no clean stitch position found ({tried} fills tried)')
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity()
    print('unconnected connections after stitching:', b.GetConnectivity().GetUnconnectedCount(True))

def import_ses():
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    assert b is not None
    ok = pcbnew.ImportSpecctraSES(b, SES)
    print('SES import', 'ok' if ok else 'FAILED')
    if not ok:
        return False
    filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
    b.BuildConnectivity()
    stitch_gnd(b)
    ntracks = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK'); nvias = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
    unrouted = b.GetConnectivity().GetUnconnectedCount(True)
    pcbnew.SaveBoard(PCB, b)
    print('saved', PCB, ':', ntracks, 'track segments,', nvias, 'vias, unrouted connections:', unrouted)
    return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('step', choices=['dsn', 'route', 'import', 'all'])
    ap.add_argument('--passes', type=int, default=40); ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('--gnd-plane', choices=['bcu', 'both', 'none'], default='bcu')
    a = ap.parse_args()
    if a.step in ('dsn', 'all'): export_dsn(a.gnd_plane)
    if a.step in ('route', 'all'):
        if not route(a.passes, a.timeout): sys.exit(1)
    if a.step in ('import', 'all'):
        if not import_ses(): sys.exit(1)
