#!/usr/bin/env python3
"""Starsplash Station - World of Padman FFA map generator (map 'wop_padspace').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_space.py

Writes <OUT>/maps/wop_padspace.map, textures/padspace/*, env/padspace/* (sky), models/padspace/*,
scripts/padspace.shader and scripts/wop_padspace.arena.

An outer-space water park on the moon, human scale (~32u per metre). x east, y north, park deck z 0, water z -16.
The lunar plain lies 112u below the park's rim wall on three sides, a crater ridge closes the north. Overhead: the
stars, the Milky Way, a ringed gas giant and the Earth rising.

  Padstar I       the rocket on its launch pad: walk in through the door, climb the stair round the inside to the
                  cockpit (consoles, portholes), step out onto the balcony, ride the pads up into the nose deck
                  (Imperius) and fling back out through the panorama window. Two slides leave the balcony: the
                  Wormhole tube into Crater Springs and the Comet Run flume into the Black Hole.
  Crater Lagoon   the lunar lander standing on its legs in the middle of the lagoon: jetties and stairs up to the
                  deck, walk through the cabin (Bubble G), pads onto the cabin roof (Pumper).
  Planet Padurn   a ringed planet on a crystal pedestal inside a lazy river: walk the stair bridge up onto the ring,
                  a pad onto the icy polar cap (Betty).
  The Black Hole  a gravity-well dive bowl (16u ring steps all the way down, Splasher on the bottom) with a swirling
                  accretion vortex; the satellite dive tower beside it (Balloony on top).
  Crater Springs  a beach pool with a deep crater (Floater), two habitat pods (pads to their roofs).
  Star Boulevard  the Cosmic Cafe (Boaster, roof terrace), Mission Control (BamBam inside, pad onto the roof),
                  and the Zero-G Loo.
  SECRET          step into the Zero-G Loo -> the Star Vault under the world.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import sp_textures as TX
import splib
import sp_shapes as SH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padspace'
T = lambda n: 'padspace/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns'); SLICK = T('slide_clip')

for k, v in {'regolith': (1.0, 1.0), 'regolith_d': (1.0, 1.0), 'plain': (2.0, 2.0), 'lunar_rock': (1.0, 1.0), 'bank': (1.0, 1.0),
             'plate': (0.5, 0.5), 'plate_d': (0.5, 0.5), 'hexdeck': (0.5, 0.5), 'pool_tile': (0.5, 0.5), 'pool_band': (0.5, 0.5),
             'coping': (0.5, 0.5), 'rim': (0.5, 0.5), 'panel_w': (0.5, 0.5), 'panel_d': (0.5, 0.5), 'starfloor': (0.5, 0.5),
             'water': (1.0, 1.0), 'water_deep': (1.0, 1.0), 'sky': (1, 1), 'gold_foil': (0.5, 0.5), 'carpet': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '10', '_color': '0.85 0.85 1', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
KEEP_OUT = []
NOGO = []
LX, LY = L.LANDER
RX, RY = L.RK


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x, 1), round(y, 1), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def mdl_box(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.15, top_cut=2, **kw):
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    pts = []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            pts.append((ox + (px * ca - py * sa) * scale, oy + (px * sa + py * ca) * scale))
    c = np.mean(pts, 0)
    pts = [tuple(c + (np.array(p) - c) * (1 - shrink)) for p in pts]
    z1 = oz + b['max'][2] * scale - top_cut
    A(hull([(p[0], p[1], zsurf) for p in pts] + [(p[0], p[1], z1) for p in pts], WCLIP, round_pts=False))
    return e


def custom(name, x, y, zbase, angle=0, lit=True, mul=1.0, angles=None, **kw):
    path, sc, zo = splib.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, angles=angles, **extra)


def lbox(x, y, z, ang, mn, mx, tex=WCLIP):
    a = math.radians(ang); ca, sa = math.cos(a), math.sin(a)
    pts = []
    for px in (mn[0], mx[0]):
        for py in (mn[1], mx[1]):
            for pz in (mn[2], mx[2]):
                pts.append((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))
    b = hull(pts, tex, round_pts=False)
    A(b)
    return b


def furn(name, x, y, z, ang=0, boxes=(), mul=1.0, lit=True, **kw):
    e = custom(name, x, y, z, ang, lit=lit, mul=mul, **kw)
    for (mn, mx) in boxes:
        lbox(x, y, z, ang, [v * mul for v in mn], [v * mul for v in mx])
    return e


def light(x, y, z, val, color='0.85 0.9 1', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise if noise.startswith('sound/') else f'sound/world/{noise}.ogg'}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
    M.ent('func_timer', (round(x), round(y), round(z + 64)), target=name, wait=wait, random=rnd, spawnflags=1)


def trigger_sound(mn, mx, noise, name, wait=4, **kw):
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    speaker(c[0], c[1], c[2] + 40, noise, loop=False, targetname=name, **kw)
    M.ent('trigger_multiple', brushes=[box(mn, mx, TRIG)], target=name, wait=wait)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))
    KEEP_OUT.append((x, y, 40))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))
    KEEP_OUT.append((x, y, 48))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((x, y, floor))
    KEEP_OUT.append((x, y, 48))


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)
    KEEP_OUT.append((x, y, 72))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def jumppad(x, y, z, land, apex, name, glow=True):
    """launch pad (r 34) + trigger_push + target_position (the apex, t_up/(t_up+t_down) of the way to `land`)"""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38
    tx, ty = pad_target((x, y, oz), land, apex)
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    if glow: light(x, y, z + 48, 110, '0.5 0.9 1')
    KEEP_OUT.append((x, y, 80))


def route(name, a, b):
    ROUTES.append((name, a, b))


def face_pts(b, f, V=None):
    V = b.verts() if V is None else V
    on = V[np.abs(V @ np.array(f.n) - f.d) < 0.5]
    return on if len(on) else V


def texby(b, fn):
    V = b.verts()
    if len(V) < 4: return None
    for f in b.faces:
        on = face_pts(b, f, V); c = on.mean(0)
        smp = [c] + [c + (p - c) * 0.85 for p in on]
        f.tex = fn(smp, np.array(f.n)); f.sc = wopmap.default_scale(f.tex)
    return b


def clipped(brushes, tex=WCLIP):
    for b in brushes:
        for f in b.faces:
            f.tex = tex; f.sc = (0.5, 0.5)
        A(b)


def in_rect(x, y, r, m=0):
    return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m


def free(x, y, r):
    if abs(x) > L.HX - r - 8 or abs(y) > L.HY - r - 8: return False
    if any(in_rect(x, y, q, r) for q in NOGO): return False
    return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT)


def near_free(x, y, r, search=320):
    if free(x, y, r): return (x, y)
    for d in range(32, search + 1, 32):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if free(px, py, r): return (round(px), round(py))
    return None


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'origin', 'water', 'botclip', 'slide_clip')


def fix_items():
    sol = []
    for b in M.world + [bb for e in M.ents if e['classname'] not in ('trigger_push', 'trigger_multiple', 'trigger_teleport', 'func_rotating') for bb in e['_brushes']]:
        ts = b.textures()
        if all(any(h in t for h in NONSOLID_TEX) for t in ts): continue
        mn, mx = b.bounds()
        sol.append((mn, mx, b.planes()))
    smn = np.array([s[0] for s in sol]); smx = np.array([s[1] for s in sol])
    def blocked(o, lo, hi):
        bmn, bmx = o + lo, o + hi
        cand = np.where(np.all(smn < bmx - 0.25, 1) & np.all(smx > bmn + 0.25, 1))[0]
        if len(cand) == 0: return False
        pts = [o + np.array([x, y, z]) for x in (lo[0], 0, hi[0]) for y in (lo[1], 0, hi[1]) for z in (lo[2] + 1, 0, hi[2])]
        for k in cand:
            P = sol[k][2]
            if any(all(np.dot(n, p) - d < -0.25 for n, d in P) for p in pts): return True
        return False
    moved = []
    for e in M.ents:
        c = e['classname']
        if not c.startswith(('weapon_', 'ammo_', 'item_', 'holdable_', 'info_player_deathmatch')): continue
        o = np.array([float(v) for v in e['origin'].split()])
        lo, hi = (np.array([-16, -16, -24]), np.array([16, 16, 32])) if c.startswith('info_') else (np.array([-16, -16, -15.5]), np.array([16, 16, 16]))
        if not blocked(o, lo, hi): continue
        done = False
        for d in range(16, 260, 16):
            for k in range(16):
                a = k * math.pi / 8
                p = o + np.array([d * math.cos(a), d * math.sin(a), 0])
                if not blocked(p, lo, hi) and blocked(p + np.array([0, 0, lo[2] - 8]), np.array([-4, -4, -2]), np.array([4, 4, 2])):
                    e['origin'] = ' '.join(fmt([v]) for v in np.round(p)); moved.append((c, o.astype(int).tolist(), np.round(p).astype(int).tolist()))
                    done = True; break
            if done: break
        if not done: moved.append((c, o.astype(int).tolist(), 'STUCK'))
    return moved


SLIV = []


def drop_slivers(min_vol=16.0, min_thick=1.0):
    """carve() can leave near-zero-volume slivers (q3map2 'duplicate plane'); drop them"""
    from scipy.spatial import ConvexHull
    keep = []; n = 0
    for b in M.world:
        V = b.verts()
        try:
            h = ConvexHull(V); ok = h.volume >= min_vol
            if ok:
                ok = min(np.ptp(V @ np.array(f.n)) for f in b.faces) >= 0 and \
                     all(np.ptp(V @ np.array(f.n)) >= min_thick for f in b.faces)
        except Exception:
            ok = False
        if ok: keep.append(b)
        else:
            n += 1
            V = b.verts()
            if len(V): SLIV.append((np.round(V.min(0)), np.round(V.max(0)), sorted(b.textures())))
    M.world[:] = keep
    print('dropped slivers', n)


def write_routes():
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padspace/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_space.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== sky hull, ground, plain, ridge
def tile_of(r, m=32): return (r[0] - m, r[1] - m, r[2] + m, r[3] + m)


LAG_TILE = tile_of(L.LAG)
COVE_TILE = tile_of(L.COVE)
BH_TILE = (L.BH[0] - L.BH_R - 32, L.BH[1] - L.BH_R - 32, L.BH[0] + L.BH_R + 32, L.BH[1] + L.BH_R + 32)
PL_TILE = (L.PL[0] - L.RIVER_R1 - 32, L.PL[1] - L.RIVER_R1 - 32, L.PL[0] + L.RIVER_R1 + 32, L.PL[1] + L.RIVER_R1 + 32)
TILES = [LAG_TILE, COVE_TILE, BH_TILE, PL_TILE]
ZONES = [((-2304, -2048, -1344, 448), 'regolith'), ((-1344, -2048, 1344, -1792), 'regolith'), ((-640, 520, 640, 1760), 'plate'),
         ((1344, -2048, 1600, 640), 'plate'), ((-2304, 1856, 2304, 2048), 'regolith_d'), ((2160, 400, 2304, 1856), 'regolith_d'),
         ((-2304, -2048, 2304, -1984), 'coping'), ((-2304, -1984, -2240, 2048), 'coping'), ((2240, -1984, 2304, 2048), 'coping'),
         (L.CAFE, 'carpet'), (L.MC, 'plate_d')] + [(r, 'plate_d') for r in L.PODS]


def sky_hull():
    H = L.SKY
    x0, x1, y0, y1, z0, z1 = H['x0'], H['x1'], H['y0'], H['y1'], H['z0'], H['z1']
    W = 16; sk = T('sky')
    side = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), dict(side, top=sk), detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), dict(side, bot=sk), detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), dict(side, s=sk), detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), dict(side, n=sk), detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), dict(side, w=sk), detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), dict(side, e=sk), detail=False))


def ground():
    X1, Y1 = L.HX, L.HY
    cuts = list(TILES) + [z[0] for z in ZONES]
    def tx_side(r):
        d = {'top': T('hexdeck'), 'side': CAULK, 'bot': CAULK}
        for k, cond in (('s', abs(r[1] + Y1) < 0.5), ('e', abs(r[2] - X1) < 0.5), ('w', abs(r[0] + X1) < 0.5), ('n', False)):
            d[k] = T('rim') if cond else CAULK
        return d
    for r in sub_rects((-X1, -Y1, X1, Y1), cuts):
        A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), tx_side(r)))
    for i, (zr, tex) in enumerate(ZONES):
        later = [z[0] for z in ZONES[i + 1:]]
        for r in sub_rects(zr, later + list(TILES)):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), dict(tx_side(r), top=T(tex))))


def plain_and_ridge():
    """the lunar plain round the south, east and west rim walls (decor, unreachable), the crater ridge in the north,
    player clip all round the playable edge; distant moon rocks, a radio telescope dish and a parked mini rocket"""
    H = L.SKY; X1, Y1 = L.HX, L.HY; bw, bh = L.BANK_W, L.BANK_H
    pl = {'top': T('plain'), 'side': CAULK, 'bot': CAULK}
    for r in sub_rects((H['x0'], H['y0'], H['x1'], Y1), [(-X1, -Y1, X1, Y1)]):
        A(box((r[0], r[1], H['z0']), (r[2], r[3], L.PLAIN_Z), pl))
    bt = {'top': T('bank'), 'side': T('bank'), 'bot': CAULK}
    A(hull([(x, Y1, z) for x in (H['x0'], H['x1']) for z in (H['z0'], 0)] + [(x, Y1 + bw, z) for x in (H['x0'], H['x1']) for z in (H['z0'], bh)],
           bt, round_pts=False))
    A(box((H['x0'], Y1 + bw, H['z0']), (H['x1'], H['y1'], bh), {'top': T('bank'), 'side': CAULK, 'bot': CAULK}))
    for s in (-1, 1):
        A(box((-X1, s * Y1 - (16 if s > 0 else 0), 0), (X1, s * Y1 + (0 if s > 0 else 16), H['z1']), CLIP))
        A(box((s * X1 - (16 if s > 0 else 0), -Y1 + 16, 0), (s * X1 + (0 if s > 0 else 16), Y1 - 16, H['z1']), CLIP))
    rng = np.random.default_rng(42)
    for i in range(16):
        t = (i + rng.uniform(0.2, 0.8)) / 16
        x = H['x0'] + 260 + (H['x1'] - H['x0'] - 520) * t
        y = Y1 + bw + rng.uniform(60, 200)
        k = i % 4
        if k == 0: custom('crystal_big', x, y, bh, rng.uniform(0, 360), lit=False)
        elif k == 1: custom(['bulbtree_a', 'bulbtree_b', 'bulbtree_c'][i % 3], x, y, bh, rng.uniform(0, 360))
        else: custom(['moonrock_b', 'moonrock_c'][i % 2], x, y, bh, rng.uniform(0, 360))
    # out on the plain (beyond the clip)
    for (x, y, nm) in ((-2650, -1500, 'moonrock_c'), (2700, -400, 'moonrock_b'), (2600, -2400, 'moonrock_c'), (-2700, 600, 'moonrock_b'),
                       (900, -2380, 'moonrock_b'), (-1300, -2480, 'moonrock_c'), (2620, 1400, 'crystal_big'), (-2650, -300, 'crystal_big')):
        custom(nm, x, y, L.PLAIN_Z, int(x) % 360)
    custom('dish_small', -2600, 1700, L.PLAIN_Z, 200, mul=2.0)
    custom('mini_rocket', 2650, -1500, L.PLAIN_Z, 30, mul=2.0)
    custom('rover', -1900, -2420, L.PLAIN_Z, 70, mul=1.0)


# =================================================================================================== pool helpers
def pool_tex(smp, n):
    if n[2] > 0.99 and abs(max(p[2] for p in smp) - 0) < 0.5: return T('coping')
    if n[2] < -0.7: return CAULK
    if n[2] > 0.3: return T('pool_tile')
    return T('pool_band')


def water_faces(b, deep=False, wt=None):
    wt = wt or T('water_deep' if deep else 'water')
    for f in b.faces:
        top = f.n[2] > 0.99 and abs(max(p[2] for p in face_pts(b, f)) - L.WATER) < 0.5
        f.tex = wt if top else wt + '_nodraw'
        f.sc = (1, 1)
    return b


def edge_faces_caulk(b, tile):
    if b is None: return []
    V = b.verts()
    for f in b.faces:
        if abs(f.n[2]) > 0.01: continue
        on = face_pts(b, f, V)
        if abs(f.n[0]) > 0.99 and (np.all(np.abs(on[:, 0] - tile[0]) < 0.5) or np.all(np.abs(on[:, 0] - tile[2]) < 0.5)): f.tex = CAULK
        if abs(f.n[1]) > 0.99 and (np.all(np.abs(on[:, 1] - tile[1]) < 0.5) or np.all(np.abs(on[:, 1] - tile[3]) < 0.5)): f.tex = CAULK
    return b


# =================================================================================================== Crater Lagoon + the lander
WATER_SOLIDS = []


def lagoon():
    cut = L.LAG_CUT; sb = L.SHALLOW_BAND
    oct0 = L.octagon(L.LAG, cut); oct1 = L.octagon(L.LAG, cut, sb); oct2 = L.octagon(L.LAG, cut, sb + L.SLOPE_W)
    c1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, 64)], CAULK, round_pts=False)
    c2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, 64)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    hw = L.JETTY_HW
    keep = [box((LX - hw, LY + L.LD_HALF, -600), (LX + hw, L.LAG[3] + 64, 80), CAULK),
            box((LX - hw, L.LAG[1] - 64, -600), (LX + hw, LY - L.LD_HALF, 80), CAULK)] + \
           [cyl(x, y, r, -600, 80, CAULK, 16) for (x, y, r) in L.ISLETS]
    cutters = []
    for c in (c1, c2):
        cutters += carve(c, keep)
    tile = box((LAG_TILE[0], LAG_TILE[1], L.SLAB_BOT), (LAG_TILE[2], LAG_TILE[3], 0), CAULK)

    def tx(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(c[2]) < 0.5:
            if any(math.hypot(c[0] - x, c[1] - y) < r + 1 for (x, y, r) in L.ISLETS): return T('regolith')
            if abs(c[0] - LX) < hw + 1 and L.LAG[1] - 40 < c[1] < L.LAG[3] + 40: return T('plate')
            return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('pool_tile')
        if abs(abs(c[0] - LX) - hw) < 2: return T('rim')
        if any(math.hypot(c[0] - x, c[1] - y) < r + 2 for (x, y, r) in L.ISLETS): return T('lunar_rock')
        return T('pool_band')
    for b in carve(tile, cutters):
        A(edge_faces_caulk(texby(b, tx), LAG_TILE))
    solids = []
    for (x0, y0, x1, y1, d) in L.LAG_STEPS:
        n = 3
        for j in range(n):
            if d == 's': r = (x0, y0 + (y1 - y0) * j / n, x1, y0 + (y1 - y0) * (j + 1) / n)
            elif d == 'w': r = (x0 + (x1 - x0) * j / n, y0, x0 + (x1 - x0) * (j + 1) / n, y1)
            else: r = (x1 - (x1 - x0) * (j + 1) / n, y0, x1 - (x1 - x0) * j / n, y1)
            zt = L.SHALLOW + 16 * (n - j)
            b = box((round(r[0]), round(r[1]), L.SHALLOW), (round(r[2]), round(r[3]), zt), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
            A(b); solids.append(b)
    bx0, by0, bx1, by1 = L.BEACH
    beach = hull([(x, by1, L.SHALLOW) for x in (bx0, bx1)] + [(x, by1, 0) for x in (bx0, bx1)] + [(x, by0, L.SHALLOW) for x in (bx0, bx1)],
                 {'top': T('regolith'), 'side': T('pool_band'), 'bot': CAULK}, round_pts=False)
    A(beach); solids.append(beach)
    W_ = L.WATER
    w1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, W_)], CAULK, round_pts=False)
    w2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, W_)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    oct1_box = hull([(x, y, z) for (x, y) in oct1 for z in (L.DEEP - 10, W_ + 10)], CAULK, round_pts=False)
    all_solids = solids + WATER_SOLIDS
    def cut_all(w):
        out_ = [w]
        for cset in (keep, all_solids):
            out_ = [pp for ww in out_ for pp in carve(ww, cset)]
        return out_
    w1p = [pp for w in cut_all(w1) for pp in carve(w, [oct1_box])]
    w2p = cut_all(w2)
    for pc in w1p + w2p:
        A(water_faces(pc))
    NOGO.append(tuple(L.LAG))
    for k, (x, y, r) in enumerate(L.ISLETS):
        custom('moonrock_b' if r > 90 else 'moonrock_a', x + 14, y - 10, 0, 40 + 90 * k)
        A(cyl(x + 14, y - 10, (64 if r > 90 else 42), 0, (75 if r > 90 else 48), WCLIP, 10))
        po = 46 if r > 90 else 36
        custom(['crystal_a', 'crystal_b'][k % 2], x - po, y + po, 0, 120 * k, lit=False)
        A(cyl(x - po, y + po, 20, 0, 90, WCLIP, 8))
    item('ammo_splasher', -620, -1300, L.DEEP); item('ammo_pumper', 820, -1700, L.SHALLOW); item('item_armor_shard', -1150, -300, L.SHALLOW)
    for (x, y) in ((-640, -1200), (640, -800), (-700, -700), (700, -1350)):
        light(x, y, L.DEEP + 60, 180, '0.4 0.9 1')
    speaker(-700, -1000, 0, 'ambient/water_rippling', volume=0.5); speaker(700, -1000, 0, 'ambient/water_rippling', volume=0.5)


SPIRES = [(-380.0, -300.0), (560.0, -300.0), (-1250.0, -800.0), (1250.0, -1250.0), (-400.0, -1695.0), (400.0, -1695.0)]


def spires():
    """giant crystal spires standing in the lagoon's shallow band (cover over the open water)"""
    for k, (x, y, z, m) in enumerate([(x, y, L.SHALLOW, 1.5) for (x, y) in SPIRES] + [(-470.0, -640.0, L.DEEP, 2.2), (450.0, -1250.0, L.DEEP, 2.2)]):
        custom('crystal_big', x, y, z, 40 * k, lit=False, mul=m)
        for b in (cyl(x, y, 35 * m, z, z + 17 * m, WCLIP, 10), cyl(x, y, 15 * m, z + 17 * m, z + 200 * m, WCLIP, 8)):
            A(b); WATER_SOLIDS.append(b)
        light(x + 50 * m, y, 40, 160, '0.7 0.5 1')


