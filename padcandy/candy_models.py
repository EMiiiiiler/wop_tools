"""Custom MD3 map objects for wop_padcandy (Candy Garden). All geometry and art is original and generated here.

    make(out) -> writes models/padcandy/*.md3 and their images, returns the shader text

Scale: ~200u per metre (Padman is the size of a gummy bear). Origin = base centre unless noted. build_candy.py reads
the geometry constants below (and layout.py) so the invisible collision brushes sit just inside the visible surfaces.

  redcap        red fly agaric with big white spots (walk under it; pad onto the cap)
  yellowhouse   yellow spotted mushroom house: hollow stem with a door and two windows, cap you can stand on
  flowertree_w / flowertree_e   crepe-paper flower trees: patchwork pompom domes on a bark trunk
  gumtree       gumball tree: green crepe leaves hung with glossy gumballs
  lolli_*       giant lollipops (spiral, starburst, flower, rainbow rings, pinwheel), disc_* spinning discs
  cane / cane_arch   striped candy canes and a candy-cane arch over the path
  jaw_a/b/c     swirl-striped jawbreakers (scaled per placement)
  urn           black iron urn on a pedestal heaped with gumballs
  buttercup     buttercup flowers with drinkable cups
  twisty        twisted rainbow candy stalk with a starburst on top
  shed / pump / deck_frame / pipes_deck   pump house on the iron deck with its coloured pipes into the river
  augpipe       the glass suction pipe from the river to the summit (follows the real jump-pad flight)
  waterfall / splash / outlet   the chocolate waterfall, its splash ring, the copper outlet pipe on the summit
  boat          pink candy boat with a swan figurehead
  bridge        candy-cane bridge
  pedestal / lamppost   stone pillar lamp, iron garden lamps
  truss / wallpipes     iron roof trusses, pipe runs high on the walls
  crystal_a/b   glowing rock candy clusters (cave)
  bottle_*/fan  fizzy lifting bottles and the ceiling fan (secret)
  bonbon_a/b, chocbar, cupcake, flower_a/b/c, toad_a/b   cover and garden dressing
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, save_md3, grid_normals, rot_z, rot_axis, frame, arc_path
import layout as L

MD = 'models/padcandy'
OUT = None
REG = {}
PLACE = {}          # model name -> (path, scale, zoff)
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# ================================================================================================= shared geometry
REDCAP_STEM = [(0, 96), (30, 100), (90, 86), (200, 76), (320, 72), (372, 78)]          # (z, r) MD3 stem
REDCAP_COL = dict(stem_r=70, stem_z=330, layers=[(286, 330, 300, 380), (300, 380, 246, 432), (246, 432, 168, 464)], top=464)
YH = dict(stem=[(0, 312), (40, 300), (120, 276), (300, 264), (420, 268)], rin=196, h=420,
          top=[(0, 642), (240, 630), (400, 582), (520, 500), (584, 440)], under=[(272, 420), (584, 394)],
          door=(11, 12, 232), windows=[(3, 150, 256), (7, 150, 256)])
FT = dict(trunk_r=(44, 30), trunk_z=660, cz=860, a=410, c=280, top=1100,
          col=[(170, 600, 360, 700), (360, 700, 404, 900), (404, 900, 250, 1100)])
GT = dict(trunk_z=520, cz=780, a=300, c=210, col=[(150, 560, 290, 660), (290, 660, 300, 860), (300, 860, 150, 980)])
LOLLI_H, LOLLI_R, LOLLI_T = 340, 100, 16
CANE_H = 400
ARCH_W, ARCH_H = 520, 640
JAW_R = 64
URN_H = 262
SHED_DOOR = 112                      # door width (centred on the south wall), height 224
BOAT_L, BOAT_B = 440, 176            # candy boat length (x) and beam (y)
BRIDGE_L, BRIDGE_HW, BRIDGE_Z = 672, 104, 48


# ================================================================================================= registry / helpers
def S(img, kind='lm', **opt):
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
    return float(np.interp(z, [p[0] for p in prof], [p[1] for p in prof]))


def lathe(M, rows, n=48, inward=False, uvf=None, u_tiles=4.0, vlen=256.0, deform=None, holes=(), cx=0.0, cy=0.0, a0=0.0, a1=360.0):
    """surface of revolution through rows [(r, z)...]; uvf(P) -> (u, v) for planar mapping (else u = angle, v = arc
    length); holes: angular cells (a0, a1, z0, z1) skipped; deform(a_rad, r, z) -> r"""
    rows = np.asarray(rows, float)
    angs = np.linspace(a0, a1, n + 1)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=1))])
    tg = np.gradient(rows, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    P = np.zeros((len(rows), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(rows), len(angs), 2))
    for j, a in enumerate(angs):
        ar = math.radians(a); c, s = math.cos(ar), math.sin(ar)
        rr = rows[:, 0] if deform is None else np.array([deform(ar, r, z) for r, z in rows])
        P[:, j] = np.stack([cx + rr * c, cy + rr * s, rows[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = (a - a0) / 360 * u_tiles; UV[:, j, 1] = Ls / vlen
    if deform is not None:
        N2 = grid_normals(P)
        if (N2 * N).sum() < 0: N2 = -N2
        N = N2
    if uvf is not None:
        for i in range(len(rows)):
            for j in range(len(angs)): UV[i, j] = uvf(P[i, j])
    if not holes:
        M.grid(P, N, UV); return
    o = len(M.V)
    for i in range(len(rows)):
        for j in range(len(angs)): M.add_v(P[i, j], N[i, j], UV[i, j])
    nc = len(angs)
    for i in range(len(rows) - 1):
        zm = (rows[i, 1] + rows[i + 1, 1]) / 2
        for j in range(nc - 1):
            am = (angs[j] + angs[j + 1]) / 2
            if any((h[0] <= am <= h[1]) and h[2] - 1e-3 <= zm <= h[3] + 1e-3 for h in holes): continue
            a, b, c2, d = o + i * nc + j, o + i * nc + j + 1, o + (i + 1) * nc + j, o + (i + 1) * nc + j + 1
            M.tri(a, b, c2); M.tri(b, d, c2)


def refine(rows, extra_z=()):
    rows = list(rows)
    for v in extra_z:
        for i in range(len(rows) - 1):
            a, b = rows[i][1], rows[i + 1][1]
            if min(a, b) + 1e-6 < v < max(a, b) - 1e-6:
                t = (v - a) / (b - a)
                rows.insert(i + 1, (rows[i][0] + (rows[i + 1][0] - rows[i][0]) * t, v)); break
    return rows


def frame_path_on_cyl(rfun, a0, a1, z0, z1, n=10):
    pts = []
    for z in np.linspace(z0, z1, 6): pts.append((rfun(z), a0, z))
    for a in np.linspace(a0, a1, n)[1:-1]: pts.append((rfun(z1), a, z1))
    for z in np.linspace(z1, z0, 6): pts.append((rfun(z), a1, z))
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z) for (r, a, z) in pts]


def blob(M, c, r, seed, nu=14, nv=9, amp=0.18, freq=5, R=np.eye(3), squash=1.0, uvs=1.0):
    """crumpled ball (crepe-paper pompom / leaf cluster)"""
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, 6)
    def bump(p, t):
        return 1 + amp * (0.5 * math.sin(freq * t + ph[0]) * math.cos(freq * p + ph[1]) + 0.3 * math.sin(2.3 * freq * t + ph[2] + 3 * p)
                          + 0.2 * math.sin(3.7 * freq * p + ph[3] + 2 * t))
    ellipsoid(M, c, r, r, r * squash, nu, nv, R=R, bump=bump, u0=rng.uniform(0, 1), u1=rng.uniform(0, 1) + 2 * uvs, v0=0, v1=uvs)


def oriented(M_src, R, t):
    out = Mesh(); out.add(M_src, R, t); return out


def gumball(M, c, r, nu=12, nv=8):
    sphere(M, c, r, nu, nv)


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


def _emboss(h, k=1.0):
    gx = np.roll(h, -1, 1) - np.roll(h, 1, 1); gy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    return np.clip(0.85 + k * (gx * 0.6 - gy * 0.8), 0.35, 1.4)


def tex_crepe(col, seed, n=256):
    """crumpled crepe paper: folded ridges, soft highlights"""
    h = np.abs(_noise(n, 3.5, seed)) * 0.9 + np.abs(_noise(n, 1.6, seed + 1)) * 0.5 + _noise(n, 9, seed + 2) * 0.4
    sh = _emboss(h, 0.55)
    c = _C(col)[None, None, :] * sh[..., None]
    c += np.clip(h - 1.4, 0, 1)[..., None] * 40
    return c


def tex_cap(base, rim, spot, n=512, seed=1, nspots=26, rs=(0.035, 0.07)):
    """mushroom cap seen from above (planar UV over the cap disc): base colour fading to the rim, painted round spots"""
    x, y = _xy(n)
    rr = np.hypot(x - 0.5, y - 0.5) * 2
    c = _lerp(_C(base), _C(rim), np.clip((rr - 0.55) / 0.45, 0, 1)[..., None]) + _noise(n, 12, seed)[..., None] * 8
    im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed + 5)
    pts = []
    tries = 0
    while len(pts) < nspots and tries < 4000:
        tries += 1
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0, 0.88)) * 0.5
        px, py = 0.5 + r * math.cos(a), 0.5 + r * math.sin(a)
        s = rng.uniform(*rs) * (1 - 0.4 * r)
        if any(math.hypot(px - qx, py - qy) < s + qs + 0.012 for (qx, qy, qs) in pts): continue
        pts.append((px, py, s))
    for (px, py, s) in pts:
        jit = [(px + s * (1 + 0.12 * math.sin(k * 1.7 + px * 40)) * math.cos(k * 2 * math.pi / 18),
                py + s * (1 + 0.12 * math.sin(k * 1.7 + px * 40)) * math.sin(k * 2 * math.pi / 18)) for k in range(18)]
        d.polygon([(u * n, v * n) for (u, v) in jit], fill=tuple(int(v) for v in spot))
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    return a + _noise(n, 1, seed + 9)[..., None] * 5


def tex_stem(n=256, seed=5, col=(242, 232, 206)):
    x, y = _xy(n)
    c = np.zeros((n, n, 3), np.float32) + _C(col)
    fib = _noise(n, 1.0, seed); fib = np.asarray(_img(fib * 40 + 128).resize((n, n // 10)).resize((n, n)), np.float32) - 128
    return c + fib[..., None] * 0.35 + _noise(n, 14, seed + 1)[..., None] * 6


def tex_gills(w=512, h=128, col=(236, 220, 186)):
    x, y = _xy(w, h)
    g = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 72)
    return _lerp(_C(col) * 0.7, _C(col), (g ** 2)[..., None])


def tex_bark(w=256, h=512, seed=13, col0=(70, 54, 44), col1=(140, 118, 96)):
    x, y = _xy(w, h)
    ridge = np.clip(np.sin(x * 2 * math.pi * 10 + _noise(w, 22, seed, h) * 1.6) * 0.5 + 0.5, 0, 1)
    gro = np.asarray(_img(_noise(w, 2, seed + 1, h) * 50 + 128).resize((w // 5, h)).resize((w, h)), np.float32) / 255
    c = _lerp(_C(col0), _C(col1), (ridge * 0.7 + gro * 0.3)[..., None])
    return c + _noise(w, 0.8, seed + 3, h)[..., None] * 6


def tex_stripes(cols, n=256, k=6, soft=0.04, gloss=True, seed=0):
    """vertical stripes cycling through cols (k repeats across the width); used on twisted tubes and spheres"""
    x, y = _xy(n)
    t = (x * k * len(cols)) % len(cols)
    idx = np.floor(t).astype(int) % len(cols); f = t - np.floor(t)
    C = np.array([_C(c) for c in cols])
    c = C[idx]
    nxt = C[(idx + 1) % len(cols)]
    edge = np.clip((f - (1 - soft)) / soft, 0, 1)[..., None]
    c = c * (1 - edge) + nxt * edge
    if gloss: c = c + np.clip(np.sin(y * math.pi * 2 * 3) - 0.85, 0, 1)[..., None] * 160
    return c + _noise(n, 1, seed)[..., None] * 3


def tex_lolli(design, n=512, seed=0):
    x, y = _xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; th = np.arctan2(dy, dx)
    if design == 'spiral':
        v = np.sin(th * 2 + r * 26)
        c = np.where((v > 0)[..., None], _C((246, 120, 30)), _C((252, 214, 60)))
        c = np.where((np.sin(th * 2 + r * 26 + 1.2) > 0.85)[..., None], _C((210, 40, 30)), c)
    elif design == 'star':
        spikes = np.cos(th * 12) * 0.5 + 0.5
        c = _hue(th / (2 * math.pi) * 3 + 0.05, 0.85, 1.0)
        c = np.where((r < 0.25 + 0.5 * spikes ** 3)[..., None], _hue(th / (2 * math.pi) * 3 + 0.55, 0.9, 0.95), c)
        c = np.where((r < 0.18)[..., None], _C((120, 40, 150)), c)
        c = np.where((np.abs(r - 0.18) < 0.012)[..., None], _C((250, 230, 90)), c)
        c = np.where((r > 0.9)[..., None], _C((240, 60, 40)), c)
    elif design == 'flower':
        c = np.zeros((n, n, 3), np.float32) + _C((250, 222, 70))
        lat = (np.abs(np.sin(dx * 40)) < 0.12) | (np.abs(np.sin(dy * 40)) < 0.12)
        c = np.where((lat & (r < 0.92))[..., None], _C((246, 160, 40)), c)
        for k in range(8):
            a = k * math.pi / 4; px, py = 0.27 * math.cos(a) * 0.5 * 2, 0.27 * math.sin(a)
            m = np.hypot(dx - 0.27 * math.cos(a), dy - 0.27 * math.sin(a)) < 0.055
            c = np.where(m[..., None], _C((230, 40, 40)), c)
        for k in range(12):
            a = k * math.pi / 6 + 0.26
            m = np.hypot(dx - 0.4 * math.cos(a), dy - 0.4 * math.sin(a)) < 0.03
            c = np.where(m[..., None], _C((220, 50, 60)), c)
        c = np.where((r < 0.12)[..., None], _C((230, 40, 40)), c)
        c = np.where((r > 0.93)[..., None], _C((236, 120, 30)), c)
    elif design == 'rings':
        c = _hue(r * 3.2, 0.8, 1.0)
        c = np.where((np.abs(np.sin(r * math.pi * 9.6)) < 0.08)[..., None], _C((255, 255, 255)), c)
    else:   # pinwheel swirl
        v = np.sin(th * 5 + r * 9)
        c = np.where((v > 0)[..., None], _C((244, 90, 160)), _C((252, 240, 246)))
    c = c.astype(np.float32)
    # glossy candy glaze: soft highlight band + edge shade
    c = c * (1 - 0.25 * np.clip(r - 0.85, 0, 1)[..., None] * 6)
    c += np.clip(1 - np.hypot(dx + 0.18, dy + 0.2) * 5, 0, 1)[..., None] * 70
    return c + _noise(n, 1, seed)[..., None] * 3


def tex_swirlball(cols, n=256, seed=0):
    """jawbreaker: UV u = longitude, v = latitude; diagonal bands -> swirl on the sphere"""
    x, y = _xy(n)
    t = (x * 4 + y * 2.2 + 0.08 * np.sin(y * 18)) * len(cols)
    idx = np.floor(t).astype(int) % len(cols); f = t - np.floor(t)
    C = np.array([_C(c) for c in cols]); c = C[idx]
    c = c * (0.9 + 0.1 * np.cos(f * 2 * math.pi))[..., None]
    c += (np.sin(x * 2 * math.pi * 40 + y * 30) * 6)[..., None]
    return c + _noise(n, 1.0, seed)[..., None] * 4


def tex_solid(col, n=64, grain=3, seed=0):
    return np.zeros((n, n, 3), np.float32) + _C(col) + _noise(n, 1.2, seed)[..., None] * grain + _noise(n, 8, seed + 1)[..., None] * grain


def tex_iron(col=(46, 50, 54), n=256, seed=7, rivets=True):
    c = tex_solid(col, n, 5, seed)
    rust = np.clip(_noise(n, 6, seed + 3) - 1.3, 0, 1)[..., None]
    c = c * (1 - rust * 0.6) + _C((110, 60, 34)) * rust * 0.6
    if rivets:
        im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
        for i in range(8):
            for v in (6, n - 8):
                u = (i + 0.5) * n / 8
                d.ellipse((u - 3, v - 3, u + 3, v + 3), fill=tuple(int(a * 1.5) for a in col))
                d.ellipse((v - 3, u - 3, v + 3, u + 3), fill=tuple(int(a * 1.5) for a in col))
        d.line((0, 2, n, 2), fill=tuple(int(a * 0.6) for a in col), width=2)
        d.line((2, 0, 2, n), fill=tuple(int(a * 0.6) for a in col), width=2)
        c = np.asarray(im, np.float32)
    return c


def tex_chocfall(w=256, h=512, seed=21):
    """flowing chocolate: long vertical streaks of light and dark brown (tileable; scrolls down)"""
    x, y = _xy(w, h)
    r = np.random.default_rng(seed)
    n1 = np.zeros(w * 4, np.float32)
    for k in range(1, 40):
        n1 += r.normal() / k ** 0.9 * np.sin(2 * math.pi * (k * np.arange(w * 4) / (w * 4) + r.random()))
    n1 = (n1 - n1.mean()) / n1.std()
    def samp(u):
        return np.interp((u % 1) * w * 4, np.arange(w * 4), n1)
    wob = 0.03 * np.sin(2 * math.pi * (y * 2 + x * 3)) + 0.02 * np.sin(2 * math.pi * (y * 5 + 0.3))
    v = samp(x + wob) * 0.6 + samp(x * 3 + wob * 2 + 0.37) * 0.3
    v *= 0.85 + 0.15 * np.sin(2 * math.pi * (y * 3 + samp(x * 2) * 0.2))
    c = _lerp(_C((66, 34, 16)), _C((146, 84, 42)), np.clip(0.5 + v * 0.35, 0, 1)[..., None])
    c += np.clip(v - 1.0, 0, 1.5)[..., None] * 90                 # glossy highlights
    return c


def tex_choc_surface(n=256, seed=23):
    h = _noise(n, 6, seed) + _noise(n, 2, seed + 1) * 0.3
    c = _lerp(_C((70, 38, 18)), _C((128, 72, 36)), np.clip(0.5 + h * 0.25, 0, 1)[..., None])
    c += np.clip(h - 1.2, 0, 1)[..., None] * 90
    return c


def tex_crystal(col, n=128, seed=0):
    x, y = _xy(n)
    c = _lerp(_C(col) * 0.55, _C(col), (1 - y)[..., None]) + np.clip(0.25 - np.abs(x - 0.5), 0, 1)[..., None] * 300
    return c + _noise(n, 2, seed)[..., None] * 10


def tex_glass(n=64, col=(200, 225, 240)):
    x, y = _xy(n)
    return np.zeros((n, n, 3), np.float32) + _C(col) * (0.8 + 0.2 * np.sin(x * 6))[..., None]


def tex_env(n=128, seed=37):
    x, y = _xy(n)
    c = _lerp(_C((255, 250, 240)), _C((120, 150, 200)), y[..., None]) * (0.6 + 0.4 * np.clip(np.sin(x * 9) + 0.3, 0, 1))[..., None]
    c += np.clip(1 - np.hypot(x - 0.3, y - 0.25) * 6, 0, 1)[..., None] * 255
    return c


def tex_glow(col, n=64):
    x, y = _xy(n)
    m = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1)[..., None]
    return _C(col) * (0.75 + 0.25 * m) + 255 * m ** 3 * 0.4


def tex_wafer(n=256, seed=31):
    x, y = _xy(n)
    g = (np.abs(np.sin(x * math.pi * 12)) < 0.12) | (np.abs(np.sin(y * math.pi * 12)) < 0.12)
    c = np.where(g[..., None], _C((176, 120, 60)), _C((222, 170, 98)))
    return c.astype(np.float32) + _noise(n, 1, seed)[..., None] * 6


def tex_chocbar(n=256, seed=33):
    x, y = _xy(n)
    gx = np.abs(((x * 4) % 1) - 0.5); gy = np.abs(((y * 4) % 1) - 0.5)
    e = np.maximum(gx, gy)
    c = _lerp(_C((92, 50, 24)), _C((60, 30, 14)), np.clip((e - 0.38) * 9, 0, 1)[..., None])
    c += np.clip(0.42 - e, 0, 1)[..., None] * 30
    return c + _noise(n, 1, seed)[..., None] * 3


def tex_wrapper(col, text, w=512, h=256, seed=0):
    c = tex_solid(col, w, 4, seed)[:h]
    c = np.zeros((h, w, 3), np.float32) + _C(col) + _noise(w, 1.5, seed, h)[..., None] * 4
    im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((0, 18, w, 30), fill=(250, 210, 80)); d.rectangle((0, h - 30, w, h - 18), fill=(250, 210, 80))
    f = ImageFont.truetype(FONTB, 76)
    tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, h / 2 - 46), text, font=f, fill=(255, 240, 200))
    return np.asarray(im, np.float32)


def tex_ticket(w=512, h=256):
    x, y = _xy(w, h)
    c = _lerp(_C((250, 214, 90)), _C((200, 140, 30)), (0.5 + 0.5 * np.sin(x * 14 + y * 6))[..., None])
    im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w - 10, h - 10), outline=(120, 70, 10), width=6)
    f = ImageFont.truetype(FONTB, 54); f2 = ImageFont.truetype(FONTB, 28)
    for (t, ff, yy) in (('GOLDEN TICKET', f, 60), ('ADMIT ONE TO THE CANDY GARDEN', f2, 150)):
        tw = d.textlength(t, font=ff); d.text(((w - tw) / 2, yy), t, font=ff, fill=(100, 50, 10))
    return np.asarray(im, np.float32)


def tex_label(text, col, fg, w=256, h=128):
    im = _img(np.zeros((h, w, 3)) + _C(col)).convert('RGB'); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONTB, 30)
    lines = text.split('\n')
    for i, t in enumerate(lines):
        tw = d.textlength(t, font=f); d.text(((w - tw) / 2, h / 2 - 20 * len(lines) + i * 40), t, font=f, fill=fg)
    d.rectangle((4, 4, w - 4, h - 4), outline=fg, width=3)
    return np.asarray(im, np.float32)


def tex_leaf(n=128, seed=41, col=(70, 150, 50)):
    x, y = _xy(n)
    vein = (np.abs(x - 0.5) < 0.02) | (np.abs(np.sin((y + np.abs(x - 0.5)) * 30)) < 0.05)
    c = np.where(vein[..., None], _C(col) * 1.3, _C(col)) + _noise(n, 2, seed)[..., None] * 8
    return c.astype(np.float32)


def tex_frosting(col, n=256, seed=43):
    h = np.abs(_noise(n, 4, seed)) + _noise(n, 12, seed + 1) * 0.5
    c = _C(col)[None, None] * _emboss(h, 0.3)[..., None]
    return c + np.clip(h - 1.2, 0, 1)[..., None] * 60


def tex_cupcase(n=256, col=(240, 120, 170)):
    x, y = _xy(n)
    f = 0.75 + 0.25 * np.abs(np.sin(x * math.pi * 24))
    return np.zeros((n, n, 3), np.float32) + _C(col) * f[..., None]


def tex_swan(n=256, seed=45):
    h = _noise(n, 3, seed)
    c = np.zeros((n, n, 3), np.float32) + _C((248, 246, 240)) + h[..., None] * 6
    x, y = _xy(n)
    feather = np.abs(np.sin(x * 30 + np.sin(y * 20) * 2)) < 0.08
    c[feather] *= 0.93
    return c


def tex_boat(n=256, seed=47):
    x, y = _xy(n)
    c = np.zeros((n, n, 3), np.float32) + _C((246, 150, 190))
    c = np.where((np.abs(y - 0.12) < 0.04)[..., None], _C((255, 245, 250)), c)
    dots = (np.hypot(((x * 16) % 1) - 0.5, ((y * 8) % 1) - 0.5) < 0.18) & (y > 0.25)
    c = np.where(dots[..., None], _C((255, 220, 236)), c)
    return c.astype(np.float32) + _noise(n, 1, seed)[..., None] * 3


def tex_stone(n=256, seed=49, col=(206, 192, 160)):
    c = tex_solid(col, n, 8, seed)
    x, y = _xy(n)
    jo = (np.abs(((y * 2) % 1) - 0.5) > 0.47) | (np.abs((((x * 2) + 0.5 * (np.floor(y * 2) % 2)) % 1) - 0.5) > 0.47)
    c[jo] *= 0.72
    return c


# ================================================================================================= models
def redcap():
    X = Model()
    stem = S('stem_cream', 'lm'); cap = S('cap_red', 'lms', v=0.09); gill = S('gills_cream', 'lm'); skirt = S('stem_cream', 'lm2s', tag='s')
    rows = [(r, z) for (z, r) in REDCAP_STEM]
    rows = sorted(refine(rows, (10, 60, 140, 260)), key=lambda p: p[1])
    lathe(X.mesh(stem), rows, 32, u_tiles=4, deform=lambda a, r, z: r + 3 * math.sin(a * 6 + z / 50))
    # skirt (drooping ring) at z ~290
    lathe(X.mesh(skirt), [(72, 302), (100, 296), (118, 280), (124, 262)], 32, u_tiles=6,
          deform=lambda a, r, z: r + (5 * math.sin(a * 9) if z < 285 else 0))
    R = 308
    top = [(0, 476), (60, 475), (130, 468), (190, 454), (238, 434), (272, 410), (296, 380), (308, 350), (306, 334), (296, 324)]
    lathe(X.mesh(cap), top, 48, inward=True, uvf=lambda p: (0.5 + p[0] / (2 * R), 0.5 - p[1] / (2 * R)),
          deform=lambda a, r, z: r + (4 * math.sin(a * 5) if r > 250 else 0))
    under = [(296, 324), (240, 340), (170, 354), (110, 364), (76, 372)]
    lathe(X.mesh(gill), under, 48, inward=True, u_tiles=10)
    return _save('redcap', X)


def toadstool(name, base, rim, spot, h, R, seed):
    """small decorative mushrooms (vertex lit)"""
    X = Model()
    capm = S(name + '_cap', 'vl'); stem = S('stem_cream', 'vl', tag='t')
    lathe(X.mesh(stem), [(R * 0.28, 0), (R * 0.24, h * 0.5), (R * 0.22, h * 0.86)], 12)
    top = [(0, h * 1.18), (R * 0.5, h * 1.13), (R * 0.85, h * 1.0), (R, h * 0.88), (R * 0.96, h * 0.84)]
    lathe(X.mesh(capm), top, 20, inward=True, uvf=lambda p: (0.5 + p[0] / (2 * R), 0.5 - p[1] / (2 * R)))
    lathe(X.mesh(stem), [(R * 0.96, h * 0.84), (R * 0.3, h * 0.86)], 20, inward=True)
    return _save(name, X)


def yellowhouse():
    X = Model()
    D = YH
    cap = S('cap_yellow', 'lms', v=0.08); stem = S('stem_house', 'lm'); gill = S('gills_cream', 'lm', tag='y')
    frame_ = S('wood_red', 'lm'); wart = S('spot_orange', 'lm')
    rows = [(r, z) for (z, r) in D['stem']]
    d0, d1, dh = D['door']
    holes = [(d0 * 22.5, (d1 + 1) * 22.5, 0, dh)]
    ez = [dh]
    for (k, z0, z1) in D['windows']:
        holes.append((k * 22.5, (k + 1) * 22.5, z0, z1)); ez += [z0, z1]
    rows = sorted(refine(rows, extra_z=ez + [20, 80, 200, 340]), key=lambda p: p[1])
    rows = [(r + 6, z) for (r, z) in rows]
    lathe(X.mesh(stem), rows, 48, holes=holes, u_tiles=5, vlen=420)
    rf = lambda z: interp_r(D['stem'], z) + 14
    tube(X.mesh(frame_), frame_path_on_cyl(rf, d0 * 22.5, (d1 + 1) * 22.5, 0, dh), 16, nseg=8, vlen=128)
    for (k, z0, z1) in D['windows']:
        p = frame_path_on_cyl(rf, k * 22.5, (k + 1) * 22.5, z0, z1); p = p + [p[0]]
        tube(X.mesh(frame_), p, 11, nseg=6, vlen=128)
    top = [(r, z + 5) for (r, z) in D['top']]
    R = top[-1][0]
    top = top + [(R + 8, top[-1][1] - 16), (R + 8, D['under'][-1][1] + 4), (R - 2, D['under'][-1][1] - 4)]
    lathe(X.mesh(cap), top, 64, inward=True, uvf=lambda p: (0.5 + p[0] / (2 * (R + 12)), 0.5 - p[1] / (2 * (R + 12))),
          deform=lambda a, r, z: r + (8 * math.sin(a * 7) + 4 * math.sin(a * 13) if r > 560 else 0))
    under = [(R - 2, D['under'][-1][1] - 4), (D['under'][0][0] - 4, D['under'][0][1] - 4), (D['stem'][-1][1] - 2, D['h'] - 2)]
    lathe(X.mesh(gill), under, 64, inward=True, u_tiles=14)
    # raised orange spots (domes) over the painted ones on the outer cap
    rng = np.random.default_rng(12)
    W = X.mesh(wart)
    tr = [p[0] for p in D['top']]; tz = [p[1] for p in D['top']]
    for i in range(22):
        r = rng.uniform(300, 540); a = rng.uniform(0, 2 * math.pi)
        z = np.interp(r, tr, tz) + 5
        sz = rng.uniform(22, 40)
        slope = (np.interp(r + 5, tr, tz) - np.interp(r - 5, tr, tz)) / 10
        tilt = math.atan(-slope)
        Rm = rot_z(a) @ rot_axis((0, 1, 0), tilt)
        ellipsoid(W, (r * math.cos(a), r * math.sin(a), z + 1), sz, sz * rng.uniform(0.75, 1.0), min(5.0, sz * 0.15), nu=10, nv=6, R=Rm)
    # little chimney-like toadstool on the roof? no: keep the walkable top clear
    return _save('yellowhouse', X)


CREPE = {'red': (226, 40, 46), 'yellow': (250, 216, 40), 'orange': (250, 140, 30), 'blue': (40, 70, 170), 'navy': (30, 34, 90),
         'green': (60, 160, 70), 'lime': (170, 220, 80), 'pink': (240, 90, 160), 'violet': (150, 80, 190), 'white': (244, 240, 230)}


def flowertree(name, palette, seed, accessible):
    X = Model()
    bark = S('bark_tree', 'lm')
    D = FT
    rng = np.random.default_rng(seed)
    # trunk: tapered, slightly leaning tube with root flare, two hidden branches
    zs = np.linspace(0, D['trunk_z'] + 120, 12)
    path = [(12 * math.sin(z / 260), 8 * math.sin(z / 330 + 1), z) for z in zs]
    radii = [D['trunk_r'][0] + 30 * max(0, 1 - z / 90) ** 2 + (D['trunk_r'][1] - D['trunk_r'][0]) * z / (D['trunk_z'] + 120) for z in zs]
    tube(X.mesh(bark), path, radii, nseg=14, caps=(False, True), utiles=3, vlen=300)
    for k in range(3):
        a = k * 2.1 + 0.4
        p0 = np.array([0, 0, D['trunk_z'] - 40.0]); p1 = p0 + [220 * math.cos(a), 220 * math.sin(a), 180]
        tube(X.mesh(bark), [p0, (p0 + p1) / 2 + [0, 0, 30], p1], [26, 20, 12], nseg=10, utiles=2)
    # pompoms on the dome: patchwork colour zones from a low-frequency field on the direction
    shaders = {c: S('crepe_' + c, 'lm', tag='t') for c in palette}
    zones = [(np.array([math.cos(t) * math.cos(p), math.sin(t) * math.cos(p), math.sin(p)]), palette[i % len(palette)])
             for i, (t, p) in enumerate(zip(rng.uniform(0, 2 * math.pi, 14), rng.uniform(-0.3, 1.2, 14)))]
    cz, A_, C_ = D['cz'], D['a'], D['c']
    pts = []
    # Fibonacci sphere over the upper ~85% of the ellipsoid
    n = 120
    for i in range(n):
        zz = 1 - (i + 0.5) / n * 1.75
        if zz < -0.75: continue
        rr = math.sqrt(max(0, 1 - zz * zz)); t = i * 2.39996 + rng.uniform(-0.1, 0.1)
        d = np.array([rr * math.cos(t), rr * math.sin(t), zz])
        pts.append(d)
    for d in pts:
        p = np.array([d[0] * A_, d[1] * A_, cz + d[2] * C_])
        r = rng.uniform(72, 104)
        col = max(zones, key=lambda zc: d @ zc[0])[1]
        if accessible and math.hypot(p[0], p[1]) < D['col'][2][2] + 30 and p[2] > D['top'] - 120:
            p[2] = D['top'] - 34; r = rng.uniform(56, 70)          # keep the walkable top shallow
        blob(X.mesh(shaders[col]), p, r, int(rng.integers(1 << 30)), amp=0.2, freq=6, squash=0.85)
    # inner fill so no gaps show from below
    for k in range(10):
        a = k * 2 * math.pi / 10
        p = np.array([250 * math.cos(a), 250 * math.sin(a), cz - 170])
        blob(X.mesh(shaders[palette[k % len(palette)]]), p, 110, int(rng.integers(1 << 30)), amp=0.15, freq=5, squash=0.7)
    blob(X.mesh(shaders[palette[0]]), np.array([0, 0, cz - 200.0]), 150, 3, amp=0.12, squash=0.6)
    return _save(name, X)


def gumtree():
    X = Model()
    bark = S('bark_tree', 'lm', tag='g')
    D = GT
    rng = np.random.default_rng(77)
    zs = np.linspace(0, D['trunk_z'] + 100, 10)
    path = [(10 * math.sin(z / 200), 0, z) for z in zs]
    tube(X.mesh(bark), path, [34 + 26 * max(0, 1 - z / 80) ** 2 - z * 0.01 for z in zs], nseg=12, caps=(False, True), utiles=3)
    leaf = {c: S('crepe_' + c, 'lm', tag='g') for c in ('lime', 'navy', 'orange', 'green')}
    cz, A_, C_ = D['cz'], D['a'], D['c']
    for i in range(70):
        zz = 1 - (i + 0.5) / 70 * 1.7
        rr = math.sqrt(max(0, 1 - zz * zz)); t = i * 2.39996
        p = np.array([rr * math.cos(t) * A_, rr * math.sin(t) * A_, cz + zz * C_])
        col = ['lime', 'lime', 'navy', 'orange', 'green'][int(rng.integers(5))]
        blob(X.mesh(leaf[col]), p, rng.uniform(64, 92), int(rng.integers(1 << 30)), amp=0.26, freq=7, squash=0.8)
    blob(X.mesh(leaf['green']), np.array([0, 0, cz - 120.0]), 170, 5, amp=0.15, squash=0.7)
    # gumballs hanging on the outside
    gcols = {'gb_red': (220, 40, 40), 'gb_yellow': (250, 210, 40), 'gb_blue': (40, 90, 210), 'gb_green': (40, 180, 90),
             'gb_orange': (250, 130, 30), 'gb_pink': (240, 110, 170)}
    gs = {k: S(k, 'lms', v=0.22) for k in gcols}
    keys = list(gcols)
    for i in range(80):
        zz = rng.uniform(-0.85, 0.75); t = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(1 - zz * zz)
        d = np.array([rr * math.cos(t), rr * math.sin(t), zz])
        p = np.array([d[0] * (A_ + 44), d[1] * (A_ + 44), cz + d[2] * (C_ + 40)])
        gumball(X.mesh(gs[keys[i % len(keys)]]), p, rng.uniform(32, 46))
    return _save('gumtree', X)


def lolli_disc_mesh(M, design_shader_mesh, axis='y'):
    pass


def _disc(M, Mrim, r, t, n=40, axis='y'):
    """candy disc of radius r and thickness t centred at the origin, faces +-axis; planar UVs on the faces"""
    for sgn in (1, -1):
        pts = []; uvs = []
        for k in range(n):
            a = 2 * math.pi * k / n
            u, v = math.cos(a) * (r - t * 0.4), math.sin(a) * (r - t * 0.4)
            if axis == 'y': p = (u, sgn * t / 2, v)
            else: p = (sgn * t / 2, u, v)
            pts.append(p); uvs.append((0.5 + u / (2 * r) * sgn, 0.5 - v / (2 * r)))
        nrm = (0, sgn, 0) if axis == 'y' else (sgn, 0, 0)
        M.poly(pts, nrm, uvs)
    # rounded rim (half torus)
    nr = 6
    P = np.zeros((nr + 1, n + 1, 3)); N = np.zeros_like(P); UV = np.zeros((nr + 1, n + 1, 2))
    for i in range(nr + 1):
        ph = -math.pi / 2 + math.pi * i / nr
        for j in range(n + 1):
            a = 2 * math.pi * j / n
            rr = r - t * 0.4 + t * 0.5 * math.cos(ph); w = t * 0.5 * math.sin(ph)
            u, v = rr * math.cos(a), rr * math.sin(a)
            nu, nv, nw = math.cos(ph) * math.cos(a), math.cos(ph) * math.sin(a), math.sin(ph)
            if axis == 'y': P[i, j] = (u, w, v); N[i, j] = (nu, nw, nv)
            else: P[i, j] = (w, u, v); N[i, j] = (nw, nu, nv)
            UV[i, j] = (j / n * 8, i / nr)
    Mrim.grid(P, N, UV)


LOLLI_RIM = {'spiral': (236, 110, 30), 'star': (240, 60, 40), 'flower': (236, 130, 30), 'rings': (240, 240, 250), 'swirl': (244, 90, 160)}


def lollipop(design):
    X = Model()
    face = S('lolli_' + design, 'lms', v=0.18); rim = S('rim_' + design, 'lms', v=0.18); stick = S('stick', 'lm')
    lathe(X.mesh(stick), [(7, 0), (7, LOLLI_H - LOLLI_R + 10), (5, LOLLI_H)], 10)
    D = Mesh()
    _disc(D, D, LOLLI_R, LOLLI_T)
    Mf = X.mesh(face); Mr = X.mesh(rim)
    _disc(Mf, Mr, LOLLI_R, LOLLI_T)
    for M_ in (Mf, Mr):
        M_.V = [v + np.array([0, 0, LOLLI_H]) for v in M_.V]
    return _save('lolli_' + design, X)


def spin_disc(design):
    """disc alone, facing +-x, centred on the origin (func_rotating X_AXIS model2) + its stick as a separate MD3"""
    X = Model()
    face = S('lolli_' + design, 'lms', v=0.18, tag='d'); rim = S('rim_' + design, 'lms', v=0.18, tag='d')
    _disc(X.mesh(face), X.mesh(rim), LOLLI_R * 1.4, LOLLI_T * 1.3, axis='x', n=48)
    return _save('disc_' + design, X)


def stickonly():
    X = Model()
    lathe(X.mesh(S('stick', 'lm', tag='s')), [(10, 0), (10, LOLLI_H * 1.3 - LOLLI_R * 1.4 + 4), (8, LOLLI_H * 1.3 - LOLLI_R * 1.4 + 30)], 10)
    return _save('stick_tall', X)


def cane():
    X = Model()
    st = S('stripe_rw', 'lms', v=0.16)
    hook = [(0, 0, z) for z in np.linspace(0, CANE_H - 60, 8)]
    hook += [(60 - 60 * math.cos(a), 0, CANE_H - 60 + 60 * math.sin(a)) for a in np.linspace(0.15, math.pi, 10)]
    hook += [(120, 0, CANE_H - 60 - d) for d in (20, 50)]
    tube(X.mesh(st), hook, 14, nseg=12, utiles=1, twist=1 / 120)
    return _save('cane', X)


def cane_arch():
    X = Model()
    st = S('stripe_rw', 'lms', v=0.16, tag='a'); st2 = S('stripe_gw', 'lms', v=0.16)
    hw = ARCH_W / 2; rr = hw
    for (off, sh) in ((-18, st), (18, st2)):
        p = [(-hw, off, z) for z in np.linspace(0, ARCH_H - rr, 6)]
        p += [(-rr * math.cos(a), off, ARCH_H - rr + rr * math.sin(a)) for a in np.linspace(0.1, math.pi - 0.1, 24)]
        p += [(hw, off, z) for z in np.linspace(ARCH_H - rr, 0, 6)]
        tube(X.mesh(sh), p, 16, nseg=12, utiles=1, twist=1 / 140)
    # a bow on top + hanging gumdrops
    bow = S('crepe_red', 'lm', tag='b')
    blob(X.mesh(bow), (0, 0, ARCH_H + 10), 34, 3, amp=0.2)
    for sx in (-1, 1):
        ellipsoid(X.mesh(bow), (sx * 50, 0, ARCH_H + 4), 50, 16, 26, R=rot_axis((0, 1, 0), sx * 0.4))
    return _save('cane_arch', X)


def jawbreaker(name):
    X = Model()
    sh = S('jaw_' + name, 'lms', v=0.2)
    ellipsoid(X.mesh(sh), (0, 0, JAW_R), JAW_R, JAW_R, JAW_R, 28, 18)
    return _save('jaw_' + name, X)


def urn():
    X = Model()
    iron = S('urn_black', 'lms', v=0.12); stone = S('stone_sand', 'lm', tag='u')
    rbox(X.mesh(stone), (-46, -46, 0), (46, 46, 70), r=6, tile=128)
    rbox(X.mesh(stone), (-54, -54, 70), (54, 54, 84), r=4, tile=128)
    prof = [(28, 84), (24, 100), (18, 120), (30, 136), (54, 156), (66, 180), (66, 200), (60, 214), (64, 220)]
    lathe(X.mesh(iron), prof, 24)
    lathe(X.mesh(iron), [(64, 220), (52, 222)], 24, inward=True)
    gcols = ['gb_red', 'gb_yellow', 'gb_blue', 'gb_green', 'gb_orange', 'gb_pink']
    rng = np.random.default_rng(5)
    for i in range(26):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0, 1)) * 44
        z = 228 + (1 - r / 44) * 24 + rng.uniform(-4, 4)
        gumball(X.mesh(S(gcols[i % 6], 'lms', v=0.22)), (r * math.cos(a), r * math.sin(a), z), rng.uniform(13, 17), nu=10, nv=7)
    return _save('urn', X)


def buttercup():
    X = Model()
    stem = S('leaf_green', 'vl2s'); cup = S('petal_yellow', 'vl2s')
    path = [(8 * math.sin(z / 60), 0, z) for z in np.linspace(0, 300, 8)]
    tube(X.mesh(stem), path, 5, nseg=8)
    for (z, a) in ((90, 0.3), (160, 2.6)):
        c = np.array([math.cos(a) * 40, math.sin(a) * 40, z + 10])
        ellipsoid(X.mesh(stem), c, 48, 14, 3, R=rot_z(a) @ rot_axis((0, 1, 0), -0.4), nu=10, nv=4)
    prof = [(4, 300), (16, 304), (34, 316), (46, 334), (52, 350)]
    lathe(X.mesh(cup), prof, 16, deform=lambda a, r, z: r + (6 * math.cos(a * 5) if z > 330 else 0))
    lathe(X.mesh(cup), [(r - 3, z + 2) for (r, z) in prof[::-1]], 16, inward=False)
    return _save('buttercup', X)


def twisty():
    X = Model()
    cols = [S('candy_red', 'lms', v=0.15), S('candy_yellow', 'lms', v=0.15), S('candy_blue', 'lms', v=0.15)]
    H = 560
    for k, sh in enumerate(cols):
        path = [(14 * math.cos(z / 45 + k * 2.094), 14 * math.sin(z / 45 + k * 2.094), z) for z in np.linspace(0, H, 48)]
        tube(X.mesh(sh), path, 9, nseg=8)
    bead = S('candy_pink', 'lms', v=0.2)
    rng = np.random.default_rng(3)
    for i in range(14):
        z = rng.uniform(140, H - 60); a = rng.uniform(0, 2 * math.pi)
        r = 60 + rng.uniform(0, 30)
        tube(X.mesh(cols[i % 3]), [(0, 0, z), (r * 0.6 * math.cos(a), r * 0.6 * math.sin(a), z + 20), (r * math.cos(a), r * math.sin(a), z + 50)], 4, nseg=6)
        sphere(X.mesh(bead if i % 2 else cols[(i + 1) % 3]), (r * math.cos(a), r * math.sin(a), z + 62), 14, 10, 7)
    st = S('lolli_star', 'lms', v=0.18, tag='t'); rim = S('rim_star', 'lms', v=0.18, tag='t')
    Mf, Mr = X.mesh(st), X.mesh(rim)
    o1, o2 = len(Mf.V), len(Mr.V)
    _disc(Mf, Mr, 70, 12)
    for M_, o in ((Mf, o1), (Mr, o2)):
        for i in range(o, len(M_.V)): M_.V[i] = M_.V[i] + np.array([0, 0, H + 64])
    return _save('twisty', X)


# ------------------------------------------------------------------------------------------- pump house
def shed():
    """iron + glass pump shed, footprint 320 x 256 (x, y) centred on the origin, door in the south wall, windows E/W.
    Walls are panels 12 thick (collision = brushes 8 inside); flat roof with a rim at SHED_H"""
    X = Model()
    W, D, H = 160, 128, L.SHED_H
    pan = S('iron_teal', 'lm'); frm = S('iron_dark', 'lm'); gl = S('glass', 'glass'); inner = S('iron_teal_in', 'lm')
    t = 12
    dw = SHED_DOOR / 2
    # south wall with the door
    for (x0, x1) in ((-W, -dw), (dw, W)):
        rbox(X.mesh(pan), (x0, -D, 0), (x1, -D + t, H), r=1, tile=128)
    rbox(X.mesh(pan), (-dw, -D, 224), (dw, -D + t, H), r=1, tile=128)
    # north wall
    rbox(X.mesh(pan), (-W, D - t, 0), (W, D, H), r=1, tile=128)
    # east/west walls with a window each (112 wide, z 112..208)
    for sx in (-1, 1):
        x0, x1 = (W - t, W) if sx > 0 else (-W, -W + t)
        for (y0, y1, z0, z1) in ((-D + t, -56, 0, H), (56, D - t, 0, H), (-56, 56, 0, 112), (-56, 56, 208, H)):
            rbox(X.mesh(pan), (x0, y0, z0), (x1, y1, z1), r=1, tile=128)
        q = [(x0 + t / 2, -56, 112), (x0 + t / 2, 56, 112), (x0 + t / 2, 56, 208), (x0 + t / 2, -56, 208)]
        X.mesh(gl).quad(*q, tile=128)
        for (a, b) in (((-56, 112), (56, 112)), ((-56, 208), (56, 208)), ((-56, 112), (-56, 208)), ((56, 112), (56, 208)), ((0, 112), (0, 208))):
            tube(X.mesh(frm), [(x0 + t / 2, a[0], a[1]), (x0 + t / 2, b[0], b[1])], 4, nseg=6)
    # corner posts + roof rim
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(X.mesh(frm), (sx * W - 10 if sx > 0 else -W - 6, sy * D - 10 if sy > 0 else -D - 6, 0),
                 (sx * W + 6 if sx > 0 else -W + 10, sy * D + 6 if sy > 0 else -D + 10, H + 6), r=2, tile=64)
    rbox(X.mesh(frm), (-W - 8, -D - 8, H - 8), (W + 8, D + 8, H + 4), r=2, tile=128, faces='nsewb')
    X.mesh(S('roof_plate', 'lm')).quad((-W - 8, -D - 8, H + 4), (W + 8, -D - 8, H + 4), (W + 8, D + 8, H + 4), (-W - 8, D + 8, H + 4), tile=128,
                                      n=(0, 0, 1))
    # door frame
    tube(X.mesh(frm), [(-dw, -D - 2, 0), (-dw, -D - 2, 224), (dw, -D - 2, 224), (dw, -D - 2, 0)], 6, nseg=6)
    # inside faces (darker) so the interior isn't see-through
    X.mesh(inner).quad((-W + t, D - t, 0), (W - t, D - t, 0), (W - t, D - t, H), (-W + t, D - t, H), tile=128, n=(0, -1, 0))
    X.mesh(inner).quad((-W + t, -D + t, H - 8), (W - t, -D + t, H - 8), (W - t, D - t, H - 8), (-W + t, D - t, H - 8), tile=128, n=(0, 0, -1))
    # sign over the door
    X.mesh(S('sign_pump', 'lm')).quad((-80, -D - 3, 236), (80, -D - 3, 236), (80, -D - 3, 276), (-80, -D - 3, 276), tile=1, n=(0, -1, 0))
    m = X.m[S('sign_pump', 'lm')]
    m.ST = [(0, 1), (1, 1), (1, 0), (0, 0)]
    return _save('shed', X)


def pump():
    """pump machine inside the shed: flywheel, cylinder, gauges, pipes into the floor (base at z 0)"""
    X = Model()
    iron = S('iron_dark', 'lm', tag='p'); brass = S('brass', 'lms', v=0.25); red = S('enamel_red', 'lms', v=0.15)
    rbox(X.mesh(iron), (-60, -40, 0), (60, 40, 30), r=4)
    lathe(X.mesh(red), [(34, 30), (34, 140), (28, 150), (10, 154)], 16)
    tube(X.mesh(brass), [(-70, 0, 110), (70, 0, 110)], 6, nseg=8)
    # flywheel facing +-x at x 80
    for (a0) in np.linspace(0, 2 * math.pi, 6, endpoint=False):
        tube(X.mesh(iron), [(84, 0, 110), (84, 70 * math.cos(a0), 110 + 70 * math.sin(a0))], 5, nseg=6)
    tube(X.mesh(iron), [(84, 74 * math.cos(a), 110 + 74 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)], 9, nseg=8, caps=(False, False))
    for (y, z) in ((-30, 170), (30, 170)):
        lathe(X.mesh(brass), [(14, z - 4), (16, z), (16, z + 4)], 12, cx=0, cy=y)
    X.mesh(S('gauge', 'glow')).poly([(-12, -45, 175), (12, -45, 175), (12, -45, 199), (-12, -45, 199)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    tube(X.mesh(S('enamel_pink', 'lms', v=0.15)), [(-40, 0, 30), (-40, 0, 80), (-80, 0, 100), (-110, 0, 100), (-110, 0, 0)], 12, nseg=10)
    return _save('pump', X)


def deck_frame():
    """iron lattice columns + beams under the deck (origin = deck centre at z 0 = ground), railing on the open edges"""
    X = Model()
    iron = S('iron_dark', 'lm', tag='d')
    x0, y0, x1, y1 = L.DECK
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    Z = L.DECK_Z
    cols = deck_columns()
    for (px, py) in cols:
        px -= cx; py -= cy
        for (dx, dy) in ((-14, -14), (14, -14), (14, 14), (-14, 14)):
            tube(X.mesh(iron), [(px + dx, py + dy, 0), (px + dx, py + dy, Z - 16)], 4, nseg=6)
        for z in np.arange(0, Z - 40, 64):
            for (a, b) in (((-14, -14), (14, 14)), ((14, -14), (-14, 14))):
                tube(X.mesh(iron), [(px + a[0], py + a[1], z), (px + b[0], py + b[1], z + 64)], 2.5, nseg=5, caps=(False, False))
        rbox(X.mesh(iron), (px - 24, py - 24, 0), (px + 24, py + 24, 12), r=2)
    # edge beams under the deck
    for (a, b) in (((-hx, -hy), (hx, -hy)), ((hx, -hy), (hx, hy)), ((hx, hy), (-hx, hy)), ((-hx, hy), (-hx, -hy))):
        tube(X.mesh(iron), [(a[0], a[1], Z - 28), (b[0], b[1], Z - 28)], 10, nseg=6)
    # railing posts + top rail along the south and west edges and the east edge south of the stair landing
    rail = S('iron_dark', 'lm', tag='r')
    runs = [[(-hx + 8, -hy + 8), (hx - 8, -hy + 8)], [(-hx + 8, -hy + 8), (-hx + 8, hy - 8)],
            [(hx - 8, -hy + 8), (hx - 8, 200 - cy - 8)]]
    seen = set()
    for run in runs:
        (ax, ay), (bx, by) = run
        Ln = math.hypot(bx - ax, by - ay); n = max(2, int(Ln / 64))
        for i in range(n + 1):
            px, py = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            if (round(px), round(py)) in seen: continue
            seen.add((round(px), round(py)))
            tube(X.mesh(rail), [(px, py, Z), (px, py, Z + 44)], 2.5, nseg=5)
        tube(X.mesh(rail), [(ax, ay, Z + 44), (bx, by, Z + 44)], 3.5, nseg=6)
        tube(X.mesh(rail), [(ax, ay, Z + 22), (bx, by, Z + 22)], 2, nseg=5)
    return _save('deck_frame', X)


def deck_columns():
    x0, y0, x1, y1 = L.DECK
    out = []
    for px in (x0 + 40, (x0 + x1) / 2, x1 - 40):
        for py in (y0 + 40, y0 + 330):
            out.append((px, py))
    return out


def pipes_deck():
    """four enamel pipes from the deck's south edge down into the river (origin = deck south edge centre, z 0 = ground)"""
    X = Model()
    Z = L.DECK_Z
    x0, y0, x1, y1 = L.DECK
    cx = (x0 + x1) / 2
    specs = [('enamel_pink', -220, 380, 22), ('enamel_red', -80, 360, 26), ('enamel_yellow', 70, 400, 20), ('enamel_white', 210, 350, 24)]
    for (sh, dx, drop_y, r) in specs:
        s = S(sh, 'lms', v=0.15)
        # from under the deck, out over the edge, down in a bend into the water (water is ~drop_y south of the edge)
        path = [(dx, 120, Z - 20), (dx, 0, Z - 30), (dx, -60, Z - 60)]
        path += [(dx + 10 * math.sin(k), -60 - (drop_y - 60) * k / 6, Z - 60 - (Z + 10) * (1 - math.cos(k / 6 * math.pi / 2))) for k in range(1, 7)]
        path += [(dx + 10, -drop_y, L.RIV_FLOOR + 6)]
        tube(X.mesh(s), path, r, nseg=12, utiles=1, vlen=200)
        for k in (2, 5):
            p = np.array(path[k]); q = np.array(path[k + 1])
            d = q - p; d /= np.linalg.norm(d)
            b1, b2 = frame(d)
            tube(X.mesh(S('brass', 'lms', v=0.25, tag='f')), [p - d * 6, p + d * 6], r + 6, nseg=12)
    return _save('pipes_deck', X)


