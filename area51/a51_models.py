"""Custom MD3 map objects for wop_padarea51 (Area 51: Dreamland). All geometry and art is original and generated here.

    make(out) -> writes models/padarea51/*.md3 (+ IQM movers) and their images, returns the shader text

Scale: ~64u per metre (Padman is a small fellow on a full-size airbase). Origin = base centre unless noted. The
geometry constants below are shared with build_area51.py so the invisible collision brushes match the visible MD3s.

Big pieces (lightmapped): hangar (Hangar 18 shell), saucer (the flying saucer inside), saucer_crash (the crashed scout,
built tilted and clipped at the crater floor), tower (control tower), watertower, radar_base, quonset, jet (black
triangle), airstairs, bunker (S-4 blockhouse), booth + boom, floodlight, fueltank, container, generator.
Props (vertex lit): drums, crates, jersey barriers, sandbags, humvee, forklift, lab furniture (specimen tanks with
greys, autopsy table, server racks, consoles, lockers), bunks, joshua trees, tumbleweeds, rocks, cow, mailbox.
Movers (model2, lightingDiffuse): radar_dish, searchlight beams, the hovering scout with its tractor beam + cow (IQM),
the UFO circling the sky (IQM), the mothership's spinning core.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, save_md3, grid_normals, rot_z, rot_axis, frame
import md3write, iqmtool

MD = 'models/padarea51'
OUT = None
REG = {}
PLACE = {}          # model name -> (path, scale, zoff)
IQM = {}            # mover name -> path

# ================================================================================================= shared geometry
# Hangar 18 (centre north). Outer walls x +-HG_X, y HG_Y0..HG_Y1, 32 thick, eave HG_H, segmental arch roof to HG_RIDGE.
HG_X, HG_Y0, HG_Y1, HG_T = 960, 576, 1728, 32
HG_H, HG_RIDGE = 544, 736
HG_R = 2496.0
HG_ZC = HG_RIDGE - HG_R
HG_CY = (HG_Y0 + HG_Y1) / 2
HG_DOOR = (704, 448)                       # main door half width, height (south facade)
HG_NDOOR = (64, 160)                       # north personnel door half width, height
HG_SDOOR = (1504, 1632, 160)               # east/west side doors: y0, y1, height
HG_FACETS = 16                             # roof collision facets across x (120 wide)
HG_SKY = [(-360, -120, 1104, 1328), (120, 360, 1104, 1328)]   # roof skylights x0, x1, y0, y1 (on facet edges)
HG_CAT = 416                               # catwalk height


def hg_roof(x):
    return HG_ZC + math.sqrt(HG_R ** 2 - x * x)


# Flying saucer in the hangar
SC = (0.0, 1216.0)
S_BELLY, S_FLOOR, S_DECK_BOT, S_DECK = 200, 232, 384, 416
S_RIM, S_DECK_R, S_DOME_R, S_IN = 480, 288, 160, 264
S_RIM_BOT, S_RIM_TOP = 272, 304
S_RAMP = (11, 12)                          # sectors (16) with the belly ramp (south)
S_RAMP_R = (110, 340)                      # belly opening radii in the ramp sectors
S_RAMP_END = 546                           # ramp foot radius (z 0)
S_HATCH = (3, 4)                           # deck hatch sectors (north)
S_HATCH_R = (176, 264)
S_LEGS = (90, 210, 330)


def s_bot(r):
    """saucer underside z (collision) at radius r"""
    return S_BELLY if r <= 300 else S_BELLY + (r - 300) * (S_RIM_BOT - S_BELLY) / (S_RIM - 300)


def s_top(r):
    """saucer top z (collision) at radius r"""
    return S_DECK if r <= S_DECK_R else S_DECK - (r - S_DECK_R) * (S_DECK - S_RIM_TOP) / (S_RIM - S_DECK_R)


def s_ramp_z(r):
    return S_FLOOR - (r - S_RAMP_R[0]) * S_FLOOR / (S_RAMP_END - S_RAMP_R[0])


# Control tower (east)
TW = (1728.0, 896.0)
TW_SHAFT = 256                             # shaft half size (outer)
TW_CAB = 320                               # cab half size (outer)
TW_FLOOR, TW_SILL, TW_ROOF_BOT, TW_ROOF = 512, 576, 688, 704
TW_DOOR = (832, 960, 160)                  # west wall door y0, y1, height
TW_HATCH = (1824, 1984, 944, 1072)         # roof hatch x0, x1, y0, y1

# Water tower (north-east)
WT = (1856.0, 1696.0)
WT_LEG, WT_TANK_R, WT_Z0, WT_Z1, WT_CONE, WT_RING = 176, 240, 576, 800, 880, 352

# Radar station (west)
RD = (-1920.0, 1216.0)
RD_PLAT = (-2176, -1664, 960, 1472, 192)
RD_PED_R, RD_PED_Z, RD_DISH_Z = 72, 440, 520

# S-4 bunker (south-west)
BK = (-1664, -1152, -960, -576)            # x0, x1, y0, y1
BK_H, BK_DOOR = 240, (-832, -704, 160)

# quonset huts
HUTS = [(-1824.0, -1536.0), (-1120.0, -1536.0)]
HUT_R, HUT_L, HUT_T = 256, 320, 16         # outer radius, half length, shell thickness

# black triangle on the apron (nose west)
JET = (1408.0, -1088.0)
JET_NOSE, JET_TAIL, JET_SPAN = -416, 288, 448
JET_BELLY, JET_EDGE, JET_APEX = 96, 120, 224
JET_APEX_X = 40

# crater + crashed scout
CR = (0.0, -1024.0)
CR_R0, CR_R1, CR_D = 640, 384, 112         # top radius, floor radius, depth
CS_R = 300                                 # crashed scout radius
CS_TILT = 14.0                             # degrees, high side north
CS_Z = -92                                 # centre height of the lens (local origin)

# floodlight towers
FL_H = 640


# ================================================================================================= registry / helpers
def S(img, kind='lm', **opt):
    """register a model shader using models/padarea51/<img> (or a textures/... path)"""
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


def _save_iqm(name, X):
    """IQM writer front end: splits every surface into chunks under the renderer's 999-vertex limit"""
    meshes = []
    for i, (sh, Mm) in enumerate(X.m.items()):
        if not len(Mm): continue
        V, Nn, ST, T = np.array(Mm.V), np.array(Mm.N), np.array(Mm.ST), np.array(Mm.T)
        k0 = 0; part = 0
        while k0 < len(T):
            k1 = k0; used = {}
            while k1 < len(T) and len(set(used) | set(T[k1].tolist())) < 990:
                for v in T[k1].tolist(): used.setdefault(v, len(used))
                k1 += 1
            idx = np.array(sorted(used, key=used.get))
            remap = {v: j for j, v in enumerate(idx)}
            tt = np.vectorize(remap.get)(T[k0:k1])
            meshes.append(dict(name=f'{name}{i}_{part}', material=sh, verts=V[idx], normals=Nn[idx], st=ST[idx], tris=tt))
            k0 = k1; part += 1
    path = f'{MD}/{name}.iqm'
    iqmtool.save(os.path.join(OUT, path), meshes)
    IQM[name] = path
    return path


def revolve_grid(M, rows, n_ang=48, holes=(), u_tiles=4.0, v_of=None, inward=False, cx=0.0, cy=0.0, deform=None, a_off=0.0):
    """surface of revolution through rows [(r, z)...]; angular cells (360/n_ang deg) skipped where a hole
    (a0, a1, z0, z1[, r0, r1]) in degrees covers the cell centre."""
    rows = np.asarray(rows, float)
    angs = np.linspace(0, 360, n_ang + 1) + a_off
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
        UV[:, j, 0] = (a - a_off) / 360 * u_tiles
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
            am = ((angs[j] + angs[j + 1]) / 2) % 360
            skip = False
            for h in holes:
                a0, a1, z0, z1 = h[:4]
                r0, r1 = (h[4], h[5]) if len(h) > 4 else (-1, 1e9)
                inang = a0 <= am <= a1 or a0 <= am + 360 <= a1
                if inang and z0 - 1e-3 <= (za + zb) / 2 <= z1 + 1e-3 and r0 - 1e-3 <= (ra + rb) / 2 <= r1 + 1e-3:
                    skip = True
            if skip: continue
            a, b, c2, d = o + i * nc + j, o + i * nc + j + 1, o + (i + 1) * nc + j, o + (i + 1) * nc + j + 1
            M.tri(a, b, c2); M.tri(b, d, c2)


def wall(M, origin, udir, n, u0, u1, z0, z1, holes=(), tile=128.0, back=None, t=0.0, jambs=True, uoff=0.0):
    """vertical wall face: points origin + u*udir + (0,0,z) for u in [u0,u1], z in [z0,z1], facing n, rectangular holes
    [(ua, ub, za, zb)] cut out. back: also build the opposite face t units behind (and hole jambs)."""
    import wopmap
    o = np.asarray(origin, float); ud = np.asarray(udir, float); nn = np.asarray(n, float)
    rects = wopmap.sub_rects((u0, z0, u1, z1), [(a, c, b, d) for (a, b, c, d) in holes])
    for side, off in ((1, 0.0), (-1, -t)) if back else ((1, 0.0),):
        for (ua, za, ub, zb) in rects:
            P = [o + ud * u + np.array([0, 0, z]) + nn * off for (u, z) in ((ua, za), (ub, za), (ub, zb), (ua, zb))]
            uv = [((u + uoff) / tile * side, -z / tile) for (u, z) in ((ua, za), (ub, za), (ub, zb), (ua, zb))]
            M.poly(P, nn * side, uv)
    if back and jambs:
        for (a, b, c, d) in holes:
            for (pa, pb, nrm) in (((a, c), (a, d), ud), ((b, c), (b, d), -ud), ((a, d), (b, d), np.array([0, 0, -1.0])),
                                  ((a, c), (b, c), np.array([0, 0, 1.0]))):
                if nrm[2] > 0.5 and c <= z0 + 1e-3: continue          # door sill at the floor
                q0 = o + ud * pa[0] + np.array([0, 0, pa[1]]); q1 = o + ud * pb[0] + np.array([0, 0, pb[1]])
                P = [q0, q1, q1 - nn * t, q0 - nn * t]
                L = np.linalg.norm(q1 - q0)
                M.poly(P, nrm, [(0, 0), (L / tile, 0), (L / tile, t / tile), (0, t / tile)])


def boxm(M, mn, mx, tile=64.0, faces='nsewtb'):
    rbox(M, mn, mx, r=0.01, k=2, tile=tile, faces=faces)


def cyl_m(M, c, r, z0, z1, n=16, caps=True, tile=64.0, utiles=None):
    c = np.asarray(c, float)
    revolve(M, [(r, z0), (r, z1)], u_tiles=utiles or max(1, round(2 * math.pi * r / tile)), n=n, cx=c[0], cy=c[1], vlen=tile)
    if caps:
        disc(M, r, z1, True, n, c[0], c[1]); disc(M, r, z0, False, n, c[0], c[1])


def htube(M, p0, p1, r, nseg=10, caps=True):
    tube(M, [p0, p1], r, nseg=nseg, caps=(caps, caps))


def lattice(M, pts_bottom, pts_top, r, levels):
    """lattice mast: corner tubes between bottom and top rings of points, zig-zag braces between levels"""
    nb = len(pts_bottom)
    B = np.asarray(pts_bottom, float); T = np.asarray(pts_top, float)
    for i in range(nb): tube(M, [B[i], T[i]], r, nseg=6)
    for k in range(levels):
        t0, t1 = k / levels, (k + 1) / levels
        for i in range(nb):
            a0 = B[i] + (T[i] - B[i]) * t0; b1 = B[(i + 1) % nb] + (T[(i + 1) % nb] - B[(i + 1) % nb]) * t1
            tube(M, [a0, b1], r * 0.6, nseg=5, caps=(False, False))
            a1 = B[i] + (T[i] - B[i]) * t1; b1h = B[(i + 1) % nb] + (T[(i + 1) % nb] - B[(i + 1) % nb]) * t1
            tube(M, [a1, b1h], r * 0.6, nseg=5, caps=(False, False))


def transform_mesh(Msrc, R, t):
    Msrc.V = [R @ v + np.asarray(t, float) for v in Msrc.V]; Msrc.N = [R @ n for n in Msrc.N]


def lathe_profile(prof, n=24):
    """smooth a polyline profile [(r, z)] with Catmull-Rom (n points per segment)"""
    P = np.asarray(prof, float)
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, len(P) - 1)]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return [tuple(p) for p in out]


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


def _fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + _C(col) + _noise(n, 1.2, seed, m)[..., None] * grain + _noise(n, 12, seed + 1, m)[..., None] * grain


FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
if not os.path.exists(FONT): FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def _font(sz): return ImageFont.truetype(FONT, sz)


def tex_corr(w=256, h=256, seed=1, col=(120, 128, 118)):
    """corrugated sheet metal: vertical ribs (u across), panel laps, rust streaks"""
    x, y = _xy(w, h)
    rib = np.sin(x * 2 * math.pi * 8)
    a = _fill(w, col, 4, seed, h) + (rib * 16)[..., None]
    a += (np.clip(_noise(w, 2, seed + 2, h) * 0.5, 0, 1) * np.clip(_noise(w, 30, seed + 3, h), 0, 1))[..., None] * _C((40, 10, -10))
    a[(np.abs(y - 0.5) < 0.006)] *= 0.75
    return a


def tex_hull(n=512, seed=3, col=(176, 182, 190)):
    """saucer hull: brushed alloy with concentric panel seams (v = radius) and rivets"""
    x, y = _xy(n)
    a = _fill(n, col, 3, seed) + (_noise(n, 0.6, seed + 1) * 4)[..., None]
    im = _img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, n // 8): d.line([(0, k), (n, k)], fill=(110, 116, 124), width=3)
    for k in range(0, n, n // 16): d.line([(k, 0), (k, n)], fill=(130, 136, 144), width=2)
    for k in range(0, n, n // 8):
        for j in range(8, n, 16): d.ellipse((j - 2, k + 5, j + 2, k + 9), fill=(150, 154, 160))
    return np.asarray(im, np.float32)


def tex_alien_wall(w=256, h=256, seed=5):
    a = _fill(w, (60, 56, 76), 4, seed, h)
    im = _img(a); d = ImageDraw.Draw(im)
    for k in range(0, w, 64):
        d.line([(k, 0), (k, h)], fill=(70, 230, 210), width=2)
    for (y0, y1) in ((40, 80), (150, 200)):
        for k in range(0, w, 64):
            d.rounded_rectangle((k + 10, y0, k + 54, y1), 8, outline=(90, 255, 220), width=2)
            for j in range(3): d.ellipse((k + 16 + j * 12, y0 + 12, k + 22 + j * 12, y0 + 18), fill=(255, 120, 200))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), np.float32)


def tex_glyphs(w=512, h=64, seed=7):
    """alien writing (glowing) for rims and consoles"""
    im = Image.new('RGB', (w, h), (8, 20, 18)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    x = 6
    while x < w - 30:
        cx = x + 14; cy = h / 2
        for _ in range(rng.integers(2, 4)):
            kind = rng.integers(0, 3)
            if kind == 0: d.ellipse((cx - 8, cy - 8 + rng.integers(-6, 6), cx + 8, cy + 8 + rng.integers(-6, 6)), outline=(80, 255, 200), width=2)
            elif kind == 1: d.line([(cx - 9, cy - rng.integers(-14, 14)), (cx + 9, cy + rng.integers(-14, 14))], fill=(80, 255, 200), width=2)
            else: d.arc((cx - 10, cy - 14, cx + 10, cy + 14), rng.integers(0, 180), rng.integers(180, 360), fill=(80, 255, 200), width=2)
        x += 30
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), np.float32)


def tex_glow(col, n=64, edge=None):
    a = np.zeros((n, n, 3), np.float32) + _C(col)
    y, x = np.mgrid[0:n, 0:n] / n
    r = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    a *= (1.0 - 0.35 * np.clip(r * 2, 0, 1) ** 2)[..., None]
    return a


