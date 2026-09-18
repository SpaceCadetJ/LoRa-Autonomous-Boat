#!/usr/bin/env python3
"""kicad_sym.py - Read KiCad 9 symbol libraries: extract one symbol's s-expression block, flatten (extends ...),
list its pins (number, name, x, y, angle, electrical type, unit), and re-serialize for embedding in a schematic's
(lib_symbols ...) section.  Self-contained s-expression parser that keeps quoted strings distinct from atoms.
"""
import os, re

KICAD_SHARE = os.environ.get('KICAD_SYMBOL_DIR', r'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\share\kicad\symbols')

class Str(str):
    """A quoted string token (serialized with double quotes)."""
    pass

def tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
        elif c in '()':
            yield c; i += 1
        elif c == '"':
            j = i + 1; buf = []
            while j < n:
                ch = text[j]
                if ch == chr(92) and j + 1 < n:
                    buf.append(text[j:j + 2]); j += 2; continue
                if ch == '"':
                    break
                buf.append(ch); j += 1
            yield Str(''.join(buf)); i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()':
                j += 1
            yield text[i:j]; i = j

def parse(text):
    stack = [[]]
    for t in tokenize(text):
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop(); stack[-1].append(node)
        else:
            stack[-1].append(t)
    return stack[0]

def serialize(node, indent=0):
    """Serialize a parsed tree back to KiCad-style text (tabs, one child per line for lists that contain lists)."""
    pad = '\t' * indent
    if not isinstance(node, list):
        return f'"{node}"' if isinstance(node, Str) else str(node)
    has_list = any(isinstance(c, list) for c in node)
    if not has_list:
        return pad + '(' + ' '.join(serialize(c) for c in node) + ')'
    # head atoms on the first line, list children on their own lines
    head = []
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        head.append(serialize(node[i])); i += 1
    lines = [pad + '(' + ' '.join(head)]
    for c in node[i:]:
        if isinstance(c, list):
            lines.append(serialize(c, indent + 1))
        else:
            lines.append('\t' * (indent + 1) + serialize(c))
    lines.append(pad + ')')
    return '\n'.join(lines)

def _find_block(text, name):
    """Return the text of the top-level (symbol "name" ...) block in a .kicad_sym file."""
    pat = re.compile(r'\(symbol\s+"' + re.escape(name) + r'"')
    for m in pat.finditer(text):
        # must be a top-level symbol: preceded by newline + one tab (KiCad 9 formatting) or check depth
        start = m.start()
        # scan forward for the matching paren, honouring quotes
        depth = 0; i = start; inq = False; esc = False
        while i < len(text):
            ch = text[i]
            if inq:
                if esc: esc = False
                elif ch == chr(92): esc = True
                elif ch == '"': inq = False
            else:
                if ch == '"': inq = True
                elif ch == '(': depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        blk = text[start:i + 1]
                        # top-level symbols contain (property ...) or (extends ...) directly; unit sub-symbols do not
                        if re.search(r'\(extends\s|\(property\s', blk):
                            return blk
                        break
            i += 1
    return None

_lib_cache = {}
def lib_text(lib):
    if lib not in _lib_cache:
        if os.path.isfile(lib):
            path = lib
        else:
            path = os.path.join(KICAD_SHARE, lib + '.kicad_sym')
        _lib_cache[lib] = open(path, encoding='utf-8').read()
    return _lib_cache[lib]

def _props(tree):
    return {c[1]: c for c in tree[2:] if isinstance(c, list) and c and c[0] == 'property'}

def load_symbol(lib, name):
    """Return {'tree': flattened parsed symbol (name = 'lib:name'), 'pins': [...], 'raw_name': name}."""
    txt = lib_text(lib)
    blk = _find_block(txt, name)
    if blk is None:
        raise KeyError(f'symbol {name} not found in {lib}')
    tree = parse(blk)[0]
    ext = [c for c in tree if isinstance(c, list) and c and c[0] == 'extends']
    if ext:
        parent = load_symbol(lib, str(ext[0][1]))
        ptree = parent['tree']
        # rename: parent 'lib:parent' -> child; unit sub-symbols 'parent_N_M' -> 'name_N_M'
        pname = parent['raw_name']
        ptree[1] = Str(f'{os.path.basename(lib).replace(".kicad_sym", "")}:{name}')
        for c in ptree:
            if isinstance(c, list) and c and c[0] == 'symbol' and str(c[1]).startswith(pname + '_'):
                c[1] = Str(name + str(c[1])[len(pname):])
        # override properties with the child's
        pprops = _props(ptree)
        for k, v in _props(tree).items():
            if k in pprops:
                idx = ptree.index(pprops[k]); ptree[idx] = v
            else:
                ptree.insert(2, v)
        tree = ptree
    else:
        tree[1] = Str(f'{os.path.basename(lib).replace(".kicad_sym", "")}:{name}')
    return {'tree': tree, 'pins': symbol_pins(tree), 'raw_name': name}

def symbol_pins(tree):
    pins = []
    for c in tree:
        if isinstance(c, list) and c and c[0] == 'symbol':
            m = re.search(r'_(\d+)_(\d+)$', str(c[1]))
            unit = int(m.group(1)) if m else 1
            for p in c:
                if isinstance(p, list) and p and p[0] == 'pin':
                    at = next(x for x in p if isinstance(x, list) and x[0] == 'at')
                    ln = next((x for x in p if isinstance(x, list) and x[0] == 'length'), ['length', 0])
                    nm = next(x for x in p if isinstance(x, list) and x[0] == 'name')
                    num = next(x for x in p if isinstance(x, list) and x[0] == 'number')
                    pins.append({'unit': unit, 'type': str(p[1]), 'style': str(p[2]), 'x': float(at[1]), 'y': float(at[2]),
                                 'angle': float(at[3]) if len(at) > 3 else 0.0, 'length': float(ln[1]),
                                 'name': str(nm[1]), 'number': str(num[1])})
    return pins

def symbol_bbox(tree):
    """Rough body bounding box (symbol coords, Y up) from rectangles/polylines/pins."""
    xs, ys = [], []
    for c in tree:
        if isinstance(c, list) and c and c[0] == 'symbol':
            for g in c:
                if not isinstance(g, list): continue
                if g[0] == 'rectangle':
                    s = next(x for x in g if isinstance(x, list) and x[0] == 'start'); e = next(x for x in g if isinstance(x, list) and x[0] == 'end')
                    xs += [float(s[1]), float(e[1])]; ys += [float(s[2]), float(e[2])]
                elif g[0] in ('polyline',):
                    pts = next(x for x in g if isinstance(x, list) and x[0] == 'pts')
                    for xy in pts[1:]:
                        xs.append(float(xy[1])); ys.append(float(xy[2]))
                elif g[0] == 'pin':
                    at = next(x for x in g if isinstance(x, list) and x[0] == 'at')
                    xs.append(float(at[1])); ys.append(float(at[2]))
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))

if __name__ == '__main__':
    import sys
    s = load_symbol(sys.argv[1], sys.argv[2])
    print(serialize(s['tree'])[:1500])
    for p in s['pins'][:70]:
        print(p)
