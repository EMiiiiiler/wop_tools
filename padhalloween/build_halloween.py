#!/usr/bin/env python3
"""Pumpkin Hollow - World of Padman FFA map generator (map 'wop_padhalloween').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_halloween.py

Writes <OUT>/maps/wop_padhalloween.map, textures/padhalloween/*, models/padhalloween/*, env/padhalloween/*,
scripts/padhalloween.shader and scripts/wop_padhalloween.arena.

Halloween night in a hollow ringed by dark banks and dead woods, a harvest moon (with a witch crossing it) behind
the haunted manor. ~64u per metre, giant fantasy pumpkins. x east, y north, ground z 0.

  Blackwood Manor   north: Second Empire house - porch, hall, parlour (fireplace, piano), dining room, stairs to the
                    bedroom and library, balcony on the porch roof, pad to the mansard roof deck, stairs into the
                    cupola (Imperius). Bats circle the cupola, a bat weathervane turns on top.
  Graveyard         north-west: iron fence and gates, rows of headstones, a ghost drifting between them, ground mist,
                    the mausoleum - stairs down into the crypt (Pumper). SECRET: step into the open coffin at the west
                    end of the crypt -> the witch's lair.
  Pumpkin patch     north-east: the Great Pumpkin - walk in through its carved mouth, a pad shoots you up through the
                    lid hole onto its top (Balloony); pumpkins, hay, a scarecrow.
  Hanging tree      centre: a giant dead oak with a spiral plank stair round the trunk up to the treehouse deck (Betty)
                    and a hut (pad to its roof); a tyre swing.
  Witch's cottage   south-west: walk in (Bubble G), pad onto the roof ridge (Speedy); the big cauldron bubbling on its
                    fire - a pad drops you into the brew, Splasher on the bottom, steps inside lead back up to the rim.
  Corn maze         south-east: Boaster on the stage in the middle, a scarecrow watching.
  Gate plaza        south: the stone gate with its iron arch, the hearse, the bonfire to the west, the pumpkin stand
                    and hay wagon to the east.
  Witch's lair      SECRET, sealed under the world: rune circle, crystal ball, potion shelves, bats; Pad Power,
                    Revival, Killer Ducks; a teleporter back to the gate.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import hw_textures as TX
import hwlib
import hw_models as HM
import hw_houses as HH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padhalloween'
T = lambda n: 'padhalloween/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'grass': (1, 1), 'leafbed': (1, 1), 'dirt': (0.5, 0.5), 'cobble': (0.5, 0.5), 'bank': (1, 1), 'stone': (0.5, 0.5),
             'stone_dark': (0.5, 0.5), 'flagstone': (0.5, 0.5), 'brick': (0.5, 0.5), 'wallpaper': (0.5, 0.5), 'wallpaper_g': (0.5, 0.5),
             'floor_wood': (0.5, 0.5), 'porch_wood': (0.5, 0.5), 'planks': (0.5, 0.5), 'planks_v': (0.5, 0.5), 'ceiling': (0.5, 0.5),
             'carpet': (0.5, 0.5), 'tin': (0.5, 0.5), 'plaster': (0.5, 0.5), 'hay': (0.5, 0.5), 'lair_wall': (0.5, 0.5),
             'lair_floor': (0.5, 0.5), 'earth_dark': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '20', '_color': '0.7 0.7 1', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '1.5'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
KEEP_OUT = []                       # (x, y, r) discs where floor decoration must not go
ROUTES = []


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.15, round_n=0, top_cut=4):
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    z1 = oz + b['max'][2] * scale
    if round_n:
        r = min(b['max'][0] - b['min'][0], b['max'][1] - b['min'][1]) * scale / 2 * (1 - shrink)
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
    """one of our own MD3s (models/padhalloween), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = hwlib.PLACE[name] if isinstance(name, str) else name
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, **extra)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex, round_pts=False)


def light(x, y, z, val, color='1 0.6 0.25', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
    M.ent('func_timer', (round(x), round(y), round(z + 400)), target=name, wait=wait, random=rnd, spawnflags=1)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))
    KEEP_OUT.append((x, y, 40))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))
    KEEP_OUT.append((x, y, 50))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((x, y, floor))
    KEEP_OUT.append((x, y, 60))


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)
    KEEP_OUT.append((x, y, 100))


def jumppad(x, y, z, land, apex, name, glow=True):
    """pumpkin-swirl pad (r 34 disc) + trigger_push + target_position (AimAtTarget: the target is the apex, measured
    from the trigger centre; it sits t_up/(t_up+t_down) of the way to `land`)"""
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
    if glow: light(x, y, z + 48, 120, '1 0.55 0.2')
    KEEP_OUT.append((x, y, 80))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


ang_pt = L.ang_pt


def ring_seg(cx, cy, a0, a1, r0, r1, z0a, z1a, z0b, z1b, tex):
    """wedge between angles a0..a1 (deg) and radii r0 (z range z0a..z1a) .. r1 (z0b..z1b)"""
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


def disc_brush(cx, cy, r, z0, z1, tex, n=16):
    return hull([(px, py, z) for (px, py) in ngon(cx, cy, r, n, 0) for z in (z0, z1)], tex, round_pts=False)


def rbx(cx, cy, ang, u0, u1, v0, v1, z0, z1, tex):
    """box in a rotated frame: u along `ang` (deg), v to its left"""
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
    pts = [(cx + ux * u + vx * v, cy + uy * u + vy * v, z) for u in (u0, u1) for v in (v0, v1) for z in (z0, z1)]
    return hull(pts, tex, round_pts=False)


def ball_clip(x, y, z0, r, h=None, n=12):
    """weapon-clip polyhedron approximating a pumpkin/ball of radius r (height h) resting on z0"""
    h = h or 2 * r
    pts = []
    for ph in np.linspace(-math.pi / 2 + 0.35, math.pi / 2 - 0.3, 5):
        rr = r * math.cos(ph) * 0.9
        for (px, py) in ngon(x, y, max(rr, 4), n):
            pts.append((px, py, z0 + h / 2 + h / 2 * math.sin(ph) * 0.92))
    pts += [(x, y, z0 + 2)]
    A(hull(pts, WCLIP, round_pts=False))


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


def sign_post(x, y, tex, w, h, facing, z0=96, tw=512, th=256):
    """sign board on a post (board brush + post brush)"""
    hw = w / 2
    if facing in 'ns':
        A(sign_box((round(x - hw), round(y - 4), z0), (round(x + hw), round(y + 4), z0 + h), T(tex), tw, th, facing=facing, back=T('wood_dark'),
                   edge=T('wood_dark')))
    else:
        A(sign_box((round(x - 4), round(y - hw), z0), (round(x + 4), round(y + hw), z0 + h), T(tex), tw, th, facing=facing, back=T('wood_dark'),
                   edge=T('wood_dark')))
    A(box((round(x - 6), round(y - 6), 0), (round(x + 6), round(y + 6), z0), {'side': T('wood_dark'), 'top': T('wood_dark'), 'bot': CAULK}))
    KEEP_OUT.append((x, y, hw + 30))


def wall_brushes(w, tex):
    """collision pieces of a hw_houses.Wall; tex: dict face kind -> texture ('out', 'in', 'jamb', 'top', 'bot')"""
    for (mn, mx) in w.pieces():
        b = box(tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx), CAULK)
        for f in b.faces:
            k = w.face_kind(f.n)
            t = tex.get(k, CAULK)
            if k == 'top' and abs(max(p[2] for p in f.pts) - w.z1) < 0.5: t = tex.get('wtop', CAULK)
            if k == 'bot' and abs(min(p[2] for p in f.pts) - w.z0) < 0.5: t = CAULK
            f.tex = t; f.sc = wopmap.default_scale(t)
        A(b)
    # glass in the windows (nonsolid, alpha)
    for h in w.holes:
        if h.kind != 'win' or not h.glass or w.out == 0 or not tex.get('glass'): continue
        p0, p1 = w.span(); pm = (p0 + p1) / 2
        if w.axis == 'x': b = box((h.u0, pm - 1, h.z0), (h.u1, pm + 1, h.z1), tex['glass'])
        else: b = box((pm - 1, h.u0, h.z0), (pm + 1, h.u1, h.z1), tex['glass'])
        for f in b.faces: f.sc = ((h.u1 - h.u0) / 256, (h.z1 - h.z0) / 256)
        A(b)


def route(name, a, b):
    ROUTES.append((name, a, b))


def free(x, y, r):
    if abs(x) > L.HX - r - 24 or y < L.YS + r + 24 or y > L.YN - r - 24: return False
    for (x0, y0, x1, y1) in BLOCKED:
        if x0 - r < x < x1 + r and y0 - r < y < y1 + r: return False
    return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT) and path_dist(x, y) > r + 70


def free_bl(x, y, r, pathgap):
    """looser test for sightline blockers: next to paths is fine, on them is not"""
    if abs(x) > L.HX - r - 24 or y < L.YS + r + 24 or y > L.YN - r - 24: return False
    for (x0, y0, x1, y1) in BLOCKED:
        if x0 - r < x < x1 + r and y0 - r < y < y1 + r: return False
    return all(math.hypot(x - kx, y - ky) >= kr + r - 20 for (kx, ky, kr) in KEEP_OUT) and path_dist(x, y) > pathgap


def near_free(x, y, r, search=400, pathgap=None):
    if pathgap is not None:
        ok = lambda px, py: free_bl(px, py, r, pathgap)
        if ok(x, y): return (x, y)
        for d in range(32, search + 1, 32):
            for k in range(16):
                a = k * math.pi / 8
                px, py = x + d * math.cos(a), y + d * math.sin(a)
                if ok(px, py): return (round(px), round(py))
        return None
    if free(x, y, r): return (x, y)
    for d in range(32, search + 1, 32):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if free(px, py, r): return (round(px), round(py))
    return None


# rectangles nothing loose may be placed in (buildings, maze, plazas)
BLOCKED = [(L.MAN[0] - 120, L.PORCH_STEPS[1] - 60, L.MAN[2] + 120, L.MAN[3] + 60),
           (L.MAUS[0] - 80, L.MAUS[1] - 120, L.MAUS[2] + 80, L.MAUS[3] + 40),
           (L.COT[0] - 140, L.COT[1] - 80, L.COT[2] + 120, L.COT[3] + 80),
           (L.MAZE[0] - 40, L.MAZE[1], L.MAZE[2], L.MAZE[3] + 40),
           (L.GPUMP[0] - L.GP_R - 60, L.GPUMP[1] - L.GP_R - 60, L.GPUMP[0] + L.GP_R + 60, L.GPUMP[1] + L.GP_R + 60),
           (L.TREE[0] - 300, L.TREE[1] - 440, L.TREE[0] + 620, L.TREE[1] + 300),
           (L.CAUL[0] - 420, L.CAUL[1] - 340, L.CAUL[0] + 340, L.CAUL[1] + 340),
           (-940, L.GATE[1] - 60, 940, L.GATE[1] + 60)]

PATHS = [[(0, -2000), (0, -1660), (0, -1000), (40, -640)],
         [(-300, -340), (-700, -800), (-1000, -1100), (-1270, -1232)],
         [(330, -420), (700, -900), (930, -1184)],
         [(-360, 120), (-700, 300), (-1000, 330), (-1000, 420)],
         [(-700, 300), (-1300, 260), (-1600, 330), (-1600, 420)],
         [(0, 280), (0, 700), (0, 1060)],
         [(330, 120), (800, 500), (1150, 850), (1240, 950)],
         [(-560, 1150), (-760, 900), (-900, 900)],
         [(1248, -560), (1248, -700)],
         [(-1000, -1100), (-1380, -380)],
         [(560, 1150), (760, 1040), (1000, 1000)]]


def path_dist(x, y):
    best = 1e9
    for r in PATHS:
        for (a, b) in zip(r, r[1:]):
            ax, ay = a; bx, by = b
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


