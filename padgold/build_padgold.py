#!/usr/bin/env python3
"""Gold Rush Gulch (wop_padgold) - a Wild West mining-town water park in a red-rock canyon.

    OUT=<dir> python3 build_padgold.py        (names from mapinfo.json; design sheet in README.md)

Layers: shell (slab with water holes, strata banks, sky) -> water bodies -> mesa + mine -> Main Street buildings ->
water tower + stair tower + flume -> steamer -> dredge -> props/cover -> items, pads, secret, movers -> lights, sounds.
Buildings, tower, steamer and the other main pieces are custom MD3s (K.solid_piece / gold_models) with weapclip
collision of the same shapes.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, cyl, hull, carve, sub_rects, sign_box, prism, ngon
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL
import gold_models as GM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                     # playable floor
HX0, HY0, HX1, HY1 = INFO['hull']                   # sky hull (strata banks between)
ZTOP = 2560
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1),
           worldspawn={'_ambient': '14', '_color': '1 0.95 0.88', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
GM.bind(TX)

# ------------------------------------------------------------------------------------------------ layout
# Main Street (south): buildings front onto y = SY1 (doors north), boardwalk in front, dirt street beyond
SY0, SY1 = -1900, -1500
BW_Y1 = -1372                                        # boardwalk front edge (z 0..16)
STREET = (X0, -1372, X1, -760)                       # dirt street texture strip
WALL = 16
BLD = {   # name: (x0, x1, H, sign, paint, door centre x, door width, door top)
    'livery':  (-2200, -1640, 256, 'LIVERY STABLE', 'red', -1920, 192, 192),
    'saloon':  (-1400, -840, 320, 'SALOON', 'yellow', -1120, 112, 128),
    'bank':    (-712, -264, 256, 'BANK', 'brick', -560, 96, 128),
    'store':   (-136, 376, 224, 'GENERAL STORE', 'white', 120, 96, 128),
    'sheriff': (504, 952, 224, 'SHERIFF', 'blue', 728, 96, 128),
    'smith':   (1080, 1560, 192, 'BLACKSMITH', 'grey', 1320, 288, 160),
    'assay':   (1700, 2140, 208, 'ASSAY OFFICE', 'teal', 1920, 96, 128),
}
ALLEY_STAIR = (376, 504)                             # 16u stair to the store roof, plank bridge to the sheriff
OUTHOUSE = (-1576, -1890, -1480, -1794)              # secret entrance (alley west of the saloon)

# water tower (centrepiece)
TWR = (-200, 1150); R_TANK, R_CAT, Z_CAT, Z_TOP, R_CAP, Z_CAP, LEG_R = 300, 400, 576, 896, 96, 1008, 270
STAIRT = 300                                          # stair tower x0 (east of the tank)
BAND_P, BAND_Q = (1086, 1214), (1262, 1390)           # stair flights run along x in two bands, 48u apart

# flume: catwalk north -> east -> south into the plunge pool
FL_W = 128; FL_Y = (1636, 1764); FL_XN = (-264, -136); FL_XS = (1036, 1164)
FL_Z0, FL_ZC, FL_ZE = Z_CAT, 112, 16                  # floor heights: start, corner C, end
ROCK = (380, 1560, 720, 1860, 520)                    # "mine shaft" outcrop the flume runs through

# water
LAKE = (1100, -700, 2200, 700); LAKE_F = -224
PLUNGE = (880, 900, 1500, 1450); PLUNGE_F = -192
CREEK = (-1300, 480, 800, 720); CREEK_F = -16
WTOP = -16; CREEK_TOP = -4

# mine mesa (west)
MESA = (-2304, -420, -1500, 820, 384)
TUN_S = (-1820, -440, -1660, 300)                      # south corridor (x0 y0 x1 y1), 192 high
CHAMBER = (-2180, 300, -1660, 660)                     # 224 high
TUN_N = (-1960, 640, -1816, 840)
PIT = (-2160, 340, -1720, 600); PIT_F = -128           # gallery pit (hole in the slab), steps on its east side
CARTS = (-1900, 200); CART_R = 300; CART_N = 5; CART_O = 430

# steamer (east, on the lake floor)
SH_X = (1660, 1940); SH_Y = (-440, 460); SH_BOW = 600; DECK = 48
CABIN = (1720, -260, 1880, 140); CAB_H = 160; WH = (1752, -252, 1848, -120)

DREDGE = (-360, 40)                                     # x range, spans the creek
VAULT = (-384, -320, 384, 320, -1600)                  # the Mother Lode (sealed, below the town)

LIGHT_Z = {}


def tx(name): return T(name)


# ------------------------------------------------------------------------------------------------ texfn helpers
def planar(key, tile=256.0):
    return lambda c, n, poly: (TX[key], ML.planar_uv(n, tile))


def hut_brushes(x0, y0, x1, y1, z0, H, openings=None, floor=True, roof=True, T_=WALL):
    """walls (with rectangular openings), floor slab, roof slab as convex brushes. openings: {'n': [(a, b, zlo, zhi)]}
    with a, b along x for n/s walls and along y for e/w walls (world coordinates)."""
    op = openings or {}
    out = []
    walls = {'n': (x0, y1 - T_, x1, y1), 's': (x0, y0, x1, y0 + T_),
             'e': (x1 - T_, y0 + T_, x1, y1 - T_), 'w': (x0, y0 + T_, x0 + T_, y1 - T_)}
    for k, (a0, b0, a1, b1) in walls.items():
        horiz = k in 'ns'
        u0, u1 = (a0, a1) if horiz else (b0, b1)
        holes = [(a, zl, b, zh) for (a, b, zl, zh) in op.get(k, [])]
        for (ua, za, ub, zb) in sub_rects((u0, z0, u1, z0 + H), holes):
            if horiz: out.append(box((ua, b0, za), (ub, b1, zb), CAULK))
            else: out.append(box((a0, ua, za), (a1, ub, zb), CAULK))
    if floor: out.append(box((x0 + T_, y0 + T_, z0), (x1 - T_, y1 - T_, z0 + 16), CAULK))
    if roof: out.append(box((x0, y0, z0 + H), (x1, y1, z0 + H + 16), CAULK))
    return out


def hut_texfn(x0, y0, x1, y1, z0, H, front='n', fac=None, side='wood', roof='tin', floor='floor', inner='interior',
              jamb='timber', T_=WALL, extra_top=None):
    """per-face material for hut_brushes pieces: facade fitted across the front (never mirrored), siding on the
    other outer faces, jambs timber, interior planks, roof/floor tops; faces resting on the ground are dropped"""
    ztop = z0 + H + 16

    def f(c, n, poly):
        nx, ny, nz = n
        if nz > 0.7:
            k = roof if c[2] >= z0 + H + 15 else (extra_top or floor)
            return TX[k], ML.planar_uv(n, 256)
        if nz < -0.7:
            if c[2] <= z0 + 0.5: return None
            return TX[inner], ML.planar_uv(n, 256)
        outer = ((ny > 0.7 and c[1] >= y1 - 0.5, 'n'), (ny < -0.7 and c[1] <= y0 + 0.5, 's'),
                 (nx > 0.7 and c[0] >= x1 - 0.5, 'e'), (nx < -0.7 and c[0] <= x0 + 0.5, 'w'))
        for ok, k in outer:
            if not ok: continue
            if k == front and fac:
                W = x1 - x0 if k in 'ns' else y1 - y0
                if k == 'n': uf = lambda p: ((x1 - p[0]) / W, (ztop - p[2]) / (ztop - z0))
                elif k == 's': uf = lambda p: ((p[0] - x0) / W, (ztop - p[2]) / (ztop - z0))
                elif k == 'e': uf = lambda p: ((p[1] - y0) / W, (ztop - p[2]) / (ztop - z0))
                else: uf = lambda p: ((y1 - p[1]) / W, (ztop - p[2]) / (ztop - z0))
                return TX[fac], uf
            return TX[side], ML.planar_uv(n, 256)
        jam = ((abs(nx) > 0.7 and (y1 - T_ < c[1] < y1 or y0 < c[1] < y0 + T_)) or
               (abs(ny) > 0.7 and (x1 - T_ < c[0] < x1 or x0 < c[0] < x0 + T_)))
        return TX[jamb if jam else inner], ML.planar_uv(n, 128 if jam else 256)
    return f


# ------------------------------------------------------------------------------------------------ models
def models():
    GM.materials(TX, {k: (v[3], v[4]) for k, v in BLD.items()} | {'cabin': ('RIVER QUEEN', 'white'),
                                                                     'dredge': ('GOLD DREDGE', 'grey'), 'chapel': ('CHAPEL', 'white')})
    GM.model_textures(TX)
    ML.save('tower', GM.water_tower(R_TANK, R_CAT, Z_CAT, Z_TOP, R_CAP, Z_CAP, LEG_R))
    ML.save('smokestack', GM.smokestack())
    ML.save('headframe', GM.headframe())
    ML.save('portal', GM.mine_portal(160, 192))
    ML.save('portal_n', GM.mine_portal(144, 192))
    ML.save('rails', GM.rail_ring(CART_R, 0))
    ML.save('wagon', GM.wagon())
    ML.save('barrels', GM.barrel_group())
    ML.save('barrel', GM.barrel())
    ML.save('hay1', GM.hay_bale(1)); ML.save('hay3', GM.hay_bale(3))
    ML.save('trough', GM.trough())
    ML.save('crates', GM.crate_stack(CRATES))
    ML.save('crates_s', GM.crate_stack(CRATES_S))
    for i in range(3): ML.save(f'geyser{i}', GM.geyser_cone(150 - 20 * i, 60 - 10 * i, seed=i))
    ML.save('steam', GM.steam_column())
    ML.save('windmill', GM.windmill_tower())
    ML.save('bar_s', GM.bar_counter(L=240)); ML.save('bar_m', GM.bar_counter(L=200)); ML.save('backbar', GM.back_bar(L=240))
    ML.save('table', GM.saloon_table())
    ML.save('shelves', GM.shelves()); ML.save('shelves_s', GM.shelves(L=200))
    ML.save('bars', GM.jail_bars(208, 160))
    ML.save('vaultdoor', GM.vault_door())
    ML.save('forge', GM.forge())
    ML.save('lantern', GM.lantern_post())
    ML.save('hitch', GM.hitching_rail())
    for i in range(3): ML.save(f'nuggets{i}', GM.nugget_pile(seed=i))
    ML.save('flume_bents', GM.flume_trestle(FLUME_BENTS))
    ML.save('pews', GM.pews(L=120)); ML.save('belfry', GM.belfry()); ML.save('sluice', GM.sluice())
    ML.save_iqm('carts', GM.ore_carts(CART_R, CART_N, 384 - CART_O))
    ML.save_iqm('sternwheel', GM.stern_wheel(110, 160))
    ML.save_iqm('windwheel', GM.windmill_wheel())


CRATES = [((-48, -48, 0), (48, 48, 96)), ((48, -40, 0), (128, 40, 80)), ((-40, -40, 96), (40, 40, 176))]
CRATES_S = [((-40, -40, 0), (40, 40, 80)), ((40, -32, 0), (104, 32, 64))]

# flume bents (x, y, top z, axis of the cross beam); filled by flume_plan()
FLUME_BENTS = []


# ------------------------------------------------------------------------------------------------ shell
def shell():
    """structural slab with the water holes (+ basins), sky hull, stepped strata banks outside the playable area,
    player clip on the playable edge"""
    holes = [LAKE[:4], PLUNGE[:4], CREEK[:4], PIT]
    sand = {'top': tx('sand'), 'side': tx('pool_wall'), 'bot': CAULK}
    for r in sub_rects((HX0, HY0, HX1, HY1), holes + [STREET]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), sand, detail=False))
    K.add(box((STREET[0], STREET[1], -32), (STREET[2], STREET[3], 0), {'top': tx('street'), 'side': tx('pool_wall'), 'bot': CAULK},
              detail=False))
    for (x0, y0, x1, y1), fz, wt in ((LAKE[:4], LAKE_F, 'lakebed'), (PLUNGE[:4], PLUNGE_F, 'tile'), (CREEK[:4], CREEK_F, 'creekbed'),
                                     (PIT, PIT_F, 'rock')):
        t = {'top': tx(wt), 'side': tx('rock' if wt in ('rock', 'lakebed') else 'pool_wall'), 'bot': CAULK}
        if fz >= -32: K.add(box((x0, y0, -32), (x1, y1, fz), t, detail=False))
        else: K.add(box((x0 - 16, y0 - 16, fz - 16), (x1 + 16, y1 + 16, fz), t, detail=False))
        if fz < -32:
            for b in (box((x0 - 16, y0 - 16, fz), (x0, y1 + 16, -32), t, False), box((x1, y0 - 16, fz), (x1 + 16, y1 + 16, -32), t, False),
                      box((x0, y0 - 16, fz), (x1, y0, -32), t, False), box((x0, y1, fz), (x1, y1 + 16, -32), t, False)):
                K.add(b)
    sky = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: tx('sky')})
    K.add(box((HX0 - 32, HY0 - 32, -32), (HX0, HY1 + 32, ZTOP), sky('e'), detail=False))
    K.add(box((HX1, HY0 - 32, -32), (HX1 + 32, HY1 + 32, ZTOP), sky('w'), detail=False))
    K.add(box((HX0, HY0 - 32, -32), (HX1, HY0, ZTOP), sky('n'), detail=False))
    K.add(box((HX0, HY1, -32), (HX1, HY1 + 32, ZTOP), sky('s'), detail=False))
    K.add(box((HX0 - 32, HY0 - 32, ZTOP), (HX1 + 32, HY1 + 32, ZTOP + 32), sky('bot'), detail=False))
    # player clip on the playable edge, up to the sky
    for mn, mx in (((X0 - 16, Y0 - 16, 0), (X0, Y1 + 16, ZTOP)), ((X1, Y0 - 16, 0), (X1 + 16, Y1 + 16, ZTOP)),
                   ((X0, Y0 - 16, 0), (X1, Y0, ZTOP)), ((X0, Y1, 0), (X1, Y1 + 16, ZTOP))):
        K.add(box(mn, mx, CLIP))
    banks()


def banks():
    """stepped sandstone strata: courses recede and rise away from the playable edge; each 512u chunk has its own
    course heights and slanted, jittered fronts so the canyon wall doesn't read as a box"""
    rng = np.random.default_rng(7)
    rock = {'top': tx('rock'), 'bot': CAULK, 'side': tx('strata')}
    sides = (('w', X0 - 16, HX0, Y0 - 16, Y1 + 16), ('e', X1 + 16, HX1, Y0 - 16, Y1 + 16),
             ('s', Y0 - 16, HY0, HX0, HX1), ('n', Y1 + 16, HY1, HX0, HX1))
    for (k, edge, far, a0, a1) in sides:
        sg = 1 if far > edge else -1
        a = a0
        while a < a1 - 1:
            b = min(a1, a + 512)
            z = 0; rec = 0
            hs = rng.integers(140, 260, size=8)
            for i, h in enumerate(hs):
                z1 = min(1600, z + int(h))
                rb = rec + rng.integers(0, 40); rt = rb + 24 + rng.integers(0, 40)
                inner_b, inner_t = edge + sg * rb, edge + sg * rt
                if abs(far - inner_t) < 64: break
                if k in 'we':
                    pts = [(inner_b, a, z), (inner_b, b, z), (inner_t, a, z1), (inner_t, b, z1), (far, a, z), (far, b, z), (far, a, z1), (far, b, z1)]
                else:
                    pts = [(a, inner_b, z), (b, inner_b, z), (a, inner_t, z1), (b, inner_t, z1), (a, far, z), (b, far, z), (a, far, z1), (b, far, z1)]
                K.add(hull(pts, rock))
                z = z1; rec = rt + rng.integers(16, 64)
                if z >= 1600: break
            a = b