def lander():
    stage = SH.lander_stage()
    clipped(stage)
    WATER_SOLIDS.extend(stage)
    clipped(SH.lander_cabin())
    custom('lander', LX, LY, 0)
    # leg collision: thin slanted posts in the water (carved out of the water) and the footpads
    for a in (45, 135, 225, 315):
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        top = d * 246; foot = d * L.LEG_R1
        pts = []
        for (p, z) in ((top, 60), (foot, L.DEEP + 12)):
            for (ox, oy) in ((-6, -6), (6, -6), (6, 6), (-6, 6)):
                pts.append((LX + p[0] + ox, LY + p[1] + oy, z))
        b = hull(pts, WCLIP, round_pts=False); A(b); WATER_SOLIDS.append(b)
        fp = cyl(LX + foot[0], LY + foot[1], 30, L.DEEP, L.DEEP + 12, WCLIP, 10); A(fp); WATER_SOLIDS.append(fp)
    NOGO.append((LX - L.LEG_R1 - 40, LY - L.LEG_R1 - 40, LX + L.LEG_R1 + 40, LY + L.LEG_R1 + 40))
    # jetty stairs up to the deck (north and south)
    n = L.DECK_Z // 16
    for s in (-1, 1):
        ye = LY + s * L.LD_HALF
        for j in range(n):
            zt = 16 * (j + 1)
            ya = ye + s * 32 * (n - j); yb = ya - s * 32
            A(box((LX - L.JETTY_HW, min(ya, yb), 0), (LX + L.JETTY_HW, max(ya, yb), zt), {'top': T('plate'), 'side': T('plate_d'), 'bot': CAULK}))
        route(f'jetty_{"n" if s > 0 else "s"}', (LX, ye + s * 360, 0), (LX + 130, LY + s * 150, L.DECK_Z))
    c = L.CAB
    route('cabin_n', (LX - 140, LY + 160, L.DECK_Z), (LX, LY, L.DECK_Z))
    route('cabin_s', (LX + 140, LY - 160, L.DECK_Z), (LX + 10, LY - 10, L.DECK_Z))
    # inside the cabin: consoles, two seats, Bubble G
    furn('console', LX + 20, LY + 46, L.DECK_Z, 180, [((-58, -10, 0), (58, 30, 60))])
    furn('pilot_seat', LX - 56, LY + 20, L.DECK_Z, 0, [((-18, -14, 0), (18, 24, 60))])
    weapon('bubbleg', LX - 20, LY - 34, L.DECK_Z, 'green')
    item('ammo_bubbleg', LX + 50, LY - 40, L.DECK_Z)
    light(LX, LY, L.CAB_TOP - 40, 220, '0.9 0.95 1')
    # deck: pad onto the cabin roof (Pumper), a second pad from the north jetty
    jumppad(LX + 165, LY - 100, L.DECK_Z, (LX + 30, LY - 20, L.CAB_TOP), L.CAB_TOP + 200, 'pad_cabin')
    jumppad(LX, -480, 0, (LX - 40, LY + 30, L.CAB_TOP), L.CAB_TOP + 220, 'pad_cabin_jetty')
    weapon('pumper', LX - 40, LY - 10, L.CAB_TOP, 'green')
    item('ammo_pumper', LX + 50, LY - 50, L.CAB_TOP)
    A(cyl(LX + c[2] - 26, LY + c[3] - 26, 5, L.CAB_TOP, L.CAB_TOP + 96, WCLIP, 6))
    item('ammo_splasher', LX - 150, LY + 140, L.DECK_Z); item('item_armor_shard', LX + 150, LY + 140, L.DECK_Z)
    for (x, y) in ((LX - 170, LY), (LX + 170, LY)):
        light(x, y, L.DECK_Z + 90, 150, '1 0.85 0.6')
    speaker(LX, LY, L.DECK_Z + 60, 'machine/transformer', volume=0.25)
    trigger_sound((LX - 60, LY - 40, L.CAB_TOP + 2), (LX + 60, LY + 60, L.CAB_TOP + 70), 'sound/world/human/applause.ogg', 'cab_cheer', 15, volume=0.5)
    spawn(LX - 150, LY - 150, L.DECK_Z, 90)


