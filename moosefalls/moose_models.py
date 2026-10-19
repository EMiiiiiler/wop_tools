"""Custom MD3 map objects for wop_moosefalls (Moose Mountain Falls). All geometry and art is original and generated here.

    make(out) -> writes models/moosefalls/*.md3 and their images (base set)
    gen_*()   -> per-placement models the builder asks for (railings, rope fences, posts of a given height)
    shaders() -> shader text for every model surface registered so far (call after the builder is done)

Human scale (~32u per metre). Origin = base centre unless noted. The builder (build_moose.py) reads layout.py for the
same numbers, so collision brushes (common/weapclip, moosefalls/slide_clip) sit just inside the visible surfaces.

  pine_trunk / pine_needles   the giant indoor pine on the tree island (trunk, limbs; needle sprays are vertex lit)
  tube_yellow                 Yellow Jacket closed tube slide (bolted flanges, running water strip, supports)
  flume_green                 Green Gulch open flume (supports)
  kid_blue / kid_yellow / kid_teal   Tiny Timbers kids' slides
  gable_*                     gable roofs (tower, play cabins, snack porch, stump hut)
  crib_*                      log-cabin walls (tower core, play structure base, tower top, stump hut)
  column_*                    glulam columns with painted bases (picture 1), rafter + ridge beam, ducts, pendant lamps
  tube_*                      inner tubes (single, double) floating on the water
  table_set, adirondack, lounger, lifeguard, hoop, ladder, bucket, moose, boulders_*, rockface_*, rocktop, stump, net_frame
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, save_md3, grid_normals, rot_z, rot_axis, frame
import layout as L

MD = 'models/moosefalls'
OUT = None
REG = {}
PLACE = {}          # model name -> (path, scale, zoff)
PAD_AZ = 300.0      # azimuth (deg) of the treehouse -> crow's nest pad (branches leave it clear)


# ================================================================================================= registry / helpers
def S(img, kind='lm', **opt):
    """register a model shader using models/moosefalls/<img>"""
    key = f'{img}_{kind}{opt.get("tag", "")}'.replace('/', '_')
    name = f'{MD}/{key}'
    REG[name] = (img, kind, opt)
    return name


class Model:
    def __init__(self): self.m = {}

    def mesh(self, shader):
        if shader not in self.m: self.m[shader] = Mesh()
        return self.m[shader]

    def surfaces(self):
        return [M.surface(f's{i}', sh) for i, (sh, M) in enumerate(self.m.items()) if len(M)]


def _save(name, X):
    path = f'{MD}/{name}.md3'
    sc, zo = save_md3(os.path.join(OUT, path), X.surfaces(), name, with_offset=True)
    PLACE[name] = (path, sc, zo)
    return path, sc, zo


def sweep(M, path, prof, closed=False, vlen=128.0, inward=False, utile=1.0):
    """sweep a 2D cross-section prof [(u, v)] (u lateral, v up) along a 3D path; frames keep 'up' = world z
    (good for slides up to ~25 deg). Normals from the grid; inward flips them (inside of a tube)."""
    P0 = np.asarray(path, float)
    n = len(P0)
    T = np.gradient(P0, axis=0)
    Th = T[:, :2] / np.maximum(np.linalg.norm(T[:, :2], axis=1, keepdims=True), 1e-9)
    lat = np.stack([-Th[:, 1], Th[:, 0], np.zeros(n)], 1)        # left of travel
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P0, axis=0), axis=1))])
    pr = list(prof) + ([prof[0]] if closed else [])
    m = len(pr)
    P = np.zeros((n, m, 3)); UV = np.zeros((n, m, 2))
    cl = np.concatenate([[0], np.cumsum([math.hypot(pr[k + 1][0] - pr[k][0], pr[k + 1][1] - pr[k][1]) for k in range(m - 1)])])
    for i in range(n):
        for j, (u, v) in enumerate(pr):
            P[i, j] = P0[i] + lat[i] * u + np.array([0, 0, v])
            UV[i, j] = (cl[j] / max(cl[-1], 1e-6) * utile, Ls[i] / vlen)
    N = grid_normals(P)
    # orient: outward = away from the profile centroid
    cu = np.mean([p[0] for p in prof]); cv = np.mean([p[1] for p in prof])
    cen = P0[:, None, :] + lat[:, None, :] * cu + np.array([0, 0, cv])
    if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
    if inward: N = -N
    M.grid(P, N, UV)
    return P


def circle_prof(r, n=16, a0=0.0, a1=360.0):
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n + 1)[:(-1 if a1 - a0 >= 360 else None)]]


def densify(path, step=48.0):
    out = [np.asarray(path[0], float)]
    for a, b in zip(path, path[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for t in np.linspace(0, 1, k + 1)[1:]: out.append(a + (b - a) * t)
    return out


def interp_r(prof, z):
    return float(np.interp(z, [p[0] for p in prof], [p[1] for p in prof]))


def box_mesh(M, mn, mx, tile=64.0, faces='nsewtb'):
    rbox(M, mn, mx, r=0.0, k=1, tile=tile, faces=faces)


def beam(M, a, b, w, h, tile=128.0):
    """rectangular beam from a to b (w across horizontally, h across vertically-ish), flat shaded"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; Ld = np.linalg.norm(d); d /= Ld
    up = np.array([0, 0, 1.0])
    side = np.cross(d, up)
    if np.linalg.norm(side) < 1e-6: side = np.array([1.0, 0, 0])
    side /= np.linalg.norm(side); vup = np.cross(side, d)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    ring = lambda c: [c + side * u + vup * v for (u, v) in corners]
    ra, rb = ring(a), ring(b)
    for k in range(4):
        q = [ra[k], ra[(k + 1) % 4], rb[(k + 1) % 4], rb[k]]
        nrm = (ra[k] + ra[(k + 1) % 4]) / 2 - a
        nrm /= np.linalg.norm(nrm)
        lw = w if k % 2 == 0 else h
        M.poly(q, nrm, [(0, 0), (lw / tile, 0), (lw / tile, Ld / tile), (0, Ld / tile)])
    for (r, c, s) in ((ra, a, -1), (rb, b, 1)):
        M.poly(r, d * s, [(0, 0), (w / tile, 0), (w / tile, h / tile), (0, h / tile)])


# ================================================================================================= textures (models)
def _tx():
    import moose_textures as TX
    return TX


def tex_needles(w=256, h=256, seed=3):
    """pine needle spray (alpha): a twig with dense needles both sides"""
    r = np.random.default_rng(seed)
    col = np.zeros((h, w, 3), np.float32)
    al = Image.new('L', (w, h), 0); im = Image.new('RGB', (w, h), (40, 80, 40))
    d = ImageDraw.Draw(im); da = ImageDraw.Draw(al)
    for tw in range(3):
        x0, y0 = w * 0.5 + r.normal(0, 18), h - 4
        x1, y1 = w * 0.5 + r.normal(0, 40), 10
        for t in np.linspace(0, 1, 70):
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for s in (-1, 1):
                L_ = (1 - t * 0.6) * r.uniform(30, 56)
                ang = math.radians(90 - s * r.uniform(35, 65))
                ex, ey = cx + s * L_ * math.sin(ang), cy - L_ * math.cos(ang) * 0.5
                c = tuple(int(v) for v in (np.array([46, 96, 52]) + r.normal(0, 16, 3)).clip(0, 255))
                d.line((cx, cy, ex, ey), fill=c, width=2); da.line((cx, cy, ex, ey), fill=255, width=2)
        d.line((x0, y0, x1, y1), fill=(90, 64, 40), width=4); da.line((x0, y0, x1, y1), fill=255, width=4)
    a = np.asarray(im, np.float32); A = np.asarray(al, np.float32)
    return a, A


def tex_slide(col, w=128, h=256, seed=5, stripe=None):
    TX = _tx()
    a = TX.fill(w, col, 3, seed, h)
    x, y = TX.tile_xy(w, h)
    a *= (0.88 + 0.12 * np.cos((x - 0.5) * math.pi * 2))[..., None]
    if stripe is not None:
        a[:, (np.arange(w) % 64) < 4] = stripe
    return a


def tex_water_strip(w=64, h=256, seed=7):
    TX = _tx()
    x, y = TX.tile_xy(w, h)
    st = TX.noise(w, 1.5, seed, h) * 0.5 + np.sin(x * math.pi * 8) * 0.2
    return np.zeros((h, w, 3), np.float32) + TX.C((120, 190, 230)) * np.clip(0.4 + 0.4 * st, 0, 1)[..., None]


def tex_column_base(w=256, h=256, seed=9):
    """painted column cladding: white with a zigzag band in teal, gold and navy (picture 1)"""
    TX = _tx()
    a = TX.fill(w, (236, 232, 222), 3, seed, h)
    im = TX.img(a); d = ImageDraw.Draw(im)
    for (y0, col) in ((60, (40, 60, 130)), (96, (220, 170, 60)), (132, (40, 150, 150))):
        pts = []
        for k in range(0, w + 33, 32):
            pts += [(k, y0), (k + 16, y0 + 20)]
        d.line(pts, fill=col, width=6)
    d.rectangle((0, 24, w, 30), fill=(40, 60, 130)); d.rectangle((0, 176, w, 182), fill=(40, 60, 130))
    return TX.arr(im)


def tex_duct(w=128, h=128, seed=11):
    TX = _tx()
    a = TX.fill(w, (214, 196, 160), 4, seed, h)
    a[:, (np.arange(w) % 32) < 2] *= 0.85
    return a


def tex_tube(col, col2, w=256, h=64, seed=13):
    """inner tube rubber: base colour with splashes of a second colour"""
    TX = _tx()
    a = TX.fill(w, col, 4, seed, h)
    m = TX.noise(w, 5, seed + 1, h) > 0.7
    a[m] = col2
    a[:, :] *= 1.0
    return a


def tex_white(n=64, seed=15): return _tx().fill(n, (238, 238, 234), 3, seed)


def tex_wood(n=128, seed=17, col=(150, 100, 60)):
    TX = _tx()
    x, y = TX.tile_xy(n)
    return TX.C(col) + np.sin((y * 10 + TX.noise(n, 8, seed) * 0.4) * 2 * math.pi)[..., None] * 12 + TX.N3(n, 1, seed + 1, 6)


