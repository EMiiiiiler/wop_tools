"""Procedural brush textures, night sky, shader + arena for wop_padhalloween (Pumpkin Hollow).
All art is original and generated here.

make_all(out, extra) writes textures/padhalloween/*, env/padhalloween/night_*, models/padhalloween/* (hw_models),
scripts/padhalloween.shader and scripts/wop_padhalloween.arena (pk3dir layout)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from hwlib import *
import hwlib

MAP = 'wop_padhalloween'
LONGNAME = 'Pumpkin Hollow'
SIZES = {}
ALPHA = set()


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


# ------------------------------------------------------------------------------------------- ground
def leaves_layer(im, n, seed, count, cols, size=(4, 10)):
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(count):
        x, y = r.uniform(0, n, 2); s = r.uniform(*size); a = r.uniform(0, math.pi)
        col = cols[r.integers(len(cols))]
        pts = []
        for k in range(10):
            t = k / 10 * 2 * math.pi
            rr = s * (1 + 0.35 * math.cos(5 * t)) * (0.6 if k % 2 else 1)
            pts.append((x + rr * math.cos(t + a) * 1.0, y + rr * math.sin(t + a) * 0.62))
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.polygon([(px + ox, py + oy) for (px, py) in pts], fill=tuple(int(c * r.uniform(0.75, 1.05)) for c in col))
    return im


LEAF_COLS = [(176, 72, 22), (200, 110, 30), (140, 40, 20), (190, 150, 40), (120, 60, 30), (90, 50, 28)]


def grass(n=512, seed=1):
    c = fill(n, (52, 62, 34), 9, seed)
    c += noise(n, 0.7, seed + 2)[..., None] * C((10, 14, 6))
    c += N3(n, 30, seed + 3, 9) * C((1.0, 0.9, 0.4))
    dry = np.clip(noise(n, 18, seed + 4) * 0.6, 0, 1)[..., None]
    c = lerp(c, c * C((1.25, 1.05, 0.7)), dry)
    im = img(c).convert('RGB')
    leaves_layer(im, n, seed + 5, 90, LEAF_COLS)
    return np.asarray(im, np.float32)


def leafbed(n=512, seed=11):
    c = fill(n, (70, 46, 26), 8, seed)
    im = img(c).convert('RGB')
    leaves_layer(im, n, seed + 1, 700, LEAF_COLS, (5, 13))
    a = np.asarray(im, np.float32)
    return a * (0.9 + 0.1 * noise(n, 4, seed + 2)[..., None])


def dirt(n=512, seed=21):
    c = fill(n, (96, 74, 52), 10, seed)
    c += N3(n, 0.8, seed + 1, 8)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 2)
    for _ in range(260):
        x, y = r.uniform(0, n, 2); s = r.uniform(1.5, 4.5); g = int(r.uniform(90, 150))
        d.ellipse((x - s, y - s * 0.8, x + s, y + s * 0.8), fill=(g, int(g * 0.92), int(g * 0.8)))
    leaves_layer(im, n, seed + 3, 25, LEAF_COLS)
    return np.asarray(im, np.float32)


def cobble(n=512, seed=31):
    idx, edge = voronoi(n, 70, seed)
    r = np.random.default_rng(seed + 1)
    tone = r.uniform(-18, 18, idx.max() + 1)[idx]
    c = np.zeros((n, n, 3), np.float32) + C((104, 100, 96)) + tone[..., None]
    c += N3(n, 1.5, seed + 2, 7)
    bevel = np.clip(edge * n / 7, 0, 1)
    c = c * (0.55 + 0.45 * bevel[..., None])
    moss = np.clip(noise(n, 10, seed + 3) - 0.6, 0, 1)[..., None] * (1 - bevel[..., None])
    c = lerp(c, C((54, 70, 34)), moss * 0.8)
    return c


def bank(n=512, seed=41):
    c = fill(n, (64, 50, 38), 10, seed)
    x, y = xy(n)
    strata = np.sin(y * 2 * math.pi * 6 + noise(n, 16, seed + 1) * 1.5)
    c += strata[..., None] * C((8, 6, 4))
    idx, edge = voronoi(n, 30, seed + 2)
    stone = (np.random.default_rng(seed + 3).random(idx.max() + 1) < 0.35)[idx] & (edge * n > 3)
    c = np.where(stone[..., None], C((96, 92, 86)) + N3(n, 2, seed + 4, 10), c)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 5)
    for _ in range(18):                         # roots
        x0, y0 = r.uniform(0, n, 2)
        pts = [(x0, y0)]
        for k in range(8):
            x0 += r.uniform(-14, 14); y0 += r.uniform(6, 20); pts.append((x0, y0))
        d.line(pts, fill=(40, 30, 22), width=int(r.uniform(2, 5)))
    return np.asarray(im, np.float32)


# ------------------------------------------------------------------------------------------- stone + brick
def stone_blocks(w=512, h=512, seed=51, base=(118, 116, 110), rows=8, cols=4):
    c = fill(w, base, 8, seed, h)
    r = np.random.default_rng(seed + 1)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    bh = h / rows
    for i in range(rows):
        off = (i % 2) * w / cols / 2
        for j in range(cols + 1):
            x0 = j * w / cols - off; t = r.uniform(-14, 14)
            d.rectangle((x0 + 2, i * bh + 2, x0 + w / cols - 2, (i + 1) * bh - 2),
                        fill=tuple(int(np.clip(v + t, 0, 255)) for v in base))
    a = np.asarray(im, np.float32) + N3(w, 1.4, seed + 2, 8, h) + N3(w, 6, seed + 3, 6, h)
    moss = np.clip(noise(w, 14, seed + 4, h) - 0.4, 0, 1)[..., None]
    a = lerp(a, C((58, 76, 40)), moss * 0.7)
    grime = np.clip(np.linspace(-0.3, 0.6, h), 0, 1)[:, None, None]
    return a * (1 - grime * 0.35)


def flagstone(n=512, seed=61):
    idx, edge = voronoi(n, 16, seed)
    tone = np.random.default_rng(seed + 1).uniform(-14, 14, idx.max() + 1)[idx]
    c = np.zeros((n, n, 3), np.float32) + C((92, 88, 82)) + tone[..., None] + N3(n, 1.3, seed + 2, 7)
    c *= (0.5 + 0.5 * np.clip(edge * n / 5, 0, 1))[..., None]
    return c


def brick(w=512, h=512, seed=71, base=(92, 48, 40)):
    c = fill(w, (54, 48, 44), 6, seed, h)
    r = np.random.default_rng(seed + 1)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    bh, bw = h / 16, w / 4
    for i in range(16):
        off = (i % 2) * bw / 2
        for j in range(5):
            t = r.uniform(-22, 18)
            x0 = j * bw - off
            d.rectangle((x0 + 3, i * bh + 3, x0 + bw - 3, (i + 1) * bh - 3), fill=tuple(int(np.clip(v + t, 0, 255)) for v in base))
    a = np.asarray(im, np.float32) + N3(w, 1.2, seed + 2, 9, h)
    damp = np.clip(noise(w, 20, seed + 3, h), 0, 1.5)[..., None]
    return a * (1 - damp * 0.25)


# ------------------------------------------------------------------------------------------- manor interior + wood
def wallpaper(w=256, h=256, seed=81, bg=(72, 40, 78), fg=(110, 70, 112)):
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C(bg)
    # damask: mirrored teardrop medallions on a diamond lattice
    u = (x * 2) % 1.0; v = (y * 2) % 1.0
    u2 = np.abs(u - 0.5) * 2
    med = np.clip(1 - ((u2 / 0.42) ** 2 + ((v - 0.5) / 0.38) ** 2), 0, 1)
    petals = 0.5 + 0.5 * np.cos(np.arctan2(v - 0.5, u2 + 1e-3) * 6)
    m = (med > 0.05) & (petals * med > 0.08)
    stripe = (np.abs(((x * 8) % 1.0) - 0.5) < 0.02)
    c = np.where(m[..., None], C(fg), c)
    c = np.where(stripe[..., None], C(fg) * 0.9, c)
    c += N3(w, 1.0, seed, 5, h)
    stain = np.clip(noise(w, 24, seed + 1, h) - 0.5, 0, 1)[..., None]
    c = lerp(c, C((70, 62, 40)), stain * 0.6)
    peel = np.clip(noise(w, 6, seed + 2, h) - 1.6, 0, 1)[..., None]
    return lerp(c, C((180, 170, 150)), peel)


def boards(w=256, h=256, seed=91, base=(70, 50, 36), nb=8, vertical=False, gap=(30, 22, 16)):
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32)
    coord = x if vertical else y
    b = np.floor(coord * nb).astype(int)
    tone = r.uniform(-16, 16, nb + 1)[b]
    grain = noise(w, 1.0, seed + 1, h)
    gr = np.asarray(img(grain * 40 + 128).resize((w // 12, h) if not vertical else (w, h // 12)).resize((w, h)), np.float32) - 128
    c = c + C(base) + tone[..., None] + gr[..., None] * 0.45
    f = (coord * nb) % 1.0
    c = np.where(((f < 0.03) | (f > 0.97))[..., None], C(gap), c)
    # board ends
    for k in range(nb):
        cut = r.uniform(0, 1)
        sel = (b == k) & (np.abs((x if not vertical else y) - cut) < 0.004)
        c[sel] = C(gap)
    return c


def plaster(n=256, seed=101, col=(126, 128, 104)):
    c = fill(n, col, 7, seed) + N3(n, 3, seed + 2, 6)
    crack = np.abs(noise(n, 5, seed + 3)) < 0.03
    c[crack] *= 0.6
    return c


def ceiling(n=256, seed=111):
    c = fill(n, (150, 144, 132), 6, seed)
    crack = np.abs(noise(n, 7, seed + 1)) < 0.025
    c[crack] *= 0.55
    stain = np.clip(noise(n, 20, seed + 2) - 0.6, 0, 1)[..., None]
    return lerp(c, C((100, 86, 60)), stain)


def carpet(n=256, seed=121):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((110, 24, 28))
    bord = (np.abs(x - 0.5) > 0.40) & (np.abs(x - 0.5) < 0.44)
    c = np.where(bord[..., None], C((170, 130, 50)), c)
    diam = (np.abs(((x * 4) % 1) - 0.5) + np.abs(((y * 4) % 1) - 0.5)) < 0.18
    c = np.where((diam & (np.abs(x - 0.5) < 0.38))[..., None], C((70, 16, 20)), c)
    return c + N3(n, 0.8, seed, 8)


def tin(n=256, seed=131):
    x, y = xy(n)
    c = fill(n, (62, 64, 66), 6, seed)
    seam = (np.abs(((x * 4) % 1) - 0.5) > 0.47)
    c = np.where(seam[..., None], C((40, 42, 44)), c)
    rust = np.clip(noise(n, 9, seed + 1) - 0.7, 0, 1)[..., None]
    return lerp(c, C((96, 56, 30)), rust)


def hay(n=256, seed=141):
    c = fill(n, (176, 146, 70), 10, seed)
    r = np.random.default_rng(seed + 1)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = r.uniform(0, n, 2); a = r.uniform(-0.6, 0.6) + (math.pi / 2 if r.random() < 0.3 else 0); L = r.uniform(8, 26)
        g = int(r.uniform(140, 230))
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(g, int(g * 0.82), int(g * 0.4)), width=1)
    return np.asarray(im, np.float32)


def jumppad_tex(n=256):
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; a = np.arctan2(dy, dx)
    sw = np.sin(a * 3 + r * 14)
    c = np.where((sw > 0)[..., None], C((250, 130, 20)), C((90, 30, 120)))
    c = np.where((r > 0.9)[..., None], C((30, 16, 30)), c)
    c = np.where((r < 0.18)[..., None], C((250, 220, 90)), c)
    return c


def brew_tex(n=256, seed=151):
    c = np.zeros((n, n, 3), np.float32) + C((50, 170, 40))
    bub = np.clip(noise(n, 3, seed) - 0.9, 0, 1)
    c += bub[..., None] * C((140, 200, 90))
    c += N3(n, 10, seed + 1, 22) * C((0.4, 1, 0.3))
    return c


def broken_glass(n=256, seed=161):
    """dirty window with a hole smashed in it (alpha)"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((70, 84, 80)) + N3(n, 8, seed, 10)
    a = np.full((n, n), 46.0) + noise(n, 6, seed + 1) * 16
    r = np.random.default_rng(seed + 2)
    cx, cy = r.uniform(0.35, 0.65, 2)
    ang = np.arctan2(y - cy, x - cx); rad = np.hypot(x - cx, y - cy)
    jag = 0.22 + 0.08 * np.sin(ang * 7 + 1.3) + 0.05 * np.sin(ang * 13)
    a = np.where(rad < jag, 0, a)
    cracks = (np.abs(np.sin(ang * 9)) < 0.03) & (rad < jag + 0.25)
    a = np.where(cracks, 160, a)
    edge = (x < 0.03) | (x > 0.97) | (y < 0.03) | (y > 0.97)
    a = np.where(edge, 0, a)
    return c, np.clip(a, 0, 255)


