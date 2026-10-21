"""Procedural brush textures, shader + arena for wop_padbbq (Backyard BBQ). All art is original and
generated here.

make_all(out, extra) writes textures/padbbq/*, models/padbbq/* (bb_models), scripts/padbbq.shader
and scripts/wop_padbbq.arena (pk3dir layout). The sky is WoP's own sunny garden box (env/fort-pad512)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bblib import *
import bblib

MAP = 'wop_padbbq'
LONGNAME = 'Backyard BBQ'
SIZES = {}
ALPHA = set()
SUN = (100.0, 52.0)                    # yaw (90 = north: the user plays in New Zealand, the sun is in the north), elevation


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


# ------------------------------------------------------------------------------------------- wood + floors
def boards(w=512, h=512, seed=1, base=(196, 150, 100), nb=8, vertical=False, gap=(80, 56, 36), grain=1.0, ends=True):
    """floorboards along x (rows in y) with grain, per-board tone, staggered butt joints"""
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    if vertical: x, y = y, x
    row = np.floor(y * nb).astype(int)
    tone = r.uniform(-16, 16, nb + 1)[row % (nb + 1)]
    c = np.zeros((h, w, 3), np.float32) + C(base) + tone[..., None]
    g = noise(w, 1, seed + 1, h)
    streak = np.asarray(img(g * 50 + 128).resize(((w // 24) if not vertical else w, h if not vertical else (h // 24))).resize((w, h)), np.float32) - 128
    c += streak[..., None] * 0.35 * grain
    rings = np.sin((y * nb % 1.0) * 18 + noise(w, 18, seed + 2, h) * 3) * 6 * grain
    c += rings[..., None]
    v = (y * nb) % 1.0
    c = np.where(((v < 0.035) | (v > 0.975))[..., None], C(gap), c)
    if ends:
        off = r.uniform(0, 1, nb + 1)[row % (nb + 1)]
        u = (x + off) % 0.5
        c = np.where((u < 0.006)[..., None], C(gap), c)
    return c + N3(w, 1, seed + 3, 3, h)


def herringbone(n=256, seed=5, a=(150, 100, 60), b=(176, 124, 76)):
    x, y = xy(n)
    k = 8
    u = x * k; v = y * k
    blk = (np.floor(u) + np.floor(v)) % 2
    fu = (u % 1.0); fv = (v % 1.0)
    stripe = np.where(blk == 0, (fu * 3) % 1.0, (fv * 3) % 1.0)
    c = np.where((blk == 0)[..., None], C(a), C(b)) + noise(n, 1, seed)[..., None] * 6
    c = np.where((stripe < 0.07)[..., None], C((70, 46, 30)), c)
    c = np.where(((fu < 0.02) | (fv < 0.02))[..., None], C((70, 46, 30)), c)
    return c


def checker(n=256, a=(240, 238, 230), b=(40, 42, 50), k=4, seed=7):
    x, y = xy(n)
    m = ((np.floor(x * k) + np.floor(y * k)) % 2)[..., None]
    c = np.where(m > 0, C(b), C(a)) + N3(n, 2, seed, 4)
    g = ((x * k % 1) < 0.02) | ((y * k % 1) < 0.02)
    return np.where(g[..., None], C((150, 150, 150)), c)


def tiles(n=256, col=(120, 200, 200), k=4, seed=9, grout=(235, 240, 240)):
    x, y = xy(n)
    r = np.random.default_rng(seed)
    t = r.uniform(-10, 10, (k, k))[np.floor(y * k).astype(int) % k, np.floor(x * k).astype(int) % k]
    c = np.zeros((n, n, 3), np.float32) + C(col) + t[..., None]
    sh = np.clip(1 - np.hypot((x * k % 1) - 0.35, (y * k % 1) - 0.35) * 1.2, 0, 1) * 25
    c += sh[..., None]
    g = ((x * k % 1) < 0.035) | ((y * k % 1) < 0.035)
    return np.where(g[..., None], C(grout), c)


def carpet(n=256, seed=11, col=(170, 50, 70), border=None):
    c = fill(n, col, 6, seed) + N3(n, 0.6, seed + 1, 8)
    x, y = xy(n)
    roses = (np.sin(x * math.pi * 8) * np.sin(y * math.pi * 8)) > 0.75
    return np.where(roses[..., None], c * 0.8 + C((60, 10, 20)) * 0.2, c)


# ------------------------------------------------------------------------------------------- wallpapers
def stripes(w=256, h=256, a=(244, 200, 210), b=(252, 236, 240), k=8, seed=13, sprig=None):
    x, y = xy(w, h)
    m = ((x * k) % 1.0) < 0.5
    c = np.where(m[..., None], C(a), C(b)) + N3(w, 1, seed, 3, h)
    if sprig is not None:
        im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
        r = np.random.default_rng(seed)
        for i in range(k):
            cx = int((i + 0.75) * w / k)
            for j in range(4):
                cy = int((j + 0.25 + 0.5 * (i % 2)) * h / 4) % h
                for (dx, dy) in ((0, -5), (4, 0), (0, 5), (-4, 0)):
                    d.ellipse((cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3), fill=sprig)
                d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(250, 220, 90))
                d.line([(cx, cy + 6), (cx + 3, cy + 14)], fill=(110, 160, 100), width=2)
        c = np.asarray(im, np.float32)
    return c


def damask(n=256, bg=(150, 176, 140), fg=(176, 200, 164), seed=15):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    for (cx, cy) in ((n // 2, n // 2), (0, 0), (n, 0), (0, n), (n, n)):
        for s in (1, -1):
            d.ellipse((cx - 40, cy - 70, cx + 40, cy + 70), outline=tuple(fg), width=6)
            d.ellipse((cx - 16, cy - 30, cx + 16, cy + 30), fill=tuple(fg))
            d.polygon([(cx, cy - 96), (cx + 14 * s, cy - 76), (cx, cy - 60)], fill=tuple(fg))
            d.polygon([(cx, cy + 96), (cx + 14 * s, cy + 76), (cx, cy + 60)], fill=tuple(fg))
            d.arc((cx - 70, cy - 20, cx + 70, cy + 120), 200, 340, fill=tuple(fg), width=5)
    for (cx, cy) in ((n // 2, 0), (0, n // 2), (n, n // 2), (n // 2, n)):
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=tuple(fg))
    return np.asarray(im, np.float32) + N3(n, 1, seed, 3)


def floral(n=256, bg=(250, 226, 220), seed=17, cols=((220, 90, 120), (240, 140, 160), (200, 70, 100)), leaf=(120, 170, 110)):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    pts = [(r.uniform(0, n), r.uniform(0, n)) for _ in range(14)]
    for (cx, cy) in pts:
        col = tuple(int(v) for v in cols[r.integers(len(cols))])
        rr = r.uniform(10, 18)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                x0, y0 = cx + ox, cy + oy
                for a in np.linspace(0, 2 * math.pi, 6)[:-1]:
                    d.ellipse((x0 + math.cos(a + 0.4) * rr * 1.2 - 6, y0 + math.sin(a + 0.4) * rr * 1.2 - 3, x0 + math.cos(a + 0.4) * rr * 1.2 + 6,
                               y0 + math.sin(a + 0.4) * rr * 1.2 + 3), fill=leaf)
                for k in range(3):
                    s = rr * (1 - k * 0.3)
                    d.ellipse((x0 - s, y0 - s, x0 + s, y0 + s), fill=tuple(max(0, v - 25 * k) for v in col))
                d.arc((x0 - rr * 0.5, y0 - rr * 0.5, x0 + rr * 0.5, y0 + rr * 0.5), 0, 270, fill=(255, 230, 230), width=2)
    return np.asarray(im, np.float32) + N3(n, 1, seed, 3)


def stars_paper(n=256, bg=(186, 214, 236), fg=(250, 226, 120), seed=19, duck=True):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for i in range(10):
        cx, cy = r.uniform(0, n), r.uniform(0, n); s = r.uniform(7, 13)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                p = []
                for k in range(10):
                    rr = s if k % 2 == 0 else s * 0.45
                    a = k * math.pi / 5 - math.pi / 2
                    p.append((cx + ox + rr * math.cos(a), cy + oy + rr * math.sin(a)))
                d.polygon(p, fill=tuple(fg))
    if duck:
        for (cx, cy) in ((n * 0.25, n * 0.7), (n * 0.75, n * 0.2)):
            d.ellipse((cx - 16, cy - 8, cx + 14, cy + 12), fill=(250, 210, 60))
            d.ellipse((cx + 4, cy - 20, cx + 20, cy - 4), fill=(250, 210, 60))
            d.polygon([(cx + 19, cy - 13), (cx + 28, cy - 10), (cx + 19, cy - 8)], fill=(240, 130, 40))
            d.ellipse((cx + 12, cy - 15, cx + 15, cy - 12), fill=(30, 30, 30))
    return np.asarray(im, np.float32) + N3(n, 1, seed, 3)


def gingham(n=256, col=(250, 214, 110), k=8, seed=21):
    x, y = xy(n)
    a = ((x * k) % 1.0) < 0.5; b = ((y * k) % 1.0) < 0.5
    base = C((255, 250, 236))
    c = np.where((a & b)[..., None], C(col) * 0.86, np.where((a | b)[..., None], lerp(base, C(col), 0.55), base))
    return c + N3(n, 1, seed, 3)


def library_paper(n=256, seed=23):
    c = stripes(n, n, (40, 80, 60), (48, 92, 70), 6, seed)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    for i in range(6):
        for j in range(3):
            cx = (i + 0.75) * n / 6; cy = (j + 0.5) * n / 3
            d.polygon([(cx, cy - 8), (cx + 5, cy), (cx, cy + 8), (cx - 5, cy)], fill=(196, 168, 90))
    return np.asarray(im, np.float32)


def bedroom_wall(w=512, h=512, seed=25):
    """the girl's bedroom: candy-pink stripes with little white flower sprigs"""
    return stripes(w, h, (244, 190, 206), (252, 222, 230), 10, seed, sprig=(255, 255, 255))


