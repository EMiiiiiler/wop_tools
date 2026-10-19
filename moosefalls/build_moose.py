#!/usr/bin/env python3
"""Moose Mountain Falls - World of Padman map generator (map 'wop_moosefalls').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_moose.py

Writes <OUT>/maps/wop_moosefalls.map, textures/moosefalls/*, models/moosefalls/*, scripts/moosefalls.shader and
scripts/wop_moosefalls.arena.

An indoor water park in a big timber lodge on a snowy evening (inspired by the Moose Mountain Falls park at Timber
Ridge Lodge). Human scale (~32u per metre). x east, y north, deck z 0, water surface z -16. Glulam rafters, painted
columns, tan ducts and pendant floodlights under a pine-board ceiling; a skylight along the ridge and big windows show
the snowy forest outside.

  Tree island      centre: a giant pine growing out of an island ringed by the Lazy Bear River (48 deep, wade it;
                   stairs out on both banks, two wooden bridges). A spiral stair round the trunk climbs to the
                   Eagle's Nest deck (Pad shield); a pad on the deck shoots you up to the crow's nest (Imperius).
  Activity pool    north-west: lily-pad crossing under a cargo net, basketball hoop, beach entry; the deep end under
                   the Grotto waterfall hides the Splasher on the bottom. Swim through the waterfall into the cave
                   (SECRET: Pad Power), walk out of the cave's dry tunnel onto the north deck.
  Timber Peak      north-east: log-built slide tower; stairs wind up the outside to the platform (Pumper), a pad goes
                   up to the roof (Floater). Yellow Jacket, a closed tube, circles the tree island and dumps you in
                   the river; Green Gulch, an open flume, runs down the east wall into the plunge pool.
  Plunge pool      east: steps down into deep water (Killer Ducks on the bottom).
  Moose Lodge Grill  north: walk in at the side door (Boaster in the kitchen); stairs up to the roof deck and the
                   porch roof.
  Tiny Timbers     south-east: kids' play structure on a splash pad - crawl tunnel through the log base, stairs to
                   the deck, three little slides, a pad up to the bucket tower (Betty).
  Lookout stump    south-west: walk into the hollow trunk, a pad inside fires you onto the top deck (Balloony) with a
                   little log hut (walk in; steps to its roof).
  Seating, loungers, Adirondack chairs, lifeguard chairs, a carved moose on a rock, potted pines and ferns break up
  the deck.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import moose_textures as TX
import moose_models as MM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
SNDROOT = os.environ.get('SNDROOT', '')
MAPNAME = 'wop_moosefalls'
T = lambda n: 'moosefalls/' + n
CAULK = 'common/caulk'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
PCLIP = 'common/clip'; BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns'); SLICK = T('slide_clip')

for k, v in {'deck': (1, 1), 'coping': (0.5, 0.5), 'pool_tile': (0.5, 0.5), 'pool_band': (1, 1), 'lane': (0.5, 0.5),
             'splashpad': (1, 1), 'kitchen_tile': (0.5, 0.5), 'planks': (0.5, 0.5), 'planks_dark': (0.5, 0.5), 'ceiling': (0.5, 0.5),
             'glulam': (0.5, 0.5), 'stucco': (1, 1), 'stucco_green': (1, 1), 'stucco_cream': (1, 1), 'wainscot': (0.5, 0.5),
             'logwall': (0.5, 0.5), 'fieldstone': (0.5, 0.5), 'rock': (1, 1), 'bark': (1, 1), 'rotten': (1, 1), 'glass': (2, 2),
             'roof_red': (0.5, 0.5), 'shingles': (0.5, 0.5), 'water': (1, 1), 'steel': (0.5, 0.5), 'metal_white': (0.5, 0.5),
             'mural': (2, 2), 'lily': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '14', '_color': '1 0.9 0.8', 'gridsize': '96 96 128', '_blocksize': '0'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
KEEP_OUT = []                   # (x, y, r) discs where floor decoration must not go
NOGO = []                       # (x0, y0, x1, y1) rects: no slide supports / decoration
CX, CY = L.C


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


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.15, round_n=0, top_cut=4):
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


def custom(placed, x, y, zbase, angle=0, lit=True, mul=1.0, **kw):
    """one of our own MD3s; placed = (path, scale, zoff) from moose_models"""
    path, sc, zo = placed
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=sc, angle=angle, **extra)


def light(x, y, z, val, color='1 0.85 0.7', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def snd(name):
    """sound path with the extension WoP really ships (ogg or wav)"""
    for ext in ('.ogg', '.wav'):
        if SNDROOT and os.path.exists(os.path.join(SNDROOT, 'sound', 'world', name + ext)): return f'sound/world/{name}{ext}'
    return f'sound/world/{name}.ogg'


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': snd(noise) if not noise.startswith('sound/') else noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
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
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.7: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def jumppad(x, y, z, land, apex, name, glow=True):
    """splash launcher pad (r 34 disc) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of the
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
    if glow: light(x, y, z + 48, 100, '0.5 0.9 1')
    KEEP_OUT.append((x, y, 80))


def sprite(x, y, z0, z1, tex, w, ang=0):
    """thin vertical slab (2u), shader on both broad faces"""
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


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, tex, z0b=None, z1b=None):
    """wedge of a ring band between angles a0..a1 (deg); r0 == 0 gives a pie slice"""
    z0b = z0 if z0b is None else z0b; z1b = z1 if z1b is None else z1b
    pts = []
    for a in (a0, a1):
        for (r, za, zb) in ((r0, z0, z1), (r1, z0b, z1b)):
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


def in_rect(x, y, r, m=0):
    return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m


def on_deck(x, y, m=24):
    """open deck floor at z 0 (slide supports, decoration)"""
    if abs(x) > L.HX - m or abs(y) > L.HY - m: return False
    d = math.hypot(x - CX, y - CY)
    if d < L.R_RIV + m: return False
    if any(in_rect(x, y, r, m) for r in L.POOL_A + [L.POOL_P, L.ROCK]): return False
    if any(in_rect(x, y, r, m) for r in NOGO): return False
    return True


def free(x, y, r):
    return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT) and on_deck(x, y, r)


def near_free(x, y, r, search=320):
    """closest free spot to (x, y) within `search` (spiral of candidates), or None"""
    if free(x, y, r): return (x, y)
    for d in range(32, search + 1, 32):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if free(px, py, r): return (round(px), round(py))
    return None


# =================================================================================================== hall: hull, slab, walls, roof
def hull_box():
    W = 16
    X0, Y0 = L.HX + L.WALL + 64, L.HY + L.WALL + 64
    Z0, Z1 = L.SLAB_BOT - 32, L.RIDGE + L.ROOF_T + 160
    sk = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((-X0 - W, -Y0 - W, Z0 - W), (X0 + W, Y0 + W, Z0), dict(sk, top=T('sky')), detail=False))
    A(box((-X0 - W, -Y0 - W, Z1), (X0 + W, Y0 + W, Z1 + W), dict(sk, bot=T('sky')), detail=False))
    A(box((-X0 - W, Y0, Z0), (X0 + W, Y0 + W, Z1), dict(sk, s=T('sky')), detail=False))
    A(box((-X0 - W, -Y0 - W, Z0), (X0 + W, -Y0, Z1), dict(sk, n=T('sky')), detail=False))
    A(box((X0, -Y0, Z0), (X0 + W, Y0, Z1), dict(sk, w=T('sky')), detail=False))
    A(box((-X0 - W, -Y0, Z0), (-X0, Y0, Z1), dict(sk, e=T('sky')), detail=False))


POOL_TILE_A = (-1984, 224, -800, 1504)
RIV_TILE = (CX - 768, CY - 768, CX + 768, CY + 768)
POOL_TILE_P = (L.POOL_P[0] - 16, L.POOL_P[1] - 16, L.POOL_P[2] + 16, L.POOL_P[3] + 16)
ZONES = []          # (rect, top texture) floor zones (later override earlier)


def slab():
    X1, Y1 = L.HX + L.WALL, L.HY + L.WALL
    tiles = [POOL_TILE_A, RIV_TILE, POOL_TILE_P]
    cuts = list(tiles) + [z[0] for z in ZONES]
    for r in sub_rects((-X1, -Y1, X1, Y1), cuts):
        A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('deck'), 'side': CAULK, 'bot': CAULK}))
    for i, (zr, tex) in enumerate(ZONES):
        later = [z[0] for z in ZONES[i + 1:]]
        for r in sub_rects(zr, later + tiles):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': tex, 'side': CAULK, 'bot': CAULK}))


def pool_faces(b, wall=T('pool_band'), floor=T('pool_tile'), top=T('coping')):
    for f in b.faces:
        zmax = max(p[2] for p in f.pts)
        if f.n[2] > 0.99 and abs(zmax) < 0.5: f.tex = top
        elif f.n[2] < -0.99: f.tex = CAULK
        elif abs(f.n[2]) < 1e-3 and (abs(abs(f.n[0]) - 1) < 1e-6 or abs(abs(f.n[1]) - 1) < 1e-6) and \
                _on_tile_edge(f): f.tex = CAULK
        elif f.n[2] > 0.3: f.tex = floor
        else: f.tex = wall
        f.sc = wopmap.default_scale(f.tex)
        if f.tex == wall: f.off = (0, 0)
    return b


_TILES = []


def _on_tile_edge(f):
    xs = [p[0] for p in f.pts]; ys = [p[1] for p in f.pts]
    for t in _TILES:
        if abs(f.n[0]) > 0.5 and (all(abs(x - t[0]) < 0.5 for x in xs) or all(abs(x - t[2]) < 0.5 for x in xs)): return True
        if abs(f.n[1]) > 0.5 and (all(abs(y - t[1]) < 0.5 for y in ys) or all(abs(y - t[3]) < 0.5 for y in ys)): return True
    return False


def water_faces(b):
    for f in b.faces:
        f.tex = T('water') if (f.n[2] > 0.99 and abs(max(p[2] for p in f.pts) - L.WATER) < 0.5) else T('water_nodraw')
        f.sc = (1, 1)
    return b