def tex_log_side(w=256, h=128, seed=19):
    """log bark side: u = round the log, v = along it"""
    TX = _tx()
    x, y = TX.tile_xy(w, h)
    a = TX.fill(w, (150, 98, 54), 6, seed, h)
    a += (np.sin(x * 2 * math.pi * 3 + TX.noise(w, 10, seed + 1, h) * 1.2) * 14)[..., None] * TX.C((1, 0.8, 0.6))
    knots = TX.noise(w, 3, seed + 2, h) > 2.0
    a[knots] *= 0.5
    return a


def tex_log_end(n=128, seed=21):
    TX = _tx()
    x, y = TX.tile_xy(n)
    rr = np.hypot(x - 0.5, y - 0.5) * 2
    ring = 0.5 + 0.5 * np.sin(rr * 2 * math.pi * 7)
    c = TX.lerp(TX.C((176, 126, 76)), TX.C((214, 170, 116)), ring[..., None])
    c = np.where((rr > 0.9)[..., None], TX.C((90, 60, 36)), c)
    return c


def tex_gable(w=256, h=256, seed=23):
    """gable end boards: vertical boards with battens, stained brown"""
    TX = _tx()
    a = TX.planks(w, h, seed, (130, 82, 44))
    return np.transpose(a, (1, 0, 2)).copy()


def tex_rockface(n=512, seed=25): return _tx().rock(n, seed)


def tex_moose_wood(n=256, seed=27):
    TX = _tx()
    x, y = TX.tile_xy(n)
    a = TX.C((120, 74, 38)) + (np.sin((x * 16 + TX.noise(n, 10, seed) * 0.7) * 2 * math.pi) * 16)[..., None] * TX.C((1, 0.8, 0.6))
    a += TX.N3(n, 1, seed + 1, 8)
    chis = np.abs(TX.noise(n, 3, seed + 2)) < 0.06            # chisel marks
    a[chis] *= 0.7
    return a


def tex_antler(n=128, seed=29):
    TX = _tx()
    return TX.fill(n, (214, 190, 150), 6, seed)


def tex_net(w=128, h=128):
    """rope net (alpha): diagonal mesh"""
    x, y = _tx().tile_xy(w, h)
    m = (np.abs(np.sin((x + y) * math.pi * 4)) < 0.12) | (np.abs(np.sin((x - y) * math.pi * 4)) < 0.12)
    col = np.zeros((h, w, 3), np.float32) + np.array([206, 178, 118], np.float32)
    return col, m.astype(np.float32) * 255


def tex_env(n=128, seed=31):
    TX = _tx()
    x, y = TX.tile_xy(n)
    return TX.C((150, 170, 190)) + (np.sin(y * math.pi * 2) * 60)[..., None] + TX.N3(n, 8, seed, 20)


def tex_glowpanel(n=64):
    return _tx().fill(n, (255, 236, 196), 2, 33)


# ================================================================================================= the giant pine
def branch_paths():
    """limb centre lines [(points, radii)] for the pine (shared by trunk limbs and needle sprays)"""
    rng = np.random.default_rng(7)
    whorls = [580, 640, 700, 760, 900, 960, 1015, 1065, 1105, 1140]
    out = []
    for wi, z in enumerate(whorls):
        nb = 8 if z < 1000 else 6
        Lmax = 600 * (1 - (z - 560) / 780) + 90
        a0 = rng.uniform(0, 360)
        for k in range(nb):
            a = a0 + k * 360.0 / nb + rng.uniform(-12, 12)
            if z < 900 and min(abs((a - PAD_AZ + 180) % 360 - 180), 360) < 28: continue
            Lb = Lmax * rng.uniform(0.8, 1.05)
            r0 = interp_r(L.TRUNK_VIS, z) - 6
            pts, rad = [], []
            for t in np.linspace(0, 1, 9):
                rr = r0 + Lb * t
                zz = z - 50 * math.sin(math.pi * t * 0.9) + 60 * t * t
                aa = math.radians(a + 10 * math.sin(t * 3))
                px, py = L.C[0] + rr * math.cos(aa), L.C[1] + rr * math.sin(aa)
                zz = min(zz, L.roof_z(py) - 110)
                pts.append((px, py, zz))
                rad.append(max(3.0, 15 * (1 - t) * (1.1 - (z - 600) / 1000)) + 1)
            out.append((pts, rad))
    return out


def pine():
    X = Model()
    bark = S('pine_bark', 'lm')
    rows = [(r, z * 0.97) for (z, r) in L.TRUNK_VIS]
    # trunk (local coords: origin at island centre)
    def dfm(a, r, z):
        return r + 3 * math.sin(a * 13 + z / 40) + (14 * max(0, math.sin(a * 5)) ** 4) * max(0, 1 - z / 80)
    M = X.mesh(bark)
    revolve(M, rows[:-1] + [(0.5, rows[-1][1])], u_tiles=4, n=24, vlen=256, rfun=dfm)
    for pts, rad in branch_paths():
        p = [(x - L.C[0], y - L.C[1], z) for (x, y, z) in pts]
        tube(M, p, rad, nseg=8, caps=(False, True), vlen=256)
    # needles (vertex lit, alpha): crossed sprays along each limb + a crown (same model as the trunk so it stands on the floor)
    Y = X
    nd = S('needles', 'leaf')
    N = Y.mesh(nd)
    rng = np.random.default_rng(9)
    def spray(c, d, s):
        """three crossed quads centred at c, long axis along d (unit), size s; kept under the roof and off the decks"""
        c = np.asarray(c, float)
        room = L.roof_z(c[1] + L.C[1]) - 24 - c[2]
        s = min(s, room / 0.62)
        if s < 30: return
        rr = math.hypot(c[0], c[1])
        if rr < L.CROW_R[1] + 0.62 * s and L.CROW_Z - 16 - 0.62 * s < c[2] < L.CROW_Z + 0.62 * s + 60: return
        d = np.asarray(d, float); d /= np.linalg.norm(d)
        b1, b2 = frame(d)
        for k in range(3):
            ang = k * math.pi / 3 + rng.uniform(0, 0.3)
            w = b1 * math.cos(ang) + b2 * math.sin(ang)
            nrm = np.cross(d, w)
            q = [c - d * s * 0.6 - w * s * 0.45, c + d * s * 0.6 - w * s * 0.45, c + d * s * 0.6 + w * s * 0.45, c - d * s * 0.6 + w * s * 0.45]
            N.poly(q, nrm, [(0, 1), (0, 0), (1, 0), (1, 1)])
    for pts, rad in branch_paths():
        P = np.array([(x - L.C[0], y - L.C[1], z) for (x, y, z) in pts])
        Lb = np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))
        nsp = max(4, int(Lb / 38))
        for t in np.linspace(0.25, 1.0, nsp):
            i = min(len(P) - 2, int(t * (len(P) - 1)))
            f = t * (len(P) - 1) - i
            c = P[i] + (P[i + 1] - P[i]) * f
            d = P[i + 1] - P[i]
            spray(c + rng.normal(0, 6, 3), d + rng.normal(0, 0.2 * np.linalg.norm(d), 3), 175 * (1.15 - 0.5 * t))
            # side twigs
            for s in (-1, 1):
                b1, _ = frame(d)
                spray(c + b1 * s * 46, d + b1 * s * np.linalg.norm(d) * 0.8 + np.array([0, 0, -0.15 * np.linalg.norm(d)]), 130 * (1.1 - 0.5 * t))
    # crown
    for k in range(18):
        z = 1120 + k * 6
        a = k * 137.5
        r = 70 * (1 - k / 18) + 8
        c = np.array([r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z])
        spray(c, np.array([math.cos(math.radians(a)) * 0.6, math.sin(math.radians(a)) * 0.6, 1.0]), 130 - k * 3)
    return _save('pine', X)


# ================================================================================================= slides
TUBE_ZC, TUBE_R = 44, 62           # yellow tube: centre above the floor, outer radius


def supports_for(path, on_deck, every=5, zmin=96, rtop=0):
    """support posts under a slide path: every n-th point with floor z >= zmin standing on the deck"""
    out = []
    for i in range(2, len(path) - 2, every):
        x, y, z = path[i]
        if z >= zmin and on_deck(x, y): out.append((x, y, z - rtop))
    return out


def tube_yellow(path, sup):
    X = Model()
    yel = S('slide_yellow', 'lms', v=0.22); yin = S('slide_yellow', 'lm', tag='in'); fl = S('slide_yellow2', 'lms', v=0.3, tag='f')
    wat = S('slide_water', 'addw'); met = S('metal_white', 'lms', v=0.15, tag='m')
    P = densify(path[1:], 40)
    C3 = [np.array([p[0], p[1], p[2] + TUBE_ZC]) for p in P]
    sweep(X.mesh(yel), C3, circle_prof(TUBE_R, 20), closed=True, vlen=256)
    sweep(X.mesh(yin), C3, circle_prof(TUBE_R - 4, 20), closed=True, vlen=256, inward=True)
    # flanges every ~4 points
    for i in range(0, len(C3) - 1, 5):
        c = C3[i]; d = C3[min(i + 1, len(C3) - 1)] - C3[max(i - 1, 0)]
        d /= np.linalg.norm(d)
        b1, b2 = frame(d)
        ring = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * (TUBE_R + 3) for t in np.linspace(0, 2 * math.pi, 25)]
        tube(X.mesh(fl), ring, 5, nseg=6, caps=(False, False), vlen=64)
    # running water strip on the floor (slightly above the collision floor)
    strip = [np.array([p[0], p[1], p[2] + 1.5]) for p in P]
    sweep(X.mesh(wat), strip, [(-36, 0), (36, 0)], vlen=200)
    # entry funnel ring on the deck
    c0 = C3[0]
    for (x, y, z) in sup:
        zt = z + TUBE_ZC - TUBE_R + 4
        box_mesh(X.mesh(met), (x - 7, y - 7, 0), (x + 7, y + 7, zt), tile=64)
        box_mesh(X.mesh(met), (x - 30, y - 6, zt - 10), (x + 30, y + 6, zt), tile=64)
    # local coords: model origin at world (0, 0, 0) (placed with origin 0 0 0)
    return _save('tube_yellow', X)


