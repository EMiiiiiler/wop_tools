#!/usr/bin/env python3
"""Countertop Clash - World of Padman Capture the Lolly map generator (map 'wop_padkitchen').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_kitchen.py

Writes <OUT>/maps/wop_padkitchen.map, textures/padkitchen/*, models/padkitchen/*, scripts/padkitchen.shader and
scripts/wop_padkitchen.arena.

A giant kitchen at "army man" scale (~13u per cm, catalog models at ~1.3-1.6). x east, y north, counter tops at z 0,
kitchen floor (instant death) at z -1152, ceiling z 2048. The map is mirror-symmetric about x = 0: every red piece is
built by a function taking s = +1 (red, west, negative x) and mirrored for blue (s = -1, east).

  U-shaped counters  back counter along the tiled back wall (y 512..1280), side counters along both end walls
                     (x +-2176..+-3072), a free-standing island in front (y -1280..-128) with the sink in the middle.
                     The aisle between them is a drop to the floor (death), crossed by two cutting boards, a wooden
                     spatula (neutral lolly) and two baguettes from the side counters to the island ends.
  bases              a giant team-coloured four-slice toaster on each side counter: three doors, the lolly inside
                     between glowing coils, roof slots you can drop through, toast-stack stairs up the wall side
                     (Balloony on the roof)
  sink               1280 x 640 stainless basin 448 deep with 48u of soapy water (wade, never swim); two cutting-board
                     ramps out, a plate-stack jump pad up to the faucet spout. Betty at the bottom, Imperius on the spout.
  stove              centre of the back counter: two lit front burners (they burn), enamel stock pots on the back
                     burners (pads up to the lids, Boaster), range hood above whose top joins the two open upper
                     cabinets (Splasher each) into a high walkway (Pad Power on the hood)
  props              lying cereal box tunnels (Bubble G), a paper towel holder per corner (pad to the top, Pad shield),
                     a fallen paper towel roll with its sheet as a ramp, donut stacks, sponges with forks, cans, cereal
                     spills, buzzing flies circling the donuts
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import kitchen_textures as TX
import kitchen_models as KM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padkitchen'
T = lambda n: 'padkitchen/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW_NS = T('nodraw_ns')

for k, v in {'granite': (1, 1), 'granite_edge': (0.5, 0.5), 'backsplash': (0.75, 0.75), 'wall': (1, 1), 'ceiling': (1, 1), 'floor': (1.5, 1.5),
             'cab_wood': (1, 1), 'cab_inside': (1, 1), 'steel': (1, 1), 'steel_v': (1, 1), 'sink': (1, 1), 'cooktop': (1, 1), 'grate': (0.6, 0.6),
             'toaster_red': (1, 1), 'toaster_blue': (1, 1), 'chrome': (1, 1), 'toaster_in': (1, 1), 'coils': (1, 1), 'bread': (0.6, 0.6),
             'crust': (0.6, 0.6), 'board': (1, 1), 'board_dark': (1, 1), 'towel': (0.75, 0.75), 'core': (0.5, 0.5), 'sponge': (0.75, 0.75),
             'scrub': (0.75, 0.75), 'sugar': (0.5, 0.5), 'cardboard': (1, 1), 'cardboard_in': (1, 1), 'fridge_side': (1, 1), 'kick': (1, 1),
             'baseboard': (1, 1), 'window_frame': (1, 1), 'plate_side': (1, 1), 'mat_red': (1, 1), 'mat_blue': (1, 1), 'water': (1, 1),
             'fan': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '14', '_color': '1 0.95 0.88', 'gridsize': '96 96 128', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
XW, YB, YS = 3072, 1280, -2816       # end walls (inner face x = +-XW), back wall face, far (south) wall face
ZF, ZC = -1152, 2048                  # kitchen floor (death), ceiling
SLAB = 48                             # counter slab thickness (z -48..0)
BC0 = 512                             # back counter front edge
SX = 2176                             # side counters run from x +-SX to the end walls
SY0 = -1280                           # side counter / island south edge
IX, IY0, IY1 = 1792, -1280, -128      # island
SK = (-640, -1024, 640, -384)         # sink basin interior (x0, y0, x1, y1)
SKZ, WZ = -448, -400                  # basin floor, water surface
KILLZ = -640                          # anything that falls below this dies
# toaster (red): footprint, wall thickness, roof top, slots
TA = (-XW + 8, -960, -XW + 456, 64)   # flush against the end wall's backsplash
TT, TROOF, TCH = 32, 512, 48
TXM, TYM = (TA[0] + TA[2]) // 2, -448  # toaster centre (lolly)
SLOT_A, SLOT_B, SLOT_Y = (TXM - 112, TXM - 48), (TXM + 48, TXM + 112), (-768, -128)
TST = (TA[2], TA[2] + 256)             # toast-stack stairs on the toaster's east side (x range)
# stove / hood / cabinets
ST_X = 768
CAB_Z0, CAB_Z1, CAB_Y0 = 944, 1728, 960
HOOD_Y0, HOOD_Z0, HOOD_Z1 = 896, 760, 960
SHELF_Z = 1392
POT = (-384, 1056)
GRATE_Z = 32
FAUCET = (0, -296)
WIN = (-896, 256, 640, 1536)          # window in the end walls (y0, y1, z0, z1)
BREAD_Y = -700
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []


# =================================================================================================== helpers
def rtex(s, tex):
    if s > 0 or not isinstance(tex, dict): return tex
    sw = {'e': 'w', 'w': 'e'}
    return {sw.get(k, k): v for k, v in tex.items()}


def sb(s, x0, y0, z0, x1, y1, z1, tex, detail=True):
    xa, xb = sorted((s * x0, s * x1)); ya, yb = sorted((y0, y1))
    return box((round(xa), round(ya), z0), (round(xb), round(yb), z1), rtex(s, tex), detail)


def sh(s, pts, tex, rnd=True):
    return hull([(s * x, y, z) for (x, y, z) in pts], rtex(s, tex), round_pts=rnd)


def scyl(s, x, y, r, z0, z1, tex, n=12, phase=None):
    return cyl(s * x, y, r, z0, z1, rtex(s, tex), n, phase=phase)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=12, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex)


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


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, round_n=0):
    """mdl_c + a weapon-clip box (or n-gon for round things) around the model so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    z1 = oz + b['max'][2] * scale
    if round_n:
        r = (b['max'][0] - b['min'][0]) * scale / 2 * (1 - shrink)
        A(cyl(round(x), round(y), round(r), round(zsurf), round(z1 - 4), WCLIP, round_n))
        return e
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - 4)), WCLIP))
    return e


def smdl(s, path, x, y, zsurf, scale=1.0, angle=0, solid=False, round_n=0, shrink=0.12):
    ang = ((180 - angle) if s < 0 else angle) % 360
    if solid or round_n: return solid_mdl(path, s * x, y, zsurf, scale, ang, shrink, round_n)
    return mdl_c(path, s * x, y, zsurf, scale, ang)


