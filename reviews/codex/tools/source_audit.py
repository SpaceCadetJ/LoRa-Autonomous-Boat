"""Read sources only; from repo root run python reviews/codex/tools/source_audit.py.
Writes only reviews/codex/SOURCE_AUDIT.json. No conversion-tool imports or dependencies.
This is a source-facts inventory, NOT a PCB validation or gate pass.
"""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reviews/codex/SOURCE_AUDIT.json'
V5 = ROOT / 'Allegro/hardware/allegro-original/Allegro v5/Allegro'
FAB = ROOT / 'Allegro/hardware/allegro-original/BoatcrewArtwork'
manifest = {}


def read(path):
    raw = path.read_bytes()
    manifest[path.relative_to(ROOT).as_posix()] = {
        'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return raw.decode('latin-1')


def git(*args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    return {'exit_code': r.returncode, 'stdout': r.stdout.strip(), 'stderr': r.stderr.strip()}


nettext = read(V5 / 'pstxnet.dat')
nets = {}
for match in re.finditer(r"(?m)^NET_NAME\s*\n'([^\n]+)'\s*\n([\s\S]*?)(?=^NET_NAME|^END\.|\Z)", nettext):
    name, body = match.groups()
    nodes = []
    for node in re.finditer(r"(?m)^NODE_NAME\s+(\S+)\s+(\d+)\s*\n[^\n]*\n\s*'([^']*)'", body):
        ref, pin, label = node.groups()
        offset = match.start(2) + node.start()
        nodes.append({'ref': ref, 'pin': str(int(pin)), 'label': label,
                      'line': nettext.count('\n', 0, offset) + 1})
    if not nodes:
        raise ValueError('Empty/unparsed source net: ' + name)
    nets[name] = nodes
if len(nets) != len(re.findall(r'(?m)^NET_NAME\s*$', nettext)):
    raise ValueError('Not all source nets parsed')
if sum(map(len, nets.values())) != len(re.findall(r'(?m)^NODE_NAME\s', nettext)):
    raise ValueError('Not all source nodes parsed')

parts_text = read(V5 / 'pstxprt.dat')
parts = dict(re.findall(r"(?m)^PART_NAME\s*\n\s*(\S+)\s+'([^']+)'", parts_text))
connected = {n: p for n, p in nets.items() if n != 'NC'}
pin_counts = collections.Counter((p['ref'], p['pin']) for pins in nets.values() for p in pins)

artwork = []
for p in sorted((ROOT / 'Allegro').rglob('*')):
    if p.is_file() and (p.name.lower().endswith('.art') or '.art,' in p.name.lower()):
        t = read(p)
        def field(key):
            m = re.search(r'(?m)^G04 ' + re.escape(key) + r':\s*(.*?)\*', t)
            return m.group(1) if m else None
        artwork.append({'path': p.relative_to(ROOT).as_posix(),
                        'source_board': field('Layout Name'), 'date': field('Origin Date'),
                        'film': field('Film Name')})

outline = read(FAB / 'BOATCREWOUTLINE.art')
if '%FSLAX25Y25*MOIN*%' not in outline:
    raise ValueError('Unsupported outline format')
x = y = None
points = []
for cmd in outline.split('*'):
    m = re.fullmatch(r'\s*(?:G01)?(?:X(-?\d+))?(?:Y(-?\d+))?D0[12]', cmd)
    if m and any(v is not None for v in m.groups()):
        xx, yy = m.groups()
        x = int(xx) if xx is not None else x
        y = int(yy) if yy is not None else y
        if x is None or y is None:
            raise ValueError('Incomplete first outline coordinate')
        points.append([x / 100000, y / 100000])
if len(points) < 4 or points[0] != points[-1]:
    raise ValueError('Outline not closed')

drill = read(V5 / 'BOATCREWDRILL-1-2.drl')
old_drill = read(V5 / 'senior design v4-1-2.drl')
def strip_file_line(t):
    return '\n'.join(line for line in t.splitlines() if not line.startswith(';FILE'))
tool = None
holes = collections.Counter()
for line in drill.splitlines():
    if re.fullmatch(r'T\d+', line):
        tool = line
    elif re.match(r'^[XY]-?\d', line):
        holes[tool] += 1
zip_path = V5 / 'Artwork.zip'
read(zip_path)
with zipfile.ZipFile(zip_path) as z:
    zi = z.getinfo('Artwork/BOATCREWDRILL-1-2.drl')
    zipped_drill = z.read(zi)
    zip_evidence = {'timestamp': zi.date_time, 'same_bytes_as_boatcrew_drill':
                    hashlib.sha256(zipped_drill).hexdigest() == manifest[(V5 / 'BOATCREWDRILL-1-2.drl').relative_to(ROOT).as_posix()]['sha256']}

observed_files = [
    'AGENT_PROMPT_V2.md', 'CONVERSION_LOG.md', 'docs/A0_PROVENANCE.md',
    'hardware/kicad/tools/gen_pcb.py', 'hardware/kicad/tools/validate_pcb.py',
    'hardware/kicad/LoRa_Boat_Controller.kicad_pcb',
    'hardware/kicad/LoRa_Boat_Controller.kicad_pro',
    'firmware/Core/Src/main.c', 'firmware/Core/Src/stm32f4xx_hal_msp.c',
    'firmware/BoatTHISTIMEITSDIFFERENT.ioc',
    'Allegro/hardware/allegro-original/Allegro v5/Allegro/netrev.lst',
    'reviews/codex/tools/source_audit.py',
    'hardware/kicad/_build/validate_pcb.json', 'hardware/kicad/_build/drc.json',
]
for p in observed_files:
    if (ROOT / p).exists():
        read(ROOT / p)
pcb = (ROOT / observed_files[5]).read_text(encoding='utf-8')
schematics = {}
for p in sorted((ROOT / 'hardware/kicad').glob('*.kicad_sch')):
    t = read(p)
    schematics[p.name] = {'wire_objects_text_count': len(re.findall(r'\(wire\s+\(', t))}
primary_reports = {}
for name in ['validate_pcb.json', 'drc.json']:
    p = ROOT / 'hardware/kicad/_build' / name
    if p.exists():
        data = json.loads(read(p))
        if name == 'drc.json':
            primary_reports[name] = {
                'date': data.get('date'), 'source': data.get('source'),
                'violations_by_type_severity': dict(collections.Counter(
                    str(v.get('type')) + ':' + str(v.get('severity')) for v in data.get('violations', []))),
                'unconnected_report_entries': len(data.get('unconnected_items', [])),
                'status': 'Observed primary output; input linkage and independent run NOT verified'}
        else:
            primary_reports[name] = data
changed = [p for p, meta in manifest.items()
           if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != meta['sha256']]
report = {
    'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'purpose': 'Independent source inventory; not ERC/DRC/copper continuity proof',
    'command': 'python reviews/codex/tools/source_audit.py',
    'git_head': git('rev-parse', 'HEAD'), 'git_status': git('status', '--short', '--branch'),
    'electrical_net_count_excluding_NC': len(connected), 'NC_node_count': len(nets.get('NC', [])),
    'part_count': len(parts), 'parts': parts, 'nets_including_NC': nets,
    'duplicate_pin_membership': [list(p) for p, count in pin_counts.items() if count != 1],
    'artwork_headers': artwork,
    'outline': {'centerline_points_inches': points,
                'width_mm': round((max(p[0] for p in points) - min(p[0] for p in points))*25.4, 6),
                'height_mm': round((max(p[1] for p in points) - min(p[1] for p in points))*25.4, 6)},
    'drill': {'holes_per_tool': dict(holes), 'total': sum(holes.values()),
              'same_as_v4_except_FILE_line': strip_file_line(drill) == strip_file_line(old_drill),
              'archived_copy': zip_evidence,
              'interpretation': 'Older v4-identical drill; no independent v5 drill fidelity proof'},
    'pcb_text_counts_only': {key: len(re.findall(r'\(' + key + r'\s', pcb)) for key in ['footprint', 'segment', 'via', 'zone']},
    'schematic_text_counts_only': schematics,
    'observed_primary_reports_not_independently_rerun': primary_reports,
    'files_changed_during_read': changed, 'input_manifest': manifest,
}
OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['timestamp_utc','electrical_net_count_excluding_NC','NC_node_count','part_count','outline','drill','pcb_text_counts_only','files_changed_during_read']}, indent=2))
print('Wrote', OUT)
