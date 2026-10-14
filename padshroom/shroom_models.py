"""Custom MD3 map objects for wop_padshroom (Shroom Trip). All geometry and art is original and generated here.

    make(out) -> writes models/padshroom/*.md3 (+ an IQM spore ring) and their images, returns the shader text

Scale: Padman scale, ~8u per cm (a 2 m tall golden cap mushroom is the centrepiece). Origin = base centre unless
noted; every model is placed by build_shroom.py, which reads the geometry constants below so the invisible collision
brushes sit just inside the visible surfaces (MD3 surfaces are 4-6u outside the brushes).

  mother        the Mother Mushroom: golden psilocybe ~1570 tall, stem with a doorway, drooping ring, wide cap with an
                umbo, glowing gill fins underneath; holes in the cap for the hatch and three skylights
  amanita_big / amanita_small   fly-agaric cottages: scaly white stems with a door and windows, red caps with warts
  stump         hollow tree stump (bark, root flares, arch into the hollow)
  log           hollow fallen log lying along +x (bark, moss blanket, little mushrooms on top)
  bracket       shelf fungus (walkable shelf on the stump)
  puffball      white puffball (scaled per placement)
  mycena_a/b/c  clusters of thin bioluminescent bonnet mushrooms
  snail         rainbow snail with a spiral shell and eye stalks
  rocks         boulders + iridescent crystals at the waterfall
  frog          rainbow poison-dart frog
  grass         clump of giant grass blades (bank tops)
  lamp          glowing toadstool lamp (house interiors)
  eye           the Void's floating eye (func_rotating model2)
  spores.iqm    ~60 glowing spores on a ring round the Mother cap (func_rotating model2; IQM for the +-1400 reach)
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, save_md3, grid_normals, rot_z, rot_axis, frame
import md3write, iqmtool

MD = 'models/padshroom'
OUT = None
REG = {}
PLACE = {}          # model name -> (path, scale, zoff)

# ================================================================================================= shared geometry
# Mother Mushroom (centre). Collision (build_shroom.py): stem shell = 16-gon wedges, outer radius = MD3 radius - 6,
# inner radius MOTHER_IN; cap = radial bands (see build_shroom.mother()).
MOTHER_STEM = [(0, 404), (40, 414), (120, 384), (260, 344), (500, 314), (800, 304), (1000, 310), (1144, 334)]   # (z, r)
MOTHER_IN = 260
MOTHER_DOOR = (11, 12, 240)                      # door = 16-gon segments 11+12 (south), height
M_STEM_TOP = 1144
M_FLOOR = 1176                                    # chamber floor
M_PLAT = 1460                                     # plateau top (collision)
M_PLATEAU_R = (150, 360)
M_WALL_R = 600                                    # chamber wall


def m_ct(r):
    """Mother cap: collision top surface z at radius r (r >= 150)"""
    if r <= 360: return float(M_PLAT)
    if r <= 800: return 1180 + (800 - r) * 280 / 440
    return 1180 - (r - 800) / 36 * 60


def m_cb(r):
    """Mother cap: collision underside z at radius r"""
    if r <= 340: return 1144.0
    return 1144 - (r - 340) * 60 / 476


M_HATCH = (11, 12)                                # plateau segments left open (hatch pad shaft)
M_SKY = [(4, 380, 560), (9, 380, 560), (14, 380, 560)]   # skylights: segment, r0, r1 in the chamber ceiling

# fly-agaric houses: stem (z, r) MD3, inner radius, cap collision top profile (r, z), underside (r, z), door, windows
AMA_BIG = dict(stem=[(0, 352), (40, 342), (110, 304), (300, 288), (440, 282)], rin=220, h=440,
               top=[(0, 716), (260, 676), (440, 590), (580, 500), (640, 446)], under=[(276, 440), (640, 418)],
               door=(13, 14, 240), windows=[(4, 200, 304), (8, 200, 304)], warts=34, seed=5)
AMA_SMALL = dict(stem=[(0, 252), (40, 238), (100, 216), (260, 204)], rin=150, h=260,
                 top=[(0, 404), (200, 404), (330, 312), (360, 288)], under=[(198, 260), (360, 244)],
                 door=(11, 12, 200), windows=[(3, 96, 176)], warts=16, seed=9)

# hollow stump
STUMP = dict(prof=[(0, 560), (60, 500), (160, 460), (300, 444), (400, 440), (880, 436)], rin=330, h=880, door=(1, 2, 300))
# fallen log (axis along +x from -LOG_L/2 to LOG_L/2 round the model origin, axis height LOG_R)
LOG_R, LOG_IN, LOG_L, LOG_FLOOR = 280, 212, 1400, 130
BRACKET_R = 200
PUFF = (100.0, 150.0)            # puffball radius, height (scale 1)


# ================================================================================================= registry / helpers
def S(img, kind='lm', **opt):
    """register a model shader using models/padshroom/<img> (or a textures/... path)"""
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


def interp_r(prof, z):
    zs = [p[0] for p in prof]; rs = [p[1] for p in prof]
    return float(np.interp(z, zs, rs))


def revolve_grid(M, rows, n_ang=48, holes=(), u_tiles=4.0, v_of=None, inward=False, cx=0.0, cy=0.0, deform=None):
    """surface of revolution through rows [(r, z)...] with angular cells (360/n_ang deg) skipped where a hole
    (a0, a1, z0, z1) in degrees covers the cell. Holes must line up with the cell edges. deform(a, r, z) -> r."""
    rows = np.asarray(rows, float)
    angs = np.linspace(0, 360, n_ang + 1)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=1))])
    tg = np.gradient(rows, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    P = np.zeros((len(rows), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(rows), len(angs), 2))
    for j, a in enumerate(angs):
        ar = math.radians(a); c, s = math.cos(ar), math.sin(ar)
        rr = rows[:, 0] if deform is None else np.array([deform(ar, r, z) for r, z in rows])
        P[:, j] = np.stack([cx + rr * c, cy + rr * s, rows[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = a / 360 * u_tiles
        UV[:, j, 1] = [v_of(r, z) for r, z in rows] if v_of else L / 256
    if deform is not None:
        N = grid_normals(P, inward)
    o = len(M.V)
    for i in range(len(rows)):
        for j in range(len(angs)): M.add_v(P[i, j], N[i, j], UV[i, j])
    nc = len(angs)
    for i in range(len(rows) - 1):
        za, zb = sorted((rows[i, 1], rows[i + 1, 1])); ra, rb = sorted((rows[i, 0], rows[i + 1, 0]))
        for j in range(len(angs) - 1):
            am = (angs[j] + angs[j + 1]) / 2
            skip = False
            for h in holes:
                a0, a1, z0, z1 = h[:4]
                if len(h) > 4: r0, r1 = h[4], h[5]
                else: r0, r1 = -1, 1e9
                inang = a0 <= am <= a1 or a0 <= am + 360 <= a1
                if inang and z0 - 1e-3 <= (za + zb) / 2 <= z1 + 1e-3 and r0 - 1e-3 <= (ra + rb) / 2 <= r1 + 1e-3:
                    skip = True
            if skip: continue
            a, b, c2, d = o + i * nc + j, o + i * nc + j + 1, o + (i + 1) * nc + j, o + (i + 1) * nc + j + 1
            M.tri(a, b, c2); M.tri(b, d, c2)


def refine(rows, extra_z=(), extra_r=(), key='z'):
    """insert interpolated rows at given z (or r) values into a profile [(r, z)...] that is monotonic in that key"""
    rows = list(rows)
    k = 1 if key == 'z' else 0
    vals = extra_z if key == 'z' else extra_r
    for v in vals:
        for i in range(len(rows) - 1):
            a, b = rows[i][k], rows[i + 1][k]
            if min(a, b) + 1e-6 < v < max(a, b) - 1e-6:
                t = (v - a) / (b - a)
                rows.insert(i + 1, (rows[i][0] + (rows[i + 1][0] - rows[i][0]) * t, rows[i][1] + (rows[i + 1][1] - rows[i][1]) * t))
                break
    return rows


def frame_path_on_cyl(rfun, a0, a1, z0, z1, n=10):
    """door/window outline on a (varying radius) cylinder: up the a0 jamb, across at z1, down the a1 jamb"""
    pts = []
    for z in np.linspace(z0, z1, 6): pts.append((rfun(z), a0, z))
    for a in np.linspace(a0, a1, n)[1:-1]: pts.append((rfun(z1), a, z1))
    for z in np.linspace(z1, z0, 6): pts.append((rfun(z), a1, z))
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z) for (r, a, z) in pts]


# ================================================================================================= textures
def _noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, m * 3))
    for i in range(3):
        for j in range(3): big.paste(im, (i * n, j * m))
    a = np.asarray(big.filter(ImageFilter.GaussianBlur(blur)).crop((n, m, 2 * n, 2 * m)), np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def _img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
def _C(c): return np.array(c, np.float32)
def _lerp(a, b, t): return a + (b - a) * t


def _xy(n, m=None):
    m = m or n
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    return x / n, y / m


def _hue(t, s=0.85, v=1.0):
    t = np.mod(t, 1.0); s = np.broadcast_to(s, t.shape); v = np.broadcast_to(v, t.shape)
    i = np.floor(t * 6).astype(int) % 6; f = t * 6 - np.floor(t * 6)
    p = v * (1 - s); q = v * (1 - s * f); u = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, u, v]); g = np.choose(i, [u, v, v, q, p, p]); b = np.choose(i, [p, p, u, v, v, q])
    return np.stack([r, g, b], -1) * 255


def tex_cap_gold(w=512, h=512, seed=1):
    """psilocybe cap: rows = centre (top) to rim (bottom); dark caramel umbo, golden middle, pale rim; radial fibrils"""
    x, y = _xy(w, h)
    c = np.where((y < 0.3)[..., None], _lerp(_C((120, 64, 26)), _C((196, 128, 44)), (y / 0.3)[..., None]),
                 _lerp(_C((196, 128, 44)), _C((246, 214, 150)), np.clip((y - 0.3) / 0.7, 0, 1)[..., None]))
    fib = _noise(w, 1.0, seed, h); fib = np.asarray(_img(fib * 40 + 128).resize((w // 8, h)).resize((w, h)), np.float32) - 128
    c += fib[..., None] * 0.35
    c += _noise(w, 14, seed + 1, h)[..., None] * 10
    spots = np.clip(_noise(w, 4, seed + 2, h) - 1.8, 0, 2)[..., None]        # faint blue bruising
    c = c * (1 - 0.4 * spots) + _C((70, 110, 190)) * 0.4 * spots
    return c


def tex_gills(w=512, h=128, seed=3):
    x, y = _xy(w, h)
    g = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 64)
    c = _lerp(_C((60, 34, 46)), _C((150, 90, 120)), (g ** 2)[..., None]) + _noise(w, 1, seed, h)[..., None] * 6
    return c


def tex_fin(w=256, h=64, seed=4):
    x, y = _xy(w, h)
    c = _lerp(_C((210, 120, 230)), _C((70, 30, 70)), (y ** 0.7)[..., None])
    c += np.sin(x * 2 * math.pi * 12)[..., None] * 10
    return c


def tex_stem_white(w=256, h=512, seed=5):
    x, y = _xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + _C((236, 228, 210))
    fib = _noise(w, 1.0, seed, h); fib = np.asarray(_img(fib * 40 + 128).resize((w, h // 8)).resize((w, h)), np.float32) - 128
    c += fib[..., None] * 0.4
    blue = np.clip(_noise(w, 18, seed + 1, h) - 0.9, 0, 2)[..., None]
    c = c * (1 - 0.5 * blue) + _C((70, 120, 210)) * 0.5 * blue
    return c


def tex_amanita(w=512, h=512, seed=7):
    """fly agaric cap, rows centre -> rim: deep red, orange-red, pale striated rim"""
    x, y = _xy(w, h)
    c = np.where((y < 0.75)[..., None], _lerp(_C((196, 20, 18)), _C((236, 64, 24)), (y / 0.75)[..., None]),
                 _lerp(_C((236, 64, 24)), _C((240, 160, 90)), np.clip((y - 0.75) / 0.25, 0, 1)[..., None]))
    c += _noise(w, 10, seed, h)[..., None] * 9
    stri = (np.sin(x * 2 * math.pi * 90) * np.clip((y - 0.85) * 6, 0, 1))[..., None] * 20
    return c + stri


def tex_wart(n=128, seed=9):
    c = np.zeros((n, n, 3), np.float32) + _C((246, 240, 222)) + _noise(n, 1.5, seed)[..., None] * 8
    return c


def tex_amanita_stem(w=256, h=512, seed=11):
    x, y = _xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + _C((240, 234, 214))
    sc = np.asarray(_img(_noise(w, 2, seed, h) * 50 + 128).resize((w // 2, h // 6)).resize((w, h), Image.NEAREST), np.float32) - 128
    c += sc[..., None] * 0.25
    c[(y > 0.86)] *= 0.92                                   # volva band
    return c


def tex_bark(w=512, h=512, seed=13):
    x, y = _xy(w, h)
    gro = _noise(w, 3, seed, h)
    gro = np.asarray(_img(gro * 50 + 128).resize((w // 6, h // 1)).resize((w, h)), np.float32) / 255
    ridge = np.clip(np.sin(x * 2 * math.pi * 14 + _noise(w, 20, seed + 1, h) * 1.4) * 0.5 + 0.5, 0, 1)
    c = _lerp(_C((48, 34, 26)), _C((120, 94, 72)), (ridge * 0.7 + gro * 0.3)[..., None])
    lich = np.clip(_noise(w, 10, seed + 2, h) - 1.0, 0, 1)[..., None]
    c = c * (1 - lich) + _C((140, 170, 120)) * lich
    return c + _noise(w, 0.8, seed + 3, h)[..., None] * 6


def tex_rings(n=256, seed=15):
    x, y = _xy(n)
    rr = np.hypot(x - 0.5, y - 0.5) * 2 + _noise(n, 12, seed) * 0.02
    ring = 0.5 + 0.5 * np.sin(rr * 2 * math.pi * 22)
    c = _lerp(_C((170, 120, 76)), _C((214, 170, 120)), ring[..., None])
    c = np.where((rr > 0.94)[..., None], _C((70, 50, 36)), c)
    cr = np.abs(np.sin(np.arctan2(y - 0.5, x - 0.5) * 3)) < 0.02                 # drying cracks
    c[cr & (rr < 0.9)] *= 0.6
    return c + _noise(n, 1, seed + 1)[..., None] * 6


def tex_moss_cover(n=256, seed=17):
    c = np.zeros((n, n, 3), np.float32) + _C((70, 120, 50)) + _noise(n, 1.2, seed)[..., None] * 16 + _noise(n, 10, seed + 1)[..., None] * 14
    return c


def tex_bracket(w=256, h=256, seed=19):
    """zoned shelf fungus: concentric bands (rows from the trunk to the rim)"""
    x, y = _xy(w, h)
    band = 0.5 + 0.5 * np.sin(y * 2 * math.pi * 7 + _noise(w, 16, seed, h) * 0.6)
    c = _lerp(_C((150, 80, 30)), _C((236, 170, 90)), band[..., None])
    c = np.where((y > 0.9)[..., None], _C((250, 236, 200)), c)
    return c + _noise(w, 1, seed + 1, h)[..., None] * 8


def tex_puffball(n=256, seed=21):
    c = np.zeros((n, n, 3), np.float32) + _C((240, 236, 226)) + _noise(n, 8, seed)[..., None] * 6
    r = np.random.default_rng(seed); im = _img(c); d = ImageDraw.Draw(im)
    for _ in range(260):
        x, y = r.integers(0, n, 2); s = r.integers(2, 5)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(214, 206, 188))
    return np.asarray(im, np.float32)


def tex_glowcap(col, w=128, h=128):
    x, y = _xy(w, h)
    c = _lerp(_C(col) * 0.45, _C(col), (1 - y)[..., None]) + 255 * np.clip(0.3 - y, 0, 1)[..., None]
    c += np.sin(x * 2 * math.pi * 16)[..., None] * 10 * y[..., None]
    return c


def tex_snail_shell(w=512, h=512, seed=23):
    """rows = along the spiral tube; rainbow growth bands + dark spiral stripe"""
    x, y = _xy(w, h)
    c = _hue(y * 3 + x * 0.1, 0.7, 0.95)
    growth = 0.85 + 0.15 * np.sin(y * 2 * math.pi * 40)
    stripe = np.exp(-((x - 0.5) ** 2) / 0.004)
    c = c * growth[..., None] * (1 - 0.7 * stripe[..., None])
    return c + _noise(w, 1, seed, h)[..., None] * 5


def tex_snail_body(n=256, seed=25):
    c = np.zeros((n, n, 3), np.float32) + _C((150, 140, 110)) + _noise(n, 3, seed)[..., None] * 20
    tex = np.clip(_noise(n, 1.2, seed + 1), -1, 1)[..., None] * 14
    return c + tex


def tex_rock(n=256, seed=27):
    c = np.zeros((n, n, 3), np.float32) + _C((86, 80, 96)) + _noise(n, 6, seed)[..., None] * 18 + _noise(n, 1, seed + 1)[..., None] * 10
    r = np.random.default_rng(seed); im = _img(c); d = ImageDraw.Draw(im)
    for _ in range(90):
        x, y = r.integers(0, n, 2)
        col = tuple(int(v) for v in _hue(np.array(r.random()), 0.6, 1.0))
        d.point((x, y), fill=col); d.point((x + 1, y), fill=col)
    return np.asarray(im, np.float32)


def tex_crystal(n=128, seed=29):
    x, y = _xy(n)
    return _hue(y * 0.6 + 0.65, 0.5, 0.9) + _noise(n, 2, seed)[..., None] * 10


def tex_frog(n=256, seed=31):
    x, y = _xy(n)
    c = _hue(x * 2 + _noise(n, 12, seed) * 0.15, 0.85, 0.95)
    blot = _noise(n, 4, seed + 1) > 1.0
    c[blot] = (20, 16, 30)
    return c


def tex_eye(n=256):
    x, y = _xy(n)
    rr = np.hypot(x - 0.5, y - 0.5) * 2; th = np.arctan2(y - 0.5, x - 0.5)
    c = np.zeros((n, n, 3), np.float32) + _C((246, 240, 236))
    iris = rr < 0.62
    c[iris] = _hue(th[iris] / (2 * math.pi) * 2 + rr[iris], 0.85, 0.9)
    c[rr < 0.24] = (6, 4, 10)
    c[(np.hypot(x - 0.42, y - 0.42) < 0.06)] = (255, 255, 255)
    veins = (np.abs(np.sin(th * 9 + rr * 6)) < 0.04) & (rr > 0.7)
    c[veins] = (220, 90, 110)
    return c


def tex_grass(w=128, h=512, seed=33):
    x, y = _xy(w, h)
    c = _lerp(_C((150, 210, 80)), _C((40, 100, 40)), y[..., None])
    c += (np.abs(np.sin(x * 2 * math.pi * 3)) < 0.08)[..., None] * 25
    return c + _noise(w, 1, seed, h)[..., None] * 6


def tex_wood(n=128, seed=35, col=(110, 70, 40)):
    x, y = _xy(n)
    return _C(col) + np.sin((y * 12 + _noise(n, 8, seed) * 0.4) * 2 * math.pi)[..., None] * 12 + _noise(n, 1, seed + 1)[..., None] * 6


def tex_env(n=128, seed=37):
    """iridescent environment map (oil-slick sheen) for tcGen environment stages"""
    x, y = _xy(n)
    return _hue(x * 1.3 + y * 0.7 + _noise(n, 10, seed) * 0.2, 0.55, 0.85)


def tex_spore(n=64):
    x, y = _xy(n)
    m = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1)
    return np.zeros((n, n, 3), np.float32) + 255 * (m ** 1.5)[..., None]


def tex_skirt(w=256, h=128, seed=39):
    x, y = _xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + _C((232, 224, 214)) + _noise(w, 1.5, seed, h)[..., None] * 10
    c *= (1 - 0.3 * y)[..., None]
    return c


# ================================================================================================= models
def mother():
    X = Model()
    cap = S('cap_gold', 'lma', amp=0.06, breathe=3); gill = S('gills', 'lm'); fin = S('fin', 'glow2s', light=0)
    stem = S('stem_white', 'lm'); skirt = S('skirt', 'lm2s'); wood = S('doorwood', 'lm')
    # stem with the doorway (south)
    d0, d1, dh = MOTHER_DOOR
    a0, a1 = d0 * 22.5, (d1 + 1) * 22.5
    rows = [(r, z) for (z, r) in MOTHER_STEM]
    rows = refine(rows, extra_z=(dh, 20, 80, 180, 360, 650, 900))
    rows = sorted(rows, key=lambda p: p[1])
    revolve_grid(X.mesh(stem), rows, 48, holes=[(a0, a1, 0, dh)], u_tiles=6,
                 deform=lambda a, r, z: r + 4 * math.sin(a * 5 + z / 90.0))
    rf = lambda z: interp_r(MOTHER_STEM, z) + 12
    tube(X.mesh(wood), frame_path_on_cyl(rf, a0, a1, 0, dh), 16, nseg=8, utiles=1, vlen=128)
    # drooping ring (annulus) - two-sided membrane
    ring = [(306, 860), (380, 852), (436, 826), (466, 786), (474, 740), (468, 714)]
    revolve(X.mesh(skirt), ring, u_tiles=8, n=48, rfun=lambda a, r, z: r + (8 * math.sin(a * 9) if z < 800 else 0))
    # cap top: umbo, plateau, cone, rolled rim; holes for the hatch and the skylights
    top = [(0, 1562), (40, 1558), (75, 1544), (105, 1520), (126, 1496), (140, 1474), (150, 1464), (250, 1464), (360, 1464),
           (380, 1451), (480, 1388), (560, 1337), (600, 1311), (700, 1248), (800, 1184), (822, 1168), (838, 1144),
           (844, 1116), (838, 1094), (822, 1080)]
    holes = [(M_HATCH[0] * 22.5, (M_HATCH[1] + 1) * 22.5, 1463, 1465, 150, 360)]
    for (k, r0, r1) in M_SKY:
        holes.append((k * 22.5, (k + 1) * 22.5, 0, 9999, r0, r1))
    vof = lambda r, z: min(0.999, r / 860.0)
    revolve_grid(X.mesh(cap), top, 48, holes=holes, u_tiles=8, v_of=vof, inward=True,
                 deform=lambda a, r, z: r + (10 * math.sin(a * 7) + 6 * math.sin(a * 13) if r > 790 else 0))
    # underside (gill plane) + fins
    under = [(822, 1080), (700, 1095), (560, 1113), (440, 1128), (340, 1140), (330, 1146)]
    revolve(X.mesh(gill), under, u_tiles=16, n=48, inward=True, rfun=lambda a, r, z: r + (10 * math.sin(a * 7) + 6 * math.sin(a * 13) if r > 790 else 0))
    F = X.mesh(fin)
    for k in range(96):
        a = math.radians(k * 3.75 + 1.0); c, s = math.cos(a), math.sin(a)
        rs = np.linspace(346, 812, 9)
        zt = np.interp(rs, [340, 440, 560, 700, 822], [1139, 1127, 1112, 1094, 1079]) - 1
        dep = 46 * np.sin(np.pi * (rs - 346) / 466) + 2
        P = np.zeros((2, 9, 3)); UV = np.zeros((2, 9, 2))
        for j, r in enumerate(rs):
            P[0, j] = (r * c, r * s, zt[j]); P[1, j] = (r * c, r * s, zt[j] - dep[j])
            UV[0, j] = (j / 8, 0); UV[1, j] = (j / 8, 1)
        N = np.zeros_like(P); N[..., 0] = -s; N[..., 1] = c
        F.grid(P, N, UV)
    return _save('mother', X)


def amanita(name, D):
    X = Model()
    cap = S('amanita', 'lms', v=0.12, breathe=2.5); wart = S('wart', 'lm'); stem = S('amanita_stem', 'lm'); gill = S('wart', 'lm', tag='g')
    fin = S('wart', 'lm2s', tag='f'); frame_ = S('frame_green', 'lm')
    rows = [(r, z) for (z, r) in D['stem']]
    d0, d1, dh = D['door']
    holes = [(d0 * 22.5, (d1 + 1) * 22.5, 0, dh)]
    ez = [dh]
    for (k, z0, z1) in D['windows']:
        holes.append((k * 22.5, (k + 1) * 22.5, z0, z1)); ez += [z0, z1]
    rows = sorted(refine(rows, extra_z=ez), key=lambda p: p[1])
    revolve_grid(X.mesh(stem), rows, 48, holes=holes, u_tiles=5, v_of=lambda r, z: 1 - z / (D['h'] * 1.15))
    rf = lambda z: interp_r(D['stem'], z) + 10
    tube(X.mesh(frame_), frame_path_on_cyl(rf, d0 * 22.5, (d1 + 1) * 22.5, 0, dh), 14, nseg=8, vlen=128)
    for (k, z0, z1) in D['windows']:
        p = frame_path_on_cyl(rf, k * 22.5, (k + 1) * 22.5, z0, z1)
        p = p + [p[0]]
        tube(X.mesh(frame_), p, 10, nseg=6, vlen=128)
    # cap top (collision profile + 4, rim raised a little)
    top = [(r, z + 4) for (r, z) in D['top']]
    R = top[-1][0]
    top = top + [(R + 6, top[-1][1] - 14), (R + 6, D['under'][-1][1] + 2), (R - 2, D['under'][-1][1] - 4)]
    revolve_grid(X.mesh(cap), top, 48, u_tiles=4, v_of=lambda r, z: min(0.999, r / (R + 10)), inward=True)
    under = [(R - 2, D['under'][-1][1] - 4), (D['under'][0][0] - 4, D['under'][0][1] - 4), (D['stem'][-1][1] - 2, D['h'] - 2)]
    revolve(X.mesh(gill), under, u_tiles=12, n=48, inward=True)
    Fm = X.mesh(fin)
    r0g, z0g = D['under'][0]; r1g, z1g = D['under'][-1]
    for k in range(64):
        a = math.radians(k * 5.625 + 1); c, s = math.cos(a), math.sin(a)
        rs = np.linspace(r0g + 6, r1g - 8, 6)
        zt = np.interp(rs, [r0g, r1g], [z0g - 5, z1g - 5])
        dep = 22 * np.sin(np.pi * (rs - rs[0]) / (rs[-1] - rs[0])) + 1
        P = np.zeros((2, 6, 3)); UV = np.zeros((2, 6, 2))
        for j, r in enumerate(rs):
            P[0, j] = (r * c, r * s, zt[j]); P[1, j] = (r * c, r * s, zt[j] - dep[j]); UV[0, j] = (j / 5, 0); UV[1, j] = (j / 5, 1)
        N = np.zeros_like(P); N[..., 0] = -s; N[..., 1] = c
        Fm.grid(P, N, UV)
    # warts: flattened white bumps sitting on the cap
    rng = np.random.default_rng(D['seed'])
    W = X.mesh(wart)
    tr = [p[0] for p in D['top']]; tz = [p[1] for p in D['top']]
    for i in range(D['warts']):
        r = R * math.sqrt(rng.uniform(0.0, 0.85)); a = rng.uniform(0, 2 * math.pi)
        z = np.interp(r, tr, tz) + 4
        sz = rng.uniform(18, 34) * (R / 640) ** 0.5 + 10
        slope = (np.interp(r + 5, tr, tz) - np.interp(r - 5, tr, tz)) / 10
        tilt = math.atan(-slope)
        Rm = rot_z(a) @ rot_axis((0, 1, 0), -tilt) if r > 1 else np.eye(3)
        ellipsoid(W, (r * math.cos(a), r * math.sin(a), z + sz * 0.45 - 3 + sz * abs(math.sin(tilt))), sz, sz * rng.uniform(0.7, 1.0), sz * 0.45, nu=10, nv=6, R=Rm)
    return _save(name, X)


def stump():
    X = Model()
    bark = S('bark', 'lm'); rim = S('rings', 'lm', tag='r')
    D = STUMP
    d0, d1, dh = D['door']
    rows = sorted(refine([(r, z) for (z, r) in D['prof']], extra_z=(dh, 30, 100, 220, 600, 760)), key=lambda p: p[1])
    rows = [(r + 6, z) for (r, z) in rows]
    def dfm(a, r, z):
        return r + 10 * math.sin(a * 11 + z / 70) + (40 * max(0, math.sin(a * 6)) ** 3) * max(0, 1 - z / 260)
    revolve_grid(X.mesh(bark), rows, 48, holes=[(d0 * 22.5, (d1 + 1) * 22.5, 0, dh)], u_tiles=8, deform=dfm)
    # bark rim ring on top (thin lip showing the bark thickness)
    rt = D['prof'][-1][1]
    revolve(X.mesh(rim), [(rt + 8, D['h'] + 2), (rt - 14, D['h'] + 2)], u_tiles=8, n=48)
    # arch: rough wood framing the opening
    rf = lambda z: interp_r([(z_, r_ + 20) for (z_, r_) in D['prof']], z)
    tube(X.mesh(bark), frame_path_on_cyl(rf, d0 * 22.5, (d1 + 1) * 22.5, 0, dh, n=12), 26, nseg=8, vlen=256)
    return _save('stump', X)


def log():
    X = Model()
    bark = S('bark', 'lm', tag='l'); moss = S('moss_cover', 'lma', amp=0.04)
    R = LOG_R + 12
    nx, na = 29, 48
    P = np.zeros((nx, na + 1, 3)); UV = np.zeros((nx, na + 1, 2))
    for i in range(nx):
        x = LOG_L * i / (nx - 1) - LOG_L / 2
        for j in range(na + 1):
            a = 2 * math.pi * j / na
            rr = R + 4 * math.sin(a * 9 + x / 120) + 3 * math.sin(x / 47)
            P[i, j] = (x, rr * math.cos(a), LOG_R + rr * math.sin(a))
            UV[i, j] = (j / na * 6, x / 512)
    N = grid_normals(P); cen = np.zeros_like(P); cen[..., 0] = P[..., 0]; cen[..., 2] = LOG_R
    if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
    X.mesh(bark).grid(P, N, UV)
    # moss blanket over the top (+-50 deg), slightly proud of the bark, ragged edge
    ma = np.radians(np.linspace(40, 140, 13))
    P = np.zeros((nx, len(ma), 3)); UV = np.zeros_like(P[..., :2])
    for i in range(nx):
        x = LOG_L * i / (nx - 1) - LOG_L / 2
        for j, a in enumerate(ma):
            edge = 1 if j in (0, len(ma) - 1) else 0
            rr = R + 10 - edge * (6 + 4 * math.sin(x / 33))
            P[i, j] = (x, rr * math.cos(a), LOG_R + rr * math.sin(a))
            UV[i, j] = (x / 256, j / 4)
    N = grid_normals(P); cen = np.zeros_like(P); cen[..., 0] = P[..., 0]; cen[..., 2] = LOG_R
    if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
    X.mesh(moss).grid(P, N, UV)
    # end rings (bark lip at both ends)
    for x0, sgn in ((-LOG_L / 2, -1), (LOG_L / 2, 1)):
        Mm = X.mesh(bark)
        for j in range(na):
            a0, a1 = 2 * math.pi * j / na, 2 * math.pi * (j + 1) / na
            q = [(x0, rr * math.cos(a), LOG_R + rr * math.sin(a)) for (rr, a) in ((R + 4, a0), (R + 4, a1), (LOG_R - 14, a1), (LOG_R - 14, a0))]
            Mm.poly(q, (sgn, 0, 0), [(0, 0), (0.1, 0), (0.1, 0.05), (0, 0.05)])
    return _save('log', X)


def bracket():
    X = Model()
    sh = S('bracket', 'lma', amp=0.05)
    M = X.mesh(sh)
    # half disc shelf (+x out from the trunk), rows = radial bands, flattish top, rounded rim
    angs = np.radians(np.linspace(-90, 90, 25))
    prof = [(0, 30), (60, 34), (130, 30), (180, 22), (BRACKET_R, 6), (BRACKET_R - 6, -10), (150, -14), (40, -16), (0, -16)]
    P = np.zeros((len(prof), len(angs), 3)); UV = np.zeros((len(prof), len(angs), 2))
    for i, (r, z) in enumerate(prof):
        for j, a in enumerate(angs):
            rr = r * (1 + 0.06 * math.sin(a * 5))
            P[i, j] = (rr * math.cos(a), rr * 1.25 * math.sin(a), z)
            UV[i, j] = (j / 24 * 2, min(0.999, r / BRACKET_R) if z >= 0 else 0.95)
    M.grid(P, grid_normals(P, True), UV)
    return _save('bracket', X)


def puffball():
    X = Model()
    sh = S('puffball', 'lma', amp=0.05, breathe=2)
    r, h = PUFF
    prof = [(0, 0), (0.62 * r, 2), (0.92 * r, 0.22 * h), (r, 0.5 * h), (0.86 * r, 0.82 * h), (0.5 * r, 0.97 * h), (0.0, h)]
    revolve(X.mesh(sh), prof, u_tiles=3, n=24, rfun=lambda a, rr, z: rr * (1 + 0.04 * math.sin(a * 5 + z / 20)))
    # little nipple on top
    sphere(X.mesh(sh), (0, 0, h - 2), 10, nu=8, nv=5)
    return _save('puffball', X)


def mycena(seed, cols):
    """cluster of thin bioluminescent bonnet mushrooms; cols = list of shader names"""
    X = Model()
    rng = np.random.default_rng(seed)
    stem = S('glowstem', 'glow', wave='wave sin 0.75 0.15 0 0.3')
    n = rng.integers(5, 8)
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(0, 70) if i else 0
        bx, by = d * math.cos(a), d * math.sin(a)
        H = rng.uniform(70, 230) if i else 250.0
        lean = rng.uniform(-0.25, 0.25, 2)
        path = [(bx + lean[0] * H * t * t, by + lean[1] * H * t * t, H * t) for t in np.linspace(0, 1, 7)]
        tube(X.mesh(stem), path, np.linspace(7, 4, 7) * (H / 200) ** 0.5 + 1.5, nseg=6, caps=(False, False), vlen=64)
        top = np.asarray(path[-1])
        cr = rng.uniform(26, 46) * (H / 180) ** 0.5
        bell = [(0, cr * 0.95), (cr * 0.45, cr * 0.85), (cr * 0.8, cr * 0.45), (cr, 0.0), (cr * 0.95, -cr * 0.08), (cr * 0.4, -cr * 0.05), (0, -cr * 0.04)]
        Mc = X.mesh(cols[i % len(cols)])
        sub = Mesh()
        revolve(sub, bell, u_tiles=2, n=14, inward=True, v_of=lambda r, z: min(0.99, max(0.0, 0.5 - z / (2.2 * cr))))
        Mc.add(sub, t=top - (0, 0, cr * 0.2))
    return X


def mycena_models():
    cs = [S('glow_cyan', 'glow', wave='wave sin 0.8 0.2 0 0.25', light=60, rgb='0.4 1 0.9'),
          S('glow_mag', 'glow', wave='wave sin 0.8 0.2 0.33 0.25', light=60, rgb='1 0.4 0.9'),
          S('glow_lime', 'glow', wave='wave sin 0.8 0.2 0.66 0.25', light=60, rgb='0.7 1 0.4')]
    out = []
    for k, (seed, c) in enumerate(((3, cs), (8, cs[1:] + cs[:1]), (14, cs[2:] + cs[:2]))):
        out.append(_save('mycena_' + 'abc'[k], mycena(seed, c)))
    return out


def snail():
    X = Model()
    shell = S('snail_shell', 'lms', v=0.25); body = S('snail_body', 'lms', v=0.12, tag='b'); eye = S('eye', 'lm', tag='s')
    # body: long tapered slug on the ground along +x (head at +x), foot flat on z 0
    B = X.mesh(body)
    ellipsoid(B, (0, 0, 60), 430, 120, 90, nu=24, nv=12, flat_bottom=-60)
    # neck rising to the head
    tube(B, [(300, 0, 70), (400, 0, 120), (470, 0, 190), (520, 0, 230)], [95, 80, 70, 62], nseg=14, caps=(False, True))
    # eye stalks + eyes
    for s in (-1, 1):
        p = [(520, 18 * s, 260), (555, 40 * s, 330), (585, 62 * s, 400), (600, 76 * s, 450)]
        tube(B, p, [16, 13, 11, 10], nseg=8, caps=(False, False))
        sphere(X.mesh(eye), (604, 80 * s, 462), 26, nu=12, nv=8)
    # shell: planispiral tube in the x-z plane (axis along y), sitting on the back
    path, rad = [], []
    cx, cz = -40.0, 300.0
    for t in np.linspace(0, 3.2 * math.pi, 70):
        k = math.exp(-0.21 * t)
        R = 220 * k
        path.append((cx + R * math.cos(t + 0.3), 0.0, cz + R * math.sin(t + 0.3)))
        rad.append(130 * k + 8)
    tube(X.mesh(shell), path, rad, nseg=20, caps=(True, True), utiles=1, vlen=1400)
    return _save('snail', X)


def rocks():
    X = Model()
    rk = S('rock', 'lm'); cr = S('crystal', 'lms', v=0.45, tag='c')
    rng = np.random.default_rng(41)
    blobs = [((0, 0), 300, 260, 300), ((260, 120), 220, 200, 230), ((-240, 140), 210, 180, 210), ((90, -200), 200, 170, 170), ((-120, -160), 160, 150, 140)]
    for (x, y), a, b, h in blobs:
        ph = rng.uniform(0, 6)
        ellipsoid(X.mesh(rk), (x, y, 0), a, b, h, nu=18, nv=10, flat_bottom=0,
                  bump=lambda p, t, ph=ph: 1 + 0.08 * math.sin(3 * t + ph) * math.cos(2 * p) + 0.05 * math.sin(7 * t + 2 * p))
    # crystals: hexagonal prisms with pointed tips sprouting from the boulders
    for (x, y, z, L, rr, tilt, az) in ((40, 10, 250, 230, 38, 0.2, 0.3), (-60, 60, 240, 170, 30, 0.45, 2.1), (120, -40, 220, 150, 26, 0.5, 5.0),
                                       (250, 140, 190, 140, 26, 0.35, 0.9), (-250, 160, 170, 160, 30, 0.4, 2.8), (80, -200, 140, 120, 22, 0.5, 4.4)):
        d = np.array([math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)])
        b1, b2 = frame(d)
        base = np.array([x, y, z - 30.0])
        ring0 = [base + rr * (math.cos(t) * b1 + math.sin(t) * b2) for t in np.linspace(0, 2 * math.pi, 7)[:-1]]
        ring1 = [p + d * L for p in ring0]
        tip = base + d * (L + rr * 1.6)
        M = X.mesh(cr)
        for k in range(6):
            q = [ring0[k], ring0[(k + 1) % 6], ring1[(k + 1) % 6], ring1[k]]
            n = ((q[0] + q[1]) / 2 - base); n -= d * (n @ d); M.poly(q, n, [(0, 1), (0.3, 1), (0.3, 0), (0, 0)])
            t3 = [ring1[k], ring1[(k + 1) % 6], tip]
            n2 = np.cross(t3[1] - t3[0], t3[2] - t3[0]); c0 = sum(t3) / 3
            if n2 @ (c0 - (base + d * L)) < 0: n2 = -n2
            M.poly(t3, n2, [(0, 0.2), (0.3, 0.2), (0.15, 0)])
    return _save('rocks', X)


def frog():
    X = Model()
    sk = S('frog', 'lms', v=0.3); ey = S('eye', 'lm', tag='f')
    B = X.mesh(sk)
    ellipsoid(B, (0, 0, 70), 120, 80, 62, nu=18, nv=10, flat_bottom=-60, R=rot_axis((0, 1, 0), -0.35))
    ellipsoid(B, (95, 0, 112), 62, 66, 42, nu=14, nv=8)
    for s in (-1, 1):
        tube(B, [(-60, 60 * s, 60), (-100, 120 * s, 50), (-40, 140 * s, 10), (30, 150 * s, 8)], [30, 26, 18, 14], nseg=8)
        tube(B, [(60, 50 * s, 50), (90, 80 * s, 26), (110, 90 * s, 8)], [18, 14, 11], nseg=8)
        sphere(X.mesh(ey), (110, 42 * s, 146), 24, nu=10, nv=7)
    return _save('frog', X)


def grass():
    X = Model()
    g = S('grass', 'lm2s')
    rng = np.random.default_rng(51)
    M = X.mesh(g)
    for i in range(10):
        a = rng.uniform(0, 2 * math.pi); d = rng.uniform(0, 70)
        bx, by = d * math.cos(a), d * math.sin(a)
        H = rng.uniform(700, 1450); w0 = rng.uniform(40, 70)
        bend = rng.uniform(0.12, 0.3); az = rng.uniform(-0.7, 0.7)
        dx, dy = math.cos(az), math.sin(az); px, py = -dy, dx
        n = 9
        P = np.zeros((n, 2, 3)); UV = np.zeros((n, 2, 2))
        for k in range(n):
            t = k / (n - 1)
            off = bend * H * t * t
            cxx, cyy, cz = bx + dx * off, by + dy * off, H * t * (1 - 0.25 * bend * t)
            w = w0 * (1 - t) + 2
            P[k, 0] = (cxx - px * w / 2, cyy - py * w / 2, cz); P[k, 1] = (cxx + px * w / 2, cyy + py * w / 2, cz)
            UV[k, 0] = (0, 1 - t); UV[k, 1] = (1, 1 - t)
        N = grid_normals(P)
        M.grid(P, N, UV)
    return _save('grass', X)


def lamp():
    X = Model()
    st = S('amanita_stem', 'lm', tag='l'); cap = S('glow_lamp', 'glow', wave='wave sin 0.9 0.1 0 0.4', light=120, rgb='1 0.7 0.4')
    revolve(X.mesh(st), [(26, 0), (22, 10), (14, 40), (12, 120), (14, 150)], n=12)
    revolve(X.mesh(cap), [(0, 210), (40, 200), (66, 170), (72, 148), (60, 144), (0, 150)], n=16, v_of=lambda r, z: 0.4, inward=True)
    return _save('lamp', X)


def eye_orb():
    """the Void's eye (model2 on a func_rotating, so +-512 and lightingDiffuse/fullbright shaders)"""
    X = Model()
    e = S('eye', 'glow', tag='o', wave='wave sin 0.9 0.1 0 0.2'); rg = S('crystal', 'glow', tag='r', wave='wave sin 0.7 0.3 0 0.15')
    # sphere with the iris facing +x: map u/v so the iris (texture centre) sits at +x
    E = X.mesh(e)
    nu, nv, r = 24, 16, 90.0
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        p = math.pi * i / nv - math.pi / 2
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            v = np.array([r * math.cos(p) * math.cos(t), r * math.cos(p) * math.sin(t), r * math.sin(p)])
            P[i, j] = v
            if v[0] > 0.2 * r: UV[i, j] = (0.5 + 0.62 * v[1] / r, 0.5 - 0.62 * v[2] / r)
            else: UV[i, j] = (0.03, 0.03 + 0.1 * (i / nv))
    E.grid(P, grid_normals(P), UV)
    tube(X.mesh(rg), [(150 * math.cos(t), 150 * math.sin(t), 0) for t in np.linspace(0, 2 * math.pi, 33)], 9, nseg=6, caps=(False, False))
    tube(X.mesh(rg), [(0, 175 * math.cos(t), 175 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 33)], 7, nseg=6, caps=(False, False))
    return _save('eye', X)


