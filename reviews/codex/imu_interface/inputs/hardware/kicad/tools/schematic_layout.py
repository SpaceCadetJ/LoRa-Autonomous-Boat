"""Presentation-only schematic layout shared by V1/V2. No connectivity or PCB writes.

Functional panels reserve space for pin labels, properties and design notes. Symbol
UUIDs and sheet membership stay unchanged. Netlist equivalence is checked by CI.
"""
import math
import os
import json
import itertools
import textwrap
import kicad_sym as ks
from kicad_write import f, esc, uid

PLANS = {
 ('v1','PowerSupply'): [
  ('01  Battery entry', 'VIN GND CIN', 'Existing V1 solder pads. No fuse, reverse protection or transient clamp.'),
  ('02  Logic regulator and switching loop', 'U6 D21 L1 C12 R3 R4', 'R1240N asynchronous buck. Preserve the original catch diode and bootstrap network.'),
  ('03  Feedback and output reservoir', 'R1 R2 C14 COUT', 'Nominal output: 0.8 x (1 + 15k / 4.7k) = 3.35 V. Values describe V1, not a new qualification.'),
  ('04  Battery sensing and test access', 'R5 R6 TP4 TP5', 'Divider is 4:1; 3.3 V ADC full scale corresponds to 13.2 V. Legacy firmware does not sample it.')],
 ('v1','MCU'): [
  ('01  MCU signal map', 'U3', 'STM32F446RET6 / LQFP-64. PA8 reaches ESC-labelled header; PC6 reaches servo-labelled header. Firmware roles are reversed.'),
  ('02  Core supply - preserved defect', 'CEXT', 'CEXT returns VCAP_1 to +3V3 in the original design. Do not copy this return into V2.'),
  ('03  Logic supply decoupling', 'C2 C3 C4 C5 C6 C7 C8 C9 C10', 'Preserved capacitors and net membership. VBAT and BOOT0 are floating in V1; see design review before bench power.')],
 ('v1','CAN_Bus'): [
  ('01  Transceiver', 'U5 C1', 'VCC is external 4.5-5.5 V. RXD reaches PA10, which has no CAN receive function; V1 CAN is not operational.'),
  ('02  External CAN port', 'CANHEADER', 'Pin numbers are electrical numbering, not a cable-side view. Confirm pin 1 and supply polarity on the real board.')],
 ('v1','LoRa_Module'): [
  ('01  UART radio socket', 'LORAMODULE', 'Identify the fitted radio and capture AT replies before selecting SF/BW or assuming reset-pin behavior.'),
  ('02  Supply filter', 'L4 C20 L3 C21 C22 C23', 'Preserved defect: C20 returns to +3V3. C23 value/MPN conflict remains in the BOM; resolve the fitted value.')],
 ('v1','GPS_Module'): [('01  GNSS serial interface', 'GPSMODULE', 'PC11 is GNSS-to-MCU data; PC10 is MCU-to-GNSS data. PB0 on pin 3 is driven low by legacy firmware; confirm the module pin function.')],
 ('v1','PWM_Outputs'): [
  ('01  ESC-labelled connector / legacy rudder', 'SPEEDCONTROLLER TP1', 'PA8 / TIM1. Confirm physical harness before changing firmware. Pin 1 is +3V3, not a BEC input.'),
  ('02  Servo-labelled connector / legacy thrust', 'STEERINGSERVO TP3', 'PC6 / TIM3. Legacy thrust output starts at 1000 us in C; CubeMX configuration differs. Disconnect propulsion during first tests.')],
 ('v1','Debug'): [('01  Cortex debug access', 'JTAG', '3.3 V target reference, SWDIO, SWCLK, NRST and ground. Probe VTref is a sense input; avoid competing power supplies. See docs/build/FLASHING_V1.md.')],
 ('v2','Power'): [
  ('01  Protected board input', 'J1 F1 Q1 D2 R1 D1 C1 C2', 'Board supply path only; propulsion battery current bypasses this PCB. Protection ratings and 2S-6S margin require design review.'),
  ('02  Board current and battery sensing', 'R33 U8 C37 R31 R32 C36', '20 mOhm shunt, INA180 gain 20: nominal 0.4 V/A. Divider: 6.8k / (47k + 6.8k). Check ADC scaling before use.'),
  ('03  3.3 V logic supply', 'U2 R2 R3 C3 D3 L1 R4 R5 C4 C5 C6', 'Nominal 3.35 V. Follow the labelled bootstrap, switch and feedback nets; verify component ratings and switching-loop placement before fabrication.'),
  ('04  Actuator supply and BEC isolation', 'U3 R6 C7 L2 R8 R9 C8 C9 C10 D4 D9 C11 C12', 'Nominal buck output 5.08 V before OR-ing diode loss. VSERVO is separate from +3V3. Confirm BEC voltage, population option and back-feed behavior.'),
  ('05  Power test points', 'TP3 TP4 TP5 TP6', 'Expected node labels only. No measured rail, ripple, load or thermal qualification is claimed.')],
 ('v2','MCU'): [
  ('01  MCU and assigned interfaces', 'U1', '3.3 V logic. Labels define the current board wiring; fleet/ground-vehicle and handheld behavior still requires firmware and interface qualification.'),
  ('02  Digital and core supply', 'C15 C16 C17 C18 C19 C20 C23', 'Place each 100 nF capacitor near its VDD pin. C20 is the 4.7 uF VCAP_1-to-GND capacitor. VBAT is tied to VDD.'),
  ('03  Analog supply and reset defaults', 'FB1 C21 C22 C24 R16 SW1', 'VDDA filter is fed from +3V3. BOOT0 pull-down selects flash boot; NRST is available at the debug header.'),
  ('04  Clock sources', 'Y1 C25 C26 Y2 C27 C28', 'HSE: 8 MHz / CL 10 pF. LSE: 32.768 kHz / CL 7 pF. Check actual stray capacitance and startup; LSE is a population option.'),
  ('05  Status indicators', 'D5 R29 D6 R30 D7 R34 D8 R35', 'Power, link, fix and fault labels describe intended application states. Firmware must define and verify the indications.')],
 ('v2','Radio'): [
  ('01  Radio socket and serial protection', 'J4 R17 R18 R19', 'Verify the chosen REYAX module pinout and voltage. UART/reset series resistors are not voltage translators.'),
  ('02  Radio supply filtering', 'FB3 C29 FB2 C30 C31 C32', 'Filter returns are to GND. Keep antenna placement clear of switching/actuator noise. Voice/RC airtime coexistence is an open requirement.')],
 ('v2','Navigation'): [
  ('01  GNSS UART and timing pulse', 'J5 R20 R21 R22 TP7', 'Check module pin order and PPS polarity before connecting. PB0 is intended for PPS capture; it is not the V1 debug-LED output.'),
  ('02  Inertial sensor', 'U6 C33 C34 C35 R23 R24', 'I2C address, VDDIO rating, REGOUT capacitor and AD0/SDO strapping need datasheet review. Draft schematic is not sensor qualification.')],
 ('v2','Actuators'): [
  ('01  Thrust channel', 'U4 C13 R14 R10 R11 D10 J2 TP1', 'J2: signal / BEC input / GND. MCU-side pull-down does not replace a command-loss failsafe. Verify arm and reset behavior with propulsion disconnected.'),
  ('02  Steering channel', 'U5 C14 R15 R12 R13 D11 J3 TP2', 'J3: signal / VSERVO output / GND. Verify buffer supply range against the selected BEC and clamp ratings.')],
 ('v2','Debug'): [
  ('01  USB-C device connection', 'J6 R25 R26 U7', 'CC pull-downs identify a USB device. Route D+/D- together and place ESD near the connector. USB is not a qualified first-flash path.'),
  ('02  VBUS detection', 'R27 R28', '47k / 47k divider gives nominal 2.5 V at 5 V VBUS. Firmware must use PA9 consistently with this divided signal.'),
  ('03  Cortex debug / first flashing', 'J7', 'Use SWD for initial programming; check VTref, ground, SWDIO, SWCLK and NRST. See docs/build/FLASHING_V2.md.')]
}

