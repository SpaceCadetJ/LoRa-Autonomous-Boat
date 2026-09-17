"""Analyze the hashed S2 snapshot and read-only KiCad outputs without conversion imports."""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SNAP = HERE / 'snapshot'
V5 = SNAP / 'Allegro/hardware/allegro-original/Allegro v5/Allegro'
FILMS = SNAP / 'Allegro/hardware/allegro-original/BoatcrewArtwork'

def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf8')

def pin(value):
    return str(int(value)) if value.isdigit() else value

def groups(nets, nc=False):
    result = []
    for name, members in nets.items():
        if name == 'NC' and nc:
            result.extend(frozenset([member]) for member in members)
        else:
            result.append(frozenset(members))
    return set(result)

text = (V5 / 'pstxnet.dat').read_text(encoding='latin1')
source = {}
for part in re.split(r'(?m)^NET_NAME\s*\n', text)[1:]:
    name = re.match(r"'([^']+)'", part)[1]
    source[name] = [(ref, pin(n)) for ref, n in re.findall(r'(?m)^NODE_NAME\s+(\S+)\s+(\d+)', part)]
assert sum(map(len, source.values())) == len(re.findall(r'(?m)^NODE_NAME\s', text))
assert len(source) == len(re.findall(r'(?m)^NET_NAME\s*$', text))
sourceparts = set(re.findall(r"(?m)^PART_NAME\s*\n\s*(\S+)\s+'", (V5 / 'pstxprt.dat').read_text(encoding='latin1')))
tree = ET.parse(HERE / 'netlist.xml').getroot()
components = {}
refmap = {}
for c in tree.find('components'):
    properties = {p.attrib['name']: p.attrib['value'] for p in c.findall('property')}
    aref = properties['Allegro_RefDes']
    refmap[c.attrib['ref']] = aref
    components[aref] = {'ref': c.attrib['ref'], 'value': c.findtext('value'), 'footprint': c.findtext('footprint'),
                        'path': c.find('sheetpath').attrib['tstamps'] + c.findtext('tstamps')}
schematic = {n.attrib['name']: [(refmap[x.attrib['ref']], pin(x.attrib['pin'])) for x in n.findall('node')]
             for n in tree.find('nets')}
inventory = json.loads((HERE / 'pcb_inventory.json').read_text())
pcb = collections.defaultdict(list)
pcbparts = set()
path_mismatches = []
fp_mismatches = []
for f in inventory['footprints']:
    aref = f['allegro_ref']
    pcbparts.add(aref)
    if f['path'] != components[aref]['path']:
        path_mismatches.append(aref)
    if f['footprint'] != components[aref]['footprint']:
        fp_mismatches.append(aref)
    for p in f['pads']:
        # An unassigned PCB pad is an individual isolated pin, never a shared NC net.
        net = p['net'] or '@isolated:' + aref + ':' + p['pin']
        pcb[net].append((aref, pin(p['pin'])))
expected = groups(source, nc=True)
sch_groups = groups(schematic)
pcb_groups = groups(pcb)
convert = lambda seq: [sorted(s) for s in sorted(seq, key=lambda g: sorted(g))]
connectivity = {'source_parts': len(sourceparts), 'schematic_parts': len(components), 'pcb_parts': len(pcbparts),
                'source_connected_nets': len(source) - ('NC' in source),
                'source_multi_pin_nets': sum(len(v) > 1 for n, v in source.items() if n != 'NC'),
                'source_nc_pins': len(source.get('NC', [])), 'all_physical_pins': sum(map(len, source.values())),
                'schematic_pin_count': sum(map(len, schematic.values())), 'pcb_pad_count': sum(map(len, pcb.values())),
                'source_pin_groups_with_NC_split': len(expected),
                'source_duplicate_memberships': [p for p, n in collections.Counter(p for ns in source.values() for p in ns).items() if n > 1],
                'schematic_duplicate_memberships': [p for p, n in collections.Counter(p for ns in schematic.values() for p in ns).items() if n > 1],
                'pcb_duplicate_memberships': [p for p, n in collections.Counter(p for ns in pcb.values() for p in ns).items() if n > 1],
                'schematic_missing_groups': convert(expected - sch_groups), 'schematic_extra_groups': convert(sch_groups - expected),
                'pcb_missing_groups': convert(expected - pcb_groups), 'pcb_extra_groups': convert(pcb_groups - expected),
                'refs_missing_in_schematic': sorted(sourceparts - components.keys()), 'refs_extra_in_schematic': sorted(components.keys() - sourceparts),
                'refs_missing_in_pcb': sorted(sourceparts - pcbparts), 'refs_extra_in_pcb': sorted(pcbparts - sourceparts),
                'footprint_path_mismatches': path_mismatches, 'footprint_library_mismatches': fp_mismatches}
connectivity['pass'] = not any(v for k, v in connectivity.items() if isinstance(v, list))
write('connectivity.json', connectivity)

