#!/usr/bin/env python3
"""kicad_write.py - Small helpers shared by the KiCad file generators (deterministic UUIDs, number formatting,
mil->mm, s-expression fragments).  No file output by itself.
"""
import uuid as _uuid
NS = _uuid.UUID('6f4c1d2e-0b7a-4c1e-9a1d-5b2f8e3c7a10')

def uid(*parts):
    """Deterministic UUID so that regenerated files diff cleanly."""
    return str(_uuid.uuid5(NS, '|'.join(str(p) for p in parts)))

def f(v):
    """Format a float for KiCad (max 6 decimals, no trailing zeros, no negative zero)."""
    s = f'{v:.6f}'.rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s

MIL = 0.0254
def mm(v_mil):
    return v_mil * MIL

def esc(s):
    return str(s).replace('\\', '\\\\').replace('"', '\\"')