# =================================================================================================== the rocket
NOSE_HOLE = (RX, RY + 130)


def rocket():
    clipped(SH.rocket_shell())
    inter = SH.rocket_interior()
    nose_hole = cyl(NOSE_HOLE[0], NOSE_HOLE[1], L.RK_HOLE, L.NOSE_Z - 40, L.NOSE_Z + 20, CAULK, 16)
    keep = []
    for b in inter:
        if b.part == 'ndeck':
            keep += carve(b, [nose_hole])
        else:
            keep.append(b)
    clipped(keep)
    balc = SH.rocket_balcony()
    clipped([b for b in balc if b.part == 'balcony'])
    clipped([b for b in balc if b.part == 'rail'], CLIP)
    clipped(SH.rocket_fins())
    custom('rocket', RX, RY, 0, _lightmapscale=1.0)
    NOGO.append((RX - L.FIN_R1 - 30, RY - L.FIN_R1 - 30, RX + L.FIN_R1 + 30, RY + L.FIN_R1 + 30))
    # routes: door, stair, balcony doors
    route('rocket_door', (RX, RY - 520, 0), (RX - 40, RY + 40, 0))
    a0 = math.radians(L.RK_STAIR_A0 - 10)
    route('rocket_stair', (RX + 150 * math.cos(a0) - 40, RY + 150 * math.sin(a0), 0), (RX + 30, RY - 120, L.COCK_Z))
    route('balcony_w', (RX - 110, RY - 40, L.COCK_Z), (RX - 340, RY - 60, L.COCK_Z))
    route('balcony_e', (RX + 110, RY + 40, L.COCK_Z), (RX + 340, RY + 60, L.COCK_Z))
    # ground floor
    item('ammo_balloony', RX - 100, RY + 60, 0); item('item_armor_shard', RX + 80, RY - 120, 0)
    jumppad(RX, RY, 0, (RX, RY - 120, L.COCK_Z), L.COCK_Z + 150, 'pad_cockpit')
    for (x, y) in ((RX - 60, RY - 60), (RX + 60, RY + 60)):
        light(x, y, 240, 200, '0.8 0.9 1')
    # cockpit: consoles round the north wall, seats, Visionless, the pad up to the nose
    for (a, d) in ((25, 168), (155, 168)):
        x, y = L.ang_pt(RX, RY, d, a)
        furn('console', x, y, L.COCK_Z, a - 90, [((-58, -10, 0), (58, 30, 60))])
    furn('pilot_seat', RX + 143, RY - 83, L.COCK_Z, 240, [((-18, -14, 0), (18, 24, 60))])
    item('item_visionless', RX + 130, RY + 20, L.COCK_Z); item('ammo_imperius', RX - 140, RY + 10, L.COCK_Z)
    jumppad(NOSE_HOLE[0], NOSE_HOLE[1], L.COCK_Z, (RX, RY + 30, L.NOSE_Z), L.NOSE_Z + 150, 'pad_nose')
    for (x, y) in ((RX - 120, RY - 40), (RX + 120, RY - 40)):
        light(x, y, L.COCK_Z + 180, 200, '0.8 0.9 1')
    # nose deck: Imperius, applause, fling pad out through the panorama window
    weapon('imperius', RX + 60, RY - 30, L.NOSE_Z, 'purple')
    item('ammo_imperius', RX - 70, RY + 40, L.NOSE_Z)
    mdl_c('pad_ddmix/cabin/telescope.md3', RX - 120, RY - 60, L.NOSE_Z, 0.3, 300)
    lbox(RX - 120, RY - 60, L.NOSE_Z, 0, (-18, -16, 0), (18, 16, 100))
    jumppad(RX - 10, RY - 120, L.NOSE_Z, (-260, 420, 0), L.NOSE_Z + 150, 'pad_window_fling')
    trigger_sound((RX - 40, RY - 40, L.NOSE_Z + 2), (RX + 120, RY + 20, L.NOSE_Z + 70), 'sound/world/human/applause.ogg', 'nose_cheer', 15, volume=0.6)
    light(RX, RY, L.NOSE_Z + 220, 170, '1 0.9 0.8')
    # balcony: Jumper, ammo, the pad up into the nose window
    item('item_jumper', RX + 300, RY - 230, L.COCK_Z); item('ammo_bubbleg', RX - 300, RY + 220, L.COCK_Z)
    item('ammo_balloony', RX + 260, RY + 280, L.COCK_Z)
    jumppad(RX, RY - 384, L.COCK_Z, (RX, RY - 60, L.NOSE_Z), L.NOSE_Z + 145, 'pad_balcony_nose')
    # outside: a pad from the plaza onto the balcony
    jumppad(120, 470, 0, (RX + 90, RY - 345, L.COCK_Z), L.COCK_Z + 170, 'pad_plaza_balcony')
    for a in (30, 150, 210, 330):
        x, y = L.ang_pt(RX, RY, 380, a)
        light(x, y, L.COCK_Z + 80, 140, '1 0.9 0.8')
    for a in (45, 135, 225, 315):
        x, y = L.ang_pt(RX, RY, 600, a + 22)
        light(x, y, 80, 260, '1 0.7 0.4')
    speaker(RX, RY, 200, 'machine/ventilation', volume=0.3)
    speaker(RX, RY, L.COCK_Z + 60, 'machine/electric_sizzle', volume=0.2)
    timer_sound(RX, RY, 300, 'misc/alarm_buzzer', 'countdown', 45, 20, volume=0.35)
    spawn(RX + 90, RY + 90, 0, 225)
    spawn(RX + 60, RY - 110, L.COCK_Z, 90)


