"""Custom MD3 props and movers for wop_padbakery (Sweet Padman's Bakery). All geometry and art is original.
Props have their origin at the floor centre (the model rests on z 0). Padman scale: ~8u per cm.

BOX[name] lists the collision boxes (local mn, mx) the builder turns into common/weapclip; props without an entry
are small enough to walk over or sit on surfaces only."""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from bk_mesh import *
import layout as L

BOX = {}            # name -> [((x0,y0,z0),(x1,y1,z1)), ...] local collision
CYL = {}            # name -> [(x, y, r, z0, z1)] local collision cylinders


def SM(img, shade=60, **kw): return S(img, 'lm', shade=shade, **kw)
def SV(img, **kw): return S(img, 'vl', **kw)
def SC(img='steel', v=0.2, **kw): return S(img, 'lms', v=v, shade=kw.pop('shade', 50), **kw)


def ground(X):
    """shift a model so its lowest vertex sits on z 0"""
    zmin = min(min(v[2] for v in M.V) for M in X.m.values() if len(M.V))
    for M in X.m.values(): M.V = [v - np.array([0, 0, zmin]) for v in M.V]
    return X


def swirl(M, c, r0, h, turns=3.0, n=60, rt=None):
    """piped frosting swirl: a tube spiralling up and in from radius r0 to the tip"""
    c = np.asarray(c, float)
    pts, rad = [], []
    for k in range(n + 1):
        t = k / n
        a = 2 * math.pi * turns * t
        r = r0 * (1 - t) ** 0.85
        pts.append(c + np.array([r * math.cos(a), r * math.sin(a), h * t * 0.75]))
        rad.append((rt or r0 * 0.42) * (1 - 0.65 * t))
    tube(M, pts, rad, nseg=10, caps=(True, True))


# ================================================================================================= small sweets
def cupcake(name, liner='liner_p', frost='bc_pink', top='cherry', r=30.0):
    X = Model()
    h = r * 1.15
    revolve(X.mesh(SM(liner, 70, tag='cc')), [(0, 0), (r * 0.78, 0), (r, h)], n=24, u_tiles=1, vlen=h)
    disc(X.mesh(SM('crust', tag='cc')), r, h, up=True, n=24)
    swirl(X.mesh(SM(frost, 70, tag='cc' + frost)), (0, 0, h + r * 0.25), r * 0.95, r * 1.5, turns=2.6)
    tip = h + r * 0.25 + r * 1.5 * 0.75
    if top == 'cherry':
        sphere(X.mesh(SM('red', 70, tag='cc')), (0, 0, tip + 6), 9, nu=10, nv=6)
        tube(X.mesh(SM('leaf', tag='cc')), [(0, 0, tip + 14), (4, 2, tip + 24), (10, 4, tip + 30)], 1.5, nseg=5)
    elif top == 'berry':
        revolve(X.mesh(SM('strawberry', tag='cc')), [(0, tip - 2), (9, tip + 4), (11, tip + 12), (0, tip + 22)], n=10, vlen=24)
    elif top == 'chips':
        rng = np.random.default_rng(len(name))
        for k in range(9):
            a = rng.uniform(0, 6.28); rr = rng.uniform(4, r * 0.7); zz = h + r * 0.4 + (1 - rr / r) * r
            revolve(X.mesh(SM('choc_d', tag='cc')), [(0, zz), (4, zz), (0, zz + 6)], n=6, cx=rr * math.cos(a), cy=rr * math.sin(a))
    elif top == 'pearls':
        for k in range(7):
            a = 2 * math.pi * k / 7
            sphere(X.mesh(SM('pearl', 70, tag='cc')), (r * 0.6 * math.cos(a), r * 0.6 * math.sin(a), h + r * 0.55), 4, nu=6, nv=4)
        sphere(X.mesh(SM('pearl', 70, tag='cc')), (0, 0, tip + 3), 6, nu=8, nv=5)
    CYL[name] = [(0, 0, r * 0.9, 0, tip)]
    return save(name, X)


