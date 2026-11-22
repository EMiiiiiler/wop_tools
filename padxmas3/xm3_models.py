"""Custom MD3 geometry for wop_padxmas3 (Padman's Christmas: Under the Tree). Original geometry built with meshlib.
Every builder returns a woplib.models.Model in MODEL space (origin = bottom centre unless noted); the generator saves
them with ML.save and places them with K.custom / K.prop / K.themed_pad. Collision lives in the generator.

Scale: ~16u per cm (Padman is 3.5 cm tall): a 40 cm present is a 640u building, the tree stand is a plastic tub
832u across, a bauble is a 700u glass dome."""
import math, random
import numpy as np
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, grid_normals
from woplib import models as ML
import xm3_art as A

M = A.M
Model = ML.Model


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def card(Mm, p, d, w, L, tilt=0.0, droop=0.0):
    """needle card: quad from p along unit vector d (length L), width w, rolled by `tilt` about d, ends drooping"""
    p = np.asarray(p, float); d = np.asarray(d, float); d = d / np.linalg.norm(d)
    side = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(side) < 1e-6: side = np.array([1.0, 0, 0])
    side /= np.linalg.norm(side)
    up = np.cross(side, d)
    s2 = side * math.cos(tilt) + up * math.sin(tilt)
    q = p + d * L + np.array([0, 0, -droop])
    pts = [p - s2 * w / 2, q - s2 * w / 2, q + s2 * w / 2, p + s2 * w / 2]
    n = np.cross(q - p, s2); n /= max(1e-6, np.linalg.norm(n))
    if n[2] < 0: n = -n
    Mm.poly(pts, n, [(0, 1), (1, 1), (1, 0), (0, 0)])


# ================================================================================================ the tree
def bough_path(ang, r0, z0, L, droop, n=9, wobble=0.0, seed=0):
    rr = random.Random(seed)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        d = r0 + L * t
        a = ang + wobble * math.sin(t * 3 + seed)
        pts.append((d * math.cos(a), d * math.sin(a), z0 - droop * t ** 1.6 + rr.uniform(-6, 6) * t))
    return pts


def dress_bough(X, pts, rad0, rad1, card_every=70.0, w0=200, w1=120, seed=0, dense=1.0):
    """bark tube + crossed needle cards along a bough path (cards on both sides, slanting outward, drooping tips)"""
    rr = random.Random(seed)
    pts = np.asarray(pts, float)
    tube(X.mesh(M['bark']), pts, np.linspace(rad0, rad1, len(pts)), nseg=8, caps=(False, True), vlen=256)
    nd = X.mesh(M['needles'])
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    tot = L[-1]
    s = 30.0
    while s < tot:
        t = s / tot
        i = min(np.searchsorted(L, s) - 1, len(pts) - 2); i = max(i, 0)
        f = (s - L[i]) / max(1e-6, L[i + 1] - L[i])
        p = pts[i] + (pts[i + 1] - pts[i]) * f
        d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d)
        side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
        w = w0 + (w1 - w0) * t
        for sg in (-1, 1):
            if rr.random() > dense: continue
            dd = d * 0.55 + side * sg * 0.85 + np.array([0, 0, -0.15])
            card(nd, p, dd, w * 0.55, w * 1.05, tilt=rr.uniform(-0.3, 0.3), droop=rr.uniform(10, 30))
        card(nd, p, d + np.array([0, 0, -0.05]), w * 0.7, card_every * 1.6, tilt=rr.uniform(-0.25, 0.25), droop=8)
        card(nd, p - np.array([0, 0, 6]), d, w * 0.5, card_every * 1.4, tilt=math.pi / 2, droop=12)
        s += card_every
    return pts


