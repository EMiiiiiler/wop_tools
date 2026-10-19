"""Procedural textures, shader + arena for wop_moosefalls (Moose Mountain Falls).
All art is original and generated here. make_all(out) writes textures/moosefalls/*, models/moosefalls/* (moose_models),
scripts/moosefalls.shader and scripts/wop_moosefalls.arena (pk3dir layout). The sky is WoP's own env/frost-bite512
(snowy evening over a fir forest, seen through the windows and the ridge skylight)."""
import os, sys, math, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import moose_models

MAP = 'wop_moosefalls'
NS = 'moosefalls'
LONGNAME = 'Moose Mountain Falls'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
if not os.path.exists(FONTS): FONTS = FONTB


# ------------------------------------------------------------------------------------------- helpers
def noise(n, blur, seed, m=None):
    """tileable gaussian-blurred noise, zero mean / unit std"""
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, m * 3))
    for i in range(3):
        for j in range(3): big.paste(im, (i * n, j * m))
    a = np.asarray(big.filter(ImageFilter.GaussianBlur(blur)).crop((n, m, 2 * n, 2 * m)), np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def N3(n, blur, seed, amp, m=None): return noise(n, blur, seed, m)[..., None] * amp
def C(c): return np.array(c, np.float32)
def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
def arr(im): return np.asarray(im.convert('RGB'), np.float32)
def lerp(a, b, t): return a + (b - a) * t


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def tile_xy(n, m=None):
    m = m or n
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    return x / n, y / m


def font(sz, serif=False): return ImageFont.truetype(FONTS if serif else FONTB, sz)


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', NS); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}; self.alpha = set()

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a
        if alpha is not None or im.mode == 'RGBA':
            im = im.convert('RGBA')
            if alpha is not None: im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga')); self.alpha.add(name)
        else:
            im.convert('RGB').save(os.path.join(self.dir, name + '.jpg'), quality=92)
        self.sizes[name] = im.size


def tileable_draw(n, draw_fn, base, m=None):
    """draw shapes with wrap-around (draw_fn(d, ox, oy) is called for the 9 offsets)"""
    m = m or n
    im = img(base); d = ImageDraw.Draw(im)
    for ox in (-n, 0, n):
        for oy in (-m, 0, m):
            draw_fn(d, ox, oy)
    return arr(im)


# ------------------------------------------------------------------------------------------- floors
def flagstone(n=512, seed=1):
    """tan stamped-concrete flagstone (the pool deck): irregular stones with grout lines, warm sandy tones"""
    r = np.random.default_rng(seed)
    pts = r.random((26, 2)) * n
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    d1 = np.full((n, n), 1e9, np.float32); d2 = np.full((n, n), 1e9, np.float32); lab = np.zeros((n, n), np.int32)
    for i, (px, py) in enumerate(pts):
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dd = np.hypot(x - px - ox, y - py - oy)
                m = dd < d1
                d2 = np.where(m, d1, np.minimum(d2, dd)); lab = np.where(m, i, lab); d1 = np.where(m, dd, d1)
    edge = np.clip((d2 - d1) / 5.0, 0, 1)
    tint = r.normal(0, 1, (26, 3)) * 10
    base = C((196, 160, 118)) + tint[lab] + N3(n, 1.2, seed, 7) + N3(n, 20, seed + 1, 9)
    grout = C((140, 108, 78))
    a = base * edge[..., None] + grout * (1 - edge[..., None])
    a *= (0.92 + 0.08 * np.clip(d1 / 40, 0, 1))[..., None]        # stones slightly darker at their rims
    return a


def coping(n=256, seed=3):
    """pool coping: pale bull-nosed concrete pavers"""
    a = fill(n, (214, 206, 190), 5, seed)
    a[:, ::64] *= 0.8; a[:, 1::64] *= 0.9
    return a


def pool_tile(n=256, seed=5):
    """aqua pool mosaic tile (floor + walls)"""
    a = np.zeros((n, n, 3), np.float32)
    r = np.random.default_rng(seed)
    t = 16
    for i in range(0, n, t):
        for j in range(0, n, t):
            a[i:i + t, j:j + t] = C((70, 170, 200)) + r.normal(0, 9, 3)
    a[::t] = (200, 225, 230); a[:, ::t] = (200, 225, 230)
    return a + N3(n, 1, seed + 1, 4)


def pool_band(w=256, h=256, seed=7):
    """pool wall: aqua tile with a dark blue waterline band of small tiles at the top"""
    a = pool_tile(w, seed)
    a[:32] = pool_tile(w, seed + 9)[:32] * 0.35 + C((20, 50, 140)) * 0.65
    a[30:34] = (230, 236, 236)
    return a


def lane_line(n=256, seed=9):
    a = pool_tile(n, seed)
    a[:, 104:152] = C((20, 50, 130)) + N3(n, 1, seed, 4)[:, 104:152]
    return a


def splashpad(n=512, seed=11):
    """kids' splash pad: blue/teal rubber surfacing with big triangle mosaic in sand and navy (picture 3)"""
    a = fill(n, (40, 150, 210), 5, seed)
    im = img(a); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    cols = [(232, 196, 140), (30, 70, 150), (90, 200, 220), (240, 210, 160)]
    s = 64
    for i in range(0, n, s):
        for j in range(0, n, s):
            k = r.integers(0, 6)
            if k >= 4: continue
            c = cols[k]
            if r.random() < 0.5: d.polygon([(i, j), (i + s, j), (i + s / 2, j + s)], fill=c)
            else: d.polygon([(i, j + s), (i + s, j + s), (i + s / 2, j)], fill=c)
    return arr(im) + N3(n, 1, seed + 2, 5)


def kitchen_tile(n=256, seed=13):
    a = np.zeros((n, n, 3), np.float32)
    t = 32
    for i in range(0, n, t):
        for j in range(0, n, t):
            a[i:i + t, j:j + t] = (200, 40, 36) if ((i + j) // t) % 2 else (236, 230, 220)
    return a + N3(n, 1, seed, 5)


def planks(w=256, h=256, seed=17, col=(150, 104, 62)):
    """chunky deck planks (bridges, treehouse, stairs)"""
    a = np.zeros((h, w, 3), np.float32)
    r = np.random.default_rng(seed)
    for k in range(4):
        y0 = k * h // 4
        c = C(col) + r.normal(0, 10, 3)
        g = noise(w, 1.5, seed + k, h // 4)
        band = c + g[..., None] * 10 + np.sin(np.arange(w) / w * 2 * math.pi * r.integers(3, 7))[None, :, None] * 8
        a[y0:y0 + h // 4] = band
        a[y0:y0 + 3] = C(col) * 0.45
    return a


def ceiling(w=256, h=256, seed=19):
    """tongue-and-groove pine ceiling boards (warm orange-brown, picture 3)"""
    a = np.zeros((h, w, 3), np.float32)
    r = np.random.default_rng(seed)
    for k in range(8):
        x0 = k * w // 8
        c = C((176, 112, 62)) + r.normal(0, 12, 3)
        g = noise(w // 8, 1.0, seed + k, h)
        grain = np.sin(np.arange(h)[:, None] / h * 2 * math.pi * r.integers(4, 9) + g * 0.5)
        a[:, x0:x0 + w // 8] = c + g[..., None] * 6 + grain[..., None] * 8
        a[:, x0:x0 + 2] = (80, 46, 24)
    return a


def glulam(w=256, h=256, seed=23):
    """glued-laminated timber: thin lamination lines along the beam"""
    a = np.zeros((h, w, 3), np.float32) + C((190, 124, 66))
    for k in range(0, h, 16):
        a[k:k + 16] += np.random.default_rng(seed + k).normal(0, 9, 3)
        a[k] *= 0.8
    a += N3(w, 1, seed, 5, h)
    a += np.sin(np.arange(w) / w * 2 * math.pi * 3 + noise(w, 8, seed + 1, h) * 0.6)[..., None] * 6
    return a


def stucco(n=256, col=(232, 206, 112), seed=29):
    """lodge wall: warm painted stucco (yellow by default, picture 1)"""
    return fill(n, col, 6, seed)


def wainscot(w=256, h=256, seed=31):
    """lower wall: vertical cedar boards with a dark base"""
    a = np.zeros((h, w, 3), np.float32)
    r = np.random.default_rng(seed)
    for k in range(8):
        x0 = k * w // 8
        a[:, x0:x0 + w // 8] = C((126, 76, 44)) + r.normal(0, 10, 3) + N3(w // 8, 1, seed + k, 6, h)
        a[:, x0:x0 + 2] = (60, 34, 18)
    a[-24:] = C((60, 40, 28)) + N3(w, 1, seed, 4, 24)
    return a


def logwall(w=256, h=256, seed=37):
    """stacked round logs seen from the side (horizontal, 64u per log)"""
    x, y = tile_xy(w, h)
    k = (y * 4) % 1.0
    shade = np.sqrt(np.clip(1 - (2 * k - 1) ** 2, 0, 1))
    a = lerp(C((70, 42, 22)), C((168, 112, 64)), shade[..., None])
    a += N3(w, 1.5, seed, 8, h) + (np.sin(x * 2 * math.pi * 6 + noise(w, 10, seed + 1, h) * 1.5) * 6)[..., None]
    a[(k < 0.04) | (k > 0.96)] = (230, 222, 200)                       # chinking
    return a


def fieldstone(n=256, seed=41):
    """rounded river stones in mortar (play structure base, picture 3)"""
    base = fill(n, (200, 192, 176), 6, seed)
    r = np.random.default_rng(seed)
    stones = [(r.integers(0, n), r.integers(0, n), r.integers(16, 30), r.integers(12, 22), r.normal(0, 1, 3)) for _ in range(70)]
    def dr(d, ox, oy):
        for (x, y, w, h, t) in stones:
            c = tuple(int(v) for v in (C((150, 104, 76)) + t * 24 + (r.random() * 30)).clip(0, 255))
            d.ellipse((x - w + ox, y - h + oy, x + w + ox, y + h + oy), fill=c, outline=(110, 96, 82))
    a = tileable_draw(n, dr, base)
    return a + N3(n, 1, seed + 1, 6)


def rock(n=512, seed=43):
    """artificial rockwork (grotto): layered sandstone with cracks"""
    x, y = tile_xy(n)
    a = fill(n, (150, 120, 92), 10, seed)
    a += (np.sin(y * 2 * math.pi * 6 + noise(n, 24, seed + 1) * 1.5)[..., None] * 14) * C((1, 0.9, 0.8))
    cr = np.abs(noise(n, 6, seed + 2)) < 0.05
    a[cr] *= 0.55
    return a + N3(n, 2, seed + 3, 8)


def bark(n=512, seed=47):
    x, y = tile_xy(n)
    gro = noise(n, 3, seed)
    gro = np.asarray(img(np.repeat((gro * 50 + 128)[..., None], 3, 2)).convert('L').resize((n // 6, n)).resize((n, n)), np.float32) / 255
    ridge = np.clip(np.sin(x * 2 * math.pi * 14 + noise(n, 20, seed + 1) * 1.4) * 0.5 + 0.5, 0, 1)
    a = lerp(C((54, 36, 26)), C((130, 96, 70)), (ridge * 0.7 + gro * 0.3)[..., None])
    return a + N3(n, 0.8, seed + 3, 6)


def rotten(n=256, seed=53):
    x, y = tile_xy(n)
    a = fill(n, (110, 72, 44), 8, seed)
    a += (np.sin((x * 14 + noise(n, 10, seed + 1) * 0.6) * 2 * math.pi)[..., None] * 14) * C((1, 0.8, 0.6))
    return a


def metal_white(n=64, seed=59): return fill(n, (232, 234, 236), 3, seed)
def metal_dark(n=64, seed=61): return fill(n, (70, 74, 80), 3, seed)
def steel(n=128, seed=67):
    x, y = tile_xy(n)
    return fill(n, (178, 182, 188), 3, seed) + (np.sin(x * 2 * math.pi * 40) * 5)[..., None]


def roof_red(w=256, h=256, seed=71):
    """red standing-seam metal roof (snack bar, play cabins)"""
    x, y = tile_xy(w, h)
    a = fill(w, (176, 40, 34), 5, seed, h)
    a[:, (np.arange(w) % 32) < 3] *= 0.7
    return a


def shingles(w=256, h=256, seed=73):
    """cedar shake roof"""
    a = np.zeros((h, w, 3), np.float32)
    r = np.random.default_rng(seed)
    for row in range(8):
        y0 = row * h // 8
        off = (row % 2) * 16
        for k in range(-1, 9):
            x0 = k * 32 + off
            c = C((120, 76, 44)) + r.normal(0, 14, 3)
            a[y0:y0 + h // 8, max(0, x0):max(0, x0 + 30)] = c
        a[y0 + h // 8 - 4:y0 + h // 8] *= 0.55
    return a + N3(w, 1, seed, 5, h)


def glass(n=128):
    a = fill(n, (150, 190, 210), 4, 79)
    x, y = tile_xy(n)
    a += (np.clip(1 - np.abs(x - y - 0.2) * 8, 0, 1) * 60)[..., None]
    return a


def mullion(n=64): return fill(n, (60, 40, 26), 3, 83)


def rubber(n=64): return fill(n, (40, 40, 44), 3, 89)


def jumppad_tex(n=256):
    """splash-launcher pad: teal ring with white arrows and a yellow centre"""
    x, y = tile_xy(n)
    dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    a = np.where((rr < 0.18)[..., None], C((255, 210, 40)), C((20, 170, 200)))
    a = np.where(((rr > 0.42))[..., None], C((250, 250, 250)), a)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(4):
        ang = k * math.pi / 2 + math.pi / 4
        cx, cy = n / 2 + n * 0.3 * math.cos(ang), n / 2 + n * 0.3 * math.sin(ang)
        d.polygon([(cx + 14 * math.cos(ang), cy + 14 * math.sin(ang)), (cx + 12 * math.cos(ang + 2.2), cy + 12 * math.sin(ang + 2.2)),
                   (cx + 12 * math.cos(ang - 2.2), cy + 12 * math.sin(ang - 2.2))], fill=(255, 255, 255))
    return arr(im)


def caustics(n=256, seed=97):
    """bright caustic network (additive on pool tiles, scrolled + turbulent)"""
    a = np.abs(noise(n, 7, seed)) + np.abs(noise(n, 5, seed + 1)) * 0.7
    c = np.clip(1.0 - a * 1.2, 0, 1) ** 3
    return np.repeat((c * 200)[..., None], 3, 2) * C((0.7, 0.95, 1.0))


def water_tex(n=256, seed=101):
    x, y = tile_xy(n)
    f = noise(n, 14, seed) * 0.6 + noise(n, 4, seed + 1) * 0.2
    return C((40, 150, 190)) + f[..., None] * C((20, 30, 30))


def waterfall(w=128, h=512, seed=103):
    x, y = tile_xy(w, h)
    st = noise(w, 1.2, seed, h) * 0.5 + np.sin(x * 2 * math.pi * 9) * 0.2
    streak = np.clip(np.sin(x * 2 * math.pi * 13 + noise(w, 6, seed + 1, h) * 2.0), 0, 1) ** 2
    col = np.zeros((h, w, 3), np.float32) + C((176, 214, 232)) * np.clip(0.7 + 0.3 * st, 0, 1)[..., None]
    al = np.clip(0.12 + 0.45 * streak + 0.15 * st, 0, 0.75) * 255 * np.clip(np.sin(x * math.pi) * 3, 0, 1)
    return col, al


def spray(w=128, h=256, seed=107):
    """fountain jet (alpha, additive white)"""
    x, y = tile_xy(w, h)
    m = np.clip(1 - np.abs(x - 0.5) * (2.8 - 1.6 * y), 0, 1) ** 1.2
    al = np.clip(m * (0.55 + 0.45 * noise(w, 2, seed, h)), 0, 1) * 255 * np.clip(y * 6, 0, 1)
    return np.zeros((h, w, 3), np.float32) + C((235, 248, 255)), al


def rope_tex(w=64, h=64):
    x, y = tile_xy(w, h)
    return C((200, 170, 110)) + (np.sin((x + y) * 2 * math.pi * 4) * 30)[..., None]


def bulb(n=32, col=(255, 200, 120)):
    x, y = tile_xy(n)
    m = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1)[..., None]
    return C(col) * (0.5 + 0.5 * m) + 255 * m ** 3 * 0.5


# ------------------------------------------------------------------------------------------- signs (original art)
def moose_silhouette(d, cx, cy, s, fill):
    """a simple original moose head + antlers silhouette (centre, size)"""
    # head + muzzle
    d.ellipse((cx - 0.30 * s, cy - 0.25 * s, cx + 0.30 * s, cy + 0.30 * s), fill=fill)
    d.polygon([(cx - 0.22 * s, cy + 0.1 * s), (cx + 0.22 * s, cy + 0.1 * s), (cx + 0.16 * s, cy + 0.78 * s), (cx - 0.16 * s, cy + 0.78 * s)], fill=fill)
    d.ellipse((cx - 0.2 * s, cy + 0.58 * s, cx + 0.2 * s, cy + 0.9 * s), fill=fill)
    # ears
    for sg in (-1, 1):
        d.polygon([(cx + sg * 0.25 * s, cy - 0.05 * s), (cx + sg * 0.62 * s, cy + 0.05 * s), (cx + sg * 0.3 * s, cy + 0.16 * s)], fill=fill)
        # palmate antler: a broad paddle with tines
        base = (cx + sg * 0.22 * s, cy - 0.18 * s)
        pts = [base, (cx + sg * 0.5 * s, cy - 0.32 * s), (cx + sg * 0.95 * s, cy - 0.38 * s)]
        tips = []
        for k in range(6):
            t = k / 5
            px = cx + sg * (0.95 - 0.55 * t) * s; py = cy - (0.38 + 0.42 * math.sin(t * math.pi * 0.55) + 0.12 * t) * s
            tips += [(px, py), (px - sg * 0.06 * s, py + 0.12 * s)]
        pts += tips + [(cx + sg * 0.36 * s, cy - 0.5 * s), (cx + sg * 0.3 * s, cy - 0.28 * s)]
        d.polygon(pts, fill=fill)


def sign_main(w=1024, h=256):
    """MOOSE MOUNTAIN FALLS: carved wooden sign with a moose and pine trees"""
    a = planks(w, h, 201, (120, 74, 40))
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, w - 7, h - 7), radius=40, outline=(60, 34, 16), width=12)
    moose_silhouette(d, 130, 120, 110, (40, 26, 14))
    for x0 in (w - 210, w - 140, w - 70):
        d.polygon([(x0, 40), (x0 - 40, 150), (x0 + 40, 150)], fill=(30, 90, 50)); d.polygon([(x0, 90), (x0 - 50, 210), (x0 + 50, 210)], fill=(30, 90, 50))
    sz = 92
    while d.textlength('MOOSE MOUNTAIN', font=font(sz, True)) > w - 520 and sz > 20: sz -= 2
    d.text((w / 2 - 20, 88), 'MOOSE MOUNTAIN', font=font(sz, True), fill=(255, 224, 150), anchor='mm', stroke_width=4, stroke_fill=(70, 40, 18))
    d.text((w / 2 - 20, 186), 'F A L L S', font=font(int(sz * 0.95), True), fill=(110, 200, 240), anchor='mm', stroke_width=4, stroke_fill=(20, 40, 80))
    return arr(im)


def sign_board(text, w=512, h=128, bg=(110, 66, 34), fg=(255, 230, 160), serif=True, sub=None):
    a = planks(w, h, 211 + len(text), bg)
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w - 5, h - 5), radius=18, outline=(56, 32, 14), width=8)
    sz = int(h * 0.62) if not sub else int(h * 0.45)
    while d.textlength(text, font=font(sz, serif)) > w - 48 and sz > 10: sz -= 2
    y = h / 2 if not sub else h * 0.38
    d.text((w / 2, y), text, font=font(sz, serif), fill=fg, anchor='mm', stroke_width=3, stroke_fill=(50, 26, 10))
    if sub:
        s2 = int(h * 0.24)
        while d.textlength(sub, font=font(s2)) > w - 48 and s2 > 8: s2 -= 1
        d.text((w / 2, h * 0.76), sub, font=font(s2), fill=(240, 240, 230), anchor='mm')
    return arr(im)


def sign_tiny(w=512, h=128):
    a = planks(w, h, 223, (96, 60, 30))
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=(40, 24, 10), width=8)
    for x0 in (44, w - 44):
        d.polygon([(x0, 18), (x0 - 26, 72), (x0 + 26, 72)], fill=(40, 110, 60)); d.polygon([(x0, 46), (x0 - 32, 108), (x0 + 32, 108)], fill=(40, 110, 60))
    sz = 64
    while d.textlength('TINY TIMBERS', font=font(sz, True)) > w - 140 and sz > 10: sz -= 2
    d.text((w / 2, h / 2), 'TINY TIMBERS', font=font(sz, True), fill=(255, 220, 120), anchor='mm', stroke_width=3, stroke_fill=(40, 20, 6))
    return arr(im)


def sign_depth(text, w=128, h=64):
    """pool deck depth marker tile (black on white)"""
    a = fill(w, (238, 236, 230), 3, 227, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), text, font=font(36), fill=(20, 20, 24), anchor='mm')
    return arr(im)


def sign_nodiving(w=256, h=128):
    a = fill(w, (240, 238, 232), 3, 229, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((3, 3, w - 4, h - 4), outline=(200, 30, 30), width=6)
    d.text((w / 2, h * 0.36), 'NO DIVING', font=font(34), fill=(200, 30, 30), anchor='mm')
    d.text((w / 2, h * 0.72), 'SHALLOW WATER', font=font(22), fill=(30, 30, 30), anchor='mm')
    return arr(im)


def menu_board(w=512, h=256):
    a = fill(w, (30, 32, 30), 4, 233, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(140, 96, 50), width=10)
    d.text((w / 2, 40), 'TRAIL GRUB', font=font(40, True), fill=(255, 210, 110), anchor='mm')
    rows = [('Moose Burger', '9.50'), ('Lumberjack Fries', '4.25'), ('Campfire Pizza', '7.75'), ('Pine Cone Pretzel', '3.50'), ('Hot Cocoa', '2.95')]
    for k, (a_, b_) in enumerate(rows):
        y = 86 + k * 34
        d.text((36, y), a_, font=font(24), fill=(240, 236, 220), anchor='lm'); d.text((w - 36, y), b_, font=font(24), fill=(140, 220, 160), anchor='rm')
    return arr(im)


def mural(w=1024, h=512, seed=241):
    """lodge wall mural: pine forest, mountains and a waterfall in flat painted shapes (original)"""
    x, y = tile_xy(w, h)
    a = lerp(C((120, 190, 230)), C((240, 220, 170)), y[..., None])
    im = img(a); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    d.polygon([(0, 330), (200, 120), (360, 260), (520, 90), (720, 280), (880, 150), (1024, 300), (1024, h), (0, h)], fill=(110, 130, 160))
    d.polygon([(200, 120), (240, 160), (170, 170)], fill=(250, 250, 250)); d.polygon([(520, 90), (570, 140), (480, 150)], fill=(250, 250, 250))
    d.polygon([(860, 300), (900, 300), (930, h), (830, h)], fill=(210, 240, 255))
    d.rectangle((0, 400, w, h), fill=(70, 120, 70))
    for k in range(30):
        x0 = r.integers(0, w); hgt = r.integers(80, 200); y0 = r.integers(380, 470)
        c = (int(30 + r.integers(0, 30)), int(80 + r.integers(0, 40)), int(50 + r.integers(0, 20)))
        d.polygon([(x0, y0 - hgt), (x0 - hgt * 0.32, y0), (x0 + hgt * 0.32, y0)], fill=c)
    moose_silhouette(d, 300, 380, 70, (60, 36, 20))
    return arr(im)


# ------------------------------------------------------------------------------------------- textures
def make_textures(W):
    W.save('deck', flagstone()); W.save('coping', coping()); W.save('pool_tile', pool_tile()); W.save('pool_band', pool_band())
    W.save('lane', lane_line()); W.save('splashpad', splashpad()); W.save('kitchen_tile', kitchen_tile())
    W.save('planks', planks()); W.save('planks_dark', planks(256, 256, 19, (110, 72, 40))); W.save('ceiling', ceiling())
    W.save('glulam', glulam()); W.save('stucco', stucco()); W.save('stucco_green', stucco(256, (120, 180, 80), 33))
    W.save('stucco_cream', stucco(256, (232, 222, 196), 35)); W.save('wainscot', wainscot()); W.save('logwall', logwall())
    W.save('fieldstone', fieldstone()); W.save('rock', rock()); W.save('bark', bark()); W.save('rotten', rotten())
    W.save('metal_white', metal_white()); W.save('metal_dark', metal_dark()); W.save('steel', steel())
    W.save('roof_red', roof_red()); W.save('shingles', shingles()); W.save('glass', glass()); W.save('mullion', mullion())
    W.save('rubber', rubber()); W.save('jumppad', jumppad_tex()); W.save('caustics', caustics()); W.save('water', water_tex())
    s, sa = waterfall(); W.save('waterfall', s, sa)
    s, sa = spray(); W.save('spray', s, sa)
    W.save('sign_main', sign_main()); W.save('sign_grill', sign_board('MOOSE LODGE GRILL', 512, 128))
    W.save('sign_welcome', sign_board('WELCOME', 512, 128, sub='MOOSE MOUNTAIN FALLS WATER PARK'))
    W.save('sign_tiny', sign_tiny()); W.save('sign_peak', sign_board('TIMBER PEAK', 512, 128, (90, 56, 28), sub='YELLOW JACKET  -  GREEN GULCH'))
    W.save('sign_nest', sign_board("EAGLE'S NEST", 512, 128, (80, 50, 26))); W.save('sign_river', sign_board('LAZY BEAR RIVER', 512, 128, (70, 46, 24)))
    W.save('sign_grotto', sign_board('GROTTO', 256, 64, (60, 40, 22)))
    for t in ('3.0', '4.0', '7.0', '1.5'):
        W.save('depth_' + t.replace('.', ''), sign_depth(t + ' FT'))
    W.save('nodiving', sign_nodiving()); W.save('menu', menu_board()); W.save('mural', mural())
    W.save('rope', rope_tex())
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 73)); W.save('water_ed', fill(64, (80, 150, 200), 3, 75))
    W.save('clip_ed', fill(64, (160, 120, 200), 2, 77))
    for nm, c in (('bulb_w', (255, 220, 160)), ('bulb_y', (255, 200, 90))):
        W.save(nm, bulb(col=c))
    W.save('lamp_panel', fill(64, (255, 236, 190), 2, 91))


def lily(n=256, seed=251):
    """floating lily-pad stepping stone: green foam pad with a notch and a pink flower"""
    x, y = tile_xy(n)
    a = fill(n, (60, 150, 60), 6, seed)
    rr = np.hypot(x - 0.5, y - 0.5); th = np.arctan2(y - 0.5, x - 0.5)
    a *= (0.85 + 0.15 * np.cos(th * 18))[..., None]
    notch = (np.abs(th - 0.3) < 0.25) & (rr > 0.08)
    a[notch] = (30, 90, 40)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(6):
        t = k * math.pi / 3
        cx, cy = n * 0.62 + 16 * math.cos(t), n * 0.38 + 16 * math.sin(t)
        d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(250, 140, 190))
    d.ellipse((n * 0.62 - 8, n * 0.38 - 8, n * 0.62 + 8, n * 0.38 + 8), fill=(250, 220, 80))
    return arr(im)


def extra_textures(W):
    W.save('lily', lily()); W.save('lily_side', fill(64, (50, 120, 50), 4, 253))
    W.save('sign_summit', sign_board('SUMMIT DECK', 512, 128, (90, 56, 28), sub='ROOFTOP PATIO  -  MOOSE LODGE GRILL'))


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/moosefalls/moose_textures.py)\n\n"
STEPS = {'deck': None, 'planks': 'woodsteps', 'planks_dark': 'woodsteps', 'glulam': 'woodsteps', 'logwall': 'woodsteps',
         'rotten': 'woodsteps', 'bark': 'woodsteps', 'splashpad': 'softsteps', 'pool_tile': 'splashsteps', 'lane': 'splashsteps',
         'pool_band': 'splashsteps', 'rock': None, 'kitchen_tile': None}
CAUSTIC = {'pool_tile', 'pool_band', 'lane'}


def lm(name, steps=None, extra='', tex=None, caustic=False):
    t = tex or f'textures/{NS}/{name}'
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if caustic:
        s += (f'\t{{\n\t\tmap textures/{NS}/caustics\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.45 0.15 0 0.2\n'
              '\t\ttcMod scale 0.5 0.5\n\t\ttcMod turb 0 0.06 0 0.11\n\t\ttcMod scroll 0.03 0.02\n\t}\n')
    return s + '}\n\n'


def glow(name, light, rgb, extra=''):
    t = f'textures/{NS}/{name}'
    return (f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
            f'\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t}}\n}}\n\n')


def make_shader(W, out, model_shaders):
    S = SH
    special = {'jumppad', 'caustics', 'water', 'waterfall', 'spray', 'nodraw_ns', 'water_ed', 'clip_ed', 'glass', 'lamp_panel',
               'rope'} | {n for n in W.sizes if n.startswith('bulb_')}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm), caustic=nm in CAUSTIC)
    S += lm('jumppad', extra='\tq3map_surfacelight 80\n\tq3map_lightRGB 0.4 0.9 1\n')[:-3] + (
        f'\t{{\n\t\tmap textures/{NS}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.2 0.2 0 0.8\n'
        '\t\ttcMod rotate 60\n\t}\n}\n\n')
    S += glow('lamp_panel', 1600, '1 0.86 0.62')
    for nm in sorted(n for n in W.sizes if n.startswith('bulb_')):
        rgb = {'bulb_w': '1 0.86 0.64', 'bulb_y': '1 0.75 0.4'}[nm]
        S += (f'textures/{NS}/{nm}\n{{\n\tqer_editorimage textures/{NS}/{nm}\n\tq3map_surfacelight 400\n\tq3map_lightRGB {rgb}\n'
              f'\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
              f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S += f'''textures/{NS}/sky
{{
	qer_editorimage env/frost-bite512_ft
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/glass
	q3map_sun 0.75 0.86 1 160 50 40
	q3map_skylight 90 3
	skyparms env/frost-bite512 - -
}}

textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{{
		map textures/{NS}/glass
		blendFunc GL_ONE GL_ONE_MINUS_SRC_COLOR
		rgbGen const ( 0.22 0.26 0.3 )
	}}
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.08 0.08 0.1 )
		tcGen environment
	}}
}}

textures/{NS}/water
{{
	qer_editorimage textures/{NS}/water_ed
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm splashsteps
	q3map_globaltexture
	deformVertexes wave 160 sin 0 2 0 0.4
	cull none
	{{
		map textures/{NS}/water
		blendFunc GL_DST_COLOR GL_ONE
		rgbGen identity
		tcMod scale 0.5 0.5
		tcMod turb 0 0.06 0 0.09
		tcMod scroll 0.01 0.02
	}}
	{{
		map textures/{NS}/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.22 0.24 )
		tcMod scale 0.3 0.3
		tcMod scroll -0.02 0.015
	}}
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.22 0.24 0.26 )
		tcGen environment
	}}
}}

textures/{NS}/water_nodraw
{{
	qer_editorimage textures/{NS}/water_ed
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

textures/{NS}/waterfall
{{
	qer_editorimage textures/{NS}/waterfall
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map textures/{NS}/waterfall.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0.02 -1.3
	}}
	{{
		map textures/{NS}/waterfall.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen const ( 0.25 0.25 0.28 )
		tcMod scale 1.3 1
		tcMod scroll -0.03 -1.9
	}}
}}

textures/{NS}/spray
{{
	qer_editorimage textures/{NS}/spray
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/spray.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen wave sin 0.7 0.3 0 0.9
		tcMod scroll 0 0.6
	}}
}}

textures/{NS}/bucket_dump
{{
	qer_editorimage textures/{NS}/waterfall
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map textures/{NS}/waterfall.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen wave sin -9 10 0 0.0333
		tcMod scroll 0 -2.2
	}}
}}

textures/{NS}/rope
{{
	qer_editorimage textures/{NS}/rope
	surfaceparm nonsolid
	surfaceparm trans
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/rope
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

textures/{NS}/slide_clip
{{
	qer_editorimage textures/{NS}/clip_ed
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm slick
	surfaceparm playerclip
	surfaceparm trans
}}

textures/{NS}/nodraw_ns
{{
	qer_editorimage textures/{NS}/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	surfaceparm nolightmap
}}

'''
    S += model_shaders
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    ms = moose_models.make(out)
    make_shader(W, out, ms)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
