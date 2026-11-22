"""Textures (brush + model materials) and the custom sky for wop_padxmas3 (Padman's Christmas: Under the Tree).
All art is original and generated here. Palette: deep wine carpet, forest-green plastic, warm cream wallpaper,
gingerbread browns, satin ribbons, fairy-light primaries.

    import xm3_art as A
    A.brush(TX)            # every brush texture (TX.add)
    A.materials(TX)        # every model material (TX.material) -> A.M[key] = shader name
    A.sky(out, ns)         # env/<ns>/room_{rt,lf,bk,ft,up,dn}.jpg + the sky stanza text
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from woplib import models as ML, texlib as TL

C, N3, xy, lerp, img = ML.C, ML.N3, ML.xy, ML.lerp, ML.img
M = {}

PAPERS = {  # key: (paper, motif colour, motif, ribbon key)
    'red':    ((176, 24, 34), (240, 196, 80), 'stars', 'gold'),
    'green':  ((28, 104, 58), (236, 236, 228), 'holly', 'red'),
    'blue':   ((34, 60, 150), (226, 234, 250), 'flakes', 'silver'),
    'gold':   ((206, 158, 52), (150, 20, 28), 'dots', 'red'),
    'stripe': ((238, 234, 226), (198, 30, 40), 'stripes', 'green'),
    'purple': ((104, 44, 132), (246, 214, 96), 'stars', 'gold'),
    'kraft':  ((172, 124, 80), (240, 236, 224), 'trees', 'red'),
}
RIBBONS = {'gold': (232, 182, 60), 'red': (196, 22, 36), 'silver': (214, 220, 230), 'green': (30, 130, 70)}
BAUBLES = {'red': (190, 20, 30), 'gold': (220, 170, 50), 'blue': (30, 70, 190), 'silver': (200, 205, 215),
           'green': (20, 130, 60), 'purple': (120, 40, 160)}
BULBS = {'r': (255, 70, 60), 'g': (80, 255, 110), 'b': (90, 140, 255), 'y': (255, 210, 80), 'w': (255, 244, 220)}


def star_pts(cx, cy, r1, r2, n=5, rot=0.0):
    return [(cx + (r1 if k % 2 == 0 else r2) * math.cos(rot - math.pi / 2 + k * math.pi / n),
             cy + (r1 if k % 2 == 0 else r2) * math.sin(rot - math.pi / 2 + k * math.pi / n)) for k in range(2 * n)]


def tiled(im, fn):
    d = ImageDraw.Draw(im); n = im.size[0]
    for ox in (-n, 0, n):
        for oy in (-n, 0, n): fn(d, ox, oy)
    return im


def flake(d, cx, cy, r, col, w=2):
    for k in range(6):
        a = k * math.pi / 3
        d.line((cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)), fill=col, width=w)
        mx, my = cx + r * 0.55 * math.cos(a), cy + r * 0.55 * math.sin(a)
        for s in (-1, 1):
            b = a + s * 0.7
            d.line((mx, my, mx + r * 0.3 * math.cos(b), my + r * 0.3 * math.sin(b)), fill=col, width=w)


def paper(col, mc, motif, seed, n=256):
    im = img(ML.fill(n, col, 3, seed))
    if motif == 'stars':
        tiled(im, lambda d, ox, oy: [d.polygon(star_pts(x + ox, y + oy, r, r * 0.42), fill=mc)
                                     for (x, y, r) in ((50, 50, 18), (180, 90, 12), (110, 190, 16), (230, 220, 10), (20, 200, 8))])
    elif motif == 'holly':
        def f(d, ox, oy):
            for (x, y) in ((50, 60), (180, 150), (110, 220), (220, 30)):
                x += ox; y += oy
                for s in (-1, 1): d.ellipse((x + s * 14 - 12, y - 6, x + s * 14 + 12, y + 6), fill=(16, 70, 34))
                for (bx, by) in ((0, -4), (-5, 3), (5, 3)): d.ellipse((x + bx - 5, y + by - 5, x + bx + 5, y + by + 5), fill=(210, 30, 40))
        tiled(im, f)
    elif motif == 'flakes':
        tiled(im, lambda d, ox, oy: [flake(d, x + ox, y + oy, r, mc, 3)
                                     for (x, y, r) in ((60, 60, 26), (190, 120, 18), (100, 200, 20), (220, 230, 12), (20, 150, 10))])
    elif motif == 'dots':
        tiled(im, lambda d, ox, oy: [d.ellipse((32 + i * 64 + (32 if j % 2 else 0) + ox - 10, 32 + j * 64 + oy - 10,
                                                32 + i * 64 + (32 if j % 2 else 0) + ox + 10, 32 + j * 64 + oy + 10), fill=mc)
                                     for i in range(4) for j in range(4)])
    elif motif == 'stripes':
        d = ImageDraw.Draw(im)
        for k in range(-8, 9):
            o = k * 64
            d.polygon([(o, 0), (o + 28, 0), (o + 28 + n, n), (o + n, n)], fill=mc)
    elif motif == 'trees':
        def f(d, ox, oy):
            for (x, y) in ((50, 70), (180, 40), (120, 170), (230, 200), (30, 230)):
                x += ox; y += oy
                d.polygon([(x, y - 26), (x - 18, y + 14), (x + 18, y + 14)], fill=(30, 110, 56))
                d.polygon(star_pts(x, y - 28, 6, 2.5), fill=(230, 180, 40))
        tiled(im, f)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.5)), np.float32) + N3(n, 1, seed + 3, 2)


def satin(col, n=128):
    x, y = xy(n)
    sh = 0.82 + 0.25 * np.sin(y * math.pi * 2) ** 2 + 0.08 * np.sin(x * 40)
    return C(col) * sh[..., None] + N3(n, 1, 7, 2)


def bark(n=256):
    x, y = xy(n)
    f = ML.noise(n, 3, 11) * 0.6 + np.sin(x * math.pi * 2 * 9 + ML.noise(n, 10, 12) * 2.5) * 0.7
    plates = (np.sin(y * math.pi * 2 * 5 + ML.noise(n, 8, 13) * 3) > 0.85)
    c = lerp(C((70, 46, 30)), C((128, 92, 62)), np.clip(0.5 + f * 0.3, 0, 1)[..., None])
    return np.where(plates[..., None], c * 0.6, c)


def needles(w=256, h=128):
    """alpha card: a twig along the middle with needles slanting forward on both sides"""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(5)
    for i in range(140):
        x = rng.uniform(4, w - 20); s = rng.choice([-1, 1]); L = rng.uniform(28, 56) * (1 - 0.35 * x / w)
        a = math.radians(rng.uniform(30, 60))
        g = int(rng.uniform(70, 130))
        d.line((x, h / 2, x + L * math.cos(a), h / 2 + s * L * math.sin(a)), fill=(18, g, 40, 255), width=3)
    d.line((0, h / 2, w, h / 2), fill=(90, 62, 40, 255), width=5)
    a = np.asarray(im, np.float32)
    return a[..., :3], a[..., 3]


def needle_mass(n=256):
    a = ML.fill(n, (22, 70, 34), 6, 21)
    x, y = xy(n)
    st = np.sin((x * 3 + y) * math.pi * 2 * 14 + ML.noise(n, 3, 22) * 3)
    return a * (0.75 + 0.25 * st)[..., None] + N3(n, 1, 23, 10)


def gingerbread(n=256):
    a = ML.fill(n, (164, 98, 46), 5, 31)
    x, y = xy(n)
    sp = ML.noise(n, 0.6, 32) > 2.2
    a = np.where(sp[..., None], a * 0.6, a)
    return a + ML.noise(n, 12, 33)[..., None] * 10


def candy(n=128):
    x, y = xy(n)
    s = ((x + y) * 4) % 1
    red = (s < 0.38); thin = (s > 0.55) & (s < 0.62)
    c = np.where(red[..., None], C((210, 24, 34)), C((246, 244, 240)))
    return np.where(thin[..., None], C((40, 150, 70)), c)


def cookie(n=256):
    a = ML.fill(n, (196, 140, 70), 4, 41)
    rng = np.random.default_rng(42)
    im = img(a); d = ImageDraw.Draw(im)
    for _ in range(26):
        cx, cy = rng.uniform(0, n, 2); r = rng.uniform(6, 13)
        d.polygon([(cx + r * math.cos(t) * rng.uniform(0.7, 1.1), cy + r * math.sin(t) * rng.uniform(0.7, 1.1))
                   for t in np.linspace(0, 6.28, 7)], fill=(70, 38, 20))
    return np.asarray(im, np.float32) + N3(n, 1, 43, 6)


def carpet(n=256):
    a = ML.fill(n, (110, 22, 34), 2, 51)
    x, y = xy(n)
    pat = (np.abs(((x * 4) % 1) - 0.5) + np.abs(((y * 4) % 1) - 0.5) < 0.12)
    a = np.where(pat[..., None], a * 0.82 + C((30, 20, 6)), a)
    return a + N3(n, 0.7, 52, 9)


def wallpaper(n=256):
    a = ML.fill(n, (226, 208, 170), 4, 61)
    x, y = xy(n)
    stripe = (np.abs(((x * 4) % 1) - 0.5) < 0.05)
    im = img(np.where(stripe[..., None], a * 0.9 + C((0, 8, 0)), a))
    def f(d, ox, oy):
        for (cx, cy) in ((32, 64), (96, 192), (160, 64), (224, 192)):
            cx += ox; cy += oy
            d.ellipse((cx - 14, cy - 22, cx + 14, cy + 22), outline=(170, 150, 110), width=3)
            d.ellipse((cx - 5, cy - 8, cx + 5, cy + 8), fill=(186, 60, 54))
    tiled(im, f)
    return np.asarray(im, np.float32)


def abc_face(ch, bg, fg, n=128):
    a = ML.fill(n, bg, 3, ord(ch))
    im = img(a); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, n - 7, n - 7), outline=tuple(int(v * 0.7) for v in bg), width=6)
    f = ML.font(84, serif=False)
    tw = d.textlength(ch, font=f)
    d.text(((n - tw) / 2, 12), ch, font=f, fill=fg)
    return np.asarray(im, np.float32)


def letter(w=512, h=256):
    a = ML.fill(w, (238, 230, 206), 3, 71, m=h)
    im = img(a); d = ImageDraw.Draw(im)
    f = ML.font(40); g = ML.font(26, serif=True)
    d.text((26, 18), 'Dear Santa,', font=f, fill=(150, 20, 30))
    for i, t in enumerate(('I have been VERY good.', 'Please bring a new Imperius', 'and lots of balloons.', '   love, Padgirl  xx')):
        d.text((40, 80 + i * 38), t, font=g, fill=(40, 40, 70))
    return np.asarray(im, np.float32)


def socket(n=128):
    a = ML.fill(n, (238, 236, 230), 2, 81)
    im = img(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, n - 7, n - 7), 14, outline=(190, 188, 180), width=3)
    for cx in (44, 84):
        d.rectangle((cx - 5, 40, cx + 5, 62), fill=(30, 30, 30))
    d.rectangle((60, 78, 68, 96), fill=(30, 30, 30))
    return np.asarray(im, np.float32)


# ------------------------------------------------------------------------------------------------ brush textures
def brush(TX):
    TX.add('carpet', carpet(), scale=1.0, steps='carpetsteps')
    TX.add('wall', wallpaper(), scale=2.0)
    TX.add('skirting', TL.planks((236, 232, 222), n_planks=2, gap=(200, 196, 186), grain=3), scale=2.0)
    TX.add('stand', TL.solid((34, 112, 58), 3, 91), steps=None)
    TX.add('choc', TL.tiles((92, 52, 30), (64, 34, 18), cols=2, rows=2, offset=0, grout_w=0.06, vary=4))
    TX.add('paper_sheet', paper(*PAPERS['red'][:3], 95), scale=1.0)
    TX.add('paper_back', TL.solid((240, 236, 228), 2, 96))
    TX.add('water', TL.solid((70, 110, 80), 10, 97, 128), 'water', rgb=(0.25, 0.45, 0.3), alpha=0.55)
    TX.add('letter', letter(), 'sign', check_tile=False)
    TX.add('socket', socket(), 'sign', check_tile=False)
    TX.add('grate', grate(), check_tile=True)
    TX.add('felt', TL.fabric((150, 20, 30), weave=96))
    TX.add('china', TL.solid((240, 240, 236), 2, 98))
    TX.add('secret_wall', TL.solid((236, 220, 160), 3, 99))
    TX.add('secret_floor', paper(*PAPERS['gold'][:3], 100))


def grate(n=128):
    x, y = xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    holes = (r < 0.42) & ((np.abs(((x * 6) % 1) - 0.5) < 0.22) & (np.abs(((y * 6) % 1) - 0.5) < 0.22))
    return np.where(holes[..., None], C((10, 14, 10)), C((180, 184, 190))) + N3(n, 1, 101, 6)


# ------------------------------------------------------------------------------------------------ model materials
def materials(TX):
    m = lambda key, arr, kind='lm', **o: M.__setitem__(key, TX.material(key, arr, kind, **o))
    m('plastic_g', TL.solid((34, 112, 58), 3, 201), 'lms', v=0.14, shade=60)
    m('plastic_r', TL.solid((186, 26, 32), 3, 202), 'lms', v=0.16, shade=60)
    m('brass', TL.metal((206, 168, 80), brushed=False), 'lms', v=0.45, shade=60)
    m('chrome', TL.metal((200, 204, 212), brushed=False), 'lms', v=0.5, shade=60)
    m('bark', bark(), shade=80)
    nc, na = needles()
    m('needles', nc, 'alpha', alpha=na, vs=1.2)
    m('needle_mass', needle_mass(), shade=80, sample=32)
    for k, c in BAUBLES.items():
        m('bauble_' + k, TL.solid(c, 2, 210 + len(k)), 'lms', v=0.55, shade=80)
    m('mirror', TL.solid((150, 156, 170), 2, 220), 'lms', v=0.7, shade=80, two=True)
    for k, c in BULBS.items():
        ph = 'rgbyw'.index(k) * 0.2
        m('bulb_' + k, TL.solid(c, 2, 230), 'glow', wave=f'wave square 0.65 0.35 {ph:g} 0.4')
    m('cable', TL.solid((26, 60, 34), 2, 240), shade=60)
    m('thread', TL.solid((230, 200, 120), 1, 241))
    m('ginger', gingerbread(), shade=40)
    m('icing', TL.solid((250, 250, 246), 2, 251), 'lms', v=0.08, shade=70)
    m('candy', candy(), 'lms', v=0.25, shade=70)
    for k, c in (('red', (220, 30, 40)), ('green', (40, 180, 70)), ('yellow', (250, 200, 40)), ('purple', (150, 50, 190)),
                 ('orange', (250, 130, 30))):
        m('gum_' + k, TL.solid(c, 2, 260 + len(k)), 'lms', v=0.3, shade=80)
    m('cardboard', TL.solid((168, 130, 88), 6, 270), shade=30)
    m('cardboard_in', TL.solid((150, 112, 72), 6, 271), shade=30)
    for k, (pc, mc, mo, rb) in PAPERS.items():
        m('paper_' + k, paper(pc, mc, mo, 280 + len(k)), shade=30)
    for k, c in RIBBONS.items():
        m('ribbon_' + k, satin(c), 'lms', v=0.35, shade=70)
    m('tissue', TL.solid((248, 238, 240), 6, 290), shade=80)
    m('paint_red', TL.solid((196, 30, 36), 2, 300), 'lms', v=0.25, shade=60)
    m('paint_green', TL.solid((30, 110, 60), 2, 301), 'lms', v=0.25, shade=60)
    m('paint_black', TL.solid((26, 26, 30), 2, 302), 'lms', v=0.25, shade=60)
    m('paint_blue', TL.solid((40, 70, 170), 2, 303), 'lms', v=0.25, shade=60)
    m('wood', TL.planks((170, 120, 70), n_planks=4), shade=40)
    m('china', TL.solid((244, 244, 240), 2, 310), 'lms', v=0.25, shade=70)
    m('china_rim', TL.stripes((244, 244, 240), (40, 110, 60), n_stripes=1, vertical=False), 'lms', v=0.25, shade=70)
    m('cookie', cookie(), shade=60)
    m('cookie_side', TL.solid((176, 118, 54), 4, 311), shade=60)
    m('milk', TL.solid((250, 250, 246), 2, 312), shade=80)
    m('glass', TL.solid((180, 200, 210), 2, 313), 'glass', two=True)
    m('felt', TL.fabric((150, 20, 30), weave=96), shade=80)
    m('fur', TL.solid((246, 246, 244), 8, 320) , shade=80)
    m('skin', TL.solid((236, 222, 190), 4, 321), shade=60)
    m('slinky', TL.stripes((220, 60, 60), (60, 120, 220), n_stripes=6, vertical=True), 'lms', v=0.5, shade=80)
    m('pine', TL.solid((120, 82, 50), 5, 330), shade=70)
    m('white', TL.solid((236, 236, 232), 2, 331), shade=60)
    m('shard', TL.solid((190, 20, 30), 2, 332), 'lms', v=0.6, shade=20, two=True)
    for ch, bg, fg in (('A', (200, 40, 40), (250, 240, 200)), ('B', (40, 90, 190), (250, 240, 200)), ('C', (40, 150, 70), (250, 240, 200)),
                       ('X', (230, 180, 40), (120, 30, 30)), ('M', (150, 60, 170), (250, 240, 200)), ('S', (230, 120, 30), (40, 30, 30))):
        m('abc_' + ch.lower(), abc_face(ch, bg, fg))
    m('plug', TL.solid((240, 240, 236), 2, 340), shade=60)


# ------------------------------------------------------------------------------------------------ sky: the living room
def room_color(D):
    """the huge out-of-focus living room seen from under the tree: wine carpet below, cream walls, a glowing fireplace
    to the west, a frosty night window to the south, a lamp to the east, bokeh fairy lights everywhere above"""
    D = D / np.linalg.norm(D, axis=-1, keepdims=True)
    z = D[..., 2]; az = np.arctan2(D[..., 1], D[..., 0]); el = np.arcsin(np.clip(z, -1, 1))
    wall = lerp(C((120, 92, 64)), C((52, 36, 30)), np.clip(el / 1.2, 0, 1)[..., None])
    c = np.where((el < -0.02)[..., None], C((60, 14, 20)), wall)
    sk = np.exp(-((el - 0.02) / 0.02) ** 2)                                # skirting board line
    c = c + sk[..., None] * C((70, 66, 60))

    def blob(a0, e0, sa, se, col):
        da = np.angle(np.exp(1j * (az - a0)))
        return np.exp(-(da / sa) ** 2 - ((el - e0) / se) ** 2)[..., None] * C(col)
    c = c + blob(math.pi, 0.08, 0.25, 0.10, (190, 90, 30)) + blob(math.pi, 0.05, 0.10, 0.04, (120, 60, 10))
    # night window (south): blue rectangle with frost and snow
    da = np.angle(np.exp(1j * (az + math.pi / 2)))
    win = (np.abs(da) < 0.35) & (el > 0.15) & (el < 0.6)
    frame = win & ((np.abs(da) > 0.32) | (el < 0.17) | (el > 0.58) | (np.abs(da) < 0.012) | (np.abs(el - 0.375) < 0.01))
    c = np.where(win[..., None], lerp(C((24, 40, 80)), C((60, 80, 130)), np.clip((0.6 - el) / 0.45, 0, 1)[..., None]), c)
    c = np.where(frame[..., None], C((200, 190, 170)), c)
    c = c + blob(0.0, 0.35, 0.18, 0.12, (150, 120, 70))                      # lamp east
    c = c + blob(0.0, 0.28, 0.05, 0.05, (120, 100, 60))
    c = c * (1 - 0.5 * np.clip((el - 0.7) / 0.6, 0, 1))[..., None]          # dark tree above
    return np.clip(c, 0, 255), win


def sky(out, ns, n=512):
    d = os.path.join(out, 'env', ns); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V; one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t),
             'up': (-t, -s, one), 'dn': (t, -s, -one)}
    rng = np.random.default_rng(9)
    bok = [(rng.uniform(-math.pi, math.pi), rng.uniform(0.25, 1.4), rng.uniform(0.02, 0.06),
            list(BULBS.values())[rng.integers(5)]) for _ in range(90)]
    snow = rng.random((n, n))
    for k, (x, y, zz) in faces.items():
        D = np.stack([x, y, zz], -1)
        c, win = room_color(D)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        az = np.arctan2(Dn[..., 1], Dn[..., 0]); el = np.arcsin(np.clip(Dn[..., 2], -1, 1))
        for (a0, e0, r, col) in bok:
            dd = np.hypot(np.angle(np.exp(1j * (az - a0))) * np.cos(el), el - e0)
            disk = np.clip((r - dd) / (r * 0.25), 0, 1) * 0.5 + np.exp(-(dd / (r * 0.6)) ** 2) * 0.25
            c = c + disk[..., None] * C(col) * 0.6
        c = np.where((win & (snow > 0.996))[..., None], C((240, 244, 250)), c)
        img(np.clip(c, 0, 255)).save(os.path.join(d, f'room_{k}.jpg'), quality=93)
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage env/{ns}/room_ft\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 1 0.78 0.55 40 180 30\n\tq3map_skylight 30 3\n\tskyparms env/{ns}/room - -\n}}\n\n')


# ------------------------------------------------------------------------------------------------ round 3: the room + fireplace
def fire_brush(TX):
    TX.add('ceiling', TL.solid((228, 222, 210), 3, 501), scale=4.0)
    TX.add('sill', TL.solid((240, 238, 232), 2, 502), scale=2.0)


def fire_mats(TX):
    m = lambda key, arr, kind='lm', **o: M.__setitem__(key, TX.material(key, arr, kind, **o))
    m('hearth_tile', TL.tiles((120, 60, 50), (60, 40, 34), cols=4, rows=4, offset=0, grout_w=0.03, vary=10), shade=20)
    m('sootbrick', TL.grime(TL.bricks((110, 56, 44), (70, 60, 54)), 0.6), shade=20)
    m('mantel_paint', TL.solid((240, 236, 226), 2, 503), 'lms', v=0.08, shade=40)
    m('plaster', wallpaper(), shade=20)