def hang_bauble(X, top, length, r, col, rng):
    top = np.asarray(top, float)
    c = top + [0, 0, -length - r]
    tube(X.mesh(M['thread']), [top, top + [0, 0, -length * 0.5], top + [0, 0, -length]], 1.2, nseg=4, caps=(False, False))
    cap = Mesh(); revolve(cap, [(r * 0.30, -r * 0.18), (r * 0.30, 0), (r * 0.18, r * 0.12), (0.1, r * 0.14)], n=12)
    X.mesh(M['brass']).add(cap, t=top + [0, 0, -length - r * 0.15])
    sphere(X.mesh(M['bauble_' + col]), c, r, nu=16, nv=10)


def light_string(X, a, b, sag, nb, cols, rng):
    a, b = np.asarray(a, float), np.asarray(b, float)
    pts = [a + (b - a) * t + np.array([0, 0, -sag * 4 * t * (1 - t)]) for t in np.linspace(0, 1, 12)]
    tube(X.mesh(M['cable']), pts, 2.2, nseg=4, caps=(False, False))
    for k in range(nb):
        t = (k + 0.5) / nb
        p = a + (b - a) * t + np.array([0, 0, -sag * 4 * t * (1 - t) - 8])
        col = cols[(k + rng.randint(0, 4)) % len(cols)]
        ellipsoid(X.mesh(M['bulb_' + col]), p, 6, 6, 11, nu=8, nv=5)


def canopy(trunk_z0, tiers, wall_y=None, skip_angle=None, seed=3):
    """the tree above the arena, in model space round the trunk axis (origin = trunk base): whorls of drooping
    boughs dressed with needle cards, an opaque needle skirt above each whorl so gaps show greenery (not sky),
    baubles hanging from the lowest whorl, fairy-light strings swagged between its boughs.
    tiers = [(z, length, droop, n_boughs)]. wall_y: shorten boughs that would poke through the room wall (local y)."""
    rr = random.Random(seed)
    X = Model()
    lights = []
    for ti, (z, L, droop, nb) in enumerate(tiers):
        tips = []
        for k in range(nb):
            ang = 2 * math.pi * (k + rr.uniform(-0.2, 0.2) + 0.5 * ti) / nb
            if skip_angle is not None and ti == 0 and abs(math.atan2(math.sin(ang - skip_angle), math.cos(ang - skip_angle))) < 0.2:
                continue
            LL = L * rr.uniform(0.86, 1.04)
            if wall_y is not None and math.sin(ang) > 0.05:
                LL = min(LL, (wall_y - 40) / math.sin(ang) - 140)
            pts = bough_path(ang, 120, z + rr.uniform(-40, 40), LL, droop * LL / L, wobble=0.06, seed=ti * 31 + k)
            dress_bough(X, pts, 34 - ti * 4, 8, seed=ti * 97 + k)
            # side branchlets
            for f in (0.35, 0.6, 0.82):
                p = np.asarray(pts[int(f * (len(pts) - 1))])
                for sg in (-1, 1):
                    a2 = ang + sg * rr.uniform(0.5, 0.8)
                    l2 = LL * 0.28 * (1 - f * 0.4)
                    q = [p, p + [l2 * 0.5 * math.cos(a2), l2 * 0.5 * math.sin(a2), -20], p + [l2 * math.cos(a2), l2 * math.sin(a2), -60]]
                    dress_bough(X, q, 12, 5, card_every=60, w0=150, w1=100, seed=ti * 13 + k * 7 + (sg > 0))
            tips.append((ang, pts))
        # opaque needle skirt above the whorl (hides the sky between boughs when seen from below)
        Lm = L * 0.98
        prof = [(Lm * t + 100, z + 60 - droop * t ** 1.6 + 30) for t in np.linspace(1, 0, 8)]
        def rf(a, r, zz, Lm=Lm):
            rmax = r
            if wall_y is not None and math.sin(a) > 0.05: rmax = min(r, (wall_y - 40) / math.sin(a))
            return rmax * (1 + 0.05 * math.sin(a * 11 + ti))
        revolve(X.mesh(M['needle_mass']), prof, u_tiles=16, n=48, rfun=rf, vlen=256, inward=False)
        if ti == 0:
            tips.sort()
            for i, (ang, pts) in enumerate(tips):
                # baubles hanging along the bough
                for f, col in ((0.55, list(A.BAUBLES)[i % 6]), (0.92, list(A.BAUBLES)[(i + 3) % 6])):
                    p = np.asarray(pts[int(f * (len(pts) - 1))])
                    hang_bauble(X, p - [0, 0, 6], rr.uniform(60, 160), rr.uniform(46, 70), col, rr)
                # light swag to the next bough
                ang2, pts2 = tips[(i + 1) % len(tips)]
                for f in (0.45, 0.8):
                    a_ = np.asarray(pts[int(f * (len(pts) - 1))]) - [0, 0, 10]
                    b_ = np.asarray(pts2[int(f * (len(pts2) - 1))]) - [0, 0, 10]
                    light_string(X, a_, b_, rr.uniform(70, 140), 9, 'rgbyw', rr)
                    lights.append(((a_ + b_) / 2 - [0, 0, 110]).tolist())
    return X, lights


