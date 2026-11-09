#!/usr/bin/env python3
"""Couch Lock Lagoon (wop_padlagoon) - a water park built out of Couch Lock's furniture, on a night balcony. FFA.

    OUT=<dir> python3 build_padlagoon.py          (wopbuild.py padlagoon preview / all)

Padman scale (~8u/cm, catalog models 1.0) like Couch Lock: room x -2048..2048, y -1792..1792, deck z 0, ceiling 2048,
the same smoky haze. x east, y north. Levels: pool floor -192 (water top -16) | deck 0 | coffee-table island 320 |
couch seat 400 | sideboard 560 | couch arms 640 (slide start) | couch back 1000 | tent roof 1016 | wall shelf 1200.
Design sheet: README.md.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'lounge'))
import wopmap
from wopmap import box, hull, prism, ngon, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import lg_models as GM
import lounge_models as LM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZC, ZF = 2048, -256                          # ceiling, hull floor
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '24', '_color': '0.85 0.85 1'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
PCX, PCY = GM.POOL_C                         # the Whirl Pool: round (16-gon, flat edges on the axes), sunk in the deck
POOL_POLY = ngon(PCX, PCY, GM.POOL_R, 16)
PN, PS = PCY + GM.POOL_A, PCY - GM.POOL_A    # its north / south flat edges (y 664 / -1064)
PZ, WZ = -192, -16                           # pool floor top, water top
NOTCH_X, NOTCH_Y = 320, 600                  # the cave steps: a 640-wide flight from under the couch down into the pool
CAVE_STAIRS = (-NOTCH_X, GM.SEAT_Y0 - 384, NOTCH_X, GM.SEAT_Y0, 'n')
S_STAIRS = (-160, PS, 160, PS + 384, 's')
TUB_STAIRS = [(-GM.LAND_X, GM.TUB_Y0, -GM.LAND_X + 320, GM.BACK_Y0, 'w'), (GM.LAND_X - 320, GM.TUB_Y0, GM.LAND_X, GM.BACK_Y0, 'e')]
VAULT = (-448, -384, 448, 384); VAULT_Z = -4400       # under the street slab, outside the sky box
TX0, TY0, TX1, TY1 = GM.TABLE
SHELF = (-2048, -1650, -1728, -300, 1200)    # x0 y0 x1 y1 top (north end over the sideboard: a 640 drop, no bot trap)
BONG = (-1590, -1100)                        # the Bong Tube: ride up inside the glass and out of the mouthpiece
BONG_SC = 1.75
# Slip'n'Slide: east couch arm (640) -> over the east deck -> shoots you under the coffee table
SLIP = [(1550, 900, 640), (1550, 500, 520), (1450, 150, 400), (1250, -100, 290), (1000, -200, 180), (780, -200, 90)]
# Gutter Run: white guttering from the top shelf (1200) along the south railing and round into the pool
FLUME = [(-1728, -1500, 1200), (-1400, -1500, 1120), (-280, -1630, 850), (480, -1600, 668), (960, -1480, 540),
         (1180, -1220, 440), (1010, -900, 300), (770, -700, 170), (545, -565, 75)]
DRAIN = (PCX, PCY)                           # under the island, where the whirlpool turns
STACK = (-810, -1340)                        # the spare seat cushions, stacked on the south deck
RAMP = (-1380, 330, -1120, GM.SEAT_Y0)       # the third cushion leaning on the couch: the walk up to the tub


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = GM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def lounge(name, x, y, z, angle=0, scale=1.0, ofs=0.0, boxes=(), cyls=(), lit=True, **kw):
    """a Couch Lock model (models/padlounge, written by LM.make); ofs = its stored mid-height offset"""
    return K.custom((f'{LM.MD}/{name}.md3', scale, ofs * scale), x, y, z, angle, lit=lit, boxes=boxes, cyls=cyls, **kw)


# ------------------------------------------------------------------------------------------------ structure
HULL = (-4500, -8000, 7000, 2400, -3200, 6000)   # sky box round the balcony (x0 y0 x1 y1 z0 z1)
ROOF = 4200                                   # top of the apartment block


def shell():
    """a corner balcony high up an apartment block: the building's facade north (sliding door, LAGOON neon), a brick
    wing west, glass railings south and east open to Couch Lock's painted night city. Sky box + building + street are
    the structural hull; the deck (detail) floats over the street, closed by clip above the railings."""
    hx0, hy0, hx1, hy1, hz0, hz1 = HULL
    sky = T('sky')
    for (mn, mx) in (((hx0 - 16, hy0 - 16, hz1), (hx1 + 16, hy1 + 16, hz1 + 16)), ((hx0 - 16, hy0 - 16, hz0), (hx0, hy1 + 16, hz1)),
                     ((hx1, hy0 - 16, hz0), (hx1 + 16, hy1 + 16, hz1)), ((hx0, hy0 - 16, hz0), (hx1, hy0, hz1)),
                     ((hx0, hy1, hz0), (hx1, hy1 + 16, hz1))):
        K.add(box(mn, mx, {'side': sky, 'top': sky, 'bot': sky}, detail=False))
    K.add(box((hx0 - 16, hy0 - 16, hz0 - 16), (hx1 + 16, hy1 + 16, hz0), {'top': T('street'), 'side': CAULK, 'bot': CAULK}, detail=False))
    fac = {'s': T('facade'), 'w': T('brick'), 'e': T('brick'), 'top': T('concrete'), 'n': CAULK, 'bot': CAULK}
    K.add(box((hx0, Y1, hz0), (hx1, hy1, ROOF), fac, detail=False))                       # the block (north)
    K.add(box((hx0, Y0 - 64, hz0), (X0, Y1, ROOF), {'e': T('brick'), 's': T('brick'), 'top': T('concrete'),
                                                     'n': CAULK, 'w': CAULK, 'bot': CAULK}, detail=False))   # west wing
    K.add(box((-3800, -7400, hz0), (-600, -6400, 1200), T('far_a')))                       # across the street
    K.add(box((600, -7000, hz0), (4600, -6100, -400), T('far_b')))
    K.add(box((3600, -2600, hz0), (6400, 400, 900), T('far_a')))                           # east, down the road
    # deck: one slab with the round pool and the notch for the cave steps carved out of it
    ex, ey = X1 + 40, Y0 - 40
    cutters = [prism(POOL_POLY, ZF - 8, 8, CAULK), box((-NOTCH_X, NOTCH_Y, ZF - 8), (NOTCH_X, GM.SEAT_Y0, 8), CAULK)]
    for pc in wopmap.carve(box((X0, ey, ZF), (ex, Y1, 0), T('carpet')), cutters):
        for f in pc.faces:
            f.tex = T('carpet') if f.n[2] > 0.9 else T('concrete') if f.n[2] < -0.9 else T('pool_tile')
        K.add(pc)
    floor = prism(POOL_POLY, ZF, PZ, {'top': T('pool_floor'), 'side': CAULK, 'bot': T('concrete')})
    K.add(floor)
    for pc in wopmap.carve(box((-NOTCH_X, NOTCH_Y, ZF), (NOTCH_X, GM.SEAT_Y0, PZ), T('pool_floor')), [floor]):
        K.add(pc)
    K.reserve(((X0, ey, ZF), (ex, Y1, 0)))
    # glass railings (south + east) with steel posts and top rail; clip up to the sky above them
    rh = 400
    for (a, b) in (((X0, Y0 - 24), (ex, Y0 - 8)), ((X1 + 8, Y0 - 8), (X1 + 24, Y1))):
        K.add(box((a[0], a[1], 0), (b[0], b[1], rh), T('rail_glass')))
        K.add(box((a[0], a[1], rh), (b[0], b[1], rh + 24), T('rail_steel')))
        K.add(box((a[0], a[1], rh + 24), (b[0], b[1], 3600), CLIP))
    place('rail_posts', 0, 0, 0)
    K.reserve(((X0, Y0 - 40, 0), (ex, Y0 + 8, rh + 24)), ((X1 - 8, Y0 - 40, 0), (ex, Y1, rh + 24)))
    # the flat's sliding door (lit room behind sheer curtains), LAGOON neon over the couch, one poster on the brick
    K.add(sign_box((1730, Y1 - 4, 0), (2030, Y1, 1100), T('slider_door'), 512, 512, facing='s', edge=T('rail_steel')))
    K.add(sign_box((-512, Y1 - 6, 1300), (512, Y1, 1556), T('sign_lagoon'), 1024, 256, facing='s', edge=T('skirting')))
    K.add(box((-1700, Y1 - 10, 1240), (1700, Y1 - 2, 1254), T('neon_purple')))
    K.add(box((X0 + 2, -1700, 1640), (X0 + 10, 1700, 1654), T('neon_green')))
    K.add(sign_box((X0, 900, 800), (X0 + 4, 1300, 1400), T('poster2'), 512, 768, facing='e', edge=T('skirting')))
    # a low smoky haze over the deck (Couch Lock's)
    K.add(box((X0 + 16, Y0 + 16, 0), (X1 - 16, Y1 - 16, 1300), T('fog_haze')))


def pool():
    """the Whirl Pool: round water body carved by the steps and the island's legs, a slow circular current, the
    drain under the island (the secret). Cave steps north (through the waterfall), pool steps south."""
    st = {'top': T('coping'), 'side': T('pool_tile'), 'bot': CAULK}
    cutters = []
    for (x0, y0, x1, y1, d) in (CAVE_STAIRS, S_STAIRS):
        K.stairs16(x0, y0, x1, y1, PZ, 0, d, st)
        cutters.append(K.stair_wedge(x0, y0, x1, y1, PZ, 0, d))
    K.keep_clear(-200, PS - 110, 200, PS, 0)
    tc = ((TX0 + TX1) / 2, (TY0 + TY1) / 2)
    for (a, b) in GM.COLL['coffee_table']['boxes']:
        if a[2] < WZ - PZ:
            cutters.append(box((tc[0] + a[0], tc[1] + a[1], PZ + a[2]), (tc[0] + b[0], tc[1] + b[1], PZ + min(b[2], 400)), CAULK))
    dx, dy = DRAIN
    K.add(box((dx - 96, dy - 96, PZ), (dx + 96, dy + 96, PZ + 2), {'top': T('drain'), 'side': T('pool_floor'), 'bot': CAULK}))
    cutters.append(box((dx - 96, dy - 96, PZ), (dx + 96, dy + 96, PZ + 2), CAULK))
    body = prism(POOL_POLY, PZ, WZ, T('water'))
    K.water_box(None, None, T('water'), cutters=cutters, brush=body)
    K.water_box((-NOTCH_X, NOTCH_Y, PZ), (NOTCH_X, GM.SEAT_Y0, WZ), T('water'),
                cutters=[prism(POOL_POLY, PZ - 8, WZ + 8, CAULK)] + cutters[:1])
    K.secret((dx - 80, dy - 80, PZ + 2), (dx + 80, dy + 80, PZ + 72), dest=(0, -250, VAULT_Z), angle=90, name='drain')
    place('coping_ring', 0, 0, 0)
    for k, yaw in enumerate((135, 225, 315, 45)):                      # the whirl: four short pulses, anticlockwise
        a = math.radians(45 + 90 * k)
        cx, cy = PCX + 600 * math.cos(a), PCY + 600 * math.sin(a)
        K.current((cx - 80, cy - 80, PZ + 8), (cx + 80, cy + 80, WZ), yaw, speed=190, wait=0.45, name=f'whirl{k}')


def tub():
    """the Couch Tub: water in the couch (floor 240, surface 384), moulded steps up to the end cushions, and Couch
    Falls spilling over the lip onto the cave steps"""
    st = {'top': T('coping'), 'side': T('coping'), 'bot': CAULK}
    cutters = []
    for (x0, y0, x1, y1, d) in TUB_STAIRS:
        K.stairs16(x0, y0, x1, y1, GM.TUB_FLOOR, GM.SEAT_Z, d, st)
        cutters.append(K.stair_wedge(x0, y0, x1, y1, GM.TUB_FLOOR, GM.SEAT_Z, d))
    K.water_box((-GM.LAND_X, GM.TUB_Y0, GM.TUB_FLOOR), (GM.LAND_X, GM.BACK_Y0, GM.TUB_WATER), T('water'), cutters=cutters)
    place('waterfall', 0, 0, 0, lit=False)
    place('hose', 0, 0, 0)
    rb = K.ramp(*RAMP, 0, GM.SEAT_Z, 'n', {'top': T('cushion'), 'side': T('cushion'), 'bot': CAULK}, route='cushion_ramp')
    K.keep_clear(RAMP[0], RAMP[1] - 110, RAMP[2], RAMP[1], 0)


def vault():
    """the stash box: a sealed wooden box under the world (Pad Power, Revival, Killer Ducks, Pad shield)"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 384
    w, lid = T('stash'), T('stash_lid')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), tex6(top=w), detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), tex6(bot=w), detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False),
          box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False),
          box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    K.add(sign_box((-200, y1 - 4, z + 140), (200, y1, z + 340), lid, 512, 512, facing='s', edge=w))
    lounge('jar', -300, 250, z, scale=1.4, cyls=[(0, 0, LM.JAR_R * 1.4, 0, LM.JAR_H * 1.4)])
    lounge('grinder', 200, 150, z, scale=1.3, cyls=[(0, 0, LM.GRINDER_R * 1.3, 0, 70)])
    K.item('item_padpower', 0, 150, z); K.item('item_revival', -300, -200, z); K.item('holdable_killerducks', 300, -200, z)
    K.item('item_armor_padshield', 0, 0, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(460, -1180, 0), angle=90, name='stash_exit')
    K.light(0, 0, z + 320, 700, '1 0.85 0.6'); K.light(-300, 0, z + 160, 250, '0.6 1 0.6'); K.light(300, 0, z + 160, 250, '0.6 1 0.6')


