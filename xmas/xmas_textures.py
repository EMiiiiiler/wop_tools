"""Procedural textures + shader + arena for wop_padxmas (Padman's Christmas).
All art is original and generated here. make_all(out) writes textures/padxmas/*, scripts/padxmas.shader and
scripts/wop_padxmas.arena (pk3dir layout). Helpers are shared with playroom/textures.py."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('playroom_textures', os.path.join(os.path.dirname(HERE), 'playroom', 'textures.py'))
_pt = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_pt)
noise, C, N3, img, fill, font, text_c, planks = _pt.noise, _pt.C, _pt.N3, _pt.img, _pt.fill, _pt.font, _pt.text_c, _pt.planks

MAP = 'wop_padxmas'
NS = 'padxmas'
R = random.Random(1225)


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


def star_pts(cx, cy, r1, r2, n=5, rot=0):
    return [(cx + (r1 if k % 2 == 0 else r2) * math.cos(math.radians(rot) - math.pi / 2 + k * math.pi / n),
             cy + (r1 if k % 2 == 0 else r2) * math.sin(math.radians(rot) - math.pi / 2 + k * math.pi / n)) for k in range(2 * n)]


def snowflake(d, cx, cy, r, col, w=2):
    for k in range(6):
        a = k * math.pi / 3
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        d.line((cx, cy, ex, ey), fill=col, width=w)
        for f in (0.55,):
            mx, my = cx + r * f * math.cos(a), cy + r * f * math.sin(a)
            for s in (-1, 1):
                b = a + s * 0.7
                d.line((mx, my, mx + r * 0.3 * math.cos(b), my + r * 0.3 * math.sin(b)), fill=col, width=w)


def tile_draw(im, fn):
    """call fn(d, ox, oy) for the 9 wrap offsets so motifs tile seamlessly"""
    d = ImageDraw.Draw(im); n = im.size[0]
    for ox in (-n, 0, n):
        for oy in (-n, 0, n):
            fn(d, ox, oy)
    return im


def soft(im, r=0.6):
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32)


# ----------------------------------------------------------------------------------------------- textures
GIFTS = {  # name: (paper colour, ribbon colour, motif)
    'red': ((196, 30, 40), (248, 206, 80), 'plain'),
    'green': ((32, 120, 64), (220, 40, 40), 'holly'),
    'blue': ((40, 70, 170), (220, 228, 240), 'flakes'),
    'gold': ((222, 172, 60), (180, 20, 30), 'stars'),
    'stripe': ((236, 236, 230), (40, 140, 70), 'stripes'),
    'dots': ((120, 50, 150), (250, 214, 90), 'dots'),
    'trees': ((246, 242, 232), (200, 30, 40), 'trees'),
    'kraft': ((176, 128, 82), (236, 230, 214), 'twine'),
}


def gift_paper(n, col, motif, seed):
    a = fill(n, col, 3, seed)
    im = img(a)
    if motif == 'holly':
        def f(d, ox, oy):
            for (x, y) in ((50, 60), (180, 150), (110, 220), (220, 30)):
                x += ox; y += oy
                for s in (-1, 1):
                    d.ellipse((x + s * 14 - 12, y - 6, x + s * 14 + 12, y + 6), fill=(20, 80, 40))
                for (bx, by) in ((0, -4), (-5, 3), (5, 3)):
                    d.ellipse((x + bx - 5, y + by - 5, x + bx + 5, y + by + 5), fill=(210, 30, 40))
        tile_draw(im, f)
    elif motif == 'flakes':
        def f(d, ox, oy):
            for (x, y, r) in ((60, 60, 26), (190, 120, 18), (100, 200, 20), (220, 230, 12), (20, 150, 10)):
                snowflake(d, x + ox, y + oy, r, (230, 236, 250), 3)
        tile_draw(im, f)
    elif motif == 'stars':
        def f(d, ox, oy):
            for (x, y, r) in ((50, 50, 18), (180, 90, 12), (110, 190, 16), (230, 220, 10), (20, 200, 8)):
                d.polygon(star_pts(x + ox, y + oy, r, r * 0.42), fill=(250, 236, 160))
        tile_draw(im, f)
    elif motif == 'stripes':
        d = ImageDraw.Draw(im)
        for k in range(-8, 9):
            o = k * 64
            d.polygon([(o, 0), (o + 32, 0), (o + 32 + n, n), (o + n, n)], fill=(206, 30, 40))
    elif motif == 'dots':
        def f(d, ox, oy):
            for i in range(4):
                for j in range(4):
                    x = 32 + i * 64 + (32 if j % 2 else 0) + ox; y = 32 + j * 64 + oy
                    d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(246, 240, 250))
        tile_draw(im, f)
    elif motif == 'trees':
        def f(d, ox, oy):
            for (x, y) in ((50, 70), (180, 40), (120, 170), (230, 200), (30, 230)):
                x += ox; y += oy
                d.polygon([(x, y - 26), (x - 18, y + 14), (x + 18, y + 14)], fill=(30, 120, 60))
                d.rectangle((x - 3, y + 14, x + 3, y + 22), fill=(110, 70, 40))
                d.polygon(star_pts(x, y - 28, 6, 2.5), fill=(230, 180, 40))
        tile_draw(im, f)
    return soft(im, 0.5) + N3(n, 1, seed + 3, 2)


def ribbon_band(a, x0, x1, col, vertical=True):
    """paint a satin ribbon band (with highlight stripes) into array a"""
    n = a.shape[0]
    w = x1 - x0
    prof = np.array([0.78 + 0.35 * math.sin(math.pi * (i + 0.5) / w) ** 6 + (0.12 if i in (2, w - 3) else 0) for i in range(w)], np.float32)
    band = C(col)[None, :] * prof[:, None]
    if vertical: a[:, x0:x1] = band[None, :, :]
    else: a[x0:x1, :] = band[:, None, :]


def make_textures(W):
    n = 256
    # ---- room
    W.save('floor_oak', planks(256, (128, 80, 46), 4, 3, gap=(48, 30, 18)))
    W.save('wood_dark', planks(256, (92, 54, 32), 2, 5, gap=(60, 36, 22)))
    W.save('wood_mid', planks(256, (150, 100, 60), 2, 7, gap=(110, 70, 40)))
    W.save('wood_light', planks(256, (214, 178, 128), 2, 9, gap=(170, 136, 96)))
    # wainscot: raised red-brown panels
    a = fill(n, (120, 44, 36), 3, 11)
    for (x0, x1) in ((16, 112), (144, 240)):
        a[24:232, x0:x1] = a[24:232, x0:x1] * 1.12
        a[24:28, x0:x1] *= 1.25; a[228:232, x0:x1] *= 0.7; a[24:232, x0:x0 + 4] *= 1.2; a[24:232, x1 - 4:x1] *= 0.7
    W.save('wainscot', a)
    W.save('trim_white', fill(n, (242, 238, 228), 2, 12))
    W.save('trim_gold', fill(n, (206, 164, 70), 5, 13) + N3(n, 0.6, 14, 6))
    # wallpaper: cream with tiny gold stars and holly sprigs (scale 2 -> 512u tile)
    im = img(fill(n, (238, 226, 196), 2, 15))
    def wp(d, ox, oy):
        for (x, y) in ((32, 32), (160, 96), (96, 192), (224, 224)):
            d.polygon(star_pts(x + ox, y + oy, 9, 4), fill=(200, 160, 70))
        for (x, y) in ((160, 224), (32, 128), (224, 64)):
            x += ox; y += oy
            d.ellipse((x - 14, y - 4, x - 2, y + 4), fill=(60, 110, 60)); d.ellipse((x + 2, y - 4, x + 14, y + 4), fill=(60, 110, 60))
            d.ellipse((x - 4, y - 8, x + 4, y), fill=(180, 40, 40))
    tile_draw(im, wp)
    a = soft(im, 0.5)
    for i in range(0, n, 64): a[:, i:i + 2] *= 0.96
    W.save('wallpaper', a)
    W.save('ceiling', fill(n, (236, 232, 222), 3, 16))
    # rug: deep red with a woven border pattern (fitted 1024x768 on the floor)
    rug = np.zeros((384, 512, 3), np.float32) + C((150, 28, 34)) + N3(512, 1, 17, 6, 384)
    im = img(rug); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, 501, 373), outline=(220, 180, 90), width=6)
    d.rectangle((30, 30, 481, 353), outline=(30, 80, 50), width=10)
    for k in range(0, 512, 32):
        d.polygon([(k, 52), (k + 16, 44), (k + 32, 52), (k + 16, 60)], fill=(220, 180, 90))
        d.polygon([(k, 332), (k + 16, 324), (k + 32, 332), (k + 16, 340)], fill=(220, 180, 90))
    for (cx, cy) in ((256, 192),):
        d.polygon(star_pts(cx, cy, 120, 50, 8), fill=(30, 80, 50)); d.polygon(star_pts(cx, cy, 80, 34, 8), fill=(220, 180, 90))
        d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(150, 28, 34))
    for (cx, cy) in ((100, 110), (412, 110), (100, 274), (412, 274)):
        snowflake(d, cx, cy, 34, (236, 220, 180), 5)
    W.save('rug', soft(im, 0.7) + N3(512, 0.5, 18, 5, 384))
    W.save('rug_edge', fill(n, (200, 160, 80), 6, 19))

    # ---- fireplace
    a = np.zeros((n, n, 3), np.float32)
    rr = random.Random(5)
    for row in range(8):
        y0 = row * 32; off = 32 if row % 2 else 0
        for k in range(-1, 4):
            x0 = k * 64 + off
            col = C((150, 62, 44)) * rr.uniform(0.75, 1.15)
            a[y0 + 3:y0 + 32, max(0, x0 + 3):max(0, min(n, x0 + 64))] = col
    a[a.sum(2) == 0] = C((190, 180, 164))
    W.save('brick', a + N3(n, 0.8, 21, 8) + N3(n, 8, 22, 6))
    W.save('brick_soot', (a + N3(n, 0.8, 23, 8)) * 0.32 + N3(n, 6, 24, 6))
    W.save('stone', fill(n, (170, 164, 156), 8, 25) + N3(n, 0.5, 26, 10))
    W.save('soot', fill(n, (34, 28, 26), 6, 27))
    W.save('log_bark', planks(256, (86, 58, 36), 6, 29, gap=(40, 26, 16)))
    a = fill(n, (214, 176, 120), 4, 31)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    rings = np.sin(np.sqrt((xx - 128) ** 2 + (yy - 128) ** 2) * 0.35) * 14
    W.save('log_end', a + rings[..., None])
    W.save('metal_black', fill(n, (34, 34, 38), 4, 33))
    W.save('brass', fill(n, (200, 160, 70), 6, 35) + N3(n, 0.6, 36, 8))
    # fire: 4 animation frames of flames on black (additive), embers
    for fi in range(4):                 # flame tongues, phase-shifted per frame
        im = Image.new('L', (n, n), 0); d = ImageDraw.Draw(im); rr = random.Random(40 + fi)
        for k in range(7):
            cx = 30 + k * 32 + rr.uniform(-8, 8)
            h = rr.uniform(110, 230) * (1 - abs(cx - 128) / 220)
            w = rr.uniform(22, 34)
            sway = 14 * math.sin(fi * 1.6 + k)
            d.polygon([(cx - w, n), (cx - w * 0.6 + sway * 0.3, n - h * 0.45), (cx + sway, n - h), (cx + w * 0.6 + sway * 0.3, n - h * 0.45),
                       (cx + w, n)], fill=int(rr.uniform(170, 255)))
        d.rectangle((0, n - 40, n, n), fill=255)
        fa = np.asarray(im.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
        fa = np.clip(fa * (1 + noise(n, 3, 50 + fi) * 0.25), 0, 1)
        rgb = np.stack([np.clip(fa * 2.0, 0, 1) * 255, np.clip(fa * 1.6 - 0.35, 0, 1) * 225, np.clip(fa * 1.8 - 1.2, 0, 1) * 170], -1)
        W.save('fire%d' % fi, rgb)
    a = np.zeros((n, n, 3), np.float32)
    nz = noise(n, 2, 61)
    a[..., 0] = np.clip(nz * 90 + 140, 0, 255); a[..., 1] = np.clip(nz * 60 + 40, 0, 255); a[..., 2] = 10
    W.save('embers', a)
    a = np.zeros((n, n, 3), np.float32) + 255
    al = np.clip((noise(n, 10, 63) * 0.5 + 0.4) * (1 - np.abs(xx - 128) / 128) * 255 * 0.5, 0, 255)
    W.save('smoke', a * 0.8, alpha=al)

    # ---- tree
    def needles(base, seed, dens=900, light=1.0):
        a = fill(n, base, 4, seed) * light
        im = img(a); d = ImageDraw.Draw(im); r2 = random.Random(seed)
        for _ in range(dens):
            x, y = r2.uniform(-8, n + 8), r2.uniform(-8, n + 8)
            ang = r2.uniform(-0.6, 0.6) + math.pi / 2
            L = r2.uniform(8, 18)
            c = tuple(int(v * r2.uniform(0.6, 1.35) * light) for v in base)
            for ox in (-n, 0, n):
                for oy in (-n, 0, n):
                    d.line((x + ox, y + oy, x + ox + L * math.cos(ang) * 0.5, y + oy + L * math.sin(ang)), fill=c, width=2)
        return soft(im, 0.4)
    W.save('needles', needles((40, 104, 58), 71))
    W.save('needles_top', needles((46, 112, 62), 73, 700))
    W.save('needles_under', needles((24, 62, 36), 75, 900, 0.8))
    W.save('bark', planks(256, (98, 66, 42), 5, 77, gap=(60, 40, 24), vertical=True))
    W.save('stand_red', fill(n, (176, 26, 32), 3, 79) + N3(n, 0.5, 80, 4))
    a = fill(n, (178, 22, 30), 3, 81)
    im = img(a)
    tile_draw(im, lambda d, ox, oy: [snowflake(d, x + ox, y + oy, r, (246, 246, 246), 4) for (x, y, r) in ((64, 64, 34), (192, 192, 34), (192, 60, 16), (60, 190, 16))])
    W.save('treeskirt', soft(im, 0.6) + N3(n, 1, 82, 4))
    for nm, col in (('bauble_red', (210, 24, 34)), ('bauble_gold', (226, 176, 50)), ('bauble_blue', (40, 90, 210)),
                    ('bauble_silver', (200, 206, 216)), ('bauble_green', (30, 150, 70)), ('bauble_purple', (140, 50, 170))):
        a = fill(n, col, 3, hash(nm) % 999)
        a[118:138, :] = a[118:138, :] * 1.25 + 20          # glitter band
        W.save(nm, a + N3(n, 0.4, 83, 6))
    W.save('tinsel', np.clip(fill(n, (236, 196, 80), 10, 85) + N3(n, 0.3, 86, 40), 0, 255))
    W.save('tinsel_silver', np.clip(fill(n, (210, 214, 224), 10, 87) + N3(n, 0.3, 88, 40), 0, 255))
    for nm, col in (('bulb_red', (255, 60, 50)), ('bulb_green', (70, 255, 90)), ('bulb_yellow', (255, 220, 80)),
                    ('bulb_blue', (90, 140, 255))):
        a = np.zeros((64, 64, 3), np.float32) + C(col)
        W.save(nm, a)
    W.save('star_gold', np.clip(fill(n, (255, 214, 90), 6, 89) + N3(n, 0.5, 90, 18), 0, 255))
    W.save('wire', fill(64, (30, 60, 30), 2, 91))

    # ---- presents: paper with ribbon (side: vertical band, top: cross)
    for k, (nm, (col, rib, motif)) in enumerate(GIFTS.items()):
        paper = gift_paper(n, col, motif, 100 + k * 7)
        side = paper.copy(); ribbon_band(side, 110, 146, rib, True)
        top = paper.copy(); ribbon_band(top, 110, 146, rib, True); ribbon_band(top, 110, 146, rib, False)
        if motif == 'twine':   # kraft paper with thin twine instead of satin
            side = paper.copy(); top = paper.copy()
            for b in (124, 132):
                side[:, b:b + 3] = C(rib); top[:, b:b + 3] = C(rib); top[b:b + 3, :] = C(rib)
        W.save('gift_%s_side' % nm, side); W.save('gift_%s_top' % nm, top)
        W.save('paper_%s' % nm, paper)
        sat = np.zeros((128, 128, 3), np.float32) + C(rib)
        prof = 0.82 + 0.3 * np.sin(np.linspace(0, math.pi, 128)) ** 8 + 0.08 * np.sin(np.linspace(0, 9 * math.pi, 128))
        sat = sat * prof[None, :, None] + N3(128, 0.6, 210 + k, 3)
        W.save('ribbon_%s' % nm, np.clip(sat, 0, 255))
    W.save('tissue', fill(n, (248, 236, 240), 6, 131) + N3(n, 0.4, 132, 6))
    W.save('box_inside', fill(n, (220, 200, 170), 4, 133))

    # ---- living room furniture
    def velvet(col, seed):
        return fill(n, col, 4, seed) + N3(n, 6, seed + 1, 10) + N3(n, 0.5, seed + 2, 4)
    W.save('velvet_green', velvet((36, 92, 56), 141))
    W.save('velvet_red', velvet((150, 26, 36), 143))
    a = fill(n, (160, 30, 36), 3, 145)              # tartan cushion
    for (o, w, col) in ((0, 48, (30, 70, 40)), (96, 16, (220, 190, 80)), (150, 48, (30, 70, 40)), (220, 8, (20, 20, 30))):
        a[:, o:o + w] = a[:, o:o + w] * 0.4 + C(col) * 0.6; a[o:o + w, :] = a[o:o + w, :] * 0.4 + C(col) * 0.6
    W.save('tartan', a + N3(n, 0.5, 146, 4))
    a = fill(n, (236, 228, 214), 3, 147)            # knitted blanket: cable stripes
    for i in range(0, n, 32):
        a[:, i:i + 4] *= 0.85
        for j in range(0, n, 16):
            a[j:j + 8, i + 8:i + 24] *= 0.92
    for (o, col) in ((40, (170, 30, 40)), (200, (40, 100, 60))):
        a[o:o + 20, :] = C(col) + N3(n, 0.5, o, 6)[o:o + 20]
    W.save('knit', a)
    W.save('marble', fill(n, (232, 228, 222), 4, 149) + np.abs(N3(n, 3, 150, 14)) * -1)
    W.save('felt_green', fill(n, (40, 110, 60), 5, 151))
    W.save('candle_red', fill(64, (196, 24, 34), 3, 153))
    W.save('candle_white', fill(64, (246, 240, 226), 3, 154))
    W.save('wax_top', fill(64, (250, 244, 232), 2, 155))
    a = fill(128, (246, 246, 242), 2, 156); yy2, xx2 = np.mgrid[0:128, 0:128]
    a[(np.abs(np.hypot(xx2 - 64, yy2 - 64) - 50) < 3)] = C((40, 110, 70)); a[(np.abs(np.hypot(xx2 - 64, yy2 - 64) - 56) < 2)] = C((200, 30, 40))
    W.save('porcelain', a)
    W.save('glass', fill(64, (140, 160, 180), 2, 157))
    # candle flame sprite (alpha blended)
    fa = np.zeros((64, 64), np.float32); yy6, xx6 = np.mgrid[0:64, 0:64].astype(np.float32)
    dd = ((xx6 - 32) / 10) ** 2 + ((yy6 - 40) / 22) ** 2
    fl = np.clip(1.2 - dd, 0, 1)
    rgb = np.stack([np.clip(fl * 2, 0, 1) * 255, np.clip(fl * 1.6 - 0.2, 0, 1) * 230, np.clip(fl * 1.6 - 0.9, 0, 1) * 200], -1)
    W.save('flame', rgb)
    # snow + garden
    W.save('snow', np.clip(fill(n, (236, 242, 252), 4, 161) + N3(n, 0.4, 162, 6), 0, 255))
    W.save('snow_drift', np.clip(fill(n, (224, 232, 246), 8, 163) + N3(n, 5, 164, 10), 0, 255))
    rows = [np.concatenate([fill(64, (226, 232, 244), 6, 165 + i)] * 4, 1) - np.linspace(0, 40, 64)[:, None, None] for i in range(4)]
    W.save('roof_tiles_snow', np.clip(np.concatenate(rows, 0), 0, 255))
    W.save('house_wall', fill(n, (196, 178, 150), 6, 167) + N3(n, 0.5, 168, 8))
    W.save('fence', planks(256, (110, 80, 54), 4, 169, vertical=True))
    # falling snow sheet (additive): soft dots
    a = np.zeros((n, n), np.float32)
    im = Image.new('L', (n, n), 0); d = ImageDraw.Draw(im); r2 = random.Random(171)
    for _ in range(40):
        x, y, r = r2.uniform(0, n), r2.uniform(0, n), r2.uniform(1.2, 3.2)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=int(r2.uniform(150, 255)))
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), np.float32)
    W.save('snowfall', np.stack([a, a, a], -1))

    # ---- gingerbread house
    W.save('gingerbread', fill(n, (166, 96, 46), 6, 181) + N3(n, 0.5, 182, 10) + N3(n, 5, 183, 8))
    a = fill(n, (166, 96, 46), 6, 184) + N3(n, 0.5, 185, 10)   # roof: icing scallop shingles
    im = img(a); d = ImageDraw.Draw(im)
    for row in range(5):
        y = row * 52 + 26
        for k in range(-1, 6):
            x = k * 52 + (26 if row % 2 else 0)
            d.arc((x - 26, y - 26, x + 26, y + 26), 0, 180, fill=(250, 248, 244), width=7)
    W.save('ginger_roof', soft(im, 0.5))
    W.save('icing', np.clip(fill(n, (250, 248, 246), 3, 186) + N3(n, 0.4, 187, 4), 0, 255))
    a = fill(n, (166, 96, 46), 6, 188)       # wall with icing frame
    a[:12] = C((250, 248, 244)); a[-12:] = C((250, 248, 244))
    for i in range(0, n, 32):
        a[12:28, i:i + 16] = a[12:28, i:i + 16] * 0.2 + C((250, 248, 244)) * 0.8
    W.save('ginger_wall', a + N3(n, 0.5, 189, 8))
    for nm, col in (('gumdrop_red', (220, 40, 50)), ('gumdrop_green', (50, 190, 80)), ('gumdrop_yellow', (250, 210, 60)),
                    ('gumdrop_purple', (150, 70, 200))):
        W.save(nm, fill(64, col, 3, hash(nm) % 99) + N3(64, 0.4, 7, 14))
    W.save('choco', fill(n, (76, 44, 26), 4, 191) + N3(n, 0.5, 192, 6))
    # candy cane stripes (diagonal red/white so axial projection reads as a spiral)
    im = Image.new('RGB', (n, n), (250, 248, 246)); d = ImageDraw.Draw(im)
    for k in range(-8, 9):
        o = k * 64
        d.polygon([(o, 0), (o + 26, 0), (o + 26 + n, n), (o + n, n)], fill=(206, 28, 36))
    W.save('candystripe', soft(im, 0.8))
    # gingerbread man cutout face (sign)
    im = Image.new('RGB', (128, 256), (166, 96, 46)); d = ImageDraw.Draw(im)
    d.ellipse((34, 14, 94, 74), fill=(180, 106, 52)); d.ellipse((48, 34, 56, 42), fill=(30, 20, 15)); d.ellipse((72, 34, 80, 42), fill=(30, 20, 15))
    d.arc((48, 40, 80, 64), 20, 160, fill=(250, 248, 244), width=4)
    for y in (110, 140, 170): d.ellipse((58, y, 70, y + 12), fill=(220, 40, 50))
    d.line((24, 96, 104, 96), fill=(250, 248, 244), width=4)
    d.arc((30, 210, 60, 240), 0, 180, fill=(250, 248, 244), width=4); d.arc((68, 210, 98, 240), 0, 180, fill=(250, 248, 244), width=4)
    W.save('gingerman', im)

    # ---- sideboard / clock / nutcracker / pyramid / snow globe
    W.save('nut_red', fill(64, (190, 30, 40), 3, 201)); W.save('nut_black', fill(64, (24, 24, 28), 3, 202))
    W.save('nut_skin', fill(64, (236, 196, 160), 3, 203)); W.save('nut_white', fill(64, (240, 240, 236), 3, 204))
    W.save('nut_blue', fill(64, (40, 60, 150), 3, 205)); W.save('nut_green', fill(64, (30, 110, 60), 3, 206))
    W.save('lampglow', fill(64, (255, 226, 170), 2, 207))
    im = Image.new('RGB', (256, 256), (240, 232, 210)); d = ImageDraw.Draw(im)      # clock face
    d.ellipse((8, 8, 248, 248), outline=(60, 40, 20), width=8)
    for h in range(12):
        a = math.radians(h * 30)
        text_c(d, (128 + 96 * math.sin(a), 128 - 96 * math.cos(a)), ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'][h], 22, (40, 30, 20))
    d.line((128, 128, 128 + 50 * math.sin(math.radians(-60)), 128 - 50 * math.cos(math.radians(-60))), fill=(30, 20, 10), width=7)
    d.line((128, 128, 128, 40), fill=(30, 20, 10), width=5)
    W.save('clockface', im)
    W.save('pyramid_wood', fill(n, (226, 196, 140), 4, 211))
    # ---- signs / posters
    poster_advent(W); painting(W); cards(W); letter(W); W.save('wallframe', fill(n, (150, 110, 40), 6, 221) + N3(n, 0.5, 222, 10))
    # sleigh, reindeer, sack
    W.save('sleigh_red', fill(n, (178, 24, 32), 3, 231) + N3(n, 0.5, 232, 4))
    W.save('reindeer', fill(n, (132, 86, 52), 6, 233) + N3(n, 0.5, 234, 8))
    W.save('reindeer_light', fill(n, (214, 182, 140), 6, 235))
    W.save('antler', fill(64, (200, 176, 136), 4, 236))
    W.save('nose_red', fill(64, (255, 40, 30), 2, 237))
    a = fill(n, (156, 120, 74), 6, 238)
    for i in range(0, n, 8): a[i:i + 2] *= 0.85; a[:, i:i + 2] *= 0.88
    W.save('burlap', a)
    # rocking horse + toy train
    W.save('horse_white', fill(n, (240, 236, 228), 3, 241) + np.abs(N3(n, 6, 242, 14)) * -1)
    W.save('horse_mane', fill(n, (60, 40, 30), 6, 243))
    W.save('paint_red', fill(n, (200, 30, 36), 2, 245)); W.save('paint_green', fill(n, (30, 120, 60), 2, 246))
    W.save('paint_blue', fill(n, (40, 70, 170), 2, 247)); W.save('paint_yellow', fill(n, (240, 200, 50), 2, 248))
    W.save('track', planks(256, (110, 80, 50), 8, 249))
    W.save('rail', fill(64, (170, 170, 176), 3, 250))
    W.save('poinsettia', fill(n, (200, 20, 34), 6, 251) + N3(n, 0.5, 252, 10))
    W.save('pot_terra', fill(n, (180, 96, 60), 4, 253))
    W.save('curtain', fill(n, (140, 20, 30), 3, 255) + np.sin(np.mgrid[0:n, 0:n][1] / 6.0)[..., None] * 14)
    W.save('window_frame', fill(n, (236, 232, 224), 2, 257))
    W.save('cushion_white', fill(n, (236, 234, 226), 4, 259))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 261))
    W.save('skylight', fill(64, (120, 140, 190), 2, 262))
    W.save('jumppad', jumppad_tex())
    W.save('rubber', fill(n, (40, 40, 44), 4, 263))


def jumppad_tex():
    im = Image.new('RGB', (256, 256), (40, 40, 44)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 252, 252), fill=(200, 30, 40)); d.ellipse((28, 28, 228, 228), fill=(246, 246, 240))
    d.ellipse((52, 52, 204, 204), fill=(30, 120, 60))
    d.polygon(star_pts(128, 128, 64, 26), fill=(250, 210, 70))
    return im


def poster_advent(W):
    im = Image.new('RGB', (384, 512), (150, 26, 36)); d = ImageDraw.Draw(im)
    d.rectangle((8, 8, 375, 503), outline=(230, 190, 90), width=6)
    # night village scene
    d.rectangle((20, 20, 363, 300), fill=(30, 40, 90))
    for (x, y) in ((50, 50), (300, 70), (180, 40), (100, 110), (330, 140), (240, 120)):
        d.polygon(star_pts(x, y, 7, 3), fill=(255, 236, 160))
    d.ellipse((260, 30, 310, 80), fill=(250, 246, 220))
    d.polygon([(20, 300), (120, 220), (220, 300)], fill=(236, 240, 250)); d.polygon([(160, 300), (280, 200), (363, 300)], fill=(220, 228, 244))
    for (x, w, h) in ((60, 60, 60), (150, 50, 80), (250, 70, 60)):
        d.rectangle((x, 300 - h, x + w, 300), fill=(120, 70, 40)); d.polygon([(x - 8, 300 - h), (x + w // 2, 300 - h - 34), (x + w + 8, 300 - h)], fill=(240, 244, 250))
        d.rectangle((x + w // 2 - 8, 300 - h + 14, x + w // 2 + 8, 300 - h + 30), fill=(255, 220, 110))
    text_c(d, (192, 340), 'ADVENT', 42, (250, 226, 140))
    nums = list(range(1, 25)); random.Random(24).shuffle(nums)
    for i, nmb in enumerate(nums):
        cx = 20 + (i % 8) * 43 + 21; cy = 380 + (i // 8) * 40
        d.rectangle((cx - 18, cy - 16, cx + 18, cy + 16), fill=(236, 216, 170), outline=(120, 70, 40), width=2)
        text_c(d, (cx, cy), str(nmb), 18, (150, 26, 36))
    W.save('advent', im)


def painting(W):
    im = Image.new('RGB', (512, 320), (40, 60, 110)); d = ImageDraw.Draw(im)
    for y in range(200):
        c = (int(40 + y * 0.5), int(60 + y * 0.5), int(110 + y * 0.4)); d.line((0, y, 512, y), fill=c)
    d.ellipse((380, 40, 430, 90), fill=(250, 246, 220))
    d.polygon([(0, 230), (140, 150), (300, 220), (420, 160), (512, 200), (512, 320), (0, 320)], fill=(230, 236, 248))
    for (x, s) in ((60, 1.0), (110, 0.7), (420, 1.1), (470, 0.8), (330, 0.6)):
        for k in range(4):
            w = (50 - k * 11) * s; y0 = 260 - (k * 28 + 10) * s
            d.polygon([(x, y0 - 40 * s), (x - w, y0 + 20 * s), (x + w, y0 + 20 * s)], fill=(30, 80, 50))
    d.rectangle((210, 210, 300, 270), fill=(140, 70, 40)); d.polygon([(200, 212), (255, 170), (310, 212)], fill=(240, 244, 250))
    d.rectangle((240, 225, 262, 245), fill=(255, 220, 110))
    im = im.filter(ImageFilter.GaussianBlur(1.0))
    W.save('painting', np.asarray(im, np.float32) + N3(512, 0.5, 271, 6, 320))


def cards(W):
    for i, (bg, motif) in enumerate((((200, 30, 40), 'tree'), ((30, 90, 60), 'star'), ((40, 60, 140), 'flake'))):
        im = Image.new('RGB', (128, 192), bg); d = ImageDraw.Draw(im)
        d.rectangle((6, 6, 121, 185), outline=(240, 210, 120), width=3)
        if motif == 'tree':
            d.polygon([(64, 30), (28, 130), (100, 130)], fill=(30, 120, 60)); d.polygon(star_pts(64, 30, 12, 5), fill=(250, 210, 70))
        elif motif == 'star':
            d.polygon(star_pts(64, 80, 44, 18), fill=(250, 210, 70))
        else:
            snowflake(d, 64, 80, 40, (240, 244, 255), 4)
        text_c(d, (64, 160), 'Merry X-mas', 15, (250, 240, 220))
        W.save('card%d' % i, im)


def letter(W):
    im = Image.new('RGB', (256, 320), (246, 240, 222)); d = ImageDraw.Draw(im)
    for y in range(60, 320, 28): d.line((14, y, 242, y), fill=(190, 200, 220), width=1)
    text_c(d, (128, 34), 'Dear Santa,', 28, (60, 40, 120))
    for i, t in enumerate(['I was VERY good', 'this year! Please', 'bring me a new', 'Imperius and lots', 'of gummy bears.', '      - Padman']):
        text_c(d, (128, 76 + i * 28), t, 19, (60, 40, 120))
    W.save('letter', im)


# ----------------------------------------------------------------------------------------------- shader
SH = "// padxmas.shader - Padman's Christmas (generated by wop_tools/xmas/xmas_textures.py)\n\n"
STEPS = {'floor_oak': 'woodsteps', 'wood_dark': 'woodsteps', 'wood_mid': 'woodsteps', 'wood_light': 'woodsteps',
         'rug': 'carpetsteps', 'rug_edge': 'carpetsteps', 'treeskirt': 'carpetsteps', 'needles_top': 'softsteps',
         'needles': 'softsteps', 'velvet_green': 'softsteps', 'velvet_red': 'softsteps', 'tartan': 'softsteps', 'knit': 'softsteps',
         'cushion_white': 'softsteps', 'tissue': 'softsteps', 'snow': 'snowsteps', 'snow_drift': 'snowsteps',
         'roof_tiles_snow': 'snowsteps', 'burlap': 'softsteps', 'felt_green': 'carpetsteps', 'track': 'woodsteps',
         'pyramid_wood': 'woodsteps', 'gingerbread': 'softsteps', 'ginger_roof': 'softsteps', 'icing': 'softsteps',
         'log_bark': 'woodsteps', 'trim_white': 'woodsteps'}
for _g in GIFTS:
    STEPS['gift_%s_top' % _g] = 'softsteps'; STEPS['gift_%s_side' % _g] = 'softsteps'


def lm(name, steps=None, extra=''):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    return s


def shiny(name, steps=None):
    """lightmapped colour + faint environment sheen (baubles, brass, presents ribbons)"""
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.22 0.22 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return s


def glow(name, light, rgb, wave=None, nonsolid=False, extra=''):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n\tsurfaceparm nolightmap\n'
    if nonsolid: s += '\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n'
    if light: s += f'\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb}\n\tq3map_lightSubdivide 32\n'
    s += extra
    s += f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\trgbGen {wave or "identity"}\n\t}}\n}}\n\n'
    return s


NSV = {'log_bark_ns': 'log_bark', 'log_end_ns': 'log_end', 'brass_ns': 'brass', 'pyramid_ns': 'pyramid_wood', 'nut_red_ns': 'nut_red',
       'nut_green_ns': 'nut_green', 'nut_skin_ns': 'nut_skin', 'nut_white_ns': 'nut_white', 'poinsettia_ns': 'poinsettia'}


def make_shader(W, out):
    S = SH
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 0.55 0.65 1 70 120 40
	q3map_skylight 45 3
	skyparms env/frost-bite512 - -
}}

textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	{{
		map textures/{NS}/glass
		blendFunc GL_DST_COLOR GL_ONE
		rgbGen const ( 0.10 0.12 0.15 )
		tcGen environment
	}}
}}

textures/{NS}/globe_glass
{{
	qer_editorimage textures/{NS}/glass
	qer_trans 0.3
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{{
		map textures/{NS}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.10 0.12 0.15 )
		tcGen environment
	}}
}}

textures/{NS}/fire
{{
	qer_editorimage textures/{NS}/fire0
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	q3map_surfacelight 1600
	q3map_lightRGB 1 0.55 0.2
	cull none
	deformVertexes autosprite2
	{{
		animmap 7 textures/{NS}/fire0 textures/{NS}/fire1 textures/{NS}/fire2 textures/{NS}/fire3
		blendFunc GL_ONE GL_ONE
		rgbGen wave noise 0.85 0.15 0 3
	}}
}}

textures/{NS}/flame
{{
	qer_editorimage textures/{NS}/flame
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	q3map_surfacelight 400
	q3map_lightRGB 1 0.7 0.35
	cull none
	deformVertexes autosprite2
	{{
		map textures/{NS}/flame
		blendFunc GL_ONE GL_ONE
		rgbGen wave noise 0.8 0.2 0 5
	}}
}}

textures/{NS}/smoke
{{
	qer_editorimage textures/{NS}/smoke
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	deformVertexes autosprite2
	{{
		map textures/{NS}/smoke
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0 0.25
	}}
}}

textures/{NS}/snowfall
{{
	qer_editorimage textures/{NS}/snowfall
	qer_trans 0.3
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{{
		map textures/{NS}/snowfall
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.32 0.34 0.4 )
		tcMod scroll 0.02 0.18
	}}
	{{
		map textures/{NS}/snowfall
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.19 0.22 )
		tcMod scale 1.7 1.7
		tcMod scroll -0.03 0.11
	}}
}}

textures/{NS}/tinsel
{{
	qer_editorimage textures/{NS}/tinsel
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map textures/{NS}/tinsel
		rgbGen vertex
	}}
	{{
		map textures/{NS}/tinsel
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.25 0.2 0 0.7
		tcGen environment
	}}
}}

textures/{NS}/tinsel_silver
{{
	qer_editorimage textures/{NS}/tinsel_silver
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map textures/{NS}/tinsel_silver
		rgbGen vertex
	}}
	{{
		map textures/{NS}/tinsel_silver
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.25 0.2 0.5 0.7
		tcGen environment
	}}
}}

textures/{NS}/fabric_ns
{{
	qer_editorimage textures/{NS}/velvet_red
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/velvet_red
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

textures/{NS}/knit_ns
{{
	qer_editorimage textures/{NS}/knit
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/knit
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

textures/{NS}/needles_ns
{{
	qer_editorimage textures/{NS}/needles
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/needles
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

textures/{NS}/wire_ns
{{
	qer_editorimage textures/{NS}/wire
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	{{
		map textures/{NS}/wire
		rgbGen vertex
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

'''
    for nsn, base in NSV.items():
        S += (f'textures/{NS}/{nsn}\n{{\n\tqer_editorimage textures/{NS}/{base}\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
              f'\tsurfaceparm nomarks\n\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n'
              f'\t{{\n\t\tmap textures/{NS}/{base}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S += glow('lampglow', 600, '1 0.85 0.6')
    S += glow('embers', 500, '1 0.45 0.15', 'wave noise 0.8 0.2 0 2')
    S += glow('star_gold', 900, '1 0.85 0.45', 'wave sin 0.9 0.1 0 0.5')
    for i, (nm, rgb) in enumerate((('bulb_red', '1 0.3 0.25'), ('bulb_green', '0.35 1 0.45'), ('bulb_yellow', '1 0.85 0.4'),
                                   ('bulb_blue', '0.45 0.6 1'))):
        S += glow(nm, 260, rgb, f'wave square 0.6 0.4 {i * 0.25:g} 0.5', nonsolid=True)
    S += glow('nose_red', 120, '1 0.2 0.15', 'wave sin 0.75 0.25 0 1')
    S += glow('clockface', 0, None)
    special = {'fire0', 'fire1', 'fire2', 'fire3', 'flame', 'smoke', 'snowfall', 'tinsel', 'tinsel_silver', 'nodraw_ns', 'skylight',
               'glass', 'embers', 'star_gold', 'bulb_red', 'bulb_green', 'bulb_yellow', 'bulb_blue', 'nose_red', 'clockface', 'wire', 'lampglow'}
    for nme in sorted(W.sizes):
        if nme in special: continue
        if nme.startswith('bauble_') or nme.startswith('ribbon_') or nme in ('brass', 'trim_gold'):
            S += shiny(nme, STEPS.get(nme))
        else:
            S += lm(nme, STEPS.get(nme))
    S += f'''levelshots/{MAP}B
{{
	nomipmaps
	{{
		animmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3
	}}
}}

'''
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "Padman\'s Christmas"\n\ttype     "ffa lps team ft ctkd"\n}\n' % MAP)


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
