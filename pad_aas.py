#!/usr/bin/env python3
"""pad_aas.py - where does bspc think each jump pad lands? (the ground truth for bots)

    python3 pad_aas.py maps/X.aas maps/X.map [--spots maps/X.spots.json] [--tol 220]

pad_check.py flies the pads the way the game does. bspc builds the bots' jump-pad links with its own simulation
(be_aas_reach.c AAS_Reachability_JumpPad: 10 % more horizontal speed than the game, 0.1 s frames, at most 3 s) and
its flights come out lower and shorter than the game's. When its flight hits an edge it ends there, in mid-air, and
bots never take the pad (padgarage: the roof and loft pads; padbakery / padmuseum: "raise the apex 60-70u").

For every trigger_push this reads the jump-pad reachability from the .aas and prints its end point, whether that
area is grounded, and the distance to the intended landing (from woplib's spots.json). FAIL when a pad has no
link, ends in a non-grounded (mid-air) area, or ends more than --tol from where it should land.
Fixes: more apex (or start the pad further back) so the flight crosses edges higher; land further from edges.
"""
import os, sys, json, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aas_check as AC
import audit_map as AM

JUMPPAD = 18


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('aas'); ap.add_argument('map'); ap.add_argument('--spots'); ap.add_argument('--tol', type=float, default=220)
    a = ap.parse_args()
    planes, areas, sets, reach, nodes = AC.load_aas(a.aas)
    sp_path = a.spots or os.path.splitext(a.map)[0] + '.spots.json'
    spots = json.load(open(sp_path)) if os.path.exists(sp_path) else {}
    by_target = {tuple(int(round(v)) for v in p['target']): p for p in spots.get('pads', [])}
    ents = AM.parse(a.map)
    tn = {e['kv']['targetname']: e for e in ents if 'targetname' in e['kv']}
    fails = 0
    for ei, e in enumerate(ents):
        if e['kv'].get('classname') != 'trigger_push': continue
        P = [AM.planes_of(b) for b in e['brushes']]
        P = [p for p in P if p]
        if not P: continue
        mn, mx = AM.brush_bounds(P[0])
        o = (mn + mx) / 2
        t = tn.get(e['kv'].get('target', ''))
        tgt = tuple(int(round(float(v))) for v in t['kv']['origin'].split()) if t else None
        info = by_target.get(tgt, {})
        name = info.get('name', f'ent{ei}')
        # the pad's own area: probe the trigger volume
        area = 0
        for dz in (0, -8, 8, -16, 16, 24):
            area = AC.point_area(planes, nodes, np.array([o[0], o[1], o[2] + dz], np.float32))
            if area > 0: break
        links = []
        if area > 0:
            s = sets[area]
            links = [r for r in reach[s['freach']:s['freach'] + s['nreach']] if int(r['type']) & 0xFFFFFF == JUMPPAD]
        if not links:
            print(f'  FAIL {name:14s} no bspc jump-pad link (pad area {area})'); fails += 1; continue
        r = links[0]
        end = np.array(r['end'], float); ta = int(r['area'])
        grounded = bool(int(sets[ta]['flags']) & 1)
        msg = f'{name:14s} bspc lands at {np.round(end).astype(int).tolist()} area {ta}{"" if grounded else " (MID-AIR)"}'
        bad = not grounded
        if info.get('land'):
            L = np.array(info['land'][:2] + [info['land'][2] + 24], float)
            d = float(np.linalg.norm(end - L))
            msg += f', {d:.0f}u from the intended landing {[int(v) for v in info["land"]]}'
            bad |= d > a.tol
        print(('  FAIL ' if bad else '  ok   ') + msg)
        fails += bad
    print('RESULT:', 'OK' if not fails else f'{fails} pad(s) bspc does not land where intended')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