def rectangle(sh, x, y, w, h):
    pts=' '.join(f'(xy {f(a)} {f(b)})' for a,b in [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)])
    sh.items.append(f'(polyline (pts {pts}) (stroke (width 0.15) (type solid)) (fill (type none)) (uuid "{sh._u("panel")}"))')

def wrapped(sh, text, x, y, width, size=1.27):
    lines=textwrap.wrap(text, max(20,int(width/(size*0.62))), break_long_words=False)
    for i,line in enumerate(lines): sh.text(line,x,y+i*2.8,size)
    return len(lines)*2.8

def dimensions(sym, value, nets):
    x1,y1,x2,y2=ks.symbol_bbox(sym['tree'])
    # Reserve a separate, horizontal label lane on each side, including long port names.
    longest=max([len(n) for n in nets.values() if n]+[5])
    margin=max(18, longest*0.75+9)
    extra=7 if len(sym['pins'])>2 and any(int(p['angle'])%180==90 for p in sym['pins']) else 0
    return (max(x2-x1+margin*2, len(value)*0.8+12,42), y2-y1+25+extra, margin, (x1,y1,x2,y2))

def panel_layout(refs, records, width):
    positions=[]; x=7; y=19; row_h=0
    for ref in refs:
        r=records[ref]; w,h,margin,bb=dimensions(r['sym'],r['value'],r['pins'])
        if w>width-14: raise ValueError(f'{ref} needs a wider panel ({w:.1f} mm)')
        if x+w>width-7: x=7; y+=row_h+5; row_h=0
        # The position includes all pin endpoints and external label/property space.
        sx=round((x+w/2-(bb[0]+bb[2])/2)/2.54)*2.54
        extra=7 if len(r['sym']['pins'])>2 and any(int(p['angle'])%180==90 for p in r['sym']['pins']) else 0
        sy=round((y+14+extra+bb[3])/2.54)*2.54
        positions.append((ref,sx,sy,w,h)); x+=w+3; row_h=max(row_h,h)
    return positions,y+row_h+5

