from pathlib import Path
import argparse
import json

HERE = Path(__file__).resolve().parent

def render():
    data = json.loads((HERE / 'analysis.json').read_text(encoding='utf-8-sig'))
    return (HERE / 'index.template.html').read_text(encoding='utf-8-sig').replace('__RAIL_DATA__', json.dumps(data, ensure_ascii=True).replace('<', '\\u003c'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build only the isolated ACT-05 viewer; never CAD.')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    html = render()
    if args.check:
        assert (HERE / 'index.html').read_text(encoding='utf-8') == html, 'Viewer data or template changed; rebuild'
        print('PASS ACT-05 embedded data/template match')
    else:
        (HERE / 'index.html').write_text(html, encoding='utf-8', newline='\n')
