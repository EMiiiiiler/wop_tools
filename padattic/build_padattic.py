#!/usr/bin/env python3
"""Attic Express - World of Padman map generator (map 'wop_padattic'): a model railway in the attic at night.

    OUT=/path/to/out python3 build_padattic.py

Writes <OUT>/maps/wop_padattic.map, textures/padattic/*, models/padattic/* (MD3 railway + the train loop IQM),
scripts/padattic.shader and scripts/wop_padattic.arena.

Padman scale (catalog models at 1.0, ~8u per cm). x east, y north, attic floor z 0. Gabled roof: ridge along x at
z 1856 (y = 0), knee walls at y +-1792 (256 tall), gable walls at x +-2304. The map is mirror-symmetric about x = 0:
red owns the west, blue the east (every team piece is built by a function taking s = +1 for red, coordinates written
with negative x, mirrored for blue).

  train table   3328 x 2560 plywood table (top z 384, static-grass flock) on legs, a circular track (R 1000) round it
  the train     the centrepiece: steam loco, tender and three carriages (MD3 parts baked into one IQM) circling the
                track on a func_rotating (9 deg/s, ~160 u/s); ride on the roofs, or get shoved along the rails
  stations      Red Hill (west) / Blue Valley (east): halls the track runs through, platforms both sides, team lolly
                on the outer platform, outside stairs to the roof (Pumper), roof kicker up to the rafter catwalk
  mountain      papier-mache mountain at the north: the track runs through a railway cutting into a stone-portal
                tunnel; stairs up to the plateau, kickers up to the snowy peak (Imperius)
  village       town hall in the middle (neutral lolly, clock tower, stairs to the roof), two cottages per side
                (walk in, stairs up to the tiled roof), pine trees, street lamps
  pond          a duck pond sunk into the table at the south, the track crosses it on a timber trestle; ramps out
  under table   the dark under the layout: the toy crate with the Betty, two train controllers, boxes, cobwebs, spiders
  attic         floorboards, exposed rafters, a rafter catwalk (Splasher), the dormer window with a window seat
                (Boaster) and a telescope, gable windows, hanging bulbs, an old trunk per side (Balloony inside),
                stored Christmas things, a TV; staircases of crates from the floor up to the table, floor kickers
  hatch         the loft hatch drops into the closet below (Pad Power); a kicker shoots you back up through it
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import attic_textures as TX
import rail_models as RM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padattic'
T = lambda n: 'padattic/' + n
CAULK = 'common/caulk'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'; NODRAW = 'common/nodraw'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floorboards': (1, 1), 'roofboards': (1, 1), 'kneewall': (1, 1), 'gable': (1, 1), 'beam': (0.5, 0.5), 'plywood': (1, 1),
             'ply_edge': (0.25, 0.25), 'ply_under': (1.5, 1.5), 'crate': (0.75, 0.75), 'grass': (1, 1), 'ballast': (0.5, 0.5),
             'rock': (0.5, 0.5), 'rock_moss': (0.6, 0.6), 'rock_dark': (0.5, 0.5), 'snow': (1, 1), 'sand': (0.75, 0.75), 'brick_red': (0.5, 0.5),
             'timber_blue': (0.75, 0.75), 'trim_white': (0.5, 0.5), 'paving': (0.5, 0.5), 'roof_flat': (1, 1), 'tiles_red': (0.5, 0.5),
             'tiles_blue': (0.5, 0.5), 'plaster_warm': (0.75, 0.75), 'plaster_cool': (0.75, 0.75), 'stone': (0.75, 0.75),
             'trestle': (0.5, 0.5), 'cardboard': (1, 1), 'trunk': (1, 1), 'lining': (0.5, 0.5), 'wallpaper': (1, 1), 'carpet': (1, 1),
             'wicker': (0.5, 0.5), 'metal': (0.5, 0.5), 'water': (1, 1), 'sky': (4, 4), 'glass': (2, 2)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '14', '_color': '0.8 0.85 1', 'gridsize': '96 96 96', '_blocksize': '0'})
A = M.add

# ---------------------------------------------------------------------------------------------------- layout
AX, AY, KW, RZ = 2304, 1792, 256, 1856   # attic interior half x, knee wall inner face, knee wall height, ridge
RT = 48                                   # roof slab thickness (vertical)
TX0, TY0, TZB, TZ = 1664, 1280, 352, 384  # table half sizes, slab bottom, top
TR = 1000                                 # track radius
BAL0, BAL1, BALZ = 928, 1072, 392         # ballast ring radii, top
RAIL = BALZ + 16                          # rail top
TRAIN_Z = 700                             # train mover origin height
MC, MRX, MRY = (0, 680), 620, 520         # mountain lower body ellipse
MPL = 688                                 # mountain plateau (lower body top)
BORE = (912, 1088, 640)                   # tunnel bore radii + top
CUT = (864, 1136)                         # cutting radii
TUN = (62.0, 118.0)                       # tunnel sector (degrees); cutting outside it
PEAK = (0, 560, 992)
DORM_X, DORM_Y, DORM_C = 320, -2112, 956  # dormer interior half width, window wall inner face, ceiling
HATCH = (0, 1536)
CAT_Z = 1168                              # catwalk top
POND = (-448, -1216, 448, -800)
STA_Y = 288                               # station hall half length (outer)
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
RAIL_MODELS = os.path.join(OUT, 'models', 'padattic')


def roof_z(y):
    """inner surface of the roof slope at |y|"""
    return RZ - (RZ - KW) * abs(y) / AY


# =================================================================================================== helpers
def rtex(s, tex):
    if s > 0 or not isinstance(tex, dict): return tex
    sw = {'e': 'w', 'w': 'e'}
    return {sw.get(k, k): v for k, v in tex.items()}


def sb(s, x0, y0, z0, x1, y1, z1, tex, detail=True):
    xa, xb = sorted((s * x0, s * x1))
    return box((round(xa), round(y0), z0), (round(xb), round(y1), z1), rtex(s, tex), detail)


def sh(s, pts, tex, rnd=True):
    return hull([(s * x, y, z) for (x, y, z) in pts], rtex(s, tex), round_pts=rnd)


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


def clip_box_for(b, ox, oy, oz, scale, angle, zsurf, shrink=0.12, ztop=None):
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    z1 = ztop if ztop is not None else oz + b['max'][2] * scale - 4
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1)), WCLIP))


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12):
    e = mdl_c(path, x, y, zsurf, scale, angle)
    ox, oy, oz = (float(v) for v in e['origin'].split())
    clip_box_for(BOUNDS['models/mapobjects/' + path], ox, oy, oz, scale, angle, zsurf, shrink)
    return e


def smdl(s, path, x, y, zsurf, scale=1.0, angle=0, solid=False, shrink=0.12):
    ang = (180 - angle) % 360 if s < 0 else angle % 360
    if solid: return solid_mdl(path, s * x, y, zsurf, scale, ang, shrink)
    return mdl_c(path, s * x, y, zsurf, scale, ang)


def own(name, x, y, z, angle=0, scale=1.0, **kw):
    """place one of this map's own MD3s (origin on the surface it stands on)"""
    return M.model(f'models/padattic/{name}.md3', (round(x, 2), round(y, 2), z), scale=scale, angle=angle % 360, **kw)


