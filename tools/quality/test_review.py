"""Behavioral tests: reject electrical changes, known DRC blockers and false QA passes."""
import copy
from pathlib import Path
import tempfile
import unittest
from review import (allowed_review_output, canonical_netlist, compare_netlists, coordinate_bounds,
                    evaluate_gates, sha256, snapshot_inputs, summarize_drc, summarize_erc)


class SnapshotTests(unittest.TestCase):
    def test_active_cad_and_libraries_preserved_without_local_backups_or_sessions(self):
        active = ["Controller.kicad_sch", "Controller.kicad_pcb", "Controller.kicad_pro",
                  "Controller.kicad_dru", "Controller.kicad_sym", "fp-lib-table", "sym-lib-table",
                  "Controller.pretty/Backup_Connector.kicad_mod", "hierarchy/Child.kicad_sch"]
        excluded = ["_backup_2026-09-16/Controller.kicad_pcb", "_BACKUP_old/Controller.kicad_sch",
                    "Controller-backups/Controller.kicad_sch", "backups/Old.kicad_sch",
                    "_build/Generated.kicad_pcb", "tools/Fixture.kicad_sch", "cache/Old.kicad_sym",
                    ".cache/Old.kicad_sch", "__pycache__/Old.kicad_sch", "Controller.kicad_prl",
                    "Controller.kicad_sch-bak", "Controller.kicad_pcb-bak", "Controller.lck",
                    "_autosave-Controller.kicad_sch", "~Controller.kicad_sch"]
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            project = repo / "hardware/kicad"
            for name in active + excluded:
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((name + "\r\n").encode())
            out = repo / "reviews/codex/publication/test"
            manifest, unstable = snapshot_inputs(repo, out)
            expected = {"hardware/kicad/" + name for name in active}
            self.assertEqual(set(manifest), expected)
            self.assertEqual(unstable, [])
            self.assertEqual({p.relative_to(out / "inputs").as_posix()
                              for p in (out / "inputs").rglob("*") if p.is_file()}, expected)
            for relative, digest in manifest.items():
                self.assertEqual((out / "inputs" / relative).read_bytes(), (repo / relative).read_bytes())
                self.assertEqual(digest, sha256(repo / relative))

    def test_output_locations_remain_narrowly_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            for allowed in ("reviews/codex/professionalization/new-review", "reviews/codex/publication/native-review"):
                self.assertTrue(allowed_review_output(repo, repo / allowed))
            for forbidden in ("hardware/kicad", "reviews/codex/publication", "reviews/codex/professionalization", "reviews/other"):
                self.assertFalse(allowed_review_output(repo, repo / forbidden))


class ConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.before = {"components": {"U1": {"value": "MCU", "footprint": "LQFP"}},
                       "pin_groups": [[["U1", "1"], ["U1", "2"]], [["U1", "3"]]],
                       "net_names": {'[["U1","1"],["U1","2"]]': "GND", '[["U1","3"]]': "unconnected-old"}, "pin_count": 3}

    def test_cosmetic_net_name_change_preserves_topology_but_is_reported(self):
        after = copy.deepcopy(self.before)
        after["net_names"]['[["U1","3"]]'] = "unconnected-new"
        result = compare_netlists(self.before, after)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["net_name_changes"]), 1)

    def test_rewired_pin_rejected(self):
        after = copy.deepcopy(self.before)
        after["pin_groups"] = [[["U1", "1"], ["U1", "3"]], [["U1", "2"]]]
        after["net_names"] = {'[["U1","1"],["U1","3"]]': "GND", '[["U1","2"]]': "unconnected"}
        self.assertFalse(compare_netlists(self.before, after)["passed"])

    def test_dropped_isolated_pin_rejected(self):
        after = copy.deepcopy(self.before)
        after["pin_groups"].pop()
        self.assertFalse(compare_netlists(self.before, after)["passed"])

    def test_component_substitution_rejected(self):
        after = copy.deepcopy(self.before)
        after["components"]["U1"]["value"] = "DIFFERENT_MCU"
        self.assertFalse(compare_netlists(self.before, after)["passed"])

    def test_duplicate_physical_pin_rejected(self):
        xml = '<export><components><comp ref="U1"><value>MCU</value></comp></components><nets><net name="A"><node ref="U1" pin="1"/></net><net name="B"><node ref="U1" pin="1"/><node ref="U1" pin="2"/></net></nets></export>'
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "net.xml"
            p.write_text(xml)
            with self.assertRaisesRegex(ValueError, "Repeated physical pins"):
                canonical_netlist(p)


class AcceptanceTests(unittest.TestCase):
    def test_review_can_pass_with_fabrication_blocked(self):
        checks = [{"gate": "both", "passed": True}, {"gate": "fabrication", "passed": False}]
        self.assertEqual(evaluate_gates(checks), {"review": True, "fabrication": False})

    def test_incomplete_check_fails_both_profiles(self):
        checks = [{"gate": "both", "passed": False}, {"gate": "fabrication", "passed": True}]
        self.assertEqual(evaluate_gates(checks), {"review": False, "fabrication": False})

    def test_unconnected_board_fails_without_drc_error_entry(self):
        report = {"violations": [], "unconnected_items": [{"severity": "error"}], "schematic_parity": []}
        self.assertFalse(summarize_drc(report)["passed"])

    def test_parity_warnings_cannot_be_hidden_by_zero_errors(self):
        report = {"violations": [], "unconnected_items": [], "schematic_parity": [{"severity": "warning"}]}
        self.assertFalse(summarize_drc(report)["passed"])

    def test_warning_only_erc_is_not_clean(self):
        self.assertFalse(summarize_erc({"sheets": [{"violations": [{"severity": "warning"}]}]})["passed"])

    def test_missing_report_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            summarize_drc({"violations": []})

    def test_no_checks_is_not_a_pass(self):
        self.assertEqual(evaluate_gates([]), {"review": False, "fabrication": False})


class BoundsTests(unittest.TestCase):
    def bounds(self, text):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "test.kicad_sch"
            p.write_text(text)
            return coordinate_bounds(p)

    def test_off_page_wire_rejected(self):
        result = self.bounds('(kicad_sch (paper "A4") (wire (pts (xy 280 20) (xy 320 20))))')
        self.assertFalse(result["passed"])
        self.assertEqual(result["outside"][0]["x_mm"], 320)

    def test_local_library_symbol_coordinates_not_page_coordinates(self):
        result = self.bounds('(kicad_sch (paper "A4") (lib_symbols (symbol "lib" (at -100 -100))) (symbol (at 20 20)))')
        self.assertTrue(result["passed"])

    def test_textbox_extent_not_only_anchor_is_checked(self):
        result = self.bounds('(kicad_sch (paper "A4") (text_box "note" (at 290 20) (size 20 10)))')
        self.assertFalse(result["passed"])

    def test_portrait_dimensions(self):
        result = self.bounds('(kicad_sch (paper "A4" portrait) (text "note" (at 220 20)))')
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
