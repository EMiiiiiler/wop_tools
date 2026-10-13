"""Procedural textures + shader + arena for wop_padpinball ("Tilt!" - Padman inside a giant pinball machine).
All art is original and generated here. make_all(out) writes textures/padpinball/*, models/padpinball/* (MD3s),
levelshots-ready shader entries, scripts/padpinball.shader and scripts/wop_padpinball.arena (pk3dir layout).

The playfield is one big painted artwork (PF_W x PF_H pixels) cut into 2 x 2 tiles that build_padpinball.py fits
exactly onto the floor brushes; glowing inserts are separate decals with pulsing additive shaders."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pin_models

MAP = 'wop_padpinball'
NS = 'padpinball'
LONGNAME = 'Tilt! (Padman Pinball)'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTI = '/usr/share/fonts/truetype/google-fonts/Poppins-BoldItalic.ttf'
if not os.path.exists(FONTI): FONTI = FONTB
FONTM = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'

# playfield world rectangle the art covers (must match build_padpinball.py)
FX, FY = 1280, 2432
PF_W, PF_H = 2048, 4096              # art canvas, cut into 2 x 2 tiles of 1024 x 2048


# ----------------------------------------------------------------------------------------------- helpers
def noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, m * 3))
    for i in range(3):
        for j in range(3): big.paste(im, (i * n, j * m))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(big.crop((n, m, 2 * n, 2 * m)), dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def C(c): return np.array(c, np.float32)
def N3(n, blur, seed, amp, m=None): return noise(n, blur, seed, m)[..., None] * amp
def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
def arr(im): return np.asarray(im.convert('RGB'), np.float32)


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def font(sz, f=None): return ImageFont.truetype(f or FONTB, int(sz))


def text_c(d, xy, text, sz, fill, maxw=None, anchor='mm', stroke=0, stroke_fill=None, f=None):
    fo = font(sz, f)
    while maxw and d.textlength(text, font=fo) > maxw and sz > 8:
        sz -= 2; fo = font(sz, f)
    d.text(xy, text, font=fo, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def star(d, x, y, r0, r1, col, n=5, outline=None, rot=0.0, width=1):
    pts = []
    for k in range(2 * n):
        a = -math.pi / 2 + rot + math.pi * k / n
        r = r0 if k % 2 == 0 else r1
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    d.polygon(pts, fill=col, outline=outline, width=width)


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
            im.save(os.path.join(self.dir, name + '.jpg'), quality=90)
        self.sizes[name] = im.size


# ----------------------------------------------------------------------------------------------- the playfield art
def W2P(x, y):
    """world (x, y) -> canvas pixel"""
    return ((x + FX) / (2 * FX) * PF_W, (FY - y) / (2 * FY) * PF_H)


def playfield_art():
    W, H = PF_W, PF_H
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wx = xx / W * 2 * FX - FX; wy = FY - yy / H * 2 * FY
    # base: deep night-purple, red tint on the west (red team) half, blue on the east half
    base = np.zeros((H, W, 3), np.float32) + C((44, 26, 92))
    side = np.clip(wx / 900, -1, 1)[..., None]
    base += np.where(side < 0, -side * C((70, -6, -30)), side * C((-20, 20, 60)))
    base *= (0.85 + 0.15 * (wy[..., None] + FY) / (2 * FY))
    base += noise(W // 4, 3, 1, H // 4).repeat(4, 0).repeat(4, 1)[..., None] * 6
    # sunburst behind the steel ball
    bx, by = 0, -560
    ang = np.arctan2(wy - by, wx - bx); dist = np.hypot(wx - bx, wy - by)
    rays = (np.sin(ang * 16) > 0.2) & (dist < 1100) & (dist > 190)
    fade = np.clip(1 - dist / 1100, 0, 1)[..., None]
    base = np.where(rays[..., None], base * (1 - 0.55 * fade) + C((255, 190, 40)) * 0.55 * fade, base)
    ring = (np.abs(dist - 200) < 14)
    base[ring] = C((255, 230, 120))
    # bumper city: concentric rings round the three pop bumpers
    for (cx, cy) in ((-288, 960), (288, 960), (0, 1300)):
        dd = np.hypot(wx - cx, wy - cy)
        m = (np.sin(dd / 18) > 0.55) & (dd < 300) & (dd > 118)
        base[m] = base[m] * 0.5 + C((60, 220, 255)) * 0.5
    # plunger lanes: brushed metal strips
    lane = (np.abs(wx) > 1120)
    base[lane] = C((150, 150, 160)) + noise(W // 4, 1, 3, H // 4).repeat(4, 0).repeat(4, 1)[lane][:, None] * 10
    im = img(base); d = ImageDraw.Draw(im)
    rr = random.Random(7)
    # sparkles everywhere
    for _ in range(900):
        x, y = rr.uniform(0, W), rr.uniform(0, H)
        r = rr.choice([3, 4, 5, 7, 10])
        star(d, x, y, r, r * 0.42, rr.choice([(255, 255, 255), (255, 230, 90), (120, 220, 255), (255, 120, 220)]), rot=rr.uniform(0, 1))
    def P(x, y): return W2P(x, y)
    def sc(v): return v / (2 * FX) * W      # world units -> pixels (x)
    # big logo between the flippers and the ball (reads upright from the flipper end)
    x, y = P(0, -1280)
    text_c(d, (x, y), 'TILT!', sc(300), (255, 220, 40), stroke=int(sc(16)), stroke_fill=(140, 20, 40), f=FONTI)
    text_c(d, (x, y + sc(190)), 'PAD - O - RAMA', sc(80), (255, 255, 255), stroke=int(sc(6)), stroke_fill=(40, 20, 90))
    # shoot again near the drain, team triangles above the flippers
    x, y = P(0, -1960)
    text_c(d, (x, y), 'SHOOT AGAIN', sc(44), (255, 255, 255), stroke=3, stroke_fill=(30, 10, 60))
    for s, col in ((-1, (230, 40, 50)), (1, (40, 110, 255))):
        tri = [P(s * 300, -1500), P(s * 120, -1720), P(s * 480, -1720)]
        d.polygon(tri, fill=col, outline=(255, 255, 255), width=4)
        x, y = P(s * 300, -1660)
        text_c(d, (x, y), 'RED' if s < 0 else 'BLUE', sc(46), (255, 255, 255), stroke=3, stroke_fill=(20, 10, 40))
    # bumper city label
    x, y = P(0, 1620)
    text_c(d, (x, y), 'BUMPER CITY', sc(90), (120, 240, 255), stroke=int(sc(5)), stroke_fill=(20, 30, 90), f=FONTI)
    # top lane letters
    for k, ch in enumerate('PAD'):
        x, y = P(-192 + 192 * k, 1860)
        d.ellipse((x - sc(48), y - sc(48), x + sc(48), y + sc(48)), fill=(255, 255, 255), outline=(255, 60, 160), width=6)
        text_c(d, (x, y), ch, sc(64), (200, 20, 120))
    # ramp arrows painted on the field toward the ramp entrances
    for s in (-1, 1):
        for k in range(3):
            x, y = P(s * 720, -700 + k * 110)
            w = sc(70)
            d.polygon([(x - w, y + w * 0.5), (x, y - w * 0.6), (x + w, y + w * 0.5), (x, y)], fill=(255, 200, 40), outline=(90, 30, 10))
        x, y = P(s * 720, -880)
        text_c(d, (x, y), 'RAMP', sc(56), (255, 220, 80), stroke=3, stroke_fill=(60, 20, 10))
    # lane labels
    for s in (-1, 1):
        x, y = P(s * 1008, -1300)
        text_c(d, (x, y), 'KICK', sc(38), (255, 255, 255), stroke=2, stroke_fill=(0, 0, 0))
        x, y = P(s * 1200, -1900)
        text_c(d, (x, y), 'SHOOTER', sc(30), (40, 40, 50))
    # under the mini-playfields
    for s, col, t in ((-1, (255, 90, 90), 'RED CORNER'), (1, (110, 170, 255), 'BLUE CORNER')):
        x, y = P(s * 816, 1300)
        text_c(d, (x, y), t, sc(60), col, stroke=3, stroke_fill=(20, 10, 40), maxw=sc(440))
    # outline of the play area edge
    d.rectangle((2, 2, W - 3, H - 3), outline=(20, 10, 30), width=6)
    a = arr(im)
    # subtle clear-coat sheen
    a = a * (0.94 + 0.06 * (np.sin(yy / 40 + xx / 90)[..., None]))
    return img(a)


def playfield_tiles(W_):
    im = playfield_art()
    tw, th = PF_W // 2, PF_H // 2
    for i in range(2):
        for j in range(2):
            W_.save('pf_%d%d' % (i, j), im.crop((i * tw, j * th, (i + 1) * tw, (j + 1) * th)))
    return im


def pf_detail(n=256):
    a = np.zeros((n, n, 3), np.float32) + 128 + N3(n, 0.7, 51, 10) + N3(n, 6, 52, 4)
    return a


# ----------------------------------------------------------------------------------------------- cabinet + metal
def cab_side(n=512):
    """inner side wall art: deep blue with thin pink / cyan pinstripes and stars (kept dark so the playfield pops)"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    a = np.zeros((n, n, 3), np.float32) + C((22, 16, 58)) + N3(n, 30, 8, 6)
    band = np.sin((xx / n) * 2 * math.pi * 4 + (yy / n) * 2 * math.pi * 2)
    a += (band > 0.95)[..., None] * C((90, 18, 64)) + ((band < -0.95)[..., None]) * C((8, 56, 96))
    im = img(a)
    rr = random.Random(9)
    pts = [(rr.uniform(0, n), rr.uniform(0, n), rr.choice([4, 6, 9]), rr.choice([(255, 220, 60), (230, 230, 255), (120, 255, 200)])) for _ in range(30)]
    def f(d, ox, oy):
        for (x, y, r, c) in pts: star(d, x + ox, y + oy, r, r * 0.4, c)
    wrap_draw(im, f)
    return arr(im)