def lair_wall(n=512, seed=171):
    a = stone_blocks(n, n, seed, (64, 58, 70), 8, 3)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 1)
    for i in range(10):
        x, y = r.uniform(30, n - 30, 2)
        for k in range(3):
            pts = [(x + r.uniform(-14, 14), y + r.uniform(-14, 14)) for _ in range(3)]
            d.line(pts, fill=(60, 220, 120), width=2)
    return np.asarray(im, np.float32)


def rune_circle(n=512):
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32)
    ring = (np.abs(r - 0.92) < 0.015) | (np.abs(r - 0.78) < 0.01) | (np.abs(r - 0.3) < 0.012)
    ticks = (r > 0.8) & (r < 0.9) & (np.abs(np.sin(a * 12)) < 0.08)
    star = np.zeros_like(r, dtype=bool)
    for k in range(7):                                  # a seven-point star of straight chords
        a0 = 2 * math.pi * k / 7; a1 = 2 * math.pi * ((k + 3) % 7) / 7
        p0 = np.array([math.cos(a0), math.sin(a0)]) * 0.78; p1 = np.array([math.cos(a1), math.sin(a1)]) * 0.78
        dvec = p1 - p0; L = np.linalg.norm(dvec); dvec /= L
        px, py = dx * 2 - p0[0], dy * 2 - p0[1]
        t = np.clip(px * dvec[0] + py * dvec[1], 0, L)
        star |= np.hypot(px - t * dvec[0], py - t * dvec[1]) < 0.01
    m = ring | ticks | star
    c[m] = C((90, 255, 150))
    return np.asarray(img(c).filter(ImageFilter.GaussianBlur(1.2)), np.float32) * 1.6