def tex_concrete(n=256, seed=9, col=(150, 148, 142)):
    a = _fill(n, col, 7, seed) + _noise(n, 1, seed + 1)[..., None] * 6 + _noise(n, 30, seed + 2)[..., None] * 9
    st = np.clip(_noise(n, 3, seed + 4) * 0.3, 0, 1)
    y = np.linspace(0, 1, n)[:, None]
    a *= (1 - 0.12 * st * y)[..., None]
    im = _img(a); d = ImageDraw.Draw(im)
    d.line([(0, n - 1), (n, n - 1)], fill=tuple(int(v * 0.7) for v in col), width=2)
    return np.asarray(im, np.float32)


def tex_stencil(text, w=512, h=256, bg=(150, 148, 142), fg=(30, 30, 30), seed=11, alpha=False):
    if alpha:
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    else:
        im = _img(tex_concrete(max(w, h), seed, bg)[:h, :w])
    d = ImageDraw.Draw(im)
    sz = h
    while sz > 8:
        f = _font(sz); l, t, r, b = d.textbbox((0, 0), text, font=f)
        if r - l < w * 0.92 and b - t < h * 0.86: break
        sz -= 4
    d.text((w / 2 - (r - l) / 2 - l, h / 2 - (b - t) / 2 - t), text, font=f, fill=fg + ((255,) if alpha else ()))
    # stencil bridges
    for k in range(1, 4): d.line([(0, h * k / 4), (w, h * k / 4)], fill=(0, 0, 0, 0) if alpha else bg, width=3)
    return im


def tex_tank(w=256, h=256, seed=13):
    """water tank: white with red checker band near the top (v=0 top)"""
    x, y = _xy(w, h)
    a = _fill(w, (225, 225, 220), 4, seed, h)
    band = (y < 0.28) & (y > 0.08)
    chk = ((np.floor(x * 8) + np.floor(y * 8 / 0.25 * 0.25 * 4)) % 2 == 0)
    a[band & chk] = _C((200, 40, 30)) + _noise(w, 1, seed + 1, h)[band & chk][:, None] * 4
    streak = np.clip(_noise(w, 2, seed + 2, h) * 0.3, 0, 1) * y
    return a * (1 - 0.25 * streak)[..., None]


def tex_stealth(n=512, seed=15):
    a = _fill(n, (34, 35, 40), 3, seed) + _noise(n, 0.8, seed + 1)[..., None] * 3
    im = _img(a); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed + 2)
    for _ in range(40):
        x0, y0 = rng.integers(0, n, 2); L = rng.integers(40, 200)
        if rng.random() < 0.5: d.line([(x0, y0), (x0 + L, y0)], fill=(22, 22, 26), width=2)
        else: d.line([(x0, y0), (x0 + L * 0.6, y0 + L * 0.6)], fill=(22, 22, 26), width=2)
    return np.asarray(im, np.float32)


def tex_drum(w=128, h=128, col=(200, 160, 30), seed=17, label=True):
    x, y = _xy(w, h)
    a = _fill(w, col, 5, seed, h)
    for yy in (0.33, 0.66): a[np.abs(y - yy) < 0.02] *= 0.7
    a += np.clip(_noise(w, 2, seed + 1, h), 0, 2)[..., None] * _C((-20, -25, -25)) * (_noise(w, 20, seed + 2, h) > 0.5)[..., None]
    if label:
        im = _img(a); d = ImageDraw.Draw(im)
        d.rectangle((w * 0.35, h * 0.4, w * 0.65, h * 0.6), fill=(240, 240, 235))
        d.polygon([(w * 0.5, h * 0.42), (w * 0.43, h * 0.57), (w * 0.57, h * 0.57)], outline=(20, 20, 20), width=2)
        a = np.asarray(im, np.float32)
    return a


def tex_crate(n=256, seed=19, text='TOP SECRET'):
    x, y = _xy(n)
    a = _fill(n, (150, 118, 76), 6, seed) + (np.sin(y * 2 * math.pi * 30 + _noise(n, 3, seed + 1) * 2) * 6)[..., None]
    im = _img(a); d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in ((0, 0, n, 20), (0, n - 20, n, n), (0, 0, 20, n), (n - 20, 0, n, n)):
        d.rectangle((x0, y0, x1, y1), fill=(120, 92, 58))
    d.line([(20, 20), (n - 20, n - 20)], fill=(120, 92, 58), width=16)
    if text:
        f = _font(int(n * 0.11)); l, t, r, b = d.textbbox((0, 0), text, font=f)
        d.rectangle((n / 2 - (r - l) / 2 - 8, n * 0.42, n / 2 + (r - l) / 2 + 8, n * 0.42 + (b - t) + 14), fill=(150, 118, 76))
        d.text((n / 2 - (r - l) / 2 - l, n * 0.42 + 7 - t), text, font=f, fill=(170, 30, 25))
    return np.asarray(im, np.float32)


def tex_barrier(w=256, h=128, seed=21):
    x, y = _xy(w, h)
    a = tex_concrete(w, seed)[:h] if h <= w else tex_concrete(h, seed)[:, :w]
    s = ((np.floor(x * 8 + y * 2) % 2) == 0) & (y > 0.55) & (y < 0.78)
    a[s] = _C((200, 40, 30)); a[(y > 0.55) & (y < 0.78) & ~s] = _C((235, 235, 230))
    return a


def tex_sandbag(n=128, seed=23):
    a = _fill(n, (150, 132, 92), 7, seed) + _noise(n, 0.7, seed + 1)[..., None] * 8
    x, y = _xy(n)
    a *= (0.85 + 0.15 * np.sin(y * math.pi * 4) ** 2)[..., None]
    return a


def tex_camo(n=256, seed=25):
    a = np.zeros((n, n, 3), np.float32) + _C((170, 150, 110))
    for (col, sd, th) in (((120, 100, 70), 1, 0.4), ((90, 80, 60), 2, 0.8), ((190, 175, 140), 3, 1.0)):
        m = _noise(n, 10, seed + sd) > th
        a[m] = _C(col)
    return a + _noise(n, 1, seed + 9)[..., None] * 4


def tex_skin(n=128, seed=27, col=(160, 170, 160)):
    return _fill(n, col, 5, seed) + _noise(n, 3, seed + 1)[..., None] * 5


def tex_cow(n=256, seed=29):
    a = np.zeros((n, n, 3), np.float32) + _C((240, 238, 230))
    m = _noise(n, 12, seed) > 0.55
    a[m] = _C((30, 28, 26))
    return a + _noise(n, 1, seed + 1)[..., None] * 4


def tex_liquid(n=128, seed=31):
    x, y = _xy(n)
    a = np.zeros((n, n, 3), np.float32) + _C((40, 200, 90))
    a += (np.sin(y * 20 + _noise(n, 6, seed) * 2) * 20)[..., None] * _C((0.3, 1, 0.5))
    rng = np.random.default_rng(seed)
    im = _img(a); d = ImageDraw.Draw(im)
    for _ in range(30):
        px, py = rng.integers(0, n, 2); r = rng.integers(1, 4)
        d.ellipse((px - r, py - r, px + r, py + r), outline=(200, 255, 220))
    return np.asarray(im, np.float32)


def tex_screen(w=256, h=128, seed=33, kind='radar'):
    im = Image.new('RGB', (w, h), (5, 20, 12)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    if kind == 'radar':
        for k in range(2):
            cx = w * (0.25 + 0.5 * k); cy = h / 2; r = h * 0.42
            for rr in (r, r * 0.66, r * 0.33): d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(40, 200, 90), width=2)
            d.line([(cx, cy), (cx + r * 0.9, cy - r * 0.4)], fill=(120, 255, 150), width=3)
            for _ in range(5):
                a = rng.uniform(0, 6.28); rr = rng.uniform(0.1, 0.9) * r
                d.ellipse((cx + rr * math.cos(a) - 3, cy + rr * math.sin(a) - 3, cx + rr * math.cos(a) + 3, cy + rr * math.sin(a) + 3), fill=(180, 255, 180))
    else:
        for row in range(8):
            y = 8 + row * 14
            L = rng.integers(40, w - 20)
            d.line([(10, y), (10 + L, y)], fill=(80, 220, 255) if row % 3 else (255, 200, 80), width=6)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.7)), np.float32)


def tex_rack(w=128, h=256, seed=35):
    a = _fill(w, (30, 32, 36), 3, seed, h)
    im = _img(a); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for k in range(0, h, 20):
        d.rectangle((6, k + 2, w - 6, k + 18), outline=(60, 62, 68), width=1)
        for j in range(4):
            c = [(60, 255, 120), (255, 180, 40), (80, 160, 255)][rng.integers(0, 3)]
            d.rectangle((w - 30 + j * 6, k + 8, w - 27 + j * 6, k + 11), fill=c)
    return np.asarray(im, np.float32)


def tex_paint(col, n=64, seed=37, grain=4):
    return _fill(n, col, grain, seed)


def tex_beam(w=64, h=256):
    """vertical gradient for additive light beams (v=0 at the emitter)"""
    x, y = _xy(w, h)
    edge = np.clip(1 - np.abs(x - 0.5) * 2, 0, 1) ** 0.6
    fall = np.clip(1 - y, 0, 1) ** 1.3
    a = (edge * fall * 0.6 + 0.08 * fall)[..., None] * _C((255, 255, 255))
    a += (np.sin(y * 40) * 6)[..., None] * fall[..., None]
    return np.clip(a, 0, 255)


def tex_tumble(n=256, seed=39):
    """tumbleweed twig scribble (alpha)"""
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for _ in range(220):
        x0, y0 = rng.uniform(0, n, 2); a = rng.uniform(0, 2 * math.pi); L = rng.uniform(10, 50)
        c = tuple(int(v) for v in (rng.uniform(120, 170), rng.uniform(95, 130), rng.uniform(60, 80))) + (255,)
        d.line([(x0, y0), (x0 + math.cos(a) * L, y0 + math.sin(a) * L)], fill=c, width=2)
    return im


def tex_joshua_leaf(w=128, h=128, seed=41):
    """spiky leaf cluster (alpha): radial blades"""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    cx, cy = w / 2, h / 2
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi); L = rng.uniform(0.25, 0.48) * w
        col = (int(rng.uniform(70, 110)), int(rng.uniform(110, 150)), int(rng.uniform(60, 80)), 255)
        d.line([(cx, cy), (cx + math.cos(a) * L, cy + math.sin(a) * L)], fill=col, width=2)
    return im


def tex_bark(w=128, h=256, seed=43):
    x, y = _xy(w, h)
    a = _fill(w, (100, 84, 62), 6, seed, h)
    sc = np.sin((y * 30 + x * 6 + _noise(w, 3, seed + 1, h) * 0.6) * math.pi * 2)
    a += (np.sign(sc) * 10)[..., None]
    return a


def tex_rock(n=256, seed=45):
    x, y = _xy(n)
    layers = np.sin((y * 10 + _noise(n, 20, seed) * 0.3) * 2 * math.pi)
    return _fill(n, (160, 112, 80), 8, seed) + (layers * 12)[..., None] + _noise(n, 5, seed + 1)[..., None] * 10


def tex_dish(n=256, seed=47):
    x, y = _xy(n)
    a = _fill(n, (225, 228, 230), 3, seed)
    a[(np.abs(np.sin(x * math.pi * 24)) < 0.05) | (np.abs(np.sin(y * math.pi * 12)) < 0.05)] *= 0.82
    return a


def tex_glassy(n=64, col=(60, 90, 110)):
    x, y = _xy(n)
    return np.zeros((n, n, 3), np.float32) + _C(col) + (y * 30)[..., None]


def tex_env(n=128, seed=49):
    """sky-ish reflection map for chrome/glass (night: dark with a bright band)"""
    x, y = _xy(n)
    a = _lerp(_C((20, 24, 40)), _C((140, 150, 190)), np.clip(1 - np.abs(y - 0.45) * 3, 0, 1)[..., None])
    return a + _noise(n, 4, seed)[..., None] * 8


def tex_num18(w=512, h=256):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = _font(int(h * 0.95)); l, t, r, b = d.textbbox((0, 0), '18', font=f)
    d.text((w / 2 - (r - l) / 2 - l, h / 2 - (b - t) / 2 - t), '18', font=f, fill=(245, 205, 40, 255))
    return im


def tex_mailbox(n=128, seed=51):
    a = _fill(n, (22, 22, 24), 3, seed)
    im = _img(a); d = ImageDraw.Draw(im)
    d.text((10, n * 0.4), 'U.S. MAIL', font=_font(16), fill=(220, 220, 220))
    return np.asarray(im, np.float32)