# =================================================================================================== sky hull + banks
def hull_and_banks():
    S = L.SKY
    W = 16
    sk = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    x0, x1, y0, y1, z0, z1 = S['x0'], S['x1'], S['y0'], S['y1'], S['z0'], S['z1']
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), sk, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), dict(sk, bot=T('sky')), detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), dict(sk, s=T('sky')), detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), dict(sk, n=T('sky')), detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), dict(sk, w=T('sky')), detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), dict(sk, e=T('sky')), detail=False))
    # earth banks: steep inner face from the boundary up to BANK_Z, flat leafy top out to the sky walls.
    # Each side is one prism (corners handled by the x sides spanning the full y range).
    HX, YS, YN, Z, R = L.HX, L.YS, L.YN, L.BANK_Z, L.BANK_RUN
    bt = {'top': T('leafbed'), 'bot': CAULK}
    def tf(n):
        if n[2] > 0.9: return T('leafbed')
        if n[2] < -0.9: return CAULK
        if n[2] > 0.05: return T('bank')
        return CAULK
    zb = L.SLAB_BOT
    # east / west banks (full y), north / south banks between them
    A(hull([(HX, y, zb) for y in (y0, y1)] + [(HX, y, 0) for y in (y0, y1)] + [(HX + R, y, Z) for y in (y0, y1)] +
           [(x1, y, Z) for y in (y0, y1)] + [(x1, y, zb) for y in (y0, y1)], tf))
    A(hull([(-HX, y, zb) for y in (y0, y1)] + [(-HX, y, 0) for y in (y0, y1)] + [(-HX - R, y, Z) for y in (y0, y1)] +
           [(x0, y, Z) for y in (y0, y1)] + [(x0, y, zb) for y in (y0, y1)], tf))
    # north/south: slanted face from the boundary; their x ends follow the east/west slopes
    for (yy, sg, yend) in ((YN, 1, y1), (YS, -1, y0)):
        pts = []
        for x in (-HX, HX):
            pts += [(x, yy, zb), (x, yy, 0)]
        for x in (-HX - R, HX + R):
            pts += [(x, yy + sg * R, Z)]
        for x in (x0, x1):
            pts += [(x, yend, Z), (x, yend, zb)]
        b = hull(pts, tf)
        for p in carve(b, [hull([(HX, y, zb) for y in (y0, y1)] + [(HX, y, 0) for y in (y0, y1)] + [(HX + R, y, Z) for y in (y0, y1)] +
                                [(x1, y, Z) for y in (y0, y1)] + [(x1, y, zb) for y in (y0, y1)], CAULK),
                           hull([(-HX, y, zb) for y in (y0, y1)] + [(-HX, y, 0) for y in (y0, y1)] + [(-HX - R, y, Z) for y in (y0, y1)] +
                                [(x0, y, Z) for y in (y0, y1)] + [(x0, y, zb) for y in (y0, y1)], CAULK)]):
            for f in p.faces: f.tex = tf(f.n); f.sc = wopmap.default_scale(f.tex)
            A(p)
    # player clip along the boundary up to the sky (shots fly on into the banks)
    A(box((-HX - 16, YS - 16, 0), (-HX, YN + 16, z1), CLIP), box((HX, YS - 16, 0), (HX + 16, YN + 16, z1), CLIP))
    A(box((-HX, YS - 16, 0), (HX, YS, z1), CLIP), box((-HX, YN, 0), (HX, YN + 16, z1), CLIP))
    # dead woods on the banks (silhouettes against the sky), bushes
    rng = np.random.default_rng(5)
    kinds = ['tree_a', 'tree_b', 'tree_c']
    for side in range(4):
        n = 9 if side < 2 else 8
        for k in range(n):
            t = (k + 0.5) / n + rng.uniform(-0.03, 0.03)
            d = rng.uniform(R + 60, R + 240)
            if side == 0: x, y = -HX - d, y0 + 200 + (y1 - y0 - 400) * t
            elif side == 1: x, y = HX + d, y0 + 200 + (y1 - y0 - 400) * t
            elif side == 2: x, y = x0 + 500 + (x1 - x0 - 1000) * t, YN + d
            else: x, y = x0 + 500 + (x1 - x0 - 1000) * t, YS - d
            custom(kinds[(k + side) % 3], x, y, Z, angle=int(rng.uniform(0, 360)), mul=rng.uniform(0.85, 1.1))
    for side in range(4):
        for k in range(10):
            t = (k + 0.5) / 10
            d = rng.uniform(R + 40, R + 300)
            if side == 0: x, y = -HX - d, YS + 100 + (YN - YS - 200) * t
            elif side == 1: x, y = HX + d, YS + 100 + (YN - YS - 200) * t
            elif side == 2: x, y = -HX + 100 + 2 * (HX - 100) * t, YN + d
            else: x, y = -HX + 100 + 2 * (HX - 100) * t, YS - d
            mdl_c(['pad_ddmix/trashcan/bush.md3', 'pad_ddmix/trashcan/tree_autumn.md3'][(k + side) % 2], x, y, Z,
                  [1.2, 1.0][(k + side) % 2], int(rng.uniform(0, 360)))


# =================================================================================================== ground (two layers: the upper one has the crypt holes)
MAUS_HOLE = (L.MAUS[0] + HH.MT, L.MAUS[1] + HH.MT, L.MAUS[2] - HH.MT, L.MAUS[3] - HH.MT)
PASSAGE = (L.MAUS_STAIR[0], L.MAUS[3] - HH.MT, L.MAUS_STAIR[1], L.MAUS[3])
CRYPT_HOLE = (L.CRYPT[0] - 16, L.CRYPT[1], L.CRYPT[2] + 16, L.CRYPT[3] + 16)
HOLES = [MAUS_HOLE, PASSAGE, CRYPT_HOLE]
DEEP = -256


def ground():
    HX, YS, YN = L.HX, L.YS, L.YN
    step = 512
    for x0 in range(-HX, HX, step):
        for y0 in range(YS, YN, step):
            x1, y1 = min(x0 + step, HX), min(y0 + step, YN)
            A(box((x0, y0, L.SLAB_BOT), (x1, y1, DEEP), CAULK))
            mine = [h for h in HOLES if h[0] < x1 and h[2] > x0 and h[1] < y1 and h[3] > y0]
            rects = sub_rects((x0, y0, x1, y1), mine) if mine else [(x0, y0, x1, y1)]
            for (a, b, c, d) in rects:
                bb = box((a, b, DEEP), (c, d, 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK})
                for f in bb.faces:
                    if abs(f.n[2]) > 0.5: continue
                    # side faces bounding a hole are visible (crypt walls)
                    cx = (a + c) / 2 + f.n[0] * ((c - a) / 2 + 1); cy = (b + d) / 2 + f.n[1] * ((d - b) / 2 + 1)
                    if abs(f.n[0]) > 0.5: pts = [(cx, y) for y in np.linspace(b + 2, d - 2, 5)]
                    else: pts = [(x, cy) for x in np.linspace(a + 2, c - 2, 5)]
                    if any(h[0] < px < h[2] and h[1] < py < h[3] for (px, py) in pts for h in HOLES):
                        f.tex = T('stone_dark'); f.sc = (0.5, 0.5)
                A(bb)


def paths():
    """dirt paths: nonsolid 1u decal strips along PATHS (quads per segment + octagon joints)"""
    n = 0
    tex = {'top': T('dirt_ns'), 'side': NODRAW_NS, 'bot': NODRAW_NS}
    for r in PATHS:
        for (a, b) in zip(r, r[1:]):
            a = np.array(a, float); b = np.array(b, float)
            d = (b - a) / np.linalg.norm(b - a); nn = np.array([-d[1], d[0]]) * 72
            q = [a + nn, b + nn, b - nn, a - nn]
            if any(_in_hole_or_building(p) for p in q): continue
            A(hull([(p[0], p[1], z) for p in q for z in (0, 1)], tex, round_pts=False)); n += 1
        for p in r[1:-1]:
            A(hull([(x, y, z) for (x, y) in ngon(p[0], p[1], 72, 8) for z in (0, 1)], tex, round_pts=False))
    return n


def _in_hole_or_building(p):
    x, y = p
    return any(h[0] - 8 < x < h[2] + 8 and h[1] - 8 < y < h[3] + 8 for h in HOLES)


