"""Custom MD3/IQM props and movers for wop_padspace (Starsplash Station). All geometry and art is original.
Props have their origin at the floor centre (the model rests on z 0)."""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, frame
from splib import *
import layout as L
from sp_models import tube, cylm, boxm, torus, cone, quad_uv, picture, SB, BT


def moonrock(name, r=60.0, seed=7):
    X = Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    bump = lambda p, t: 1 + 0.14 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]) + 0.08 * math.sin(5 * t + ph[2]) + 0.05 * math.sin(9 * t + ph[3])
    ellipsoid(X.mesh(SB('lunar_rock', 70, tag='mr')), (0, 0, r * 0.45), r, r * 0.8, r * 0.6, nu=20, nv=10, bump=bump, flat_bottom=-r * 0.45)
    return save(name, X)


def bulbtree(name, h=260.0, n=5, seed=1, col='glow_c', stem='bands_g'):
    """alien tree: a curving ribbed trunk that splits into stalks ending in glowing bulbs (vertex lit leaves)"""
    X = Model()
    rng = np.random.default_rng(seed)
    tr = X.mesh(S(stem, 'lm', shade=70, tag='bt')); bl = X.mesh(S(col, 'glow', wave='sin 0.85 0.15 %.2f 0.4' % rng.uniform(0, 1), tag=name))
    lean = rng.uniform(-0.15, 0.15, 2)
    pts = [np.array([lean[0] * h * (t ** 2), lean[1] * h * (t ** 2), h * 0.6 * t]) for t in np.linspace(0, 1, 8)]
    tube(tr, pts, [16, 13, 11, 10, 9, 9, 8, 8], nseg=10, vlen=96)
    top = pts[-1]
    lf = X.mesh(S('crystal_g', 'vl', tag='bt', two=True))
    for k in range(n):
        a = 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
        d = np.array([math.cos(a), math.sin(a), 0])
        L_ = h * rng.uniform(0.3, 0.45)
        sp = [top + d * L_ * t + np.array([0, 0, h * 0.4 * math.sin(t * 1.4)]) for t in np.linspace(0, 1, 6)]
        tube(tr, sp, [7, 6, 5, 4, 4, 3], nseg=6, vlen=64)
        sphere(bl, sp[-1] + [0, 0, 10], rng.uniform(13, 19), nu=10, nv=6)
        # two drooping leaves along each stalk
        for t0 in (0.35, 0.65):
            p = sp[int(t0 * 5)]
            side = np.array([-d[1], d[0], 0])
            quad_uv(lf, p, p + side * 26 + [0, 0, -8], p + d * 30 + side * 14 - [0, 0, 22], p + d * 18, [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, 1))
    revolve(tr, [(0, 0), (22, 0), (18, 10), (14, 18)], n=10, vlen=64)
    return save(name, X)


def crystal(name, h=110.0, seed=3, col='crystal'):
    """cluster of glowing crystal prisms on a rock base"""
    X = Model()
    rng = np.random.default_rng(seed)
    cr = X.mesh(S(col, 'glow', wave='sin 0.8 0.2 %.2f 0.25' % rng.uniform(0, 1), tag=name))
    ellipsoid(X.mesh(SB('lunar_rock', 70, tag='cr')), (0, 0, 8), 40, 34, 22, nu=12, nv=6, flat_bottom=-8)
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi); tilt = rng.uniform(0.05, 0.5) * (0 if k == 0 else 1)
        hh = h * (1.0 if k == 0 else rng.uniform(0.4, 0.75)); rr = 13 if k == 0 else rng.uniform(6, 10)
        d = np.array([math.sin(tilt) * math.cos(a), math.sin(tilt) * math.sin(a), math.cos(tilt)])
        base = np.array([math.cos(a), math.sin(a), 0]) * (0 if k == 0 else rng.uniform(8, 24)) + [0, 0, 4]
        m = Mesh()
        revolve(m, [(0, 0), (rr, 0), (rr, hh * 0.78), (0, hh)], n=6, vlen=64)
        b1, b2 = frame(d)
        cr.add(m, np.stack([b1, b2, d], 1), base)
    return save(name, X)