def flume(name, path, sup, r, lip, col_shader, inner_shader, metal):
    X = Model()
    # U profile: half circle below the floor centre line (floor = chord at depth r*0.35), lips up to floor + lip
    zc = r * 0.55                                 # circle centre above the floor
    prof_out = [(-(r + 3), zc + lip - zc)] + [((r + 3) * math.cos(a), zc + (r + 3) * math.sin(a)) for a in np.radians(np.linspace(180, 360, 13))] + [((r + 3), lip)]
    prof_in = [(-r, lip)] + [(r * math.cos(a), zc + r * math.sin(a)) for a in np.radians(np.linspace(180, 360, 13))] + [(r, lip)]
    prof_out[0] = (-(r + 3), lip)
    P = densify(path[1:], 40)
    sweep(X.mesh(col_shader), P, prof_out, vlen=256)
    sweep(X.mesh(inner_shader), P, prof_in, vlen=256, inward=True)
    sweep(X.mesh(col_shader), P, [(-(r + 3), lip), (-r, lip)], vlen=256)
    sweep(X.mesh(col_shader), P, [(r, lip), (r + 3, lip)], vlen=256)
    wat = S('slide_water', 'addw')
    strip = [np.array([p[0], p[1], p[2] + 1.5]) for p in P]
    sweep(X.mesh(wat), strip, [(-r * 0.6, 0), (r * 0.6, 0)], vlen=200)
    bot = zc - r - 3
    for (x, y, z) in sup:
        zt = z + bot + 4
        box_mesh(X.mesh(metal), (x - 6, y - 6, 0), (x + 6, y + 6, zt), tile=64)
        box_mesh(X.mesh(metal), (x - r, y - 5, zt - 8), (x + r, y + 5, zt), tile=64)
    return _save(name, X)


# ================================================================================================= gable roofs, log cribs, posts
def gable(name, Lx, Wy, rise, over=24, roof='roof_red', trim='glulam', end='gable', ends=True):
    """gable roof, ridge along x. Local: eave line z 0 at y = +-Wy/2 (wall faces), ridge z rise at y 0;
    slabs overhang `over` beyond the walls and the gable ends. Roof top surface = collision top + 2."""
    X = Model()
    rt = S(roof, 'lm'); tr = S(trim, 'lm', tag='t'); en = S(end, 'lm', tag='e')
    hw = Wy / 2; s = rise / hw
    x0, x1 = -Lx / 2 - over, Lx / 2 + over
    for sg in (-1, 1):
        ye = sg * (hw + over); ze = -over * s
        yr = 0.0; zr = rise
        top = [(x0, yr, zr + 2), (x1, yr, zr + 2), (x1, ye, ze + 2), (x0, ye, ze + 2)]
        nrm = np.array([0, sg * s, 1.0]); nrm /= np.linalg.norm(nrm)
        X.mesh(rt).poly(top, nrm, [(0, 0), ((x1 - x0) / 128, 0), ((x1 - x0) / 128, math.hypot(hw + over, rise + over * s) / 128), (0, math.hypot(hw + over, rise + over * s) / 128)])
        bot = [(x0, yr, zr - 8), (x1, yr, zr - 8), (x1, ye, ze - 8), (x0, ye, ze - 8)]
        X.mesh(tr).poly(bot, -nrm, [(0, 0), ((x1 - x0) / 128, 0), ((x1 - x0) / 128, 2), (0, 2)])
        # fascia along the eave
        X.mesh(tr).quad((x0, ye, ze + 2), (x1, ye, ze + 2), (x1, ye, ze - 12), (x0, ye, ze - 12), tile=64, n=(0, sg, 0))
        # barge boards at the gable ends
        for xx, sx in ((x0, -1), (x1, 1)):
            X.mesh(tr).poly([(xx, 0, zr + 2), (xx, ye, ze + 2), (xx, ye, ze - 10), (xx, 0, zr - 10)], (sx, 0, 0), [(0, 0), (2, 0), (2, 0.2), (0, 0.2)])
    # ridge cap
    beam(X.mesh(tr), (x0, 0, rise + 2), (x1, 0, rise + 2), 14, 10)
    if ends:
        for xx, sx in ((-Lx / 2, -1), (Lx / 2, 1)):
            tri = [(xx, -hw, 0), (xx, hw, 0), (xx, 0, rise - 6)]
            X.mesh(en).poly(tri, (sx, 0, 0), [(-hw / 128, 0), (hw / 128, 0), (0, -rise / 128)])
    return _save(name, X)


LOG_R = 16


def crib(name, Lx, Ly, H, openings=(), z0=0.0, over=20):
    """log-cabin walls round a Lx x Ly rectangle centred on the origin (walls' centre lines on the edges), logs
    every 32u from z0; openings [(side 'n'/'s'/'e'/'w', u0, u1, zlo, zhi)] in wall-local u (x for n/s, y for e/w)"""
    X = Model()
    lg = S('log_side', 'lm'); le = S('log_end', 'lm', tag='e')
    rows = int(round((H - z0) / (2 * LOG_R)))
    hx, hy = Lx / 2, Ly / 2
    for k in range(rows):
        zc = z0 + LOG_R + k * 2 * LOG_R
        for side in 'nsew':
            if side in 'ns':
                y = hy if side == 'n' else -hy
                a, b = -hx - over, hx + over
                segs = [(a, b)]
            else:
                x = hx if side == 'e' else -hx
                a, b = -hy - over, hy + over
                segs = [(a, b)]
            for (sd, u0, u1, zl, zh) in openings:
                if sd != side or not (zl - LOG_R < zc < zh + LOG_R): continue
                ns = []
                for (p, q) in segs:
                    if u1 <= p or u0 >= q: ns.append((p, q)); continue
                    if u0 > p: ns.append((p, u0))
                    if u1 < q: ns.append((u1, q))
                segs = ns
            for (p, q) in segs:
                if q - p < 8: continue
                if side in 'ns': pa, pb = (p, y, zc), (q, y, zc)
                else: pa, pb = (x, p, zc), (x, q, zc)
                rr = LOG_R * (0.94 + 0.06 * math.sin(k * 2.3 + (0 if side in 'ns' else 1)))
                tube(X.mesh(lg), [pa, pb], rr, nseg=10, caps=(False, False), vlen=256)
                for (pp, dd) in ((pa, -1), (pb, 1)):
                    c = np.asarray(pp, float); dv = (np.array([1.0, 0, 0]) if side in 'ns' else np.array([0, 1.0, 0])) * dd
                    b1, b2 = frame(dv)
                    pts = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * rr for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
                    X.mesh(le).poly(pts, dv, [(0.5 + 0.5 * math.cos(t), 0.5 + 0.5 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)])
    return _save(name, X)


def post(name, H, w=24, tex='glulam'):
    X = Model()
    sh = S(tex, 'lm', tag='p')
    rbox(X.mesh(sh), (-w / 2, -w / 2, 0), (w / 2, w / 2, H), r=3, k=2, tile=128)
    return _save(name, X)


# ================================================================================================= hall timbers, ducts, lamps
def column(name, H, braces):
    """glulam column (44 square) from 0 to H with painted round cladding to 150; braces = list of y offsets for
    knee braces up to the rafter line (along y)"""
    X = Model()
    gl = S('glulam', 'lm', tag='c'); cb = S('column_base', 'lm')
    rbox(X.mesh(gl), (-22, -22, 140), (22, 22, H), r=4, k=2, tile=128)
    revolve(X.mesh(cb), [(36, 0), (36, 150), (30, 160), (24, 166)], u_tiles=2, n=24, v_of=lambda r, z: 1 - z / 180)
    disc(X.mesh(cb), 24, 166, up=True, n=24)
    for dy in braces:
        sg = 1 if dy > 0 else -1
        a = (0, sg * 16, H - 220); b = (0, dy, H - 10 - abs(dy) * (L.RIDGE - L.EAVE) / L.HY * 0)
        beam(X.mesh(gl), a, b, 24, 24)
    return _save(name, X)


def rafter():
    """glulam rafter along y following the roof underside (x = 0), 40 wide, 72 deep"""
    X = Model()
    gl = S('glulam', 'lm', tag='r')
    D = 72
    th = math.atan((L.RIDGE - L.EAVE) / L.HY)
    off = D / 2 / math.cos(th) + 1.5
    for sg in (-1, 1):
        a = (0, sg * L.HY, L.EAVE - off); b = (0, 0, L.RIDGE - off)
        beam(X.mesh(gl), a, b, 40, D)
    # bolted plate at the ridge
    box_mesh(X.mesh(S('metal_dark', 'lm', tag='rp')), (-22, -40, L.RIDGE - D - 8), (22, 40, L.RIDGE - D + 30))
    return _save('rafter', X)


def ridge_beam():
    X = Model()
    gl = S('glulam', 'lm', tag='rb')
    beam(X.mesh(gl), (-L.HX, 0, L.RIDGE - 40), (L.HX, 0, L.RIDGE - 40), 48, 80)
    return _save('ridge_beam', X)


def duct(hang):
    """long round duct along x (radius 40, from x -1980 to 1980), hangers up to the roof (length hang above the top)"""
    X = Model()
    dt = S('duct', 'lm'); mt = S('metal_dark', 'lm', tag='d')
    R = 40
    path = [(x, 0, 0) for x in np.linspace(-1980, 1980, 34)]
    tube(X.mesh(dt), path, R, nseg=16, caps=(True, True), vlen=128, utiles=2)
    for x in np.arange(-1920, 1921, 256):
        ring = [(x, (R + 2) * math.cos(t), (R + 2) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 17)]
        tube(X.mesh(mt), ring, 3, nseg=5, caps=(False, False))
        box_mesh(X.mesh(mt), (x - 3, -3, R), (x + 3, 3, R + hang))
    return _save('duct', X)


