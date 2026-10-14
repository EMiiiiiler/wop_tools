"""Procedural textures, psychedelic sky, shader + arena for wop_padshroom (Shroom Trip).
All art is original and generated here. make_all(out) writes textures/padshroom/*, env/padshroom/* (sky cube),
models/padshroom/* (shroom_models), scripts/padshroom.shader and scripts/wop_padshroom.arena (pk3dir layout)."""
import os, sys, math, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shroom_models

MAP = 'wop_padshroom'
NS = 'padshroom'
LONGNAME = 'Shroom Trip'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


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


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def lerp(a, b, t): return a + (b - a) * t


def hue(t, s=0.85, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(t % 1.0, s, v)
    return np.array([r * 255, g * 255, b * 255], np.float32)


def hue_arr(t, s=0.85, v=1.0):
    """vectorised hsv->rgb for an array of hues (0..1); s, v scalars or arrays"""
    t = np.mod(t, 1.0); s = np.broadcast_to(s, t.shape); v = np.broadcast_to(v, t.shape)
    i = np.floor(t * 6).astype(int) % 6; f = t * 6 - np.floor(t * 6)
    p = v * (1 - s); q = v * (1 - s * f); u = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, u, v]); g = np.choose(i, [u, v, v, q, p, p]); b = np.choose(i, [p, p, u, v, v, q])
    return np.stack([r, g, b], -1) * 255


def tile_xy(n, m=None):
    m = m or n
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    return x / n, y / m


def font(sz): return ImageFont.truetype(FONTB, sz)


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


# ------------------------------------------------------------------------------------------- ground + earth
def moss(n=512, seed=1):
    """deep green cushion moss with tiny star-shaped fronds and a few glowing spore dots"""
    a = fill(n, (72, 128, 56), 8, seed)
    a += N3(n, 30, seed + 2, 16) * C((0.6, 1.0, 0.5))
    a += N3(n, 3, seed + 3, 14) * C((0.7, 1.0, 0.6))
    r = np.random.default_rng(seed)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(2600):                     # moss fronds: little stars
        x, y = r.integers(0, n, 2); L = r.integers(3, 7)
        c = tuple(int(v) for v in (C((86, 150, 60)) + r.normal(0, 18, 3)).clip(0, 255))
        for k in range(5):
            ang = r.random() * 6.28
            d.line((x, y, x + L * math.cos(ang), y + L * math.sin(ang)), fill=c, width=1)
    for _ in range(70):                       # spore glints (cyan / magenta / amber)
        x, y = r.integers(4, n - 4, 2); col = [(120, 255, 240), (255, 120, 240), (255, 220, 120)][r.integers(0, 3)]
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=col)
    a = arr(im)
    # soil showing through in patches
    m = (noise(n, 18, seed + 5) > 1.1).astype(np.float32)[..., None]
    m = arr(Image.fromarray((m[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)))[..., :1] / 255
    soil = fill(n, (84, 60, 40), 10, seed + 6)
    return a * (1 - m) + soil * m


def bank(n=512, seed=7):
    """steep earth bank: layered soil with roots"""
    x, y = tile_xy(n)
    a = fill(n, (92, 66, 44), 10, seed)
    a += (np.sin(y * 2 * math.pi * 7 + noise(n, 16, seed + 1) * 1.2)[..., None] * 10) * C((1, 0.8, 0.6))
    im = img(a); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    for _ in range(40):
        px, py = r.integers(0, n, 2); w = r.integers(2, 6)
        pts = [(px, py)]
        for k in range(8):
            px += r.integers(-20, 21); py += r.integers(8, 30); pts.append((px, py))
        d.line(pts, fill=(140, 104, 70), width=int(w))
    a = arr(im)
    top = np.clip(1 - y * 5, 0, 1)[..., None]                       # mossy top edge
    return a * (1 - top) + moss(n, seed + 9) * top


def dirt(n=256, seed=11):
    a = fill(n, (96, 70, 48), 12, seed)
    r = np.random.default_rng(seed); im = img(a); d = ImageDraw.Draw(im)
    for _ in range(300):
        x, y = r.integers(0, n, 2); s = r.integers(1, 5)
        c = tuple(int(v) for v in (C((130, 110, 90)) + r.normal(0, 20, 3)).clip(0, 255))
        d.ellipse((x - s, y - s, x + s, y + s), fill=c)
    return arr(im)


def pebbles(n=512, seed=13):
    """pond bed: rounded pebbles in rainbow tints (the trip colours everything)"""
    a = fill(n, (60, 70, 70), 6, seed)
    r = np.random.default_rng(seed); im = img(a); d = ImageDraw.Draw(im)
    for _ in range(420):
        x, y = r.integers(0, n, 2); w, h = r.integers(8, 28, 2)
        c = hue(r.random(), 0.35, 0.75)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x - w + ox, y - h + oy, x + w + ox, y + h + oy), fill=tuple(int(v) for v in c), outline=(40, 44, 44))
    return arr(im) + N3(n, 1, seed + 2, 6)