def wood_black(n=256):
    return fill(n, (28, 22, 20), 3, 61) + N3(n, 8, 62, 3) * np.array([1, 0.8, 0.7])


def steel(n=256, seed=63, base=(168, 170, 178)):
    """brushed steel (horizontal streaks)"""
    a = np.zeros((n, n, 3), np.float32) + C(base)
    st = np.asarray(Image.fromarray(((noise(n, 0.6, seed) + 3) * 40).clip(0, 255).astype(np.uint8)).resize((n * 8, n)).crop((0, 0, n, n)), np.float32)
    a += (st / 40 - 3)[..., None] * 9
    return a


def chrome_brush(n=256):
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32) / n
    v = 140 + 100 * np.cos(yy * 9) * np.exp(-((yy - 0.4) ** 2) * 5)
    a = np.stack([v, v, v + 8], -1) + N3(n, 4, 64, 6)
    return a


def rubber(n=128):
    a = fill(n, (24, 24, 26), 3, 65)
    a[n // 2 - 2:n // 2 + 2] += 14
    return a


def plastic(n, col, seed):
    return fill(n, col, 3, seed) + N3(n, 20, seed + 1, 6)


def apron_card(title, lines, w=1024, h=256, col=(255, 236, 160)):
    im = Image.new('RGB', (w, h), (245, 245, 240)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 18), fill=(30, 30, 40)); d.rectangle((0, h - 18, w, h), fill=(30, 30, 40))
    # the card itself
    cx0, cx1 = w * 0.12, w * 0.88
    d.rectangle((cx0, 34, cx1, h - 34), fill=col, outline=(40, 30, 20), width=4)
    text_c(d, (w / 2, 64), title, 36, (150, 20, 30))
    for k, t in enumerate(lines):
        text_c(d, (w / 2, 106 + 34 * k), t, 24, (30, 20, 20), maxw=cx1 - cx0 - 30)
    for (x, y) in ((24, 40), (w - 24, 40), (24, h - 40), (w - 24, h - 40)):
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(190, 190, 196), outline=(90, 90, 96), width=2)
    return arr(im)


