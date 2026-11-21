#!/usr/bin/env python3
"""Padland Funfair (wop_padfunfair) - FFA at a travelling funfair on a summer night, built on woplib.

    OUT=<dir> python3 build_padfunfair.py          (wopbuild.py padfunfair preview / all)

48u per metre (you are a kid-sized figure). x east, y north, ground z 0. Playable x -2560..2560, y -2304..2304 inside a
fence; the sky hull is 512u bigger with trees and showmen's lorries in the field beyond.
Rides you can use: the big wheel (8 level gondolas, func_train), the carousel (rotating deck), the ghost train (carts
on a circle through the haunted house), the helter-skelter (walk up the spiral slide or take the lift).
Levels: duck pool -48 | ground 0 | dodgem roof 336 | stalls 208 | carousel crown 640 | big-top crown 620 |
trapeze 360 | ghost house roof ~520 | helter-skelter top 896 | wheel hub deck 916.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, hull, cyl, carve, sub_rects, sign_box, prism, ngon
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL, town, railway as RW, rides, shopbits as SB
from meshlib import Mesh, rbox, tube, revolve, disc, ellipsoid, sphere
import ff_models as FM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                 # -2560 -2304 2560 2304
HX0, HY0, HX1, HY1 = X0 - 512, Y0 - 512, X1 + 512, Y1 + 512
ZS = 2600
WHEEL = (0.0, 1300.0, 900.0); WR = 700.0
CAR = (-1750.0, -150.0); CAR_RIN, CAR_ROUT = 110.0, 420.0
GT_C = (1700.0, -150.0); GT_R = 400.0
HS = (1800.0, 1450.0); HS_R = 170.0; HS_H = 880.0
BT = (-1650.0, 1450.0); BT_R = 650.0; BT_WALL = 300.0; BT_PEAK = 620.0
POOL = (-1050.0, -1000.0); POOL_R = 230.0
VAULT = (0, 1900, -1400)                        # sealed, far under the ground (inside the playable bounds)

K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '22', '_color': '0.75 0.8 1', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
FM.setup(TX)


def tex6(**f):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t.update(f); return t


def place(name, x, y, z, angle=0, occupy=True, **kw):
    c = FM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), occupy=occupy, **kw)


def deco(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


def skin(name, angle='auto'):
    c = FM.COLL.get(name, {})
    h = {'striker': 8}.get(name, 16)                    # deck height (the trigger sits on it)
    return dict(place=ML.PLACE[name], h=h, angle=angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()))


# ================================================================================================ textures
def grass_tex(n=256, seed=1):
    a = TL.solid((60, 96, 46), 6, seed, n)
    fl = ML.noise(n, 1, seed + 1)
    return a + np.where((fl > 1.5)[..., None], ML.C((40, 34, 10)), 0)


def textures():
    TX.add('grass', grass_tex(), steps='softsteps')
    TX.add('tarmac', TL.grime(TL.solid((64, 64, 68), 8, 11, 256), 0.2, 12))
    TX.add('sawdust', TL.stone((186, 150, 100), cells=80, edge=(150, 116, 74), edge_w=0.03, vary=20, seed=13), steps='sandsteps')
    TX.add('plates', TL.checker((120, 124, 130), (100, 104, 110), 4, (70, 72, 76), 0.03, 14))
    TX.add('boards', TL.planks((150, 108, 66), 6, (90, 62, 36), 10, True, False, 15), steps='woodsteps')
    TX.add('roof', TL.grime(TL.solid((80, 80, 86), 6, 16, 128), 0.2, 17))
    TX.add('redpaint', TL.solid((190, 40, 40), 4, 18, 128))
    TX.add('wood', TL.planks((140, 98, 60), 4, (86, 58, 34), 8, False, True, 19), steps='woodsteps')
    TX.add('kerb', TL.solid((150, 146, 140), 4, 20, 128))
    TX.add('stairtread', TL.planks((150, 112, 72), 2, (90, 64, 40), 8, False, False, 21), steps='woodsteps')
    TX.add('stairside', TL.solid((120, 90, 60), 4, 22, 128))
    TX.add('pooltile', TL.tiles((90, 170, 210), (240, 244, 246), cols=6, rows=6, offset=0, grout_w=0.05, seed=23))
    TX.add('water', TL.solid((60, 140, 180), 10, 24, 128), 'water', rgb=(0.25, 0.5, 0.65), alpha=0.55)
    TX.add('slidefloor', TL.solid((220, 60, 40), 3, 25, 128))
    TX.add('canvaswall', FM.stripes_v((210, 40, 40), (250, 236, 200), 12))
    TX.add('vault', TL.grime(TL.planks((120, 30, 40), 6, (70, 16, 24), 8, False, True, 26), 0.2, 27))
    for key, text, bg, fg in (('sign_entrance', 'PADLAND FUNFAIR', (30, 20, 60), (255, 220, 80)),
                              ('sign_coconut', 'COCONUT SHY', (120, 60, 20), (255, 240, 200)),
                              ('sign_candy', 'CANDY FLOSS', (230, 120, 180), (255, 255, 255)),
                              ('sign_ghost', 'GHOST TRAIN', (20, 10, 30), (120, 255, 120)),
                              ('sign_dodgems', 'DODGEMS', (200, 40, 40), (255, 230, 90)),
                              ('sign_tickets', 'TICKETS', (40, 80, 180), (255, 255, 255)),
                              ('sign_ducks', 'HOOK-A-DUCK', (40, 120, 200), (255, 230, 90))):
        TX.add(key, FM.sign_tex(text, bg, fg), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(250, 200, 60), rubber=(50, 54, 60))


def building_mats():
    M = TX.material
    M('b_red', FM.stripes_v((200, 40, 40), (240, 236, 226), 10), shade=20)
    M('b_blue', FM.stripes_v((40, 80, 180), (240, 236, 226), 10), shade=20)
    M('b_green', FM.stripes_v((40, 140, 80), (240, 236, 226), 10), shade=20)
    M('b_plain', TL.solid((236, 230, 214), 4, 50, 128), shade=20)
    M('b_trim', TL.solid((240, 200, 50), 3, 51, 64), shade=20)
    M('b_floor', TL.planks((150, 108, 66), 6, (90, 62, 36), 10, True, False, 52), shade=20, steps='woodsteps')
    M('b_roof', TL.grime(TL.solid((80, 80, 86), 6, 53, 128), 0.2, 54), shade=20)
    M('haunt_wall', TL.grime(TL.planks((70, 60, 70), 8, (40, 34, 40), 8, False, True, 55), 0.4, 56), shade=20)
    M('haunt_in', TL.grime(TL.stripes((60, 40, 60), (46, 30, 46), 8, True, 0.3, 57), 0.3, 58), shade=20)
    M('haunt_roof', TL.tiles((50, 46, 56), (30, 28, 34), cols=6, rows=10, offset=0.5, vary=12, seed=59), shade=20)
    M('booth', FM.stripes_v((40, 80, 180), (250, 220, 90), 8), shade=20)
    M('canvas_r', TL.stripes((200, 40, 40), (240, 236, 226), 8, True, 0.0, 60), shade=60, two=True)
    M('canvas_b', TL.stripes((40, 80, 170), (240, 236, 226), 8, True, 0.0, 61), shade=60, two=True)
    M('metal', TL.metal((120, 122, 126), True, 62), shade=40)
    M('caravan_w', FM.caravan_tex(), shade=20)
    M('van_w', FM.van_tex(), shade=20)
    M('duck', TL.solid((250, 210, 40), 3, 63, 64), 'dyn')
    M('beak', TL.solid((240, 120, 30), 3, 64, 64), 'dyn')


def M_(**m): return {k: TX[v] for k, v in m.items()}


# ================================================================================================ ground + hull
def shell():
    holes = [(POOL[0] - POOL_R - 16, POOL[1] - POOL_R - 16, POOL[0] + POOL_R + 16, POOL[1] + POOL_R + 16)]
    paths = [((-320, Y0 + 60, 320, -560), 'tarmac'), ((-320, 260, 320, 900), 'sawdust'), ((-1300, 300, -320, 560), 'sawdust'),
             ((320, 600, 1500, 860), 'sawdust'), ((BT[0] - 320, BT[1] - 320, BT[0] + 320, BT[1] + 320), 'sawdust')]
    for r in sub_rects((HX0, HY0, HX1, HY1), holes + [p for p, _ in paths]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK}, detail=False))
    for (r, tex) in paths:
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), {'top': T(tex), 'side': CAULK, 'bot': CAULK}, detail=False))
    S = T('sky')
    K.add(box((HX0 - 32, HY0 - 32, -32), (HX0, HY1 + 32, ZS), tex6(e=S), detail=False))
    K.add(box((HX1, HY0 - 32, -32), (HX1 + 32, HY1 + 32, ZS), tex6(w=S), detail=False))
    K.add(box((HX0, HY0 - 32, -32), (HX1, HY0, ZS), tex6(n=S), detail=False))
    K.add(box((HX0, HY1, -32), (HX1, HY1 + 32, ZS), tex6(s=S), detail=False))
    K.add(box((HX0 - 32, HY0 - 32, ZS), (HX1 + 32, HY1 + 32, ZS + 32), tex6(bot=S), detail=False))
    # the fence line: player clip to the sky, fence panels just inside
    for (mn, mx) in (((X0 - 16, Y0 - 16, 0), (X1 + 16, Y0, ZS)), ((X0 - 16, Y1, 0), (X1 + 16, Y1 + 16, ZS)),
                     ((X0 - 16, Y0, 0), (X0, Y1, ZS)), ((X1, Y0, 0), (X1 + 16, Y1, ZS))):
        K.add(box(mn, mx, CLIP))
    for x in np.arange(X0 + 256, X1, 512):
        deco('fence_panel', x, Y0 + 2, 0, 0); deco('fence_panel', x, Y1 - 2, 0, 180)
    for y in np.arange(Y0 + 256, Y1, 512):
        deco('fence_panel', X0 + 2, y, 0, 270); deco('fence_panel', X1 - 2, y, 0, 90)
    K.occupy(X0, Y0, X1, Y0 + 40, 0, 200); K.occupy(X0, Y1 - 40, X1, Y1, 0, 200)
    K.occupy(X0, Y0, X0 + 40, Y1, 0, 200); K.occupy(X1 - 40, Y0, X1, Y1, 0, 200)
    # the field beyond: trees and showmen's lorries
    rng = np.random.default_rng(3)
    for k in range(26):
        side = k % 4; t = rng.uniform(-0.9, 0.9)
        x, y = [(t * X1, Y1 + 280), (t * X1, Y0 - 280), (X0 - 280, t * Y1), (X1 + 280, t * Y1)][side]
        K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, scale=rng.uniform(0.8, 1.1), clip=False, nudge=False, lit=False)


# ================================================================================================ the rides
def big_wheel():
    hx, hy, hz = WHEEL
    place('wheel_frame', hx, hy, 0)
    for sy in (-1, 1):                                           # leg collision (weapclip tubes as 4-sided hulls)
        for sx in (-1, 1):
            a = np.array([sx * 520, sy * 290, 0.0]); b = np.array([0, sy * 165, hz])
            for t0, t1 in ((0.0, 0.5), (0.5, 0.97)):
                p0, p1 = a + (b - a) * t0, a + (b - a) * t1
                pts = [(p[0] + dx, hy + p[1] + dy, p[2]) for p in (p0, p1) for dx in (-16, 16) for dy in (-16, 16)]
                K.add(hull(pts, WCLIP, round_pts=False))
    K.occupy(hx - 560, hy - 330, hx + 560, hy + 330, 0, 60)
    K.rotating_model2(ML.IQM['wheel_rims'], (hx, hy, hz), 4.9, axis='y')
    rides.wheel_gondolas(K, 'wheel', WHEEL, WR, 8, ML.PLACE['gondola'], speed=60, plane='x', half=(80, 90), drop=150,
                         open_side='-y')
    # boarding platform beside the bottom gondola + steps
    pl = box((hx - 220, hy - 300, 0), (hx + 220, hy - 104, 48), {'top': T('boards'), 'side': T('redpaint'), 'bot': CAULK})
    K.add(pl); K.reserve(pl)
    K.reserve(K.stairs16(hx - 120, hy - 396, hx + 120, hy - 300, 0, 48, 'n', {'top': T('stairtread'), 'side': T('redpaint')}))
    K.route('wheel_platform', (hx, hy - 440, 2), (hx, hy - 200, 48))
    K.keep_clear(hx - 120, hy - 460, hx + 120, hy - 396, 0)
    K.jumppad(hx + 420, hy - 640, 0, land=(hx, hy, hz + 16), apex=hz + 140, name='pad_wheel',
              skin=skin('bouncy_castle', angle=0), glow=False, edges=[(hx, hy - 110, hz + 16)])
    K.reserve(((hx + 260, hy - 800, 0), (hx + 580, hy - 480, 220)))
    K.speaker(hx, hy, 300, 'machine/mechanics')


def carousel():
    cx, cy = CAR
    base = cyl(cx, cy, CAR_ROUT + 10, 0, 16, {'top': T('boards'), 'side': T('redpaint'), 'bot': CAULK}, 32)
    K.add(base)
    place('carousel_top', cx, cy, 0)
    rides.carousel_deck(K, 'carousel', (cx, cy), CAR_RIN, CAR_ROUT, 16, ML.PLACE['carousel_deck'], speed=16)
    # the canopy roof you can stand on: 16 wedge slabs (30 deg) round the crown
    rin, rout, zin, zout = 90.0, 480.0, 640.0, 420.0
    for k in range(16):
        a0 = 2 * math.pi * k / 16; a1 = 2 * math.pi * (k + 1) / 16
        pts = []
        for a in (a0, a1):
            for (r, z) in ((rin, zin), (rout, zout)):
                pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z), (cx + r * math.cos(a), cy + r * math.sin(a), z - 12)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.jumppad(cx + 640, cy - 120, 0, land=(cx + 60, cy, 640), apex=800, name='pad_carousel', skin=skin('trampoline'), glow=False,
              edges=[(cx + 480, cy, 420)])
    K.route('carousel_base', (cx + 560, cy, 2), (cx + 300, cy, 16))
    K.speaker(cx, cy, 200, 'misc/wind_chimes')


def ghost_train():
    """haunted house (2 storeys + gable roof) with the ghost train looping out of its front through two arches"""
    gx, gy = GT_C
    hs = town.Building(K, 'haunted', (1150, -150, 2250, 500), 0, (240, 176),
                       M_(ext='haunt_wall', int='haunt_in', trim='b_trim', floor='b_floor', roof='haunt_roof', ceil='haunt_in',
                          gable='haunt_wall'),
                       doors=[('s', 1210, 1390), ('s', 2010, 2190), ('w', 300, 412), ('e', 300, 412)],
                       stairs=[(1250, 388, 1730, 484, 'e')], roof='gable_x', door_h=210, floor_mat=False,
                       windows={'n': [(1400, 1480, 1), (1700, 1780, 1), (2000, 2080, 1)], 's': [(1600, 1680, 1), (1800, 1880, 1)]})
    hs.build()
    K.add(sign_box((1560, -156, 250), (1840, -150, 320), T('sign_ghost'), 1024, 256, facing='s', edge=T('wood')))
    deco('skull_sign', 1700, -150, 325, 0)                                   # big skull over the ride sign
    for x in (1640, 1840):                                                   # crooked shutters on the upper windows
        deco('shutters', x, -150, 240 + 56, 0)
    for x in (1440, 1740, 2040):
        deco('shutters', x, 500, 240 + 56, 180)
    cars = []
    for k in range(3):
        X = ML.Model()
        rbox(X.mesh(TX['cart_body']), (-70, -48, 14), (70, 48, 70), r=10, k=2, tile=140)
        rbox(X.mesh(TX['cart_dark']), (-60, -40, 30), (40, 40, 78), r=8, k=2, tile=64)
        for x in (-46, 46):
            for y in (-40, 40):
                tube(X.mesh(TX['steel_dyn']), [(x, y, 14), (x, y * 1.05, 14)], 12, nseg=8)
        if k == 0:
            sphere(X.mesh(TX['rim_white']), (66, 0, 90), 26, nu=10, nv=8)
            for e in (-10, 10): sphere(X.mesh(TX['bulb_red']), (86, e, 96), 6, nu=6, nv=4)
        cars.append(RW.Car(f'cart{k}', X, -72, 72, 80, 50, gap=24))
    TR = RW.CircleTrain(K, 'ghosttrain', GT_C, GT_R, 18, cars, front_deg=270.0, speed=14.0, origin_dz=200)
    TR.build()
    RW.track_ring(K, 'gt_track', GT_C, GT_R, 0, TX['steel'], TX['wood_dark'], gauge=60.0, n=24, tie_len=110, tie_w=14, tie_h=6, rail_h=8)
    # spooky things inside (clear of the ride band R 340..480)
    for (x, y, nm, a) in ((1260, 150, 'skeleton', 90), (2140, 150, 'skeleton', 270), (1700, 330, 'ghost', 180), (1700, -30, 'ghost', 0)):
        deco(nm, x, y, 0, a, lit=nm != 'ghost')
    K.light(1700, 150, 180, 260, '0.6 1 0.6'); K.light(1300, 300, 150, 220, '1 0.3 0.2'); K.light(2100, 300, 150, 220, '0.4 0.4 1')
    K.light(1700, 160, 380, 380, '0.7 0.6 1')
    K.speaker(1700, 150, 120, 'animal/bird_owl1')
    K.jumppad(1000, 600, 0, land=(1400, hs.ridge[1], hs.roof_top), apex=hs.roof_top + 170, name='pad_haunted',
              dress=ML.PLACE['coffin_pad'], dress_light=120, dress_rgb='0.5 1 0.5', edges=[(1150, 400, 416)])
    # secret: the upright coffin in the north-east corner upstairs -> the showmen's strongroom
    deco('coffin_pad', 2150, 430, 240, 180)
    K.secret((2110, 370, 240), (2190, 450, 324), dest=(VAULT[0], VAULT[1], VAULT[2]), angle=90, name='strongroom', approach='w')
    return hs, TR


def helter_skelter():
    cx, cy = HS
    deco('helter_tower', cx, cy, 0)
    # tower collision: 16 wall segments with the door gap at -90 deg; flat top you stand on
    n = 16
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        am = math.degrees((a0 + a1) / 2)
        if -112 <= ((am + 180) % 360) - 180 <= -68: z0 = 150
        else: z0 = 0
        pts = []
        for a in (a0, a1):
            for r in (HS_R - 16, HS_R):
                pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z0), (cx + r * math.cos(a), cy + r * math.sin(a), HS_H - 16)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.add(cyl(cx, cy, HS_R, HS_H - 16, HS_H, {'top': T('boards'), 'side': T('redpaint'), 'bot': T('redpaint')}, 16))
    K.occupy_r(cx, cy, HS_R + 8, 0, HS_H)
    # lift inside: springboard pad up through a hatch? the top is closed: the lift lands you on top from the door side
    K.jumppad(cx, cy + 520, 0, land=(cx, cy, HS_H), apex=HS_H + 300, name='pad_helter', skin=skin('springboard'), glow=False,
              edges=[(cx, cy + HS_R, HS_H)])                             # north side: the top coil of the slide is south
    # the spiral slide: 2.25 turns from the top edge down to the ground, walkable both ways (13 deg)
    pts = rides.helix((cx, cy), HS_R + 70, HS_H - 40, 24, 2.25, a0=-90, n_per_turn=20, ccw=False)
    pts[0] = (pts[0][0], pts[0][1], HS_H)
    # landing from the tower top to the slide's open top end (CCW side of the start, flush with the deck)
    lp = []
    for a in (-86.0, -62.0):
        for r in (HS_R + 8, HS_R + 120):
            ar = math.radians(a); lp += [(cx + r * math.cos(ar), cy + r * math.sin(ar), HS_H - 16), (cx + r * math.cos(ar), cy + r * math.sin(ar), HS_H)]
    K.add(hull(lp, {'top': T('boards'), 'side': T('redpaint'), 'bot': T('redpaint')}, round_pts=False))
    K.slide(pts, 50, 44, T('slidefloor'), wall_tex=T('redpaint'))
    low = [p for p in pts if p[2] < 140]
    if len(low) > 1: K.slide_skirt(low, 50, 0)                       # no crawl gap under the low end
    X = ML.Model(); ML.flume(X, pts, 50, 44, TX['slide_red']); c = np.mean(np.array(pts), 0)
    X.shift((c[0], c[1], 0)); ML.save('helter_slide', X); deco('helter_slide', c[0], c[1], 0)
    d = np.array(pts[-1][:2]) - np.array(pts[-2][:2]); d /= np.linalg.norm(d)
    K.route('helter_slide', (pts[-1][0] + d[0] * 140, pts[-1][1] + d[1] * 140, 0), (cx, cy, HS_H))


def big_top():
    cx, cy = BT
    deco('bigtop', cx, cy, 0)
    n = 48; door = (-105, -75)
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        am = math.degrees((a0 + a1) / 2)
        z0 = 240 if door[0] <= ((am + 180) % 360) - 180 <= door[1] else 0
        pts = []
        for a in (a0, a1):
            for r in (BT_R - 10, BT_R):
                pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z0), (cx + r * math.cos(a), cy + r * math.sin(a), BT_WALL - 10)]
        wb = hull(pts, WCLIP, round_pts=False); K.add(wb); K.reserve(wb)
    for k in range(24):                                          # roof: 24 wedge slabs (30 deg slope) up to the crown
        a0 = 2 * math.pi * k / 24; a1 = 2 * math.pi * (k + 1) / 24
        pts = []
        for a in (a0, a1):
            for (r, z) in ((70, BT_PEAK), (BT_R + 30, BT_WALL - 10)):
                pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z), (cx + r * math.cos(a), cy + r * math.sin(a), z - 14)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.add(cyl(cx, cy, 70, BT_PEAK - 14, BT_PEAK, WCLIP, 12))
    K.add(cyl(cx, cy, 14, 0, BT_PEAK - 14, WCLIP, 8))
    # inside: sawdust ring with a kerb, bleachers on the north side, two trapeze rigs, the cannon
    bt = {'top': T('boards'), 'side': T('wood')}
    K.stairs16(cx - 210, cy + 330, cx + 210, cy + 330 + 5 * 32, 0, 80, 'n', bt)
    K.route('bleachers', (cx, cy + 290, 2), (cx, cy + 520, 80))
    for (dx, dy) in ((-330, -40), (330, -40)):
        place('trapeze', cx + dx, cy + dy, 0)
    K.jumppad(cx - 120, cy - 180, 0, land=(cx - 330, cy - 40, 300), apex=410, name='pad_trapeze', dress=ML.PLACE['cannon'],
              dress_light=140, ceiling=465, edges=[(cx - 270, cy - 40, 300)])
    K.jumppad(cx + 120, cy - 180, 0, land=(cx + 330, cy - 40, 300), apex=410, name='pad_trapeze2', dress=ML.PLACE['cannon'],
              dress_light=140, ceiling=465, edges=[(cx + 270, cy - 40, 300)])
    # outside: a cannon that fires you onto the tent roof crown
    K.jumppad(cx + 760, cy - 300, 0, land=(cx, cy, BT_PEAK), apex=960, name='pad_bigtop',
              dress=ML.PLACE['cannon'], dress_light=140, edges=[(cx + BT_R, cy - 60, BT_WALL)])
    K.route('bigtop_door', (cx, cy - BT_R - 120, 2), (cx, cy - BT_R + 140, 2))
    for (x, y) in ((cx - 260, cy + 120), (cx + 260, cy + 120), (cx, cy - 300)):
        K.light(x, y, 420, 420, '1 0.85 0.6')


def dodgems():
    w, d, h = 1000, 700, 320
    floor = box((-w / 2, -d / 2 - 100, 0), (w / 2, d / 2 - 100, 8), {'top': T('plates'), 'side': T('kerb'), 'bot': CAULK})
    K.add(floor)
    deco('pavilion', 0, -100, 8)
    for x in np.linspace(-w / 2 + 20, w / 2 - 20, 5):
        for y in (-d / 2 + 20 - 100, d / 2 - 20 - 100):
            K.add(box((x - 16, y - 16, 8), (x + 16, y + 16, h - 8), WCLIP))
    roof = box((-w / 2 - 20, -d / 2 - 120, h - 8), (w / 2 + 20, d / 2 - 80, h + 8), {'top': T('roof'), 'side': T('redpaint'), 'bot': T('roof')})
    K.add(roof); K.reserve(roof)
    K.add(sign_box((-260, -d / 2 - 126, h - 70), (260, -d / 2 - 120, h - 8), T('sign_dodgems'), 1024, 256, facing='s', edge=T('redpaint')))
    for (x, y, a, key) in ((-300, -200, 30, 'dodgem_red'), (-60, 40, 160, 'dodgem_blue'), (120, -300, 260, 'dodgem_yellow'),
                           (360, 60, 100, 'dodgem_red'), (-380, 100, 300, 'dodgem_blue')):
        place(f'dodgem_{key}', x, y - 100, 8, a)
    K.jumppad(-700, -650, 0, land=(-300, -150, h + 8), apex=h + 200, name='pad_dodgems', skin=skin('trampoline'), glow=False,
              edges=[(-500, -360, h + 8)])
    K.route('dodgems', (0, -560, 0), (0, -350, 8))


def duck_pool():
    """hook-a-duck: a round tiled pool sunk into the grass (40u deep, steps out east), ducks bobbing round"""
    px, py = POOL
    hx0, hy0, hx1, hy1 = px - POOL_R - 16, py - POOL_R - 16, px + POOL_R + 16, py + POOL_R + 16
    zb = -48
    K.add(box((hx0 - 16, hy0 - 16, zb - 16), (hx1 + 16, hy1 + 16, zb), {'top': T('pooltile'), 'side': CAULK, 'bot': CAULK}, detail=False))
    for (mn, mx, f) in (((hx0 - 16, hy0 - 16, zb), (hx0, hy1 + 16, -32), 'e'), ((hx1, hy0 - 16, zb), (hx1 + 16, hy1 + 16, -32), 'w'),
                        ((hx0, hy0 - 16, zb), (hx1, hy0, -32), 'n'), ((hx0, hy1, zb), (hx1, hy1 + 16, -32), 's')):
        K.add(box(mn, mx, tex6(**{f: T('pooltile')}), detail=False))
    poly = ngon(px, py, POOL_R, 20)
    st = K.stairs16(px + POOL_R - 100, py - 50, px + POOL_R + 8, py + 50, zb, 0, 'e', {'top': T('pooltile'), 'side': T('pooltile')})
    cut = prism(poly, zb, 8, T('pooltile'))
    fill = box((hx0, hy0, zb), (hx1, hy1, 0), T('pooltile'))
    for p in carve(fill, [cut] + st):
        for f in p.faces: f.tex = T('kerb') if (f.n[2] > 0.7 and abs(f.d) < 0.5) else (CAULK if f.n[2] < -0.7 else T('pooltile'))
        K.add(p)
    for p in carve(prism(poly, zb, -8, T('water')), st):
        for f in p.faces: f.tex = T('water') if (f.n[2] > 0.9 and abs(f.d + 8) < 0.5) else T('water_nd')
        K.add(p)
    K.spots.setdefault('water', []).append(dict(mn=[hx0, hy0, zb], mx=[hx1, hy1, -8], depth=40))
    K.reserve(((hx0, hy0, zb), (hx1, hy1, 8)))
    X = ML.Model()
    for k in range(6):
        a = 2 * math.pi * k / 6; x, y = 150 * math.cos(a), 150 * math.sin(a)
        ellipsoid(X.mesh(TX['duck']), (x, y, 0), 22, 16, 14, nu=10, nv=6)
        sphere(X.mesh(TX['duck']), (x + 16 * math.cos(a + 1.57), y + 16 * math.sin(a + 1.57), 18), 10, nu=8, nv=6)
        ellipsoid(X.mesh(TX['beak']), (x + 26 * math.cos(a + 1.57), y + 26 * math.sin(a + 1.57), 17), 7, 4, 3, nu=6, nv=4)
    ML.save('duck_ring', X)
    K.rotating_model2(ML.PLACE['duck_ring'][0], (px, py, -6), 10)
    K.keep_clear(px + POOL_R + 8, py - 60, px + POOL_R + 110, py + 60, 0)
    K.add(sign_box((px - 120, py + POOL_R + 40, 140), (px + 120, py + POOL_R + 46, 200), T('sign_ducks'), 1024, 256, facing='s', edge=T('wood')))
    for x in (px - 126, px + 126):
        K.add(box((x - 6, py + POOL_R + 37, 0), (x + 6, py + POOL_R + 49, 200), {'side': T('wood'), 'top': T('wood'), 'bot': CAULK}))


def stalls():
    """the midway: coconut shy, candy floss and ticket booths (walk in through a side door, counters you can vault,
    flat roofs you reach by pad), the burger van, test-your-strength"""
    sts = []
    def stall(name, rect, key, sign, door, counter_side, counter, sign_y=None):
        b = town.Building(K, name, rect, 0, (192,), M_(ext=key, int='b_plain', trim='b_trim', floor='b_floor', roofflat='b_roof', ceil='b_plain'),
                          doors=[door], roof='flat', windows={counter_side: [(counter[0], counter[1], 0, 70, 170)]})
        b.build(); sts.append(b)
        x0, y0, x1, y1 = rect
        if counter_side == 'e':
            K.add(sign_box((x1, counter[0], 176), (x1 + 6, counter[1], 236), T(sign), 1024, 256, facing='e', edge=T('wood')))
        elif counter_side == 'w':
            K.add(sign_box((x0 - 6, counter[0], 176), (x0, counter[1], 236), T(sign), 1024, 256, facing='w', edge=T('wood')))
        return b
    co = stall('coconut', (-1300, -1720, -800, -1380), 'b_red', 'sign_coconut', ('s', -1200, -1088), 'e', (-1690, -1410))
    deco('coconut_stand', -1000, -1550, 4, 90)
    cf = stall('candyfloss', (800, -1720, 1200, -1400), 'b_blue', 'sign_candy', ('s', 900, 1012), 'w', (-1690, -1430))
    place('candyfloss', 1080, -1500, 4)
    tb1 = stall('tickets_w', (-760, -2220, -480, -1980), 'booth', 'sign_tickets', ('n', -700, -588), 'e', (-2190, -2010))
    tb2 = stall('tickets_e', (480, -2220, 760, -1980), 'booth', 'sign_tickets', ('n', 588, 700), 'w', (-2190, -2010))
    # burger van: a little building in van livery with the serving hatch facing the midway
    van = town.Building(K, 'burgervan', (800, -1180, 1300, -900), 0, (200,), M_(ext='van_w', int='b_plain', trim='b_trim',
                        floor='b_floor', roofflat='b_roof', ceil='b_plain'), doors=[('e', -1100, -988)], roof='flat',
                        windows={'w': [(-1150, -930, 0, 80, 170)]})
    van.build(); sts.append(van)
    # test-your-strength: striker plate is a pad onto the coconut-shy roof
    K.jumppad(-600, -1300, 0, land=(-1000, -1550, 208), apex=420, name='pad_coconut', skin=skin('striker', angle=302), glow=False,
              edges=[(-800, -1450, 208)])
    K.jumppad(1450, -1300, 0, land=(1050, -1040, 216), apex=430, name='pad_van', skin=skin('trampoline'), glow=False,
              edges=[(1300, -1040, 216)])
    K.jumppad(600, -1300, 0, land=(1000, -1560, 208), apex=420, name='pad_candy', skin=skin('springboard'), glow=False,
              edges=[(800, -1460, 208)])
    K.jumppad(150, -1960, 0, land=(620, -2100, 208), apex=400, name='pad_tickets', skin=skin('trampoline'), glow=False,
              edges=[(480, -2060, 208)])
    for b in sts:
        x0, y0, x1, y1 = b.rect
        K.light((x0 + x1) / 2, (y0 + y1) / 2, 150, 260, '1 0.9 0.7')
    return sts


def caravans():
    for (x, y, a) in ((-2150, -1650, 0), (2150, -1700, 180)):
        b = town.Building(K, f'caravan{"w" if x < 0 else "e"}', (x - 210, y - 100, x + 210, y + 100), 32, (176,),
                          M_(ext='caravan_w', int='b_plain', trim='b_trim', floor='b_floor', roofflat='b_roof', ceil='b_plain'),
                          doors=[('n', x - 40, x + 72)], roof='flat', door_h=120, no_windows='nsew', ground_z=0)
        b.build()
        K.add(box((x - 210, y - 100, 0), (x + 210, y + 100, 32), {'top': CAULK, 'side': T('wood'), 'bot': CAULK}))
        K.reserve(K.stairs16(x - 40, y + 100, x + 72, y + 164, 0, 32, 's', {'top': T('stairtread'), 'side': T('stairside')}))
        K.keep_clear(x - 40, y + 164, x + 72, y + 240, 0)
        K.light(x, y, 150, 220, '1 0.85 0.6')
    K.jumppad(-2150, -1350, 0, land=(-2150, -1650, 224), apex=400, name='pad_caravan', skin=skin('springboard'), glow=False,
              edges=[(-2150, -1550, 224)])


def entrance():
    """the arch over the way in (pylons + a walkable top beam with the big sign below it)"""
    parts = [box((x - 60, Y0 + 140, 0), (x + 60, Y0 + 260, 520), 'x/x') for x in (-300, 300)]
    parts.append(box((-360, Y0 + 140, 520), (360, Y0 + 260, 560), 'x/x'))
    def arch_tex(c, n, poly):
        uv = ML.planar_uv(n, 128)
        if n[2] > 0.7 and c[2] > 550: return TX['wood'], uv
        if c[2] > 515: return TX['paint_yellow'], uv
        return TX['canvas_ry'], uv
    K.solid_piece('entrance_arch', parts, arch_tex)
    for b in parts: K.reserve(b)
    deco('arch_dress', 0, Y0 + 200, 0, 0)
    K.add(sign_box((-300, Y0 + 134, 400), (300, Y0 + 140, 516), T('sign_entrance'), 1024, 256, facing='s', edge=T('redpaint')))
    K.add(sign_box((-300, Y0 + 260, 400), (300, Y0 + 266, 516), T('sign_entrance'), 1024, 256, facing='n', edge=T('redpaint')))
    K.jumppad(0, Y0 + 520, 0, land=(0, Y0 + 200, 560), apex=720, name='pad_arch', skin=skin('springboard', angle='auto'), glow=False,
              edges=[(0, Y0 + 260, 560)])


def fortune_booth():
    cx, cy, r = -1120.0, 780.0, 160.0
    deco('fortune_tent', cx, cy, 0)
    n = 24
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        am = math.degrees((a0 + a1) / 2)
        z0 = 150 if -112 <= ((am + 180) % 360) - 180 <= -68 else 0
        pts = []
        for a in (a0, a1):
            for rr in (r - 10, r):
                pts += [(cx + rr * math.cos(a), cy + rr * math.sin(a), z0), (cx + rr * math.cos(a), cy + rr * math.sin(a), 194)]
        wb = hull(pts, WCLIP, round_pts=False); K.add(wb); K.reserve(wb)
    for k in range(16):                                           # cone roof (30 deg) up to a small gold crown
        a0 = 2 * math.pi * k / 16; a1 = 2 * math.pi * (k + 1) / 16
        pts = []
        for a in (a0, a1):
            for (rr, z) in ((40, 330), (r + 20, 194)):
                pts += [(cx + rr * math.cos(a), cy + rr * math.sin(a), z), (cx + rr * math.cos(a), cy + rr * math.sin(a), z - 12)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.add(cyl(cx, cy, 40, 318, 330, WCLIP, 12))
    place('crystal_ball', cx, cy + 40, 0)
    K.light(cx, cy, 150, 220, '0.8 0.5 1')
    K.route('fortune_door', (cx, cy - r - 120, 0), (cx, cy - 40, 0))
    K.keep_clear(cx - 60, cy - r - 112, cx + 60, cy - r, 0)
    K.jumppad(cx + 380, cy - 60, 0, land=(cx, cy, 330), apex=500, name='pad_fortune', skin=skin('springboard'), glow=False,
              edges=[(cx + r, cy, 194)])


def props():
    # festoon light strings along the midway + bins, benches, crates
    for y in (-1900, -1300, -800):
        deco('festoon_6', -330, y, 0, 0)
    for (x, y, a) in ((-330, 420, 0), (-1300, 240, 0), (620, 880, 0), (1500, 900, 90), (-1050, -420, 90)):
        place('festoon_6', x, y, 0, a)
    for (x, y) in ((-700, 450), (700, 450), (-400, 900), (450, 1050), (-900, -500), (900, -400), (-2200, 300), (2300, 900),
                   (-2300, -900), (100, 2100), (-700, 1900), (1000, 1900)):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, scale=0.55, lit=True)
    for (x, y) in ((-500, -1000), (480, -1100), (-1500, 700), (1300, 1000), (-450, 700), (2420, 1250), (-2300, 700)):
        place('crate_stack', x, y, 0, angle=(x * 3) % 90)
    K.catalog('pad_ducks/pad_duck.md3', -1350, -1000, 0, scale=0.6, angle=30, lit=True)
    for (x, y) in ((-1400, -300), (-1000, 500), (1300, 650), (2300, -300)):
        K.catalog('pad_ddmix/padship/shiplamp.md3', x, y, 0, scale=1.6, lit=True)


def cover():
    """sightline cover that belongs at a fair: generators in the corners, hay bales, picnic tables, food carts"""
    for (x, y, a) in ((2250, 2060, 0), (-2250, 2080, 0), (2300, -2080, 0), (-2330, -2090, 0), (2420, -650, 90), (-2420, 1300, 90)):
        place('generator', x, y, 0, a)
    for (x, y, a) in ((-1450, -720, 20), (-1700, -1300, 80), (1800, -1300, 10), (2350, -1250, 90), (-900, -110, 60),
                      (-2400, 220, 90), (2350, 1500, 90), (1150, 1200, 30),
                      (-1500, -1870, 0), (1500, -1870, 0), (-2200, -1880, 0), (2100, -1880, 0), (650, 1250, 70), (-1300, -560, 0), (-1600, -960, 90)):
        place('hay_bales', x, y, 0, a)
    for (x, y, a) in ((950, -250, 90), (-150, 330, 0), (700, 1800, 10), (-900, 1690, 80), (-400, -1240, 90), (-1600, 520, 0)):
        place('picnic_table', x, y, 0, a)
    for (x, y, a) in ((400, -760, 0), (-250, -920, 90), (180, -1380, 0), (-1150, 250, 30), (-60, -1620, 90)):
        place('hotdog_cart', x, y, 0, a)


def items():
    hx, hy, hz = WHEEL
    K.weapon('imperius', hx, hy, hz + 16, marker='purple')
    K.weapon('balloony', HS[0], HS[1], HS_H, marker='orange')
    K.weapon('betty', BT[0] - 330, BT[1] - 40, 300, marker='black')
    K.weapon('pumper', 1900, 300, 240, marker='green')
    K.weapon('splasher', POOL[0] - 60, POOL[1], -48, marker='blue')
    K.weapon('boaster', 0, -800, 2, marker='orange')
    K.weapon('bubbleg', -150, -1700, 2, marker='green')
    ammo = {'imperius': [(BT[0], BT[1] + 470, 80), (2150, -1700, 36), (-2150, -1650, 224), (0, Y0 + 200, 560)],
            'balloony': [(CAR[0] + 60, CAR[1], 640), (1400, 200, 240), (2300, 1900, 0), (-2300, 1900, 0)],
            'betty': [(BT[0] + 330, BT[1] - 40, 300), (BT[0], BT[1] + 500, 80), (-300, -150, 328), (1000, -1560, 208)],
            'pumper': [(1300, 440, 4), (1260, -40, 4), (1000, -1050, 4), (-2150, -1650, 36), (500, 1900, 0)],
            'splasher': [(POOL[0] + 120, POOL[1] + 60, -48), (-1000, -1550, 4), (-1600, -800, 0), (-2300, -200, 0)],
            'boaster': [(600, -700, 2), (-600, -700, 2), (1000, -1560, 4), (620, -2100, 208)],
            'bubbleg': [(150, -1700, 2), (-620, -2100, 4), (0, 600, 2), (1700, 1000, 2)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((-200, 200), (1000, 1300), (-1300, 900)): K.ammo('nipper', x, y, 2)
    K.item('item_armor_padshield', -1000, -1550, 208)
    K.item('item_speedy', 0, 800, 2)
    K.item('holdable_floater', HS[0] + 300, HS[1] + 100, 0)
    for (x, y, z) in ((CAR[0] - 60, CAR[1], 640), (1100, -1040, 216), (-300, 100, 328)): K.item('item_armor_shard', x, y, z)
    K.station(-400, -1500, 2, ang=0); K.station(1100, 900, 2, ang=180); K.station(-2420, 0, 0, ang=0)
    for (x, y, a) in ((0, -2000, 90), (-900, -1900, 45), (900, -1900, 135), (-400, -400, 90), (400, -400, 90), (-1300, -300, 0),
                      (1200, -650, 180), (-1100, 600, 0), (800, 700, 180), (-300, 1000, 270), (2200, 1100, 180), (-2300, 1100, 0),
                      (-2200, -1200, 45), (2200, -1100, 135), (0, 2000, 270), (1300, 1900, 225)):
        K.spawn(x, y, 2, a)


def vault():
    """the showmen's strongroom (secret): cash boxes, a crystal ball, Pad Power, Revival, Killer Ducks"""
    x, y, z = VAULT
    t = lambda **f: tex6(**f)
    w = 320
    K.add(box((x - w - 16, y - w - 16, z - 16), (x + w + 16, y + w + 16, z), t(top=T('vault')), detail=False),
          box((x - w - 16, y - w - 16, z + 300), (x + w + 16, y + w + 16, z + 316), t(bot=T('vault')), detail=False),
          box((x - w - 16, y - w, z), (x - w, y + w, z + 300), t(e=T('vault')), detail=False),
          box((x + w, y - w, z), (x + w + 16, y + w, z + 300), t(w=T('vault')), detail=False),
          box((x - w - 16, y - w - 16, z), (x + w + 16, y - w, z + 300), t(n=T('vault')), detail=False),
          box((x - w - 16, y + w, z), (x + w + 16, y + w + 16, z + 300), t(s=T('vault')), detail=False))
    K.item('item_padpower', x - 150, y + 150, z); K.item('item_revival', x + 150, y + 150, z); K.item('holdable_killerducks', x, y - 150, z)
    place('crystal_ball', x, y + 40, z)
    K.teleporter((x - 40, y - w + 8, z), (x + 40, y - w + 64, z + 96), dest=(0, 650, 2), angle=270, name='strongroom_exit')
    K.light(x, y, z + 250, 600, '1 0.6 0.9')


