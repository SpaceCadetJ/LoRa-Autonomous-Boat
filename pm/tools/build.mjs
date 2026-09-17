// Run: node pm/tools/build.mjs. Reads repository evidence; writes only pm/status.json and pm/index.html.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const out=path.join(root,'pm');
const hashes={};
const exists=p=>fs.existsSync(path.join(root,p));
function read(p){if(!exists(p))return '';const b=fs.readFileSync(path.join(root,p));hashes[p]=crypto.createHash('sha256').update(b).digest('hex');return b.toString('utf8');}
function json(p){const t=read(p);return t?JSON.parse(t):null;}
function git(...args){return execFileSync('git',args,{cwd:root,encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();}
function csv(t){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<t.length;i++){const c=t[i];if(c==='"'){if(quoted&&t[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}else cell+=c;}if(cell||row.length){row.push(cell);rows.push(row);}const h=rows.shift();return rows.filter(r=>r.some(Boolean)).map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]??''])));}
function walk(dir){if(!exists(dir))return [];return fs.readdirSync(path.join(root,dir),{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(`${dir}/${e.name}`):[`${dir}/${e.name}`]);}
const docs=[...new Set(['README.md','REPORT.md','HANDOFF.md','BLOCKERS.md','AGENT_STATUS.md','CONVERSION_LOG.md',...walk('docs').filter(p=>p.endsWith('.md')&&!p.includes('/archive/')),...walk('reviews/codex').filter(p=>p.endsWith('.md')&&!p.includes('/s2/snapshot/'))])].filter(exists);
const documentData=docs.map(p=>({path:p,title:(read(p).match(/^# (.+)/m)||[])[1]||path.basename(p),text:read(p)}));
const bom=csv(read('docs/BOM.csv'));
const bomV2=exists('docs/BOM_V2.csv')?csv(read('docs/BOM_V2.csv')):[];
function tableRows(p,pattern){return read(p).split('\n').filter(l=>pattern.test(l)).map(l=>l.trim().replace(/^\||\|$/g,'').split(/(?<!\\)\|/).map(s=>s.trim()));}
const requirements=tableRows('docs/V2_REQUIREMENTS.md',/^\| REQ-/).map(r=>({id:r[0],requirement:r[1],findings:r[2],verify:r[3],source:'docs/V2_REQUIREMENTS.md'}));
const designFindings=tableRows('docs/V1_DESIGN_REVIEW.md',/^\| F-/).map(r=>({id:r[0],severity:r[1].replaceAll('**',''),finding:r[2],evidence:r[3],disposition:r[4],requirements:requirements.filter(q=>(q.findings||'').includes(r[0])).map(q=>q.id)}));
const decisionRows=tableRows('BLOCKERS.md',/^\| \d+ \|/).map(r=>({id:r[0],question:r[1],default:r[2]}));
const blockers=read('BLOCKERS.md');
if(blockers.includes('72 × 38')){const d=decisionRows.find(x=>x.id==='7');if(d)d.default='80 × 46 mm board; four M3 holes on 72 × 38 mm pattern (latest primary revision)';}
const fabrication=(read('REPORT.md').match(/\*\*Before fabrication[^\n]*/)||[])[0]||'No pre-fabrication disposition published.';
const datasheets=[
{id:'stm32',title:'STM32F446RE',refs:['U3'],maker:'STMicroelectronics',url:'https://www.st.com/resource/en/datasheet/stm32f446re.pdf',note:'DS10693 Rev 11; pin map, alternate functions, regulator supply scheme. Independently consulted in intake.'},
{id:'can',title:'TCAN1042H-Q1',refs:['U5'],maker:'Texas Instruments',url:'https://www.ti.com/lit/gpn/tcan1042h-q1',note:'SLLSES9D; transceiver pinout and supply requirements. Independently consulted in intake.'},
{id:'buck',title:'R1240 series',refs:['U6'],maker:'Nisshinbo Micro Devices',url:'https://www.nisshinbo-microdevices.co.jp/en/pdf/datasheet/r1240-ea.pdf',note:'EA-190-240903; manufacturer link recorded in primary datasheet notes.'},
{id:'radio',title:'RYLR998 / 498 command guide',refs:['LORAMODULE1'],maker:'REYAX',url:'https://reyax.com/upload/products_download/download_file/LoRa_AT_Command_RYLR998_RYLR498_EN.pdf',note:'Verify installed module before using these limits. RYLR896 is not interchangeable by assumption.'},
{id:'radio-ds',title:'RYLR998 module',refs:['LORAMODULE1'],maker:'REYAX',url:'https://reyax.com/upload/products_download/download_file/RYLR998_EN.pdf',note:'Module candidate/reference; installed hardware identity remains open.'}
];
const images=walk('docs/img').filter(p=>/\.(png|svg|pdf)$/.test(p)).map(p=>({path:p,title:path.basename(p).replace(/v1_|\.(png|svg|pdf)/g,'').replaceAll('_',' '),type:path.extname(p).slice(1)}));
const reports={};for(const n of ['drc','erc','netlist_check','xor_report','validate_pcb']){const p=`hardware/kicad/_build/${n}.json`;reports[n]={path:p,data:json(p),provenance:'Primary report; independently checked only where S2 says so'};}
const v2Reports={};for(const n of ['erc.json','drc.rpt','drc_all.rpt','placement.json']){const p=`hardware/kicad_v2/_build/${n}`;if(exists(p))v2Reports[n]={path:p,content:read(p)};}
const findings=[
['R01','Baseline corrected','Resolved by primary','32 connected nets, 44 parts, v5 rectangular outline; drill provenance is explicit.'],
['R02','Netlist validation coverage','Addressed; independent review','Dedicated check_netlist.py compares schematic/PCB/source pin sets. Geometry validator alone is insufficient.'],
['R03','CANH / CANL names','Resolved by primary','Corrected in release 639e08f.'],
['R04','Command-loss failsafe','Open firmware defect','Last commanded PWM persists. Correction prototype must be integrated and tested on hardware.'],
['R05','Startup configuration drift','Open firmware defect','TIM3 startup value differs between C and CubeMX configuration.'],
['R06','PWM destination mismatch','Confirmed V1 condition','PA8 reaches ESC-labelled header; PC6 reaches servo-labelled header. Harness verification remains necessary.'],
['R07','VCAP capacitor return','Confirmed V1 defect','CEXT returns to +3V3 instead of VSS. Preserve baseline; correct successor design.'],
['R08','CAN receive pin','Confirmed V1 defect','RXD reaches PA10, which lacks the required CAN function.'],
['R09','Actuator power domain','Open hardware risk','Both actuator pin 1s are on +3V3. Verify harness/BEC and separate power in successor.'],
['R10','Input and GPS validity','Open firmware defect','Strict frame parsing, buffer handoff, UART recovery and stale-fix handling required.'],
['R11','Radio identity / settings','Needs hardware facts','Identify module and read back accepted settings before timing/range commitments.']
].map(([id,title,status,detail])=>({id,title,status,detail,source:'HANDOFF.md'}));
const phases=[
{id:'A0',title:'Source provenance',status:'Reported complete',detail:'v5 films and packaged netlist identified; older drill distinguished.',source:'docs/A0_PROVENANCE.md'},
{id:'A1',title:'Footprints',status:'Reported complete',detail:'Project-local geometry reconstructed; 44 footprints.',source:'docs/CONVERSION_NOTES.md'},
{id:'A2',title:'PCB fidelity',status:'Reported complete',detail:'Primary release reports 0 DRC errors and 0 unrouted; warnings and inferred drills retained.',source:'HANDOFF.md'},
{id:'A3',title:'Schematic',status:'Reported complete',detail:'Wired hierarchy, ERC and pin membership checked by primary.',source:'docs/img/v1_schematic.pdf'},
{id:'A4',title:'Baseline documentation',status:exists('docs/V1_DESIGN_REVIEW.md')?'Reported complete':'In progress',detail:'Primary reports baseline closed; independent release review remains separate.',source:'REPORT.md'},
{id:'B',title:'Review and requirements',status:requirements.length?'Published draft':'Next gate',detail:`${designFindings.length} V1 findings linked to ${requirements.length} requirements. Acceptance tests and open defaults remain visible.`,source:'docs/V2_REQUIREMENTS.md'},
{id:'C',title:'Successor implementation',status:exists('hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb')?'Primary draft':'Planned',detail:'V2 design work is active. Reported electrical checks do not establish fabrication or firmware readiness.',source:'hardware/kicad_v2/README.md'}
];
const sourcePaths=['firmware/Core/Src/main.c','firmware/Core/Src/stm32f4xx_hal_msp.c','firmware/BoatTHISTIMEITSDIFFERENT.ioc',...walk('reviews/codex/firmware_prototype').filter(p=>/\.(c|h|md)$/.test(p))];
const sources=sourcePaths.filter(exists).map(p=>({path:p,text:read(p)}));
const previous=json('pm/status.json');delete hashes['pm/status.json'];
const connectorData=json('pm/data/connectors.json');
const software=json('pm/data/software.json');
const independent=json('reviews/codex/s2/summary.json');
const data={schema:1,generated_at:new Date().toISOString(),head:git('rev-parse','HEAD'),branch:git('branch','--show-current'),released_revision:'639e08f',title:'LoRa engineering workspace',
purpose:'A faithful boat-controller baseline, documented so it can evolve into a reusable RC and voice/text/location platform.',
bom,bomV2,requirements,designFindings,decisionRows,fabrication,v2Reports,datasheets,documents:documentData,images,reports,findings,phases,connectors:connectorData?.connectors||[],connector_meta:connectorData?{generated_at:connectorData.generated_at,sources:connectorData.sources}:null,software,independent,sources,
next:['Inspect independent release verification and its limitations.','Review actuator power, VCAP and PWM evidence before bench work.','Record radio, battery, ESC/BEC and harness identities.','Integrate and test protocol corrections after firmware ownership transfer.','Measure voice airtime, intelligibility and RC coexistence before radio selection.'],
decisions:[['Radio hardware','Identify installed RYLR model and firmware; capture AT readback.','Required before RF commitments'],['Battery and actuator supply','Record chemistry, cell count, BEC voltage and actual harness routing.','Required before V2 power design'],['Voice behavior','Voice + text + location required; evaluate live PTT and recorded messages.','Feasibility packet'],['Operating envelope','Agree control deadline, range, antenna installation and region.','Requirements packet'],['Expansion and mechanics','Decide CAN role, sensor set, connectors and mounting from use cases.','Architecture review']],
manifest:hashes};
data.available_paths=[...new Set([...docs,...images.map(x=>x.path),...sourcePaths,...walk('hardware/kicad').filter(x=>/\.(kicad_pro|kicad_pcb|kicad_sch)$/.test(x)&&!x.includes('/_')),...walk('hardware/kicad_v2').filter(x=>/\.(kicad_pro|kicad_pcb|kicad_sch)$/.test(x)&&!x.includes('/_')),'docs/BOM.csv','docs/BOM_V2.csv','firmware/V2_FIRMWARE_PLAN.md'].filter(exists))];
for(const p of ['firmware/V2_FIRMWARE_PLAN.md','hardware/kicad_v2/README.md'])if(exists(p)&&!data.documents.some(d=>d.path===p))data.documents.push({path:p,title:(read(p).match(/^# (.+)/m)||[])[1]||p,text:read(p)});
data.changed_since_previous=previous?Object.keys(hashes).filter(p=>previous.manifest?.[p]!==hashes[p]):[];
data.inputs_changed_during_build=Object.entries(hashes).filter(([p,h])=>!exists(p)||crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')!==h).map(([p])=>p);
const template=read('pm/index.template.html');data.manifest={...hashes};
const serialized=JSON.stringify(data).replaceAll('<','\\u003c');
fs.writeFileSync(path.join(out,'status.json'),JSON.stringify(data,null,2)+'\n');
// A callback preserves dollar sequences in embedded firmware and documents literally.
// A replacement string would expand $&, $' and $` and corrupt the HTML/script boundary.
fs.writeFileSync(path.join(out,'index.html'),template.replace('/*__PROJECT_DATA__*/',()=>`window.PROJECT=${serialized};`));
console.log(JSON.stringify({parts:bom.length,connectors:data.connectors.length,documents:documentData.length,images:images.length,head:data.head,inputs_changed_during_build:data.inputs_changed_during_build}));