def walls():
    """long walls (windows), gable walls (west: grotto + sign; east: big triangular window), roof with ridge skylight"""
    X1, Y1, Wt = L.HX, L.HY, L.WALL
    s = (L.RIDGE - L.EAVE) / L.HY
    WIN = (112, 464)
    def wtex(face, lower=False):
        return {'side': CAULK, face: T('wainscot') if lower else T('stucco'), 'top': CAULK, 'bot': CAULK}
    for sg in (-1, 1):
        y0, y1 = (Y1, Y1 + Wt) if sg > 0 else (-Y1 - Wt, -Y1)
        face = 's' if sg > 0 else 'n'
        # window openings
        opens = []
        for xc in range(-1792, 1793, 384):
            if sg > 0 and (xc < -1400 or -640 < xc < 640): continue          # grotto, snack bar
            opens.append((xc - 128, xc + 128))
        xs = [-X1 - Wt]
        for (a, b) in opens: xs += [a, b]
        xs.append(X1 + Wt)
        # lower band, piers
        A(box((-X1 - Wt, y0, 0), (X1 + Wt, y1, 96), wtex(face, True)))
        A(box((-X1 - Wt, y0, 96), (X1 + Wt, y1, WIN[0]), wtex(face)))
        for i in range(0, len(xs), 2):
            A(box((xs[i], y0, WIN[0]), (xs[i + 1], y1, WIN[1]), wtex(face)))
        for (a, b) in opens:
            gl = box((a, (y0 + y1) / 2 - 2, WIN[0]), (b, (y0 + y1) / 2 + 2, WIN[1]), T('glass'))
            A(gl)
            M.ent('light', (round((a + b) / 2), round(sg * (Y1 - 40)), 300), light=160, _color='0.6 0.75 1')
        # top band up to the roof underside (sloped top)
        zin = L.EAVE; zout = L.EAVE - Wt * s
        yi, yo = (y0, y1) if sg > 0 else (y1, y0)
        A(hull([(x, yi, z) for x in (-X1 - Wt, X1 + Wt) for z in (WIN[1], zin)] + [(x, yo, z) for x in (-X1 - Wt, X1 + Wt) for z in (WIN[1], zout)],
               wtex(face)))
    # gable walls
    for sx in (-1, 1):
        x0, x1 = (X1, X1 + Wt) if sx > 0 else (-X1 - Wt, -X1)
        face = 'w' if sx > 0 else 'e'
        tex = {'side': CAULK, face: T('stucco_cream'), 'top': CAULK, 'bot': CAULK}
        A(box((x0, -Y1, 0), (x1, Y1, 96), {'side': CAULK, face: T('wainscot'), 'top': CAULK, 'bot': CAULK}))
        A(box((x0, -Y1, 96), (x1, Y1, L.EAVE), tex))
        # gable triangle: east = glass strips between mullions, west = solid with the mural
        if sx > 0:
            # triangle with window strips cut out (carve keeps the mullions), glass panes in the holes
            tri = hull([(x, y, z) for y in (-Y1, Y1, 0) for x in (x0, x1) for z in (L.EAVE, L.roof_z(y))], tex)
            cutters, panes = [], []
            for ya in range(-1280, 1280, 256):
                yb = ya + 240
                parts = [(ya, 0), (0, yb)] if ya < 0 < yb else [(ya, yb)]
                for (pa, pb) in parts:
                    za, zb = L.roof_z(pa) - 48, L.roof_z(pb) - 48
                    if min(za, zb) < L.EAVE + 96: continue
                    cutters.append(hull([(x, y, z) for x in (x0 - 4, x1 + 4) for (y, zt) in ((pa, za), (pb, zb)) for z in (L.EAVE + 48, zt)], CAULK))
                    xm = (x0 + x1) / 2
                    panes.append(hull([(x, y, z) for x in (xm - 2, xm + 2) for (y, zt) in ((pa, za), (pb, zb)) for z in (L.EAVE + 48, zt)], T('glass')))
            for pc in carve(tri, cutters):
                for f in pc.faces:
                    if abs(f.n[0]) > 0.99: f.tex = T('stucco_cream') if f.n[0] < 0 else CAULK
                    else: f.tex = T('mullion')
                A(pc)
            for pn in panes: A(pn)
            M.ent('light', (L.HX - 80, 0, 900), light=500, _color='0.6 0.75 1')
        else:
            pts = []
            for y in (-Y1, Y1, 0):
                zr = L.roof_z(y)
                pts += [(x, y, L.EAVE) for x in (x0, x1)] + [(x, y, zr) for x in (x0, x1)]
            A(hull(pts, tex))
    # main sign + mural on the west gable (above the grotto / pool)
    sb = sign_box((-L.HX, -560, 700), (-L.HX + 8, 560, 980), T('sign_main'), 1024, 256, back=CAULK, facing='e')
    A(sb)
    mb = sign_box((-L.HX, -1500, 140), (-L.HX + 4, -260, 640), T('mural'), 1024, 512, back=CAULK, facing='e')
    A(mb)
    # roof: two slabs from the skylight to beyond the walls, glass strip along the ridge between the rafters
    for sg in (-1, 1):
        ya, yb = sg * L.SKY_Y, sg * (L.HY + Wt + 8)
        pts = []
        for y in (ya, yb):
            zu = L.RIDGE - (L.RIDGE - L.EAVE) * abs(y) / L.HY
            pts += [(x, y, z) for x in (-X1 - Wt, X1 + Wt) for z in (zu, zu + L.ROOF_T)]
        rt = lambda n, sg=sg: T('ceiling') if n[2] < -0.5 else CAULK
        A(hull(pts, rt))
        # glass: strips between rafters (rafter lines carry a glulam bar)
        xs = sorted(set([-X1 - Wt] + [v for x in L.RAFTER_X for v in (x - 20, x + 20)] + [X1 + Wt]))
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            tex = T('glass') if i % 2 == 0 else T('glulam')
            pts = []
            for y in (0, ya):
                zu = L.RIDGE - (L.RIDGE - L.EAVE) * abs(y) / L.HY
                pts += [(x, y, z) for x in (xa, xb) for z in (zu, zu + (4 if tex == T('glass') else L.ROOF_T))]
            if tex == T('glass'):
                pts = [(x, y, z + 6) for (x, y, z) in pts]
            A(hull(pts, tex))
    # sky light through the ridge glass
    for x in (-1700, -1150, -600, 0, 600, 1150, 1700):
        M.ent('light', (x, 0, L.RIDGE - 60), light=300, _color='0.6 0.72 1')


def hall_timbers():
    """rafters, ridge beam, ducts, columns, pendant lamps"""
    for x in L.RAFTER_X:
        custom(MM.PLACE['rafter'], x, 0, 0)
    custom(MM.PLACE['ridge_beam'], 0, 0, 0)
    hang = L.roof_z(L.DUCT_Y[0]) - (L.DUCT_Z + 40) + 1
    dp = MM.duct(hang)
    for y in L.DUCT_Y:
        custom(dp, 0, y, L.DUCT_Z)
        speaker(-1000, y, L.DUCT_Z, 'machine/ventilation', volume=0.25)
    # columns (collision 16-gon) with knee braces where a rafter runs above
    made = {}
    for (x, y) in L.COLUMNS:
        H = round(L.roof_z(y) - 72) if x in L.RAFTER_X else round(L.roof_z(y + 22 * (1 if y > 0 else -1)))
        key = (H, x in L.RAFTER_X, y > 0)
        if key not in made:
            braces = [-180, 180] if x in L.RAFTER_X else []
            made[key] = MM.column(f'column{len(made)}', H, braces)
        custom(made[key], x, y, 0)
        A(cyl(x, y, 34, 0, 166, WCLIP, 16, phase=0))
        A(box((x - 20, y - 20, 166), (x + 20, y + 20, min(H, 700)), WCLIP))
        KEEP_OUT.append((x, y, 80))
        NOGO.append((x - 60, y - 60, x + 60, y + 60))
    # pendant floodlights between the rafters
    lamps = {}
    for x in (-1920, -1152, -384, 384, 1152, 1920):
        for y in (-1216, -704, 704, 1216):
            zr = L.roof_z(y)
            rod = 96 if abs(y) > 1000 else 320
            if (x, y) in ((384, 704), (-384, 704)): rod = 400
            if rod not in lamps: lamps[rod] = MM.lamp(f'lamp{rod}', rod)
            custom(lamps[rod], x, y, zr, lit=False)
            light(x, y, zr - rod - 60, 2200, '1 0.82 0.6')


