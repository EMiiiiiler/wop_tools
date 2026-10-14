#!/usr/bin/env python3
"""Shroom Trip - World of Padman FFA map generator (map 'wop_padshroom').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_shroom.py

Writes <OUT>/maps/wop_padshroom.map, textures/padshroom/*, env/padshroom/* (sky), models/padshroom/*,
scripts/padshroom.shader and scripts/wop_padshroom.arena.

Padman eats the wrong mushroom and wakes up shrunk on a forest floor that will not keep still: giant mushrooms breathe
colour, spores drift round the sky in slow rings, the pond swirls like oil on water. Padman scale (~8u per cm,
catalog models at 1.0 unless scaled up on purpose). x east, y north, ground z 0, sky at z 3200.

  Mother Mushroom   centre: a 1570-tall golden cap. Walk in at the south door; the spore-print disc in the stem is an
                    elevator (func_plat) up to the gill chamber inside the cap (Pumper, Pad shield). A pad in the
                    chamber fires you up through the hatch onto the plateau (Imperius); three skylights drop you back
                    in. Four bouncy pads on the plateau fling you to the stump, the cottage roof, the pond and the log.
  Fly-agaric village  north-west: a big cottage (walk in: Bubble G, Climber; pad to the roof: Balloony) and a small
                    one (walk in: ammo; 16u stairs to its roof: Jumper; a pad on to the big roof).
  Hollow stump      south-west: walk in through the root arch, a pad inside shoots you up the hollow onto the cut top
                    (Boaster); two shelf fungi on the outside are ledges to drop onto (Floater, Boaster ammo).
  Fallen log        south-east: walk through the tunnel (Speedy); pads either side to the mossy top (Splasher). A tiny
                    glowing door inside the log is the SECRET: it takes you to the Void (Pad Power, Revival, Killer
                    Ducks) - a kaleidoscope room with a floating eye; a teleporter brings you back.
  Rainbow pond      north-east: swirling oil-slick water, gentle banks all round (walk out anywhere); Betty on the
                    bottom; crystal rocks with a rainbow waterfall; lily pads and a rubber duck.
  Rainbow snail     south: a giant snail crawling past (cover).
  Fern thicket      west: catalog ferns, Visionless hidden in the middle.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import shroom_textures as TX
import shroom_models as SM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padshroom'
T = lambda n: 'padshroom/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
PCLIP = 'common/playerclip'; BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'moss': (1, 1), 'bank': (1, 1), 'dirt': (0.5, 0.5), 'pebbles': (1, 1), 'planks': (0.5, 0.5), 'rotten': (1, 1),
             'gill_flesh': (1, 1), 'stem_inner': (1, 1), 'house_wall': (1, 1), 'trim': (0.5, 0.5), 'dark': (1, 1), 'sky': (4, 4),
             'water': (1, 1), 'kaleido': (1, 1), 'void_floor': (1, 1), 'rings': (1, 1), 'bark_flat': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '18', '_color': '1 0.85 1', 'gridsize': '96 96 128', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
XW, YN = 2048, 1792                 # playable ground half extents (bank toes)
HX, HY = 2432, 2176                 # sky hull inner half extents
BANK_X = 2240                       # bank slope reaches z BANK_H here (then flat to the hull)
BANK_H = 512
ZSKY, ZBOT = 3200, -512
GROUND_BOT = -256
AB = (-1280, 1060)                  # big fly-agaric cottage
AS = (-300, 1450)                   # small cottage
STC = (-1380, -1120)                # stump centre
LX, LY = 1060, -1250                # log centre (axis along x)
PD = (1200, 960)                    # pond centre
POND_R0, POND_R1, POND_Z1, WATER_Z = 560, 240, -224, -24
VOID_Z0, VOID_Z1, VOID_R = -2240, -1600, 540
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
KEEP_OUT = []                       # (x, y, r) discs where floor decoration must not go


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """(x,y) = where the model's bounding-box centre should land"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, round_n=0, top_cut=4):
    """mdl_c + a weapon-clip box (or n-gon for round things) around the model so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    z1 = oz + b['max'][2] * scale
    if round_n:
        r = (b['max'][0] - b['min'][0]) * scale / 2 * (1 - shrink)
        A(cyl(round(x), round(y), round(r), round(zsurf), round(z1 - top_cut), WCLIP, round_n))
        return e
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - top_cut)), WCLIP))
    return e


def custom(name, x, y, zbase, angle=0, lit=True, mul=1.0, **kw):
    """one of our own MD3s (models/padshroom), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = SM.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=sc, angle=angle, **extra)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex)


def light(x, y, z, val, color='1 0.85 0.75', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd):
    speaker(x, y, z, noise, loop=False, targetname=name)
    M.ent('func_timer', (round(x), round(y), round(z + 40)), target=name, wait=wait, random=rnd, spawnflags=1)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=ang % 360)
    SPOTS['spawn'].append((x, y, floor))


def hfit(b, x0, y0, x1, y1, tw, th, tex):
    """top face(s) with `tex`: exactly one copy of a tw x th texture over the rectangle (north = texture top)"""
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.7: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def jumppad(x, y, z, land, apex, name, glow=True):
    """bouncy mushroom pad (r 34 disc) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of the
    flight measured from the trigger centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down)
    of the way to `land`."""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38
    lx, ly, lz = land
    lz_o = lz + 24
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - lz_o) / 800)
    f = tu / (tu + td)
    tx, ty = x + (lx - x) * f, y + (ly - y) * f
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    if glow: light(x, y, z + 48, 120, '1 0.45 0.9')
    KEEP_OUT.append((x, y, 80))


def sprite(x, y, z0, z1, tex, w, ang=0):
    """thin vertical autosprite2 slab (taller than wide), shader on both broad faces"""
    a = math.radians(ang); dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2; nx, ny = -math.sin(a), math.cos(a)
    q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx * 2, y + dy + ny * 2), (x - dx + nx * 2, y - dy + ny * 2)]
    def tf(n, nx=nx, ny=ny):
        return T(tex) if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
    b = hull([(px, py, zz) for (px, py) in q for zz in (z0, z1)], tf, round_pts=False)
    for f in b.faces:
        if f.tex == T(tex): f.sc = (w / 128, (z1 - z0) / 512); f.off = (0, 0)
    return b


def deco(mn, mx, tex):
    """nonsolid decoration box"""
    d = {'side': NODRAW_NS}
    if isinstance(tex, dict): d.update(tex)
    else: d = {'side': tex, 'top': tex, 'bot': tex}
    return box(mn, mx, d)