def lights():
    K.light_grid(X0 + 300, Y0 + 300, X1 - 300, Y1 - 300, 1100, 900, 2400, color='1 0.88 0.72')
    hx, hy, hz = WHEEL
    for (x, y, z, v, c) in ((hx, hy, hz + 200, 1200, '1 0.5 0.4'), (hx, hy - 400, 300, 700, '0.6 0.7 1'), (HS[0], HS[1], HS_H + 260, 420, '1 0.8 0.5'),
                            (CAR[0], CAR[1], 300, 900, '1 0.8 0.5'), (CAR[0], CAR[1], 800, 700, '1 0.7 0.6'),
                            (BT[0], BT[1], BT_PEAK + 220, 800, '1 0.8 0.6'), (0, -100, 250, 700, '0.7 0.8 1'), (0, -100, 520, 600, '1 0.9 0.7'),
                            (POOL[0], POOL[1], 200, 500, '0.6 0.8 1'), (0, Y0 + 200, 700, 700, '1 0.8 0.5'), (1700, 150, 700, 700, '0.6 0.5 1')):
        K.light(x, y, z, v, c)
    for (x, y, z, v) in ((1500, 200, 380, 320), (2050, 200, 380, 320), (2121, 1775, 400, 700), (-1728, 2064, 400, 700),
                         (2261, 181, 300, 600), (-2133, 1291, 300, 600), (-1216, 1216, 300, 600), (1139, -1421, 260, 500),
                         (2389, -1899, 300, 500), (-1216, -1536, 300, 500)):
        K.light(x, y, z, v, '1 0.85 0.65')
    K.timer_sound(0, 0, 600, 'human/applause', 'crowd', 45, 25)