def planks(w=256, h=256, seed=17):
    """chunky toadstool-house planks (stairs, landings, floors)"""
    a = np.zeros((h, w, 3), np.float32)
    r = np.random.default_rng(seed)
    for k in range(4):
        y0 = k * h // 4
        col = C((150, 104, 62)) + r.normal(0, 10, 3)
        g = noise(w, 1.5, seed + k, h // 4)
        band = col + g[..., None] * 10 + np.sin(np.arange(w) / w * 2 * math.pi * r.integers(3, 7))[None, :, None] * 8
        a[y0:y0 + h // 4] = band
        a[y0:y0 + 2] = (70, 46, 28)
    return a


def rotten(n=512, seed=19):
    """inside of hollow wood: soft fibrous rotten wood with glowing fungal threads"""
    x, y = tile_xy(n)
    a = fill(n, (110, 72, 44), 8, seed)
    a += (np.sin((x * 14 + noise(n, 10, seed + 1) * 0.6) * 2 * math.pi)[..., None] * 14) * C((1, 0.8, 0.6))
    im = img(a); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    for _ in range(60):                       # mycelium threads
        px, py = r.integers(0, n, 2); pts = [(px, py)]
        for k in range(10):
            px += r.integers(-12, 13); py += r.integers(-12, 13); pts.append((px, py))
        d.line(pts, fill=(200, 255, 240), width=1)
    return arr(im)


def gill_flesh(n=512, seed=23):
    """chamber walls inside the Mother cap: violet lamellae with a pink glow between them"""
    x, y = tile_xy(n)
    lam = np.abs(np.sin((x * 24 + noise(n, 20, seed) * 0.15) * math.pi))
    base = lerp(C((150, 60, 180)), C((255, 150, 230)), (lam ** 3)[..., None])
    base += N3(n, 2, seed + 1, 8)
    return base


def stem_inner(n=256, seed=29):
    """inside the Mother stem: fibrous white flesh with blue bruising"""
    x, y = tile_xy(n)
    a = fill(n, (220, 214, 200), 6, seed)
    a += (noise(n, 1.0, seed + 1, n) * 0)[..., None]
    streak = noise(n, 1.5, seed + 2)
    a += streak[..., None] * 10
    blue = np.clip(noise(n, 22, seed + 3) - 0.6, 0, 2)[..., None]
    a = a * (1 - 0.4 * blue) + C((60, 110, 200)) * 0.4 * blue
    return a


def house_wall(w=256, h=256, seed=31):
    """inside the fly-agaric houses: cream plaster with painted spirals"""
    a = fill(w, (238, 226, 196), 5, seed, h)
    im = img(a); d = ImageDraw.Draw(im)
    for (cx, cy, c) in ((64, 64, (220, 80, 60)), (192, 192, (90, 150, 220))):
        pts = [(cx + 3 * t * math.cos(t), cy + 3 * t * math.sin(t)) for t in np.linspace(0, 14, 120)]
        d.line(pts, fill=c, width=3)
    return arr(im)


def plat_top(n=256, seed=37):
    """the elevator disc: a spore print (radial gills printed dark purple on cream)"""
    x, y = tile_xy(n)
    dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    g = 0.5 + 0.5 * np.sin(th * 64)
    a = lerp(C((230, 220, 200)), C((70, 40, 80)), (g * np.clip((rr - 0.08) * 3, 0, 1) * np.clip((0.5 - rr) * 8, 0, 1))[..., None])
    return a + N3(n, 1, seed, 6)


def jumppad_tex(n=256):
    """bouncy mushroom pad: spotted glowing cap seen from above with a spiral"""
    x, y = tile_xy(n)
    dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    spiral = 0.5 + 0.5 * np.sin(th * 3 + rr * 40)
    a = lerp(C((255, 60, 170)), C((90, 255, 220)), spiral[..., None])
    a *= np.clip(1.3 - rr * 1.6, 0.3, 1)[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(6):
        ang = k * math.pi / 3
        cx, cy = n / 2 + n * 0.3 * math.cos(ang), n / 2 + n * 0.3 * math.sin(ang)
        d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(255, 250, 230))
    d.ellipse((n / 2 - 16, n / 2 - 16, n / 2 + 16, n / 2 + 16), fill=(255, 250, 230))
    return arr(im)


def kaleido(n=512, seed=41):
    """the Void: 8-fold kaleidoscope mandala (tileable)"""
    x, y = tile_xy(n)
    dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy) * 2; th = np.arctan2(dy, dx)
    k = np.abs(((th / (2 * math.pi) * 8) % 1.0) - 0.5) * 2         # 8-fold mirror wedge
    f = np.sin(rr * 18 + k * 6) * np.cos(k * 9 - rr * 7) + 0.4 * np.sin(rr * 40)
    h = (rr * 0.8 + f * 0.12 + k * 0.2)
    a = hue_arr(h, 0.9, np.clip(0.55 + 0.45 * f, 0.15, 1))
    edge = np.clip((rr - 0.92) * 10, 0, 1)[..., None]
    return a * (1 - edge) + C((30, 10, 50)) * edge


def void_floor(n=512, seed=43):
    x, y = tile_xy(n)
    dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy) * 2; th = np.arctan2(dy, dx)
    sp = np.sin(th * 5 - rr * 22)
    a = hue_arr(rr * 0.6 + th / (2 * math.pi), 0.8, 0.35 + 0.35 * (sp > 0))
    return a


