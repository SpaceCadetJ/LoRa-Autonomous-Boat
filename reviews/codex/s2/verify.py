"""Independent read-only verification of released commit 639e08f.

Run with KiCad 9 Python from repository root. Writes only this script's directory.
Does not import the primary conversion implementation or change Git/CAD inputs.
"""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SNAP = OUT / 'snapshot'
REVISION = '639e08f'
KICAD = Path(r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin')
V5 = 'Allegro/hardware/allegro-original/Allegro v5/Allegro/'
FILMS = 'Allegro/hardware/allegro-original/BoatcrewArtwork/'
log = []

def execute(args):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True)
    log.append({'argv': [str(a) for a in args], 'exit_code': result.returncode,
                'stdout': result.stdout.decode('utf8', errors='replace'),
                'stderr': result.stderr.decode('utf8', errors='replace')})
    (OUT / 'commands.json').write_text(json.dumps(log, indent=2), encoding='utf8')
    if result.returncode:
        raise RuntimeError(log[-1])
    return result.stdout

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')

def main():
    if '--resume-inventory' in sys.argv:
        log.extend(json.loads((OUT / 'commands.json').read_text()))
        recorded = json.loads((OUT / 'input_manifest.json').read_text())
        inventory(recorded['revision'], recorded['files'], '9.0.7')
        return
    commit = execute(['git', 'rev-parse', REVISION]).decode().strip()
    names = execute(['git', 'ls-tree', '-r', '--name-only', commit, 'hardware/kicad']).decode().splitlines()
    keep = [p for p in names if Path(p).suffix in {'.kicad_pcb', '.kicad_pro', '.kicad_sch', '.kicad_sym', '.kicad_dru', '.kicad_mod'} or Path(p).name in {'sym-lib-table', 'fp-lib-table'}]
    keep += [V5 + f for f in ('pstxnet.dat', 'pstxprt.dat', 'BOATCREWDRILL-1-2.drl', 'senior design v4-1-2.drl')]
    keep += [FILMS + f for f in ('BOATCREWTOPL.art', 'BOATCREWBOTL.art', 'BOATCREWOUTLINE.art')]
    manifest = {}
    for p in keep:
        raw = execute(['git', 'show', f'{commit}:{p}'])
        target = SNAP / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        # Keep the command transcript compact: blobs live in the hashed snapshot.
        log[-1]['stdout'] = '[blob captured in snapshot: ' + p + ']'
        manifest[p] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    dump('input_manifest.json', {'revision': commit, 'files': manifest})
    cli = KICAD / 'kicad-cli.exe'
    version = execute([cli, 'version']).decode().strip()
    cad = SNAP / 'hardware/kicad/LoRa_Boat_Controller'
    execute([cli, 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', OUT / 'netlist.xml', str(cad) + '.kicad_sch'])
    execute([cli, 'sch', 'erc', '--severity-all', '--format', 'json', '--output', OUT / 'erc.json', str(cad) + '.kicad_sch'])
    execute([cli, 'pcb', 'drc', '--severity-all', '--schematic-parity', '--format', 'json', '--output', OUT / 'drc.json', str(cad) + '.kicad_pcb'])
    inventory(commit, manifest, version)

def inventory(commit, manifest, version):
    import pcbnew
    cad = SNAP / 'hardware/kicad/LoRa_Boat_Controller'
    board = pcbnew.LoadBoard(str(cad) + '.kicad_pcb')
    # pcbnew 9 does not expose the older GetProperty API. Read explicit properties
    # from each top-level footprint in the same hashed PCB; do not infer suffixes.
    refmap = {}
    for block in re.split(r'\n\t\(footprint ', Path(str(cad) + '.kicad_pcb').read_text(encoding='utf8'))[1:]:
        props = dict(re.findall(r'\(property "(Reference|Allegro_RefDes)" "([^"]*)"', block))
        if set(props) != {'Reference', 'Allegro_RefDes'}:
            raise ValueError('Missing explicit footprint provenance field')
        refmap[props['Reference']] = props['Allegro_RefDes']
    fps = []
    for fp in board.GetFootprints():
        fps.append({'ref': fp.GetReference(), 'allegro_ref': refmap[fp.GetReference()],
                    'path': fp.GetPath().AsString(), 'footprint': fp.GetFPIDAsString(),
                    'pads': [{'pin': p.GetNumber(), 'net': p.GetNetname(),
                              'at_mm': [p.GetPosition().x / 1e6, p.GetPosition().y / 1e6],
                              'drill_mm': [p.GetDrillSize().x / 1e6, p.GetDrillSize().y / 1e6]}
                             for p in fp.Pads()]})
    vias = [{'at_mm': [t.GetPosition().x / 1e6, t.GetPosition().y / 1e6],
             'diameter_mm': t.GetWidth(pcbnew.F_Cu) / 1e6, 'drill_mm': t.GetDrillValue() / 1e6}
            for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    dump('pcb_inventory.json', {'footprints': fps, 'vias': vias})
    changed = [p for p, m in manifest.items() if hashlib.sha256((SNAP / p).read_bytes()).hexdigest() != m['sha256']]
    dump('run.json', {'revision': commit, 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'kicad_version': version, 'python_version': sys.version, 'snapshot_changed_by_checks': changed})
    print('Snapshot and independent KiCad outputs complete:', commit, version, len(fps), 'footprints;', len(vias), 'vias')

if __name__ == '__main__':
    main()