def decorate_and_place(sh, records, net_sheets, root_uuid, version):
    plans=PLANS[(version,sh.name)]
    seen=[]; usable={r for r,v in records.items() if v['sym']['pins']}
    groups=[]
    for title,refstr,note in plans:
        refs=[r for r in refstr.split() if r in usable]
        if refs: groups.append((title,refs,note)); seen+=refs
    missing=sorted(usable-set(seen))
    if missing: groups.append(('Additional components',missing,'See part descriptions in the BOM for exact assembly intent.'))
    if len(seen)!=len(set(seen)): raise ValueError('Duplicate component in presentation plan')
    # Try A3 first; dense power/MCU pages can use A2 without cropping or shrinking text.
    attempts=[]
    for paper,W,H,cols in [('A3',420,297,2),('A3',420,297,3),('A2',594,420,3),('A2',594,420,2)]:
        width=(W-26-(cols-1)*12)/cols; heights=[34]*cols; arranged=[]
        try:
            prepared=[]
            for title,refs,note in groups:
                positions,body=panel_layout(refs,records,width)
                note_lines=textwrap.wrap(note,max(20,int((width-14)/(1.27*0.62))),break_long_words=False)
                height=body+len(note_lines)*2.8+10
                prepared.append((title,note,height,body,positions))
            def score(assignment):
                totals=[34+sum(p[2]+8 for p,c in zip(prepared,assignment) if c==col) for col in range(cols)]
                return max(totals),sum(h*h for h in totals),assignment
            assignment=min(((0,)+tail for tail in itertools.product(range(cols),repeat=len(prepared)-1)),key=score)
            for col,(title,note,height,body,positions) in zip(assignment,prepared):
                x=13+col*(width+12); y=heights[col]
                arranged.append((title,note,x,y,width,height,body,positions))
                heights[col]+=height+8
        except ValueError as error:
            attempts.append(str(error)); continue
        attempts.append((paper,cols,heights,[(a[0],a[5]) for a in arranged]))
        if max(heights)<H-60: break
    else: raise ValueError(f'{version}/{sh.name}: schematic layout exceeds available pages: {attempts}')
    sh.paper=paper
    sh.text(f'{version.upper()}  /  {sh.name.replace("_"," ").upper()}',13,17,2.5)
    sh.text('Functional groups / electrical pin numbers / named-net connections',13,24,1.5)
    for title,note,x,y,w,h,body,positions in arranged:
        rectangle(sh,x,y,w,h); sh.text(title,x+5,y+7,1.7)
        for ref,sx,sy,_,_ in positions:
            r=records[ref]
            sh.place(ref,r['sym'],round((x+sx)/2.54)*2.54,round((y+sy)/2.54)*2.54,r['value'],r['props'],r['pins'],net_sheets,root_uuid)
        wrapped(sh,note,x+7,y+body+3,w-14)
    sh.text('Read named nets within each group; matching labels are electrically connected. Cross-sheet signals use hierarchical ports.',13,H-36,1.1)
    sh.text('V1 preserves original defects. V2 is a review draft. Bench values and firmware behavior require validation.',13,H-31,1.1)
    return W,H