def backboard(w=2048, h=512):
    """north wall of the playfield under the backbox: carnival skyline"""
    a = np.zeros((h, w, 3), np.float32)
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32) / h
    a[:] = (C((20, 10, 60)) * (1 - yy[..., None]) + C((160, 40, 120)) * yy[..., None])
    im = img(a); d = ImageDraw.Draw(im)
    rr = random.Random(11)
    for _ in range(120):
        x, y = rr.uniform(0, w), rr.uniform(0, h * 0.5)
        star(d, x, y, 5, 2, (255, 255, 220))
    # tents and a ferris wheel silhouette
    for k, x in enumerate(range(80, w, 330)):
        hh = rr.uniform(140, 220); col = [(230, 50, 60), (250, 200, 40), (40, 120, 230), (60, 200, 110)][k % 4]
        d.polygon([(x, h - 40), (x + 120, h - 40 - hh), (x + 240, h - 40)], fill=col, outline=(255, 255, 255))
        for j in range(4):
            d.line([(x + 120, h - 40 - hh), (x + 30 + 60 * j, h - 40)], fill=(255, 255, 255), width=3)
    cx, cy, R = w * 0.5, h * 0.5, 190
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 230, 120), width=10)
    for k in range(12):
        t = 2 * math.pi * k / 12
        d.line([(cx, cy), (cx + R * math.cos(t), cy + R * math.sin(t))], fill=(255, 230, 120), width=5)
        d.ellipse((cx + R * math.cos(t) - 18, cy + R * math.sin(t) - 18, cx + R * math.cos(t) + 18, cy + R * math.sin(t) + 18),
                  fill=[(230, 50, 60), (250, 200, 40), (40, 120, 230)][k % 3])
    d.rectangle((0, h - 40, w, h), fill=(30, 20, 40))
    text_c(d, (w / 2, h - 20), 'PAD-O-RAMA  *  STEP RIGHT UP  *  PAD-O-RAMA', 26, (255, 230, 120))
    return arr(im)


def target_face(col, w=128, h=192):
    im = Image.new('RGB', (w, h), col); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=(255, 255, 255), width=6)
    for k, r in enumerate((44, 30, 16)):
        d.ellipse((w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r), fill=[(255, 255, 255), col, (255, 255, 255)][k])
    return arr(im)


def sling_top(col, w=256, h=512):
    im = Image.new('RGB', (w, h), col); d = ImageDraw.Draw(im)
    for k in range(9):
        y = 30 + k * 56
        star(d, w / 2 + (30 if k % 2 else -30), y, 22, 9, (255, 255, 255))
    text_c(d, (w / 2, h / 2), '10', 90, (255, 240, 120), stroke=5, stroke_fill=(40, 20, 20))
    return arr(im)


def ramp_deck(col, n=256, seed=70):
    a = fill(n, col, 4, seed)
    xx = np.mgrid[0:n, 0:n][1]
    a[(xx % 128) < 6] = C((240, 240, 250))
    a[((xx + 64) % 128) < 3] = C((255, 255, 255))
    return a


def ramp_side(n=256):
    a = fill(n, (230, 230, 240), 3, 71)
    yy = np.mgrid[0:n, 0:n][0]
    a[(yy % 64) < 8] = C((60, 60, 70))
    return a


def jumppad_tex(n=256, col=(255, 210, 40)):
    im = Image.new('RGB', (n, n), (30, 30, 36)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, n - 6, n - 6), fill=col, outline=(255, 255, 255), width=8)
    d.ellipse((40, 40, n - 40, n - 40), fill=(220, 30, 60))
    text_c(d, (n / 2, n / 2), 'KICK', 54, (255, 255, 255), stroke=3, stroke_fill=(60, 10, 20))
    return arr(im)


def insert(kind, col, n=128):
    """insert decal: bright shape on black (additive), alpha unused"""
    im = Image.new('RGB', (n, n), (0, 0, 0)); d = ImageDraw.Draw(im)
    c2 = tuple(min(255, int(v * 1.0 + 60)) for v in col)
    if kind == 'arrow':
        d.polygon([(n * 0.5, n * 0.06), (n * 0.94, n * 0.62), (n * 0.66, n * 0.62), (n * 0.66, n * 0.94), (n * 0.34, n * 0.94),
                   (n * 0.34, n * 0.62), (n * 0.06, n * 0.62)], fill=col, outline=c2, width=4)
    elif kind == 'circle':
        d.ellipse((6, 6, n - 6, n - 6), fill=col, outline=c2, width=6)
        d.ellipse((n * 0.3, n * 0.3, n * 0.7, n * 0.7), fill=c2)
    elif kind == 'star':
        star(d, n / 2, n / 2, n * 0.46, n * 0.2, col, outline=c2, width=4)
    elif kind == 'tri':
        d.polygon([(n * 0.5, n * 0.08), (n * 0.94, n * 0.9), (n * 0.06, n * 0.9)], fill=col, outline=c2, width=5)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    return arr(im)


def word_insert(text, col, w=256, h=96):
    im = Image.new('RGB', (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w - 4, h - 4), radius=24, fill=tuple(int(v * 0.35) for v in col), outline=col, width=5)
    text_c(d, (w / 2, h / 2), text, 44, (255, 255, 255), maxw=w - 30, stroke=2, stroke_fill=col)
    return arr(im.filter(ImageFilter.GaussianBlur(0.8)))


def spinner_tex(w=256, h=128):
    a = chrome_brush(256)[:h]
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(40, 40, 50), width=6)
    text_c(d, (w / 2, h / 2), 'SPINNER', 44, (220, 30, 50), stroke=2, stroke_fill=(255, 255, 255))
    return arr(im)


