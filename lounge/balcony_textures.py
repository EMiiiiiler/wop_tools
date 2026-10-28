"""Brush textures, the painted night-city skybox and their shaders for the balcony of wop_padlounge (original art).

    make(W, out) -> shader text   (W = lounge_textures.TexWriter; the sky goes to env/padlounge/night_*.jpg)
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import lounge_textures as LT

NS = LT.NS
noise, N3, C, img, arr, fill = LT.noise, LT.N3, LT.C, LT.img, LT.arr, LT.fill
FACADE_TILE = (1536, 2304)      # one apartment: width x storey height (world units) = one 512 x 768 texture cell


# ------------------------------------------------------------------------------------------------ surfaces
def deck_boards(n=512, seed=401):
    """grey-brown hardwood decking, boards along x (8 per tile), screw dots, a few darker boards"""
    rr = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32)
    bh = n // 8
    for k in range(8):
        base = C((128, 104, 84)) * rr.uniform(0.82, 1.1)
        g = noise(n, 1, seed + k, bh)
        grain = np.sin(np.linspace(0, 1, bh)[:, None] * 18 + g * 2 + np.linspace(0, 8, n)[None, :] * 0.3)
        a[k * bh:(k + 1) * bh] = base + grain[..., None] * 7 + N3(n, 0.7, seed + 20 + k, 5, bh)
        a[k * bh:k * bh + 3] = 30
        for x in (int(rr.uniform(0.1, 0.4) * n), int(rr.uniform(0.6, 0.9) * n)):
            for yy in (k * bh + 10, (k + 1) * bh - 12):
                a[yy - 2:yy + 2, x - 2:x + 2] = 60
    return a * (1 + 0.04 * noise(n, 40, seed + 50))[..., None]


def brick(n=512, seed=403, col=(150, 78, 58)):
    rr = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32) + C((170, 166, 158))          # mortar
    bh, bw = n // 16, n // 4
    for r in range(16):
        off = (bw // 2) * (r % 2)
        for c in range(-1, 5):
            x0 = c * bw + off + 3; y0 = r * bh + 3
            shade = rr.uniform(0.8, 1.15)
            xa, xb = max(0, x0), min(n, x0 + bw - 6)
            if xb <= xa: continue
            a[y0:y0 + bh - 6, xa:xb] = C(col) * shade
    a += N3(n, 0.8, seed + 1, 8) + N3(n, 6, seed + 2, 6)
    return a


def facade(seed=405):
    """two neighbouring apartments side by side (1024 x 768 = 3072 x 2304 world): brick, one big window each with
    curtains, a sill and a little juliet balcony rail. Returns (colour, glow) - glow lights up some windows at night."""
    w, h = 1024, 768
    a = np.concatenate([brick(512, seed), brick(512, seed + 7)], 1)
    a = np.concatenate([a, a[:256]], 0)[:h]
    glow = np.zeros((h, w, 3), np.float32)
    im = img(a); d = ImageDraw.Draw(im); g = Image.fromarray(glow.astype(np.uint8)); dg = ImageDraw.Draw(g)
    rr = np.random.default_rng(seed + 3)
    # storey slab band at the bottom of each storey (concrete), window per apartment
    d.rectangle((0, h - 26, w, h), fill=(150, 150, 146))
    for k in range(2):
        x0 = k * 512 + 110; x1 = x0 + 292; y0 = 210; y1 = 560
        lit = (k == 0)
        d.rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 18), fill=(220, 216, 206))      # frame
        inner = (255, 196, 120) if lit else (26, 30, 44)
        d.rectangle((x0, y0, x1, y1), fill=tuple(int(c * 0.35) for c in inner))
        if lit:
            dg.rectangle((x0, y0, x1, y1), fill=(230, 170, 90))
            # curtains half drawn, a lamp silhouette
            cc = (200, 60, 80) if rr.uniform() < 0.5 else (60, 110, 170)
            d.rectangle((x0, y0, x0 + 70, y1), fill=tuple(int(c * 0.6) for c in cc)); dg.rectangle((x0, y0, x0 + 70, y1), fill=tuple(int(c * 0.5) for c in cc))
            d.rectangle((x1 - 70, y0, x1, y1), fill=tuple(int(c * 0.6) for c in cc)); dg.rectangle((x1 - 70, y0, x1, y1), fill=tuple(int(c * 0.5) for c in cc))
            dg.ellipse((x0 + 150, y0 + 120, x0 + 200, y0 + 160), fill=(255, 230, 170))
            dg.rectangle((x0 + 170, y0 + 160, x0 + 178, y1), fill=(40, 30, 20))
        else:
            d.line((x0 + 20, y0 + 30, x0 + 120, y0 + 130), fill=(60, 70, 90), width=3)   # a reflection streak
        d.rectangle((x0 - 30, y1 + 10, x1 + 30, y1 + 30), fill=(200, 198, 190))         # sill
        for xx in range(x0 - 20, x1 + 24, 22):                                          # juliet rail
            d.line((xx, y1 - 70, xx, y1 + 10), fill=(40, 40, 44), width=3)
        d.line((x0 - 24, y1 - 72, x1 + 24, y1 - 72), fill=(40, 40, 44), width=6)
        # AC box under one of them
        if k == 1:
            d.rectangle((x0 + 60, y1 + 60, x0 + 230, y1 + 150), fill=(210, 210, 206)); d.ellipse((x0 + 90, y1 + 70, x0 + 160, y1 + 140), fill=(70, 70, 74))
    return arr(im), arr(g)


def concrete(n=256, seed=407):
    return fill(n, (150, 148, 142), 6, seed) + N3(n, 20, seed + 2, 8)


def bamboo(w=512, h=512, seed=409):
    rr = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), np.float32)
    x = 0
    while x < w:
        cw = min(int(rr.integers(26, 40)), w - x)
        base = C((176, 150, 88)) * rr.uniform(0.8, 1.1)
        xs = np.linspace(-1, 1, cw)
        shade = (0.65 + 0.35 * np.sqrt(np.clip(1 - xs ** 2, 0, 1)))
        a[:, x:x + cw] = base * shade[None, :, None]
        for y in range(int(rr.integers(0, 120)), h, int(rr.integers(110, 160))):      # nodes
            a[y:y + 5, x:x + cw] *= 0.6
        a[:, x + cw - 2:x + cw] = 30
        x += cw
    return a[:, :w] + N3(w, 0.7, seed + 1, 5, h)


def street(n=512, seed=411):
    """night street seen from above: asphalt, sodium-lit sidewalk, lane dashes, a few car lights"""
    a = fill(n, (30, 30, 34), 6, seed)
    im = img(a); d = ImageDraw.Draw(im); rr = np.random.default_rng(seed)
    d.rectangle((0, 0, n, 90), fill=(70, 64, 56)); d.rectangle((0, n - 90, n, n), fill=(70, 64, 56))
    for x in range(0, n, 64): d.rectangle((x, n // 2 - 3, x + 32, n // 2 + 3), fill=(220, 210, 160))
    glow = Image.new('RGB', (n, n)); dg = ImageDraw.Draw(glow)
    for x in range(40, n, 170):
        dg.ellipse((x - 70, -20, x + 70, 150), fill=(255, 170, 70)); dg.ellipse((x + 20, n - 150, x + 160, n + 20), fill=(255, 170, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    a = arr(im) + arr(glow) * 0.6
    im = img(a); d = ImageDraw.Draw(im)
    for k in range(5):
        y = int(rr.uniform(130, n - 130)); x = int(rr.uniform(0, n - 60))
        col = (255, 250, 220) if y > n // 2 else (255, 60, 50)
        d.rectangle((x, y - 4, x + 50, y + 4), fill=col)
    return im


def far_building(seed=413, base=(28, 30, 42)):
    """windows grid of an apartment block at night, self-lit (nolightmap)"""
    n = 512
    rr = np.random.default_rng(seed)
    a = np.zeros((n, n, 3), np.float32) + C(base) + N3(n, 1, seed, 3)
    for r in range(8):
        for c in range(8):
            x0, y0 = c * 64 + 14, r * 64 + 18
            if rr.uniform() < 0.42:
                col = C(((255, 200, 120), (255, 230, 190), (160, 200, 255), (255, 150, 90))[rr.integers(0, 4)]) * rr.uniform(0.55, 1)
                if rr.uniform() < 0.15: col = C((90, 140, 255)) * 0.8                   # TV glow
            else:
                col = C((14, 16, 24))
            a[y0:y0 + 30, x0:x0 + 36] = col
            if rr.uniform() < 0.3: a[y0:y0 + 30, x0:x0 + 10] *= 0.5                     # curtain
        a[r * 64 + 58:r * 64 + 64] = C(base) * 1.3
    return a


def tub_floor(n=128, seed=415):
    a = np.zeros((n, n, 3), np.float32) + C((120, 200, 230))
    a[::32] *= 0.7; a[:, ::32] *= 0.7
    return a + N3(n, 1, seed, 4)


def doormat(w=512, h=256):
    a = fill(w, (110, 80, 50), 14, 417, h)
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((14, 14, w - 14, h - 14), outline=(50, 36, 24), width=10)
    LT.text_c(d, (w / 2, h / 2), 'GOOD VIBES', 70, (40, 28, 18), maxw=w - 60)
    return im


def nb_door(w=512, h=512):
    """the upstairs neighbour's sliding door seen from outside: lit room behind drawn sheer curtains"""
    a = np.zeros((h, w, 3), np.float32) + C((255, 200, 140)) * 0.85
    yy, xx = np.mgrid[0:h, 0:w]
    a *= (0.75 + 0.25 * np.sin(xx / w * math.pi * 14) ** 2)[..., None]
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(40, 40, 44), width=14); d.line((w / 2, 0, w / 2, h), fill=(40, 40, 44), width=12)
    d.ellipse((150, 330, 230, 390), fill=(90, 60, 40)); d.polygon([(160, 335), (172, 300), (182, 338)], fill=(90, 60, 40))   # cat silhouette
    d.polygon([(205, 335), (215, 300), (226, 338)], fill=(90, 60, 40)); d.ellipse((130, 370, 260, 470), fill=(90, 60, 40))
    return im