# =================================================================================================== the manor
def manor():
    X0, Y0, X1, Y1 = L.MAN
    F0, F1, C1, E = L.MAN_F0, L.MAN_F1, L.MAN_C1, L.MAN_EAVE
    WT = L.WALL
    ext = {'out': CAULK, 'in': T('wallpaper'), 'jamb': T('wood_dark'), 'top': T('wood_dark'), 'bot': T('wood_dark'), 'glass': T('glass_broken')}
    for w in HH.manor_walls(): wall_brushes(w, ext)
    inn = {'in': T('wallpaper'), 'jamb': T('wood_dark'), 'top': T('wood_dark'), 'bot': T('wood_dark'), 'wtop': CAULK}
    for w in HH.manor_inner_walls(): wall_brushes(w, inn)
    ix0, iy0, ix1, iy1 = X0 + WT, Y0 + WT, X1 - WT, Y1 - WT
    A(box((ix0, iy0, 0), (ix1, iy1, F0), {'top': T('floor_wood'), 'side': CAULK, 'bot': CAULK}))
    hole = HH.stair_e_hole()
    for (a, b, c, d) in sub_rects((ix0, iy0, ix1, iy1), [tuple(round(v) for v in hole)]):
        A(box((a, b, F1 - 16), (c, d, F1), {'top': T('floor_wood'), 'bot': T('ceiling'), 'side': T('wood_dark')}))
    A(box((ix0, iy0, C1), (ix1, iy1, E), {'bot': T('ceiling'), 'top': CAULK, 'side': CAULK}))
    # east-room staircase (rises north along the east wall), 16u steps
    s = HH.STAIR_E
    for k in range(s['n']):
        ya, yb = s['y0'] + s['run'] * k, s['y0'] + s['run'] * (k + 1)
        A(box((s['x0'], round(ya), F0), (s['x1'], round(yb), F0 + 16 * (k + 1)), {'top': T('carpet'), 'side': T('wood_dark'), 'bot': CAULK}))
    # banister clip on the upper floor along the open side of the stairwell
    A(box((s['x0'] - 8, round(hole[1]), F1), (s['x0'], round(hole[3]) - 64, F1 + 40), CLIP))
    route('manor_stairs', (370, 1330, F0), (448, 1690, F1))
    # porch: deck, step, roof (balcony), posts
    px0, py0, px1, py1 = L.PORCH
    A(box((px0, py0, 0), (px1, py1, F0), {'top': T('porch_wood'), 'side': T('wood_dark'), 'bot': CAULK}))
    sx0, sy0, sx1, sy1 = L.PORCH_STEPS
    A(box((sx0, sy0 + 32, 0), (sx1, sy1, 16), {'top': T('porch_wood'), 'side': T('wood_dark'), 'bot': CAULK}))
    A(box((px0 - 16, py0 - 16, F1 - 16), (px1 + 16, py1, F1), {'top': T('porch_wood'), 'bot': T('wood_dark'), 'side': CAULK}))
    for x in (-376, -176, 176, 376):
        A(box((x - 8, py0, F0), (x + 8, py0 + 16, F1 - 16), WCLIP))
    # railing clip (players only): porch front either side of the steps, porch sides, balcony front and sides
    RAIL = 48
    for (a0, a1) in ((-368, -184), (184, 368)):
        A(box((a0, py0, F0), (a1, py0 + 16, F0 + RAIL), CLIP))
    for sx in (-1, 1):
        A(box((min(sx * 384, sx * 368), py0 + 16, F0), (max(sx * 384, sx * 368), py1, F0 + RAIL), CLIP))
    A(box((px0 - 16, py0 - 16, F1), (px1 + 16, py0, F1 + RAIL), CLIP))
    for sx in (-1, 1):
        A(box((min(sx * (px1 + 16), sx * px1), py0, F1), (max(sx * (px1 + 16), sx * px1), py1, F1 + RAIL), CLIP))
    route('porch_door', (0, 1000, 0), (0, 1400, F0))
    route('hall_parlour', (0, 1400, F0), (-300, 1420, F0))
    route('hall_dining', (0, 1400, F0), (180, 1420, F0))
    route('back_door', (0, 1600, F0), (0, 1820, 0))
    route('balcony_door', (0, 1350, F1), (0, 1200, F1))
    # roof: mansard hull (deck on top), chimneys, cupola plinth + stair + posts + roof
    ov, inn_, D = L.MAN_OVER, L.MAN_IN, L.MAN_DECK
    pts = [(x, y, E) for x in (X0 - ov, X1 + ov) for y in (Y0 - ov, Y1 + ov)] + [(x, y, D) for x in (X0 + inn_, X1 - inn_) for y in (Y0 + inn_, Y1 - inn_)]
    A(hull(pts, lambda n: T('tin') if n[2] > 0.9 else (T('wood_dark') if n[2] < -0.9 else CAULK)))
    for sx in (-1, 1):
        cx = sx * 400
        A(box((cx - 40, 1556, D), (cx + 40, 1652, 800), {'side': T('brick'), 'top': T('stone_dark'), 'bot': CAULK}))
        custom('chimney_cap', cx, 1604, 800)
        speaker(cx, 1604, 820, 'sound/world/ambient/wind_night.ogg', volume=0.3)
    cx0, cy0, cx1, cy1 = L.CUPOLA
    Z, TOP = L.CUPOLA_Z, L.CUPOLA_TOP
    A(box((cx0, cy0, D), (cx1, cy1, Z), {'top': T('floor_wood'), 'side': T('wood_dark'), 'bot': CAULK}))
    for k in range(4):
        A(box((-48, cy0 - 80 + 20 * k, D), (48, cy0 - 60 + 20 * k, D + 16 * (k + 1)), {'top': T('floor_wood'), 'side': T('wood_dark'), 'bot': CAULK}))
    for (px, py) in ((cx0 + 8, cy0 + 8), (cx1 - 8, cy0 + 8), (cx1 - 8, cy1 - 8), (cx0 + 8, cy1 - 8)):
        A(box((px - 8, py - 8, Z), (px + 8, py + 8, TOP), WCLIP))
    A(box((cx0 - 16, cy0 - 16, TOP), (cx1 + 16, cy1 + 16, TOP + 16), {'bot': T('wood_dark'), 'top': CAULK, 'side': CAULK}))
    ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    R0 = (cx1 - cx0) / 2 + 8
    for (r0, z0, r1, z1) in ((R0, TOP + 16, R0 * 1.0, TOP + 90), (R0 * 0.98, TOP + 90, R0 * 0.7, TOP + 140), (R0 * 0.68, TOP + 140, R0 * 0.2, TOP + 200)):
        A(frustum(ccx, ccy, r0 - 8, z0, r1 - 8, z1, WCLIP, 12))
    custom('manor_shell', HH.MCX, HH.MCY, 0); custom('manor_roof', HH.MCX, HH.MCY, 0); custom('manor_porch', HH.MCX, HH.MCY, 0)
    custom('cupola', ccx, ccy, D)
    # cupola railing clip (open to the south over the stair) and a low clip round the roof deck edge
    for (mn, mx) in (((cx0 + 16, cy1 - 16, Z), (cx1 - 16, cy1, Z + 40)), ((cx0, cy0 + 16, Z), (cx0 + 16, cy1 - 16, Z + 40)),
                     ((cx1 - 16, cy0 + 16, Z), (cx1, cy1 - 16, Z + 40)), ((cx0 + 16, cy0, Z), (-56, cy0 + 16, Z + 40)),
                     ((56, cy0, Z), (cx1 - 16, cy0 + 16, Z + 40))):
        A(box(mn, mx, CLIP))
    ex0, ey0, ex1, ey1 = X0 + inn_, Y0 + inn_, X1 - inn_, Y1 - inn_
    for (mn, mx) in (((ex0, ey0, D), (-64, ey0 + 12, D + 40)), ((64, ey0, D), (ex1, ey0 + 12, D + 40)),
                     ((ex0, ey1 - 12, D), (ex1, ey1, D + 40)), ((ex0, ey0 + 12, D), (ex0 + 12, ey1 - 12, D + 40)),
                     ((ex1 - 12, ey0 + 12, D), (ex1, ey1 - 12, D + 40))):
        A(box(mn, mx, CLIP))
    route('cupola_stair', (0, 1340, D), (0, 1520, Z))
    weapon('imperius', ccx, ccy + 20, Z, 'purple')
    light(ccx, ccy, TOP - 30, 220, '0.8 0.6 1')
    # weathervane (turning slowly) on the onion spire + bats circling the cupola
    wz = round(HH.CUPOLA_SPIRE)
    M.ent('func_rotating', brushes=[box((ccx - 8, ccy - 8, wz - 8), (ccx + 8, ccy + 8, wz + 8), ORIGIN),
                                    box((ccx - 4, ccy - 4, wz + 20), (ccx + 4, ccy + 4, wz + 28), NODRAW_NS)],
          model2=hwlib.IQM['weathervane'], speed=14, spawnflags=0, dmg=0)
    bz = TOP + 260
    M.ent('func_rotating', brushes=[box((ccx - 8, ccy - 8, bz - 8), (ccx + 8, ccy + 8, bz + 8), ORIGIN),
                                    box((ccx - 4, ccy - 4, bz + 60), (ccx + 4, ccy + 4, bz + 68), NODRAW_NS)],
          model2=hwlib.IQM['bats_manor'], speed=34, spawnflags=0, dmg=0)
    # balcony -> roof deck pads (both ends of the balcony)
    for sx in (-1, 1):
        jumppad(sx * 300, 1196, F1, (sx * 300, 1440, D), D + 150, f'roofpad{"we"[sx > 0]}')
    jumppad(-330, 1400, D, (-650, 950, 0), D + 120, 'deck_fling')
    item('ammo_imperius', -330, 1640, D); item('item_armor_shard', 330, 1400, D)
    item('holdable_boomies', -250, 1380, D)
    # interior: parlour (west), hall, dining (east); upstairs bedroom (west), landing, library (east)
    hx = L.HALL_X
    custom('fireplace', ix0, 1504, F0, angle=90)
    light(ix0 + 90, 1504, F0 + 60, 240, '1 0.5 0.15')
    speaker(ix0 + 60, 1504, F0 + 60, 'sound/world/ambient/fire_crackling.ogg', volume=0.6)
    custom('armchair', -360, 1420, F0, angle=250)                    # one armchair by the fire
    A(box((-400, 1380, F0), (-320, 1460, F0 + 60), WCLIP))
    custom('piano', -230, 1640, F0, angle=180)
    A(box((-312, 1530, F0), (-148, 1700, F0 + 66), WCLIP))
    custom('chandelier', -316, 1504, F1 - 16)
    light(-316, 1504, F1 - 120, 200, '1 0.75 0.45')
    station(70, 1600, F0, 180)                                      # health station in the hall
    item('ammo_betty', -420, 1360, F0)
    custom('dining_table', 268, 1504, F0, angle=90)
    A(box((214, 1396, F0), (322, 1612, F0 + 60), WCLIP))
    custom('chandelier', 268, 1504, F1 - 16)
    light(268, 1504, F1 - 120, 200, '1 0.75 0.45')
    item('ammo_pumper', 200, 1680, F0)
    item('ammo_bubbleg', 0, 1440, F0)
    A(box((-40, 1296, F0), (40, 1712, F0 + 1), {'top': T('carpet_ns'), 'side': NODRAW_NS, 'bot': NODRAW_NS}))
    light(0, 1504, F1 - 60, 180, '1 0.7 0.4')
    speaker(0, 1504, F0 + 100, 'sound/world/machine/clock_ticking.ogg', volume=0.5)
    speaker(0, 1504, F1 + 100, 'sound/world/ambient/floor_creaking.ogg', volume=0.5)
    # portraits on the hall walls
    A(sign_box((-hx + 8, 1560, F0 + 70), (-hx + 10, 1640, F0 + 170), T('portrait_lady'), 256, 320, facing='e'))
    A(sign_box((hx - 10, 1560, F0 + 70), (hx - 8, 1640, F0 + 170), T('portrait_man'), 256, 320, facing='w'))
    A(sign_box((60, iy1 - 2, F1 + 60), (120, iy1, F1 + 135), T('portrait_cat'), 256, 320, facing='s'))
    # upstairs
    custom('bed', -360, 1600, F1)
    A(box((-416, 1494, F1), (-304, 1706, F1 + 44), WCLIP))
    item('item_visionless', -250, 1400, F1)
    light(-320, 1500, C1 - 50, 160, '0.7 0.6 1')
    custom('bookshelf', 260, iy0, F1, angle=180)
    A(box((164, iy0, F1), (356, iy0 + 40, C1 - 2), WCLIP))
    custom('bookshelf', hx + 8, 1440, F1, angle=90)
    A(box((hx + 8, 1344, F1), (hx + 48, 1536, C1 - 2), WCLIP))
    custom('armchair', 260, 1600, F1, angle=200)
    A(box((220, 1560, F1), (300, 1640, F1 + 60), WCLIP))
    item('item_armor_padshield', 300, 1420, F1)
    light(260, 1500, C1 - 50, 160, '1 0.7 0.4')
    item('ammo_splasher', 0, 1640, F1)
    light(0, 1450, C1 - 40, 150, '0.9 0.6 0.4')
    item('ammo_boaster', 0, 1220, F1)
    spawn(-80, 1220, F1, 270)
    spawn(-420, 1400, F0, 0)
    # front lamps + porch light
    for x in (-300, 300):
        light(x, 1210, 210, 180, '1 0.6 0.25')
    custom('jack_m0', -250, 1185, F0, angle=0, lit=False); custom('jack_s1', 250, 1180, F0, angle=0, lit=False)


# =================================================================================================== graveyard + mausoleum + crypt
def graveyard():
    gx0, gy0, gx1, gy1 = L.GRAVE
    # fence along the south (y = gy0) and east (x = gx1) sides, gates as gaps between stone pillars
    start, corner, end, Ls, gaps = fence_spec()
    p, sc, zo, o = FENCE[0]
    custom((p, sc, zo), o[0], o[1], 0)
    # clip along the fence (players only), split at the gates and pillars
    def along(s):
        return (start[0] + s, gy0) if s <= Ls else (gx1, gy0 + (s - Ls))
    cuts = sorted([0.0] + [g for gp in gaps for g in (gp[0] - 40, gp[1] + 40)] + [Ls - 8, Ls + 8, Ls + (end[1] - gy0)])
    spans = []
    s0 = 0.0
    for (ga, gb) in gaps:
        spans.append((s0, ga - 40)); s0 = gb + 40
    spans.append((s0, Ls + (end[1] - gy0)))
    for (a, b) in spans:
        segs = [(a, min(b, Ls - 8)), (max(a, Ls + 8), b)]
        for (sa, sb) in segs:
            if sb - sa < 4: continue
            (xa, ya), (xb, yb) = along(sa), along(sb)
            A(box((round(min(xa, xb)) - 4, round(min(ya, yb)) - 4, 0), (round(max(xa, xb)) + 4, round(max(ya, yb)) + 4, 128), CLIP))
    A(box((gx1 - 12, gy0 - 12, 0), (gx1 + 12, gy0 + 12, 128), CLIP))
    for (ga, gb) in gaps:
        for s in (ga - 20, gb + 20):
            x, y = along(s)
            custom('gate_pillar', x, y, 0)
            A(box((round(x) - 30, round(y) - 30, 0), (round(x) + 30, round(y) + 30, 236), WCLIP))
            light(x, y, 280, 140, '1 0.6 0.25')
            custom('jack_s0' if s < Ls else 'jack_s1', x, y, 236, angle=270 if s < Ls else 0, lit=False)
    route('grave_gate_s', (-1600, 150, 0), (-1600, 520, 0))
    route('grave_gate_s2', (-1000, 150, 0), (-1000, 520, 0))
    route('grave_gate_e', (-600, 900, 0), (-950, 900, 0))
    gtrees = []
    # dead trees + catalog tombstones and skulls along the west bank
    for (x, y, nm, s, a) in ((-2120, 1240, 'tree_c', 1.0, 40), (-1180, 640, 'tree_a', 1.0, 200), (-2100, 520, 'tree_b', 1.1, 120),
                             (-940, 1640, 'tree_a', 0.9, 300)):
        custom(nm, x, y, 0, angle=a, mul=s)
        A(cyl(round(x), round(y), round(40 * s), 0, round(500 * s), WCLIP, 8))
        KEEP_OUT.append((x, y, 120)); gtrees.append((x, y))
    # headstones in rows (front faces south), mounds in front, a few zombie hands
    rng = np.random.default_rng(13)
    kinds = ['tomb_arch', 'tomb_cross', 'tomb_celtic', 'tomb_obelisk', 'tomb_slab', 'tomb_broken', 'tomb_arch_b', 'tomb_slab_b']
    n = 0
    for row, y in enumerate(range(470, 1330, 165)):
        for col, x in enumerate(range(-2170, -860, 150)):
            if (x + 1600) ** 2 < 120 ** 2 or (x + 1000) ** 2 < 100 ** 2: continue      # aisles to the gates
            if x > -1120 and y > 1000: continue
            if L.MAUS[0] - 110 < x < L.MAUS[2] + 110 and y > L.MAUS[1] - 190: continue     # in front of the mausoleum
            if abs(y - 900) < 100 and x > -1000: continue                                # east gate aisle
            xx, yy = x + rng.uniform(-24, 24), y + rng.uniform(-20, 20)
            if any(math.hypot(xx - kx, yy - ky) < 150 for (kx, ky) in gtrees + [GHOST_C]): continue
            k = kinds[(row * 3 + col + int(rng.integers(3))) % len(kinds)]
            a = rng.uniform(-8, 8)
            w, t, h = HM.TOMB_DIM['tomb_arch' if k == 'tomb_arch_b' else ('tomb_slab' if k == 'tomb_slab_b' else k)]
            custom(k, xx, yy, 0, angle=a)
            tt = max(t, 30) if 'cross' in k or 'celtic' in k else t
            A(rbx(xx, yy, a, -w / 2 + 2, w / 2 - 2, -tt / 2, tt / 2, 0, h - 6, WCLIP))
            if rng.random() < 0.75:
                custom('mound_a' if rng.random() < 0.5 else 'mound_b', xx, yy - 120, 0, angle=a, lit=True)
                if rng.random() < 0.18: custom('zombie_hand', xx + rng.uniform(-20, 20), yy - 110, 0, angle=int(rng.uniform(0, 360)), lit=False)
            KEEP_OUT.append((xx, yy, 60)); KEEP_OUT.append((xx, yy - 120, 60))
            n += 1
    for (x, y, nm, a) in ((-2220, 820, 'tombstone1', 10), (-2230, 980, 'tombstone2', -6), (-2210, 1120, 'tombstone3', 4)):
        mdl_c('pad_westernset/' + nm + '.md3', x, y, 0, 1.0, a + 90)
    mdl_c('pad_ddmix/jail/skull.md3', -1200, 1080, 0, 0.4, 200)
    # ghosts drifting round the middle of the graveyard
    gz = 50
    gcx, gcy = GHOST_C
    M.ent('func_rotating', brushes=[box((gcx - 8, gcy - 8, gz - 8), (gcx + 8, gcy + 8, gz + 8), ORIGIN),
                                    box((gcx - 4, gcy - 4, gz + 100), (gcx + 4, gcy + 4, gz + 108), NODRAW_NS)],
          model2=hwlib.IQM['ghosts'], speed=-9, spawnflags=0, dmg=0)
    speaker(gcx, gcy, 120, 'sound/pad_ambiente/ambi_ghost.wav', volume=0.5)
    # ground mist over the graveyard (fog volume)
    A(box((gx0 + 8, gy0 + 24, -16), (gx1 - 24, gy1 - 8, 36), T('mist'), detail=True))
    for (x, y) in ((-1800, 700), (-1200, 700), (-1500, 1100), (-2000, 1100)):
        light(x, y, 200, 160, '0.5 0.6 1')
    item('item_jumper', -1350, 800, 0)
    item('ammo_balloony', -2050, 600, 0)
    item('ammo_imperius', -1950, 1650, 0)
    item('ammo_nipper', -880, 1300, 0)
    spawn(-1150, 420, 0, 90); spawn(-2050, 950, 0, 0); spawn(-900, 1820, 0, 225)
    return n


