"""Procedural brush textures, the deep-space sky cube, shader + arena for wop_padspace (Starsplash Station).
All art is original and generated here.

make_textures() writes textures/padspace/* and env/padspace/* (sky); make_shader() writes scripts/padspace.shader
(brush textures + every MD3 shader registered in splib.REG); make_arena() writes scripts/wop_padspace.arena."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from splib import *
import splib

MAP = 'wop_padspace'
LONGNAME = 'Starsplash Station'
SIZES = {}
ALPHA = set()
SUN = (110.0, 38.0)                      # yaw (90 = north), elevation: a white star low in the north-north-west
PLANET_DIR = (215.0, 24.0)               # the ringed gas giant in the sky (south-west)
EARTH_DIR = (330.0, 14.0)                # Earth rising (south-east)

NAVY = (16, 22, 52); CYAN = (60, 230, 255); MAGENTA = (255, 60, 200); VIOLET = (130, 70, 255); LIME = (150, 255, 90)
WHITE = (236, 238, 244); MOON = (150, 150, 156)


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


# ------------------------------------------------------------------------------------------- ground
def craters(c, n, seed, count=40, rmin=0.01, rmax=0.07, depth=26):
    """tileable little impact craters: dark floor, bright raised rim toward the light (top-left)"""
    r = np.random.default_rng(seed)
    x, y = xy(n)
    for _ in range(count):
        cx, cy, rr = r.random(), r.random(), r.uniform(rmin, rmax) * (1 if r.random() > 0.15 else 1.8)
        dx = np.abs(x - cx); dx = np.minimum(dx, 1 - dx); dy = np.abs(y - cy); dy = np.minimum(dy, 1 - dy)
        sx = np.where(((x - cx) % 1.0) < 0.5, 1, -1); sy = np.where(((y - cy) % 1.0) < 0.5, 1, -1)
        d = np.hypot(dx, dy) / rr
        bowl = np.clip(1 - d, 0, 1)
        rim = np.exp(-((d - 1.05) / 0.12) ** 2)
        light = (-(dx * sx) - (dy * sy)) / (np.hypot(dx, dy) + 1e-6)
        c = c - (bowl ** 0.7 * depth * (0.6 + 0.4 * light))[..., None] + (rim * depth * 0.6 * (0.5 - 0.5 * light))[..., None]
    return c


def regolith(n=512, seed=3, base=(150, 148, 146), count=46):
    c = fill(n, base, 6, seed) + N3(n, 0.5, seed + 1, 14) + N3(n, 10, seed + 2, 10)
    c = craters(c, n, seed + 3, count)
    pebbles = np.clip(noise(n, 0.7, seed + 4) - 1.9, 0, 1)[..., None] * 60
    return c + pebbles


def plain(n=512, seed=5):
    return regolith(n, seed, (128, 126, 128), 70) * 0.92


def lunar_rock(n=512, seed=31, base=(122, 120, 124)):
    x, y = xy(n)
    strata = np.sin((y + noise(n, 14, seed) * 0.05) * 2 * math.pi * 5) * 8
    c = np.zeros((n, n, 3), np.float32) + C(base) + strata[..., None] + N3(n, 1, seed + 1, 12) + N3(n, 6, seed + 2, 16)
    cr = np.clip(np.abs(noise(n, 3, seed + 3)) < 0.05, 0, 1)
    c = craters(c * (1 - cr * 0.35)[..., None], n, seed + 4, 18, 0.01, 0.04, 20)
    return c


def bank(n=512, seed=25):
    return lunar_rock(n, seed, (104, 100, 108))


def plate(n=256, seed=33, base=(150, 158, 170)):
    """metal deck plating: 2x2 panels with seams, rivets and a diamond tread"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C(base) + N3(n, 0.6, seed, 4) + N3(n, 8, seed + 1, 5)
    u = (x * 2) % 1; v = (y * 2) % 1
    # diamond tread
    du = ((x * 24 + y * 24) % 1.0); dv = ((x * 24 - y * 24) % 1.0)
    tread = (np.abs(du - 0.5) < 0.08) & (np.abs((y * 48) % 2 - 1) < 0.5) | (np.abs(dv - 0.5) < 0.08) & (np.abs((y * 48) % 2 - 1) >= 0.5)
    c = np.where(tread[..., None], c + 18, c)
    seam = (np.minimum(u, 1 - u) < 0.012) | (np.minimum(v, 1 - v) < 0.012)
    c = np.where(seam[..., None], C((60, 64, 72)), c)
    riv = ((np.hypot(u - 0.05, v - 0.05) < 0.018) | (np.hypot(u - 0.95, v - 0.05) < 0.018) | (np.hypot(u - 0.05, v - 0.95) < 0.018) |
           (np.hypot(u - 0.95, v - 0.95) < 0.018))
    c = np.where(riv[..., None], C((200, 206, 214)), c)
    tone = np.random.default_rng(seed).uniform(-10, 10, 4)[(np.floor(x * 2) + 2 * np.floor(y * 2)).astype(int) % 4]
    return c + tone[..., None]