def fairy_door(w=128, h=256):
    """a tiny glowing spiral door painted on the inside of the log (the secret)"""
    a = np.zeros((h, w, 3), np.float32) + C((60, 30, 20))
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 20, w - 8, h - 4), radius=56, fill=(120, 60, 160), outline=(255, 210, 120), width=6)
    cx, cy = w / 2, h * 0.55
    pts = [(cx + 3.2 * t * math.cos(t), cy + 3.2 * t * math.sin(t)) for t in np.linspace(0, 15, 200)]
    d.line(pts, fill=(140, 255, 230), width=4)
    d.ellipse((w - 34, h * 0.55 - 6, w - 22, h * 0.55 + 6), fill=(255, 220, 120))
    return arr(im)


def signboard(text, w=512, h=128, bg=(110, 70, 40), fg=(255, 230, 160)):
    a = np.zeros((h, w, 3), np.float32) + C(bg) + N3(w, 2, 5, 8, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=(60, 36, 20), width=6)
    sz = 72
    while d.textlength(text, font=font(sz)) > w - 40 and sz > 10: sz -= 2
    d.text((w / 2, h / 2), text, font=font(sz), fill=fg, anchor='mm', stroke_width=3, stroke_fill=(60, 30, 20))
    return arr(im)


def aura(n=256, seed=47):
    """soft rainbow noise used as an additive 'breathing colour' stage on many surfaces"""
    x, y = tile_xy(n)
    h = noise(n, 26, seed) * 0.25 + x * 1.0 + y * 1.0
    v = np.clip(0.5 + 0.35 * noise(n, 14, seed + 1), 0, 1)
    return hue_arr(h, 0.9, v)


def ripple(n=256, seed=53):
    """pond surface: concentric rainbow oil-slick swirls"""
    x, y = tile_xy(n)
    f = noise(n, 18, seed) * 0.6 + noise(n, 6, seed + 1) * 0.15
    h = (x + y) * 1.0 + f
    return hue_arr(h, 0.55, 0.55 + 0.25 * np.sin(f * 6))