def portrait(kind, w=256, h=320, seed=181):
    """haunted portrait: dark oil background, a sitter in silhouette whose eyes glow, gilt frame painted on"""
    x, y = xy(w, h)
    bg = lerp(C((40, 30, 24)), C((90, 70, 44)), np.clip(1 - np.hypot(x - 0.5, y - 0.35) * 1.6, 0, 1)[..., None])
    c = bg + N3(w, 3, seed, 6, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    body = {'lady': (60, 40, 60), 'man': (30, 30, 36), 'cat': (20, 20, 22)}[kind]
    if kind == 'cat':
        d.ellipse((w * 0.25, h * 0.45, w * 0.75, h * 0.95), fill=body)
        d.ellipse((w * 0.33, h * 0.25, w * 0.67, h * 0.55), fill=body)
        d.polygon([(w * 0.34, h * 0.33), (w * 0.38, h * 0.16), (w * 0.47, h * 0.28)], fill=body)
        d.polygon([(w * 0.66, h * 0.33), (w * 0.62, h * 0.16), (w * 0.53, h * 0.28)], fill=body)
        ey = h * 0.38; ex = (w * 0.43, w * 0.57); er = w * 0.035
    else:
        d.ellipse((w * 0.18, h * 0.55, w * 0.82, h * 1.2), fill=body)
        d.ellipse((w * 0.36, h * 0.22, w * 0.64, h * 0.56), fill=(200, 186, 160) if kind == 'lady' else (180, 170, 150))
        if kind == 'lady':
            d.ellipse((w * 0.30, h * 0.12, w * 0.70, h * 0.40), fill=(60, 30, 20))
        else:
            d.rectangle((w * 0.34, h * 0.12, w * 0.66, h * 0.26), fill=(20, 20, 22)); d.rectangle((w * 0.28, h * 0.24, w * 0.72, h * 0.27), fill=(20, 20, 22))
        ey = h * 0.38; ex = (w * 0.45, w * 0.55); er = w * 0.022
    for e in ex:
        d.ellipse((e - er, ey - er, e + er, ey + er), fill=(255, 60, 30) if kind != 'cat' else (180, 255, 60))
    a = np.asarray(im, np.float32)
    f = 14
    frame = (x * w < f) | (x * w > w - f) | (y * h < f) | (y * h > h - f)
    a = np.where(frame[..., None], C((170, 130, 50)) * (0.7 + 0.3 * np.sin(x * 60 + y * 40))[..., None], a)
    return a


def sign_board(text, w, h, bg, fg, serif=True, border=None, glow=None):
    a = text_img(text, w, h, bg, fg, serif, border=border, glow=glow)
    grain = boards(w, h, 7, (0, 0, 0), 4)[..., 0] if False else noise(w, 1.0, len(text), h)
    return a + grain[..., None] * 6


def bulb(n=32, col=(255, 170, 60)):
    x, y = xy(n)
    r = np.hypot(x - 0.5, y - 0.5) * 2
    return C(col) * np.clip(1.2 - r, 0.3, 1)[..., None]


def flame(w=64, h=128, seed=191):
    x, y = xy(w, h)
    u = (x - 0.5) * 2; v = 1 - y
    shape = np.clip(1 - (np.abs(u) / (0.9 * (1 - v) ** 0.6 * np.clip(v * 4, 0, 1) + 1e-3)) ** 2, 0, 1)
    shape *= np.clip(1.2 - v, 0, 1)
    c = lerp(C((255, 120, 20)), C((255, 240, 160)), np.clip(shape * 1.3 - 0.3, 0, 1)[..., None]) * shape[..., None]
    return c


def mist(n=256, seed=201):
    c = np.zeros((n, n, 3), np.float32) + C((150, 160, 180))
    return c + N3(n, 10, seed, 20)


# ------------------------------------------------------------------------------------------- the night sky (custom cube)
MOON_DIR = (96.0, 22.0)          # yaw, elevation of the harvest moon (q3map_sun uses the same direction)


def hills_h(az):
    h = (0.05 + 0.025 * np.sin(az * 2 + 0.4) + 0.012 * np.sin(az * 5 + 2.0) + 0.006 * np.sin(az * 13 + 0.5)
         + 0.003 * np.sin(az * 37))
    return np.clip(h, 0.012, 0.11)


def sky_color(d):
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    z = d[..., 2]; az = np.arctan2(d[..., 1], d[..., 0])
    el = np.arcsin(np.clip(z, -1, 1))
    t = np.clip(el / (math.pi / 2), 0, 1)
    hor = C((66, 40, 72)); zen = C((8, 8, 26))
    c = lerp(hor, zen, (t ** 0.5)[..., None])
    yaw, pit = math.radians(MOON_DIR[0]), math.radians(MOON_DIR[1])
    mdv = np.array([math.cos(pit) * math.cos(yaw), math.cos(pit) * math.sin(yaw), math.sin(pit)])
    ang = np.arccos(np.clip(d @ mdv, -1, 1))
    halo = np.exp(-(ang / 0.35) ** 2) * 0.5 + np.exp(-(ang / 0.10) ** 2) * 0.7
    c = c + halo[..., None] * C((110, 70, 40))
    disc = ang < 0.085
    # moon surface: maria from low-frequency waves in a moon-local frame
    e1 = np.cross(mdv, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(e1, mdv)
    mu = (d @ e1) / 0.085; mv = (d @ e2) / 0.085
    mar = 0.5 + 0.5 * np.sin(mu * 3.1 + 0.7) * np.sin(mv * 2.7 - 0.4) + 0.25 * np.sin(mu * 7 + mv * 5)
    limb = np.clip(1 - (mu ** 2 + mv ** 2), 0, 1) ** 0.25
    moon = lerp(C((250, 196, 110)), C((214, 140, 70)), np.clip(mar, 0, 1)[..., None]) * (0.7 + 0.3 * limb)[..., None]
    c = np.where(disc[..., None], moon, c)
    # flying witch silhouette across the lower moon (broom + body + hat), in moon-local coordinates
    wx, wy = mu + 0.15, mv + 0.15
    broom = (np.abs(wy - 0.06 * wx) < 0.035) & (wx > -0.75) & (wx < 0.62)
    bristle = (wx > 0.5) & (wx < 0.85) & (np.abs(wy - 0.04) < (wx - 0.5) * 0.45 + 0.03)
    body = ((wx + 0.05) ** 2 / 0.03 + (wy - 0.16) ** 2 / 0.02) < 1
    head = ((wx + 0.12) ** 2 + (wy - 0.36) ** 2) < 0.006
    hat = (wy > 0.38) & (wy < 0.62) & (np.abs(wx + 0.13 - (wy - 0.38) * 0.35) < (0.62 - wy) * 0.4)
    brim = (np.abs(wy - 0.40) < 0.02) & (np.abs(wx + 0.12) < 0.16)
    cape = (wx > -0.05) & (wx < 0.35) & (wy > 0.05) & (wy < 0.3 - (wx + 0.05) * 0.5)
    sil = (broom | bristle | body | head | hat | brim | cape) & (ang < 0.12)
    c = np.where(sil[..., None], C((16, 10, 14)), c)
    # clouds: soft purple bands, lit from the moon
    cl = np.clip(0.55 + 0.5 * np.sin(az * 3 + el * 9 + np.sin(az * 7) * 0.8) * np.sin(el * 14 - az * 2), 0, 1)
    band = np.exp(-((el - 0.30) / 0.10) ** 2) + 0.6 * np.exp(-((el - 0.12) / 0.05) ** 2)
    cloud = cl * band * (z > 0)
    c = lerp(c, C((70, 50, 80)) + halo[..., None] * C((90, 60, 40)), np.clip(cloud * 0.6, 0, 0.75)[..., None])
    # hills: dark rolling silhouette with dead trees and a far church spire, faint rim light
    hh = hills_h(az)
    trees = np.zeros_like(az)
    for k in range(70):
        a0 = (k * 2.399) % (2 * math.pi) - math.pi
        w = 0.004 + 0.003 * ((k * 7) % 5) / 5
        ht = 0.03 + 0.03 * ((k * 13) % 7) / 7
        da = np.angle(np.exp(1j * (az - a0)))
        trees = np.maximum(trees, np.where(np.abs(da) < w, ht * (1 - np.abs(da) / w * 0.3), 0))
        for b in (-1, 1):                               # two crooked branches each
            trees = np.maximum(trees, np.where(np.abs(da - b * (el - hh - ht * 0.5) * 0.6) < w * 0.35, np.minimum(ht * 0.9, (el - hh) + 0.002), 0))
    ch_a = math.radians(-40)
    da = np.angle(np.exp(1j * (az - ch_a)))
    church = np.where(np.abs(da) < 0.025, 0.05, 0) + np.where(np.abs(da + 0.012) < 0.006, 0.05 + (0.006 - np.abs(da + 0.012)) * 9, 0)
    top = hh + np.maximum(trees, church)
    below = el < top
    rim = np.exp(-((el - top) / 0.004) ** 2) * (~below)
    c = c + rim[..., None] * C((60, 40, 50))
    c = np.where(below[..., None], C((10, 8, 14)), c)
    return np.clip(c, 0, 255), below


def make_sky(n=512):
    d = out('env', NS); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t),
             'up': (-t, -s, one), 'dn': (t, -s, -one)}
    rng = np.random.default_rng(3)
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        c, below = sky_color(D)
        st = rng.random((n, n))
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        above = (~below) & (Dn[..., 2] > 0.06)
        c = np.where(((st > 0.9975) & above)[..., None], C((250, 248, 235)), c)
        c = np.where(((st > 0.993) & (st <= 0.9975) & above)[..., None], c + C((50, 46, 60)), c)
        img(c).save(os.path.join(d, f'night_{k}.jpg'), quality=94)
    cl = np.clip(noise(512, 20, 7) * 0.7 + noise(512, 6, 8) * 0.3 - 0.5, 0, 2)
    img(np.clip(cl[..., None] * C((44, 30, 50)), 0, 255)).save(os.path.join(d, 'night_clouds.jpg'), quality=92)
    W('skylight', np.zeros((64, 64, 3)) + C((70, 80, 130)))


