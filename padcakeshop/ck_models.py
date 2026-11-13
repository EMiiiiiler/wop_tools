"""Padman's Little Cake Shop (wop_padcakeshop) - textures (woplib.texlib registry) and custom MD3s.
All art is original and procedural.

Padman scale ~8u per cm (catalog models at 1.0; a cupcake is about Padman's height). Every model is built in model
space with z = 0 on the surface it stands on; COLL[name] holds the weapclip collision (boxes / cylinders in model
space) that build_padcakeshop.py places with it, so what bots path over is what players see.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_z

TX = None
M_ = {}
COLL = {}
C = ML.C

# ------------------------------------------------------------------------------------------------- sizes shared with the map
UNIT_W, UNIT_D = 1600, 560                      # display unit (x, y)
UNIT_Z = (96, 400, 704, 1008)                   # walkable shelf tops
SHELF_T = 24
COUNTER_L, COUNTER_D, COUNTER_H = 1600, 400, 720
ESP_H = 440                                     # espresso machine top deck above the counter
RACK_L, RACK_D = 1400, 320
RACK_Z = (400, 800, 1200)
TIER_Z = (30, 220, 400)                         # plate tops of the tiered stand
TIER_R = (230, 165, 105)
TABLE_Z, SEAT_Z = 600, 360
JAR_R, JAR_H, JAR_FILL = 120, 280, 90
AWN_L, AWN_D = 2440, 240
DOOR_W, DOOR_H = 720, 1300


# ================================================================================================= helpers
def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n, w x h, never mirrored (u to the viewer's right, v down the image)"""
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    M.poly([c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh], n, [(0, 0), (1, 0), (1, 1), (0, 1)])


def coll(name, boxes=(), cyls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls))


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def cut_z(b, cutters):
    """collision box b minus the height ranges where boxes of `cutters` cross it (posts through shelves), so the
    weapclip pieces never overlap"""
    (x0, y0, z0), (x1, y1, z1) = b
    cuts = sorted((max(z0, c[0][2]), min(z1, c[1][2])) for c in cutters
                  if c[0][0] < x1 and c[1][0] > x0 and c[0][1] < y1 and c[1][1] > y0 and c[0][2] < z1 and c[1][2] > z0)
    out, z = [], z0
    for a, e in cuts:
        if a > z: out.append(((x0, y0, z), (x1, y1, a)))
        z = max(z, e)
    if z < z1: out.append(((x0, y0, z), (x1, y1, z1)))
    return out


def boxes(X, mat, bl, r=3, k=1, tile=128):
    for a, b in bl: rbox(X.mesh(M_[mat]), a, b, r=r, k=k, tile=tile)


def draw(arr):
    im = Image.fromarray(np.uint8(np.clip(arr, 0, 255)))
    return im, ImageDraw.Draw(im)


# ================================================================================================= brush textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('floor', TL.checker((250, 244, 232), (186, 224, 210), 4, grout=(214, 208, 198), grout_w=0.015), scale=1.0)
    a('wall', TL.solid((222, 238, 230), 3, 11, 256), scale=1.0)
    a('beadboard', beadboard(), scale=1.0)
    a('rail', TL.solid((250, 248, 242), 2, 12, 64))
    a('ceiling', TL.solid((250, 248, 244), 3, 13, 256), scale=1.0)
    a('pine', TL.planks((226, 194, 142), n_planks=4, gap=(170, 136, 92), grain=7), steps='woodsteps', scale=0.75)
    a('white', TL.solid((246, 244, 238), 2, 14, 64))
    a('sugar', sugar_tex(), scale=0.5)
    a('pavement', TL.tiles((200, 196, 188), (150, 146, 140), cols=2, rows=4, offset=0.5, grout_w=0.02), scale=1.0)
    a('facade', TL.planks((244, 196, 204), n_planks=8, gap=(206, 150, 162), grain=2, stagger=False), scale=1.0)
    a('kerb', TL.solid((170, 168, 164), 5, 15, 128))
    a('road', TL.solid((92, 94, 100), 8, 19, 256) + TL.N3(256, 1, 20, 6), scale=1.0)
    a('doormat', doormat(), 'sign', check_tile=False, steps='carpetsteps')
    a('cookie', cookie_tex(), scale=1.0)
    a('dough', TL.solid((226, 190, 130), 6, 16, 256) + TL.N3(256, 3, 17, 5), scale=1.0)
    a('menu', menu_board(), 'sign', check_tile=False)
    a('shopsign', shop_sign(), 'sign', check_tile=False)
    for i, art in enumerate((art_cupcake, art_teapot, art_fresh)):
        a(f'frame{i}', art(), 'sign', check_tile=False)
    a('sky', TL.solid((150, 190, 240), 2, 18, 64), 'raw', check_tile=False, shader=sky_stanza(K.ns))
    TX.kit_defaults(pad_rgb=(255, 150, 190), rubber=(250, 246, 240), pad=donut_pad())
    materials()
    return TX


def sky_stanza(ns):
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 1 0.96 0.88 120 250 55\n\tq3map_skylight 70 3\n\tskyparms env/fort-pad512 - -\n}}\n\n')


def beadboard(n=256):
    """white tongue-and-groove boarding (vertical boards with soft grey grooves)"""
    x, y = TL.xy(n)
    g = (x * 8) % 1
    c = TL.fill(n, (248, 246, 240), 2, 21)
    c = c - (np.clip(1 - np.abs(g - 0.5) * 2, 0, 1) ** 8 * 0 + (g < 0.06) * 46 + ((g > 0.06) & (g < 0.12)) * 14)[..., None]
    return c


def sugar_tex(n=128):
    rng = np.random.default_rng(22)
    c = TL.fill(n, (250, 250, 252), 3, 23)
    return c - (rng.random((n, n)) > 0.86)[..., None] * 26


def doormat(w=512, h=256):
    c = TL.fabric((150, 110, 76), weave=96, n=512)[:h, :w]
    im, d = draw(c)
    d.rectangle((14, 14, w - 15, h - 15), outline=(90, 60, 40), width=8)
    f = ML.font(90); tw = d.textlength('HELLO!', font=f)
    d.text(((w - tw) / 2, 70), 'HELLO!', font=f, fill=(70, 44, 30))
    return np.asarray(im, np.float32)


def cookie_tex(n=256):
    """cookie dough with chocolate chips (the secret jar's floor)"""
    c = TL.fill(n, (214, 168, 104), 8, 24) + TL.N3(n, 5, 25, 8)
    idx, d = ML.voronoi(n, 60, 26)
    chip = (d > 0.045) & ((idx % 3) == 0)
    return np.where(chip[..., None], C((84, 50, 34)), c)