# =================================================================================================== activity pool + grotto
def activity_pool():
    tile = box((POOL_TILE_A[0], POOL_TILE_A[1], L.SLAB_BOT), (POOL_TILE_A[2], POOL_TILE_A[3], 0), CAULK)
    _TILES.append(POOL_TILE_A)
    dz = L.POOL_DEEP; sz = L.POOL_SHALLOW
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = L.POOL_A
    cut = [box((ax0, ay0, dz), (ax1, ay1, 32), CAULK),
           box((bx0, by0, dz), (L.DEEP_X1, by1, 32), CAULK),
           hull([(L.DEEP_X1, y, dz) for y in (by0, by1)] + [(L.SHALLOW_X0, y, sz) for y in (by0, by1)] +
                [(x, y, 32) for x in (L.DEEP_X1, L.SHALLOW_X0) for y in (by0, by1)], CAULK),
           box((L.SHALLOW_X0, by0, sz), (L.BEACH_X0, by1, 32), CAULK),
           hull([(L.BEACH_X0, y, sz) for y in (by0, by1)] + [(bx1, y, 0) for y in (by0, by1)] +
                [(x, y, 32) for x in (L.BEACH_X0, bx1) for y in (by0, by1)], CAULK),
           # cave mouth basin (ramp up into the grotto)
           hull([(x, L.MOUTH[1], -64) for x in (L.MOUTH[0], L.MOUTH[2])] + [(x, L.MOUTH[3], 0) for x in (L.MOUTH[0], L.MOUTH[2])] +
                [(x, y, 32) for x in (L.MOUTH[0], L.MOUTH[2]) for y in (L.MOUTH[1], L.MOUTH[3])], CAULK)]
    for b in carve(tile, cut):
        A(pool_faces(b))
    # water: same shapes up to the surface (beach part only where deeper than the surface)
    W = L.WATER
    xw = L.BEACH_X0 + (W - sz) / (0 - sz) * (bx1 - L.BEACH_X0)
    wat = [box((ax0, ay0, dz), (ax1, ay1, W), CAULK), box((bx0, by0, dz), (L.DEEP_X1, by1, W), CAULK),
           hull([(L.DEEP_X1, y, dz) for y in (by0, by1)] + [(L.SHALLOW_X0, y, sz) for y in (by0, by1)] +
                [(x, y, W) for x in (L.DEEP_X1, L.SHALLOW_X0) for y in (by0, by1)], CAULK),
           box((L.SHALLOW_X0, by0, sz), (L.BEACH_X0, by1, W), CAULK),
           hull([(L.BEACH_X0, y, sz) for y in (by0, by1)] + [(xw, y, W) for y in (by0, by1)] + [(L.BEACH_X0, y, W) for y in (by0, by1)], CAULK),
           hull([(x, L.MOUTH[1], -64) for x in (L.MOUTH[0], L.MOUTH[2])] + [(x, L.MOUTH[1] + 48 * (L.MOUTH[3] - L.MOUTH[1]) / 64, W) for x in (L.MOUTH[0], L.MOUTH[2])] +
                [(x, L.MOUTH[1], W) for x in (L.MOUTH[0], L.MOUTH[2])], CAULK)]
    # rock island in the deep end (cover over the water; swim round it, climb out on the ladder or the beach)
    isl = [cyl(-1730, 820, 104, L.POOL_DEEP, 40, {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}, 12),
           cyl(-1730, 820, 70, 40, 88, {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}, 10)]
    for b in isl: A(b)
    custom(MM.PLACE['boulders_b'], -1735, 815, 88, angle=40, mul=0.6)
    A(cyl(-1730, 820, 56, 88, 120, WCLIP, 8))
    for b in wat:
        for pc in carve(b, isl[:1]):
            A(water_faces(pc))
    # lily-pad crossing (floating discs, top at the deck) under the cargo net
    lx = -1056
    for k, y in enumerate(range(340, 1400, 132)):
        b = cyl(lx + (24 if k % 2 else -24), y, 44, W, 0, {'top': T('lily'), 'side': T('lily_side'), 'bot': T('lily_side')}, 12)
        A(b)
    net = MM.net_frame(176, 1552)
    custom(net, lx, 0, 0)
    for y in (176, 1552):
        for dx in (-60, 60):
            A(box((lx + dx - 8, y - 8, 0), (lx + dx + 8, y + 8, 200), WCLIP))
    NOGO.append((lx - 90, 140, lx + 90, 1600))
    # hoop, ladders, lifeguard chair, signs
    custom(MM.PLACE['hoop'], -1290, ay1 + 30 + (by1 - ay1), 0, angle=270)
    KEEP_OUT.append((-1290, by1 + 30, 60))
    custom(MM.ladder(224), ax0, 640, 0, angle=180)
    custom(MM.ladder(64), -1100, by0, 0, angle=270)
    custom(MM.PLACE['lifeguard'], -700, 400, 0, angle=180)
    A(box((-720, 380, 0), (-680, 420, 120), WCLIP))
    KEEP_OUT.append((-700, 400, 70))
    for (x, y, t) in ((-1700, ay0 - 28, 'depth_70'), (-1000, by0 - 28, 'depth_30'), (-880, by1 + 28, 'depth_15'), (-1600, ay0 - 28, 'depth_40')):
        b = box((x - 32, y - 16, 0), (x + 32, y + 16, 1), {'top': T(t), 'side': NODRAW_NS, 'bot': NODRAW_NS})
        hfit(b, x - 32, y - 16, x + 32, y + 16, 128, 64, T(t))
        A(b)
    A(box((-812, 360, 0), (-804, 368, 120), T('metal_white')))
    A(sign_box((-804, 300, 120), (-800, 428, 184), T('nodiving'), 256, 128, back=T('metal_white'), facing='e'))
    # contents
    weapon('splasher', -1720, 560, L.POOL_DEEP, 'orange')
    item('ammo_splasher', -1300, 1380, L.POOL_SHALLOW)
    item('item_armor_shard', -1600, 160, 0)
    for (x, y, z) in ((-1500, 700, -100), (-1100, 500, -60), (-1100, 1200, -60)):
        light(x, y, z, 220, '0.5 0.85 1')
    speaker(-1200, 860, 0, 'ambient/water_rippling', volume=0.5)
    # beach-side floats
    for (x, y, nm, a) in ((-1250, 420, 'tube1p', 20), (-1320, 1200, 'tube1y', 80), (-1250, 960, 'tube1k', 150), (-1560, 420, 'tube2t', 40)):
        custom(MM.PLACE[nm], x, y, L.WATER, angle=a)
    mdl_c('pad_ducks/pad_duck.md3', -1620, 380, L.WATER, 0.3, 300)


def grotto():
    """rock mass in the north-west corner with a waterfall over the cave mouth; cave chamber with a dry exit east"""
    rx0, ry0, rx1, ry1 = L.ROCK
    rt = L.ROCK_TOP
    rock = box((rx0, ry0, 0), (rx1, ry1, rt), CAULK)
    cuts = [box((L.CAVE[0], L.CAVE[1], 0), (L.CAVE[2], L.CAVE[3], L.CAVE_Z), CAULK),
            box((L.MOUTH[0], L.MOUTH[1] - 8, -8), (L.MOUTH[2], L.MOUTH[3] + 8, 112), CAULK),
            box((L.CAVE_EXIT[0] - 8, L.CAVE_EXIT[1], 0), (L.CAVE_EXIT[2] + 8, L.CAVE_EXIT[3], 128), CAULK)]
    for b in carve(rock, cuts):
        for f in b.faces:
            p = [np.array(q) for q in f.pts]
            c = sum(p) / 3
            on_outer = (abs(f.n[1] + 1) < 1e-3 and abs(c[1] - ry0) < 0.5) or (abs(f.n[0] - 1) < 1e-3 and abs(c[0] - rx1) < 0.5) or \
                       (f.n[2] > 0.99 and abs(c[2] - rt) < 0.5)
            f.tex = CAULK if on_outer or f.n[2] < -0.99 and abs(c[2]) < 0.5 else T('rock')
            if abs(f.n[0] + 1) < 1e-3 and abs(c[0] - rx0) < 0.5: f.tex = CAULK
            if abs(f.n[1] - 1) < 1e-3 and abs(c[1] - ry1) < 0.5: f.tex = CAULK
            f.sc = (1, 1)
        A(b)
    # rock skins
    zb_s = lambda u: L.POOL_DEEP if u >= L.POOL_A[0][0] else 0
    custom(MM.rockface('rockface_s', rx0 + 4, rx1 + 20, zb_s, rt + 10, [(L.MOUTH[0] + 4, L.MOUTH[2] - 4, -70, 106)], 'x', ry0, -1, 31), 0, 0, 0)
    zb_e = lambda u: L.POOL_DEEP if u < L.POOL_A[1][3] else 0
    custom(MM.rockface('rockface_e', ry0 - 20, ry1 - 4, zb_e, rt + 10, [(L.CAVE_EXIT[1] + 4, L.CAVE_EXIT[3] - 4, -10, 122)], 'y', rx1, 1, 37), 0, 0, 0)
    custom(MM.rocktop(rx0, ry0, rx1, ry1, rt, 41), 0, 0, 0)
    # waterfall lip + curtain over the mouth
    A(box((L.MOUTH[0] - 16, ry0 - 72, 336), (L.MOUTH[2] + 16, ry0 - 58, 352), T('rock')))
    wx = (L.MOUTH[0] + L.MOUTH[2]) / 2
    A(sprite(wx, ry0 - 66, L.WATER, 336, 'waterfall', 176))
    A(sprite(wx, ry0 - 74, L.WATER, 300, 'waterfall', 120))
    speaker(wx, ry0 - 60, 120, 'ambient/water_falling', volume=0.8)
    # inside the cave: secret, Pad Power, ammo, a glow
    cx = (L.CAVE[0] + L.CAVE[2]) / 2; cy = (L.CAVE[1] + L.CAVE[3]) / 2
    M.ent('trigger_multiple', brushes=[box((L.MOUTH[0] + 8, L.CAVE[1] + 8, 0), (L.MOUTH[2] - 8, L.CAVE[1] + 48, 96), TRIG)], target='secret_snd', wait=8)
    speaker(wx, L.CAVE[1] + 60, 60, 'misc/secret_found', loop=False, targetname='secret_snd')
    item('item_padpower', cx - 60, cy + 120, 0)
    item('ammo_imperius', cx + 100, cy - 60, 0)
    item('ammo_splasher', cx - 100, cy - 80, 0)
    item('ammo_betty', cx + 100, cy + 160, 0)
    mdl_c('pad_ducks/pad_duck.md3', cx + 90, cy + 150, 0, 0.35, 220)
    light(cx, cy, 120, 360, '0.4 0.75 1'); light(L.CAVE_EXIT[0] + 40, L.CAVE_EXIT[1] + 64, 90, 180, '0.5 0.8 1')
    speaker(cx, cy, 80, 'ambient/droplets_echoing', volume=0.6)
    M.ent('target_location', (round(cx), round(cy), 60), message='Grotto')
    # sign by the exit tunnel
    A(sign_box((L.CAVE_EXIT[2], L.CAVE_EXIT[3] + 8, 140), (L.CAVE_EXIT[2] + 4, L.CAVE_EXIT[3] + 56, 164), T('sign_grotto'), 256, 64, back=CAULK, facing='e'))
    # boulders on the deck strip and in the shallows
    custom(MM.PLACE['boulders_b'], -1900, 160, 0, angle=10)
    A(box((-1980, 100, 0), (-1830, 220, 50), WCLIP))
    KEEP_OUT.append((-1900, 160, 160))
    NOGO.append((L.CAVE_EXIT[2], L.CAVE_EXIT[1] - 32, L.CAVE_EXIT[2] + 120, L.CAVE_EXIT[3] + 32))


# =================================================================================================== lazy river + tree island
RIV_EXITS = [(25, 'out'), (125, 'out'), (300, 'out'), (330, 'in'), (215, 'in')]
BRIDGES = [90, 165]


