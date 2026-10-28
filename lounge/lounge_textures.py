"""Procedural textures + shader + arena for wop_padlounge (Couch Lock).
All art is original and generated here. make_all(out) writes textures/padlounge/*, models/padlounge/* (lounge_models),
scripts/padlounge.shader and scripts/wop_padlounge.arena (pk3dir layout)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lounge_models

MAP = 'wop_padlounge'
NS = 'padlounge'
LONGNAME = 'Couch Lock'
FOG = ((0.22, 0.22, 0.2), 11000)
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
FONTBI = '/usr/share/fonts/truetype/google-fonts/Poppins-BoldItalic.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
for _f in ('FONTB', 'FONTBI', 'FONTS'):
    if not os.path.exists(globals()[_f]): globals()[_f] = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


# ------------------------------------------------------------------------------------------- helpers
def noise(n, blur, seed, m=None):
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


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def font(sz, f=None): return ImageFont.truetype(f or FONTB, sz)


def text_c(d, xy, text, sz, fill, maxw=None, anchor='mm', stroke=0, stroke_fill=None, f=None):
    ft = font(sz, f)
    while maxw and d.textlength(text, font=ft) > maxw and sz > 8:
        sz -= 2; ft = font(sz, f)
    d.text(xy, text, font=ft, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


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


def hsv_wheel(t):
    """t 0..1 -> saturated rainbow colour"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(t % 1.0, 0.85, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


# ------------------------------------------------------------------------------------------- surfaces
def planks(n=512, seed=1):
    """warm oak floorboards running along x, 4 boards per tile, staggered joints"""
    a = np.zeros((n, n, 3), np.float32)
    rr = np.random.default_rng(seed)
    bh = n // 4
    for k in range(4):
        base = C((150, 100, 60)) * rr.uniform(0.85, 1.12)
        y0 = k * bh
        g = noise(n, 1, seed + k, bh)
        grain = np.sin(np.linspace(0, 1, bh)[:, None] * 30 + g * 2.2 + np.linspace(0, 6, n)[None, :] * 0.4)
        a[y0:y0 + bh] = base + grain[..., None] * 9 + N3(n, 0.7, seed + 10 + k, 5, bh)
        a[y0:y0 + 2] *= 0.55
        j = int(rr.uniform(0.15, 0.85) * n)
        a[y0:y0 + bh, j:j + 2] *= 0.55
    a *= (1 + 0.04 * noise(n, 40, seed + 30))[..., None]
    return a


def shag_rug(n=512, seed=3):
    """70s shag: chunky orange/brown/mustard concentric squares, fluffy noise"""
    yy, xx = np.mgrid[0:n, 0:n] / n
    d = np.maximum(abs(xx - 0.5), abs(yy - 0.5))
    band = (d * 14).astype(int) % 4
    cols = np.array([(196, 96, 34), (120, 62, 30), (220, 160, 50), (160, 80, 36)], np.float32)
    a = cols[band]
    fluff = noise(n, 0.6, seed) * 16 + noise(n, 2, seed + 1) * 10
    a += fluff[..., None]
    return a


def wall_paint(n=256, seed=5):
    return fill(n, (110, 128, 104), 3, seed) + N3(n, 30, seed + 1, 5)


def popcorn(n=256, seed=7):
    a = fill(n, (214, 208, 196), 6, seed)
    a += np.clip(noise(n, 0.8, seed + 2), 0.5, 3)[..., None] * 18
    return a


def corduroy(n=256, col=(150, 132, 52), seed=9, dirn='v'):
    a = np.zeros((n, n, 3), np.float32) + C(col)
    x = np.arange(n)
    ribs = (0.82 + 0.18 * np.sin(x * math.pi / 4) ** 2)
    a *= (ribs[None, :] if dirn == 'v' else ribs[:, None])[..., None]
    a += N3(n, 1, seed, 5) + N3(n, 20, seed + 1, 6)
    return a


def cushion(w=512, h=256, col=(150, 132, 52), seed=11):
    """seat cushion top: corduroy with piping round the edge and a soft dimple shading"""
    a = np.zeros((h, w, 3), np.float32) + C(col)
    x = np.arange(w)
    a *= (0.82 + 0.18 * np.sin(x * math.pi / 4) ** 2)[None, :, None]
    a += N3(w, 1, seed, 5, h)
    yy, xx = np.mgrid[0:h, 0:w]
    ex = np.minimum(xx, w - 1 - xx) / w; ey = np.minimum(yy, h - 1 - yy) / h
    e = np.minimum(ex * 2, ey * 2 * h / w)
    a *= (0.78 + 0.22 * np.clip(e * 10, 0, 1))[..., None]
    pip = (np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) < 7)
    a[pip] = C(col) * 0.7
    return a


