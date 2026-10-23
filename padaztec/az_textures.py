"""Procedural brush textures, the jungle sky cube, shader + arena for wop_padaztec (Tlaloc's Lagoon).
All art is original and generated here.

make_textures() writes textures/padaztec/* and env/padaztec/* (sky); make_shader() writes scripts/padaztec.shader
(brush textures + every MD3 shader registered in azlib.REG); make_arena() writes scripts/wop_padaztec.arena."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from azlib import *
import azlib

MAP = 'wop_padaztec'
LONGNAME = "Tlaloc's Lagoon"
SIZES = {}
ALPHA = set()
SUN = (95.0, 56.0)                      # yaw (90 = north: southern hemisphere sun, the user plays in New Zealand), elevation

# Aztec palette
LIME = (214, 200, 168); LIME_D = (176, 160, 128); TEZ = (148, 62, 46); TURQ = (40, 168, 168); JADE = (62, 140, 92)
OCHRE = (204, 150, 60); INK = (34, 30, 28); STUCCO = (236, 228, 210); GOLD = (226, 178, 64)


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


# ------------------------------------------------------------------------------------------- stone
def ashlar(w=512, h=512, seed=1, base=LIME, rows=6, cols=3, jitter=14, mortar=0.7, moss=0.0):
    """cut stone courses with staggered joints, per-block tone, worn edges, optional moss in the joints"""
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    row = np.floor(y * rows).astype(int)
    off = (row % 2) * 0.5 / cols + r.uniform(-0.08, 0.08, rows + 1)[row % (rows + 1)] / cols
    cx_ = np.floor((x + off) * cols).astype(int)
    tone = r.uniform(-jitter, jitter, (rows + 1, cols + 3))[row % (rows + 1), cx_ % (cols + 3)]
    c = np.zeros((h, w, 3), np.float32) + C(base) + tone[..., None] + N3(w, 1, seed + 1, 6, h) + N3(w, 7, seed + 2, 7, h)
    fu = (x + off) * cols % 1.0; fv = y * rows % 1.0
    d = np.minimum(np.minimum(fu, 1 - fu) / cols * w / h, np.minimum(fv, 1 - fv) / rows)
    edge = np.clip(d * 60, 0, 1)
    c = c * (mortar + (1 - mortar) * edge)[..., None]
    pits = np.clip(noise(w, 0.7, seed + 3, h) - 2.0, 0, 1)[..., None]
    c = c * (1 - pits * 0.35)
    if moss > 0:
        m = np.clip((1 - edge) * 1.2 + noise(w, 5, seed + 4, h) * 0.35 - 0.6, 0, 1) * moss
        c = lerp(c, C((70, 100, 50)) + N3(w, 0.8, seed + 5, 14, h), m[..., None])
    return c


def pavers(n=512, seed=3, base=(212, 196, 162)):
    """big irregular plaza flagstones (Voronoi), sun-bleached, grass in a few joints"""
    idx, ed = voronoi(n, 26, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-16, 16, 26)[idx]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 1.2, seed + 1, 6) + N3(n, 8, seed + 2, 6)
    c = c * (0.62 + 0.38 * np.clip(ed * 90, 0, 1))[..., None]
    g = (ed < 0.008) & (noise(n, 10, seed + 3) > 0.4)
    return np.where(g[..., None], C((86, 120, 56)) + N3(n, 0.6, seed + 4, 18), c)


def red_path(n=256, seed=5):
    """red tezontle volcanic-stone path setts"""
    c = ashlar(n, n, seed, (150, 70, 52), 4, 4, 16, 0.55)
    holes = np.clip(noise(n, 0.5, seed + 1) - 1.6, 0, 1)[..., None]
    return c * (1 - holes * 0.5)


def fret_band(w=512, h=128, seed=7, bg=TEZ, fg=STUCCO, edge=INK):
    """xicalcoliuhqui (step-fret) frieze: stepped spirals alternating up and down, painted stucco"""
    im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 10), fill=edge); d.rectangle((0, h - 10, w, h), fill=edge)
    u = w // 4; m = 14
    for k in range(4):
        x0 = k * u
        flip = k % 2
        # stepped diagonal + spiral hook, as one polygon
        if not flip:
            pts = [(x0 + 4, h - m), (x0 + u * 0.25, h - m), (x0 + u * 0.25, h * 0.62), (x0 + u * 0.5, h * 0.62), (x0 + u * 0.5, h * 0.38),
                   (x0 + u * 0.75, h * 0.38), (x0 + u * 0.75, m), (x0 + u - 4, m), (x0 + u - 4, h * 0.55), (x0 + u * 0.88, h * 0.55),
                   (x0 + u * 0.88, m + 16), (x0 + u * 0.84, m + 16), (x0 + u * 0.84, h * 0.5), (x0 + u * 0.62, h * 0.5), (x0 + u * 0.62, h * 0.74),
                   (x0 + u * 0.38, h * 0.74), (x0 + u * 0.38, h - m - 16), (x0 + 4, h - m - 16)]
        else:
            pts = [(x0 + 4, m), (x0 + u * 0.25, m), (x0 + u * 0.25, h * 0.38), (x0 + u * 0.5, h * 0.38), (x0 + u * 0.5, h * 0.62),
                   (x0 + u * 0.75, h * 0.62), (x0 + u * 0.75, h - m), (x0 + u - 4, h - m), (x0 + u - 4, h * 0.45), (x0 + u * 0.88, h * 0.45),
                   (x0 + u * 0.88, h - m - 16), (x0 + u * 0.84, h - m - 16), (x0 + u * 0.84, h * 0.5), (x0 + u * 0.62, h * 0.5), (x0 + u * 0.62, h * 0.26),
                   (x0 + u * 0.38, h * 0.26), (x0 + u * 0.38, m + 16), (x0 + 4, m + 16)]
        d.polygon(pts, fill=fg, outline=edge)
    a = np.asarray(im, np.float32) + N3(w, 1, seed, 5, h) + N3(w, 10, seed + 1, 8, h)
    crack = np.clip(noise(w, 0.6, seed + 2, h) - 2.2, 0, 1)[..., None]
    return a * (1 - crack * 0.4)


def glyph_wall(w=512, h=512, seed=9, base=LIME):
    """carved relief panels: day-sign glyphs (water, flint, reed, house, rabbit...) in square cartouches"""
    c = ashlar(w, h, seed, base, 2, 2, 8, 0.8)
    hgt = np.zeros((h, w), np.float32)
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for gy in range(2):
        for gx in range(2):
            x0, y0 = gx * w // 2 + 20, gy * h // 2 + 20; s = w // 2 - 40
            d.rectangle((x0, y0, x0 + s, y0 + s), outline=255, width=8)
            cx, cy = x0 + s / 2, y0 + s / 2
            k = (gx + 2 * gy + seed) % 4
            if k == 0:                                     # water (atl): waves with droplets
                for i in range(3):
                    d.arc((cx - 80, cy - 70 + i * 40, cx + 80, cy - 10 + i * 40), 200, 340, fill=255, width=8)
                for i in range(4): d.ellipse((cx - 70 + i * 45, cy + 70, cx - 54 + i * 45, cy + 86), fill=255)
            elif k == 1:                                   # sun (tonatiuh): disc with rays
                d.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), outline=255, width=8)
                for i in range(8):
                    a = i * math.pi / 4
                    d.polygon([(cx + 60 * math.cos(a - 0.2), cy + 60 * math.sin(a - 0.2)), (cx + 95 * math.cos(a), cy + 95 * math.sin(a)),
                               (cx + 60 * math.cos(a + 0.2), cy + 60 * math.sin(a + 0.2))], fill=255)
                d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=255)
            elif k == 2:                                   # serpent head (coatl) in profile
                d.ellipse((cx - 80, cy - 50, cx + 40, cy + 50), outline=255, width=8)
                d.polygon([(cx + 30, cy - 30), (cx + 95, cy - 10), (cx + 30, cy + 5)], outline=255)
                d.ellipse((cx - 30, cy - 30, cx - 6, cy - 6), fill=255)
                for i in range(4): d.line([(cx - 70 + i * 18, cy + 50), (cx - 76 + i * 18, cy + 80)], fill=255, width=6)
            else:                                          # flint knife (tecpatl) with a face
                d.polygon([(cx - 90, cy), (cx, cy - 50), (cx + 90, cy), (cx, cy + 50)], outline=255)
                d.ellipse((cx - 20, cy - 20, cx + 4, cy + 4), outline=255, width=6)
                d.line([(cx - 20, cy + 22), (cx + 30, cy + 22)], fill=255, width=6)
    hgt = np.asarray(im.filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
    return c * emboss(hgt * 6, 1.0)[..., None] * (1 - hgt * 0.12)[..., None]


def stucco(n=256, col=STUCCO, seed=11):
    return fill(n, col, 4, seed) + N3(n, 6, seed + 1, 6) - np.clip(noise(n, 0.7, seed + 2) - 2.0, 0, 1)[..., None] * 40


def painted_wall(w=512, h=512, seed=13):
    """red stucco wall with a turquoise/ochre painted dado band and a black base stripe"""
    c = stucco(w, TEZ, seed)
    x, y = xy(w, h)
    c = np.where((y > 0.78)[..., None], stucco(w, INK, seed + 1), c)
    c = np.where(((y > 0.70) & (y < 0.78))[..., None], stucco(w, TURQ, seed + 2), c)
    c = np.where(((y > 0.67) & (y < 0.70))[..., None], stucco(w, OCHRE, seed + 3), c)
    return c


def turq_mosaic(n=256, seed=15, base=TURQ):
    """turquoise mosaic: small irregular tesserae"""
    idx, ed = voronoi(n, 160, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-1, 1, (160, 3)) * np.array([10, 26, 26])
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[idx] + N3(n, 0.8, seed + 1, 5)
    return c * (0.7 + 0.3 * np.clip(ed * 160, 0, 1))[..., None]


def pool_tile(n=256, seed=17):
    """pool floor: turquoise mosaic with darker lines"""
    c = turq_mosaic(n, seed, (54, 176, 188))
    x, y = xy(n)
    g = ((x * 2 % 1) < 0.02) | ((y * 2 % 1) < 0.02)
    return np.where(g[..., None], C((30, 110, 120)), c)


def pool_band(w=512, h=256, seed=19):
    """pool wall: stone with a jade step-fret band near the top (the water line)"""
    c = ashlar(w, h, seed, (180, 190, 176), 3, 4, 8, 0.75)
    f = fret_band(w, 64, seed + 1, (30, 120, 110), (230, 220, 190), (20, 50, 50))
    c[16:80] = f
    return c


def coping(n=256, seed=21):
    return ashlar(n, n, seed, (226, 214, 186), 1, 2, 6, 0.75)


def grass(n=512, seed=23):
    """jungle lawn: lush grass with clover patches and a few fallen leaves"""
    c = fill(n, (78, 128, 52), 10, seed) + N3(n, 0.5, seed + 1, 22) + N3(n, 10, seed + 2, 12)
    d = noise(n, 16, seed + 3)
    c = lerp(c, C((104, 150, 60)), np.clip(d * 0.5, 0, 1)[..., None])
    c = lerp(c, C((96, 80, 48)), np.clip(-d * 0.35 - 0.2, 0, 1)[..., None])
    im = img(c).convert('RGB'); dr = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 4)
    for _ in range(60):
        x, y, a = r.uniform(0, n), r.uniform(0, n), r.uniform(0, math.pi)
        col = [(150, 110, 40), (120, 90, 40), (170, 140, 50)][r.integers(3)]
        dx, dy = math.cos(a) * 7, math.sin(a) * 7
        dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=col); dr.line([(x - dx, y - dy), (x + dx, y + dy)], fill=col, width=3)
    return np.asarray(im, np.float32)


def bank(n=512, seed=25):
    """jungle bank: dark earth, roots, moss and ferns"""
    c = fill(n, (86, 66, 44), 10, seed) + N3(n, 0.6, seed + 1, 16)
    m = np.clip(noise(n, 9, seed + 2) * 0.6 + 0.25, 0, 1)
    c = lerp(c, C((66, 108, 46)) + N3(n, 0.5, seed + 3, 18), m[..., None])
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 4)
    for _ in range(18):
        x, y = r.uniform(0, n), r.uniform(0, n)
        pts = [(x, y)]
        for k in range(8):
            x += r.uniform(-24, 24); y += r.uniform(10, 34); pts.append((x, y))
        d.line(pts, fill=(60, 42, 28), width=int(r.uniform(3, 7)))
    return np.asarray(im, np.float32)


def sand(n=256, seed=27):
    return fill(n, (226, 206, 156), 6, seed) + N3(n, 0.4, seed + 1, 14) + N3(n, 6, seed + 2, 6)


def cave_rock(n=512, seed=29, base=(150, 140, 118)):
    """cenote limestone: layered, wet, mossy streaks"""
    x, y = xy(n)
    strata = np.sin((y + noise(n, 14, seed) * 0.05) * 2 * math.pi * 7) * 10
    c = np.zeros((n, n, 3), np.float32) + C(base) + strata[..., None] + N3(n, 1, seed + 1, 10) + N3(n, 6, seed + 2, 14)
    streak = np.clip(noise(n, 3, seed + 3) * 0.5 + np.asarray(img(noise(n, 1, seed + 4) * 40 + 128).resize((n // 16, n)).resize((n, n)), np.float32) / 255 - 0.75, 0, 1)
    c = lerp(c, C((70, 96, 56)), (streak * 0.8)[..., None])
    return c


def wood(n=256, seed=31, base=(128, 86, 54)):
    x, y = xy(n)
    nb = 4
    v = (y * nb) % 1.0
    tone = np.random.default_rng(seed).uniform(-14, 14, nb + 1)[np.floor(y * nb).astype(int) % (nb + 1)]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None]
    st = np.asarray(img(noise(n, 1, seed + 1) * 50 + 128).resize((n // 24, n)).resize((n, n)), np.float32) - 128
    c += st[..., None] * 0.3
    return np.where(((v < 0.04) | (v > 0.97))[..., None], C((60, 40, 26)), c)


def gold_floor(n=256, seed=33):
    c = turq_mosaic(n, seed, (210, 160, 60))
    x, y = xy(n)
    g = ((x * 4 % 1) < 0.03) | ((y * 4 % 1) < 0.03)
    return np.where(g[..., None], C((120, 80, 30)), c * 1.05)


def jumppad_tex(n=256):
    """sun-disc jump pad: gold rays on turquoise"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C((40, 170, 170))
    ray = rr < 0.33 + 0.14 * (np.abs(((a * 8 / (2 * math.pi)) % 1.0) - 0.5) * 2)
    c = np.where(ray[..., None], C((250, 200, 70)), c)
    c = np.where((rr < 0.22)[..., None], C((255, 236, 150)), c)
    c = np.where((np.abs(rr - 0.22) < 0.012)[..., None], C((150, 70, 30)), c)
    c = np.where((rr > 0.47)[..., None], C((150, 60, 40)), c)
    return c + N3(n, 1, 35, 4)