# ----------------------------------------------------------------------------------- shells of revolution
def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def ring_seg(cx, cy, k, n, r0, r1, z0a, z1a, z0b, z1b, tex):
    """wedge of a ring band: inner radius r0 spans z0a..z1a, outer radius r1 spans z0b..z1b, angles k*360/n..(k+1)*360/n.
    r0 == 0 gives a pie slice. Vertices sit on the circles (16-gon with a vertex at angle 0)."""
    a0, a1 = k * 360.0 / n, (k + 1) * 360.0 / n
    pts = []
    for a in (a0, a1):
        for (r, za, zb) in ((r0, z0a, z1a), (r1, z0b, z1b)):
            px, py = ang_pt(cx, cy, r, a)
            pts += [(px, py, za), (px, py, zb)]
    return hull(pts, tex, round_pts=False)


def ring_tex(amid, inner=CAULK, outer=CAULK, top=CAULK, bot=CAULK, side=CAULK):
    rx, ry = math.cos(math.radians(amid)), math.sin(math.radians(amid))
    def f(n):
        if n[2] > 0.7: return top
        if n[2] < -0.7: return bot
        d = n[0] * rx + n[1] * ry
        if d > 0.5: return outer
        if d < -0.5: return inner
        return side
    return f


def disc_brush(cx, cy, r, z0, z1, tex, n=16, z1c=None):
    """16-gon (vertex at angle 0) prism; optional apex height z1c at the centre (cone top)"""
    pts = []
    for k in range(n):
        px, py = ang_pt(cx, cy, r, k * 360.0 / n)
        pts += [(px, py, z0), (px, py, z1)]
    if z1c is not None: pts.append((cx, cy, z1c))
    return hull(pts, tex, round_pts=False)


def stem_shell(cx, cy, prof, rin, bands, door, windows=(), tex_in=T('stem_inner'), shrink=6, n=16, out_tex=CAULK):
    """hollow cylinder with a varying outer radius (MD3 profile [(z, r)] minus shrink), door segments
    door=(k0, k1, height), windows [(k, z0, z1)]; bands = z boundaries (must include door/window heights)"""
    k0, k1, dh = door
    for (za, zb) in zip(bands, bands[1:]):
        ra = SM.interp_r(prof, za) - shrink; rb = SM.interp_r(prof, zb) - shrink
        for k in range(n):
            open_ = (k in (k0, k1) and zb <= dh) or any(k == wk and za >= w0 and zb <= w1 for (wk, w0, w1) in windows)
            if open_: continue
            nb_door = (k in (k0 - 1, k1 + 1) and zb <= dh) or any(k in (wk - 1, wk + 1) and za >= w0 and zb <= w1 for (wk, w0, w1) in windows)
            under = (k in (k0, k1) and za == dh) or any(k == wk and za == w1 for (wk, w0, w1) in windows)
            over = any(k == wk and zb == w0 for (wk, w0, w1) in windows)
            amid = (k + 0.5) * 360.0 / n
            tf = ring_tex(amid, inner=tex_in, outer=out_tex, side=tex_in if nb_door else CAULK,
                          bot=tex_in if under else CAULK, top=tex_in if over else CAULK)
            A(ring_seg(cx, cy, k, n, rin, ra, za, zb, za, zb, tf) if ra == rb else
              hull([(px, py, z) for a in (k * 22.5, (k + 1) * 22.5) for (r, z) in ((rin, za), (rin, zb), (ra, za), (rb, zb))
                    for (px, py) in [ang_pt(cx, cy, r, a)]], tf, round_pts=False))


# =================================================================================================== sky hull, ground, banks
def hull_and_ground():
    W = 16
    sk = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((-HX - W, -HY - W, ZBOT - W), (HX + W, HY + W, ZBOT), dict(sk, top=T('sky')), detail=False))
    A(box((-HX - W, -HY - W, ZSKY), (HX + W, HY + W, ZSKY + W), dict(sk, bot=T('sky')), detail=False))
    A(box((-HX - W, HY, ZBOT), (HX + W, HY + W, ZSKY), dict(sk, s=T('sky')), detail=False))
    A(box((-HX - W, -HY - W, ZBOT), (HX + W, -HY, ZSKY), dict(sk, n=T('sky')), detail=False))
    A(box((HX, -HY, ZBOT), (HX + W, HY, ZSKY), dict(sk, w=T('sky')), detail=False))
    A(box((-HX - W, -HY, ZBOT), (-HX, HY, ZSKY), dict(sk, e=T('sky')), detail=False))
    # ground slab with the pond tile and the elevator pit cut out
    pond_tile = (PD[0] - 640, PD[1] - 640, PD[0] + 640, PD[1] + 640)
    pit = (-104, -104, 104, 104)
    gt = {'top': T('moss'), 'side': CAULK, 'bot': CAULK}
    for (x0, y0, x1, y1) in sub_rects((-XW, -YN, XW, YN), [pond_tile, pit]):
        A(box((x0, y0, GROUND_BOT), (x1, y1, 0), gt, detail=False))
    A(box((-104, -104, GROUND_BOT), (104, 104, -16), {'top': T('dark'), 'side': CAULK, 'bot': CAULK}, detail=False))
    # pond: carve the basin out of the tile, fill it with one water frustum
    cut_r = lambda z: POND_R1 + (z - POND_Z1) * (POND_R0 - POND_R1) / (0 - POND_Z1)
    cutter = hull([(x, y, z) for z in (POND_Z1, 16) for (x, y) in ngon(PD[0], PD[1], cut_r(z), 16, 0)], CAULK, round_pts=False)
    tile = box((pond_tile[0], pond_tile[1], GROUND_BOT), (pond_tile[2], pond_tile[3], 0), CAULK, detail=False)
    for b in carve(tile, [cutter]):
        for f in b.faces:
            if f.n[2] > 0.99 and abs(max(p[2] for p in f.pts)) < 0.5: f.tex = T('moss')
            elif f.n[2] < -0.99: f.tex = CAULK
            elif abs(f.n[2]) < 1e-3 and (abs(abs(f.n[0]) - 1) < 1e-6 or abs(abs(f.n[1]) - 1) < 1e-6): f.tex = CAULK
            else: f.tex = T('pebbles')
            f.sc = wopmap.default_scale(f.tex)
        b.detail = False
        A(b)
    wt = lambda n: T('water') if n[2] > 0.99 else T('water_nodraw')
    A(hull([(x, y, z) for z in (POND_Z1, WATER_Z) for (x, y) in ngon(PD[0], PD[1], cut_r(z), 16, 0)], wt, round_pts=False))
    # banks round the edge: steep earth (unwalkable 69 deg), flat top with giant grass, player clip above
    bt = lambda n: T('bank') if n[2] < 0.99 and n[2] > 0.2 else (T('moss') if n[2] >= 0.99 else CAULK)
    for sx in (-1, 1):
        A(hull([(sx * x, y, z) for y in (-YN, YN) for (x, z) in ((XW, 0), (BANK_X, BANK_H), (HX, BANK_H), (HX, GROUND_BOT), (XW, GROUND_BOT))], bt))
    for sy in (-1, 1):
        A(hull([(x, sy * y, z) for x in (-XW, XW) for (y, z) in ((YN, 0), (YN + BANK_X - XW, BANK_H), (HY, BANK_H), (HY, GROUND_BOT), (YN, GROUND_BOT))], bt))
    for sx in (-1, 1):
        for sy in (-1, 1):
            yb = YN + BANK_X - XW
            pts = [(XW, YN, 0), (BANK_X, YN, BANK_H), (XW, yb, BANK_H), (BANK_X, yb, BANK_H), (HX, YN, BANK_H), (HX, HY, BANK_H),
                   (XW, HY, BANK_H), (HX, yb, BANK_H), (BANK_X, HY, BANK_H)]
            pts = pts + [(x, y, GROUND_BOT) for (x, y) in ((XW, YN), (HX, YN), (HX, HY), (XW, HY))]
            A(hull([(sx * x, sy * y, z) for (x, y, z) in pts], bt))
    # nothing stands on the bank tops: player clip from the bank top up to the sky
    for sx in (-1, 1):
        A(box((min(sx * BANK_X, sx * HX), -HY, BANK_H), (max(sx * BANK_X, sx * HX), HY, ZSKY), PCLIP))
    for sy in (-1, 1):
        A(box((-BANK_X, min(sy * (YN + BANK_X - XW), sy * HY), BANK_H), (BANK_X, max(sy * (YN + BANK_X - XW), sy * HY), ZSKY), PCLIP))
    # giant grass clumps on the bank tops
    rng = np.random.default_rng(5)
    yb = YN + BANK_X - XW
    mid = (BANK_X + HX) / 2
    places = [(x, sy * (yb + HY) / 2) for sy in (-1, 1) for x in np.arange(-2050, 2051, 300)]
    places += [(sx * mid, y) for sx in (-1, 1) for y in np.arange(-1800, 1801, 300)]
    for (x, y) in places:
        face = math.degrees(math.atan2(-y, -x)) if abs(abs(x) - mid) < 1 else (270 if y > 0 else 90)
        if abs(abs(x) - mid) < 1: face = 180 if x > 0 else 0
        custom('grass', x + rng.uniform(-20, 20), y + rng.uniform(-20, 20), BANK_H, angle=int(face + rng.uniform(-20, 20)))


