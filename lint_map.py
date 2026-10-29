#!/usr/bin/env python3
"""lint_map.py - static checks for the play-test complaints audit_map doesn't catch (no compile needed).

    python3 lint_map.py maps/X.map [--shaders <dir>]... [--md3root <dir>]... [--spots maps/X.spots.json]
                        [--arena scripts/X.arena] [--only names,entities,...] [-v]

Every check exists because a shipped map had the bug. Sections (FAIL = must fix, WARN = look at it):
  names     texture names with a 'textures/' prefix (renders untextured), upper case in texture/model/sound paths
            (pk3s on Linux are case sensitive), common/playerclip (does not exist in WoP)
  entities  forbidden classnames (item_berserker), unknown classnames, targets that point nowhere, trigger_push
            without target_position, trigger_teleport without misc_teleporter_dest, rotating movers with BOTH an origin
            key and an origin brush (leak), or with no origin brush, func_bobbing used as nonsolid decoration (bots try
            to ride it), point entities / model origins outside the world
  pads      flight time of every trigger_push (> 2.9 s: bspc makes no reachability), landings inside a hurt zone
            (+ 15u, a lava area for bspc) when the landing is known (--spots from woplib.kit)
  items     pickups resting on common/clip or botclip floors without spawnflags 1 (they fall through at spawn),
            pickups within 100u of a trigger_hurt, a table of every weapon's height (best weapons go on hard spots)
  water     every water body needs a way out: wadeable floor (<= 44u deep) next to dry floor <= 18u higher (steps or a
            ramp), or a teleporter in it. A sheer lip that needs a water jump trapped players.
  headroom  crouch-only floor (40-56u clearance under the player's 32u footprint) that is not a declared crawl space:
            on a stair it is a FAIL (the step before a ceiling edge needs step top + 56), elsewhere a WARN
  caulk     caulk faces that face open space inside the map (see-through holes in game); faces covered by an
            opaque brush or a model's bounds are fine. WARN with coordinates: look at them in the walk-through.
  rotors    func_rotating solid parts whose swept cylinder hits static brushes
  arena     arena types are valid WoP tokens; ctl/1lc have their lollies; the map name matches
  sounds    target_speaker noises not in woplib.wopdata.KNOWN_SOUNDS (pk3_check.py --game proves they exist)
Exit status 1 when anything FAILs.
"""
import os, sys, re, json, math, argparse
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_map as AM
from woplib import wopdata, padmath

FAILS = []; WARNS = []; INFO = []


def fail(sec, msg): FAILS.append((sec, msg))
def warn(sec, msg): WARNS.append((sec, msg))


# ------------------------------------------------------------------------------------------------ geometry
class Brushes:
    """all brushes with planes, bounds, kind and a column (vertical line) query"""

    def __init__(self, ents):
        self.B = []
        for ei, e in enumerate(ents):
            cls = e['kv'].get('classname', '')
            for bi, b in enumerate(e['brushes']):
                P = AM.planes_of(b)
                if P is None: continue
                texs = [t[3] for t in b]
                k = AM.kind(texs)
                if cls.startswith('trigger_'): k = 'trigger'
                if any('origin' in t.lower() for t in texs) and all('origin' in t.lower() for t in texs): k = 'skip'
                V = verts(P)
                if V is None or len(V) < 4: continue
                self.B.append(dict(P=P, k=k, ei=ei, bi=bi, cls=cls, texs=texs, faces=b, mn=V.min(0), mx=V.max(0),
                                   mover=cls in AM.MOVERS))
        self.mn = np.array([b['mn'] for b in self.B]); self.mx = np.array([b['mx'] for b in self.B])

    def of_kind(self, *ks, movers=False):
        return [b for b in self.B if b['k'] in ks and (movers or not b['mover'])]

    def near(self, mn, mx, kinds=None, movers=False):
        idx = np.where(np.all(self.mn < np.asarray(mx), 1) & np.all(self.mx > np.asarray(mn), 1))[0]
        out = [self.B[i] for i in idx]
        if kinds: out = [b for b in out if b['k'] in kinds]
        if not movers: out = [b for b in out if not b['mover']]
        return out