# ------------------------------------------------------------------------------------------------ water
def water():
    # lake: west-shore 16u stair out of the water; pier + steamer hull stand on the lake floor (carved out)
    x0, y0, x1, y1 = LAKE
    lake_steps = K.stairs16(x0, -200, x0 + 448, 200, LAKE_F, 0, 'w', {'top': tx('boardwalk'), 'side': tx('timber')})
    K.keep_clear(x0 - 112, -200, x0, 200, 0)
    cut = list(lake_steps) + steamer_hull_brushes() + [pier_brush()] + lake_rocks()
    K.water_box((x0, y0, LAKE_F), (x1, y1, WTOP), tx('water'), cutters=cut)
    K.add(*lake_rocks())
    K.speaker((x0 + x1) / 2, 300, 16, 'ambient/water_rippling')
    # plunge pool: 16u stair out on its south side
    px0, py0, px1, py1 = PLUNGE
    st = K.stairs16(px1 - 384, py0, px1, py0 + 128, PLUNGE_F, 0, 'e', {'top': tx('tile'), 'side': tx('pool_wall')})
    K.keep_clear(px1, py0, px1 + 112, py0 + 128, 0)
    K.water_box((px0, py0, PLUNGE_F), (px1, py1, WTOP), tx('water'), cutters=st)
    K.speaker((FL_XS[0] + FL_XS[1]) / 2, py1 - 60, 32, 'ambient/water_flowing')
    # creek: 12u deep, walk out anywhere (16u bank); the dredge hull stands on its bed
    cx0, cy0, cx1, cy1 = CREEK
    K.water_box((cx0, cy0, CREEK_F), (cx1, cy1, CREEK_TOP), tx('creek'), cutters=[dredge_hull()])
    K.speaker(-700, 600, 16, 'ambient/water_flowing')