# =================================================================================================== the Mother Mushroom
def mother():
    st = T('stem_inner'); gf = T('gill_flesh')
    custom('mother', 0, 0, 0, angle=0)
    KEEP_OUT.append((0, 0, 900))
    # stem shell (south door)
    bands = [0, 40, 120, 240, 500, 800, 1000, SM.M_STEM_TOP]
    stem_shell(0, 0, SM.MOTHER_STEM, SM.MOTHER_IN, bands, SM.MOTHER_DOOR)
    # chamber floor over the shaft (square hole for the elevator) + floor ring
    F0, F1 = SM.M_STEM_TOP, SM.M_FLOOR
    R = SM.MOTHER_IN; H = 104
    poly = [ang_pt(0, 0, R, k * 22.5) for k in range(16)]
    def clip_poly(P, a, b, c):          # keep a*x + b*y <= c
        out = []
        for i in range(len(P)):
            p, q = P[i], P[(i + 1) % len(P)]
            fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
            if fp <= 0: out.append(p)
            if fp * fq < 0:
                t = fp / (fp - fq); out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out
    pieces = [clip_poly(poly, -1, 0, -H), clip_poly(poly, 1, 0, -H),
              clip_poly(clip_poly(clip_poly(poly, 0, -1, -H), 1, 0, H), -1, 0, H),
              clip_poly(clip_poly(clip_poly(poly, 0, 1, -H), 1, 0, H), -1, 0, H)]
    for P in pieces:
        A(hull([(x, y, z) for (x, y) in P for z in (F0, F1)], {'top': T('plat_floor'), 'bot': st, 'side': st}, round_pts=False))
    # cap bands (16 wedges each). profile helpers from shroom_models
    ct, cb = SM.m_ct, SM.m_cb
    n = 16
    for k in range(n):
        am = (k + 0.5) * 22.5
        # floor ring r 260..600 (top = chamber floor)
        for (ra, rb_) in ((R, 340), (340, SM.M_WALL_R)):
            A(ring_seg(0, 0, k, n, ra, rb_, max(cb(ra), F0) if ra > 340 else F0, F1, cb(rb_) if rb_ > 340 else F0, F1,
                       ring_tex(am, inner=st, top=T('plat_floor'))))
        # chamber wall r 600..640 (cap top above it)
        ra, rb_ = SM.M_WALL_R, 640
        A(ring_seg(0, 0, k, n, ra, rb_, cb(ra), ct(ra), cb(rb_), ct(rb_), ring_tex(am, inner=gf)))
        # brim r 640..800, rolled edge 800..836
        A(ring_seg(0, 0, k, n, 640, 800, cb(640), ct(640), cb(800), ct(800), ring_tex(am)))
        A(ring_seg(0, 0, k, n, 800, 836, cb(800), ct(800), 1100, 1120, ring_tex(am)))
        # chamber ceiling under the cone r 360..600 (skylights left open)
        sky = [s for s in SM.M_SKY if s[0] == k]
        ce = lambda r: ct(r) - 44
        if sky:
            _, s0, s1 = sky[0]
            for (ra, rb_) in ((360, s0), (s1, SM.M_WALL_R)):
                A(ring_seg(0, 0, k, n, ra, rb_, ce(ra), ct(ra), ce(rb_), ct(rb_),
                           ring_tex(am, bot=gf, inner=st if ra == s1 else CAULK, outer=st if rb_ == s0 else CAULK)))
        else:
            nbs = any(abs(k - s[0]) == 1 for s in SM.M_SKY)
            A(ring_seg(0, 0, k, n, 360, SM.M_WALL_R, ce(360), ct(360), ce(SM.M_WALL_R), ct(SM.M_WALL_R),
                       ring_tex(am, bot=gf, side=st if nbs else CAULK)))
        # plateau ring r 150..360 (hatch left open)
        if k not in SM.M_HATCH:
            side = st if k in (SM.M_HATCH[0] - 1, SM.M_HATCH[1] + 1) else CAULK
            A(ring_seg(0, 0, k, n, SM.M_PLATEAU_R[0], 360, SM.M_PLAT - 44, SM.M_PLAT, SM.M_PLAT - 44, SM.M_PLAT,
                       ring_tex(am, bot=gf, side=side)))
    A(disc_brush(0, 0, SM.M_PLATEAU_R[0], SM.M_PLAT - 44, SM.M_PLAT, {'bot': gf, 'side': CAULK, 'top': CAULK}))
    # umbo (walkable bump on the plateau)
    for (r0, z0, r1, z1) in ((140, 1460, 120, 1500), (120, 1500, 70, 1540), (70, 1540, 30, 1556)):
        A(hull([(x, y, z0) for (x, y) in [ang_pt(0, 0, r0, k * 22.5) for k in range(16)]] +
               [(x, y, z1) for (x, y) in [ang_pt(0, 0, r1, k * 22.5) for k in range(16)]], CAULK, round_pts=False))
    # elevator: spore-print disc, drawn at the top (Q3 plats are drawn raised), travels 1176 down to the ground pit
    plat = box((-96, -96, F1 - 16), (96, 96, F1), {'top': T('plat'), 'side': T('trim'), 'bot': T('trim')})
    hfit(plat, -96, -96, 96, 96, 256, 256, T('plat'))
    M.ent('func_plat', brushes=[plat], height=F1, speed=300, lip=0, noise='sound/world/plats/start.wav')
    # contents: ground room (health station, ammo), chamber (Pumper, Pad shield, ammo), plateau (Imperius)
    M.ent('station_health', (0, 190, 0), angle=270)
    item('ammo_splasher', -170, -60, 0)
    item('item_armor_shard', 170, -40, 0)
    weapon('pumper', -300, 300, F1, 'green')
    item('item_armor_padshield', 330, 250, F1)
    item('ammo_imperius', 300, -360, F1)
    item('ammo_pumper', -420, -160, F1)
    item('holdable_boomies', 120, 420, F1)
    custom('mycena_b', -300, 120, F1, angle=30, mul=0.7)
    custom('mycena_c', 290, -60, F1, angle=200, mul=0.7)
    weapon('imperius', 230, 70, SM.M_PLAT, 'purple')
    item('ammo_imperius', -230, -40, SM.M_PLAT)
    # hatch pad (chamber -> plateau through the hatch, lands on the cone south of it)
    jumppad(0, -228, F1, (0, -480, ct(480)), 1650, 'hatch')
    # fling pads from the plateau
    fl = [(45, (PD[0] - 100, PD[1] - 100, WATER_Z), 1580, 'fling_pond'),
          (130, (AB[0] + 120, AB[1] - 60, 700), 1720, 'fling_cottage'),
          (215, (STC[0] + 170, STC[1] + 170, 880), 1690, 'fling_stump'),
          (320, (LX - 60, LY, 560), 1690, 'fling_log')]
    for (a, land, apex, nm) in fl:
        px, py = ang_pt(0, 0, 262, a)
        jumppad(px, py, SM.M_PLAT, land, apex, nm)
    # lights: stem shaft, chamber, under the cap
    for z in (160, 560, 960):
        light(0, 0, z, 380, '0.6 0.9 1')
    for (a, r) in ((30, 400), (150, 400), (270, 420)):
        x, y = ang_pt(0, 0, r, a); light(x, y, F1 + 110, 260, '1 0.55 0.95')
    for k in range(6):
        x, y = ang_pt(0, 0, 640, k * 60 + 15); light(x, y, 860, 650, '0.75 0.45 1')
    speaker(0, 0, 600, 'sound/world/machine/portal_idle.ogg', volume=0.35)
    speaker(0, 0, F1 + 120, 'sound/world/ambient/slime_bubbling.ogg', volume=0.4)


