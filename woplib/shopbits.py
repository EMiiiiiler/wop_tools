"""Shop / stall / bar dressing for custom MD3 buildings (first used on padwave's Surf Shop, Banana Hut and Tiki Bar).

The building shell stays a K.building + K.solid_piece (walls you can walk into, flat roof you can stand on). This module
adds the detail that makes it read as a real place, all as ONE extra MD3 per building with its own weapclip:

    D = Dress(K, 'surf_shop_dress', origin=(x, y, z))       # collects meshes + collision in world coordinates
    w = D.wall((x_face, y0), 'e')                            # a wall frame: local x = out of the wall, y = along it
    awning(D, w, sh_canvas, sh_metal, u0, u1, z_top, depth=72, drop=22)
    frame(D, w, sh_trim, u0, u1, z0, z1)                     # door / window trims
    surfboard(D, sh_board, base, lean_dir, ...)              # standing, leaning or lying boards
    stool(D, ..., (x, y, z)); totem(...); torch(...); thatch_skirt(...); fascia(...); banana_arch(...)
    D.finish()                                               # ML.save + K.custom with the collected collision

Rules baked in (the user's standing rules + audit): nothing goes above the roof top (clear line of fire), wall-mounted
parts start 0.5u off the wall face (never inside the collision), things that stand on the ground get a weapclip
cylinder/box so players don't walk through them.
"""
import math
import numpy as np
from meshlib import Mesh, tube, revolve, rbox, sphere, ellipsoid, rot_z
from . import models as ML

OUT = {'n': (0, 1, 0), 's': (0, -1, 0), 'e': (1, 0, 0), 'w': (-1, 0, 0)}


class Wall:
    """frame on a wall face: local (x = out of the wall, y = along it, left->right seen from outside, z = up).
    p0 = a point (x, y) on the face; u = 0 there. R has det +1 (no mirrored winding)."""
    def __init__(self, p0, side, z0=0.0):
        o = np.array(OUT[side], float); z = np.array([0, 0, 1.0])
        u = np.cross(-o, z)                      # viewer faces -o; right = (-o) x up
        self.O, self.U, self.Z = o, u, z
        self.R = np.stack([o, u, z], 1)
        self.p0 = np.array([p0[0], p0[1], z0], float)
        self.side = side

    def at(self, x, u, z):
        return self.p0 + self.O * x + self.U * u + self.Z * z

    def uof(self, coord):
        """the u of a world x (n/s walls) or y (e/w walls) coordinate"""
        ax = 0 if self.side in 'ns' else 1
        return (coord - self.p0[ax]) * self.U[ax]


class Dress:
    def __init__(self, K, name, origin):
        self.K, self.name = K, name
        self.o = np.array(origin, float)
        self.X = ML.Model()
        self.boxes, self.cyls = [], []

    def mesh(self, sh): return self.X.mesh(sh)

    def add(self, sh, local, R=np.eye(3), t=(0, 0, 0)):
        self.X.mesh(sh).add(local, R, t)

    def clip_box(self, mn, mx):
        """weapclip box in world coordinates"""
        self.boxes.append((tuple(np.subtract(mn, self.o)), tuple(np.subtract(mx, self.o))))

    def clip_cyl(self, x, y, r, z0, z1):
        self.cyls.append((x - self.o[0], y - self.o[1], r, z0 - self.o[2], z1 - self.o[2]))

    def wall(self, p0, side): return Wall(p0, side, 0.0)

    def finish(self, lit=True):
        self.X.shift(self.o)
        place = ML.save(self.name, self.X)
        return self.K.custom(place, float(self.o[0]), float(self.o[1]), float(self.o[2]), lit=lit,
                             boxes=self.boxes, cyls=self.cyls)


