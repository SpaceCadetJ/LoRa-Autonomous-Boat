"""Replay POWER-DOC-01 with its exact captured PM template and builder.

The old packet remains byte-identical. All source, artifact, review and browser
input hashes are checked, then the unchanged native-equivalence and comparison
viewer functions are replayed. No Git, native tools, browser or writes are used.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
PACKET = 'reviews/codex/power_sheet_polish'
ARCHIVE_PATHS = {
    'pm/index.template.html': PACKET + '/viewer-template.snapshot.html',
    'pm/tools/build.mjs': 'reviews/codex/vservo_shunt_spec/historical-power-build.snapshot.mjs',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_id(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def resolve(name):
    require(isinstance(name, str) and not Path(name).is_absolute(), 'Expected relative repository path')
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT), 'Path escapes repository: ' + name)
    return path


def load(name):
    return resolve(name).read_bytes()


def read(name):
    return json.loads(load(name).decode('utf-8-sig'))


def check_hashes(entries, loader=load):
    require(isinstance(entries, dict) and bool(entries), 'Empty hash map')
    for name, expected in entries.items():
        require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected), 'Invalid SHA-256: ' + name)
        require(digest(loader(name)) == expected, 'Hash mismatch: ' + name)


def anchored_manifest(data, expected):
    require(digest(data) == expected, 'Historical manifest anchor changed')
    return json.loads(data.decode('utf-8-sig'))


def check_coverage(entries, actual):
    require(set(entries) == set(actual), 'Historical artifact coverage differs')


def validate_archives(entries, record, loader=load):
    require(set(entries) == set(ARCHIVE_PATHS), 'Only the two recorded shared PM inputs may be archived')
    inputs = record['input_sha256']
    require(set(ARCHIVE_PATHS) <= set(inputs), 'Viewer record omits an archived PM input')
    saved = {}
    for target, entry in entries.items():
        require(entry['source_path'] == target, 'Archive source target differs: ' + target)
        require(entry['snapshot'] == ARCHIVE_PATHS[target], 'Archive snapshot target differs: ' + target)
        require(re.fullmatch(r'[0-9a-f]{40}', entry['source_commit']) is not None, 'Invalid archive source commit')
        data = loader(entry['snapshot'])
        require(digest(data) == entry['sha256'], 'Archived SHA-256 differs: ' + target)
        require(git_blob_id(data) == entry['git_blob'], 'Archived Git blob differs: ' + target)
        require(digest(data) == inputs[target], 'Archive differs from viewer capture: ' + target)
        saved[target] = data
    for name, expected in inputs.items():
        data = saved[name] if name in saved else loader(name)
        require(digest(data) == expected, 'Viewer input mismatch: ' + name)
    return saved


def registry():
    data = json.loads((P / 'historical_power_viewer.json').read_text(encoding='utf-8'))
    require(data['schema'] == 1 and data['revision'] == 'POWER-DOC-01' and data['packet'] == PACKET, 'Registry packet changed')
    require(data['expected_input_count'] == 456 and data['expected_artifact_count'] == 75 and data['expected_viewer_input_count'] == 13, 'Registry evidence counts changed')
    require(re.fullmatch(r'[0-9a-f]{40}', data['source_commit']) is not None, 'Invalid source commit')
    require(all(a['source_commit'] == data['source_commit'] for a in data['archives'].values()), 'Archive source commits differ')
    return data


def check_manifest(entry):
    manifest = anchored_manifest(load(PACKET + '/packet_manifest.json'), entry['packet_manifest_sha256'])
    inputs = read(PACKET + '/input_manifest.json')
    require(manifest['revision'] == 'POWER-DOC-01' and manifest['electrical_candidate'] == 'VSERVO-01', 'Historical revision changed')
    require(manifest['input_sha256'] == inputs['input_sha256'], 'Input manifest coverage differs')
    require(manifest['source_revision'] == inputs['baseline_head'], 'Input source revision differs')
    require(len(manifest['input_sha256']) == 456 and len(manifest['artifact_sha256']) == 75, 'Historical evidence count changed')
    actual = {f.relative_to(ROOT).as_posix() for f in resolve(PACKET).rglob('*')
              if f.is_file() and f != resolve(PACKET + '/packet_manifest.json') and '__pycache__' not in f.parts}
    check_coverage(manifest['artifact_sha256'], actual)
    check_hashes(manifest['input_sha256'])
    check_hashes(manifest['artifact_sha256'])
    check_hashes(read(PACKET + '/review_notes.json')['reviewed_sha256'])
    require(all(manifest[k] == 0 for k in ['candidate_electrical_delta', 'live_electrical_delta', 'live_copper_delta']), 'Historical electrical delta changed')
    require(all(manifest[k] is False for k in ['hardware_accepted', 'fabrication_approved', 'procurement_approved', 'protection_qualified', 'qualification_ports_implemented']), 'Historical acceptance changed')
    require(manifest['native_commands_rerun'] is True, 'Historical recorded native scope changed')
    return manifest


def import_immutable(name, path):
    spec = importlib.util.spec_from_file_location(name, resolve(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replay():
    entry = registry()
    manifest = check_manifest(entry)
    viewer = read(PACKET + '/viewer_check.json')
    require(len(viewer['input_sha256']) == 13, 'Historical viewer input coverage changed')
    saved = validate_archives(entry['archives'], viewer)
    native = import_immutable('immutable_power_doc01_native_equivalence', PACKET + '/verify_packet.py')
    require(native.collect() == read(PACKET + '/validation.json'), 'Historical native equivalence differs')
    comparison = import_immutable('immutable_power_doc01_view_output', PACKET + '/build_view.py')
    require(comparison.output() == load(PACKET + '/index.html').decode('utf-8'), 'Historical comparison viewer differs')
    # Close the check against concurrent edits after executing the original functions.
    require(registry() == entry, 'Replay registry changed during check')
    require(check_manifest(entry) == manifest, 'Historical manifest changed during replay')
    require(validate_archives(entry['archives'], read(PACKET + '/viewer_check.json')) == saved, 'Archived inputs changed during replay')
    return {'revision': 'POWER-DOC-01', 'input_hashes': 456, 'artifact_hashes': 75,
            'viewer_input_hashes': 13, 'deterministic_outputs': 2, 'archived_pm_inputs': 2,
            'native_commands_rerun': False, 'browser_checks_rerun': False, 'hardware_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Replay captured evidence; also the default')
    parser.parse_args()
    result = replay()
    print('PASS POWER-DOC-01: {input_hashes} inputs, {artifact_hashes} artifacts, {viewer_input_hashes} viewer inputs, {deterministic_outputs} deterministic outputs; exact historical template and builder'.format(**result))
    print('Scope: immutable captured evidence only; no fresh native, browser or hardware execution.')


if __name__ == '__main__':
    main()