def neon_post(name='neon_post', h=170.0, col='glow_c'):
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.25, tag='np')); gl = X.mesh(S(col, 'glow', wave='sin 0.85 0.15 0 0.5', tag=name))
    revolve(mt, [(0, 0), (16, 0), (14, 6), (5, 10)], n=12, vlen=32)
    cylm(mt, (0, 0, 0), 4, h, n=8)
    torus(gl, (0, 0, h + 14), 16, 3, n=20, m=6)
    sphere(X.mesh(S('glow_w', 'glow', tag='np')), (0, 0, h + 14), 8, nu=10, nv=6)
    cylm(gl, (0, 0, h * 0.4), 4.6, 30, n=8)
    return save(name, X)


def parasol(name='parasol', h=150.0, r=96.0, cv='bands_p'):
    X = Model()
    mt = X.mesh(S('metal', 'lm', tag='pa')); th = X.mesh(S(cv, 'lm', shade=60, tag='pa' + name))
    cylm(mt, (0, 0, 0), 3.5, h + 30, n=8)
    revolve(th, [(0, h + 40), (r * 0.5, h + 22), (r, h)], n=16, u_tiles=8, vlen=64)
    revolve(th, [(r, h), (r * 0.5, h + 22), (0, h + 40)], n=16, u_tiles=8, vlen=64)
    sphere(X.mesh(S('glow_y', 'glow', tag='pa')), (0, 0, h + 44), 5, nu=8, nv=4)
    return save(name, X)


def lounger(name='lounger', cv='blue'):
    X = Model()
    wd = X.mesh(S('white', 'lm', tag='lo')); cu = X.mesh(S(cv, 'lm', tag='lo' + name))
    for x in (-30, 30):
        for y in (-12, 12):
            cylm(wd, (x, y, 0), 2, 10, n=6)
    boxm(wd, (-34, -14, 10), (34, 14, 13), r=1, tile=64)
    boxm(cu, (-32, -13, 13), (14, 13, 16), r=1.5, tile=64)
    P = [np.array(p, float) for p in ((14, -13, 14), (14, 13, 14), (34, 13, 34), (34, -13, 34))]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    if nn[2] < 0: nn = -nn
    cu.poly(P, nn, [(0, 0), (0.4, 0), (0.4, 0.3), (0, 0.3)])
    cu.poly(P[::-1], -nn, [(0, 0.3), (0.4, 0.3), (0.4, 0), (0, 0)])
    return save(name, X)


def astronaut(X, base, scale=1.0, R=np.eye(3), suit='white', visor='gold', flag=False, wave=False):
    """a chunky astronaut figure (standing, facing -y), base at `base`, height ~62*scale"""
    def P(v): return R @ (np.array(v, float) * scale) + np.asarray(base, float)
    su = X.mesh(S(suit, 'lm', tag='astro')); vi = X.mesh(S(visor, 'lms', v=0.45, tag='astro')); bk = X.mesh(S('metal', 'lm', tag='astro'))
    Rs = R * scale
    for s in (-1, 1):
        tube(su, [P((s * 7, 0, 0)), P((s * 7, 0, 14)), P((s * 7, 0, 26))], 6.5 * scale, nseg=8)
        ellipsoid(su, P((s * 7, -2, 3)), 7 * scale, 9 * scale, 4 * scale, nu=8, nv=5, R=R)
    ellipsoid(su, P((0, 0, 36)), 15 * scale, 11 * scale, 14 * scale, nu=12, nv=8, R=R)
    boxm_ = Mesh(); rbox(boxm_, (-12, 8, 26), (12, 18, 50), r=3, k=2, tile=32)
    bk.add(boxm_, R, base, scale)
    for s in (-1, 1):
        up = wave and s > 0
        tube(su, [P((s * 15, 0, 46)), P((s * 19, -2, 38 if not up else 54)), P((s * 20, -4, 30 if not up else 64))], 5 * scale, nseg=8)
        sphere(su, P((s * 20, -4, 28 if not up else 66)), 5 * scale, nu=8, nv=5)
    sphere(su, P((0, 0, 58)), 12 * scale, nu=14, nv=9)
    ellipsoid(vi, P((0, -6, 58)), 9 * scale, 7 * scale, 7 * scale, nu=12, nv=7, R=R)
    if flag:
        tube(bk, [P((22, -4, 0)), P((22, -4, 96))], 1.4 * scale, nseg=6)
        fl = X.mesh(S('flag', 'flag', div=40, amp=2, freq=0.8, tag='astro'))
        a, b = P((22, -4, 96)), P((22, -4, 70)); c_, d_ = P((62, -4, 70)), P((62, -4, 96))
        fl.poly([a, b, c_, d_], R @ np.array([0, -1.0, 0]), [(0, 0), (0, 1), (1, 1), (1, 0)])
        fl.poly([d_, c_, b, a], R @ np.array([0, 1.0, 0]), [(1, 0), (1, 1), (0, 1), (0, 0)])