def verts(P, eps=0.01):
    A = np.array([p[0] for p in P]); d = np.array([p[1] for p in P])
    n = len(P); out = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                M = A[[i, j, k]]
                if abs(np.linalg.det(M)) < 1e-9: continue
                x = np.linalg.solve(M, d[[i, j, k]])
                if np.all(A @ x - d <= eps): out.append(x)
    return np.unique(np.round(np.array(out), 3), axis=0) if out else None


def column(b, x, y):
    """z interval of brush b on the vertical line (x, y), or None"""
    lo, hi = -1e9, 1e9
    for n, d in b['P']:
        nz = n[2]; r = d - n[0] * x - n[1] * y
        if abs(nz) < 1e-6:
            if r < -0.01: return None
        elif nz > 0: hi = min(hi, r / nz)
        else: lo = max(lo, r / nz)
    return (lo, hi) if hi - lo > 0.01 else None


def inside_any(bs, p, eps=0.5):
    for b in bs:
        if np.any(p < b['mn'] - eps) or np.any(p > b['mx'] + eps): continue
        if all(n @ p - d < -eps for n, d in b['P']): return b
    return None


def face_poly(b, fi):
    n, d = b['P'][fi]
    V = verts(b['P'])
    on = V[np.abs(V @ n - d) < 0.05]
    if len(on) < 3: return None, n
    c = on.mean(0); u = on[0] - c; u /= max(np.linalg.norm(u), 1e-9); v = np.cross(n, u)
    return on[np.argsort(np.arctan2((on - c) @ v, (on - c) @ u))], n


def face_samples(poly, n, step=32.0, inset=2.0):
    """points spread over a convex polygon (inset from its edges)"""
    c = poly.mean(0)
    u = poly[0] - c; u /= max(np.linalg.norm(u), 1e-9); v = np.cross(n, u)
    pu, pv = (poly - c) @ u, (poly - c) @ v
    pts = [c]
    for a in np.arange(pu.min() + inset, pu.max() - inset + 0.01, step):
        for b in np.arange(pv.min() + inset, pv.max() - inset + 0.01, step):
            p = c + a * u + b * v
            ok = True
            for i in range(len(poly)):
                e0, e1 = poly[i], poly[(i + 1) % len(poly)]
                if np.dot(np.cross(e1 - e0, p - e0), n) < inset * np.linalg.norm(e1 - e0) - 1e-6: ok = False; break
            if ok: pts.append(p)
    return pts


# ------------------------------------------------------------------------------------------------ checks
def kv_cls(e): return e['kv'].get('classname', '')


def check_names(ents):
    for ei, e in enumerate(ents):
        for b in e['brushes']:
            for f in b:
                t = f[3]
                if t.lower().startswith('textures/'): fail('names', f'texture {t}: no textures/ prefix in .map files'); return
                if t != t.lower(): fail('names', f'texture {t}: upper case (pk3 paths are case sensitive)')
                if t.lower().startswith('common/') and t.lower() not in wopdata.COMMON:
                    fail('names', f'{t} does not exist in WoP (renders as a missing-texture grid); common/clip is the player clip')
            if all(f[3].lower() == 'common/nodraw' for f in b) and kv_cls(e) in ('worldspawn', 'func_rotating', 'func_bobbing',
                                                                                    'func_plat', 'func_train', 'func_door'):
                warn('names', f'ent{ei} brush entirely common/nodraw: NONSOLID in WoP (unlike Q3) - use common/weapclip '
                              'or caulk if it should block')
        kv = e['kv']
        for k in ('model', 'model2', 'noise'):
            v = kv.get(k)
            if v and not v.startswith('*') and v != v.lower() and not v.startswith('models/mapobjects/'):
                warn('names', f'ent{ei} {k} {v}: upper case in your own file names (keep them lower case; pk3dir folders are case sensitive)')
    seen = set()
    FAILS[:] = [f for f in FAILS if not (f in seen or seen.add(f))]


