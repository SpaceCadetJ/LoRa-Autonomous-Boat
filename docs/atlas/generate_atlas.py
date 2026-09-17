"""Generate the V1 connector atlas from source snapshots (standard library only).

Run from any directory with Python 3.10+: python docs/atlas/generate_atlas.py
Use --check to verify committed/generated outputs against the current sources.
Writes only docs/atlas/*.md and pm/data/connectors.json. Never imports CAD tools.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PST = "Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat"
MAP = "hardware/kicad/_build/netmap.json"
BOM = "docs/BOM.csv"
XML = "hardware/kicad/_build/netlist.xml"
MAIN = "firmware/Core/Src/main.c"
MSP = "firmware/Core/Src/stm32f4xx_hal_msp.c"
IOC = "firmware/BoatTHISTIMEITSDIFFERENT.ioc"
DS = "docs/research/DATASHEET_NOTES.md"
SELF = "docs/atlas/generate_atlas.py"
INPUTS = (PST, MAP, BOM, XML, MAIN, MSP, IOC, DS, SELF)
RAW = {p: (ROOT / p).read_bytes() for p in INPUTS}
TEXT = {p: raw.decode("utf-8-sig") for p, raw in RAW.items()}
MANIFEST = [{"path": p, "sha256": hashlib.sha256(RAW[p]).hexdigest(), "bytes": len(RAW[p])} for p in INPUTS]


def evidence(path, needle):
    index = TEXT[path].find(needle)
    if index < 0:
        raise ValueError(f"Reviewed evidence no longer matches {path}: {needle!r}; review before regenerating")
    return {"path": path, "line": TEXT[path].count("\n", 0, index) + 1}


def cite(item):
    return f"[{item['path']}:{item['line']}](../../{item['path'].replace(' ', '%20')}#L{item['line']})"


def ev(path, needle):
    return cite(evidence(path, needle))


def parse_pst():
    nets = {}
    for match in re.finditer(r"(?m)^NET_NAME\s*\n'([^\n]+)'\s*\n([\s\S]*?)(?=^NET_NAME|^END\.|\Z)", TEXT[PST]):
        name, body = match.groups()
        nodes = []
        for node in re.finditer(r"(?m)^NODE_NAME\s+(\S+)\s+(\d+)\s*\n[^\n]*\n\s*'([^']*)'", body):
            ref, raw_pin, label = node.groups()
            nodes.append({"ref": ref, "pin": str(int(raw_pin)), "allegro_pin": raw_pin, "label": label,
                          "line": TEXT[PST].count("\n", 0, match.start(2) + node.start()) + 1})
        assert nodes, f"Unparsed net {name}"
        nets[name] = nodes
    assert len(nets) == len(re.findall(r"(?m)^NET_NAME\s*$", TEXT[PST]))
    assert sum(map(len, nets.values())) == len(re.findall(r"(?m)^NODE_NAME\s", TEXT[PST]))
    return nets


NETS = parse_pst()
NETMAP = json.loads(TEXT[MAP])
BOMS = {r["Allegro_RefDes"]: r for r in csv.DictReader(io.StringIO(TEXT[BOM]))}
KREF = {r["Ref"]: a for a, r in BOMS.items()}
XML_NETS = {}
for net in ET.fromstring(TEXT[XML]).find("nets"):
    members = frozenset((KREF[n.get("ref")], str(int(n.get("pin")))) for n in net.findall("node"))
    XML_NETS[members] = net.get("name")

# Guard reviewed behavioral claims: changed firmware needs renewed human/agent review.
for token in ["__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, pulse)",
              "__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pulse)",
              "HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET)",
              "huart4.Init.BaudRate   = 115200", "huart3.Init.BaudRate   = 9600",
              "#define PWM_MOTOR_MIN_US     1000U", "#define PWM_MOTOR_MAX_US     2000U",
              "#define PWM_RUDDER_CENTER_US 1500U", "#define PWM_RUDDER_LEFT_US   1100U",
              "#define PWM_RUDDER_RIGHT_US  1900U", "sConfigOC.Pulse      = PWM_MOTOR_IDLE_US",
              "if (gps_valid && (now - last_lora_tx >= 5000U))"]:
    evidence(MAIN, token)
assert len(re.findall(r"\bHAL_GetTick\s*\(", TEXT[MAIN])) == 1, "Re-review link-loss behavior before regeneration"
assert "MX_CAN" not in TEXT[MAIN], "Re-review CAN implementation"
assert "GPIO_PIN_3" not in TEXT[MAIN], "Re-review LoRa reset configuration"
evidence(IOC, "TIM3.Pulse-PWM\\ Generation1\\ CH1=1500")

COMMON = "Electrical pin numbers below come from v5 pstxnet.dat, not a physical left-to-right view. Board side, connector key, cable view, and pin-1 marking require physical verification. All voltages and waveforms are design/code expectations, not bench measurements."
ACTUATOR = "V1 connector names conflict with firmware roles: SPEEDCONTROLLER pin 2 carries the firmware rudder waveform; STEERINGSERVO pin 2 carries the firmware thrust waveform. Treat both as electrical identities until harness labels and physical continuity are verified."
POWER = "Pin 1 is on the board +3V3 rail. ESC/BEC/servo external power compatibility and current budget are unverified; this is not a certified actuator power port."

# net: firmware role, voltage, direction relative to board, bench observation, evidence anchors
SPEC = {
    "GND": ("Common reference", "0 V reference (expected)", "Reference", "Unpowered continuity to GND1/TP5; resistance/continuity has not been measured.", []),
    "+3V3": ("Board supply / debug voltage reference", "3.3 V nominal (unmeasured)", "Board rail; external powering unsupported until reviewed", "Measure rail relative to TP5 with loads disconnected after V1 power defects are reviewed.", []),
    "LORA_VCC": ("LoRa supply through L3", "Derived from +3V3; actual voltage unmeasured", "Board → module supply", "Unpowered continuity through L3 to +3V3; identify module before powering.", []),
    "LORA_TX_PA0": ("UART4 TX; AT commands at 115200 baud, 8N1", "3.3 V logic domain; module tolerance unverified", "MCU → LoRa RX", "Logic analyzer: expect AT commands at startup. Read module replies to establish accepted settings.", [(MAIN, "huart4.Init.BaudRate   = 115200"), (MSP, "PA0-WKUP     ------> UART4_TX")]),
    "LORA_RX_PA1": ("UART4 RX; +RCV line parser", "Module TX level must be verified", "LoRa TX → MCU", "Capture startup replies and +RCV traffic at 115200 baud, 8N1; no capture exists in this atlas.", [(MAIN, "huart4.Init.BaudRate   = 115200"), (MAIN, "/* Parse one LoRa line"), (MSP, "PA1     ------> UART4_RX")]),
    "LORA_RST_PA3": ("Wired to PA3; no PA3 reset GPIO configuration in this firmware snapshot", "Reset polarity/level needs module identification", "Intended MCU → module reset; unconfigured", "Confirm module reset pin and pull network; do not assume this firmware can reset the radio.", [(MAIN, "static void MX_GPIO_Init(void)\n{")]),
    "GPS_PB0": ("PB0 is a push-pull output held LOW, described as debug LED/probe", "0 V expected after GPIO init (unmeasured)", "MCU → attached GPS pin 3; external function unknown", "Identify GPS module pin 3 before attachment; possible output contention if that module drives this pin.", [(MAIN, "HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET)")]),
    "GPS_RX_PC11": ("USART3 RX; $GPRMC/$GNRMC parsing at 9600 baud, 8N1", "GPS TX level unverified", "GPS TX → MCU", "Capture NMEA lines and verify actual GPS baud rate/logic levels.", [(MAIN, "huart3.Init.BaudRate   = 9600"), (MSP, "PC11     ------> USART3_RX")]),
    "GPS_TX_PC10": ("USART3 TX; debug strings share the GPS UART", "3.3 V logic domain; module tolerance unverified", "MCU → GPS RX", "Capture transmitted debug text; determine whether the connected GPS interprets or rejects it.", [(MAIN, "HAL_UART_Transmit(&huart3"), (MSP, "PC10     ------> USART3_TX")]),
    "PWM_PA8_ESCHDR": ("TIM1_CH1 / set_rudder(): 1100–1900 us; startup 1500 us", "3.3 V logic; load compatibility unverified", "MCU → header / TP1", "Expected 50 Hz, 1500 us after startup; source name says ESC but firmware role is rudder. Scope with actuators disconnected.", [(MAIN, "__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pulse)"), (MSP, "PA8     ------> TIM1_CH1"), (MAIN, "sConfigOC.Pulse        = PWM_RUDDER_CENTER_US")]),
    "PWM_PC6_SERVOHDR": ("TIM3_CH1 / set_thrust(): 1000–2000 us; C startup 1000 us", "3.3 V logic; load compatibility unverified", "MCU → header / TP3", "Expected 50 Hz, 1000 us after C startup. CubeMX .ioc instead specifies 1500 us. Scope with actuators disconnected.", [(MAIN, "__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, pulse)"), (MSP, "PC6     ------> TIM3_CH1"), (MAIN, "sConfigOC.Pulse      = PWM_MOTOR_IDLE_US"), (IOC, "TIM3.Pulse-PWM\\ Generation1\\ CH1=1500")]),
    "CAN_VCC": ("No CAN initialization; transceiver supply net connects header to U5-3 and C1-2", "External supply unidentified; TCAN1042H needs 4.5–5.5 V", "External connector → CAN supply (source unresolved)", "Confirm supply source and polarity. This net is separate from +3V3 and VIN_RAW in v5.", [(DS, "VCC range: 4.5–5.5 V")]),
    "CANH": ("Bus line to U5-7; CAN firmware not implemented", "Differential CAN bus; not a TTL UART pin", "Bidirectional bus via U5", "Check continuity header pin 3 → U5-7 and external termination; no working bus is claimed.", [(DS, "6 CANL, 7 CANH")]),
    "CANL": ("Bus line to U5-6; CAN firmware not implemented", "Differential CAN bus; not a TTL UART pin", "Bidirectional bus via U5", "Check continuity header pin 4 → U5-6 and external termination; no working bus is claimed.", [(DS, "6 CANL, 7 CANH")]),
    "SWDIO": ("PA13 debug data", "Target +3V3 logic domain", "Bidirectional debugger ↔ MCU", "Verify cable numbering against actual header view before debug attachment.", [(IOC, "PA13.Signal=SYS_JTMS-SWDIO")]),
    "SWCLK": ("PA14 debug clock", "Target +3V3 logic domain", "Debugger → MCU", "Verify continuity pin 4 → U3-49; no successful programming session recorded here.", [(IOC, "PA14.Signal=SYS_JTCK-SWCLK")]),
    "SWO_TDO": ("PB3 trace/JTAG output; usable debug mode must be confirmed", "Target +3V3 logic domain", "MCU → debugger", "Verify trace/debug configuration before expecting SWO output.", []),
    "TDI": ("PA15 JTAG input; usable debug mode must be confirmed", "Target +3V3 logic domain", "Debugger → MCU", "Confirm chosen debug mode; SWD normally uses SWDIO/SWCLK instead.", []),
    "NRST": ("MCU reset", "Reset domain; pull-up and waveform unmeasured", "Debugger → MCU reset", "Verify reset pull network and observe reset release waveform.", []),
    "NC": ("No connection in v5 source", "No defined voltage", "None", "Do not treat NC as a common net; JTAG pin 7 is an individually unconnected pin.", []),
    "VIN_RAW": ("Battery input to buck converter and R5/R6 divider; ADC not initialized", "Battery specification and safe board operating envelope unresolved", "Battery/external supply → board", "Identify battery and input protection; regulator rating alone does not establish safe board input voltage.", [(MAIN, "/* Initialize all configured peripherals */")]),
}

CONNECTORS = [
    ("LORAMODULE", "LoRa module", "Five-pin serial radio interface; the BOM identifies the socket, not the fitted radio module.", ["Installed RYLR model remains unconfirmed. Capture identification and accepted AT settings before using performance estimates.", "No LoRa reset GPIO setup appears in the current source. Legacy command reception has no link-loss timeout."]),
    ("GPSMODULE", "GPS module", "Five-pin GPS socket with USART3 and an extra PB0 signal.", ["The BOM identifies the socket, not the GPS module. PB0/pin 3 is actively driven LOW by firmware.", "USART3 TX also carries debug output; assess its effect on the selected GPS module."]),
    ("SPEEDCONTROLLER", "SPEEDCONTROLLER header / firmware rudder", "Source-named ESC header carries PA8/TIM1, currently assigned to rudder in firmware.", [ACTUATOR, POWER, "No link-loss failsafe exists in the reviewed C main loop; last command persists."]),
    ("STEERINGSERVO", "STEERINGSERVO header / firmware thrust", "Source-named servo header carries PC6/TIM3, currently assigned to thrust in firmware.", [ACTUATOR, POWER, "TIM3 startup differs: current C requests 1000 us, .ioc requests 1500 us. Regeneration needs review."]),
    ("CANHEADER", "CAN bus", "Four-pin bus/supply header; its H/L names are corrected while original pin membership is preserved.", ["CANH = pin 3 / U5-7 / N24691; CANL = pin 4 / U5-6 / N04855. Older docs/NETLIST.md reverses them.", "V1 RXD is wired U5-4 → U3-43/PA10. PA10 has no CAN alternate function; no CAN initialization exists in current firmware.", "U5-8/STB goes to PA11, U5-1/TXD goes to PA12. The CAN transceiver supply source and bus termination require review."]),
    ("JTAG", "Debug / JTAG", "Ten numbered electrical pins; do not infer cable orientation from the table.", ["Raw Allegro pin numbers 01–10 are normalized to 1–10 here. Pin 7 is NC, pin 1 is +3V3, and pins 3/5/9 are GND.", "This corrects the stale debug table in docs/NETLIST.md. Physical keyed-header orientation remains unverified."]),
    ("VIN", "Battery positive", "Single solder pad for raw input supply.", ["The input voltage/current envelope is not established by this source reconstruction. Identify battery and protection first."]),
    ("GND", "Battery ground", "Single solder pad on the board common ground net.", ["Allegro reference GND maps to KiCad GND1; original net name is 0. It is not a separate battery-only ground net in v5."]),
    ("TP1", "TP1 — PA8 PWM", "Test point on the source ESC header signal, currently firmware rudder output.", [ACTUATOR]),
    ("TP3", "TP3 — PC6 PWM", "Test point on the source servo header signal, currently firmware thrust output.", [ACTUATOR]),
    ("TP4", "TP4 — +3V3", "Test point on the main 3.3 V rail.", ["Use TP5 as the source-defined reference. Bench rail tolerance/ripple has not been measured."]),
    ("TP5", "TP5 — ground", "Test point on common ground.", ["TP2 is absent from the v5 netlist and current BOM. Do not reuse the older documentation's ADC test-point claim."]),
]


def make_connectors():
    out = []
    for aref, title, description, notes in CONNECTORS:
        bom = BOMS[aref]
        pins = []
        for anet, nodes in NETS.items():
            matches = [n for n in nodes if n["ref"] == aref]
            for node in matches:
                net = NETMAP.get(anet, anet)
                firmware, voltage, direction, bench, anchors = SPEC[net]
                members = frozenset((n["ref"], n["pin"]) for n in nodes)
                if anet != "NC":
                    assert members in XML_NETS, f"KiCad export differs on {anet}; rerun primary validation"
                    assert XML_NETS[members].split("/")[-1] == net, f"KiCad readable net name differs on {anet}"
                refs = [{"path": PST, "line": node["line"]}]
                mcu_nodes = [] if anet == "NC" else [n for n in nodes if n["ref"] == "U3"]
                mcu = "; ".join(f"U3-{n['pin']} {n['label']}" for n in mcu_nodes) or "No direct MCU pin"
                refs.extend({"path": PST, "line": n["line"]} for n in mcu_nodes)
                if anet in NETMAP:
                    refs.append(evidence(MAP, json.dumps(anet)))
                refs.extend(evidence(p, token) for p, token in anchors)
                pins.append({"pin": node["pin"], "allegro_pin": node["allegro_pin"], "net": net,
                             "allegro_net": anet, "mcu": mcu, "firmware": firmware,
                             "voltage": voltage, "direction": direction, "bench": bench, "evidence": refs})
        assert pins, aref
        pins.sort(key=lambda x: int(x["pin"]))
        out.append({"id": bom["Ref"], "allegro_ref": aref, "title": title, "description": description,
                    "doc": f"docs/atlas/{aref}.md", "notes": [COMMON, *notes], "pins": pins,
                    "bom": {k: bom[k] for k in ("Ref", "Allegro_RefDes", "Value", "MPN", "Manufacturer", "Footprint", "Confidence")}})
    return out


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def connector_md(c):
    b = c["bom"]
    lines = [f"# {c['title']}", "", c["description"], "", f"Allegro reference **{c['allegro_ref']}** → KiCad reference **{c['id']}**.", "",
             f"BOM: {b['Value']}; MPN `{b['MPN'] or 'not applicable (bare pad)'}`; {b['Manufacturer'] or 'no purchased component'}; confidence: {b['Confidence']}.",
             f"Footprint: `{b['Footprint']}`. [Full BOM](../BOM.csv).", "", "## Read before wiring", ""]
    lines += ["- " + note for note in c["notes"]]
    lines += ["", "## Electrical pin map", "", "| Pin | Readable net | Allegro net | MCU | Firmware role |", "|---|---|---|---|---|"]
    for p in c["pins"]:
        lines.append("| " + " | ".join(cell(p[k]) for k in ("pin", "net", "allegro_net", "mcu", "firmware")) + " |")
    lines += ["", "## Verification targets — not measured results", ""]
    for p in c["pins"]:
        lines += [f"### Pin {p['pin']} — {p['net']}", "", f"**Domain:** {p['voltage']}. **Direction:** {p['direction']}.", "", p["bench"], "", "Evidence: " + "; ".join(cite(e) for e in p["evidence"]) + ".", ""]
    lines += ["[Atlas index and snapshot provenance](README.md) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png)", ""]
    return "\n".join(lines)


def readme_md(connectors):
    lines = ["# V1 connector atlas", "", "This atlas connects the authoritative v5 electrical netlist to the current KiCad reference names, BOM, and firmware. It is a wiring/review aid for the faithful V1 reconstruction, not a corrected V2 hardware release or a bench sign-off.", "", COMMON, "", "## Navigate", "", "| Connector / test point | Allegro reference | KiCad reference | Pins |", "|---|---|---|---|"]
    for c in connectors:
        lines.append(f"| [{c['title']}]({c['allegro_ref']}.md) | {c['allegro_ref']} | {c['id']} | {len(c['pins'])} |")
    lines += ["", "[Full BOM](../BOM.csv) · [Schematic PDF](../img/v1_schematic.pdf) · [PCB top](../img/v1_pcb_top.png) · [PCB bottom](../img/v1_pcb_bottom.png) · [Viewer JSON](../../pm/data/connectors.json)", "", "## Known V1 issues that affect connection decisions", "",
              f"- **Actuator mapping:** {ACTUATOR} Evidence: {ev(MAIN, 'BOARD WIRING NOTE')}; both PWM connector tables provide pin-level source links.",
              f"- **Link loss:** reviewed C has one HAL_GetTick use, for outgoing telemetry; its main loop has no command-age timeout. Last actuator command is retained. Evidence: {ev(MAIN, 'uint32_t now = HAL_GetTick()')}; {ev(MAIN, 'static void set_thrust(uint8_t value)\n{')}.",
              f"- **Regeneration hazard:** C initializes TIM3 at 1000 us; CubeMX stores 1500 us. Evidence: {ev(MAIN, 'sConfigOC.Pulse      = PWM_MOTOR_IDLE_US')}; {ev(IOC, 'TIM3.Pulse-PWM\\ Generation1\\ CH1=1500')}.",
              f"- **GPS pin 3:** PB0 is driven LOW; its attached module function is unidentified. Debug text also uses GPS TX. Evidence: {ev(MAIN, 'HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET)')}; {ev(MAIN, 'HAL_UART_Transmit(&huart3')}.",
              f"- **CAN routing:** U5 RXD connects to PA10, which lacks a CAN alternate function; STB connects to PA11. The TCAN1042H requires 4.5–5.5 V on CAN_VCC. Source evidence: {ev(PST, 'NODE_NAME\tU5 4')}; {ev(PST, 'NODE_NAME\tU5 8')}; [ST pin/alternate-function tables](https://www.st.com/resource/en/datasheet/stm32f446re.pdf); [TI pin table and operating conditions](https://www.ti.com/lit/ds/symlink/tcan1042h-q1.pdf). No operational CAN stack is present in this firmware snapshot.",
              f"- **Power and boot:** CEXT connects VCAP1 to the +3V3 net, not ground. BOOT0 is listed NC; VBAT is a singleton. These source facts need an electrical correction decision before treating a reconstructed board as ready to power. Evidence: {ev(PST, 'NODE_NAME\tCEXT 2')}; {ev(PST, 'NODE_NAME\tCEXT 1')}; {ev(PST, 'NODE_NAME\tU3 60')}; {ev(PST, chr(39) + 'VBAT' + chr(39))}; [ST MCU supply requirements](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).",
              "- **External power:** ESC and servo header pin 1 are both on +3V3. Exact loads, BEC wiring, regulator thermal margin, and connector orientation are not verified by this atlas.",
              "- **Stale reference:** docs/NETLIST.md is an older DSN-derived document with incorrect V5 CAN/debug pin tables and TP2. It is intentionally not an input to this atlas. TP2 is absent from both v5 source and the current BOM.",
              "", "## Reproduce and refresh", "", "Run `python docs/atlas/generate_atlas.py` from the repository (or use the installed KiCad Python executable). Run with `--check` to compare outputs with the same source snapshot without writing. Only Python's standard library is required.", "",
              "The generator parses every v5 net/node, preserves Allegro reference and raw pin identifiers, maps readable nets using the current KiCad netmap, obtains KiCad references from the BOM, and compares each connected atlas pin's entire source net membership with the exported KiCad XML. NC is never treated as an electrical net. Reviewed firmware assertions cause generation to stop if key behavior changes. Full source SHA-256 hashes and byte sizes are stored in the JSON; inputs are rehashed before outputs are written to detect concurrent edits.", "",
              "A successful atlas check proves repeatable extraction and agreement with that exported XML snapshot. It does not independently validate the current CAD copper, a stale XML export, a physical board, firmware build/flash results, or external harnesses. Root S2 validation owns CAD equivalence checks. Manufacturer links were checked on 2026-09-17; local datasheet research remains a separately authored review input.", "",
              "Before adaptation: identify fitted radio/GPS and actuator hardware, resolve the power/boot/CAN defects, label the actual harness, scope unloaded PWM, add/test command failsafe, then perform documented bench bring-up. Voice, text, and location handheld requirements are a future platform requirement, not implemented on these connectors.", "", "## Input snapshot", "", "| Input | SHA-256 |", "|---|---|"]
    lines += [f"| [{x['path']}](../../{x['path'].replace(' ', '%20')}) | `{x['sha256']}` |" for x in MANIFEST]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    connectors = make_connectors()
    assert len(connectors) == 12 and sum(len(c["pins"]) for c in connectors) == 36
    assert not any(n["ref"] == "TP2" for nodes in NETS.values() for n in nodes)
    report = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "sources": MANIFEST,
              "status": "Source-derived snapshot; bench and physical orientation unverified", "connectors": connectors}
    json_path = ROOT / "pm/data/connectors.json"
    if json_path.exists():
        previous = json.loads(json_path.read_text(encoding="utf-8"))
        if {k: v for k, v in previous.items() if k != "generated_at"} == {k: v for k, v in report.items() if k != "generated_at"}:
            report["generated_at"] = previous["generated_at"]
    outputs = {c["doc"]: connector_md(c) for c in connectors}
    outputs["docs/atlas/README.md"] = readme_md(connectors)
    outputs["pm/data/connectors.json"] = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    changed_inputs = [p for p in INPUTS if (ROOT / p).read_bytes() != RAW[p]]
    assert not changed_inputs, f"Inputs changed while building atlas: {changed_inputs}; retry from stable snapshot"
    stale = []
    for path, content in outputs.items():
        dest = ROOT / path
        if args.check:
            if not dest.exists() or dest.read_text(encoding="utf-8") != content:
                stale.append(path)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        raise SystemExit("Atlas outputs stale: " + ", ".join(stale))
    print(f"Atlas {'verified' if args.check else 'generated'}: {len(connectors)} connectors/test points, 36 pins, {len(MANIFEST)} hashed inputs; bench status unverified.")


if __name__ == "__main__":
    main()