def plaster(n=256, seed=27, col=(246, 242, 236)):
    return fill(n, col, 3, seed) + N3(n, 6, seed + 1, 4)


def paint(n=128, col=(246, 244, 240), seed=29):
    return fill(n, col, 2, seed) + N3(n, 0.8, seed + 1, 2)


def flock(n=512, seed=31):
    """model-railway grass flock on the house board"""
    c = fill(n, (96, 150, 64), 10, seed) + N3(n, 0.6, seed + 1, 22)
    d = noise(n, 14, seed + 2)
    c = lerp(c, C((126, 170, 70)), np.clip(d * 0.4, 0, 1)[..., None])
    r = np.random.default_rng(seed + 3)
    im = img(c).convert('RGB'); dr = ImageDraw.Draw(im)
    for _ in range(140):
        x, y = r.uniform(0, n), r.uniform(0, n)
        col = [(255, 255, 255), (250, 230, 90), (240, 150, 190)][r.integers(3)]
        dr.ellipse((x - 2, y - 2, x + 2, y + 2), fill=col)
    return np.asarray(im, np.float32)


def stone(n=256, seed=33, base=(170, 164, 150)):
    idx, ed = voronoi(n, 22, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-18, 18, 22)[idx]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 1.5, seed + 1, 6)
    return np.where((ed < 0.012)[..., None], C((90, 86, 78)), c)


