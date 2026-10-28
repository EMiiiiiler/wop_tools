"""Moose Mountain Falls Deluxe: the south wing (Frost Deck + Thunder Bay hall) for build_moose.py.

    import wing; wing.build(sys.modules[__name__])      # called from build_moose.main()

Layout (x east, y north, deck z 0; the main hall's inner south wall face is y -1664):
  Frost Deck     y -2464..-1696, open to the snowy sky. Heated pool with steam, ice rink, fire pit, snow forts,
                 snowmen, snowy pines, lamp posts, falling snow. The igloo's ice-fishing hole is the SECRET:
                 it drops you into the sealed Ice Cave (Imperius, Pad shield) with a teleporter back.
  Thunder Bay    second timber hall y -5056..-2496 (inner): a wave pool with a beach (west), the wave-machine house
                 (flywheels inside, the Storm Deck dive platform on its roof: Splasher), Avalanche Peak tower (16u
                 stairs round a stone core to z 640: Balloony) with the Black Hole tube (helix into its own pool) and a
                 flume into the Tornado Bowl (slick cone, drop through the middle into the splash pool), Cocoa Cabin.
  Doors          three doorways in each hall wall facing the deck (x -1408, 128, 1664).
"""
import math
import numpy as np
from wopmap import box, hull, cyl, carve, sub_rects, sign_box, ngon
import wopmap
import layout as L
import moose_models as MM
import wing_models as WM

DOOR_X = (-1408, 128, 1664)
DOOR_W, DOOR_H = 256, 176
DECK_Y0, DECK_Y1 = -2464, -1696                  # outdoor deck (outer faces of the two hall walls)
BX = L.HX                                        # wing hall inner half width
BY0, BY1 = -5056, -2496                          # wing hall inner y range
BYC, BHY = (BY0 + BY1) / 2, (BY1 - BY0) / 2
B_EAVE, B_RIDGE = L.EAVE, 1168
B_SKY = 256
WT = L.WALL
HULL_Y0 = BY0 - WT - 64                          # sky hull south inner face


def roof_b(y):
    return B_RIDGE - (B_RIDGE - B_EAVE) * min(abs(y - BYC), BHY) / BHY


# --- wave pool + machine house
WP = (-1856, -4928, -256, -2752)                 # pool rectangle
WP_DEEP_X1, WP_SHALLOW_X0, WP_BEACH_X0 = -1408, -1152, -896
WP_TILE = (WP[0] - 16, WP[1] - 16, WP[2] + 16, WP[3] + 16)
MH = (-2048, -4928, -1872, -2752)                # machine house footprint
MH_H = 352
# --- Avalanche Peak
AV = (1248, -4192, 1632, -3808)                  # stone core
AV_Z = 640
AV_BAND = 96
# --- bowl + splash pool
BC = (600.0, -3136.0)
BOWL = dict(r_hole=104, r_rim=448, z_hole=200, z_rim=384)
SP1 = (160, -3584, 1040, -2720)                  # splash pool under the bowl
SP1_FLOOR = -176
SP1_TILE = (SP1[0] - 16, SP1[1] - 16, SP1[2] + 16, SP1[3] + 16)
# --- Black Hole helix + its pool
HC = (930.0, -4680.0); HR = 300.0
SP2 = (80, -4960, 640, -4544)
SP2_FLOOR = -144
SP2_TILE = (SP2[0] - 16, SP2[1] - 16, SP2[2] + 16, SP2[3] + 16)
# --- Frost Deck
HOTPOOL = (-832, -2368, -96, -1824)
HOT_FLOOR = -96
HOT_TILE = (HOTPOOL[0] - 16, HOTPOOL[1] - 16, HOTPOOL[2] + 16, HOTPOOL[3] + 16)
RINK = (320, -2384, 1104, -1776)
IGLOO = (-1700.0, -2080.0)
FIRE = (1300.0, -2080.0)
CABIN = (-100.0, -4720.0)
ICE_Z0, ICE_Z1 = -1600, -1360                    # sealed ice cave under the deck
ICE = (-560, -2400, 560, -1760)


def build(B):
    """B = the build_moose module (helpers, Map, lists)"""
    G = _Wing(B)
    G.run()


