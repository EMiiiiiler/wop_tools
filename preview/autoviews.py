#!/usr/bin/env python3
"""autoviews.py - camera positions for the review screenshots, generated from the map instead of written by hand.

    python3 preview/autoviews.py maps/X.map [--spots maps/X.spots.json] [--max 24]   -> prints name:x,y,z,yaw,pitch lines

One view per weapon, per secret room, per jump pad landing (from spots.json when present, else from the entities), and
two high overviews from opposite corners. Each camera is put 220-420u from its subject at eye height + a bit, on the
first of 16 directions whose camera point is in reachable air and whose line to the subject crosses no opaque brush
(same voxel flood lint_map uses), so screenshots show the thing, not the inside of a wall. Yaw follows Q3 (0 = +x,
90 = +y), pitch < 0 looks down - the format preview/shoot.py and bsp2scene --views take.
"""
import os, sys, json, math, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import audit_map as AM
import lint_map as LM
from woplib import wopdata


def clear_line(G, a, b, step=None):
    step = step or G.res * 0.5
    d = np.asarray(b, float) - np.asarray(a, float); L = np.linalg.norm(d)
    for t in np.arange(step, L - step, step):
        if not G.open_at(np.asarray(a) + d * (t / L)): return False
    return True


def look(cam, tgt):
    d = np.asarray(tgt, float) - np.asarray(cam, float)
    yaw = math.degrees(math.atan2(d[1], d[0])) % 360
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return yaw, pitch


def place(G, tgt, dists=(300, 220, 420, 160), heights=(90, 160, 40), prefer=None):
    """camera looking at tgt from a clear spot; prefer = yaw (deg) to try first (e.g. the side players arrive from)"""
    order = list(range(16))
    if prefer is not None: order.sort(key=lambda k: abs(((k * 22.5 - prefer) + 180) % 360 - 180))
    for dist in dists:
        for h in heights:
            for k in order:
                a = math.radians(k * 22.5)
                cam = np.array([tgt[0] + dist * math.cos(a), tgt[1] + dist * math.sin(a), tgt[2] + h])
                if G.open_at(cam) and clear_line(G, cam, tgt):
                    return cam, look(cam, tgt)
    return None, None


def views(mapfile, spots=None, maxn=24):
    ents = AM.parse(mapfile)
    BR = LM.Brushes(ents)
    G = LM.air_grid(BR, ents)
    subjects = []                       # (name, target xyz, prefer yaw)
    if spots:
        for w in spots.get('weapon', []):
            subjects.append((w['cls'].replace('weapon_', 'w_'), (w['x'], w['y'], w['floor'] + 24), None))
        for s in spots.get('secrets', []):
            subjects.append(('secret_' + s['name'], (s['dest'][0], s['dest'][1], s['dest'][2] + 40), None))
            mn, mx = np.array(s['mn']), np.array(s['mx'])
            subjects.append(('entry_' + s['name'], tuple((mn + mx) / 2), None))
        for p in spots.get('pads', []):
            subjects.append(('land_' + p['name'], (p['land'][0], p['land'][1], p['land'][2] + 24), None))
    else:
        for e in ents:
            c = e['kv'].get('classname', '')
            if c.startswith('weapon_') and 'origin' in e['kv']:
                o = [float(v) for v in e['kv']['origin'].split()]
                subjects.append((c.replace('weapon_', 'w_'), (o[0], o[1], o[2] + 8), None))
    out, seen = [], set()
    for name, tgt, pref in subjects:
        if len(out) >= maxn - 2: break
        n = name; k = 2
        while n in seen: n = f'{name}{k}'; k += 1
        cam, yp = place(G, np.array(tgt, float), prefer=pref)
        if cam is None: print(f'# no clear camera for {n} at {np.round(tgt).astype(int).tolist()}', file=sys.stderr); continue
        if any(np.linalg.norm(cam - c) < 64 and abs(yp[0] - q[0]) < 20 for _, c, q in out): continue   # same view twice
        seen.add(n); out.append((n, cam, yp))
    # overviews: as high as the air allows near two opposite corners, looking at the centre
    air = np.argwhere(G.air)
    if len(air):
        P = G.o + (air + 0.5) * G.res
        ctr = P.mean(0)
        for nm, sx, sy in (('overview_sw', -1, -1), ('overview_ne', 1, 1)):
            score = P[:, 2] * 2 + sx * P[:, 0] + sy * P[:, 1]
            cam = P[np.argmax(score)] - np.array([sx, sy, 1.0]) * G.res
            yaw, pitch = look(cam, ctr)
            out.append((nm, cam, (yaw, min(pitch, -15))))
    return [f'{n}:{c[0]:.0f},{c[1]:.0f},{c[2]:.0f},{yp[0]:.0f},{yp[1]:.0f}' for n, c, yp in out]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map'); ap.add_argument('--spots'); ap.add_argument('--max', type=int, default=24)
    a = ap.parse_args()
    sp = a.spots or os.path.splitext(a.map)[0] + '.spots.json'
    spots = json.load(open(sp)) if os.path.exists(sp) else None
    for v in views(a.map, spots, a.max): print(v)


if __name__ == '__main__':
    main()
