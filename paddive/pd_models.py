"""Pad Deep Dive - custom MD3s: the shell roof, the glass drum, palms, loungers, planters, waterfalls, desk, plinth.
All shapes share the constants in pd_shape.py with the collision built in build_paddive.py."""
import math
import numpy as np
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, tube, rot_z
from pd_shape import roof_f, roof_w, ROOF_X, DRUM_RV, FACE_KIND, face_pts, MEZZ_Z

CR = {}          # collision recipes: name -> dict(boxes=[...], cyls=[...])


def frond_tex(n=256):
    x, y = ML.xy(n)
    v = np.abs(y - 0.5)
    env = 0.47 * np.clip(np.sin(np.clip(x * 1.05 + 0.04, 0, 1) * math.pi), 0, 1) ** 0.6
    slit = np.sin(x * 70 + v * 26) > -0.45
    a = ((v < env) & (slit | (v < 0.035))) * 255.0
    c = ML.lerp(ML.C((52, 120, 44)), ML.C((120, 170, 60)), (v * 2)[..., None]) + ML.N3(n, 2, 5, 8)
    c = np.where((v < 0.03)[..., None], ML.C((150, 170, 80)), c)
    return c, a


def trunk_tex(n=128):
    x, y = ML.xy(n)
    ring = (np.sin(y * math.pi * 2 * 10) * 0.5 + 0.5) ** 3
    return ML.lerp(ML.C((150, 122, 86)), ML.C((92, 70, 48)), ring[..., None]) + ML.N3(n, 1.5, 9, 8)


def fall_tex(n=256):
    x, y = ML.xy(n)
    s = ML.noise(n, 1.2, 77) * 0.5 + ML.noise(n, 6, 78)
    streak = np.clip(0.55 + 0.25 * np.sin(x * math.pi * 2 * 9 + s * 1.5) + 0.2 * ML.noise(n, 3, 79), 0, 1)
    # smear vertically so it reads as falling water (tileable: roll-average)
    st = sum(np.roll(streak, k * 6, 0) for k in range(8)) / 8
    c = ML.lerp(ML.C((120, 190, 220)), ML.C((250, 252, 255)), st[..., None])
    return c, np.clip(st * 300 - 40, 40, 235)


def shell_tex(n=256):
    c = TL.tiles((240, 228, 200), (206, 190, 150), cols=2, rows=1, offset=0, grout_w=0.012, vary=4, n=n)
    x, y = ML.xy(n)
    return c * (0.94 + 0.06 * np.sin(y * math.pi)[..., None])