def shader():
    TX.write_shader(extra=[SH.sky('env/pf-garden512', sun=(225, 35), sun_rgb=(0.7, 0.75, 1.0), sun_int=55, skylight=(30, 3))],
                    arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


def models():
    FM.mats(); building_mats()
    FM.wheel_rims(WR); FM.wheel_frame(WHEEL[2]); FM.gondola()
    FM.carousel_deck(CAR_RIN, CAR_ROUT); FM.carousel_top()
    FM.bigtop_shell(BT_R, BT_WALL, BT_PEAK); FM.trapeze_rig(h=300); FM.helter_tower(HS_R, HS_H)
    for k in ('dodgem_red', 'dodgem_blue', 'dodgem_yellow'): FM.dodgem_car(k)
    FM.pavilion(1000, 700, 312)
    FM.bouncy_castle(); FM.trampoline(); FM.cannon(); FM.striker_plate(); FM.coffin_pad(); FM.springboard()
    FM.fence_panel(); FM.festoon(660, name='festoon_6'); FM.candyfloss_machine(); FM.coconut_stand(); FM.skeleton(); FM.ghost_sheet()
    FM.crystal_ball(); FM.skull_sign(); FM.shutters(); FM.arch_dress(); FM.fortune_tent()
    FM.generator_trailer(); FM.hay_bales(); FM.picnic_table(); FM.hotdog_cart()
    X = ML.Model()
    for (mn, mx) in (((-60, -60, 0), (60, 60, 96)), ((60, -50, 0), (150, 40, 80)), ((-40, -40, 96), (40, 40, 170))):
        rbox(X.mesh(TX['crate']), mn, mx, r=4, k=2, tile=96)
    ML.save('crate_stack', X)
    FM.COLL['crate_stack'] = dict(boxes=[((-58, -58, 0), (58, 58, 96)), ((60, -48, 0), (148, 38, 80)), ((-38, -38, 96), (38, 38, 168))])


if __name__ == '__main__':
    textures()
    models()
    shell(); big_wheel(); carousel(); hs, TR = ghost_train(); helter_skelter(); big_top(); dodgems(); duck_pool()
    stalls(); caravans(); entrance(); fortune_booth(); props(); cover(); vault()
    items(); lights()
    K.fix_items()
    TR.sweep_check()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