def light(x, y, z, val, color='1 0.85 0.62', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def slight(s, x, y, z, val, color='1 0.85 0.62'):
    light(s * x, y, z, val, color)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def item(s, cls, x, y, floor, **kw):
    M.ent(cls, (round(s * x), round(y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, s * x, y, floor))


def weapon(s, w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(s * x), round(y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, s * x, y, floor))


def spawn(s, cls, x, y, floor, ang):
    a = ang if s > 0 else (180 - ang) % 360
    M.ent(cls, (round(s * x), round(y), floor + 25), angle=a)
    SPOTS['spawn'].append((s * x, y, floor))


def ssign(s, mn, mx, tex, tw, th, facing, back):
    if s > 0: return sign_box(mn, mx, tex, tw, th, back=back, facing=facing)
    sw = {'n': 'n', 's': 's', 'e': 'w', 'w': 'e'}
    return sign_box((-mx[0], mn[1], mn[2]), (-mn[0], mx[1], mx[2]), tex, tw, th, back=back, facing=''.join(sw[c] for c in facing))


def fit_top(b, x0, y0, x1, y1, tw, th, tex=None):
    for f in b.faces:
        if f.n[2] > 0.9:
            if tex: f.tex = tex
            sx = (x1 - x0) / tw; sy = (y1 - y0) / th
            f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def wedge(r0, r1, a0, a1, z0, z1, tex, rnd=False):
    """annulus sector prism between angles a0..a1 (degrees)"""
    p = []
    for a in (a0, a1):
        c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        p += [(r0 * c, r0 * s_), (r1 * c, r1 * s_)]
    return hull([(x, y, z) for (x, y) in p for z in (z0, z1)], tex, round_pts=rnd)


def ellipse_pts(cx, cy, rx, ry, n=32, jit=0.0, seed=0, ph=None):
    rr = np.random.default_rng(seed)
    ph = math.pi / n if ph is None else ph
    out = []
    for k in range(n):
        a = ph + 2 * math.pi * k / n
        f = 1 + (rr.uniform(-jit, jit) if jit else 0)
        out.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a)))
    return out


def jumppad(x, y, z, land, apex, name):
    """kicker: disc (r 34) + trigger_push + target_position (target = apex of the flight, from the trigger centre,
    t_up/(t_up+t_down) of the way to `land`)"""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('metal'), 'bot': T('metal')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - lz - 24) / 800)
    f = tu / (tu + td)
    tx, ty = x + (lx - x) * f, y + (ly - y) * f
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    light(x, y, z + 48, 90, '1 0.8 0.4')


def spad(s, x, y, z, land, apex, name):
    jumppad(s * x, y, z, (s * land[0], land[1], land[2]), apex, name)


def stairs_s(s, x0, y0, x1, y1, z0, ztop, run_dir, tex, step_h=16, base=None, thick=None):
    """stairs() in red coordinates, mirrored for blue (run directions e/w swap)"""
    rd = run_dir if s > 0 else {'e': 'w', 'w': 'e'}.get(run_dir, run_dir)
    xa, xb = sorted((s * x0, s * x1))
    return stairs(round(xa), y0, round(xb), y1, z0, ztop, rd, tex, step_h=step_h, base=base, thick=thick)


def thin_sprite(x0, y0, x1, y1, z0, z1, tex, sx=None, sy=None):
    """2u vertical plate (nonsolid sprite shader on both big faces, nodraw_ns elsewhere)"""
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    q = [(x0, y0), (x1, y1), (x1 + nx * 2, y1 + ny * 2), (x0 + nx * 2, y0 + ny * 2)]
    def tf(n, nx=nx, ny=ny): return T(tex) if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
    b = hull([(px, py, z) for (px, py) in q for z in (z0, z1)], tf, round_pts=False)
    for f in b.faces:
        if f.tex == T(tex): f.sc = (sx or L / 256, sy or (z1 - z0) / 256); f.off = (0, 0)
    A(b)


# =================================================================================================== attic shell
def hull_box():
    """structural hull round everything; its inner faces are the night sky seen through every window"""
    x0, y0, z0, x1, y1, z1 = -AX - 256, -2560, -480, AX + 256, AY + 320, RZ + 256
    W = 16; sk = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), dict(sk, top=T('sky')), detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), dict(sk, bot=T('sky')), detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), dict(sk, s=T('sky')), detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), dict(sk, n=T('sky')), detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), dict(sk, w=T('sky')), detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), dict(sk, e=T('sky')), detail=False))


