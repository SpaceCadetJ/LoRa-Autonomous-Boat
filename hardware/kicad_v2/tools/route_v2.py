#!/usr/bin/env python3
"""route_v2.py - (KiCad python) autoroute the generated V2 board with freerouting and pull the result back into KiCad.
  "C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad_v2/tools/route_v2.py dsn|route|import|all [--passes N] [--timeout S]
  dsn    : export hardware/kicad_v2/_build/LoRa_Boat_Controller_V2.dsn (Specctra) from the generated (unrouted) board
  route  : run freerouting on the DSN -> _build/LoRa_Boat_Controller_V2.ses  (needs Java 21 and the freerouting 2.1.0 jar,
           default %LOCALAPPDATA%/freerouting/freerouting-2.1.0.jar, override with FREEROUTING_JAR;
           download: https://github.com/freerouting/freerouting/releases/download/v2.1.0/freerouting-2.1.0.jar)
  import : import the SES into the board, refill the GND pours, save hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb
  all    : dsn + route + import
Re-running gen_v2.py regenerates the unrouted board; run this again afterwards (the routing is not kept in the generator).
"""
import os, sys, time, subprocess, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
import v2_design as D
V2DIR = os.path.join(ROOT, 'hardware', 'kicad_v2')
BUILD = os.path.join(V2DIR, '_build')
PCB = os.path.join(V2DIR, D.PROJ + '.kicad_pcb')
DSN = os.path.join(BUILD, D.PROJ + '.dsn')
SES = os.path.join(BUILD, D.PROJ + '.ses')
JAR = os.environ.get('FREEROUTING_JAR') or os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'freerouting', 'freerouting-2.1.0.jar')

def export_dsn():
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    assert b is not None, 'board failed to load: ' + PCB
    os.makedirs(BUILD, exist_ok=True)
    ok = pcbnew.ExportSpecctraDSN(b, DSN)
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
    ntracks = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK'); nvias = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
    unrouted = b.GetConnectivity().GetUnconnectedCount(True)
    pcbnew.SaveBoard(PCB, b)
    print('saved', PCB, ':', ntracks, 'track segments,', nvias, 'vias, unrouted connections:', unrouted)
    return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('step', choices=['dsn', 'route', 'import', 'all'])
    ap.add_argument('--passes', type=int, default=40); ap.add_argument('--timeout', type=int, default=1800)
    a = ap.parse_args()
    if a.step in ('dsn', 'all'): export_dsn()
    if a.step in ('route', 'all'):
        if not route(a.passes, a.timeout): sys.exit(1)
    if a.step in ('import', 'all'):
        if not import_ses(): sys.exit(1)