def water_tex(n=256, seed=37, col=(40, 150, 160)):
    c = fill(n, col, 6, seed)
    r = np.sin(noise(n, 10, seed + 1) * 3) * 16
    return c + r[..., None]


def waterfall_tex(w=128, h=256, seed=39):
    """falling-water streaks (alpha in the second return)"""
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.8, seed, h) * 60 + 128).resize((w, h // 16)).resize((w, h)), np.float32) / 255
    a = np.clip(0.35 + (st - 0.5) * 1.6 + noise(w, 2, seed + 1, h) * 0.1, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((210, 240, 245)) + (st * 40)[..., None]
    return c, a * 255


def caustic(n=256, seed=41):
    """additive caustics for the pool floors"""
    a = np.abs(noise(n, 5, seed)) + np.abs(noise(n, 5, seed + 1))
    v = np.clip(1.0 - a * 1.1, 0, 1) ** 3
    return np.zeros((n, n, 3), np.float32) + (v * 140)[..., None] * C((0.7, 1.0, 1.0))


SIGNS = {
    'sign_main': ("TLALOC'S LAGOON", 1024, 256, TEZ, (250, 226, 150)),
    'sign_cantina': ('CANTINA', 512, 128, (40, 120, 110), (255, 236, 180)),
    'sign_court': ('TLACHTLI', 512, 128, INK, GOLD),
    'sign_cenote': ('CENOTE', 512, 128, (40, 70, 60), (220, 240, 200)),
    'sign_jaguar': ('TEMPLE OF THE JAGUAR', 1024, 128, INK, OCHRE),
    'sign_treasure': ("MOCTEZUMA'S TREASURE", 1024, 128, (60, 30, 10), (255, 214, 100)),
    'sign_nodive': ('NO DIVING', 256, 128, (200, 40, 30), (255, 255, 255)),
}


def signboard(text, w, h, bg, fg):
    """carved and painted board with a fret border"""
    a = text_img(text, w, h, bg, fg, True, border=fg)
    return a + N3(w, 1, 43, 4, h)


# ------------------------------------------------------------------------------------------- sky
def sky_color(D):
    Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
    z = Dn[..., 2]
    az = np.degrees(np.arctan2(Dn[..., 1], Dn[..., 0]))
    up = np.clip(z, 0, 1)
    c = lerp(C((180, 214, 236)), C((56, 120, 210)), (up ** 0.6)[..., None])
    # sun glow (yaw SUN[0], elevation SUN[1])
    sy, se = math.radians(SUN[0]), math.radians(SUN[1])
    sd = np.array([math.cos(se) * math.cos(sy), math.cos(se) * math.sin(sy), math.sin(se)])
    cs = np.clip((Dn @ sd), -1, 1)
    c = c + (np.clip(cs, 0, 1) ** 40 * 120 + np.clip(cs, 0, 1) ** 600 * 400)[..., None] * C((1.0, 0.95, 0.8))
    # clouds: cumulus band above the horizon
    return c, z, az


def make_sky(n=512):
    d = out('env', NS); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}
    # horizon profile (elevation in degrees by azimuth): far blue mountains with two volcanoes, near jungle hills
    A = np.linspace(-180, 180, 2049)
    rng = np.random.default_rng(5)
    def ridge(seed, amp, rough):
        g = np.random.default_rng(seed)
        v = np.zeros_like(A)
        for k in range(1, 40):
            v += g.normal() * amp / k ** rough * np.sin(np.radians(A) * k + g.uniform(0, 6.28))
        return v
    far = 4.5 + ridge(7, 1.6, 1.2)
    for (ca, h, w) in ((70, 15.0, 13), (110, 11.0, 10)):            # Popocatepetl + Iztaccihuatl to the north
        far = np.maximum(far, h - np.abs(A - ca) / w * h * 0.9 + 0.3 * np.sin(A * 0.7))
    near = 3.0 + ridge(11, 1.1, 0.9) + np.abs(ridge(13, 0.5, 0.4))
    cl_noise = [noise(512, 10, 21 + k) for k in range(3)]
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        c, zz, az = sky_color(D)
        el = np.degrees(np.arcsin(np.clip(zz, -1, 1)))
        fa = np.interp(az, A, far); ne = np.interp(az, A, near)
        # clouds: puffy cumulus between 6 and 30 degrees, sparse above
        uu = (az + 180) / 360 * 4; vv = el / 40
        ci = (np.floor(uu * 512) % 512).astype(int); cj = (np.floor(np.clip(vv, 0, 0.999) * 511)).astype(int)
        cn = cl_noise[0][cj, ci] * 0.6 + cl_noise[1][(cj * 3) % 512, (ci * 3) % 512] * 0.4
        band = np.exp(-((el - 14) / 9) ** 2)
        cov = np.clip(cn * 0.9 + band * 0.9 - 0.75, 0, 1)
        shade = np.clip(1.15 - (el - 6) / 40, 0.75, 1.15)
        c = lerp(c, C((250, 250, 248)) * shade[..., None], (cov * (el > 1))[..., None])
        # mountains + smoke plume from the volcano
        plume = np.exp(-((az - 70 - (el - 15) * 0.8) / (2 + (el - 15) * 0.35).clip(1)) ** 2) * (el > 14.5) * np.clip(1 - (el - 15) / 22, 0, 1)
        c = lerp(c, C((220, 216, 210)), (plume * 0.7)[..., None])
        mtn = el < fa
        snow = (el > fa - 3.5) & (fa > 9)
        mc = lerp(C((108, 128, 160)), C((150, 166, 190)), np.clip((el / 15)[..., None], 0, 1))
        mc = np.where(snow[..., None], C((236, 240, 246)), mc)
        c = np.where(mtn[..., None], mc, c)
        jungle = el < ne
        jc = C((44, 82, 44)) + (noise(512, 1.5, 31)[cj, ci] * 14)[..., None]
        c = np.where(jungle[..., None], jc, c)
        c = np.where((el < 0)[..., None], C((36, 64, 36)), c)
        img(c).save(os.path.join(d, f'jungle_{k}.jpg'), quality=94)
    # cloud layer (scrolling, additive)
    cl = np.clip(noise(512, 14, 41) * 0.7 + noise(512, 4, 42) * 0.3 - 0.4, 0, 2)
    img(np.zeros((512, 512, 3)) + (cl * 120)[..., None]).save(os.path.join(d, 'jungle_clouds.jpg'), quality=92)
    W('skylight', fill(64, (170, 200, 230), 2, 45))


# ------------------------------------------------------------------------------------------- all brush textures
def make_textures():
    W('pavers', pavers()); W('red_path', red_path()); W('grass', grass()); W('bank', bank()); W('sand', sand())
    W('ashlar', ashlar()); W('ashlar_moss', ashlar(512, 512, 47, LIME_D, 5, 3, 14, 0.7, 0.8)); W('ashlar_red', ashlar(512, 512, 49, TEZ, 5, 3, 12, 0.7))
    W('fret', fret_band()); W('fret_jade', fret_band(512, 128, 51, (40, 110, 80), (236, 226, 200), INK)); W('glyph_wall', glyph_wall())
    W('stucco', stucco()); W('stucco_red', stucco(256, TEZ, 53)); W('stucco_turq', stucco(256, TURQ, 55)); W('painted_wall', painted_wall())
    W('turq_mosaic', turq_mosaic()); W('pool_tile', pool_tile()); W('pool_band', pool_band()); W('coping', coping())
    W('cave_rock', cave_rock()); W('wood', wood()); W('planks', wood(256, 57, (150, 104, 64))); W('gold_floor', gold_floor())
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (150, 60, 40), 3, 59)); W('water', water_tex()); W('water_deep', water_tex(256, 61, (24, 110, 130)))
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 63)); W('clip_ed', fill(64, (200, 120, 40), 2, 65)); W('caustic', caustic())
    W('obsidian', fill(128, (30, 28, 34), 4, 67) + N3(128, 0.5, 68, 10)); W('dark', fill(64, (20, 18, 16), 2, 69))
    wf, wa = waterfall_tex(); W('waterfall', wf, wa)
    for nm, (t, w, h, bg, fg) in SIGNS.items():
        W(nm, signboard(t, w, h, bg, fg))
    make_sky()