# =================================================================================================== slides
def slide_brushes(pts, hw, wall_h, roof=None, floor_t=16, wall_t=8):
    P = [np.array(p, float) for p in pts]
    n = len(P)
    dirs = []
    for i in range(n - 1):
        d = P[i + 1][:2] - P[i][:2]; dirs.append(d / np.linalg.norm(d))
    perps = [np.array([-d[1], d[0]]) for d in dirs]
    jl = []
    for k in range(n):
        if k == 0: m = perps[0]
        elif k == n - 1: m = perps[-1]
        else:
            m = perps[k - 1] + perps[k]; m = m / np.linalg.norm(m)
        ref = perps[min(k, n - 2)]
        f = 1.0 / max(0.5, float(m @ ref))
        jl.append((m, f))
    for i in range(n - 1):
        (ma, fa), (mb, fb) = jl[i], jl[i + 1]
        ca, cb = P[i], P[i + 1]
        za, zb = ca[2], cb[2]
        def edge(c, m, f, off): return c[:2] + m * off * f
        La, Ra = edge(ca, ma, fa, hw), edge(ca, ma, fa, -hw)
        Lb, Rb = edge(cb, mb, fb, hw), edge(cb, mb, fb, -hw)
        for tri in ((La, Ra, Lb, za, za, zb), (Ra, Rb, Lb, za, zb, zb)):
            p1, p2, p3, z1, z2, z3 = tri
            A(hull([(p1[0], p1[1], z1), (p2[0], p2[1], z2), (p3[0], p3[1], z3),
                    (p1[0], p1[1], z1 - floor_t), (p2[0], p2[1], z2 - floor_t), (p3[0], p3[1], z3 - floor_t)], SLICK, round_pts=False))
        for side in (1, -1):
            ia, ib = edge(ca, ma, fa, side * hw), edge(cb, mb, fb, side * hw)
            oa, ob = edge(ca, ma, fa, side * (hw + wall_t)), edge(cb, mb, fb, side * (hw + wall_t))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - floor_t), (p[0], p[1], zz + wall_h)]
            A(hull(pw, WCLIP, round_pts=False))
        if roof:
            oLa, oRa = edge(ca, ma, fa, hw + wall_t), edge(ca, ma, fa, -hw - wall_t)
            oLb, oRb = edge(cb, mb, fb, hw + wall_t), edge(cb, mb, fb, -hw - wall_t)
            for tri in ((oLa, oRa, oLb, za, za, zb), (oRa, oRb, oLb, za, zb, zb)):
                p1, p2, p3, z1, z2, z3 = tri
                A(hull([(p1[0], p1[1], z1 + wall_h), (p2[0], p2[1], z2 + wall_h), (p3[0], p3[1], z3 + wall_h),
                        (p1[0], p1[1], z1 + wall_h + 6), (p2[0], p2[1], z2 + wall_h + 6), (p3[0], p3[1], z3 + wall_h + 6)], WCLIP, round_pts=False))


def on_ground_free(x, y, m=48):
    if abs(x) > L.HX - m or abs(y) > L.HY - m: return False
    for t in TILES:
        if in_rect(x, y, t, m): return False
    if math.hypot(x - RX, y - RY) < L.FIN_R1 + m: return False
    for r in L.PODS:
        if in_rect(x, y, r, m + 40): return False
    # the planet's stair bridge
    if in_rect(x, y, (L.PL[0] + L.RING_R1, L.PL[1] - 60, L.PL[0] + L.RING_R1 + 32 * 19 + 32, L.PL[1] + 60), m): return False
    return True


def supports_for(path, every=5, zmin=110):
    out = []
    for i in range(2, len(path) - 2, every):
        x, y, z = path[i]
        if z >= zmin and on_ground_free(x, y): out.append((x, y, z))
    return out


def slides_place():
    import sp_models as PM
    sp = L.tube_path(); fp = L.flume_path()
    custom('wormhole_tube', 0, 0, 0)
    slide_brushes(sp[1:], 40, 96, roof=True)
    for (x, y, z) in PM.SUPPORTS['tube']:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        A(box((round(x) - 34, round(y) - 12, 0), (round(x) + 34, round(y) + 12, round(zt) - 30), WCLIP))
        KEEP_OUT.append((x, y, 70))
    for (x, y, z) in sp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    x0, y0, z0 = sp[1]
    custom('wormhole_mouth', x0, y0, z0, 180)
    route('tube_mouth', (x0 + 120, y0 - 20, z0), (x0 + 30, y0, z0))
    custom('comet_flume', 0, 0, 0)
    slide_brushes(fp[1:], 46, 48)
    for (x, y, z) in PM.SUPPORTS['flume']:
        A(box((round(x) - 36, round(y) - 12, 0), (round(x) + 36, round(y) + 12, round(z) - 40), WCLIP))
        KEEP_OUT.append((x, y, 70))
    for (x, y, z) in fp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    fx, fy, fz = fp[1]
    custom('comet_gate', fx - 6, fy, fz, 0)
    for s in (-1, 1):
        A(cyl(fx - 6, fy + s * 74, 7, fz, fz + 150, WCLIP, 8))
    speaker(sp[-1][0], sp[-1][1], 40, 'ambient/water_shower', volume=0.4)
    speaker(fp[-1][0], fp[-1][1], 40, 'ambient/water_shower', volume=0.4)