# ------------------------------------------------------------------------------------------------ wall-mounted parts
def awning(D, w, sh_canvas, sh_metal, u0, u1, z_top, depth=72.0, drop=22.0, valance=14.0, scallop=12.0, arms=True):
    """striped canvas awning on wall frame w between u0 and u1: slope from the wall (z_top) out to `depth` (z_top -
    drop), scalloped valance, side cheeks, two steel arms. Canvas shader should be two-sided (material two=True)."""
    M = D.mesh(sh_canvas)
    x0 = 0.5
    zt, zb = z_top, z_top - drop
    n = max(2, int((u1 - u0) / 16))
    us = np.linspace(u0, u1, n + 1)
    # slope (two rows), stripes run down it: texture u along the wall
    P = np.zeros((2, n + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, n + 1, 2))
    nrm = np.array([drop, 0, depth - x0]); nrm /= np.linalg.norm(nrm)
    for j, u in enumerate(us):
        P[0, j] = w.at(x0, u, zt); P[1, j] = w.at(depth, u, zb)
        N[:, j] = w.R @ nrm
        UV[0, j] = ((u - u0) / 64.0, 0); UV[1, j] = ((u - u0) / 64.0, 1)
    M.grid(P, N, UV)
    # valance with scallops
    ns = max(1, int((u1 - u0) / scallop))
    us = np.linspace(u0, u1, ns * 4 + 1)
    for j in range(len(us) - 1):
        ua, ub = us[j], us[j + 1]
        dz = lambda u: valance * (0.55 + 0.45 * abs(math.sin(math.pi * (u - u0) / ((u1 - u0) / ns))))
        quad = [w.at(depth, ua, zb), w.at(depth, ub, zb), w.at(depth, ub, zb - dz(ub)), w.at(depth, ua, zb - dz(ua))]
        M.poly(quad, w.R @ np.array([1.0, 0, 0]), [((ua - u0) / 64, 0), ((ub - u0) / 64, 0), ((ub - u0) / 64, 0.3), ((ua - u0) / 64, 0.3)])
    # cheeks
    for u, s in ((u0, -1), (u1, 1)):
        tri = [w.at(x0, u, zt), w.at(depth, u, zb), w.at(x0, u, zb)]
        M.poly(tri if s > 0 else tri[::-1], w.U * s, [(0, 0), (1, 1), (0, 1)])
    if arms:
        for u in (u0 + 6, u1 - 6):
            tube(D.mesh(sh_metal), [w.at(0.5, u, zb - 34), w.at(depth - 6, u, zb - 2)], 2.0, nseg=6, caps=(False, True))
            tube(D.mesh(sh_metal), [w.at(0.5, u, zb - 36), w.at(4, u, zb - 36)], 3.5, nseg=6)


def frame(D, w, sh, u0, u1, z0, z1, width=8.0, depth=4.0, sill=False):
    """trim round a door (z0 = floor) or window (sill=True adds a deeper ledge under it) on wall frame w"""
    def b(ua, ub, za, zb, dx=depth):
        loc = Mesh(); rbox(loc, (0.5, ua, za), (dx, ub, zb), r=1.0, k=1, tile=64)
        D.add(sh, loc, w.R, w.p0)
    b(u0 - width, u0, z0, z1 + width); b(u1, u1 + width, z0, z1 + width); b(u0 - width, u1 + width, z1, z1 + width)
    if sill: b(u0 - width - 4, u1 + width + 4, z0 - 6, z0, dx=depth + 8)


def fascia(D, sh, rect, z0, z1, depth=5.0, sides='nsew'):
    """trim band round the OUTSIDE of a building's walls between z0 and z1 (keep z1 <= the roof top: nothing above it
    so the roof keeps a clear line of fire). E/W bands cover the corners."""
    x0, y0, x1, y1 = rect
    for s in sides:
        loc = Mesh()
        if s == 's': rbox(loc, (x0, y0 - depth, z0), (x1, y0 - 0.5, z1), r=1.5, k=1, tile=64)
        if s == 'n': rbox(loc, (x0, y1 + 0.5, z0), (x1, y1 + depth, z1), r=1.5, k=1, tile=64)
        if s == 'w': rbox(loc, (x0 - depth, y0 - depth, z0), (x0 - 0.5, y1 + depth, z1), r=1.5, k=1, tile=64)
        if s == 'e': rbox(loc, (x1 + 0.5, y0 - depth, z0), (x1 + depth, y1 + depth, z1), r=1.5, k=1, tile=64)
        D.add(sh, loc)


