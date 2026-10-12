"""Procedural textures + shader + arena for wop_padbath (Battle in the Bathtub).
All art is original and generated here. make_all(out) writes textures/padbath/*, scripts/padbath.shader and
scripts/wop_padbath.arena (pk3dir layout). Helpers are shared with playroom/textures.py."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('playroom_textures', os.path.join(os.path.dirname(HERE), 'playroom', 'textures.py'))
_pt = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_pt)
noise, C, N3, img, fill, font, text_c, planks = _pt.noise, _pt.C, _pt.N3, _pt.img, _pt.fill, _pt.font, _pt.text_c, _pt.planks

MAP = 'wop_padbath'
NS = 'padbath'
R = random.Random(1906)


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


def soft(im, r=0.6):
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32)


def tile_draw(im, fn):
    d = ImageDraw.Draw(im); n = im.size[0]
    for ox in (-n, 0, n):
        for oy in (-n, 0, n):
            fn(d, ox, oy)
    return im


def duck_icon(d, x, y, s, body=(250, 210, 40), beak=(240, 120, 30), eye=(30, 30, 30)):
    """little side-view rubber duck facing right, centred at x,y, size s"""
    d.ellipse((x - s, y - s * 0.35, x + s * 0.9, y + s * 0.65), fill=body)                        # body
    d.polygon([(x - s, y - s * 0.1), (x - s * 1.25, y - s * 0.45), (x - s * 0.8, y + s * 0.05)], fill=body)   # tail
    d.ellipse((x + s * 0.05, y - s * 1.05, x + s * 0.85, y - s * 0.25), fill=body)                # head
    d.polygon([(x + s * 0.75, y - s * 0.7), (x + s * 1.2, y - s * 0.6), (x + s * 0.75, y - s * 0.45)], fill=beak)
    d.ellipse((x + s * 0.48, y - s * 0.85, x + s * 0.62, y - s * 0.71), fill=eye)


def tiles(n, col, grout, ntile, seed, var=6, bevel=True):
    """square ceramic tiles, ntile per side"""
    a = np.zeros((n, n, 3), np.float32) + C(grout)
    t = n // ntile
    rr = random.Random(seed)
    for i in range(ntile):
        for j in range(ntile):
            c = C(col) * rr.uniform(1 - var / 200, 1 + var / 200)
            a[j * t + 2:(j + 1) * t - 2, i * t + 2:(i + 1) * t - 2] = c
            if bevel:
                a[j * t + 2:j * t + 5, i * t + 2:(i + 1) * t - 2] += 14
                a[(j + 1) * t - 5:(j + 1) * t - 2, i * t + 2:(i + 1) * t - 2] -= 12
    return a + N3(n, 0.8, seed, 2.5) + N3(n, 10, seed + 1, 2)


def jumppad_tex():
    im = Image.new('RGB', (256, 256), (40, 40, 44)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 252, 252), fill=(30, 140, 210)); d.ellipse((28, 28, 228, 228), fill=(246, 246, 240))
    d.ellipse((52, 52, 204, 204), fill=(60, 190, 230))
    duck_icon(d, 124, 150, 52)
    return im


def stripe_band(n, base, band, y0, y1):
    a = fill(n, base, 3, 7)
    a[y0:y1] = C(band) + N3(n, 1, 9, 3)[y0:y1]
    return a


def make_textures(W):
    n = 256
    # ---------------------------------------------------------------- room
    W.save('tile_wall', tiles(n, (236, 240, 242), (186, 192, 196), 4, 11))
    W.save('tile_blue', tiles(n, (120, 186, 220), (190, 210, 220), 4, 12))
    # border band: blue tiles with a duck on every tile (256 x 64)
    im = Image.fromarray(np.clip(tiles(256, (84, 160, 210), (200, 214, 222), 4, 13), 0, 255).astype(np.uint8)).crop((0, 0, 256, 64))
    d = ImageDraw.Draw(im)
    for k in range(4): duck_icon(d, 32 + k * 64, 40, 15)
    W.save('tile_border', soft(im, 0.4))
    W.save('ceiling', fill(n, (236, 236, 232), 3, 21))
    W.save('grout_dark', fill(64, (90, 96, 100), 3, 22))
    # enamel (bath) + floor with anti-slip dots
    W.save('enamel', fill(n, (246, 246, 242), 2, 31) + N3(n, 30, 32, 3))
    im = Image.fromarray(np.clip(fill(n, (238, 240, 238), 2, 33), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for i in range(8):
        for j in range(8):
            x = 16 + i * 32 + (16 if j % 2 else 0); y = 16 + j * 32
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(214, 220, 224))
    W.save('enamel_floor', soft(im, 0.6))
    W.save('chrome', fill(n, (196, 204, 212), 3, 41) + N3(n, 2, 42, 10) + (np.linspace(-30, 30, n)[:, None, None]))
    # drain grate
    im = Image.new('RGB', (128, 128), (190, 196, 204)); d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 125, 125), fill=(206, 212, 220), outline=(120, 126, 134), width=4)
    for r in (20, 36, 52):
        for k in range(int(r * 0.45)):
            a = 2 * math.pi * k / int(r * 0.45)
            x, y = 64 + r * math.cos(a), 64 + r * math.sin(a)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(30, 34, 40))
    d.ellipse((58, 58, 70, 70), fill=(30, 34, 40))
    W.save('drain', soft(im, 0.4))
    W.save('plug', fill(64, (30, 30, 34), 3, 43))
    # curtain: pastel blue with bubbles and ducks (tall: 256 x 512)
    im = Image.fromarray(np.clip(fill(256, (176, 214, 236), 3, 51, 512), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    rr = random.Random(52)
    for _ in range(46):
        x, y, r = rr.randint(0, 255), rr.randint(0, 511), rr.randint(6, 22)
        for ox in (-256, 0, 256):
            d.ellipse((x + ox - r, y - r, x + ox + r, y + r), outline=(240, 248, 255), width=3)
            d.ellipse((x + ox - r * 0.5, y - r * 0.6, x + ox - r * 0.2, y - r * 0.3), fill=(250, 252, 255))
    for (x, y) in ((70, 90), (190, 230), (60, 360), (180, 470)):
        duck_icon(d, x, y, 30)
    a = soft(im, 0.5)
    shade = (0.82 + 0.18 * np.sin(np.linspace(0, 2 * math.pi, 256)))[None, :, None]   # fold shading across u
    W.save('curtain', a * shade)
    W.save('rail', fill(64, (210, 214, 220), 3, 53) + N3(64, 1, 54, 12))

    # ---------------------------------------------------------------- ships
    def hull(col, seed):
        a = fill(n, col, 3, seed)
        for y in (60, 190):                                   # plate seams
            a[y:y + 2] *= 0.75
        for x in range(0, n, 64):
            a[:, x:x + 2] *= 0.8
        for y in (30, 160):                                    # rivets
            for x in range(8, n, 16):
                a[y - 1:y + 2, x - 1:x + 2] += 25
        return a
    W.save('hull_red', hull((176, 40, 40), 61))
    W.save('hull_blue', hull((40, 80, 170), 62))
    W.save('hull_bottom', fill(n, (60, 30, 30), 4, 63))
    W.save('hull_stripe_red', stripe_band(n, (176, 40, 40), (240, 240, 236), 96, 160))
    W.save('hull_stripe_blue', stripe_band(n, (40, 80, 170), (240, 240, 236), 96, 160))
    W.save('deck', planks(n, (150, 150, 146), 8, 64, gap=(60, 60, 64), knots=False))
    W.save('ship_grey', fill(n, (166, 172, 178), 3, 65) + N3(n, 20, 66, 4))
    W.save('ship_dark', fill(n, (90, 96, 104), 3, 67))
    W.save('trim_red', fill(64, (210, 40, 40), 3, 68))
    W.save('trim_blue', fill(64, (40, 100, 220), 3, 69))
    # superstructure wall with portholes (one porthole row centred on the texture)
    for team, rim_c in (('red', (200, 50, 50)), ('blue', (50, 100, 210))):
        im = Image.fromarray(np.clip(fill(n, (176, 182, 188), 3, 70), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
        for k in range(2):
            cx = 64 + k * 128; cy = 112
            d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=rim_c)
            d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(40, 70, 100))
            d.ellipse((cx - 14, cy - 16, cx - 4, cy - 6), fill=(150, 200, 230))
        W.save('porthole_' + team, soft(im, 0.5))
    # bridge windows strip (256 x 64)
    im = Image.new('RGB', (256, 64), (170, 176, 182)); d = ImageDraw.Draw(im)
    for k in range(4):
        d.rectangle((8 + k * 64, 10, 56 + k * 64, 54), fill=(30, 50, 70), outline=(230, 230, 230), width=3)
        d.line((14 + k * 64, 48, 40 + k * 64, 16), fill=(120, 170, 210), width=3)
    W.save('bridge_windows', soft(im, 0.4))
    for team, c in (('red', (200, 36, 36)), ('blue', (36, 90, 210))):
        a = fill(n, (36, 36, 40), 3, 71)
        a[64:128] = C(c) + N3(n, 1, 72, 3)[64:128]
        a[140:156] = C((240, 240, 236))
        W.save('funnel_' + team, a)
        W.save('flag_' + team, flag_tex(team))
    W.save('turret', fill(n, (130, 136, 142), 3, 73) + N3(n, 16, 74, 5))
    W.save('crate', planks(n, (176, 132, 78), 4, 75, gap=(80, 56, 30)))
    W.save('crate_side', crate_side())
    W.save('rope', fill(64, (190, 160, 110), 6, 76))
    # ship name boards (512 x 96)
    for team, name, c in (('red', 'S.S. RUBBER RUBY', (200, 36, 36)), ('blue', 'H.M.S. BUBBLE BLUE', (36, 90, 210))):
        im = Image.new('RGB', (512, 96), (240, 240, 232)); d = ImageDraw.Draw(im)
        d.rectangle((4, 4, 507, 91), outline=c, width=6)
        text_c(d, (256, 50), name, 50, c, maxw=480)
        W.save('name_' + team, im)
    # lifebuoy (red/white segments, used on flat ring brushes)
    a = np.zeros((64, 256, 3), np.float32)
    for k in range(8):
        a[:, k * 32:(k + 1) * 32] = C((220, 40, 40) if k % 2 == 0 else (244, 244, 240))
    W.save('buoy', a + N3(256, 1, 77, 3, 64))

    # ---------------------------------------------------------------- toy ferries
    W.save('boat_yellow', hull((236, 196, 40), 81))
    W.save('boat_green', hull((60, 170, 90), 82))
    W.save('boat_deck', planks(n, (180, 120, 70), 6, 83, gap=(70, 46, 26)))
    im = Image.new('RGB', (256, 128), (240, 240, 236)); d = ImageDraw.Draw(im)
    for k in range(3):
        d.rounded_rectangle((14 + k * 80, 26, 76 + k * 80, 84), 10, fill=(40, 70, 100), outline=(200, 60, 40), width=4)
    d.rectangle((0, 108, 256, 128), fill=(200, 60, 40))
    W.save('boat_cabin', soft(im, 0.4))
    W.save('boat_roof', fill(n, (200, 60, 40), 3, 84))

    # ---------------------------------------------------------------- toys
    marb = noise(n, 14, 91)
    W.save('soap', np.zeros((n, n, 3), np.float32) + C((238, 168, 196)) + marb[..., None] * C((10, 8, 10)) + N3(n, 1, 92, 2))
    im = Image.fromarray(np.clip(np.zeros((256, 512, 3), np.float32) + C((238, 168, 196)) + noise(512, 14, 93, 256)[..., None] * 9, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 30, 486, 226), 50, outline=(214, 140, 172), width=10)
    text_c(d, (256, 128), 'PADSOAP', 100, (220, 146, 178), stroke=3, stroke_fill=(250, 196, 220))
    W.save('soap_top', soft(im, 0.8))
    # sponge: yellow with pores
    a = fill(n, (236, 204, 60), 5, 94)
    pores = noise(n, 1.5, 95)
    a[pores > 1.2] *= 0.62
    a[(pores > 0.9) & (pores <= 1.2)] *= 0.8
    W.save('sponge', a)
    a = fill(n, (60, 150, 70), 6, 96)
    a[noise(n, 1.2, 97) > 1.0] *= 0.6
    W.save('sponge_green', a)
    for nm, c in (('ring_red', (220, 50, 50)), ('ring_orange', (240, 140, 40)), ('ring_yellow', (244, 210, 50)),
                  ('ring_green', (70, 180, 80)), ('ring_blue', (60, 120, 220)), ('ring_purple', (150, 80, 200)),
                  ('float_white', (240, 242, 244))):
        W.save(nm, fill(n, c, 3, sum(map(ord, nm)) % 997) + N3(n, 30, 98, 6))
    a = fill(n, (246, 248, 250), 3, 99)
    bub = noise(n, 3, 100)
    a += np.clip(bub, 0, 3)[..., None] * 8
    W.save('suds', a)
    # translucent bubbles (alpha)
    im = Image.new('RGB', (256, 256), (255, 255, 255)); al = Image.new('L', (256, 256), 0); dA = ImageDraw.Draw(al)
    rr = random.Random(101)
    for _ in range(70):
        x, y, r = rr.randint(0, 255), rr.randint(0, 255), rr.randint(6, 30)
        for ox in (-256, 0, 256):
            for oy in (-256, 0, 256):
                dA.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=150)
                dA.ellipse((x + ox - r + 3, y + oy - r + 3, x + ox + r - 3, y + oy + r - 3), fill=70)
                dA.ellipse((x + ox - r * 0.5, y + oy - r * 0.6, x + ox - r * 0.1, y + oy - r * 0.2), fill=230)
    W.save('bubbles', np.asarray(im, np.float32), alpha=np.asarray(al.filter(ImageFilter.GaussianBlur(0.7)), np.float32))
    # shampoo bottles + labels
    W.save('bottle_teal', fill(n, (40, 170, 170), 3, 102) + N3(n, 40, 103, 8))
    W.save('bottle_pink', fill(n, (230, 110, 160), 3, 104) + N3(n, 40, 105, 8))
    W.save('bottle_white', fill(n, (236, 236, 230), 3, 106))
    for nm, title, sub, bg, fg in (('label_shampoo', 'SHAMPAD', 'extra bubbly', (250, 246, 230), (30, 130, 140)),
                                   ('label_bubble', 'BUBBLE', 'bath foam', (250, 236, 244), (200, 70, 120))):
        im = Image.new('RGB', (256, 384), bg); d = ImageDraw.Draw(im)
        d.rectangle((8, 8, 247, 375), outline=fg, width=6)
        text_c(d, (128, 150), title, 56, fg, maxw=230)
        text_c(d, (128, 220), sub, 26, fg, maxw=230)
        for k in range(5):
            d.ellipse((40 + k * 40 - 10, 290 - (k % 2) * 16, 40 + k * 40 + 10, 310 - (k % 2) * 16), outline=fg, width=3)
        W.save(nm, im)
    W.save('cup_plastic', fill(n, (120, 200, 120), 3, 107) + N3(n, 40, 108, 6))
    W.save('glass_shelf', fill(64, (190, 220, 220), 2, 109))
    W.save('wood_light', planks(n, (210, 176, 128), 4, 110, gap=(120, 90, 60)))
    # ---------------------------------------------------------------- misc
    W.save('jumppad', jumppad_tex())
    W.save('rubber', fill(n, (40, 40, 44), 4, 111))
    W.save('lamp', fill(64, (255, 250, 236), 1, 112))
    W.save('lamp_rim', fill(64, (220, 222, 226), 2, 113))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 114))
    # water + caustics
    w = noise(n, 6, 115) * 0.6 + noise(n, 2, 116) * 0.4
    W.save('water', np.zeros((n, n, 3), np.float32) + C((90, 170, 200)) + w[..., None] * C((18, 22, 22)))
    c = np.abs(noise(n, 4, 117)); c = np.clip(1.0 - c * 1.6, 0, 1) ** 3
    W.save('caustics', (c * 255)[..., None] * np.array([0.8, 1.0, 1.0]))
    W.save('drip', np.zeros((32, 32, 3), np.float32) + 255, alpha=_drop_alpha())


def _drop_alpha():
    al = Image.new('L', (32, 32), 0); d = ImageDraw.Draw(al)
    d.ellipse((10, 14, 22, 28), fill=170); d.polygon([(16, 2), (11, 18), (21, 18)], fill=170)
    return np.asarray(al.filter(ImageFilter.GaussianBlur(0.8)), np.float32)


def flag_tex(team):
    c = (200, 36, 36) if team == 'red' else (36, 90, 210)
    im = Image.new('RGB', (256, 128), c); d = ImageDraw.Draw(im)
    duck_icon(d, 128, 84, 40, body=(250, 230, 120))
    return soft(im, 0.5)


def crate_side():
    a = planks(256, (176, 132, 78), 4, 118, gap=(80, 56, 30))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, 251, 251), outline=(110, 76, 40), width=10)
    d.line((10, 10, 246, 246), fill=(110, 76, 40), width=12)
    text_c(d, (128, 200), 'AMMO', 40, (60, 40, 20))
    return soft(im, 0.4)


# ----------------------------------------------------------------------------------------------- shader
SH = "// padbath.shader - Battle in the Bathtub (generated by wop_tools/padbath/bath_textures.py)\n\n"
STEPS = {'deck': 'woodsteps', 'crate': 'woodsteps', 'crate_side': 'woodsteps', 'boat_deck': 'woodsteps', 'wood_light': 'woodsteps',
         'sponge': 'softsteps', 'sponge_green': 'softsteps', 'suds': 'softsteps', 'soap': 'softsteps', 'soap_top': 'softsteps',
         'curtain': 'softsteps', 'rope': 'softsteps', 'float_white': 'softsteps'}


def lm(name, steps=None, extra='', editor=None):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{editor or name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    return s


def shiny(name, amount=0.22, steps=None, extra=''):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {amount} {amount} {amount} )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return s


def make_shader(W, out):
    S = SH
    shinies = {'enamel': 0.12, 'enamel_floor': 0.08, 'chrome': 0.45, 'rail': 0.4, 'drain': 0.3, 'tile_wall': 0.08, 'tile_blue': 0.08,
               'tile_border': 0.08, 'bottle_teal': 0.15, 'bottle_pink': 0.15, 'bottle_white': 0.12, 'ring_red': 0.12, 'ring_orange': 0.12,
               'ring_yellow': 0.12, 'ring_green': 0.12, 'ring_blue': 0.12, 'ring_purple': 0.12, 'float_white': 0.1, 'cup_plastic': 0.12,
               'soap': 0.06, 'soap_top': 0.06, 'boat_yellow': 0.1, 'boat_green': 0.1, 'lamp_rim': 0.3}
    special = {'water', 'caustics', 'bubbles', 'lamp', 'nodraw_ns', 'flag_red', 'flag_blue', 'glass_shelf', 'drip', 'jumppad'}
    for nme in sorted(W.sizes):
        if nme in special: continue
        if nme in shinies:
            S += shiny(nme, shinies[nme], STEPS.get(nme))
        else:
            S += lm(nme, STEPS.get(nme))
    S += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 0.4 0.8 1\n')
    S += f'''textures/{NS}/water
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	tessSize 128
	deformVertexes wave 300 sin 0 2 0 0.3
	{{
		map textures/{NS}/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.55
		rgbGen identity
		tcMod turb 0 0.05 0 0.15
		tcMod scroll 0.01 0.007
	}}
	{{
		map textures/{NS}/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.14 0.17 0.17 )
		tcMod scale 0.6 0.6
		tcMod scroll -0.015 0.02
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

textures/{NS}/bubbles
{{
	qer_editorimage textures/{NS}/bubbles
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	deformVertexes wave 64 sin 0 3 0 0.4
	{{
		map textures/{NS}/bubbles.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.9 0.92 0.95 )
		tcMod scroll 0.02 0.01
	}}
}}

textures/{NS}/drip
{{
	qer_editorimage textures/{NS}/drip
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	deformVertexes autosprite2
	{{
		map textures/{NS}/drip.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.75 0.88 0.95 )
		tcMod scroll 0 -1.5
	}}
}}

textures/{NS}/lamp
{{
	qer_editorimage textures/{NS}/lamp
	surfaceparm nolightmap
	q3map_surfacelight 1400
	q3map_lightRGB 1 0.97 0.9
	q3map_lightSubdivide 64
	{{
		map textures/{NS}/lamp
		rgbGen identity
	}}
}}

textures/{NS}/glass_shelf
{{
	qer_editorimage textures/{NS}/glass_shelf
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nomarks
	{{
		map textures/{NS}/glass_shelf
		blendFunc GL_DST_COLOR GL_ONE
		rgbGen const ( 0.35 0.45 0.45 )
	}}
	{{
		map textures/{NS}/glass_shelf
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.14 0.14 )
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

'''
    for team in ('red', 'blue'):
        S += f'''textures/{NS}/flag_{team}
{{
	qer_editorimage textures/{NS}/flag_{team}
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull disable
	tessSize 32
	deformVertexes wave 96 sin 0 6 0 0.7
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/flag_{team}
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

'''
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
        '{\n\tmap      "%s"\n\tlongname "Battle in the Bathtub"\n\ttype     "ctl 1lc ffa team ft"\n}\n' % MAP)


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