def floor_and_walls():
    fl = {'top': T('floorboards'), 'side': T('beam'), 'bot': T('wallpaper')}
    hx, hy = HATCH
    holes = [(hx - 64, hy - 64, hx + 64, hy + 64)]
    for (x0, y0, x1, y1) in sub_rects((-AX, -AY - 32, AX, AY + 32), holes):
        A(box((x0, y0, -32), (x1, y1, 0), fl))
    A(box((-DORM_X - 32, DORM_Y - 32, -32), (DORM_X + 32, -AY - 32, 0), fl))      # dormer floor
    # knee walls (north full, south with the dormer gap)
    kw = {'side': T('kneewall'), 'top': T('beam'), 'bot': CAULK}
    A(box((-AX, AY, 0), (AX, AY + 32, KW + RT), kw))
    A(box((-AX, -AY - 32, 0), (-DORM_X - 32, -AY, KW + RT), kw)); A(box((DORM_X + 32, -AY - 32, 0), (AX, -AY, KW + RT), kw))
    # roof slopes (inner face = roof boards); the south slope has the dormer cut out
    rf = {'bot': T('roofboards'), 'side': CAULK, 'top': CAULK}
    def slope(sg):
        pts = []
        for x in (-AX, AX):
            for (y, z) in ((0, RZ), (sg * AY, KW), (sg * AY, KW + RT), (0, RZ + RT)):
                pts.append((x, y, z))
        return hull(pts, lambda n: T('roofboards') if n[2] < -0.3 else CAULK)
    A(slope(1))
    cutter = box((-DORM_X - 32, -2600, -64), (DORM_X + 32, -1008, 1100), CAULK)
    for b in carve(slope(-1), [cutter], tex=CAULK):
        for f in b.faces:
            if f.n[2] < -0.3: f.tex = T('roofboards')
        A(b)
    # gable walls with a square window each (glass + frame)
    for sg in (1, -1):
        x0, x1 = (AX, AX + 32) if sg > 0 else (-AX - 32, -AX)
        pts = [(x, y, z) for x in (x0, x1) for (y, z) in ((-AY - 32, 0), (AY + 32, 0), (AY + 32, KW + RT), (0, RZ + RT + 40), (-AY - 32, KW + RT))]
        g = hull(pts, lambda n, sg=sg: T('gable') if n[0] * sg < -0.9 else CAULK)
        win = box((x0 - 1, -160, 1120), (x1 + 1, 160, 1440), CAULK)
        for b in carve(g, [win], tex=CAULK):
            for f in b.faces:
                if f.n[0] * sg < -0.9: f.tex = T('gable')
            A(b)
        gx = AX + 12 if sg > 0 else -AX - 20
        A(box((gx, -160, 1120), (gx + 8, 160, 1440), T('glass')))
        mx0, mx1 = (AX - 8, AX + 12) if sg > 0 else (-AX - 12, -AX + 8)
        A(box((mx0, -6, 1120), (mx1, 6, 1440), T('beam'))); A(box((mx0, -160, 1274), (mx1, -6, 1286), T('beam'))); A(box((mx0, 6, 1274), (mx1, 160, 1286), T('beam')))
        sx0, sx1 = (AX - 24, AX) if sg > 0 else (-AX, -AX + 24)
        A(box((sx0, -176, 1104), (sx1, 176, 1120), T('beam')))                     # sill
        speaker(sg * (AX - 60), 0, 1280, 'sound/world/ambient/wind_night.ogg')
    # dormer: side walls, ceiling, window wall with window, window seat + steps
    dw = {'side': T('gable'), 'top': CAULK, 'bot': CAULK}
    for sg in (1, -1):
        xa, xb = sorted((sg * DORM_X, sg * (DORM_X + 32)))
        A(box((xa, DORM_Y, 0), (xb, -AY, DORM_C), dw))
        A(hull([(x, y, z) for x in (xa, xb) for (y, z) in ((-AY, KW), (-1008, DORM_C), (-AY, DORM_C))], dw))
    A(box((-DORM_X - 32, DORM_Y - 32, DORM_C), (DORM_X + 32, -1008, DORM_C + 32), {'bot': T('roofboards'), 'side': CAULK, 'top': CAULK}))
    wall = box((-DORM_X - 32, DORM_Y - 32, 0), (DORM_X + 32, DORM_Y, DORM_C), {'n': T('gable'), 'side': CAULK})
    for b in carve(wall, [box((-224, DORM_Y - 40, 192), (224, DORM_Y + 8, 760), CAULK)], tex=CAULK):
        for f in b.faces:
            if f.n[1] > 0.9: f.tex = T('gable')
        A(b)
    A(box((-224, DORM_Y - 20, 192), (224, DORM_Y - 12, 760), T('glass')))
    A(box((-6, DORM_Y - 12, 192), (6, DORM_Y, 760), T('beam'))); A(box((-224, DORM_Y - 12, 470), (-6, DORM_Y, 482), T('beam'))); A(box((6, DORM_Y - 12, 470), (224, DORM_Y, 482), T('beam')))
    A(box((-DORM_X, DORM_Y, 0), (DORM_X, DORM_Y + 144, 160), {'top': T('lining'), 'side': T('beam'), 'bot': CAULK}))
    for b in stairs(-96, DORM_Y + 144, 96, DORM_Y + 304, 0, 160, 's', {'top': T('beam'), 'side': T('crate'), 'bot': CAULK}, step_h=16):
        A(b)
    weapon(1, 'boaster', 0, DORM_Y + 72, 160, 'orange')
    mdl_c('pad_ddmix/cabin/telescope.md3', 230, DORM_Y + 70, 160, 1.0, 270)
    item(1, 'ammo_betty', 220, -1880, 0)
    light(0, DORM_Y + 200, 600, 300, '0.7 0.8 1')
    speaker(0, DORM_Y + 40, 500, 'sound/world/ambient/wind_night.ogg')
    speaker(0, DORM_Y + 40, 600, 'sound/world/animal/bird_owl1.ogg', loop=False, targetname='owl')
    M.ent('func_timer', (0, DORM_Y + 100, 700), target='owl', wait=40, random=20, spawnflags=1)
    # poster on each gable wall
    for s in (1, -1):
        A(ssign(s, (-AX, -560, 300), (-AX + 4, -304, 684), T('poster'), 256, 384, 'e', T('gable')))


def rafters():
    """exposed rafters under both slopes, collar beams carrying the catwalk, ridge beam, hanging bulbs"""
    bm = T('beam')
    for x in (-1920, -1152, -384, 384, 1152, 1920):
        for sg in (1, -1):
            pts = []
            for xx in (x - 24, x + 24):
                for y in (sg * 40, sg * (AY - 8)):
                    z = roof_z(y)
                    pts += [(xx, y, z), (xx, y, z - 40)]
            A(hull(pts, bm, round_pts=False))
    A(box((-AX, -24, 1784), (AX, 24, 1830), bm))
    yc = int(AY * (RZ - CAT_Z + 16) / (RZ - KW))                                  # where z 1152 meets the slope
    for x in (-1536, -768, 0, 768, 1536):
        A(box((x - 24, -yc, CAT_Z - 64), (x + 24, yc, CAT_Z - 16), bm))
    A(box((-1600, -80, CAT_Z - 16), (1600, 80, CAT_Z), {'top': T('floorboards'), 'side': bm, 'bot': bm}))
    weapon(1, 'splasher', 0, 0, CAT_Z, 'orange')
    for s in (1, -1):
        item(s, 'ammo_imperius', -1440, 0, CAT_Z)
        item(s, 'item_armor_shard', -620, 0, CAT_Z)
    # hanging bulbs below the collar beams (nonsolid glow + cord) and their lights
    for x in (-1536, -768, 0, 768, 1536):
        for y in (-420, 420):
            A(box((x - 2, y - 2, 1010), (x + 2, y + 2, CAT_Z - 64), {'side': T('cord'), 'top': NODRAW_NS, 'bot': NODRAW_NS}))
            b = hull([(px, py, z) for (px, py) in ngon(x, y, 12, 8) for z in (974, 1010)], T('bulb'))
            A(b)
            light(x, y, 950, 2700, '1 0.82 0.58')
    for (x, y, z) in ((0, 0, 1350), (-1100, 0, 1350), (1100, 0, 1350)):
        light(x, y, z, 600, '1 0.85 0.65')


# =================================================================================================== table + track
def table():
    tt = {'top': T('grass'), 'side': T('ply_edge'), 'bot': T('ply_under')}
    for (x0, y0, x1, y1) in sub_rects((-TX0, -TY0, TX0, TY0), [POND]):
        A(box((x0, y0, TZB), (x1, y1, TZ), tt))
    leg = {'side': T('beam'), 'top': CAULK, 'bot': CAULK}
    for (x, y) in ((-1600, -1216), (-800, -1216), (-560, -1216), (-1600, 1216), (-800, 1216), (0, 1216), (-1600, 0), (-800, 0)):
        for s in ((1, -1) if x else (1,)):
            A(sb(s, x - 32, y - 32, 0, x + 32, y + 32, TZB, leg))


def ballast_ring():
    n = 64
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        am = math.radians((a0 + a1) / 2)
        mx, my = TR * math.cos(am), TR * math.sin(am)
        over_pond = POND[0] < mx < POND[2] and POND[1] < my < POND[3]
        tex = {'top': T('trestle'), 'side': T('trestle'), 'bot': T('trestle')} if over_pond else {'top': T('ballast'), 'side': T('ballast'), 'bot': CAULK}
        A(wedge(BAL0, BAL1, a0, a1, TZ, BALZ, tex))
        if over_pond and abs(mx) < 320:                                        # trestle legs into the pond
            for r in (950, 1050):
                lx, ly = r * math.cos(am), r * math.sin(am)
                A(box((round(lx) - 8, round(ly) - 8, 320), (round(lx) + 8, round(ly) + 8, TZ), T('trestle')))
    for k in range(8):
        a = 22.5 + 45 * k
        own('track_arc', TR * math.cos(math.radians(a)), TR * math.sin(math.radians(a)), BALZ, angle=a)