def check_entities(ents, BR, world_mn, world_mx):
    tn = defaultdict(list)
    for ei, e in enumerate(ents):
        if 'targetname' in e['kv']: tn[e['kv']['targetname']].append(ei)
    for ei, e in enumerate(ents):
        kv = e['kv']; c = kv.get('classname', '')
        if c in wopdata.FORBIDDEN: fail('entities', f'ent{ei} {c}: {wopdata.FORBIDDEN[c]}')
        elif c.startswith(('item_', 'weapon_', 'ammo_', 'holdable_')) and c not in wopdata.PICKUPS:
            fail('entities', f'ent{ei} {c}: not a WoP pickup - it never spawns (e.g. item_floater -> holdable_floater)')
        elif c not in wopdata.KNOWN_CLASSES: warn('entities', f'ent{ei} {c}: unknown classname (check WoP entities.def)')
        t = kv.get('target')
        if t and t not in tn: fail('entities', f'ent{ei} {c}: target "{t}" has no entity with that targetname')
        if c == 'trigger_push' and t and not any(ents[j]['kv'].get('classname') in ('target_position', 'info_notnull', 'info_null')
                                                for j in tn.get(t, [])):
            fail('entities', f'ent{ei} trigger_push -> {t}: not a target_position')
        if c == 'trigger_teleport' and t and not any(ents[j]['kv'].get('classname') in ('misc_teleporter_dest', 'target_position')
                                                    for j in tn.get(t, [])):
            fail('entities', f'ent{ei} trigger_teleport -> {t}: no misc_teleporter_dest')
        if c in ('trigger_push', 'trigger_teleport') and not t: fail('entities', f'ent{ei} {c} without a target')
        if c in ('func_rotating', 'func_pendulum', 'func_train') and e['brushes']:
            has_ob = any(all('origin' in f[3].lower() for f in b) for b in e['brushes'])
            if not has_ob and 'origin' not in kv: fail('entities', f'ent{ei} {c} has no origin brush (it would turn round the world origin)')
            if has_ob and 'origin' in kv: fail('entities', f'ent{ei} {c} has an origin brush AND an origin key: '
                                                          'q3map2 adds them and the mover ends up outside the map (leak)')
        if c == 'func_bobbing':
            ks = [b['k'] for b in BR.B if b['ei'] == ei]
            if ks and all(k in ('decor', 'skip') for k in ks):
                fail('entities', f'ent{ei} func_bobbing with only nonsolid brushes: bspc still makes it a bot ride '
                                 '(use func_pendulum/func_rotating + model2 for decoration)')
        if 'origin' in kv and not e['brushes'] and c not in ('worldspawn',):
            o = np.array([float(v) for v in kv['origin'].split()])
            if np.any(o < world_mn - 1) or np.any(o > world_mx + 1):
                fail('entities', f'ent{ei} {c} origin {o.astype(int)} is outside the world (models: "Entity leaked")')
    for n, lst in tn.items():
        cl = {ents[j]['kv'].get('classname') for j in lst}
        if len(lst) > 1 and cl & {'target_position', 'misc_teleporter_dest'}:
            warn('entities', f'targetname "{n}" used {len(lst)} times ({", ".join(sorted(cl))})')


def trigger_centre(BR, ei):
    bs = [b for b in BR.B if b['ei'] == ei]
    if not bs: return None
    return (np.min([b['mn'] for b in bs], 0) + np.max([b['mx'] for b in bs], 0)) / 2


def check_pads(ents, BR, spots):
    tn = {e['kv']['targetname']: e for e in ents if 'targetname' in e['kv']}
    known = {tuple(p['target']): p for p in (spots or {}).get('pads', [])}
    hurt = [(np.array(h['mn']), np.array(h['mx'])) for h in (spots or {}).get('hurt', [])]
    for ei, e in enumerate(ents):
        if e['kv'].get('classname') != 'trigger_push' or 'target' not in e['kv']: continue
        t = tn.get(e['kv']['target'])
        if not t or 'origin' not in t['kv']: continue
        o = trigger_centre(BR, ei); a = np.array([float(v) for v in t['kv']['origin'].split()])
        if o is None: continue
        if a[2] <= o[2]: fail('pads', f'pad {e["kv"]["target"]}: target_position below the trigger centre'); continue
        tu = padmath.t_fall(a[2] - o[2])
        p = known.get(tuple(int(round(v)) for v in a))
        if p:
            tt = padmath.flight_time(o[2], a[2], p['land'][2])
            if tt > padmath.MAX_FLIGHT: fail('pads', f'pad {p["name"]}: flight {tt:.2f} s > {padmath.MAX_FLIGHT} s (no bspc link)')
            L = np.array(p['land'][:2] + [p['land'][2] + 24])
            for mn, mx in hurt:
                d = np.maximum(np.maximum(mn[:2] - L[:2], 0), L[:2] - mx[:2])
                if np.hypot(*d) < 30 and mn[2] - 64 < L[2] < mx[2] + 64:
                    fail('pads', f'pad {p["name"]}: lands {np.hypot(*d):.0f}u from a trigger_hurt (bspc lava area, keep > 30u)')
        elif tu > 1.9:
            warn('pads', f'pad {e["kv"]["target"]} at {o.astype(int)}: {tu:.2f} s up alone - check pad_check t= < 2.9 s')


