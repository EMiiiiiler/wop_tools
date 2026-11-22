#!/usr/bin/env python3
"""Padman's Plumbing (wop_padplumbing) - a cut-away house: bathroom upstairs, the crawlspace under its floor and the
sewer culvert beside it, all joined by pipes.

    OUT=<dir> python3 build_padplumbing.py          (wopbuild.py padplumbing preview / check / ...)

Scale ~6u per cm. x east, y north. Hull x -2048..2048, y -1792..1792, z -192 (canal bed) .. 2000 (ceiling).
Levels:  canal bed -192 / water -48 | sewer hall + crawlspace floor 0 | tunnel walkway 56 | joists 432-480 |
         bathroom floor 512 | toilet seat 764, bath rim 842, vanity counter 1022, cistern 1004, mirror cabinet 1592.
Zones:   bathroom   y 224..1792 at z 512 (open south edge = a balcony over the sewer hall)
         crawlspace y 256..1792 at z 0 under it (piers, joists, the walk-through drain tunnel, valve chamber)
         sewer hall y -1792..224 full height (canal y -1100..-700 with a current, two bridges, water heater, pump)
Mechanics: flush the toilet (walk into the bowl -> drain tunnel), the drain-hole lift and the express pipe over the
canal (pads inside glass pipes), shoot the red valve to open the sluice gate, the bath plughole secret.
See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from wopmap import box, hull, cyl, sub_rects
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL
import plumb_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                       # -2048 -1792 2048 1792
ZB, ZC = -192, 2000                                   # canal bed (hull floor top), ceiling
BZ = 512                                              # bathroom floor
EDGE = 224                                            # bathroom slab south edge / foundation wall south face
CRAWL_Y = 256                                         # crawlspace south face (foundation wall north face)
JZ = 432                                              # joist bottom
CAN = (-1100, -700); WTOP = -48                       # canal y0 y1, water surface
ARCHES = [(-1408, -1216), (-96, 96), (1216, 1408)]; ARCH_TOP = 320
LIFT_HOLE = (-780, 660, -620, 916)                    # bathroom floor hole over the drain lift
TILE_HOLE = (820, 620, 980, 780)                      # missing tile: drop into the crawlspace
TUB_C = (-1440, 1567); TOILET_C = (0, 1480); VAN_C = (1340, 1612)
TUN = dict(x0=-1500, x1=200, y=1100, ri=96, t=24, zc=120, walk=56)
CHAMBER = (1632, 1432, 2048, 1792); GATE_Y = (1540, 1700); GATE_TOP = 200
HEATER = (1500, -1480); PUMP = (-1500, -1500)
CROSS = [-1050, 1200]                                 # brick culvert cross-walls splitting the sewer hall into vaults
CROSS_OPEN = [(-1520, -1200, 0, 420), (CAN[0], CAN[1], ZB, 220), (-500, -160, 0, 420)]   # y0 y1 z0 z1
BRIDGES = {'plank': -900, 'pipe': 700}; BR_W = 224
VAULT = (-400, -400, 400, 400); VZ = -1600
JOISTS = [-1856, -1472, -1088, -320, 256, 640, 1216, 1856]
PIERS = [(640, 1000), (1216, 1060), (-1856, 640), (-1472, 1500), (-1088, 640), (-320, 1500), (256, 640), (640, 1500), (1216, 640)]

K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '22', '_color': '0.95 0.97 1', 'gridsize': '128 128 192'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)


def tex6(**kw):
    d = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; d.update(kw); return d


def cylb(x, y, r, z0, z1):
    return cyl(x, y, r, z0, z1, WCLIP, 10)


# ------------------------------------------------------------------------------------------------ textures
def textures():
    TX.add('floor_tile', TL.checker((236, 238, 240), (60, 120, 170), 8, grout=(200, 204, 208), grout_w=0.015), scale=0.5)
    TX.add('wall_tile', TL.tiles((214, 232, 236), (170, 180, 184), cols=8, rows=8, offset=0, grout_w=0.04, vary=4))
    TX.add('plaster', TL.solid((196, 186, 166), 6, 3, 256))
    TX.add('boards', TL.planks((150, 112, 72), n_planks=4), steps='woodsteps')
    TX.add('joist', TL.grime(TL.planks((136, 98, 60), n_planks=2, grain=12), 0.2), steps='woodsteps')
    TX.add('stairwood', TL.planks((120, 84, 50), n_planks=3), steps='woodsteps')
    TX.add('brick', TL.grime(TL.bricks((128, 70, 54), (120, 112, 102), rows=8, cols=4), 0.3))
    TX.add('brick_dark', TL.grime(TL.bricks((74, 50, 42), (66, 62, 58), rows=8, cols=4, seed=43), 0.4))
    TX.add('concrete', TL.grime(TL.stone((132, 128, 120), cells=30, edge=(110, 106, 100), vary=8), 0.3))
    TX.add('paving', TL.grime(TL.tiles((112, 110, 104), (70, 68, 64), cols=4, rows=4, offset=0.5, grout_w=0.03), 0.35))
    TX.add('canal_bed', TL.grime(TL.stone((70, 84, 60), cells=20, edge=(46, 56, 40)), 0.4))
    TX.add('sluice', TL.grime(TL.stripes((90, 96, 104), (60, 64, 70), 6), 0.3))
    TX.add('sewer_water', TL.solid((50, 80, 44), 10, 11, 128), 'water', rgb=(0.22, 0.34, 0.18), alpha=0.7)
    TX.add('tub_water', TL.solid((80, 160, 200), 10, 13, 128), 'water', rgb=(0.35, 0.65, 0.8), alpha=0.45)
    TX.kit_defaults()
    TX.material('pvc_t', TL.grime(TL.solid((178, 184, 176), 4, 9), 0.3), shade=40)      # drain tunnel solid_piece


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull only (floor slab, walls split by zone so each face gets its material, ceiling, a sky window
    above the toilet); everything inside is detail."""
    K.add(box((X0 - 32, Y0 - 32, ZB - 32), (X1 + 32, Y1 + 32, ZB), tex6(top=T('canal_bed')), detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, EDGE, ZC + 32), tex6(bot=T('brick_dark')), detail=False))
    K.add(box((X0 - 32, EDGE, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('plaster')), detail=False))
    for (xa, xb, face) in ((X0 - 32, X0, 'e'), (X1, X1 + 32, 'w')):
        K.add(box((xa, Y0 - 32, ZB), (xb, EDGE, ZC), tex6(**{face: T('brick')}), detail=False))
        K.add(box((xa, EDGE, ZB), (xb, Y1 + 32, BZ - 32), tex6(**{face: T('concrete')}), detail=False))
        K.add(box((xa, EDGE, BZ - 32), (xb, Y1 + 32, 900), tex6(**{face: T('wall_tile')}), detail=False))
        K.add(box((xa, EDGE, 900), (xb, Y1 + 32, ZC), tex6(**{face: T('plaster')}), detail=False))
    K.add(box((X0, Y0 - 32, ZB), (X1, Y0, ZC), tex6(n=T('brick')), detail=False))
    K.add(box((X0, Y1, ZB), (X1, Y1 + 32, BZ - 32), tex6(s=T('concrete')), detail=False))
    K.add(box((X0, Y1, BZ - 32), (X1, Y1 + 32, 900), tex6(s=T('wall_tile')), detail=False))
    K.sky_window((X0, Y1, 900), (X1, Y1 + 32, ZC), (-360, 360, 1250, 1750), T('plaster'), T('sky'),
                 jamb_tex=T('wall_tile'), glass_tex=T('glass'), face='s')