# =================================================================================================== Planet Padurn
def planet():
    cx, cy = L.PL
    tile = box((PL_TILE[0], PL_TILE[1], L.SLAB_BOT), (PL_TILE[2], PL_TILE[3], 0), CAULK)
    n = 32
    ring_cut = cyl(cx, cy, L.RIVER_R1, L.RIVER_FLOOR, 32, CAULK, n, phase=0)
    def tx(smp, nn):
        c = smp[0]
        if nn[2] > 0.99 and abs(c[2]) < 0.5: return T('coping')
        if nn[2] < -0.7: return CAULK
        if nn[2] > 0.3: return T('pool_tile')
        return T('pool_band')
    for b in carve(tile, [ring_cut]):
        A(edge_faces_caulk(texby(b, tx), PL_TILE))
    # the island (back up to z 0) inside the river: 32 wedges
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        b = SH.ring_seg(cx, cy, a0, a1, 0, L.RIVER_R0, L.RIVER_FLOOR, 0, tex={'top': T('regolith'), 'side': T('pool_band'), 'bot': CAULK})
        A(b)
    # step exits on both banks + flat footbridges
    solids = []
    for a in L.RIVER_STEPS:
        for (r0, r1, zt) in ((L.RIVER_R0, L.RIVER_R0 + 24, -16), (L.RIVER_R0 + 24, L.RIVER_R0 + 48, -32), (L.RIVER_R0 + 48, L.RIVER_R0 + 72, -48),
                             (L.RIVER_R1 - 24, L.RIVER_R1, -16), (L.RIVER_R1 - 48, L.RIVER_R1 - 24, -32), (L.RIVER_R1 - 72, L.RIVER_R1 - 48, -48)):
            k0 = round(a / 11.25)
            b = SH.ring_seg(cx, cy, k0 * 11.25, (k0 + 1) * 11.25, r0, r1, L.RIVER_FLOOR, zt, tex={'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
            A(b); solids.append(b)
    for a in L.PL_BRIDGES:
        b = SH.ring_seg(cx, cy, a - 6, a + 6, L.RIVER_R0 - 16, L.RIVER_R1 + 16, 0, 12, tex={'top': T('plate'), 'side': T('plate_d'), 'bot': T('plate_d')})
        A(b)
        mid = (L.RIVER_R0 + L.RIVER_R1) / 2
        route(f'bridge_{int(a)}', L.ang_pt(cx, cy, L.RIVER_R1 + 120, a) + (0,), L.ang_pt(cx, cy, L.RIVER_R0 - 80, a) + (0,))
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        w = SH.ring_seg(cx, cy, a0, a1, L.RIVER_R0, L.RIVER_R1, L.RIVER_FLOOR, L.WATER)
        for p in carve(w, solids):
            A(water_faces(p))
    NOGO.append(tuple(PL_TILE))
    # the planet, its ring and the stair bridge
    clipped(SH.planet_sphere()); clipped(SH.planet_ring()); clipped(SH.planet_stair())
    custom('planet', cx, cy, 0, _lightmapscale=1.0)
    xr = L.RING_R1 * math.cos(math.radians(180 / 32))
    custom('planet_stair', cx + xr + 16 * (L.RING_Z // 16), cy, 0)
    NOGO.append((cx + xr - 20, cy - 80, cx + xr + 32 * 20, cy + 80))
    route('planet_stair', (cx + xr + 32 * 19 + 120, cy, 0), (cx + 330, cy + 10, L.RING_Z))
    # pads: plaza -> ring, ring -> polar cap (Betty), fling off the cap
    pa = L.ang_pt(cx, cy, 650, 322)
    la = L.ang_pt(cx, cy, 330, 322)
    jumppad(pa[0], pa[1], 0, (la[0], la[1], L.RING_Z), L.RING_Z + 200, 'pad_ring')
    pr = L.ang_pt(cx, cy, 340, 200); lc = L.ang_pt(cx, cy, 70, 200)
    jumppad(pr[0], pr[1], L.RING_Z, (lc[0], lc[1], L.PL_CAP), L.PL_CAP + 170, 'pad_cap')
    weapon('betty', cx + 10, cy - 10, L.PL_CAP, 'purple')
    fl = L.ang_pt(cx, cy, 60, 20); fland = L.ang_pt(cx, cy, 900, 20)
    jumppad(fl[0], fl[1], L.PL_CAP, (fland[0], fland[1], 0), L.PL_CAP + 120, 'pad_cap_fling')
    trigger_sound((cx - 70, cy - 80, L.PL_CAP + 2), (cx - 10, cy - 20, L.PL_CAP + 70), 'sound/world/human/applause.ogg', 'cap_cheer', 15, volume=0.6)
    # ring + island items
    for (a, cls) in ((90, 'ammo_betty'), (150, 'ammo_pumper'), (240, 'item_armor_shard'), (0 + 30, 'ammo_nipper')):
        x, y = L.ang_pt(cx, cy, 330, a)
        item(cls, x, y, L.RING_Z)
    for (a, cls, r) in ((100, 'holdable_boomies', 290), (210, 'ammo_balloony', 300), (330, 'item_armor_shard', 300)):
        x, y = L.ang_pt(cx, cy, r, a)
        item(cls, x, y, 0)
    for k in range(4):
        x, y = L.ang_pt(cx, cy, 300, 45 + 90 * k)
        light(x, y, 200, 200, '1 0.8 0.6')
    for k in range(6):
        x, y = L.ang_pt(cx, cy, 620, 30 + 60 * k)
        light(x, y, 340, 220, '1 0.85 0.7')
    light(cx, cy, L.PL_CAP + 100, 200, '0.8 0.9 1')
    for k in range(6):
        x, y = L.ang_pt(cx, cy, 340, 60 * k + 30)
        light(x, y, L.RING_Z + 110, 170, '1 0.85 0.7')
    speaker(cx, cy, 0, 'ambient/water_flowing', volume=0.4)
    speaker(cx + 330, cy, L.RING_Z + 60, 'misc/wind_chimes', volume=0.3)
    # Padurn's moonlets circling
    zc = L.MOON_Z
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, zc - 8), (cx + 8, cy + 8, zc + 8), ORIGIN),
                                    box((cx - 4, cy - 4, zc + 20), (cx + 4, cy + 4, zc + 28), NODRAW_NS)],
          model2=splib.IQM['moonlets'], speed=10, spawnflags=0, dmg=0)
    spawn(cx + 280, cy - 120, L.RING_Z, 180)
    spawn(cx - 200, cy + 200, 0, 270)


# =================================================================================================== the Black Hole + the satellite tower
def black_hole():
    cx, cy = L.BH
    n = 24
    tile = box((BH_TILE[0], BH_TILE[1], L.SLAB_BOT), (BH_TILE[2], BH_TILE[3], 0), CAULK)
    cut = cyl(cx, cy, L.BH_R, L.BH_FLOOR, 32, CAULK, n, phase=0)
    for b in carve(tile, [cut]):
        A(edge_faces_caulk(texby(b, pool_tex), BH_TILE))
    for k in range(L.BH_RINGS - 1):
        r0, r1, zt = L.bh_ring(k)
        for j in range(n):
            a0, a1 = 360 * j / n, 360 * (j + 1) / n
            A(SH.ring_seg(cx, cy, a0, a1, r0, r1, L.BH_FLOOR, zt, tex={'top': T('pool_tile'), 'side': T('pool_band'), 'bot': CAULK}))
            if zt < L.WATER:
                A(water_faces(SH.ring_seg(cx, cy, a0, a1, r0, r1, zt, L.WATER), wt=T('water_bh')))
    rc = L.BH_R - L.BH_STEP * (L.BH_RINGS - 1)
    A(water_faces(cyl(cx, cy, rc, L.BH_FLOOR, L.WATER, CAULK, n, phase=0), wt=T('water_bh')))
    # the vortex image fitted to the bowl (rotated round its centre by the shader)
    D = 2 * L.BH_R; Npx = 512
    for b in M.world[-(L.BH_RINGS - 1) * n * 2 - 2:]:
        for f in b.faces:
            if f.tex == T('water_bh'):
                f.sc = (D / Npx, D / Npx); f.off = ((-(cx - L.BH_R) / (D / Npx)) % Npx, ((cy + L.BH_R) / (D / Npx)) % Npx)
    NOGO.append(tuple(BH_TILE))
    weapon('splasher', cx, cy, L.BH_FLOOR, 'orange')
    for (a, k, cls) in ((30, 12, 'ammo_splasher'), (150, 6, 'ammo_balloony'), (260, 15, 'item_armor_shard'), (330, 3, 'ammo_nipper')):
        r0, r1, zt = L.bh_ring(k)
        x, y = L.ang_pt(cx, cy, (r0 + r1) / 2, a)
        item(cls, x, y, zt)
    for k in range(6):
        x, y = L.ang_pt(cx, cy, 220, 60 * k)
        light(x, y, -180, 220, '0.7 0.5 1')
    light(cx, cy, -260, 260, '0.6 0.9 1')
    for k in range(8):
        x, y = L.ang_pt(cx, cy, L.BH_R + 40, 45 * k + 22)
        light(x, y, 90, 160, '1 0.5 0.9')
    speaker(cx, cy, 0, 'ambient/water_drain', volume=0.5)
    speaker(cx, cy, -200, 'ambient/water_bubbling', volume=0.4)
    route('bh_steps', L.ang_pt(cx, cy, L.BH_R + 80, 200) + (0,), L.ang_pt(cx, cy, L.BH_R - 24 * 1 - 12, 200) + (-32,))
    A(sign_box((cx - 256, cy - L.BH_R - 100, 120), (cx + 256, cy - L.BH_R - 96, 216), T('sign_bh'), 1024, 192, back=CAULK, facing='s'))
    A(box((cx - 264, cy - L.BH_R - 96, 0), (cx + 264, cy - L.BH_R - 80, 224), {'side': T('panel_d'), 'top': T('panel_d'), 'bot': CAULK}))
    NOGO.append((cx - 290, cy - L.BH_R - 130, cx + 290, cy - L.BH_R - 50))
    # the satellite tower
    sx, sy = L.SAT
    custom('sat_tower', sx, sy, 0)
    blist, steps, holes = SH.sat_tower()
    clipped(blist); clipped(SH.sat_arm())
    h = L.SAT_HALF; top = L.SAT_TOP
    NOGO.append((sx - h - 40, sy - h - 40, sx + h + 40, sy + h + 40))
    # clip rails round the top: the stair opening and the arm corner left open
    for (a, b) in (((sx + h - 8, sy - h), (sx + h, sy + h)), ((sx - h, sy - h), (sx + h - 8, sy - h + 8)), ((sx - h, sy - h + 8), (sx - h + 8, sy + 0.3 * h)),
                   ((sx + 0.3 * h, sy + h - 8), (sx + h - 8, sy + h))):
        A(box((a[0], a[1], top), (b[0], b[1], top + 40), CLIP))
    route('sat_stair', (sx - h - 40, sy - h - 40, 0), (sx + 30, sy + 30, top))
    jumppad(sx - h - 40, sy - h - 120, 0, (sx + 40, sy - 30, top), top + 220, 'pad_sat')
    weapon('balloony', sx + 50, sy + 20, top, 'black')
    item('ammo_imperius', sx + 20, sy - 60, top)
    rx, ry = sx + h - 6, sy + h - 6
    M.ent('func_rotating', brushes=[box((rx - 8, ry - 8, top + 36), (rx + 8, ry + 8, top + 52), ORIGIN),
                                    box((rx - 4, ry - 4, top + 70), (rx + 4, ry + 4, top + 78), NODRAW_NS)],
          model2=splib.IQM['radar'], speed=20, spawnflags=0, dmg=0)
    trigger_sound((sx - h - 220, sy + h + 140, top + 2), (sx - h - 140, sy + h + 220, top + 60), 'sound/world/items/jumper/boing.wav', 'arm_boing', 6, volume=0.5)
    light(sx, sy, top + 120, 180, '1 0.9 0.8')
    spawn(sx + 160, sy - 100, 0, 135)


