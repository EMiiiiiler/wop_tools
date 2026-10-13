#!/usr/bin/env python3
"""Fish Tank Temple - World of Padman Capture the Lolly map generator (map 'wop_padtank').

    OUT=/path/to/out python3 build_padtank.py

Writes <OUT>/maps/wop_padtank.map, textures/padtank/*, models/padtank/* (swimming fish), scripts/padtank.shader and
scripts/wop_padtank.arena.

Inside a giant aquarium at Padman scale (catalog models at 1.0). x east, y north, gravel at z 0, the water surface
(seen from below) is the ceiling at z 1664. The whole tank is one fog volume (blue haze) - breathable "water"; only
the Blue Hole in the middle is real, swimmable water.
The map is point-symmetric about (0, 0): every red-side piece is built by a function taking s = +1 (red, west) and
rotated 180 degrees for blue (s = -1, east).
  bases     sunken sandstone temples with a stone face on the front (mouth = door, glowing team eyes), the team
            lolly inside (3 doors), outside stairs to the roof; a roof bubble-lift to the aquarium filter (Boaster)
  causeway  stone walkway on pillars from each temple roof over the Blue Hole to the ring around the central rock
            spire; stairs down to the gravel on both sides
  centre    the Blue Hole: deep pool (Betty + Pad Power on the bottom), rock spire (Imperius on top, bubble lifts
            from the ring), stone steps out of the water under the causeways
  north/south  red reef (rock mesa + coral plate spiral to a sniper perch, Splasher) / blue diving bell (enter
            through two hatches, climb the coral plates or ride the bubble lift to the roof, Pumper); point-symmetric
            so each lane has one of each; treasure chests mid-lane (enterable, gold-bar steps to the lid)
  fish      func_rotating movers carrying IQM models: leopard sharks circling the tank, a whale shark, a blue-tang
            school round the spire and round each diving bell, angel fish in the Blue Hole
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import tank_textures as TX
import fish_models as FM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padtank'
T = lambda n: 'padtank/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; NODRAW = 'common/nodraw'
ORIGIN = 'common/origin'; NODRAW_NS = T('nodraw_ns')

for k, v in {'gravel': (1, 1), 'sand': (1, 1), 'rock': (1, 1), 'rock_dark': (1, 1), 'rock_moss': (1, 1), 'sandstone': (0.75, 0.75),
             'sandstone_big': (1, 1), 'sandstone_plain': (1, 1), 'flagstone': (1, 1), 'face_stone': (0.75, 0.75), 'key_band': (0.5, 0.5),
             'pillar': (0.5, 1), 'coral_stalk': (0.5, 0.5), 'brass': (0.75, 0.75), 'bell_roof': (1, 1), 'chest_wood': (0.75, 0.75),
             'gold': (0.5, 0.5), 'coins': (0.5, 0.5), 'surface': (2, 2), 'water': (2, 2), 'glass': (2, 2), 'room_wall': (4, 4),
             'room_floor': (2, 2), 'filter_body': (0.75, 0.75), 'filter_plain': (1, 1), 'kelp': (1, 1), 'kelp2': (1, 1),
             'bubbles': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v
for c in ('purple', 'magenta', 'green', 'blue', 'red', 'yellow', 'orange'):
    wopmap.TEXSCALE[T('coral_' + c)] = (0.75, 0.75)

M = Map({'message': TX.LONGNAME, '_ambient': '12', '_color': '0.8 0.92 1', 'gridsize': '96 96 96', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
TXI, TYI = 2560, 1216            # tank interior half sizes (glass inner faces); the reef poster panel is 4u thick on the north
TYN = TYI - 4                    # poster face
CZ = 1664                        # water surface (ceiling)
BZ = -480                        # bottom of the gravel fill
PR, PZ = 512, -448               # Blue Hole radius (16-gon), pool floor
OX, OYS, OZ = 3072, -1856, CZ + 384   # outer room (behind the glass)
# temples (red values; blue = rotated)
TX0, TX1, TY = -2240, -1664, 288      # temple outer x range, half width
TFL, TWZ, TRZ = 32, 224, 256          # temple floor, wall top, roof top
CW, CZ0 = 80, 224                     # causeway half width, slab bottom (top = TRZ)
SP_R0, SP_R1, SP_R2, SP_TOP = 208, 176, 144, 640    # spire radii (pool floor / deck / top) and top height
DECK_R = 352
FILTER_Z = 768
BELL = (-1000, -800)                  # red diving bell centre
BELL_R, BELL_H = 240, 256
CHEST_Y = (776, 1000)                 # red chest (north, x -192..192)
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
LOOPS = []


# =================================================================================================== helpers
def rtex(s, tex):
    if s > 0 or not isinstance(tex, dict): return tex
    sw = {'n': 's', 's': 'n', 'e': 'w', 'w': 'e'}
    return {sw.get(k, k): v for k, v in tex.items()}


def sb(s, x0, y0, z0, x1, y1, z1, tex, detail=True):
    xa, xb = sorted((s * x0, s * x1)); ya, yb = sorted((s * y0, s * y1))
    return box((round(xa), round(ya), z0), (round(xb), round(yb), z1), rtex(s, tex), detail)


def sh(s, pts, tex, rnd=True):
    return hull([(s * x, s * y, z) for (x, y, z) in pts], rtex(s, tex), round_pts=rnd)


def scyl(s, x, y, r, z0, z1, tex, n=12, phase=None):
    return cyl(s * x, s * y, r, z0, z1, rtex(s, tex), n, phase=phase)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=12, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex)


def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """(x,y) = where the model's bounding-box centre should land (several models have off-centre origins)"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12):
    """mdl_c + a weapon-clip box around the model's rotated bounds so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    z1 = oz + b['max'][2] * scale
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - 4)), WCLIP))
    return e


def smdl(s, path, x, y, zsurf, scale=1.0, angle=0, solid=False, shrink=0.12):
    ang = (angle + (180 if s < 0 else 0)) % 360
    if solid: return solid_mdl(path, s * x, s * y, zsurf, scale, ang, shrink)
    return mdl_c(path, s * x, s * y, zsurf, scale, ang)


def light(x, y, z, val, color='0.85 0.95 1', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def slight(s, x, y, z, val, color='0.85 0.95 1'):
    light(s * x, s * y, z, val, color)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def item(s, cls, x, y, floor, **kw):
    M.ent(cls, (round(s * x), round(s * y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, s * x, s * y, floor))


def weapon(s, w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(s * x), round(s * y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, s * x, s * y, floor))


def spawn(s, cls, x, y, floor, ang):
    M.ent(cls, (round(s * x), round(s * y), floor + 25), angle=(ang + (180 if s < 0 else 0)) % 360)
    SPOTS['spawn'].append((s * x, s * y, floor))


def ssign(s, mn, mx, tex, tw, th, facing, back):
    """sign_box given in red-side coordinates, rotated 180 degrees for blue"""
    if s > 0: return sign_box(mn, mx, tex, tw, th, back=back, facing=facing)
    sw = {'n': 's', 's': 'n', 'e': 'w', 'w': 'e'}
    return sign_box((-mx[0], -mx[1], mn[2]), (-mn[0], -mn[1], mx[2]), tex, tw, th, back=back, facing=''.join(sw[c] for c in facing))


def ring_pts(cx, cy, r, z, n=16, ph=None):
    return [(x, y, z) for (x, y) in ngon(cx, cy, r, n, ph)]


def jumppad(x, y, z, land, apex, name, glow=True, bubbles=True):
    """bubble lift: air-stone disc (r 34) + trigger_push + target_position. Q3 AimAtTarget: target = apex of the flight,
    measured from the trigger centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way
    to `land` (x, y, floor z)."""
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
    if glow: light(x, y, z + 48, 110, '0.5 0.85 1')
    if bubbles:      # rising bubble column above the trigger (nonsolid sprite, starts above the trigger box)
        A(bubble_column(x, y, z + 74, z + 74 + min(320, int(apex - z - 120))))
    speaker(x, y, z + 40, 'sound/world/ambient/water_bubbling.ogg')


def bubble_column(x, y, z0, z1, w=24):
    b = box((x - w, y - 1, z0), (x + w, y + 1, z1), {'n': T('bubbles'), 's': T('bubbles'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS})
    for f in b.faces:
        if f.tex == T('bubbles'): f.sc = (w * 2 / 128, 0.75)
    return b


def spad(s, x, y, z, land, apex, name):
    jumppad(s * x, s * y, z, (s * land[0], s * land[1], land[2]), apex, name)


def kelp(x, y, h, z=0, tex='kelp', w=64, ang=0):
    """two crossing single-sided sway sprites (nonsolid), base on the surface z"""
    out = []
    for k in range(2):
        a = math.radians(ang + 90 * k)
        dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        nx, ny = -math.sin(a), math.cos(a)
        q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx * 2, y + dy + ny * 2), (x - dx + nx * 2, y - dy + ny * 2)]
        def tf(n, nx=nx, ny=ny):
            return T(tex) if (n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
        b = hull([(px, py, zz) for (px, py) in q for zz in (z, z + h)], tf, round_pts=False)
        for f in b.faces:
            if f.tex == T(tex):
                f.sc = (w / 128, h / 512); f.off = (0, 0)
        out.append(b)
    A(out)


def skelp(s, x, y, h, z=0, tex='kelp', w=64, ang=0):
    kelp(s * x, s * y, h, z, tex, w, ang)


def rock(cx, cy, rx, ry, h, z=0, seed=0, tex=None, n=9, topflat=0.55):
    """irregular boulder: hull of a jittered ring at the base, a smaller ring higher up and a few top points"""
    rr = np.random.default_rng(seed)
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + rr.uniform(-0.25, 0.25)) / n
        f = rr.uniform(0.85, 1.05)
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a), z))
        f2 = rr.uniform(0.6, 0.85)
        pts.append((cx + rx * f2 * math.cos(a + 0.3), cy + ry * f2 * math.sin(a + 0.3), z + h * rr.uniform(0.45, 0.7)))
    for k in range(4):
        a = 2 * math.pi * k / 4 + rr.uniform(0, 1)
        pts.append((cx + rx * topflat * 0.5 * math.cos(a), cy + ry * topflat * 0.5 * math.sin(a), z + h * rr.uniform(0.9, 1.0)))
    return hull(pts, tex or {'top': T('rock_moss'), 'side': T('rock'), 'bot': CAULK})


def srock(s, cx, cy, rx, ry, h, z=0, seed=0, tex=None):
    A(rock(s * cx, s * cy, rx, ry, h, z, seed, rtex(s, tex) if tex else None))


CORALS = ['purple', 'magenta', 'green', 'blue', 'red', 'yellow', 'orange']


def tubes(x, y, z, seed, n=4, hmax=96):
    """tube sponge cluster (like the purple tubes in a reef): n separate 8-gon tubes, no overlaps"""
    rr = np.random.default_rng(seed)
    col = CORALS[seed % len(CORALS)]
    placed = []
    for k in range(n * 3):
        if len(placed) >= n: break
        a = rr.uniform(0, 2 * math.pi); d = 0 if not placed else rr.uniform(26, 46)
        r = rr.uniform(9, 15); px, py = x + d * math.cos(a), y + d * math.sin(a)
        if any(math.hypot(px - qx, py - qy) < r + qr + 3 for (qx, qy, qr) in placed): continue
        placed.append((px, py, r))
        h = rr.uniform(0.45, 1.0) * hmax
        A(cyl(round(px), round(py), r, z, z + round(h), {'side': T('coral_' + col), 'top': T('coral_stalk'), 'bot': CAULK}, 8))


def brain(x, y, z, r, seed):
    col = CORALS[(seed * 3) % len(CORALS)]
    A(hull([(px, py, z) for (px, py) in ngon(x, y, r, 10)] + [(px, py, z + r * 0.45) for (px, py) in ngon(x, y, r * 0.8, 10, 18)] +
           [(px, py, z + r * 0.7) for (px, py) in ngon(x, y, r * 0.4, 6)], {'side': T('coral_' + col), 'top': T('coral_' + col), 'bot': CAULK}))


def inside_brush(b, p, eps=0.5):
    return all(n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - d < -eps for (n, d) in b.planes())


# =================================================================================================== tank shell
def tank_shell():
    W = 16
    # outer room (structural hull): floor, ceiling, walls; the tank's north glass carries the reef poster
    A(box((-OX - W, OYS - W, BZ - 16), (OX + W, TYI + 32, BZ), {'top': T('room_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((-OX - W, OYS - W, OZ), (OX + W, TYI + 32, OZ + 16), {'bot': T('tank_frame'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((-OX - W, TYI, BZ), (OX + W, TYI + 32, OZ), {'side': CAULK, 's': T('room_wall')}, detail=False))
    A(box((-OX - W, OYS - W, BZ), (OX + W, OYS, OZ), {'side': CAULK, 'n': T('room_wall')}, detail=False))
    A(box((OX, OYS, BZ), (OX + W, TYI, OZ), {'side': CAULK, 'w': T('room_wall')}, detail=False))
    A(box((-OX - W, OYS, BZ), (-OX, TYI, OZ), {'side': CAULK, 'e': T('room_wall')}, detail=False))
    # reef poster on the inside of the back glass (fitted, 4u panel)
    A(sign_box((-TXI, TYN, 0), (TXI, TYI, CZ), T('reef_poster'), 2048, 512, back=T('tank_frame'), facing='s'))
    # glass: south (front) and the two ends, from the stand to the top rim
    A(box((-TXI - 16, -TYI - 16, BZ), (TXI + 16, -TYI, CZ + 32), T('glass')))
    A(box((-TXI - 16, -TYI, BZ), (-TXI, TYI, CZ + 32), T('glass')))
    A(box((TXI, -TYI, BZ), (TXI + 16, TYI, CZ + 32), T('glass')))
    # black plastic frame: bottom rail outside the glass, top rim, corner posts
    fr = T('tank_frame')
    A(box((-TXI - 48, -TYI - 48, BZ), (TXI + 48, -TYI - 16, 24), fr))
    A(box((-TXI - 48, -TYI - 16, BZ), (-TXI - 16, TYI, 24), fr)); A(box((TXI + 16, -TYI - 16, BZ), (TXI + 48, TYI, 24), fr))
    A(box((-TXI - 48, -TYI - 48, CZ - 24), (TXI + 48, -TYI - 16, CZ + 64), fr))
    A(box((-TXI - 48, -TYI - 16, CZ - 24), (-TXI - 16, TYI, CZ + 64), fr)); A(box((TXI + 16, -TYI - 16, CZ - 24), (TXI + 48, TYI, CZ + 64), fr))
    for sx in (-1, 1):
        x0 = TXI + 16 if sx > 0 else -TXI - 48
        A(box((x0, -TYI - 48, 24), (x0 + 32, -TYI - 16, CZ - 24), fr))
    # the water surface seen from below (ceiling) + lid above it
    A(box((-TXI, -TYI, CZ), (TXI, TYN, CZ + 32), {'bot': T('surface'), 'side': CAULK, 'top': CAULK}))
    A(box((-TXI - 48, -TYI - 48, CZ + 64), (TXI + 48, TYI, CZ + 96), {'bot': fr, 'side': fr, 'top': CAULK}))
    # outer room lights (warm, dim)
    for (x, y) in ((-1800, -1500), (0, -1500), (1800, -1500), (-2850, 0), (2850, 0)):
        light(x, y, 900, 900, '1 0.85 0.65')
    # fog volume = the tank's water, from the gravel to the surface
    A(box((-TXI, -TYI, 0), (TXI, TYN, CZ), T('fog')))


def ground():
    """gravel fill from BZ to 0 around the Blue Hole: 16 convex sectors between the pool 16-gon and the tank walls"""
    n = 16
    angs = [math.radians(11.25 + 22.5 * i) for i in range(n)]
    P = [(PR * math.cos(a), PR * math.sin(a)) for a in angs]

    def hit(a):
        c, s_ = math.cos(a), math.sin(a)
        t = min(TXI / abs(c) if abs(c) > 1e-9 else 1e9, TYN / abs(s_) if abs(s_) > 1e-9 else 1e9)
        return (t * c, t * s_)
    corners = [(TXI, TYN), (-TXI, TYN), (-TXI, -TYI + 0.0), (TXI, -TYI)]
    # the south interior face is at -TYI, the north at TYN (poster); use exact walls
    def hit2(a):
        c, s_ = math.cos(a), math.sin(a)
        ty = TYN if s_ > 0 else TYI
        t = min(TXI / abs(c) if abs(c) > 1e-9 else 1e9, ty / abs(s_) if abs(s_) > 1e-9 else 1e9)
        return (t * c, t * s_)
    cang = [(math.atan2(cy, cx) % (2 * math.pi), (cx, cy)) for (cx, cy) in ((TXI, TYN), (-TXI, TYN), (-TXI, -TYI), (TXI, -TYI))]
    for i in range(n):
        a0, a1 = angs[i], angs[(i + 1) % n]
        a1u = a1 if a1 > a0 else a1 + 2 * math.pi
        poly = [P[i], hit2(a0)]
        for (ca, cp) in sorted(cang):
            for cc in (ca, ca + 2 * math.pi):
                if a0 < cc < a1u: poly.append(cp)
        poly += [hit2(a1), P[(i + 1) % n]]
        mid = ((P[i][0] + P[(i + 1) % n][0]) / 2, (P[i][1] + P[(i + 1) % n][1]) / 2)
        L = math.hypot(*mid); ux, uy = mid[0] / L, mid[1] / L

        def tf(nn, ux=ux, uy=uy):
            if nn[2] > 0.7: return T('gravel')
            if nn[2] < -0.7: return CAULK
            return T('rock_dark') if (nn[0] * ux + nn[1] * uy) < -0.9 else CAULK
        A(hull([(x, y, z) for (x, y) in poly for z in (BZ, 0)], tf))
    # pool floor + water
    A(cyl(0, 0, PR, BZ, PZ, {'top': T('sand'), 'side': CAULK, 'bot': CAULK}, 16))
    A(cyl(0, 0, PR, PZ, 0, T('water'), 16))


# =================================================================================================== Blue Hole + spire
def spire():
    rk = {'side': T('rock_moss'), 'top': T('rock_moss'), 'bot': CAULK}
    rr = np.random.default_rng(7)
    def jring(n, r0, r1, z, ph=0.0):
        return [((rr.uniform(r0, r1)) * math.cos(ph + 2 * math.pi * (k + rr.uniform(-0.2, 0.2)) / n),
                 (rr.uniform(r0, r1)) * math.sin(ph + 2 * math.pi * (k + rr.uniform(-0.2, 0.2)) / n), z) for k in range(n)]
    deck_ring = [(x, y, z) for (x, y) in ngon(0, 0, SP_R1, 12) for z in (CZ0,)]
    # under water: a rough rock base narrowing to the deck's 12-gon
    A(hull(jring(10, 190, 212, PZ) + jring(10, 192, 208, -200, 0.3) + deck_ring, rk))
    A(cyl(0, 0, SP_R1, CZ0, TRZ, T('rock_moss'), 12))
    # above the deck: two craggy chunks, the top one flat (Imperius)
    mid = [(round(x), round(y), z) for (x, y, z) in jring(9, 150, 168, 470, 0.5)]
    A(hull([(x, y, TRZ) for (x, y) in ngon(0, 0, SP_R1, 12)] + jring(9, 160, 176, 360, 0.2) + mid, rk))
    A(hull(mid + jring(9, 140, 160, 560, 0.9) + jring(8, 122, 140, SP_TOP, 0.4), {'side': T('rock_moss'), 'top': T('rock_moss'), 'bot': CAULK}))
    # ring deck (12 wedges between the spire and r 352)
    inner = ngon(0, 0, SP_R1, 12); outer = ngon(0, 0, DECK_R, 12)
    for k in range(12):
        q = [inner[k], outer[k], outer[(k + 1) % 12], inner[(k + 1) % 12]]
        A(hull([(x, y, z) for (x, y) in q for z in (CZ0, TRZ)], {'top': T('flagstone'), 'side': T('key_band'), 'bot': T('sandstone_plain')}))
    # decorative pillars under the deck's diagonal corners (standing on the pool floor)
    for a in (45, 135, 225, 315):
        x, y = 260 * math.cos(math.radians(a)), 260 * math.sin(math.radians(a))
        A(box((round(x) - 28, round(y) - 28, PZ), (round(x) + 28, round(y) + 28, CZ0), T('pillar')))
    # low posts around the deck rim (cover), not where the causeways or the lifts are
    for k in range(12):
        a = 15 + 30 * k
        if a in (165, 195, 345, 15): continue           # beside the causeway joints
        x, y = 326 * math.cos(math.radians(a)), 326 * math.sin(math.radians(a))
        A(box((round(x) - 12, round(y) - 12, TRZ), (round(x) + 12, round(y) + 12, TRZ + 40),
              {'side': T('sandstone_plain'), 'top': T('sandstone_plain'), 'bot': CAULK}))
    # bubble lifts from the ring to the top of the spire (60 / 240 deg)
    for s in (1, -1):
        a = math.radians(60)
        spad(s, 266 * math.cos(a), 266 * math.sin(a), TRZ, (40 * math.cos(a), 40 * math.sin(a), SP_TOP), 880, 'spire_%s' % ('r' if s > 0 else 'b'))
    # tube sponges on the ring (cover)
    for s in (1, -1):
        a = math.radians(125 if s > 0 else 305)
        tubes(round(250 * math.cos(a)), round(250 * math.sin(a)), TRZ, 3 if s > 0 else 4, 4, 80)
    # loot
    weapon(1, 'imperius', 0, 0, SP_TOP, 'purple')
    item(1, 'team_CTL_neutrallolly', 0, 268, TRZ)
    for s in (1, -1):
        item(s, 'ammo_imperius', -268, -70 if s > 0 else -70, TRZ)
    light(0, 0, SP_TOP + 200, 700, '1 0.97 0.9')
    for a in (30, 120, 210, 300):
        light(300 * math.cos(math.radians(a)), 300 * math.sin(math.radians(a)), TRZ + 120, 380, '1 0.95 0.85')


def blue_hole():
    # stone steps out of the water under each causeway (west for red, east for blue), from -224 up to the gravel
    for s in (1, -1):
        for b in stairs(-502, -64, -278, 64, -224, 0, 'w', {'top': T('sandstone_plain'), 'side': T('sandstone')}, base=PZ, thick=64):
            mn, mx = b.bounds()
            A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], {'top': T('sandstone_plain'), 'side': T('sandstone'), 'bot': CAULK}))
    # bottom loot (equally far from both bases)
    weapon(1, 'betty', 0, 400, PZ, 'black')
    item(1, 'item_padpower', 0, -400, PZ)
    for s in (1, -1):
        item(s, 'ammo_betty', -330, -300, PZ)
    # sunken treasure on the bottom
    mdl_c('pad_ddmix/padship/amphora.md3', 300, 300, PZ, 0.8, 30)
    mdl_c('pad_ddmix/padship/amphora.md3', -300, -300, PZ, 0.8, 210)
    mdl_c('pad_ddmix/jail/skull.md3', -330, 250, PZ, 0.8, 300)
    mdl_c('pad_ddmix/door/ancient_key_lying.md3', 120, -330, PZ, 1.5, 40)
    for (x, y) in ((0, 360), (0, -360), (330, 0), (-330, 0)):
        light(x, y, -250, 420, '0.45 0.8 1')
    speaker(0, 0, -100, 'sound/world/ambient/water_bubble.ogg')
    # kelp on the bottom of the hole
    for (x, y, h) in ((260, 380, 300), (-260, -380, 300), (380, -230, 260), (-380, 230, 260)):
        kelp(x, y, h, PZ, 'kelp2')


def carve_water():
    wi = next(i for i, b in enumerate(M.world) if T('water') in b.textures())
    wb = M.world[wi]
    wmn, wmx = wb.bounds()
    cut = []
    for i, b in enumerate(M.world):
        if i == wi or not b.is_solid(): continue
        if b.textures() <= {NODRAW_NS, T('kelp'), T('kelp2'), T('bubbles')}: continue
        mn, mx = b.bounds()
        if np.all(mn < wmx - 0.5) and np.all(mx > wmn + 0.5): cut.append(b)
    pieces = carve(wb, cut, T('water'))
    for b in pieces:
        for f in b.faces:
            f.tex = T('water') if (f.n[2] > 0.99 and abs(f.d) < 0.01) else T('water_inner')
    M.world[wi:wi + 1] = pieces
    print('water pieces', len(pieces), 'cutters', len(cut))


# =================================================================================================== causeways
def causeway(s):
    top = {'top': T('flagstone'), 'side': T('key_band'), 'bot': T('sandstone_plain')}
    A(sb(s, TX1, -CW, CZ0, -DECK_R * math.cos(math.radians(15)), CW, TRZ, top))
    for px in (-1424, -1136, -848, -624):
        A(sb(s, px - 32, -32, 0, px + 32, 32, 192, T('pillar')))
        A(sb(s, px - 48, -48, 192, px + 48, 48, CZ0, {'side': T('sandstone'), 'top': CAULK, 'bot': T('sandstone_plain')}))
    # low edge posts (cover), skipping the stair landings and the temple joint
    for x in range(-1600, -400, 192):
        for sy in (1, -1):
            if sy > 0 and -1340 < x < -1150: continue
            if sy < 0 and -1610 < x < -1430: continue
            A(sb(s, x, sy * (CW - 24), TRZ, x + 24, sy * CW, TRZ + 40, {'side': T('sandstone_plain'), 'top': T('sandstone_plain'), 'bot': CAULK}))
    # stairs down to the gravel: north (x -1312..-1184) and south (x -1584..-1456) for red
    st = {'top': T('flagstone'), 'side': T('sandstone')}
    for b in stairs(-1312, CW, -1184, CW + 512, 0, TRZ, 's', st):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], {'top': T('flagstone'), 'side': T('sandstone'), 'bot': CAULK}))
    for b in stairs(-1584, -CW - 512, -1456, -CW, 0, TRZ, 'n', st):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], {'top': T('flagstone'), 'side': T('sandstone'), 'bot': CAULK}))
    for x in (-1280, -880, -560):
        slight(s, x, 0, 120, 260, '1 0.9 0.75')        # under the walkway
    for x in (-1400, -1000, -600):
        slight(s, x, 0, TRZ + 140, 300, '1 0.95 0.85')
    # loot on the walkway
    item(s, 'ammo_nipper', -1040, 40, TRZ)
    item(s, 'ammo_bubbleg', -720, -40, TRZ)


# =================================================================================================== temples
def temple(s):
    team = 'red' if s > 0 else 'blue'
    ss = {'side': T('sandstone'), 'top': T('sandstone_plain'), 'bot': CAULK}
    big = {'side': T('sandstone_big'), 'top': T('sandstone_plain'), 'bot': T('sandstone_plain')}
    xm = (TX0 + TX1) / 2                                   # -1952
    # plinth: step 1 (z 0..16) wider all round (64 at the front for the columns), step 2 = floor slab under the walls
    A(sb(s, TX0 - 32, -TY - 32, 0, TX1 + 64, TY + 32, 16, ss))
    A(sb(s, TX0, -TY, 16, TX1, TY, TFL, {'side': T('sandstone'), 'top': T('flagstone'), 'bot': CAULK}))
    # walls (32 thick, z 32..224) with doors: front mouth y -64..64 (z ..160), north/south x xm-64..xm+64 (z ..160)
    A(sb(s, TX0, -TY, TFL, TX0 + 32, TY, TWZ, big))
    A(sb(s, TX1 - 32, -TY, TFL, TX1, -64, TWZ, big)); A(sb(s, TX1 - 32, 64, TFL, TX1, TY, TWZ, big))
    A(sb(s, TX1 - 32, -64, 160, TX1, 64, TWZ, big))
    for (y0, y1) in ((TY - 32, TY), (-TY, -TY + 32)):
        A(sb(s, TX0 + 32, y0, TFL, xm - 64, y1, TWZ, big)); A(sb(s, xm + 64, y0, TFL, TX1 - 32, y1, TWZ, big))
        A(sb(s, xm - 64, y0, 160, xm + 64, y1, TWZ, big))
    # roof slab with the meander band round its edge
    A(sb(s, TX0, -TY, TWZ, TX1, TY, TRZ, {'top': T('flagstone'), 'side': T('key_band'), 'bot': T('sandstone_plain')}))
    # ---- the stone face on the front wall (x = TX1 outward)
    fs = {'side': T('face_stone'), 'top': T('face_stone'), 'bot': T('face_stone')}
    for sy in (1, -1):
        A(sb(s, TX1, sy * 96, 196, TX1 + 24, sy * 224, 216, fs))                       # brows
        A(sb(s, TX1, sy * 80, 104, TX1 + 16, sy * 224, 128, fs))                       # cheekbones
        ey0, ey1 = sorted((sy * 112, sy * 208))
        A(ssign(s, (TX1, ey0, 140), (TX1 + 2, ey1, 188), T('eye_' + team), 128, 128, 'e', T('face_stone')))
    A(sh(s, [(TX1, -36, 216), (TX1, 36, 216), (TX1, -36, 164), (TX1, 36, 164), (TX1 + 48, -28, 164), (TX1 + 48, 28, 164)], fs))   # nose
    for k in range(4):                                                                  # teeth along the top of the mouth
        y0 = -56 + k * 30
        A(sb(s, TX1 - 8, y0, 144, TX1, y0 + 20, 160, T('sandstone_plain')))
    A(sb(s, TX1, -96, 16, TX1 + 32, 96, TFL, fs))                                      # chin / lip = entry step
    # columns on the front corners (standing on step 1) with capitals below the roof line
    for sy in (1, -1):
        A(scyl(s, TX1 + 32, sy * 256, 24, 16, TWZ, T('pillar'), 12))
        A(sb(s, TX1 + 2, sy * 224, TWZ, TX1 + 62, sy * 288, TWZ + 20, {'side': T('key_band'), 'top': T('sandstone_plain'), 'bot': T('sandstone_plain')}))
    # name plaques above the side doors, team banners beside them
    for sy in (1, -1):
        if sy > 0: A(ssign(s, (xm - 128, TY, 164), (xm + 128, TY + 4, 220), T('plaque_' + team), 512, 128, 'n', T('sandstone_plain')))
        else: A(ssign(s, (xm - 128, -TY - 4, 164), (xm + 128, -TY, 220), T('plaque_' + team), 512, 128, 's', T('sandstone_plain')))
        for bx in (xm - 190, xm + 190):
            yb0, yb1 = sorted((sy * TY, sy * (TY + 2)))
            A(sb(s, bx - 40, yb0, 40, bx + 40, yb1, 210, {'n': T('banner_' + team), 's': T('banner_' + team), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS}))
    # ---- interior: lolly on a low dais, two altars (cover), health station, amphorae in the corners
    A(sb(s, xm - 64, -64, TFL, xm + 64, 64, TFL + 16, {'side': T('key_band'), 'top': T('sandstone_plain'), 'bot': CAULK}))
    lol = 'team_CTL_%slolly' % team
    M.ent(lol, (s * xm, 0, TFL + 16 + 16))
    SPOTS['item'].append((lol, s * xm, 0, TFL + 16))
    for sy in (1, -1):
        A(sb(s, xm - 40, sy * 150 - 32, TFL, xm + 40, sy * 150 + 32, TFL + 56, {'side': T('face_stone'), 'top': T('sandstone_plain'), 'bot': CAULK}))
    M.ent('station_health', (s * (TX0 + 72), s * -180, TFL), angle=(0 if s > 0 else 180))
    smdl(s, 'pad_ddmix/padship/amphora.md3', TX0 + 80, 200, TFL, 0.55, 20, solid=True)
    smdl(s, 'pad_ddmix/padship/amphora.md3', TX1 - 90, 200, TFL, 0.5, 200, solid=True)
    smdl(s, 'pad_ddmix/padship/amphora.md3', TX1 - 90, -200, TFL, 0.5, 120, solid=True)
    item(s, 'ammo_balloony', xm + 120, -60, TFL)
    item(s, 'item_armor_shard', TX0 + 80, 40, TFL)
    slight(s, xm, 0, 190, 300, '1 0.85 0.6')
    slight(s, xm, 150, 150, 160, '1 0.8 0.55'); slight(s, xm, -150, 150, 160, '1 0.8 0.55')
    slight(s, TX1 + 120, 0, 120, 350, '1 0.9 0.8')
    # ---- outside stairs on the outboard side: up the back (rising north) to a landing tower, then onto the roof
    stt = {'top': T('flagstone'), 'side': T('sandstone'), 'bot': CAULK}
    for b in stairs(TX0 - 160, -448, TX0 - 32, 64, 0, TRZ, 'n', stt):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], stt))
    A(sb(s, TX0 - 160, 64, 0, TX0 - 32, TY, TRZ, {'top': T('flagstone'), 'side': T('sandstone_big'), 'bot': CAULK}))
    A(sb(s, TX0 - 32, 64, TRZ - 16, TX0, TY, TRZ, {'top': T('flagstone'), 'side': T('sandstone'), 'bot': T('sandstone_plain')}))
    # ---- roof: Balloony, bubble lift to the filter box behind
    weapon(s, 'balloony', TX1 - 140, -200, TRZ, 'green')
    item(s, 'ammo_nipper', TX1 - 140, 200, TRZ)
    spad(s, TX0 + 120, -150, TRZ, (-TXI + 80, -40, FILTER_Z), 1010, '%s_filter' % team)
    # ---- team spawns: around the temple, on the roof; none inside the lolly room
    for (x, y, z, a) in ((xm, TY + 80, 0, 90), (xm, -TY - 80, 0, 270), (TX1 + 100, 140, 0, 0), (TX1 + 100, -30, 0, 0)):
        spawn(s, 'team_%splayer' % team, x, y, z, a)
    for (x, y, z, a) in ((TX1 - 120, 120, TRZ, 0), (TX1 - 120, -100, TRZ, 0), (TX0 - 100, 560, 0, 0), (TX0 - 100, -640, 0, 0),
                         (TX1 + 260, 560, 0, 0), (TX1 + 260, -560, 0, 0)):
        spawn(s, 'team_%sspawn' % team, x, y, z, a)
    # behind the temple
    item(s, 'ammo_pumper', TX0 - 100, 420, 0)
    item(s, 'item_armor_shard', TX0 - 100, -760, 0)
    smdl(s, 'pad_ddmix/plants/waterplant1a.md3', -TXI + 160, 900, 0, 1.2, 30)
    smdl(s, 'pad_ddmix/plants/waterplant1b.md3', -TXI + 140, -980, 0, 1.3, 200)
    skelp(s, -TXI + 60, 640, 720); skelp(s, -TXI + 60, 520, 560, tex='kelp2'); skelp(s, -TXI + 70, -1100, 640)
    skelp(s, -TXI + 60, -560, 760, tex='kelp2'); skelp(s, -TXI + 200, 1120, 600)
    srock(s, -TXI + 90, -760, 70, 60, 110, seed=11)
    slight(s, TX0 - 140, 0, 520, 900, '0.9 0.95 1')


def filter_box(s):
    """hang-on aquarium filter on the end glass behind the temple: walkable top (Boaster), intake tube to the gravel"""
    x0, x1 = -TXI, -TXI + 160
    A(sb(s, x0, -256, FILTER_Z - 128, x1, 256, FILTER_Z, {'top': T('filter_plain'), 'side': T('filter_body'), 'bot': T('filter_plain')}))
    A(ssign(s, (x1, -176, FILTER_Z - 112), (x1 + 4, 176, FILTER_Z - 48), T('filter_label'), 512, 128, 'e', T('filter_plain')))
    A(scyl(s, -TXI + 60, 180, 28, 48, FILTER_Z - 128, {'side': T('filter_plain'), 'top': CAULK, 'bot': CAULK}, 12))
    A(scyl(s, -TXI + 60, 180, 44, 0, 48, {'side': T('filter_body'), 'top': T('filter_plain'), 'bot': CAULK}, 12))      # intake basket
    # outflow: a curtain of bubbles pouring out of the front lip
    A(bubble_column(s * (x1 + 50), s * -120, 200, FILTER_Z - 140, 40)); A(bubble_column(s * (x1 + 50), s * 120, 200, FILTER_Z - 140, 40))
    weapon(s, 'boaster', -TXI + 80, 160, FILTER_Z, 'orange')
    item(s, 'ammo_boaster', -TXI + 80, -170, FILTER_Z)
    slight(s, -TXI + 260, 0, FILTER_Z + 160, 420, '0.8 0.95 1')
    speaker(s * (-TXI + 100), 0, FILTER_Z - 60, 'sound/world/machine/fishtank.ogg')


# =================================================================================================== coral plate spirals
def plate(cx, cy, top, r, col, base, stalk_r=22):
    """table coral: frustum disc (24 thick, top radius r) on a stalk from `base`"""
    out = [frustum(cx, cy, r * 0.82, top - 24, r, top, {'top': T('coral_' + col), 'side': T('coral_' + col), 'bot': T('coral_stalk')}, 12)]
    if top - 24 > base:
        out.append(cyl(cx, cy, stalk_r, base, top - 24, T('coral_stalk'), 8))
    return out


def plan_spiral(C, R, a0, n, top0, rise=32, r=88, chord=150, dirn=1):
    """plate centres along a circle (C, R) starting at angle a0, consecutive centres `chord` apart"""
    step = math.degrees(2 * math.asin(chord / 2 / R)) * dirn
    out = []
    for k in range(n):
        a = math.radians(a0 + step * k)
        out.append([C[0] + R * math.cos(a), C[1] + R * math.sin(a), top0 + rise * k, r])
    return out


def check_plates(P, stalk_r=22, extra_solids=()):
    """no stalk through another plate, no two plates whose z ranges touch overlapping, consecutive plates overlapping
    a little (walkable step) and players fit under any higher plate (56 headroom) unless it's the next step"""
    for i, (x, y, z, r) in enumerate(P):
        for j, (x2, y2, z2, r2) in enumerate(P):
            if i == j: continue
            d = math.hypot(x - x2, y - y2)
            if z2 < z - 24 and d < r2 + stalk_r + 2:
                raise AssertionError(f'stalk of plate {i} hits plate {j} ({d:.0f})')
            if j == i + 1:
                assert d < r + r2 - 10, f'plates {i},{j} too far apart ({d:.0f})'
            elif z2 > z and z2 - 24 - z < 60 and d < r + r2:
                raise AssertionError(f'plate {j} is a low ceiling over plate {i} ({d:.0f})')