# =================================================================================================== fly-agaric cottages
def cottage(c, D, name, bands):
    cx, cy = c
    custom(name, cx, cy, 0, angle=0)
    stem_shell(cx, cy, D['stem'], D['rin'], bands, D['door'], D['windows'], tex_in=T('house_wall'))
    # floor
    b = disc_brush(cx, cy, D['rin'] - 6, 0, 8, {'top': T('planks'), 'side': T('trim'), 'bot': CAULK})
    A(b)
    # cap: centre cone over the room, then rings following the top profile; underside = 'under' line
    top = D['top']; h = D['h']
    (ru0, zu0), (ru1, zu1) = D['under']
    zt = lambda r: float(np.interp(r, [p[0] for p in top], [p[1] for p in top]))
    zb = lambda r: h if r <= ru0 else zu0 + (r - ru0) * (zu1 - zu0) / (ru1 - ru0)
    rc = top[1][0]
    A(disc_brush(cx, cy, rc, h, zt(rc), {'bot': T('house_wall'), 'side': CAULK, 'top': CAULK}, z1c=zt(0) if zt(0) > zt(rc) + 0.5 else None))
    rs = [p[0] for p in top[1:]]
    for k in range(16):
        am = (k + 0.5) * 22.5
        for (ra, rb_) in zip(rs, rs[1:]):
            A(ring_seg(cx, cy, k, 16, ra, rb_, zb(ra), zt(ra), zb(rb_), zt(rb_), ring_tex(am)))
    KEEP_OUT.append((cx, cy, top[-1][0] + 40))