# ------------------------------------------------------------------------------------------- shader
STEPS = {'pavers': 'sandsteps', 'red_path': 'sandsteps', 'sand': 'sandsteps', 'grass': 'softsteps', 'bank': 'softsteps', 'planks': 'woodsteps',
         'wood': 'woodsteps', 'pool_tile': 'splashsteps'}
CAUSTIC_ON = {'pool_tile', 'pool_band', 'cave_rock'}


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
    s = '// ---- MD3 / IQM models (az_models.py)\n'
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
            s += '}\n\n'
        elif kind == 'vl':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n{two}'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform') and opt['deform'] != 'autosprite2': s += f'\tdeformVertexes {opt["deform"]}\n'
            elif opt.get('deform') == 'autosprite2': s += '\tdeformVertexes autosprite2\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'flow':                        # running water on slides / fountains (alpha streaks + additive sheen)
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen identity\n'
                  f'\t\ttcMod scroll 0 {opt.get("speed", -1.2)}\n\t}}\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.14 0.15 )\n\t\ttcMod scroll 0.05 {opt.get("speed", -1.2) * 1.4:g}\n\t}}\n}}\n\n')
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += (f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n')
        elif kind == 'flag':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nomarks\n\tcull none\n\tdeformVertexes wave 60 sin 0 4 0 1.2\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.12 0.14 0.15")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.2 0.2 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return s


def water_shader(name, img_):
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
		alphaGen const 0.62
		rgbGen identity
		tcMod turb 0 0.05 0 0.12
		tcMod scroll 0.01 0.02
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.2 0.22 0.22 )
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


def make_shader():
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padaztec/az_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'water', 'water_deep', 'waterfall', 'caustic', 'clip_ed'}
    for nm in sorted(SIZES):
        if nm in special: continue
        S_ += lm(nm, STEPS.get(nm), stage=CAUSTIC_STAGE if nm in CAUSTIC_ON else '')
    NS_ = '\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tq3map_nonplanar\n'
    pad_stage = f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 40\n\t}}\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.8 0.4\n\tq3map_lightSubdivide 128\n', stage=pad_stage)
    S_ += water_shader('water', 'water')
    S_ += water_shader('water_deep', 'water_deep')
    S_ += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 1 0.94 0.82 240 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 70 3
	skyparms env/{NS}/jungle 512 -
	{{
		map env/{NS}/jungle_clouds
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.35 0.35 )
		tcMod scale 3 3
		tcMod scroll 0.006 0.003
	}}
}}

{TD}/waterfall
{{
	qer_editorimage {TD}/waterfall.tga
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map {TD}/waterfall.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0 1.6
	}}
	{{
		map {TD}/waterfall.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.14 0.15 )
		tcMod scroll 0.03 2.3
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