def reef(s):
    """red reef (north-west): rock mesa against the back glass with stairs up its front, coral plates spiralling from
    the mesa up to a sniper perch (Splasher)"""
    mx0, mx1, my0 = -1696, -1184, 864
    A(sb(s, mx0, my0, 0, mx1, TYN, TRZ, {'top': T('rock_moss'), 'side': T('rock'), 'bot': CAULK}))
    st = {'top': T('rock_moss'), 'side': T('rock'), 'bot': CAULK}
    for b in stairs(mx0, my0 - 128, mx1, my0, 0, TRZ, 'e', st):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], st))
    # spiral: 7 plates (288..480) clockwise round (-940, 940), then the perch (512)
    RC = (-940, 940)
    P = plan_spiral(RC, 180, 180, 7, TRZ + 32, dirn=-1)
    # perch: a big table coral on a tall stalk in the middle of the spiral, one step up from the last plate
    P.append([-985, 970, P[-1][2] + 32, 120])
    check_plates(P)
    cols = ['purple', 'magenta', 'orange', 'green', 'yellow', 'blue', 'red', 'magenta']
    for k, (x, y, z, r) in enumerate(P):
        inside_mesa = (mx0 + 24 < x < mx1 - 24 and y > my0 + 24)
        base = TRZ if inside_mesa else 0
        assert inside_mesa or not (x + 24 > mx0 and x - 24 < mx1 and y + 24 > my0), f'reef stalk {k} straddles the mesa'
        for b in plate(round(x), round(y), z, r, cols[k], base): A(sb_brush(s, b))
    px, py, pz, _ = P[-1]
    weapon(s, 'splasher', px, py, pz, 'orange')
    # bubble lift from the mesa straight up to the perch (the plates are the scenic way; bots prefer the lift)
    spad(s, -1330, 1030, TRZ, (px - 30, py, pz), 720, 'perch_%s' % ('r' if s > 0 else 'b'))
    item(s, 'item_armor_shard', P[3][0], P[3][1], P[3][2])
    # mesa top: ammo + plants, centre of the spiral: tall plant
    item(s, 'ammo_splasher', -1520, 1000, TRZ)
    srock(s, -1650, 1150, 46, 54, 200, z=TRZ, seed=21)
    srock(s, -1236, 1160, 44, 46, 170, z=TRZ, seed=22)
    item(s, 'ammo_balloony', -1300, 950, TRZ)
    smdl(s, 'pad_ddmix/plants/waterplant1b.md3', -1450, 1120, TRZ, 0.9, 40)
    smdl(s, 'pad_ddmix/plants/fern.md3', -1580, 960, TRZ, 0.28, 0)
    smdl(s, 'pad_ddmix/plants/waterplant1b.md3', -700, 1120, 0, 0.8, 120)
    skelp(s, -1560, 1190, 520, TRZ); skelp(s, -1330, 1190, 460, TRZ, 'kelp2')
    slight(s, -1440, 1000, 520, 500); slight(s, -940, 940, 700, 500); slight(s, -1440, 700, 200, 300)