GHOST_C = (-1450.0, 800.0)
FENCE = []


def fence_spec():
    gx0, gy0, gx1, gy1 = L.GRAVE
    start = (gx0 + 16, gy0); corner = (gx1, gy0); end = (gx1, gy1 - 16)
    Ls = corner[0] - start[0]
    gaps = []
    for (side, c, w) in L.GRAVE_GATES:
        s = (c - start[0]) if side == 's' else Ls + (c - gy0)
        gaps.append((s - w / 2, s + w / 2))
    return start, corner, end, Ls, gaps


def extra_models():
    """models that depend on the builder's layout: made before the shader file is written"""
    start, corner, end, Ls, gaps = fence_spec()
    FENCE[:] = [HM.iron_fence('fence_grave', [start, corner, end], gaps=gaps)]


def mausoleum():
    X0, Y0, X1, Y1 = L.MAUS
    MT = HH.MT
    tx = {'out': CAULK, 'in': T('stone'), 'jamb': T('stone'), 'top': T('stone'), 'bot': T('stone'), 'glass': None}
    for w in HH.maus_walls(): wall_brushes(w, tx)
    # roof: gable hull, ridge along y
    ov = 16
    cx = (X0 + X1) / 2
    pts = [(X0 - ov, y, L.MAUS_H) for y in (Y0 - ov, Y1 + ov)] + [(X1 + ov, y, L.MAUS_H) for y in (Y0 - ov, Y1 + ov)] + \
          [(cx, y, HH.MAUS_RIDGE) for y in (Y0 - ov, Y1 + ov)]
    A(hull(pts, lambda n: T('stone_dark') if n[2] < -0.9 else CAULK))
    # front steps up to the podium (doorway sill at MAUS_F)
    dx0, dx1 = L.MAUS_STAIR
    A(box((dx0, Y0 - 64, 0), (dx1, Y0 - 32, 16), {'top': T('stone'), 'side': T('stone'), 'bot': CAULK}))
    A(box((dx0, Y0 - 32, 0), (dx1, Y0, 32), {'top': T('stone'), 'side': T('stone'), 'bot': CAULK}))
    # inside: ledges and the landing at MAUS_F, the stair down the middle to the crypt
    hx0, hy0, hx1, hy1 = MAUS_HOLE
    st = {'top': T('stone'), 'side': T('stone_dark'), 'bot': CAULK}
    A(box((hx0, hy0, DEEP), (dx0, hy1, L.MAUS_F), st))
    A(box((dx1, hy0, DEEP), (hx1, hy1, L.MAUS_F), st))
    A(box((dx0, hy0, DEEP), (dx1, hy0 + 40, L.MAUS_F), st))
    y = hy0 + 40
    zt = L.MAUS_F
    k = 0
    while zt > L.CRYPT_F:
        zt -= 16
        A(box((dx0, y, DEEP), (dx1, y + 24, zt), {'top': T('stone'), 'side': T('stone_dark'), 'bot': CAULK}))
        y += 24; k += 1
    assert y == L.MAUS[3], (y, k)
    # crypt: floor, lining walls, ceiling slab
    cx0, cy0, cx1, cy1 = L.CRYPT
    A(box((CRYPT_HOLE[0], CRYPT_HOLE[1], DEEP), (CRYPT_HOLE[2], CRYPT_HOLE[3], L.CRYPT_F), {'top': T('flagstone'), 'side': CAULK, 'bot': CAULK}))
    br = {'side': T('brick'), 'top': CAULK, 'bot': CAULK}
    A(box((CRYPT_HOLE[0], cy0, L.CRYPT_F), (cx0, CRYPT_HOLE[3], L.CRYPT_C), br))
    A(box((cx1, cy0, L.CRYPT_F), (CRYPT_HOLE[2], CRYPT_HOLE[3], L.CRYPT_C), br))
    A(box((cx0, cy1, L.CRYPT_F), (cx1, CRYPT_HOLE[3], L.CRYPT_C), br))
    A(box((CRYPT_HOLE[0], CRYPT_HOLE[1], L.CRYPT_C), (CRYPT_HOLE[2], CRYPT_HOLE[3], 0), {'bot': T('stone_dark'), 'top': T('grass'), 'side': CAULK}))
    custom('mausoleum', cx, (Y0 + Y1) / 2, 0)
    custom('crypt_vault', (cx0 + cx1) / 2, (cy0 + cy1) / 2, L.CRYPT_C)
    route('maus_door', (-1600, 1150, 0), (-1600, 1350, L.MAUS_F))
    route('crypt_stair', (-1600, 1350, L.MAUS_F), (-1600, 1880, L.CRYPT_F))
    # ledges: sarcophagi + candles; the stairwell
    for x in (hx0 + 60, hx1 - 60):
        custom('sarcophagus', x, 1560, L.MAUS_F, angle=90)
        A(box((x - 54, 1436, L.MAUS_F), (x + 54, 1684, L.MAUS_F + 92), WCLIP))
        custom('candles_b', x, 1410, L.MAUS_F, lit=False)
        light(x, 1420, L.MAUS_F + 90, 120, '1 0.65 0.3')
    light(cx, 1500, 200, 160, '0.6 0.5 1')
    # crypt contents: sarcophagi, Pumper, candles, skulls, coffins; the open coffin at the west end is the SECRET
    for x in (-1830, -1370):
        custom('sarcophagus', x, 1880, L.CRYPT_F)
        A(box((x - 116, 1832, L.CRYPT_F), (x + 116, 1928, L.CRYPT_F + 92), WCLIP))
        custom('candles_c', x, 1810, L.CRYPT_F, lit=False)
    for x in (-1250, -1950):
        custom('coffin_stand', x, cy1 - 1, L.CRYPT_F, angle=180)
    weapon('pumper', -1600, 1890, L.CRYPT_F, 'green')
    item('ammo_imperius', -1700, 1950, L.CRYPT_F)
    item('ammo_betty', -1450, 1810, L.CRYPT_F)
    mdl_c('pad_ddmix/jail/skull.md3', -1210, 1820, L.CRYPT_F, 0.35, 230)
    mdl_c('pad_ddmix/jail/skull.md3', -2000, 1960 - 40, L.CRYPT_F, 0.3, 100)
    for (x, c) in ((-1950, '0.6 0.4 1'), (-1750, '1 0.6 0.3'), (-1600, '1 0.65 0.35'), (-1450, '1 0.6 0.3'), (-1250, '0.4 1 0.5')):
        light(x, 1880, L.CRYPT_C - 60, 300, c)
    speaker(-1600, 1880, -100, 'sound/world/ambient/droplets_echoing.ogg', volume=0.6)
    # SECRET: the open coffin standing against the west wall
    ox = cx0 + 53 + 1
    custom('coffin_open', ox, 1880, L.CRYPT_F, angle=90, lit=False)
    light(cx0 + 40, 1880, L.CRYPT_F + 100, 160, '0.7 0.3 1')
    M.ent('trigger_multiple', brushes=[box((cx0 + 32, 1856, L.CRYPT_F), (cx0 + 56, 1904, L.CRYPT_F + 150), TRIG)], target='secret_snd', wait=6)
    speaker(cx0 + 60, 1880, L.CRYPT_F + 120, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('trigger_teleport', brushes=[box((cx0 + 2, 1860, L.CRYPT_F), (cx0 + 30, 1900, L.CRYPT_F + 140), TRIG)], target='lair_in')
    KEEP_OUT.append((cx0 + 30, 1880, 80))
    # mausoleum roof: pad beside the east wall up onto the ridge; ammo + powerup up there
    jumppad(X1 + 150, 1500, 0, (cx + 40, 1520, HH.MAUS_RIDGE - 24), HH.MAUS_RIDGE + 170, 'maus_roof')
    item('ammo_pumper', cx, 1640, HH.MAUS_RIDGE)
    item('item_armor_shard', cx, 1400, HH.MAUS_RIDGE)


# =================================================================================================== the Great Pumpkin + patch
def gp_profile_pts(dz=None):
    rows = np.array(HM.GP_ROWS, float)
    return rows


def gp_collision():
    """shell wedges (64 round, between two offset curves inside the visual shell) with the carved openings left out"""
    cx, cy = L.GPUMP
    rows = np.array(HM.GP_ROWS, float)
    zs = [0, 48, 96, 144, 192, 240, 300, 340, 380, 420, 460, 500]
    R = np.array([float(np.interp(z, rows[:, 1], rows[:, 0])) for z in zs])
    P = np.stack([R, np.array(zs, float)], 1)
    tg = np.gradient(P, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.linalg.norm(pn, axis=1, keepdims=True)
    g = HM.GP_G
    outer = P - pn * (6 + g * P[:, :1])
    inner = P - pn * (HM.GP_THICK - 6)
    nw = 48
    Rr = 440.0
    polys = HM_face_polys()
    face = L.GP_FACE
    def open_cell(a0, a1, z0, z1):
        for a in np.linspace(a0, a1, 4):
            da = (a - face + 180) % 360 - 180
            u = math.radians(da) * Rr
            for z in np.linspace(z0, z1, 4):
                if not any(HM.pip(p, u, z) for p in polys): return False
        return True
    nb = 0
    for i in range(len(zs) - 1):
        for k in range(nw):
            a0, a1 = 360 * k / nw, 360 * (k + 1) / nw
            if open_cell(a0, a1, zs[i], zs[i + 1]): continue
            pts = []
            for a in (a0, a1):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                for (r, z) in (outer[i], outer[i + 1], inner[i], inner[i + 1]):
                    pts.append((cx + r * ca, cy + r * sa, z))
            A(hull(pts, WCLIP, round_pts=False)); nb += 1
    # the top: three flat terraces round the lid hole (bots need flat ground; the faceted slope gave broken areas)
    for (r0, r1, zt, zb) in GP_TERRACES:
        for k in range(nw):
            a0, a1 = 360 * k / nw, 360 * (k + 1) / nw
            A(ring_seg(cx, cy, a0, a1, r0, r1, zb, zt, zb, zt, WCLIP)); nb += 1
    return nb


GP_TERRACES = [(L.GP_LID + 4, 200, 538, 514), (200, 250, 526, 500), (250, 300, 512, 492)]


def HM_face_polys():
    return HM.gp_face_polys()


def gp_top_z(r):
    for (r0, r1, zt, zb) in GP_TERRACES:
        if r < r1: return zt
    return GP_TERRACES[-1][2]


def pumpkin_patch():
    cx, cy = L.GPUMP
    custom('great_pumpkin', cx, cy, 0)
    nb = gp_collision()
    A(disc_brush(cx, cy, 290, 0, 8, {'top': T('hay'), 'side': T('hay'), 'bot': CAULK}, 24))
    # inside: giant candle beside the pad, the pad up through the lid hole onto the top
    fa = math.radians(L.GP_FACE)
    jumppad(cx, cy, 8, (cx + 215 * math.cos(fa + math.pi), cy + 215 * math.sin(fa + math.pi), gp_top_z(215)), 730, 'gp_top')
    ccx, ccy = ang_pt(cx, cy, 170, L.GP_FACE + 120)
    custom('candles_c', ccx, ccy, 8, mul=2.2, lit=False)
    A(cyl(round(ccx), round(ccy), 60, 8, 200, WCLIP, 10))
    light(cx, cy, 300, 420, '1 0.6 0.2')
    light(ccx, ccy, 240, 260, '1 0.55 0.15')
    item('ammo_balloony', *ang_pt(cx, cy, 170, L.GP_FACE - 120), 8)
    speaker(cx, cy, 200, 'sound/world/ambient/fire_crackling.ogg', volume=0.4)
    route('gp_mouth', ang_pt(cx, cy, 600, L.GP_FACE) + (0,), ang_pt(cx, cy, 120, L.GP_FACE) + (8,))
    # on top: Balloony + a fling pad back down (the steep sides give bots no way off)
    tx, ty = ang_pt(cx, cy, 178, L.GP_FACE + 180)
    weapon('boaster', tx, ty, gp_top_z(180), 'orange')
    item('ammo_splasher', *ang_pt(cx, cy, 178, L.GP_FACE + 90), gp_top_z(178))
    fx, fy = ang_pt(cx, cy, 226, L.GP_FACE - 90)
    lx, ly = ang_pt(cx, cy, 1000, L.GP_FACE - 80)
    slope_pad(fx, fy, (cx, cy), (lx, ly, 0), gp_top_z(170) + 320, 'gp_fling')
    light(cx, cy, 760, 260, '1 0.7 0.4')
    # the lid lying beside it
    lx2, ly2 = ang_pt(cx, cy, L.GP_R + 230, L.GP_FACE + 60)
    custom('gp_lid', lx2, ly2, 0, angle=30)
    A(frustum(lx2, ly2, L.GP_LID, 0, 90, 46, WCLIP, 12))
    KEEP_OUT.append((lx2, ly2, L.GP_LID + 40))
    # pumpkins round the patch (cover), jack-o'-lanterns, leaves, hay bales, scarecrow
    rng = np.random.default_rng(23)
    big = [('pump_b', 140, 0.9), ('pump_a', 100, 1.0), ('pump_e', 120, 0.85), ('pump_c', 80, 1.0), ('pump_d', 60, 1.1), ('pump_f', 46, 1.0)]
    spots = [(900, 600), (1100, 420), (1900, 520), (2100, 800), (2150, 1350), (2050, 1800), (1700, 1850), (1150, 1800), (900, 1500),
             (850, 1050), (1250, 640), (1700, 640), (2000, 1100), (1350, 1880), (900, 1880), (2150, 450)]
    for i, (x, y) in enumerate(spots):
        nm, R, sq = big[i % len(big)]
        p = near_free(x, y, R + 40, 200)
        if p is None: continue
        px, py = p
        custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), lit=R >= 100)
        ball_clip(px, py, 0, R, R * 1.6 * sq * 0.94)
        KEEP_OUT.append((px, py, R + 30))
        if R >= 80 and rng.random() < 0.7:
            q = near_free(px + R + 60, py, 60, 140)
            if q: custom('leaves_a' if i % 2 else 'leaves_b', q[0], q[1], 0, angle=int(rng.uniform(0, 360)), lit=False)
    for (x, y, nm, a) in ((1000, 760, 'jack_l0', 230), (1950, 980, 'jack_l1', 200), (1300, 1650, 'jack_m0', 250), (2100, 1600, 'jack_m1', 190),
                          (880, 1250, 'jack_g', 260), (1750, 420, 'jack_m0', 160)):
        p = near_free(x, y, 110, 200)
        if not p: continue
        R = HM.JACK[nm.split('_')[1][0]]
        custom(nm, p[0], p[1], 0, angle=a, lit=False)
        ball_clip(p[0], p[1], 0, R, R * 1.72 * 0.94)
        light(p[0], p[1], R * 0.9, 90 + R, '1 0.55 0.15')
        KEEP_OUT.append((p[0], p[1], R + 40))
    # hay bale stacks (cover, 32u steps onto them? no: 64u bales, a stack with a step)
    for (x, y, a) in ((1050, 1350, 20), (2000, 640, -30), (1650, 1700, 70)):
        p = near_free(x, y, 160, 200)
        if not p: continue
        hay_stack(p[0], p[1], a)
    sx, sy = near_free(2050, 1250, 140, 200) or (2050, 1250)
    custom('scarecrow', sx, sy, 0, angle=200)
    A(cyl(round(sx), round(sy), 10, 0, HM.SCARE_H - 40, WCLIP, 8))
    for (u0, u1) in ((-110, -12), (12, 110)):
        A(rbx(sx, sy, 200, u0, u1, -14, 14, HM.SCARE_H - 140, HM.SCARE_H - 100, WCLIP))
    KEEP_OUT.append((sx, sy, 150))
    timer_sound(sx, sy, 400, 'sound/world/animal/bird_crow.ogg', 'crow', 22, 12)
    for (x, y) in ((1150, 980), (1900, 1500)):
        p = near_free(x, y, 60, 200)
        if p: lamppost(p[0], p[1])
    item('item_floater', 1820, 1400, 0)
    item('ammo_betty', 2150, 1000, 0)
    item('ammo_pumper', 1000, 1650, 0)
    item('ammo_nipper', 1600, 560, 0)
    spawn(1900, 900, 0, 200); spawn(1000, 1900, 0, 270)
    spawn(1200, 520, 0, 120)
    return nb