class _Wing:
    def __init__(self, B):
        self.B = B; self.A = B.A; self.T = B.T; self.M = B.M

    # ------------------------------------------------------------------ small helpers
    def floor_ok(self, x, y, r=24):
        """open wing floor at z 0 (deck or hall), away from pools and buildings"""
        B = self.B
        if abs(x) > BX - r: return False
        if not (BY0 + r <= y <= DECK_Y1 - r): return False
        if BY1 - r < y < DECK_Y0 + r: return False          # inside the wall between deck and hall
        if DECK_Y0 <= y <= DECK_Y1 and abs(x) > BX - 100 - r: return False   # snowbanks at the deck ends
        if DECK_Y1 - r < y <= DECK_Y1 + 32: return False    # main hall wall
        for rc in (WP_TILE, SP1_TILE, SP2_TILE, HOT_TILE, RINK, MH, (AV[0] - AV_BAND - 24, AV[1] - AV_BAND - 24, AV[2] + AV_BAND + 24, AV[3] + AV_BAND + 24)):
            if B.in_rect(x, y, rc, r): return False
        if math.hypot(x - BC[0], y - BC[1]) < BOWL['r_rim'] + 40 + r: return False
        if any(B.in_rect(x, y, n, r) for n in B.NOGO): return False
        return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in B.KEEP_OUT)

    def near(self, x, y, r, search=320):
        if self.floor_ok(x, y, r): return (x, y)
        for d in range(32, search + 1, 32):
            for k in range(16):
                a = k * math.pi / 8
                px, py = x + d * math.cos(a), y + d * math.sin(a)
                if self.floor_ok(px, py, r): return (round(px), round(py))
        return None

    def keep(self, x, y, r):
        self.B.KEEP_OUT.append((x, y, r))

    # ------------------------------------------------------------------ run
    def run(self):
        B = self.B
        # walk paths stay clear: through every doorway (both sides), the deck's cross path, the igloo entrance
        for xc in DOOR_X:
            B.NOGO.append((xc - 170, DECK_Y0, xc + 170, DECK_Y1))
            B.NOGO.append((xc - 170, BY1 - 320, xc + 170, BY1))
        B.NOGO.append((-L.HX, -2176, L.HX, -1984))
        B.NOGO.append((IGLOO[0] + 180, IGLOO[1] - 90, IGLOO[0] + 480, IGLOO[1] + 90))
        self.textures()
        self.slab_and_snow()
        self.hall_b()
        self.timbers_b()
        self.wave_pool()
        self.machine_house()
        self.avalanche()
        self.bowl()
        self.blackhole()
        self.cabin()
        self.frost_deck()
        self.ice_cave()
        self.decor_b()
        self.items_b()
        self.spawns_b()

    def textures(self):
        B = self.B
        for k, v in {'snow': (1, 1), 'path': (1, 1), 'ice': (1, 1), 'sand': (1, 1), 'rink_board': (0.5, 0.5), 'snowbank': (1, 1)}.items():
            wopmap.TEXSCALE[self.T(k)] = v

    # ------------------------------------------------------------------ floors (deck snow + wing hall), carved pools
    def slab_and_snow(self):
        B, A, T = self.B, self.A, self.T
        X1 = L.HX + WT
        # deck: snow everywhere, plowed paths between the doors, tiles for the hot pool
        paths = [(x - 160, DECK_Y0, x + 160, DECK_Y1) for x in DOOR_X] + [(-X1, -2176, X1, -1984)]
        tiles = [HOT_TILE]
        for r in sub_rects((-X1, DECK_Y0, X1, DECK_Y1), tiles + paths + [RINK]):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('snow'), 'side': B.CAULK, 'bot': B.CAULK}))
        for pr in paths:
            others = [p for p in paths if p is not pr and paths.index(p) < paths.index(pr)]
            for r in sub_rects(pr, tiles + others + [RINK]):
                A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('path'), 'side': B.CAULK, 'bot': B.CAULK}))
        # ice rink (slick, 4u lower so the boards read)
        A(box((RINK[0], RINK[1], L.SLAB_BOT), (RINK[2], RINK[3], 0), {'top': T('ice'), 'side': B.CAULK, 'bot': B.CAULK}))
        # wing hall floor: deck flagstone, sand beach strip, tiles for the pools
        beach = (WP[2] + 16, BY0, 256, BY1)
        tiles = [WP_TILE, SP1_TILE, SP2_TILE]
        for r in sub_rects((-X1, BY0 - WT, X1, DECK_Y0), tiles + [beach]):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('deck'), 'side': B.CAULK, 'bot': B.CAULK}))
        for r in sub_rects(beach, tiles):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('sand'), 'side': B.CAULK, 'bot': B.CAULK}))
        self.hot_pool()

    def hot_pool(self):
        """heated outdoor pool on the deck: 80 deep, 16u steps on the north and south sides, steam"""
        B, A, T = self.B, self.A, self.T
        x0, y0, x1, y1 = HOTPOOL
        tile = box((HOT_TILE[0], HOT_TILE[1], L.SLAB_BOT), (HOT_TILE[2], HOT_TILE[3], 0), B.CAULK)
        B._TILES.append(HOT_TILE)
        for b in carve(tile, [box((x0, y0, HOT_FLOOR), (x1, y1, 32), B.CAULK)]):
            A(B.pool_faces(b, top=T('coping')))
        steps = []
        for k in range(1, 6):          # 5 steps of 16u at both ends (x), 32 deep
            zt = HOT_FLOOR + 16 * k
            if zt >= 0: break
            for (xa, xb) in ((x0 + 32 * (5 - k), x0 + 32 * (6 - k)), (x1 - 32 * (6 - k), x1 - 32 * (5 - k))):
                steps.append(box((xa, y0, HOT_FLOOR), (xb, y1, zt), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': B.CAULK}))
        for s in steps: A(s)
        # hot-spring rock in the middle with a snowy pine on it
        rx, ry = (x0 + x1) / 2, (y0 + y1) / 2
        rock = hull([(px, py, HOT_FLOOR) for (px, py) in ngon(rx, ry, 78, 10)] + [(px, py, 48) for (px, py) in ngon(rx, ry, 56, 10)],
                    B.WCLIP, round_pts=False)
        A(rock)
        B.custom(WM.seastack('lagoon_rock', 104, 138, 91), rx, ry, HOT_FLOOR - 2)
        B.custom(MM.PLACE['snow_pine'], rx - 20, ry + 10, 48, angle=70)
        A(cyl(round(rx - 20), round(ry + 10), 18, 48, 248, B.WCLIP, 8))
        for pc in carve(box((x0, y0, HOT_FLOOR), (x1, y1, L.WATER), B.CAULK), steps + [rock]):
            A(B.water_faces(pc))
        for (x, y) in ((-680, -2250), (-300, -1960), (-240, -2260), (-640, -1940)):
            A(B.sprite(x, y, L.WATER, 220, 'steam', 160))
        B.light((x0 + x1) / 2, (y0 + y1) / 2, -40, 300, '0.5 0.9 1')
        B.speaker((x0 + x1) / 2, (y0 + y1) / 2, 0, 'ambient/water_bubbling', volume=0.4)
        self.M.ent('target_location', ((x0 + x1) // 2, (y0 + y1) // 2, 40), message='Steam Lagoon')

    # ------------------------------------------------------------------ the second hall shell
    def hall_b(self):
        B, A, T, M = self.B, self.A, self.T, self.M
        CA = B.CAULK
        X1 = L.HX
        s = (B_RIDGE - B_EAVE) / BHY
        WIN = (112, 464)
        def wtex(face, lower=False):
            return {'side': CA, face: T('wainscot') if lower else T('stucco'), 'top': CA, 'bot': CA}
        def ftex(face_in, face_out, lower=False):
            return {'side': CA, face_in: T('wainscot') if lower else T('stucco'), face_out: T('logwall'), 'top': CA, 'bot': CA}
        for side in ('n', 's'):
            if side == 'n': y0, y1, fin, fout = BY1, BY1 + WT, 's', 'n'
            else: y0, y1, fin, fout = BY0 - WT, BY0, 'n', 's'
            opens, doors = [], []
            for xc in range(-1792, 1793, 384):
                if side == 's' and (-2048 < xc < -200): continue        # wave pool side: solid wall behind the beach
                (doors if side == 'n' and xc in DOOR_X else opens).append(xc)
            xs = [-X1 - WT]
            for xc in sorted(opens + doors): xs += [xc - 128, xc + 128]
            xs.append(X1 + WT)
            # lower band (split at doors), window band piers, glass
            lows = [(-X1 - WT, X1 + WT)]
            for xc in doors:
                nl = []
                for (a, b) in lows:
                    if b <= xc - 128 or a >= xc + 128: nl.append((a, b)); continue
                    if a < xc - 128: nl.append((a, xc - 128))
                    if b > xc + 128: nl.append((xc + 128, b))
                lows = nl
            for (a, b) in lows:
                A(box((a, y0, 0), (b, y1, 96), ftex(fin, fout, True)))
                A(box((a, y0, 96), (b, y1, WIN[0]), ftex(fin, fout)))
            for i in range(0, len(xs), 2):
                A(box((xs[i], y0, WIN[0]), (xs[i + 1], y1, WIN[1]), ftex(fin, fout)))
            for xc in opens:
                A(box((xc - 128, (y0 + y1) / 2 - 2, WIN[0]), (xc + 128, (y0 + y1) / 2 + 2, WIN[1]), T('glass')))
            for xc in doors:
                A(box((xc - 128, y0, DOOR_H), (xc + 128, y1, DOOR_H + 16), {'side': T('glulam'), 'top': CA, 'bot': T('glulam')}))
                A(box((xc - 128, (y0 + y1) / 2 - 2, DOOR_H + 16), (xc + 128, (y0 + y1) / 2 + 2, WIN[1]), T('glass')))
            # top band up to the roof (sloped top)
            zin, zout = B_EAVE, B_EAVE - WT * s
            yi, yo = (y0, y1) if side == 'n' else (y1, y0)
            A(hull([(x, yi, z) for x in (-X1 - WT, X1 + WT) for z in (WIN[1], zin)] + [(x, yo, z) for x in (-X1 - WT, X1 + WT) for z in (WIN[1], zout)],
                   ftex(fin, fout)))
        # gable walls (solid; the west one is behind the wave-machine house)
        for sx in (-1, 1):
            x0, x1 = (X1, X1 + WT) if sx > 0 else (-X1 - WT, -X1)
            face = 'w' if sx > 0 else 'e'
            tex = {'side': CA, face: T('stucco_cream'), 'top': CA, 'bot': CA}
            A(box((x0, BY0, 0), (x1, BY1, 96), {'side': CA, face: T('wainscot'), 'top': CA, 'bot': CA}))
            A(box((x0, BY0, 96), (x1, BY1, B_EAVE), tex))
            pts = []
            for y in (BY0, BY1, BYC):
                pts += [(x, y, B_EAVE) for x in (x0, x1)] + [(x, y, roof_b(y)) for x in (x0, x1)]
            A(hull(pts, tex))
        # roof: two slabs + ridge skylight between the rafters
        for sg in (-1, 1):
            ya, yb = BYC + sg * B_SKY, BYC + sg * (BHY + WT + 8)
            pts = []
            for y in (ya, yb):
                zu = roof_b(y) if abs(y - BYC) <= BHY else B_EAVE - (abs(y - BYC) - BHY) * s
                pts += [(x, y, z) for x in (-X1 - WT, X1 + WT) for z in (zu, zu + L.ROOF_T)]
            A(hull(pts, lambda n: T('ceiling') if n[2] < -0.5 else CA))
            xs = sorted(set([-X1 - WT] + [v for x in L.RAFTER_X for v in (x - 20, x + 20)] + [X1 + WT]))
            for i in range(len(xs) - 1):
                xa, xb = xs[i], xs[i + 1]
                tex = T('glass') if i % 2 == 0 else T('glulam')
                pts = []
                for y in (BYC, ya):
                    zu = roof_b(y)
                    pts += [(x, y, z) for x in (xa, xb) for z in (zu, zu + (4 if tex == T('glass') else L.ROOF_T))]
                if tex == T('glass'): pts = [(x, y, z + 6) for (x, y, z) in pts]
                A(hull(pts, tex))
        for x in (-1700, -1150, -600, 0, 600, 1150, 1700):
            M.ent('light', (x, round(BYC), B_RIDGE - 60), light=300, _color='0.6 0.72 1')
        for xc in range(-1792, 1793, 384):
            M.ent('light', (xc, BY0 + 40, 300), light=160, _color='0.6 0.75 1')
        # signs over the doors (deck side)
        A(sign_box((-224, DECK_Y0, 440), (224, DECK_Y0 + 6, 552), T('sign_thunder'), 512, 128, back=CA, facing='n'))
        M.ent('target_location', (0, round(BYC), 60), message='Thunder Bay')

    def timbers_b(self):
        B = self.B
        raf = WM.rafter_b(BHY, B_EAVE, B_RIDGE)
        for x in L.RAFTER_X:
            B.custom(raf, x, BYC, 0)
        B.custom(WM.ridge_b(L.HX, B_RIDGE), 0, BYC, 0)
        dy = 1040
        hang = roof_b(BYC - dy) - (L.DUCT_Z + 40) + 1
        dp = MM.duct(hang)
        for y in (BYC - dy, BYC + dy):
            B.custom(dp, 0, y, L.DUCT_Z)
        made = {}
        for (x, y) in ((-128, -3200), (-128, -4400), (1856, -2900), (1856, -4700)):
            H = round(roof_b(y) - 72) if x in L.RAFTER_X else round(roof_b(y + 22 * (1 if y > BYC else -1)))
            if H not in made:
                made[H] = MM.column(f'column_b{len(made)}', H, [-180, 180] if x in L.RAFTER_X else [])
            B.custom(made[H], x, y, 0)
            self.A(cyl(x, y, 34, 0, 166, B.WCLIP, 16, phase=0))
            self.A(box((x - 20, y - 20, 166), (x + 20, y + 20, min(H, 700)), B.WCLIP))
            self.keep(x, y, 80); B.NOGO.append((x - 60, y - 60, x + 60, y + 60))
        lamps = {}
        for x in (-1920, -1152, -384, 384, 1152, 1920):
            for y in (BYC - 1000, BYC - 500, BYC + 500, BYC + 1000):
                zr = roof_b(y)
                rod = 96 if abs(y - BYC) > 800 else 200
                if rod not in lamps: lamps[rod] = MM.lamp(f'lamp{rod}', rod)
                B.custom(lamps[rod], x, y, zr, lit=False)
                B.light(x, y, zr - rod - 60, 2200, '1 0.82 0.6')

    # ------------------------------------------------------------------ wave pool
    def wave_pool(self):
        B, A, T = self.B, self.A, self.T
        x0, y0, x1, y1 = WP
        B._TILES.append(WP_TILE)
        dz, sz = L.POOL_DEEP, L.POOL_SHALLOW
        tile = box((WP_TILE[0], WP_TILE[1], L.SLAB_BOT), (WP_TILE[2], WP_TILE[3], 0), B.CAULK)
        cut = [box((x0, y0, dz), (WP_DEEP_X1, y1, 32), B.CAULK),
               hull([(WP_DEEP_X1, y, dz) for y in (y0, y1)] + [(WP_SHALLOW_X0, y, sz) for y in (y0, y1)] +
                    [(x, y, 32) for x in (WP_DEEP_X1, WP_SHALLOW_X0) for y in (y0, y1)], B.CAULK),
               box((WP_SHALLOW_X0, y0, sz), (WP_BEACH_X0, y1, 32), B.CAULK),
               hull([(WP_BEACH_X0, y, sz) for y in (y0, y1)] + [(x1, y, 0) for y in (y0, y1)] +
                    [(x, y, 32) for x in (WP_BEACH_X0, x1) for y in (y0, y1)], B.CAULK)]
        for b in carve(tile, cut):
            B.pool_faces(b)
            for f in b.faces:              # the beach slope is sand
                c = np.mean([np.array(q) for q in f.pts], 0)
                if f.tex == T('pool_tile') and c[0] > WP_BEACH_X0 + 1: f.tex = T('sand'); f.sc = (1, 1)
            A(b)
        W = L.WATER
        xw = WP_BEACH_X0 + (W - sz) / (0 - sz) * (x1 - WP_BEACH_X0)
        wat = [box((x0, y0, dz), (WP_DEEP_X1, y1, W), B.CAULK),
               hull([(WP_DEEP_X1, y, dz) for y in (y0, y1)] + [(WP_SHALLOW_X0, y, sz) for y in (y0, y1)] +
                    [(x, y, W) for x in (WP_DEEP_X1, WP_SHALLOW_X0) for y in (y0, y1)], B.CAULK),
               box((WP_SHALLOW_X0, y0, sz), (WP_BEACH_X0, y1, W), B.CAULK),
               hull([(WP_BEACH_X0, y, sz) for y in (y0, y1)] + [(xw, y, W) for y in (y0, y1)] + [(WP_BEACH_X0, y, W) for y in (y0, y1)], B.CAULK)]
        # two rock stacks in the deep end (cover; storm rocks)
        # rock stacks: two in the deep end, three in the beach shallows (cover over the open water)
        stacks = [(-1600, -3300, 96, dz, 120, 0.45), (-1560, -4380, 110, dz, 150, 0.5),
                  (-480, -3480, 88, -64, 128, 0.4), (-520, -4200, 80, -64, 112, 0.38), (-660, -2980, 72, -64, 96, 0.34),
                  (-1010, -3600, 84, sz, 120, 0.4), (-340, -3920, 64, -64, 104, 0.3), (-700, -3700, 64, -64, 100, 0.3)]
        rocks = []
        zslope = lambda x: sz + (x - WP_BEACH_X0) * (0 - sz) / (x1 - WP_BEACH_X0)
        for k, (rx, ry, rr, zb, zt, mul) in enumerate(stacks):
            rt = B.WCLIP
            if rx - rr > WP_BEACH_X0:                # on the beach slope: the base follows the sloped floor exactly
                pts = [(px, py, zslope(px)) for (px, py) in ngon(rx, ry, rr * 0.85, 10)] + [(px, py, zt) for (px, py) in ngon(rx, ry, rr * 0.7, 10)]
                rocks.append(hull(pts, rt, round_pts=False)); zb = min(zslope(rx - rr), zslope(rx + rr))
            else:
                rocks.append(hull([(px, py, zb) for (px, py) in ngon(rx, ry, rr * 0.85, 10)] + [(px, py, zt) for (px, py) in ngon(rx, ry, rr * 0.7, 10)], rt, round_pts=False))
            B.custom(WM.seastack(f'stack{k}', rr, zt - zb + 30, 70 + k), rx, ry, zb - 2)
        for r in rocks: A(r)
        for b in wat:
            for pc in carve(b, rocks):
                for f in pc.faces:
                    f.tex = T('water_wave') if (f.n[2] > 0.99 and abs(max(p[2] for p in f.pts) - W) < 0.5) else T('water_nodraw')
                    f.sc = (1, 1)
                A(pc)
        # underwater grilles on the deep wall
        for y in (-4500, -4100, -3700, -3300):
            B.custom(MM.PLACE['vent'], x0, y, dz + 8)
        # floats + ducks, lifeguard on the beach
        rng = np.random.default_rng(41)
        for k in range(14):
            x = rng.uniform(-1300, -500); y = rng.uniform(y0 + 150, y1 - 150)
            if any(math.hypot(x - st[0], y - st[1]) < st[2] + 60 for st in stacks): continue
            nm = ['tube1y', 'tube1p', 'tube1k', 'tube2t'][k % 4]
            B.custom(MM.PLACE[nm], x, y, W, angle=int(rng.uniform(0, 360)))
        B.mdl_c('pad_ducks/pad_duck.md3', -1100, -3000, W, 0.3, 120)
        B.mdl_c('pad_ducks/pad_duck.md3', -800, -4600, W, 0.25, 300)
        B.custom(MM.PLACE['lifeguard'], -150, -3840, 0, angle=180, mul=1.4)
        A(box((-178, -3868, 0), (-122, -3812, 168), B.WCLIP))
        self.keep(-150, -3840, 70)
        for (x, y, z) in ((-1500, -3800, -120), (-1000, -3200, -60), (-1000, -4400, -60), (-1600, -2900, -120)):
            B.light(x, y, z, 260, '0.5 0.85 1')
        B.speaker(-1100, -3840, 0, 'ambient/ocean_waves', volume=0.7)
        B.speaker(-500, -3200, 0, 'ambient/ocean_waves', volume=0.4)
        B.timer_sound(-1700, -3840, 300, 'machine/fog_horn', 'wavehorn', 45, 15, volume=0.6)
        self.M.ent('target_location', (-1000, round(BYC), 60), message='Wave Pool')

    def machine_house(self):
        """wave-machine house on the west wall: walk in at the north end (flywheels), pad to the Storm Deck roof"""
        B, A, T, M = self.B, self.A, self.T, self.M
        x0, y0, x1, y1 = MH
        t = 16; H = MH_H
        wall = lambda: {'side': T('stucco_green'), 'top': B.CAULK, 'bot': B.CAULK, 'e': T('stucco_green'), 'w': B.CAULK}
        inner = T('steel')
        # east facade over the pool (x1-t..x1) with vents above the water
        A(box((x1 - t, y0, 0), (x1, y1, H - 16), {'e': T('stucco_green'), 'w': inner, 'side': T('stucco_green'), 'top': B.CAULK, 'bot': B.CAULK}))
        # south end wall, north end wall with a door
        A(box((x0, y0, 0), (x1 - t, y0 + t, H - 16), {'n': inner, 'side': T('stucco_green'), 'top': B.CAULK, 'bot': B.CAULK}))
        dx0, dx1 = -2000, -1920
        A(box((x0, y1 - t, 0), (dx0, y1, H - 16), {'s': inner, 'side': T('stucco_green'), 'top': B.CAULK, 'bot': B.CAULK}))
        A(box((dx1, y1 - t, 0), (x1 - t, y1, H - 16), {'s': inner, 'side': T('stucco_green'), 'top': B.CAULK, 'bot': B.CAULK}))
        A(box((dx0, y1 - t, 128), (dx1, y1, H - 16), {'s': inner, 'n': T('stucco_green'), 'bot': T('steel'), 'side': T('stucco_green'), 'top': B.CAULK}))
        # roof deck (Storm Deck)
        A(box((x0, y0, H - 16), (x1, y1, H), {'top': T('planks'), 'bot': T('steel'), 'side': T('glulam')}))
        # facade detail: vents, pipes, beacons, sign
        for y in (-4560, -4240, -3920, -3600, -3280, -2960):
            B.custom(MM.PLACE['vent'], x1, y, 48)
        B.custom(WM.pipes(y1 - y0 - 64), x1, (y0 + y1) / 2, 0)
        for y in (-4800, -3840, -2880):
            B.custom(MM.PLACE['beacon'], x1, y, 300, lit=False)
            B.light(x1 + 30, y, 300, 200, '1 0.6 0.2')
        A(sign_box((x1, -4096 - 0, 200), (x1 + 4, -3584, 328), T('sign_thunder'), 512, 128, back=B.CAULK, facing='e'))
        # inside: flywheels (func_rotating model2, axis x) against the west wall, a walkway, machine noise
        for k, y in enumerate((-4700, -4300, -3900, -3500, -3100)):
            z = 150
            M.ent('func_rotating', brushes=[box((-2030, y - 8, z - 8), (-2014, y + 8, z + 8), B.ORIGIN),
                                            box((-2026, y - 4, z - 4), (-2018, y + 4, z + 4), B.NODRAW_NS)],
                  model2=MM.PLACE['flywheel'][0], speed=60 + 15 * k, spawnflags=4 | (2 if k % 2 else 0), dmg=2)
        A(box((x0, y0 + t, 0), (x0 + 8, y1 - t, H - 16), {'e': inner, 'side': B.CAULK, 'top': B.CAULK, 'bot': B.CAULK}))
        for y in (-4500, -3700, -2950):
            B.light(-1950, y, 260, 380, '1 0.8 0.6')
        B.custom(WM.pipes(y1 - y0 - 160), x1 - t, (y0 + y1) / 2, 0, angle=180)
        B.speaker(-1960, -3900, 150, 'machine/mechanics', volume=0.6)
        B.speaker(-1960, -3200, 150, 'machine/transformer', volume=0.3)
        # Storm Deck railing (south end; the north end is where the pad lands, the pool side is open: dive in!)
        for (a, b) in (((x0 + 4, y0 + 4), (x1 - 4, y0 + 4)),):
            path, sc, zo, o = MM.gen_railing(f'mh_rail{int(a[1])}', [(a[0], a[1], H), (b[0], b[1], H)], tex='metal_white')
            B.custom((path, sc, zo), o[0], o[1], o[2])
            A(box((a[0], a[1] - 3, H), (b[0], a[1] + 3, H + 40), B.WCLIP))
        # pad from the deck north of the house onto the Storm Deck
        B.jumppad(-1790, -2600, 0, (-1950, -2900, H), H + 120, 'storm_deck')
        self.M.ent('target_location', (-1960, -3800, H + 40), message='Storm Deck')

    # ------------------------------------------------------------------ Avalanche Peak
    def avalanche(self):
        B, A, T = self.B, self.A, self.T
        x0, y0, x1, y1 = AV
        Z = AV_Z; Bd = AV_BAND; t = 16
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        B.NOGO.append((x0 - Bd - 40, y0 - Bd - 40, x1 + Bd + 40, y1 + Bd + 40))
        self.keep(cx, cy, 380)
        # stone core: walls with a door (north), an upper room floor, solid upper core
        stone = {'side': T('fieldstone'), 'top': B.CAULK, 'bot': B.CAULK}
        dx0, dx1 = cx - 48, cx + 48
        A(box((x0, y1 - t, 0), (dx0, y1, 192), stone)); A(box((dx1, y1 - t, 0), (x1, y1, 192), stone))
        A(box((dx0, y1 - t, 128), (dx1, y1, 192), dict(stone, bot=T('glulam'))))
        A(box((x0, y0, 0), (x1, y0 + t, 192), stone))
        A(box((x0, y0 + t, 0), (x0 + t, y1 - t, 192), stone)); A(box((x1 - t, y0 + t, 0), (x1, y1 - t, 192), stone))
        A(box((x0, y0, 192), (x1, y1, Z - 16), {'side': T('fieldstone'), 'bot': T('planks_dark'), 'top': B.CAULK}))
        A(box((x0, y0, Z - 16), (x1, y1, Z), {'top': T('planks'), 'side': T('glulam'), 'bot': B.CAULK}))
        # stairs: four 10-step flights round the core (16u rise, 32 deep), corner landings
        st = {'top': T('planks'), 'side': T('planks_dark'), 'bot': B.CAULK}
        z = 0
        # E band rising north
        for k in range(10):
            A(box((x1, y0 + 32 * k, 0), (x1 + Bd, y0 + 32 * (k + 1), 16 * (k + 1)), st))
        A(box((x1, y0 + 320, 0), (x1 + Bd, y1 + Bd, 160), st))                   # NE landing z160 (solid)
        th = 16                                                                    # upper flights are thin treads you can walk under
        for k in range(10):                                                        # N band rising west
            zt = 160 + 16 * (k + 1)
            A(box((x1 - 32 * (k + 1), y1, zt - th), (x1 - 32 * k, y1 + Bd, zt), st))
        A(box((x0 - Bd, y1, 320 - th), (x1 - 320, y1 + Bd, 320), st))            # NW landing z320
        for k in range(10):                                                        # W band rising south
            zt = 320 + 16 * (k + 1)
            A(box((x0 - Bd, y1 - 32 * (k + 1), zt - th), (x0, y1 - 32 * k, zt), st))
        A(box((x0 - Bd, y0 - Bd, 480 - th), (x0, y1 - 320, 480), st))            # SW landing z480
        for k in range(10):                                                        # S band rising east
            zt = 480 + 16 * (k + 1)
            A(box((x0 + 32 * k, y0 - Bd, zt - th), (x0 + 32 * (k + 1), y0, zt), st))
        A(box((x0 + 320, y0 - Bd, Z - th), (x1 + Bd, y0, Z), st))                # SE: top landing
        for (px, py) in ((x0 - Bd + 12, y1 + Bd - 12), (x0 - Bd + 12, y0 - Bd + 12), (x1 + Bd - 12, y0 - Bd + 12)):
            ztop = {0: 320, 1: 480, 2: Z}[[(x0 - Bd + 12, y1 + Bd - 12), (x0 - Bd + 12, y0 - Bd + 12), (x1 + Bd - 12, y0 - Bd + 12)].index((px, py))] - th
            A(box((px - 12, py - 12, 0), (px + 12, py + 12, ztop), {'side': T('glulam'), 'top': B.CAULK, 'bot': B.CAULK}))
        # railings round the platform and outer stair edges (clip)
        for (a, b, nm) in (((x0 + 2, y1 - 2), (x1 - 2, y1 - 2), 'n'), ((x0 + 2, y0 + 2), (x0 + 300, y0 + 2), 's')):
            path, sc, zo, o = MM.gen_railing(f'av_rail_{nm}', [(a[0], a[1], Z), (b[0], b[1], Z)], tex='metal_white')
            B.custom((path, sc, zo), o[0], o[1], o[2])
            A(box((min(a[0], b[0]), a[1] - 3, Z), (max(a[0], b[0]), a[1] + 3, Z + 40), B.WCLIP))
        # pads: express pad from the floor (south-east) to the top, for bots and players
        B.jumppad(x1 + Bd + 190, cy - 60, 0, (cx + 40, cy - 40, Z), Z + 170, 'avalanche_express')
        B.light(cx, cy, Z + 120, 600, '1 0.85 0.65'); B.light(cx, cy, 100, 300, '1 0.8 0.55')
        self.M.ent('target_location', (round(cx), round(cy), Z + 40), message='Avalanche Peak')

    # ------------------------------------------------------------------ Tornado Bowl
    def bowl(self):
        B, A, T = self.B, self.A, self.T
        bx, by = BC
        rh, rr, zh, zr = BOWL['r_hole'], BOWL['r_rim'], BOWL['z_hole'], BOWL['z_rim']
        n = 24
        slope = (zr - zh) / (rr - rh)
        # splash pool under the bowl (160 deep) with 16u steps on its south side
        x0, y0, x1, y1 = SP1
        B._TILES.append(SP1_TILE)
        tile = box((SP1_TILE[0], SP1_TILE[1], L.SLAB_BOT), (SP1_TILE[2], SP1_TILE[3], 0), B.CAULK)
        for b in carve(tile, [box((x0, y0, SP1_FLOOR), (x1, y1, 32), B.CAULK)]):
            A(B.pool_faces(b))
        steps = []
        for k in range(1, 11):
            zt = SP1_FLOOR + 16 * k
            if zt >= 0: break
            steps.append(box((x0, y0 + 24 * (10 - k), SP1_FLOOR), (x0 + 320, y0 + 24 * (11 - k), zt), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': B.CAULK}))
        # stilts from the pool floor to under the bowl
        posts = []; post_xy = []
        stairs_rect = (x0 - 20, y0 - 20, x0 + 340, y0 + 260)
        for k in range(8):
            a = math.radians(22.5 + 45 * k)
            px, py = bx + 400 * math.cos(a), by + 400 * math.sin(a)
            if B.in_rect(px, py, stairs_rect): continue
            ztop = zh + (390 - rh) * slope - 30
            post_xy.append((px - bx, py - by, ztop))
            posts.append(box((round(px) - 10, round(py) - 10, SP1_FLOOR), (round(px) + 10, round(py) + 10, round(ztop) - 2), B.WCLIP))
        for p in steps + posts: A(p)
        for pc in carve(box((x0, y0, SP1_FLOOR), (x1, y1, L.WATER), B.CAULK), steps + posts):
            A(B.water_faces(pc))
        # the bowl: slick cone segments (top = the riding surface), weapon-clip lip with a gap at the flume entry (east)
        for k in range(n):
            a0, a1 = k * 360 / n, (k + 1) * 360 / n
            pts = []
            for a in (a0, a1):
                for (r, z) in ((rh, zh), (rr, zr)):
                    px, py = bx + r * math.cos(math.radians(a)), by + r * math.sin(math.radians(a))
                    pts += [(px, py, z), (px, py, z - 16)]
            A(hull(pts, B.SLICK, round_pts=False))
            am = (a0 + a1) / 2
            if not (-35 < ((am + 180) % 360) - 180 < 35):
                A(B.ring_seg(bx, by, a0, a1, rr, rr + 20, zr - 16, zr + 48, B.WCLIP))
        B.custom(WM.bowl(rh, rr, zh, zr, post_xy, 0), bx, by, 0)
        B.NOGO.append((x0 - 40, y0 - 40, x1 + 40, y1 + 40))
        B.speaker(bx, by, 300, 'ambient/water_flowing', volume=0.4)
        B.light(bx, by, zr + 200, 600, '1 0.85 0.65'); B.light(bx, by, 0, 400, '0.5 0.85 1')
        self.M.ent('target_location', (round(bx), round(by), 60), message='Tornado Bowl')
        # flume from the tower's west face to the bowl's east rim point, heading north into the bowl tangentially
        ax0, ay0, ax1, ay1 = AV
        start = (ax0 - AV_BAND - 8, -3900.0)
        rim = (bx + rr + 10, by)
        xy = [start] + L._bez(start, (start[0] - 140, start[1]), (rim[0] + 20, rim[1] - 500), (rim[0], rim[1] - 260), 10)[1:]
        xy += [(rim[0], rim[1] - 130), rim]
        pts = L._with_z(xy, AV_Z - 2, zr + 24)
        path = [(ax0 + 40, start[1], AV_Z)] + pts
        ok = lambda x, y: self.floor_ok(x, y, 40)
        sup = MM.supports_for(path, ok, every=3, zmin=90)
        B.custom(MM.flume('flume_bowl', path, sup, 56, 48, MM.S('slide_teal', 'lms', v=0.22, tag='fb'), MM.S('slide_kidyel', 'lm', tag='fbin'),
                          MM.S('metal_white', 'lms', v=0.15, tag='fbm')), 0, 0, 0)
        B.slide_brushes(path[1:], 46, 48)
        B.supports(sup)
        for (x, y, z) in path: B.NOGO.append((x - 70, y - 70, x + 70, y + 70))

    # ------------------------------------------------------------------ Black Hole
    def blackhole(self):
        B, A, T = self.B, self.A, self.T
        ax0, ay0, ax1, ay1 = AV
        start = (1650.0, ay0 - AV_BAND - 24)                # off the SE top landing, heading south
        top = (HC[0], HC[1] + HR)                            # helix entry (top point), heading west = counter-clockwise
        lead = L._bez(start, (start[0], start[1] - 130), (top[0] + 320, top[1]), top, 12)
        arc = [(HC[0] + HR * math.cos(math.radians(a)), HC[1] + HR * math.sin(math.radians(a))) for a in np.linspace(90, 540, 60)][1:]
        e0 = arc[-1]                                         # west point, heading south
        ex = L._bez(e0, (e0[0], e0[1] - 160), (e0[0] - 120, -4900), (e0[0] - 220, -4900), 6)[1:] + [(e0[0] - 320, -4900)]
        xy = [start] + lead[1:] + arc + ex
        pts = L._with_z(xy, AV_Z - 2, 24)
        path = [(start[0], start[1] + 70, AV_Z)] + pts
        self.bh_path = path
        ok = lambda x, y: self.floor_ok(x, y, 40)
        sup = MM.supports_for(path, ok, every=4, zmin=110)
        # a post must not pass through a lower turn of the helix
        sup = [(x, y, z) for (x, y, z) in sup if not any(math.hypot(x - px, y - py) < 120 and pz < z - 60 for (px, py, pz) in path)]
        B.custom(WM.blackhole(path, sup, HC), HC[0], HC[1], 0)
        B.slide_brushes(path[1:], 40, 90, roof=True)
        B.supports(sup)
        for (x, y, z) in path: B.NOGO.append((x - 80, y - 80, x + 80, y + 80))
        # splash pool where it exits
        x0, y0, x1, y1 = SP2
        B._TILES.append(SP2_TILE)
        tile = box((SP2_TILE[0], SP2_TILE[1], L.SLAB_BOT), (SP2_TILE[2], SP2_TILE[3], 0), B.CAULK)
        for b in carve(tile, [box((x0, y0, SP2_FLOOR), (x1, y1, 32), B.CAULK)]):
            A(B.pool_faces(b))
        steps = []
        for k in range(1, 9):
            zt = SP2_FLOOR + 16 * k
            if zt >= 0: break
            steps.append(box((x1 - 32 * (9 - k), y0, SP2_FLOOR), (x1 - 32 * (8 - k), y0 + 192, zt), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': B.CAULK}))
        for s in steps: A(s)
        for pc in carve(box((x0, y0, SP2_FLOOR), (x1, y1, L.WATER), B.CAULK), steps):
            A(B.water_faces(pc))
        B.NOGO.append((x0 - 40, y0 - 40, x1 + 40, y1 + 40))
        B.light((x0 + x1) / 2, (y0 + y1) / 2, -60, 260, '0.6 0.4 1')
        B.speaker(xy[-1][0], xy[-1][1], 40, 'ambient/water_shower', volume=0.4)

    # ------------------------------------------------------------------ Cocoa Cabin
    def cabin(self):
        B, A, T = self.B, self.A, self.T
        cx, cy = CABIN
        w, d, hh = 224, 256, 128
        hx0, hy0, hx1, hy1 = cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2
        crib = MM.crib('cocoa', w, d, hh, openings=[('n', -36, 36, 0, 96)])
        B.custom(crib, cx, cy, 0)
        t = 10
        A(box((hx0 - t, hy0 - t, 0), (hx1 + t, hy0 + t, hh), B.WCLIP))
        A(box((hx0 - t, hy0 + t, 0), (hx0 + t, hy1 - t, hh), B.WCLIP)); A(box((hx1 - t, hy0 + t, 0), (hx1 + t, hy1 - t, hh), B.WCLIP))
        A(box((hx0 - t, hy1 - t, 0), (cx - 36, hy1 + t, hh), B.WCLIP)); A(box((cx + 36, hy1 - t, 0), (hx1 + t, hy1 + t, hh), B.WCLIP))
        A(box((cx - 36, hy1 - t, 96), (cx + 36, hy1 + t, hh), B.WCLIP))
        A(box((hx0 + t, hy0 + t, hh - 8), (hx1 - t, hy1 - t, hh), {'bot': T('planks_dark'), 'side': T('planks_dark'), 'top': B.CAULK}))
        A(box((hx0 - t, hy0 - t, hh), (hx1 + t, hy1 + t, hh + 12), {'top': T('planks'), 'side': T('glulam'), 'bot': B.CAULK}))
        path, sc, zo, o = MM.gen_railing('cocoa_rail', [(hx0 - 6, hy0 - 6, hh + 12), (hx1 + 6, hy0 - 6, hh + 12), (hx1 + 6, hy1 + 6, hh + 12)], tex='glulam')
        B.custom((path, sc, zo), o[0], o[1], o[2])
        A(box((hx0 - 9, hy0 - 9, hh + 12), (hx1 + 9, hy0 - 3, hh + 52), B.WCLIP))
        A(box((hx1 + 3, hy0 - 3, hh + 12), (hx1 + 9, hy1 + 9, hh + 52), B.WCLIP))
        B.custom(MM.PLACE['cooler'], cx, hy0 + t + 34, 0, mul=0.7)
        A(box((cx - 90, hy0 + t, 0), (cx + 90, hy0 + t + 46, 106), B.WCLIP))
        B.custom(MM.lantern(24), cx, cy, hh - 8, lit=False)
        B.light(cx, cy, 80, 300, '1 0.75 0.45')
        A(sign_box((cx - 80, hy1 + 22, 100), (cx + 80, hy1 + 26, 140), T('sign_cocoa'), 512, 128, back=T('glulam'), facing='n'))
        # pad onto the roof
        B.jumppad(cx - 230, cy + 60, 0, (cx - 30, cy, hh + 12), hh + 170, 'cocoa_roof')
        B.NOGO.append((hx0 - 60, hy0 - 60, hx1 + 60, hy1 + 60)); self.keep(cx, cy, 220)
        self.M.ent('target_location', (round(cx), round(cy), 60), message='Cocoa Cabin')

    # ------------------------------------------------------------------ Frost Deck
    def frost_deck(self):
        B, A, T, M = self.B, self.A, self.T, self.M
        X1 = L.HX
        self.igloo()
        # ends of the deck: snowbanks + player clip up to the sky
        for sx in (-1, 1):
            xa, xb = sorted((sx * (X1 - 96), sx * (X1 + WT)))
            rng = np.random.default_rng(3 + sx)
            for y in range(DECK_Y0, DECK_Y1, 128):
                h = int(rng.uniform(72, 120))
                pts = [(x, yy, 0) for x in (xa, xb) for yy in (y, y + 128)] + [(sx * (X1 - 40), y + 64, h), (sx * (X1 + WT), y + 20, h), (sx * (X1 + WT), y + 108, h)]
                A(hull(pts, {'top': T('snowbank'), 'side': T('snowbank'), 'bot': B.CAULK}))
            A(box((min(sx * (X1 + WT), sx * (X1 + WT + 64)), DECK_Y0 + 8, 0), (max(sx * (X1 + WT), sx * (X1 + WT + 64)), DECK_Y1 - 8, L.RIDGE + L.ROOF_T + 160), B.PCLIP))
            A(box((min(sx * (X1 - 40), sx * (X1 + WT)), DECK_Y0 + 8, 124), (max(sx * (X1 - 40), sx * (X1 + WT)), DECK_Y1 - 8, L.RIDGE + L.ROOF_T + 160), B.PCLIP))
        # nothing climbs onto the hall roofs from the deck: player clip over the deck at eave height is not needed
        # (eaves are 576 up); falling snow (big soft sprites)
        rng = np.random.default_rng(7)
        for k in range(14):
            x = rng.uniform(-1900, 1900); y = rng.uniform(DECK_Y0 + 80, DECK_Y1 - 80)
            A(B.sprite(x, y, 60, 560, 'snowfall', 200))
        # ice rink: boards with gaps on the paths' sides, lamp posts
        x0, y0, x1, y1 = RINK
        bt = {'side': T('rink_board'), 'top': T('metal_white'), 'bot': B.CAULK}
        A(box((x0, y0, 0), (x1, y0 + 8, 40), bt)); A(box((x0, y1 - 8, 0), (x1, y1, 40), bt))
        for xx in (x0, x1 - 8):
            A(box((xx, y0 + 8, 0), (xx + 8, -2176 + 0, 40), bt)); A(box((xx, -1984, 0), (xx + 8, y1 - 8, 40), bt))
        for (lx, ly) in ((x0 - 40, y0 + 40), (x1 + 40, y1 - 40), (x0 - 40, y1 - 40), (x1 + 40, y0 + 40)):
            B.custom(MM.PLACE['lamppost'], lx, ly, 0); A(box((lx - 8, ly - 8, 0), (lx + 8, ly + 8, 150), B.WCLIP))
            B.light(lx, ly, 160, 260, '1 0.8 0.55')
        B.light((x0 + x1) / 2, (y0 + y1) / 2, 200, 500, '0.75 0.85 1')
        B.NOGO.append((x0 - 30, y0 - 30, x1 + 30, y1 + 30))
        M.ent('target_location', (round((x0 + x1) / 2), round((y0 + y1) / 2), 40), message='Ice Rink')
        # fire pit + Adirondack chairs
        fx, fy = FIRE
        B.custom(MM.PLACE['firepit'], fx, fy, 0, lit=False)
        A(B.cyl(round(fx), round(fy), 80, 0, 20, B.WCLIP, 12))
        B.light(fx, fy, 70, 700, '1 0.6 0.3'); B.speaker(fx, fy, 30, 'ambient/fire_crackling', volume=0.7)
        for k, a in enumerate((20, 110, 200, 290)):
            px, py = fx + 170 * math.cos(math.radians(a)), fy + 170 * math.sin(math.radians(a))
            B.custom(MM.PLACE[['adi_red', 'adi_green', 'adi_wood', 'adi_red'][k]], px, py, 0, angle=a + 180)
        self.keep(fx, fy, 230)
        M.ent('target_location', (round(fx), round(fy), 40), message='Fire Pit')
        # snow forts (cover): lumpy snow walls with snowball piles
        for (cx, cy, ang) in ((-1100, -2300, 0), (-1150, -1860, 180), (1650, -2350, 0), (1680, -1850, 180)):
            for (u0, u1) in ((-120, -40), (40, 120)):
                pts = []
                for (u, h) in ((u0, 64), (u1, 72)):
                    for v in (-20, 20):
                        pts += [(cx + u, cy + v, 0), (cx + u * 0.97, cy + v * 0.7, h)]
                A(hull(pts, {'top': T('snowbank'), 'side': T('snowbank'), 'bot': B.CAULK}))
            B.custom(MM.PLACE['snowballs'], cx, cy + (40 if ang == 0 else -40), 0, lit=True)
            self.keep(cx, cy, 160)
        # ice moose on a snow plinth
        mx, my = 120, -2080
        A(B.cyl(mx, my, 110, 0, 32, {'top': T('snowbank'), 'side': T('snowbank'), 'bot': B.CAULK}, 12))
        B.custom(MM.PLACE['moose'], mx - 20, my, 32, angle=180, mul=0.8, _remap='*;models/moosefalls/ice_lms')
        A(box((mx - 80, my - 60, 32), (mx + 60, my + 60, 130), B.WCLIP))
        self.keep(mx, my, 170)
        # snowmen, snowy pines, string lights
        for (x, y, s, a) in ((-1880, -2380, 0.7, 30), (-300, -2380, 0.6, 80), (1150, -1800, 0.65, 250), (-1900, -1800, 0.6, 300),
                             (-20, -2398, 0.6, 140), (-1380, -1880, 0.65, 200), (-1380, -2398, 0.6, 20)):
            q = self.near(x, y, 60)
            if q: B.solid_mdl('pad_ddmix/jail/snowman.md3', q[0], q[1], 0, s, a); self.keep(q[0], q[1], 80)
        for (x, y) in ((-1250, -2320), (-1000, -2080), (-80, -2080), (1150, -2350), (1850, -2080), (-1880, -2080), (1500, -1800), (-30, -2390), (-1500, -2400), (-1600, -1880)):
            q = self.near(x, y, 150)
            if not q: continue
            B.custom(MM.PLACE['snow_pine'], q[0], q[1], 0, angle=int(rng.uniform(0, 360)))
            A(B.cyl(round(q[0]), round(q[1]), 18, 0, 200, B.WCLIP, 8))
            self.keep(q[0], q[1], 110)
        for i, (a_, b_) in enumerate((((-1900, -1720), (1900, -1720)), ((-1900, -2440), (1900, -2440)))):
            path, sc, zo, o = MM.string_lights(f'deck_lights{i}', (a_[0], a_[1], 0), (b_[0], b_[1], 0), sag=60, h=260)
            B.custom((path, sc, zo), o[0], o[1], o[2], lit=False)
            for p_ in (a_, b_): A(box((p_[0] - 4, p_[1] - 4, 0), (p_[0] + 4, p_[1] + 4, 260), B.WCLIP))
        # light + sounds
        B.speaker(0, -2080, 300, 'ambient/wind_icy', volume=0.5)
        B.timer_sound(-1600, -2300, 200, 'animal/wolf_howl2', 'wolf2', 60, 30, volume=0.4)
        for x in range(-1800, 1801, 600):
            B.light(x, -2080, 400, 500, '0.7 0.8 1')
        M.ent('target_location', (-600, -2080, 40), message='Frost Deck')

    def igloo(self):
        """igloo on the deck (walk in through the tunnel); the ice-fishing hole in its floor is the secret"""
        B, A, T, M = self.B, self.A, self.T, self.M
        cx, cy = IGLOO
        R, H = 196, 168
        B.custom(MM.PLACE['igloo'], cx, cy, 0)
        # collision: 16 wedge tiers following the dome 8u inside, doorway (east) = skipped wedges 15 and 0 below 80
        tiers = [(0, 80), (80, 120), (120, 150), (150, 160)]
        for (za, zb) in tiers:
            ra = (R - 8) * math.cos(math.asin(min(1, za / (H - 8)))); rb = (R - 8) * math.cos(math.asin(min(1, zb / (H - 8))))
            r = min(ra, rb)
            for k in range(16):
                a0, a1 = k * 22.5 - 11.25, (k + 1) * 22.5 - 11.25
                if k == 0 and zb <= 80: continue
                A(B.ring_seg(cx, cy, a0, a1, max(r - 18, 8), r, za, zb, B.WCLIP))
        # tunnel walls (clip) from the dome out to R + 96
        A(box((cx + R - 6, cy - 54, 0), (cx + R + 96, cy - 40, 80), B.WCLIP))
        A(box((cx + R - 6, cy + 40, 0), (cx + R + 96, cy + 54, 80), B.WCLIP))
        A(box((cx + R - 6, cy - 40, 72), (cx + R + 96, cy + 40, 86), B.WCLIP))
        # the hole: a dark water disc on the floor and a teleport trigger above it
        hx, hy = cx - 70, cy
        A(B.cyl(round(hx), round(hy), 34, 0, 1, {'top': T('fishhole'), 'side': B.NODRAW_NS, 'bot': B.NODRAW_NS}, 12))
        M.ent('trigger_teleport', brushes=[B.cyl(round(hx), round(hy), 22, 2, 40, B.TRIG, 8)], target='icecave_in')
        B.light(cx, cy, 100, 160, '0.5 0.8 1')
        B.light(hx, hy, 10, 80, '0.3 0.6 1')
        self.keep(cx, cy, R + 130)
        B.NOGO.append((cx - R - 40, cy - R - 40, cx + R + 140, cy + R + 40))
        M.ent('target_location', (round(cx), round(cy), 40), message='Igloo')

    def ice_cave(self):
        """sealed ice cave under the deck (separate sealed area): Imperius + Pad shield, teleporter back to the igloo"""
        B, A, T, M = self.B, self.A, self.T, self.M
        x0, y0, x1, y1 = ICE
        z0, z1 = ICE_Z0, ICE_Z1
        W_ = 32
        ice = {'side': T('ice_wall'), 'top': T('ice_wall'), 'bot': T('ice_wall')}
        A(box((x0 - W_, y0 - W_, z0 - W_), (x1 + W_, y1 + W_, z0), {'top': T('ice'), 'side': B.CAULK, 'bot': B.CAULK}, detail=False))
        A(box((x0 - W_, y0 - W_, z1), (x1 + W_, y1 + W_, z1 + W_), {'bot': T('ice_wall'), 'side': B.CAULK, 'top': B.CAULK}, detail=False))
        A(box((x0 - W_, y0 - W_, z0), (x1 + W_, y0, z1), {'n': T('ice_wall'), 'side': B.CAULK, 'top': B.CAULK, 'bot': B.CAULK}, detail=False))
        A(box((x0 - W_, y1, z0), (x1 + W_, y1 + W_, z1), {'s': T('ice_wall'), 'side': B.CAULK, 'top': B.CAULK, 'bot': B.CAULK}, detail=False))
        A(box((x0 - W_, y0, z0), (x0, y1, z1), {'e': T('ice_wall'), 'side': B.CAULK, 'top': B.CAULK, 'bot': B.CAULK}, detail=False))
        A(box((x1, y0, z0), (x1 + W_, y1, z1), {'w': T('ice_wall'), 'side': B.CAULK, 'top': B.CAULK, 'bot': B.CAULK}, detail=False))
        # ice pillars + crystals (cover)
        for (px, py) in ((-300, -2250), (280, -1920), (0, -2080)):
            A(B.cyl(px, py, 40, z0, z1, {'side': T('ice_wall'), 'top': B.CAULK, 'bot': B.CAULK}, 8))
        for (cx_, cy_, k) in ((-420, -2280, 9), (420, -2300, 10), (-150, -1840, 10), (300, -2050, 9), (-420, -1880, 9)):
            B.custom(MM.PLACE[f'crystals{k}'], cx_, cy_, z0)
            A(B.cyl(cx_, cy_, 26, z0, z0 + 120, B.WCLIP, 8))
        for (ix, iy, k) in ((-400, -2100, 5), (-100, -2300, 6), (150, -1950, 5), (400, -2200, 6), (-250, -1850, 6), (250, -2330, 5), (110, -2200, 6)):
            B.custom(MM.PLACE[f'icicles{k}'], ix, iy, z1, lit=False)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        M.ent('misc_teleporter_dest', (x0 + 80, round(cy), z0 + 24), targetname='icecave_in', angle=0)
        M.ent('trigger_multiple', brushes=[box((x0 + 40, cy - 60, z0), (x0 + 140, cy + 60, z0 + 80), B.TRIG)], target='ice_snd', wait=8)
        B.speaker(x0 + 100, cy, z0 + 60, 'misc/secret_found', loop=False, targetname='ice_snd')
        B.weapon('imperius', 200, -2200, z0, 'purple')
        B.item('item_armor_padshield', -200, -1900, z0)
        B.item('ammo_imperius', 420, -1880, z0)
        # exit teleporter (east end) back to the deck beside the igloo
        B.mdl_c('pad_teleporter/padtp_blue.md3', x1 - 80, cy, z0, 1.0, 0)
        M.ent('trigger_teleport', brushes=[box((x1 - 130, cy - 40, z0 + 2), (x1 - 30, cy + 40, z0 + 90), B.TRIG)], target='icecave_out')
        M.ent('misc_teleporter_dest', (round(IGLOO[0]) + 340, round(IGLOO[1]), 24), targetname='icecave_out', angle=0)
        for (lx, ly) in ((-350, -2080), (0, -2300), (350, -2080), (0, -1880)):
            B.light(lx, ly, z0 + 160, 400, '0.5 0.85 1')
        B.speaker(cx, cy, z0 + 100, 'ambient/ice_cracking', volume=0.5)
        B.speaker(cx, cy, z0 + 100, 'ambient/droplets_echoing', volume=0.5)
        M.ent('target_location', (round(cx), round(cy), z0 + 40), message='Ice Cave')

    # ------------------------------------------------------------------ decoration in the wing hall
    def decor_b(self):
        B = self.B
        rng = np.random.default_rng(53)
        # beach umbrellas + loungers on the sand strip, tube racks, potted pines, ducks, beach balls
        for (x, y) in ((-120, -3100), (-120, -4300), (80, -3500), (80, -4080)):
            q = self.near(x, y, 70)
            if not q: continue
            B.custom(MM.PLACE['umbrella'], q[0], q[1], 0, angle=int(rng.uniform(0, 90)))
            self.A(B.cyl(round(q[0]), round(q[1]), 40, 0, 31, B.WCLIP, 12)); self.keep(q[0], q[1], 100)
        for (x, y) in ((-60, -2900), (40, -3800), (-60, -4500), (200, -4400)):
            q = self.near(x, y, 40)
            if not q: continue
            B.custom(MM.PLACE['lounger'], q[0], q[1], 0, angle=0); self.keep(q[0], q[1], 50)
        for (x, y) in ((1100, -2700), (1900, -3300), (1900, -4300), (300, -4300), (1300, -4900), (-200, -2650), (60, -3780), (200, -3980), (560, -4380), (-180, -3480),
                       (700, -3700), (1150, -3450), (300, -2690), (-1300, -5000), (-700, -5000), (-1750, -5000), (800, -4150), (620, -4080)):
            q = self.near(x, y, 50)
            if not q: continue
            B.custom(MM.PLACE['tube_stack'], q[0], q[1], 0, angle=int(rng.uniform(0, 360)))
            self.A(B.cyl(round(q[0]), round(q[1]), 32, 0, 88, B.WCLIP, 12)); self.keep(q[0], q[1], 60)
        for (x, y, s) in ((1900, -2650, 0.7), (1900, -4950, 0.7), (-1700, -2620, 0.6), (1150, -3300, 0.6), (380, -3800, 0.6), (1700, -3000, 0.6)):
            q = self.near(x, y, 150)
            if not q: continue
            self.A(B.cyl(round(q[0]), round(q[1]), 56, 0, 40, {'top': self.T('rock'), 'side': self.T('fieldstone'), 'bot': B.CAULK}, 12))
            B.custom(MM.PLACE['small_pine'], q[0], q[1], 40, angle=int(rng.uniform(0, 360)), mul=s / 0.65)
            self.A(B.cyl(round(q[0]), round(q[1]), 18, 40, 240, B.WCLIP, 8)); self.keep(q[0], q[1], 130)
        for (x, y, s, a) in ((1600, -3500, 0.5, 200), (60, -2700, 0.45, 300)):
            q = self.near(x, y, 70)
            if q: B.solid_mdl('pad_ducks/pad_duck.md3', q[0], q[1], 0, s, a); self.keep(q[0], q[1], 80)
        for (x, y) in ((-40, -3300), (150, -4650)):
            q = self.near(x, y, 30)
            if q: B.mdl_c('pad_ball/pad_basketball.md3', q[0], q[1], 0, 0.3, 0); self.keep(q[0], q[1], 30)
        # trail-map board on two posts inside the middle door (breaks the straight view through all three doorways)
        A = self.A; T = self.T
        A(B.sign_box((-20, -2866, 48), (120, -2858, 118), T('sign_trailmap'), 256, 128, back=T('glulam'), facing='ns'))
        for px in (-20, 112):
            A(box((px, -2866, 0), (px + 8, -2858, 48), T('glulam'))); A(box((px, -2866, 118), (px + 8, -2858, 126), T('glulam')))
        # lamp posts along the deck's north strip (between the steam lagoon and the main hall)
        for (x, y) in ((-1000, -1764), (-620, -1764), (-300, -1764), (-650, -2424), (-300, -2424), (450, -2424), (800, -2424)):
            q = self.near(x, y, 26, 64)
            if not q: print('NOTE lamppost', x); continue
            B.custom(MM.PLACE['lamppost'], q[0], q[1], 0); A(box((q[0] - 8, q[1] - 8, 0), (q[0] + 8, q[1] + 8, 150), B.WCLIP))
            B.light(q[0], q[1], 160, 220, '1 0.8 0.55'); self.keep(q[0], q[1], 40)
        self.M.ent('station_health', (1760, -3420, 0), angle=180)
        self.keep(1760, -3420, 90)
        for (x, y) in ((-1400, BYC), (900, BYC), (0, -2800), (0, -4800)):
            B.light(x, y, 700, 900, '1 0.85 0.65')

    # ------------------------------------------------------------------ items + spawns
    def items_b(self):
        B = self.B
        H = MH_H
        B.weapon('splasher', -1960, -3700, H, 'orange')                  # Storm Deck (pad)
        B.weapon('betty', -1700, -3840, L.POOL_DEEP, 'black')           # bottom of the wave pool deep end
        cx, cy = (AV[0] + AV[2]) / 2, (AV[1] + AV[3]) / 2
        B.weapon('balloony', cx - 80, cy + 60, AV_Z, 'green')           # top of Avalanche Peak
        B.weapon('pumper', CABIN[0] + 20, CABIN[1], 128 + 12, 'green')   # Cocoa Cabin roof deck (pad)
        B.weapon('bubbleg', FIRE[0] - 120, FIRE[1] + 140, 0, 'blue')     # by the fire pit
        B.weapon('boaster', 712, -2080, 0, 'orange')                     # middle of the ice rink
        for (cls, x, y, z) in (('ammo_balloony', 1440, -3600, 0), ('ammo_balloony', -900, -2300, 0),
                               ('ammo_betty', -1960, -4600, H), ('ammo_betty', 900, -4300, 0),
                               ('ammo_boaster', 1700, -1850, 0), ('ammo_boaster', 0, -4400, 0),
                               ('ammo_bubbleg', -1000, -4800, 0), ('ammo_bubbleg', 1500, -2350, 0),
                               ('ammo_splasher', -1960, -2950, 0), ('ammo_splasher', 640, -3180, SP1_FLOOR),
                               ('ammo_imperius', cx + 100, cy - 100, AV_Z), ('ammo_nipper', 1800, -4400, 0),
                               ('item_armor_shard', -400, -2100, 0), ('item_armor_shard', 1000, -2700, 0),
                               ('item_speedy', 712, -2300, 0)):
            if z == 0:
                q = self.near(x, y, 24, 400)
                if q is None: print('NOTE wing item not free', cls, x, y)
                else: x, y = q
            B.item(cls, x, y, z)
            self.keep(x, y, 40)
        B.item('item_armor_shard', -1944, -4200, 0)          # inside the wave-machine house
        B.item('holdable_boomies', 1440, -3960, 0)           # in the tower's stone room

    def spawns_b(self):
        B = self.B
        for (x, y, a) in ((-1250, -1880, 0), (-200, -1900, 0), (1180, -1760, 180), (1900, -2300, 180), (-500, -2440, 90),
                          (-1780, -2590, 270), (-100, -3000, 180), (1100, -2650, 270), (1900, -3800, 180), (1100, -4900, 90),
                          (-600, -5000, 90), (-100, -4100, 0), (1500, -3000, 270), (-1960, -4850, 90)):
            q = self.near(x, y, 40, 400)
            if q is None: print('NOTE wing spawn not free', x, y); continue
            B.spawn(q[0], q[1], 0, a)
            self.keep(q[0], q[1], 50)