def source_flags(sh, nets, root_uuid, power_nets):
    # Dedicated compact service rail above the title block, never on top of its text.
    import gen_sch
    W,H=gen_sch.PAPER[sh.paper]
    x0=18; y=round((H-53)/2.54)*2.54
    for i,net in enumerate(nets):
        x=round((x0+i*32)/2.54)*2.54
        flag=ks.load_symbol('power','PWR_FLAG'); sh.add_lib(flag)
        sh.items.append(sh._symbol(str(flag['tree'][1]),x,y,0,f'#FLG{sh.name[:3]}{i+1:02d}','PWR_FLAG',{},flag,root_uuid,power=True))
        sh.wire(x,y,x,y+2.54)
        sh.label(net,x,y+2.54,0,'global_label' if net in power_nets else 'label')

def root_blocks(root, sheets, root_uuid):
    """Compact hierarchy: reserve left label lanes and derive row heights from pin counts."""
    root.paper='A3'; blocks=[]; W=420; top=40; cols=3; pitch=130
    root.text(root.title,13,16,2.5)
    root.text('SHEET INDEX / Open a subsystem for component groups, net labels and review notes',13,24,1.5)
    root.text('Power names are global; matching signal labels below join hierarchical sheet pins.',13,30,1.27)
    for start in range(0,len(sheets),cols):
        row=sheets[start:start+cols]
        row_height=max(max(26,2.54*(len(s.hier)+2)) for s in row)
        for col,sh in enumerate(row):
            x=round((58+col*pitch)/2.54)*2.54; y=round(top/2.54)*2.54
            h=max(26,2.54*(len(sh.hier)+2)); w=66
            pins=''
            for k,net in enumerate(sorted(sh.hier)):
                py=y+2.54*(k+1)
                pins+=f'(pin "{esc(net)}" passive (at {f(x)} {f(py)} 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "{uid("sheetpin",root.proj,sh.name,net)}"))'
                root.wire(x,py,x-5.08,py); root.label(net,x-5.08,py,180,'label')
            i=start+col
            blocks.append(f'(sheet (at {f(x)} {f(y)}) (size {w} {f(h)}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sh.uuid}") (property "Sheetname" "{esc(sh.name)}" (at {f(x)} {f(y-2.2)} 0) (effects (font (size 1.8 1.8)) (justify left bottom))) (property "Sheetfile" "{esc(sh.file)}" (at {f(x)} {f(y+h+2)} 0) (effects (font (size 1.1 1.1)) (justify left top))) {pins} (instances (project "{root.proj}" (path "/{root_uuid}" (page "{i+2}")))))')
        top+=row_height+22
    if top>249: raise ValueError('Root hierarchy would enter the footer/title block')
    root.text('BUILD PATH: review -> order selected BOM -> inspect/assemble -> verify power -> program over SWD -> functional acceptance',13,257,1.1)
    root.text('Start: docs/build/README.md | V1 is the existing board; V2 is the multifunction vehicle-node draft.',13,263,1.1)
    return '\n'.join(blocks)

def generate_v1(g, input_dir=None):
    b,netmap,mpn=g.load_inputs(input_dir)
    comps={c['ref']:c for c in b['components']}; pn={}; net_sheets={}
    root_uuid=g.design_root_uuid(); sheets=[]; paths={}
    for c in b['components']:
        for p in c['pads']:
            if p['net'] is not None:
                net=netmap.get(p['net'],p['net']); pn[c['ref'],p['number']]=net
                net_sheets.setdefault(net,set()).add(g.SHEET_OF[c['ref']])
    for name,file,paper,descr,refs in g.SHEETS:
        sh=g.Sheet(name,file,paper,descr,refs); records={}
        for ref in refs:
            c=comps[ref]; sym=ks.load_symbol(*g.symbol_for(ref,c['jedec']))
            props={'Footprint':f'{g.PROJ}:{c["jedec"]}','Allegro_Device':c['device'],'Description':c['part'] or ''}
            for p in sym['tree']:
                if isinstance(p,list) and p and p[0]=='property' and str(p[1]) in ('Datasheet','Description') and str(p[2]): props[str(p[1])]=str(p[2])
            props.update({k:mpn.get(ref,{}).get(k,props.get(k,'')) for k in ('MPN','Manufacturer','Description')})
            records[ref]={'sym':sym,'value':g.nice_value(ref,c['part'],c['value']),'props':props,'pins':{p['number']:pn.get((ref,p['number'])) for p in sym['pins']}}
            paths[ref]=f'/{sh.uuid}/{g.symbol_uuid(ref)}'
        decorate_and_place(sh,records,net_sheets,root_uuid,'v1')
        if name=='PowerSupply': source_flags(sh,['VIN_RAW','+3V3','GND'],root_uuid,g.POWER_NETS)
        if name=='CAN_Bus': source_flags(sh,['CAN_VCC'],root_uuid,g.POWER_NETS)
        sheets.append(sh)
    root=g.Sheet('Root',g.PROJ+'.kicad_sch','A3','V1 electrical reconstruction / annotated review edition',[],title='LoRa boat controller V1 | existing hardware')
    blocks=root_blocks(root,sheets,root_uuid)
    _write(g.KDIR,g.BUILD,root,sheets,root_uuid,paths,blocks)