# ----------------------------------------------------------------------------------------------- booths
def booth_wall(col, n=256, seed=80):
    a = np.zeros((n, n, 3), np.float32)
    xx = np.mgrid[0:n, 0:n][1]
    a[:] = np.where(((xx // 32) % 2 == 0)[..., None], C(col), C((246, 240, 228)))
    a += N3(n, 1, seed, 4) + N3(n, 10, seed + 1, 5)
    return a


def boardwalk(n=256, seed=82):
    rr = random.Random(seed)
    a = np.zeros((n, n, 3), np.float32)
    for p in range(8):
        tint = C((176, 130, 82)) * rr.uniform(0.85, 1.1)
        a[p * 32:(p + 1) * 32] = tint + N3(n, 0.8, seed + p, 5)[p * 32:(p + 1) * 32]
        a[p * 32] = C((60, 40, 24))
    return a


def booth_sign(text, col, w=512, h=128):
    im = Image.new('RGB', (w, h), tuple(int(v * 0.5) for v in col)); d = ImageDraw.Draw(im)
    d.rectangle((3, 3, w - 4, h - 4), outline=(255, 230, 140), width=5)
    for k in range(18):
        x = 14 + k * (w - 28) / 17
        for y in (12, h - 12):
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 250, 200))
    text_c(d, (w / 2, h / 2), text, 46, (255, 255, 255), maxw=w - 60, stroke=3, stroke_fill=(30, 10, 10))
    return arr(im)


def awning(col, w=256, h=128):
    """scalloped striped awning edge (alpha cut-out)"""
    a = np.zeros((h, w, 3), np.float32)
    xx = np.mgrid[0:h, 0:w][1]
    a[:] = np.where(((xx // 32) % 2 == 0)[..., None], C(col), C((248, 244, 236)))
    al = np.full((h, w), 255.0)
    yy, xx2 = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = (xx2 % 32) - 16
    edge = h - 22 + np.sqrt(np.maximum(0, 16 ** 2 - cx ** 2)) * 1.2
    al[yy > edge] = 0
    return a, al


def toy_block(ch, col, n=256):
    im = Image.new('RGB', (n, n), col); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, n - 11, n - 11), outline=(255, 255, 255), width=12)
    text_c(d, (n / 2, n / 2 + 6), ch, 170, (255, 255, 255), stroke=6, stroke_fill=tuple(int(v * 0.5) for v in col))
    return arr(im) + N3(n, 1, ord(ch), 3)


def tent_top(n=256):
    """tent roof seen from above: yellow/purple pie slices round the centre"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ang = np.arctan2(yy - n / 2, xx - n / 2)
    a = np.where(((np.floor((ang + math.pi) / (2 * math.pi) * 16)) % 2 == 0)[..., None], C((250, 200, 40)), C((140, 50, 190)))
    r = np.hypot(xx - n / 2, yy - n / 2)
    a[r > n / 2 - 8] = C((255, 255, 255))
    return a + N3(n, 1, 86, 3)


def counter(n=256):
    return fill(n, (196, 150, 96), 4, 84) + N3(n, 30, 85, 8)


# ----------------------------------------------------------------------------------------------- underworld
def underside(n=512, seed=90):
    """underside of the playfield: plywood with coil assemblies, wiring runs and lamp sockets"""
    a = fill(n, (178, 146, 104), 5, seed) + N3(n, 30, seed + 1, 10)
    im = img(a); d = ImageDraw.Draw(im)
    rr = random.Random(seed)
    for _ in range(9):          # wiring runs
        y = rr.uniform(0, n); col = rr.choice([(220, 40, 40), (40, 80, 220), (240, 220, 50), (40, 170, 70), (250, 250, 250)])
        pts = [(x, y + 20 * math.sin(x / 40 + y)) for x in range(-10, n + 20, 20)]
        d.line(pts, fill=col, width=5)
    for _ in range(5):          # coils
        x, y = rr.uniform(30, n - 60), rr.uniform(30, n - 60)
        d.rectangle((x, y, x + 50, y + 26), fill=(160, 90, 40), outline=(40, 30, 20), width=2)
        for k in range(8): d.line([(x + 4 + 6 * k, y), (x + 4 + 6 * k, y + 26)], fill=(200, 120, 60), width=2)
    for _ in range(14):         # lamp sockets
        x, y = rr.uniform(0, n), rr.uniform(0, n)
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(70, 70, 76), outline=(30, 30, 30))
    return arr(im)


def plywood(n=256, seed=92, col=(150, 118, 80)):
    a = fill(n, col, 4, seed)
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32)
    a += (np.sin(yy / 6 + noise(n, 8, seed + 1) * 2) * 6)[..., None]
    return a


def galvanised(n=256, seed=94):
    a = fill(n, (150, 156, 162), 5, seed) + N3(n, 3, seed + 1, 10) * np.array([1, 1, 1.05])
    return a


def coins(n=256, seed=96):
    a = fill(n, (90, 80, 60), 4, seed)
    im = img(a); rr = random.Random(seed)
    cs = [(rr.uniform(0, n), rr.uniform(0, n), rr.uniform(10, 18), rr.choice([(200, 170, 80), (190, 190, 196), (170, 120, 70)])) for _ in range(160)]
    def f(d, ox, oy):
        for (x, y, r, c) in cs:
            d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=c, outline=tuple(int(v * 0.6) for v in c), width=2)
            d.ellipse((x + ox - r * 0.6, y + oy - r * 0.6, x + ox + r * 0.6, y + oy + r * 0.6), outline=tuple(int(v * 0.8) for v in c), width=1)
    wrap_draw(im, f)
    return arr(im)


def coin_door(w=256, h=256):
    im = img(galvanised(256)); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(60, 60, 66), width=6)
    for k, x in enumerate((w * 0.3, w * 0.7)):
        d.rectangle((x - 30, 40, x + 30, 120), fill=(30, 30, 34), outline=(200, 30, 40), width=4)
        d.rectangle((x - 4, 54, x + 4, 104), fill=(240, 60, 60))
        text_c(d, (x, 140), '25c', 26, (40, 40, 40))
    text_c(d, (w / 2, 200), 'INSERT COIN', 30, (180, 20, 30))
    return arr(im)


def transformer(n=256, seed=97):
    a = np.zeros((n, n, 3), np.float32) + C((70, 74, 80))
    yy = np.mgrid[0:n, 0:n][0]
    a[(yy % 8) < 1] = C((40, 42, 46))
    return a + N3(n, 1, seed, 4)


def copper(n=256, seed=98):
    a = fill(n, (184, 108, 54), 4, seed)
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32)
    a *= (0.8 + 0.2 * np.abs(np.sin(yy / 2.5)))[..., None]
    return a


def cables(w=128, h=256, seed=99):
    """loose wiring loom sprite (alpha)"""
    a = np.zeros((h, w, 3), np.float32); al = np.zeros((h, w), np.float32)
    im = Image.new('RGB', (w, h)); ia = Image.new('L', (w, h)); d = ImageDraw.Draw(im); da = ImageDraw.Draw(ia)
    rr = random.Random(seed)
    for k in range(9):
        x0 = w / 2 + rr.uniform(-20, 20); col = rr.choice([(220, 40, 40), (40, 80, 220), (240, 220, 50), (40, 170, 70), (240, 240, 240), (30, 30, 30)])
        pts = [(x0 + 18 * math.sin(y / 30 + k), y) for y in range(0, h + 8, 8)]
        d.line(pts, fill=col, width=5); da.line(pts, fill=255, width=5)
    return arr(im), np.asarray(ia, np.float32)


def speaker_cone(n=256):
    im = Image.new('RGB', (n, n), (20, 20, 22)); d = ImageDraw.Draw(im)
    for k in range(10):
        r = n / 2 - 4 - k * 11
        c = 40 + k * 6
        d.ellipse((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), fill=(c, c, c + 4), outline=(10, 10, 10))
    d.ellipse((n / 2 - 22, n / 2 - 22, n / 2 + 22, n / 2 + 22), fill=(170, 170, 180))
    return arr(im)


def circuit(n=256, seed=100):
    a = fill(n, (30, 110, 60), 3, seed)
    im = img(a); d = ImageDraw.Draw(im); rr = random.Random(seed)
    for _ in range(40):
        x, y = rr.uniform(0, n), rr.uniform(0, n)
        if rr.random() < 0.5: d.line([(x, y), (x + rr.uniform(20, 90), y)], fill=(200, 170, 80), width=2)
        else: d.line([(x, y), (x, y + rr.uniform(20, 90))], fill=(200, 170, 80), width=2)
    for _ in range(14):
        x, y = rr.uniform(10, n - 50), rr.uniform(10, n - 30)
        d.rectangle((x, y, x + rr.uniform(20, 46), y + rr.uniform(10, 20)), fill=(20, 20, 24))
    for _ in range(12):
        x, y = rr.uniform(10, n - 10), rr.uniform(10, n - 10)
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=rr.choice([(40, 60, 200), (200, 160, 40), (150, 40, 40)]))
    return arr(im)


# ----------------------------------------------------------------------------------------------- backbox
def dmd_frame(text, sub='', w=512, h=128):
    """orange dot-matrix display frame (dots on black)"""
    src = Image.new('L', (w // 4, h // 4), 0); d = ImageDraw.Draw(src)
    if sub:
        text_c(d, (w // 8, h // 8 - 6), text, 15, 255, maxw=w // 4 - 6, f=FONTM)
        text_c(d, (w // 8, h // 8 + 9), sub, 9, 170, maxw=w // 4 - 6, f=FONTM)
    else:
        text_c(d, (w // 8, h // 8), text, 20, 255, maxw=w // 4 - 6, f=FONTM)
    s = np.asarray(src, np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w]
    cell = np.clip(s[yy // 4, xx // 4] * 2.2, 0, 1)
    dot = (((xx % 4) - 1.5) ** 2 + ((yy % 4) - 1.5) ** 2) < 3.3
    v = np.where(dot, 0.14 + 0.86 * cell, 0.03)
    a = np.stack([v * 255, v * 140, v * 30], -1)
    return a


def backglass(w=2048, h=512):
    """the backbox front above the playfield glass: big logo, carnival art, score lamps (original artwork)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.zeros((h, w, 3), np.float32)
    a[:] = C((30, 10, 70)) * (1 - yy[..., None] / h) + C((120, 20, 90)) * (yy[..., None] / h)
    cx, cy = w / 2, h * 1.1
    ang = np.arctan2(yy - cy, xx - cx)
    a[np.sin(ang * 24) > 0.5] *= 1.35
    im = img(a); d = ImageDraw.Draw(im)
    rr = random.Random(13)
    for _ in range(200):
        star(d, rr.uniform(0, w), rr.uniform(0, h), rr.choice([4, 6, 9]), 2.5, (255, 255, 230))
    # bulb border
    for k in range(60):
        x = 12 + k * (w - 24) / 59
        for y in (12, h - 12): d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 240, 170), outline=(120, 80, 20))
    for k in range(14):
        y = 12 + k * (h - 24) / 13
        for x in (12, w - 12): d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 240, 170), outline=(120, 80, 20))
    text_c(d, (w / 2, h * 0.42), 'TILT!', 250, (255, 220, 40), stroke=14, stroke_fill=(150, 20, 40), f=FONTI)
    text_c(d, (w / 2, h * 0.8), 'PAD - O - RAMA', 74, (255, 255, 255), stroke=6, stroke_fill=(40, 20, 90))
    # ferris wheel left, big top right
    fx, fy, R = w * 0.16, h * 0.5, 170
    d.ellipse((fx - R, fy - R, fx + R, fy + R), outline=(255, 230, 120), width=10)
    for k in range(10):
        t = 2 * math.pi * k / 10
        d.line([(fx, fy), (fx + R * math.cos(t), fy + R * math.sin(t))], fill=(255, 230, 120), width=4)
        d.ellipse((fx + R * math.cos(t) - 20, fy + R * math.sin(t) - 20, fx + R * math.cos(t) + 20, fy + R * math.sin(t) + 20),
                  fill=[(230, 50, 60), (250, 200, 40), (40, 120, 230), (60, 200, 110)][k % 4])
    tx = w * 0.84
    for k in range(8):
        col = (230, 40, 50) if k % 2 == 0 else (250, 245, 235)
        d.polygon([(tx, h * 0.12), (tx - 190 + 47.5 * k, h * 0.86), (tx - 190 + 47.5 * (k + 1), h * 0.86)], fill=col)
    d.rectangle((tx - 200, h * 0.86, tx + 200, h * 0.92), fill=(250, 200, 40))
    # score reels
    for k, sc in enumerate(('PLAYER 1   01,250,000', 'HIGH SCORE  9,999,990')):
        text_c(d, (w * 0.5, h * 0.95 - 0 * k), '', 10, (0, 0, 0))
    return arr(im)