def jumppad_tex(n=256):
    """pink daisy jump pad"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    petal = rr < 0.3 + 0.17 * np.abs(np.cos(a * 4))
    c = np.zeros((n, n, 3), np.float32) + C((250, 120, 170))
    c = np.where(petal[..., None], C((255, 240, 250)) - (rr * 60)[..., None], c)
    c = np.where((rr < 0.15)[..., None], C((255, 210, 60)), c)
    c = np.where((rr > 0.48)[..., None], C((190, 60, 120)), c)
    return c + N3(n, 1, 35, 4)


def water_tex(n=256, seed=37, col=(70, 150, 170)):
    c = fill(n, col, 6, seed)
    r = np.sin(noise(n, 10, seed + 1) * 3) * 18
    return c + r[..., None]


def bathwater_tex(n=256, seed=39):
    c = water_tex(n, seed, (150, 200, 230))
    x, y = xy(n)
    r = np.random.default_rng(seed)
    for _ in range(40):
        cx, cy, s = r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.01, 0.04)
        d = np.hypot(np.minimum(np.abs(x - cx), 1 - np.abs(x - cx)), np.minimum(np.abs(y - cy), 1 - np.abs(y - cy)))
        c = np.where((np.abs(d - s) < 0.004)[..., None], C((255, 255, 255)), c)
    return c


def grass(n=512, seed=51):
    """mown lawn: fine blades, mowing stripes are done by the lightmap; clover flecks and a few daisies"""
    c = fill(n, (84, 140, 52), 8, seed) + N3(n, 0.5, seed + 1, 22) + N3(n, 1.5, seed + 2, 10)
    d = noise(n, 24, seed + 3)
    c = lerp(c, C((112, 158, 60)), np.clip(d * 0.35, 0, 1)[..., None])
    c = lerp(c, C((70, 118, 44)), np.clip(-d * 0.3, 0, 1)[..., None])
    im = img(c).convert('RGB'); dr = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 4)
    for _ in range(900):
        x, y = r.uniform(0, n), r.uniform(0, n); L_ = r.uniform(3, 8); a = r.uniform(-0.5, 0.5)
        col = tuple(int(v) for v in (C((120, 176, 72)) + r.uniform(-20, 20)))
        dr.line([(x, y), (x + L_ * math.sin(a), y - L_ * math.cos(a))], fill=col, width=1)
    for _ in range(26):
        x, y = r.uniform(4, n - 4), r.uniform(4, n - 4)
        for k in range(8):
            a = k * math.pi / 4
            dr.ellipse((x + math.cos(a) * 3 - 1.5, y + math.sin(a) * 3 - 1.5, x + math.cos(a) * 3 + 1.5, y + math.sin(a) * 3 + 1.5), fill=(250, 250, 245))
        dr.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(250, 210, 50))
    return np.asarray(im, np.float32)


def soil(n=256, seed=53):
    c = fill(n, (86, 62, 42), 8, seed) + N3(n, 0.6, seed + 1, 16)
    im = img(c).convert('RGB'); dr = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 2)
    for _ in range(160):
        x, y, s_ = r.uniform(0, n), r.uniform(0, n), r.uniform(1, 3)
        g = int(r.uniform(60, 140)); dr.ellipse((x - s_, y - s_, x + s_, y + s_), fill=(g, int(g * 0.8), int(g * 0.6)))
    return np.asarray(im, np.float32)


def soil_wall(n=512, seed=55):
    """ant tunnel walls: packed earth with roots and pebbles"""
    c = soil(n, seed) * 0.9
    im = img(c).convert('RGB'); dr = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 1)
    for _ in range(10):
        x, y = r.uniform(0, n), r.uniform(0, n)
        pts = [(x, y)]
        for k in range(12):
            x += r.uniform(-14, 14); y += r.uniform(4, 16); pts.append((x, y))
        dr.line(pts, fill=(150, 116, 80), width=int(r.uniform(2, 5)))
    for _ in range(40):
        x, y, s_ = r.uniform(0, n), r.uniform(0, n), r.uniform(4, 10)
        g = int(r.uniform(120, 170)); dr.ellipse((x - s_, y - s_ * 0.7, x + s_, y + s_ * 0.7), fill=(g, g - 6, g - 14))
    return np.asarray(im, np.float32)


def weatherboard(w=256, h=256, seed=57, col=(232, 224, 206), nb=8):
    """painted bevel-back weatherboards (horizontal), shadow under each lap"""
    x, y = xy(w, h)
    b = (y * nb) % 1.0
    c = np.zeros((h, w, 3), np.float32) + C(col) * (0.9 + 0.12 * b)[..., None]
    c = np.where((b > 0.93)[..., None], C(col) * 0.62, c)
    gr = np.asarray(img(noise(w, 1, seed, h) * 40 + 128).resize((w // 16, h)).resize((w, h)), np.float32) - 128
    return c + gr[..., None] * 0.08 + N3(w, 1, seed + 3, 2, h)


def palings(w=256, h=512, seed=59, col=(150, 112, 74)):
    """weathered pine palings (vertical boards) with two rails' worth of nail heads"""
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    k = 6
    col_i = np.floor(x * k).astype(int)
    tone = r.uniform(-18, 18, k + 1)[col_i % (k + 1)]
    c = np.zeros((h, w, 3), np.float32) + C(col) + tone[..., None]
    st = np.asarray(img(noise(w, 0.6, seed + 1, h) * 40 + 128).resize((w, h // 24)).resize((w, h)), np.float32) - 128
    c += st[..., None] * 0.35
    u = (x * k) % 1.0
    c = np.where(((u < 0.04) | (u > 0.97))[..., None], C((60, 44, 30)), c)
    for yy in (0.18, 0.82):
        c = np.where(((np.abs(y - yy) < 0.006) & (np.abs(u - 0.5) < 0.02))[..., None], C((50, 50, 54)), c)
    grey = np.clip(noise(w, 20, seed + 2, h) * 0.4, 0, 1)[..., None]
    return lerp(c, C((130, 126, 118)), grey * 0.6)


def decking(n=256, seed=61):
    return boards(n, n, seed, (150, 96, 60), 5, False, (50, 32, 22), 0.8)


def pavers(n=256, seed=63):
    x, y = xy(n)
    r = np.random.default_rng(seed)
    k = 4
    row = np.floor(y * k).astype(int)
    off = (row % 2) * 0.5 / 2
    cx = np.floor((x + off) * 2).astype(int)
    tone = r.uniform(-14, 14, (k + 1, 4))[row % (k + 1), cx % 4]
    c = np.zeros((n, n, 3), np.float32) + C((178, 170, 156)) + tone[..., None] + N3(n, 1, seed + 1, 8)
    g = ((y * k % 1) < 0.03) | (((x + off) * 2 % 1) < 0.015)
    return np.where(g[..., None], C((96, 92, 84)), c)


def brick(w=256, h=256, seed=65, base=(150, 70, 52)):
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    rows = 8
    row = np.floor(y * rows).astype(int)
    off = (row % 2) * 0.5 / 4
    cx = np.floor((x + off) * 4).astype(int)
    tone = r.uniform(-20, 20, (rows + 1, 5))[row % (rows + 1), cx % 5]
    c = np.zeros((h, w, 3), np.float32) + C(base) + tone[..., None] + N3(w, 1, seed + 1, 8, h)
    g = ((y * rows % 1) < 0.08) | (((x + off) * 4 % 1) < 0.03)
    return np.where(g[..., None], C((190, 184, 170)), c)


def corrugated(w=256, h=256, seed=67, col=(170, 176, 178)):
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C(col) * (0.82 + 0.22 * np.sin(x * math.pi * 16))[..., None]
    rust = np.clip(noise(w, 10, seed, h) - 1.2, 0, 1)[..., None]
    return lerp(c + N3(w, 1, seed + 1, 4, h), C((150, 90, 50)), rust)


def concrete(n=256, seed=69):
    return fill(n, (172, 168, 160), 6, seed) + N3(n, 0.7, seed + 1, 8)


def lattice(n=128, seed=71):
    """diagonal timber lattice (alpha cut-out)"""
    x, y = xy(n)
    d1 = ((x + y) * 4) % 1.0; d2 = ((x - y) * 4) % 1.0
    bar = (d1 < 0.22) | (d2 < 0.22)
    c = np.zeros((n, n, 3), np.float32) + C((150, 100, 62)) + N3(n, 0.8, seed, 8)
    c = np.where((d1 < 0.22)[..., None], c * 1.05, c * 0.92)
    return c, np.where(bar, 255.0, 0.0)


def curtain_tex(n=256, seed=73, col=(236, 226, 200)):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C(col) * (0.8 + 0.2 * np.sin(x * math.pi * 14))[..., None]
    return c + N3(n, 1, seed, 3)


def kids_tiles(n=256, seed=75):
    return tiles(n, (240, 236, 226), 4, seed, (200, 196, 188))


def sign_img(text, w, h, bg, fg, serif=True, border=None):
    return text_img(text, w, h, bg, fg, serif, border=border)


SIGNS = {
    'sign_colony': ('ANT COLONY  -  STAFF ONLY', 1024, 128, (60, 40, 26), (250, 220, 150), False),
    'sign_shed': ("DAD'S SHED", 512, 128, (30, 70, 50), (250, 240, 200), False),
}


def make_textures():
    W('grass', grass()); W('soil', soil()); W('soil_wall', soil_wall()); W('soil_floor', soil(256, 77) * 0.85)
    W('weatherboard', weatherboard()); W('weatherboard_green', weatherboard(256, 256, 79, (120, 150, 120)))
    W('palings', palings()); W('decking', decking()); W('pavers', pavers()); W('brick', brick()); W('concrete', concrete())
    W('corrugated', corrugated()); W('corrugated_red', corrugated(256, 256, 81, (150, 54, 44)))
    c, a = lattice(); W('lattice', c, a); W('curtain', curtain_tex()); W('curtain_b', curtain_tex(256, 83, (170, 196, 220)))
    W('paint_white', paint()); W('paint_dark', paint(128, (60, 62, 66), 85)); W('pine', boards(256, 256, 87, (214, 176, 120), 4, ends=False))
    W('shed_floor', boards(256, 256, 89, (170, 140, 104), 5)); W('shed_wall_in', boards(256, 256, 91, (200, 170, 126), 6, True, ends=False))
    W('sleeper', boards(256, 128, 93, (120, 84, 56), 2, ends=False)); W('kennel_in', boards(256, 256, 95, (190, 150, 100), 6, True, ends=False))
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (200, 70, 130), 3, 97))
    W('water', water_tex(256, 99, (90, 170, 210))); W('glass', fill(64, (200, 226, 240), 3, 101))
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 103)); W('skylight', fill(64, (255, 250, 230), 2, 105))
    W('vinyl_blue', fill(128, (80, 150, 220), 4, 107)); W('stone', stone())
    W('cubby_in', boards(256, 256, 109, (246, 230, 206), 6, True, ends=False)); W('sand', fill(256, (232, 210, 160), 8, 111) + N3(256, 0.5, 112, 12))
    for nm, (t, w, h, bg, fg, serif) in SIGNS.items():
        W(nm, sign_img(t, w, h, bg, fg, serif, border=fg))