def chalk_board(w, h, lines, title=None, col=(46, 58, 54)):
    c = np.zeros((h, w, 3), np.float32) + C(col) + TL.N3(w, 6, 27, 7, h) + TL.N3(w, 1, 28, 3, h)
    im, d = draw(c)
    y = int(h * 0.05)
    if title:
        f = ML.font(int(h * 0.13)); tw = d.textlength(title, font=f)
        d.text(((w - tw) / 2, y), title, font=f, fill=(250, 240, 220)); y += int(h * 0.17)
        d.line((w * 0.15, y, w * 0.85, y), fill=(244, 182, 196), width=max(3, h // 120)); y += int(h * 0.04)
    cols = [(250, 250, 244), (244, 182, 196), (186, 230, 214), (250, 228, 160)]
    fs = int((h - y) * 0.8 / max(1, len(lines)))
    for i, l in enumerate(lines):
        f = ML.font(min(fs, int(h * 0.1)), serif=False); tw = d.textlength(l, font=f)
        while tw > w * 0.88:
            f = ML.font(f.size - 2, serif=False); tw = d.textlength(l, font=f)
        d.text(((w - tw) / 2, y), l, font=f, fill=cols[i % 4]); y += int(fs * 1.2)
    d.rectangle((4, 4, w - 5, h - 5), outline=(222, 190, 140), width=max(6, w // 40))
    return np.asarray(im, np.float32)


def menu_board():
    return chalk_board(512, 512, ['Cupcake ......... 2.50', 'Cake pop ........ 1.50', 'Strawberry slice . 3.00', 'Matcha heart ..... 3.20',
                                  'Espresso ......... 1.80', 'Flat white ....... 2.90', 'Hot chocolate .... 2.60'], 'TODAY')


def shop_sign(w=1024, h=128):
    c = np.zeros((h, w, 3), np.float32) + C((252, 248, 240)) + TL.N3(w, 2, 29, 3, h)
    im, d = draw(c)
    f = ML.font(70); t = "PADMAN'S  LITTLE  CAKE  SHOP"; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 22), t, font=f, fill=(196, 96, 124))
    d.rectangle((3, 3, w - 4, h - 4), outline=(186, 224, 210), width=6)
    return np.asarray(im, np.float32)


def _framed(draw_fn, bg, w=256, h=320):
    c = np.zeros((h, w, 3), np.float32) + C(bg) + TL.N3(w, 2, 30, 3, h)
    im, d = draw(c)
    draw_fn(d, w, h)
    d.rectangle((0, 0, w - 1, h - 1), outline=(226, 194, 142), width=14)
    d.rectangle((14, 14, w - 15, h - 15), outline=(255, 255, 255), width=10)
    return np.asarray(im, np.float32)


def art_cupcake():
    def f(d, w, h):
        d.polygon([(80, 190), (176, 190), (160, 270), (96, 270)], fill=(244, 182, 196))
        for k in range(5): d.line((88 + k * 20, 192, 98 + k * 15, 268), fill=(250, 250, 250), width=3)
        d.ellipse((66, 130, 190, 204), fill=(250, 246, 236)); d.ellipse((84, 96, 172, 168), fill=(250, 246, 236))
        d.ellipse((104, 72, 152, 124), fill=(250, 246, 236)); d.ellipse((116, 52, 140, 78), fill=(220, 50, 60))
    return _framed(f, (236, 246, 240))


def art_teapot():
    def f(d, w, h):
        d.ellipse((60, 130, 196, 250), fill=(186, 224, 210)); d.rectangle((108, 116, 148, 136), fill=(186, 224, 210))
        d.ellipse((118, 98, 138, 118), fill=(244, 182, 196))
        d.arc((170, 150, 236, 226), 270, 90, fill=(186, 224, 210), width=12)
        d.polygon([(70, 190), (26, 150), (40, 144), (84, 170)], fill=(186, 224, 210))
        for (x, y) in ((100, 170), (140, 200), (120, 220), (160, 168)): d.ellipse((x, y, x + 10, y + 10), fill=(250, 250, 250))
    return _framed(f, (252, 240, 236))


def art_fresh():
    def f(d, w, h):
        for i, (t, col, sz) in enumerate((('FRESH', (196, 96, 124), 52), ('BAKED', (90, 150, 130), 52), ('every day', (120, 100, 90), 30))):
            ft = ML.font(sz); tw = d.textlength(t, font=ft)
            d.text(((w - tw) / 2, 70 + i * 66), t, font=ft, fill=col)
    return _framed(f, (252, 248, 236))


def donut_pad(n=256):
    """jump pad top: a pink glazed donut with sprinkles"""
    x, y = TL.xy(n); dx, dy = x - 0.5, y - 0.5; rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C((250, 246, 240))
    dough = (rr > 0.13) & (rr < 0.47)
    glaze = (rr > 0.17 + 0.012 * np.sin(a * 7)) & (rr < 0.43 + 0.014 * np.sin(a * 9 + 1))
    c = np.where(dough[..., None], C((222, 170, 100)), c)
    c = np.where(glaze[..., None], C((250, 140, 180)), c)
    rng = np.random.default_rng(31)
    im, d = draw(c)
    cols = [(255, 255, 255), (120, 220, 200), (255, 230, 90), (120, 170, 255)]
    for _ in range(70):
        t, r = rng.random() * 2 * math.pi, 0.2 + rng.random() * 0.2
        px, py = (0.5 + r * math.cos(t)) * n, (0.5 + r * math.sin(t)) * n; q = rng.random() * math.pi
        d.line((px - 5 * math.cos(q), py - 5 * math.sin(q), px + 5 * math.cos(q), py + 5 * math.sin(q)), fill=cols[_ % 4], width=3)
    return np.asarray(im, np.float32)


# ================================================================================================= model materials
def materials():
    m('pine', TL.planks((226, 194, 142), n_planks=4, gap=(176, 142, 96), grain=7), shade=20)
    m('pinev', TL.planks((226, 194, 142), n_planks=4, gap=(176, 142, 96), grain=7, vertical=True), shade=20, tag='v')
    m('white', TL.solid((246, 244, 238), 2, 41), shade=40)
    m('porcelain', TL.solid((250, 250, 248), 1, 42), 'lms', v=0.12, shade=60)
    m('bead', beadboard(), shade=20)
    m('mint', TL.solid((178, 222, 206), 2, 43), shade=50)
    m('mintgloss', TL.solid((178, 222, 206), 2, 43), 'lms', v=0.14, shade=60, tag='g')
    m('pink', TL.solid((244, 182, 196), 2, 44), shade=60)
    m('pinkgloss', TL.solid((240, 170, 188), 2, 44), 'lms', v=0.14, shade=50, tag='g')
    m('cream', TL.solid((252, 242, 220), 2, 45), shade=70)
    m('creamgloss', TL.solid((246, 236, 212), 2, 45), 'lms', v=0.12, shade=40, tag='g')
    m('choc', TL.solid((96, 58, 40), 4, 46), shade=70)
    m('chocfrost', TL.solid((122, 76, 52), 4, 47), shade=70)
    m('berry', berry_tex(), shade=70)
    m('matcha', TL.solid((172, 204, 124), 4, 48), shade=60)
    m('sponge', layer_tex(), shade=20)
    m('caramel', TL.solid((212, 150, 76), 5, 49), shade=60)
    m('bluefrost', TL.solid((150, 200, 236), 3, 50), shade=70)
    m('liner_pink', TL.stripes((246, 190, 204), (255, 255, 255), 24, n=128), shade=40)
    m('liner_brown', TL.stripes((120, 78, 54), (96, 60, 42), 24, n=128), shade=40)
    m('liner_mint', TL.stripes((170, 220, 204), (250, 250, 250), 24, n=128), shade=40)
    m('gold', TL.metal((226, 186, 90), brushed=False), 'lms', v=0.3, shade=60)
    m('brass', TL.metal((206, 166, 80), brushed=False), 'lms', v=0.35, shade=60, tag='b')
    m('chrome', TL.metal((200, 204, 210)), 'lms', v=0.4, shade=60)
    m('black', TL.solid((34, 32, 34), 2, 51), shade=50)
    m('glass', TL.solid((190, 215, 225), 2, 52, 64), 'glass', c='0.07 0.09 0.10')
    _a = lace_tex(); m('lace', _a[0], 'alpha', alpha=_a[1], two=True)
    m('tag', tag_tex(), shade=10)
    m('crust', crust_tex(), shade=70)
    m('baguette', baguette_tex(), shade=70)
    m('wicker', wicker_tex(), shade=40)
    m('waffle', waffle_tex(), shade=50)
    m('latte', latte_tex(), shade=10)
    m('chalk', chalk_board(256, 384, ['CUPCAKES', 'COFFEE', 'CAKE POPS', '-> inside'], 'OPEN'), shade=10)
    m('stripe', TL.stripes((244, 150, 176), (255, 252, 246), 16, n=256), shade=30)
    _a = valance_tex(); m('valance', _a[0], 'alpha', alpha=_a[1], two=True)
    _a = bunting_tex(); m('bunting', _a[0], 'alpha', alpha=_a[1], two=True)
    m('soil', TL.solid((92, 66, 48), 8, 53), shade=60)
    m('sack', sack_tex(), shade=80)
    m('sack_plain', TL.fabric((230, 220, 196), weave=96, n=256), shade=80)
    m('coffee_sack', coffee_sack_tex(), shade=80)
    m('burlap', TL.fabric((176, 140, 96), weave=64, n=256), shade=80)
    m('beans', beans_tex(), shade=60)
    m('sugar_paper', TL.solid((238, 240, 244), 3, 73, 128), shade=60)
    m('sugar_label', sugar_label_tex(), shade=60)
    m('cakebox', cakebox_tex(), shade=10)
    m('ribbon', TL.solid((120, 170, 230), 2, 54, 64), shade=60)
    m('teddy', TL.fabric((206, 160, 104), weave=80, n=128), shade=80)
    m('straw', TL.stripes((226, 50, 60), (255, 255, 255), 6, vertical=False, n=64), shade=60)
    m('pearl', sugar_tex(), shade=60)
    m('grid', grid_tex(), 'lms', v=0.25, shade=20)
    m('gauge', gauge_tex(), shade=10)
    m('badge', TL.label('LA PADMANA', 256, 64, (206, 166, 80), (60, 40, 20), serif=True, border=(60, 40, 20)), shade=10)
    m('keys', keys_tex(), shade=10)
    m('glow', TL.solid((255, 240, 200), 1, 55, 32), 'glow')
    m('coffee', TL.solid((70, 40, 24), 3, 56, 64), shade=40)
    m('candy_a', candy_tex((240, 120, 150), (250, 220, 90)), shade=30)
    m('candy_b', candy_tex((120, 200, 180), (250, 250, 250)), shade=30)
    m('candy_c', candy_tex((250, 170, 80), (150, 110, 220)), shade=30)
    m('cookie', cookie_tex(), shade=40)
    for word in ('FLOUR', 'SUGAR', 'TEA', 'COOKIES'):
        m('tin_' + word.lower(), TL.label(word, 256, 256, (186, 224, 210), (70, 100, 92), band=(0.3, 0.7), band_bg=(250, 248, 240), serif=True),
          'lms', v=0.1, shade=60, lathe=True)
    m('open', TL.label('OPEN', 256, 128, (250, 248, 240), (196, 96, 124), serif=True, border=(196, 96, 124)), shade=10)
    m('iron', TL.metal((60, 62, 66), brushed=False), shade=50)
    m('leaf', TL.solid((110, 160, 90), 8, 57), shade=80)
    m('rose', TL.solid((240, 150, 170), 5, 58), shade=80)


def berry_tex(n=128):
    c = TL.fill(n, (220, 50, 60), 5, 61)
    return TL.dots((220, 50, 60), (250, 220, 120), 8, 0.1, n=n) * 0.5 + c * 0.5


def layer_tex(n=128):
    """sponge / cream layers (side of a slice), rows run across the image"""
    x, y = TL.xy(n)
    band = np.floor(y * 6) % 2
    c = np.where(band[..., None] > 0, C((250, 240, 220)), C((236, 196, 120)))
    return c + TL.N3(n, 1, 62, 6)


def lace_tex(w=256, h=128):
    """scalloped lace edging: (rgb, alpha)"""
    x, y = TL.xy(w, h)
    sc = np.abs(np.sin(x * math.pi * 8))
    edge = y < 0.55 + 0.4 * sc
    holes = (np.hypot(((x * 16) % 1) - 0.5, ((y * 5) % 1) - 0.5) < 0.2) & (y > 0.2)
    a = (edge & ~holes) * 255.0
    return np.zeros((h, w, 3), np.float32) + C((255, 255, 252)), a


def valance_tex(w=256, h=64):
    x, y = TL.xy(w, h)
    c = TL.stripes((244, 150, 176), (255, 252, 246), 16, n=256)[:h, :w]
    a = (y < 0.45 + 0.5 * np.abs(np.sin(x * math.pi * 8))) * 255.0
    return c, a


def bunting_tex(w=256, h=64):
    x, y = TL.xy(w, h)
    k = np.floor(x * 4).astype(int)
    fx = (x * 4) % 1
    cols = np.array([(244, 182, 196), (186, 224, 210), (250, 228, 160), (170, 200, 240)], np.float32)
    c = cols[k % 4]
    a = ((np.abs(fx - 0.5) < 0.46 * (1 - y)) | (y < 0.06)) * 255.0
    return c, a


def tag_tex(w=128, h=64):
    im = Image.new('RGB', (w, h), (252, 252, 248)); d = ImageDraw.Draw(im)
    d.text((16, 6), '2.50', font=ML.font(44, serif=False), fill=(70, 70, 76))
    d.rectangle((0, 0, w - 1, h - 1), outline=(190, 190, 190), width=2)
    return np.asarray(im, np.float32)


def crust_tex(n=256):
    c = TL.fill(n, (206, 144, 72), 10, 63) + TL.N3(n, 6, 64, 14)
    x, y = TL.xy(n)
    flour = np.clip(ML.noise(n, 4, 65) * 0.5 + 0.2, 0, 1)[..., None]
    c = c * (1 - flour * 0.5) + C((246, 236, 214)) * flour * 0.5
    score = (np.abs(((x + y) * 3) % 1 - 0.5) < 0.03)
    return np.where(score[..., None], C((240, 214, 160)), c)


def baguette_tex(n=128):
    x, y = TL.xy(n)
    c = TL.fill(n, (214, 150, 76), 8, 66)
    score = np.abs(((y * 5 + x * 1.0) % 1) - 0.5) < 0.09
    return np.where(score[..., None], C((244, 216, 160)), c)


def wicker_tex(n=128):
    x, y = TL.xy(n)
    w = np.sin(x * math.pi * 16) * np.sign(np.sin(y * math.pi * 16))
    return TL.fill(n, (196, 150, 96), 4, 67) + w[..., None] * 22


def waffle_tex(n=128):
    x, y = TL.xy(n)
    g = (np.abs(((x + y) * 8) % 1 - 0.5) < 0.1) | (np.abs(((x - y) * 8) % 1 - 0.5) < 0.1)
    return np.where(g[..., None], C((176, 120, 60)), C((226, 176, 104))) + TL.N3(n, 1, 68, 5)


def latte_tex(n=128):
    """a cup of coffee seen from above with a latte-art heart"""
    x, y = TL.xy(n); dx, dy = x - 0.5, y - 0.5
    c = np.zeros((n, n, 3), np.float32) + C((150, 96, 58))
    heart = ((dx * 3) ** 2 + (dy * 3 - np.sqrt(np.abs(dx * 3)) * 0.7 + 0.15) ** 2) < 0.5
    ring = np.abs(np.hypot(dx, dy) - 0.4) < 0.03
    return np.where((heart | ring)[..., None], C((246, 232, 210)), c)


def sack_tex(n=256):
    c = TL.fabric((230, 220, 196), weave=96, n=n)
    im, d = draw(c)
    f = ML.font(56); tw = d.textlength('FLOUR', font=f)
    d.text(((n - tw) / 2, 70), 'FLOUR', font=f, fill=(150, 90, 80))
    d.ellipse((n / 2 - 26, 150, n / 2 + 26, 202), outline=(150, 90, 80), width=5)
    return np.asarray(im, np.float32)


def coffee_sack_tex(n=256):
    """burlap coffee sack: coarse weave, stencilled COFFEE and a bean mark"""
    c = TL.fabric((176, 140, 96), weave=64, n=n)
    im, d = draw(c)
    ink = (74, 46, 30)
    f = ML.font(50); tw = d.textlength('COFFEE', font=f)
    d.text(((n - tw) / 2, 56), 'COFFEE', font=f, fill=ink)
    d.ellipse((n / 2 - 34, 132, n / 2 + 34, 212), outline=ink, width=6)
    d.arc((n / 2 - 30, 120, n / 2 + 14, 224), 300, 60, fill=ink, width=5)
    d.line((30, 30, n - 30, 30), fill=ink, width=4); d.line((30, n - 30, n - 30, n - 30), fill=ink, width=4)
    return np.asarray(im, np.float32)


def sugar_label_tex(n=256):
    """paper sugar sack label: blue band, SUGAR, a little crystal"""
    c = TL.solid((238, 240, 244), 3, 73, n)
    im, d = draw(c)
    blue = (70, 120, 200)
    d.rectangle((0, 0, n, 44), fill=blue); d.rectangle((0, n - 44, n, n), fill=blue)
    f = ML.font(58); tw = d.textlength('SUGAR', font=f)
    d.text(((n - tw) / 2, 66), 'SUGAR', font=f, fill=blue)
    d.polygon([(n / 2, 140), (n / 2 + 32, 172), (n / 2, 204), (n / 2 - 32, 172)], outline=blue, width=6)
    return np.asarray(im, np.float32)


def beans_tex(n=256):
    """roasted coffee beans seen from above"""
    rng = np.random.default_rng(71)
    im, d = draw(TL.solid((52, 32, 22), 6, 72, n))
    for _ in range(170):
        x, y = rng.uniform(0, n, 2); a = rng.uniform(0, math.pi); w, h = 15, 10
        col = tuple(int(v * rng.uniform(0.85, 1.15)) for v in (112, 70, 44))
        pts = [(x + w * math.cos(t) * math.cos(a) - h * math.sin(t) * math.sin(a),
                y + w * math.cos(t) * math.sin(a) + h * math.sin(t) * math.cos(a)) for t in np.linspace(0, 2 * math.pi, 14)]
        d.polygon(pts, fill=col, outline=(40, 24, 16))
        d.line((x - w * 0.8 * math.cos(a), y - w * 0.8 * math.sin(a), x + w * 0.8 * math.cos(a), y + w * 0.8 * math.sin(a)), fill=(40, 24, 16), width=2)
    return np.asarray(im, np.float32)


def cakebox_tex(n=256):
    c = TL.fill(n, (246, 190, 206), 2, 69)
    im, d = draw(c)
    d.rectangle((n * 0.44, 0, n * 0.56, n), fill=(255, 255, 255)); d.rectangle((0, n * 0.44, n, n * 0.56), fill=(255, 255, 255))
    d.rectangle((2, 2, n - 3, n - 3), outline=(226, 150, 172), width=4)
    return np.asarray(im, np.float32)


def grid_tex(n=64):
    x, y = TL.xy(n)
    g = ((x * 8) % 1 < 0.45)
    return np.where(g[..., None], C((60, 62, 66)), C((190, 194, 200)))


def gauge_tex(n=128):
    im = Image.new('RGB', (n, n), (240, 236, 220)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 5, n - 5), fill=(252, 252, 248), outline=(120, 100, 60), width=6)
    for k in range(9):
        a = math.radians(210 - k * 30)
        d.line((n / 2 + 40 * math.cos(a), n / 2 - 40 * math.sin(a), n / 2 + 52 * math.cos(a), n / 2 - 52 * math.sin(a)), fill=(40, 40, 40), width=3)
    d.line((n / 2, n / 2, n / 2 + 34, n / 2 - 30), fill=(200, 40, 40), width=4)
    return np.asarray(im, np.float32)


def keys_tex(n=128):
    im = Image.new('RGB', (n, n), (236, 164, 184)); d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            d.ellipse((10 + i * 29, 10 + j * 29, 32 + i * 29, 32 + j * 29), fill=(250, 248, 240), outline=(150, 120, 60), width=2)
            d.text((16 + i * 29, 12 + j * 29), '7894561230.+-=C%'[j * 4 + i], font=ML.font(14, serif=False), fill=(60, 50, 50))
    return np.asarray(im, np.float32)


def candy_tex(c1, c2, n=64):
    rng = np.random.default_rng(sum(c1))
    idx, d = ML.voronoi(n, 40, int(sum(c2)))
    return np.where(((idx % 2) == 0)[..., None], C(c1), C(c2)) * (0.8 + 0.2 * (d > 0.02))[..., None]


# ================================================================================================= little bakes (added into other models)
FROST = {'pink': ('pink', 'liner_pink', 'berry'), 'choc': ('chocfrost', 'liner_brown', 'cream'), 'mint': ('mint', 'liner_mint', 'choc'),
         'cream': ('cream', 'liner_pink', 'berry'), 'blue': ('bluefrost', 'liner_mint', 'pink'), 'caramel': ('caramel', 'liner_brown', 'choc')}


def cupcake(X, x, y, z, kind='pink', s=1.0, n=14):
    """ribbed paper liner, a piped swirl of frosting and a topping; about 44 r x 104 h at s = 1"""
    fr, ln, top = FROST[kind]
    revolve(X.mesh(M_[ln]), [(30 * s, z), (44 * s, z + 48 * s)], u_tiles=3, n=n, cx=x, cy=y, vlen=64,
            rfun=lambda a, r, zz: r * (1 + 0.05 * math.sin(a * 16)))
    prof = [(45, 46), (48, 56), (40, 66), (41, 70), (29, 80), (30, 84), (17, 94), (0, 99)]
    revolve(X.mesh(M_[fr]), [(r * s, z + h * s) for r, h in prof], u_tiles=2, n=n, cx=x, cy=y, vlen=128)
    sphere(X.mesh(M_[top]), (x, y, z + 102 * s), 9 * s, nu=8, nv=5)
    return (x, y, 42 * s, z, z + 96 * s)


def round_cake(X, x, y, z, R, H, side, top='cream', deco='berry', nd=8, n=28):
    """frosted round cake on a gold board with a ring of piped dollops topped with berries"""
    revolve(X.mesh(M_['gold']), [(R + 14, z), (R + 14, z + 6), (R, z + 6)], n=n, cx=x, cy=y)
    revolve(X.mesh(M_[side]), [(R, z + 6), (R, z + H - 8), (R - 8, z + H), (0, z + H)], u_tiles=4, n=n, cx=x, cy=y)
    for k in range(nd):
        a = 2 * math.pi * k / nd; px, py = x + (R - 30) * math.cos(a), y + (R - 30) * math.sin(a)
        revolve(X.mesh(M_[top]), [(22, z + H), (20, z + H + 12), (10, z + H + 22), (0, z + H + 26)], n=8, cx=px, cy=py)
        ellipsoid(X.mesh(M_[deco]), (px, py, z + H + 32), 11, 11, 13, nu=8, nv=5)
    return (x, y, R, z, z + H)


def tag(X, x, y, z, face=(0, -1, 0)):
    """price card on a pick"""
    tube(X.mesh(M_['white']), [(x, y, z), (x, y, z + 44)], 2, nseg=5)
    pic(X.mesh(M_['tag']), (x + face[0] * 2.5, y + face[1] * 2.5, z + 56), face, 48, 26)
    pic(X.mesh(M_['white']), (x - face[0] * 0.5, y - face[1] * 0.5, z + 56), (-face[0], -face[1], 0), 48, 26)


def heart_poly(s):
    pts = []
    for t in np.linspace(0, 2 * math.pi, 22, endpoint=False):
        pts.append((s * 16 * math.sin(t) ** 3 / 16, s * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16))
    return pts


# ================================================================================================= display unit + its goods
def display_unit():
    """the pine display shelving from the reference photo: four walkable shelves between corner posts.
    Origin: centre of the footprint, long side along x, customer side -y."""
    X = ML.Model(); W, D = UNIT_W / 2, UNIT_D / 2
    shelves = [((-W, -D, z - SHELF_T), (W, D, z)) for z in UNIT_Z]
    posts = [((sx * W - (40 if sx > 0 else 0), sy * D - (40 if sy > 0 else 0), 0), (sx * W + (40 if sx < 0 else 0), sy * D + (40 if sy < 0 else 0), UNIT_Z[3] - SHELF_T))
             for sx in (-1, 1) for sy in (-1, 1)]
    mid = [((-20, sy * D - (36 if sy > 0 else 0), 0), (20, sy * D + (36 if sy < 0 else 0), UNIT_Z[3] - SHELF_T)) for sy in (-1, 1)]
    # recessed plinth under the bottom shelf (kick space 40u): no eye-level gap under the unit (sightlines)
    plinth = [((-W + 40, -D + 40, 0), (W - 40, D - 40, UNIT_Z[0] - SHELF_T))]
    boxes(X, 'pine', shelves, r=4, tile=192)
    boxes(X, 'pinev', posts + mid + plinth, r=4, tile=192)
    # front lip on every shelf like the trays in the photo
    lips = [((-W + 40, -D - 6, z - SHELF_T - 16), (W - 40, -D, z - SHELF_T)) for z in UNIT_Z[1:]]
    boxes(X, 'pinev', lips, r=2)
    ML.save('display_unit', X)
    coll('display_unit', shelves + plinth + [q for b in posts + mid for q in cut_z(b, shelves)])


TRAYS = {'tray_cup_a': ('cup', ('pink', 'cream', 'pink')), 'tray_cup_b': ('cup', ('mint', 'choc', 'mint')),
         'tray_cup_c': ('cup', ('blue', 'caramel', 'blue')), 'tray_mousse': ('mousse', None), 'tray_slices': ('slice', None),
         'tray_hearts': ('heart', None), 'tray_cream': ('cream', None)}


def trays():
    """pine trays of three bakes with price cards (front -y). Collision: one low box (cover on the shelves)."""
    for name, (kind, sub) in TRAYS.items():
        X = ML.Model()
        boxes(X, 'pine', [((-180, -100, 0), (180, 100, 12))], r=3)
        boxes(X, 'pinev', [((-180, -100, 12), (-168, 100, 24)), ((168, -100, 12), (180, 100, 24))], r=2)
        for i, px in enumerate((-112, 0, 112)):
            if kind == 'cup': cupcake(X, px, 10, 12, sub[i], 0.9)
            elif kind == 'mousse':
                rbox(X.mesh(M_['pink']), (px - 38, -28, 12), (px + 38, 48, 62), r=6, k=2)
                rbox(X.mesh(M_['cream']), (px - 38, -28, 62), (px + 38, 48, 74), r=5, k=2)
                ellipsoid(X.mesh(M_['berry']), (px, 10, 86), 16, 16, 18, nu=8, nv=5)
            elif kind == 'slice':
                rbox(X.mesh(M_['sponge']), (px - 44, -30, 12), (px + 44, 50, 72), r=2, k=1, tile=60, faces='nsew')
                rbox(X.mesh(M_['caramel']), (px - 44, -30, 70), (px + 44, 50, 80), r=3, k=1)
                for q in (-20, 20): sphere(X.mesh(M_['choc']), (px + q, 10, 86), 10, nu=8, nv=5)
            elif kind == 'heart':
                hp = [(px + a, 10 + b) for a, b in heart_poly(46)]
                mprism(X.mesh(M_['matcha']), hp, 12, 58, tile=64)
                mprism(X.mesh(M_['cream']), [(px + a, 10 + b) for a, b in heart_poly(34)], 58, 66, tile=64, bot=False)
                mprism(X.mesh(M_['berry']), [(px + a, 12 + b) for a, b in heart_poly(14)], 66, 72, tile=64, bot=False)
            else:
                revolve(X.mesh(M_['choc']), [(40, 12), (40, 52), (34, 58), (0, 58)], n=14, cx=px, cy=10)
                revolve(X.mesh(M_['cream']), [(30, 58), (30, 68), (18, 80), (0, 88)], n=12, cx=px, cy=10)
                sphere(X.mesh(M_['berry']), (px, 10, 92), 9, nu=8, nv=5)
            tag(X, px, -82, 12)
        ML.save(name, X)
        coll(name, [((-180, -100, 0), (180, 100, 96))])


def big_cakes():
    for name, side, top, deco in (('cake_pink', 'pink', 'cream', 'berry'), ('cake_green', 'matcha', 'cream', 'berry'),
                                  ('cake_brown', 'chocfrost', 'cream', 'choc')):
        X = ML.Model()
        c = round_cake(X, 0, 0, 0, 150, 140, side, top, deco, nd=10)
        tag(X, 0, -168, 0)
        ML.save(name, X)
        coll(name, cyls=[(0, 0, 150, 0, 140)])


def tier_stand():
    """three-tier porcelain cupcake stand (photo, top left). The top plate is left clear for the Imperius."""
    X = ML.Model(); P = M_['porcelain']; cy = []
    revolve(X.mesh(P), [(120, 0), (120, 8), (40, 20), (22, 30)], n=24)
    revolve(X.mesh(P), [(22, 30), (20, TIER_Z[2] - 6)], n=12)
    for R, z in zip(TIER_R, TIER_Z):
        revolve(X.mesh(P), [(20, z - 8), (R - 2, z - 8), (R + 4, z - 2), (R, z + 2), (R - 14, z), (0, z)], n=32)
        cy.append((0, 0, R, z - 8, z))
    kinds = ('pink', 'mint', 'cream', 'blue', 'choc', 'caramel')
    for k in range(6):
        a = math.radians(k * 60 + 30); cy.append(cupcake(X, 165 * math.cos(a), 165 * math.sin(a), TIER_Z[0], kinds[k], 0.85))
    for k in range(5):
        a = math.radians(k * 72 + 10); cy.append(cupcake(X, 108 * math.cos(a), 108 * math.sin(a), TIER_Z[1], kinds[(k + 2) % 6], 0.8))
    cy += [(0, 0, 24, a, b) for a, b in ((0, TIER_Z[0] - 8), (TIER_Z[0], TIER_Z[1] - 8), (TIER_Z[1], TIER_Z[2] - 8))]
    ML.save('tier_stand', X)
    coll('tier_stand', cyls=cy)


def lace_stand():
    """pedestal cake stand with a lace skirt and chocolate cupcakes (photo, top centre)"""
    X = ML.Model(); P = M_['porcelain']
    revolve(X.mesh(P), [(100, 0), (100, 8), (34, 30), (26, 110), (60, 134)], n=24)
    revolve(X.mesh(P), [(60, 134), (188, 134), (194, 140), (188, 146), (0, 146)], n=32)
    revolve(X.mesh(M_['lace']), [(192, 142), (198, 78)], u_tiles=6, n=32, v_of=lambda r, z: (142 - z) / 64)
    cy = [(0, 0, 100, 0, 30), (0, 0, 34, 30, 134), (0, 0, 190, 134, 146)]
    for k in range(6):
        a = math.radians(k * 60); cy.append(cupcake(X, 122 * math.cos(a), 122 * math.sin(a), 146, 'choc', 0.9))
    cy.append(cupcake(X, 0, 0, 146, 'cream', 0.9))
    tag(X, 0, -176, 146)
    ML.save('lace_stand', X)
    coll('lace_stand', cyls=cy)


def vases():
    """glass vases of sugar pearls: one of ruffled cake pops with blue ribbons, one of straws and teddy-bear cookies"""
    for name in ('vase_pops', 'vase_bears'):
        X = ML.Model()
        revolve(X.mesh(M_['glass']), [(48, 0), (42, 70), (62, 210), (78, 236)], n=20)
        revolve(X.mesh(M_['porcelain']), [(50, 0), (50, 4), (0, 4)], n=20)
        revolve(X.mesh(M_['pearl']), [(40, 6), (41, 70), (58, 196), (0, 196)], n=16, vlen=64)
        if name == 'vase_pops':
            for k in range(7):
                a = math.radians(k * 51 + 12); r0, r1 = 22, 60 + (k % 3) * 22
                top = (r1 * math.cos(a), r1 * math.sin(a), 330 + (k % 2) * 46)
                tube(X.mesh(M_['white']), [(r0 * math.cos(a), r0 * math.sin(a), 190), top], 3, nseg=5)
                sphere(X.mesh(M_['pink' if k % 2 else 'rose']), top, 30, nu=10, nv=7, bump=lambda p, t: 1 + 0.07 * math.sin(t * 8) * math.cos(p))
                ellipsoid(X.mesh(M_['ribbon']), (top[0], top[1], top[2] - 34), 12, 12, 6, nu=6, nv=4)
        else:
            for k in range(9):
                a = math.radians(k * 40); r1 = 70 + (k % 2) * 16
                tube(X.mesh(M_['straw']), [(20 * math.cos(a), 20 * math.sin(a), 190), (r1 * math.cos(a), r1 * math.sin(a), 330)], 5, nseg=6, vlen=24)
            for (bx, by, bz) in ((-28, -10, 420), (40, 14, 392)):
                tube(X.mesh(M_['white']), [(bx * 0.4, by * 0.4, 190), (bx, by, bz - 40)], 3, nseg=5)
                T = X.mesh(M_['teddy'])
                ellipsoid(T, (bx, by, bz - 16), 22, 17, 26, nu=10, nv=6)
                sphere(T, (bx, by, bz + 26), 24, nu=10, nv=7)
                for s in (-1, 1):
                    sphere(T, (bx + s * 20, by, bz + 46), 10, nu=8, nv=5)
                    ellipsoid(T, (bx + s * 24, by - 4, bz - 6), 8, 8, 14, nu=6, nv=4)
                    sphere(X.mesh(M_['black']), (bx + s * 9, by - 21, bz + 30), 3.5, nu=6, nv=4)
                sphere(X.mesh(M_['cream']), (bx, by - 20, bz + 20), 10, nu=8, nv=5)
                sphere(X.mesh(M_['black']), (bx, by - 29, bz + 23), 3.5, nu=6, nv=4)
                pic(X.mesh(M_['tag']), (bx + 4, by - 20, bz - 56), (0, -1, 0), 44, 24)
        ML.save(name, X)
        coll(name, cyls=[(0, 0, 76, 0, 236), (0, 0, 60, 236, 420)])


def single_cupcakes():
    for kind in FROST:
        X = ML.Model(); cupcake(X, 0, 0, 0, kind, 1.0, n=18)
        ML.save('cupcake_' + kind, X)
        coll('cupcake_' + kind, cyls=[(0, 0, 42, 0, 96)])


# ================================================================================================= counter + what stands on it
def counter():
    """service counter: white tongue-and-groove front (customer side +x), pine top, open cubbies on the staff side
    (-x) that you can walk into (cubby floor 16, a shelf at 352). Origin: centre of the footprint, long side y."""
    X = ML.Model(); L, D, H = COUNTER_L / 2, COUNTER_D / 2, COUNTER_H
    top = [((-D - 16, -L - 16, H - 32), (D + 16, L + 16, H))]
    front = [((D - 24, -L, 0), (D, L, H - 32))]
    ends = [((-D, -L, 0), (D - 24, -L + 24, H - 32)), ((-D, L - 24, 0), (D - 24, L, H - 32))]
    div = [((-D, y - 12, 16), (D - 24, y + 12, H - 32)) for y in (-270, 270)]
    plinth = [((-D, -L + 24, 0), (D - 24, L - 24, 16))]
    shelf = [((-D + 40, -L + 24, 336), (D - 24, L - 24, 352))]
    boxes(X, 'pine', top, r=5, tile=192)
    boxes(X, 'bead', front + ends, r=2, tile=256)
    boxes(X, 'white', div + plinth + shelf, r=2)
    boxes(X, 'mint', [((D, -L, 0), (D + 6, L, 56))], r=2)
    ML.save('counter', X)
    coll('counter', top + front + ends + [q for b in div for q in cut_z(b, shelf)] + plinth + shelf)


def espresso():
    """retro lever espresso machine, cream enamel and chrome, working side +x (towards the customers). You can walk
    under the group heads on the drip tray (z 60) and stand on the cup-warmer deck (z ESP_H)."""
    X = ML.Model(); W = 280
    base = ((-170, -W, 0), (170, W, 60)); body = ((-170, -W, 60), (30, W, 380)); deck = ((-170, -W, 380), (170, W, ESP_H))
    rbox(X.mesh(M_['chrome']), *base, r=8, k=2)
    rbox(X.mesh(M_['creamgloss']), *body, r=10, k=2)
    rbox(X.mesh(M_['chrome']), *deck, r=10, k=2)
    pic(X.mesh(M_['grid']), (100, 0, 60.6), (0, 0, 1), 2 * W - 40, 120, up=(1, 0, 0))
    for y in (-120, 120):                                           # group heads + portafilters + levers
        revolve(X.mesh(M_['chrome']), [(0, 296), (38, 296), (44, 310), (44, 380)], n=16, cx=100, cy=y)
        tube(X.mesh(M_['black']), [(100, y, 300), (190, y - 30, 286)], 9, nseg=8)
        tube(X.mesh(M_['chrome']), [(100, y, ESP_H), (124, y, ESP_H + 150)], 7, nseg=8)
        sphere(X.mesh(M_['black']), (126, y, ESP_H + 160), 16, nu=8, nv=6)
        pic(X.mesh(M_['gauge']), (30.6, y, 250), (1, 0, 0), 70, 70)
    for y in (-250, 250):                                           # steam wands
        tube(X.mesh(M_['chrome']), [(60, y, 380), (110, y, 330), (120, y * 0.94, 150)], 6, nseg=6)
    pic(X.mesh(M_['badge']), (30.6, 0, 160), (1, 0, 0), 220, 56)
    pic(X.mesh(M_['badge']), (-170.6, 0, 230), (-1, 0, 0), 300, 76)
    for k in range(4): pic(X.mesh(M_['glow']), (30.6, -45 + k * 30, 330), (1, 0, 0), 16, 16)
    for (a, b) in (((-160, -W + 10, ESP_H + 36), (160, -W + 10, ESP_H + 36)), ((-160, W - 10, ESP_H + 36), (160, W - 10, ESP_H + 36)),
                   ((-160, -W + 10, ESP_H + 36), (-160, W - 10, ESP_H + 36))):          # cup rail (three sides)
        tube(X.mesh(M_['chrome']), [a, b], 5, nseg=6)
    for (px, py) in ((-160, -W + 10), (-160, W - 10), (160, -W + 10), (160, W - 10), (-160, 0)):
        tube(X.mesh(M_['chrome']), [(px, py, ESP_H), (px, py, ESP_H + 36)], 4, nseg=6)
    tube(X.mesh(M_['coffee']), [(100, -120, 296), (100, -120, 150)], 3, nseg=5)      # the pour
    ML.save('espresso', X)
    coll('espresso', [base, body, deck], cyls=[(100, -120, 44, 290, 380), (100, 120, 44, 290, 380)])


def cash_register():
    """vintage till in pink enamel and brass, keys facing +x"""
    X = ML.Model()
    rbox(X.mesh(M_['pinkgloss']), (-150, -150, 0), (150, 150, 130), r=10, k=2)
    rbox(X.mesh(M_['pinkgloss']), (-150, -140, 130), (10, 140, 300), r=14, k=2)
    X.mesh(M_['keys']).poly([np.array(p, float) for p in ((140, 120, 134), (140, -120, 134), (12, -120, 250), (12, 120, 250))],
                            (0.68, 0, 0.73), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(M_['brass']), (-120, -110, 300), (-20, 110, 360), r=6, k=2)
    pic(X.mesh(M_['tag']), (-19.4, 0, 330), (1, 0, 0), 150, 44)
    rbox(X.mesh(M_['brass']), (150, -130, 20), (158, 130, 100), r=3, k=1)
    tube(X.mesh(M_['brass']), [(-60, -150, 180), (-60, -190, 180), (-60, -190, 250)], 8, nseg=8)
    sphere(X.mesh(M_['black']), (-60, -190, 262), 16, nu=8, nv=6)
    ML.save('cash_register', X)
    coll('cash_register', [((-150, -150, 0), (158, 150, 130)), ((-150, -140, 130), (10, 140, 360))])


def cone_holder():
    """a pine block holding stacked waffle cones (photo, left edge)"""
    X = ML.Model()
    rbox(X.mesh(M_['pine']), (-170, -56, 0), (170, 56, 44), r=5, k=2)
    for px in (-120, -40, 40, 120):
        for dz in (0, 40):
            revolve(X.mesh(M_['waffle']), [(6, 30 + dz), (48, 210 + dz), (44, 212 + dz)], u_tiles=3, n=14, cx=px, cy=0, vlen=64)
    ML.save('cone_holder', X)
    coll('cone_holder', [((-170, -56, 0), (170, 56, 250))])


def cake_dome():
    """glass cloche over a strawberry cake on a pedestal stand"""
    X = ML.Model(); P = M_['porcelain']
    revolve(X.mesh(P), [(100, 0), (100, 8), (34, 30), (26, 100), (60, 124)], n=24)
    revolve(X.mesh(P), [(60, 124), (178, 124), (184, 130), (178, 136), (0, 136)], n=32)
    round_cake(X, 0, 0, 136, 110, 96, 'pink', 'cream', 'berry', nd=7, n=24)
    arc = [(166 * math.cos(t), 136 + 190 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)]
    revolve(X.mesh(M_['glass']), arc, n=24)
    sphere(X.mesh(M_['glass']), (0, 0, 340), 18, nu=8, nv=6)
    ML.save('cake_dome', X)
    coll('cake_dome', cyls=[(0, 0, 100, 0, 30), (0, 0, 34, 30, 124), (0, 0, 180, 124, 136), (0, 0, 150, 136, 330)])


# ================================================================================================= customer side
def bistro():
    X = ML.Model()
    revolve(X.mesh(M_['white']), [(170, 0), (170, 10), (44, 30), (26, 70), (26, TABLE_Z - 40), (60, TABLE_Z - 20)], n=20)
    revolve(X.mesh(M_['pine']), [(60, TABLE_Z - 20), (296, TABLE_Z - 20), (300, TABLE_Z - 10), (296, TABLE_Z), (0, TABLE_Z)], n=36,
            v_of=lambda r, z: r / 150)
    ML.save('bistro_table', X)
    coll('bistro_table', cyls=[(0, 0, 170, 0, 16), (0, 0, 30, 16, TABLE_Z - 20), (0, 0, 300, TABLE_Z - 20, TABLE_Z)])
    # chair: round pine seat, white splayed legs, bentwood back with a heart (front +x)
    X = ML.Model(); Z = SEAT_Z
    revolve(X.mesh(M_['pine']), [(40, Z - 26), (146, Z - 20), (152, Z - 10), (146, Z), (0, Z)], n=28, v_of=lambda r, z: r / 150)
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(X.mesh(M_['white']), [(sx * 122, sy * 122, 0), (sx * 96, sy * 96, Z - 22)], 13, nseg=8)
            legs.append(((sx * 110 - 14, sy * 110 - 14, 0), (sx * 110 + 14, sy * 110 + 14, Z - 24)))
    hoop = [(-128 - 26 * math.sin(t) , 118 * math.cos(t), Z + 400 * math.sin(t)) for t in np.linspace(0, math.pi, 17)]
    tube(X.mesh(M_['white']), hoop, 13, nseg=8)
    mprism(X.mesh(M_['pinev']), [(a * 3.2, b * 3.2) for a, b in heart_poly(26)], -4, 4, tile=96)
    Hm = X.m.pop(M_['pinev'])                                                   # stand the heart up in the back
    R = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]])
    X.mesh(M_['pinev']).add(Hm, R, (-146, 0, Z + 220))
    for y in (-60, 60): tube(X.mesh(M_['white']), [(-132, y, Z), (-150, y * 0.9, Z + 150)], 7, nseg=6)
    ML.save('bistro_chair', X)
    coll('bistro_chair', legs + [((-170, -124, Z), (-124, 124, Z + 404))], cyls=[(0, 0, 150, Z - 24, Z)])