def speaker_panel(w=2048, h=256):
    im = Image.new('RGB', (w, h), (18, 18, 22)); d = ImageDraw.Draw(im)
    for cx in (w * 0.13, w * 0.87):
        for y in range(20, h - 10, 14):
            for x in range(int(cx - 180), int(cx + 180), 14):
                if (x - cx) ** 2 + (y - h / 2) ** 2 < 110 ** 2:
                    d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(50, 50, 56))
    text_c(d, (w * 0.13, h - 22), 'PAD-O-RAMA', 26, (255, 220, 60))
    text_c(d, (w * 0.87, h - 22), 'TILT!', 26, (255, 220, 60))
    return arr(im)


def lampboard(n=256, seed=110):
    a = fill(n, (40, 36, 30), 3, seed)
    im = img(a); d = ImageDraw.Draw(im)
    for y in range(16, n, 32):
        for x in range(16, n, 32):
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 236, 170), outline=(120, 100, 60), width=2)
    return arr(im)


def cab_exterior(n=256, seed=112):
    a = fill(n, (26, 16, 40), 3, seed)
    im = img(a); d = ImageDraw.Draw(im)
    xx = 0
    for k in range(4):
        d.line([(0, 40 + 64 * k), (n, 10 + 64 * k)], fill=(255, 60, 160), width=6)
    return arr(im)