def floors():
    """ground fill (sewer paving / crawlspace concrete) round the canal trench, the foundation wall with its three
    arches, the bathroom floor slab with the lift hole and the missing tile"""
    for r in sub_rects((X0, Y0, X1, EDGE), [(X0, CAN[0], X1, CAN[1])]):
        K.add(box((r[0], r[1], ZB), (r[2], r[3], 0), {'top': T('paving'), 'side': T('brick'), 'bot': CAULK}))
    K.add(box((X0, EDGE, ZB), (X1, Y1, 0), {'top': T('concrete'), 'side': T('brick'), 'bot': CAULK}))
    bw = {'side': T('brick'), 'top': T('brick'), 'bot': T('brick')}
    xs = [X0] + [v for a in ARCHES for v in a] + [X1]
    for i in range(0, len(xs), 2):
        K.add(box((xs[i], EDGE, 0), (xs[i + 1], CRAWL_Y, BZ - 32), bw))
    for (a, b) in ARCHES:
        K.add(box((a, EDGE, ARCH_TOP), (b, CRAWL_Y, BZ - 32), bw))
        K.keep_clear(a - 32, EDGE - 112, b + 32, CRAWL_Y + 112, 0)
        K.route(f'arch_{a}', ((a + b) / 2, EDGE - 96, 0), ((a + b) / 2, CRAWL_Y + 96, 0))
    st = {'top': T('floor_tile'), 'bot': T('boards'), 'side': T('boards')}
    for r in sub_rects((X0, EDGE, X1, Y1), [LIFT_HOLE, TILE_HOLE]):
        K.add(box((r[0], r[1], BZ - 32), (r[2], r[3], BZ), st))
    for h in (LIFT_HOLE, TILE_HOLE):
        K.keep_clear(h[0] - 64, h[1] - 64, h[2] + 64, h[3] + 64, BZ)
    K.keep_clear(TILE_HOLE[0] - 32, TILE_HOLE[1] - 32, TILE_HOLE[2] + 32, TILE_HOLE[3] + 32, 0)   # landing under the drop


