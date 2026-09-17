#!/usr/bin/env python3
"""provenance.py - Parse every Gerber (.art) and Excellon (.drl) header under Allegro/ and write the
provenance table (file -> source .brd revision -> date -> layers -> md5) into docs/A0_PROVENANCE.md
between the GENERATED markers, plus hardware/kicad/_build/provenance.json.
Run from repo root:  python hardware/kicad/tools/provenance.py
"""
import hashlib, json, os, re, sys, zipfile, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ALLEGRO = os.path.join(ROOT, 'Allegro', 'hardware', 'allegro-original')
OUT_MD = os.path.join(ROOT, 'docs', 'A0_PROVENANCE.md')
OUT_JSON = os.path.join(ROOT, 'hardware', 'kicad', '_build', 'provenance.json')

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()[:12]

def parse_gerber_header(p):
    d = {'kind': 'gerber', 'layers': []}
    with open(p, 'r', errors='replace') as f:
        for line in f:
            line = line.rstrip('\r\n')
            m = re.match(r'G04 Layout Name:\s*(.*)\*$', line)
            if m: d['layout'] = m.group(1).strip()
            m = re.match(r'G04 Film Name:\s*(.*)\*$', line)
            if m: d['film'] = m.group(1).strip()
            m = re.match(r'G04 Origin Date:\s*(.*)\*$', line)
            if m: d['date'] = m.group(1).strip()
            m = re.match(r'G04 Layer:\s*(.*)\*$', line)
            if m: d['layers'].append(m.group(1).strip())
            m = re.match(r'%FS(L|T)(A|I)X(\d)(\d)Y(\d)(\d)\*MO(IN|MM)\*%', line)
            if m: d['format'] = f"FS{m.group(1)}{m.group(2)} {m.group(3)}.{m.group(4)} {m.group(7)}"
            if line.startswith('M02'): break
    return d

def parse_drill_header(p):
    d = {'kind': 'drill', 'tools': []}
    with open(p, 'r', errors='replace') as f:
        for line in f:
            line = line.rstrip('\r\n')
            m = re.match(r';FILE\s*:\s*(.*)', line)
            if m: d['file_note'] = m.group(1).strip()
            m = re.match(r';DESIGN:\s*(.*)', line)
            if m: d['layout'] = m.group(1).strip()
            m = re.match(r';\s*(?:T\d+\s+)?Holesize \d+\. = ([\d.]+) .*?Quantity = (\d+)', line)
            if m: d['tools'].append((float(m.group(1)), int(m.group(2))))
            if line.startswith('%') or line.startswith('G90'): 
                if d['tools']: break
    return d

def brd_rev(layout):
    if not layout: return '?'
    m = re.search(r'senior design (v\d)', layout, re.I)
    if m: return m.group(1)
    if 'seniordesignboard' in layout.lower(): return 'v1?'
    return '?'

rows = []
for base in ['BoatcrewArtwork', 'Allegro v5/Allegro', 'Allegro v5/Allegro/Artwork']:
    dpath = os.path.join(ALLEGRO, base)
    for fn in sorted(os.listdir(dpath)):
        p = os.path.join(dpath, fn)
        if not os.path.isfile(p): continue
        low = fn.lower()
        if re.search(r'\.art(,\d+)?$', low):
            d = parse_gerber_header(p)
        elif re.search(r'\.drl(,\d+)?$', low):
            d = parse_drill_header(p)
        else:
            continue
        d.update(path=os.path.join(base, fn).replace(os.sep, '/'), size=os.path.getsize(p), md5=md5(p),
                 mtime=datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M'))
        d['rev'] = brd_rev(d.get('layout', ''))
        rows.append(d)

# Artwork.zip entries (dates are what the zip recorded)
zp = os.path.join(ALLEGRO, 'Allegro v5', 'Allegro', 'Artwork.zip')
zrows = []
if os.path.exists(zp):
    for i in zipfile.ZipFile(zp).infolist():
        zrows.append({'name': i.filename, 'size': i.file_size, 'zip_date': '%04d-%02d-%02d %02d:%02d' % i.date_time[:5]})

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
json.dump({'files': rows, 'artwork_zip': zrows}, open(OUT_JSON, 'w'), indent=1)

# Markdown table
lines = []
lines.append('| File | Source .brd | Rev | Origin date (Allegro) | Layers / tools | Format | Bytes | md5 |')
lines.append('|---|---|---|---|---|---|---:|---|')
for d in rows:
    if d['kind'] == 'gerber':
        lay = '; '.join(d['layers'])
        src = d.get('layout', '?')
        date = d.get('date', '?')
        fmt = d.get('format', '?')
    else:
        lay = ', '.join(f"{t:.2f} mil x{q}" for t, q in d['tools'])
        src = d.get('layout') or d.get('file_note', '?')
        date = '(no date in file; see mtime %s)' % d['mtime']
        fmt = 'Excellon INCH TZ 2.4'
    lines.append(f"| `{d['path']}` | {src} | **{d['rev']}** | {date} | {lay} | {fmt} | {d['size']} | `{d['md5']}` |")
lines.append('')
lines.append('Artwork.zip (inside `Allegro v5/Allegro/`) member timestamps:')
lines.append('')
lines.append('| Member | Bytes | Zip timestamp |')
lines.append('|---|---:|---|')
for z in zrows:
    lines.append(f"| `{z['name']}` | {z['size']} | {z['zip_date']} |")
table = '\n'.join(lines)

BEGIN, END = '<!-- BEGIN GENERATED provenance.py -->', '<!-- END GENERATED provenance.py -->'
if os.path.exists(OUT_MD):
    md = open(OUT_MD, encoding='utf-8').read()
    if BEGIN in md and END in md:
        pre, rest = md.split(BEGIN, 1); _, post = rest.split(END, 1)
        md = pre + BEGIN + '\n' + table + '\n' + END + post
    else:
        md += '\n' + BEGIN + '\n' + table + '\n' + END + '\n'
else:
    md = '# A0 Provenance\n\n' + BEGIN + '\n' + table + '\n' + END + '\n'
open(OUT_MD, 'w', encoding='utf-8').write(md)
print(f'wrote {OUT_MD} ({len(rows)} artwork/drill files) and {OUT_JSON}')
for d in rows:
    print(f"{d['rev']:4s} {d.get('date', d.get('file_note',''))[:26]:26s} {d['md5']} {d['path']}")