# ================================================================================================= HANGAR 18
def hangar():
    X = Model()
    corr = S('corr', 'lm'); inner = S('corr_in', 'lm'); roof = S('corr_roof', 'lm'); rin = S('corr_in', 'lm', tag='r')
    beam = S('beam', 'lm'); lamp = S('lamp_white', 'glow', light=0, rgb='1 1 1'); num = S('num18', 'alpha')
    stripe = S('hazard', 'lm', tex=True)
    cy = HG_CY
    y0, y1 = HG_Y0 - cy, HG_Y1 - cy           # local y of south/north outer faces
    xw, t = HG_X, HG_T
    dw, dh = HG_DOOR
    # ---- side walls (east/west), with personnel doors
    for sx in (-1, 1):
        sy0, sy1, sdh = HG_SDOOR
        hole = [(sy0 - cy, sy1 - cy, 0, sdh)]
        wall(X.mesh(corr), (sx * xw, 0, 0), (0, 1, 0), (sx, 0, 0), y0, y1, 0, HG_H, hole, tile=192, back=False)
        wall(X.mesh(inner), (sx * (xw - t), 0, 0), (0, 1, 0), (-sx, 0, 0), y0 + t, y1 - t, 0, HG_H, hole, tile=192, back=False)
        for (ua, ub, nrm) in ((sy0 - cy, sy0 - cy, (0, 1, 0)), (sy1 - cy, sy1 - cy, (0, -1, 0))):
            X.mesh(beam).quad((sx * xw, ua, 0), (sx * xw, ua, sdh), (sx * (xw - t), ua, sdh), (sx * (xw - t), ua, 0), 64, n=nrm)
        X.mesh(beam).quad((sx * xw, sy0 - cy, sdh), (sx * xw, sy1 - cy, sdh), (sx * (xw - t), sy1 - cy, sdh), (sx * (xw - t), sy0 - cy, sdh), 64, n=(0, 0, -1))
        # door frame + canopy
        for yy in (sy0 - cy - 8, sy1 - cy + 8):
            boxm(X.mesh(beam), (sx * xw - (12 if sx > 0 else -12) * 0 + min(0, sx * 12), yy - 8, 0), (sx * xw + max(0, sx * 12), yy + 8, sdh + 16))
        boxm(X.mesh(beam), (min(sx * xw, sx * (xw + 12)), sy0 - cy - 16, sdh), (max(sx * xw, sx * (xw + 12)), sy1 - cy + 16, sdh + 16))
        boxm(X.mesh(roof), (min(sx * xw, sx * (xw + 64)), sy0 - cy - 32, sdh + 40), (max(sx * xw, sx * (xw + 64)), sy1 - cy + 32, sdh + 48))
    # ---- gable walls (south with the big door, north with a personnel door)
    archx = np.linspace(-xw, xw, 33)
    for (yo, yi, nrm, holes) in ((y0, y0 + t, -1, [(-dw, dw, 0, dh)]), (y1, y1 - t, 1, [(-HG_NDOOR[0], HG_NDOOR[0], 0, HG_NDOOR[1])])):
        wall(X.mesh(corr), (0, yo, 0), (1, 0, 0), (0, nrm, 0), -xw, xw, 0, HG_H, holes, tile=192)
        wall(X.mesh(inner), (0, yi, 0), (1, 0, 0), (0, -nrm, 0), -xw + t, xw - t, 0, 500, holes, tile=192)
        pts = [(x, yo, hg_roof(abs(x))) for x in archx] + [(xw, yo, HG_H), (-xw, yo, HG_H)]
        X.mesh(corr).poly(pts, (0, nrm, 0), [(p[0] / 192, -p[2] / 192) for p in pts])
        xi = np.linspace(-xw + t, xw - t, 33)
        pts = [(x, yi, hg_roof(abs(x)) - t) for x in xi] + [(xw - t, yi, 500), (-xw + t, yi, 500)]
        X.mesh(inner).poly(pts, (0, -nrm, 0), [(p[0] / 192, -p[2] / 192) for p in pts])
        a, b, c, d = holes[0]
        for (ua, nrm2) in ((a, (1, 0, 0)), (b, (-1, 0, 0))):
            X.mesh(beam).quad((ua, yo, 0), (ua, yo, d), (ua, yi, d), (ua, yi, 0), 64, n=nrm2)
        X.mesh(beam).quad((a, yo, d), (b, yo, d), (b, yi, d), (a, yi, d), 64, n=(0, 0, -1))
    # big door: steel portal frame + hazard-striped jambs + top rail, the numbers on the gable
    boxm(X.mesh(beam), (-dw - 24, y0 - 24, 0), (-dw, y0 + 4, dh + 24))
    boxm(X.mesh(beam), (dw, y0 - 24, 0), (dw + 24, y0 + 4, dh + 24))
    boxm(X.mesh(beam), (-dw - 24, y0 - 24, dh), (dw + 24, y0 + 4, dh + 32))
    for sx in (-1, 1):
        X.mesh(stripe).quad((sx * (dw + 1), y0 - 25, 0), (sx * (dw + 23), y0 - 25, 0), (sx * (dw + 23), y0 - 25, 120), (sx * (dw + 1), y0 - 25, 120), 48, n=(0, -1, 0))
    # sliding door leaves parked at both ends of the opening, outside the facade on their rail
    for sx in (-1, 1):
        for k in range(2):
            xa = sx * (dw + 40 + k * 20); xb = sx * (xw - 4 + k * 0)
            boxm(X.mesh(corr), (min(xa, sx * (dw + 40 + k * 20 + 230)), y0 - 48 - k * 18, 0), (max(xa, sx * (dw + 40 + k * 20 + 230)), y0 - 34 - k * 18, dh - 8), tile=192)
    q = X.mesh(num)
    q.quad((-200, y0 - 1.5, 560), (200, y0 - 1.5, 560), (200, y0 - 1.5, 700), (-200, y0 - 1.5, 700), 400, n=(0, -1, 0))
    for v, st in zip(range(len(q.V) - 4, len(q.V)), ((0, 1), (1, 1), (1, 0), (0, 0))): q.ST[v] = st
    # ---- roof: outer arch with skylight holes, underside, eave + gable edges, gutters
    nx = 32
    xs = np.linspace(-xw - 16, xw + 16, nx + 1)
    for (msh, off, outward) in ((roof, 0.0, True), (rin, -t, False)):
        ys = np.array([y0 - 16, y1 + 16]) if msh == roof else np.array([y0 + t, y1 - t])
        cuts = sorted({float(v) for h in HG_SKY for v in (h[2] - cy, h[3] - cy)})
        ygrid = [ys[0]] + [c for c in cuts if ys[0] < c < ys[1]] + [ys[1]]
        Mm = X.mesh(msh)
        for i in range(nx):
            xa, xb = xs[i], xs[i + 1]
            if msh == rin: xa, xb = max(xa, -xw + t), min(xb, xw - t)
            if xb <= xa: continue
            for j in range(len(ygrid) - 1):
                ya, yb = ygrid[j], ygrid[j + 1]
                xm, ym = (xa + xb) / 2, (ya + yb) / 2 + cy
                if any(h[0] < xm < h[1] and h[2] < ym < h[3] for h in HG_SKY): continue
                za, zb = hg_roof(min(abs(xa), xw)) + off, hg_roof(min(abs(xb), xw)) + off
                if abs(xa) > xw: za = hg_roof(xw) + off - (abs(xa) - xw) * 0.4
                if abs(xb) > xw: zb = hg_roof(xw) + off - (abs(xb) - xw) * 0.4
                na = np.array([xa / HG_R, 0, math.sqrt(max(0.0, 1 - (xa / HG_R) ** 2))]); nb = np.array([xb / HG_R, 0, math.sqrt(max(0.0, 1 - (xb / HG_R) ** 2))])
                if not outward: na, nb = -na, -nb
                o = len(Mm.V)
                for (px, pz, nn) in ((xa, za, na), (xb, zb, nb)):
                    for py in (ya, yb):
                        Mm.add_v((px, py, pz), nn, (py / 192, px / 192))
                Mm.tri(o, o + 2, o + 1); Mm.tri(o + 1, o + 2, o + 3)
    # skylight curbs
    for (sx0, sx1, sy0, sy1) in HG_SKY:
        za = hg_roof(abs(sx0)); zb = hg_roof(abs(sx1))
        p = [(sx0, sy0 - cy, max(za, zb) + 12), (sx1, sy0 - cy, max(za, zb) + 12), (sx1, sy1 - cy, max(za, zb) + 12), (sx0, sy1 - cy, max(za, zb) + 12), (sx0, sy0 - cy, max(za, zb) + 12)]
        tube(X.mesh(beam), [(x, y, min(hg_roof(abs(x)), hg_roof(abs(x))) + 6) for (x, y, _) in p], 6, nseg=6)
    # eave fascia + gutters, gable barge boards
    for sx in (-1, 1):
        boxm(X.mesh(beam), (min(sx * xw, sx * (xw + 22)), y0 - 16, HG_H - 20), (max(sx * xw, sx * (xw + 22)), y1 + 16, HG_H - 2))
    for yy in (y0 - 16, y1 + 16):
        tube(X.mesh(beam), [(x, yy, hg_roof(min(abs(x), xw)) - 4) for x in np.linspace(-xw - 16, xw + 16, 25)], 8, nseg=6)
    # corner + intermediate steel columns on the outside
    for sx in (-1, 1):
        for yy in np.arange(y0, y1 + 1, 192):
            boxm(X.mesh(beam), (sx * xw - (0 if sx > 0 else 10), yy - 8, 0), (sx * xw + (10 if sx > 0 else 0), yy + 8, HG_H - 20))
    # ---- interior: arch trusses, purlins, hanging lamps
    for yy in np.arange(y0 + 96, y1 - 95, 192):
        path = [(x, yy, hg_roof(abs(x)) - t - 8) for x in np.linspace(-xw + t, xw - t, 25)]
        tube(X.mesh(beam), path, 7, nseg=6)
        path2 = [(x, yy, hg_roof(abs(x)) - t - 56) for x in np.linspace(-xw + t + 40, xw - t - 40, 25)]
        tube(X.mesh(beam), path2, 5, nseg=6)
        for x in np.linspace(-xw + t + 40, xw - t - 40, 13):
            tube(X.mesh(beam), [(x, yy, hg_roof(abs(x)) - t - 56), (x + 30, yy, hg_roof(abs(x + 30)) - t - 8)], 3, nseg=4, caps=(False, False))
        for x in (-520, 0, 520):
            zt = hg_roof(abs(x)) - t - 56
            tube(X.mesh(beam), [(x, yy, zt), (x, yy, zt - 70)], 2, nseg=4)
            revolve(X.mesh(beam), [(4, zt - 70), (40, zt - 92), (44, zt - 96)], n=12, cx=x, cy=yy)
            disc(X.mesh(lamp), 38, zt - 94, False, 12, x, yy)
    return _save('hangar', X)


# ================================================================================================= flying saucer
def saucer_profiles(scale=1.0, z0=0.0, belly=S_BELLY):
    """visual profiles (r, z) of the saucer, from the deck edge outward over the rim and back underneath"""
    k = scale
    top = lathe_profile([(S_DOME_R * k, z0 + (S_DECK + 2) * k), (S_DECK_R * k, z0 + (S_DECK + 2) * k), (380 * k, z0 + 380 * k),
                         (440 * k, z0 + 340 * k), (S_RIM * k, z0 + (S_RIM_TOP + 2) * k)], 6)
    rim = [(S_RIM * k, z0 + (S_RIM_TOP + 2) * k), ((S_RIM + 12) * k, z0 + (S_RIM_TOP - 6) * k), ((S_RIM + 14) * k, z0 + 288 * k),
           ((S_RIM + 12) * k, z0 + (S_RIM_BOT + 6) * k), (S_RIM * k, z0 + (S_RIM_BOT - 2) * k)]
    under = lathe_profile([(S_RIM * k, z0 + (S_RIM_BOT - 2) * k), (420 * k, z0 + 240 * k), (330 * k, z0 + 206 * k), (300 * k, z0 + (belly - 2) * k)], 6)
    return top, rim, under


def saucer_body(X, scale=1.0, z0=0.0, holes_top=(), holes_under=(), dome=True, kinds=('lm', 'glow'), legs=False, belly_r0=0.0, tag=''):
    k = scale
    hull = S('hull', kinds[0], tag=tag); dark = S('hull_dark', kinds[0], tag=tag)
    rimg = S('glyphs', kinds[1], tag=tag + 'r', light=0, wave='wave sin 0.8 0.2 0 0.5')
    bulb = S('glow_teal', kinds[1], tag=tag + 'b', light=0, wave='wave square 0.6 0.4 0 1.2')
    belly = S('glow_teal', kinds[1], tag=tag + 'u', light=0, wave='wave sin 0.75 0.25 0 0.3')
    domes = S('dome', 'lms' if kinds[0] == 'lm' else kinds[0], tag=tag, v=0.35)
    top, rim, under = saucer_profiles(scale, z0)
    revolve_grid(X.mesh(hull), top[::-1], 64, holes=holes_top, u_tiles=16, v_of=lambda r, z: r / (S_RIM * k) * 2, inward=False)
    revolve_grid(X.mesh(rimg), rim, 64, u_tiles=12, v_of=lambda r, z: (z - (z0 + S_RIM_BOT * k)) / (32 * k))
    revolve_grid(X.mesh(dark), under, 64, holes=holes_under, u_tiles=16, v_of=lambda r, z: r / (S_RIM * k) * 2)
    # flat belly (with a ring of light)
    r_in = belly_r0 * k
    zb = z0 + (S_BELLY - 2) * k
    revolve_grid(X.mesh(dark), [(300 * k, zb), (250 * k, zb), (220 * k, zb)], 64, holes=holes_under, u_tiles=16, inward=True)
    revolve_grid(X.mesh(belly), [(220 * k, zb - 1), (190 * k, zb - 1)], 64, holes=holes_under, u_tiles=8, inward=True)
    revolve_grid(X.mesh(dark), [(190 * k, zb), (max(r_in, 1.0), zb)], 64, holes=holes_under, u_tiles=8, inward=True)
    # rim bulbs
    for i in range(32):
        a = 2 * math.pi * (i + 0.5) / 32
        sphere(X.mesh(bulb), ((S_RIM + 14) * k * math.cos(a), (S_RIM + 14) * k * math.sin(a), z0 + 288 * k), 7 * k, nu=8, nv=5)
    # portholes on the upper hull
    port = S('glow_amber', kinds[1], tag=tag + 'p', light=0)
    for i in range(12):
        a = 2 * math.pi * (i + 0.25) / 12
        r = 410 * k; z = z0 + 0.0
        zz = np.interp(r, [p[0] for p in top], [p[1] for p in top])
        c = np.array([r * math.cos(a), r * math.sin(a), zz + 1.5 * k])
        n = np.array([math.cos(a) * 0.55, math.sin(a) * 0.55, 0.83]); n /= np.linalg.norm(n)
        ellipsoid(X.mesh(port), c, 16 * k, 16 * k, 4 * k, nu=10, nv=4, R=rot_z(a) @ rot_axis((0, 1, 0), -0.6))
    if dome:
        prof = [(S_DOME_R * k * math.cos(t), z0 + (S_DECK + 2) * k + 130 * k * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)]
        revolve(X.mesh(domes), prof, u_tiles=4, n=48, vlen=200 * k)
        revolve(X.mesh(hull), [(S_DOME_R * k + 10 * k, z0 + (S_DECK + 2) * k), (S_DOME_R * k + 6 * k, z0 + (S_DECK + 12) * k), (S_DOME_R * k - 2, z0 + (S_DECK + 12) * k)], u_tiles=8, n=48)
        sphere(X.mesh(bulb), (0, 0, z0 + (S_DECK + 2 + 130) * k + 6 * k), 10 * k, nu=8, nv=5)


def saucer():
    X = Model()
    dark = S('hull_dark', 'lm'); wallm = S('alien_wall', 'lm'); hull = S('hull', 'lm')
    a0, a1 = S_RAMP[0] * 22.5, (S_RAMP[1] + 1) * 22.5
    h0, h1 = S_HATCH[0] * 22.5, (S_HATCH[1] + 1) * 22.5
    saucer_body(X, holes_top=[(h0, h1, 0, 9999, S_HATCH_R[0] - 4, S_HATCH_R[1] + 16)],
                holes_under=[(a0, a1, 0, 9999, S_RAMP_R[0], S_RAMP_R[1] + 4)], belly_r0=0.0)
    # interior: cockpit wall (inward), ceiling (with the hatch hole), ramp-opening wall pieces
    rows = [(S_IN, S_FLOOR), (S_IN, S_DECK_BOT)]
    revolve_grid(X.mesh(wallm), rows, 64, holes=[(a0, a1, S_FLOOR, 300)], u_tiles=12, inward=True, v_of=lambda r, z: (S_DECK_BOT - z) / 152)
    revolve_grid(X.mesh(dark), [(S_IN, S_DECK_BOT), (S_HATCH_R[1], S_DECK_BOT), (S_HATCH_R[0], S_DECK_BOT), (0.5, S_DECK_BOT)], 64,
                 holes=[(h0, h1, 0, 9999, S_HATCH_R[0] - 1, S_HATCH_R[1] + 1)], u_tiles=8, inward=True)
    # hatch shaft lining + open lid
    for (ra, rb) in ((S_HATCH_R[0], S_HATCH_R[0]), (S_HATCH_R[1], S_HATCH_R[1])):
        pass
    for a in (h0, h1):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        n = np.array([-s, c, 0]) * (1 if a == h0 else -1)
        X.mesh(hull).quad((S_HATCH_R[0] * c, S_HATCH_R[0] * s, S_DECK_BOT), (S_HATCH_R[1] * c, S_HATCH_R[1] * s, S_DECK_BOT),
                          (S_HATCH_R[1] * c, S_HATCH_R[1] * s, S_DECK + 2), (S_HATCH_R[0] * c, S_HATCH_R[0] * s, S_DECK + 2), 64, n=n)
    for r_, sgn in ((S_HATCH_R[0], 1), (S_HATCH_R[1], -1)):
        revolve_grid(X.mesh(hull), [(r_, S_DECK_BOT), (r_, S_DECK + 2)] if sgn > 0 else [(r_, S_DECK + 2), (r_, S_DECK_BOT)], 64,
                     holes=[(0, h0, 0, 9999), (h1, 360, 0, 9999)], u_tiles=8)
    # ramp-opening jambs (vertical faces where the belly is cut) and the ramp
    for a in (a0, a1):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        n = np.array([-s, c, 0]) * (1 if a == a0 else -1)
        for (ra, rb) in ((S_RAMP_R[0], S_RAMP_R[1]),):
            X.mesh(dark).quad((ra * c, ra * s, S_BELLY), (rb * c, rb * s, S_BELLY), (rb * c, rb * s, S_FLOOR), (ra * c, ra * s, S_FLOOR), 64, n=n)
            X.mesh(dark).quad((S_IN * c, S_IN * s, S_FLOOR), (S_RAMP_R[1] * c, S_RAMP_R[1] * s, S_FLOOR), (S_RAMP_R[1] * c, S_RAMP_R[1] * s, 300), (S_IN * c, S_IN * s, 300), 64, n=n)
    revolve_grid(X.mesh(dark), [(S_RAMP_R[1], 300), (S_IN, 300)], 64, holes=[(0, a0, 0, 9999), (a1, 360, 0, 9999)], u_tiles=8, inward=True)
    revolve_grid(X.mesh(dark), [(S_RAMP_R[1], s_bot(S_RAMP_R[1])), (S_RAMP_R[1], 300)], 64, holes=[(0, a0, 0, 9999), (a1, 360, 0, 9999)], u_tiles=8, inward=True)
    rmp = S('plate', 'lm', tex=True)
    hw = 96
    L0, L1 = S_RAMP_R[0], S_RAMP_END
    pts = lambda r, x, dz=0: (x, -r, s_ramp_z(r) + dz)
    X.mesh(rmp).quad(pts(L0, -hw), pts(L0, hw), pts(L1, hw), pts(L1, -hw), 96, n=(0, -math.sin(math.atan(S_FLOOR / (L1 - L0))), math.cos(math.atan(S_FLOOR / (L1 - L0)))))
    for sx in (-1, 1):
        X.mesh(hull).quad(pts(L0, sx * hw), pts(L1, sx * hw), pts(L1, sx * hw, -10), pts(L0, sx * hw, -10), 64, n=(sx, 0, 0))
        tube(X.mesh(hull), [pts(L0 + 10, sx * (hw + 4), 40), pts(L1 - 30, sx * (hw + 4), 40)], 3, nseg=6)
        for r in np.linspace(L0 + 20, L1 - 40, 5): tube(X.mesh(hull), [pts(r, sx * (hw + 4), 0), pts(r, sx * (hw + 4), 40)], 2, nseg=5)
    # landing legs
    for a in S_LEGS:
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        top_ = np.array([330 * c, 330 * s, s_bot(330) + 4]); foot = np.array([430 * c, 430 * s, 26])
        tube(X.mesh(hull), [top_, foot], 18, nseg=10)
        tube(X.mesh(dark), [top_ + [0, 0, -30], (top_ + foot) / 2 + np.array([-40 * c, -40 * s, 0])], 8, nseg=8)
        revolve(X.mesh(dark), [(48, 0), (48, 10), (36, 20), (18, 30)], n=16, cx=foot[0], cy=foot[1])
        disc(X.mesh(dark), 48, 0.5, False, 16, foot[0], foot[1])
    # cockpit: console ring with glowing screens, two pilot seats (tiny)
    scr = S('glyphs', 'glow', tag='c', light=60, rgb='0.3 1 0.8', wave='wave sin 0.85 0.15 0 0.6')
    for k in range(16):
        if k in S_RAMP or k in S_HATCH or k in (2, 5): continue
        am = math.radians((k + 0.5) * 22.5)
        c, s = math.cos(am), math.sin(am)
        p0 = np.array([150 * c, 150 * s, S_FLOOR]); n = np.array([-c, -s, 0])
        R = rot_z(am)
        Mb = Mesh(); rbox(Mb, (-20, -26, 0), (20, 26, 44), r=6, tile=64); transform_mesh(Mb, R, p0 + n * -10)
        X.mesh(hull).add(Mb)
        Ms = Mesh(); Ms.quad((-21, -22, 30), (-21, 22, 30), (-12, 22, 46), (-12, -22, 46), 64); transform_mesh(Ms, R, p0 + n * -10)
        for v in range(len(Ms.ST)): Ms.ST[v] = ((Ms.ST[v][0] * 0.5) % 1, Ms.ST[v][1])
        X.mesh(scr).add(Ms)
    return _save('saucer', X)


