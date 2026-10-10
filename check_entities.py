#!/usr/bin/env python3
"""Usage: python3 check_entities.py maps/padcounter.map
Lists entity origins that sit inside a solid brush, and (optionally) outside a bounding box.
Works on Quake 3 format .map files. Patches (patchDef) are ignored."""
import re, sys, math

SKIP_TEX = ('water', 'trigger', 'origin', 'hint', 'skip', 'fog', 'lava', 'slime', 'nodraw_nonsolid')
SKIP_ENT = ('misc_model',)           # baked by q3map2, origin may legitimately be anywhere
ROOM = None                          # e.g. ((-1792,-1280,0),(1792,1280,1792)) to flag entities outside this box

def parse(path):
    ents, cur, brush, depth, in_patch = [], None, None, 0, False
    for raw in open(path, errors='ignore'):
        line = raw.strip()
        if not line or line.startswith('//'): continue
        if line.startswith('patchDef') or line.startswith('patchDef2'): in_patch = True
        if line == '{':
            depth += 1
            if depth == 1: cur = {'kv': {}, 'brushes': []}
            elif depth == 2: brush = []
            continue
        if line == '}':
            if depth == 2:
                if not in_patch: cur['brushes'].append(brush)
                in_patch = False; brush = None
            elif depth == 1: ents.append(cur)
            depth -= 1
            continue
        if in_patch: continue
        if depth == 1:
            m = re.match(r'"([^"]+)"\s+"([^"]*)"', line)
            if m: cur['kv'][m.group(1)] = m.group(2)
        elif depth == 2 and line.startswith('('):
            m = re.match(r'\(\s*([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)\s*\)\s*\(\s*([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)\s*\)\s*\(\s*([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)\s*\)\s*(\S+)', line)
            if m:
                v = [float(x) for x in m.groups()[:9]]
                brush.append((tuple(v[0:3]), tuple(v[3:6]), tuple(v[6:9]), m.group(10)))
    return ents

def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

def planes(brush):
    out = []
    for a, b, c, tex in brush:
        n = cross(sub(a, b), sub(c, b)); l = math.sqrt(dot(n, n))
        if l < 1e-9: return None, tex
        n = tuple(v/l for v in n); out.append((n, dot(n, a)))
    return out, brush[0][3]

def main(path):
    ents = parse(path)
    solids = []
    for e in ents:                    # only world brushes block entities
        if e['kv'].get('classname') != 'worldspawn': continue
        for i, b in enumerate(e['brushes']):
            if any(any(s in t[3].lower() for s in SKIP_TEX) for t in b): continue
            pl, _ = planes(b)
            if pl: solids.append((i, pl, b[0][3]))
    bad = 0
    for idx, e in enumerate(ents):
        kv = e['kv']; cls = kv.get('classname', '?')
        if 'origin' not in kv or cls in SKIP_ENT or cls == 'worldspawn': continue
        p = tuple(float(v) for v in kv['origin'].split())
        hits = [(i, t) for i, pl, t in solids if all(dot(n, p) - d < -0.01 for n, d in pl)]
        out = ROOM and not all(ROOM[0][k] < p[k] < ROOM[1][k] for k in range(3))
        if hits or out:
            bad += 1
            print(f'entity {idx} {cls} at {p}: ' + (f'inside world brush {hits[0][0]} ({hits[0][1]})' if hits else 'outside ROOM box'))
    print(f'{bad} problem entit{"y" if bad == 1 else "ies"} found')

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1])