def falsa_blanket(n=512, seed=13):
    """striped Mexican falsa blanket: bright stripes across, woven texture"""
    rr = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32)
    y = 0
    palette = [(30, 30, 120), (230, 60, 60), (250, 200, 40), (40, 160, 90), (250, 250, 240), (230, 110, 30), (130, 40, 140), (60, 150, 220)]
    while y < n:
        h = int(rr.choice([6, 10, 16, 28, 40]))
        a[y:y + h] = C(palette[rr.integers(0, len(palette))])
        y += h
    yy, xx = np.mgrid[0:n, 0:n]
    a *= (0.88 + 0.12 * ((xx // 2 + yy // 2) % 2))[..., None]
    a += N3(n, 0.8, seed + 1, 6)
    return a


def walnut(n=256, seed=15, col=(92, 58, 36), rings=14):
    g = noise(n, 2, seed)
    v = np.linspace(0, 1, n)[:, None]
    a = np.zeros((n, n, 3), np.float32) + C(col)
    a += (np.sin((v * rings + g * 0.5) * 2 * math.pi) * 9)[..., None] + N3(n, 0.6, seed + 1, 4)
    return a


def table_top(w=1024, h=512, seed=17):
    """walnut top with coffee rings, a cigarette burn and scattered ash/crumbs (exactly fitted to the table)"""
    a = np.zeros((h, w, 3), np.float32) + C((96, 60, 38))
    g = noise(w, 3, seed, h)
    yy = np.linspace(0, 1, h)[:, None]
    a += (np.sin((yy * 9 + g * 0.4) * 2 * math.pi) * 10)[..., None] + N3(w, 0.6, seed + 1, 4, h)
    a[:, :] *= (1 + 0.03 * noise(w, 50, seed + 2, h))[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    for (x, y, r) in ((150, 380, 46), (190, 350, 44), (820, 120, 50), (640, 420, 40)):
        d.ellipse((x - r, y - r, x + r, y + r), outline=(70, 42, 26), width=5)
    for (x, y) in ((560, 90), (300, 160)):
        d.ellipse((x - 9, y - 6, x + 9, y + 6), fill=(30, 18, 12)); d.ellipse((x - 16, y - 11, x + 16, y + 11), outline=(60, 36, 22), width=3)
    rr = np.random.default_rng(seed + 3)
    for _ in range(220):
        x, y = rr.integers(0, w), rr.integers(0, h); r = rr.uniform(0.6, 1.8)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(150, 146, 136) if rr.uniform() < 0.6 else (70, 120, 50))
    # edge banding shade
    a = arr(im)
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    a *= (0.8 + 0.2 * np.clip(edge / 10, 0, 1))[..., None]
    return a


def book_spines(w=512, h=256, seed=19):
    """a row of book spines (fitted on book-block faces), titles as stripes and blocks"""
    rr = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), np.float32) + 20
    im = img(a); d = ImageDraw.Draw(im)
    x = 0
    cols = [(150, 40, 40), (40, 70, 140), (40, 110, 70), (200, 170, 60), (90, 50, 110), (220, 220, 210), (30, 30, 30), (190, 90, 40), (60, 130, 150)]
    while x < w:
        bw = int(rr.integers(18, 44)); top = int(rr.integers(0, 50))
        c = cols[rr.integers(0, len(cols))]
        d.rectangle((x, top, x + bw - 2, h), fill=c)
        sh = tuple(min(255, v + 70) for v in c)
        for k in range(rr.integers(1, 3)):
            yb = int(rr.integers(top + 20, h - 30))
            d.rectangle((x + 3, yb, x + bw - 5, yb + 5), fill=sh)
        d.rectangle((x + bw // 2 - 3, top + 40, x + bw // 2 + 2, top + 40 + int(rr.integers(40, 110))), fill=sh)
        x += bw
    a = arr(im)
    for x0 in range(0, w):
        pass
    a *= (1 + 0.05 * noise(w, 1, seed + 1, h))[..., None]
    return a


def records(w=512, h=256, seed=23):
    """vinyl record sleeves seen edge on (thin spines) - for the bottom shelf"""
    rr = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), np.float32)
    x = 0
    while x < w:
        bw = min(int(rr.integers(4, 9)), w - x)
        a[:, x:x + bw] = C(hsv_wheel(rr.uniform())) * rr.uniform(0.35, 0.8)
        a[:, min(x + bw - 1, w - 1)] *= 0.4
        x += bw
    return a + N3(w, 0.7, seed + 1, 5, h)


def tv_screen(w=512, h=288, seed=29):
    """psychedelic visualiser frame (scrolls/rotates in the shader)"""
    yy, xx = np.mgrid[0:h, 0:w]
    x = xx / w * 2 - 1; y = yy / h * 2 - 1
    r = np.hypot(x * w / h, y); t = np.arctan2(y, x * w / h)
    v = np.sin(r * 9 - t * 3) * 0.5 + np.sin(x * 7 + y * 5) * 0.3 + np.sin(r * 4 + t * 6) * 0.2
    import colorsys
    hue = (v * 0.5 + 0.5 + r * 0.2) % 1
    rgb = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        rgb[..., c] = 0.5 + 0.5 * np.sin(2 * math.pi * (hue + c / 3))
    rgb *= 230
    return rgb


def speaker_front(w=256, h=1024, seed=31):
    a = fill(w, (26, 24, 24), 3, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    for (cy, r) in ((150, 70), (420, 108), (740, 108)):
        d.ellipse((w / 2 - r - 12, cy - r - 12, w / 2 + r + 12, cy + r + 12), fill=(60, 58, 56))
        d.ellipse((w / 2 - r, cy - r, w / 2 + r, cy + r), fill=(18, 18, 18))
        d.ellipse((w / 2 - r * 0.35, cy - r * 0.35, w / 2 + r * 0.35, cy + r * 0.35), fill=(70, 70, 74))
        for k in range(1, 4):
            rr_ = r * (0.35 + 0.2 * k)
            d.ellipse((w / 2 - rr_, cy - rr_, w / 2 + rr_, cy + rr_), outline=(36, 36, 36), width=2)
    text_c(d, (w / 2, 960), 'PADSOUND', 30, (180, 180, 180))
    return im


def subwoofer(n=512, seed=143):
    a = fill(n, (24, 22, 22), 3, seed)
    im = img(a); d = ImageDraw.Draw(im)
    c = n / 2
    for (r, col) in ((200, (60, 58, 56)), (180, (16, 16, 16)), (80, (54, 54, 58)), (40, (30, 30, 32))):
        d.ellipse((c - r, c - r, c + r, c + r), fill=col)
    for r in (110, 140, 165): d.ellipse((c - r, c - r, c + r, c + r), outline=(34, 34, 34), width=3)
    for (x, y) in ((40, 40), (n - 40, 40), (40, n - 40), (n - 40, n - 40)): d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(120, 120, 124))
    text_c(d, (c, n - 26), 'PADSOUND  BASS', 26, (170, 170, 170))
    return im


def leather(n=256, seed=145, col=(120, 64, 36)):
    a = fill(n, col, 6, seed) + N3(n, 0.6, seed + 2, 6)
    a *= (1 + 0.08 * np.clip(noise(n, 4, seed + 3), -1, 1))[..., None]
    yy, xx = np.mgrid[0:n, 0:n]
    a[(xx % 64 < 3)] *= 0.75                         # stitched panels
    return a


def crate(n=256, seed=147):
    a = np.zeros((n, n, 3), np.float32) + C((230, 110, 30)) + N3(n, 1, seed, 4)
    yy, xx = np.mgrid[0:n, 0:n]
    holes = ((xx % 64) > 10) & ((xx % 64) < 54) & ((yy % 48) > 8) & ((yy % 48) < 40)
    a[holes] = a[holes] * 0.25
    return a


def console_front(w=512, h=128):
    a = fill(w, (28, 28, 32), 2, 33, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((40, 50, 300, 62), fill=(10, 10, 12))
    d.ellipse((440, 40, 470, 70), outline=(60, 200, 255), width=3)
    text_c(d, (380, 96), 'PADSTATION', 22, (140, 140, 150))
    return im


def tent_out(n=256, seed=37):
    a = fill(n, (30, 30, 32), 4, seed)
    a[:, ::32] *= 0.7               # seam lines
    yy, xx = np.mgrid[0:n, 0:n]
    a *= (0.95 + 0.05 * ((xx + yy) % 4 < 2))[..., None]
    return a


def mylar(n=256, seed=39):
    a = np.zeros((n, n, 3), np.float32) + 196 + noise(n, 3, seed)[..., None] * 34 + noise(n, 0.8, seed + 1)[..., None] * 10
    return a * C((1, 1, 1.03))


def tent_door(w=512, h=1024, seed=41):
    """the rolled-up door flap edge with a zipper running round the opening (fitted)"""
    a = tent_out(512, seed)[:h] if h <= 512 else np.concatenate([tent_out(512, seed)] * 2)[:h]
    im = img(a); d = ImageDraw.Draw(im)
    for x in (24, w - 24):
        d.line((x, 120, x, h), fill=(120, 120, 120), width=6)
        for y in range(120, h, 14): d.line((x - 7, y, x + 7, y + 6), fill=(170, 170, 170), width=2)
    return im


def led_panel(w=512, h=512):
    a = np.zeros((h, w, 3), np.float32) + 20
    im = img(a); d = ImageDraw.Draw(im)
    for i in range(16):
        for j in range(16):
            cx, cy = 16 + i * 32, 16 + j * 32
            col = (255, 60, 200) if (i + j) % 3 else (90, 120, 255)
            d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=col)
    return im.filter(ImageFilter.GaussianBlur(1.2))


def pizza_top(n=512, seed=43):
    a = fill(n, (214, 186, 140), 5, seed)
    im = img(a); d = ImageDraw.Draw(im)
    d.ellipse((60, 40, n - 60, n - 80), fill=(196, 40, 36))
    d.ellipse((90, 70, n - 90, n - 110), fill=(240, 230, 210))
    text_c(d, (n / 2, 190), "PADDY'S", 70, (196, 40, 36), maxw=300)
    text_c(d, (n / 2, 270), 'PIZZA', 84, (40, 120, 60), maxw=300)
    text_c(d, (n / 2, 470), 'HOT & FRESH  *  WE DELIVER 24/7', 26, (120, 60, 40))
    # grease spots
    rr = np.random.default_rng(seed + 1)
    a = arr(im)
    for _ in range(5):
        x, y, r = rr.integers(40, n - 40), rr.integers(40, n - 40), rr.uniform(10, 30)
        yy, xx = np.mgrid[0:n, 0:n]
        a *= (1 - 0.18 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / r ** 2))[..., None]
    return a