# ------------------------------------------------------------------------------------------- the suction pipe
def augpipe(start, land, apex):
    """glass tube following the jump-pad flight (origin = start point); returns (path, scale, zoff)"""
    X = Model()
    gl = S('glass_pipe', 'glass'); brass = S('brass', 'lms', v=0.25, tag='a'); choc = S('choc_smear', 'alpha')
    tr, T = L.apex_traj(start, land, apex, n=60)
    tr = tr - np.array(start)
    # keep the part of the flight until it is 150 above the landing height on the way down
    zl = land[2] - start[2] + 150
    keep = [0]
    for i in range(1, len(tr)):
        if tr[i, 2] < zl and tr[i, 2] < tr[i - 1, 2]: break
        keep.append(i)
    tr = tr[keep]
    # start a bit below the water as a funnel
    path = [tr[0] + [0, 0, L.RIV_FLOOR + 30 - start[2]]] + list(tr)
    tube(X.mesh(gl), path, 62, nseg=20, caps=(False, False), vlen=400)
    tube(X.mesh(choc), path, 60, nseg=20, caps=(False, False), vlen=300, utiles=2)
    # brass rings every ~260u along the path
    acc = 0
    for i in range(1, len(path)):
        acc += np.linalg.norm(path[i] - path[i - 1])
        if acc > 260:
            acc = 0
            p = np.array(path[i]); d = np.array(path[min(i + 1, len(path) - 1)]) - np.array(path[i - 1]); d /= np.linalg.norm(d)
            tube(X.mesh(brass), [p - d * 6, p + d * 6], 70, nseg=20)
    # intake funnel (bell mouth) at the bottom, sitting in the river
    zb_ = L.RIV_FLOOR + 1 - start[2]
    lathe(X.mesh(brass), [(108, zb_), (96, zb_ + 10), (80, zb_ + 30), (70, 20), (66, 40)], 24)
    return _save('augpipe', X)