drc = json.loads((HERE / 'drc.json').read_text())
erc = json.loads((HERE / 'erc.json').read_text())
parity_categories = collections.Counter()
unclassified = []
for v in drc['schematic_parity']:
    desc = v['description']
    m = re.fullmatch(r"Pad net \((.*?)\) doesn't match net given by schematic \((.*?)\)\.", desc)
    if v['type'] == 'footprint_symbol_mismatch' and desc.startswith('Value ('):
        parity_categories['footprint_value_mismatch'] += 1
    elif m and m[1] == m[2].split('/')[-1]:
        parity_categories['sheet_prefix_net_name_difference'] += 1
    elif desc.startswith('Pad missing net given by schematic (unconnected-'):
        parity_categories['unassigned_pad_vs_schematic_unconnected_name'] += 1
    elif m and m[1] == 'VBAT' and m[2] == 'unconnected-(U3-VBAT-Pad1)':
        parity_categories['VBAT_singleton_vs_schematic_unconnected_name'] += 1
    else:
        unclassified.append(v)
rules = {'erc_violations': sum(len(s['violations']) for s in erc['sheets']),
         'drc_violations': len(drc['violations']), 'drc_counts': dict(collections.Counter(v['type'] + ':' + v['severity'] for v in drc['violations'])),
         'drc_errors': sum(v['severity'] == 'error' for v in drc['violations']), 'unconnected_items': len(drc['unconnected_items']),
         'schematic_parity_issues': len(drc['schematic_parity']), 'schematic_parity_counts': dict(parity_categories),
         'schematic_parity_unclassified': unclassified}
write('rule_summary.json', rules)

def flashes(path):
    raw = path.read_text(encoding='latin1')
    assert '%FSLAX25Y25*MOIN*%' in raw
    apertures = {int(n): (shape, params) for n, shape, params in re.findall(r'%ADD(\d+)([CRO]),([^*]+)\*%', raw)}
    x = y = aperture = None
    polarity = 'D'
    output = set()
    for line in raw.splitlines():
        pol = re.fullmatch(r'%LP([DC])\*%', line)
        if pol:
            polarity = pol[1]
        ap = re.fullmatch(r'(?:G54)?D(\d+)\*', line)
        if ap and int(ap[1]) >= 10:
            aperture = int(ap[1])
            continue
        # Arc endpoints also update the modal location. No geometry is rendered.
        coord = re.fullmatch(r'(?:G0[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0([123])\*', line)
        if not coord:
            continue
        if coord[1] is not None:
            x = int(coord[1])
        if coord[2] is not None:
            y = int(coord[2])
        if coord[3] == '3' and polarity == 'D' and apertures[aperture][0] == 'C':
            assert x is not None and y is not None
            output.add((round(x * 25.4 / 1e5, 6), round(-y * 25.4 / 1e5, 6)))
    return output

top = flashes(FILMS / 'BOATCREWTOPL.art')
bottom = flashes(FILMS / 'BOATCREWBOTL.art')
film_holes = top & bottom
holes = [p['at_mm'] for f in inventory['footprints'] for p in f['pads'] if any(p['drill_mm'])]
via_holes = [p['at_mm'] for p in inventory['vias']]
all_holes = holes + via_holes
# Solve one common translation after the Gerber-to-KiCad Y inversion. No primary transform imported.
translations = collections.Counter((round(a[0]-b[0], 4), round(a[1]-b[1], 4)) for a in all_holes for b in film_holes)
translation = translations.most_common(1)[0][0]
mapped = [(x + translation[0], y + translation[1]) for x, y in film_holes]
distances = [min(math.dist(p, q) for q in mapped) for p in all_holes]
reverse_distances = [min(math.dist(p, q) for q in all_holes) for p in mapped]
strip_header = lambda p: '\n'.join(l for l in p.read_text(encoding='latin1').splitlines() if not l.startswith(';FILE'))
drill_report = {'board_plated_pad_holes': len(holes), 'board_vias': len(via_holes), 'board_total_holes': len(all_holes),
                'top_round_dark_flash_centers': len(top), 'bottom_round_dark_flash_centers': len(bottom),
                'shared_v5_round_dark_flash_centers': len(film_holes), 'alignment_translation_mm_after_Y_inversion': translation,
                'max_board_to_film_error_mil': max(distances) / .0254, 'max_film_to_board_error_mil': max(reverse_distances) / .0254,
                'centers_within_0_05mil': len(all_holes) == len(film_holes) and max(distances + reverse_distances) <= .05 * .0254,
                'available_drill_identical_to_v4_except_FILE_header': strip_header(V5 / 'BOATCREWDRILL-1-2.drl') == strip_header(V5 / 'senior design v4-1-2.drl'),
                'diameters_independently_verified_against_v5_drill': False}
write('drill_comparison.json', drill_report)
manifest = json.loads((HERE / 'input_manifest.json').read_text())
changed = [p for p, m in manifest['files'].items() if hashlib.sha256((SNAP / p).read_bytes()).hexdigest() != m['sha256']]
write('analysis.json', {'revision': manifest['revision'], 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'snapshot_hash_mismatches': changed, 'connectivity': connectivity, 'rules': rules, 'drill': drill_report})
print(json.dumps({'connectivity': connectivity, 'rules': rules, 'drill': drill_report, 'snapshot_hash_mismatches': changed}, indent=2))