def pizza_inside(n=512, seed=47):
    """an open box: half-eaten pepperoni pizza (fitted on the box floor)"""
    a = fill(n, (214, 186, 140), 4, seed)
    im = img(a); d = ImageDraw.Draw(im)
    c = n / 2; R = n * 0.45
    # missing slices: draw 5 of 8
    for k in range(8):
        if k in (1, 4, 5): continue
        a0 = k * 45
        d.pieslice((c - R, c - R, c + R, c + R), a0, a0 + 45, fill=(222, 160, 70))
        d.pieslice((c - R * 0.88, c - R * 0.88, c + R * 0.88, c + R * 0.88), a0 + 1, a0 + 44, fill=(240, 200, 90))
        rr = np.random.default_rng(seed + k)
        for _ in range(3):
            t = math.radians(a0 + rr.uniform(8, 37)); rad = R * rr.uniform(0.3, 0.75)
            x, y = c + rad * math.cos(t), c + rad * math.sin(t)
            d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=(170, 40, 30))
        for _ in range(8):
            t = math.radians(a0 + rr.uniform(4, 41)); rad = R * rr.uniform(0.1, 0.85)
            x, y = c + rad * math.cos(t), c + rad * math.sin(t)
            d.ellipse((x - 4, y - 3, x + 4, y + 3), fill=(60, 110, 40))
    a = arr(im) + N3(n, 1, seed + 9, 6)
    return a


