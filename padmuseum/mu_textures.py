"""Procedural brush textures, shader + arena for wop_padmuseum (Midnight Museum). All art is original and
generated here.

make_all(out, extra) writes textures/padmuseum/*, models/padmuseum/* (mu_models), scripts/padmuseum.shader
and scripts/wop_padmuseum.arena (pk3dir layout). The sky is WoP's own sunny garden box (env/fort-pad512)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mulib import *
import mulib

MAP = 'wop_padmuseum'
LONGNAME = 'Midnight Museum'
SIZES = {}
ALPHA = set()
SUN = (60.0, 58.0)                      # yaw (90 = north: the user plays in New Zealand, the sun is in the north), elevation


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


def marble(n=512, seed=51, base=(232, 228, 220), vein=(120, 116, 112), k=2):
    """marble slabs with soft veins, k x k slabs per tile"""
    x, y = xy(n)
    v = noise(n, 6, seed) * 1.2 + noise(n, 2, seed + 1) * 0.5
    vein_m = np.clip(1 - np.abs(np.sin(v * 3 + x * 9)) * 6, 0, 1)
    c = np.zeros((n, n, 3), np.float32) + C(base) + N3(n, 1.5, seed + 2, 5)
    c = lerp(c, C(vein), (vein_m * 0.55)[..., None])
    g = ((x * k % 1) < 0.006) | ((y * k % 1) < 0.006)
    return np.where(g[..., None], c * 0.75, c)


def marble_checker(n=512, seed=53):
    a = marble(n, seed, (236, 232, 224), (140, 136, 130), 4)
    b = marble(n, seed + 7, (52, 50, 56), (150, 146, 150), 4)
    x, y = xy(n)
    m = ((np.floor(x * 4) + np.floor(y * 4)) % 2)[..., None]
    return np.where(m > 0, b, a)


def limestone(w=512, h=512, seed=55, base=(206, 196, 176), rows=6, cols=3):
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    row = np.floor(y * rows).astype(int)
    off = (row % 2) * 0.5 / cols
    cx_ = np.floor((x + off) * cols).astype(int)
    tone = r.uniform(-12, 12, (rows + 1, cols + 2))[row % (rows + 1), cx_ % (cols + 2)]
    c = np.zeros((h, w, 3), np.float32) + C(base) + tone[..., None] + N3(w, 1, seed + 1, 6, h) + N3(w, 6, seed + 2, 6, h)
    g = ((y * rows % 1) < 0.012) | (((x + off) * cols % 1) < 0.008)
    return np.where(g[..., None], c * 0.72, c)


def gallery_paint(n=256, col=(120, 30, 36), seed=57):
    return fill(n, col, 3, seed) + N3(n, 6, seed + 1, 3)


def wainscot(w=256, h=256, seed=59, col=(92, 60, 38)):
    """dark timber panelling: raised panels"""
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C(col) + N3(w, 1, seed, 5, h)
    u = (x * 2) % 1.0; v = y
    panel = (np.abs(u - 0.5) < 0.38) & (np.abs(v - 0.5) < 0.4)
    edge = (np.abs(np.abs(u - 0.5) - 0.38) < 0.02) & (np.abs(v - 0.5) < 0.42) | (np.abs(np.abs(v - 0.5) - 0.4) < 0.02) & (np.abs(u - 0.5) < 0.4)
    c = np.where(panel[..., None], c * 1.08, c)
    return np.where(edge[..., None], c * 0.6, c)


def sandstone(n=512, seed=61):
    return limestone(n, n, seed, (214, 182, 128), 5, 2)


def hieroglyphs(w=512, h=256, seed=63):
    """sandstone frieze carved with rows of glyphs (painted ochre / blue / red)"""
    r = np.random.default_rng(seed)
    im = Image.fromarray(np.clip(sandstone(512, seed)[:256], 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    cols = [(60, 90, 150), (150, 60, 40), (40, 40, 40), (180, 140, 40)]
    for row in range(3):
        y0 = 20 + row * 80
        d.line([(0, y0 - 10), (w, y0 - 10)], fill=(120, 96, 60), width=2)
        x = 12
        while x < w - 30:
            kind = r.integers(6); col = cols[r.integers(4)]
            if kind == 0: d.ellipse((x, y0, x + 26, y0 + 40), outline=col, width=4)                          # cartouche-ish oval
            elif kind == 1:                                                                                      # eye
                d.ellipse((x, y0 + 12, x + 30, y0 + 28), outline=col, width=3); d.ellipse((x + 11, y0 + 15, x + 19, y0 + 25), fill=col)
            elif kind == 2: d.polygon([(x, y0 + 50), (x + 14, y0), (x + 28, y0 + 50)], outline=col)               # reed / pyramid
            elif kind == 3:                                                                                      # ankh
                d.ellipse((x + 6, y0, x + 22, y0 + 18), outline=col, width=3); d.line([(x + 14, y0 + 18), (x + 14, y0 + 50)], fill=col, width=4)
                d.line([(x + 2, y0 + 26), (x + 26, y0 + 26)], fill=col, width=4)
            elif kind == 4:                                                                                      # bird
                d.ellipse((x, y0 + 14, x + 24, y0 + 38), fill=col); d.ellipse((x + 16, y0 + 4, x + 30, y0 + 18), fill=col)
                d.line([(x + 6, y0 + 38), (x + 2, y0 + 52)], fill=col, width=3); d.line([(x + 16, y0 + 38), (x + 18, y0 + 52)], fill=col, width=3)
            else: d.line([(x, y0 + 25), (x + 28, y0 + 25)], fill=col, width=6); d.line([(x + 14, y0 + 5), (x + 14, y0 + 45)], fill=col, width=6)
            x += 36
    return np.asarray(im, np.float32)


def star_carpet(n=256, seed=65):
    c = fill(n, (24, 26, 60), 4, seed) + N3(n, 0.6, seed + 1, 6)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 2)
    for _ in range(30):
        x, y, s_ = r.uniform(0, n), r.uniform(0, n), r.uniform(2, 5)
        d.ellipse((x - s_, y - s_, x + s_, y + s_), fill=(220, 200, 120))
    return np.asarray(im, np.float32)


def starfield(w=1024, h=256, seed=67):
    """planetarium dome sky: deep blue gradient, stars, a faint milky way band, constellation lines"""
    x, y = xy(w, h)
    c = lerp(C((4, 6, 20)), C((20, 26, 60)), y[..., None]) + N3(w, 20, seed, 6, h)
    mw = np.exp(-((y - 0.4 - 0.15 * np.sin(x * 2 * math.pi)) / 0.08) ** 2)
    c += (mw * (40 + 30 * noise(w, 2, seed + 1, h)))[..., None] * C((0.8, 0.8, 1.0))
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 2)
    pts = []
    for _ in range(900):
        px, py = r.uniform(0, w), r.uniform(0, h * 0.95); s_ = r.choice([0.6, 0.8, 1.2, 1.8], p=[0.5, 0.3, 0.15, 0.05])
        g = int(r.uniform(160, 255)); d.ellipse((px - s_, py - s_, px + s_, py + s_), fill=(g, g, min(255, g + 20)))
        if s_ > 1.5: pts.append((px, py))
    for k in range(0, len(pts) - 3, 4):
        d.line(pts[k:k + 4], fill=(70, 90, 150), width=1)
    return np.asarray(im, np.float32)


def roof_gravel(n=256, seed=69):
    c = fill(n, (110, 108, 104), 10, seed) + N3(n, 0.5, seed + 1, 24)
    return c


def coffer(n=256, seed=71):
    """plaster ceiling coffers"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((216, 210, 196)) + N3(n, 2, seed, 4)
    u = (x * 2) % 1.0; v = (y * 2) % 1.0
    d = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    return c * (0.7 + 0.3 * np.clip(d * 8, 0, 1))[..., None]