def donut(name, glaze='bc_pink', spr='sprinkles'):
    X = Model()
    R, r = 36.0, 17.0
    torus(X.mesh(SM('crust', 60, tag='dn')), (0, 0, r), R, r, n=28, m=12)
    # the glaze: upper half of a slightly bigger torus, scalloped edge
    m = X.mesh(SM(spr if spr else glaze, 70, tag='dn' + glaze))
    nA, nB = 32, 7
    P = np.zeros((nB + 1, nA + 1, 3)); UV = np.zeros((nB + 1, nA + 1, 2))
    for i in range(nA + 1):
        a = 2 * math.pi * i / nA
        wob = 0.25 * math.sin(a * 7)
        for j in range(nB + 1):
            b = -0.15 - wob + (math.pi + 0.3 + 2 * wob) * j / nB
            rr = R + (r + 1.5) * math.cos(b)
            P[j, i] = (rr * math.cos(a), rr * math.sin(a), r + (r + 1.5) * math.sin(b))
            UV[j, i] = (i / nA * 4, j / nB)
    N = grid_normals(P)
    if (N[nB // 2, 0] @ np.array([0, 0, 1.0])) < 0: N = -N
    m.grid(P, N, UV)
    CYL[name] = [(0, 0, R + r - 6, 0, 2 * r)]
    return save(name, X)


def macaron(name, col='bc_pink', fill='bc_white'):
    X = Model()
    sh = SM(col, 70, tag='mc' + col)
    for (z0, up) in ((0, False), (12, True)):
        ellipsoid(X.mesh(sh), (0, 0, z0 + (2 if up else 8)), 20, 20, 9, nu=14, nv=6, flat_bottom=(-1 if up else None))
    revolve(X.mesh(SM(fill, 70, tag='mcf')), [(19, 8), (20, 10), (19, 13)], n=16)
    return save(name, X)


def eclair(name='eclair'):
    X = Model()
    ellipsoid(X.mesh(SM('crust', tag='ec')), (0, 0, 14), 48, 14, 13, nu=16, nv=8, flat_bottom=-12)
    ellipsoid(X.mesh(SM('choc', 70, tag='ec')), (0, 0, 19), 44, 12, 9, nu=16, nv=6, flat_bottom=0)
    ground(X)
    return save(name, X)


def croissant(name='croissant'):
    X = Model()
    cr = SM('crust', 60, tag='cr')
    for k in range(7):
        t = (k - 3) / 3.0
        a = t * 1.2
        p = (math.sin(a) * 60, -math.cos(a) * 30 + 30, 16 - abs(t) * 6)
        sz = 1 - abs(t) * 0.55
        ellipsoid(X.mesh(cr), p, 22 * sz, 18 * sz, 16 * sz, nu=12, nv=7, R=rot_z(a), flat_bottom=-(16 - abs(t) * 6) / max(sz, 0.3) * 0 - 10 * sz)
    ground(X)
    return save(name, X)


def loaf(name='loaf', L_=200.0, W_=110.0, H_=90.0, crust='crust', slashes=3):
    X = Model()
    ellipsoid(X.mesh(SM(crust, 60, tag='lf' + crust)), (0, 0, H_ * 0.45), L_ / 2, W_ / 2, H_ * 0.55, nu=20, nv=10, flat_bottom=-H_ * 0.45)
    for k in range(slashes):
        x = (k - (slashes - 1) / 2) * L_ / (slashes + 0.5)
        ellipsoid(X.mesh(SM('dough', 60, tag='lf')), (x, 0, H_ * 0.96), W_ * 0.12, W_ * 0.36, 4, nu=8, nv=4, R=rot_z(0.5))
    BOX[name] = [((-L_ / 2 + 12, -W_ / 2 + 10, 0), (L_ / 2 - 12, W_ / 2 - 10, H_ - 8))]
    return save(name, X)


def boule(name='boule', r=80.0):
    X = Model()
    ellipsoid(X.mesh(SM('crust_d', 60, tag='bl')), (0, 0, r * 0.35), r, r, r * 0.6, nu=20, nv=10, flat_bottom=-r * 0.35)
    for a in (0, math.pi / 2):
        ellipsoid(X.mesh(SM('flour', 60, tag='bl')), (0, 0, r * 0.94), r * 0.7, 5, 3, nu=10, nv=4, R=rot_z(a))
    CYL[name] = [(0, 0, r * 0.85, 0, r * 0.9)]
    return save(name, X)


# ================================================================================================= display cakes
def round_cake(name, side='bc_white', top='bc_white', r=96.0, h=88.0, deco='berries'):
    X = Model()
    revolve(X.mesh(SM(side, 50, tag='rc' + side)), [(0, 0), (r, 0), (r, h)], n=40, u_tiles=4, vlen=128)
    disc(X.mesh(SM(top, 50, tag='rc' + top)), r, h, n=40)
    bead_n = int(2 * math.pi * r / 18)
    for k in range(bead_n):
        a = 2 * math.pi * k / bead_n
        sphere(X.mesh(SM(top, 70, tag='rcb' + top)), ((r - 6) * math.cos(a), (r - 6) * math.sin(a), h + 4), 8, nu=8, nv=5)
    if deco == 'berries':
        for k in range(8):
            a = 2 * math.pi * k / 8
            revolve(X.mesh(SM('strawberry', tag='rc')), [(0, h), (10, h + 6), (13, h + 14), (0, h + 26)], n=10, vlen=26,
                    cx=(r * 0.55) * math.cos(a), cy=(r * 0.55) * math.sin(a))
    elif deco == 'drip':
        rng = np.random.default_rng(len(name))
        ch = SM('choc', 60, tag='rcd')
        disc(X.mesh(ch), r + 2, h + 1, n=40)
        for k in range(22):
            a = 2 * math.pi * (k + rng.uniform(-0.2, 0.2)) / 22
            Ld = rng.uniform(14, 40)
            ellipsoid(X.mesh(ch), ((r + 1) * math.cos(a), (r + 1) * math.sin(a), h - Ld * 0.45), 6, 6, Ld * 0.55, nu=6, nv=5)
        for k in range(5):
            a = 2 * math.pi * k / 5
            sphere(X.mesh(SM('red', 70, tag='rc')), (r * 0.5 * math.cos(a), r * 0.5 * math.sin(a), h + 8), 8, nu=8, nv=5)
    elif deco == 'lemon':
        for k in range(7):
            a = 2 * math.pi * k / 7
            m = Mesh(); revolve(m, [(0, -3), (16, -3), (16, 3), (0, 3)], n=12)
            X.mesh(SM('bc_lemon', 60, tag='rcl')).add(m, rot_axis((math.cos(a + 1.57), math.sin(a + 1.57), 0), 1.2),
                                                     ((r * 0.62) * math.cos(a), (r * 0.62) * math.sin(a), h + 10))
    CYL[name] = [(0, 0, r - 4, 0, h + 8)]
    return save(name, X)


def cake_stand_cake(name='standcake'):
    """tall glass-domed cake on a pedestal stand (display cabinet top)"""
    X = Model()
    ch = SC('steel', 0.3, tag='sc')
    revolve(X.mesh(ch), [(0, 0), (60, 0), (50, 10), (14, 20), (12, 70), (110, 74), (110, 82), (0, 82)], n=32)
    revolve(X.mesh(SM('bc_choc', 50, tag='sc')), [(0, 82), (86, 82), (86, 170), (0, 170)], n=32, vlen=96)
    swirl(X.mesh(SM('bc_white', 70, tag='scw')), (0, 0, 176), 40, 50, 2.0)
    revolve(X.mesh(S('glass_g', 'glass', tag='sc')), [(108, 82), (108, 220), (80, 262), (20, 276), (0, 278)], n=32)
    sphere(X.mesh(ch), (0, 0, 286), 10, nu=8, nv=5)
    CYL[name] = [(0, 0, 100, 0, 276)]
    return save(name, X)


def cupcake_tower(name='cctower'):
    """three-tier cupcake stand (east counter) loaded with cupcakes"""
    X = Model()
    ch = SC('steel', 0.3, tag='ct')
    tube(X.mesh(ch), [(0, 0, 0), (0, 0, 330)], 8, nseg=10)
    rng = np.random.default_rng(9)
    kinds = [('liner_p', 'bc_pink'), ('liner_b', 'bc_blue'), ('liner_g', 'bc_lemon'), ('liner_p', 'bc_choc'), ('liner_b', 'bc_mint')]
    for (rr, zz) in ((170, 0), (124, 110), (78, 220)):
        revolve(X.mesh(SM('white', 50, tag='ct')), [(0, zz), (rr, zz), (rr + 4, zz + 8), (rr, zz + 10), (0, zz + 10)], n=32)
        k = max(1, int(rr / 30))
        for j in range(k if rr < 100 else k + 1):
            a = 2 * math.pi * j / (k if rr < 100 else k + 1) + zz
            ln, fr = kinds[j % len(kinds)]
            m = Model(); _cup_into(m, 24, ln, fr)
            X.add_model(m, rot_z(a), ((rr - 34) * math.cos(a), (rr - 34) * math.sin(a), zz + 10))
    sphere(X.mesh(ch), (0, 0, 336), 12, nu=8, nv=5)
    CYL[name] = [(0, 0, 160, 0, 12), (0, 0, 20, 12, 330)]
    return save(name, X)


def _cup_into(X, r, liner, frost):
    h = r * 1.15
    revolve(X.mesh(SM(liner, 70, tag='cc')), [(0, 0), (r * 0.78, 0), (r, h)], n=16, u_tiles=1, vlen=h)
    swirl(X.mesh(SM(frost, 70, tag='cc' + frost)), (0, 0, h + r * 0.25), r * 0.95, r * 1.5, turns=2.4, n=36)


# ================================================================================================= ingredients and stock
def flour_sack(name='sack_flour', tex='sack_flour', L_=600.0, W_=380.0, H_=118.0):
    """a 25 kg sack lying flat (pillow shape), print on top"""
    X = Model()
    rbox(X.mesh(SM(tex, 50, tag='sk' + tex)), (-L_ / 2, -W_ / 2, 0), (L_ / 2, W_ / 2, H_), r=H_ * 0.42, k=4, tile=W_ * 1.6)
    # the sewn ends: puffy seams
    for s in (-1, 1):
        tube(X.mesh(SM(tex, 50, tag='sk' + tex)), [(s * (L_ / 2 - 4), -W_ / 2 + 20, H_ * 0.5), (s * (L_ / 2 - 4), W_ / 2 - 20, H_ * 0.5)], 10, nseg=8)
    BOX[name] = [((-L_ / 2 + 16, -W_ / 2 + 16, 0), (L_ / 2 - 16, W_ / 2 - 16, H_ - 6))]
    return save(name, X)


def sugar_bag(name='sugar_bag'):
    """a 10 kg sugar bag standing up, the top folded"""
    X = Model()
    rbox(X.mesh(SM('sack_sugar', 50, tag='sb')), (-110, -60, 0), (110, 60, 300), r=30, k=3, tile=380)
    rbox(X.mesh(SM('sack_sugar', 50, tag='sb')), (-100, -24, 290), (100, 24, 340), r=14, k=2, tile=380)
    BOX[name] = [((-100, -52, 0), (100, 52, 330))]
    return save(name, X)


def egg_stack(name='eggs', n=4):
    """stacked egg trays (5 x 6 eggs), eggs showing on the top tray"""
    X = Model()
    W_ = 250.0
    ca = SM('carton', 60, tag='eg')
    for k in range(n):
        z0 = k * 46
        rbox(X.mesh(ca), (-W_ / 2, -W_ / 2, z0), (W_ / 2, W_ / 2, z0 + 22), r=3, k=1, tile=128)
        for i in range(5):
            for j in range(6 if k == n - 1 else 0):
                pass
    zt = (n - 1) * 46 + 22
    rng = np.random.default_rng(3)
    for i in range(5):
        for j in range(5):
            x, y = -W_ / 2 + 25 + i * 50, -W_ / 2 + 25 + j * 50
            ellipsoid(X.mesh(SM('shell' if (i + j) % 3 else 'shell_w', 70, tag='eg')), (x, y, zt + 18), 19, 19, 25, nu=12, nv=7, flat_bottom=-14)
    for k in range(n - 1):
        for (x, y) in ((-W_ / 2 + 8, -W_ / 2 + 8), (W_ / 2 - 8, -W_ / 2 + 8), (-W_ / 2 + 8, W_ / 2 - 8), (W_ / 2 - 8, W_ / 2 - 8)):
            cylm(X.mesh(ca), (x, y, k * 46 + 22), 7, 24, n=6, caps=False)
    BOX[name] = [((-W_ / 2 + 4, -W_ / 2 + 4, 0), (W_ / 2 - 4, W_ / 2 - 4, zt + 30))]
    return save(name, X)


def butter(name='butter'):
    X = Model()
    rbox(X.mesh(SM('butter', 60, tag='bt')), (-52, -28, 0), (52, 28, 28), r=3, k=1, tile=104)
    return save(name, X)


def milk_crate(name='milkcrate'):
    """plastic crate with nine milk bottles"""
    X = Model()
    W_, H_ = 264.0, 150.0
    cr = SM('crate', 50, tag='mk')
    for (mn, mx) in (((-W_ / 2, -W_ / 2, 0), (W_ / 2, W_ / 2, 10)),
                     ((-W_ / 2, -W_ / 2, 0), (W_ / 2, -W_ / 2 + 10, H_)), ((-W_ / 2, W_ / 2 - 10, 0), (W_ / 2, W_ / 2, H_)),
                     ((-W_ / 2, -W_ / 2, 0), (-W_ / 2 + 10, W_ / 2, H_)), ((W_ / 2 - 10, -W_ / 2, 0), (W_ / 2, W_ / 2, H_))):
        rbox(X.mesh(cr), mn, mx, r=2, k=1, tile=128)
    gl, lb, cap = S('glass_g', 'glass', tag='mk'), SM('milk_label', 60, tag='mk'), SM('red', 60, tag='mk')
    for i in range(3):
        for j in range(3):
            x, y = (i - 1) * 82, (j - 1) * 82
            revolve(X.mesh(SM('white', 60, tag='mkm')), [(0, 10), (34, 10), (34, 150), (22, 190), (14, 214), (0, 214)], n=16, cx=x, cy=y)
            revolve(X.mesh(lb), [(35, 60), (35, 130)], n=16, cx=x, cy=y, u_tiles=1, vlen=70)
            cylm(X.mesh(cap), (x, y, 212), 15, 12, n=12)
    BOX[name] = [((-W_ / 2 + 4, -W_ / 2 + 4, 0), (W_ / 2 - 4, W_ / 2 - 4, H_ + 60))]
    return save(name, X)


def cake_boxes(name='boxes', n=2, seed=1):
    X = Model()
    rng = np.random.default_rng(seed)
    z = 0.0
    for k in range(n):
        s = 200 - k * 24
        R = rot_z(rng.uniform(-0.25, 0.25))
        m = Mesh(); rbox(m, (-s / 2, -s / 2, 0), (s / 2, s / 2, s * 0.8), r=3, k=1, tile=s)
        X.mesh(SM('box_pink', 50, tag='bx')).add(m, R, (0, 0, z))
        for a in (0, math.pi / 2):
            m2 = Mesh(); rbox(m2, (-s / 2 - 1, -8, -1), (s / 2 + 1, 8, s * 0.8 + 1), r=1, k=1, tile=64)
            X.mesh(SM('ribbon', 60, tag='bx')).add(m2, R @ rot_z(a), (0, 0, z))
        z += s * 0.8
    for k in range(4):
        a = k * math.pi / 2 + 0.6
        ellipsoid(X.mesh(SM('ribbon', 60, tag='bx')), (math.cos(a) * 16, math.sin(a) * 16, z + 8), 18, 8, 8, nu=8, nv=5, R=rot_z(a))
    BOX[name] = [((-88, -88, 0), (88, 88, z - 4))]
    return save(name, X)


def bowl_upside(name='bowl_up', r=170.0, h=120.0):
    """copper mixing bowl turned upside down on the floor"""
    X = Model()
    cu = SC('copper', 0.25, tag='bw')
    revolve(X.mesh(cu), [(r + 10, 0), (r + 10, 8), (r, 14), (r * 0.92, h * 0.55), (r * 0.6, h * 0.92), (0, h)], n=40, u_tiles=6)
    CYL[name] = [(0, 0, r - 10, 0, h * 0.5), (0, 0, r * 0.7, h * 0.5, h - 6)]
    return save(name, X)


def rolling_pin(name='rollpin', L_=360.0, r=30.0):
    X = Model()
    wd = SM('wood', 60, tag='rp')
    m = Mesh(); revolve(m, [(0, -L_ / 2), (r - 2, -L_ / 2), (r, -L_ / 2 + 6), (r, L_ / 2 - 6), (r - 2, L_ / 2), (0, L_ / 2)], n=20, vlen=128)
    X.mesh(wd).add(m, rot_axis((0, 1, 0), math.pi / 2), (0, 0, r))
    for s in (-1, 1):
        m = Mesh(); revolve(m, [(0, 0), (10, 0), (13, 30), (12, 80), (0, 84)], n=12)
        X.mesh(SM('wood_d', 60, tag='rp')).add(m, rot_axis((0, 1, 0), s * math.pi / 2), (s * L_ / 2, 0, r))
    BOX[name] = [((-L_ / 2, -r + 6, 0), (L_ / 2, r - 6, 2 * r - 6))]
    return save(name, X)


def whisk(name='whisk'):
    X = Model()
    ch = SC('steel', 0.3, tag='wk')
    for k in range(6):
        a = k * math.pi / 6
        pts = [(x, math.cos(a) * 34 * math.sin(math.pi * t) * 1.0, 18 + math.sin(a) * 16 * math.sin(math.pi * t))
               for t, x in ((t, 140 * t) for t in np.linspace(0, 1, 12))]
        tube(X.mesh(ch), pts, 1.6, nseg=5)
    tube(X.mesh(SM('wood_d', tag='wk')), [(-120, 0, 12), (0, 0, 16)], [8, 10], nseg=10)
    ground(X)
    return save(name, X)


def piping_bag(name='pipingbag', col='bc_pink'):
    X = Model()
    m = Mesh(); revolve(m, [(0, 0), (8, 6), (30, 60), (44, 150), (36, 172), (0, 180)], n=16, vlen=96)
    X.mesh(S('glass_g', 'glass', tag='pb')).add(m, rot_axis((0, 1, 0), math.pi / 2 * 0.98), (-90, 0, 40))
    m = Mesh(); revolve(m, [(0, 4), (6, 8), (26, 60), (38, 140), (0, 150)], n=12, vlen=96)
    X.mesh(SM(col, 60, tag='pb' + col)).add(m, rot_axis((0, 1, 0), math.pi / 2 * 0.98), (-90, 0, 40))
    m = Mesh(); revolve(m, [(0, -14), (3, -14), (8, 6), (0, 6)], n=10)
    X.mesh(SC('steel', 0.3, tag='pb')).add(m, rot_axis((0, 1, 0), math.pi / 2), (-92, 0, 40))
    return save(name, X)


def jar(name, contents='sprinkles', h=110.0, r=44.0, lid='red'):
    X = Model()
    revolve(X.mesh(SM(contents, 60, tag='jr' + contents)), [(0, 4), (r - 4, 4), (r - 4, h * 0.7), (0, h * 0.72)], n=20, vlen=64)
    revolve(X.mesh(S('glass_g', 'glass', tag='jr')), [(0, 0), (r, 0), (r, h * 0.85), (r * 0.8, h * 0.92)], n=20)
    cylm(X.mesh(SM(lid, 60, tag='jr' + lid)), (0, 0, h * 0.9), r * 0.85, h * 0.1, n=20)
    return save(name, X)


def canister(name, label, col='tin'):
    X = Model()
    revolve(X.mesh(SC(col, 0.2, tag='cn')), [(0, 0), (62, 0), (62, 150), (0, 150)], n=24, vlen=150)
    revolve(X.mesh(SM(label, 60, tag='cn' + label)), [(63, 120), (63, 40)], n=24, a0=200, a1=340, u_tiles=360 / 140, v_of=lambda r, z: (120 - z) / 80)
    cylm(X.mesh(SC('steel', 0.3, tag='cn')), (0, 0, 150), 64, 14, n=24)
    sphere(X.mesh(SM('black', tag='cn')), (0, 0, 170), 10, nu=8, nv=5)
    return save(name, X)


def scale_model(name='scale'):
    X = Model()
    boxm(X.mesh(SM('white', 60, tag='sl')), (-110, -110, 0), (110, 110, 50), r=12, tile=128)
    cylm(X.mesh(SC('steel', 0.3, tag='sl')), (0, 10, 50), 96, 8, n=28)
    picture(X.mesh(S('screen', 'glow', tag='sl')), (0, -110.6, 26), 120, 30, (0, -1, 0))
    BOX[name] = [((-104, -104, 0), (104, 104, 52))]
    return save(name, X)


def cookie_tray(name='cookies'):
    X = Model()
    W_, D_ = 520.0, 360.0
    boxm(X.mesh(SC('tin', 0.15, tag='tr')), (-W_ / 2, -D_ / 2, 0), (W_ / 2, D_ / 2, 6), r=1, tile=256)
    for s in (-1, 1):
        boxm(X.mesh(SC('tin', 0.15, tag='tr')), (-W_ / 2, s * D_ / 2 - (6 if s > 0 else 0), 0), (W_ / 2, s * D_ / 2 + (0 if s > 0 else 6), 14), r=1, tile=64)
        boxm(X.mesh(SC('tin', 0.15, tag='tr')), (s * W_ / 2 - (6 if s > 0 else 0), -D_ / 2, 0), (s * W_ / 2 + (0 if s > 0 else 6), D_ / 2, 14), r=1, tile=64)
    rng = np.random.default_rng(5)
    for i in range(5):
        for j in range(3):
            x, y = -W_ / 2 + 60 + i * 100 + rng.uniform(-8, 8), -D_ / 2 + 70 + j * 110 + rng.uniform(-8, 8)
            ellipsoid(X.mesh(SM('crust', 60, tag='tr')), (x, y, 10), 36, 36, 8, nu=14, nv=5, flat_bottom=-4)
            for k in range(4):
                sphere(X.mesh(SM('choc_d', tag='tr')), (x + rng.uniform(-20, 20), y + rng.uniform(-20, 20), 16), 5, nu=6, nv=4)
    return save(name, X)


def banneton(name='banneton'):
    X = Model()
    revolve(X.mesh(SM('wood', 60, tag='bn2')), [(0, 0), (70, 0), (90, 56), (86, 60), (66, 6), (0, 6)], n=24, u_tiles=8, vlen=24)
    ellipsoid(X.mesh(SM('dough', 70, tag='bn2')), (0, 0, 44), 80, 80, 26, nu=16, nv=6, flat_bottom=-8)
    CYL[name] = [(0, 0, 80, 0, 64)]
    return save(name, X)


def dough_ball(name='dough'):
    X = Model()
    ellipsoid(X.mesh(SM('dough', 70, tag='dg')), (0, 0, 40), 160, 140, 70, nu=24, nv=10, flat_bottom=-40)
    CYL[name] = [(0, 0, 140, 0, 100)]
    return save(name, X)


def turntable_base(name='turntable'):
    X = Model()
    revolve(X.mesh(SC('steel', 0.3, tag='tt')), [(0, 0), (90, 0), (80, 10), (24, 16), (20, 60), (150, 62), (150, 72), (0, 72)], n=36)
    CYL[name] = [(0, 0, 146, 0, 72)]
    return save(name, X)


def turn_cake(name='turncake'):
    """the cake being decorated on the turntable (mover model2, origin at the turntable axis on its plate)"""
    X = Model()
    r, h = 132.0, 110.0
    revolve(X.mesh(S('bc_mint', 'dyn', tag='tc')), [(0, 0), (r, 0), (r, h), (0, h)], n=40, vlen=96)
    for k in range(20):
        a = 2 * math.pi * k / 40 + math.pi
        sphere(X.mesh(S('bc_white', 'dyn', tag='tc')), ((r - 8) * math.cos(a), (r - 8) * math.sin(a), h + 6), 10, nu=8, nv=5)
    for k in range(9):
        a = 2 * math.pi * k / 9
        sphere(X.mesh(S('red', 'dyn', tag='tc')), (r * 0.5 * math.cos(a), r * 0.5 * math.sin(a), h + 10), 9, nu=8, nv=5)
    return save(name, X)


# ================================================================================================= shop + room furniture
def cafe_table(name='cafetable'):
    X = Model()
    ir = SM('black', 50, tag='tb')
    revolve(X.mesh(ir), [(0, 0), (100, 0), (92, 10), (24, 24), (16, 40), (14, 560), (40, 580), (0, 580)], n=28)
    revolve(X.mesh(SM('marble', 40, tag='tb')), [(0, 580), (196, 580), (202, 590), (196, 604), (0, 604)], n=40)
    CYL[name] = [(0, 0, 84, 0, 20), (0, 0, 16, 20, 580), (0, 0, 192, 580, 604)]
    return save(name, X)


def cafe_chair(name='cafechair'):
    X = Model()
    ir = SM('black', 50, tag='ch')
    for (x, y) in ((-90, -90), (90, -90), (-90, 90), (90, 90)):
        tube(X.mesh(ir), [(x * 1.05, y * 1.05, 0), (x * 0.95, y * 0.95, 340)], 8, nseg=8)
    revolve(X.mesh(SM('cushion', 50, tag='ch')), [(0, 340), (124, 340), (130, 352), (122, 366), (0, 366)], n=28)
    for k in range(5):
        a = math.radians(55 + 17.5 * k)
        tube(X.mesh(ir), [(108 * math.cos(a), 108 * math.sin(a), 366), (120 * math.cos(a), 120 * math.sin(a), 640)], 6, nseg=6)
    tube(X.mesh(ir), [(120 * math.cos(math.radians(a_)), 120 * math.sin(math.radians(a_)), 640) for a_ in np.linspace(50, 130, 9)], 9, nseg=8)
    CYL[name] = [(x, y, 11, 0, 340) for (x, y) in ((-88, -88), (88, -88), (-88, 88), (88, 88))] + [(0, 0, 120, 340, 366)]
    return save(name, X)


def register(name='register'):
    X = Model()
    boxm(X.mesh(SM('cab_pink', 40, tag='rg')), (-120, -100, 0), (120, 100, 70), r=8, tile=128)
    P = [np.array(p, float) for p in ((-110, -96, 70), (110, -96, 70), (110, 40, 120), (-110, 40, 120))]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    X.mesh(SM('steel_d', tag='rg')).poly(P, nn, [(0, 0), (1, 0), (1, 1), (0, 1)])
    boxm(X.mesh(SM('cab_pink', 40, tag='rg')), (-120, 40, 70), (120, 100, 130), r=6, tile=128)
    for i in range(4):
        for j in range(3):
            boxm(X.mesh(SM('white', 60, tag='rg')), (-90 + i * 40, -80 + j * 34 + 0, 0), (-66 + i * 40, -60 + j * 34, 6), r=1, tile=16)
    boxm(X.mesh(SM('black', tag='rg')), (-60, 60, 130), (60, 74, 210), r=3, tile=64)
    picture(X.mesh(S('screen', 'glow', tag='rg')), (0, 59.4, 176), 100, 50, (0, -1, 0))
    BOX[name] = [((-116, -96, 0), (116, 96, 128))]
    return save(name, X)


def pendant(name='pendant', drop=380.0):
    """enamel pendant lamp hanging from the ceiling (origin at the ceiling point, model hangs down to -drop)"""
    X = Model()
    tube(X.mesh(SM('black', tag='pl')), [(0, 0, 0), (0, 0, -drop + 60)], 2.5, nseg=6)
    cylm(X.mesh(SM('black', tag='pl')), (0, 0, -16), 30, 16, n=12)
    revolve(X.mesh(SM('cab_pink', 40, tag='pl', two=True)), [(14, -drop + 60), (40, -drop + 40), (90, -drop + 4), (96, -drop)], n=28)
    sphere(X.mesh(S('glow_w', 'glow', tag='pl')), (0, 0, -drop + 20), 22, nu=10, nv=6)
    return save(name, X)


def fan_rod(name='fanrod'):
    X = Model()
    cylm(X.mesh(SM('white', tag='fr')), (0, 0, -16), 48, 16, n=16)
    tube(X.mesh(SM('white', tag='fr')), [(0, 0, -16), (0, 0, -200)], 8, nseg=8)
    return save(name, X)


def fan_blades(name='fanblades'):
    """ceiling fan motor + four wooden blades (mover model2, origin at the motor centre)"""
    X = Model()
    revolve(X.mesh(S('white', 'dyn', tag='fb')), [(0, 30), (40, 28), (56, 0), (40, -24), (0, -30)], n=20)
    for k in range(4):
        a = k * math.pi / 2
        m = Mesh(); rbox(m, (60, -36, -4), (380, 36, 4), r=3, k=1, tile=256)
        X.mesh(S('wood', 'dyn', tag='fb')).add(m, rot_z(a) @ rot_axis((1, 0, 0), 0.18), (0, 0, -8))
    return save(name, X)


def wall_clock(name='clock'):
    """kitchen wall clock, origin on the wall surface, face toward -y"""
    X = Model()
    m = Mesh(); revolve(m, [(0, 0), (104, 0), (108, 14), (100, 22), (0, 22)], n=32)
    X.mesh(SM('red', 50, tag='ck2')).add(m, rot_axis((1, 0, 0), math.pi / 2), (0, 0, 0))
    picture(X.mesh(SM('clock', 50, tag='ck2')), (0, -22.6, 0), 190, 190, (0, -1, 0))
    return save(name, X)


def window(name, w, h):
    """window frame + mullions + sill (origin bottom-centre on the inside wall face, frame toward -y... built facing +y)"""
    X = Model()
    wd = SM('white', 40, tag='wn')
    t = 22.0
    for (mn, mx) in (((-w / 2 - t, 0, -t), (w / 2 + t, 12, 0)), ((-w / 2 - t, 0, h), (w / 2 + t, 12, h + t)),
                     ((-w / 2 - t, 0, 0), (-w / 2, 12, h)), ((w / 2, 0, 0), (w / 2 + t, 12, h))):
        boxm(X.mesh(wd), mn, mx, r=2, tile=128)
    for k in (1, 2):
        x = -w / 2 + w * k / 3
        boxm(X.mesh(wd), (x - 6, 2, 0), (x + 6, 10, h), r=1, tile=64)
    boxm(X.mesh(wd), (-w / 2, 2, h * 0.62 - 6), (w / 2, 10, h * 0.62 + 6), r=1, tile=64)
    boxm(X.mesh(SM('marble', 40, tag='wn')), (-w / 2 - 40, 0, -t - 22), (w / 2 + 40, 60, -t), r=3, tile=128)
    return save(name, X)


def oven_peel(name='peel'):
    X = Model()
    boxm(X.mesh(SM('wood', 60, tag='pe')), (-140, -110, 0), (140, 110, 6), r=2, tile=256)
    tube(X.mesh(SM('wood', 60, tag='pe')), [(140, 0, 4), (640, 0, 6)], 10, nseg=8)
    return save(name, X)


def fruit_crate(name='berrycrate'):
    X = Model()
    W_, D_, H_ = 300.0, 200.0, 90.0
    cr = SM('wood', 60, tag='fc')
    for (mn, mx) in (((-W_ / 2, -D_ / 2, 0), (W_ / 2, D_ / 2, 8)), ((-W_ / 2, -D_ / 2, 0), (W_ / 2, -D_ / 2 + 8, H_)),
                     ((-W_ / 2, D_ / 2 - 8, 0), (W_ / 2, D_ / 2, H_)), ((-W_ / 2, -D_ / 2, 0), (-W_ / 2 + 8, D_ / 2, H_)),
                     ((W_ / 2 - 8, -D_ / 2, 0), (W_ / 2, D_ / 2, H_))):
        rbox(X.mesh(cr), mn, mx, r=1, k=1, tile=128)
    rng = np.random.default_rng(7)
    for k in range(34):
        x, y = rng.uniform(-W_ / 2 + 26, W_ / 2 - 26), rng.uniform(-D_ / 2 + 26, D_ / 2 - 26)
        z = H_ - 22 + rng.uniform(-6, 8)
        revolve(X.mesh(SM('strawberry', tag='fc')), [(0, z), (13, z + 8), (16, z + 18), (0, z + 32)], n=10, vlen=32, cx=x, cy=y)
    BOX[name] = [((-W_ / 2 + 4, -D_ / 2 + 4, 0), (W_ / 2 - 4, D_ / 2 - 4, H_ + 6))]
    return save(name, X)


def bread_basket(name='breadbasket'):
    """wicker basket of baguettes (shop corner)"""
    X = Model()
    revolve(X.mesh(SM('wood', 60, tag='bb')), [(0, 0), (120, 0), (140, 160), (132, 164), (112, 10), (0, 10)], n=28, u_tiles=10, vlen=32)
    rng = np.random.default_rng(3)
    for k in range(7):
        a = 2 * math.pi * k / 7; tilt = 0.25
        d = np.array([math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)])
        base = np.array([math.cos(a) * 60, math.sin(a) * 60, 20])
        m = Mesh(); ellipsoid(m, (0, 0, 0), 26, 22, 260, nu=12, nv=10)
        b1, b2 = frame(d)
        X.mesh(SM('crust', 60, tag='bb')).add(m, np.stack([b1, b2, d], 1), base + d * 240)
    CYL[name] = [(0, 0, 130, 0, 164), (0, 0, 70, 164, 480)]
    return save(name, X)


# ================================================================================================= the Sugar Vault
def choc_fountain(name='fountain'):
    X = Model()
    gd = SC('gold', 0.35, tag='cf')
    revolve(X.mesh(gd), [(0, 0), (200, 0), (190, 30), (60, 50), (40, 120)], n=36)
    for (r, z) in ((180, 120), (120, 260), (70, 380)):
        revolve(X.mesh(gd), [(30, z - 10), (r, z), (r + 8, z + 24), (r - 4, z + 28)], n=36)
        disc(X.mesh(SM('choc', 70, tag='cf')), r - 4, z + 22, n=36)
        revolve(X.mesh(S('fountain', 'flow', speed=-0.9, tag='cf')), [(r + 8, z + 24), (r + 14, z - 30), (r + 16, z - 110)], n=36, u_tiles=8, vlen=128)
    tube(X.mesh(gd), [(0, 0, 100), (0, 0, 440)], 26, nseg=12)
    sphere(X.mesh(SM('choc', 70, tag='cf')), (0, 0, 450), 30, nu=12, nv=7)
    CYL[name] = [(0, 0, 196, 0, 60), (0, 0, 176, 60, 150), (0, 0, 40, 150, 470)]
    return save(name, X)


def gold_cake(name='goldcake'):
    X = Model()
    gd = SC('gold', 0.45, tag='gc')
    for (r, z0, z1) in ((150, 0, 100), (104, 100, 190), (60, 190, 260)):
        revolve(X.mesh(gd), [(0, z0), (r, z0), (r, z1), (0, z1)], n=36)
        bead_n = int(2 * math.pi * r / 16)
        for k in range(bead_n):
            a = 2 * math.pi * k / bead_n
            sphere(X.mesh(SM('pearl', 70, tag='gc')), (r * math.cos(a), r * math.sin(a), z1), 6, nu=6, nv=4)
    sphere(X.mesh(S('glow_y', 'glow', tag='gc')), (0, 0, 290), 26, nu=12, nv=8)
    CYL[name] = [(0, 0, 146, 0, 100), (0, 0, 100, 100, 190), (0, 0, 56, 190, 280)]
    return save(name, X)


def rock_candy(name='rockcandy', seed=3):
    X = Model()
    rng = np.random.default_rng(seed)
    cr = S('candy', 'glow', wave='sin 0.85 0.15 0 0.3', tag='rk' + name)
    for k in range(7):
        a = rng.uniform(0, 2 * math.pi); tilt = rng.uniform(0.0, 0.5) * (0 if k == 0 else 1)
        hh = rng.uniform(90, 200); rr = rng.uniform(14, 26)
        d = np.array([math.sin(tilt) * math.cos(a), math.sin(tilt) * math.sin(a), math.cos(tilt)])
        m = Mesh(); revolve(m, [(0, 0), (rr, 0), (rr, hh * 0.8), (0, hh)], n=6, vlen=64)
        b1, b2 = frame(d)
        cr_ = X.mesh(cr); cr_.add(m, np.stack([b1, b2, d], 1), (math.cos(a) * rng.uniform(0, 30), math.sin(a) * rng.uniform(0, 30), 0))
    CYL[name] = [(0, 0, 40, 0, 150)]
    return save(name, X)


def choc_coins(name='coins'):
    X = Model()
    rng = np.random.default_rng(2)
    gd = SC('gold', 0.4, tag='co')
    for k in range(40):
        a = rng.uniform(0, 6.28); rr = rng.uniform(0, 70) * (1 - k / 60)
        z = k * 1.6
        m = Mesh(); cylm(m, (0, 0, 0), 22, 5, n=14)
        gd_ = X.mesh(gd); gd_.add(m, rot_axis((math.cos(a), math.sin(a), 0), rng.uniform(-0.3, 0.3)), (rr * math.cos(a), rr * math.sin(a), z))
    return save(name, X)


def sack_pile(name='sackpile'):
    """three flour/sugar sacks stacked crosswise"""
    X = Model()
    for k, (tex, a) in enumerate((('sack_flour', 0.0), ('sack_sugar', math.pi / 2), ('sack_flour', 0.15))):
        m = Mesh(); rbox(m, (-280, -170, 0), (280, 170, 110), r=46, k=4, tile=540)
        X.mesh(SM(tex, 50, tag='sk' + tex)).add(m, rot_z(a), (0, 0, k * 104))
    BOX[name] = [((-150, -150, 0), (150, 150, 300))]
    return save(name, X)


def ingredient_bin(name='ingbin', label='lab_sugar'):
    """tall wheeled ingredient bin with a sloped lid and a scoop"""
    X = Model()
    W_, D_, H_ = 300.0, 380.0, 460.0
    pl = SM('white', 40, tag='ib')
    rbox(X.mesh(pl), (-W_ / 2, -D_ / 2, 30), (W_ / 2, D_ / 2, H_), r=18, k=3, tile=256)
    P = [np.array(p, float) for p in ((-W_ / 2 - 6, -D_ / 2 - 6, H_), (W_ / 2 + 6, -D_ / 2 - 6, H_), (W_ / 2 + 6, D_ / 2 + 6, H_ + 40), (-W_ / 2 - 6, D_ / 2 + 6, H_ + 40))]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    X.mesh(S('glass_g', 'glass', tag='ib')).poly(P, nn, [(0, 0), (1, 0), (1, 1), (0, 1)])
    picture(X.mesh(SM(label, 60, tag='ib' + label)), (0, -D_ / 2 - 0.6, 300), 200, 100, (0, -1, 0))
    for (x, y) in ((-W_ / 2 + 30, -D_ / 2 + 30), (W_ / 2 - 30, -D_ / 2 + 30), (-W_ / 2 + 30, D_ / 2 - 30), (W_ / 2 - 30, D_ / 2 - 30)):
        m = Mesh(); cylm(m, (0, 0, -6), 16, 12, n=12)
        X.mesh(SM('rubber_b', tag='ib')).add(m, rot_axis((1, 0, 0), math.pi / 2), (x, y, 16))
    BOX[name] = [((-W_ / 2 + 6, -D_ / 2 + 6, 0), (W_ / 2 - 6, D_ / 2 - 6, H_ + 30))]
    return save(name, X)


def tin_stack(name='tins'):
    """a stack of round cake tins (shelf stock)"""
    X = Model()
    tn = SC('tin', 0.2, tag='ts')
    for k in range(5):
        r = 110 - k * 10
        revolve(X.mesh(tn), [(0, k * 46), (r, k * 46), (r + 4, k * 46 + 44), (r - 2, k * 46 + 44)], n=28)
    CYL[name] = [(0, 0, 100, 0, 230)]
    return save(name, X)


def make():
    for nm, ln, fr, tp in (('cup_pink', 'liner_p', 'bc_pink', 'cherry'), ('cup_choc', 'liner_g', 'bc_choc', 'chips'),
                           ('cup_mint', 'liner_b', 'bc_mint', 'pearls'), ('cup_lemon', 'liner_p', 'bc_lemon', 'berry'),
                           ('cup_blue', 'liner_g', 'bc_blue', 'cherry')):
        cupcake(nm, ln, fr, tp)
    donut('donut_pink', 'bc_pink', 'sprinkles'); donut('donut_choc', 'bc_choc', 'sprinkles_c'); donut('donut_white', 'bc_white', None)
    for nm, col in (('mac_pink', 'bc_pink'), ('mac_mint', 'bc_mint'), ('mac_lemon', 'bc_lemon'), ('mac_lilac', 'bc_lilac'), ('mac_choc', 'bc_choc')):
        macaron(nm, col)
    eclair(); croissant(); loaf(); loaf('loaf_d', 220, 120, 96, 'crust_d', 4); loaf('baguette', 480, 64, 56, 'crust', 6); boule()
    round_cake('cake_berry', 'bc_white', 'bc_white', deco='berries'); round_cake('cake_choc', 'bc_choc', 'bc_choc', deco='drip')
    round_cake('cake_lemon', 'bc_lemon', 'bc_white', 90, 80, deco='lemon'); round_cake('cake_pink', 'bc_pink', 'bc_pink', 84, 96, deco='berries')
    cake_stand_cake(); cupcake_tower()
    flour_sack(); flour_sack('sack_sugar', 'sack_sugar', 560, 360, 110); sugar_bag(); egg_stack(); egg_stack('eggs3', 3); butter(); milk_crate()
    cake_boxes('boxes2', 2, 1); cake_boxes('boxes3', 3, 2); bowl_upside(); rolling_pin(); whisk(); piping_bag(); piping_bag('pipingbag_b', 'bc_blue')
    jar('jar_spr', 'sprinkles'); jar('jar_choc', 'sprinkles_c', lid='black'); jar('jar_jam', 'jam', 90, 38, 'white')
    for nm, lab in (('can_flour', 'lab_flour'), ('can_sugar', 'lab_sugar'), ('can_cocoa', 'lab_cocoa'), ('can_salt', 'lab_salt')):
        T(lab, tex_label(256, 128, lab.split('_')[1].upper(), (250, 246, 236), (196, 40, 90)))
        canister(nm, lab)
    scale_model(); cookie_tray(); banneton(); dough_ball(); turntable_base(); turn_cake()
    cafe_table(); cafe_chair(); register(); pendant(); fan_rod(); fan_blades(); wall_clock(); oven_peel(); fruit_crate(); bread_basket()
    for i, (x0, x1, z0, z1) in enumerate(L.WINDOWS):
        window(f'window{i}', x1 - x0, z1 - z0)
    sack_pile(); ingredient_bin('ingbin', 'lab_sugar'); ingredient_bin('ingbin_f', 'lab_flour'); tin_stack()
    choc_fountain(); gold_cake(); rock_candy('rockcandy', 3); rock_candy('rockcandy_b', 11); choc_coins()
