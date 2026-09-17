"""Verify that only two intended vias and their refill differ from source."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
spec = importlib.util.spec_from_file_location('quality_review', ROOT / 'tools/quality/review.py')
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)
source = ROOT / 'reviews/codex/publication/native-review/inputs/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb'
candidate = OUT / 'candidate' / source.name
manifest = json.loads((OUT / 'candidate_manifest.json').read_text())
tree_a = quality.parse_sexpr(source.read_text())
tree_b = quality.parse_sexpr(candidate.read_text())
def records(tree, kind):
    return [n for n in tree if isinstance(n, list) and n and n[0] == kind]
def signature(item):
    return json.dumps(item, sort_keys=True, separators=(',', ':'))
counts = {}
changed = {}
for kind in ('footprint', 'segment', 'arc', 'via', 'gr_line', 'gr_arc', 'gr_text', 'net', 'setup', 'layers', 'general'):
    before = Counter(map(signature, records(tree_a, kind)))
    after = Counter(map(signature, records(tree_b, kind)))
    counts[kind] = {'before': sum(before.values()), 'after': sum(after.values())}
    removed = list((before - after).elements())
    added = list((after - before).elements())
    if removed or added:
        changed[kind] = {'removed': [json.loads(n) for n in removed], 'added': [json.loads(n) for n in added]}
zone_a = [[n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')] for z in records(tree_a, 'zone')]
zone_b = [[n for n in z if not (isinstance(n, list) and n and n[0] == 'filled_polygon')] for z in records(tree_b, 'zone')]
other_a = Counter(signature(n) for n in tree_a if not (isinstance(n, list) and n and n[0] in ('zone', 'via')))
other_b = Counter(signature(n) for n in tree_b if not (isinstance(n, list) and n and n[0] in ('zone', 'via')))
drc_before = json.loads((OUT / 'drc_before.json').read_text())
drc_after = json.loads((OUT / 'drc_after.json').read_text())
def drc_count(d):
    return {'violation_errors': sum(v['severity'] == 'error' for v in d['violations']),
            'violation_warnings': sum(v['severity'] == 'warning' for v in d['violations']),
            'unconnected': len(d['unconnected_items']), 'schematic_parity': len(d['schematic_parity'])}
check = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
         'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(), 'object_counts': counts,
         'changed_structures': changed, 'zone_settings_and_outlines_unchanged': zone_a == zone_b,
         'all_other_top_level_records_unchanged': other_a == other_b,
         'drc_before': drc_count(drc_before), 'drc_after': drc_count(drc_after),
         'ordinary_violations_exactly_equal': drc_before['violations'] == drc_after['violations'],
         'schematic_parity_exactly_equal': drc_before['schematic_parity'] == drc_after['schematic_parity'],
         'fabrication_approved': False}
expected_uuids = {c['uuid'] for c in manifest['changes']}
added_uuids = {quality.child(v, 'uuid')[1] for v in changed.get('via', {}).get('added', [])}
check['passed'] = (check['source_sha256'] == manifest['source_sha256'] and check['candidate_sha256'] == manifest['candidate_sha256']
                   and set(changed) == {'via'} and not changed['via']['removed'] and added_uuids == expected_uuids
                   and check['zone_settings_and_outlines_unchanged'] and check['ordinary_violations_exactly_equal']
                   and check['all_other_top_level_records_unchanged']
                   and check['schematic_parity_exactly_equal'] and check['drc_after']['unconnected'] == 1)
(OUT / 'verification.json').write_text(json.dumps(check, indent=2) + '\n', encoding='utf-8')
print(json.dumps(check, indent=2))
raise SystemExit(0 if check['passed'] else 1)
