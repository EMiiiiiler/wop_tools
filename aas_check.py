#!/usr/bin/env python3
"""Check bot navigation (.aas from bspc) against the map's entities.

    python3 aas_check.py maps/mymap.aas maps/mymap.map [--points "x,y,z;x,y,z"] [--rj]
                         [--route "name:x,y,z>x,y,z;..." | --route @routes.txt]

For every pickup / spawn / extra point it finds the AAS area and runs a graph search over the
reachability links from all spawn points. Reports
  - pickups with no AAS area (in solid / floating),
  - pickups bots cannot reach from the spawns (rocket/bfg jumps excluded unless --rj),
  - pickups bots can reach but cannot leave again (traps),
and a travel-type summary.
--route checks that a designed path (stairs into a cellar, a hatch into a ship's hold...) works ON FOOT in both
directions while standing: only walk / step / jump / walk-off-ledge links into areas a standing player fits in
(no crouching, swimming, teleporters or jump pads), staying near the straight line between the two points. Pickups can pass the main check through a back door while
the front door is blocked by a low ceiling; this catches that.
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


TEAMSPAWN = ('team_redspawn', 'team_bluespawn', 'team_redplayer', 'team_blueplayer',
             'team_CTF_redspawn', 'team_CTF_bluespawn', 'team_CTF_redplayer', 'team_CTF_blueplayer')


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
    ap.add_argument('--route', default='', help='"name:x,y,z>x,y,z;..." on-foot standing routes, checked both ways')
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
    PRES_NORMAL = 2
    foot = [[] for _ in range(na)]
    for ai in range(1, na):
        if not sets[ai]['pres'] & PRES_NORMAL: continue
        s_ = sets[ai]
        for r in reach[s_['freach']:s_['freach'] + s_['nreach']]:
            t = int(r['type']) & 0xFFFFFF; b_ = int(r['area'])
            if t in (2, 4, 5, 7) and sets[b_]['pres'] & PRES_NORMAL: foot[ai].append(b_)

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
        if c in ('info_player_deathmatch', 'info_player_start') or c in TEAMSPAWN:
            spawns.append((c, o, find(o, 'spawn')))
        elif c.startswith(('weapon_', 'ammo_', 'item_', 'holdable_', 'team_CTL_', 'team_CTF_')) or c == 'station_health':
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
    import heapq
    C = areas['c']
    MN, MX = areas['mins'], areas['maxs']
    def walk_len(src, dst, pa, pb, corridor=448):
        """shortest on-foot path between two areas using only areas whose box overlaps the A-B box grown by
        `corridor` (2D) and whose floor lies between the lower point - 24 and the higher point + 160, so a
        long way round (out a back door, through the water...) doesn't count; inf if none"""
        if not (src and dst): return float('inf')
        bx0 = min(pa[0], pb[0]) - corridor; bx1 = max(pa[0], pb[0]) + corridor
        by0 = min(pa[1], pb[1]) - corridor; by1 = max(pa[1], pb[1]) + corridor
        z0, z1 = min(pa[2], pb[2]) - 24, max(pa[2], pb[2]) + 160
        def inside(x):
            if x in (src, dst): return True
            return (z0 <= MN[x][2] <= z1 and MX[x][0] >= bx0 and MN[x][0] <= bx1 and MX[x][1] >= by0 and MN[x][1] <= by1)
        dist = {src: 0.0}; pq = [(0.0, src)]
        while pq:
            d, x = heapq.heappop(pq)
            if x == dst: return d
            if d > dist.get(x, 1e18): continue
            for y in foot[x]:
                if not inside(y): continue
                nd = d + float(np.linalg.norm(C[x] - C[y]))
                if nd < dist.get(y, 1e18): dist[y] = nd; heapq.heappush(pq, (nd, y))
        return float('inf')
    rts = a.route
    if rts.startswith('@'):              # @file: one "name: x,y,z > x,y,z" per line, # comments
        rts = ';'.join(l.split('#')[0].replace(' ', '') for l in open(rts[1:]) if l.split('#')[0].strip())
    for rt in filter(None, rts.split(';')):
        name, pts = rt.split(':') if ':' in rt else ('route', rt)
        pa, pb = ([float(v) for v in q.split(',')] for q in pts.split('>'))
        # route points are floor heights; find() probes like an item (origin floor + 16)
        aa, ab = find([pa[0], pa[1], pa[2] + 16], 'item'), find([pb[0], pb[1], pb[2] + 16], 'item')
        res = []
        for lbl, (x, y, p0, p1) in (('there', (aa, ab, pa, pb)), ('back', (ab, aa, pb, pa))):
            res.append('' if walk_len(x, y, p0, p1) < float('inf') else f'{lbl} blocked')
        st = 'NO AREA' if not (aa and ab) else ('OK' if not any(res) else ', '.join(r for r in res if r))
        print(f'  route {name:20s} {st}')
        if st != 'OK': bad += 1
    # CTL / CTF: each team's capture run (own spawns -> enemy lolly -> own lolly), fastest by bot travel time
    lol = {c: ar for c, o, ar in picks if c.startswith(('team_CTL_', 'team_CTF_'))}
    def tm(c): return 'red' if 'red' in c.lower() else ('blue' if 'blue' in c.lower() else '')
    flags = {tm(c): ar for c, ar in lol.items() if tm(c)}
    if len(flags) == 2:
        import heapq as _hq
        def fastest(srcs, dst):
            # cost (1/100 s) = reach time + distance from where the area was entered to the reach start, walking
            # 320 u/s, swimming 150 u/s (approximates the bot's area travel times)
            dist = {x: 0 for x in srcs}; prev = {}; pq = [(0, x) for x in srcs]
            entry = {x: C[x] for x in srcs}
            while pq:
                d, x = _hq.heappop(pq)
                if x == dst: break
                if d > dist[x]: continue
                s_ = sets[x]
                spd = 150.0 if s_['contents'] & 1 else 320.0
                for r in reach[s_['freach']:s_['freach'] + s_['nreach']]:
                    t = int(r['type']) & 0xFFFFFF
                    if t in (12, 13) and not a.rj: continue
                    y = int(r['area'])
                    nd = d + int(r['time']) + 1 + float(np.linalg.norm(r['start'] - entry[x])) / spd * 100
                    if nd < dist.get(y, 1 << 60): dist[y] = nd; prev[y] = (x, t); entry[y] = r['end']; _hq.heappush(pq, (nd, y))
            if dst not in dist: return None, []
            ty = []; y = dst
            while y in prev: x, t = prev[y]; ty.append(TT.get(t, t)); y = x
            return dist[dst], ty[::-1]
        for team, other in (('red', 'blue'), ('blue', 'red')):
            srcs = [ar for c, o, ar in spawns if ar and c in TEAMSPAWN and team in c]
            for lbl, (sa, da) in (('to enemy lolly', (srcs, flags[other])), ('capture home', ([flags[other]], flags[team]))):
                t_, ty = fastest(sa, da)
                if t_ is None:
                    print(f'  CTL {team:4s} {lbl:15s} NO PATH'); bad += 1
                else:
                    used = sorted(set(ty) - {'walk'})
                    print(f'  CTL {team:4s} {lbl:15s} {t_ / 100:5.1f} s  via {", ".join(used) or "walk"}')
    print('reach types: ' + ', '.join(f'{TT.get(k, k)} {v}' for k, v in sorted(counts.items())))
    print(f'reachable areas from spawns: {len(fwd)} / {na - 1}')
    print('RESULT:', 'OK' if not bad else f'{bad} problem(s)')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