LAKE_ROCKS = [(1380, -590, 95, 70, 1), (2070, -600, 85, 90, 2), (2080, 450, 90, 60, 3)]


def lake_rocks():
    """sandstone outcrops standing on the lake floor (sightline cover across the water; not item spots)"""
    out = []
    for (x, y, r, top, seed) in LAKE_ROCKS:
        g = np.random.default_rng(seed)
        bot = [(x + r * 1.15 * math.cos(a) * g.uniform(0.85, 1.1), y + r * 1.15 * math.sin(a) * g.uniform(0.85, 1.1), LAKE_F)
               for a in np.linspace(0, 2 * math.pi, 9, endpoint=False)]
        tp = [(x + r * 0.7 * math.cos(a + 0.3), y + r * 0.7 * math.sin(a + 0.3), top + g.uniform(-12, 12))
              for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)]
        out.append(hull(bot + tp, {'top': tx('rock'), 'side': tx('strata'), 'bot': CAULK}))
    return out


def pier_brush():
    return box((LAKE[0], -420, LAKE_F), (SH_X[0], -300, 32), {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK})


def steamer_hull_brushes():
    a = prism([(SH_X[0], SH_Y[0]), (SH_X[1], SH_Y[0]), (SH_X[1], 0), (SH_X[0], 0)], LAKE_F, DECK, CAULK)
    b = prism([(SH_X[0], 0), (SH_X[1], 0), (SH_X[1], SH_Y[1]), ((SH_X[0] + SH_X[1]) / 2, SH_BOW), (SH_X[0], SH_Y[1])],
              LAKE_F, DECK, CAULK)
    return [a, b]


def dredge_hull():
    return box((DREDGE[0], CREEK[1], CREEK_F), (DREDGE[1], CREEK[3], DECK), CAULK)


# ------------------------------------------------------------------------------------------------ mine mesa
def mesa():
    x0, y0, x1, y1, ztop = MESA
    rock = {'top': tx('rock'), 'bot': CAULK, 'side': tx('strata')}
    base = box((x0, y0, 0), (x1, y1, ztop), rock)
    cutters = [box((TUN_S[0], TUN_S[1], 0), (TUN_S[2], TUN_S[3], 192), CAULK),
               box((CHAMBER[0], CHAMBER[1], 0), (CHAMBER[2], CHAMBER[3], 224), CAULK),
               box((TUN_N[0], TUN_N[1], 0), (TUN_N[2], TUN_N[3], 192), CAULK)]
    for p in carve(base, cutters):
        for f in p.faces:
            if f.n[2] > 0.7: f.tex = tx('rock')
            elif f.n[2] < -0.7: f.tex = tx('rock')
            else: f.tex = tx('strata')
        K.add(p)
    K.reserve(((x0, y0, 0), (x1, y1, ztop)))
    K.keep_clear(TUN_S[0] - 48, TUN_S[1] - 160, TUN_S[2] + 48, TUN_S[1], 0)
    K.keep_clear(TUN_N[0] - 48, TUN_N[3], TUN_N[2] + 48, TUN_N[3] + 160, 0)
    # pit steps (16u) on the pit's east side, rim at z 0
    px0, py0, px1, py1 = PIT
    K.stairs16(px1 - 256, py0, px1, py1, PIT_F, 0, 'e', {'top': tx('planks_d'), 'side': tx('rock')})
    # 16u stairs up the mesa's east face + landing
    K.stairs16(x1, y0, x1 + 128, y0 + 768, 0, ztop, 'n', {'top': tx('planks_d'), 'side': tx('timber')}, route='mesa_stairs')
    K.add(box((x1, y0 + 768, 0), (x1 + 128, y0 + 864, ztop), {'top': tx('planks_d'), 'side': tx('timber'), 'bot': CAULK}))
    K.reserve(((x1, y0, 0), (x1 + 128, y0 + 864, ztop)))
    K.keep_clear(x1, y0 - 112, x1 + 128, y0, 0)
    K.route('mine_south', ((TUN_S[0] + TUN_S[2]) / 2, TUN_S[1] - 96, 0), ((TUN_S[0] + TUN_S[2]) / 2, TUN_S[3] - 64, 0))
    K.route('mine_north', ((TUN_N[0] + TUN_N[2]) / 2, TUN_N[3] + 96, 0), ((TUN_N[0] + TUN_N[2]) / 2, CHAMBER[3] - 30, 0))
    K.route('mine_pit', (px1 + 30, (py0 + py1) / 2, 0), (px0 + 80, (py0 + py1) / 2, PIT_F))
    # portals, signs, lamps
    K.custom(ML.PLACE['portal'], (TUN_S[0] + TUN_S[2]) / 2, MESA[1] - 18, 0, occupy=False)
    K.custom(ML.PLACE['portal_n'], (TUN_N[0] + TUN_N[2]) / 2, MESA[3] + 18, 0, angle=180, occupy=False)
    K.add(sign_box((TUN_S[0] - 40, y0 - 4, 236), (TUN_S[2] + 40, y0, 296), tx('sign_mine'), 1024, 192, facing='s', edge=tx('timber')))
    for (lx, ly) in ((-1740, -200), (-1740, 150), (-1900, 480), (-2100, 360), (-1888, 760)):
        K.light(lx, ly, 160, 260, '1 0.8 0.5')
    K.light(-2040, 470, 40, 300, '1 0.8 0.5')
    # mesa top: rail ring + ore carts (ridable func_rotating), headframe, ore
    cx, cy = CARTS
    K.custom(ML.PLACE['rails'], cx, cy, ztop, occupy=False)
    carts()
    K.custom(ML.PLACE['headframe'], -2150, 660, ztop,
             cyls=[(sx, sy, 10, 0, 300) for sx in (-70, 70) for sy in (-80, 80)])
    K.custom(ML.PLACE['nuggets0'], -2180, 500, ztop, occupy=True)
    K.speaker(cx, cy, ztop + 80, 'machine/mechanics')


def carts():
    cx, cy = CARTS
    brushes = [box((cx - 8, cy - 8, CART_O - 8), (cx + 8, cy + 8, CART_O + 8), 'common/origin')]
    for k in range(CART_N):
        a = 2 * math.pi * k / CART_N
        R = np.array([[math.cos(a + math.pi / 2), -math.sin(a + math.pi / 2)], [math.sin(a + math.pi / 2), math.cos(a + math.pi / 2)]])
        c = np.array([cx + CART_R * math.cos(a), cy + CART_R * math.sin(a)])
        pts = [tuple(c + R @ np.array([px, py])) + (z,) for px in (-58, 58) for py in (-34, 34) for z in (MESA[4] + 16, MESA[4] + 68)]
        brushes.append(hull(pts, WCLIP, round_pts=False))
    K.ent('func_rotating', brushes=brushes, model2=ML.IQM['carts'], speed=20, spawnflags=0)
    K.spots['movers'].append(dict(cls='func_rotating', centre=[cx, cy, CART_O], model=ML.IQM['carts']))


# ------------------------------------------------------------------------------------------------ Main Street
def street():
    # boardwalk along the whole street front
    K.add(box((X0 + 104, SY1, 0), (2140, BW_Y1, 16), {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK}))
    K.reserve(((X0 + 104, SY1, 0), (2140, BW_Y1, 16)))
    for name, (x0, x1, H, sign, paint, dc, dw, dtop) in BLD.items():
        building(name, x0, x1, H, dc, dw, dtop)
    alley_stair()
    outhouse()