def slope_pad(x, y, centre, land, apex, name):
    """jump pad on the Great Pumpkin's sloping top: a nonsolid decal disc that follows the slope, trigger above it"""
    pts = []
    for (px, py) in ngon(x, y, 34, 12, 0):
        z = 526 + 1
        pts += [(px, py, z), (px, py, z + 2)]
    A(hull(pts, {'top': T('jumppad_ns'), 'side': NODRAW_NS, 'bot': NODRAW_NS}, round_pts=False))
    ztop = max(p[2] for p in pts)
    trig = box((round(x) - 16, round(y) - 16, round(ztop) + 1), (round(x) + 16, round(y) + 16, round(ztop) + 64), TRIG)
    oz = (ztop + 1 + ztop + 64) / 2
    tx, ty = pad_target((x, y, oz), land, apex)
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (round(x), round(y), round(oz)), (round(tx), round(ty), round(apex)), land))
    light(x, y, ztop + 48, 120, '1 0.55 0.2')


def hay_stack(x, y, a):
    """3 bales on the ground + 1 on top (cover)"""
    w, d, h = HM.HAY
    for (u, v, z) in ((-w / 2 - 2, 0, 0), (w / 2 + 2, 0, 0), (0, 0, h)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        bx, by = x + u * ca, y + u * sa
        custom('hay_bale', bx, by, z, angle=a)
        A(rbx(bx, by, a, -w / 2 + 4, w / 2 - 4, -d / 2 + 4, d / 2 - 4, z, z + h - (2 if z else 0), WCLIP))
    KEEP_OUT.append((x, y, w + 40))


def lamppost(x, y):
    custom('lamppost', x, y, 0)
    A(cyl(round(x), round(y), 10, 0, HM.LAMP_H - 50, WCLIP, 8))
    light(x, y, HM.LAMP_H - 10, 200, '1 0.62 0.3')
    KEEP_OUT.append((x, y, 60))


# =================================================================================================== the hanging tree + treehouse
def hanging_tree():
    tx, ty = L.TREE
    BR, tp, tr = HM.TREE_BIG[1], HM.TREE_BIG[2], HM.TREE_BIG[3]
    custom('tree_big', tx, ty, 0)
    custom('treehouse', tx, ty, 0)
    A(cyl(round(tx), round(ty), L.TRUNK_R, 0, 900, WCLIP, 16))
    # spiral stair (weapclip under the plank MD3)
    r0, r1 = L.SPIRAL_R
    for (a0, a1, z) in L.spiral_steps():
        A(ring_seg(tx, ty, a0, a1, r0, r1, z - 16, z, z - 16, z, WCLIP))
    # round deck except over the top of the spiral; east deck (carved round the round deck and the trunk)
    g0, g1 = L.deck_gap()
    Z = L.PLAT_Z
    ring = []
    n = 32
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        if any(a0 < g1 - off and a1 > g0 - off for off in (0, 360)): continue
        b = ring_seg(tx, ty, a0, a1, r0, L.PLAT_R, Z - 16, Z, Z - 16, Z, WCLIP)
        A(b); ring.append(b)
    dx0, dy0, dx1, dy1 = L.TH_DECK
    rect = box((tx + dx0, ty + dy0, Z - 16), (tx + dx1, ty + dy1, Z), WCLIP)
    cutters = [hull([(px, py, z) for (px, py) in ngon(tx, ty, L.PLAT_R / math.cos(math.pi / 32) + 0.5, 32, 0) for z in (Z - 20, Z + 4)], WCLIP, round_pts=False)]
    for p in carve(rect, cutters): A(p)
    for (px, py) in HM.TH_POSTS:
        A(cyl(round(tx + px), round(ty + py), 10, 0, Z - 16, WCLIP, 8))
    # rail clip round the decks (players only), open over the stair and where the decks join
    for k in range(48):
        a0, a1 = 360 * k / 48, 360 * (k + 1) / 48
        am = (a0 + a1) / 2
        if any(g0 - 6 <= am + off <= g1 + 6 for off in (0, 360)) or -72 <= ((am + 180) % 360 - 180) <= 14: continue
        A(ring_seg(tx, ty, a0, a1, L.PLAT_R - 12, L.PLAT_R, Z, Z + 48, Z, Z + 48, CLIP))
    A(box((tx + dx0 + 194, ty + dy0, Z), (tx + dx1 - 12, ty + dy0 + 12, Z + 48), CLIP))
    A(box((tx + dx1 - 12, ty + dy0, Z), (tx + dx1, ty + dy1, Z + 48), CLIP))
    A(box((tx + dx0 + 194, ty + dy1 - 12, Z), (tx + dx1 - 12, ty + dy1, Z + 48), CLIP))
    route('spiral', ang_pt(tx, ty, 330, L.SPIRAL_A0 - 20) + (0,), ang_pt(tx, ty, 280, (g1 + 20) % 360) + (Z,))
    # the hut on the east deck
    tex = {'out': CAULK, 'in': T('planks_v'), 'jamb': T('wood_dark'), 'top': T('wood_dark'), 'bot': T('wood_dark'), 'glass': None}
    for w in HH.hut_walls(): wall_brushes(w, tex)
    hx0, hy0, hx1, hy1 = HH.hut_rect()
    H = Z + L.TH_HUT_H
    A(box((hx0 - 24, hy0 - 24, H), (hx1 + 24, hy1 + 24, H + 16), {'top': T('tin'), 'bot': T('planks'), 'side': T('wood_dark')}))
    custom('hut', (hx0 + hx1) / 2, (hy0 + hy1) / 2, Z)
    hcy = (hy0 + hy1) / 2
    route('hut_door', (hx0 - 90, hcy, Z), ((hx0 + hx1) / 2 + 30, hcy, Z))
    custom('candles_b', hx1 - 40, hy1 - 40, Z, lit=False)
    light((hx0 + hx1) / 2, hcy, Z + 120, 160, '1 0.6 0.3')
    item('ammo_imperius', hx1 - 50, hy0 + 50, Z)
    item('ammo_balloony', hx0 + 60, hy0 + 50, Z)
    weapon('betty', tx + 200, ty - 300, Z, 'black')
    # a pad up onto the round deck as well (bots skip long spiral climbs)
    px_, py_ = ang_pt(tx, ty, 640, 235)
    lx_, ly_ = ang_pt(tx, ty, 290, 235)
    jumppad(px_, py_, 0, (lx_, ly_, Z), Z + 260, 'deck_pad')
    item('item_armor_shard', *ang_pt(tx, ty, 260, 210), Z)
    # pad on the east deck up onto the hut roof (Boomies? -> ammo + powerup)
    jumppad(tx + 470, ty + 30, Z, ((hx0 + hx1) / 2, hcy, H + 16), H + 16 + 150, 'hut_roof')
    item('ammo_betty', (hx0 + hx1) / 2 - 40, hcy - 40, H + 16)
    item('item_armor_shard', (hx0 + hx1) / 2 + 50, hcy + 40, H + 16)
    # tyre swing on a branch on the west side, lanterns in the branches
    best = None
    for (pts, rad) in BR:
        for i in range(2, len(pts) - 1):
            p = pts[i]
            rh = math.hypot(p[0], p[1]); az = math.degrees(math.atan2(p[1], p[0])) % 360
            if 110 < az < 250 and 420 < rh < 640 and 560 < p[2] < 760:
                sc = abs(p[2] - 640) + abs(rh - 500)
                if best is None or sc < best[0]: best = (sc, p, rad[i])
    if best:
        p = best[1]
        pz = round(p[2] - best[2] * 0.8)
        px, py = round(tx + p[0]), round(ty + p[1])
        bottom = pz - HM.TIRE_ROPE - 70
        M.ent('func_pendulum', brushes=[box((px - 8, py - 8, pz - 8), (px + 8, py + 8, pz + 8), ORIGIN),
                                        box((px - 4, py - 4, bottom), (px + 4, py + 4, bottom + 8), NODRAW_NS)],
              model2=hwlib.IQM['tire_swing'], speed=14, angle=int(math.degrees(math.atan2(p[1], p[0]))) % 360, phase=0)
        TIRE[:] = [px, py, pz]
    lantern_pts = []
    for (bi, t, drop) in [(0, 0.55, 140), (2, 0.6, 120), (4, 0.5, 160), (5, 0.7, 110)]:
        pts, rad = BR[bi % len(BR)]
        p = pts[int(t * (len(pts) - 1))]
        light(tx + p[0], ty + p[1], p[2] - drop + 10, 140, '1 0.6 0.25')
    light(tx, ty, Z + 160, 260, '1 0.7 0.45')
    light(tx - 300, ty, 200, 200, '0.6 0.5 1')
    timer_sound(tx, ty, 900, 'sound/world/animal/bird_owl1.ogg', 'owl', 28, 15)
    speaker(tx, ty, 500, 'sound/world/ambient/metal_creaking.ogg', volume=0.25)
    spawn(tx - 200, ty + 400, 0, 315); spawn(tx + 400, ty + 300, 0, 200)


TIRE = [0, 0, 0]


# =================================================================================================== witch's cottage + cauldron
def cottage():
    X0, Y0, X1, Y1 = L.COT
    tex = {'out': CAULK, 'in': T('plaster'), 'jamb': T('wood_dark'), 'top': T('wood_dark'), 'bot': T('wood_dark'), 'glass': T('glass_broken')}
    for w in HH.cottage_walls(): wall_brushes(w, tex)
    CT = HH.CT
    A(box((X0 + CT, Y0 + CT, 0), (X1 - CT, Y1 - CT, L.COT_F), {'top': T('planks'), 'side': CAULK, 'bot': CAULK}))
    ov = HH.COT_OV; cy = (Y0 + Y1) / 2; hw = HH.COT_RIDGE_HW
    pts = [(x, y, L.COT_EAVE) for x in (X0 - ov, X1 + ov) for y in (Y0 - ov, Y1 + ov)] + \
          [(x, y, L.COT_RIDGE - 4) for x in (X0 - ov, X1 + ov) for y in (cy - hw, cy + hw)]
    A(hull(pts, lambda n: T('wood_dark') if n[2] < -0.9 else CAULK))
    c = HH.CHIM
    A(box((c[0], c[1], 0), (c[2] - 12, c[3], HH.CHIM_H), {'side': T('stone'), 'top': T('stone_dark'), 'bot': CAULK}))
    custom('cottage', (X0 + X1) / 2, cy, 0)
    custom('cottage_chimney', (c[0] + c[2]) / 2, (c[1] + c[3]) / 2, 0)
    route('cottage_door', (X1 + 200, -1232, 0), (X1 - 120, -1232, L.COT_F))
    # interior
    F = L.COT_F
    custom('bed', X0 + CT + 70, Y1 - CT - 108, F, angle=0)
    A(box((X0 + CT + 12, Y1 - CT - 214, F), (X0 + CT + 128, Y1 - CT - 2, F + 44), WCLIP))
    custom('black_cat', X0 + CT + 70, Y1 - CT - 150, F + 44, lit=False)
    custom('table_chair', -1560, -1250, F, angle=0)
    A(box((-1642, -1296, F), (-1478, -1204, F + 60), WCLIP))
    custom('witch_hat', -1590, -1240, F + 60, lit=False)
    custom('candles_b', -1520, -1262, F + 60, lit=False)
    custom('potion_shelf', -1400, Y1 - CT, F, angle=0)
    custom('small_cauldron', X0 + CT + 60, -1340, F, lit=True)
    A(cyl(X0 + CT + 60, -1340, 50, F, F + 76, WCLIP, 12))
    custom('lectern_book', -1420, -1340, F, angle=210)
    A(cyl(-1420, -1340, 26, F, F + 80, WCLIP, 8))
    custom('broom', X1 - CT - 30, -1340, F, angle=270, lit=False)
    weapon('bubbleg', -1640, -1150, F, 'blue')
    item('ammo_splasher', -1430, -1150, F)
    light(-1560, -1250, 190, 200, '0.5 1 0.4'); light(-1700, -1232, 120, 160, '1 0.55 0.2')
    speaker(-1560, -1232, 120, 'sound/world/animal/kitten_meow.ogg', loop=False, targetname='meow')
    M.ent('func_timer', (-1560, -1232, 170), target='meow', wait=30, random=15, spawnflags=1)
    M.ent('trigger_multiple', brushes=[box((X1 - CT - 40, -1280, F), (X1 - CT, -1184, F + 100), TRIG)], target='cackle', wait=25)
    speaker(-1560, -1232, 160, 'sound/world/misc/evil_laughter.ogg', loop=False, targetname='cackle')
    # outside: pad onto the roof ridge (Speedy up there), sign, garden pumpkins, broom rack
    jumppad(-1536, Y0 - 210, 0, (-1500, cy, L.COT_RIDGE), L.COT_RIDGE + 170, 'cot_roof')
    item('item_speedy', -1460, cy, L.COT_RIDGE - 4)
    item('ammo_bubbleg', -1680, cy, L.COT_RIDGE - 4)
    sign_post(X1 + 120, Y1 + 80, 'sign_witch', 160, 80, 'e', 96)
    for (x, y, nm) in ((X1 + 70, Y0 + 40, 'jack_s0'), (X1 + 70, Y1 - 30, 'jack_s1')):
        custom(nm, x, y, 0, angle=0, lit=False); light(x, y, 40, 90, '1 0.55 0.15')
        ball_clip(x, y, 0, HM.JACK['s'], HM.JACK['s'] * 1.6)
        KEEP_OUT.append((x, y, 70))
    station(X1 + 120, Y0 - 120, 0, 180)
    spawn(-2000, -1700, 0, 45); spawn(-1300, -1700, 0, 90)


def cauldron():
    cx, cy = L.CAUL
    custom('cauldron_big', cx, cy, 0)
    n = 24
    r_in = L.CAUL_IN / math.cos(math.pi / n)
    A(disc_brush(cx, cy, r_in, 52, L.CAUL_FLOOR, {'top': T('stone_dark'), 'side': CAULK, 'bot': CAULK}, n))
    A(disc_brush(cx, cy, 190, 0, 52, WCLIP, n))
    prof = np.array(HM.CAUL_PROFILE[:8], float)
    def rmin(z0, z1):
        zz = np.linspace(z0, z1, 12)
        return float(np.min(np.interp(zz, prof[:, 1], prof[:, 0])))
    bands = []
    zs = [L.CAUL_FLOOR, 120, 170, 220, 262, 290, L.CAUL_RIM]
    for (z0, z1) in zip(zs, zs[1:]):
        bands.append((z0, z1, rmin(z0, z1) - 8))
    for (z0, z1, ro) in bands:
        for k in range(n):
            a0, a1 = 360 * k / n, 360 * (k + 1) / n
            am = (a0 + a1) / 2
            A(ring_seg(cx, cy, a0, a1, L.CAUL_IN / math.cos(math.pi / n), ro, z0, z1, z0, z1,
                       ring_tex(am, inner=T('iron'), outer=CAULK, top=T('iron') if z1 == L.CAUL_RIM else CAULK, bot=CAULK, side=CAULK)))
    # steps up the inner wall (solid from the floor), carved out of the brew
    steps = []
    for (a0, a1, z) in L.caul_steps():
        b = ring_seg(cx, cy, a0, a1, 136, L.CAUL_IN - 2, L.CAUL_FLOOR, z, L.CAUL_FLOOR, z,
                     ring_tex((a0 + a1) / 2, inner=T('stone_dark'), outer=CAULK, top=T('stone'), side=T('stone_dark')))
        A(b); steps.append(b)
    water = hull([(px, py, z) for (px, py) in ngon(cx, cy, r_in, n, 0) for z in (L.CAUL_FLOOR, L.CAUL_WATER)], T('brew'), round_pts=False)
    for p in carve(water, steps):
        for f in p.faces:
            f.tex = T('brew') if f.n[2] > 0.99 and abs(max(q[2] for q in f.pts) - L.CAUL_WATER) < 0.5 else T('brew_nodraw')
            f.sc = (1, 1)
        A(p)
    weapon('splasher', cx - 40, cy + 60, L.CAUL_FLOOR, 'orange')
    item('ammo_splasher', cx + 70, cy - 80, L.CAUL_FLOOR)
    light(cx, cy, L.CAUL_WATER + 60, 260, '0.4 1 0.35'); light(cx, cy, 140, 300, '1 0.5 0.15')
    light(cx, cy, 30, 240, '1 0.5 0.15')
    speaker(cx, cy, L.CAUL_WATER, 'sound/world/ambient/slime_bubbling.ogg', volume=0.8)
    speaker(cx, cy, 40, 'sound/world/ambient/fire_crackling.ogg', volume=0.7)
    # a pad drops you into the brew from the east; the logs round the fire are low weapclip
    jumppad(cx + 420, cy, 0, (cx - 30, cy, L.CAUL_FLOOR), L.CAUL_RIM + 160, 'brew')
    KEEP_OUT.append((cx, cy, 360))


# =================================================================================================== corn maze
def corn_maze():
    X0, Y0, X1, Y1 = L.MAZE
    C = L.MAZE_CELL
    nx, ny = (X1 - X0) // C, (Y1 - Y0) // C
    rng = np.random.default_rng(27)
    centre = {(i, j) for i in range(2, 5) for j in range(2, 5)}
    # DFS maze over the cells, the centre 3x3 merged into one clearing
    links = set()
    def key(a, b): return (min(a, b), max(a, b))
    for a in centre:
        for b in centre:
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1: links.add(key(a, b))
    seen = set(centre); stack = [(2, 2)]
    order = list(centre)
    while stack:
        c = stack[-1]
        nb = [(c[0] + dx, c[1] + dy) for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        nb = [b for b in nb if 0 <= b[0] < nx and 0 <= b[1] < ny and b not in seen]
        if not nb:
            stack.pop(); continue
        b = nb[int(rng.integers(len(nb)))]
        links.add(key(c, b)); seen.add(b); stack.append(b)
    # a few extra openings so it isn't a single corridor (loops)
    for _ in range(4):
        i, j = int(rng.integers(nx - 1)), int(rng.integers(ny))
        links.add(key((i, j), (i + 1, j)))
    # walls: edges between unlinked neighbours + the north/west boundary (entrances left open)
    ent_w = 4                        # west entrance at row j = 4
    ent_n = 1                        # north entrance at column i = 1
    segs = []                        # ('h' (along x) or 'v', node i, node j)
    for i in range(nx):
        for j in range(ny):
            if i + 1 < nx and key((i, j), (i + 1, j)) not in links: segs.append(('v', i + 1, j))
            if j + 1 < ny and key((i, j), (i, j + 1)) not in links: segs.append(('h', i, j + 1))
    for j in range(ny):
        if j != ent_w: segs.append(('v', 0, j))
    for i in range(nx):
        if i != ent_n: segs.append(('h', i, ny))
    nodes = set()
    for (o, i, j) in segs:
        nodes.add((i, j)); nodes.add((i + 1, j) if o == 'h' else (i, j + 1))
    for (i, j) in nodes:
        x, y = X0 + i * C, Y0 + j * C
        if i == nx or j == 0: continue                  # on the east/south bank line
        A(box((x - 8, y - 8, 0), (x + 8, y + 8, L.MAZE_H), WCLIP))
    for (o, i, j) in segs:
        x, y = X0 + i * C, Y0 + j * C
        if o == 'h':
            A(box((x + 8, y - 8, 0), (x + C - 8, y + 8, L.MAZE_H), WCLIP))
            custom('corn_192', x + C / 2 - (10 if i == nx - 1 else 0), y, 0, angle=0, lit=False)
        else:
            A(box((x - 8, y + 8, 0), (x + 8, y + C - 8, L.MAZE_H), WCLIP))
            custom('corn_192', x, y + C / 2 + (10 if j == 0 else 0), 0, angle=90, lit=False)
    # corn along the bank edges (south, east), visual only
    for i in range(nx):
        custom('corn_192', X0 + i * C + C / 2 - (10 if i == nx - 1 else 0), Y0 + 20, 0, angle=0, lit=False)
    for j in range(ny):
        custom('corn_192', X1 - 20, Y0 + j * C + C / 2 + (10 if j == 0 else 0), 0, angle=90, lit=False)
    # centre clearing: a little stage with a scarecrow, Boaster, hay
    sx0, sy0 = X0 + 2 * C, Y0 + 2 * C
    stx0, sty0, stx1, sty1 = sx0 + 192, sy0 + 176, sx0 + 384, sy0 + 400
    A(box((stx0, sty0, 0), (stx1, sty1, 32), {'top': T('planks'), 'side': T('wood_dark'), 'bot': CAULK}))
    A(box((stx0 - 32, sty0 + 64, 0), (stx0, sty1 - 64, 16), {'top': T('planks'), 'side': T('wood_dark'), 'bot': CAULK}))
    scx, scy = (stx0 + stx1) / 2 + 40, sty1 - 50
    custom('scarecrow', scx, scy, 32, angle=270)
    A(cyl(round(scx), round(scy), 10, 32, 32 + HM.SCARE_H - 40, WCLIP, 8))
    for (u0, u1) in ((-110, -12), (12, 110)):
        A(rbx(scx, scy, 270, u0, u1, -14, 14, 32 + HM.SCARE_H - 140, 32 + HM.SCARE_H - 100, WCLIP))
    weapon('balloony', (stx0 + stx1) / 2 - 30, (sty0 + sty1) / 2 - 30, 32, 'green')
    route('maze_stage', (stx0 - 100, (sty0 + sty1) / 2, 0), ((stx0 + stx1) / 2 - 30, (sty0 + sty1) / 2 - 30, 32))
    for (x, y) in ((stx0 - 70, sty0 - 60), (stx1 + 60, sty0 - 40)):
        hay_stack(x, y, 0 if x < stx0 else 90)
    light((stx0 + stx1) / 2, (sty0 + sty1) / 2, 260, 260, '1 0.6 0.3')
    custom('jack_m0', 1830, -1180, 0, angle=270, lit=False); ball_clip(1830, -1180, 0, HM.JACK['m'], HM.JACK['m'] * 1.6)
    light(1830, -1180, 70, 150, '1 0.55 0.15')
    timer_sound(scx, scy, 300, 'sound/world/animal/bird_crow.ogg', 'crow2', 26, 14)
    # dead ends get items
    deg = {}
    for (a, b) in links:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    dead = [c for c in seen if deg.get(c, 0) == 1 and c not in centre and c not in ((0, ent_w), (ent_n, ny - 1))]
    dead.sort(key=lambda c: (c[0] * 7 + c[1] * 13) % 17)
    goods = ['holdable_bambam', 'ammo_boaster', 'ammo_balloony', 'item_armor_shard', 'ammo_pumper', 'holdable_floater']
    for c, g in zip(dead, goods):
        item(g, X0 + c[0] * C + C / 2, Y0 + c[1] * C + C / 2, 0)
    MAZE_INFO[:] = [len(segs), len(dead)]
    # signs at the entrances
    sign_post(X0 - 70, Y0 + ent_w * C + C + 60, 'sign_maze', 128, 64, 'w', 100)
    sign_post(X0 + ent_n * C + C + 70, Y1 + 70, 'sign_maze', 128, 64, 'n', 100)
    route('maze_west', (X0 - 150, Y0 + ent_w * C + C / 2, 0), (X0 + C / 2, Y0 + ent_w * C + C / 2, 0))
    route('maze_north', (X0 + ent_n * C + C / 2, Y1 + 150, 0), (X0 + ent_n * C + C / 2, Y1 - C / 2, 0))
    for (x, y) in ((X0 - 60, Y0 + ent_w * C - 60), (X0 + ent_n * C - 60, Y1 + 60)):
        light(x, y, 180, 160, '1 0.6 0.3')


MAZE_INFO = [0, 0]


# =================================================================================================== gate plaza + misc zones
def gate_plaza():
    gx, gy = L.GATE
    hw = L.GATE_W / 2 + 32
    for sx in (-1, 1):
        custom('gate_pillar', gx + sx * hw, gy, 0)
        A(box((round(gx + sx * hw) - 30, round(gy) - 30, 0), (round(gx + sx * hw) + 30, round(gy) + 30, 236), WCLIP))
        light(gx + sx * hw, gy - 40, 280, 180, '1 0.6 0.25')
        custom('jack_s1', gx + sx * hw, gy, 236, angle=0, lit=False)
        # low stone walls out from the pillars (cover)
        x0, x1 = (gx + sx * (hw + 30), gx + sx * 900)
        A(box((round(min(x0, x1)), round(gy) - 16, 0), (round(max(x0, x1)), round(gy) + 16, 64), {'side': T('stone'), 'top': T('stone_dark'), 'bot': CAULK}))
    custom('gate_arch', gx, gy, 0)
    A(sign_box((round(gx - 156), round(gy) - 3, 150), (round(gx + 156), round(gy) + 3, 210), T('sign_hollow'), 1024, 192, facing='s',
               back=T('wood_dark'), edge=T('wood_dark')))
    route('gate', (gx, gy - 250, 0), (gx, gy + 250, 0))
    speaker(gx, gy, 260, 'sound/world/ambient/metal_creaking.ogg', volume=0.35)
    # hearse (cover), benches, health
    custom('hearse', 560, -1880, 0, angle=0)
    A(box((430, -1940, 0), (690, -1820, 200), WCLIP))
    KEEP_OUT.append((560, -1880, 260))
    station(-420, -1900, 0, 90)
    station(400, -1500, 0, 270)
    for (x, y) in ((-260, -1500), (260, -1500), (-260, -1900)):
        lamppost(x, y)
    item('ammo_nipper', -150, -1820, 0)
    item('item_armor_shard', 150, -1800, 0)
    spawn(-120, -1950, 0, 90); spawn(220, -1960, 0, 110); spawn(-700, -1850, 0, 60); spawn(900, -1600, 0, 150)


def bonfire_zone():
    bx, by = L.BONFIRE
    custom('bonfire', bx, by, 0, lit=False)
    A(cyl(round(bx), round(by), 70, 0, 110, WCLIP, 12))
    for k in range(4):
        a = 45 + k * 90
        x, y = ang_pt(bx, by, 260, a)
        custom('log_bench', x, y, 0, angle=a + 90)
        A(rbx(x, y, a + 90, -106, 106, -18, 18, 0, 40, WCLIP))
        KEEP_OUT.append((x, y, 130))
    KEEP_OUT.append((bx, by, 340))
    light(bx, by, 120, 600, '1 0.5 0.15'); light(bx, by, 300, 300, '1 0.6 0.3')
    speaker(bx, by, 80, 'sound/world/ambient/fire_crackling.ogg', volume=0.9)
    item('ammo_balloony', bx + 120, by - 330, 0)
    item('ammo_bubbleg', bx - 330, by + 100, 0)
    spawn(bx + 350, by + 300, 0, 200)
    route('bonfire', (bx + 420, by, 0), (bx, by + 360, 0))


def market_zone():
    sx, sy = L.STAND
    custom('market_stand', sx, sy, 0, angle=0)
    A(box((round(sx) - 128, round(sy) - 64, 0), (round(sx) + 128, round(sy) + 64, 160), WCLIP))
    sign_post(sx - 220, sy - 140, 'sign_pumpkins', 112, 56, 's', 90)
    KEEP_OUT.append((sx, sy, 200))
    wx, wy = sx - 420, sy + 260
    custom('hay_wagon', wx, wy, 0, angle=20)
    A(rbx(wx, wy, 20, -160, 160, -96, 96, 0, 140, WCLIP))
    KEEP_OUT.append((wx, wy, 230))
    for (x, y, nm) in ((sx + 200, sy - 80, 'pump_a'), (sx + 220, sy + 120, 'pump_c'), (sx - 200, sy + 40, 'pump_f')):
        R = {'pump_a': 100, 'pump_c': 80, 'pump_f': 46}[nm]
        if free(x, y, R):
            custom(nm, x, y, 0, angle=int(x) % 360, lit=R >= 100); ball_clip(x, y, 0, R, R * 1.6 * 0.94); KEEP_OUT.append((x, y, R + 30))
    light(sx, sy - 140, 220, 220, '1 0.6 0.3')
    item('ammo_boaster', sx + 60, sy + 140, 0)
    spawn(sx + 300, sy + 250, 0, 180)


def well_zone():
    wx, wy = L.WELL
    custom('well', wx, wy, 0)
    A(cyl(round(wx), round(wy), 82, 0, 76, WCLIP, 16))
    for sx in (-1, 1):
        A(box((round(wx + sx * 74) - 6, round(wy) - 6, 76), (round(wx + sx * 74) + 6, round(wy) + 6, 220), WCLIP))
    KEEP_OUT.append((wx, wy, 140))
    item('ammo_boaster', wx + 150, wy - 100, 0)


# =================================================================================================== cover + dressing over the open ground
def dressing():
    rng = np.random.default_rng(41)
    placed = 0
    def put(fn, x, y, r):
        nonlocal placed
        p = near_free(x, y, r, 260)
        if p is None: return None
        fn(*p); KEEP_OUT.append((p[0], p[1], r)); placed += 1
        return p
    # dead trees in the open
    for (x, y, nm, s) in ((-1900, -800, 'tree_a', 1.1), (-500, -400, 'tree_b', 0.9), (700, 200, 'tree_c', 0.9), (-2100, 150, 'tree_b', 1.0),
                          (1950, -620, 'tree_a', 1.0), (-380, 680, 'tree_b', 0.8), (500, 900, 'tree_a', 0.8), (-900, -1700, 'tree_c', 1.0)):
        def f(px, py, nm=nm, s=s):
            custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), mul=s)
            A(cyl(round(px), round(py), round(36 * s), 0, round(480 * s), WCLIP, 8))
        put(f, x, y, 110)
    # hay stacks, pumpkins, crates of jack-o'-lanterns as cover in the middle band
    for (x, y, a) in ((-900, -500, 30), (650, -300, -20), (-400, 450, 60), (500, 500, 10), (-1200, 50, 80), (1100, -900, 0),
                      (-300, -1300, 45), (350, -1200, -45), (900, 1500 - 1700, 0)):
        put(lambda px, py, a=a: hay_stack(px, py, a), x, y, 170)
    big = [('pump_b', 140), ('pump_a', 100), ('pump_e', 120), ('pump_c', 80)]
    for i, (x, y) in enumerate(((-650, -150), (300, -820), (-200, 700), (900, -450), (-1100, -800), (200, 400), (-1700, 300), (1700, 150),
                                 (-2000, -1300), (0, -1350), (-700, 1050), (700, 1050))):
        nm, R = big[i % len(big)]
        def f(px, py, nm=nm, R=R):
            custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), lit=R >= 100); ball_clip(px, py, 0, R, R * 1.6 * 0.94)
        put(f, x, y, R + 40)
    for i, (x, y) in enumerate(((-450, -900), (450, -500), (-1000, 600), (1100, 200), (-1600, -600), (1600, -1900 + 1300), (-300, 300),
                                 (300, 650), (-1900, -100), (1900, -100))):
        nm = ['jack_m0', 'jack_l0', 'jack_m1', 'jack_s1', 'jack_g'][i % 5]
        R = HM.JACK[nm.split('_')[1][0]] if nm != 'jack_g' else HM.JACK['m']
        def f(px, py, nm=nm, R=R):
            custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), lit=False); ball_clip(px, py, 0, R, R * 1.6)
            light(px, py, R + 20, 80 + R, '1 0.55 0.15')
        put(f, x, y, R + 50)
    # lampposts along the paths
    for (x, y) in ((110, -1000), (-110, -600), (110, 450), (-110, 850), (-560, -720), (500, -720), (-1100, 330), (-600, 360), (700, 470),
                   (1000, 800), (-820, 1050)):
        p = (x, y) if free(x, y, 30) else near_free(x, y, 30, 120)
        if p: lamppost(*p); placed += 1
    # catalog dressing: autumn trees in the corners, bushes, garbage bags, tyres, spiders on the manor wall
    for (x, y, nm, s) in ((-2150, -1900 + 0, 'pad_ddmix/trashcan/tree_autumn.md3', 1.3), (2150, 0 + 150, 'pad_ddmix/trashcan/tree_autumn.md3', 1.2),
                          (-2150, -500, 'pad_ddmix/trashcan/bush.md3', 0.9), (850, -1950, 'pad_ddmix/trashcan/bush.md3', 0.8),
                          (-900, 250, 'pad_ddmix/trashcan/bush.md3', 0.8), (780, 1250, 'pad_ddmix/trashcan/bush.md3', 0.8)):
        def f(px, py, nm=nm, s=s): solid_mdl(nm, px, py, 0, s, int(rng.uniform(0, 360)))
        put(f, x, y, 200 * s if 'tree' in nm else 160 * s)
    for (x, y) in ((-1150, -1500), (700, -1350), (-150, 1000)):
        def f(px, py): mdl_c('pad_ddmix/trashcan/garbage_bag_group.md3', px, py, 0, 0.9, int(rng.uniform(0, 360)))
        put(f, x, y, 70)
    for (x, y) in ((-260, -250), (1300, 300)):
        def f(px, py): mdl_c('pad_ddmix/backyard/tire.md3', px, py, 0, 0.4, int(rng.uniform(0, 360)))
        put(f, x, y, 70)
    return placed