# ----------------------------------------------------------------------------------------------- arcade room
def room_ceiling(n=256, seed=120):
    a = fill(n, (58, 56, 66), 4, seed)
    a[::64] = C((30, 30, 34)); a[:, ::64] = C((30, 30, 34))
    return a


def light_panel(n=128):
    a = np.zeros((n, n, 3), np.float32) + C((236, 240, 255))
    a[::16] = C((200, 206, 220))
    a[:6] = a[-6:] = C((120, 120, 130)); a[:, :6] = a[:, -6:] = C((120, 120, 130))
    return a


def room_wall(w=512, h=256, seed=122):
    a = fill(w, (34, 20, 54), 4, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    for k, c in enumerate(((255, 40, 180), (40, 220, 255))):
        y = 60 + 90 * k
        d.line([(0, y), (w, y)], fill=c, width=6)
    return arr(im)


def marquee(text, col, w=512, h=128):
    im = Image.new('RGB', (w, h), (12, 10, 20)); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=col, width=6)
    text_c(d, (w / 2, h / 2), text, 58, (255, 255, 255), maxw=w - 40, stroke=4, stroke_fill=col, f=FONTI)
    return arr(im)


def neon_sign(text, col, w=512, h=128):
    im = Image.new('RGB', (w, h), (6, 4, 10)); d = ImageDraw.Draw(im)
    text_c(d, (w / 2, h / 2), text, 70, col, maxw=w - 30, f=FONTI)
    im = Image.blend(im.filter(ImageFilter.GaussianBlur(6)), im, 0.6)
    return arr(im)


def poster(title, sub, col, w=256, h=384):
    im = Image.new('RGB', (w, h), col); d = ImageDraw.Draw(im)
    rr = random.Random(hash(title) & 1023)
    for _ in range(30): star(d, rr.uniform(0, w), rr.uniform(0, h), 8, 3, (255, 255, 255))
    d.rectangle((10, 10, w - 11, h - 11), outline=(255, 255, 255), width=5)
    text_c(d, (w / 2, h * 0.3), title, 46, (255, 240, 120), maxw=w - 30, stroke=3, stroke_fill=(20, 10, 30))
    text_c(d, (w / 2, h * 0.62), sub, 22, (255, 255, 255), maxw=w - 30)
    return arr(im)


def cabinet_side(col, n=256, seed=124):
    a = fill(n, col, 4, seed)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(5):
        star(d, 40 + 44 * k, 128 + 40 * math.sin(k), 18, 7, (255, 255, 255))
    return arr(im)


def glass(n=64):
    return fill(n, (180, 200, 220), 2, 130)


# ----------------------------------------------------------------------------------------------- write everything
INSERT_COLS = {'red': (255, 50, 50), 'yellow': (255, 200, 30), 'green': (40, 230, 90), 'blue': (50, 120, 255),
               'white': (230, 230, 255), 'orange': (255, 130, 20), 'purple': (190, 70, 255)}