def trunk(h, r=128):
    X = Model()
    prof = [(r + 10, 0), (r + 4, 30), (r, 80), (r * 0.98, h * 0.5), (r * 0.9, h)]
    revolve(X.mesh(M['bark']), prof, u_tiles=4, n=24, vlen=512, rfun=lambda a, rr, z: rr * (1 + 0.04 * math.sin(a * 7 + z * 0.002)))
    return X


def walk_branch_extras(X, nodes, widths, seed=8):
    """needles, a hanging bauble and lights on the walkable branch (world space; collision is the slab brushes).
    Cards only to the sides and below the walk surface so the path stays readable."""
    rr = random.Random(seed)
    nd = X.mesh(M['needles'])
    for i in range(len(nodes) - 1):
        p0, p1 = np.asarray(nodes[i], float), np.asarray(nodes[i + 1], float)
        d = p1 - p0; L = np.linalg.norm(d); d /= L
        side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
        for s in np.arange(10, L, 60):
            p = p0 + d * s
            w = widths[i] + (widths[i + 1] - widths[i]) * s / L
            for sg in (-1, 1):
                b = p + side * sg * (w / 2 - 6) + [0, 0, -14]
                card(nd, b, d * 0.5 + side * sg * 0.9 + [0, 0, -0.3], 120, 190, tilt=rr.uniform(-0.3, 0.3), droop=40)
            card(nd, p + [0, 0, -40], d, w * 1.1, 80, tilt=0, droop=4)
    tip = np.asarray(nodes[-1], float)
    hang_bauble(X, tip + [0, 0, -40], 120, 80, 'gold', rr)
    for i in range(len(nodes) - 1):
        a = np.asarray(nodes[i], float); b = np.asarray(nodes[i + 1], float)
        light_string(X, a + [0, 0, -46], b + [0, 0, -46], 50, 6, 'rgbyw', rr)


def skirt(r=1500, r_in=470):
    """felt tree skirt with a white fur hem, lying on the carpet (visual only)"""
    X = Model()
    disc(X.mesh(M['felt']), r - 40, 0.6, n=48, r_in=r_in, uvscale=512)
    revolve(X.mesh(M['fur']), [(r + 10, 0.2), (r + 4, 8), (r - 20, 12), (r - 46, 6), (r - 52, 0.8)], u_tiles=40, n=64)
    return X


# ================================================================================================ presents
def ribbon_bands(Mr, mn, mx, bx=None, by=None, bw=40, e=2.0, skip_side=None):
    """satin ribbon bands over the top and down the sides of box mn..mx: one along x at y=by, one along y at x=bx"""
    (x0, y0, z0), (x1, y1, z1) = mn, mx
    if by is not None:
        rbox(Mr, (x0 - e, by - bw / 2, z1 - 1), (x1 + e, by + bw / 2, z1 + e), r=0, k=1, tile=64, faces='tnsb')
        for xs, f in ((x1 - 1, 'ens'), (x0 - e, 'wns')):
            if skip_side != ('e' if f[0] == 'e' else 'w'):
                rbox(Mr, (xs, by - bw / 2, z0), (xs + 1 + e, by + bw / 2, z1 + e), r=0, k=1, tile=64, faces=f)
    if bx is not None:
        rbox(Mr, (bx - bw / 2, y0 - e, z1 - 1), (bx + bw / 2, y1 + e, z1 + e), r=0, k=1, tile=64, faces='tewb')
        for ys, f in ((y1 - 1, 'new'), (y0 - e, 'sew')):
            if skip_side != f[0]:
                rbox(Mr, (bx - bw / 2, ys, z0), (bx + bw / 2, ys + 1 + e, z1 + e), r=0, k=1, tile=64, faces=f)