def river_island():
    tile = box((RIV_TILE[0], RIV_TILE[1], L.SLAB_BOT), (RIV_TILE[2], RIV_TILE[3], 0), CAULK)
    _TILES.append(RIV_TILE)
    n = 32
    cut = [ring_seg(CX, CY, k * 360 / n, (k + 1) * 360 / n, L.R_ISL, L.R_RIV, L.RIV_FLOOR, 32, CAULK) for k in range(n)]
    for b in carve(tile, cut):
        pool_faces(b, wall=T('rock'), floor=T('pool_tile'), top=T('deck'))
        # island top: stamped deck too; the ring right at the river edge gets coping
        A(b)
    # exit stairs (3 steps of 16u from the river floor) on both banks
    stairs_b = []
    for (a, side) in RIV_EXITS:
        for k in range(3):
            if side == 'out':
                u0, u1 = L.R_RIV - 6 - 32 * (k + 1), L.R_RIV - 6 - 32 * k
            else:
                u0, u1 = L.R_ISL + 6 + 32 * k, L.R_ISL + 6 + 32 * (k + 1)
            zt = L.RIV_FLOOR + 16 * (3 - k)
            b = rbox(CX, CY, a, u0, u1, -64, 64, L.RIV_FLOOR, zt, {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': CAULK})
            stairs_b.append(b); A(b)
    # water: wedges carved around the stairs
    for k in range(n):
        w = ring_seg(CX, CY, k * 360 / n, (k + 1) * 360 / n, L.R_ISL, L.R_RIV, L.RIV_FLOOR, L.WATER, CAULK)
        near = [s for s in stairs_b]
        for piece in carve(w, near):
            A(water_faces(piece))
    # bridges: ramps on both banks + a deck over the water, rope rails (MD3) on weapon-clip rails
    for a in BRIDGES:
        hw = 72
        r0, r1 = L.R_ISL - 144, L.R_RIV + 144
        A(rbox(CX, CY, a, r0, L.R_ISL, -hw, hw, 0, 0, {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}, z1e=64))
        A(rbox(CX, CY, a, L.R_ISL, L.R_RIV, -hw, hw, 48, 64, {'top': T('planks'), 'side': T('planks_dark'), 'bot': T('planks_dark')}))
        A(rbox(CX, CY, a, L.R_RIV, r1, -hw, hw, 0, 64, {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}, z1e=0))
        for v in (-hw + 6, hw - 6):
            pts = []
            for (r, z) in ((r0 + 8, 0), (L.R_ISL, 64), (L.R_RIV, 64), (r1 - 8, 0)):
                pts.append((*ang_pt(CX, CY, r, a), z))
            # shift sideways
            ax, ay = -math.sin(math.radians(a)), math.cos(math.radians(a))
            pts = [(x + ax * v, y + ay * v, z) for (x, y, z) in pts]
            nm = f'bridge_rail_{a}_{"l" if v < 0 else "r"}'
            path, sc, zo, o = MM.gen_ropefence(nm, pts)
            custom((path, sc, zo), o[0], o[1], o[2])
            # weapclip rail (low wall following the bridge)
            A(rbox(CX, CY, a, L.R_ISL, L.R_RIV, v - 4, v + 4, 64, 104, WCLIP))
            A(rbox(CX, CY, a, r0 + 8, L.R_ISL, v - 4, v + 4, 64 * 8 / 144, 40 + 64 * 8 / 144, WCLIP, z0e=64, z1e=104))
            A(rbox(CX, CY, a, L.R_RIV, r1 - 8, v - 4, v + 4, 64, 104, WCLIP, z0e=64 * 8 / 144, z1e=40 + 64 * 8 / 144))
        bx, by = ang_pt(CX, CY, (r0 + r1) / 2, a)
        NOGO.append((bx - 240, by - 240, bx + 240, by + 240))
        KEEP_OUT.append((bx, by, 260))
    # tree: trunk + needles, trunk collision
    custom(MM.PLACE['pine'], CX, CY, 0)
    A(cyl(CX, CY, L.TRUNK_COL, 0, L.TRUNK_COL_Z, WCLIP, 16))
    # spiral stair round the trunk
    r0, r1 = L.STAIR_R
    for k in range(L.STAIR_N):
        a0 = L.STAIR_A0 + k * L.STAIR_DA; a1 = a0 + L.STAIR_DA
        zt = 16 * (k + 1)
        am = (a0 + a1) / 2
        A(ring_seg(CX, CY, a0, a1, r0, r1, 0, zt, ring_tex(am, inner=T('bark'), outer=T('planks_dark'), top=T('planks'), side=T('planks_dark'))))
    # Eagle's Nest deck (ring with a hatch over the last steps) + railing
    nz = L.NEST_Z
    h0, h1 = L.NEST_HATCH
    nseg = 30
    for k in range(nseg):
        a0, a1 = k * 360 / nseg, (k + 1) * 360 / nseg
        am = (a0 + a1) / 2
        inh = (h0 <= am % 360 <= h1) or (h0 <= am + 360 <= h1)
        tex = ring_tex(am, inner=T('planks_dark'), outer=T('planks_dark'), top=T('planks'), bot=T('planks_dark'), side=T('planks_dark'))
        if inh:
            A(ring_seg(CX, CY, a0, a1, L.NEST_HATCH_R, L.NEST_R[1], nz - 16, nz, tex))
        else:
            A(ring_seg(CX, CY, a0, a1, L.NEST_R[0], L.NEST_R[1], nz - 16, nz, tex))
        A(ring_seg(CX, CY, a0, a1, L.NEST_R[1] - 10, L.NEST_R[1], nz, nz + 40, WCLIP))
    pts = [(*ang_pt(CX, CY, L.NEST_R[1] - 5, a), nz) for a in np.linspace(0, 360, 31)]
    path, sc, zo, o = MM.gen_railing('nest_rail', pts, h=40, tex='glulam')
    custom((path, sc, zo), o[0], o[1], o[2])
    # crow's nest (round platform on the trunk)
    cz = L.CROW_Z
    for k in range(16):
        a0, a1 = k * 22.5, (k + 1) * 22.5
        A(ring_seg(CX, CY, a0, a1, L.CROW_R[0], L.CROW_R[1], cz - 16, cz, ring_tex((a0 + a1) / 2, inner=T('planks_dark'), outer=T('planks_dark'), top=T('planks'), bot=T('planks_dark'), side=T('planks_dark'))))
    # pad: nest deck -> crow's nest
    px, py = ang_pt(CX, CY, 300, MM.PAD_AZ)
    lx, ly = ang_pt(CX, CY, 120, MM.PAD_AZ)
    jumppad(px, py, nz, (lx, ly, cz), cz + 150, 'crow')
    # sign on the deck rail
    # contents
    weapon('imperius', *ang_pt(CX, CY, 118, MM.PAD_AZ + 180), cz, 'purple')
    item('ammo_imperius', *ang_pt(CX, CY, 300, 200), nz)
    item('item_armor_padshield', *ang_pt(CX, CY, 300, 20), nz)
    item('ammo_bubbleg', *ang_pt(CX, CY, 300, 250), nz)
    weapon('bubbleg', *ang_pt(CX, CY, 300, 60), 0, 'blue')
    item('ammo_balloony', *ang_pt(CX, CY, 340, 280), 0)
    item('item_speedy', *ang_pt(CX, CY, 592, 0), L.RIV_FLOOR)
    item('ammo_bubbleg', *ang_pt(CX, CY, 592, 200), L.RIV_FLOOR)
    # river floats + ducks
    rng = np.random.default_rng(5)
    for k in range(12):
        a = k * 30 + rng.uniform(-6, 6)
        if any(min(abs((a - b + 180) % 360 - 180), 360) < 22 for b in BRIDGES): continue
        if any(min(abs((a - e + 180) % 360 - 180), 360) < 14 for (e, _) in RIV_EXITS): continue
        r = rng.uniform(530, 650)
        nm = ['tube1y', 'tube1p', 'tube1k', 'tube2t'][k % 4]
        custom(MM.PLACE[nm], *ang_pt(CX, CY, r, a), L.WATER, angle=int(rng.uniform(0, 360)))
    for a in (65, 245, 170):
        mdl_c('pad_ducks/pad_duck.md3', *ang_pt(CX, CY, 600, a), L.WATER, 0.18, int(a + 90))
    # island planting: ferns + boulders round the base, lights
    for (a, r) in ((50, 360), (198, 370), (300, 380)):
        x, y = ang_pt(CX, CY, r, a)
        mdl_c('pad_ddmix/plants/fern.md3', x, y, 0, 0.22, a)
    custom(MM.PLACE['boulders_a'], *ang_pt(CX, CY, 330, 140), 0, angle=140)
    A(cyl(*[round(v) for v in ang_pt(CX, CY, 330, 140)], 56, 0, 40, WCLIP, 8))
    for a in (-40, 30):
        x, y = ang_pt(CX, CY, 385, a)
        A(cyl(round(x), round(y), 56, 0, 40, {'top': T('rock'), 'side': T('fieldstone'), 'bot': CAULK}, 12))
        custom(MM.PLACE['small_pine'], x, y, 40, angle=int(a * 7), mul=0.42 / 0.65); A(cyl(round(x), round(y), 18, 40, 240, WCLIP, 8))
    for (a, r) in ((-12, 600), (275, 590)):
        x, y = ang_pt(CX, CY, r, a)
        solid_mdl('pad_ducks/pad_duck.md3', x, y, L.RIV_FLOOR, 0.6, int(a + 90))
    for a in (5, 250):
        x, y = ang_pt(CX, CY, 340, a)
        custom(MM.PLACE['tube_stack'], x, y, 0, angle=a)
        A(cyl(round(x), round(y), 32, 0, 88, WCLIP, 12))
    for a in (0, 120, 240):
        x, y = ang_pt(CX, CY, 260, a); light(x, y, 300, 420, '1 0.85 0.65')
    light(CX, CY, nz + 120, 700, '1 0.85 0.65'); light(CX, CY, cz + 100, 500, '1 0.85 0.7')
    for a in (45, 225):
        x, y = ang_pt(CX, CY, 590, a); light(x, y, 40, 260, '0.5 0.85 1')
    speaker(*ang_pt(CX, CY, 590, 0), 0, 'ambient/water_flowing', volume=0.45)
    speaker(*ang_pt(CX, CY, 590, 180), 0, 'ambient/water_flowing', volume=0.45)
    timer_sound(CX, CY, 1100, 'animal/bird_eagle', 'eagle', 50, 30, volume=0.5)
    M.ent('target_location', (round(CX), round(CY), nz + 40), message="Eagle's Nest")
    # deck sign (river)
    sx, sy = ang_pt(CX, CY, L.R_RIV + 220, 40)


# =================================================================================================== Timber Peak tower + slides
def tower():
    x0, y0, x1, y1 = L.TW
    B = L.TW_BAND; Z = L.TW_Z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    NOGO.append((x0 - B - 40, y0 - B - 40, x1 + B + 40, y1 + B + 40))
    KEEP_OUT.append((cx, cy, 460))
    # log core (MD3) + weapon-clip walls, door south
    dxa, dxb = cx - 48, cx + 48
    crib = MM.crib('tower_core', x1 - x0, y1 - y0, Z - 16, openings=[('s', -48, 48, 0, 112)])
    custom(crib, cx, cy, 0)
    t = 12
    A(box((x0 - t, y0 - t, 0), (dxa, y0 + t, Z - 16), WCLIP)); A(box((dxb, y0 - t, 0), (x1 + t, y0 + t, Z - 16), WCLIP))
    A(box((dxa, y0 - t, 112), (dxb, y0 + t, Z - 16), WCLIP))
    A(box((x0 - t, y1 - t, 0), (x1 + t, y1 + t, Z - 16), WCLIP))
    A(box((x0 - t, y0 + t, 0), (x0 + t, y1 - t, Z - 16), WCLIP)); A(box((x1 - t, y0 + t, 0), (x1 + t, y1 - t, Z - 16), WCLIP))
    # room ceiling + lining
    A(box((x0 + t, y0 + t, 176), (x1 - t, y1 - t, 192), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': CAULK}))
    item('ammo_betty', cx - 100, cy + 80, 0)
    item('item_armor_shard', cx + 100, cy + 80, 0)
    item('ammo_nipper', cx, cy + 120, 0)
    light(cx, cy, 120, 300, '1 0.8 0.55')
    mdl_c('pad_ddmix/padshop/cardboard_standup.md3', cx + 110, cy - 110, 0, 0.3, 135)
    # platform: core + west band + south band
    ptex = {'top': T('planks'), 'side': T('glulam'), 'bot': T('planks_dark')}
    A(box((x0 - t, y0 - t, Z - 16), (x1 + t, y1 + t, Z), ptex))
    A(box((x0 - B, y0 - B, Z - 16), (x0 - t, y1 + t, Z), ptex))
    A(box((x0 - t, y0 - B, Z - 16), (x1 + t, y0 - t, Z), ptex))
    # posts under the bands (timber MD3 + clip)
    pst = MM.post('post464', Z - 16, 28)
    for (px, py) in ((x0 - B + 16, y0 - B + 16), (x0 - B + 16, y1 - 16), (x1 - 16, y0 - B + 16), (x0 - B + 16, (y0 + y1) / 2 - 120)):
        custom(pst, px, py, 0)
        A(box((px - 12, py - 12, 0), (px + 12, py + 12, Z - 16), WCLIP))
    # stairs: F1 east band rising north (15 steps), landing NE, F2 north band rising west (15 steps)
    st = {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}
    for k in range(15):
        A(box((x1 + t, y0 - B + 32 * k, 0), (x1 + B + t, y0 - B + 32 * (k + 1), 16 * (k + 1)), st))
    A(box((x1 + t, y1, 0), (x1 + B + t, y1 + B + t, 240), st))
    for k in range(15):
        xa = x1 + t - 32 * (k + 1); xb = x1 + t - 32 * k
        A(box((xa, y1 + t, 0), (xb, y1 + B + t, 240 + 16 * (k + 1)), st))
    # railings: platform edges (gaps for slide launches and the stair arrival), stairs outer edges
    rails = [((x0 - B, y0 - B + 140), (x0 - B, 990)), ((x0 - B, 1090), (x0 - B, y1 + t - 4)),
             ((x0 - B + 4, y0 - B), (1430, y0 - B)), ((x1 + t, y0 - B), (x1 + t, y1 + t)),
             ((x0, y1 + t), (x1 + t - 4, y1 + t))]
    for i, (a, b) in enumerate(rails):
        pts = [(a[0], a[1], Z), (b[0], b[1], Z)]
        path, sc, zo, o = MM.gen_railing(f'tw_rail{i}', pts)
        custom((path, sc, zo), o[0], o[1], o[2])
        ax, ay = a; bx, by = b
        if ax == bx: A(box((ax - 3, min(ay, by), Z), (ax + 3, max(ay, by), Z + 40), WCLIP))
        else: A(box((min(ax, bx), ay - 3, Z), (max(ax, bx), ay + 3, Z + 40), WCLIP))
    # stair rails (sloped)
    xr, yr = x1 + B + t + 3, y1 + B + t + 3
    pts = [(xr, y0 - B, 0), (xr, y1, 240), (xr, yr, 240), (x1 + t, yr, 240), (x1 + t - 480, yr, Z)]
    path, sc, zo, o = MM.gen_railing('tw_stair_rail', pts)
    custom((path, sc, zo), o[0], o[1], o[2])
    A(hull([(x, y, z) for x in (xr - 3, xr + 3) for (y, zz) in ((y0 - B, 0), (y1, 240)) for z in (zz + 1, zz + 40)], WCLIP))
    A(box((xr - 3, y1, 241), (xr + 3, yr + 3, 280), WCLIP))
    A(box((x1 + t, yr - 3, 241), (xr - 3, yr + 3, 280), WCLIP))
    A(hull([(x, y, z) for (x, zz) in ((x1 + t, 240), (x1 + t - 480, Z)) for y in (yr - 3, yr + 3) for z in (zz + 1, zz + 40)], WCLIP))
    # roof over the core on four posts + clip slabs, pad from the platform to the roof
    e, rr = L.TW_ROOF_EAVE, L.TW_ROOF_RIDGE
    W2 = (y1 - y0) / 2
    g = MM.gable('gable_tower', x1 - x0, y1 - y0, rr - e, over=8, roof='shingles')
    custom(g, cx, cy, e)
    pr = MM.post('post128', e - Z, 24)
    for (px, py) in ((x0 + 12, y0 + 12), (x1 - 12, y0 + 12), (x0 + 12, y1 - 12), (x1 - 12, y1 - 12)):
        custom(pr, px, py, Z)
        A(box((px - 12, py - 12, Z), (px + 12, py + 12, e - 10), WCLIP))
    s = (rr - e) / W2
    for sg in (-1, 1):
        yo = cy + sg * (W2 + 8); zo_ = e - 8 * s
        A(hull([(x, y, z) for x in (x0 - 8, x1 + 8) for (y, zt) in ((cy, rr), (yo, zo_)) for z in (zt - 10, zt)], WCLIP))
    jumppad(x0 + 60, y0 - 56, Z, (x0 + 120, cy - 30, L.TW_ROOF_RIDGE - 12), L.TW_ROOF_RIDGE + 130, 'tower_roof')
    # signs
    A(sign_box((cx - 128, y0 - 26, 128), (cx + 128, y0 - 22, 192), T('sign_peak'), 512, 128, back=CAULK, facing='s'))
    # contents
    weapon('pumper', cx + 40, cy, Z, 'green')
    item('ammo_pumper', x0 - 48, y0 + 40, Z)
    item('holdable_floater', cx + 120, cy - 70, e + (rr - e) * (1 - 70 / W2) + 8)
    item('ammo_imperius', cx - 120, cy + 70, e + (rr - e) * (1 - 70 / W2) + 8)
    light(cx, cy, Z + 100, 500, '1 0.82 0.6'); light(x1 + 60, cy, 300, 300, '1 0.82 0.6')
    speaker(cx, cy, Z + 40, 'ambient/water_flowing', volume=0.3)
    M.ent('target_location', (round(cx), round(cy), Z + 40), message='Timber Peak')


def slide_brushes(pts, hw, wall_h, roof=None, floor_t=16, wall_t=8):
    """slick floor + weapon-clip walls (+ roof) along a slide centre line [(x, y, z_floor)] (mitred segments)"""
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


def supports(sup, floor_t=16, bot=0.0, half=8):
    for (x, y, z) in sup:
        ztop = z - floor_t - 10
        if ztop < 40: continue
        A(box((round(x) - half, round(y) - half, 0), (round(x) + half, round(y) + half, round(ztop)), WCLIP))


def slides():
    yp = L.yellow_path()
    ok = lambda x, y: on_deck(x, y, 40)
    ys = MM.supports_for(yp, ok, every=4, zmin=110)
    custom(MM.tube_yellow(yp, ys), 0, 0, 0)
    slide_brushes(yp[1:], 40, 90, roof=True)
    supports(ys)
    for (x, y, z) in ys: KEEP_OUT.append((x, y, 60)); NOGO.append((x - 50, y - 50, x + 50, y + 50))
    for (x, y, z) in yp[1:]:
        if z > 40: KEEP_OUT.append((x, y, 90))
    gp = L.green_path()
    gs = MM.supports_for(gp, ok, every=3, zmin=90)
    custom(MM.flume('flume_green', gp, gs, 56, 48, MM.S('slide_green', 'lms', v=0.22), MM.S('slide_green_in', 'lm'),
                    MM.S('metal_white', 'lms', v=0.15, tag='g')), 0, 0, 0)
    slide_brushes(gp[1:], 46, 48)
    supports(gs)
    for (x, y, z) in gs: KEEP_OUT.append((x, y, 60)); NOGO.append((x - 50, y - 50, x + 50, y + 50))
    for (x, y, z) in gp[1:]:
        KEEP_OUT.append((x, y, 90)); NOGO.append((x - 70, y - 70, x + 70, y + 70))
    speaker(yp[-1][0], yp[-1][1], 40, 'ambient/water_shower', volume=0.4)
    speaker(gp[-1][0], gp[-1][1], 40, 'ambient/water_shower', volume=0.4)


# =================================================================================================== plunge pool
def plunge_pool():
    x0, y0, x1, y1 = L.POOL_P
    fz = L.POOL_P_FLOOR
    tile = box((POOL_TILE_P[0], POOL_TILE_P[1], L.SLAB_BOT), (POOL_TILE_P[2], POOL_TILE_P[3], 0), CAULK)
    _TILES.append(POOL_TILE_P)
    for b in carve(tile, [box((x0, y0, fz), (x1, y1, 32), CAULK)]):
        A(pool_faces(b))
    # steps down from the south edge (tops -16 ... -160), 40 deep
    steps = []
    for k in range(10):
        b = box((x0, y0 + 40 * k, fz), (x1, y0 + 40 * (k + 1), -16 - 16 * k), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': CAULK})
        steps.append(b); A(b)
    for b in carve(box((x0, y0, fz), (x1, y1, L.WATER), CAULK), steps):
        A(water_faces(b))
    # lane line on the deep floor + ladder
    custom(MM.ladder(176), x1, 200, 0, angle=0)
    item('holdable_killerducks', (x0 + x1) / 2, 260, fz)
    item('ammo_splasher', x0 + 120, 320, fz)
    item('ammo_pumper', x1 + 100, -380, 0)
    item('item_jumper', x0 - 100, 300, 0)
    for (x, y) in ((1400, 200), (1650, 0)):
        light(x, y, -80, 260, '0.5 0.85 1')
    light((x0 + x1) / 2, (y0 + y1) / 2, 400, 900, '1 0.85 0.7')
    speaker((x0 + x1) / 2, (y0 + y1) / 2, 0, 'ambient/water_bubbling', volume=0.4)
    custom(MM.PLACE['tube1y'], 1350, 100, L.WATER, angle=30); custom(MM.PLACE['tube2t'], 1560, 330, L.WATER, angle=120)
    custom(MM.PLACE['lifeguard'], x0 - 70, y0 - 60, 0, angle=45)
    A(box((x0 - 90, y0 - 80, 0), (x0 - 50, y0 - 40, 120), WCLIP))
    KEEP_OUT.append((x0 - 70, y0 - 60, 70))


# =================================================================================================== snack bar
def snack_bar():
    x0, y0, x1, y1 = L.SB
    H = L.SB_H; t = 16
    NOGO.append((x0 - 140, L.SB_PORCH[1] - 40, x1 + 40, y1))
    KEEP_OUT.append((0, 1400, 520))
    # south facade with the counter opening (56..176) and the sign above
    A(box((x0, y0, 0), (-320, y0 + t, H - 16), {'side': T('logwall'), 'n': T('stucco_cream'), 'top': CAULK, 'bot': CAULK}))
    A(box((320, y0, 0), (x1, y0 + t, H - 16), {'side': T('logwall'), 'n': T('stucco_cream'), 'top': CAULK, 'bot': CAULK}))
    A(box((-320, y0, 0), (320, y0 + t, 56), {'side': T('logwall'), 'top': T('steel'), 'n': T('stucco_cream'), 'bot': CAULK}))
    A(box((-320, y0, 176), (320, y0 + t, H - 16), {'side': T('logwall'), 'n': T('stucco_cream'), 'bot': T('glulam'), 'top': CAULK}))
    A(sign_box((-112, y0 - 4, 184), (112, y0, 240), T('sign_grill'), 512, 128, back=CAULK, facing='s'))
    # counter top inside, back counter, side walls (door east)
    A(box((-320, y0 + t, 0), (320, y0 + 64, 56), {'top': T('steel'), 'side': T('wainscot'), 'bot': CAULK}))
    A(box((x0, y0 + t, 0), (x0 + t, y1, H - 16), {'side': CAULK, 'e': T('stucco_cream'), 'w': T('logwall'), 'top': CAULK, 'bot': CAULK}))
    A(box((x1 - t, y0 + t, 0), (x1, 1440, H - 16), {'side': CAULK, 'w': T('stucco_cream'), 'e': T('logwall'), 'top': CAULK, 'bot': CAULK}))
    A(box((x1 - t, 1536, 0), (x1, y1, H - 16), {'side': CAULK, 'w': T('stucco_cream'), 'e': T('logwall'), 'top': CAULK, 'bot': CAULK}))
    A(box((x1 - t, 1440, 120), (x1, 1536, H - 16), {'side': CAULK, 'w': T('stucco_cream'), 'e': T('logwall'), 'bot': T('glulam'), 'top': CAULK}))
    A(box((x0 + t, y1 - 64, 0), (x1 - t, y1, 48), {'top': T('steel'), 'side': T('steel'), 'bot': CAULK}))           # back counter / grill
    A(box((x0 + t, y1 - 72, 48), (-180, y1, 200), {'side': T('steel'), 'top': CAULK, 'bot': CAULK}))                  # fridge
    A(sign_box((-128, y1 - 68, 96), (128, y1 - 64, 224), T('menu'), 512, 256, back=CAULK, facing='s'))
    # roof deck
    A(box((x0, y0, H - 16), (x1, y1, H), {'top': T('planks'), 'side': T('glulam'), 'bot': T('ceiling')}))
    # porch gable roof (ridge along y at x 0) on posts + clip slabs
    px0, py0, px1, py1 = L.SB_PORCH
    e = L.SB_PORCH_EAVE; rise = H - e
    g = MM.gable('gable_porch', py1 - py0, px1 - px0, rise, over=0, roof='roof_red')
    custom(g, 0, (py0 + py1) / 2, e, angle=90)
    s = rise / ((px1 - px0) / 2)
    for sg in (-1, 1):
        xo = sg * (px1 - px0) / 2
        A(hull([(x, y, z) for y in (py0, py1 - 8) for (x, zt) in ((0, H), (xo, e)) for z in (zt - 10, zt)], WCLIP))
    pst = MM.post('post_porch', e - 10, 24)
    for x in (px0 + 14, px1 - 14):
        custom(pst, x, py0 + 14, 0)
        A(box((x - 12, py0 + 2, 0), (x + 12, py0 + 26, e - 10), WCLIP))
    # stairs to the roof deck on the west side
    for k in range(16):
        A(box((x0 - 96, py0 + 32 * k, 0), (x0, py0 + 32 * (k + 1), 16 * (k + 1)), {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}))
    path, sc, zo, o = MM.gen_railing('sb_stair_rail', [(x0 - 99, py0, 0), (x0 - 99, y1 - 4, H)], tex='glulam')
    custom((path, sc, zo), o[0], o[1], o[2])
    A(hull([(x, y, z) for x in (x0 - 102, x0 - 96) for (y, zz) in ((py0, 0), (y1, H)) for z in (zz + 1, zz + 40)], WCLIP))
    # door bell when someone steps up to the counter
    M.ent('trigger_multiple', brushes=[box((-200, y0 - 80, 0), (200, y0 - 20, 64), TRIG)], target='order_up', wait=12)
    speaker(0, y0 + 80, 120, 'machine/dingdong', loop=False, targetname='order_up', volume=0.7)
    speaker(-200, y1 - 100, 100, 'machine/coffee_maker', volume=0.3)
    speaker(-300, y1 - 100, 100, 'machine/freezer', volume=0.25)
    # contents
    weapon('boaster', 120, 1560, 0, 'orange')
    item('ammo_bubbleg', -200, 1520, 0)
    item('ammo_boaster', 200, 1500, H)
    item('item_visionless', -260, 1560, H)
    item('ammo_pumper', -300, 1260, 0)
    M.ent('station_health', (300, 1220, 0), angle=270)
    KEEP_OUT.append((300, 1220, 90))
    mdl_c('pad_condiments/pad_ketchup.md3', -240, y0 + 40, 56, 0.25, 0); mdl_c('pad_condiments/pad_mustard.md3', -210, y0 + 40, 56, 0.25, 0)
    mdl_c('padtv/padtv2.md3', 260, y1 - 40, 48, 0.22, 270)
    light(0, 1500, 200, 500, '1 0.85 0.6'); light(0, 1250, 150, 350, '1 0.8 0.55')
    M.ent('target_location', (0, 1500, 60), message='Moose Lodge Grill')
    # picnic tables in front (tables with chairs)
    for (x, y) in ((-260, 960), (260, 960)):
        custom(MM.PLACE['table_set'], x, y, 0, angle=15)
        A(cyl(x, y, 36, 0, 30, WCLIP, 12))
        KEEP_OUT.append((x, y, 110))


# =================================================================================================== Tiny Timbers
KID_SLIDES = {}


def tiny_timbers():
    x0, y0, x1, y1 = L.TT_BASE
    D = L.TT_DECK
    NOGO.append((x0 - 60, y0 - 360, x1 + 60, y1 + 60))
    KEEP_OUT.append(((x0 + x1) / 2, (y0 + y1) / 2, 360))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # base: log crib with a crawl tunnel along x
    ty0, ty1 = cy - 40, cy + 40
    crib = MM.crib('tt_base', x1 - x0, y1 - y0, D - 16, openings=[('e', -40, 40, 0, 112), ('w', -40, 40, 0, 112)])
    custom(crib, cx, cy, 0)
    t = 12
    A(box((x0 - t, y0 - t, 0), (x1 + t, y0 + t, D - 16), WCLIP)); A(box((x0 - t, y1 - t, 0), (x1 + t, y1 + t, D - 16), WCLIP))
    for xx in (x0, x1):
        A(box((xx - t, y0 + t, 0), (xx + t, ty0, D - 16), WCLIP)); A(box((xx - t, ty1, 0), (xx + t, y1 - t, D - 16), WCLIP))
        A(box((xx - t, ty0, 112), (xx + t, ty1, D - 16), WCLIP))
    A(box((x0 + t, y0 + t, 112), (x1 - t, ty0, 128), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': CAULK}))
    A(box((x0 + t, ty1, 112), (x1 - t, y1 - t, 128), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': CAULK}))
    A(box((x0 + t, ty0, 112), (x1 - t, ty1, 128), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': CAULK}))
    # deck
    A(box((x0 - t, y0 - t, D - 16), (x1 + t, y1 + t, D), {'top': T('planks'), 'side': T('glulam'), 'bot': T('planks_dark')}))
    # front stairs (south)
    sx0, sx1 = x1 - 128, x1
    for k in range(10):
        A(box((sx0, y0 - t - 32 * (10 - k), 0), (sx1, y0 - t - 32 * (9 - k), 16 * (k + 1)), {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}))
    for xx in (sx0 - 3, sx1 + 3):
        path, sc, zo, o = MM.gen_railing(f'tt_stair_rail{int(xx)}', [(xx, y0 - t - 320, 0), (xx, y0 - t, D)], tex='metal_white')
        custom((path, sc, zo), o[0], o[1], o[2])
        A(hull([(x, y, z) for x in (xx - 3, xx + 3) for (y, zz) in ((y0 - t - 320, 0), (y0 - t, D)) for z in (zz + 1, zz + 40)], WCLIP))
    # tower + top platform
    tx0, ty0_, tx1, ty1_ = L.TT_TOWER
    tcx, tcy = (tx0 + tx1) / 2, (ty0_ + ty1_) / 2
    tc = MM.crib('tt_tower', tx1 - tx0, ty1_ - ty0_, L.TT_TOP - 16 - D)
    custom(tc, tcx, tcy, D)
    A(box((tx0 - t, ty0_ - t, D), (tx1 + t, ty1_ + t, L.TT_TOP - 16), WCLIP))
    pt = (tcx - 88, tcy - 64, tcx + 88, tcy + 88)
    A(box((pt[0], pt[1], L.TT_TOP - 16), (pt[2], pt[3], L.TT_TOP), {'top': T('planks'), 'side': T('glulam'), 'bot': T('planks_dark')}))
    # cabin roofs west + east of the tower (ridge = top platform height) on posts
    e = L.TT_TOP - 64
    for sg in (-1, 1):
        if sg < 0: rx0, rx1 = x0 + 8, pt[0]
        else: rx0, rx1 = pt[2], x1 - 8
        rcx = (rx0 + rx1) / 2
        g = MM.gable(f'gable_tt{"w" if sg < 0 else "e"}', rx1 - rx0 - 16, (y1 - y0) - 64, 64, over=8, roof='roof_red')
        custom(g, rcx, cy, e)
        hwr = ((y1 - y0) - 64) / 2
        s = 64 / hwr
        for sy in (-1, 1):
            yo = cy + sy * (hwr + 8)
            A(hull([(x, y, z) for x in (rx0, rx1) for (y, zt) in ((cy, L.TT_TOP), (yo, e - 8 * s)) for z in (zt - 10, zt)], WCLIP))
        pp = MM.post('post_tt', e - D - 10, 20)
        for (px, py) in ((rx0 + 12 if sg < 0 else rx1 - 12, cy - hwr + 10), (rx0 + 12 if sg < 0 else rx1 - 12, cy + hwr - 10)):
            custom(pp, px, py, D)
            A(box((px - 10, py - 10, D), (px + 10, py + 10, e - 10), WCLIP))
    # bucket on the top platform + its periodic dump
    custom(MM.PLACE['bucket'], tcx - 30, tcy, L.TT_TOP)
    A(box((tcx - 34, tcy - 64, L.TT_TOP), (tcx - 26, tcy - 56, L.TT_TOP + 220), WCLIP))
    A(box((tcx - 34, tcy + 56, L.TT_TOP), (tcx - 26, tcy + 64, L.TT_TOP + 220), WCLIP))
    A(sprite(tcx + 20, tcy, L.TT_TOP, L.TT_TOP + 196, 'bucket_dump', 80, 90))
    timer_sound(tcx, tcy, L.TT_TOP + 220, 'ambient/water_drain', 'bucket', 30, 0, volume=0.8)
    # pad from the deck (south strip, between the roofs) to the top platform
    jumppad(tcx, y0 + 40, D, (tcx + 10, tcy - 10, L.TT_TOP), L.TT_TOP + 130, 'tt_top')
    # railings round the deck (gaps: stairs, slides)
    rails = [((x0, y0), (sx0, y0)), ((x1, y0), (x1, cy - 56)), ((x1, cy + 56), (x1, y1)),
             ((x0, y1), (cx - 56, y1)), ((cx + 56, y1), (x1, y1)), ((x0, y0), (x0, cy - 56)), ((x0, cy + 56), (x0, y1))]
    for i, (a, b) in enumerate(rails):
        path, sc, zo, o = MM.gen_railing(f'tt_rail{i}', [(a[0], a[1], D), (b[0], b[1], D)], tex='metal_white')
        custom((path, sc, zo), o[0], o[1], o[2])
        if a[0] == b[0]:
            xx = a[0]; A(box((xx - 3, min(a[1], b[1]) + 4, D), (xx + 3, max(a[1], b[1]) - 4, D + 40), WCLIP))
        else:
            yy = a[1]; A(box((min(a[0], b[0]) + 4, yy - 3, D), (max(a[0], b[0]) - 4, yy + 3, D + 40), WCLIP))
    # kids' slides
    blue = [(x1 - 20, cy + 0.0, D)] + L._with_z(L._bez((x1 + t + 6, cy), (x1 + 260, cy), (x1 + 330, cy - 120), (x1 + 330, cy - 330), 10), D, 16)
    teal = [(cx, y1 - 20, D), (cx, y1 + t + 6, D)] + [(cx, y1 + t + 6 + 300 * k / 6, D - (D - 16) * (k / 6) ** 0.9) for k in range(1, 7)] + [(cx, y1 + 380, 16)]
    KID_SLIDES['blue'] = blue
    KID_SLIDES['teal'] = teal
    for nm, pth, col in (('kid_blue', blue, 'slide_blue'), ('kid_teal', teal, 'slide_teal')):
        sup = MM.supports_for(pth, lambda x, y: in_rect(x, y, L.TT_PAD) and not in_rect(x, y, (x0, y0, x1, y1), 20), every=3, zmin=70)
        custom(MM.flume(nm, pth, sup, 36, 32, MM.S(col, 'lms', v=0.22), MM.S(col, 'lm', tag='in'), MM.S('metal_white', 'lms', v=0.15, tag='k')), 0, 0, 0)
        slide_brushes(pth[1:], 30, 34)
        supports(sup, half=6)
        for (x, y, z) in pth: KEEP_OUT.append((x, y, 70))
    # water sprays on the splash pad
    for (x, y) in ((700, -1500), (820, -800), (1560, -760), (1700, -1100), (620, -1150), (1480, -1520)):
        A(sprite(x, y, 0, 110, 'spray', 18))
        A(sprite(x, y, 0, 80, 'spray', 14, 90))
    speaker(1100, -900, 40, 'ambient/water_shower', volume=0.5)
    timer_sound(1100, -1200, 300, 'human/applause', 'cheer', 45, 25, volume=0.4)
    # sign on the tower front
    A(sign_box((tcx - 72, ty0_ - 24, D + 72), (tcx + 72, ty0_ - 20, D + 108), T('sign_tiny'), 512, 128, back=CAULK, facing='s'))
    # contents
    weapon('betty', tcx + 40, tcy + 40, L.TT_TOP, 'black')
    item('ammo_betty', cx - 120, cy, 0)
    item('holdable_boomies', cx + 140, cy, 0)
    item('ammo_boaster', x0 + 60, y1 - 60, D)
    item('ammo_pumper', x1 - 60, y0 + 60, D)
    item('ammo_nipper', 1700, -880, 0)
    for (x, y) in ((cx - 140, cy), (cx + 140, cy)): light(x, y, 80, 220, '1 0.8 0.55')
    light(cx, cy, D + 160, 500, '1 0.85 0.65'); light(tcx, tcy, L.TT_TOP + 120, 350, '1 0.85 0.65')
    M.ent('target_location', (round(cx), round(cy), D + 40), message='Tiny Timbers')
    ZONES.append((L.TT_PAD, T('splashpad')))


# =================================================================================================== lookout stump
def stump():
    cx, cy = L.ST_C
    R, RI, H = L.ST_R, L.ST_RIN, L.ST_H
    d0, d1, dh = L.ST_DOOR
    custom(MM.PLACE['stump'], cx, cy, 0)
    KEEP_OUT.append((cx, cy, R + 120)); NOGO.append((cx - R - 60, cy - R - 60, cx + R + 60, cy + R + 60))
    Rc = R - 8
    for k in range(16):
        a0, a1 = k * 22.5, (k + 1) * 22.5
        am = (a0 + a1) / 2
        door = k in (d0, d1)
        nb = k in (d0 - 1, d1 + 1)
        if door:
            A(ring_seg(cx, cy, a0, a1, RI, Rc, dh, H - 16, ring_tex(am, inner=T('rotten'), bot=T('rotten'))))
        else:
            A(ring_seg(cx, cy, a0, a1, RI, Rc, 0, H - 16, ring_tex(am, inner=T('rotten'), side=T('rotten') if nb else CAULK)))
    # top deck: ring with the hole for the pad (segments 11, 12), rim of the shell
    hole = (11, 12)
    for k in range(16):
        a0, a1 = k * 22.5, (k + 1) * 22.5
        am = (a0 + a1) / 2
        tex = ring_tex(am, top=T('planks'), bot=T('rotten'), inner=T('rotten'), side=T('rotten') if k in (10, 13) else CAULK)
        if k in hole:
            A(ring_seg(cx, cy, a0, a1, 0, 96, H - 16, H, tex))
            A(ring_seg(cx, cy, a0, a1, 216, Rc, H - 16, H, ring_tex(am, top=T('planks'), bot=T('rotten'), inner=T('rotten'))))
        else:
            A(ring_seg(cx, cy, a0, a1, 0, Rc, H - 16, H, tex))
        A(ring_seg(cx, cy, a0, a1, Rc - 10, Rc, H, H + 40, WCLIP))
    pts = [(*ang_pt(cx, cy, Rc - 5, a), H) for a in np.linspace(0, 360, 17)]
    path, sc, zo, o = MM.gen_ropefence('stump_rail', pts, h=44)
    custom((path, sc, zo), o[0], o[1], o[2])
    px, py = ang_pt(cx, cy, 96, 270)
    lx, ly = ang_pt(cx, cy, 276, 270)
    jumppad(px, py, 0, (lx, ly, H), H + 185, 'stump_up')
    # second launcher outside on the deck (south-east of the stump), over the rope rail onto the top deck
    ox, oy = ang_pt(cx, cy, Rc + 260, 310)
    lx2, ly2 = ang_pt(cx, cy, 180, 310)
    jumppad(ox, oy, 0, (lx2, ly2, H), H + 170, 'stump_out')
    NOGO.append((ox - 80, oy - 80, ox + 80, oy + 80))
    # hut on the deck (walk in from the east; steps on the south side to its roof)
    hx0, hy0, hx1, hy1 = cx - 224, cy - 16, cx - 80, cy + 128
    hcx, hcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
    hh = 96
    hc = MM.crib('hut', hx1 - hx0, hy1 - hy0, hh, openings=[('e', -32, 32, 0, 80)])
    custom(hc, hcx, hcy, H)
    t = 10
    A(box((hx0 - t, hy0 - t, H), (hx1 + t, hy0 + t, H + hh), WCLIP)); A(box((hx0 - t, hy1 - t, H), (hx1 + t, hy1 + t, H + hh), WCLIP))
    A(box((hx0 - t, hy0 + t, H), (hx0 + t, hy1 - t, H + hh), WCLIP))
    A(box((hx1 - t, hy0 + t, H), (hx1 + t, hcy - 32, H + hh), WCLIP)); A(box((hx1 - t, hcy + 32, H), (hx1 + t, hy1 - t, H + hh), WCLIP))
    A(box((hx1 - t, hcy - 32, H + 80), (hx1 + t, hcy + 32, H + hh), WCLIP))
    A(box((hx0 + t, hy0 + t, H + hh - 8), (hx1 - t, hy1 - t, H + hh), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': CAULK}))
    g = MM.gable('gable_hut', hx1 - hx0, hy1 - hy0, 40, over=0, roof='shingles')
    custom(g, hcx, hcy, H + hh)
    hw = (hy1 - hy0) / 2
    A(hull([(x, y, z) for x in (hx0 - t, hx1 + t) for (y, z) in ((hcy - hw - t, H + hh), (hcy + hw + t, H + hh), (hcy, H + hh + 40))], WCLIP))
    for k in range(6):
        xa = hx1 - 24 * (k + 1); xb = hx1 - 24 * k
        A(box((xa, hy0 - t - 32, H), (xb, hy0 - t, H + 16 * (k + 1)), {'top': T('planks'), 'side': T('planks_dark'), 'bot': CAULK}))
    # contents
    weapon('balloony', *ang_pt(cx, cy, 200, 20), H, 'green')
    item('ammo_balloony', hcx, hcy - 20, H)
    item('item_revival', hcx - 30, hcy + 40, H)
    item('ammo_imperius', hcx, hcy, H + hh + 40)
    item('ammo_bubbleg', *ang_pt(cx, cy, 160, 160), 0)
    item('ammo_boaster', *ang_pt(cx, cy, 170, 60), 0)
    light(cx, cy, 200, 380, '1 0.8 0.55'); light(cx, cy, H + 160, 500, '1 0.85 0.65')
    speaker(cx, cy, 200, 'animal/bird_owl1', volume=0.25)
    M.ent('target_location', (round(cx), round(cy), H + 40), message='Lookout Stump')


# =================================================================================================== whirlpool spa
SPA = (-560.0, -1000.0)


def spa():
    """raised rock-ringed whirlpool: wall 56 high (cover), bench inside, steps up on the east side"""
    cx, cy = SPA
    n = 24
    for k in range(n):
        a0, a1 = k * 360 / n, (k + 1) * 360 / n
        am = (a0 + a1) / 2
        A(ring_seg(cx, cy, a0, a1, 176, 208, 0, 56, ring_tex(am, inner=T('pool_band'), outer=T('fieldstone'), top=T('coping'))))
        A(ring_seg(cx, cy, a0, a1, 136, 176, 0, 24, ring_tex(am, inner=T('pool_tile'), top=T('pool_tile'))))
        A(water_faces(ring_seg(cx, cy, a0, a1, 136, 176, 24, 40, CAULK)))
        A(water_faces(ring_seg(cx, cy, a0, a1, 0, 136, 0, 40, CAULK)))
    for k in range(3):
        A(rbox(cx, cy, 0, 208 + 32 * (2 - k), 208 + 32 * (3 - k), -48, 48, 0, 16 * (k + 1), {'top': T('coping'), 'side': T('fieldstone'), 'bot': CAULK}))
    KEEP_OUT.append((cx, cy, 330)); NOGO.append((cx - 320, cy - 230, cx + 330, cy + 230))
    item('ammo_pumper', cx - 60, cy + 40, 0)
    light(cx, cy, 30, 260, '0.5 0.85 1'); light(cx, cy, 260, 420, '1 0.85 0.65')
    speaker(cx, cy, 40, 'ambient/water_bubbling', volume=0.5)
    custom(MM.PLACE['tube1k'], cx + 40, cy - 60, 40, angle=30)


def blockers():
    """tall cover on the open decks: potted pines, tube racks, giant ducks (sightline breakers)"""
    rng = np.random.default_rng(31)
    for (x, y, s) in ((-1650, -520, 0.7), (-1000, -500, 0.65), (1000, -580, 0.65), (-200, -760 - 260, 0.6), (240, -1060, 0.6),
                      (-560, 520, 0.6), (620, 860, 0.6), (-1650, 100, 0.6), (1600, 600, 0.6), (-1100, -1420, 0.65), (420, -1440, 0.6),
                      (-1450, -1510, 0.6), (-750, -1510, 0.6), (-60, -1510, 0.6), (1000, 220, 0.6), (-1000, 100, 0.6), (1900, -1450, 0.6)):
        q = near_free(x, y, 90)
        if q is None:
            print('NOTE blocker not free', x, y); continue
        x, y = q
        A(cyl(round(x), round(y), 56, 0, 40, {'top': T('rock'), 'side': T('fieldstone'), 'bot': CAULK}, 12))
        custom(MM.PLACE['small_pine'], x, y, 40, angle=int(rng.uniform(0, 360)), mul=s / 0.65); A(cyl(round(x), round(y), 18, 40, 240, WCLIP, 8))
        KEEP_OUT.append((x, y, 130))
    for (x, y) in ((-1300, -560), (720, -500), (-760, -660), (-150, 560), (1300, -620), (-1950, 1000 - 900), (0, -1560),
                   (-900, 1300), (900, 1150), (1500, -1580), (-1100, -1590), (380, -1590), (-560, 1000), (560, 700), (-1250, 1580), (1700, 1580), (1150, 450), (-1150, 450 - 600), (1000, -120), (980, 380)):
        q = near_free(x, y, 50)
        if q is None:
            print('NOTE blocker not free', x, y); continue
        x, y = q
        custom(MM.PLACE['tube_stack'], x, y, 0, angle=int(rng.uniform(0, 360)))
        A(cyl(round(x), round(y), 32, 0, 88, WCLIP, 12))
        KEEP_OUT.append((x, y, 60))
    for (x, y) in ((-1560, -1560), (-860, -1560), (-260, -1560), (1700, -1560), (1860, 160)):
        q = near_free(x, y, 70, 200)
        if q is None: print('NOTE bush not free', x, y); continue
        x, y = q
        solid_mdl('pad_ddmix/trashcan/bush.md3', x, y, 0, 0.45, 0)
        KEEP_OUT.append((x, y, 100))
    for (x, y, s, a) in ((1900, 820, 0.55, 200), (-1880, -1260, 0.5, 30), (-1250, -180, 0.5, 300), (1120, 1560, 0.5, 250), (900, -320, 0.5, 140)):
        q = near_free(x, y, 70)
        if q is None:
            print('NOTE blocker not free', x, y); continue
        x, y = q
        solid_mdl('pad_ducks/pad_duck.md3', x, y, 0, s, a)
        KEEP_OUT.append((x, y, 80))


# =================================================================================================== deck furniture, decor
def decor():
    rng = np.random.default_rng(23)
    # moose statue on a rock plinth (south)
    mx, my = -380, -1330
    A(cyl(mx, my, 150, 0, 40, {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}, 12))
    custom(MM.PLACE['moose'], mx - 30, my, 40, angle=60)
    A(box((mx - 110, my - 90, 40), (mx + 60, my + 90, 140), WCLIP))
    KEEP_OUT.append((mx, my, 220)); NOGO.append((mx - 200, my - 200, mx + 200, my + 200))
    A(sign_box((-128, -L.HY, 496), (128, -L.HY + 6, 560), T('sign_welcome'), 512, 128, back=CAULK, facing='n'))
    # seating clusters
    sets = [(-700, -380), (-640, -980), (-120, -1100), (240, -1260), (-1120, -320), (-1500, -420), (-760, 640)]
    for (x, y) in sets:
        if not free(x, y, 90): continue
        custom(MM.PLACE['table_set'], x, y, 0, angle=int(rng.uniform(0, 90)))
        A(cyl(x, y, 36, 0, 30, WCLIP, 12))
        KEEP_OUT.append((x, y, 110))
    # adirondack chairs along the river (outer deck) and by the windows
    for (x, y, a) in ((620, -760, 135), (720, -620, 150), (-860, 120, 330), (-900, -60, 0), (900, 240, 200), (980, 120, 190),
                      (-60, -940, 90), (60, -950, 100)):
        if not free(x, y, 40): continue
        nm = ['adi_wood', 'adi_green', 'adi_red'][int(rng.integers(0, 3))]
        custom(MM.PLACE[nm], x, y, 0, angle=a)
        KEEP_OUT.append((x, y, 50))
    # loungers along the south windows and east wall
    for i, x in enumerate(range(-1800, 400, 140)):
        y = -1560
        if not free(x, y, 40): continue
        custom(MM.PLACE['lounger'], x, y, 0, angle=90)
        KEEP_OUT.append((x, y, 50))
    # potted pines + ferns + bushes (catalog)
    for (x, y, s) in ((-1950, -1560, 0.75), (-1950, -700, 0.7), (-560, 1560 - 300, 0.6), (620, 1560, 0.7), (1950, -1560, 0.75),
                      (1960, 1040, 0.7), (-1240, -1560, 0.6), (1950, -600, 0.6), (-200, -560 - 180, 0.5)):
        if not free(x, y, 110): continue
        A(cyl(round(x), round(y), 56, 0, 40, {'top': T('rock'), 'side': T('fieldstone'), 'bot': CAULK}, 12))
        custom(MM.PLACE['small_pine'], x, y, 40, angle=int(rng.uniform(0, 360)), mul=s / 0.65); A(cyl(round(x), round(y), 18, 40, 240, WCLIP, 8))
        KEEP_OUT.append((x, y, 130))
    for (x, y) in ((-1560, -180), (1040, 520), (-640, 1080), (640, 1000), (300, -560 - 300)):
        if not free(x, y, 100): continue
        mdl_c('pad_ddmix/plants/fern.md3', x, y, 0, 0.28, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 100))
    for (x, y) in ((-1300, -1500), (1200, 640 + 0), (-1700, 40)):
        if not free(x, y, 100): continue
        solid_mdl('pad_ddmix/trashcan/bush.md3', x, y, 0, 0.45, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 100))
    # beach balls + rubber duck on the deck
    for (x, y, s) in ((-640, -560, 0.3), (180, -800, 0.25), (1100, -380, 0.28), (-1120, 120, 0.3)):
        if not free(x, y, 30): continue
        mdl_c('pad_ball/pad_basketball.md3', x, y, 0, s, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 30))
    # lifeguard chair by the river
    lgx, lgy = ang_pt(CX, CY, L.R_RIV + 70, 340)
    if free(lgx, lgy, 40):
        custom(MM.PLACE['lifeguard'], lgx, lgy, 0, angle=160)
        A(box((round(lgx) - 20, round(lgy) - 20, 0), (round(lgx) + 20, round(lgy) + 20, 120), WCLIP))
        KEEP_OUT.append((lgx, lgy, 60))
    # trash bins / towel stacks near seating
    for (x, y) in ((-900, -1500), (520, -560), (-1460, -60)):
        if not free(x, y, 40): continue
        mdl_c('pad_ddmix/trashcan/garbage_bag_group.md3', x, y, 0, 0.5, int(rng.uniform(0, 360)))
        KEEP_OUT.append((x, y, 40))


def items_misc():
    for (cls, x, y) in (('ammo_nipper', -1560, -1380), ('ammo_nipper', 600, 1100), ('ammo_nipper', -200, -1500),
                        ('item_armor_shard', 1000, -500), ('item_armor_shard', -400, 900), ('item_armor_shard', 1700, 1400),
                        ('ammo_balloony', 1700, 1100), ('ammo_betty', -1400, -1400),
                        ('ammo_boaster', -1000, -800), ('ammo_splasher', -820 + 30, 1550), ('ammo_pumper', 1000, 1500),
                        ('item_climber', 880, -300), ('holdable_bambam', -1700, -900), ('ammo_balloony', -380, -960)):
        q = near_free(x, y, 24, 400)
        if q is None: print('NOTE item spot not free', cls, x, y)
        else: x, y = q
        item(cls, x, y, 0)
        KEEP_OUT.append((x, y, 40))
    M.ent('station_health', (1200, -1560 + 80, 0), angle=90)
    KEEP_OUT.append((1200, -1480, 90))


def spawns():
    sp = [(-1700, -1300, 45), (-600, -1500, 90), (300, -1500, 90), (1800, -1300, 135), (1950, -200, 180), (1950, 1300, 225),
          (900, 1500, 270), (-700, 1500, 270), (-1400, 1580, 300), (-1950, -100, 0), (-1950, -1000, 0), (600, -400, 135),
          (-600, -200, 30), (-300, 920, 300), (900, 600, 225), (1050, -200, 160)]
    for (x, y, a) in sp:
        q = near_free(x, y, 40, 400)
        if q is None: print('NOTE spawn not free', x, y)
        else: x, y = q
        spawn(x, y, 0, a)
        KEEP_OUT.append((x, y, 50))


def lights_and_sound():
    speaker(0, -1600, 300, 'ambient/wind_icy', volume=0.2)
    speaker(0, 1600, 300, 'ambient/wind_icy', volume=0.15)
    timer_sound(-1900, -1600, 300, 'animal/wolf_howl1', 'wolf', 70, 40, volume=0.35)
    timer_sound(1900, 1600, 300, 'animal/bird_owl2', 'owl', 60, 30, volume=0.3)
    # warm fill under the roof
    for (x, y) in ((-1400, 0), (1400, 0), (0, 900), (0, -900), (-1400, -1100), (1400, 1100)):
        light(x, y, 700, 900, '1 0.85 0.65')


# =================================================================================================== main
def main():
    W = TX.TexWriter(OUT)
    TX.make_textures(W)
    TX.extra_textures(W)
    MM.make(OUT)
    hull_box()
    walls(); hall_timbers()
    activity_pool(); grotto(); river_island(); tower(); slides(); plunge_pool(); snack_bar(); tiny_timbers(); stump(); spa()
    ZONES.insert(0, ((L.SB[0] + 16, L.SB[1] + 16, L.SB[2] - 16, L.SB[3]), T('kitchen_tile')))
    ZONES.insert(1, ((L.TW[0] + 12, L.TW[1] + 12, L.TW[2] - 12, L.TW[3] - 12), T('planks')))
    slab()
    blockers(); decor(); items_misc(); spawns(); lights_and_sound()
    M.ent('info_player_intermission', (-1500, -1300, 420), angles='18 40 0')
    TX.make_shader(W, OUT, MM.shaders())
    TX.make_arena(OUT)
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/moosefalls/build_moose.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