# =================================================================================================== Crater Springs + habitat pods
def crater_springs():
    x0, y0, x1, y1 = L.COVE
    hx, hy, hr = L.COVE_HOLE
    tile = box((COVE_TILE[0], COVE_TILE[1], L.SLAB_BOT), (COVE_TILE[2], COVE_TILE[3], 0), CAULK)
    cut = [box((x0, y0, L.SHALLOW), (x1, y1, 32), CAULK), cyl(hx, hy, hr, L.COVE_HOLE_Z, 32, CAULK, 16)]
    def tx(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(c[2]) < 0.5: return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('regolith') if c[2] > L.COVE_HOLE_Z + 1 else T('pool_tile')
        return T('lunar_rock') if math.hypot(c[0] - hx, c[1] - hy) < hr + 2 else T('pool_band')
    for b in carve(tile, cut):
        A(edge_faces_caulk(texby(b, tx), COVE_TILE))
    solids = []
    bw = L.COVE_BEACH
    beach = hull([(x, y1, L.SHALLOW) for x in (x0, x1)] + [(x, y1, 0) for x in (x0, x1)] + [(x, y1 - bw, L.SHALLOW) for x in (x0, x1)],
                 {'top': T('regolith'), 'side': T('pool_band'), 'bot': CAULK}, round_pts=False)
    A(beach); solids.append(beach)
    for j in range(3):
        b = box((x1 - 64 + 21 * j, -1400, L.SHALLOW), (x1 - 64 + 21 * (j + 1), -1180, L.SHALLOW + 16 * (j + 1)), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
        A(b); solids.append(b)
    for b in carve(box((x0, y0, L.SHALLOW), (x1, y1, L.WATER), CAULK), solids):
        A(water_faces(b))
    A(water_faces(cyl(hx, hy, hr, L.COVE_HOLE_Z, L.SHALLOW, CAULK, 16), True))
    NOGO.append(tuple(COVE_TILE))
    item('holdable_floater', hx, hy, L.COVE_HOLE_Z); item('ammo_betty', hx + 90, hy - 60, L.COVE_HOLE_Z)
    item('ammo_splasher', x0 + 90, y0 + 120, L.SHALLOW); item('ammo_bubbleg', x1 - 140, y1 - 60, 0)
    light(hx, hy, L.COVE_HOLE_Z + 80, 220, '0.5 1 0.6')
    for (x, y) in ((x0 + 160, y0 + 300), (x1 - 160, y0 + 700)):
        light(x, y, 40, 160, '0.5 1 0.7')
    speaker((x0 + x1) / 2, (y0 + y1) / 2, 0, 'ambient/water_bubble', volume=0.4)
    A(sign_box((x0 - 96, y1 + 120, 100), (x0 + 288, y1 + 124, 172), T('sign_springs'), 1024, 192, back=CAULK, facing='s'))
    A(box((x0 - 104, y1 + 124, 0), (x0 + 296, y1 + 140, 180), {'side': T('panel_d'), 'top': T('panel_d'), 'bot': CAULK}))
    NOGO.append((x0 - 120, y1 + 100, x0 + 310, y1 + 160))
    for i, (rx0, ry0, rx1, ry1) in enumerate(L.PODS):
        custom(f'pod_{i}', (rx0 + rx1) / 2, (ry0 + ry1) / 2, 0)
        clipped(SH.pod((rx0, ry0, rx1, ry1)))
        NOGO.append((rx0 - 40, ry0 - 40, rx1 + 40, ry1 + 40))
        xc, yc = (rx0 + rx1) / 2, (ry0 + ry1) / 2
        route(f'pod{i}_door', (rx1 + 120, yc, 0), (xc - 30, yc, 0))
        if i == 0: jumppad(rx1 + 130, ry1 - 30, 0, (xc - 40, yc + 30, L.POD_H), L.POD_H + 140, f'pad_pod{i}')
        else: jumppad(rx1 + 110, ry0 + 40, 0, (xc - 40, yc - 20, L.POD_H), L.POD_H + 140, f'pad_pod{i}')
        light(xc, yc, L.POD_H - 50, 160, '0.9 0.95 1')
        furn('cargo', xc - 90, yc + 50, 0, 10, [((-26, -26, 0), (26, 26, 54))])
        furn('canister', xc - 100, yc - 60, 0, 0, [((-20, -20, 0), (20, 20, 58))])
    p0, p1 = L.PODS
    item('ammo_balloony', (p0[0] + p0[2]) / 2 + 40, (p0[1] + p0[3]) / 2 - 40, L.POD_H)
    item('item_speedy', (p1[0] + p1[2]) / 2 - 60, (p1[1] + p1[3]) / 2, L.POD_H)
    item('ammo_boaster', (p0[0] + p0[2]) / 2 + 20, (p0[1] + p0[3]) / 2, 0)
    item('ammo_bubbleg', (p1[0] + p1[2]) / 2 + 60, (p1[1] + p1[3]) / 2, 0)
    furn('rover', -1440, -620, 0, 110, [((-108, -42, 0), (108, 42, 72))])
    furn('lounger_o', -2210, -1720, 0, 80, [((-34, -14, 0), (34, 14, 14))])
    furn('mini_rocket_b', -1460, -900, 0, 30, [((-30, -30, 0), (30, 30, 170))])
    furn('dish_small', -2230, -350, 0, 135, [((-10, -10, 0), (10, 10, 110))])
    spawn(-1450, -300, 0, 270)
    spawn(-2200, -1900, 0, 45)


# =================================================================================================== Star Boulevard
def boulevard():
    x0, y0, x1, y1 = L.CAFE
    custom('cafe', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    clipped(SH.cafe())
    NOGO.append((x0 - 160, y0 - 130, x1 + 40, y1 + 140))
    yc = (y0 + y1) / 2
    route('cafe_door', (x0 - 160, yc, 0), (x0 + 160, yc, 0))
    for s in (-1, 1):
        A(cyl(x0 - 105, yc + s * 75, 5, 0, 176, WCLIP, 8))
    A(box((x0 - 84, y1 + 30, 0), (x0 - 56, y1 + 110, 360), WCLIP))     # the googie pylon
    route('cafe_stair', (x1 - 400, y0 - 60, 0), (x0 + 200, yc, L.CAFE_H))
    weapon('boaster', (x0 + x1) / 2 - 40, yc + 60, 0, 'orange')
    item('ammo_boaster', x0 + 80, y0 + 80, 0); item('ammo_pumper', x0 + 80, y1 - 80, 0)
    for (x, y) in ((x0 + 140, yc - 130), (x0 + 140, yc + 150), (x0 + 300, yc - 170)):
        custom('table_s', x, y, 0, 0); A(cyl(x, y, 26, 0, 36, WCLIP, 10))
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            custom('stool_s', x + 50 * math.cos(a), y + 50 * math.sin(a), 0, 0)
        mdl_c('pad_ddmix/diner/glass_sunrise.md3', x + 8, y - 6, 36, 0.12, 20)
        mdl_c('pad_ddmix/diner/muffin_blueberry.md3', x - 10, y + 8, 36, 0.12, 0)
    bx = x1 - 24 - 130
    for k in range(4):
        custom('stool_s', bx - 50, yc - 120 + k * 80, 0, 0)
    mdl_c('pad_ddmix/diner/coffe_pot.md3', bx, yc + 60, 62, 0.18, 0)
    mdl_c('pad_ddmix/diner/glass_betty.md3', bx, yc - 40, 62, 0.14, 0)
    mdl_c('pad_ddmix/diner/glass_midnight.md3', bx, yc - 80, 62, 0.14, 0)
    furn('jukebox', x0 + 300, y1 - 50, 0, 0, [((-30, -17, 0), (30, 17, 108))])
    light((x0 + x1) / 2 - 60, yc, L.CAFE_H - 90, 200, '1 0.75 0.9')
    light(x1 - 120, yc, 150, 160, '0.8 0.9 1')
    speaker((x0 + x1) / 2, yc, 100, 'machine/tv_upstairs', volume=0.25)
    item('item_armor_padshield', x0 + 120, y1 - 120, L.CAFE_H); item('ammo_betty', x1 - 120, y1 - 100, L.CAFE_H)
    for (x, y) in ((x0 + 160, y0 + 160), (x1 - 200, y1 - 180)):
        custom('parasol_p', x, y, L.CAFE_H); A(cyl(x, y, 5, L.CAFE_H, L.CAFE_H + 180, WCLIP, 6))
    spawn(x0 + 260, yc + 180, L.CAFE_H, 180)
    # Mission Control
    sx0, sy0, sx1, sy1 = L.MC
    custom('mission_control', (sx0 + sx1) / 2, (sy0 + sy1) / 2, 0)
    clipped(SH.mission_control())
    NOGO.append((sx0 - 100, sy0 - 40, sx1 + 40, sy1 + 40))
    syc = (sy0 + sy1) / 2
    route('mc_door', (sx0 - 140, syc, 0), (sx0 + 240, syc, 0))
    for (x, y, a) in ((sx0 + 240, syc - 80, 180), (sx0 + 240, syc + 80, 180)):
        furn('console', x, y, 0, a + 90, [((-58, -10, 0), (58, 30, 60))])
    mdl_c('pad_pc/pad_tft.md3', sx0 + 160, syc - 60, 40, 0.25, 0)
    mdl_c('pad_pc/keyboard.md3', sx0 + 160, syc + 30, 40, 0.3, 0)
    item('holdable_bambam', sx1 - 80, syc, 0); item('ammo_imperius', sx0 + 80, sy0 + 70, 0)
    jumppad(sx0 - 90, sy0 + 70, 0, (sx0 + 150, sy0 + 150, L.MC_H), L.MC_H + 230, 'pad_mc')
    item('ammo_balloony', sx1 - 160, sy1 - 90, L.MC_H); item('item_climber', sx0 + 200, syc, L.MC_H)
    A(cyl(sx1 - 70, sy1 - 70, 52, L.MC_H, L.MC_H + 60, WCLIP, 12))
    light((sx0 + sx1) / 2, syc, L.MC_H - 60, 220, '0.7 0.9 1')
    speaker((sx0 + sx1) / 2, syc, 100, 'machine/fan_pc', volume=0.3)
    timer_sound((sx0 + sx1) / 2, syc, 40, 'machine/dingdong', 'mc_bell', 30, 15, volume=0.3)
    # the Zero-G Loo: the secret
    lx, ly = L.LOO
    custom('loo', lx, ly, 0)
    clipped(SH.loo())
    h = L.LOO_HALF
    mdl_c('pad_train/ttoilet.md3', lx + 12, ly, 0, 0.1, 180)
    M.ent('trigger_teleport', brushes=[box((lx - h + 10, ly - 22, 4), (lx + h - 22, ly + 22, 90), TRIG)], target='vault_in')
    trigger_sound((lx - h - 60, ly - 30, 4), (lx - h - 8, ly + 30, 80), 'sound/world/misc/toilet_flush.ogg', 'loo_flush', 20, volume=0.6)
    light(lx, ly, 110, 80, '0.8 0.9 1')
    NOGO.append((lx - h - 80, ly - h - 30, lx + h + 30, ly + h + 30))
    # boulevard dressing: neon posts, cargo stacks, a rover, fuel tanks
    for (y, nm) in ((-1440, 'fuel_tank'), (180, 'fuel_tank')):
        furn(nm, 1470, y, 0, 90, [((-140, -40, 0), (140, 40, 100))])
        NOGO.append((1400, y - 160, 1540, y + 160))
    for (x, y, a) in ((1700, -1060, 10), (2170, -1290, -20), (1700, 300, 30), (2050, 420, 0)):
        furn('cargo_big', x, y, 0, a, [((-40, -40, 0), (40, 40, 82))])
        furn('cargo', x + 10, y + 6, 84, a + 25, [((-26, -26, 0), (26, 26, 54))])
        KEEP_OUT.append((x, y, 70))
    for (x, y) in ((1640, -1180), (2180, -280), (1640, 460)):
        furn('canister', x, y, 0, 0, [((-20, -20, 0), (20, 20, 58))])
        furn('canister_r', x + 44, y + 10, 0, 0, [((-20, -20, 0), (20, 20, 58))])
        KEEP_OUT.append((x + 20, y, 60))
    for (x, y) in ((1420, -1650), (1420, -900), (1420, -400), (1420, 420)):
        custom('neon_post_m', x, y, 0, 0); A(box((x - 6, y - 6, 0), (x + 6, y + 6, 180), WCLIP))
        light(x, y, 190, 160, '1 0.5 0.9')
        KEEP_OUT.append((x, y, 30))
    station(2200, -1550, 0, 180)
    spawn(1900, -1150, 0, 180); spawn(2100, 200, 0, 225)


# =================================================================================================== secret: the Star Vault
def vault():
    F = L.VAULT
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('panel_d'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('starfloor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    for (x, y, nm) in ((-480, 300, 'trophy_heap'), (480, 300, 'trophy_heap'), (-560, -220, 'trophy_heap_s'), (560, -220, 'trophy_heap_s'), (-250, 420, 'trophy_heap_s')):
        custom(nm, x, y, z0)
        rr = 80 if nm == 'trophy_heap' else 50
        A(cyl(x, y, rr * 0.85, z0, z0 + rr * 0.45 - 4, WCLIP, 12))
    furn('orb', 0, 380, z0, 0, [((-50, -50, 0), (50, 50, 60))])
    A(cyl(0, 380, 44, z0 + 60, z0 + 160, WCLIP, 12))
    for (x, y, a) in ((-200, 330, 160), (200, 330, 20), (380, 60, 90), (-380, 60, 270)):
        furn('grey_alien', x, y, z0, a + 180, [((-14, -10, 0), (14, 10, 74))])
    mdl_c('ente/padstatue_gold.md3', 250, 420, z0, 0.8, 270)
    lbox(250, 420, z0, 0, (-36, -60, 0), (36, 60, 190))
    for (x, y) in ((-640, 480), (640, 480), (-640, -480), (640, -480)):
        custom('crystal_big', x, y, z0, 0, lit=False); A(cyl(x, y, 26, z0, z0 + 180, WCLIP, 6))
        light(x, y, z0 + 260, 260, '0.7 0.5 1')
    item('item_padpower', 0, 200, z0); item('item_revival', -300, 120, z0); item('holdable_killerducks', 300, 120, z0)
    item('ammo_imperius', -620, 0, z0); item('ammo_betty', 620, 0, z0); item('item_armor_padshield', 0, -100, z0)
    A(sign_box((-320, y1 - 4, z0 + 280), (320, y1, z0 + 400), T('sign_vault'), 1024, 192, facing='s'))
    M.ent('misc_teleporter_dest', (0, -260, z0 + 24), targetname='vault_in', angle=90)
    mdl_c('pad_teleporter/padtp_purple.md3', 0, -480, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -516, z0 + 2), (36, -444, z0 + 90), TRIG)], target='vault_out')
    M.ent('misc_teleporter_dest', (1480, -760, 24), targetname='vault_out', angle=180)
    for (x, y, c) in ((0, 0, '1 0.9 0.8'), (-480, 300, '1 0.8 0.5'), (480, 300, '1 0.8 0.5'), (0, -380, '0.8 0.9 1'), (0, 380, '1 0.6 1')):
        light(x, y, z0 + 260, 420, c)
    speaker(0, 0, z0 + 200, 'machine/transformer', volume=0.3)
    timer_sound(0, 300, z0 + 150, 'human/applause', 'vault_cheer', 40, 10, volume=0.4)


# =================================================================================================== movers
def comets():
    z = L.COMET_Z
    M.ent('func_rotating', brushes=[box((-8, -8, z - 8), (8, 8, z + 8), ORIGIN), box((-4, -4, z + 40), (4, 4, z + 48), NODRAW_NS)],
          model2=splib.IQM['comets'], speed=4, spawnflags=0, dmg=0)
    sx0, sy0, sx1, sy1 = L.MC
    rx, ry, rz = sx1 - 70, sy1 - 70, L.MC_H + 66
    M.ent('func_rotating', brushes=[box((rx - 8, ry - 8, rz), (rx + 8, ry + 8, rz + 16), ORIGIN), box((rx - 4, ry - 4, rz + 30), (rx + 4, ry + 4, rz + 38), NODRAW_NS)],
          model2=splib.IQM['radar'], speed=25, spawnflags=0, dmg=0)


# =================================================================================================== decoration, cover
def decor():
    rng = np.random.default_rng(7)
    A(sign_box((-400, -1996, 100), (400, -1992, 300), T('sign_main'), 1024, 256, back=CAULK, facing='n'))
    A(box((-416, -2024, 0), (416, -1996, 316), {'side': T('panel_d'), 'top': T('coping'), 'bot': CAULK}))
    NOGO.append((-460, -2048, 460, -1960))
    A(sign_box((RX + 300, RY - 600, 120), (RX + 556, RY - 596, 184), T('sign_rocket'), 1024, 256, back=CAULK, facing='s'))
    A(box((RX + 292, RY - 596, 0), (RX + 564, RY - 580, 192), {'side': T('panel_d'), 'top': T('panel_d'), 'bot': CAULK}))
    NOGO.append((RX + 270, RY - 630, RX + 590, RY - 560))
    A(sign_box((L.PL[0] + 500, L.PL[1] - 640, 110), (L.PL[0] + 756, L.PL[1] - 636, 158), T('sign_planet'), 1024, 192, back=CAULK, facing='s'))
    A(box((L.PL[0] + 492, L.PL[1] - 636, 0), (L.PL[0] + 764, L.PL[1] - 620, 166), {'side': T('panel_d'), 'top': T('panel_d'), 'bot': CAULK}))
    NOGO.append((L.PL[0] + 470, L.PL[1] - 670, L.PL[0] + 790, L.PL[1] - 600))
    def put(name, x, y, r, ang=None, z=0.0, box_=None, lit=True, tries=320, cyl_=None):
        p = near_free(x, y, r, tries)
        if p is None: return None
        a = rng.uniform(0, 360) if ang is None else ang
        custom(name, p[0], p[1], z, a, lit=lit)
        if box_:
            for (mn, mx) in box_:
                lbox(p[0], p[1], z, a, mn, mx)
        if cyl_:
            A(cyl(p[0], p[1], cyl_[0], z, z + cyl_[1], WCLIP, 8))
        KEEP_OUT.append((p[0], p[1], r))
        return p
    put('astro_statue', 520, 180, 90, ang=270, box_=[((-60, -60, 0), (60, 60, 96)), ((-40, -30, 96), (40, 30, 320))])
    put('flagpole', -620, 220, 40, ang=0, cyl_=(6, 320))
    trees = [(-1300, 300), (-900, 420), (-300, 300), (250, 420), (900, 380), (1250, 260), (-1250, -100), (1250, -120), (-1100, 1900),
             (-2150, -1100), (-2200, -600), (-1450, -1700), (-1500, -1200), (1700, 1950), (1000, 1900), (1300, 1900), (-1250, 1950),
             (-700, 1800), (700, 1800), (1000, -1950), (-1000, -1950), (2200, 1950), (-2200, 1950)]
    for i, (x, y) in enumerate(trees):
        p = put(['bulbtree_a', 'bulbtree_b', 'bulbtree_c'][i % 3], x, y, 40)
        if p: A(cyl(p[0], p[1], 12, 0, 150, WCLIP, 8))
    for i, (x, y) in enumerate(((-900, 120), (900, 120), (-1250, 650), (1300, 640), (-500, 1850), (500, 1850), (-2000, 800), (1000, 1500),
                                (-1500, -500), (2000, -1700), (-150, -1950), (2150, 1100), (-2100, -800))):
        nm = ['moonrock_a', 'moonrock_b', 'moonrock_c'][i % 3]
        rr = [60, 90, 130][i % 3]
        p = put(nm, x, y, rr * 0.9)
        if p: A(cyl(p[0], p[1], rr * 0.72, 0, rr * 0.9 - 6, WCLIP, 10))
    for i, (x, y) in enumerate(((-760, 640), (780, 660), (-1400, 900), (-300, 1900), (300, 1900), (1300, 1250), (-1900, -250), (2000, -400))):
        nm = ['crystal_a', 'crystal_b'][i % 2]
        p = put(nm, x, y, 50, lit=False)
        if p: A(cyl(p[0], p[1], 24, 0, 90, WCLIP, 8))
    for (x, y, a) in ((-1050, -1930, 90), (-900, -1930, 90), (900, -1930, 90), (1050, -1930, 90), (-1460, -1350, 0), (-2220, -1250, 0),
                      (1000, 900, 0), (2000, 1950, 0)):
        put('lounger_b' if x < 0 else 'lounger_o', x, y, 44, ang=a, box_=[((-34, -14, 0), (34, 14, 14))])
    for (x, y, nm) in ((-975, -1890, 'parasol_p'), (975, -1890, 'parasol_g'), (-1450, -1270, 'parasol_g'), (1050, 1000, 'parasol_p'), (-2230, -1150, 'parasol_p')):
        p = put(nm, x, y, 40)
        if p: A(cyl(p[0], p[1], 5, 0, 180, WCLIP, 6))
    for (x, y) in ((-1400, -100), (1380, 20), (1400, 1950), (-1380, -1850), (400, -1900)):
        put('life_ring', x, y, 30, box_=[((-4, 2, 0), (4, 10, 50))])
    for (x, y) in ((-200, 380), (200, 380), (-560, 560), (560, 560), (-200, -110), (200, -110), (-1200, -1900), (1200, -1900), (-1400, 1950), (1300, 1150)):
        p = put('neon_post', x, y, 30, ang=0, lit=False, cyl_=(6, 180))
        if p: light(p[0], p[1], 200, 170, '0.5 0.9 1')
    for (x, y) in ((-150, 620), (1280, -300), (-1300, 1000)):
        put('signpost', x, y, 40, box_=[((-5, -5, 0), (5, 5, 160))])
    put('dish_small', -800, 640, 70, box_=[((-10, -10, 0), (10, 10, 110))])
    put('dish_small', 760, 650, 70, box_=[((-10, -10, 0), (10, 10, 110))])
    put('mini_rocket', -1000, 1300, 80, box_=[((-34, -34, 0), (34, 34, 220))])
    for (x, y, nm) in ((-250, -130, 'mini_rocket_b'), (250, -130, 'mini_rocket_b'), (1050, 620, 'mini_rocket'), (-880, -120, 'mini_rocket'), (700, -130, 'mini_rocket'), (-280, 690, 'mini_rocket_b'), (300, 660, 'mini_rocket')):
        put(nm, x, y, 70, box_=[((-34, -34, 0), (34, 34, 180))])
    put('rover', 300, -60, 120, ang=200, box_=[((-108, -42, 0), (108, 42, 72))])
    # catalog odds and ends for fullness
    for (x, y, s) in ((-1600, 500, 0.4), (1500, -250, 0.4), (-1100, 1550, 0.35), (1150, 1200, 0.35), (2100, -800, 0.4)):
        p = near_free(x, y, 50)
        if p: mdl_box('pad_westernset/cactus.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 45))
    for (x, y, s) in ((-1480, -1500, 0.3), (1650, 1950, 0.25), (-300, -1900, 0.3)):
        p = near_free(x, y, 50)
        if p: mdl_box('pad_ducks/pad_duck.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 50))
    for (x, y) in ((-60, 680), (1100, -1900), (1400, -800)):
        p = near_free(x, y, 40, 96)
        if p: mdl_c('ente/deadalienA.md3', p[0], p[1], 0, 0.6, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 40))
    for (x, y) in ((-1350, 780), (1100, 1700), (-1800, -200)):
        p = near_free(x, y, 40, 96)
        if p: mdl_box('gummybears/greenbear.md3', p[0], p[1], 0, 0.5, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 40))
    p = near_free(-700, 1500, 120)
    if p:
        mdl_box('pad_westernset/camera.md3', p[0], p[1], 0, 0.35, 200); mdl_box('pad_westernset/directors_chair.md3', p[0] + 90, p[1] - 30, 0, 0.18, 200)
        mdl_box('pad_westernset/spotlight.md3', p[0] - 90, p[1] - 60, 0, 0.3, 160)
        KEEP_OUT.append((p[0], p[1], 150))
    p = near_free(800, 1450, 80)
    if p: mdl_box('pad_ddmix/padshop/cardboard_standup.md3', p[0], p[1], 0, 0.3, 270); KEEP_OUT.append((p[0], p[1], 70))
    for (x, y) in ((-1600, 1950), (1500, -1950), (-2150, 400)):
        p = near_free(x, y, 30, 96)
        if p: mdl_c('pad_ddmix/gallery/fire_extinguisher.md3', p[0], p[1], 0, 0.6, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 30))


def blockers():
    """mid-field cover where long eye-level lines run (cargo stacks and fuel canisters)"""
    for (x, y, a) in ((-700, 30, 0), (700, 30, 0), (-1150, 200, 90), (0, 300, 0), (-450, -1950, 0), (450, -1950, 0), (-1856, 560, 15),
                      (-1500, 400, 70), (-420, -110, 30), (420, -110, 60), (-2050, -300, 0), (1180, -100, 20), (-560, 680, 10)):
        p = near_free(x, y, 70, 200)
        if p:
            custom('cargo_big', p[0], p[1], 0, a); lbox(p[0], p[1], 0, a, (-40, -40, 0), (40, 40, 82))
            custom('cargo', p[0] + 8, p[1] - 4, 84, a + 20); lbox(p[0] + 8, p[1] - 4, 84, a + 20, (-26, -26, 0), (26, 26, 54))
            KEEP_OUT.append((p[0], p[1], 70))


# =================================================================================================== spawns + loose items
def items_misc():
    item('ammo_nipper', -400, -60, 0); item('ammo_nipper', 600, 1700, 0); item('ammo_nipper', 1800, -1800, 0)
    item('item_armor_shard', -1600, 300, 0); item('item_armor_shard', 1600, 600, 0); item('item_armor_shard', -900, 1700, 0)
    item('ammo_pumper', 1000, 500, 0); item('ammo_boaster', -1900, 1950, 0); item('ammo_boaster', 2200, 1800, 0); item('ammo_imperius', -2200, 1850, 0)
    station(-1150, 450, 0, 0)
    for (x, y, a) in ((-900, 260, 270), (900, 280, 270), (-1700, 600, 0), (1700, -300, 180), (-600, 1750, 270), (800, 1650, 270),
                      (-2000, 1950, 315), (2150, 1950, 225), (0, -1900, 90), (-1800, -1150, 0)):
        p = near_free(x, y, 48)
        if p: spawn(p[0], p[1], 0, a)


def lights_and_sound():
    for (x, y) in ((0, 200), (-1000, 1600), (1000, 1600), (-1800, 0), (1800, -600), (0, -1900), (-700, -500), (700, -500)):
        light(x, y, 420, 340, '0.85 0.88 1')
    for (x, y) in ((-2250, -1000), (-2250, 1000), (2250, -1200), (2250, 600), (-1200, -2000), (1200, -2000)):
        speaker(x, y, 60, 'ambient/wind_night', volume=0.25)
    timer_sound(2200, -1800, 400, 'machine/fog_horn', 'horn', 70, 30, volume=0.3)
    timer_sound(-2200, 1900, 400, 'machine/transformer', 'hum1', 25, 10, volume=0.3)


def main():
    splib.STATE['out'] = OUT
    TX.make_textures()
    import sp_models as PM
    import sp_props as PP
    sp, fp = L.tube_path(), L.flume_path()
    PM.SUPPORTS['tube'] = supports_for(sp[1:], 4, 120)
    PM.SUPPORTS['flume'] = supports_for(fp[1:], 3, 100)
    PM.make()
    PP.make()
    sky_hull(); ground(); plain_and_ridge()
    spires(); lander(); lagoon(); rocket(); slides_place(); planet(); black_hole(); crater_springs(); boulevard()
    vault(); comets()
    items_misc()
    decor(); blockers()
    lights_and_sound()
    drop_slivers()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (0, -1700, 700), angles='12 90 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padspace/build_space.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