def bow(Mr, c, size, bw):
    """two satin loops, two tails, a knot (on a lid at c)"""
    c = np.asarray(c, float)
    for sg in (-1, 1):
        path = []
        for t in np.linspace(0, 1, 22):
            a = 2 * math.pi * t
            path.append(c + [sg * size * 0.5 * (1 - math.cos(a)), 0, size * 0.42 * abs(math.sin(a)) * (1 - math.cos(a)) * 0.6 + 4])
        tube(Mr, path, bw * 0.42, nseg=6, ry=2.6, caps=(False, False), vlen=64)
        tail = [c + [sg * 4, sg * 6, 3], c + [sg * size * 0.35, sg * size * 0.5, 3.5], c + [sg * size * 0.55, sg * size * 0.85, 3]]
        tube(Mr, tail, bw * 0.38, nseg=6, ry=1.8, caps=(True, True), vlen=64)
    ellipsoid(Mr, c + [0, 0, 5], bw * 0.32, bw * 0.38, 8, nu=10, nv=6)


def gift(w, d, h, pat, bow_on=True, lid=True):
    """small wrapped present (cover prop): rounded box, lid overhang, crossing ribbons, a bow"""
    X = Model()
    pm = X.mesh(M['paper_' + pat]); rm = X.mesh(M['ribbon_' + A.PAPERS[pat][3]])
    hw, hd = w / 2, d / 2
    rbox(pm, (-hw, -hd, 0), (hw, hd, h - (14 if lid else 0)), r=3, k=2, tile=max(w, d, 128))
    if lid:
        rbox(pm, (-hw - 5, -hd - 5, h - 18), (hw + 5, hd + 5, h), r=3, k=2, tile=max(w, d, 128))
    bw = max(14, min(40, 0.16 * min(w, d)))
    ribbon_bands(rm, (-hw - 5 * lid, -hd - 5 * lid, 0), (hw + 5 * lid, hd + 5 * lid, h), bx=0, by=0, bw=bw)
    if bow_on: bow(rm, (0, 0, h + 2), min(w, d) * 0.32, bw)
    return X


def big_box_extras(X, mn, mx, pat, bx, by, door=None, top_bow=None, bw=56):
    """ribbons (and an optional big bow) for a building-sized present; door = (x0, x1, ztop) torn opening on -y"""
    rm = X.mesh(M['ribbon_' + A.PAPERS[pat][3]])
    ribbon_bands(rm, mn, mx, bx=bx, by=by, bw=bw, e=2.5)
    if top_bow is not None: bow(rm, top_bow, 220, bw)
    if door is not None:                                   # torn paper flaps curling out round the opening
        pm = X.mesh(M['paper_' + pat]); y = mn[1]
        rr = random.Random(int(mn[0]))
        x0, x1, zt = door
        edge = [(x0, 0)] + [(x0 - rr.uniform(6, 26), z) for z in np.linspace(20, zt - 10, 6)] + \
               [(x, zt + rr.uniform(4, 30)) for x in np.linspace(x0, x1, 7)] + \
               [(x1 + rr.uniform(6, 26), z) for z in np.linspace(zt - 10, 20, 6)] + [(x1, 0)]
        for (a, b) in zip(edge[:-1], edge[1:]):
            p0 = np.array([a[0], y - 1, a[1]]); p1 = np.array([b[0], y - 1, b[1]])
            q0 = p0 + [0, -18, 0]; q1 = p1 + [0, -22, 0]
            pm.poly([p0, p1, q1, q0], (0, 0, 1), [(0, 0), (0.3, 0), (0.3, 0.1), (0, 0.1)])
            pm.poly([q0, q1, p1, p0], (0, 0, -1), [(0, 0), (0.3, 0), (0.3, 0.1), (0, 0.1)])


