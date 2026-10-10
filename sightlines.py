#!/usr/bin/env python3
"""Find long unobstructed sightlines at eye height (rule: break long sightlines with models).

    python3 sightlines.py maps/mymap.map out.png [--md3bounds md3bounds.json] [--step 128] [--min 1600]
                          [--bounds x0,y0,x1,y1] [--zmax 64] [--underlay topdown.png --uview x0,y0,x1,y1]

Eye points: a grid over the map; for each, the floor is found by a downward ray (from `--zmax` above
deck level), eye = floor + 48. Rays in 16 horizontal directions are cast against solid/clip brushes
and (shrunken) misc_model boxes. Rays longer than --min are drawn red on a top-down plot and the
worst corridors are listed. Water, triggers and decoration (spray/fronds) do not block.
"""
import sys, os, math, json, argparse
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_map as A


def load_blockers(mapfile, bounds_json, md3scale=0.6):
    ents = A.parse(mapfile)
    planes = []      # list of (N,4) arrays
    for e in ents:
        cls = e['kv'].get('classname', '')
        if cls.startswith('trigger_'): continue
        for b in e['brushes']:
            k = A.kind([t[3] for t in b])
            if k not in ('solid', 'clip'): continue
            P = A.planes_of(b)
            if P: planes.append(np.array([[*n, d] for n, d in P]))
    nb = len(planes)
    if bounds_json and os.path.exists(bounds_json):
        B = json.load(open(bounds_json))
        for e in ents:
            kv = e['kv']
            if kv.get('classname') != 'misc_model': continue
            b = B.get(kv['model'])
            if not b: continue
            o = np.array([float(v) for v in kv['origin'].split()]); s = float(kv.get('modelscale', 1))
            mn = np.array(b['min']) * s; mx = np.array(b['max']) * s
            c = (mn + mx) / 2; h = (mx - mn) / 2 * md3scale
            r = max(h[0], h[1])
            lo = o + np.array([c[0] - r, c[1] - r, mn[2]]); hi = o + np.array([c[0] + r, c[1] + r, mx[2]])
            if hi[2] - lo[2] < 40: continue      # small props do not block a view
            planes.append(np.array([[1, 0, 0, hi[0]], [-1, 0, 0, -lo[0]], [0, 1, 0, hi[1]], [0, -1, 0, -lo[1]],
                                    [0, 0, 1, hi[2]], [0, 0, -1, -lo[2]]], float))
    return planes, nb


