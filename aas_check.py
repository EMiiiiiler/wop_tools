#!/usr/bin/env python3
"""Check bot navigation (.aas from bspc) against the map's entities.

    python3 aas_check.py maps/mymap.aas maps/mymap.map [--points "x,y,z;x,y,z"] [--rj]

For every pickup / spawn / extra point it finds the AAS area and runs a graph search over the
reachability links from all spawn points. Reports
  - pickups with no AAS area (in solid / floating),
  - pickups bots cannot reach from the spawns (rocket/bfg jumps excluded unless --rj),
  - pickups bots can reach but cannot leave again (traps),
and a travel-type summary.
"""
import struct, sys, re, argparse
from collections import deque
import numpy as np

TT = {1: 'invalid', 2: 'walk', 3: 'crouch', 4: 'barrierjump', 5: 'jump', 6: 'ladder', 7: 'walkoffledge', 8: 'swim',
      9: 'waterjump', 10: 'teleport', 11: 'elevator', 12: 'rocketjump', 13: 'bfgjump', 14: 'grapple', 15: 'doublejump',
      16: 'rampjump', 17: 'strafejump', 18: 'jumppad', 19: 'funcbob'}


def load_aas(path):
    b = bytearray(open(path, 'rb').read())
    ident, ver = struct.unpack_from('<4si', b, 0)
    assert ident == b'EAAS', ident
    if ver == 5:      # lumps are xor-obfuscated (botlib AAS_DData)
        for i in range(8, 8 + 4 + 14 * 8):
            b[i] ^= (i - 8) * 119 & 0xFF
    lumps = [struct.unpack_from('<2i', b, 12 + 8 * i) for i in range(14)]
    def arr(i, dt): o, l = lumps[i]; return np.frombuffer(bytes(b[o:o + l]), dt)
    planes = arr(2, np.dtype([('n', '<f4', 3), ('d', '<f4'), ('t', '<i4')]))
    areas = arr(7, np.dtype([('num', '<i4'), ('nf', '<i4'), ('ff', '<i4'), ('mins', '<f4', 3), ('maxs', '<f4', 3), ('c', '<f4', 3)]))
    sets = arr(8, np.dtype([('contents', '<i4'), ('flags', '<i4'), ('pres', '<i4'), ('cluster', '<i4'), ('carea', '<i4'),
                            ('nreach', '<i4'), ('freach', '<i4')]))
    reach = arr(9, np.dtype([('area', '<i4'), ('face', '<i4'), ('edge', '<i4'), ('start', '<f4', 3), ('end', '<f4', 3),
                             ('type', '<i4'), ('time', '<u2'), ('pad', '<u2')]))
    nodes = arr(10, np.dtype([('plane', '<i4'), ('ch', '<i4', 2)]))
    return planes, areas, sets, reach, nodes


def point_area(planes, nodes, p):
    n = 1
    while n > 0:
        nd = nodes[n]; pl = planes[nd['plane']]
        d = float(np.dot(pl['n'], p) - pl['d'])
        n = nd['ch'][0] if d > 0 else nd['ch'][1]
    return -n


def parse_ents(path):
    txt = open(path, errors='ignore').read()
    out = []
    depth = 0; cur = None
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('//') or not s: continue
        if s == '{':
            depth += 1
            if depth == 1: cur = {}
            continue
        if s == '}':
            if depth == 1: out.append(cur)
            depth -= 1; continue
        if depth == 1:
            m = re.match(r'"([^"]+)"\s+"([^"]*)"', s)
            if m: cur[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('aas'); ap.add_argument('map')
    ap.add_argument('--points', default='')
    ap.add_argument('--rj', action='store_true', help='allow rocket/bfg jumps')
    a = ap.parse_args()
    planes, areas, sets, reach, nodes = load_aas(a.aas)
    ents = parse_ents(a.map)
    na = len(areas)
    adj = [[] for _ in range(na)]; radj = [[] for _ in range(na)]
    counts = {}
    for ai in range(1, na):
        s = sets[ai]
        for r in reach[s['freach']:s['freach'] + s['nreach']]:
            t = int(r['type']) & 0xFFFFFF
            counts[t] = counts.get(t, 0) + 1
            if t in (12, 13) and not a.rj: continue
            adj[ai].append(int(r['area'])); radj[int(r['area'])].append(ai)

    def find(o, kind):
        # items rest on the floor: probe a standing player origin above them
        cands = []
        for dz in ((9, 10, 12, 16, 24, 32, 0) if kind != 'spawn' else (0, 1, 4, 8, -8, 16)):
            for dx, dy in ((0, 0), (8, 0), (-8, 0), (0, 8), (0, -8)):
                ar = point_area(planes, nodes, np.array([o[0] + dx, o[1] + dy, o[2] + dz], np.float32))
                if ar > 0:
                    if sets[ar]['flags'] & 5 and sets[ar]['nreach'] > 0: return ar   # grounded or liquid, linked
                    cands.append(ar)
        return cands[0] if cands else 0

    spawns, picks = [], []
    for e in ents:
        c = e.get('classname', ''); o = e.get('origin')
        if not o: continue
        o = [float(v) for v in o.split()]
        if c in ('info_player_deathmatch', 'info_player_start'):
            spawns.append((c, o, find(o, 'spawn')))
        elif c.startswith(('weapon_', 'ammo_', 'item_', 'holdable_')) or c == 'station_health':
            picks.append((c, o, find(o, 'item')))
    for i, p in enumerate(a.points.split(';')):
        if p.strip():
            o = [float(v) for v in p.split(',')]
            picks.append((f'point{i}', o, find(o, 'item')))

    def bfs(starts, g):
        seen = set(starts); dq = deque(starts)
        while dq:
            x = dq.popleft()
            for y in g[x]:
                if y not in seen: seen.add(y); dq.append(y)
        return seen
    sp = [s[2] for s in spawns if s[2] > 0]
    fwd = bfs(sp, adj)
    back = bfs(sp, radj)
    bad = 0
    print(f'AAS: {na - 1} areas, {len(reach)} reachabilities; spawns {len(spawns)} ({len(sp)} with area)')
    for c, o, ar in spawns:
        if ar == 0: print(f'  SPAWN NO AREA  {c} {o}'); bad += 1
    for c, o, ar in picks:
        if ar == 0:
            print(f'  NO AREA        {c:24s} {[round(v) for v in o]}'); bad += 1
        elif ar not in fwd:
            print(f'  UNREACHABLE    {c:24s} {[round(v) for v in o]} area {ar}'); bad += 1
        elif ar not in back:
            print(f'  TRAP (no exit) {c:24s} {[round(v) for v in o]} area {ar}'); bad += 1
    print('reach types: ' + ', '.join(f'{TT.get(k, k)} {v}' for k, v in sorted(counts.items())))
    print(f'reachable areas from spawns: {len(fwd)} / {na - 1}')
    print('RESULT:', 'OK' if not bad else f'{bad} problem(s)')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