def village():
    # big cottage
    bands = [0, 40, 110, 200, 240, 304, 440]
    cottage(AB, SM.AMA_BIG, 'amanita_big', bands)
    cx, cy = AB
    weapon('bubbleg', cx - 40, cy + 40, 8, 'blue')
    item('ammo_boaster', cx + 100, cy - 90, 8)
    item('item_climber', cx - 120, cy - 60, 8)
    custom('lamp', cx + 90, cy + 110, 8)
    mdl_c('pad_ddmix/chess/chess_white_king.md3', cx + 140, cy + 20, 8, 1.0, 0)
    light(cx, cy, 300, 450, '1 0.75 0.5')
    # roof: Balloony; pad from the ground (south-east, toward the plaza)
    zt = lambda r: float(np.interp(r, [p[0] for p in SM.AMA_BIG['top']], [p[1] for p in SM.AMA_BIG['top']]))
    weapon('balloony', cx, cy, zt(0), 'green')
    item('ammo_boaster', cx - 160, cy - 110, zt(170))
    jx, jy = ang_pt(cx, cy, 820, 320)
    lx, ly = ang_pt(cx, cy, 300, 320)
    jumppad(jx, jy, 0, (lx, ly, zt(300)), 1000, 'cottage_roof')
    light(cx, cy, 950, 500, '1 0.8 0.9')
    # small cottage
    bands = [0, 40, 96, 100, 176, 200, 260]
    cottage(AS, SM.AMA_SMALL, 'amanita_small', bands)
    sx, sy = AS
    item('ammo_pumper', sx + 40, sy + 50, 8)
    item('ammo_balloony', sx - 60, sy - 30, 8)
    custom('lamp', sx - 20, sy + 80, 8, angle=0, mul=0.7)
    light(sx, sy, 180, 300, '1 0.75 0.5')
    # 16u stairs from the east up to the small cap rim (lip top 288)
    A(stairs(sx + 362, sy - 64, sx + 362 + 18 * 32, sy + 64, 0, 288, 'w', {'top': T('planks'), 'side': T('trim')}))
    KEEP_OUT.append((sx + 362 + 9 * 32, sy, 340))
    ztS = lambda r: float(np.interp(r, [p[0] for p in SM.AMA_SMALL['top']], [p[1] for p in SM.AMA_SMALL['top']]))
    item('item_jumper', sx - 100, sy + 60, ztS(116))
    item('ammo_boaster', sx + 120, sy - 90, ztS(150))
    # pad on the small roof to the big roof
    jumppad(sx - 40, sy - 100, ztS(0), (cx + 160, cy + 40, zt(165)), 980, 'small_to_big')
    # flowers + sunflowers round the village (catalog)
    mdl_c('pad_sunflower/pad_sunflower_l.md3', -1880, 1640, 0, 1.6, 200)
    mdl_c('pad_sunflower/pad_sunflower_l.md3', -760, 1680, 0, 1.6, 90)
    for (x, y, s, a) in ((cx + 760, cy - 300, 2.2, 30), (cx - 300, cy - 720, 2.2, 140), (sx + 160, sy - 460, 2.0, 300)):
        mdl_c('pad_ddmix/plants/flower_yellow.md3', x, y, 0, s, a)
    for (x, y, s, a) in ((cx + 520, cy - 640, 2.4, 0), (sx - 240, sy - 520, 2.0, 80), (cx - 560, cy - 360, 2.2, 200)):
        mdl_c('pad_ddmix/plants/flower_pink.md3', x, y, 0, s, a)
    speaker(cx + 300, cy - 300, 400, 'sound/world/misc/wind_chimes.ogg', volume=0.6)


# =================================================================================================== hollow stump
def stump():
    cx, cy = STC
    D = SM.STUMP
    custom('stump', cx, cy, 0, angle=0)
    KEEP_OUT.append((cx, cy, 620))
    rt = T('rotten')
    stem_shell(cx, cy, D['prof'], D['rin'], [0, 60, 160, 300, 400, D['h']], D['door'], tex_in=rt, shrink=10)
    # the shell tops are the outer deck ring: give them the cut-wood rings
    span = 872
    for b in M.world[-16 * 5:]:
        for f in b.faces:
            if f.n[2] > 0.99 and abs(max(p[2] for p in f.pts) - D['h']) < 0.5:
                f.tex = T('rings')
        hfit(b, cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2, 256, 256, T('rings'))
    # deck over the hollow: centre disc, ring 100..250 with a hole (segments 9, 10), ring 250..330
    z0, z1 = D['h'] - 40, D['h']
    deck = []
    deck.append(disc_brush(cx, cy, 100, z0, z1, {'top': T('rings'), 'bot': rt, 'side': rt}))
    for k in range(16):
        am = (k + 0.5) * 22.5
        if k not in (9, 10):
            side = rt if k in (8, 11) else CAULK
            deck.append(ring_seg(cx, cy, k, 16, 100, 250, z0, z1, z0, z1, ring_tex(am, top=T('rings'), bot=rt, side=side)))
        deck.append(ring_seg(cx, cy, k, 16, 250, D['rin'], z0, z1, z0, z1,
                             ring_tex(am, top=T('rings'), bot=rt, inner=rt if k in (9, 10) else CAULK)))
    for b in deck:
        hfit(b, cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2, 256, 256, T('rings'))
        A(b)
    # pad inside -> up the hollow, through the hole, onto the deck
    px, py = ang_pt(cx, cy, 150, 225)
    lx, ly = ang_pt(cx, cy, 300, 225)
    jumppad(px, py, 0, (lx, ly, D['h']), 1200, 'stump_up')
    # inside: glowing mycena, ammo
    custom('mycena_a', *ang_pt(cx, cy, 170, 120), 0, angle=40)
    custom('mycena_c', *ang_pt(cx, cy, 190, 320), 0, angle=10)
    item('ammo_balloony', *ang_pt(cx, cy, 120, 20), 0)
    item('ammo_imperius', *ang_pt(cx, cy, 200, 180), 0)
    light(cx, cy, 200, 420, '0.4 1 0.9'); light(cx, cy, 620, 300, '0.5 0.9 1')
    # deck: Boaster, ammo
    weapon('boaster', *ang_pt(cx, cy, 180, 60), D['h'], 'orange')
    item('ammo_betty', *ang_pt(cx, cy, 300, 0), D['h'])
    item('ammo_balloony', *ang_pt(cx, cy, 340, 120), D['h'])
    mdl_c('pad_fruits/hazelnut.md3', *ang_pt(cx, cy, 300, 160), D['h'], 9.0, 30)
    light(cx, cy, D['h'] + 250, 400, '1 0.85 0.8')
    # shelf fungi on the outside: walkable ledges (drop onto them from the deck)
    for (a, ztop, cls) in ((150, 560, 'holdable_floater'), (205, 330, 'ammo_boaster')):
        ox, oy = ang_pt(cx, cy, 452, a)
        custom('bracket', ox, oy, ztop - 30, angle=a)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        loc = [(14, -96), (14, 96), (120, 150), (186, 80), (198, 0), (186, -80), (120, -150)]
        pts = [(ox + lx_ * ca - ly_ * sa, oy + lx_ * sa + ly_ * ca) for (lx_, ly_) in loc]
        A(hull([(x, y, z) for (x, y) in pts for z in (ztop - 40, ztop)], {'top': WCLIP, 'side': WCLIP, 'bot': WCLIP}, round_pts=False))
        ix, iy = ang_pt(cx, cy, 452 + 100, a)
        item(cls, ix, iy, ztop)
    speaker(cx, cy, 300, 'sound/world/animal/cricket_chirp2.ogg', volume=0.5)