# ------------------------------------------------------------------------------------------- all textures
SIGNS = {
    'sign_hollow': ('PUMPKIN HOLLOW', 1024, 192, (34, 22, 30), (250, 150, 40), True, (250, 150, 40)),
    'sign_manor': ('BLACKWOOD MANOR\nest. 1666', 512, 192, (30, 26, 30), (220, 200, 160), True, None),
    'sign_maze': ('CORN MAZE\nenter if you dare', 512, 256, (120, 80, 40), (30, 16, 10), True, None),
    'sign_pumpkins': ('PUMPKINS\n5 CENTS', 512, 256, (230, 220, 190), (190, 70, 20), False, None),
    'sign_witch': ('NO TRESPASSING\nwitch within', 512, 256, (60, 70, 40), (230, 230, 200), True, None),
    'sign_lair': ("THE WITCH'S LAIR\nwipe your feet", 512, 256, (30, 16, 40), (120, 255, 160), True, (60, 200, 100)),
    'sign_crypt': ('REST IN PEACE', 512, 128, (100, 98, 92), (40, 38, 36), True, None),
    'sign_graveyard': ('HOLLOW CEMETERY', 1024, 128, (24, 24, 26), (200, 200, 190), True, None),
}


def make_textures():
    W('grass', grass()); W('leafbed', leafbed()); W('dirt', dirt()); W('cobble', cobble()); W('bank', bank())
    W('stone', stone_blocks()); W('stone_dark', stone_blocks(512, 512, 55, (84, 82, 80))); W('flagstone', flagstone())
    W('brick', brick()); W('wallpaper', wallpaper()); W('wallpaper_g', wallpaper(256, 256, 83, (40, 60, 50), (70, 96, 76)))
    W('floor_wood', boards(256, 256, 91, (66, 44, 30), 8)); W('porch_wood', boards(256, 256, 93, (96, 92, 84), 8, False, (30, 30, 30)))
    W('planks', boards(256, 256, 95, (104, 76, 48), 6)); W('planks_v', boards(256, 256, 97, (90, 66, 44), 5, True))
    W('wood_dark', boards(128, 128, 99, (54, 38, 28), 3)); W('ceiling', ceiling()); W('carpet', carpet()); W('tin', tin())
    W('plaster', plaster()); W('hay', hay()); W('iron', fill(64, (36, 36, 40), 4, 57)); W('jumppad', jumppad_tex())
    W('rubber', fill(64, (80, 30, 110), 3, 59)); W('brew', brew_tex()); W('brew_ed', fill(64, (60, 180, 50), 3, 61))
    c, a = broken_glass(); W('glass_broken', c, a)
    W('lair_wall', lair_wall()); W('lair_floor', stone_blocks(512, 512, 175, (52, 48, 60), 6, 6)); W('runes', rune_circle())
    for k in ('lady', 'man', 'cat'): W('portrait_' + k, portrait(k, seed=len(k)))
    for nm, (t, w, h, bg, fg, serif, glow) in SIGNS.items():
        W(nm, sign_board(t, w, h, bg, fg, serif, border=fg, glow=glow))
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 73))
    W('bulb_o', bulb(col=(255, 150, 50))); W('bulb_g', bulb(col=(120, 255, 120))); W('bulb_p', bulb(col=(200, 120, 255)))
    W('mist', mist())
    fl = flame(); W('flame', fl)
    W('earth_dark', fill(128, (40, 32, 26), 6, 63))


