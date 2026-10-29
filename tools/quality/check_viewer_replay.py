"""Replay immutable packet outputs against their own captured viewer templates.

Default/--check also requires the latest packet's snapshot to match the live PM
source. Historical templates are exact Git blobs whose SHA-256 matches the old
viewer record. Every other input remains checked at its original repository path.
No files, hash functions or historical modules are modified. Native commands and
browser tests are not rerun; those results remain captured evidence.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).with_name('viewer_replay.json')
PM_TEMPLATE = 'pm/index.template.html'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_id(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def resolve(name):
    require(isinstance(name, str) and not Path(name).is_absolute(), 'Expected repository-relative path')
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT), 'Path escapes repository: ' + name)
    return path


def read_bytes(name):
    return resolve(name).read_bytes()


def read_json(name):
    return json.loads(read_bytes(name).decode('utf-8-sig'))


def validate_hashes(entries, loader=read_bytes):
    require(isinstance(entries, dict) and bool(entries), 'Empty hash mapping')
    for name, expected in entries.items():
        require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected), 'Invalid digest: ' + name)
        require(digest(loader(name)) == expected, 'Hash mismatch: ' + name)


def validate_viewer(record, snapshot, loader=read_bytes, live_template=None):
    """The only path substitution is explicit, byte-checked historical PM evidence."""
    entries = record['input_sha256']
    require(PM_TEMPLATE in entries, 'Viewer record omits PM template')
    require(digest(snapshot) == entries[PM_TEMPLATE], 'Archived PM template differs from viewer record')
    for name, expected in entries.items():
        data = snapshot if name == PM_TEMPLATE else loader(name)
        require(digest(data) == expected, 'Viewer input mismatch: ' + name)
    if live_template is not None:
        require(digest(live_template) == entries[PM_TEMPLATE], 'Current PM template differs from latest viewer capture')


def validate_archive(entry, record, loader=read_bytes):
    snapshot = loader(entry['template_snapshot'])
    require(digest(snapshot) == entry['template_sha256'], 'Archived template SHA-256 differs')
    require(git_blob_id(snapshot) == entry['template_git_blob'], 'Archived template Git blob identity differs')
    validate_viewer(record, snapshot, loader)
    return snapshot


def registry():
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    require(data['schema'] == 1, 'Unknown replay registry schema')
    packets = [entry['packet'] for entry in data['historical_packets']]
    require(len(packets) == len(set(packets)) and bool(packets), 'Duplicate or empty historical packet list')
    require(data['current_packet']['packet'] not in packets, 'Current packet must not be historical')
    for entry in data['historical_packets']:
        require(entry['analysis_api'] in ['collect', 'artifact'], 'Unsupported analysis API')
        require(entry['template_source_path'] == PM_TEMPLATE, 'Only shared PM template may be archived')
        require(re.fullmatch(r'[0-9a-f]{40}', entry['template_source_commit']), 'Invalid source commit')
        require(re.fullmatch(r'[0-9a-f]{40}', entry['template_git_blob']), 'Invalid source blob')
        resolve(entry['packet']); resolve(entry['template_snapshot'])
    return data


def check_packet_hashes(entry):
    packet = resolve(entry['packet'])
    manifest_path = entry['packet'] + '/packet_manifest.json'
    require(digest(read_bytes(manifest_path)) == entry['packet_manifest_sha256'], 'Historical manifest anchor changed: ' + entry['packet'])
    manifest = read_json(manifest_path)
    inputs = read_json(entry['packet'] + '/input_manifest.json')
    require(manifest['input_sha256'] == inputs['input_sha256'], 'Input manifest coverage differs')
    require(manifest['source_revision'] == inputs.get('baseline_head', inputs.get('source_revision')), 'Source revision differs')
    require(manifest['revision'] == entry['revision'], 'Packet revision differs')
    actual_files = {path.relative_to(ROOT).as_posix() for path in packet.rglob('*')
                    if path.is_file() and path.name != 'packet_manifest.json' and '__pycache__' not in path.parts}
    require(set(manifest['artifact_sha256']) == actual_files, 'Historical artifact coverage differs: ' + entry['packet'])
    validate_hashes(manifest['input_sha256'])
    validate_hashes(manifest['artifact_sha256'])
    notes = read_json(entry['packet'] + '/review_notes.json')
    if 'reviewed_sha256' in notes:
        validate_hashes({entry['packet'] + '/' + name: sha for name, sha in notes['reviewed_sha256'].items()})
    return manifest


def replay_outputs(entry):
    """Worker only: one fresh process prevents historical generic `model` imports colliding."""
    packet = resolve(entry['packet'])
    sys.path.insert(0, str(packet))
    spec = importlib.util.spec_from_file_location('immutable_packet_builder', packet / 'build_packet.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    if hasattr(builder, 'check_inputs'):
        builder.check_inputs()
    if hasattr(builder, 'preserved'):
        builder.preserved()
    analysis = builder.artifact(packet / 'contract.json') if entry['analysis_api'] == 'artifact' else builder.collect()
    require(read_json(entry['packet'] + '/analysis.json') == analysis, 'Historical analysis differs: ' + entry['packet'])
    outputs = builder.outputs(analysis)
    require(isinstance(outputs, dict) and bool(outputs), 'Empty deterministic output set')
    for name, text in outputs.items():
        path = (packet / name).resolve()
        require(path.is_relative_to(packet), 'Output path escapes packet')
        require(path.read_text(encoding='utf-8') == text, 'Historical deterministic output differs: ' + name)
    return {'packet': entry['packet'], 'analysis_api': entry['analysis_api'], 'outputs': sorted(outputs), 'status': 'pass'}


def historical(entry):
    manifest = check_packet_hashes(entry)
    snapshot = validate_archive(entry, read_json(entry['packet'] + '/viewer_check.json'))
    result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', entry['packet']],
                            cwd=ROOT, text=True, encoding='utf-8', capture_output=True, check=False)
    require(result.returncode == 0, 'Replay failed: ' + entry['packet'] + '\n' + result.stdout + result.stderr)
    replay = json.loads(result.stdout)
    require(replay['status'] == 'pass' and replay['packet'] == entry['packet'], 'Unexpected worker result')
    # Recheck immutable sources after importing and calculating; concurrent edits fail.
    check_packet_hashes(entry)
    require(read_bytes(entry['template_snapshot']) == snapshot, 'Archived template changed during replay')
    return {'revision': entry['revision'], 'input_count': len(manifest['input_sha256']),
            'artifact_count': len(manifest['artifact_sha256']), 'output_count': len(replay['outputs'])}


def current(entry):
    snapshot = read_bytes(entry['template_snapshot'])
    record = read_json(entry['packet'] + '/viewer_check.json')
    validate_viewer(record, snapshot, live_template=read_bytes(PM_TEMPLATE))
    return {'packet': entry['packet'], 'viewer_input_count': len(record['input_sha256']), 'live_template_matches_capture': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Check historical replay and current PM snapshot; default')
    mode.add_argument('--historical-only', action='store_true', help='Check historical packets while a new viewer capture is pending')
    mode.add_argument('--worker', metavar='PACKET', help=argparse.SUPPRESS)
    args = parser.parse_args()
    data = registry()
    if args.worker:
        entries = [entry for entry in data['historical_packets'] if entry['packet'] == args.worker]
        require(len(entries) == 1, 'Worker packet is not registered')
        print(json.dumps(replay_outputs(entries[0])))
        return
    for entry in data['historical_packets']:
        result = historical(entry)
        print('PASS {revision}: {input_count} input hashes, {artifact_count} artifact hashes, {output_count} deterministic outputs, exact archived viewer inputs'.format(**result))
    if not args.historical_only:
        result = current(data['current_packet'])
        print('PASS current viewer: {packet}; {viewer_input_count} inputs and live PM template match capture'.format(**result))
    print('Scope: portable immutable replay and captured browser provenance; no native, browser or hardware rerun.')


if __name__ == '__main__':
    main()