def crate_stack(x, y, a, n=3):
    """crates: 2 on the ground side by side + 1 on top (or 1 / 2), as cover"""
    C = HM.CRATE
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    spots = [(-C / 2 - 2, 0, 0), (C / 2 + 2, 0, 0), (-C / 4, 0, C)][:n]
    for k, (u, v, z) in enumerate(spots):
        bx, by = x + u * ca, y + u * sa
        custom('crate_p' if (k == 2 or n == 1) else 'crate_a', bx, by, z, angle=a + (8 if k == 2 else 0))
        A(rbx(bx, by, a + (8 if k == 2 else 0), -C / 2 + 2, C / 2 - 2, -C / 2 + 2, C / 2 - 2, z, z + C - (2 if z else 0), WCLIP))
    KEEP_OUT.append((x, y, C + 30))


def blockers():
    """extra cover where sightlines.py --hot showed the long eye-level rays (central and south band, the north strip)"""
    rng = np.random.default_rng(57)
    spots = [(-832, -832), (192, -576), (-192, -1216), (320, -576), (-64, -832), (-704, -960), (192, 64), (-704, -1472), (320, -64),
             (-960, -832), (-576, -832), (448, -576), (-1344, 1850), (-700, 1850), (700, 1850), (1300, 1850), (-2000, 1850), (2050, 1840), (960, 1860), (-1344, 1088), (-1088, -1600),
             (-1150, -1250), (560, -1100), (-300, -500), (900, 50)]
    n = 0
    for i, (x, y) in enumerate(spots):
        kind = ['crates', 'hay', 'crates', 'pump', 'tree'][i % 5] if y < 1700 else ['crates', 'hay'][i % 2]
        r = {'crates': 150, 'hay': 170, 'pump': 150, 'tree': 110}[kind]
        p = near_free(x, y, r, 260, pathgap=r * 0.7 + 72)
        if p is None:
            print('blocker skipped at', x, y); continue
        px, py = p
        a = int(rng.uniform(0, 180))
        if kind == 'crates': crate_stack(px, py, a, 3)
        elif kind == 'hay': hay_stack(px, py, a)
        elif kind == 'pump':
            custom('pump_b', px, py, 0, angle=a); ball_clip(px, py, 0, 140, 140 * 1.6 * 0.9 * 0.94); KEEP_OUT.append((px, py, 170))
        else:
            custom('tree_b', px, py, 0, angle=a, mul=0.9); A(cyl(round(px), round(py), 34, 0, 440, WCLIP, 8)); KEEP_OUT.append((px, py, 110))
        n += 1
    return n