def build(TX):
    """every model + its shaders; returns nothing (ML.PLACE holds the placements, CR the collision recipes)"""
    shell = TX.material('shell', shell_tex(), shade=80)
    soffit = TX.material('soffit', TL.planks((214, 160, 92), n_planks=8, stagger=False), shade=80, glowmap=None)
    frame = TX.material('frame', TL.metal((84, 96, 104)), 'lms', shade=30)
    glass = TX.material('glassamber', ML.fill(64, (255, 250, 240), 2, 3), 'glass', c='0.34 0.24 0.09')
    stone = TX.material('stonem', TL.tiles((214, 190, 158), (150, 128, 100), cols=3, rows=12, offset=0.5, vary=20), shade=30)
    white = TX.material('whitem', TL.solid((236, 232, 222), 3, 5), shade=40)
    soil = TX.material('soil', TL.solid((70, 50, 36), 10, 7))
    teak = TX.material('teak', TL.planks((176, 124, 70), n_planks=8, stagger=False), shade=30)
    towel = TX.material('towel', TL.stripes((240, 240, 236), (60, 150, 200), 6), shade=50)
    trunk = TX.material('trunk', trunk_tex(), 'vl')
    fc, fa = frond_tex()
    frond = TX.material('frond', fc, 'alpha', alpha=fa)
    wc, wa = fall_tex()
    fall = TX.material('fall', wc, 'flow', alpha=wa, speed=-0.9)
    gold = TX.material('goldm', TL.metal((226, 180, 80)), 'lms', shade=40, v=0.35)

    # ------------------------------------------------------------------ shell roof (local x, y round the building centre)
    X = ML.Model()
    xs = np.linspace(-ROOF_X, ROOF_X, 64); ts = np.linspace(-1, 1, 13)
    fz = np.array([roof_f(x) for x in xs]); fw = np.array([roof_w(x) for x in xs])
    dz = np.gradient(fz, xs)
    P = np.zeros((len(ts), len(xs), 3)); N = np.zeros_like(P); UV = np.zeros((len(ts), len(xs), 2))
    for i, t in enumerate(ts):
        P[i, :, 0] = xs; P[i, :, 1] = t * fw; P[i, :, 2] = fz + 3
        N[i, :, 0] = -dz; N[i, :, 2] = 1
        UV[i, :, 0] = xs / 192; UV[i, :, 1] = t * fw / 192
    X.mesh(shell).grid(P, N, UV)
    P2 = P.copy(); P2[..., 2] -= 30; X.mesh(soffit).grid(P2, -N, UV * 1.5)
    for sg in (-1, 1):                                   # fascia along both long edges
        E = np.stack([P[0 if sg < 0 else -1], P2[0 if sg < 0 else -1]])
        En = np.zeros_like(E); En[..., 1] = sg; En[..., 0] = np.sign(xs) * 0.3
        Eu = np.zeros((2, len(xs), 2)); Eu[..., 0] = xs / 192; Eu[1, :, 1] = 0.16
        X.mesh(shell).grid(E, En, Eu)
        k = 0 if sg < 0 else -1                          # tip caps
        X.mesh(shell).quad(P[0, k], P[-1, k], P2[-1, k], P2[0, k], n=(sg, 0, 0))
    ML.save('roof', X)

    # ------------------------------------------------------------------ glass drum: 16 faces, 3 panels each
    X = ML.Model()
    for i in range(16):
        p0, p1 = face_pts(i, DRUM_RV)
        ca = math.radians(22.5 * i); nrm = (math.cos(ca), math.sin(ca), 0)
        q = [p0 + (p1 - p0) * s / 3 for s in range(4)]
        top = [roof_f(p[0]) - 28 for p in q]
        kind = FACE_KIND.get(i)
        spans = [(128, None)] if kind == 'ground' else [(0, MEZZ_Z), (MEZZ_Z + 128, None)] if kind == 'upper' else [(0, None)]
        for s in range(3):
            for (z0, z1) in spans:
                za, zb = (top[s], top[s + 1]) if z1 is None else (z1, z1)
                X.mesh(glass).poly([(q[s][0], q[s][1], z0), (q[s + 1][0], q[s + 1][1], z0), (q[s + 1][0], q[s + 1][1], zb),
                                    (q[s][0], q[s][1], za)], nrm, [(s, z0 / 128), (s + 1, z0 / 128), (s + 1, zb / 128), (s, za / 128)])
        for s in range(3):                               # mullions (the corner post once per face)
            for (z0, z1) in ([(0, None)] if s == 0 else spans):
                tube(X.mesh(frame), [(q[s][0], q[s][1], z0), (q[s][0], q[s][1], top[s] if z1 is None else z1)], 5 if s else 8, nseg=4, vlen=64)
        for z in ([0] if kind != 'ground' else []) + [128] + ([MEZZ_Z] if kind != 'upper' else []) + [MEZZ_Z + 128]:
            tube(X.mesh(frame), [(p0[0], p0[1], z), (p1[0], p1[1], z)], 4, nseg=4, vlen=64)
        tube(X.mesh(frame), [(q[s][0], q[s][1], top[s]) for s in range(4)], 5, nseg=4, vlen=64)
    ML.save('drum', X)

    # ------------------------------------------------------------------ palm
    X = ML.Model()
    H = 380
    path = [(18 * math.sin(t * 1.4), 0, H * t) for t in np.linspace(0, 1, 9)]
    tube(X.mesh(trunk), path, [16 - 7 * t for t in np.linspace(0, 1, 9)], nseg=8, vlen=48, caps=(False, True))
    top = np.array(path[-1])
    for k in range(11):
        a = k * 2 * math.pi / 11 + 0.3 * (k % 2)
        L = 190 + 30 * (k % 3); droop = 0.9 + 0.25 * (k % 2)
        ps = []
        for s in np.linspace(0, 1, 6):
            r = L * s; z = 70 * s - droop * 150 * s * s
            ps.append((top[0] + r * math.cos(a), top[1] + r * math.sin(a), top[2] + z))
        side = np.array([-math.sin(a), math.cos(a), 0]) * 34
        Pg = np.array([[np.array(p) - side for p in ps], [np.array(p) + side for p in ps]])
        Ng = np.zeros_like(Pg); Ng[..., 2] = 1
        Ug = np.zeros((2, 6, 2)); Ug[0, :, 1] = 0; Ug[1, :, 1] = 1; Ug[:, :, 0] = np.linspace(0, 1, 6)
        X.mesh(frond).grid(Pg, Ng, Ug)
    ML.save('palm', X); CR['palm'] = dict(cyls=[(0, 0, 14, 0, 300)])

    # ------------------------------------------------------------------ sun lounger (teak frame, striped cushion)
    X = ML.Model()
    rbox(X.mesh(teak), (-56, -22, 10), (40, 22, 20), r=3, k=2, tile=64)
    for (lx, ly) in ((-48, -18), (-48, 18), (32, -18), (32, 18)):
        rbox(X.mesh(teak), (lx - 4, ly - 4, 0), (lx + 4, ly + 4, 12), r=1.5, k=1, tile=64)
    rbox(X.mesh(towel), (-52, -19, 20), (38, 19, 25), r=2.5, k=2, tile=48)
    B = ML.Model(); rbox(B.mesh(teak), (0, -22, -4), (44, 22, 4), r=3, k=2, tile=64); rbox(B.mesh(towel), (2, -19, 4), (42, 19, 9), r=2.5, k=2, tile=48)
    ca, sa = math.cos(math.radians(-38)), math.sin(math.radians(-38))
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
    X.add_model(B, Ry, (36, 0, 20))
    ML.save('lounger', X); CR['lounger'] = dict(boxes=[((-56, -22, 0), (44, 22, 24)), ((36, -22, 24), (72, 22, 48))])

    # ------------------------------------------------------------------ planter (stone tub with soil)
    X = ML.Model()
    revolve(X.mesh(stone), [(52, 0), (64, 10), (70, 60), (62, 60), (60, 52)], u_tiles=4, n=20, vlen=64)
    disc(X.mesh(soil), 60, 52, up=True, n=20)
    ML.save('planter', X); CR['planter'] = dict(cyls=[(0, 0, 66, 0, 52)])

    # ------------------------------------------------------------------ plinth for the gold statue
    X = ML.Model()
    revolve(X.mesh(stone), [(96, 0), (96, 20), (72, 28), (72, 84), (84, 96), (0, 96)], u_tiles=6, n=24, vlen=64)
    revolve(X.mesh(gold), [(86, 86), (86, 92)], u_tiles=6, n=24)
    ML.save('plinth', X); CR['plinth'] = dict(cyls=[(0, 0, 92, 0, 96)])

    # ------------------------------------------------------------------ curved reception desk (arc open to +y)
    X = ML.Model()
    revolve(X.mesh(white), [(150, 0), (150, 52), (110, 52), (110, 0)], u_tiles=3, n=18, a0=200, a1=340, vlen=64)
    revolve(X.mesh(teak), [(156, 52), (156, 58), (104, 58), (104, 52)], u_tiles=3, n=18, a0=200, a1=340, vlen=64)
    for a in (200, 340):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        X.mesh(white).quad((110 * c, 110 * s, 0), (150 * c, 150 * s, 0), (150 * c, 150 * s, 52), (110 * c, 110 * s, 52),
                           n=(-s, c, 0) if a == 340 else (s, -c, 0), tile=64)
    ML.save('desk', X)
    CR['desk'] = dict(boxes=[((-150 + 60 * k, -150 + abs(k - 2) * 28, 0), (-90 + 60 * k, -104 + abs(k - 2) * 28, 58)) for k in range(5)])

    # ------------------------------------------------------------------ waterfall sheets (thin, a few units off the wall)
    for name, w, h in (('fall_big', 216, 220), ('fall_mid', 220, 156), ('fall_side', 56, 68), ('fall_stair', 260, 20)):
        X = ML.Model(); M = X.mesh(fall)
        nx = max(2, int(w / 60))
        for k in range(nx):                              # slightly bowed sheet so it catches the eye from the side
            x0, x1 = -w / 2 + w * k / nx, -w / 2 + w * (k + 1) / nx
            M.poly([(x0, 0, 0), (x1, 0, 0), (x1, -2, h), (x0, -2, h)], (0, -1, 0),
                   [(x0 / 96, h / 96), (x1 / 96, h / 96), (x1 / 96, 0), (x0 / 96, 0)])
        ML.save(name, X)