def floor_under(BR, x, y, z, kinds=('solid', 'clip', 'decor', 'water'), maxd=96):
    """(top z, brush) of the highest brush top below z on (x, y) within maxd"""
    best = None
    for b in BR.near((x - 1, y - 1, z - maxd), (x + 1, y + 1, z + 1), kinds=kinds, movers=True):
        iv = column(b, x, y)
        if iv and iv[1] <= z + 0.5 and (best is None or iv[1] > best[0]): best = (iv[1], b)
    return best


def falls_through(texs):
    """an item dropping with MASK_SOLID passes brushes that are not CONTENTS_SOLID: common/clip (playerclip),
    botclip, nonsolid shaders. common/weapclip is solid."""
    for t in texs:
        tl = t.lower()
        if 'weapclip' in tl: return False
        p = AM.SHADER_PARMS.get('textures/' + tl)
        if p is not None:
            if 'nonsolid' not in p and 'playerclip' not in p and 'botclip' not in p: return False
        elif not (tl in ('common/clip', 'common/botclip', 'common/nodrawnonsolid') or tl.endswith('nodraw_ns')):
            return False
    return True


def check_items(ents, BR):
    hurt = [b for b in BR.B if b['cls'] == 'trigger_hurt']
    rows = []
    sp = [float(e['kv']['origin'].split()[2]) - 25 for e in ents if e['kv'].get('classname') in wopdata.SPAWNS and 'origin' in e['kv']]
    zmin = min(sp) if sp else min((b['mn'][2] for b in BR.of_kind('solid')), default=0)
    for ei, e in enumerate(ents):
        kv = e['kv']; c = kv.get('classname', '')
        if c not in wopdata.PICKUPS or 'origin' not in kv: continue
        o = np.array([float(v) for v in kv['origin'].split()])
        if not int(kv.get('spawnflags', '0')) & 1:
            f = floor_under(BR, o[0], o[1], o[2] - 14, kinds=('solid', 'clip'), maxd=64)
            if f and falls_through(f[1]['texs']):
                fail('items', f'ent{ei} {c} at {o.astype(int)} rests on {f[1]["texs"][0]} ({f[1]["k"]}): it falls through at '
                              'spawn (MASK_SOLID drop) - give it spawnflags 1 or a solid floor')
        for h in hurt:
            d = np.maximum(np.maximum(h['mn'] - o, 0), o - h['mx'])
            if np.linalg.norm(d[:2]) < 100 and d[2] < 64:
                warn('items', f'ent{ei} {c} at {o.astype(int)} is {np.linalg.norm(d[:2]):.0f}u from a trigger_hurt (keep >= 100u)'); break
        if c.startswith('weapon_'):
            f = floor_under(BR, o[0], o[1], o[2] - 14, maxd=4096)
            rows.append((c[7:], o, (f[0] if f else o[2] - 16) - zmin))
    if rows:
        rows.sort(key=lambda r: -wopdata.WEAPON_WEIGHT.get(r[0], 0))
        info = '; '.join(f'{w} {int(h)}u' for w, o, h in rows)
        INFO.append(('items', f'weapon heights above the lowest spawn floor (bot weight high -> low; best weapons belong on hard spots): {info}'))


def water_bodies(BR):
    W = BR.of_kind('water')
    parent = list(range(len(W)))

    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(len(W)):
        for j in range(i + 1, len(W)):
            if np.all(W[i]['mn'] <= W[j]['mx'] + 1) and np.all(W[j]['mn'] <= W[i]['mx'] + 1):
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(W)): groups[find(i)].append(W[i])
    return list(groups.values())


