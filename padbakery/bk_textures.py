"""Procedural brush textures, the street backdrop, shader + arena for wop_padbakery (Sweet Padman's Bakery).
All art is original and generated here.

make_textures() writes textures/padbakery/*; make_shader() writes scripts/padbakery.shader (brush textures + every MD3
shader registered in bklib.REG); make_arena() writes scripts/wop_padbakery.arena."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bklib import *
import bklib

MAP = 'wop_padbakery'
LONGNAME = "Sweet Padman's Bakery"
SIZES = {}
ALPHA = set()
SUN = (270.0, 48.0)                      # yaw (270 = south: the sun shines in through the shop windows), elevation

PINK = (246, 170, 196); CREAM = (250, 240, 222); MINT = (176, 226, 206); CHOC = (96, 56, 36); BERRY = (214, 40, 70)
GOLD = (236, 186, 70); SKY = (150, 200, 240)


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


def grout_grid(x, y, nx, ny, w=0.012, brick=False):
    u = x * nx
    v = y * ny
    if brick: u = u + (np.floor(v) % 2) * 0.5
    fu, fv = u % 1, v % 1
    g = (np.minimum(fu, 1 - fu) < w * nx) | (np.minimum(fv, 1 - fv) < w * ny)
    return g, np.floor(u).astype(int), np.floor(v).astype(int)


# ------------------------------------------------------------------------------------------- room
def floor_tex(n=512, seed=3):
    """pink and cream checker tiles, a little worn, grey grout"""
    x, y = xy(n)
    g, iu, iv = grout_grid(x, y, 4, 4, 0.004)
    chk = ((iu + iv) % 2 == 0)
    c = np.where(chk[..., None], C(CREAM), C((240, 150, 176)))
    rng = np.random.default_rng(seed)
    tone = rng.uniform(-8, 8, (8, 8))
    c = c + tone[iu % 8, iv % 8][..., None] + N3(n, 1.2, seed, 4) + N3(n, 30, seed + 1, 6)
    c = c - np.clip(noise(n, 3, seed + 2) - 1.3, 0, 2)[..., None] * 18                 # scuffs
    return np.where(g[..., None], C((150, 140, 136)), c)


def subway(w=512, h=512, seed=5):
    """white subway tiles (brick bond)"""
    x, y = xy(w, h)
    g, iu, iv = grout_grid(x, y, 4, 8, 0.006, brick=True)
    c = np.zeros((h, w, 3), np.float32) + C((242, 244, 240)) + N3(w, 1, seed, 2, h)
    # bevel: lighter top-left, darker bottom-right inside each tile
    fu = (x * 4 + (np.floor(y * 8) % 2) * 0.5) % 1; fv = (y * 8) % 1
    c = c + (np.clip(0.12 - fv, 0, 1) * 120 - np.clip(fv - 0.88, 0, 1) * 160 - np.clip(fu - 0.94, 0, 1) * 120)[..., None]
    return np.where(g[..., None], C((176, 176, 170)), c)


def wall_paint(n=256, seed=7):
    """mint wall paint with tiny cream polka dots"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C(MINT) + N3(n, 2, seed, 3) + N3(n, 20, seed + 1, 4)
    for ox, oy in ((0.25, 0.25), (0.75, 0.75)):
        d = np.hypot(((x - ox + 0.5) % 1) - 0.5, ((y - oy + 0.5) % 1) - 0.5)
        c = np.where((d < 0.035)[..., None], C((250, 246, 230)), c)
    return c