# ------------------------------------------------------------------------------------------------ furniture
def furniture():
    place('couch', 0, 0, 0)
    place('festoon', 0, 0, 0)
    sz, bz = GM.SEAT_Z, GM.BACK_Z
    place('pillow0', -1250, 1456, sz, angle=4)                       # on the west end cushion
    place('pillow2', -600, 1700, bz, angle=-5); place('pillow1', 1050, 1700, bz, angle=4)     # along the back
    place('remote', -700, 924, sz, angle=8, lit=False)
    place('popcorn', -1550, 1150, GM.ARM_Z)
    K.catalog('pad_ducks/pad_duck.md3', 450, 1660, bz, angle=250, clip=True)
    # the spare seat cushions: two stacked on the south deck (cover) with what was on the couch
    sx, sy = STACK
    place('cushion', sx, sy, 0); place('cushion', sx + 30, sy - 10, 160, angle=7)
    place('pillow3', sx - 90, sy + 60, 320, angle=20)
    place('pizza_box', sx + 220, sy - 60, 320, angle=-12)
    place('controller', sx - 250, sy - 160, 320, angle=-40, lit=False)
    K.crawl((-GM.COUCH_X, GM.SEAT_Y0, 0), (GM.COUCH_X, GM.COUCH_Y1, GM.LEG_Z))
    tc = ((TX0 + TX1) / 2, (TY0 + TY1) / 2)
    place('coffee_table', tc[0], tc[1], PZ)
    K.add(box((-64, TY1, GM.TABLE_Z), (64, TY1 + 260, GM.TABLE_Z + 12), {'top': T('coping'), 'side': T('slide_side'), 'bot': T('slide_side')}))
    K.reserve(((-64, TY1, GM.TABLE_Z), (64, TY1 + 260, GM.TABLE_Z + 12)))
    # Couch Lock's table clutter on the island
    lounge('ashtray', 60, 0, GM.TABLE_Z, angle=30, cyls=[(0, 0, LM.ASH_R, 0, 40)])
    lounge('grinder', 360, -360, GM.TABLE_Z, cyls=[(0, 0, LM.GRINDER_R, 0, 60)])
    lounge('lighter', 300, -80, GM.TABLE_Z, angle=70)
    lounge('chips', -280, -250, GM.TABLE_Z, scale=0.6, boxes=[((-LM.CHIPS[0] * 0.6, -LM.CHIPS[1] * 0.6, 0), (LM.CHIPS[0] * 0.6, LM.CHIPS[1] * 0.6, 60))])
    # sideboard + telly + lava lamps, the wall shelf above it, the bong bubble lift
    x0, y0, x1, y1, h = GM.TV_STAND
    place('tv_stand', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    lounge('lava_purple', -1760, -330, h, cyls=[(0, 0, LM.LAVA_R, 0, LM.LAVA_H)])
    lounge('lava_green', -1760, 630, h, cyls=[(0, 0, LM.LAVA_R, 0, LM.LAVA_H)])
    sx0, sy0, sx1, sy1, sz = SHELF
    place('wall_shelf', X0, (sy0 + sy1) / 2, sz)
    K.reserve(((sx0, sy0, sz - 32), (sx1, sy1, sz)))
    lounge('jar', -1960, -1560, sz, cyls=[(0, 0, LM.JAR_R, 0, LM.JAR_H)])
    bx, by = BONG
    lounge('bong', bx, by, 0, scale=BONG_SC, ofs=LM.BONG_OFS, occupy=False)
    # giant lava lamps (floor towers), the grow-tent cabin, plants
    lounge('lava_purple', -1880, 1300, 0, scale=2.4, cyls=[(0, 0, LM.LAVA_R * 2.4, 0, LM.LAVA_H * 2.4)])
    lounge('lava_green', 1880, -150, 0, scale=2.4, cyls=[(0, 0, LM.LAVA_R * 2.4, 0, LM.LAVA_H * 2.4)])
    x0, y0, x1, y1, H = GM.TENT
    place('grow_tent', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    K.keep_clear(x0 - 160, GM.TENT_DOOR[0], x0, GM.TENT_DOOR[1], 0)
    K.route('tent_in', (x0 - 120, -1440, 0), (x0 + 200, -1440, 0))
    lounge('plant_small', 1900, -1650, 0, lit=False, ofs=LM.PLANT_SMALL_OFS, cyls=[(0, 0, 70, 0, 120)])
    lounge('plant_small', 1900, -1230, 0, lit=False, ofs=LM.PLANT_SMALL_OFS, cyls=[(0, 0, 70, 0, 120)])
    lounge('plant_big', -1680, -620, 0, lit=False, ofs=LM.PLANT_OFS, cyls=[(0, 0, 110, 0, 160)])
    # pool floats circling the island
    K.rotating_model2(f'models/{NS}/floats.iqm', (tc[0], tc[1], WZ + 60), 6)


def slides():
    """two rides, both slick: the Slip'n'Slide off the east couch arm, and the Gutter Run from the top shelf"""
    K.flume(SLIP, T('slipslide'), T('slip_edge'), half_width=120, wall=28, supports=[(k, 0) for k in (1, 2, 3, 4)],
            support_tex=T('support'))
    K.flume(FLUME, T('gutter'), T('gutter_side'), half_width=88, wall=48, supports=[(k, 0) for k in range(1, 8)],
            support_tex=T('support'))


def clutter():
    """poolside: loungers, an umbrella, towels, a bean bag, the hookah, crisps - the floor cover"""
    place('lounger', -60, -1480, 0, angle=90); place('lounger', 640, -1480, 0, angle=90)
    place('umbrella', 1300, -560, 0)
    place('towel', -1200, -170, 0, angle=80); place('towel', 1650, 760, 0, angle=15)
    lounge('beanbag', -1150, -600, 0, angle=40, cyls=[(0, 0, LM.BEANBAG_R * 0.75, 0, LM.BEANBAG_H * 0.7)])
    lounge('hookah', -1510, 760, 0, ofs=LM.HOOKAH_OFS, cyls=[(0, 0, LM.HOOKAH_BASE_R, 0, 280)])
    lounge('chips', 580, 750, 0, scale=0.6, boxes=[((-LM.CHIPS[0] * 0.6, -LM.CHIPS[1] * 0.6, 0), (LM.CHIPS[0] * 0.6, LM.CHIPS[1] * 0.6, 70))])
    lounge('crisps', 1180, 520, 0, angle=40, lit=False)
    K.catalog('pad_ducks/pad_duck.md3', 1870, 560, 0, angle=180, clip=True)
    for (x, y, a) in ((-900, 760, 20), (850, -1150, 100), (-1700, 330, 200)):
        K.catalog('pad_tins/pad_coke_cr.md3', x, y, 0, angle=a, clip=False)


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    bx, by = BONG
    sx0, sy0, sx1, sy1, sz = SHELF
    tz, az, bz, lz = GM.TABLE_Z, GM.ARM_Z, GM.BACK_Z, GM.SEAT_Z
    K.jumppad(bx, by, 0, land=(-1880, by, sz), apex=sz + 260, name='bong_lift', edges=[(sx1, by, sz)], light_rgb='0.5 1 0.6')
    K.jumppad(300, -1320, 0, land=(220, -420, tz), apex=tz + 260, name='pad_table', edges=[(240, TY0, tz)])
    K.jumppad(-1060, 60, 0, land=(-380, -100, tz), apex=tz + 260, name='pad_table2', edges=[(TX0, -60, tz)])
    K.jumppad(900, 760, 0, land=(1250, 1180, lz), apex=lz + 260, name='pad_tub', edges=[(1040, GM.SEAT_Y0, lz)])
    K.jumppad(1250, 1420, lz, land=(800, 1660, bz), apex=bz + 200, name='pad_back', edges=[(1000, GM.BACK_Y0, bz)])
    K.jumppad(-1250, 1280, lz, land=(-1550, 1350, az), apex=az + 200, name='pad_westarm', edges=[(-1400, 1330, az)])
    K.jumppad(1874, 1560, 0, land=(1550, 1500, az), apex=az + 220, name='pad_slide', edges=[(1700, 1530, az)])
    K.jumppad(-1440, 160, 0, land=(-1844, 160, GM.TV_STAND[4]), apex=GM.TV_STAND[4] + 220, name='pad_sideboard',
              edges=[(-1648, 160, GM.TV_STAND[4])])
    x0, y0, x1, y1, H = GM.TENT
    K.jumppad(1770, -880, 0, land=(1770, -1380, H + 16), apex=H + 16 + 300, name='pad_tent', edges=[(1770, y1, H + 16)])


def items():
    sz, tz, az, bz, lz, th = SHELF[4], GM.TABLE_Z, GM.ARM_Z, GM.BACK_Z, GM.SEAT_Z, GM.TENT[4] + 16
    K.weapon('imperius', -1890, -1250, sz, marker='purple')          # top shelf: up the Bong Tube, down the Gutter Run
    K.weapon('betty', 1780, -1500, th, marker='black')               # tent roof
    K.weapon('balloony', -300, 1660, bz, marker='orange')            # couch back
    K.weapon('pumper', 150, -250, tz, marker='green')                # the island
    K.weapon('splasher', -1844, 300, GM.TV_STAND[4], marker='blue')  # sideboard
    K.weapon('boaster', 0, 1340, 0, marker='orange')                 # the cave behind the waterfall
    K.weapon('bubbleg', 120, -1240, 0, marker='green')
    ammo = {'imperius': [(-1890, -850, sz), (-500, -700, PZ), (1780, -1150, th)],
            'betty': [(1700, -1450, 0), (-1550, 1500, az), (600, 1650, bz), (300, -800, PZ)],
            'balloony': [(-900, 1660, bz), (1500, 1640, az), (-1700, -1650, 0), (500, 1234, GM.TUB_FLOOR)],
            'pumper': [(-150, -420, tz), (600, 150, PZ), (1480, -1000, 0), (-1000, 750, 0)],
            'splasher': [(-1844, -250, GM.TV_STAND[4]), (-650, -150, PZ), (1300, 1300, 0)],
            'boaster': [(-700, 1300, 0), (700, 1300, 0), (1880, 200, 0), (-500, 1234, GM.TUB_FLOOR)],
            'bubbleg': [(330, -1700, 0), (-1600, -300, 0), (1400, 650, 0), (700, 540, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', -250, -1140, 0); K.ammo('nipper', 1650, -380, 0); K.ammo('nipper', -760, 700, 0)
    K.item('item_armor_padshield', 0, 1234, GM.TUB_FLOOR)            # bottom of the Couch Tub
    K.item('item_armor_shard', 300, 1660, bz); K.item('item_armor_shard', 400, -300, tz)
    K.item('item_speedy', 1550, 1250, az)
    K.item('holdable_floater', 1800, -1500, 0)
    K.item('item_jumper', -1560, 1620, az)
    K.station(1600, -700, 0, ang=180)
    for (x, y, z, a) in ((-1560, -1600, 0, 45), (-200, -1180, 0, 90), (960, -1690, 0, 90), (1340, -1000, 0, 135),
                         (1700, -300, 0, 180), (1300, 800, 0, 225), (-560, 800, 0, 270), (-980, 560, 0, 300),
                         (-1560, -360, 0, 0), (-1320, -40, 0, 0), (-1250, 1050, lz, 270), (100, 1680, bz, 270),
                         (1800, -1300, 0, 180), (0, -400, tz, 90)):
        K.spawn(x, y, z, a)


def lights_sounds():
    K.light_grid(X0, Y0, X1, Y1, 1450, 768, 3600, color='1 0.88 0.72')
    for k in range(6):                                                                     # underwater ring
        a = math.radians(60 * k)
        K.light(PCX + 620 * math.cos(a), PCY + 620 * math.sin(a), -100, 300, '0.4 0.9 1')
    K.light(0, 1234, 330, 260, '0.4 0.8 1'); K.light(-600, 1234, 330, 220, '0.4 0.8 1'); K.light(600, 1234, 330, 220, '0.4 0.8 1')
    K.light(0, 780, 200, 300, '0.6 0.9 1')                                                 # Couch Falls
    K.light(-1700, 160, 900, 400, '0.6 0.8 1')                                             # telly
    K.light(-1880, 1300, 900, 350, '0.9 0.4 1'); K.light(1880, -150, 900, 350, '0.4 1 0.5')
    K.light(1768, -1440, 850, 450, '1 0.5 0.9')                                            # grow light in the tent
    K.light(BONG[0] + 200, BONG[1], 700, 400, '0.5 1 0.6')
    K.light(-1880, -1000, 1400, 400, '1 0.9 0.8')                                           # over the shelf
    K.light(-500, 1300, 40, 200, '1 0.8 0.6'); K.light(500, 1300, 40, 200, '1 0.8 0.6')     # the cave
    K.speaker(0, -250, 0, 'ambient/water_rippling')
    K.speaker(0, 860, 150, 'ambient/water_flowing')
    K.speaker(BONG[0], BONG[1] + 200, 300, 'ambient/slime_bubbling')
    K.speaker(-1700, 160, 800, 'machine/tv_upstairs')
    K.speaker(1250, 1700, 1100, 'human/snoring')
    K.timer_sound(0, 0, 1700, 'ambient/police_pass', 'siren', 50, 25)
    K.timer_sound(1900, 1700, 400, 'misc/door_buzzer', 'pizza', 70, 30)
    K.trigger_sound((-2040, -1350, SHELF[4]), (-1740, -1150, SHELF[4] + 96), 'human/applause', 'summit', wait=8)


if __name__ == '__main__':
    TX = GM.textures(K)
    GM.all_models()
    lm_shaders = LM.make(OUT)                    # Couch Lock's models + textures -> models/padlounge
    GM.BT.make_sky(OUT)                          # Couch Lock's painted night city -> env/padlounge/night_*
    shell(); vault(); furniture(); pool(); tub(); slides(); pads(); clutter(); items(); lights_sounds()
    K.fix_items()
    TX.write_shader(extra=[lm_shaders], arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