def train():
    """the centrepiece: one func_rotating carrying the whole train (IQM) round the circle; nodraw collision boxes per car"""
    front = 205.0
    path = RM.train_loop(OUT, front, RAIL - TRAIN_Z)
    brushes = [box((-8, -8, TRAIN_Z - 8), (8, 8, TRAIN_Z + 8), ORIGIN)]
    for (name, ang, xc, L) in RM.train_layout(front):
        x0, x1, top = RM.STOCK[name]
        th = math.radians(ang); c, s_ = math.cos(th), math.sin(th)
        t = (-s_, c); rad = (c, s_)
        cx, cy = TR * c, TR * s_
        pts = []
        for lx in (x0 + 6, x1 - 6):
            for ly in (-56, 56):
                px = cx + t[0] * (lx - xc) + rad[0] * ly; py = cy + t[1] * (lx - xc) + rad[1] * ly
                pts += [(px, py, RAIL + 2), (px, py, RAIL + top)]
        brushes.append(hull(pts, WCLIP))       # WoP common/nodraw is NONSOLID: the cars had no collision
    M.ent('func_rotating', brushes=brushes, model2=path, speed=9, spawnflags=0, dmg=0)
    # the train's sounds: chuffing near both stations and in the tunnel, a whistle-ish bell on a timer
    for (x, y) in ((-1000, 0), (1000, 0), (0, 1000), (0, -1000)):
        speaker(x, y, 520, 'sound/world/machine/mechanics.ogg')
    speaker(0, 0, 900, 'sound/world/ambient/train_intercity.ogg', loop=False, targetname='rumble')
    M.ent('func_timer', (0, 60, 900), target='rumble', wait=55, random=20, spawnflags=1)


def train_sweep_check():
    """the train sweeps the band R 944..1061, z RAIL..RAIL+190: no static solid may sit in it"""
    sol = []
    for b in M.world:
        if not b.is_solid(): continue
        tx = b.textures()
        mn, mx = b.bounds()
        if mx[2] <= RAIL + 1 or mn[2] >= RAIL + 190: continue
        sol.append((b, mn, mx))
    bad = []
    for a in range(0, 360, 1):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        for r in (946, 975, 1000, 1025, 1059):
            for z in (RAIL + 4, RAIL + 90, RAIL + 186):
                p = (r * ca, r * sa, z)
                for (b, mn, mx) in sol:
                    if mn[0] < p[0] < mx[0] and mn[1] < p[1] < mx[1] and mn[2] < p[2] < mx[2] and \
                       all(n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - d < -0.5 for (n, d) in b.planes()):
                        bad.append((a, r, z, tuple(np.round(mn).astype(int)))); break
    print('train sweep:', 'OK' if not bad else f'{len(bad)} hits, e.g. {bad[:4]}')


# =================================================================================================== mountain
def mountain():
    cx, cy = MC
    rk = {'top': T('rock_moss'), 'side': T('rock'), 'bot': CAULK}
    body = prism(ellipse_pts(cx, cy, MRX, MRY, 32), TZ, MPL, rk)
    cutters = []
    t0, t1 = TUN
    nb = 10
    for k in range(nb):                                                       # tunnel bore
        a0 = t0 + (t1 - t0) * k / nb; a1 = t0 + (t1 - t0) * (k + 1) / nb
        cutters.append(wedge(BORE[0], BORE[1], a0, a1, TZ - 8, BORE[2], CAULK))
    for (a, b) in ((20, t0), (t1, 160)):                                      # cutting on both approaches
        n = max(1, int(round((b - a) / 5)))
        for k in range(n):
            a0 = a + (b - a) * k / n; a1 = a + (b - a) * (k + 1) / n
            cutters.append(wedge(CUT[0], CUT[1], a0, a1, TZ - 8, MPL + 8, CAULK))
    pieces = carve(body, cutters, tex=T('rock'))
    for p in pieces:
        for f in p.faces:
            f.tex = T('rock_moss') if f.n[2] > 0.7 else (CAULK if f.n[2] < -0.7 else T('rock'))
            f.sc = wopmap.default_scale(f.tex)
        A(p)
    # upper mountain: two craggy tiers and a flat snowy peak
    pcx, pcy, pz = PEAK
    r1 = ellipse_pts(pcx, pcy, 380, 280, 14, 0.04, 3)
    r2 = ellipse_pts(pcx, pcy, 300, 220, 14, 0.06, 4, ph=0.3)
    r3 = ellipse_pts(pcx, pcy, 170, 130, 12, 0.05, 5)
    r4 = ellipse_pts(pcx, pcy, 140, 104, 12, 0.0, 6)
    A(hull([(x, y, MPL) for (x, y) in r1] + [(x, y, 840) for (x, y) in r2], {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}))
    A(hull([(x, y, 840) for (x, y) in r2] + [(x, y, 968) for (x, y) in r3], {'top': T('snow'), 'side': T('rock'), 'bot': CAULK}))
    A(hull([(x, y, 968) for (x, y) in r3] + [(x, y, pz) for (x, y) in r4], {'top': T('snow'), 'side': T('snow'), 'bot': CAULK}))
    weapon(1, 'imperius', pcx, pcy, pz, 'purple')
    light(pcx, pcy, pz + 160, 700, '0.85 0.9 1')
    for s in (1, -1):
        spad(s, -470, 640, MPL, (-40, 600, pz), 1110, 'peak_%s' % ('r' if s > 0 else 'b'))
    # stairs up to the plateau: two flights rising toward the middle + the landing
    st = {'top': T('paving'), 'side': T('rock_dark'), 'bot': CAULK}
    for s in (1, -1):
        for b in stairs_s(s, -648, -60, -40, 68, TZ, MPL, 'e', st): A(b)
    A(box((-40, -60, TZ), (40, 160, MPL), st))
    # tunnel portals (MD3) at both ends of the bore, facing out along the track; weapclip piers + lintel
    for (ang, out_sign) in ((t0, -1), (t1, 1)):
        th = math.radians(ang); c, s_ = math.cos(th), math.sin(th)
        nrm = (out_sign * -s_, out_sign * c)                                   # outward (away from the tunnel)
        yaw = math.degrees(math.atan2(nrm[1], nrm[0]))
        own('portal', TR * c, TR * s_, TZ, angle=yaw)
        rad = (c, s_)
        def P(lx, ly, z): return (TR * c + nrm[0] * lx + rad[0] * ly, TR * s_ + nrm[1] * lx + rad[1] * ly, z)
        for (ly0, ly1, z0, z1) in ((-124, -74, TZ, TZ + 304), (74, 124, TZ, TZ + 304), (-74, 74, BORE[2] - 8, TZ + 304)):
            A(hull([P(lx, ly, z) for lx in (1, 40) for ly in (ly0, ly1) for z in (z0, z1)], WCLIP, round_pts=False))
        own('signal', TR * c + nrm[0] * 140 + rad[0] * 150, TR * s_ + nrm[1] * 140 + rad[1] * 150, TZ, angle=yaw + 180)
    # boulders round the foot of the mountain
    for s in (1, -1):
        for (x, y, r, h, sd) in ((-650, 520, 60, 150, 1), (-300, 1228, 48, 110, 2), (-560, 1060, 70, 170, 3), (-560, -130, 44, 90, 4)):
            A(boulder(s * x, y, r, r * 0.85, h, TZ, sd + (0 if s > 0 else 10)))
    light(0, 260, 620, 500, '1 0.9 0.75')
    # plateau loot + trees
    item(1, 'holdable_floater', 0, 1060, MPL)
    for s in (1, -1):
        item(s, 'ammo_splasher', -300, 980, MPL)
        for (x, y) in ((-200, 1080), (-330, 900)):
            smdl_own(s, 'pine%d' % (1 + (x // 100) % 3), x, y, MPL, 0.8, solid=True)
    light(0, 900, MPL + 200, 500, '0.85 0.9 1')
    light(0, 1000, 520, 260, '1 0.8 0.5')                                      # tunnel lamps
    for a in (75, 105): light(TR * math.cos(math.radians(a)), TR * math.sin(math.radians(a)), 560, 180, '1 0.8 0.5')


def boulder(cx, cy, rx, ry, h, z, seed):
    rr = np.random.default_rng(seed)
    pts = []
    for k in range(9):
        a = 2 * math.pi * (k + rr.uniform(-0.25, 0.25)) / 9
        f = rr.uniform(0.85, 1.0)
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a), z))
        f2 = rr.uniform(0.55, 0.8)
        pts.append((cx + rx * f2 * math.cos(a + 0.3), cy + ry * f2 * math.sin(a + 0.3), z + h * rr.uniform(0.45, 0.7)))
    for k in range(4):
        a = 2 * math.pi * k / 4 + rr.uniform(0, 1)
        pts.append((cx + rx * 0.3 * math.cos(a), cy + ry * 0.3 * math.sin(a), z + h * rr.uniform(0.88, 1.0)))
    return hull(pts, {'top': T('rock_moss'), 'side': T('rock'), 'bot': CAULK})