# =================================================================================================== fallen log
def log_():
    R, RI, L = SM.LOG_R, SM.LOG_IN, SM.LOG_L
    x0, x1 = LX - L / 2, LX + L / 2
    custom('log', LX, LY, 0, angle=0)
    KEEP_OUT.append((LX, LY, 820)); KEEP_OUT.append((LX - 500, LY, 400)); KEEP_OUT.append((LX + 500, LY, 400))
    rt = T('rotten')
    P = lambda r, phi: (LY + r * math.cos(math.radians(phi)), R + r * math.sin(math.radians(phi)))
    def logtex(phim, inner=rt):
        ry, rz = math.cos(math.radians(phim)), math.sin(math.radians(phim))
        def f(n):
            if abs(n[0]) > 0.9: return T('rings')
            d = n[1] * ry + n[2] * rz
            if d > 0.5: return CAULK
            if d < -0.5: return inner
            return CAULK
        return f
    for k in list(range(14, 16)) + list(range(0, 10)):
        p0, p1 = k * 22.5, (k + 1) * 22.5
        pts = []
        for phi in (p0, p1):
            for r in (RI, R):
                y, z = P(r, phi)
                pts += [(x0, y, z), (x1, y, z)]
        A(hull(pts, logtex((p0 + p1) / 2), round_pts=False))
    # floor: the bottom of the log below the chord z LOG_FLOOR
    pts = []
    for phi in (225, 247.5, 270, 292.5, 315):
        y, z = P(R, phi); pts += [(x0, y, z), (x1, y, z)]
    for phi in (225, 315):
        y, z = P(RI, phi); pts += [(x0, y, z), (x1, y, z)]
    fl = hull(pts, lambda n: rt if n[2] > 0.99 else (T('rings') if abs(n[0]) > 0.9 else CAULK), round_pts=False)
    A(fl)
    fz = P(RI, 225)[1]
    # ramps up to the tunnel floor at both ends
    A(ramp(x0 - 300, LY - 140, x0, LY + 140, 0, 0, fz, 'e', {'top': T('dirt'), 'side': T('dirt'), 'bot': CAULK}))
    A(ramp(x1, LY - 140, x1 + 280, LY + 140, 0, 0, fz, 'w', {'top': T('dirt'), 'side': T('dirt'), 'bot': CAULK}))
    # inside: Speedy, ammo, little lights, mycena
    item('item_speedy', LX + 300, LY, fz)
    item('ammo_imperius', LX - 420, LY, fz)
    item('ammo_betty', LX + 560, LY - 40, fz)
    for xx in (LX - 450, LX, LX + 450):
        light(xx, LY, 330, 280, '0.45 1 0.85')
    # secret: the tiny glowing door on the north side of the tunnel
    dx0, dx1 = LX - 60, LX + 20
    door = box((dx0, LY + 120, fz), (dx1, LY + 132, fz + 150), {'s': T('fairy_door'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS})
    for f in door.faces:
        if f.tex == T('fairy_door'): fit_face(f, dx0, dx1, fz, fz + 150, 128, 256)
    A(door)
    M.ent('trigger_multiple', brushes=[box((dx0 - 30, LY + 40, fz), (dx1 + 30, LY + 100, fz + 80), TRIG)], target='secret_snd', wait=6)
    speaker((dx0 + dx1) / 2, LY + 80, fz + 60, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('trigger_teleport', brushes=[box((dx0 - 10, LY + 101, fz), (dx1 + 10, LY + 118, fz + 120), TRIG)], target='void_in')
    light((dx0 + dx1) / 2, LY + 60, fz + 90, 140, '0.5 1 0.9')
    # top: Splasher; pads from both sides
    top = R * 2
    weapon('splasher', LX, LY, top, 'orange')
    item('ammo_splasher', LX - 520, LY, top - 1)
    item('ammo_bubbleg', LX + 520, LY + 30, top - 1)
    jumppad(LX + 60, LY + 560, 0, (LX + 120, LY + 30, top), top + 220, 'log_north')
    jumppad(LX - 360, LY - 470, 0, (LX - 300, LY - 30, top), top + 220, 'log_south')
    light(LX, LY, top + 260, 420, '1 0.85 0.9')
    timer_sound(LX, LY, 400, 'sound/world/animal/fly_crazy.ogg', 'flies', 40, 20)


# =================================================================================================== pond
def pond():
    cx, cy = PD
    KEEP_OUT.append((cx, cy, POND_R0 + 60))
    weapon('betty', cx, cy, POND_Z1, 'black')
    item('ammo_betty', cx + 110, cy - 90, POND_Z1)
    item('ammo_bubbleg', cx - 650, cy - 120, 0)
    item('ammo_pumper', cx + 300, cy - 720, 0)
    for (x, y, z) in ((cx - 300, cy + 200, -300), (cx + 250, cy + 120, -300), (cx, cy - 280, -300)):
        light(x, y, -60, 300, '0.4 0.9 1')
    light(cx, cy, 300, 500, '0.6 1 0.95')
    # lily pads + duck on the water
    for (x, y, s, a) in ((cx - 200, cy - 140, 1.4, 20), (cx + 220, cy + 210, 1.2, 140)):
        mdl_c('pad_ddmix/plants/water_lily.md3', x, y, WATER_Z, s, a)
    mdl_c('pad_ducks/pad_duck.md3', cx + 120, cy - 260, WATER_Z, 1.2, 230)
    # crystal rocks + rainbow waterfall (north-east)
    rx, ry, rs = 1790, 1600, 0.5
    path, sc, zo = SM.PLACE['rocks']
    M.model(path, (rx, ry, zo), scale=sc * rs, angle=0, spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5)
    pts = []
    for (bx, by, a, b, h) in ((0, 0, 300, 260, 300), (260, 120, 220, 200, 230), (-240, 140, 210, 180, 210), (90, -200, 200, 170, 170), (-120, -160, 160, 150, 140)):
        for (x, y) in ngon(rx + bx * rs, ry + by * rs, min(a, b) * rs * 0.8, 8):
            pts.append((x, y, 0))
        for (x, y) in ngon(rx + bx * rs, ry + by * rs, min(a, b) * rs * 0.45, 8):
            pts.append((x, y, h * rs * 0.8))
    A(hull(pts, WCLIP))
    KEEP_OUT.append((rx, ry, 300))
    A(sprite(rx - 170, ry - 120, 0, 250, 'waterfall', 90, 45))
    speaker(rx - 170, ry - 140, 120, 'sound/world/ambient/water_falling.ogg', volume=0.6)
    speaker(cx, cy, 0, 'sound/world/ambient/water_rippling.ogg', volume=0.5)
    M.ent('station_health', (cx - 680, cy - 260, 0), angle=30)
    KEEP_OUT.append((cx - 680, cy - 260, 90))


# =================================================================================================== the Void (secret)
def void_room():
    z0, z1, R = VOID_Z0, VOID_Z1, VOID_R
    W = 32
    kz = T('kaleido')
    n = 8
    for k in range(n):
        am = (k + 1) * 45
        A(hull([(x, y, z) for a in (k * 45 + 22.5, (k + 1) * 45 + 22.5) for r in (R, R + W) for (x, y) in [ang_pt(0, 0, r, a)] for z in (z0, z1)],
               ring_tex(am, inner=kz), detail=False, round_pts=False))
    A(hull([(x, y, z) for (x, y) in [ang_pt(0, 0, R + W, k * 45 + 22.5) for k in range(8)] for z in (z0 - W, z0)],
           {'top': T('void_floor'), 'side': CAULK, 'bot': CAULK}, detail=False, round_pts=False))
    A(hull([(x, y, z) for (x, y) in [ang_pt(0, 0, R + W, k * 45 + 22.5) for k in range(8)] for z in (z1, z1 + W)],
           {'bot': kz, 'side': CAULK, 'top': CAULK}, detail=False, round_pts=False))
    for f in M.world[-2].faces:
        if f.tex == T('void_floor'): f.sc = (2 * (R + W) / 512, 2 * (R + W) / 512); f.off = (((R + W) / f.sc[0]) % 512, ((R + W) / f.sc[1]) % 512)
    # sign on the north wall
    yw = R * math.cos(math.radians(22.5))
    sb = sign_box((-190, yw - 30, z0 + 380), (190, yw - 26, z0 + 475), T('sign_void'), 512, 128, back=NODRAW_NS, facing='s')
    A(sb)
    M.ent('misc_teleporter_dest', (0, -360, z0 + 24), targetname='void_in', angle=90)
    item('item_padpower', 0, 200, z0)
    item('item_revival', -260, 60, z0)
    item('holdable_killerducks', 260, 60, z0)
    item('ammo_imperius', -200, -220, z0)
    item('ammo_splasher', 200, -220, z0)
    # the floating eye (func_rotating, origin brush at its centre)
    ez = z0 + 330
    M.ent('func_rotating', brushes=[box((-8, -8, ez - 8), (8, 8, ez + 8), ORIGIN), box((-4, -4, ez - 4), (4, 4, ez + 4), NODRAW_NS)],
          model2=SM.PLACE['eye'][0], speed=25, spawnflags=0, dmg=0)
    # exit teleporter: pad model on the floor at the north, trigger above it
    mdl_c('pad_teleporter/padtp_purple.md3', 0, 380, z0, 1.0, 0)
    M.ent('trigger_teleport', brushes=[box((-36, 330, z0 + 2), (36, 430, z0 + 90), TRIG)], target='void_out')
    M.ent('misc_teleporter_dest', (380, -880, 24), targetname='void_out', angle=0)
    light(0, 0, z0 + 520, 600, '0.9 0.6 1'); light(0, 0, z0 + 120, 300, '0.6 1 0.9')
    speaker(0, 0, z0 + 300, 'sound/world/machine/portal_idle.ogg', volume=0.8)
    speaker(0, 0, z0 + 300, 'sound/world/misc/strange_signal.ogg', volume=0.5)


# =================================================================================================== creatures + props
def snail():
    x, y = -320, -1440
    custom('snail', x, y, 0, angle=0)
    KEEP_OUT.append((x, y, 520))
    A(box((x - 400, y - 110, 0), (x + 380, y + 110, 100), WCLIP))
    A(hull([(x + px, y + py, z) for (px, z) in ((320, 100), (560, 100), (560, 250), (460, 250)) for py in (-70, 70)], WCLIP))
    pts = []
    for k in range(10):
        a = math.radians(k * 36)
        px, pz = -40 + 320 * math.cos(a), 300 + 320 * math.sin(a)
        if pz >= 100: pts += [(x + px, y + py, pz) for py in (-120, 120)]
    pts += [(x - 40 + s * math.sqrt(320 ** 2 - 200 ** 2), y + py, 100) for s in (-1, 1) for py in (-120, 120)]
    A(hull(pts, WCLIP))
    item('ammo_pumper', x + 120, y - 280, 0)
    item('ammo_bubbleg', x - 300, y + 260, 0)


def frog_():
    x, y = 640, -760
    custom('frog', x, y, 0, angle=150)
    A(box((x - 120, y - 120, 0), (x + 120, y + 120, 120), WCLIP))
    KEEP_OUT.append((x, y, 200))


def puffballs():
    rng = np.random.default_rng(11)
    sites = [(-760, -380, 1.6), (-760, 260, 1.3), (520, 420, 1.5), (880, -180, 1.2), (-1080, 180, 1.8), (1500, -380, 1.5),
             (1760, 120, 1.3), (420, -1620, 1.3), (-1700, 520, 1.4), (-1150, -430, 1.2), (300, 860, 1.2), (-180, 900, 1.5),
             (1300, -760, 1.3), (-1650, -320, 1.2), (900, 1630, 1.2), (-820, 1700, 1.1)]
    r0, h0 = SM.PUFF
    for (x, y, s) in sites:
        path, sc, zo = SM.PLACE['puffball']
        M.model(path, (x, y, 0), scale=round(sc * s, 3), angle=int(rng.uniform(0, 360)), spawnflags=4, _castshadows=1, _lightmapscale=0.5)
        r, h = r0 * s, h0 * s
        for (fa, za, fb, zb) in ((0.6, 0, 0.88, 0.22), (0.88, 0.22, 0.94, 0.5), (0.94, 0.5, 0.8, 0.82), (0.8, 0.82, 0.4, 0.96)):
            A(frustum(x, y, r * fa, round(h * za), r * fb, round(h * zb), WCLIP, 12))
        KEEP_OUT.append((x, y, r + 40))


def fairy_ring():
    """glowing bonnet clusters scattered round the Mother (decor, no collision) + in nooks"""
    rng = np.random.default_rng(17)
    for k in range(18):
        a = k * 20 + rng.uniform(-6, 6); r = 1150 + rng.uniform(-60, 60)
        x, y = ang_pt(0, 0, r, a)
        if any(math.hypot(x - kx, y - ky) < kr + 110 for (kx, ky, kr) in KEEP_OUT): continue
        custom('mycena_' + 'abc'[k % 3], x, y, 0, angle=int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 110))


def scatter():
    """catalog decoration (ferns, grass, flowers, leaves, nuts, gummy bears, spiders) with collision where it is big"""
    rng = np.random.default_rng(23)
    def free(x, y, r):
        return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT) and abs(x) < XW - r and abs(y) < YN - r
    # fern thicket (west) with Visionless in the middle
    for (x, y, s, a) in ((-1640, -40, 1.5, 10), (-1560, 330, 1.4, 120), (-1700, 620, 1.3, 250), (-1520, -380, 1.4, 300)):
        mdl_c('pad_ddmix/plants/fern.md3', x, y, 0, s, a)
        KEEP_OUT.append((x, y, 120))
    item('item_visionless', -1720, 160, 0)
    item('ammo_betty', -1560, -120, 0)
    # gummy bears (trip candy): lying ones as low cover, standing ones as tall cover
    for (x, y, s, a, nm) in ((-560, -1040, 2.2, 30, 'ldredbear'), (380, -1820 + 400, 2.4, 150, 'ldgreenbear'), (1640, -900, 2.4, 80, 'ldyellowbear'),
                             (-1130, 520, 2.0, 210, 'ldorangebear'), (240, 1180, 2.0, 300, 'ldredbear')):
        if free(x, y, 180): solid_mdl('gummybears/' + nm + '.md3', x, y, 0, s, a); KEEP_OUT.append((x, y, 220))
    for (x, y, s, a, nm) in ((1480, 180, 2.4, 200, 'redbear'), (-880, -160, 2.2, 20, 'greenbear'), (720, 1640 - 300, 2.0, 250, 'yellowbear')):
        if free(x, y, 140): solid_mdl('gummybears/' + nm + '.md3', x, y, 0, s, a); KEEP_OUT.append((x, y, 160))
    # nuts on the floor
    for (x, y, s, a, nm) in ((-420, -620, 12, 40, 'hazelnut'), (1820, -1320 + 100, 12, 10, 'walnut'), (-1500, 920 - 700, 11, 70, 'hazelnut'),
                             (420, -1250 + 650, 12, 120, 'walnut')):
        if free(x, y, 160):
            solid_mdl('pad_fruits/' + nm + '.md3', x, y, 0, s, a); KEEP_OUT.append((x, y, 180))
    # spiders by the stump
    for (x, y, s, a) in ((-900, -1500, 7, 60), (-1900, -700, 6, 200)):
        if free(x, y, 160): mdl_c('spider/spiderf.md3', x, y, 0, s, a); KEEP_OUT.append((x, y, 170))
    # fallen maple leaves (thin, walk-through) in autumn tones
    n_leaf = 0
    for _ in range(80):
        x, y = rng.uniform(-1900, 1900), rng.uniform(-1650, 1650)
        if not free(x, y, 130): continue
        mdl_c('pad_maple/pad_maple.md3', x, y, 0, 4.5, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 140)); n_leaf += 1
        if n_leaf >= 10: break
    # grass tufts + tulips (catalog) scattered
    for _ in range(60):
        x, y = rng.uniform(-1950, 1950), rng.uniform(-1700, 1700)
        if not free(x, y, 120): continue
        if rng.random() < 0.6: mdl_c('pad_ddmix/trashcan/grass.md3', x, y, 0, 2.5, int(rng.uniform(0, 360)))
        else: mdl_c('pad_ddmix/plants/tulip1.md3', x, y, 0, 2.2, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 120))
    # spore haze sprites drifting low over the plaza
    for (x, y) in ((-600, -600), (650, 300), (-400, 700), (1500, -1000), (-1600, 1000)):
        A(sprite(x, y, 120, 520, 'haze', 220))


