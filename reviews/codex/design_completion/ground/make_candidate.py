"""Deterministic two-via correction candidate; never writes the live board."""
from pathlib import Path
import hashlib
import json
import shutil
import uuid
import pcbnew
from inspect_ground import BOARD, OUT, ROOT

SOURCE_SHA256 = '6595d3b58e4a54b1d3ecbf93a69c93202503dbabcf9d279a6a578df1601d0d26'
SITES = [(93.7, 74.0), (108.0, 59.0)]
DEST = OUT / 'candidate'

def main():
    actual = hashlib.sha256(BOARD.read_bytes()).hexdigest()
    if actual != SOURCE_SHA256:
        raise SystemExit('Source PCB changed; rerun independent localization before producing a candidate.')
    DEST.mkdir(exist_ok=True)
    pcbnew.KIID.SeedGenerator(20260917)
    b = pcbnew.LoadBoard(str(BOARD))
    ground = b.GetNetcodeFromNetname('GND')
    changes = []
    stable_ids = {}
    for x, y in SITES:
        via = pcbnew.PCB_VIA(b)
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'https://github.com/SpaceCadetJ/LoRa-Autonomous-Boat/ground-review/{x:.1f}/{y:.1f}'))
        stable_ids[via.m_Uuid.AsString()] = uid
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetWidth(pcbnew.FromMM(.6)); via.SetDrill(pcbnew.FromMM(.3)); via.SetNetCode(ground)
        b.Add(via)
        changes.append({'type': 'through_via', 'net': 'GND', 'position_mm': [x, y], 'diameter_mm': .6,
                        'drill_mm': .3, 'layers': ['F.Cu', 'B.Cu'], 'uuid': uid})
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    dest_board = DEST / BOARD.name
    pcbnew.SaveBoard(str(dest_board), b)
    contents = dest_board.read_bytes()
    for temporary, stable in stable_ids.items():
        if contents.count(temporary.encode()) != 1:
            raise RuntimeError('Expected exactly one newly added via UUID in serialized candidate')
        contents = contents.replace(temporary.encode(), stable.encode())
    dest_board.write_bytes(contents)
    # Preserve the source project rules and libraries for an equivalent native DRC.
    for source in BOARD.parent.iterdir():
        if source.suffix in ('.kicad_pro', '.kicad_sym', '.kicad_sch', '.kicad_dru') or source.name in ('fp-lib-table', 'sym-lib-table'):
            shutil.copyfile(source, DEST / source.name)
        elif source.is_dir() and source.suffix == '.pretty':
            shutil.copytree(source, DEST / source.name, dirs_exist_ok=True)
    # The unmodified V2 library tables also refer to the sibling V1 conversion library.
    v1_lib_dir = BOARD.parent.parent / 'kicad'
    sibling = OUT / 'kicad'
    sibling.mkdir(exist_ok=True)
    shutil.copytree(v1_lib_dir / 'LoRa_Boat_Controller.pretty', sibling / 'LoRa_Boat_Controller.pretty', dirs_exist_ok=True)
    shutil.copyfile(v1_lib_dir / 'LoRa_Boat_Controller.kicad_sym', sibling / 'LoRa_Boat_Controller.kicad_sym')
    report = {'source': BOARD.relative_to(ROOT).as_posix(), 'source_sha256': actual, 'candidate_sha256': hashlib.sha256(dest_board.read_bytes()).hexdigest(),
              'changes': changes, 'native_unconnected_count_after_refill': b.GetConnectivity().GetUnconnectedCount(True),
              'fabrication_approved': False}
    (OUT / 'candidate_manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
