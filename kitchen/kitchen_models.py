"""Custom MD3 map objects for wop_padkitchen (Countertop Clash). All geometry and art is original and generated here.

    make(out) -> writes models/padkitchen/*.md3 + their textures, returns the shader text for them

Models (origin = bottom centre unless noted, sizes in game units):
  donut_pink / donut_choc   fried ring R 96 / tube 46 (outer radius 142, height ~82), drippy icing, sprinkles
  cereal_spill1 / 2         ~60 cereal rings in a heap (three colours), for spilled cereal on the counter
  faucet                    chrome mixer tap: escutcheon, column r 52 to z 576, flat-topped spout arm 112 x 64 running
                            -y to the aerator; origin offset (FAUCET_OFS) so every vertex stays inside +-512
  pot_red / pot_blue        enamel stock pot r 192 with rolled rim, glass-and-steel lid (walkable dome) and handles
  flies                     two house flies on a 260 / 180 radius circle round the origin (func_rotating model2),
                            wings flap with deformVertexes
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import md3write

MD = 'models/padkitchen'
DONUT_R, DONUT_T, DONUT_SQ = 96.0, 46.0, 0.85      # ring radius, tube radius, vertical squash
DONUT_H = 2 * DONUT_T * DONUT_SQ                    # dough height (icing adds ~3)
FAUCET_COL_Y = 310.0                               # column centre in model space (model origin = column base + (0,-310,320))
FAUCET_OFS = (0.0, -310.0, 320.0)
FAUCET_TOP, FAUCET_REACH, FAUCET_HALFW = 640.0, 400.0, 56.0
POT_R, POT_RIM, POT_LID_TOP = 192.0, 322.0, 347.0


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

    def add(self, other, R=np.eye(3), t=(0, 0, 0)):
        o = len(self.V)
        for v, n, st in zip(other.V, other.N, other.ST):
            self.V.append(R @ np.asarray(v) + np.asarray(t, float)); self.N.append(R @ np.asarray(n)); self.ST.append(st)
        self.T += [(a + o, b + o, c + o) for (a, b, c) in other.T]

    def offset(self, d):
        for i in range(len(self.V)): self.V[i] = np.asarray(self.V[i]) - np.asarray(d, float)

    def surface(self, name, shader):
        return dict(name=name, shader=shader, verts=np.array(self.V), normals=np.array(self.N), st=np.array(self.ST),
                    tris=np.array(self.T, np.int64))


def revolve(M, prof, u_tiles=1.0, v_of=None, n=48, a0=0.0, a1=360.0, inward=False):
    """surface of revolution of prof [(r, z)...]; v = arc length / 256 unless v_of given"""
    prof = np.asarray(prof, float)
    tg = np.gradient(prof, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    angs = np.radians(np.linspace(a0, a1, n + 1))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
    P = np.zeros((len(prof), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        P[:, j] = np.stack([prof[:, 0] * c, prof[:, 0] * s, prof[:, 1]], 1)
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


def torus(R, r, sq=1.0, nu=48, nv=20, utiles=3.0, z0=None):
    """torus round the z axis; v runs round the tube from the outer equator (0) over the top (0.25)"""
    M = Mesh()
    z0 = r * sq if z0 is None else z0
    th = np.linspace(0, 2 * math.pi, nu + 1); ph = np.linspace(0, 2 * math.pi, nv + 1)
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for i, p in enumerate(ph):
        for j, t in enumerate(th):
            rr = R + r * math.cos(p)
            P[i, j] = (rr * math.cos(t), rr * math.sin(t), z0 + r * sq * math.sin(p))
            n = np.array([math.cos(p) * math.cos(t) / r, math.cos(p) * math.sin(t) / r, math.sin(p) / (r * sq)])
            N[i, j] = n / np.linalg.norm(n)
            UV[i, j] = (t / (2 * math.pi) * utiles, p / (2 * math.pi))
    M.grid(P, N, UV)
    return M


# ================================================================================================= donut
def donut(seed, sprinkle_count=90):
    rr = np.random.default_rng(seed)
    R, r, sq = DONUT_R, DONUT_T, DONUT_SQ
    dough = torus(R, r, sq, 56, 22, 3.0)
    # icing: offset shell over the top half, its outer edge dripping down by a smooth random amount
    ice = Mesh()
    nu, nv = 112, 18
    th = np.linspace(0, 2 * math.pi, nu + 1)
    k = rr.normal(size=9) * np.array([0, .6, .5, .45, .4, .35, .3, .3, .25])
    ph0 = rr.uniform(0, 2 * math.pi, 9)
    def drip(t):
        v = sum(k[i] * math.sin(i * t * 2 + ph0[i]) for i in range(1, 9))
        return max(0.0, v) ** 1.4
    start = np.array([max(-1.05, -0.22 - 0.5 * drip(t)) for t in th]); start[-1] = start[0]
    end = math.pi + 0.55
    ro = r + 2.6
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for j, t in enumerate(th):
        for i in range(nv + 1):
            p = start[j] + (end - start[j]) * i / nv
            rad = R + ro * math.cos(p)
            P[i, j] = (rad * math.cos(t), rad * math.sin(t), r * sq + ro * sq * math.sin(p))
            n = np.array([math.cos(p) * math.cos(t) / ro, math.cos(p) * math.sin(t) / ro, math.sin(p) / (ro * sq)])
            N[i, j] = n / np.linalg.norm(n)
            UV[i, j] = (0.5 + P[i, j][0] / 320, 0.5 - P[i, j][1] / 320)
    ice.grid(P, N, UV)
    # lips that close the icing edge against the dough (outer drip edge + inner edge)
    for (pp, sgn) in ((start, -1), (np.full(nu + 1, end), 1)):
        Q = np.zeros((2, nu + 1, 3)); NQ = np.zeros_like(Q); UQ = np.zeros((2, nu + 1, 2))
        for j, t in enumerate(th):
            p = pp[j]
            for a, rad_ in enumerate((r - 0.5, ro)):
                rad = R + rad_ * math.cos(p)
                Q[a, j] = (rad * math.cos(t), rad * math.sin(t), r * sq + rad_ * sq * math.sin(p))
            tang = np.array([-math.sin(p) * math.cos(t), -math.sin(p) * math.sin(t), math.cos(p) * sq])
            NQ[:, j] = sgn * tang / np.linalg.norm(tang)
            UQ[:, j] = (0.5 + Q[1, j][0] / 320, 0.5 - Q[1, j][1] / 320)
        ice.grid(Q, NQ, UQ)
    # sprinkles: little rounded rods lying on the icing
    spr = Mesh()
    placed = 0
    while placed < sprinkle_count:
        t = rr.uniform(0, 2 * math.pi); p = rr.uniform(0.15, math.pi - 0.15)
        rad = R + (ro + 0.6) * math.cos(p)
        c = np.array([rad * math.cos(t), rad * math.sin(t), r * sq + (ro + 0.6) * sq * math.sin(p)])
        n = np.array([math.cos(p) * math.cos(t) / ro, math.cos(p) * math.sin(t) / ro, math.sin(p) / (ro * sq)]); n /= np.linalg.norm(n)
        a = rr.uniform(0, math.pi)
        e1 = np.cross(n, (0, 0, 1.0)) if abs(n[2]) < 0.95 else np.array([1.0, 0, 0])
        e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        d = e1 * math.cos(a) + e2 * math.sin(a); w = np.cross(n, d)
        col = rr.integers(0, 6)
        u0 = (col + 0.5) / 6
        L, W, Hh = 7.0, 1.9, 1.7
        corners = []
        for sx in (-1, 1):
            for sw in (-1, 1):
                for sh in (0, 1):
                    corners.append(c + d * sx * L + w * sw * W + n * sh * Hh * 2)
        C = np.array(corners).reshape(2, 2, 2, 3)
        faces = [((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1), n), ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0), -w),
                 ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1), w), ((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), -d),
                 ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0), d)]
        for f in faces:
            pts = [C[i] for i in f[:4]]
            spr.poly(pts, f[4] * 0.6 + n * 0.4, [(u0, 0.3), (u0, 0.7), (u0 + 0.02, 0.7), (u0 + 0.02, 0.3)])
        placed += 1
    return dough, ice, spr


# ================================================================================================= cereal
def cereal_spill(seed, count=64, rx=180, ry=120):
    """a heap of cereal rings lying on z 0, densest in the middle; three colour surfaces"""
    rr = np.random.default_rng(seed)
    ring = torus(15, 6.5, 0.9, 14, 8, 1.0)
    surf = [Mesh(), Mesh(), Mesh()]
    pts = []
    for k in range(count * 6):
        if len(pts) >= count: break
        a = rr.uniform(0, 2 * math.pi); f = math.sqrt(rr.uniform(0, 1))
        x, y = rx * f * math.cos(a), ry * f * math.sin(a)
        # stack height: rings near the centre sit on others
        z = 0.0
        for (px, py, pz) in pts:
            if math.hypot(px - x, py - y) < 26: z = max(z, pz + 10.5)
        if z > 44 * (1 - f) + 1: continue
        pts.append((x, y, z))
        tilt = 0 if z == 0 else rr.uniform(0.08, 0.35)
        R = rot_z(rr.uniform(0, 2 * math.pi)) @ rot_axis((1, 0, 0), tilt)
        surf[rr.integers(0, 3)].add(ring, R, (x, y, z + 2.5 * tilt))
    return surf


# ================================================================================================= faucet
def faucet():
    M = Mesh()
    cy = FAUCET_COL_Y
    def tr(m):
        m.offset((0, -cy, 0)); return m
    col = Mesh()
    revolve(col, [(84, 0), (84, 8), (78, 14), (62, 20), (54, 26), (52, 34), (52, 540), (52, 576)], 3, n=40)
    M.add(col, np.eye(3), (0, cy, 0))
    # spout arm: rounded-rectangle tube along -y, x -56..56, z 576..640, from y = cy + 56 to cy - 680
    rad = 22.0
    cs = []
    for (ccx, ccz, a0) in ((56 - rad, 640 - rad, 0), (-56 + rad, 640 - rad, 90), (-56 + rad, 576 + rad, 180), (56 - rad, 576 + rad, 270)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            cs.append((ccx + rad * math.cos(a), ccz + rad * math.sin(a), math.cos(a), math.sin(a)))
    cs.append(cs[0])
    y0, y1 = cy + 56, cy - FAUCET_REACH
    P = np.zeros((2, len(cs), 3)); N = np.zeros_like(P); UV = np.zeros((2, len(cs), 2))
    Lc = np.concatenate([[0], np.cumsum([math.hypot(cs[i + 1][0] - cs[i][0], cs[i + 1][1] - cs[i][1]) for i in range(len(cs) - 1)])])
    for j, (x, z, nx, nz) in enumerate(cs):
        for i, y in enumerate((y0, y1)):
            P[i, j] = (x, y, z); N[i, j] = (nx, 0, nz); UV[i, j] = (Lc[j] / 128, (y0 - y) / 256)
    M.grid(P, N, UV)
    for (y, ny) in ((y0, 1), (y1, -1)):
        pts = [(x, y, z) for (x, z, _, _) in cs[:-1]]
        if ny < 0: pts = pts[::-1]
        M.poly(pts[::-1] if ny > 0 else pts, (0, ny, 0), [(0.5 + x / 128, 0.5 - z / 128) for (x, y_, z) in pts])
    # aerator under the spout tip
    aer = Mesh()
    revolve(aer, [(26, 576), (26, 552), (22, 546)], 2, n=24)
    disc(aer, 22, 546, up=False, n=24)
    M.add(aer, np.eye(3), (0, cy - FAUCET_REACH + 44, 0))
    # lever on the back of the column (sticks out +y, rises)
    lev = Mesh()
    revolve(lev, [(18, 0), (18, 50), (14, 56)], 1, n=16)
    R = rot_axis((1, 0, 0), math.radians(-55))
    M.add(lev, R, (0, cy + 44, 470))
    # paddle: thin slab from the lever end, angled up-back
    p0 = np.array([0, cy + 44, 470]) + R @ np.array([0, 0, 52.0])
    d = R @ np.array([0, 0, 1.0]); w = np.array([1.0, 0, 0]); n = np.cross(d, w)
    corners = [p0 + d * a + w * b + n * c for a in (0, 70) for b in (-16, 16) for c in (-5, 5)]
    C = np.array(corners).reshape(2, 2, 2, 3)
    for f, nn in (((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1)), n), (((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), -n), \
                 (((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)), w), (((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)), -w), \
                 (((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)), d):
        M.poly([C[i] for i in f], nn, [(0, 0), (0, .3), (.3, .3), (.3, 0)])
    M.offset((0, 0, 320))
    return M


# ================================================================================================= pot
def pot():
    body, lid, steel = Mesh(), Mesh(), Mesh()
    revolve(body, [(0.01, 0), (176, 0), (188, 4), (192, 14), (192, 300), (193, 314), (197, 318), (198, 322), (195, 326), (189, 324)],
            4, v_of=lambda r, z: 1 - z / 330, n=64)
    # lid: steel rim + glass dome + steel knob
    revolve(steel, [(186, 322), (199, 323), (200, 328), (194, 331)], 6, n=64)
    revolve(lid, [(194, 331), (172, 339), (150, 345), (64, POT_LID_TOP)], 1, v_of=lambda r, z: 0.5 + r / 420, n=64)
    revolve(steel, [(64, POT_LID_TOP), (36, POT_LID_TOP + 2), (32, POT_LID_TOP + 18), (42, POT_LID_TOP + 30), (44, POT_LID_TOP + 40),
                    (36, POT_LID_TOP + 48), (0.01, POT_LID_TOP + 50)], 3, n=40)
    # handles: half loops sticking out on +x and -x at z 268
    for side in (0, math.pi):
        tube = Mesh()
        nu, nv = 20, 10
        P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
        for j in range(nu + 1):
            a = math.pi * j / nu - math.pi / 2           # -90..90 deg round the loop centre
            lc = np.array([182 + 30 * math.cos(a), 52 * math.sin(a), 268.0])
            tdir = np.array([-30 * math.sin(a), 52 * math.cos(a), 0]); tdir /= np.linalg.norm(tdir)
            b1 = np.array([0, 0, 1.0]); b2 = np.cross(tdir, b1)
            for i in range(nv + 1):
                p = 2 * math.pi * i / nv
                nn = b1 * math.sin(p) + b2 * math.cos(p)
                P[i, j] = lc + nn * 9; N[i, j] = nn; UV[i, j] = (j / nu, i / nv)
        tube.grid(P, N, UV)
        steel.add(tube, rot_z(side))
    return body, lid, steel


# ================================================================================================= kettle
KETTLE_R = 136.0


def kettle():
    """stovetop kettle: enamel dome body, steel lid + knob, curved spout, arched handle over the top (origin bottom centre)"""
    body, steel = Mesh(), Mesh()
    revolve(body, [(0.01, 0), (112, 0), (126, 6), (134, 24), (KETTLE_R, 60), (134, 120), (124, 180), (104, 230), (80, 262), (70, 270)],
            3, v_of=lambda r, z: 1 - z / 280, n=48)
    revolve(steel, [(70, 270), (72, 276), (60, 284), (30, 290), (16, 292), (14, 306), (20, 314), (16, 322), (0.01, 324)], 3, n=32)
    # spout: tapering tube from the body side (+x) rising outward
    nu, nv = 10, 12
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for j in range(nu + 1):
        t = j / nu
        c = np.array([110 + 120 * t, 0, 90 + 110 * t ** 1.4])
        d = np.array([120, 0, 154 * t ** 0.4 + 1e-3]); d /= np.linalg.norm(d)
        b1 = np.array([0, 1.0, 0]); b2 = np.cross(d, b1)
        r = 26 - 14 * t
        for i in range(nv + 1):
            p = 2 * math.pi * i / nv
            nn = b1 * math.cos(p) + b2 * math.sin(p)
            P[i, j] = c + nn * r; N[i, j] = nn; UV[i, j] = (t, i / nv)
    body.grid(P, N, UV)
    # handle: arch from (-70, 0, 250) over to (70, 0, 250), square-ish tube
    nu = 24
    P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
    for j in range(nu + 1):
        a = math.pi * j / nu
        c = np.array([-74 * math.cos(a), 0, 236 + 150 * math.sin(a)])
        d = np.array([74 * math.sin(a), 0, 150 * math.cos(a)]); d /= np.linalg.norm(d)
        b1 = np.array([0, 1.0, 0]); b2 = np.cross(d, b1)
        for i in range(nv + 1):
            p = 2 * math.pi * i / nv
            nn = b1 * math.cos(p) + b2 * math.sin(p)
            P[i, j] = c + nn * 10; N[i, j] = nn; UV[i, j] = (j / nu, i / nv)
    steel.grid(P, N, UV)
    return body, steel


# ================================================================================================= dish soap bottle
SOAP_R = 66.0


def soap_bottle():
    """squeezy dish soap bottle: label band round the body, white flip cap with a nozzle (origin bottom centre)"""
    body, label, cap = Mesh(), Mesh(), Mesh()
    revolve(body, [(0.01, 0), (58, 0), (64, 6), (SOAP_R, 20), (SOAP_R, 60)], 3, v_of=lambda r, z: 0.95, n=40)
    revolve(label, [(SOAP_R + 0.3, 60), (SOAP_R + 0.3, 230)], 1, v_of=lambda r, z: (230 - z) / 170, n=40)
    revolve(body, [(SOAP_R, 230), (64, 262), (52, 292), (34, 314), (26, 324)], 3, v_of=lambda r, z: 0.05, n=40)
    revolve(cap, [(26, 324), (30, 326), (30, 352), (20, 360), (10, 362), (9, 384), (4, 392), (0.01, 393)], 2, n=24)
    return body, label, cap


# ================================================================================================= flies
def fly_mesh():
    body, wings = Mesh(), Mesh()
    def ell(M, c, a, b, h, u0):
        nu, nv = 12, 8
        P = np.zeros((nv + 1, nu + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nv + 1, nu + 1, 2))
        for i in range(nv + 1):
            p = math.pi * i / nv - math.pi / 2
            for j in range(nu + 1):
                t = 2 * math.pi * j / nu
                P[i, j] = (c[0] + a * math.cos(p) * math.cos(t), c[1] + b * math.cos(p) * math.sin(t), c[2] + h * math.sin(p))
                n = np.array([math.cos(p) * math.cos(t) / a, math.cos(p) * math.sin(t) / b, math.sin(p) / h])
                N[i, j] = n / np.linalg.norm(n); UV[i, j] = (u0 + 0.2 * j / nu, i / nv)
        M.grid(P, N, UV)
    ell(body, (-3, 0, 0), 8, 4.5, 4.2, 0.0)        # abdomen (fly faces +x)
    ell(body, (5, 0, 0.5), 4, 4, 3.8, 0.25)         # thorax
    ell(body, (10, 0, 0.5), 2.6, 3.4, 3.0, 0.25)    # head
    ell(body, (11, 2.4, 1.2), 1.9, 1.6, 2.2, 0.75)  # eyes (red part of the strip)
    ell(body, (11, -2.4, 1.2), 1.9, 1.6, 2.2, 0.75)
    for sy in (1, -1):                               # wings: flat quads swept back
        pts = [(6, sy * 1.5, 4), (-8, sy * 12, 4.6), (-14, sy * 9, 4.6), (2, sy * 1.5, 4)]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        wings.poly(pts if sy > 0 else pts[::-1], (0, 0, 1), uv if sy > 0 else uv[::-1])
        wings.poly(pts[::-1] if sy > 0 else pts, (0, 0, -1), uv[::-1] if sy > 0 else uv)
    return body, wings


def flies():
    B, W = Mesh(), Mesh()
    fb, fw = fly_mesh()
    for (R, a, z, bank) in ((260, 0.0, 0.0, 0.35), (180, 2.4, 40.0, 0.5), (300, 4.1, -30.0, 0.3)):
        # facing along the direction of travel (counter-clockwise: +tangent), banked into the turn
        Rm = rot_z(a + math.pi / 2) @ rot_axis((1, 0, 0), -bank)
        t = (R * math.cos(a), R * math.sin(a), z)
        B.add(fb, Rm, t); W.add(fw, Rm, t)
    return B, W


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


def tex_dough(n=256):
    v = np.linspace(0, 1, n, endpoint=False)[:, None]
    # outer equator (v 0/1) pale band, browner on top / bottom, mid tone in the hole
    band = np.exp(-((np.minimum(v, 1 - v)) / 0.07) ** 2)
    base = np.array([196, 128, 62], np.float32) * (1 - band[..., None]) + np.array([238, 206, 150], np.float32) * band[..., None]
    a = np.repeat(base, n, axis=1) + _noise(n, 2, 1)[..., None] * 9 + _noise(n, 0.7, 2)[..., None] * 6
    a *= (1 + 0.05 * _noise(n, 18, 3))[..., None]
    return _img(a)


def tex_icing(col, n=256, seed=5):
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32)
    a += _noise(n, 10, seed)[..., None] * 7 + _noise(n, 1, seed + 1)[..., None] * 2
    # soft highlights (glossy blobs)
    hl = np.clip(_noise(n, 20, seed + 2), 1.2, 3) - 1.2
    a += hl[..., None] * 30
    return _img(a)


def tex_sprinkles():
    cols = [(240, 60, 70), (255, 220, 60), (80, 190, 240), (120, 220, 90), (250, 250, 245), (190, 110, 230)]
    im = Image.new('RGB', (192, 32))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(cols): d.rectangle((i * 32, 0, i * 32 + 31, 31), fill=c)
    return im


def tex_cereal(col, seed):
    a = np.zeros((64, 64, 3), np.float32) + np.array(col, np.float32)
    a += _noise(64, 1, seed)[..., None] * 14 + _noise(64, 5, seed + 1)[..., None] * 10
    return _img(a)


def tex_chrome():
    n = 256
    y = np.linspace(0, 1, n)[:, None]
    a = 150 + 70 * np.sin(y * 9) + 20 * _noise(n, 30, 9)
    a = np.repeat(a[..., None], 3, 2) * np.array([1, 1.02, 1.06])
    return _img(a)


def tex_env():
    """fake kitchen reflection for tcGen environment: warm ceiling light streaks, dark cabinets"""
    n = 256
    y = np.linspace(-1, 1, n)[:, None]; x = np.linspace(-1, 1, n)[None, :]
    a = np.zeros((n, n, 3), np.float32) + np.array([60, 44, 36], np.float32)
    a += (np.exp(-((y + 0.55) / 0.12) ** 2) * (0.6 + 0.4 * np.cos(x * 9))) [..., None] * np.array([255, 235, 200]) * 0.9
    a += (np.exp(-((y - 0.1) / 0.3) ** 2))[..., None] * np.array([90, 70, 60])
    a += _noise(n, 6, 11)[..., None] * 8
    return _img(a)


def tex_enamel(col, seed):
    n = 256
    a = np.zeros((n, n, 3), np.float32) + np.array(col, np.float32)
    a += _noise(n, 0.6, seed)[..., None] * 5 + _noise(n, 14, seed + 1)[..., None] * 8
    v = np.linspace(0, 1, n)[:, None]
    # white rim band at the top (v small = top), dark base band at the bottom
    rim = (v < 0.035)[..., None]
    a = np.where(rim, np.array([236, 236, 232], np.float32) + _noise(n, 1, seed + 2)[..., None] * 3, a)
    a = a * (1 - 0.35 * (v > 0.965))[..., None]
    # white speckles (classic enamelware)
    rr = np.random.default_rng(seed + 3)
    im = _img(a); d = ImageDraw.Draw(im)
    for _ in range(260):
        x, y = rr.integers(0, n), rr.integers(int(n * 0.05), int(n * 0.95)); r = rr.uniform(0.6, 1.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(250, 248, 240))
    return im.filter(ImageFilter.GaussianBlur(0.4))


def tex_glass_lid():
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.hypot(xx, yy)
    a = np.zeros((n, n, 3), np.float32) + np.array([70, 78, 82], np.float32)
    a += (np.exp(-((r - 0.33) / 0.03) ** 2) * 70)[..., None]
    a += _noise(n, 3, 21)[..., None] * 4
    # condensation dots
    rr = np.random.default_rng(22)
    im = _img(a); d = ImageDraw.Draw(im)
    for _ in range(500):
        x, y = rr.integers(0, n, 2); s = rr.uniform(0.6, 2.2)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(160, 170, 175))
    return im


def tex_steel():
    n = 256
    a = np.zeros((n, n, 3), np.float32) + 168 + _noise(n, 0.5, 31)[..., None] * 6
    a += (np.repeat(_noise(n, 1, 32)[:1], n, 0) * 6)[..., None]
    return _img(a)


def tex_soap():
    n = 128
    a = np.zeros((n, n, 3), np.float32) + np.array([96, 210, 90], np.float32) + _noise(n, 8, 71)[..., None] * 6
    return _img(a)


def tex_soap_label():
    w, h = 512, 256
    a = np.zeros((h, w, 3), np.float32) + np.array([96, 210, 90], np.float32)
    im = _img(a); d = ImageDraw.Draw(im)
    from PIL import ImageFont
    try: f = ImageFont.truetype('/usr/share/fonts/truetype/google-fonts/Poppins-BoldItalic.ttf', 80)
    except Exception: f = ImageFont.load_default()
    for k in range(3):                       # the label repeats round the bottle (u tiles = 1 over 360 deg)
        x0 = k * w / 3
        d.rounded_rectangle((x0 + 12, 30, x0 + w / 3 - 12, h - 30), radius=30, fill=(250, 250, 240))
        d.text((x0 + w / 6, 104), 'SUDZ', font=f, fill=(30, 120, 50), anchor='mm')
        d.text((x0 + w / 6, 176), 'PAD', font=f, fill=(240, 160, 30), anchor='mm')
    return im


def tex_plastic_white():
    n = 64
    return _img(np.zeros((n, n, 3), np.float32) + 236 + _noise(n, 3, 73)[..., None] * 3)


def tex_fly():
    im = Image.new('RGB', (128, 32), (36, 34, 32))
    d = ImageDraw.Draw(im)
    for k in range(5): d.line((k * 6, 0, k * 6, 31), fill=(70, 66, 60), width=2)   # banded abdomen
    d.rectangle((32, 0, 63, 31), fill=(60, 62, 58))                               # thorax / head grey
    d.rectangle((96, 0, 127, 31), fill=(150, 30, 26))                             # eyes
    return im


def tex_wing():
    n = 64
    a = np.zeros((n, n, 3), np.float32) + np.array([200, 205, 210], np.float32)
    al = np.full((n, n), 90.0)
    im = _img(a).convert('RGBA'); d = ImageDraw.Draw(im)
    for k in range(5): d.line((0, k * 14, 63, 6 + k * 12), fill=(80, 80, 80, 200), width=1)
    alpha = np.asarray(im)[..., 3].astype(np.float32)
    alpha = np.maximum(alpha * 0 + al, (np.asarray(im)[..., 0] < 120) * 200)
    im.putalpha(_img(alpha).convert('L'))
    return im


# ================================================================================================= shaders + make
def _vs(nm, tex=None, env=0.0, extra=''):
    """vertex-lit model shader (misc_model default), optional fake reflection"""
    t = tex or f'{MD}/{nm}'
    s = f'{MD}/{nm}\n{{\n\tqer_editorimage {t}\n{extra}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n'
    if env:
        s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {env} {env} {env} )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def shaders():
    S = '// ---- custom models (kitchen_models.py)\n'
    S += _vs('dough') + _vs('icing_pink', env=0.12) + _vs('icing_choc', env=0.10) + _vs('sprinkles')
    S += _vs('cereal_honey') + _vs('cereal_berry') + _vs('cereal_choc')
    S += _vs('chrome', env=0.75, extra='\tq3map_nonplanar\n\tq3map_shadeAngle 70\n')
    S += _vs('enamel_red', env=0.16, extra='\tq3map_shadeAngle 70\n') + _vs('enamel_blue', env=0.16, extra='\tq3map_shadeAngle 70\n')
    S += _vs('steel', env=0.4, extra='\tq3map_shadeAngle 70\n')
    S += (f'{MD}/lid_glass\n{{\n\tqer_editorimage {MD}/lid_glass\n\tq3map_shadeAngle 70\n'
          f'\t{{\n\t\tmap {MD}/lid_glass\n\t\trgbGen vertex\n\t}}\n'
          f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.45 0.45 0.45 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    S += _vs('soap_green', env=0.25) + _vs('soap_label', env=0.12) + _vs('plastic_white', env=0.1)
    S += _vs('fly')
    S += (f'{MD}/fly_wing\n{{\n\tqer_editorimage {MD}/fly_wing\n\tcull none\n\tsurfaceparm nonsolid\n'
          '\tdeformVertexes wave 6 sin 0 2.5 0 14\n'
          f'\t{{\n\t\tmap {MD}/fly_wing.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen vertex\n\t}}\n}}\n\n')
    return S


def make(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    sv = lambda nm, im: im.save(os.path.join(d, nm + '.jpg'), quality=92)
    sv('dough', tex_dough()); sv('icing_pink', tex_icing((242, 140, 170), seed=5)); sv('icing_choc', tex_icing((92, 52, 34), seed=7))
    sv('sprinkles', tex_sprinkles())
    sv('cereal_honey', tex_cereal((222, 160, 60), 41)); sv('cereal_berry', tex_cereal((200, 70, 120), 43)); sv('cereal_choc', tex_cereal((110, 64, 40), 45))
    sv('chrome', tex_chrome()); sv('env', tex_env())
    sv('enamel_red', tex_enamel((196, 40, 36), 51)); sv('enamel_blue', tex_enamel((36, 82, 190), 53))
    sv('soap_green', tex_soap()); sv('soap_label', tex_soap_label()); sv('plastic_white', tex_plastic_white())
    sv('steel', tex_steel()); sv('lid_glass', tex_glass_lid()); sv('fly', tex_fly())
    tex_wing().save(os.path.join(d, 'fly_wing.tga'))
    # donuts
    for nm, icing, seed in (('donut_pink', 'icing_pink', 3), ('donut_choc', 'icing_choc', 4)):
        dough, ice, spr = donut(seed)
        md3write.save(os.path.join(d, nm + '.md3'), [dough.surface('dough', f'{MD}/dough'), ice.surface('icing', f'{MD}/{icing}'),
                                                     spr.surface('sprinkles', f'{MD}/sprinkles')], name=nm)
    for k, seed in ((1, 61), (2, 62)):
        s = cereal_spill(seed)
        md3write.save(os.path.join(d, f'cereal_spill{k}.md3'), [m.surface(nm, f'{MD}/cereal_{nm}') for m, nm in zip(s, ('honey', 'berry', 'choc')) if m.V],
                      name=f'cereal_spill{k}')
    f = faucet()
    md3write.save(os.path.join(d, 'faucet.md3'), [f.surface('chrome', f'{MD}/chrome')], name='faucet')
    for team in ('red', 'blue'):
        body, lid, steel = pot()
        md3write.save(os.path.join(d, f'pot_{team}.md3'), [body.surface('body', f'{MD}/enamel_{team}'), lid.surface('lid', f'{MD}/lid_glass'),
                                                           steel.surface('steel', f'{MD}/steel')], name=f'pot_{team}')
    for team in ('red', 'blue'):
        kb, ks = kettle()
        md3write.save(os.path.join(d, f'kettle_{team}.md3'), [kb.surface('body', f'{MD}/enamel_{team}'), ks.surface('steel', f'{MD}/steel')],
                      name=f'kettle_{team}')
    sb_, sl_, sc_ = soap_bottle()
    md3write.save(os.path.join(d, 'soap.md3'), [sb_.surface('body', f'{MD}/soap_green'), sl_.surface('label', f'{MD}/soap_label'),
                                                sc_.surface('cap', f'{MD}/plastic_white')], name='soap')
    B, W = flies()
    md3write.save(os.path.join(d, 'flies.md3'), [B.surface('body', f'{MD}/fly'), W.surface('wings', f'{MD}/fly_wing')], name='flies')
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