# ------------------------------------------------------------------------------------------- shader
STEPS = {'grass': 'softsteps', 'leafbed': 'softsteps', 'dirt': 'softsteps', 'bank': 'softsteps', 'floor_wood': 'woodsteps',
         'porch_wood': 'woodsteps', 'planks': 'woodsteps', 'planks_v': 'woodsteps', 'wood_dark': 'woodsteps', 'carpet': 'carpetsteps',
         'hay': 'softsteps', 'tin': 'latticesteps', 'earth_dark': 'softsteps'}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


def glow(name, light, rgb, wave='identity', extra=''):
    return (f'{TD}/{name}\n{{\n\tqer_editorimage {TD}/{name}\n\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n\tq3map_lightSubdivide 256\n'
            f'\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {TD}/{name}\n\t\trgbGen {wave}\n\t}}\n}}\n\n')


def model_shaders():
    s = '// ---- MD3 / IQM models (hw_models.py)\n'
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
            s += '}\n\n'
        elif kind == 'vl':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'alpha':                       # alpha-tested cut-outs (corn, leaves, cobwebs, fringes), vertex lit
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'web':                         # translucent cobwebs
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen const ( 0.7 0.7 0.75 )\n\t}}\n}}\n\n')
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n{two}'
            if opt.get('light'): s += f'\tq3map_surfacelight {opt["light"]}\n\tq3map_lightRGB {opt.get("rgb", "1 1 1")}\n\tq3map_lightSubdivide 256\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'flicker':                     # carved-pumpkin faces / lantern glass: glowing, flickering
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave noise 0.8 0.25 {opt.get("ph", 0)} 6\n\t}}\n}}\n\n')
        elif kind == 'add':                         # additive glow sprites (flames, wisps, beams)
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform') and opt['deform'] != 'autosprite2': s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'ghost':                       # translucent ghost (mover), pulsing
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\tdeformVertexes wave 30 sin 0 3 0 0.4\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.55 0.15 0 0.3\n\t}}\n}}\n\n')
        elif kind == 'dyn':                         # movers: lit by the light grid
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n'
                  f'\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n')
        elif kind == 'batwing':                     # bat wings (mover): alpha cut-out, flapping
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tcull none\n'
                  f'\tdeformVertexes wave 12 sin 0 7 0 3.2\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.12 0.14 0.13")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.18 0.18 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return s