def lamp(name, rod):
    """pendant floodlight (picture 2): dark box with a glowing panel below, hung on a rod; origin = rod top"""
    X = Model()
    mt = S('metal_dark', 'lm', tag='l'); gp = S('glowpanel', 'glow')
    box_mesh(X.mesh(mt), (-3, -3, -rod), (3, 3, 0))
    box_mesh(X.mesh(mt), (-30, -30, -rod - 26), (30, 30, -rod), faces='nsewt')
    X.mesh(gp).quad((-26, -26, -rod - 27), (26, -26, -rod - 27), (26, 26, -rod - 27), (-26, 26, -rod - 27), tile=52, n=(0, 0, -1))
    return _save(name, X)


# ================================================================================================= tubes, furniture, pool gear
def innertube(name, img, double=False):
    X = Model()
    sh = S(img, 'lms', v=0.18)
    M = X.mesh(sh)
    R, r = (22, 11) if double else (26, 11)
    cs = [(-R, 0), (R, 0)] if double else [(0, 0)]
    for (cx, cy) in cs:
        ring = [(cx + R * math.cos(t), cy + R * math.sin(t), r) for t in np.linspace(0, 2 * math.pi, 25)]
        tube(M, ring, r, nseg=10, caps=(False, False), utiles=1, vlen=2 * math.pi * R)
    if double:
        box_mesh(M, (-8, -14, 2), (8, 14, 20))
    return _save(name, X)


def small_pine():
    """potted-size pine (~300 tall above its base): bark trunk + tiers of needle sprays; origin = trunk base"""
    X = Model()
    bk = S('pine_bark', 'lm', tag='sp'); nd = S('needles', 'leaf')
    rng = np.random.default_rng(13)
    revolve(X.mesh(bk), [(16, 0), (13, 40), (9, 200), (3, 300), (0.5, 310)], n=12, u_tiles=2, vlen=128)
    N = X.mesh(nd)
    for k in range(9):
        z = 70 + k * 27
        R = 120 * (1 - k / 9) + 22
        nb = 7 if k < 6 else 5
        for j in range(nb):
            a = (j + rng.uniform(-0.2, 0.2)) * 2 * math.pi / nb + k * 0.7
            d = np.array([math.cos(a), math.sin(a), -0.25])
            c = np.array([R * 0.55 * math.cos(a), R * 0.55 * math.sin(a), z])
            s_ = R * 0.95
            b1, b2 = frame(d / np.linalg.norm(d))
            dn = d / np.linalg.norm(d)
            for q in range(2):
                ang = q * math.pi / 2 + rng.uniform(0, 0.4)
                w = b1 * math.cos(ang) + b2 * math.sin(ang)
                quad = [c - dn * s_ * 0.6 - w * s_ * 0.4, c + dn * s_ * 0.6 - w * s_ * 0.4, c + dn * s_ * 0.6 + w * s_ * 0.4, c - dn * s_ * 0.6 + w * s_ * 0.4]
                N.poly(quad, np.cross(dn, w), [(0, 1), (0, 0), (1, 0), (1, 1)])
    for k in range(5):
        a = k * 2.4
        c = np.array([6 * math.cos(a), 6 * math.sin(a), 300 + k * 4])
        d = np.array([0.3 * math.cos(a), 0.3 * math.sin(a), 1.0]); d /= np.linalg.norm(d)
        b1, b2 = frame(d)
        N.poly([c - d * 40 - b1 * 22, c + d * 40 - b1 * 22, c + d * 40 + b1 * 22, c - d * 40 + b1 * 22], np.cross(d, b1), [(0, 1), (0, 0), (1, 0), (1, 1)])
    return _save('small_pine', X)


def tube_stack():
    """rental rack: five inner tubes stacked on a wooden pallet (~92 tall)"""
    X = Model()
    wd = S('wood_post', 'lm', tag='pal')
    box_mesh(X.mesh(wd), (-34, -34, 0), (34, 34, 8))
    imgs = ['tube_yellow', 'tube_purple', 'tube_pink', 'tube_teal', 'tube_yellow']
    rng = np.random.default_rng(3)
    for k, img in enumerate(imgs):
        sh = S(img, 'lms', v=0.18)
        R, r = 25, 10
        c = (rng.uniform(-4, 4), rng.uniform(-4, 4), 8 + r + k * 17)
        tilt = rot_axis((1, 0, 0), rng.uniform(-0.05, 0.05))
        ring = [tuple(np.asarray(c) + tilt @ np.array([R * math.cos(t), R * math.sin(t), 0])) for t in np.linspace(0, 2 * math.pi, 25)]
        tube(X.mesh(sh), ring, r, nseg=10, caps=(False, False), vlen=2 * math.pi * R)
    return _save('tube_stack', X)


def table_set():
    X = Model()
    wh = S('white', 'lm'); ch = S('white', 'lm', tag='ch')
    revolve(X.mesh(wh), [(14, 0), (12, 2), (3, 4), (3, 28), (36, 28), (37, 30), (36, 31)], n=24)
    disc(X.mesh(wh), 36, 31, up=True, n=24)
    for k in range(4):
        a = math.radians(45 + k * 90)
        cx, cy = 52 * math.cos(a), 52 * math.sin(a)
        Rm = rot_z(a + math.pi)
        sub = Mesh()
        for (lx, ly) in ((-8, -8), (8, -8), (-8, 8), (8, 8)):
            box_mesh(sub, (lx - 1.5, ly - 1.5, 0), (lx + 1.5, ly + 1.5, 17))
        box_mesh(sub, (-10, -10, 15), (10, 10, 18))
        for zz in (24, 30, 36):
            box_mesh(sub, (-10.5, -10, zz - 1.5), (-9, 10, zz + 1.5))
        for ly in (-9, 9):
            box_mesh(sub, (-11, ly - 1.5, 17), (-9, ly + 1.5, 38))
        X.mesh(ch).add(sub, R=Rm, t=(cx, cy, 0))
    return _save('table_set', X)


def adirondack(name, img):
    X = Model()
    wd = S(img, 'lm')
    M = X.mesh(wd)
    sub = Mesh()
    for ly in (-14, 14):                                   # side rails + legs
        beam(sub, (12, ly, 0), (12, ly, 14), 3, 3); beam(sub, (-12, ly, 0), (-14, ly, 12), 3, 3)
        beam(sub, (16, ly, 14), (-16, ly, 10), 3, 4)
        beam(sub, (14, ly, 22), (-10, ly, 22), 6, 2)          # arm rests
        beam(sub, (12, ly, 14), (12, ly, 22), 3, 3)
    for k in range(6):                                      # seat slats
        x = 14 - k * 5.0
        box_mesh(sub, (x - 2, -14, 13 - k * 0.6), (x + 2, 14, 15 - k * 0.6))
    for k in range(5):                                      # back slats, leaning back
        y = -10 + k * 5.0
        beam(sub, (-12, y, 10), (-24, y, 38 + 3 * math.cos((k - 2) * 0.6)), 4, 1.5)
    M.add(sub)
    return _save(name, X)


def lounger():
    X = Model()
    fr = S('white', 'lm', tag='lf'); st = S('strap_blue', 'lm')
    for ly in (-11, 11):
        beam(X.mesh(fr), (36, ly, 12), (-12, ly, 12), 2, 2)
        beam(X.mesh(fr), (-12, ly, 12), (-34, ly, 34), 2, 2)
        for lx in (32, -10):
            beam(X.mesh(fr), (lx, ly, 0), (lx, ly, 12), 2, 2)
    for k in range(10):
        x = 34 - k * 5
        box_mesh(X.mesh(st), (x - 2, -11, 11), (x + 2, 11, 13))
    for k in range(5):
        t = k / 4
        x, z = -14 - 18 * t, 14 + 18 * t
        beam(X.mesh(st), (x, -11, z), (x, 11, z), 4, 1.5)
    return _save('lounger', X)


def lifeguard():
    """tall white lifeguard chair (seat at 120) with a red rescue tube hanging off the back"""
    X = Model()
    wh = S('white', 'lm', tag='lg'); rd = S('rescue_red', 'lm')
    for (x, y) in ((-24, -24), (24, -24), (-24, 24), (24, 24)):
        beam(X.mesh(wh), (x, y, 0), (x * 0.55, y * 0.55, 120), 5, 5)
    for k in range(1, 6):
        z = k * 22
        f = 1 - 0.45 * z / 120
        beam(X.mesh(wh), (24 * f, -24 * f, z), (24 * f, 24 * f, z), 3, 3)
    box_mesh(X.mesh(wh), (-16, -16, 118), (16, 16, 124))
    box_mesh(X.mesh(wh), (-16, -16, 124), (-13, 16, 160))
    box_mesh(X.mesh(rd), (-20, -10, 128), (-17, 10, 150))
    return _save('lifeguard', X)


def hoop():
    """pool basketball hoop: weighted base on the deck, pole leaning over the water (+x), board and rim"""
    X = Model()
    wh = S('white', 'lm', tag='h'); og = S('hoop_orange', 'lm'); bd = S('hoop_board', 'lm')
    box_mesh(X.mesh(wh), (-26, -20, 0), (26, 20, 14))
    tube(X.mesh(wh), [(0, 0, 14), (0, 0, 96), (20, 0, 120)], 4, nseg=8)
    box_mesh(X.mesh(bd), (20, -24, 104), (23, 24, 140))
    ring = [(36 + 10 * math.cos(t), 10 * math.sin(t), 112) for t in np.linspace(0, 2 * math.pi, 17)]
    tube(X.mesh(og), ring, 1.2, nseg=5, caps=(False, False))
    return _save('hoop', X)


def ladder(depth):
    """stainless pool ladder: rails hook over the deck edge (+x side is the deck, water at -x), feet on the floor"""
    X = Model()
    ch = S('chrome', 'chrome')
    for y in (-14, 14):
        p = [(-6, y, -depth), (-6, y, -8), (-4, y, 14), (6, y, 22), (16, y, 18), (18, y, 0)]
        tube(X.mesh(ch), p, 2, nseg=8)
    for k in range(3):
        z = -16 - k * 22
        if z > -depth + 4: box_mesh(X.mesh(ch), (-10, -14, z - 1), (-2, 14, z + 1))
    return _save(f'ladder{depth}', X)


