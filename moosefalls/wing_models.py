"""Custom MD3s for the Moose Mountain Falls Deluxe wing (Frost Deck + Thunder Bay hall). Original geometry and art.

Uses the registry/mesh helpers of moose_models (S(), Model, _save, sweep ...), so the shaders end up in the same
moosefalls.shader. Call make(out) after moose_models.make(out).

  rafter_b / ridge_b      glulam rafter + ridge beam for the second hall (its own pitch)
  blackhole               closed tube slide: dark violet shell, glowing rings inside, flanges, supports
  bowl                    the Tornado Bowl: a giant open cone you spiral round and drop through
  flywheel                wave-machine flywheel (func_rotating model2, axis x)
  vent / pipes / beacon   wave-machine facade detail
  igloo                   snow-block igloo with an entrance tunnel (hollow; the fishing hole inside is the secret)
  snow_pine               potted-size pine with snow on the boughs
  firepit                 stone ring, logs, crossed-quad flames
  lamppost                old-style lantern post for the deck
  snowball_pile           ammo for the snow forts
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame
import moose_models as MM
from moose_models import S, Model, _save, sweep, circle_prof, densify, box_mesh, beam

MD = MM.MD


def _tx():
    import moose_textures as TX
    return TX


# ================================================================================================= textures
def tex_needles_snow(w=256, h=256, seed=7):
    a, al = MM.tex_needles(w, h, seed)
    TX = _tx()
    snow = (TX.noise(w, 3, seed + 5, h) > 0.35) & (al > 0)
    a = a.copy(); a[snow] = (236, 242, 248)
    return a, al


def tex_blackhole(w=256, h=256, seed=11):
    TX = _tx()
    a = TX.fill(w, (36, 18, 64), 4, seed, h)
    r = np.random.default_rng(seed); im = TX.img(a); d = ImageDraw.Draw(im)
    for _ in range(120):
        x, y = r.integers(0, w, 2); s = r.integers(1, 3)
        c = [(255, 255, 255), (160, 200, 255), (255, 170, 240)][int(r.integers(0, 3))]
        d.ellipse((x - s, y - s, x + s, y + s), fill=c)
    return TX.arr(im)


def tex_bowl(w=512, h=256, seed=13):
    """bowl inside: u = round the bowl, v = radius; teal with yellow spiral bands"""
    TX = _tx()
    x, y = TX.tile_xy(w, h)
    band = np.sin((x * 6 + y * 1.5) * 2 * math.pi) > 0.3
    a = np.where(band[..., None], TX.C((250, 200, 40)), TX.C((30, 170, 190))) + TX.N3(w, 1, seed, 4, h)
    return a


def tex_metal_wheel(n=128, seed=17):
    TX = _tx()
    x, y = TX.tile_xy(n)
    return TX.fill(n, (60, 70, 84), 4, seed) + (np.sin(x * 2 * math.pi * 16) * 6)[..., None]


def tex_vent(w=256, h=128, seed=19):
    TX = _tx()
    a = TX.fill(w, (54, 60, 66), 3, seed, h)
    for k in range(0, h, 16):
        a[k:k + 6] = (24, 26, 30)
    a[:, :6] = (90, 96, 104); a[:, -6:] = (90, 96, 104); a[:6] = (90, 96, 104); a[-6:] = (90, 96, 104)
    return a


def tex_snowblock(w=256, h=128, seed=23):
    TX = _tx()
    a = TX.fill(w, (232, 240, 248), 5, seed, h)
    for k in range(0, h, 32):
        a[k:k + 2] = (196, 210, 226)
        off = 32 if (k // 32) % 2 else 0
        for j in range(off, w, 64):
            a[k:k + 32, j:j + 2] = (196, 210, 226)
    return a


def tex_flame(w=64, h=128, seed=29):
    TX = _tx()
    x, y = TX.tile_xy(w, h)
    m = np.clip(1 - np.abs(x - 0.5) * (2.6 - 1.8 * y), 0, 1) * np.clip(y * 1.4, 0, 1)
    m = m * np.clip(0.6 + 0.5 * TX.noise(w, 3, seed, h), 0, 1)
    c = TX.lerp(TX.C((255, 230, 120)), TX.C((255, 80, 20)), (1 - y)[..., None])
    return c * m[..., None]


def tex_ice(n=256, seed=31):
    TX = _tx()
    a = TX.fill(n, (196, 226, 244), 5, seed)
    cr = np.abs(TX.noise(n, 4, seed + 1)) < 0.04
    a[cr] = (240, 250, 255)
    return a


# ================================================================================================= hall timbers
def rafter_b(hy, eave, ridge):
    X = Model()
    gl = S('glulam', 'lm', tag='r')
    D = 72
    th = math.atan((ridge - eave) / hy)
    off = D / 2 / math.cos(th) + 1.5
    for sg in (-1, 1):
        beam(X.mesh(gl), (0, sg * hy, eave - off), (0, 0, ridge - off), 40, D)
    box_mesh(X.mesh(S('metal_dark', 'lm', tag='rp')), (-22, -40, ridge - D - 8), (22, 40, ridge - D + 30))
    return _save('rafter_b', X)


def ridge_b(hx, ridge):
    X = Model()
    beam(X.mesh(S('glulam', 'lm', tag='rb')), (-hx, 0, ridge - 40), (hx, 0, ridge - 40), 48, 80)
    return _save('ridge_b', X)


# ================================================================================================= slides
BH_ZC, BH_R = 44, 62


def blackhole(path, sup, origin):
    """closed tube in world coords, stored relative to `origin` (x, y) so the MD3 needs less scaling"""
    X = Model()
    sh = S('blackhole', 'lms', v=0.25); sin_ = S('blackhole', 'lm2s', tag='in'); fl = S('metal_dark', 'lms', v=0.2, tag='bhf')
    gl = S('bh_glow', 'glow', light=0, rgb='0.6 0.4 1'); met = S('metal_white', 'lms', v=0.15, tag='bhm')
    o = np.array([origin[0], origin[1], 0.0])
    P = [np.asarray(p, float) - o for p in densify(path[1:], 40)]
    C3 = [np.array([p[0], p[1], p[2] + BH_ZC]) for p in P]
    sweep(X.mesh(sh), C3, circle_prof(BH_R, 20), closed=True, vlen=256)
    sweep(X.mesh(sin_), C3, circle_prof(BH_R - 4, 20), closed=True, vlen=256, inward=True)
    for i in range(0, len(C3) - 1, 3):
        c = C3[i]; d = C3[min(i + 1, len(C3) - 1)] - C3[max(i - 1, 0)]
        d /= np.linalg.norm(d)
        b1, b2 = frame(d)
        ring = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * (BH_R - 6) for t in np.linspace(0, 2 * math.pi, 21)]
        tube(X.mesh(gl), ring, 2.5, nseg=5, caps=(False, False), vlen=32)
        if i % 6 == 0:
            ring = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * (BH_R + 3) for t in np.linspace(0, 2 * math.pi, 25)]
            tube(X.mesh(fl), ring, 5, nseg=6, caps=(False, False), vlen=64)
    strip = [np.array([p[0], p[1], p[2] + 1.5]) for p in P]
    sweep(X.mesh(S('slide_water', 'addw')), strip, [(-36, 0), (36, 0)], vlen=200)
    for (x, y, z) in sup:
        x, y = x - o[0], y - o[1]
        zt = z + BH_ZC - BH_R + 4
        box_mesh(X.mesh(met), (x - 7, y - 7, 0), (x + 7, y + 7, zt), tile=64)
        box_mesh(X.mesh(met), (x - 30, y - 6, zt - 10), (x + 30, y + 6, zt), tile=64)
    return _save('blackhole', X)


def bowl(r_hole, r_rim, z_hole, z_rim, posts, entry_deg):
    """the Tornado Bowl (origin = bowl axis on the floor z 0): open cone, rolled rim with a gap at entry_deg, stilts"""
    X = Model()
    sh = S('bowl', 'lms', v=0.25); out = S('slide_teal', 'lm', tag='bo'); met = S('metal_white', 'lms', v=0.15, tag='bw')
    # inner surface 1u above the collision tops
    prof = [(r_hole, z_hole + 1), (r_rim, z_rim + 1)]
    rows = [(r_hole + (r_rim - r_hole) * t, z_hole + 1 + (z_rim - z_hole) * t) for t in np.linspace(0, 1, 9)]
    revolve(X.mesh(sh), rows, u_tiles=4, n=48, inward=True, v_of=lambda r, z: (r - r_hole) / (r_rim - r_hole))
    # underside (16 below) + hole lip + outer rim roll
    rows_o = [(r_hole, z_hole - 15), (r_rim + 20, z_rim - 15 + 20 * (z_rim - z_hole) / (r_rim - r_hole))]
    revolve(X.mesh(out), rows_o, u_tiles=8, n=48)
    revolve(X.mesh(out), [(r_hole, z_hole + 1), (r_hole - 2, z_hole - 7), (r_hole, z_hole - 15)], n=48, u_tiles=8, inward=True)
    # rim: a tube round the edge except at the entry gap (angles in degrees)
    g0, g1 = entry_deg - 30, entry_deg + 30
    angs = [a for a in np.linspace(g1, g0 + 360, 70)]
    ring = [(math.cos(math.radians(a)) * (r_rim + 10), math.sin(math.radians(a)) * (r_rim + 10), z_rim + 24) for a in angs]
    tube(X.mesh(out), ring, 22, nseg=10, vlen=128)
    for (px, py, ztop) in posts:
        box_mesh(X.mesh(met), (px - 9, py - 9, -176), (px + 9, py + 9, ztop))
    return _save('bowl', X)


# ================================================================================================= wave machine
def flywheel():
    """r 110 spoked flywheel turning about the x axis (model2 of a func_rotating, spawnflags 4)"""
    X = Model()
    mt = S('wheel_metal', 'lms', v=0.25); rd = S('rescue_red', 'lm', tag='fw')
    rim = [(0, 104 * math.cos(t), 104 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 33)]
    tube(X.mesh(mt), rim, 10, nseg=10, caps=(False, False), vlen=128, ry=6)
    for k in range(6):
        t = k * math.pi / 3
        beam(X.mesh(mt), (0, 14 * math.cos(t), 14 * math.sin(t)), (0, 98 * math.cos(t), 98 * math.sin(t)), 8, 12)
    revolve(X.mesh(rd), [(0, -12), (20, -12), (20, 12), (0, 12)], n=16)  # hub along z: rotate below
    m = X.mesh(rd)
    R = rot_axis((0, 1, 0), math.pi / 2)
    m.V = [R @ v for v in m.V]; m.N = [R @ n for n in m.N]
    return _save('flywheel', X)


def vent():
    """big wave-machine vent: dark slatted panel in a riveted frame, 192 wide x 128 tall, faces +x (origin = back centre)"""
    X = Model()
    v = S('vent', 'lm'); fr = S('steel', 'lms', v=0.15, tag='vent')
    X.mesh(v).quad((2, 96, 0), (2, -96, 0), (2, -96, 128), (2, 96, 128), tile=192, n=(1, 0, 0))
    for (a, b) in (((0, -100, -6), (14, 100, 4)), ((0, -100, 124), (14, 100, 134)), ((0, -104, -6), (14, -94, 134)), ((0, 94, -6), (14, 104, 134))):
        box_mesh(X.mesh(fr), a, b)
    for k in range(5):
        y = -80 + k * 40
        tube(X.mesh(fr), [(16, y, 0), (16, y, 128)], 2.5, nseg=6)
    return _save('vent', X)


def beacon():
    X = Model()
    dk = S('metal_dark', 'lm', tag='bc'); gl = S('beacon', 'glow', light=0)
    box_mesh(X.mesh(dk), (0, -14, -14), (8, 14, 14))
    revolve(X.mesh(gl), [(0, 0), (12, 0), (12, 18), (8, 26), (0, 28)], n=12, cx=0, cy=0)
    m = X.mesh(gl)
    R = rot_axis((0, 1, 0), math.pi / 2)
    m.V = [R @ v + np.array([8, 0, 0]) for v in m.V]; m.N = [R @ n for n in m.N]
    return _save('beacon', X)


def pipes(length):
    """two fat pipes along y on a wall (origin = wall foot, pipes at x 0..60), with flanges"""
    X = Model()
    p = S('pipe_teal', 'lms', v=0.2); fl = S('steel', 'lms', v=0.15, tag='pf')
    for (x, z, r) in ((24, 180, 18), (24, 236, 12)):
        tube(X.mesh(p), [(x, -length / 2, z), (x, length / 2, z)], r, nseg=12, vlen=128)
        for y in np.arange(-length / 2 + 64, length / 2, 256):
            tube(X.mesh(fl), [(x, y - 4, z), (x, y + 4, z)], r + 4, nseg=12)
        for y in np.arange(-length / 2 + 128, length / 2, 512):
            box_mesh(X.mesh(fl), (0, y - 6, z - 4), (x, y + 6, z + 4))
    return _save(f'pipes{int(length)}', X)


# ================================================================================================= Frost Deck
def igloo(R=196, H=168, tunnel=96):
    """snow-block igloo, door tunnel along +x (origin = centre on the ground)"""
    X = Model()
    sb = S('snowblock', 'lm'); si = S('snowblock', 'lm', tag='in')
    rows = [(R * math.cos(t), H * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)]
    rows[-1] = (0.5, H)
    import padshroom_compat as PC
    PC.revolve_grid(X.mesh(sb), rows, 48, holes=[(344, 360, 0, 80), (0, 16, 0, 80)], u_tiles=6, v_of=lambda r, z: z / 64)
    inner = [((R - 14) * math.cos(t), (H - 14) * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)]
    inner[-1] = (0.5, H - 14)
    PC.revolve_grid(X.mesh(si), inner, 48, holes=[(344, 360, 0, 80), (0, 16, 0, 80)], u_tiles=6, v_of=lambda r, z: z / 64, inward=True)
    # tunnel: half-elliptic vault from inside the dome wall out to R + tunnel, outer + inner shells
    x0, x1 = R * math.cos(math.radians(16)) - 30, R + tunnel
    for M_, (ry, rz), inw in ((sb, (46, 80), False), (si, (36, 70), True)):
        ts = np.linspace(0, math.pi, 11)
        P = np.zeros((2, len(ts), 3)); UV = np.zeros((2, len(ts), 2))
        for i, x in enumerate((x0, x1)):
            for j, t in enumerate(ts):
                P[i, j] = (x, ry * math.cos(t), rz * math.sin(t)); UV[i, j] = (x / 64, j / 3)
        N = np.zeros_like(P)
        for j, t in enumerate(ts):
            n = np.array([0, math.cos(t) / ry, math.sin(t) / rz]); n /= np.linalg.norm(n)
            N[:, j] = -n if inw else n
        X.mesh(M_).grid(P, N, UV)
    # face ring at the tunnel mouth
    ts = np.linspace(0, math.pi, 11)
    for j in range(10):
        t0, t1 = ts[j], ts[j + 1]
        q = [(x1, 46 * math.cos(t0), 80 * math.sin(t0)), (x1, 46 * math.cos(t1), 80 * math.sin(t1)),
             (x1, 36 * math.cos(t1), 70 * math.sin(t1)), (x1, 36 * math.cos(t0), 70 * math.sin(t0))]
        X.mesh(sb).poly(q, (1, 0, 0), [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)])
    return _save('igloo', X)


def snow_pine():
    """small pine with snow-tipped needles (same build as moose_models.small_pine)"""
    X = Model()
    bk = S('pine_bark', 'lm', tag='sp'); nd = S('needles_snow', 'leaf')
    rng = np.random.default_rng(29)
    revolve(X.mesh(bk), [(16, 0), (13, 40), (9, 200), (3, 300), (0.5, 310)], n=12, u_tiles=2, vlen=128)
    N = X.mesh(nd)
    for k in range(9):
        z = 70 + k * 27
        R = 120 * (1 - k / 9) + 22
        nb = 7 if k < 6 else 5
        for j in range(nb):
            a = (j + rng.uniform(-0.2, 0.2)) * 2 * math.pi / nb + k * 0.7
            d = np.array([math.cos(a), math.sin(a), -0.25]); dn = d / np.linalg.norm(d)
            c = np.array([R * 0.55 * math.cos(a), R * 0.55 * math.sin(a), z])
            s_ = R * 0.95
            b1, b2 = frame(dn)
            for q in range(2):
                ang = q * math.pi / 2 + rng.uniform(0, 0.4)
                w = b1 * math.cos(ang) + b2 * math.sin(ang)
                quad = [c - dn * s_ * 0.6 - w * s_ * 0.4, c + dn * s_ * 0.6 - w * s_ * 0.4, c + dn * s_ * 0.6 + w * s_ * 0.4, c - dn * s_ * 0.6 + w * s_ * 0.4]
                N.poly(quad, np.cross(dn, w), [(0, 1), (0, 0), (1, 0), (1, 1)])
    return _save('snow_pine', X)


def firepit():
    """stone ring r 64, logs, crossed-quad flames (origin = centre on the ground)"""
    X = Model()
    st = S('rockface', 'lm', tag='fp'); lg = S('log_side', 'lm', tag='fp'); fl = S('flame', 'flame')
    for k in range(12):
        a = k * math.pi / 6
        ellipsoid(X.mesh(st), (64 * math.cos(a), 64 * math.sin(a), 0), 20, 16, 20, nu=8, nv=6, flat_bottom=0, R=rot_z(a))
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        tube(X.mesh(lg), [(-36 * math.cos(a), -36 * math.sin(a), 6), (36 * math.cos(a), 36 * math.sin(a), 22)], 7, nseg=8)
    for k in range(3):
        a = k * math.pi / 3
        dx, dy = math.cos(a) * 30, math.sin(a) * 30
        X.mesh(fl).poly([(-dx, -dy, 10), (dx, dy, 10), (dx, dy, 90), (-dx, -dy, 90)], (-math.sin(a), math.cos(a), 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return _save('firepit', X)


def lamppost():
    X = Model()
    dk = S('metal_dark', 'lm', tag='lp'); gp = S('lantern_glow', 'glow', light=0, tag='lp')
    revolve(X.mesh(dk), [(14, 0), (10, 8), (4, 14), (4, 150), (6, 154)], n=10)
    for sg in (-1, 1):
        beam(X.mesh(dk), (0, 0, 140), (sg * 26, 0, 146), 3, 3)
        x = sg * 30
        box_mesh(X.mesh(dk), (x - 9, -9, 116), (x + 9, 9, 120))
        box_mesh(X.mesh(gp), (x - 7, -7, 120), (x + 7, 7, 140), faces='nsew')
        revolve(X.mesh(dk), [(0, 152), (11, 140), (0, 140)], n=8, cx=x, cy=0)
    return _save('lamppost', X)


def snowball_pile():
    X = Model()
    sn = S('snowblock', 'lm', tag='sb')
    for (x, y, z) in ((0, 0, 9), (16, 4, 9), (-14, 8, 9), (4, 16, 9), (6, 6, 24), (-6, 12, 24), (2, 10, 37)):
        sphere(X.mesh(sn), (x, y, z), 9, nu=8, nv=6)
    return _save('snowballs', X)


# ================================================================================================= rocks + ice
def seastack(name, r, h, seed, ice=False):
    """sea stack: lumpy boulders piled from z 0 to h, radius about r at the base (origin = base centre)"""
    X = Model()
    rk = S('ice', 'lms', v=0.35, tag='st') if ice else S('rockface', 'lm', tag='st')
    rng = np.random.default_rng(seed)
    z = 0.0
    while z < h - 8:
        f = 1 - 0.45 * z / h
        rr = r * f * rng.uniform(0.95, 1.1)
        hh = min(rng.uniform(0.35, 0.55) * r, h - z + 10)
        ph = rng.uniform(0, 6)
        ox, oy = rng.uniform(-0.12, 0.12) * r, rng.uniform(-0.12, 0.12) * r
        ellipsoid(X.mesh(rk), (ox, oy, z + hh * 0.5), rr * 1.08, rr * rng.uniform(0.9, 1.05), hh * 0.75, nu=16, nv=8,
                  bump=lambda p, t, ph=ph: 1 + 0.1 * math.sin(3 * t + ph) * math.cos(2 * p) + 0.06 * math.sin(7 * t + 2 * p))
        z += hh * 0.72
    return _save(name, X)


def icicles(n=14, seed=5):
    """cluster of icicles hanging from a ceiling (origin = ceiling point, they hang down)"""
    X = Model()
    ic = S('ice', 'lms', v=0.35, tag='ic')
    rng = np.random.default_rng(seed)
    for k in range(n):
        x, y = rng.uniform(-90, 90), rng.uniform(-90, 90)
        L_ = rng.uniform(30, 110); r0 = rng.uniform(6, 14)
        revolve(X.mesh(ic), [(0.5, -L_), (r0 * 0.4, -L_ * 0.6), (r0, -4), (r0 + 2, 0)], n=8, cx=x, cy=y)
    return _save(f'icicles{seed}', X)


def crystals(seed=9):
    """ice-crystal cluster: hexagonal prisms with points (origin = base centre on the floor)"""
    X = Model()
    cr = S('ice', 'lms', v=0.35, tag='cr')
    rng = np.random.default_rng(seed)
    for k in range(7):
        tilt = rng.uniform(0, 0.5) if k else 0.05; az = rng.uniform(0, 2 * math.pi)
        d = np.array([math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)])
        b1, b2 = frame(d)
        base = np.array([rng.uniform(-30, 30), rng.uniform(-30, 30), -6.0]) if k else np.array([0, 0, -6.0])
        L_ = rng.uniform(60, 140) if k else 170; rr = rng.uniform(10, 20) if k else 24
        ring0 = [base + rr * (math.cos(t) * b1 + math.sin(t) * b2) for t in np.linspace(0, 2 * math.pi, 7)[:-1]]
        ring1 = [p + d * L_ for p in ring0]
        tip = base + d * (L_ + rr * 1.5)
        M = X.mesh(cr)
        for i in range(6):
            q = [ring0[i], ring0[(i + 1) % 6], ring1[(i + 1) % 6], ring1[i]]
            nn = (q[0] + q[1]) / 2 - base; nn -= d * (nn @ d); M.poly(q, nn, [(0, 1), (0.3, 1), (0.3, 0), (0, 0)])
            t3 = [ring1[i], ring1[(i + 1) % 6], tip]
            n2 = np.cross(t3[1] - t3[0], t3[2] - t3[0]); c0 = sum(t3) / 3
            if n2 @ (c0 - (base + d * L_)) < 0: n2 = -n2
            M.poly(t3, n2, [(0, 0.2), (0.3, 0.2), (0.15, 0)])
    return _save(f'crystals{seed}', X)


# ================================================================================================= make
def make(out):
    TX = _tx()
    d = os.path.join(out, MD)
    def sv(nm, a, alpha=None):
        im = TX.img(a)
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(d, nm + '.tga'))
        else:
            im.convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    a, al = tex_needles_snow(); sv('needles_snow', a, al)
    sv('blackhole', tex_blackhole()); sv('bh_glow', TX.fill(32, (190, 120, 255), 2, 41)); sv('bowl', tex_bowl())
    sv('wheel_metal', tex_metal_wheel()); sv('vent', tex_vent()); sv('beacon', TX.fill(32, (255, 150, 30), 2, 43))
    sv('pipe_teal', TX.fill(64, (40, 150, 150), 3, 45)); sv('snowblock', tex_snowblock()); sv('flame', tex_flame())
    sv('ice', tex_ice())
    S('ice', 'lms', v=0.35)          # used through _remap on the ice moose
    flywheel(); vent(); beacon(); igloo(); snow_pine(); firepit(); lamppost(); snowball_pile()
    icicles(14, 5); icicles(10, 6); crystals(9); crystals(10)
