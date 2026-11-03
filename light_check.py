#!/usr/bin/env python3
"""light_check.py - how bright is every walkable floor in the compiled map? (no game client needed)

    python3 light_check.py maps/X.bsp [--map maps/X.map] [--png out.png] [--dark 30] [--bright 200] [--cell 128]

Reads the BSP's lightmaps under every upward-facing lightmapped triangle (brush floors and lightmapped MD3 tops; vertex
colours for vertex-lit surfaces), keeps those a player can stand on (with --map: inside the space flooded from spawns
and pickups, the same voxel flood lint_map uses), and buckets them into cells per floor level.

Values are raw lightmap bytes (WoP shows them about x2 with its default overbright), luminance 0-255:
    < --dark   (30)  reads near-black in game ("the ant colony is too dim", "sign renders dark under the roof")
    > --bright (200) blown out / no shading left
Prints the area-weighted median and percentiles, the share of walkable floor that is dark or blown out, and the darkest
and brightest clusters with coordinates (put lights there, or move the lights away). --png draws a top-down map.
Raw 128 is neutral (the texture at its own brightness: the game and bsp2scene draw texture x min(2 x lightmap, 1.6)),
raw 205+ is saturated (x1.6, white floors wash out), raw 30 is x0.24.
Exit 1 when more than --max-dark-pct (10 %) of the floor is dark or --max-bright-pct (35 %) is blown out. Calibration
(Oct 2026): padbbq (sunny yard, final light) median 51, dark 14 % (the north strip in the house's shade, the ant
colony secret - both flagged in its notes), bright 27 % (sunlit lawn); the sample yard median 139, bright 45 % (its
screenshots look washed out). Sunny outdoor maps are bimodal (sun ~230, shade ~25): fill light the shade.
"""
import os, sys, struct, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LUMPS = dict(entities=0, shaders=1, verts=10, indexes=11, surfaces=13, lightmaps=14)