def bucket():
    """tipping bucket on its frame (Tiny Timbers top); origin on the platform, frame along y"""
    X = Model()
    fr = S('metal_teal', 'lm'); bk = S('bucket_yellow', 'lms', v=0.15); rm = S('rescue_red', 'lm', tag='b')
    for y in (-60, 60):
        beam(X.mesh(fr), (0, y, 0), (0, y, 230), 8, 8)
    beam(X.mesh(fr), (0, -64, 226), (0, 64, 226), 8, 8)
    sub = Mesh()
    revolve(sub, [(30, -70), (46, 0)], n=20, u_tiles=2)
    revolve(sub, [(43, 0), (27, -67)], n=20, inward=True, u_tiles=2)
    disc(sub, 30, -70, up=False, n=20)
    rim = Mesh()
    ring = [(46 * math.cos(t), 46 * math.sin(t), 0) for t in np.linspace(0, 2 * math.pi, 21)]
    tube(rim, ring, 3, nseg=5, caps=(False, False))
    Rt = rot_axis((0, 1, 0), math.radians(18))
    X.mesh(bk).add(sub, R=Rt, t=(0, 0, 214)); X.mesh(rm).add(rim, R=Rt, t=(0, 0, 214))
    return _save('bucket', X)


def moose():
    """carved wooden moose (shoulder ~150, antlers to ~290), facing +x; origin = between the hooves"""
    X = Model()
    wd = S('moose_wood', 'lm'); an = S('antler', 'lm'); dk = S('metal_dark', 'lm', tag='eye')
    B = X.mesh(wd)
    ellipsoid(B, (0, 0, 118), 92, 40, 48, nu=20, nv=12)
    ellipsoid(B, (44, 0, 140), 50, 38, 46, nu=16, nv=10)
    ellipsoid(B, (-60, 0, 120), 40, 36, 40, nu=14, nv=8)
    for (x, y, k) in ((56, 20, 1), (56, -20, 1), (-62, 20, -1), (-62, -20, -1)):
        tube(B, [(x, y, 110), (x + 4 * k, y, 70), (x - 2 * k, y, 30), (x + 2 * k, y, 6), (x + 6 * k, y, 0.5)], [13, 10, 8, 7, 9], nseg=10)
    tube(B, [(78, 0, 150), (108, 0, 166), (126, 0, 170)], [30, 24, 20], nseg=12)
    Rh = rot_axis((0, 1, 0), math.radians(25))
    ellipsoid(B, (142, 0, 160), 36, 20, 22, nu=14, nv=8, R=Rh)
    ellipsoid(B, (172, 0, 142), 26, 18, 18, nu=12, nv=8, R=Rh)
    ellipsoid(B, (134, 0, 132), 8, 6, 16, nu=8, nv=6)                       # dewlap
    tube(B, [(-96, 0, 130), (-104, 0, 118)], [7, 4], nseg=6)                # tail
    for s in (-1, 1):
        ellipsoid(B, (128, 20 * s, 182), 6, 12, 5, nu=8, nv=5, R=rot_axis((1, 0, 0), 0.5 * s))
        sphere(X.mesh(dk), (156, 14 * s, 166), 3.2, nu=8, nv=5)
        # palmate antler: a flat paddle with tines, from the brow outward and up
        A = X.mesh(an)
        tube(A, [(130, 12 * s, 182), (126, 34 * s, 194), (118, 52 * s, 204)], [5, 5, 6], nseg=8)
        poly = [(0, 0), (40, -6), (78, 4), (96, 24), (88, 32), (80, 26), (78, 40), (68, 36), (64, 50), (54, 44), (48, 56), (38, 48), (30, 54), (24, 40), (14, 34), (4, 18)]
        sub = Mesh()
        prism(sub, poly, -3, 3, tile=64)
        Rm = rot_z(math.radians(90 * s)) @ rot_axis((1, 0, 0), math.radians(-70 * s)) @ rot_axis((0, 0, 1), math.radians(-15 * s))
        A.add(sub, R=Rm, t=(118, 50 * s, 202))
    return _save('moose', X)


def boulders(name, blobs, seed):
    X = Model()
    rk = S('rockface', 'lm', tag='b')
    rng = np.random.default_rng(seed)
    for (x, y), a, b, h in blobs:
        ph = rng.uniform(0, 6)
        ellipsoid(X.mesh(rk), (x, y, 0), a, b, h, nu=14, nv=8, flat_bottom=0,
                  bump=lambda p, t, ph=ph: 1 + 0.1 * math.sin(3 * t + ph) * math.cos(2 * p) + 0.06 * math.sin(7 * t + 2 * p))
    return _save(name, X)


def rockface(name, u0, u1, zbot_of_u, ztop, holes, axis, plane, outward, seed):
    """displaced rock skin over a vertical face. axis 'x': face plane y = plane, u = x; axis 'y': plane x = plane, u = y.
    outward: +1/-1 along the face normal. zbot_of_u(u) gives the bottom per column. holes [(ua, ub, za, zb)] skip cells."""
    X = Model()
    rk = S('rockface', 'lm')
    TX = _tx()
    nu = int((u1 - u0) / 24) + 1; nz = int((ztop + 240) / 24) + 1
    us = np.linspace(u0, u1, nu)
    rng = np.random.default_rng(seed)
    noi = TX.noise(64, 3, seed) * 0.6 + TX.noise(64, 9, seed + 1) * 0.8
    def disp(u, z):
        i = int((u - u0) / (u1 - u0 + 1e-6) * 63) % 64; j = int((z + 256) / (ztop + 256) * 63) % 64
        strata = 6 * math.sin(z / 23.0 + 2 * math.sin(u / 97.0))
        return min(50.0, max(4.0, 14 + 30 * max(-0.5, noi[j, i]) + strata))
    M = X.mesh(rk)
    P = np.zeros((nz, nu, 3)); UV = np.zeros((nz, nu, 2))
    for j in range(nz):
        for i, u in enumerate(us):
            zb = zbot_of_u(u); t = j / (nz - 1)
            z = zb + (ztop - zb) * t
            d = disp(u, z) * (min(1.0, (z - zb) / 24 + 0.3)) * min(1.0, (ztop - z) / 30 + 0.2)
            if axis == 'x': P[j, i] = (u, plane + outward * d, z)
            else: P[j, i] = (plane + outward * d, u, z)
            UV[j, i] = (u / 256, -z / 256)
    N = grid_normals(P)
    want = np.array([0, outward, 0]) if axis == 'x' else np.array([outward, 0, 0])
    if (N.reshape(-1, 3) @ want).mean() < 0: N = -N
    o = len(M.V)
    for j in range(nz):
        for i in range(nu): M.add_v(P[j, i], N[j, i], UV[j, i])
    for j in range(nz - 1):
        for i in range(nu - 1):
            cu = (us[i] + us[i + 1]) / 2; cz = (P[j, i, 2] + P[j + 1, i, 2]) / 2
            if any(ua <= cu <= ub and za <= cz <= zb for (ua, ub, za, zb) in holes): continue
            a, b, c, d = o + j * nu + i, o + j * nu + i + 1, o + (j + 1) * nu + i, o + (j + 1) * nu + i + 1
            M.tri(a, b, c); M.tri(b, d, c)
    return _save(name, X)


def rocktop(x0, y0, x1, y1, z, seed):
    X = Model()
    rk = S('rockface', 'lm', tag='t')
    TX = _tx()
    noi = TX.noise(32, 2, seed)
    nx, ny = int((x1 - x0) / 32) + 1, int((y1 - y0) / 32) + 1
    P = np.zeros((ny, nx, 3)); UV = np.zeros((ny, nx, 2))
    for j in range(ny):
        for i in range(nx):
            x = x0 + (x1 - x0) * i / (nx - 1); y = y0 + (y1 - y0) * j / (ny - 1)
            edge = min(i, j, nx - 1 - i, ny - 1 - j)
            h = 0 if edge == 0 else 8 + 46 * max(0, noi[j % 32, i % 32] + 0.6) * min(1.0, edge / 3)
            P[j, i] = (x, y, z + h); UV[j, i] = (x / 256, -y / 256)
    N = grid_normals(P)
    if N[..., 2].mean() < 0: N = -N
    X.mesh(rk).grid(P, N, UV)
    return _save('rocktop', X)


def stump():
    """hollow tree-stump lookout (local origin = stump centre on the floor), doorway segments L.ST_DOOR"""
    X = Model()
    bk = S('pine_bark', 'lm', tag='s'); rim = S('log_end', 'lm', tag='s')
    d0, d1, dh = L.ST_DOOR
    R = L.ST_R + 6
    prof = [(R + 70, 0), (R + 34, 30), (R + 10, 90), (R, 200), (R, L.ST_H)]
    rows = []
    for (r, z) in prof:
        rows.append((r, z))
    for z in (dh,):
        rows.append((R, z))
    rows = sorted(rows, key=lambda p: p[1])
    import padshroom_compat as PC
    PC.revolve_grid(X.mesh(bk), rows, 48, holes=[(d0 * 22.5, (d1 + 1) * 22.5, 0, dh)], u_tiles=8,
                    deform=lambda a, r, z: r + 8 * math.sin(a * 11 + z / 60) + (30 * max(0, math.sin(a * 6)) ** 3) * max(0, 1 - z / 140))
    revolve(X.mesh(rim), [(R + 8, L.ST_H + 2), (L.ST_RIN - 6, L.ST_H + 2)], u_tiles=8, n=48)
    rf = lambda z: R + 22
    a0, a1 = d0 * 22.5, (d1 + 1) * 22.5
    pts = []
    for z in np.linspace(0, dh, 6): pts.append((rf(z), a0, z))
    for a in np.linspace(a0, a1, 10)[1:-1]: pts.append((rf(dh), a, dh))
    for z in np.linspace(dh, 0, 6): pts.append((rf(z), a1, z))
    tube(X.mesh(bk), [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z) for (r, a, z) in pts], 22, nseg=8)
    return _save('stump', X)