def astro_statue(name='astro_statue'):
    """the golden astronaut planting a flag, on a round plinth with a neon ring (plinth 0..96, figure ~330)"""
    X = Model()
    pl = X.mesh(SB('panel_d', 30, tag='as')); gl = X.mesh(S('glow_c', 'glow', wave='sin 0.85 0.15 0 0.4', tag='as'))
    revolve(pl, [(0, 0), (70, 0), (70, 80), (60, 96), (0, 96)], n=24, vlen=64)
    revolve(gl, [(71, 40), (71, 50)], n=24, vlen=32)
    astronaut(X, (0, 0, 96), 3.6, suit='gold', visor='metal', flag=True)
    return save(name, X)


def flagpole(name='flagpole', h=320.0):
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.3, tag='fp'))
    revolve(mt, [(0, 0), (20, 0), (16, 8), (5, 14)], n=12, vlen=32)
    cylm(mt, (0, 0, 0), 4, h, n=8)
    sphere(X.mesh(S('glow_y', 'glow', tag='fp')), (0, 0, h + 6), 6, nu=8, nv=5)
    fl = X.mesh(S('flag', 'flag', div=60, amp=4, freq=0.6, tag='fp'))
    P = [np.array([4, 0, h - 4]), np.array([4, 0, h - 84]), np.array([132, 0, h - 84]), np.array([132, 0, h - 4])]
    fl.poly(P, (0, -1, 0), [(0, 0), (0, 1), (1, 1), (1, 0)])
    fl.poly(P[::-1], (0, 1, 0), [(1, 0), (1, 1), (0, 1), (0, 0)])
    return save(name, X)


def dish_small(name='dish_small'):
    """ground satellite dish on a tripod (dish ~120 across, tilted toward the sky), footprint r 50"""
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.25, tag='ds')); wh = X.mesh(S('white', 'lm', tag='ds', two=True))
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(mt, [(48 * math.cos(a), 48 * math.sin(a), 0), (0, 0, 100)], 3.5, nseg=6)
    cylm(mt, (0, 0, 90), 8, 30, n=10)
    d = Mesh(); revolve(d, [(0, 0), (24, 2), (44, 9), (60, 20)], n=20, vlen=64)
    revolve(d, [(60, 20), (44, 9), (24, 2), (0, 0)], n=20, vlen=64)
    tube(d, [(0, 0, 0), (0, 0, 46)], 2, nseg=6)
    sphere(d, (0, 0, 48), 5, nu=8, nv=5)
    wh.add(d, rot_axis((1, 0, 0), math.radians(-40)), (0, 0, 124))
    return save(name, X)


def cargo(name='cargo', s=56.0, col='orange'):
    """cargo pod: rounded box, coloured end caps, hazard band and a white stencil strip"""
    X = Model()
    h = s / 2
    boxm(X.mesh(S('panels_g', 'lm', tag='cg')), (-h, -h, 0), (h, h, s), r=6, k=2, tile=64)
    for z in (6, s - 10):
        boxm(X.mesh(S(col, 'lm', tag='cg' + name)), (-h - 1, -h - 1, z), (h + 1, h + 1, z + 4), r=2, k=1, tile=32)
    for sx in (-1, 1):
        picture(X.mesh(S('hazard', 'lm', tag='cg')), (sx * (h + 0.6), 0, s * 0.5), s * 0.6, 10, (sx, 0, 0))
    return save(name, X)


