#!/usr/bin/env python3
"""Candy Garden - World of Padman FFA map generator (map 'wop_padcandy').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_candy.py

Writes <OUT>/maps/wop_padcandy.map, textures/padcandy/*, models/padcandy/*, scripts/padcandy.shader and
scripts/wop_padcandy.arena.

A sweet factory's candy room under a glass roof: an emerald meadow where everything is edible, a chocolate river
fed by a chocolate waterfall pouring off a limestone cliff, giant mushrooms, crepe-paper flower trees, a gumball tree,
a lollipop grove, a pump house on an iron deck with candy-coloured pipes dipping into the river and a glass suction
pipe that slurps you up onto the cliff. Padman is gummy-bear sized (~200u per metre). x east, y north, meadow z 0.

  Balcony + lobby   south: the entrance gallery with ornate iron railings and two grand staircases down to the meadow;
                    the lobby behind it (golden ticket, chocolate bars, health).
  Chocolate falls   north: the falls pour off the summit into a deep plunge pool (Splasher on the bottom). Walk along
                    the ledge behind the falling chocolate into the rock-candy cave (Pad shield) and climb the spiral
                    stair inside the cliff to the summit (Imperius, with applause).
  Chocolate river   meanders from the pool to a tunnel in the west wall (wade anywhere, banks walk out); candy-cane
                    bridge, iron stair-bridge, peppermint stepping stones, a pink swan boat at its jetty (Boaster).
  Suction pipe      a glass pipe in the river: step into its intake and it slurps you up onto the summit.
  Pump house        north-west: iron deck on lattice columns (stair-bridge up), the shed (walk in: Pumper), a pad to
                    the shed roof, a pad from the roof to the summit.
  Red fly agaric    centre: walk under it (Bubble G), pad onto the cap (Floater).
  Yellow mushroom   south-east: a house - walk in through the door; pad onto the cap (Balloony).
  Flower tree       west, on a rockery mound: pad onto the crepe-paper dome (Betty).
  Lollipop grove    south-west: lollipops, spinning hypno-discs, twisted candy stalks, buttercups (Visionless hidden).
  Tunnel of Wonder  SECRET: wade into the river tunnel in the west wall -> the Fizzy Lifting Room (bubbles lift you up
                    to the gallery under the fan: Pad Power, Revival; Killer Ducks on the floor; teleporter back).
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import candy_textures as TX
import candy_models as CM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padcandy'
T = lambda n: 'padcandy/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'grass': (1, 1), 'path_ns': (0.5, 0.5), 'rock': (1, 1), 'rock_top': (1, 1), 'cave': (1, 1), 'choc_bank': (0.5, 0.5),
             'choc_floor': (0.5, 0.5), 'wall_stone': (0.5, 0.5), 'cornice': (0.5, 0.5), 'window': (1.5, 1.5), 'roofglass': (2, 2),
             'grate': (0.5, 0.5), 'planks': (0.5, 0.5), 'damask': (0.5, 0.5), 'checker': (0.5, 0.5), 'carpet': (0.5, 0.5),
             'tunnel': (0.5, 0.5), 'fizzy_wall': (0.5, 0.5), 'fizzy_floor': (1, 1), 'chocolate': (1, 1), 'stone_dark': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '22', '_color': '1 0.95 0.9', 'gridsize': '128 128 128', '_blocksize': '0'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
KEEP_OUT = []                       # (x, y, r) discs where floor decoration must not go
RIVER_SOLIDS = []                   # solid brushes standing in the river (carved out of the ground and the water)


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
    """one of our own MD3s (models/padcandy), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = CM.PLACE[name] if isinstance(name, str) else name
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, **extra)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex, round_pts=False)


def light(x, y, z, val, color='1 0.9 0.8', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
    M.ent('func_timer', (round(x), round(y), round(z + 40)), target=name, wait=wait, random=rnd, spawnflags=1)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))
    KEEP_OUT.append((x, y, 40))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))
    KEEP_OUT.append((x, y, 50))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=ang % 360)
    SPOTS['spawn'].append((x, y, floor))
    KEEP_OUT.append((x, y, 60))