def sb_brush(s, b):
    """rotate an already built (red side) brush for the blue side: rebuild from its vertices"""
    if s > 0: return b
    V = b.verts()
    tex = {}
    for f in b.faces:
        k = 'top' if f.n[2] > 0.7 else ('bot' if f.n[2] < -0.7 else 'side')
        tex.setdefault(k, f.tex)
    return hull([(-x, -y, z) for (x, y, z) in V], tex, round_pts=True)


def diving_bell(s):
    """red diving bell (south-west): brass 16-gon, two hatches (west / south), coral plates spiral up to the roof,
    bubble lift outside the south hatch. Bubble G inside, Pumper on the roof."""
    bx, by = BELL
    br = {'side': T('brass'), 'top': T('brass'), 'bot': CAULK}
    outer = ngon(bx, by, BELL_R, 16); inner = ngon(bx, by, BELL_R - 32, 16)
    doors = {7, 11}                                   # wall segments centred on 180 and 270 deg
    for k in range(16):
        q = [inner[k], outer[k], outer[(k + 1) % 16], inner[(k + 1) % 16]]
        z0 = 128 if k in doors else 0
        A(sh(s, [(x, y, z) for (x, y) in q for z in (z0, BELL_H)], br))
    A(sh(s, [(x, y, z) for (x, y) in outer for z in (BELL_H, BELL_H + 32)], {'top': T('bell_roof'), 'side': T('brass'), 'bot': T('brass')}))
    # portholes on the east and north faces (sign panels, 4u proud)
    ap = BELL_R * math.cos(math.radians(11.25))
    A(ssign(s, (round(bx + ap), by - 40, 104), (round(bx + ap) + 4, by + 40, 184), T('porthole'), 256, 256, 'e', T('brass')))
    A(ssign(s, (bx - 40, round(by + ap), 104), (bx + 40, round(by + ap) + 4, 184), T('porthole'), 256, 256, 'n', T('brass')))
    # coral plates: 9 plates (32..288) counter-clockwise from -30 deg, the last one beside the roof edge
    P = plan_spiral((bx, by), BELL_R + 97, -30, 9, 32, dirn=1)
    check_plates(P)
    cols = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'magenta', 'orange', 'green']
    for k, (x, y, z, r) in enumerate(P):
        for b in plate(round(x), round(y), z, r, cols[k], 0): A(sb_brush(s, b))
    # bubble lift outside the south hatch -> roof
    a = math.radians(228)
    spad(s, bx + 340 * math.cos(a), by + 340 * math.sin(a), 0, (bx, by, BELL_H + 32), 560, 'bell_%s' % ('r' if s > 0 else 'b'))
    # loot
    weapon(s, 'bubbleg', bx, by, 0, 'blue')
    item(s, 'ammo_pumper', bx + 120, by + 60, 0)
    weapon(s, 'pumper', bx + 40, by + 40, BELL_H + 32, 'green')
    item(s, 'ammo_boaster', P[4][0], P[4][1], P[4][2])
    item(s, 'item_armor_shard', bx - 110, by - 60, 0)
    smdl(s, 'pad_ddmix/padship/rumbottle1.md3', bx - 120, by + 90, 0, 1.0, 30)
    slight(s, bx, by, 200, 260, '1 0.85 0.6')
    slight(s, bx, by, BELL_H + 200, 400)
    slight(s, bx + 420, by + 120, 300, 350)
    LOOPS.append(dict(name=f'bell_{"r" if s > 0 else "b"}', centre=(s * bx, s * by, 430), speed=-20 * s, kind='tang_ring', R=200))


