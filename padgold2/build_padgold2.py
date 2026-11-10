#!/usr/bin/env python3
"""Gold Rush Gulch: Flood Day (wop_padgold2) - PROTOTYPE of the reimagined padgold.

The dam at the head of the gulch has let go: Main Street is now the river, and every ride is a piece of the mining
works (spillway slide, flume, mine-cage lift, ore-cart carousel, tramway, geysers, gold-pan pool, paddle steamer).

    OUT=<dir> python3 build_padgold2.py        (design sheet + hand-over notes in README.md)

Reuses the padgold models/textures (../padgold/gold_models.py) and woplib.huts for the buildings.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'padgold')); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, cyl, hull, carve, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL, huts
import gold_models as GM
import gold2_models as G2

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
HX0, HY0, HX1, HY1 = INFO['hull']
ZTOP = 2560; SUB = -272
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1),
           worldspawn={'_ambient': '14', '_color': '1 0.95 0.88', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
GM.bind(TX)


def tx(n): return T(n)


# ------------------------------------------------------------------------------------------------ layout
# three levels: the flooded town floor (z 0), the mine mesa (384), the dam crest + abutments + tower catwalk (576)
CREST = 576
DAM = (-768, 1600, 768, 1856)                         # dam wall; abutments carry the crest level to both canyon walls
RES_F, RES_W = 544, 564                               # reservoir behind the dam: floor, water top (open to the horizon)
GATE = (-144, 1664, 144, 1856); GATE_H = 144          # gatehouse on the crest (Imperius on its roof)
SPILL = (-192, 800, 192, 1600)                        # spillway slide: crest -> plunge pool (35.8 deg)
SPILL_PUSH = [(1300, 1440), (1060, 1200), (880, 980)]; SPILL_SPEED = 520     # slide push zones (y ranges) on the spillway
PLUNGE = (-320, 400, 320, 800); PLUNGE_F = -160
WTOP = -8
RIV1 = (-192, -1912, 192, 400); RIV2 = (192, -1912, 1100, -1528); RIV_F = -32; KERB = 32    # Main Street river + east leg
RIV1_PUSH = [(0, 160), (-660, -500), (-1260, -1100)]; RIV2_PUSH = [(420, 580), (760, 900)]; RIV_SPEED = 170
LAKE = (1100, -1960, 2200, -500); LAKE_F = -224
PAN = (-1800, -1750, -1200, -1150); PAN_F = -16       # giant gold pan (octagonal splash pool)
FRONT, DEPTH, BW = 400, 400, 96                       # building fronts at x = +-400, 400 deep, 96u boardwalk
ROW = {   # name: (side, u0, u1, H, sign, paint, door centre, door width, door top)
    'saloon':  ('W', -1400, -840, 320, 'SALOON', 'yellow', -1120, 112, 128),
    'bank':    ('W', -712, -264, 256, 'BANK', 'brick', -488, 96, 128),
    'sheriff': ('W', -136, 312, 224, 'SHERIFF', 'blue', 88, 96, 128),
    'store':   ('E', -1400, -888, 224, 'GENERAL STORE', 'white', -1144, 96, 128),
    'smith':   ('E', -760, -280, 192, 'BLACKSMITH', 'grey', -520, 288, 160),
    'assay':   ('E', -152, 288, 208, 'ASSAY OFFICE', 'teal', 68, 96, 128),
}
MESA = (-2304, -700, -1400, 900, 384)
TUN = (-1960, -700, -1800, 900)                       # mine tunnel straight through the mesa, 192 high
CHAMBER = (-2200, -160, -1700, 360)                   # 224 high
PIT = (-2180, -60, -2020, 260); PIT_F = -128
LIFT = (-1400, 36, -1272, 164)                        # mine-cage elevator (func_plat) on the mesa's east face
CARTS = (-1900, 150); CART_R = 300; CART_N = 5; CART_O = 430
TRAM = (-2200, 900, -2040, 1600)                      # tramway ramp mesa (384) -> west abutment (576)
TWR = (1500, 500); R_TANK, R_CAT, Z_CAT, Z_TOP, R_CAP, Z_CAP, LEG_R = 300, 400, CREST, 896, 96, 1008, 270
STAIRT = 900; BAND_P, BAND_Q = (1472, 1600), (1296, 1424)     # switchback stairs against the east abutment
FLUME = (2000, 2128, 1600, -560, CREST, 16)           # x0, x1, y start, y end, z start, z end (14.5 deg)
SH_X = (1660, 1940); SH_Y = (-1700, -800); SH_BOW = -660; DECK = 48
CABIN = (1720, -1520, 1880, -1120); CAB_H = 160; WH = (1752, -1512, 1848, -1380)
PIER = (-1100, -980)
OUTHOUSE = (-1100, -1000, -1004, -904)
VAULT = (-384, -320, 384, 320, -1600)
CRATES = [((-48, -48, 0), (48, 48, 96)), ((48, -40, 0), (128, 40, 80)), ((-40, -40, 96), (40, 40, 176))]
FLUME_BENTS = []


def flume_z(y):
    x0, x1, ys, ye, zs, ze = FLUME
    return zs + (ze - zs) * (ys - y) / (ys - ye)


# ------------------------------------------------------------------------------------------------ models
def models():
    fac = {k: (v[4], v[5]) for k, v in ROW.items()}
    fac.update(cabin=('RIVER QUEEN', 'white'), gate=('SPILLWAY', 'grey'))
    GM.materials(TX, fac)
    GM.model_textures(TX)
    TX.material('dam', TL.grime(TL.bricks((168, 160, 148), (120, 112, 104), rows=6, cols=3, n=256, vary=10), 0.25, 3), shade=20)
    TX.material('dam_top', TL.stone((176, 170, 160), cells=8, edge=(140, 134, 126), n=256), shade=20)
    for x in range(1400, -100, -240):
        FLUME_BENTS.append(((FLUME[0] + FLUME[1]) / 2, x, int(flume_z(x - 8)) - 18, 'y'))
    ML.save('tower', GM.water_tower(R_TANK, R_CAT, Z_CAT, Z_TOP, R_CAP, Z_CAP, LEG_R))
    ML.save('smokestack', GM.smokestack())
    ML.save('headframe', GM.headframe())
    ML.save('portal', GM.mine_portal(160, 192))
    ML.save('rails', GM.rail_ring(CART_R, 0))
    ML.save('wagon', GM.wagon()); ML.save('barrels', GM.barrel_group())
    ML.save('hay3', GM.hay_bale(3)); ML.save('trough', GM.trough())
    ML.save('crates', GM.crate_stack(CRATES))
    for i in range(3): ML.save(f'geyser{i}', GM.geyser_cone(150 - 20 * i, 60 - 10 * i, seed=i))
    ML.save('steam', GM.steam_column())
    ML.save('windmill', GM.windmill_tower())
    ML.save('bar_s', GM.bar_counter(L=240)); ML.save('bar_m', GM.bar_counter(L=200)); ML.save('backbar', GM.back_bar(L=240))
    ML.save('table', GM.saloon_table()); ML.save('shelves', GM.shelves())
    ML.save('bars', GM.jail_bars(136, 160)); ML.save('forge', GM.forge())
    ML.save('lantern', GM.lantern_post())
    for i in range(3): ML.save(f'nuggets{i}', GM.nugget_pile(seed=i))
    ML.save('flume_bents', GM.flume_trestle(FLUME_BENTS))
    ML.save('piles', GM.pier_piles(SH_X[0] - LAKE[0], 120, LAKE_F, 32))
    ML.save('liftframe', G2.lift_frame(128, 520))
    ML.save('panrim', G2.pan_rim(300))
    ML.save('tram_bents', G2.tram_bents(TRAM, MESA[4] - 18))
    ML.save('damvalve', G2.dam_valve()); ML.save('sluicegate', G2.sluice_gate()); ML.save('deckgear', G2.deck_gear())
    ML.save_iqm('carts', GM.ore_carts(CART_R, CART_N, MESA[4] - CART_O))
    ML.save_iqm('sternwheel', GM.stern_wheel(110, 160))
    ML.save_iqm('windwheel', GM.windmill_wheel())


# ------------------------------------------------------------------------------------------------ shell
HOLES = {'plunge': (PLUNGE, PLUNGE_F, 'lakebed'), 'riv1': (RIV1, RIV_F, 'creekbed'), 'riv2': (RIV2, RIV_F, 'creekbed'),
         'lake': (LAKE, LAKE_F, 'lakebed'), 'pan': (PAN, PAN_F, 'gold_rock'), 'pit': (PIT, PIT_F, 'rock'),
         'lift': (LIFT, -16, 'planks_d')}
STREET = [(-FRONT, -1528, -192, 400), (192, -1528, FRONT, 400)]


def shell():
    """one thick structural slab with the water holes cut out and each hole refilled to its floor height (no basin
    walls, no void under the floor), sky hull, strata banks, reservoir to the horizon, clip on the playable edge"""
    side = tx('rock')
    for r in sub_rects((HX0, HY0, HX1, HY1), [h[0] for h in HOLES.values()] + STREET):
        K.add(box((r[0], r[1], SUB), (r[2], r[3], 0), {'top': tx('sand'), 'side': side, 'bot': CAULK}, detail=False))
    for r in STREET:
        K.add(box((r[0], r[1], SUB), (r[2], r[3], 0), {'top': tx('street'), 'side': side, 'bot': CAULK}, detail=False))
    for (r, fz, tt) in HOLES.values():
        K.add(box((r[0], r[1], SUB), (r[2], r[3], fz), {'top': tx(tt), 'side': side, 'bot': CAULK}, detail=False))
    sky = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: tx('sky')})
    K.add(box((HX0 - 32, HY0 - 32, SUB), (HX0, HY1 + 32, ZTOP), sky('e'), detail=False),
          box((HX1, HY0 - 32, SUB), (HX1 + 32, HY1 + 32, ZTOP), sky('w'), detail=False),
          box((HX0, HY0 - 32, SUB), (HX1, HY0, ZTOP), sky('n'), detail=False),
          box((HX0, HY1, SUB), (HX1, HY1 + 32, ZTOP), sky('s'), detail=False),
          box((HX0 - 32, HY0 - 32, ZTOP), (HX1 + 32, HY1 + 32, ZTOP + 32), sky('bot'), detail=False))
    for mn, mx in (((X0 - 16, Y0 - 16, 0), (X0, Y1, ZTOP)), ((X1, Y0 - 16, 0), (X1 + 16, Y1, ZTOP)),
                   ((X0 - 16, Y1, CREST), (X0, Y1 + 16, ZTOP)), ((X1, Y1, CREST), (X1 + 16, Y1 + 16, ZTOP)),
                   ((X0, Y0 - 16, 0), (X1, Y0, ZTOP)),
                   ((X0, Y1, CREST), (DAM[0], Y1 + 16, ZTOP)), ((DAM[2], Y1, CREST), (X1, Y1 + 16, ZTOP)),
                   ((DAM[0], Y1, RES_W), (DAM[2], Y1 + 16, ZTOP))):         # over the reservoir: from the water up
        K.add(box(mn, mx, CLIP))
    banks()


def banks():
    """stepped sandstone strata outside the playable edge. North of the dam line they start at crest height, and the
    three chunks behind the dam are left out so the reservoir runs to the horizon."""
    rng = np.random.default_rng(7)
    rock = {'top': tx('rock'), 'bot': CAULK, 'side': tx('strata')}
    sides = (('w', X0 - 16, HX0, Y0 - 16, Y1 + 16), ('e', X1 + 16, HX1, Y0 - 16, Y1 + 16),
             ('s', Y0 - 16, HY0, HX0, HX1), ('n', Y1 + 16, HY1, HX0, HX1))
    for (k, edge, far, a0, a1) in sides:
        sg = 1 if far > edge else -1
        a = a0
        while a < a1 - 1:
            b = min(a1, a + 512)
            hs = rng.integers(140, 260, size=8); jit = rng.integers(0, 40, size=(8, 3))
            skip = k == 'n' and DAM[0] <= a < DAM[2]
            tall = k == 'n' or (k in 'we' and a >= 1520)      # beside the crest level: first course rises past it
            z = 0; rec = 0
            for i, h in enumerate(hs):
                z1 = min(1600, z + int(h) + (CREST if tall and i == 0 else 0))
                rb = rec + int(jit[i, 0]); rt = rb + 24 + int(jit[i, 1])
                if tall and i == 0: rb = rt = 0                 # sheer face flush with the abutment edge
                ib, it = edge + sg * rb, edge + sg * rt
                if abs(far - it) < 64 or z >= 1600: break
                if not skip:
                    if k in 'we':
                        pts = [(ib, a, z), (ib, b, z), (it, a, z1), (it, b, z1), (far, a, z), (far, b, z), (far, a, z1), (far, b, z1)]
                    else:
                        pts = [(a, ib, z), (b, ib, z), (a, it, z1), (b, it, z1), (a, far, z), (b, far, z), (a, far, z1), (b, far, z1)]
                    K.add(hull(pts, rock))
                z = z1; rec = rt + 16 + int(jit[i, 2])
            a = b


# ------------------------------------------------------------------------------------------------ the dam (centrepiece)
def dam():
    x0, y0, x1, y1 = DAM
    rock = {'top': tx('rock'), 'bot': CAULK, 'side': tx('strata')}
    K.add(box((X0, y0, 0), (x0, Y1 + 16, CREST), rock), box((x1, y0, 0), (X1, Y1 + 16, CREST), rock))       # abutments
    K.reserve(((X0, y0, 0), (x0, Y1, CREST)), ((x1, y0, 0), (X1, Y1, CREST)))
    wall = [box((x0, y0, 0), (x1, y1, CREST), CAULK)]
    for bx in (-730, -530, -300, 300, 530, 730):                                                   # battered buttresses
        wall.append(hull([(bx + s, y, z) for s in (-28, 28) for (y, z) in ((y0, 0), (y0 - 120, 0), (y0, CREST), (y0 - 24, CREST))],
                         CAULK, round_pts=False))

    def dam_tex(c, n, poly):
        if n[2] > 0.7: return TX['dam_top'], ML.planar_uv(n, 256)
        if n[2] < -0.7: return None
        return TX['dam'], ML.planar_uv(n, 384)
    K.solid_piece('dam', wall, dam_tex)
    for vx in (-630, 630):                                                        # penstock valves between the buttresses
        K.custom(ML.PLACE['damvalve'], vx, y0, 0, boxes=[((-46, -156, 0), (46, -64, 64)), ((-22, -64, 70), (22, 0, 114)),
                                                          ((-14, -32, 114), (14, 0, 520))])
    K.light(0, y0 - 300, 300, 300, '1 0.88 0.72')                                 # the dam face is on the shade side
    for vx in (-630, 630): K.light(vx, y0 - 220, 160, 260, '1 0.88 0.72')
    # reservoir: solid to its floor, water out to the sky wall, one 16u step back up to the crest
    K.add(box((x0, y1, 0), (x1, HY1, RES_F), {'top': tx('lakebed'), 'side': tx('strata'), 'bot': CAULK}))
    step = box((x0, y1, RES_F), (x1, y1 + 32, RES_F + 16), {'top': tx('pool_wall'), 'side': tx('pool_wall'), 'bot': CAULK})
    K.add(step)
    K.water_box((x0, y1, RES_F), (x1, HY1, RES_W), tx('water'), cutters=[step])
    # gatehouse on the crest
    gx0, gy0, gx1, gy1 = GATE
    op = {'s': [(-44, 44, CREST, CREST + 112)], 'n': [(-60, 60, CREST + 48, CREST + 104)],
          'e': [(gy0 + 60, gy1 - 60, CREST + 48, CREST + 104)], 'w': [(gy0 + 60, gy1 - 60, CREST + 48, CREST + 104)]}
    bs = huts.brushes(gx0, gy0, gx1, gy1, CREST, GATE_H, op, floor=False)
    K.solid_piece('gatehouse', bs, huts.texfn(TX, gx0, gy0, gx1, gy1, CREST, GATE_H, front='s', fac='fac_gate',
                                               side='side_gate', roof='tin'), hidden=bs)
    zr = CREST + GATE_H + 16
    K.jumppad(430, 1728, CREST, land=(0, 1760, zr), apex=zr + 130, name='pad_gatehouse', edges=[(gx1, 1740, zr)])
    K.light(0, 1760, CREST + 100, 250, '1 0.85 0.6')
    K.trigger_sound((-60, 1700, zr + 8), (60, 1820, zr + 72), 'human/applause', 'top_applause', wait=20)
    # spillway slide: one plain walkable ramp with white water, kerbs both sides
    sx0, sy0, sx1, sy1 = SPILL
    K.ramp(sx0, sy0, sx1, sy1, 0, CREST, 'n', {'top': tx('flume'), 'side': tx('pool_wall'), 'bot': CAULK}, base=0)
    for a, b in ((sx0 - 24, sx0), (sx1, sx1 + 24)):
        K.add(hull([(x, y, z) for x in (a, b) for (y, zt) in ((sy0, 0), (sy1, CREST)) for z in (0, zt + 28)],
                   {'top': tx('timber'), 'side': tx('pool_wall'), 'bot': CAULK}, round_pts=False))
    K.reserve(((sx0 - 24, sy0, 0), (sx1 + 24, sy1, CREST)))
    K.custom(ML.PLACE['sluicegate'], 0, sy1, CREST, boxes=[((s * 236 - 12, 4, 0), (s * 236 + 12, 28, 280)) for s in (-1, 1)] +
             [((-248, 2, 280), (248, 30, 300)), ((-224, 8, 170), (224, 24, 262))])
    K.route('crest', (-600, 1728, CREST), (600, 1728, CREST))
    K.speaker(0, 1000, 200, 'ambient/water_flowing')
    # the slide push: three sloped zones lying on the ramp (not cut into it), none at the crest lip or the pool edge
    deg = math.degrees(math.atan2(CREST, sy1 - sy0))
    zs = lambda y: CREST * (y - sy0) / (sy1 - sy0)
    for k, (ya, yb) in enumerate(SPILL_PUSH):
        K.current((sx0, ya, zs(ya)), (sx1, yb, zs(yb) + 64), 270, speed=SPILL_SPEED, wait=0.3, name=f'spill{k}', pitch=deg,
                  brush=hull([(x, y, zs(y) + dz) for x in (sx0, sx1) for y in (ya, yb) for dz in (2, 64)], TRIG, round_pts=False))


# ------------------------------------------------------------------------------------------------ water
def water():
    # plunge pool under the spillway: 16u stair out on the east side, and you can swim over the weir into the river
    px0, py0, px1, py1 = PLUNGE
    st = K.stairs16(192, py0, px1, py0 + 320, PLUNGE_F, 0, 's', {'top': tx('planks_d'), 'side': tx('timber')})
    K.keep_clear(192, py0 - 112, px1, py0, 0)
    K.water_box((px0, py0, PLUNGE_F), (px1, py1, WTOP), tx('water'), cutters=st)
    # Main Street river (wade-deep) with a 16u kerb step along both banks, east leg to the lake
    kt = {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK}
    k1 = [box((RIV1[0], RIV1[1], RIV_F), (RIV1[0] + KERB, RIV1[3], -16), kt),
          box((RIV1[2] - KERB, RIV2[3], RIV_F), (RIV1[2], RIV1[3], -16), kt),
          box((RIV1[0] + KERB, RIV1[1], RIV_F), (RIV1[2], RIV1[1] + KERB, -16), kt)]
    k2 = [box((RIV2[0], RIV2[1], RIV_F), (RIV2[2], RIV2[1] + KERB, -16), kt),
          box((RIV2[0], RIV2[3] - KERB, RIV_F), (RIV2[2], RIV2[3], -16), kt)]
    K.add(*k1); K.add(*k2)
    K.water_box((RIV1[0], RIV1[1], RIV_F), (RIV1[2], RIV1[3], WTOP), tx('creek'), cutters=k1)
    K.water_box((RIV2[0], RIV2[1], RIV_F), (RIV2[2], RIV2[3], WTOP), tx('creek'), cutters=k2)
    for y in (200, -600, -1400): K.speaker(0, y, 16, 'ambient/water_flowing')
    # gentle downstream current: short zones in mid-channel, >= 64u off both kerb steps, none near the weir or the lake
    for k, (ya, yb) in enumerate(RIV1_PUSH):
        K.current((-96, ya, RIV_F + 4), (96, yb, WTOP), 270, speed=RIV_SPEED, wait=0.4, name=f'riv1_{k}')
    for k, (xa, xb) in enumerate(RIV2_PUSH):
        K.current((xa, RIV2[1] + 96, RIV_F + 4), (xb, RIV2[3] - 96, WTOP), 0, speed=RIV_SPEED, wait=0.4, name=f'riv2_{k}')
    # lake: steps out on the west shore; steamer hull, pier and rocks stand on the lake floor
    x0, y0, x1, y1 = LAKE
    ls = K.stairs16(x0, -1500, x0 + 448, -1300, LAKE_F, 0, 'w', {'top': tx('boardwalk'), 'side': tx('timber')})
    K.keep_clear(x0 - 112, -1500, x0, -1300, 0)
    cut = list(ls) + steamer_hull() + [pier_brush()] + lake_rocks()
    K.add(*lake_rocks())
    K.water_box((x0, y0, LAKE_F), (x1, y1, WTOP), tx('water'), cutters=cut)
    K.speaker(1650, -1000, 16, 'ambient/water_rippling')
    # the giant gold pan: square hole trimmed to an octagon, 8u of water over gold-veined rock
    px0, py0, px1, py1 = PAN
    c = 176
    corners = []
    for (cx, cy, sx, sy) in ((px0, py0, 1, 1), (px1, py0, -1, 1), (px1, py1, -1, -1), (px0, py1, 1, -1)):
        corners.append(hull([(cx, cy, z) for z in (PAN_F, 0)] + [(cx + sx * c, cy, z) for z in (PAN_F, 0)] +
                            [(cx, cy + sy * c, z) for z in (PAN_F, 0)], {'top': tx('sand'), 'side': tx('iron'), 'bot': CAULK}))
    corners.append(cyl((px0 + px1) / 2, (py0 + py1) / 2, 64, PAN_F, 4, {'top': tx('gold_rock'), 'side': tx('gold_rock'), 'bot': CAULK}, 8, phase=0))   # the big nugget
    K.add(*corners)
    K.water_box((px0, py0, PAN_F), (px1, py1, -4), tx('creek'), cutters=corners)
    pcx, pcy = (px0 + px1) / 2, (py0 + py1) / 2
    K.custom(ML.PLACE['panrim'], pcx, pcy, 0, occupy=False)
    for i, (dx, dy) in enumerate(((-150, 90), (140, 120), (60, -170))):
        K.custom(ML.PLACE[f'nuggets{i}'], pcx + dx, pcy + dy, PAN_F, occupy=False)


def pier_brush():
    return box((LAKE[0], PIER[0], LAKE_F), (SH_X[0], PIER[1], 32), {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK})


def steamer_hull():
    mid = SH_Y[0] + 440
    a = wopmap.prism([(SH_X[0], SH_Y[0]), (SH_X[1], SH_Y[0]), (SH_X[1], mid), (SH_X[0], mid)], LAKE_F, DECK, CAULK)
    b = wopmap.prism([(SH_X[0], mid), (SH_X[1], mid), (SH_X[1], SH_Y[1]), ((SH_X[0] + SH_X[1]) / 2, SH_BOW), (SH_X[0], SH_Y[1])],
                     LAKE_F, DECK, CAULK)
    return [a, b]


def lake_rocks():
    out = []
    for (x, y, r, top, seed) in ((1350, -1850, 90, 70, 1), (2080, -1800, 85, 90, 2), (1400, -640, 90, 60, 3)):
        g = np.random.default_rng(seed)
        bot = [(x + r * 1.15 * math.cos(a) * g.uniform(0.85, 1.1), y + r * 1.15 * math.sin(a) * g.uniform(0.85, 1.1), LAKE_F)
               for a in np.linspace(0, 2 * math.pi, 9, endpoint=False)]
        tp = [(x + r * 0.7 * math.cos(a + 0.3), y + r * 0.7 * math.sin(a + 0.3), top + g.uniform(-12, 12))
              for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)]
        out.append(hull(bot + tp, {'top': tx('rock'), 'side': tx('strata'), 'bot': CAULK}))
    return out


# ------------------------------------------------------------------------------------------------ the flooded town
def town():
    for side in 'WE':
        R = huts.Row(side, FRONT, DEPTH)
        b = R.box(-1420, -BW, 0, 330, 0, 16, {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK})
        K.add(b); K.reserve(b)
        for u in (-1300, -800, -200, -30):
            K.custom(ML.PLACE['lantern'], R.x(-BW - 20), u, 0, boxes=[((-6, -6, 0), (6, 6, 150))])
    for name in ROW: building(name)
    outhouse()


def building(name):
    side, u0, u1, H, sign, paint, dc, dw, dtop = ROW[name]
    R = huts.Row(side, FRONT, DEPTH)
    x0, y0, x1, y1 = R.rect(u0, u1)
    mid = (u0 + u1) / 2
    op = {R.front: [(dc - dw / 2, dc + dw / 2, 16, dtop)]}
    if name != 'smith':
        for s in (-1, 1):
            wy = dc + s * (dw / 2 + 90)
            if u0 + 40 < wy - 36 and wy + 36 < u1 - 40: op[R.front].append((wy - 36, wy + 36, 56, 116))
    if name == 'saloon':
        op[R.front].append((dc - 50, dc + 50, 144, 256))
        op[R.back] = [(u0 + 310, u0 + 406, 16, 128)]
    if name in ('bank', 'store'): op[R.back] = [(u0 + 60, u0 + 156, 16, 128)]
    bs = huts.brushes(x0, y0, x1, y1, 0, H, op)
    extra = []
    zA = 128 if name == 'saloon' else min(176, H - 32)
    if name == 'saloon':
        extra.append(R.box(u0 + 16, 16, 128, u1 - 16, 128, 144))                 # gallery along the front wall
        extra.append(R.box(u0, -BW, 128, u1, 0, 144))                            # balcony over the boardwalk
        for pu in np.linspace(u0 + 12, u1 - 12, 5): extra.append(R.box(pu - 6, -BW, 16, pu + 6, -BW + 12, 128))
    else:
        extra.append(R.box(u0 + 8, -BW, zA, u1 - 8, 0, zA + 12))                 # awning
        for pu in (u0 + 20, mid, u1 - 20):
            if abs(pu - dc) >= dw / 2 + 12: extra.append(R.box(pu - 6, -BW, 16, pu + 6, -BW + 12, zA))
    if name == 'bank':                                                           # vault room in the back corner
        extra += [R.box(u1 - 200, 200, 16, u1 - 184, DEPTH - 16, H), R.box(u1 - 184, 200, 16, u1 - 130, 216, H),
                  R.box(u1 - 66, 200, 16, u1 - 16, 216, H), R.box(u1 - 130, 200, 128, u1 - 66, 216, H)]
    if name == 'sheriff': extra.append(R.box(mid - 8, 240, 16, mid + 8, DEPTH - 16, H))    # wall between the cells
    K.solid_piece('b_' + name, bs + extra, huts.texfn(TX, x0, y0, x1, y1, 0, H, front=R.front, fac='fac_' + name,
                                                        side='side_' + name, roof='tin' if H < 300 else 'shingle'),
                  hidden=bs + extra)
    xa, xb = R.span(-BW - 64, -BW)
    K.keep_clear(xa, dc - dw / 2 - 16, xb, dc + dw / 2 + 16, 0)
    K.route(f'{name}_door', (R.x(-BW - 40), dc, 0), (R.x(70), dc, 16))
    K.light(R.x(DEPTH / 2), mid, min(H - 40, 200), 420, '1 0.85 0.6')
    K.light(R.x(60), mid, 90, 240, '1 0.85 0.6')
    interior(name, R, u0, u1, H, mid)
    pu = u1 - (56 if name == 'bank' else 90)                                     # roof pad from the FAR bank, over the river
    K.jumppad(R.x(-2 * FRONT + BW + 74), pu, 0, land=(R.x(200), pu, H + 16), apex=H + 16 + 150, name=f'pad_{name}',
              edges=[(R.x(0), pu, H + 16), (R.x(-BW), pu, zA + 16)])


def interior(name, R, u0, u1, H, mid):
    A = R.ang
    if name == 'saloon':
        xa, xb = R.span(128, DEPTH - 16)
        K.stairs16(xa, u1 - 112, xb, u1 - 16, 16, 144, R.out, {'top': tx('planks'), 'side': tx('planks_d')})
        K.route('saloon_stair', (R.x(300), u1 - 170, 16), (R.x(70), u1 - 64, 144))
        K.custom(ML.PLACE['backbar'], R.x(DEPTH - 41), u0 + 156, 16, angle=A, boxes=[((-24, -120, 0), (0, 120, 180))])
        K.custom(ML.PLACE['bar_s'], R.x(DEPTH - 126), u0 + 156, 16, angle=A, boxes=[((-28, -120, 0), (28, 120, 64))])
        K.custom(ML.PLACE['table'], R.x(190), u0 + 380, 16, cyls=[(0, 0, 66, 0, 40)])
    elif name == 'bank':
        K.custom(ML.PLACE['bar_m'], R.x(170), u0 + 130, 16, angle=A, boxes=[((-28, -100, 0), (28, 100, 64))])
        K.custom(ML.PLACE['nuggets1'], R.x(340), u1 - 60, 16)
        K.light(R.x(300), u1 - 100, 120, 200, '1 0.85 0.5')
    elif name == 'store':
        for uu, da in ((u0 + 34, 90), (u1 - 34, 270)):
            K.custom(ML.PLACE['shelves'], R.x(210), uu, 16, angle=da, boxes=[((-18, -150, 0), (18, 150, 200))])
        K.custom(ML.PLACE['barrels'], R.x(300), mid + 40, 16, cyls=[(28, 24, 54, 0, 144)])
    elif name == 'sheriff':
        for uu in (u0 + 84, u1 - 84):
            K.custom(ML.PLACE['bars'], R.x(240), uu, 16, angle=A, occupy=False)
        K.add(R.box(u0 + 16, 236, 16, u0 + 152, 244, H, CLIP), R.box(u1 - 152, 236, 16, u1 - 16, 244, H, CLIP))
    elif name == 'smith':
        K.custom(ML.PLACE['forge'], R.x(280), mid, 16, angle=90,
                 boxes=[((-70, -50, 0), (70, 50, 48)), ((96, -18, 0), (170, 18, 40))], cyls=[(0, 20, 36, 48, 160)])
        K.speaker(R.x(280), mid, 80, 'ambient/fire_crackling')
        K.light(R.x(240), mid, 80, 300, '1 0.55 0.25')
    elif name == 'assay':
        K.custom(ML.PLACE['bar_m'], R.x(250), mid, 16, angle=A, boxes=[((-28, -100, 0), (28, 100, 64))])
        K.custom(ML.PLACE['nuggets2'], R.x(250), mid, 80, occupy=False)


def outhouse():
    x0, y0, x1, y1 = OUTHOUSE
    door = ((x0 + x1) / 2 - 24, (x0 + x1) / 2 + 24)
    bs = huts.brushes(x0, y0, x1, y1, 0, 160, {'n': [(door[0], door[1], 0, 112)]}, floor=False)
    K.solid_piece('outhouse', bs, huts.texfn(TX, x0, y0, x1, y1, 0, 160, side='wood_g', roof='tin'), hidden=bs)
    K.keep_clear(door[0] - 32, y1, door[1] + 32, y1 + 100, 0)
    K.secret((x0 + 16, y0 + 16, 0), (x1 - 16, y1 - 40, 72), dest=(0, VAULT[1] + 96, VAULT[4]), angle=90,
             name='outhouse', approach='top')
    K.trigger_sound((door[0], y1 + 8, 0), (door[1], y1 + 56, 64), 'misc/toilet_flush', 'flush', wait=10)


# ------------------------------------------------------------------------------------------------ mine mesa
def mesa():
    x0, y0, x1, y1, ztop = MESA
    base = box((x0, y0, 0), (x1, y1, ztop), CAULK)
    cutters = [box((TUN[0], TUN[1], 0), (TUN[2], TUN[3], 192), CAULK),
               box((CHAMBER[0], CHAMBER[1], 0), (CHAMBER[2], CHAMBER[3], 224), CAULK)]
    for p in carve(base, cutters):
        for f in p.faces: f.tex = tx('rock') if abs(f.n[2]) > 0.7 else tx('strata')
        K.add(p)
    K.reserve(((x0, y0, 0), (x1, y1, ztop)))
    tc = (TUN[0] + TUN[2]) / 2
    K.keep_clear(TUN[0] - 48, y0 - 160, TUN[2] + 48, y0, 0); K.keep_clear(TUN[0] - 48, y1, TUN[2] + 48, y1 + 160, 0)
    K.custom(ML.PLACE['portal'], tc, y0 - 18, 0, occupy=False)
    K.custom(ML.PLACE['portal'], tc, y1 + 18, 0, angle=180, occupy=False)
    K.add(sign_box((TUN[0] - 40, y0 - 4, 236), (TUN[2] + 40, y0, 296), tx('sign_mine'), 1024, 192, facing='s', edge=tx('timber')))
    K.route('mine_through', (tc, y0 - 100, 0), (tc, y1 + 100, 0))
    px0, py0, px1, py1 = PIT
    K.stairs16(px0, py0, px0 + 80, py0 + 256, PIT_F, 0, 's', {'top': tx('planks_d'), 'side': tx('rock')})
    K.route('mine_pit', (px0 + 40, py0 - 50, 0), (px1 - 40, py1 - 40, PIT_F))
    for (lx, ly) in ((tc, -500), (tc, -250), (tc, 100), (-2100, 100), (tc, 600), (tc, 800)): K.light(lx, ly, 150, 260, '1 0.8 0.5')
    K.light(-2060, 100, -40, 250, '1 0.8 0.5')
    # mine-cage elevator on the east face (func_plat; bots ride these)
    lx0, ly0, lx1, ly1 = LIFT
    K.elevator(lx0, ly0, lx1, ly1, 0, ztop, {'top': tx('planks'), 'side': tx('iron'), 'bot': tx('iron')}, name='minecage')
    K.reserve(((lx0, ly0, 0), (lx1 + 24, ly1, ztop + 140)))
    K.keep_clear(lx1, ly0 - 32, lx1 + 140, ly1 + 32, 0)
    K.custom(ML.PLACE['liftframe'], (lx0 + lx1) / 2, (ly0 + ly1) / 2, 0, occupy=False,
             cyls=[(76, -76, 8, 0, 520), (76, 76, 8, 0, 520)])
    # top: ridable ore-cart carousel round the Balloony, headframe, tramway up to the dam's west abutment
    cx, cy = CARTS
    K.custom(ML.PLACE['rails'], cx, cy, ztop, occupy=False)
    brushes = [box((cx - 8, cy - 8, CART_O - 8), (cx + 8, cy + 8, CART_O + 8), 'common/origin')]
    for k in range(CART_N):
        a = 2 * math.pi * k / CART_N
        Rm = np.array([[-math.sin(a), -math.cos(a)], [math.cos(a), -math.sin(a)]])
        c = np.array([cx + CART_R * math.cos(a), cy + CART_R * math.sin(a)])
        brushes.append(hull([tuple(c + Rm @ np.array([px, py])) + (z,) for px in (-58, 58) for py in (-34, 34)
                             for z in (ztop + 16, ztop + 68)], WCLIP, round_pts=False))
    K.ent('func_rotating', brushes=brushes, model2=ML.IQM['carts'], speed=20, spawnflags=0)
    K.spots['movers'].append(dict(cls='func_rotating', centre=[cx, cy, CART_O], model=ML.IQM['carts']))
    K.speaker(cx, cy, ztop + 80, 'machine/mechanics')
    K.custom(ML.PLACE['headframe'], -1560, -520, ztop, cyls=[(sx, sy, 10, 0, 300) for sx in (-70, 70) for sy in (-80, 80)])
    tx0, ty0, tx1, ty1 = TRAM
    K.ramp(tx0, ty0, tx1, ty1, ztop, CREST, 'n', {'top': tx('planks'), 'side': tx('timber'), 'bot': tx('planks_d')},
           base=ztop - 16, route='tramway')
    K.custom(ML.PLACE['tram_bents'], 0, 0, 0, occupy=False)


# ------------------------------------------------------------------------------------------------ water tower + stairs
def tower():
    tx0, ty0 = TWR
    K.custom(ML.PLACE['tower'], tx0, ty0, 0, occupy=False)
    ang = np.linspace(0, 2 * math.pi, 8, endpoint=False)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        b0 = [(tx0 + math.cos(a) * (LEG_R + 60) + 14 * math.cos(t), ty0 + math.sin(a) * (LEG_R + 60) + 14 * math.sin(t), 0) for t in ang]
        b1 = [(tx0 + math.cos(a) * LEG_R + 14 * math.cos(t), ty0 + math.sin(a) * LEG_R + 14 * math.sin(t), Z_CAT - 16) for t in ang]
        K.add(hull(b0 + b1, WCLIP, round_pts=False))
    for i in range(16):
        a0 = math.radians(-11.25 + 22.5 * i); a1 = a0 + math.radians(22.5)
        K.add(hull([(tx0 + r * math.cos(a), ty0 + r * math.sin(a), z) for r in (R_TANK, R_CAT) for a in (a0, a1)
                    for z in (Z_CAT - 16, Z_CAT)], WCLIP, round_pts=False))
    K.add(cyl(tx0, ty0, R_TANK - 10, Z_CAT, Z_TOP, WCLIP, 16, phase=0))
    a16 = np.linspace(0, 2 * math.pi, 16, endpoint=False)
    K.add(hull([(tx0 + (R_TANK + 6) * math.cos(t), ty0 + (R_TANK + 6) * math.sin(t), Z_TOP) for t in a16] +
               [(tx0 + R_CAP * math.cos(t), ty0 + R_CAP * math.sin(t), Z_CAP) for t in a16], WCLIP, round_pts=False))
    K.occupy_r(tx0, ty0, R_TANK + 10, Z_CAT, Z_CAP)
    K.reserve(((tx0 - LEG_R - 80, ty0 - LEG_R - 80, 0), (tx0 + LEG_R + 80, ty0 + LEG_R + 80, Z_CAT)))
    # plank bridge: catwalk north chord -> east abutment (the 576 level is one ring: dam crest, abutments, catwalk)
    lt = {'top': tx('planks'), 'side': tx('timber'), 'bot': tx('planks_d')}
    K.add(box((tx0 - 64, ty0 + 393, Z_CAT - 16), (tx0 + 64, DAM[1], Z_CAT), lt))
    K.route('tower_bridge', (tx0, ty0 + 350, Z_CAT), (tx0, DAM[1] + 80, CREST))
    K.jumppad(tx0, ty0 - 640, 0, land=(tx0, ty0 - 352, Z_CAT), apex=Z_CAT + 130, name='pad_catwalk', edges=[(tx0, ty0 - R_CAT, Z_CAT)])
    rl = 230
    zl = Z_TOP + (R_TANK + 6 - rl) / (R_TANK + 6 - R_CAP) * (Z_CAP - Z_TOP)
    K.jumppad(tx0 - 376, ty0, Z_CAT, land=(tx0 - rl, ty0, zl), apex=Z_CAP + 170, name='pad_cap', edges=[(tx0 - R_TANK - 6, ty0, Z_TOP)])
    # second way onto the cap straight from the yard west of the tower (bots ignored the two-pad chain to the Betty)
    K.jumppad(tx0 - 630, ty0, 0, land=(tx0 - 48, ty0, Z_CAP), apex=Z_CAP + 190, name='pad_cap_yard',
              edges=[(tx0 - R_CAT, ty0, Z_CAT), (tx0 - R_TANK - 6, ty0, Z_TOP)])
    stair_tower()


def stair_tower():
    """switchback 16u stairs against the east abutment: four flights, top landing steps straight onto the abutment"""
    x0 = STAIRT; xa, xb = x0 + 96, x0 + 96 + 288; xe = xb + 96
    pl = {'top': tx('planks'), 'side': tx('planks_d')}
    K.stairs16(xa, BAND_Q[0], xb, BAND_Q[1], 0, 144, 'e', pl)
    K.stairs16(xa, BAND_P[0], xb, BAND_P[1], 144, 288, 'w', pl, base=0)
    K.stairs16(xa, BAND_Q[0], xb, BAND_Q[1], 288, 432, 'e', pl, thick=24)
    K.stairs16(xa, BAND_P[0], xb, BAND_P[1], 432, 576, 'w', pl, thick=24)
    lt = {'top': tx('planks'), 'side': tx('timber'), 'bot': tx('planks_d')}
    for z in (144, 432): K.add(box((xb, BAND_Q[0], z - 16), (xe, BAND_P[1], z), lt))
    for z in (288, 576): K.add(box((x0, BAND_Q[0], z - 16), (xa, BAND_P[1], z), lt))
    K.reserve(((x0, BAND_Q[0], 0), (xe, BAND_P[1], 600)))
    K.keep_clear(x0 - 16, BAND_Q[0] - 112, xa + 64, BAND_Q[0], 0)
    K.route('dam_stairs', (xa - 40, BAND_Q[0] - 60, 0), (x0 + 48, DAM[1] + 80, CREST))
    posts = [(x, y) for x in (x0 + 8, xa - 8, xb + 8, xe - 8) for y in (BAND_Q[0] + 8, BAND_P[1] - 8)]
    mx_, my_ = (x0 + xe) / 2, (BAND_Q[0] + BAND_P[1]) / 2
    ML.save('stairposts', GM.stair_posts([(x - mx_, y - my_) for x, y in posts], 560))
    K.custom(ML.PLACE['stairposts'], mx_, my_, 0, occupy=False)


# ------------------------------------------------------------------------------------------------ flume
def flume():
    """log flume: east abutment (576) -> along the east canyon wall -> into the lake; walkable both ways (14.5 deg)"""
    x0, x1, ys, ye, zs, ze = FLUME
    wall = {'top': tx('timber'), 'side': tx('timber'), 'bot': tx('timber')}
    floor = {'top': tx('flume'), 'side': tx('timber'), 'bot': tx('timber')}
    ym = -100                                                     # south of here the flume is solid to the ground
    zm = flume_z(ym)

    def seg(ya, yb, xa, xb, lo, hi, tex, solid=False):
        pts = []
        for y in (ya, yb):
            for x in (xa, xb):
                pts += [(x, y, 0 if solid else flume_z(y) + lo), (x, y, flume_z(y) + hi)]
        return hull(pts, tex, round_pts=False)
    K.add(seg(ys, ym, x0, x1, -16, 0, floor), seg(ys, ym, x0 - 16, x0, -16, 48, wall), seg(ys, ym, x1, x1 + 16, -16, 48, wall),
          seg(ym, ye, x0, x1, 0, 0, floor, True), seg(ym, ye, x0 - 16, x0, 0, 48, wall, True), seg(ym, ye, x1, x1 + 16, 0, 48, wall, True))
    K.reserve(((x0 - 16, ye, 0), (x1 + 16, ym, zm + 48)))
    K.custom(ML.PLACE['flume_bents'], 0, 0, 0, occupy=False)
    for (x, y, zt, ax) in FLUME_BENTS:
        for s in (-1, 1): K.add(box((x + s * 56 - 7, y - 7, 0), (x + s * 56 + 7, y + 7, zt), WCLIP))
    K.route('flume_walk', ((x0 + x1) / 2, ye + 200, flume_z(ye + 200)), ((x0 + x1) / 2, ys + 80, CREST))
    K.speaker((x0 + x1) / 2, 500, flume_z(500) + 40, 'ambient/water_flowing')
    K.add(sign_box((x0 - 20, ys + 8, CREST + 84), (x1 + 20, ys + 12, CREST + 124), tx('sign_flume'), 512, 128, facing='s', edge=tx('timber')))
    for px in (x0 - 32, x1 + 20):
        K.add(box((px, ys + 4, CREST), (px + 12, ys + 16, CREST + 124), {'top': tx('timber'), 'side': tx('timber'), 'bot': CAULK}))


# ------------------------------------------------------------------------------------------------ steamer
def steamer():
    a, b = steamer_hull()

    def hull_tex(c, n, poly):
        if n[2] > 0.7: return TX['floor'], ML.planar_uv(n, 256)
        if n[2] < -0.7: return None
        return TX['hull'], (lambda p: ((p[0] + p[1]) / 256.0, (DECK - p[2]) / (DECK - LAKE_F)))
    K.solid_piece('steamer_aft', [a], hull_tex, hidden=[a, b])
    K.solid_piece('steamer_fore', [b], hull_tex, hidden=[a, b])
    K.add(pier_brush())
    K.add(box((LAKE[0] - 32, PIER[0], 0), (LAKE[0], PIER[1], 16), {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK}))
    K.custom(ML.PLACE['piles'], LAKE[0], (PIER[0] + PIER[1]) / 2, 0, occupy=False)
    K.reserve(((LAKE[0] - 32, PIER[0], 0), (SH_X[0], PIER[1], 32)))
    K.keep_clear(LAKE[0] - 140, PIER[0], LAKE[0] - 32, PIER[1], 0)
    K.route('pier', (LAKE[0] - 96, (PIER[0] + PIER[1]) / 2, 0), (SH_X[0] + 40, (PIER[0] + PIER[1]) / 2, DECK))
    cx0, cy0, cx1, cy1 = CABIN
    dc = (cx0 + cx1) / 2
    win = [(cy0 + 60, cy0 + 130, DECK + 52, DECK + 104), (cy0 + 220, cy0 + 290, DECK + 52, DECK + 104)]
    op = {'s': [(dc - 30, dc + 30, DECK, DECK + 112)], 'e': win, 'w': win + [(cy1 - 80, cy1 - 20, DECK, DECK + 112)]}
    bs = huts.brushes(cx0, cy0, cx1, cy1, DECK, CAB_H, op, floor=False)
    K.solid_piece('cabin', bs, huts.texfn(TX, cx0, cy0, cx1, cy1, DECK, CAB_H, front='s', side='side_cabin', roof='floor'), hidden=bs)
    K.stairs16(1740, cy1, 1860, cy1 + 352, DECK, DECK + CAB_H + 16, 's', {'top': tx('planks'), 'side': tx('planks_d')})
    zr = DECK + CAB_H + 16
    K.route('steamer_stairs', (1700, cy1 + 60, DECK), (1800, cy1 - 80, zr))
    w0, wy0, w1, wy1 = WH
    bs = huts.brushes(w0, wy0, w1, wy1, zr, 128, {'n': [(1776, 1824, zr, zr + 112)]}, floor=False)
    K.solid_piece('wheelhouse', bs, huts.texfn(TX, w0, wy0, w1, wy1, zr, 128, side='white', roof='floor'), hidden=bs)
    for sx in (1736, 1864): K.custom(ML.PLACE['smokestack'], sx, cy0 + 260, zr, cyls=[(0, 0, 20, 0, 300)])
    K.jumppad(1800, cy0 + 280, zr, land=(1800, (wy0 + wy1) / 2, zr + 144), apex=zr + 264, name='pad_wheelhouse', edges=[(1800, wy1, zr + 144)])
    K.jumppad(900, -1180, 0, land=(1800, cy1 - 70, zr), apex=zr + 260, name='pad_shore_deck', edges=[(cx0, cy1 - 70, zr)])
    K.reserve(((SH_X[0], SH_Y[0], LAKE_F), (SH_X[1], SH_BOW, DECK)), ((cx0, cy0, DECK), (cx1, cy1, zr)))
    K.light(dc, (cy0 + cy1) / 2, DECK + 120, 300, '1 0.85 0.6')
    K.custom(ML.PLACE['deckgear'], 1720, -1590, DECK, cyls=[(0, 0, 26, 0, 58), (170, -50, 12, 0, 32), (170, 40, 12, 0, 32)])
    K.rotating_model2(ML.IQM['sternwheel'], (1800, SH_Y[0] - 128, 64), 40, axis='x')


# ------------------------------------------------------------------------------------------------ geysers + dressing
def geysers():
    spots = ((-1150, 1250, (-1700, 760, MESA[4]), MESA[4] + 170, 'pad_geyser_mesa', [(-1543, MESA[3], MESA[4])]),
             (-415, 1250, (-415, 1728, CREST), CREST + 150, 'pad_geyser_dam', [(-415, DAM[1], CREST)]),
             (-1000, 1480, None, None, None, None))
    for i, (gx, gy, land, apex, name, edges) in enumerate(spots):
        r_, h_ = 150 - 20 * i, 60 - 10 * i
        K.custom(ML.PLACE[f'geyser{i}'], gx, gy, 0, cyls=[] if name else [(0, 0, r_ * 0.6, 0, h_)])
        K.custom(ML.PLACE['steam'], gx, gy, 0 if name else h_, lit=False, occupy=False)
        if name: K.jumppad(gx, gy, 0, land=land, apex=apex, name=name, edges=edges)
    K.speaker(-900, 1300, 40, 'ambient/water_bubbling')


def dressing():
    """a few natural pieces only (water-park rule: no props added just for sightlines)"""
    rng = np.random.default_rng(11)
    K.custom(ML.PLACE['windmill'], 1050, 950, 0, cyls=[(sx * 66, sy * 66, 8, 0, 200) for sx in (-1, 1) for sy in (-1, 1)])
    K.rotating_model2(ML.IQM['windwheel'], (1050, 974, 450), 60, axis='y')
    K.custom(ML.PLACE['trough'], 1190, 950, 0, angle=90, boxes=[((-90, -24, 0), (90, 24, 40))])
    wb = [((-150, -60, 0), (150, 60, 160))]
    for (x, y, a) in ((-1100, -300, 80), (1150, -150, 20), (-650, 1150, 10), (1000, -820, -30)):
        K.prop(ML.PLACE['wagon'], x, y, 0, boxes=wb, angle=a, search=160)
    for (x, y) in ((-950, 500), (950, 300), (-1250, -850), (600, 1250), (1800, 1250)):
        K.prop(ML.PLACE['barrels'], x, y, 0, cyls=[(28, 24, 54, 0, 144)], search=160)
    for (x, y) in ((-1000, 60), (1250, -600), (-950, -1650), (1950, 1000)):
        K.prop(ML.PLACE['hay3'], x, y, 0, boxes=[((-48, -28, 0), (68, 28, 120))], search=160)
    for (x, y) in ((-900, 900), (1250, 1100), (-2100, -1000)):
        K.prop(ML.PLACE['crates'], x, y, 0, boxes=CRATES, search=160)
    for (x, y) in ((-2150, -1900), (-950, -1950), (2150, -300), (2230, 1400), (-1300, 1500), (700, 1500), (-2200, 1300),
                   (850, -1300), (-1250, 700), (1860, 250)):
        K.catalog('pad_westernset/cactus.md3', x, y, 0, scale=float(rng.uniform(0.75, 1.0)), lit=True)
    for i, (x, y) in enumerate(((1750, 1350), (1860, 1400), (1980, 1350))):
        K.catalog(f'pad_westernset/tombstone{i % 3 + 1}.md3', x, y, 0, scale=0.9, angle=270 + rng.uniform(-10, 10))


def fill():
    """fill lights for the shade sides (sun in the west-south-west): east faces of the mesa and the tramway, the west
    boardwalk under the awnings, behind the east row, under the water tower and flume, the canyon edges, the lake bed"""
    c = '1 0.88 0.72'
    for y in (-600, -330, 330, 620, 850): K.light(-1320, y, 130, 320, c)                 # mesa east face (lift at y 36..164)
    K.light(-1220, 100, 130, 260, c)
    for y in (1050, 1350): K.light(-1960, y, 140, 300, c)                                # east of the tramway
    K.light(-2060, 1000, 140, 280, c)
    for y in (-1900, -1600, -1300, -1000): K.light(-2230, y, 150, 300, c)                # west canyon edge, south
    K.light(-2230, 1840, CREST + 120, 300, c)                                            # west abutment corner
    for y in (-1000, -600, -150): K.light(-352, y, 100, 220, c)                          # west boardwalk under the awnings
    K.light(-460, -1065, 236, 260, '1 0.85 0.6')                                         # saloon gallery
    for y in (-512, 64): K.light(850, y, 130, 280, c)                                    # behind the east row
    for (x, y) in ((1900, 300), (2010, 620), (2220, 860), (2220, 420), (1800, 900)): K.light(x, y, 150, 300, c)   # under the tower / flume
    K.light(1860, 620, CREST + 90, 260, c)                                               # catwalk under the tank
    for y in (1150, 1450): K.light(300, y, 160, 280, c)                                  # east of the spillway
    K.light(230, 1770, CREST + 110, 240, c)                                              # crest beside the gatehouse
    for (x, y) in ((2100, -1200), (2100, -1700), (1150, -880), (2150, -700)): K.light(x, y, -100, 300, '0.8 0.95 1')   # lake bed
    for y in (-1200, -800): K.light(2240, y, 150, 280, c)                                # east shore


def vault():
    x0, y0, x1, y1, z = VAULT
    t = {'side': tx('gold_rock'), 'top': tx('gold_rock'), 'bot': tx('gold_rock')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 288), (x1 + 32, y1 + 32, z + 320), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 288), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 288), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 288), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 288), t, detail=False))
    for i, (nx_, ny_) in enumerate(((-250, 200), (260, 180), (-280, -200), (250, -220), (0, 220))):
        K.custom(ML.PLACE[f'nuggets{i % 3}'], nx_, ny_, z)
    K.item('item_padpower', -150, 60, z); K.item('item_revival', 0, 120, z); K.item('holdable_killerducks', 150, 60, z)
    K.item('item_armor_padshield', 0, -60, z)
    K.ammo('imperius', -200, -100, z); K.ammo('betty', 200, -100, z)
    K.teleporter((-48, y0 + 16, z), (48, y0 + 80, z + 96), dest=(-1050, -620, 0), angle=0, name='vault_exit')
    K.light(0, 0, z + 220, 600, '1 0.85 0.5')
    for (lx, ly) in ((-240, -180), (240, -180), (-240, 180), (240, 180)): K.light(lx, ly, z + 160, 260, '1 0.85 0.5')


# ------------------------------------------------------------------------------------------------ loot
def items():
    zr = DECK + CAB_H + 16
    K.weapon('imperius', 0, 1760, CREST + GATE_H + 16, marker='purple')           # top of the map: gatehouse roof
    K.weapon('betty', TWR[0], TWR[1], Z_CAP, marker='black')                      # water-tower cap
    K.weapon('balloony', CARTS[0], CARTS[1], MESA[4], marker='orange')            # inside the ore-cart carousel
    K.weapon('pumper', -1990, 300, 0, marker='green')        # mine pit rim (bots never took it from the pit floor)
    K.weapon('splasher', 0, 560, PLUNGE_F, marker='blue')                         # bottom of the plunge pool
    K.weapon('boaster', -590, -1250, 16, marker='orange')                         # saloon
    K.weapon('bubbleg', 620, -1144, 16, marker='green')                           # general store
    ammo = {'imperius': [(600, 1728, CREST), (-1880, 780, 0), (TWR[0] + 352, TWR[1], Z_CAT)],
            'betty': [(1800, -1650, DECK), (1700, 900, 0), (-1880, -500, 0), (2064, 800, flume_z(800) + 6)],
            'balloony': [(-1500, 700, MESA[4]), (-2120, 1700, CREST), (-900, 1100, 0), (-600, -1100, 336)],
            'pumper': [(PIT[2] - 40, PIT[3] - 60, PIT_F), (-1100, 250, 0), (520, -640, 16), (-2100, -1300, 0)],
            'splasher': [(-250, 250, 0), (282, -900, 0), (1000, -1250, 0), (-280, -988, 0)],
            'boaster': [(-470, -1120, 144), (-250, -1300, 0), (520, 68, 16), (-600, 88, 16)],
            'bubbleg': [(282, -300, 0), (-250, -500, 0), (1300, 200, 0), (-1500, -900, 0), (850, -1050, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((-1000, -700), (700, 1000), (1300, -350)): K.ammo('nipper', x, y, 0)
    K.item('item_armor_padshield', 1800, (WH[1] + WH[3]) / 2, zr + 144)            # wheelhouse roof
    K.item('item_armor_shard', -680, -400, 16); K.item("item_armor_shard", 2064, 0, flume_z(0) + 6)
    K.item('holdable_floater', -620, -500, 272)                                    # bank roof
    K.item('item_speedy', (PAN[0] + PAN[2]) / 2, (PAN[1] + PAN[3]) / 2, 4)     # middle of the gold pan
    K.item('item_jumper', 1400, -900, LAKE_F)                                      # lake bottom
    K.item('holdable_boomies', -2200, 1800, CREST)                                 # far end of the west abutment
    K.item('item_climber', 2200, 1800, CREST)
    K.station(-1220, 380, 0, ang=0); K.station(1000, 600, 0, ang=180)
    for (x, y, a) in ((-1100, -500, 0), (-1050, 200, 0), (-1150, 760, 0), (-900, 1350, 270), (-600, 1000, 270),
                      (500, 1100, 270), (700, 900, 180), (1100, 300, 180), (1300, -250, 90), (1950, -150, 180),
                      (1700, 1100, 270), (1000, -950, 0), (-1000, -1500, 90), (-2050, -1950, 45), (-600, -1750, 90),
                      (-1250, -200, 0)):
        K.spawn(x, y, 0, a)


def sounds():
    K.timer_sound(0, 0, 1400, 'ambient/train_intercity', 'train', 45, 20)
    K.timer_sound(-1000, 1000, 600, 'animal/cicada_chirp', 'cicadas', 12, 8)


def shader():
    sky = GM.desert_sky(OUT, NS)
    TX.write_shader(extra=[SH.sky(sky, sun=GM.SUN, sun_int=110, skylight=(60, 3), editor=sky + '_ft')],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    GM.brush_textures(TX)
    models()
    shell(); dam(); water(); town(); mesa(); tower(); flume(); steamer(); geysers(); dressing(); fill(); vault()
    items(); sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