def thatch_skirt(D, sh, rect, z_top, out=54.0, drop=40.0, gap=6.0, sides='nsew', fringe=10.0):
    """sloped thatch eaves round a hut, starting `gap` out from the walls at z_top (keep z_top below the roof top) with
    a jagged fringe; corners are closed with triangles. Shader two-sided."""
    x0, y0, x1, y1 = rect
    M = D.mesh(sh)
    zb = z_top - drop

    def panel(a, b, oa, ob):
        """a, b: wall-line points (x, y) of the inner edge; oa/ob: outward offsets at those ends (2-vectors)"""
        pa_i = np.array([a[0], a[1], z_top]); pb_i = np.array([b[0], b[1], z_top])
        pa_o = np.array([a[0] + oa[0], a[1] + oa[1], zb]); pb_o = np.array([b[0] + ob[0], b[1] + ob[1], zb])
        L = np.linalg.norm(pb_i - pa_i)
        nrm = np.cross(pb_i - pa_i, pa_o - pa_i); nrm /= np.linalg.norm(nrm)
        if nrm[2] < 0: nrm = -nrm
        M.poly([pa_i, pb_i, pb_o, pa_o], nrm, [(0, 0), (L / 64, 0), (L / 64, 1), (0, 1)])
        k = max(2, int(L / 14))
        for j in range(k):
            t0, t1, tm = j / k, (j + 1) / k, (j + 0.5) / k
            q0 = pa_o + (pb_o - pa_o) * t0; q1 = pa_o + (pb_o - pa_o) * t1
            qm = pa_o + (pb_o - pa_o) * tm - np.array([0, 0, fringe * (0.6 + 0.4 * math.sin(j * 2.3))])
            M.poly([q0, q1, qm], nrm * np.array([1, 1, 0.2]) / max(1e-6, np.linalg.norm(nrm * np.array([1, 1, 0.2]))),
                   [(t0 * L / 64, 1), (t1 * L / 64, 1), (tm * L / 64, 1.25)])
    g, o = gap, out
    if 's' in sides: panel((x0 - g, y0 - g), (x1 + g, y0 - g), (-o + g, -o + g), (o - g, -o + g))
    if 'n' in sides: panel((x1 + g, y1 + g), (x0 - g, y1 + g), (o - g, o - g), (-o + g, o - g))
    if 'e' in sides: panel((x1 + g, y0 - g), (x1 + g, y1 + g), (o - g, -o + g), (o - g, o - g))
    if 'w' in sides: panel((x0 - g, y1 + g), (x0 - g, y0 - g), (-o + g, o - g), (-o + g, -o + g))


# ------------------------------------------------------------------------------------------------ free-standing parts
def surfboard_mesh(length=200.0, width=46.0, thick=6.0, n=22, m=6, fin=True):
    """a surfboard in local space: long axis +y (nose at +length/2), width along x, thickness along z, centred"""
    loc = Mesh()
    ts = np.linspace(0.04, 1.0, n)
    P = {s: np.zeros((n, m * 2 + 1, 3)) for s in (1, -1)}
    UV = np.zeros((n, m * 2 + 1, 2))
    for i, t in enumerate(ts):
        y = (t - 0.5) * length
        hw = width / 2 * (math.sin(math.pi * min(1.0, t * 1.05)) ** 0.55) * (1 - 0.25 * t ** 3)
        for j, a in enumerate(np.linspace(-1, 1, m * 2 + 1)):
            x = a * hw
            zt = thick / 2 * math.sqrt(max(0.0, 1 - a * a)) * (0.4 + 0.6 * math.sin(math.pi * t))
            P[1][i, j] = (x, y, zt); P[-1][i, j] = (x, y, -zt)
            UV[i, j] = ((a + 1) / 2, t)
    for s in (1, -1):
        Q = P[s]
        Nn = ML.grid_normals_safe(Q)
        if (Nn[:, :, 2].mean() > 0) != (s > 0): Nn = -Nn
        loc.grid(Q, Nn, UV)
    if fin:
        y0 = -length / 2 + length * 0.1
        tri = [(0, y0, -thick / 2), (0, y0 + 22, -thick / 2), (0, y0 + 4, -thick / 2 - 16)]
        loc.poly(tri, (1, 0, 0), [(0, 0), (1, 0), (0.2, 1)]); loc.poly(tri[::-1], (-1, 0, 0), [(0.2, 1), (1, 0), (0, 0)])
    return loc


