#!/usr/bin/env python3
"""Padman's Dollhouse - World of Padman FFA map generator (map 'wop_paddollhouse').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_dollhouse.py

Writes <OUT>/maps/wop_paddollhouse.map, textures/paddollhouse/*, models/paddollhouse/*,
scripts/paddollhouse.shader and scripts/wop_paddollhouse.arena.

A sunny afternoon in a girl's bedroom. In the middle stands Rosewood Manor, a huge Victorian dollhouse, cut away at
the back like every real dollhouse, so all its rooms open onto the bedroom floor. Padman is doll-sized: the 1:12
furniture in the house is his size, the bed, the bookcase and the toys around it are giant. ~12u per cm.
x east, y north, bedroom floor z 0.

  Rosewood Manor    three floors, three rooms each: kitchen | hall + front door + stairs | parlour; bathroom (a big
                    roll-top bath: Pumper on the bottom) | landing + balcony door | master bedroom; nursery (a tiny
                    dollhouse - SECRET) | upper landing | library. The last flight climbs out onto the roof terrace
                    between the two gables; walk up the shingles to the ridges, or along the cut-back edge into the
                    attics (Balloony in the west one). The tower on the terrace: walk in, a pad throws you up through
                    the hatch onto its deck (Imperius). Pads from the floor into the first and second floor rooms.
  Front garden      on the house board under the big window: lily pond with steps out, swing, picket fence, gnomes,
                    flowers, a toy tree; pads onto the balcony and onto the window sill.
  The bed           east wall: a pad onto the mattress (Betty among the pillows and the plush bunny); under the bed it
                    is dark and dusty (shoeboxes, a suitcase, socks, something with glowing eyes).
  The bookcase      west wall: three pads from the floor up to its shelves; the Splasher waits on the top shelf.
  The play floor    braided rug, a teddy bears' tea party, letter blocks, a spinning top, a beach ball, a pram, an RC
                    car, the toy chest against the south wall (crawl in through the broken plank: Boaster).
  SECRET            walk into the door of the little dollhouse in the nursery -> the Doll's Ballroom (sealed under the
                    world): mirrors, chandelier, a giant music box with a turning ballerina; Pad Power, Revival, Killer
                    Ducks; a teleporter back to the garden.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import dh_textures as TX
import dhlib
import dh_house as DH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_paddollhouse'
T = lambda n: 'paddollhouse/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floor_oak': (2.0, 2.0), 'wall_bed': (1.5, 1.5), 'ceiling': (2.0, 2.0), 'flock': (1.0, 1.0), 'stone': (0.75, 0.75),
             'shelf_wood': (1.0, 1.0), 'ball_floor': (2.25, 2.25), 'ball_wall': (1.0, 1.0), 'water': (1.0, 1.0), 'bathwater': (0.25, 0.25),
             'parquet': (0.5, 0.5), 'checker': (0.5, 0.5), 'carpet_rose': (0.5, 0.5), 'carpet_blue': (0.5, 0.5),
             'attic_boards': (0.5, 0.5), 'boards_pale': (0.5, 0.5), 'dh_ceiling': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '22', '_color': '1 0.96 0.9', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '1.5'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
KEEP_OUT = []


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x, 1), round(y, 1), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """catalog model centred (by its bounds) on x, y, resting on zsurf"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def mdl_box(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, top_cut=2, clip=True, **kw):
    """catalog model centred on x, y with a weapclip box from its rotated bounds"""
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
    if not clip: return e
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
    """one of our own MD3s (models/paddollhouse), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = dhlib.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, angles=angles, **extra)


def lbox(x, y, z, ang, mn, mx, tex=WCLIP):
    """box given in a model's local frame (mn, mx) placed at (x, y, z) turned by ang degrees"""
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
    """custom model + its weapclip boxes (local frame, before mul)"""
    e = custom(name, x, y, z, ang, lit=lit, mul=mul, **kw)
    for (mn, mx) in boxes:
        lbox(x, y, z, ang, [v * mul for v in mn], [v * mul for v in mx])
    return e


def light(x, y, z, val, color='1 0.9 0.75', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
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


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((x, y, floor))


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)


def jumppad(x, y, z, land, apex, name, glow=True):
    """daisy pad (r 34 disc) + trigger_push + target_position (AimAtTarget: the target is the apex, measured from the
    trigger centre; it sits t_up/(t_up+t_down) of the way to `land`)"""
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
    if glow: light(x, y, z + 48, 90, '1 0.6 0.8')
    KEEP_OUT.append((x, y, 70))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def route(name, a, b):
    ROUTES.append((name, a, b))


def clip_half(b, axis, lo=None, hi=None):
    big = 100000
    cut = []
    if lo is not None:
        mn = [-big] * 3; mx = [big] * 3; mx[axis] = lo
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    if hi is not None:
        mn = [-big] * 3; mx = [big] * 3; mn[axis] = hi
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    return carve(b, cut)


def tex_box(mn, mx, top, side, bot=CAULK, **dirs):
    t = {'top': top, 'side': side, 'bot': bot}
    t.update(dirs)
    return box(mn, mx, t)