# ------------------------------------------------------------------------------------------- the chocolate waterfall
def fall_curve(n=24):
    """curtain centreline: (y, z) from the lip down to the pool surface"""
    y0, z0 = float(L.FALL_LIP[1]), float(L.SUMMIT_Z)
    v0 = 200.0
    T = math.sqrt(2 * (z0 - L.WATER) / 800)
    out = []
    for t in np.linspace(0, T, n):
        out.append((y0 - v0 * t, z0 - 400 * t * t))
    return out


def waterfall():
    """curtain + lip spill; origin at (FALL_X, 0, 0) world -> model coords are world y, z"""
    X = Model()
    sh = S('chocfall', 'chocfall')
    curve = fall_curve(28)
    w0, w1 = L.FALL_W
    nx = 12
    P = np.zeros((len(curve), nx + 1, 3)); UV = np.zeros((len(curve), nx + 1, 2))
    Ls = np.concatenate([[0], np.cumsum([math.hypot(curve[i + 1][0] - curve[i][0], curve[i + 1][1] - curve[i][1]) for i in range(len(curve) - 1)])])
    for i, (y, z) in enumerate(curve):
        f = i / (len(curve) - 1)
        w = w0 + (w1 - w0) * f
        for j in range(nx + 1):
            u = (j / nx - 0.5)
            bulge = 18 * math.cos(u * math.pi) * (0.3 + f)
            P[i, j] = (u * w, y - bulge, z)
            UV[i, j] = (u * w / 256 + 0.5, Ls[i] / 512)
    N = grid_normals(P)
    if N[..., 1].mean() > 0: N = -N
    X.mesh(sh).grid(P, N, UV)
    # spill over the lip from the channel surface
    sp = []
    for a in np.linspace(0, math.pi / 2, 6):
        sp.append((L.FALL_LIP[1] + 24 - 24 * math.sin(a), L.CHANNEL_FLOOR + 18 - 14 * (1 - math.cos(a))))
    P = np.zeros((len(sp), nx + 1, 3)); UV = np.zeros((len(sp), nx + 1, 2))
    for i, (y, z) in enumerate(sp):
        for j in range(nx + 1):
            u = j / nx - 0.5
            P[i, j] = (u * w0, y, z); UV[i, j] = (u * w0 / 256 + 0.5, -i * 0.05)
    N = grid_normals(P)
    if N[..., 2].mean() < 0: N = -N
    X.mesh(sh).grid(P, N, UV)
    return _save('waterfall', X)


