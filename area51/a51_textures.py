"""Procedural textures, night-desert sky, shader + arena for wop_padarea51 (Area 51: Dreamland).
All art is original and generated here. make_all(out) writes textures/padarea51/*, env/padarea51/* (sky cube),
models/padarea51/* (a51_models), scripts/padarea51.shader and scripts/wop_padarea51.arena (pk3dir layout)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a51_models

MAP = 'wop_padarea51'
NS = 'padarea51'
LONGNAME = 'Area 51: Dreamland'
FONTS = ['/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
FONTB = next(f for f in FONTS if os.path.exists(f))
FONTS_STENCIL = ['/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf']
FONTST = next((f for f in FONTS_STENCIL if os.path.exists(f)), FONTB)


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


def font(sz, stencil=False): return ImageFont.truetype(FONTST if stencil else FONTB, sz)


def text_fit(draw, box, text, fill_, stencil=False, max_sz=400):
    """largest font that fits text into box (x0, y0, x1, y1), centred"""
    x0, y0, x1, y1 = box
    sz = max_sz
    while sz > 6:
        f = font(sz, stencil)
        l, t, r, b = draw.multiline_textbbox((0, 0), text, font=f, align='center', spacing=sz // 6)
        if r - l <= x1 - x0 and b - t <= y1 - y0: break
        sz -= 2
    draw.multiline_text(((x0 + x1) / 2 - (r - l) / 2 - l, (y0 + y1) / 2 - (b - t) / 2 - t), text, font=f, fill=fill_,
                        align='center', spacing=sz // 6)


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


# ------------------------------------------------------------------------------------------- desert ground
def sand(n=512, seed=1, base=(196, 160, 112)):
    a = fill(n, base, 6, seed) + N3(n, 30, seed + 2, 10) + N3(n, 3, seed + 3, 5)
    x, y = tile_xy(n)
    rip = np.sin((x * 9 + y * 3 + noise(n, 20, seed + 4) * 0.15) * 2 * math.pi * 2)    # wind ripples
    a += (rip * 5)[..., None]
    rng = np.random.default_rng(seed + 5)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(260):                                                                 # pebbles
        px, py = rng.integers(0, n, 2); r = rng.uniform(1, 3.5)
        c = tuple(int(v) for v in C(base) * rng.uniform(0.55, 1.1))
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)
    for _ in range(18):                                                                  # cracks (dry lake bed)
        px, py = rng.uniform(0, n, 2); pts = [(px, py)]
        ang = rng.uniform(0, 2 * math.pi)
        for k in range(8):
            ang += rng.uniform(-0.7, 0.7); px += math.cos(ang) * 14; py += math.sin(ang) * 14; pts.append((px, py))
        d.line(pts, fill=tuple(int(v * 0.72) for v in base), width=1)
    return arr(im)


def scorched(n=512, seed=11):
    a = sand(n, seed, (120, 100, 80))
    soot = np.clip(noise(n, 18, seed + 1) * 0.5 + 0.35, 0, 1)[..., None]
    a = lerp(a, C((35, 30, 28)), soot * 0.8)
    glass = np.clip(noise(n, 4, seed + 2) - 2.0, 0, 1)[..., None]                         # fused glass specks
    return a + glass * C((90, 150, 120))


def rock(n=512, seed=21):
    x, y = tile_xy(n)
    layers = np.sin((y * 14 + noise(n, 30, seed) * 0.25) * 2 * math.pi)
    a = fill(n, (150, 100, 72), 8, seed) + (layers * 14)[..., None] * C((1, 0.8, 0.6))
    a += N3(n, 6, seed + 1, 10) + N3(n, 40, seed + 2, 18)
    cr = np.abs(noise(n, 5, seed + 3)) < 0.06
    a[cr] *= 0.6
    return a


def tarmac(n=512, seed=31):
    a = fill(n, (58, 58, 60), 7, seed) + N3(n, 1, seed + 1, 12) + N3(n, 40, seed + 2, 6)
    rng = np.random.default_rng(seed + 3)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(6):                                                                  # tyre marks / tar seams
        y0 = rng.uniform(0, n); d.line([(0, y0), (n, y0 + rng.uniform(-20, 20))], fill=(40, 40, 42), width=int(rng.integers(3, 8)))
    for _ in range(4):
        px, py = rng.uniform(0, n, 2); r = rng.uniform(20, 50)
        d.ellipse((px - r, py - r * 0.6, px + r, py + r * 0.6), fill=(46, 45, 46))
    return arr(im.filter(ImageFilter.GaussianBlur(0.6)))


def runway(w=2048, h=512, seed=33):
    """runway strip seen from above, x along the strip (texture u), 'threshold' piano keys at both ends, centre dashes,
    designators 14 / 32, touchdown bars"""
    base = arr(img(np.concatenate([tarmac(512, seed + k) for k in range(4)], 1)).resize((w, h)))
    im = img(base); d = ImageDraw.Draw(im)
    W = (238, 238, 230)
    m = 24                                                                                # edge lines
    d.rectangle((0, m, w, m + 8), fill=W); d.rectangle((0, h - m - 8, w, h - m), fill=W)
    for k in range(10):                                                                   # piano keys both ends
        y0 = 60 + k * 40
        d.rectangle((16, y0, 120, y0 + 22), fill=W); d.rectangle((w - 120, y0, w - 16, y0 + 22), fill=W)
    for x in range(420, w - 420, 120):                                                   # centre dashes
        d.rectangle((x, h // 2 - 5, x + 64, h // 2 + 5), fill=W)
    f = font(150)
    for (txt, x, rot) in (('32', 200, 90), ('14', w - 200, 270)):
        t = Image.new('RGBA', (300, 200), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
        td.text((150, 100), txt, font=f, fill=W + (255,), anchor='mm')
        t = t.rotate(rot, expand=True)
        im.paste(t, (int(x - t.size[0] / 2), int(h / 2 - t.size[1] / 2)), t)
    for x in (360, w - 400):                                                              # touchdown bars
        for yy in (h // 2 - 120, h // 2 + 80):
            d.rectangle((x, yy, x + 40, yy + 40), fill=W)
    a = arr(im)
    a = a * (1 - 0.15 * np.clip(noise(w, 6, seed + 9, h) * 0.5, 0, 1))[..., None]        # wear
    return a


def apron(n=512, seed=41):
    a = fill(n, (150, 148, 142), 6, seed) + N3(n, 1, seed + 1, 8) + N3(n, 50, seed + 2, 8)
    im = img(a); d = ImageDraw.Draw(im)
    for k in (0, n // 2):
        d.line([(k, 0), (k, n)], fill=(98, 96, 92), width=3); d.line([(0, k), (n, k)], fill=(98, 96, 92), width=3)
    rng = np.random.default_rng(seed + 3)
    for _ in range(5):
        px, py = rng.uniform(0, n, 2); r = rng.uniform(12, 40)
        d.ellipse((px - r, py - r, px + r, py + r * 0.7), fill=(110, 106, 100))
    return arr(im.filter(ImageFilter.GaussianBlur(0.5)))


def taxi_line(w=64, h=512):
    a = fill(w, (150, 148, 142), 5, 44, h)
    a[:, 22:42] = C((230, 190, 40)) + N3(w, 1, 45, 8, h)[:, 22:42]
    return a


def concrete(n=256, seed=51, col=(158, 156, 150)):
    a = fill(n, col, 7, seed) + N3(n, 1, seed + 1, 7) + N3(n, 30, seed + 2, 10)
    rng = np.random.default_rng(seed + 3)
    im = img(a); d = ImageDraw.Draw(im)
    d.line([(0, 0), (n, 0)], fill=tuple(int(v * 0.7) for v in col), width=2)
    for _ in range(14):                                                                   # form-tie holes
        px, py = rng.integers(8, n - 8, 2); d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=tuple(int(v * 0.5) for v in col))
    a = arr(im)
    st = np.clip(noise(n, 3, seed + 4, n) * 0.3, 0, 1)                                    # rain streaks
    y = np.linspace(0, 1, n)[:, None]
    return a * (1 - 0.12 * st[..., None] * y[..., None])


# ------------------------------------------------------------------------------------------- lab + metal
def lab_floor(n=256, seed=61):
    a = fill(n, (200, 204, 206), 4, seed) + N3(n, 1, seed + 1, 5)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, n // 2):
        d.line([(k, 0), (k, n)], fill=(150, 154, 158), width=2); d.line([(0, k), (n, k)], fill=(150, 154, 158), width=2)
    return arr(im)


def lab_wall(w=256, h=256, seed=63):
    a = fill(w, (214, 218, 222), 4, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.line([(0, 0), (0, h)], fill=(160, 164, 170), width=3)
    d.rectangle((0, int(h * 0.60), w, int(h * 0.64)), fill=(40, 90, 170))                   # blue stripe
    d.rectangle((0, int(h * 0.88), w, h), fill=(120, 124, 130))                            # kick plate
    for y in (int(h * 0.3), int(h * 0.75)):
        for x in (10, w - 10): d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(140, 140, 146))
    return arr(im)


def lab_ceil(n=256, seed=65):
    a = fill(n, (190, 192, 194), 3, seed) + N3(n, 1, seed + 1, 6)
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, n // 2):
        d.line([(k, 0), (k, n)], fill=(120, 122, 126), width=4); d.line([(0, k), (n, k)], fill=(120, 122, 126), width=4)
    return arr(im)


def light_panel(w=128, h=64, col=(235, 245, 255)):
    a = np.zeros((h, w, 3), np.float32) + C(col)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(120, 124, 130), width=4)
    for x in range(8, w - 8, 12): d.line([(x, 6), (x, h - 6)], fill=tuple(int(c * 0.9) for c in col), width=1)
    return arr(im)


def hazard(n=128):
    x, y = tile_xy(n)
    s = (np.floor((x + y) * 4) % 2)[..., None]
    a = lerp(C((235, 190, 30)), C((25, 25, 25)), s) + N3(n, 1, 71, 6)
    return a


def steel(n=256, seed=73, col=(140, 146, 150)):
    a = fill(n, col, 3, seed)
    st = noise(n, 0.6, seed + 1) * 0.5 + noise(n, 8, seed + 2) * 0.5
    a += (st * 6)[..., None]
    return a


def diamond_plate(n=128, seed=75):
    a = steel(n, seed, (130, 134, 138))
    x, y = tile_xy(n)
    for (ox, oy, ang) in ((0.25, 0.25, 1), (0.75, 0.75, 1), (0.75, 0.25, -1), (0.25, 0.75, -1)):
        u = (x - ox) * math.cos(0.6 * ang) - (y - oy) * math.sin(0.6 * ang); v = (x - ox) * math.sin(0.6 * ang) + (y - oy) * math.cos(0.6 * ang)
        m = ((u / 0.17) ** 2 + (v / 0.04) ** 2) < 1
        a[m] += 35
    return a


def grate(n=128):
    a = np.zeros((n, n, 3), np.float32) + C((70, 74, 78))
    al = np.zeros((n, n), np.float32)
    for k in range(0, n, 16):
        a[:, k:k + 4] = C((120, 124, 128)); al[:, k:k + 4] = 255
        a[k:k + 4, :] = C((110, 114, 118)); al[k:k + 4, :] = 255
    return a, al


def chainlink(n=128):
    """chain-link fence diamonds (alpha)"""
    x, y = tile_xy(n)
    al = np.zeros((n, n), np.float32)
    u = (x + y) * 8; v = (x - y) * 8
    w = 0.07
    m = (np.abs(u - np.round(u)) < w) | (np.abs(v - np.round(v)) < w)
    al[m] = 255
    a = np.zeros((n, n, 3), np.float32) + C((170, 175, 178)) + N3(n, 1, 77, 15)
    return a, al


def razor_wire(w=256, h=64):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(-1, 6):
        cx = k * 48 + 24
        d.ellipse((cx - 30, 6, cx + 30, h - 6), outline=(190, 195, 200, 255), width=2)
        for t in range(0, 360, 40):
            px = cx + 30 * math.cos(math.radians(t)); py = h / 2 + (h / 2 - 6) * math.sin(math.radians(t))
            d.line([(px - 3, py - 3), (px + 3, py + 3)], fill=(220, 220, 225, 255), width=1)
    return im


def jumppad_tex(n=256):
    """alien landing glyph: concentric rings + three-pronged mark, glowing green"""
    im = Image.new('RGB', (n, n), (18, 26, 22)); d = ImageDraw.Draw(im)
    c = n / 2
    for (r, wdt, col) in ((c - 4, 8, (40, 255, 120)), (c * 0.72, 4, (40, 200, 110)), (c * 0.42, 6, (120, 255, 160))):
        d.ellipse((c - r, c - r, c + r, c + r), outline=col, width=wdt)
    for k in range(3):
        a = math.radians(90 + k * 120)
        d.line([(c, c), (c + math.cos(a) * c * 0.7, c - math.sin(a) * c * 0.7)], fill=(150, 255, 190), width=7)
    d.ellipse((c - 14, c - 14, c + 14, c + 14), fill=(200, 255, 220))
    return arr(im.filter(ImageFilter.GaussianBlur(1.2)))


def sign(text, w=512, h=256, bg=(240, 240, 235), fg=(200, 20, 20), border=(30, 30, 30), sub=None, subfg=(20, 20, 20), stencil=False):
    im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=border, width=max(4, h // 32))
    if sub:
        text_fit(d, (w * 0.06, h * 0.08, w * 0.94, h * 0.55), text, fg, stencil)
        text_fit(d, (w * 0.06, h * 0.58, w * 0.94, h * 0.92), sub, subfg, stencil)
    else:
        text_fit(d, (w * 0.06, h * 0.1, w * 0.94, h * 0.9), text, fg, stencil)
    a = arr(im)
    return a * (1 - 0.08 * np.clip(noise(w, 3, len(text), h), 0, 1))[..., None] + N3(w, 1, 5, 4, h)


def stencil_text(text, w=512, h=128, bg=(158, 156, 150), fg=(30, 30, 30), seed=91):
    a = concrete(max(w, h), seed, bg)[:h, :w] if w == h else np.asarray(img(concrete(256, seed, bg)).resize((w, h)), np.float32)
    im = img(a); d = ImageDraw.Draw(im)
    text_fit(d, (w * 0.05, h * 0.1, w * 0.95, h * 0.9), text, fg, stencil=True)
    return arr(im)


def earth_window(w=512, h=256, seed=93):
    """view from orbit: black space, stars, the blue limb of the earth with clouds"""
    a = np.zeros((h, w, 3), np.float32) + C((2, 3, 8))
    rng = np.random.default_rng(seed)
    st = rng.random((h, w)) > 0.996
    a[st] = C((230, 230, 255))
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, R = w * 0.5, h * 2.6, h * 2.25
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    inside = r < R
    cl = np.clip(noise(w, 6, seed + 1, h) * 0.6 + noise(w, 2, seed + 2, h) * 0.3, 0, 1)
    ocean = C((20, 60, 150)) + noise(w, 10, seed + 3, h)[..., None] * 10
    land = C((70, 110, 60))
    lm = noise(w, 14, seed + 4, h) > 0.6
    surf = np.where(lm[..., None], land, ocean)
    surf = lerp(surf, C((240, 245, 255)), cl[..., None] * 0.8)
    shade = np.clip((R - r) / (R * 0.15), 0, 1)[..., None]
    a = np.where(inside[..., None], surf * (0.4 + 0.6 * shade), a)
    glow = np.exp(-((r - R) / 8.0) ** 2)[..., None] * C((90, 160, 255))
    return a + glow


def alien_panel(n=256, seed=95):
    """mothership hull panels: dark hex plates with teal glow seams"""
    a = fill(n, (40, 36, 54), 4, seed)
    im = img(a); d = ImageDraw.Draw(im)
    s = n / 4
    for i in range(-1, 6):
        for j in range(-1, 6):
            cx = i * s * 1.5; cy = j * s * math.sqrt(3) + (i % 2) * s * math.sqrt(3) / 2
            pts = [(cx + s * 0.95 * math.cos(math.radians(60 * k)), cy + s * 0.95 * math.sin(math.radians(60 * k))) for k in range(6)]
            d.polygon(pts, outline=(60, 220, 200), width=2)
    return arr(im.filter(ImageFilter.GaussianBlur(0.7)))


def alien_floor(n=512, seed=97):
    x, y = tile_xy(n)
    r = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2); th = np.arctan2(y - 0.5, x - 0.5)
    rings = (np.sin(r * 60) > 0.85).astype(np.float32)
    spokes = (np.abs(np.sin(th * 6)) < 0.04).astype(np.float32) * (r > 0.12)
    a = fill(n, (30, 28, 44), 4, seed) + (rings + spokes)[..., None] * C((40, 200, 180))
    return a


def glow_tex(col, n=64, edge=(60, 60, 60)):
    a = np.zeros((n, n, 3), np.float32) + C(col)
    a[:3, :] = C(edge); a[-3:, :] = C(edge); a[:, :3] = C(edge); a[:, -3:] = C(edge)
    return a


def crate_side(n=256, seed=101):
    a = fill(n, (150, 118, 76), 6, seed)
    x, y = tile_xy(n)
    a += (np.sin(y * 2 * math.pi * 40 + noise(n, 3, seed + 1) * 2) * 6)[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(0, n, n // 4): d.line([(0, k), (n, k)], fill=(100, 76, 48), width=2)
    return arr(im)


def earthmark(n=256):
    return fill(n, (140, 120, 90), 6, 103)


# ------------------------------------------------------------------------------------------- sky
SUN_DIR = (220.0, 32.0)          # moon yaw, elevation (q3map_sun uses the same)


def ridge_h(az):
    """distant mountain silhouette elevation (radians) at azimuth az (array)"""
    h = (0.035 + 0.02 * np.sin(az * 3 + 1.0) + 0.012 * np.sin(az * 7 + 2.0) + 0.006 * np.sin(az * 19 + 0.5)
         + 0.003 * np.sin(az * 41))
    return np.clip(h, 0.008, 0.09)


def sky_color(d, rng_stars):
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    z = d[..., 2]; az = np.arctan2(d[..., 1], d[..., 0])
    el = np.arcsin(np.clip(z, -1, 1))
    t = np.clip(el / (math.pi / 2), 0, 1)
    hor = C((34, 40, 70)); zen = C((4, 6, 18))
    c = lerp(hor, zen, (t ** 0.6)[..., None])
    # city glow (Las Vegas lies south-west of the base) near the horizon
    vg = np.exp(-((az - math.radians(-130)) ** 2) / 0.25) * np.exp(-np.maximum(el, 0) / 0.08)
    c = c + vg[..., None] * C((120, 70, 40))
    # milky way: a tilted band of hazy light + dust lane
    n_band = np.array([0.35, -0.55, 0.76]); n_band /= np.linalg.norm(n_band)
    db = d @ n_band
    band = np.exp(-(db ** 2) / 0.02)
    tex = np.clip(0.6 + 0.5 * np.sin(az * 23 + el * 17) * np.sin(az * 9 - el * 31), 0, 1.4)
    dust = np.exp(-((db - 0.03) ** 2) / 0.0015) * 0.7
    c = c + (band * tex * (1 - dust) * (z > 0))[..., None] * C((60, 62, 80))
    # moon
    yaw, pit = math.radians(SUN_DIR[0]), math.radians(SUN_DIR[1])
    mdv = np.array([math.cos(pit) * math.cos(yaw), math.cos(pit) * math.sin(yaw), math.sin(pit)])
    ang = np.arccos(np.clip(d @ mdv, -1, 1))
    disc = ang < 0.045
    halo = np.exp(-(ang / 0.18) ** 2) * 0.6 + np.exp(-(ang / 0.05) ** 2) * 0.6
    c = c + halo[..., None] * C((70, 75, 90))
    crater = 0.85 + 0.15 * np.sin(d[..., 0] * 900) * np.sin(d[..., 1] * 700 + d[..., 2] * 500)
    c = np.where(disc[..., None], C((235, 235, 220)) * crater[..., None], c)
    # mountains: dark silhouette below the ridge line, faintly lit rim
    rh = ridge_h(az)
    below = el < rh
    rim = np.exp(-((el - rh) / 0.004) ** 2)
    c = c + rim[..., None] * C((30, 34, 50)) * (~below)[..., None]
    m_col = C((12, 13, 20)) + (np.sin(az * 60) * 2)[..., None]
    c = np.where(below[..., None], m_col, c)
    return np.clip(c, 0, 255)


def make_sky(out, n=512):
    d = os.path.join(out, 'env', NS); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t),
             'up': (-t, -s, one), 'dn': (t, -s, -one)}
    rng = np.random.default_rng(3)
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        c = sky_color(D, rng)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        el = np.arcsin(np.clip(Dn[..., 2], -1, 1)); az = np.arctan2(Dn[..., 1], Dn[..., 0])
        above = el > ridge_h(az) + 0.01
        st = rng.random((n, n))
        bright = (st > 0.9975) & above
        dim = (st > 0.993) & (st <= 0.9975) & above
        c = np.where(bright[..., None], C((250, 250, 255)), c)
        c = np.where(dim[..., None], c + C((70, 70, 85)), c)
        im = img(c)
        # big stars as small crosses
        dd = ImageDraw.Draw(im)
        ys, xs = np.nonzero((st > 0.99985) & above)
        for (py, px) in zip(ys, xs):
            dd.line([(px - 2, py), (px + 2, py)], fill=(255, 255, 255)); dd.line([(px, py - 2), (px, py + 2)], fill=(255, 255, 255))
        im.save(os.path.join(d, f'night_{k}.jpg'), quality=94)
    # thin high clouds (additive, dark)
    x, y = tile_xy(512)
    cl = np.clip(noise(512, 22, 7) * 0.7 + noise(512, 6, 8) * 0.3 - 0.4, 0, 2)
    img(np.clip(cl[..., None] * C((40, 44, 60)), 0, 255)).save(os.path.join(d, 'night_clouds.jpg'), quality=92)
    img(np.zeros((64, 64, 3)) + C((60, 70, 110))).save(os.path.join(out, 'textures', NS, 'skylight.jpg'))


# ------------------------------------------------------------------------------------------- textures
SIGNS = {
    'sign_restricted': ('RESTRICTED AREA', 'USE OF DEADLY FORCE AUTHORIZED', (240, 240, 235), (200, 20, 20)),
    'sign_nophoto': ('NO PHOTOGRAPHY', 'VIOLATORS WILL BE PROBED', (240, 240, 235), (20, 20, 20)),
    'sign_area51': ('AREA 51', 'DREAMLAND  -  AUTHORIZED PADS ONLY', (30, 60, 40), (240, 230, 160)),
    'sign_hangar': ('HANGAR 18', None, (40, 44, 52), (245, 200, 40)),
    'sign_s4': ('S-4  LEVEL 2', 'BIOHAZARD  -  KEEP OUT', (230, 200, 40), (20, 20, 20)),
    'sign_lab': ('XENOBIOLOGY', 'DO NOT TAP ON THE GLASS', (230, 234, 240), (40, 90, 170)),
    'sign_vault': ('CONTAINMENT', 'ITEM 51-B  -  DO NOT OPEN', (60, 10, 10), (255, 220, 60)),
    'sign_tower': ('GROOM TOWER', None, (40, 44, 52), (240, 240, 240)),
    'sign_fuel': ('FUEL - NO SMOKING', None, (220, 30, 20), (255, 255, 255)),
    'sign_mothership': ('WELCOME, EARTHLING', 'PLEASE REMAIN CALM', (20, 30, 40), (90, 255, 200)),
    'sign_secret': ('TOP SECRET', None, (240, 240, 235), (200, 20, 20)),
    'sign_cows': ('CATTLE CROSSING', 'BEAM ZONE', (240, 200, 30), (20, 20, 20)),
}


def make_textures(W):
    W.save('sand', sand()); W.save('scorched', scorched()); W.save('rock', rock()); W.save('tarmac', tarmac())
    W.save('runway', runway()); W.save('apron', apron()); W.save('taxi_line', taxi_line())
    W.save('concrete', concrete()); W.save('concrete_dark', concrete(256, 53, (110, 108, 104)))
    W.save('lab_floor', lab_floor()); W.save('lab_wall', lab_wall()); W.save('lab_ceil', lab_ceil())
    W.save('light_panel', light_panel()); W.save('light_green', light_panel(128, 64, (150, 255, 170)))
    W.save('hazard', hazard()); W.save('steel', steel()); W.save('plate', diamond_plate()); W.save('rust', steel(256, 79, (120, 76, 50)))
    a, al = grate(); W.save('grate', a, al)
    a, al = chainlink(); W.save('chainlink', a, al)
    W.save('razorwire', razor_wire())
    W.save('jumppad', jumppad_tex()); W.save('rubber', fill(64, (30, 34, 32), 3, 67))
    W.save('earth_window', earth_window()); W.save('alien_panel', alien_panel()); W.save('alien_floor', alien_floor())
    W.save('crate', crate_side()); W.save('dark', fill(64, (24, 24, 26), 3, 63))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 73))
    for nm, c in (('glow_red', (255, 60, 40)), ('glow_amber', (255, 170, 60)), ('glow_green', (90, 255, 140)), ('glow_white', (240, 245, 255)),
                  ('glow_teal', (70, 255, 220))):
        W.save(nm, glow_tex(c))
    for nm, (t, sub, bg, fg) in SIGNS.items():
        W.save(nm, sign(t, 512, 256 if sub else 128, bg, fg, sub=sub, stencil=nm in ('sign_hangar', 'sign_s4', 'sign_secret')))
    W.save('stencil_51', stencil_text('51', 256, 256, (158, 156, 150)))
    W.save('stencil_s4', stencil_text('S-4', 512, 256, (158, 156, 150)))


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/area51/a51_textures.py)\n\n"
STEPS = {'sand': 'sandsteps', 'scorched': 'sandsteps', 'rock': 'sandsteps', 'crate': 'woodsteps', 'plate': 'latticesteps',
         'grate': 'latticesteps'}


def lm(name, steps=None, extra='', tex=None, add_stage=''):
    t = tex or f'textures/{NS}/{name}'
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + add_stage + '}\n\n'


def glow(name, light, rgb, extra='', stage='\t\trgbGen identity\n', tex=None):
    t = tex or f'textures/{NS}/{name}'
    return (f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
            f'\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {t}\n{stage}\t}}\n}}\n\n')


def make_shader(W, out, model_shaders):
    S = SH
    special = {'jumppad', 'nodraw_ns', 'chainlink', 'grate', 'razorwire', 'light_panel', 'light_green', 'earth_window',
               'alien_panel', 'alien_floor', 'sign_mothership'} | {n for n in W.sizes if n.startswith('glow_')}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm, 'metalsteps' if nm in ('steel', 'rust', 'hazard') else None))
    S += lm('jumppad', extra='\tq3map_surfacelight 150\n\tq3map_lightRGB 0.3 1 0.5\n', add_stage=(
        f'\t{{\n\t\tmap textures/{NS}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.3 0.3 0 0.9\n'
        '\t\ttcMod rotate 30\n\t}\n'))
    S += glow('light_panel', 600, '0.92 0.96 1')
    S += glow('light_green', 500, '0.55 1 0.65', stage='\t\trgbGen wave sin 0.9 0.1 0 0.7\n')
    S += glow('earth_window', 120, '0.5 0.7 1')
    S += glow('sign_mothership', 100, '0.4 1 0.8')
    S += (f'textures/{NS}/alien_panel\n{{\n\tqer_editorimage textures/{NS}/alien_panel\n\tsurfaceparm metalsteps\n'
          f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap textures/{NS}/alien_panel\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/alien_panel\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.15 0.15 0 0.3\n\t}}\n}}\n\n')
    S += (f'textures/{NS}/alien_floor\n{{\n\tqer_editorimage textures/{NS}/alien_floor\n\tsurfaceparm metalsteps\n\tq3map_surfacelight 40\n\tq3map_lightRGB 0.3 1 0.9\n'
          f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap textures/{NS}/alien_floor\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/alien_floor\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.2 0.2 0 0.25\n\t\ttcMod rotate 8\n\t}}\n}}\n\n')
    for nm in sorted(n for n in W.sizes if n.startswith('glow_')):
        rgb = {'glow_red': '1 0.25 0.15', 'glow_amber': '1 0.65 0.25', 'glow_green': '0.35 1 0.55', 'glow_white': '0.95 0.97 1',
               'glow_teal': '0.3 1 0.85'}[nm]
        S += glow(nm, 300, rgb)
    # flashing beacon (red, used by the tower mast and the hangar alarm light)
    S += (f'textures/{NS}/beacon\n{{\n\tqer_editorimage textures/{NS}/glow_red\n\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
          f'\t{{\n\t\tmap textures/{NS}/glow_red\n\t\trgbGen wave square 0.5 0.5 0 0.8\n\t}}\n}}\n\n')
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 0.62 0.7 1 110 {SUN_DIR[0]:g} {SUN_DIR[1]:g}
	q3map_skylight 60 3
	skyparms env/{NS}/night 512 -
	{{
		map env/{NS}/night_clouds
		blendFunc GL_ONE GL_ONE
		rgbGen identity
		tcMod scale 2 2
		tcMod scroll 0.004 0.002
	}}
}}

textures/{NS}/chainlink
{{
	qer_editorimage textures/{NS}/chainlink
	qer_trans 0.6
	surfaceparm trans
	surfaceparm alphashadow
	surfaceparm nomarks
	surfaceparm metalsteps
	cull none
	{{
		map textures/{NS}/chainlink.tga
		alphaFunc GE128
		depthWrite
		rgbGen identity
	}}
	{{
		map $lightmap
		blendFunc GL_DST_COLOR GL_ZERO
		depthFunc equal
		rgbGen identity
	}}
}}

textures/{NS}/razorwire
{{
	qer_editorimage textures/{NS}/razorwire
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/razorwire.tga
		alphaFunc GE128
		rgbGen vertex
	}}
}}

textures/{NS}/grate
{{
	qer_editorimage textures/{NS}/grate
	qer_trans 0.6
	surfaceparm trans
	surfaceparm alphashadow
	surfaceparm latticesteps
	cull none
	{{
		map textures/{NS}/grate.tga
		alphaFunc GE128
		depthWrite
		rgbGen identity
	}}
	{{
		map $lightmap
		blendFunc GL_DST_COLOR GL_ZERO
		depthFunc equal
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

textures/{NS}/tractor_beam
{{
	qer_editorimage textures/{NS}/glow_green
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map models/{NS}/beam_light
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.45 0.15 0 0.6
		tcMod scroll 0 -0.6
	}}
}}

'''
    S += model_shaders
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    make_sky(out)
    ms = a51_models.make(out)
    make_shader(W, out, ms)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