def canal():
    """sewer canal with a gentle eastward current, steps out at both ends and in the middle (never a sheer lip)"""
    y0, y1 = CAN
    ct = {'top': T('concrete'), 'side': T('brick')}
    steps = []
    steps += K.stairs16(X0, y0, X0 + 384, y1, ZB, 0, 'w', ct)
    steps += K.stairs16(X1 - 384, y0, X1, y1, ZB, 0, 'e', ct)
    steps += K.stairs16(-192, y1 - 128, 192, y1, ZB, 0, 'e', ct)
    K.water_box((X0, y0, ZB), (X1, y1, WTOP), T('sewer_water'), cutters=steps)
    for (xa, xb) in ((-1650, -1450), (-650, -450), (900, 1100)):
        K.current((xa, y0 + 40, ZB), (xb, y1 - 140, WTOP), 0, 260, f'current_{-xa}', wait=0.4)
    for nm, x in BRIDGES.items():
        K.add(box((x - BR_W / 2, y0, -16), (x + BR_W / 2, y1, 0), WCLIP))
        K.custom(ML.PLACE[f'{nm}_bridge'], x, (y0 + y1) / 2, 0, occupy=False)
        K.keep_clear(x - BR_W / 2 - 32, y0 - 112, x + BR_W / 2 + 32, y1 + 112, 0)
        K.route(f'bridge_{nm}', (x, y0 - 96, 0), (x, y1 + 96, 0))
    K.keep_clear(X0, y0 - 96, X0 + 480, y1 + 96, 0); K.keep_clear(X1 - 480, y0 - 96, X1, y1 + 96, 0)
    K.keep_clear(-224, y1, 224, y1 + 112, 0)
    K.custom(ML.PLACE['outflow'], X0, (y0 + y1) / 2, 200, occupy=False)
    K.speaker(X0 + 200, (y0 + y1) / 2, 60, 'ambient/water_flowing')
    K.speaker(0, (y0 + y1) / 2, 0, 'ambient/slime_bubbling')
    K.speaker(1300, (y0 + y1) / 2, 0, 'ambient/water_rippling')


def cross_walls():
    """two full-height brick walls across the sewer hall with openings for the south walkway, the canal and the north
    walkway: they turn one 4000u hall into three vaults (sightlines) and frame the express pipe"""
    bw = {'side': T('brick'), 'top': T('brick'), 'bot': T('brick')}
    for x in CROSS:
        ys = [Y0] + [v for o in CROSS_OPEN for v in o[:2]] + [EDGE]
        for i in range(0, len(ys), 2):
            K.add(box((x - 32, ys[i], ZB if ys[i + 1] > CAN[0] and ys[i] < CAN[1] else 0), (x + 32, ys[i + 1], ZC), bw))
        for (a, c, z0, z1) in CROSS_OPEN:
            K.add(box((x - 32, a, z1), (x + 32, c, ZC), bw))
            if z0 == 0: K.keep_clear(x - 140, a, x + 140, c, 0)
        K.reserve(((x - 32, Y0, ZB), (x + 32, EDGE, ZC)))
        K.route(f'vault_s_{x}', (x - 120, -1240, 0), (x + 120, -1240, 0))
        K.route(f'vault_n_{x}', (x - 120, -320, 0), (x + 120, -320, 0))


MAIN_PIPE = (-250, 560, 64)                           # y, z centre, radius of the main sewer pipe slung across the hall


