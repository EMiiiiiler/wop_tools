#!/usr/bin/env python3
"""Padman's Little Cake Shop (wop_padcakeshop) - FFA in a small pastel cake shop, built on woplib + texlib.

    OUT=<dir> python3 build_padcakeshop.py          (wopbuild.py padcakeshop preview / all)

Padman scale (~8u per cm, catalog models at 1.0). Shop x -1920..1920, y -1536..1536, floor 0, ceiling 1792; the
pavement outside the south wall y -2112..-1600 under an open sky. x east, y north (the back wall).
Levels: floor 0 | display unit shelves 96 / 400 / 704 / 1008 | window display 520 | table 600 | counter 720 |
bread rack 400 / 800 / 1200 | wall shelves 944 / 1360 | espresso machine top 1160 | awning 1352 | cupcake stand 1408.
See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, hull, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import ck_models as CM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, YP, X1, Y1 = INFO['bounds']                 # playable: the shop plus the pavement
YS, YW = -1536, -1600                           # south wall: inner face, outer face
YR = -2560                                      # far side of the road (sky)
ZC, ZSKY = 1792, 2048
K = MapKit(MAP, NS, LONG, (X0, YP, X1, Y1), worldspawn={'_ambient': '60', '_color': '1 0.96 0.92'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
UNIT = (0, 640)                                 # display unit x -800..800, y 360..920
UZ = CM.UNIT_Z
COUNTER = (-1300, 300)                          # x -1500..-1100, y -500..1100, top 720
CZ = CM.COUNTER_H
ESP = (-1300, 50)                               # espresso machine on the counter, top deck CZ + 440
EZ = CZ + CM.ESP_H
RACK = (1912, 400)                              # bread rack x 1592..1912, y -300..1100
RZ = CM.RACK_Z
SHELF_LO, SHELF_HI = 944, 1360                  # north wall shelves (low: x +-1700, y 1216..; high: x -1700..300, y 1336..)
JAR = (440, 1400)                               # the cookie jar on the low shelf, below the east end of the high shelf
WIN = (-1200, 640, 520, 1300)                   # shop window x0 x1 z0 z1
SILL_Y = -1096                                  # window display x -1600..640, y -1536..-1096, top 520
DOOR = (960, 1680, CM.DOOR_H)                   # door opening x0 x1 top
TABLE = (-250, -640)
AWN = (-480, 1352)                              # awning centre x, walkable top
TIER = (-530, 660)                              # tiered cupcake stand on the unit top
TIER_TOP = UZ[3] + CM.TIER_Z[2]
VAULT = (-448, -448, 448, 448); VAULT_Z = -1280


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = CM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def clip_ring(cx, cy, r0, r1, z0, z1, n=10):
    """hollow cylinder wall as weapclip segments (a jar you can fall into)"""
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pts = [(cx + r * math.cos(a), cy + r * math.sin(a), z) for r in (r0, r1) for a in (a0, a1) for z in (z0, z1)]
        K.add(hull(pts, WCLIP, round_pts=False))
    K.occupy_r(cx, cy, r1, z0, z1)


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: the shop (floor, three walls, ceiling), the south wall with the window and the open door,
    and the pavement + road under a sky box. Everything else is detail."""
    S = T('sky')
    K.add(box((X0 - 32, YS, -32), (X1 + 32, Y1 + 32, 0), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YW, -32), (X1 + 32, YS, 0), {'top': T('pine'), 'side': CAULK, 'bot': CAULK}, detail=False))      # threshold
    K.add(box((X0 - 32, YP, -32), (X1 + 32, YW, 0), {'top': T('pavement'), 'side': T('kerb'), 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YR - 32, -32), (X1 + 32, YP, 0), {'top': T('road'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0, YP, 0), (X1, YP + 24, 8), T('kerb')))
    K.add(box((X0 - 32, YS, 0), (X0, Y1 + 32, ZC), tex6(e=T('wall')), detail=False))
    K.add(box((X1, YS, 0), (X1 + 32, Y1 + 32, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZC), tex6(s=T('wall')), detail=False))
    K.add(box((X0 - 32, YS, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # sky box round the pavement and the road
    K.add(box((X0 - 32, YR - 32, 0), (X0, YW, ZSKY), tex6(e=S), detail=False), box((X1, YR - 32, 0), (X1 + 32, YW, ZSKY), tex6(w=S), detail=False),
          box((X0, YR - 32, 0), (X1, YR, ZSKY), tex6(n=S), detail=False),
          box((X0 - 32, YR - 32, ZSKY), (X1 + 32, YS, ZSKY + 32), tex6(bot=S), detail=False))
    # south wall round the window and the door (inside: wall, outside: painted boards, jambs white)
    wx0, wx1, wz0, wz1 = WIN; dx0, dx1, dz = DOOR
    sw = lambda mn, mx, **j: K.add(box(mn, mx, tex6(n=T('wall'), s=T('facade'), **j), detail=False))
    sw((X0 - 32, YW, 0), (wx0, YS, ZSKY), e=T('white')); sw((wx1, YW, 0), (dx0, YS, ZSKY), e=T('white'), w=T('white'))
    sw((dx1, YW, 0), (X1 + 32, YS, ZSKY), w=T('white'))
    sw((wx0, YW, 0), (wx1, YS, wz0), top=T('white')); sw((wx0, YW, wz1), (wx1, YS, ZSKY), bot=T('white'))
    sw((dx0, YW, dz), (dx1, YS, ZSKY), bot=T('white'))
    m1, m2 = wx0 + (wx1 - wx0) / 3, wx0 + 2 * (wx1 - wx0) / 3
    for a, b in ((wx0, m1 - 14), (m1 + 14, m2 - 14), (m2 + 14, wx1)): K.add(box((a, YW + 28, wz0), (b, YW + 36, wz1), T('glass')))
    for x in (m1, m2):
        K.add(box((x - 14, YW + 20, wz0), (x + 14, YW + 44, wz1), T('white')))
    K.reserve(((wx0, YW, wz0), (wx1, YS, wz1)))
    # players stay on the pavement (the road is scenery)
    K.add(box((X0, YP - 16, 0), (X1, YP, ZSKY), CLIP))
    # window display cabinet
    K.add(box((wx0, YS, 0), (wx1, SILL_Y, wz0), tex6(top=T('pine'), n=T('beadboard'), e=T('beadboard'), w=T('beadboard'))))
    K.reserve(((wx0, YS, 0), (wx1, SILL_Y, wz0)))
    # white boarding to 640 with a rail, round the room
    def wains(mn, mx, face):
        K.add(box(mn, mx, tex6(**{face: T('beadboard'), 'top': T('rail'), 'e' if face in 'ns' else 'n': T('rail'), 'w' if face in 'ns' else 's': T('rail')})))
    wains((X0, Y1 - 8, 0), (X1, Y1, 640), 's'); wains((X0, YS + 8, 0), (X0 + 8, Y1 - 8, 640), 'e'); wains((X1 - 8, YS + 8, 0), (X1, Y1 - 8, 640), 'w')
    for a, b in ((X0, wx0), (wx1, dx0), (dx1, X1)): wains((a, YS, 0), (b, YS + 8, 640), 'n')
    # doormat, menu board, pictures, shop sign
    K.add(box((dx0 + 110, YS + 40, 0), (dx1 - 110, YS + 290, 3), {'top': T('doormat'), 'side': T('doormat'), 'bot': CAULK}))
    mx0, mx1, my0, my1 = dx0 + 110, dx1 - 110, YS + 40, YS + 290
    for fc in K.M.world[-1].faces:
        if fc.n[2] > 0.9:
            fc.sc = ((mx1 - mx0) / 512, (my1 - my0) / 256); fc.off = ((-mx0 / fc.sc[0]) % 512, (my1 / fc.sc[1]) % 256)
    K.add(sign_box((X0 + 8, 60, 860), (X0 + 14, 660, 1460), T('menu'), 512, 512, facing='e', edge=T('pine')))
    for i, (x, z) in enumerate(((560, 1080), (900, 1080), (1240, 1080))):
        K.add(sign_box((x, Y1 - 6, z), (x + 256, Y1, z + 320), T(f'frame{i}'), 256, 320, facing='s', edge=T('pine')))
    K.add(sign_box((-1500, YW - 8, 1440), (548, YW, 1696), T('shopsign'), 1024, 128, facing='s', edge=T('white')))
    K.keep_clear(dx0 - 40, YW - 220, dx1 + 40, YS + 300, 0)                       # the doorway, both sides


def vault():
    """the secret: inside the cookie jar (a sealed room below the world) - Pad Power, Revival, Killer Ducks, shield"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 416
    ck, dg, gl = T('cookie'), T('dough'), T('sugar')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': ck, 'side': CAULK, 'bot': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': gl, 'side': CAULK, 'top': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=dg), detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=dg), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=dg), detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=dg), detail=False))
    for (x, y, k) in ((-260, 220, 'cream'), (250, 240, 'pink'), (-280, -230, 'choc'), (290, -200, 'mint')):
        place('cupcake_' + k, x, y, z)
    place('boxes_s', 0, 300, z)
    K.item('item_padpower', 0, 60, z); K.item('item_revival', -200, 0, z); K.item('holdable_killerducks', 200, 0, z)
    K.item('item_armor_padshield', 0, -160, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(150, -1000, 0), angle=90, name='vault_exit')
    K.light(0, 0, z + 330, 700, '1 0.92 0.8'); K.light(-280, 0, z + 180, 250, '1 0.8 0.7'); K.light(280, 0, z + 180, 250, '1 0.8 0.7')


# ------------------------------------------------------------------------------------------------ the shop
def display():
    """the pine display unit from the photo, dressed shelf by shelf, and the ways up"""
    ux, uy = UNIT
    place('display_unit', ux, uy, 0)
    for x, n in ((-500, 'cake_pink'), (0, 'cake_green'), (500, 'cake_brown')): place(n, x, uy, UZ[0])
    for x, n in ((-480, 'tray_mousse'), (0, 'tray_slices'), (480, 'tray_hearts')): place(n, x, uy, UZ[1])
    for x, n in ((-480, 'tray_cup_a'), (0, 'tray_cup_b'), (480, 'tray_cup_c')): place(n, x, uy, UZ[2])
    place('tier_stand', *TIER, UZ[3])
    place('lace_stand', 300, 700, UZ[3])
    place('vase_pops', 590, 800, UZ[3]); place('vase_bears', 720, 690, UZ[3])
    place('tray_cream', 610, 470, UZ[3])
    # sugar-cube steps to the bottom shelf
    K.stairs16(300, 168, 460, 360, 0, UZ[0], 'n', {'top': T('sugar'), 'side': T('sugar'), 'bot': CAULK}, route='unit_steps')
    K.keep_clear(260, 60, 500, 168, 0)
    # cake boxes behind the unit: their tops are level with shelves 2 and 3
    place('boxes_a', 620, 1090, 0); place('boxes_b', -620, 1100, 0)
    # the bread board from the unit top down to the low wall shelf
    pts = [(x, y, z) for x in (-80, 80) for (y, z) in ((920, UZ[3]), (920, UZ[3] - 16), (1216, SHELF_LO), (1216, SHELF_LO - 16))]
    K.solid_piece('bridge', [hull(pts, T('pine'), round_pts=False)], TX.texfn('pine'))
    K.route('bridge', (0, 800, UZ[3]), (0, 1340, SHELF_LO))
    K.keep_clear(-90, 780, 90, 920, UZ[3]); K.keep_clear(-90, 1216, 90, 1360, SHELF_LO)


def counter_side():
    cx, cy = COUNTER
    place('counter', cx, cy, 0)
    place('espresso', *ESP, CZ)
    place('cash_register', cx, 500, CZ)
    # the cakes live here, out of the sun: a row of cupcakes and the tiered cake at the north end
    place('cupcake_pink', cx - 120, 705, CZ); place('cupcake_mint', cx, 705, CZ); place('cupcake_cream', cx + 120, 705, CZ)
    place('counter_cake', cx, 932, CZ)
    K.catalog('pad_cups/pad_cup02.md3', ESP[0] + 100, ESP[1] - 120, CZ + 60, angle=0, nudge=False, clip=False)     # under the pour
    K.catalog('pad_cups/pad_cup03_upd.md3', ESP[0] - 100, ESP[1] + 200, EZ, angle=30, nudge=False)
    K.catalog('pad_cups/pad_cup05_upd.md3', ESP[0] - 100, ESP[1] - 200, EZ, angle=120, nudge=False)
    # an open sack of coffee beans against the south end of the counter; the pad beside it is the way up (pads())
    place('coffee_sack', -1370, -620, 0)
    # staff side: things in the cubbies (walk in from the aisle)
    K.keep_clear(-1640, -480, -1500, 1080, 0)
    place('flour_sacks', -1310, 300, 16, angle=90)
    K.catalog('pad_plates/plate_hpstack2.md3', -1300, -200, 352, nudge=False)
    K.catalog('pad_plates/plate_hpstack1_hs.md3', -1300, 180, 352, nudge=False)
    K.catalog('pad_ddmix/diner/coffe_pot.md3', -1300, 420, 352, angle=200, nudge=False)
    place('boxes_s', -1320, 880, 352)
    place('flour_sacks', -1760, 1380, 0, angle=10)
    K.catalog('pad_tins/pad_milk_tbs.md3', -1560, 1440, 0)
    K.route('cubby', (-1700, 300, 0), (-1330, 760, 16))


def customers():
    tx, ty = TABLE
    place('bistro_table', tx, ty, 0)
    place('bistro_chair', tx - 470, ty, 0, angle=0); place('bistro_chair', tx + 470, ty, 0, angle=180)
    place('coffee_cup', tx - 130, ty + 60, CM.TABLE_Z, angle=40)
    place('croissant_plate', tx + 130, ty + 90, CM.TABLE_Z, angle=200)
    K.catalog('pad_cutlery/pad_teaspoon.md3', tx - 60, ty - 80, CM.TABLE_Z, angle=30, nudge=False, clip=False)
    K.catalog('pad_cake/pad_cakeslice.md3', tx + 30, ty - 30, CM.TABLE_Z, angle=70, nudge=False, clip=False)
    # window display
    place('planter', -700, -1316, WIN[2])                    # nothing that melts in the window: flowers, bread, boxes, tea
    place('boxes_s', -1080, -1400, WIN[2])
    place('bread_basket', -290, -1390, WIN[2])
    place('teapot', 0, -1410, WIN[2], angle=120)
    K.catalog('pad_ddmix/plants/tulip1.md3', 560, -1440, WIN[2], angle=0, nudge=False)
    K.catalog('pad_cake/pad_cakestand.md3', 250, -1420, WIN[2], angle=0, nudge=False)
    # door, bread wall
    place('shop_door', DOOR[1], YS + 8, 0)
    rx, ry = RACK
    place('bread_rack', rx, ry, 0)
    place('bread_basket', 1752, -100, RZ[0], angle=90); place('baguette_bin', 1760, 960, RZ[0])
    place('tin_loaves', 1752, 0, RZ[1], angle=90); place('bread_basket', 1752, 900, RZ[1], angle=90)
    place('baguette_bin', 1760, -170, RZ[2]); place('tin_loaves', 1752, 870, RZ[2], angle=90)
    # floor cover
    place('planter', 800, -1370, 0)
    place('flour_sacks', 1300, 1380, 0, angle=160)
    place('boxes_s', 850, -260, 0, angle=20)
    # nothing edible on the floor: sacks, churns and plants are the cover
    place('sugar_sack', 560, -80, 0, angle=30); place('milk_churn', -640, 60, 0)
    place('coffee_sack', 1450, -520, 0, angle=80)
    place('boxes_s', -900, 170, 0, angle=70)
    K.catalog('pad_ddmix/plants/bonsai.md3', 300, -1050, 0)
    place('sugar_sack', -720, -170, 0, angle=100)


def north_wall():
    place('shelf_low', 0, Y1, SHELF_LO); place('shelf_high', -700, Y1, SHELF_HI)
    z = SHELF_LO
    for x, n in ((-1560, 'jar_a'), (-1380, 'jar_b'), (-1150, 'tin_flour'), (-960, 'tin_sugar'), (905, 'tin_tea'), (1400, 'jar_c'), (1560, 'jar_a')):
        place(n, x, 1430, z)
    place('teapot', -640, 1410, z, angle=250)
    place('cone_holder', 60, 1450, z)
    place('jar_lid', 690, 1400, z)
    K.catalog('pad_cups/pad_cup06.md3', 1690, 1440, z, angle=200, nudge=False)
    z = SHELF_HI
    for x, n in ((-1600, 'jar_c'), (-1000, 'jar_b'), (-420, 'tin_tea')): place(n, x, 1456, z)
    K.catalog('pad_books/pad_cb_ur_lg.md3', -760, 1470, z, angle=0, nudge=False)
    K.catalog('pad_ddmix/diner/coffe_pot.md3', -150, 1460, z, angle=160, nudge=False)
    # the cookie jar: only open from above (walk off the east end of the high shelf)
    jx, jy = JAR; zj = SHELF_LO
    K.custom(ML.PLACE['cookie_jar'], jx, jy, zj)
    K.add(wopmap.cyl(jx, jy, CM.JAR_R, zj, zj + CM.JAR_FILL, WCLIP, 12))
    clip_ring(jx, jy, CM.JAR_R - 14, CM.JAR_R, zj + CM.JAR_FILL, zj + CM.JAR_H)
    K.secret((jx - 64, jy - 64, zj + CM.JAR_FILL + 2), (jx + 64, jy + 64, zj + CM.JAR_FILL + 110), dest=(0, 150, VAULT_Z), angle=270, name='jar')


def outside():
    ax, az = AWN
    place('awning', ax, YW, az)
    place('bench', -900, YW - 130, 0)
    place('planter', 800, YW - 170, 0); place('planter', 1740, YW - 170, 0); place('planter', -1700, YW - 170, 0)
    place('a_board', 330, -1960, 0)
    K.catalog('pad_ddmix/plants/flower_yellow.md3', -1380, -1960, 0, scale=0.8)
    for x in (-1100, 0, 1100):
        place('pendant', x, -250, ZC, lit=False, occupy=False)
    place('pendant', -1700, 300, ZC, lit=False, occupy=False)
    place('bunting', 0, -900, 1700, lit=False, occupy=False); place('bunting', 0, 200, 1740, lit=False, occupy=False)


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    ux, uy = UNIT
    J = K.jumppad
    J(-160, 80, 0, land=(-160, 520, UZ[3]), apex=UZ[3] + 230, name='pad_unit', edges=[(-160, 360, UZ[3])])
    J(-1000, 1180, 0, land=(-650, 1090, UZ[2]), apex=UZ[2] + 170, name='pad_boxes_b', edges=[(-800, 1110, UZ[2])], ceiling=SHELF_LO - 24)
    J(1000, 1170, 0, land=(660, 1090, UZ[1]), apex=UZ[1] + 170, name='pad_boxes_a', edges=[(790, 1100, UZ[1])])
    J(-560, 1200, UZ[2], land=(-240, 800, UZ[3]), apex=UZ[3] + 200, name='pad_boxes_top', edges=[(-330, 920, UZ[3])])
    J(-190, 660, UZ[3], land=(TIER[0], TIER[1], TIER_TOP), apex=TIER_TOP + 150, name='pad_tier', ceiling=ZC,
      edges=[(TIER[0] + CM.TIER_R[2], TIER[1], TIER_TOP)])
    J(-860, -380, 0, land=(-1290, -380, CZ), apex=CZ + 220, name='pad_counter', edges=[(-1084, -380, CZ)])
    J(-1380, -900, 0, land=(-1400, -390, CZ), apex=CZ + 230, name='pad_sack', edges=[(-1390, -500, CZ)])
    J(-1150, -440, CZ, land=(ESP[0] - 20, ESP[1], EZ), apex=EZ + 190, name='pad_espresso', edges=[(ESP[0], ESP[1] - 280, EZ + 40)])
    # second way onto the espresso machine from the busy display-unit top (bots never took the counter pads to it)
    J(-740, 394, UZ[3], land=(ESP[0] - 20, ESP[1] - 40, EZ), apex=EZ + 260, name='pad_unit_esp', ceiling=ZC,
      edges=[(ESP[0] + 124, ESP[1] + 120, EZ + 176), (ESP[0] + 170, ESP[1] + 40, EZ)])
    # the high wall shelf (Betty, the cookie-jar secret) straight from the busy unit top
    J(160, 860, UZ[3], land=(150, 1440, SHELF_HI), apex=SHELF_HI + 200, name='pad_unit_shelf', ceiling=ZC,
      edges=[(150, 1336, SHELF_HI)])
    J(1320, 700, 0, land=(1760, 620, RZ[0]), apex=RZ[0] + 190, name='pad_rack1', edges=[(1592, 630, RZ[0])], ceiling=RZ[1] - 24)
    J(1250, 290, 0, land=(1760, 290, RZ[1]), apex=RZ[1] + 200, name='pad_rack2', edges=[(1592, 290, RZ[1])], ceiling=RZ[2] - 24)
    J(1100, 560, 0, land=(1760, 480, RZ[2]), apex=RZ[2] + 220, name='pad_rack3', edges=[(1592, 490, RZ[2] + 40)], ceiling=ZC)
    J(1200, 1040, 0, land=(1200, 1370, SHELF_LO), apex=SHELF_LO + 270, name='pad_shelf', edges=[(1200, 1216, SHELF_LO)])
    J(-250, 1256, SHELF_LO, land=(-250, 1450, SHELF_HI), apex=SHELF_HI + 260, name='pad_shelf_hi', ceiling=ZC, edges=[(-250, 1336, SHELF_HI)])
    J(-1000, -760, 0, land=(-1090, -1190, WIN[2]), apex=WIN[2] + 200, name='pad_window', edges=[(-1070, SILL_Y, WIN[2])])
    J(-520, -1010, 0, land=(TABLE[0], TABLE[1] - 160, CM.TABLE_Z), apex=CM.TABLE_Z + 200, name='pad_table',
      edges=[(-370, -900, CM.TABLE_Z)])
    J(-150, -2040, 0, land=(-150, YW - 120, AWN[1]), apex=AWN[1] + 200, name='pad_awning', edges=[(-150, YW - CM.AWN_D, AWN[1])], ceiling=ZSKY)


def items():
    W, A = K.weapon, K.ammo
    W('imperius', TIER[0], TIER[1], TIER_TOP, marker='purple')
    W('betty', -40, 1440, SHELF_HI, marker='black')
    W('balloony', ESP[0] - 30, ESP[1] + 120, EZ, marker='orange')
    W('pumper', 1752, 160, RZ[2], marker='green')
    W('splasher', AWN[0], YW - 120, AWN[1], marker='blue')
    W('boaster', TABLE[0] + 20, TABLE[1] - 200, CM.TABLE_Z, marker='orange')
    W('bubbleg', 150, -200, 0, marker='green')
    ammo = {'imperius': [(-230, 480, UZ[3]), (-760, 640, UZ[2]), (1650, 1290, SHELF_LO), (1830, -1200, 0)],
            'betty': [(-1450, 1440, SHELF_HI), (-760, 640, UZ[0]), (-1330, -330, 16), (1100, -2000, 0)],
            'balloony': [(-1300, -420, CZ), (ESP[0] + 100, ESP[1] + 120, CZ + 60), (-1700, -900, 0), (760, 640, UZ[2])],
            'pumper': [(1752, 420, RZ[1]), (1752, 250, RZ[0]), (1450, -100, 0), (300, 1300, 0)],
            'splasher': [(600, YW - 120, AWN[1]), (-1280, -2044, 0), (300, -1250, WIN[2]), (-300, -1900, 0)],
            'boaster': [(-900, -1000, 0), (240, 640, UZ[0]), (600, -700, 0), (-1750, 600, 0)],
            'bubbleg': [(-400, 150, 0), (1000, 300, 0), (-250, 640, UZ[1]), (240, 640, UZ[2])]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: A(w, x, y, z)
    A('nipper', 60, -1180, WIN[2]); A('nipper', 900, 700, 0); A('nipper', -1750, 0, 0)
    K.item('item_armor_padshield', 760, 640, UZ[1])
    K.item('item_armor_shard', -250, 1450, SHELF_LO); K.item('item_armor_shard', 1752, 560, RZ[1]); K.item('item_armor_shard', -480, -1230, WIN[2])
    K.item('item_speedy', 480, -1300, WIN[2])
    K.item('item_jumper', 1752, 620, RZ[2])
    K.item('holdable_floater', -1330, 760, 16)
    K.item('item_visionless', 1820, -900, 0)
    K.station(1760, 1330, 0, ang=225)
    for (x, y, z, a) in ((-600, -1200, 0, 90), (500, -1000, 0, 135), (1300, -1200, 0, 135), (1400, 0, 0, 180), (-900, -100, 0, 0),
                         (-400, 220, 0, 270), (500, 200, 0, 270), (-1750, -300, 0, 45), (-1750, 900, 0, 315), (900, 1400, 0, 180),
                         (-300, 1400, 0, 0), (0, 560, UZ[3], 270), (-1300, -1900, 0, 45), (1500, -1850, 0, 135),
                         (1100, -400, 0, 180)):
        K.spawn(x, y, z, a)


def lights_sounds():
    # 2000 at 1560 with _ambient 60: floor median ~100, soft shop light (6200 washed out every top within 600u of the ceiling grid: counter, unit top, shelves)
    K.light_grid(X0, YS, X1, Y1, 1560, 768, 2000, color='1 0.95 0.88')
    for x in (-1100, 0, 1100): K.light(x, -250, 1440, 300 if x < 0 else 450, '1 0.92 0.8')   # west lamp is 400u from the chrome espresso deck (blown out at 900)
    for z in UZ[:3]:                                             # under each display shelf
        for x in (-420, 420): K.light(x, UNIT[1], z + 190, 240, '1 0.94 0.84')
    for y in (-230, 300, 830): K.light(-1340, y, 200, 220, '1 0.92 0.8')          # counter cubbies
    for x in (-1200, -400, 400, 1200): K.light(x, 1380, 600, 420, '1 0.94 0.86')  # under the low wall shelf
    for z in RZ[:2]:
        for y in (50, 750): K.light(1740, y, z + 220, 260, '1 0.92 0.8')
    K.light(-1320, 50, CZ + 200, 200, '1 0.9 0.75')                               # under the group heads
    K.light(1800, -1150, 400, 300, '1 0.95 0.85')                                  # behind the door
    K.speaker(ESP[0], ESP[1], CZ + 300, 'ambient/slime_bubbling')
    K.speaker(0, 1500, 1200, 'machine/clock_ticking')
    K.speaker(0, -1900, 400, 'animal/blackbird')
    K.timer_sound(-900, YW - 200, 300, 'misc/bicycle_bell', 'bike', 40, 20)
    K.timer_sound(1320, 900, 200, 'animal/kitten_meow', 'cat', 50, 25)
    K.trigger_sound((DOOR[0], YW, 0), (DOOR[1], YS, 200), 'machine/dingdong', 'doorbell', wait=3)
    K.trigger_sound((TIER[0] - 60, TIER[1] - 60, TIER_TOP), (TIER[0] + 60, TIER[1] + 60, TIER_TOP + 80), 'human/applause', 'summit', wait=8)


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = CM.textures(K)
    CM.all_models()                    # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); vault(); display(); counter_side(); north_wall(); pads(); customers(); outside(); items(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