def splash():
    """bubbling chocolate splash ring where the fall hits the pool (origin at the impact point on the surface)"""
    X = Model()
    sh = S('chocsplash', 'chocsplash')
    rng = np.random.default_rng(9)
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 170)
        c = (r * math.cos(a) * 1.3, r * math.sin(a) * 0.6, 0)
        ellipsoid(X.mesh(sh), c, rng.uniform(40, 70), rng.uniform(30, 50), rng.uniform(16, 34), 12, 7, flat_bottom=-4)
    return _save('splash', X)


def outlet():
    """giant copper pipe coming out of the north wall, bending down over the channel's north end (origin: channel
    centre at the north wall, z = summit)"""
    X = Model()
    cu = S('copper', 'lms', v=0.3); sh = S('chocfall', 'chocfall', tag='o')
    path = [(0, 0, 260), (0, -20, 260), (0, -90, 240), (0, -140, 190), (0, -160, 130), (0, -164, 96)]
    tube(X.mesh(cu), path, 54, nseg=20, utiles=2, vlen=300)
    for p, q in ((path[0], path[1]), (path[3], path[4])):
        p = np.array(p, float); d = np.array(q, float) - p; d /= np.linalg.norm(d)
        tube(X.mesh(cu), [p, p + d * 14], 66, nseg=20)
    # pour from the mouth down into the channel
    P = np.zeros((6, 9, 3)); UV = np.zeros((6, 9, 2))
    for i, z in enumerate(np.linspace(92, L.CHANNEL_FLOOR - L.SUMMIT_Z + 14, 6)):
        for j in range(9):
            a = 2 * math.pi * j / 8
            r = 40 + (i / 5) * 10
            P[i, j] = (r * math.cos(a), -164 + r * math.sin(a), z); UV[i, j] = (j / 8, -z / 256)
    N = np.zeros_like(P); N[..., 0] = np.cos(np.linspace(0, 2 * math.pi, 9))[None]; N[..., 1] = np.sin(np.linspace(0, 2 * math.pi, 9))[None]
    X.mesh(sh).grid(P, N, UV)
    return _save('outlet', X)