def surfboard(D, sh, base, up, face, **kw):
    """place a board: base = world point of its tail end, up = direction of its long axis (tail -> nose), face = the
    direction its deck (top) looks. Returns the nose point."""
    L = kw.get('length', 200.0)
    up = np.asarray(up, float); up /= np.linalg.norm(up)
    face = np.asarray(face, float); face = face - up * (face @ up); face /= np.linalg.norm(face)
    side = np.cross(up, face)
    R = np.stack([side, up, face], 1)
    c = np.asarray(base, float) + up * L / 2
    D.add(sh, surfboard_mesh(**kw), R, c)
    return c + up * L / 2


def stool(D, sh_seat, sh_leg, x, y, z, h=30.0, r=12.0, clip=True):
    revolve(D.mesh(sh_seat), [(r, h - 4), (r + 1, h - 1), (r - 2, h + 2), (0, h + 2.5)], n=16, cx=x, cy=y, vlen=64)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tube(D.mesh(sh_leg), [(x + (r - 3) * math.cos(a), y + (r - 3) * math.sin(a), h - 4),
                              (x + (r + 2) * math.cos(a), y + (r + 2) * math.sin(a), z)], 1.6, nseg=5, caps=(False, False))
    ring = [(x + (r - 1) * math.cos(a), y + (r - 1) * math.sin(a), z + h * 0.35) for a in np.linspace(0, 2 * math.pi, 13)]
    tube(D.mesh(sh_leg), ring, 1.0, nseg=4, caps=(False, False))
    if clip: D.clip_cyl(x, y, r, z, z + h)


def totem(D, sh_face, sh_wood, x, y, z, h=150.0, r=18.0, facing=0.0, clip=True):
    """carved tiki pole: stacked faces (face texture on every side), wing boards and a feathered top"""
    k = 3
    hb = (h - 18) / k
    for i in range(k):
        rr = r * (1.0 - 0.08 * i)
        rbox(D.mesh(sh_face), (x - rr, y - rr, z + i * hb), (x + rr, y + rr, z + (i + 1) * hb - 2), r=3, k=2, tile=2 * rr)
    a = math.radians(facing)
    d = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-d[1], d[0], 0])
    for sg in (-1, 1):
        c = np.array([x, y, z + hb * 1.5]) + s * sg * (r + 10)
        loc = Mesh(); rbox(loc, (-4, -10, -22), (4, 10, 22), r=2, k=1, tile=64)
        D.add(sh_wood, loc, np.stack([d, s, [0, 0, 1.0]], 1), c)
    for j in range(5):
        aa = math.radians(-50 + 25 * j)
        tip = np.array([x, y, z + h - 18]) + s * math.sin(aa) * 30 + np.array([0, 0, 18 + 16 * math.cos(aa)])
        tube(D.mesh(sh_wood), [np.array([x, y, z + h - 18]), tip], [4, 1.5], nseg=5, caps=(False, False))
    if clip: D.clip_cyl(x, y, r, z, z + h - 18)


def torch(D, sh_pole, sh_bowl, sh_flame, x, y, z, h=120.0, clip=True):
    """bamboo tiki torch: pole, bowl, two crossed flame quads (use an additive flickering flame shader)"""
    tube(D.mesh(sh_pole), [(x, y, z), (x, y, z + h)], [3.5, 3.0], nseg=6)
    revolve(D.mesh(sh_bowl), [(2, h - 6), (7, h - 2), (8, h + 6), (6.5, h + 7)], n=10, cx=x, cy=y)
    for a in (0, math.pi / 2):
        d = np.array([math.cos(a), math.sin(a), 0]) * 9
        q = [np.array([x, y, z + h + 4]) - d, np.array([x, y, z + h + 4]) + d, np.array([x, y, z + h + 34]) + d,
             np.array([x, y, z + h + 34]) - d]
        D.mesh(sh_flame).poly(q, np.cross(d, [0, 0, 1.0]) / 9, [(0, 1), (1, 1), (1, 0), (0, 0)])
    if clip: D.clip_cyl(x, y, 5, z, z + h)


