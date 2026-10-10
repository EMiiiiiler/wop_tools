#!/usr/bin/env python3
"""Procedurally paints every Crater Crust texture (original artwork) + the night skybox."""
import os, math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
TD = os.path.join(OUT, 'textures/cratercrust'); ED = os.path.join(OUT, 'env/cratercrust')
os.makedirs(TD, exist_ok=True); os.makedirs(ED, exist_ok=True)
FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
FONT_B = '/usr/share/fonts/truetype/google-fonts/Poppins-Black.ttf' if os.path.exists('/usr/share/fonts/truetype/google-fonts/Poppins-Black.ttf') else FONT
rng = np.random.default_rng(7)
random.seed(7)


def font(sz, black=False): return ImageFont.truetype(FONT_B if black else FONT, sz)


def noise(w, h, scale=8, octaves=4, seed=0):
    """tileable value noise in 0..1"""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = scale * (2 ** o)
        g = r.random((s, s))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        # tile: blend wrapped copy
        a = np.asarray(img, float) / 255
        a = (a + np.roll(a, w // 2, 1) + np.roll(a, h // 2, 0) + np.roll(np.roll(a, w // 2, 1), h // 2, 0)) / 4
        out += a * amp; tot += amp; amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


def col(img_arr, c1, c2, n):
    c1 = np.array(c1, float); c2 = np.array(c2, float)
    return (c1[None, None] * (1 - n[..., None]) + c2[None, None] * n[..., None])


def save(name, im, alpha=False):
    if isinstance(im, np.ndarray):
        im = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    if alpha:
        im.convert('RGBA').save(os.path.join(TD, name + '.tga'))
    else:
        im.convert('RGB').save(os.path.join(TD, name + '.jpg'), quality=92)


def grime(arr, amt=18, seed=1, scale=6):
    n = noise(arr.shape[1], arr.shape[0], scale, 4, seed)
    return arr - (n[..., None] - 0.5) * amt * 2


def panel_lines(d, w, h, step, color, width=2):
    for x in range(0, w, step): d.line([(x, 0), (x, h)], fill=color, width=width)
    for y in range(0, h, step): d.line([(0, y), (w, y)], fill=color, width=width)


# ------------------------------------------------------------------ logo (original): pizza-slice crescent moon
def logo(size):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    # crescent moon = big disc minus offset disc, filled as cheesy pizza
    mask = Image.new('L', (s, s), 0); md = ImageDraw.Draw(mask)
    md.ellipse([s * .08, s * .08, s * .92, s * .92], fill=255)
    md.ellipse([s * .32, s * .02, s * 1.1, s * .80], fill=0)
    crust = Image.new('RGBA', (s, s), (214, 140, 60, 255))
    cheese = Image.new('L', (s, s), 0); cd = ImageDraw.Draw(cheese)
    cd.ellipse([s * .14, s * .14, s * .86, s * .86], fill=255)
    cd.ellipse([s * .30, s * .04, s * 1.04, s * .78], fill=0)
    im.paste(crust, (0, 0), mask)
    im.paste(Image.new('RGBA', (s, s), (255, 206, 60, 255)), (0, 0), cheese)
    # pepperoni craters
    for (cx, cy, r) in ((.25, .52, .07), (.34, .74, .06), (.52, .82, .05), (.21, .33, .045)):
        d.ellipse([s * (cx - r), s * (cy - r), s * (cx + r), s * (cy + r)], fill=(196, 40, 36, 255), outline=(150, 25, 25, 255), width=max(1, s // 100))
    # little star
    cx, cy, r = s * .78, s * .26, s * .1
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * .42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=(120, 240, 255, 255))
    return im


# ------------------------------------------------------------------ floors
def floor_tile():
    w = 256; im = Image.new('RGB', (w, w)); d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            c = (24, 30, 72) if (i + j) % 2 else (40, 170, 170)
            d.rectangle([i * 64, j * 64, i * 64 + 63, j * 64 + 63], fill=c)
    a = np.asarray(im, float)
    a = grime(a, 10, 3)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(40):
        x, y = random.randrange(w), random.randrange(w)
        d.point((x, y), fill=(220, 230, 255))
    panel_lines(d, w, w, 64, (12, 14, 30), 2)
    save('cc_floor_tile', im)


def carpet():
    w = 256; base = np.zeros((w, w, 3)) + np.array([18, 10, 40])
    im = Image.fromarray(base.astype(np.uint8)); d = ImageDraw.Draw(im)
    cols = [(255, 60, 200), (60, 230, 255), (255, 230, 60), (120, 255, 120), (255, 120, 40)]
    for k in range(26):
        x, y = random.randrange(w), random.randrange(w); c = random.choice(cols); t = random.random()
        if t < .3:   # ringed planet
            r = random.randint(7, 14)
            for dx in (-w, 0, w):
                for dy in (-w, 0, w):
                    d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=c)
                    d.ellipse([x + dx - r * 2, y + dy - r // 2, x + dx + r * 2, y + dy + r // 2], outline=random.choice(cols), width=2)
        elif t < .65:  # squiggle
            pts = [(x + i * 6, y + 6 * math.sin(i * 1.3)) for i in range(7)]
            for dx in (-w, 0, w):
                for dy in (-w, 0, w):
                    d.line([(px + dx, py + dy) for px, py in pts], fill=c, width=3)
        else:  # star
            r = random.randint(4, 8)
            for dx in (-w, 0, w):
                for dy in (-w, 0, w):
                    d.line([(x + dx - r, y + dy), (x + dx + r, y + dy)], fill=c, width=2)
                    d.line([(x + dx, y + dy - r), (x + dx, y + dy + r)], fill=c, width=2)
    a = np.asarray(im, float); a = grime(a, 8, 4, 16)
    save('cc_carpet', a)


def kitchen_tile():
    w = 256; im = Image.new('RGB', (w, w), (236, 236, 228)); d = ImageDraw.Draw(im)
    r = random.Random(5)
    for i in range(8):
        for j in range(8):
            if r.random() < 0.06: d.rectangle([i * 32, j * 32, i * 32 + 31, j * 32 + 31], fill=(70, 200, 210))
    panel_lines(d, w, w, 32, (175, 175, 170), 2)
    save('cc_kitchen_tile', grime(np.asarray(im, float), 8, 5))
    im = Image.new('RGB', (w, w)); d = ImageDraw.Draw(im)
    for i in range(8):
        for j in range(8):
            d.rectangle([i * 32, j * 32, i * 32 + 31, j * 32 + 31], fill=(185, 55, 45) if (i + j) % 2 else (225, 210, 180))
    panel_lines(d, w, w, 32, (90, 70, 60), 2)
    save('cc_kitchen_floor', grime(np.asarray(im, float), 14, 6, 4))


def asphalt():
    w = 256; n = noise(w, w, 32, 3, 11)
    a = col(None, (34, 34, 38), (70, 70, 76), n)
    a += rng.normal(0, 7, a.shape)
    save('cc_asphalt', a)


def concrete(name='cc_concrete', base=(150, 148, 142), lines=128):
    w = 256; n = noise(w, w, 8, 4, 12)
    a = col(None, np.array(base) - 25, np.array(base) + 10, n) + rng.normal(0, 4, (w, w, 3))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    if lines: panel_lines(d, w, w, lines, tuple(int(x * .6) for x in base), 2)
    save(name, im)


def roof():
    w = 256; a = np.zeros((w, w, 3)) + 95
    a += rng.normal(0, 22, (w, w, 1)); a = a * np.array([1.0, .97, .92])
    a = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6)), float)
    save('cc_roof', a)


def grass():
    w = 256; n = noise(w, w, 16, 4, 21)
    a = col(None, (30, 70, 25), (80, 140, 50), n) + rng.normal(0, 10, (w, w, 3))
    save('cc_grass', a)


# ------------------------------------------------------------------ walls
def wall_mural():
    w = 512
    y = np.linspace(0, 1, w)[:, None]
    top = np.array([25, 10, 60]); bot = np.array([90, 30, 120])
    a = top[None, None] * (1 - y[..., None]) + bot[None, None] * y[..., None]
    a = np.repeat(a, w, 1)
    n = noise(w, w, 4, 4, 31)
    a += (n[..., None] - .5) * np.array([60, 20, 80])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(260):
        x, yy = random.randrange(w), random.randrange(w); b = random.randint(150, 255)
        d.point((x, yy), fill=(b, b, 255))
        if random.random() < .05:
            d.line([(x - 3, yy), (x + 3, yy)], fill=(b, b, 255)); d.line([(x, yy - 3), (x, yy + 3)], fill=(b, b, 255))
    # planets (original arrangement)
    def planet(cx, cy, r, c1, c2, ring=None):
        for dx in (-w, 0, w):
            pl = Image.new('RGBA', (w, w), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
            for i in range(r, 0, -1):
                t = i / r; c = tuple(int(c1[k] * t + c2[k] * (1 - t)) for k in range(3))
                pd.ellipse([cx + dx - i, cy - i, cx + dx + i, cy + i], fill=c + (255,))
            if ring:
                pd.ellipse([cx + dx - r * 1.9, cy - r * .45, cx + dx + r * 1.9, cy + r * .45], outline=ring + (255,), width=5)
            im.paste(pl, (0, 0), pl)
    planet(110, 140, 46, (255, 150, 60), (255, 220, 120), (90, 230, 255))
    planet(390, 90, 22, (80, 220, 160), (190, 255, 220))
    planet(330, 330, 34, (220, 70, 160), (255, 160, 220), (255, 240, 120))
    # comet
    d.line([(40, 420), (180, 360)], fill=(160, 220, 255), width=3); d.ellipse([176, 354, 190, 368], fill=(240, 250, 255))
    # neon wave band near the bottom
    for k, c in enumerate(((60, 230, 255), (255, 60, 200))):
        pts = [(x, 470 + k * 14 + 8 * math.sin(x / 512 * 2 * math.pi * 3 + k)) for x in range(0, w + 8, 8)]
        d.line(pts, fill=c, width=4)
    save('cc_wall_mural', im)


def store_wall():
    w = 256; n = noise(w, w, 8, 4, 41)
    a = col(None, (120, 130, 140), (160, 168, 175), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for y in range(0, w, 32): d.line([(0, y), (w, y)], fill=(95, 100, 110), width=3)
    for y in range(0, w, 64):
        off = 0 if (y // 64) % 2 == 0 else 32
        for x in range(off, w, 64): d.line([(x, y), (x, y + 32)], fill=(95, 100, 110), width=3)
    save('cc_store_wall', im)


def facade():
    w = 256; n = noise(w, w, 8, 4, 51)
    a = col(None, (40, 24, 70), (70, 44, 110), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    panel_lines(d, w, w, 128, (20, 10, 40), 4)
    for x in (16, 112, 144, 240):
        for y in (16, 112, 144, 240): d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(150, 140, 190))
    d.rectangle([0, 200, w, 212], fill=(60, 230, 255))
    save('cc_facade', im)


def brick():
    w = 256; im = Image.new('RGB', (w, w), (90, 80, 70)); d = ImageDraw.Draw(im)
    bh, bw = 32, 64
    for j in range(w // bh):
        off = 0 if j % 2 == 0 else bw // 2
        for i in range(-1, w // bw + 1):
            x0 = i * bw + off; c = random.choice([(150, 70, 45), (165, 82, 50), (135, 60, 40), (175, 95, 60)])
            d.rectangle([x0 + 3, j * bh + 3, x0 + bw - 3, j * bh + bh - 3], fill=c)
    save('cc_brick', grime(np.asarray(im, float), 20, 52))
    # oven top: brick + soot
    a = np.asarray(im, float) * 0.55
    save('cc_oven_top', grime(a, 25, 53))


def steel(name='cc_steel', tint=(1, 1, 1), base=150):
    w = 256
    a = np.zeros((w, w)) + base + rng.normal(0, 1, (1, w)).repeat(w, 0) * 0 + rng.normal(0, 9, (w, 1)).repeat(w, 1)
    a = a + rng.normal(0, 3, (w, w))
    a = np.stack([a * tint[0], a * tint[1], a * tint[2]], -1)
    save(name, a)


def counter_top():
    w = 256; n = noise(w, w, 16, 4, 61)
    a = col(None, (200, 200, 205), (235, 235, 240), n)
    for k in range(120):
        x, y = random.randrange(w), random.randrange(w)
        a[y:y + 2, x:x + 2] = (90, 90, 120)
    save('cc_counter_top', a)


def counter_front():
    w = 256; a = np.zeros((w, w, 3)) + np.array([200, 40, 60])
    im = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(im)
    for y in (0, 128):
        d.rectangle([0, y + 54, w, y + 74], fill=(250, 220, 80))
    for k in range(10):
        x, y = random.randrange(w), random.randrange(w)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 220))
    save('cc_counter_front', grime(np.asarray(im, float), 10, 62))


def wood():
    w = 256
    x = np.arange(w)[None, :].repeat(w, 0); y = np.arange(w)[:, None].repeat(w, 1)
    n = noise(w, w, 4, 3, 71)
    rings = (np.sin((y / w * 2 * math.pi * 6) + n * 6) + 1) / 2
    a = col(None, (120, 70, 35), (175, 115, 60), rings * .7 + n * .3)
    save('cc_wood', a)
    # cutting board (lighter)
    save('cc_cuttingboard', col(None, (190, 150, 95), (230, 195, 140), rings * .5 + n * .5))
    # crate
    im = Image.fromarray(np.clip(col(None, (150, 105, 55), (195, 150, 90), rings * .6 + n * .4), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for k in range(0, w, 64): d.line([(0, k), (w, k)], fill=(90, 60, 30), width=4)
    d.rectangle([2, 2, w - 3, w - 3], outline=(80, 50, 25), width=10)
    d.line([(10, 10), (w - 10, w - 10)], fill=(110, 75, 40), width=14)
    save('cc_crate', im)
    # fence planks
    im = Image.fromarray(np.clip(col(None, (110, 80, 50), (150, 115, 75), n), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 32): d.line([(k, 0), (k, w)], fill=(60, 40, 25), width=4)
    d.rectangle([0, 40, w, 52], fill=(90, 65, 40)); d.rectangle([0, 200, w, 212], fill=(90, 65, 40))
    save('cc_fence', im)


def vinyl():
    w = 256; n = noise(w, w, 8, 3, 81)
    a = col(None, (170, 20, 40), (225, 50, 70), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64): d.line([(k, 0), (k, w)], fill=(120, 10, 25), width=3)
    for x in range(32, w, 64):
        for y in range(32, w, 64): d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(110, 10, 25))
    save('cc_vinyl', im)


def pizzabox():
    w = 256; n = noise(w, w, 16, 3, 91)
    a = col(None, (190, 150, 100), (215, 180, 130), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for y in range(0, w, 32): d.line([(0, y), (w, y)], fill=(150, 110, 70), width=2)
    lg = logo(96); im.paste(lg, (80, 80), lg)
    save('cc_pizzabox', im)


def foil_and_lander():
    w = 256; n = noise(w, w, 16, 4, 101)
    a = col(None, (180, 130, 30), (255, 215, 90), n)
    a += (noise(w, w, 32, 2, 102)[..., None] - .5) * 90
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64): d.line([(k, 0), (k + 20, w)], fill=(150, 100, 20), width=2)
    save('cc_foil', im)
    im = Image.new('RGB', (w, w), (225, 228, 235)); d = ImageDraw.Draw(im)
    panel_lines(d, w, w, 128, (150, 155, 170), 3)
    for x in (12, 116, 140, 244):
        for y in (12, 116, 140, 244): d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(130, 135, 150))
    d.rectangle([0, 60, w, 68], fill=(230, 60, 60))
    save('cc_lander', grime(np.asarray(im, float), 8, 103))


def truss():
    w = 256; im = Image.new('RGB', (w, w), (60, 62, 70)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 20], fill=(150, 155, 165)); d.rectangle([0, w - 20, w, w], fill=(150, 155, 165))
    for k in range(-w, w, 64):
        d.line([(k, 20), (k + 64, w - 20)], fill=(150, 155, 165), width=10)
        d.line([(k + 64, 20), (k, w - 20)], fill=(150, 155, 165), width=10)
    save('cc_truss', im)


def cabinet():
    w = 256
    # side art: original zig-zag rocket flames + planets on deep blue
    im = Image.new('RGB', (w, w), (20, 20, 70)); d = ImageDraw.Draw(im)
    for k in range(6):
        y = 30 + k * 40
        c = [(255, 60, 200), (60, 230, 255), (255, 230, 60)][k % 3]
        d.line([(x, y + (12 if (x // 32) % 2 else -12)) for x in range(-32, w + 64, 32)], fill=c, width=6)
    d.ellipse([150, 40, 230, 120], fill=(255, 140, 50)); d.ellipse([120, 70, 260, 95], outline=(60, 230, 255), width=4)
    d.rectangle([0, 0, w, 10], fill=(10, 10, 20)); d.rectangle([0, w - 10, w, w], fill=(10, 10, 20))
    save('cc_cab_side', im)
    # lower front with coin door
    im = Image.new('RGB', (w, w), (30, 30, 90)); d = ImageDraw.Draw(im)
    d.rectangle([80, 90, 176, 200], fill=(25, 25, 30), outline=(200, 200, 210), width=4)
    for x in (100, 140):
        d.rectangle([x, 120, x + 16, 160], fill=(230, 40, 40)); d.rectangle([x + 6, 128, x + 10, 152], fill=(255, 230, 120))
    d.text((92, 210), 'INSERT COIN', fill=(255, 230, 60), font=font(14))
    save('cc_cab_front', im)
    # top
    save('cc_cab_top', grime(np.zeros((w, w, 3)) + 35, 10, 111))
    # control panel
    im = Image.new('RGB', (w, w), (15, 15, 25)); d = ImageDraw.Draw(im)
    d.ellipse([40, 90, 90, 140], fill=(200, 30, 30)); d.line([(65, 115), (65, 60)], fill=(220, 220, 220), width=8)
    for i, c in enumerate(((255, 60, 200), (60, 230, 255), (255, 230, 60), (120, 255, 120))):
        d.ellipse([130 + i * 28, 100, 150 + i * 28, 120], fill=c)
    save('cc_panel', im)


def screen():
    w = 256
    def base():
        im = Image.new('RGB', (w, w), (5, 10, 25)); d = ImageDraw.Draw(im)
        for k in range(60): x, y = random.randrange(w), random.randrange(w); d.point((x, y), fill=(200, 200, 255))
        return im, d
    # 1: saucer shooter
    im, d = base()
    for (x, y, c) in ((50, 60, (255, 60, 200)), (130, 46, (120, 255, 120)), (200, 80, (255, 230, 60)), (90, 110, (255, 140, 50)), (176, 130, (60, 230, 255))):
        d.ellipse([x - 22, y - 6, x + 22, y + 8], fill=c); d.ellipse([x - 10, y - 16, x + 10, y + 2], fill=(200, 240, 255))
        for k in (-14, 0, 14): d.ellipse([x + k - 3, y, x + k + 3, y + 5], fill=(255, 255, 255))
    d.polygon([(128, 170), (110, 204), (128, 194), (146, 204)], fill=(60, 230, 255))
    d.line([(128, 166), (128, 140)], fill=(255, 255, 255), width=3)
    d.text((10, 6), 'SCORE 04720', fill=(255, 255, 255), font=font(16))
    save('cc_screen', im)
    # 2: comet crush (rocks + rocket)
    im, d = base()
    for (x, y, r) in ((60, 70, 26), (180, 50, 18), (200, 140, 30), (90, 150, 14), (140, 100, 10)):
        pts = [(x + r * (0.75 + 0.25 * math.sin(k * 2.1)) * math.cos(k * math.pi / 4), y + r * (0.75 + 0.25 * math.cos(k * 1.7)) * math.sin(k * math.pi / 4)) for k in range(8)]
        d.polygon(pts, outline=(255, 255, 255), width=3)
    d.polygon([(120, 190), (150, 178), (124, 170)], outline=(255, 230, 60), width=3)
    d.text((10, 6), 'COMET CRUSH  1UP', fill=(255, 230, 60), font=font(16))
    save('cc_screen2', im)
    # 3: orbit racer (neon track)
    im, d = base()
    d.ellipse([20, 40, 236, 210], outline=(255, 60, 200), width=10); d.ellipse([60, 80, 196, 170], outline=(60, 230, 255), width=6)
    d.rectangle([122, 196, 140, 212], fill=(255, 230, 60)); d.rectangle([100, 34, 116, 48], fill=(120, 255, 120))
    d.text((10, 6), 'LAP 2/3   00:41', fill=(255, 255, 255), font=font(16))
    save('cc_screen3', im)
    a = np.zeros((64, 64, 3)) + 40; a[::4] = 120
    save('cc_scanlines', a)
    for name, title, c in (('cc_marquee', 'GALAXY ZAP', (255, 60, 200)), ('cc_marquee2', 'COMET CRUSH', (255, 230, 60)), ('cc_marquee3', 'ORBIT RACER', (60, 230, 255))):
        im = Image.new('RGB', (w, 64), (10, 5, 30)); d = ImageDraw.Draw(im)
        d.text((128, 32), title, fill=c, font=font(32), anchor='mm')
        save(name, im)


def claw_base():
    w = 256; im = Image.new('RGB', (w, w), (230, 40, 120)); d = ImageDraw.Draw(im)
    for k in range(0, w, 32): d.rectangle([0, k, w, k + 12], fill=(250, 210, 60))
    d.rectangle([90, 150, 166, 230], fill=(20, 20, 30), outline=(240, 240, 240), width=4)
    d.text((98, 120), 'PRIZE', fill=(255, 255, 255), font=font(22))
    save('cc_claw_base', im)


def foam():
    w = 256; im = Image.new('RGB', (w, w)); d = ImageDraw.Draw(im)
    cols = [(255, 80, 80), (80, 160, 255), (255, 220, 70), (90, 220, 120)]
    for i in range(4): d.rectangle([0, i * 64, w, i * 64 + 63], fill=cols[i])
    save('cc_foam', grime(np.asarray(im, float), 14, 121))


def ballpit():
    w = 256; im = Image.new('RGBA', (w, w), (40, 10, 60, 255)); d = ImageDraw.Draw(im)
    cols = [(255, 60, 60), (60, 140, 255), (255, 230, 60), (80, 220, 100), (255, 120, 220)]
    for k in range(260):
        x, y = random.randrange(w), random.randrange(w); r = 11; c = random.choice(cols)
        for dx in (-w, 0, w):
            for dy in (-w, 0, w):
                d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=c + (255,))
                d.ellipse([x + dx - r // 2, y + dy - r // 2 - 3, x + dx, y + dy - 3], fill=(255, 255, 255, 255))
    save('cc_ballpit', im)


def shelf():
    steel('cc_shelf', (0.95, 1.0, 1.1), 170)
    w = 256; im = Image.new('RGB', (w, w), (40, 140, 200)); d = ImageDraw.Draw(im)
    for k in range(0, w, 40): d.ellipse([110, k + 10, 146, k + 30], fill=(250, 220, 70))
    save('cc_shelf_side', im)


def duct():
    w = 256; base = 140 + rng.normal(0, 4, (w, w))
    a = np.stack([base, base, base * 1.05], -1)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64):
        d.line([(k, 0), (k, w)], fill=(100, 100, 108), width=4)
        for y in range(8, w, 32): d.ellipse([k + 4, y - 2, k + 8, y + 2], fill=(90, 90, 95))
    save('cc_duct', im)
    # grate (alpha)
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(0, 64, 16):
        d.rectangle([k, 0, k + 4, 64], fill=(120, 120, 130, 255)); d.rectangle([0, k, 64, k + 4], fill=(120, 120, 130, 255))
    save('cc_grate', im, alpha=True)


def glass():
    w = 128; im = Image.new('RGBA', (w, w), (150, 200, 255, 60)); d = ImageDraw.Draw(im)
    d.line([(10, 100), (60, 20)], fill=(255, 255, 255, 110), width=6); d.line([(40, 120), (90, 40)], fill=(255, 255, 255, 80), width=3)
    save('cc_glass', im, alpha=True)


def water():
    w = 128; n = noise(w, w, 8, 3, 131)
    a = col(None, (60, 120, 150), (140, 200, 220), n)
    save('cc_water', a)


def van():
    w = 256
    im = Image.new('RGB', (w, w), (70, 200, 190)); d = ImageDraw.Draw(im)
    d.rectangle([0, 150, w, 180], fill=(250, 210, 60)); d.rectangle([0, 186, w, 196], fill=(230, 60, 120))
    save('cc_van', grime(np.asarray(im, float), 8, 141))
    # side logo panel 512x256: CRATER CRUST + logo + "pizza  arcade  orbit"
    im = Image.new('RGB', (512, 256), (70, 200, 190)); d = ImageDraw.Draw(im)
    d.rectangle([0, 200, 512, 230], fill=(250, 210, 60)); d.rectangle([0, 236, 512, 246], fill=(230, 60, 120))
    lg = logo(150); im.paste(lg, (18, 30), lg)
    d.text((180, 46), 'CRATER', fill=(40, 20, 80), font=font(56)); d.text((180, 106), 'CRUST', fill=(230, 60, 120), font=font(56))
    d.text((184, 170), 'PIZZA  -  GAMES  -  DELIVERY', fill=(40, 20, 80), font=font(16))
    save('cc_van_logo', grime(np.asarray(im, float), 6, 142))
    im = Image.new('RGB', (w, w), (40, 40, 45)); d = ImageDraw.Draw(im)
    for y in range(40, 200, 20): d.rectangle([20, y, 236, y + 10], fill=(150, 150, 160))
    d.ellipse([10, 210, 60, 250], fill=(255, 250, 200)); d.ellipse([196, 210, 246, 250], fill=(255, 250, 200))
    save('cc_van_grille', im)
    im = Image.new('RGB', (w, w), (70, 200, 190)); d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 236, 120], fill=(40, 60, 90)); d.line([(40, 30), (90, 110)], fill=(140, 170, 200), width=6)
    save('cc_van_windshield', im)
    im = Image.new('RGB', (w, w), (70, 200, 190)); d = ImageDraw.Draw(im)
    d.rectangle([30, 20, 226, 110], fill=(40, 60, 90)); d.rectangle([0, 150, w, 180], fill=(250, 210, 60))
    save('cc_van_cabside', im)
    save('cc_van_floor', grime(np.zeros((w, w, 3)) + np.array([90, 90, 95]), 10, 143))
    save('cc_rubber', grime(np.zeros((w, w, 3)) + 28, 8, 144))


def dumpster():
    w = 256; n = noise(w, w, 8, 4, 151)
    a = col(None, (30, 80, 40), (60, 120, 60), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64): d.rectangle([k, 0, k + 6, w], fill=(25, 60, 30))
    save('cc_dumpster', grime(np.asarray(im, float), 20, 152))


def ac():
    w = 256; im = Image.new('RGB', (w, w), (175, 178, 180)); d = ImageDraw.Draw(im)
    for y in range(30, 230, 14): d.line([(20, y), (236, y)], fill=(110, 112, 115), width=6)
    save('cc_ac', im)
    im = Image.new('RGB', (w, w), (165, 168, 170)); d = ImageDraw.Draw(im)
    d.ellipse([48, 48, 208, 208], fill=(60, 62, 65)); d.ellipse([118, 118, 138, 138], fill=(170, 170, 170))
    for a in range(0, 360, 45):
        d.line([(128, 128), (128 + 70 * math.cos(math.radians(a)), 128 + 70 * math.sin(math.radians(a)))], fill=(130, 130, 135), width=10)
    save('cc_ac_top', im)


def ceiling():
    w = 256; im = Image.new('RGB', (w, w), (30, 28, 48)); d = ImageDraw.Draw(im)
    panel_lines(d, w, w, 128, (15, 14, 25), 4)
    for k in range(12):
        x, y = random.randrange(8, w - 8), random.randrange(8, w - 8); d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 250, 220))
    save('cc_ceiling', im)


def glows():
    w = 64
    for name, c in (('cc_neon_cyan', (60, 230, 255)), ('cc_neon_magenta', (255, 60, 200)), ('cc_neon_yellow', (255, 230, 60))):
        a = np.zeros((w, w, 3)) + np.array(c) * .9
        save(name, a)
    # jump pad: concentric rings + chevron rocket
    w = 256; im = Image.new('RGB', (w, w), (20, 10, 40)); d = ImageDraw.Draw(im)
    for r, c in ((120, (60, 230, 255)), (96, (20, 10, 40)), (88, (255, 60, 200)), (64, (20, 10, 40)), (56, (255, 230, 60))):
        d.ellipse([128 - r, 128 - r, 128 + r, 128 + r], fill=c)
    d.polygon([(128, 80), (100, 150), (128, 135), (156, 150)], fill=(255, 255, 255))
    save('cc_jumppad', im)
    a = np.zeros((64, 64, 3)) + np.array([60, 230, 255]); a[16:48] = (20, 10, 40)
    save('cc_pad_side', a)
    # coals
    w = 128; n = noise(w, w, 8, 4, 161)
    save('cc_coals', col(None, (60, 10, 0), (255, 140, 30), n ** 1.5))
    save('cc_lamp_light', np.zeros((64, 64, 3)) + np.array([255, 235, 190]))
    # lot line decal (alpha)
    im = Image.new('RGBA', (64, 64), (255, 255, 240, 230)); save('cc_lotline', im, alpha=True)


def sign():
    W_, H_ = 1024, 256
    im = Image.new('RGB', (W_, H_), (25, 10, 50)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, W_ - 7, H_ - 7], radius=30, outline=(60, 230, 255), width=10)
    lg = logo(220); im.paste(lg, (24, 18), lg)
    f = font(96)
    glow = Image.new('RGB', (W_, H_), (0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.text((620, 104), 'CRATER CRUST', fill=(255, 60, 200), font=f, anchor='mm')
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    im = Image.fromarray(np.clip(np.asarray(im, float) + np.asarray(glow, float) * 1.4, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((620, 104), 'CRATER CRUST', fill=(255, 210, 245), font=f, anchor='mm')
    d.text((620, 205), 'PIZZA  *  ARCADE  *  OUT OF THIS WORLD', fill=(255, 230, 60), font=font(30), anchor='mm')
    im.save(os.path.join(TD, 'cc_sign.jpg'), quality=94)
    save('cc_sign_back', grime(np.zeros((128, 128, 3)) + np.array([40, 40, 50]), 6, 171))


# ------------------------------------------------------------------ sky
def sky():
    S = 512
    def stars(a, density, seed):
        r = np.random.default_rng(seed)
        n = int(S * S * density)
        ys, xs = r.integers(0, S, n), r.integers(0, S, n)
        b = r.uniform(120, 255, n)
        for y, x, bb in zip(ys, xs, b):
            a[y, x] = np.maximum(a[y, x], (bb, bb, min(255, bb + 20)))
        return a
    def side(seed, moon=False):
        y = np.linspace(0, 1, S)[:, None, None]
        top = np.array([8, 6, 30]); hor = np.array([60, 30, 90])
        a = top * (1 - y) + hor * y
        a = np.repeat(a, S, 1).astype(float)
        a = stars(a, 0.0016, seed)
        # aurora band
        n = noise(S, S, 3, 3, seed + 5)
        band = np.exp(-((np.linspace(0, 1, S)[:, None] - 0.62 - (n - .5) * .2) ** 2) / 0.004)
        a += band[..., None] * np.array([20, 90, 70]) * n[..., None]
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
        # city/hill silhouette at the horizon (bottom 18%)
        r = np.random.default_rng(seed + 9)
        x = 0
        while x < S:
            bw = int(r.integers(18, 60)); bh = int(r.integers(10, 70))
            d.rectangle([x, S - bh - 30, x + bw, S], fill=(14, 8, 26))
            for wy in range(S - bh - 24, S - 34, 10):
                for wx in range(x + 4, x + bw - 4, 9):
                    if r.random() < .25: d.rectangle([wx, wy, wx + 3, wy + 4], fill=(255, 210, 120))
            x += bw + int(r.integers(0, 10))
        if moon:
            for i in range(60, 0, -1):
                t = i / 60; c = (int(255 - 40 * t), int(245 - 50 * t), int(220 - 60 * t))
                d.ellipse([340 - i, 120 - i, 340 + i, 120 + i], fill=c)
            for (cx, cy, rr) in ((320, 105, 9), (355, 140, 12), (348, 95, 5), (327, 140, 6)):
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(200, 190, 175))
            glow = Image.new('RGB', (S, S)); gd = ImageDraw.Draw(glow); gd.ellipse([250, 30, 430, 210], fill=(60, 50, 80))
            glow = glow.filter(ImageFilter.GaussianBlur(40))
            im = Image.fromarray(np.clip(np.asarray(im, float) + np.asarray(glow, float), 0, 255).astype(np.uint8))
        return im
    side(1).save(os.path.join(ED, 'cc_sky_rt.jpg'), quality=92)
    side(2, moon=True).save(os.path.join(ED, 'cc_sky_ft.jpg'), quality=92)
    side(3).save(os.path.join(ED, 'cc_sky_lf.jpg'), quality=92)
    side(4).save(os.path.join(ED, 'cc_sky_bk.jpg'), quality=92)
    up = stars(np.zeros((S, S, 3)) + np.array([8, 6, 30]), 0.002, 9)
    Image.fromarray(up.astype(np.uint8)).save(os.path.join(ED, 'cc_sky_up.jpg'), quality=92)
    Image.fromarray((np.zeros((S, S, 3)) + np.array([14, 8, 26])).astype(np.uint8)).save(os.path.join(ED, 'cc_sky_dn.jpg'), quality=92)


for fn in (floor_tile, carpet, kitchen_tile, asphalt, concrete, roof, grass, wall_mural, store_wall, facade, brick,
           steel, counter_top, counter_front, wood, vinyl, pizzabox, foil_and_lander, truss, cabinet, screen, claw_base,
           foam, ballpit, shelf, duct, glass, water, van, dumpster, ac, ceiling, glows, sign, sky):
    fn()
concrete('cc_curb', (190, 185, 60), 0)
# rooftop extras
w = 256
im = Image.new('RGB', (w, w), (20, 30, 70)); d = ImageDraw.Draw(im)
panel_lines(d, w, w, 64, (150, 160, 190), 3); d.line([(0, 0), (w, w)], fill=(60, 80, 140), width=2)
save('cc_solar', im)
im = Image.new('RGB', (w, w), (30, 50, 90)); d = ImageDraw.Draw(im)
panel_lines(d, w, w, 128, (200, 205, 215), 8); d.line([(20, 200), (120, 40)], fill=(120, 160, 220), width=6)
save('cc_skylight', im)
n = noise(w, w, 8, 4, 181)
im = Image.fromarray(np.clip(col(None, (140, 150, 160), (175, 185, 195), n), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
for y in range(0, w, 64): d.line([(0, y), (w, y)], fill=(110, 115, 125), width=4)
lg = logo(110); im.paste(lg, (73, 73), lg)
save('cc_tank', im)
logo(256).save(os.path.join(TD, 'cc_logo.tga'))
print(sorted(os.listdir(TD)))
