#!/usr/bin/env python3
"""Splash World: Cloud Lagoon - World of Padman water park generator (map 'waterpark').

    OUT=/path/to/out python3 build_waterpark.py

Writes <OUT>/maps/waterpark.map plus textures, scripts/waterpark.shader, scripts/waterpark.arena.
Layout (x east, y north, deck at z=0, island x -2048..2048, y -1792..1792 floating above the clouds):
  center  Mt. Splashmore slide tower (stairwell + plunge pool), 3 slides, secret grotto below
  ring    lazy river with 4 bridges, a jungle cave and a waterfall curtain
  W wave pool + wave machine house    NW high dive + dive pool       N infinity terrace, arcade, bar
  NE pirate cove lagoon + ship         E splash zone + soak fortress  SE snack shack (2 floors)
  S  entrance plaza, statue fountain, ticket gate, gondola station    SW changing rooms
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import textures
import tiki_models as TK

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
T = lambda n: 'waterpark/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'
SAND = 'pad_nature/sand007'; GRASS = 'pad_nature/nature15'; STONE = 'pad_fountain/stone_01'
PLANK = 'pad_wood/planke10'; ROOFT = 'pad_roof/roof04'; LIEGE = 'pad_garden/liegestoff02'
SHIPW = 'pad_pirate/shipplanke_wall02'; SHIPD = 'pad_pirate/planke01'; MAST = 'pad_pirate/shipmast'
CHEST = 'pad_pirate/truhe001'; WALLB = 'pad_fountain/wall_01'

wopmap.TEXSCALE.update({T('deck'): (1, 1), T('path'): (0.5, 0.5), T('rock'): (1, 1), T('rock_dark'): (1, 1),
                        T('pool_tile'): (0.5, 0.5), T('pool_lane'): (0.5, 0.5), T('pool_band'): (0.5, 0.5),
                        T('coping'): (0.5, 0.5), SAND: (0.5, 0.5), T('checker'): (0.5, 0.5), GRASS: (0.5, 0.5), STONE: (1, 1),
                        T('palm_trunk'): (0.25, 0.25), T('thatch'): (0.5, 0.5), T('frond'): (0.5, 0.5),
                        T('water'): (0.5, 0.5), T('counter_front'): (0.25, 0.25), T('stucco_sand'): (0.5, 0.5), T('teak'): (0.5, 0.5),
                        T('spray'): (0.5, 0.5), T('waterfall'): (1, 1), ROOFT: (0.5, 0.5)})

M = Map({'message': 'Splash World: Cloud Lagoon Deluxe', '_ambient': '6', 'gridsize': '96 96 128',
         '_blocksize': '0', 'enableBreath': '1'})
A = M.add
ISL = (-2048, -1792, 2048, 1792)
ZB = -448                     # bottom of the deck columns
CANNON_GAP = (1376, 1504)     # y span of the east edge left open (above z 52) for the sky cannon
HOLES = []                    # (rect, wall_tex, fill function)
ZONES = []                    # (rect, top texture)
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}


import json
BOUNDS = json.load(open(next(p for p in (os.path.join(HERE, 'md3bounds.json'), os.path.join(os.path.dirname(HERE), 'md3bounds.json'))
                             if os.path.exists(p))))


def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """misc_model resting on a surface at height zsurf (origin z from the model's real lowest vertex)"""
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p) or next((v for k, v in BOUNDS.items() if k.lower() == p.lower()), None)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def tk(name, x, y, z, angle=0, lm=True, **kw):
    """place a tiki_models MD3 (origin = base centre); lightmapped unless lm=False (vertex-lit alpha/glow pieces)"""
    path, sc = TK.get(name, **kw)
    extra = dict(spawnflags=4, _lightmapscale=0.5, _castshadows=1, _receiveshadows=1) if lm else {}
    return M.model(path, (round(x, 2), round(y, 2), round(z, 2)), scale=sc, angle=angle, **extra)


def hole(rect, wall, fn):
    HOLES.append((rect, wall, fn))


def zone(rect, tex):
    ZONES.append((rect, tex))


def on_deck(x, y, r=0):
    """True if (x,y) (+-r) is plain island deck, not inside any hole"""
    if not (ISL[0] + r < x < ISL[2] - r and ISL[1] + r < y < ISL[3] - r): return False
    return not any(h[0][0] - r < x < h[0][2] + r and h[0][1] - r < y < h[0][3] + r for h in HOLES)


def light(x, y, z, val, color='1 0.95 0.85', **kw):
    M.ent('light', (x, y, z), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    M.ent('target_speaker', (x, y, z), **kv)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (x, y, floor + 16), **kw)


def weapon(w, x, y, floor, **kw):
    M.ent('weapon_' + w, (x, y, floor + 16), marker='blue', **kw)


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (x, y, floor + 25), angle=ang)


def clipbox(mn, mx):
    A(box(mn, mx, WCLIP))


# =================================================================================================== primitives
def palm(x, y, z, h=230, lean=(18, 6), seg=6, fronds=11, r0=11, seed=0):
    """leaning trunk of stacked octagons + nonsolid arching fronds (3 bent segments each)"""
    import random
    rr = random.Random(seed * 7919 + int(x) * 31 + int(y))
    px, py = x, y
    for i in range(seg):
        t0, t1 = i / seg, (i + 1) / seg
        z0, z1 = z + h * t0, z + h * t1
        ox0, oy0 = x + lean[0] * t0 ** 1.6, y + lean[1] * t0 ** 1.6
        ox1, oy1 = x + lean[0] * t1 ** 1.6, y + lean[1] * t1 ** 1.6
        r = r0 - 4 * t0
        pts = [(ox0 + r * math.cos(a), oy0 + r * math.sin(a), z0) for a in [k * math.pi / 4 for k in range(8)]]
        pts += [(ox1 + (r - 0.6) * math.cos(a), oy1 + (r - 0.6) * math.sin(a), z1) for a in [k * math.pi / 4 for k in range(8)]]
        A(hull(pts, T('palm_trunk')))
        px, py = ox1, oy1
    top = z + h
    A(cyl(px, py, 10, top, top + 12, T('palm_trunk'), 6))
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + rr.uniform(-0.15, 0.15)
        ca, sa = math.cos(a), math.sin(a)
        nx, ny = -sa, ca
        L = rr.uniform(105, 135); up = rr.uniform(14, 30); droop = rr.uniform(40, 80)
        wdt = rr.uniform(17, 22)
        z0 = top + 6 + (k % 3) * 2
        prof = [(0, z0, 4), (L * 0.35, z0 + up, wdt), (L * 0.7, z0 + up * 0.6 - droop * 0.25, wdt * 0.85), (L, z0 - droop, 3)]
        for (u0, za, wa), (u1, zb, wb) in zip(prof, prof[1:]):
            pts = []
            for (u, zz, ww) in ((u0, za, wa), (u1, zb, wb)):
                for sgn in (-1, 1):
                    bx, by = px + ca * u + nx * ww * sgn, py + sa * u + ny * ww * sgn
                    pts.append((bx, by, zz)); pts.append((bx, by, zz + 1.2))
            A(hull(pts, T('frond'), round_pts=False))


def umbrella(x, y, z, tex, h=104, r=64):
    A(cyl(x, y, 3, z, z + h, T('metal_white'), 6))
    A(hull([(x + r * math.cos(a), y + r * math.sin(a), z + h) for a in [k * math.pi / 6 for k in range(12)]] +
           [(x, y, z + h + 30)], {'top': T(tex), 'bot': T(tex), 'side': T(tex)}))


def lounger(x, y, z, ang, tex=LIEGE):
    """sun lounger as two brushes (seat + raised back), ang in degrees (0 = back toward -x)"""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def P(u, v, w): return (x + u * c - v * s, y + u * s + v * c, z + w)
    A(hull([P(u, v, w) for u in (-36, 22) for v in (-14, 14) for w in (0, 12)], {'top': tex, 'side': T('metal_white')}))
    A(hull([P(-36, v, 12) for v in (-14, 14)] + [P(-20, v, 12) for v in (-14, 14)] + [P(-36, v, 36) for v in (-14, 14)] +
           [P(-31, v, 37) for v in (-14, 14)], {'side': tex, 'bot': T('metal_white')}))


def table(x, y, z, r=28, h=30, top=T('wood_white'), umb=None):
    A(cyl(x, y, 4, z, z + h - 4, T('metal_white'), 6))
    A(cyl(x, y, r, z + h - 4, z + h, top, 12))
    if umb:
        A(cyl(x, y, 2, z + h, z + h + 76, T('metal_white'), 6))
        A(hull([(x + 56 * math.cos(a), y + 56 * math.sin(a), z + h + 76) for a in [k * math.pi / 6 for k in range(12)]] +
               [(x, y, z + h + 100)], T(umb)))


def stool(x, y, z, h=20, r=9):
    A(cyl(x, y, r, z, z + h, T('metal'), 8))


def planter(x0, y0, x1, y1, z=0, h=12, rim=T('coping')):
    A(box((x0, y0, z), (x1, y1, z + h), {'top': GRASS, 'side': rim}))
    return z + h


