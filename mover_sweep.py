#!/usr/bin/env python3
"""Check that every func_bobbing's swept volume (its brushes moved over +-height along its axis) stays clear of the
static solid brushes (world + other non-mover entities). Exact convex test via linear programming per brush pair.

    python3 mover_sweep.py maps/mymap.map [--shaders <dir with scripts/>]
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_map as AM


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--shaders', action='append', default=[])
    a = ap.parse_args()
    if a.shaders: AM.load_shaders(a.shaders); AM.add_common_parms()
    ents = AM.parse(a.map)
    statics, movers = [], []
    for e in ents:
        cls = e['kv'].get('classname', '')
        for b in e['brushes']:
            k = AM.kind([t[3] for t in b])
            P = AM.planes_of(b)
            if cls == 'func_bobbing':
                if k == 'solid': movers.append((e, P))
            elif k in ('solid', 'clip') and not cls.startswith('trigger_'):
                statics.append(P)
    bad = 0
    def verts(P):
        import itertools
        N = np.array([p[0] for p in P]); D = np.array([p[1] for p in P]); out = []
        for i, j, k in itertools.combinations(range(len(P)), 3):
            A = N[[i, j, k]]
            if abs(np.linalg.det(A)) < 1e-9: continue
            v = np.linalg.solve(A, D[[i, j, k]])
            if np.all(N @ v - D <= 0.01): out.append(v)
        return np.array(out)
    SV = [(P, verts(P)) for P in statics]
    for e, P in movers:
        kv = e['kv']; h = float(kv.get('height', 32)); sf = int(kv.get('spawnflags', 0))
        ax = 0 if sf & 1 else (1 if sf & 2 else 2)
        V = verts(P); d = np.zeros(3); d[ax] = h
        sweep = np.vstack([V - d, V + d])          # convex hull of start and end = swept volume (straight line)
        mn, mx = sweep.min(0), sweep.max(0)
        for SP, W in SV:
            if len(W) == 0 or np.any(W.min(0) >= mx - 0.5) or np.any(W.max(0) <= mn + 0.5): continue
            # separating-axis-free test: is any static vertex inside the sweep hull or vice versa (approx) -> use LP
            from scipy.optimize import linprog
            # find x in static brush and x = sum(l_i * sweep_i), l >= 0, sum l = 1, with 0.5u margin
            n = len(sweep)
            A_ub = []; b_ub = []
            for (nn, dd) in SP:
                A_ub.append(np.concatenate([np.array(nn) @ sweep.T * 1.0])); b_ub.append(dd - 0.5)
            res = linprog(np.zeros(n), A_ub=np.array(A_ub), b_ub=np.array(b_ub), A_eq=np.ones((1, n)), b_eq=[1],
                          bounds=[(0, None)] * n, method='highs')
            if res.status == 0:
                bad += 1
                print(f'  HIT  mover model {kv.get("model", "?")} sweep {mn.astype(int)}..{mx.astype(int)} vs static {W.min(0).astype(int)}..{W.max(0).astype(int)}')
    print('movers', len(movers), 'brushes; RESULT:', 'OK' if not bad else f'{bad} problem(s)')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