def net_frame(y0, y1, h=220):
    """cargo-net frame over the lily-pad crossing (local: frame along y from y0 to y1 at x 0)"""
    X = Model()
    wd = S('glulam', 'lm', tag='n'); rp = S('rope', 'rope'); nt = S('net', 'net')
    for y, sg in ((y0, -1), (y1, 1)):
        for dx in (-60, 60):
            beam(X.mesh(wd), (dx, y, 0), (dx * 0.4, y, h + 20), 10, 10)
        beam(X.mesh(wd), (-40, y, h + 10), (40, y, h + 10), 10, 10)
    for dx in (-26, 26):
        cat = [(dx, y, h - 30 * math.sin(math.pi * (y - y0) / (y1 - y0))) for y in np.linspace(y0, y1, 30)]
        tube(X.mesh(rp), cat, 3, nseg=6, caps=(False, False), vlen=64)
    # hanging net strips + grab rings
    for y in np.arange(y0 + 120, y1 - 60, 120):
        zt = h - 30 * math.sin(math.pi * (y - y0) / (y1 - y0))
        X.mesh(nt).poly([(-26, y, zt), (26, y, zt), (26, y, zt - 70), (-26, y, zt - 70)], (0, 1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return _save('net_frame', X)


# ================================================================================================= per-placement generators
_GEN = {}
_POSTS = set()        # world positions of railing / fence posts already built (corners shared by two runs)


def gen_railing(name, pts, h=40, tex='metal_white'):
    """white metal railing along a 3D polyline (world coords). Returns (path, scale, zoff, origin): the model is built
    relative to pts[0] so it can be placed there."""
    X = Model()
    mt = S(tex, 'lms', v=0.12, tag='rail')
    o = np.asarray(pts[0], float)
    P = [np.asarray(p, float) - o for p in pts]
    def post_at(c):
        key = tuple(np.round(c + o, 0))
        if key in _POSTS: return
        _POSTS.add(key)
        box_mesh(X.mesh(mt), (c[0] - 2, c[1] - 2, c[2]), (c[0] + 2, c[1] + 2, c[2] + h))
    for a, b in zip(P, P[1:]):
        Ls = np.linalg.norm((b - a)[:2])
        k = max(1, int(math.ceil(Ls / 64)))
        for t in np.linspace(0, 1, k + 1)[:-1]:
            post_at(a + (b - a) * t)
    post_at(P[-1])
    for hz in (h, h * 0.5):
        tube(X.mesh(mt), [p + np.array([0, 0, hz]) for p in P], 2.2 if hz == h else 1.4, nseg=6, caps=(True, True))
    path, sc, zo = _save(name, X)
    return path, sc, zo, tuple(o)


def gen_ropefence(name, pts, h=44):
    X = Model()
    wd = S('wood_post', 'lm'); rp = S('rope', 'rope', tag='f')
    o = np.asarray(pts[0], float)
    P = [np.asarray(p, float) - o for p in pts]
    for p in P:
        key = tuple(np.round(p + o, 0))
        if key in _POSTS: continue
        _POSTS.add(key)
        revolve(X.mesh(wd), [(6, p[2]), (6, p[2] + h - 4), (3, p[2] + h)], n=8, cx=p[0], cy=p[1])
    for a, b in zip(P, P[1:]):
        cat = [a + (b - a) * t + np.array([0, 0, h - 8 - 12 * math.sin(math.pi * t)]) for t in np.linspace(0, 1, 10)]
        tube(X.mesh(rp), cat, 2, nseg=5, caps=(False, False), vlen=48)
    path, sc, zo = _save(name, X)
    return path, sc, zo, tuple(o)


# ================================================================================================= shaders + make
def shaders():
    s = '// ---- MD3 models (moose_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        t = f'{MD}/{img}'
        if kind in ('lm', 'lms', 'lm2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 70\n'
            if kind == 'lm2s': s += '\tcull none\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind == 'chrome':
            s += (f'{name}\n{{\n\tqer_editorimage {MD}/env\n\tq3map_nonplanar\n\tq3map_shadeAngle 70\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\ttcGen environment\n\t\trgbGen identity\n\t}}\n'
                  f'\t{{\n\t\tmap $lightmap\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
        elif kind == 'glow':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tq3map_surfacelight {opt.get("light", 1200)}\n\tq3map_lightRGB {opt.get("rgb", "1 0.86 0.62")}\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t}}\n}}\n\n')
        elif kind == 'leaf':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n'
                  f'\tsurfaceparm alphashadow\n\tcull none\n\tq3map_vertexScale 1.4\n\tdeformVertexes wave 300 sin 0 1.5 0 0.15\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'net':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen identity\n\t}}\n'
                  f'\t{{\n\t\tmap $lightmap\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\tdepthFunc equal\n\t\trgbGen identity\n\t}}\n}}\n\n')
        elif kind == 'rope':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 70\n'
                  f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
        elif kind == 'addw':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n\t\ttcMod scroll 0 1.6\n\t}}\n}}\n\n')
    return s


# ================================================================================================= Moose Lodge Grill props
def tex_bun(n=128, seed=61):
    TX = _tx()
    a = TX.fill(n, (214, 140, 60), 6, seed)
    r = np.random.default_rng(seed); im = TX.img(a); d = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = r.integers(0, n, 2)
        d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=(250, 236, 200))
    return TX.arr(im)


def tex_stripes(c1, c2, n=128, k=8):
    """vertical stripes (u) for awnings / umbrella canopies"""
    TX = _tx()
    x, y = TX.tile_xy(n)
    m = (np.floor(x * k) % 2 == 0)[..., None]
    return np.where(m, TX.C(c1), TX.C(c2)) + TX.N3(n, 1, 7, 4)


def tex_cooler(w=256, h=256, seed=63):
    """drinks cooler front: lit shelves of cans and bottles behind glass"""
    TX = _tx()
    a = TX.fill(w, (200, 220, 230), 3, seed, h)
    im = TX.img(a); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    cols = [(220, 40, 40), (40, 90, 200), (250, 200, 40), (60, 170, 80), (240, 120, 30), (150, 60, 170)]
    for row in range(4):
        y0 = 12 + row * 60
        d.rectangle((0, y0 + 48, w, y0 + 52), fill=(150, 160, 170))
        x = 6
        while x < w - 20:
            cw = int(r.integers(14, 22)); c = cols[int(r.integers(0, len(cols)))]
            hh = int(r.integers(30, 46))
            d.rounded_rectangle((x, y0 + 48 - hh, x + cw, y0 + 48), radius=4, fill=c)
            d.rectangle((x + 2, y0 + 48 - hh + 10, x + cw - 2, y0 + 48 - hh + 18), fill=(245, 245, 240))
            x += cw + 4
    d.rectangle((0, 0, w - 1, h - 1), outline=(60, 64, 70), width=6)
    d.rectangle((w // 2 - 3, 0, w // 2 + 3, h), fill=(60, 64, 70))
    return TX.arr(im)


def tex_chalk(w=128, h=192, seed=65):
    TX = _tx()
    a = TX.fill(w, (36, 44, 40), 4, seed, h)
    im = TX.img(a); d = ImageDraw.Draw(im)
    d.rectangle((3, 3, w - 4, h - 4), outline=(150, 100, 50), width=6)
    f1 = TX.font(20, True); f2 = TX.font(15)
    d.text((w / 2, 26), 'TODAY', font=f1, fill=(255, 220, 120), anchor='mm')
    for k, line in enumerate(('MOOSE', 'MELT', '- 8.95 -', '', 'S\'MORES', 'SHAKE')):
        d.text((w / 2, 60 + k * 22), line, font=f2, fill=(240, 240, 230) if k != 2 else (140, 220, 160), anchor='mm')
    return TX.arr(im)


def tex_screen(n=64):
    TX = _tx()
    a = TX.fill(n, (40, 160, 90), 2, 67)
    a[::8] *= 0.6
    return a


def tex_pizza(n=128, seed=69):
    TX = _tx()
    a = TX.fill(n, (230, 170, 70), 6, seed)
    r = np.random.default_rng(seed); im = TX.img(a); d = ImageDraw.Draw(im)
    for _ in range(18):
        x, y = r.integers(0, n, 2); d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(180, 40, 30))
    return TX.arr(im)


def griddle():
    """flat-top griddle with burger patties + buns, on the back counter (origin = counter top, front edge +y... faces -y)"""
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='kit'); dk = S('metal_dark', 'lm', tag='kit'); pt = S('patty', 'lm'); bn = S('bun', 'lm')
    ch = S('cheese', 'lm')
    box_mesh(X.mesh(st), (-90, -28, 0), (90, 28, 30))
    box_mesh(X.mesh(dk), (-86, -24, 30), (86, 24, 33))
    box_mesh(X.mesh(st), (-90, 24, 33), (90, 28, 46))                 # splash guard at the back
    for k in range(4):
        box_mesh(X.mesh(dk), (-80 + k * 44, -31, 12), (-70 + k * 44, -28, 22))  # knobs
    for k, x in enumerate((-60, -20, 20)):
        revolve(X.mesh(pt), [(0, 33), (12, 33), (13, 35), (12, 38), (0, 38)], n=12, cx=x, cy=-4)
        if k == 1:
            revolve(X.mesh(ch), [(0, 38.5), (13, 38.5), (13, 39.5), (0, 39.5)], n=4, cx=x, cy=-4)
    for x in (55, 72):
        revolve(X.mesh(bn), [(0, 33), (13, 33), (13, 36), (8, 40), (0, 41)], n=12, cx=x, cy=0)
    return _save('griddle', X)


def fryer():
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='kit'); dk = S('metal_dark', 'lm', tag='kit'); oil = S('oil', 'lms', v=0.3)
    box_mesh(X.mesh(st), (-36, -26, 0), (36, 26, 40), faces='nsewb')
    for x0 in (-32, 2):
        box_mesh(X.mesh(st), (x0, -22, 36), (x0 + 30, 22, 40), faces='nsew')
        box_mesh(X.mesh(oil), (x0 + 2, -20, 30), (x0 + 28, 20, 31), faces='t')
        box_mesh(X.mesh(dk), (x0 + 4, -18, 30), (x0 + 26, 18, 44), faces='nsew')       # basket
        beam(X.mesh(dk), (x0 + 15, -18, 44), (x0 + 15, -40, 52), 3, 3)                  # handle
    box_mesh(X.mesh(st), (-36, -26, 40), (36, -22, 40.5))
    return _save('fryer', X)