def cast(planes, O, D, tmax_init=1e5):
    """O,D: (R,3). returns nearest hit distance per ray"""
    best = np.full(len(O), tmax_init)
    for P in planes:
        n = P[:, :3]; d = P[:, 3]
        denom = D @ n.T                      # (R,k)
        dist = O @ n.T - d                   # (R,k)
        with np.errstate(divide='ignore', invalid='ignore'):
            t = -dist / denom
        enter = denom < -1e-9; exit_ = denom > 1e-9; par = ~(enter | exit_)
        tmin = np.where(enter, t, -np.inf).max(1)
        tmx = np.where(exit_, t, np.inf).min(1)
        miss = (par & (dist > 0)).any(1)
        hit = (~miss) & (tmin <= tmx) & (tmx > 0)
        th = np.maximum(tmin, 0)
        upd = hit & (th < best)
        best[upd] = th[upd]
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map'); ap.add_argument('out')
    ap.add_argument('--md3bounds', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'md3bounds.json'))
    ap.add_argument('--step', type=int, default=128)
    ap.add_argument('--min', type=float, default=1600)
    ap.add_argument('--bounds', default='-2048,-1792,2048,1792')
    ap.add_argument('--zmax', type=float, default=64)
    ap.add_argument('--dirs', type=int, default=16)
    a = ap.parse_args()
    x0, y0, x1, y1 = [float(v) for v in a.bounds.split(',')]
    planes, nb = load_blockers(a.map, a.md3bounds)
    print(f'{nb} brushes + {len(planes) - nb} model boxes as blockers')
    xs = np.arange(x0 + a.step / 2, x1, a.step); ys = np.arange(y0 + a.step / 2, y1, a.step)
    G = np.array([(x, y) for y in ys for x in xs])
    O = np.column_stack([G, np.full(len(G), a.zmax)])
    floor = a.zmax - cast(planes, O, np.tile([0, 0, -1.0], (len(G), 1)), 4000)
    ok = floor > -12           # dry floors only (river/pool bottoms are excluded)
    E = np.column_stack([G[ok], floor[ok] + 48])
    angs = np.arange(a.dirs) * 2 * math.pi / a.dirs
    D = np.array([(math.cos(t), math.sin(t), 0) for t in angs])
    RO = np.repeat(E, a.dirs, 0); RD = np.tile(D, (len(E), 1))
    L = cast(planes, RO, RD, 8000)
    # clip to map bounds
    with np.errstate(divide='ignore'):
        tx = np.where(RD[:, 0] > 0, (x1 - RO[:, 0]) / RD[:, 0], np.where(RD[:, 0] < 0, (x0 - RO[:, 0]) / RD[:, 0], np.inf))
        ty = np.where(RD[:, 1] > 0, (y1 - RO[:, 1]) / RD[:, 1], np.where(RD[:, 1] < 0, (y0 - RO[:, 1]) / RD[:, 1], np.inf))
    L = np.minimum(L, np.minimum(tx, ty))
    S = 1024 / (x1 - x0)
    W, H = 1024, int((y1 - y0) * S)
    im = Image.new('RGB', (W, H), (24, 28, 34)); d = ImageDraw.Draw(im)
    def px(x, y): return ((x - x0) * S, (y1 - y) * S)
    # floor heights as background
    for (gx, gy), f in zip(G[ok], floor[ok]):
        c = int(np.clip(90 + f * 0.25, 30, 200))
        d.rectangle([px(gx - a.step / 2, gy + a.step / 2), px(gx + a.step / 2, gy - a.step / 2)], fill=(c, c, c))
    # blockers at eye height
    for P in planes:
        n = P[:, :3]; dd = P[:, 3]
        zs = [dd[i] * n[i, 2] for i in range(len(n)) if abs(n[i, 2]) > 0.99]
        if len(P) == 6 and len(zs) == 2 and min(zs) - 1 < 0 + 0 and False: pass
    for P in planes:
        # sample brush footprint at z=48 by projecting box-like brushes
        n = P[:, :3]; dd = P[:, 3]
        if not (np.all(np.abs(n[:, 2]) < 1e-6) or True): continue
        # bounds via axis planes
        bx = [dd[i] if n[i, 0] > 0.999 else None for i in range(len(n))]
        xm = [dd[i] for i in range(len(n)) if n[i, 0] > 0.999]; xn = [-dd[i] for i in range(len(n)) if n[i, 0] < -0.999]
        ym = [dd[i] for i in range(len(n)) if n[i, 1] > 0.999]; yn = [-dd[i] for i in range(len(n)) if n[i, 1] < -0.999]
        zm = [dd[i] for i in range(len(n)) if n[i, 2] > 0.999]; zn = [-dd[i] for i in range(len(n)) if n[i, 2] < -0.999]
        if xm and xn and ym and yn and zm and zn and zn[0] < 60 and zm[0] > 40:
            d.rectangle([px(xn[0], ym[0]), px(xm[0], yn[0])], fill=(10, 40, 90))
    long_ = np.where(L >= a.min)[0]
    for i in long_:
        o = RO[i]; e = o + RD[i] * L[i]
        d.line([px(o[0], o[1]), px(e[0], e[1])], fill=(230, 40, 40), width=1)
    im.save(a.out)
    print(f'eye points {len(E)}, rays {len(L)}, rays >= {a.min:.0f}: {len(long_)} ({100 * len(long_) / len(L):.1f}%), '
          f'median {np.median(L):.0f}, p90 {np.percentile(L, 90):.0f}')
    # worst points
    per = L.reshape(len(E), a.dirs)
    worst = np.argsort(-per.max(1))[:12]
    for w in worst:
        k = per[w].argmax()
        print(f'   from {E[w].astype(int)} dir {math.degrees(angs[k]):5.1f}: {per[w, k]:.0f}u')


if __name__ == '__main__':
    main()