def canister(name='canister', h=58.0, r=22.0, col='blue'):
    X = Model()
    revolve(X.mesh(S('metal', 'lms', v=0.2, tag='cn')), [(0, 0), (r, 0), (r, h), (r - 4, h + 3), (0, h + 3)], n=16, vlen=64)
    for z in (10, h - 14):
        revolve(X.mesh(S(col, 'lm', tag='cn' + name)), [(r + 0.6, z), (r + 0.6, z + 6)], n=16, vlen=32)
    revolve(X.mesh(S('glow_g', 'glow', wave='sin 0.8 0.2 0 1', tag='cn')), [(r + 0.6, h * 0.5 - 3), (r + 0.6, h * 0.5 + 3)], n=16, vlen=32)
    return save(name, X)


def fuel_tank(name='fuel_tank', ln=220.0, r=44.0):
    """horizontal fuel tank on two cradles (along x), footprint ln x 2r, height ~2r + 14"""
    X = Model()
    t = Mesh()
    revolve(t, [(0, -ln / 2 - 20), (r * 0.7, -ln / 2 - 14), (r, -ln / 2), (r, ln / 2), (r * 0.7, ln / 2 + 14), (0, ln / 2 + 20)], n=20, vlen=128)
    X.mesh(S('white', 'lm', tag='ft')).add(t, rot_axis((0, 1, 0), math.pi / 2), (0, 0, r + 14))
    for x in (-ln * 0.3, ln * 0.3):
        boxm(X.mesh(S('metal_d', 'lm', tag='ft')), (x - 10, -r * 0.8, 0), (x + 10, r * 0.8, r * 0.6 + 14), r=1, tile=32)
    tb = Mesh(); revolve(tb, [(r + 0.6, -12), (r + 0.6, 12)], n=20, vlen=32)
    X.mesh(S('red', 'lm', tag='ft')).add(tb, rot_axis((0, 1, 0), math.pi / 2), (0, 0, r + 14))
    return save(name, X)


def rover(name='rover'):
    """moon buggy: six wire wheels, an open chassis, two seats, a dish and a rear rack (facing +x), ~230 x 120 x 110"""
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.25, tag='rv')); ty = X.mesh(S('tire', 'lm', tag='rv')); gd = X.mesh(S('gold', 'lms', v=0.3, tag='rv'))
    for x in (-80, 0, 80):
        for s in (-1, 1):
            w = Mesh(); revolve(w, [(0, -10), (22, -10), (26, -6), (26, 6), (22, 10), (0, 10)], n=16, vlen=64)
            ty.add(w, rot_axis((1, 0, 0), math.pi / 2), (x, s * 56, 26))
    boxm(gd, (-110, -44, 30), (110, 44, 42), r=3, k=2, tile=64)
    boxm(mt, (-100, -30, 42), (-40, 30, 70), r=4, k=2, tile=64)
    for s in (-1, 1):
        boxm(X.mesh(S('blue', 'lm', tag='rv')), (0, s * 22 - 16, 42), (30, s * 22 + 16, 50), r=3, k=2, tile=32)
        boxm(X.mesh(S('blue', 'lm', tag='rv')), (-6, s * 22 - 16, 50), (0, s * 22 + 16, 80), r=2, k=1, tile=32)
        tube(mt, [(70, s * 44, 42), (88, s * 30, 74)], 2.5, nseg=6)
    tube(mt, [(88, -30, 74), (88, 30, 74)], 2.5, nseg=6)
    tube(mt, [(-90, 20, 70), (-90, 20, 150)], 2, nseg=6)
    d = Mesh(); revolve(d, [(0, 0), (16, 2), (26, 8)], n=14, vlen=32); revolve(d, [(26, 8), (16, 2), (0, 0)], n=14, vlen=32)
    X.mesh(S('white', 'lm', tag='rv', two=True)).add(d, rot_axis((0, 1, 0), math.radians(-30)), (-90, 20, 150))
    return save(name, X)


