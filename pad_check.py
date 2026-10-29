#!/usr/bin/env python3
"""Fly every jump pad in a .map and report where the player really lands.

    python3 pad_check.py maps/mymap.map [--shaders <dir with scripts/>] [-v]

For each trigger_push -> target_position pair it computes the launch velocity exactly like Q3's AimAtTarget
(from the trigger brush's centre to the apex target, g_gravity 800) and steps a standing player box
(+-15, -24..+32) from the middle of the trigger's floor at 125 Hz. Solid and clip brushes (world + brush
entities, not triggers/decoration) block. Reports the first brush the box touches: if that happens while
still rising, or because of the horizontal motion (a side face / ledge edge), the arc is obstructed ("BLOCKED");
otherwise it prints the landing spot and the height of the player's feet there (slopes work too).
"""
import sys, os, math, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_map as AM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map'); ap.add_argument('--shaders', action='append', default=[]); ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    if a.shaders and hasattr(AM, 'load_shaders'):
        AM.load_shaders(a.shaders); AM.add_common_parms()
    ents = AM.parse(a.map)
    solids = []
    for e in ents:
        cls = e['kv'].get('classname', '')
        if cls.startswith('trigger_'): continue
        for b in e['brushes']:
            k = AM.kind([t[3] for t in b])
            if k not in ('solid', 'clip'): continue
            P = AM.planes_of(b)
            if P:
                mn, mx = AM.brush_bounds(P)
                solids.append((np.array([[*n, d] for n, d in P]), np.array(mn), np.array(mx)))
    def collide(bmn, bmx):
        for Pl, smn, smx in solids:
            if (bmn > smx).any() or (bmx < smn).any(): continue
            if AM.box_overlap([(r[:3], r[3]) for r in Pl], bmn, bmx, eps=0.5):
                return (smn, smx)
        return None
    targets = {e['kv'].get('targetname'): e for e in ents if e['kv'].get('classname') == 'target_position'}
    bad = 0
    for e in ents:
        if e['kv'].get('classname') != 'trigger_push': continue
        tg = targets.get(e['kv'].get('target'))
        if not tg or not e['brushes']: continue
        P = AM.planes_of(e['brushes'][0]); mn, mx = AM.brush_bounds(P)
        org = (np.array(mn) + np.array(mx)) / 2
        tgt = np.array([float(v) for v in tg['kv']['origin'].split()])
        h = tgt[2] - org[2]
        if h <= 0: print(e['kv']['target'], 'target below trigger'); continue
        t = math.sqrt(h / 400.0)
        d = tgt[:2] - org[:2]; dist = np.linalg.norm(d)
        vel = np.array([*(d / dist * dist / t if dist > 0 else (0, 0)), t * 800.0])
        pos = np.array([org[0], org[1], mn[2] + 24.0])
        dt = 1 / 125.0
        res = None
        for step in range(2000):
            npos = pos + vel * dt; nvel = vel.copy(); nvel[2] -= 800 * dt
            bmn = npos + np.array([-15, -15, -24]); bmx = npos + np.array([15, 15, 32])
            hit = collide(bmn, bmx)
            if hit is not None:
                # horizontal part of the step alone: if that is free, the vertical motion caused the contact
                hp = np.array([npos[0], npos[1], pos[2]])
                side = collide(hp + np.array([-15, -15, -24]), hp + np.array([15, 15, 32])) is not None
                landed = vel[2] <= 0 and not side
                res = ('land' if landed else 'BLOCKED', pos.copy(), pos[2] - 24, step * dt)
                break
            pos, vel = npos, nvel
        if res is None: res = ('NO LANDING', pos, None, 16)
        kind, p, floor, tt = res
        if kind != 'land': bad += 1
        print(f"{e['kv']['target']:<16} {kind:<8} at ({p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f})"
              + (f" floor {floor:.0f}" if floor is not None else '') + f"  t={tt:.2f}s")
    print('RESULT:', 'OK' if bad == 0 else f'{bad} pad(s) obstructed')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