def tissue_heap(w, d, seed=1):
    X = Model()
    rr = random.Random(seed)
    nx = ny = 9
    P = np.zeros((ny, nx, 3)); UV = np.zeros((ny, nx, 2))
    for i in range(ny):
        for j in range(nx):
            x = -w / 2 + w * j / (nx - 1); y = -d / 2 + d * i / (ny - 1)
            edge = min(i, j, ny - 1 - i, nx - 1 - j)
            P[i, j] = (x, y, 0.5 if edge == 0 else rr.uniform(6, 34) * min(1, edge / 2)); UV[i, j] = (x / 96, y / 96)
    N = grid_normals(P)
    if N[ny // 2, nx // 2, 2] < 0: N = -N
    X.mesh(M['tissue']).grid(P, N, UV)
    return X


# ================================================================================================ pad dressings
def tambourine(r=64):
    X = Model()
    revolve(X.mesh(M['wood']), [(r, 0), (r, 16), (r - 8, 16), (r - 8, 2)], n=24, u_tiles=4)
    disc(X.mesh(M['skin']), r - 8, 13, n=24)
    for k in range(6):
        a = k * math.pi / 3
        for dz in (5, 9):
            disc(X.mesh(M['brass']), 9, dz, n=8, cx=r * math.cos(a), cy=r * math.sin(a))
            disc(X.mesh(M['brass']), 9, dz - 1, up=False, n=8, cx=r * math.cos(a), cy=r * math.sin(a))
    return X


def slinky(r=56, h=26, turns=14, lean=36):
    X = Model()
    pts = []
    for t in np.linspace(0, 1, turns * 16):
        a = 2 * math.pi * turns * t
        pts.append((r * math.cos(a) + lean * t, r * math.sin(a), 3 + h * t))
    tube(X.mesh(M['slinky']), pts, 2.6, nseg=5, ry=4, utiles=1, vlen=64)
    return X


def flat_bow(col='red', size=80):
    X = Model()
    rm = X.mesh(M['ribbon_' + col])
    disc(X.mesh(M['ribbon_' + col]), size * 0.95, 1, n=20)
    bow(rm, (0, 0, 1), size * 1.4, 34)
    return X


def gum_pad(col='green', r=70):
    X = Model()
    revolve(X.mesh(M['gum_' + col]), [(r, 0), (r + 4, 6), (r, 13), (r * 0.6, 16), (0.1, 17)], n=20)
    return X


def spool(r=72):
    X = Model()
    revolve(X.mesh(M['wood']), [(r, 0), (r, 4), (r - 6, 5), (r - 6, 0)], n=20)
    revolve(X.mesh(M['ribbon_gold']), [(r - 12, 4), (r - 12, 14), (18, 14), (18, 4)], n=20, u_tiles=6)
    revolve(X.mesh(M['wood']), [(r, 12), (r, 16), (14, 16), (14, 12)], n=20)
    tube(X.mesh(M['ribbon_gold']), [(r - 12, 0, 15), (r + 30, -10, 14), (r + 90, 10, 14)], 12, nseg=4, ry=1.5)
    return X


# ================================================================================================ props
def pinecone(h=260, r=90):
    X = Model()
    rows = 11
    pm = X.mesh(M['pine'])
    tube(pm, [(0, 0, 0), (0, 0, 30)], 16, nseg=8)
    for i in range(rows):
        t = i / (rows - 1)
        z = 20 + (h - 40) * t
        rad = r * math.sin(math.pi * (0.15 + 0.8 * t)) ** 0.8 + 8
        n = 9
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (i % 2)) / n
            c = np.array([0.55 * rad * math.cos(a), 0.55 * rad * math.sin(a), z])
            R = rot_z(a) @ rot_y(-0.5)
            ellipsoid(pm, c, rad * 0.5, rad * 0.3, 10, nu=8, nv=4, R=R)
    return X