def table_things():
    """a flat white with a latte heart on its saucer, and a croissant on a plate"""
    X = ML.Model(); P = M_['porcelain']
    revolve(X.mesh(P), [(40, 0), (104, 6), (110, 12), (104, 14), (0, 10)], n=24)
    revolve(X.mesh(P), [(42, 10), (70, 40), (78, 104), (72, 104), (66, 44), (0, 30)], n=24)
    disc(X.mesh(M_['latte']), 71, 92, up=True, n=20)
    tube(X.mesh(P), [(0, 74 + 34 * math.cos(t), 62 + 30 * math.sin(t)) for t in np.linspace(-1.9, 1.9, 9)], 6, nseg=6)
    ML.save('coffee_cup', X)
    coll('coffee_cup', cyls=[(0, 0, 106, 0, 12), (0, 0, 78, 12, 104)])
    X = ML.Model()
    revolve(X.mesh(P), [(60, 0), (150, 8), (158, 16), (150, 18), (0, 10)], n=28)
    pts = [(96 * math.cos(t), 96 * math.sin(t), 46) for t in np.linspace(-2.0, 2.0, 17)]
    rad = [12 + 30 * math.sin(math.pi * i / 16) ** 0.7 for i in range(17)]
    tube(X.mesh(M_['baguette']), pts, rad, nseg=10, vlen=48)
    ML.save('croissant_plate', X)
    coll('croissant_plate', cyls=[(0, 0, 150, 0, 16), (0, 0, 120, 16, 84)])


