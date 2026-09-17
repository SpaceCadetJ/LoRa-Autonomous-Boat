#!/usr/bin/env python3
"""sexpr_check.py - Syntax sanity check for generated KiCad s-expression files (balanced parens/quotes, bad tokens,
top-level element histogram).  Usage: python hardware/kicad/tools/sexpr_check.py <file.kicad_pcb|.kicad_sch|.kicad_mod>
"""
import sys, re, collections

def check(path):
    t = open(path, encoding='utf-8').read()
    depth = 0; inq = False; line = 1; maxd = 0; esc = False
    for i, ch in enumerate(t):
        if ch == '\n':
            line += 1
        if inq:
            if esc:
                esc = False
            elif ch == chr(92):
                esc = True
            elif ch == '"':
                inq = False
            continue
        if ch == '"':
            inq = True
        elif ch == '(':
            depth += 1; maxd = max(maxd, depth)
        elif ch == ')':
            depth -= 1
            if depth < 0:
                print('negative depth at line', line); return False
    print(f'{path}: final depth {depth}, max depth {maxd}, lines {line}, open quote {inq}')
    tops = re.findall(r'^\t\((\w+)', t, re.M)
    print('  top-level:', dict(collections.Counter(tops)))
    ok = depth == 0 and not inq
    for bad in ['nan', 'inf', 'None', 'True', 'False']:
        n = len(re.findall(r'(?<![\w"])' + bad + r'(?![\w"])', t))
        if n:
            print('  BAD token', bad, n); ok = False
    return ok

if __name__ == '__main__':
    sys.exit(0 if all(check(p) for p in sys.argv[1:]) else 1)