# ------------------------------------------------------------------------------------------- boat + bridge
def boat():
    """pink candy boat along +x (bow +x), deck at z 0 (= origin), keel at RIV_FLOOR+8, swan figurehead"""
    X = Model()
    hull = S('boat_pink', 'lms', v=0.12); trim = S('trim_white', 'lm'); deck = S('wafer', 'lm', tag='b'); swan = S('swan', 'lm')
    gold = S('brass', 'lms', v=0.25, tag='b')
    Lh, Bh = BOAT_L / 2, BOAT_B / 2
    keel = L.RIV_FLOOR + 1
    # hull: stations along x with a rounded section; gunwale rises to +40 at the sides
    xs = np.linspace(-Lh, Lh, 15)
    rows = []
    for x in xs:
        f = x / Lh
        half = Bh * math.sqrt(max(0.02, 1 - (max(0, f) ** 2.2 if f > 0 else (abs(f) ** 4))))
        rows.append((x, half))
    na = 12
    P = np.zeros((len(xs), na + 1, 3)); UV = np.zeros((len(xs), na + 1, 2))
    for i, (x, half) in enumerate(rows):
        top = 40 + 30 * max(0, x / Lh) ** 2 + 16 * max(0, -x / Lh) ** 2
        for j in range(na + 1):
            a = math.pi * j / na                       # 0 = port gunwale, pi = starboard gunwale
            yy = half * math.cos(a)
            zz = top - (top - keel) * math.sin(a) ** 0.8
            P[i, j] = (x, yy, zz); UV[i, j] = (x / 256, j / na)
    N = grid_normals(P)
    if N[len(xs) // 2, na // 2, 2] > 0: N = -N
    X.mesh(hull).grid(P, N, UV)
    # gunwale rail (white trim tube) along both sides
    for sgn in (1, -1):
        tube(X.mesh(trim), [(x, sgn * half, 40 + 30 * max(0, x / Lh) ** 2 + 16 * max(0, -x / Lh) ** 2) for (x, half) in rows], 7, nseg=6)
    # deck (wafer)
    pts = [(x, half - 6) for (x, half) in rows] + [(x, -(half - 6)) for (x, half) in rows[::-1]]
    from meshlib import triangulate
    Md = X.mesh(deck)
    tri = triangulate(pts)
    for (a, b, c) in tri:
        o = len(Md.V)
        for k in (a, b, c):
            Md.add_v((pts[k][0], pts[k][1], 2), (0, 0, 1), (pts[k][0] / 128, pts[k][1] / 128))
        Md.tri(o, o + 1, o + 2)
    # benches (two)
    for bx in (-110, 40):
        rbox(X.mesh(trim), (bx - 24, -Bh + 30, 2), (bx + 24, Bh - 30, 40), r=6, tile=128)
    # swan figurehead: body bulge at the bow, S-neck, head and beak
    ellipsoid(X.mesh(swan), (Lh - 40, 0, 50), 70, 46, 40, 16, 10)
    neck = [(Lh - 20 + 30 * math.sin(t * 2.2) * 0.5 + t * 30, 0, 70 + t * 150) for t in np.linspace(0, 1, 10)]
    neck = [(Lh - 20 + 50 * math.sin(t * math.pi) * (1 - t) + 26 * t, 0, 70 + 160 * t) for t in np.linspace(0, 1, 10)]
    tube(X.mesh(swan), neck, [22, 20, 17, 15, 14, 13, 13, 13, 14, 15], nseg=10)
    hp = np.array(neck[-1]) + [10, 0, 10]
    ellipsoid(X.mesh(swan), hp, 30, 20, 22, 12, 8)
    lathe(X.mesh(S('beak', 'lm')), [(10, 0), (6, 18), (0, 34)], 10)
    m = X.m[S('beak', 'lm')]
    R = rot_axis((0, 1, 0), math.pi / 2 + 0.15)
    m.V = [R @ v + hp + [24, 0, -2] for v in m.V]; m.N = [R @ n for n in m.N]
    for sy in (-1, 1):
        sphere(X.mesh(S('eye_black', 'lm')), hp + [14, sy * 15, 8], 4, 8, 5)
    # wings folded along the hull sides
    for sy in (-1, 1):
        ellipsoid(X.mesh(swan), (Lh - 120, sy * (Bh - 4), 34), 110, 14, 30, 14, 8, R=rot_axis((1, 0, 0), sy * 0.2))
    # gold stern lantern post
    tube(X.mesh(gold), [(-Lh + 30, 0, 2), (-Lh + 30, 0, 130)], 5, nseg=8)
    sphere(X.mesh(S('lamp_warm', 'glow', light=0)), (-Lh + 30, 0, 146), 16, 12, 8)
    return _save('boat', X)


def bridge():
    """candy-cane bridge along +x, centred, deck top z BRIDGE_Z over the middle, ramps to z 0 at the ends"""
    X = Model()
    st = S('stripe_rw', 'lms', v=0.16, tag='br'); wafer = S('wafer', 'lm'); fasc = S('candy_pink', 'lms', v=0.12, tag='br')
    hl = BRIDGE_L / 2; hw = BRIDGE_HW
    flat = 240
    def ztop(x):
        ax = abs(x)
        return BRIDGE_Z if ax <= flat else BRIDGE_Z * (1 - (ax - flat) / (hl - flat))
    xs = np.linspace(-hl, hl, 29)
    # fascia boards along the sides (pink) under the deck edge
    for sgn in (1, -1):
        P = np.zeros((len(xs), 2, 3)); UV = np.zeros((len(xs), 2, 2))
        for i, x in enumerate(xs):
            zt = ztop(x)
            P[i, 0] = (x, sgn * (hw + 2), zt + 1); P[i, 1] = (x, sgn * (hw + 2), max(zt - 20, -2))
            UV[i, 0] = (x / 128, 0); UV[i, 1] = (x / 128, 0.3)
        N = np.zeros_like(P); N[..., 1] = sgn
        X.mesh(fasc).grid(P, N, UV)
    # railing: arches of striped cane between posts on both sides
    for sgn in (1, -1):
        y = sgn * (hw - 8)
        posts = np.linspace(-hl + 20, hl - 20, 7)
        for px in posts:
            tube(X.mesh(st), [(px, y, ztop(px) + 3), (px, y, ztop(px) + 66)], 7, nseg=8, twist=1 / 60)
        for a, b in zip(posts, posts[1:]):
            pts = [(a + (b - a) * t, y, ztop(a + (b - a) * t) + 50 + 16 * math.sin(t * math.pi)) for t in np.linspace(0, 1, 8)]
            tube(X.mesh(st), pts, 5, nseg=8, twist=1 / 60)
        for px in (posts[0], posts[-1]):
            sphere(X.mesh(S('gb_red', 'lms', v=0.22, tag='b')), (px, y, ztop(px) + 80), 14, 12, 8)
    return _save('bridge', X)


# ------------------------------------------------------------------------------------------- lamps, pillars, trusses
def pedestal():
    X = Model()
    st = S('stone_sand', 'lm'); iron = S('iron_dark', 'lm', tag='l'); glow = S('lamp_warm', 'glow', light=0, tag='p')
    rbox(X.mesh(st), (-60, -60, 0), (60, 60, 40), r=4)
    rbox(X.mesh(st), (-46, -46, 40), (46, 46, 460), r=3, tile=256)
    rbox(X.mesh(st), (-60, -60, 460), (60, 60, 500), r=4)
    lathe(X.mesh(iron), [(30, 500), (20, 512), (12, 540)], 12)
    sphere(X.mesh(glow), (0, 0, 572), 34, 16, 10)
    lathe(X.mesh(iron), [(36, 600), (14, 616), (4, 630)], 12)
    return _save('pedestal', X)


def lamppost():
    X = Model()
    iron = S('iron_dark', 'lm', tag='lp'); glow = S('lamp_warm', 'glow', light=0, tag='lp')
    lathe(X.mesh(iron), [(26, 0), (22, 20), (10, 34), (8, 360), (12, 372)], 12)
    for a in (0, math.pi):
        p = [(0, 0, 330)] + [(60 * math.sin(t) * math.cos(a), 60 * math.sin(t) * math.sin(a), 330 + 40 * (1 - math.cos(t))) for t in np.linspace(0.3, math.pi * 0.9, 6)]
        tube(X.mesh(iron), p, 3, nseg=5)
    lathe(X.mesh(glow), [(0.5, 372), (20, 380), (26, 404), (18, 426), (0.5, 432)], 12)
    lathe(X.mesh(iron), [(22, 430), (8, 446), (2, 456)], 12)
    return _save('lamppost', X)


def truss():
    """arched iron roof truss spanning x -HX..HX at the wall tops (origin at the centre, z 0 = roof underside - 8)"""
    X = Model()
    iron = S('iron_dark', 'lm', tag='t')
    hx = L.HX
    drop = 300
    def zb(x): return -drop * (1 - (x / hx) ** 2)
    xs = np.linspace(-hx, hx, 37)
    tube(X.mesh(iron), [(x, 0, zb(x)) for x in xs], 10, nseg=6, caps=(False, False))
    tube(X.mesh(iron), [(x, 0, -6) for x in xs], 8, nseg=6, caps=(False, False))
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        tube(X.mesh(iron), [(a, 0, zb(a)), (b, 0, -6)], 3, nseg=5, caps=(False, False))
        tube(X.mesh(iron), [(a, 0, zb(a)), (a, 0, -6)], 3, nseg=5, caps=(False, False))
    return _save('truss', X)


def wallpipes():
    """pipe runs along a wall (along x, origin at the centre, z 0 = mount height)"""
    X = Model()
    specs = [('enamel_red', 0, 18), ('enamel_yellow', 56, 14), ('copper', 104, 20)]
    for (sh, z, r) in specs:
        s = S(sh, 'lms', v=0.15, tag='w')
        tube(X.mesh(s), [(-1500, 0, z), (1500, 0, z)], r, nseg=10, utiles=1, vlen=200)
        for x in np.arange(-1440, 1441, 320):
            tube(X.mesh(S('iron_dark', 'lm', tag='w')), [(x, 0, z - r - 4), (x, 30, z - r - 4)], 4, nseg=6)
    return _save('wallpipes', X)


def crystal(name, cols, seed):
    X = Model()
    rng = np.random.default_rng(seed)
    for i in range(9):
        col = cols[i % len(cols)]
        sh = S('crys_' + col, 'glow', light=0)
        a = rng.uniform(0, 2 * math.pi); tilt = rng.uniform(0.1, 0.6)
        h = rng.uniform(60, 150); r = rng.uniform(12, 24)
        d = np.array([math.sin(tilt) * math.cos(a), math.sin(tilt) * math.sin(a), math.cos(tilt)])
        base = np.array([rng.uniform(-30, 30), rng.uniform(-30, 30), 0])
        b1, b2 = frame(d)
        ring = [base + (b1 * math.cos(k * math.pi / 3) + b2 * math.sin(k * math.pi / 3)) * r for k in range(6)]
        ring2 = [p + d * h for p in ring]
        tip = base + d * (h + r * 1.5)
        M = X.mesh(sh)
        for k in range(6):
            p0, p1, q0, q1 = ring[k], ring[(k + 1) % 6], ring2[k], ring2[(k + 1) % 6]
            n = np.cross(p1 - p0, q0 - p0); n = n / np.linalg.norm(n)
            if n @ ((p0 + p1) / 2 - base) < 0: n = -n
            M.poly([p0, p1, q1, q0], n, [(0, 1), (1, 1), (1, 0), (0, 0)])
            n2 = np.cross(q1 - q0, tip - q0); n2 = n2 / np.linalg.norm(n2)
            if n2 @ ((q0 + q1) / 2 - (base + d * h)) < 0: n2 = -n2
            M.poly([q0, q1, tip], n2, [(0, 1), (1, 1), (0.5, 0)])
    return _save(name, X)


def bottle(name, col):
    X = Model()
    gl = S('bottle_' + name, 'lms', v=0.25); lab = S('label_fizzy', 'lm'); cap = S('brass', 'lms', v=0.25, tag='c')
    prof = [(60, 0), (64, 10), (64, 200), (58, 230), (34, 270), (24, 300), (24, 330)]
    lathe(X.mesh(gl), prof, 24, u_tiles=1)
    lathe(X.mesh(lab), [(65.5, 70), (65.5, 170)], 24, u_tiles=1, a0=-60, a1=60, vlen=100)
    m = X.m[lab]
    m.ST = [((s), 1 - min(1, t)) for (s, t) in m.ST]
    lathe(X.mesh(cap), [(26, 330), (28, 334), (28, 350), (0.5, 356)], 16)
    return _save('bottle_' + name, X)


def boulder(name, seed):
    """lumpy limestone boulder (origin at the base centre, ~140 wide, ~90 tall)"""
    X = Model()
    sh = S('rock_lump', 'lm')
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    def bump(p, t):
        return 1 + 0.16 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]) + 0.09 * math.sin(7 * t + ph[2] + 4 * p) + 0.05 * math.sin(13 * t + ph[3])
    ellipsoid(X.mesh(sh), (0, 0, 40), 76, 62, 56, 22, 12, bump=bump, flat_bottom=-40, u1=3, v1=1.5)
    ellipsoid(X.mesh(sh), (50, 30, 20), 40, 34, 30, 14, 8, bump=bump, flat_bottom=-20, u1=2, v1=1)
    return _save(name, X)


