from pathlib import Path
import json,argparse
P=Path(__file__).resolve().parent

def output():
    data=json.loads((P/'validation.json').read_text(encoding='utf-8-sig'))
    return (P/'viewer.template.html').read_text(encoding='utf-8-sig').replace('@@VALIDATION@@',json.dumps(data).replace('</','<\\/'))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args();text=output()
    if a.check:assert (P/'index.html').read_text(encoding='utf-8')==text,'Stale native comparison viewer'
    else:(P/'index.html').write_text(text,encoding='utf-8',newline='\n')