def read_bsp(path):
    b = open(path, 'rb').read()
    if b[:4] != b'IBSP': raise SystemExit(f'{path}: not a Q3 BSP')
    lump = lambda i: struct.unpack_from('<ii', b, 8 + 8 * i)
    o, l = lump(LUMPS['verts'])
    V = np.frombuffer(b, dtype=np.dtype([('xyz', '<f4', 3), ('st', '<f4', 2), ('lm', '<f4', 2), ('n', '<f4', 3), ('c', 'u1', 4)]),
                      count=l // 44, offset=o)
    o, l = lump(LUMPS['indexes']); I = np.frombuffer(b, '<i4', l // 4, o)
    o, l = lump(LUMPS['surfaces'])
    S = np.frombuffer(b, dtype=np.dtype([('shader', '<i4'), ('fog', '<i4'), ('type', '<i4'), ('fv', '<i4'), ('nv', '<i4'),
                                         ('fi', '<i4'), ('ni', '<i4'), ('lmn', '<i4'), ('lmxy', '<i4', 4), ('lmo', '<f4', 3),
                                         ('lmv', '<f4', 9), ('pw', '<i4'), ('ph', '<i4')]), count=l // 104, offset=o)
    o, l = lump(LUMPS['lightmaps'])
    LM = np.frombuffer(b, 'u1', l, o).reshape(-1, 128, 128, 3) if l else np.zeros((0, 128, 128, 3), np.uint8)
    o, l = lump(LUMPS['shaders'])
    SH = [(b[o + 72 * i:o + 72 * i + 64].split(b'\0')[0].decode('latin1'), *struct.unpack_from('<ii', b, o + 72 * i + 64))
          for i in range(l // 72)]
    return V, I, S, LM, SH


def lum(rgb): return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def sample_lm(LM, n, uv):
    """bilinear lightmap sample at uv (0..1 over the whole 128x128 page)"""
    page = LM[n].astype(np.float32)
    x = np.clip(uv[:, 0] * 128 - 0.5, 0, 127); y = np.clip(uv[:, 1] * 128 - 0.5, 0, 127)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    x1 = np.minimum(x0 + 1, 127); y1 = np.minimum(y0 + 1, 127)
    fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    return (page[y0, x0] * (1 - fx) * (1 - fy) + page[y0, x1] * fx * (1 - fy) + page[y1, x0] * (1 - fx) * fy + page[y1, x1] * fx * fy)


def floor_samples(V, I, S, LM, SH, skip_shader=('sky', 'water', 'nodraw', 'caulk', 'clip', 'trigger', 'glass', 'fog')):
    """[(x, y, z, area, luminance)] for upward triangles, 3 samples per triangle (centroid + 2 inner points)"""
    out = []
    for s in S:
        if s['type'] not in (1, 3) or s['ni'] < 3: continue
        name = SH[s['shader']][0].lower() if 0 <= s['shader'] < len(SH) else ''
        if any(k in name for k in skip_shader): continue
        idx = I[s['fi']:s['fi'] + s['ni']].reshape(-1, 3) + s['fv']
        P = V['xyz'][idx]                                    # (T, 3, 3)
        nrm = np.cross(P[:, 2] - P[:, 0], P[:, 1] - P[:, 0])       # Q3 front faces wind clockwise
        area = np.linalg.norm(nrm, axis=1) / 2
        up = (nrm[:, 2] / np.maximum(2 * area, 1e-9) > 0.7) & (area > 4)
        if not up.any(): continue
        idx, P = idx[up], P[up]
        LMUV = V['lm'][idx].astype(np.float64); COL = V['c'][idx][..., :3].astype(np.float64)
        # split big triangles 1 -> 4 until each is under ~64x64u, so a 3000u floor quad lands in every cell it covers
        for _ in range(8):
            ar = np.linalg.norm(np.cross(P[:, 2] - P[:, 0], P[:, 1] - P[:, 0]), axis=1) / 2
            big = ar > 4096
            if not big.any(): break
            def split(T):
                a_, b_, c_ = T[big, 0], T[big, 1], T[big, 2]
                ab, bc, ca = (a_ + b_) / 2, (b_ + c_) / 2, (c_ + a_) / 2
                new = np.concatenate([np.stack(t, 1) for t in ((a_, ab, ca), (ab, b_, bc), (ca, bc, c_), (ab, bc, ca))])
                return np.concatenate([T[~big], new])
            P, LMUV, COL = split(P), split(LMUV), split(COL)
        area = np.linalg.norm(np.cross(P[:, 2] - P[:, 0], P[:, 1] - P[:, 0]), axis=1) / 2
        pt = P.mean(1)
        if 0 <= s['lmn'] < len(LM):
            L = lum(sample_lm(LM, s['lmn'], LMUV.mean(1)))
        else:
            L = lum(COL.mean(1))
        out.append(np.column_stack([pt, area, L]))
    return np.concatenate(out) if out else np.zeros((0, 5))


def reachable_mask(F, mapfile):
    import audit_map as AM, lint_map as LM_
    ents = AM.parse(mapfile)
    BR = LM_.Brushes(ents)
    G = LM_.AirGrid(BR, ents)
    return np.array([G.open_at(p[:3] + [0, 0, 40]) for p in F]), G


def aas_mask(F, aasfile, mapfile):
    """floor samples whose standing origin lies in an AAS area reachable from a spawn (walk, jump, pads, teleports):
    the floor players really get to, not air over a fence"""
    import aas_check as AC
    from collections import deque
    planes, areas, sets, reach, nodes = AC.load_aas(aasfile)
    na = len(areas)
    adj = [[] for _ in range(na)]
    for ai in range(1, na):
        st = sets[ai]
        for r in reach[st['freach']:st['freach'] + st['nreach']]: adj[ai].append(int(r['area']))
    starts = set()
    for e in AC.parse_ents(mapfile):
        c = e.get('classname', '')
        if (c.startswith('info_player') or c.startswith('team_') and 'spawn' in c) and e.get('origin'):
            o = np.array([float(v) for v in e['origin'].split()], np.float32)
            for dz in (0, 4, 8, -8, 16):
                ar = AC.point_area(planes, nodes, o + [0, 0, dz])
                if ar > 0: starts.add(ar); break
    seen = set(starts); dq = deque(starts)
    while dq:
        x = dq.popleft()
        for y in adj[x]:
            if y not in seen: seen.add(y); dq.append(y)
    keep = np.zeros(len(F), bool)
    for i, p in enumerate(F):
        for dz in (25, 32, 16):
            ar = AC.point_area(planes, nodes, np.array([p[0], p[1], p[2] + dz], np.float32))
            if ar > 0:
                keep[i] = ar in seen; break
    return keep


def wquant(v, w, q):
    o = np.argsort(v); c = np.cumsum(w[o]); c /= c[-1]
    return float(np.interp(q, c, v[o]))


def clusters(cells, flag, cell):
    """connected groups of flagged cells -> [(area, centre, mean lum, n)]"""
    keys = [k for k, v in cells.items() if flag(v)]
    left = set(keys); groups = []
    while left:
        k = left.pop(); g = [k]; q = [k]
        while q:
            c = q.pop()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
                nb = (c[0] + d[0], c[1] + d[1], c[2])
                if nb in left: left.remove(nb); g.append(nb); q.append(nb)
        A = sum(cells[c][0] for c in g)
        L = sum(cells[c][1] for c in g) / max(A, 1e-9)
        ctr = np.array([(c[0] + 0.5) * cell for c in g]).mean(), np.array([(c[1] + 0.5) * cell for c in g]).mean(), g[0][2] * 64
        groups.append((A, ctr, L, len(g)))
    return sorted(groups, key=lambda t: -t[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bsp'); ap.add_argument('--map'); ap.add_argument('--aas', help='maps/X.aas: count only floor bots can reach from the spawns')
    ap.add_argument('--png')
    ap.add_argument('--dark', type=float, default=30); ap.add_argument('--bright', type=float, default=200)
    ap.add_argument('--cell', type=float, default=128)
    ap.add_argument('--max-dark-pct', type=float, default=10.0); ap.add_argument('--max-bright-pct', type=float, default=35.0)
    a = ap.parse_args()
    V, I, S, LM, SH = read_bsp(a.bsp)
    F = floor_samples(V, I, S, LM, SH)
    if not len(F): raise SystemExit('no lightmapped floor found (was -light run?)')
    if a.aas and a.map:
        F = F[aas_mask(F, a.aas, a.map)]
        if not len(F): raise SystemExit('no floor sample in a reachable AAS area (stale .aas?)')
    elif a.map:
        m, G = reachable_mask(F, a.map)
        F = F[m]
        if not len(F): raise SystemExit('no reachable floor sample (spawns outside the map?)')
    x, y, z, w, L = F.T
    med = wquant(L, w, 0.5); p10 = wquant(L, w, 0.1); p90 = wquant(L, w, 0.9)
    dark = w[L < a.dark].sum() / w.sum() * 100; bright = w[L > a.bright].sum() / w.sum() * 100
    print(f'walkable floor {w.sum() / 1e6:.2f} M sq u, {len(F)} samples, {len(LM)} lightmap pages')
    print(f'luminance (raw lightmap, game shows ~x2): median {med:.0f}, p10 {p10:.0f}, p90 {p90:.0f}')
    print(f'dark (< {a.dark:g}): {dark:.1f} %   blown out (> {a.bright:g}): {bright:.1f} %')
    cells = {}
    for xi, yi, zi, wi, li in zip(np.floor(x / a.cell), np.floor(y / a.cell), np.round(z / 64), w, L):
        k = (int(xi), int(yi), int(zi)); c = cells.setdefault(k, [0.0, 0.0]); c[0] += wi; c[1] += wi * li
    cl = {k: (v[0], v[1], v[1] / v[0]) for k, v in cells.items()}
    for title, flag in (('darkest areas', lambda v: v[2] < a.dark), ('blown-out areas', lambda v: v[2] > a.bright)):
        g = clusters({k: (v[0], v[1]) for k, v in cl.items() if flag(v)}, lambda v: True, a.cell)
        if g:
            print(f'{title} (centre x y z: mean lum, size):')
            for A, c, Lm, n in g[:10]:
                print(f'   {c[0]:7.0f} {c[1]:7.0f} {c[2]:6.0f}: {Lm:5.1f}  {n} cell(s) {A / 1e3:.0f}k sq u')
    if a.png:
        from PIL import Image, ImageDraw
        x0, x1, y0, y1 = x.min(), x.max(), y.min(), y.max()
        sc = 900 / max(x1 - x0, y1 - y0, 1)
        im = Image.new('RGB', (int((x1 - x0) * sc) + 20, int((y1 - y0) * sc) + 20), (30, 30, 40)); d = ImageDraw.Draw(im)
        top = {}
        for k, v in cl.items():
            if (k[0], k[1]) not in top or k[2] > top[(k[0], k[1])][0]: top[(k[0], k[1])] = (k[2], v[2])
        for (cx, cy), (_, Lm) in top.items():
            px0 = (cx * a.cell - x0) * sc + 10; py0 = (y1 - (cy + 1) * a.cell) * sc + 10
            col = (200, 40, 40) if Lm < a.dark else (250, 250, 120) if Lm > a.bright else (int(Lm), int(Lm), int(Lm))
            d.rectangle([px0, py0, px0 + a.cell * sc, py0 + a.cell * sc], fill=col)
        im.save(a.png); print(f'top-down map (highest floor per cell; red = dark, yellow = blown out): {a.png}')
    ok = dark <= a.max_dark_pct and bright <= a.max_bright_pct
    print('RESULT:', 'OK' if ok else f'{"too dark " if dark > a.max_dark_pct else ""}{"blown out" if bright > a.max_bright_pct else ""}'.strip())
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    try: main()
    except BrokenPipeError: pass
