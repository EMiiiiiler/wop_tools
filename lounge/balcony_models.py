"""Custom MD3s for the night balcony of wop_padlounge (Couch Lock). All geometry and art is original and generated here.

    make(out) -> writes models/padlounge/b_*.md3 + textures, returns (shader text, {model: modelscale})

The balcony layout constants live here too (build_lounge.py imports them), so models and collision always agree.
Padman scale (~8u per cm). World axes: x east, y north, the balcony runs south from the apartment wall (y -1808).
Models are built in world coordinates round an anchor and saved relative to it (`ANCHOR[name]`), so the map just puts
the misc_model origin at the anchor.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, frame, save_md3, grid_normals
import lounge_models as LM

MD = 'models/padlounge'
# ------------------------------------------------------------------------------------------------ layout
YS = -1792                       # lounge south wall inner face; its outer face (the facade) is YS - 16
YF = YS - 16
DECK = (-2048, -4992, 2048, YF)  # balcony deck (top z 0)
DOOR = (-720, 720, 1600)         # sliding door opening x0, x1, height
VENT = (1400, 1560, 72)          # crawl vent through the wall x0, x1, height
PLAT = (320, -4960, 2048, -2880, 256)        # spa platform x0, y0, x1, y1, top
TUB = (1200, -3960)
TUB_RO, TUB_RI, TUB_FLOOR, TUB_WATER, TUB_RIM = 500.0, 462.0, 32, 300, 336
TUB_PH = 11.25                   # 16-gon phase: a flat side faces +y (the steps)
PERG = (-1920, -4860, -560, -2720)            # pergola footprint (post outer faces)
PERG_POST, PERG_BEAM_Z, PERG_TOP = 32, 1460, 1600
PERG_RAFT_W, PERG_RAFT_STEP = 40, 64
PERG_HATCH = (-1340, -2980, -1140, -2780)    # x0, y0, x1, y1: lift hatch through the rafters (func_plat)
SOFA_SEAT, SOFA_BACK = 320, 620
NB = (-1400, -2700, 1400, YF, 2400)          # upstairs neighbour's balcony x0, y0, x1, y1, deck top
RAIL_H = 800
BBQ = (-1650, -2260)
AC = (1230, -2260, 1870, -1968, 560)          # x0, y0, x1, y1, top
HEATER = (-230, -3150)
HAMMOCK = (-60, -4050)                        # stand centre; it runs along y
LOUNGERS = ((500, -3700, 90), (1850, -3360, 90))  # x, y, yaw (on the platform)
PLANTERS = ((-460, -4952, 260, -4772),)       # x0, y0, x1, y1 (along the south railing)
ANCHOR = {}


def tw(p): return np.asarray(p, float)


# ------------------------------------------------------------------------------------------------ helpers
class Model:
    """a set of meshes keyed by shader name"""
    def __init__(self): self.m = {}

    def __call__(self, shader):
        if shader not in self.m: self.m[shader] = Mesh()
        return self.m[shader]

    def surfaces(self, anchor):
        out = []
        for k, (sh, M) in enumerate(self.m.items()):
            if not M.T: continue
            M.V = [np.asarray(v) - np.asarray(anchor, float) for v in M.V]
            out.append(M.surface(f's{k}', f'{MD}/b_{sh}'))
        return out


def bar(M, a, b, r, n=8, caps=True):
    tube(M, [tw(a), tw(b)], [r, r], n, caps=(caps, caps))


def box(M, mn, mx, r=2.0, tile=128.0, k=2, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def cyl(M, c, r, z0, z1, n=16, caps=True, utile=1.0):
    revolve(M, [(r, z0), (r, z1)], utile, n=n, cx=c[0], cy=c[1], v_of=lambda rr, z: -z / 256)
    if caps:
        disc(M, r, z1, up=True, n=n, cx=c[0], cy=c[1]); disc(M, r, z0, up=False, n=n, cx=c[0], cy=c[1])


def cushion(M, mn, mx, puff=14.0, r=18.0):
    mn = tw(mn); mx = tw(mx); c = (mn + mx) / 2; H = (mx - mn) / 2
    def inf(x, y, z, n):
        u = 1 - ((x - c[0]) / H[0]) ** 2; v = 1 - ((y - c[1]) / H[1]) ** 2; w = 1 - ((z - c[2]) / H[2]) ** 2
        return puff * max(0.0, min(u, 1)) * max(0.0, min(v, 1)) * max(0.0, min(w, 1)) ** 0.3 * 0.5
    rbox(M, mn, mx, r=r, k=4, tile=128, inflate=inf)


def ngon16(cx, cy, r, phase=TUB_PH):
    return [(cx + r * math.cos(math.radians(phase + 22.5 * i)), cy + r * math.sin(math.radians(phase + 22.5 * i))) for i in range(16)]


# ================================================================================================ hot tub
def hottub():
    X = Model()
    cx, cy = TUB
    ro, ri, z0, zr = TUB_RO, TUB_RI, TUB_FLOOR, TUB_RIM
    st = X('cedar_v'); band = X('steel_dark'); rim = X('cedar')
    # outer staves (only above the platform shows; start just below it), slightly faceted (48 staves)
    revolve(st, [(ro + 3, PLAT[4]), (ro + 3, zr - 6), (ro - 2, zr)], 12.0, n=48, cx=cx, cy=cy, v_of=lambda r, z: -z / 128)
    # inner wall: 460 round (stays just outside the 16-gon apothem 453 on the flats)
    revolve(X('cedar_in'), [(ri - 2, zr - 2), (ri - 2, z0)], 12.0, n=48, cx=cx, cy=cy, inward=True, v_of=lambda r, z: -z / 128)
    # rim cap
    disc(rim, ro + 4, zr, up=True, n=48, cx=cx, cy=cy, r_in=ri - 2)
    for zb in (PLAT[4] + 24, zr - 30):
        revolve(band, [(ro + 5, zb - 7), (ro + 6, zb), (ro + 5, zb + 7)], 6.0, n=48, cx=cx, cy=cy)
    # jets + underwater LED ring (glow) on the inner wall
    for k in range(8):
        a = math.radians(30 + 45 * k)
        c = np.array([cx + (ri - 3) * math.cos(a), cy + (ri - 3) * math.sin(a), 170.0])
        if abs(math.sin(a) - 1) < 0.05: continue
        d = np.array([-math.cos(a), -math.sin(a), 0])
        tube(X('chrome'), [c, c + d * 6], [10, 8], 10, caps=(False, True))
    for k in range(24):
        a = math.radians(7.5 + 15 * k)
        c = np.array([cx + (ri - 3) * math.cos(a), cy + (ri - 3) * math.sin(a), 90.0])
        d = np.array([-math.cos(a), -math.sin(a), 0])
        tube(X('led_blue'), [c, c + d * 3], [6, 5], 8, caps=(False, True))
    # water surface: a smooth disc just inside the wall (the water volume itself is a nodraw brush)
    disc(X('tub_water'), ri - 2, TUB_WATER, up=True, n=48, cx=cx, cy=cy, uvscale=400)
    # folded tub cover leaning against the platform side? -> keep the rim clear; a towel over the rim instead
    tw_ = X('towel_stripe')
    a = math.radians(-70)
    for k, (r0, r1) in enumerate(((ri - 10, ro + 10),)):
        p0 = np.array([cx + r0 * math.cos(a), cy + r0 * math.sin(a), zr + 1.0])
        e = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-math.sin(a), math.cos(a), 0])
        X('towel_stripe').quad(p0 - s * 80, p0 + s * 80, p0 + s * 80 + e * (r1 - r0), p0 - s * 80 + e * (r1 - r0), tile=200)
        q0 = p0 + e * (r1 - r0)
        X('towel_stripe').quad(q0 - s * 80, q0 + s * 80, q0 + s * 80 + np.array([0, 0, -64.0]) + e * 6, q0 - s * 80 + np.array([0, 0, -64.0]) + e * 6, tile=200)
    # rubber duck floating = no (floating model). A bottle + two glasses on the rim instead
    for (ang, kind) in ((150, 'bottle'), (165, 'glass'), (175, 'glass')):
        a = math.radians(ang); r = (ri + ro) / 2
        c = (cx + r * math.cos(a), cy + r * math.sin(a))
        if kind == 'bottle':
            revolve(X('bottle_green'), [(0.01, zr), (12, zr), (12, zr + 60), (5, zr + 80), (5, zr + 96), (0.01, zr + 96)], 1.0, n=16, cx=c[0], cy=c[1])
        else:
            revolve(X('glass_m'), [(0.01, zr), (8, zr), (2, zr + 4), (2, zr + 30), (11, zr + 40), (12, zr + 62)], 1.0, n=14, cx=c[0], cy=c[1])
    ANCHOR['b_hottub'] = (cx, cy, 0)
    return X


# ================================================================================================ pergola
def pergola_posts():
    x0, y0, x1, y1 = PERG
    p = PERG_POST
    ym = (y0 + y1) / 2
    return [(x0 + p, y0 + p), (x1 - p, y0 + p), (x0 + p, y1 - p), (x1 - p, y1 - p), (x0 + p, ym), (x1 - p, ym)]


def pergola_rafters():
    """(y0, y1, x0, x1) of the walkable rafters (along x) on top of the beams; the ones crossing the lift hatch are split"""
    x0, y0, x1, y1 = PERG
    hx0, hy0, hx1, hy1 = PERG_HATCH
    out = []
    y = y0
    while y + PERG_RAFT_W <= y1:
        if y + PERG_RAFT_W > hy0 and y < hy1:
            out += [(y, y + PERG_RAFT_W, x0 - 48, hx0), (y, y + PERG_RAFT_W, hx1, x1 + 48)]
        else:
            out.append((y, y + PERG_RAFT_W, x0 - 48, x1 + 48))
        y += PERG_RAFT_STEP
    return out


def pergola():
    X = Model()
    x0, y0, x1, y1 = PERG
    p = PERG_POST
    W = X('timber'); Wd = X('timber_dark')
    for (x, y) in pergola_posts():
        box(W, (x - p, y - p, 0), (x + p, y + p, PERG_BEAM_Z), r=3, tile=128)
        box(Wd, (x - p - 6, y - p - 6, 0), (x + p + 6, y + p + 6, 18), r=2, tile=64)
        for sy in (-1, 1):
            if (sy < 0 and y <= y0 + p + 1) or (sy > 0 and y >= y1 - p - 1): continue
            bar(W, (x, y + sy * p, PERG_BEAM_Z - 260), (x, y + sy * 240, PERG_BEAM_Z - 10), 9, n=6)     # knee braces
    for xb in (x0, x1 - 2 * p):
        box(W, (xb - 8, y0 - 40, PERG_BEAM_Z), (xb + 2 * p + 8, y1 + 40, PERG_TOP - 60), r=3, tile=128)  # beams along y
    for (ya, yb, xa, xb) in pergola_rafters():
        box(Wd, (xa, ya, PERG_TOP - 60), (xb, yb, PERG_TOP), r=2, tile=128)                            # rafters along x
    # climbing vine along the front beam + leaf cards on top (alpha, nonsolid)
    V = X('vine')
    rng = np.random.default_rng(11)
    for k in range(70):
        x = rng.uniform(x0 - 30, x1 + 30); y = rng.uniform(y0, y0 + 500) if k % 3 else rng.uniform(y0, y1)
        s_ = rng.uniform(60, 120); a = rng.uniform(0, math.pi)
        q = [np.array([x + math.cos(a + t) * s_, y + math.sin(a + t) * s_, PERG_TOP + 2 + rng.uniform(0, 4)]) for t in (0, math.pi / 2, math.pi, 1.5 * math.pi)]
        V.poly(q, (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in range(18):          # dangling down the south face
        x = x0 + 30 + (x1 - x0 - 60) * k / 17 + rng.uniform(-20, 20); h = rng.uniform(140, 320)
        V.poly([(x - 55, y0 - 44, PERG_TOP - 40), (x + 55, y0 - 44, PERG_TOP - 40), (x + 55, y0 - 44, PERG_TOP - 40 - h), (x - 55, y0 - 44, PERG_TOP - 40 - h)],
               (0, -1, 0), [(0, 0), (1, 0), (1, h / 110), (0, h / 110)])
    # festoon lights sagging along both beams' outer faces and across the south end
    Cb = X('cable'); runs = []
    for xb in (x0 - 12, x1 + 12):
        for (ya, yb) in ((y0, (y0 + y1) / 2), ((y0 + y1) / 2, y1)):
            runs.append([(xb, ya + (yb - ya) * t, PERG_BEAM_Z - 30 - 110 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 15)])
    runs.append([(x0 + (x1 - x0) * t, y0 - 50, PERG_BEAM_Z - 30 - 150 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 21)])
    cols = ['bulb_warm', 'bulb_warm', 'bulb_pink', 'bulb_warm', 'bulb_green']
    k = 0
    for pts in runs:
        tube(Cb, pts, 1.6, nseg=4, caps=(False, False))
        for q in pts[1:-1]:
            sphere(X(cols[k % len(cols)]), (q[0], q[1], q[2] - 14), 9, nu=8, nv=5); k += 1
            bar(Cb, q, (q[0], q[1], q[2] - 6), 2.5, n=5)
    # hanging baskets from the front corners of the beams (chains + pot + trailing leaves)
    for (x, y) in ((x0 + p, y0 + 300), (x1 - p, y0 + 300), (x0 + p, y1 - 400), (x1 - p, y1 - 400)):
        top = PERG_BEAM_Z
        bz = top - 520
        for a in (0, 2.1, 4.2):
            bar(X('chain'), (x, y, top), (x + 70 * math.cos(a), y + 70 * math.sin(a), bz + 120), 2.2, n=4)
        revolve(X('terracotta'), [(0.01, bz), (60, bz), (78, bz + 40), (86, bz + 120), (82, bz + 124)], 2.0, n=20, cx=x, cy=y)
        rr = np.random.default_rng(int(x + y) % 997)
        for j in range(14):
            a = rr.uniform(0, 2 * math.pi); h = rr.uniform(120, 300)
            c = np.array([x + 80 * math.cos(a), y + 80 * math.sin(a), bz + 120]); o = np.array([math.cos(a), math.sin(a), 0])
            s = np.array([-math.sin(a), math.cos(a), 0])
            X('trail').quad(c - s * 40, c + s * 40, c + s * 40 + o * 30 - np.array([0, 0, h]), c - s * 40 + o * 30 - np.array([0, 0, h]), tile=120)
        ellipsoid(X('trail_top'), (x, y, bz + 124), 84, 84, 40, 12, 6, flat_bottom=0)
    # wind chime from the middle of the south beam
    cxw, cyw = (x0 + x1) / 2, y0 - 50
    disc(X('timber_dark'), 60, PERG_BEAM_Z - 140, up=True, n=12, cx=cxw, cy=cyw); disc(X('timber_dark'), 60, PERG_BEAM_Z - 150, up=False, n=12, cx=cxw, cy=cyw)
    bar(X('chain'), (cxw, cyw, PERG_BEAM_Z - 140), (cxw, cyw, PERG_BEAM_Z - 30), 2, n=4)
    for j in range(6):
        a = 2 * math.pi * j / 6; L = 160 + 40 * (j % 3)
        c = (cxw + 44 * math.cos(a), cyw + 44 * math.sin(a))
        bar(X('chrome'), (c[0], c[1], PERG_BEAM_Z - 160), (c[0], c[1], PERG_BEAM_Z - 160 - L), 6, n=8)
    ANCHOR['b_pergola'] = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return X


# ================================================================================================ rattan sofa + table + rug
SOFA_PARTS = []      # (x0, y0, x1, y1, z1) collision boxes, filled by sofa()


def sofa():
    X = Model()
    x0, y0, x1, y1 = PERG
    R = X('rattan'); C = X('cushion_out'); P = X('cushion_pink')
    # long side along the west posts, short side along the south
    lx0, lx1, ly0, ly1 = x0 + 110, x0 + 470, y0 + 140, y0 + 1500
    sx0, sx1, sy0, sy1 = lx1, x0 + 1150, y0 + 140, y0 + 500
    SOFA_PARTS.clear()
    for (a0, b0, a1, b1, back) in ((lx0, ly0, lx1, ly1, 'w'), (sx0, sy0, sx1, sy1, 's')):
        box(R, (a0, b0, 40), (a1, b1, 220), r=18, tile=96)
        for (fx, fy) in ((a0 + 30, b0 + 30), (a1 - 30, b0 + 30), (a0 + 30, b1 - 30), (a1 - 30, b1 - 30)):
            box(X('steel_dark'), (fx - 16, fy - 16, 0), (fx + 16, fy + 16, 40), r=4, tile=64)
        if back == 'w':
            box(R, (a0, b0, 220), (a0 + 100, b1, SOFA_BACK), r=22, tile=96)
            n = 3
            for k in range(n):
                ya = b0 + 10 + (b1 - b0 - 20) * k / n; yb = b0 + 10 + (b1 - b0 - 20) * (k + 1) / n - 12
                cushion(C, (a0 + 110, ya, 220), (a1 - 10, yb, SOFA_SEAT), 16)
                cushion(C, (a0 + 100, ya + 10, SOFA_SEAT), (a0 + 190, yb - 10, SOFA_BACK - 30), 20)
            SOFA_PARTS.append((a0 + 100, b0, a1, b1, SOFA_SEAT)); SOFA_PARTS.append((a0, b0, a0 + 100, b1, SOFA_BACK))
        else:
            box(R, (a0, b0, 220), (a1, b0 + 100, SOFA_BACK), r=22, tile=96)
            box(R, (a1 - 100, b0, 220), (a1, b1, 440), r=22, tile=96)                    # arm
            n = 2
            for k in range(n):
                xa = a0 + 10 + (a1 - 100 - a0 - 10) * k / n; xb = a0 + 10 + (a1 - 100 - a0 - 10) * (k + 1) / n - 12
                cushion(C, (xa, b0 + 110, 220), (xb, b1 - 10, SOFA_SEAT), 16)
                cushion(C, (xa + 10, b0 + 100, SOFA_SEAT), (xb - 10, b0 + 190, SOFA_BACK - 30), 20)
            SOFA_PARTS.append((a0, b0 + 100, a1 - 100, b1, SOFA_SEAT)); SOFA_PARTS.append((a0, b0, a1, b0 + 100, SOFA_BACK))
            SOFA_PARTS.append((a1 - 100, b0 + 100, a1, b1, 440))
    # throw pillows
    for (c, sz) in (((lx0 + 200, ly0 + 300, SOFA_SEAT + 70), 1.0), ((lx0 + 190, ly1 - 250, SOFA_SEAT + 70), 0.9), ((sx0 + 400, sy0 + 200, SOFA_SEAT + 70), 1.0)):
        R_ = rot_axis((0, 1, 0), 0.5)
        ellipsoid(P, c, 90 * sz, 26, 90 * sz, 14, 8, R=rot_z(0.3) @ R_)
    ANCHOR['b_sofa'] = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return X


TABLE = (-1300, -4100, -900, -3740, 260)        # x0, y0, x1, y1, top


def table_out():
    X = Model()
    x0, y0, x1, y1, top = TABLE
    box(X('teak'), (x0, y0, top - 30), (x1, y1, top), r=6, tile=96)
    box(X('teak'), (x0 + 30, y0 + 30, 60), (x1 - 30, y1 - 30, 80), r=4, tile=96)            # lower shelf
    for (fx, fy) in ((x0 + 30, y0 + 30), (x1 - 30, y0 + 30), (x0 + 30, y1 - 30), (x1 - 30, y1 - 30)):
        box(X('teak'), (fx - 18, fy - 18, 0), (fx + 18, fy + 18, top - 30), r=3, tile=96)
    # lantern with a candle, a bowl of crisps, a rolled joint on a little tray, phone
    cx, cy = x0 + 110, y0 + 120
    box(X('steel_dark'), (cx - 44, cy - 44, top), (cx + 44, cy + 44, top + 10), r=2)
    for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bar(X('steel_dark'), (cx + sx * 40, cy + sy * 40, top + 10), (cx + sx * 40, cy + sy * 40, top + 150), 4, n=6)
    box(X('lantern_glass'), (cx - 38, cy - 38, top + 12), (cx + 38, cy + 38, top + 148), r=1, faces='nsew')
    revolve(X('steel_dark'), [(48, top + 150), (52, top + 156), (20, top + 190), (0.01, top + 196)], 1, n=4, cx=cx, cy=cy, a0=45, a1=405)
    revolve(X('candle'), [(0.01, top + 10), (16, top + 10), (16, top + 70), (0.01, top + 70)], 1, n=12, cx=cx, cy=cy)
    ellipsoid(X('flame'), (cx, cy, top + 84), 6, 6, 14, 8, 6)
    bx, by = x1 - 140, y1 - 130
    revolve(X('ceramic_w'), [(0.01, top), (50, top), (80, top + 30), (96, top + 60), (92, top + 62), (74, top + 34), (0.01, top + 26)], 2, n=24, cx=bx, cy=by)
    rr = np.random.default_rng(5)
    for k in range(14):
        a = rr.uniform(0, 2 * math.pi); d = rr.uniform(0, 60)
        c = np.array([bx + d * math.cos(a), by + d * math.sin(a), top + 40 + rr.uniform(0, 14)])
        ellipsoid(X('crisp'), c, 24, 20, 3, 8, 4, R=rot_z(a) @ rot_axis((1, 0, 0), rr.uniform(-0.6, 0.6)))
    box(X('teak'), (x0 + 210, y1 - 120, top), (x0 + 330, y1 - 40, top + 6), r=2)                 # tray
    tube(X('paper'), [(x0 + 220, y1 - 80, top + 13), (x0 + 310, y1 - 74, top + 13)], [5, 7], 10)
    ANCHOR['b_table'] = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return X


# ================================================================================================ kettle BBQ
def bbq():
    X = Model()
    cx, cy = BBQ
    zc = 560.0; R = 210.0
    # bowl: lower half sphere, lid: upper half (lid slightly lifted on one side? keep closed, with a vent)
    prof_b = [(R * math.sin(t), zc - R * math.cos(t)) for t in np.linspace(0.05, math.pi / 2, 12)]
    revolve(X('enamel_black'), [(0.01, zc - R)] + prof_b, 3, n=32, cx=cx, cy=cy)
    prof_l = [(R * math.cos(t) + 2, zc + 6 + R * 0.9 * math.sin(t)) for t in np.linspace(0, math.pi / 2 - 0.08, 12)]
    revolve(X('enamel_black'), prof_l + [(0.01, zc + 6 + R * 0.9)], 3, n=32, cx=cx, cy=cy)
    revolve(X('chrome'), [(R + 4, zc - 2), (R + 6, zc + 3), (R + 4, zc + 8)], 4, n=32, cx=cx, cy=cy)          # lip band
    revolve(X('chrome'), [(30, zc + 6 + R * 0.9 - 2), (32, zc + 6 + R * 0.9 + 8), (0.01, zc + 6 + R * 0.9 + 10)], 1, n=12, cx=cx, cy=cy)  # vent
    # handles
    bar(X('wood_handle'), (cx - 70, cy - R - 26, zc + 150), (cx + 70, cy - R - 26, zc + 150), 12, n=8)
    for sx in (-60, 60):
        bar(X('chrome'), (cx + sx, cy - R * 0.85, zc + 110), (cx + sx, cy - R - 26, zc + 150), 4, n=6)
    # legs (three), wheels, ash catcher, bottom rack
    for k, a in enumerate((90, 210, 330)):
        a = math.radians(a)
        top = np.array([cx + R * 0.55 * math.cos(a), cy + R * 0.55 * math.sin(a), zc - R * 0.8])
        bot = np.array([cx + R * 0.95 * math.cos(a), cy + R * 0.95 * math.sin(a), 40.0])
        bar(X('chrome'), top, bot, 9, n=8)
        if k > 0:
            c = bot + np.array([0, 0, -6.0])
            d = np.array([-math.sin(a), math.cos(a), 0])
            tube(X('rubber_black'), [c - d * 14, c + d * 14], [36, 36], 16)
        else:
            revolve(X('rubber_black'), [(14, 0), (16, 40)], 1, n=10, cx=bot[0], cy=bot[1])
    revolve(X('chrome'), [(0.01, 200), (120, 200), (124, 206), (0.01, 206)], 1, n=24, cx=cx, cy=cy)
    revolve(X('enamel_black'), [(0.01, zc - R - 60), (70, zc - R - 60), (80, zc - R - 30), (0.01, zc - R - 30)], 1, n=20, cx=cx, cy=cy)
    # warm glow leaking at the lid seam + a thermometer
    revolve(X('ember'), [(R + 1, zc + 2), (R + 1, zc + 6)], 6, n=32, cx=cx, cy=cy)
    disc(X('chrome'), 20, zc + 120, up=True, n=12, cx=cx + 60, cy=cy - 60)
    ANCHOR['b_bbq'] = (cx, cy, 0)
    return X


# ================================================================================================ AC condenser + fan
def ac_unit():
    X = Model()
    x0, y0, x1, y1, top = AC
    box(X('ac_side'), (x0, y0, 40), (x1, y1, top - 20), r=10, tile=128, faces='nsewb')
    box(X('ac_top'), (x0, y0, top - 20), (x1, y1, top), r=8, tile=128, faces='nsewt')
    box(X('steel_dark'), (x0 + 40, y0 + 20, 0), (x0 + 120, y1 - 20, 40), r=3)
    box(X('steel_dark'), (x1 - 120, y0 + 20, 0), (x1 - 40, y1 - 20, 40), r=3)
    # fan guard ring (the blades are a separate func_rotating model)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    disc(X('fan_hole'), 168, top + 0.6, up=True, n=32, cx=cx, cy=cy)
    for r in (60, 110, 160):
        revolve(X('chrome'), [(r - 3, top + 1), (r, top + 4), (r + 3, top + 1)], 1, n=32, cx=cx, cy=cy)
    for k in range(8):
        a = math.pi * k / 8
        bar(X('chrome'), (cx - 160 * math.cos(a), cy - 160 * math.sin(a), top + 3), (cx + 160 * math.cos(a), cy + 160 * math.sin(a), top + 3), 2.5, n=4)
    # copper pipes into the wall
    for dz in (100, 150):
        tube(X('copper'), [(x0 + 200, y1 - 10, dz), (x0 + 200, y1 + 60, dz), (x0 + 200, y1 + 60, dz + 300), (x0 + 200, YF + 1, dz + 300)][:3] +
             [(x0 + 200, YF + 2, dz + 300)], [9, 9, 9, 9], 8)
    # a dozing cat-shaped cushion? no. Two potted cacti on the top as decoration
    for (px, py) in ((x0 + 90, y0 + 70), (x1 - 90, y1 - 70)):
        revolve(X('terracotta'), [(0.01, top), (36, top), (44, top + 70), (40, top + 72)], 1, n=16, cx=px, cy=py)
        ellipsoid(X('cactus'), (px, py, top + 130), 30, 30, 70, 12, 8)
    ANCHOR['b_ac'] = (cx, cy, 0)
    return X


def ac_fan():
    X = Model()
    cx, cy = (AC[0] + AC[2]) / 2, (AC[1] + AC[3]) / 2; zw = AC[4] - 14; z = 0.0
    cyl(X('steel_dark'), (0, 0), 30, z - 10, z + 4, 16)
    for k in range(4):
        a = 2 * math.pi * k / 4
        d = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-math.sin(a), math.cos(a), 0])
        p0 = np.array([0, 0, z]) + d * 28
        q = [p0 - s * 22, p0 + s * 30 + np.array([0, 0, 6]), p0 + d * 120 + s * 60 + np.array([0, 0, 8]), p0 + d * 130 - s * 30]
        X('fan_blade').quad(*q, tile=128)
        X('fan_blade').quad(*q[::-1], tile=128)
    ANCHOR['b_acfan'] = (0, 0, 0)
    return X, (cx, cy, zw)


# ================================================================================================ patio heater
def heater():
    X = Model()
    cx, cy = HEATER
    revolve(X('steel_green'), [(0.01, 0), (150, 0), (150, 20), (124, 40), (124, 560), (100, 600), (40, 620)], 2, n=32, cx=cx, cy=cy)
    revolve(X('steel_green'), [(22, 620), (22, 1640)], 1, n=12, cx=cx, cy=cy)
    # burner (glowing mesh cylinder) + reflector hood
    revolve(X('heater_glow'), [(46, 1640), (46, 1760)], 4, n=20, cx=cx, cy=cy)
    disc(X('steel_green'), 48, 1640, up=False, n=20, cx=cx, cy=cy)
    revolve(X('steel_green'), [(48, 1762), (300, 1810), (304, 1820), (296, 1822), (44, 1778)], 3, n=32, cx=cx, cy=cy)
    revolve(X('steel_green'), [(44, 1778), (0.01, 1790)], 1, n=20, cx=cx, cy=cy)
    disc(X('steel_green'), 50, 1762, up=True, n=20, cx=cx, cy=cy)
    # control knob + regulator
    tube(X('chrome'), [(cx + 124, cy, 480), (cx + 140, cy, 480)], [14, 14], 10)
    ANCHOR['b_heater'] = (cx, cy, 0)
    return X


# ================================================================================================ loungers
def lounger(x, y, yaw, z0):
    X = Model()
    R = rot_z(math.radians(yaw))
    def P(p): return R @ np.asarray(p, float) + np.array([x, y, z0])
    L, Wd = 900.0, 300.0
    # frame: two side rails following the profile (flat seat, raised back)
    prof = [(-L / 2, 220), (L / 2 - 340, 220), (L / 2 - 330, 240), (L / 2, 620)]
    for sx in (-Wd / 2, Wd / 2):
        tube(X('alu'), [P((px, sx, pz)) for (px, pz) in prof], [10] * 4, 8)
        for (px, pz) in ((-L / 2 + 30, 220), (L / 2 - 360, 220)):
            bar(X('alu'), P((px, sx, pz)), P((px, sx, 0)), 10, n=8)
    # wheels at the head, crossbars
    for px in (-L / 2 + 30, L / 2 - 360):
        bar(X('alu'), P((px, -Wd / 2, 210)), P((px, Wd / 2, 210)), 8, n=8)
    # cushion (seat + back) as rounded slabs in the lounger's frame
    seat = Mesh(); rbox(seat, (-L / 2 + 10, -Wd / 2 + 6, 222), (L / 2 - 340, Wd / 2 - 6, 262), r=14, k=3, tile=128)
    back = Mesh(); rbox(back, (0, -Wd / 2 + 6, 0), (390, Wd / 2 - 6, 40), r=14, k=3, tile=128)
    Rb = R @ rot_axis((0, 1, 0), -math.atan2(380, 340))
    X('cushion_stripe').add(seat, R, (x, y, z0))
    X('cushion_stripe').add(back, Rb, P((L / 2 - 340, 0, 240)))
    return X, [(P((-L / 2, -Wd / 2, 0)), P((L / 2 - 330, Wd / 2, 0)))]


# ================================================================================================ planters
def planter(x0, y0, x1, y1, h=320):
    X = Model()
    box(X('cedar'), (x0, y0, 0), (x1, y1, h), r=6, tile=128, faces='nsewb')
    box(X('cedar'), (x0 - 10, y0 - 10, h), (x1 + 10, y1 + 10, h + 16), r=4, tile=128, faces='nsewtb')
    # soil (a sunken lid) - the top surface the plants stand on is soil at h - 24, as a separate quad ring + plane
    X('soil').quad((x0 + 10, y0 + 10, h - 24), (x1 - 10, y0 + 10, h - 24), (x1 - 10, y1 - 10, h - 24), (x0 + 10, y1 - 10, h - 24), tile=128, n=(0, 0, 1))
    for (p, q, n) in (((x0 + 10, y0 + 10), (x1 - 10, y0 + 10), (0, 1, 0)), ((x1 - 10, y1 - 10), (x0 + 10, y1 - 10), (0, -1, 0)),
                      ((x0 + 10, y1 - 10), (x0 + 10, y0 + 10), (1, 0, 0)), ((x1 - 10, y0 + 10), (x1 - 10, y1 - 10), (-1, 0, 0))):
        X('cedar').quad((p[0], p[1], h - 24), (q[0], q[1], h - 24), (q[0], q[1], h), (p[0], p[1], h), tile=128, n=n)
    # herbs: leafy mounds of alpha cards
    rr = np.random.default_rng(int(abs(x0 + y0)) % 1000)
    for k in range(int((x1 - x0) / 60)):
        c = np.array([rr.uniform(x0 + 40, x1 - 40), rr.uniform(y0 + 40, y1 - 40), h - 24])
        for j in range(3):
            a = rr.uniform(0, math.pi); s_ = rr.uniform(50, 90); hh = rr.uniform(80, 170)
            d = np.array([math.cos(a), math.sin(a), 0])
            X('herb_card').quad(c - d * s_, c + d * s_, c + d * s_ + np.array([0, 0, hh]), c - d * s_ + np.array([0, 0, hh]), tile=2 * s_)
    return X


# ================================================================================================ railing
def railing(p0, p1, h=RAIL_H, post_step=512, posts_at_ends=(True, True)):
    """glass balustrade from p0 to p1 (x, y at deck z0): steel posts, glass panels, a round handrail"""
    X = Model()
    p0 = np.array([p0[0], p0[1], p0[2]], float); p1 = np.array([p1[0], p1[1], p1[2]], float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n_ = max(1, int(round(L / post_step)))
    pts = [p0 + d * L * k / n_ for k in range(n_ + 1)]
    nrm = np.cross(np.array([0, 0, 1.0]), d)
    for k, p in enumerate(pts):
        if (k == 0 and not posts_at_ends[0]) or (k == n_ and not posts_at_ends[1]): continue
        box(X('steel_dark'), (p[0] - 14, p[1] - 14, p[2]), (p[0] + 14, p[1] + 14, p[2] + h - 20), r=3, tile=64)
    for k in range(n_):
        a = pts[k] + d * 20; b = pts[k + 1] - d * 20
        q = [a + np.array([0, 0, 40]), b + np.array([0, 0, 40]), b + np.array([0, 0, h - 60]), a + np.array([0, 0, h - 60])]
        X('rail_glass').quad(*q, tile=256, n=nrm); X('rail_glass').quad(*q[::-1], tile=256, n=-nrm)
        for zz in (40, h - 60):        # glass clamps
            for t in (0.15, 0.85):
                c = a + (b - a) * t + np.array([0, 0, zz])
                box(X('chrome'), c - np.array([10, 10, 8]), c + np.array([10, 10, 8]), r=2)
    tube(X('steel_dark'), [p0 + np.array([0, 0, h - 10]), p1 + np.array([0, 0, h - 10])], [16, 16], 12)
    return X


# ================================================================================================ sliding door frame + parked panels
def slider():
    X = Model()
    x0, x1, h = DOOR
    f = X('alu_dark')
    box(f, (x0 - 40, YF - 24, 0), (x0, YF, h + 40), r=3)
    box(f, (x1, YF - 24, 0), (x1 + 40, YF, h + 40), r=3)
    box(f, (x0 - 40, YF - 24, h), (x1 + 40, YF, h + 40), r=3)
    # two glass panels slid out sideways on an outer track (parked against the facade)
    for (a, b) in ((x0 - 760, x0 - 40), (x1 + 40, x1 + 760)):
        box(f, (a, YF - 48, 0), (b, YF - 28, 30), r=2)
        box(f, (a, YF - 48, h - 10), (b, YF - 28, h + 40), r=2)
        box(f, (a, YF - 48, 30), (a + 30, YF - 28, h - 10), r=2); box(f, (b - 30, YF - 48, 30), (b, YF - 28, h - 10), r=2)
        q = [(a + 30, YF - 38, 30), (b - 30, YF - 38, 30), (b - 30, YF - 38, h - 10), (a + 30, YF - 38, h - 10)]
        X('door_glass').quad(*q, tile=256, n=(0, -1, 0)); X('door_glass').quad(*q[::-1], tile=256, n=(0, 1, 0))
        box(X('chrome'), (b - 70 if a < 0 else a + 50, YF - 54, 700), (b - 50 if a < 0 else a + 70, YF - 48, 900), r=2)   # handle
    # door track on the floor (flush) is a brush; a doormat is a brush too
    ANCHOR['b_slider'] = (0, YF, 0)
    return X


# ================================================================================================ hammock on a stand
def hammock():
    X = Model()
    cx, cy = HAMMOCK
    L = 1100.0
    ya, yb = cy - L / 2, cy + L / 2
    st = X('timber')
    # curved wooden arc stand: two arcs (one each side) joined by a base beam
    arc = [(cx, ya + (yb - ya) * t, 60 + 880 * abs(2 * t - 1) ** 1.6) for t in np.linspace(0, 1, 21)]
    for side in (-1, 1):
        a = [(cx + side * 60, y, z) for (_, y, z) in arc]
        tube(st, a, [22] * len(a), 10)
    box(st, (cx - 80, ya - 20, 0), (cx + 80, ya + 60, 60), r=6); box(st, (cx - 80, yb - 60, 0), (cx + 80, yb + 20, 60), r=6)
    box(st, (cx - 30, ya, 20), (cx + 30, yb, 60), r=6)
    for side in (-1, 1):
        bar(st, (cx + side * 60, ya + 30, 60), (cx + side * 60, ya + 30, 30), 22)
    # the hammock: woven bed sagging between the two hook ends (z 940 at the tips, lowest ~420)
    ha, hb = ya + 40, yb - 40
    U, V = 24, 8
    P = np.zeros((V + 1, U + 1, 3)); UV = np.zeros((V + 1, U + 1, 2))
    for i in range(V + 1):
        s = -1 + 2 * i / V
        for j in range(U + 1):
            t = j / U
            y = ha + 180 + (hb - ha - 360) * t
            wdt = 170 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.6
            sag = 430 + 430 * (2 * t - 1) ** 2 - 40 * (1 - s * s)
            P[i, j] = (cx + s * wdt, y, sag); UV[i, j] = (t * 3, (s + 1) / 2)
    X('hammock').grid(P, grid_normals(P), UV)
    for (tip, end) in ((ha, P[:, 0]), (hb, P[:, -1])):
        for q in end[::2]:
            bar(X('rope'), (cx, tip, 900), q, 2.5, n=4, caps=False)
    ANCHOR['b_hammock'] = (cx, cy, 0)
    return X


# ================================================================================================ deck box + cooler
DECKBOX = (-240, -2420, 240, -2180, 300)       # x0, y0, x1, y1, top
COOLER = (-900, -2240, -600, -2040, 260)


def deckbox():
    X = Model()
    x0, y0, x1, y1, top = DECKBOX
    box(X('cedar'), (x0, y0, 0), (x1, y1, top - 30), r=6, tile=128, faces='nsewb')
    box(X('cedar_v'), (x0 - 8, y0 - 8, top - 30), (x1 + 8, y1 + 8, top), r=6, tile=128)
    for xx in (x0 + 60, x1 - 60):
        box(X('steel_dark'), (xx - 30, y0 - 12, top - 70), (xx + 30, y0 - 6, top - 30), r=2)
    # a folded hoodie + a skate helmet on the lid
    cushion(X('cushion_pink'), (x0 + 40, y0 + 30, top), (x0 + 220, y1 - 30, top + 40), 8, 10)
    ellipsoid(X('helmet'), (x1 - 110, (y0 + y1) / 2, top), 80, 70, 70, 16, 8, flat_bottom=0)
    ANCHOR['b_deckbox'] = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return X


def cooler():
    X = Model()
    x0, y0, x1, y1, top = COOLER
    box(X('cooler_blue'), (x0, y0, 0), (x1, y1, top - 40), r=14, tile=128, faces='nsewb')
    box(X('cooler_white'), (x0 - 6, y0 - 6, top - 40), (x1 + 6, y1 + 6, top), r=12, tile=128)
    bar(X('cooler_white'), (x0 + 40, (y0 + y1) / 2, top), (x0 + 40, (y0 + y1) / 2, top + 40), 8)
    bar(X('cooler_white'), (x1 - 40, (y0 + y1) / 2, top), (x1 - 40, (y0 + y1) / 2, top + 40), 8)
    bar(X('cooler_white'), (x0 + 40, (y0 + y1) / 2, top + 40), (x1 - 40, (y0 + y1) / 2, top + 40), 8)
    # cans on the lid
    for (dx, col) in ((-40, 'can_red'), (40, 'can_green')):
        c = ((x0 + x1) / 2 + dx, y0 + 50)
        revolve(X(col), [(0.01, top), (20, top), (22, top + 4), (22, top + 70), (18, top + 76), (0.01, top + 76)], 1, n=14, cx=c[0], cy=c[1])
    ANCHOR['b_cooler'] = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return X


# ================================================================================================ garden gnome (upstairs neighbour)
def gnome():
    X = Model()
    cx, cy, z0 = 900.0, -2380.0, float(NB[4])
    revolve(X('gnome_blue'), [(0.01, z0), (70, z0), (78, z0 + 40), (74, z0 + 150), (60, z0 + 190), (0.01, z0 + 200)], 1, n=20, cx=cx, cy=cy)
    sphere(X('gnome_skin'), (cx, cy - 10, z0 + 240), 50, 14, 10)
    ellipsoid(X('gnome_white'), (cx, cy - 40, z0 + 190), 50, 30, 60, 12, 8)
    revolve(X('gnome_red'), [(56, z0 + 262), (40, z0 + 330), (12, z0 + 420), (0.01, z0 + 440)], 1, n=16, cx=cx + 6, cy=cy)
    sphere(X('gnome_skin'), (cx, cy - 58, z0 + 240), 14, 10, 6)
    for sx in (-1, 1):
        ellipsoid(X('steel_dark'), (cx + sx * 34, cy - 10, z0 + 10), 26, 36, 12, 10, 6, flat_bottom=-12)
    ANCHOR['b_gnome'] = (cx, cy, z0)
    return X


# ================================================================================================ textures
_noise, _img, _fill = LM._noise, LM._img, LM._fill
FONTB = LM.FONTB


def tex_cedar(seed=301, vertical=True):
    n = 256
    a = np.zeros((n, n, 3), np.float32) + np.array([168, 96, 58], np.float32)
    g = _noise(n, 3, seed)
    x = np.linspace(0, 1, n)[None, :] if vertical else np.linspace(0, 1, n)[:, None]
    a += (np.sin((x * 14 + g * 0.5) * 2 * math.pi) * 12)[..., None] + _noise(n, 0.7, seed + 1)[..., None] * 6
    if vertical:
        for k in range(0, n, 32): a[:, k:k + 2] *= 0.7
    return _img(a)


def tex_timber(col=(150, 110, 70), seed=303):
    n = 256
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32)
    g = _noise(n, 2, seed)
    a += (np.sin((np.linspace(0, 1, n)[:, None] * 22 + g * 0.6) * 2 * math.pi) * 10)[..., None] + _noise(n, 0.6, seed + 1)[..., None] * 5
    return _img(a)


def tex_rattan():
    n = 128
    yy, xx = np.mgrid[0:n, 0:n]
    w = (np.sin(xx * math.pi / 8) * np.sin(yy * math.pi / 8))
    a = np.zeros((n, n, 3), np.float32) + np.array([96, 70, 48], np.float32) * (0.7 + 0.45 * (w > 0))[..., None]
    a += _noise(n, 0.7, 305)[..., None] * 8
    return _img(a)


def tex_cushion(col, seed):
    n = 128
    a = _fill(n, col, 3, seed)
    yy, xx = np.mgrid[0:n, 0:n]
    a *= (0.94 + 0.06 * ((xx + yy) % 4 < 2))[..., None]
    return _img(a)


def tex_stripe(cols, w=256, h=256, k=8, seed=307):
    a = np.zeros((h, w, 3), np.float32)
    for i in range(k): a[:, i * w // k:(i + 1) * w // k] = np.array(cols[i % len(cols)], np.float32)
    return _img(a + _noise(w, 0.8, seed, h)[..., None] * 4)


def tex_flat(col, n=64, g=3, seed=309): return _img(_fill(n, col, g, seed))


def tex_glow(col, n=32): return _img(np.zeros((n, n, 3), np.float32) + np.array(col, np.float32))


def tex_tub_water():
    n = 256
    a = np.zeros((n, n, 3), np.float32) + np.array([40, 150, 220], np.float32)
    a += _noise(n, 6, 311)[..., None] * np.array([20, 30, 30]) + np.clip(_noise(n, 2, 312), 1.2, 3)[..., None] * 40
    return _img(a)


def tex_vine(seed=313):
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im); rr = np.random.default_rng(seed)
    for _ in range(26):
        x, y = rr.integers(10, 118, 2); r = rr.uniform(9, 17)
        col = (int(rr.uniform(40, 70)), int(rr.uniform(110, 160)), int(rr.uniform(40, 70)), 255)
        d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=col)
    d.line((0, 64, 128, 60), fill=(80, 60, 40, 255), width=3)
    return im


def tex_trail(seed=315):
    im = Image.new('RGBA', (64, 256), (0, 0, 0, 0)); d = ImageDraw.Draw(im); rr = np.random.default_rng(seed)
    for k in range(5):
        x = 6 + k * 13
        d.line((x, 0, x + rr.integers(-6, 6), 250), fill=(70, 110, 40, 255), width=2)
        for y in range(4, 250, 14):
            d.ellipse((x - 7, y, x + 7, y + 9), fill=(60 + rr.integers(0, 40), 140 + rr.integers(0, 40), 60, 255))
    return im


def tex_herb(seed=317):
    im = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im); rr = np.random.default_rng(seed)
    for _ in range(14):
        x = rr.integers(10, 118); top = rr.integers(5, 60)
        d.line((x, 127, x + rr.integers(-10, 10), top), fill=(70, 120, 50, 255), width=3)
        for y in range(top, 120, 12):
            d.ellipse((x - 8, y, x + 8, y + 7), fill=(80 + rr.integers(0, 40), 150 + rr.integers(0, 40), 70, 255))
    return im


def tex_ac_side():
    n = 256
    a = np.zeros((n, n, 3), np.float32) + 200 + _noise(n, 1, 319)[..., None] * 4
    a[::8, :] *= 0.72                         # fins
    return _img(a * np.array([0.98, 1, 1.02]))


def tex_ac_top():
    n = 256
    a = np.zeros((n, n, 3), np.float32) + 196
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - n / 2, yy - n / 2)
    return _img(a + _noise(n, 1, 321)[..., None] * 4)


def tex_heater_glow():
    w, h = 64, 64
    a = np.zeros((h, w, 3), np.float32) + np.array([255, 110, 30], np.float32)
    a *= (0.75 + 0.25 * (np.mgrid[0:h, 0:w][1] % 8 < 4))[..., None]
    return _img(a)


def tex_hammock():
    w, h = 256, 128
    a = np.zeros((h, w, 3), np.float32)
    cols = [(230, 60, 60), (250, 200, 50), (60, 160, 90), (240, 240, 230), (60, 110, 200)]
    for i in range(10): a[i * h // 10:(i + 1) * h // 10] = np.array(cols[i % 5], np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    a *= (0.8 + 0.2 * ((xx // 3 + yy // 3) % 2))[..., None]
    return _img(a)


def make_textures(d):
    sv = lambda nm, im: im.save(os.path.join(d, 'b_' + nm + ('.tga' if im.mode == 'RGBA' else '.jpg')), **({} if im.mode == 'RGBA' else {'quality': 92}))
    sv('cedar_v', tex_cedar()); sv('cedar_in', tex_cedar(323)); sv('cedar', tex_cedar(325, False))
    sv('steel_dark', tex_flat((52, 54, 58), 64, 3, 327)); sv('chrome', tex_flat((200, 204, 210), 64, 3, 329))
    sv('led_blue', tex_glow((90, 200, 255))); sv('tub_water', tex_tub_water())
    sv('towel_stripe', tex_stripe([(250, 250, 245), (240, 90, 60), (250, 250, 245), (40, 130, 200)], k=8))
    sv('bottle_green', tex_flat((30, 110, 50), 32, 5, 331)); sv('glass_m', tex_flat((200, 220, 225), 32, 2, 333))
    sv('timber', tex_timber()); sv('timber_dark', tex_timber((110, 76, 48), 335)); sv('vine', tex_vine())
    sv('cable', tex_flat((20, 20, 20), 32, 2, 337))
    for nm, c in (('bulb_warm', (255, 210, 120)), ('bulb_pink', (255, 120, 200)), ('bulb_green', (130, 255, 140))): sv(nm, tex_glow(c))
    sv('chain', tex_flat((90, 90, 94), 32, 6, 339)); sv('terracotta', tex_flat((176, 92, 56), 64, 6, 341)); sv('trail', tex_trail())
    sv('trail_top', tex_flat((70, 140, 60), 64, 12, 343))
    sv('rattan', tex_rattan()); sv('cushion_out', tex_cushion((232, 226, 210), 345)); sv('cushion_pink', tex_cushion((230, 110, 150), 347))
    sv('teak', tex_timber((150, 98, 56), 349)); sv('lantern_glass', tex_flat((255, 200, 120), 32, 2, 351))
    sv('candle', tex_flat((245, 236, 214), 32, 2, 353)); sv('flame', tex_glow((255, 190, 90))); sv('ceramic_w', tex_flat((236, 234, 228), 64, 2, 355))
    sv('crisp', tex_flat((236, 186, 84), 32, 10, 357)); sv('paper', tex_flat((236, 230, 214), 32, 3, 359))
    sv('enamel_black', tex_flat((24, 24, 26), 64, 2, 361)); sv('wood_handle', tex_timber((120, 70, 40), 363)); sv('rubber_black', tex_flat((22, 22, 22), 32, 3, 365))
    sv('ember', tex_glow((255, 120, 40)))
    sv('ac_side', tex_ac_side()); sv('ac_top', tex_ac_top()); sv('fan_hole', tex_flat((14, 14, 16), 32, 2, 397)); sv('copper', tex_flat((190, 110, 60), 32, 6, 367)); sv('cactus', tex_flat((60, 130, 70), 64, 10, 369))
    sv('fan_blade', tex_flat((40, 40, 44), 32, 2, 371))
    sv('steel_green', tex_flat((40, 70, 56), 64, 3, 373)); sv('heater_glow', tex_heater_glow())
    sv('alu', tex_flat((190, 194, 198), 64, 3, 375)); sv('alu_dark', tex_flat((60, 62, 66), 64, 3, 377))
    sv('cushion_stripe', tex_stripe([(40, 120, 150), (240, 236, 220)], k=10, seed=379))
    sv('soil', tex_flat((58, 40, 28), 64, 12, 381)); sv('herb_card', tex_herb())
    sv('rail_glass', tex_flat((150, 190, 200), 32, 2, 383)); sv('door_glass', tex_flat((140, 170, 190), 32, 2, 385))
    sv('hammock', tex_hammock()); sv('rope', tex_flat((210, 190, 150), 32, 6, 387))
    sv('gnome_blue', tex_flat((50, 80, 190), 64, 3, 389)); sv('gnome_red', tex_flat((210, 40, 40), 64, 3, 391))
    sv('gnome_white', tex_flat((240, 240, 236), 64, 4, 393)); sv('gnome_skin', tex_flat((240, 190, 160), 64, 3, 395))
    sv('helmet', tex_flat((230, 200, 40), 64, 3, 399)); sv('cooler_blue', tex_flat((40, 110, 200), 64, 3, 401)); sv('cooler_white', tex_flat((236, 236, 232), 64, 2, 403))
    sv('can_red', tex_flat((210, 40, 40), 32, 3, 405)); sv('can_green', tex_flat((40, 160, 70), 32, 3, 407))


# ================================================================================================ shaders
def _lm(nm, env=0.0, extra=''):
    """lightmapped misc_model shader (spawnflags 4)"""
    s = f'{MD}/b_{nm}\n{{\n\tqer_editorimage {MD}/b_{nm}\n\tq3map_shadeAngle 40\n{extra}\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n' \
        f'\t{{\n\t\tmap {MD}/b_{nm}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
    if env:
        s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {env} {env} {env} )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def _vs(nm, env=0.0, extra=''):
    s = f'{MD}/b_{nm}\n{{\n\tqer_editorimage {MD}/b_{nm}\n{extra}\t{{\n\t\tmap {MD}/b_{nm}\n\t\trgbGen vertex\n\t}}\n'
    if env:
        s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {env} {env} {env} )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def _alpha(nm):
    return (f'{MD}/b_{nm}\n{{\n\tqer_editorimage {MD}/b_{nm}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tcull none\n'
            f'\t{{\n\t\tmap {MD}/b_{nm}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')


def _glass(nm, k=0.35):
    return (f'{MD}/b_{nm}\n{{\n\tqer_editorimage {MD}/b_{nm}\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tcull none\n\tsort 7\n'
            f'\t{{\n\t\tmap {MD}/b_{nm}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.14 0.16 )\n\t}}\n'
            f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {k} {k} {k} )\n\t\ttcGen environment\n\t}}\n}}\n\n')


def _glow(nm, wave=None):
    st = f'\t\trgbGen wave sin {wave[0]} {wave[1]} {wave[2]} {wave[3]}\n' if wave else '\t\trgbGen identity\n'
    return f'{MD}/b_{nm}\n{{\n\tqer_editorimage {MD}/b_{nm}\n\tsurfaceparm nolightmap\n\t{{\n\t\tmap {MD}/b_{nm}\n{st}\t}}\n}}\n\n'


def shaders():
    S = '// ---- balcony models (balcony_models.py)\n'
    for nm in ('cedar_v', 'cedar_in', 'cedar', 'timber', 'timber_dark', 'rattan', 'teak', 'ac_side', 'ac_top', 'soil', 'terracotta'):
        S += _lm(nm, extra='\tq3map_lightmapSampleSize 8\n')
    for nm, e in (('steel_dark', 0.25), ('chrome', 0.6), ('alu', 0.35), ('alu_dark', 0.2), ('enamel_black', 0.3), ('steel_green', 0.25),
                  ('copper', 0.35)):
        S += _lm(nm, e, extra='\tq3map_lightmapSampleSize 8\n')
    for nm in ('cushion_out', 'cushion_pink', 'cushion_stripe', 'towel_stripe', 'candle', 'ceramic_w', 'crisp', 'paper', 'wood_handle',
               'rubber_black', 'fan_hole', 'cable', 'chain', 'trail_top', 'cactus', 'fan_blade', 'rope', 'gnome_blue', 'gnome_red', 'gnome_white',
               'gnome_skin', 'bottle_green', 'glass_m', 'helmet', 'cooler_blue', 'cooler_white', 'can_red', 'can_green'):
        S += _vs(nm, 0.12 if nm in ('bottle_green', 'glass_m', 'ceramic_w') else 0.0)
    S += _vs('hammock', extra='\tcull none\n\tq3map_shadeAngle 80\n')
    for nm in ('vine', 'trail', 'herb_card'): S += _alpha(nm)
    S += _glass('rail_glass', 0.3) + _glass('door_glass', 0.4) + _glass('lantern_glass', 0.1)
    S += _glow('led_blue') + _glow('flame', (0.85, 0.15, 0, 3.1)) + _glow('ember', (0.8, 0.2, 0, 0.6)) + _glow('heater_glow', (0.85, 0.15, 0.2, 0.4))
    for k, nm in enumerate(('bulb_warm', 'bulb_pink', 'bulb_green')): S += _glow(nm, (0.8, 0.2, k * 0.3, 0.25))
    S += (f'{MD}/b_tub_water\n{{\n\tqer_editorimage {MD}/b_tub_water\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n\tsort 6\n'
          f'\t{{\n\t\tmap {MD}/b_tub_water\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.55 0.6 0.65 )\n\t\ttcMod turb 0 0.05 0 0.25\n\t\ttcMod scroll 0.02 0.03\n\t}}\n'
          f'\t{{\n\t\tmap {MD}/b_tub_water\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.25 0.3 0.35 )\n\t\ttcMod scale 1.7 1.7\n\t\ttcMod scroll -0.03 0.02\n\t}}\n}}\n\n')
    return S


# ================================================================================================ make
def make(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    make_textures(d)
    scales = {}
    def save(name, X, anchor=None):
        a = ANCHOR.get(name, (0, 0, 0)) if anchor is None else anchor
        sc = save_md3(os.path.join(d, name + '.md3'), X.surfaces(a), name=name)
        scales[name] = (sc, a)
    save('b_hottub', hottub()); save('b_pergola', pergola()); save('b_sofa', sofa()); save('b_table', table_out())
    save('b_bbq', bbq()); save('b_ac', ac_unit())
    fan, fc = ac_fan(); save('b_acfan', fan, (0, 0, 0)); scales['b_acfan'] = (scales['b_acfan'][0], fc)
    save('b_heater', heater()); save('b_deckbox', deckbox()); save('b_cooler', cooler()); save('b_hammock', hammock()); save('b_slider', slider()); save('b_gnome', gnome())
    LOUNGER_BOXES.clear()
    for k, (x, y, yaw) in enumerate(LOUNGERS):
        X, boxes = lounger(x, y, yaw, PLAT[4]); LOUNGER_BOXES.extend(boxes)
        save(f'b_lounger{k}', X, (x, y, PLAT[4]))
    for k, (x0, y0, x1, y1) in enumerate(PLANTERS):
        save(f'b_planter{k}', planter(x0, y0, x1, y1), ((x0 + x1) / 2, (y0 + y1) / 2, 0))
    for k, (p0, p1, ends) in enumerate(RAILS):
        a = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, p0[2])
        save(f'b_rail{k}', railing(p0, p1, posts_at_ends=ends), a)
    return shaders(), scales


LOUNGER_BOXES = []
# railing runs: (start, end, posts at ends). South edge in 4 x 1024 runs (sharing posts -> only the first run has the
# west end post), plus the upstairs neighbour's front and sides.
RAILS = [((-2032 + 1024 * k, -4984, 0), (-2032 + 1024 * (k + 1) - (32 if k == 3 else 0), -4984, 0), (k == 0, True)) for k in range(4)] + \
        [((NB[0] + 32, NB[1] + 32, NB[4]), (NB[2] - 32, NB[1] + 32, NB[4]), (True, True)),
         ((NB[0] + 32, NB[1] + 64, NB[4]), (NB[0] + 32, NB[3] - 16, NB[4]), (False, True)),
         ((NB[2] - 32, NB[1] + 64, NB[4]), (NB[2] - 32, NB[3] - 16, NB[4]), (False, True))]


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    sh, sc = make(o)
    import md3tool
    for name, (s, a) in sorted(sc.items()):
        m = md3tool.load(os.path.join(o, MD, name + '.md3'))
        V = np.concatenate([x['verts'] for x in m['surfaces']])
        print(f'{name:14s} scale {s} anchor {tuple(round(v) for v in a)} verts {len(V)} bounds {V.min(0).round()} {V.max(0).round()}')
