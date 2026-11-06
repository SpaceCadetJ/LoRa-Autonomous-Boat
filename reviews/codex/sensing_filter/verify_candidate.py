"""Portable, independent checks of SENSE-02's captured native evidence.

This module never launches KiCad or changes CAD. --check is read-only;
--capture-validation writes only the deterministic validation record.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import uuid
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
BASE = ROOT / 'reviews/codex/power_sheet_polish'
BASELINE_HEAD = '95150a0916fee0fd9fc1dbb7f3c1a9185e499c63'
INPUT_MAP_SHA256 = 'a137502b3048239da92644bd36652430ddb25a7c839e5b4eb0aa5425382ad420'
POWER = 'hardware/kicad_v2/Power.kicad_sch'
MOVED = {'U8.1': ['/ISENSE', '/Power/ISENSE_DRV']}
ADDED = {'R44.1': '/Power/ISENSE_DRV', 'R44.2': '/ISENSE',
         'C59.1': '+3V3', 'C59.2': 'GND'}
FIELD_CHANGES = {'C36': ['MPN', 'Manufacturer', 'Datasheet'],
                 'C37': ['MPN', 'Manufacturer', 'Datasheet'], 'R33': ['Value']}
FALSE_FLAGS = ['hardware_accepted', 'fabrication_approved', 'procurement_approved',
               'protection_qualified', 'qualification_ports_implemented', 'pcb_integrated']
CAPACITOR_100NF = {
    'value': '100nF', 'MPN': 'C1608X7R1H104K080AA', 'Manufacturer': 'TDK',
    'Datasheet': 'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1H104K080AA',
    'Footprint': 'Capacitor_SMD:C_0603_1608Metric',
}
PARTS = {
    'C36': CAPACITOR_100NF, 'C37': CAPACITOR_100NF,
    'R33': {'value': '0.02R 3W', 'MPN': 'CRA2512-FZ-R020ELF'},
    'R44': {
        'value': '1k', 'MPN': 'RC0603FR-071KL', 'Manufacturer': 'Yageo',
        'Datasheet': 'https://yageogroup.com/component-documentation/download/specsheet/RC0603FR-071KL',
        'Footprint': 'Resistor_SMD:R_0603_1608Metric',
        'Description': 'INA180 output isolation; stability and acquisition unqualified',
    },
    'C59': {
        'value': '1uF', 'MPN': 'C1608X7R1E105K080AB', 'Manufacturer': 'TDK',
        'Datasheet': 'https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1E105K080AB',
        'Footprint': 'Capacitor_SMD:C_0603_1608Metric',
        'Description': 'INA180 local bypass; effective capacitance and layout held',
    },
}
SVG_STEMS = ['', '-Actuators', '-Actuators-ArmInterlock', '-Debug', '-MCU',
             '-Navigation', '-Power', '-Power-Buck3V3', '-Power-Buck5V', '-PowerInput', '-Radio']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def label(path):
    return path.relative_to(ROOT).as_posix()


def write(path, record):
    path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')


def mapping(directory):
    return {label(f): sha(f) for f in sorted(directory.rglob('*')) if f.is_file()}


def relative_mapping(directory):
    return {f.relative_to(directory).as_posix(): sha(f)
            for f in sorted(directory.rglob('*')) if f.is_file()}


def check_map(records, root=None):
    root = (ROOT if root is None else root).resolve()
    require(bool(records), 'Empty hash map')
    for name, expected in records.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root), 'Path outside repository: ' + name)
        require(path.is_file(), 'Missing input/artifact: ' + name)
        require(sha(path) == expected, 'Changed input/artifact: ' + name)


def validate_contract(contract):
    expected = {
        'revision': 'SENSE-02', 'baseline_head': BASELINE_HEAD,
        'baseline_candidate': 'VSERVO-01', 'baseline_presentation': 'POWER-DOC-01',
        'baseline_source': 'reviews/codex/power_sheet_polish/source',
        'expected_changed_source_files': [POWER], 'expected_added_source_files': [],
        'expected_component_count': 130, 'expected_physical_pin_count': 433,
        'expected_net_count': 122, 'expected_sheet_count': 11,
        'candidate_electrical_delta': {'moved_existing_pins': MOVED, 'added_pins': ADDED},
        'allowed_existing_field_changes': FIELD_CHANGES, 'parts': PARTS,
    }
    for key, value in expected.items():
        require(contract.get(key) == value, 'Contract boundary changed: ' + key)
    for key in ['live_electrical_delta', 'live_copper_delta']:
        require(type(contract.get(key)) is int and contract[key] == 0, 'Live delta claimed: ' + key)
    require(contract.get('native_commands_rerun') is True, 'Native execution declaration missing')
    for key in FALSE_FLAGS:
        require(contract.get(key) is False, 'Release hold changed: ' + key)


def validate_input_manifest(inputs):
    require(inputs.get('revision') == 'SENSE-02' and inputs.get('baseline_head') == BASELINE_HEAD,
            'Input revision changed')
    records = inputs['input_sha256']
    digest = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(len(records) == 580 and digest == INPUT_MAP_SHA256, 'Preserved 580-input coverage changed')
    check_map(records)


def canonical(element):
    require(element is not None, 'Missing XML element')
    return (element.tag, tuple(sorted(element.attrib.items())), (element.text or '').strip(),
            tuple(canonical(child) for child in element))


def net_evidence(tree):
    elements = tree.findall('./components/comp')
    components = {e.get('ref'): e for e in elements}
    require(len(components) == len(elements), 'Duplicate component')
    require(all(components), 'Unnamed component')
    pins, attrs, nets, net_attrs = {}, {}, {}, {}
    codes = set()
    for net in tree.findall('./nets/net'):
        name = net.get('name')
        require(name and name not in nets, 'Duplicate or missing net name')
        require(net.get('code') not in codes, 'Duplicate net code')
        codes.add(net.get('code'))
        members = []
        for node in net:
            require(node.tag == 'node' and not list(node), 'Unexpected net child')
            key = (node.get('ref'), node.get('pin'))
            require(key not in pins, 'Duplicate pin membership')
            require(key[0] in components and key[1], 'Node without component/pin')
            pins[key] = name
            attrs[key] = canonical(node)
            members.append(key)
        nets[name] = tuple(sorted(members))
        net_attrs[name] = {k: v for k, v in net.attrib.items() if k != 'code'}
    sheet_elements = tree.findall('./design/sheet')
    sheets = {s.get('name'): s for s in sheet_elements}
    require(len(sheets) == len(sheet_elements), 'Duplicate sheet')
    return {'components': components, 'pins': pins, 'attrs': attrs,
            'nets': nets, 'net_attrs': net_attrs, 'sheets': sheets}


def set_component_field(component, name, value):
    """Change every native encoding of a field, leaving its structure exact."""
    tag = {'Value': 'value', 'Footprint': 'footprint', 'Datasheet': 'datasheet',
           'Description': 'description'}.get(name)
    hits = 0
    if tag:
        for element in component.findall(tag):
            element.text = value
            hits += 1
    for element in component.findall('./fields/field'):
        if element.get('name') == name:
            element.text = value
            hits += 1
    for element in component.findall('property'):
        if element.get('name') == name:
            element.set('value', value)
            hits += 1
    require(hits > 0, 'Missing expected component field: ' + name)


def validate_netlists(before, after):
    old, new = net_evidence(before), net_evidence(after)
    require([len(old[k]) for k in ['components', 'pins', 'nets', 'sheets']] == [128, 429, 121, 11],
            'Baseline counts changed')
    require([len(new[k]) for k in ['components', 'pins', 'nets', 'sheets']] == [130, 433, 122, 11],
            'Candidate counts changed')
    require(set(new['components']) == set(old['components']) | {'R44', 'C59'}, 'Unexpected component set')
    changed_fields = {}
    for ref, component in old['components'].items():
        expected = copy.deepcopy(component)
        for field in FIELD_CHANGES.get(ref, []):
            set_component_field(expected, field, PARTS[ref]['value' if field == 'Value' else field])
        require(canonical(expected) == canonical(new['components'][ref]), 'Changed component record: ' + ref)
        if ref in FIELD_CHANGES:
            changed_fields[ref] = FIELD_CHANGES[ref]
    timestamps = [c.findtext('tstamps') for c in new['components'].values()]
    require(len(timestamps) == len(set(timestamps)), 'Duplicate component UUID')
    for ref, template in [('R44', 'R32'), ('C59', 'C37')]:
        actual = new['components'][ref]
        stamp = actual.findtext('tstamps')
        try:
            require(str(uuid.UUID(stamp)) == stamp, 'Invalid new component UUID')
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError('Invalid new component UUID: ' + ref) from error
        expected = copy.deepcopy(old['components'][template])
        expected.set('ref', ref)
        expected.find('tstamps').text = stamp
        for field, value in PARTS[ref].items():
            set_component_field(expected, 'Value' if field == 'value' else field, value)
        require(canonical(expected) == canonical(actual), 'Unexpected new component record: ' + ref)
    expected_pins = dict(old['pins'])
    for key, (source, target) in MOVED.items():
        pin = tuple(key.split('.'))
        require(expected_pins.get(pin) == source, 'Baseline moved pin differs')
        expected_pins[pin] = target
    for key, target in ADDED.items():
        expected_pins[tuple(key.split('.'))] = target
    require(new['pins'] == expected_pins, 'Pin membership differs from declared delta')
    for pin, attributes in old['attrs'].items():
        require(new['attrs'].get(pin) == attributes, 'Changed old node attributes: ' + '.'.join(pin))
    for key in ADDED:
        ref, pin = key.split('.')
        expected = ET.Element('node', {'ref': ref, 'pin': pin, 'pintype': 'passive'})
        require(new['attrs'][(ref, pin)] == canonical(expected), 'Unexpected added node attributes: ' + key)
    expected_nets = {name: [] for name in old['nets']}
    expected_nets['/Power/ISENSE_DRV'] = []
    for pin, name in expected_pins.items():
        expected_nets[name].append(pin)
    expected_nets = {name: tuple(sorted(members)) for name, members in expected_nets.items()}
    require(new['nets'] == expected_nets, 'Complete net membership changed')
    expected_net_attrs = copy.deepcopy(old['net_attrs'])
    expected_net_attrs['/Power/ISENSE_DRV'] = {'name': '/Power/ISENSE_DRV', 'class': 'Default'}
    require(new['net_attrs'] == expected_net_attrs, 'Net identity/class metadata changed')
    require(set(new['sheets']) == set(old['sheets']), 'Sheet set changed')
    for name, sheet in old['sheets'].items():
        actual = new['sheets'][name]
        require(sheet.attrib == actual.attrib, 'Sheet identity changed: ' + name)
        if name != '/Power/':
            require(canonical(sheet) == canonical(actual), 'Unrelated sheet metadata changed: ' + name)
    require(canonical(before.find('libparts')) == canonical(after.find('libparts')), 'Symbol pin definitions changed')
    return {
        'components': 130, 'physical_pin_memberships': 433, 'nets': 122, 'sheets': 11,
        'old_component_records_checked': 128, 'old_node_attributes_preserved': 429,
        'unchanged_old_pin_memberships': 428, 'added_components': ['C59', 'R44'],
        'moved_existing_pins': MOVED, 'added_pins': ADDED,
        'changed_existing_fields': changed_fields, 'complete_net_memberships_checked': 122,
        'sheet_identities_preserved': 11, 'symbol_pin_definitions_preserved': True,
    }


def validate_erc(before, after):
    # Dates are capture metadata. No positions, UUIDs, findings or sheet data are normalized.
    require({k: v for k, v in before.items() if k != 'date'} ==
            {k: v for k, v in after.items() if k != 'date'}, 'ERC findings, positions or sheet metadata changed')
    findings = [v for sheet in after['sheets'] for v in sheet['violations']]
    require(len(after['sheets']) == 11 and len(findings) == 1 and
            findings[0]['severity'] == 'warning' and findings[0]['type'] == 'pin_to_pin' and
            any(item['description'] == 'Symbol U6 Pin 9 [SDO/AD0, Bidirectional, Line]'
                for item in findings[0]['items']), 'Unexpected inherited ERC baseline')
    return {'errors': 0, 'warnings': 1, 'unchanged_ad0_warning': True,
            'finding_position_normalizations': []}


def source_subtree(text, name):
    match = re.search(r'^\t\(' + re.escape(name) + r'(?=\s|\))', text, re.M)
    require(match is not None, 'Missing source subtree: ' + name)
    start, depth, quoted, escaped = match.start() + 1, 0, False, False
    for i in range(start, len(text)):
        char = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError('Unbalanced source subtree: ' + name)


def validate_power_source(before, after):
    for key in ['uuid', 'lib_symbols']:
        require(source_subtree(before, key) == source_subtree(after, key), 'Changed source ' + key)
    return {'root_uuid_preserved': True, 'embedded_symbol_definitions_preserved_after_newline_normalization': True}


def validate_source_coverage(before, after):
    require(len(before) == 38 and set(before) == set(after), 'Source coverage changed')
    changed = [name for name in sorted(before) if before[name] != after[name]]
    require(changed == [POWER], 'Unexpected changed source')
    return changed


def validate_native_manifest(native, source_map, output_map):
    require(native.get('revision') == 'SENSE-02', 'Native revision changed')
    require(native.get('kicad_version') == '9.0.7', 'Unexpected native version')
    require(native.get('inputs_unchanged_after_commands') is True, 'Native input drift')
    require(native['input_sha256'] == source_map, 'Native input coverage changed')
    nr = label(P / 'native')
    expected_outputs = {nr + '/netlist.xml', nr + '/erc.json'} | {
        nr + '/svg/LoRa_Boat_Controller_V2' + stem + '.svg' for stem in SVG_STEMS}
    require(set(output_map) == expected_outputs and native['output_sha256'] == output_map,
            'Native output coverage changed')
    sch = label(P / 'source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch')
    expected = [
        ['sch', 'export', 'netlist', '--format', 'kicadxml', '-o', nr + '/netlist.xml', sch],
        ['sch', 'erc', '--format', 'json', '--severity-all', '-o', nr + '/erc.json', sch],
        ['sch', 'export', 'svg', '-o', nr + '/svg/', sch],
    ]
    require(len(native['commands']) == 3, 'Native command coverage changed')
    for command, argv in zip(native['commands'], expected):
        executable = command['argv'][0].replace('\\', '/').rsplit('/', 1)[-1].lower()
        require(executable in ['kicad-cli', 'kicad-cli.exe'] and command['argv'][1:] == argv and
                type(command['returncode']) is int and command['returncode'] == 0,
                'Native command failed or changed')


def collect():
    contract = read(P / 'expected_contract.json')
    validate_contract(contract)
    inputs = read(P / 'input_manifest.json')
    validate_input_manifest(inputs)
    build, native = read(P / 'build_manifest.json'), read(P / 'native_manifest.json')
    require(build.get('revision') == 'SENSE-02' and build['baseline_head'] == BASELINE_HEAD,
            'Build revision changed')
    baseline_map = read(BASE / 'native_manifest.json')['input_sha256']
    require(build['baseline_source_sha256'] == baseline_map == mapping(BASE / 'source'),
            'Baseline source set changed')
    for key, filename in [('builder_sha256', 'scoped_native.py'),
                          ('expected_contract_sha256', 'expected_contract.json'),
                          ('population_contract_sha256', 'population_contract.json')]:
        require(build[key] == sha(P / filename), 'Build provenance differs: ' + key)
    current_map = mapping(P / 'source')
    require(build['output_sha256'] == current_map, 'Build output coverage changed')
    changed = validate_source_coverage(relative_mapping(BASE / 'source'), relative_mapping(P / 'source'))
    source_semantics = validate_power_source((BASE / 'source' / POWER).read_text(encoding='utf-8'),
                                             (P / 'source' / POWER).read_text(encoding='utf-8'))
    require((BASE / 'population_contract.json').read_bytes() == (P / 'population_contract.json').read_bytes(),
            'Population contract changed')
    require(native['runner_sha256'] == sha(P / 'scoped_native.py'), 'Native runner provenance changed')
    validate_native_manifest(native, current_map, mapping(P / 'native'))
    delta = validate_netlists(ET.parse(BASE / 'native/netlist.xml'), ET.parse(P / 'native/netlist.xml'))
    erc = validate_erc(read(BASE / 'native/erc.json'), read(P / 'native/erc.json'))
    return {
        'revision': 'SENSE-02', 'baseline_presentation': 'POWER-DOC-01',
        'status': 'pass_captured_declared_delta', 'candidate_electrical_delta': delta,
        'source_preservation': {'source_files': 38, 'byte_identical_files': 37, 'changed_files': changed,
                                'both_converters_preserved': True, 'population_contract_preserved': True,
                                **source_semantics},
        'native_erc': erc, 'native_commands_reported': 3, 'native_svg_sheets': 11,
        'preserved_input_count': 580, 'live_electrical_delta': 0, 'live_copper_delta': 0,
        **{key: False for key in FALSE_FLAGS}, 'native_commands_rerun': True,
        'limits': [
            'Portable checks replay captured files; they do not launch native tools or execute hardware.',
            'Native/ERC and delta checks do not qualify stability, ADC settling, bypass placement, '
            'effective capacitance, land pattern, PCB integration, fabrication or application acceptance.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--capture-validation', '--render', '--capture', dest='capture', action='store_true')
    args = parser.parse_args()
    result = collect()
    if args.capture:
        write(P / 'validation.json', result)
    else:
        require(result == read(P / 'validation.json'), 'Stale validation record')
    print('PASS SENSE-02: 130 components, 433 pins, 122 nets, 11 sheets; '
          'one old pin moved, four new pins; 580 prior inputs preserved; hardware held')


if __name__ == '__main__':
    main()