def scout_mesh(X, scale, kinds=('dyn', 'dynglow'), tag='s'):
    saucer_body(X, scale=scale, z0=-S_BELLY * scale, kinds=kinds, tag=tag)


def saucer_crash():
    """the crashed scout, built in the crater's frame (origin = crater centre at ground level): lens tilted CS_TILT about
    x (north side up), scorched, rim torn on the low side; every vertex under the crater floor is clamped to it"""
    X = Model()
    hullc = S('hull_burnt', 'lm'); darkc = S('hull_dark', 'lm', tag='c')
    glyph = S('glyphs', 'glow', tag='x', light=40, rgb='0.3 1 0.8', wave='wave noise 0.6 0.4 0 3')
    k = CS_R / S_RIM
    zc = S_BELLY * k
    top, rim, under = saucer_profiles(k, -zc + CS_Z)
    rng = np.random.default_rng(5)
    dfm = lambda a, r, z: r - (18 * max(0, math.sin(a - 4.4)) ** 6 if r > 250 * k else 0) + 3 * math.sin(a * 13)
    revolve_grid(X.mesh(hullc), top[::-1], 48, u_tiles=12, v_of=lambda r, z: r / (S_RIM * k) * 2, deform=dfm)
    revolve_grid(X.mesh(glyph), rim, 48, u_tiles=10, v_of=lambda r, z: 0.5, deform=dfm)
    revolve_grid(X.mesh(darkc), under, 48, u_tiles=12, v_of=lambda r, z: r / (S_RIM * k) * 2, deform=dfm)
    prof = [(S_DOME_R * k * math.cos(t), -zc + CS_Z + (S_DECK + 2) * k + 130 * k * math.sin(t)) for t in np.linspace(0, math.pi / 2, 8)]
    revolve(X.mesh(S('dome', 'lms', tag='c', v=0.25)), prof, u_tiles=4, n=32, vlen=200 * k,
            rfun=lambda a, r, z: r * (0.85 if 0.5 < a < 1.6 else 1.0))
    # torn panels sticking up from the low (south) rim
    for i in range(5):
        a = math.radians(250 + i * 10)
        c, s = math.cos(a), math.sin(a)
        r0 = 300
        P0 = np.array([r0 * c, r0 * s, CS_Z - 4])
        Mm = Mesh(); Mm.quad((0, -18, 0), (0, 18, 0), (50 + 10 * i % 30, 14, 34), (50, -14, 30), 64)
        Mm.quad((0, -18, 0), (50, -14, 30), (50 + 10 * i % 30, 14, 34), (0, 18, 0), 64)
        transform_mesh(Mm, rot_z(a) @ rot_axis((0, 1, 0), -0.5), P0)
        X.mesh(hullc).add(Mm)
    # tilt + clamp at the crater floor
    R = rot_axis((1, 0, 0), math.radians(CS_TILT))
    floor = -CR_D + 0.5
    for sh, Mm in X.m.items():
        Mm.V = [R @ v for v in Mm.V]; Mm.N = [R @ n for n in Mm.N]
        Mm.V = [np.array([v[0], v[1], max(v[2], floor)]) for v in Mm.V]
        T = []
        for (a, b, c) in Mm.T:
            if Mm.V[a][2] <= floor + 0.01 and Mm.V[b][2] <= floor + 0.01 and Mm.V[c][2] <= floor + 0.01: continue
            T.append((a, b, c))
        Mm.T = T
    # scorched debris ring + dirt berm (thrown up by the impact) around the lens
    berm = S('dirt', 'lm')
    prof = [(CS_R + 8, floor), (CS_R + 40, floor + 26), (CS_R + 90, floor + 12), (CS_R + 130, floor)]
    revolve(X.mesh(berm), prof, u_tiles=12, n=48, rfun=lambda a, r, z: r + 10 * math.sin(a * 7), vlen=128)
    return _save('saucer_crash', X)


def crash_collision_points():
    """convex hull points of the crashed lens (world-relative to the crater centre), before clipping at the floor"""
    k = CS_R / S_RIM
    zc = S_BELLY * k
    pts = []
    R = rot_axis((1, 0, 0), math.radians(CS_TILT))
    for a in np.linspace(0, 2 * math.pi, 17)[:-1]:
        c, s = math.cos(a), math.sin(a)
        for (r, z) in ((S_RIM * k - 8, S_RIM_TOP * k - 6), (S_RIM * k - 8, S_RIM_BOT * k + 4), (S_DECK_R * k - 6, S_DECK * k - 4),
                       (300 * k - 6, S_BELLY * k + 4), (S_DOME_R * k * 0.7, (S_DECK + 2 + 90) * k)):
            pts.append(R @ np.array([r * c, r * s, z - zc + CS_Z]))
    pts.append(R @ np.array([0, 0, (S_DECK + 2 + 126) * k - zc + CS_Z]))
    return pts