def fan():
    """big ceiling fan, hub at the origin, blades in the xy plane (func_rotating model2, Z axis)"""
    X = Model()
    iron = S('iron_dark', 'lm', tag='f'); blade = S('fan_blade', 'lm')
    lathe(X.mesh(iron), [(40, -30), (46, -10), (46, 10), (30, 30), (14, 60)], 16)
    for k in range(4):
        a = k * math.pi / 2
        R = rot_z(a)
        b = Mesh()
        rbox(b, (40, -36, -4), (300, 36, 4), r=3, tile=128)
        X.mesh(blade).add(b, R @ rot_axis((1, 0, 0), 0.25), (0, 0, 0))
    return _save('fan', X)


def bonbon(name, col_sh):
    """twist-wrapped sweet lying on the ground along x (origin at the base centre)"""
    X = Model()
    w = S(col_sh, 'lms', v=0.2)
    ellipsoid(X.mesh(w), (0, 0, 70), 110, 72, 70, 20, 12)
    for sx in (-1, 1):
        rows = [(70 * (1 - t) + 8 * t, sx * (100 + 30 * t)) for t in np.linspace(0, 1, 5)]
        rows += [(8 + 60 * t, sx * (130 + 70 * t)) for t in np.linspace(0.2, 1, 5)]
        P = np.zeros((len(rows), 17, 3)); UV = np.zeros((len(rows), 17, 2))
        for i, (r, x) in enumerate(rows):
            for j in range(17):
                a = 2 * math.pi * j / 16 + i * 0.2
                rr = r * (1 + 0.15 * math.cos(a * 6))
                P[i, j] = (x, rr * math.cos(a), 70 + rr * math.sin(a) * 0.9); UV[i, j] = (j / 16, i / len(rows))
        N = grid_normals(P)
        cen = np.zeros_like(P); cen[..., 0] = P[..., 0]; cen[..., 2] = 70
        if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
        X.mesh(S(col_sh, 'lms', v=0.2, tag='2s2')).grid(P, N, UV)
    return _save(name, X)