# =================================================================================================== secret: the witch's lair
def lair():
    F = L.LAIR
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('lair_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('lair_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('stone_dark'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    # rune circle on the floor (glowing decal), dais with steps in the north (Pad Power)
    A(box((-240, -240, z0), (240, 240, z0 + 1), {'top': T('runes'), 'side': NODRAW_NS, 'bot': NODRAW_NS}))
    for f in M.world[-1].faces:
        if f.tex == T('runes'): f.sc = (480 / 512, 480 / 512); f.off = ((240 / (480 / 512)) % 512, (240 / (480 / 512)) % 512)
    A(box((-160, 260, z0), (160, y1, z0 + 32), {'top': T('lair_floor'), 'side': T('stone_dark'), 'bot': CAULK}))
    A(box((-96, 228, z0), (96, 260, z0 + 16), {'top': T('lair_floor'), 'side': T('stone_dark'), 'bot': CAULK}))
    item('item_padpower', 0, 320, z0 + 32)
    item('item_revival', -300, -250, z0)
    item('holdable_killerducks', 300, -250, z0)
    item('ammo_imperius', -330, 200, z0)
    item('ammo_splasher', 330, 200, z0)
    # crystal ball turning on a pedestal in the circle, potion shelves, cauldron, bats
    A(cyl(0, 0, 30, z0, z0 + 40, {'top': T('stone_dark'), 'side': T('stone_dark'), 'bot': CAULK}, 12))
    M.ent('func_rotating', brushes=[box((-8, -8, z0 + 40), (8, 8, z0 + 56), ORIGIN), box((-4, -4, z0 + 60), (4, 4, z0 + 68), NODRAW_NS)],
          model2=hwlib.IQM['crystal_ball'], speed=30, spawnflags=0, dmg=0)
    for (x, a) in ((-300, 0), (300, 0)):
        custom('potion_shelf', x, y1, z0, angle=a)
    custom('small_cauldron', -340, -60, z0, mul=1.4); A(cyl(-340, -60, 70, z0, z0 + 100, WCLIP, 12))
    custom('candles_c', 340, -60, z0, lit=False)
    bz = z0 + 380
    M.ent('func_rotating', brushes=[box((-8, -8, bz - 8), (8, 8, bz + 8), ORIGIN), box((-4, -4, bz + 40), (4, 4, bz + 48), NODRAW_NS)],
          model2=hwlib.IQM['bats_lair'], speed=-40, spawnflags=0, dmg=0)
    A(sign_box((-180, y0, z0 + 220), (180, y0 + 4, z0 + 400), T('sign_lair'), 512, 256, facing='n'))
    M.ent('misc_teleporter_dest', (0, -200, z0 + 24), targetname='lair_in', angle=90)
    mdl_c('pad_teleporter/padtp_purple.md3', 0, -330, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -366, z0 + 2), (36, -294, z0 + 90), TRIG)], target='lair_out')
    M.ent('misc_teleporter_dest', (0, -1460, 24), targetname='lair_out', angle=270)
    KEEP_OUT.append((0, -1460, 100))
    for (x, y, z, c) in ((0, 0, z0 + 200, '0.4 1 0.5'), (-300, 250, z0 + 300, '0.8 0.5 1'), (300, -250, z0 + 300, '0.8 0.5 1'), (0, 320, z0 + 200, '1 0.8 0.4')):
        light(x, y, z, 380, c)
    speaker(0, 0, z0 + 100, 'sound/world/ambient/slime_bubbling.ogg', volume=0.6)
    speaker(0, 0, z0 + 300, 'sound/world/misc/evil_laughter.ogg', loop=False, targetname='lair_laugh')
    M.ent('func_timer', (0, 0, z0 + 340), target='lair_laugh', wait=20, random=8, spawnflags=1)