# ================================================================================================= control tower
def tower():
    X = Model()
    conc = S('concrete', 'lm'); cin = S('concrete', 'lm', tag='i'); frm = S('frame', 'lm'); roofm = S('roofing', 'lm')
    glass = S('glass', 'glass'); scr = S('screen_radar', 'glow', light=40, rgb='0.4 1 0.6'); dark = S('paint_dark', 'lm')
    beacon = S('glow_red', 'glow', tag='b', light=0, wave='wave square 0.5 0.5 0 0.8')
    s, c = TW_SHAFT, TW_CAB
    t = 32
    d0, d1, dh = TW_DOOR
    dl0, dl1 = d0 - TW[1], d1 - TW[1]
    # shaft: 4 walls to the cab floor, door in the west wall, slit windows
    slits = [(-24, 24, 200, 330)]
    for (o, ud, n, holes) in (((-s, 0, 0), (0, 1, 0), (-1, 0, 0), [(dl0, dl1, 0, dh)]), ((s, 0, 0), (0, 1, 0), (1, 0, 0), slits),
                              ((0, -s, 0), (1, 0, 0), (0, -1, 0), slits), ((0, s, 0), (1, 0, 0), (0, 1, 0), slits)):
        wall(X.mesh(conc), o, ud, n, -s, s, 0, TW_FLOOR - 16, holes, tile=256, back=True, t=t)
    # cab: sill walls, corner posts + mullions, roof slab with overhang and a hatch hole, glass
    zs, zr = TW_SILL, TW_ROOF_BOT
    boxm(X.mesh(conc), (-c, -c, TW_FLOOR - 16), (c, c, TW_FLOOR - 0.5), tile=256, faces='b')
    for (o, ud, n) in (((-c, 0, 0), (0, 1, 0), (-1, 0, 0)), ((c, 0, 0), (0, 1, 0), (1, 0, 0)), ((0, -c, 0), (1, 0, 0), (0, -1, 0)), ((0, c, 0), (1, 0, 0), (0, 1, 0))):
        wall(X.mesh(conc), o, ud, n, -c, c, TW_FLOOR - 16, zs, (), tile=256)
        wall(X.mesh(cin), np.asarray(o) * (c - t) / c, ud, -np.asarray(n), -c + t, c - t, TW_FLOOR, zs, (), tile=256)
    for (a, b, cc, d) in ((-c, c, -c, -c + t), (-c, c, c - t, c), (-c, -c + t, -c + t, c - t), (c - t, c, -c + t, c - t)):
        X.mesh(conc).quad((a, cc, zs), (b, cc, zs), (b, d, zs), (a, d, zs), 128, n=(0, 0, 1))
    lean = 22
    for k in np.linspace(-c, c, 7):
        for (p0, p1) in ((( -c, k), (-c - lean, k * (c + lean) / c)), ((c, k), (c + lean, k * (c + lean) / c)),
                         ((k, -c), (k * (c + lean) / c, -c - lean)), ((k, c), (k * (c + lean) / c, c + lean))):
            tube(X.mesh(frm), [(p0[0], p0[1], zs), (p1[0], p1[1], zr)], 5, nseg=6)
    for (sx, sy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if sx:
            P = [(sx * c, -c, zs), (sx * c, c, zs), (sx * (c + lean), c + lean, zr), (sx * (c + lean), -c - lean, zr)]
        else:
            P = [(-c, sy * c, zs), (c, sy * c, zs), (c + lean, sy * (c + lean), zr), (-c - lean, sy * (c + lean), zr)]
        X.mesh(glass).poly(P, (sx * 0.97, sy * 0.97, 0.2), [(0, 0), (1, 0), (1, 1), (0, 1)])
    hx0, hx1, hy0, hy1 = (TW_HATCH[0] - TW[0], TW_HATCH[1] - TW[0], TW_HATCH[2] - TW[1], TW_HATCH[3] - TW[1])
    ro = c + lean + 24
    for (a, b, cc, d) in [(-ro, hx0, -ro, ro), (hx1, ro, -ro, ro), (hx0, hx1, -ro, hy0), (hx0, hx1, hy1, ro)]:
        boxm(X.mesh(roofm), (a, cc, zr), (b, d, TW_ROOF + 0.5), tile=128)
    boxm(X.mesh(frm), (-ro - 4, -ro - 4, TW_ROOF), (ro + 4, -ro + 8, TW_ROOF + 14))
    boxm(X.mesh(frm), (-ro - 4, ro - 8, TW_ROOF), (ro + 4, ro + 4, TW_ROOF + 14))
    boxm(X.mesh(frm), (-ro - 4, -ro, TW_ROOF), (-ro + 8, ro, TW_ROOF + 14))
    boxm(X.mesh(frm), (ro - 8, -ro, TW_ROOF), (ro + 4, ro, TW_ROOF + 14))
    # hatch lid + frame
    tube(X.mesh(frm), [(hx0, hy0, TW_ROOF + 4), (hx1, hy0, TW_ROOF + 4), (hx1, hy1, TW_ROOF + 4), (hx0, hy1, TW_ROOF + 4), (hx0, hy0, TW_ROOF + 4)], 4, nseg=5)
    X.mesh(dark).quad((hx0, hy1, TW_ROOF + 4), (hx1, hy1, TW_ROOF + 4), (hx1, hy1 + 6, TW_ROOF + 96), (hx0, hy1 + 6, TW_ROOF + 96), 64)
    # antenna mast + beacon on the roof (centre)
    lattice(X.mesh(frm), [(-14, -14, TW_ROOF), (14, -14, TW_ROOF), (14, 14, TW_ROOF), (-14, 14, TW_ROOF)],
            [(-6, -6, TW_ROOF + 330), (6, -6, TW_ROOF + 330), (6, 6, TW_ROOF + 330), (-6, 6, TW_ROOF + 330)], 2.5, 6)
    sphere(X.mesh(beacon), (0, 0, TW_ROOF + 344), 12, nu=10, nv=6)
    for z in (TW_ROOF + 160, TW_ROOF + 260):
        tube(X.mesh(frm), [(-60, 0, z), (60, 0, z)], 2.5, nseg=5)
    # interior: consoles along the south and east windows with radar screens, two chairs
    for (x0, y0, x1, y1, nrm) in ((-c + 40, -c + 34, c - 40, -c + 90, (0, 1, 0)), (c - 90, -c + 120, c - 34, c - 120, (-1, 0, 0))):
        boxm(X.mesh(dark), (x0, y0, TW_FLOOR), (x1, y1, TW_FLOOR + 56), tile=64)
        n = np.array(nrm, float)
        if nrm[1]:
            for xx in np.arange(x0 + 20, x1 - 80, 110):
                X.mesh(scr).quad((xx, y0 + 30, TW_FLOOR + 57), (xx + 80, y0 + 30, TW_FLOOR + 57), (xx + 80, y0 + 6, TW_FLOOR + 80), (xx, y0 + 6, TW_FLOOR + 80), 80)
        else:
            for yy in np.arange(y0 + 20, y1 - 80, 110):
                X.mesh(scr).quad((x1 - 30, yy, TW_FLOOR + 57), (x1 - 30, yy + 80, TW_FLOOR + 57), (x1 - 6, yy + 80, TW_FLOOR + 80), (x1 - 6, yy, TW_FLOOR + 80), 80)
    # door frame + sign plate
    boxm(X.mesh(frm), (-s - 8, dl0 - 10, 0), (-s + 2, dl0, dh + 10)); boxm(X.mesh(frm), (-s - 8, dl1, 0), (-s + 2, dl1 + 10, dh + 10))
    boxm(X.mesh(frm), (-s - 8, dl0 - 10, dh), (-s + 2, dl1 + 10, dh + 10))
    return _save('tower', X)


# ================================================================================================= water tower
def watertower():
    X = Model()
    tank = S('tank', 'lm'); frm = S('frame', 'lm', tag='w'); grate = S('grate', 'alpha', tex=True)
    L = WT_LEG
    for (sx, sy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        tube(X.mesh(frm), [(sx * (L + 40), sy * (L + 40), 0), (sx * L * 0.82, sy * L * 0.82, WT_Z0 - 16)], 12, nseg=8)
        revolve(X.mesh(frm), [(30, 0), (30, 16), (16, 24)], n=10, cx=sx * (L + 40), cy=sy * (L + 40))
    corners = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    for lvl in (0.33, 0.66):
        z = (WT_Z0 - 16) * lvl
        pts = [(sx * (L + 40 - (L * 0.18 + 40) * lvl), sy * (L + 40 - (L * 0.18 + 40) * lvl), z) for (sx, sy) in corners]
        tube(X.mesh(frm), pts + [pts[0]], 5, nseg=6)
    for i in range(4):
        (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
        for (za, zb) in ((0.0, 0.33), (0.33, 0.66), (0.66, 1.0)):
            pa = lambda sx, sy, f: (sx * (L + 40 - (L * 0.18 + 40) * f), sy * (L + 40 - (L * 0.18 + 40) * f), (WT_Z0 - 16) * f)
            tube(X.mesh(frm), [pa(ax, ay, za), pa(bx, by, zb)], 3, nseg=5, caps=(False, False))
            tube(X.mesh(frm), [pa(bx, by, za), pa(ax, ay, zb)], 3, nseg=5, caps=(False, False))
    R = WT_TANK_R
    revolve_grid(X.mesh(tank), [(R + 2, WT_Z0), (R + 2, WT_Z1)], 48, u_tiles=6, v_of=lambda r, z: (WT_Z1 - z) / (WT_Z1 - WT_Z0) * 0.999)
    revolve(X.mesh(tank), [(0, WT_Z0 - 40), (R * 0.7, WT_Z0 - 24), (R + 2, WT_Z0)], u_tiles=6, n=48, vlen=600)
    roofm = S('roofing', 'lm', tag='w')
    revolve(X.mesh(roofm), [(R + 18, WT_Z1 - 2), (R + 14, WT_Z1 + 6), (0, WT_CONE + 4)], u_tiles=8, n=48, vlen=128)
    sphere(X.mesh(frm), (0, 0, WT_CONE + 10), 14, nu=10, nv=6)
    # catwalk ring (grating) + railing
    Mg = X.mesh(grate)
    revolve_grid(Mg, [(WT_RING, WT_Z0 - 2), (R + 2, WT_Z0 - 2)], 48, u_tiles=24, inward=False)
    revolve_grid(Mg, [(R + 2, WT_Z0 - 4), (WT_RING, WT_Z0 - 4)], 48, u_tiles=24, inward=False)
    ring = [(WT_RING * math.cos(a), WT_RING * math.sin(a), WT_Z0 + 40) for a in np.linspace(0, 2 * math.pi, 49)]
    tube(X.mesh(frm), ring, 3, nseg=5)
    for a in np.linspace(0, 2 * math.pi, 25)[:-1]:
        tube(X.mesh(frm), [(WT_RING * math.cos(a), WT_RING * math.sin(a), WT_Z0 - 2), (WT_RING * math.cos(a), WT_RING * math.sin(a), WT_Z0 + 40)], 2, nseg=4)
    # ladder up one leg (visual: bots and players use the pad)
    for sgn in (-1, 1):
        tube(X.mesh(frm), [(L + 70, sgn * 14, 0), (L + 70, sgn * 14, WT_Z0)], 2.5, nseg=5)
    for z in np.arange(24, WT_Z0, 32):
        tube(X.mesh(frm), [(L + 70, -14, z), (L + 70, 14, z)], 2, nseg=4)
    for z in np.arange(WT_Z0 + 8, WT_Z1, 32):
        tube(X.mesh(frm), [(R + 10, -14, z), (R + 10, 14, z)], 2, nseg=4)
    # painted "51"
    num = S('num51', 'alpha')
    q = X.mesh(num)
    a = math.radians(200)
    for (aa, bb) in ((a - 0.32, a + 0.32),):
        P = []
        n = 6
        for i in range(n + 1):
            t = aa + (bb - aa) * i / n
            P.append(((R + 3) * math.cos(t), (R + 3) * math.sin(t)))
        for i in range(n):
            (xa, ya), (xb, yb) = P[i], P[i + 1]
            o = len(q.V)
            for (px, py, z, u, v) in ((xa, ya, WT_Z0 + 30, i / n, 1), (xb, yb, WT_Z0 + 30, (i + 1) / n, 1), (xb, yb, WT_Z0 + 170, (i + 1) / n, 0), (xa, ya, WT_Z0 + 170, i / n, 0)):
                q.add_v((px, py, z), (px, py, 0), (u, v))
            q.tri(o, o + 1, o + 2); q.tri(o, o + 2, o + 3)
    return _save('watertower', X)


# ================================================================================================= radar
def radar_base():
    X = Model()
    paint = S('paint_white', 'lm'); frm = S('frame', 'lm', tag='r'); dark = S('paint_dark', 'lm', tag='r')
    z0 = RD_PLAT[4]
    revolve(X.mesh(paint), [(RD_PED_R + 30, z0), (RD_PED_R + 30, z0 + 40), (RD_PED_R + 4, z0 + 50), (RD_PED_R, RD_PED_Z - 20),
                            (RD_PED_R + 10, RD_PED_Z - 10), (RD_PED_R + 10, RD_PED_Z), (20, RD_PED_Z + 2)], u_tiles=4, n=24, vlen=128)
    boxm(X.mesh(dark), (RD_PED_R + 30, -40, z0), (RD_PED_R + 110, 40, z0 + 80))
    # railing round the platform edge (visual; 36 tall, it never blocks a shot)
    x0, x1, y0, y1 = (RD_PLAT[0] - RD[0], RD_PLAT[1] - RD[0], RD_PLAT[2] - RD[1], RD_PLAT[3] - RD[1])
    stairs_x = (-1984 - RD[0], -1824 - RD[0])
    for (pa, pb) in (((x0 + 8, y1 - 8), (x1 - 8, y1 - 8)), ((x0 + 8, y0 + 8), (x0 + 8, y1 - 8)), ((x1 - 8, y0 + 8), (x1 - 8, y1 - 8)),
                     ((x0 + 8, y0 + 8), (stairs_x[0], y0 + 8)), ((stairs_x[1], y0 + 8), (x1 - 8, y0 + 8))):
        tube(X.mesh(frm), [(pa[0], pa[1], z0 + 36), (pb[0], pb[1], z0 + 36)], 3, nseg=5)
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
        for f in np.linspace(0, 1, max(2, int(L / 96)) + 1):
            p = (pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f)
            tube(X.mesh(frm), [(p[0], p[1], z0), (p[0], p[1], z0 + 36)], 2.5, nseg=4)
    return _save('radar_base', X)


def radar_dish():
    """rotating dish (model2 on a func_rotating, origin at the pedestal top RD_DISH_Z): lightingDiffuse shaders"""
    X = Model()
    dish = S('dish', 'dyn'); frm = S('frame', 'dyn', tag='d')
    R = 224
    # paraboloid facing +x, tilted up 20 deg
    Mm = X.mesh(dish)
    nu, nv = 28, 8
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        rr = R * i / nv
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            y, z = rr * math.cos(t), rr * math.sin(t) * 0.75
            x = -(rr * rr) / (4 * 180)
            P[i, j] = (x, y, z); UV[i, j] = (0.5 + 0.5 * math.cos(t) * i / nv, 0.5 + 0.5 * math.sin(t) * i / nv)
    Rt = rot_axis((0, 1, 0), math.radians(-20))
    P = P @ Rt.T + np.array([30, 0, 0])
    N = grid_normals(P)
    Mm.grid(P, N, UV)
    Mm.grid(P[:, ::-1] - N[:, ::-1] * 3, -N[:, ::-1], UV[:, ::-1])
    feed = Rt @ np.array([180, 0, 0]) + np.array([30, 0, 0])
    for t in (0, 2.1, 4.2):
        rim = Rt @ np.array([-(R * R) / 720, R * math.cos(t) * 0.95, R * math.sin(t) * 0.7]) + np.array([30, 0, 0])
        tube(X.mesh(frm), [rim, feed], 3, nseg=5)
    sphere(X.mesh(frm), feed, 12, nu=8, nv=5)
    tube(X.mesh(frm), [(-40, 0, -80), (10, 0, 0)], 22, nseg=8)
    revolve(X.mesh(frm), [(50, -80), (50, -70), (30, -60), (24, -50)], n=16)
    return _save('radar_dish', X)


# ================================================================================================= quonset hut
def quonset():
    X = Model()
    corr = S('corr', 'lm', tag='q'); inner = S('corr_in', 'lm', tag='q'); ply = S('plywood', 'lm'); frm = S('frame', 'lm', tag='q')
    lampg = S('glow_amber', 'glow', tag='q', light=0)
    R, L, t = HUT_R, HUT_L, HUT_T
    n = 24
    angs = np.linspace(0, math.pi, n + 1)
    for (msh, rr, sgn) in ((corr, R, 1), (inner, R - t, -1)):
        Mm = X.mesh(msh)
        P = np.zeros((2, n + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, n + 1, 2))
        for j, a in enumerate(angs):
            for i, y in enumerate((-L + (0 if msh == corr else t), L - (0 if msh == corr else t))):
                P[i, j] = (rr * math.cos(a), y, rr * math.sin(a)); N[i, j] = (sgn * math.cos(a), 0, sgn * math.sin(a))
                UV[i, j] = (a * rr / 96, y / 192)
        Mm.grid(P, N, UV)
    # end walls with a door and two windows
    for sy in (-1, 1):
        pts = [(R * math.cos(a), sy * L, R * math.sin(a)) for a in angs]
        holes_u = [(-64, 64, 0, 160), (-170, -100, 80, 140), (100, 170, 80, 140)]
        import wopmap
        for (yy, nrm, rr) in ((sy * L, sy, R), (sy * (L - t), -sy, R - t)):
            # split the half-disc into vertical strips around the holes
            xs = sorted({float(v) for v in np.linspace(-rr, rr, 33)} | {-170.0, -100.0, -64.0, 64.0, 100.0, 170.0})
            for xa, xb in zip(xs, xs[1:]):
                za_top = math.sqrt(max(0, rr * rr - xa * xa)); zb_top = math.sqrt(max(0, rr * rr - xb * xb))
                segs = [(0, 1e9)]
                for (ha, hb, hz0, hz1) in holes_u:
                    if ha <= xa and xb <= hb:
                        segs = [(lo, hi) for (lo, hi) in [(0, hz0), (hz1, 1e9)] if hi > lo]
                for (lo, hi) in segs:
                    if lo >= min(za_top, zb_top) - 1: continue
                    P = [(xa, yy, lo), (xb, yy, lo), (xb, yy, min(hi, zb_top)), (xa, yy, min(hi, za_top))]
                    X.mesh(ply).poly(P, (0, nrm, 0), [(p[0] / 128, -p[2] / 128) for p in P])
        for (ha, hb, hz0, hz1) in holes_u:
            for (xx, nx) in ((ha, 1), (hb, -1)):
                X.mesh(frm).quad((xx, sy * L, hz0), (xx, sy * L, hz1), (xx, sy * (L - t), hz1), (xx, sy * (L - t), hz0), 64, n=(nx, 0, 0))
            X.mesh(frm).quad((ha, sy * L, hz1), (hb, sy * L, hz1), (hb, sy * (L - t), hz1), (ha, sy * (L - t), hz1), 64, n=(0, 0, -1))
            if hz0 > 0: X.mesh(frm).quad((ha, sy * L, hz0), (hb, sy * L, hz0), (hb, sy * (L - t), hz0), (ha, sy * (L - t), hz0), 64, n=(0, 0, 1))
        tube(X.mesh(frm), pts, 6, nseg=6)
        boxm(X.mesh(frm), (-96, sy * L + (0 if sy > 0 else -40), 176), (96, sy * L + (40 if sy > 0 else 0), 184))
        sphere(X.mesh(lampg), (0, sy * (L + 14), 196), 9, nu=8, nv=5)
    # ribs every 128 on the outside
    for y in np.arange(-L + 64, L, 128):
        tube(X.mesh(frm), [(R * math.cos(a) * 1.01, y, R * math.sin(a) * 1.01) for a in angs], 4, nseg=5)
    return _save('quonset', X)


# ================================================================================================= black triangle
def jet():
    X = Model()
    sk = S('stealth', 'lm'); gl = S('glass_dark', 'lms', v=0.35); eng = S('glow_amber', 'glow', tag='j', light=80, rgb='1 0.6 0.3', wave='wave sin 0.8 0.2 0 0.4')
    ring = S('glow_red', 'glow', tag='j', light=0, wave='wave sin 0.6 0.4 0 0.25'); gear = S('paint_dark', 'lm', tag='j')
    A = np.array([JET_APEX_X, 0, JET_APEX + 2.0])
    corners = [np.array([JET_NOSE - 6, 0, JET_EDGE]), np.array([JET_TAIL + 4, -JET_SPAN - 6, JET_EDGE]), np.array([JET_TAIL + 4, JET_SPAN + 6, JET_EDGE])]
    # top: three faceted panels from the apex to the edges (split for a gentle ridge)
    for i in range(3):
        a, b = corners[i], corners[(i + 1) % 3]
        mid = (a + b) / 2; mid[2] += 10
        for (p, q) in ((a, mid), (mid, b)):
            n = np.cross(q - p, A - p); n /= np.linalg.norm(n)
            X.mesh(sk).poly([p, q, A], n, [(p[0] / 256, p[1] / 256), (q[0] / 256, q[1] / 256), (A[0] / 256, A[1] / 256)])
    # edge band down to the belly + flat belly
    bel = [c * np.array([0.97, 0.97, 0]) + np.array([0, 0, JET_BELLY]) for c in corners]
    for i in range(3):
        a, b = corners[i], corners[(i + 1) % 3]; c, d = bel[(i + 1) % 3], bel[i]
        n = np.cross(b - a, d - a); n = -n / np.linalg.norm(n)
        mid = (a + b + c + d) / 4
        cen = (corners[0] + corners[1] + corners[2]) / 3
        if np.dot(n[:2], (mid - cen)[:2]) < 0: n = -n
        X.mesh(sk).poly([a, b, c, d], n, [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
    X.mesh(sk).poly(bel[::-1], (0, 0, -1), [(p[0] / 256, p[1] / 256) for p in bel[::-1]])
    # cockpit canopy near the nose
    ellipsoid(X.mesh(gl), (JET_NOSE + 200, 0, 0.5 * (JET_EDGE + JET_APEX) + 22), 90, 44, 26, nu=16, nv=8,
              R=rot_axis((0, 1, 0), math.radians(10)))
    # engine pods under the three corners + centre ring
    for c in bel:
        p = c * np.array([0.72, 0.72, 0]) + np.array([JET_APEX_X * 0.28, 0, JET_BELLY - 1])
        disc(X.mesh(eng), 46, p[2], False, 20, p[0], p[1])
        revolve(X.mesh(gear), [(52, p[2] + 0.5), (54, p[2] - 6), (46, p[2] - 8)], n=20, cx=p[0], cy=p[1])
    revolve_grid(X.mesh(ring), [(130, JET_BELLY - 1.5), (110, JET_BELLY - 1.5)], 32, inward=True)
    # landing gear: struts + wheels
    for (gx, gy) in ((JET_NOSE + 170, 0), (JET_TAIL - 110, -200), (JET_TAIL - 110, 200)):
        tube(X.mesh(gear), [(gx, gy, JET_BELLY), (gx, gy, 22)], 7, nseg=8)
        for sgn in (-1, 1):
            tube(X.mesh(gear), [(gx, gy + sgn * 8, 20), (gx, gy + sgn * 26, 20)], 20, nseg=12)
    # nav lights at the wing tips
    sphere(X.mesh(S('glow_red', 'glow', tag='jn', light=0)), corners[1] + [0, 0, 4], 6, nu=8, nv=5)
    sphere(X.mesh(S('glow_green', 'glow', tag='jn', light=0)), corners[2] + [0, 0, 4], 6, nu=8, nv=5)
    return _save('jet', X)


def jet_collision_points():
    pts = [(JET_APEX_X - 8, 0, JET_APEX - 4)]
    for (x, y) in ((JET_NOSE + 10, 0), (JET_TAIL - 4, -JET_SPAN + 8), (JET_TAIL - 4, JET_SPAN - 8)):
        pts += [(x, y, JET_EDGE - 4), (x * 0.97, y * 0.97, JET_BELLY + 4)]
    return pts


def airstairs():
    """mobile boarding stairs: 8 steps of 16 rising toward -x, top platform at 128 (origin at the stair foot centre,
    stairs occupy x -256..0, platform x -320..-256)"""
    X = Model()
    wh = S('paint_white', 'lm', tag='a'); dk = S('paint_dark', 'lm', tag='a'); st = S('plate', 'lm', tex=True, tag='a')
    for i in range(8):
        x1 = -32 * i; x0 = x1 - 32; z = 16 * (i + 1)
        boxm(X.mesh(st), (x0, -64, z - 4), (x1, 64, z), tile=64)
    boxm(X.mesh(st), (-320, -64, 124), (-256, 64, 128), tile=64)
    for sy in (-1, 1):
        X.mesh(wh).poly([(0, sy * 66, 0), (-256, sy * 66, 128), (-256, sy * 66, 96), (-30, sy * 66, 0)], (0, sy, 0),
                        [(0, 0), (2, 1), (2, 0.8), (0.2, 0)])
        tube(X.mesh(dk), [(-10, sy * 66, 46), (-256, sy * 66, 166), (-320, sy * 66, 166)], 3, nseg=6)
        tube(X.mesh(dk), [(-320, sy * 66, 128), (-320, sy * 66, 166)], 3, nseg=5)
        for x in (-80, -160, -240): tube(X.mesh(dk), [(x, sy * 66, 16 * (-x / 32) + 4), (x, sy * 66, 16 * (-x / 32) + 44)], 2, nseg=4)
    # truck chassis under the platform
    boxm(X.mesh(wh), (-330, -70, 20), (-150, 70, 96), tile=64)
    for (x, y) in ((-310, -72), (-310, 72), (-170, -72), (-170, 72)):
        tube(X.mesh(dk), [(x, y - 10, 20), (x, y + 10, 20)], 20, nseg=12)
    return _save('airstairs', X)


# ================================================================================================= S-4 bunker
def bunker():
    X = Model()
    conc = S('concrete', 'lm', tag='b'); cin = S('concrete', 'lm', tag='bi'); frm = S('frame', 'lm', tag='b')
    sten = S('stencil_s4', 'lm'); dark = S('paint_dark', 'lm', tag='b'); lamp = S('glow_amber', 'glow', tag='bk', light=0)
    x0, x1, y0, y1 = BK
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    t = 32
    d0, d1, dh = BK_DOOR
    hole = [(d0 - cy, d1 - cy, 0, dh)]
    for (o, ud, n, holes) in (((hx, 0, 0), (0, 1, 0), (1, 0, 0), hole), ((-hx, 0, 0), (0, 1, 0), (-1, 0, 0), []),
                              ((0, hy, 0), (1, 0, 0), (0, 1, 0), []), ((0, -hy, 0), (1, 0, 0), (0, -1, 0), [])):
        wall(X.mesh(conc), o, ud, n, -(hy if ud[1] else hx), (hy if ud[1] else hx), 0, BK_H - 16, holes, tile=256, back=True, t=t)
    # chamfered roof slab
    ch = 20
    pts_top = [(-hx + ch, -hy + ch), (hx - ch, -hy + ch), (hx - ch, hy - ch), (-hx + ch, hy - ch)]
    X.mesh(conc).poly([(x, y, BK_H) for (x, y) in pts_top], (0, 0, 1), [(x / 256, y / 256) for (x, y) in pts_top])
    edges = [((-hx, -hy), (hx, -hy)), ((hx, -hy), (hx, hy)), ((hx, hy), (-hx, hy)), ((-hx, hy), (-hx, -hy))]
    for i, ((ax, ay), (bx, by)) in enumerate(edges):
        (cx2, cy2), (dx2, dy2) = pts_top[(i + 1) % 4], pts_top[i]
        P = [(ax, ay, BK_H - 16), (bx, by, BK_H - 16), (cx2, cy2, BK_H), (dx2, dy2, BK_H)]
        nn = np.cross(np.subtract(P[1], P[0]), np.subtract(P[3], P[0])); nn = nn / np.linalg.norm(nn)
        X.mesh(conc).poly(P, nn, [(0, 0), (4, 0), (4, 0.1), (0, 0.1)])
    X.mesh(cin).poly([(-hx + t, -hy + t, BK_H - 16), (hx - t, -hy + t, BK_H - 16), (hx - t, hy - t, BK_H - 16), (-hx + t, hy - t, BK_H - 16)][::-1],
                     (0, 0, -1), [(0, 0), (2, 0), (2, 2), (0, 2)])
    # blast door (open, swung against the wall) + frame, stencil, lamp, vents
    boxm(X.mesh(frm), (hx - 2, d0 - cy - 20, 0), (hx + 14, d0 - cy, dh + 20)); boxm(X.mesh(frm), (hx - 2, d1 - cy, 0), (hx + 14, d1 - cy + 20, dh + 20))
    boxm(X.mesh(frm), (hx - 2, d0 - cy - 20, dh), (hx + 14, d1 - cy + 20, dh + 20))
    boxm(X.mesh(dark), (hx + 14, d1 - cy + 24, 0), (hx + 30, d1 - cy + 24 + 128, dh - 4), tile=64)
    q = X.mesh(sten)
    q.quad((hx + 1, d1 - cy + 170, 60), (hx + 1, hy - 20, 60), (hx + 1, hy - 20, 160), (hx + 1, d1 - cy + 170, 160), 128, n=(1, 0, 0))
    for v, st_ in zip(range(len(q.V) - 4, len(q.V)), ((0, 1), (1, 1), (1, 0), (0, 0))): q.ST[v] = st_
    sphere(X.mesh(lamp), (hx + 12, (d0 + d1) / 2 - cy, dh + 40), 10, nu=8, nv=5)
    for (vx, vy) in ((-hx + 90, -hy + 90), (-hx + 90, hy - 90)):
        revolve(X.mesh(frm), [(30, BK_H), (30, BK_H + 40), (44, BK_H + 46), (44, BK_H + 56), (0, BK_H + 62)], n=12, cx=vx, cy=vy)
    return _save('bunker', X)


def booth():
    X = Model()
    wh = S('paint_white', 'lm', tag='g'); frm = S('frame', 'lm', tag='g'); gl = S('glass', 'glass', tag='g'); rf = S('roofing', 'lm', tag='g')
    h = 96
    for (o, ud, n, holes) in (((h, 0, 0), (0, 1, 0), (1, 0, 0), [(-64, 64, 80, 150)]), ((-h, 0, 0), (0, 1, 0), (-1, 0, 0), [(-64, 64, 80, 150)]),
                              ((0, h, 0), (1, 0, 0), (0, 1, 0), [(-40, 40, 0, 150)]), ((0, -h, 0), (1, 0, 0), (0, -1, 0), [(-64, 64, 80, 150)])):
        wall(X.mesh(wh), o, ud, n, -h, h, 0, 176, holes, tile=128, back=True, t=12)
    boxm(X.mesh(rf), (-h - 24, -h - 24, 176), (h + 24, h + 24, 192), tile=128)
    for (o, ud, n) in (((h - 6, 0, 0), (0, 1, 0), (1, 0, 0)), ((-h + 6, 0, 0), (0, 1, 0), (-1, 0, 0)), ((0, -h + 6, 0), (1, 0, 0), (0, -1, 0))):
        o = np.array(o, float); ud = np.array(ud, float)
        X.mesh(gl).poly([o + ud * -64 + [0, 0, 80], o + ud * 64 + [0, 0, 80], o + ud * 64 + [0, 0, 150], o + ud * -64 + [0, 0, 150]], n,
                        [(0, 0), (1, 0), (1, 1), (0, 1)])
    return _save('booth', X)


def boom():
    """boom barrier: post + red/white arm along +x (length 480), origin at the post foot"""
    X = Model()
    post = S('paint_dark', 'lm', tag='bm'); arm = S('barrier_arm', 'lm')
    boxm(X.mesh(post), (-24, -24, 0), (24, 24, 96), tile=64)
    Mm = Mesh(); rbox(Mm, (0, -6, 84), (480, 6, 96), r=3, tile=96)
    for i in range(len(Mm.ST)): Mm.ST[i] = (Mm.V[i][0] / 96, 0.5)
    X.mesh(arm).add(Mm)
    boxm(X.mesh(post), (470, -10, 0), (490, 10, 84), tile=64)
    return _save('boom', X)


# ================================================================================================= floodlight mast
def floodlight():
    X = Model()
    frm = S('frame', 'lm', tag='f'); lamp = S('glow_white', 'glow', tag='f', light=0); dark = S('paint_dark', 'lm', tag='f')
    b = 40; tp = 14
    lattice(X.mesh(frm), [(-b, -b, 0), (b, -b, 0), (b, b, 0), (-b, b, 0)], [(-tp, -tp, FL_H), (tp, -tp, FL_H), (tp, tp, FL_H), (-tp, tp, FL_H)], 4, 10)
    boxm(X.mesh(dark), (-70, -70, FL_H), (70, 70, FL_H + 8), tile=64)
    for (x, y) in ((-48, 0), (48, 0)):
        for z in (FL_H + 30, FL_H + 90):
            boxm(X.mesh(dark), (x - 26, y - 20, z), (x + 26, y + 20, z + 46), tile=64)
            X.mesh(lamp).quad((x - 22, y - 21, z + 4), (x + 22, y - 21, z + 4), (x + 22, y - 21, z + 42), (x - 22, y - 21, z + 42), 64, n=(0, -1, 0))
            X.mesh(lamp).quad((x + 22, y + 21, z + 4), (x - 22, y + 21, z + 4), (x - 22, y + 21, z + 42), (x + 22, y + 21, z + 42), 64, n=(0, 1, 0))
    boxm(X.mesh(dark), (-80, -80, 0), (80, 80, 24), tile=64)
    return _save('floodlight', X)


def beam_iqm(name, length, r0, r1, color_tag):
    """additive light cone along +x (searchlight) from r0 at the lamp to r1 at `length`"""
    X = Model()
    bm = S('beam', 'beam', tag=color_tag)
    Mm = X.mesh(bm)
    n = 16
    for j in range(n):
        a0, a1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
        o = len(Mm.V)
        for (a, x, r, v) in ((a0, 0, r0, 0), (a1, 0, r0, 0), (a1, length, r1, 1), (a0, length, r1, 1)):
            Mm.add_v((x, r * math.cos(a), r * math.sin(a)), (0, math.cos(a), math.sin(a)), (0.5, v))
        Mm.tri(o, o + 1, o + 2); Mm.tri(o, o + 2, o + 3)
    return Mm, X


# ================================================================================================= props (vertex lit)
def drum(name, col, label=True):
    X = Model()
    img = f'drum_{name}'
    m = S(img, 'vl')
    revolve(X.mesh(m), [(22, 0), (22, 60)], u_tiles=1, n=16, vlen=60)
    for z in (20, 40): revolve(X.mesh(m), [(22.5, z - 2), (23.5, z), (22.5, z + 2)], n=16, u_tiles=1, vlen=200)
    disc(X.mesh(S('paint_dark', 'vl', tag='dr')), 21, 59.5, True, 16)
    revolve(X.mesh(m), [(22, 60), (20, 61), (20, 58)], n=16, u_tiles=1, vlen=200)
    return _save('drum_' + name, X)


def crate(name, s, text='TOP SECRET'):
    X = Model()
    m = S('crate', 'vl', tag='')
    Mm = Mesh(); rbox(Mm, (-s / 2, -s / 2, 0), (s / 2, s / 2, s), r=2, tile=s)
    # per-face UVs: map each face's own square to the full texture
    for i, (v, n) in enumerate(zip(Mm.V, Mm.N)):
        ax = int(np.argmax(np.abs(n)))
        if ax == 2: Mm.ST[i] = ((v[0] + s / 2) / s, (v[1] + s / 2) / s)
        elif ax == 0: Mm.ST[i] = ((v[1] + s / 2) / s * (1 if n[0] > 0 else -1), 1 - v[2] / s)
        else: Mm.ST[i] = ((v[0] + s / 2) / s * (-1 if n[1] > 0 else 1), 1 - v[2] / s)
    X.mesh(m).add(Mm)
    return _save(name, X)


def barrier():
    X = Model()
    m = S('barrier', 'vl')
    prof = [(-30, 0), (-30, 8), (-10, 20), (-8, 52), (8, 52), (10, 20), (30, 8), (30, 0)]
    Mm = X.mesh(m)
    for i in range(len(prof) - 1):
        (ya, za), (yb, zb) = prof[i], prof[i + 1]
        n = np.array([0, zb - za, -(yb - ya)]); n = -n / np.linalg.norm(n)
        Mm.quad((-80, ya, za), (80, ya, za), (80, yb, zb), (-80, yb, zb), 96, n=n)
        for v in range(len(Mm.V) - 4, len(Mm.V)): Mm.ST[v] = ((Mm.V[v][0] + 80) / 160, 1 - Mm.V[v][2] / 60)
    for sx in (-1, 1):
        Mm.poly([(sx * 80, y, z) for (y, z) in (prof if sx > 0 else prof[::-1])], (sx, 0, 0), [(0.5 + y / 64, 1 - z / 64) for (y, z) in (prof if sx > 0 else prof[::-1])])
    return _save('barrier', X)


def sandbags():
    X = Model()
    m = S('sandbag', 'vl')
    for row in range(3):
        for i in range(5):
            x = -128 + i * 64 + (32 if row % 2 else 0)
            if x > 128: continue
            ellipsoid(X.mesh(m), (x, 0, 10 + row * 18), 34, 22, 11, nu=10, nv=6, flat_bottom=-10 if row == 0 else None)
    return _save('sandbags', X)


def humvee():
    X = Model()
    camo = S('camo', 'vl'); dk = S('paint_dark', 'vl', tag='h'); gl = S('glass_dark', 'vl', tag='h')
    rbox(X.mesh(camo), (-150, -70, 30), (150, 70, 80), r=8, tile=128)
    rbox(X.mesh(camo), (-60, -64, 80), (90, 64, 126), r=6, tile=128)
    rbox(X.mesh(camo), (90, -66, 80), (150, 66, 92), r=4, tile=128)
    for (x, y) in ((-100, -72), (-100, 72), (100, -72), (100, 72)):
        tube(X.mesh(dk), [(x, y - 14, 26), (x, y + 14, 26)], 26, nseg=12)
    X.mesh(gl).quad((90, -58, 92), (90, 58, 92), (84, 56, 122), (84, -56, 122), 64, n=(1, 0, 0.2))
    for sy in (-1, 1):
        X.mesh(gl).quad((-50, sy * 64.5, 92), (80, sy * 64.5, 92), (80, sy * 64.5, 120), (-50, sy * 64.5, 120), 64, n=(0, sy, 0))
    return _save('humvee', X)


def forklift():
    X = Model()
    y = S('paint_yellow', 'vl'); dk = S('paint_dark', 'vl', tag='fk')
    rbox(X.mesh(y), (-80, -48, 20), (60, 48, 70), r=6, tile=64)
    for (x0, x1) in ((-70, -60), (40, 50)):
        for sy in (-1, 1): tube(X.mesh(dk), [(x0 + 5, sy * 40, 70), (x0 + 5, sy * 40, 150)], 4, nseg=6)
    boxm(X.mesh(dk), (-75, -46, 148), (50, 46, 154))
    boxm(X.mesh(dk), (60, -44, 4), (70, 44, 180))
    for sy in (-1, 1): boxm(X.mesh(dk), (70, sy * 30 - 6, 10), (150, sy * 30 + 6, 16))
    for (x, yy) in ((-50, -50), (-50, 50), (30, -50), (30, 50)):
        tube(X.mesh(dk), [(x, yy - 10, 20), (x, yy + 10, 20)], 20, nseg=10)
    return _save('forklift', X)


def specimen_tank():
    """glass tube with green liquid and a grey alien floating inside (origin at the base centre)"""
    X = Model()
    st = S('steel', 'vl', tex=True); liq = S('liquid', 'liquid'); gl = S('glass', 'glass', tag='t')
    revolve(X.mesh(st), [(56, 0), (56, 30), (50, 34), (50, 36)], n=20, u_tiles=2)
    revolve(X.mesh(st), [(50, 220), (56, 224), (56, 250), (20, 260)], n=20, u_tiles=2)
    revolve(X.mesh(liq), [(46, 36), (46, 200)], n=20, u_tiles=1, vlen=164)
    disc(X.mesh(liq), 46, 200, True, 20)
    revolve(X.mesh(gl), [(49, 36), (49, 220)], n=20, u_tiles=1, vlen=184)
    alien_into(X, (0, 0, 50), 0.62, 'vl', pose='float')
    for a in (0, 2.1, 4.2):
        tube(X.mesh(st), [(52 * math.cos(a), 52 * math.sin(a), 250), (70 * math.cos(a), 70 * math.sin(a), 320)], 4, nseg=5)
    return _save('spec_tank', X)


def alien_into(X, base, s, kind, pose='stand'):
    """grey alien figure (height ~170*s), facing +x"""
    skin = S('skin_grey', kind); eye = S('paint_black', kind, tag='e')
    b = np.asarray(base, float)
    arms = 0.0 if pose == 'stand' else 0.6
    ellipsoid(X.mesh(skin), b + np.array([0, 0, 150 * s]), 26 * s, 24 * s, 30 * s, nu=14, nv=10)                    # head
    ellipsoid(X.mesh(skin), b + np.array([4 * s, 0, 126 * s]), 14 * s, 13 * s, 10 * s, nu=10, nv=6)                 # chin
    for sy in (-1, 1):
        ellipsoid(X.mesh(eye), b + np.array([20 * s, sy * 11 * s, 152 * s]), 6 * s, 9 * s, 14 * s, nu=10, nv=6,
                  R=rot_axis((1, 0, 0), sy * 0.5))
    tube(X.mesh(skin), [b + [0, 0, 120 * s], b + [0, 0, 108 * s]], 5 * s, nseg=8)
    ellipsoid(X.mesh(skin), b + np.array([0, 0, 82 * s]), 14 * s, 18 * s, 28 * s, nu=12, nv=8)                     # torso
    for sy in (-1, 1):
        tube(X.mesh(skin), [b + [0, sy * 16 * s, 100 * s], b + [6 * s, sy * (26 + 20 * arms) * s, 70 * s], b + [8 * s, sy * (28 + 30 * arms) * s, 40 * s]], 3.5 * s, nseg=6)
        tube(X.mesh(skin), [b + [0, sy * 8 * s, 58 * s], b + [2 * s, sy * (10 + 8 * arms) * s, 28 * s], b + [0, sy * (11 + 12 * arms) * s, 2 * s]], 4.5 * s, nseg=6)


def alien():
    X = Model()
    alien_into(X, (0, 0, 0), 0.7, 'vl')
    return _save('alien', X)


def autopsy_table():
    X = Model()
    st = S('steel', 'vl', tex=True, tag='a'); sheet = S('paint_white', 'vl', tag='sh')
    boxm(X.mesh(st), (-120, -44, 64), (120, 44, 72), tile=64)
    revolve(X.mesh(st), [(20, 0), (20, 4), (8, 8), (8, 64)], n=12)
    # covered body (sheet) with the head sticking out
    ellipsoid(X.mesh(sheet), (-10, 0, 74), 80, 30, 14, nu=14, nv=6, flat_bottom=0)
    skin = S('skin_grey', 'vl')
    ellipsoid(X.mesh(skin), (88, 0, 84), 18, 16, 14, nu=12, nv=8)
    for sy in (-1, 1):
        ellipsoid(X.mesh(S('paint_black', 'vl', tag='e')), (100, sy * 7, 90), 4, 6, 8, nu=8, nv=5)
    # lamp over the table
    lamp = S('glow_white', 'vl_glow', tag='t')
    return _save('autopsy', X)


def server_rack():
    X = Model()
    rk = S('rack', 'vl_glow')
    dk = S('paint_dark', 'vl', tag='rk')
    rbox(X.mesh(dk), (-40, -32, 0), (40, 32, 220), r=2, tile=128, faces='nswtb')
    Mm = X.mesh(rk)
    Mm.quad((40.5, -30, 6), (40.5, 30, 6), (40.5, 30, 214), (40.5, -30, 214), 64, n=(1, 0, 0))
    for v, st in zip(range(len(Mm.V) - 4, len(Mm.V)), ((0, 1), (1, 1), (1, 0), (0, 0))): Mm.ST[v] = st
    return _save('rack', X)


def console():
    X = Model()
    dk = S('paint_dark', 'vl', tag='cn'); scr = S('screen_data', 'vl_glow')
    Mm = Mesh()
    prof = [(-40, 0), (40, 0), (40, 70), (10, 90), (-40, 90)]
    for i in range(len(prof) - 1):
        (xa, za), (xb, zb) = prof[i], prof[i + 1]
        n = np.array([zb - za, 0, -(xb - xa)]); n = -n / np.linalg.norm(n)
        Mm.quad((xa, -80, za), (xb, -80, zb), (xb, 80, zb), (xa, 80, za), 64, n=n)
    for sy in (-1, 1): Mm.poly([(x, sy * 80, z) for (x, z) in (prof if sy > 0 else prof[::-1])], (0, sy, 0), [(x / 64, z / 64) for (x, z) in prof])
    X.mesh(dk).add(Mm)
    X.mesh(scr).quad((40.5, -70, 72), (40.5, 70, 72), (10.5, 70, 89), (10.5, -70, 89), 64)
    for v, st in zip(range(len(X.mesh(scr).V) - 4, len(X.mesh(scr).V)), ((0, 1), (1, 1), (1, 0), (0, 0))): X.mesh(scr).ST[v] = st
    boxm(X.mesh(dk), (-30, -60, 90), (-20, 60, 170))
    q = X.mesh(scr)
    q.quad((-19.5, -56, 100), (-19.5, 56, 100), (-19.5, 56, 164), (-19.5, -56, 164), 64, n=(1, 0, 0))
    for v, st in zip(range(len(q.V) - 4, len(q.V)), ((0, 1), (1, 1), (1, 0.4), (0, 0.4))): q.ST[v] = st
    return _save('console', X)


def lockers():
    X = Model()
    m = S('locker', 'vl')
    for i in range(4):
        y0 = -96 + i * 48
        Mm = Mesh(); rbox(Mm, (-24, y0 + 1, 0), (24, y0 + 47, 176), r=1.5, tile=48)
        for k, (v, n) in enumerate(zip(Mm.V, Mm.N)):
            Mm.ST[k] = ((v[1] - y0) / 48, 1 - v[2] / 176)
        X.mesh(m).add(Mm)
    return _save('lockers', X)


def bunk():
    X = Model()
    frm = S('paint_dark', 'vl', tag='bu'); mat = S('mattress', 'vl')
    for (x, y) in ((-100, -40), (-100, 40), (100, -40), (100, 40)):
        tube(X.mesh(frm), [(x, y, 0), (x, y, 150)], 3, nseg=6)
    for z in (30, 110):
        boxm(X.mesh(frm), (-104, -44, z), (104, 44, z + 6))
        rbox(X.mesh(mat), (-98, -38, z + 6), (98, 38, z + 18), r=5, tile=64)
        rbox(X.mesh(mat), (70, -30, z + 18), (94, 30, z + 26), r=5, tile=32)
    return _save('bunk', X)


def filing():
    X = Model()
    m = S('paint_olive', 'vl')
    rbox(X.mesh(m), (-26, -24, 0), (26, 24, 112), r=1.5, tile=64)
    for z in (14, 40, 66, 92): boxm(X.mesh(S('paint_dark', 'vl', tag='fi')), (25, -10, z), (28, 10, z + 4))
    return _save('filing', X)


def generator():
    X = Model()
    ol = S('paint_olive', 'lm', tag='gen'); dk = S('paint_dark', 'lm', tag='gen'); y = S('hazard', 'lm', tex=True, tag='g')
    rbox(X.mesh(ol), (-160, -72, 24), (160, 72, 160), r=8, tile=128)
    boxm(X.mesh(dk), (-170, -80, 0), (170, 80, 24), tile=128)
    for k in range(10): boxm(X.mesh(dk), (-150 + k * 16, 72, 40), (-144 + k * 16, 76, 140))
    tube(X.mesh(dk), [(120, 0, 160), (120, 0, 230), (140, 0, 240)], 9, nseg=8)
    X.mesh(y).quad((-160, -72.5, 30), (160, -72.5, 30), (160, -72.5, 44), (-160, -72.5, 44), 48, n=(0, -1, 0))
    return _save('generator', X)


def fueltank():
    """horizontal tank along x (r 112, length 448) on two saddles; origin at ground centre"""
    X = Model()
    wh = S('paint_white', 'lm', tag='ft'); dk = S('paint_dark', 'lm', tag='ft'); rd = S('paint_red', 'lm')
    R, L, zc = 112, 224, 144
    Mm = Mesh()
    revolve(Mm, [(R, -L), (R, L)], u_tiles=4, n=24, vlen=256)
    revolve(Mm, [(0, -L - 30), (R * 0.8, -L - 18), (R, -L)], u_tiles=4, n=24)
    revolve(Mm, [(R, L), (R * 0.8, L + 18), (0, L + 30)], u_tiles=4, n=24)
    transform_mesh(Mm, rot_axis((0, 1, 0), math.pi / 2), (0, 0, zc))
    X.mesh(wh).add(Mm)
    for x in (-150, 150):
        X.mesh(dk).poly([(x - 20, -90, 0), (x + 20, -90, 0), (x + 20, -90, 60), (x - 20, -90, 60)], (0, -1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
        boxm(X.mesh(dk), (x - 20, -96, 0), (x + 20, 96, 56))
    Ms = Mesh(); revolve(Ms, [(R + 1, -12), (R + 1, 12)], u_tiles=4, n=24); transform_mesh(Ms, rot_axis((0, 1, 0), math.pi / 2), (0, 0, zc))
    X.mesh(rd).add(Ms)
    return _save('fueltank', X)


def container():
    """shipping container along x (length 384, width 160, height 160), doors open at the -x end; origin at ground centre"""
    X = Model()
    c = S('corr_red', 'lm'); cin = S('corr_red', 'lm', tag='i'); dk = S('paint_dark', 'lm', tag='ct')
    hx, hy, h, t = 192, 80, 160, 6
    wall(X.mesh(c), (0, -hy, 0), (1, 0, 0), (0, -1, 0), -hx, hx, 0, h, (), tile=96, back=False)
    wall(X.mesh(c), (0, hy, 0), (1, 0, 0), (0, 1, 0), -hx, hx, 0, h, (), tile=96, back=False)
    wall(X.mesh(cin), (0, -hy + t, 0), (1, 0, 0), (0, 1, 0), -hx, hx - t, 0, h - t, (), tile=96, back=False)
    wall(X.mesh(cin), (0, hy - t, 0), (1, 0, 0), (0, -1, 0), -hx, hx - t, 0, h - t, (), tile=96, back=False)
    wall(X.mesh(c), (hx, 0, 0), (0, 1, 0), (1, 0, 0), -hy, hy, 0, h, (), tile=96, back=False)
    wall(X.mesh(cin), (hx - t, 0, 0), (0, 1, 0), (-1, 0, 0), -hy + t, hy - t, 0, h - t, (), tile=96, back=False)
    boxm(X.mesh(c), (-hx, -hy, h - t), (hx, hy, h), tile=96)
    boxm(X.mesh(dk), (-hx, -hy, 0), (hx, hy, 4), tile=96, faces='t')
    for sy in (-1, 1):
        # door leaves swung fully open against the side walls
        boxm(X.mesh(c), (-hx + 4, sy * (hy + 2) + (0 if sy > 0 else -6), 4), (-hx + 4 + 76, sy * (hy + 2) + (6 if sy > 0 else 0), h - 6), tile=96)
    for (xx, yy) in ((-hx, -hy), (-hx, hy), (hx, -hy), (hx, hy)):
        boxm(X.mesh(dk), (xx - 6, yy - 6, 0), (xx + 6, yy + 6, h + 2))
    return _save('container', X)


def joshua(seed):
    X = Model()
    bk = S('bark_j', 'vl'); lf = S('leaf_j', 'alpha_vl')
    rng = np.random.default_rng(seed)
    def branch(p, d, L, r, depth):
        q = p + d * L
        tube(X.mesh(bk), [p, (p + q) / 2 + rng.uniform(-6, 6, 3), q], [r, r * 0.9, r * 0.75], nseg=7)
        if depth == 0 or L < 40:
            for _ in range(3):
                c = q + rng.uniform(-10, 10, 3) + d * 10
                sz = rng.uniform(28, 40)
                for ang in (0, math.pi / 2):
                    u = np.array([math.cos(ang), math.sin(ang), 0])
                    X.mesh(lf).quad(c - u * sz - [0, 0, sz], c + u * sz - [0, 0, sz], c + u * sz + [0, 0, sz], c - u * sz + [0, 0, sz], 2 * sz)
                    for v, st in zip(range(len(X.mesh(lf).V) - 4, len(X.mesh(lf).V)), ((0, 1), (1, 1), (1, 0), (0, 0))): X.mesh(lf).ST[v] = st
            return
        for _ in range(2):
            nd = d + rng.uniform(-0.8, 0.8, 3); nd[2] = abs(nd[2]) + 0.4; nd /= np.linalg.norm(nd)
            branch(q, nd, L * rng.uniform(0.55, 0.75), r * 0.7, depth - 1)
    branch(np.array([0, 0, -4.0]), np.array([0, 0, 1.0]), rng.uniform(150, 200), 16, 3)
    return _save(f'joshua{seed}', X)


def tumbleweed():
    X = Model()
    tw = S('tumble', 'alpha_vl')
    for k in range(10):
        a = k * math.pi / 10
        for b in (0, math.pi / 2):
            u = np.array([math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b)]) * 34
            Mm = X.mesh(tw)
            w = np.cross(u, [0.1, 0.2, 0.97]); w = w / np.linalg.norm(w) * 34
            c = np.array([0, 0, 32.0])
            Mm.quad(c - u - w, c + u - w, c + u + w, c - u + w, 68)
            for v, st in zip(range(len(Mm.V) - 4, len(Mm.V)), ((0, 1), (1, 1), (1, 0), (0, 0))): Mm.ST[v] = st
    return _save('tumbleweed', X)


def rocks(seed, s=1.0):
    X = Model()
    rk = S('rock_m', 'vl')
    rng = np.random.default_rng(seed)
    for i in range(rng.integers(2, 4)):
        c = np.array([rng.uniform(-40, 40) * s, rng.uniform(-40, 40) * s, 0])
        a, b, h = rng.uniform(40, 80) * s, rng.uniform(35, 70) * s, rng.uniform(30, 70) * s
        ellipsoid(X.mesh(rk), c, a, b, h, nu=12, nv=7, bump=lambda p, t: 1 + 0.12 * math.sin(t * 3 + i) * math.cos(p * 2), flat_bottom=0)
    return _save(f'rocks{seed}', X)


def cow_into(X, base, kind, s=1.0):
    hide = S('cow', kind); dk = S('paint_black', kind, tag='cw'); pk = S('paint_pink', kind)
    b = np.asarray(base, float)
    ellipsoid(X.mesh(hide), b + np.array([0, 0, 70 * s]), 60 * s, 30 * s, 30 * s, nu=14, nv=8)
    ellipsoid(X.mesh(hide), b + np.array([66 * s, 0, 86 * s]), 22 * s, 16 * s, 16 * s, nu=10, nv=6)
    ellipsoid(X.mesh(pk), b + np.array([84 * s, 0, 80 * s]), 9 * s, 13 * s, 9 * s, nu=8, nv=5)
    for (x, y) in ((40, -16), (40, 16), (-40, -16), (-40, 16)):
        tube(X.mesh(hide), [b + [x * s, y * s, 50 * s], b + [x * s, y * s, 6 * s]], 6 * s, nseg=6)
        tube(X.mesh(dk), [b + [x * s, y * s, 8 * s], b + [x * s, y * s, 0]], 6.5 * s, nseg=6)
    for sy in (-1, 1):
        tube(X.mesh(dk), [b + [62 * s, sy * 10 * s, 100 * s], b + [64 * s, sy * 18 * s, 110 * s]], 2.5 * s, nseg=5)
    ellipsoid(X.mesh(pk), b + np.array([-20 * s, 0, 42 * s]), 12 * s, 10 * s, 8 * s, nu=8, nv=5)
    tube(X.mesh(hide), [b + [-58 * s, 0, 82 * s], b + [-66 * s, 0, 40 * s]], 2 * s, nseg=4)


def cow():
    X = Model()
    cow_into(X, (0, 0, 0), 'vl')
    return _save('cow', X)


def mailbox():
    X = Model()
    mb = S('mailbox', 'vl'); post = S('bark_j', 'vl', tag='p')
    boxm(X.mesh(post), (-6, -6, 0), (6, 6, 90), tile=64)
    Mm = Mesh()
    revolve(Mm, [(0.1, -40), (22, -40), (22, 40), (0.1, 40)], u_tiles=1, n=16)
    for i, v in enumerate(Mm.V):
        Mm.V[i] = np.array([v[0], v[1], max(v[2] * 0 + v[2], v[2])])
    transform_mesh(Mm, rot_axis((0, 1, 0), math.pi / 2), (0, 0, 110))
    X.mesh(mb).add(Mm)
    boxm(X.mesh(mb), (-40, -22, 88), (40, 22, 110))
    return _save('mailbox', X)


# ================================================================================================= movers (IQM)
def scout_iqm():
    """the hovering scout over the crater with its tractor beam and a lifted cow; func_rotating origin at the scout
    (z SCOUT_Z), beam reaches down to the crashed saucer top"""
    X = Model()
    k = 0.5
    scout_mesh(X, k)
    bm = S('beam', 'beam', tag='g')
    Mm = X.mesh(bm)
    n = 20; top_r, bot_r = 90, 150; L = SCOUT_Z - BEAM_FOOT
    for j in range(n):
        a0, a1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
        o = len(Mm.V)
        for (a, z, r, v, u) in ((a0, 0, top_r, 0, 0.5), (a1, 0, top_r, 0, 0.5), (a1, -L, bot_r, 1, 0.5), (a0, -L, bot_r, 1, 0.5)):
            Mm.add_v((r * math.cos(a), r * math.sin(a), z), (math.cos(a), math.sin(a), 0), (u, v))
        Mm.tri(o, o + 1, o + 2); Mm.tri(o, o + 2, o + 3)
    cow_into(X, (0, 0, -L * 0.55), 'dyn', 0.8)
    return _save_iqm('scout', X)


SCOUT_Z = 1000
BEAM_FOOT = 140                      # set from the crashed scout's dome top below


def orbiter_iqm():
    """a saucer circling far out over the base (func_rotating origin at the map centre, radius ORBIT_R)"""
    X = Model()
    Y = Model()
    scout_mesh(Y, 0.6, tag='o')
    for sh, Mm in Y.m.items():
        Mm2 = X.mesh(sh)
        Mm2.add(Mm, R=rot_axis((1, 0, 0), math.radians(8)), t=(0, ORBIT_R, 0))
    return _save_iqm('orbiter', X)


ORBIT_R = 1900
ORBIT_Z = 1900


def searchlight_iqm(name, length=1500):
    Mm, X = beam_iqm(name, length, 18, 170, 'w')
    # tilt the cone down 28 deg
    R = rot_axis((0, 1, 0), math.radians(28))
    for sh, M2 in X.m.items():
        M2.V = [R @ v for v in M2.V]; M2.N = [R @ nn for nn in M2.N]
    lamp = S('glow_white', 'dynglow', tag='sl')
    sphere(X.mesh(lamp), (0, 0, 0), 22, nu=10, nv=6)
    return _save_iqm(name, X)


def mother_core():
    """spinning energy core of the mothership (model2 on a func_rotating)"""
    X = Model()
    c = S('glow_teal', 'dynglow', tag='mc'); r = S('glyphs', 'dynglow', tag='mr')
    sphere(X.mesh(c), (0, 0, 0), 60, nu=16, nv=10)
    for (ax, rr) in (((1, 0, 0), 110), ((0, 1, 0), 130), ((1, 1, 0), 150)):
        Mm = Mesh()
        tube(Mm, [(rr * math.cos(t), rr * math.sin(t), 0) for t in np.linspace(0, 2 * math.pi, 41)], 6, nseg=6, caps=(False, False))
        transform_mesh(Mm, rot_axis(ax, math.pi / 3), (0, 0, 0))
        X.mesh(r).add(Mm)
    return _save('mother_core', X)


# ================================================================================================= moon-landing film set
def lander():
    """lunar module prop: gold-foil octagonal descent stage on four splayed legs, angular ascent stage (origin = ground)"""
    X = Model()
    foil = S('foil', 'lm'); grey = S('paint_white', 'lm', tag='lm'); dk = S('paint_dark', 'lm', tag='lm')
    oct_ = [(56 * math.cos(math.radians(22.5 + 45 * k)), 56 * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    prism(X.mesh(foil), oct_, 60, 104, tile=64)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c, s_ = math.cos(a), math.sin(a)
        top = np.array([50 * c, 50 * s_, 96]); foot = np.array([110 * c, 110 * s_, 10])
        tube(X.mesh(grey), [top, foot], 4, nseg=6)
        tube(X.mesh(grey), [np.array([50 * c, 50 * s_, 64]), foot], 3, nseg=5)
        revolve(X.mesh(grey), [(14, 0), (16, 4), (12, 10)], n=10, cx=foot[0], cy=foot[1])
    rbox(X.mesh(grey), (-40, -36, 104), (40, 36, 150), r=6, tile=64)
    X.mesh(dk).poly([(40.5, -18, 116), (40.5, 18, 116), (40.5, 18, 140), (40.5, -18, 140)], (1, 0, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    tube(X.mesh(grey), [(0, 0, 150), (0, 0, 176)], 3, nseg=5)
    disc(X.mesh(grey), 16, 176, True, 12)
    return _save('lander', X)


def flag():
    X = Model()
    pole = S('paint_white', 'vl', tag='fp'); cloth = S('flag', 'vl2s')
    tube(X.mesh(pole), [(0, 0, 0), (0, 0, 220)], 2.5, nseg=6)
    tube(X.mesh(pole), [(0, 0, 214), (110, 0, 214)], 1.5, nseg=5)
    Mm = X.mesh(cloth)
    nu, nv = 10, 4
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        for j in range(nu + 1):
            x = 110 * j / nu
            P[i, j] = (x, 4 * math.sin(x / 18), 214 - 66 * i / nv); UV[i, j] = (j / nu, i / nv)
    Mm.grid(P, grid_normals(P), UV)
    return _save('flag', X)


def tex_flag(w=256, h=160):
    im = Image.new('RGB', (w, h), (240, 240, 240)); d = ImageDraw.Draw(im)
    for k in range(13):
        if k % 2 == 0: d.rectangle((0, k * h / 13, w, (k + 1) * h / 13), fill=(190, 30, 40))
    d.rectangle((0, 0, w * 0.4, h * 7 / 13), fill=(40, 50, 120))
    for i in range(5):
        for j in range(6):
            d.ellipse((8 + j * 16, 6 + i * 16, 12 + j * 16, 10 + i * 16), fill=(240, 240, 240))
    return np.asarray(im, np.float32)


def tex_foil(n=128, seed=55):
    a = _fill(n, (210, 165, 60), 10, seed) + _noise(n, 0.8, seed + 1)[..., None] * 18
    return a


# ================================================================================================= shaders + make
def shaders():
    s = '// ---- MD3 models (a51_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        if opt.get('tex'): t = f'textures/padarea51/{img}'
        else: t = img if img.startswith('textures/') else f'{MD}/{img}'
        if kind in ('lm', 'lms', 'lm2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 70\n'
            if kind == 'lm2s': s += '\tcull none\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind in ('vl', 'vl2s'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n' + ('\tcull none\n' if kind == 'vl2s' else '') + f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n'
            if 'hull' in img or 'dome' in img:
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.25 0.25 0.3 )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind in ('glow', 'dynglow', 'vl_glow'):
            wave = opt.get('wave', 'identity')
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n'
            if opt.get('light'): s += f'\tq3map_surfacelight {opt["light"]}\n\tq3map_lightRGB {opt.get("rgb", "1 1 1")}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {wave}\n\t}}\n}}\n\n'
        elif kind in ('alpha', 'alpha_vl'):
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm alphashadow\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen {"vertex" if kind == "alpha_vl" else "identity"}\n\t}}\n')
            if kind == 'alpha':
                s += '\t{\n\t\tmap $lightmap\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\tdepthFunc equal\n\t\trgbGen identity\n\t}\n'
            s += '}\n\n'
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.22 0.25 0.3 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'liquid':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tq3map_surfacelight 120\n\tq3map_lightRGB 0.3 1 0.5\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave sin 0.75 0.15 0 0.4\n\t\ttcMod scroll 0 0.12\n\t\ttcMod turb 0 0.03 0 0.2\n\t}}\n}}\n\n')
        elif kind == 'beam':
            col = {'w': '0.55 0.55 0.5', 'g': '0.25 0.9 0.4'}[opt.get('tag', 'w')]
            s += (f'{name}\n{{\n\tqer_editorimage {MD}/beam_light\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n\tcull none\n'
                  f'\t{{\n\t\tmap {MD}/beam_light\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {col} )\n'
                  + ('\t\ttcMod scroll 0 -0.5\n' if opt.get('tag') == 'g' else '') + '\t}\n}\n\n')
    return s


def make(out):
    global OUT
    OUT = out
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    def sv(nm, a):
        im = a if isinstance(a, Image.Image) else _img(a)
        if im.mode == 'RGBA': im.save(os.path.join(d, nm + '.tga'))
        else: im.convert('RGB').save(os.path.join(d, nm + '.jpg'), quality=92)
    sv('corr', tex_corr()); sv('corr_in', tex_corr(256, 256, 2, (92, 96, 92))); sv('corr_roof', tex_corr(256, 256, 3, (138, 142, 136)))
    sv('corr_red', tex_corr(256, 256, 4, (150, 60, 44)))
    sv('beam', tex_paint((110, 116, 120), 64, 5)); sv('lamp_white', tex_glow((250, 250, 235)))
    sv('num18', tex_num18()); sv('num51', tex_stencil('51', 256, 256, alpha=True, fg=(40, 40, 44)))
    sv('hull', tex_hull()); sv('hull_dark', tex_hull(512, 4, (96, 100, 108))); sv('hull_burnt', tex_hull(512, 6, (90, 84, 78)) * 0.9)
    sv('glyphs', tex_glyphs()); sv('alien_wall', tex_alien_wall()); sv('dome', tex_glassy(64, (70, 40, 110)))
    sv('glow_teal', tex_glow((80, 255, 220))); sv('glow_amber', tex_glow((255, 180, 70))); sv('glow_red', tex_glow((255, 50, 40)))
    sv('glow_green', tex_glow((60, 255, 90))); sv('glow_white', tex_glow((250, 250, 240)))
    sv('concrete', tex_concrete()); sv('frame', tex_paint((70, 74, 80), 64, 7)); sv('roofing', tex_paint((60, 60, 62), 128, 8, 8))
    sv('glass', tex_glassy()); sv('glass_dark', tex_glassy(64, (20, 24, 30))); sv('paint_dark', tex_paint((44, 46, 50)))
    sv('screen_radar', tex_screen()); sv('screen_data', tex_screen(256, 128, 34, 'data'))
    sv('tank', tex_tank()); sv('paint_white', tex_paint((220, 222, 220))); sv('dish', tex_dish())
    sv('plywood', tex_paint((150, 130, 96), 128, 9, 6)); sv('stealth', tex_stealth())
    sv('stencil_s4', tex_stencil('S-4', 512, 256)); sv('barrier_arm', tex_barrier_arm())
    sv('drum_yellow', tex_drum(128, 128, (210, 170, 30), 17)); sv('drum_blue', tex_drum(128, 128, (40, 80, 160), 18, False))
    sv('drum_rust', tex_drum(128, 128, (130, 80, 50), 19, False)); sv('drum_green', tex_drum(128, 128, (60, 110, 60), 20))
    sv('crate', tex_crate()); sv('barrier', tex_barrier()); sv('sandbag', tex_sandbag()); sv('camo', tex_camo())
    sv('paint_yellow', tex_paint((220, 180, 30))); sv('paint_olive', tex_paint((90, 96, 60))); sv('paint_red', tex_paint((190, 40, 30)))
    sv('paint_black', tex_paint((12, 12, 14), 64, 3, 2)); sv('paint_pink', tex_paint((230, 160, 160)))
    sv('skin_grey', tex_skin()); sv('cow', tex_cow()); sv('liquid', tex_liquid()); sv('rack', tex_rack())
    sv('locker', tex_locker()); sv('mattress', tex_paint((90, 100, 80), 64, 11, 6)); sv('bark_j', tex_bark()); sv('leaf_j', tex_joshua_leaf())
    sv('tumble', tex_tumble()); sv('rock_m', tex_rock()); sv('mailbox', tex_mailbox()); sv('env', tex_env())
    sv('beam_light', tex_beam())
    sv('dirt', tex_paint((120, 100, 80), 128, 12, 10)); sv('flag', tex_flag()); sv('foil', tex_foil())
    hangar(); saucer(); saucer_crash(); tower(); watertower(); radar_base(); radar_dish(); quonset(); jet(); airstairs()
    bunker(); booth(); boom(); floodlight(); generator(); fueltank(); container()
    for nm, col in (('yellow', 0), ('blue', 0), ('rust', 0), ('green', 0)): drum(nm, col)
    crate('crate64', 64); crate('crate96', 96); barrier(); sandbags(); humvee(); forklift()
    specimen_tank(); alien(); autopsy_table(); server_rack(); console(); lockers(); bunk(); filing()
    for sd in (1, 2, 3): joshua(sd)
    tumbleweed()
    for sd in (1, 2, 3): rocks(sd)
    cow(); mailbox(); mother_core(); lander(); flag()
    scout_iqm(); orbiter_iqm(); searchlight_iqm('searchlight_a'); searchlight_iqm('searchlight_b')
    return shaders()


def tex_barrier_arm(w=256, h=32):
    x, y = _xy(w, h)
    a = np.where((np.floor(x * 8) % 2 == 0)[..., None], _C((210, 30, 25)), _C((240, 240, 235)))
    return a + _noise(w, 1, 3, h)[..., None] * 4


def tex_locker(w=64, h=256, seed=53):
    a = _fill(w, (100, 110, 100), 3, seed, h)
    im = _img(a); d = ImageDraw.Draw(im)
    d.rectangle((2, 2, w - 3, h - 3), outline=(70, 76, 70), width=2)
    for k in range(6): d.line([(14, 20 + k * 6), (w - 14, 20 + k * 6)], fill=(50, 54, 50), width=2)
    d.rectangle((w - 14, h * 0.45, w - 8, h * 0.55), fill=(180, 180, 170))
    return np.asarray(im, np.float32)


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    import a51_textures
    sh = make(o)
    import md3tool
    for fn in sorted(os.listdir(os.path.join(o, MD))):
        if fn.endswith('.md3'):
            m = md3tool.load(os.path.join(o, MD, fn))
            V = np.concatenate([s_['verts'] for s_ in m['surfaces']])
            print(fn, sum(len(s_['verts']) for s_ in m['surfaces']), 'v', sum(len(s_['tris']) for s_ in m['surfaces']), 't',
                  V.min(0).round(1), V.max(0).round(1), PLACE.get(fn[:-4]))


BEAM_FOOT = round(max(p[2] for p in crash_collision_points()))