# =================================================================================================== treasure chests
def chest(s):
    """treasure chest mid-lane (red copy north at x 0): enter through the broken front, gold-bar steps up to the lid"""
    y0, y1 = CHEST_Y
    wd = {'side': T('chest_wood'), 'top': T('chest_wood'), 'bot': CAULK}
    A(sb(s, -192, y0, 0, -56, y0 + 24, 160, wd)); A(sb(s, 56, y0, 0, 192, y0 + 24, 160, wd))
    A(sb(s, -56, y0, 112, 56, y0 + 24, 160, wd))
    A(sb(s, -192, y1 - 24, 0, 192, y1, 160, wd))
    A(sb(s, -192, y0 + 24, 0, -168, y1 - 24, 160, wd)); A(sb(s, 168, y0 + 24, 0, 192, y1 - 24, 160, wd))
    A(sb(s, -200, y0 - 8, 160, 192, y1 + 8, 192, {'side': T('gold'), 'top': T('chest_wood'), 'bot': T('chest_wood')}))
    A(sb(s, -184, y0 + 8, 192, 184, y1 - 8, 208, {'side': T('chest_wood'), 'top': T('chest_wood'), 'bot': CAULK}))
    A(ssign(s, (-24, y0 - 4, 112), (24, y0, 156), T('chest_lock'), 128, 128, 's', T('gold')))
    # gold bar steps on the east side (32 rise), top bar 16 below the lid
    for k in range(6):
        x0 = 192 + 48 * k
        A(sb(s, x0, y0 + 8, 0, x0 + 48, y0 + 72, 192 - 32 * k, {'side': T('coins'), 'top': T('gold'), 'bot': CAULK}))
    # loot: inside (Pad shield + Speedy), on the lid, on the bars
    item(s, 'item_armor_padshield', -80, (y0 + y1) / 2, 0)
    item(s, 'holdable_floater' if s > 0 else 'item_jumper', 80, (y0 + y1) / 2 + 30, 0)
    item(s, 'ammo_imperius', 0, (y0 + y1) / 2, 208)
    item(s, 'ammo_splasher', 192 + 48 * 3 + 24, y0 + 40, 192 - 96)
    # treasure clutter
    smdl(s, 'ente/padstatue_gold.md3', -330, 900, 0, 0.7, 300, solid=True)
    smdl(s, 'pad_ddmix/door/ancient_key_lying.md3', -120, y0 - 70, 0, 2.0, 25)
    smdl(s, 'pad_ddmix/padship/rumbottle2.md3', 260, 1120, 0, 1.0, 140)
    smdl(s, 'pad_ddmix/jail/skull.md3', 120, y1 + 90, 0, 0.9, 200)
    slight(s, 0, (y0 + y1) / 2, 120, 160, '1 0.85 0.5')
    slight(s, 0, y0 - 150, 340, 420, '1 0.95 0.85')


