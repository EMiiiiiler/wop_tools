#!/usr/bin/env python3
"""Padman's Snow Globe (wop_padsnowglobe) - FFA in a winter village sealed inside a giant snow globe on a desk.

    OUT=<dir> python3 build_padsnowglobe.py          (wopbuild.py padsnowglobe preview / all)

48u per metre inside the globe (you are a villager). The glass is a sphere (centre z SPH_CZ, radius SPH_R) cut by the
snow at z 0 (floor radius RF). Outside the glass is the giant's desk at z DESK: the turned wooden base, a mug, a stack
of books, a pencil, the desk lamp that lights the globe, and the window behind (night sky) - all out of reach.
Inside: the skating rink and bandstand (centre), the chapel (north), the stage windmill (east), the sledging hill and
the snowman (west), the ice-fishing pond and hut (north-east), the log cabin (north-west), the gingerbread bakery and
cottages (south-west), the Christmas market (south-east) and the station (south) of the tiny train that circles the
whole village just inside the glass. Secret: the chapel organ -> the globe's music box under the snow.
Levels: fishing hole -144 | ground 0 | plateau 256 | bandstand roof 288 | stage 392 | tower 720 | hat 924 | cap 962.
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
from woplib import models as ML, shaders as SH, texlib as TL, town, railway as RW
from meshlib import Mesh, rbox, tube, revolve, disc, ellipsoid, sphere
import sg_models as GM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                     # the glass's footprint square
SPH_CZ, SPH_R, GT = 700.0, 2600.0, 32.0            # glass sphere centre height, inner radius, thickness
RF = math.sqrt(SPH_R ** 2 - SPH_CZ ** 2)            # 2504: where the glass meets the snow
RG = 2496.0                                         # snow disc radius (8u slot to the glass)
RUSE = 2150.0                                       # everything but the train stays inside this
HW = 4800.0; DESK = -480.0; CEIL = 5600.0          # the giant's room (the sealed hull)
TR_R = 2250.0                                       # train circle
RINK_R = 560.0; BAND_R = 170.0; BAND_ROOF = 272.0
TOWER = (-120.0, 900.0, 120.0, 1140.0); TOWER_H = 720.0
NAVE = (-210.0, 1190.0, 210.0, 1750.0)
MILL = (1450.0, 0.0); MILL_RECT = (1150.0, -300.0, 1750.0, 300.0)
HILL = (-1950.0, -250.0, -1300.0, 450.0); HILL_Z = 256.0; SNOWMAN = (-1700.0, 150.0)
POND = (1150.0, 1250.0); POND_R = 400.0; HOLE = (1078.0, 1178.0, 1222.0, 1322.0); HOLE_Z = -144.0
TREE = (800.0, -1000.0)
VAULT = (0.0, 0.0, -440.0)                          # the music box room under the snow (sealed)

K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '20', '_color': '0.8 0.85 1', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
GM.setup(TX)


def tex6(**f):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t.update(f); return t


def place(name, x, y, z, angle=0, occupy=True, **kw):
    c = GM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), occupy=occupy, **kw)


def deco(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


def skin(name, angle='auto'):
    c = GM.COLL.get(name, {})
    return dict(place=ML.PLACE[name], h=16, angle=angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()))


def M_(**m): return {k: TX[v] for k, v in m.items()}


def r_of(x, y): return math.hypot(x, y)


# ================================================================================================ textures
def textures():
    TX.add('snow', GM.snow_tex(seed=101), steps='snowsteps')
    TX.add('ice', TL.frost((196, 222, 238), 102), 'slick', steps='snowsteps')
    TX.add('cobble', TL.grime(TL.stone((150, 150, 158), cells=60, edge=(200, 206, 214), edge_w=0.05, vary=14, seed=103), 0.1, 104),
           steps='snowsteps')
    TX.add('rock', TL.grime(TL.stone((120, 118, 126), cells=30, edge=(80, 78, 86), seed=105), 0.2, 106))
    TX.add('platform', TL.tiles((160, 156, 150), (110, 106, 100), cols=4, rows=4, offset=0.5, seed=107))
    TX.add('stairtread', TL.planks((150, 112, 72), 2, (90, 64, 40), 8, False, False, 108), steps='woodsteps')
    TX.add('stairside', TL.solid((120, 90, 60), 4, 109, 128))
    TX.add('pooltile', TL.tiles((60, 110, 140), (180, 200, 210), cols=6, rows=6, offset=0, grout_w=0.05, seed=110))
    TX.add('water', TL.solid((40, 90, 120), 10, 111, 128), 'water', rgb=(0.2, 0.4, 0.5), alpha=0.6)
    TX.add('slidefloor', TL.solid((220, 230, 240), 3, 112, 128), steps='snowsteps')
    TX.add('desk', TL.planks((120, 70, 40), 3, (80, 44, 24), 12, False, False, 113))
    TX.add('wallpaper', GM.wallpaper_tex())
    TX.add('skirting', TL.solid((220, 214, 200), 3, 114, 128))
    TX.add('ceiling', TL.solid((200, 196, 186), 4, 115, 128))
    TX.add('velvet', TL.fabric((90, 20, 50), 32, 116))
    TX.add('brasswall', TL.metal((170, 130, 60), True, 117))
    for key, text, bg, fg, sub in (('sign_station', 'PADVILLE', (30, 60, 40), (240, 220, 150), 'HALT'),
                                   ('sign_bakery', 'GINGERBREAD', (120, 60, 30), (255, 240, 220), 'BAKERY'),
                                   ('sign_market', 'WINTER MARKET', (140, 30, 40), (255, 230, 160), None),
                                   ('sign_mill', 'PADMILL', (40, 50, 80), (240, 236, 220), 'FLOUR'),
                                   ('sign_bait', 'BAIT & TACKLE', (40, 80, 110), (240, 240, 240), None),
                                   ('sign_toys', 'TOYS', (180, 40, 60), (255, 230, 90), None)):
        TX.add(key, GM.sign_tex(text, bg, fg, sub=sub), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(150, 210, 255), rubber=(60, 64, 72))


def building_mats():
    M = TX.material
    M('cab_logs', TL.stripes((126, 82, 48), (96, 60, 34), 12, False, 0.5, 120), shade=20)
    M('b_plaster', TL.solid((236, 226, 204), 4, 121, 128), shade=20)
    M('b_blue', TL.solid((150, 180, 210), 4, 122, 128), shade=20)
    M('b_pink', TL.solid((226, 170, 170), 4, 123, 128), shade=20)
    M('b_yellow', TL.solid((236, 210, 140), 4, 124, 128), shade=20)
    M('b_ginger', TL.grime(TL.solid((170, 104, 52), 6, 125, 128), 0.15, 126), shade=20)
    M('b_stone', TL.stone((178, 170, 156), cells=40, edge=(130, 122, 110), edge_w=0.02, seed=127), shade=20)
    M('b_brick', TL.bricks((150, 70, 52), (200, 190, 176), seed=128), shade=20)
    M('b_trim', TL.solid((240, 238, 232), 3, 129, 64), shade=20)
    M('b_trim_red', TL.solid((180, 40, 40), 3, 130, 64), shade=20)
    M('b_icing', TL.solid((250, 250, 250), 2, 131, 64), shade=20)
    M('b_floor', TL.planks((150, 108, 66), 6, (90, 62, 36), 10, True, False, 132), shade=20, steps='woodsteps')
    M('b_roofsnow', GM.snow_tex(seed=133, base=(240, 244, 250)), shade=20)
    M('b_candyroof', TL.stripes((250, 250, 250), (230, 60, 70), 8, True, 0.15, 134), shade=20)
    M('b_ceil', TL.solid((220, 212, 196), 4, 135, 128), shade=20)
    M('b_chalet', TL.planks((150, 100, 60), 6, (96, 62, 34), 8, False, True, 136), shade=20)
    M('b_station', TL.solid((60, 110, 80), 4, 137, 128), shade=20)


# ================================================================================================ globe, snow and the giant's room
def room():
    """the sealed hull = the giant's room: desk top, wallpapered walls, ceiling, the window (sky) behind the desk"""
    S = T('sky')
    K.add(box((-HW - 32, -HW - 32, DESK - 32), (HW + 32, HW + 32, DESK), tex6(top=T('desk')), detail=False))
    K.add(box((-HW - 32, -HW - 32, CEIL), (HW + 32, HW + 32, CEIL + 32), tex6(bot=T('ceiling')), detail=False))
    K.add(box((-HW - 32, -HW, DESK), (-HW, HW, CEIL), tex6(e=T('wallpaper')), detail=False))
    K.add(box((HW, -HW, DESK), (HW + 32, HW, CEIL), tex6(w=T('wallpaper')), detail=False))
    K.add(box((-HW - 32, -HW - 32, DESK), (HW + 32, -HW, CEIL), tex6(n=T('wallpaper')), detail=False))
    # north wall with the big window: wallpaper round it, sky in the opening
    wx0, wx1, wz1 = -2700.0, 2700.0, 4400.0
    for r in sub_rects((-HW - 32, DESK, HW + 32, CEIL), [(wx0, DESK, wx1, wz1)]):
        W = T('wallpaper'); K.add(box((r[0], HW, r[1]), (r[2], HW + 32, r[3]), tex6(s=W, e=W, w=W, top=W, bot=W), detail=False))
    K.add(box((wx0, HW + 32, DESK), (wx1, HW + 64, wz1), tex6(s=S), detail=False))
    deco('window_frame', 0, HW - 40, DESK - 3, 0, lit=True)
    # desk things (out of reach behind the glass)
    deco('plinth', 0, 0, 0, 0)
    deco('giant_mug', -3400, 3000, DESK, 30)
    deco('book_stack', 3150, 3000, DESK, 10)
    deco('giant_pencil', 2500, -3500, DESK, 12)
    deco('desk_lamp', -3300, -3000, DESK, 0)
    # the lamp's light falls on the globe from above the south-west; the window gives a little moonlight
    K.light(-1650, -1600, 3700, 9000, '1 0.86 0.62', spawnflags=1)
    K.light(0, 4300, 3000, 2500, '0.55 0.65 1', spawnflags=1)
    K.light(3000, 2500, 2000, 2000, '1 0.86 0.62', spawnflags=1)