def smoke_tex(w=128, h=256, seed=59):
    """spore haze puff (alpha)"""
    x, y = tile_xy(w, h)
    m = np.clip(1 - np.hypot((x - 0.5) * 2, (y - 0.5) * 1.6), 0, 1) ** 1.5
    al = np.clip(m * (0.6 + 0.5 * noise(w, 10, seed, h)), 0, 1) * 255
    col = np.zeros((h, w, 3), np.float32) + C((255, 230, 255))
    return col, al


def waterfall(w=128, h=512, seed=61):
    x, y = tile_xy(w, h)
    st = noise(w, 1.2, seed, h) * 0.5 + np.sin(x * 2 * math.pi * 9) * 0.2
    col = hue_arr(y * 2 + x * 0.3, 0.45, np.clip(0.7 + 0.3 * st, 0, 1))
    al = np.clip(0.55 + 0.4 * st, 0, 1) * 255 * np.clip(np.sin(x * math.pi) * 3, 0, 1)
    return col, al


def bulb(n=32, col=(255, 200, 80)):
    x, y = tile_xy(n)
    m = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1)[..., None]
    return C(col) * (0.5 + 0.5 * m) + 255 * m ** 3 * 0.5


# ------------------------------------------------------------------------------------------- sky
def sky_color(d):
    """psychedelic dusk: violet zenith, a slowly turning kaleidoscope swirl overhead, aurora ribbons, warm horizon"""
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    z = d[..., 2]; az = np.arctan2(d[..., 1], d[..., 0])
    el = np.arcsin(np.clip(z, -1, 1))
    t = np.clip(el / (math.pi / 2), -1, 1)
    hor = C((255, 150, 90)); mid = C((220, 70, 160)); zen = C((40, 20, 90))
    c = np.where((t < 0.25)[..., None], lerp(hor, mid, np.clip(t / 0.25, 0, 1)[..., None]),
                 lerp(mid, zen, np.clip((t - 0.25) / 0.75, 0, 1)[..., None]))
    c = np.where((t < 0)[..., None], lerp(hor, C((60, 30, 50)), np.clip(-t * 3, 0, 1)[..., None]), c)
    # aurora ribbons: wavy bands of hue across the mid sky
    band = np.sin(az * 3 + np.sin(az * 5) * 0.8 + t * 9)
    rib = np.exp(-((t - 0.45 - 0.08 * np.sin(az * 4)) ** 2) / 0.006) * (0.6 + 0.4 * band)
    c = c + hue_arr(az / (2 * math.pi) + t, 0.8, 1.0) * rib[..., None] * 0.55
    # overhead swirl (polar coords around the zenith)
    rr = np.sqrt(np.maximum(0, 1 - z)) ; th = az
    sw = np.sin(th * 6 + rr * 22) * np.exp(-rr * 2.2)
    c = c + hue_arr(rr * 1.5 + th / (2 * math.pi), 0.9, 1.0) * np.clip(sw, 0, 1)[..., None] * 0.35 * (z > 0)[..., None]
    # stars
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
        c = sky_color(D)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        # stars where the sky is dark
        st = rng.random((n, n)) > 0.9985
        c = np.where((st & (Dn[..., 2] > 0.35))[..., None], C((255, 250, 230)), c)
        img(c).save(os.path.join(d, f'trip_{k}.jpg'), quality=94)
    # cloud layer: wispy spirals (alpha via brightness, used additively)
    x, y = tile_xy(512)
    cl = noise(512, 18, 7) * 0.7 + noise(512, 5, 8) * 0.3
    cl = np.clip(cl - 0.2, 0, 2)
    col = hue_arr(x + y + cl * 0.2, 0.6, np.clip(cl * 0.6, 0, 1))
    img(col).save(os.path.join(d, 'trip_clouds.jpg'), quality=92)
    # editor/lightimage swatch
    img(np.zeros((64, 64, 3)) + C((200, 110, 170))).save(os.path.join(out, 'textures', NS, 'skylight.jpg'))