def lantern(n=64):
    return np.zeros((n, n, 3), np.float32) + C((255, 210, 140))


# ------------------------------------------------------------------------------------------------ sky
def _sky_side(seed, moon=None, skyline=True):
    n = 512
    rr = np.random.default_rng(seed)
    v = np.linspace(0, 1, n)[:, None]
    top, mid, hor, below = C((6, 8, 26)), C((24, 22, 58)), C((92, 56, 80)), C((14, 12, 22))
    a = np.zeros((n, n, 3), np.float32) + np.where((v < 0.42)[..., None], top + (mid - top) * (v / 0.42)[..., None],
                                                   mid + (hor - mid) * np.clip((v - 0.42) / 0.12, 0, 1)[..., None])
    a[v[:, 0] > 0.55] = below
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(180):                                                # stars
        x, y = rr.integers(0, n), rr.integers(0, int(n * 0.42))
        b = int(rr.uniform(120, 255)); r = 1 if rr.uniform() < 0.85 else 2
        d.ellipse((x - r / 2, y - r / 2, x + r / 2, y + r / 2), fill=(b, b, min(255, b + 20)))
    if moon:
        mx, my, mr = moon
        glow = Image.new('RGB', (n, n)); dg = ImageDraw.Draw(glow); dg.ellipse((mx - mr * 3, my - mr * 3, mx + mr * 3, my + mr * 3), fill=(70, 80, 110))
        im = Image.fromarray(np.clip(arr(im) + arr(glow.filter(ImageFilter.GaussianBlur(25))), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
        d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=(246, 242, 220))
        for (ox, oy, r) in ((-8, -6, 7), (9, 7, 5), (2, -12, 4), (-4, 11, 4)):
            d.ellipse((mx + ox - r, my + oy - r, mx + ox + r, my + oy + r), fill=(214, 210, 192))
    if skyline:
        hz = int(n * 0.555)
        for layer, (col, hmin, hmax, wmin, wmax, lit) in enumerate((((40, 34, 62), 20, 90, 20, 60, 0.15), ((18, 16, 30), 30, 170, 26, 70, 0.35))):
            x = int(rr.integers(-30, 0))
            while x < n:
                bw = int(rr.integers(wmin, wmax)); bh = int(rr.integers(hmin, hmax))
                if layer == 1 and rr.uniform() < 0.08: bh = int(rr.integers(180, 230))      # a tower
                d.rectangle((x, hz - bh, x + bw, hz + 2), fill=col)
                if layer == 1:
                    for wy in range(hz - bh + 6, hz - 2, 7):
                        for wx in range(x + 4, x + bw - 3, 6):
                            if rr.uniform() < lit:
                                c = ((255, 210, 130), (255, 240, 200), (170, 200, 255))[rr.integers(0, 3)]
                                d.rectangle((wx, wy, wx + 2, wy + 3), fill=c)
                    if bh > 120 and rr.uniform() < 0.7:
                        d.ellipse((x + bw / 2 - 3, hz - bh - 8, x + bw / 2 + 3, hz - bh - 2), fill=(255, 40, 40))
                        d.line((x + bw / 2, hz - bh - 2, x + bw / 2, hz - bh), fill=(60, 60, 70), width=2)
                x += bw + int(rr.integers(-4, 10))
        # city lights below the horizon
        for _ in range(500):
            x = rr.integers(0, n); y = int(hz + 4 + rr.uniform(0, 1) ** 2 * (n - hz - 4))
            c = ((255, 170, 70), (255, 220, 160), (200, 220, 255))[rr.integers(0, 3)]
            d.point((x, y), fill=c)
    return im


def make_sky(out):
    d = os.path.join(out, 'env', NS); os.makedirs(d, exist_ok=True)
    faces = {'ft': _sky_side(501, moon=(150, 120, 26)), 'rt': _sky_side(503), 'lf': _sky_side(505), 'bk': _sky_side(507)}
    for k, im in faces.items(): im.save(os.path.join(d, f'night_{k}.jpg'), quality=92)
    up = _sky_side(509, skyline=False).crop((0, 0, 512, 210)).resize((512, 512))
    up.save(os.path.join(d, 'night_up.jpg'), quality=92)
    dn = Image.fromarray(np.full((512, 512, 3), (14, 12, 22), np.uint8)); dd = ImageDraw.Draw(dn); rr = np.random.default_rng(511)
    for _ in range(1500):
        x, y = rr.integers(0, 512, 2); dd.point((int(x), int(y)), fill=((255, 170, 70), (255, 220, 160))[rr.integers(0, 2)])
    dn.save(os.path.join(d, 'night_dn.jpg'), quality=92)


# ------------------------------------------------------------------------------------------------ write + shaders
SPECIAL = {'facade', 'facade_glow', 'street', 'far_a', 'far_b', 'tub_floor', 'nb_door', 'lantern', 'brick'}


def make(W, out):
    W.save('deck', deck_boards()); W.save('brick', brick()); W.save('concrete', concrete()); W.save('bamboo', bamboo())
    fc, fg = facade(); W.save('facade', fc); W.save('facade_glow', fg)
    W.save('street', street()); W.save('far_a', far_building()); W.save('far_b', far_building(415, (34, 28, 36)))
    W.save('tub_floor', tub_floor()); W.save('doormat', doormat()); W.save('nb_door', nb_door()); W.save('lantern', lantern())
    W.save('alu_track', fill(64, (150, 152, 156), 3, 419))
    make_sky(out)
    S = '// ---- balcony (balcony_textures.py)\n'
    S += LT.lm('deck', 'woodsteps') + LT.lm('concrete') + LT.lm('bamboo', 'woodsteps') + LT.lm('doormat', 'carpetsteps') + LT.lm('alu_track', shiny=0.2)
    # big outer walls: coarse lightmaps
    for nm in ('brick',):
        S += LT.lm(nm, extra='\tq3map_lightmapSampleSize 32\n')
    S += (f'textures/{NS}/facade\n{{\n\tqer_editorimage textures/{NS}/facade\n\tq3map_lightmapSampleSize 64\n'
          f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap textures/{NS}/facade\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/facade_glow\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n\t}}\n}}\n\n')
    for nm in ('street', 'far_a', 'far_b'):
        S += (f'textures/{NS}/{nm}\n{{\n\tqer_editorimage textures/{NS}/{nm}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
              f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S += LT.glow('tub_floor', 120, '0.4 0.8 1')
    S += LT.glow('nb_door', 120, '1 0.8 0.55')
    S += LT.glow('lantern', 600, '1 0.8 0.55')
    S += f'''textures/{NS}/water_inner
{{
	qer_editorimage textures/{NS}/tub_floor
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm water
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
}}

'''
    return S
