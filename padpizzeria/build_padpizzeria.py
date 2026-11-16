#!/usr/bin/env python3
"""Padman's Pizza Joint (wop_padpizzeria) - FFA in a 90s New York slice shop, built on woplib + texlib.

    OUT=<dir> python3 build_padpizzeria.py          (wopbuild.py padpizzeria preview / all)

Toy scale (~5u per cm, Padman ~11 cm). x east, y north (front window south, counter + kitchen north).
Dining room x -1600..1600, y -1960..2050, kitchen y 2082..3100, sidewalk y -2700..-1992; floor 0, ceiling 1400.
Levels: floor 0 | booth seat 225 | booth table 375 | kitchen counters 450 | counter 525 | booth backs 560 |
ATM 760 | oven top 850 | menu shelf 900 | cooler top 1000 | awning 1280. See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, hull, cyl, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import pz_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, YP, X1, YK = INFO['bounds']                 # playable: sidewalk .. kitchen back wall
YF, YFO = -1960, -1992                          # front wall: inner face, outer face
YB0, YB1 = 2930, 2962                           # back wall (counter side / kitchen side)
YR = -3300                                      # far side of the road (sky)
ZC, ZSKY = 1400, 2200
K = MapKit(MAP, NS, LONG, (X0, YP, X1, YK), worldspawn={'_ambient': '40', '_color': '1 0.95 0.88'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
WIN_W, WIN_E = (-820, -300), (300, 820)         # shop window panes x0 x1 either side of the door
WZ = (200, 1100)
DOOR = (-250, 250, 1100)                        # front door x0 x1 top (on the aisle)
KDOOR = (-860, -520, 1100)                      # kitchen door in the back wall
ROW_YC = {'end_s': -1920, 'd1': -1040, 'd2': -160, 'd3': 720, 'end_n': 1600}
TABLES = (-1480, -600, 280, 1160)               # booth table centres (y)
AISLE = 320                                     # booth rows end at x = +-320: one 640u aisle
ROW_N = 1640                                    # rows end here
PILLAR = (-600, 1780, -350, 2030)
COUNTER = (-400, 2180)                          # counter origin: x -400..400 (+ round end to -565), y 2180..2510
CZ = PM.COUNTER_Z
BACKC = (-480, 2730, X1, YB0)                   # back counter, top CZ
SHELF = (-100, -100 + PM.SHELF_L, 900)          # menu shelf x0 x1 top (y YB0-260..YB0)
SHELF_Y0 = YB0 - 260
COOLER = (580, 1815)                            # cooler origin (x 550..880, y 1640..1990)
ATM = (630, 2100)                               # ATM (x 570..880, y 1990..2210)
OVEN = (-30, 3380)                              # oven front-centre: x -480..420, y 3380..3980
OZ = PM.OVEN[2]
SINK = (430, 3080, X1, YK)                      # sink counter, top PM.SINK_Z
BASIN = (510, 3180, 810, 3680)
SZ, SF = PM.SINK_Z, PM.SINK_FLOOR               # rim, basin floor
WTOP = 420
STEPS = (585, 3296, 735, 3680)                  # plate stair out of the water (12 x 16u)
PREP = (-710, 3550)                             # prep table, turned along the west wall
FAN1, FAN2 = (0, -600), (0, 1000)
VAULT = (-480, -400, 480, 400); VZ = -1800


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = PM.COLL.get(name, {})
    e = K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    for h in c.get('hulls', ()):                     # convex collision outlines (rounded counter end)
        pts = [(round(x + px * ca - py * sa, 2), round(y + px * sa + py * ca, 2), z + pz) for (px, py, pz) in h]
        K.add(hull(pts, WCLIP, round_pts=False))
        K.occupy(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts),
                 min(p[2] for p in pts), max(p[2] for p in pts))
    return e


def deco(name, x, y, z, angle=0, **kw):
    """a custom MD3 with no collision (wall-mounted / overhead art)"""
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: dining room + kitchen (floor, walls, ceiling), the front wall with two window panes either side
    of the door, the back wall with the kitchen door, and the sidewalk + road under a sky box. Everything else is
    detail."""
    S = T('sky')
    K.add(box((X0 - 32, YF, -32), (X1 + 32, YB0, 0), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YB0, -32), (X1 + 32, YB1, 0), {'top': T('stone'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YB1, -32), (X1 + 32, YK + 32, 0), {'top': T('quarry'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YFO, -32), (X1 + 32, YF, 0), {'top': T('stone'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0, YP, -32), (X1, YFO, 0), {'top': T('pavement'), 'side': T('kerb'), 'bot': CAULK}, detail=False))
    K.add(box((X0, YR, -48), (X1, YP - 8, -16), {'top': T('road'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0, YP - 8, -48), (X1, YP, 0), {'top': T('kerb'), 's': T('kerb'), 'n': CAULK, 'e': CAULK, 'w': CAULK,
                                               'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, YF, 0), (X0, YB0, ZC), tex6(e=T('brick')), detail=False))
    K.add(box((X1, YF, 0), (X1 + 32, YB0, ZC), tex6(w=T('checker')), detail=False))
    K.add(box((X0 - 32, YB0, 0), (X0, YK + 32, ZC), tex6(e=T('subway')), detail=False))
    K.add(box((X1, YB0, 0), (X1 + 32, YK + 32, ZC), tex6(w=T('subway')), detail=False))
    K.add(box((X0, YK, 0), (X1, YK + 32, ZC), tex6(s=T('subway')), detail=False))
    K.add(box((X0 - 32, YF, ZC), (X1 + 32, YK + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # back wall round the kitchen door (checker on the shop side, subway in the kitchen)
    kx0, kx1, kz = KDOOR
    bw = lambda mn, mx, **j: K.add(box(mn, mx, tex6(s=T('checker'), n=T('subway'), **j), detail=False))
    bw((X0, YB0, 0), (kx0, YB1, ZC), e=T('stone')); bw((kx1, YB0, 0), (X1, YB1, ZC), w=T('stone'))
    bw((kx0, YB0, kz), (kx1, YB1, ZC), bot=T('stone'))
    # sky box round the sidewalk and the road, painted buildings across the road
    K.add(box((X0 - 32, YR - 32, -48), (X0, YFO, ZSKY), tex6(e=S), detail=False),
          box((X1, YR - 32, -48), (X1 + 32, YFO, ZSKY), tex6(w=S), detail=False),
          box((X0, YR - 32, -48), (X1, YR, ZSKY), tex6(n=S), detail=False),
          box((X0 - 32, YR - 32, ZSKY), (X1 + 32, YFO, ZSKY + 32), tex6(bot=S), detail=False))
    K.add(sign_box((X0, YR, -16), (X1, YR + 8, 1600), T('across'), 1024, 512, facing='n', edge=T('across')))
    K.add(sign_box((X0, YR + 8, -16), (X0 + 8, YP - 200, 1600), T('across'), 1024, 512, facing='e', edge=T('across')))
    K.add(sign_box((X1 - 8, YR + 8, -16), (X1, YP - 200, 1600), T('across'), 1024, 512, facing='w', edge=T('across')))
    # front wall: two window panes either side of the door (inside plaster, outside brick facade, jambs stone)
    wz0, wz1 = WZ; dx0, dx1, dz = DOOR
    fw = lambda mn, mx, **j: K.add(box(mn, mx, tex6(n=T('plaster'), s=T('facade'), **j), detail=False))
    fw((X0 - 32, YFO, 0), (WIN_W[0], YF, ZSKY), e=T('stone'))
    fw((WIN_W[1], YFO, 0), (dx0, YF, ZSKY), e=T('stone'), w=T('stone'))
    fw((dx1, YFO, 0), (WIN_E[0], YF, ZSKY), e=T('stone'), w=T('stone'))
    fw((WIN_E[1], YFO, 0), (X1 + 32, YF, ZSKY), w=T('stone'))
    for (a, b) in (WIN_W, WIN_E):
        fw((a, YFO, 0), (b, YF, wz0), top=T('stone')); fw((a, YFO, wz1), (b, YF, ZSKY), bot=T('stone'))
        m = (a + b) / 2
        for p, q in ((a, m - 12), (m + 12, b)):
            K.add(box((p, YFO + 12, wz0), (q, YFO + 20, wz1), T('glass')))
        K.add(box((m - 12, YFO + 4, wz0), (m + 12, YFO + 28, wz1), T('trim')))
        K.reserve(((a, YFO, wz0), (b, YF, wz1)))
    fw((dx0, YFO, dz), (dx1, YF, ZSKY), bot=T('stone'))
    K.add(box((X0, YP - 16, 0), (X1, YP, ZSKY), CLIP))                 # players stay on the sidewalk
    K.keep_clear(dx0 - 50, YP + 10, dx1 + 50, YF + 260, 0)              # the doorway, both sides
    K.keep_clear(kx0 - 20, YB0 - 220, kx1 + 40, YB1 + 220, 0)           # the kitchen door, both sides


def walls():
    """wall dressing: smiley mural in a brick arch (west), paintings + flags (east), menu board, pillar, panels"""
    cy = ROW_YC['d2']
    hw = PM.ARCH_W / 2 + PM.ARCH_T
    K.add(sign_box((X0, cy - hw, 560), (X0 + 2, cy + hw, 1340), T('mural'), 512, 512, facing='e', edge=T('brick')))
    deco('arch', X0 + 2, cy, 560)
    for i, y in enumerate(TABLES):
        K.add(sign_box((X1 - 4, y - 150, 760), (X1, y + 150, 1140), T(f'paint{i % 2}'), 256, 320, facing='w', edge=T('trim')))
        deco('frame_a', X1 - 4, y, 760, angle=180)
    deco('flag_us', X1, 1660, 1000, angle=180, lit=False); deco('flag_it', X1, 1780, 1000, angle=180, lit=False)
    sx0, sx1, sz = SHELF
    K.add(sign_box((sx0, YB0 - 6, 1050), (sx1, YB0, 1290), T('menu'), 1024, 256, facing='s', edge=T('trim')))
    K.add(sign_box((-460, YB0 - 6, 1100), (-180, YB0, 1170), T('pizzasign'), 512, 128, facing='s', edge=T('steel')))
    K.add(sign_box((X0, 2600, 600), (X0 + 3, 2800, 900), T('poster'), 256, 384, facing='e', edge=T('trim')))
    x0, y0, x1, y1 = PILLAR
    K.add(box((x0, y0, 40), (x1, y1, ZC), {'side': T('whitetile'), 'top': CAULK, 'bot': CAULK}))
    K.add(box((x0 - 8, y0 - 8, 0), (x1 + 8, y1 + 8, 40), {'side': T('trim'), 'top': T('trim'), 'bot': CAULK}))
    K.reserve(((x0 - 8, y0 - 8, 0), (x1 + 8, y1 + 8, ZC)))
    for y in (-1500, -800, -100, 600, 1300, 2000, 2650):                 # fluorescent panels over the aisle
        K.add(box((-120, y - 240, ZC - 4), (120, y + 240, ZC), {'bot': T('fluor'), 'side': T('steel'), 'top': CAULK}))
    for x in (-450, 450):
        for y in (3220, 3720):
            K.add(box((x - 120, y - 240, ZC - 4), (x + 120, y + 240, ZC), {'bot': T('fluor'), 'side': T('steel'), 'top': CAULK}))
    deco('tv_bracket', X0, 2350, 1000)
    K.add(box((X0, 2220, 984), (X0 + 200, 2480, 1000), WCLIP))
    K.catalog('padtv/padtv.md3', X0 + 70, 2350, 1000, scale=0.45, angle=0, clip=False, nudge=False)
    for (x0, x1, z0, z1, tx) in ((-760, -360, 640, 840, 'neon_pizza'), (420, 680, 860, 990, 'neon_open')):
        K.add(sign_box((x0, YF + 2, z0), (x1, YF + 4, z1), T(tx), 512, 256, facing='s', edge=T('black')))
        K.add(sign_box((x0, YF + 4, z0), (x1, YF + 6, z1), T(tx), 512, 256, facing='n', edge=T('black')))
    K.add(sign_box((-800, YFO - 8, 1400), (800, YFO, 1700), T('shopsign'), 1024, 192, facing='s', edge=T('trim')))


def booths():
    """two rows of red booths with wood-grain tables either side of one aisle (you can run underneath the tables)"""
    for side, x, ang in (('w', X0, 0), ('e', X1, 180)):
        flip = side == 'e'
        names = {'end_s': 'booth_end_s' if flip else 'booth_end_n', 'end_n': 'booth_end_n' if flip else 'booth_end_s',
                 'd1': 'booth_double', 'd2': 'booth_double', 'd3': 'booth_double'}
        for k, yc in ROW_YC.items():
            place(names[k], x, yc, 0, angle=ang)
        s = 1 if side == 'w' else -1
        for y in TABLES:
            place('booth_table', x, y, 0, angle=ang)
            deco('condiments', x + s * 120, y - 40, PM.TABLE_Z, angle=ang)


def counter_area():
    """the curved counter with the slice case and register; back counter with the soda fountain; menu shelf with
    pizza boxes; ATM and cooler against the east wall"""
    cx, cy = COUNTER
    place('counter', cx, cy, 0)
    place('display_case', -150, cy + 25, CZ)
    place('register', -460, cy + 165, CZ, angle=20)
    deco('condiments', 520 - 140, cy + 60, CZ, angle=270)
    bx0, by0, bx1, by1 = BACKC
    K.solid_piece('back_counter', [box((bx0, by0, 0), (bx1, by1, CZ), CAULK)], TX.texfn('steel'))
    place('soda_fountain', -440, by0 + 40, CZ)
    sx0, sx1, sz = SHELF
    deco('menu_shelf', sx1, YB0, sz, angle=180)
    K.add(box((sx0, SHELF_Y0, sz - 20), (sx1, YB0, sz), WCLIP))
    K.occupy(sx0, SHELF_Y0, sx1, YB0, sz - 20, sz)
    place('boxes3', 480, YB0 - 130, sz, angle=0); place('boxes2', 740, YB0 - 130, sz, angle=0)
    place('cooler', *COOLER, 0)
    place('atm', *ATM, 0)
    K.catalog('pad_ddmix/plants/bonsai.md3', 760, YB0 - 90, CZ, scale=0.55, nudge=False)
    K.route('staff_w', (-700, 2300, 0), (-200, 2620, 0))
    K.route('staff_e', (600, 2350, 0), (600, 2620, 0))


def dining():
    """the arcade cabinet, gumball machine, high chair, wet-floor sign, pizza-box stack, the two ceiling fans"""
    place('arcade', -730, 1760, 0, angle=180)
    place('gumball', 640, 2330, 0)
    place('high_chair', -230, 1850, 0, angle=20)
    place('wet_sign', 260, 2080, 0, angle=15)
    for (fx, fy) in (FAN1, FAN2):
        deco('fan_mount', fx, fy, ZC, lit=False)
        assert ML.PLACE['fan_blades'][1] == 1.0
        K.rotating_model2(ML.PLACE['fan_blades'][0], (fx, fy, ZC - 140), 60)
        K.light(fx, fy, ZC - 300, 500, '1 0.9 0.75')


def kitchen():
    """deck oven (walk into the lower deck, stand on top), peel ramp, prep table, sink with the drain"""
    ox, oy = OVEN
    place('oven', ox, oy, 0)
    deco('peel', ox, oy - 330, 0)
    K.ramp(ox - 150, oy - 330, ox + 150, oy, 0, PM.OVEN_CH[0], 'n', WCLIP)
    K.occupy(ox - 150, oy - 330, ox + 150, oy, 0, PM.OVEN_CH[0])
    K.route('oven_mouth', (ox, oy - 420, 0), (ox, oy + 250, PM.OVEN_CH[0]))
    place('prep_table', *PREP, 0, angle=90)
    sink()


def sink():
    """stainless sink counter along the east kitchen wall; the basin is deep water with a stair of plates out and the
    secret drain at the bottom"""
    x0, y0, x1, y1 = SINK
    bx0, by0, bx1, by1 = BASIN
    parts = [box((x0, y0, 0), (x1, by0, SZ), CAULK), box((x0, by1, 0), (x1, y1, SZ), CAULK),
             box((x0, by0, 0), (bx0, by1, SZ), CAULK), box((bx1, by0, 0), (x1, by1, SZ), CAULK),
             box((bx0, by0, 0), (bx1, by1, SF), CAULK)]
    K.solid_piece('sink_counter', parts, TX.texfn('steel'))
    sx0, sy0, sx1, sy1 = STEPS
    steps = K.stairs16(sx0, sy0, sx1, sy1, SF, SZ, 'n', WCLIP)
    deco('plate_steps', (sx0 + sx1) / 2, sy0, SF)
    K.water_box((bx0, by0, SF), (bx1, by1, WTOP), T('water'), cutters=steps)
    deco('faucet', x1 - 40, (by0 + by1) / 2, SZ)
    K.add(box((620, 3200, SF), (700, 3280, SF + 1), {'top': T('grate'), 'side': T('grate'), 'bot': CAULK}))
    K.secret((620, 3200, SF + 1), (700, 3280, SF + 72), dest=(0, -250, VZ), angle=90, name='drain')


def vault():
    """the secret Dough Vault (sealed room below the world): Pad Power, Revival, Killer Ducks, Pad shield"""
    x0, y0, x1, y1 = VAULT; z = VZ; h = 420
    w, f = T('dough'), T('vault')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': f, 'side': CAULK, 'bot': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': w, 'side': CAULK, 'top': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    place('flour_sacks', -330, 220, z); place('tomato_case', 300, 260, z, angle=20)
    place('boxes4', 330, -230, z, angle=10)
    deco('pizza_tray0', -300, -250, z)
    K.item('item_padpower', 0, 120, z); K.item('item_revival', -180, 0, z); K.item('holdable_killerducks', 180, 0, z)
    K.item('item_armor_padshield', 0, -60, z)
    K.teleporter((-48, y1 - 64, z), (48, y1, z + 96), dest=(-300, 3200, 0), angle=0, name='vault_exit')
    K.light(0, 0, z + 330, 700, '1 0.9 0.75'); K.light(-300, 0, z + 180, 250, '1 0.8 0.6'); K.light(300, 0, z + 180, 250, '1 0.8 0.6')


def outside():
    """sidewalk: awning over the shop front (walkable), propped-open door, hydrant, newspaper box, trash basket, lamp"""
    ax0, ax1 = -PM.VALANCE_L / 2, PM.VALANCE_L / 2
    K.solid_piece('awning', [box((ax0, YFO - PM.AWN_D, PM.AWN_Z - 40), (ax1, YFO, PM.AWN_Z), CAULK)], TX.texfn('awning'))
    deco('valance', 0, YFO - PM.AWN_D, PM.AWN_Z - 40)
    deco('door_leaf', DOOR[1], YFO - 10, 0)
    place('hydrant', -650, -2560, 0)
    place('newsbox', 520, -2200, 0)
    place('trash_basket', 700, -2450, 0)
    place('street_lamp', -780, -2640, 0)
    K.catalog('pad_ddmix/plants/flower_pink.md3', -520, -2110, 0, scale=1.0, angle=0)
    K.catalog('pad_ddmix/trashcan/garbage_bag_group.md3', -720, -2180, 0, scale=1.6, angle=30)
    K.route('front_door', (0, YFO - 150, 0), (0, YF + 150, 0))
    K.route('kitchen_door', ((KDOOR[0] + KDOOR[1]) / 2, YB0 - 150, 0), ((KDOOR[0] + KDOOR[1]) / 2, YB1 + 150, 0))


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    J = K.jumppad
    tz = PM.TABLE_Z
    J(-110, TABLES[0], 0, land=(-640, TABLES[0], tz), apex=tz + 260, name='pad_table_w1', edges=[(-330, TABLES[0], tz)])
    J(110, TABLES[1], 0, land=(640, TABLES[1], tz), apex=tz + 260, name='pad_table_e2', edges=[(330, TABLES[1], tz)])
    J(-110, TABLES[3], 0, land=(-640, TABLES[3], tz), apex=tz + 260, name='pad_table_w4', edges=[(-330, TABLES[3], tz)])
    J(-260, 1960, 0, land=(-260, 2270, CZ), apex=CZ + 220, name='pad_counter', edges=[(-260, COUNTER[1], CZ)])
    J(-260, 2430, CZ, land=(100, SHELF_Y0 + 150, SHELF[2]), apex=SHELF[2] + 190, name='pad_shelf', ceiling=ZC,
      edges=[(30, SHELF_Y0, SHELF[2])])
    J(240, COOLER[1], 0, land=(730, COOLER[1], PM.COOLER[2]), apex=PM.COOLER[2] + 190, name='pad_cooler', ceiling=ZC,
      edges=[(550, COOLER[1], PM.COOLER[2])])
    J(-300, 3110, 0, land=(-200, 3700, OZ), apex=OZ + 270, name='pad_oven', ceiling=ZC, edges=[(-230, OVEN[1], OZ)])
    # the sink counter is reached by walking off the oven top's east edge (no floor pad clears the oven)
    J(-450, -2560, 0, land=(-450, YFO - 170, PM.AWN_Z), apex=PM.AWN_Z + 180, name='pad_awning', ceiling=ZSKY,
      edges=[(-450, YFO - PM.AWN_D, PM.AWN_Z)])


def items():
    W, A = K.weapon, K.ammo
    tz = PM.TABLE_Z
    W('imperius', 260, SHELF_Y0 + 120, SHELF[2], marker='purple')
    W('betty', 760, 3230, SF, marker='black')
    W('balloony', 200, 3750, OZ, marker='orange')
    W('pumper', 730, COOLER[1] + 70, PM.COOLER[2], marker='green')
    W('splasher', 300, YFO - 170, PM.AWN_Z, marker='blue')
    W('boaster', 560, TABLES[1] + 70, tz, marker='orange')
    W('bubbleg', 0, -1000, 0, marker='green')
    ammo = {'imperius': [(-20, SHELF_Y0 + 130, SHELF[2]), (-30, 3700, PM.OVEN_CH[0]), (-640, TABLES[1], 0), (500, -2550, 0)],
            'betty': [(660, 3900, SZ), (-300, 3550, 0), (640, TABLES[2], 0), (-600, YFO - 170, PM.AWN_Z)],
            'balloony': [(-250, 3850, OZ), (300, 2830, CZ), (100, 2620, 0), (-560, TABLES[0] + 70, tz)],
            'pumper': [(750, ATM[1], PM.ATM[2]), (700, 2620, 0), (150, -1300, 0), (0, 3150, 0)],
            'splasher': [(-650, -2350, 0), (300, -2600, 0), (540, 3580, SF), (-150, -1850, 0)],
            'boaster': [(-560, TABLES[3] + 70, tz), (0, -1800, 0), (-150, 2150, 0), (640, TABLES[0], 0)],
            'bubbleg': [(-150, 400, 0), (150, 1500, 0), (300, 3550, 0), (-640, TABLES[2], 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: A(w, x, y, z)
    A('nipper', 0, 1700, 0); A('nipper', -700, 2600, 0); A('nipper', 0, -2400, 0)
    K.item('item_armor_shard', -560, TABLES[3] - 70, tz); K.item('item_armor_shard', 100, 2360, CZ)
    K.item('item_armor_shard', 560, TABLES[1] - 80, tz); K.item('item_armor_shard', 150, 3600, PM.OVEN_CH[0])
    K.item('item_speedy', 300, 2340, CZ)
    K.item('item_jumper', 640, TABLES[3], 0)
    K.item('holdable_floater', -400, 3900, 0)
    K.item('item_visionless', -730, 2050, 0)
    K.station(-720, 2520, 0, ang=0)
    for (x, y, a) in ((-150, -1400, 90), (150, -900, 90), (-150, -300, 90), (150, 300, 270), (-150, 900, 270),
                      (150, 1350, 270), (-150, 1700, 270), (0, 2050, 0), (-700, 2280, 0), (700, 2450, 180),
                      (-100, 2620, 0), (-650, 3150, 90), (100, 3150, 90), (-300, 3700, 0), (-600, -2400, 45),
                      (200, -2350, 90), (-250, -2600, 90)):
        K.spawn(x, y, 0, a)


def lights_sounds():
    K.light_grid(X0, YF, X1, YB0, 1320, 600, 1500, color='1 0.97 0.9')
    K.light_grid(X0, YB1, X1, YK, 1320, 600, 1500, color='1 0.98 0.94')
    for y in TABLES:                                    # under the booth tables
        for x in (-640, 640): K.light(x, y, 220, 160, '1 0.9 0.78')
    K.light(OVEN[0], 3700, 320, 300, '1 0.6 0.3')          # inside the oven
    K.light(660, 3430, 520, 260, '0.9 0.95 1')             # over the sink
    K.light(260, 2830, 1150, 260, '1 0.92 0.8')            # menu shelf
    K.light(-700, 2550, 700, 300, '1 0.92 0.8')            # the corner by the kitchen door
    K.speaker(*FAN1, 1200, 'machine/fan_pc'); K.speaker(*FAN2, 1200, 'machine/fan_pc')
    K.speaker(730, COOLER[1], 500, 'machine/freezer')
    K.speaker(OVEN[0], 3600, 300, 'ambient/fire_crackling')
    K.speaker(660, 3430, 480, 'ambient/water_drippling')
    K.speaker(X0 + 150, 2350, 1100, 'machine/tv_upstairs')
    K.timer_sound(0, -2600, 400, 'ambient/police_pass', 'siren', 60, 30)
    K.timer_sound(-600, -2500, 200, 'animal/dog_bark2', 'dog', 45, 25)
    K.timer_sound(500, -2550, 200, 'misc/bicycle_bell', 'bike', 40, 20)
    K.trigger_sound((DOOR[0], YFO, 0), (DOOR[1], YF, 200), 'machine/dingdong', 'doorbell', wait=3)
    K.trigger_sound((150, SHELF_Y0 + 60, SHELF[2]), (370, YB0 - 10, SHELF[2] + 80), 'human/applause', 'summit', wait=8)


def shader():
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(250, 55), sun_int=110, skylight=(60, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = PM.textures(K)
    PM.all_models()                    # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); walls(); booths(); counter_area(); kitchen(); vault(); pads(); dining(); outside(); items(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