# =================================================================================================== items, spawns, light, sound
def items_misc():
    item('ammo_nipper', 600, -1100, 0)
    item('ammo_nipper', -1600, -300 + 600, 0)
    item('item_armor_shard', -400, -1100 + 300, 0)
    item('item_armor_shard', 1400, -500, 0)
    item('ammo_bubbleg', 1700, 300 + 100, 0)
    item('ammo_bubbleg', -500, -1550, 0)
    item('ammo_boaster', 700, -150, 0)
    item('ammo_pumper', -1950, -1150, 0)
    item('ammo_betty', 1300, -150, 0)
    item('ammo_splasher', 900, 300 + 400, 0)


def spawns():
    pts = [(-600, -500), (600, -600), (1700, 100), (-2000, -400), (600, 1100), (-600, 1100)]
    for k, (x, y) in enumerate(pts):
        p = near_free(x, y, 40, 300)
        if p: spawn(p[0], p[1], 0, math.degrees(math.atan2(-p[1], -p[0])))


def lights_and_sound():
    # soft moonlit fill high up (the moon itself is the sun in the sky shader)
    for x in (-1700, -560, 560, 1700):
        for y in (-1500, -400, 700, 1700):
            light(x, y, 1200, 500, '0.55 0.6 1')
    timer_sound(-1800, 1600, 900, 'sound/world/animal/wolf_howl1.ogg', 'wolf1', 45, 20)
    timer_sound(1900, -1700, 900, 'sound/world/animal/wolf_howl2.ogg', 'wolf2', 55, 25)
    timer_sound(0, 0, 1600, 'sound/pad_ambiente/thunder03.wav', 'thunder', 70, 30, volume=0.5)
    timer_sound(-900, 1400, 600, 'sound/world/animal/bird_owl2.ogg', 'owl2', 33, 15)
    timer_sound(1500, 1100, 300, 'sound/world/animal/cricket_chirp1.ogg', 'cricket', 15, 8, volume=0.4)
    speaker(0, 0, 1500, 'sound/world/ambient/wind_night.ogg', volume=0.35)
    speaker(-1600, 1000, 300, 'sound/world/ambient/wind_night.ogg', volume=0.3)
    speaker(1600, -1200, 300, 'sound/world/ambient/shrubbery.ogg', volume=0.3)


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'mist', 'glass_broken', 'dirt_ns', 'carpet_ns', 'jumppad_ns', 'runes',
                'origin', 'brew', 'botclip')


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
            # brush vertices inside the box
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
                # keep the same floor: something solid just below
                if not blocked(p, lo, hi) and blocked(p + np.array([0, 0, lo[2] - 8]), np.array([-4, -4, -2]), np.array([4, 4, 2])):
                    e['origin'] = ' '.join(fmt([v]) for v in np.round(p)); moved.append((c, o.astype(int).tolist(), np.round(p).astype(int).tolist()))
                    done = True; break
            if done: break
        if not done: moved.append((c, o.astype(int).tolist(), 'STUCK'))
    return moved


def write_routes():
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padhalloween/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_halloween.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== main
def main():
    TX.make_all(OUT, extra_models)
    hull_and_banks(); ground()
    manor(); n_tombs = graveyard(); mausoleum(); nb = pumpkin_patch(); hanging_tree(); cottage(); cauldron(); corn_maze()
    gate_plaza(); bonfire_zone(); market_zone(); well_zone(); lair()
    items_misc(); spawns()
    n_paths = paths()
    n_dress = dressing()
    blockers()
    lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    M.ent('info_player_intermission', (-1400, -1900, 700), angles='12 50 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padhalloween/build_halloween.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}, tombs {n_tombs}, gp wedges {nb}, path decals {n_paths}, '
          f'dressing {n_dress}, maze segs/deadends {MAZE_INFO}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