def make_shader():
    S = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padhalloween/hw_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'brew', 'brew_ed', 'glass_broken', 'runes', 'mist', 'flame', 'sign_hollow', 'sign_lair'} | \
              {n for n in SIZES if n.startswith('bulb_')}
    for nm in sorted(SIZES):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm))
    NS_ = '\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tq3map_nonplanar\n'
    S += lm('dirt_ns', extra=NS_, tex=f'{TD}/dirt').replace(f'{TD}/dirt_ns\n', f'{TD}/dirt_ns\n', 1)
    S += lm('carpet_ns', extra=NS_, tex=f'{TD}/carpet')
    S += lm('jumppad_ns', extra=NS_ + '\tq3map_surfacelight 80\n\tq3map_lightRGB 1 0.55 0.15\n\tq3map_lightSubdivide 128\n', tex=f'{TD}/jumppad', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 70\n\t}}\n'))
    S += lm('jumppad', extra='\tq3map_surfacelight 80\n\tq3map_lightRGB 1 0.55 0.15\n\tq3map_lightSubdivide 128\n', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 70\n\t}}\n'))
    for nm, rgb in (('sign_hollow', '1 0.6 0.2'), ('sign_lair', '0.4 1 0.6')):
        S += lm(nm, extra=f'\tq3map_surfacelight 50\n\tq3map_lightRGB {rgb}\n', stage=(
            f'\t{{\n\t\tmap {TD}/{nm}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.18 0.08 0 0.4\n\t}}\n'))
    S += (f'{TD}/runes\n{{\n\tqer_editorimage {TD}/runes\n\tq3map_surfacelight 120\n\tq3map_lightRGB 0.4 1 0.6\n'
          f'\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n'
          f'\t{{\n\t\tmap {TD}/runes\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.75 0.25 0 0.3\n\t\ttcMod rotate 6\n\t}}\n}}\n\n')
    for nm in sorted(n for n in SIZES if n.startswith('bulb_')):
        rgb = {'bulb_o': '1 0.6 0.2', 'bulb_g': '0.45 1 0.45', 'bulb_p': '0.8 0.5 1'}[nm]
        S += glow(nm, 600, rgb, extra='\tsurfaceparm nonsolid\n\tsurfaceparm trans\n')
    S += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 0.75 0.78 1 115 {MOON_DIR[0]:g} {MOON_DIR[1] + 18:g}
	q3map_skylight 55 3
	skyparms env/{NS}/night 512 -
	{{
		map env/{NS}/night_clouds
		blendFunc GL_ONE GL_ONE
		rgbGen identity
		tcMod scale 2 2
		tcMod scroll 0.006 0.002
	}}
}}