def soda():
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='kit'); dk = S('metal_dark', 'lm', tag='kit'); pn = S('screen', 'glow', light=60, rgb='0.6 1 0.7')
    box_mesh(X.mesh(st), (-44, -22, 0), (44, 22, 12))
    box_mesh(X.mesh(dk), (-44, 0, 12), (44, 22, 96))
    box_mesh(X.mesh(dk), (-44, -14, 70), (44, 0, 96))
    X.mesh(pn).quad((-40, -14.5, 74), (40, -14.5, 74), (40, -14.5, 92), (-40, -14.5, 92), tile=80, n=(0, -1, 0))
    for k in range(4):
        x = -30 + k * 20
        tube(X.mesh(st), [(x, -8, 70), (x, -8, 58)], 3, nseg=6)
    cups = [S('cup_red', 'lm'), S('cup_blue', 'lm')]
    for k in range(3):
        revolve(X.mesh(cups[k % 2]), [(0, 12), (6, 12), (8, 34), (0, 34)], n=10, cx=-30 + k * 20, cy=-12)
    return _save('soda', X)


def register():
    X = Model()
    dk = S('metal_dark', 'lm', tag='kit'); sc = S('screen', 'glow', light=40, rgb='0.6 1 0.7')
    box_mesh(X.mesh(dk), (-18, -16, 0), (18, 16, 10))
    beam(X.mesh(dk), (0, 4, 10), (0, 8, 30), 6, 6)
    box_mesh(X.mesh(dk), (-16, 6, 26), (16, 10, 46))
    X.mesh(sc).quad((-14, 5.5, 28), (14, 5.5, 28), (14, 5.5, 44), (-14, 5.5, 44), tile=28, n=(0, -1, 0))
    return _save('register', X)


def pizza_warmer():
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='kit'); gl = S('glass_case', 'lm2s'); pz = S('pizza', 'lm')
    box_mesh(X.mesh(st), (-34, -24, 0), (34, 24, 6))
    box_mesh(X.mesh(st), (-34, -24, 50), (34, 24, 54))
    for (x, y) in ((-34, -24), (34, -24), (-34, 24), (34, 24)):
        box_mesh(X.mesh(st), (x - 2, y - 2, 6), (x + 2, y + 2, 50))
    box_mesh(X.mesh(gl), (-33, -23, 6), (33, 23, 50), faces='new')
    box_mesh(X.mesh(st), (-30, -20, 26), (30, 20, 27))
    for (x, z) in ((-14, 7), (14, 7), (-14, 27), (14, 27)):
        revolve(X.mesh(pz), [(0, z), (13, z), (13, z + 2), (0, z + 2)], n=12, cx=x, cy=0)
    return _save('pizza_warmer', X)


def hood():
    """stainless extractor hood, hangs from the ceiling (origin = top centre, back against +y)"""
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='hood')
    pts_top = [(-110, -10, 0), (110, -10, 0), (110, 56, 0), (-110, 56, 0)]
    # trapezoid body: wide bottom at z -50, narrow top
    b = [(-120, -50, -50), (120, -50, -50), (120, 56, -50), (-120, 56, -50)]
    t = [(-90, -6, -6), (90, -6, -6), (90, 56, -6), (-90, 56, -6)]
    for k in range(4):
        q = [b[k], b[(k + 1) % 4], t[(k + 1) % 4], t[k]]
        n = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0]); n = n / np.linalg.norm(n)
        if n @ (np.mean(q, 0) - [0, 3, -28]) < 0: n = -n
        X.mesh(st).poly(q, n, [(0, 0), (2, 0), (2, 0.5), (0, 0.5)])
    box_mesh(X.mesh(st), (-26, 10, -6), (26, 56, 0))                 # duct stub to the ceiling
    X.mesh(st).quad(*b[::-1], tile=64, n=(0, 0, -1))
    return _save('hood', X)


def cooler():
    """glass-door drinks cooler (252 wide, 64 deep, 152 tall), front -y"""
    X = Model()
    st = S('steel', 'lms', v=0.15, tag='cool'); fr = S('cooler_front', 'glow', light=90, rgb='0.85 0.95 1')
    box_mesh(X.mesh(st), (-126, -32, 0), (126, 32, 152), faces='nsewt')
    X.mesh(fr).quad((-120, -32.5, 8), (120, -32.5, 8), (120, -32.5, 144), (-120, -32.5, 144), tile=240, n=(0, -1, 0))
    for x in (-8, 8):
        beam(X.mesh(st), (x, -36, 50), (x, -36, 100), 3, 3)
    return _save('cooler', X)


def stool():
    X = Model()
    ch = S('chrome', 'chrome', tag='st'); rd = S('rescue_red', 'lm', tag='st')
    revolve(X.mesh(ch), [(16, 0), (14, 2), (3, 4), (3, 54)], n=12)
    ring = [(11 * math.cos(t), 11 * math.sin(t), 22) for t in np.linspace(0, 2 * math.pi, 13)]
    tube(X.mesh(ch), ring, 1.5, nseg=5, caps=(False, False))
    revolve(X.mesh(rd), [(0, 54), (15, 54), (16, 58), (14, 62), (0, 63)], n=14)
    return _save('stool', X)


def aframe():
    X = Model()
    wd = S('wood_post', 'lm', tag='af'); ck = S('chalk', 'lm')
    for sg in (-1, 1):
        a = (0, sg * 22, 0); b = (0, sg * 2, 96)
        for x in (-34, 34):
            beam(X.mesh(wd), (x, a[1], 0), (x, b[1], 96), 4, 4)
        n = np.array([0, sg * 96, 20.0]); n /= np.linalg.norm(n)
        q = [(-30, sg * 21, 6), (30, sg * 21, 6), (30, sg * 3.5, 90), (-30, sg * 3.5, 90)]
        q = [(x, y + sg * 2.5, z) for (x, y, z) in q]
        X.mesh(ck).poly(q, n, [(0, 1), (1, 1), (1, 0), (0, 0)] if sg < 0 else [(1, 1), (0, 1), (0, 0), (1, 0)])
    return _save('aframe', X)


def lantern(drop):
    """hanging lantern (origin = hook at the top), chain `drop` long"""
    X = Model()
    dk = S('metal_dark', 'lm', tag='lan'); gp = S('lantern_glow', 'glow', light=300, rgb='1 0.75 0.45')
    box_mesh(X.mesh(dk), (-1, -1, -drop), (1, 1, 0))
    z = -drop
    revolve(X.mesh(dk), [(0, z), (10, z - 6), (12, z - 8), (0, z - 8)], n=8)
    box_mesh(X.mesh(gp), (-8, -8, z - 30), (8, 8, z - 8), faces='nsew')
    box_mesh(X.mesh(dk), (-10, -10, z - 34), (10, 10, z - 30))
    for (x, y) in ((-9, -9), (9, -9), (-9, 9), (9, 9)):
        box_mesh(X.mesh(dk), (x - 1, y - 1, z - 30), (x + 1, y + 1, z - 8))
    return _save(f'lantern{drop}', X)


def trophy():
    """moose-head trophy on a shield plaque; origin = plaque back centre on the wall, head faces +x"""
    X = Model()
    wd = S('wood_post', 'lm', tag='tr'); mw = S('moose_wood', 'lm', tag='tr'); an = S('antler', 'lm', tag='tr'); dk = S('metal_dark', 'lm', tag='tr')
    sub = Mesh()
    prism(sub, [(-30, -40), (30, -40), (36, 10), (0, 44), (-36, 10)], 0, 6, tile=64)
    X.mesh(wd).add(sub, R=rot_axis((0, 1, 0), math.pi / 2), t=(0, 0, 0))
    ellipsoid(X.mesh(mw), (22, 0, 4), 22, 22, 26, nu=12, nv=8)
    Rh = rot_axis((0, 1, 0), math.radians(35))
    ellipsoid(X.mesh(mw), (50, 0, -8), 32, 16, 16, nu=12, nv=8, R=Rh)
    ellipsoid(X.mesh(mw), (72, 0, -24), 18, 13, 12, nu=10, nv=6, R=Rh)
    for sg in (-1, 1):
        sphere(X.mesh(dk), (52, 12 * sg, 0), 2.5, nu=6, nv=4)
        ellipsoid(X.mesh(mw), (26, 20 * sg, 24), 4, 9, 4, nu=6, nv=4)
        tube(X.mesh(an), [(26, 10 * sg, 26), (24, 26 * sg, 34), (18, 40 * sg, 40)], [4, 4, 5], nseg=6)
        poly = [(0, 0), (30, -4), (52, 4), (60, 18), (54, 22), (48, 18), (46, 28), (40, 24), (36, 34), (30, 28), (22, 32), (16, 22), (6, 18)]
        p2 = Mesh(); prism(p2, poly, -2, 2, tile=64)
        Rm = rot_z(math.radians(90 * sg)) @ rot_axis((1, 0, 0), math.radians(-75 * sg))
        X.mesh(an).add(p2, R=Rm, t=(18, 38 * sg, 40))
    return _save('trophy', X)