def frieze(w=1024, h=128, seed=9):
    """the bakery frieze: little cupcakes, whisks, rolling pins and croissants on a pink band"""
    im = Image.new('RGB', (w, h), PINK); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 10), fill=(250, 246, 236)); d.rectangle((0, h - 10, w, h), fill=(250, 246, 236))
    d.rectangle((0, 10, w, 14), fill=CHOC); d.rectangle((0, h - 14, w, h - 10), fill=CHOC)
    k = 8
    for i in range(k):
        cx, cy = (i + 0.5) * w / k, h / 2
        t = i % 4
        if t == 0:      # cupcake
            d.polygon([(cx - 22, cy + 6), (cx + 22, cy + 6), (cx + 16, cy + 34), (cx - 16, cy + 34)], fill=(250, 220, 120))
            for j in range(-2, 3): d.line([(cx + j * 8, cy + 8), (cx + j * 6, cy + 32)], fill=(220, 180, 80), width=2)
            d.ellipse((cx - 26, cy - 16, cx + 26, cy + 12), fill=(255, 250, 252))
            d.ellipse((cx - 16, cy - 34, cx + 16, cy - 6), fill=(255, 250, 252))
            d.ellipse((cx - 6, cy - 44, cx + 6, cy - 32), fill=BERRY)
        elif t == 1:    # whisk
            for j in range(-2, 3):
                d.arc((cx - 14 + j * 3, cy - 40, cx + 14 - j * 3, cy + 6), 0, 360, fill=(200, 204, 214), width=2)
            d.rectangle((cx - 4, cy + 4, cx + 4, cy + 40), fill=CHOC)
        elif t == 2:    # rolling pin
            d.rounded_rectangle((cx - 40, cy - 10, cx + 40, cy + 10), 8, fill=(220, 180, 120))
            d.rectangle((cx - 54, cy - 4, cx - 40, cy + 4), fill=(180, 130, 80)); d.rectangle((cx + 40, cy - 4, cx + 54, cy + 4), fill=(180, 130, 80))
        else:           # croissant
            for j, s in enumerate((-1, 0, 1)):
                d.ellipse((cx - 16 + s * 22, cy - 14 + abs(s) * 6, cx + 16 + s * 22, cy + 14 + abs(s) * 4), fill=(222, 150, 70), outline=(160, 90, 40))
    return np.asarray(im, np.float32) + N3(w, 1, seed, 3, h)


def tin_ceiling(n=256, seed=11):
    """white pressed-tin ceiling squares"""
    x, y = xy(n)
    u, v = (x * 2) % 1, (y * 2) % 1
    r = np.maximum(np.abs(u - 0.5), np.abs(v - 0.5))
    rose = np.hypot(u - 0.5, v - 0.5)
    sh = np.where(r > 0.46, -30, 0) + np.where(np.abs(r - 0.36) < 0.02, 26, 0) + np.where(np.abs(rose - 0.16) < 0.03, 20, 0) - np.where(rose < 0.05, 14, 0)
    return np.zeros((n, n, 3), np.float32) + C((238, 236, 230)) + sh[..., None] + N3(n, 1, seed, 3)


def skirting(w=256, h=64, seed=13):
    c = fill(w, (120, 76, 48), 4, seed, h)
    x, y = xy(w, h)
    c = c + (np.sin(x * 60 + noise(w, 6, seed, h) * 2) * 8)[..., None]
    c = np.where((y < 0.12)[..., None], c * 1.25, c)
    return c


def wood_white(n=128, seed=15):
    c = fill(n, (246, 244, 238), 3, seed)
    x, y = xy(n)
    return c + (np.sin(y * 40 + noise(n, 8, seed) * 1.5) * 4)[..., None]


