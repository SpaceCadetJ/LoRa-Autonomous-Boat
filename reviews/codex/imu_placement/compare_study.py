"""Portable structural comparison of the normalized PCB and placement copy."""
from collections import Counter
from pathlib import Path
import json,re,hashlib
OUT=Path(__file__).resolve().parent

def children(text):
    result=[];level=0;start=None;quoted=False;escape=False
    for i,c in enumerate(text):
        if quoted:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quoted=False
            continue
        if c=='"':quoted=True
        elif c=='(':
            level+=1
            if level==2:start=i
        elif c==')':
            if level==2:result.append(text[start:i+1])
            level-=1
    if level or quoted:raise ValueError('Unbalanced PCB expression')
    return result

def compare(before,after):
    old=children(before);new=children(after)
    a=Counter(x for x in old if not x.startswith('(footprint '))
    b=Counter(x for x in new if not x.startswith('(footprint '))
    if a!=b:raise ValueError('Unexpected non-footprint change: rules, nets, copper, outline, zones or metadata')
    af=Counter(x for x in old if x.startswith('(footprint '));bf=Counter(x for x in new if x.startswith('(footprint '))
    if af-bf:raise ValueError('Original footprint changed or removed')
    extras=list((bf-af).elements())
    refs=[re.search(r'\(property "Reference" "([^"]+)"',f).group(1) for f in extras]
    if set(refs)!={'U9','U10','U11','R36','R37','R38','R39','C38','C39','C40','C41','C42'} or len(refs)!=12:raise ValueError('Unexpected added footprints')
    if any(re.search(r'\(net [1-9]',f) for f in extras):raise ValueError('Study-only pads must be unassigned')
    return {'original_footprints_preserved_exactly':sum(af.values()),'added_footprints':sorted(refs),'non_footprint_blocks_preserved_exactly':sum(a.values()),'tracks_vias_zones_fills_outline_rules_nets_unchanged':True,'new_pads_unassigned':True}

def main():
    result=compare((OUT/'inputs/normalized_baseline.kicad_pcb').read_text(),(OUT/'study/IMU_PLACEMENT_STUDY.kicad_pcb').read_text())
    (OUT/'preservation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))
if __name__=='__main__':main()