# ------------------------------------------------------------------------------------------- textures
def make_textures(W):
    W.save('moss', moss()); W.save('bank', bank()); W.save('dirt', dirt()); W.save('pebbles', pebbles())
    W.save('planks', planks()); W.save('rotten', rotten()); W.save('gill_flesh', gill_flesh()); W.save('stem_inner', stem_inner())
    W.save('house_wall', house_wall()); W.save('plat', plat_top()); W.save('jumppad', jumppad_tex())
    W.save('plat_floor', gill_flesh(256, 81) * 0.55 + fill(256, (90, 70, 60), 8, 83) * 0.45)
    W.save('kaleido', kaleido()); W.save('void_floor', void_floor()); W.save('fairy_door', fairy_door())
    W.save('aura', aura()); W.save('ripple', ripple())
    s, sa = smoke_tex(); W.save('haze', s, sa)
    s, sa = waterfall(); W.save('waterfall', s, sa)
    W.save('sign_void', signboard('IT\'S JUST SPORES', 512, 128, (60, 20, 90), (180, 255, 230)))
    W.save('sign_house', signboard('SPORE SWEET HOME', 512, 128))
    W.save('rings', shroom_models.tex_rings(256))
    W.save('bark_flat', shroom_models.tex_bark(256, 256, 71))
    W.save('dark', fill(64, (30, 22, 18), 3, 63)); W.save('trim', fill(64, (88, 56, 34), 4, 65))
    W.save('rubber', fill(64, (60, 30, 60), 3, 67)); W.save('chrome', fill(64, (200, 200, 215), 3, 69))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 73)); W.save('water_ed', fill(64, (80, 150, 200), 3, 75))
    for nm, c in (('bulb_c', (90, 255, 230)), ('bulb_m', (255, 90, 230)), ('bulb_y', (255, 220, 90)), ('bulb_v', (170, 110, 255))):
        W.save(nm, bulb(col=c))


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padshroom/shroom_textures.py)\n\n"
STEPS = {'moss': 'softsteps', 'bank': 'softsteps', 'dirt': 'softsteps', 'planks': 'woodsteps', 'rotten': 'woodsteps',
         'rings': 'woodsteps', 'bark_flat': 'woodsteps', 'trim': 'woodsteps', 'plat': 'softsteps', 'gill_flesh': 'softsteps',
         'stem_inner': 'softsteps', 'plat_floor': 'softsteps', 'pebbles': 'splashsteps', 'void_floor': 'softsteps'}
AURA = {'moss': (0.05, 0.05, 0.04), 'gill_flesh': (0.18, 0.14, 0.1), 'stem_inner': (0.06, 0.06, 0.08), 'house_wall': (0.04, 0.04, 0.05),
        'rotten': (0.06, 0.05, 0.03)}


def lm(name, steps=None, extra='', tex=None, aura=None):
    """lightmapped surface; optional additive rainbow 'aura' stage that breathes in and out"""
    t = tex or f'textures/{NS}/{name}'
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if aura:
        base, amp, freq = aura
        s += (f'\t{{\n\t\tmap textures/{NS}/aura\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin {base} {amp} 0 {freq}\n'
              '\t\ttcMod scale 0.25 0.25\n\t\ttcMod scroll 0.013 0.021\n\t\ttcMod turb 0 0.05 0 0.07\n\t}\n')
    return s + '}\n\n'


def glow(name, light, rgb, extra='', stage_extra='', tex=None):
    t = tex or f'textures/{NS}/{name}'
    return (f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n'
            f'\tsurfaceparm nolightmap\n{extra}\t{{\n\t\tmap {t}\n\t\trgbGen identity\n{stage_extra}\t}}\n}}\n\n')