def building(name, x0, x1, H, dc, dw, dtop):
    y0, y1 = SY0, SY1
    op = {'n': [(dc - dw / 2, dc + dw / 2, 16, dtop)]}
    if x1 - x0 >= 440 and name != 'smith':
        for s in (-1, 1):
            wx = dc + s * (dw / 2 + 90)
            if x0 + 40 < wx - 36 and wx + 36 < x1 - 40: op['n'].append((wx - 36, wx + 36, 56, 116))
    if name == 'saloon':
        op['n'].append((dc - 50, dc + 50, 144, 256))                       # balcony door
        op['s'] = [(x1 - 300, x1 - 204, 16, 128)]                        # back door to the alley
    if name in ('bank', 'store', 'livery'):
        op['s'] = [(x0 + 60, x0 + 156, 16, 128)] if name != 'livery' else [(x1 - 200, x1 - 104, 16, 128)]
    bs = hut_brushes(x0, y0, x1, y1, 0, H, op)
    extra = []
    awn = name not in ('saloon',)
    if name == 'saloon':
        extra.append(box((x0 + WALL, -1628, 128), (x1 - WALL, y1 - WALL, 144), CAULK))       # mezzanine
        extra.append(box((x0, y1, 128), (x1, BW_Y1, 144), CAULK))                              # balcony
        for px in np.linspace(x0 + 12, x1 - 12, 5):
            extra.append(box((px - 6, BW_Y1 - 12, 16), (px + 6, BW_Y1, 128), CAULK))
    if awn:
        zA = min(176, H - 32)
        extra.append(box((x0 + 8, y1, zA), (x1 - 8, BW_Y1, zA + 12), CAULK))
        for px in (x0 + 20, (x0 + x1) / 2, x1 - 20):
            if abs(px - dc) < dw / 2 + 12: continue
            extra.append(box((px - 6, BW_Y1 - 12, 16), (px + 6, BW_Y1, zA), CAULK))
    if name == 'livery':                                                                       # hay loft
        extra.append(box((x0 + WALL, y0 + WALL, 144), (x1 - WALL, -1700, 160), CAULK))
    if name == 'bank':                                                                         # vault room walls
        extra.append(box((-464, y0 + WALL, 16), (-448, -1716, H), CAULK))
        extra += [box((-448, -1716, 16), (-400, -1700, H), CAULK), box((-336, -1716, 16), (x1 - WALL, -1700, H), CAULK),
                  box((-400, -1716, 128), (-336, -1700, H), CAULK)]
    if name == 'sheriff':                                                                      # cell divider wall
        extra.append(box((720, y0 + WALL, 16), (736, -1724, H), CAULK))
    texf = hut_texfn(x0, y0, x1, y1, 0, H, front='n', fac='fac_' + name, side='side_' + name, roof='tin' if H < 300 else 'shingle')
    K.solid_piece('b_' + name, bs + extra, texf, hidden=bs + extra)
    K.keep_clear(dc - dw / 2 - 32, BW_Y1, dc + dw / 2 + 32, BW_Y1 + 120, 0)
    K.keep_clear(dc - dw / 2, y1 - 120, dc + dw / 2, y1 - WALL, 16)
    K.route(f'{name}_door', (dc, BW_Y1 + 64, 0), (dc, y1 - 60, 16))
    K.light((x0 + x1) / 2, (y0 + y1) / 2, min(H - 40, 200), 420, '1 0.85 0.6')
    if x1 - x0 > 500: K.light((x0 + x1) / 2 + (x1 - x0) / 4, -1800, 120, 260, '1 0.85 0.6')
    interior(name, x0, x1, H, dc)
    # roof pad from the street (stairs + bridge for store/sheriff instead)
    if name not in ('store', 'sheriff'):
        land_x = dc if name != 'smith' else dc
        ztop = H + 16
        edges = [(land_x, y1, ztop)] + ([(land_x, BW_Y1, min(176, H - 32) + 12)] if awn else [(land_x, BW_Y1, 144)])
        K.jumppad(land_x, -1180, 0, land=(land_x, -1720, ztop), apex=ztop + 150, name=f'pad_{name}', edges=edges)


def interior(name, x0, x1, H, dc):
    y0, y1 = SY0, SY1
    if name == 'saloon':
        K.stairs16(x1 - WALL - 96, y0 + WALL, x1 - WALL, -1628, 16, 144, 'n', {'top': tx('planks'), 'side': tx('planks_d')},
                   route='saloon_stair')
        K.custom(ML.PLACE['backbar'], x0 + WALL + 24, -1756, 16, boxes=[((-24, -120, 0), (0, 120, 180))])
        K.custom(ML.PLACE['bar_s'], x0 + WALL + 110, -1756, 16, boxes=[((-28, -120, 0), (28, 120, 64))])
        for (tx_, ty) in ((-1050, -1760),):
            K.custom(ML.PLACE['table'], tx_, ty, 16, cyls=[(0, 0, 66, 0, 40)])
        K.trigger_sound((x1 - 300, y0 + WALL, 16), (x1 - 204, y0 + 64, 96), 'machine/dingdong', 'saloon_bell', wait=6)
    elif name == 'bank':
        K.custom(ML.PLACE['vaultdoor'], -420, -1692, 16, angle=-60, occupy=False)
        K.custom(ML.PLACE['bar_m'], -580, -1680, 16, angle=90, boxes=[((-28, -100, 0), (28, 100, 64))])
        K.catalog('pad_westernset/colt.md3', -590, -1680, 80, scale=0.6, clip=False, nudge=False, angle=30)
        K.custom(ML.PLACE['nuggets1'], -330, -1820, 16)
    elif name == 'store':
        K.custom(ML.PLACE['shelves'], x0 + WALL + 18, -1700, 16, boxes=[((-18, -150, 0), (18, 150, 200))])
        K.custom(ML.PLACE['shelves'], x1 - WALL - 18, -1700, 16, angle=180, boxes=[((-18, -150, 0), (18, 150, 200))])
        K.custom(ML.PLACE['shelves_s'], 120, y0 + WALL + 18, 16, angle=90, boxes=[((-18, -100, 0), (18, 100, 200))])
        K.custom(ML.PLACE['barrels'], 200, -1620, 16, cyls=[(28, 24, 54, 0, 144)])
    elif name == 'sheriff':
        for cx0 in (520, 736):
            K.custom(ML.PLACE['bars'], cx0 + 100, -1724, 16, angle=90, occupy=False)
        for (a, b) in ((504 + WALL, 600), (664, 720), (736, 808), (872, 952 - WALL)):
            K.add(box((a, -1728, 16), (b, -1720, BLD['sheriff'][2]), CLIP))
        K.add(sign_box((600, -1884, 80), (664, -1880, 168), tx('poster1'), 128, 176, facing='n', edge=tx('planks')))
        K.catalog('pad_westernset/sheriff_badge.md3', 800, -1600, 16, scale=0.8, clip=False)
    elif name == 'smith':
        K.custom(ML.PLACE['forge'], 1320, -1780, 16, boxes=[((-70, -50, 0), (70, 50, 48)), ((96, -18, 0), (170, 18, 40))],
                 cyls=[(0, 20, 36, 48, 160)])
        K.speaker(1320, -1780, 80, 'ambient/fire_crackling')
        K.light(1320, -1760, 80, 300, '1 0.55 0.25')
    elif name == 'assay':
        K.custom(ML.PLACE['bar_m'], 1920, -1720, 16, angle=90, boxes=[((-28, -100, 0), (28, 100, 64))])
        K.custom(ML.PLACE['nuggets2'], 1900, -1720, 80, occupy=False)
    elif name == 'livery':
        K.stairs16(-2040, -1676, -1752, -1580, 16, 160, 'w', {'top': tx('planks'), 'side': tx('planks_d')}, route='livery_loft')
        K.add(box((-2072, -1700, 144), (-2040, -1676, 160), {'top': tx('planks'), 'side': tx('planks_d'), 'bot': tx('planks_d')}))
        for (hx, hy) in ((-2120, -1820), (-1980, -1840), (-1800, -1820)):
            K.custom(ML.PLACE['hay1'], hx, hy, 160, boxes=[((-48, -28, 0), (48, 28, 40))])
        for (hx, hy) in ((-2120, -1600), (-1720, -1820)):
            K.custom(ML.PLACE['hay1'], hx, hy, 16, boxes=[((-48, -28, 0), (48, 28, 40))])


def alley_stair():
    a, b = ALLEY_STAIR
    H = BLD['store'][2]
    K.stairs16(a, SY1 - 448, b, SY1, 16, H + 16, 's', {'top': tx('planks'), 'side': tx('planks_d')}, route='store_roof')
    K.add(box((a, -1640, H), (b, -1560, H + 16), {'top': tx('planks'), 'side': tx('timber'), 'bot': tx('planks_d')}))
    K.route('roof_bridge', (a - 80, -1600, H + 16), (b + 80, -1600, H + 16))


