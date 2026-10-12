from pathlib import Path
import json,sys
import model
P=Path(__file__).resolve().parent
def render():
    a=json.loads((P/'analysis.json').read_text());assert a==model.study()
    return (P/'view.template.html').read_text().replace('__DATA__',json.dumps(a,separators=(',',':')).replace('<','\\u003c'))
if __name__=='__main__':
    text=render();out=P/'index.html'
    if '--check' in sys.argv:assert out.read_text()==text,'Saved review UI is stale'
    else:out.write_text(text,encoding='utf-8',newline='\n')
    print('Capacitor review UI checked/built; no circuit qualification.')