def spores_iqm(z0, seed=61):
    """glowing spores on a ring round the Mother cap (IQM: +-1400 from the rotation origin); returns path"""
    rng = np.random.default_rng(seed)
    meshes = []
    for mat_i, mat in enumerate((S('spore_c', 'add', col='0.4 1 0.9'), S('spore_m', 'add', col='1 0.4 0.9'), S('spore_y', 'add', col='1 0.9 0.4'))):
        for part in range(2):
            M = Mesh()
            for i in range(12):
                a = rng.uniform(0, 2 * math.pi); R = rng.uniform(980, 1380); z = rng.uniform(880, 2050) - z0
                sphere(M, (R * math.cos(a), R * math.sin(a), z), rng.uniform(9, 20), nu=8, nv=5)
            V = np.array(M.V); Nn = np.array(M.N); ST = np.array(M.ST); T = np.array(M.T)
            meshes.append(dict(name=f'spores{mat_i}{part}', material=mat, verts=V, normals=Nn, st=ST, tris=T))
    path = f'{MD}/spores.iqm'
    iqmtool.save(os.path.join(OUT, path), meshes)
    return path


# ================================================================================================= shaders + make
def shaders():
    s = '// ---- MD3 models (shroom_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        t = img if img.startswith('textures/') else f'{MD}/{img}'
        if kind in ('lm', 'lma', 'lms', 'lm2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 75\n'
            if kind == 'lm2s': s += '\tcull none\n'
            if opt.get('breathe'): s += f'\tdeformVertexes wave 400 sin 0 {opt["breathe"]} 0 0.12\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lma':
                amp = opt.get('amp', 0.05)
                s += (f'\t{{\n\t\tmap textures/padshroom/aura\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin {amp} {amp} 0 0.2\n'
                      '\t\ttcMod scale 0.5 0.5\n\t\ttcMod scroll 0.02 0.03\n\t}\n')
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind in ('glow', 'glow2s'):
            wave = opt.get('wave', 'identity')
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n'
            if opt.get('light'): s += f'\tq3map_surfacelight {opt["light"]}\n\tq3map_lightRGB {opt.get("rgb", "1 1 1")}\n'
            if kind == 'glow2s': s += '\tcull none\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {wave}\n\t}}\n'
            s += (f'\t{{\n\t\tmap textures/padshroom/aura\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.15 0.15 0 0.3\n'
                  '\t\ttcMod scroll 0.05 0.08\n\t}\n}\n\n')
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {MD}/spore\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tcull none\n'
                  f'\t{{\n\t\tmap {MD}/spore\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.7 0.3 {np.random.default_rng(len(name)).random():.2f} 0.4\n'
                  f'\t}}\n}}\n\n')
    return s