def light(x, y, z, val, color='1 0.94 0.84', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def slight(s, x, y, z, val, color='1 0.94 0.84'):
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
    a = ang if s > 0 else (180 - ang)
    M.ent(cls, (round(s * x), round(y), floor + 25), angle=a % 360)
    SPOTS['spawn'].append((s * x, y, floor))


def vfit(b, ztop, zbot, th, tw=None, tex=None):
    """vertical faces showing a texture `th` px tall: stretch it to exactly ztop..zbot, tile horizontally at tw px/unit"""
    for f in b.faces:
        if abs(f.n[2]) > 0.1: continue
        if tex and f.tex != tex: continue
        sy = (ztop - zbot) / th
        sx = abs(f.sc[0]) if tw is None else tw
        f.sc = (sx, sy); f.off = (f.off[0], round((ztop / sy) % th, 3))
    return b


def hfit(b, x0, y0, x1, y1, tw, th, tex):
    """top face(s) with `tex`: exactly one copy of a tw x th texture over the rectangle (north = texture top)"""
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.9: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def mirror_x(b, s):
    """mirror an already built red brush for blue (x -> -x), keeping each face's texture"""
    if s > 0: return b
    texof = [((-f.n[0], f.n[1], f.n[2]), f.tex) for f in b.faces]
    def tf(n):
        return max(texof, key=lambda q: q[0][0] * n[0] + q[0][1] * n[1] + q[0][2] * n[2])[1]
    return hull([(-x, y, z) for (x, y, z) in b.verts()], tf, round_pts=True)


def jumppad(x, y, z, land, apex, name, glow=True):
    """pad disc (r 34) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of the flight measured from
    the trigger centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way to `land`."""
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
    if glow: light(x, y, z + 48, 120, '1 0.75 0.3')


def spad(s, x, y, z, land, apex, name):
    jumppad(s * x, y, z, (s * land[0], land[1], land[2]), apex, name)


def sprite(x, y, z0, z1, tex, w, ang=0):
    """thin vertical autosprite2 slab (taller than wide), shader on both broad faces"""
    a = math.radians(ang); dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2; nx, ny = -math.sin(a), math.cos(a)
    q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx * 2, y + dy + ny * 2), (x - dx + nx * 2, y - dy + ny * 2)]
    def tf(n, nx=nx, ny=ny):
        return T(tex) if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
    b = hull([(px, py, zz) for (px, py) in q for zz in (z0, z1)], tf, round_pts=False)
    for f in b.faces:
        if f.tex == T(tex): f.sc = (w / 64, (z1 - z0) / 128); f.off = (0, 0)
    return b


def drop_check():
    pass