{TD}/brew
{{
	qer_editorimage {TD}/brew_ed
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	deformVertexes wave 64 sin 0 3 0 0.6
	cull none
	{{
		map {TD}/brew
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.85
		rgbGen identity
		tcMod turb 0 0.06 0 0.15
		tcMod scroll 0.02 0.03
	}}
	{{
		map {TD}/brew
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.3 0.15 0 0.5
		tcMod scale 1.7 1.7
		tcMod scroll -0.03 0.02
	}}
}}

{TD}/brew_nodraw
{{
	qer_editorimage {TD}/brew_ed
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

{TD}/glass_broken
{{
	qer_editorimage {TD}/glass_broken.tga
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm alphashadow
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{{
		map {TD}/glass_broken.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
	}}
}}

{TD}/mist
{{
	qer_editorimage {TD}/mist
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm fog
	surfaceparm nolightmap
	q3map_fogDir ( 0 0 -1 )
	fogparms ( 0.42 0.45 0.55 ) 520
}}

{TD}/flame
{{
	qer_editorimage {TD}/flame
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map {TD}/flame
		blendFunc GL_ONE GL_ONE
		rgbGen wave noise 0.85 0.25 0 7
	}}
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
    S += model_shaders()
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(out('scripts'), exist_ok=True)
    open(out('scripts', NS + '.shader'), 'w').write(S)


def make_arena():
    open(out('scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(o, extra_models=None):
    hwlib.STATE['out'] = o
    make_textures(); make_sky()
    import hw_models
    hw_models.make()
    if extra_models: extra_models()
    make_shader(); make_arena()


if __name__ == '__main__':
    make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(SIZES), 'textures')