def chocbar():
    """giant chocolate bar block (240 x 120 x 60) with a half-peeled wrapper"""
    X = Model()
    ch = S('chocbar', 'lm'); wr = S('wrapper_purple', 'lm'); foil = S('foil_gold', 'lms', v=0.3)
    rbox(X.mesh(ch), (-120, -60, 0), (40, 60, 56), r=6, tile=128)
    rbox(X.mesh(foil), (38, -61, 0), (60, 61, 58), r=2, tile=64)
    rbox(X.mesh(wr), (58, -62, 0), (122, 62, 60), r=3, tile=1, faces='nsewt')
    m = X.m[wr]
    return _save('chocbar', X)


def cupcake():
    X = Model()
    case = S('cupcase_pink', 'lm'); fr = S('frosting_white', 'lm'); cherry = S('gb_red', 'lms', v=0.25, tag='ch')
    lathe(X.mesh(case), [(80, 0), (104, 120)], 24, u_tiles=1, vlen=120)
    lathe(X.mesh(fr), [(104, 120), (110, 130), (100, 160), (76, 190), (50, 214), (30, 236), (8, 254), (0.5, 258)], 32,
          deform=lambda a, r, z: r + 6 * math.sin(a * 8 + z / 12))
    sphere(X.mesh(cherry), (0, 0, 278), 24, 14, 10)
    tube(X.mesh(S('leaf_green', 'lm2s', tag='c')), [(0, 0, 300), (10, 0, 330), (24, 0, 344)], 3, nseg=5)
    for k in range(30):
        a = k * 2.4; r = 30 + (k % 7) * 9
        z = float(np.interp(r, [0, 30, 50, 76, 100], [258, 236, 214, 190, 160])) + 2
        rbox(X.mesh(S(['candy_red', 'candy_yellow', 'candy_blue', 'candy_pink'][k % 4], 'lms', v=0.15, tag='s')),
             (r * math.cos(a) - 6, r * math.sin(a) - 2, z), (r * math.cos(a) + 6, r * math.sin(a) + 2, z + 4), r=0.5, k=1)
    return _save('cupcake', X)


def candyflower(name, petal, seed):
    X = Model()
    stem = S('leaf_green', 'vl2s', tag='f'); pet = S(petal, 'vl2s', tag='f'); mid = S('candy_yellow', 'vl', tag='f')
    rng = np.random.default_rng(seed)
    for k in range(3):
        a = k * 2.1 + rng.uniform(-0.3, 0.3); h = rng.uniform(120, 200); lean = rng.uniform(10, 30)
        top = np.array([lean * math.cos(a), lean * math.sin(a), h])
        tube(X.mesh(stem), [(0, 0, 0), top / 2 + [0, 0, 10], top], 3.5, nseg=6)
        for p in range(6):
            pa = p * math.pi / 3
            c = top + [22 * math.cos(pa), 22 * math.sin(pa), 2]
            ellipsoid(X.mesh(pet), c, 22, 11, 4, R=rot_z(pa), nu=10, nv=4)
        sphere(X.mesh(mid), top + [0, 0, 5], 10, 10, 6)
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        ellipsoid(X.mesh(stem), (30 * math.cos(a), 30 * math.sin(a), 10), 40, 12, 3, R=rot_z(a) @ rot_axis((0, 1, 0), -0.5), nu=8, nv=4)
    return _save(name, X)