def make_shader(W, out, model_shaders):
    S = SH
    special = {'jumppad', 'kaleido', 'void_floor', 'fairy_door', 'aura', 'ripple', 'haze', 'waterfall', 'nodraw_ns', 'water_ed',
               'sign_void', 'gill_flesh', 'plat'} | {n for n in W.sizes if n.startswith('bulb_')}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm), aura=AURA.get(nm))
    # the chamber gills glow softly (surface light) and breathe colour
    S += lm('gill_flesh', 'softsteps', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.5 0.9\n', aura=AURA['gill_flesh'])
    S += lm('plat', 'softsteps')
    S += lm('jumppad', extra='\tq3map_surfacelight 120\n\tq3map_lightRGB 1 0.4 0.9\n')[:-3] + (
        f'\t{{\n\t\tmap textures/{NS}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.25 0 0.8\n'
        '\t\ttcMod rotate 40\n\t}\n}\n\n')
    S += lm('fairy_door', extra='\tq3map_surfacelight 80\n\tq3map_lightRGB 0.5 1 0.9\n')[:-3] + (
        f'\t{{\n\t\tmap textures/{NS}/fairy_door\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.3 0.3 0 0.5\n\t}}\n}}\n\n')
    # the Void: walls swirl, floor turns
    S += (f'textures/{NS}/kaleido\n{{\n\tqer_editorimage textures/{NS}/kaleido\n\tq3map_surfacelight 160\n\tq3map_lightRGB 0.9 0.6 1\n'
          f'\tsurfaceparm nolightmap\n\tdeformVertexes wave 120 sin 0 6 0 0.25\n'
          f'\t{{\n\t\tmap textures/{NS}/kaleido\n\t\trgbGen identity\n\t\ttcMod rotate 12\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/aura\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.3 0.3 0 0.15\n\t\ttcMod scroll 0.1 0.07\n\t}}\n}}\n\n')
    S += (f'textures/{NS}/void_floor\n{{\n\tqer_editorimage textures/{NS}/void_floor\n\tsurfaceparm softsteps\n\tq3map_surfacelight 60\n'
          f'\tq3map_lightRGB 0.6 0.9 1\n\tsurfaceparm nolightmap\n'
          f'\t{{\n\t\tmap textures/{NS}/void_floor\n\t\trgbGen identity\n\t\ttcMod rotate -20\n\t}}\n}}\n\n')
    S += glow('sign_void', 80, '0.6 1 0.9')
    for nm in sorted(n for n in W.sizes if n.startswith('bulb_')):
        rgb = {'bulb_c': '0.4 1 0.9', 'bulb_m': '1 0.4 0.9', 'bulb_y': '1 0.85 0.4', 'bulb_v': '0.7 0.45 1'}[nm]
        ph = {'bulb_c': 0, 'bulb_m': 0.25, 'bulb_y': 0.5, 'bulb_v': 0.75}[nm]
        S += (f'textures/{NS}/{nm}\n{{\n\tqer_editorimage textures/{NS}/{nm}\n\tq3map_surfacelight 500\n\tq3map_lightRGB {rgb}\n'
              f'\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
              f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\trgbGen wave sin 0.7 0.3 {ph} 0.3\n\t}}\n}}\n\n')
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 1 0.78 0.85 300 220 38
	q3map_skylight 150 3
	skyparms env/{NS}/trip 512 -
	{{
		map env/{NS}/trip_clouds
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.35 0.2 0 0.05
		tcMod scale 2 2
		tcMod scroll 0.006 0.003
		tcMod rotate 2
	}}
	{{
		map textures/{NS}/aura
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.12 0.1 0.5 0.07
		tcMod scale 1.5 1.5
		tcMod scroll -0.004 0.008
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
	deformVertexes wave 128 sin 0 3 0 0.3
	cull none
	{{
		map textures/{NS}/ripple
		blendFunc GL_DST_COLOR GL_ONE
		rgbGen identity
		tcMod scale 0.5 0.5
		tcMod turb 0 0.08 0 0.1
		tcMod scroll 0.02 0.01
	}}
	{{
		map textures/{NS}/aura
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.18 0.12 0 0.1
		tcMod scale 0.3 0.3
		tcMod rotate 6
	}}
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.25 0.25 0.3 )
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
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen identity
		tcMod scroll 0.02 -1.4
	}}
}}

textures/{NS}/haze
{{
	qer_editorimage textures/{NS}/haze
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/haze.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen wave sin 0.35 0.15 0 0.1
		tcMod scroll 0.02 -0.08
		tcMod turb 0 0.08 0 0.12
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
    ms = shroom_models.make(out)
    make_shader(W, out, ms)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