# ------------------------------------------------------------------------------------------- shader
STEPS = {'grass': 'softsteps', 'soil': 'softsteps', 'soil_floor': 'softsteps', 'decking': 'woodsteps', 'pine': 'woodsteps', 'shed_floor': 'woodsteps',
         'sleeper': 'woodsteps', 'corrugated': 'latticesteps', 'corrugated_red': 'latticesteps', 'vinyl_blue': 'splashsteps'}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


def model_shaders():
    s = '// ---- MD3 / IQM models (bb_models.py)\n'
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
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n{two}'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform') and opt['deform'] != 'autosprite2': s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n'
                  f'\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n')
        elif kind == 'dynenv':                      # movers with a chrome / porcelain sheen
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.25 0.25 0.25 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'flag':                        # waving pennant on the tower (vertex lit)
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nomarks\n\tcull none\n\tdeformVertexes wave 60 sin 0 5 0 1.4\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.12 0.14 0.15")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.2 0.2 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'water':                       # bath water / pond surface inside a model (nonsolid, translucent)
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\talphaGen const 0.7\n\t\trgbGen identity\n'
                  f'\t\ttcMod turb 0 0.04 0 0.2\n\t}}\n}}\n\n')
    return s


def water_shader(name, img, fog, depth, col_ed):
    return f'''{TD}/{name}
{{
	qer_editorimage {TD}/{img}
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	cull none
	{{
		map {TD}/{img}
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.72
		rgbGen identity
		tcMod turb 0 0.05 0 0.12
		tcMod scroll 0.01 0.02
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.2 0.22 )
		tcGen environment
	}}
}}

{TD}/{name}_nodraw
{{
	qer_editorimage {TD}/{img}
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

'''