# ================================================================================================= bread wall
def bread_rack():
    """pine baker's rack against a wall: origin on the wall at the middle, the shelves reach out to -x"""
    X = ML.Model(); L, D = RACK_L / 2, RACK_D
    H = RACK_Z[2] + 40
    ends = [((-D, -L, 0), (0, -L + 32, H)), ((-D, L - 32, 0), (0, L, H))]
    posts = [((-D, -16, 0), (-D + 32, 16, H)), ((-32, -16, 0), (0, 16, H))]
    shelves = [((-D, -L + 32, z - 24), (0, L - 32, z)) for z in RACK_Z]
    back = [((-8, -L + 32, z), (0, L - 32, z + 60)) for z in RACK_Z]
    boxes(X, 'pinev', ends + posts, r=3, tile=192)
    boxes(X, 'pine', shelves + back, r=3, tile=192)
    ML.save('bread_rack', X)
    coll('bread_rack', ends + [q for b in posts for q in cut_z(b, shelves)] + shelves)


def breads():
    X = ML.Model()                                                              # wicker tray of round loaves
    rbox(X.mesh(M_['wicker']), (-150, -100, 0), (150, 100, 60), r=10, k=2, tile=64, faces='nsewb')
    for (px, py) in ((-80, -20), (60, 30), (0, -10)):
        ellipsoid(X.mesh(M_['crust']), (px, py, 70), 84, 76, 56, nu=14, nv=8)
    ML.save('bread_basket', X)
    coll('bread_basket', [((-150, -100, 0), (150, 100, 116))])
    X = ML.Model()                                                              # tall wicker bin of baguettes
    revolve(X.mesh(M_['wicker']), [(70, 0), (88, 170), (82, 170), (66, 8), (0, 8)], u_tiles=6, n=18, vlen=64)
    for k in range(6):
        a = math.radians(k * 60 + 15)
        p0 = (30 * math.cos(a), 30 * math.sin(a), 20); p1 = (74 * math.cos(a), 74 * math.sin(a), 330 + (k % 3) * 24)
        tube(X.mesh(M_['baguette']), [p0, tuple((np.array(p0) + np.array(p1)) / 2), p1], [22, 26, 14], nseg=8, vlen=80)
    ML.save('baguette_bin', X)
    coll('baguette_bin', cyls=[(0, 0, 90, 0, 170), (0, 0, 70, 170, 360)])
    X = ML.Model()                                                              # tin loaves on a board
    rbox(X.mesh(M_['pine']), (-190, -70, 0), (190, 70, 12), r=3, k=1)
    for px in (-120, 0, 120):
        rbox(X.mesh(M_['crust']), (px - 50, -56, 12), (px + 50, 56, 96), r=18, k=3,
             inflate=lambda x, y, z, n: 14 * max(0.0, n[2]))
    ML.save('tin_loaves', X)
    coll('tin_loaves', [((-190, -70, 0), (190, 70, 108))])