def snow_ground():
    """the snow disc with the rink, the pond and the paths cut in as their own textures"""
    disc_b = prism(ngon(0, 0, RG, 48, phase=0), -32, 0, {'top': T('snow'), 'side': CAULK, 'bot': CAULK})
    rink = prism(ngon(0, 0, RINK_R, 32), -32, 0, {'top': T('ice'), 'side': CAULK, 'bot': CAULK})
    pond = prism(ngon(POND[0], POND[1], POND_R, 24), -32, 0, {'top': T('ice'), 'side': CAULK, 'bot': CAULK})
    hole = box((HOLE[0], HOLE[1], -32), (HOLE[2], HOLE[3], 0), CAULK)
    paths = [box((-150, -1966, -32), (150, -RINK_R + 40, 0), T('cobble')), box((-110, RINK_R - 40, -32), (110, 900, 0), T('cobble')),
             box((RINK_R - 40, -90, -32), (1150, 90, 0), T('cobble')), box((-1300, -40, -32), (-RINK_R + 40, 280, 0), T('cobble')),
             box((-1100, -980, -32), (-700, -880, 0), T('cobble')), box((-700, -1300, -32), (-150, -1200, 0), T('cobble')), box((150, -1300, -32), (450, -1200, 0), T('cobble'))]
    for p in carve(disc_b, [rink, pond] + paths):
        for f in p.faces: f.tex = T('snow') if f.n[2] > 0.9 else CAULK
        K.add(p)
    K.add(rink)
    for p in carve(pond, [hole]):
        for f in p.faces: f.tex = T('ice') if f.n[2] > 0.9 else CAULK
        K.add(p)
    for pb in paths:
        for p in carve(pb, [rink]):
            for f in p.faces: f.tex = T('cobble') if f.n[2] > 0.9 else CAULK
            K.add(p)