# =================================================================================================== decoration: rocks, kelp, plants
def scenery(s):
    # boulders breaking up the lanes
    srock(s, -1560, 620, 80, 64, 140, seed=1)
    srock(s, -520, 700, 90, 70, 150, seed=2)
    srock(s, -470, -610, 90, 70, 160, seed=3)
    srock(s, -1700, -930, 110, 90, 120, seed=4)
    srock(s, -760, 380, 60, 54, 90, seed=6)
    srock(s, -620, -420, 70, 56, 110, seed=7)
    # tube sponges and brain corals on the gravel
    for (x, y, sd, n, hm) in ((-1460, 470, 11, 4, 96), (-820, 520, 12, 3, 96), (-470, -1080, 13, 4, 96), (-2420, -500, 14, 3, 96),
                              (-1840, 900, 15, 5, 110), (-300, 1080, 16, 3, 96)):
        tubes(s * x, s * y, 0, sd, n, hm)
    for (x, y, r, sd) in ((-660, 420, 46, 1), (-1880, -900, 52, 2), (-2440, 260, 40, 3), (-300, -640, 44, 4)):
        brain(s * x, s * y, 0, r, sd)
    # kelp stands along the glass and around the hole
    for (x, y, h, t) in ((-2100, -1150, 720, 'kelp'), (-1900, -1130, 600, 'kelp2'), (-1460, -1150, 800, 'kelp'), (-760, -1150, 660, 'kelp2'),
                         (-380, -1140, 820, 'kelp'), (-2400, -260, 520, 'kelp2'), (-560, 560, 520, 'kelp'), (-600, -580, 480, 'kelp2'),
                         (-1560, 520, 560, 'kelp2'), (-430, 1150, 720, 'kelp'), (-2180, 1150, 640, 'kelp2')):
        skelp(s, x, y, h, tex=t, ang=(x * 7 + y) % 90)
    # catalog plants and props on the gravel
    smdl(s, 'pad_ddmix/plants/waterplant1a.md3', -1500, -1080, 0, 1.1, 300)
    smdl(s, 'pad_ddmix/plants/waterplant1b.md3', -330, -1060, 0, 1.0, 20)
    smdl(s, 'pad_ddmix/plants/waterplant1a.md3', -2450, 470, 0, 0.8, 140)
    smdl(s, 'pad_ddmix/trashcan/grass.md3', -720, 640, 0, 1.2, 0)
    smdl(s, 'pad_ddmix/trashcan/grass.md3', -1640, -760, 0, 1.0, 70)
    smdl(s, 'pad_ddmix/trashcan/grass.md3', -660, 1120, 0, 1.1, 130)
    smdl(s, 'pad_ddmix/trashcan/tree_leafless.md3', -1800, -560, 0, 0.6, 30)
    smdl(s, 'pad_statues/statue_super.md3', -700, -260, 0, 1.0, 20, solid=True)
    smdl(s, 'pad_ddmix/padship/amphora.md3', -2400, -900, 0, 0.6, 80, solid=True)
    smdl(s, 'pad_ddmix/padship/amphora.md3', -2440, -1080, 0, 0.45, 160, solid=True)
    smdl(s, 'pad_ddmix/jail/skull.md3', -1380, 640, 0, 1.0, 330)
    smdl(s, 'pad_ddmix/trashcan/cannedfish_rusty.md3', -840, -260, 0, 1.6, 40)
    smdl(s, 'pad_ball/pad_softball.md3', -560, 1040, 0, 3.0, 0)
    smdl(s, 'ente/boneb.md3', -1200, -320, 0, 3.0, 60)
    # FFA spawns
    for (x, y, z, a) in ((-1440, 930, TRZ, 270), (-1700, -720, 0, 0), (-760, 160, 0, 0), (-260, -940, 0, 0), (-2480, -100, 0, 0),
                         (-900, -560, 0, 90), (-760, 700, 0, 0), (-1200, 0, TRZ, 0)):
        spawn(s, 'info_player_deathmatch', x, y, z, a)
    # scattered ammo / items in plain sight and hidden
    item(s, 'ammo_bubbleg', -2440, -380, 0)
    item(s, 'ammo_nipper', -380, -980, 0)
    item(s, 'ammo_betty', -1880, -1080, 0)
    item(s, 'ammo_pumper', -760, 250, 0)
    item(s, 'ammo_boaster', -2440, 1060, 0)
    item(s, 'holdable_killerducks' if s > 0 else 'item_speedy', -660, 960, 0)
    item(s, 'item_armor_shard', -900, -420, 0)