def smdl_own(s, name, x, y, z, scale=1.0, angle=0, solid=False):
    own(name, s * x, y, z, angle=(angle if s > 0 else 180 - angle), scale=scale)
    if solid:
        r = 36 * scale
        A(box((round(s * x - r), round(y - r), z), (round(s * x + r), round(y + r), round(z + 170 * scale)), WCLIP))


# =================================================================================================== stations
def station(s):
    team = 'red' if s > 0 else 'blue'
    wall = {'side': T('brick_red' if s > 0 else 'timber_blue'), 'top': T('trim_white'), 'bot': CAULK}
    x0, x1, y0, y1 = -1232, -768, -STA_Y, STA_Y
    zt = 688
    # outer wall (door in the north part), inner wall (door in the middle)
    A(sb(s, x0, y0, TZ, x0 + 32, 144, zt, wall)); A(sb(s, x0, 240, TZ, x0 + 32, y1, zt, wall)); A(sb(s, x0, 144, 528, x0 + 32, 240, zt, wall))
    A(sb(s, x1 - 32, y0, TZ, x1, -48, zt, wall)); A(sb(s, x1 - 32, 48, TZ, x1, y1, zt, wall)); A(sb(s, x1 - 32, -48, 528, x1, 48, zt, wall))
    # end walls with the track openings
    for (ya, yb) in ((y1 - 32, y1), (y0, y0 + 32)):
        A(sb(s, x0 + 32, ya, TZ, -1046, yb, zt, wall)); A(sb(s, -876, ya, TZ, x1 - 32, yb, zt, wall))
        A(sb(s, -1046, ya, BORE[2], -876, yb, zt, wall))
    # roof, platforms, steps outside the doors
    A(sb(s, x0, y0, zt, x1, y1, zt + 16, {'top': T('roof_flat'), 'side': T('trim_white'), 'bot': T('roofboards')}))
    pl = {'top': T('paving'), 'side': T('stone'), 'bot': CAULK}
    A(sb(s, -1200, y0 + 32, TZ, -1078, y1 - 32, 416, pl)); A(sb(s, -884, y0 + 32, TZ, -800, y1 - 32, 416, pl))
    A(sb(s, x0 - 32, 144, TZ, x0, 240, 400, pl)); A(sb(s, x1, -48, TZ, x1 + 32, 48, 400, pl))
    # name boards outside
    A(ssign(s, (-1046, y1, 644), (-876, y1 + 4, 684), T('sign_' + team), 512, 128, 'n', T('trim_white')))
    A(ssign(s, (-1046, y0 - 4, 644), (-876, y0, 684), T('sign_' + team), 512, 128, 's', T('trim_white')))
    A(ssign(s, (x1, 80, 560), (x1 + 4, 260, 640), T('sign_' + team), 512, 128, 'e', T('trim_white')))
    # stairs to the roof along the outer wall (32u risers), Pumper on the roof, kicker up to the catwalk
    st = {'top': T('paving'), 'side': T('stone'), 'bot': CAULK}
    for b in stairs_s(s, -1360, -320, x0, 80, TZ, zt + 16, 'n', st, step_h=16): A(b)
    weapon(s, 'pumper', -1000, 100, zt + 16, 'green')
    spad(s, -1000, -240, zt + 16, (-1000, 10, CAT_Z), 1340, 'catwalk_' + team)
    # lolly, health, loot, lights
    lol = 'team_CTL_%slolly' % team
    M.ent(lol, (s * -1140, 0, 416 + 16)); SPOTS['item'].append((lol, s * -1140, 0, 416))
    M.ent('station_health', (s * -842, 150, 416), angle=(0 if s > 0 else 180))
    item(s, 'ammo_pumper', -842, -150, 416)
    item(s, 'item_armor_shard', -1140, -200, 416)
    for y in (-150, 150): slight(s, -1000, y, 640, 330, '1 0.85 0.6')
    slight(s, -1300, 200, 600, 300); slight(s, -700, 0, 600, 320)
    speaker(s * -1000, 0, 600, 'sound/world/machine/dingdong.ogg', loop=False, targetname='bell_' + team)
    M.ent('func_timer', (s * -1000, 40, 640), target='bell_' + team, wait=30, random=10, spawnflags=1)
    # siding with a parked loco + carriage (MD3, weapclip), water tower
    for yc in (-744, -232): own('track_straight', s * -1540, yc, TZ, angle=90)
    own('loco', s * -1540, -300, TZ, angle=90); own('carriage', s * -1540, -760, TZ, angle=90)
    A(sb(s, -1596, -482, TZ, -1484, -120, 564, WCLIP)); A(sb(s, -1596, -936, TZ, -1484, -584, 568, WCLIP))
    item(s, 'ammo_balloony', -1420, -760, TZ)
    own('water_tower', s * -1450, 640, TZ, angle=(0 if s > 0 else 180))
    for (lx, ly) in ((-1500, 590), (-1400, 590), (-1500, 690), (-1400, 690)):
        A(sb(s, lx - 6, ly - 6, TZ, lx + 6, ly + 6, TZ + 200, WCLIP))
    A(cyl(s * -1450, 640, 70, TZ + 208, TZ + 312, WCLIP, 12))