def street(w=1024, h=512, seed=17):
    """painted backdrop seen through the shop windows: the far side of a sunny street (shop fronts, awnings, trees)"""
    im = Image.new('RGB', (w, h), SKY); d = ImageDraw.Draw(im)
    for yy in range(h // 2):
        t = yy / (h / 2)
        d.line([(0, yy), (w, yy)], fill=(int(130 + 70 * t), int(190 + 40 * t), int(240 + 10 * t)))
    rng = np.random.default_rng(seed)
    cols = [(236, 200, 160), (200, 120, 110), (240, 226, 190), (150, 180, 200), (230, 170, 120), (190, 210, 170)]
    x = 0; k = 0
    while x < w:
        bw = int(rng.uniform(150, 230)); top = int(rng.uniform(60, 150))
        col = cols[k % len(cols)]
        d.rectangle((x, top, x + bw, h), fill=col)
        d.rectangle((x, top, x + bw, top + 10), fill=tuple(int(v * 0.8) for v in col))
        for wy in range(top + 30, int(h * 0.55), 56):
            for wx in range(x + 18, x + bw - 30, 46):
                d.rectangle((wx, wy, wx + 26, wy + 34), fill=(70, 90, 120)); d.rectangle((wx, wy, wx + 26, wy + 34), outline=(250, 250, 250), width=2)
        aw = [(230, 60, 70), (60, 140, 90), (40, 90, 170), (240, 160, 40)][k % 4]
        ay = int(h * 0.62)
        for s in range(0, bw, 20):
            d.polygon([(x + s, ay), (x + s + 20, ay), (x + s + 20, ay + 34), (x + s, ay + 40)], fill=aw if (s // 20) % 2 == 0 else (250, 250, 246))
        d.rectangle((x + 14, ay + 44, x + bw - 14, h - 40), fill=(60, 70, 80))
        d.rectangle((x + 20, ay + 50, x + bw - 20, h - 46), fill=(120, 150, 170))
        x += bw; k += 1
    d.rectangle((0, h - 40, w, h), fill=(170, 170, 166))
    for tx in range(60, w, 260):
        d.rectangle((tx - 5, int(h * 0.45), tx + 5, h - 30), fill=(90, 70, 50))
        for j in range(5):
            ox, oy = rng.uniform(-50, 50), rng.uniform(-40, 30)
            d.ellipse((tx + ox - 46, h * 0.38 + oy - 40, tx + ox + 46, h * 0.38 + oy + 40), fill=(70 + j * 10, 140 + j * 8, 70))
    return np.asarray(im, np.float32) + N3(w, 0.8, seed, 3, h)


def cool_floor(n=256, seed=27):
    """diamond-plate steel (cool room floor)"""
    x, y = xy(n)
    u, v = (x * 8) % 1, (y * 8) % 1
    k = (np.floor(x * 8) + np.floor(y * 8)) % 2
    d1 = np.abs((u - 0.5) * 0.6 + (v - 0.5)) < 0.08; d2 = np.abs((u - 0.5) * 0.6 - (v - 0.5)) < 0.08
    bump = np.where(k == 0, d1, d2) & (np.abs(u - 0.5) < 0.42)
    c = np.zeros((n, n, 3), np.float32) + C((176, 180, 186)) + N3(n, 1, seed, 6) + N3(n, 20, seed + 1, 8)
    return np.where(bump[..., None], c * 1.18, c)


def shop_floor(n=512, seed=29):
    """herringbone oak parquet (shop floor)"""
    x, y = xy(n)
    k = 8
    u, v = x * k, y * k
    a = np.floor(u + v); b = np.floor(u - v)
    par = (a % 2 == 0)
    w = np.where(par, (u - v) % 1, (u + v) % 1)
    rng = np.random.default_rng(seed)
    tone = rng.uniform(-16, 16, (64, 64))[(a.astype(int)) % 64, (b.astype(int)) % 64]
    c = np.zeros((n, n, 3), np.float32) + C((190, 136, 84)) + tone[..., None] + (np.sin(w * 30 + noise(n, 6, seed) * 2) * 6)[..., None]
    seam = np.minimum(((u + v) % 1), 1 - ((u + v) % 1)) < 0.03
    seam2 = np.minimum(((u - v) % 1), 1 - ((u - v) % 1)) < 0.03
    return np.where((seam | seam2)[..., None], c * 0.75, c)


def pavement(n=256, seed=19):
    x, y = xy(n)
    g, iu, iv = grout_grid(x, y, 2, 2, 0.008)
    c = np.zeros((n, n, 3), np.float32) + C((176, 174, 168)) + np.random.default_rng(seed).uniform(-10, 10, (4, 4))[iu % 4, iv % 4][..., None] + N3(n, 1, seed, 6)
    return np.where(g[..., None], C((120, 118, 112)), c)


def jumppad_tex(n=256):
    """a pink-glazed donut top with sprinkles (the launch pads)"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C((214, 150, 80))
    gl = rr + 0.02 * np.sin(a * 9) < 0.44
    c = np.where(gl[..., None], C((250, 130, 180)), c)
    rng = np.random.default_rng(23)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    cols = [(255, 255, 255), (90, 200, 255), (255, 220, 60), (120, 230, 120), (180, 90, 230)]
    for _ in range(90):
        r_ = rng.uniform(0.16, 0.42) * n; t = rng.uniform(0, 2 * math.pi); L_ = rng.uniform(5, 9); o = rng.uniform(0, math.pi)
        px, py = n / 2 + r_ * math.cos(t), n / 2 + r_ * math.sin(t)
        d.line([(px - L_ * math.cos(o), py - L_ * math.sin(o)), (px + L_ * math.cos(o), py + L_ * math.sin(o))], fill=cols[_ % 5], width=3)
    c = np.asarray(im, np.float32)
    c = np.where((rr < 0.12)[..., None], C((255, 250, 252)), c)
    return c + N3(n, 1, 35, 3)


def choc_wall(n=256, seed=21):
    """vault wall: a giant chocolate bar (raised squares)"""
    x, y = xy(n)
    u, v = (x * 2) % 1, (y * 2) % 1
    e = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    sh = np.where(e < 0.06, -26, np.where(e < 0.1, 26 * (e - 0.06) / 0.04 - 10, 12))
    return np.zeros((n, n, 3), np.float32) + C((104, 60, 36)) + sh[..., None] + N3(n, 1, seed, 3)


def gold_tile(n=256, seed=23):
    x, y = xy(n)
    g, iu, iv = grout_grid(x, y, 2, 2, 0.01)
    c = np.zeros((n, n, 3), np.float32) + C(GOLD) + N3(n, 6, seed, 14) + np.where(((iu + iv) % 2 == 0)[..., None], 10, -10)
    return np.where(g[..., None], C((150, 100, 40)), c)


def neon(w=64, h=64, col=(255, 90, 170)):
    x, y = xy(w, h)
    v = np.exp(-((y - 0.5) / 0.18) ** 2)
    return np.zeros((h, w, 3), np.float32) + (v[..., None] * C(col)) + (np.exp(-((y - 0.5) / 0.05) ** 2) * 120)[..., None]


SIGNS = {
    'sign_bakery': ("SWEET PADMAN'S BAKERY", 'FRESH EVERY MORNING - EST. 2026', 1024, 256, (250, 240, 222), (196, 40, 90)),
    'sign_vault': ('THE SUGAR VAULT', "YOU FOUND THE BAKER'S SECRET STASH", 1024, 192, (60, 30, 16), GOLD),
    'sign_cool': ('COOL ROOM', 'KEEP DOOR CLOSED - 4 C', 512, 192, (220, 236, 246), (30, 80, 150)),
}


def signboard(text, sub, w, h, bg, fg):
    a = text_img(text, int(w), int(h * (0.62 if sub else 1)), bg, fg, True, border=None)
    if sub:
        b = text_img(sub, int(w), h - a.shape[0], bg, tuple(v * 0.85 for v in fg), False)
        a = np.concatenate([a, b], 0)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=tuple(int(v) for v in fg), width=max(3, h // 32))
    return np.asarray(im, np.float32)


def menu_board(w=512, h=512, seed=25):
    """chalk menu board for the shop wall"""
    c = fill(w, (36, 44, 40), 4, seed, h) + N3(w, 0.7, seed + 1, 6, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(150, 100, 60), width=14)
    f1 = font(48, True); f2 = font(28, False)
    d.text((w / 2, 60), 'TODAY', font=f1, fill=(250, 240, 230), anchor='mm')
    rows = [('Cupcakes', '2.50'), ('Croissant', '3.00'), ('Eclair', '4.50'), ('Macarons x6', '8.00'), ('Donut', '2.00'),
            ('Lemon Tart', '5.50'), ('Fragfruit Pie', '6.00'), ('Padman Cake', '29.99')]
    for i, (a, b) in enumerate(rows):
        yy = 130 + i * 44
        col = [(255, 200, 220), (200, 240, 255), (255, 240, 170), (210, 255, 200)][i % 4]
        d.text((40, yy), a, font=f2, fill=col)
        d.text((w - 40, yy), b, font=f2, fill=(250, 250, 240), anchor='ra')
    return np.asarray(im, np.float32)


def make_textures():
    W('floor', floor_tex()); W('subway', subway()); W('wall_paint', wall_paint()); W('frieze', frieze())
    W('ceiling', tin_ceiling()); W('skirting', skirting()); W('wood_white', wood_white())
    W('street', street()); W('pavement', pavement()); W('cool_floor', cool_floor()); W('shop_floor', shop_floor())
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (120, 70, 40), 3, 59))
    W('choc_wall', choc_wall()); W('gold_tile', gold_tile())
    W('glass', fill(64, (170, 200, 210), 2, 61)); W('skylight', fill(64, (200, 220, 250), 2, 63))
    W('nodraw_ns', fill(64, (200, 60, 200), 2, 69)); W('clip_ed', fill(64, (200, 120, 40), 2, 71)); W('dark', fill(64, (20, 16, 14), 2, 73))
    W('neon_p', neon()); W('neon_y', neon(col=(255, 210, 90)))
    W('menu', menu_board())
    for nm, (t, sub, w, h, bg, fg) in SIGNS.items():
        W(nm, signboard(t, sub, w, h, bg, fg))


# ------------------------------------------------------------------------------------------- shader
STEPS = {'floor': None, 'pavement': None, 'gold_tile': None}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


def model_shaders():
    s = '// ---- MD3 / IQM models (bk_models.py)\n'
    for name, (im, kind, opt) in sorted(REG.items()):
        t = im if im.startswith('textures/') else f'{MD}/{im}'
        two = '\tcull none\n' if opt.get('two') else ''
        if kind in ('lm', 'lms'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle {opt.get("shade", 75)}\n{two}'
            if opt.get('steps'): s += f'\tsurfaceparm {opt["steps"]}\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            if opt.get('glowmap'):
                s += f'\t{{\n\t\tmap {MD}/{opt["glowmap"]}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n'
            s += '}\n\n'
        elif kind == 'vl':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'flow':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen identity\n'
                  f'\t\ttcMod scroll 0 {opt.get("speed", -1.2)}\n\t}}\n}}\n\n')
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n'
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.10 0.12 0.13")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.16 0.16 0.17 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'flicker':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave noise 0.85 0.15 {opt.get("ph", 0)} 6\n\t}}\n}}\n\n')
    return s


def make_shader():
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padbakery/bk_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'clip_ed', 'neon_p', 'neon_y', 'glass', 'street'}
    for nm in sorted(SIZES):
        if nm in special or nm.startswith('sign_') or nm == 'menu': continue
        S_ += lm(nm, STEPS.get(nm))
    for nm in sorted(SIZES):
        if nm.startswith('sign_') or nm == 'menu':
            S_ += lm(nm, extra='\tsurfaceparm nomarks\n')
    S_ += lm('street', extra='\tsurfaceparm nomarks\n\tq3map_lightmapSampleSize 64\n',
             stage=f'\t{{\n\t\tmap {TD}/street\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.45 0.45 0.45 )\n\t}}\n')
    pad_stage = f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.2 0.2 0 0.8\n\t\ttcMod rotate 30\n\t}}\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.6 0.8\n\tq3map_lightSubdivide 128\n', stage=pad_stage)
    for nm, col in (('neon_p', (255, 90, 170)), ('neon_y', (255, 210, 90))):
        S_ += (f'{TD}/{nm}\n{{\n\tqer_editorimage {TD}/{nm}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
               f'\tq3map_surfacelight 300\n\tq3map_lightRGB {col[0] / 255:.2f} {col[1] / 255:.2f} {col[2] / 255:.2f}\n\tq3map_lightSubdivide 64\n'
               f'\t{{\n\t\tmap {TD}/{nm}\n\t\trgbGen wave sin 0.9 0.1 0 0.5\n\t}}\n}}\n\n')
    S_ += f'''{TD}/glass
{{
	qer_editorimage {TD}/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm alphashadow
	cull none
	{{
		map {TD}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.10 0.12 0.13 )
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.12 0.13 )
		tcGen environment
	}}
}}

{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 1 0.96 0.88 220 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 40 3
	skyparms env/fort-pad512 - -
}}

{TD}/nodraw_ns
{{
	qer_editorimage {TD}/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	surfaceparm nolightmap
}}

'''
    S_ += model_shaders()
    S_ += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(out('scripts'), exist_ok=True)
    open(out('scripts', NS + '.shader'), 'w').write(S_)


def make_arena():
    open(out('scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))
