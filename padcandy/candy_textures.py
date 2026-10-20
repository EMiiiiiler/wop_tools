"""Procedural brush textures, shader + arena for wop_padcandy (Candy Garden). All art is original and generated here.
make_all(out) writes textures/padcandy/*, models/padcandy/* (candy_models), scripts/padcandy.shader and
scripts/wop_padcandy.arena (pk3dir layout). The sky is WoP's own env/fort-pad512 (sunny garden)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import candy_models as CM
from candy_models import _noise, _img, _C, _lerp, _xy, _hue, _emboss

MAP = 'wop_padcandy'
NS = 'padcandy'
LONGNAME = 'Candy Garden'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
if not os.path.exists(FONTS): FONTS = FONTB


def N3(n, blur, seed, amp, m=None): return _noise(n, blur, seed, m)[..., None] * amp
def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + _C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', NS); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}; self.alpha = set()

    def save(self, name, a, alpha=None):
        im = _img(a).convert('RGB') if isinstance(a, np.ndarray) else a
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga')); self.alpha.add(name)
        else:
            im.convert('RGB').save(os.path.join(self.dir, name + '.jpg'), quality=92)
        self.sizes[name] = im.size


def voronoi(n, cells, seed):
    """tileable Voronoi: (cell id, distance to edge) per pixel"""
    r = np.random.default_rng(seed)
    P = r.random((cells, 2))
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    best = np.full((n, n), 9.0); second = np.full((n, n), 9.0); idx = np.zeros((n, n), int)
    for i, (px, py) in enumerate(P):
        dx = np.abs(x - px); dx = np.minimum(dx, 1 - dx)
        dy = np.abs(y - py); dy = np.minimum(dy, 1 - dy)
        d = np.hypot(dx, dy)
        m = d < best
        second = np.where(m, best, np.minimum(second, d)); idx = np.where(m, i, idx); best = np.where(m, d, best)
    return idx, second - best


# ------------------------------------------------------------------------------------------- textures
def grass(n=512, seed=1):
    """lush emerald carpet grass with tiny flowers"""
    c = fill(n, (70, 168, 56), 10, seed)
    blades = _noise(n, 0.7, seed + 2)
    c += blades[..., None] * np.array([10, 18, 8])
    c += N3(n, 24, seed + 3, 10) * np.array([0.6, 1, 0.4])
    im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed + 4)
    for _ in range(140):
        x, y = r.integers(0, n, 2)
        col = [(255, 250, 240), (255, 230, 80), (250, 140, 190), (180, 140, 250)][r.integers(4)]
        s = r.integers(1, 3)
        d.ellipse((x - s, y - s, x + s, y + s), fill=col)
    return np.asarray(im, np.float32)


def path(n=512, seed=5):
    idx, edge = voronoi(n, 26, seed)
    r = np.random.default_rng(seed + 1)
    tone = r.uniform(-14, 14, idx.max() + 1)[idx]
    c = np.zeros((n, n, 3), np.float32) + _C((222, 214, 190)) + tone[..., None]
    c += N3(n, 1.5, seed + 2, 6) + N3(n, 6, seed + 3, 5)
    grout = np.clip(1 - edge * n / 5, 0, 1)[..., None]
    c = c * (1 - grout) + _C((120, 118, 104)) * grout
    return c


def rock(n=512, seed=7, base=(176, 166, 146)):
    """layered limestone: horizontal strata of varying thickness, cracks, weathering"""
    x, y = _xy(n)
    wob = _noise(n, 18, seed) * 0.012
    layer = (y + wob) * 7
    li = np.floor(layer); lf = layer - li
    r = np.random.default_rng(seed + 1)
    tone = r.uniform(-20, 16, 9)[(li.astype(int)) % 9]
    c = np.zeros((n, n, 3), np.float32) + _C(base) + tone[..., None]
    c += N3(n, 1.2, seed + 2, 7) + N3(n, 5, seed + 3, 9)
    seam = np.clip(1 - np.minimum(lf, 1 - lf) * n / 7 / 3, 0, 1)
    c *= (1 - 0.35 * seam)[..., None]
    crack = np.abs(_noise(n, 3, seed + 4)) < 0.035
    c[crack] *= 0.7
    return c


def rock_top(n=512, seed=9):
    c = rock(n, seed, (170, 162, 140))
    moss = np.clip(_noise(n, 10, seed + 5) * 0.8 + 0.2, 0, 1)[..., None]
    g = fill(n, (78, 150, 60), 10, seed + 6)
    return c * (1 - moss * 0.8) + g * moss * 0.8


def cave(n=256, seed=11):
    c = rock(n, seed, (120, 104, 112))
    c += np.clip(_noise(n, 6, seed + 3) - 1.0, 0, 1)[..., None] * np.array([60, 20, 50])
    return c


def choc_bank(n=256, seed=13):
    h = _noise(n, 5, seed) + _noise(n, 1.5, seed + 1) * 0.4
    c = _lerp(_C((60, 32, 16)), _C((112, 64, 32)), np.clip(0.5 + h * 0.3, 0, 1)[..., None])
    return c + np.clip(h - 1.1, 0, 1)[..., None] * 80


def choc_floor(n=256, seed=15):
    return fill(n, (52, 28, 14), 6, seed)


def wall_stone(w=512, h=512, seed=17):
    """sandstone ashlar: 128 x 64 blocks"""
    x, y = _xy(w, h)
    row = np.floor(y * 8); col = np.floor(x * 4 + 0.5 * (row % 2))
    r = np.random.default_rng(seed)
    tone = r.uniform(-14, 14, (9, 9))[(row.astype(int)) % 9, (col.astype(int)) % 9]
    c = np.zeros((h, w, 3), np.float32) + _C((214, 196, 158)) + tone[..., None] + N3(w, 1.2, seed + 1, 6, h) + N3(w, 7, seed + 2, 6, h)
    fy = (y * 8) % 1; fx = (x * 4 + 0.5 * (row % 2)) % 1
    jo = (np.minimum(fy, 1 - fy) < 0.04) | (np.minimum(fx, 1 - fx) < 0.02)
    c[jo] = c[jo] * 0.6 + _C((150, 136, 110)) * 0.4
    return c


def cornice(w=256, h=128, seed=19):
    x, y = _xy(w, h)
    prof = 0.75 + 0.25 * np.cos(y * math.pi * 6) * (y < 0.5) + 0.15 * np.sin(y * math.pi * 3)
    c = np.zeros((h, w, 3), np.float32) + _C((226, 212, 178)) * prof[..., None]
    dent = (y > 0.6) & (y < 0.8) & ((x * 16 % 1) < 0.5)
    c[dent] *= 0.75
    return c + N3(w, 1, seed, 4, h)


def window(n=256, panes=4, frame=10, mull=5, tint=(190, 220, 230), alpha_glass=50):
    """iron-framed factory glazing: RGBA (bars opaque, glass mostly clear)"""
    x, y = _xy(n)
    c = np.zeros((n, n, 3), np.float32) + _C(tint)
    c += (np.clip(1 - np.abs(x + y - 0.8) * 6, 0, 1) * 40)[..., None]
    fx = (x * panes) % 1; fy = (y * panes) % 1
    bar = (np.minimum(fx, 1 - fx) * n / panes < mull / 2) | (np.minimum(fy, 1 - fy) * n / panes < mull / 2)
    edge = (np.minimum(x, 1 - x) * n < frame / 2) | (np.minimum(y, 1 - y) * n < frame / 2)
    m = bar | edge
    c[m] = _C((38, 40, 44))
    a = np.full((n, n), float(alpha_glass)); a[m] = 255
    return c, a


def grate(n=128, seed=21):
    x, y = _xy(n)
    gx = np.abs(((x * 8) % 1) - 0.5) > 0.38; gy = np.abs(((y * 8) % 1) - 0.5) > 0.38
    c = np.where((gx | gy)[..., None], _C((70, 74, 78)), _C((26, 28, 30)))
    return c.astype(np.float32) + N3(n, 1, seed, 5)


def planks(w=256, h=256, seed=23):
    x, y = _xy(w, h)
    row = np.floor(y * 4)
    r = np.random.default_rng(seed)
    tone = r.uniform(-18, 18, 8)[(row.astype(int)) % 8]
    grain = np.sin(x * 2 * math.pi * 3 + _noise(w, 14, seed, h) * 2 + row * 1.3) * 10
    c = np.zeros((h, w, 3), np.float32) + _C((168, 116, 72)) + (tone + grain)[..., None] + N3(w, 1, seed + 1, 6, h)
    gap = np.minimum((y * 4) % 1, 1 - (y * 4) % 1) < 0.025
    c[gap] *= 0.45
    return c


def peppermint(n=256):
    x, y = _xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; th = np.arctan2(dy, dx)
    v = np.sin(th * 8 + r * 2.5)
    c = np.where((v > 0)[..., None], _C((226, 30, 40)), _C((252, 250, 248)))
    c = np.where((r > 0.9)[..., None], _C((246, 242, 238)), c)
    c = np.where((r < 0.14)[..., None], _C((226, 30, 40)), c)
    return c.astype(np.float32) + np.clip(1 - np.hypot(dx + 0.2, dy + 0.2) * 4, 0, 1)[..., None] * 50


def jumppad_tex(n=256):
    x, y = _xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; th = np.arctan2(dy, dx)
    c = _hue(th / (2 * math.pi) + r * 0.6, 0.75, 1.0)
    c = np.where((np.sin(th * 6 + r * 10) > 0.3)[..., None], _C((255, 250, 252)), c)
    c = np.where((r > 0.92)[..., None], _C((250, 90, 160)), c)
    return c.astype(np.float32)


def damask(w=256, h=256, seed=25):
    x, y = _xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + _C((94, 40, 110))
    u = (x * 2) % 1 - 0.5; v = (y * 2) % 1 - 0.5
    d = np.abs(u) + np.abs(v)
    motif = (np.abs(d - 0.32) < 0.03) | ((np.hypot(u, v) < 0.08)) | (np.abs(np.abs(u) - np.abs(v) * 0.5) < 0.015) & (d < 0.3)
    c[motif] = _C((214, 170, 70))
    return c + N3(w, 1, seed, 3, h)


def checker(n=256, seed=27):
    x, y = _xy(n)
    m = ((np.floor(x * 4) + np.floor(y * 4)) % 2) == 0
    c = np.where(m[..., None], _C((236, 232, 224)), _C((30, 28, 34)))
    vein = np.abs(_noise(n, 4, seed)) < 0.06
    c = c.astype(np.float32); c[vein] = c[vein] * 0.85 + 30
    return c


def carpet(n=256, seed=29):
    c = fill(n, (160, 30, 44), 8, seed)
    x, y = _xy(n)
    b = (np.abs(x - 0.06) < 0.02) | (np.abs(x - 0.94) < 0.02)
    c[b] = _C((230, 190, 80))
    return c


def tunnel(n=512, seed=31):
    x, y = _xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    return _hue(th / math.pi + r * 3 + 0.1 * np.sin(th * 7), 0.9, 1.0) * (0.75 + 0.25 * np.sin(r * 60))[..., None]


def fizzy_wall(n=256, seed=33):
    x, y = _xy(n)
    c = _lerp(_C((250, 200, 230)), _C((180, 230, 250)), (0.5 + 0.5 * np.sin(x * 2 * math.pi * 2))[..., None])
    im = _img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(60):
        px, py = r.integers(0, n, 2); s = int(r.integers(3, 14))
        d.ellipse((px - s, py - s, px + s, py + s), outline=(255, 255, 255), width=2)
    return np.asarray(im, np.float32)


def bubbles(w=128, h=512, seed=35):
    x, y = _xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + 255
    a = np.zeros((h, w), np.float32)
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(70):
        px, py = r.uniform(0, w), r.uniform(0, h); s = r.uniform(3, 12)
        d = np.hypot(xx - px, yy - py)
        ring = np.clip(1 - np.abs(d - s) / 2.0, 0, 1)
        a = np.maximum(a, ring * 230)
    return c, a


def signboard(text, w=512, h=128, bg=(110, 40, 120), fg=(255, 214, 90), font=FONTS, size=None):
    im = _img(np.zeros((h, w, 3)) + _C(bg) + N3(w, 1, 3, 4, h)).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=fg, width=4)
    lines = text.split('\n')
    sz = size or int(h * 0.5 / len(lines))
    f = ImageFont.truetype(font, sz)
    while max(d.textlength(t, font=f) for t in lines) > w - 40 and sz > 10:
        sz -= 2; f = ImageFont.truetype(font, sz)
    tot = len(lines) * sz * 1.2
    for i, t in enumerate(lines):
        tw = d.textlength(t, font=f)
        d.text(((w - tw) / 2, (h - tot) / 2 + i * sz * 1.2), t, font=f, fill=fg)
    return np.asarray(im, np.float32)


def bulb(n=32, col=(255, 210, 120)):
    x, y = _xy(n)
    m = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1)[..., None]
    return _C(col) * (0.5 + 0.5 * m) + 255 * m ** 3 * 0.5


def make_textures(W):
    W.save('grass', grass()); W.save('path', path()); W.save('rock', rock()); W.save('rock_top', rock_top())
    W.save('cave', cave()); W.save('choc_bank', choc_bank()); W.save('choc_floor', choc_floor())
    W.save('chocolate', CM.tex_choc_surface(256, 51)); W.save('choc_ed', fill(64, (110, 60, 30), 3, 53))
    W.save('wall_stone', wall_stone()); W.save('cornice', cornice()); W.save('stone_dark', fill(128, (120, 108, 88), 6, 55))
    c, a = window(); W.save('window', c, a)
    c, a = window(256, 2, 12, 8, (200, 226, 236), 40); W.save('roofglass', c, a)
    W.save('grate', grate()); W.save('iron', fill(64, (44, 46, 50), 4, 57)); W.save('planks', planks())
    W.save('peppermint', peppermint()); W.save('candy_white_b', fill(64, (246, 242, 236), 3, 77)); W.save('path_ns', path(512, 79)); W.save('jumppad', jumppad_tex()); W.save('rubber', fill(64, (240, 110, 170), 3, 59))
    W.save('damask', damask()); W.save('checker', checker()); W.save('carpet', carpet()); W.save('ceiling', fill(128, (240, 230, 214), 4, 61))
    W.save('gold', fill(64, (220, 176, 70), 8, 63)); W.save('tunnel', tunnel()); W.save('fizzy_wall', fizzy_wall())
    W.save('fizzy_floor', checker(256, 65) * np.array([1.0, 0.85, 0.95]) + np.array([20, 0, 30]))
    c, a = bubbles(); W.save('bubbles', c, a)
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 73)); W.save('skylight', fill(64, (255, 250, 230), 2, 75))
    W.save('sign_garden', signboard('THE CANDY GARDEN', 1024, 128))
    W.save('sign_fizzy', signboard('FIZZY LIFTING ROOM\nmind the fan', 512, 256, (240, 120, 180), (255, 255, 255)))
    W.save('sign_tunnel', signboard('TUNNEL OF WONDER', 512, 128, (40, 20, 60), (120, 255, 200)))
    W.save('sign_river', signboard('PLEASE DO NOT DRINK\nFROM THE RIVER', 512, 256, (250, 240, 220), (110, 50, 20)))
    W.save('sign_touch', signboard('EVERYTHING HERE IS EATABLE\n(EVEN THE MUSHROOMS)', 512, 256, (60, 20, 70), (255, 214, 90)))
    W.save('sign_pump', signboard('CAUTION: SUCTION PIPE', 512, 128, (230, 190, 40), (30, 30, 30), FONTB))
    W.save('ticket', CM.tex_ticket())
    for nm, c in (('bulb_w', (255, 230, 170)), ('bulb_p', (255, 140, 210)), ('bulb_c', (140, 255, 230))):
        W.save(nm, bulb(col=c))


# ------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padcandy/candy_textures.py)\n\n"
STEPS = {'grass': 'softsteps', 'rock_top': 'softsteps', 'choc_bank': 'softsteps', 'choc_floor': 'softsteps', 'planks': 'woodsteps',
         'grate': 'latticesteps', 'carpet': 'carpetsteps', 'peppermint': None, 'fizzy_floor': None}


def lm(name, steps=None, extra='', tex=None):
    t = tex or f'textures/{NS}/{name}'
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + '}\n\n'


def make_shader(W, out, model_shaders):
    S = SH
    special = {'path_ns', 'window', 'roofglass', 'chocolate', 'choc_ed', 'nodraw_ns', 'skylight', 'jumppad', 'tunnel', 'bubbles', 'sign_garden',
               'sign_fizzy', 'sign_tunnel'} | {n for n in W.sizes if n.startswith('bulb_')}
    for nm in sorted(W.sizes):
        if nm in special: continue
        S += lm(nm, STEPS.get(nm))
    S += lm('path_ns', extra='\tsurfaceparm nonsolid\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tq3map_nonplanar\n')
    S += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.6 0.9\n')[:-3] + (
        f'\t{{\n\t\tmap textures/{NS}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.2 0.2 0 0.7\n'
        '\t\ttcMod rotate 60\n\t}\n}\n\n')
    for nm, rgb in (('sign_garden', '1 0.85 0.5'), ('sign_fizzy', '1 0.7 0.9'), ('sign_tunnel', '0.5 1 0.8')):
        S += lm(nm, extra=f'\tq3map_surfacelight 40\n\tq3map_lightRGB {rgb}\n')[:-3] + (
            f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.15 0.1 0 0.3\n\t}}\n}}\n\n')
    for nm in sorted(n for n in W.sizes if n.startswith('bulb_')):
        rgb = {'bulb_w': '1 0.9 0.7', 'bulb_p': '1 0.55 0.85', 'bulb_c': '0.55 1 0.9'}[nm]
        S += (f'textures/{NS}/{nm}\n{{\n\tqer_editorimage textures/{NS}/{nm}\n\tq3map_surfacelight 600\n\tq3map_lightRGB {rgb}\n'
              f'\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
              f'\t{{\n\t\tmap textures/{NS}/{nm}\n\t\trgbGen identity\n\t}}\n}}\n\n')
    S += f'''textures/{NS}/sky
{{
	qer_editorimage textures/{NS}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/{NS}/skylight
	q3map_sun 1 0.94 0.82 300 215 62
	q3map_skylight 110 3
	skyparms env/fort-pad512 - -
}}

textures/{NS}/window
{{
	qer_editorimage textures/{NS}/window
	qer_trans 0.6
	surfaceparm trans
	surfaceparm alphashadow
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{{
		map textures/{NS}/window.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
	}}
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.08 0.09 0.1 )
		tcGen environment
	}}
}}

textures/{NS}/roofglass
{{
	qer_editorimage textures/{NS}/roofglass
	qer_trans 0.6
	surfaceparm trans
	surfaceparm alphashadow
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	{{
		map textures/{NS}/roofglass.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
	}}
}}

textures/{NS}/chocolate
{{
	qer_editorimage textures/{NS}/choc_ed
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	deformVertexes wave 160 sin 0 2 0 0.25
	cull none
	{{
		map textures/{NS}/chocolate
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.9
		rgbGen identity
		tcMod scale 0.5 0.5
		tcMod turb 0 0.04 0 0.08
		tcMod scroll 0.01 0.02
	}}
	{{
		map models/{NS}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.16 0.12 0.1 )
		tcGen environment
	}}
}}

textures/{NS}/choc_nodraw
{{
	qer_editorimage textures/{NS}/choc_ed
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

textures/{NS}/tunnel
{{
	qer_editorimage textures/{NS}/tunnel
	surfaceparm nolightmap
	q3map_surfacelight 80
	q3map_lightRGB 0.9 0.6 1
	{{
		map textures/{NS}/tunnel
		rgbGen identity
		tcMod rotate 25
		tcMod turb 0 0.05 0 0.1
	}}
}}

textures/{NS}/bubbles
{{
	qer_editorimage textures/{NS}/bubbles
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	deformVertexes autosprite2
	cull none
	{{
		map textures/{NS}/bubbles.tga
		blendFunc GL_SRC_ALPHA GL_ONE
		rgbGen identity
		tcMod scroll 0 0.6
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
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))


def make_all(out, extra_models=None):
    W = TexWriter(out)
    make_textures(W)
    CM.make(out)
    if extra_models: extra_models()
    make_shader(W, out, CM.shaders())
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