# =================================================================================================== village
def town_hall():
    wall = {'side': T('stone'), 'top': T('trim_white'), 'bot': CAULK}
    x0, x1, y0, y1 = -192, 192, -500, -220
    zt = 560
    A(box((x0, y0, TZ), (x1, y0 + 32, zt), wall)); A(box((x0, y1 - 32, TZ), (x1, y1, zt), wall))
    for s in (1, -1):
        A(sb(s, x0, y0 + 32, TZ, x0 + 32, -400, zt, wall)); A(sb(s, x0, -320, TZ, x0 + 32, y1 - 32, zt, wall))
        A(sb(s, x0, -400, 496, x0 + 32, -320, zt, wall))
    A(box((x0, y0, zt), (x1, y1, zt + 16), {'top': T('roof_flat'), 'side': T('trim_white'), 'bot': T('wallpaper')}))
    # clock tower (MD3) on the roof, weapclip shaft + roof
    own('clock_tower', 0, -290, zt + 16, angle=0, spawnflags=4, _castshadows=1)
    A(box((-58, -348, zt + 16), (58, -232, zt + 16 + 262), WCLIP))
    A(hull([(x, y, zt + 16 + 262) for x in (-56, 56) for y in (-346, -234)] + [(0, -290, zt + 16 + 330)], WCLIP))
    light(0, -400, zt + 260, 160, '1 0.95 0.8'); light(0, -180, zt + 260, 160, '1 0.95 0.8')
    A(sign_box((-128, y1, 480), (128, y1 + 4, 528), T('sign_hall'), 512, 128, back=T('trim_white'), facing='n'))
    st = {'top': T('paving'), 'side': T('stone'), 'bot': CAULK}
    for s in (1, -1):
        for b in stairs_s(s, -224, -564, -32, y0, TZ, zt + 16, 'e', st, step_h=16): A(b)
    A(box((-32, -564, TZ), (32, y0, zt + 16), st))
    item(1, 'team_CTL_neutrallolly', 0, -360, TZ)
    item(1, 'ammo_boaster', 0, -440, zt + 16)
    light(0, -360, 520, 300, '1 0.85 0.6')
    light(0, -560, 720, 300)
    speaker(0, -260, 640, 'sound/world/machine/clock_ticking.ogg')


def cottage(s, x0, x1, y0, y1, stairs_side, wall_tex, roof_tex, door_tex, ox=16):
    """walk-in cottage with a tiled 28-degree roof (ridge along x), door toward the middle, outside stairs to the eave"""
    wall = {'side': T(wall_tex), 'top': T('trim_white'), 'bot': CAULK}
    zw = 540
    yc = (y0 + y1) / 2
    A(sb(s, x0, y0, TZ, x1, y0 + 32, zw, wall)); A(sb(s, x0, y1 - 32, TZ, x1, y1, zw, wall))
    A(sb(s, x0, y0 + 32, TZ, x0 + 32, y1 - 32, zw, wall))
    A(sb(s, x1 - 32, y0 + 32, TZ, x1, yc - 40, zw, wall)); A(sb(s, x1 - 32, yc + 40, TZ, x1, y1 - 32, zw, wall))
    A(sb(s, x1 - 32, yc - 40, 496, x1, yc + 40, zw, wall))
    hw = (y1 - y0) / 2
    zr = zw + 60
    for xa, xb in ((x0, x0 + 32), (x1 - 32, x1)):                               # gable triangles
        A(sh(s, [(x, y, z) for x in (xa, xb) for (y, z) in ((y0, zw), (y1, zw), (yc, zr))], {'side': T(wall_tex), 'top': T(wall_tex), 'bot': CAULK}))
    k = 60 / hw
    for sg in (1, -1):                                                          # roof slabs (12 thick, 16 overhang)
        ye = yc - sg * (hw + 16); zi = zw - 16 * k
        pts = [(x, y, z) for x in (x0 - ox, x1 + ox) for (y, z) in ((ye, zi), (yc, zr), (yc, zr + 12), (ye, zi + 12))]
        A(sh(s, pts, {'top': T(roof_tex), 'side': T('beam'), 'bot': T('beam')}, rnd=False))
    # lit windows on the long walls
    for (ya, yb, fc) in ((y0 - 2, y0, 's'), (y1, y1 + 2, 'n')):
        if (fc == 'n' and stairs_side == 'n') or (fc == 's' and stairs_side == 's'): continue
        xm = (x0 + x1) / 2
        A(ssign(s, (xm - 40, ya, 430), (xm + 40, yb, 500), T('window_lit'), 128, 128, fc, T('trim_white')))
    # stairs to the eave
    st = {'top': T('beam'), 'side': T('crate'), 'bot': CAULK}
    if stairs_side == 'n':
        ya, yb = y1 + 16, y1 + 80
    else:
        ya, yb = y0 - 80, y0 - 16
    for b in stairs_s(s, x0, ya, x0 + 200, yb, TZ, TZ + 160, 'e', st): A(b)
    slight(s, (x0 + x1) / 2, yc, 500, 200, '1 0.8 0.5')


def village():
    for s in (1, -1):
        warm = s > 0
        cottage(s, -688, -432, -492, -268, 'n', 'plaster_warm' if warm else 'plaster_cool', 'tiles_red' if warm else 'tiles_blue', 'door_red' if warm else 'door_blue')
        cottage(s, -744, -560, 200, 410, 's', 'plaster_warm' if warm else 'plaster_cool', 'tiles_red' if warm else 'tiles_blue', 'door_wood', ox=8)
        item(s, 'ammo_bubbleg', -560, -380, TZ)
        item(s, 'ammo_pumper', -660, 260, TZ)
        weapon(s, 'bubbleg', -400, -110, TZ, 'blue')
        for (x, y) in ((-300, -120), (-300, 150), (-620, -570)):
            mdl_c('pad_ddmix/padship/shiplamp.md3', s * x, y, TZ, 1.0, 0)
            slight(s, x, y, TZ + 170, 220, '1 0.8 0.5')
    item(1, 'item_jumper', 0, -120, TZ)
    for (x, y) in ((-600, 0), (600, 0), (0, -700)):
        light(x, y, 700, 500)


def pond():
    x0, y0, x1, y1 = POND
    A(box((x0, y0, 288), (x1, y1, 320), {'top': T('sand'), 'side': CAULK, 'bot': T('ply_under')}))
    pw = {'side': T('ply_under'), 'top': CAULK, 'bot': T('ply_under')}
    A(box((x0 - 32, y0 - 32, 288), (x0, y1 + 32, TZB), pw)); A(box((x1, y0 - 32, 288), (x1 + 32, y1 + 32, TZB), pw))
    A(box((x0, y0 - 32, 288), (x1, y0, TZB), pw)); A(box((x0, y1, 288), (x1, y1 + 32, TZB), pw))
    rp = []
    for s in (1, -1):
        rb = sh(s, [(x, y, z) for y in (y0, y1) for (x, z) in ((x0, 320), (x0 + 128, 320), (x0, TZ))], {'top': T('sand'), 'side': T('sand'), 'bot': CAULK}, rnd=False)
        A(rb); rp.append(rb)
    legs = [b for b in M.world if T('trestle') in b.textures() and b.bounds()[0][2] == 320]
    water = box((x0, y0, 320), (x1, y1, 368), T('water_inner'))
    for p in carve(water, rp + legs, tex=T('water_inner')):
        for f in p.faces:
            f.tex = T('water') if (f.n[2] > 0.9 and abs(f.d - 368) < 0.5) else T('water_inner')
        A(p)
    item(1, 'item_visionless', -200, -870, 320)
    item(1, 'ammo_nipper', 150, -860, 320)
    for s in (1, -1):
        smdl(s, 'gummybears/ldredbear.md3' if s > 0 else 'gummybears/ldyellowbear.md3', -640, -1150, TZ, 0.8, 20, solid=True)
    light(0, -1000, 620, 500, '0.9 0.92 1')