def snow(n=256, seed=73):
    return fill(n, (232, 238, 246), 6, seed) + N3(n, 0.5, seed + 1, 10)


def ocean_wall(n=256, seed=75):
    c = fill(n, (24, 60, 96), 4, seed)
    x, y = xy(n)
    r = np.sin(noise(n, 10, seed + 1) * 4 + y * 10) * 10
    return c + r[..., None]


def gem_wall(n=256, seed=77):
    return fill(n, (40, 26, 52), 4, seed) + N3(n, 4, seed + 1, 6)


def tomb_stone(n=512, seed=79):
    return limestone(n, n, seed, (150, 128, 96), 4, 2) * 0.85


def gold_floor(n=256, seed=81):
    return tiles(n, (200, 160, 60), 4, seed, (110, 80, 30))


def exit_sign(w=256, h=96):
    return text_img('EXIT', w, h, (20, 140, 60), (240, 255, 240), False)


def sign_img(text, w, h, bg, fg, serif=True, border=None):
    return text_img(text, w, h, bg, fg, serif, border=border)




SIGNS = {
    'sign_museum': ('NATURAL HISTORY MUSEUM', 1024, 128, (36, 30, 26), (230, 200, 130), True),
    'sign_egypt': ('ANCIENT EGYPT', 512, 128, (60, 40, 20), (230, 190, 90), True),
    'sign_planet': ('PLANETARIUM', 512, 128, (16, 20, 50), (200, 210, 255), True),
    'sign_ice': ('THE ICE AGE', 512, 128, (30, 50, 70), (220, 240, 255), True),
    'sign_gems': ('GEMS & MINERALS', 512, 128, (40, 20, 50), (230, 190, 255), True),
    'sign_ocean': ('THE DEEP OCEAN', 512, 128, (10, 40, 70), (180, 230, 255), True),
    'sign_gift': ('GIFT SHOP', 512, 128, (100, 30, 40), (255, 236, 200), True),
    'sign_staff': ('STAFF ONLY', 512, 128, (180, 30, 30), (255, 255, 255), False),
    'sign_treasury': ("THE PHARAOH'S TREASURY", 1024, 128, (50, 30, 10), (250, 210, 100), True),
}