def make_textures(W):
    playfield_tiles(W)
    W.save('pf_detail', pf_detail())
    W.save('cab_side', cab_side())
    W.save('wood_black', wood_black())
    W.save('steel', steel())
    W.save('steel_dark', steel(seed=66, base=(110, 112, 120)))
    W.save('chrome', chrome_brush())
    W.save('rubber', rubber())
    for nme, col, sd in (('plastic_red', (220, 40, 46), 140), ('plastic_blue', (40, 100, 230), 141), ('plastic_yellow', (250, 200, 40), 142),
                         ('plastic_green', (50, 190, 90), 143), ('plastic_white', (236, 234, 228), 144), ('plastic_purple', (150, 60, 210), 145),
                         ('plastic_orange', (250, 130, 30), 146), ('plastic_black', (30, 30, 34), 147)):
        W.save(nme, plastic(256, col, sd))
    W.save('apron_l', apron_card('HOW TO PLAY', ['Grab the enemy lolly from its corner booth', 'Shoot the ramps to reach the corners',
                                                 'Plunger lanes launch you to the top', 'Drain = Underworld. Find the coin box!']))
    W.save('apron_r', apron_card('PAD-O-RAMA', ['Backbox JACKPOT: take the top-lane kicker', 'Steel ball perch: side kickers', 'Kickbacks in both outlanes',
                                                'TILT! means game over. Have fun!'], col=(190, 230, 255)))
    W.save('apron_side', plastic(256, (240, 238, 232), 148))
    W.save('backboard', backboard())
    for nme, col in (('target_red', (220, 40, 46)), ('target_yellow', (250, 200, 40)), ('target_green', (50, 190, 90)),
                     ('target_blue', (40, 100, 230)), ('target_orange', (250, 130, 30))):
        W.save(nme, target_face(col))
    W.save('sling_red', sling_top((210, 40, 50))); W.save('sling_blue', sling_top((40, 90, 220)))
    W.save('ramp_red', ramp_deck((200, 50, 60))); W.save('ramp_blue', ramp_deck((50, 90, 210), seed=72))
    W.save('ramp_side', ramp_side())
    W.save('jumppad', jumppad_tex())
    W.save('jumppad_blue', jumppad_tex(col=(80, 200, 255)))
    for k in ('arrow', 'circle', 'star', 'tri'):
        for c, rgb in INSERT_COLS.items():
            W.save('ins_%s_%s' % (k, c), insert(k, rgb))
    for nme, t, c in (('ins_jackpot', 'JACKPOT', (255, 200, 30)), ('ins_lock', 'LOCK', (40, 230, 90)), ('ins_extraball', 'EXTRA BALL', (255, 50, 50)),
                      ('ins_special', 'SPECIAL', (190, 70, 255)), ('ins_kickback', 'KICKBACK', (255, 130, 20)), ('ins_lolly', 'LOLLY', (255, 80, 200))):
        W.save(nme, word_insert(t, c))
    W.save('spinner', spinner_tex())
    W.save('booth_red', booth_wall((210, 40, 46))); W.save('booth_blue', booth_wall((40, 90, 220), seed=81))
    W.save('boardwalk', boardwalk())
    W.save('sign_red', booth_sign('RED TEAM PRIZES', (210, 40, 46))); W.save('sign_blue', booth_sign('BLUE TEAM PRIZES', (40, 90, 220)))
    a, al = awning((210, 40, 46)); W.save('awning_red', a, al)
    a, al = awning((40, 90, 220)); W.save('awning_blue', a, al)
    W.save('counter', counter())
    W.save('tent_wall', booth_wall((140, 50, 190), seed=87) * 0 + np.where(((np.mgrid[0:256, 0:256][1] // 32) % 2 == 0)[..., None], C((140, 50, 190)), C((250, 200, 40))) + N3(256, 1, 88, 4))
    W.save('tent_top', tent_top())
    for ch, col in (('A', (220, 50, 50)), ('B', (40, 110, 230)), ('C', (40, 170, 80)), ('D', (250, 170, 30)), ('E', (160, 70, 210))):
        W.save('block_' + ch.lower(), toy_block(ch, col))
    W.save('underside', underside())
    W.save('plywood', plywood())
    W.save('plywood_dark', plywood(seed=93, col=(96, 76, 54)))
    W.save('galvanised', galvanised())
    W.save('coins', coins())
    W.save('coin_door', coin_door())
    W.save('transformer', transformer())
    W.save('copper', copper())
    a, al = cables(); W.save('cables', a, al)
    W.save('speaker_cone', speaker_cone())
    W.save('circuit', circuit())
    frames = [('TILT!', ''), ('JACKPOT', '5,000,000'), ('PAD-O-RAMA', 'PRESS START'), ('INSERT COIN', 'FREE PLAY'), ('LOLLY', 'CAPTURED!'), ('REPLAY', 'AT 10,000,000')]
    for k, (t, s) in enumerate(frames):
        W.save('dmd_%d' % k, dmd_frame(t, s))
    W.save('backglass', backglass())
    W.save('speaker_panel', speaker_panel())
    W.save('lampboard', lampboard())
    W.save('cab_exterior', cab_exterior())
    W.save('room_ceiling', room_ceiling())
    W.save('light_panel', light_panel())
    W.save('room_wall', room_wall())
    for nme, t, c in (('marquee_1', 'DUCK DASH', (255, 200, 30)), ('marquee_2', 'GALAXY PADDLE', (60, 220, 255)),
                      ('marquee_3', 'BALLOON BLAST', (255, 60, 160)), ('marquee_4', 'KILLER DUCKS', (120, 255, 90))):
        W.save(nme, marquee(t, c))
    W.save('neon_arcade', neon_sign('ARCADE', (255, 60, 200)))
    W.save('neon_hiscore', neon_sign('HIGH SCORE', (60, 230, 255)))
    W.save('poster_1', poster('PAD-O-RAMA', 'Now with real lollies!', (150, 30, 90)))
    W.save('poster_2', poster('TOURNAMENT', 'Saturday 8 pm  -  free play', (30, 60, 150)))
    W.save('cabside_1', cabinet_side((40, 30, 90))); W.save('cabside_2', cabinet_side((110, 30, 40), seed=125))
    W.save('glass', glass())
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 131))


# ----------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padpinball/pin_textures.py)\n\n"
STEPS = {'boardwalk': 'woodsteps', 'counter': 'woodsteps', 'plywood': 'woodsteps', 'plywood_dark': 'woodsteps', 'wood_black': 'woodsteps',
         'coins': 'latticesteps', 'galvanised': 'latticesteps', 'steel': 'latticesteps', 'steel_dark': 'latticesteps', 'rubber': 'softsteps'}
for _i in range(2):
    for _j in range(2): STEPS['pf_%d%d' % (_i, _j)] = 'woodsteps'
SHINY = {'chrome': 0.5, 'steel': 0.12, 'steel_dark': 0.1, 'galvanised': 0.1, 'coin_door': 0.1, 'copper': 0.15, 'coins': 0.2,
         'ramp_red': 0.12, 'ramp_blue': 0.12, 'ramp_side': 0.1, 'apron_l': 0.06, 'apron_r': 0.06, 'apron_side': 0.06}
for _c in ('red', 'blue', 'yellow', 'green', 'white', 'purple', 'orange', 'black'): SHINY['plastic_' + _c] = 0.08


def lm(name, steps=None, extra='', shiny=0.0, detail=False):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if detail:
        s += f'\t{{\n\t\tmap textures/{NS}/pf_detail\n\t\tblendFunc GL_DST_COLOR GL_SRC_COLOR\n\t\ttcMod scale 9 4.75\n\t\tdetail\n\t}}\n'
    if shiny:
        s += f'\t{{\n\t\tmap textures/{NS}/chrome\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {shiny} {shiny} {shiny} )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def glow(name, light, rgb, extra='', wave=None, editor=None):
    """self-lit surface (no lightmap) that also lights the room"""
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{editor or name}\n\tsurfaceparm nolightmap\n'
    if light: s += f'\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
    s += extra
    rg = f'rgbGen wave {wave}' if wave else 'rgbGen identity'
    return s + f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\t{rg}\n\t}}\n}}\n\n'