# ================================================================================================= wall shelves + jars
def wall_shelves():
    """pine boards on white brackets. Origin on the wall at the middle of the board, z = 0 is the walk surface."""
    for name, L, D in (('shelf_low', 3400, 320), ('shelf_high', 2000, 200)):
        X = ML.Model()
        board = ((-L / 2, -D, -24), (L / 2, 0, 0))
        rbox(X.mesh(M_['pine']), *board, r=4, k=1, tile=192)
        n = int(L // 600)
        for k in range(n + 1):
            x = -L / 2 + 60 + k * (L - 120) / n
            boxes(X, 'white', [((x - 12, -D + 30, -52), (x + 12, 0, -24)), ((x - 12, -36, -52 - D * 0.7), (x + 12, 0, -52))], r=3)
            tube(X.mesh(M_['white']), [(x, -D + 40, -50), (x, -20, -40 - D * 0.7)], 9, nseg=6)
        ML.save(name, X)
        coll(name, [board])


def jars():
    for name, fill in (('jar_a', 'candy_a'), ('jar_b', 'candy_b'), ('jar_c', 'candy_c')):
        X = ML.Model()
        revolve(X.mesh(M_['glass']), [(60, 0), (72, 20), (72, 170), (52, 196), (52, 206)], n=18)
        revolve(X.mesh(M_[fill]), [(64, 4), (66, 20), (66, 140), (0, 150)], n=14, vlen=64)
        revolve(X.mesh(M_['chrome']), [(56, 204), (56, 222), (0, 226)], n=16)
        ML.save(name, X)
        coll(name, cyls=[(0, 0, 72, 0, 224)])
    for word in ('flour', 'sugar', 'tea'):
        X = ML.Model()
        revolve(X.mesh(M_['tin_' + word]), [(74, 0), (74, 190)], u_tiles=2, n=20, v_of=lambda r, z: z / 190)
        revolve(X.mesh(M_['mintgloss']), [(78, 186), (78, 206), (20, 212), (16, 226), (0, 230)], n=20)
        ML.save('tin_' + word, X)
        coll('tin_' + word, cyls=[(0, 0, 78, 0, 226)])
    X = ML.Model(); G = M_['mintgloss']                                          # teapot, spout towards +x
    ellipsoid(X.mesh(G), (0, 0, 96), 120, 120, 96, nu=20, nv=12)
    revolve(X.mesh(G), [(70, 0), (70, 8), (40, 12)], n=16)
    revolve(X.mesh(M_['porcelain']), [(56, 180), (50, 196), (16, 204), (14, 220), (0, 224)], n=16)
    tube(X.mesh(G), [(100, 0, 70), (160, 0, 110), (196, 0, 180)], [26, 18, 12], nseg=8)
    tube(X.mesh(G), [(-104 - 56 * math.sin(t), 0, 100 - 64 * math.cos(t)) for t in np.linspace(0.2, math.pi - 0.2, 9)], 10, nseg=6)
    for k in range(8):
        a = math.radians(k * 45); sphere(X.mesh(M_['porcelain']), (116 * math.cos(a), 116 * math.sin(a), 110), 9, nu=6, nv=4)
    ML.save('teapot', X)
    coll('teapot', cyls=[(0, 0, 122, 0, 200)])
    # the cookie jar (the secret): open glass jar, cookies in the bottom, its lid beside it
    X = ML.Model()
    revolve(X.mesh(M_['glass']), [(104, 0), (JAR_R, 30), (JAR_R, JAR_H - 30), (108, JAR_H - 8), (112, JAR_H)], n=24)
    for k, zz in enumerate((0, 22, 44, 66)):
        revolve(X.mesh(M_['cookie']), [(100 - k * 2, zz + 2), (100 - k * 2, zz + 20), (0, zz + 24)], n=16, cx=(k % 2) * 6 - 3, cy=(k % 3) * 4 - 4,
                v_of=lambda r, z: r / 100)
    pic(X.mesh(M_['open']), (0, -JAR_R - 1, 170), (0, -1, 0), 1, 1)             # (kept tiny: the label is the tin_cookies band below)
    revolve(X.mesh(M_['tin_cookies']), [(JAR_R + 1, 120), (JAR_R + 1, 200)], u_tiles=2, n=24, a0=200, a1=340, v_of=lambda r, z: 0.3 + (z - 120) / 200)
    ML.save('cookie_jar', X)
    X = ML.Model()
    revolve(X.mesh(M_['mintgloss']), [(0, 0), (116, 0), (116, 16), (30, 26), (24, 50), (0, 56)], n=24)
    ML.save('jar_lid', X)
    coll('jar_lid', cyls=[(0, 0, 116, 0, 26)])


# ================================================================================================= shop fittings
def fittings():
    # the open shop door: hinge at the origin, the leaf runs +y, 30 thick towards +x
    X = ML.Model(); Wd, Hd = DOOR_W, DOOR_H
    fr = [((0, 0, 0), (30, 70, Hd)), ((0, Wd - 70, 0), (30, Wd, Hd)), ((0, 70, 0), (30, Wd - 70, 240)), ((0, 70, Hd - 80), (30, Wd - 70, Hd)),
          ((0, 70, 620), (30, Wd - 70, 660))]
    boxes(X, 'white', fr, r=3, tile=256)
    for z0, z1 in ((240, 620), (660, Hd - 80)):
        for xx, nx in ((13, -1), (17, 1)):
            X.mesh(M_['glass']).quad((xx, 70, z0), (xx, Wd - 70, z0), (xx, Wd - 70, z1), (xx, 70, z1), n=(nx, 0, 0))
    for sx in (-1, 1):
        tube(X.mesh(M_['brass']), [(15 + sx * 15, Wd - 110, 560), (15 + sx * 44, Wd - 110, 580), (15 + sx * 44, Wd - 110, 760), (15 + sx * 15, Wd - 110, 780)], 9, nseg=8)
        pic(X.mesh(M_['open']), (15 + sx * 19, Wd / 2, 900), (sx, 0, 0), 300, 150)
    ML.save('shop_door', X)
    coll('shop_door', [((0, 0, 0), (30, Wd, Hd))])
    # pendant lamp: origin at the ceiling, hangs down 300
    X = ML.Model()
    tube(X.mesh(M_['black']), [(0, 0, 0), (0, 0, -170)], 3, nseg=5)
    revolve(X.mesh(M_['mintgloss']), [(110, -300), (104, -250), (40, -190), (14, -170), (0, -168)], n=20)
    revolve(X.mesh(M_['white']), [(12, -172), (38, -192), (100, -250), (106, -298)], n=20, inward=True)
    sphere(X.mesh(M_['glow']), (0, 0, -262), 26, nu=10, nv=7)
    ML.save('pendant', X)
    # bunting: a sagging string of pastel flags 3600 long along x, origin mid-span at the string ends' height
    X = ML.Model(); n = 40
    for k in range(n):
        x0, x1 = -1920 + k * 96, -1824 + k * 96
        z0, z1 = (-150 * (1 - (x / 1920) ** 2) for x in (x0, x1))
        X.mesh(M_['bunting']).poly([np.array(p, float) for p in ((x0, 0, z0), (x1, 0, z1), (x1, 0, z1 - 90), (x0, 0, z0 - 90))], (0, -1, 0),
                                   [(k * 0.25, 0), (k * 0.25 + 0.25, 0), (k * 0.25 + 0.25, 1), (k * 0.25, 1)])
    ML.save('bunting', X)
    # awning: striped canvas with a scalloped valance; origin on the wall, mid-length, z = 0 is the walkable top
    X = ML.Model(); L = AWN_L / 2
    rbox(X.mesh(M_['stripe']), (-L, -AWN_D, -32), (L, 0, 0), r=3, k=1, tile=256)
    X.mesh(M_['valance']).poly([np.array(p, float) for p in ((-L, -AWN_D - 1, -32), (L, -AWN_D - 1, -32), (L, -AWN_D - 1, -112), (-L, -AWN_D - 1, -112))],
                               (0, -1, 0), [(0, 0), (AWN_L / 256, 0), (AWN_L / 256, 1), (0, 1)])
    for x in (-L + 40, 0, L - 40):
        tube(X.mesh(M_['iron']), [(x, -AWN_D + 30, -34), (x, -6, -260)], 8, nseg=6)
    ML.save('awning', X)
    coll('awning', [((-L, -AWN_D, -32), (L, 0, 0))])
    # pavement A-board (chalk faces +y and -y)
    X = ML.Model()
    for s in (-1, 1):
        P = [np.array(p, float) for p in ((-140, s * 120, 0), (140, s * 120, 0), (140, s * 14, 470), (-140, s * 14, 470))]
        nn = (0, s * 0.97, 0.22)
        X.mesh(M_['chalk']).poly(P if s > 0 else P[::-1], nn, [(1, 1), (0, 1), (0, 0), (1, 0)] if s > 0 else [(0, 0), (1, 0), (1, 1), (0, 1)])   # u to the viewer's right on both faces
        X.mesh(M_['pinev']).poly([p - np.array((0, s * 6, 0)) for p in (P[::-1] if s > 0 else P)], (0, -s * 0.97, -0.22), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for sx in (-1, 1):
        X.mesh(M_['pinev']).poly([np.array(p, float) for p in ((sx * 140, -120, 0), (sx * 140, 120, 0), (sx * 140, 14, 470), (sx * 140, -14, 470))],
                                 (sx, 0, 0), [(0, 1), (1, 1), (0.6, 0), (0.4, 0)])
    rbox(X.mesh(M_['pine']), (-146, -18, 462), (146, 18, 480), r=3, k=1)
    ML.save('a_board', X)
    coll('a_board', [((-140, -120, 0), (140, 120, 160)), ((-140, -84, 160), (140, 84, 320)), ((-140, -46, 320), (140, 46, 480))])
    # bench (seat along x, back at +y), planter tub, flour sacks, cake boxes
    X = ML.Model()
    seat = [((-400, -110, 250), (400, 90, 280))]; back = [((-400, 90, 280), (400, 120, 560))]
    legs = [((x - 20, -100, 0), (x + 20, 110, 250)) for x in (-340, 340)]
    boxes(X, 'pine', seat + back, r=4, tile=192); boxes(X, 'iron', legs, r=4)
    ML.save('bench', X); coll('bench', seat + back + legs)
    X = ML.Model()
    rbox(X.mesh(M_['mint']), (-150, -150, 0), (150, 150, 200), r=8, k=2)
    pic(X.mesh(M_['soil']), (0, 0, 200.6), (0, 0, 1), 270, 270, up=(0, 1, 0))
    for k in range(7):
        a = math.radians(k * 51); r = 70 + (k % 2) * 40
        tube(X.mesh(M_['leaf']), [(r * math.cos(a) * 0.4, r * math.sin(a) * 0.4, 200), (r * math.cos(a), r * math.sin(a), 330 + (k % 3) * 30)], 5, nseg=5)
        sphere(X.mesh(M_['rose' if k % 2 else 'pink']), (r * math.cos(a), r * math.sin(a), 345 + (k % 3) * 30), 30, nu=8, nv=6,
               bump=lambda p, t: 1 + 0.1 * math.sin(t * 6))
    ML.save('planter', X); coll('planter', [((-150, -150, 0), (150, 150, 200))], cyls=[(0, 0, 110, 200, 380)])
    X = ML.Model()
    for (c, sz) in (((0, 0, 0), (130, 90, 110)), ((30, 10, 110), (120, 84, 100))):
        rbox(X.mesh(M_['sack_plain']), (c[0] - sz[0], c[1] - sz[1], c[2]), (c[0] + sz[0], c[1] + sz[1], c[2] + sz[2]), r=36, k=3, tile=256,
             inflate=lambda x, y, z, n: 8 * abs(n[2]))
    pic(X.mesh(M_['sack']), (30, 10, 219), (0, 0, 1), 150, 150, up=(0, 1, 0))      # one stencil on the top sack, never wrapped
    ML.save('flour_sacks', X); coll('flour_sacks', [((-130, -90, 0), (150, 94, 210))])

    # open sack of coffee beans (stands by the counter next to the jump pad): bulging burlap body, rolled rim, beans on top
    X = ML.Model()
    rbox(X.mesh(M_['burlap']), (-130, -100, 0), (130, 100, 340), r=44, k=3, tile=256, inflate=lambda x, y, z, n: 10 * (1 - abs(n[2])))
    for n, w in (((0, -1, 0), 170), ((0, 1, 0), 170), ((1, 0, 0), 110), ((-1, 0, 0), 110)):     # one stencil per side, never wrapped
        pic(X.mesh(M_['coffee_sack']), (n[0] * 141, n[1] * 111, 170), n, w, w)
    for (a, b) in (((-112, -84, 346), (112, -84, 346)), ((112, -84, 346), (112, 84, 346)), ((112, 84, 346), (-112, 84, 346)), ((-112, 84, 346), (-112, -84, 346))):
        tube(X.mesh(M_['burlap']), [a, b], 16, nseg=8)
    pic(X.mesh(M_['beans']), (0, 0, 352), (0, 0, 1), 216, 160, up=(0, 1, 0))
    ML.save('coffee_sack', X); coll('coffee_sack', [((-136, -106, 0), (136, 106, 356))])

    # paper sack of sugar (folded top) and a steel milk churn: floor cover that isn't food lying about
    X = ML.Model()
    rbox(X.mesh(M_['sugar_paper']), (-110, -80, 0), (110, 80, 290), r=30, k=3, tile=256, inflate=lambda x, y, z, n: 8 * (1 - abs(n[2])))
    rbox(X.mesh(M_['sugar_paper']), (-112, -26, 286), (112, 26, 312), r=10, k=2, tile=256)
    for n, w in (((0, -1, 0), 170), ((0, 1, 0), 170), ((1, 0, 0), 120), ((-1, 0, 0), 120)):
        pic(X.mesh(M_['sugar_label']), (n[0] * 119, n[1] * 89, 150), n, w, 190)
    ML.save('sugar_sack', X); coll('sugar_sack', [((-116, -86, 0), (116, 86, 312))])
    X = ML.Model()
    revolve(X.mesh(M_['chrome']), [(0, 0), (80, 0), (86, 10), (86, 196), (62, 244), (52, 262), (66, 280), (66, 292), (0, 292)], n=24)
    for z in (40, 170):
        revolve(X.mesh(M_['chrome']), [(86, z - 6), (90, z), (86, z + 6)], n=24)
    for s in (-1, 1):
        tube(X.mesh(M_['chrome']), [(s * 60, 0, 250), (s * 104, 0, 236), (s * 104, 0, 190), (s * 86, 0, 180)], 6, nseg=6)
    ML.save('milk_churn', X); coll('milk_churn', cyls=[(0, 0, 88, 0, 292)])


def box_stack(name, sizes):
    """a stack of pink cake boxes tied with ribbon; sizes = [(half_x, half_y, height)...] bottom to top"""
    X = ML.Model(); z = 0; bl = []
    for (hx, hy, h) in sizes:
        b = ((-hx, -hy, z), (hx, hy, z + h)); bl.append(b)
        rbox(X.mesh(M_['cakebox']), *b, r=5, k=1, tile=2 * max(hx, hy))
        z += h
    ML.save(name, X); coll(name, bl)
    return z


def tiered_cake(name, tiers):
    """three-tier celebration cake; tiers = [(radius, height)...] bottom to top"""
    X = ML.Model(); z = 0; cy = []
    for R, H in tiers:
        revolve(X.mesh(M_['cream']), [(R, z), (R, z + H - 10), (R - 10, z + H), (0, z + H)], u_tiles=4, n=28)
        revolve(X.mesh(M_['pink']), [(R + 4, z), (R + 6, z + 10), (R + 1, z + 20)], n=28)
        for k in range(0, 12, 1 if R > 120 else 2):
            a = math.radians(k * 30 + R); sphere(X.mesh(M_['rose']), ((R - 6) * math.cos(a), (R - 6) * math.sin(a), z + H), 15, nu=8, nv=5)
        cy.append((0, 0, R, z, z + H)); z += H
    sphere(X.mesh(M_['berry']), (0, 0, z + 20), 26, nu=10, nv=7)
    ML.save(name, X); coll(name, cyls=cy)


def all_models():
    display_unit(); trays(); big_cakes(); tier_stand(); lace_stand(); vases(); single_cupcakes()
    counter(); espresso(); cash_register(); cone_holder(); cake_dome()
    bistro(); table_things(); bread_rack(); breads(); wall_shelves(); jars(); fittings()
    tiered_cake('counter_cake', ((160, 130), (112, 112), (70, 96)))            # fits the counter's 400u depth
    box_stack('boxes_a', [(170, 170, 220), (150, 150, 180)])                     # top 400 = display shelf 2
    box_stack('boxes_b', [(180, 180, 260), (165, 165, 240), (150, 150, 204)])    # top 704 = display shelf 3
    box_stack('boxes_s', [(120, 120, 150), (100, 100, 110)])