def make(out):
    global OUT
    OUT = out
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    sv = lambda nm, a: _img(a).convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    sv('cap_gold', tex_cap_gold()); sv('gills', tex_gills()); sv('fin', tex_fin()); sv('stem_white', tex_stem_white())
    sv('skirt', tex_skirt()); sv('doorwood', tex_wood()); sv('frame_green', tex_wood(128, 36, (60, 140, 70)))
    sv('amanita', tex_amanita()); sv('wart', tex_wart()); sv('amanita_stem', tex_amanita_stem())
    sv('bark', tex_bark()); sv('rings', tex_rings()); sv('moss_cover', tex_moss_cover()); sv('bracket', tex_bracket())
    sv('puffball', tex_puffball()); sv('glowstem', tex_glowcap((200, 255, 240)))
    sv('glow_cyan', tex_glowcap((90, 255, 230))); sv('glow_mag', tex_glowcap((255, 90, 230))); sv('glow_lime', tex_glowcap((190, 255, 80)))
    sv('glow_lamp', tex_glowcap((255, 170, 90)))
    sv('snail_shell', tex_snail_shell()); sv('snail_body', tex_snail_body()); sv('rock', tex_rock()); sv('crystal', tex_crystal())
    sv('frog', tex_frog()); sv('eye', tex_eye()); sv('grass', tex_grass()); sv('env', tex_env()); sv('spore', tex_spore())
    mother(); amanita('amanita_big', AMA_BIG); amanita('amanita_small', AMA_SMALL); stump(); log(); bracket(); puffball()
    mycena_models(); snail(); rocks(); frog(); grass(); lamp(); eye_orb()
    return shaders()


def tex_bark_flat(w, h, seed): return tex_bark(w, h, seed)


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    make(o)
    spores_iqm(1500)
    import md3tool
    for fn in sorted(os.listdir(os.path.join(o, MD))):
        if fn.endswith('.md3'):
            m = md3tool.load(os.path.join(o, MD, fn))
            V = np.concatenate([s['verts'] for s in m['surfaces']])
            print(fn, sum(len(s['verts']) for s in m['surfaces']), 'verts', sum(len(s['tris']) for s in m['surfaces']), 'tris',
                  V.min(0).round(1), V.max(0).round(1), PLACE.get(fn[:-4]))