# =================================================================================================== bedroom hull
def bedroom_hull():
    X, Y0, Y1, Z = L.RX, L.RYS, L.RYN, L.RZ
    W = L.WALLT
    wl = T('wall_bed')
    # structural floor slab (the floorboards are a detail layer on top: the pond is dug into it)
    A(box((-X - W, Y0 - W, -256), (X + W, Y1 + W, -128), CAULK, detail=False))
    A(box((-X - W, Y0 - W, Z), (X + W, Y1 + W, Z + W), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((-X - W, Y0 - W, -128), (-X, Y1 + W, Z), {'e': wl, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((X, Y0 - W, -128), (X + W, Y1 + W, Z), {'w': wl, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((-X, Y0 - W, -128), (X, Y0, Z), {'n': wl, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    # north wall with the big window
    wx0, wx1, wz0, wz1 = L.WIN
    for (a, b, c, d) in sub_rects((-X, -128, X, Z), [(wx0, wz0, wx1, wz1)]):
        bb = box((a, Y1, b), (c, Y1 + W, d), CAULK, detail=False)
        for f in bb.faces:
            if f.n[1] < -0.9: f.tex = wl; f.sc = wopmap.default_scale(wl)
            elif abs(f.n[1]) < 0.1 and wx0 - 1 <= sum(p[0] for p in f.pts) / 3 <= wx1 + 1 and wz0 - 1 <= sum(p[2] for p in f.pts) / 3 <= wz1 + 1:
                f.tex = T('paint_white'); f.sc = (0.5, 0.5)
        A(bb)
    # the garden outside the window: a sealed sky box
    S = L.SKYBOX; t = 16
    sk = T('sky')
    A(box((S['x0'] - t, S['y0'], S['z0'] - t), (S['x1'] + t, S['y1'] + t, S['z0']), {'top': sk, 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((S['x0'] - t, S['y0'], S['z1']), (S['x1'] + t, S['y1'] + t, S['z1'] + t), {'bot': sk, 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((S['x0'] - t, S['y1'], S['z0']), (S['x1'] + t, S['y1'] + t, S['z1']), {'s': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((S['x0'] - t, S['y0'], S['z0']), (S['x0'], S['y1'], S['z1']), {'e': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((S['x1'], S['y0'], S['z0']), (S['x1'] + t, S['y1'], S['z1']), {'w': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    # window glass (solid, translucent) + the sill ledge
    g = box((wx0, Y1 + 28, wz0), (wx1, Y1 + 36, wz1), T('glass'))
    for f in g.faces: f.sc = (0.5, 0.5)
    A(g)
    A(tex_box((wx0 - 64, Y1 - L.SILL_D, wz0 - 16), (wx1 + 64, Y1, wz0), T('shelf_wood'), T('paint_white'), T('paint_white')))
    # skirting boards
    sk_ = {'top': T('paint_white'), 'side': T('paint_white'), 'bot': CAULK}
    D, H = L.SKIRT_D, L.SKIRT_H
    runs = [((-X, Y1 - D), (L.BOARD[0] - L.PLINTH, Y1)),                                  # north, west of the house board
            ((-X, Y0), (L.CHEST[0], Y0 + D)), ((L.CHEST[2], Y0), (X, Y0 + D)),              # south, either side of the toy chest
            ((-X, Y0 + D), (-X + D, L.SHELF[1])), ((-X, L.SHELF[3]), (-X + D, Y1 - D)),     # west, either side of the bookcase
            ((X - D, Y0 + D), (X, L.BED[1]))]                                               # east, south of the bed
    for (a, b) in runs:
        A(box((a[0], a[1], 0), (b[0], b[1], H), sk_))
    # floorboards (detail layer, the pond pit is carved out of it later)
    return box((-X, Y0, -128), (X, Y1, 0), {'top': T('floor_oak'), 'side': CAULK, 'bot': CAULK})


# =================================================================================================== board, garden, pond
def pond_poly(shrink=0.0, n=28):
    cx, cy, rx, ry = L.POND
    return [(cx + (rx - shrink) * math.cos(2 * math.pi * k / n), cy + (ry - shrink) * math.sin(2 * math.pi * k / n)) for k in range(n)]


POND_STEPS_Y = (1652, 1748)


def pond_steps():
    """stone steps out of the pond, rising east; returns [(x0, x1, ztop)]"""
    cx, cy, rx, ry = L.POND
    P = pond_poly()
    # inner x limit of the pond polygon at the step band's y edges
    xs = []
    for k in range(len(P)):
        (x0, y0), (x1, y1) = P[k], P[(k + 1) % len(P)]
        for yy in POND_STEPS_Y:
            if (y0 - yy) * (y1 - yy) <= 0 and y1 != y0 and (x0 > cx or x1 > cx):
                xs.append(x0 + (x1 - x0) * (yy - y0) / (y1 - y0))
    xe = min(xs) - 6
    n = 8
    run = 28
    out_ = []
    for k in range(n):
        out_.append((xe - run * (n - k), xe - run * (n - k - 1), L.POND_BOT + 16 * (k + 1)))
    return out_


def board_and_floor(floor_box):
    """the dollhouse board (z 0..32) with its plinth step, the floorboards, the pond pit + water + steps"""
    bx0, by0, bx1, by1 = L.BOARD
    P = L.PLINTH
    pit = prism(pond_poly(), L.POND_BOT, L.BOARD_Z, CAULK)
    # floorboards minus the pit
    for p in carve(floor_box, [pit]):
        for f in p.faces:
            if f.n[2] > 0.9: f.tex = T('floor_oak')
            elif abs(f.n[2]) < 0.9 and p.bounds()[0][2] > -129 and _near_pond(f): f.tex = T('stone')
            f.sc = wopmap.default_scale(f.tex)
        A(p)
    # plinth step (16u) round the open sides
    pt = {'top': T('board_edge'), 'side': T('board_edge'), 'bot': CAULK}
    A(box((bx0 - P, by0 - P, 0), (bx1 + P, by0, 16), pt))
    A(box((bx0 - P, by0, 0), (bx0, by1, 16), pt))
    A(box((bx1, by0, 0), (bx1 + P, by1, 16), pt))
    # the board: per region top texture (house rooms take their floor finish)
    regions = []
    for c, (xa, xb) in (('W', (L.DX0, -L.IWX)), ('C', (-L.IWX, L.IWX)), ('E', (L.IWX, L.DX1))):
        regions.append(((xa, L.DY0, xb, L.DY1), T(DH.ROOMS[(0, c)][1])))
    rest = sub_rects((bx0, by0, bx1, by1), [r for (r, _) in regions])
    regions += [(r, T('flock')) for r in rest]
    for ((a, b, c, d), top) in regions:
        bb = box((a, b, 0), (c, d, L.BOARD_Z), {'top': top, 'side': T('board_edge'), 'bot': CAULK})
        parts = carve(bb, [pit]) if (a < L.POND[0] + L.POND[2] and c > L.POND[0] - L.POND[2] and b < L.POND[1] + L.POND[3] and d > L.POND[1] - L.POND[3]) else [bb]
        for p in parts:
            for f in p.faces:
                if f.n[2] > 0.9: f.tex = top
                elif f.n[2] < -0.9: f.tex = CAULK
                elif _near_pond(f): f.tex = T('stone')
                else: f.tex = T('board_edge')
                f.sc = wopmap.default_scale(f.tex)
            A(p)
    # pit bottom (sand/stone) is the floorboard layer's carved floor; steps + water
    st = pond_steps()
    stt = {'top': T('stone'), 'side': T('stone'), 'bot': CAULK}
    steps_b = []
    for (x0, x1, zt) in st:
        b = box((round(x0), POND_STEPS_Y[0], L.POND_BOT), (round(x1), POND_STEPS_Y[1], zt), stt)
        steps_b.append(b); A(b)
    water = prism(pond_poly(), L.POND_BOT, L.POND_Z, T('water_nodraw'))
    for p in carve(water, steps_b):
        for f in p.faces:
            f.tex = T('water') if (f.n[2] > 0.9 and abs(max(q[2] for q in f.pts) - L.POND_Z) < 0.5) else T('water_nodraw')
            f.sc = wopmap.default_scale(f.tex)
        A(p)
    route('pond_steps', (st[-1][1] - 14, 1700, L.POND_Z + 8), (st[-1][1] + 60, 1700, L.BOARD_Z))


def _near_pond(f):
    cx, cy, rx, ry = L.POND
    c = np.mean(np.array(f.pts), 0)
    return ((c[0] - cx) / (rx + 8)) ** 2 + ((c[1] - cy) / (ry + 8)) ** 2 < 1.05


# =================================================================================================== the dollhouse
def wall_brushes(w):
    for (mn, mx) in w.pieces():
        b = box(tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx), CAULK)
        c = [(a + bb) / 2 for a, bb in zip(mn, mx)]
        for f in b.faces:
            f.tex = w.face_tex(f.n, [np.mean([p[i] for p in f.pts]) for i in range(3)])
            if f.tex in (CAULK,): pass
            f.sc = wopmap.default_scale(f.tex)
        A(b)
    for (mn, mx) in DH.window_glass_brushes(w):
        g = box(mn, mx, T('glass'))
        A(g)


def slab_brushes(f):
    """floor slab f (1..3) between the outer walls, minus its stair hole, split by room column for its finishes"""
    z0, z1 = L.FL[f] - L.SLAB, L.FL[f]
    holes = [L.stair_hole(f - 1)]
    for c, (xa, xb) in (('W', (L.DX0 + L.WT, -L.IWX)), ('C', (-L.IWX, L.IWX)), ('E', (L.IWX, L.DX1 - L.WT))):
        top = T(DH.ROOMS[(f, c)][1]); bot = T(DH.ROOMS[(f - 1, c)][2])
        for (a, b, cc, d) in sub_rects((xa, L.DY0, xb, L.DY1 - L.WT), holes):
            bb = box((a, b, z0), (cc, d, z1), CAULK)
            for fc in bb.faces:
                if fc.n[2] > 0.9: fc.tex = top
                elif fc.n[2] < -0.9: fc.tex = bot
                elif fc.n[1] < -0.9 and b <= L.DY0 + 0.5: fc.tex = T('dh_edge')
                else: fc.tex = T('paint_white')
                fc.sc = wopmap.default_scale(fc.tex)
            A(bb)


def stairs_brushes(k):
    x0, x1, d, y = L.flight(k)
    st = L.steps(k)[:-1]                      # the last tread is the slab edge above
    for (ya, yb, zt) in st:
        A(box((x0, ya, L.FL[k]), (x1, yb, zt), {'top': T('carpet_rose'), 'side': T('paint_white'), 'bot': CAULK}))
    # sloped handrail clip on the open (hall) side, under the slab above
    xr = x1 if x0 < 0 else x0
    xa, xb = (xr, xr + 6) if x0 < 0 else (xr - 6, xr)
    (ya0, yb0, z0), (ya1, yb1, z1) = st[0], st[-1]
    if d == 'n': yA, yB = ya0, yb1
    else: yA, yB = yb0, ya1
    zA, zB = L.FL[k], z1
    pts = [(x, yA, zA + 6) for x in (xa, xb)] + [(x, yB, zB) for x in (xa, xb)] + [(x, yA, zA + 54) for x in (xa, xb)] + [(x, yB, zB + 48) for x in (xa, xb)]
    rail = hull(pts, WCLIP, round_pts=False)
    for p in clip_half(rail, 2, hi=L.FL[k + 1] - L.SLAB):
        A(p)
    RAILS.append(('stair', k, xa, xb, yA, yB, zA, zB))


RAILS = []


def hole_rails(f):
    """clip railings round the stair hole in slab f (40 tall), leaving the arrival side open"""
    k = f - 1
    hx0, hy0, hx1, hy1 = L.stair_hole(k)
    x0, x1, d, y = L.flight(k)
    z = L.FL[f]
    out_ = []
    side_x = hx1 if x0 < 0 else hx0 - 6          # the hall side of the hole
    if x0 < 0: out_.append(((hx1, hy0, z), (hx1 + 6, hy1, z + 40)))
    else: out_.append(((hx0 - 6, hy0, z), (hx0, hy1, z + 40)))
    if d == 'n': out_.append(((hx0, hy0 - 6, z), (hx1, hy0, z + 40)))
    else: out_.append(((hx0, hy1, z), (hx1, hy1 + 6, z + 40)))
    for (mn, mx) in out_:
        A(box(mn, mx, WCLIP))
        RAILS.append(('hole', f, mn, mx))


def house():
    for w in DH.outer_walls() + DH.inner_walls():
        wall_brushes(w)
    for f in (1, 2, 3):
        slab_brushes(f)
    for k in (0, 1, 2):
        stairs_brushes(k)
    for f in (1, 2, 3):
        hole_rails(f)
    rail_models()
    # ---- roof: gable front walls, slopes, ridge walks
    for gi, g in enumerate(L.GABLES):
        xa, xb = g; xm = (xa + xb) / 2
        zr = L.ridge_z(g) - L.ROOF_T
        dx = L.ROOF_T / L.TP
        y0, y1 = L.DY1 - L.WT, L.DY1
        pts = []
        for yy in (y0, y1):
            pts += [(xa + dx, yy, L.FL[3]), (xm - L.RIDGE_W / 2, yy, zr), (xm + L.RIDGE_W / 2, yy, zr), (xb - dx, yy, L.FL[3])]
        gw = hull(pts, CAULK, round_pts=False)
        cz = L.FL[3] + 150; hw = DH.GABLE_WIN / 2
        win_cut = box((xm - hw, y0 - 1, cz - hw), (xm + hw, y1 + 1, cz + hw), CAULK)
        for p in carve(gw, [win_cut]):
            for fc in p.faces:
                if fc.n[1] < -0.9: fc.tex = T('attic_boards')
                elif fc.n[1] > 0.9: fc.tex = CAULK
                else: fc.tex = T('paint_white')
                fc.sc = wopmap.default_scale(fc.tex)
            A(p)
        A(box((xm - hw, y0 + 7, cz - hw), (xm + hw, y0 + 9, cz + hw), T('glass')))
        # slopes: top surface = layout.roof_top, ROOF_T thick (vertically), clipped at the attic floor level
        ry0, ry1 = L.ROOF_Y0, L.ROOF_Y1
        for (xo, xr) in ((xa, xm - L.RIDGE_W / 2), (xb, xm + L.RIDGE_W / 2)):
            zt_o, zt_r = L.FL[3], L.ridge_z(g)
            pts = []
            for yy in (ry0, ry1):
                pts += [(xo, yy, zt_o), (xr, yy, zt_r), (xo, yy, zt_o - L.ROOF_T), (xr, yy, zt_r - L.ROOF_T)]
            sl = hull(pts, CAULK, round_pts=False)
            for p in clip_half(sl, 2, lo=L.FL[3]):
                for fc in p.faces:
                    if fc.n[2] > 0.3: fc.tex = CAULK
                    elif fc.n[2] < -0.3: fc.tex = T('attic_boards')
                    else: fc.tex = T('paint_white') if abs(fc.n[1]) > 0.9 else CAULK
                    fc.sc = wopmap.default_scale(fc.tex)
                A(p)
        rz = L.ridge_z(g)
        # flat ridge walk, 4u proud of the slopes' top edge (flush seams left bspc without a walk link onto it)
        A(box((xm - L.RIDGE_W / 2, ry0, rz - L.ROOF_T), (xm + L.RIDGE_W / 2, ry1, rz + 4), {'top': CAULK, 'bot': T('attic_boards'), 'side': T('paint_white')}))
        o = DH.MODELS[f'roof_{gi}'][3]
        custom(f'roof_{gi}', o[0], o[1], o[2])
        o = DH.MODELS[f'gable_{gi}'][3]
        custom(f'gable_{gi}', o[0], o[1], o[2])
        route(f'ridge_{gi}', ((150 if gi else -150), 480, L.FL[3]), (xm, 480, rz + 4))
    # ---- tower on the terrace
    for w in DH.tower_walls():
        wall_brushes(w)
    x0, y0, x1, y1 = L.TOWER
    zt = L.TOWER_TOP
    for (a, b, c, d) in sub_rects((x0 + L.WT, y0 + L.WT, x1 - L.WT, y1 - L.WT), [L.TOWER_HATCH]):
        A(box((a, b, zt - L.SLAB), (c, d, zt), {'top': T('boards_pale'), 'bot': T('dh_ceiling'), 'side': T('paint_white')}))
    pt = {'top': T('paint_white'), 'side': CAULK, 'bot': CAULK}
    A(box((x0, y0, zt), (x1, y0 + L.WT, zt + L.PARAPET), dict(pt, n=T('paint_cream'))))
    A(box((x0, y1 - L.WT, zt), (x1, y1, zt + L.PARAPET), dict(pt, s=T('paint_cream'))))
    A(box((x0, y0 + L.WT, zt), (x0 + L.WT, y1 - L.WT, zt + L.PARAPET), dict(pt, e=T('paint_cream'))))
    A(box((x1 - L.WT, y0 + L.WT, zt), (x1, y1 - L.WT, zt + L.PARAPET), dict(pt, w=T('paint_cream'))))
    o = DH.MODELS['tower'][3]; custom('tower', o[0], o[1], o[2])
    custom('flag', x1 - 8, (y0 + y1) / 2, zt + L.PARAPET, lit=False)
    # ---- porch, balcony on its roof, the open front door leaves
    px0, py0, px1, py1 = L.PORCH
    A(box((px0, py0, L.FL[1] - L.SLAB), (px1, py1, L.FL[1]), {'top': T('boards_pale'), 'bot': T('paint_white'), 'side': T('paint_white')}))
    for (x, y) in ((px0 + 16, py1 - 16), (px1 - 16, py1 - 16)):
        A(cyl(x, y, 12, L.FL[0], L.FL[1] - L.SLAB, WCLIP, 8))
    for (mn, mx) in DH.balcony_rail_boxes():
        A(box(mn, mx, WCLIP))
    fx0, fx1 = L.FRONT_DOOR
    lw = (fx1 - fx0) / 2; yd = L.DY1 - L.WT
    for (hx, sg) in ((fx0, 1), (fx1, -1)):
        xa, xb = sorted((hx + sg * 2, hx + sg * 10))
        A(box((xa, yd - lw, L.FL[0]), (xb, yd - 2, L.FL[0] + L.DOOR_H - 4), WCLIP))
    o = DH.MODELS['porch'][3]; custom('porch', o[0], o[1], o[2])
    o = DH.MODELS['house_facade'][3]; custom('house_facade', o[0], o[1], o[2])
    # ---- MD3 railings on the stairs and round the holes (built in extra_models)
    for k in range(3):
        custom(f'srail_{k}', 0, 0, 0)
    for f in (1, 2, 3):
        custom(f'hrail_{f}', 0, 0, 0)
    # routes through the house
    route('gf_ff_stair', (-248, 500, L.FL[0]), (-248, 1240, L.FL[1]))
    route('ff_sf_stair', (248, 500, L.FL[1]), (248, 1240, L.FL[2]))
    route('sf_north', (248, 1240, L.FL[2]), (-248, 1248, L.FL[2]))
    route('sf_terrace', (-248, 1248, L.FL[2]), (-248, 500, L.FL[3]))
    route('terrace_tower', (0, 640, L.FL[3]), (0, 1000, L.FL[3]))
    route('terrace_attic_w', (-150, 416, L.FL[3]), (-560, 416, L.FL[3]))
    route('attic_w_in', (-560, 416, L.FL[3]), (-664, 880, L.FL[3]))
    route('terrace_attic_e', (150, 416, L.FL[3]), (560, 416, L.FL[3]))
    route('attic_e_in', (560, 416, L.FL[3]), (664, 900, L.FL[3]))
    route('front_door', (0, 1700, L.BOARD_Z), (0, 1050, L.FL[0]))
    route('back_in', (0, 120, 0), (0, 520, L.FL[0]))
    for f in range(3):
        route(f'door_w{f}', (-560, 480, L.FL[f]), (-100, 480, L.FL[f]))
        route(f'door_e{f}', (560, 480, L.FL[f]), (30, 520, L.FL[f]))
    route('kitchen_door', (-700, 1064, L.FL[0]), (-1100, 1064, L.BOARD_Z))
    route('parlour_door', (700, 1064, L.FL[0]), (1100, 1064, L.BOARD_Z))
    route('balcony', (0, 1150, L.FL[1]), (0, 1400, L.FL[1]))


def rail_models():
    """balusters + handrails for the stair flights and the hole railings (MD3, from the RAILS specs)"""
    import dh_models as DM
    from meshlib import Mesh, tube, revolve, rbox
    W = DM.S('wood_dark', 'lm', tag='rail'); Wh = DM.S('trim_white', 'lm', tag='rail')
    for k in range(3):
        X = dhlib.Model()
        x0, x1, d, y = L.flight(k)
        xr = (x1 + 3) if x0 < 0 else (x0 - 3)
        st = L.steps(k)[:-1]
        top_line = []
        for (ya, yb, zt) in st:
            yc = (ya + yb) / 2
            revolve(X.mesh(Wh), [(0, zt), (3, zt), (2.2, zt + 8), (3.2, zt + 22), (2, zt + 34), (2.6, zt + 46), (0, zt + 48)], n=8, cx=xr, cy=yc)
            top_line.append((xr, yc, zt + 50))
        under = L.FL[k + 1] - L.SLAB - 4
        tl = [p for p in top_line if p[2] < under]
        if len(tl) >= 2: tube(X.mesh(W), tl, 3.5, nseg=8)
        # newel post at the foot
        (ya, yb, zt) = st[0]
        yn = ya - 10 if d == 'n' else yb + 10
        rbox(X.mesh(W), (xr - 7, yn - 7, L.FL[k]), (xr + 7, yn + 7, L.FL[k] + 70), r=2, k=2, tile=64)
        X.mesh(W).add(DM._ball(7), t=(xr, yn, L.FL[k] + 78))
        dhlib.save(f'srail_{k}', X)
    for f in (1, 2, 3):
        X = dhlib.Model()
        for (kind, ff, mn, mx) in [r for r in RAILS if r[0] == 'hole' and r[1] == f]:
            mn = np.array(mn, float); mx = np.array(mx, float)
            c = (mn + mx) / 2
            along = 0 if (mx[0] - mn[0]) > (mx[1] - mn[1]) else 1
            a0, a1 = mn[along], mx[along]
            n = max(2, int((a1 - a0) / 16))
            for j in range(n + 1):
                p = c.copy(); p[along] = a0 + (a1 - a0) * j / n
                revolve(X.mesh(Wh), [(0, mn[2]), (2.6, mn[2]), (2, mn[2] + 10), (3, mn[2] + 22), (2, mn[2] + 34), (0, mn[2] + 36)], n=8, cx=p[0], cy=p[1])
            q0 = c.copy(); q0[along] = a0; q0[2] = mn[2] + 38
            q1 = c.copy(); q1[along] = a1; q1[2] = mn[2] + 38
            tube(X.mesh(W), [q0, q1], 3.5, nseg=8)
        dhlib.save(f'hrail_{f}', X)


# =================================================================================================== rooms
D = 1.5          # doll furniture scale (1:12 furniture made a little chunkier so the rooms read full)


def fw(name, x, y, z, ang=0, boxes=(), lit=True, mul=D, **kw):
    """doll furniture at scale D with its weapclip boxes (local frame of the model)"""
    return furn(name, x, y, z, ang, boxes, mul=mul, lit=lit, **kw)


def pic(name, wall, u, z, mul=D):
    """picture / wall clock / shelf on a wall: wall = ('x', x, facing +1/-1) or ('y', y, -1 for the north wall)"""
    kind, c, sg = wall
    if kind == 'x': custom(name, c + 0.5 * sg, u, z, 0 if sg > 0 else 180, mul=mul)
    else: custom(name, u, c - 0.5, z, -90, mul=mul)


def room_light(f, col, val=650, color='1 0.88 0.7', chand=True, x=None, y=820, two=True):
    xa, xb = DH.COLS[col]
    x = (xa + xb) / 2 if x is None else x
    zc = L.FL[f + 1] - L.SLAB
    if chand: custom('chandelier', x, y, zc - 0.01, lit=False, mul=2.0)
    if two:
        light(x - (xb - xa) * 0.25, y, L.FL[f] + 150, val * 0.6, color)
        light(x + (xb - xa) * 0.25, y, L.FL[f] + 150, val * 0.6, color)
        light(x, 560, L.FL[f] + 140, val * 0.4, color)
    else:
        light(x, y, zc - 80, val, color)


def kitchen():
    z = L.FL[0]
    fw('range', -672, 1264 - 45, z, -90, [((-30, -50, 0), (30, 50, 90))])
    fw('dresser', -1008 + 33, 864, z, 0, [((-22, -60, 0), (22, 60, 92)), ((-22, -60, 92), (-16, 60, 205))])
    fw('sink', -1008 + 42, 500, z, 0, [((-28, -50, 0), (30, 52, 90))])
    fw('larder', -320 - 38, 1080, z, 180, [((-25, -45, 0), (25, 45, 200))])
    tx, ty = -650, 820
    fw('k_table', tx, ty, z, 0, [((-40, -70, 61), (40, 70, 75))])
    for (x, y) in ((-34, -64), (-34, 64), (34, -64), (34, 64)):
        A(cyl(tx + x * D, ty + y * D, 6, z, z + 61 * D, WCLIP, 6))
    for (x, y, a) in ((tx - 96, ty - 50, 0), (tx - 96, ty + 50, 0), (tx + 96, ty - 50, 180), (tx + 96, ty + 50, 180)):
        fw('k_chair', x, y, z, a, [((-21, -22, 0), (21, 22, 46)), ((-24, -21, 46), (-18, 21, 96))])
    custom('apples', tx, ty - 30, z + 75 * D, mul=D)
    custom('rug_kitchen', tx, ty, z, 90, mul=D)
    pic('wall_jars', ('x', -1008, 1), 1180, z + 190)
    pic('wall_clock', ('y', 1264, -1), -960, z + 240)
    pic('pic_sea', ('x', -320, -1), 760, z + 200)
    custom('pot_plant', -1008 + 30, 1210, z, mul=D)
    A(cyl(-1008 + 30, 1210, 28, z, z + 33, WCLIP, 8))
    room_light(0, 'W')
    station(-470, 560, z)
    item('ammo_bubbleg', -800, 480, z)
    item('ammo_betty', -850, 1120, z)
    speaker(-672, 1200, z + 60, 'sound/world/ambient/fire_crackling.ogg', volume=0.25)
    timer_sound(-700, 900, z + 80, 'sound/world/animal/kitten_meow.ogg', 'meow', 40, 20, volume=0.6)
    spawn(-480, 1000, z, 270)


def hall_gf():
    z = L.FL[0]
    fw('gclock', 304 - 24, 1150, z, 180, [((-15, -24, 0), (16, 24, 214))])
    speaker(270, 1150, z + 200, 'sound/world/machine/clock_ticking.ogg', volume=0.5)
    fw('coat_stand', 240, 1236, z, 0, [((-6, -6, 0), (6, 6, 180))])
    fw('console', 304 - 27, 760, z, 180, [((-18, -50, 0), (18, 50, 80))])
    custom('runner_long', 0, 860, z, 0)
    custom('pot_plant_b', -140, 1220, z, mul=D)
    A(cyl(-140, 1220, 36, z, z + 45, WCLIP, 8))
    pic('pic_lady', ('x', 304, -1), 960, z + 200)
    pic('pic_flowers', ('x', 304, -1), 560, z + 200)
    room_light(0, 'C', y=860)
    item('ammo_pumper', 60, 1100, z)
    spawn(40, 600, z, 270)
    trigger_sound((-80, L.DY1 + 20, z), (80, L.DY1 + 120, z + 120), 'sound/world/machine/dingdong.ogg', 'doorbell', 6, volume=0.8)


def parlour():
    z = L.FL[0]
    fw('fireplace', 1008 - 24, 860, z, 180, [((-14, -65, 0), (16, 65, 110)), ((-16, -72, 110), (22, 72, 118))])
    speaker(950, 860, z + 30, 'sound/world/ambient/fire_crackling.ogg', volume=0.6)
    light(930, 860, z + 40, 200, '1 0.55 0.25')
    fw('sofa', 700, 860, z, 0, [((-42, -95, 0), (42, 95, 48)), ((-42, -79, 48), (-20, 79, 88)), ((-42, -95, 48), (40, -79, 64)), ((-42, 79, 48), (40, 95, 64))])
    fw('coffee_table', 840, 860, z, 0, [((-30, -50, 0), (30, 50, 45))])
    fw('armchair', 880, 560, z, 120, [((-42, -42, 0), (42, 42, 48)), ((-42, -42, 48), (-24, 42, 98))])
    fw('armchair_r', 880, 1160, z, 240, [((-42, -42, 0), (42, 42, 48)), ((-42, -42, 48), (-24, 42, 98))])
    fw('piano', 320 + 45, 1000, z, 0, [((-30, -75, 0), (26, 75, 86)), ((-30, -75, 86), (0, 75, 130)), ((34, -16, 0), (66, 16, 52))])
    fw('floor_lamp', 980, 1230, z, 0, [((-5, -5, 0), (5, 5, 160))])
    light(980, 1230, z + 230, 160, '1 0.85 0.6')
    fw('side_table', 560, 1200, z, 0, [((-18, -18, 0), (18, 18, 57))])
    custom('rug_parlour', 760, 860, z, 0, mul=D)
    pic('pic_big', ('x', 1008, -1), 560, z + 200, mul=1.2)
    pic('wall_clock', ('y', 1264, -1), 672, z + 250)
    room_light(0, 'E', val=600)
    item('item_armor_padshield', 520, 860, z)
    item('ammo_splasher', 600, 470, z)
    item('ammo_boaster', 940, 1000, z)
    spawn(500, 640, z, 270)


def bathroom():
    z = L.FL[1]
    cx, cy = -600, 800
    custom('tub', cx, cy, z)
    hl, hw = 120, 55
    n = 20
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pts = []
        for a in (a0, a1):
            for (sc, zz) in ((1.03, z), (1.03, z + 86), (0.86, z + 18), (0.88, z + 86)):
                pts.append((cx + math.cos(a) * hw * sc, cy + math.sin(a) * hl * sc, zz))
        A(hull(pts, WCLIP, round_pts=False))
    inner = [(cx + math.cos(a) * hw * 0.86, cy + math.sin(a) * hl * 0.86) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    A(prism(inner, z, z + 18, WCLIP))
    sx = cx + hw * 1.03
    for j, zt in enumerate((16, 32, 48, 64, 80)):
        A(box((round(sx + 4 + 14 * (4 - j)), cy - 40, z), (round(sx + 4 + 14 * (5 - j)), cy + 40, z + zt), {'top': T('pine'), 'side': T('pine'), 'bot': CAULK}))
    ins = []
    for j, zt in enumerate((82, 66, 50, 34)):
        x1 = cx + hw * 0.80 - 14 * j; x0 = x1 - 14
        b = box((round(x0), cy - 30, z + 18), (round(x1), cy + 30, z + zt), {'top': T('pine'), 'side': T('pine'), 'bot': CAULK})
        ins.append(b); A(b)
    wpoly = [(cx + math.cos(a) * hw * 0.85, cy + math.sin(a) * hl * 0.85) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    water = prism(wpoly, z + 18, z + 66, T('bathwater_nodraw'))
    for p in carve(water, ins):
        for fc in p.faces:
            fc.tex = T('bathwater') if (fc.n[2] > 0.9 and abs(max(q[2] for q in fc.pts) - (z + 66)) < 0.5) else T('bathwater_nodraw')
            fc.sc = wopmap.default_scale(fc.tex)
        A(p)
    weapon('pumper', cx - 5, cy - 70, z + 18)
    mdl_c('pad_ducks/pad_duck.md3', sx + 120, cy - 130, z, 0.32, 200)
    fw('toilet', -1008 + 36, 880, z, 0, [((-24, -20, 0), (24, 20, 46)), ((-24, -24, 46), (-12, 24, 80))])
    trigger_sound((-930, 840, z), (-880, 920, z + 60), 'sound/world/misc/toilet_flush.ogg', 'flush', 8, volume=0.7)
    fw('basin', -672, 1264 - 31, z, -90, [((-14, -16, 0), (14, 16, 70)), ((-20, -30, 70), (26, 30, 86))])
    fw('towel_rail', -1008, 540, z, 0, [((0, -32, 0), (12, 32, 100))])
    fw('laundry', -420, 1180, z, 0, [((-22, -22, 0), (22, 22, 46))])
    pic('wall_jars', ('y', 1264, -1), -950, z + 170)
    custom('bathmat', sx + 70, cy + 130, z, 0, mul=D)
    mdl_c('pad_items/towelstack.md3', -900, 1200, z, 1.2, 0)
    speaker(cx, cy + 100, z + 80, 'sound/world/ambient/water_drippling.ogg', volume=0.4)
    room_light(1, 'W', val=620, color='0.9 0.97 1')
    item('ammo_bubbleg', -480, 1100, z)
    item('item_armor_shard', -880, 600, z)


def landing_ff():
    z = L.FL[1]
    fw('console', -304 + 27, 760, z, 0, [((-18, -50, 0), (18, 50, 80))])
    pic('pic_pad', ('x', 304, -1), 760, z + 200)
    pic('pic_sea', ('x', -304, 1), 560, z + 200)
    custom('runner_long', 0, 760, z)
    fw('side_table', 120, 470, z, 0, [((-18, -18, 0), (18, 18, 57))])
    room_light(1, 'C', y=760)
    item('ammo_bubbleg', 0, 1000, z)
    spawn(-40, 640, z, 270)
    # balcony
    item('holdable_floater', 0, L.DY1 + 110, L.FL[1])
    custom('pot_small', -150, L.DY1 + 110, L.FL[1]); mdl_c('pad_ddmix/plants/tulip1.md3', -150, L.DY1 + 110, L.FL[1] + 114, 0.45, 0)
    A(cyl(-150, L.DY1 + 110, 56, L.FL[1], L.FL[1] + 114, WCLIP, 10))


def bedroom_doll():
    z = L.FL[1]
    bx, by = 846, 840
    fw('fourposter', bx, by, z, 180, [((-100, -75, 0), (100, 75, 56)), ((-100, -67, 56), (-94, 67, 120))] +
       [((sx * 96 - 4, sy * 71 - 4, 56), (sx * 96 + 4, sy * 71 + 4, 212)) for sx in (-1, 1) for sy in (-1, 1)])
    for s in (-1, 1):
        fw('bedside', 1008 - 30, by + s * 150, z, 180, [((-20, -22, 0), (20, 22, 55))])
    fw('dressing', 672, 1264 - 33, z, -90, [((-22, -55, 0), (22, 55, 75)), ((-22, -28, 75), (-15, 28, 165)), ((32, -15, 0), (60, 15, 48))])
    fw('drawers', 320 + 38, 1080, z, 0, [((-25, -50, 0), (26, 50, 100))])
    fw('wardrobe', 320 + 45, 720, z, 0, [((-30, -60, 0), (30, 60, 204))])
    custom('rug_bed', 640, 760, z, 90, mul=D)
    pic('pic_flowers', ('y', 1264, -1), 900, z + 220)
    room_light(1, 'E', val=580, color='1 0.85 0.85')
    item('ammo_pumper', 640, 500, z)
    item('item_armor_shard', 520, 1180, z)


def nursery():
    z = L.FL[2]
    fw('crib', -672, 1264 - 52, z, 0, [((-60, -34, 0), (60, 34, 104))])
    fw('rhorse', -860, 1000, z, 30, [((-40, -16, 0), (40, 16, 70))])
    fw('toyshelf', -1008 + 27, 864, z, 0, [((-18, -60, 0), (18, 60, 90))])
    fw('trunk_b', -880, 500, z, 0, [((-27, -55, 0), (27, 55, 60))])
    fw('rchair', -470, 1080, z, -120, [((-26, -22, 0), (24, 22, 46)), ((-30, -22, 46), (-24, 22, 110))])
    custom('rag_doll', -880, 500, z + 60 * D, 20, mul=D)
    custom('rug_nursery', -640, 780, z, 0, mul=D)
    pic('pic_pad', ('x', -1008, 1), 1180, z + 220)
    zc = L.FL[3] - L.SLAB
    my_ = 1264 - 52
    M.ent('func_rotating', brushes=[box((-680, my_ - 8, zc - 16), (-664, my_ + 8, zc), ORIGIN), box((-676, my_ - 4, zc - 40), (-668, my_ + 4, zc - 32), NODRAW_NS)],
          model2=dhlib.IQM['mobile'], speed=14, spawnflags=0, dmg=0)
    # the little dollhouse against the interior wall, door facing west: walk in -> the ballroom
    mx, my = -L.IWX - 60, 900
    custom('mini_house', mx, my, z, 180)
    hd, hw, H = 60, 110, 180
    def lb(mn, mx_): lbox(mx, my, z, 180, mn, mx_)
    lb((-hd, -hw, 0), (-hd + 6, hw, H)); lb((-hd + 6, -hw, 0), (hd - 6, -hw + 6, H)); lb((-hd + 6, hw - 6, 0), (hd - 6, hw, H))
    lb((hd - 6, -hw, 0), (hd, -32, H)); lb((hd - 6, 32, 0), (hd, hw, H)); lb((hd - 6, -32, 96), (hd, 32, H))
    lb((-hd + 6, -hw + 6, H - 8), (hd - 6, hw - 6, H))
    lb((-hd, -hw - 10, H), (hd + 8, hw + 10, H + 76))
    lb((hd, 36, 0), (hd + 60, 40, 94))
    M.ent('trigger_teleport', brushes=[box((mx - 30, my - 26, z + 2), (mx + 30, my + 26, z + 90), TRIG)], target='ball_in')
    M.ent('trigger_multiple', brushes=[box((mx - 100, my - 30, z + 2), (mx - 64, my + 30, z + 90), TRIG)], target='secret_snd', wait=2)
    speaker(mx, my, z + 120, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    route('mini_house', (mx - 170, my, z), (mx - 75, my, z))
    room_light(2, 'W', val=600, color='0.9 0.95 1')
    item('ammo_balloony', -760, 560, z)
    item('item_armor_shard', -500, 1000, z)
    station(-880, 1150, z)


def landing_sf():
    z = L.FL[2]
    fw('armchair_r', 40, 700, z, -90, [((-42, -42, 0), (42, 42, 48)), ((-42, -42, 48), (-24, 42, 98))])
    fw('floor_lamp', 150, 620, z, 0, [((-5, -5, 0), (5, 5, 160))])
    light(150, 620, z + 230, 140, '1 0.85 0.6')
    fw('side_table', -80, 640, z, 0, [((-18, -18, 0), (18, 18, 57))])
    custom('pot_plant_b', 130, 460, z, mul=D); A(cyl(130, 460, 36, z, z + 45, WCLIP, 8))
    pic('pic_chart', ('x', -304, 1), 800, z + 200)
    pic('wall_clock', ('x', 304, -1), 800, z + 230)
    room_light(2, 'C', y=780)
    item('ammo_boaster', -60, 500, z)


def library():
    z = L.FL[2]
    for (x, y, a) in ((1008 - 26, 864, 180), (672, 1264 - 26, -90), (320 + 26, 900, 0), (320 + 26, 1100, 0)):
        fw('bookcase', x, y, z, a, [((-17, -50, 0), (17, 50, 208))])
    fw('desk', 700, 740, z, 0, [((-30, -60, 0), (30, 60, 77))])
    fw('d_chair', 700 - 80, 740, z, 0, [((-21, -22, 0), (21, 22, 46)), ((-24, -21, 46), (-18, 21, 96))])
    fw('globe', 900, 520, z, 0, [((-18, -18, 0), (18, 18, 96))])
    fw('armchair', 560, 1120, z, -40, [((-42, -42, 0), (42, 42, 48)), ((-42, -42, 48), (-24, 42, 98))])
    fw('floor_lamp', 460, 1200, z, 0, [((-5, -5, 0), (5, 5, 160))])
    light(460, 1200, z + 230, 140, '1 0.85 0.6')
    custom('rug_parlour', 700, 760, z, 90, mul=D)
    room_light(2, 'E', val=580)
    item('item_visionless', 820, 1050, z)
    item('ammo_betty', 900, 1180, z) if False else item('ammo_betty', 560, 470, z)
    spawn(540, 560, z, 90)


def attics():
    z = L.FL[3]
    # west attic (Balloony): dusty storage under the shingles (keep things under the slopes' headroom)
    fw('trunk', -820, 1120, z, 0, [((-25, -45, 0), (25, 45, 55))])
    fw('trunk_b', -560, 1150, z, 90, [((-27, -55, 0), (27, 55, 60))])
    custom('dress_form', -672, 960, z); lbox(-672, 960, z, 0, (-12, -12, 0), (12, 12, 160))
    fw('rchair', -620, 700, z, -40, [((-26, -22, 0), (24, 22, 46)), ((-30, -22, 46), (-24, 22, 110))])
    custom('lamp_old', -700, 560, z); lbox(-700, 560, z, 0, (-8, -8, 0), (8, 8, 150))
    fw('cbox', -820, 960, z, 10, [((-30, -35, 0), (30, 35, 50))])
    fw('cbox_o', -820, 820, z, -20, [((-30, -40, 0), (30, 40, 44))])
    weapon('balloony', -560, 860, z)
    light(-672, 860, z + 180, 360, '1 0.92 0.75')
    light(-672, 520, z + 120, 240, '1 0.92 0.75')
    # east attic
    fw('cbox_o', 560, 1180, z, 20, [((-30, -40, 0), (30, 40, 44))])
    fw('cbox', 800, 1150, z, -15, [((-30, -35, 0), (30, 35, 50))])
    fw('drawers_b', 672, 820, z, 180, [((-20, -40, 0), (21, 40, 70))])
    custom('birdcage', 672, 820, z + 70 * D)
    fw('trunk', 540, 640, z, 90, [((-25, -45, 0), (25, 45, 55))])
    custom('rag_doll', 540, 640, z + 41 * D * 1.5 + 0.0, 200) if False else None
    item('holdable_boomies', 820, 900, z)
    item('ammo_imperius', 760, 560, z)
    light(672, 860, z + 180, 360, '1 0.92 0.75')
    light(672, 520, z + 120, 240, '1 0.92 0.75')
    # terrace
    item('item_speedy', 120, 600, z)
    item('ammo_balloony', -120, 500, z)
    custom('pot_small', 260, 440, z); mdl_c('pad_ddmix/plants/flower_pink.md3', 260, 440, z + 114, 0.35, 0)
    A(cyl(260, 440, 56, z, z + 114, WCLIP, 10))
    light(0, 600, z + 260, 300, '1 0.95 0.85')
    # tower room + deck
    furn('telescope', -100, 1200, z, 135, [((-8, -8, 0), (8, 8, 110))])
    jumppad(0, 1180, z, (0, 960, L.TOWER_TOP), L.TOWER_TOP + 130, 'pad_tower')
    jumppad(110, 1080, L.TOWER_TOP, (150, -650, 0), L.TOWER_TOP + 220, 'pad_tower_down')
    custom('pic_chart', 159.5, 950, z + 200, angle=180, mul=D)
    light(0, 1000, L.TOWER_TOP - 80, 420, '1 0.95 0.85')
    weapon('imperius', -60, 980, L.TOWER_TOP)
    trigger_sound((-160, 896, L.TOWER_TOP + 2), (40, 1264, L.TOWER_TOP + 90), 'sound/world/human/applause.ogg', 'applause', 20, volume=0.6)
    item('ammo_imperius', 100, 1000, z)


def house_rooms():
    kitchen(); hall_gf(); parlour(); bathroom(); landing_ff(); bedroom_doll(); nursery(); landing_sf(); library(); attics()


# =================================================================================================== garden on the board
def garden():
    z = L.BOARD_Z
    custom('pond_rim', L.POND[0], L.POND[1], 0)
    # sailboat circling the pond
    cx, cy = L.POND[0], L.POND[1]
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, L.POND_Z - 8), (cx + 8, cy + 8, L.POND_Z + 8), ORIGIN), box((cx - 4, cy - 4, L.POND_Z + 30), (cx + 4, cy + 4, L.POND_Z + 38), NODRAW_NS)],
          model2=dhlib.IQM['sailboat_ring'], speed=-9, spawnflags=0, dmg=0)
    item('ammo_splasher', cx - 60, cy + 40, L.POND_BOT)
    # swing
    sx, sy = L.SWING
    custom('swing', sx, sy, z, 90)                          # frame along x, the seat swings north-south
    for s in (-1, 1):
        for d in (-1, 1):
            A(hull([(sx + s * 260 + dx, sy + d * 150 + dy, z) for dx in (-12, 12) for dy in (-12, 12)] +
                   [(sx + s * 244 + dx, sy + d * 20 + dy, z + 520) for dx in (-10, 10) for dy in (-10, 10)], WCLIP, round_pts=False))
    A(cyl(sx - 260, sy, 4, z + 520, z + 540, WCLIP, 6)) if False else None
    pz = z + 540
    M.ent('func_pendulum', brushes=[box((sx - 8, sy - 8, pz - 8), (sx + 8, sy + 8, pz + 8), ORIGIN), box((sx - 4, sy - 4, pz - 448), (sx + 4, sy + 4, pz - 440), NODRAW_NS)],
          model2=dhlib.IQM['swing_seat'], speed=24, phase=0)
    item('item_jumper', 480, 1380, z)
    # picket fences on the board edges (gates left open), bench, mailbox, gnomes, flowers, the toy tree, path stones
    for x in (L.BOARD[0] + 12, L.BOARD[2] - 12):
        for yc in (1456, 1880):
            custom('fence_s', x, yc, z, 0)
            A(box((x - 10, yc - 160, z), (x + 10, yc + 160, z + 150), WCLIP))
    furn('bench', 0, 1960, z, -90, [((-50, -200, 0), (50, 200, 100)), ((-56, -200, 100), (-40, 200, 220))])
    furn('mailbox', 1000, 1440, z, 180, [((-50, -24, 0), (50, 24, 290))])
    furn('gnome', -620, 1360, z, -60, [((-30, -30, 0), (30, 30, 160))])
    furn('gnome', 1060, 1620, z, 200, [((-30, -30, 0), (30, 30, 160))])
    flowers = [('pad_ddmix/plants/tulip1.md3', 0.9), ('pad_ddmix/plants/tulip2.md3', 1.0), ('pad_ddmix/plants/flower_pink.md3', 0.8),
               ('pad_ddmix/plants/flower_yellow.md3', 0.7), ('pad_sunflower/pad_sunflower_l.md3', 0.9)]
    spots = [(-900, 1400), (-780, 1400), (700, 1410), (860, 1400), (-1060, 1930), (-420, 1930), (300, 1930), (-560, 1330)]
    for k, (x, y) in enumerate(spots):
        p, s = flowers[k % len(flowers)]
        mdl_c(p, x, y, z, s, (k * 47) % 360)
    mdl_c('pad_ddmix/plants/bonsai.md3', 980, 1880, z, 1.2, 30)
    A(cyl(980, 1880, 34, z, z + 160, WCLIP, 8))
    for k in range(6):
        custom('stone_step', 0, 1520 + k * 70, z, k * 23)
    mdl_c('pad_ddmix/trashcan/lamp_house_day.md3', -1060, 1380, z, 1.6, 0)
    item('ammo_bubbleg', 600, 1460, z)
    item('item_armor_shard', -200, 1800, z)
    item('ammo_pumper', 980, 1600, z)
    spawn(300, 1750, z, 180)
    spawn(-260, 1900, z, 270)
    # pads: onto the balcony and onto the window sill
    jumppad(330, 1520, z, (110, L.DY1 + 100, L.FL[1]), L.FL[1] + 140, 'pad_balcony')
    jumppad(-380, 1430, z, (-590, L.RYN - 48, L.WIN[2]), L.WIN[2] + 130, 'pad_sill')
    # the window sill: pots between the curtains, a sleeping cat, Speedy... no: Boaster ammo + armour
    for x in (-900, 900):
        custom('pot_small', x, L.RYN - 48, L.WIN[2])
        fl = ['pad_ddmix/plants/tulip2.md3', 'pad_ddmix/plants/flower_pink.md3', 'pad_ddmix/plants/tulip1.md3', 'pad_ddmix/plants/flower_pink.md3'][(x // 300) % 4]
        mdl_c(fl, x, L.RYN - 48, L.WIN[2] + 114, 0.45 if 'tulip' in fl else 0.4, 0)
        A(cyl(x, L.RYN - 48, 52, L.WIN[2], L.WIN[2] + 114, WCLIP, 10))
    item('ammo_boaster', 0, L.RYN - 48, L.WIN[2])
    item('item_armor_shard', -150, L.RYN - 48, L.WIN[2])
    for x in (-800, -300, 300, 800):
        light(x, 1700, 520, 900, '1 0.96 0.85')
    light(-760, 1700, 140, 300, '0.85 0.95 1')
    timer_sound(0, L.SKYBOX['y0'] + 400, 1800, 'sound/world/animal/bird_blackcap.ogg', 'bird1', 18, 10, volume=0.6)
    timer_sound(-900, L.SKYBOX['y0'] + 600, 1600, 'sound/world/animal/blackbird.ogg', 'bird2', 26, 12, volume=0.5)


# =================================================================================================== bedroom furniture
def bookcase_big():
    x0, y0, x1, y1 = L.SHELF
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    custom('bookshelf', xc, yc, 0)
    zt = L.SHELF_Z; t = L.SHELF_T
    W = WCLIP
    A(box((x0, y0, 0), (x1 - 24, y1, zt[0]), W))                                                  # plinth
    A(box((x0, y0, zt[0]), (x0 + L.SHELF_BACK, y1, zt[-1] - t), W))                                # back
    for z in zt[1:-1]:
        for i in range(3):
            A(box((x0 + L.SHELF_BACK, L.SHELF_DIV[i] + 16, z - t), (x1, L.SHELF_DIV[i + 1] - 16, z), W))
    A(box((x0, y0 - 16, zt[-1] - t), (x1 + 24, y1 + 16, zt[-1] + 24), W))                         # top + crown
    for yd in L.SHELF_DIV:
        lo = max(yd - 16, y0 - 16) if yd in (y0, y1) else yd - 16
        A(box((x0 + L.SHELF_BACK, yd - 16, zt[0]), (x1, yd + 16, zt[-1] - t), W))
    # contents per compartment (3 bays x 4 levels): book rows at the back, toys, items
    bays = [(L.SHELF_DIV[i] + 16, L.SHELF_DIV[i + 1] - 16) for i in range(3)]
    levels = zt[:-1]
    bx = x0 + L.SHELF_BACK
    plan = {(0, 0): 'books_0', (1, 0): 'books_1', (2, 0): 'books_2', (0, 1): 'books_3', (1, 1): 'toys1', (2, 1): 'books_4',
            (0, 2): 'books_1', (1, 2): 'books_0', (2, 2): 'toys2', (0, 3): 'books_2', (1, 3): 'books_3', (2, 3): 'books_4'}
    for (bi, li), what in plan.items():
        ya, yb = bays[bi]; zf = levels[li]
        if what.startswith('books'):
            ln = {'books_0': 680, 'books_1': 520, 'books_2': 720, 'books_3': 460, 'books_4': 600}[what]
            yy = ya + 40 + ln / 2 if (bi + li) % 2 == 0 else yb - 40 - ln / 2
            custom(what, bx, yy, zf, 0)
            A(box((bx, round(yy - ln / 2), zf), (bx + 200, round(yy + ln / 2), zf + 210), W))
            # a book lying flat in front / a catalog prop
        elif what == 'toys1':
            custom('teddy', bx + 140, (ya + yb) / 2 - 150, zf, 0, mul=0.85)
            lbox(bx + 140, (ya + yb) / 2 - 150, zf, 0, (-85, -85, 0), (85, 85, 280))
            mdl_box('pad_ddmix/padlibrary/bookend.md3', bx + 90, (ya + yb) / 2 + 200, zf, 1.4, 0)
        elif what == 'toys2':
            mdl_box('pad_ddmix/attic/kaspad.md3', bx + 150, (ya + yb) / 2 - 120, zf, 1.4, 0)
            custom('ball', bx + 170, (ya + yb) / 2 + 200, zf, mul=0.5)
            A(hull([(bx + 170 + px, (ya + yb) / 2 + 200 + py, zf + pz) for (px, py) in ngon(0, 0, 66, 10) for pz in (0, 140)], W, round_pts=False))
    # pads up to shelf 1, 2 and 3 from the floor (in front of bays 0, 1, 2)
    fx = x1 + 200
    jumppad(fx, (bays[0][0] + bays[0][1]) / 2, 0, (x1 - 110, (bays[0][0] + bays[0][1]) / 2 + 120, zt[1]), zt[1] + 150, 'pad_s1')
    jumppad(fx + 40, (bays[1][0] + bays[1][1]) / 2 + 150, 0, (x1 - 110, (bays[1][0] + bays[1][1]) / 2 + 150, zt[2]), zt[2] + 150, 'pad_s2')
    jumppad(fx + 80, (bays[2][0] + bays[2][1]) / 2 - 100, 0, (x1 - 110, (bays[2][0] + bays[2][1]) / 2 - 100, zt[3]), zt[3] + 150, 'pad_s3')
    weapon('splasher', x1 - 90, (bays[2][0] + bays[2][1]) / 2 + 160, zt[3])
    item('ammo_splasher', x1 - 90, (bays[1][0] + bays[1][1]) / 2 - 180, zt[2])
    item('item_armor_shard', x1 - 90, (bays[1][0] + bays[1][1]) / 2 + 180, zt[2])
    item('ammo_betty', x1 - 90, (bays[0][0] + bays[0][1]) / 2 - 160, zt[1])
    item('ammo_nipper', x1 - 90, (bays[0][0] + bays[0][1]) / 2 + 200, zt[1])


def bed_big():
    x0, y0, x1, y1 = L.BED
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    custom('bed', xc, yc, 0)
    lg = L.BED_LEG
    for (x, y) in ((x0, y0), (x1 - lg, y0), (x0, y1 - lg), (x1 - lg, y1 - lg)):
        h = 720 if y > yc else 640
        A(box((x, y, 0), (x + lg, y + lg, L.BED_RAIL[0]), WCLIP))
        A(box((x, y, L.BED_TOP), (x + lg, y + lg, h + 60), WCLIP))
    A(box((x0, y0, L.BED_RAIL[0]), (x1, y1, L.BED_TOP), WCLIP))                                   # rails + mattress block
    A(box((x0 + lg, y1 - 40, L.BED_TOP), (x1 - lg, y1, 1080), WCLIP))                             # headboard
    for sx in (-1, 1):                                                                            # pillows
        cxp = xc + sx * 300
        A(box((cxp - 210, y1 - 370, L.BED_TOP), (cxp + 210, y1 - 100, L.BED_TOP + 90), WCLIP))
    yf = yc + (y1 - y0) / 2 * 0.25
    A(box((x0 + 100, yf - 56, L.BED_TOP), (x1 - 100, yf + 56, L.BED_TOP + 36), WCLIP))          # turnover fold
    furn('bunny', 1600, 700, L.BED_TOP, -60, [((-140, -130, 0), (140, 130, 420))])
    weapon('betty', 2000, 1050, L.BED_TOP)
    item('ammo_splasher', 1450, 1050, L.BED_TOP)
    item('item_armor_shard', 2100, 300, L.BED_TOP)
    mdl_c('pad_books/kids/mbook_fl_2.md3', 1900, 400, L.BED_TOP, 1.5, 20)
    jumppad(1800, y0 - 300, 0, (1800, y0 + 380, L.BED_TOP), L.BED_TOP + 200, 'pad_bed')
    spawn(1650, 200, L.BED_TOP, 180)
    # under the bed: dusty and dark
    furn('shoebox', 1500, 1500, 0, 10, [((-180, -110, 0), (180, 110, 150))])
    furn('shoebox_b', 2000, 700, 0, 80, [((-180, -110, 0), (180, 110, 140))])
    furn('suitcase', 1800, 1750, 0, 0, [((-320, -110, 0), (320, 110, 200))])
    furn('shoebox', 1450, 400, 0, -30, [((-180, -110, 0), (180, 110, 150))])
    custom('dust_a', 1750, 1050, 0); custom('dust_b', 2100, 1350, 0); custom('dust_a', 1600, 80, 0, mul=0.7)
    custom('eyes', L.RX - 13, 1650, 0, 180)
    light(2150, 1650, 60, 90, '0.6 1 0.4')
    mdl_c('pad_clothes/sock_grey2.md3', 2150, 1000, 0, 3.0, 70)
    weapon('bubbleg', 2050, 1500, 0)
    item('holdable_bambam', 1600, 900, 0)
    item('ammo_betty', 2150, 250, 0)
    light(1800, 1000, 200, 120, '0.7 0.7 1')
    route('under_bed', (1800, -200, 0), (1800, 1250, 0))


def toy_chest():
    x0, y0, x1, y1 = L.CHEST
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    custom('toy_chest', xc, yc, 0, 90)
    t = L.CHEST_T; H = L.CHEST_H
    hx0, hx1, hz = L.CHEST_HOLE
    W = WCLIP
    A(box((x0 + t, y0 + t, 0), (x1 - t, y1 - t, 16), W))
    A(box((x0, y0, 0), (x1, y0 + t, H), W))
    A(box((x0, y0 + t, 0), (x0 + t, y1, H), W)); A(box((x1 - t, y0 + t, 0), (x1, y1, H), W))
    for (a, b, za, zb) in ((x0 + t, hx0, 0, H), (hx1, x1 - t, 0, H), (hx0, hx1, hz, H)):
        A(box((a, y1 - t, za), (b, y1, zb), W))
    A(box((x0 + 4, y0 + 2, H), (x1 - 4, y0 + 50, H + 470), W))                                 # the open lid against the wall
    weapon('boaster', xc - 120, yc + 20, 16)
    for (p, px, py, s) in (('pad_ball/pad_soccerball.md3', xc + 200, yc - 60, 1.6), ('pad_ball/pad_basketball.md3', xc + 120, yc + 90, 1.4)):
        mdl_c(p, px, py, 16, s, 0)
        A(hull([(px + qx, py + qy, 16 + qz) for (qx, qy) in ngon(0, 0, 55, 10) for qz in (0, 120)], W, round_pts=False))
    custom('block_C', xc + 250, yc + 100, 16, 20, mul=0.8)
    lbox(xc + 250, yc + 100, 16, 20, (-58, -58, 0), (58, 58, 115))
    item('ammo_boaster', xc - 240, yc - 80, 16)
    route('toy_chest', (xc, y1 + 160, 0), (xc - 60, yc - 40, 16))


def tea_party():
    tx, ty = L.TEA
    custom('tea_table', tx, ty, 0)
    A(cyl(tx, ty, L.TEA_R, L.TEA_H - 14, L.TEA_H, WCLIP, 16))
    for a in range(4):
        x, y = tx + math.cos(a * math.pi / 2 + math.pi / 4) * L.TEA_R * 0.62, ty + math.sin(a * math.pi / 2 + math.pi / 4) * L.TEA_R * 0.62
        A(cyl(x, y, 14, 0, L.TEA_H - 14, WCLIP, 8))
    for k, a in enumerate((20, 110, 200, 290)):
        r = L.TEA_R + 120
        x, y = tx + math.cos(math.radians(a)) * r, ty + math.sin(math.radians(a)) * r
        furn('toy_chair', x, y, 0, a + 180, [((-56, -56, 0), (56, 56, 112)), ((-58, -54, 112), (-50, 54, 230))])
    for k, (a, nm) in enumerate(((65, 'teddy'), (245, 'teddy_pink'))):
        r = L.TEA_R + 160
        x, y = tx + math.cos(math.radians(a)) * r, ty + math.sin(math.radians(a)) * r
        furn(nm, x, y, 0, a + 180, [((-100, -100, 0), (110, 100, 330))])
    zt = L.TEA_H
    mdl_c('pad_cake/pad_cakestand.md3', tx, ty, zt, 1.1, 0)
    for k in range(4):
        a = k * math.pi / 2 + 0.6
        mdl_c('pad_plates/plate_coffee%d.md3' % (k + 1), tx + math.cos(a) * 150, ty + math.sin(a) * 150, zt, 0.6, k * 30)
        mdl_c('pad_cups/pad_cup0%d.md3' % (k + 2), tx + math.cos(a + 0.45) * 140, ty + math.sin(a + 0.45) * 140, zt, 0.6, k * 80)
    mdl_c('pad_cutlery/pad_teaspoon.md3', tx - 60, ty + 120, zt, 0.8, 40)
    item('ammo_pumper', tx, ty - 420, 0)


def play_floor():
    custom('rug', L.RUG[0], L.RUG[1], 0)
    # letter block towers + scattered blocks
    def stack(x, y, letters, a0=0, da=11):
        z = 0
        for k, lt in enumerate(letters):
            a = a0 + k * da
            custom(f'block_{lt}', x, y, z, a)
            lbox(x, y, z, a, (-70, -70, 0), (70, 70, 144))
            z += 144
    stack(380, -360, 'ABC', 5)
    stack(-540, -1460, 'DEF', -8, 17)
    stack(-260, -1520, 'AB', 30, -9)
    stack(-400, -1240, 'C', 50)
    stack(1520, -1300, 'ED', 15)
    stack(-1520, -500, 'F', 33)
    stack(1050, -400, 'BA', -20, 25)
    stack(-1400, 1760, 'ACE', 12, 9)
    # spinning top (mover) with a static clip
    tx, ty = 240, -1150
    M.ent('func_rotating', brushes=[box((tx - 8, ty - 8, 152), (tx + 8, ty + 8, 168), ORIGIN), box((tx - 4, ty - 4, 300), (tx + 4, ty + 4, 308), NODRAW_NS)],
          model2=dhlib.IQM['top'], speed=180, spawnflags=0, dmg=0)
    A(cyl(tx, ty, 140, 0, 310, WCLIP, 12))
    # beach ball, pram, RC car, big teddy, crayons + drawing, books, beanbag
    bx, by = -320, -1760
    custom('ball', bx, by, 0)
    A(hull([(bx + px * math.cos(ph), by + py * math.cos(ph), 150 + 150 * math.sin(ph)) for ph in np.linspace(-1.3, 1.3, 6) for (px, py) in [(math.cos(a) * 146, math.sin(a) * 146) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]] + [(bx, by, 1)], WCLIP, round_pts=False))
    furn('pram', -1560, -1250, 0, 30, [((-250, -140, 0), (240, 140, 420)), ((240, -120, 380), (370, 120, 550))])
    mdl_box('pad_nascars/padcar_orange_rc.md3', 760, -860, 0, 1.5, 20)
    furn('teddy', -1780, 1450, 0, -30, [((-100, -100, 0), (110, 100, 330))], mul=1.5)
    for k, p in enumerate(('pad_pencils/pad_pencilsr_lg.md3', 'pad_pencils/pad_pencilsb_lg.md3' if False else 'pad_pencils/pad_pencilsbl_lg.md3',
                           'pad_pencils/pad_pencilsy_lg.md3', 'pad_pencils/pad_pencilsg_lg.md3', 'pad_pencils/pad_pencilsp_lg.md3')):
        mdl_c(p, 620 + k * 40, -1560 + (k % 2) * 60, 0, 1.5, 10 + k * 37)
    mdl_c('pad_books/kids/pad_okb_lg.md3', 700, -1350, 0, 1.5, -12)
    mdl_c('pad_books/kids/mbook_fl_1.md3', -800, -300, 0, 1.6, 40)
    mdl_c('pad_books/kids/mbook_fl_3.md3', 1300, -700, 0, 1.6, -70)
    mdl_c('pad_books/kids/mbook_fl_4_ang.md3', -1250, -1700, 0, 1.6, 15)
    mdl_box('pad_ddmix/padshop/cardboard_standup.md3', 1900, -1750, 0, 1.6, 135)
    mdl_box('pad_actionfigures/fig_lilly.md3', -1350, 300, 0, 1.6, 30)
    mdl_box('pad_actionfigures/fig_girl.md3', 1950, -1150, 0, 1.6, 120)
    mdl_box('pad_radio_car/radio_control.md3', 1200, -1050, 0, 1.6, -30)
    for (x, y, a) in ((-L.RX + 4, -1800, 0), (L.RX - 4, -1500, 180), (-L.RX + 4, 1600, 0)):
        mdl_c('pad_objects/pad_litesw_steck03.md3', x, y, 300, 1.5, a)
    # more toys: sightline cover across the play floor
    def round_toy(name, x, y, r, h, ang=0):
        custom(name, x, y, 0, ang)
        A(cyl(x, y, r, 0, h, WCLIP, 12))
    round_toy('rings', -360, 60, 112, 330)
    round_toy('drum', 380, 30, 118, 170, 30)
    round_toy('drum', -1950, 1800, 118, 170, 200)
    round_toy('rings', 1000, 100, 112, 330, 90)
    custom('beanbag', -1460, 960, 0, 20)
    A(cyl(-1460, 960, 250, 0, 260, WCLIP, 14))
    furn('truck', -1060, -180, 0, 80, [((-220, -100, 0), (220, 100, 220))])
    furn('truck', 1450, -700, 0, 160, [((-220, -100, 0), (220, 100, 220))])
    for (nm, x, y) in (('book_pile', -150, -520), ('book_pile_b', 120, -1500)):
        custom(nm, x, y, 0)
        A(box((x - 180, y - 130, 0), (x + 180, y + 130, 220), WCLIP))
    mdl_box('pad_actionfigures/fig_lilly.md3', 170, 170, 0, 1.6, -60)
    # the pendant lamp
    custom('ceiling_lamp', 0, -900, L.RZ, lit=False)
    # curtains + rod at the window
    custom('curtain_rod', 0, L.RYN - 1, L.WIN[3] + 90, -90)
    for x in (-1180, 1180):
        custom('curtain', x, L.RYN, L.WIN[3] + 80, -90, lit=True)
    custom('window', 0, L.RYN, L.WIN[2])
    # pads from the floor up into the dollhouse
    jumppad(700, 180, 0, (700, 650, L.FL[1]), L.FL[1] + 200, 'pad_ff')
    jumppad(-700, 170, 0, (-700, 660, L.FL[2]), L.FL[2] + 190, 'pad_sf')
    jumppad(-200, 200, 0, (-200, 500, L.FL[3]), L.FL[3] + 270, 'pad_terrace')
    station(300, -700, 0)
    item('ammo_balloony', 560, -1700, 0)
    item('ammo_boaster', 1020, -1000, 0)
    item('ammo_nipper', -900, -1400, 0)
    item('ammo_nipper', 1700, -1550, 0)
    item('ammo_nipper', -1700, -100, 0)
    item('ammo_bubbleg', -100, -1300, 0)
    item('item_armor_shard', 100, -600, 0)
    item('item_armor_shard', -1200, -900, 0)
    item('item_climber', -1450, 1200, 0)
    for (x, y, a) in ((-450, -650, 60), (650, -1250, 120), (-1350, -1650, 45), (1750, -850, 150), (0, -1850, 90), (-1500, 650, 0), (-1600, -1000, 20)):
        spawn(x, y, 0, a)
    route('garden_west', (-900, 1500, L.BOARD_Z), (-1500, 0, 0))
    route('garden_east', (1090, 1500, L.BOARD_Z), (1150, -300, 0))


# =================================================================================================== secret ballroom
def ballroom():
    F = L.BALL
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('ball_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('ball_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('paint_pink'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    for f in M.world[-6].faces:
        if f.tex == T('ball_floor'):
            f.sc = ((x1 - x0) / 512, (y1 - y0) / 512); f.off = ((-x0 / f.sc[0]) % 512, (y1 / f.sc[1]) % 512)
    # mirror panels on the side walls (2u, against the walls)
    for (xa, xb) in ((x0, x0 + 2), (x1 - 2, x1)):
        for yc in (-300, 0, 300):
            A(box((xa, yc - 110, z0 + 60), (xb, yc + 110, z0 + 400), {'side': T('mirror'), 'top': T('gold'), 'bot': T('gold')}))
    custom('chandelier_big', 0, 0, z1 - 0.01, lit=False)
    light(0, 0, z1 - 230, 600, '1 0.9 0.8')
    for (x, y) in ((-400, -400), (400, -400), (-400, 400), (400, 400)):
        light(x, y, z0 + 300, 260, '1 0.8 0.9')
    # the music box with the turning ballerina
    custom('musicbox', 0, 120, z0)
    A(box((-160, -40, z0), (160, 280, z0 + 128), WCLIP))
    M.ent('func_rotating', brushes=[box((-8, 112, z0 + 128), (8, 128, z0 + 144), ORIGIN), box((-4, 116, z0 + 300), (4, 124, z0 + 308), NODRAW_NS)],
          model2=dhlib.IQM['ballerina'], speed=40, spawnflags=0, dmg=0)
    speaker(0, 120, z0 + 200, 'sound/world/misc/wind_chimes.ogg', volume=0.7)
    item('item_padpower', 0, -220, z0)
    item('item_revival', -380, -100, z0)
    item('holdable_killerducks', 380, -100, z0)
    item('ammo_imperius', 0, -420, z0)
    M.ent('misc_teleporter_dest', (0, -330, z0 + 24), targetname='ball_in', angle=90)
    # the way back: a WoP teleporter in the south-west corner -> the garden
    mdl_c('pad_teleporter/padtp_pink.md3', -420, -470, z0, 1.0, 45)
    M.ent('trigger_teleport', brushes=[box((-456, -506, z0 + 2), (-384, -434, z0 + 90), TRIG)], target='ball_out')
    M.ent('misc_teleporter_dest', (200, 1650, L.BOARD_Z + 24), targetname='ball_out', angle=270)
    A(sign_box((-240, y1 - 4, z0 + 380), (240, y1, z0 + 500), T('sign_ball'), 512, 128, facing='s'))


# =================================================================================================== extra pickups, lights
def lights_and_sound():
    # bedroom: soft daylight from the pendant lamp and the room (the sun comes in through the north window)
    for x in (-1700, -560, 560, 1700):
        for y in (-1500, -500, 500, 1500):
            light(x, y, 1500, 1500, '1 0.95 0.88')
    light(0, -900, L.RZ - 520, 1200, '1 0.9 0.75')
    for x in (-600, 0, 600):
        light(x, 250, 300, 260, '1 0.95 0.85')         # into the open back of the house
        light(x, 250, 640, 240, '1 0.95 0.85')
        light(x, 250, 960, 240, '1 0.95 0.85')
    speaker(0, -500, 600, 'sound/world/ambient/floor_creaking.ogg', loop=False, targetname='creak')
    M.ent('func_timer', (0, -500, 700), target='creak', wait=35, random=15, spawnflags=1)


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'jumppad_ns', 'origin', 'water', 'botclip')


def fix_items():
    """nudge items / weapons / spawns that ended up inside a solid or clip brush to the nearest free spot (same height)"""
    sol = []
    for b in M.world + [bb for e in M.ents if e['classname'] not in ('trigger_push', 'trigger_multiple', 'trigger_teleport') for bb in e['_brushes']]:
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


def write_routes():
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @paddollhouse/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_dollhouse.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== main
def extra_models():
    rail_models()


def main():
    dhlib.STATE['out'] = OUT
    TX.make_textures()
    import dh_models
    DH.MODELS = dh_models.make()
    floor_box = bedroom_hull()
    board_and_floor(floor_box)
    house()
    house_rooms(); garden(); bookcase_big(); bed_big(); toy_chest(); tea_party(); play_floor(); ballroom()
    lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (-1800, -1800, 900), angles='14 40 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/paddollhouse/build_dollhouse.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