def make_textures():
    W('marble_checker', marble_checker()); W('marble', marble()); W('marble_dark', marble(512, 83, (60, 56, 60), (160, 150, 150)))
    W('limestone', limestone()); W('paint_red', gallery_paint()); W('paint_green', gallery_paint(256, (36, 70, 56), 85))
    W('paint_blue', gallery_paint(256, (30, 44, 80), 87)); W('wainscot', wainscot()); W('parquet', herringbone(256, 89, (120, 80, 48), (146, 100, 60)))
    W('sandstone', sandstone()); W('hieroglyphs', hieroglyphs()); W('star_carpet', star_carpet()); W('roof_gravel', roof_gravel())
    W('coffer', coffer()); W('snow', snow()); W('ocean_wall', ocean_wall()); W('gem_wall', gem_wall()); W('tomb_stone', tomb_stone())
    W('gold_floor', gold_floor()); W('concrete', fill(256, (150, 148, 144), 6, 91) + N3(256, 0.7, 92, 8)); W('lead', fill(128, (110, 116, 120), 4, 93))
    W('paint_white', paint()); W('paint_dark', paint(128, (50, 50, 56), 95)); W('carpet_red', carpet(256, 97, (130, 30, 40)))
    W('stair_tread', boards(256, 256, 99, (110, 74, 46), 4, ends=False)); W('terrazzo', fill(256, (200, 194, 184), 6, 101) + N3(256, 0.4, 102, 18))
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (150, 120, 60), 3, 103)); W('glass', fill(64, (200, 226, 240), 3, 105))
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 107)); W('skylight', fill(64, (120, 140, 200), 2, 109)); W('exit_sign', exit_sign())
    W('water', water_tex(256, 111, (40, 110, 150))); W('starfield', starfield())
    for nm, (t, w, h, bg, fg, serif) in SIGNS.items():
        W(nm, sign_img(t, w, h, bg, fg, serif, border=fg))


# ------------------------------------------------------------------------------------------- shader
STEPS = {'parquet': 'woodsteps', 'stair_tread': 'woodsteps', 'carpet_red': 'carpetsteps', 'star_carpet': 'carpetsteps', 'snow': 'snowsteps',
         'roof_gravel': 'sandsteps', 'sandstone': 'sandsteps'}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


def model_shaders():
    s = '// ---- MD3 / IQM models (mu_models.py)\n'
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
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padmuseum/mu_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'water', 'glass', 'exit_sign'}
    for nm in sorted(SIZES):
        if nm in special: continue
        S_ += lm(nm, STEPS.get(nm))
    NS_ = '\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tq3map_nonplanar\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.6 0.8\n\tq3map_lightSubdivide 128\n', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 60\n\t}}\n'))
    S_ += lm('jumppad_ns', extra=NS_, tex=f'{TD}/jumppad', stage=(
        f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 60\n\t}}\n'))
    S_ += water_shader('water', 'water', None, None, None)
    S_ += lm('exit_sign', extra='\tq3map_surfacelight 120\n\tq3map_lightRGB 0.3 1 0.4\n\tq3map_lightSubdivide 64\n', stage=(
        f'\t{{\n\t\tmap {TD}/exit_sign\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n\t}}\n'))
    S_ += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 0.55 0.65 1 120 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 25 3
	skyparms env/pc-friday-13th-512 - -
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
    mulib.STATE['out'] = o
    make_textures()
    import mu_models
    mu_models.make()
    if extra_models: extra_models()
    make_shader(); make_arena()


if __name__ == '__main__':
    make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(SIZES), 'textures')