def items_misc():
    item('ammo_nipper', -520, -260, 0)
    item('ammo_nipper', 940, 520, 0)
    item('ammo_nipper', -1500, 1500 - 900, 0)
    item('item_armor_shard', 420, -420, 0)
    item('item_armor_shard', -420, 420, 0)
    item('item_armor_shard', 1660, -1600 + 100, 0)
    item('ammo_balloony', 1700, -200, 0)
    item('ammo_splasher', 700, 1400, 0)
    item('ammo_bubbleg', -980, -620, 0)
    item('ammo_pumper', -1200, 300, 0)
    item('ammo_boaster', 200, -620, 0)
    item('holdable_bambam', 1600, 380, 0)


def spawns():
    for (x, y, a) in ((-560, -240, 30), (700, -320, 150), (-200, 620, 270), (480, 640, 225), (-1800, -1650, 45), (1500, -1680, 135),
                      (-1150, -150, 0), (1150, 140, 180), (-1650, 1620 - 100, 315), (1850, 1500 - 900, 200), (0, -980, 90), (-420, 1050, 0),
                      (1840, -820, 160), (-850, -1600, 80)):
        spawn(x, y, 0, a)


def lights_and_sound():
    # soft fill over the open ground (the sky does most of the work)
    for (x, y) in ((-1300, -300), (1300, -300), (-300, -1300), (300, 1300), (1500, 1500 - 300), (-1500, -1500 + 200)):
        light(x, y, 900, 700, '1 0.75 0.95')
    speaker(0, 0, 1800, 'sound/world/ambient/wind_night.ogg', volume=0.4)
    timer_sound(-1800, 0, 600, 'sound/world/animal/bird_owl1.ogg', 'owl', 45, 25)
    timer_sound(1800, -1500, 600, 'sound/world/misc/strange_signal.ogg', 'signal', 60, 30)
    timer_sound(0, 1700, 600, 'sound/world/animal/bird_owl2.ogg', 'owl2', 55, 25)


def spores():
    """glowing spores circling the Mother cap (func_rotating, IQM model2)"""
    z0 = 1500
    path = SM.spores_iqm(z0)
    M.ent('func_rotating', brushes=[box((-8, -8, z0 - 8), (8, 8, z0 + 8), ORIGIN), box((-4, -4, z0 + 140), (4, 4, z0 + 148), NODRAW_NS)],
          model2=path, speed=6, spawnflags=0, dmg=0)


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    hull_and_ground(); mother(); village(); stump(); log_(); pond(); void_room(); snail(); frog_(); puffballs()
    fairy_ring(); scatter(); items_misc(); spawns(); lights_and_sound(); spores()
    M.ent('info_player_intermission', (-1500, -1500, 1400), angles='18 45 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/padshroom/build_shroom.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