def main_pipe():
    """the big main pipe crossing the hall at balcony eye level, in three spans between the cross-walls"""
    y, z, r = MAIN_PIPE
    xs = [X0, CROSS[0] - 32, CROSS[0] + 32, CROSS[1] - 32, CROSS[1] + 32, X1]
    for i in range(0, len(xs), 2):
        xa, xb = xs[i], xs[i + 1]
        oct_ = [(y + r * math.cos(math.radians(22.5 + 45 * k)), z + r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
        K.add(hull([(x, p[0], p[1]) for x in (xa, xb) for p in oct_], WCLIP, round_pts=False))
        place, o = PM.pipe_run(f'main_pipe_{i}', [(xa, y, z), (xb, y, z)], r + 4, 'rust')
        K.custom(place, xa, y, z, occupy=False)
        K.reserve(((xa, y - r, z - r), (xb, y + r, z + r)))
    for x in (-1700, -400, 500, 1650):          # hanger straps up to the ceiling
        place, o = PM.pipe_run(f'hanger_{x}', [(x, y, z + r), (x, y, ZC)], 6, 'steel')
        K.custom(place, x, y, z + r, occupy=False)


def basement_stairs():
    """two 16u flights from the sewer hall up to the bathroom edge"""
    wt = {'top': T('stairwood'), 'side': T('boards')}
    K.stairs16(400, 64, 912, EDGE, 0, 256, 'e', wt)
    K.add(box((912, -144, 0), (1136, EDGE, 256), {'top': T('stairwood'), 'side': T('brick'), 'bot': CAULK}))
    K.stairs16(400, -144, 912, 16, 256, BZ, 'w', wt, base=0)
    K.add(box((176, -144, BZ - 16), (400, EDGE, BZ), {'top': T('floor_tile'), 'side': T('boards'), 'bot': T('boards')}))
    K.reserve(((176, -144, 0), (1136, EDGE, BZ)))
    K.route('stairs_low', (330, 144, 0), (1024, 120, 256))
    K.route('stairs_high', (1024, -64, 256), (288, -64, BZ))
    K.route('stairs_top', (288, 0, BZ), (288, 420, BZ))


def crawlspace():
    """joists, brick piers, the walk-through drain tunnel, the soil stack and the valve chamber"""
    jt = {'side': T('joist'), 'top': T('joist'), 'bot': T('joist')}
    for x in JOISTS:
        if x == 1856:
            K.add(box((x - 24, CRAWL_Y, JZ), (x + 24, CHAMBER[1] - 32, BZ - 32), jt),
                  box((x - 24, CHAMBER[1], JZ), (x + 24, Y1, BZ - 32), jt))
        else:
            K.add(box((x - 24, CRAWL_Y, JZ), (x + 24, Y1, BZ - 32), jt))
    for (x, y) in PIERS:
        pt = {'side': T('brick'), 'top': T('brick'), 'bot': CAULK}
        K.add(box((x - 64, y - 64, 0), (x + 64, y + 64, JZ), pt))
        K.add(box((x - 64, y - 64, JZ), (x - 24, y + 64, BZ - 32), pt), box((x + 24, y - 64, JZ), (x + 64, y + 64, BZ - 32), pt))
        K.reserve(((x - 64, y - 64, 0), (x + 64, y + 64, JZ)))
    tunnel()
    K.custom(ML.PLACE['soil_stack'], TOILET_C[0], TOILET_C[1], 0, occupy=False)
    K.add(cylb(TOILET_C[0], TOILET_C[1], 50, 350, BZ - 32))
    K.lbox(TOILET_C[0], TOILET_C[1], 0, 0, (-50, -440, 250), (50, -30, 350))
    K.crawl((TOILET_C[0] - 60, TUN['y'] + 40, 190), (TOILET_C[0] + 60, TUN['y'] + 140, 250))   # unreachable slot on the tunnel roof
    K.reserve(((TOILET_C[0] - 60, TOILET_C[1] - 450, 240), (TOILET_C[0] + 60, TOILET_C[1] + 60, BZ)))
    cx0, cy0, cx1, cy1 = CHAMBER
    bw = {'side': T('brick'), 'top': T('brick'), 'bot': T('brick')}
    K.add(box((cx0 - 32, cy0 - 32, 0), (cx0, GATE_Y[0], BZ - 32), bw), box((cx0 - 32, GATE_Y[1], 0), (cx0, cy1, BZ - 32), bw),
          box((cx0 - 32, GATE_Y[0], GATE_TOP), (cx0, GATE_Y[1], BZ - 32), bw), box((cx0, cy0 - 32, 0), (cx1, cy0, BZ - 32), bw))
    K.reserve(((cx0 - 32, cy0 - 32, 0), (cx1, cy1, BZ)))
    K.shoot_gate((cx0 - 44, 1446, 136), (cx0 - 32, 1494, 184), T('sluice'),
                 (cx0 - 28, GATE_Y[0], 0), (cx0 - 4, GATE_Y[1], GATE_TOP), T('sluice'), 'sluice',
                 push=0, model2=ML.PLACE['valve_wheel'][0], wait=12, sound='misc/toilet_flush')
    K.custom(ML.PLACE['gauge_panel'], cx0 - 32, 1620, 300, occupy=False)
    K.keep_clear(cx0 - 160, GATE_Y[0] - 32, cx0 + 160, GATE_Y[1] + 32, 0)


def tunnel():
    """octagonal drain pipe you walk through (solid_piece: the same brushes are the MD3 and its collision), a plank
    walkway inside, little ramps at both ends. The toilet flush drops you in here."""
    x0, x1, yc, ri, t, zc, wz = TUN['x0'], TUN['x1'], TUN['y'], TUN['ri'], TUN['t'], TUN['zc'], TUN['walk']
    ro = ri + t

    def vtx(ap, k):
        a = math.radians(-90 + 22.5 + 45 * k); rr = ap / math.cos(math.radians(22.5))
        return yc + rr * math.cos(a), zc + rr * math.sin(a)
    slabs = []
    for k in range(8):
        pts = [(x, p[0], p[1]) for x in (x0, x1) for p in (vtx(ri, k - 1), vtx(ri, k), vtx(ro, k - 1), vtx(ro, k))]
        slabs.append(hull(pts, WCLIP, round_pts=False))
    K.solid_piece('drain_tunnel', slabs, TX.texfn('pvc_t', 'pvc_t', tile=192))
    lo = ro * math.tan(math.radians(22.5)); zs = zc - ro * math.tan(math.radians(22.5))
    for s in (-1, 1):            # fill the wedge under each lower slant (a crouch-only slot otherwise)
        K.add(hull([(x, yc + s * lo, 0) for x in (x0, x1)] + [(x, yc + s * ro, 0) for x in (x0, x1)] +
                   [(x, yc + s * ro, zs) for x in (x0, x1)], WCLIP, round_pts=False))
    hb = ri * math.tan(math.radians(22.5)) - 1
    w = [(x, yc + s * hb, zc - ri) for x in (x0, x1) for s in (-1, 1)] + \
        [(x, yc + s * (hb + wz - (zc - ri)), wz) for x in (x0, x1) for s in (-1, 1)]
    K.add(hull(w, {'top': T('boards'), 'side': T('boards'), 'bot': CAULK}, round_pts=False))
    rt = {'top': T('boards'), 'side': T('boards'), 'bot': CAULK}
    K.ramp(x0 - 112, yc - 56, x0, yc + 56, 0, wz, 'e', rt, route='tunnel_w')
    K.ramp(x1, yc - 56, x1 + 112, yc + 56, 0, wz, 'w', rt, route='tunnel_e')
    K.reserve(((x0 - 112, yc - ro, 0), (x1 + 112, yc + ro, zc + ro)))
    K.keep_clear(x0 - 240, yc - 80, x0 - 112, yc + 80, 0); K.keep_clear(x1 + 112, yc - 80, x1 + 240, yc + 80, 0)
    K.route('tunnel_through', (x0 + 60, yc, wz), (x1 - 60, yc, wz))
    K.speaker((x0 + x1) / 2, yc, 120, 'ambient/water_drippling')


# ------------------------------------------------------------------------------------------------ bathroom
def put(name, x, y, z, angle=0, **kw):
    c = PM.COL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle=angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def bathroom():
    tx, ty = TUB_C
    put('bathtub', tx, ty, BZ)
    hx, hy, w, fl = PM.TUB['hx'], PM.TUB['hy'], PM.TUB['wall'], PM.TUB['floor']
    ix0, iy0, ix1, iy1 = tx - hx + w, ty - hy + w, tx + hx - w, ty + hy - w
    tf, rim = BZ + fl, BZ + PM.TUB['rim']
    wt = {'top': T('stairwood'), 'side': T('stairwood')}
    steps = K.stairs16(ix1 - 140 - 19 * 32, iy0, ix1 - 140, iy0 + 130, tf, rim, 'e', wt)
    K.add(box((ix1 - 140, iy0, rim - 24), (ix1, iy1, rim), {'top': T('stairwood'), 'side': T('stairwood'), 'bot': T('stairwood')}))
    K.water_box((ix0, iy0, tf), (ix1, iy1, BZ + 270), T('tub_water'), cutters=steps)
    K.speaker(ix0 + 60, ty, BZ + 360, 'ambient/water_drippling')
    K.route('tub_steps', (ix1 - 140 - 4 * 32 + 16, iy0 + 65, rim - 48), (ix1 - 70, (iy0 + iy1) / 2, rim))   # dry steps -> caddy
    px = tx - hx + 80
    K.secret((px - 30, ty - 30, tf), (px + 30, ty + 30, tf + 48), dest=(0, -250, VZ), angle=90, name='plughole')
    # toilet: walk off the seat into the bowl -> flushed into the drain tunnel
    ox, oy = TOILET_C
    put('toilet', ox, oy, BZ)
    hxo, hyo = PM.HOLE
    K.trigger_sound((ox - hxo + 4, oy - hyo + 4, BZ + PM.SEAT_Z - 20), (ox + hxo - 4, oy + hyo - 4, BZ + PM.SEAT_Z + 30),
                    'misc/toilet_flush', 'flush_snd', wait=3)
    K.teleporter((ox - hxo + 4, oy - hyo + 4, BZ + PM.BOWL_FLOOR), (ox + hxo - 4, oy + hyo - 4, BZ + PM.SEAT_Z - 24),
                 dest=(TUN['x1'] - 140, TUN['y'], TUN['walk']), angle=180, name='flush')
    vx, vy = VAN_C
    put('vanity', vx, vy, BZ)
    K.keep_clear(vx - 240, vy - 180 - 140, vx + 240, vy - 180, BZ)
    put('fan_frame', -800, Y1, 1650)
    K.rotating_model2(ML.PLACE['fan_blades'][0], (-800, Y1 - 24, 1650), 220, axis='y')
    K.speaker(-800, Y1 - 60, 1650, 'machine/ventilation')
    K.custom(ML.PLACE['bathmat'], tx + 300, 1180, BZ, occupy=False)
    for (nm, x, y, a) in (('hamper', -420, 1020, 15), ('pedal_bin', -330, 1690, 0), ('mop_bucket', -780, 1660, 30),
                          ('stool', 700, 1640, 0), ('hamper', 380, 640, -20), ('bath_scale', 860, 1240, 10),
                          ('crates', -1500, 520, 90), ('pedal_bin', 1800, 1100, 0), ('hamper', -650, 380, 40),
                          ('mop_bucket', 50, 340, 200), ('stool', 1250, 420, 15)):
        c = PM.COL.get(nm, {})
        K.prop(ML.PLACE[nm], x, y, BZ, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), angle=a)
    K.catalog('pad_toiletroll/pad_toiletroll.md3', 260, 1720, BZ, scale=0.7, angle=10)
    K.catalog('pad_ddmix/plants/fern.md3', 1800, 560, BZ, scale=0.45, lit=True)
    K.catalog('pad_items/towelstack.md3', -820, 1060, BZ, scale=1.2)
    vtop = BZ + PM.VAN['top']
    K.catalog('pad_bath/toothpaste_up.md3', vx - 170, vy - 165, vtop, scale=0.55, nudge=False, clip=False)
    K.catalog('pad_bath/deocan1.md3', vx + 190, vy + 130, vtop, scale=0.6, nudge=False, clip=False)
    K.catalog('pad_bath/deocan1.md3', tx - hx + 22, ty + 170, BZ + PM.TUB['rim'], scale=0.5, nudge=False, clip=False)


def pads():
    """every pad is a bathroom/plumbing object (themed_pad hides the disc); two run inside glass pipes"""
    tx, ty = TUB_C; ox, oy = TOILET_C; vx, vy = VAN_C
    rim = BZ + PM.TUB['rim']; cist = BZ + PM.CISTERN_Z; vtop = BZ + PM.VAN['top']; mtop = BZ + PM.VAN['mirror'][5]
    caddy_x = tx + PM.TUB['hx'] - PM.TUB['wall'] - 70
    K.themed_pad(caddy_x, 1150, BZ, land=(caddy_x, ty, rim), apex=rim + 170, name='pad_duck',
                 dress=ML.PLACE['pad_duck'], edges=[(caddy_x, ty - PM.TUB['hy'] + 20, rim)])
    K.themed_pad(ox, 1020, BZ, land=(ox, 1728, cist), apex=cist + 150, name='pad_cistern', dress=ML.PLACE['pad_looroll'],
                 edges=[(ox, oy - 175, BZ + PM.SEAT_Z), (ox, 1660, cist)])
    K.themed_pad(vx - 170, 1110, BZ, land=(vx - 170, 1640, vtop), apex=vtop + 150, name='pad_counter',
                 dress=ML.PLACE['pad_soap'], edges=[(vx - 170, vy - 196, vtop)])
    K.themed_pad(vx + 175, vy - 135, vtop, land=(vx, 1726, mtop), apex=mtop + 140, name='pad_mirror',
                 dress=ML.PLACE['pad_sponge'], ceiling=ZC, edges=[(vx, vy + 40, mtop)])
    hx_, hy_ = HEATER
    K.themed_pad(1950, hy_, 0, land=(hx_ - 60, hy_, 960), apex=960 + 340, name='pad_heater',
                 dress=ML.PLACE['pad_valve'], edges=[(hx_ + 220, hy_, 960)], glow=90)
    lx = (LIFT_HOLE[0] + LIFT_HOLE[2]) / 2
    K.tube_lift(lx, LIFT_HOLE[3] - 56, 0, land=(lx, LIFT_HOLE[1] - 120, BZ), apex=BZ + 190, name='lift_drain',
                glass_sh=PM.M['glass'], ring_sh=PM.M['chrome'], arc=True, r=56, mouth=PM.M['chrome'], glow=False,
                top_tex=T('nodraw_ns'), side_tex=T('nodraw_ns'), edges=[(lx, LIFT_HOLE[1], BZ)])
    K.tube_lift(-400, -1450, 0, land=(-160, 520, BZ), apex=1000, name='express', glass_sh=PM.M['glass'],
                ring_sh=PM.M['copper'], arc=True, r=64, mouth=PM.M['copper'], glow=False,
                top_tex=T('nodraw_ns'), side_tex=T('nodraw_ns'), edges=[(-180, EDGE, BZ)], ceiling=ZC)
    K.light(-400, -1450, 60, 160, '0.6 0.9 1'); K.light(lx, LIFT_HOLE[3] - 56, 60, 140, '0.6 0.9 1')


# ------------------------------------------------------------------------------------------------ sewer hall
def sewer():
    hx_, hy_ = HEATER
    put('water_heater', hx_, hy_, 0)
    K.speaker(hx_, hy_, 200, 'machine/transformer')
    px, py = PUMP
    put('pump', px, py, 0)
    K.rotating_model2(ML.PLACE['flywheel'][0], (px - 190, py, 150), 160, axis='x')
    K.speaker(px, py, 150, 'machine/mechanics')
    for (nm, x, y) in (('stack_a', -1650, -520), ('stack_b', 250, -1650), ('stack_c', -350, 60)):
        place, o = PM.pipe_run(nm, [(x, y, 0), (x, y, ZC)], 56, 'pvc')
        K.custom(place, x, y, 0, occupy=False)
        K.add(cylb(x, y, 56, 0, ZC)); K.reserve(((x - 60, y - 60, 0), (x + 60, y + 60, ZC)))
    for (x, y, a) in ((-200, -1600, 20), (600, -1250, 80), (450, -600, 30), (-650, -1220, 70), (-150, -420, 5), (-520, -620, 50), (-640, -330, 15), (-1350, -150, 10), (1700, -350, 60), (1650, 0, 0),
                      (-900, -1350, 45)):
        K.prop(ML.PLACE['crates'], x, y, 0, boxes=PM.COL['crates']['boxes'], angle=a)
    for (p, x, y, s) in (('pad_ddmix/trashcan/garbage_bag_group.md3', -1850, -1650, 1.3),
                         ('pad_ddmix/trashcan/garbage_bag_standing.md3', 900, -1700, 1.3),
                         ('pad_ddmix/backyard/tire.md3', 50, -1250, 0.8), ('pad_tins/pad_paint1.md3', 1100, -1200, 1.0),
                         ('pad_tins/pad_paint2_tl.md3', -1600, -1250, 1.0), ('pad_ddmix/trashcan/cannedfish_rusty.md3', -700, -1200, 1.0),
                         ('pad_ducktape/ducktape.md3', 300, -300, 1.4), ('pad_ddmix/gallery/fire_extinguisher.md3', -1950, 150, 1.8),
                         ('pad_ddmix/backyard/screw_nut.md3', -400, -600, 2.0)):
        K.catalog(p, x, y, 0, scale=s)


def crawl_props():
    for (p, x, y, s) in (('pad_tins/pad_paint1_tl.md3', -1700, 1700, 1.0), ('pad_ducktape/ducktape.md3', 900, 1100, 1.4),
                         ('spider/spider30.md3', -1200, 400, 1.5), ('pad_ddmix/trashcan/cannedfish.md3', 500, 1300, 1.0),
                         ('pad_tins/pad_paint2.md3', -500, 400, 1.0), ('pad_ddmix/backyard/screwnut_thin.md3', 1400, 1100, 2.0)):
        K.catalog(p, x, y, 0, scale=s)
    for (x, y, a) in ((-1250, 400, 30), (1000, 1600, 0), (-1750, 1250, 70), (30, 640, 10)):
        K.prop(ML.PLACE['crates'], x, y, 0, boxes=PM.COL['crates']['boxes'], angle=a)
    for (x, y) in ((-700, 1400), (900, 1250), (-1600, 900)):
        K.pendulum_model2(ML.PLACE['bulb'][0], (x, y, BZ - 48), 6, 160)
        K.light(x, y, BZ - 48 - 210, 420, '1 0.85 0.6')
    K.speaker(0, 900, 200, 'ambient/floor_creaking')


# ------------------------------------------------------------------------------------------------ secret + loot
def vault():
    """the Lost & Found under the plughole: sealed room below the world, teleporter back to the bathroom"""
    x0, y0, x1, y1 = VAULT; z = VZ; h = 320
    w, f = T('wall_tile'), T('floor_tile')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), tex6(top=f), detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), tex6(bot=T('plaster')), detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    K.item('item_padpower', -160, 120, z); K.item('item_revival', 0, 180, z); K.item('holdable_killerducks', 160, 120, z)
    K.item('item_armor_padshield', 0, 20, z)
    K.custom(ML.PLACE['pad_duck'], -300, 300, z, angle=225, occupy=False)
    K.teleporter((-48, y1 - 64, z), (48, y1, z + 96), dest=(-1150, 800, BZ), angle=0, name='vault_exit')
    K.light(0, 0, z + 260, 600, '0.8 0.95 1')
    K.speaker(0, 0, z + 200, 'ambient/water_bubbling')