def scenery(s):
    """pines on the table, trees and lamps"""
    for (x, y, k, sc) in ((-1250, 1000, 1, 1.0), (-1480, 1140, 2, 0.85), (-1000, 1180, 3, 0.9), (-1150, -1150, 1, 1.0),
                          (-760, -1180, 2, 0.8), (-760, 1120, 3, 0.95), (-300, -680, 1, 0.75), (-1400, -1120, 2, 0.9)):
        smdl_own(s, 'pine%d' % k, x, y, TZ, sc, angle=(x * 7) % 360, solid=True)


# =================================================================================================== under the table + attic floor
def cardboard_box(x0, x1, y0, y1, h, face=None, label='box_trains', z0=0):
    b = box((x0, y0, z0), (x1, y1, z0 + h), {'side': T('cardboard'), 'top': T('cardboard'), 'bot': CAULK})
    if face:
        for f in b.faces:
            v = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[face]
            if f.n[0] * v[0] + f.n[1] * v[1] > 0.99:
                f.tex = T(label)
                if face in 'ns': fit_face(f, x0, x1, z0, z0 + h, 256, 256)
                else: fit_face(f, y0, y1, z0, z0 + h, 256, 256)
    A(b)


def under_table():
    # the toy crate in the middle with the Betty (gaps in the east and west walls)
    cr = {'side': T('crate'), 'top': T('beam'), 'bot': CAULK}
    A(box((-128, -128, 0), (128, -112, 144), cr)); A(box((-128, 112, 0), (128, 128, 144), cr))
    for s in (1, -1):
        A(sb(s, -128, -112, 0, -112, -40, 144, cr)); A(sb(s, -128, 40, 0, -112, 112, 144, cr)); A(sb(s, -128, -40, 96, -112, 40, 144, cr))
    weapon(1, 'betty', 0, 0, 0, 'black')
    light(0, 0, 220, 220, '1 0.85 0.6')
    for s in (1, -1):
        # train controller
        b = sb(s, -496, 536, 0, -304, 664, 96, {'side': T('metal'), 'top': T('powerpack'), 'bot': CAULK})
        xa = min(s * -496, s * -304); fit_top(b, xa, 536, xa + 192, 664, 256, 256)
        A(b)
        speaker(s * -400, 600, 120, 'sound/world/machine/transformer.ogg')
        # boxes (cover), spiders, cobwebs, loot
        cardboard_box(*sorted((s * -1180, s * -980)), -700, -520, 160, 's', 'box_trains')
        cardboard_box(*sorted((s * -1400, s * -1220)), 600, 820, 200, 's', 'box_books')
        cardboard_box(*sorted((s * -760, s * -600)), -1000, -840, 128, 'n', 'box_xmas')
        mdl_c('spider/spiderf.md3', s * -560, -20, 0, 3.0, 30 if s > 0 else 150)
        item(s, 'item_armor_padshield', -1200, 0, 0)
        item(s, 'ammo_betty', -1300, 900, 0)
        item(s, 'ammo_bubbleg', -1000, -1000, 0)
        item(s, 'holdable_boomies' if s > 0 else 'holdable_killerducks', -1300, -900, 0)
        for (x, y) in ((-1568, -1150), (-1568, 1150)):
            thin_sprite(s * x, y, s * (x + 220), y, 140, TZB - 1, 'cobweb', 220 / 256, (TZB - 141) / 256)
        for (x, y, z) in ((-1100, 400, 200), (-600, -500, 200), (-1300, -600, 200), (-500, 900, 200)):
            slight(s, x, y, z, 300, '0.9 0.8 0.65')
    # storage clutter under the layout (cover)
    for s in (1, -1):
        for (x, y, w, d, h, lab, fc) in ((-400, -300, 200, 160, 200, 'box_books', 'e'), (-960, 160, 180, 180, 160, 'box_trains', 'e'),
                                          (-650, 900, 200, 150, 150, 'box_xmas', 's'), (-250, 300, 160, 140, 120, 'box_trains', 's'),
                                          (-1350, -350, 220, 160, 180, 'box_books', 'e'), (-1000, -1150, 160, 120, 140, 'box_trains', 'n'),
                                          (-1250, 1080, 200, 140, 170, 'box_xmas', 's')):
            xa, xb = sorted((s * (x - w / 2), s * (x + w / 2)))
            cardboard_box(round(xa), round(xb), y - d // 2, y + d // 2, h, fc if s > 0 else {'e': 'w', 'w': 'e'}.get(fc, fc), lab)
        smdl(s, 'pad_tins/pad_paint1.md3', -520, -660, 0, 1.0, 30, solid=True)
        smdl(s, 'pad_tins/pad_paint2.md3', -1150, -1000, 0, 1.0, 200, solid=True)
    A(box((-120, -580, 0), (120, -420, 120), {'side': T('trunk'), 'top': T('trunk'), 'bot': CAULK}))     # old suitcase
    A(box((-100, 720, 0), (100, 840, 110), {'side': T('crate'), 'top': T('beam'), 'bot': CAULK}))
    item(1, 'item_speedy', 0, 1050, 0)
    item(1, 'ammo_imperius', 0, -900, 0)
    item(1, 'ammo_boaster', 0, 600, 0)


def gable_end(s):
    team = 'red' if s > 0 else 'blue'
    cr = {'top': T('beam'), 'side': T('crate'), 'bot': CAULK}
    for b in stairs_s(s, -1856, -868, -1696, -100, 0, TZ, 'n', cr): A(b)
    A(sb(s, -1856, -100, 0, -TX0, 100, TZ, cr))
    # the old trunk: book steps up, steps down inside, Balloony
    tr = {'side': T('trunk'), 'top': T('beam'), 'bot': CAULK}
    x0, x1, y0, y1 = -2210, -1890, -1196, -1004
    A(sb(s, x0, y0, 0, x1, y1, 16, {'top': T('lining'), 'side': T('trunk'), 'bot': CAULK}))
    A(sb(s, x0, y0, 16, x1, y0 + 16, 128, tr)); A(sb(s, x0, y1 - 16, 16, x1, y1, 128, tr))
    A(sb(s, x0, y0 + 16, 16, x0 + 16, y1 - 16, 128, tr)); A(sb(s, x1 - 16, y0 + 16, 16, x1, y1 - 16, 128, tr))
    A(sh(s, [(x, y, z) for x in (x0, x1) for (y, z) in ((y0, 128), (y0 - 16, 128), (y0 - 52, 316), (y0 - 36, 320))], tr, rnd=False))   # open lid
    bk = {'top': T('box_books'), 'side': T('lining'), 'bot': CAULK}
    for b in stairs_s(s, -2110, y1, -1990, y1 + 120, 0, 96, 's', bk, step_h=32): A(b)
    for b in stairs_s(s, -2110, y1 - 112, -1990, y1 - 16, 16, 112, 'n', bk, step_h=32): A(b)
    weapon(s, 'balloony', -2150, -1150, 16, 'green')
    # stored things: Christmas tree + snowman + box, TV, standee, kasperle theatre, tyre, toy pumper
    smdl(s, 'pad_ddmix/trashcan/tree_winter.md3', -2060, 1000, 0, 0.55, 30, solid=True, shrink=0.4)
    smdl(s, 'pad_ddmix/jail/snowman.md3', -1860, 1240, 0, 1.0, 300, solid=True)
    cardboard_box(*sorted((s * -2240, s * -2040)), 1380, 1560, 160, 'n', 'box_xmas')
    smdl(s, 'padtv/padtv2.md3', -2190, 380, 0, 0.7, 0, solid=True)
    smdl(s, 'pad_ddmix/padshop/cardboard_standup.md3', -2200, -420, 0, 0.9, 0, solid=True)
    smdl(s, 'pad_ddmix/attic/kaspad.md3', -2160, 0, 0, 1.0, 0)
    smdl(s, 'pad_ddmix/backyard/tire.md3', -1900, -1480, 0, 0.9, 90, solid=True)
    smdl(s, 'pad_ddmix/attic/pumper.md3', -1950, 650, 0, 1.0, 20)
    item(s, 'ammo_balloony', -2200, 720, 0)
    spad(s, -2000, 260, 0, (-1540, 20, CAT_Z), 1290, 'rafters_' + team)
    item(s, 'ammo_splasher', -2150, -640, 0)
    for (x, y) in ((-2000, -600), (-2000, 600), (-2000, -1300), (-2000, 1300)):
        slight(s, x, y, 380, 520)


def floor_strips():
    for s in (1, -1):
        team = 'red' if s > 0 else 'blue'
        spad(s, -900, -1420, 0, (-900, -1110, TZ), 545, 'kick_s_' + team)
        spad(s, -900, 1420, 0, (-900, 1110, TZ), 545, 'kick_n_' + team)
        cardboard_box(*sorted((s * -1500, s * -1320)), -1660, -1480, 140, 'n', 'box_books')
        cardboard_box(*sorted((s * -400, s * -240)), 1600, 1760, 120, 's', 'box_trains')
        smdl(s, 'pad_ddmix/trashcan/garbage_bag_group.md3', -1300, 1600, 0, 1.0, 40)
        smdl(s, 'pad_radio_car/radio_control.md3', -600, -1640, 0, 1.0, 60)
        item(s, 'ammo_boaster', -600, 1560, 0)
        item(s, 'ammo_nipper', -1300, -1460, 0)
        cardboard_box(*sorted((s * -1100, s * -900)), 1560, 1720, 150, 's', 'box_xmas')
        cardboard_box(*sorted((s * -1100, s * -940)), -1720, -1560, 130, 'n', 'box_trains')
        for (x, y) in ((-1200, -1500), (-400, -1500), (-1200, 1500), (-400, 1500)):
            slight(s, x, y, 230, 420)


def rolled_rug():
    pts = [(x, -1560 + 40 * math.cos(2 * math.pi * k / 10), 40 + 40 * math.sin(2 * math.pi * k / 10)) for x in (-300, 300) for k in range(10)]
    A(hull(pts, {'side': T('carpet'), 'top': T('carpet'), 'bot': T('carpet')}, round_pts=True))


def hatch():
    hx, hy = HATCH
    x0, x1, y0, y1, zf = -256, 256, 1344, 1728, -352
    wl = {'side': T('wallpaper'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - 32, y0 - 32, zf - 32), (x1 + 32, y1 + 32, zf), {'top': T('carpet'), 'side': CAULK, 'bot': CAULK}))
    A(box((x0 - 32, y0 - 32, zf), (x0, y1 + 32, -32), wl)); A(box((x1, y0 - 32, zf), (x1 + 32, y1 + 32, -32), wl))
    A(box((x0, y0 - 32, zf), (x1, y0, -32), wl)); A(box((x0, y1, zf), (x1, y1 + 32, -32), wl))
    # trap door lid hinged open on the north side of the hatch (decor)
    A(hull([(x, y, z) for x in (hx - 64, hx + 64) for (y, z) in ((hy + 64, 0), (hy + 72, 0), (hy + 100, 124), (hy + 92, 126))],
           {'side': T('floorboards'), 'top': T('floorboards'), 'bot': T('floorboards')}, round_pts=False))
    # pull-down ladder (decor, nonsolid) and a kicker back up through the hatch
    jumppad(hx, hy + 34, zf, (hx, hy - 170, 0), 260, 'hatch_up')
    item(1, 'item_padpower', 150, 1430, zf)
    item(1, 'ammo_betty', -150, 1430, zf)
    item(1, 'ammo_nipper', 0, 1700, 0)
    A(box((-232, 1600, zf), (-120, 1704, zf + 80), {'side': T('wicker'), 'top': T('wicker'), 'bot': CAULK}))
    mdl_c('pad_lamps/gooseneck.md3', 180, 1660, zf, 0.8, 200)
    light(0, 1450, -120, 420, '1 0.85 0.6')
    light(hx, hy, -60, 300, '1 0.85 0.6')