def candy_cane_lying(L=520, r=24, hook=80):
    X = Model()
    pts = [(-L / 2, 0, r), (L / 2 - hook, 0, r)]
    for a in np.linspace(0, math.pi, 10)[1:]:
        pts.append((L / 2 - hook + hook * math.sin(a), hook - hook * math.cos(a), r))
    tube(X.mesh(M['candy']), pts, r, nseg=12, utiles=1, twist=0.0, vlen=160)
    return X


def abc_block(s=128, faces=('A', 'B', 'C', 'X', 'M', 'S')):
    X = Model()
    h = s / 2
    for f, ch in zip('tnsewb', faces):
        rbox(X.mesh(M['abc_' + ch.lower()]), (-h, -h, 0), (h, h, s), r=6, k=2, tile=s, faces=f)
    return X


def lying_bauble(r, col):
    X = Model()
    sphere(X.mesh(M['bauble_' + col]), (0, 0, r), r, nu=20, nv=12)
    cap = Mesh(); revolve(cap, [(r * 0.3, 0), (r * 0.3, r * 0.22), (r * 0.1, r * 0.3), (0.1, r * 0.3)], n=12)
    X.mesh(M['brass']).add(cap, R=rot_y(math.pi / 2), t=(r * 0.92, 0, r))
    tube(X.mesh(M['brass']), [(r * 1.2, -12, r), (r * 1.32, 0, r + 6), (r * 1.2, 12, r)], 2.5, nseg=5)
    return X


def bauble_cap(r=100, L=90):
    """the crown of the big fallen bauble, lying along +x (origin = centre of its inner face)"""
    X = Model()
    m = Mesh()
    revolve(m, [(r, 0), (r, L * 0.7), (r * 0.8, L * 0.8), (r * 0.25, L), (0.1, L)], n=24, u_tiles=6)
    for k in range(12):
        a = 2 * math.pi * k / 12
        tube(m, [(r * math.cos(a), r * math.sin(a), -6), (r * 1.04 * math.cos(a), r * 1.04 * math.sin(a), L * 0.75)], 6, nseg=5)
    X.mesh(M['brass']).add(m, R=rot_y(math.pi / 2))
    loop = [(L + 50 * math.sin(t) * 0 + 40 * (1 - math.cos(t)), 0, 40 * math.sin(t) * 1.2) for t in np.linspace(0, 2 * math.pi, 20)]
    tube(X.mesh(M['brass']), [(L + p[0] * 0.8, p[1], p[2] * 0.8) for p in loop], 6, nseg=6, caps=(False, False))
    return X


def milk_glass(r=150, h=500, milk=360):
    X = Model()
    revolve(X.mesh(M['glass']), [(r - 4, 0), (r, 6), (r + 6, h), (r - 2, h)], n=32)
    revolve(X.mesh(M['milk']), [(r - 6, 2), (r - 3, milk), (0.1, milk)], n=32, u_tiles=2)
    return X


def cookie_stack(r, h, n, seed=0):
    X = Model()
    rr = random.Random(seed)
    for k in range(n):
        ox, oy = rr.uniform(-10, 10), rr.uniform(-10, 10)
        z = k * h
        revolve(X.mesh(M['cookie_side']), [(r * 0.96, z + 1), (r, z + h * 0.5), (r * 0.96, z + h - 1)], n=24, cx=ox, cy=oy, u_tiles=6)
        disc(X.mesh(M['cookie']), r * 0.96, z + h - 1, n=24, cx=ox, cy=oy, uvscale=2 * r)
    return X


def plug_and_cable(path):
    X = Model()
    rbox(X.mesh(M['plug']), (-40, -56, -48), (40, 0, 48), r=8, k=3, tile=96)
    tube(X.mesh(M['cable']), path, 9, nseg=8, caps=(True, True), vlen=128)
    return X