def items():
    W, A = K.weapon, K.ammo
    vx, vy = VAN_C; tx, ty = TUB_C
    mtop = BZ + PM.VAN['mirror'][5]; basin = BZ + PM.VAN['basin_floor']; tf = BZ + PM.TUB['floor']
    W('imperius', vx, 1726, mtop, marker='purple')                     # top of the mirror cabinet (two pads)
    W('betty', vx, vy, basin, marker='black')                           # bottom of the sink
    W('splasher', tx - 330, ty + 80, tf, marker='blue')                 # bottom of the bath (underwater)
    W('balloony', HEATER[0] - 60, HEATER[1] + 90, 960, marker='orange')      # top of the water heater
    W('pumper', -600, TUN['y'], TUN['walk'], marker='green')            # inside the drain tunnel
    W('boaster', -800, -200, 0, marker='orange')
    W('bubbleg', 300, 900, 0, marker='green')
    ammo = {'imperius': [(vx, vy - 60, BZ + 18), (1840, 1600, 0), (-1900, -1700, 0)],
            'betty': [(110, 1730, BZ + PM.CISTERN_Z), (-1700, 900, 0), (1900, -400, 0), (-1000, 1700, BZ)],
            'splasher': [(300, -1000, ZB), (-1200, 520, BZ), (1500, 400, 0), (-1950, -900, -96)],
            'balloony': [(1700, 400, BZ), (-600, -1700, 0), (-1300, 1650, 0)],
            'pumper': [(TUN['x1'] - 60, TUN['y'], TUN['walk']), (600, -1500, 0), (-600, 1500, BZ), (1300, 1000, 0)],
            'boaster': [(1500, -200, 0), (-1700, 1100, 0), (500, 400, BZ)],
            'bubbleg': [(900, 1400, 0), (-1600, -1450, 0), (-300, 700, BZ), (1950, 900, BZ)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: A(w, x, y, z)
    for (x, y, z) in ((-1950, 600, 0), (1950, -1650, 0), (0, 300, BZ)): A('nipper', x, y, z)
    K.item('item_armor_shard', -100, 1730, BZ + PM.CISTERN_Z)
    K.item('item_jumper', tx + PM.TUB['hx'] - PM.TUB['wall'] - 70, ty + 140, BZ + PM.TUB['rim'])
    K.item('item_speedy', 1900, 1500, 0); K.item('holdable_floater', -100, -560, 0)
    K.item('item_armor_shard', 1840, 1700, 0); K.item('item_visionless', -1000, 1200, 0)
    K.station(-1880, 420, 0, ang=0); K.station(0, -1700, 0, ang=90); K.station(1900, 300, BZ, ang=180)
    for (x, y, z, a) in ((-1300, 900, BZ, 0), (-200, 1100, BZ, 90), (700, 1000, BZ, 180), (1500, 800, BZ, 135),
                         (-600, 450, BZ, 270), (-1500, 700, 0, 0), (-400, 1000, 0, 0), (700, 800, 0, 90), (1400, 1300, 0, 180),
                         (-1300, -400, 0, 0), (600, -400, 0, 180), (-850, -1500, 0, 45), (900, -1450, 0, 135),
                         (1800, -1300, 0, 90), (-1800, -1450, 0, 0)):
        K.spawn(x, y, z, a)


def lights():
    K.light_grid(X0, EDGE, X1, Y1, BZ + 700, 512, 1800, '1 0.97 0.92')              # bathroom
    K.light_grid(X0, Y0, X1, EDGE, 760, 640, 1700, '0.85 1 0.85')                    # sewer hall (greenish)
    K.light_grid(X0, CRAWL_Y, X1, Y1, 360, 512, 650, '1 0.85 0.65')                  # crawlspace
    K.light(1840, 1610, 300, 420, '1 0.4 0.3')                                       # valve chamber
    K.light(TUN['x0'] + 200, TUN['y'], 150, 260, '0.7 0.9 1'); K.light(-400, TUN['y'], 150, 260, '0.7 0.9 1')
    for x in (-1500, -500, 500, 1500): K.light(x, (CAN[0] + CAN[1]) / 2, 40, 300, '0.5 0.9 0.4')
    K.light(VAN_C[0], VAN_C[1] - 60, 760, 260); K.light(VAN_C[0], VAN_C[1] - 200, BZ + 1400, 300)
    K.light(TUB_C[0], TUB_C[1], BZ + 600, 360, '0.9 0.95 1')
    K.light(HEATER[0], HEATER[1], 1300, 450, '1 0.95 0.8')                           # heater top (above the grid)
    K.light(VAN_C[0], 1650, BZ + PM.VAN['mirror'][5] + 260, 380)                     # mirror cabinet top
    K.light(TOILET_C[0], 1700, BZ + PM.CISTERN_Z + 260, 300)                         # cistern top
    K.timer_sound(0, -900, 400, 'misc/toilet_flush', 'distant_flush', 40, 20)


if __name__ == '__main__':
    textures()
    PM.build_all(TX, CAN[1] - CAN[0], BR_W)          # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); floors(); canal(); cross_walls(); main_pipe(); basement_stairs(); crawlspace(); bathroom(); pads(); vault()
    sewer(); crawl_props(); items(); lights()
    K.fix_items()
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(200, 50), sun_int=90, skylight=(40, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