def mini_rocket(name='mini_rocket', h=230.0, body='white', nose='red'):
    """a small rocket on its fins (decor + cover), r ~36 body, fins out to ~70"""
    X = Model()
    r = 36
    revolve(X.mesh(S(body, 'lm', shade=70, tag='mr' + name)), [(0, 12), (r * 0.8, 12), (r, 30), (r, h * 0.6)], n=20, vlen=128)
    revolve(X.mesh(S(nose, 'lm', shade=70, tag='mr' + name)), [(r, h * 0.6), (r * 0.9, h * 0.75), (r * 0.55, h * 0.9), (0, h)], n=20, vlen=128)
    for k in range(3):
        a = 2 * math.pi * k / 3
        d = np.array([math.cos(a), math.sin(a)]); t = np.array([-d[1], d[0]])
        pts = []
        for (rr, z) in ((r - 4, 0), (r + 34, 0), (r + 30, 30), (r - 4, 90)):
            for w in (-3, 3):
                pts.append((d[0] * rr + t[0] * w, d[1] * rr + t[1] * w, z))
        # build the fin as a flat quad pair
        q = [np.array(p) for p in pts]
        fn = X.mesh(S(nose, 'lm', tag='mrf' + name, two=True))
        quad_uv(fn, q[0], q[2], q[4], q[6], [(0, 1), (1, 1), (1, 0.6), (0, 0)], np.array([t[0], t[1], 0]) * -1)
        quad_uv(fn, q[7], q[5], q[3], q[1], [(0, 0), (1, 0.6), (1, 1), (0, 1)], np.array([t[0], t[1], 0]))
    sphere(X.mesh(S('glow_c', 'glow', tag='mr')), (0, -r + 2, h * 0.5), 9, nu=10, nv=6)
    revolve(X.mesh(S('glow_o', 'glow', wave='sin 0.7 0.3 0 2', tag='mr')), [(0, 2), (r * 0.6, 4), (r * 0.7, 12)], n=12, vlen=32)
    return save(name, X)


def table(name='table_s'):
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.3, tag='tb'))
    revolve(mt, [(0, 0), (16, 0), (14, 3), (3, 6)], n=12, vlen=32)
    cylm(mt, (0, 0, 0), 2.5, 34, n=8)
    revolve(X.mesh(S('red', 'lm', tag='tb')), [(0, 33), (28, 33), (29, 36), (0, 36)], n=20, vlen=32)
    return save(name, X)


def stool(name='stool_s'):
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.3, tag='st'))
    revolve(mt, [(0, 0), (11, 0), (9, 3), (2, 5)], n=10, vlen=32)
    cylm(mt, (0, 0, 0), 2, 26, n=6)
    revolve(X.mesh(S('blue', 'lm', tag='st')), [(0, 26), (11, 26), (12, 30), (0, 31)], n=12, vlen=32)
    return save(name, X)


def jukebox(name='jukebox'):
    """space-age jukebox (faces -y), 60 x 34 x 110"""
    X = Model()
    boxm(X.mesh(S('red', 'lm', tag='jb')), (-30, -17, 0), (30, 17, 80), r=4, k=2, tile=64)
    pts = [(30 * math.cos(t), 0, 80 + 30 * math.sin(t)) for t in np.linspace(0, math.pi, 12)]
    tube(X.mesh(S('glow_y', 'glow', wave='sin 0.7 0.3 0 1.3', tag='jb')), pts, 4, nseg=8)
    picture(X.mesh(S('glow_m', 'glow', wave='sin 0.6 0.4 0.5 1.3', tag='jb')), (0, -17.6, 56), 40, 30, (0, -1, 0))
    return save(name, X)


def signpost(name='signpost'):
    """direction signpost with arrows to the planets"""
    X = Model()
    mt = X.mesh(S('metal', 'lms', v=0.25, tag='sp'))
    cylm(mt, (0, 0, 0), 3.5, 160, n=8)
    cols = ['glow_c', 'glow_m', 'glow_y', 'glow_g']
    for k, (z, a) in enumerate(((140, 20), (118, 140), (96, 250), (74, 320))):
        R = rot_z(math.radians(a))
        m = Mesh(); rbox(m, (4, -3, -8), (70, 3, 8), r=1, k=1, tile=32)
        X.mesh(S('panels_d', 'lm', tag='sp')).add(m, R, (0, 0, z))
        q = Mesh(); rbox(q, (70, -3.5, -8), (84, 3.5, 8), r=1, k=1, tile=32)
        X.mesh(S(cols[k], 'glow', tag='sp')).add(q, R, (0, 0, z))
    return save(name, X)