def outhouse():
    x0, y0, x1, y1 = OUTHOUSE
    door = ((x0 + x1) / 2 - 24, (x0 + x1) / 2 + 24)
    bs = hut_brushes(x0, y0, x1, y1, 0, 160, {'n': [(door[0], door[1], 0, 112)]}, floor=False)
    K.solid_piece('outhouse', bs, hut_texfn(x0, y0, x1, y1, 0, 160, side='wood_g', fac=None, roof='tin'), hidden=bs)
    K.keep_clear(door[0] - 32, y1, door[1] + 32, y1 + 100, 0)
    K.secret((x0 + WALL, y0 + WALL, 0), (x1 - WALL, y1 - WALL - 24, 72), dest=(0, VAULT[1] + 96, VAULT[4]), angle=90,
             name='outhouse', approach='top')
    K.catalog('pad_train/ttoilet.md3', (x0 + x1) / 2, y0 + 40, 0, scale=0.08, clip=False, nudge=False, angle=90)
    K.trigger_sound((door[0], y1 + 8, 0), (door[1], y1 + 56, 64), 'misc/toilet_flush', 'flush', wait=10)


# ------------------------------------------------------------------------------------------------ water tower
def tower():
    tx0, ty0 = TWR
    K.custom(ML.PLACE['tower'], tx0, ty0, 0, occupy=False)
    # collision: splayed legs, catwalk ring, tank, cone + cap
    for k in range(4):
        a = math.radians(45 + 90 * k)
        b0 = [(tx0 + math.cos(a) * (LEG_R + 60) + 14 * math.cos(t), ty0 + math.sin(a) * (LEG_R + 60) + 14 * math.sin(t), 0) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        b1 = [(tx0 + math.cos(a) * LEG_R + 14 * math.cos(t), ty0 + math.sin(a) * LEG_R + 14 * math.sin(t), Z_CAT - 16) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        K.add(hull(b0 + b1, WCLIP, round_pts=False))
    ring = []
    for i in range(16):
        a0 = math.radians(-11.25 + 22.5 * i); a1 = a0 + math.radians(22.5)
        pts = [(tx0 + r * math.cos(a), ty0 + r * math.sin(a), z) for r in (R_TANK, R_CAT) for a in (a0, a1) for z in (Z_CAT - 16, Z_CAT)]
        ring.append(hull(pts, WCLIP, round_pts=False))
    K.add(*ring)
    K.add(cyl(tx0, ty0, R_TANK - 10, Z_CAT, Z_TOP, WCLIP, 16, phase=0))
    cone = [(tx0 + (R_TANK + 6) * math.cos(t), ty0 + (R_TANK + 6) * math.sin(t), Z_TOP) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    cone += [(tx0 + R_CAP * math.cos(t), ty0 + R_CAP * math.sin(t), Z_CAP) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    K.add(hull(cone, WCLIP, round_pts=False))
    K.occupy_r(tx0, ty0, R_TANK + 10, Z_CAT, Z_CAP)
    K.reserve(((tx0 - LEG_R - 80, ty0 - LEG_R - 80, 0), (tx0 + LEG_R + 80, ty0 + LEG_R + 80, Z_CAT)))
    stair_tower()
    # pads: ground (west) -> catwalk; catwalk (south) -> cap
    K.jumppad(tx0 - 620, ty0, 0, land=(tx0 - 352, ty0, Z_CAT), apex=Z_CAT + 130, name='pad_catwalk',
              edges=[(tx0 - R_CAT, ty0, Z_CAT)])
    rl = 230                                            # land on the cone (walkable 29 deg), walk up to the cap
    zl = Z_TOP + (R_TANK + 6 - rl) / (R_TANK + 6 - R_CAP) * (Z_CAP - Z_TOP)
    K.jumppad(tx0, ty0 - 376, Z_CAT, land=(tx0, ty0 - rl, zl), apex=Z_CAP + 170, name='pad_cap',
              edges=[(tx0, ty0 - R_TANK - 6, Z_TOP)])
    K.trigger_sound((tx0 - 60, ty0 - 60, Z_CAP + 8), (tx0 + 60, ty0 + 60, Z_CAP + 72), 'human/applause', 'cap_applause', wait=20)
    for (lx, ly) in ((tx0, ty0 - 600), (tx0 + 600, ty0 - 300)):
        K.light(lx, ly, 300, 200)


def stair_tower():
    """switchback 16u stairs: Q1 east (0-144), landing E, P1 west (144-288), landing W, Q2 east (288-432), landing E,
    P2 west (432-576), landing W, bridge west to the catwalk's east chord"""
    x0 = STAIRT; xa, xb = x0 + 96, x0 + 96 + 288; xe = xb + 96
    pl = {'top': tx('planks'), 'side': tx('planks_d')}
    K.stairs16(xa, BAND_Q[0], xb, BAND_Q[1], 0, 144, 'e', pl, route='tower_q1')
    K.stairs16(xa, BAND_P[0], xb, BAND_P[1], 144, 288, 'w', pl, base=0)
    K.stairs16(xa, BAND_Q[0], xb, BAND_Q[1], 288, 432, 'e', pl, thick=24)
    K.stairs16(xa, BAND_P[0], xb, BAND_P[1], 432, 576, 'w', pl, thick=24)
    lt = {'top': tx('planks'), 'side': tx('timber'), 'bot': tx('planks_d')}
    for z in (144, 432):
        K.add(box((xb, BAND_P[0], z - 16), (xe, BAND_Q[1], z), lt))
    for z in (288, 576):
        K.add(box((x0, BAND_P[0], z - 16), (xa, BAND_Q[1], z), lt))
    K.add(box((TWR[0] + 392, BAND_P[0], Z_CAT - 16), (x0, BAND_P[1], Z_CAT), lt))
    K.reserve(((x0, BAND_P[0], 0), (xe, BAND_Q[1], 600)))
    K.keep_clear(x0 - 112, BAND_Q[0], xa, BAND_Q[1], 0)
    K.route('tower_stairs', (x0 + 40, (BAND_Q[0] + BAND_Q[1]) / 2, 0), (TWR[0] + 350, TWR[1], Z_CAT))
    posts = [(x, y) for x in (x0 + 8, xa - 8, xb + 8, xe - 8) for y in (BAND_P[0] + 8, BAND_Q[1] - 8)]
    ML.save('stairposts', GM.stair_posts([(x - (x0 + xe) / 2, y - (BAND_P[0] + BAND_Q[1]) / 2) for x, y in posts], 560))
    K.custom(ML.PLACE['stairposts'], (x0 + xe) / 2, (BAND_P[0] + BAND_Q[1]) / 2, 0, occupy=False)
    K.add(sign_box((xe, 1180, 300), (xe + 4, 1300, 330), tx('sign_flume'), 512, 128, facing='e', edge=tx('timber')))


# ------------------------------------------------------------------------------------------------ flume
def flume_z(x):
    """east-leg floor height"""
    t = (x - FL_XN[1]) / (FL_XS[0] - FL_XN[1])
    return FL_Z0 + (FL_ZC - FL_Z0) * t


def flume_plan():
    FLUME_BENTS.clear()
    for x in range(-60, FL_XS[0] - 40, 200):
        if ROCK[0] - 40 < x < ROCK[2] + 40: continue
        FLUME_BENTS.append((x, (FL_Y[0] + FL_Y[1]) / 2, int(flume_z(x + 8)) - 18, 'x'))
    FLUME_BENTS.append(((FL_XS[0] + FL_XS[1]) / 2, (FL_Y[0] + FL_Y[1]) / 2, FL_ZC - 16, 'y'))
    FLUME_BENTS.append(((FL_XN[0] + FL_XN[1]) / 2, (FL_Y[0] + FL_Y[1]) / 2, FL_Z0 - 16, 'y'))
    FLUME_BENTS.append(((FL_XN[0] + FL_XN[1]) / 2, 1590, FL_Z0 - 16, 'y'))


def slab(p0, p1, w_axis, w0, w1, za, zb, zlo, zhi, tex):
    """sloped slab between p0 and p1 along one axis (x or y), spanning w0..w1 across; top za->zb (+zhi), bottom +zlo"""
    pts = []
    for (s, z) in ((p0, za), (p1, zb)):
        for w in (w0, w1):
            for dz in (zlo, zhi):
                pts.append((s, w, z + dz) if w_axis == 'y' else (w, s, z + dz))
    return hull(pts, tex, round_pts=False)


def flume():
    flume_plan()
    wall_t = {'top': tx('timber'), 'side': tx('timber'), 'bot': tx('timber')}
    floor_t = {'top': tx('flume'), 'side': tx('timber'), 'bot': tx('timber')}
    out = []
    yN, yS = FL_Y[1], FL_Y[0]
    xw, xe = FL_XN
    # north leg (flat at the catwalk): x xw..xe, y 1542..yS
    y_start = TWR[1] + 392
    out += [box((xw, y_start, FL_Z0 - 16), (xe, yS, FL_Z0), floor_t),
            box((xw - 16, y_start, FL_Z0 - 16), (xw, yS, FL_Z0 + 48), wall_t),
            box((xe, y_start, FL_Z0 - 16), (xe + 16, yS, FL_Z0 + 48), wall_t)]
    # corner B
    out += [box((xw, yS, FL_Z0 - 16), (xe, yN, FL_Z0), floor_t),
            box((xw - 16, yS, FL_Z0 - 16), (xw, yN + 16, FL_Z0 + 48), wall_t),
            box((xw, yN, FL_Z0 - 16), (xe, yN + 16, FL_Z0 + 48), wall_t)]
    # east leg (slope)
    xa, xb = xe, FL_XS[0]
    out += [slab(xa, xb, 'y', yS, yN, FL_Z0, FL_ZC, -16, 0, floor_t),
            slab(xa, xb, 'y', yN, yN + 16, FL_Z0, FL_ZC, -16, 48, wall_t),
            slab(xa + 16, xb - 16, 'y', yS - 16, yS, flume_z(xa + 16), flume_z(xb - 16), -16, 48, wall_t)]
    # corner C
    cx0, cx1 = FL_XS
    out += [box((cx0, yS, FL_ZC - 16), (cx1, yN, FL_ZC), floor_t),
            box((cx0, yN, FL_ZC - 16), (cx1 + 16, yN + 16, FL_ZC + 48), wall_t),
            box((cx1, yS, FL_ZC - 16), (cx1 + 16, yN, FL_ZC + 48), wall_t)]
    # south leg (slope down to the pool)
    ye = PLUNGE[3] + 10
    out += [hull([(cx, y, z) for cx in (cx0, cx1) for (y, zt) in ((yS, FL_ZC), (ye, FL_ZE)) for z in (0, zt)], floor_t,
                 round_pts=False),                                      # solid ramp to the ground: no crawl gap under it
            slab(yS, ye, 'x', cx0 - 16, cx0, FL_ZC, FL_ZE, -16, 48, wall_t),
            slab(yS, ye, 'x', cx1, cx1 + 16, FL_ZC, FL_ZE, -16, 48, wall_t)]
    for b in out: K.add(b)
    K.reserve(((xw - 16, y_start, 0), (xe + 16, yN + 16, FL_Z0 + 48)), ((xe, yS - 16, 0), (cx1 + 16, yN + 16, FL_Z0 + 48)),
              ((cx0 - 16, ye, 0), (cx1 + 16, yS, FL_ZC + 48)))
    # timber bents (MD3) + their collision
    K.custom(ML.PLACE['flume_bents'], 0, 0, 0, occupy=False)
    for (x, y, zt, ax) in FLUME_BENTS:
        dx, dy = (0, 56) if ax == 'x' else (56, 0)
        for s in (-1, 1):
            K.add(box((x + s * dx - 7, y + s * dy - 7, 0), (x + s * dx + 7, y + s * dy + 7, zt), WCLIP))
    # rock outcrop the flume runs through (carved by the flume channel)
    rx0, ry0, rx1, ry1, rz = ROCK
    rock = hull([(rx0, ry0, 0), (rx1, ry0, 0), (rx0, ry1, 0), (rx1, ry1, 0),
                 (rx0 + 70, ry0 + 50, rz), (rx1 - 50, ry0 + 60, rz), (rx0 + 60, ry1 - 70, rz), (rx1 - 70, ry1 - 50, rz)],
                {'top': tx('rock'), 'side': tx('strata'), 'bot': CAULK})
    cutter = slab(xa, xb, 'y', yS - 16, yN + 16, FL_Z0, FL_ZC, -16, 220, CAULK)
    for p in carve(rock, [cutter]):
        for f in p.faces:
            f.tex = tx('rock') if f.n[2] > 0.7 else (tx('timber') if f.n[2] < -0.7 else tx('strata'))
        K.add(p)
    K.reserve(((rx0, ry0, 0), (rx1, ry1, rz)))
    K.speaker((xa + xb) / 2, (yS + yN) / 2, flume_z((xa + xb) / 2) + 40, 'ambient/water_flowing')
    K.route('flume_walk', (cx0 + 64, (yS + yN) / 2, FL_ZC), (xe + 200, (yS + yN) / 2, flume_z(xe + 200)))


# ------------------------------------------------------------------------------------------------ steamer
def steamer():
    a, b = steamer_hull_brushes()

    def hull_tex(c, n, poly):
        if n[2] > 0.7: return TX['floor'], ML.planar_uv(n, 256)
        if n[2] < -0.7: return None
        return TX['hull'], (lambda p: ((p[0] + p[1]) / 256.0, (DECK - p[2]) / (DECK - LAKE_F)))
    K.solid_piece('steamer_aft', [a], hull_tex, hidden=[a, b])
    K.solid_piece('steamer_fore', [b], hull_tex, hidden=[a, b])
    K.add(pier_brush())
    ML.save('piles', GM.pier_piles(SH_X[0] - LAKE[0], 120, LAKE_F, 32))
    K.custom(ML.PLACE['piles'], LAKE[0], -360, 0, occupy=False)
    K.add(box((LAKE[0] - 32, -420, 0), (LAKE[0], -300, 16), {'top': tx('boardwalk'), 'side': tx('timber'), 'bot': CAULK}))
    K.reserve(((LAKE[0] - 32, -420, 0), (SH_X[0], -300, 32)))
    K.keep_clear(LAKE[0] - 140, -420, LAKE[0] - 32, -300, 0)
    K.route('pier', (LAKE[0] - 96, -360, 0), (SH_X[0] + 40, -360, DECK))
    # cabin (walk through from the stern deck), upper deck = its roof, bow stairs, wheelhouse
    cx0, cy0, cx1, cy1 = CABIN
    dc = (cx0 + cx1) / 2
    op = {'s': [(dc - 30, dc + 30, DECK, DECK + 112)],
          'e': [(-200, -130, DECK + 52, DECK + 104), (-40, 30, DECK + 52, DECK + 104)],
          'w': [(-200, -130, DECK + 52, DECK + 104), (-40, 30, DECK + 52, DECK + 104), (60, 120, DECK, DECK + 112)]}
    bs = hut_brushes(cx0, cy0, cx1, cy1, DECK, CAB_H, op, floor=False)
    K.solid_piece('cabin', bs, hut_texfn(cx0, cy0, cx1, cy1, DECK, CAB_H, front='s', fac=None, side='side_cabin', roof='floor'), hidden=bs)
    K.stairs16(1740, cy1, 1860, cy1 + 352, DECK, DECK + CAB_H + 16, 's', {'top': tx('planks'), 'side': tx('planks_d')},
               route='steamer_stairs')
    zr = DECK + CAB_H + 16
    w0, wy0, w1, wy1 = WH
    bs = hut_brushes(w0, wy0, w1, wy1, zr, 128, {'n': [(1776, 1824, zr, zr + 112)]}, floor=False)
    K.solid_piece('wheelhouse', bs, hut_texfn(w0, wy0, w1, wy1, zr, 128, front='n', fac=None, side='white', roof='floor'), hidden=bs)
    for sx in (1736, 1864):
        K.custom(ML.PLACE['smokestack'], sx, 0, zr, cyls=[(0, 0, 20, 0, 300)])
    K.jumppad(1800, 20, zr, land=(1800, (wy0 + wy1) / 2, zr + 144), apex=zr + 144 + 120, name='pad_wheelhouse',
              edges=[(1800, wy1, zr + 144)])
    K.reserve(((SH_X[0], SH_Y[0], LAKE_F), (SH_X[1], SH_BOW, DECK)), ((cx0, cy0, DECK), (cx1, cy1, zr)))
    K.keep_clear(dc - 60, SH_Y[0] + 20, dc + 60, cy0, DECK)
    K.light(dc, (cy0 + cy1) / 2, DECK + 120, 300, '1 0.85 0.6')
    K.light(1800, -186, zr + 90, 200, '1 0.85 0.6')
    # turning stern wheel (decoration)
    K.rotating_model2(ML.IQM['sternwheel'], (1800, SH_Y[0] - 128, 64), 40, axis='x')


# ------------------------------------------------------------------------------------------------ dredge
def dredge():
    h = dredge_hull()

    def hull_tex(c, n, poly):
        if n[2] > 0.7: return TX['floor'], ML.planar_uv(n, 256)
        if n[2] < -0.7: return None
        return TX['hull'], (lambda p: ((p[0] + p[1]) / 256.0, (DECK - p[2]) / 120.0))
    K.solid_piece('dredge_hull', [h], hull_tex)
    x0, x1 = DREDGE
    cy0, cy1 = CREEK[1] + 60, CREEK[3] - 60
    bs = hut_brushes(x0 + 90, cy0, x1 - 90, cy1, DECK, 144, {'e': [(570, 630, DECK, DECK + 112)], 'w': [(570, 630, DECK, DECK + 112)],
                                                             'n': [(-200, -120, DECK + 50, DECK + 100)]}, floor=False)
    K.solid_piece('dredge_cabin', bs, hut_texfn(x0 + 90, cy0, x1 - 90, cy1, DECK, 144, front='s', fac='fac_dredge', side='side_dredge',
                                                 roof='tin'), hidden=bs)
    K.stairs16(-200, CREEK[3], -104, CREEK[3] + 96, 0, DECK, 's', {'top': tx('planks'), 'side': tx('planks_d')})
    K.stairs16(-200, CREEK[1] - 96, -104, CREEK[1], 0, DECK, 'n', {'top': tx('planks'), 'side': tx('planks_d')})
    K.route('dredge_n', (-152, CREEK[3] + 150, 0), (-152, cy1 + 30, DECK))
    K.route('dredge_s', (-152, CREEK[1] - 150, 0), (-152, cy0 - 30, DECK))
    K.route('dredge_cabin', (x0 + 45, 600, DECK), (x1 - 45, 600, DECK))
    K.reserve(((x0, CREEK[1] - 96, -16), (x1, CREEK[3] + 96, DECK + 160)))
    K.jumppad(-160, CREEK[1] - 300, 0, land=(-160, (cy0 + cy1) / 2, DECK + 160), apex=DECK + 160 + 150, name='pad_dredge',
              edges=[(-160, cy0, DECK + 160)])
    K.light(-160, 600, DECK + 110, 220, '1 0.85 0.6')


# ------------------------------------------------------------------------------------------------ geysers, windmill
def geysers():
    for i, (gx, gy, land, apex, name, edges) in enumerate((
            (-1850, 1150, (-1980, 700, MESA[4]), MESA[4] + 170, 'pad_geyser_mesa', [(-1980, MESA[3], MESA[4])]),
            (-1450, 1560, (TWR[0] - 352, TWR[1] + 40, Z_CAT), Z_CAT + 160, 'pad_geyser_tower', [(TWR[0] - R_CAT, TWR[1] + 40, Z_CAT)]),
            (-2000, 1700, None, None, None, None))):
        r_ = 150 - 20 * i; h_ = 60 - 10 * i
        K.custom(ML.PLACE[f'geyser{i}'], gx, gy, 0, occupy=True, cyls=[] if name else [(0, 0, r_ * 0.6, 0, h_)])
        K.custom(ML.PLACE['steam'], gx, gy, h_ if name is None else 0, lit=False, occupy=False)
        if name:
            K.jumppad(gx, gy, 0, land=land, apex=apex, name=name, edges=edges)
    K.speaker(-1800, 1500, 40, 'ambient/water_bubbling')
    # hot-spring puddles (standing on the floor, <= 16 deep)
    for (px, py, r) in ((-1650, 1850, 110), (-2120, 1300, 90)):
        poly = ngon(px, py, r, 12)
        K.add(prism(poly, 0, 12, {'top': tx('creek'), 'side': tx('creek_nd'), 'bot': tx('creek_nd')}))


def windmill():
    wx, wy = 520, 180
    K.custom(ML.PLACE['windmill'], wx, wy, 0, cyls=[(sx * 66, sy * 66, 8, 0, 200) for sx in (-1, 1) for sy in (-1, 1)])
    K.rotating_model2(ML.IQM['windwheel'], (wx, wy + 24, 450), 60, axis='y')
    K.custom(ML.PLACE['trough'], wx + 140, wy, 0, angle=90, boxes=[((-90, -24, 0), (90, 24, 40))])


# ------------------------------------------------------------------------------------------------ props + cover
def props():
    rng = np.random.default_rng(11)
    W = ML.PLACE['wagon']; wbox = [((-150, -60, 0), (150, 60, 160))]
    for (x, y, a) in ((-600, -900, 10), (300, -620, -20), (-1300, -100, 80), (700, -300, 30), (1500, 1650, 60), (-900, 1750, 0)):
        K.prop(W, x, y, 0, boxes=wbox, angle=a, search=160)
    for (x, y) in ((-1050, -1050), (480, -1100), (-200, -700), (900, 420), (-1350, 300), (1700, 1000), (300, 1900), (-700, 300)):
        K.prop(ML.PLACE['barrels'], x, y, 0, cyls=[(28, 24, 54, 0, 144)], search=160)
    for (x, y) in ((-400, -1150), (1000, -1050), (-1200, 1300), (1900, 1450), (-300, 300), (250, -250)):
        K.prop(ML.PLACE['hay3'], x, y, 0, boxes=[((-48, -28, 0), (68, 28, 120))], search=160)
    for (x, y) in ((-800, -1100), (200, -1050), (1300, -1060), (-1700, -1100)):
        K.prop(ML.PLACE['trough'], x, y, 0, boxes=[((-90, -24, 0), (90, 24, 40))], angle=0, search=120)
    for (x, y) in ((-150, -300), (600, -900), (-1000, 100), (1000, 1700), (-500, 1650), (1600, -1100)):
        K.prop(ML.PLACE['crates'], x, y, 0, boxes=CRATES, search=160)
    for (x, y) in ((-1320, -1250), (-450, -1250), (250, -1250), (800, -1250), (1500, -1250)):
        K.prop(ML.PLACE['hitch'], x, y, 0, boxes=[((-88, -6, 0), (88, 6, 48))], angle=0, search=80)
    for (x, y) in ((-1300, -800), (-300, -820), (700, -800), (1600, -820), (-1100, 800), (900, 1200), (-1250, 450)):
        K.prop(ML.PLACE['lantern'], x, y, 0, boxes=[((-6, -6, 0), (6, 6, 150))], search=80)
    # cacti and tumble of rocks round the edges
    for (x, y) in ((-2150, -650), (-1400, -650), (2150, 900), (1950, 1900), (-2150, 1950), (-600, 1950), (600, 1950),
                   (2150, -900), (-1200, 1050), (300, 900), (1300, 750), (-2200, -1000)):
        K.catalog('pad_westernset/cactus.md3', x, y, 0, scale=float(rng.uniform(0.75, 1.0)), lit=True)
    # boot hill (NE)
    for i, (x, y) in enumerate(((1800, 1250), (1900, 1300), (2000, 1250), (1850, 1450), (1980, 1500), (2100, 1400))):
        K.catalog(f'pad_westernset/tombstone{i % 3 + 1}.md3', x, y, 0, scale=0.9, angle=270 + rng.uniform(-10, 10))
    # film set nod (SE corner of the plaza)
    K.catalog('pad_westernset/camera.md3', 1650, 1700, 0, scale=0.6, angle=200)
    K.catalog('pad_westernset/directors_chair.md3', 1780, 1820, 0, scale=0.4, angle=220)
    # town sign at the west end of the street
    K.add(sign_box((-2040, -1000, 220), (-1640, -992, 300), tx('sign_town'), 1024, 192, facing='n', edge=tx('timber')))
    for px in (-2056, -1640):
        K.add(box((px, -1004, 0), (px + 16, -988, 300), {'top': tx('timber'), 'side': tx('timber'), 'bot': CAULK}))
    # posters on the boardwalk fronts
    K.add(sign_box((-110, SY1, 40), (-46, SY1 + 4, 128), tx('poster2'), 128, 176, facing='n', edge=tx('planks')))
    K.add(sign_box((1100, SY1, 40), (1164, SY1 + 4, 128), tx('poster1'), 128, 176, facing='n', edge=tx('planks')))


# ------------------------------------------------------------------------------------------------ secret vault
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
    K.teleporter((-48, y0 + 16, z), (48, y0 + 80, z + 96), dest=(0, -560, 0), angle=270, name='vault_exit')
    K.light(0, 0, z + 220, 600, '1 0.85 0.5'); K.light(-250, 0, z + 120, 250, '1 0.8 0.4'); K.light(250, 0, z + 120, 250, '1 0.8 0.4')
    K.speaker(0, 0, z + 100, 'ambient/water_drippling')


# ------------------------------------------------------------------------------------------------ items
CHAPEL = (-560, -380, -240, 80, 224)


def chapel():
    """walk-in chapel in the plaza (door south, windows east/west), belfry on the north end of the roof, pad onto
    the roof from the south; breaks the long plaza diagonals"""
    x0, y0, x1, y1, H = CHAPEL
    dc = (x0 + x1) / 2
    op = {'s': [(dc - 48, dc + 48, 16, 144)], 'n': [(dc - 40, dc + 40, 16, 128)],
          'e': [(-260, -180, 64, 150), (-60, 20, 64, 150)], 'w': [(-260, -180, 64, 150), (-60, 20, 64, 150)]}
    bs = hut_brushes(x0, y0, x1, y1, 0, H, op)
    K.solid_piece('chapel', bs, hut_texfn(x0, y0, x1, y1, 0, H, front='s', fac='fac_chapel', side='side_chapel', roof='shingle'),
                  hidden=bs)
    K.keep_clear(dc - 80, y0 - 120, dc + 80, y0, 0); K.keep_clear(dc - 80, y1, dc + 80, y1 + 120, 0)
    K.route('chapel', (dc, y0 - 80, 0), (dc, y1 + 80, 0))
    K.custom(ML.PLACE['pews'], dc - 70, y0 + 80, 16, boxes=[((-64, 0, 0), (64, 246, 52))])
    K.custom(ML.PLACE['pews'], dc + 70, y0 + 80, 16, boxes=[((-64, 0, 0), (64, 246, 52))])
    K.custom(ML.PLACE['belfry'], dc, y1 - 60, H + 16, boxes=[((-36, -36, 0), (36, 36, 128))])
    K.light(dc, (y0 + y1) / 2, 150, 380, '1 0.9 0.75')
    K.jumppad(dc, y0 - 300, 0, land=(dc, (y0 + y1) / 2 - 40, H + 16), apex=H + 16 + 150, name='pad_chapel',
              edges=[(dc, y0, H + 16)])


def cover():
    """sightline cover at the sightlines --hot cells: sluice box by the creek, supplies stored under the water tower,
    clutter in the back alley and along the street edge"""
    K.custom(ML.PLACE['sluice'], 330, 790, 0, boxes=[((-210, -44, 0), (210, 44, 110))])
    K.custom(ML.PLACE['crates'], -230, 1130, 0, boxes=CRATES, angle=20)          # stored under the tank
    K.custom(ML.PLACE['barrels'], -80, 1240, 0, cyls=[(28, 24, 54, 0, 144)])
    K.custom(ML.PLACE['hay3'], -330, 1040, 0, boxes=[((-48, -28, 0), (68, 28, 120))], angle=70)
    for x in (-1000, -150, 700, 1350, 1950):
        K.prop(ML.PLACE['crates_s'] if x % 2 else ML.PLACE['barrels'], x, -1975, 0,
               boxes=CRATES_S if x % 2 else (), cyls=() if x % 2 else [(28, 24, 54, 0, 144)], search=60)
    K.prop(ML.PLACE['crates'], 1650, 920, 0, boxes=CRATES, search=120)
    K.prop(ML.PLACE['barrels'], -600, 940, 0, cyls=[(28, 24, 54, 0, 144)], search=120)
    for x in (-1700, -380, 600, 1640):
        K.prop(ML.PLACE['barrels'], x, -1300, 0, cyls=[(28, 24, 54, 0, 144)], search=100)
    for (x, y) in ((40, 250), (-850, -420), (560, 820), (-1050, 1300), (1250, 400)):
        K.prop(ML.PLACE['hay3'] if x < 0 else ML.PLACE['crates'], x, y, 0,
               boxes=[((-48, -28, 0), (68, 28, 120))] if x < 0 else CRATES, search=140)


def fill_lights():
    """lights.png dark spots: building fronts inside, under the stair tower and flume, the lake floor"""
    for name, (x0, x1, H, *_rest) in BLD.items():
        K.light((x0 + x1) / 2, -1580, 90, 240, '1 0.85 0.6')
        K.light(x0 + 70, -1800, 90, 200, '1 0.85 0.6')
        K.light(x1 - 70, -1800, 90, 200, '1 0.85 0.6')
    for (x, y, z, v) in ((420, 1300, 120, 300), (700, 1250, 120, 260), (220, 1440, 120, 260), (-1408, 576, 140, 260),
                         (2050, 150, -120, 300), (1750, 500, -120, 260), (1750, -500, -120, 260), (-1976, -1615, 100, 260)):
        K.light(x, y, z, v)


def items():
    tx0, ty0 = TWR
    zr = DECK + CAB_H + 16
    K.weapon('imperius', tx0, ty0, Z_CAP, marker='purple')
    K.weapon('betty', 1800, (WH[1] + WH[3]) / 2, zr + 144, marker='black')
    K.weapon('balloony', CARTS[0], CARTS[1], MESA[4], marker='orange')
    K.weapon('pumper', PIT[0] + 90, (PIT[1] + PIT[3]) / 2, PIT_F, marker='green')
    K.weapon('splasher', 2000, 250, LAKE_F, marker='blue')
    K.weapon('boaster', -1220, -1740, 16, marker='orange')
    K.weapon('bubbleg', 120, -1720, 16, marker='green')
    ammo = {'imperius': [(tx0 + 352, ty0, Z_CAT), ((TUN_N[0] + TUN_N[2]) / 2, 760, 0), (2070, -1960, 0)],
            'betty': [(1800, -360, DECK), (1650, 1150, 0), (-1900, -1750, 160)],
            'balloony': [(-1600, 600, MESA[4]), (-1440, 400, MESA[4]), (-900, 1500, 0), (250, -1720, 240)],
            'pumper': [(-1740, 0, 0), (-2000, 380, 0), (1350, -1650, 16), (-1100, 300, 0)],
            'splasher': [(1000, 1150, PLUNGE_F), (900, -100, 0), (FL_XS[0] - 120, 1550, 0), (-560, -1800, 16)],
            'boaster': [(-1120, -1580, 144), (-1120, -1430, 144), (700, -1600, 16), (-400, 1400, 0)],
            'bubbleg': [(250, -1800, 16), (-160, 600, DECK + 160), (1920, -1600, 16), (-1600, 1300, 0), (600, 400, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((0, -400), (-1500, 1100), (950, 560)): K.ammo('nipper', x, y, 0)
    K.item('item_armor_padshield', -160, 600, DECK + 160)
    K.item('item_armor_shard', -380, -1800, 16); K.item('item_armor_shard', -2100, -1650, 160)
    K.item('holdable_floater', -488, -1720, 272)
    K.item('item_speedy', 620, -1820, 16)
    K.item('item_jumper', -1000, -1440, 144)
    K.item('holdable_boomies', -1900, 650, MESA[4])
    K.station(150, -450, 0, ang=90); K.station(1250, -1290, 0, ang=270)
    for (x, y, a) in ((-1800, -1200, 0), (-900, -1250, 90), (0, -1150, 90), (900, -1150, 90), (1800, -1150, 180),
                      (-1100, -400, 45), (200, -500, 90), (1000, -100, 180), (-500, 900, 270), (600, 1000, 180),
                      (-1600, 1600, 315), (1300, 1800, 225), (-2000, 1000, 0), (2100, 1100, 180), (-100, 1900, 270),
                      (900, 650, 135)):
        K.spawn(x, y, 0, a)


def sounds():
    K.timer_sound(0, 0, 1400, 'ambient/train_intercity', 'train', 45, 20)
    K.timer_sound(-1000, 1000, 600, 'animal/cicada_chirp', 'cicadas', 12, 8)
    K.timer_sound(1600, -1200, 600, 'animal/cicada_chirp', 'cicadas2', 14, 8)


def shader():
    sky = GM.desert_sky(OUT, NS)
    TX.write_shader(extra=[SH.sky(sky, sun=GM.SUN, sun_int=110, skylight=(60, 3), editor=sky + '_ft')],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    GM.brush_textures(TX)
    flume_plan()
    models()                          # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); water(); mesa(); street(); tower(); flume(); steamer(); dredge(); geysers(); windmill(); vault(); chapel()
    props(); cover(); items(); fill_lights(); sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