def check_water(BR):
    teles = [b for b in BR.B if b['cls'] == 'trigger_teleport']
    floors = BR.of_kind('solid', 'clip')
    for body in water_bodies(BR):
        mn = np.min([b['mn'] for b in body], 0); mx = np.max([b['mx'] for b in body], 0)
        surf = mx[2]
        if mx[0] - mn[0] < 40 or mx[1] - mn[1] < 40: continue
        if any(np.all(t['mn'] < mx) and np.all(t['mx'] > mn) for t in teles): continue
        step = 16.0
        xs = np.arange(mn[0] - 47, mx[0] + 48.1, step); ys = np.arange(mn[1] - 47, mx[1] + 48.1, step)   # off the brush edges
        near = BR.near(mn - [48, 48, 600], mx + [48, 48, 64], kinds=('solid', 'clip'), movers=False)
        wet = np.zeros((len(xs), len(ys)), bool); fl = np.full((len(xs), len(ys)), -1e9)
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                for b in body:
                    iv = column(b, x, y)
                    if iv and iv[1] > surf - 2: wet[i, j] = True; break
                top = -1e9
                for b in near:
                    if b['mn'][0] > x or b['mx'][0] < x or b['mn'][1] > y or b['mx'][1] < y: continue
                    iv = column(b, x, y)
                    if iv and iv[1] <= surf + 40 and iv[1] > top: top = iv[1]
                fl[i, j] = top
        ok = False
        for i in range(len(xs)):
            for j in range(len(ys)):
                if not wet[i, j] or fl[i, j] < surf - 44: continue
                for di in (-2, -1, 0, 1, 2):
                    for dj in (-2, -1, 0, 1, 2):
                        a, b = i + di, j + dj
                        # walk out (<= 18 step) from wadeable water, or jump out (barrier 33) where only the feet are wet
                        if 0 <= a < len(xs) and 0 <= b < len(ys) and not wet[a, b] and fl[a, b] > surf - 8 \
                                and (fl[a, b] - fl[i, j] <= 18.5 or (surf - fl[i, j] <= 24 and fl[a, b] - fl[i, j] <= 33)):
                            ok = True; break
                    if ok: break
                if ok: break
            if ok: break
        if not ok:
            deep = wet & (fl < surf - 44)
            fail('water', f'water body {mn.astype(int)}..{mx.astype(int)} (surface z {surf:g}): no way out on foot - '
                          f'add 16u steps or a ramp into shallow water (<= 44 deep) next to the deck, or a teleporter'
                          + ('' if deep.any() else ' (shallow, but the deck is more than 18u above the water floor)'))