def burger():
    """giant fibreglass burger sculpture (~200 across, 150 tall) for the grill's roof"""
    X = Model()
    bn = S('bun', 'lms', v=0.12, tag='big'); pt = S('patty', 'lm', tag='big'); ch = S('cheese', 'lms', v=0.1, tag='big')
    le = S('lettuce', 'lm2s'); tm = S('tomato', 'lms', v=0.15)
    R = 100
    revolve(X.mesh(bn), [(0, 0), (R - 10, 0), (R, 8), (R, 22), (R - 6, 30), (0, 30)], n=32, u_tiles=4)
    revolve(X.mesh(pt), [(0, 30), (R + 2, 30), (R + 6, 36), (R + 4, 52), (R - 2, 56), (0, 56)], n=32, u_tiles=4)
    # cheese: square slice with drooping corners
    P = np.zeros((9, 9, 3)); UV = np.zeros((9, 9, 2))
    for i in range(9):
        for j in range(9):
            u, v = -1 + 2 * i / 8, -1 + 2 * j / 8
            x, y = u * 92, v * 92
            rr = math.hypot(x, y)
            z = 58 - max(0, rr - 80) * 0.9
            P[i, j] = (x, y, z); UV[i, j] = (i / 8, j / 8)
    X.mesh(ch).grid(P, grid_normals(P) * (1 if grid_normals(P)[..., 2].mean() > 0 else -1), UV)
    # lettuce frill
    rows = []
    for k in range(64):
        a = 2 * math.pi * k / 64
        rr = R + 8 + 6 * math.sin(a * 12)
        rows.append((rr * math.cos(a), rr * math.sin(a), 60 + 4 * math.sin(a * 9)))
    rows.append(rows[0])
    P = np.zeros((2, len(rows), 3)); UV = np.zeros((2, len(rows), 2))
    for j, (x, y, z) in enumerate(rows):
        P[0, j] = (x * 0.75, y * 0.75, 62); P[1, j] = (x, y, z); UV[0, j] = (j / 8, 0); UV[1, j] = (j / 8, 1)
    N = np.zeros_like(P); N[..., 2] = 1
    X.mesh(le).grid(P, N, UV)
    for k in range(3):
        a = k * 2.1 + 0.4
        revolve(X.mesh(tm), [(0, 62), (40, 62), (42, 66), (40, 70), (0, 70)], n=16, cx=40 * math.cos(a), cy=40 * math.sin(a))
    # top bun dome with sesame seeds (texture)
    revolve(X.mesh(bn), [(R + 2, 70), (R + 4, 84), (R - 6, 110), (R - 30, 132), (R - 60, 146), (0, 152)], n=32, u_tiles=4, inward=True)
    return _save('burger', X)


def umbrella():
    """patio table with a striped umbrella (canopy r 66 at ~76..100)"""
    X = Model()
    wh = S('white', 'lm', tag='um'); cn = S('canopy', 'lm2s'); ch = S('chrome', 'chrome', tag='um')
    revolve(X.mesh(wh), [(16, 0), (14, 2), (3, 4), (3, 28), (40, 28), (41, 30), (40, 31), (0, 31)], n=24)
    tube(X.mesh(ch), [(0, 0, 31), (0, 0, 98)], 1.5, nseg=6)
    prof = [(0, 100), (34, 92), (64, 80), (66, 76)]
    revolve(X.mesh(cn), prof, n=16, u_tiles=8, inward=True, v_of=lambda r, z: r / 66)
    for k in range(3):
        a = math.radians(45 + k * 120)
        cx, cy = 58 * math.cos(a), 58 * math.sin(a)
        Rm = rot_z(a + math.pi)
        sub = Mesh()
        for (lx, ly) in ((-8, -8), (8, -8), (-8, 8), (8, 8)):
            box_mesh(sub, (lx - 1.5, ly - 1.5, 0), (lx + 1.5, ly + 1.5, 17))
        box_mesh(sub, (-10, -10, 15), (10, 10, 18))
        for zz in (24, 30, 36):
            box_mesh(sub, (-10.5, -10, zz - 1.5), (-9, 10, zz + 1.5))
        X.mesh(wh).add(sub, R=Rm, t=(cx, cy, 0))
    return _save('umbrella', X)


def hvac():
    X = Model()
    mt = S('metal_white', 'lms', v=0.1, tag='hv'); dk = S('metal_dark', 'lm', tag='hv')
    box_mesh(X.mesh(mt), (-48, -36, 0), (48, 36, 56))
    revolve(X.mesh(dk), [(0, 56.5), (26, 56.5), (28, 60), (0, 60)], n=16, cx=-14, cy=0)
    for k in range(6):
        box_mesh(X.mesh(dk), (-46, -37, 8 + k * 7), (46, -36, 11 + k * 7))
    box_mesh(X.mesh(dk), (40, -10, 56), (46, 10, 64))
    return _save('hvac', X)


def string_lights(name, a, b, sag=40, h=150):
    """two wooden posts (bases at a and b, world coords) with a festoon of bulbs between their tops"""
    X = Model()
    wd = S('wood_post', 'lm', tag='sl'); rp = S('rope', 'rope', tag='sl'); bl = S('bulb', 'glow', light=150, rgb='1 0.8 0.5')
    o = np.asarray(a, float); A_ = np.zeros(3); B_ = np.asarray(b, float) - o
    for p in (A_, B_):
        box_mesh(X.mesh(wd), (p[0] - 4, p[1] - 4, p[2]), (p[0] + 4, p[1] + 4, p[2] + h))
    cat = [A_ + (B_ - A_) * t + np.array([0, 0, h - 6 - sag * math.sin(math.pi * t)]) for t in np.linspace(0, 1, 24)]
    tube(X.mesh(rp), cat, 1.2, nseg=4, caps=(False, False))
    for t in np.linspace(0.06, 0.94, 12):
        c = A_ + (B_ - A_) * t + np.array([0, 0, h - 6 - sag * math.sin(math.pi * t) - 7])
        sphere(X.mesh(bl), c, 4, nu=6, nv=4)
    path, sc, zo = _save(name, X)
    return path, sc, zo, tuple(o)


def grill_models():
    TX = _tx()
    d = os.path.join(OUT, MD)
    def sv(nm, a): TX.img(a).convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    sv('steel', TX.steel()); sv('patty', TX.fill(64, (96, 52, 30), 8, 71)); sv('bun', tex_bun()); sv('cheese', TX.fill(64, (250, 190, 40), 4, 73))
    sv('lettuce', TX.fill(64, (90, 180, 60), 8, 75)); sv('tomato', TX.fill(64, (220, 50, 40), 6, 77)); sv('oil', TX.fill(64, (200, 150, 40), 3, 79))
    sv('cup_red', TX.fill(32, (220, 50, 40), 2, 81)); sv('cup_blue', TX.fill(32, (40, 90, 200), 2, 83)); sv('screen', tex_screen())
    sv('glass_case', TX.fill(32, (200, 220, 230), 2, 85)); sv('pizza', tex_pizza()); sv('cooler_front', tex_cooler()); sv('chalk', tex_chalk())
    sv('lantern_glow', TX.fill(32, (255, 200, 120), 2, 87)); sv('canopy', tex_stripes((200, 40, 36), (245, 236, 214)))
    sv('bulb', TX.fill(16, (255, 230, 170), 1, 89))
    for f in (griddle, fryer, soda, register, pizza_warmer, hood, cooler, stool, aframe, trophy, burger, umbrella, hvac):
        f()


def make(out):
    global OUT
    OUT = out
    TX = _tx()
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    def sv(nm, a, alpha=None):
        im = TX.img(a)
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(d, nm + '.tga'))
        else:
            im.convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    sv('pine_bark', TX.bark(512, 47)); a, al = tex_needles(); sv('needles', a, al)
    sv('slide_yellow', tex_slide((246, 196, 30))); sv('slide_yellow2', tex_slide((226, 170, 20)))
    sv('slide_green', tex_slide((40, 150, 70))); sv('slide_green_in', tex_slide((70, 180, 96)))
    sv('slide_blue', tex_slide((40, 140, 220))); sv('slide_teal', tex_slide((40, 190, 180))); sv('slide_kidyel', tex_slide((250, 210, 50)))
    sv('slide_water', tex_water_strip()); sv('metal_white', TX.metal_white()); sv('metal_dark', TX.metal_dark())
    sv('metal_teal', TX.fill(64, (40, 160, 160), 3, 41)); sv('chrome', tex_env()); sv('env', tex_env())
    sv('glulam', TX.glulam()); sv('column_base', tex_column_base()); sv('duct', tex_duct()); sv('glowpanel', tex_glowpanel())
    sv('tube_yellow', tex_tube((250, 200, 30), (40, 110, 220), seed=3)); sv('tube_purple', tex_tube((150, 70, 200), (240, 240, 240), seed=5))
    sv('tube_pink', tex_tube((240, 90, 170), (250, 220, 60), seed=7)); sv('tube_teal', tex_tube((30, 170, 150), (240, 250, 250), seed=9))
    sv('white', tex_white()); sv('strap_blue', TX.fill(64, (40, 90, 200), 3, 43)); sv('rescue_red', TX.fill(64, (220, 40, 30), 3, 45))
    sv('hoop_orange', TX.fill(32, (240, 110, 20), 2, 47)); sv('hoop_board', TX.fill(64, (240, 240, 240), 2, 49))
    sv('bucket_yellow', TX.fill(64, (250, 200, 30), 3, 51)); sv('wood_post', tex_wood(128, 53, (120, 80, 46)))
    sv('adi_wood', tex_wood(128, 55, (170, 120, 70))); sv('adi_green', tex_wood(128, 57, (50, 120, 70))); sv('adi_red', tex_wood(128, 59, (170, 50, 40)))
    sv('log_side', tex_log_side()); sv('log_end', tex_log_end()); sv('gable', tex_gable()); sv('rockface', tex_rockface())
    sv('moose_wood', tex_moose_wood()); sv('antler', tex_antler()); sv('rope', TX.rope_tex()); a, al = tex_net(); sv('net', a, al)
    sv('roof_red', TX.roof_red()); sv('shingles', TX.shingles())
    # fixed models
    pine()
    rafter(); ridge_beam()
    for nm, img, dbl in (('tube1y', 'tube_yellow', False), ('tube1p', 'tube_purple', False), ('tube1k', 'tube_pink', False), ('tube2t', 'tube_teal', True)):
        innertube(nm, img, dbl)
    table_set(); tube_stack(); small_pine(); lounger(); lifeguard(); hoop(); bucket(); moose()
    for nm, img in (('adi_wood', 'adi_wood'), ('adi_green', 'adi_green'), ('adi_red', 'adi_red')):
        adirondack(nm, img)
    boulders('boulders_a', [((0, 0), 60, 50, 50), ((70, 30), 44, 40, 36), ((-50, 40), 40, 36, 30)], 3)
    boulders('boulders_b', [((0, 0), 90, 70, 70), ((100, -30), 60, 54, 50), ((-80, 50), 64, 50, 46), ((30, 90), 50, 46, 40), ((-60, -70), 44, 40, 30)], 5)
    stump()
    grill_models()
    return None


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    import moose_textures as TX
    TX.make_all(o)
