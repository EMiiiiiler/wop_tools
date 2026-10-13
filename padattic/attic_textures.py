"""Procedural textures + shader + arena for wop_padattic ("Attic Express" - a model railway in the attic at night).
All art is original and generated here. make_all(out) writes textures/padattic/*, models/padattic/* (rail_models),
scripts/padattic.shader and scripts/wop_padattic.arena (pk3dir layout).

The sky shader uses WoP's night sky env/pf-garden512 and casts the moonlight (q3map_sun) through the dormer window;
the hull of the map is sky on the inside, so every window looks out at the night."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rail_models

MAP = 'wop_padattic'
NS = 'padattic'
LONGNAME = 'Attic Express'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
SKY = 'env/pf-garden512'
MOON = '0.62 0.72 1 170 270 32'            # q3map_sun r g b intensity yaw elevation (from the south, low)


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


def text_c(d, xy, text, sz, fill, maxw=None, stroke=0, stroke_fill=None, f=None):
    fo = font(sz, f)
    while maxw and d.textlength(text, font=fo) > maxw and sz > 8:
        sz -= 2; fo = font(sz, f)
    d.text(xy, text, font=fo, fill=fill, anchor='mm', stroke_width=stroke, stroke_fill=stroke_fill)


def wrap_draw(im, fn):
    d = ImageDraw.Draw(im); w, h = im.size
    for ox in (-w, 0, w):
        for oy in (-h, 0, h): fn(d, ox, oy)
    return im


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', NS); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a.convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga'))
        else:
            im.save(os.path.join(self.dir, name + '.jpg'), quality=90)
        self.sizes[name] = im.size


# ----------------------------------------------------------------------------------------------- wood
def planks(n, base, nplank, seed, gap=(48, 34, 22), vertical=False, knots=True, dust=0.0, nails=True):
    """boards running along x (rows = planks); dust lightens + desaturates"""
    rr = random.Random(seed)
    a = np.zeros((n, n, 3), np.float32)
    ph = n // nplank
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    for p in range(nplank):
        tint = C(base) * rr.uniform(0.84, 1.1)
        s = rr.randint(0, 999)
        g = noise(n, 0.8, seed * 31 + p)
        streak = noise(n, 6, seed * 17 + p)
        gr = np.asarray(Image.fromarray(((noise(n // 8, 1, s) + 3) * 40).clip(0, 255).astype(np.uint8)).resize((n, n * 4), Image.BICUBIC)
                        .crop((0, 0, n, n)).transpose(Image.Transpose.TRANSPOSE), np.float32) / 40 - 3
        blk = tint + gr[..., None] * 9 + g[..., None] * 3 + streak[..., None] * 5
        y0, y1 = p * ph, (p + 1) * ph
        a[y0:y1] = blk[y0:y1]
        a[y0:y0 + 2] = C(gap); a[y1 - 1:y1] *= 0.8
        cut = rr.randint(0, n - 1)
        a[y0:y1, cut:cut + 2] = C(gap)
        if nails:
            for cx in (cut + 8, cut - 8):
                for cy in (y0 + 6, y1 - 7):
                    a[max(0, cy - 1):cy + 2, max(0, cx - 1) % n:(cx + 2) % n or n] = C((40, 38, 36))
        if knots:
            for _ in range(rr.randint(0, 2)):
                kx, ky = rr.randint(0, n - 1), rr.randint(y0 + 4, y1 - 4)
                d = np.sqrt(((xx - kx) / 2.2) ** 2 + (yy - ky) ** 2)
                m = (d < 6) & (yy >= y0) & (yy < y1)
                a[m] = a[m] * 0.66
    if dust:
        grey = a.mean(2, keepdims=True)
        a = a * (1 - dust) + (grey * 0.6 + 90) * dust + N3(n, 3, seed + 7, 6)
    if vertical: a = a.transpose(1, 0, 2)
    return a


def beam(n=256, seed=11):
    a = planks(n, (124, 88, 56), 1, seed, gap=(124 * 0.8, 88 * 0.8, 56 * 0.8), knots=True, nails=False)
    a += N3(n, 0.6, seed + 2, 5)
    return a


def plywood(n=256, seed=12):
    a = fill(n, (196, 160, 112), 4, seed)
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32)
    a += (np.sin(yy / 5 + noise(n, 10, seed + 1) * 2) * 7)[..., None]
    return a


def ply_edge(n=128, seed=13):
    a = np.zeros((n, n, 3), np.float32)
    for k in range(9):
        y0, y1 = int(k * n / 9), int((k + 1) * n / 9)
        a[y0:y1] = C((206, 170, 120) if k % 2 == 0 else (176, 138, 92))
    return a + N3(n, 1, seed, 5)


def crate(n=256, seed=14):
    a = planks(n, (190, 150, 96), 4, seed, knots=False)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, n - 1, n - 1), outline=(120, 90, 50), width=14)
    d.line([(14, 14), (n - 14, n - 14)], fill=(150, 112, 66), width=16)
    text_c(d, (n * 0.5, n * 0.3), 'PAD TOYS', 30, (70, 40, 20))
    return arr(im)


# ----------------------------------------------------------------------------------------------- layout scenery
def grass(n=256, seed=20):
    """static grass flock: fine fibres in several greens with darker patches"""
    a = fill(n, (78, 124, 56), 6, seed) + N3(n, 24, seed + 1, 14) * C((0.6, 1, 0.4))
    rr = random.Random(seed)
    im = img(a)
    def f(d, ox, oy):
        for _ in range(3800):
            x, y = rr.uniform(0, n), rr.uniform(0, n)
            c = rr.choice([(96, 150, 64), (70, 110, 46), (120, 160, 70), (88, 132, 52), (150, 150, 80)])
            d.line([(x + ox, y + oy), (x + ox + rr.uniform(-2, 2), y + oy + rr.uniform(-3, 3))], fill=c, width=1)
    rr2 = random.Random(seed); wrap_draw(im, f)
    return arr(im)


def ballast(n=256, seed=21):
    a = fill(n, (120, 116, 108), 5, seed)
    im = img(a); rr = random.Random(seed)
    peb = [(rr.uniform(0, n), rr.uniform(0, n), rr.uniform(2.5, 6), rr.choice([(150, 146, 136), (100, 98, 92), (170, 164, 150), (86, 82, 78), (130, 120, 104)])) for _ in range(1400)]
    def f(d, ox, oy):
        for (x, y, r, c) in peb: d.ellipse((x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8), fill=c)
    wrap_draw(im, f)
    return arr(im.filter(ImageFilter.GaussianBlur(0.5)))


def rock(n=256, base=(124, 114, 100), seed=22, moss=False):
    """papier-mache rock: painted strata, dry-brushed highlights, a few dark cracks"""
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32)
    a = fill(n, base, 6, seed) + N3(n, 2, seed + 2, 10) + N3(n, 16, seed + 3, 16)
    a += (np.sin(yy / 9 + noise(n, 14, seed + 4) * 3) * 10)[..., None]
    hi = noise(n, 1.5, seed + 5) > 1.4
    a[hi] = a[hi] * 0.5 + C((220, 214, 200)) * 0.5
    cr = np.abs(noise(n, 4, seed + 6)) < 0.05
    a[cr] *= 0.55
    if moss:
        m = (noise(n, 10, seed + 7) > 0.2)[..., None]
        a = np.where(m, a * 0.5 + C((80, 120, 56)) * 0.5, a)
    return a


def snow(n=256, seed=23):
    return fill(n, (236, 240, 246), 4, seed) + N3(n, 10, seed + 1, 8) * C((0.9, 0.95, 1))


def sand(n=256, seed=24):
    return fill(n, (196, 176, 132), 6, seed) + N3(n, 0.7, seed + 2, 8)


def brick(n=256, base=(150, 60, 44), seed=25):
    a = np.zeros((n, n, 3), np.float32) + C((176, 168, 150))
    rr = random.Random(seed)
    bh, bw = n // 8, n // 4
    for r in range(8):
        off = 0 if r % 2 == 0 else bw // 2
        for c in range(-1, 5):
            x0 = c * bw + off; y0 = r * bh
            col = C(base) * rr.uniform(0.82, 1.15)
            xa, xb = max(0, x0 + 3), min(n, x0 + bw - 3)
            if xb > xa: a[y0 + 3:y0 + bh - 2, xa:xb] = col
    return a + N3(n, 0.8, seed + 1, 8)


def boards_painted(n=256, col=(70, 110, 170), seed=26):
    a = planks(n, col, 6, seed, gap=(30, 34, 44), knots=False, nails=False, vertical=True)
    return a


def paving(n=256, seed=27):
    a = np.zeros((n, n, 3), np.float32) + C((90, 88, 86))
    rr = random.Random(seed)
    for r in range(4):
        for c in range(4):
            a[r * 64 + 2:r * 64 + 62, c * 64 + 2:c * 64 + 62] = C((150, 146, 138)) * rr.uniform(0.9, 1.08)
    return a + N3(n, 0.8, seed, 6)


def roof_tiles(n=256, base=(150, 64, 44), seed=28):
    a = np.zeros((n, n, 3), np.float32)
    rr = random.Random(seed)
    for r in range(8):
        off = 0 if r % 2 == 0 else 16
        for c in range(-1, 9):
            col = C(base) * rr.uniform(0.85, 1.12)
            x0 = c * 32 + off
            for y in range(32):
                shade = 1 - 0.35 * (y / 32)
                xa, xb = max(0, x0 + 1), min(n, x0 + 31)
                if xb > xa: a[r * 32 + y, xa:xb] = col * shade
    return a + N3(n, 0.8, seed + 1, 5)


def plaster(n=256, col=(222, 206, 170), seed=29, timber=True):
    a = fill(n, col, 4, seed) + N3(n, 20, seed + 1, 6)
    if timber:
        im = img(a); d = ImageDraw.Draw(im)
        tc = (86, 58, 36)
        d.rectangle((0, 0, n, 14), fill=tc); d.rectangle((0, n - 14, n, n), fill=tc)
        d.rectangle((0, 0, 14, n), fill=tc); d.rectangle((n // 2 - 7, 0, n // 2 + 7, n), fill=tc)
        d.line([(14, n - 14), (n // 2 - 7, 14)], fill=tc, width=12)
        a = arr(im)
    return a


def house_window(n=128):
    im = Image.new('RGB', (n, n), (255, 210, 120)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, n - 1, n - 1), outline=(70, 46, 30), width=12)
    d.line([(n / 2, 0), (n / 2, n)], fill=(70, 46, 30), width=8); d.line([(0, n / 2), (n, n / 2)], fill=(70, 46, 30), width=8)
    return arr(im)


def door_tex(col, n=128):
    im = Image.new('RGB', (n, 2 * n), col); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, n - 7, 2 * n - 7), outline=tuple(int(v * 0.6) for v in col), width=6)
    for y in (20, n + 10): d.rectangle((20, y, n - 20, y + n - 40), outline=tuple(int(v * 0.7) for v in col), width=4)
    d.ellipse((n - 30, n - 6, n - 18, n + 6), fill=(210, 180, 80))
    return arr(im)


def station_sign(text, col, w=512, h=128):
    im = Image.new('RGB', (w, h), col); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(245, 240, 225), width=6)
    text_c(d, (w / 2, h / 2 + 2), text, 70, (250, 246, 236), maxw=w - 50, f=FONTS)
    return arr(im)


def clock_face(n=128):
    im = Image.new('RGB', (n, n), (40, 34, 30)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, n - 6, n - 6), fill=(248, 240, 214), outline=(180, 150, 80), width=5)
    c = n / 2
    for k in range(12):
        a = 2 * math.pi * k / 12
        d.line([(c + 46 * math.cos(a), c + 46 * math.sin(a)), (c + 54 * math.cos(a), c + 54 * math.sin(a))], fill=(30, 30, 30), width=4)
    d.line([(c, c), (c + 30 * math.cos(-1.9), c + 30 * math.sin(-1.9))], fill=(20, 20, 20), width=5)
    d.line([(c, c), (c + 44 * math.cos(-0.6), c + 44 * math.sin(-0.6))], fill=(20, 20, 20), width=3)
    return arr(im)


def trestle(n=256, seed=30):
    return planks(n, (100, 70, 44), 4, seed, gap=(40, 28, 18), knots=True, nails=True)


# ----------------------------------------------------------------------------------------------- attic junk
def cardboard(n=256, seed=31):
    a = fill(n, (184, 146, 98), 5, seed) + N3(n, 30, seed + 1, 8)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, n // 2 - 14, n, n // 2 + 14), fill=(200, 176, 120))          # packing tape
    return arr(im)


def box_print(text, sub, w=256, h=256, seed=32):
    im = img(cardboard(256, seed)); d = ImageDraw.Draw(im)
    text_c(d, (w / 2, h * 0.36), text, 50, (50, 34, 20), maxw=w - 30)
    text_c(d, (w / 2, h * 0.66), sub, 22, (90, 60, 30), maxw=w - 30)
    d.polygon([(w * 0.8, h * 0.82), (w * 0.86, h * 0.72), (w * 0.92, h * 0.82)], outline=(50, 34, 20))
    text_c(d, (w * 0.86, h * 0.9), 'THIS WAY UP', 12, (50, 34, 20))
    return arr(im)


def trunk(n=256, seed=33):
    a = fill(n, (86, 48, 34), 4, seed) + N3(n, 6, seed + 1, 6)
    im = img(a); d = ImageDraw.Draw(im)
    for x in (40, n - 56): d.rectangle((x, 0, x + 16, n), fill=(60, 36, 24))
    for (x, y) in ((0, 0), (n - 40, 0), (0, n - 40), (n - 40, n - 40)):
        d.rectangle((x, y, x + 40, y + 40), fill=(186, 148, 70), outline=(110, 84, 40), width=3)
    return arr(im)


def lining(n=128, seed=34):
    a = fill(n, (128, 30, 44), 4, seed)
    yy, xx = np.mgrid[0:n, 0:n]
    a[((xx + yy) // 16) % 2 == 0] *= 0.85
    return a


def cobweb(n=256, seed=35):
    """radial web, alpha cut-out"""
    al = Image.new('L', (n, n), 0); d = ImageDraw.Draw(al)
    c = (n * 0.08, n * 0.08)
    rr = random.Random(seed)
    spokes = [math.radians(rr.uniform(-5, 95)) for _ in range(9)]
    for a_ in spokes: d.line([c, (c[0] + n * 1.3 * math.cos(a_), c[1] + n * 1.3 * math.sin(a_))], fill=255, width=2)
    for k in range(1, 12):
        r = k * n / 11
        pts = [(c[0] + r * math.cos(a_) * rr.uniform(0.95, 1.05), c[1] + r * math.sin(a_) * rr.uniform(0.95, 1.05)) for a_ in sorted(spokes)]
        d.line(pts, fill=230, width=1)
    rgb = np.zeros((n, n, 3), np.float32) + 225
    return rgb, np.asarray(al, np.float32)


def powerpack(w=256, h=256):
    im = Image.new('RGB', (w, h), (44, 46, 52)); d = ImageDraw.Draw(im)
    d.rectangle((8, 8, w - 9, h - 9), outline=(120, 120, 128), width=4)
    text_c(d, (w / 2, 34), 'PAD TRAINS', 26, (240, 210, 70))
    d.ellipse((w / 2 - 64, 70, w / 2 + 64, 198), fill=(28, 28, 30), outline=(200, 200, 206), width=5)
    for k in range(9):
        a = math.radians(150 + k * 30)
        d.line([(w / 2 + 52 * math.cos(a), 134 + 52 * math.sin(a)), (w / 2 + 62 * math.cos(a), 134 + 62 * math.sin(a))], fill=(240, 240, 240), width=3)
    d.line([(w / 2, 134), (w / 2 + 44 * math.cos(math.radians(300)), 134 + 44 * math.sin(math.radians(300)))], fill=(230, 50, 40), width=6)
    text_c(d, (w / 2, 222), '0  -  16 V', 18, (220, 220, 220))
    d.ellipse((24, 210, 44, 230), fill=(80, 230, 90))
    return arr(im)


def poster(w=256, h=384):
    """vintage railway poster (original art)"""
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32) / h
    a = C((40, 60, 110)) * (1 - yy[..., None]) + C((230, 140, 80)) * yy[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    d.polygon([(0, h * 0.62), (w * 0.35, h * 0.3), (w * 0.55, h * 0.48), (w * 0.75, h * 0.25), (w, h * 0.55), (w, h * 0.7), (0, h * 0.7)], fill=(70, 80, 100))
    d.polygon([(w * 0.3, h * 0.36), (w * 0.35, h * 0.3), (w * 0.4, h * 0.36)], fill=(240, 244, 250))
    d.polygon([(w * 0.7, h * 0.31), (w * 0.75, h * 0.25), (w * 0.8, h * 0.31)], fill=(240, 244, 250))
    d.rectangle((0, h * 0.7, w, h), fill=(60, 110, 60))
    d.ellipse((w * 0.72, h * 0.06, w * 0.86, h * 0.15), fill=(250, 240, 200))
    d.rectangle((w * 0.1, h * 0.66, w * 0.5, h * 0.72), fill=(30, 30, 30))
    text_c(d, (w / 2, h * 0.82), 'VISIT', 30, (250, 240, 210), f=FONTS)
    text_c(d, (w / 2, h * 0.91), 'PAD MOUNTAIN', 30, (250, 220, 120), maxw=w - 20, f=FONTS)
    d.rectangle((4, 4, w - 5, h - 5), outline=(240, 230, 200), width=4)
    return arr(im)


def jumppad_tex(n=256):
    im = Image.new('RGB', (n, n), (30, 30, 34)); d = ImageDraw.Draw(im)
    for k in range(12):
        a0 = k * 30
        d.pieslice((6, 6, n - 6, n - 6), a0, a0 + 15, fill=(240, 200, 40))
    d.ellipse((50, 50, n - 50, n - 50), fill=(200, 30, 30), outline=(250, 250, 250), width=6)
    text_c(d, (n / 2, n / 2), 'JUMP', 40, (255, 255, 255), stroke=3, stroke_fill=(60, 10, 10))
    return arr(im)


def wallpaper(n=256, seed=36):
    a = fill(n, (200, 186, 150), 3, seed)
    im = img(a); d = ImageDraw.Draw(im)
    for x in range(0, n, 32): d.line([(x, 0), (x, n)], fill=(176, 156, 120), width=4)
    for y in range(16, n, 64):
        for x in range(16, n, 32): d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(150, 90, 80))
    return arr(im)


def carpet(n=256, seed=37):
    return fill(n, (110, 40, 46), 6, seed) + N3(n, 0.6, seed + 1, 10)


def wicker(n=128, seed=38):
    a = np.zeros((n, n, 3), np.float32)
    yy, xx = np.mgrid[0:n, 0:n]
    a[:] = C((196, 160, 104))
    a[((xx // 8) + (yy // 8)) % 2 == 0] *= 0.8
    return a + N3(n, 0.6, seed, 8)


def roof_flat(n=256, seed=39):
    return fill(n, (52, 52, 56), 4, seed) + N3(n, 0.6, seed + 1, 8)


# ----------------------------------------------------------------------------------------------- write
def make_textures(W):
    n = 256
    W.save('floorboards', planks(n, (150, 108, 70), 4, 1, dust=0.22))
    W.save('roofboards', planks(n, (168, 124, 82), 6, 2, dust=0.1))
    W.save('kneewall', planks(n, (140, 100, 64), 6, 3, vertical=True, dust=0.18))
    W.save('gable', planks(n, (132, 96, 62), 5, 4, vertical=True, dust=0.15))
    W.save('beam', beam())
    W.save('plywood', plywood()); W.save('ply_edge', ply_edge()); W.save('ply_under', plywood(seed=15) * 0.8)
    W.save('crate', crate())
    W.save('grass', grass()); W.save('ballast', ballast())
    W.save('rock', rock()); W.save('rock_moss', rock(seed=40, moss=True)); W.save('rock_dark', rock(base=(70, 66, 60), seed=41))
    W.save('snow', snow()); W.save('sand', sand())
    W.save('brick_red', brick()); W.save('timber_blue', boards_painted())
    W.save('trim_white', fill(64, (236, 232, 222), 3, 42))
    W.save('paving', paving()); W.save('roof_flat', roof_flat())
    W.save('tiles_red', roof_tiles()); W.save('tiles_blue', roof_tiles(base=(60, 80, 120), seed=43))
    W.save('plaster_warm', plaster()); W.save('plaster_cool', plaster(col=(196, 214, 230), seed=44))
    W.save('stone', rock(base=(180, 172, 156), seed=45) * 0.5 + fill(n, (186, 178, 160), 4, 46) * 0.5)
    W.save('window_lit', house_window())
    W.save('door_red', door_tex((150, 40, 36))); W.save('door_blue', door_tex((40, 70, 150))); W.save('door_wood', door_tex((110, 76, 46)))
    W.save('sign_red', station_sign('RED HILL', (150, 30, 30))); W.save('sign_blue', station_sign('BLUE VALLEY', (30, 60, 150)))
    W.save('sign_hall', station_sign('TOWN HALL', (70, 60, 50)))
    W.save('clock', clock_face())
    W.save('trestle', trestle())
    W.save('water', fill(n, (40, 80, 90), 4, 47) + N3(n, 10, 48, 12))
    W.save('cardboard', cardboard())
    W.save('box_trains', box_print('TRAINS', 'spare track + points', seed=49))
    W.save('box_xmas', box_print('XMAS', 'lights - baubles - star', seed=50))
    W.save('box_books', box_print('BOOKS', 'old comics, do not bend', seed=51))
    W.save('trunk', trunk()); W.save('lining', lining())
    rgb, al = cobweb(); W.save('cobweb', rgb, al)
    W.save('powerpack', powerpack())
    W.save('poster', poster())
    W.save('jumppad', jumppad_tex())
    W.save('wallpaper', wallpaper()); W.save('carpet', carpet()); W.save('wicker', wicker())
    W.save('bulb', fill(32, (255, 226, 160), 2, 52)); W.save('cord', fill(32, (30, 28, 26), 2, 53))
    W.save('glass', fill(64, (150, 170, 200), 2, 54))
    W.save('metal', fill(64, (120, 122, 128), 4, 55))
    W.save('sky', fill(64, (20, 24, 50), 2, 56))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 57))


SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padattic/attic_textures.py)\n\n"
STEPS = {'floorboards': 'woodsteps', 'roofboards': 'woodsteps', 'beam': 'woodsteps', 'plywood': 'woodsteps', 'crate': 'woodsteps',
         'trestle': 'woodsteps', 'grass': 'softsteps', 'ballast': 'sandsteps', 'sand': 'sandsteps', 'snow': 'snowsteps',
         'cardboard': 'softsteps', 'box_trains': 'softsteps', 'box_xmas': 'softsteps', 'box_books': 'softsteps', 'carpet': 'carpetsteps',
         'tiles_red': 'woodsteps', 'tiles_blue': 'woodsteps', 'trunk': 'woodsteps', 'lining': 'carpetsteps', 'wicker': 'softsteps'}


def lm(name, steps=None, extra=''):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    return s


def glow(name, light, rgb, wave=None):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n\tsurfaceparm nolightmap\n'
    if light: s += f'\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
    rg = f'rgbGen wave {wave}' if wave else 'rgbGen identity'
    return s + f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\t{rg}\n\t}}\n}}\n\n'


def make_shader(W, out):
    S = SH
    special = {'window_lit', 'clock', 'bulb', 'water', 'cobweb', 'glass', 'sky', 'nodraw_ns', 'sign_red', 'sign_blue', 'jumppad', 'powerpack', 'cord'}
    for nme in sorted(W.sizes):
        if nme in special: continue
        S += lm(nme, STEPS.get(nme))
    S += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.8 0.3\n')
    S += lm('powerpack', extra='\tq3map_surfacelight 30\n\tq3map_lightRGB 0.4 1 0.5\n')
    S += lm('cord')
    S += glow('window_lit', 250, '1 0.8 0.5')
    S += glow('clock', 120, '1 0.95 0.8')
    S += glow('bulb', 2400, '1 0.82 0.55')
    S += glow('sign_red', 90, '1 0.5 0.4'); S += glow('sign_blue', 90, '0.5 0.6 1')
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/sky
	surfaceparm sky
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_sun {MOON}
	q3map_lightimage textures/{NS}/sky
	skyparms {SKY} - -
}}

textures/{NS}/glass
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
		map textures/{NS}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.06 0.07 0.1 )
		tcGen environment
	}}
}}

textures/{NS}/water
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	tessSize 64
	deformVertexes wave 120 sin 0 1.5 0 0.4
	{{
		map textures/{NS}/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.7
		rgbGen identity
		tcMod turb 0 0.03 0 0.12
		tcMod scroll 0.01 0.006
	}}
	{{
		map textures/{NS}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.08 0.1 0.14 )
		tcGen environment
	}}
}}

textures/{NS}/water_inner
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.3
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nomarks
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

textures/{NS}/cobweb
{{
	qer_editorimage textures/{NS}/cobweb.tga
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull disable
	{{
		map textures/{NS}/cobweb.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.55 0.55 0.6 )
	}}
}}

'''
    S += rail_models.shaders()
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa team ctl 1lc ft lps syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    rail_models.make(out)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