def hexdeck(n=512, seed=35, base=(218, 222, 232), seam=(40, 60, 90)):
    """white hexagon tiles; returns (colour, glow mask) - the seams glow cyan through an additive stage"""
    x, y = xy(n)
    s = 8.0                                  # hexes across
    X = x * s; Y = y * s * 2 / math.sqrt(3) * (math.sqrt(3) / 2) * 2
    # axial hex distance via cube coords
    q = (X * 2 / 3)
    r_ = (-X / 3 + Y / math.sqrt(3) * 1.0)
    def hround(q, r):
        x_, z_ = q, r; y_ = -x_ - z_
        rx, ry, rz = np.round(x_), np.round(y_), np.round(z_)
        dx, dy, dz = np.abs(rx - x_), np.abs(ry - y_), np.abs(rz - z_)
        m1 = (dx > dy) & (dx > dz); m2 = (~m1) & (dy > dz)
        rx = np.where(m1, -ry - rz, rx); ry = np.where(m2, -rx - rz, ry); rz = np.where(~m1 & ~m2, -rx - ry, rz)
        return rx, rz
    hq, hr = hround(q, r_)
    cxh = hq * 1.5; cyh = (hr + hq / 2) * math.sqrt(3)
    d = np.maximum.reduce([np.abs(X - cxh) * 0 + np.abs((Y - cyh)) * 1.0,
                           np.abs((X - cxh) * math.sqrt(3) / 2 + (Y - cyh) / 2),
                           np.abs((X - cxh) * math.sqrt(3) / 2 - (Y - cyh) / 2)]) / (math.sqrt(3) / 2)
    rng = np.random.default_rng(seed)
    tone = rng.uniform(-10, 10, 97)[((hq * 31 + hr * 17) % 97).astype(int)]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 0.6, seed + 1, 4)
    edge = d > 0.9
    c = np.where(edge[..., None], C(seam), c)
    glow = np.where(edge, 1.0, 0.0) * (0.6 + 0.4 * (rng.random(97)[((hq * 13 + hr * 7) % 97).astype(int)] > 0.7))
    g = np.zeros((n, n, 3), np.float32) + (glow * 255)[..., None] * (C(CYAN) / 255)
    g = np.asarray(img(g).filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    return c, g


def pool_tile(n=256, seed=17):
    """deep navy mosaic with scattered star tiles"""
    idx, ed = voronoi(n, 180, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-1, 1, (180, 3)) * np.array([8, 12, 22])
    c = np.zeros((n, n, 3), np.float32) + C((30, 60, 140)) + tone[idx] + N3(n, 0.8, seed + 1, 5)
    star = r.random(180) > 0.94
    c = np.where(star[idx][..., None], C((240, 230, 150)), c)
    c = c * (0.7 + 0.3 * np.clip(ed * 160, 0, 1))[..., None]
    x, y = xy(n)
    g = ((x * 2 % 1) < 0.02) | ((y * 2 % 1) < 0.02)
    return np.where(g[..., None], C((20, 40, 90)), c)


def pool_band(w=512, h=256, seed=19):
    """pool wall: navy tiles with a band of little planets, rockets and stars at the water line"""
    c = np.zeros((h, w, 3), np.float32) + C((26, 40, 100)) + N3(w, 0.8, seed, 5, h)
    x, y = xy(w, h)
    g = ((x * 8 % 1) < 0.02) | ((y * 4 % 1) < 0.03)
    c = np.where(g[..., None], C((16, 26, 70)), c)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((0, 14, w, 82), fill=(14, 16, 40))
    cols = [(255, 120, 60), (90, 200, 255), (250, 210, 80), (200, 110, 255), (120, 240, 140)]
    for k in range(8):
        x0 = k * w / 8 + w / 16
        if k % 2 == 0:
            col = cols[(k // 2) % len(cols)]
            d.ellipse((x0 - 18, 30, x0 + 18, 66), fill=col)
            d.ellipse((x0 - 32, 44, x0 + 32, 52), outline=(240, 236, 220), width=3)
        else:
            d.polygon([(x0, 24), (x0 + 9, 44), (x0 + 9, 64), (x0 - 9, 64), (x0 - 9, 44)], fill=(236, 236, 240))
            d.polygon([(x0 - 9, 56), (x0 - 18, 70), (x0 - 9, 66)], fill=(220, 50, 50)); d.polygon([(x0 + 9, 56), (x0 + 18, 70), (x0 + 9, 66)], fill=(220, 50, 50))
            d.ellipse((x0 - 4, 38, x0 + 4, 46), fill=(80, 180, 255))
            d.polygon([(x0 - 6, 68), (x0 + 6, 68), (x0, 80)], fill=(255, 180, 40))
    r = np.random.default_rng(seed)
    for _ in range(26):
        sx, sy = r.uniform(0, w), r.uniform(18, 80)
        d.point((sx, sy), fill=(255, 255, 230))
    return np.asarray(im, np.float32)


def coping(n=256, seed=21):
    x, y = xy(n)
    c = fill(n, (230, 232, 238), 4, seed)
    c = np.where((np.abs(y - 0.5) < 0.03)[..., None], C((60, 200, 240)), c)
    c = np.where((((x * 2) % 1) < 0.01)[..., None], C((150, 154, 164)), c)
    return c


def rim(w=512, h=256, seed=37):
    """park rim wall: grey hull panels, a yellow/black hazard band along the top"""
    x, y = xy(w, h)
    c = plate(w, seed, (120, 126, 136))[:h] if h <= w else plate(w, seed)
    c = np.asarray(img(c).resize((w, h)), np.float32)
    stripe = ((x * 16 + y * 4) % 1.0) < 0.5
    c = np.where(((y < 0.12) & stripe)[..., None], C((240, 200, 30)), c)
    c = np.where(((y < 0.12) & ~stripe)[..., None], C((30, 30, 30)), c)
    return c


def panel(n=256, seed=41, base=WHITE, seam=(150, 156, 168), rows=2, cols=2):
    """spacecraft hull panels: seams, rivet rows, subtle tone per panel"""
    x, y = xy(n)
    rng = np.random.default_rng(seed)
    k = (np.floor(x * cols) + cols * np.floor(y * rows)).astype(int)
    c = np.zeros((n, n, 3), np.float32) + C(base) + rng.uniform(-8, 8, rows * cols + 1)[k][..., None] + N3(n, 0.6, seed, 3) + N3(n, 10, seed + 1, 4)
    u = (x * cols) % 1; v = (y * rows) % 1
    sm = (np.minimum(u, 1 - u) < 0.01) | (np.minimum(v, 1 - v) < 0.01)
    c = np.where(sm[..., None], C(seam), c)
    rv = ((np.abs(u - 0.04) < 0.008) | (np.abs(u - 0.96) < 0.008)) & ((v * 10) % 1 < 0.3)
    return np.where(rv[..., None], c * 0.82, c)


def googie(w=512, h=512, seed=43):
    """Cosmic Cafe wall: turquoise with boomerangs and starbursts, a chrome band"""
    c = fill(w, (70, 196, 196), 4, seed, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for k in range(10):
        cx_, cy_ = rng.uniform(0, w), rng.uniform(0, h * 0.8)
        if k % 2:
            for a in range(8):
                ang = a * math.pi / 4
                d.line([(cx_, cy_), (cx_ + 22 * math.cos(ang), cy_ + 22 * math.sin(ang))], fill=(250, 240, 200), width=3)
        else:
            d.arc((cx_ - 40, cy_ - 20, cx_ + 40, cy_ + 20), 200, 340, fill=(250, 120, 90), width=8)
    d.rectangle((0, int(h * 0.86), w, h), fill=(200, 206, 214))
    d.rectangle((0, int(h * 0.86), w, int(h * 0.87)), fill=(120, 126, 136))
    return np.asarray(im, np.float32)


def gold_foil(n=256, seed=45):
    """crinkled gold foil (lander descent stage)"""
    c = fill(n, (214, 168, 60), 6, seed)
    cr = noise(n, 2, seed + 1) * 0.6 + noise(n, 0.8, seed + 2) * 0.4
    return c * (0.75 + 0.35 * np.clip(cr * 0.5 + 0.5, 0, 1))[..., None]


def starfloor(n=256, seed=47):
    """vault floor: black glass with a glowing grid and scattered stars"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((14, 14, 30)) + N3(n, 6, seed, 4)
    g = (np.minimum(x * 4 % 1, 1 - x * 4 % 1) < 0.01) | (np.minimum(y * 4 % 1, 1 - y * 4 % 1) < 0.01)
    c = np.where(g[..., None], C((90, 60, 220)), c)
    st = np.random.default_rng(seed).random((n, n)) > 0.996
    return np.where(st[..., None], C((240, 240, 255)), c)


def jumppad_tex(n=256):
    """launch pad: glowing cyan rings and chevrons on dark metal"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C((30, 32, 44))
    for r0 in (0.18, 0.30, 0.42):
        c = np.where((np.abs(rr - r0) < 0.02)[..., None], C(CYAN), c)
    ch = (np.abs(((a * 6 / (2 * math.pi)) % 1.0) - 0.5) < 0.08) & (rr > 0.2) & (rr < 0.4)
    c = np.where(ch[..., None], C((255, 200, 60)), c)
    c = np.where((rr < 0.07)[..., None], C((255, 255, 255)), c)
    c = np.where((rr > 0.47)[..., None], C((70, 74, 86)), c)
    return c + N3(n, 1, 35, 4)


def water_tex(n=256, seed=41, col=(30, 190, 210)):
    c = fill(n, col, 6, seed)
    r = np.sin(noise(n, 10, seed + 1) * 3) * 18
    sp = np.clip(noise(n, 0.6, seed + 2) - 2.0, 0, 1) * 160
    return c + r[..., None] + sp[..., None]


def vortex(n=512, seed=49):
    """the Black Hole's accretion swirl: a log spiral of violet and cyan around a black centre (rotated in the shader)"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy) * 2; a = np.arctan2(dy, dx)
    sp = np.sin(a * 3 + np.log(rr + 0.02) * 9 + noise(n, 6, seed) * 0.6)
    c = lerp(C((50, 20, 120)), C((60, 210, 255)), np.clip(sp * 0.5 + 0.5, 0, 1)[..., None] ** 2)
    c = c * np.clip((rr - 0.06) * 4, 0, 1)[..., None]
    c = c + (np.exp(-((rr - 0.12) / 0.03) ** 2) * 200)[..., None] * C((1.0, 0.7, 1.0))
    return np.where((rr > 1.0)[..., None], C((40, 30, 110)), c)


def caustic(n=256, seed=45):
    a = np.abs(noise(n, 5, seed)) + np.abs(noise(n, 5, seed + 1))
    v = np.clip(1.0 - a * 1.1, 0, 1) ** 3
    return np.zeros((n, n, 3), np.float32) + (v * 150)[..., None] * C((0.6, 0.9, 1.0))


def neon_strip(w=64, h=64, col=CYAN):
    x, y = xy(w, h)
    v = np.exp(-((y - 0.5) / 0.18) ** 2)
    return np.zeros((h, w, 3), np.float32) + (v[..., None] * C(col)) + (np.exp(-((y - 0.5) / 0.05) ** 2) * 120)[..., None]


SIGNS = {
    'sign_main': ('STARSPLASH STATION', None, 1024, 256, (14, 16, 40), CYAN),
    'sign_rocket': ('PADSTAR I', 'LAUNCH COMPLEX 39P', 1024, 256, (20, 20, 30), (255, 200, 60)),
    'sign_bh': ('THE BLACK HOLE', 'EVENT HORIZON AHEAD - SWIM AT YOUR OWN RISK', 1024, 192, (20, 10, 40), MAGENTA),
    'sign_springs': ('CRATER SPRINGS', None, 1024, 192, (14, 30, 40), LIME),
    'sign_planet': ('PLANET PADURN', None, 1024, 192, (30, 14, 40), (255, 170, 80)),
    'sign_cafe': ('COSMIC CAFE', None, 1024, 192, (20, 30, 40), (255, 110, 150)),
    'sign_mc': ('MISSION CONTROL', None, 1024, 160, (230, 234, 240), (30, 70, 170)),
    'sign_loo': ('ZERO-G LOO', None, 512, 128, (240, 240, 244), (40, 90, 200)),
    'sign_vault': ('THE STAR VAULT', 'YOU HAVE FOUND THE CENTRE OF THE UNIVERSE', 1024, 192, (10, 8, 26), (255, 220, 100)),
    'sign_lander': ('EAGLE PAD', None, 512, 128, (40, 40, 44), (240, 236, 220)),
}


def signboard(text, sub, w, h, bg, fg):
    a = text_img(text, int(w), int(h * (0.62 if sub else 1)), bg, fg, False, border=None, glow=fg)
    if sub:
        b = text_img(sub, int(w), h - a.shape[0], bg, tuple(v * 0.85 for v in fg), False)
        a = np.concatenate([a, b], 0)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((3, 3, w - 4, h - 4), outline=tuple(int(v) for v in fg), width=max(3, h // 40))
    return np.asarray(im, np.float32)


# ------------------------------------------------------------------------------------------- sky
def sdir(yaw, el):
    y_, e = math.radians(yaw), math.radians(el)
    return np.array([math.cos(e) * math.cos(y_), math.cos(e) * math.sin(y_), math.sin(e)])


def waves(Dn, W):
    v = np.zeros(Dn.shape[:2], np.float32)
    for (k, f, ph) in W:
        k = k / np.linalg.norm(k)
        v += np.sin((Dn @ k) * f + ph)
    return v / math.sqrt(len(W) / 2)


def make_sky(n=512):
    """deep space: black-violet with the Milky Way band, a nebula, a ringed gas giant (south-west), the Earth rising
    (south-east), a small white sun in the north-north-west and the grey crater ridge of the moon on the horizon"""
    d = out('env', NS); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    Uu, Vv = np.meshgrid(u, u)
    s = 2 * Uu - 1; t = 1 - 2 * Vv
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}
    A = np.linspace(-180, 180, 4097)
    ridge = 1.6 + 1.2 * np.sin(np.radians(A) * 3 + 0.7) * 0.5 + 0.9 * np.sin(np.radians(A) * 7 + 2.1) * 0.5 + 0.5 * np.sin(np.radians(A) * 17)
    ridge = np.clip(ridge, 0.4, 4.0)
    sd = sdir(*SUN); pd = sdir(*PLANET_DIR); ed = sdir(*EARTH_DIR)
    band_n = sdir(40, 60); band_n /= np.linalg.norm(band_n)        # Milky Way plane normal
    rng = np.random.default_rng(11)
    rw = np.random.default_rng(5)
    WV1 = [(rw.normal(size=3), rw.uniform(2, 5), rw.uniform(0, 6.3)) for _ in range(14)]
    WV2 = [(rw.normal(size=3), rw.uniform(8, 18), rw.uniform(0, 6.3)) for _ in range(24)]
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        zz = Dn[..., 2]
        az = np.degrees(np.arctan2(Dn[..., 1], Dn[..., 0]))
        el = np.degrees(np.arcsin(np.clip(zz, -1, 1)))
        c = np.zeros(Dn.shape, np.float32) + C((6, 6, 16))
        c = c + (np.clip(1 - np.abs(zz) * 2.5, 0, 1) * 10)[..., None] * C((0.6, 0.5, 1.0))
        # Milky Way: a soft band with dust lanes; nebula clouds near it (smooth plane-wave noise: no cube seams)
        bd = np.abs(Dn @ band_n)
        nn = waves(Dn, WV1); fn = waves(Dn, WV2)
        mw = np.exp(-(bd / 0.2) ** 2) * np.clip(0.8 + nn * 0.5, 0, 1.6)
        lane = np.clip(np.exp(-((Dn @ band_n + 0.02 * fn) / 0.035) ** 2), 0, 1)
        c = c + (mw * (1 - 0.75 * lane) * 85)[..., None] * C((1.0, 0.92, 1.1))
        nb = np.clip(nn * 0.9 + 0.35 - bd * 1.6, 0, 1.4) ** 1.5
        c = c + (nb * 70)[..., None] * C((1.0, 0.25, 0.8)) + (np.clip(fn * 0.8, 0, 1) * nb * 70)[..., None] * C((0.2, 0.8, 1.0))
        # stars
        st = rng.random(Dn.shape[:2])
        c = np.where((st > 0.9965)[..., None], c + C((150, 150, 170)) * rng.uniform(0.4, 1.0, Dn.shape[:2])[..., None], c)
        c = np.where((st > 0.9993)[..., None], C((255, 250, 240)), c)
        # sun: tiny hot disc + glare
        cs = np.clip(Dn @ sd, 0, 1)
        c = c + (cs ** 2000 * 600 + cs ** 120 * 80 + cs ** 12 * 14)[..., None] * C((1.0, 0.97, 0.9))
        # ringed gas giant
        cp = Dn @ pd
        ang = np.degrees(np.arccos(np.clip(cp, -1, 1)))
        Rp = 11.0
        # local frame on the sky round pd
        up = np.array([0, 0, 1.0]); e1 = np.cross(up, pd); e1 /= np.linalg.norm(e1); e2 = np.cross(pd, e1)
        px = np.degrees(np.arctan2(Dn @ e1, cp)); py = np.degrees(np.arctan2(Dn @ e2, cp))
        tilt = math.radians(18)
        rx = px * math.cos(tilt) + py * math.sin(tilt); ry = -px * math.sin(tilt) + py * math.cos(tilt)
        disc = (ang < Rp) & (cp > 0)
        bands = np.sin(ry / Rp * 9 + np.sin(rx / Rp * 3) * 0.6) * 0.5 + 0.5
        pc = lerp(C((210, 150, 90)), C((250, 220, 170)), bands[..., None])
        shade = np.clip(0.25 + 0.75 * np.clip((Dn @ sd) * 0 + (rx / Rp * 0.5 + 0.6), 0, 1), 0, 1)
        pc = pc * shade[..., None] * np.clip(1.2 - (ang / Rp) ** 4 * 0.6, 0, 1.2)[..., None]
        ringd = np.hypot(rx, ry * 4.2)
        ringm = (ringd > Rp * 1.35) & (ringd < Rp * 2.2) & (cp > 0)
        front = (ry < 0) | (~disc)
        rb = (np.sin(ringd * 2.4) * 0.5 + 0.5) * 0.5 + 0.5
        rc = C((220, 200, 160)) * rb[..., None]
        c = np.where(disc[..., None], pc, c)
        c = np.where((ringm & front)[..., None], lerp(c, rc, 0.85), c)
        # Earth rising: blue marble with clouds, half lit
        ce = Dn @ ed
        ange = np.degrees(np.arccos(np.clip(ce, -1, 1)))
        Re = 5.5
        f1 = np.cross(up, ed); f1 /= np.linalg.norm(f1); f2 = np.cross(ed, f1)
        qx = np.degrees(np.arctan2(Dn @ f1, ce)) / Re; qy = np.degrees(np.arctan2(Dn @ f2, ce)) / Re
        ed_disc = (ange < Re) & (ce > 0)
        land = (np.sin(qx * 4.1 + np.sin(qy * 3) * 1.5) + np.sin(qy * 3.7 + 1 + np.sin(qx * 2.3))) > 0.6
        ec = np.where(land[..., None], C((70, 130, 70)), C((30, 80, 190)))
        cl_ = (np.sin(qx * 9 + qy * 4 + np.sin(qy * 6)) * 0.6 + np.sin(qy * 8 - qx * 3) * 0.5) > 0.55
        ec = np.where(cl_[..., None], C((240, 244, 250)), ec)
        lit = np.clip((-qx * 0.8 + qy * 0.3) + 0.4, 0.06, 1)
        ec = ec * lit[..., None]
        c = np.where(ed_disc[..., None], ec, c)
        c = c + (np.exp(-((ange - Re) / 0.5) ** 2) * (ce > 0) * 60)[..., None] * C((0.4, 0.7, 1.0))
        # the moon's horizon: grey crater ridge, lit from the sun's side
        rh = np.interp(az, A, ridge)
        below = el < rh
        gl = C((90, 90, 96)) * (0.6 + 0.4 * np.clip(np.cos(np.radians(az - SUN[0])), 0, 1))[..., None] + N3(n, 1.2, 70 + len(k), 6)
        gl = gl * np.clip(0.55 + (el + 30) / 60, 0.3, 1.0)[..., None]
        c = np.where(below[..., None], gl, c)
        img(c).save(os.path.join(d, f'space_{k}.jpg'), quality=94)
    # drifting nebula wisps (additive cloud layer)
    c2 = np.clip(noise(512, 16, 81) * 0.6 + noise(512, 5, 82) * 0.4 - 0.5, 0, 2)
    img(np.zeros((512, 512, 3)) + (c2 * 80)[..., None] * C((0.9, 0.4, 1.0))).save(os.path.join(d, 'space_wisps.jpg'), quality=92)
    W('skylight', fill(64, (140, 130, 220), 2, 45))


# ------------------------------------------------------------------------------------------- all brush textures
def make_textures():
    W('regolith', regolith()); W('regolith_d', regolith(512, 9, (124, 122, 124))); W('plain', plain()); W('lunar_rock', lunar_rock())
    W('bank', bank()); W('plate', plate()); W('plate_d', plate(256, 51, (90, 96, 108)))
    c, g = hexdeck(); W('hexdeck', c); W('hexdeck_glow', g)
    W('pool_tile', pool_tile()); W('pool_band', pool_band()); W('coping', coping()); W('rim', rim())
    W('panel_w', panel()); W('panel_d', panel(256, 53, (70, 74, 86), (40, 42, 50))); W('panel_red', panel(256, 55, (196, 40, 40), (120, 20, 20)))
    W('googie', googie()); W('gold_foil', gold_foil()); W('starfloor', starfloor())
    W('mc_wall', panel(256, 57, (226, 230, 238), (60, 110, 200), 2, 1)); W('pod_wall', panel(256, 59, (236, 236, 228), (240, 140, 40), 3, 2))
    W('carpet', fill(128, (60, 40, 110), 6, 61) + N3(128, 0.5, 62, 10))
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (50, 52, 60), 3, 59)); W('water', water_tex()); W('water_deep', water_tex(256, 67, (90, 50, 200)))
    W('water_bh', water_tex(256, 69, (60, 30, 140))); W('vortex', vortex())
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 69)); W('clip_ed', fill(64, (200, 120, 40), 2, 71)); W('caustic', caustic())
    W('dark', fill(64, (14, 14, 22), 2, 73)); W('neon_c', neon_strip()); W('neon_m', neon_strip(col=MAGENTA)); W('neon_y', neon_strip(col=(255, 210, 60)))
    for nm, (t, sub, w, h, bg, fg) in SIGNS.items():
        W(nm, signboard(t, sub, w, h, bg, fg))
    make_sky()


# ------------------------------------------------------------------------------------------- shader
STEPS = {'regolith': 'sandsteps', 'regolith_d': 'sandsteps', 'plate': 'latticesteps', 'plate_d': 'latticesteps', 'pool_tile': 'splashsteps',
         'carpet': 'carpetsteps', 'coping': None}
CAUSTIC_ON = {'pool_tile', 'pool_band', 'lunar_rock'}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


CAUSTIC_STAGE = (f'\t{{\n\t\tmap {TD}/caustic\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.35 0.35 0.35 )\n'
                 f'\t\ttcMod scale 0.5 0.5\n\t\ttcMod turb 0 0.05 0 0.12\n\t\ttcMod scroll 0.02 0.015\n\t}}\n')


def model_shaders():
    s = '// ---- MD3 / IQM models (sp_models.py)\n'
    for name, (im, kind, opt) in sorted(REG.items()):
        t = im if im.startswith('textures/') else f'{MD}/{im}'
        two = '\tcull none\n' if opt.get('two') else ''
        if kind in ('lm', 'lms'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle {opt.get("shade", 75)}\n{two}'
            if opt.get('steps'): s += f'\tsurfaceparm {opt["steps"]}\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            if opt.get('caustic'): s += CAUSTIC_STAGE
            if opt.get('glowmap'):
                s += f'\t{{\n\t\tmap {MD}/{opt["glowmap"]}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n'
            s += '}\n\n'
        elif kind == 'vl':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'flow':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen identity\n'
                  f'\t\ttcMod scroll 0 {opt.get("speed", -1.2)}\n\t}}\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.14 0.15 )\n\t\ttcMod scroll 0.05 {opt.get("speed", -1.2) * 1.4:g}\n\t}}\n}}\n\n')
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynglow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n'
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'flag':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nomarks\n\tsurfaceparm nonsolid\n\tcull none\n'
                  f'\tdeformVertexes wave {opt.get("div", 60)} sin 0 {opt.get("amp", 4)} 0 {opt.get("freq", 1.2)}\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.12 0.14 0.15")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.2 0.2 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'flicker':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave noise 0.85 0.15 {opt.get("ph", 0)} 6\n\t}}\n}}\n\n')
    return s


def water_shader(name, img_, extra_stage=''):
    return f'''{TD}/{name}
{{
	qer_editorimage {TD}/{img_}
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	cull none
	{{
		map {TD}/{img_}
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.6
		rgbGen identity
		tcMod turb 0 0.05 0 0.12
		tcMod scroll 0.01 0.02
	}}
	{{
		map {TD}/caustic
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.25 0.08 0 0.3
		tcMod scale 0.5 0.5
		tcMod scroll -0.02 0.01
	}}
{extra_stage}	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.18 0.24 )
		tcGen environment
	}}
}}

{TD}/{name}_nodraw
{{
	qer_editorimage {TD}/{img_}
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

'''


def make_shader(bh_centre=(0, 0)):
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padspace/sp_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'water', 'water_deep', 'water_bh', 'vortex', 'caustic', 'clip_ed', 'hexdeck', 'hexdeck_glow',
               'neon_c', 'neon_m', 'neon_y', 'plain'}
    for nm in sorted(SIZES):
        if nm in special or nm.startswith('sign_'): continue
        S_ += lm(nm, STEPS.get(nm), stage=CAUSTIC_STAGE if nm in CAUSTIC_ON else '')
    for nm in sorted(SIZES):
        if not nm.startswith('sign_'): continue
        S_ += lm(nm, extra='\tsurfaceparm nomarks\n', stage=f'\t{{\n\t\tmap {TD}/{nm}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.35 0.08 0 0.4\n\t}}\n')
    S_ += lm('hexdeck', extra='', stage=f'\t{{\n\t\tmap {TD}/hexdeck_glow\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.55 0.35 0 0.25\n\t}}\n')
    S_ += lm('plain', 'sandsteps', extra='\tq3map_globaltexture\n')
    pad_stage = f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.3 0.25 0 0.8\n\t\ttcMod rotate 40\n\t}}\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 80\n\tq3map_lightRGB 0.4 0.9 1\n\tq3map_lightSubdivide 128\n', stage=pad_stage)
    S_ += water_shader('water', 'water')
    S_ += water_shader('water_deep', 'water_deep')
    # the Black Hole: the vortex image fitted to the bowl and rotated round its centre (texture alignment in the .map)
    vstage = (f'\t{{\n\t\tmap {TD}/vortex\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n\t\ttcMod rotate -24\n\t}}\n'
              f'\t{{\n\t\tmap {TD}/vortex\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.35 0.35 0.35 )\n\t\ttcMod rotate -60\n\t\ttcMod stretch sin 1 0.03 0 0.2\n\t}}\n')
    S_ += water_shader('water_bh', 'water_bh', vstage).replace('\tq3map_globaltexture\n', '', 1)
    for nm, col in (('neon_c', CYAN), ('neon_m', MAGENTA), ('neon_y', (255, 210, 60))):
        S_ += (f'{TD}/{nm}\n{{\n\tqer_editorimage {TD}/{nm}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
               f'\tq3map_surfacelight 400\n\tq3map_lightRGB {col[0] / 255:.2f} {col[1] / 255:.2f} {col[2] / 255:.2f}\n\tq3map_lightSubdivide 64\n'
               f'\t{{\n\t\tmap {TD}/{nm}\n\t\trgbGen wave sin 0.9 0.1 0 0.5\n\t}}\n}}\n\n')
    S_ += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 1 0.97 0.92 170 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 55 3
	skyparms env/{NS}/space 512 -
	{{
		map env/{NS}/space_wisps
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.35 0.35 )
		tcMod scale 2 2
		tcMod scroll 0.003 0.0015
	}}
}}

{TD}/slide_clip
{{
	qer_editorimage {TD}/clip_ed
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm slick
	surfaceparm playerclip
	surfaceparm trans
}}

{TD}/nodraw_ns
{{
	qer_editorimage {TD}/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	surfaceparm nolightmap
}}

'''
    S_ += model_shaders()
    S_ += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(out('scripts'), exist_ok=True)
    open(out('scripts', NS + '.shader'), 'w').write(S_)


def make_arena():
    open(out('scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))