def check_headroom(BR, bounds, spots, step=16.0):
    crawl = [(np.array(a), np.array(b)) for a, b in (spots or {}).get('crawl', [])]
    stairs = (spots or {}).get('stairs', [])
    solids = BR.of_kind('solid', 'clip')
    if not solids: return
    x0, y0, x1, y1 = bounds
    xs = np.arange(x0 + 8, x1, step); ys = np.arange(y0 + 8, y1, step)
    cols = defaultdict(list)            # (i, j) -> [(zlo, zhi)]
    for b in solids:
        i0 = max(0, int(np.ceil((b['mn'][0] - xs[0]) / step))); i1 = min(len(xs) - 1, int(np.floor((b['mx'][0] - xs[0]) / step)))
        j0 = max(0, int(np.ceil((b['mn'][1] - ys[0]) / step))); j1 = min(len(ys) - 1, int(np.floor((b['mx'][1] - ys[0]) / step)))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                iv = column(b, xs[i], ys[j])
                if iv: cols[(i, j)].append(iv)
    merged = {}
    for k, ivs in cols.items():
        ivs.sort(); m = [list(ivs[0])]
        for lo, hi in ivs[1:]:
            if lo <= m[-1][1] + 0.5: m[-1][1] = max(m[-1][1], hi)
            else: m.append([lo, hi])
        merged[k] = m
    hits = []
    for (i, j), m in merged.items():
        for a in range(len(m) - 1):
            fz = m[a][1]
            # lowest ceiling over the player's footprint (+-16) above this floor
            ceil = m[a + 1][0]
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for lo, hi in merged.get((i + di, j + dj), []):
                        if lo > fz + 1 and lo < ceil: ceil = lo
            gap = ceil - fz
            if 40 <= gap < 56:
                p = np.array([xs[i], ys[j], fz])
                if any(np.all(p >= c0 - 16) and np.all(p <= c1 + 16) for c0, c1 in crawl): continue
                on_stair = any(s['rect'][0] - 16 <= p[0] <= s['rect'][2] + 16 and s['rect'][1] - 16 <= p[1] <= s['rect'][3] + 16
                               and s['z0'] - 1 <= fz <= s['ztop'] + 1 for s in stairs)
                hits.append((p, gap, on_stair))
    # cluster
    done = [False] * len(hits)
    for k, (p, g, st) in enumerate(hits):
        if done[k]: continue
        grp = [k]; done[k] = True; q = 0
        while q < len(grp):
            for m2, (p2, g2, st2) in enumerate(hits):
                if not done[m2] and np.all(np.abs(p2 - hits[grp[q]][0]) <= [step + 1, step + 1, 17]):
                    done[m2] = True; grp.append(m2)
            q += 1
        P = np.array([hits[g][0] for g in grp]); stair = any(hits[g][2] for g in grp)
        gmin = min(hits[g][1] for g in grp)
        msg = (f'crouch-only floor ({gmin:.0f}u clearance) at {P.min(0).astype(int)}..{P.max(0).astype(int)} '
               f'({len(grp)} cells)')
        if stair: fail('headroom', msg + ' ON A STAIR: lift the ceiling edge (step top + 56) or open it two steps earlier')
        elif len(grp) >= 2: warn('headroom', msg + ' - intended crawl space? declare it with MapKit.crawl()')