def glass():
    """the glass sphere as weapclip cells (players and shots stop at it) + the visible two-sided glass MD3"""
    e0 = -math.asin(SPH_CZ / SPH_R)
    bands = [(e0, 0.0, 48), (0.0, 15.0, 48), (15.0, 30.0, 48), (30.0, 45.0, 48), (45.0, 60.0, 24), (60.0, 75.0, 24)]
    def pt(r, a, e):
        return (r * math.cos(e) * math.cos(a), r * math.cos(e) * math.sin(a), max(0.0, SPH_CZ + r * math.sin(e)))
    for (ea, eb, n) in bands:
        ea_r = ea if isinstance(ea, float) and ea < 0 else math.radians(ea)
        eb_r = math.radians(eb)
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            pts = [pt(r, a, e) for r in (SPH_R, SPH_R + GT) for a in (a0, a1) for e in (ea_r, eb_r)]
            K.add(hull(pts, WCLIP, round_pts=False))
    cap = [pt(r, 2 * math.pi * k / 24, math.radians(75)) for r in (SPH_R, SPH_R + GT) for k in range(24)]
    cap += [(0, 0, SPH_CZ + SPH_R), (0, 0, SPH_CZ + SPH_R + GT)]
    K.add(hull(cap, WCLIP, round_pts=False))
    deco('glass_dome', 0, 0, 0, 0, lit=False)
    deco('snowfall', 0, 0, 0, 0, lit=False, _structure=1)