def life_ring(name='life_ring'):
    X = Model()
    torus(X.mesh(S('orange', 'lm', tag='lr')), (0, 0, 30), 18, 5, axis=(0, 1, 0), n=20, m=8)
    cylm(X.mesh(S('metal', 'lm', tag='lr')), (0, 4, 0), 3, 50, n=6)
    return save(name, X)


def grey_alien(name='grey_alien', R=np.eye(3)):
    """a friendly little grey (~70 tall) on a base"""
    X = Model()
    sk = X.mesh(S('bands_g', 'lm', tag='ga')); ey = X.mesh(S('black', 'lms', v=0.4, tag='ga'))
    for s in (-1, 1):
        tube(sk, [(s * 5, 0, 0), (s * 5, 0, 24)], 3, nseg=6)
        tube(sk, [(s * 9, 0, 38), (s * 14, -4, 24), (s * 15, -6, 14)], 2.4, nseg=6)
    ellipsoid(sk, (0, 0, 32), 9, 7, 12, nu=10, nv=6)
    ellipsoid(sk, (0, 0, 58), 15, 13, 17, nu=14, nv=8)
    for s in (-1, 1):
        ellipsoid(ey, (s * 6, -11, 58), 5, 3, 7, nu=8, nv=5, R=rot_z(math.radians(s * 20)))
    return save(name, X)


def orb(name='orb'):
    """glowing planet orb on a plinth (vault centrepiece): plinth 0..60, orb r 50"""
    X = Model()
    revolve(X.mesh(SB('panel_d', 30, tag='ob')), [(0, 0), (60, 0), (50, 20), (34, 60), (0, 60)], n=20, vlen=64)
    sphere(X.mesh(S('bands_p', 'glow', wave='sin 0.85 0.15 0 0.2', tag='ob')), (0, 0, 112), 50, nu=24, nv=14)
    torus(X.mesh(S('glow_y', 'glow', tag='ob')), (0, 0, 112), 74, 3, axis=(0.2, 0.1, 1), n=32, m=6)
    return save(name, X)


def trophy_heap(name='trophy_heap', r=80.0, seed=13):
    """a heap of glowing star crystals and golden ducks (vault loot), flat-ish mound r, height ~0.45 r"""
    X = Model()
    rng = np.random.default_rng(seed)
    ellipsoid(X.mesh(S('gold', 'lms', v=0.35, tag='th')), (0, 0, 0), r, r, r * 0.45, nu=18, nv=8, flat_bottom=0,
              bump=lambda p, t: 1 + 0.06 * math.sin(7 * t + p * 3))
    gl = X.mesh(S('crystal_c', 'glow', wave='sin 0.8 0.2 0.3 0.4', tag='th'))
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, r * 0.6)
        z = r * 0.45 * math.sqrt(max(0.0, 1 - (rr / r) ** 2)) - 6
        m = Mesh(); revolve(m, [(0, 0), (8, 0), (8, 24), (0, 34)], n=6, vlen=32)
        gl.add(m, rot_axis((math.cos(a), math.sin(a), 0), rng.uniform(-0.4, 0.4)), (rr * math.cos(a), rr * math.sin(a), z))
    return save(name, X)


# ================================================================================================= movers (IQM)
def comet_ring():
    """comets and tumbling asteroids orbiting high over the park (radius COMET_R round the func_rotating origin)"""
    X = Model()
    rk = S('rock_m', 'dyn', tag='cm'); cm = S('comet', 'add', tag='cmt'); hd = S('glow_c', 'dynglow', tag='cmh')
    rng = np.random.default_rng(21)
    for k in range(9):
        a = 2 * math.pi * k / 9 + rng.uniform(-0.1, 0.1)
        R = L.COMET_R + rng.uniform(-300, 300)
        c = np.array([R * math.cos(a), R * math.sin(a), rng.uniform(-200, 300)])
        d = np.array([-math.sin(a), math.cos(a), 0])
        if k % 3 == 0:
            sphere(X.mesh(hd), c, 18, nu=10, nv=6)
            side = np.cross(d, [0, 0, 1.0])
            for (ax, sg) in ((side, 1), ((0, 0, 1.0), 1)):
                ax = np.asarray(ax, float)
                quad_uv(X.mesh(cm), c - ax * 26, c + ax * 26, c + ax * 10 - d * 420, c - ax * 10 - d * 420, [(0, 0), (1, 0), (1, 1), (0, 1)])
        else:
            ph = rng.uniform(0, 6.28, 3)
            ellipsoid(X.mesh(rk), c, rng.uniform(30, 60), rng.uniform(24, 44), rng.uniform(20, 36), nu=10, nv=6,
                      R=rot_axis(rng.normal(size=3), rng.uniform(0, 3)),
                      bump=lambda p, t, ph=ph: 1 + 0.2 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]))
    # a little flying saucer in the same orbit
    a = 0.5
    c = np.array([L.COMET_R * math.cos(a), L.COMET_R * math.sin(a), 120])
    ellipsoid(X.mesh(S('metal', 'dyn', tag='ufo')), c, 90, 90, 18, nu=20, nv=8)
    ellipsoid(X.mesh(S('glow_g', 'dynglow', tag='ufo')), c + [0, 0, 16], 36, 36, 22, nu=14, nv=6)
    for k in range(8):
        t = 2 * math.pi * k / 8
        sphere(X.mesh(S('glow_y', 'dynglow', tag='ufo')), c + [80 * math.cos(t), 80 * math.sin(t), -4], 6, nu=6, nv=4)
    return save_iqm('comets', X)