def crate(x, y, z, s=48, h=None):
    A(box((x - s // 2, y - s // 2, z), (x + s // 2, y + s // 2, z + (h or s)), T('crate')))
    return z + (h or s)


def sign(mn, mx, tex, facing, tw=512, th=128):
    A(sign_box(mn, mx, T(tex), tw, th, back=T('metal_white'), facing=facing))


def post_sign(x, y, tex, facing, w=128, h=32, z=88, tw=512, th=128):
    A(cyl(x, y, 4, 0, z, T('metal_white'), 6))
    if facing in ('n', 's'):
        sign((x - w // 2, y - 3, z), (x + w // 2, y + 3, z + h), tex, 'ns', tw, th)
    else:
        sign((x - 3, y - w // 2, z), (x + 3, y + w // 2, z + h), tex, 'ew', tw, th)


def jumppad(x, y, z, land, apex_extra=48, name=None):
    """pad + trigger_push + target_position aimed so the player lands at `land` (x,y,z)"""
    A(cyl(x, y, 36, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    lx, ly, lz = land
    oz = z + 6 + 32
    apex = max(lz, oz) + apex_extra
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - lz) / 800)
    f = tu / (tu + td)
    tx, ty = x + (lx - x) * f, y + (ly - y) * f
    name = name or f'jp{len(M.ents)}'
    M.ent('trigger_push', brushes=[box((x - 28, y - 28, z + 6), (x + 28, y + 28, z + 70), TRIG)], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    light(x, y, z + 40, 120, '1 0.6 0.2')


def rail(x0, y0, x1, y1, z, h=24, t=4, tex=None):
    A(box((min(x0, x1), min(y0, y1), z), (max(x0, x1), max(y0, y1), z + h), tex or T('metal_white')))


def glass_rail(x0, y0, x1, y1, z):
    """perimeter railing segment along an axis: glass panel + top bar"""
    A(box((x0, y0, z), (x1, y1, z + 36), T('glassns')))
    A(box((x0, y0, z + 36), (x1, y1, z + 40), T('metal_white')))


def tri_pts(cx, cy, r, n, z0, z1, ph=0):
    return [(cx + r * math.cos(ph + 2 * math.pi * k / n), cy + r * math.sin(ph + 2 * math.pi * k / n), zz) for k in range(n) for zz in (z0, z1)]


# =================================================================================================== slides
def slide_path(pts, width, tex, wall_h=32, wall_t=8, floor_t=16, roof=None, wall_tex=None):
    """pts: centerline (x,y,z_floor_top). Mitred segments; returns nothing (adds brushes)."""
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
    hw = width / 2
    wt = wall_tex or tex
    for i in range(n - 1):
        (ma, fa), (mb, fb) = jl[i], jl[i + 1]
        ca, cb = P[i], P[i + 1]
        za, zb = ca[2], cb[2]
        def edge(c, m, f, off): return c[:2] + m * off * f
        La, Ra = edge(ca, ma, fa, hw), edge(ca, ma, fa, -hw)
        Lb, Rb = edge(cb, mb, fb, hw), edge(cb, mb, fb, -hw)
        # floor: two triangle prisms
        for tri in ((La, Ra, Lb, za, za, zb), (Ra, Rb, Lb, za, zb, zb)):
            p1, p2, p3, z1, z2, z3 = tri
            pts3 = [(p1[0], p1[1], z1), (p2[0], p2[1], z2), (p3[0], p3[1], z3),
                    (p1[0], p1[1], z1 - floor_t), (p2[0], p2[1], z2 - floor_t), (p3[0], p3[1], z3 - floor_t)]
            A(hull(pts3, {'top': T(tex), 'side': T(wt), 'bot': T(wt)}, round_pts=False))
        for side in (1, -1):
            ia, ib = edge(ca, ma, fa, side * hw), edge(cb, mb, fb, side * hw)
            oa, ob = edge(ca, ma, fa, side * (hw + wall_t)), edge(cb, mb, fb, side * (hw + wall_t))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - floor_t), (p[0], p[1], zz + wall_h)]
            A(hull(pw, T(wt), round_pts=False))
        if roof:
            oLa, oRa = edge(ca, ma, fa, hw + wall_t), edge(ca, ma, fa, -hw - wall_t)
            oLb, oRb = edge(cb, mb, fb, hw + wall_t), edge(cb, mb, fb, -hw - wall_t)
            for tri in ((oLa, oRa, oLb, za, za, zb), (oRa, oRb, oLb, za, zb, zb)):
                p1, p2, p3, z1, z2, z3 = tri
                pr = [(p1[0], p1[1], z1 + wall_h), (p2[0], p2[1], z2 + wall_h), (p3[0], p3[1], z3 + wall_h),
                      (p1[0], p1[1], z1 + wall_h + 6), (p2[0], p2[1], z2 + wall_h + 6), (p3[0], p3[1], z3 + wall_h + 6)]
                A(hull(pr, T(roof), round_pts=False))


def ease_path(p0, p1, n, zcurve=None):
    out = []
    for i in range(n + 1):
        t = i / n
        z = p0[2] + (p1[2] - p0[2]) * (zcurve(t) if zcurve else t)
        out.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, z))
    return out


# =================================================================================================== ISLAND / DECK
def build_ground():
    cuts = [h[0] for h in HOLES]
    for zr, tex in ZONES: cuts.append(zr)
    pieces = [(r, T('deck')) for r in sub_rects(ISL, cuts)]
    for i, (zr, tex) in enumerate(ZONES):          # later zones override earlier ones
        later = [z[0] for z in ZONES[i + 1:] if z[0][0] < zr[2] and z[0][2] > zr[0] and z[0][1] < zr[3] and z[0][3] > zr[1]]
        for r in sub_rects(zr, [h[0] for h in HOLES] + later):
            pieces.append((r, tex))

    def side_tex(px, py):
        if not (ISL[0] < px < ISL[2] and ISL[1] < py < ISL[3]): return T('rock')
        for (r, wall, fn) in HOLES:
            if r[0] < px < r[2] and r[1] < py < r[3]: return wall
        return CAULK
    for (x0, y0, x1, y1), top in pieces:
        b = box((x0, y0, ZB), (x1, y1, 0), {'top': top, 'bot': CAULK, 'side': CAULK})
        for f in b.faces:
            if abs(f.n[2]) > 0.5: continue
            # sample along the face just outside
            if abs(f.n[0]) > 0.5:
                xs = x1 + 1 if f.n[0] > 0 else x0 - 1
                samples = [(xs, y0 + (y1 - y0) * t) for t in (0.02, 0.25, 0.5, 0.75, 0.98)]
            else:
                ys = y1 + 1 if f.n[1] > 0 else y0 - 1
                samples = [(x0 + (x1 - x0) * t, ys) for t in (0.02, 0.25, 0.5, 0.75, 0.98)]
            texs = [side_tex(*s) for s in samples]
            vis = [t for t in texs if t != CAULK]
            f.tex = vis[0] if vis else CAULK
            f.sc = wopmap.default_scale(f.tex)
        A(b)
    for r, wall, fn in HOLES:
        fn(r)
    # base slab + rock skirt
    A(box((ISL[0], ISL[1], ZB - 64), (ISL[2], ISL[3], ZB), {'side': T('rock'), 'top': CAULK, 'bot': T('rock_dark')}))
    # hanging rock cones under the island
    import random
    rnd = random.Random(4)
    nx, ny = 5, 4
    cw, ch = (ISL[2] - ISL[0]) / nx, (ISL[3] - ISL[1]) / ny
    for i in range(nx):
        for j in range(ny):
            cx = ISL[0] + cw * (i + 0.5) + rnd.uniform(-30, 30); cy = ISL[1] + ch * (j + 0.5) + rnd.uniform(-30, 30)
            r = min(cw, ch) / 2 - 40
            depth = rnd.uniform(500, 1200) * (1.3 if 0 < i < nx - 1 and 0 < j < ny - 1 else 0.8)
            base = [(cx + r * math.cos(a) * rnd.uniform(0.85, 1.0), cy + r * math.sin(a) * rnd.uniform(0.85, 1.0), ZB - 64)
                    for a in [k * 2 * math.pi / 7 + rnd.uniform(0, 0.4) for k in range(7)]]
            tip = (cx + rnd.uniform(-80, 80), cy + rnd.uniform(-80, 80), ZB - 64 - depth)
            A(hull(base + [tip], {'top': CAULK, 'side': T('rock'), 'bot': T('rock')}))
    # perimeter: railing + invisible walls just outside the island
    z = 0
    for x in range(ISL[0], ISL[2], 256):
        for y0, y1 in ((ISL[1], ISL[1] + 8), (ISL[3] - 8, ISL[3])):
            pass
    return


def perimeter(skip):
    """glass railing inside the edge (except `skip` spans) + clip walls outside"""
    E = 8
    segs = []
    for x in range(ISL[0] + E, ISL[2] - E, 256):
        x2 = min(x + 256, ISL[2] - E)
        segs.append(('s', x, x2)); segs.append(('n', x, x2))
    for y in range(ISL[1] + E, ISL[3] - E, 256):
        y2 = min(y + 256, ISL[3] - E)
        segs.append(('w', y, y2)); segs.append(('e', y, y2))
    for side, a0, a1 in segs:
        for (s2, b0, b1) in skip:
            if s2 == side and a0 < b1 and a1 > b0:
                break
        else:
            if side == 's': glass_rail(a0, ISL[1], a1, ISL[1] + E, 0)
            if side == 'n': glass_rail(a0, ISL[3] - E, a1, ISL[3], 0)
            if side == 'w': glass_rail(ISL[0], a0, ISL[0] + E, a1, 0)
            if side == 'e': glass_rail(ISL[2] - E, a0, ISL[2], a1, 0)
    H = 1400
    A(box((ISL[0] - 16, ISL[1] - 16, 0), (ISL[2] + 16, ISL[1], H), CLIP))
    A(box((ISL[0] - 16, ISL[3], 0), (ISL[2] + 16, ISL[3] + 16, H), CLIP))
    A(box((ISL[0] - 16, ISL[1], 0), (ISL[0], ISL[3], H), CLIP))
    gy0, gy1 = CANNON_GAP                      # sky cannon flight path: clip only up to z 80 there
    A(box((ISL[2], ISL[1], 0), (ISL[2] + 16, gy0, H), CLIP)); A(box((ISL[2], gy1, 0), (ISL[2] + 16, ISL[3], H), CLIP))
    A(box((ISL[2], gy0, 0), (ISL[2] + 16, gy1, 52), CLIP))
    # rocky outcrops hugging the cliffs (below deck level, outside the island footprint)
    import random
    rnd = random.Random(21)
    def chunks(a0, a1):
        out = []; a = a0
        while a < a1 - 60:
            L = min(a1 - a, rnd.uniform(180, 340)); out.append((a, a + L)); a += L
        return out
    for side in 'nsew':
        span = (ISL[0], ISL[2]) if side in 'ns' else (ISL[1], ISL[3])
        for (a, b) in chunks(*span):
            if side == 'n' and b > -720 and a < 720: continue          # infinity waterfall
            if side == 's' and b > -80 and a < 80: continue            # gondola cable
            dep = rnd.uniform(40, 130); ztop = -rnd.uniform(14, 60); zbot = -rnd.uniform(380, 640)
            m = (a + b) / 2; L = b - a
            def P(u, v, z):           # u along the side, v outward distance
                if side == 'n': return (u, ISL[3] + v, z)
                if side == 's': return (u, ISL[1] - v, z)
                if side == 'e': return (ISL[2] + v, u, z)
                return (ISL[0] - v, u, z)
            pts = [P(a, 0, ztop), P(b, 0, ztop), P(a, 0, zbot + 120), P(b, 0, zbot + 120),
                   P(a + L * 0.15, dep * 0.7, ztop - 14), P(b - L * 0.2, dep * 0.8, ztop - 24),
                   P(m, dep, ztop - rnd.uniform(40, 120)), P(m + rnd.uniform(-40, 40), dep * 0.5, zbot)]
            A(hull(pts, {'top': GRASS, 'side': T('rock'), 'bot': T('rock')}))


def skybox():
    S = T('sky'); x, y, z0, z1 = 3328, 3072, -2304, 1664
    for mn, mx in (((-x - 16, -y - 16, z0 - 16), (x + 16, y + 16, z0)), ((-x - 16, -y - 16, z1), (x + 16, y + 16, z1 + 16)),
                   ((-x - 16, -y, z0), (-x, y, z1)), ((x, -y, z0), (x + 16, y, z1)),
                   ((-x, -y - 16, z0), (x, -y, z1)), ((-x, y, z0), (x, y + 16, z1))):
        A(box(mn, mx, S, detail=False))
    # anything falling off the island dies in the clouds
    M.ent('trigger_hurt', brushes=[box((-x, -y, z0), (x, y, z0 + 256), TRIG)], dmg=500, spawnflags=0)


def floating_islets():
    import random
    rnd = random.Random(9)
    for (cx, cy, cz, r) in ((-2900, 1700, 200, 260), (2800, -2100, -100, 320), (-2700, -2500, -300, 240)):
        top = [(cx + r * math.cos(a), cy + r * math.sin(a), cz) for a in [k * 2 * math.pi / 9 for k in range(9)]]
        A(hull(top + [(x, y, cz - 40) for x, y, _ in top], {'top': GRASS, 'side': T('rock'), 'bot': T('rock')}))
        A(hull([(x, y, cz - 40) for x, y, _ in top] + [(cx + rnd.uniform(-50, 50), cy, cz - r * 1.8)], T('rock')))
        palm(cx - r * 0.3, cy + r * 0.2, cz, h=220, lean=(30, 10), seed=int(cx) % 7)
        if r > 250: palm(cx + r * 0.35, cy - r * 0.3, cz, h=180, lean=(-20, 14), seed=3)


# =================================================================================================== POOL helper
def basic_pool(r, floor, water, floor_tex=T('pool_tile'), steps_corner=None, depth_tex=None):
    x0, y0, x1, y1 = r
    A(box((x0, y0, ZB), (x1, y1, floor), {'top': floor_tex, 'side': CAULK, 'bot': CAULK}))
    blocks = []
    if steps_corner:
        cx, cy, dx, dy = steps_corner     # corner (x,y), direction of steps going down (dx,dy) unit along pool wall
        for k, zt in enumerate((-16, -32, -48)):
            # each step 32 deep stripe along the wall, 96 wide
            if dx:
                xa = cx + dx * 32 * k; xb = xa + dx * 32
                ya = cy; yb = cy + (96 if cy == y0 else -96)
            else:
                ya = cy + dy * 32 * k; yb = ya + dy * 32
                xa = cx; xb = cx + (96 if cx == x0 else -96)
            mn = (min(xa, xb), min(ya, yb), floor); mx = (max(xa, xb), max(ya, yb), zt)
            A(box(mn, mx, {'top': T('coping'), 'side': T('pool_tile')}))
            blocks.append((mn, mx))
    # water as pieces avoiding step blocks
    wr = sub_rects(r, [(b[0][0], b[0][1], b[1][0], b[1][1]) for b in blocks])
    for (a0, b0, a1, b1) in wr:
        A(box((a0, b0, floor), (a1, b1, -8), T(water)))
    for (mn, mx) in blocks:
        if mx[2] < -8:
            A(box((mn[0], mn[1], mx[2]), (mx[0], mx[1], -8), T(water)))


# =================================================================================================== ZONES
def wave_pool():
    r = (-1792, -512, -1088, 640)
    x0, y0, x1, y1 = r

    def fill(rr):
        # beach ramp (south), second slope, deep flat
        A(ramp(x0, -512, x1, -128, ZB, 0, -96, 'n', {'top': SAND, 'side': CAULK, 'bot': CAULK}))
        A(ramp(x0, -128, x1, 64, ZB, -96, -144, 'n', {'top': T('pool_tile'), 'side': CAULK, 'bot': CAULK}))
        A(box((x0, 64, ZB), (x1, y1, -144), {'top': T('pool_tile'), 'side': CAULK}))
        W = T('water_wave')
        A(hull([(x, y, z) for x in (x0, x1) for (y, z) in ((-480, -8), (-128, -8), (-128, -96))], W))
        A(hull([(x, y, z) for x in (x0, x1) for (y, z) in ((-128, -8), (64, -8), (-128, -96), (64, -144))], W))
        # corner exit steps NE
        for k, zt in enumerate((-16, -32, -48)):
            A(box((x1 - 96, y1 - 32 * (k + 1), -144), (x1, y1 - 32 * k, zt), {'top': T('coping'), 'side': T('pool_tile')}))
        isl = (-1520, 120, -1392, 248)
        wr = sub_rects((x0, 64, x1, y1), [(x1 - 96, y1 - 96, x1, y1), isl])
        for a in wr: A(box((a[0], a[1], -144), (a[2], a[3], -8), W))
        A(box((isl[0], isl[1], -144), (isl[2], isl[3], 8), {'top': SAND, 'side': T('rock'), 'bot': T('rock')}))
        palm(-1456, 184, 8, h=210, lean=(26, -18), seed=41)
        mdl('ente/ducka.md3', -1420, 140, 8, scale=0.7, angle=45)
        for k, zt in enumerate((-16, -32, -48)):
            if zt < -8: A(box((x1 - 96, y1 - 32 * (k + 1), zt), (x1, y1 - 32 * k, -8), W))
    hole(r, T('pool_band'), fill)
    zone((x0 - 32, y0, x0, y1 + 32), T('coping')); zone((x1, y0, x1 + 32, y1 + 32), T('coping'))
    zone((x0, y1, x1, y1 + 32), T('coping'))
    zone((-2048, -704, -1824, 832), SAND)
    # wave machine house  (north end)
    hx0, hx1, hy0, hy1, hz = -1760, -1120, 704, 832, 144
    wt = T('stucco_sky')
    A(box((hx0, hy0, 0), (hx1, hy0 + 16, 16), wt))                               # low sill under grates
    for gx in range(hx0, hx1, 128):                                             # grate openings w/ pillars
        A(box((gx, hy0, 16), (gx + 32, hy0 + 16, hz), wt))
        A(box((gx + 32, hy0, 112), (min(gx + 128, hx1), hy0 + 16, hz), wt))
        for bx in range(gx + 44, min(gx + 128, hx1), 24):
            A(box((bx, hy0 + 4, 16), (bx + 6, hy0 + 12, 112), T('metal_dark')))
    A(box((hx0, hy1 - 16, 0), (hx1, hy1, hz), wt))
    A(box((hx0, hy0 + 16, 0), (hx0 + 16, hy1 - 16, 8), wt)); A(box((hx0, hy0 + 16, 104), (hx0 + 16, hy1 - 16, hz), wt))
    A(box((hx1 - 16, hy0 + 16, 0), (hx1, hy1 - 16, 8), wt)); A(box((hx1 - 16, hy0 + 16, 104), (hx1, hy1 - 16, hz), wt))
    A(box((hx0 + 16, hy0 + 16, 0), (hx1 - 16, hy1 - 16, 8), T('metal_dark')))  # interior floor plate
    A(box((hx0, hy0, hz), (hx1, hy1, hz + 16), {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('metal_white')}))
    # pumps inside
    for px in (-1600, -1440, -1280):
        A(cyl(px, 768, 26, 8, 72, T('metal'), 12)); A(cyl(px, 768, 10, 72, 128, T('metal_dark'), 8))
    sign((-1520, hy0 - 8, 112), (-1360, hy0, 144), 'sign_wave_mach', 's')
    A(box((-1250, hy1 - 22, 48), (-1170, hy1 - 16, 96), T('screen')))
    light(-1440, 760, 100, 260, '0.8 0.9 1')
    item('ammo_imperius', -1700, 790, 8)
    # roof stairs on the north side
    for b in stairs(-1440, hy1, -1120, hy1 + 96, 0, hz + 16, 'e', {'top': T('teak'), 'side': T('stucco_white')}): A(b)
    # sign + loungers on the sand strip
    post_sign(-1060, -560, 'sign_wave', 'e', w=160, h=40)
    for i, y in enumerate(range(-560, 560, 128)):
        lounger(-1960, y, 0, 0, LIEGE)
        if i % 2 == 0: umbrella(-1890, y + 64, 0, ['umb_red', 'umb_blue', 'umb_yellow', 'umb_green'][i // 2 % 4])
    # bobbing inflatable rafts
    for i, (rx, ry) in enumerate(((-1560, 360), (-1340, 470), (-1660, 140))):
        M.ent('func_bobbing', brushes=[cyl(rx, ry, 52, -14, 2, {'top': T('raft'), 'side': T('raft'), 'bot': T('raft')}, 10)],
              height=6, speed=3 + i, phase=0.3 * i)
    # giant inflatable duck in the shallows
    mdl('pad_ducks/pad_duck.md3', -1860, -650, 0, scale=0.5, angle=200)
    clipbox((-1895, -700, 0), (-1825, -600, 100))
    speaker(-1440, 0, 40, 'sound/world/ambient/ocean_waves.ogg')
    speaker(-1440, 760, 60, 'sound/world/machine/mechanics.ogg')
    light(-1440, 60, 300, 600, '0.9 0.95 1')


def dive_zone():
    r = (-1600, 1056, -1152, 1504)
    x0, y0, x1, y1 = r

    def fill(rr):
        A(box((x0, y0, ZB), (x1, y1, -384), {'top': T('pool_lane'), 'side': CAULK}))
        for k, zt in enumerate((-16, -32, -48)):
            A(box((x1 - 32 * (k + 1), y0, -384), (x1 - 32 * k, y0 + 96, zt), {'top': T('coping'), 'side': T('pool_tile')}))
        W = T('water_deep')
        wr = sub_rects(r, [(x1 - 96, y0, x1, y0 + 96)])
        for a in wr: A(box((a[0], a[1], -384), (a[2], a[3], -8), W))
        for k, zt in enumerate((-16, -32, -48)):
            if zt < -8: A(box((x1 - 32 * (k + 1), y0, zt), (x1 - 32 * k, y0 + 96, -8), W))
    hole(r, T('pool_tile'), fill)
    zone((x0, y0 - 32, x1 + 32, y0), T('coping')); zone((x0, y1, x1 + 32, y1 + 32), T('coping'))
    zone((x1, y0, x1 + 32, y1), T('coping'))
    # teleporter out of the deep end (SW bottom corner)
    M.ent('trigger_teleport', brushes=[box((x0 + 8, y0 + 8, -384), (x0 + 72, y0 + 72, -320), TRIG)], target='tp_dive')
    mdl('pad_teleporter/padtp_blue.md3', x0 + 40, y0 + 40, -384, scale=0.5, angle=90)
    M.ent('misc_teleporter_dest', (-1376, 1640, 24), targetname='tp_dive', angle=270)
    light(x0 + 40, y0 + 40, -340, 200, '0.4 0.7 1')
    weapon('bubbleg', -1376, 1280, -384)            # bottom of the dive pool
    item('ammo_bubbleg', -1250, 1420, -384)
    light(-1376, 1280, -300, 320, '0.6 0.85 1')
    # ---- dive tower (west of pool): open frame, slab stairs, landings on posts
    wt = {'top': T('teak'), 'side': T('stucco_white'), 'bot': T('stucco_white')}
    post = T('metal_white')
    for b in stairs(-1888, 1120, -1792, 1440, 0, 160, 'n', wt, thick=16): A(b)              # F1 0->160
    A(box((-1888, 1440, 144), (-1600, 1536, 160), wt))                                       # landing L1
    A(box((-1600, 1440, 144), (-1504, 1504, 160), {'top': T('teak'), 'side': T('teak')}))  # 3 m board over pool
    for b in stairs(-1792, 1120, -1696, 1440, 160, 320, 's', wt, base=160, thick=16): A(b)  # F2 160->320 (going south)
    A(box((-1792, 1024, 304), (-1600, 1120, 320), wt))                                       # landing L2 / top
    A(box((-1600, 1056, 304), (-1472, 1136, 320), {'top': T('teak'), 'side': T('slide_red')}))  # 10 m platform
    for (px, py, ztop) in ((-1888, 1520, 144), (-1616, 1520, 144), (-1616, 1440, 144), (-1888, 1440, 144),
                           (-1792, 1024, 304), (-1616, 1024, 304), (-1616, 1104, 304), (-1792, 1104, 304),
                           (-1712, 1424, 160 + 16 - 16)):
        pass
    for (px, py, ztop) in ((-1888, 1520, 144), (-1616, 1520, 144), (-1888, 1456, 144), (-1616, 1456, 144),
                           (-1792, 1024, 304), (-1616, 1024, 304), (-1792, 1104, 304), (-1616, 1104, 304)):
        A(box((px, py, 0), (px + 16, py + 16, ztop), post))
    for (rx0, ry0, rx1, ry1, rz) in ((-1888, 1532, -1600, 1536, 160), (-1888, 1440, -1884, 1532, 160),
                                     (-1792, 1024, -1600, 1028, 320), (-1792, 1028, -1788, 1120, 320)):
        rail(rx0, ry0, rx1, ry1, rz, 24)
    for (ax0, ay0, ax1, ay1) in ((-1600, 1056, -1472, 1060), (-1600, 1132, -1472, 1136)):
        rail(ax0, ay0, ax1, ay1, 320, 24)
    sign((-1776, 1024, 232), (-1616, 1032, 272), 'sign_dive', 's')
    item('item_padpower', -1520, 1096, 320)
    # springboard on south edge
    A(box((-1420, 992, 0), (-1340, 1024, 40), T('stucco_white')))
    A(box((-1408, 1024, 32), (-1352, 1152, 40), {'top': T('rubberfloor'), 'side': T('metal_white')}))
    post_sign(-1200, 1010, 'sign_nodive', 's', w=96, h=24)
    item('ammo_imperius', -1648, 1280, 0)       # hidden under the dive tower walkway? (open strip x -1696..-1600)
    speaker(-1376, 1280, 40, 'sound/world/ambient/water_rippling.ogg')


def lazy_river():
    rin = (-576, -448, 576, 832); rout = (-768, -640, 768, 1024)
    legs = {'s': (rout[0], rout[1], rout[2], rin[1]), 'n': (rout[0], rin[3], rout[2], rout[3]),
            'w': (rout[0], rin[1], rin[0], rin[3]), 'e': (rin[2], rin[1], rout[2], rin[3])}
    F = -48
    # exit steps against the outer bank of each leg: (x0, y0, x1, y1, rising direction)
    STEPS = {'s': (-560, -640, -464, -544, 's'), 'n': (432, 928, 528, 1024, 'n'),
             'w': (-768, -64, -672, 32, 'w'), 'e': (672, -320, 768, -224, 'e')}
    for k, rr in legs.items():
        def fill(r, k=k):
            x0, y0, x1, y1 = r
            A(box((x0, y0, ZB), (x1, y1, F), {'top': T('pool_tile'), 'side': CAULK}))
            W = T('water_river_x') if k in 'ns' else T('water_river')
            # exit steps (-32, -16 tops; the deck is the third step)
            sx0, sy0, sx1, sy1, d = STEPS[k]
            cuts = [(sx0, sy0, sx1, sy1)]
            for j, zt in enumerate((-16, -32)):
                if d == 's': b = (sx0, sy0 + 48 * j, sx1, sy0 + 48 * (j + 1))
                if d == 'n': b = (sx0, sy1 - 48 * (j + 1), sx1, sy1 - 48 * j)
                if d == 'w': b = (sx0 + 48 * j, sy0, sx0 + 48 * (j + 1), sy1)
                if d == 'e': b = (sx1 - 48 * (j + 1), sy0, sx1 - 48 * j, sy1)
                A(box((b[0], b[1], F), (b[2], b[3], zt), {'top': T('coping'), 'side': T('pool_tile')}))
                A(box((b[0], b[1], zt), (b[2], b[3], -8), W))
            if k in 'ns':
                cy = y0 if k == 's' else y1
                for cx, sx in ((x0, 1), (x1, -1)):
                    pts = [(cx, cy), (cx + sx * 128, cy), (cx, cy + (128 if k == 's' else -128))]
                    A(prism(pts, F, 0, {'top': T('deck'), 'side': T('pool_band')}))
                # chamfered ends + rect middle (cut around the steps)
                if k == 's':
                    A(prism([(x0 + 128, y0), (x0 + 128, y1), (x0, y1), (x0, y0 + 128)], F, -8, W))
                    A(prism([(x1 - 128, y0), (x1, y0 + 128), (x1, y1), (x1 - 128, y1)], F, -8, W))
                else:
                    A(prism([(x0, y0), (x0 + 128, y0), (x0 + 128, y1), (x0, y1 - 128)], F, -8, W))
                    A(prism([(x1 - 128, y0), (x1, y0), (x1, y1 - 128), (x1 - 128, y1)], F, -8, W))
                for a in sub_rects((x0 + 128, y0, x1 - 128, y1), cuts):
                    A(box((a[0], a[1], F), (a[2], a[3], -8), W))
            else:
                for a in sub_rects(r, cuts):
                    A(box((a[0], a[1], F), (a[2], a[3], -8), W))
        hole(rr, T('pool_band'), fill)
    # bridges
    def bridge(cx, cy, axis, L=192, w=128):
        """arched wooden bridge; axis 'y' = walking north-south"""
        tex = {'top': PLANK, 'side': T('wood_dark'), 'bot': T('wood_dark')}
        if axis == 'y':
            ya, yb = cy - L // 2, cy + L // 2
            A(ramp(cx - w // 2, ya - 112, cx + w // 2, ya, 0, 0, 32, 'n', tex))
            A(box((cx - w // 2, ya, 16), (cx + w // 2, yb, 32), tex))
            A(ramp(cx - w // 2, yb, cx + w // 2, yb + 112, 0, 32, 0, 'n', tex))
            for sx in (-1, 1):
                xr = cx + sx * (w // 2 - 4)
                A(box((xr - 4, ya, 32), (xr + 4, yb, 56), T('wood_dark')))
        else:
            xa, xb = cx - L // 2, cx + L // 2
            A(ramp(xa - 112, cy - w // 2, xa, cy + w // 2, 0, 0, 32, 'e', tex))
            A(box((xa, cy - w // 2, 16), (xb, cy + w // 2, 32), tex))
            A(ramp(xb, cy - w // 2, xb + 112, cy + w // 2, 0, 32, 0, 'e', tex))
            for sy in (-1, 1):
                yr = cy + sy * (w // 2 - 4)
                A(box((xa, yr - 4, 32), (xb, yr + 4, 56), T('wood_dark')))
    bridge(0, -544, 'y'); bridge(-288, 928, 'y'); bridge(-672, -192, 'x'); bridge(672, 640, 'x')
    item('ammo_nipper', 0, -544, -48)               # under the south bridge (in the water)
    item('item_armor_shard', -672, -192, 32)
    # jungle cave over the east leg: rock piers on both banks + roof slab (walkable top)
    cy0, cy1 = 0, 320
    A(box((528, cy0, 0), (576, cy1, 112), T('rock'))); A(box((768, cy0, 0), (816, cy1, 112), T('rock')))
    A(box((528, cy0, 112), (816, cy1, 160), {'top': GRASS, 'side': T('rock'), 'bot': T('rock_dark')}))
    for b in stairs(816, 64, 1008, 160, 0, 160, 'w', {'top': T('rock'), 'side': T('rock')}): A(b)   # up to cave top from E
    light(672, 128, 72, 220, '0.5 1 0.6')
    item('item_speedy', 672, 128, -48)
    mdl('pad_ddmix/plants/fern.md3', 560, 260, 160, scale=0.12, angle=30)
    mdl('pad_ddmix/plants/fern.md3', 790, 0, 160, scale=0.1, angle=120)
    mdl('pad_ddmix/trashcan/bush.md3', 690, 60, 160, scale=0.25, angle=0)
    # waterfall curtain over the west leg
    A(box((-800, 480, 0), (-768, 576, 176), T('rock'))); A(box((-576, 480, 0), (-544, 576, 176), T('rock')))
    A(box((-800, 480, 176), (-544, 576, 208), {'top': GRASS, 'side': T('rock')}))
    A(box((-768, 520, -8), (-576, 528, 176), T('waterfall')))
    speaker(-672, 524, 60, 'sound/world/ambient/water_falling.ogg')
    speaker(672, 128, 40, 'sound/world/ambient/water_flowing.ogg')
    speaker(0, 928, 20, 'sound/world/ambient/water_flowing.ogg')
    post_sign(-860, -660, 'sign_river', 'e', w=128, h=32)


def tower():
    """Mt. Splashmore: 512x512 tile tower, interior square-spiral stairs, plunge pool, roof 512, summit 640"""
    X0, Y0, X1, Y1, H = -256, 64, 256, 576, 512
    wt = {'side': T('tile_white'), 'top': T('coping'), 'bot': T('tile_white')}
    # walls with doors: west (y 256..384), north (x -64..64), east (y 256..384); door height 128
    def wall_x(x0, x1, ys, door=None):
        if door:
            A(box((x0, ys[0], 0), (x1, door[0], H - 16), wt)); A(box((x0, door[1], 0), (x1, ys[1], H - 16), wt))
            A(box((x0, door[0], 128), (x1, door[1], H - 16), wt))
        else:
            A(box((x0, ys[0], 0), (x1, ys[1], H - 16), wt))
    wall_x(X0, X0 + 32, (Y0, Y1), (256, 384)); wall_x(X1 - 32, X1, (Y0, Y1), (256, 384))
    A(box((X0 + 32, Y0, 0), (X1 - 32, Y0 + 32, H - 16), wt))                     # south wall
    A(box((X0 + 32, Y1 - 32, 0), (-64, Y1, H - 16), wt)); A(box((64, Y1 - 32, 0), (X1 - 32, Y1, H - 16), wt))
    A(box((-64, Y1 - 32, 128), (64, Y1, H - 16), wt))
    # window slots (light into the stairwell) - small notches cut as separate sill brushes are skipped; use glass panes
    # roof slab with stair hole over flight 4 (x -224..-128, y 192..384)
    rt = {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('tile_white')}
    A(box((X0, Y0, H - 16), (X1, 192, H), rt))
    A(box((X0, 384, H - 16), (X1, Y1, H), rt))
    A(box((X0, 192, H - 16), (-224, 384, H), rt)); A(box((-128, 192, H - 16), (X1, 384, H), rt))
    # interior floor: well with plunge pool hole x -96..96, y 224..416 handled by HOLE; floor = deck zone
    zone((X0 + 32, Y0 + 32, X1 - 32, Y1 - 32), T('tile_white'))
    # flights (thin slabs so doors underneath stay open)
    st = {'top': T('coping'), 'side': T('tile_white'), 'bot': T('tile_white')}
    def flight(x0, y0, x1, y1, z0, d):
        for k in range(8):
            zt = z0 + 16 * (k + 1)
            if d == 'e': r = (x0 + 32 * k, y0, x0 + 32 * (k + 1), y1)
            if d == 'n': r = (x0, y0 + 32 * k, x1, y0 + 32 * (k + 1))
            if d == 'w': r = (x1 - 32 * (k + 1), y0, x1 - 32 * k, y1)
            if d == 's': r = (x0, y1 - 32 * (k + 1), x1, y1 - 32 * k)
            A(box((r[0], r[1], max(z0 - 16, zt - 32) if z0 > 0 else 0), (r[2], r[3], zt), st))
    flight(-128, 96, 128, 192, 0, 'e')         # south wall, 0 -> 128
    A(box((128, 96, 112), (224, 192, 128), st))              # SE landing
    flight(128, 192, 224, 448, 128, 'n')       # east wall, 128 -> 256
    A(box((128, 448, 240), (224, 544, 256), st))             # NE landing
    flight(-128, 448, 128, 544, 256, 'w')      # north wall 256 -> 384
    A(box((-224, 448, 368), (-128, 544, 384), st))           # NW landing
    flight(-224, 192, -128, 448, 384, 's')     # west wall 384 -> 512 (top step = roof level)
    # roof landing SW is the roof slab itself (x -224..-128, y 96..192 at 512) -> ok
    # plunge pool + tunnel + grotto (underground holes)
    def plunge(r):
        x0, y0, x1, y1 = r
        A(box((x0, y0, ZB), (x1, y1, -320), {'top': T('pool_lane'), 'side': CAULK}))
        W = T('water_deep')
        for k, zt in enumerate((-16, -32, -48)):
            A(box((x0, y0 + 32 * k, -320), (x0 + 64, y0 + 32 * (k + 1), zt), {'top': T('coping'), 'side': T('pool_tile')}))
        A(box((x0 + 64, y0, -320), (x1, y0 + 96, -8), W)); A(box((x0, y0 + 96, -320), (x1, y1, -8), W))
        for k, zt in enumerate((-16, -32, -48)):
            if zt < -8: A(box((x0, y0 + 32 * k, zt), (x0 + 64, y0 + 32 * (k + 1), -8), W))
    hole((-96, 224, 96, 416), T('pool_tile'), plunge)

    def tunnel(r):
        x0, y0, x1, y1 = r
        A(box((x0, y0, ZB), (x1, y1, -320), {'top': T('rock'), 'side': CAULK}))
        A(box((x0, y0, -320), (x1, y1, -208), T('water_deep')))
        A(box((x0, y0, -208), (x1, y1, 0), {'bot': T('rock_dark'), 'side': CAULK, 'top': T('tile_white') if x0 < 224 else T('deck')}))
        light((x0 + x1) // 2, (y0 + y1) // 2, -240, 160, '0.4 0.8 1')
    hole((96, 288, 352, 384), T('rock'), tunnel)
    # summit
    A(box((-96, 352, H), (96, 544, H + 128), {'top': T('deck'), 'side': T('tile_aqua')}))
    for b in stairs(-48, 96 + 64, 48, 352, H, H + 128, 'n', {'top': T('coping'), 'side': T('tile_aqua')}): A(b)
    weapon('splasher', 0, 448, H + 128, wait=25)
    mdl('ente/padstatue_winner.md3', -60, 520, H + 128, scale=0.18, angle=270)
    # roof props: start gates, umbrellas, signs
    sign((X0 - 8, 256, 392), (X0, 384, 424), 'sign_kamikaze', 'w')
    item('ammo_splasher', 200, 120, H)
    item('ammo_betty', -180, 520, H)
    spawn(150, 200, H, 180)
    # tower interior goodies
    weapon('balloony', -170, 256, 0)          # under the west-wall flight, next to the plunge well
    item('item_armor_shard', 0, 460, 0)
    for z in (60, 200, 330, 460):
        light(0, 320, z, 200, '1 0.97 0.9')
    light(0, 320, -200, 260, '0.4 0.8 1')
    # outside decoration
    sign((-160, Y0 - 8, 300), (160, Y0, 380), 'sign_splash', 's', 1024, 256)
    item('item_climber', -120, 0, 0)
    spawn(120, -40, 0, 270)
    return X0, Y0, X1, Y1, H


def grotto():
    def g1(r):    # grotto chamber
        x0, y0, x1, y1 = r
        A(box((x0, y0, ZB), (x1, y1, -320), {'top': T('rock'), 'side': CAULK}))
        # pool part x 352..448, y 256..416
        A(box((x0, y0, -320), (448, 256, -192), {'top': T('rock'), 'side': T('rock')}))
        A(box((x0, 416, -320), (448, y1, -192), {'top': T('rock'), 'side': T('rock')}))
        A(box((448, y0, -320), (x1, y1, -192), {'top': T('rock'), 'side': T('rock')}))
        A(box((416, 256, -320), (448, 416, -208), {'top': T('rock'), 'side': T('rock')}))        # exit step
        A(box((x0, 256, -320), (416, 416, -200), T('water_deep')))
        A(box((416, 256, -208), (448, 416, -200), T('water_deep')))
        A(box((x0, y0, -48), (x1, y1, 0), {'bot': T('rock_dark'), 'side': CAULK, 'top': T('deck')}))
        # crystals
        for (cx, cy, h) in ((542, 230, 90), (372, 490, 70), (542, 494, 110), (372, 150, 60)):
            A(hull([(cx - 14, cy - 10, -192), (cx + 14, cy - 8, -192), (cx, cy + 14, -192), (cx + 2, cy, -192 + h)], T('crystal')))
        A(box((488, 300, -192), (536, 348, -168), T('rock_dark')))                                 # pedestal
        A(box((460, 440, -192), (520, 480, -160), {'top': CHEST, 'side': CHEST}))                 # treasure chest
    hole((352, 128, 560, 512), T('rock'), g1)

    def g2(r):    # covered stair corridor
        x0, y0, x1, y1 = r
        A(box((x0, y0, ZB), (x1, y1, -192), {'top': T('rock'), 'side': CAULK}))
        A(box((x0, y0, -48), (x1, y1, 0), {'bot': T('rock_dark'), 'side': CAULK, 'top': T('deck')}))
    hole((448, 0, 560, 128), T('rock'), g2)       # covered part starts where the stairs are low enough to walk under

    def g3(r):    # open pit
        x0, y0, x1, y1 = r
        A(box((x0, y0, ZB), (x1, y1, -192), {'top': T('rock'), 'side': CAULK}))
    hole((448, -256, 560, 0), T('rock'), g3)
    for b in stairs(448, -256, 560, 128, -192, 0, 's', {'top': T('rock'), 'side': T('rock_dark')}, base=-192): A(b)
    weapon('imperius', 512, 324, -168, wait=150)
    item('ammo_imperius', 420, 200, -192)
    item('item_visionless', 420, 470, -192)
    item('ammo_bubbleg', 520, 200, -192)
    mdl('pad_ddmix/jail/skull.md3', 380, 200, -192, scale=0.2, angle=60)
    mdl('pad_ddmix/padship/rumbottle1.md3', 540, 420, -192, scale=0.25)
    light(512, 324, -100, 300, '0.4 0.8 1'); light(400, 200, -120, 200, '0.5 0.9 1'); light(504, 0, -60, 160, '0.6 0.9 1')
    speaker(450, 320, -120, 'sound/world/ambient/droplets_echoing.ogg')
    M.ent('trigger_multiple', brushes=[box((452, 136, -184), (556, 200, -120), TRIG)], target='secret', wait=30)
    speaker(504, 168, -140, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret')
    # rock rim + bushes around the pit
    A(box((432, -272, 0), (576, -256, 16), T('rock'))); A(box((432, -256, 0), (448, 0, 16), T('rock')))
    A(box((560, -256, 0), (576, 0, 16), T('rock')))


def slides(TW):
    X0, Y0, X1, Y1, H = TW
    # ---- KAMIKAZE (red, open, straight 28deg) west from the roof into the wave pool
    ys = 320
    pts = [(X0, ys, H), (X0 - 48, ys, H)]
    run = 900
    for i in range(1, 13):
        t = i / 12
        pts.append((X0 - 48 - run * t, ys, H - (H - 8) * (t ** 1.08)))
    pts.append((X0 - 48 - run - 96, ys, 8))
    slide_path(pts, 112, 'slide_red', wall_h=28)
    for i, (px, py, pz) in enumerate(pts[3:-1:2]):
        if pz > 90 and on_deck(px, ys, 16):
            A(box((round(px) - 8, ys - 8, 0), (round(px) + 8, ys + 8, round(pz) - 24), T('metal_white')))
    # ---- RAPIDS (green) north from the roof into the infinity pool
    xs = 160
    pts = [(xs, Y1, H), (xs, Y1 + 48, H)]
    for i in range(1, 11):                                   # main run 512 -> 332 with a lazy S-curve
        t = i / 10
        pts.append((xs + 44 * math.sin(t * math.pi * 2), Y1 + 48 + (1180 - Y1 - 48) * t, H - (H - 332) * t ** 1.1))
    pts += [(xs, 1300, 318), (xs, 1440, 300), (xs, 1490, 252), (xs, 1536, 206), (xs, 1600, 204)]   # plunge
    slide_path(pts, 112, 'slide_green', wall_h=30)
    for py in (1290, 1420):                                     # supports standing on the terrace
        z = 318 if py == 1290 else 302
        A(box((xs - 60, py - 8, 192), (xs - 44, py + 8, z - 24), T('metal_white')))
        A(box((xs + 44, py - 8, 192), (xs + 60, py + 8, z - 24), T('metal_white')))
    for (px, py, pz) in pts[3:-2:2]:
        if py < 1200 and on_deck(px, py, 16):
            A(box((round(px) - 8, round(py) - 8, 0), (round(px) + 8, round(py) + 8, round(pz) - 24), T('metal_white')))
    # ---- TORNADO (blue tube) helix SW of the tower -> river south leg
    cx, cy, rc = -352, -176, 176
    th0 = math.radians(45); sweep = math.radians(450)
    nseg = 24
    pts = [(-228, 48, H - 16)]
    for i in range(nseg + 1):
        t = i / nseg
        th = th0 - sweep * t
        pts.append((cx + rc * math.cos(th), cy + rc * math.sin(th), (H - 24) - (H - 24 - 56) * t))
    # exit chute: continue tangentially, then drop into the river
    thE = th0 - sweep
    tx, ty = math.sin(thE), -math.cos(thE)   # clockwise tangent
    ex, ey, ez = pts[-1]
    for k, zz in ((1, 44), (2, 32), (3, 14)):
        pts.append((ex + tx * 90 * k, ey + ty * 90 * k, zz))
    slide_path(pts, 96, 'slide_blue', wall_h=80, roof='tube')
    A(cyl(cx, cy, 40, 0, H - 40, T('metal_white'), 12))
    for k in range(6):
        a = th0 - math.radians(k * 60 + 30)
        for zz in (H - 120, 220):
            pass
    # balcony from tower roof to the tornado start
    A(box((-288, 48, H - 32), (-160, 64, H - 16), {'top': T('deck'), 'side': T('metal_white')}))
    return pts


def terrace():
    TX0, TX1, TY0, TY1, TZ = -960, 960, 1216, 1792, 192
    rock = {'top': T('deck'), 'side': T('stucco_sand'), 'bot': T('stucco_white')}
    # arcade ceiling slab
    A(box((TX0, TY0, 176), (TX1, 1472, TZ), {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('stucco_white')}))
    # end walls
    A(box((TX0, TY0, 0), (TX0 + 64, 1472, 176), T('stucco_sand'))); A(box((TX1 - 64, TY0, 0), (TX1, 1472, 176), T('stucco_sand')))
    # columns
    for x in range(-768, 769, 256):
        A(box((x - 20, TY0 + 8, 0), (x + 20, TY0 + 48, 176), T('stucco_white')))
    # solid mass behind the arcade (with pool basin)
    A(box((TX0, 1472, 0), (TX1, TY1, 96), {'top': T('pool_tile'), 'side': T('stucco_sand')}))
    A(box((TX0, 1472, 96), (-640, TY1, TZ), rock)); A(box((640, 1472, 96), (TX1, TY1, TZ), rock))
    A(box((-640, 1472, 96), (640, 1504, TZ), {'top': T('coping'), 'side': T('pool_band')}))
    A(box((-640, 1728, 96), (640, 1744, 184), {'top': T('coping'), 'side': T('pool_band')}))     # infinity edge
    A(box((-640, 1744, 96), (640, TY1, 152), {'top': T('pool_tile'), 'side': T('stucco_sand')}))  # catch gutter
    # pool exit steps (east end) + water
    W = T('water_pool')
    for k in range(5):
        A(box((640 - 32 * (k + 1), 1504, 96), (640 - 32 * k, 1728, 176 - 16 * k), {'top': T('coping'), 'side': T('pool_tile')}))
    sq = [(x - 8, 1512, x + 8, 1528) for x in range(-416, -128, 64)] + [(-504, 1560, -488, 1576), (-88, 1560, -72, 1576)]
    for a in sub_rects((-640, 1504, 480, 1728), sq):
        A(box((a[0], a[1], 96), (a[2], a[3], 184), W))
    for (a0, b0, a1, b1) in sq[:-2]:                         # swim-up bar stools: clip + MD3
        clipbox((a0, b0, 96), (a1, b1, 176))
        tk('swim_stool', (a0 + a1) / 2, (b0 + b1) / 2, 96, h=80)
        A(box((a0, b0, 176), (a1, b1, 184), W))
    for k in range(5):
        zt = 176 - 16 * k
        A(box((640 - 32 * (k + 1), 1504, zt), (640 - 32 * k, 1728, 184), W))
    A(box((-640, 1744, 152), (640, 1752, 184), T('spray')))                                           # spill-over
    A(box((-640, 1800, -1300), (640, 1808, 152), T('waterfall')))                                     # off the edge
    speaker(0, 1760, 100, 'sound/world/ambient/water_falling.ogg')
    # west pool exit steps too
    # INFINITY BAR: tiki bar built from MD3s (tiki_models.py); the old brush shapes stay as invisible weapon clip
    clipbox((-448, 1440, TZ), (-128, 1472, TZ + 42))                                                   # counter
    tk('counter', -288, 1456, TZ)
    A(box((-448, 1376, TZ), (-128, 1392, TZ + 96), T('bamboo')))                                       # back wall
    tk('back_bar', -288, 1392, TZ)
    for (px, py) in ((-496, 1408), (-80, 1408), (-496, 1568), (-80, 1568)):                            # tiki posts
        z0 = 96 if py > 1504 else TZ
        clipbox((px - 8, py - 8, z0), (px + 8, py + 8, 320))
        tk('totem', px, py, z0, h=320 - z0)
    A(box((-512, 1392, 320), (-64, 1584, 336), {'top': T('thatch'), 'side': T('thatch'), 'bot': T('bamboo')}))
    tk('fringe', -288, 1488, 320, lm=False)
    tk('bar_sign', -288, 1579, 272)                       # hangs from the roof slab on two ropes
    tk('string_lights', -288, 1576, 314, lm=False, L=400)
    for x in (-504, -72):
        M.model(TK.get('string_lights', L=144)[0], (x, 1488, 314), scale=TK.get('string_lights', L=144)[1], angle=90)
    sign((-400, 1380, 300), (-176, 1384, 320), 'sign_bar', 's')
    for i, (cx, top) in enumerate(((-736, TZ + 32), (-672, TZ + 64), (-608, TZ + 96), (-544, TZ + 128))):
        A(box((cx - 32, 1408, TZ), (cx + 32, 1472, top), T('crate')))
    weapon('betty', -288, 1488, 336)
    for (dx, k) in ((-420, 0), (-360, 1), (-250, 0), (-170, 1)):                                       # cocktails
        tk('drink', dx, 1458, TZ + 42, kind=k)
    for (tx, ty) in ((-40, 1440), (-520, 1350)):                                                        # tiki torches
        clipbox((tx - 4, ty - 4, TZ), (tx + 4, ty + 4, TZ + 110))
        tk('torch', tx, ty, TZ)
        light(tx, ty, TZ + 128, 220, '1 0.6 0.25')
    light(-400, 1500, 300, 160, '1 0.45 0.75'); light(-170, 1500, 300, 160, '0.35 0.95 0.9')
    light(-288, 1650, 286, 150, '1 0.92 0.75')                                                        # sign lamp
    item('ammo_betty', -200, 1420, TZ)
    item('item_armor_padshield', 760, 1600, TZ)
    # stairs up to the terrace (west + east)
    st = {'top': T('teak'), 'side': T('stucco_sand')}
    for b in stairs(-1088, 1216, -960, 1600, 0, TZ, 'n', st): A(b)
    for b in stairs(960, 1216, 1088, 1600, 0, TZ, 'n', st): A(b)
    A(box((-1088, 1600, 0), (-960, TY1, TZ), rock)); A(box((960, 1600, 0), (1088, TY1, TZ), rock))
    # jump pad from deck in front of arcade onto terrace
    jumppad(-560, 1120, 0, (-560, 1360, TZ), apex_extra=80)
    # loungers & umbrellas on terrace
    for i, x in enumerate((-900, -820, -740)):
        lounger(x, 1640, TZ, 90)
    umbrella(-780, 1720, TZ, 'umb_blue')
    for i, x in enumerate((740, 820, 900)):
        lounger(x, 1660, TZ, 90)
    umbrella(800, 1560, TZ, 'umb_red')
    # arcade interior: lockers, benches, health station, lights
    A(box((-880, 1440, 0), (-560, 1472, 112), T('locker')))
    A(box((560, 1440, 0), (880, 1472, 112), T('locker')))
    for x in (-400, 0, 400):
        A(box((x - 64, 1424, 0), (x + 64, 1456, 20), T('teak')))
    M.ent('station_health', (-200, 1380, 0), angle=270)
    item('item_revival', 240, 1380, 0)
    item('ammo_splasher', 700, 1380, 0)
    for x in (-640, -256, 256, 640):
        A(box((x - 32, 1312, 168), (x + 32, 1376, 176), T('lightpanel')))
    for x in (-400, 0, 400):
        mdl('pad_items/towelstack.md3', x, 1440, 20, scale=0.5)
    spawn(-700, 1300, 0, 270); spawn(700, 1300, 0, 270); spawn(-820, 1520, TZ, 0)


def pirate_cove():
    r = (1152, 832, 1920, 1600)
    x0, y0, x1, y1 = r
    F = -40
    HB = (1408, 1088, 1664, 1376)             # hull body
    def fill(rr):
        A(box((x0, y0, ZB), (x1, 1504, F), {'top': SAND, 'side': CAULK}))
        A(ramp(x0, 1504, x1, y1, ZB, F, 0, 'n', {'top': SAND, 'side': CAULK}))
        W = T('water_lagoon')
        cut = (1408, 1024, 1664, 1504)
        for a in sub_rects((x0, y0, x1, 1504), [cut]):
            A(box((a[0], a[1], F), (a[2], a[3], -8), W))
        A(box((1408, 1024, F), (1504, 1088, -8), W)); A(box((1568, 1024, F), (1664, 1088, -8), W))
        A(box((1504, 1024, -24), (1568, 1056, -8), W))
        A(prism([(1408, 1376), (1536, 1504), (1408, 1504)], F, -8, W))
        A(prism([(1664, 1376), (1664, 1504), (1536, 1504)], F, -8, W))
        # beach water wedge (north slope): floor rises from -40 at 1504 to 0 at 1600 -> water until z=-8 at y=1584.8
        A(hull([(x, y, z) for x in (x0, x1) for (y, z) in ((1504, -8), (1580, -8), (1504, F))], W))
    hole(r, T('pool_band'), fill)
    zone((1088, 704, 2048, 832), SAND); zone((1920, 832, 2048, 1792), SAND); zone((1088, 1600, 1920, 1792), SAND)
    zone((1088, 832, 1152, 1600), SAND)
    # --- ship
    hx0, hy0, hx1, hy1 = HB
    hull_t = {'side': SHIPW, 'top': SHIPD, 'bot': SHIPW}
    A(box((hx0, hy0, F), (hx0 + 16, 1264, 120), hull_t)); A(box((hx0, 1328, F), (hx0 + 16, hy1, 120), hull_t))
    A(box((hx0, 1264, F), (hx0 + 16, 1328, 96), hull_t))                         # gangplank gap in west bulwark
    A(box((hx1 - 16, hy0, F), (hx1, hy1, 120), hull_t))
    A(box((hx0 + 16, hy0, F), (1504, hy0 + 16, 160), hull_t)); A(box((1568, hy0, F), (hx1 - 16, hy0 + 16, 160), hull_t))
    A(box((1504, hy0, 80), (1568, hy0 + 16, 160), hull_t))                       # over stern door
    A(box((1504, hy0, F), (1568, hy0 + 16, 0), hull_t))                          # door sill
    A(box((1504, 1024, F), (1568, 1056, -24), hull_t)); A(box((1504, 1056, F), (1568, 1088, -8), hull_t))   # steps
    A(box((hx0 + 16, hy0 + 16, F), (hx1 - 16, hy1, 0), {'top': SHIPD, 'side': CAULK}))    # hold floor
    # deck slab with hatch over interior stairs (x 1424..1488, y 1184..1376)
    dk = {'top': SHIPD, 'bot': T('wood_dark'), 'side': SHIPW}
    A(box((1488, hy0 + 16, 80), (hx1 - 16, hy1, 96), dk)); A(box((hx0 + 16, hy0 + 16, 80), (1488, 1184, 96), dk))   # hatch open over the whole flight
    for b in stairs(1424, 1184, 1488, 1376, 0, 96, 'n', {'top': SHIPD, 'side': T('wood_dark')}): A(b)
    # bow
    A(prism([(hx0, hy1), (hx1, hy1), (1536, 1504)], F, 96, {'top': SHIPD, 'side': SHIPW, 'bot': SHIPW}))
    for (a, b) in (((hx0, hy1), (1536, 1504)), ((hx1, hy1), (1536, 1504))):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); nx, ny = -dy / L * 8, dx / L * 8
        A(hull([(a[0], a[1], 96), (b[0], b[1], 96), (a[0] + nx * (1 if a[0] < 1536 else -1), a[1] + ny * (1 if a[0] < 1536 else -1), 96),
                (b[0] + nx * (1 if a[0] < 1536 else -1), b[1] + ny * (1 if a[0] < 1536 else -1), 96)] +
               [(a[0], a[1], 120), (b[0], b[1], 120), (a[0] + nx * (1 if a[0] < 1536 else -1), a[1] + ny * (1 if a[0] < 1536 else -1), 120),
                (b[0] + nx * (1 if a[0] < 1536 else -1), b[1] + ny * (1 if a[0] < 1536 else -1), 120)], SHIPW))
    A(hull([(1528, 1504, 80), (1544, 1504, 80), (1536, 1620, 140), (1536, 1504, 100)], T('wood_dark')))  # bowsprit
    # quarterdeck
    A(box((hx0 + 16, hy0 + 16, 96), (hx1 - 16, 1184, 160), {'top': SHIPD, 'side': SHIPW}))
    for b in stairs(1600, 1184, 1648, 1312, 96, 160, 's', {'top': SHIPD, 'side': T('wood_dark')}): A(b)
    # mast + crow's nest
    A(cyl(1536, 1264, 16, 96, 432, MAST, 8))
    A(cyl(1536, 1264, 72, 432, 448, {'top': SHIPD, 'side': T('wood_dark'), 'bot': T('wood_dark')}, 8))
    A(cyl(1536, 1264, 12, 448, 560, MAST, 8))
    for k in range(8):
        if k in (0, 1, 2): continue
        a0 = math.pi / 8 + k * math.pi / 4; a1 = a0 + math.pi / 4
        p = [(1536 + rr * math.cos(a), 1264 + rr * math.sin(a), zz) for a in (a0, a1) for rr in (64, 72) for zz in (448, 472)]
        A(hull(p, T('wood_dark')))
    A(box((1528, 1180, 300), (1544, 1348, 312), T('beam_ns')))                     # yard (nonsolid)
    A(hull([(1536, 1184, 300), (1536, 1344, 300), (1536, 1190, 150), (1536, 1338, 150),
            (1537, 1184, 300), (1537, 1344, 300), (1537, 1190, 150), (1537, 1338, 150)], T('sail'), round_pts=False))
    weapon('betty', 1536, 1300, 448)
    mdl('pad_ddmix/cabin/telescope.md3', 1560, 1220, 448, scale=0.16, angle=90)
    jumppad(1536, 1420, 96, (1536, 1302, 448), apex_extra=64)
    # gangplank (west)
    A(hull([(1152, 1272, 0), (1152, 1320, 0), (1408, 1272, 96), (1408, 1320, 96),
            (1152, 1272, -8), (1152, 1320, -8), (1408, 1272, 88), (1408, 1320, 88)], {'top': PLANK, 'side': T('wood_dark')}))
    # kids slide from quarterdeck west into the lagoon
    slide_path([(1424, 1144, 160), (1400, 1144, 160), (1300, 1144, 70), (1220, 1144, 16), (1180, 1144, 8)], 64, 'slide_yellow', wall_h=20)
    # hold goodies
    A(box((1560, 1320, 0), (1632, 1360, 32), {'top': CHEST, 'side': CHEST}))
    mdl('pad_ddmix/padship/amphora.md3', 1600, 1150, 0, scale=0.22)
    mdl('pad_ddmix/padship/rumbottle2.md3', 1460, 1130, 0, scale=0.25)
    item('holdable_boomies', 1590, 1260, 0)
    item('ammo_betty', 1470, 1300, 96)
    light(1540, 1240, 50, 260, '1 0.75 0.4')
    # lagoon decoration
    mdl('pad_ducks/pad_duck.md3', 1300, 960, -40, scale=0.35, angle=160)
    clipbox((1270, 925, -40), (1330, 995, 34))
    for (bx, by, mname) in ((1250, 1700, 'pad_soccerball'), (1700, 1680, 'pad_basketball'), (1990, 1100, 'pad_soccerball')):
        mdl(f'pad_ball/{mname}.md3', bx, by, 0, scale=0.35)
    mdl('pad_ddmix/jail/skull.md3', 1995, 1215, 0, scale=0.22, angle=200)
    for (px, py, s) in ((1130, 760, 1), (1990, 900, 2), (1990, 1320, 3), (1300, 1720, 4), (1840, 1720, 5), (1600, 760, 6)):
        palm(px, py, 0, h=220 + (s % 3) * 25, lean=(20 - s * 8, 14 - s * 3), seed=s)
    item('ammo_bubbleg', 1990, 1600, 0)
    item('item_armor_shard', 1200, 1450, -40)
    spawn(1990, 1000, 0, 180); spawn(1400, 1680, 0, 270); spawn(1240, 900, -40, 90)
    post_sign(1120, 1140, 'sign_pirate', 'e', w=160, h=40)
    speaker(1536, 1264, 200, 'sound/world/animal/bird_gull.ogg')


def kids_zone():
    r = (1152, -384, 1792, 256)
    def fill(rr):
        x0, y0, x1, y1 = rr
        A(box((x0, y0, ZB), (x1, y1, -16), {'top': T('rubberfloor'), 'side': CAULK}))
    hole(r, T('tile_aqua'), fill)
    zone((1120, -416, 1824, -384), T('coping')); zone((1120, 256, 1824, 288), T('coping'))
    zone((1120, -384, 1152, 256), T('coping')); zone((1792, -384, 1824, 256), T('coping'))
    # mushroom fountains standing in the splash pad (on its floor at -16)
    for i, (mx, my) in enumerate(((1312, -200), (1520, 40), (1660, -260))):
        A(cyl(mx, my, 18, -16, 104, T('stucco_white'), 10))
        A(cyl(mx, my, 92, 104, 120, {'top': T('mushroom'), 'side': T('mushroom'), 'bot': T('stucco_white')}, 16))
        A(hull(tri_pts(mx, my, 60, 12, 120, 120) + [(mx, my, 150)], T('mushroom')))
        for k in range(8):
            a = k * math.pi / 4
            px, py = mx + 96 * math.cos(a), my + 96 * math.sin(a)
            nx, ny = -math.sin(a) * 30, math.cos(a) * 30
            A(hull([(px - nx, py - ny, -8), (px + nx, py + ny, -8), (px - nx, py - ny, 104), (px + nx, py + ny, 104),
                    (px - nx + math.cos(a), py - ny + math.sin(a), -8), (px + nx + math.cos(a), py + ny + math.sin(a), 104)],
                   T('spray'), round_pts=False))
        speaker(mx, my, 60, 'sound/world/ambient/water_shower.ogg')
    item('item_jumper', 1420, -30, -16)
    item('holdable_killerducks', 1700, 120, -16)
    mdl('pad_ducks/pad_duck.md3', 1720, 180, -16, scale=0.3, angle=230)
    for (dx, dy) in ((1650, 190), (1690, 90), (1760, 140)):
        mdl('ente/ducka.md3', dx, dy, -16, scale=0.6, angle=dx % 360)
    # gummy bear statues on the deck around
    for (gx, gy, c, a) in ((1072, -300, 'redbear', 0), (1072, 120, 'greenbear', 0), (1880, -300, 'yellowbear', 180),
                           (1880, 120, 'orangebear', 180)):
        mdl(f'gummybears/{c}.md3', gx, gy, 0, scale=0.8, angle=a)
        clipbox((gx - 26, gy - 40, 0), (gx + 26, gy + 40, 120))
    mdl('pad_sunflower/pad_sunflower_l.md3', 1960, -520, 0, scale=0.45, angle=120)
    mdl('pad_sunflower/pad_sunflower_l.md3', 1000, -540, 0, scale=0.4, angle=40)
    # ---- soak fortress
    FX0, FY0, FX1, FY1 = 1216, 384, 1728, 704
    wood = {'top': T('rubberfloor'), 'side': T('stucco_sun'), 'bot': T('wood_white')}
    for (px, py) in ((FX0, FY0), (FX1 - 24, FY0), (FX0, FY1 - 24), (FX1 - 24, FY1 - 24), (1460, FY0), (1460, FY1 - 24)):
        A(box((px, py, 0), (px + 24, py + 24, 112), T('stucco_coral')))
    A(box((FX0, FY0, 112), (FX1, FY1, 128), wood))
    for b in stairs(1120, 416, 1216, 672, 0, 128, 'n', {'top': T('rubberfloor'), 'side': T('stucco_sky')}): A(b)
    L2 = (1344, 448, 1600, 640)
    for (px, py) in ((L2[0], L2[1]), (L2[2] - 24, L2[1]), (L2[0], L2[3] - 24), (L2[2] - 24, L2[3] - 24)):
        A(box((px, py, 128), (px + 24, py + 24, 240), T('stucco_coral')))
    A(box((L2[0], L2[1], 240), (L2[2], L2[3], 256), wood))
    for b in stairs(1600, 448, 1696, 704, 128, 256, 's', {'top': T('rubberfloor'), 'side': T('stucco_sky')}, base=128): A(b)
    # giant tipping bucket (static, pouring) on a frame above L2
    for (px, py) in ((1376, 480), (1544, 480), (1376, 584), (1544, 584)):
        A(box((px, py, 256), (px + 16, py + 16, 400), T('stucco_coral')))
    A(box((1376, 480, 400), (1560, 600, 412), T('stucco_coral')))
    pts = []
    for k in range(12):
        a = 2 * math.pi * k / 12
        for (rr, zz) in ((60, 412), (84, 540)):
            x, y = 1468 + rr * math.cos(a), 540 + rr * math.sin(a)
            pts.append((x, y + (zz - 412) * 0.35, zz))
    A(hull(pts, {'side': T('stucco_sky'), 'top': T('water'), 'bot': T('stucco_sky')}))
    A(box((1468 - 40, 640, 128), (1468 + 40, 648, 250), T('spray')))
    weapon('bubbleg', 1460, 620, 256)
    item('ammo_boaster', 1280, 640, 128)
    # slide from L1 south edge into the splash pad
    slide_path([(1500, FY0, 128), (1500, FY0 - 24, 128), (1500, 300, 60), (1500, 250, 10), (1500, 210, 0)], 64, 'slide_purple', wall_h=20)
    light(1460, 540, 90, 260)
    item('ammo_pumper', 1300, 600, 0)
    post_sign(1100, -440, 'sign_kids', 'e', w=160, h=40)
    spawn(1880, -100, 0, 180); spawn(1950, 450, 0, 180)
    spawn(1000, 300, 0, 0)


def snack_bar(Y0, H):
    """Snack Shack serving counter: tiled counter with display case, register and striped awning; behind it a
    drinks cooler, slushie machine, coffee and popcorn machines and three chalk menu boards."""
    CT = T('counter_top')
    # front counter (tiled body + overhanging top) and the back counter with cabinet doors
    A(box((1216, -1440, 0), (1728, -1412, 36), {'top': CT, 'n': T('counter_front'), 'e': T('counter_front'),
                                                'w': T('counter_front'), 's': T('cabinet'), 'bot': CT}))
    A(box((1208, -1444, 36), (1736, -1404, 42), CT))
    A(box((1104, Y0 + 16, 0), (1840, Y0 + 48, 64), {'top': CT, 'n': T('cabinet'), 'side': T('metal_white')}))
    # glass display case on the counter (open at the back for the staff)
    G = T('glass')
    A(hull([(x, y, z) for x in (1292, 1448) for (y, z) in ((-1406, 42), (-1410, 42), (-1426, 84), (-1430, 84))], G))
    A(box((1292, -1440, 84), (1448, -1426, 86), G))
    for (xa, xb) in ((1290, 1292), (1448, 1450)):
        A(hull([(x, y, z) for x in (xa, xb) for (y, z) in ((-1406, 42), (-1440, 42), (-1440, 86), (-1426, 86))], G))
    mdl('pad_ddmix/diner/muffin_blueberry.md3', 1322, -1426, 42, scale=0.18, angle=200)
    mdl('pad_cake/pad_cakestand.md3', 1372, -1424, 42, scale=0.22)
    mdl('pad_ddmix/diner/muffin_choco.md3', 1420, -1444, 42, scale=0.18, angle=0)
    # register, tip jar, condiments
    mdl('pad_pc/padshop_tft.md3', 1600, -1428, 42, scale=0.12, angle=270)
    mdl('pad_ddmix/diner/glass_simple.md3', 1650, -1420, 42, scale=0.3)
    mdl('pad_condiments/pad_ketchup.md3', 1690, -1418, 42, scale=0.3); mdl('pad_condiments/pad_mustard.md3', 1710, -1430, 42, scale=0.3)
    mdl('pad_ddmix/diner/sugar_packet.md3', 1250, -1424, 42, scale=0.4, angle=30)
    # striped awning over the counter with a valance, lit underneath
    A(hull([(x, y, z) for x in (1200, 1744) for (y, z) in ((-1452, 176), (-1452, 170), (-1384, 148), (-1384, 142))], T('awning_red')))
    A(box((1200, -1384, 128), (1744, -1380, 150), T('awning_red')))
    for x in (1300, 1470, 1640):
        light(x, -1420, 118, 150, '1 0.9 0.75')
    # bar stools in front of the counter
    for x in (1260, 1340, 1580, 1660):
        A(cyl(x, -1384, 5, 0, 24, T('metal'), 8)); A(cyl(x, -1384, 12, 24, 30, {'top': T('awning_red'), 'side': T('metal_white'), 'bot': T('metal')}, 10))
    # behind the counter: drinks cooler, slushie machine, coffee + popcorn machines, cups and bottles
    zb = 64; yb0, yb1 = -1516, -1494
    A(box((1112, Y0 + 16, zb), (1176, -1492, 168), {'n': T('fridge'), 'side': T('metal_white'), 'top': T('metal_white'), 'bot': T('metal_white')}))
    A(box((1196, yb0, zb), (1304, yb1, zb + 10), T('metal_white')))
    for i, (x0, tex) in enumerate(((1200, 'slush_red'), (1236, 'slush_blue'), (1272, 'slush_green'))):
        A(box((x0, yb0 + 2, zb + 10), (x0 + 28, yb1 - 2, zb + 44), T(tex)))
        A(box((x0, yb0 + 2, zb + 44), (x0 + 28, yb1 - 2, zb + 48), T('metal_white')))
    A(box((1340, yb0, zb + 14), (1390, yb1, zb + 44), {'side': T('metal_dark'), 'top': T('metal'), 'bot': T('metal_dark')}))   # coffee machine
    A(box((1340, yb0, zb), (1350, yb1, zb + 14), T('metal_dark'))); A(box((1380, yb0, zb), (1390, yb1, zb + 14), T('metal_dark')))
    A(box((1356, yb1, zb + 34), (1374, yb1 + 2, zb + 40), T('awning_red')))
    mdl('pad_ddmix/diner/coffe_pot.md3', 1415, -1508, zb, scale=0.16)
    A(box((1500, yb0, zb), (1560, yb1, zb + 4), T('awning_red')))
    A(box((1500, yb0, zb + 4), (1560, yb1, zb + 36), T('popcorn')))
    A(hull([(1496, yb0, zb + 36), (1564, yb0, zb + 36), (1496, yb1, zb + 36), (1564, yb1, zb + 36), (1530, -1505, zb + 50)], T('awning_red')))
    for k, x in enumerate((1590, 1606, 1622)):
        mdl(f'pad_cups/pad_cup0{k + 1}.md3', x, -1508, zb, scale=0.12, angle=90)
    mdl('pad_ddmix/padship/rumbottle1.md3', 1690, -1505, zb, scale=0.14)
    mdl('pad_ddmix/diner/glass_sunrise.md3', 1730, -1505, zb, scale=0.13)
    mdl('pad_ddmix/diner/glass_midnight.md3', 1765, -1505, zb, scale=0.13)
    mdl('pad_ddmix/diner/muffin_blueberry.md3', 1805, -1505, zb, scale=0.16, angle=90)
    # menu boards on the back wall (fitted, readable from the room)
    for (x0, tex) in ((1328, 'menu_snacks'), (1480, 'menu_drinks'), (1632, 'menu_ice')):
        A(sign_box((x0, Y0 + 16, 108), (x0 + 136, Y0 + 19, 172), T(tex), 512, 256, back=T('wood_dark'), facing='n'))


def snack_shack():
    X0, Y0, X1, Y1, H = 1088, -1536, 1856, -1024, 176
    wt = T('stucco_coral')
    # walls: south solid, west door, north 2 doors + window openings, east solid
    A(box((X0, Y0, 0), (X1, Y0 + 16, H), wt))
    A(box((X1 - 16, Y0 + 16, 0), (X1, Y1 - 16, H), wt))
    A(box((X0, Y0 + 16, 0), (X0 + 16, -1344, H), wt)); A(box((X0, -1216, 0), (X0 + 16, Y1 - 16, H), wt))
    A(box((X0, -1344, 128), (X0 + 16, -1216, H), wt))
    # north wall: doors x 1216..1344 & 1600..1728, windows between (z 48..144)
    nx = [(X0, 1216), (1344, 1408), (1536, 1600), (1728, X1)]
    for a, b in nx: A(box((a, Y1 - 16, 0), (b, Y1, H), wt))
    for a, b in ((1216, 1344), (1600, 1728)): A(box((a, Y1 - 16, 128), (b, Y1, H), wt))
    A(box((1408, Y1 - 16, 0), (1536, Y1, 48), wt)); A(box((1408, Y1 - 16, 144), (1536, Y1, H), wt))
    # roof slab
    A(box((X0, Y0, H), (X1, Y1, H + 16), {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('stucco_white')}))
    zone((X0 + 16, Y0 + 16, X1 - 16, Y1 - 16), T('tile_white'))
    # counter + kitchen
    snack_bar(Y0, H)
    sign((1256, Y1, 140), (1576, Y1 + 8, 172), 'sign_snack', 'n')
    for (x, y) in ((1300, -1220), (1460, -1180), (1620, -1220), (1380, -1310), (1560, -1310)):
        table(x, y, 0)
        for a in range(0, 360, 90):
            stool(x + 44 * math.cos(math.radians(a)), y + 44 * math.sin(math.radians(a)), 0, 18, 9)
    for (mx, my, mname, s) in ((1300, -1220, 'pad_condiments/pad_ketchup', 0.18), (1316, -1206, 'pad_condiments/pad_mustard', 0.18),
                             (1460, -1180, 'pad_ddmix/diner/muffin_choco', 0.2), (1620, -1220, 'pad_cups/pad_cup03', 0.12),
                             (1560, -1310, 'pad_ddmix/diner/glass_diner', 0.25), (1380, -1310, 'pad_condiments/salt', 0.3)):
        mdl(mname + '.md3', mx, my, 30, scale=s, angle=int(mx) % 360)
    for x in range(1180, 1800, 160):
        A(box((x - 32, -1312, H - 8), (x + 32, -1248, H), T('lightpanel')))
    weapon('pumper', 1460, -1360, 0)
    item('ammo_nipper', 1700, -1464, 0)
    item('ammo_pumper', 1150, -1100, 0)
    M.ent('station_health', (1780, -1100, 0), angle=180)
    speaker(1450, -1490, 80, 'sound/world/machine/coffee_maker.ogg')
    # exterior stairs to the roof (east side)
    for b in stairs(1856, -1536, 1952, -1152, 0, H + 16, 'n', {'top': T('teak'), 'side': T('stucco_white')}): A(b)
    # roof terrace furniture
    for (x, y, u) in ((1250, -1400, 'umb_red'), (1450, -1200, 'umb_yellow'), (1650, -1420, 'umb_blue')):
        table(x, y, H + 16, umb=u)
    for x in range(1120, 1840, 96):
        A(box((x, Y0 + 4, H + 16), (x + 64, Y0 + 20, H + 40), {'top': GRASS, 'side': T('stucco_white')}))
    item('holdable_floater', 1780, -1100, H + 16)
    item('ammo_splasher', 1150, -1460, H + 16)
    spawn(1300, -1100, H + 16, 180)
    # outdoor picnic area north of the shack
    for (x, y, u) in ((1200, -880, 'umb_green'), (1440, -840, 'umb_red'), (1700, -880, 'umb_yellow')):
        table(x, y, 0, r=40, umb=u)
    spawn(1880, -900, 0, 180); spawn(1150, -1300, 0, 0)


def changing_rooms():
    X0, Y0, X1, Y1, H = -1856, -1536, -1088, -1024, 160
    wt = T('stucco_mint')
    # walls: north door x -1536..-1408, east door y -1344..-1216
    A(box((X0, Y0, 0), (X1, Y0 + 16, H), wt)); A(box((X0, Y0 + 16, 0), (X0 + 16, Y1, H), wt))
    A(box((X0 + 16, Y1 - 16, 0), (-1536, Y1, H), wt)); A(box((-1408, Y1 - 16, 0), (X1, Y1, H), wt))
    A(box((-1536, Y1 - 16, 128), (-1408, Y1, H), wt))
    A(box((X1 - 16, Y0 + 16, 0), (X1, -1344, H), wt)); A(box((X1 - 16, -1216, 0), (X1, Y1 - 16, H), wt))
    A(box((X1 - 16, -1344, 128), (X1, -1216, H), wt))
    A(box((X0, Y0, H), (X1, Y1, H + 16), {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('stucco_white')}))
    zone((X0 + 16, Y0 + 16, X1 - 16, Y1 - 16), T('tile_white'))
    # interior partitions: shower block (west), toilet stalls (south), lockers (north wall)
    A(box((-1600, Y0 + 16, 0), (-1584, -1280, 128), T('tile_aqua')))                   # shower partition
    for y in (-1440, -1360):
        A(box((X0 + 16, y - 4, 0), (-1680, y + 4, 112), T('tile_aqua')))               # shower stall walls
    for y in (-1480, -1400, -1320):
        A(box((X0 + 20, y - 2, 124), (X0 + 60, y + 2, 128), T('metal')))
        A(box((X0 + 40, y - 20, 0), (X0 + 42, y + 20, 120), T('spray')))
    speaker(-1780, -1400, 80, 'sound/world/ambient/water_shower.ogg')
    for x in (-1440, -1344, -1248):
        A(box((x - 4, Y0 + 16, 0), (x + 4, -1408, 112), T('stucco_white')))                # toilet stall walls
    for x in (-1392, -1296, -1200):
        mdl('pad_train/ttoilet.md3', x, -1480, 0, scale=0.11, angle=90)
    A(box((-1408, Y1 - 48, 0), (-1104, Y1 - 16, 112), T('locker')))
    A(box((-1840, Y1 - 48, 0), (-1600, Y1 - 16, 112), T('locker')))
    A(box((-1500, -1300, 0), (-1220, -1268, 18), T('teak')))                            # bench
    for (x, y) in ((-1400, -1284), (-1300, -1284)):
        mdl('pad_items/towelstack.md3', x, y, 18, scale=0.4, angle=0)
    for x in range(-1760, -1150, 160):
        A(box((x - 32, -1312, H - 8), (x + 32, -1248, H), T('lightpanel')))
    sign((-1700, Y1, 112), (-1380, Y1 + 8, 144), 'sign_change', 'n')
    weapon('balloony', -1300, -1150, 0)
    item('ammo_balloony', -1750, -1100, 0)
    M.ent('station_health', (-1700, -1180, 0), angle=0)
    # roof: stairs on west side, loungers
    for b in stairs(-1952, -1536, -1856, -1184, 0, H + 16, 'n', {'top': T('teak'), 'side': T('stucco_white')}): A(b)
    for i, x in enumerate(range(-1760, -1150, 110)):
        lounger(x, -1150, H + 16, 270)
    umbrella(-1500, -1400, H + 16, 'umb_green'); umbrella(-1260, -1420, H + 16, 'umb_yellow')
    item('holdable_bambam', -1700, -1460, H + 16)
    item('ammo_boaster', -1150, -1480, H + 16)
    spawn(-1450, -1450, H + 16, 90)
    spawn(-1250, -1350, 0, 180)


def plaza():
    # ---- statue fountain at (0,-1088): 16-sided basin, ring wall 16 high, water 12 deep
    cx, cy, R0, R1 = 0, -1088, 192, 208
    n = 16
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        pts = [(cx + rr * math.cos(a), cy + rr * math.sin(a), z) for a in (a0, a1) for rr in (R0, R1) for z in (0, 16)]
        A(hull(pts, {'top': T('coping'), 'side': T('tile_aqua')}))
        wp = [(cx + rr * math.cos(a), cy + rr * math.sin(a), z) for a in (a0, a1) for rr in (58, R0) for z in (0, 12)]
        A(hull(wp, T('water_pool')))
    A(cyl(cx, cy, 56, 0, 72, {'top': T('coping'), 'side': WALLB}, 16))
    # spinning gold Padman (func_rotating with a model2; idea from the hand-edited v1 map)
    M.ent('func_rotating', (cx, cy, 72), brushes=[box((cx - 8, cy - 8, 72), (cx + 8, cy + 8, 88), T('nodraw_ns'))],
          model2='models/mapobjects/ente/padstatue_gold.md3', speed=30)
    clipbox((cx - 44, cy - 44, 72), (cx + 44, cy + 44, 300))
    light(cx, cy - 150, 330, 260, '1 0.85 0.5')
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        px, py = cx + 120 * math.cos(a), cy + 120 * math.sin(a)
        A(hull([(px - 6, py - 6, 0), (px + 6, py + 6, 0), (px - 6, py + 6, 0), (px + 6, py - 6, 0), (px, py, 110)], T('spray_up'), round_pts=False))
    weapon('pumper', 0, -1240, 0)
    speaker(cx, cy, 60, 'sound/world/ambient/water_bubbling.ogg')
    # ---- gondola station
    for (a, b) in ((-384, -128), (128, 384)):
        for (px, py) in ((a, -1760), (b - 24, -1760), (a, -1592), (b - 24, -1592)):
            A(box((px, py, 0), (px + 24, py + 24, 208), T('metal_white')))
        A(box((a, -1760, 208), (b, -1568, 224), {'top': T('deck'), 'side': T('trim_wave'), 'bot': T('metal_white')}))
    st = {'top': T('teak'), 'side': T('stucco_white')}
    for b in stairs(-832, -1760, -384, -1664, 0, 224, 'e', st): A(b)
    for b in stairs(384, -1760, 832, -1664, 0, 224, 'w', st): A(b)
    # cabin (sits on the platform), door north
    gx0, gy0, gx1, gy1 = -96, -1728, 96, -1600
    ct = {'side': T('stucco_sun'), 'top': T('metal_white'), 'bot': T('metal_white')}
    A(box((gx0, gy0, 0), (gx1, gy0 + 8, 56), ct)); A(box((gx0, gy0, 104), (gx1, gy0 + 8, 128), ct))
    A(box((gx0, gy0, 56), (-64, gy0 + 8, 104), ct)); A(box((64, gy0, 56), (gx1, gy0 + 8, 104), ct))
    for (wx0, wx1) in ((gx0, gx0 + 8), (gx1 - 8, gx1)):
        A(box((wx0, gy0 + 8, 0), (wx1, gy1, 56), ct)); A(box((wx0, gy0 + 8, 104), (wx1, gy1, 128), ct))
        A(box((wx0, gy0 + 8, 56), (wx1, -1696, 104), ct)); A(box((wx0, -1632, 56), (wx1, gy1, 104), ct))
    light(0, -1664, 100, 220, '1 0.95 0.8')
    A(box((gx0 + 8, gy1 - 8, 0), (-40, gy1, 128), ct)); A(box((40, gy1 - 8, 0), (gx1 - 8, gy1, 128), ct))
    A(box((-40, gy1 - 8, 104), (40, gy1, 128), ct))
    A(box((gx0, gy0, 128), (gx1, gy1, 144), {'top': T('metal'), 'side': T('metal_white'), 'bot': T('metal_white')}))
    A(box((gx0 + 8, gy0 + 8, 0), (gx1 - 8, gy0 + 40, 20), T('teak')))                   # bench
    A(box((-8, -1672, 144), (8, -1656, 300), T('metal_dark')))                              # hanger
    A(box((-24, -1680, 300), (24, -1648, 320), T('metal_dark')))
    for dx in (-20, 20):
        A(box((dx - 2, -2900, 312), (dx + 2, -1680, 316), T('cable')))
        A(box((dx - 2, -1648, 312), (dx + 2, -1560, 316), T('cable')))
    A(cyl(0, -1540, 40, 300, 330, T('metal_dark'), 12))                                    # bull wheel
    A(box((-12, -1552, 224), (12, -1528, 300), T('metal_dark')))
    sign((-64, -1600, 104), (64, -1592, 128), 'sign_gondola', 'n')
    item('ammo_splasher', 60, -1700, 144)
    item('item_armor_padshield', 0, -1690, 20)        # (item_berserker crashes WoP servers on pickup)
    item('ammo_pumper', -256, -1660, 224)
    item('ammo_balloony', 256, -1660, 224)
    # ---- ticket gate: canopy on posts + 4 booths with turnstile gaps
    A(box((-640, -1472, 144), (640, -1376, 160), {'top': T('deck'), 'side': T('awning'), 'bot': T('metal_white')}))
    for x in (-640, -24, 616):
        A(box((x, -1440, 0), (x + 24, -1416, 144), T('metal_white')))
    for i, bx in enumerate((-448, -192, 192, 448)):
        bt = {'side': T('stucco_white'), 'top': T('stucco_white')}
        A(box((bx - 64, -1464, 0), (bx + 64, -1456, 40), bt)); A(box((bx - 64, -1464, 104), (bx + 64, -1456, 144), bt))
        A(box((bx - 64, -1464, 40), (bx - 48, -1456, 104), bt)); A(box((bx + 48, -1464, 40), (bx + 64, -1456, 104), bt))
        A(box((bx - 64, -1392, 0), (bx - 16, -1384, 144), bt)); A(box((bx + 16, -1392, 0), (bx + 64, -1384, 144), bt))
        A(box((bx - 16, -1392, 112), (bx + 16, -1384, 144), bt))
        A(box((bx - 64, -1456, 0), (bx - 56, -1392, 144), bt)); A(box((bx + 56, -1456, 0), (bx + 64, -1392, 144), bt))
        A(box((bx - 56, -1456, 40), (bx + 56, -1440, 48), T('teak')))
        sign((bx - 48, -1472, 104), (bx + 48, -1464, 128), 'sign_tickets', 's')
        mdl('pad_pc/padshop_tft.md3', bx, -1446, 48, scale=0.12, angle=90)
    for (x, h) in ((672, 144), (736, 128), (800, 96), (864, 64), (928, 32)):
        A(box((x - 32, -1456, 0), (x + 32, -1392, h), T('crate')))
    item('ammo_nipper', -320, -1424, 0)
    item('item_armor_shard', 400, -1440, 160)
    # big SPLASH WORLD arch sign on the gate canopy
    sign((-256, -1424, 160), (256, -1416, 288), 'sign_splash', 'ns', 1024, 256)
    # plaza decoration
    mdl('pad_ddmix/padshop/cardboard_standup.md3', -300, -900, 0, scale=0.28, angle=270)
    for (px, py, s) in ((-760, -900, 11), (760, -900, 12), (-760, -1300, 13), (760, -1300, 14), (-420, -1000, 15), (420, -1000, 16)):
        planter(px - 48, py - 48, px + 48, py + 48)
        palm(px, py, 12, h=230 + (s % 3) * 20, lean=((s % 5) * 6 - 12, 10 - (s % 4) * 5), seed=s)
        flowers(px, py, 12, seed=s, r=32)
    for (x, y) in ((-200, -820), (200, -820)):
        A(box((x - 64, y - 16, 0), (x + 64, y + 16, 18), T('teak')))
    spawn(-500, -1320, 0, 90); spawn(500, -1320, 0, 90); spawn(0, -1550, 0, 90); spawn(-900, -900, 0, 45)


def center_island(TW):
    X0, Y0, X1, Y1, H = TW
    # jump pad to the tower roof from NE corner of the center island
    jumppad(416, 720, 0, (176, 440, H), apex_extra=60)
    for (px, py, s) in ((480, -360, 22), (-500, 200, 23), (360, 160, 24)):
        planter(px - 40, py - 40, px + 40, py + 40)
        palm(px, py, 12, h=240, lean=(14, -12), seed=s)
        flowers(px, py, 12, seed=s)
    post_sign(-570, -40, 'sign_tornado', 'e', w=128, h=32)
    item('item_armor_padshield', -120, -320, 0)
    item('ammo_bubbleg', 300, -320, 0)
    item('ammo_balloony', -520, 440, 0)
    spawn(-420, 480, 0, 0); spawn(300, 780, 0, 270); spawn(400, -60, 0, 90)


def scatter_east_west():
    # NW lounge between dive zone and terrace stairs
    # deck palms along walkways
    for (px, py, s) in ((-960, -700, 31), (-960, 760, 32), (960, -700, 33), (960, 760, 34), (-1300, 980, 35),
                        (900, 1120, 36), (-900, 1120, 37), (-1980, 920, 38), (1990, -700, 39)):
        planter(px - 40, py - 40, px + 40, py + 40)
        palm(px, py, 12, h=230, lean=(10, 10), seed=s)
        flowers(px, py, 12, seed=s)
    # lifeguard stands
    def stand(x, y, face):
        for (dx, dy) in ((-24, -24), (16, -24), (-24, 16), (16, 16)):
            A(box((x + dx, y + dy, 0), (x + dx + 8, y + dy + 8, 96), T('wood_white')))
        A(box((x - 32, y - 32, 96), (x + 32, y + 32, 104), {'top': T('teak'), 'side': T('wood_white')}))
        A(box((x - 32, y - 32, 160), (x + 32, y + 32, 166), T('awning_red')))
        for (dx, dy) in ((-30, -30), (26, -30), (-30, 26), (26, 26)):
            A(box((x + dx, y + dy, 104), (x + dx + 4, y + dy + 4, 160), T('wood_white')))
        # steps on the back (guard faces `face`)
        for k in range(6):
            if face == 'w': xa = x + 32 + 16 * (5 - k)
            else: xa = x - 48 - 16 * (5 - k)
            A(box((xa, y - 16, 0), (xa + 16, y + 16, 16 * (k + 1)), T('wood_white')))
    stand(-1000, 200, 'w'); stand(1060, 1040, 'e')
    item('item_armor_shard', -1000, 200, 104); item('item_armor_shard', 1060, 1040, 104)
    # extra spawns
    spawn(-1950, -620, 0, 0); spawn(-1020, 880, 0, 270); spawn(-1700, 1700, 0, 270)
    spawn(-1450, -620, 0, 90); spawn(1100, -620, 0, 90); spawn(-650, 1120, 0, 0)
    # ammo & items around
    item('ammo_nipper', -1960, -240, 0); item('ammo_nipper', 1990, -300, 0)
    item('ammo_pumper', -1180, 1640, 0)
    item('ammo_balloony', 1120, 1660, 0)
    item('ammo_bubbleg', -1990, 1500, 0)
    item('ammo_boaster', -880, 0, 0)
    item('ammo_betty', 1990, 200, 0); item('ammo_betty', -1990, 1100, 0)
    item('ammo_pumper', -880, -620, 0)
    item('item_armor_shard', 1990, -1600, 0); item('item_armor_shard', -1990, -1700, 0)
    item('item_armor_shard', 0, 1100, 0); item('item_armor_shard', -1400, 950, 0)


def flowers(px, py, z, seed=0, n=3, r=28):
    """small flowering plants around a palm in a planter"""
    kinds = [('pad_ddmix/plants/flower_pink.md3', 0.13), ('pad_ddmix/plants/flower_yellow.md3', 0.1),
             ('pad_ddmix/plants/fern.md3', 0.045), ('pad_ddmix/trashcan/grass.md3', 0.2)]
    for k in range(n):
        a = math.radians(45 + 90 * k + seed * 13)
        m, sc = kinds[(seed + k) % len(kinds)]
        mdl(m, px + r * math.cos(a), py + r * math.sin(a), z, scale=sc, angle=(seed * 50 + k * 90) % 360)
    return


def cabana(x0, y0, x1, y1, crates_side):
    for (px, py) in ((x0, y0), (x1 - 8, y0), (x0, y1 - 8), (x1 - 8, y1 - 8)):
        A(box((px, py, 0), (px + 8, py + 8, 96), T('bamboo')))
    A(box((x0 - 8, y0 - 8, 96), (x1 + 8, y1 + 8, 104), {'top': T('thatch'), 'side': T('thatch'), 'bot': T('bamboo')}))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    lounger(cx - 30, cy, 0, 270); lounger(cx + 30, cy, 0, 270)
    mdl('pad_items/towelstack.md3', cx - 30, cy + 7, 12, scale=0.3)
    yy0, yy1 = (y0 + y1) / 2 - 24, (y0 + y1) / 2 + 24
    if crates_side == 'w':
        for k, h in enumerate((96, 64, 32)):
            A(box((x0 - 8 - 48 * (k + 1), yy0, 0), (x0 - 8 - 48 * k, yy1, h), T('crate')))
    else:
        for k, h in enumerate((96, 64, 32)):
            A(box((x1 + 8 + 48 * k, yy0, 0), (x1 + 8 + 48 * (k + 1), yy1, h), T('crate')))


def extras():
    # ---------- lifeguard HQ on the center island (SE): enterable, roof via west stairs
    X0, Y0, X1, Y1, H = 160, -400, 416, -240, 112
    wt = T('stucco_white')
    A(box((X0, Y0, 0), (X1, Y0 + 16, H), wt))                                       # south
    A(box((X0, Y1 - 16, 0), (256, Y1, H), wt)); A(box((320, Y1 - 16, 0), (X1, Y1, H), wt)); A(box((256, Y1 - 16, 96), (320, Y1, H), wt))
    A(box((X1 - 16, Y0 + 16, 0), (X1, Y1 - 16, H), wt))                             # east
    A(box((X0, Y0 + 16, 0), (X0 + 16, -352, H), wt)); A(box((X0, -288, 0), (X0 + 16, Y1 - 16, H), wt))   # west w/ window
    A(box((X0, -352, 0), (X0 + 16, -288, 48), wt)); A(box((X0, -352, 96), (X0 + 16, -288, H), wt))
    A(box((X0, Y0, H), (X1, Y1, H + 16), {'top': T('deck'), 'side': T('awning_red'), 'bot': T('stucco_white')}))
    zone((X0 + 16, Y0 + 16, X1 - 16, Y1 - 16), T('tile_white'))
    sign((224, Y1, 100), (352, Y1 + 8, 124), 'sign_lifeguard', 'n') if False else None
    for b in stairs(64, -400, 160, -144, 0, H + 16, 's', {'top': T('teak'), 'side': T('stucco_white')}): A(b)
    A(box((X1 - 64, Y0 + 16, 0), (X1 - 16, Y0 + 112, 18), T('teak')))                 # bench
    mdl('pad_ddmix/backyard/tire.md3', 200, -368, 0, scale=0.14, angle=0)
    mdl('pad_ddmix/backyard/tire.md3', 240, -368, 0, scale=0.14, angle=0)
    mdl('pad_westernset/directors_chair.md3', 300, -330, 0, scale=0.25, angle=90)
    item('item_armor_shard', 220, -300, 0)
    item('ammo_boaster', 300, -300, H + 16)
    light(288, -320, 90, 220)
    # ---------- tiki hut (center NW) with crate steps to its roof
    for (px, py) in ((-544, 600), (-396, 600), (-544, 748), (-396, 748)):
        A(box((px, py, 0), (px + 12, py + 12, 120), T('bamboo')))
    A(box((-560, 584, 120), (-368, 776, 132), {'top': T('thatch'), 'side': T('thatch'), 'bot': T('bamboo')}))
    A(box((-528, 616, 0), (-412, 640, 40), {'top': T('teak'), 'side': T('bamboo')}))
    for k, h in enumerate((128, 96, 64, 32)):
        A(box((-368 + 48 * k, 652, 0), (-368 + 48 * (k + 1), 700, h), T('crate')))
    for i, (mx, mn) in enumerate(((-500, 'pad_ddmix/diner/glass_sunrise'), (-470, 'pad_ddmix/diner/glass_betty'),
                                  (-440, 'pad_ddmix/padship/rumbottle2'))):
        mdl(mn + '.md3', mx, 628, 40, scale=0.12, angle=i * 70)
    item('item_armor_shard', -470, 700, 0)
    light(-470, 690, 100, 200, '1 0.8 0.5')
    # ---------- cabanas on the south bank
    cabana(-640, -880, -480, -768, 'w'); cabana(400, -880, 560, -768, 'e')
    # ---------- giant lawn chess (deck strip west of the river)
    zone((-1056, -608, -800, -352), T('checker'))
    for (cx, cy, m, a) in ((-1024, -576, 'chess_white_tower', 0), (-896, -576, 'chess_white_king', 90),
                           (-960, -448, 'chess_white_dame', 0), (-832, -384, 'chess_black_king', 270),
                           (-1024, -384, 'chess_black_tower', 0), (-832, -512, 'chess_black_dame', 180)):
        mdl(f'pad_ddmix/chess/{m}.md3', cx, cy, 0, scale=1.4, angle=a)
        clipbox((cx - 22, cy - 22, 0), (cx + 22, cy + 22, 64))
    # ---------- hedges on the north strip
    for (hx, hy) in ((-120, 1150), (420, 1150), (700, 1150)):
        A(box((hx - 60, hy - 28, 0), (hx + 60, hy + 28, 24), {'top': GRASS, 'side': T('coping')}))
        mdl('pad_ddmix/trashcan/bush.md3', hx, hy, 24, scale=0.3, angle=0)
    # ---------- ice cream cart (plaza)
    A(box((544, -1040, 16), (624, -992, 56), {'top': T('metal_white'), 'side': T('stucco_sun')}))
    for (wx, wy) in ((548, -1036), (612, -1036), (548, -1004), (612, -1004)):
        A(box((wx, wy, 0), (wx + 8, wy + 8, 16), T('rubber')))
    umbrella(584, -1016, 56, 'umb_red', h=72, r=48)
    mdl('pad_ddmix/diner/muffin_blueberry.md3', 600, -1016, 56, scale=0.15)
    # ---------- shade trees in the plaza
    for (tx, ty) in ((-560, -1180), (560, -1180)):
        A(cyl(tx, ty, 96, 0, 12, {'top': GRASS, 'side': T('coping')}, 12))
        mdl('pad_ddmix/trashcan/tree_summer.md3', tx, ty, 12, scale=0.5, angle=tx % 360)
        clipbox((tx - 12, ty - 22, 12), (tx + 12, ty + 2, 120))
    # ---------- extra mushrooms in the splash zone
    for (mx, my) in ((1340, 120), (1700, -60)):
        A(cyl(mx, my, 18, -16, 104, T('stucco_white'), 10))
        A(cyl(mx, my, 92, 104, 120, {'top': T('mushroom'), 'side': T('mushroom'), 'bot': T('stucco_white')}, 16))
        A(hull(tri_pts(mx, my, 60, 12, 120, 120) + [(mx, my, 150)], T('mushroom')))
        for k in range(8):
            a = k * math.pi / 4 + 0.2
            px, py = mx + 96 * math.cos(a), my + 96 * math.sin(a)
            nx, ny = -math.sin(a) * 30, math.cos(a) * 30
            A(hull([(px - nx, py - ny, -16), (px + nx, py + ny, -16), (px - nx, py - ny, 104), (px + nx, py + ny, 104),
                    (px - nx + math.cos(a), py - ny + math.sin(a), -16), (px + nx + math.cos(a), py + ny + math.sin(a), 104)],
                   T('spray'), round_pts=False))
    # ---------- rotating sprinkler (func_rotating) in the splash zone
    SX, SY = 1480, -330
    A(cyl(SX, SY, 8, -16, 100, T('metal_white'), 8))
    arm = [box((SX - 4, SY - 4, 100), (SX + 4, SY + 4, 106), 'common/origin'),
           box((SX - 80, SY - 4, 100), (SX + 80, SY + 4, 106), T('metal')),
           box((SX - 82, SY - 2, -10), (SX - 78, SY + 2, 100), T('spray')), box((SX + 78, SY - 2, -10), (SX + 82, SY + 2, 100), T('spray'))]
    M.ent('func_rotating', brushes=arm,              # origin comes from the origin brush only
          speed=60, noise='sound/world/ambient/water_shower.ogg')
    # ---------- tower roof raven (animated WoP model, entity)
    M.ent('misc_externalmodel', (224, 548, 512), model='models/mapobjects/animated/raven_sitting_2_small.md3',
          angle=45, animationStart=0, animationEnd=210, animationFPS=30)
    # ---------- decoration: ducks, sunbathing gummy bears, beach toys, towels
    for (dx, dy, dz, a) in ((-1072, -300, 0, 180), (-1072, 420, 0, 180), (-1136, 1300, 0, 180), (1136, -300, 0, 0),
                            (1808, 40, 0, 180), (300, 1488, 192, 90), (-600, 1488, 192, 90), (60, -860, 0, 270),
                            (-1560, 1520, 0, 270), (720, 980, 0, 0)):
        mdl('ente/ducka.md3' if dx % 2 else 'ente/duckb.md3', dx, dy, dz, scale=0.7, angle=a)
    for (bx, by, c, a) in ((-1950, -650, 'ldredbear', 0), (1450, 1700, 'ldgreenbear', 20), (1810, 1640, 'ldyellowbear', 160),
                           (-1880, 1640, 'ldorangebear', 80)):
        mdl(f'gummybears/{c}.md3', bx, by, 0, scale=0.4, angle=a)
    for (bx, by, m) in ((-1900, 300, 'pad_basketball'), (-1900, -110, 'pad_soccerball'), (1450, 1600, 'pad_tennisball'),
                        (-700, -1500, 'pad_soccerball'), (1000, 200, 'pad_basketball')):
        mdl(f'pad_ball/{m}.md3', bx, by, 0, scale=0.35 if 'tennis' not in m else 1.2)
    for y in (-560, -304, -48, 208):
        mdl('pad_items/towelstack.md3', -1967, y, 12, scale=0.3, angle=90)
    # cocktails and towels on the infinity terrace, garbage bags by the snack shack
    mdl('pad_ddmix/trashcan/garbage_bag_group.md3', 1880, -1600, 0, scale=0.5)
    mdl('pad_ddmix/trashcan/garbage_bag_standing.md3', 1040, -1560, 0, scale=0.5)
    mdl('pad_ddmix/padshop/cardboard_standup.md3', 380, 620, 0, scale=0.26, angle=200)
    mdl('pad_actionfigures/fig_lilly.md3', 1290, 420, 128, scale=0.45, angle=270)
    mdl('pad_actionfigures/fig_girl.md3', 1660, 420, 128, scale=0.45, angle=270)
    mdl('pad_statues/statue_super.md3', -1440, 1660, 0, scale=0.3, angle=270)
    mdl('pad_ddmix/castle/sword.md3', 390, 190, -192, scale=0.7, angle=30)
    mdl('pad_ddmix/door/ancient_key_lying.md3', 470, 470, -160, scale=0.3, angle=10)
    for (sx, sy) in ((-1500, -1060), (-1820, -1060)):
        pass
    for x in (-1240, -1180, -1120):
        mdl('pad_sink/sink.md3', x, -1050, 0, scale=0.28, angle=270) if False else None


def beach_hut(x0, y0, x1, y1, door, crates, z=0):
    """small enterable hut (walls 8, roof 96..112) with a crate staircase to the roof, standing on z"""
    h = 96; wt = {'side': T('wood_white'), 'top': T('wood_white')}
    def bx(mn, mx, tex): A(box((mn[0], mn[1], mn[2] + z), (mx[0], mx[1], mx[2] + z), tex))
    xm, ym = (x0 + x1) // 2, (y0 + y1) // 2
    for side, (a0, b0, a1, b1) in (('s', (x0, y0, x1, y0 + 8)), ('n', (x0, y1 - 8, x1, y1)),
                                   ('w', (x0, y0 + 8, x0 + 8, y1 - 8)), ('e', (x1 - 8, y0 + 8, x1, y1 - 8))):
        if side == door:
            if side in 'ns':
                bx((a0, b0, 0), (xm - 32, b1, h), wt); bx((xm + 32, b0, 0), (a1, b1, h), wt)
                bx((xm - 32, b0, 80), (xm + 32, b1, h), wt)
            else:
                bx((a0, b0, 0), (a1, ym - 32, h), wt); bx((a0, ym + 32, 0), (a1, b1, h), wt)
                bx((a0, ym - 32, 80), (a1, ym + 32, h), wt)
        else:
            bx((a0, b0, 0), (a1, b1, h), wt)
    bx((x0 - 8, y0 - 8, h), (x1 + 8, y1 + 8, h + 16), {'top': T('thatch'), 'side': T('thatch'), 'bot': T('wood_white')})
    if z == 0:
        zone((x0 + 8, y0 + 8, x1 - 8, y1 - 8), T('teak'))
    cx, cy, dx, dy = crates
    for k, top in enumerate((96, 64, 32)):
        bx((cx + dx * 48 * k - 24, cy + dy * 48 * k - 24, 0), (cx + dx * 48 * k + 24, cy + dy * 48 * k + 24, top), T('crate'))
    light(xm, ym, z + 70, 140)


def blockers():
    # hedges between the plaza and the side buildings
    for (hx, hy) in ((-940, -960), (940, -960)):
        A(box((hx - 100, hy - 28, 0), (hx + 100, hy + 28, 24), {'top': GRASS, 'side': T('coping')}))
        mdl('pad_ddmix/trashcan/bush.md3', hx - 46, hy, 24, scale=0.28, angle=0)
        mdl('pad_ddmix/trashcan/bush.md3', hx + 50, hy, 24, scale=0.26, angle=180)
    # outdoor showers (post + head + spray) on the north deck
    for (sx, sy) in ((-900, 960), (880, 940)):
        A(box((sx - 24, sy - 24, 0), (sx + 24, sy + 24, 8), T('tile_aqua')))
        A(box((sx - 6, sy - 6, 8), (sx + 6, sy + 6, 120), T('metal_white')))
        A(box((sx - 6, sy - 40, 112), (sx + 6, sy - 6, 120), T('metal_white')))
        A(box((sx - 10, sy - 36, 8), (sx + 10, sy - 32, 112), T('spray')))
        speaker(sx, sy - 30, 60, 'sound/world/ambient/water_shower.ogg')
    # beach huts on the west sand and the east edge
    beach_hut(-2032, 600, -1904, 728, 'e', (-1936, 760, 0, 1))
    beach_hut(1912, 272, 2040, 400, 'w', (1888, 240, -1, 0))
    item('ammo_nipper', -1968, 664, 0)
    item('item_armor_shard', 1976, 336, 112)
    # towel kiosks on the north deck strip
    for (kx, ky) in ((-420, 1076), (320, 1076)):
        A(box((kx - 40, ky - 24, 0), (kx + 40, ky + 24, 72), {'side': T('towel_b'), 'top': T('wood_white')}))
        mdl('pad_items/towelstack.md3', kx - 14, ky, 72, scale=0.35, angle=0)
        mdl('pad_items/towelroll.md3', kx + 22, ky, 72, scale=0.4, angle=90)
    # duck statue in the splash zone (fits under the mushroom caps)
    mdl('pad_ducks/pad_duck.md3', 1500, -100, -16, scale=0.45, angle=210)
    clipbox((1474, -140, -16), (1526, -60, 72))


def window_panel(face, c, wall, z0=40, z1=104, w=56, awn='awning'):
    """fake window (2u panel with fitted window texture) + small striped awning on an exterior wall.
    face: 'n','s','e','w' = direction the wall faces; c = centre along the wall; wall = wall plane coordinate"""
    hw = w // 2
    if face in 'ns':
        sgn = 1 if face == 'n' else -1
        y0, y1 = (wall, wall + 2) if sgn > 0 else (wall - 2, wall)
        A(sign_box((c - hw, y0, z0), (c + hw, y1, z1), T('window'), 256, 256, back=T('metal_white'), facing=face))
        yo = wall + sgn * 26
        A(hull([(c - hw - 6, wall, z1 + 18), (c + hw + 6, wall, z1 + 18), (c - hw - 6, wall, z1 + 22), (c + hw + 6, wall, z1 + 22),
                (c - hw - 6, yo, z1 + 4), (c + hw + 6, yo, z1 + 4), (c - hw - 6, yo, z1 + 8), (c + hw + 6, yo, z1 + 8)], T(awn)))
    else:
        sgn = 1 if face == 'e' else -1
        x0, x1 = (wall, wall + 2) if sgn > 0 else (wall - 2, wall)
        A(sign_box((x0, c - hw, z0), (x1, c + hw, z1), T('window'), 256, 256, back=T('metal_white'), facing=face))
        xo = wall + sgn * 26
        A(hull([(wall, c - hw - 6, z1 + 18), (wall, c + hw + 6, z1 + 18), (wall, c - hw - 6, z1 + 22), (wall, c + hw + 6, z1 + 22),
                (xo, c - hw - 6, z1 + 4), (xo, c + hw + 6, z1 + 4), (xo, c - hw - 6, z1 + 8), (xo, c + hw + 6, z1 + 8)], T(awn)))


def facades():
    for x in (-1760, -1600, -1440, -1280, -1160):
        window_panel('s', x, -1536)
    for x in (-1780, -1300, -1180):
        window_panel('n', x, -1024)
    for y in (-1460, -1110):
        window_panel('e', y, -1088)
    for x in (1200, 1360, 1520, 1680):
        window_panel('s', x, -1536, awn='awning_red')
    for y in (-1460, -1110):
        window_panel('w', y, 1088, awn='awning_red')
    for x in (230, 345):
        window_panel('s', x, -400, z0=36, z1=84)
    window_panel('e', -320, 416, z0=36, z1=84)
    # tower: aqua skirting (skips the doors) + wave band
    sk = {'side': T('tile_aqua'), 'top': T('coping')}
    A(box((-256, 62, 0), (256, 64, 40), sk))
    for (a, b) in ((64, 256), (384, 576)):
        A(box((-258, a, 0), (-256, b, 40), sk)); A(box((256, a, 0), (258, b, 40), sk))
    for (a, b) in ((-256, -64), (64, 256)):
        A(box((a, 576, 0), (b, 578, 40), sk))
    bd = {'side': T('trim_wave'), 'top': T('coping'), 'bot': T('coping')}
    A(box((-258, 60, 232), (258, 64, 264), bd)); A(box((-258, 576, 232), (258, 580, 264), bd))
    A(box((-258, 64, 232), (-254, 576, 264), bd)) if False else None
    A(box((-260, 64, 232), (-256, 576, 264), bd)); A(box((256, 64, 232), (260, 576, 264), bd))


# =================================================================================================== DELUXE (v3)
def mover_model(cls, model, x, y, z, length=8, **kw):
    """brush mover that only shows a model2 (invisible, nonsolid brush hanging `length` below the origin).
    func_pendulum: swing period comes from `length` (Q3: f = sqrt(g / (3 * length)) / 2pi), `speed` = swing degrees.
    (func_bobbing would also work, but bspc turns every func_bobbing into a bot 'funcbob' ride, even nonsolid ones.)"""
    return M.ent(cls, (x, y, z), brushes=[box((x - 8, y - 8, z - length), (x + 8, y + 8, z + 8), T('nodraw_ns'))],
                 model2='models/mapobjects/' + model, **kw)


def floaties():
    """rocking ducks / beach balls on the water and wiggling fish under it (idea from the hand-edited v1 map)"""
    D, DB, SB, BB = 'ente/ducka.md3', 'ente/duckb.md3', 'pad_ball/pad_soccerball.md3', 'pad_ball/pad_basketball.md3'
    surf = {D: -14, DB: -12, SB: -46, BB: -50}          # origin offsets so they float half in the water (surface -8)
    for i, (m, x, y, wz) in enumerate((
            (SB, -1250, -60, 0), (BB, -1700, 520, 0), (D, -1250, 380, 0), (DB, -1600, -200, 0), (D, -1180, 560, 0),   # wave pool
            (D, -672, -400, 0), (DB, 672, 420, 0), (D, 120, 930, 0), (DB, -380, -560, 0), (D, -672, 300, 0),        # lazy river
            (SB, 1250, 1100, 8), (D, 1800, 950, 0), (DB, 1760, 1450, 0), (BB, 1300, 1450, 12),                         # lagoon
            (SB, -1250, 1300, 0), (D, -1480, 1160, 0),                                                                 # dive pool
            (D, -200, 1650, 192), (BB, 200, 1600, 192))):                                                               # infinity pool
        mover_model('func_pendulum', m, x, y, wz + surf[m], length=48 + 16 * (i % 4), speed=5 + i % 4,
                    phase=round((i * 0.137) % 1, 3), angle=(i * 47) % 360)
    fish = ['pad_fish/flame_angel.md3', 'pad_fish/flame_angel02.md3', 'pad_fish/flame_angel05.md3',
            'pad_fish/flame_angel_r.md3', 'pad_fish/flame_angel_r02.md3', 'pad_fish/flame_angel_r05.md3']
    for i, (x, y, z) in enumerate(((-1450, 1200, -260), (-1300, 1400, -200), (-1500, 1420, -320), (-1350, 1250, -150),
                                   (-1200, 400, -122), (-1600, 300, -122))):
        mover_model('func_pendulum', fish[i % 6], x, y, z, length=24, speed=10, phase=round(i / 6, 3), angle=(i * 70) % 360)


def ravens():
    for (x, y, z, a) in ((-1700, 780, 160, 300), (240, -360, 128, 20), (1300, -1080, 192, 180), (-260, -1700, 224, 0),
                         (-1820, -1060, 176, 250)):
        M.ent('misc_externalmodel', (x, y, z), model='models/mapobjects/animated/raven_sitting_2_small.md3', angle=a,
              animationStart=0, animationEnd=210, animationFPS=30)


def booster(mn, mx, pitch, yaw, speed, name, wait=0.5):
    """trigger_multiple -> target_push: sets the player's velocity (pitch > 0 = downward)"""
    M.ent('trigger_multiple', brushes=[box(mn, mx, TRIG)], target=name, wait=wait)
    M.ent('target_push', ((mn[0] + mx[0]) // 2, (mn[1] + mx[1]) // 2, mx[2] + 8), targetname=name,
          angles=f'{pitch} {yaw} 0', speed=speed)


def rapids():
    # slide launchers on the tower roof
    booster((-300, 280, 512), (-236, 360, 580), 20, 180, 820, 'boost_kamikaze')
    booster((112, 576, 512), (208, 640, 580), 8, 90, 560, 'boost_rapids')
    # river jets: south leg flows east, east leg north, north leg west, west leg south
    for (mn, mx, yaw, nm) in (((-296, -624, -48), (-120, -464, 8), 0, 'jet_s'), ((592, 330, -48), (752, 560, 8), 90, 'jet_e'),
                              ((60, 848, -48), (380, 1008, 8), 180, 'jet_n'), ((-752, 120, -48), (-592, 440, 8), 270, 'jet_w')):
        booster(mn, mx, 0, yaw, 380, nm, wait=0.25)
        A(box((mn[0], mn[1], -10), (mx[0], mx[1], -9), T('foam')))
        speaker((mn[0] + mx[0]) // 2, (mn[1] + mx[1]) // 2, 0, 'sound/world/ambient/water_bubbling.ogg')
    post_sign(-240, -688, 'sign_rapids_jet', 's', w=128, h=32)


def sky_cannon_and_isle():
    """jump pad on the east beach that fires you across the sky to Paradise Isle (teleporter back)"""
    CX, CY, ZT, R = 2880, 1440, 320, 300
    jumppad(1984, 1440, 0, (2860, 1440, ZT), apex_extra=140, name='sky_cannon')
    # launch ring (open to the west so you can walk in) + striped posts with lamps
    for k in range(12):
        if k in (5, 6, 7): continue
        a0, a1 = 2 * math.pi * k / 12, 2 * math.pi * (k + 1) / 12
        A(hull([(1984 + rr * math.cos(a), 1440 + rr * math.sin(a), z) for a in (a0, a1) for rr in (44, 56) for z in (0, 22)],
               {'top': T('coping'), 'side': T('awning_red')}))
    for (px, py) in ((1946, 1386), (1946, 1494)):
        A(cyl(px, py, 6, 0, 120, T('awning_red'), 8)); A(cyl(px, py, 10, 120, 132, T('lightpanel'), 8))
        light(px, py, 140, 120, '1 0.7 0.3')
    post_sign(1968, 1544, 'sign_cannon', 'w', w=160, h=40)
    speaker(1984, 1440, 40, 'sound/world/ambient/wind_stormy.ogg')
    # the isle: 12-gon slab, rock cone below, boulder rim (32 high: no walking off, landing from the air is fine)
    top = ngon(CX, CY, R, 12, phase=0)
    A(prism(top, ZT - 48, ZT, {'top': GRASS, 'side': T('rock'), 'bot': T('rock')}))
    A(hull([(x, y, ZT - 48) for x, y in top] + [(CX + 40, CY - 30, ZT - 620)], {'top': CAULK, 'side': T('rock'), 'bot': T('rock')}))
    for k in range(12):
        a0, a1 = 2 * math.pi * k / 12, 2 * math.pi * (k + 1) / 12
        pts = [(CX + rr * math.cos(a), CY + rr * math.sin(a), z) for a in (a0, a1) for rr in (276, R) for z in (ZT, ZT + 32)]
        A(hull(pts, {'top': T('rock'), 'side': T('rock')}))
    zt = ZT
    beach_hut(2900, 1480, 3060, 1608, 'w', (2980, 1448, 0, -1), z=zt)
    A(sign_box((2940, 1608, zt + 50), (3040, 1612, zt + 80), T('sign_isle'), 512, 128, back=T('wood_white'), facing='n'))
    weapon('splasher', 2980, 1544, zt + 112, wait=20)
    item('ammo_splasher', 2760, 1560, zt)
    item('item_armor_shard', 2990, 1560, zt)
    palm(2700, 1500, zt, h=240, lean=(-30, 10), seed=51); palm(2830, 1650, zt, h=200, lean=(10, 26), seed=52)
    lounger(2860, 1250, zt, 90); lounger(2930, 1250, zt, 90); umbrella(2895, 1300, zt, 'umb_green')
    mdl('pad_ducks/pad_duck.md3', 3050, 1330, zt, scale=0.3, angle=135)
    for (fx, fy, sd) in ((2700, 1500, 61), (2830, 1650, 62), (2660, 1380, 63), (3100, 1440, 64)):
        flowers(fx, fy, zt, seed=sd, n=3, r=34)
    mdl('pad_items/towelstack.md3', 2895, 1215, zt, scale=0.35, angle=90)
    mdl('pad_ball/pad_soccerball.md3', 2780, 1600, zt, scale=0.35)
    mdl('pad_ddmix/padship/amphora.md3', 3070, 1500, zt, scale=0.2, angle=40)
    clipbox((3030, 1300, zt), (3070, 1360, zt + 64))
    M.ent('misc_externalmodel', (2985, 1585, zt + 112), model='models/mapobjects/animated/raven_sitting_2_small.md3',
          angle=0, animationStart=0, animationEnd=210, animationFPS=30)
    # teleporter home (to the pirate cove beach)
    M.ent('trigger_teleport', brushes=[box((2730, 1270, zt), (2794, 1334, zt + 64), TRIG)], target='tp_isle')
    mdl('pad_teleporter/padtp_blue.md3', 2762, 1302, zt, scale=0.5, angle=0)
    M.ent('misc_teleporter_dest', (1140, 1650, 24), targetname='tp_isle', angle=0)
    light(2762, 1302, zt + 50, 200, '0.4 0.7 1'); light(CX, CY, zt + 160, 300)
    spawn(2700, 1380, zt, 180)


def gondola_ride():
    """second gondola cabin running out along the cable into the clouds (func_train, out of reach)"""
    y0, y1 = -2000, -2800
    cab = {'top': T('metal'), 'bot': T('metal_white'), 'e': T('window'), 'w': T('window'), 'n': T('stucco_sun'), 's': T('stucco_sun')}
    br = [box((-8, y0 - 8, 222), (8, y0 + 8, 238), 'common/origin'),
          box((-72, y0 - 56, 170), (72, y0 + 56, 280), cab),
          box((-80, y0 - 64, 280), (80, y0 + 64, 290), T('metal_white')),
          box((-6, y0 - 6, 290), (6, y0 + 6, 306), T('metal_dark')),
          box((-24, y0 - 16, 306), (24, y0 + 16, 312), T('metal_dark'))]
    M.ent('func_train', brushes=br, target='gond_a', speed=90)
    M.ent('path_corner', (0, y0, 230), targetname='gond_a', target='gond_b', wait=4)
    M.ent('path_corner', (0, y1, 230), targetname='gond_b', target='gond_a', wait=2)


def hot_air_balloon():
    cx, cy, z0 = -2700, -500, 900
    prof = [(0, 50), (60, 120), (140, 165), (230, 175), (310, 150), (370, 100), (400, 40)]
    br = []
    for i, ((za, ra), (zb, rb)) in enumerate(zip(prof, prof[1:])):
        pts = [(x, y, z0 + za) for x, y in ngon(cx, cy, ra, 12)] + [(x, y, z0 + zb) for x, y in ngon(cx, cy, rb, 12)]
        br.append(hull(pts, T('balloon') if i % 2 == 0 else T('balloon_b')))
    br.append(box((cx - 36, cy - 36, z0 - 140), (cx + 36, cy + 36, z0 - 90), {'side': T('bamboo'), 'top': T('teak'), 'bot': T('bamboo')}))
    for dx, dy in ((-30, -30), (26, -30), (-30, 26), (26, 26)):
        br.append(box((cx + dx, cy + dy, z0 - 90), (cx + dx + 4, cy + dy + 4, z0), T('metal_dark')))
    M.ent('func_bobbing', brushes=br, height=60, speed=14, phase=0.2)


def rainbow():
    """additive 7-band arc over the infinity waterfall"""
    cx, cy, cz = 0, 2150, -420
    n = 26
    for k in range(7):
        r0 = 1080 - 18 * k
        for i in range(n):
            a0 = math.radians(12 + 156 * i / n); a1 = math.radians(12 + 156 * (i + 1) / n)
            pts = [(cx + rr * math.cos(a), yy, cz + rr * math.sin(a)) for a in (a0, a1) for rr in (r0 - 18, r0) for yy in (cy, cy + 4)]
            A(hull(pts, T(f'rainbow{k}'), round_pts=False))


def deluxe():
    floaties(); ravens(); rapids(); sky_cannon_and_isle(); gondola_ride(); hot_air_balloon(); rainbow()



# =================================================================================================== main
def main():
    textures.make_all(OUT)
    TK.init(OUT)
    # custinfoparms for -custinfoparms (WoP footstep surfaceparms)
    os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
    open(os.path.join(OUT, 'scripts', 'custinfoparms.txt'), 'w').write(
        '// World of PADMAN custom infoparm file\n{\n}\n{\n carpetsteps  0x0080000\n latticesteps 0x0100000\n'
        ' sandsteps    0x0200000\n softsteps    0x0400000\n woodsteps    0x0800000\n snowsteps    0x1000000\n'
        ' splashsteps  0x2000000\n}\n')
    wave_pool(); dive_zone(); lazy_river()
    TW = tower(); grotto()
    terrace(); pirate_cove(); kids_zone(); snack_shack(); changing_rooms(); plaza()
    center_island(TW); scatter_east_west(); extras(); blockers(); facades(); deluxe()
    # tower boaster on wave machine roof
    weapon('boaster', -1440, 760, 160)
    item('ammo_boaster', -1150, 1000, 0)
    build_ground()
    slides(TW)
    perimeter(skip=[('n', -1088, 1088)])
    for (a0, a1) in ((-1088, -640), (640, 1088)):
        glass_rail(a0, ISL[3] - 8, a1, ISL[3], 192)
    skybox(); floating_islets()
    M.ent('info_player_intermission', (-1400, -1500, 900), angles='30 45 0')
    open(os.path.join(OUT, 'scripts', 'waterpark.shader'), 'a').write(TK.shaders())
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', 'waterpark.map'), 'w').write(
        M.text('// Splash World: Cloud Lagoon - generated by wop_tools/waterpark/build_waterpark.py\n'))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')


if __name__ == '__main__':
    main()