def railing(name, pts, h=56, sh='iron_dark'):
    """ornate iron railing along a polyline (world coords); returns (path, scale, zoff, origin)"""
    X = Model()
    iron = S(sh, 'lm', tag='rl')
    P = np.array(pts, float)
    o = P[0].copy(); P = P - o
    tube(X.mesh(iron), [p + [0, 0, h] for p in P], 4, nseg=6)
    tube(X.mesh(iron), [p + [0, 0, 8] for p in P], 3, nseg=6)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        Ln = np.linalg.norm(b - a); n = max(1, int(Ln / 24))
        for k in range(n + 1):
            p = a + (b - a) * k / n
            tube(X.mesh(iron), [p + [0, 0, 8], p + [0, 0, h]], 1.8, nseg=4, caps=(False, False))
            if k % 4 == 2:
                c = p + [0, 0, h * 0.62]
                d = (b - a) / Ln
                ring = [c + d * 9 * math.cos(t) + np.array([0, 0, 9 * math.sin(t)]) for t in np.linspace(0, 2 * math.pi, 9)]
                tube(X.mesh(iron), ring, 1.6, nseg=4, caps=(False, False))
        if i == 0 or True:
            tube(X.mesh(iron), [a, a + [0, 0, h + 10]], 5, nseg=6)
            sphere(X.mesh(iron), a + [0, 0, h + 14], 6, 8, 5)
    tube(X.mesh(iron), [P[-1], P[-1] + [0, 0, h + 10]], 5, nseg=6)
    sphere(X.mesh(iron), P[-1] + [0, 0, h + 14], 6, 8, 5)
    path = f'{MD}/{name}.md3'
    sc, zo = save_md3(os.path.join(OUT, path), X.surfaces(), name, with_offset=True)
    return path, sc, zo, tuple(o)


# ================================================================================================= shaders + make
def shaders():
    s = '// ---- MD3 models (candy_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        t = img if img.startswith('textures/') else f'{MD}/{img}'
        if kind in ('lm', 'lms', 'lm2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 75\n'
            if kind == 'lm2s' or opt.get('tag', '').startswith('2s'): s += '\tcull none\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind in ('vl', 'vl2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n' + ('\tcull none\n' if kind == 'vl2s' else '') + f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n'
            if opt.get('light'): s += f'\tq3map_surfacelight {opt["light"]}\n\tq3map_lightRGB {opt.get("rgb", "1 1 1")}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen identity\n\t\ttcMod scroll 0 -0.35\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.1 0.12 0.14 )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.22 0.25 0.3 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'chocfall':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n\tcull none\n'
                  '\tdeformVertexes wave 64 sin 0 3 0 1.2\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen const ( 0.85 0.85 0.85 )\n\t\ttcMod scroll 0 -1.1\n\t}}\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.18 0.14 0.12 )\n\t\ttcMod scroll 0.03 -1.7\n\t\ttcMod scale 1.3 1\n\t}}\n}}\n\n')
        elif kind == 'chocsplash':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  '\tdeformVertexes wave 40 sin 4 8 0 0.9\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen const ( 0.8 0.8 0.8 )\n\t\ttcMod scroll 0.1 0.25\n\t\ttcMod turb 0 0.1 0 0.3\n\t}}\n}}\n\n')
    return s


def make(out):
    global OUT
    OUT = out
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)

    def sv(nm, a, alpha=None):
        im = a if isinstance(a, Image.Image) else _img(a).convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(d, nm + '.tga'))
        else:
            im.convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    for k, (c) in CREPE.items(): sv('crepe_' + k, tex_crepe(c, 100 + len(k) * 7))
    sv('cap_red', tex_cap((214, 26, 24), (180, 18, 16), (252, 248, 236), seed=3, nspots=22, rs=(0.04, 0.075)))
    sv('cap_yellow', tex_cap((252, 206, 40), (240, 170, 30), (236, 90, 30), seed=7, nspots=30, rs=(0.03, 0.06)))
    for nm, base, rim, spot in (('toad_a', (214, 30, 26), (190, 20, 18), (250, 246, 236)), ('toad_b', (250, 200, 50), (236, 160, 30), (220, 70, 30))):
        sv(nm + '_cap', tex_cap(base, rim, spot, 256, seed=len(nm), nspots=10, rs=(0.05, 0.09)))
    sv('stem_cream', tex_stem()); sv('stem_house', tex_stem(256, 9, (246, 238, 214))); sv('gills_cream', tex_gills())
    sv('spot_orange', tex_solid((240, 110, 30), 64, 6, 3)); sv('wood_red', tex_solid((170, 50, 40), 64, 6, 4))
    sv('bark_tree', tex_bark())
    for k, c in (('gb_red', (220, 30, 36)), ('gb_yellow', (250, 210, 30)), ('gb_blue', (36, 80, 210)), ('gb_green', (30, 170, 80)),
                 ('gb_orange', (250, 126, 20)), ('gb_pink', (244, 100, 170))):
        sv(k, tex_solid(c, 64, 2, len(k)))
    for des in ('spiral', 'star', 'flower', 'rings', 'swirl'):
        sv('lolli_' + des, tex_lolli(des, seed=len(des))); sv('rim_' + des, tex_solid(LOLLI_RIM[des], 64, 3, 5))
    sv('stick', tex_solid((246, 244, 236), 64, 2, 6))
    sv('stripe_rw', tex_stripes([(250, 250, 248), (214, 24, 30)], k=4))
    sv('stripe_gw', tex_stripes([(250, 250, 248), (40, 170, 70)], k=4))
    sv('jaw_a', tex_swirlball([(240, 70, 40), (250, 150, 40), (250, 230, 200), (200, 40, 40)], seed=1))
    sv('jaw_b', tex_swirlball([(244, 120, 180), (252, 240, 246), (200, 60, 140)], seed=2))
    sv('jaw_c', tex_swirlball([(120, 70, 190), (250, 220, 60), (60, 180, 90), (40, 140, 220)], seed=3))
    sv('jaw_d', tex_swirlball([(150, 90, 50), (240, 210, 170), (110, 60, 30)], seed=4))
    sv('urn_black', tex_solid((24, 24, 28), 64, 3, 7)); sv('stone_sand', tex_stone())
    sv('leaf_green', tex_leaf()); sv('petal_yellow', tex_solid((252, 222, 50), 64, 4, 8))
    for k, c in (('candy_red', (220, 40, 46)), ('candy_yellow', (250, 214, 40)), ('candy_blue', (40, 110, 220)), ('candy_pink', (246, 120, 180)),
                 ('candy_white', (248, 246, 240))):
        sv(k, tex_solid(c, 64, 3, len(k)))
    sv('iron_teal', tex_iron((54, 96, 96))); sv('iron_teal_in', tex_iron((40, 70, 70), seed=8)); sv('iron_dark', tex_iron((40, 42, 46), rivets=False))
    sv('roof_plate', tex_iron((70, 74, 76), seed=9)); sv('glass', tex_glass()); sv('glass_pipe', tex_glass(64, (210, 236, 250)))
    sv('brass', tex_solid((200, 160, 60), 64, 6, 10)); sv('copper', tex_solid((190, 100, 56), 128, 8, 11))
    for k, c in (('enamel_red', (210, 40, 40)), ('enamel_pink', (236, 110, 170)), ('enamel_yellow', (240, 200, 40)), ('enamel_white', (236, 236, 228))):
        sv(k, tex_solid(c, 64, 3, len(k)))
    sv('gauge', tex_glow((250, 240, 200))); sv('lamp_warm', tex_glow((255, 220, 150)))
    sv('sign_pump', tex_label('PUMP\nHOUSE', (40, 70, 70), (250, 214, 90), 256, 64))
    sv('chocfall', tex_chocfall()); sv('chocsplash', tex_choc_surface())
    sm = tex_chocfall(128, 256, 77)
    al = np.clip(_noise(128, 3, 78, 256) * 120 - 60, 0, 200)
    sv('choc_smear', sm, al)
    sv('boat_pink', tex_boat()); sv('trim_white', tex_solid((250, 246, 248), 64, 3, 12)); sv('wafer', tex_wafer()); sv('swan', tex_swan())
    sv('beak', tex_solid((250, 150, 40), 32, 3, 13)); sv('eye_black', tex_solid((10, 10, 12), 32, 1, 14))
    for k, c in (('pink', (250, 180, 220)), ('blue', (160, 220, 255)), ('yellow', (255, 236, 140))):
        sv('crys_' + k, tex_crystal(c, seed=len(k)))
    for k, c in (('blue', (90, 170, 230)), ('pink', (240, 120, 190)), ('green', (120, 220, 120))):
        sv('bottle_' + k, tex_solid(c, 64, 4, len(k) + 20))
    sv('label_fizzy', tex_label('FIZZY\nLIFTING', (250, 246, 230), (200, 40, 80), 256, 128))
    sv('fan_blade', tex_solid((120, 124, 130), 64, 6, 15))
    sv('wrap_red', tex_stripes([(230, 40, 50), (250, 240, 240)], k=3, seed=2)); sv('wrap_teal', tex_stripes([(40, 190, 190), (250, 250, 250)], k=3, seed=3))
    sv('chocbar', tex_chocbar()); sv('wrapper_purple', tex_wrapper((110, 40, 120), 'CHOCOLATE')); sv('foil_gold', tex_solid((230, 190, 80), 64, 10, 16))
    sv('cupcase_pink', tex_cupcase()); sv('frosting_white', tex_frosting((250, 236, 240)))
    sv('petal_pink', tex_solid((246, 120, 180), 64, 4, 17)); sv('petal_violet', tex_solid((160, 90, 220), 64, 4, 18))
    sv('petal_red', tex_solid((230, 50, 50), 64, 4, 19))
    sv('ticket', tex_ticket()); sv('env', tex_env())
    import candy_textures as _T
    sv('rock_lump', _T.rock(256, 91, (178, 168, 150)))
    # ---- models
    redcap(); yellowhouse()
    toadstool('toad_a', 0, 0, 0, 90, 60, 1); toadstool('toad_b', 0, 0, 0, 70, 50, 2)
    flowertree('flowertree_w', ['red', 'yellow', 'orange', 'blue', 'green', 'pink', 'navy', 'violet'], 21, True)
    flowertree('flowertree_e', ['yellow', 'red', 'pink', 'white', 'orange', 'lime', 'violet'], 37, False)
    gumtree()
    for des in ('spiral', 'star', 'flower', 'rings', 'swirl'): lollipop(des)
    spin_disc('swirl'); spin_disc('spiral'); stickonly()
    cane(); cane_arch()
    for k in ('a', 'b', 'c', 'd'): jawbreaker(k)
    urn(); buttercup(); twisty()
    shed(); pump(); deck_frame(); pipes_deck()
    waterfall(); splash(); outlet()
    boat(); bridge(); pedestal(); lamppost(); truss(); wallpipes()
    crystal('crystal_a', ['pink', 'blue'], 3); crystal('crystal_b', ['yellow', 'pink'], 4)
    bottle('blue', 0); bottle('pink', 0); bottle('green', 0); fan(); boulder('boulder_a', 3); boulder('boulder_b', 8)
    bonbon('bonbon_a', 'wrap_red'); bonbon('bonbon_b', 'wrap_teal'); chocbar(); cupcake()
    candyflower('flower_a', 'petal_pink', 1); candyflower('flower_b', 'petal_violet', 2); candyflower('flower_c', 'petal_red', 3)


def make_aug(start, land, apex):
    return augpipe(start, land, apex)


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/candy_models'
    make(o)
    make_aug((L.PIPE_START[0], L.PIPE_START[1], -8), (L.PIPE_LAND[0], L.PIPE_LAND[1], L.SUMMIT_Z), 1320)
    import md3tool
    for fn in sorted(os.listdir(os.path.join(o, MD))):
        if fn.endswith('.md3'):
            m = md3tool.load(os.path.join(o, MD, fn))
            V = np.concatenate([s['verts'] for s in m['surfaces']])
            print(fn, sum(len(s['verts']) for s in m['surfaces']), 'verts', sum(len(s['tris']) for s in m['surfaces']), 'tris',
                  V.min(0).round(1), V.max(0).round(1), PLACE.get(fn[:-4]))
    open(os.path.join(o, 'models.shader'), 'w').write(shaders())