def moonlets():
    """Padurn's three moonlets on its orbit (radius MOON_R round the planet's axis)"""
    X = Model()
    for k, (tex, r) in enumerate((('rock_m', 30), ('ice', 22), ('bands_g', 26))):
        a = 2 * math.pi * k / 3
        R_ = L.MOON_R + k * 26
        sphere(X.mesh(S(tex, 'dyn', tag='ml')), (R_ * math.cos(a), R_ * math.sin(a), (k - 1) * 30), r, nu=14, nv=9)
    return save_iqm('moonlets', X)


def radar_dish(name='radar', r=46.0):
    """rotating dish (model2 on func_rotating, origin = the axis foot); also used on the satellite tower"""
    X = Model()
    mt = S('metal', 'dyn', tag='rd'); wh = S('white', 'dyn', tag='rd', two=True)
    tube(X.mesh(mt), [(0, 0, 0), (0, 0, 40)], 4, nseg=8)
    d = Mesh(); revolve(d, [(0, 0), (r * 0.4, 2), (r * 0.75, 8), (r, 18)], n=20, vlen=64); revolve(d, [(r, 18), (r * 0.75, 8), (r * 0.4, 2), (0, 0)], n=20, vlen=64)
    tube(d, [(0, 0, 0), (0, 0, r * 0.8)], 2, nseg=6)
    X.mesh(wh).add(d, rot_axis((1, 0, 0), math.radians(-55)), (0, 0, 44))
    sphere(X.mesh(S('glow_r', 'dynglow', tag='rd')), (0, 0, 40), 4, nu=6, nv=4)
    return save_iqm(name, X)


def make():
    moonrock('moonrock_a', 60, 7); moonrock('moonrock_b', 90, 8); moonrock('moonrock_c', 130, 9)
    bulbtree('bulbtree_a', 260, 5, 1, 'glow_c'); bulbtree('bulbtree_b', 330, 6, 2, 'glow_m', 'bands_p'); bulbtree('bulbtree_c', 220, 4, 3, 'glow_y')
    crystal('crystal_a', 110, 3, 'crystal'); crystal('crystal_b', 80, 4, 'crystal_c'); crystal('crystal_big', 220, 5, 'crystal')
    neon_post('neon_post', col='glow_c'); neon_post('neon_post_m', col='glow_m')
    parasol('parasol_p', cv='bands_p'); parasol('parasol_g', cv='bands_g'); lounger('lounger_b', 'blue'); lounger('lounger_o', 'orange')
    astro_statue(); flagpole(); dish_small(); cargo('cargo', 56, 'orange'); cargo('cargo_big', 84, 'blue'); canister('canister', col='blue')
    canister('canister_r', col='red'); fuel_tank(); rover(); mini_rocket('mini_rocket'); mini_rocket('mini_rocket_b', 190, 'yellow', 'blue')
    table(); stool(); jukebox(); signpost(); life_ring(); grey_alien(); orb(); trophy_heap('trophy_heap', 80, 13); trophy_heap('trophy_heap_s', 50, 14)
    comet_ring(); moonlets(); radar_dish('radar')