def lights_and_sound():
    for x in range(-2200, 2201, 550):
        for y in (-820, 0, 820):
            light(x, y, 1250, 2300, '0.8 0.92 1')
    for (x, y) in ((-1300, 0), (1300, 0), (0, 900), (0, -900)):
        light(x, y, 560, 700, '0.85 0.95 1')
    for (x, y) in ((-1600, 700), (1600, -700), (-1600, -700), (1600, 700), (0, 0)):
        speaker(x, y, 400, 'sound/world/ambient/water_rippling.ogg')
    # a big bubble burst somewhere now and then
    speaker(0, 0, 900, 'sound/world/ambient/water_bubble.ogg', loop=False, targetname='burst')
    M.ent('func_timer', (0, 300, 1200), target='burst', wait=25, random=12, spawnflags=1)


# =================================================================================================== swimming fish
def fish_loops():
    """one func_rotating per loop: origin brush at the circle centre, a tiny nodraw_ns brush, model2 = the school"""
    specs = [dict(name='sharks', centre=(0, 0, 760), speed=9, kind='sharks'),
             dict(name='whaleshark', centre=(0, 0, 1180), speed=-6, kind='whaleshark'),
             dict(name='tangs_spire', centre=(0, 0, 430), speed=16, kind='tangs_spire'),
             dict(name='angels_hole', centre=(0, 0, -360), speed=-12, kind='angels_hole')] + LOOPS
    out = []
    for sp in specs:
        Lm = FM.LoopModel(sp['name'])
        ccw = sp['speed'] > 0
        k = sp['kind']
        if k == 'sharks':
            FM.add_shark(Lm, 1050, 0, 10, ccw); FM.add_shark(Lm, 1050, 180, -10, ccw)
            FM.add_tang(Lm, 1000, 24, 40, ccw); FM.add_tang(Lm, 1100, 200, -30, ccw)
        elif k == 'whaleshark':
            FM.add_shark(Lm, 760, 90, 0, ccw, L=520, kind='whaleshark', bank=6)
            for j in range(4): FM.add_tang(Lm, 740 + 25 * j, 70 - 6 * j, -60 + 12 * j, ccw)
        elif k == 'tangs_spire':
            for j in range(9): FM.add_tang(Lm, 410 + 22 * (j % 4), 8 * j, -30 + 9 * ((j * 5) % 7), ccw)
            for j in range(7): FM.add_tang(Lm, 420 + 20 * (j % 3), 180 + 9 * j, -20 + 10 * ((j * 3) % 5), ccw)
        elif k == 'angels_hole':
            for j in range(6): FM.add_angel(Lm, MD3ROOT, 330 + 18 * (j % 3), 60 * j, -30 + 12 * (j % 5), ccw,
                                            ['flame_angel', 'flame_angel02', 'flame_angel05'][j % 3], 1.0)
        elif k == 'tang_ring':
            for j in range(6): FM.add_tang(Lm, sp['R'] + 14 * (j % 3), 10 * j, -15 + 8 * ((j * 3) % 4), ccw)
        elif k == 'angel_ring':
            for j in range(3): FM.add_angel(Lm, MD3ROOT, sp['R'], 120 * j, -20 + 20 * j, ccw, 'flame_angel05', 0.7)
        path = Lm.save(OUT)
        cx, cy, cz = sp['centre']
        org = box((round(cx) - 8, round(cy) - 8, round(cz) - 8), (round(cx) + 8, round(cy) + 8, round(cz) + 8), ORIGIN)
        nd = box((round(cx) - 8, round(cy) - 8, round(cz) + 8), (round(cx) + 8, round(cy) + 8, round(cz) + 24), NODRAW_NS)
        M.ent('func_rotating', brushes=[org, nd], model2=path, speed=sp['speed'], spawnflags=0, dmg=0)
        out.append((sp, Lm))
    return out