def generate_v2(v, pin_net, syms):
    import gen_sch as g
    g.POWER_NETS={k:(v.lib_path(p[0]) if p[0] in (v.D.V1LIB,v.PROJ,'LoRa_Boat_Controller') else p[0],p[1],p[2]) for k,p in v.D.POWER_NETS.items()}
    root_uuid=uid('sch',v.PROJ,'root'); net_sheets={}; sheets=[]; paths={}
    for ref,pins in pin_net.items():
        for net in pins.values(): net_sheets.setdefault(net,set()).add(v.D.PARTS[ref][5])
    for name,file,paper,descr in v.D.SHEETS:
        refs=[r for r in v.D.PARTS if v.D.PARTS[r][5]==name]
        sh=g.Sheet(name,file,paper,descr,refs,ref_fn=lambda r:r,uuid_fn=lambda r:uid('sch',v.PROJ,r),proj=v.PROJ,title='LoRa multifunction vehicle node V2')
        records={}
        for ref in refs:
            sym=syms[ref]
            if not sym['pins']: continue
            fp,value,mpn,mfr,_,desc=v.D.PARTS[ref][1:7]
            props={'Footprint':fp,'Description':desc,'MPN':mpn,'Manufacturer':mfr,'Datasheet':''}
            for p in sym['tree']:
                if isinstance(p,list) and p and p[0]=='property' and str(p[1])=='Datasheet': props['Datasheet']=str(p[2])
            records[ref]={'sym':sym,'value':value,'props':props,'pins':pin_net[ref]}
            paths[ref]=f'/{sh.uuid}/{uid("sch",v.PROJ,ref)}'
        decorate_and_place(sh,records,net_sheets,root_uuid,'v2')
        if name=='Power': source_flags(sh,['VIN_RAW','+3V3','VSERVO','GND','VIN_BUCK'],root_uuid,g.POWER_NETS)
        if name=='MCU': source_flags(sh,['VDDA'],root_uuid,g.POWER_NETS)
        if name=='Debug': source_flags(sh,['VBUS'],root_uuid,g.POWER_NETS)
        sheets.append(sh)
    root=g.Sheet('Root',v.PROJ+'.kicad_sch','A3','V2 review draft / annotated functional hierarchy',[],ref_fn=lambda r:r,uuid_fn=lambda r:uid('sch',v.PROJ,r),proj=v.PROJ,title='LoRa multifunction vehicle node V2')
    blocks=root_blocks(root,sheets,root_uuid)
    _write(v.V2DIR,v.BUILD,root,sheets,root_uuid,paths,blocks)
    return paths

def _write(directory, build, root, sheets, root_uuid, paths, blocks):
    os.makedirs(build, exist_ok=True)
    for sh in [root]+sheets:
        with open(os.path.join(directory,sh.file),'w',encoding='utf-8',newline='\n') as fh:
            fh.write(sh.render(root_uuid,root=sh is root,sheets_block=blocks if sh is root else ''))
    with open(os.path.join(build,'sch_paths.json'),'w') as fh: json.dump({'root_uuid':root_uuid,'sheet_uuid':{s.name:s.uuid for s in sheets},'paths':paths},fh,indent=2)
    print('Annotated schematic:',len(sheets)+1,'sheets;',len(paths),'symbols;',', '.join(s.name+':'+s.paper for s in sheets))
