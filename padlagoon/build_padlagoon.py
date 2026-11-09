#!/usr/bin/env python3
"""Couch Lock Lagoon (wop_padlagoon) - Couch Lock's living room flooded into a water park. FFA, built on woplib.

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
from wopmap import box, hull, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import lg_models as GM
import lounge_models as LM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZC, ZF = 2048, -256                          # ceiling, hull floor
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '30', '_color': '1 0.9 0.8'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
POOL = (-1200, -1000, 1200, 500)             # pool hole in the deck
PZ, WZ = -192, -16                           # pool floor top, water top
VAULT = (-448, -384, 448, 384); VAULT_Z = -1600
TX0, TY0, TX1, TY1 = GM.TABLE
SHELF = (-2048, -1650, -1728, -300, 1200)    # x0 y0 x1 y1 top (north end over the sideboard: a 640 drop, no bot trap)
BONG = (-1470, -1100)
BONG_SC = 1.5
SLIDE = [(1550, 900, 640), (1550, 470, 510), (1550, 60, 370), (1440, -290, 240), (1210, -560, 120), (980, -700, 40)]
DRAIN = (-760, 300)
STAIRS = [(-1150, -1000, -910, -616, 's'), (910, 116, 1150, 500, 'n')]   # 16u flights out of the pool


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
def shell():
    """structural hull round the room and the sunken pool; the deck is detail blocks round the pool hole"""
    K.add(box((X0 - 32, Y0 - 32, ZF - 32), (X1 + 32, Y1 + 32, ZF), tex6(), detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZF), (X0, Y1 + 32, ZC), tex6(e=T('wall')), detail=False))
    K.add(box((X1, Y0 - 32, ZF), (X1 + 32, Y1 + 32, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((X0, Y0 - 32, ZF), (X1, Y0, ZC), tex6(n=T('wall')), detail=False))
    K.add(box((X0, Y1, ZF), (X1, Y1 + 32, ZC), tex6(s=T('wall')), detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    px0, py0, px1, py1 = POOL
    deck = [((X0, Y0), (X1, py0), {'n': T('pool_tile')}), ((X0, py1), (X1, Y1), {'s': T('pool_tile')}),
            ((X0, py0), (px0, py1), {'e': T('pool_tile')}), ((px1, py0), (X1, py1), {'w': T('pool_tile')})]
    for (a, b, side) in deck:
        K.add(box((a[0], a[1], ZF), (b[0], b[1], 0), tex6(top=T('carpet'), **side)))
    K.add(box((px0, py0, ZF), (px1, py1, PZ), tex6(top=T('pool_floor'))))
    K.reserve(((X0, Y0, ZF), (X1, Y1, 0)))
    # skirting, neon strips, posters, the neon LAGOON sign over the couch
    for (a, b) in (((X0, Y0), (X0 + 8, Y1)), ((X1 - 8, Y0), (X1, Y1)), ((X0 + 8, Y0), (X1 - 8, Y0 + 8)), ((X0 + 8, Y1 - 8), (-1700, Y1)), ((1700, Y1 - 8), (X1 - 8, Y1))):
        K.add(box((a[0], a[1], 0), (b[0], b[1], 48), T('skirting')))
    zt = ZC - 80
    K.add(box((X0 + 8, Y1 - 14, zt), (X1 - 8, Y1 - 6, zt + 14), T('neon_purple')))
    K.add(box((X0 + 8, Y0 + 6, zt), (X1 - 8, Y0 + 14, zt + 14), T('neon_purple')))
    K.add(box((X0 + 6, Y0 + 14, zt), (X0 + 14, Y1 - 14, zt + 14), T('neon_green')))
    K.add(box((X1 - 14, Y0 + 14, zt), (X1 - 6, Y1 - 14, zt + 14), T('neon_green')))
    K.add(sign_box((-512, Y1 - 6, 1300), (512, Y1, 1556), T('sign_lagoon'), 1024, 256, facing='s', edge=T('skirting')))
    K.add(sign_box((X1 - 4, -200, 800), (X1, 200, 1400), T('poster0'), 512, 768, facing='w', edge=T('skirting')))
    K.add(sign_box((-1000, Y0, 800), (-600, Y0 + 4, 1400), T('poster1'), 512, 768, facing='n', edge=T('skirting')))
    K.add(sign_box((X0, 900, 800), (X0 + 4, 1300, 1400), T('poster2'), 512, 768, facing='e', edge=T('skirting')))
    # the haze (Couch Lock's smoky room): one fog brush over the deck level
    K.add(box((X0 + 16, Y0 + 16, 0), (X1 - 16, Y1 - 16, ZC - 96), T('fog_haze')))


def pool():
    """water box carved by the table legs and the walk-out stairs; drain grate = the secret"""
    px0, py0, px1, py1 = POOL
    cutters = []
    for (x0, y0, x1, y1, d) in STAIRS:
        K.stairs16(x0, y0, x1, y1, PZ, 0, d, {'top': T('coping'), 'side': T('pool_tile'), 'bot': CAULK},
                   route=f'pool_out_{d}')
        cutters.append(box((x0, y0, PZ), (x1, y1, 0), CAULK))
    tc = ((TX0 + TX1) / 2, (TY0 + TY1) / 2)
    for (a, b) in GM.COLL['coffee_table']['boxes']:
        if a[2] < WZ - PZ:
            cutters.append(box((tc[0] + a[0], tc[1] + a[1], PZ + a[2]), (tc[0] + b[0], tc[1] + b[1], PZ + min(b[2], 400)), CAULK))
    dx, dy = DRAIN
    K.add(box((dx - 96, dy - 96, PZ), (dx + 96, dy + 96, PZ + 2), {'top': T('drain'), 'side': T('pool_floor'), 'bot': CAULK}))
    cutters.append(box((dx - 96, dy - 96, PZ), (dx + 96, dy + 96, PZ + 2), CAULK))
    K.water_box((px0, py0, PZ), (px1, py1, WZ), T('water'), cutters=cutters)
    K.secret((dx - 80, dy - 80, PZ + 2), (dx + 80, dy + 80, PZ + 72), dest=(0, -250, VAULT_Z), angle=90, name='drain')


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
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(0, -1450, 0), angle=90, name='stash_exit')
    K.light(0, 0, z + 320, 700, '1 0.85 0.6'); K.light(-300, 0, z + 160, 250, '0.6 1 0.6'); K.light(300, 0, z + 160, 250, '0.6 1 0.6')


# ------------------------------------------------------------------------------------------------ furniture
def furniture():
    place('couch', 0, 0, 0)
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
    lounge('lava_green', 1000, -1600, 0, scale=2.4, cyls=[(0, 0, LM.LAVA_R * 2.4, 0, LM.LAVA_H * 2.4)])
    x0, y0, x1, y1, H = GM.TENT
    place('grow_tent', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    K.keep_clear(x0 - 160, GM.TENT_DOOR[0], x0, GM.TENT_DOOR[1], 0)
    K.route('tent_in', (x0 - 120, -1440, 0), (x0 + 200, -1440, 0))
    lounge('plant_small', 1900, -1650, 0, lit=False, ofs=LM.PLANT_SMALL_OFS, cyls=[(0, 0, 70, 0, 120)])
    lounge('plant_small', 1900, -1230, 0, lit=False, ofs=LM.PLANT_SMALL_OFS, cyls=[(0, 0, 70, 0, 120)])
    lounge('plant_big', -1680, -620, 0, lit=False, ofs=LM.PLANT_OFS, cyls=[(0, 0, 110, 0, 160)])
    # pool floats circling the island
    K.rotating_model2(f'models/{NS}/floats.iqm', (tc[0], tc[1], WZ + 60), 6)


def slide():
    """'Cushion Plunge': from the east couch arm (640) down over the east deck into the pool. Slick floor."""
    P = [np.array(p, float) for p in SLIDE]
    n = len(P); hw, wt, wh, ft = 96, 16, 40, 16
    dirs = [(P[i + 1][:2] - P[i][:2]) / np.linalg.norm(P[i + 1][:2] - P[i][:2]) for i in range(n - 1)]
    perps = [np.array([-d[1], d[0]]) for d in dirs]
    J = []
    for k in range(n):
        mm = perps[0] if k == 0 else perps[-1] if k == n - 1 else (perps[k - 1] + perps[k]) / np.linalg.norm(perps[k - 1] + perps[k])
        J.append((mm, 1.0 / max(0.5, float(mm @ perps[min(k, n - 2)]))))
    for i in range(n - 1):
        (ma, fa), (mb, fb) = J[i], J[i + 1]
        ca, cb = P[i], P[i + 1]
        za, zb = ca[2], cb[2]
        e = lambda c, mm, f, off: c[:2] + mm * off * f
        La, Ra, Lb, Rb = e(ca, ma, fa, hw), e(ca, ma, fa, -hw), e(cb, mb, fb, hw), e(cb, mb, fb, -hw)
        for (p1, p2, p3, z1, z2, z3) in ((La, Ra, Lb, za, za, zb), (Ra, Rb, Lb, za, zb, zb)):
            pts = [(p1[0], p1[1], z1), (p2[0], p2[1], z2), (p3[0], p3[1], z3),
                   (p1[0], p1[1], z1 - ft), (p2[0], p2[1], z2 - ft), (p3[0], p3[1], z3 - ft)]
            K.add(hull(pts, {'top': T('slide'), 'side': T('slide_side'), 'bot': T('slide_side')}, round_pts=False))
        for s in (1, -1):
            ia, ib = e(ca, ma, fa, s * hw), e(cb, mb, fb, s * hw)
            oa, ob = e(ca, ma, fa, s * (hw + wt)), e(cb, mb, fb, s * (hw + wt))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - ft), (p[0], p[1], zz + wh)]
            K.add(hull(pw, T('slide_side'), round_pts=False))
    for (x, y, z) in SLIDE[1:4]:                     # supports down to the deck
        K.add(box((x - 20, y - 20, 0), (x + 20, y + 20, z - ft - 24), T('support')))
    x, y, z = SLIDE[4]
    K.add(box((1240, y - 20, 0), (1280, y + 20, z - ft - 30), T('support')))
    mn = np.min([p for p in SLIDE], 0) - (hw + wt + 8); mx = np.max([p for p in SLIDE], 0) + (hw + wt + 8)
    for i in range(n - 1):                           # keep props off the slide's footprint
        a, b = P[i], P[i + 1]
        K.reserve(((min(a[0], b[0]) - 120, min(a[1], b[1]) - 120, 0), (max(a[0], b[0]) + 120, max(a[1], b[1]) + 120, max(a[2], b[2]) + 60)))


def clutter():
    """poolside: loungers, umbrellas, towels, bean bags, the hookah, crisps - the floor cover"""
    place('lounger', -400, -1500, 0, angle=90); place('lounger', 200, -1520, 0, angle=90)
    place('umbrella', -100, -1400, 0)
    place('towel', 650, -1250, 0, angle=15); place('towel', -1500, 200, 0, angle=80)
    lounge('beanbag', -1050, -1380, 0, angle=40, cyls=[(0, 0, LM.BEANBAG_R * 0.75, 0, LM.BEANBAG_H * 0.7)])
    lounge('hookah', -1450, 750, 0, ofs=LM.HOOKAH_OFS, cyls=[(0, 0, LM.HOOKAH_BASE_R, 0, 280)])
    lounge('chips', 800, 700, 0, scale=0.6, boxes=[((-LM.CHIPS[0] * 0.6, -LM.CHIPS[1] * 0.6, 0), (LM.CHIPS[0] * 0.6, LM.CHIPS[1] * 0.6, 70))])
    lounge('crisps', 1150, 640, 0, angle=40, lit=False)
    K.catalog('pad_ducks/pad_duck.md3', 1870, 300, 0, angle=180, clip=True)
    for (x, y, a) in ((-900, -1650, 20), (800, -1100, 100), (-1700, 300, 200)):
        K.catalog('pad_tins/pad_coke_cr.md3', x, y, 0, angle=a, clip=False)


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    bx, by = BONG
    sx0, sy0, sx1, sy1, sz = SHELF
    K.jumppad(bx, by, 0, land=(-1890, by, sz), apex=sz + 160, name='bong_lift', ceiling=ZC, edges=[(sx1, by, sz)],
              light_rgb='0.5 1 0.6')
    K.jumppad(0, -1250, 0, land=(0, -380, GM.TABLE_Z), apex=GM.TABLE_Z + 260, name='pad_table', edges=[(0, TY0, GM.TABLE_Z)])
    K.jumppad(420, 720, 0, land=(300, -60, GM.TABLE_Z), apex=GM.TABLE_Z + 260, name='pad_table2', edges=[(300, TY1, GM.TABLE_Z)])
    K.jumppad(-500, 720, 0, land=(-500, 1200, GM.SEAT_Z), apex=GM.SEAT_Z + 260, name='pad_seat', edges=[(-500, GM.SEAT_Y0, GM.SEAT_Z)])
    K.jumppad(800, 1030, GM.SEAT_Z, land=(800, 1660, GM.BACK_Z), apex=GM.BACK_Z + 200, name='pad_back', ceiling=ZC,
              edges=[(800, GM.BACK_Y0, GM.BACK_Z)])
    K.jumppad(-1180, 1050, GM.SEAT_Z, land=(-1550, 1350, GM.ARM_Z), apex=GM.ARM_Z + 200, name='pad_westarm',
              edges=[(-1400, 1200, GM.ARM_Z)])
    K.jumppad(1874, 1560, 0, land=(1550, 1500, GM.ARM_Z), apex=GM.ARM_Z + 220, name='pad_slide', edges=[(1700, 1530, GM.ARM_Z)])
    K.jumppad(-1440, 160, 0, land=(-1844, 160, GM.TV_STAND[4]), apex=GM.TV_STAND[4] + 220, name='pad_sideboard',
              edges=[(-1648, 160, GM.TV_STAND[4])])
    x0, y0, x1, y1, H = GM.TENT
    K.jumppad(1150, -1300, 0, land=(1780, -1300, H + 16), apex=H + 16 + 300, name='pad_tent', ceiling=ZC, edges=[(x0, -1260, H + 16)])


def items():
    sz = SHELF[4]
    K.weapon('imperius', -1890, -1250, sz, marker='purple')
    K.weapon('betty', 1780, -1500, GM.TENT[4] + 16, marker='black')
    K.weapon('balloony', -300, 1660, GM.BACK_Z, marker='orange')
    K.weapon('pumper', 150, -250, GM.TABLE_Z, marker='green')
    K.weapon('splasher', -1844, 300, GM.TV_STAND[4], marker='blue')
    K.weapon('boaster', 0, 1340, 0, marker='orange')
    K.weapon('bubbleg', -300, -1250, 0, marker='green')
    ammo = {'imperius': [(-1890, -850, sz), (-500, -700, PZ), (1780, -1150, GM.TENT[4] + 16)],
            'betty': [(1700, -1450, 0), (-1550, 1500, GM.ARM_Z), (600, 1650, GM.BACK_Z), (300, -800, PZ)],
            'balloony': [(-900, 1660, GM.BACK_Z), (1550, 1650, GM.ARM_Z), (-1700, -1650, 0)],
            'pumper': [(-150, -420, GM.TABLE_Z), (800, 200, PZ), (1650, -900, 0), (-1000, 750, 0)],
            'splasher': [(-1844, -250, GM.TV_STAND[4]), (-900, -200, PZ), (1300, 1300, 0)],
            'boaster': [(-700, 1300, 0), (700, 1300, 0), (1880, 0, 0), (-600, -1700, 0)],
            'bubbleg': [(500, -1700, 0), (-1600, -300, 0), (1400, 650, 0), (200, 650, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', -1000, -1150, 0); K.ammo('nipper', 1500, -200, 0); K.ammo('nipper', 0, 800, 0)
    K.item('item_armor_padshield', -1550, 1500, GM.ARM_Z)
    K.item('item_armor_shard', 1100, 1200, GM.SEAT_Z); K.item('item_armor_shard', 400, -300, GM.TABLE_Z)
    K.item('item_speedy', 1550, 1250, GM.ARM_Z)
    K.item('holdable_floater', 1800, -1500, 0)
    K.item('item_jumper', -800, 1250, GM.SEAT_Z)
    K.station(1600, -700, 0, ang=180)
    for (x, y, z, a) in ((-1400, -1500, 0, 45), (-200, -1150, 0, 90), (600, -1600, 0, 90), (1300, -1000, 0, 135),
                         (1880, -250, 0, 180), (1300, 800, 0, 225), (-200, 820, 0, 270), (-1100, 800, 0, 300),
                         (-1600, -900, 0, 0), (-1400, 0, 0, 0), (900, 1200, GM.SEAT_Z, 270), (-200, 1700, GM.BACK_Z, 270),
                         (1800, -1300, 0, 180), (0, -400, GM.TABLE_Z, 90)):
        K.spawn(x, y, z, a)


def lights_sounds():
    K.light_grid(X0, Y0, X1, Y1, 1450, 768, 5000, color='1 0.88 0.72')
    for (x, y) in ((-700, -600), (0, -100), (700, -600), (-700, 250), (700, 250)):       # underwater
        K.light(x, y, -100, 300, '0.4 0.9 1')
    K.light(-1700, 160, 900, 400, '0.6 0.8 1')                                             # telly
    K.light(-1880, 1300, 900, 350, '0.9 0.4 1'); K.light(1000, -1600, 900, 350, '0.4 1 0.5')
    K.light(1768, -1440, 850, 450, '1 0.5 0.9')                                            # grow light in the tent
    K.light(BONG[0], BONG[1], 600, 350, '0.5 1 0.6')
    K.light(-1880, -1000, 1400, 400, '1 0.9 0.8')                                           # over the shelf
    K.light(0, 1300, 40, 200, '1 0.8 0.6')                                                  # crawl space
    K.speaker(0, -250, 0, 'ambient/water_rippling')
    K.speaker(BONG[0], BONG[1], 200, 'ambient/slime_bubbling')
    K.speaker(-1700, 160, 800, 'machine/tv_upstairs')
    K.speaker(0, 1300, 450, 'human/snoring')
    K.timer_sound(0, 0, 1700, 'ambient/police_pass', 'siren', 50, 25)
    K.timer_sound(-1900, -1700, 400, 'misc/door_buzzer', 'pizza', 70, 30)
    K.trigger_sound((-2040, -1350, SHELF[4]), (-1740, -1150, SHELF[4] + 96), 'human/applause', 'summit', wait=8)


if __name__ == '__main__':
    TX = GM.textures(K)
    GM.all_models()
    lm_shaders = LM.make(OUT)                    # Couch Lock's models + textures -> models/padlounge
    shell(); vault(); furniture(); pool(); slide(); pads(); clutter(); items(); lights_sounds()
    K.fix_items()
    TX.write_shader(extra=[lm_shaders], arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
