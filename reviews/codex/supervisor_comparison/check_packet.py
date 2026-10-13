"""Check exact preservation and captured packet hashes without executing CAD tools."""
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_preserved():
    inputs = read('input_manifest.json')
    for name, expected in inputs['input_sha256'].items():
        assert sha(ROOT / name) == expected, f'Preserved input changed: {name}'
    evidence = read('preservation.json')
    netlist = ROOT / evidence['baseline_native_path']
    assert sha(netlist) == evidence['baseline_native_sha256']
    nets = ET.parse(netlist).getroot().find('nets')
    actual = {n.attrib['name']: sorted(p.attrib['ref']+'.'+p.attrib['pin'] for p in n.findall('node')) for n in nets}
    for name, expected in evidence['checked_memberships'].items():
        assert actual[name] == sorted(expected), name
    assert len(inputs['input_sha256']) == evidence['preserved_input_count'] == 198
    assert not read('contract.json')['parts_selected'] and not inputs['native_commands_rerun']
    assert not evidence['qualified_for_power']
    return inputs

def capture():
    inputs = check_preserved()
    artifact = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and p.name != 'packet_manifest.json' and '__pycache__' not in p.parts}
    return {'schema': 1, 'revision': 'ACT-06', 'source_revision': inputs['source_revision'],
            'input_sha256': inputs['input_sha256'], 'artifact_sha256': artifact,
            'candidate_electrical_delta': 0, 'live_electrical_delta': 0, 'live_copper_delta': 0,
            'parts_selected': False, 'hardware_tested': False, 'fabrication_approved': False,
            'native_commands_rerun': False, 'qualification_ports_implemented': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = capture()
    if args.capture:
        (HERE / 'packet_manifest.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    else:
        assert result == read('packet_manifest.json'), 'Packet files or limits changed'
    print(f"PASS ACT-06: {len(result['input_sha256'])} preserved inputs, {len(result['artifact_sha256'])} packet artifacts; no circuit change")
