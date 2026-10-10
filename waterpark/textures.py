"""Procedural textures + shader + arena for 'waterpark' (Splash World: Cloud Lagoon).
make_all(out_dir) writes textures/waterpark/*.jpg|tga, scripts/waterpark.shader, scripts/waterpark.arena."""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

R = random.Random(11)
FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONT):
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def noise(n, blur, seed):
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((n, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, n * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * n, j * n))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(big.crop((n, n, 2 * n, 2 * n)), dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def C(c): return np.array(c, np.float32)
def N3(n, blur, seed, amp): return noise(n, blur, seed)[..., None] * amp
def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', 'waterpark'); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a.convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga'))
        else:
            im.save(os.path.join(self.dir, name + '.jpg'), quality=90)
        self.sizes[name] = im.size


def text_fit(d, text, maxw, size, font=FONT):
    while size > 8:
        f = ImageFont.truetype(font, size)
        if d.textlength(text, font=f) <= maxw: return f
        size -= 2
    return ImageFont.truetype(font, size)


def make_textures(W):
    n = 256
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    # --- deck pavers (warm sandstone, 4x4 slabs per texture) -----------------------------
    a = C((198, 184, 158)) + N3(n, 18, 1, 6) + N3(n, 1.0, 2, 7)
    for i in range(4):
        for j in range(4):
            a[j * 64:(j + 1) * 64, i * 64:(i + 1) * 64] += R.uniform(-9, 9)
    g = (xx % 64 < 2) | (yy % 64 < 2)
    a[g] = a[g] * 0.72
    a[(xx % 64 == 2) | (yy % 64 == 2)] *= 1.06
    W.save('deck', a)
    # deck accent (terracotta path)
    a = C((196, 120, 84)) + N3(n, 10, 3, 8) + N3(n, 1.0, 4, 8)
    for j in range(8):
        off = 32 if j % 2 else 0
        for i in range(5):
            a[j * 32:(j + 1) * 32, (i * 64 + off) % n:((i * 64 + off) % n) + 64] += R.uniform(-12, 12)
    a[(yy % 32 < 2)] *= 0.7
    for j in range(8):
        off = 32 if j % 2 else 0
        a[j * 32:(j + 1) * 32][:, ((xx[0] + off) % 64 < 2)] *= 0.7
    W.save('path', a)
    # --- pool tile mosaic --------------------------------------------------------------------
    n2 = 512; y2, x2 = np.mgrid[0:n2, 0:n2].astype(np.float32)
    a = np.zeros((n2, n2, 3), np.float32)
    for j in range(32):
        for i in range(32):
            v = R.uniform(-14, 14); h = R.random()
            base = (54, 160, 214) if h > 0.12 else ((38, 128, 196) if h > 0.04 else (110, 200, 230))
            a[j * 16:(j + 1) * 16, i * 16:(i + 1) * 16] = C(base) + v
    gm = (x2 % 16 < 2) | (y2 % 16 < 2)
    a[gm] = C((220, 236, 240))
    a += N3(n2, 1, 5, 4)
    W.save('pool_tile', a)
    # dark-blue lane line tile (dive pool floor)
    b = a.copy(); band = (x2 > 224) & (x2 < 288) & ~gm
    b[band] = C((20, 50, 120)) + N3(n2, 1, 6, 4)[band]
    W.save('pool_lane', b)
    # waterline band tile (deep blue + white) for upper pool walls
    a2 = a.copy(); a2[0:96] = C((20, 70, 150)) + N3(n2, 1, 7, 5)[0:96]
    a2[(y2 < 96) & gm] = C((200, 220, 230))
    W.save('pool_band', a2)
    # coping (white bullnose stone)
    a = C((236, 233, 224)) + N3(n, 8, 8, 5) + N3(n, 0.8, 9, 5)
    a[(xx % 128 < 2)] *= 0.8
    a[0:10] *= 0.9; a[-10:] *= 0.9
    W.save('coping', a)
    # white wall tiles (interiors / showers)
    a = np.zeros((n, n, 3), np.float32)
    for j in range(8):
        for i in range(8):
            a[j * 32:(j + 1) * 32, i * 32:(i + 1) * 32] = C((238, 240, 238)) + R.uniform(-5, 5)
    a[(xx % 32 < 2) | (yy % 32 < 2)] = C((178, 186, 190))
    W.save('tile_white', a + N3(n, 1, 10, 3))
    # aqua wall tiles with wave border
    a = np.zeros((n, n, 3), np.float32)
    for j in range(8):
        for i in range(8):
            a[j * 32:(j + 1) * 32, i * 32:(i + 1) * 32] = C((120, 210, 214)) + R.uniform(-8, 8)
    a[(xx % 32 < 2) | (yy % 32 < 2)] = C((236, 240, 236))
    W.save('tile_aqua', a)
    # --- stucco walls (several colours) ---------------------------------------------------------
    for name, col in (('stucco_sand', (238, 214, 172)), ('stucco_coral', (238, 142, 118)), ('stucco_mint', (150, 214, 186)),
                      ('stucco_sky', (128, 186, 230)), ('stucco_white', (240, 238, 230)), ('stucco_sun', (250, 204, 90))):
        a = C(col) + N3(n, 6, hash(name) % 1000, 7) + N3(n, 0.7, hash(name) % 997 + 3, 6)
        W.save(name, a)
    # trim band (wave pattern) for building tops
    im = Image.new('RGB', (n, 64), (245, 245, 240)); d = ImageDraw.Draw(im)
    pts = [(x, 32 + 14 * math.sin(x / n * 4 * math.pi)) for x in range(0, n + 1, 4)]
    d.polygon(pts + [(n, 64), (0, 64)], fill=(30, 140, 200))
    d.line(pts, fill=(255, 255, 255), width=4)
    W.save('trim_wave', im)
    # --- slides (glossy fibreglass) --------------------------------------------------------------
    for name, col in (('slide_red', (226, 52, 44)), ('slide_yellow', (250, 196, 30)), ('slide_blue', (40, 110, 226)),
                      ('slide_green', (46, 186, 90)), ('slide_purple', (150, 70, 200)), ('slide_orange', (250, 130, 30))):
        a = C(col) + N3(n, 2, hash(name) % 777, 3)
        sh = 0.82 + 0.28 * np.sin(np.pi * xx / (n - 1))
        a *= sh[..., None]
        a[:, 60:70] = np.minimum(255, a[:, 60:70] * 1.25 + 40)
        a[:, 186:192] = np.minimum(255, a[:, 186:192] * 1.15 + 20)
        W.save(name, a)
    # tube (translucent) stripes
    a = np.zeros((n, n, 3), np.float32) + C((60, 140, 230))
    a[(xx // 32) % 2 == 0] = C((130, 200, 250))
    W.save('tube', a + N3(n, 2, 12, 4))
    # --- water + caustics + spray ---------------------------------------------------------------
    t = (yy / n)[..., None]
    a = C((40, 150, 210)) * (0.85 + 0.25 * t) + N3(n, 6, 13, 10) + N3(n, 1.5, 14, 5)
    W.save('water', a)
    u = 2 * np.pi * xx / n; v = 2 * np.pi * yy / n
    c = (np.sin(5 * u + 2 * np.sin(3 * v)) + np.sin(5 * v + 2 * np.sin(2 * u)) + np.sin(3 * (u + v) + 1.3)) / 3
    c = np.exp(-(c / 0.14) ** 2)
    W.save('caustics', (c * 255)[..., None] * np.array([0.8, 1.0, 1.0]))
    im = Image.new('RGB', (128, 256), (0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(90):
        x = R.randint(0, 127); y0 = R.randint(0, 255); ln = R.randint(30, 140); b = R.randint(110, 255)
        for k in range(ln):
            d.point(((x + R.randint(-1, 1)) % 128, (y0 + k) % 256), fill=(b // 2 + 80, b // 2 + 100, b))
    W.save('spray', im.filter(ImageFilter.GaussianBlur(0.8)))
    # foam ring (for splash zones)
    a = np.zeros((n, n, 3), np.float32)
    f = np.clip(noise(n, 3, 15) * 0.8 + 0.2, 0, 1)
    W.save('foam', (f * 255)[..., None] * np.ones(3))
    # --- island rock / cliff --------------------------------------------------------------------
    a = C((150, 132, 112)) + N3(n, 14, 16, 16) + N3(n, 3, 17, 10) + N3(n, 0.8, 18, 6)
    strata = np.sin(yy / n * 2 * np.pi * 6 + noise(n, 12, 19) * 1.5)[..., None] * 9
    W.save('rock', a + strata)
    a = C((112, 98, 86)) + N3(n, 10, 20, 14) + N3(n, 1.2, 21, 8)
    W.save('rock_dark', a)
    # grotto crystal glow
    a = C((40, 120, 180)) + N3(n, 4, 22, 30)
    W.save('crystal', a)
    # --- palm trunk / thatch / frond ----------------------------------------------------------
    a = C((128, 96, 64)) + N3(n, 1, 23, 8)
    for k in range(0, n, 16):
        a[k:k + 4] *= 0.66; a[k + 4:k + 6] *= 1.15
    W.save('palm_trunk', a)
    a = C((196, 160, 86)) + N3(n, 0.6, 24, 18)
    for k in range(0, n, 32): a[k:k + 3] *= 0.6
    W.save('thatch', a)
    im = Image.new('RGBA', (256, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(2, 252, 5):
        t = x / 255.0
        L = 60 * math.sin(math.pi * min(1.0, t * 1.15) ** 0.7) * (1 - 0.35 * t) + 4
        g = 120 + R.randint(-25, 30); col = (40 + R.randint(-8, 20), g, 34 + R.randint(-6, 12), 255)
        for sgn in (-1, 1):
            d.line([(x, 64), (x + 22, 64 + sgn * L)], fill=col, width=2)
    d.line([(0, 64), (255, 64)], fill=(96, 120, 50, 255), width=4)
    a = np.asarray(im).astype(np.float32)
    W.save('frond', a[..., :3], alpha=a[..., 3])
    # --- fabrics / umbrellas / loungers / awnings ------------------------------------------------
    def stripes(c1, c2, k, vertical=True, size=256):
        a = np.zeros((size, size, 3), np.float32)
        idx = (np.arange(size) // (size // k)) % 2
        for i in range(size):
            col = c1 if idx[i] == 0 else c2
            if vertical: a[:, i] = col
            else: a[i, :] = col
        return a + N3(size, 1, k * 7, 4)
    W.save('umb_red', stripes((222, 52, 60), (250, 248, 240), 8))
    W.save('umb_blue', stripes((36, 110, 214), (250, 248, 240), 8))
    W.save('umb_yellow', stripes((250, 200, 40), (250, 248, 240), 8))
    W.save('umb_green', stripes((40, 170, 120), (250, 248, 240), 8))
    W.save('awning', stripes((24, 150, 200), (250, 250, 245), 8))
    W.save('awning_red', stripes((230, 60, 60), (250, 250, 245), 8))
    W.save('towel_a', stripes((250, 120, 40), (250, 230, 120), 4, False))
    W.save('towel_b', stripes((60, 180, 220), (250, 250, 250), 4, False))
    W.save('raft', stripes((250, 196, 40), (240, 90, 40), 4, False))
    W.save('beachball', stripes((230, 50, 50), (250, 250, 250), 6))
    # --- metal / glass / misc ------------------------------------------------------------------
    r = np.random.default_rng(25).random((n, n)).astype(np.float32)
    s = sum(np.roll(r, k, axis=1) for k in range(-12, 13)) / 25.0; s = (s - s.mean()) / (s.std() + 1e-6)
    W.save('metal', C((182, 188, 194)) + s[..., None] * 8)
    W.save('metal_white', C((236, 238, 240)) + s[..., None] * 5)
    W.save('metal_dark', C((70, 76, 84)) + s[..., None] * 6)
    a = C((170, 220, 235)) + N3(n, 30, 26, 10)
    a[(xx + yy) % 96 < 6] += 40
    W.save('glass', a)
    a = C((40, 40, 46)) + N3(n, 1, 27, 4)
    W.save('cable', a)
    W.save('rubber', C((46, 48, 52)) + N3(n, 1, 28, 5))
    # jump pad (animated arrows)
    im = Image.new('RGB', (n, n), (255, 150, 20)); d = ImageDraw.Draw(im)
    for yk in (0, 64, 128, 192):
        d.line([(40, yk + 52), (128, yk + 14), (216, yk + 52)], fill=(255, 250, 220), width=14)
    W.save('jumppad', im)
    im = Image.new('RGB', (n, n), (40, 40, 44)); d = ImageDraw.Draw(im)
    d.ellipse([20, 20, 236, 236], outline=(255, 160, 30), width=14)
    W.save('jumppad_ring', im)
    # lockers
    a = C((60, 120, 200)) + N3(n, 1, 29, 4)
    im = img(a); d = ImageDraw.Draw(im)
    for c_ in range(4):
        x0 = c_ * 64
        d.rectangle([x0, 0, x0 + 63, 255], outline=(30, 60, 110), width=3)
        d.rectangle([x0 + 10, 20, x0 + 54, 30], fill=(30, 60, 110)); d.rectangle([x0 + 10, 36, x0 + 54, 46], fill=(30, 60, 110))
        d.rectangle([x0 + 44, 120, x0 + 52, 150], fill=(200, 200, 205))
        d.ellipse([x0 + 14, 200, x0 + 30, 216], fill=(240, 200, 60))
    W.save('locker', im)
    # crates
    a = C((176, 132, 80)) + N3(n, 1, 30, 10)
    for k in range(0, n, 32): a[k:k + 3] *= 0.7
    a[:12] *= 0.7; a[-12:] *= 0.7; a[:, :12] *= 0.7; a[:, -12:] *= 0.7
    im = img(a); d = ImageDraw.Draw(im); d.line([(12, 12), (244, 244)], fill=(110, 76, 40), width=12)
    W.save('crate', im)
    # windows (sky reflection with frame)
    im = Image.new('RGB', (n, n), (150, 200, 235)); d = ImageDraw.Draw(im)
    for y in range(n): d.line([(0, y), (n, y)], fill=(110 + y // 6, 170 + y // 10, 230))
    d.rectangle([0, 0, n - 1, n - 1], outline=(245, 245, 240), width=12); d.line([(128, 0), (128, n)], fill=(245, 245, 240), width=8)
    W.save('window', im)
    # interior light panel
    im = Image.new('RGB', (n, n), (255, 250, 230)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, n - 1, n - 1], outline=(190, 190, 185), width=12)
    W.save('lightpanel', im)
    # dark wood / planks / bamboo
    def wood(light, dark, k, seed, planks=True):
        g = ((np.sin(yy * 2 * np.pi * k / n + noise(n, 10, seed) * 6) + 1) / 2)[..., None]
        a = C(dark) * (1 - g) + C(light) * g + N3(n, 1.0, seed + 50, 8)
        if planks:
            for k2 in range(0, n, 64): a[k2:k2 + 3] *= 0.6
        return a
    W.save('teak', wood((168, 112, 66), (128, 80, 44), 14, 31))
    W.save('wood_dark', wood((110, 72, 44), (76, 48, 28), 12, 32))
    W.save('wood_white', wood((236, 230, 216), (214, 204, 186), 10, 33))
    a = C((206, 182, 110)) + N3(n, 1, 34, 8)
    for k in range(0, n, 32):
        a[:, k:k + 4] *= 0.7
        for kk in range(0, n, 48): a[kk:kk + 3, k:k + 32] *= 0.8
    W.save('bamboo', a)
    # chalk menu board
    im = img(C((34, 52, 44)) + N3(n, 8, 35, 8)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, n - 1, n - 1], outline=(150, 100, 60), width=12)
    f = ImageFont.truetype(FONT, 26); f2 = ImageFont.truetype(FONT, 20)
    for t, y, c in (('SNACKS', 20, (250, 220, 120)), ('Fries ..... 3', 70, (235, 235, 225)), ('Pad Dog ... 4', 104, (235, 235, 225)),
                    ('Muffin .... 2', 138, (235, 235, 225)), ('Ice Pop ... 1', 172, (235, 235, 225)), ('Slushie ... 3', 206, (235, 235, 225))):
        ff = f if y == 20 else f2; tw = d.textlength(t, font=ff); d.text(((n - tw) / 2, y), t, fill=c, font=ff)
    W.save('menu', im)
    # tv / scoreboard screen
    im = Image.new('RGB', (n, 128), (16, 24, 40)); d = ImageDraw.Draw(im)
    f = text_fit(d, 'NEXT WAVE IN 0:42', 230, 30)
    tw = d.textlength('NEXT WAVE IN 0:42', font=f); d.text(((n - tw) / 2, 44), 'NEXT WAVE IN 0:42', fill=(255, 200, 40), font=f)
    W.save('screen', im)
    # treasure / gold
    W.save('gold', C((236, 184, 50)) + N3(n, 2, 36, 20))
    # kids tiles (rubber floor, colourful)
    a = np.zeros((n, n, 3), np.float32)
    pal = [(240, 80, 80), (250, 200, 50), (80, 180, 240), (100, 200, 110)]
    for j in range(4):
        for i in range(4):
            a[j * 64:(j + 1) * 64, i * 64:(i + 1) * 64] = C(pal[(i + j * 3) % 4])
    a[(xx % 64 < 2) | (yy % 64 < 2)] *= 0.75
    W.save('rubberfloor', a + N3(n, 1, 37, 6))
    # mushroom cap dots
    im = Image.new('RGB', (n, n), (228, 44, 56)); d = ImageDraw.Draw(im)
    for _ in range(14):
        cx, cy, rr = R.randint(0, n), R.randint(0, n), R.randint(10, 22)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(252, 250, 240))
    W.save('mushroom', im)
    a = np.zeros((n, n, 3), np.float32)
    par = (((xx // 128) + (yy // 128)) % 2 == 0)[..., None]
    a = np.where(par, C((240, 236, 226)), C((40, 44, 52))) + N3(n, 1, 38, 5)
    W.save('checker', a)
    # signs -----------------------------------------------------------------------------------
    def sign(name, text, bg, fg, sub=None, w=512, h=128, icon=None, border=None):
        im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
        d.rounded_rectangle([6, 6, w - 7, h - 7], 18, outline=border or fg, width=6)
        f = text_fit(d, text, w - 60, int(h * (0.55 if sub is None else 0.46)))
        tw = d.textlength(text, font=f)
        ty = (h - f.size * 1.25) / 2 if sub is None else h * 0.06
        d.text(((w - tw) / 2 + 3, ty + 3), text, fill=tuple(int(v * 0.55) for v in bg), font=f)
        d.text(((w - tw) / 2, ty), text, fill=fg, font=f)
        if sub:
            f2 = text_fit(d, sub, w - 80, int(h * 0.2)); tw2 = d.textlength(sub, font=f2)
            d.text(((w - tw2) / 2, h - f2.size * 1.45), sub, fill=fg, font=f2)
        W.save(name, im)
    sign('sign_splash', 'SPLASH WORLD', (20, 130, 210), (255, 255, 255), 'CLOUD LAGOON  *  EST. 2026', w=1024, h=256)
    sign('sign_kamikaze', 'KAMIKAZE', (220, 44, 40), (255, 240, 200), 'FREE FALL SLIDE')
    sign('sign_tornado', 'TORNADO', (40, 100, 220), (255, 255, 255), 'TUBE SLIDE')
    sign('sign_rapids', 'RAPIDS', (40, 170, 90), (255, 255, 255), 'TO THE INFINITY POOL')
    sign('sign_wave', 'WAVE POOL', (30, 160, 200), (255, 255, 255))
    sign('sign_river', 'LAZY RIVER', (40, 150, 100), (255, 255, 255))
    sign('sign_pirate', 'PIRATE COVE', (60, 40, 30), (250, 210, 90))
    sign('sign_kids', 'SPLASH ZONE', (250, 190, 40), (40, 40, 60))
    sign('sign_snack', 'SNACK SHACK', (230, 90, 50), (255, 255, 255))
    sign('sign_change', 'CHANGING ROOMS', (90, 90, 180), (255, 255, 255))
    sign('sign_gondola', 'GONDOLA', (40, 40, 60), (255, 220, 90), 'VALLEY STATION  ->  2400 m')
    sign('sign_bar', 'INFINITY BAR', (30, 30, 50), (120, 220, 255))
    sign('sign_dive', 'HIGH DIVE', (200, 40, 80), (255, 255, 255), 'EXPERTS ONLY')
    sign('sign_nodive', 'NO DIVING', (250, 250, 250), (220, 30, 30))
    sign('sign_tickets', 'TICKETS', (30, 30, 90), (255, 230, 90))
    sign('sign_wave_mach', 'WAVE MACHINE', (60, 70, 80), (255, 210, 60), 'STAFF ONLY')
    sign('sign_lifeguard', 'LIFEGUARD', (220, 40, 40), (255, 255, 255))
    sign('sign_grotto', '???', (20, 30, 40), (120, 230, 255))
    sign('sign_tall', 'YOU MUST BE THIS TALL', (250, 220, 60), (40, 40, 60))
    # depth markers
    for dname, txt in (('depth_1', '1 m'), ('depth_2', '2 m'), ('depth_5', '5 m')):
        im = Image.new('RGB', (128, 64), (235, 240, 240)); d = ImageDraw.Draw(im)
        f = ImageFont.truetype(FONT, 34); tw = d.textlength(txt, font=f); d.text(((128 - tw) / 2, 8), txt, fill=(20, 40, 90), font=f)
        W.save(dname, im)
    # levelshot-ish logo not needed


SHADER_HEAD = '// waterpark.shader - Splash World: Cloud Lagoon (generated by wop_tools/waterpark)\n\n'


def lm_shader(name, extra='', steps=None):
    s = f'textures/waterpark/{name}\n{{\n\tqer_editorimage textures/waterpark/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/waterpark/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    return s


def make_shader(W, out):
    S = SHADER_HEAD
    S += '''textures/waterpark/sky
{
	qer_editorimage env/ueberdenwolken_ft
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/waterpark/skylight
	q3map_sun 1 0.94 0.84 300 30 34
	q3map_skylight 150 3
	skyparms env/ueberdenwolken - -
}

'''
    steps = {'deck': None, 'path': None, 'coping': None, 'tile_white': 'splashsteps', 'tile_aqua': 'splashsteps',
             'teak': 'woodsteps', 'wood_dark': 'woodsteps', 'wood_white': 'woodsteps', 'bamboo': 'woodsteps',
             'crate': 'woodsteps', 'rubberfloor': 'softsteps', 'thatch': 'softsteps', 'metal': 'metalsteps',
             'metal_white': 'metalsteps', 'metal_dark': 'metalsteps'}
    plain = ['deck', 'path', 'coping', 'tile_white', 'tile_aqua', 'stucco_sand', 'stucco_coral', 'stucco_mint',
             'stucco_sky', 'stucco_white', 'stucco_sun', 'trim_wave', 'rock', 'rock_dark', 'palm_trunk', 'thatch',
             'umb_red', 'umb_blue', 'umb_yellow', 'umb_green', 'awning', 'awning_red', 'towel_a', 'towel_b', 'raft',
             'beachball', 'metal', 'metal_white', 'metal_dark', 'rubber', 'locker', 'crate', 'teak', 'wood_dark',
             'wood_white', 'bamboo', 'menu', 'gold', 'rubberfloor', 'mushroom', 'jumppad_ring', 'checker']
    for nme in plain:
        if nme in W.sizes: S += lm_shader(nme, steps=steps.get(nme))
    for nme in sorted(k for k in W.sizes if k.startswith(('sign_', 'depth_'))):
        S += lm_shader(nme)
    # slides: slick + glossy env highlight
    for nme in ('slide_red', 'slide_yellow', 'slide_blue', 'slide_green', 'slide_purple', 'slide_orange'):
        S += f'''textures/waterpark/{nme}
{{
	qer_editorimage textures/waterpark/{nme}
	surfaceparm slick
	surfaceparm splashsteps
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/waterpark/{nme}
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/waterpark/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.10 0.10 0.10 )
		tcGen environment
	}}
}}

'''
    # pool tiles with animated caustics
    for nme in ('pool_tile', 'pool_lane', 'pool_band'):
        S += f'''textures/waterpark/{nme}
{{
	qer_editorimage textures/waterpark/{nme}
	surfaceparm splashsteps
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/waterpark/{nme}
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/waterpark/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.22 0.22 )
		tcMod scale 0.5 0.5
		tcMod turb 0 0.04 0 0.15
		tcMod scroll 0.02 0.013
	}}
}}

'''
    # water bodies
    def water(nme, alpha, turb, scroll, wave=None):
        dv = f'\tdeformVertexes wave 256 sin 0 {wave[0]} 0 {wave[1]}\n' if wave else ''
        return f'''textures/waterpark/{nme}
{{
	qer_editorimage textures/waterpark/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	tessSize 64
{dv}	{{
		map textures/waterpark/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const {alpha}
		rgbGen identity
		tcMod turb 0 {turb} 0 0.2
		tcMod scroll {scroll}
	}}
	{{
		map textures/waterpark/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.16 0.19 0.19 )
		tcMod scale 0.7 0.7
		tcMod scroll -0.02 0.03
	}}
}}

'''
    S += water('water_pool', 0.45, 0.06, '0.01 0.006')
    S += water('water_river', 0.5, 0.05, '0.0 0.08')
    S += water('water_river_x', 0.5, 0.05, '0.08 0.0')
    S += water('water_wave', 0.5, 0.2, '0.02 0.03', wave=(3, 0.25))
    S += water('water_lagoon', 0.4, 0.08, '0.01 0.01')
    S += water('water_deep', 0.55, 0.05, '0.005 0.01')
    # translucent / additive decoration
    S += '''textures/waterpark/spray
{
	qer_editorimage textures/waterpark/spray
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{
		map textures/waterpark/spray
		blendFunc GL_ONE GL_ONE
		rgbGen identity
		tcMod scroll 0 -1.4
	}
	{
		map textures/waterpark/spray
		blendFunc GL_ONE GL_ONE
		rgbGen identity
		tcMod scale 1.7 1
		tcMod scroll 0.05 -2.1
	}
}

textures/waterpark/spray_up
{
	qer_editorimage textures/waterpark/spray
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{
		map textures/waterpark/spray
		blendFunc GL_ONE GL_ONE
		rgbGen identity
		tcMod scroll 0 1.2
	}
}

textures/waterpark/waterfall
{
	qer_editorimage textures/pad_liquidfx/pad_waterfall
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{
		map textures/pad_liquidfx/pad_waterfall
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		tcMod scroll 0 -1.2
	}
	{
		map textures/pad_liquidfx/pad_waterfall
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		tcMod scroll 0.03 -0.7
	}
}

textures/waterpark/frond
{
	qer_editorimage textures/waterpark/frond
	qer_alphafunc greater 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm alphashadow
	surfaceparm pointlight
	cull none
	deformVertexes wave 194 sin 0 1.2 0 0.35
	{
		map textures/waterpark/frond
		alphaFunc GE128
		depthWrite
		rgbGen vertex
	}
}

textures/waterpark/glass
{
	qer_editorimage textures/waterpark/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nomarks
	{
		map textures/waterpark/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.4 0.42 )
	}
}

textures/waterpark/glassns
{
	qer_editorimage textures/waterpark/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	{
		map textures/waterpark/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.4 0.42 )
	}
}

textures/waterpark/tube
{
	qer_editorimage textures/waterpark/tube
	qer_trans 0.5
	surfaceparm trans
	surfaceparm slick
	surfaceparm nomarks
	cull none
	{
		map textures/waterpark/tube
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.45
		rgbGen identity
	}
}

textures/waterpark/cable
{
	qer_editorimage textures/waterpark/cable
	surfaceparm nonsolid
	surfaceparm nomarks
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/waterpark/cable
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}

textures/waterpark/beam_ns
{
	qer_editorimage textures/waterpark/wood_dark
	surfaceparm nonsolid
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/waterpark/wood_dark
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}

textures/waterpark/sail
{
	qer_editorimage textures/pad_pirate/segel
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm alphashadow
	cull none
	{
		map textures/pad_pirate/segel
		rgbGen vertex
	}
}

textures/waterpark/jumppad
{
	qer_editorimage textures/waterpark/jumppad
	surfaceparm nodamage
	surfaceparm nolightmap
	surfaceparm metalsteps
	q3map_surfacelight 120
	{
		map textures/waterpark/jumppad
		tcMod scroll 0 -1.5
		rgbGen identity
	}
}

textures/waterpark/window
{
	qer_editorimage textures/waterpark/window
	surfaceparm nomarks
	{
		map textures/waterpark/window
		rgbGen identity
	}
	{
		map $lightmap
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}

textures/waterpark/lightpanel
{
	qer_editorimage textures/waterpark/lightpanel
	surfaceparm nomarks
	q3map_surfacelight 900
	q3map_lightSubdivide 64
	{
		map textures/waterpark/lightpanel
		rgbGen identity
	}
}

textures/waterpark/crystal
{
	qer_editorimage textures/waterpark/crystal
	surfaceparm nomarks
	q3map_surfacelight 260
	q3map_lightRGB 0.4 0.8 1.0
	{
		map textures/waterpark/crystal
		rgbGen identity
	}
	{
		map textures/waterpark/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.4 0.3 0 0.3
		tcMod scroll 0.1 0.07
	}
}

textures/waterpark/screen
{
	qer_editorimage textures/waterpark/screen
	surfaceparm nomarks
	q3map_surfacelight 80
	{
		map textures/waterpark/screen
		rgbGen identity
	}
}

textures/waterpark/foam
{
	qer_editorimage textures/waterpark/foam
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	{
		map textures/waterpark/foam
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.5 0.5 0.5 )
		tcMod scroll 0.05 0.08
	}
}

'''
    S += '''levelshots/waterparkB
{
	nomipmaps
	{
		animmap 0.5 levelshots/waterparkB1 levelshots/waterparkB2 levelshots/waterparkB3
	}
}

'''
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', 'waterpark.shader'), 'w').write(S)
    # sky light image (1x1 colour sample used by q3map_lightimage)
    Image.new('RGB', (8, 8), (205, 222, 255)).save(os.path.join(W.dir, 'skylight.jpg'))


def make_arena(out):
    open(os.path.join(out, 'scripts', 'waterpark.arena'), 'w').write(
        '{\nmap "waterpark"\nlongname "Splash World: Cloud Lagoon"\ntype "ffa lps team ft ctkd"\nfraglimit "25"\ntimelimit "15"\n}\n')


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    make_shader(W, out)
    make_arena(out)
    return W
