#!/usr/bin/env python3
"""Audit a Quake 3 / WoP .map for the standing mapping rules.

    python3 audit_map.py maps/mymap.map [--md3root <dir holding models/>] [--shaders <dir with scripts/>] [-v]

Checks
  1. brush overlaps: any two brushes (world or brush entities) whose interiors intersect by more than
     0.5u. Pure decoration (spray/frond/sail/cable shaders) is skipped. Clip brushes are only
     checked against other brushes, not against models.
  2. point entities: item/weapon/ammo bounding box (+-15) and spawn-point player box
     (-15,-15,-24..15,15,32) must not intersect solid brushes; nothing may sit inside a trigger.
  3. misc_model support: model's lowest vertices (scaled/rotated) must rest on a solid or water-floor
     surface within 3u below; reports % of the footprint that is unsupported (overhang) and floaters. A model whose
     vertices touch a wall brush (>= 2% of them within 3u) counts as mounted there (wreaths, frames); one whose top
     touches a ceiling brush counts as hanging from it (stars and mistletoe on threads).
  4. misc_model vs brush: model bbox shrunk by 25% must not sink into solid brushes.
     misc_externalmodel (animated, frame 0) gets the same support/sink checks.
  5. counts: weapons, ammo per weapon type (rule: 3-6), spawns, models.
--shaders: read every scripts/*.shader below the given dir(s) and classify brushes by surfaceparm
  (water/slime/lava -> liquid, fog -> ignored (a fog volume may enclose everything), nonsolid -> decoration)
  instead of guessing from the texture name.
Exit status 1 if anything failed.
"""
import re, sys, os, math, json, argparse
import numpy as np
from scipy.optimize import linprog

DECOR = ('rainbow', 'foam', 'nodraw_ns', 'spray', 'frond', 'sail', 'cable', 'waterfall', 'caustic', 'beam_ns', 'glow_ns', 'leaf')
WATER = ('water',)
TRIGGER = ('common/trigger',)
CLIP = ('clip',)
SKIP_TEX = ('common/origin', 'common/hint', 'common/skip')
MOVERS = {'func_bobbing', 'func_door', 'func_plat', 'func_rotating', 'func_train', 'func_pendulum'}


def parse(path):
    ents, cur, brush, depth, in_patch = [], None, None, 0, False
    for raw in open(path, errors='ignore'):
        line = raw.strip()
        if not line or line.startswith('//'): continue
        if line.startswith('patchDef'): in_patch = True
        if line == '{':
            depth += 1
            if depth == 1: cur = {'kv': {}, 'brushes': []}
            elif depth == 2: brush = []
            continue
        if line == '}':
            if depth == 2:
                if not in_patch and brush: cur['brushes'].append(brush)
                in_patch = False; brush = None
            elif depth == 1: ents.append(cur)
            depth -= 1
            continue
        if in_patch: continue
        if depth == 1:
            m = re.match(r'"([^"]+)"\s+"([^"]*)"', line)
            if m: cur['kv'][m.group(1)] = m.group(2)
        elif depth == 2 and line.startswith('('):
            nums = re.findall(r'\(\s*([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)\s*\)', line)
            tex = line.split(')')[3].split()[0]
            v = [tuple(float(x) for x in t) for t in nums[:3]]
            brush.append((v[0], v[1], v[2], tex))
    return ents


def planes_of(brush):
    P = []
    for a, b, c, tex in brush:
        a, b, c = np.array(a), np.array(b), np.array(c)
        n = np.cross(a - b, c - b); l = np.linalg.norm(n)
        if l < 1e-9: return None
        n = n / l; P.append((n, float(n @ a)))
    return P


def brush_bounds(P):
    A = np.array([p[0] for p in P]); d = np.array([p[1] for p in P])
    mn, mx = [], []
    for k in range(3):
        c = np.zeros(3)
        for sgn, lst in ((1, mn), (-1, mx)):
            c[:] = 0; c[k] = sgn
            r = linprog(c, A_ub=A, b_ub=d, bounds=[(None, None)] * 3, method='highs')
            lst.append(sgn * r.fun if r.status == 0 else (-1e9 if sgn == 1 else 1e9))
    return np.array(mn), np.array(mx)


def overlap_depth(P1, P2):
    """max t such that a point is >= t inside all planes of both brushes"""
    A = np.array([np.append(p[0], 1.0) for p in P1 + P2]); d = np.array([p[1] for p in P1 + P2])
    r = linprog([0, 0, 0, -1], A_ub=A, b_ub=d, bounds=[(None, None)] * 3 + [(None, 64)], method='highs')
    return -r.fun if r.status == 0 else -1


def inside(P, p, eps=0.01):
    return all(n @ p - d < -eps for n, d in P)