def crate(D, sh, mn, mx, clip=True):
    rbox(D.mesh(sh), mn, mx, r=2, k=1, tile=48)
    if clip: D.clip_box(mn, mx)


def sandwich_board(D, sh_board, sh_wood, x, y, z, facing=0.0, h=64.0, w=36.0, clip=True):
    """A-frame menu board standing on the ground, label on both faces"""
    a = math.radians(facing)
    d = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-d[1], d[0], 0])
    c = np.array([x, y, z])
    for sg in (1, -1):
        foot = c + d * sg * 14
        top = c + d * sg * 2 + np.array([0, 0, h])
        q = [foot - s * w / 2, foot + s * w / 2, top + s * w / 2, top - s * w / 2]
        nn = np.cross(q[1] - q[0], q[3] - q[0]); nn /= np.linalg.norm(nn)
        if nn @ d * sg < 0: q = q[::-1]; nn = -nn
        D.mesh(sh_board).poly([p + nn * 0.6 for p in q], nn, [(0, 1), (1, 1), (1, 0), (0, 0)] if sg > 0 else [(1, 1), (0, 1), (0, 0), (1, 0)])
        for e in (-1, 1):
            tube(D.mesh(sh_wood), [foot + s * e * (w / 2 + 2), top + s * e * (w / 2 + 2)], 1.8, nseg=5)
    if clip: D.clip_box((x - 16, y - 16, z), (x + 16, y + 16, z + h - 8))


def banana_mesh(length=120.0, r=11.0, bend=0.35, n=16):
    """a banana in local space along +y, curving up (+z); returns (body mesh, stem/tip mesh)"""
    body, tips = Mesh(), Mesh()
    Rb = length / (2 * math.sin(bend))
    path = [np.array([0.0, Rb * math.sin(a), -Rb * math.cos(a) + Rb * math.cos(bend)]) for a in np.linspace(-bend, bend, n)]
    radii = [r * (math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.5) for t in np.linspace(0, 1, n)]
    tube(body, path, radii, nseg=5, caps=(True, True), vlen=length)
    tube(tips, [path[-1], path[-1] + (path[-1] - path[-2]) * 0.8], [radii[-1] * 0.9, 2.0], nseg=5)
    tube(tips, [path[0] + (path[0] - path[1]) * 0.4, path[0]], [1.5, radii[0]], nseg=5)
    return body, tips


def banana_bunch(D, sh_body, sh_tip, top, k=5, size=30.0, hang=True):
    """small bunch of bananas; hang=True hangs it from `top` (string up to top)"""
    top = np.asarray(top, float)
    c = top - np.array([0, 0, 10]) if hang else top
    for j in range(k):
        a = 2 * math.pi * j / k
        body, tips = banana_mesh(size, size * 0.11, 0.45, 10)
        R = rot_z(a) @ np.array([[1, 0, 0], [0, math.cos(2.4), -math.sin(2.4)], [0, math.sin(2.4), math.cos(2.4)]])   # tips down-out
        D.add(sh_body, body, R, c + np.array([math.cos(a), math.sin(a), 0]) * 3)
        D.add(sh_tip, tips, R, c + np.array([math.cos(a), math.sin(a), 0]) * 3)
    if hang: tube(D.mesh(sh_tip), [c, top], 0.8, nseg=4, caps=(False, False))


def lantern(D, sh_paper, sh_cord, x, y, z_ceiling, drop=30.0, r=9.0):
    sphere(D.mesh(sh_paper), (x, y, z_ceiling - drop - r), r, 10, 8)
    tube(D.mesh(sh_cord), [(x, y, z_ceiling - 0.5), (x, y, z_ceiling - drop)], 0.6, nseg=4, caps=(False, False))