def sweep_check(loops):
    """the fish are nonsolid, but should not swim through solid scenery: sample each school's swept annulus"""
    solids = [b for b in M.world if b.is_solid() and not (b.textures() & {T('fog'), T('glass')} and False)]
    sol = []
    for b in solids:
        tx = b.textures()
        if tx & {T('fog'), T('water'), T('water_inner')} or tx <= {NODRAW_NS, T('kelp'), T('kelp2'), T('bubbles'), T('banner_red'), T('banner_blue')}:
            continue
        mn, mx = b.bounds(); sol.append((b, mn, mx))
    bad = []
    for sp, Lm in loops:
        cx, cy, cz = sp['centre']
        for (R, dz, half) in Lm.extent:
            w = half * 0.45; h = half * 0.5
            hits = set()
            for a in range(0, 360, 3):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                for rr in (R - w, R, R + w):
                    for zz in (cz + dz - h, cz + dz, cz + dz + h):
                        p = (cx + rr * ca, cy + rr * sa, zz)
                        for (b, mn, mx) in sol:
                            if mn[0] < p[0] < mx[0] and mn[1] < p[1] < mx[1] and mn[2] < p[2] < mx[2] and inside_brush(b, p, 1.0):
                                hits.add((a, tuple(np.round(mn).astype(int))))
                                break
            if hits:
                bad.append((sp['name'], R, dz, sorted(hits)[:3], len(hits)))
    for b in bad: print('FISH SWEEP:', b)
    print('fish sweep:', 'OK' if not bad else f'{len(bad)} schools touch scenery')


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    tank_shell(); ground(); spire(); blue_hole()
    for s in (1, -1):
        temple(s); filter_box(s); causeway(s); reef(s); diving_bell(s); chest(s); scenery(s)
    lights_and_sound()
    carve_water()
    loops = fish_loops()
    sweep_check(loops)
    M.ent('info_player_intermission', (-2300, -1000, 900), angles='18 30 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/padtank/build_padtank.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
