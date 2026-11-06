"""Spin Cycle (wop_padlaundry) - textures + custom MD3/IQM models. Every model is built in its own frame
(origin = floor centre of the footprint) unless the docstring says otherwise."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from woplib import models as ML, texlib as TL, shaders as SH
from woplib.geom import tube, cylm, boxm, torus, picture, annulus, frustum_m, sweep, circle_prof
from meshlib import Mesh, revolve, disc, rbox, sphere, frame
import layout as L

C, fill, N3, xy, noise, lerp = ML.C, ML.fill, ML.N3, ML.xy, ML.noise, ML.lerp
MINT = (150, 214, 196); CREAM = (240, 232, 210); ORANGE = (240, 130, 40); TEAL = (40, 150, 150)
WHITE = (238, 240, 242); CHROME = (196, 200, 208); RED = (210, 50, 50); YELLOW = (250, 210, 60)
TX = None
MAT = {}


def setup(tx):
    global TX
    TX = tx


# ================================================================================================= brush textures
def checker_vinyl(n=256):
    x, y = xy(n)
    c = ((np.floor(x * 4) + np.floor(y * 4)) % 2)[..., None]
    base = lerp(C((236, 228, 206)), C((40, 120, 120)), c)
    return base + N3(n, 2, 11, 5) - (noise(n, 3, 12)[..., None] * 8)


def acoustic(n=256):
    x, y = xy(n)
    c = fill(n, (230, 228, 220), 4, 13)
    holes = (noise(n, 64, 14) > 0.72)
    grid = ((x * 2) % 1 < 0.015) | ((y * 2) % 1 < 0.015)
    c = np.where(holes[..., None], C((200, 196, 186)), c)
    return np.where(grid[..., None], C((160, 160, 156)), c)


def make_brush_textures():
    TX.add('vinyl', checker_vinyl(), scale=1.0)
    TX.add('wall_tile', TL.tiles(MINT, (232, 240, 236), cols=4, rows=4, offset=0, grout_w=0.04, vary=6))
    TX.add('wall_upper', TL.solid(CREAM, 4, 3, 256))
    TX.add('ceiling', acoustic(), scale=2.0)
    TX.add('steel', TL.metal((170, 174, 182)))
    TX.add('mat_floor', TL.dots((50, 52, 60), (70, 72, 80), 10, 0.25))
    TX.add('laminate', TL.solid((236, 220, 180), 3, 6, 128))
    TX.add('enamel', TL.solid(WHITE, 2, 7, 128))
    TX.add('sink_white', TL.tiles((240, 242, 244), (220, 224, 228), cols=2, rows=2, offset=0, grout_w=0.01, vary=2))
    TX.add('water', TL.solid((150, 200, 230), 10, 11, 128), 'water', rgb=(0.6, 0.8, 0.95), alpha=0.55)
    TX.add('water_suds', TL.solid((220, 235, 255), 8, 12, 128), 'water', rgb=(0.85, 0.92, 1.0), alpha=0.7)
    TX.add('glass', TL.solid((150, 190, 200), 2, 13, 64), 'glass')
    TX.add('neon_open', TL.neon('OPEN 24 HRS', RED, 512, 128), 'sign', check_tile=False)
    TX.add('sign_spin', TL.neon('SPIN CYCLE', (80, 220, 255), 512, 128), 'sign', check_tile=False)
    TX.add('sock_wall', sock_stripes((120, 60, 200), (250, 200, 60)), check_tile=False)
    TX.add('sock_floor', sock_stripes((240, 90, 140), (90, 220, 220)), check_tile=False)
    TX.kit_defaults(pad_rgb=(80, 220, 255), rubber=(40, 44, 54))


def sock_stripes(c1, c2, n=128):
    x, y = xy(n)
    return lerp(C(c1), C(c2), ((y * 6) % 1 < 0.5)[..., None]) + N3(n, 2, 15, 4)


def lint_tex(n=128):
    x, y = xy(n)
    mesh = ((x * 24) % 1 < 0.2) | ((y * 24) % 1 < 0.2)
    fluff = noise(n, 6, 16)
    return lerp(C((180, 160, 220)), C((250, 240, 255)), fluff[..., None]) * np.where(mesh[..., None], 0.7, 1.0)


# ================================================================================================= model textures
def panel_tex(text, w=512, h=128, bg=(70, 74, 84)):
    """machine control panel: coin slot, a dial, two buttons and a small LED label"""
    a = np.zeros((h, w, 3), np.float32) + C(bg)
    x, y = xy(w, h)
    lab = TL.label(text, 256, 48, (20, 22, 26), (90, 240, 160))
    a[40:88, 40:296] = lab[:48, :256]
    d = np.hypot((x - 0.72) * w / h, y - 0.5)
    a = np.where((d < 0.30)[..., None], C((200, 204, 212)), a)
    a = np.where((d < 0.06)[..., None], C((40, 40, 46)), a)
    for bx, col in ((0.87, RED), (0.93, (60, 200, 90))):
        dd = np.hypot((x - bx) * w / h, y - 0.5)
        a = np.where((dd < 0.10)[..., None], C(col), a)
    a[30:98, 330:342] = C((20, 20, 24))          # coin slot
    return a


def drum_tex(n=256):
    x, y = xy(n)
    holes = np.hypot((x * 16) % 1 - 0.5, (y * 16) % 1 - 0.5) < 0.18
    base = fill(n, (196, 200, 206), 4, 17) + (np.sin(x * 40) * 6)[..., None]
    return np.where(holes[..., None], C((40, 42, 48)), base)


def clothes_tex(n=256, seed=3):
    """patchwork of laundry: stripes, checks, denim, polka dots"""
    rng = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32)
    x, y = xy(n)
    pals = [((40, 70, 140), (60, 90, 170)), ((220, 60, 70), (250, 250, 250)), ((250, 200, 60), (240, 120, 40)),
            ((90, 180, 90), (240, 240, 230)), ((150, 80, 170), (230, 200, 240)), ((40, 40, 50), (90, 90, 100))]
    cells = 4
    for i in range(cells):
        for j in range(cells):
            c1, c2 = pals[rng.integers(len(pals))]
            k = rng.integers(3)
            sl = (slice(j * n // cells, (j + 1) * n // cells), slice(i * n // cells, (i + 1) * n // cells))
            xx, yy = x[sl], y[sl]
            if k == 0: m = ((yy * 40) % 1 < 0.5)
            elif k == 1: m = (((xx * 24) % 1 < 0.5) ^ ((yy * 24) % 1 < 0.5))
            else: m = np.hypot((xx * 30) % 1 - 0.5, (yy * 30) % 1 - 0.5) < 0.25
            a[sl] = lerp(C(c1), C(c2), m[..., None].astype(np.float32))
    folds = (noise(n, 5, seed + 9) - 0.5)[..., None] * 50
    return a + folds


def bottle_label(n=256):
    a = fill(n, (40, 120, 230), 3, 18)
    lab = TL.label('SUDZ!', 256, 96, (250, 210, 60), (200, 30, 40))
    a[80:176] = lab[:96, :n]
    return a


def mats():
    M = MAT
    M['enamel'] = TX.material('enamel_m', TL.solid(WHITE, 2, 21, 128), 'lms', v=0.08, shade=40)
    M['chrome'] = TX.material('chrome', TL.metal(CHROME), 'lms', v=0.35, shade=50)
    M['steel'] = TX.material('steel_m', TL.metal((150, 154, 162)), shade=40)
    M['dark'] = TX.material('dark', TL.solid((40, 42, 48), 3, 22, 128), shade=40)
    M['panel_w'] = TX.material('panel_w', panel_tex('WASH 4.50'), shade=40)
    M['panel_d'] = TX.material('panel_d', panel_tex('DRY 2.00'), shade=40)
    M['glass'] = TX.material('glass_m', TL.solid((170, 210, 230), 2, 23, 64), 'glass', c='0.1 0.13 0.15')
    M['rubber'] = TX.material('rubber_m', TL.solid((40, 40, 46), 3, 24, 128), shade=40)
    M['drum'] = TX.material('drum_m', drum_tex(), shade=40)
    M['clothes'] = TX.material('clothes', clothes_tex(), shade=60)
    M['clothes2'] = TX.material('clothes2', clothes_tex(seed=7), shade=60)
    M['orange'] = TX.material('orange_p', TL.solid(ORANGE, 3, 25, 128), shade=50)
    M['teal'] = TX.material('teal_p', TL.solid(TEAL, 3, 26, 128), shade=50)
    M['laminate'] = TX.material('laminate_m', TL.solid((236, 220, 180), 3, 27, 128), shade=40)
    M['bottle'] = TX.material('bottle_lab', bottle_label(), lathe=True, shade=50)
    M['blue'] = TX.material('blue_p', TL.solid((40, 120, 230), 3, 28, 128), shade=50)
    M['red'] = TX.material('red_p', TL.solid(RED, 3, 29, 128), shade=50)
    M['yellow'] = TX.material('yellow_p', TL.solid(YELLOW, 3, 30, 128), shade=50)
    M['bubble'] = TX.material('bubble', bubble_tex(), 'add', tcmod='scroll 0 0.4')
    M['glow_w'] = TX.material('glow_white', TL.solid((250, 250, 240), 1, 31, 64), 'glow')
    M['glow_g'] = TX.material('glow_green', TL.solid((90, 240, 160), 1, 32, 64), 'glow')
    M['change'] = TX.material('change_front', machine_front('CHANGE', (60, 60, 70), YELLOW), shade=40)
    M['soapv'] = TX.material('soap_front', machine_front('SOAP', (160, 30, 40), (250, 250, 250)), shade=40)
    M['lint'] = TX.material('lint_m', lint_tex(), 'glow')
    return M


def bubble_tex(n=128):
    rng = np.random.default_rng(4)
    a = np.zeros((n, n, 3), np.float32)
    x, y = xy(n)
    for _ in range(40):
        cx, cy, r = rng.random(), rng.random(), rng.uniform(0.03, 0.09)
        d = np.hypot(x - cx, y - cy)
        ring = np.exp(-((d - r) / 0.008) ** 2) * 160 + np.exp(-(d / (r * 0.35)) ** 2) * 60 * (d < r)
        a += ring[..., None] * np.array([0.8, 0.95, 1.0])
    return np.clip(a, 0, 255)


def machine_front(text, bg, fg, w=256, h=512):
    a = fill(w, bg, 3, 33, h)
    lab = TL.label(text, 256, 64, (20, 20, 24), fg)
    a[40:104] = lab[:64, :w]
    a[150:330, 40:216] = C((30, 30, 36))
    for i, yy in enumerate(range(170, 320, 30)):
        a[yy:yy + 18, 60:196] = C((200, 204, 210) if i % 2 else fg)
    a[380:420, 90:166] = C((10, 10, 12))
    return a


# ================================================================================================= mesh helpers
def fpoly(M, pts, n, uvs):
    """Mesh.poly with the winding fixed to face n (front = counter-clockwise round n, as Mesh.quad builds)"""
    P = [np.asarray(p, float) for p in pts]
    if len(P) >= 3 and float(np.dot(np.cross(P[1] - P[0], P[2] - P[0]), n)) < 0:
        pts, uvs = list(pts)[::-1], list(uvs)[::-1]
    M.poly(pts, n, uvs)


def plate_with_hole(M, o, u, v, nrm, w, h, hc, r, n=48, tile=None):
    """flat w x h plate (corner o, axes u v, normal nrm) with a round hole of radius r centred at hc=(hu, hv);
    triangles fan from the hole to the plate edge along rays, corners filled. Planar UVs over the plate."""
    o, u, v, nrm = (np.asarray(a, float) for a in (o, u, v, nrm))
    P = lambda a, b: o + u * a + v * b
    uvf = (lambda a, b: (a / w, 1 - b / h)) if tile is None else (lambda a, b: (a / tile, -b / tile))
    corners = [(w, h), (0, h), (0, 0), (w, 0)]

    def ray(t):
        dx, dy = math.cos(t), math.sin(t)
        ts = []
        if dx > 1e-9: ts.append((w - hc[0]) / dx)
        if dx < -1e-9: ts.append(-hc[0] / dx)
        if dy > 1e-9: ts.append((h - hc[1]) / dy)
        if dy < -1e-9: ts.append(-hc[1] / dy)
        s = min(ts)
        return (hc[0] + dx * s, hc[1] + dy * s)
    angs = [2 * math.pi * k / n for k in range(n + 1)]
    cang = [math.atan2(cy - hc[1], cx - hc[0]) % (2 * math.pi) for (cx, cy) in corners]
    for k in range(n):
        ta, tb = angs[k], angs[k + 1]
        ca = (hc[0] + r * math.cos(ta), hc[1] + r * math.sin(ta)); cb = (hc[0] + r * math.cos(tb), hc[1] + r * math.sin(tb))
        ba, bb = ray(ta), ray(tb)
        mids = [corners[i] for i in range(4) if ta < cang[i] <= tb]
        ring = [ba] + mids + [bb]
        for i in range(len(ring) - 1):
            pts = [ca, ring[i], ring[i + 1]]
            fpoly(M, [P(*p) for p in pts], nrm, [uvf(*p) for p in pts])
        pts = [ca, bb, cb]
        fpoly(M, [P(*p) for p in pts], nrm, [uvf(*p) for p in pts])


def front_loader(name, depth, width, height, hole_r, hole_z, panel, door_tunnel, closed=False, base=0):
    """machine cabinet facing +x: front plate with a round door hole (or a closed glass door), chrome rim, control
    panel strip at the top, enamel sides/top, rubber tunnel through the front. Origin = front-face centre at the
    cabinet's floor; the cabinet extends to -x."""
    X = ML.Model()
    e = MAT['enamel']; hw = width / 2
    boxm(X.mesh(e), (-depth, -hw, base), (-4, hw, height), r=6, tile=128, faces='nsewt')
    # front plate with the hole, a hair in front of the box face
    plate_with_hole(X.mesh(e), (-2, hw, base), (0, -1, 0), (0, 0, 1), (1, 0, 0), width, height - base - 96,
                    (hw, hole_z - base), hole_r + 6)
    picture(X.mesh(MAT[panel]), (-1.5, 0, height - 50), width - 24, 80, (1, 0, 0))
    torus(X.mesh(MAT['chrome']), (0, 0, hole_z), hole_r + 10, 8, axis=(1, 0, 0), n=48, m=8)
    revolve_tunnel(X.mesh(MAT['rubber']), hole_r + 6, door_tunnel, hole_z)
    if closed:
        disc_x(X.mesh(MAT['glass']), 6, hole_r + 4, hole_z)
        disc_x(X.mesh(MAT['drum']), -door_tunnel - 4, hole_r + 6, hole_z)
    # feet / kick plate
    boxm(X.mesh(MAT['dark']), (-depth + 8, -hw + 8, base), (-8, hw - 8, base + 12), r=2, tile=64, faces='nsewt')
    return ML.save(name, X)