def skate_grip(w=128, h=512, seed=53):
    a = fill(w, (30, 30, 30), 14, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    for (y0, y1) in ((60, 70), (h - 70, h - 60)):
        for x in (36, 92):
            d.ellipse((x - 5, y0 - 5, x + 5, y0 + 5), fill=(120, 120, 120))
    return im


def skate_bottom(w=128, h=512, seed=55):
    a = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for c in range(3):
        a[..., c] = 128 + 120 * np.sin(yy / h * 6 + c * 2.1)
    im = img(a); d = ImageDraw.Draw(im)
    text_c(d, (w / 2, h / 2), 'PADBOARDS', 26, (255, 255, 255), stroke=2, stroke_fill=(0, 0, 0))
    return im.rotate(0)


def papers_pack(w=256, h=128):
    a = fill(w, (240, 150, 30), 3, 57, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w - 10, h - 10), outline=(250, 240, 220), width=4)
    text_c(d, (w / 2, 50), 'PAD', 40, (250, 248, 240), f=FONTS)
    text_c(d, (w / 2, 92), 'KING SIZE SLIM', 18, (80, 40, 10))
    return im


def remote(w=128, h=256):
    a = fill(w, (30, 30, 34), 2, 59, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.ellipse((50, 14, 78, 42), fill=(200, 40, 40))
    for i in range(3):
        for j in range(4):
            d.rounded_rectangle((22 + i * 30, 70 + j * 30, 44 + i * 30, 88 + j * 30), 4, fill=(110, 110, 120))
    d.ellipse((36, 200, 92, 250), fill=(80, 80, 90))
    return im


def fridge_front(w=512, h=64):
    a = fill(w, (238, 238, 232), 2, 61, h)
    return a


def curtain(w=256, h=1024, seed=63):
    """tie-dye curtain: spiral rainbow + vertical folds (fitted)"""
    yy, xx = np.mgrid[0:h, 0:w]
    x = xx / w - 0.5; y = yy / h * 4 - 2
    r = np.hypot(x * 2, (y % 1.0 - 0.5) * 2); t = np.arctan2((y % 1.0 - 0.5), x)
    hue = (r * 1.4 + t / (2 * math.pi) * 2 + np.floor(y) * 0.2) % 1
    a = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        a[..., c] = 0.5 + 0.45 * np.sin(2 * math.pi * (hue + c / 3))
    a *= 220
    folds = 0.78 + 0.22 * np.sin(xx / w * math.pi * 6) ** 2
    a *= folds[..., None]
    return a + N3(w, 1, seed, 4, h)


def window_sky():
    n = 64
    return fill(n, (40, 50, 90), 2, 65)


def tapestry(w=1024, h=1024, seed=67):
    """red/yellow/green striped wall hanging with a big leaf in the middle and a fringe"""
    a = np.zeros((h, w, 3), np.float32)
    a[: h // 3] = C((200, 40, 40)); a[h // 3: 2 * h // 3] = C((240, 200, 40)); a[2 * h // 3:] = C((40, 140, 60))
    a += N3(w, 0.8, seed, 6, h)
    im = img(a)
    leaf = lounge_models.fan_leaf(620, (20, 24, 20), (60, 70, 60), seed=71)
    im.paste(leaf, (w // 2 - 310, h // 2 - 330), leaf)
    d = ImageDraw.Draw(im)
    text_c(d, (w / 2, 80), 'ONE LOVE', 90, (250, 240, 200), stroke=4, stroke_fill=(60, 20, 20))
    text_c(d, (w / 2, h - 90), 'STAY CHILL', 80, (250, 240, 200), stroke=4, stroke_fill=(10, 50, 20))
    for x in range(0, w, 16): d.line((x, h - 18, x + 4, h), fill=(240, 230, 200), width=4)
    return im


def poster_420(w=768, h=1024, seed=73):
    """black-light poster: Padman-ish duck silhouette meditating in a neon swirl, PADMAN 420 lettering"""
    yy, xx = np.mgrid[0:h, 0:w]
    x = xx / w - 0.5; y = yy / h - 0.45
    r = np.hypot(x, y * w / h); t = np.arctan2(y, x)
    sw = np.sin(r * 60 - t * 5)
    a = np.zeros((h, w, 3), np.float32) + 12
    a += (sw > 0.6)[..., None] * C((200, 40, 255)) * 0.9
    a += ((sw > -0.2) & (sw < 0.1))[..., None] * C((40, 255, 120)) * 0.8
    a *= (1 - np.clip(r * 1.2, 0, 1))[..., None] * 0.9 + 0.1
    im = img(a); d = ImageDraw.Draw(im)
    # meditating blob figure (head + body + crossed legs), neon orange outline
    cx, cy = w / 2, h * 0.47
    d.ellipse((cx - 150, cy - 40, cx + 150, cy + 190), fill=(10, 10, 12), outline=(255, 150, 30), width=8)
    d.ellipse((cx - 90, cy - 220, cx + 90, cy - 40), fill=(10, 10, 12), outline=(255, 150, 30), width=8)
    d.ellipse((cx - 230, cy + 140, cx + 230, cy + 240), fill=(10, 10, 12), outline=(255, 150, 30), width=8)
    d.arc((cx - 50, cy - 140, cx - 10, cy - 110), 200, 340, fill=(40, 255, 120), width=6)
    d.arc((cx + 10, cy - 140, cx + 50, cy - 110), 200, 340, fill=(40, 255, 120), width=6)
    d.arc((cx - 40, cy - 110, cx + 40, cy - 70), 20, 160, fill=(255, 60, 200), width=6)
    text_c(d, (w / 2, 90), 'PADMAN', 120, (255, 240, 60), stroke=6, stroke_fill=(255, 40, 160), maxw=w - 60)
    text_c(d, (w / 2, h - 110), '4:20', 170, (40, 255, 140), stroke=6, stroke_fill=(120, 20, 200))
    return im


def poster_mush(w=768, h=1024, seed=79):
    """retro mushroom poster: sunset bands, three red toadstools, groovy lettering"""
    a = np.zeros((h, w, 3), np.float32)
    bands = [(250, 210, 120), (250, 170, 80), (240, 120, 70), (200, 70, 80), (130, 50, 100), (60, 40, 90)]
    for k, c in enumerate(bands):
        a[k * h // 6:(k + 1) * h // 6] = C(c)
    im = img(a); d = ImageDraw.Draw(im)
    d.ellipse((w / 2 - 160, h * 0.22, w / 2 + 160, h * 0.22 + 320), fill=(255, 230, 140))
    for (cx, base, s) in ((w * 0.3, h * 0.86, 0.8), (w * 0.62, h * 0.9, 1.1), (w * 0.82, h * 0.88, 0.6)):
        d.rounded_rectangle((cx - 40 * s, base - 260 * s, cx + 40 * s, base), 20, fill=(245, 236, 210))
        d.pieslice((cx - 170 * s, base - 400 * s, cx + 170 * s, base - 140 * s), 180, 360, fill=(220, 40, 40))
        for (ox, oy, r) in ((-80, -300, 22), (10, -340, 28), (90, -290, 18), (-20, -290, 14)):
            d.ellipse((cx + ox * s - r * s, base + oy * s - r * s, cx + ox * s + r * s, base + oy * s + r * s), fill=(255, 250, 240))
    d.rectangle((0, h * 0.9, w, h), fill=(40, 90, 40))
    text_c(d, (w / 2, 100), 'GROOVY', 140, (120, 30, 110), stroke=6, stroke_fill=(255, 240, 200))
    return im


def neon_chill(w=1024, h=256):
    a = np.zeros((h, w, 3), np.float32) + 8
    im = img(a); d = ImageDraw.Draw(im)
    f = font(170, FONTBI)
    glow = Image.new('RGB', (w, h)); dg = ImageDraw.Draw(glow)
    dg.text((w / 2, h / 2), 'chill out', font=f, fill=(255, 40, 200), anchor='mm')
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    im = Image.fromarray(np.clip(arr(im) + arr(glow) * 1.4, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), 'chill out', font=f, fill=(255, 210, 250), anchor='mm', stroke_width=3, stroke_fill=(255, 60, 210))
    return im


def jumppad_tex():
    n = 256
    im = Image.new('RGB', (n, n), (40, 40, 44)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), fill=(60, 200, 90), outline=(20, 60, 30), width=8)
    d.ellipse((34, 34, n - 34, n - 34), fill=(24, 30, 26))
    leaf = lounge_models.fan_leaf(170, (90, 255, 120), (200, 255, 200), seed=83)
    im.paste(leaf, (n // 2 - 85, n // 2 - 92), leaf)
    return im


def mousehole(n=128):
    im = Image.new('RGB', (n, n), (236, 232, 222)); d = ImageDraw.Draw(im)
    d.pieslice((14, 18, n - 14, n * 2 - 18), 180, 360, fill=(8, 6, 6))
    d.rectangle((14, n - 2, n - 14, n), fill=(8, 6, 6))
    return im


def smoke_tex(w=128, h=256, seed=89):
    yy = np.linspace(0, 1, h)[:, None]; xx = np.linspace(-1, 1, w)[None, :]
    wig = noise(w, 6, seed, h) * 0.18
    col = np.exp(-((xx + wig) / (0.25 + 0.5 * (1 - yy))) ** 2) * (1 - np.abs(yy - 0.55) * 1.4).clip(0, 1)
    al = np.clip(col * (0.7 + 0.3 * noise(w, 3, seed + 1, h)) * 190, 0, 200)
    rgb = np.zeros((h, w, 3), np.float32) + 220
    return rgb, al


def fairy_bulb(n=32, col=(255, 200, 80)):
    return np.zeros((n, n, 3), np.float32) + C(col)


def label(text, w=512, h=128, bg=(250, 246, 236), fg=(40, 40, 40), sz=60):
    im = img(fill(w, bg, 2, 97, h)); d = ImageDraw.Draw(im)
    text_c(d, (w / 2, h / 2), text, sz, fg, maxw=w - 20)
    return im


def dust(n=256, seed=101):
    a = fill(n, (120, 84, 52), 4, seed)
    a = planks(n, seed) * 0.55 + C((70, 66, 60)) * 0.45
    a += np.clip(noise(n, 2, seed + 1), 1.0, 3)[..., None] * 25
    return a


# ------------------------------------------------------------------------------------------- write all
def make_textures(W):
    W.save('floor', planks()); W.save('rug', shag_rug()); W.save('wall', wall_paint()); W.save('ceiling', popcorn())
    W.save('baseboard', fill(64, (232, 226, 214), 2, 103)); W.save('dust', dust())
    W.save('couch', corduroy()); W.save('couch_h', corduroy(dirn='h', seed=105)); W.save('cushion', cushion())
    W.save('couch_dark', fill(64, (40, 36, 20), 3, 107)); W.save('blanket', falsa_blanket())
    W.save('walnut', walnut()); W.save('table_top', table_top()); W.save('pine', walnut(256, 109, (170, 128, 82), 9))
    W.save('books', book_spines()); W.save('books2', book_spines(seed=111)); W.save('records', records())
    W.save('book_top', fill(64, (236, 230, 214), 3, 113)); W.save('black', fill(64, (22, 22, 24), 2, 115))
    W.save('tv_screen', tv_screen()); W.save('speaker', speaker_front()); W.save('console', console_front())
    W.save('tent_out', tent_out()); W.save('mylar', mylar()); W.save('tent_door', tent_door()); W.save('led', led_panel())
    W.save('duct', mylar(64, 117) * 0.85); W.save('chrome', fill(64, (200, 204, 210), 3, 119)); W.save('filter', fill(128, (40, 44, 40), 10, 121))
    W.save('pizza_top', pizza_top()); W.save('pizza_side', fill(64, (200, 170, 124), 4, 123)); W.save('pizza_in', pizza_inside())
    W.save('skate_grip', skate_grip()); W.save('skate_bottom', skate_bottom()); W.save('wheel', fill(32, (240, 230, 120), 3, 125))
    W.save('papers', papers_pack()); W.save('remote', remote())
    W.save('fridge', fridge_front()); W.save('fridge_in', fill(128, (232, 236, 238), 2, 127)); W.save('fridge_light', fill(32, (230, 245, 255), 1, 129))
    W.save('curtain', curtain()); W.save('window_frame', fill(64, (236, 232, 222), 2, 131)); W.save('skylight', window_sky())
    W.save('tapestry', tapestry()); W.save('poster_420', poster_420()); W.save('poster_mush', poster_mush()); W.save('neon', neon_chill())
    W.save('jumppad', jumppad_tex()); W.save('rubber', fill(64, (36, 40, 38), 3, 133)); W.save('mousehole', mousehole())
    s, sa = smoke_tex(); W.save('smoke', s, sa)
    for nm, c in (('bulb_r', (255, 80, 80)), ('bulb_g', (90, 255, 110)), ('bulb_b', (90, 140, 255)), ('bulb_y', (255, 220, 90)), ('bulb_p', (230, 100, 255))):
        W.save(nm, fairy_bulb(col=c))
    W.save('lampshade', fill(64, (250, 214, 150), 3, 135)); W.save('cable', fill(32, (20, 20, 20), 2, 137))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 139)); W.save('fog', fill(32, (80, 80, 72), 1, 141))
    W.save('label_snacks', label('SNACKS', fg=(200, 40, 40)))
    W.save('subwoofer', subwoofer()); W.save('leather', leather()); W.save('crate', crate())


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/lounge/lounge_textures.py)\n\n"
STEPS = {'floor': 'woodsteps', 'walnut': 'woodsteps', 'table_top': 'woodsteps', 'pine': 'woodsteps', 'rug': 'carpetsteps',
         'couch': 'softsteps', 'couch_h': 'softsteps', 'cushion': 'softsteps', 'blanket': 'softsteps', 'tent_out': 'softsteps',
         'pizza_top': 'softsteps', 'pizza_side': 'softsteps', 'pizza_in': 'softsteps', 'skate_grip': 'woodsteps', 'book_top': 'softsteps',
         'dust': 'woodsteps', 'mylar': 'softsteps', 'leather': 'softsteps'}
SHINY = {'leather': 0.08, 'floor': 0.06, 'table_top': 0.07, 'walnut': 0.05, 'black': 0.1, 'chrome': 0.4, 'fridge': 0.1, 'fridge_in': 0.06}


def lm(name, steps=None, extra='', shiny=0.0, tex=None):
    t = tex or f'textures/{NS}/{name}'
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if shiny:
        s += (f'\t{{\n\t\tmap models/{NS}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {shiny} {shiny} {shiny} )\n'
              '\t\ttcGen environment\n\t}\n')
    return s + '}\n\n'


def glow(name, light, rgb, extra='', stage_extra='', tex=None):
    """self-lit surface (full bright texture) that also emits light"""
    t = tex or f'textures/{NS}/{name}'
    return (f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
            f'\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {t}\n\t\trgbGen identity\n{stage_extra}\t}}\n}}\n\n')


def make_shader(W, out, model_shaders):
    S = SH
    special = {'tv_screen', 'led', 'fridge_light', 'neon', 'jumppad', 'mousehole', 'smoke', 'nodraw_ns', 'fog', 'skylight', 'poster_420',
               'lampshade', 'cable'} | {n for n in W.sizes if n.startswith('bulb_')}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm), shiny=SHINY.get(nm, 0.0))
    S += lm('jumppad', extra='\tq3map_surfacelight 90\n\tq3map_lightRGB 0.4 1 0.5\n')
    S += lm('mousehole') + lm('cable', extra='\tsurfaceparm nonsolid\n\tsurfaceparm trans\n')
    for nm in ('chrome', 'wheel'):
        S += lm(nm + '_ns', extra='\tsurfaceparm nonsolid\n', tex=f'textures/{NS}/{nm}')
    # black-light poster: lightmapped + a pulsing additive glow of itself
    S += (f'textures/{NS}/poster_420\n{{\n\tqer_editorimage textures/{NS}/poster_420\n\tq3map_surfacelight 40\n\tq3map_lightRGB 0.7 0.3 1\n'
          f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap textures/{NS}/poster_420\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/poster_420\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.55 0.15 0 0.3\n\t}}\n}}\n\n')
    S += glow('tv_screen', 260, '0.6 0.5 1', stage_extra='\t\ttcMod rotate 6\n\t\ttcMod turb 0 0.04 0 0.1\n\t\ttcMod scroll 0.03 0.01\n')
    S += glow('led', 320, '1 0.4 0.9')
    S += glow('fridge_light', 500, '0.85 0.95 1')
    S += glow('lampshade', 300, '1 0.8 0.55')
    S += (f'textures/{NS}/neon\n{{\n\tqer_editorimage textures/{NS}/neon\n\tq3map_surfacelight 200\n\tq3map_lightRGB 1 0.3 0.85\n'
          f'\tsurfaceparm nolightmap\n\t{{\n\t\tmap textures/{NS}/neon\n\t\trgbGen wave inversesawtooth 0.8 0.2 0 0.07\n\t}}\n}}\n\n')
    for nm in sorted(n for n in W.sizes if n.startswith('bulb_')):
        rgb = {'bulb_r': '1 0.35 0.35', 'bulb_g': '0.4 1 0.45', 'bulb_b': '0.4 0.6 1', 'bulb_y': '1 0.85 0.4', 'bulb_p': '0.9 0.45 1'}[nm]
        ph = {'bulb_r': 0, 'bulb_g': 0.25, 'bulb_b': 0.5, 'bulb_y': 0.75, 'bulb_p': 0.4}[nm]
        S += (f'textures/{NS}/{nm}\n{{\n\tqer_editorimage textures/{NS}/{nm}\n\tq3map_surfacelight 700\n\tq3map_lightRGB {rgb}\n'
              f'\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
              f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\trgbGen wave sin 0.75 0.25 {ph} 0.35\n\t}}\n}}\n\n')
    (fr, fg, fb), fd = FOG
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 0.62 0.7 1 55 270 35
	q3map_skylight 30 3
	skyparms env/padlounge/night - -
}}

textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/window_frame
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nonsolid
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.15 0.15 0.18 )
		tcGen environment
	}}
}}

textures/{NS}/smoke
{{
	qer_editorimage textures/{NS}/smoke
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/smoke.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.8 0.8 0.78 )
		alphaGen wave sin 0.7 0.2 0 0.15
		tcMod scroll 0.02 -0.18
		tcMod turb 0 0.08 0 0.12
	}}
}}

textures/{NS}/steam
{{
	qer_editorimage textures/{NS}/smoke
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/smoke.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.75 0.85 0.9 )
		alphaGen wave sin 0.35 0.12 0 0.2
		tcMod scroll 0.03 -0.25
		tcMod turb 0 0.1 0 0.15
	}}
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

textures/{NS}/fog
{{
	qer_editorimage textures/{NS}/fog
	qer_trans 0.3
	surfaceparm fog
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	fogparms ( {fr} {fg} {fb} ) {fd}
}}

'''
    S += model_shaders
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa"\n}\n' % (MAP, LONGNAME))


BALCONY_SCALES = {}


def make_all(out):
    import balcony_models, balcony_textures
    W = TexWriter(out)
    make_textures(W)
    ms = lounge_models.make(out)
    bs, sc = balcony_models.make(out)
    BALCONY_SCALES.clear(); BALCONY_SCALES.update(sc)
    ms += bs + balcony_textures.make(TexWriter(out), out)
    make_shader(W, out, ms)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