def box_overlap(P, mn, mx, eps=0.5):
    """does axis box (mn,mx) intersect brush interior by > eps"""
    Pb = [(np.array(v), float(np.array(v) @ (mx if sum(v) > 0 else mn))) for v in
          ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    Pb = [(n, n @ (mx if n.sum() > 0 else mn)) for n, _ in Pb]
    return overlap_depth(P, Pb) > eps


SHADER_PARMS = {}   # 'textures/x/y' -> set of surfaceparms (filled by load_shaders)


def load_shaders(dirs):
    """parse scripts/*.shader under each dir; remember surfaceparms per shader name"""
    for d in dirs:
        for root, _, files in os.walk(d):
            for fn in files:
                if not fn.endswith('.shader'): continue
                txt = re.sub(r'//[^\n]*', '', open(os.path.join(root, fn), errors='ignore').read())
                depth = 0; name = None; parms = set(); tok_iter = re.finditer(r'\{|\}|[^\s{}]+(?:[ \t]+[^\s{}]+)*', txt)
                for m in tok_iter:
                    t = m.group(0)
                    if t == '{': depth += 1; continue
                    if t == '}':
                        depth -= 1
                        if depth == 0 and name: SHADER_PARMS[name] = parms; name = None
                        continue
                    if depth == 0: name = t.strip().lower(); parms = set()
                    elif depth == 1 and t.lower().startswith('surfaceparm'):
                        parms.add(t.split()[1].lower())


def parm_kind(tex):
    p = SHADER_PARMS.get('textures/' + tex.lower())
    if p is None: return None
    if 'fog' in p: return 'fog'                 # fog volumes legitimately contain geometry
    if p & {'water', 'slime', 'lava'}: return 'water'
    if 'nonsolid' in p: return 'decor'
    return 'solid'


def kind(texs):
    t = [x.lower() for x in texs]
    if SHADER_PARMS:
        pk = [parm_kind(x) for x in t]
        if 'fog' in pk: return 'fog'
        if all(k == 'decor' or 'caulk' in x or 'nodraw' in x for k, x in zip(pk, t)) and 'decor' in pk: return 'decor'
        if 'water' in pk and not any(any(s in x for s in TRIGGER) for x in t): return 'water'
    if all(any(s in x for s in SKIP_TEX) for x in t): return 'skip'
    if all('botclip' in x for x in t): return 'decor'          # bots only (nonsolid for players/shots) even without --shaders
    if all(any(s in x for s in DECOR) or 'caulk' in x or 'nodraw' in x for x in t) and any(any(s in x for s in DECOR) for x in t):
        return 'decor'
    if any(any(s in x for s in TRIGGER) for x in t): return 'trigger'
    if any('water' in x.split('/')[-1] and 'waterfall' not in x for x in t): return 'water'
    if all(any(s in x for s in CLIP) for x in t): return 'clip'
    return 'solid'


def model_points(md3root, model, scale, ang, cache={}):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import md3tool
    key = model
    if key not in cache:
        p = None
        for root in (md3root if isinstance(md3root, list) else [md3root]):      # first root that has the file wins
            q = os.path.join(root, model)
            if not os.path.exists(q):
                d = os.path.dirname(q); b = os.path.basename(q).lower()
                alt = [f for f in os.listdir(d) if f.lower() == b] if os.path.isdir(d) else []
                q = os.path.join(d, alt[0]) if alt else None
            if q: p = q; break
        if not p: cache[key] = None
        else:
            m = md3tool.load(p)
            cache[key] = np.concatenate([s['verts'] for s in m['surfaces']])
    v = cache[key]
    if v is None: return None
    v = v * scale
    return v @ rot_matrix(ang).T


def rot_matrix(ang):
    """q3map2 misc_model: angles (pitch yaw roll) -> R = Rz(yaw) Ry(pitch) Rx(roll), v' = R v"""
    p, y, r = [math.radians(a) for a in ang]
    Rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
    Ry = np.array([[math.cos(p), 0, math.sin(p)], [0, 1, 0], [-math.sin(p), 0, math.cos(p)]])
    Rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('--md3root', action='append', default=None, help='dir holding models/ (repeat for several, e.g. WoP + the map folder)')
    ap.add_argument('-v', action='store_true')
    ap.add_argument('--maxlist', type=int, default=40)
    ap.add_argument('--shaders', action='append', default=[], help='dir(s) holding scripts/*.shader')
    a = ap.parse_args()
    if a.shaders: load_shaders(a.shaders)
    ents = parse(a.map)
    B = []      # (planes, kind, ent index, brush index, mn, mx, texs)
    for ei, e in enumerate(ents):
        cls = e['kv'].get('classname', '')
        for bi, b in enumerate(e['brushes']):
            P = planes_of(b)
            if P is None:
                print(f'DEGENERATE brush ent {ei} brush {bi}'); continue
            texs = [t[3] for t in b]
            k = kind(texs)
            if cls.startswith('trigger_'): k = 'trigger'
            if k == 'skip': continue
            mn, mx = brush_bounds(P)
            B.append((P, k, ei, bi, mn, mx, texs, cls))
    fails = 0
    # 1. overlaps
    idx = [i for i, b in enumerate(B) if b[1] not in ('decor', 'fog')]
    mns = np.array([B[i][4] for i in idx]); mxs = np.array([B[i][5] for i in idx])
    ov = []
    for ii, i in enumerate(idx):
        cand = np.where(np.all(mns[ii + 1:] < mxs[ii] - 0.5, 1) & np.all(mxs[ii + 1:] > mns[ii] + 0.5, 1))[0] + ii + 1
        for jj in cand:
            j = idx[jj]
            if B[i][2] == B[j][2] and B[i][1] == 'trigger' and B[j][1] == 'trigger': continue
            ks = {B[i][1], B[j][1]}
            if 'water' in ks and ('trigger' in ks or 'clip' in ks or {B[i][7], B[j][7]} & MOVERS): continue
            dep = overlap_depth(B[i][0], B[j][0])
            if dep > 0.5:
                ov.append((dep, i, j))
    print(f'[overlaps] {len(ov)} brush pairs intersect')
    for dep, i, j in sorted(ov, reverse=True)[:a.maxlist]:
        bi, bj = B[i], B[j]
        print(f'   ent{bi[2]}/b{bi[3]} {bi[1]} {bi[6][0]} {bi[4].astype(int)}..{bi[5].astype(int)}  X  '
              f'ent{bj[2]}/b{bj[3]} {bj[1]} {bj[6][0]} {bj[4].astype(int)}..{bj[5].astype(int)}  depth {dep:.1f}')
    fails += len(ov)
    # 2. point entities
    solids = [b for b in B if b[1] in ('solid', 'clip')]
    trig = [b for b in B if b[1] == 'trigger']
    smn = np.array([b[4] for b in solids]); smx = np.array([b[5] for b in solids])
    bad = []
    counts = {}
    for ei, e in enumerate(ents):
        kv = e['kv']; c = kv.get('classname', '')
        counts[c] = counts.get(c, 0) + 1
        if 'origin' not in kv or c in ('misc_model', 'misc_externalmodel', 'path_corner', 'worldspawn', 'light', 'target_position', 'info_null',
                                        'target_speaker', 'info_notnull', 'target_location') or e['brushes']: continue
        o = np.array([float(v) for v in kv['origin'].split()])
        if c.startswith(('weapon_', 'ammo_', 'item_', 'holdable_')):
            mn, mx = o - 15, o + 15
        elif c.startswith(('info_player', 'team_')) and ('player' in c or 'spawn' in c) or c == 'misc_teleporter_dest':
            mn, mx = o + np.array([-15, -15, -24]), o + np.array([15, 15, 32])
        elif c == 'station_health':
            mn, mx = o + np.array([-40, -40, 1]), o + np.array([40, 40, 64])
        else:
            mn, mx = o - 1, o + 1
        cand = np.where(np.all(smn < mx, 1) & np.all(smx > mn, 1))[0]
        hit = [solids[k] for k in cand if box_overlap(solids[k][0], mn, mx, 0.25)]
        intrig = [t for t in trig if inside(t[0], o) and t[7] != 'trigger_multiple']
        if hit or intrig:
            what = (f'solid ent{hit[0][2]}/b{hit[0][3]} {hit[0][6][0]}' if hit else f'inside {intrig[0][7]}')
            bad.append(f'   {c} at {o.astype(int)}: {what}')
        # floor check for items (they drop to floor): must have something below within 512
    print(f'[point entities] {len(bad)} problems')
    for s in bad[:a.maxlist]: print(s)
    fails += len(bad)
    # 3/4 models
    mbad = []
    if a.md3root:
        floors = [b for b in B if b[1] in ('solid', 'clip', 'water')]
        fmn = np.array([b[4] for b in floors]); fmx = np.array([b[5] for b in floors])
        for ei, e in enumerate(ents):
            kv = e['kv']
            if kv.get('classname') not in ('misc_model', 'misc_externalmodel'): continue
            o = np.array([float(v) for v in kv['origin'].split()])
            s = float(kv.get('modelscale', 1))
            if 'angles' in kv: ang = [float(v) for v in kv['angles'].split()]
            else: ang = [0, float(kv.get('angle', 0)), 0]
            v = model_points(a.md3root, kv['model'], s, ang)
            if v is None:
                mbad.append(f'   ent{ei} {kv["model"]}: model file not found'); continue
            v = v + o
            zb = v[:, 2].min()
            ring = v[v[:, 2] <= zb + max(2.0, 0.04 * (v[:, 2].max() - zb))]
            # subsample
            if len(ring) > 60: ring = ring[np.linspace(0, len(ring) - 1, 60).astype(int)]
            unsup = 0
            for p in ring:
                q = np.array([p[0], p[1], zb - 1.5])
                cand = np.where(np.all(fmn <= q + 0.01, 1) & np.all(fmx >= q - 0.01, 1))[0]
                ok = False
                for k in cand:
                    P = floors[k][0]
                    if all(n @ q - d <= 0.01 for n, d in P) and not all(n @ (q + [0, 0, 4.0]) - d < -0.5 for n, d in P):
                        ok = True; break
                if not ok: unsup += 1
            frac = unsup / max(1, len(ring))
            attached = False
            if frac > 0.2:
                # wall- or ceiling-mounted (wreath, picture frame, hanging star): enough vertices touch a solid/clip
                # brush away from the bottom ring
                sv = v[::max(1, len(v) // 3000)]
                sv = sv[sv[:, 2] > zb + max(2.0, 0.04 * (v[:, 2].max() - zb))]
                touch = 0; hang = False
                vmn, vmx = v.min(0) - 3, v.max(0) + 3
                cand = [b for b in B if b[1] in ('solid', 'clip') and np.all(b[4] <= vmx) and np.all(b[5] >= vmn)]
                for b in cand:
                    A_ = np.array([n for n, d in b[0]]); d_ = np.array([d for n, d in b[0]])
                    hit = np.all(sv @ A_.T - d_ <= 3.0, 1)
                    touch += int(np.sum(hit))
                    hang |= bool(np.any(sv[hit][:, 2] >= v[:, 2].max() - 2)) if hit.any() else False
                # mounted on a wall (>= 2% of vertices touch) or hanging from a ceiling (its top touches a brush)
                attached = len(sv) > 0 and touch >= 3 and (touch >= 0.02 * len(sv) or hang)
                if attached: frac = 0.0
            # sink check: shrunk bbox vs solids
            mn, mx = v.min(0), v.max(0); c0 = (mn + mx) / 2; h = (mx - mn) / 2 * 0.75
            smn2, smx2 = c0 - h, c0 + h
            smn2[2] = max(smn2[2], zb + 2)
            cand = np.where(np.all(smn < smx2, 1) & np.all(smx > smn2, 1))[0]
            sink = [solids[k] for k in cand if solids[k][1] == 'solid' and box_overlap(solids[k][0], smn2, smx2, 2.0)]
            # hollow models (a bell, an arch) have empty bbox corners: keep only brushes that really hold model vertices
            sink = [b for b in sink if any(all(n @ p - d < -2.0 for n, d in b[0]) for p in v[::max(1, len(v) // 4000)])]
            if frac > 0.2 or sink:
                msg = f'   ent{ei} {kv["model"].split("mapobjects/")[-1]} at {o.astype(int)} s{s:g}: '
                if frac > 0.2: msg += f'{frac * 100:.0f}% of base unsupported (base z {zb:.1f}) '
                if sink: msg += f'intersects solid ent{sink[0][2]}/b{sink[0][3]} {sink[0][6][0]}'
                mbad.append(msg)
    print(f'[models] {len(mbad)} problems ({counts.get("misc_model", 0)} models, {counts.get("misc_externalmodel", 0)} external)')
    for s in mbad[:a.maxlist]: print(s)
    fails += len(mbad)
    # 5. counts
    W = ['balloony', 'betty', 'boaster', 'bubbleg', 'imperius', 'pumper', 'splasher']
    print('[pickups]')
    for w in W:
        na = counts.get('ammo_' + w, 0); nw = counts.get('weapon_' + w, 0)
        flag = '' if (nw == 0 or 3 <= na <= 6) else '   <-- rule: 3-6 ammo spots'
        if flag: fails += 1
        print(f'   {w:9s} weapons {nw}  ammo {na}{flag}')
    nn = counts.get('ammo_nipper', 0)          # Nipper is the starting weapon: no pickup, but the ammo rule still applies
    nflag = '' if (nn == 0 or 3 <= nn <= 6) else '   <-- rule: 3-6 ammo spots'
    if nflag: fails += 1
    print(f'   nipper    (start)     ammo {nn}{nflag}')
    others = {k: v for k, v in counts.items() if k.startswith(('item_', 'holdable_', 'station_'))}
    print('   ' + ', '.join(f'{k} {v}' for k, v in sorted(others.items())))
    print(f'   spawns {counts.get("info_player_deathmatch", 0)}')
    print('RESULT:', 'OK' if not fails else f'{fails} problem(s)')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