def revolve_tunnel(M, r, length, zc):
    """short inward tube along -x from the front (the rubber door seal)"""
    n = 32
    for k in range(n):
        a, b = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = lambda t, x: (x, r * math.cos(t), zc + r * math.sin(t))
        nm = (0, -math.cos((a + b) / 2), -math.sin((a + b) / 2))
        fpoly(M, [p(a, 0), p(a, -length), p(b, -length), p(b, 0)], nm, [(k / 8, 0), (k / 8, 1), ((k + 1) / 8, 1), ((k + 1) / 8, 0)])


def disc_x(M, x, r, zc, n=32, facing=1):
    pts = [(x, r * math.cos(2 * math.pi * k / n) * facing, zc + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for k in range(n):
        a, b = pts[k], pts[(k + 1) % n]
        fpoly(M, [(x, 0, zc), a, b] if facing > 0 else [(x, 0, zc), b, a], (facing, 0, 0),
               [(0.5, 0.5), (0.5 + 0.5 * math.cos(2 * math.pi * k / n), 0.5 + 0.5 * math.sin(2 * math.pi * k / n)),
                (0.5 + 0.5 * math.cos(2 * math.pi * (k + 1) / n), 0.5 + 0.5 * math.sin(2 * math.pi * (k + 1) / n))])


# ================================================================================================= models
def washer():
    return front_loader('washer', L.W_X[1] - L.W_X[0], 2 * L.W_HALF, L.W_H, L.W_DOOR_R, L.W_DRUM_Z - L.PED, 'panel_w', 40)


def dryer_low():
    return front_loader('dryer_low', L.D_X[1] - L.D_X[0], 2 * L.D_HALF, L.D_LOW_H, L.D_DRUM_R, L.D_DRUM_Z, 'panel_d', 30)


def dryer_up():
    return front_loader('dryer_up', L.D_X[1] - L.D_X[0], 2 * L.D_HALF, L.D_TOP - L.D_LOW_H, 200, 280, 'panel_d', 30, closed=True)


def door():
    """open washer door: chrome ring + glass bowl, hinge at the origin, the disc lies in the x-z plane extending +x
    (place it rotated so it swings away from the machine front)"""
    X = ML.Model()
    R = 166
    torus(X.mesh(MAT['chrome']), (R, 0, 0), R - 14, 14, axis=(0, 1, 0), n=48, m=8)
    for s in (-1, 1):
        m = X.mesh(MAT['glass'])
        pts = [(R + (R - 24) * math.cos(t), 0, (R - 24) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 33)[:-1]]
        for k in range(32):
            a, b = pts[k], pts[(k + 1) % 32]
            c = (R, s * 30, 0)
            fpoly(m, [a, b, c] if s > 0 else [b, a, c], (0, s, 0), [(0, 0), (1, 0), (0.5, 1)])
    boxm(X.mesh(MAT['chrome']), (-6, -12, -40), (14, 12, 40), r=2, tile=32)
    return ML.save('door', X)


DOOR_BOX = [((0, -18, -162), (332, 18, 162))]


def drum_iqm(name, R, length, socks=3):
    """the spinning drum (model2 on a func_rotating, x axis): perforated inner cylinder seen from inside, back plate,
    three baffles, a few tumbling socks. Origin = drum centre; the drum runs from -length/2 to +length/2 along x."""
    X = ML.Model()
    dm = ML.S('drum_dyn', 'dyn'); ML.T('drum_dyn', drum_tex())
    h = length / 2
    n = 32
    m = X.mesh(dm)
    for k in range(n):
        a, b = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = lambda t, x: (x, R * math.cos(t), R * math.sin(t))
        nm = (0, -math.cos((a + b) / 2), -math.sin((a + b) / 2))
        fpoly(m, [p(a, -h), p(b, -h), p(b, h), p(a, h)], nm, [(k / 4, 0), ((k + 1) / 4, 0), ((k + 1) / 4, length / 128), (k / 4, length / 128)])
    disc_x(X.mesh(dm), -h, R, 0, facing=1)
    for k in range(3):
        a = 2 * math.pi * k / 3
        d = np.array([0, math.cos(a), math.sin(a)]); t = np.array([0, -math.sin(a), math.cos(a)])
        base = d * (R - 1); tip = d * (R - 40)
        for s in (-1, 1):
            q = [base + t * 22 * s + np.array([-h + 10, 0, 0]), base + t * 22 * s + np.array([h - 10, 0, 0]),
                 tip + np.array([h - 10, 0, 0]), tip + np.array([-h + 10, 0, 0])]
            nn = t * s
            fpoly(X.mesh(dm), q if s > 0 else q[::-1], nn, [(0, 0), (1, 0), (1, 0.3), (0, 0.3)])
    sk = ML.S('sock_dyn', 'dyn'); ML.T('sock_dyn', sock_stripes((240, 90, 140), (250, 250, 250)))
    rng = np.random.default_rng(len(name))
    for i in range(socks):
        a = rng.uniform(0, 2 * math.pi); x = rng.uniform(-h + 60, h - 60)
        c = np.array([x, (R - 30) * math.cos(a), (R - 30) * math.sin(a)])
        path = [c + np.array([0, 0, 0]), c + np.array([30, 6, 4]), c + np.array([44, 30, 10])]
        tube(X.mesh(sk), path, [9, 9, 10], nseg=10)
    return ML.save_iqm(name, X)


def sock_stripes(c1, c2, n=128):
    x, y = xy(n)
    return lerp(C(c1), C(c2), ((y * 6) % 1 < 0.5)[..., None]) + N3(n, 2, 15, 4)


def folding_table():
    """folding table: laminate top (TABLE_T thick) on chrome legs; origin floor centre, top 400 x 1440"""
    X = ML.Model()
    w, l = 200, 720
    boxm(X.mesh(MAT['laminate']), (-w, -l, L.TABLE_Z - L.TABLE_T), (w, l, L.TABLE_Z), r=6, tile=128)
    boxm(X.mesh(MAT['chrome']), (-w + 4, -l + 4, L.TABLE_Z - L.TABLE_T - 24), (w - 4, l - 4, L.TABLE_Z - L.TABLE_T), r=2, tile=128, faces='nsewb')
    for x in (-w + 40, w - 40):
        for y in (-l + 60, 0, l - 60):
            tube(X.mesh(MAT['chrome']), [(x, y, 0), (x, y, L.TABLE_Z - L.TABLE_T - 24)], 14, nseg=10)
    return ML.save('table', X)


TABLE_LEGS = [(x, y, 16, 0, L.TABLE_Z - L.TABLE_T) for x in (-160, 160) for y in (-660, 0, 660)]


def pile():
    """Mount Laundry: a lumpy heap of clothes (revolve with noise lumps), a sock and a T-shirt sleeve on top.
    The collision is 16u terraces under it (builder), so the mesh hugs the terrace edges."""
    X = ML.Model()
    rng = np.random.default_rng(12)
    tiers = L.PILE_TIERS
    prof = []
    for i in range(tiers + 1):
        r = L.PILE_R0 - i * L.PILE_STEP_R
        prof.append((r + 6, i * 16 + 2))
    prof.append((0, tiers * 16 + 8))
    G = Mesh(); revolve(G, prof, n=40, vlen=256, u_tiles=6)
    # lumps: push vertices out/up with smooth noise by angle
    ph = rng.uniform(0, 6.3, 5)
    for i, p in enumerate(G.V):
        a = math.atan2(p[1], p[0]); rr = math.hypot(p[0], p[1])
        bump = sum(math.sin(a * (k + 2) + ph[k]) for k in range(5)) * 2.5 * min(1, rr / 200)
        G.V[i] = (p[0], p[1], p[2] + max(0, bump))
    X.mesh(MAT['clothes']).add(G, np.eye(3), (0, 0, 0))
    top = tiers * 16
    tube(X.mesh(MAT['clothes2']), [(-60, 20, top + 8), (0, 40, top + 30), (70, 10, top + 12)], [26, 30, 24], nseg=12)
    sk = TX.material('sock_m', sock_stripes((120, 60, 200), (250, 200, 60)), shade=60)
    tube(X.mesh(sk), [(L.PILE_R0 - 120, 0, 60), (L.PILE_R0 - 60, 40, 44), (L.PILE_R0 - 20, 90, 30)], [22, 22, 26], nseg=10)
    return ML.save('pile', X)


def chair(col):
    """moulded plastic chair (seat 48 high, Padman sized is 3x that), origin floor centre, faces +y"""
    X = ML.Model()
    m = MAT[col]
    boxm(X.mesh(m), (-70, -70, 140), (70, 70, 156), r=8, tile=64)
    boxm(X.mesh(m), (-70, -78, 156), (70, -62, 300), r=8, tile=64)
    for x in (-60, 60):
        for y in (-60, 60):
            tube(X.mesh(MAT['chrome']), [(x, y, 0), (x, y, 140)], 6, nseg=8)
    return ML.save(f'chair_{col}', X)


CHAIR_BOXES = [((-70, -78, 0), (70, 70, 156)), ((-70, -78, 156), (70, -62, 300))]


def cart():
    """laundry cart: chrome frame, wire basket of mixed clothes, 4 castors; origin floor centre, 360 x 260, 420 tall"""
    X = ML.Model()
    hw, hl = 130, 180
    for x in (-hw, hw):
        for y in (-hl, hl):
            tube(X.mesh(MAT['chrome']), [(x, y, 30), (x, y, 420)], 6, nseg=8)
            sphere(X.mesh(MAT['rubber']), (x, y, 15), 15, nu=10, nv=6)
    for z in (180, 300, 420):
        tube(X.mesh(MAT['chrome']), [(-hw, -hl, z), (hw, -hl, z), (hw, hl, z), (-hw, hl, z), (-hw, -hl, z)], 4, nseg=6)
    boxm(X.mesh(MAT['steel']), (-hw, -hl, 170), (hw, hl, 180), r=1, tile=64)
    G = Mesh(); revolve(G, [(0, 180), (120, 180), (110, 300), (60, 360), (0, 380)], n=20, vlen=128)
    X.mesh(MAT['clothes2']).add(G, np.diag([1.0, 1.35, 1.0]), (0, 0, 0))
    return ML.save('cart', X)


CART_BOXES = [((-136, -186, 0), (136, 186, 420))]


def detergent():
    """giant SUDZ! detergent bottle with a cap and handle, origin floor centre, 300 across, 700 tall"""
    X = ML.Model()
    revolve(X.mesh(MAT['bottle']), [(150, 0), (160, 40), (160, 520), (110, 610), (60, 640)], n=32, vlen=640, u_tiles=1)
    revolve(X.mesh(MAT['red']), [(64, 640), (64, 700), (0, 700)], n=24, vlen=64)
    tube(X.mesh(MAT['blue']), [(110, -60, 470), (190, 0, 520), (110, 60, 570)], 18, nseg=10)
    return ML.save('detergent', X)


def sink():
    """utility sink: thick enamel basin on chrome legs, faucet over the back. Origin = footprint centre at the floor.
    Collision is the builder's brushes; this mesh matches them."""
    X = ML.Model()
    x0, y0, x1, y1 = L.SINK
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    t = L.SINK_T; zb, zt = L.SINK_Z
    e = MAT['enamel']
    boxm(X.mesh(e), (-hx - 2, -hy - 2, zb - 2), (hx + 2, -hy + t, zt + 2), r=6, tile=128)
    boxm(X.mesh(e), (-hx - 2, hy - t, zb - 2), (hx + 2, hy + 2, zt + 2), r=6, tile=128)
    boxm(X.mesh(e), (-hx - 2, -hy + t, zb - 2), (-hx + t, hy - t, zt + 2), r=6, tile=128)
    boxm(X.mesh(e), (hx - t, -hy + t, zb - 2), (hx + 2, hy - t, zt + 2), r=6, tile=128)
    boxm(X.mesh(e), (-hx + t, -hy + t, zb - 2), (hx - t, hy - t, L.SINK_FLOOR), r=2, tile=128, faces='nsewbt')
    for x in (-hx + 50, hx - 50):
        for y in (-hy + 50, hy - 50):
            tube(X.mesh(MAT['chrome']), [(x, y, 0), (x, y, zb)], 22, nseg=10)
    # faucet on the back wall
    tube(X.mesh(MAT['chrome']), [(0, hy - 30, zt), (0, hy - 30, zt + 260), (0, hy - 140, zt + 320), (0, hy - 220, zt + 260)],
         [26, 26, 24, 22], nseg=12)
    for x in (-110, 110):
        cylm(X.mesh(MAT['chrome']), (x, hy - 30, zt + 120), 24, 40)
        sphere(X.mesh(MAT['red'] if x < 0 else MAT['blue']), (x, hy - 30, zt + 170), 18, nu=10, nv=6)
    drain = Mesh(); disc(drain, 40, L.SINK_FLOOR + 0.5, up=True, n=24, cx=hx - 160, cy=0)
    X.mesh(MAT['steel']).add(drain, np.eye(3), (0, 0, 0))
    return ML.save('sink', X)


def soap_steps(n):
    """bars of soap stacked as the sink's inner steps (one bar per step, the builder's 16u stair brushes)"""
    X = ML.Model()
    cols = ['yellow', 'teal', 'orange', 'red', 'blue']
    for i in range(n):
        x0 = i * 32
        boxm(X.mesh(MAT[cols[i % 5]]), (x0, -80, 0), (x0 + 32, 80, (i + 1) * 16), r=4, tile=64)
    return ML.save('soap_steps', X)


def vending(name, mat):
    """change / soap vending machine 400 x 256 x 1000 with a glowing front, origin floor centre, faces +y"""
    X = ML.Model()
    boxm(X.mesh(MAT['steel']), (-200, -128, 0), (200, 124, 1000), r=8, tile=128)
    picture(X.mesh(MAT[mat]), (0, 125, 520), 360, 720, (0, 1, 0))
    boxm(X.mesh(MAT['glow_w']), (-180, 118, 940), (180, 126, 980), r=2, tile=64)
    return ML.save(name, X)


def bubbles():
    """soap-bubble column over a bubble lift pad (additive, scrolls upward), a slow func_rotating model2 (it floats, so
    it can't be a static misc_model); origin 40u above the pad"""
    X = ML.Model()
    for k, r in enumerate((56, 44)):
        revolve(X.mesh(MAT['bubble']), [(r, -36), (r, 560 - k * 80)], n=20, vlen=256, u_tiles=2)
    return ML.save_iqm('bubbles', X)


def ceiling_fan():
    X = ML.Model()
    cylm(X.mesh(ML.S('fan_dyn', 'dyn')), (0, 0, -40), 40, 40)
    ML.T('fan_dyn', TL.solid((240, 240, 236), 3, 34, 64))
    for k in range(4):
        a = k * math.pi / 2
        d = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-d[1], d[0], 0])
        p = [d * 40 + s * 40 + [0, 0, -28], d * 460 + s * 60 + [0, 0, -28], d * 460 - s * 60 + [0, 0, -28], d * 40 - s * 40 + [0, 0, -28]]
        fpoly(X.mesh(ML.S('fan_dyn', 'dyn')), p, (0, 0, -1), [(0, 0), (1, 0), (1, 1), (0, 1)])
        fpoly(X.mesh(ML.S('fan_dyn', 'dyn')), p[::-1], (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return ML.save_iqm('fan', X)


def light_panel():
    """fluorescent ceiling panel 512 x 160 (glowing diffuser in a white frame), origin = ceiling centre, hangs down"""
    X = ML.Model()
    boxm(X.mesh(MAT['enamel']), (-256, -80, -20), (256, 80, 0), r=2, tile=128, faces='nsewb')
    picture(X.mesh(MAT['glow_w']), (0, 0, -21), 480, 128, (0, 0, -1), up=(0, 1, 0))
    return ML.save('light_panel', X)


def lint_screen():
    """the dryer's lint screen at the back of its drum (the secret's entry); faces +x, origin bottom centre"""
    X = ML.Model()
    boxm(X.mesh(MAT['chrome']), (-6, -74, 0), (0, 74, 160), r=2, tile=64)
    picture(X.mesh(MAT['lint']), (0.5, 0, 80), 132, 144, (1, 0, 0))
    return ML.save('lint_screen', X)


def make_all():
    mats()
    washer(); dryer_low(); dryer_up(); door()
    drum_iqm('washer_drum', L.W_DRUM_R + 6, L.W_DRUM_X[1] - L.W_DRUM_X[0])
    drum_iqm('dryer_drum', L.D_DRUM_R + 6, L.D_DRUM_X[1] - L.D_DRUM_X[0], socks=4)
    folding_table(); pile(); chair('orange'); chair('teal'); cart(); detergent(); sink(); soap_steps(17)
    vending('change_machine', 'change'); vending('soap_machine', 'soapv'); bubbles(); ceiling_fan(); light_panel()
    lint_screen()
