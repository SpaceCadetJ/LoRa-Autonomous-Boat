"""SENSE-02: bounded edit of one immutable captured Power-sheet copy.

This is a local review-candidate transform, not a primary schematic generator.
Only this packet's 38-file source copy and recorded native outputs are written.
No board, router, firmware, live CAD or previous packet is modified.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, re, shutil, subprocess, uuid
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
BASE = ROOT / 'reviews/codex/power_sheet_polish'
SOURCE = P / 'source'
POWER = Path('hardware/kicad_v2/Power.kicad_sch')
CLI = 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe'
REV = 'SENSE-02'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')

def label(path):
    return path.relative_to(ROOT).as_posix()

def mapping(path):
    return {label(f): sha(f) for f in sorted(path.rglob('*')) if f.is_file()}

def check_map(records):
    require(bool(records), 'Empty source hash map')
    for name, digest in records.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), 'Input path outside repository: ' + name)
        require(sha(path) == digest, 'Input changed: ' + name)

def blocks(text):
    """Yield exact root child text without parsing or rewriting libraries."""
    level = 0
    quoted = escaped = False
    start = None
    for i, ch in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == '(':
            level += 1
            if level == 2:
                start = i
        elif ch == ')':
            if level == 2:
                yield text[start:i + 1]
            level -= 1
    require(level == 0 and not quoted, 'Unbalanced schematic')

def kind(block):
    return re.match(r'\(([^\s()]+)', block)[1]

def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'lora-review/' + REV + '/' + name))

def ident(block):
    match = re.search(r'\(uuid "([^"]+)"', block)
    return match[1] if match else None

def replace_one(text, before, after):
    require(text.count(before) == 1, 'Expected one literal: ' + before)
    return text.replace(before, after)

def set_prop(block, name, value):
    pat = r'(\(property "' + re.escape(name) + r'" )"(?:[^"\\]|\\.)*"'
    block, count = re.subn(pat, lambda m: m[1] + json.dumps(value), block)
    require(count == 1, 'Expected one property: ' + name)
    return block

def translate(block, dx, dy):
    return re.sub(r'\((at|xy) (-?[\d.]+) (-?[\d.]+)',
        lambda m: f'({m[1]} {float(m[2])+dx:.6f} {float(m[3])+dy:.6f}', block)

def new_component(template, old_ref, ref, dx, dy, values):
    block = translate(template, dx, dy)
    block = set_prop(block, 'Reference', ref)
    block = replace_one(block, f'(reference "{old_ref}")', f'(reference "{ref}")')
    block = re.sub(r'\(uuid "([^"]+)"', lambda m: f'(uuid "{uid(ref + "/" + m[1])}"', block)
    for key, value in values.items():
        block = set_prop(block, 'Value' if key == 'value' else key, value)
    return block

def wire(name, a, b):
    return (f'(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) '
            f'(stroke (width 0) (type default)) (uuid "{uid(name)}"))')

def local_label(name, x, y):
    return (f'(label "{name}" (at {x:g} {y:g} 0) '
            f'(effects (font (size 1 1)) (justify left bottom)) (uuid "{uid(name)}"))')

def junction(name, x, y):
    return (f'(junction (at {x:g} {y:g}) (diameter 0) (color 0 0 0 0) '
            f'(uuid "{uid(name)}"))')

def property_position(block, name, x, y, angle):
    pat = r'(\(property "' + re.escape(name) + r'" "(?:[^"\\]|\\.)*"\s*\(at )[^)]+'
    block, count = re.subn(pat, lambda m: m[1] + f'{x:g} {y:g} {angle:g}', block)
    require(count == 1, 'Property location missing: ' + name)
    return block

def amend(text, contract):
    original = list(blocks(text))
    symbols = {}
    for block in original:
        if kind(block) == 'symbol':
            ref = re.search(r'\(property "Reference" "([^"]+)"', block)[1]
            symbols[ref] = block
    require('R44' not in symbols and 'C59' not in symbols, 'New references already used')
    require('#PWRPOW36' not in symbols and '#PWRPOW37' not in symbols, 'Power references used')
    parts = contract['parts']
    c37_island = {
        '9d5e1e2c-1e33-529b-ba23-b3f50b04bdf6',
        '2965c184-da4f-50a7-b16f-722eb15c905a',
        '43f6fa5f-9903-55a3-bb5f-6e9c59ae35c4',
        '47fbbb5b-d5b3-54c1-bd38-3c5f7b76d744',
        'f0b43484-b834-5c12-b326-e32f67671fc4',
        '64a00305-172e-5ed3-80e0-788c312583d5',
    }
    changed = set()
    out = []
    for block in original:
        k = kind(block)
        identity = ident(block)
        if k == 'title_block':
            block = replace_one(block, '(date "2026-10-29")', '(date "2026-11-06")')
            block = replace_one(block, '(rev "PD-01")', '(rev "SN-02")')
            block = replace_one(block, 'Presentation only; electrical baseline VSERVO-01',
                                'SENSE-02 isolated filter correction; hardware held')
            block = replace_one(block, 'reviews/codex/power_sheet_polish/README.md',
                                'reviews/codex/sensing_filter/README.md')
        elif k == 'symbol':
            ref = re.search(r'\(property "Reference" "([^"]+)"', block)[1]
            if ref in ['C36', 'C37']:
                for key in ['MPN', 'Manufacturer', 'Datasheet']:
                    block = set_prop(block, key, parts[ref][key])
                changed.add(ref)
            elif ref == 'R33':
                block = set_prop(block, 'Value', parts[ref]['value'])
                changed.add(ref)
        elif identity == '136210cc-fcda-5333-a430-7f8d291379f2':
            # Replace only the amplifier's old hierarchy label; C37 retains ISENSE.
            require(k == 'hierarchical_label', 'Unexpected original U8 output label')
            block = local_label('ISENSE_DRV', 100.33, 160.02)
            changed.add('U8.1')
        elif k == 'text':
            block = block.replace(
                'POWER-DOC-01 | Presentation revision; electrical baseline VSERVO-01',
                'SENSE-02 | Isolated output-filter + bypass correction; physical acceptance held')
            block = block.replace(
                'Circuit retained for review; correct the full 6S sensing path before use.',
                'R44/C37 isolation + C59 bypass proposed; stability, ADC and full 6S limits held.')
        if identity in c37_island:
            block = translate(block, 0, 21.59)
        out.append(block)
    require(changed == {'C36', 'C37', 'R33', 'U8.1'}, 'Unexpected edits')
    # R44 is horizontal: pin 1 left at118.11,160.02; pin2 right at125.73,160.02.
    resistor = new_component(symbols['R31'], 'R31', 'R44', 81.28, -40.64, parts['R44'])
    resistor = re.sub(r'\(at (-?[\d.]+) (-?[\d.]+) 0\)',
                      r'(at \1 \2 90)', resistor, count=1)
    resistor = property_position(resistor, 'Reference', 121.92, 153.67, 90)
    resistor = property_position(resistor, 'Value', 121.92, 156.21, 90)
    # KiCad rotates symbol fields: stored90 with symbol90 renders world-horizontal.
    # Center both visible fields above the resistor without changing its pins.
    resistor = resistor.replace('(justify left)', '')
    out.append(resistor)
    out.append(wire('R44-input', (104.14, 160.02), (118.11, 160.02)))
    out.append(wire('R44-output', (125.73, 160.02), (139.70, 160.02)))
    out.append(junction('C37-filter-junction', 139.70, 160.02))
    # 1uF nominal local supply-bypass candidate; effective capacitance/PCB held.
    out.append(new_component(symbols['C37'], 'C37', 'C59', 35.56, 0, parts['C59']))
    out.append(new_component(symbols['#PWRPOW08'], '#PWRPOW08', '#PWRPOW36',
                             86.36, -8.89, {}))
    out.append(new_component(symbols['#PWRPOW10'], '#PWRPOW10', '#PWRPOW37',
                             35.56, 0, {}))
    out.append(wire('C59-supply', (175.26, 143.51), (175.26, 138.43)))
    out.append(wire('C59-ground', (175.26, 151.13), (175.26, 156.21)))
    result = '(kicad_sch\n\t' + '\n\t'.join(out) + '\n)\n'
    result_blocks = list(blocks(result))
    for key in ['uuid', 'lib_symbols']:
        require(next(b for b in original if kind(b) == key) ==
                next(b for b in result_blocks if kind(b) == key), 'Changed preserved ' + key)
    return result

def build():
    contract = read(P / 'expected_contract.json')
    inputs = read(P / 'input_manifest.json')
    require(contract['revision'] == inputs['revision'] == REV, 'Wrong revision')
    require(contract['baseline_head'] == inputs['baseline_head'], 'Baseline HEAD mismatch')
    check_map(inputs['input_sha256'])
    basehash = read(BASE / 'native_manifest.json')['input_sha256']
    check_map(basehash)
    require(len(basehash) == 38, 'Expected 38 baseline source files')
    require(sha(P / 'population_contract.json') == sha(BASE / 'population_contract.json'),
            'Population contract changed')
    expected = set()
    for name in basehash:
        rel = (ROOT / name).relative_to(BASE / 'source')
        destination = SOURCE / rel
        expected.add(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    power = SOURCE / POWER
    power.write_text(amend(power.read_text(encoding='utf-8'), contract),
                     encoding='utf-8', newline='\n')
    require({f for f in SOURCE.rglob('*') if f.is_file()} == expected, 'Source coverage changed')
    check_map(basehash)
    check_map(inputs['input_sha256'])
    changed = sorted((ROOT / name).relative_to(BASE / 'source').as_posix()
                     for name, digest in basehash.items()
                     if sha(SOURCE / (ROOT / name).relative_to(BASE / 'source')) != digest)
    require(changed == contract['expected_changed_source_files'], 'Unexpected source changes')
    write(P / 'build_manifest.json', {
        'revision': REV,
        'baseline_head': inputs['baseline_head'],
        'baseline_candidate': contract['baseline_candidate'],
        'baseline_presentation': contract['baseline_presentation'],
        'builder_sha256': sha(Path(__file__)),
        'expected_contract_sha256': sha(P / 'expected_contract.json'),
        'population_contract_sha256': sha(P / 'population_contract.json'),
        'input_manifest_sha256': sha(P / 'input_manifest.json'),
        'baseline_source_sha256': basehash,
        'output_sha256': mapping(SOURCE),
        'changed_source_files': changed,
        'added_source_files': [],
        'candidate_electrical_delta': contract['candidate_electrical_delta'],
        'live_electrical_delta': 0,
        'live_copper_delta': 0,
        'primary_generator_or_router_invoked': False
    })
    print('Built isolated 38-file candidate; Power changed, 37 files byte-identical')

def native():
    contract = read(P / 'expected_contract.json')
    built = read(P / 'build_manifest.json')
    inputs = read(P / 'input_manifest.json')
    check_map(built['output_sha256'])
    check_map(inputs['input_sha256'])
    check_map(built['baseline_source_sha256'])
    for key, path in [('builder_sha256', Path(__file__)),
                      ('expected_contract_sha256', P / 'expected_contract.json'),
                      ('population_contract_sha256', P / 'population_contract.json'),
                      ('input_manifest_sha256', P / 'input_manifest.json')]:
        require(built[key] == sha(path), 'Build prerequisite changed: ' + key)
    out = P / 'native'
    out.mkdir(exist_ok=True)
    nr = label(out)
    sch = label(SOURCE / 'hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch')
    commands = [
        ['sch', 'export', 'netlist', '--format', 'kicadxml', '-o', nr + '/netlist.xml', sch],
        ['sch', 'erc', '--format', 'json', '--severity-all', '-o', nr + '/erc.json', sch],
        ['sch', 'export', 'svg', '-o', nr + '/svg/', sch],
    ]
    version = subprocess.run([CLI, 'version'], cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', errors='replace')
    require(version.returncode == 0 and version.stdout.strip() == '9.0.7',
            'Unexpected native KiCad version')
    report = {
        'revision': REV,
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'kicad_version': version.stdout.strip(),
        'version_command': {'argv': [CLI, 'version'], 'returncode': version.returncode,
                            'stdout': version.stdout, 'stderr': version.stderr},
        'runner_sha256': sha(Path(__file__)),
        'expected_contract_sha256': sha(P / 'expected_contract.json'),
        'population_contract_sha256': sha(P / 'population_contract.json'),
        'input_sha256': built['output_sha256'],
        'commands': []
    }
    for command in commands:
        result = subprocess.run([CLI] + command, cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        report['commands'].append({'argv': [CLI] + command, 'returncode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr})
        require(result.returncode == 0, result.stderr or result.stdout)
    check_map(built['output_sha256'])
    check_map(inputs['input_sha256'])
    check_map(built['baseline_source_sha256'])
    require(report['expected_contract_sha256'] == sha(P / 'expected_contract.json'),
            'Contract changed during capture')
    require(report['population_contract_sha256'] == sha(P / 'population_contract.json'),
            'Population changed during capture')
    report['inputs_unchanged_after_commands'] = True
    report['output_sha256'] = mapping(out)
    tree = ET.parse(out / 'netlist.xml')
    counts = {'components': len(tree.findall('./components/comp')),
              'physical_pins': len(tree.findall('./nets/net/node')),
              'nets': len(tree.findall('./nets/net')),
              'sheets': len(tree.findall('./design/sheet'))}
    expected = {'components': contract['expected_component_count'],
                'physical_pins': contract['expected_physical_pin_count'],
                'nets': contract['expected_net_count'],
                'sheets': contract['expected_sheet_count']}
    report['expected_counts'] = expected
    report['actual_counts'] = counts
    erc = read(out / 'erc.json')
    violations = [v for s in erc['sheets'] for v in s['violations']]
    report['erc_summary'] = {severity: sum(v['severity'] == severity for v in violations)
                             for severity in ['error', 'warning']}
    report['svg_sheet_count'] = len(list((out / 'svg').glob('*.svg')))
    write(P / 'native_manifest.json', report)
    require(counts == expected, 'Native counts differ from frozen contract: ' + str(counts))
    require(len(report['output_sha256']) == 13 and report['svg_sheet_count'] == 11,
            'Unexpected native output coverage')
    require(report['erc_summary'] == {'error': 0, 'warning': 1} and 'AD0' in str(violations),
            'Unexpected ERC findings')
    print('Captured native 9.0.7:', counts, report['erc_summary'], '11 SVG sheets; source hashes stable')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    if not (args.build or args.native):
        parser.error('Choose --build and/or --native explicitly')
    if args.build:
        build()
    if args.native:
        native()

