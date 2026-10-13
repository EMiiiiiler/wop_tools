"""Custom MD3 map objects for wop_padlounge (Couch Lock). All geometry and art is original and generated here.

    make(out) -> writes models/padlounge/*.md3 + their textures, returns the shader text for them

Models (Padman scale, ~8u per cm; origin = bottom centre unless noted):
  bong            90 cm glass beaker bong: conical beaker (r 170) with green water, bubbling percolator column,
                  ice pinch, straight tube (r 72) with a PADMAN decal, flared mouthpiece, milky smoke rising inside the
                  tube, downstem + bowl packed with herb and a glowing ember. 720 tall: origin at mid-height
                  (BONG_OFS) so every vertex stays inside MD3's +-512.
  lava_purple/_green   lava lamp: brushed-steel base, glowing liquid in a glass bottle, wax blobs that rise and sink
                  (deformVertexes move, one surface per blob, different phases), wax pool at the bottom
  plant_big       potted cannabis plant ~1000 tall: terracotta pot, stalk, branches, ~70 alpha-cutout fan leaves,
                  frosty colas with orange hairs. Origin at mid-height (PLANT_OFS).
  plant_small     same species 700 tall for the grow tent (origin at the pot base)
  ashtray         ceramic ashtray r 110 with a joint resting in a notch (glowing ember), roaches and ash
  grinder         four-piece green anodised herb grinder + its lid lying beside it
  jar             mason stash jar with buds inside (glass, steel lid)
  chips           giant crumpled "MUNCHIES" crisp bag lying on its side (pillow with crimped seams)
  crisps          a spill of ~40 curved crisps
  beanbag         slouchy purple bean bag chair (r ~400) with a sitting dent
  lighter         disposable lighter standing up
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import md3write

MD = 'models/padlounge'
BONG_H, BONG_OFS = 720.0, 360.0
BONG_BEAKER_R, BONG_TUBE_R = 170.0, 72.0
PLANT_OFS = 505.0
PLANT_SMALL_OFS = 330.0
LAVA_H, LAVA_R = 344.0, 60.0
ASH_R, GRINDER_R, JAR_R, JAR_H = 110.0, 52.0, 64.0, 200.0
CHIPS = (380.0, 250.0, 110.0)          # half length (x), half width (y), max thickness of the bag lying on its side
BEANBAG_R, BEANBAG_H = 400.0, 330.0
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


# ================================================================================================= mesh helpers
class Mesh:
    def __init__(self):
        self.V, self.N, self.ST, self.T = [], [], [], []

    def grid(self, P, N, UV):
        rows, cols = P.shape[:2]
        o = len(self.V)
        self.V += list(P.reshape(-1, 3)); self.N += list(N.reshape(-1, 3)); self.ST += list(UV.reshape(-1, 2))
        for i in range(rows - 1):
            for j in range(cols - 1):
                a, b, c, d = o + i * cols + j, o + i * cols + j + 1, o + (i + 1) * cols + j, o + (i + 1) * cols + j + 1
                self.tri(a, b, c); self.tri(b, d, c)

    def tri(self, a, b, c):
        V = self.V
        fn = np.cross(np.asarray(V[c]) - V[a], np.asarray(V[b]) - V[a])
        want = np.asarray(self.N[a]) + self.N[b] + self.N[c]
        self.T.append((a, b, c) if fn @ want >= 0 else (a, c, b))

    def poly(self, pts, n, uvs):
        o = len(self.V)
        for p, uv in zip(pts, uvs):
            self.V.append(np.asarray(p, float)); self.N.append(np.asarray(n, float)); self.ST.append(uv)
        for k in range(1, len(pts) - 1): self.tri(o, o + k, o + k + 1)

    def add(self, other, R=np.eye(3), t=(0, 0, 0), sc=1.0):
        o = len(self.V)
        for v, n, st in zip(other.V, other.N, other.ST):
            self.V.append(R @ (np.asarray(v) * sc) + np.asarray(t, float)); self.N.append(R @ np.asarray(n)); self.ST.append(st)
        self.T += [(a + o, b + o, c + o) for (a, b, c) in other.T]

    def offset(self, d):
        for i in range(len(self.V)): self.V[i] = np.asarray(self.V[i]) - np.asarray(d, float)
        return self

    def surface(self, name, shader):
        return dict(name=name, shader=shader, verts=np.array(self.V), normals=np.array(self.N), st=np.array(self.ST),
                    tris=np.array(self.T, np.int64))


def revolve(M, prof, u_tiles=1.0, v_of=None, n=48, a0=0.0, a1=360.0, inward=False, cx=0.0, cy=0.0):
    """surface of revolution of prof [(r, z)...] round the z axis; v = arc length / 256 unless v_of given"""
    prof = np.asarray(prof, float)
    tg = np.gradient(prof, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    angs = np.radians(np.linspace(a0, a1, n + 1))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
    P = np.zeros((len(prof), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        P[:, j] = np.stack([cx + prof[:, 0] * c, cy + prof[:, 0] * s, prof[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = (a - angs[0]) / (2 * math.pi) * u_tiles
        UV[:, j, 1] = [v_of(r, z) for (r, z) in prof] if v_of else L / 256
    M.grid(P, N, UV)


def disc(M, r, z, up=True, n=48, cx=0.0, cy=0.0, uvscale=None):
    pts = [(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    if not up: pts = pts[::-1]
    us = uvscale or 2 * r
    M.poly(pts, (0, 0, 1 if up else -1), [(0.5 + (x - cx) / us, 0.5 - (y - cy) / us) for (x, y, z) in pts])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rot_axis(axis, a):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def frame(d):
    """two unit vectors perpendicular to d"""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    b1 = np.cross(d, a); b1 /= np.linalg.norm(b1)
    return b1, np.cross(d, b1)


def tube(M, path, radii, nseg=16, caps=(True, True), utiles=1.0, vlen=256.0):
    """tube along a polyline path [(x,y,z)...] with radius per point; parallel-transported frames"""
    path = np.asarray(path, float); radii = np.asarray(radii, float)
    n = len(path)
    T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    b1, _ = frame(T[0]); B1 = [b1]
    for i in range(1, n):
        b = B1[-1] - T[i] * (B1[-1] @ T[i]); b /= np.linalg.norm(b); B1.append(b)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    P = np.zeros((n, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((n, nseg + 1, 2))
    for i in range(n):
        b2 = np.cross(T[i], B1[i])
        for j in range(nseg + 1):
            a = 2 * math.pi * j / nseg
            nn = B1[i] * math.cos(a) + b2 * math.sin(a)
            P[i, j] = path[i] + nn * radii[i]; N[i, j] = nn; UV[i, j] = (j / nseg * utiles, L[i] / vlen)
    M.grid(P, N, UV)
    for k, (i, sgn) in enumerate(((0, -1), (n - 1, 1))):
        if not caps[k] or radii[i] < 0.5: continue
        b2 = np.cross(T[i], B1[i])
        pts = [path[i] + (B1[i] * math.cos(a) + b2 * math.sin(a)) * radii[i] for a in np.linspace(0, 2 * math.pi, nseg, endpoint=False)]
        M.poly(pts, T[i] * sgn, [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, nseg, endpoint=False)])


def ellipsoid(M, c, a, b, h, nu=16, nv=10, u0=0.0, u1=1.0, R=np.eye(3), bump=None):
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        p = math.pi * i / nv - math.pi / 2
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            k = 1.0 if bump is None else bump(p, t)
            v = np.array([a * math.cos(p) * math.cos(t), b * math.cos(p) * math.sin(t), h * math.sin(p)]) * k
            n = np.array([math.cos(p) * math.cos(t) / a, math.cos(p) * math.sin(t) / b, math.sin(p) / h])
            P[i, j] = R @ v + c; N[i, j] = R @ (n / np.linalg.norm(n)); UV[i, j] = (u0 + (u1 - u0) * j / nu, i / nv)
    M.grid(P, N, UV)


# ================================================================================================= bong
def bong():
    glass, water, bubbles, smoke, decal, herb, ember, steel = (Mesh() for _ in range(8))
    # outer glass: foot ring, conical beaker, neck, tube, ice pinch bulges, flared mouthpiece with a rolled lip
    prof = [(0.01, 0), (150, 0), (164, 4), (170, 14), (169, 30), (160, 80), (140, 140), (116, 200), (92, 256), (78, 298),
            (73, 320), (BONG_TUBE_R, 340), (BONG_TUBE_R, 420), (BONG_TUBE_R - 8, 432), (BONG_TUBE_R, 444), (BONG_TUBE_R, 640),
            (76, 668), (84, 700), (88, 714), (85, 720), (78, 716)]
    revolve(glass, prof, 1.0, v_of=lambda r, z: 1 - z / BONG_H, n=56)
    # inner wall of the mouthpiece (you see it looking down the tube)
    revolve(glass, [(78, 716), (70, 690), (64, 640), (64, 360)], 1.0, v_of=lambda r, z: 1 - z / BONG_H, n=40, inward=True)
    # base glass slab (thick bottom) seen through the water
    disc(glass, 150, 14, up=True, n=48)
    # water: cone up to z 170 just inside the glass, flat surface on top
    wz = 170.0
    revolve(water, [(0.01, 16), (148, 16), (158, 30), (150, 80), (wz - 41, 140), (124, wz)], 1.0, v_of=lambda r, z: z / 256, n=48)
    disc(water, 124, wz, n=48, uvscale=200)
    # rising bubbles: a column above the downstem slit + a ring (percolator)
    revolve(bubbles, [(36, 30), (36, wz - 4)], 2.0, v_of=lambda r, z: z / 140, n=16)
    revolve(bubbles, [(96, 40), (90, wz - 4)], 5.0, v_of=lambda r, z: z / 140 + 0.3, n=32)
    # milky smoke inside the beaker headspace and the tube (swirls upward)
    revolve(smoke, [(118, wz + 2), (100, 230), (80, 290), (66, 340), (64, 480), (60, 620)], 2.0, v_of=lambda r, z: z / 300, n=32)
    # PADMAN decal on the tube (front, +x side): a band of the tube 120 deg wide, standing just outside the glass
    revolve(decal, [(BONG_TUBE_R + 0.6, 600), (BONG_TUBE_R + 0.6, 470)], 1.0, v_of=lambda r, z: (600 - z) / 130, n=16, a0=-60, a1=60)
    # downstem: from inside the water (r 30, z 60) out through the beaker wall on the -x side up to the bowl
    ang = math.radians(42)
    d = np.array([-math.cos(ang), 0, math.sin(ang)])
    p0 = np.array([-20.0, 0, 52]); p1 = p0 + d * 270
    tube(steel, [p0, p0 + d * 60, p1 - d * 10, p1], [15, 15, 15, 17], 14, caps=(True, False))
    # joint ring where the stem enters the glass (rubber grommet look)
    gp = p0 + d * 170
    tube(steel, [gp - d * 8, gp + d * 8], [22, 22], 16)
    # bowl: glass cup on the stem end, herb dome, ember
    b1, b2 = frame(d)
    bowl_c = p1 + np.array([0, 0, 6.0])
    cup = Mesh()
    revolve(cup, [(17, 0), (24, 8), (40, 34), (46, 52), (44, 56), (38, 52)], 1.0, n=24)
    revolve(cup, [(38, 52), (30, 30), (14, 14)], 1.0, n=24, inward=True)
    glass.add(cup, np.eye(3), bowl_c)
    hm = Mesh()
    def hb(p, t): return 1.0 + 0.10 * math.sin(5 * t + 1.3) * math.cos(3 * p) + 0.06 * math.sin(9 * t)
    ellipsoid(hm, np.zeros(3), 37, 37, 16, 18, 8, bump=hb)
    herb.add(hm, np.eye(3), bowl_c + np.array([0, 0, 50.0]))
    ellipsoid(ember, bowl_c + np.array([4, 2, 62.0]), 20, 17, 6, 12, 6)
    # carb hole highlight + ice pinch spikes (three little inward glass bumps visible as rings)
    return glass, water, bubbles, smoke, decal, herb, ember, steel


# ================================================================================================= hookah
HOOKAH_H, HOOKAH_OFS, HOOKAH_BASE_R = 640.0, 320.0, 120.0


def hookah():
    """floor hookah: bulbous glass base with water, brass stem with bulges and an ash tray, clay bowl with foil and
    glowing coals, a hose curling down to the floor (origin bottom centre before HOOKAH_OFS)"""
    glass, water, brass, clay, foil, coal, hose, tip = (Mesh() for _ in range(8))
    revolve(glass, [(0.01, 0), (70, 0), (96, 10), (HOOKAH_BASE_R, 60), (118, 120), (100, 170), (70, 200), (44, 222), (36, 236), (38, 248)],
            1.0, v_of=lambda r, z: 1 - z / 250, n=48)
    revolve(water, [(0.01, 6), (72, 6), (98, 16), (116, 60), (112, 110)], 1.0, v_of=lambda r, z: z / 256, n=40)
    disc(water, 112, 110, n=40, uvscale=220)
    # brass stem: grommet, bulges, ash tray, bowl seat
    prof = [(40, 246), (34, 262), (30, 300), (44, 320), (30, 340), (24, 400), (110, 420), (112, 430), (24, 436), (24, 470),
            (36, 486), (24, 502), (22, 560), (30, 572), (30, 584)]
    revolve(brass, prof, 2.0, v_of=lambda r, z: z / 200, n=32)
    revolve(brass, [(110, 430), (100, 426), (24, 426)], 1.0, n=32)            # tray top
    # clay bowl, foil, coals
    revolve(clay, [(30, 584), (40, 592), (58, 614), (62, 626), (58, 630), (46, 628)], 1.0, n=28)
    revolve(foil, [(58, 628), (60, 630), (0.01, 632)], 1.0, n=28)
    for k, (dx, dy) in enumerate(((-20, -10), (18, -14), (0, 20))):
        ellipsoid(coal, np.array([dx, dy, 640.0]), 16, 16, 8, 10, 6)
    # hose: from the stem port (r 34, z 300) out and down in a lazy curve to the floor, mouthpiece lying there
    pts = []
    for t in np.linspace(0, 1, 26):
        a = t * 2.4
        r_ = 40 + 280 * t
        x = r_ * math.cos(a * 0.6); y = r_ * math.sin(a * 0.6) + 60 * math.sin(t * math.pi)
        z = 300 - 290 * t ** 0.7 + 60 * math.sin(t * math.pi)
        pts.append((x, y, max(z, 14.0)))
    tube(hose, pts, [12] * len(pts), 10, caps=(True, False))
    end = np.array(pts[-1]); d = end - np.array(pts[-2]); d[2] = 0; d /= np.linalg.norm(d)
    tube(tip, [end, end + d * 50, end + d * 90], [13, 10, 8], 10, caps=(False, True))
    return glass, water, brass, clay, foil, coal, hose, tip


# ================================================================================================= lava lamp
def lava_lamp():
    base, bottle, liquid, pool = Mesh(), Mesh(), Mesh(), Mesh()
    blobs = [Mesh() for _ in range(4)]
    # brushed steel base: wide cone to the bottle seat, then the cap
    revolve(base, [(0.01, 0), (LAVA_R - 4, 0), (LAVA_R, 4), (LAVA_R - 2, 10), (50, 70), (42, 112), (44, 116)], 1.0, n=40)
    revolve(base, [(26, 300), (22, 330), (16, 340), (0.01, LAVA_H)], 1.0, n=32)
    # glass bottle: bulges to r 50 then tapers to the cap
    bprof = [(44, 116), (48, 140), (50, 170), (48, 210), (40, 250), (32, 285), (26, 300)]
    revolve(bottle, bprof, 1.0, v_of=lambda r, z: 1 - (z - 116) / 184, n=40)
    revolve(liquid, [(r - 2.5, z) for (r, z) in bprof[:-1]] + [(25, 292), (0.01, 292)], 1.0, v_of=lambda r, z: 1 - (z - 116) / 184, n=32)
    # wax pool at the bottom (always there)
    def pb(p, t): return 1.0 + 0.08 * math.sin(4 * t)
    ellipsoid(pool, np.array([0, 0, 124.0]), 40, 40, 14, 20, 8, bump=pb)
    # blobs: each one gets its own deformVertexes move in the shader; place them low, they rise up to ~110
    for k, (r, h, x, y, z) in enumerate(((17, 22, 6, -4, 160), (13, 16, -8, 6, 150), (11, 14, 4, 8, 175), (15, 20, -3, -6, 140))):
        def bb(p, t, k=k): return 1.0 + 0.12 * math.sin(3 * t + k) * math.cos(p)
        ellipsoid(blobs[k], np.array([x, y, float(z)]), r, r, h, 14, 8, bump=bb)
    return base, bottle, liquid, pool, blobs


# ================================================================================================= cannabis plant
def plant(height, seed, n_leaves=70):
    """pot + stalk + branches + fan leaves (quads with an alpha-cut leaf texture) + colas; origin at the pot base"""
    rr = np.random.default_rng(seed)
    pot, soil, stem, leaves, buds = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    pr = 0.16 * height                     # pot radius at the rim
    ph = 0.25 * height
    revolve(pot, [(0.01, 0), (pr * 0.72, 0), (pr * 0.78, 6), (pr * 0.95, ph - 26), (pr, ph - 24), (pr + 6, ph - 20), (pr + 6, ph),
                  (pr - 4, ph), (pr - 8, ph - 18)], 2.0, v_of=lambda r, z: 1 - z / ph, n=40)
    sz = ph - 22
    def sb(p, t): return 1.0
    revolve(soil, [(pr - 8, sz), (pr * 0.5, sz + 4), (0.01, sz + 8)], 3.0, v_of=lambda r, z: r / 128, n=32)
    # main stalk
    top = height
    S = [np.array([0, 0, sz + 6.0])]
    for k in range(1, 9):
        z = sz + (top - sz - 30) * k / 8
        S.append(np.array([8 * math.sin(k * 1.7 + seed), 8 * math.cos(k * 1.3 + seed), z]))
    rad = np.linspace(0.022 * height, 0.008 * height, len(S))
    tube(stem, S, rad, 10, caps=(False, True))
    # branches: alternating nodes up the stalk, longer near the bottom (christmas-tree shape)
    tips = []
    nodes = 9
    for k in range(nodes):
        f = (k + 1) / (nodes + 1)
        z = sz + 40 + (top - sz - 140) * f
        L = (0.34 - 0.24 * f) * height
        a = k * 2.4 + rr.uniform(-0.3, 0.3) + seed
        dirn = np.array([math.cos(a), math.sin(a), 0.0])
        base_pt = np.array([0, 0, z])
        mid = base_pt + dirn * L * 0.55 + np.array([0, 0, L * 0.28])
        tip = base_pt + dirn * L + np.array([0, 0, L * 0.62])
        tube(stem, [base_pt, mid, tip], [rad.max() * 0.45, rad.max() * 0.32, rad.max() * 0.2], 8, caps=(False, True))
        tips.append((tip, dirn, L))
        # a smaller opposite branch
        a2 = a + math.pi + rr.uniform(-0.4, 0.4)
        d2 = np.array([math.cos(a2), math.sin(a2), 0.0]); L2 = L * 0.8
        tip2 = base_pt + np.array([0, 0, 20]) + d2 * L2 + np.array([0, 0, L2 * 0.6])
        tube(stem, [base_pt + np.array([0, 0, 20]), base_pt + np.array([0, 0, 20]) + d2 * L2 * 0.5 + np.array([0, 0, L2 * 0.25]), tip2],
             [rad.max() * 0.4, rad.max() * 0.28, rad.max() * 0.18], 8, caps=(False, True))
        tips.append((tip2, d2, L2))
    tips.append((S[-1], np.array([1.0, 0, 0]), 0.2 * height))
    # colas at the branch tips + the main top cola
    def bud(c, h, r, up=np.array([0, 0, 1.0])):
        R = rot_axis(np.cross([0, 0, 1.0], up) + np.array([1e-6, 0, 0]), math.acos(np.clip(up[2] / np.linalg.norm(up), -1, 1)))
        def bb(p, t): return 1.0 + 0.13 * math.sin(7 * t + 2 * p) * math.cos(p) + 0.08 * math.sin(13 * t)
        ellipsoid(buds, c, r, r, h, 16, 10, R=R, bump=bb)
    for (tip, d, L) in tips[:-1]:
        bud(tip + np.array([0, 0, 0.03 * height]), 0.06 * height, 0.024 * height, d * 0.3 + np.array([0, 0, 1.0]))
    bud(S[-1] + np.array([0, 0, 0.07 * height]), 0.11 * height, 0.034 * height)
    # fan leaves: quads (petiole at the bottom-centre of the texture) hanging off the branches and the stalk
    lw = 0.2 * height
    count = 0
    while count < n_leaves:
        if rr.uniform() < 0.25:                             # on the stalk
            z = rr.uniform(sz + 60, top - 60)
            p0 = np.array([0, 0, z]); a = rr.uniform(0, 2 * math.pi); out = np.array([math.cos(a), math.sin(a), 0])
        else:                                               # along a branch
            tip, d, L = tips[rr.integers(0, len(tips) - 1)]
            t = rr.uniform(0.35, 1.0)
            p0 = tip - (d * L + np.array([0, 0, L * 0.6])) * (1 - t)
            a = math.atan2(d[1], d[0]) + rr.uniform(-1.4, 1.4); out = np.array([math.cos(a), math.sin(a), 0])
        sz_ = lw * rr.uniform(0.55, 1.0) * (1.15 - 0.5 * (p0[2] - sz) / (top - sz))
        droop = rr.uniform(0.15, 0.55)                     # leaf plane tilted: mostly horizontal, drooping outward
        fwd = out * math.cos(droop) - np.array([0, 0, 1.0]) * math.sin(droop)
        side = np.cross(np.array([0, 0, 1.0]), out); side /= np.linalg.norm(side)
        roll = rr.uniform(-0.3, 0.3)
        side = side * math.cos(roll) + np.cross(fwd, side) * math.sin(roll)
        nrm = np.cross(side, fwd); nrm /= np.linalg.norm(nrm)
        if nrm[2] < 0: nrm = -nrm
        p0 = p0 + out * 6
        pts = [p0 - side * sz_ / 2, p0 + side * sz_ / 2, p0 + side * sz_ / 2 + fwd * sz_, p0 - side * sz_ / 2 + fwd * sz_]
        leaves.poly(pts, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])
        count += 1
    return pot, soil, stem, leaves, buds


# ================================================================================================= ashtray + joint
def ashtray():
    tray, ash, paper, ember, roach = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    R = ASH_R
    # thick ceramic ring with three rest notches (dips in the rim)
    nseg = 72
    def rim_z(a):
        d = min(abs(((a - k * 2 * math.pi / 3 + math.pi) % (2 * math.pi)) - math.pi) for k in range(3))
        return 40 - 16 * max(0.0, 1 - d / 0.16)
    angs = np.linspace(0, 2 * math.pi, nseg + 1)
    prof_r = [R, R + 2, R - 4, R - 22, R - 30, R - 34]
    rows = []
    for (rad, kind) in zip(prof_r, ('foot', 'side', 'top_out', 'top_in', 'inner', 'floor')):
        rows.append(rad)
    P = np.zeros((7, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((7, nseg + 1, 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a); zt = rim_z(a)
        prof = [(R - 6, 0, (0, -1)), (R, 6, (1, -0.2)), (R + 2, zt - 8, (1, 0.2)), (R - 6, zt, (0.3, 1)), (R - 24, zt, (-0.3, 1)),
                (R - 32, zt - 10, (-1, 0.1)), (R - 36, 14, (-0.5, 0.8))]
        for i, (rad, z, (nr, nz)) in enumerate(prof):
            P[i, j] = (rad * c, rad * s, z); nn = np.array([nr * c, nr * s, nz]); N[i, j] = nn / np.linalg.norm(nn)
            UV[i, j] = (a / (2 * math.pi) * 4, i / 6)
    tray.grid(P, N, UV)
    disc(tray, R - 36, 14, n=48)
    disc(tray, R - 6, 0, up=False, n=48)
    # ash heap
    def ab(p, t): return 1.0 + 0.2 * math.sin(5 * t) * math.cos(p)
    ellipsoid(ash, np.array([-18, 10, 14.0]), 44, 36, 9, 16, 6, bump=ab)
    # joint resting in the notch at angle 0 (+x), its lit end over the tray
    a = 0.0
    rest = np.array([R - 8, 0, rim_z(0) + 6])
    d = np.array([-1.0, 0.18, -0.05]); d /= np.linalg.norm(d)
    out = rest - d * 120                                     # mouth end outside the tray
    tip = rest + d * 70
    pts = [out + (tip - out) * t for t in np.linspace(0, 1, 9)]
    rads = [6.5 + 3.5 * t for t in np.linspace(0, 1, 9)]
    tube(paper, pts, rads, 14, caps=(True, False))
    tube(ember, [tip - d * 1, tip + d * 9], [10, 7], 14, caps=(False, True))
    # crutch (filter) end looks like rolled card: a short darker tube inside the mouth end
    tube(roach, [out - d * 0.5, out + d * 18], [6.8, 6.8], 12, caps=(True, False))
    # two roaches in the tray
    for (x, y, ang, L) in ((30, -40, 0.7, 34), (-50, -20, 2.4, 28)):
        dd = np.array([math.cos(ang), math.sin(ang), 0])
        c = np.array([x, y, 21.0])
        tube(roach, [c - dd * L / 2, c + dd * L / 2], [6, 6.5], 10)
    return tray, ash, paper, ember, roach


# ================================================================================================= grinder
def grinder():
    body, knurl, lid, teeth = Mesh(), Mesh(), Mesh(), Mesh()
    r = GRINDER_R
    # three stacked sections, small grooves between them; knurled bands on each
    zs = [(0, 26), (28, 50), (52, 74)]
    for (za, zb) in zs:
        revolve(body, [(r - 4, za), (r, za + 2), (r, za + 4)], 1.0, n=40)
        revolve(knurl, [(r + 0.2, za + 4), (r + 0.2, zb - 4)], 6.0, v_of=lambda rad, z: z / 40, n=48)
        revolve(body, [(r, zb - 4), (r, zb - 2), (r - 4, zb)], 1.0, n=40)
    disc(body, r - 4, 74, n=40)
    disc(body, r - 4, 0, up=False, n=40)
    # lid lying beside it, upside down so the teeth show (+x side)
    cx = r * 2 + 18
    revolve(lid, [(0.01, 0), (r - 4, 0), (r, 3), (r, 28), (r - 3, 30), (r - 10, 30), (r - 10, 8), (0.01, 8)], 1.0, n=40, cx=cx)
    for k in range(14):
        a = 2 * math.pi * k / 14
        for rad in (18, 34):
            x, y = cx + rad * math.cos(a + rad / 40), rad * math.sin(a + rad / 40)
            revolve(teeth, [(5, 8), (4, 18), (0.01, 22)], 1.0, n=6, cx=x, cy=y)
    return body, knurl, lid, teeth


# ================================================================================================= stash jar
def jar():
    glass, lid, buds = Mesh(), Mesh(), Mesh()
    R, H = JAR_R, JAR_H
    revolve(glass, [(0.01, 2), (R - 6, 0), (R, 8), (R, H - 40), (R - 8, H - 26), (R - 10, H - 18)], 1.0,
            v_of=lambda r, z: 1 - z / H, n=40)
    revolve(lid, [(R - 10, H - 20), (R - 6, H - 20), (R - 4, H - 16), (R - 4, H - 2), (R - 8, H), (0.01, H)], 3.0, n=40)
    rr = np.random.default_rng(77)
    for k in range(9):
        a = rr.uniform(0, 2 * math.pi); d = rr.uniform(0, R - 30)
        z = 34 + rr.uniform(0, 1) * 50 + (k // 3) * 22
        def bb(p, t, k=k): return 1.0 + 0.15 * math.sin(6 * t + k) * math.cos(p) + 0.08 * math.sin(11 * t + 2 * p)
        ellipsoid(buds, np.array([d * math.cos(a), d * math.sin(a), z]), 22, 20, 30, 14, 8,
                  R=rot_axis((math.sin(a), -math.cos(a), 0), rr.uniform(-0.8, 0.8)), bump=bb)
    return glass, lid, buds


# ================================================================================================= chips bag + crisps
def chips_bag():
    """a crisp bag lying flat: x along its length, y across, z up; crimped seams at both x ends"""
    bag, seam = Mesh(), Mesh()
    hx, hy, th = CHIPS
    nu, nv = 40, 28
    for side in (1, -1):                              # top and bottom sheet
        P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
        for i in range(nv + 1):
            v = -1 + 2 * i / nv
            for j in range(nu + 1):
                u = -1 + 2 * j / nu
                puff = (1 - u ** 2) ** 0.35 * (1 - v ** 2) ** 0.55
                wr = 0.06 * math.sin(9 * u + 2 * v) * math.sin(5 * v + 1) + 0.04 * math.sin(17 * u * v)  # crinkles
                z = th / 2 + side * th / 2 * (puff + wr * puff)
                x = u * hx * (1 - 0.06 * (1 - v ** 2) * u ** 2); y = v * hy * (1 - 0.05 * puff)
                P[i, j] = (x, y, max(z, 0.5) if side > 0 else max(z, 0.0))
                UV[i, j] = ((u + 1) / 2, (1 - v) / 2) if side > 0 else ((1 - u) / 2, (1 - v) / 2)
        # normals from the grid
        dU = np.gradient(P, axis=1); dV = np.gradient(P, axis=0)
        Nn = np.cross(dU, dV) * side; Nn /= np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-9)
        bag.grid(P, Nn, UV)
    # crimped seams (flat zig-zag strips) at both ends, standing slightly up
    for sx in (1, -1):
        pts = []
        for k in range(25):
            y = -hy + 2 * hy * k / 24
            pts.append((sx * (hx + 8 + 4 * (k % 2)), y, th / 2))
        for k in range(24):
            a, b = pts[k], pts[k + 1]
            q = [(sx * hx, a[1], th / 2 - 2), (sx * hx, b[1], th / 2 - 2), b, a]
            seam.poly(q if sx > 0 else q[::-1], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
            seam.poly(q[::-1] if sx > 0 else q, (0, 0, -1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return bag, seam


def crisps(seed=9, count=40, rx=260, ry=160):
    rr = np.random.default_rng(seed)
    M = Mesh()
    one = Mesh()
    nu, nv = 9, 4
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        rad = 26 * i / nv
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            x, y = rad * math.cos(t), rad * math.sin(t) * 0.85
            z = 0.012 * (x * x - y * y) + 4                 # saddle (pringle-ish curl)
            P[i, j] = (x, y, z); n = np.array([-0.024 * x, 0.024 * y, 1.0]); N[i, j] = n / np.linalg.norm(n)
            UV[i, j] = (0.5 + x / 60, 0.5 + y / 60)
    one.grid(P, N, UV)
    # underside
    P2 = P.copy(); P2[..., 2] -= 1.5
    one.grid(P2[::-1], -N[::-1], UV[::-1])
    placed = []
    for k in range(count * 4):
        if len(placed) >= count: break
        a = rr.uniform(0, 2 * math.pi); f = math.sqrt(rr.uniform())
        x, y = rx * f * math.cos(a), ry * f * math.sin(a)
        z = 0.0
        for (px, py, pz) in placed:
            if math.hypot(px - x, py - y) < 40: z = max(z, pz + 7)
        if z > 30: continue
        placed.append((x, y, z))
        R = rot_z(rr.uniform(0, 2 * math.pi)) @ rot_axis((1, 0, 0), rr.uniform(-0.25, 0.25) if z else 0)
        M.add(one, R, (x, y, z + 3))
    return M


# ================================================================================================= bean bag
def beanbag():
    M = Mesh()
    nu, nv = 64, 26
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    R, H = BEANBAG_R, BEANBAG_H
    for i in range(nv + 1):
        p = i / nv                                       # 0 = bottom edge, 1 = top centre
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            lump = 1 + 0.05 * math.sin(3 * t + 0.5) + 0.03 * math.sin(7 * t)
            if p < 0.55:                                  # bulging lower body
                q = p / 0.55
                rad = R * lump * (0.9 + 0.1 * math.sin(q * math.pi * 0.9)) * (1 - 0.18 * q ** 3)
                z = H * 0.62 * (1 - math.cos(q * math.pi / 2)) ** 0.8
            else:                                         # rolled top edge into the dent, back side higher
                q = (p - 0.55) / 0.45
                back = 0.5 + 0.5 * math.cos(t - math.pi)  # +x is the back (high side)
                rad = R * lump * 0.8 * (1 - q) ** 0.9
                zr = H * (0.62 + 0.38 * back) * (1 - 0.35 * q ** 1.5) + 20 * math.sin(q * math.pi)
                z = zr - (H * 0.25 * q ** 2 if q > 0.6 else 0)
            P[i, j] = (rad * math.cos(t), rad * math.sin(t), max(z, 0))
            UV[i, j] = (j / nu * 4, p * 3)
    dU = np.gradient(P, axis=1); dV = np.gradient(P, axis=0)
    N = np.cross(dU, dV); N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-9)
    if N[nv // 2, 0, 0] < 0: N = -N
    M.grid(P, N, UV)
    disc(M, R * 0.9, 0.0, up=False, n=48)
    return M


# ================================================================================================= lighter
def lighter():
    body, metal = Mesh(), Mesh()
    pts = [(12 * math.cos(t), 7 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
    nseg = len(pts)
    P = np.zeros((2, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, nseg + 1, 2))
    for j in range(nseg + 1):
        x, y = pts[j % nseg]
        n = np.array([x / 144, y / 49, 0]); n /= np.linalg.norm(n)
        for i, z in enumerate((0, 62)):
            P[i, j] = (x, y, z); N[i, j] = n; UV[i, j] = (j / nseg, 1 - z / 62)
    body.grid(P, N, UV)
    body.poly([(x, y, 0) for (x, y) in pts[::-1]], (0, 0, -1), [(0.5, 0.5)] * nseg)
    # metal hood + wheel
    for (z0, z1) in ((62, 78),):
        P = np.zeros((2, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, nseg + 1, 2))
        for j in range(nseg + 1):
            x, y = pts[j % nseg]
            n = np.array([x / 144, y / 49, 0]); n /= np.linalg.norm(n)
            for i, z in enumerate((z0, z1)):
                P[i, j] = (x * 0.92, y * 0.92, z); N[i, j] = n; UV[i, j] = (j / nseg * 3, i)
        metal.grid(P, N, UV)
        metal.poly([(x * 0.92, y * 0.92, z1) for (x, y) in pts], (0, 0, 1), [(0.5, 0.5)] * nseg)
    tube(metal, [(-4, -6, 72), (-4, 6, 72)], [6, 6], 12)
    return body, metal


# ================================================================================================= textures
def _noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    big = Image.new('L', (n * 3, m * 3))
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    for i in range(3):
        for j in range(3): big.paste(im, (i * n, j * m))
    a = np.asarray(big.filter(ImageFilter.GaussianBlur(blur)).crop((n, m, 2 * n, 2 * m)), np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def _img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
def _fill(n, col, g=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + np.array(col, np.float32) + _noise(n, 1, seed, m)[..., None] * g + _noise(n, 10, seed + 1, m)[..., None] * g


def tex_glass():
    n = 128
    y = np.linspace(0, 1, n)[:, None]
    a = np.zeros((n, n, 3), np.float32) + np.array([206, 236, 230], np.float32)
    a -= (np.sin(np.linspace(0, 6.28, n))[None, :] ** 8 * 26)[..., None]        # a darker streak (glass edge)
    return _img(a)


def tex_env():
    """fake room reflection for tcGen environment: warm lamp streaks, purple/green lava glow, dark room"""
    n = 256
    y = np.linspace(-1, 1, n)[:, None]; x = np.linspace(-1, 1, n)[None, :]
    a = np.zeros((n, n, 3), np.float32) + np.array([24, 20, 30], np.float32)
    a += (np.exp(-((y + 0.5) / 0.08) ** 2) * np.exp(-((x + 0.2) / 0.5) ** 2))[..., None] * np.array([255, 230, 190])
    a += (np.exp(-((y - 0.2) / 0.25) ** 2) * np.exp(-((x - 0.6) / 0.2) ** 2))[..., None] * np.array([170, 60, 220])
    a += (np.exp(-((y - 0.1) / 0.3) ** 2) * np.exp(-((x + 0.7) / 0.2) ** 2))[..., None] * np.array([60, 200, 90])
    a += _noise(n, 6, 11)[..., None] * 6
    return _img(a)


def tex_water():
    n = 128
    a = np.zeros((n, n, 3), np.float32) + np.array([70, 140, 90], np.float32) + _noise(n, 6, 3)[..., None] * 14
    return _img(a)


def tex_bubbles(w=128, h=256, seed=5):
    rr = np.random.default_rng(seed)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(60):
        x, y = rr.integers(0, w), rr.integers(0, h); r = rr.uniform(2, 7)
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), outline=(230, 255, 240, 220), width=2)
                d.ellipse((x + ox - r * 0.4 - 1, y + oy - r * 0.5 - 1, x + ox - r * 0.4 + 1, y + oy - r * 0.5 + 1), fill=(255, 255, 255, 255))
    return im


def tex_smoke(w=256, h=256, seed=7):
    a = _noise(w, 14, seed) * 0.6 + _noise(w, 5, seed + 1) * 0.4
    al = np.clip((a + 0.3) * 120, 0, 200)
    rgb = np.zeros((h, w, 3), np.float32) + 225
    im = _img(rgb).convert('RGBA'); im.putalpha(_img(al).convert('L'))
    return im


def tex_decal():
    w, h = 256, 256
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONTB, 54)
    d.text((w / 2, 62), 'PAD', font=f, fill=(255, 255, 255, 235), anchor='mm', stroke_width=3, stroke_fill=(40, 200, 90, 255))
    d.text((w / 2, 128), 'MAN', font=f, fill=(255, 255, 255, 235), anchor='mm', stroke_width=3, stroke_fill=(40, 200, 90, 255))
    # leaf emblem below
    leaf = fan_leaf(96, (60, 210, 100))
    im.alpha_composite(leaf, (w // 2 - 48, 150))
    return im


def fan_leaf(n=256, col=(58, 140, 52), vein=(150, 210, 110), seed=13):
    """seven-fingered fan leaf, petiole at the bottom centre, serrated leaflets, RGBA"""
    rr = np.random.default_rng(seed)
    S = n * 2
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = S / 2, S * 0.92
    spec = [(-80, 0.32), (-55, 0.55), (-28, 0.8), (0, 0.98), (28, 0.8), (55, 0.55), (80, 0.32)]
    for (ang, L) in spec:
        a = math.radians(ang - 90)
        dx, dy = math.cos(a), math.sin(a); px, py = -dy, dx
        Lp = L * S * 0.86
        W = Lp * 0.115
        pts_l, pts_r = [], []
        m = 28
        for k in range(m + 1):
            t = k / m
            wid = W * (math.sin(math.pi * min(1.0, t * 1.05)) ** 0.9) * (1 - 0.15 * t)
            ser = 1 + (0.22 if k % 2 else -0.05) * (0.2 < t < 0.97)
            x, y = cx + dx * Lp * t, cy + dy * Lp * t
            pts_l.append((x + px * wid * ser, y + py * wid * ser)); pts_r.append((x - px * wid * ser, y - py * wid * ser))
        d.polygon(pts_l + pts_r[::-1], fill=tuple(int(c * rr.uniform(0.92, 1.05)) for c in col) + (255,))
        d.line((cx, cy, cx + dx * Lp * 0.96, cy + dy * Lp * 0.96), fill=vein + (255,), width=max(2, S // 160))
    # petiole
    d.line((cx, cy, cx, S - 2), fill=vein + (255,), width=max(3, S // 80))
    im = im.resize((n, n), Image.LANCZOS)
    # shading noise
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= (1 + 0.08 * _noise(n, 3, seed + 1))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def tex_bud(n=256, seed=21):
    rr = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32) + np.array([96, 150, 70], np.float32)
    a += _noise(n, 3, seed)[..., None] * 22 + _noise(n, 0.8, seed + 1)[..., None] * 10
    im = _img(a); d = ImageDraw.Draw(im)
    for _ in range(140):                            # orange pistils (hairs)
        x, y = rr.integers(0, n, 2); L = rr.uniform(6, 16); t = rr.uniform(0, 2 * math.pi)
        d.line((x, y, x + L * math.cos(t), y + L * math.sin(t)), fill=(214, 120, 40), width=2)
    for _ in range(900):                            # frosty trichomes
        x, y = rr.integers(0, n, 2)
        d.point((x, y), fill=(236, 244, 230))
    for _ in range(60):                             # purple hints
        x, y = rr.integers(0, n, 2); r = rr.uniform(2, 5)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(110, 80, 120))
    return im.filter(ImageFilter.GaussianBlur(0.5))


def tex_terracotta():
    n = 256
    a = _fill(n, (176, 92, 56), 6, 31)
    v = np.linspace(0, 1, n)[:, None]
    a *= (1 - 0.12 * (v < 0.09))[..., None]
    return _img(a)


def tex_soil():
    n = 128
    a = _fill(n, (60, 42, 30), 10, 33)
    im = _img(a); d = ImageDraw.Draw(im); rr = np.random.default_rng(34)
    for _ in range(80):
        x, y = rr.integers(0, n, 2); d.point((x, y), fill=(230, 230, 220))   # perlite
    return im


def tex_stem():
    n = 64
    a = _fill(n, (98, 140, 62), 6, 35)
    a[:, ::8] *= 0.85
    return _img(a)


def tex_ceramic():
    n = 256
    a = _fill(n, (36, 46, 60), 4, 41)
    v = np.linspace(0, 1, n)[:, None]
    a += (np.sin(v * 40) * 6)[..., None]
    return _img(a)


def tex_ash():
    n = 64
    return _img(_fill(n, (120, 118, 112), 14, 43))


def tex_paper():
    w, h = 128, 64
    a = np.zeros((h, w, 3), np.float32) + np.array([236, 230, 214], np.float32) + _noise(w, 1, 45, h)[..., None] * 5
    # a slight spiral seam
    for k in range(0, w, 16): a[:, k:k + 2] *= 0.9
    return _img(a)


def tex_ember():
    n = 64
    yy, xx = np.mgrid[0:n, 0:n] / n
    a = np.zeros((n, n, 3), np.float32) + np.array([255, 120, 30], np.float32)
    a += _noise(n, 2, 47)[..., None] * np.array([40, 50, 20])
    a *= (0.7 + 0.3 * np.clip(_noise(n, 1, 48), -1, 1))[..., None]
    return _img(a)


def tex_card():
    n = 64
    return _img(_fill(n, (200, 170, 120), 6, 49))


def tex_anodised(col, seed):
    n = 128
    a = _fill(n, col, 3, seed)
    a += (np.repeat(_noise(n, 1, seed + 2)[:1], n, 0) * 8)[..., None]
    return _img(a)


def tex_knurl(col):
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    k = (np.sin((xx + yy) * math.pi / 4) * np.sin((xx - yy) * math.pi / 4))
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32) * (0.75 + 0.35 * k)[..., None]
    return _img(a)


def tex_steel():
    n = 128
    a = np.zeros((n, n, 3), np.float32) + 170 + _noise(n, 0.5, 51)[..., None] * 6
    a += (np.repeat(_noise(n, 1, 52)[:1], n, 0) * 8)[..., None]
    return _img(a)


def tex_lava_liquid(col):
    n = 128
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32) + _noise(n, 8, 53)[..., None] * 18
    return _img(a)


def tex_wax(col):
    n = 64
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32) + _noise(n, 4, 55)[..., None] * 14
    return _img(a)


def tex_chips_bag():
    w, h = 1024, 512
    a = np.zeros((h, w, 3), np.float32) + np.array([236, 60, 40], np.float32) + _noise(w, 2, 61, h)[..., None] * 4
    im = _img(a); d = ImageDraw.Draw(im)
    # yellow burst
    for k in range(18):
        t = 2 * math.pi * k / 18
        d.polygon([(330, 256), (330 + 240 * math.cos(t), 256 + 210 * math.sin(t)), (330 + 240 * math.cos(t + 0.17), 256 + 210 * math.sin(t + 0.17))],
                  fill=(255, 210, 40))
    d.ellipse((150, 96, 510, 416), fill=(255, 226, 70))
    f = ImageFont.truetype(FONTB, 84); f2 = ImageFont.truetype(FONTB, 40)
    d.text((700, 200), 'MUNCHIES', font=f, fill=(255, 255, 255), anchor='mm', stroke_width=8, stroke_fill=(120, 20, 20))
    d.text((700, 300), 'EXTRA CHEESY CRISPS', font=f2, fill=(255, 230, 90), anchor='mm', stroke_width=3, stroke_fill=(120, 20, 20))
    d.text((700, 370), 'PARTY SIZE', font=f2, fill=(255, 255, 255), anchor='mm')
    # crisps drawn in the burst
    for (x, y, r) in ((300, 230, 70), (380, 290, 64), (260, 320, 56)):
        d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(240, 180, 70), outline=(200, 130, 40), width=4)
    # foil crinkle shading
    a = np.asarray(im).astype(np.float32)
    a *= (1 + 0.06 * _noise(w, 6, 62, h))[..., None]
    return _img(a)


def tex_foil():
    n = 64
    a = np.zeros((n, n, 3), np.float32) + np.array([210, 200, 196], np.float32) + _noise(n, 1, 63)[..., None] * 18
    return _img(a)


def tex_crisp():
    n = 64
    a = np.zeros((n, n, 3), np.float32) + np.array([236, 186, 84], np.float32) + _noise(n, 2, 65)[..., None] * 16
    im = _img(a); d = ImageDraw.Draw(im); rr = np.random.default_rng(66)
    for _ in range(30):
        x, y = rr.integers(0, n, 2); d.point((x, y), fill=(250, 140, 40))
    return im


def tex_fabric(col, seed):
    n = 256
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32)
    yy, xx = np.mgrid[0:n, 0:n]
    a *= (0.92 + 0.08 * np.sin(xx * math.pi / 2) * np.sin(yy * math.pi / 2))[..., None]
    a += _noise(n, 1, seed)[..., None] * 6 + _noise(n, 14, seed + 1)[..., None] * 10
    # seams
    a[:, ::64] *= 0.8
    return _img(a)


def tex_brass():
    n = 128
    a = _fill(n, (196, 150, 64), 4, 93)
    a += (np.repeat(_noise(n, 1, 94)[:1], n, 0) * 10)[..., None]
    return _img(a)


def tex_hose():
    n = 64
    a = _fill(n, (60, 30, 70), 4, 95)
    a[::8] *= 0.6
    return _img(a)


def tex_lighter():
    w, h = 128, 64
    a = np.zeros((h, w, 3), np.float32) + np.array([60, 200, 90], np.float32) + _noise(w, 3, 71, h)[..., None] * 5
    return _img(a)


# ================================================================================================= shaders + make
def _vs(nm, tex=None, env=0.0, extra=''):
    """vertex-lit model shader (misc_model default), optional fake reflection"""
    t = tex or f'{MD}/{nm}'
    s = f'{MD}/{nm}\n{{\n\tqer_editorimage {t}\n{extra}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n'
    if env:
        s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {env} {env} {env} )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def _glow(nm, extra='', blend='', tcmod=''):
    return (f'{MD}/{nm}\n{{\n\tqer_editorimage {MD}/{nm}\n\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {MD}/{nm}\n'
            f'{blend}\t\trgbGen identity\n{tcmod}\t}}\n}}\n\n')


def shaders():
    S = '// ---- custom models (lounge_models.py)\n'
    # glass: tinted filter + additive reflection, both sides
    for nm, tint in (('glass', 'glass'), ('jar_glass', 'glass')):
        S += (f'{MD}/{nm}\n{{\n\tqer_editorimage {MD}/glass\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tcull none\n'
              '\tq3map_shadeAngle 80\n\tsort 7\n'
              f'\t{{\n\t\tmap {MD}/glass\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
              f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.55 0.6 0.6 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    S += (f'{MD}/bong_water\n{{\n\tqer_editorimage {MD}/bong_water\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tcull none\n\tsort 6\n'
          f'\t{{\n\t\tmap {MD}/bong_water\n\t\tblendFunc GL_DST_COLOR GL_SRC_COLOR\n\t\trgbGen identity\n\t\ttcMod turb 0 0.06 0 0.3\n\t}}\n'
          f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.2 0.14 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    S += (f'{MD}/bubbles\n{{\n\tqer_editorimage {MD}/bubbles\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tcull none\n\tsort 8\n'
          f'\t{{\n\t\tmap {MD}/bubbles.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE\n\t\trgbGen identity\n\t\ttcMod scroll 0.02 1.1\n\t}}\n}}\n\n')
    S += (f'{MD}/bong_smoke\n{{\n\tqer_editorimage {MD}/smoke\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tcull none\n\tsort 8\n'
          f'\t{{\n\t\tmap {MD}/smoke.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen const ( 0.85 0.85 0.82 )\n'
          '\t\talphaGen wave sin 0.55 0.25 0 0.12\n\t\ttcMod scroll 0.05 0.25\n\t\ttcMod turb 0 0.06 0 0.15\n\t}\n}\n\n')
    S += (f'{MD}/decal\n{{\n\tqer_editorimage {MD}/decal\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n\tsort 9\n\tpolygonOffset\n'
          f'\t{{\n\t\tmap {MD}/decal.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen vertex\n\t}}\n}}\n\n')
    S += _vs('herb') + _vs('steel', env=0.45, extra='\tq3map_shadeAngle 70\n')
    S += _glow('ember', extra='\tq3map_surfacelight 90\n\tq3map_lightRGB 1 0.5 0.15\n', tcmod='\t\ttcMod turb 0 0.1 0 0.8\n')
    S += (f'{MD}/ember_pulse\n{{\n\tqer_editorimage {MD}/ember\n\tsurfaceparm nolightmap\n'
          f'\t{{\n\t\tmap {MD}/ember\n\t\trgbGen wave sin 0.8 0.2 0 0.7\n\t\ttcMod turb 0 0.1 0 0.8\n\t}}\n}}\n\n')
    # lava lamps
    for col in ('purple', 'green'):
        S += (f'{MD}/lava_liquid_{col}\n{{\n\tqer_editorimage {MD}/lava_liquid_{col}\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n'
              f'\tcull none\n\tsort 6\n\t{{\n\t\tmap {MD}/lava_liquid_{col}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n'
              '\t\ttcMod turb 0 0.08 0 0.2\n\t\ttcMod scroll 0 0.05\n\t}\n}\n\n')
        S += _glow(f'wax_{col}', extra='\tq3map_surfacelight 60\n')
        for k, (amp, freq, ph) in enumerate(((112, 0.045, 0.0), (96, 0.06, 0.4), (88, 0.05, 0.7), (104, 0.038, 0.25))):
            S += (f'{MD}/wax_{col}_{k}\n{{\n\tqer_editorimage {MD}/wax_{col}\n\tsurfaceparm nolightmap\n'
                  f'\tdeformVertexes move 0 0 {amp // 2} sin 1 1 {ph} {freq}\n'
                  f'\tdeformVertexes wave 30 sin 0 2 {ph} 0.4\n'
                  f'\t{{\n\t\tmap {MD}/wax_{col}\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S += _vs('lava_base', tex=f'{MD}/steel', env=0.5, extra='\tq3map_shadeAngle 70\n')
    # plants
    S += (f'{MD}/leaf\n{{\n\tqer_editorimage {MD}/leaf\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tcull none\n'
          f'\t{{\n\t\tmap {MD}/leaf.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')
    S += _vs('bud', env=0.06) + _vs('terracotta') + _vs('soil') + _vs('stem')
    S += _vs('ceramic', env=0.22, extra='\tq3map_shadeAngle 70\n') + _vs('ash') + _vs('paper') + _vs('card')
    S += _vs('anod_green', env=0.25, extra='\tq3map_shadeAngle 70\n') + _vs('knurl_green', env=0.2)
    S += _vs('chips_bag', env=0.12) + _vs('foil', env=0.3) + _vs('crisp')
    S += _vs('beanbag', extra='\tq3map_shadeAngle 120\n') + _vs('lighter', env=0.15)
    S += _vs('brass', env=0.55, extra='\tq3map_shadeAngle 70\n') + _vs('hose', extra='\tq3map_shadeAngle 80\n')
    return S


def make(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    sv = lambda nm, im: im.save(os.path.join(d, nm + '.jpg'), quality=92)
    sva = lambda nm, im: im.save(os.path.join(d, nm + '.tga'))
    sv('glass', tex_glass()); sv('env', tex_env()); sv('bong_water', tex_water()); sva('bubbles', tex_bubbles())
    sva('smoke', tex_smoke()); sva('decal', tex_decal()); sv('herb', tex_bud(128, 23)); sv('ember', tex_ember())
    sv('steel', tex_steel())
    for col, liq, wax in (('purple', (120, 40, 150), (255, 120, 210)), ('green', (30, 120, 70), (190, 255, 90))):
        sv(f'lava_liquid_{col}', tex_lava_liquid(liq)); sv(f'wax_{col}', tex_wax(wax))
    sva('leaf', fan_leaf()); sv('bud', tex_bud()); sv('terracotta', tex_terracotta()); sv('soil', tex_soil()); sv('stem', tex_stem())
    sv('ceramic', tex_ceramic()); sv('ash', tex_ash()); sv('paper', tex_paper()); sv('card', tex_card())
    sv('anod_green', tex_anodised((40, 150, 80), 81)); sv('knurl_green', tex_knurl((40, 150, 80)))
    sv('chips_bag', tex_chips_bag()); sv('foil', tex_foil()); sv('crisp', tex_crisp())
    sv('beanbag', tex_fabric((112, 50, 150), 91)); sv('lighter', tex_lighter()); sv('brass', tex_brass()); sv('hose', tex_hose())
    # bong (origin at mid-height)
    g, w, b, s, dc, h, e, st = bong()
    for m in (g, w, b, s, dc, h, e, st): m.offset((0, 0, BONG_OFS))
    md3write.save(os.path.join(d, 'bong.md3'), [st.surface('steel', f'{MD}/steel'), h.surface('herb', f'{MD}/herb'),
                                                e.surface('ember', f'{MD}/ember_pulse'), w.surface('water', f'{MD}/bong_water'),
                                                b.surface('bubbles', f'{MD}/bubbles'), s.surface('smoke', f'{MD}/bong_smoke'),
                                                g.surface('glass', f'{MD}/glass'), dc.surface('decal', f'{MD}/decal')], name='bong')
    for col in ('purple', 'green'):
        base, bottle, liquid, pool, blobs = lava_lamp()
        surfs = [base.surface('base', f'{MD}/lava_base'), pool.surface('pool', f'{MD}/wax_{col}')]
        surfs += [bl.surface(f'blob{k}', f'{MD}/wax_{col}_{k}') for k, bl in enumerate(blobs)]
        surfs += [liquid.surface('liquid', f'{MD}/lava_liquid_{col}'), bottle.surface('glass', f'{MD}/glass')]
        md3write.save(os.path.join(d, f'lava_{col}.md3'), surfs, name=f'lava_{col}')
    for nm, H, seed, nl, ofs in (('plant_big', 880.0, 3, 90, PLANT_OFS), ('plant_small', 620.0, 5, 60, PLANT_SMALL_OFS)):
        pot, soil, stem, leaves, buds = plant(H, seed, nl)
        for m in (pot, soil, stem, leaves, buds): m.offset((0, 0, ofs))
        md3write.save(os.path.join(d, nm + '.md3'), [pot.surface('pot', f'{MD}/terracotta'), soil.surface('soil', f'{MD}/soil'),
                                                     stem.surface('stem', f'{MD}/stem'), buds.surface('buds', f'{MD}/bud'),
                                                     leaves.surface('leaves', f'{MD}/leaf')], name=nm)
    tray, ash, paper, ember, roach = ashtray()
    md3write.save(os.path.join(d, 'ashtray.md3'), [tray.surface('tray', f'{MD}/ceramic'), ash.surface('ash', f'{MD}/ash'),
                                                   paper.surface('joint', f'{MD}/paper'), roach.surface('roach', f'{MD}/card'),
                                                   ember.surface('ember', f'{MD}/ember')], name='ashtray')
    gb, gk, gl, gt = grinder()
    md3write.save(os.path.join(d, 'grinder.md3'), [gb.surface('body', f'{MD}/anod_green'), gk.surface('knurl', f'{MD}/knurl_green'),
                                                   gl.surface('lid', f'{MD}/anod_green'), gt.surface('teeth', f'{MD}/steel')], name='grinder')
    jg, jl, jb = jar()
    md3write.save(os.path.join(d, 'jar.md3'), [jb.surface('buds', f'{MD}/bud'), jl.surface('lid', f'{MD}/steel'),
                                               jg.surface('glass', f'{MD}/jar_glass')], name='jar')
    cb, cs = chips_bag()
    md3write.save(os.path.join(d, 'chips.md3'), [cb.surface('bag', f'{MD}/chips_bag'), cs.surface('seam', f'{MD}/foil')], name='chips')
    md3write.save(os.path.join(d, 'crisps.md3'), [crisps().surface('crisps', f'{MD}/crisp')], name='crisps')
    md3write.save(os.path.join(d, 'beanbag.md3'), [beanbag().surface('bag', f'{MD}/beanbag')], name='beanbag')
    hg, hw, hb, hc, hf, hco, hh, ht = hookah()
    for m in (hg, hw, hb, hc, hf, hco, hh, ht): m.offset((0, 0, HOOKAH_OFS))
    md3write.save(os.path.join(d, 'hookah.md3'), [hb.surface('brass', f'{MD}/brass'), hc.surface('bowl', f'{MD}/terracotta'),
                                                  hf.surface('foil', f'{MD}/foil'), hco.surface('coals', f'{MD}/ember_pulse'),
                                                  hh.surface('hose', f'{MD}/hose'), ht.surface('tip', f'{MD}/brass'),
                                                  hw.surface('water', f'{MD}/bong_water'), hg.surface('glass', f'{MD}/glass')], name='hookah')
    lb, lm_ = lighter()
    md3write.save(os.path.join(d, 'lighter.md3'), [lb.surface('body', f'{MD}/lighter'), lm_.surface('metal', f'{MD}/steel')], name='lighter')
    return shaders()


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    make(o)
    import md3tool
    for fn in sorted(os.listdir(os.path.join(o, MD))):
        if fn.endswith('.md3'):
            m = md3tool.load(os.path.join(o, MD, fn))
            V = np.concatenate([s['verts'] for s in m['surfaces']])
            print(fn, sum(len(s['verts']) for s in m['surfaces']), 'verts', V.min(0).round(1), V.max(0).round(1))