def insert_shader(name, phase, freq=1.0):
    """playfield insert decal: thin nonsolid brush whose top face sits 1u above the floor; additive, pulsing"""
    return f'''textures/{NS}/{name}_p{phase}
{{
	qer_editorimage textures/{NS}/{name}
	qer_trans 0.7
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm nodlight
	polygonOffset
	{{
		map textures/{NS}/{name}
		blendFunc GL_ONE GL_ONE
		rgbGen wave square 0.55 0.45 {phase * 0.25:g} {freq:g}
	}}
}}

'''


def make_shader(W, out):
    S = SH
    special = {'glass', 'nodraw_ns', 'light_panel', 'awning_red', 'awning_blue', 'cables', 'spinner', 'jumppad', 'jumppad_blue',
               'lampboard', 'neon_arcade', 'neon_hiscore', 'marquee_1', 'marquee_2', 'marquee_3', 'marquee_4', 'pf_detail',
               'sign_red', 'sign_blue', 'backglass', 'speaker_panel'}
    special |= {n for n in W.sizes if n.startswith('ins_') or n.startswith('dmd_')}
    for nme in sorted(W.sizes):
        if nme in special: continue
        S += lm(nme, STEPS.get(nme), shiny=SHINY.get(nme, 0), detail=nme.startswith('pf_'))
    S += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.8 0.3\n')
    S += lm('jumppad_blue', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 0.4 0.8 1\n')
    S += glow('light_panel', 1400, '0.92 0.95 1')
    S += glow('lampboard', 500, '1 0.9 0.6')
    S += glow('neon_arcade', 300, '1 0.3 0.8', wave='sin 0.85 0.15 0 0.3')
    S += glow('neon_hiscore', 300, '0.3 0.9 1', wave='sin 0.85 0.15 0.5 0.4')
    for k in range(1, 5): S += glow('marquee_%d' % k, 200, '1 0.95 0.85')
    S += glow('sign_red', 250, '1 0.5 0.4', wave='sin 0.9 0.1 0 1.5')
    S += glow('sign_blue', 250, '0.4 0.6 1', wave='sin 0.9 0.1 0.5 1.5')
    S += glow('backglass', 160, '1 0.8 0.7')
    S += lm('speaker_panel')
    # DMD: animated orange dot matrix
    S += f'''textures/{NS}/dmd
{{
	qer_editorimage textures/{NS}/dmd_0
	surfaceparm nolightmap
	q3map_surfacelight 200
	q3map_lightRGB 1 0.5 0.1
	{{
		animmap 0.35 textures/{NS}/dmd_0 textures/{NS}/dmd_1 textures/{NS}/dmd_2 textures/{NS}/dmd_3 textures/{NS}/dmd_4 textures/{NS}/dmd_5
		rgbGen identity
	}}
}}

'''
    # inserts: 4 phases each so rows chase
    for nme in sorted(n for n in W.sizes if n.startswith('ins_')):
        for ph in range(4):
            S += insert_shader(nme, ph, 0.8 if 'arrow' in nme else 1.1)
    S += f'''textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/glass
	qer_trans 0.35
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	{{
		map textures/{NS}/glass
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/{NS}/chrome
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.07 0.07 0.08 )
		tcGen environment
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
	surfaceparm nolightmap
}}

textures/{NS}/spinner
{{
	qer_editorimage textures/{NS}/spinner
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull disable
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/spinner
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/{NS}/chrome
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.3 0.3 0.3 )
		tcGen environment
	}}
}}

textures/{NS}/cables
{{
	qer_editorimage textures/{NS}/cables.tga
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm alphashadow
	cull disable
	{{
		map textures/{NS}/cables.tga
		alphaFunc GE128
		depthWrite
		rgbGen vertex
	}}
}}

'''
    for team in ('red', 'blue'):
        S += f'''textures/{NS}/awning_{team}
{{
	qer_editorimage textures/{NS}/awning_{team}.tga
	qer_trans 0.7
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm alphashadow
	cull disable
	{{
		map textures/{NS}/awning_{team}.tga
		alphaFunc GE128
		depthWrite
		rgbGen vertex
	}}
}}

'''
    S += pin_models.shaders()
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa team ctl ft lps syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    pin_models.make(out)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
