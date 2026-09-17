"""Reject incorrect pin mappings and stale CAD evidence before compilation."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("v2_build", ROOT / "firmware_v2/tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ContractTests(unittest.TestCase):
    def setUp(self):
        parent = (ROOT / "firmware_v2/build").resolve()
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="pin-test-", dir=parent)
        self.root = Path(self.temp.name).resolve()
        # The context cleanup is restricted to this verified task directory.
        assert self.root.parent == parent and self.root.name.startswith("pin-test-")
        self.addCleanup(self.temp.cleanup)
        self.contract = json.loads((ROOT / "firmware_v2/board_contract.json").read_text())
        report = json.loads((ROOT / self.contract["schematic_evidence"]).read_text())
        paths = {"firmware_v2/board_contract.json", self.contract["schematic_evidence"], self.contract["netlist"]}
        paths.update(p for p in report["input_manifest"] if p.startswith("hardware/kicad_v2/") and p.endswith((".kicad_sch", ".kicad_sym")))
        for p in paths:
            target = self.root / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, target)

    def save_contract(self):
        (self.root / "firmware_v2/board_contract.json").write_text(json.dumps(self.contract))

    def test_valid_contract(self):
        self.assertEqual(len(build.pin_contract(self.root)[0]["pins"]), 7)

    def test_wrong_pad(self):
        self.contract["pins"]["ESC"]["pad"] = "41"
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "does not match"):
            build.pin_contract(self.root)

    def test_wrong_connector_peer(self):
        self.contract["pins"]["SWDIO"]["peer"] = ["J7", "4"]
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "does not match"):
            build.pin_contract(self.root)

    def test_changed_schematic(self):
        p = self.root / "hardware/kicad_v2/MCU.kicad_sch"
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Schematic changed"):
            build.pin_contract(self.root)

    def test_changed_export(self):
        p = self.root / self.contract["netlist"]
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "netlist differs"):
            build.pin_contract(self.root)

    def test_missing_output(self):
        del self.contract["pins"]["SERVO"]
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "GPIO set changed"):
            build.pin_contract(self.root)

    def test_wrong_target(self):
        self.contract["target"] = "STM32F103C8T6"
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "STM32F446RET6"):
            build.pin_contract(self.root)

    def test_wrong_schema(self):
        self.contract["schema"] = 2
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "schema 1"):
            build.pin_contract(self.root)

    def test_swd_output_mode(self):
        self.contract["pins"]["SWDIO"]["mode"] = "output_low"
        self.save_contract()
        with self.assertRaisesRegex(ValueError, "pin modes changed"):
            build.pin_contract(self.root)


if __name__ == "__main__":
    unittest.main()