def make_shader():
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padbbq/bb_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'water', 'glass', 'lattice'}
    for nm in sorted(SIZES):
        if nm in special: continue
        S_ += lm(nm, STEPS.get(nm))
    NS_ = '\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tq3map_nonplanar\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.6 0.8\n\tq3map_lightSubdivide 128\n', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 60\n\t}}\n'))
    S_ += lm('jumppad_ns', extra=NS_, tex=f'{TD}/jumppad', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 60\n\t}}\n'))
    S_ += water_shader('water', 'water', None, None, None)
    S_ += (f'{TD}/lattice\n{{\n\tqer_editorimage {TD}/lattice.tga\n\tqer_trans 0.6\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm alphashadow\n'
           f'\tsurfaceparm nomarks\n\tcull none\n\tnopicmip\n\t{{\n\t\tmap {TD}/lattice.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen identity\n\t}}\n'
           f'\t{{\n\t\tmap $lightmap\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\tdepthFunc equal\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S_ += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 1 0.94 0.8 260 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 110 3
	skyparms env/fort-pad512 - -
}}

{TD}/glass
{{
	qer_editorimage {TD}/glass
	qer_trans 0.35
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{{
		map {TD}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.1 0.12 0.13 )
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.16 0.16 0.18 )
		tcGen environment
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
    S_ += model_shaders()
    S_ += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(out('scripts'), exist_ok=True)
    open(out('scripts', NS + '.shader'), 'w').write(S_)


def make_arena():
    open(out('scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(o, extra_models=None):
    bblib.STATE['out'] = o
    make_textures()
    import bb_models
    bb_models.make()
    if extra_models: extra_models()
    make_shader(); make_arena()


if __name__ == '__main__':
    make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(SIZES), 'textures')