def rails(L, gauge=120):
    X = Model()
    for y in (-gauge / 2, gauge / 2):
        rbox(X.mesh(M['chrome']), (-L / 2, y - 6, 4), (L / 2, y + 6, 14), r=0, k=1, tile=128)
    for x in np.arange(-L / 2 + 20, L / 2, 64):
        rbox(X.mesh(M['wood']), (x - 14, -gauge / 2 - 34, 0), (x + 14, gauge / 2 + 34, 6), r=0, k=1, tile=64)
    return X


def wheel(Mm, Mh, c, r, w=16, axis_y=True):
    c = np.asarray(c, float)
    m = Mesh(); revolve(m, [(0.1, -w / 2), (r, -w / 2), (r, w / 2), (r * 0.8, w / 2 + 3), (0.1, w / 2 + 3)], n=20)
    R = rot_x(-math.pi / 2) if axis_y else np.eye(3)
    Mm.add(m, R=R, t=c)
    hub = Mesh(); revolve(hub, [(r * 0.35, w / 2 + 2), (r * 0.3, w / 2 + 8), (0.1, w / 2 + 9)], n=10)
    Mh.add(hub, R=R, t=c)


def ginger_man(h=300, t=16):
    """flat gingerbread man lying on the floor (union of convex prisms), icing outline dots"""
    X = Model()
    g = X.mesh(M['ginger'])
    parts = [((0, h * 0.78), h * 0.16), ]
    sphere_r = h * 0.15
    prism(g, [(math.cos(a) * sphere_r, h * 0.8 + math.sin(a) * sphere_r) for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)], 0, t, tile=128)
    prism(g, [(-h * 0.16, h * 0.62), (h * 0.16, h * 0.62), (h * 0.2, h * 0.3), (-h * 0.2, h * 0.3)], 0, t, tile=128)
    for s in (-1, 1):
        prism(g, sorted_ccw([(s * h * 0.12, h * 0.6), (s * h * 0.42, h * 0.55), (s * h * 0.44, h * 0.46), (s * h * 0.14, h * 0.48)]), 0, t, tile=128)
        prism(g, sorted_ccw([(s * h * 0.02, h * 0.32), (s * h * 0.2, h * 0.32), (s * h * 0.28, 0.0), (s * h * 0.1, 0.0)]), 0, t, tile=128)
    ic = X.mesh(M['icing'])
    for (x, y) in ((-0.05, 0.84), (0.05, 0.84), (0, 0.55), (0, 0.47), (0, 0.39)):
        ellipsoid(ic, (x * h, y * h, t), 7, 7, 3, nu=8, nv=4)
    tube(ic, [(math.cos(a) * h * 0.07, h * 0.78 + math.sin(a) * h * 0.05, t + 1) for a in np.linspace(math.pi * 1.15, math.pi * 1.85, 6)], 2.5, nseg=4)
    for s in (-1, 1):
        tube(ic, [(s * h * 0.36, h * 0.56, t + 1), (s * h * 0.38, h * 0.47, t + 1)], 3, nseg=4)
    X2 = Model()
    for sh, Mm in X.m.items(): X2.mesh(sh).add(Mm, t=(0, -h * 0.5, 0))
    return X2


def sorted_ccw(pts):
    c = np.mean(pts, 0)
    return sorted(pts, key=lambda p: math.atan2(p[1] - c[1], p[0] - c[0]))


def gumdrop(r=48, h=80, col='red'):
    X = Model()
    revolve(X.mesh(M['gum_' + col]), [(r, 0), (r * 1.02, h * 0.3), (r * 0.8, h * 0.8), (r * 0.4, h * 0.98), (0.1, h)], n=16)
    return X


def chimney_top(X, mn, mx):
    rbox(X.mesh(M['icing']), (mn[0] - 8, mn[1] - 8, mx[2] - 10), (mx[0] + 8, mx[1] + 8, mx[2] + 4), r=4, k=2, tile=64)