class AirGrid:
    """voxel grid of the space a player's eye can reach: flood fill from every spawn/pickup through cells not blocked by
    opaque brushes (solid, sky). Clip, botclip, water, triggers and movers count as open (you can see through them).
    Cells are marked blocked conservatively (box vs brush planes), so 8u walls never leak."""

    def __init__(self, BR, ents, max_cells=14e6):
        from scipy import ndimage
        blk = [b for b in BR.B if b['k'] == 'solid' and not b['mover']]
        mn = np.min([b['mn'] for b in blk], 0) - 32; mx = np.max([b['mx'] for b in blk], 0) + 32
        vol = np.prod(mx - mn)
        self.res = r = max(16.0, float(np.ceil((vol / max_cells) ** (1 / 3) / 8) * 8))
        self.o = mn; self.shape = tuple(int(v) for v in np.ceil((mx - mn) / r))
        solid = np.zeros(self.shape, bool)
        for b in blk:
            i0 = np.maximum(np.floor((b['mn'] - mn) / r).astype(int), 0)
            i1 = np.minimum(np.floor((b['mx'] - mn) / r).astype(int), np.array(self.shape) - 1)
            g = np.stack(np.meshgrid(*[np.arange(i0[k], i1[k] + 1) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
            lo = mn + g * r; hi = lo + r
            # inside: overlap by > 1u on every axis and every brush plane reaches into the cell
            ok = np.all(lo < b['mx'] - 1, 1) & np.all(hi > b['mn'] + 1, 1)
            for n, d in b['P']:
                nn = np.asarray(n)
                sup = (np.where(nn > 0, lo, hi) @ nn)          # min of n.x over the cell
                ok &= sup < d - 1
            g = g[ok]
            solid[g[:, 0], g[:, 1], g[:, 2]] = True
        lab, _ = ndimage.label(~solid)
        seeds = set()
        for e in ents:
            c = e['kv'].get('classname', '')
            if (c in wopdata.PICKUPS or c in wopdata.SPAWNS) and 'origin' in e['kv']:
                q = self.cell(np.array([float(v) for v in e['kv']['origin'].split()]))
                if q is not None and lab[q]: seeds.add(lab[q])
        self.air = np.isin(lab, list(seeds)) if seeds else np.zeros(self.shape, bool)
        self.solid = solid

    def cell(self, p):
        i = np.floor((np.asarray(p) - self.o) / self.res).astype(int)
        if np.any(i < 0) or np.any(i >= self.shape): return None
        return tuple(i)

    def open_at(self, p):
        q = self.cell(p)
        return q is not None and bool(self.air[q])


def check_caulk(BR, ents, models_boxes, step=48.0):
    """caulk faces seen from reachable space. Probe 1.2 cells out along the face normal: the cell must be in the flooded
    air and nothing opaque between (an opaque brush, another water body's surface or a model's bounds)."""
    G = AirGrid(BR, ents)
    if not G.air.any():
        warn('caulk', 'no spawn or pickup inside the map: caulk check skipped'); return
    opaque = [b for b in BR.of_kind('solid') if not b['mover']]
    bad = []
    out = G.res * 1.2
    for b in BR.of_kind('solid', 'water'):
        if b['mover']: continue
        for fi, f in enumerate(b['faces']):
            if 'caulk' not in f[3].lower(): continue
            poly, n = face_poly(b, fi)
            if poly is None: continue
            seen = 0; first = None
            for p in face_samples(poly, n, step):
                q = p + n * out
                if not G.open_at(q): continue
                mid = p + n * 2.0
                if inside_any(opaque, mid, 0.25) or inside_any(opaque, p + n * out * 0.5, 0.25): continue
                if any(np.all(mid >= mn) and np.all(mid <= mx) for mn, mx in models_boxes): continue
                seen += 1; first = first if first is not None else p
            if seen: bad.append((seen, first, n, b))
    if not bad: return
    bad.sort(key=lambda r: -r[0])
    for seen, c, n, b in bad[:40]:
        warn('caulk', f'caulk visible at {c.astype(int)} facing {np.round(n, 2).tolist()} (ent{b["ei"]}/b{b["bi"]}, '
                      f'{seen} sample(s) open to reachable space): give that face a real texture')
    if len(bad) > 40: warn('caulk', f'... {len(bad) - 40} more caulk faces')


def model_boxes(ents, md3roots):
    out = []
    if not md3roots: return out
    for e in ents:
        kv = e['kv']
        if kv.get('classname') not in ('misc_model',): continue
        o = np.array([float(v) for v in kv['origin'].split()])
        ang = [float(v) for v in kv['angles'].split()] if 'angles' in kv else [0, float(kv.get('angle', 0)), 0]
        v = AM.model_points(md3roots, kv['model'], float(kv.get('modelscale', 1)), ang)
        if v is None: continue
        v = v + o
        out.append((v.min(0) - 4, v.max(0) + 4))
    return out


def check_rotors(ents, BR):
    statics = BR.of_kind('solid', 'clip')
    for ei, e in enumerate(ents):
        if e['kv'].get('classname') != 'func_rotating': continue
        bs = [b for b in BR.B if b['ei'] == ei]
        ob = [b for b in bs if all('origin' in t.lower() for t in b['texs'])]
        parts = [b for b in bs if b['k'] in ('solid', 'clip')]
        if not ob or not parts: continue
        c = (ob[0]['mn'] + ob[0]['mx']) / 2
        sf = int(e['kv'].get('spawnflags', '0'))
        ax = 0 if sf & 4 else (1 if sf & 8 else 2)
        R = 0.0; lo, hi = 1e9, -1e9
        for b in parts:
            V = verts(b['P']) - c
            o = [k for k in range(3) if k != ax]
            R = max(R, float(np.max(np.hypot(V[:, o[0]], V[:, o[1]]))))
            lo = min(lo, V[:, ax].min()); hi = max(hi, V[:, ax].max())
        for s in statics:
            if s['ei'] == ei: continue
            V = verts(s['P']) - c
            o = [k for k in range(3) if k != ax]
            if V[:, ax].max() <= lo + 1 or V[:, ax].min() >= hi - 1: continue
            # nearest distance of the static brush to the axis (approximate with its vertices / bounds)
            dmin = np.min(np.hypot(V[:, o[0]], V[:, o[1]]))
            inside_axis = np.all(V[:, o[0]].min() < 0 < V[:, o[0]].max()) and (V[:, o[1]].min() < 0 < V[:, o[1]].max())
            if dmin < R - 1 or inside_axis:
                warn('rotors', f'ent{ei} func_rotating (r {R:.0f}) sweeps into static ent{s["ei"]}/b{s["bi"]} {s["texs"][0]} '
                               f'{s["mn"].astype(int)}..{s["mx"].astype(int)}')
                break


def check_arena(ents, mapname, arena):
    if not arena: return
    if not os.path.exists(arena):
        fail('arena', f'{arena} missing (every map needs scripts/<map>.arena)'); return
    txt = open(arena).read()
    m = re.search(r'map\s+"([^"]+)"', txt); t = re.search(r'type\s+"([^"]+)"', txt)
    if not m or m.group(1) != mapname: fail('arena', f'arena map "{m.group(1) if m else None}" != {mapname}')
    if not re.search(r'longname\s+"[^"]+"', txt): fail('arena', 'arena has no longname')
    if not t: fail('arena', 'arena has no type'); return
    classes = {e['kv'].get('classname') for e in ents}
    for tok in t.group(1).split():
        if tok not in wopdata.ARENA_TYPES: fail('arena', f'unknown game type "{tok}"')
        for need in wopdata.ARENA_NEEDS.get(tok, ()):
            if need not in classes: fail('arena', f'type {tok} needs a {need}')
    if {'team_CTL_redlolly', 'team_CTL_bluelolly'} <= classes and 'ctl' not in t.group(1).split():
        warn('arena', 'the map has CTL lollies but the arena does not list ctl')


def check_sounds(ents):
    for ei, e in enumerate(ents):
        n = e['kv'].get('noise')
        if e['kv'].get('classname') == 'target_speaker' and n and not n.startswith('*'):
            if os.path.splitext(n)[0] not in wopdata.KNOWN_SOUNDS:
                warn('sounds', f'ent{ei} {n}: not a known WoP sound (pk3_check.py --game checks the file exists)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--shaders', action='append', default=[])
    ap.add_argument('--md3root', action='append', default=[])
    ap.add_argument('--spots', help='maps/X.spots.json from woplib.kit (default: next to the map)')
    ap.add_argument('--arena', help='scripts/X.arena (default: ../scripts/<map>.arena)')
    ap.add_argument('--only', help='comma list of sections')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    if a.shaders: AM.load_shaders(a.shaders); AM.add_common_parms()
    ents = AM.parse(a.map)
    mapname = os.path.splitext(os.path.basename(a.map))[0]
    sp_path = a.spots or os.path.splitext(a.map)[0] + '.spots.json'
    spots = json.load(open(sp_path)) if os.path.exists(sp_path) else None
    arena = a.arena or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(a.map))), 'scripts', mapname + '.arena')
    only = set(a.only.split(',')) if a.only else None
    run = lambda s: only is None or s in only
    BR = Brushes(ents)
    allb = [b for b in BR.B if b['k'] in ('solid', 'clip', 'water')] or BR.B
    world_mn = np.min([b['mn'] for b in allb], 0); world_mx = np.max([b['mx'] for b in allb], 0)
    bounds = tuple(spots['bounds']) if spots and spots.get('bounds') else (world_mn[0], world_mn[1], world_mx[0], world_mx[1])
    if run('names'): check_names(ents)
    if run('entities'): check_entities(ents, BR, world_mn, world_mx)
    if run('pads'): check_pads(ents, BR, spots)
    if run('items'): check_items(ents, BR)
    if run('water'): check_water(BR)
    if run('headroom'): check_headroom(BR, bounds, spots)
    if run('caulk'): check_caulk(BR, ents, model_boxes(ents, a.md3root))
    if run('rotors'): check_rotors(ents, BR)
    if run('arena'): check_arena(ents, mapname, arena)
    if run('sounds'): check_sounds(ents)
    secs = ['names', 'entities', 'pads', 'items', 'water', 'headroom', 'caulk', 'rotors', 'arena', 'sounds']
    for s in secs:
        if not run(s): continue
        f = [m for k, m in FAILS if k == s]; w = [m for k, m in WARNS if k == s]
        print(f'[{s}] {len(f)} fail, {len(w)} warn')
        for m in f: print('   FAIL', m)
        for m in [m for k, m in INFO if k == s]: print('   info', m)
        for m in w[:(1000 if a.v else 25)]: print('   warn', m)
        if len(w) > 25 and not a.v: print(f'   ... {len(w) - 25} more (-v)')
    print('RESULT:', 'OK' if not FAILS else f'{len(FAILS)} problem(s)', f'({len(WARNS)} warnings)')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