# ================================================================================================ centre: skating rink + bandstand
def rink():
    place('bandstand', 0, 0, 0, 22.5, occupy=False)
    a0 = math.pi / 8
    for k in range(8):                                           # posts (weapclip)
        a = a0 + 2 * math.pi * k / 8 + math.radians(22.5)
        px, py = (BAND_R - 14) * math.cos(a), (BAND_R - 14) * math.sin(a)
        K.add(box((px - 7, py - 7, 32), (px + 7, py + 7, BAND_ROOF), WCLIP))
    K.add(prism(ngon(0, 0, BAND_R + 24, 8, phase=22.5 + 22.5), 0, 16, {'top': T('platform'), 'side': T('rock'), 'bot': CAULK}))
    K.add(prism(ngon(0, 0, BAND_R, 8, phase=22.5 + 22.5), 16, 32, {'top': T('stairtread'), 'side': T('stairside'), 'bot': CAULK}))
    K.add(prism(ngon(0, 0, 212, 8, phase=22.5 + 22.5), BAND_ROOF, BAND_ROOF + 16, WCLIP))
    # railings on the four diagonal sides (32u: jumpable cover)
    for k in (1, 3, 5, 7):
        a1 = math.radians(45 * k); a2 = math.radians(45 * (k + 1))
        P = [((BAND_R - 14) * math.cos(a), (BAND_R - 14) * math.sin(a)) for a in (a1, a2)]
        d = np.array(P[1]) - np.array(P[0]); d /= np.linalg.norm(d); nrm = np.array([-d[1], d[0]]) * 3
        P = [np.array(P[0]) + d * 10, np.array(P[1]) - d * 10]
        pts = [(p[0] + s * nrm[0], p[1] + s * nrm[1], z) for p in P for s in (-1, 1) for z in (32, 64)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.occupy_r(0, 0, 240, 0, 320)
    K.jumppad(380, -320, 0, land=(0, 0, BAND_ROOF + 16), apex=BAND_ROOF + 190, name='pad_bandstand', skin=skin('curling_pad'),
              glow=False, edges=[(160, -135, BAND_ROOF + 16)])
    K.jumppad(-380, 320, 0, land=(0, 0, BAND_ROOF + 16), apex=BAND_ROOF + 190, name='pad_bandstand2', skin=skin('curling_pad'),
              glow=False, edges=[(-160, 135, BAND_ROOF + 16)])
    K.route('bandstand_steps', (0, -330, 0), (0, 0, 32))
    for (x, y, a) in ((0, -620, 0), (620, 0, 90), (-560, -340, 210), (420, 440, 135)):
        place('bench', x, y, 0, a)
    K.light(0, 0, BAND_ROOF - 20, 260, '1 0.85 0.6'); K.light(0, 0, BAND_ROOF + 220, 500, '1 0.9 0.75')
    K.speaker(0, 0, 120, 'misc/wind_chimes')


# ================================================================================================ north: the chapel
def wall_holes(axis, fixed0, fixed1, span, zr, holes):
    """vertical wall slab with rectangular openings: axis 'x' (wall runs along x, y between fixed0..fixed1)"""
    out = []
    for r in sub_rects((span[0], zr[0], span[1], zr[1]), holes):
        if axis == 'x': out.append(box((r[0], fixed0, r[1]), (r[2], fixed1, r[3]), 'x/x'))
        else: out.append(box((fixed0, r[0], r[1]), (fixed1, r[2], r[3]), 'x/x'))
    return out


def chapel():
    x0, y0, x1, y1 = TOWER; t = 24.0; H = TOWER_H
    bel = (500.0, 640.0)
    parts = []
    cx = (x0 + x1) / 2
    door = [(cx - 56, 0, cx + 56, 176), (cx - 48, bel[0], cx + 48, bel[1])]
    louv = [(cx - 48, bel[0], cx + 48, bel[1])]
    parts += wall_holes('x', y0, y0 + t, (x0, x1), (0, H - 16), door)                   # south (door + belfry)
    parts += wall_holes('x', y1 - t, y1, (x0, x1), (0, H - 16), door)                   # north (door to the nave)
    cy = (y0 + y1) / 2
    parts += wall_holes('y', x0, x0 + t, (y0 + t, y1 - t), (0, H - 16), [(cy - 48, bel[0], cy + 48, bel[1])])
    parts += wall_holes('y', x1 - t, x1, (y0 + t, y1 - t), (0, H - 16), [(cy - 48, bel[0], cy + 48, bel[1])])
    parts.append(box((x0, y0, H - 16), (x1, y1, H), 'x/x'))
    def ttex2(c, n, poly):
        if n[2] > 0.9 and c[2] > H - 2: return None
        uvf = ML.planar_uv(n, 160)
        return TX['chapel_stone'], uvf
    K.solid_piece('chapel_tower', parts, ttex2)
    for b in parts: K.reserve(b)
    deco('tower_dress', cx, cy, 0, 0)
    nave = town.Building(K, 'chapel', NAVE, 0, (300,), M_(ext='b_stone', int='b_plaster', trim='b_trim', floor='b_floor',
                         roof='b_roofsnow', ceil='b_ceil', gable='b_stone'),
                         doors=[('s', -56, 56), ('e', 1560, 1672)], roof='gable_y', door_h=200,
                         windows={'e': [(1280, 1340, 0, 90, 250), (1420, 1480, 0, 90, 250)],
                                  'w': [(1280, 1340, 0, 90, 250), (1420, 1480, 0, 90, 250), (1560, 1620, 0, 90, 250)]})
    nave.build()
    # inside: pews either side of the aisle, the altar, the organ against the north wall (secret entry)
    for y in (1280, 1360, 1440):
        for x in (-100, 100):
            place('pew', x, y, 4, 0)
    place('altar', 0, 1550, 4, 0)
    place('organ', 0, NAVE[3] - 16, 4, 0)
    K.secret((-34, NAVE[3] - 88, 4), (34, NAVE[3] - 26, 100), dest=(VAULT[0], VAULT[1] - 200, VAULT[2]), angle=90, name='musicbox',
             approach='s')
    K.light(0, 1450, 250, 300, '1 0.8 0.55'); K.light(0, 1650, 200, 200, '1 0.7 0.4')
    K.light(0, 1020, 600, 220, '1 0.85 0.6'); K.light(0, 1020, 140, 180, '1 0.85 0.6')
    # pads: the tower top (Imperius) and the nave ridge
    K.jumppad(420, 760, 0, land=(0, 1020, H), apex=H + 170, name='pad_tower', skin=skin('ski_pad'), glow=False,
              edges=[(x1, y0 + 40, H)])
    rx, ry, rz = nave.roof_spot(0.55)
    K.jumppad(520, 1500, 0, land=(rx, 1500, rz), apex=rz + 170, name='pad_chapel', skin=skin('present_pad1'), glow=False,
              edges=[(NAVE[2] + 20, 1500, 300)])
    # churchyard
    for (x, y, k, a) in ((-420, 1250, 0, 0), (-480, 1420, 1, 10), (-400, 1580, 0, -8), (-560, 1300, 1, 5), (-560, 1520, 0, 0)):
        place(f'gravestone{k}', x, y, 0, a + 90)
    for (x, y) in ((-700, 1000), (430, 1850), (-420, 1900)):
        place('pine', x, y, 0, (x * 7) % 360)
    return nave


# ================================================================================================ east: the windmill
def windmill():
    mx, my = MILL
    base = town.Building(K, 'millbase', MILL_RECT, 0, (200, 176), M_(ext='b_brick', int='b_plaster', trim='b_trim', floor='b_floor',
                         roofflat='b_roofsnow', ceil='b_ceil'),
                         doors=[('w', -56, 56), ('s', 1394, 1506)], roof='flat',
                         stairs=[(1180, 176, 1596, 284, 'e')], roof_stairs=(1210, -284, 1610, -188, "e"))
    base.build()
    zs = base.roof_top                                                      # the stage you walk round the tower on
    K.add(sign_box((1150 - 6, -200, 120), (1150, -60, 170), T('sign_mill'), 1024, 256, facing='w', edge=T('stairside')))
    r0, r1, h = 200.0, 150.0, 490.0                                         # walls up to the cap skirt
    n = 16
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        am = math.degrees((a0 + a1) / 2)
        if abs(((am + 90 + 180) % 360) - 180) < 20: zlo = zs + 140                 # door toward -y
        else: zlo = zs
        pts = []
        for a in (a0, a1):
            for (rb, rt) in ((r0 - 16, r1 - 16 + (r0 - r1) * 0.0), (r0, r1)):
                fb = (zlo - zs) / 520.0
                rbz = r0 - (r0 - r1) * fb if rb == r0 else r0 - 16 - (r0 - r1) * fb
                rtz = r0 - (r0 - r1) * (h / 520.0) if rb == r0 else r0 - 16 - (r0 - r1) * (h / 520.0)
                pts += [(mx + rbz * math.cos(a), my + rbz * math.sin(a), zlo), (mx + rtz * math.cos(a), my + rtz * math.sin(a), zs + h)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.add(cyl(mx, my, 232, zs + h, zs + 570, WCLIP, 16))                    # the cap drum: its flat top is walkable
    deco('mill_tower', mx, my, zs, 0)
    deco('mill_cap', mx, my, zs + 520, 0)
    K.rotating_model2(ML.PLACE['mill_sails'][0], (mx + 262, my, zs + 540), 24, axis='x')
    K.occupy_r(mx, my, 240, zs, zs + 600)
    K.route('mill_tower_door', (mx, my - 300, zs), (mx, my - 60, zs))
    cap_top = zs + 570
    K.jumppad(1100, -650, 0, land=(mx, my - 20, cap_top), apex=cap_top + 150, name='pad_cap', skin=skin('flour_pad'), glow=False,
              edges=[(1294, -300, zs), (1337, -223, cap_top)])
    K.jumppad(mx, 760, 0, land=(mx, 240, zs), apex=zs + 170, name='pad_stage', skin=skin('flour_pad'), glow=False,
              edges=[(mx, 300, zs)])
    K.light(mx, my, zs + 300, 260, '1 0.85 0.6'); K.light(1300, 0, 120, 260, '1 0.85 0.6'); K.light(1300, 0, 300, 240, '1 0.85 0.6')
    K.speaker(mx, my, zs + 200, 'machine/mechanics')
    return base, cap_top


# ================================================================================================ west: sledging hill + snowman
def sledging_hill():
    x0, y0, x1, y1 = HILL
    parts = [box((x0, y0, 0), (x1, y1, HILL_Z), 'x/x')]
    def htex(c, n, poly):
        uvf = ML.planar_uv(n, 256)
        return (TX['snow_m'] if n[2] > 0.9 else TX['rock_m']), uvf
    K.solid_piece('hill', parts, htex)
    K.reserve(*parts)
    K.ramp(x1, -60, -720, 260, 0, HILL_Z, 'w', {'top': T('snow'), 'side': T('rock'), 'bot': CAULK}, route='hill_ramp')
    K.reserve(((x1, -60, 0), (-720, 260, HILL_Z)))
    # snowman (collision drums; the hat top is the Balloony perch)
    sx, sy = SNOWMAN; z = HILL_Z
    tiers = [(130, 0, 260), (95, 260, 440), (66, 440, 570), (110, 570, 578), (70, 578, 668)]
    for (r, a, b) in tiers:
        K.add(cyl(sx, sy, r, z + a, z + b, WCLIP, 16 if r > 80 else 12))
    deco('snowman', sx, sy, z, 0)
    K.occupy_r(sx, sy, 150, z, z + 700)
    hat = z + 668
    K.jumppad(-1440, 150, HILL_Z, land=(sx, sy, hat), apex=hat + 160, name='pad_hat', skin=skin('sled_pad'), glow=False,
              edges=[(sx + 110, sy, z + 578)])
    # the toboggan run: down from the north edge of the plateau, round to the cabin meadow (walkable both ways, 16 deg)
    pts = [(-1650, y1, HILL_Z), (-1652, 560, 226), (-1690, 700, 190), (-1660, 830, 148), (-1560, 920, 106), (-1420, 965, 66),
           (-1270, 985, 32), (-1140, 990, 16)]
    pts = [(x, y, float(zz)) for (x, y, zz) in pts]
    pts[0] = (pts[0][0], y1 + 1, HILL_Z)
    K.slide(pts, 56, 40, T('slidefloor'), wall_tex=T('rock'))
    low = [p for p in pts if p[2] < 140]
    if len(low) > 1: K.slide_skirt(low, 56, 0)
    X = ML.Model(); ML.flume(X, pts, 56, 40, TX['roof_snow']); c = np.mean(np.array(pts), 0)
    X.shift((c[0], c[1], 0)); ML.save('toboggan', X); deco('toboggan', c[0], c[1], 0)
    K.route('toboggan', (-1040, 990, 0), (-1650, 300, HILL_Z))
    for (x, y, s) in ((-1850, -150, 1), (-1400, 380, 2), (-1800, 330, 3)):
        deco(f'snow_drift{s}', x, y, HILL_Z)
    K.light(-1600, 100, 800, 500, '0.9 0.92 1')


# ================================================================================================ north-east: ice-fishing pond
def fishing_pond():
    px, py = POND
    hx0, hy0, hx1, hy1 = HOLE
    zb = HOLE_Z
    # the hole under the hut: tiled shaft below the snow slab, water to -8, teleporter out at the bottom
    K.add(box((hx0 - 16, hy0 - 16, zb - 16), (hx1 + 16, hy1 + 16, zb), {'top': T('pooltile'), 'side': CAULK, 'bot': CAULK}))
    for (mn, mx, f) in (((hx0 - 16, hy0 - 16, zb), (hx0, hy1 + 16, -32), 'e'), ((hx1, hy0 - 16, zb), (hx1 + 16, hy1 + 16, -32), 'w'),
                        ((hx0, hy0 - 16, zb), (hx1, hy0, -32), 'n'), ((hx0, hy1, zb), (hx1, hy1 + 16, -32), 's')):
        K.add(box(mn, mx, tex6(**{f: T('pooltile')})))
    K.add(box((hx0, hy0, zb), (hx1, hy1, -8), tex6(top=T('water'), n=T('water_nd'), s=T('water_nd'), e=T('water_nd'), w=T('water_nd'),
                                                    bot=T('water_nd'))))
    K.spots.setdefault('water', []).append(dict(mn=[hx0, hy0, zb], mx=[hx1, hy1, -8], depth=136))
    K.teleporter((px - 30, hy0 + 8, zb), (px + 30, hy0 + 60, zb + 80), dest=(px, 1030, 0), angle=270, name='hole_exit')
    hut = town.Building(K, 'hut', (1010, 1110, 1290, 1390), 0, (160,), M_(ext='b_blue', int='b_plaster', trim='b_trim', floor='b_floor',
                        roof='b_roofsnow', ceil='b_ceil', gable='b_blue'),
                        doors=[('s', 1100, 1200)], roof='gable_x', floor_mat=False, windows={'n': [(1110, 1190, 0, 70, 130)]})
    hut.build()
    K.add(sign_box((1060, 1104, 106), (1240, 1110, 136), T('sign_bait'), 1024, 256, facing='s', edge=T('stairside')))
    K.reserve(((hx0, hy0, zb), (hx1, hy1, 4)))
    rx, ry, rz = hut.roof_spot(0.5)
    K.jumppad(1560, 980, 0, land=(rx, ry, rz), apex=rz + 170, name='pad_hut', skin=skin('ski_pad'), glow=False,
              edges=[(1290, 1200, 160)])
    for (x, y, a) in ((900, 950, 30), (1450, 1500, 120)):
        place('bench', x, y, 0, a)
    K.light(px, py, 120, 180, '1 0.85 0.6'); K.light(px, py, -60, 160, '0.5 0.8 1')
    return hut


# ================================================================================================ north-west: log cabin
def log_cabin():
    c = town.Building(K, 'cabin', (-1200, 1140, -720, 1460), 0, (192, 160), M_(ext='cab_logs', int='cab_logs', trim='b_trim_red',
                      floor='b_floor', roof='b_roofsnow', ceil='b_ceil', gable='cab_logs'),
                      doors=[('s', -1010, -898), ('e', 1200, 1312)], roof='gable_x', stairs=[(-1180, 1350, -796, 1440, 'e')], no_windows='n')
    c.build()
    rx, ry, rz = c.roof_spot(0.4)
    K.jumppad(-560, 1060, 0, land=(rx, ry, rz), apex=rz + 170, name='pad_cabin', skin=skin('sled_pad'), glow=False,
              edges=[(-720, 1300, 352)])
    place('woodpile', -1340, 1300, 0, 90)
    place('sleigh', -560, 1650, 0, 200)
    K.light(-960, 1300, 150, 220, '1 0.8 0.55'); K.light(-960, 1300, 320, 200, '1 0.8 0.55')
    return c


# ================================================================================================ south-west: gingerbread bakery + cottages
def village():
    bs = []
    bak = town.Building(K, 'bakery', (-1250, -1300, -800, -980), 0, (192, 160), M_(ext='b_ginger', int='b_plaster', trim='b_icing',
                        floor='b_floor', roof='b_candyroof', ceil='b_ceil', gable='b_ginger'),
                        doors=[('n', -1100, -988)], roof='gable_x', stairs=[(-1230, -1284, -846, -1190, 'e')], no_windows='s')
    bak.build(); bs.append(bak)
    K.add(sign_box((-1150, -1306, 150), (-900, -1300, 190), T('sign_bakery'), 1024, 256, facing='s', edge=T('stairside')))
    ca = town.Building(K, 'cottage_a', (-1750, -900, -1400, -600), 0, (176,), M_(ext='b_pink', int='b_plaster', trim='b_trim',
                       floor='b_floor', roof='b_roofsnow', ceil='b_ceil', gable='b_pink'), doors=[('e', -800, -688)], roof='gable_y')
    ca.build(); bs.append(ca)
    cb = town.Building(K, 'toyshop', (-1350, -1650, -1050, -1400), 0, (176,), M_(ext='b_yellow', int='b_plaster', trim='b_trim_red',
                       floor='b_floor', roof='b_roofsnow', ceil='b_ceil', gable='b_yellow'), doors=[('n', -1260, -1148)], roof='gable_x')
    cb.build(); bs.append(cb)
    K.add(sign_box((-1300, -1400, 130), (-1100, -1394, 165), T('sign_toys'), 1024, 256, facing='n', edge=T('stairside')))
    for (b, pad, spot, frac, edge) in ((bak, (-680, -1400), 'present_pad0', 0.4, (-800, -1250, 352)),
                                       (ca, (-1250, -560), 'present_pad2', 0.5, (-1400, -700, 176)),
                                       (cb, (-900, -1560), 'present_pad3', 0.5, (-1050, -1525, 176))):
        rx, ry, rz = b.roof_spot(frac)
        K.jumppad(pad[0], pad[1], 0, land=(rx, ry, rz), apex=rz + 170, name=f'pad_{b.name}', skin=skin(spot), glow=False, edges=[edge])
    for b in bs:
        x0, y0, x1, y1 = b.rect
        K.light((x0 + x1) / 2, (y0 + y1) / 2, 150, 220, '1 0.8 0.55')
    place('woodpile', -1600, -1050, 0, 0)
    return bs


# ================================================================================================ south: the station and the tiny train
def station():
    K.add(box((-320, -2150, 0), (320, -2030, 32), {'top': T('platform'), 'side': T('rock'), 'bot': CAULK}))
    K.reserve(((-320, -2150, 0), (320, -2030, 32)))
    K.reserve(K.stairs16(-200, -2030, 200, -1966, 0, 32, 's', {'top': T('stairtread'), 'side': T('stairside')}))
    K.keep_clear(-200, -1966, 200, -1900, 0)
    K.route('platform', (0, -1880, 0), (0, -2090, 32))
    st = town.Building(K, 'station', (360, -2000, 700, -1760), 0, (176,), M_(ext='b_station', int='b_plaster', trim='b_trim',
                       floor='b_floor', roof='b_roofsnow', ceil='b_ceil', gable='b_station'), doors=[('w', -1940, -1828)], roof='gable_x')
    st.build()
    K.add(sign_box((-200, -2040, 150), (200, -2034, 210), T('sign_station'), 1024, 256, facing='n', edge=T('stairside')))
    for x in (-210, 210):
        K.add(box((x - 6, -2040, 32), (x + 6, -2028, 210), {'side': T('stairside'), 'top': T('stairside'), 'bot': CAULK}))
    rx, ry, rz = st.roof_spot(0.5)
    K.jumppad(860, -1700, 0, land=(rx, ry, rz), apex=rz + 170, name='pad_station', skin=skin('present_pad1'), glow=False,
              edges=[(700, -1880, 176)])
    place('bench', -120, -2100, 32, 0); place('bench', 120, -2100, 32, 0)
    K.light(0, -2090, 220, 260, '1 0.85 0.6'); K.light(530, -1880, 150, 200, '1 0.8 0.55')
    # the train: a little tank engine pulling three wagons round the whole village just inside the glass
    cars = [RW.Car('loco', GM.loco(), -100, 124, 122, 54, gap=20)]
    for k in range(3):
        cars.append(RW.Car(f'wagon{k}', GM.flatcar(k), -90, 90, 30, 50, gap=20))
    TR = RW.CircleTrain(K, 'snowtrain', (0, 0), TR_R, 18, cars, front_deg=280.0, speed=3.0, origin_dz=1500)
    TR.build()
    RW.track_ring(K, 'snowtrack', (0, 0), TR_R, 0, TX['iron'], TX['wood_dark'], gauge=64.0, n=64, tie_len=116, tie_w=14, tie_h=8, rail_h=10)
    return st, TR


# ================================================================================================ south-east: the winter market
def market():
    place('xmas_tree', TREE[0], TREE[1], 0, 0)
    place('presents_pile', TREE[0] - 340, TREE[1] - 50, 0, 20)
    chs = []
    for (name, rect, door, cside, counter, pad, roofdir) in (
            ('chalet1', (450, -1500, 750, -1280), ('w', -1450, -1338), 'n', (500, 700), (380, -1660), 'gable_x'),
            ('chalet2', (1100, -1550, 1400, -1330), ('e', -1500, -1388), 'n', (1150, 1350), (1560, -1250), 'gable_x'),
            ('chalet3', (1400, -1000, 1650, -700), ('s', 1470, 1582), 'w', (-950, -750), (1250, -1150), 'gable_y')):
        b = town.Building(K, name, rect, 0, (176,), M_(ext='b_chalet', int='b_plaster', trim='b_trim_red', floor='b_floor',
                          roof='b_roofsnow', ceil='b_ceil', gable='b_chalet'), doors=[door], roof=roofdir,
                          windows={cside: [(counter[0], counter[1], 0, 70, 150)]})
        b.build(); chs.append(b)
        x0, y0, x1, y1 = rect
        w, d = (x1 - x0, y1 - y0) if roofdir == 'gable_x' else (y1 - y0, x1 - x0)
        deco(f'market_dress_{int(w)}_{int(d)}', (x0 + x1) / 2, (y0 + y1) / 2, 0, 0 if roofdir == 'gable_x' else 90)
        rx, ry, rz = b.roof_spot(0.5)
        e = (x0 - 20, ry, 176) if pad[0] < x0 else (x1 + 20, ry, 176) if pad[0] > x1 else (rx, y0 - 20, 176)
        K.jumppad(pad[0], pad[1], 0, land=(rx, ry, rz), apex=rz + 170, name=f'pad_{name}', skin=skin('present_pad0'), glow=False,
                  edges=[e])
        K.light((x0 + x1) / 2, (y0 + y1) / 2, 140, 200, '1 0.8 0.55')
    K.add(sign_box((862, -1260, 220), (1138, -1254, 280), T('sign_market'), 1024, 256, facing='n', edge=T('stairside')))
    for x in (856, 1144):
        K.add(box((x - 6, -1266, 0), (x + 6, -1248, 280), {'side': T('stairside'), 'top': T('stairside'), 'bot': CAULK}))
    K.light(TREE[0], TREE[1], 1050, 500, '1 0.9 0.7')
    return chs


# ================================================================================================ scenery, cover, lamps
def scenery():
    for (x, y, a) in ((-260, -900, 0), (260, -900, 0), (-260, -1500, 0), (260, -1500, 0), (180, 700, 0), (-180, 700, 0),
                      (750, 160, 0), (1000, -160, 0), (-900, 330, 0), (-700, -930, 0), (-420, 1200, 0), (700, 1000, 0)):
        place('street_lamp', x, y, 0, a)
        K.light(x, y, 240, 200, '1 0.82 0.5')
    for (x, y) in ((-1850, 850), (-1900, -700), (1900, 700), (1950, -400), (-1000, 1800), (1000, 1850), (-1650, -1200), (1750, -1050),
                   (220, -1700), (-450, -1850), (900, 600), (-880, -520), (550, -500), (-300, 1500), (1850, 1200), (-1450, 600)):
        if r_of(x, y) < RUSE: place('pine', x, y, 0, (x * 13) % 360)
    for (x, y, a) in ((-600, 650, 30), (650, 600, 120), (-650, -650, 200), (650, -650, 300), (0, -1200, 0), (-700, 1750, 90)):
        place('crate_stack', x, y, 0, a)
    place('sleigh', 260, -620, 0, 40)
    place('sleigh', -800, 760, 0, 130)
    for (x, y, s) in ((-300, -1700, 1), (300, 1300, 2), (1700, 500, 3), (-1100, 600, 1), (1200, -400, 2), (-800, -1700, 3)):
        deco(f'snow_drift{s}', x, y, 0, (x + y) % 360)


def items(base, cap_top, hut, cabin, bakery):
    K.weapon('imperius', 0, 1020, TOWER_H, marker='purple')
    K.weapon('balloony', SNOWMAN[0], SNOWMAN[1], HILL_Z + 668, marker='orange')
    K.weapon('betty', MILL[0], MILL[1] - 20, cap_top, marker='black')
    K.weapon('pumper', -1000, 1240, 192, marker='green')
    K.weapon('splasher', POND[0], HOLE[3] - 30, HOLE_Z, marker='blue')
    K.weapon('boaster', 1000, -1150, 0, marker='orange')
    K.weapon('bubbleg', 0, -420, 0, marker='green')
    ammo = {'imperius': [(MILL[0] - 200, 0, base.roof_top), (-1600, 0, HILL_Z), (0, 1450, 4), (-60, -2090, 32)],
            'balloony': [(0, 0, BAND_ROOF + 16), (-1500, 300, HILL_Z), (1150, 1050, 0), (1900, -900, 0)],
            'betty': [(MILL[0], 200, base.roof_top), (-960, 1300, 196), (0, 1650, 4), (-2050, 600, 0)],
            'pumper': [(-1100, -1150, 192), (1250, -1440, 4), (-560, 1000, 0), (200, 1100, 0), (1700, -100, 0)],
            'splasher': [(POND[0] + 300, POND[1] - 100, 0), (-1600, -750, 4), (1300, 0, 4), (-200, -1100, 0)],
            'boaster': [(1550, -850, 4), (600, -1400, 4), (0, 600, 0), (-560, -320, 0)],
            'bubbleg': [(420, 120, 0), (-420, -120, 0), (-1200, -1520, 4), (100, -2090, 32), (-1050, 1000, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((300, 900), (-900, -300), (900, -1800)): K.ammo('nipper', x, y, 0)
    K.item('item_armor_padshield', 0, 0, BAND_ROOF + 16)
    K.item('item_speedy', 300, 300, 0)
    K.item('holdable_floater', -1500, -150, HILL_Z)
    K.item('item_armor_shard', 1300, 200, base.roof_top)
    K.item('item_armor_shard', -1800, 350, HILL_Z)
    K.station(-700, -400, 0, ang=0); K.station(700, 450, 0, ang=180); K.station(-300, 1900, 0, ang=270)
    for (x, y, a) in ((0, -1800, 90), (-800, -1850, 60), (800, -1500, 120), (-500, -500, 45), (500, -350, 135), (-1500, -400, 30),
                      (1000, 400, 200), (-800, 450, 0), (700, 1250, 270), (-300, 1150, 300), (1900, 300, 180), (-2050, -450, 0),
                      (-1550, -1500, 45), (1300, -1800, 120), (0, 2050, 270), (1500, 1650, 225)):
        K.spawn(x, y, 0, a)


def music_box():
    """the secret: the snow globe's own wind-up music box, a sealed velvet-lined room under the snow"""
    x, y, z = VAULT
    w, h = 360, 330
    V = T('velvet'); B = T('brasswall')
    K.add(box((x - w - 16, y - w - 16, z - 16), (x + w + 16, y + w + 16, z), tex6(top=B), detail=False),
          box((x - w - 16, y - w - 16, z + h), (x + w + 16, y + w + 16, z + h + 16), tex6(bot=V), detail=False),
          box((x - w - 16, y - w, z), (x - w, y + w, z + h), tex6(e=V), detail=False),
          box((x + w, y - w, z), (x + w + 16, y + w, z + h), tex6(w=V), detail=False),
          box((x - w - 16, y - w - 16, z), (x + w + 16, y - w, z + h), tex6(n=V), detail=False),
          box((x - w - 16, y + w, z), (x + w + 16, y + w + 16, z + h), tex6(s=V), detail=False))
    place('music_frame', x, y + 80, z, 0)
    K.add(box((x - 210, y + 80 - 100, z + 20), (x + 210, y + 80 + 100, z + 250), WCLIP))
    K.rotating_model2(ML.PLACE['music_drum'][0], (x, y + 80, z + 150), 18, axis='x')
    K.add(box((x + 236, y + 80 - 112, z + 20), (x + 268, y + 80 + 112, z + 264), WCLIP))
    K.rotating_model2(ML.PLACE['music_gear'][0], (x + 252, y + 80, z + 150), 30, axis='x', reverse=True)
    K.item('item_padpower', x - 250, y - 120, z); K.item('item_revival', x + 250, y - 120, z); K.item('holdable_killerducks', x, y - 140, z)
    K.teleporter((x - 40, y - w + 8, z), (x + 40, y - w + 64, z + 96), dest=(0, 800, 0), angle=270, name='musicbox_exit')
    K.light(x, y, z + 280, 500, '1 0.8 0.6'); K.light(x, y - 200, z + 100, 200, '1 0.6 0.8')
    K.speaker(x, y + 80, z + 200, 'misc/wind_chimes')


def lights():
    K.light_grid(-2000, -2000, 2000, 2000, 1500, 800, 2600, color='0.85 0.9 1', skip=lambda x, y: r_of(x, y) > 2100)
    K.timer_sound(0, 0, 900, 'animal/bird_owl1', 'owl', 40, 20)


def shader():
    TX.write_shader(extra=[SH.sky('env/pf-garden512', sun=(90, 30), sun_rgb=(0.6, 0.7, 1.0), sun_int=30, skylight=(25, 3))],
                    arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


def models():
    GM.mats(); building_mats()
    GM.glass_dome(SPH_R, SPH_CZ); GM.snowfall(); GM.plinth(RF, DESK)
    GM.giant_mug(); GM.book_stack(); GM.giant_pencil(3600); GM.desk_lamp(); GM.window_frame(5400, 4880)
    GM.bandstand(BAND_R, 32, BAND_ROOF, 212)
    GM.tower_dress(TOWER[2] - TOWER[0], TOWER_H); GM.pew(); GM.organ(); GM.altar(); GM.gravestone(0); GM.gravestone(1)
    GM.mill_tower(); GM.mill_cap(); GM.mill_sails()
    GM.snowman([(130, 0, 260), (95, 260, 440), (66, 440, 570), (110, 570, 578), (70, 578, 668)])
    GM.xmas_tree(); GM.pine(); GM.street_lamp(); GM.bench(); GM.sleigh(); GM.woodpile(); GM.presents_pile(); GM.crate_stack()
    for s in (1, 2, 3): GM.snow_drift(90 + 20 * s, 12, s)
    GM.market_dress(300, 220, 176); GM.market_dress(300, 250, 176)
    GM.sled_pad(); GM.ski_pad(); GM.curling_pad(); GM.flour_pad()
    for k in range(4): GM.present_pad(k=k)
    GM.music_drum(); GM.music_gear(); GM.music_frame()


if __name__ == '__main__':
    textures()
    models()
    room(); snow_ground(); glass()
    rink(); nave = chapel(); base, cap_top = windmill(); sledging_hill(); hut = fishing_pond(); cabin = log_cabin()
    bs = village(); st, TR = station(); chs = market(); scenery(); music_box()
    items(base, cap_top, hut, cabin, bs[0]); lights()
    K.fix_items()
    TR.sweep_check()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