def spawns():
    for s in (1, -1):
        team = 'red' if s > 0 else 'blue'
        for (x, y, z, a) in ((-1140, -180, 416, 90), (-842, -40, 416, 270), (-1300, 300, TZ, 0), (-1450, -60, TZ, 0)):
            spawn(s, 'team_%splayer' % team, x, y, z, a)
        for (x, y, z, a) in ((-1300, -700, TZ, 90), (-1260, 700, TZ, 270), (-620, -640, TZ, 45), (-1100, 420, 0, 0),
                             (-2000, -300, 0, 0), (-2050, 120, 0, 0)):
            spawn(s, 'team_%sspawn' % team, x, y, z, a)
        for (x, y, z, a) in ((-1500, 0, 0, 0), (-600, -1500, 0, 90), (-600, 1460, 0, 270), (-2100, 1250, 0, 0),
                             (-640, -150, TZ, 0), (-1200, -400, 0, 0), (-450, 700, MPL, 270), (-1700, -1300, 0, 90)):
            spawn(s, 'info_player_deathmatch', x, y, z, a)
    M.ent('info_player_intermission', (-1900, -1500, 1100), angles='22 35 0')


def ambience():
    speaker(0, 0, 1500, 'sound/world/ambient/wind_night.ogg')
    speaker(-1000, 0, 200, 'sound/world/ambient/floor_creaking.ogg', loop=False, targetname='creak')
    speaker(1000, 0, 200, 'sound/world/ambient/floor_creaking.ogg', loop=False, targetname='creak')
    M.ent('func_timer', (0, -200, 300), target='creak', wait=35, random=15, spawnflags=1)


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    hull_box(); floor_and_walls(); rafters(); table(); ballast_ring(); mountain(); town_hall(); village(); pond()
    for s in (1, -1):
        station(s); scenery(s); gable_end(s)
    under_table(); floor_strips(); rolled_rug(); hatch(); spawns(); ambience()
    train()
    train_sweep_check()
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/padattic/build_padattic.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