def hfit(b, x0, y0, x1, y1, tw, th, tex):
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.7: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def jumppad(x, y, z, land, apex, name, glow=True):
    """candy-swirl pad (r 34 disc) + trigger_push + target_position (AimAtTarget: the target is the apex, measured
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
    if glow: light(x, y, z + 48, 110, '1 0.6 0.9')
    KEEP_OUT.append((x, y, 80))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def sprite(x, y, z0, z1, tex, w, ang=0):
    a = math.radians(ang); dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2; nx, ny = -math.sin(a), math.cos(a)
    q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx * 2, y + dy + ny * 2), (x - dx + nx * 2, y - dy + ny * 2)]
    def tf(n, nx=nx, ny=ny):
        return T(tex) if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
    b = hull([(px, py, zz) for (px, py) in q for zz in (z0, z1)], tf, round_pts=False)
    for f in b.faces:
        if f.tex == T(tex): f.sc = (w / 128, (z1 - z0) / 512); f.off = (0, 0)
    return b


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def ring_seg(cx, cy, k, n, r0, r1, z0a, z1a, z0b, z1b, tex):
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
    pts = []
    for k in range(n):
        px, py = ang_pt(cx, cy, r, k * 360.0 / n)
        pts += [(px, py, z0), (px, py, z1)]
    if z1c is not None: pts.append((cx, cy, z1c))
    return hull(pts, tex, round_pts=False)


def rbox(cx, cy, ang, u0, u1, v0, v1, z0, z1, tex, z0e=None, z1e=None):
    """box in a rotated frame: u along `ang` (deg), v to its left; optional z at u1 (ramps): z0e/z1e"""
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
    z0e = z0 if z0e is None else z0e; z1e = z1 if z1e is None else z1e
    pts = []
    for u, za, zb in ((u0, z0, z1), (u1, z0e, z1e)):
        for v in (v0, v1):
            px, py = cx + ux * u + vx * v, cy + uy * u + vy * v
            pts += [(px, py, za), (px, py, zb)]
    return hull(pts, tex, round_pts=False)


PATHS = [[(-2050, -1620), (-1100, -1500), (-500, -1150), (0, -900), (500, -1150), (1100, -1500), (2050, -1620)],
         [(0, -900), (-480, -600), (-560, -150), (-300, 200), (100, 380), (470, 560)],
         [(-560, -150), (-380, -30)],
         [(500, -1150), (700, -300), (900, 300), (1000, 700), (1090, 1250), (1000, 1420)],
         [(-1100, -1500), (-1250, -600), (-1300, -200), (-1080, 160)],
         [(130, 1110), (330, 1300), (560, 1380)]]


def path_dist(x, y):
    best = 1e9
    for r in PATHS:
        for (a, b) in zip(r, r[1:]):
            ax, ay = a; bx, by = b
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def free(x, y, r, land=True, path=True):
    if path and path_dist(x, y) < r + 84: return False
    if y < L.BALC[3] + r + 24 and abs(x) < L.BALC[2] + 32 * (L.BALC_Z // 16) + r + 24: return False
    if abs(x) > L.HX - r - 16 or y < L.YS + r + 16 or y > L.cliff_foot_y(x) - r - 16: return False
    if land and not L.on_land(x, y, r): return False
    return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT)


def near_free(x, y, r, search=400, pathgap=None):
    ok = (lambda px, py: free(px, py, r)) if pathgap is None else \
         (lambda px, py: free(px, py, r, path=False) and path_dist(px, py) > pathgap)
    if ok(x, y): return (x, y)
    for d in range(32, search + 1, 32):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if ok(px, py): return (round(px), round(py))
    return None


def ball_clip(x, y, z0, r, n=12):
    """weapon-clip polyhedron approximating a sphere of radius r resting on z0"""
    zc = z0 + r
    pts = []
    for k, ph in enumerate(np.linspace(-math.pi / 2 + 0.35, math.pi / 2 - 0.25, 5)):
        rr = r * math.cos(ph) * 0.92
        for (px, py) in ngon(x, y, max(rr, 4), n):
            pts.append((px, py, zc + r * math.sin(ph) * 0.95))
    pts += [(x, y, z0 + 2)]
    A(hull(pts, WCLIP, round_pts=False))


# =================================================================================================== hall: hull, walls, roof
def hall():
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
    HX, YS, YN, R = L.HX, L.YS, L.YN, L.ROOF
    WT = L.WALL_T
    stone = {'side': CAULK, 'top': T('cornice'), 'bot': CAULK}
    # walls: (axis, fixed coordinate of the inner face, outward sign, run from, run to, stone height, openings)
    walls = [('y', YS, -1, -HX - WT, HX + WT, 768, [(-L.LOBBY_DOOR[1], L.LOBBY_DOOR[1], L.BALC_Z, L.BALC_Z + L.LOBBY_DOOR[2]),
                                                    (-480, -240, 448, 640), (240, 480, 448, 640)]),
             ('y', YN, 1, -HX - WT, HX + WT, 1104, []),
             ('x', -HX, -1, YS, YN, L.STONE_Z, [(L.TUNNEL['y0'], L.TUNNEL['y1'], L.RIV_FLOOR, L.TUNNEL['z1'])]),
             ('x', HX, 1, YS, YN, L.STONE_Z, [])]
    for (ax, f, sg, a0, a1, sz, holes) in walls:
        def wb(u0, u1, z0_, z1_, tex):
            if ax == 'y':
                yy0, yy1 = (f - WT, f) if sg < 0 else (f, f + WT)
                return box((u0, yy0, z0_), (u1, yy1, z1_), tex)
            xx0, xx1 = (f - WT, f) if sg < 0 else (f, f + WT)
            return box((xx0, u0, z0_), (xx1, u1, z1_), tex)
        inner = {'y': {1: 's', -1: 'n'}, 'x': {1: 'w', -1: 'e'}}[ax][sg]
        tex = dict(stone); tex[inner] = T('wall_stone')
        # stone band with holes, as columns of z ranges
        cuts = sorted(set([a0, a1] + [h[0] for h in holes] + [h[1] for h in holes]))
        for ua, ub in zip(cuts, cuts[1:]):
            hz = [(h[2], h[3]) for h in holes if h[0] <= ua and h[1] >= ub]
            zs = [L.SLAB_BOT]
            for (hz0, hz1) in sorted(hz): zs += [hz0, hz1]
            zs.append(sz)
            for k in range(0, len(zs) - 1, 2):
                if zs[k + 1] > zs[k]:
                    t2 = dict(tex)
                    if k > 0: t2['bot'] = T('wall_stone')
                    if k + 2 < len(zs) - 1 or (k + 1 < len(zs) - 1 and zs[k + 1] != sz): t2['top'] = T('wall_stone')
                    A(wb(ua, ub, zs[k], zs[k + 1], t2))
        # window band: piers every 384 + glass panes (glass in the outer half of the wall)
        zt = R - 64
        n = int(round((a1 - a0) / 384))
        step = (a1 - a0) / n
        for i in range(n):
            pa, pb = a0 + i * step, a0 + i * step + 64
            A(wb(round(pa), round(pb), sz, zt, tex))
            ga, gb = round(pb), round(a0 + (i + 1) * step)
            if ax == 'y':
                yy0, yy1 = (f - 20, f - 12) if sg < 0 else (f + 12, f + 20)
                A(box((ga, yy0, sz), (gb, yy1, zt), T('window')))
            else:
                xx0, xx1 = (f - 20, f - 12) if sg < 0 else (f + 12, f + 20)
                A(box((xx0, ga, sz), (xx1, gb, zt), T('window')))
        A(wb(round(a1 - 64) if False else round(a0 + n * step - 0), round(a1), sz, zt, tex)) if False else None
        # cornice band at the top
        A(wb(a0, a1, zt, R, dict(tex, **{inner: T('cornice')})))
    # glass roof over everything (sitting on the walls)
    A(box((-HX - WT, YS - WT, R), (HX + WT, YN + WT, R + 8), T('roofglass')))
    # iron trusses under the roof
    for y in (-1440, -720, 0, 720, 1440):
        custom('truss', 0, y, R - 2, angle=0)
    # pipe runs high on the east and west walls
    for (x, ang) in ((-HX + 8, 90), (HX - 8, 270)):
        for y in (-900, 900):
            custom('wallpipes', x + (14 if x < 0 else -14), y, 1250, angle=ang)


# =================================================================================================== ground, river, pool
def clip_half(b, axis, lo=None, hi=None):
    """the part of brush b with lo <= coordinate <= hi (exact, via carve against big boxes)"""
    big = 100000
    cut = []
    if lo is not None:
        mn = [-big] * 3; mx = [big] * 3; mx[axis] = lo
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    if hi is not None:
        mn = [-big] * 3; mx = [big] * 3; mn[axis] = hi
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    return carve(b, cut)


def river_cutters(top_z=16.0, bot_z=None, hw_top=None, hw_bot=None, clip_x=-L.HX):
    """convex pieces (segments + joints) whose union is the river channel between bot_z and top_z"""
    bot_z = L.RIV_FLOOR if bot_z is None else bot_z
    slope = (240.0 - 172.0) / 56.0
    hw = lambda z: 172.0 + (z - L.RIV_FLOOR) * slope
    ht, hb = hw(top_z) if hw_top is None else hw_top, hw(bot_z) if hw_bot is None else hw_bot
    P = L.river_points(64)
    # stop at the west wall; start where the centreline leaves the pool
    P = [p for p in P if p[0] >= -L.HX]
    P = [p for p in P if math.hypot(p[0] - L.POOL[0], p[1] - L.POOL[1]) > L.POOL_R - 60]
    P = np.array(P)
    # keep every ~4th point plus the end
    idx = list(range(0, len(P), 4))
    if idx[-1] != len(P) - 1: idx.append(len(P) - 1)
    Q = P[idx]
    if Q[-1][0] > -L.HX + 1: Q = np.vstack([Q, [[-L.HX, -300]]])
    out = []
    for i in range(len(Q) - 1):
        a, b = Q[i], Q[i + 1]
        d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
        pts = []
        for p in (a, b):
            for s in (-1, 1):
                pts += [(*(p + n * s * ht), top_z), (*(p + n * s * hb), bot_z)]
        out.append(hull(pts, CAULK, round_pts=False))
    for i in range(1, len(Q) - 1):
        out.append(frustum(Q[i][0], Q[i][1], hb, bot_z, ht, top_z, CAULK, 16))
    res = []
    for b in out:
        mn, mx = b.bounds()
        res += clip_half(b, 0, lo=clip_x) if mn[0] < clip_x else [b]
    return res


def pool_cutter(top_z=16.0, bot_z=None):
    bot_z = L.POOL_FLOOR if bot_z is None else bot_z
    r_at = lambda z: 200 + (z - L.POOL_FLOOR) * (L.POOL_R + 20 - 200) / (16 - L.POOL_FLOOR)
    pts = []
    for z in (bot_z, top_z):
        for (x, y) in ngon(L.POOL[0], L.POOL[1], r_at(z), 24):
            pts.append((x, y, z))
    return clip_half(hull(pts, CAULK, round_pts=False), 1, hi=1400)


def tex_ground(b):
    for f in b.faces:
        if f.n[2] > 0.99 and abs(max(p[2] for p in f.pts)) < 0.5: f.tex = T('grass')
        elif f.n[2] < -0.99: f.tex = CAULK
        elif abs(f.n[2]) < 1e-3 and (abs(abs(f.n[0]) - 1) < 1e-6 or abs(abs(f.n[1]) - 1) < 1e-6) and _on_tile_edge(f): f.tex = CAULK
        elif f.n[2] > 0.99: f.tex = T('choc_floor')
        else: f.tex = T('choc_bank')
        f.sc = wopmap.default_scale(f.tex)
    return b


_TILES = []


def _on_tile_edge(f):
    for (x0, y0, x1, y1) in _TILES:
        if abs(f.n[0]) > 0.99 and abs(f.d * f.n[0] - (x0 if f.n[0] < 0 else x1)) < 0.5: return True
        if abs(f.n[1]) > 0.99 and abs(f.d * f.n[1] - (y0 if f.n[1] < 0 else y1)) < 0.5: return True
    return False


def ground():
    HX, YS, YN = L.HX, L.YS, L.YN
    cut = river_cutters() + pool_cutter() + RIVER_SOLIDS
    step = 512
    for x0 in range(-HX, HX, step):
        for y0 in range(YS, YN, step):
            x1, y1 = min(x0 + step, HX), min(y0 + step, YN)
            tile = box((x0, y0, L.SLAB_BOT), (x1, y1, 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK})
            mine = []
            for c in cut:
                mn, mx = c.bounds()
                if mn[0] < x1 and mx[0] > x0 and mn[1] < y1 and mx[1] > y0: mine.append(c)
            if not mine:
                A(tile); continue
            _TILES.append((x0, y0, x1, y1))
            for b in carve(tile, mine):
                A(tex_ground(b))
    for b in RIVER_SOLIDS: A(b)
    # chocolate: river water pieces made disjoint, pool water, minus the solids standing in it
    wt = lambda n: T('chocolate') if n[2] > 0.99 else T('choc_nodraw')
    wcuts = river_cutters(top_z=L.WATER) + pool_cutter(top_z=L.WATER)
    done = []
    for c in wcuts:
        pieces = carve(c, done + RIVER_SOLIDS) if (done or RIVER_SOLIDS) else [c]
        for p in pieces:
            for f in p.faces:
                f.tex = wt(f.n); f.sc = (1, 1)
            A(p)
        done.append(c)
    # tunnel: channel floor + water through the west wall (x -2700..-2304)
    t = L.TUNNEL
    A(box((t['x0'], t['y0'] - 32, L.SLAB_BOT), (-HX - 32, t['y1'] + 32, L.RIV_FLOOR), {'top': T('choc_floor'), 'side': CAULK, 'bot': CAULK}))
    w = box((t['x0'], t['y0'], L.RIV_FLOOR), (-HX, t['y1'], L.WATER), wt)
    for f in w.faces: f.tex = wt(f.n); f.sc = (1, 1)
    A(w)
    tw = {'side': T('tunnel'), 'top': CAULK, 'bot': T('tunnel')}
    A(box((t['x0'], t['y0'] - 32, L.RIV_FLOOR), (-HX - 32, t['y0'], t['z1']), tw))
    A(box((t['x0'], t['y1'], L.RIV_FLOOR), (-HX - 32, t['y1'] + 32, t['z1']), tw))
    A(box((t['x0'], t['y0'] - 32, t['z1']), (-HX - 32, t['y1'] + 32, t['z1'] + 32), tw))
    A(box((t['x0'] - 32, t['y0'] - 32, L.RIV_FLOOR), (t['x0'], t['y1'] + 32, t['z1'] + 32), tw))
    # the tunnel is the SECRET: secret sound, then a teleport into the Fizzy Lifting Room
    M.ent('trigger_multiple', brushes=[box((-2500, t['y0'], L.RIV_FLOOR), (-2440, t['y1'], t['z1']), TRIG)], target='secret_snd', wait=8)
    speaker(-2470, -300, 120, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('trigger_teleport', brushes=[box((-2640, t['y0'], L.RIV_FLOOR), (-2600, t['y1'], t['z1']), TRIG)], target='fizz_in')
    speaker(-2500, -300, 100, 'sound/world/tunnel/wp1.ogg', volume=0.7)
    for x in (-2380, -2560):
        light(x, -300, 220, 220, '0.9 0.5 1')
    sb = sign_box((-2290, t['y0'] - 8, t['z1'] + 24), (-2274, t['y1'] + 8, t['z1'] + 104), T('sign_tunnel'), 512, 128, facing='e')
    A(sb)


# =================================================================================================== the cliff
def cliff_cutters():
    c = []
    x0, y0, x1, y1 = L.CAVE
    c.append(('cave', box((x0, y0, 0), (x1, y1, L.CAVE_Z), CAULK)))
    x0, y0, x1, y1 = L.WELL
    c.append(('cave', box((x0, y0, 0), (x1, y1, L.SUMMIT_Z + 8), CAULK)))
    x0, y0, x1, y1 = L.CHANNEL
    c.append(('bank', box((x0, y0 - 40, L.CHANNEL_FLOOR), (x1, y1, L.SUMMIT_Z + 8), CAULK)))
    x0, y0, x1, y1 = L.DECK
    c.append(('hide', box((x0, y0, L.DECK_Z - 16), (x1, y1, L.DECK_Z + 8), CAULK)))
    c.append(('rock', box((2080, 1200, 0), (L.HX, 1504, 520), CAULK)))          # east shoulder stair notch
    return c


def cliff():
    """stacked limestone courses: every chunk has its own course heights and a slanted, jittered front, so the
    strata stagger like a real rock wall; faces next to the cave/well/channel/deck are textured after carving"""
    rng = np.random.default_rng(31)
    cuts = cliff_cutters()
    pieces = []
    for (x0, x1, fy, ty, tz) in L.CLIFF_SEGS:
        steep = (ty - fy) < 60
        jmax = 10 if steep else 34
        xs = [float(x0)]
        while xs[-1] < x1:
            xs.append(min(float(x1), xs[-1] + float(rng.integers(150, 290))))
        if len(xs) > 2 and xs[-1] - xs[-2] < 110: xs.pop(-2)
        for (xa, xb) in zip(xs, xs[1:]):
            zs = [0]
            while zs[-1] < tz:
                zs.append(min(tz, zs[-1] + int(rng.integers(56, 116))))
            if len(zs) > 2 and tz - zs[-2] < 56: zs.pop(-2)
            for k in range(len(zs) - 1):
                za, zb = zs[k], zs[k + 1]
                last = k == len(zs) - 2
                zm = tz if last else (za + zb) / 2
                base = fy + (ty - fy) * (zm / tz)
                ya = min(base + float(rng.uniform(0, jmax)), L.YN - 32); yb = min(base + float(rng.uniform(0, jmax)), L.YN - 32)
                pts = [(xa, ya, za), (xa, ya, zb), (xb, yb, za), (xb, yb, zb), (xa, L.YN, za), (xa, L.YN, zb), (xb, L.YN, za), (xb, L.YN, zb)]
                top = T('rock_top') if last else T('rock')
                pieces.append(hull(pts, {'top': top, 'bot': CAULK, 'n': CAULK, 'side': T('rock')}, round_pts=False))
    for b in pieces:
        mn, mx = b.bounds()
        mine = [(kind, c) for (kind, c) in cuts if np.all(c.bounds()[0] < mx - 0.5) and np.all(c.bounds()[1] > mn + 0.5)]
        if not mine:
            A(b); continue
        for p in carve(b, [c for _, c in mine]):
            for f in p.faces:
                for (kind, c) in mine:
                    if any(abs(f.n[0] + cn[0]) < 1e-4 and abs(f.n[1] + cn[1]) < 1e-4 and abs(f.n[2] + cn[2]) < 1e-4 and abs(f.d + cd) < 0.5
                           for (cn, cd) in c.planes()):
                        if kind == 'bank': f.tex = T('choc_floor') if f.n[2] > 0.7 else T('rock')
                        else: f.tex = {'cave': T('cave'), 'hide': CAULK, 'rock': T('rock')}[kind]
                        f.sc = wopmap.default_scale(f.tex)
            A(p)
    # boulders + plants along the foot of the cliff and on the shoulders
    for (x, y, nm, s, a) in ((-2120, 1240, 'boulder_a', 1.2, 10), (-1300, 1250, 'boulder_b', 1.0, 80), (-200, 1350, 'boulder_a', 0.9, 200),
                             (250, 1370, 'boulder_b', 1.1, 300), (1150, 1380, 'boulder_a', 1.0, 140), (1650, 1260, 'boulder_b', 1.2, 30),
                             (2150, 1260 - 900, 'boulder_a', 0.8, 260)):
        if free(x, y, 90 * s):
            custom(nm, x, y, 0, angle=a, mul=s)
            A(cyl(round(x), round(y), round(66 * s), 0, round(70 * s), WCLIP, 10))
            KEEP_OUT.append((x, y, 100 * s))
    for (x, y, z, nm, s, a) in ((-1900, 1700, 448, 'pad_ddmix/plants/fern.md3', 0.6, 30), (-1500, 1800, 448, 'pad_sunflower/pad_sunflower_l.md3', 0.9, 200),
                                (-2150, 1820, 448, 'pad_ddmix/trashcan/bush.md3', 0.8, 120), (1700, 1700, 480, 'pad_ddmix/plants/fern.md3', 0.55, 300),
                                (2150, 1700, 480, 'pad_sunflower/pad_sunflower_l.md3', 0.9, 60), (-300, 1720, 1040, 'pad_ddmix/plants/fern.md3', 0.45, 160)):
        mdl_c(nm, x, y, z, s, a)
    for (x, y, z) in ((-1750, 1650, 448), (-1250, 1700, 448), (1900, 1600, 480)):
        custom('flower_b', x, y, z, angle=int(x) % 360, lit=False)


# =================================================================================================== waterfall, cave, stair well, summit
def falls():
    fx = L.FALL_X
    custom('waterfall', fx, 0, 0, lit=False)
    # bubbling splash ring where the fall hits the pool: turns slowly (func_rotating), so it needs no support
    sy = CM.fall_curve(28)[-1][0]
    M.ent('func_rotating', brushes=[box((fx - 8, round(sy) - 8, L.WATER - 8), (fx + 8, round(sy) + 8, L.WATER + 8), ORIGIN),
                                    box((fx - 4, round(sy) - 4, L.WATER - 4), (fx + 4, round(sy) + 4, L.WATER + 4), NODRAW_NS)],
          model2=CM.PLACE['splash'][0], speed=6, spawnflags=0, dmg=0)
    custom('outlet', fx, L.YN - 2, L.SUMMIT_Z, angle=0)
    # summit channel water (spills over the lip)
    x0, y0, x1, y1 = L.CHANNEL
    w = box((x0, y0, L.CHANNEL_FLOOR), (x1, y1, L.SUMMIT_Z - 8), CAULK)
    for f in w.faces: f.tex = T('chocolate') if f.n[2] > 0.99 else T('choc_nodraw'); f.sc = (1, 1)
    A(w)
    # weapon clip so rockets don't fly through the curtain? no - the curtain is liquid. Sounds + light.
    speaker(fx, 1250, 120, 'sound/world/ambient/water_falling.ogg', volume=1.0)
    speaker(fx, 1600, 1080, 'sound/world/ambient/water_flowing.ogg', volume=0.6)
    speaker(fx, 1180, 40, 'sound/world/ambient/water_bubbling.ogg', volume=0.5)
    # Splasher on the bottom of the plunge pool
    weapon('splasher', fx - 60, 1060, L.POOL_FLOOR, 'orange')
    item('ammo_bubbleg', fx + 120, 1120, L.POOL_FLOOR)
    for (x, y) in ((fx - 120, 1000), (fx + 140, 1240)):
        light(x, y, -150, 260, '1 0.7 0.4')
    KEEP_OUT.append((fx, 1180, L.POOL_R + 40))


def cave_and_well():
    x0, y0, x1, y1 = L.CAVE
    cx = (x0 + x1) / 2
    # rock candy crystals on the cave floor (glowing) + lights
    for (x, y, nm, a) in ((x0 + 70, y0 + 120, 'crystal_a', 30), (x0 + 90, y1 - 100, 'crystal_b', 200), (x1 - 100, y1 - 100, 'crystal_a', 120),
                          (cx + 20, y1 - 110, 'crystal_b', 300)):
        custom(nm, x, y, 0, angle=a, lit=False)
        KEEP_OUT.append((x, y, 90))
    for (x, y, c) in ((x0 + 100, y0 + 160, '1 0.6 0.9'), (cx, y1 - 90, '0.6 0.8 1'), (x1 - 100, y1 - 100, '1 0.9 0.6')):
        light(x, y, 200, 300, c)
    item('item_armor_padshield', cx - 40, y0 + 210, 0)
    item('ammo_imperius', x0 + 90, y1 - 170, 0)
    item('ammo_boaster', cx + 120, y0 + 110, 0)
    speaker(cx, y0 + 150, 120, 'sound/world/ambient/droplets_echoing.ogg', volume=0.6)
    # square spiral stair round a central pillar inside the well, up to the summit
    wx0, wy0, wx1, wy1 = L.WELL
    wcx, wcy = (wx0 + wx1) / 2, (wy0 + wy1) / 2
    P = L.WELL_PILLAR
    A(box((wcx - P, wcy - P, 0), (wcx + P, wcy + P, L.SUMMIT_Z - 32), T('cave')))
    hw = (wx1 - wx0) / 2
    ring = hw - P                     # 128
    # the path: start on the west side heading south, counter-clockwise; items: ('step'|'land', rect, ztop)
    seq = []
    z = 0
    side = 0                          # 0: west going south, 1: south going east, 2: east going north, 3: north going west
    # starting corner: NW corner landing at ground level is the cave entrance side
    corner = {0: (wx0, wy1 - ring, wx0 + ring, wy1), 1: (wx0, wy0, wx0 + ring, wy0 + ring), 2: (wx1 - ring, wy0, wx1, wy0 + ring),
              3: (wx1 - ring, wy1 - ring, wx1, wy1)}
    # side strips between corners (4 steps each of 32)
    def side_steps(s):
        if s == 0: return [(wx0, wy1 - ring - 32 * (i + 1), wx0 + ring, wy1 - ring - 32 * i) for i in range(4)]
        if s == 1: return [(wx0 + ring + 32 * i, wy0, wx0 + ring + 32 * (i + 1), wy0 + ring) for i in range(4)]
        if s == 2: return [(wx1 - ring, wy0 + ring + 32 * i, wx1, wy0 + ring + 32 * (i + 1)) for i in range(4)]
        return [(wx1 - ring - 32 * (i + 1), wy1 - ring, wx1 - ring - 32 * i, wy1) for i in range(4)]
    next_corner = {0: 1, 1: 2, 2: 3, 3: 0}
    s = 0
    seq.append(('land', corner[0], 0))
    while z < L.SUMMIT_Z:
        for r in side_steps(s):
            z += 16
            seq.append(('step', r, z))
            if z >= L.SUMMIT_Z: break
        if z >= L.SUMMIT_Z: break
        seq.append(('land', corner[next_corner[s]], z))
        s = next_corner[s]
    # summit slab over the well with a hole over the last flight
    hole = [it[1] for it in seq if it[2] > L.SUMMIT_Z - 32 - 56 - 16]
    # the final step reaches the summit height: it IS the floor there
    for i, (kind, (ax, ay, bx, by), zt) in enumerate(seq):
        if zt == 0: continue
        first_rev = zt <= 256
        bot = 0 if first_rev else zt - 16
        tex = {'top': T('rock_top'), 'side': T('cave'), 'bot': T('cave')}
        A(box((round(ax), round(ay), bot), (round(bx), round(by), zt), tex))
    for (ax, ay, bx, by) in sub_rects((wx0, wy0, wx1, wy1), [(round(a), round(b), round(c), round(d)) for (a, b, c, d) in hole] +
                                      [(wcx - P, wcy - P, wcx + P, wcy + P)]):
        A(box((ax, ay, L.SUMMIT_Z - 32), (bx, by, L.SUMMIT_Z), {'top': T('rock_top'), 'bot': T('cave'), 'side': T('cave')}))
    A(box((wcx - P, wcy - P, L.SUMMIT_Z - 32), (wcx + P, wcy + P, L.SUMMIT_Z), {'top': T('rock_top'), 'bot': T('cave'), 'side': T('cave')}))
    for zz in range(120, L.SUMMIT_Z, 220):
        light(wcx, wcy - P - 40, zz, 420, '1 0.8 0.6'); light(wcx, wcy + P + 40, zz + 128, 360, '1 0.7 0.9')
    global WELL_SEQ, WELL_HOLE
    WELL_SEQ, WELL_HOLE = seq, hole


def summit():
    sz = L.SUMMIT_Z
    weapon('imperius', 300, 1790, sz, 'purple')
    item('holdable_boomies', -260, 1830, sz)
    item('ammo_betty', 1380, 1720, sz)
    item('ammo_pumper', 1400, 1580, sz)
    item('item_armor_shard', 120, 1700, sz)
    # applause when you make it up to the Imperius
    M.ent('trigger_multiple', brushes=[box((360, 1660, sz), (460, 1900, sz + 80), TRIG)], target='applause', wait=20)
    speaker(300, 1790, sz + 100, 'sound/world/human/applause.ogg', loop=False, targetname='applause')
    # rocks + candy on the summit (cover against the meadow)
    for (x, y, nm, s, a) in ((-380, 1760, 'jaw_c', 0.9, 30), (1460, 1880 - 40, 'jaw_a', 0.8, 200)):
        custom(nm, x, y, sz, angle=a, mul=s); ball_clip(x, y, sz, CM.JAW_R * s)
    for (x, y, a) in ((-60, 1840, 20), (-200, 1700, 160)):
        custom('flower_a' if x < 0 else 'flower_c', x, y, sz, angle=a, lit=False)
    mdl_c('pad_sunflower/pad_sunflower_l.md3', -420, 1770, sz, 1.0, 300)
    mdl_c('pad_sunflower/pad_sunflower3.md3', 1220, 1880, sz, 1.4, 80)
    light(300, 1780, sz + 260, 400, '1 0.95 0.85')


# =================================================================================================== the pump house deck
def pumphouse():
    x0, y0, x1, y1 = L.DECK
    Z = L.DECK_Z
    d = box((x0, y0, Z - 16), (x1, y1, Z), {'top': T('grate'), 'side': T('iron'), 'bot': T('iron')})
    A(d)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    custom('deck_frame', cx, cy, 0, angle=0)
    for (px, py) in CM.deck_columns():
        A(box((round(px - 18), round(py - 18), 0), (round(px + 18), round(py + 18), Z - 16), WCLIP))
        KEEP_OUT.append((px, py, 60))
    # player clip along the railed edges (shots pass)
    A(box((x0, y0, Z), (x1, y0 + 12, Z + 48), CLIP))
    A(box((x0, y0 + 12, Z), (x0 + 12, y1, Z + 48), CLIP))
    A(box((x1 - 12, y0 + 12, Z), (x1, 200 - 8, Z + 48), CLIP)) if False else None
    custom('pipes_deck', cx, y0, 0, angle=0)
    # the shed (walls 8 thick inside the MD3 panels), door south, windows east/west
    sx0, sy0, sx1, sy1 = L.SHED
    scx, scy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    custom('shed', scx, scy, Z)
    H = L.SHED_H
    inn = T('stone_dark')
    def wall(b): A(b)
    dw = CM.SHED_DOOR / 2
    wt = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    # south wall (door)
    for (a, b) in ((sx0 + 2, scx - dw), (scx + dw, sx1 - 2)):
        wall(box((round(a), sy0 + 2, Z), (round(b), sy0 + 10, Z + H - 12), wt))
    wall(box((round(scx - dw), sy0 + 2, Z + 224), (round(scx + dw), sy0 + 10, Z + H - 12), wt))
    wall(box((sx0 + 2, sy1 - 10, Z), (sx1 - 2, sy1 - 2, Z + H - 12), wt))
    for (xa, xb) in ((sx0 + 2, sx0 + 10), (sx1 - 10, sx1 - 2)):
        for (ya, yb, za, zb) in ((sy0 + 10, scy - 56, Z, Z + H - 12), (scy + 56, sy1 - 10, Z, Z + H - 12), (scy - 56, scy + 56, Z, Z + 112),
                                 (scy - 56, scy + 56, Z + 208, Z + H - 12)):
            wall(box((xa, round(ya), za), (xb, round(yb), zb), wt))
    A(box((sx0, sy0, Z + H - 12), (sx1, sy1, Z + H), {'top': CAULK, 'side': CAULK, 'bot': CAULK}))
    custom('pump', scx + 20, scy + 20, Z, angle=180)
    A(box((round(scx + 20 - 92), round(scy + 20 - 82), Z), (round(scx + 20 + 120), round(scy + 20 + 82), Z + 200), WCLIP))
    weapon('pumper', scx - 110, scy - 66, Z, 'green')
    light(scx, scy, Z + 220, 300, '1 0.85 0.6')
    speaker(scx, scy, Z + 120, 'sound/world/machine/mechanics.ogg', volume=0.5)
    # pad on the deck -> shed roof; pad on the roof -> summit
    jumppad(x1 - 80, scy + 40, Z, (scx + 60, scy, Z + H), Z + H + 140, 'shed_roof')
    jumppad(scx - 90, scy, Z + H, (-200, 1760, L.SUMMIT_Z), 1220, 'roof_summit')
    item('ammo_imperius', scx + 60, scy - 70, Z + H)
    item('ammo_balloony', x0 + 90, y1 - 90, Z)
    item('item_armor_shard', x0 + 120, y0 + 90, Z)
    # stair-bridge over the river up to the deck (16u steps, thin treads over the water)
    bx0, bx1, by0, by1 = L.STAIR_BRIDGE
    n = (L.DECK_Z) // 16
    run = (by1 - by0) / n
    for k in range(n):
        ya, yb = by0 + run * k, by0 + run * (k + 1)
        zt = 16 * (k + 1)
        midy = (ya + yb) / 2
        over_land = L.on_land((bx0 + bx1) / 2, midy, 40)
        solid = over_land and zt - 24 < 96
        bot = 0 if solid else zt - 24
        A(box((bx0, round(ya), bot), (bx1, round(yb), zt), {'top': T('grate'), 'side': T('iron'), 'bot': T('iron')}))
    A(box((bx0, by1, Z - 16), (bx1, 1100, Z), {'top': T('grate'), 'side': T('iron'), 'bot': T('iron')}))
    # posts in the river under the treads (carved out of the water)
    for py in (430, 700):
        zt = 16 * math.ceil((py - by0) / run) - 24
        for px in (bx0 + 14, bx1 - 14):
            RIVER_SOLIDS.append(cyl(round(px), py, 12, L.RIV_FLOOR, round(zt), WCLIP, 8))
    item('ammo_splasher', (bx0 + bx1) / 2, 575, L.RIV_FLOOR)
    item('ammo_boaster', (bx0 + bx1) / 2, 1000, Z)
    KEEP_OUT.append(((bx0 + bx1) / 2, 450, 520))
    light((bx0 + bx1) / 2, 450, 520, 300, '1 0.9 0.8')
    light(cx, cy, 300, 400, '1 0.9 0.75')
    item('ammo_pumper', cx, y0 + 150, 0)


def stairbridge_model():
    """iron stringers (plates against the tread ends, so the model is mounted on the stair) + railing (MD3)"""
    bx0, bx1, by0, by1 = L.STAIR_BRIDGE
    for (nm, x, sg) in (('sb_rail_w', bx0 - 2, -1), ('sb_rail_e', bx1 + 2, 1)):
        X = CM.Model()
        iron = CM.S('iron_dark', 'lm', tag='sb')
        line = [(32.0, 32.0), (by1 - 32.0, float(L.DECK_Z)), (1100.0, float(L.DECK_Z))]
        ys = np.concatenate([np.linspace(32, by1 - 32, 28), np.linspace(by1 - 32, 1100, 7)[1:]])
        zl = np.interp(ys, [p[0] for p in line], [p[1] for p in line])
        rows = [8, -6, -16, -24, -36]
        P = np.zeros((len(rows), len(ys), 3)); N = np.zeros_like(P); UV = np.zeros((len(rows), len(ys), 2))
        for j, (y, z) in enumerate(zip(ys, zl)):
            for i, dz in enumerate(rows):
                P[i, j] = (x, y, max(z + dz, 1.0 + i * 0.5)); UV[i, j] = (y / 128, (8 - dz) / 128)
        N[..., 0] = sg
        X.mesh(iron).grid(P, N, UV)
        # rail posts every ~96 + top rail
        for j in range(0, len(ys), 3):
            CM.tube(X.mesh(iron), [(x + sg * 3, ys[j], zl[j] + 8), (x + sg * 3, ys[j], zl[j] + 56)], 2.5, nseg=5)
        CM.tube(X.mesh(iron), [(x + sg * 3, y, z + 56) for (y, z) in zip(ys, zl)], 3.5, nseg=6)
        CM.tube(X.mesh(iron), [(x + sg * 3, y, z + 30) for (y, z) in zip(ys, zl)], 2, nseg=5)
        # shift to a local origin at the first point
        o = np.array([x, 32.0, 32.0])
        for m in X.m.values(): m.V = [v - o for v in m.V]
        path = f'{CM.MD}/{nm}.md3'
        sc, zo = CM.save_md3(os.path.join(CM.OUT, path), X.surfaces(), nm, with_offset=True)
        CM.PLACE[nm] = (path, sc, zo)
        CM.PLACE[nm + '_o'] = tuple(o)


# =================================================================================================== balcony + lobby
def balcony():
    x0, y0, x1, y1 = L.BALC
    Z = L.BALC_Z
    st = {'top': T('path'), 'side': T('wall_stone'), 'bot': T('stone_dark')}
    A(box((x0, y0, Z - 32), (x1, y1, Z), st))
    # columns under the front edge
    for x in range(-1120, 1121, 320):
        A(box((x - 24, y1 - 48, 0), (x + 24, y1, Z - 32), {'side': T('wall_stone'), 'top': CAULK, 'bot': CAULK}))
        KEEP_OUT.append((x, y1 - 24, 60))
    # grand stairs down along the south wall at both ends
    W = L.BALC_STAIR_W
    n = Z // 16
    for sx in (-1, 1):
        for k in range(n):
            zt = 16 * (k + 1)
            xa = x0 - 32 * (n - k) if sx < 0 else x1 + 32 * (n - k - 1)
            xb = xa + 32
            A(box((xa, y0, 0), (xb, y0 + W, zt), {'top': T('path'), 'side': T('wall_stone'), 'bot': CAULK}))
        KEEP_OUT.append((sx * (x1 + 32 * n / 2), y0 + W / 2, 420))
    # ornate railings: along the front edge and down the open side of each stair
    for (nm, pts) in (('rail_balc', [(x0 + 6, y1 - 6, Z), (x1 - 6, y1 - 6, Z)]),
                      ('rail_sw', [(x0 - 32 * n + 10, y0 + W - 6, 16), (x0 - 6, y0 + W - 6, Z)]),
                      ('rail_se', [(x1 + 6, y0 + W - 6, Z), (x1 + 32 * n - 10, y0 + W - 6, 16)])):
        p, sc, zo, o = CM.railing(nm, pts, h=56)
        custom((p, sc, zo), o[0], o[1], o[2])
    # urns on the newel posts at the stair feet + lampposts
    for sx in (-1, 1):
        xf = sx * (x1 + 32 * n + 80)
        custom('urn', xf, y0 + W + 70, 0, angle=0)
        A(box((round(xf - 44), round(y0 + W + 26), 0), (round(xf + 44), round(y0 + W + 114), 220), WCLIP))
        KEEP_OUT.append((xf, y0 + W + 70, 110))
    # under the balcony: health stations, ammo
    M.ent('station_health', (-600, y0 + 60, 0), angle=90)
    M.ent('station_health', (600, y0 + 60, 0), angle=90)
    for x in (-600, 600): KEEP_OUT.append((x, y0 + 60, 100))
    item('ammo_splasher', 0, y0 + 100, 0)
    item('ammo_balloony', 600, y0 + 130, Z)
    item('ammo_bubbleg', -800, y0 + 130, Z)
    item('ammo_imperius', -2210, y0 + 100, 0)
    item('item_armor_shard', 900, y0 + 120, 0)
    for x in (-900, -300, 300, 900):
        light(x, y0 + 130, 260, 240, '1 0.85 0.6')
    # sign over the lobby door
    A(sign_box((-512, L.YS + 1, Z + 260), (512, L.YS + 9, Z + 388), T('sign_garden'), 1024, 128, facing='n'))


def lobby():
    x0, y0, x1, y1 = L.LOBBY
    Z = L.BALC_Z; H = L.LOBBY_H
    A(box((x0, y0 + 32, Z - 32), (x1, y1 - 32, Z), {'top': T('carpet'), 'side': CAULK, 'bot': CAULK}))
    A(box((x0, y0 + 32, Z + H), (x1, y1 - 32, Z + H + 32), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}))
    wall = {'side': T('damask'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - 32, y0, Z - 32), (x0, y1 - 32, Z + H + 32), dict(wall, w=CAULK)))
    A(box((x1, y0, Z - 32), (x1 + 32, y1 - 32, Z + H + 32), dict(wall, e=CAULK)))
    A(box((x0, y0, Z - 32), (x1, y0 + 32, Z + H + 32), dict(wall, s=CAULK)))
    # lobby window panes in the hall wall openings
    for (a, b) in ((-480, -240), (240, 480)):
        A(box((a, L.YS - 20, 448), (b, L.YS - 12, 640), T('window')))
    # golden ticket on the back wall, signs
    A(sign_box((-200, y0 + 32, Z + 90), (200, y0 + 40, Z + 290), T('ticket'), 512, 256, facing='n'))
    A(sign_box((x0 + 1, -2160, Z + 100), (x0 + 9, -1990, Z + 230), T('sign_touch'), 512, 256, facing='e'))
    A(sign_box((x1 - 9, -2180, Z + 100), (x1 - 1, -2010, Z + 230), T('sign_river'), 512, 256, facing='w'))
    # chocolate bar stacks + candy
    for (x, y, a) in ((-480, -2210, 0), (480, -2210, 180)):
        custom('chocbar', x, y, Z, angle=a)
        A(box((round(x - 120), round(y - 60), Z), (round(x + 120), round(y + 60), Z + 52), WCLIP))
    custom('cupcake', -536, -2045, Z, mul=0.85); A(cyl(-536, -2045, 84, Z, Z + 210, WCLIP, 12))
    custom('jaw_b', 500, -2060, Z, mul=0.8); ball_clip(500, -2060, Z, CM.JAW_R * 0.8)
    M.ent('station_health', (0, y0 + 90, Z), angle=90)
    item('ammo_balloony', 300, -2100, Z)
    item('ammo_pumper', -300, -2100, Z)
    item('ammo_nipper', 0, -2010, Z)
    for x in (-360, 360):
        spawn(x, -2160 + 60, Z, 90)
    for x in (-400, 0, 400):
        light(x, -2110, Z + H - 50, 260, '1 0.85 0.6')
    custom('lamppost', -600, -2240, Z, mul=0.6); custom('lamppost', 600, -2240, Z, mul=0.6)
    speaker(0, -2110, Z + 150, 'sound/world/machine/clock_ticking.ogg', volume=0.4)


# =================================================================================================== mushrooms
def redcap():
    cx, cy = L.REDCAP
    custom('redcap', cx, cy, 0, angle=20)
    C = CM.REDCAP_COL
    A(cyl(cx, cy, C['stem_r'], 0, C['stem_z'], WCLIP, 12))
    for (r0, z0, r1, z1) in C['layers']:
        A(frustum(cx, cy, r0, z0, r1, z1, WCLIP, 16))
    KEEP_OUT.append((cx, cy, 340))
    weapon('bubbleg', cx + 150, cy - 40, 0, 'blue')
    item('ammo_nipper', cx - 160, cy + 60, 0)
    item('holdable_floater', cx + 30, cy + 20, C['top'])
    item('ammo_betty', cx - 80, cy - 60, C['top'])
    jumppad(cx + 420, cy - 220, 0, (cx + 60, cy - 20, C['top']), 660, 'redcap')
    light(cx, cy, 250, 300, '1 0.85 0.75')
    light(cx, cy, 700, 300, '1 0.95 0.9')


def stem_shell(cx, cy, prof, rin, bands, door, windows=(), tex_in=T('wall_stone'), shrink=6, n=16, out_tex=CAULK):
    k0, k1, dh = door
    for (za, zb) in zip(bands, bands[1:]):
        ra = CM.interp_r(prof, za) - shrink; rb = CM.interp_r(prof, zb) - shrink
        for k in range(n):
            open_ = (k in (k0, k1) and zb <= dh) or any(k == wk and za >= w0 and zb <= w1 for (wk, w0, w1) in windows)
            if open_: continue
            nb_door = (k in (k0 - 1, k1 + 1) and zb <= dh) or any(k in (wk - 1, wk + 1) and za >= w0 and zb <= w1 for (wk, w0, w1) in windows)
            under = (k in (k0, k1) and za == dh) or any(k == wk and za == w1 for (wk, w0, w1) in windows)
            over = any(k == wk and zb == w0 for (wk, w0, w1) in windows)
            amid = (k + 0.5) * 360.0 / n
            tf = ring_tex(amid, inner=tex_in, outer=out_tex, side=tex_in if nb_door else CAULK,
                          bot=tex_in if under else CAULK, top=tex_in if over else CAULK)
            A(hull([(px, py, z) for a in (k * 22.5, (k + 1) * 22.5) for (r, z) in ((rin, za), (rin, zb), (ra, za), (rb, zb))
                    for (px, py) in [ang_pt(cx, cy, r, a)]], tf, round_pts=False))


def yellowhouse():
    cx, cy = L.YELLOW
    D = CM.YH
    custom('yellowhouse', cx, cy, 0, angle=0)
    bands = [0, 40, 120, 150, 232, 256, 300, D['h']]
    stem_shell(cx, cy, D['stem'], D['rin'], bands, D['door'], D['windows'], tex_in=T('stone_dark'))
    A(disc_brush(cx, cy, D['rin'] - 2, 0, 8, {'top': T('planks'), 'side': T('planks'), 'bot': CAULK}))
    top = D['top']; h = D['h']
    (ru0, zu0), (ru1, zu1) = D['under']
    zt = lambda r: float(np.interp(r, [p[0] for p in top], [p[1] for p in top]))
    zb = lambda r: h if r <= ru0 else zu0 + (r - ru0) * (zu1 - zu0) / (ru1 - ru0)
    rc = top[1][0]
    A(disc_brush(cx, cy, rc, h, zt(rc), {'bot': T('stone_dark'), 'side': CAULK, 'top': CAULK}, z1c=zt(0) if zt(0) > zt(rc) + 0.5 else None))
    rs = sorted(set([p[0] for p in top[1:]] + [ru0]))
    for k in range(16):
        am = (k + 0.5) * 22.5
        for (ra, rb_) in zip(rs, rs[1:]):
            A(ring_seg(cx, cy, k, 16, ra, rb_, zb(ra), zt(ra), zb(rb_), zt(rb_), ring_tex(am)))
    KEEP_OUT.append((cx, cy, top[-1][0] + 50))
    # inside: Pumper ammo, Betty ammo, a little toadstool lamp
    item('ammo_pumper', cx - 60, cy + 60, 8)
    item('ammo_betty', cx + 80, cy - 20, 8)
    custom('toad_b', cx + 40, cy + 110, 8, lit=False)
    light(cx, cy, 300, 380, '1 0.85 0.6')
    # roof: Balloony, pad from the meadow (west of the house)
    weapon('balloony', cx, cy, zt(0), 'green')
    item('ammo_bubbleg', cx + 150, cy + 90, zt(170))
    jumppad(cx - 720, cy + 260, 0, (cx - 90, cy + 30, zt(100)), zt(0) + 260, 'yellow_roof')
    light(cx, cy, 1000, 400, '1 0.95 0.85')
    M.ent('station_health', (cx + 720, cy + 60, 0), angle=180)
    KEEP_OUT.append((cx + 720, cy + 60, 100))


# =================================================================================================== trees
def trees():
    D = CM.FT
    # west flower tree on a rockery mound (pad onto the dome: Betty)
    tx, ty = L.TREE_W
    r0, r1, h = L.MOUND_R0, L.MOUND_R1, L.MOUND_H
    A(frustum(tx, ty, r0, 0, r1, h, {'top': T('rock_top'), 'side': T('rock_top'), 'bot': CAULK}, 16, 0))
    custom('flowertree_w', tx, ty, h, angle=0)
    A(cyl(tx, ty, D['trunk_r'][0] - 6, h, D['col'][0][1] + h - 20, WCLIP, 12))
    for (ra, za, rb, zb) in D['col']:
        A(frustum(tx, ty, ra, za + h - 20, rb, zb + h - 20, WCLIP, 16))
    top = D['top'] + h - 20
    weapon('betty', tx, ty, top, 'black')
    item('ammo_splasher', tx + 140, ty - 60, top)
    jumppad(tx + 700, ty - 40, 0, (tx + 110, ty, top), top + 190, 'tree_top')
    # fling pad off the dome (the steep crepe skirts give bots no way down)
    fx_, fy_ = ang_pt(tx, ty, 170, 225)
    lx_, ly_ = ang_pt(tx, ty, 800, 225)
    jumppad(fx_, fy_, top, (lx_, ly_, 0), top + 190, 'tree_fling')
    KEEP_OUT.append((tx, ty, r0 + 30))
    for (a, s) in ((40, 1.0), (160, 0.8), (250, 1.1), (320, 0.9)):
        x, y = ang_pt(tx, ty, r1 + (r0 - r1) * 0.45, a)
        custom('toad_a' if a % 80 else 'toad_b', x, y, h * 0.5, angle=a, mul=s, lit=False) if False else None
    for (a, nm) in ((20, 'flower_a'), (110, 'flower_b'), (200, 'flower_c'), (290, 'flower_a')):
        x, y = ang_pt(tx, ty, 180, a)
        custom(nm, x, y, h, angle=a, lit=False)
    light(tx, ty, top + 260, 500, '1 0.95 0.9')
    light(tx, ty, 300, 380, '1 0.85 0.75')
    # east flower tree by the pool (cover)
    ex, ey = L.TREE_E
    custom('flowertree_e', ex, ey, 0, angle=0)
    A(cyl(ex, ey, D['trunk_r'][0] - 6, 0, D['col'][0][1] - 20, WCLIP, 12))
    for (ra, za, rb, zb) in D['col']:
        A(frustum(ex, ey, ra, za - 20, rb, zb - 20, WCLIP, 16))
    KEEP_OUT.append((ex, ey, 140))
    item('ammo_balloony', ex + 80, ey - 230, 0)
    # gumball tree (east)
    gx, gy = L.GUMTREE
    G = CM.GT
    custom('gumtree', gx, gy, 0, angle=0)
    A(cyl(gx, gy, 36, 0, G['col'][0][1], WCLIP, 12))
    for (ra, za, rb, zb) in G['col']:
        A(frustum(gx, gy, ra, za, rb, zb, WCLIP, 16))
    KEEP_OUT.append((gx, gy, 120))
    item('item_jumper', gx - 150, gy - 160, 0)
    item('ammo_splasher', gx + 120, gy - 140, 0)


# =================================================================================================== river furniture
def river_things():
    # candy-cane bridge across the river at BRIDGE, perpendicular to the flow
    bx, by = L.BRIDGE
    d, i = L.river_dist(bx, by)
    P = L.river_points()
    t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
    flow = math.degrees(math.atan2(t[1], t[0]))
    ang = flow + 90
    bx, by = P[i]
    hw = CM.BRIDGE_HW
    zt = CM.BRIDGE_Z
    deck = {'top': T('planks'), 'side': T('planks'), 'bot': T('planks')}
    A(rbox(bx, by, ang, -240, 240, -hw, hw, zt - 16, zt, deck))
    A(rbox(bx, by, ang, 240, 336, -hw, hw, 0, zt, deck, z0e=0, z1e=0))
    A(rbox(bx, by, ang, -336, -240, -hw, hw, 0, 0, deck, z0e=0, z1e=zt))
    custom('bridge', bx, by, 0, angle=ang)
    item('ammo_boaster', bx, by, zt)
    for sgn in (-1, 1):
        x, y = ang_pt(bx, by, sgn * 400, ang)
        KEEP_OUT.append((x, y, 150))
    KEEP_OUT.append((bx, by, 340))
    # cane arch over the south approach
    ax, ay = ang_pt(bx, by, -460, ang)
    custom('cane_arch', ax, ay, 0, angle=ang + 90)
    for s in (-1, 1):
        px, py = ax + math.cos(math.radians(ang + 90)) * s * CM.ARCH_W / 2, ay + math.sin(math.radians(ang + 90)) * s * CM.ARCH_W / 2
        A(cyl(round(px), round(py), 18, 0, 300, WCLIP, 8))
    KEEP_OUT.append((ax, ay, 300))
    # the candy boat at its jetty on the south bank
    ox, oy = L.BOAT
    d, i = L.river_dist(ox, oy)
    t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
    flow = math.atan2(t[1], t[0])
    nx, ny = -math.sin(flow), math.cos(flow)            # left of the flow (flow runs west: left = south)
    cxl, cyl_ = P[i]
    side = 1 if ny < 0 else -1                          # pick the southern bank
    bcx, bcy = cxl + nx * side * 60, cyl_ + ny * side * 60
    bang = math.degrees(flow) + 180                     # bow pointing upstream (east)
    Lh, Bh = CM.BOAT_L / 2, CM.BOAT_B / 2
    ca_, sa_ = math.cos(math.radians(bang)), math.sin(math.radians(bang))
    hp = []
    for u in np.linspace(-Lh + 20, Lh - 40, 9):
        f = u / Lh
        half = Bh * math.sqrt(max(0.02, 1 - (max(0, f) ** 2.2 if f > 0 else (abs(f) ** 4))))
        for (v, z) in ((half - 14, 0), (-(half - 14), 0), (half * 0.3, -40), (-half * 0.3, -40)):
            hp.append((bcx + ca_ * u - sa_ * v, bcy + sa_ * u + ca_ * v, z))
    hull_b = hull(hp, {'top': T('planks'), 'side': CAULK, 'bot': CAULK}, round_pts=False)
    RIVER_SOLIDS.append(hull_b)
    custom('boat', bcx, bcy, 0, angle=bang)
    # gunwale clip (players) except the gangway gap facing the jetty
    gap_v = Bh * (-side if True else 1)
    for v in (-Bh + 14, Bh - 22):
        if (v > 0) == (side * (1 if math.sin(math.radians(bang)) * 0 == 0 else 1) < 0): pass
    # jetty: planks from the bank to the boat's side
    jx, jy = cxl + nx * side * 198, cyl_ + ny * side * 198
    jet = rbox(jx, jy, math.degrees(flow), -70, 70, -61, 61, -16, 0, {'top': T('planks'), 'side': T('planks'), 'bot': T('planks')})
    RIVER_SOLIDS.append(jet)
    weapon('boaster', bcx - math.cos(math.radians(bang)) * 40, bcy - math.sin(math.radians(bang)) * 40, 0, 'orange')
    item('holdable_bambam', jx + nx * side * 140, jy + ny * side * 140, 0)
    KEEP_OUT.append((bcx, bcy, 260)); KEEP_OUT.append((jx + nx * side * 100, jy + ny * side * 100, 120))
    light(bcx, bcy, 200, 260, '1 0.8 0.85')
    global BOAT_INFO
    BOAT_INFO = (bcx, bcy, bang, jx, jy, nx * side, ny * side)
    # peppermint stepping stones
    sx, sy = L.STONES
    d, i = L.river_dist(sx, sy)
    t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
    flow = math.atan2(t[1], t[0])
    nx, ny = -math.sin(flow), math.cos(flow)
    cx_, cy_ = P[i]
    for k in range(-2, 3):
        px, py = cx_ + nx * k * 116, cy_ + ny * k * 116
        st = cyl(round(px), round(py), 56, L.RIV_FLOOR, 0, {'top': T('peppermint'), 'side': T('candy_white_b'), 'bot': CAULK}, 16)
        hfit(st, round(px) - 56, round(py) - 56, round(px) + 56, round(py) + 56, 256, 256, T('peppermint'))
        RIVER_SOLIDS.append(st)
    item('item_speedy', cx_ - math.cos(flow) * 220, cy_ - math.sin(flow) * 220, L.RIV_FLOOR)
    for k in (-1, 1):
        KEEP_OUT.append((cx_ + nx * k * 360, cy_ + ny * k * 360, 120))
    global STONES_INFO
    STONES_INFO = (cx_, cy_, nx, ny)
    # suction pipe: intake trigger in the river, glass tube along the flight, onto the summit
    px, py = L.PIPE_START
    custom('augpipe', px, py, (L.RIV_FLOOR + 40) / 2)
    trig = box((px - 40, py - 40, L.RIV_FLOOR), (px + 40, py + 40, 40), TRIG)
    o = (px, py, (L.RIV_FLOOR + 40) / 2)
    land = (L.PIPE_LAND[0], L.PIPE_LAND[1], L.SUMMIT_Z)
    tx, ty = pad_target(o, land, AUG_APEX)
    M.ent('trigger_push', brushes=[trig], target='augpipe')
    M.ent('target_position', (round(tx), round(ty), AUG_APEX), targetname='augpipe')
    JUMPPADS.append(('augpipe', o, (round(tx), round(ty), AUG_APEX), land))
    speaker(px, py, 60, 'sound/world/misc/air_leakage.ogg', volume=0.6)
    light(px, py, 120, 200, '0.8 0.9 1')
    A(sign_box((px + 150, py - 260, 120), (px + 290, py - 252, 190), T('sign_pump'), 512, 128, facing='s'))
    A(box((px + 216, py - 252, 0), (px + 224, py - 244, 120), {'side': T('iron'), 'top': T('iron'), 'bot': CAULK}))
    KEEP_OUT.append((px + 220, py - 250, 60))
    # river sounds + a few floating ducks
    for (x, y) in ((300, 760), (-800, 500), (-1600, 230), (-2200, -250)):
        speaker(x, y, 20, 'sound/world/ambient/water_flowing.ogg', volume=0.4)
    for (x, y, a) in ((-560, 470, 30), (-1300, 300, 200)):
        mdl_c('pad_ducks/pad_duck.md3', x, y, L.WATER, 0.35, a)


AUG_APEX = 1320


# =================================================================================================== the lollipop grove + garden dressing
def grove():
    gx, gy = L.GROVE
    lol = [('lolli_spiral', -320, 220, 1.2, 20), ('lolli_star', -60, 330, 1.0, 70), ('lolli_flower', 260, 180, 1.15, 140),
           ('lolli_rings', -380, -150, 1.05, 200), ('lolli_swirl', 120, -240, 1.25, 300), ('lolli_star', 380, -60, 0.9, 10),
           ('lolli_spiral', -150, -380, 0.95, 250), ('lolli_flower', 470, 300, 0.85, 80)]
    for (nm, dx, dy, s, a) in lol:
        x, y = gx + dx, gy + dy
        custom(nm, x, y, 0, angle=a, mul=s)
        A(cyl(round(x), round(y), 10, 0, round((CM.LOLLI_H - CM.LOLLI_R) * s), WCLIP, 8))
        # disc clip (thin oriented octagon prism)
        R = CM.LOLLI_R * s * 0.92; hz = CM.LOLLI_H * s; t = CM.LOLLI_T * s / 2
        ar = math.radians(a)
        ny = (-math.sin(ar), math.cos(ar))
        ux = (math.cos(ar), math.sin(ar))
        pts = []
        for k in range(8):
            q = 2 * math.pi * k / 8 + math.pi / 8
            u, v = R * math.cos(q), R * math.sin(q)
            for sg in (-1, 1):
                pts.append((x + ux[0] * u + ny[0] * sg * t, y + ux[1] * u + ny[1] * sg * t, hz + v))
        A(hull(pts, WCLIP, round_pts=False))
        KEEP_OUT.append((x, y, 110 * s))
    # twisted candy stalks + buttercups
    for (dx, dy, a) in ((-480, 60, 0), (200, 400, 120), (40, -60, 240)):
        custom('twisty', gx + dx, gy + dy, 0, angle=a)
        A(cyl(gx + dx, gy + dy, 26, 0, 520, WCLIP, 8))
        KEEP_OUT.append((gx + dx, gy + dy, 100))
    for (dx, dy, s, a) in ((-200, 40, 1.0, 10), (300, -300, 1.2, 80), (-480, -340, 0.9, 200), (520, 80, 1.1, 300), (0, 520, 1.0, 40)):
        if free(gx + dx, gy + dy, 50):
            custom('buttercup', gx + dx, gy + dy, 0, angle=a, mul=s, lit=False)
            KEEP_OUT.append((gx + dx, gy + dy, 60))
    item('item_visionless', gx - 40, gy + 120, 0)
    item('ammo_splasher', gx + 230, gy - 140, 0)
    item('ammo_bubbleg', gx - 300, gy - 380 + 60, 0)
    # two spinning hypno-discs by the path (func_rotating on the x axis)
    for (dx, dy, des, sp) in ((640, 420, 'swirl', 40), (-620, 420, 'spiral', -55)):
        x, y = gx + dx, gy + dy
        hz = round(CM.LOLLI_H * 1.3)
        custom('stick_tall', x, y, 0, angle=0)
        A(cyl(x, y, 12, 0, hz - round(CM.LOLLI_R * 1.4), WCLIP, 8))
        M.ent('func_rotating', brushes=[box((x - 8, y - 8, hz - 8), (x + 8, y + 8, hz + 8), ORIGIN),
                                        box((x - 4, y - 4, hz - 4), (x + 4, y + 4, hz + 4), NODRAW_NS)],
              model2=CM.PLACE['disc_' + des][0], speed=sp, spawnflags=4, dmg=0)
        KEEP_OUT.append((x, y, 170))
    light(gx, gy, 600, 400, '1 0.9 0.95')


def garden():
    """cover + dressing over the meadow: jawbreakers, bonbons, cupcakes, gummy bears, urns, lamps, flowers, bushes"""
    rng = np.random.default_rng(41)
    def put(fn, x, y, r, tries=True):
        p = near_free(x, y, r) if tries else ((x, y) if free(x, y, r) else None)
        if p is None: return None
        fn(*p); KEEP_OUT.append((p[0], p[1], r)); return p
    # jawbreakers (big cover)
    for (x, y, nm, s) in ((420, -1000, 'jaw_a', 1.8), (-760, -880, 'jaw_c', 1.5), (900, 260, 'jaw_b', 1.6), (-500, 120, 'jaw_d', 1.3),
                          (1900, -1400, 'jaw_c', 1.7), (-1950, -620, 'jaw_a', 1.4), (40, 260, 'jaw_c', 1.1), (1500, 500, 'jaw_d', 1.2),
                          (-1100, -300, 'jaw_b', 1.6), (750, -1500, 'jaw_d', 1.3), (-260, -1250, 'jaw_b', 1.1), (2080, 80, 'jaw_a', 1.3)):
        R = CM.JAW_R * s
        def f(px, py, nm=nm, s=s, R=R):
            custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), mul=s); ball_clip(px, py, 0, R)
        put(f, x, y, R + 30)
    # wrapped bonbons
    for (x, y, nm, a) in ((-300, -700, 'bonbon_a', 30), (1100, -1200, 'bonbon_b', 120), (-1300, 120, 'bonbon_b', 70), (500, 500, 'bonbon_a', 160),
                          (1700, -300, 'bonbon_a', 80), (-900, -1500, 'bonbon_b', 10)):
        def f(px, py, nm=nm, a=a):
            custom(nm, px, py, 0, angle=a)
            A(rbox(px, py, a, -104, 104, -66, 66, 0, 132, WCLIP))
        put(f, x, y, 210)
    # cupcakes + chocolate bars
    for (x, y) in ((100, -1300), (-1800, -200), (1650, 120), (-650, -1250)):
        def f(px, py):
            custom('cupcake', px, py, 0, angle=int(rng.uniform(0, 360))); A(cyl(round(px), round(py), 96, 0, 250, WCLIP, 12))
        put(f, x, y, 140)
    for (x, y, a) in ((1000, -500, 30), (-1300, -700, 100), (-400, 900 - 200, 0), (1150, 520, 60)):
        def f(px, py, a=a):
            custom('chocbar', px, py, 0, angle=a)
            A(rbox(px, py, a, -118, 118, -58, 58, 0, 56, WCLIP))
        put(f, x, y, 150)
    # gummy bears (catalog): standing and lying
    for (x, y, s, a, nm) in ((-780, -380, 1.3, 30, 'redbear'), (650, -760, 1.4, 150, 'greenbear'), (1200, -1650, 1.3, 80, 'yellowbear'),
                             (-1650, -1480, 1.3, 210, 'orangebear'), (300, 1180, 1.2, 250, 'redbear'), (-200, 1150, 1.3, 300, 'yellowbear'),
                             (1950, 800, 1.3, 190, 'greenbear')):
        def f(px, py, s=s, a=a, nm=nm): solid_mdl('gummybears/' + nm + '.md3', px, py, 0, s, a)
        put(f, x, y, 90)
    for (x, y, s, a, nm) in ((-900, -1100, 1.4, 40, 'ldgreenbear'), (1350, -1300, 1.5, 120, 'ldredbear'), (-1500, 200 + 380, 1.4, 300, 'ldyellowbear'),
                             (800, -200, 1.3, 200, 'ldorangebear'), (-1100, 1100, 1.4, 20, 'ldredbear')):
        def f(px, py, s=s, a=a, nm=nm): solid_mdl('gummybears/' + nm + '.md3', px, py, 0, s, a)
        put(f, x, y, 130)
    # urns + stone pedestal lamps + lampposts along the paths
    for (x, y) in ((-300, -1550), (300, -1550), (-950, -50), (650, 40), (1050, 1150)):
        def f(px, py):
            custom('urn', px, py, 0); A(box((round(px - 44), round(py - 44), 0), (round(px + 44), round(py + 44), 220), WCLIP))
        put(f, x, y, 80)
    for (x, y) in ((-1000, -1700 + 40), (1000, -1650), (-180, 300), (1650, -1000), (-2000, 600)):
        def f(px, py):
            custom('pedestal', px, py, 0); A(box((round(px - 52), round(py - 52), 0), (round(px + 52), round(py + 52), 500), WCLIP))
            light(px, py, 572, 220, '1 0.85 0.6')
        put(f, x, y, 80)
    for (x, y) in ((-600, -1200), (600, -1250), (200, 40), (-1250, -1250), (1250, -150), (900, 900)):
        def f(px, py):
            custom('lamppost', px, py, 0); A(cyl(round(px), round(py), 12, 0, 430, WCLIP, 8))
            light(px, py, 404, 160, '1 0.85 0.6')
        put(f, x, y, 60)
    # candy canes along the river banks and the paths
    for (x, y, a) in ((-60, 980 - 100, 0), (560, 560, 90), (-1150, 650, 200), (-2000, 360, 30), (1300, 260, 120), (-400, -1600, 300),
                      (400, -1650, 240), (1000, -950, 60)):
        def f(px, py, a=a):
            custom('cane', px, py, 0, angle=a); A(cyl(round(px), round(py), 16, 0, 300, WCLIP, 8))
        put(f, x, y, 60)
    # big catalog plants: bushes, ferns, sunflowers (with clip where they are dense)
    for (x, y, s, a) in ((-2050, -1200, 1.0, 20), (2100, -800, 1.0, 200), (-2100, 1150, 0.9, 80), (1500, 1250, 0.9, 260),
                         (-700, 300 - 60, 0.8, 140), (1800, -1750, 0.9, 120)):
        def f(px, py, s=s, a=a): solid_mdl('pad_ddmix/trashcan/bush.md3', px, py, 0, s, a)
        put(f, x, y, 160)
    for (x, y, s, a) in ((-2150, -1650, 0.7, 10), (2150, -1650, 0.7, 110), (-1950, 1000 + 200, 0.5, 60), (1700, 950 + 300, 0.55, 200)):
        def f(px, py, s=s, a=a): mdl_c('pad_ddmix/plants/fern.md3', px, py, 0, s, a)
        put(f, x, y, 200 * s)
    for (x, y, nm, s, a) in ((-1300, -1650, 'pad_sunflower_l', 0.9, 30), (1500, -1600, 'pad_sunflower_l', 1.0, 200), (2150, 1100, 'pad_sunflower_l', 0.9, 260),
                             (-2150, 200, 'pad_sunflower3', 1.6, 80), (900, 1300, 'pad_sunflower6', 1.6, 140), (-500, -1750, 'pad_sunflower', 1.6, 300)):
        def f(px, py, nm=nm, s=s, a=a): mdl_c(f'pad_sunflower/{nm}.md3', px, py, 0, s, a)
        put(f, x, y, 80)
    # small dressing: toadstools, candy flowers, tulips, flowers (walk-through)
    kinds = ['toad_a', 'toad_b', 'flower_a', 'flower_b', 'flower_c']
    n = 0
    for _ in range(400):
        x, y = rng.uniform(-2200, 2200), rng.uniform(-1820, 1300)
        if not free(x, y, 70): continue
        nm = kinds[n % len(kinds)]
        custom(nm, x, y, 0, angle=int(rng.uniform(0, 360)), mul=rng.uniform(0.8, 1.3), lit=False)
        KEEP_OUT.append((x, y, 70)); n += 1
        if n >= 46: break
    for _ in range(300):
        x, y = rng.uniform(-2200, 2200), rng.uniform(-1820, 1300)
        if not free(x, y, 90): continue
        nm = ['pad_ddmix/plants/flower_pink.md3', 'pad_ddmix/plants/flower_yellow.md3', 'pad_ddmix/plants/tulip1.md3'][n % 3]
        mdl_c(nm, x, y, 0, [0.7, 0.6, 0.6][n % 3], int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 90)); n += 1
        if n >= 70: break


def blockers():
    """extra cover where sightlines.py --hot showed the long eye-level rays (central/south meadow)"""
    rng = np.random.default_rng(57)
    spots = [(-192, -832), (576, -576), (-192, -64), (448, -1088), (64, -832), (-320, -832), (320, -320), (704, -576),
             (-576, -1088), (832, -576), (-704, -576), (832, -64), (-900, -1300), (1250, -1250), (-1500, -500), (1550, -500),
             (300, -1500), (-800, 300), (150, 650), (-1900, 900 - 100), (300, -60), (700, -40), (1000, -150), (1250, -80),
             (-1000, -150), (-200, 320), (-150, 520), (-1450, -200), (-60, -60)]
    kinds = ['jaw', 'cup', 'bon', 'gum', 'bush', 'jaw', 'urn', 'gum']
    n = 0
    for i, (x, y) in enumerate(spots):
        k = kinds[i % len(kinds)]
        r = {'jaw': 130, 'cup': 110, 'bon': 160, 'gum': 70, 'bush': 140, 'urn': 60}[k]
        p = near_free(x, y, r, 300, pathgap=r + 20)
        if p is None:
            print('blocker skipped at', x, y); continue
        px, py = p
        if k == 'jaw':
            s = float(rng.uniform(1.5, 1.9)); nm = ['jaw_a', 'jaw_b', 'jaw_c', 'jaw_d'][i % 4]
            custom(nm, px, py, 0, angle=int(rng.uniform(0, 360)), mul=s); ball_clip(px, py, 0, CM.JAW_R * s)
        elif k == 'cup':
            custom('cupcake', px, py, 0, angle=int(rng.uniform(0, 360))); A(cyl(round(px), round(py), 96, 0, 250, WCLIP, 12))
        elif k == 'bon':
            a = int(rng.uniform(0, 180)); custom('bonbon_a' if i % 2 else 'bonbon_b', px, py, 0, angle=a)
            A(rbox(px, py, a, -104, 104, -66, 66, 0, 132, WCLIP))
        elif k == 'gum':
            nm = ['redbear', 'greenbear', 'yellowbear', 'orangebear'][i % 4]
            solid_mdl('gummybears/' + nm + '.md3', px, py, 0, 1.4, int(rng.uniform(0, 360)))
        elif k == 'bush':
            solid_mdl('pad_ddmix/trashcan/bush.md3', px, py, 0, 0.9, int(rng.uniform(0, 360)))
        else:
            custom('urn', px, py, 0); A(box((round(px - 44), round(py - 44), 0), (round(px + 44), round(py + 44), 220), WCLIP))
        KEEP_OUT.append((px, py, r)); n += 1
    return n


def stone_path():
    """crazy-paving path stones (nonsolid 1u decals) along PATHS: balcony stairs -> bridge, boat, stair-bridge, ledge"""
    from scipy.spatial import Voronoi
    rng = np.random.default_rng(7)
    pts = []
    for r in PATHS:
        for (a, b) in zip(r, r[1:]):
            a, b = np.array(a, float), np.array(b, float)
            Ln = np.linalg.norm(b - a); d = (b - a) / Ln; nrm = np.array([-d[1], d[0]])
            for s in np.arange(0, Ln, 50):
                for w in (-50, 0, 50):
                    pts.append(a + d * s + nrm * (w + rng.uniform(-12, 12)) + d * rng.uniform(-12, 12))
    pts = np.array(pts)
    # thin out duplicates where segments meet
    keep = []
    for p in pts:
        if all(np.hypot(*(p - q)) > 30 for q in keep[-60:]): keep.append(p)
    pts = np.array(keep)
    vor = Voronoi(pts)
    stones = 0
    for i, ri in enumerate(vor.point_region):
        reg = vor.regions[ri]
        if -1 in reg or len(reg) < 3: continue
        poly = vor.vertices[reg]
        c = pts[i]
        if np.max(np.linalg.norm(poly - c, axis=1)) > 56: continue
        poly = c + (poly - c) * 0.85
        if not all(free(px, py, 0, path=False) for (px, py) in poly): continue
        if any(math.hypot(px - kx, py - ky) < kr for (px, py) in poly for (kx, ky, kr) in KEEP_OUT if kr >= 70): continue
        b = hull([(px, py, z) for (px, py) in poly for z in (0, 1)], {'top': T('path_ns'), 'side': NODRAW_NS, 'bot': NODRAW_NS}, round_pts=False)
        A(b); stones += 1
    return stones


# =================================================================================================== the fizzy lifting room (secret)
def fizzy_room():
    F = L.FIZZ
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('fizzy_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('fizzy_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    # gallery ring at z GZ (inner radius ~260) round the bubble column
    GZ = z0 + 640
    gi = 250
    for (a, b, c, d) in sub_rects((x0, y0, x1, y1), [(-gi, -gi, gi, gi)]):
        A(box((a, b, GZ - 24), (c, d, GZ), {'top': T('fizzy_floor'), 'side': T('gold'), 'bot': T('fizzy_wall')}))
    # bubble lift: trigger_push from the floor centre up to the gallery
    A(cyl(0, 0, 90, z0, z0 + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 16))
    trig = box((-70, -70, z0 + 6), (70, 70, z0 + 90), TRIG)
    o = (0, 0, z0 + 48)
    land = (0, -360, GZ)
    tx, ty = pad_target(o, land, GZ + 200)
    M.ent('trigger_push', brushes=[trig], target='fizz_lift')
    M.ent('target_position', (round(tx), round(ty), GZ + 200), targetname='fizz_lift')
    JUMPPADS.append(('fizz_lift', o, (round(tx), round(ty), GZ + 200), land))
    for k in range(6):
        a = k * 60
        x, y = ang_pt(0, 0, 60, a)
        A(sprite(x, y, z0 + 8, GZ + 240, 'bubbles', 60, a + 90))
    # the fan above (func_rotating), dangerously close to the gallery
    fz = GZ + 300
    M.ent('func_rotating', brushes=[box((-8, -8, fz - 8), (8, 8, fz + 8), ORIGIN), box((-4, -4, fz - 4), (4, 4, fz + 4), NODRAW_NS)],
          model2=CM.PLACE['fan'][0], speed=90, spawnflags=0, dmg=0)
    A(cyl(0, 0, 12, fz + 30, z1, T('iron'), 8))
    # signs + bottles on the floor
    A(sign_box((-180, y1 - 8, z0 + 260), (180, y1, z0 + 440), T('sign_fizzy'), 512, 256, facing='s'))
    for (x, y, nm, a) in ((-330, 330, 'bottle_pink', 0), (330, 330, 'bottle_blue', 90), (-330, -330, 'bottle_green', 200), (330, -330, 'bottle_pink', 300)):
        custom(nm, x, y, z0, angle=a); A(cyl(x, y, 56, z0, z0 + 330, WCLIP, 12))
    item('item_padpower', 0, 360, GZ)
    item('item_revival', -360, 0, GZ)
    item('ammo_imperius', 360, 0, GZ)
    item('holdable_killerducks', 0, -200, z0)
    item('ammo_betty', 200, 120, z0)
    M.ent('misc_teleporter_dest', (-200, -360, z0 + 24), targetname='fizz_in', angle=90)
    # exit teleporter on the floor (WoP catalog pad) back to the meadow
    mdl_c('pad_teleporter/padtp_purple.md3', 200, -330, z0, 1.0, 0)
    M.ent('trigger_teleport', brushes=[box((164, -366, z0 + 2), (236, -294, z0 + 90), TRIG)], target='fizz_out')
    M.ent('misc_teleporter_dest', (-1350, -620, 24), targetname='fizz_out', angle=0)
    KEEP_OUT.append((-1350, -620, 120))
    for (x, y, z, c) in ((0, 0, z0 + 200, '1 0.7 0.9'), (0, 0, GZ + 160, '0.7 0.9 1'), (-300, 300, z0 + 300, '1 1 0.8'), (300, -300, z0 + 300, '0.8 1 1')):
        light(x, y, z, 400, c)
    speaker(0, 0, fz - 40, 'sound/world/machine/fan_pc.ogg', volume=0.8)
    speaker(0, 0, z0 + 100, 'sound/world/ambient/water_bubbling.ogg', volume=0.7)


# =================================================================================================== east shoulder stairs
def east_stairs():
    x0, x1 = 2080, L.HX
    y0 = 1504 - 32 * 30
    for k in range(30):
        zt = 16 * (k + 1)
        A(box((x0, y0 + 32 * k, 0), (x1, y0 + 32 * (k + 1), zt), {'top': T('rock_top'), 'side': T('rock'), 'bot': CAULK}))
    KEEP_OUT.append(((x0 + x1) / 2, (y0 + 1504) / 2, 520))
    # top of the east shoulder: pad up to the summit, ammo
    jumppad(1880, 1720, 480, (1420, 1720, L.SUMMIT_Z), 1220, 'shoulder_summit')
    item('ammo_imperius', 2000, 1840, 480)
    item('ammo_betty', 1700, 1600 + 40, 480)
    light(1900, 1700, 760, 300, '1 0.95 0.85')


# =================================================================================================== items, spawns, light, sound
def items_misc():
    item('ammo_nipper', 600, -1100, 0)
    item('ammo_nipper', -1600, -300, 0)
    item('item_armor_shard', -400, -1500, 0)
    item('item_armor_shard', 1400, -1000, 0)
    item('item_armor_shard', -1200, 900 - 300, 0)
    item('ammo_boaster', 900, -100, 0)
    item('ammo_bubbleg', 1700, -1200, 0)
    item('ammo_balloony', -900, -300, 0)
    item('ammo_betty', -1500, -100, 0)


def spawns():
    pts = [(-1800, -1300, 45), (1800, -1300, 135), (-600, -1000, 60), (600, -1100, 120), (-1100, -500, 0), (1100, -400, 180),
           (-300, 0, 270), (500, 0, 225), (1000, 700, 200), (-1100, 800 - 160, 315), (1700, -600, 160), (-1900, -200, 20),
           (-500, 1050, 300), (1400, 1250, 250), (60, -1500, 90), (-1500, -1700 + 40, 70)]
    for (x, y, a) in pts:
        p = near_free(x, y, 40, 300)
        if p: spawn(p[0], p[1], 0, a)
    spawn(-800, 1420, L.DECK_Z, 270)
    spawn(-100, 1850, L.SUMMIT_Z, 270)


def lights_and_sound():
    # soft daylight fill under the glass roof (the sun does the main work)
    for x in (-1700, -560, 560, 1700):
        for y in (-1300, -300, 700):
            light(x, y, 1500, 900, '1 0.97 0.9')
    timer_sound(-1800, -1000, 900, 'sound/world/animal/bird_blackcap.ogg', 'bird1', 25, 15)
    timer_sound(1800, -200, 900, 'sound/world/animal/bird_vireo.ogg', 'bird2', 30, 15)
    timer_sound(0, 1200, 900, 'sound/world/animal/blackbird.ogg', 'bird3', 35, 20)
    timer_sound(-800, 1000, 260, 'sound/world/misc/steam_leakage.ogg', 'steam', 40, 20, volume=0.6)
    timer_sound(-1500, -1050, 300, 'sound/world/misc/toy_squeeze.ogg', 'squeak', 45, 25)
    speaker(0, 0, 1700, 'sound/world/ambient/shrubbery.ogg', volume=0.25)


def jumppad_list(): return JUMPPADS


def write_routes():
    """on-foot routes for aas_check.py --route @routes.txt (generated, because the boat/stones follow the river)"""
    bcx, bcy, bang, jx, jy, nx, ny = BOAT_INFO
    sx, sy, snx, sny = STONES_INFO
    scx = (L.SHED[0] + L.SHED[2]) / 2
    R = [('balc_stairs_w', (-2150, -1810, 0), (-1100, -1810, L.BALC_Z)),
         ('balc_stairs_e', (2150, -1810, 0), (1100, -1810, L.BALC_Z)),
         ('lobby_door', (0, -1780, L.BALC_Z), (0, -2150, L.BALC_Z)),
         ('stair_bridge', (-364, -60, 0), (-364, 1000, L.DECK_Z)),
         ('shed_door', (scx, 1000, L.DECK_Z), (scx - 100, 1170, L.DECK_Z)),
         ('deck_shoulder', (-1000, 1400, L.DECK_Z), (-1600, 1700, L.DECK_Z)),
         ('ledge_cave', (1120, 1300, 0), (700, 1650, 0)),
         ('well_summit', (700, 1650, 0), (1400, 1650, L.SUMMIT_Z)),
         ('east_stairs', (2190, 440, 0), (2190, 1700, 480)),
         ('yellow_door', (L.YELLOW[0], L.YELLOW[1] - 520, 0), (L.YELLOW[0], L.YELLOW[1], 8)),
         ('under_redcap', (L.REDCAP[0] - 420, L.REDCAP[1], 0), (L.REDCAP[0] + 330, L.REDCAP[1] + 60, 0)),
         ('bridge', (560, 460, 0), (70, 1180, 0)),
         ('stones', (sx + snx * 380, sy + sny * 380, 0), (sx - snx * 380, sy - sny * 380, 0)),
         ('boat_jetty', (jx + nx * 150, jy + ny * 150, 0), (bcx, bcy, 0)),
         ('tree_mound', (L.TREE_W[0] + 470, L.TREE_W[1], 0), (L.TREE_W[0] + 200, L.TREE_W[1] + 40, L.MOUND_H)),
         ('summit_channel', (400, 1750, L.SUMMIT_Z), (1000, 1600, L.SUMMIT_Z))]
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padcandy/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_candy.py\n')
        for (n, a, b) in R:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== main
def main():
    def extra():
        CM.make_aug((L.PIPE_START[0], L.PIPE_START[1], (L.RIV_FLOOR + 40) / 2), (L.PIPE_LAND[0], L.PIPE_LAND[1], L.SUMMIT_Z), AUG_APEX)
        stairbridge_model()
    W = TX.make_all(OUT, extra)
    hall(); pumphouse()                     # pumphouse adds the stair-bridge posts to RIVER_SOLIDS
    river_things()                          # boat hull, jetty, stones -> RIVER_SOLIDS
    ground(); cliff(); falls(); cave_and_well(); summit()
    for nm in ('sb_rail_w', 'sb_rail_e'):
        o = CM.PLACE[nm + '_o']
        custom(CM.PLACE[nm], o[0], o[1], o[2])
    balcony(); lobby(); redcap(); yellowhouse(); trees(); grove(); east_stairs(); fizzy_room()
    items_misc(); spawns()
    n_stones = stone_path()
    blockers()
    garden()
    lights_and_sound()
    write_routes()
    TX.make_shader(W, OUT, CM.shaders())     # again: railings register their shaders after make_all (they drew without one)
    M.ent('info_player_intermission', (-1900, -1500, 1100), angles='22 40 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padcandy/build_candy.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}, path stones {n_stones}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
