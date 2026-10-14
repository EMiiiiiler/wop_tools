"""Procedural textures + shader + arena for wop_padkitchen (Countertop Clash).
All art is original and generated here. make_all(out) writes textures/padkitchen/*, models/padkitchen/* (kitchen_models),
scripts/padkitchen.shader and scripts/wop_padkitchen.arena (pk3dir layout)."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitchen_models

MAP = 'wop_padkitchen'
NS = 'padkitchen'
LONGNAME = 'Countertop Clash'
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


def wrap_draw(im, fn):
    d = ImageDraw.Draw(im); w, h = im.size
    for ox in (-w, 0, w):
        for oy in (-h, 0, h): fn(d, ox, oy)
    return im


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', NS); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}; self.alpha = set()

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a.convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga')); self.alpha.add(name)
        else:
            im.save(os.path.join(self.dir, name + '.jpg'), quality=92)
        self.sizes[name] = im.size


# ------------------------------------------------------------------------------------------- surfaces
def granite(n=512, seed=1):
    a = fill(n, (34, 34, 36), 3, seed) + N3(n, 6, seed + 2, 6)
    rr = np.random.default_rng(seed + 3)
    im = img(a)
    def f(d, ox, oy):
        for _ in range(0):
            pass
    d = ImageDraw.Draw(im)
    for _ in range(5200):
        x, y = rr.integers(0, n, 2); r = rr.uniform(0.6, 2.4)
        c = rr.choice([0, 1, 2, 3], p=[0.55, 0.25, 0.12, 0.08])
        col = [(70, 70, 72), (120, 118, 112), (180, 176, 168), (14, 14, 16)][c]
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    # faint white veins
    for _ in range(6):
        pts = [(rr.uniform(0, n), rr.uniform(0, n))]
        for k in range(24):
            px, py = pts[-1]; ang = rr.uniform(-0.6, 0.6) + (k * 0.1)
            pts.append((px + 18 * math.cos(ang), py + 18 * math.sin(ang)))
        d.line(pts, fill=(96, 96, 98), width=1)
    return arr(im.filter(ImageFilter.GaussianBlur(0.45)))


def wood(n, base, seed, rings=18, vertical=True, m=None):
    m = m or n
    rr = np.random.default_rng(seed)
    x = np.linspace(0, 1, n)[None, :]; y = np.linspace(0, 1, m)[:, None]
    warp = noise(n, 24, seed, m) * 0.06 + noise(n, 6, seed + 1, m) * 0.01
    g = np.sin((x + warp) * rings * 2 * math.pi + np.sin(y * 3 + seed) * 0.6) if vertical else np.sin((y + warp) * rings * 2 * math.pi)
    a = np.zeros((m, n, 3), np.float32) + C(base)
    a *= (0.88 + 0.08 * g)[..., None]
    a += N3(n, 0.7, seed + 2, 5, m)
    streak = noise(n, 1, seed + 3, m)
    streak = np.asarray(Image.fromarray(np.clip(streak * 40 + 128, 0, 255).astype(np.uint8)).resize((n, m)).filter(ImageFilter.GaussianBlur((0, 6) if vertical else (6, 0))), np.float32) - 128
    return a + streak[..., None] * 0.25


def cab_door(w=256, h=512):
    """cherry raised-panel cabinet door with a brushed nickel knob"""
    a = wood(w, (128, 48, 30), 11, rings=7, m=h)
    im = img(a); d = ImageDraw.Draw(im)
    # frame bevels
    m = 26
    d.rectangle((0, 0, w - 1, h - 1), outline=(70, 24, 14), width=3)
    d.rectangle((m, m, w - m, h - m), outline=(60, 20, 12), width=4)
    d.rectangle((m + 6, m + 6, w - m - 6, h - m - 6), outline=(160, 72, 46), width=3)
    # raised panel (arched top)
    pm = 48
    d.rounded_rectangle((pm, pm + 10, w - pm, h - pm), radius=26, outline=(66, 22, 12), width=4)
    d.rounded_rectangle((pm + 8, pm + 18, w - pm - 8, h - pm - 8), radius=20, outline=(170, 82, 52), width=2)
    sh = Image.new('L', (w, h), 0); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle((pm + 14, pm + 24, w - pm - 14, h - pm - 14), radius=18, fill=255)
    a = arr(im)
    a *= (1 + 0.06 * (np.asarray(sh.filter(ImageFilter.GaussianBlur(8)), np.float32) / 255))[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    for (cx, cy) in ((w - 40, h // 2),):
        for r, c in ((16, (60, 60, 58)), (14, (176, 172, 160)), (9, (214, 210, 200)), (4, (240, 238, 230))):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    return im


def cab_drawer(w=256, h=128):
    a = wood(w, (128, 48, 30), 12, rings=7, m=h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(70, 24, 14), width=3)
    d.rectangle((14, 14, w - 14, h - 14), outline=(64, 22, 12), width=3)
    d.rectangle((18, 18, w - 18, h - 18), outline=(166, 78, 50), width=2)
    for r, c in ((14, (60, 60, 58)), (12, (176, 172, 160)), (8, (214, 210, 200)), (3, (240, 238, 230))):
        d.ellipse((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r), fill=c)
    return im


def tiles(n, base, k, grout=(150, 136, 112), seed=21, var=12, gw=3):
    a = fill(n, base, 5, seed) + N3(n, 10, seed + 1, 8)
    s = n // k
    rr = np.random.default_rng(seed + 2)
    for i in range(k):
        for j in range(k):
            a[i * s:(i + 1) * s, j * s:(j + 1) * s] *= rr.uniform(1 - var / 100, 1 + var / 100)
    im = img(a); d = ImageDraw.Draw(im)
    for i in range(k + 1):
        d.line((0, i * s, n, i * s), fill=grout, width=gw); d.line((i * s, 0, i * s, n), fill=grout, width=gw)
    return arr(im.filter(ImageFilter.GaussianBlur(0.6)))


def brushed(n, col, seed, dirn='h'):
    """brushed metal: fine streaks along one axis, very little low-frequency mottling"""
    rr = np.random.default_rng(seed)
    rows = rr.normal(size=(n, 1)) * 5 + np.repeat(rr.normal(size=(n // 4, 1)), 4, 0) * 3
    st = np.repeat(rows, n, 1)
    fine = np.asarray(Image.fromarray(np.clip(noise(n, 0.5, seed + 2) * 40 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur((10, 0))), np.float32) - 128
    st = st + fine * 0.35
    if dirn != 'h': st = st.T
    a = np.zeros((n, n, 3), np.float32) + C(col) + st[..., None]
    return a + N3(n, 40, seed + 1, 2.5)


def bread_crumb(n=256, seed=31):
    a = fill(n, (236, 214, 168), 6, seed) + N3(n, 2, seed + 1, 8)
    rr = np.random.default_rng(seed + 2)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(420):
        x, y = rr.integers(0, n, 2); r = rr.uniform(2, 5); e = rr.uniform(0.7, 1.8)
        d.ellipse((x - r * e, y - r, x + r * e, y + r), fill=(196, 170, 124))
        d.ellipse((x - r * e + 1, y - r + 1, x + r * e - 1, y), fill=(214, 190, 142))
    return arr(im.filter(ImageFilter.GaussianBlur(0.5)))


def toast_face(n=256, seed=33):
    """toasted bread face: golden-brown middle, darker toward the crust (texture = one whole slice)"""
    a = bread_crumb(n, seed)
    yy, xx = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.maximum(np.abs(xx), np.abs(yy) * 1.05)
    brown = np.clip((r - 0.08) * 2.2, 0, 1)[..., None]
    a = a * (1 - brown * 0.45) * np.array([0.98, 0.84, 0.62]) + N3(n, 8, seed + 3, 10)
    crust = (r > 0.46)[..., None]
    a = np.where(crust, C((120, 70, 32)) + N3(n, 1, seed + 4, 10), a)
    return a


def crust(n=256, seed=35, col=(150, 88, 38)):
    return fill(n, col, 8, seed) + N3(n, 3, seed + 1, 12) + N3(n, 20, seed + 2, 14)


def baguette(w=512, h=256, seed=37):
    a = crust(w, seed, (196, 132, 56))[:h] if False else (fill(w, (200, 136, 58), 8, seed, h) + N3(w, 3, seed + 1, 12, h) + N3(w, 24, seed + 2, 16, h))
    im = img(a); d = ImageDraw.Draw(im)
    # diagonal scoring slashes (pale, floury)
    for k in range(5):
        x0 = 30 + k * w / 5
        d.line((x0, h * 0.25, x0 + 70, h * 0.75), fill=(236, 210, 150), width=14)
        d.line((x0 + 4, h * 0.25, x0 + 74, h * 0.75), fill=(170, 104, 40), width=3)
    return arr(im.filter(ImageFilter.GaussianBlur(1.2))) + N3(w, 0.8, seed + 3, 5, h)


def plate_top(n=256):
    yy, xx = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.hypot(xx, yy)
    a = np.zeros((n, n, 3), np.float32) + C((240, 240, 236)) + N3(n, 1, 41, 2)
    a = np.where((np.abs(r - 0.43) < 0.018)[..., None], C((40, 80, 170)), a)
    a = np.where((np.abs(r - 0.39) < 0.006)[..., None], C((40, 80, 170)), a)
    a *= (1 - 0.06 * np.clip((0.3 - r) * 4, 0, 1))[..., None]
    return a


def paper_towel(n=256, seed=43):
    a = fill(n, (240, 240, 236), 3, seed)
    yy, xx = np.mgrid[0:n, 0:n]
    q = (np.sin(xx / n * 2 * math.pi * 8) * np.sin(yy / n * 2 * math.pi * 8))
    a += (q * 9)[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, 64):          # perforation line + embossed flowers
        for x in range(0, n, 6): d.point((x, k), fill=(200, 200, 196))
    return arr(im) + N3(n, 0.6, seed + 1, 3)


def cardboard(n=256, seed=45, col=(176, 140, 96)):
    a = fill(n, col, 6, seed)
    a += (np.sin(np.linspace(0, 40 * math.pi, n))[None, :] * 4)[..., None]
    return a + N3(n, 0.7, seed + 1, 6)


def sponge(n=128, seed=47, col=(250, 214, 60)):
    a = fill(n, col, 6, seed)
    rr = np.random.default_rng(seed)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(600):
        x, y = rr.integers(0, n, 2); r = rr.uniform(0.6, 2.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * 0.72) for c in col))
    return arr(im)


def scrub(n=128, seed=49):
    a = fill(n, (40, 120, 150), 6, seed) + N3(n, 0.5, seed + 1, 22)
    return a


def cereal_front(name, tag, bg, fg, mascot, seed):
    """original cereal box art 512x768: name banner, a bowl of cereal, mascot blob, 'NEW!' burst"""
    w, h = 512, 768
    a = fill(w, bg, 4, seed, h)
    yy = np.linspace(0, 1, h)[:, None, None]
    a = a * (1.08 - 0.25 * yy)
    im = img(a); d = ImageDraw.Draw(im)
    # sunburst behind the mascot
    cx, cy = 300, 430
    for k in range(18):
        a0 = k * 20
        d.pieslice((cx - 520, cy - 520, cx + 520, cy + 520), a0, a0 + 10, fill=tuple(min(255, int(c * 1.12 + 10)) for c in bg))
    # name banner
    d.rounded_rectangle((26, 40, w - 26, 230), radius=40, fill=(255, 255, 250), outline=fg, width=10)
    words = name.split()
    if len(words) == 2:
        text_c(d, (w // 2, 100), words[0], 92, fg, maxw=w - 90, f=FONTBI)
        text_c(d, (w // 2, 182), words[1], 92, fg, maxw=w - 90, f=FONTBI)
    else:
        text_c(d, (w // 2, 140), name, 96, fg, maxw=w - 90, f=FONTBI)
    # mascot: a round character with big eyes
    mx, my, mr = 340, 420, 110
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=mascot, outline=(30, 20, 20), width=6)
    for ex in (-38, 38):
        d.ellipse((mx + ex - 30, my - 60, mx + ex + 30, my + 4), fill=(255, 255, 255), outline=(30, 20, 20), width=4)
        d.ellipse((mx + ex - 10, my - 34, mx + ex + 14, my - 6), fill=(20, 20, 30))
    d.arc((mx - 60, my - 10, mx + 60, my + 70), 20, 160, fill=(30, 20, 20), width=8)
    d.ellipse((mx - 160, my + 40, mx - 110, my + 90), fill=mascot, outline=(30, 20, 20), width=5)   # waving hand
    # bowl of cereal
    bx, by = 190, 620
    d.ellipse((bx - 170, by - 60, bx + 170, by + 30), fill=(250, 250, 250), outline=(60, 60, 80), width=5)
    rr = np.random.default_rng(seed)
    for _ in range(40):
        x = bx + rr.uniform(-140, 140); y = by - 20 + rr.uniform(-34, 10)
        c = [(230, 160, 60), (210, 70, 120), (120, 70, 40)][rr.integers(0, 3)]
        d.ellipse((x - 16, y - 10, x + 16, y + 10), fill=c, outline=(90, 50, 20), width=2)
        d.ellipse((x - 5, y - 3, x + 5, y + 3), fill=(250, 250, 240))
    d.chord((bx - 170, by - 60, bx + 170, by + 160), 0, 180, fill=(70, 110, 200), outline=(40, 60, 120), width=5)
    # burst
    pts = []
    for k in range(28):
        r = 70 if k % 2 == 0 else 52
        t = k / 28 * 2 * math.pi
        pts.append((410 + r * math.cos(t), 640 + r * math.sin(t)))
    d.polygon(pts, fill=(255, 220, 40), outline=(200, 60, 30))
    text_c(d, (410, 628), 'NEW!', 30, (200, 30, 30))
    text_c(d, (410, 658), tag, 16, (200, 30, 30), maxw=100)
    d.rectangle((0, h - 40, w, h), fill=fg)
    text_c(d, (w // 2, h - 20), 'NET WT 2000 kg  -  PADMAN APPROVED', 18, (255, 255, 255), maxw=w - 30)
    return im


def cereal_side(bg, fg, name, seed):
    w, h = 256, 768
    a = fill(w, bg, 4, seed, h) * 0.92
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((16, 60, w - 16, 560), fill=(252, 250, 244))
    text_c(d, (w // 2, 90), 'NUTRITION', 26, (20, 20, 20), maxw=w - 50)
    text_c(d, (w // 2, 118), 'FACTS', 26, (20, 20, 20))
    rows = ['Crunch 100%', 'Sugar  lots', 'Fun  9000%', 'Vitamin P  12g', 'Balloons  0g', 'Bubbles  2g', 'Duck  trace']
    for k, t in enumerate(rows):
        d.line((30, 150 + k * 52, w - 30, 150 + k * 52), fill=(20, 20, 20), width=2)
        text_c(d, (36, 176 + k * 52), t, 20, (20, 20, 20), anchor='lm', maxw=w - 70)
    text_c(d, (w // 2, 660), name, 34, fg, maxw=w - 30, f=FONTBI)
    return im


def jumppad_tex():
    n = 256
    im = Image.new('RGB', (n, n), (60, 60, 64)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), fill=(255, 196, 40), outline=(80, 60, 20), width=8)
    d.ellipse((40, 40, n - 40, n - 40), fill=(240, 240, 236))
    for k in range(3):
        y = 150 - k * 40
        d.polygon([(n / 2, y - 40), (n / 2 + 46, y), (n / 2 + 24, y), (n / 2 + 24, y + 18), (n / 2 - 24, y + 18), (n / 2 - 24, y), (n / 2 - 46, y)],
                  fill=(230, 80, 40))
    return im


def flame(w=64, h=128, seed=51):
    """blue gas flame tongue with a soft alpha"""
    yy, xx = np.mgrid[0:h, 0:w] / np.array([h, w], np.float32)[:, None, None].reshape(2, 1, 1)
    yy = np.mgrid[0:h, 0:w][0] / h; xx = np.mgrid[0:h, 0:w][1] / w - 0.5
    shape = np.clip(1 - np.abs(xx) / (0.08 + 0.4 * (yy ** 0.8)), 0, 1) * np.clip((yy - 0.02) * 3, 0, 1)
    col = np.zeros((h, w, 3), np.float32)
    col[..., 0] = 60 + 140 * (1 - yy); col[..., 1] = 110 + 120 * (1 - yy); col[..., 2] = 255
    core = np.clip(1 - np.abs(xx) / (0.03 + 0.15 * yy), 0, 1) * (yy > 0.55)
    col += core[..., None] * 60
    al = shape * 255 * np.clip(yy * 1.4, 0, 1)
    return col[::-1], al[::-1]


def steam(w=128, h=256, seed=53):
    a = np.zeros((h, w, 3), np.float32) + 235
    n1 = noise(w, 10, seed, h); n2 = noise(w, 3, seed + 1, h)
    xx = np.mgrid[0:h, 0:w][1] / w - 0.5; yy = np.mgrid[0:h, 0:w][0] / h
    al = np.clip(0.6 + 0.35 * n1 + 0.1 * n2, 0, 1) * np.clip(1 - np.abs(xx) * 2.4, 0, 1) * np.clip((1 - yy) * 1.5, 0, 1) * np.clip(yy * 4, 0, 1) * 120
    return a, al


def bubbles_tex(w=256, h=128, seed=55):
    """soap foam: clusters of bubbles with rims and highlights (alpha)"""
    a = np.zeros((h, w, 3), np.float32) + 250
    al = Image.new('L', (w, h), 0); da = ImageDraw.Draw(al)
    im = img(a); d = ImageDraw.Draw(im)
    rr = np.random.default_rng(seed)
    for _ in range(90):
        x, y = rr.uniform(10, w - 10), rr.uniform(h * 0.35, h - 4); r = rr.uniform(4, 20) * (1 - (h - y) / h * 0.4)
        if y - r < 0: continue
        da.ellipse((x - r, y - r, x + r, y + r), fill=70)
        da.ellipse((x - r, y - r, x + r, y + r), outline=230, width=2)
        da.ellipse((x - r * 0.55, y - r * 0.6, x - r * 0.15, y - r * 0.25), fill=250)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(170, 210, 240), width=2)
    return arr(im), np.asarray(al, np.float32)


def soapy_water(n=256, seed=57):
    a = fill(n, (130, 170, 190), 4, seed) + N3(n, 8, seed + 1, 18)
    rr = np.random.default_rng(seed + 2)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(140):
        x, y = rr.integers(0, n, 2); r = rr.uniform(2, 10)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(236, 244, 250), width=1)
    return arr(im.filter(ImageFilter.GaussianBlur(0.5)))


def stream_tex(w=64, h=256, seed=59):
    a = np.zeros((h, w, 3), np.float32) + C((200, 225, 240))
    st = noise(w, 1, seed, h)
    st = np.asarray(Image.fromarray(np.clip(st * 50 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur((0.6, 10))), np.float32) - 128
    a += st[..., None] * 1.2
    xx = np.mgrid[0:h, 0:w][1] / w - 0.5
    al = np.clip(1 - np.abs(xx) * 2.2, 0, 1) * (150 + st * 1.5)
    return a, al


def knob_panel(w=1024, h=128):
    a = brushed(256, (180, 182, 186), 61)
    a = np.asarray(img(a).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    for k, cx in enumerate((112, 304, 720, 912)):
        d.ellipse((cx - 44, 20, cx + 44, 108), fill=(40, 40, 44), outline=(20, 20, 22), width=4)
        d.ellipse((cx - 30, 34, cx + 30, 94), fill=(70, 70, 76))
        d.rectangle((cx - 6, 28, cx + 6, 64), fill=(220, 220, 224))
    text_c(d, (w // 2, 64), 'BURNPAD 4000', 44, (30, 30, 34), f=FONTBI)
    return im


def oven_door(w=1024, h=512):
    a = np.asarray(img(brushed(256, (176, 178, 182), 63)).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((120, 120, w - 120, h - 60), radius=20, fill=(30, 22, 18), outline=(60, 60, 64), width=10)
    g = Image.new('L', (w, h), 0); dg = ImageDraw.Draw(g); dg.rounded_rectangle((160, 160, w - 160, h - 100), radius=14, fill=255)
    a = arr(im) + (np.asarray(g.filter(ImageFilter.GaussianBlur(40)), np.float32) / 255)[..., None] * C((180, 90, 30))
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((80, 34, w - 80, 74), radius=20, fill=(210, 212, 216), outline=(110, 110, 116), width=4)   # handle
    return im


def grate(n=256):
    a = fill(n, (40, 38, 36), 4, 65)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, 32):
        d.line((k + 16, 0, k + 16, n), fill=(20, 19, 18), width=8)
    for k in range(0, n, 64):
        d.line((0, k + 32, n, k + 32), fill=(18, 17, 16), width=6)
    return arr(im) + N3(n, 0.7, 66, 6)


def cooktop(n=512):
    a = fill(n, (14, 14, 16), 2, 67) + N3(n, 30, 68, 5)
    im = img(a); d = ImageDraw.Draw(im)
    return arr(im)


def hood_lights(w=512, h=256):
    a = brushed(256, (170, 172, 176), 69)
    a = np.asarray(img(a).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    for cx in (96, 416):
        d.ellipse((cx - 30, 100, cx + 30, 160), fill=(255, 250, 230), outline=(120, 120, 120), width=4)
    for x in range(160, 360, 10):
        d.line((x, 40, x, 220), fill=(70, 72, 76), width=4)
    return im


def window_sky():
    return fill(8, (200, 225, 255), 0, 71)


def wall_paint(n=256, seed=73): return fill(n, (232, 216, 186), 3, seed) + N3(n, 30, seed + 1, 4)


def floor_tile(n=512):
    a = tiles(n, (176, 104, 70), 4, grout=(214, 206, 190), seed=75, var=8, gw=6)
    return a + N3(n, 2, 76, 6)


def painting(w=512, h=384):
    """framed landscape on the far wall: hills, sun, a little padman-ish duck"""
    im = Image.new('RGB', (w, h), (140, 190, 240)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, h), outline=(120, 80, 30), width=30)
    d.ellipse((360, 50, 440, 130), fill=(255, 220, 90))
    d.polygon([(30, 300), (180, 170), (330, 300)], fill=(90, 160, 80))
    d.polygon([(200, 300), (360, 190), (482, 300)], fill=(70, 140, 70))
    d.rectangle((30, 290, 482, 354), fill=(60, 120, 60))
    d.ellipse((230, 250, 290, 300), fill=(255, 220, 40)); d.ellipse((270, 236, 306, 270), fill=(255, 220, 40))
    d.polygon([(304, 250), (324, 256), (304, 262)], fill=(240, 120, 30))
    return im


def fridge_door(w=512, h=1024):
    a = np.asarray(img(brushed(256, (196, 198, 202), 81, 'v')).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    d.line((0, 360, w, 360), fill=(90, 90, 96), width=8)
    d.rounded_rectangle((w - 70, 120, w - 46, 300), radius=10, fill=(230, 230, 234), outline=(120, 120, 126), width=3)
    d.rounded_rectangle((w - 70, 420, w - 46, 760), radius=10, fill=(230, 230, 234), outline=(120, 120, 126), width=3)
    text_c(d, (180, 60), 'FROSTPAD', 52, (60, 64, 70), f=FONTBI)
    # magnets + kid drawings
    rr = np.random.default_rng(82)
    for (x, y, c) in ((80, 470, (250, 240, 220)), (230, 560, (240, 250, 230)), (90, 700, (250, 250, 250))):
        d.rectangle((x, y, x + 120, y + 150), fill=c)
        for k in range(5):
            d.line((x + 10, y + 20 + k * 26, x + 100, y + 20 + k * 26), fill=tuple(int(v) for v in rr.integers(30, 200, 3)), width=3)
    for (x, y, c) in ((140, 465, (230, 40, 40)), (290, 555, (40, 120, 230)), (150, 695, (40, 180, 60))):
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=c)
    return im


def toaster_enamel(col, seed):
    n = 256
    a = fill(n, col, 3, seed) + N3(n, 40, seed + 1, 6)
    return a


def toaster_logo(team, col):
    w, h = 512, 128
    im = Image.new('RGB', (w, h), (210, 212, 216)); d = ImageDraw.Draw(im)
    a = np.asarray(img(brushed(256, (205, 207, 212), 91)).resize((w, h)), np.float32); im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, w - 6, h - 6), radius=30, outline=(120, 120, 126), width=6)
    text_c(d, (w // 2, 50), 'PADTOAST', 64, col, f=FONTBI, stroke=2, stroke_fill=(40, 40, 40))
    text_c(d, (w // 2, 100), f'TEAM {team.upper()} DELUXE  -  4 SLICE', 22, (50, 50, 56))
    return im


def coil_wall(w=256, h=256):
    a = fill(w, (54, 50, 48), 4, 93)
    im = img(a); d = ImageDraw.Draw(im)
    for y in range(24, h, 40):
        pts = [(x, y + 10 * math.sin(x / 8)) for x in range(0, w + 1, 4)]
        d.line(pts, fill=(255, 120, 30), width=5)
    g = arr(im)
    return g


def tea_towel(col):
    w, h = 256, 256
    im = Image.new('RGB', (w, h), (245, 244, 238)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64):
        d.rectangle((k, 0, k + 18, h), fill=col); d.rectangle((0, k, w, k + 18), fill=col)
    return arr(im) + N3(w, 0.6, 95, 6)


def team_mat(col):
    n = 256
    a = fill(n, col, 4, 97)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, 16): d.line((0, k, n, k), fill=tuple(int(c * 0.85) for c in col), width=4)
    return arr(im)


def sugar(n=128, seed=99):
    a = fill(n, (246, 246, 244), 6, seed) + N3(n, 0.5, seed + 1, 10)
    return a


def cereal_edge(name, bg, fg, seed):
    w, h = 1024, 256
    a = fill(w, bg, 4, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 24), fill=fg); d.rectangle((0, h - 24, w, h), fill=fg)
    text_c(d, (w // 2, h // 2), name, 120, (255, 255, 250), maxw=w - 60, f=FONTBI, stroke=4, stroke_fill=fg)
    return im


def clock_tex(n=256):
    im = Image.new('RGB', (n, n), (232, 216, 186)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, n - 6, n - 6), fill=(250, 248, 240), outline=(170, 40, 34), width=14)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        r0, r1 = (88, 104) if k % 3 else (78, 104)
        d.line((n / 2 + r0 * math.sin(a), n / 2 - r0 * math.cos(a), n / 2 + r1 * math.sin(a), n / 2 - r1 * math.cos(a)), fill=(40, 40, 44), width=6 if k % 3 == 0 else 3)
    d.line((n / 2, n / 2, n / 2 + 50 * math.sin(5.4), n / 2 - 50 * math.cos(5.4)), fill=(30, 30, 34), width=9)
    d.line((n / 2, n / 2, n / 2 + 80 * math.sin(2.1), n / 2 - 80 * math.cos(2.1)), fill=(30, 30, 34), width=6)
    d.ellipse((n / 2 - 9, n / 2 - 9, n / 2 + 9, n / 2 + 9), fill=(170, 40, 34))
    text_c(d, (n / 2, n / 2 + 46), 'PADTIME', 18, (120, 120, 126))
    return im


def fridge_double(w=1024, h=2048):
    a = np.asarray(img(brushed(256, (196, 198, 202), 81, 'v')).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    d.line((w // 2, 0, w // 2, int(h * 0.62)), fill=(90, 90, 96), width=8)       # french doors
    d.line((0, int(h * 0.62), w, int(h * 0.62)), fill=(90, 90, 96), width=10)    # freezer drawer below
    for x in (w // 2 - 50, w // 2 + 26):
        d.rounded_rectangle((x, 300, x + 24, 900), radius=10, fill=(230, 230, 234), outline=(120, 120, 126), width=3)
    d.rounded_rectangle((300, int(h * 0.62) + 60, w - 300, int(h * 0.62) + 90), radius=12, fill=(230, 230, 234), outline=(120, 120, 126), width=3)
    text_c(d, (w // 2, 140), 'FROSTPAD', 70, (60, 64, 70), f=FONTBI)
    d.rounded_rectangle((w // 2 + 90, 420, w // 2 + 300, 700), radius=14, fill=(40, 44, 50))   # water/ice dispenser
    d.rectangle((w // 2 + 150, 520, w // 2 + 240, 640), fill=(20, 22, 26))
    rr = np.random.default_rng(82)
    for (x, y, c) in ((120, 520, (250, 240, 220)), (250, 760, (240, 250, 230)), (90, 980, (250, 250, 250)), (330, 300, (255, 240, 240))):
        d.rectangle((x, y, x + 140, y + 180), fill=c)
        for k in range(6):
            d.line((x + 12, y + 22 + k * 26, x + 120, y + 22 + k * 26), fill=tuple(int(v) for v in rr.integers(30, 200, 3)), width=3)
    for (x, y, c) in ((190, 515, (230, 40, 40)), (320, 755, (40, 120, 230)), (160, 975, (40, 180, 60)), (400, 295, (250, 200, 40))):
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=c)
    return im


def mousehole(n=128):
    im = Image.new('RGB', (n, n), (150, 140, 128)); d = ImageDraw.Draw(im)
    a = arr(im) + N3(n, 0.7, 131, 6); im = img(a); d = ImageDraw.Draw(im)
    d.pieslice((16, 20, n - 16, n + 90), 180, 360, fill=(14, 10, 8))
    d.rectangle((16, 75, n - 16, n), fill=(14, 10, 8))
    d.arc((12, 16, n - 12, n + 94), 180, 360, fill=(110, 96, 80), width=5)
    return im


def label_wall(text, w=1024, h=256, bg=(250, 246, 236), fg=(150, 40, 30)):
    im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w - 8, h - 8), radius=40, outline=fg, width=10)
    text_c(d, (w // 2, h // 2), text, 120, fg, maxw=w - 80, f=FONTBI)
    return im


# ------------------------------------------------------------------------------------------- make
def make_textures(W):
    W.save('granite', granite())
    W.save('granite_edge', granite(256, 2) * 1.05)
    W.save('cab_door', cab_door()); W.save('cab_drawer', cab_drawer())
    W.save('cab_wood', wood(256, (124, 46, 28), 13, rings=6)); W.save('cab_inside', wood(256, (176, 120, 84), 14, rings=10))
    W.save('kick', fill(64, (30, 20, 16), 3, 15))
    W.save('backsplash', tiles(256, (212, 180, 136), 4, seed=21) + N3(256, 1, 22, 6))
    W.save('wall', wall_paint()); W.save('ceiling', fill(256, (240, 238, 232), 2, 23))
    W.save('floor', floor_tile()); W.save('baseboard', fill(64, (236, 232, 222), 2, 24))
    W.save('window_frame', fill(64, (244, 244, 240), 2, 25)); W.save('skylight', window_sky())
    W.save('steel', brushed(256, (184, 186, 190), 26)); W.save('steel_v', brushed(256, (184, 186, 190), 27, 'v'))
    W.save('sink', brushed(256, (170, 174, 178), 28)); W.save('drain', drain_tex())
    W.save('cooktop', cooktop()); W.save('grate', grate()); W.save('knobs', knob_panel()); W.save('oven_door', oven_door())
    W.save('hood_lights', hood_lights())
    W.save('toaster_red', toaster_enamel((200, 34, 30), 31)); W.save('toaster_blue', toaster_enamel((34, 84, 200), 32))
    W.save('chrome', brushed(256, (214, 216, 222), 33)); W.save('toaster_base', fill(64, (24, 24, 26), 2, 34))
    W.save('logo_red', toaster_logo('red', (200, 30, 26))); W.save('logo_blue', toaster_logo('blue', (30, 80, 200)))
    W.save('coils', coil_wall()); W.save('toaster_in', fill(128, (60, 56, 54), 4, 35))
    W.save('bread', bread_crumb()); W.save('crust', crust()); W.save('toast', toast_face()); W.save('baguette', baguette())
    W.save('baguette_end', fill(128, (232, 208, 160), 6, 36) + N3(128, 2, 37, 10))
    fr, fa = 'padman_pops', ('PADMAN POPS', 'CRUNCH', (220, 50, 40), (160, 20, 20), (255, 210, 60), 101)
    W.save('cereal1', cereal_front(*fa)); W.save('cereal1_side', cereal_side((220, 50, 40), (160, 20, 20), 'PADMAN POPS', 102))
    W.save('cereal2', cereal_front('DUCKY OS', 'BERRY', (40, 110, 220), (20, 50, 150), (255, 230, 60), 103))
    W.save('cereal2_side', cereal_side((40, 110, 220), (20, 50, 150), 'DUCKY OS', 104))
    W.save('cereal3', cereal_front('CHOCO BUBBLES', 'COCOA', (110, 64, 40), (70, 34, 20), (250, 160, 200), 105))
    W.save('cereal3_side', cereal_side((110, 64, 40), (70, 34, 20), 'CHOCO BUBBLES', 106))
    W.save('cereal1_edge', cereal_edge('PADMAN POPS', (220, 50, 40), (160, 20, 20), 121))
    W.save('cereal2_edge', cereal_edge('DUCKY OS', (40, 110, 220), (20, 50, 150), 122))
    W.save('cereal3_edge', cereal_edge('CHOCO BUBBLES', (110, 64, 40), (70, 34, 20), 123))
    W.save('cardboard', cardboard()); W.save('cardboard_in', cardboard(256, 46, (150, 140, 128)))
    W.save('board', wood(256, (214, 172, 120), 107, rings=12, vertical=False))
    W.save('board_dark', wood(256, (150, 100, 60), 108, rings=10, vertical=False))
    W.save('plate', plate_top()); W.save('plate_side', fill(64, (236, 236, 232), 2, 109))
    W.save('towel', paper_towel()); W.save('core', cardboard(128, 110, (160, 120, 80)))
    W.save('sponge', sponge()); W.save('scrub', scrub())
    W.save('sugar', sugar())
    W.save('jumppad', jumppad_tex()); W.save('rubber', fill(64, (60, 64, 70), 3, 111))
    f, fa_ = flame(); W.save('flame', f, fa_)
    s, sa = steam(); W.save('steam', s, sa)
    b, ba = bubbles_tex(); W.save('foam', b, ba)
    W.save('water', soapy_water())
    st, sta = stream_tex(); W.save('stream', st, sta)
    W.save('painting', painting()); W.save('fridge_side', brushed(256, (180, 182, 186), 112, 'v'))
    W.save('door', door_tex())
    W.save('towel_red', tea_towel((200, 40, 36))); W.save('towel_blue', tea_towel((36, 80, 200)))
    W.save('mat_red', team_mat((190, 50, 44))); W.save('mat_blue', team_mat((44, 84, 190)))
    W.save('lamp', fill(32, (255, 248, 228), 1, 113)); W.save('led', fill(32, (255, 244, 220), 1, 114))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 115))
    W.save('clock', clock_tex()); W.save('fridge', fridge_double()); W.save('mousehole', mousehole())
    W.save('fridge_top', fill(256, (200, 202, 206), 3, 132) + N3(256, 20, 133, 8))
    W.save('fan', fill(64, (236, 232, 222), 2, 116))


def drain_tex(n=128):
    im = Image.new('RGB', (n, n), (170, 174, 178)); d = ImageDraw.Draw(im)
    d.ellipse((8, 8, n - 8, n - 8), fill=(120, 124, 128), outline=(90, 90, 96), width=4)
    d.ellipse((24, 24, n - 24, n - 24), fill=(30, 30, 32))
    for k in range(6):
        t = k / 6 * math.pi
        d.line((n / 2 + 40 * math.cos(t), n / 2 + 40 * math.sin(t), n / 2 - 40 * math.cos(t), n / 2 - 40 * math.sin(t)), fill=(150, 150, 156), width=5)
    return im


def door_tex(w=512, h=1024):
    a = fill(w, (240, 238, 232), 2, 117, h)
    im = img(a); d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in ((60, 60, 452, 480), (60, 540, 452, 964)):
        d.rectangle((x0, y0, x1, y1), outline=(200, 196, 188), width=8)
        d.rectangle((x0 + 20, y0 + 20, x1 - 20, y1 - 20), outline=(255, 255, 252), width=4)
    d.ellipse((440, 500, 480, 540), fill=(196, 160, 60))
    return im


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/kitchen/kitchen_textures.py)\n\n"
STEPS = {'board': 'woodsteps', 'board_dark': 'woodsteps', 'cab_wood': 'woodsteps', 'cab_inside': 'woodsteps', 'bread': 'softsteps',
         'crust': 'softsteps', 'toast': 'softsteps', 'baguette': 'softsteps', 'baguette_end': 'softsteps', 'towel': 'softsteps',
         'sponge': 'softsteps', 'scrub': 'softsteps', 'cardboard': 'softsteps', 'cardboard_in': 'softsteps', 'mat_red': 'carpetsteps',
         'mat_blue': 'carpetsteps', 'sugar': 'sandsteps', 'grate': 'latticesteps'}
SHINY = {'granite': 0.10, 'granite_edge': 0.12, 'steel': 0.22, 'steel_v': 0.22, 'sink': 0.25, 'cooktop': 0.18, 'chrome': 0.4, 'knobs': 0.2,
         'oven_door': 0.18, 'hood_lights': 0.15, 'toaster_red': 0.2, 'toaster_blue': 0.2, 'logo_red': 0.2, 'logo_blue': 0.2,
         'plate': 0.12, 'plate_side': 0.12, 'fridge': 0.12, 'fridge_side': 0.12, 'backsplash': 0.05, 'floor': 0.06}


def lm(name, steps=None, extra='', shiny=0.0):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if shiny:
        s += (f'\t{{\n\t\tmap models/padkitchen/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {shiny} {shiny} {shiny} )\n'
              '\t\ttcGen environment\n\t}\n')
    return s + '}\n\n'


def make_shader(W, out, model_shaders):
    S = SH
    special = {'mousehole', 'flame', 'steam', 'foam', 'water', 'stream', 'nodraw_ns', 'skylight', 'lamp', 'led', 'coils', 'jumppad', 'towel_red',
               'towel_blue'}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm), shiny=SHINY.get(nm, 0.0))
    S += lm('jumppad', extra='\tq3map_surfacelight 120\n') + lm('towel_red', extra='\tcull none\n') + lm('towel_blue', extra='\tcull none\n')
    S += f'''textures/{NS}/coils
{{
	qer_editorimage textures/{NS}/coils
	q3map_surfacelight 260
	q3map_lightRGB 1 0.45 0.15
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/coils
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/{NS}/coils
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.35 0.12 0 0.4
	}}
}}

textures/{NS}/lamp
{{
	qer_editorimage textures/{NS}/lamp
	surfaceparm nolightmap
	q3map_surfacelight 2600
	q3map_lightRGB 1 0.94 0.82
	{{
		map textures/{NS}/lamp
	}}
}}

textures/{NS}/led
{{
	qer_editorimage textures/{NS}/led
	surfaceparm nolightmap
	q3map_surfacelight 900
	q3map_lightRGB 1 0.92 0.78
	{{
		map textures/{NS}/led
	}}
}}

textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 1 0.93 0.78 380 180 38
	q3map_skylight 70 3
	skyparms env/fort-pad512 - -
}}

textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/skylight
	qer_trans 0.3
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	{{
		map models/padkitchen/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.08 0.09 0.1 )
		tcGen environment
	}}
}}

textures/{NS}/mousehole
{{
	qer_editorimage textures/{NS}/mousehole
	surfaceparm nonsolid
	surfaceparm nomarks
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/mousehole
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
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

textures/{NS}/water
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm water
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm splashsteps
	q3map_globaltexture
	tessSize 128
	cull none
	deformVertexes wave 128 sin 0 1.5 0 0.4
	{{
		map textures/{NS}/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.72
		rgbGen identity
		tcMod turb 0 0.03 0 0.06
		tcMod scroll 0.01 0.006
	}}
	{{
		map models/padkitchen/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.12 0.12 )
		tcGen environment
	}}
}}

textures/{NS}/water_inner
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.3
	surfaceparm trans
	surfaceparm water
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nodraw
	surfaceparm nolightmap
}}

textures/{NS}/foam
{{
	qer_editorimage textures/{NS}/foam
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/foam.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod stretch sin 1 0.03 0 0.3
	}}
}}

textures/{NS}/stream
{{
	qer_editorimage textures/{NS}/stream
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/stream.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0 -2.2
	}}
	{{
		map textures/{NS}/stream.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen const ( 0.4 0.45 0.5 )
		tcMod scroll 0.05 -3.1
	}}
}}

textures/{NS}/flame
{{
	qer_editorimage textures/{NS}/flame
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	q3map_surfacelight 300
	q3map_lightRGB 0.4 0.6 1
	{{
		map textures/{NS}/flame.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen wave sin 0.85 0.15 0 4.7
		tcMod stretch triangle 1 0.06 0.3 3.1
	}}
}}

textures/{NS}/steam
{{
	qer_editorimage textures/{NS}/steam
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/steam.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0.03 -0.35
		tcMod turb 0 0.05 0 0.2
	}}
}}

'''
    S += model_shaders
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ctl 1lc ffa team ft"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    ms = kitchen_models.make(out)
    make_shader(W, out, ms)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