# =================================================================================================== room shell
def shell():
    W = 16
    wall = {'side': CAULK}
    A(box((-XW - W, YS - W, ZF - W), (XW + W, YB + W, ZF), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((-XW - W, YS - W, ZC), (XW + W, YB + W, ZC + W), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((-XW - W, YB, ZF), (XW + W, YB + W, ZC), {'side': CAULK, 's': T('wall')}, detail=False))
    A(box((-XW - W, YS - W, ZF), (XW + W, YS, ZC), {'side': CAULK, 'n': T('wall')}, detail=False))
    for s in (1, -1):
        x0, x1 = -XW - W, -XW
        y0, y1, z0, z1 = WIN
        for (ya, yb, za, zb) in ((YS, YB, ZF, z0), (YS, YB, z1, ZC), (YS, y0, z0, z1), (y1, YB, z0, z1)):
            A(sb(s, x0, ya, za, x1, yb, zb, {'side': CAULK, 'e': T('wall')}, detail=False))
        # sky pocket behind the window
        SKY = T('sky')
        A(sb(s, -XW - 400, y0 - 128, z0 - 128, -XW - 384, y1 + 128, z1 + 128, SKY, detail=False))
        A(sb(s, -XW - 384, y0 - 128, z0 - 128, -XW - W, y0 - 112, z1 + 128, SKY, detail=False))
        A(sb(s, -XW - 384, y1 + 112, z0 - 128, -XW - W, y1 + 128, z1 + 128, SKY, detail=False))
        A(sb(s, -XW - 384, y0 - 112, z0 - 128, -XW - W, y1 + 112, z0 - 112, SKY, detail=False))
        A(sb(s, -XW - 384, y0 - 112, z1 + 112, -XW - W, y1 + 112, z1 + 128, SKY, detail=False))
        # window: frame inside the opening, glass pane, sill, mullion
        fr = T('window_frame')
        A(sb(s, -XW - W, y0, z0, -XW + 24, y1, z0 + 16, fr))                      # sill (sticks 24 into the room)
        A(sb(s, -XW - W, y0, z1 - 16, -XW, y1, z1, fr))
        A(sb(s, -XW - W, y0, z0 + 16, -XW, y0 + 16, z1 - 16, fr)); A(sb(s, -XW - W, y1 - 16, z0 + 16, -XW, y1, z1 - 16, fr))
        ym = (y0 + y1) // 2
        A(sb(s, -XW - W, ym - 8, z0 + 16, -XW - 4, ym + 8, z1 - 16, fr))
        for (ya, yb) in ((y0 + 16, ym - 8), (ym + 8, y1 - 16)):
            A(sb(s, -XW - W, ya, (z0 + z1) // 2 - 8, -XW - 4, yb, (z0 + z1) // 2 + 8, fr))
        for (ya, yb) in ((y0 + 16, ym - 8), (ym + 8, y1 - 16)):
            for (za, zb) in ((z0 + 16, (z0 + z1) // 2 - 8), ((z0 + z1) // 2 + 8, z1 - 16)):
                A(sb(s, -XW - 12, ya, za, -XW - 8, yb, zb, T('glass')))
    # backsplash tiles: thin tile panel on the back wall above the counter (y 1272..1280) up to the cabinets
    A(box((-XW, YB - 8, 0), (XW, YB, CAB_Z0), {'s': T('backsplash'), 'side': CAULK, 'top': CAULK, 'bot': CAULK}))
    for s in (1, -1):
        A(sb(s, -XW, SY0, 0, -XW + 8, YB - 8, 0 + 576, {'e': T('backsplash'), 'side': CAULK, 'top': T('backsplash'), 'bot': CAULK}))
    # baseboards round the kitchen floor
    for (mn, mx) in (((-XW, YS, ZF), (DOOR[0], YS + 12, ZF + 64)), ((DOOR[1], YS, ZF), (XW, YS + 12, ZF + 64))):
        A(box(mn, mx, T('baseboard')))


# =================================================================================================== counters
def cab_body(x0, y0, x1, y1, faces, sink_hole=None):
    """counter cabinet body z ZF..-SLAB: drawer band on top, doors below, recessed toe kick. faces = sides that show
    cabinet fronts ('n','s','e','w'); the others are caulk (against walls / other bodies)."""
    zd = -SLAB - 160
    def tx(kind):
        d = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
        for k in faces: d[k] = T(kind)
        return d
    for (za, zb, kind, th) in ((zd, -SLAB, 'cab_drawer', 128), (ZF + 96, zd, 'cab_door', 512)):
        rects = sub_rects((x0, y0, x1, y1), [sink_hole]) if (sink_hole and za >= SKZ - 16) else [(x0, y0, x1, y1)]
        if sink_hole and za < SKZ - 16:
            # doors band split at the basin floor: below it full footprint, above it a ring round the basin
            for (zz0, zz1) in ((za, SKZ - 16), (SKZ - 16, zb)):
                rr = [(x0, y0, x1, y1)] if zz1 <= SKZ - 16 else sub_rects((x0, y0, x1, y1), [sink_hole])
                for r in rr:
                    b = box((r[0], r[1], zz0), (r[2], r[3], zz1), tx(kind))
                    vfit(b, zb, za, th, 1.0, T(kind)); _sinkfaces(b, sink_hole); A(b)
            continue
        for r in rects:
            b = box((r[0], r[1], za), (r[2], r[3], zb), tx(kind))
            vfit(b, zb, za, th, 1.0, T(kind)); _sinkfaces(b, sink_hole); A(b)
    # toe kick, recessed 40
    k = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    for f in faces: k[f] = T('kick')
    xa, ya, xb, yb = x0, y0, x1, y1
    if 'w' in faces: xa += 40
    if 'e' in faces: xb -= 40
    if 's' in faces: ya += 40
    if 'n' in faces: yb -= 40
    A(box((xa, ya, ZF), (xb, yb, ZF + 96), k))


def _sinkfaces(b, hole):
    if not hole: return
    hx0, hy0, hx1, hy1 = hole
    for f in b.faces:
        if abs(f.n[2]) > 0.1: continue
        p = f.pts[0]
        if (abs(f.n[0]) > 0.9 and (abs(p[0] - hx0) < 0.5 or abs(p[0] - hx1) < 0.5) and hy0 - 0.5 <= p[1] <= hy1 + 0.5) or \
           (abs(f.n[1]) > 0.9 and (abs(p[1] - hy0) < 0.5 or abs(p[1] - hy1) < 0.5) and hx0 - 0.5 <= p[0] <= hx1 + 0.5):
            f.tex = T('sink'); f.sc = (1, 1)


def counters():
    gt = {'top': T('granite'), 'side': T('granite_edge'), 'bot': T('cab_wood')}
    # back counter
    A(box((-XW + 8, BC0, -SLAB), (XW - 8, YB - 8, 0), gt))
    cab_body(-XW + 8, BC0 + 24, XW - 8, YB - 8, 's')
    for s in (1, -1):
        A(sb(s, -XW + 8, SY0, -SLAB, -SX, BC0, 0, gt))
        xa, xb = sorted((s * (-XW + 8), s * (-SX - 24)))
        cab_body(xa, SY0 + 24, xb, BC0 + 24, 's' + ('e' if s > 0 else 'w'))
    # island: slab with the sink hole, body round the basin
    hole = SK
    for r in sub_rects((-IX, IY0, IX, IY1), [hole]):
        b = box((r[0], r[1], -SLAB), (r[2], r[3], 0), gt); _sinkfaces(b, hole); A(b)
    cab_body(-IX + 24, IY0 + 24, IX - 24, IY1 - 24, 'nsew', sink_hole=hole)
    # basin floor
    A(box((SK[0], SK[1], SKZ - 16), (SK[2], SK[3], SKZ), {'top': T('sink'), 'side': T('sink'), 'bot': CAULK}))


# =================================================================================================== sink
def sink():
    x0, y0, x1, y1 = SK
    ramps = []; clips = []
    for s in (1, -1):
        # cutting-board ramp: plank leaning from the basin floor (x -128) up to the rim (x -640), against the south wall
        pts = [(-640, 0), (-128, SKZ), (-165, SKZ), (-640, -32)]
        b = sh(s, [(x, y, z) for (x, z) in pts for y in (y0, y0 + 192)], {'top': T('board_dark'), 'side': T('board'), 'bot': T('board')})
        A(b); ramps.append(b)
        # a stack of (catalog) plates standing in the water (cover) and a saucer
        smdl(s, 'pad_plates/plate_hpstack2.md3', -440, -560, SKZ, 1.3, 20, round_n=12, shrink=0.08)
        clips.append(M.world[-1])
        smdl(s, 'pad_plates/plate_coffeeblue.md3', -200, -720, SKZ, 1.3, 70)
    # plate stack in the middle with the jump pad up to the faucet spout
    stack = []
    for (r, za, zb) in ((120, SKZ, SKZ + 32), (104, SKZ + 32, SKZ + 64), (88, SKZ + 64, SKZ + 96)):
        b = cyl(0, -880, r, za, zb, {'top': T('plate'), 'side': T('plate_side'), 'bot': T('plate_side')}, 16)
        hfit(b, -r, -880 - r, r, -880 + r, 256, 256, T('plate')); A(b); stack.append(b)
    jumppad(0, -880, SKZ + 96, (0, -560, KM.FAUCET_TOP), 900, 'faucet')
    # water: one box carved round the ramps and the plate stack; only the top faces draw
    wb = box((x0, y0, SKZ), (x1, y1, WZ), T('water'))
    for p in carve(wb, ramps + stack + clips, T('water')):
        for f in p.faces:
            f.tex = T('water') if f.n[2] > 0.9 and abs(f.d - WZ) < 0.5 else T('water_inner')
        A(p)
    # foam drifting on the water
    for (x, y, w, a) in ((-300, -500, 220, 10), (260, -470, 180, 100), (-520, -660, 160, 60), (480, -650, 200, 140), (-120, -720, 140, 30),
                         (150, -980, 160, 0), (-470, -980, 120, 90), (520, -960, 120, 80), (0, -430, 200, 0)):
        A(sprite(x, y, WZ - 4, WZ + 30, 'foam', w, a))
    # running water from the aerator onto the plate stack
    tipy = FAUCET[1] - KM.FAUCET_REACH + 44
    A(sprite(0, tipy, SKZ + 100, 546, 'stream', 36))
    speaker(0, tipy, WZ + 60, 'sound/world/ambient/water_flowing.ogg')
    speaker(0, -700, WZ + 20, 'sound/world/ambient/water_drain.ogg')
    # loot
    weapon(1, 'betty', 0, -560, SKZ, 'black')
    for s in (1, -1):
        item(s, 'ammo_betty', -560, -760, SKZ)
    light(0, -700, 200, 900, '0.92 0.97 1')
    for s in (1, -1):
        slight(s, -400, -700, -200, 500, '0.9 0.96 1')
    light(0, -700, -300, 400, '0.85 0.95 1')


def faucet():
    fx, fy = FAUCET
    M.model('models/padkitchen/faucet.md3', (fx + KM.FAUCET_OFS[0], fy + KM.FAUCET_OFS[1], KM.FAUCET_OFS[2]), spawnflags=4,
            _castshadows=1, _receiveshadows=1, _lightmapscale=0.5)
    A(cyl(fx, fy, 54, 0, 576, WCLIP, 12))
    A(box((fx - 56, fy - KM.FAUCET_REACH, 576), (fx + 56, fy + 56, 640), WCLIP))
    weapon(1, 'imperius', 0, fy - 180, 640, 'purple')
    light(0, fy - 300, 900, 500, '1 0.97 0.9')


# =================================================================================================== bridges
def bridges():
    # wooden spatula across the middle of the aisle: handle on the counters, blade on the cooktop (neutral lolly)
    b = box((-48, -200, 0), (48, ST_COOK_Y0, 16), {'top': T('board'), 'side': T('board'), 'bot': T('board')}); A(b)
    A(box((-112, ST_COOK_Y0, 16), (112, 800, 28), {'top': T('board'), 'side': T('board'), 'bot': T('board')}))
    item(1, 'team_CTL_neutrallolly', 0, 192, 16)
    for s in (1, -1):
        # cutting boards
        A(sb(s, -1342, -200, 0, -958, 584, 16, {'top': T('board'), 'side': T('board_dark'), 'bot': T('board_dark')}))
        A(sb(s, -1180, 520, 16, -1120, 560, 18, T('board_dark')))  # little juice groove end-stop (visual)
        # bread board from the side counter to the island end, a baguette lying along its north edge (cover)
        xa, xb, yc = -2240, -1728, BREAD_Y
        A(sb(s, xa, yc - 160, 0, xb, yc + 160, 16, {'top': T('board_dark'), 'side': T('board'), 'bot': T('board')}))
        bx0, bx1, by = -2140, -1828, yc + 100
        pts = []
        for (x, hw, h) in ((bx0, 34, 16), (bx0, 20, 40), (bx0 + 50, 56, 16), (bx0 + 50, 50, 56), (bx0 + 50, 30, 74),
                           (bx1 - 50, 56, 16), (bx1 - 50, 50, 56), (bx1 - 50, 30, 74), (bx1, 34, 16), (bx1, 20, 40)):
            pts += [(x, by - hw, h), (x, by + hw, h)]
        A(sh(s, pts, {'top': T('baguette'), 'side': T('baguette'), 'bot': T('crust')}))
        item(s, 'ammo_imperius', -1150, 40, 16)
        # a teacup standing on the cutting board (breaks the long view down the aisle)
        smdl(s, 'pad_cups/pad_cup02.md3', -1250, 330, 16, 1.5, 250, round_n=10, shrink=0.2)
        smdl(s, 'pad_condiments/pepper.md3', -1270, 192, 16, 6.0, 0, round_n=10)
        smdl(s, 'pad_condiments/salt.md3', -1270, 40, 16, 6.0, 0, round_n=10)


# =================================================================================================== toaster (team base)
def oct_pts(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def toaster(s):
    team = 'red' if s > 0 else 'blue'
    x0, y0, x1, y1 = TA
    en = T('toaster_' + team)
    outer = oct_pts(x0, y0, x1, y1, TCH)
    inner = oct_pts(x0 + TT, y0 + TT, x1 - TT, y1 - TT, TCH - 14)
    # doors: (edge index, centre along the edge param 0..1 is not needed: give the opening as coordinate ranges)
    # edge 0 = south (y0), 2 = east (x1), 4 = north (y1)
    doors = {0: ('x', TXM - 64, TXM + 64), 4: ('x', TXM - 64, TXM + 64), 2: ('y', -128, 0)}
    DZ = 176
    bands = ((16, 360, en), (360, 400, T('chrome')), (400, 480, en))
    for k in range(8):
        a0, a1 = outer[k], outer[(k + 1) % 8]; b0, b1 = inner[k], inner[(k + 1) % 8]
        segs = [(0.0, 1.0, 16)]
        if k in doors:
            ax, lo, hi = doors[k]
            i = 0 if ax == 'x' else 1
            t0 = (lo - a0[i]) / (a1[i] - a0[i]); t1 = (hi - a0[i]) / (a1[i] - a0[i])
            t0, t1 = sorted((t0, t1))
            segs = [(0.0, t0, 16), (t1, 1.0, 16), (t0, t1, DZ)]
        for (ta, tb, zfrom) in segs:
            def P(p, q, t): return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            q = [P(a0, a1, ta), P(a0, a1, tb), P(b0, b1, tb), P(b0, b1, ta)]
            for (za, zb, tx) in bands:
                za2 = max(za, zfrom)
                if za2 >= zb: continue
                if zfrom == DZ and za < DZ < zb:
                    pass
                wb = sh(s, [(x, y, z) for (x, y) in q for z in (za2, zb)], {'side': tx, 'top': tx, 'bot': tx}, rnd=False)
                for f in wb.faces:       # faces looking into the toaster are dark metal, not enamel
                    if abs(f.n[2]) < 0.1:
                        p = f.pts[0]
                        if f.n[0] * (s * TXM - p[0]) + f.n[1] * (TYM - p[1]) > 1 and abs(f.d - (f.n[0] * s * TXM + f.n[1] * TYM)) > 150:
                            f.tex = T('toaster_in')
                    elif f.n[2] < -0.7 and za2 == DZ:
                        f.tex = T('toaster_in')
                A(wb)
            if zfrom == DZ:      # door lintel face below band 1 start: covered by the loop (za2 = DZ)
                pass
    # base plinth (black) and roof plate with the two bread slots
    A(sh(s, [(x, y, z) for (x, y) in outer for z in (0, 16)], {'top': T('toaster_in'), 'side': T('toaster_base'), 'bot': CAULK}))
    roof = sh(s, [(x, y, z) for (x, y) in outer for z in (480, TROOF)], {'top': T('chrome'), 'side': T('chrome'), 'bot': T('toaster_in')})
    cutters = [sb(s, SLOT_A[0], SLOT_Y[0], 470, SLOT_A[1], SLOT_Y[1], 520, CAULK), sb(s, SLOT_B[0], SLOT_Y[0], 470, SLOT_B[1], SLOT_Y[1], 520, CAULK)]
    xa, xb = sorted((s * x0, s * x1))
    for p in carve(roof, cutters):
        for f in p.faces:
            if abs(f.n[2]) < 0.1:
                px, py = (sum(q[0] for q in f.pts) / 3, sum(q[1] for q in f.pts) / 3)
                if xa + 60 < px < xb - 60 and y0 + 60 < py < y1 - 60:
                    f.tex = T('toaster_in')
        A(p)
    # coils on the inside of the long walls (thin glowing panels standing 2 off the wall, nonsolid)
    for (xa, xb) in ((x0 + TT, x0 + TT + 2), (x1 - TT - 2, x1 - TT)):
        for (ya, yb) in ((y0 + TT + 64, -560), (-336, y1 - TT - 64)):
            if xa > x0 + TT + 10 and ya < -384 < yb: continue
            fdir = 'e' if xa < TXM else 'w'
            A(sb(s, xa, ya, 200, xb, yb, 440, {'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS,
                                                fdir: T('coils')}))
    # toast slice standing in slot A (south half): pillar inside, cover on the roof
    tz = TROOF + 160
    tp = [(SLOT_A[0] + 16, SLOT_Y[0], 16), (SLOT_A[0] + 48, SLOT_Y[0], 16), (SLOT_A[0] + 16, -448, 16), (SLOT_A[0] + 48, -448, 16)]
    for x in (SLOT_A[0] + 16, SLOT_A[0] + 48):
        tp += [(x, SLOT_Y[0], tz - 40), (x, -448, tz - 40), (x, SLOT_Y[0] + 30, tz), (x, -478, tz)]
    tb = sh(s, tp, {'e': T('toast'), 'w': T('toast'), 'side': T('crust'), 'top': T('crust'), 'bot': CAULK})
    for f in tb.faces:
        if f.tex == T('toast'): fit_face(f, SLOT_Y[0], -448, 16, tz, 256, 256)
    A(tb)
    # exterior details: team logo on the east face, lever + dial, chrome feet
    A(ssign(s, (TXM - 128, y1, 220), (TXM + 128, y1 + 4, 284), T('logo_' + team), 512, 128, 'n', T('chrome')))
    A(sb(s, TXM + 120, y0 - 40, 400, TXM + 200, y0, 440, T('toaster_base')))
    A(sb(s, TXM + 150, y0 - 4, 300, TXM + 170, y0, 400, T('toaster_base')))     # lever slot plate
    A(sh(s, [(TXM - 170 + 32 * math.cos(a), y0 - dz, 260 + 32 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False) for dz in (0, 24)],
         T('toaster_base'), rnd=True))
    # interior: lolly dais, health station
    A(sb(s, TXM - 48, TYM - 48, 16, TXM + 48, TYM + 48, 32, {'top': T('chrome'), 'side': T('toaster_base'), 'bot': CAULK}))
    lol = 'team_CTL_%slolly' % team
    M.ent(lol, (s * TXM, TYM, 32 + 16)); SPOTS['item'].append((lol, s * TXM, TYM, 32))
    M.ent('station_health', (s * (x0 + TT + 56), -820, 16), angle=(0 if s > 0 else 180))
    item(s, 'item_armor_shard', x1 - 100, -800, 16)
    item(s, 'item_armor_shard', x1 - 100, -120, 16)
    slight(s, TXM, -700, 330, 260, '1 0.6 0.3'); slight(s, TXM, -150, 330, 260, '1 0.6 0.3'); slight(s, TXM, TYM, 120, 160, '1 0.8 0.6')
    speaker(s * TXM, TYM, 300, 'sound/world/machine/electric_sizzle.ogg')
    # roof: Balloony, toast slice cover
    weapon(s, 'balloony', TXM, -900, TROOF, 'green')
    item(s, 'ammo_nipper', TXM, 0, TROOF)
    slight(s, TXM, -400, TROOF + 260, 400)
    # toast-stack stairs up the wall side to the roof (16u steps)
    stt = {'top': T('bread'), 'side': T('crust'), 'bot': CAULK}
    for b in stairs(TST[0], -1216, TST[1], -192, 0, TROOF, 'n', stt):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], stt))


def ssign(s, mn, mx, tex, tw, th, facing, back):
    if s > 0: return sign_box(mn, mx, tex, tw, th, back=back, facing=facing)
    sw = {'e': 'w', 'w': 'e', 'n': 'n', 's': 's'}
    return sign_box((-mx[0], mn[1], mn[2]), (-mn[0], mx[1], mx[2]), tex, tw, th, back=back, facing=''.join(sw[c] for c in facing))


# =================================================================================================== side counter + corner
def side_counter(s):
    team = 'red' if s > 0 else 'blue'
    # rolling pin on the north part (cover): wooden cylinder lying along y with handles
    rp = []
    for (y0, y1, r) in ((180, 440, 56),):
        rp.append(sh(s, [(-2930 + r * math.cos(a), y, r + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False) for y in (y0, y1)],
                     {'side': T('board'), 'n': T('board_dark'), 's': T('board_dark')}))
    A(rp)
    for (y0, y1) in ((120, 180), (440, 500)):
        A(sh(s, [(-2930 + 20 * math.cos(a), y, 56 + 20 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False) for y in (y0, y1)],
             T('board_dark')))
    # catalog clutter (all resting on the counter)
    smdl(s, 'pad_condiments/salt.md3', -2260, 150, 0, 4.0, 0, round_n=8)
    M.model(f'models/padkitchen/kettle_{team}.md3', (s * -2400, 360, 0), angle=90, spawnflags=4, _castshadows=1, _lightmapscale=0.5)
    A(scyl(s, -2400, 360, 130, 0, 300, WCLIP, 16))
    speaker(s * -2400, 360, 200, 'sound/world/machine/coffee_maker.ogg')
    smdl(s, 'pad_tins/tomatoes_tl.md3', -2980, -1180, 0, 1.3, 30, round_n=12)
    smdl(s, 'pad_fruits/orange.md3', -2780, 200, 0, 1.4, 0)
    # spawns
    for (x, y, a) in ((-2700, 300, 0), (-2400, 160, 0), (-2840, -1120, 90), (-2300, -1040, 90)):
        spawn(s, 'team_%splayer' % team, x, y, 0, a)
    for (x, y, z, a) in ((-2830, 400, 0, 0), (-2600, 160, 0, 0), (-2950, -1040, 0, 0), (-2272, -300, 0, 90), (-2350, 960, 0, 0),
                         (TXM, -500, TROOF, 0), (-2272, -840, 0, 90)):
        spawn(s, 'team_%sspawn' % team, x, y, z, a)
    # loot
    item(s, 'ammo_bubbleg', -2560, 230, 0)
    item(s, 'ammo_pumper', -2750, -1180, 0)
    item(s, 'ammo_splasher', -2290, -160, 0)
    item(s, 'item_speedy', -2290, -1110, 0)
    slight(s, -2600, 300, 400, 700); slight(s, -2500, -1100, 400, 600); slight(s, -2272, -400, 300, 400)


def corner(s):
    """back counter corner (x -XW..-SX): paper towel holder with a pad to its top (Pad shield), health station"""
    cx, cy = -2780, 980
    A(scyl(s, cx, cy, 200, 0, 16, {'top': T('chrome'), 'side': T('chrome'), 'bot': CAULK}, 24))
    roll = scyl(s, cx, cy, 168, 16, 664, {'top': T('core'), 'side': T('towel'), 'bot': CAULK}, 24)
    A(roll)
    A(scyl(s, cx, cy, 20, 664, 760, T('chrome'), 12))
    A(scyl(s, cx, cy, 34, 760, 784, T('chrome'), 12))
    spad(s, -2470, 720, 0, (cx + 70, cy - 40, 664), 860, 'towel_%s' % ('r' if s > 0 else 'b'))
    item(s, 'item_armor_padshield', cx + 96, cy - 30, 664)
    item(s, 'ammo_balloony', cx - 80, cy - 90, 664)
    M.ent('station_health', (s * -2300, 1180, 0), angle=(270 if s > 0 else 270))
    item(s, 'ammo_balloony', -2300, 640, 0)
    item(s, 'ammo_nipper', -2830, 620, 0)
    smdl(s, 'pad_cups/pad_cup03.md3', -2960, 640, 0, 1.4, 200, round_n=10, shrink=0.2)
    slight(s, cx, cy, 900, 600); slight(s, -2500, 700, 300, 400)


# =================================================================================================== back counter
def cereal_box(s, x0, y0, x1, y1, h, art, edge):
    """lying cereal box (front art on top), open south end, a torn hole in the west side, walls 12, floor 8"""
    t, fl = 12, 8
    cin = T('cardboard_in')
    xa, xb = sorted((s * x0, s * x1))
    A(hfit(sb(s, x0, y0, h - t, x1, y1, h, {'top': T(art), 'side': T(edge), 'bot': cin}), xa, y0, xb, y1, 512, 768, T(art)))
    A(sb(s, x0, y0, 0, x1, y1, fl, {'top': cin, 'side': T(edge), 'bot': CAULK}))
    # north end wall (closed)
    A(sb(s, x0, y1 - t, fl, x1, y1, h - t, {'side': T(edge), 's': cin, 'top': cin, 'bot': cin}))
    # east wall (solid) and west wall with a torn doorway (y 880..1008)
    A(sb(s, x1 - t, y0, fl, x1, y1 - t, h - t, {'side': T(edge), 'w': cin, 'top': cin, 'bot': cin}))
    for (ya, yb) in ((y0, 880), (1008, y1 - t)):
        A(sb(s, x0, ya, fl, x0 + t, yb, h - t, {'side': T(edge), 'e': cin, 'top': cin, 'bot': cin}))
    # torn flaps at the open south end (low, thin, lying on the counter = little lips)
    A(sb(s, x0 + 24, y0 - 72, 0, x1 - 24, y0, 4, {'top': T('cardboard'), 'side': T('cardboard'), 'bot': CAULK}))


def back_counter(s):
    # cereal box tunnel
    bx0, by0, bx1, by1 = -2112, 640, -1728, 1216
    cereal_box(s, bx0, by0, bx1, by1, 144, 'cereal1' if s > 0 else 'cereal2', 'cereal1_edge' if s > 0 else 'cereal2_edge')
    weapon(s, 'bubbleg', -1920, 1080, 8, 'blue')
    item(s, 'ammo_balloony', -1830, 700, 8)
    item(s, 'ammo_boaster', -1920, 900, 144)
    item(s, 'item_armor_shard', -2040, 1150, 144)
    # sugar cube steps up the east side to the box top
    for k in range(4):
        ya = 900 + 64 * k
        A(sb(s, bx1, ya, 0, bx1 + 64, ya + 64, 32 * (k + 1), {'top': T('sugar'), 'side': T('sugar'), 'bot': CAULK}))
    mdl(f'models/padkitchen/cereal_spill{1 if s > 0 else 2}.md3', s * -1440, 1090, 0, 1.0, 0)
    # open upper cabinet pad (Splasher), coffee corner clutter
    spad(s, -1024, 720, 0, (-1024, 1120, CAB_Z0 + 16), 1250, 'cab_%s' % ('r' if s > 0 else 'b'))
    smdl(s, 'pad_tins/tomatoes_tbl.md3', -1560, 600, 0, 1.4, 0, round_n=12)
    smdl(s, 'pad_cups/pad_cup05.md3', -1100, 1150, 0, 1.5, 300, round_n=10, shrink=0.25)
    smdl(s, 'pad_tins/pad_milk_s.md3', -880, 1160, 0, 1.6, 0, round_n=10)
    item(s, 'ammo_pumper', -1350, 800, 0)
    item(s, 'ammo_betty', -1150, 650, 0)
    slight(s, -1920, 920, 80, 220, '1 0.92 0.8')
    slight(s, -1400, 800, 500, 600); slight(s, -2000, 600, 400, 500)


# =================================================================================================== stove + hood + cabinets
ST_COOK_Y0 = BC0 + 32


def stove():
    # cooktop slab (black glass) with a steel frame, knob panel on the counter's front edge below
    A(box((-ST_X, ST_COOK_Y0, 0), (ST_X, YB - 16, 16), {'top': T('cooktop'), 'side': T('steel'), 'bot': CAULK}))
    A(sign_box((-ST_X, BC0 + 20, -SLAB - 96), (ST_X, BC0 + 24, -SLAB), T('knobs'), 1024, 128, back=T('steel'), facing='s'))
    A(sign_box((-ST_X + 64, BC0 + 20, -SLAB - 96 - 520), (ST_X - 64, BC0 + 24, -SLAB - 104), T('oven_door'), 1024, 512, back=T('steel'), facing='s'))
    for s in (1, -1):
        fx, fy = -384, 704
        # front grate + lit burner
        A(sb(s, fx - 152, ST_COOK_Y0 + 8, 16, fx + 152, 856, GRATE_Z, {'top': T('grate'), 'side': T('grate'), 'bot': CAULK}))
        for k in range(8):
            a = 2 * math.pi * k / 8
            A(sprite(s * fx + 64 * math.cos(a), fy + 64 * math.sin(a), GRATE_Z, GRATE_Z + 56, 'flame', 22, math.degrees(a) + 90))
        M.ent('trigger_hurt', brushes=[sb(s, fx - 96, fy - 96, GRATE_Z, fx + 96, fy + 96, GRATE_Z + 80, TRIG)], dmg=15, spawnflags=16)
        speaker(s * fx, fy, GRATE_Z + 40, 'sound/world/ambient/fire_sizzling.ogg')
        slight(s, fx, fy, GRATE_Z + 100, 220, '0.45 0.6 1')
        # back grate + stock pot (MD3 with brush collision), pad up to the lid
        px, py = POT
        A(sb(s, px - 200, 856, 16, px + 200, YB - 24, GRATE_Z, {'top': T('grate'), 'side': T('grate'), 'bot': CAULK}))
        M.model(f'models/padkitchen/pot_{"red" if s > 0 else "blue"}.md3', (s * px, py, GRATE_Z), spawnflags=4, _castshadows=1, _receiveshadows=1,
                _lightmapscale=0.5)
        A(scyl(s, px, py, 190, GRATE_Z, GRATE_Z + 322, WCLIP, 16))
        A(hull([(x, y, GRATE_Z + 322) for (x, y) in ngon(s * px, py, 194, 16)] + [(x, y, GRATE_Z + 345) for (x, y) in ngon(s * px, py, 150, 16)], WCLIP))
        lidz = GRATE_Z + 345
        spad(s, -96, 980, 16, (px + 40, py - 100, lidz), 560, 'pot_%s' % ('r' if s > 0 else 'b'))
        weapon(s, 'boaster', px + 100, py - 20, lidz, 'orange')
        for k in range(4):
            a = 2 * math.pi * k / 4 + 0.4
            A(sprite(s * px + 175 * math.cos(a), py + 175 * math.sin(a), lidz + 4, lidz + 150, 'steam', 48, math.degrees(a) + 90))
        speaker(s * px, py, lidz + 30, 'sound/world/ambient/water_bubbling.ogg')


def hood_and_cabinets():
    # range hood: canopy (lights underneath), walkable top, chimney to the ceiling
    A(box((-ST_X, HOOD_Y0, HOOD_Z0), (ST_X, YB - 8, HOOD_Z1), {'bot': T('hood_lights'), 'side': T('steel'), 'top': T('steel')}))
    for f in M.world[-1].faces:
        if f.n[2] < -0.9: f.sc = (2 * ST_X / 512 / 2, (YB - 8 - HOOD_Y0) / 256); f.off = (0, 0)
    A(box((-256, 1120, HOOD_Z1), (256, YB, ZC), T('steel_v')))
    item(1, 'item_padpower', 0, 1000, HOOD_Z1)
    for s in (1, -1):
        light(s * 400, 1060, HOOD_Z0 - 24, 520, '1 0.95 0.85')
        item(s, 'ammo_imperius', -600, 1000, HOOD_Z1)
    for s in (1, -1):
        door = {'side': T('cab_wood'), 's': T('cab_door'), 'top': T('cab_wood'), 'bot': T('cab_wood')}
        # closed cabinets
        for (xa, xb) in ((-SX, -1728), (-1728, -1280)):
            b = sb(s, xa, CAB_Y0, CAB_Z0, xb, YB, CAB_Z1, door)
            vfit(b, CAB_Z1, CAB_Z0, 512, (abs(xb - xa) / 2) / 256, T('cab_door')); A(b)
        # open cabinet: bottom, top, shelf, west side, back; door swung open (stands out over the counter)
        x0, x1 = -1280, -ST_X
        ci = T('cab_inside')
        A(sb(s, x0, CAB_Y0, CAB_Z0, x1, YB, CAB_Z0 + 16, {'top': ci, 'side': T('cab_wood'), 'bot': T('cab_wood')}))
        A(sb(s, x0, CAB_Y0, CAB_Z1 - 16, x1, YB, CAB_Z1, {'bot': ci, 'side': T('cab_wood'), 'top': T('cab_wood')}))
        A(sb(s, x0 + 16, CAB_Y0, SHELF_Z, x1, YB - 16, SHELF_Z + 16, {'side': T('cab_wood'), 'top': ci, 'bot': ci}))
        A(sb(s, x0, CAB_Y0, CAB_Z0 + 16, x0 + 16, YB, CAB_Z1 - 16, {'side': T('cab_wood'), 'e': ci}))
        A(sb(s, x0 + 16, YB - 16, CAB_Z0 + 16, x1, YB, CAB_Z1 - 16, {'side': T('cab_wood'), 's': ci}))
        b = sb(s, x0 - 16, CAB_Y0 - 448, CAB_Z0, x0, CAB_Y0, CAB_Z1, {'side': T('cab_wood'), 'e': T('cab_door'), 'w': T('cab_wood')})
        A(b)
        weapon(s, 'splasher', -1024, 1120, CAB_Z0 + 16, 'orange')
        smdl(s, 'pad_tins/tomatoes_ts.md3', -1200, 1180, CAB_Z0 + 16, 1.5, 0, round_n=10)
        smdl(s, 'pad_condiments/pad_ketchup.md3', -900, 1200, SHELF_Z + 16, 2.2, 0)
        smdl(s, 'pad_condiments/pad_mustard.md3', -980, 1190, SHELF_Z + 16, 2.2, 0)
        smdl(s, 'pad_condiments/sugar.md3', -1120, 1180, SHELF_Z + 16, 2.6, 0)
        smdl(s, 'pad_teabags/squareteabag.md3', -1150, 1080, CAB_Z0 + 16, 1.4, 20)
        slight(s, -1024, 1100, 1300, 300, '1 0.9 0.75')
        # under-cabinet LED strips (front edge)
        for (xa, xb) in ((-SX + 32, -1312), (x0 + 32, x1 - 32)):
            A(sb(s, xa, CAB_Y0 + 16, CAB_Z0 - 4, xb, CAB_Y0 + 40, CAB_Z0, {'bot': T('led'), 'side': T('cab_wood'), 'top': CAULK}))
        # cereal boxes standing on top of the cabinets (decoration)
        for (xa, xb, art, ed) in ((-2100, -1820, 'cereal3', 'cereal3_side'), (-1760, -1480, 'cereal1' if s > 0 else 'cereal2', 'cereal1_side' if s > 0 else 'cereal2_side')):
            b = sb(s, xa, 1100, CAB_Z1, xb, 1240, CAB_Z1 + 280, {'s': T(art), 'side': T(ed), 'top': T('cardboard'), 'bot': CAULK})
            for f in b.faces:
                if f.tex == T(art): fit_face(f, min(s * xa, s * xb), max(s * xa, s * xb), CAB_Z1, CAB_Z1 + 280, 512, 768)
            A(b)


# =================================================================================================== island
def island(s):
    # fallen paper towel roll (lying along x) with its sheet unrolled into a ramp up to the top
    rx0, rx1, ry, r = -1600, -1184, -1150, 128
    roll = sh(s, [(x, ry + r * math.cos(a), r + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False) + math.pi / 24 for x in (rx0, rx1)],
              {'side': T('towel'), 'e': T('core'), 'w': T('core')})
    A(roll)
    # sheet ramp (8 thick) from the counter (y -540) up to where it meets the roll near its top, almost tangent
    # (23 deg) so it never runs into the roll's steep side; carved round the roll anyway
    ye = ry + 50; ze = round(r + math.sqrt(r * r - 50 * 50))
    ramp = sh(s, [(x, y, z) for x in (rx0 + 100, rx1 - 100) for (y, z) in ((-540, 0), (-550, 0), (ye, ze - 8), (ye, ze))],
              {'top': T('towel'), 'side': T('towel'), 'bot': T('towel')})
    for p in carve(ramp, [roll]): A(p)
    item(s, 'ammo_splasher', -1392, ry, round(r + r * math.cos(math.pi / 24)))
    item(s, 'item_armor_shard', -1100, -760, 0)
    # donut stacks (MD3s with weapon-clip collision)
    stacks = [(-1600, -400, 3, 'pink'), (-860, -320, 2, 'choc'), (-900, -980, 1, 'pink')]
    for i, (x, y, n, kind) in enumerate(stacks):
        for k in range(n):
            ox, oy = (12 * ((k * 7 + i) % 3 - 1), 10 * ((k * 5 + i) % 3 - 1))
            z = k * 84
            kk = kind if k % 2 == 0 else ('choc' if kind == 'pink' else 'pink')
            M.model(f'models/padkitchen/donut_{kk}.md3', (s * (x + ox), y + oy, z), angle=(k * 47 + i * 30) % 360)
            A(cyl(round(s * (x + ox)), round(y + oy), 132, z, z + 84, WCLIP, 12))
    # sponges with forks (catalog forks standing on the sponge, tines down)
    for (x, y, ang) in ((-1150, -330, 0),):
        A(sb(s, x - 104, y - 64, 0, x + 104, y + 64, 56, {'top': T('sponge'), 'side': T('sponge'), 'bot': CAULK}))
        A(sb(s, x - 104, y - 64, 56, x + 104, y + 64, 72, {'top': T('scrub'), 'side': T('scrub'), 'bot': CAULK}))
        for dx in (-40, 40):
            fork(s, x + dx, y, 72)
    # cans and clutter
    smdl(s, 'pad_tins/pad_coke.md3', -1720, -1180, 0, 1.35, 30, round_n=12)
    smdl(s, 'pad_tins/pad_pupsi.md3', -700, -620, 0, 1.35, 200, round_n=12)
    smdl(s, 'pad_tins/pad_coke_sd.md3', -1000, -1180, 0, 1.35, 10, solid=True)
    smdl(s, 'pad_fruits/banana.md3', -760, -1210, 0, 1.5, 0)
    smdl(s, 'pad_scouringpad/scouringpad_green.md3', -1380, -230, 0, 2.0, 40)
    smdl(s, 'pad_tins/pad_coke.md3', -420, -1160, 0, 1.35, 120, round_n=12)
    M.model('models/padkitchen/soap.md3', (s * -700, -760, 0), angle=(30 if s > 0 else 150), spawnflags=4, _lightmapscale=0.5)
    A(scyl(s, -700, -760, 64, 0, 388, WCLIP, 12))
    # loot
    weapon(s, 'pumper', -1240, -640, 0, 'green')
    item(s, 'ammo_bubbleg', -1000, -1090, 0)
    item(s, 'ammo_boaster', -420, -250, 0)
    item(s, 'ammo_nipper', -1660, -250, 0)
    item(s, 'holdable_floater', -1650, -1050, 0)
    # flies circling the donuts
    cx, cy, cz = -1300, -650, 420
    org = sb(s, cx - 8, cy - 8, cz - 8, cx + 8, cy + 8, cz + 8, ORIGIN)
    nd = sb(s, cx - 8, cy - 8, cz + 8, cx + 8, cy + 8, cz + 24, NODRAW_NS)
    M.ent('func_rotating', brushes=[org, nd], model2='models/padkitchen/flies.md3', speed=70 * s, spawnflags=0, dmg=0)
    speaker(s * cx, cy, cz, 'sound/world/animal/fly_crazy.ogg')
    slight(s, -1300, -700, 600, 900); slight(s, -900, -300, 300, 400); slight(s, -1500, -1100, 400, 500)


def fork(s, x, y, zsurf):
    """catalog fork standing upright on a surface: its tines are the -x end, pitch -90 turns -x down (z' = x)"""
    sc = 1.3
    b = BOUNDS['models/mapobjects/pad_cutlery/pad_fork.md3']
    zmin = b['min'][0] * sc
    M.model('models/mapobjects/pad_cutlery/pad_fork.md3', (round(s * x), round(y), round(zsurf - zmin, 2)), scale=sc, angles=(-90, 0, 0))
    A(box((round(s * x) - 8, round(y) - 18, zsurf), (round(s * x) + 8, round(y) + 18, round(zsurf + (b['max'][0] - b['min'][0]) * sc - 6)), WCLIP))


# =================================================================================================== far side of the kitchen (decoration)
FRIDGE = (-448, YS + 12, 448, YS + 652, 1100)     # x0, y0, x1, y1, top
DOOR = (1700, 2800, 2560)                          # x0, x1, height (life-size next to the 2250-tall fridge)
TABLE = (-2500, -2500, -1300, -1800, -177)         # x0, y0, x1, y1, top: too far from the island to jump to
LEGS = []                                          # (x0, y0, x1, y1) of every table/chair leg (holes in the kill zone)


def dining_table():
    """dining table and chairs on the far side of the kitchen (out of reach, 520u from the island edge)"""
    x0, y0, x1, y1, top = TABLE
    wd = {'top': T('board'), 'side': T('board_dark'), 'bot': T('board_dark')}
    A(box((x0, y0, top - 40), (x1, y1, top), wd))
    for (lx, ly) in ((x0 + 40, y0 + 40), (x1 - 104, y0 + 40), (x0 + 40, y1 - 104), (x1 - 104, y1 - 104)):
        A(box((lx, ly, ZF), (lx + 64, ly + 64, top - 40), T('board_dark'))); LEGS.append((lx, ly, lx + 64, ly + 64))
    seat, sz = 340, -567
    def chair(cx, cy, back):
        sx0, sy0 = cx - seat // 2, cy - seat // 2
        A(box((sx0, sy0, sz - 40), (sx0 + seat, sy0 + seat, sz), wd))
        for (lx, ly) in ((sx0 + 16, sy0 + 16), (sx0 + seat - 56, sy0 + 16), (sx0 + 16, sy0 + seat - 56), (sx0 + seat - 56, sy0 + seat - 56)):
            A(box((lx, ly, ZF), (lx + 40, ly + 40, sz - 40), T('board_dark'))); LEGS.append((lx, ly, lx + 40, ly + 40))
        bx = {'w': (sx0, sy0, sx0 + 36, sy0 + seat), 'e': (sx0 + seat - 36, sy0, sx0 + seat, sy0 + seat),
              's': (sx0, sy0, sx0 + seat, sy0 + 36)}[back]
        A(box((bx[0], bx[1], sz), (bx[2], bx[3], sz + 500), wd))
    chair(x0 - 230, (y0 + y1) // 2, 'w'); chair(x1 + 230, (y0 + y1) // 2, 'e')
    chair(-2030, y0 - 120, 's'); chair(-1670, y0 - 120, 's')
    # laid table: plates, cake stand with cake, cups, fruit (all resting on the table top)
    mdl_c('pad_plates/plate_hp1.md3', -2200, -2150, top, 1.3, 0)
    mdl_c('pad_plates/plate_hp2.md3', -1600, -2150, top, 1.3, 40)
    mdl_c('pad_cake/pad_cakestand.md3', -1900, -2050, top, 1.6, 0)
    mdl_c('pad_cake/pad_cakeslice.md3', -2380, -2330, top, 2.0, 30)
    mdl_c('pad_cups/pad_cup04.md3', -2380, -1950, top, 1.4, 120)
    mdl_c('pad_cups/pad_cup07.md3', -1420, -2350, top, 1.4, 300)
    mdl_c('pad_fruits/orange.md3', -1900, -2350, top, 1.4, 0)
    mdl_c('pad_fruits/apple.md3', -1780, -2380, top, 1.6, 0)
    mdl_c('pad_fruits/banana.md3', -2050, -2380, top, 1.4, 20)
    light(-1900, -2150, top + 500, 900, '1 0.9 0.75')


def room_decor():
    """the far side of the kitchen: a big double-door fridge against the far wall (its top is the secret lookout),
    the door, a painting, wall clocks, a rug and the cat's bowl on the floor (all out of reach except the fridge top)"""
    fx0, fy0, fx1, fy1, ftop = FRIDGE
    b = box((fx0, fy0, ZF), (fx1, fy1, ftop), {'n': T('fridge'), 'side': T('fridge_side'), 'top': T('fridge_top'), 'bot': CAULK})
    for f in b.faces:
        if f.tex == T('fridge'): fit_face(f, fx0, fx1, ZF, ftop, 1024, 2048)
    A(b)
    speaker(0, fy1 + 40, ZF + 1200, 'sound/world/machine/freezer.ogg')
    A(sign_box((DOOR[0], YS, ZF), (DOOR[1], YS + 4, ZF + DOOR[2]), T('door'), 512, 1024, facing='n', back=T('baseboard')))
    dining_table()
    A(sign_box((-2300, YS, ZF + 900), (-1500, YS + 8, ZF + 1500), T('painting'), 512, 384, facing='n', back=T('window_frame')))
    for s in (1, -1):         # wall clocks above the windows
        A(ssign(s, (-XW, -416, 1620), (-XW + 4, -160, 1876), T('clock'), 256, 256, 'e', T('wall')))
    mdl('pad_ddmix/trashcan/cannedfish.md3', 1500, -1900, ZF, 2.5, 0)
    A(box((-860, -2100, ZF), (1200, -1500, ZF + 2), {'top': T('mat_red'), 'side': T('mat_red'), 'bot': CAULK}))
    for (x, y) in ((-2000, -2200), (2000, -2200)):
        light(x, y, ZF + 900, 1500, '1 0.92 0.8')
    # ---- the secret: a mouse hole in the back of each cereal box tunnel -> the top of the fridge
    fy = (fy0 + fy1) / 2
    for s in (1, -1):
        nm = 'secret_%s' % ('r' if s > 0 else 'b')
        A(sb(s, -1840, 1202, 8, -1744, 1204, 104, {'s': T('mousehole'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS}))
        for f in M.world[-1].faces:
            if f.tex == T('mousehole'): fit_face(f, min(s * -1840, s * -1744), max(s * -1840, s * -1744), 8, 104, 128, 128)
        M.ent('trigger_multiple', brushes=[sb(s, -1850, 1060, 8, -1740, 1138, 120, TRIG)], target=nm + '_snd', wait=6)
        speaker(s * -1795, 1100, 60, 'sound/world/misc/secret_found.ogg', loop=False, targetname=nm + '_snd')
        M.ent('trigger_teleport', brushes=[sb(s, -1850, 1140, 8, -1740, 1200, 120, TRIG)], target=nm)
        M.ent('misc_teleporter_dest', (s * 220, round(fy) - 60, ftop + 24), targetname=nm, angle=90)
    # fridge top: lookout with a few treats, a pad back to the island (lands in front of the sink)
    jumppad(0, fy - 140, ftop, (0, IY0 + 110, 0), ftop + 260, 'fridge')
    item(1, 'holdable_killerducks', 0, fy + 140, ftop)
    item(1, 'ammo_splasher', -300, fy + 180, ftop)
    item(1, 'item_armor_shard', 300, fy + 180, ftop)
    mdl_c('gummybears/redbear.md3', -360, fy0 + 60, ftop, 1.6, 300)
    mdl_c('gummybears/greenbear.md3', 360, fy0 + 70, ftop, 1.6, 240)
    mdl_c('gummybears/ldyellowbear.md3', 330, fy - 40, ftop, 1.6, 20)
    b = box((-120, fy0 + 20, ftop), (120, fy0 + 110, ftop + 300), {'n': T('cereal3'), 'side': T('cereal3_side'), 'top': T('cardboard'), 'bot': CAULK})
    for f in b.faces:
        if f.tex == T('cereal3'): fit_face(f, -120, 120, ftop, ftop + 300, 512, 768)
    A(b)
    light(0, fy, ftop + 300, 700, '1 0.95 0.85')
    speaker(0, fy, ftop + 100, 'sound/world/animal/kitten_meow.ogg', loop=False, targetname='meow')
    M.ent('func_timer', (0, fy, ftop + 200), target='meow', wait=50, random=25, spawnflags=1)


def edge_botclip():
    """24u common/botclip strips along every counter edge that drops into the void (bots only; players walk through):
    the AAS keeps bot paths away from the edges, so bots stop slipping off while strafing. Gaps where bridges land."""
    BC = 'common/botclip'
    W, H = 24, 64
    def xstrip(x0, x1, y0, y1, gaps):
        for (a, b) in _gapped(x0, x1, gaps): A(box((a, y0, 0), (b, y1, H), BC))
    def ystrip(y0, y1, x0, x1, gaps):
        for (a, b) in _gapped(y0, y1, gaps): A(box((x0, a, 0), (x1, b, H), BC))
    cb = [(-1342, -958), (958, 1342), (-48, 48)]
    xstrip(-SX, SX, BC0, BC0 + W, cb + [(-112, 112)])                      # back counter front
    xstrip(-IX, IX, IY1 - W, IY1, cb)                                     # island north
    xstrip(-IX, SK[0], IY0, IY0 + W, []); xstrip(SK[2], IX, IY0, IY0 + W, [])  # island south (not in front of the sink)
    xstrip(SK[0], SK[2], IY0, IY0 + W, [])
    for s in (1, -1):
        bg = [(BREAD_Y - 160, BREAD_Y + 160)]
        x0, x1 = sorted((s * -IX, s * (-IX + W)))
        ystrip(IY0 + W, IY1 - W, x0, x1, bg)                               # island ends
        x0, x1 = sorted((s * -SX, s * (-SX - W)))
        ystrip(SY0, BC0, x0, x1, bg)                                       # side counter inner edge
        xa, xb = sorted((s * (-XW + 8), s * -SX))
        xstrip(xa, xb, SY0, SY0 + W, [])                                   # side counter south edge


def _gapped(a, b, gaps):
    out, cur = [], a
    for (g0, g1) in sorted(gaps):
        if g1 <= a or g0 >= b: continue
        if g0 > cur: out.append((cur, g0))
        cur = max(cur, g1)
    if cur < b: out.append((cur, b))
    return out


def kill_zone():
    foot = [(-XW, SY0, -SX, YB), (SX, SY0, XW, YB), (-SX, BC0, SX, YB), (-IX, IY0, IX, IY1), (FRIDGE[0], YS, FRIDGE[2], FRIDGE[3])]
    for r in sub_rects((-XW, YS, XW, YB), foot + LEGS):
        M.ent('trigger_hurt', brushes=[box((r[0], max(r[1], YS + 16), -900), (r[2], r[3], KILLZ), TRIG)], dmg=9999)


def lights_and_sound():
    # ceiling lamps (surface lights) + fill lights over the counters
    for x in (-2200, -1100, 0, 1100, 2200):
        for y in (-700, 700):
            A(box((x - 96, y - 96, ZC - 8), (x + 96, y + 96, ZC), {'bot': T('lamp'), 'side': T('steel'), 'top': CAULK}))
    for x in range(-2600, 2601, 650):
        for y in (-800, 0, 820):
            light(x, y, 1500, 1500)
    for x in (-1500, 0, 1500):
        light(x, -1700, 400, 1400, '1 0.92 0.8')
    speaker(0, 600, 1200, 'sound/world/machine/clock_ticking.ogg')
    speaker(0, 900, 1500, 'sound/world/machine/dingdong.ogg', loop=False, targetname='ding')
    M.ent('func_timer', (0, 200, 1500), target='ding', wait=40, random=20, spawnflags=1)


# =================================================================================================== main
def ffa_spawns():
    for s in (1, -1):
        for (x, y, z, a) in ((-1500, 760, 0, 90), (-1100, 760, 0, 90), (-1150, -880, 0, 0), (-1600, -680, 0, 0), (-500, -250, 0, 0),
                             (-2280, -960, 0, 90), (-2600, 300, 0, 0), (-250, -1150, 0, 0)):
            spawn(s, 'info_player_deathmatch', x, y, z, a)


def main():
    TX.make_all(OUT)
    shell(); counters(); sink(); faucet(); bridges(); stove(); hood_and_cabinets(); room_decor(); kill_zone(); edge_botclip(); lights_and_sound()
    for s in (1, -1):
        toaster(s); side_counter(s); corner(s); back_counter(s); island(s)
    ffa_spawns()
    M.ent('info_player_intermission', (-2000, -1250, 900), angles='22 25 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/kitchen/build_kitchen.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
