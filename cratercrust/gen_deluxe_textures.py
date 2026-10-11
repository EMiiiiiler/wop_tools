#!/usr/bin/env python3
"""Crater Crust Deluxe: new textures + shaders (all original art).

    python3 gen_deluxe_textures.py <out>

Expects <out>/textures/ccdeluxe and <out>/scripts/ccdeluxe.shader to exist already (base set copied
from Crater Crust and renamed); adds the deluxe textures and appends their shaders.
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
TD = os.path.join(OUT, 'textures/ccdeluxe')
FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
P = 'textures/ccdeluxe/'
rng = np.random.default_rng(42)
random.seed(42)
SH = []


def font(sz): return ImageFont.truetype(FONT, sz)


def save(name, im, alpha=False):
    if isinstance(im, np.ndarray):
        im = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    if alpha:
        im.convert('RGBA').save(os.path.join(TD, name + '.tga'))
    else:
        im.convert('RGB').save(os.path.join(TD, name + '.jpg'), quality=92)


def noise(w, h, scale=8, octaves=4, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(octaves):
        s = scale * (2 ** o)
        a = np.asarray(Image.fromarray((r.random((s, s)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
        a = (a + np.roll(a, w // 2, 1) + np.roll(a, h // 2, 0) + np.roll(np.roll(a, w // 2, 1), h // 2, 0)) / 4
        out += a * amp; tot += amp; amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


def mix(c1, c2, n):
    c1 = np.array(c1, float); c2 = np.array(c2, float)
    return c1[None, None] * (1 - n[..., None]) + c2[None, None] * n[..., None]


# ------------------------------------------------------------------ shader writers
def sh_lm(name, ext='jpg', parms=(), extra=(), scroll=None):
    s = [P + name, '{', f'\tqer_editorimage {P}{name}.{ext}']
    s += ['\tsurfaceparm ' + p for p in parms] + ['\t' + e for e in extra]
    tc = f'\n\t\ttcMod scroll {scroll[0]} {scroll[1]}' if scroll else ''
    if scroll:   # texture first (scrolling), then lightmap multiplied in
        s.append(f'\t{{\n\t\tmap {P}{name}.{ext}{tc}\n\t\trgbGen identity\n\t}}')
        s.append('\t{\n\t\tmap $lightmap\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}')
    else:
        s.append('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}')
        s.append(f'\t{{\n\t\tmap {P}{name}.{ext}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}')
    s.append('}\n')
    SH.append('\n'.join(s))


def sh_glow(name, light, ext='jpg', parms=(), pulse=None, subdiv=64, extra=()):
    rg = f'rgbGen wave sin {pulse}' if pulse else 'rgbGen identity'
    s = [P + name, '{', f'\tqer_editorimage {P}{name}.{ext}', f'\tq3map_surfacelight {light}',
         f'\tq3map_lightSubdivide {subdiv}', '\tsurfaceparm nomarks']
    s += ['\tsurfaceparm ' + p for p in parms] + ['\t' + e for e in extra]
    s.append('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}')
    s.append(f'\t{{\n\t\tmap {P}{name}.{ext}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}')
    s.append(f'\t{{\n\t\tmap {P}{name}.{ext}\n\t\tblendFunc GL_ONE GL_ONE\n\t\t{rg}\n\t}}')
    s.append('}\n')
    SH.append('\n'.join(s))


# ------------------------------------------------------------------ signs
def neon_sign(name, text, w, h, col, sub=None, subcol=(255, 230, 60), border=(60, 230, 255), bg=(22, 8, 44)):
    im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
    bw = max(4, h // 24)
    d.rounded_rectangle([bw, bw, w - bw - 1, h - bw - 1], radius=h // 6, outline=border, width=bw)
    fs = int(h * (0.52 if sub else 0.62))
    while fs > 8 and d.textlength(text, font=font(fs)) > w * 0.86: fs -= 2
    ty = h * (0.42 if sub else 0.5)
    glow = Image.new('RGB', (w, h)); gd = ImageDraw.Draw(glow)
    gd.text((w / 2, ty), text, fill=col, font=font(fs), anchor='mm')
    glow = glow.filter(ImageFilter.GaussianBlur(max(2, h // 18)))
    im = Image.fromarray(np.clip(np.asarray(im, float) + np.asarray(glow, float) * 1.5, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    light = tuple(min(255, c + 140) for c in col)
    d.text((w / 2, ty), text, fill=light, font=font(fs), anchor='mm')
    if sub:
        ss = int(h * 0.17)
        while ss > 6 and d.textlength(sub, font=font(ss)) > w * 0.86: ss -= 1
        d.text((w / 2, h * 0.8), sub, fill=subcol, font=font(ss), anchor='mm')
    save(name, im)
    sh_glow(name, 140, parms=('metalsteps',), subdiv=128)


def logo(size):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = size
    mask = Image.new('L', (s, s), 0); md = ImageDraw.Draw(mask)
    md.ellipse([s * .08, s * .08, s * .92, s * .92], fill=255); md.ellipse([s * .32, s * .02, s * 1.1, s * .80], fill=0)
    cheese = Image.new('L', (s, s), 0); cd = ImageDraw.Draw(cheese)
    cd.ellipse([s * .14, s * .14, s * .86, s * .86], fill=255); cd.ellipse([s * .30, s * .04, s * 1.04, s * .78], fill=0)
    im.paste(Image.new('RGBA', (s, s), (214, 140, 60, 255)), (0, 0), mask)
    im.paste(Image.new('RGBA', (s, s), (255, 206, 60, 255)), (0, 0), cheese)
    for (cx, cy, r) in ((.25, .52, .07), (.34, .74, .06), (.52, .82, .05), (.21, .33, .045)):
        d.ellipse([s * (cx - r), s * (cy - r), s * (cx + r), s * (cy + r)], fill=(196, 40, 36, 255))
    cx, cy, r = s * .78, s * .26, s * .1
    d.polygon([(cx + (r if k % 2 == 0 else r * .42) * math.cos(-math.pi / 2 + k * math.pi / 5),
                cy + (r if k % 2 == 0 else r * .42) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)], fill=(120, 240, 255, 255))
    return im


def logo_sign():
    s = 512
    im = Image.new('RGB', (s, s), (22, 8, 44)); d = ImageDraw.Draw(im)
    d.ellipse([8, 8, s - 8, s - 8], outline=(60, 230, 255), width=14)
    d.ellipse([30, 30, s - 30, s - 30], fill=(40, 14, 80))
    lg = logo(330); im.paste(lg, (90, 40), lg)
    d.text((s / 2, 400), 'CRATER', fill=(255, 210, 245), font=font(64), anchor='mm')
    d.text((s / 2, 458), 'CRUST', fill=(255, 230, 60), font=font(44), anchor='mm')
    save('ccd_logo_sign', im)
    sh_glow('ccd_logo_sign', 220, parms=('metalsteps',), subdiv=128)


# ------------------------------------------------------------------ materials
def slide():
    w = 256; im = Image.new('RGB', (w, w), (235, 245, 255)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64):
        d.rectangle([k, 0, k + 24, w], fill=(80, 200, 255))
    a = np.asarray(im, float) + rng.normal(0, 3, (w, w, 3))
    save('ccd_slide', a)
    SH.append(f'''{P}ccd_slide
{{
	qer_editorimage {P}ccd_slide.jpg
	surfaceparm slick
	surfaceparm metalsteps
	surfaceparm nomarks
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map {P}ccd_slide.jpg
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map {P}ccd_shine.jpg
		blendFunc GL_ONE GL_ONE
		tcGen environment
		rgbGen const ( 0.25 0.25 0.3 )
	}}
}}
''')
    # environment shine
    n = noise(128, 128, 4, 3, 7)
    save('ccd_shine', mix((10, 10, 30), (255, 255, 255), n ** 3))
    im = Image.new('RGB', (w, w), (255, 60, 170)); d = ImageDraw.Draw(im)
    for k in range(0, w, 32): d.line([(0, k), (w, k)], fill=(255, 120, 210), width=4)
    save('ccd_slide_wall', im)
    sh_lm('ccd_slide_wall', parms=('metalsteps',))


def curtain():
    w = 256
    x = np.arange(w)[None, :].repeat(w, 0)
    folds = (np.sin(x / w * 2 * math.pi * 8) + 1) / 2
    a = mix((90, 0, 20), (210, 30, 60), folds ** 1.5)
    a += (noise(w, w, 4, 3, 21)[..., None] - .5) * 20
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for y in range(20, w, 64):
        for xx in range(32, w, 64):
            cx, cy, r = xx + (y // 64 % 2) * 32, y, 6
            d.polygon([(cx + (r if k % 2 == 0 else r * .4) * math.cos(-math.pi / 2 + k * math.pi / 5),
                        cy + (r if k % 2 == 0 else r * .4) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)], fill=(255, 210, 90))
    save('ccd_curtain', im)
    sh_lm('ccd_curtain', parms=('softsteps',))
    # photo booth bead curtain: nonsolid alpha strands
    im = Image.new('RGBA', (64, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(0, 64, 8):
        for y in range(0, 128, 8):
            c = [(255, 60, 200), (60, 230, 255), (255, 230, 60)][(k // 8 + y // 8) % 3]
            d.ellipse([k + 1, y + 1, k + 6, y + 6], fill=c + (255,))
    save('ccd_beads', im, alpha=True)
    SH.append(f'''{P}curtain_ns
{{
	qer_editorimage {P}ccd_beads.tga
	qer_trans 0.6
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	deformVertexes wave 24 sin 0 1.5 0 0.4
	{{
		map {P}ccd_beads.tga
		alphaFunc GE128
		rgbGen identity
	}}
}}
''')


def freezer():
    w = 256; n = noise(w, w, 8, 4, 31)
    a = mix((150, 185, 210), (220, 240, 252), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64): d.line([(k, 0), (k, w)], fill=(120, 150, 175), width=4)
    for y in range(0, w, 16): d.line([(0, y), (w, y)], fill=(170, 200, 220), width=1)
    frost = noise(w, w, 32, 2, 32)
    a = np.asarray(im, float); a = a * (1 - frost[..., None] * .25) + 255 * frost[..., None] * .25
    save('ccd_ice_wall', a)
    sh_lm('ccd_ice_wall', parms=('metalsteps',))
    n = noise(w, w, 16, 4, 33)
    a = mix((200, 220, 235), (250, 252, 255), n) + rng.normal(0, 5, (w, w, 3))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 128): d.line([(k, 0), (k, w)], fill=(170, 190, 210), width=3); d.line([(0, k), (w, k)], fill=(170, 190, 210), width=3)
    save('ccd_frost_floor', im)
    sh_lm('ccd_frost_floor', parms=('snowsteps',))
    im = Image.new('RGB', (w, w)); d = ImageDraw.Draw(im)
    for i in range(2):
        for j in range(2):
            n = noise(128, 128, 4, 3, 40 + i * 2 + j)
            blk = Image.fromarray(np.clip(mix((120, 190, 230), (225, 245, 255), n), 0, 255).astype(np.uint8))
            im.paste(blk, (i * 128, j * 128))
    d.rectangle([0, 0, w - 1, w - 1], outline=(240, 250, 255), width=6)
    d.line([(128, 0), (128, w)], fill=(240, 250, 255), width=4); d.line([(0, 128), (w, 128)], fill=(240, 250, 255), width=4)
    save('ccd_iceblock', im)
    sh_lm('ccd_iceblock', parms=('snowsteps',))


def aquarium():
    w, h = 256, 128
    y = np.linspace(0, 1, h)[:, None]
    a = (np.array([20, 90, 140]) * (1 - y[..., None]) + np.array([5, 40, 80]) * y[..., None]).repeat(w, 1)
    a += (noise(w, h, 8, 3, 51)[..., None] - .5) * 30
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 18):      # weed + pebbles
        hgt = random.randint(30, 70)
        d.line([(k + 6 + 4 * math.sin(t / 6), h - t) for t in range(0, hgt, 3)], fill=(40, 160, 80), width=3)
    for k in range(70):
        x0 = random.randrange(w); d.ellipse([x0, h - 10 + random.randint(0, 6), x0 + 7, h - 3 + random.randint(0, 3)], fill=random.choice([(200, 180, 140), (150, 130, 110), (230, 220, 200)]))
    save('ccd_aqua_bg', im)
    fish = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(fish)
    for (x, yy, c, s) in ((30, 30, (255, 140, 30), 1.0), (110, 70, (255, 230, 60), 0.8), (180, 40, (255, 80, 160), 1.2), (220, 90, (80, 230, 255), 0.7), (70, 100, (255, 200, 80), 0.6)):
        d.ellipse([x - 14 * s, yy - 7 * s, x + 14 * s, yy + 7 * s], fill=c + (255,))
        d.polygon([(x - 12 * s, yy), (x - 24 * s, yy - 8 * s), (x - 24 * s, yy + 8 * s)], fill=c + (255,))
        d.ellipse([x + 6 * s, yy - 3 * s, x + 10 * s, yy + 1 * s], fill=(10, 10, 10, 255))
        d.line([(x - 4 * s, yy - 6 * s), (x - 4 * s, yy + 6 * s)], fill=(255, 255, 255, 255), width=max(1, int(2 * s)))
    save('ccd_aqua_fish', fish, alpha=True)
    bub = Image.new('RGBA', (64, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(bub)
    for k in range(18):
        x0, y0, r = random.randrange(6, 58), random.randrange(128), random.randint(2, 5)
        d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], outline=(220, 245, 255, 255), width=1)
    save('ccd_aqua_bubbles', bub, alpha=True)
    SH.append(f'''{P}ccd_aquarium
{{
	qer_editorimage {P}ccd_aqua_bg.jpg
	q3map_surfacelight 120
	q3map_lightSubdivide 64
	surfaceparm nomarks
	{{
		map {P}ccd_aqua_bg.jpg
		rgbGen identity
	}}
	{{
		map {P}ccd_aqua_fish.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		tcMod scroll -0.06 0
		tcMod turb 0 0.02 0 0.3
		rgbGen identity
	}}
	{{
		map {P}ccd_aqua_fish.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		tcMod scale -1 1
		tcMod scroll 0.04 0.3
		rgbGen const ( 0.7 0.7 0.8 )
	}}
	{{
		map {P}ccd_aqua_bubbles.tga
		blendFunc GL_ONE GL_ONE
		tcMod scale 3 1
		tcMod scroll 0 0.25
		rgbGen identity
	}}
}}
''')


def saucer():
    w = 256; n = noise(w, w, 8, 4, 61)
    a = mix((120, 120, 150), (200, 200, 225), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(0, w, 64):
        d.line([(k, 0), (k, w)], fill=(90, 90, 120), width=3); d.line([(0, k), (w, k)], fill=(90, 90, 120), width=3)
        for j in range(8, w, 32): d.ellipse([k + 4, j - 2, k + 8, j + 2], fill=(80, 80, 100))
    save('ccd_saucer', im)
    sh_lm('ccd_saucer', parms=('metalsteps',))
    im = Image.new('RGB', (w, w), (70, 70, 95)); d = ImageDraw.Draw(im)
    for k in range(0, w, 128): d.line([(k, 0), (k, w)], fill=(50, 50, 70), width=4)
    d.ellipse([90, 90, 166, 166], outline=(60, 230, 255), width=6)
    d.text((128, 128), 'X-7', fill=(60, 230, 255), font=font(26), anchor='mm')
    save('ccd_saucer_deck', grime(np.asarray(im, float), 10, 62))
    sh_lm('ccd_saucer_deck', parms=('metalsteps',))
    im = Image.new('RGB', (w, 64), (40, 40, 60)); d = ImageDraw.Draw(im)
    cols = [(255, 60, 200), (60, 230, 255), (255, 230, 60), (120, 255, 120)]
    for k in range(8):
        d.ellipse([k * 32 + 6, 16, k * 32 + 26, 46], fill=cols[k % 4])
    save('ccd_saucer_rim', im)
    sh_glow('ccd_saucer_rim', 300, parms=('metalsteps',), pulse='0.7 0.3 0 1.5', subdiv=32)
    n = noise(w, w, 4, 3, 63)
    save('ccd_saucer_under', mix((20, 120, 60), (120, 255, 150), n ** 2))
    sh_glow('ccd_saucer_under', 500, parms=('metalsteps',), pulse='0.85 0.15 0 0.7', subdiv=64)
    # tractor beam (nonsolid, additive, scrolling rings)
    im = Image.new('RGB', (64, 128), (0, 0, 0)); d = ImageDraw.Draw(im)
    for y in range(0, 128, 16):
        d.rectangle([0, y, 64, y + 5], fill=(60, 255, 140))
    im = im.filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(im, float) * 0.6 + np.array([5, 40, 20])
    save('ccd_beam', a)
    SH.append(f'''{P}beam_ns
{{
	qer_editorimage {P}ccd_beam.jpg
	qer_trans 0.4
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{{
		map {P}ccd_beam.jpg
		blendFunc GL_ONE GL_ONE
		tcMod scroll 0 0.8
		rgbGen wave sin 0.7 0.2 0 0.5
	}}
}}
''')
    im = Image.new('RGB', (w, w), (10, 30, 20)); d = ImageDraw.Draw(im)
    for r, c in ((120, (60, 255, 140)), (100, (10, 30, 20)), (84, (60, 255, 140)), (60, (10, 30, 20)), (40, (180, 255, 210))):
        d.ellipse([128 - r, 128 - r, 128 + r, 128 + r], fill=c)
    save('ccd_beam_pad', im)
    sh_glow('ccd_beam_pad', 350, parms=('metalsteps',), pulse='0.7 0.3 0 1.2', subdiv=32)


def grime(arr, amt=18, seed=1, scale=6):
    n = noise(arr.shape[1], arr.shape[0], scale, 4, seed)
    return arr - (n[..., None] - 0.5) * amt * 2


def kitchen_bits():
    w = 256; im = Image.new('RGB', (w, w), (40, 40, 44)); d = ImageDraw.Draw(im)
    for k in range(0, w, 32): d.rectangle([0, k, w, k + 4], fill=(70, 70, 76))
    for k in range(16, w, 64): d.ellipse([60, k, 76, k + 16], fill=(230, 160, 60)); d.ellipse([180, k + 32, 196, k + 48], fill=(230, 160, 60))
    save('ccd_belt', grime(np.asarray(im, float), 8, 71))
    sh_lm('ccd_belt', parms=('metalsteps',), scroll=(0, 0.25))
    n = noise(64, 64, 4, 3, 72)
    save('ccd_heatlamp', mix((255, 110, 20), (255, 210, 120), n))
    sh_glow('ccd_heatlamp', 600, pulse='0.9 0.1 0 0.3', subdiv=32)
    n = noise(w, w, 16, 4, 73)
    a = mix((50, 32, 20), (95, 65, 40), n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(40):
        x, y = random.randrange(w), random.randrange(w)
        d.line([(x, y), (x + 3, y - 6)], fill=(90, 170, 60), width=2)
    save('ccd_soil', im)
    sh_lm('ccd_soil', parms=('sandsteps',))


def rides():
    w = 256; im = Image.new('RGB', (w, w), (30, 20, 60)); d = ImageDraw.Draw(im)
    for k in range(12):
        a0 = k * 30
        d.pieslice([-w, -w, 2 * w, 2 * w], a0, a0 + 15, fill=[(255, 60, 200), (60, 230, 255), (255, 230, 60)][k % 3])
    d.ellipse([96, 96, 160, 160], fill=(30, 20, 60))
    save('ccd_carousel', im)
    sh_lm('ccd_carousel', parms=('metalsteps',))
    im = Image.new('RGB', (w, w), (235, 235, 240)); d = ImageDraw.Draw(im)
    d.rectangle([0, 100, w, 156], fill=(220, 40, 50))
    for k in range(0, w, 64): d.ellipse([k + 16, 112, k + 48, 144], fill=(60, 200, 255), outline=(40, 40, 60), width=4)
    save('ccd_rocket', im)
    sh_lm('ccd_rocket', parms=('metalsteps',))
    n = noise(128, 128, 4, 3, 81)
    save('ccd_sun', mix((255, 150, 20), (255, 240, 120), n))
    sh_glow('ccd_sun', 300, subdiv=32)
    y = np.linspace(0, 1, 128)[:, None].repeat(128, 1)
    bands = (np.sin(y * math.pi * 9 + noise(128, 128, 4, 2, 82) * 3) + 1) / 2
    save('ccd_planet', mix((80, 120, 255), (255, 140, 200), bands))
    sh_lm('ccd_planet')


def clouds():
    w = 256
    n = noise(w, w, 4, 5, 91)
    a = np.clip((n - 0.45) * 2.4, 0, 1)
    rgba = np.zeros((w, w, 4)); rgba[..., 0] = 120; rgba[..., 1] = 90; rgba[..., 2] = 170; rgba[..., 3] = a * 170
    save('ccd_clouds', Image.fromarray(rgba.astype(np.uint8), 'RGBA'), alpha=True)


def main():
    slide(); curtain(); freezer(); aquarium(); saucer(); kitchen_bits(); rides(); clouds(); logo_sign()
    neon_sign('ccd_sign_gamezone', 'GAME ZONE', 512, 128, (255, 60, 200), sub='HIGH SCORES WIN PIZZA')
    neon_sign('ccd_sign_prizes', 'PRIZES', 512, 128, (255, 230, 60), sub='TRADE YOUR TICKETS', subcol=(60, 230, 255))
    neon_sign('ccd_sign_diner', 'DINER', 512, 128, (60, 230, 255), sub='HOT SLICES 24/7')
    neon_sign('ccd_sign_live', 'LIVE TONIGHT', 512, 128, (255, 230, 60), sub='THE CRUST-O-NAUTS', subcol=(255, 120, 220))
    neon_sign('ccd_sign_staff', 'STAFF ONLY', 512, 128, (255, 80, 80), border=(255, 80, 80))
    neon_sign('ccd_sign_freezer', 'FREEZER', 512, 128, (150, 230, 255), border=(150, 230, 255), bg=(10, 30, 60))
    neon_sign('ccd_sign_photo', 'PHOTO', 256, 128, (255, 120, 220), sub='4 POSES')
    neon_sign('ccd_sign_beam', 'BEAM ME UP', 512, 128, (120, 255, 150), border=(120, 255, 150), bg=(5, 25, 15))
    neon_sign('ccd_sign_open', 'OPEN LATE', 512, 128, (255, 60, 200), sub='DRIVE-IN  PICK-UP')
    # sky: same box, drifting cloud layer
    SH.insert(0, '''textures/ccdeluxe/cc_sky
{
	qer_editorimage env/ccdeluxe/cc_sky_ft.jpg
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm sky
	q3map_sunExt 0.62 0.68 1.0 110 70 40 3 16
	q3map_skyLight 40 3
	skyparms env/ccdeluxe/cc_sky 384 -
	{
		map textures/ccdeluxe/ccd_clouds.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		tcMod scale 2 2
		tcMod scroll 0.006 0.002
		rgbGen identity
	}
}
''')
    path = os.path.join(OUT, 'scripts/ccdeluxe.shader')
    base = open(path).read()
    # drop the base sky shader, deluxe one replaces it
    i = base.index('textures/ccdeluxe/cc_sky\n'); j = base.index('}\n', i) + 2
    base = base[:i] + base[j:]
    open(path, 'w').write(base.replace('// Crater Crust (wop_cratercrust) - shaders', '// Crater Crust Deluxe (wop_cratercrust_deluxe) - shaders')
                          + '\n// ---------------- deluxe additions\n' + '\n'.join(SH))
    print('deluxe shaders:', len(SH))


main()
