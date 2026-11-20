"""Padman's Classroom (wop_padclassroom) - textures (woplib.texlib registry) and custom MD3s. All art is procedural.

Padman scale ~8u per cm (catalog models at 1.0); jumbo pencils and giant rulers are cartoon-sized so they can be
bridges and ramps. Every model is built in model space with z = 0 on the surface it stands on, origin at the centre
of its footprint, front as described per function. COLL[name] holds the weapclip collision (boxes / cylinders in
model space) that build_padclassroom.py places with it, so what bots path over is what players see.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_z

TX = None            # texlib.Textures (set by textures())
M_ = {}              # material key -> model shader name
COLL = {}            # model name -> dict(boxes=[(mn, mx)], cyls=[(cx, cy, r, z0, z1)])

# ------------------------------------------------------------------------------------------------ shared dimensions
DESK_W, DESK_D, DESK_Z = 640, 400, 560          # student desk (x, y, top)
CHAIR_SEAT = 320
TD_W, TD_D, TD_Z = 1280, 600, 608                # teacher's desk
PED_W = 400                                      # teacher's desk pedestal width (x)
BK_D, BK_L, BK_H = 320, 1280, 960                # bookcase depth (x), length (y), height
TANK_CAB_H = 400
CB_W, CB_H = 640, 1600                           # stationery cupboard (square footprint)
GLOBE_Z, GLOBE_R = 700, 250
BIN_R, BIN_L, BIN_T = 176, 480, 16               # tipped bin (collision circumradius, length, wall)
PCASE_R, PCASE_L, PCASE_T = 100, 400, 8          # pencil case
SPIRAL_RIN, SPIRAL_ROUT, SPIRAL_STEP, SPIRAL_TOP, SPIRAL_END = 48, 330, 22.5, TD_Z, 0.0
TURRET = (-96, 0)                                # castle turret centre (model space)
RY90 = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])     # model +z -> +x (rotation, det +1)
RX90 = np.array([[1.0, 0, 0], [0, 0, -1], [0, 1, 0]])     # model +z -> -y


# ================================================================================================= helpers
def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n (towards the viewer), w x h, never mirrored"""
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    P = [c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh]
    M.poly(P, n, [(0, 0), (1, 0), (1, 1), (0, 1)])


def coll(name, boxes=(), cyls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls))


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def canvas(w, h, col):
    im = Image.new('RGB', (w, h), tuple(int(v) for v in col))
    return im, ImageDraw.Draw(im)


def arr(im): return np.asarray(im, np.float32)


def ctext(d, cx, y, s, f, fill, **kw):
    tw = d.textlength(s, font=f)
    d.text((cx - tw / 2, y), s, font=f, fill=fill, **kw)


# ================================================================================================= textures
PAINTS = {'yellow': (250, 200, 40), 'red': (220, 50, 50), 'blue': (50, 110, 220), 'green': (60, 170, 80),
          'orange': (245, 140, 40), 'purple': (140, 70, 200), 'pink': (240, 110, 170), 'teal': (40, 170, 170)}
CHAIR_COLS = ['red', 'blue', 'green', 'yellow']
BOOK_COLS = [(200, 50, 50), (50, 100, 200), (60, 160, 80), (240, 180, 40), (150, 70, 190), (240, 120, 40),
             (40, 160, 170), (230, 100, 150)]


def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('lino', TL.checker((206, 198, 180), (164, 184, 196), n_tiles=4, grout=(150, 146, 138), grout_w=0.008), scale=1.0)
    a('wall', wall_tex(), check_tile=False, scale=(2.0, 2.25))
    a('wall_plain', TL.solid((236, 226, 196), 3, 11, 256), scale=1.0)
    a('ceiling', TL.tiles((200, 200, 196), (160, 160, 156), cols=4, rows=4, offset=0, grout_w=0.02, vary=3), scale=1.0)
    a('sill', TL.planks((236, 232, 222), n_planks=2, gap=(200, 196, 186), grain=3), steps='woodsteps')
    a('frame', TL.solid((246, 246, 246), 2, 18, 64))
    a('ledge', TL.metal((190, 194, 200)))
    a('board', blackboard_art(), 'sign', check_tile=False)
    a('stone', TL.stone((150, 140, 128), cells=16))
    a('gravel', gravel_tex(), scale=0.5)
    a('ruler', ruler_tex(), 'sign', check_tile=False, steps='woodsteps')
    a('water', TL.solid((70, 150, 190), 10, 12, 128), 'water', rgb=(0.35, 0.62, 0.72), alpha=0.45)
    a('fluoro', TL.solid((252, 252, 246), 1, 19, 64), 'neon', rgb=(1.0, 1.0, 0.95), light=120)
    a('det_board', detention_art(), 'sign', check_tile=False)
    a('det_wall', TL.bricks((150, 150, 156), (100, 100, 104), rows=8, cols=4, vary=8), scale=1.0)
    a('det_floor', TL.checker((60, 60, 66), (120, 120, 126), n_tiles=4, grout=(40, 40, 44), grout_w=0.01), scale=1.0)
    a('sky', TL.solid((140, 190, 240), 2, 21, 64), 'raw', shader=sky_stanza(K.ns), check_tile=False)
    for i, (w, h, fn) in enumerate(POSTERS):
        a(f'poster{i}', fn(), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 210, 60), rubber=(50, 60, 90))
    materials()
    return TX


def sky_stanza(ns):
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 1 0.95 0.85 110 270 50\n\tq3map_skylight 70 3\n\tskyparms env/fort-pad512 - -\n}}\n\n')


def wall_tex(w=256, h=1024):
    """two-tone classroom wall, whole wall height in one tile: blue dado up to ~0.9 m, a white rail, cream above.
    Image row 0 = top of the wall (axial t runs down)."""
    im, d = canvas(w, h, (214, 202, 170))
    rail = int(h * (1 - 900 / 2304))
    d.rectangle((0, rail, w, h), fill=(120, 160, 196))
    d.rectangle((0, rail - 10, w, rail + 6), fill=(246, 246, 246))
    d.rectangle((0, h - 40, w, h), fill=(70, 80, 96))                       # skirting
    a_ = arr(im) + TL.N3(256, 4, 12, 3)[:, :, :].repeat(4, 0)[:h, :w]
    return a_


def blackboard_art(w=2048, h=728):
    rng = np.random.default_rng(7)
    base = TL.fill(256, (34, 70, 52), 8, 81)
    im = Image.fromarray(np.uint8(np.clip(base, 0, 255))).resize((w, h))
    d = ImageDraw.Draw(im)
    for _ in range(26):                                                       # eraser smudges
        x, y = rng.integers(0, w), rng.integers(0, h)
        d.ellipse((x - 140, y - 40, x + 140, y + 40), fill=(46, 84, 64))
    chalk = (236, 240, 232)
    f1, f2, f3 = ML.font(110, serif=False), ML.font(70, serif=False), ML.font(58, serif=False)
    d.text((70, 40), 'Padman 101', font=f1, fill=chalk)
    d.text((70, 190), 'Today: Advanced Fragging', font=f2, fill=(250, 220, 120))
    d.text((70, 300), '1 Balloony + 2 Duckies = ?', font=f3, fill=chalk)
    d.text((70, 380), 'Imperius > everything', font=f3, fill=(150, 220, 250))
    d.text((70, 460), 'NO JUMPING ON THE DESKS', font=f3, fill=(250, 150, 150))
    d.text((70, 560), 'Homework: page 42', font=f3, fill=chalk)
    # sums and a drawing on the right
    d.text((1300, 60), '2 + 2 = FRAG', font=f2, fill=chalk)
    d.text((1300, 160), '7 x 6 = 42', font=f2, fill=chalk)
    cx, cy = 1600, 470
    d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), outline=chalk, width=8)       # Padman face doodle
    d.ellipse((cx - 70, cy - 60, cx - 30, cy - 10), fill=chalk); d.ellipse((cx + 30, cy - 60, cx + 70, cy - 10), fill=chalk)
    d.arc((cx - 90, cy - 40, cx + 90, cy + 100), 20, 160, fill=chalk, width=8)
    d.line((cx + 150, cy - 60, cx + 330, cy - 160), fill=(250, 220, 120), width=6)
    d.text((cx + 200, cy - 250), 'PADMAN!', font=f3, fill=(250, 220, 120))
    a_ = arr(im)
    return a_ + TL.N3(256, 1, 82, 5).repeat(8, 0).repeat(8, 1)[:h, :w]


def detention_art(w=1024, h=512):
    im, d = canvas(w, h, (30, 64, 48))
    f = ML.font(40, serif=False)
    for k in range(9):
        d.text((40 + (k % 2) * 6, 30 + k * 52), 'I will not frag in class.', font=f, fill=(232, 236, 228))
    d.text((680, 440), '- Mr. Pad', font=ML.font(36, serif=False), fill=(250, 220, 120))
    return arr(im)


def gravel_tex(n=256):
    rng = np.random.default_rng(13)
    im, d = canvas(n, n, (60, 70, 80))
    pal = [(230, 120, 60), (60, 160, 230), (240, 220, 80), (90, 200, 120), (220, 220, 230), (240, 110, 170)]
    for _ in range(420):
        x, y = rng.integers(-8, n + 8), rng.integers(-8, n + 8)
        r = rng.integers(5, 11); c = pal[rng.integers(0, len(pal))]
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=c, outline=(40, 40, 46))
    return arr(im)


def ruler_tex(w=256, h=1024):
    """a wooden ruler seen from above: long axis = image height (v), cm marks every 8u-ish, numbers"""
    base = TL.planks((222, 184, 120), n_planks=1, grain=10, vertical=True, n=256)
    im = Image.fromarray(np.uint8(np.clip(base, 0, 255))).resize((w, h))
    d = ImageDraw.Draw(im)
    f = ML.font(26, serif=False)
    for k in range(0, 101):
        y = int(k * (h - 1) / 100)
        L = 70 if k % 10 == 0 else (46 if k % 5 == 0 else 26)
        d.line((0, y, L, y), fill=(40, 30, 24), width=3)
        d.line((w - L, y, w, y), fill=(40, 30, 24), width=3)
        if k % 10 == 0 and 0 < k < 100:
            d.text((86, y - 14), str(k // 10), font=f, fill=(40, 30, 24))
    d.rectangle((0, 0, w - 1, h - 1), outline=(150, 110, 70), width=4)
    return arr(im)


def poster_alphabet(w=2048, h=256):
    im, d = canvas(w, h, (250, 248, 236))
    f = ML.font(150, serif=False)
    cols = list(PAINTS.values())
    letters = 'AaBbCcDdEeFfGgHhIi'
    for k, ch in enumerate(letters):
        x = 30 + k * 112
        d.rounded_rectangle((x, 30, x + 100, 226), 14, fill=cols[k % len(cols)])
        ctext(d, x + 50, 40, ch, f, (255, 255, 255), stroke_width=3, stroke_fill=(40, 40, 40))
    return arr(im)


def poster_alphabet2(w=2048, h=256):
    im, d = canvas(w, h, (250, 248, 236))
    f = ML.font(150, serif=False)
    cols = list(PAINTS.values())[::-1]
    letters = 'JjKkLlMmNnOoPpQqRr'
    for k, ch in enumerate(letters):
        x = 30 + k * 112
        d.rounded_rectangle((x, 30, x + 100, 226), 14, fill=cols[k % len(cols)])
        ctext(d, x + 50, 40, ch, f, (255, 255, 255), stroke_width=3, stroke_fill=(40, 40, 40))
    return arr(im)


def poster_map(w=1024, h=640):
    """an invented world map (blobby continents, not a real map)"""
    a_ = continents(w, h, seed=4)
    im = Image.fromarray(np.uint8(np.clip(a_, 0, 255)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(120, 80, 40), width=14)
    ctext(d, w / 2, 20, 'THE WORLD OF PADMAN', ML.font(48, serif=True), (40, 40, 60))
    return arr(im)


def continents(w, h, seed=4, ocean=(70, 140, 210), land=(110, 180, 90), sand=(220, 200, 140), grid=True):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    f = np.zeros((h, w), np.float32)
    for _ in range(14):
        cx, cy, r = rng.uniform(0, w), rng.uniform(h * 0.15, h * 0.85), rng.uniform(w * 0.05, w * 0.14)
        for ox in (-w, 0, w):
            f += np.exp(-(((x - cx - ox) / r) ** 2 + ((y - cy) / (r * 0.8)) ** 2))
    f += ML.noise(256, 6, seed + 3)[np.arange(h) % 256][:, np.arange(w) % 256] * 0.18
    im = np.empty((h, w, 3), np.float32)
    im[:] = ocean
    im[f > 0.55] = sand
    im[f > 0.62] = land
    im[f > 1.3] = (90, 150, 70)
    if grid:
        im[(np.abs((x / w * 12) % 1 - 0.5) > 0.49) | (np.abs((y / h * 6) % 1 - 0.5) > 0.49)] *= 0.8
    return im


def poster_times(w=640, h=896):
    im, d = canvas(w, h, (255, 244, 200))
    ctext(d, w / 2, 24, 'TIMES TABLES', ML.font(60, serif=False), (200, 60, 40))
    f = ML.font(44, serif=False)
    for k in range(1, 11):
        d.text((90, 90 + k * 72), f'{k} x 7 = {k * 7}', font=f, fill=(40, 40, 80))
    d.rectangle((0, 0, w - 1, h - 1), outline=(200, 60, 40), width=12)
    return arr(im)


def poster_rules(w=640, h=896):
    im, d = canvas(w, h, (220, 240, 255))
    ctext(d, w / 2, 24, 'CLASS RULES', ML.font(64, serif=False), (30, 80, 170))
    f = ML.font(36, serif=False)
    rules = ['1. Be kind to ducks', '2. Share your Balloony', '3. No camping', '4. Hands up first',
             '5. Respawn quietly', '6. Tidy your desk', '7. Have fun!']
    for k, r in enumerate(rules):
        d.text((50, 140 + k * 100), r, font=f, fill=(30, 40, 70))
    d.rectangle((0, 0, w - 1, h - 1), outline=(30, 80, 170), width=12)
    return arr(im)


def poster_drawing(seed):
    def f(w=512, h=640):
        rng = np.random.default_rng(seed)
        im, d = canvas(w, h, (252, 252, 248))
        d.rectangle((0, h * 0.72, w, h), fill=(120, 200, 90))                      # grass
        d.ellipse((w * 0.72, 30, w * 0.95, 30 + w * 0.23), fill=(255, 210, 40))     # sun
        for k in range(8):
            a = k * math.pi / 4
            cx, cy = w * 0.835, 30 + w * 0.115
            d.line((cx + math.cos(a) * 80, cy + math.sin(a) * 80, cx + math.cos(a) * 120, cy + math.sin(a) * 120),
                   fill=(255, 190, 30), width=8)
        hx = rng.integers(60, 200)
        d.rectangle((hx, h * 0.45, hx + 200, h * 0.72), fill=tuple(int(v) for v in BOOK_COLS[seed % 8]), outline=(30, 30, 30), width=5)
        d.polygon([(hx - 20, h * 0.45), (hx + 100, h * 0.3), (hx + 220, h * 0.45)], fill=(200, 60, 50), outline=(30, 30, 30))
        d.rectangle((hx + 80, h * 0.6, hx + 120, h * 0.72), fill=(120, 80, 40))
        px = w * 0.7                                                                 # stick Padman
        d.ellipse((px - 30, h * 0.5, px + 30, h * 0.5 + 60), outline=(30, 30, 30), width=6)
        d.line((px, h * 0.5 + 60, px, h * 0.66), fill=(30, 30, 30), width=6)
        d.line((px - 40, h * 0.58, px + 40, h * 0.58), fill=(30, 30, 30), width=6)
        d.line((px, h * 0.66, px - 30, h * 0.72), fill=(30, 30, 30), width=6)
        d.line((px, h * 0.66, px + 30, h * 0.72), fill=(30, 30, 30), width=6)
        names = ['Lilly, 7', 'Tim, 6', 'Ava, 8', 'Max, 7']
        d.text((20, h - 60), names[seed % 4], font=ML.font(36, serif=False), fill=(60, 60, 200))
        return arr(im)
    return f


POSTERS = [(2048, 256, poster_alphabet), (2048, 256, poster_alphabet2), (1024, 640, poster_map),
           (640, 896, poster_times), (640, 896, poster_rules)] + [(512, 640, poster_drawing(s)) for s in range(4)]


def desk_top_tex(n=512, seed=0):
    base = TL.planks((214, 186, 146), n_planks=3, grain=6, n=256)
    im = Image.fromarray(np.uint8(np.clip(base, 0, 255))).resize((n, n))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed + 40)
    ink = (60, 60, 120)
    doodles = ['PADMAN WAS HERE', 'GG', 'BALLOONY 4 EVER', 'L + P', 'BOOM!', 'DUCKS RULE']
    f = ML.font(34, serif=False)
    for k in range(2):
        s = doodles[(seed * 2 + k) % len(doodles)]
        d.text((rng.integers(20, 200), rng.integers(30, 420)), s, font=f, fill=ink)
    x, y = rng.integers(300, 440), rng.integers(80, 400)
    d.polygon([(x, y + 20), (x - 30, y - 10), (x - 15, y - 30), (x, y - 15), (x + 15, y - 30), (x + 30, y - 10)], outline=(200, 40, 60), width=4)
    d.rectangle((0, 0, n - 1, n - 1), outline=(90, 70, 50), width=8)
    return arr(im)


def pencil_paint(col, n=128):
    """hexagonal pencil paint: lengthwise facet stripes (u runs round, v along) + a gold brand band"""
    x, y = TL.xy(n)
    c = np.zeros((n, n, 3), np.float32) + col
    c *= (0.86 + 0.14 * np.abs(np.cos(x * math.pi * 6)))[..., None]
    band = (y > 0.08) & (y < 0.12)
    c[band] = (230, 190, 60)
    return c + TL.N3(n, 1, 90, 3)


def book_spines(col, n=128):
    c = TL.fill(n, col, 3, 91)
    x, y = TL.xy(n)
    c[(y > 0.12) & (y < 0.16)] = (240, 220, 140); c[(y > 0.84) & (y < 0.88)] = (240, 220, 140)
    return c


def crayon_box_tex(w=512, h=256):
    im, d = canvas(w, h, (250, 210, 40))
    for k in range(10):
        d.polygon([(k * 52, h), (k * 52 + 26, 0), (k * 52 + 52, h)], fill=(250, 196, 30))
    d.rectangle((0, 70, w, 190), fill=(40, 140, 60))
    ctext(d, w / 2, 82, 'PADOLA', ML.font(84, serif=False), (250, 240, 60), stroke_width=4, stroke_fill=(20, 60, 30))
    ctext(d, w / 2, 200, '24 JUMBO CRAYONS', ML.font(34, serif=False), (40, 40, 40))
    return arr(im)


def clock_face(n=256):
    im, d = canvas(n, n, (250, 250, 246))
    d.ellipse((4, 4, n - 4, n - 4), outline=(30, 30, 30), width=10)
    f = ML.font(28, serif=False)
    for k in range(12):
        a = math.radians(k * 30 - 60)
        r = n * 0.38
        ctext(d, n / 2 + math.cos(a) * r, n / 2 + math.sin(a) * r - 16, str(k + 1), f, (30, 30, 30))
    for k, (ln, wd, ang) in enumerate(((0.22, 8, -50), (0.32, 6, 100))):       # hour + minute hands (painted)
        a = math.radians(ang)
        d.line((n / 2, n / 2, n / 2 + math.cos(a) * n * ln, n / 2 + math.sin(a) * n * ln), fill=(20, 20, 20), width=wd)
    d.ellipse((n / 2 - 8, n / 2 - 8, n / 2 + 8, n / 2 + 8), fill=(20, 20, 20))
    return arr(im)


def globe_tex(w=512, h=256):
    return continents(w, h, seed=11, ocean=(60, 120, 200), land=(120, 190, 90), sand=(225, 205, 145))


def coins_tex(n=128):
    rng = np.random.default_rng(5)
    im, d = canvas(n, n, (160, 110, 20))
    for _ in range(60):
        x, y, r = rng.integers(0, n), rng.integers(0, n), rng.integers(6, 12)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(250, 210, 60), outline=(180, 130, 20))
    return arr(im)


def bubbles_tex(n=128):
    rng = np.random.default_rng(3)
    im, d = canvas(n, n, (0, 0, 0))
    for _ in range(26):
        x, y, r = rng.integers(20, n - 20), rng.integers(0, n), rng.integers(3, 9)
        for oy in (-n, 0, n):
            d.ellipse((x - r, y + oy - r, x + r, y + oy + r), outline=(150, 200, 230), width=2)
    return arr(im)


def lunch_tex(w=256, h=128):
    im, d = canvas(w, h, (60, 170, 230))
    for k in range(12):
        x = (k * 47) % w; y = (k * 31) % h
        d.ellipse((x, y, x + 18, y + 18), fill=(250, 250, 250))
    return arr(im)


def ream_tex(w=256, h=128):
    im, d = canvas(w, h, (246, 246, 240))
    d.rectangle((0, 40, w, 88), fill=(40, 110, 200))
    ctext(d, w / 2, 46, 'PAD PAPER A4', ML.font(30, serif=False), (255, 255, 255))
    return arr(im)


def plane_tex(n=128):
    im, d = canvas(n, n, (246, 246, 240))
    for k in range(6):
        d.line((0, 20 + k * 20, n, 20 + k * 20), fill=(170, 190, 230), width=2)
    return arr(im)


def materials():
    m('desk_top0', desk_top_tex(seed=0), shade=20)
    m('desk_top1', desk_top_tex(seed=1), shade=20)
    m('desk_top2', desk_top_tex(seed=2), shade=20)
    m('desk_top3', desk_top_tex(seed=3), shade=20)
    m('steel', TL.metal((170, 176, 184)), 'lms', v=0.22, shade=50)
    m('steel_dark', TL.metal((70, 74, 80)), 'lms', v=0.12, shade=40)
    for c in CHAIR_COLS:
        m(f'plastic_{c}', TL.solid(PAINTS[c], 2, 30 + len(c)), 'lms', v=0.10, shade=60, tag=c)
    m('oak', TL.planks((170, 120, 76), n_planks=4, grain=8, vertical=True), shade=20)
    m('oakh', TL.planks((170, 120, 76), n_planks=4, grain=8), shade=20, tag='h')
    m('pine', TL.planks((214, 178, 122), n_planks=4, grain=8, vertical=True), shade=20)
    m('pineh', TL.planks((214, 178, 122), n_planks=4, grain=8), shade=20, tag='h')
    m('laminate', TL.solid((226, 222, 210), 2, 33), shade=20)
    m('cupboard', TL.planks((150, 196, 220), n_planks=3, gap=(120, 160, 186), grain=2, vertical=True), shade=20)
    m('cb_sign', TL.label('STATIONERY', 512, 256, (250, 250, 240), (40, 60, 120), border=(40, 60, 120)), shade=20)
    m('blotter', TL.fabric((40, 110, 70), weave=48), shade=20)
    m('chair_fab', TL.fabric((36, 40, 52), weave=96), shade=60)
    m('black', TL.solid((28, 28, 32), 2, 31), shade=40)
    m('white', TL.solid((240, 240, 236), 2, 34), shade=40)
    m('paper', TL.solid((246, 246, 240), 2, 40, 64), shade=60, two=True)
    m('pages', TL.stripes((244, 242, 232), (220, 216, 204), n_stripes=32, vertical=False), shade=20)
    for i, col in enumerate(BOOK_COLS):
        m(f'book{i}', book_spines(col), shade=20)
    m('pencil_wood', TL.planks((226, 188, 140), n_planks=1, grain=12, vertical=True), shade=60)
    m('graphite', TL.solid((50, 50, 56), 2, 41, 64), 'lms', v=0.2, shade=60)
    m('ferrule', TL.metal((200, 190, 150)), 'lms', v=0.35, shade=60)
    m('eraser', TL.solid((240, 130, 150), 2, 42, 64), shade=60)
    for c in ('yellow', 'red', 'blue', 'green', 'orange', 'purple'):
        m(f'pencil_{c}', pencil_paint(PAINTS[c]), shade=30, tag=c)
    for c in ('red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'teal'):
        m(f'crayon_{c}', TL.solid(PAINTS[c], 2, 50 + len(c), 64), shade=60, tag='cr' + c)
    m('ruler_m', ruler_tex(256, 512), shade=20)
    m('crayon_box', crayon_box_tex(), shade=20)
    m('cardboard', TL.fill(128, (180, 140, 96), 6, 72), shade=20)
    m('bin_blue', TL.solid((40, 110, 190), 2, 43), 'lms', v=0.12, shade=60)
    m('crumple', TL.fill(128, (240, 240, 232), 2, 45) + ML.N3(128, 1.5, 46, 18), shade=80)
    m('pcase', TL.fabric((150, 60, 170), weave=64), shade=60)
    m('zip', TL.metal((200, 200, 210)), 'lms', v=0.3, shade=40)
    m('lunch', lunch_tex(), 'lms', v=0.08, shade=40)
    m('radiator', TL.solid((240, 240, 240), 2, 47), shade=40, tag='rad')
    m('fluoro_m', TL.solid((255, 255, 248), 1, 48, 32), 'glow')
    m('clock', clock_face(), shade=20)
    m('clock_red', TL.solid((220, 40, 40), 1, 49, 32), shade=20)
    m('globe', globe_tex(), shade=60)
    m('brass', TL.metal((200, 160, 70), brushed=False), 'lms', v=0.4, shade=60)
    m('chalk', TL.solid((246, 246, 240), 2, 52, 64), shade=60)
    m('felt', TL.fabric((90, 90, 96), weave=64), shade=40)
    m('castle', TL.stone((190, 170, 140), cells=10), shade=30)
    m('castle_dark', TL.solid((30, 30, 40), 1, 53, 32), shade=30)
    m('coins', coins_tex(), 'glow')
    m('chest', TL.planks((120, 70, 40), n_planks=3, grain=8), shade=30)
    m('fish_orange', TL.solid((250, 130, 30), 2, 54, 64), shade=60, two=True)
    m('fish_blue', TL.solid((60, 160, 240), 2, 55, 64), shade=60, two=True)
    m('fish_eye', TL.solid((20, 20, 20), 1, 56, 32), shade=60)
    m('bubbles', bubbles_tex(), 'add', tcmod='scroll 0 0.6')
    m('ream', ream_tex(), shade=20)
    m('plane', plane_tex(), shade=60, two=True)
    m('string', TL.solid((230, 230, 230), 1, 57, 32), shade=60)
    m('bag_red', TL.fabric((190, 50, 50), weave=64), shade=70)
    m('bag_blue', TL.fabric((40, 80, 170), weave=64), shade=70)
    m('bag_green', TL.fabric((50, 140, 80), weave=64), shade=70)
    m('apple_red', TL.solid((200, 30, 40), 2, 58, 64), 'lms', v=0.15, shade=70)
    m('recycle', TL.label('RECYCLE', 256, 256, (40, 110, 190), (250, 250, 250)), shade=20)
    m('sticker', TL.pad_sticker(), 'alpha', alpha=TL.disc_alpha())
    m('glue', TL.solid((250, 250, 250), 2, 59, 64), shade=60)
    m('glue_cap', TL.solid((240, 120, 30), 2, 60, 64), shade=60)


# ================================================================================================= models
def all_models():
    for i in range(4): student_desk(i)
    for c in CHAIR_COLS: school_chair(c)
    teacher_desk(); teacher_chair(); blackboard_ledge(); bookcase(); tank_cabinet(); castle(); chest()
    cupboard(); globe_stand(); globe_ball(); tipped_bin(); paper_balls(); pencil_bridge(); ruler_bridge()
    spiral_books(); jumbo_pencil(); pencil_case(); lunchbox(); crayon_box(); radiator(); fluoro_panel()
    clock(); clock_hand(); plane_mobile(); fish_ring('fish_big', 150, 5, 'fish_orange', 1.0); fish_ring('fish_small', 110, 7, 'fish_blue', 0.7)
    bubbler(); for_bag = [schoolbag(c) for c in ('red', 'blue', 'green')]
    paper_stack(); pencil_cup(); duster(); chalk_sticks(); eraser(); glue_bottle(); detention_desk(); open_book(); cover_props(); more_cover(); pad_skins()


def student_desk(i):
    """single school desk, origin footprint centre, chair side -y: doodled laminate top, steel tube frame, a book tray
    under the top with a back panel (closed on +y)"""
    X = ML.Model(); W, D, Z = DESK_W / 2, DESK_D / 2, DESK_Z
    top = ((-W, -D, Z - 28), (W, D, Z))
    rbox(X.mesh(M_[f'desk_top{i}']), *top, r=6, k=2, tile=512)
    st = M_['steel']
    legs = [(-W + 30, -D + 30), (W - 30, -D + 30), (-W + 30, D - 30), (W - 30, D - 30)]
    for (x, y) in legs:
        tube(X.mesh(st), [(x, y, 8), (x, y, Z - 28)], 13, nseg=10)
        rbox(X.mesh(M_['black']), (x - 16, y - 16, 0), (x + 16, y + 16, 10), r=3, k=1)
    tube(X.mesh(st), [(-W + 30, -D + 30, 90), (-W + 30, D - 30, 90)], 9, nseg=8)
    tube(X.mesh(st), [(W - 30, -D + 30, 90), (W - 30, D - 30, 90)], 9, nseg=8)
    tray = ((-W + 46, -D + 50, 372), (W - 46, D - 18, 384))
    back = ((-W + 46, D - 34, 384), (W - 46, D - 18, Z - 28))
    rbox(X.mesh(M_['steel_dark']), *tray, r=2, k=1); rbox(X.mesh(M_['steel_dark']), *back, r=2, k=1)
    # a couple of books in the tray
    rbox(X.mesh(M_['book1']), (-200, -100, 384), (40, 120, 412), r=3, k=1)
    rbox(X.mesh(M_['book3']), (60, -60, 384), (260, 130, 404), r=3, k=1)
    ML.save(f'student_desk{i}', X)
    b = [top, tray, back] + [((x - 14, y - 14, 0), (x + 14, y + 14, Z - 28)) for (x, y) in legs]
    coll(f'student_desk{i}', b)


def school_chair(col):
    """stacking school chair, origin footprint centre, sitter faces -y (back panel at +y)"""
    X = ML.Model(); S = CHAIR_SEAT
    pl, st = M_[f'plastic_{col}'], M_['steel']
    seat = ((-180, -180, S - 24), (180, 170, S))
    back = ((-170, 150, S + 60), (170, 176, S + 340))
    rbox(X.mesh(pl), *seat, r=12, k=3)
    rbox(X.mesh(pl), *back, r=12, k=3)
    legs = [(-160, -160), (160, -160), (-160, 160), (160, 160)]
    for (x, y) in legs:
        tube(X.mesh(st), [(x, y, 6), (x, y, S - 24)], 11, nseg=8)
        rbox(X.mesh(M_['black']), (x - 14, y - 14, 0), (x + 14, y + 14, 8), r=3, k=1)
    for x in (-160, 160):                                                        # back uprights
        tube(X.mesh(st), [(x, 163, S), (x, 163, S + 300)], 10, nseg=8)
    ML.save(f'chair_{col}', X)
    coll(f'chair_{col}', [seat, back] + [((x - 12, y - 12, 0), (x + 12, y + 12, S - 24)) for (x, y) in legs]
         + [((x - 10, 153, S), (x + 10, 173, S + 60)) for x in (-160, 160)])


def teacher_desk():
    """teacher's desk, origin footprint centre, class side -y. Two pedestals (drawers face +y, the teacher's side),
    knee hole open both ways (walk-through), oak top with a green blotter"""
    X = ML.Model(); W, D, Z = TD_W / 2, TD_D / 2, TD_Z
    top = ((-W, -D, Z - 32), (W, D, Z))
    rbox(X.mesh(M_['oakh']), *top, r=6, k=2, tile=512)
    pic(X.mesh(M_['blotter']), (0, 0, Z + 0.6), (0, 0, 1), 640, 380, up=(0, 1, 0))
    peds = [((-W, -D + 8, 0), (-W + PED_W, D - 8, Z - 32)), ((W - PED_W, -D + 8, 0), (W, D - 8, Z - 32))]
    for a, b in peds:
        rbox(X.mesh(M_['oak']), a, b, r=4, k=1, tile=256)
        x0, x1 = a[0], b[0]
        for k in range(3):                                                        # drawer fronts + handles (teacher side)
            z0 = 24 + k * 180
            rbox(X.mesh(M_['oakh']), (x0 + 16, D - 8, z0), (x1 - 16, D + 4, z0 + 168), r=3, k=1)
            rbox(X.mesh(M_['steel']), ((x0 + x1) / 2 - 50, D + 4, z0 + 120), ((x0 + x1) / 2 + 50, D + 14, z0 + 134), r=4, k=1)
    # modesty rail (thin, high) so the knee hole reads as a desk from the class side
    rail = ((-W + PED_W, -D + 8, Z - 112), (W - PED_W, -D + 24, Z - 32))
    rbox(X.mesh(M_['oak']), *rail, r=2, k=1)
    ML.save('teacher_desk', X)
    coll('teacher_desk', [top, rail] + peds)


def teacher_chair():
    """office chair, origin at the column, sitter faces -y (back at +y)"""
    X = ML.Model()
    bl = M_['black']
    for k in range(5):
        a = math.radians(90 + k * 72)
        tube(X.mesh(bl), [(0, 0, 40), (math.cos(a) * 200, math.sin(a) * 200, 30)], 14, nseg=8)
        sphere(X.mesh(bl), (math.cos(a) * 200, math.sin(a) * 200, 16), 16, nu=10, nv=6)
    tube(X.mesh(M_['steel']), [(0, 0, 40), (0, 0, 370)], 22, nseg=12)
    seat = ((-200, -200, 370), (200, 190, 430))
    back = ((-190, 140, 470), (190, 180, 760))
    rbox(X.mesh(M_['chair_fab']), *seat, r=24, k=3)
    rbox(X.mesh(M_['chair_fab']), *back, r=26, k=3)
    tube(X.mesh(bl), [(0, 160, 400), (0, 170, 480)], 14, nseg=8)
    for x in (-210, 210):                                                         # arm rests
        tube(X.mesh(bl), [(x, -60, 430), (x, -60, 540), (x, 120, 540)], 10, nseg=8)
    ML.save('teacher_chair', X)
    coll('teacher_chair', [seat, back, ((-24, -24, 0), (24, 24, 370))])


def blackboard_ledge():
    """the chalk tray: model space x along the board, y = depth (0 at the wall, -160 into the room), top at z 0.
    Board frame is a separate sign brush; the tray carries brackets, chalk and the duster is a prop."""
    X = ML.Model()
    tray = ((-1440, -160, -32), (1440, 0, 0))
    rbox(X.mesh(M_['steel']), *tray, r=4, k=2, tile=256)
    for x in np.linspace(-1360, 1360, 7):                                         # brackets under the tray
        P = [(x - 10, -150, -32), (x + 10, -150, -32), (x + 10, -4, -32), (x - 10, -4, -32)]
        rbox(X.mesh(M_['steel_dark']), (x - 10, -40, -200), (x + 10, -4, -32), r=2, k=1)
        tube(X.mesh(M_['steel_dark']), [(x, -140, -36), (x, -20, -190)], 7, nseg=6)
    ML.save('chalk_tray', X)
    coll('chalk_tray', [tray])


def bookcase():
    """low classroom bookcase, origin footprint centre, back against the wall at -x, open front +x. Four bays along y,
    three shelves; the bottom of bay 2 is left open as a walk-in nook"""
    X = ML.Model(); D, L, H = BK_D / 2, BK_L / 2, BK_H
    pn, ph = M_['pine'], M_['pineh']
    parts = [((-D, -L, 0), (D, L, 16)), ((-D, -L, H - 16), (D, L, H)), ((-D, -L, 16), (-D + 16, L, H - 16)),
             ((-D + 16, -L, 16), (D, -L + 16, H - 16)), ((-D + 16, L - 16, 16), (D, L, H - 16))]
    for z in (320, 624):
        parts.append(((-D + 16, -L + 16, z), (D, L - 16, z + 16)))
    divs = [-328, -8, 312]
    for y in divs:
        for (z0, z1) in ((16, 320), (336, 624), (640, H - 16)):
            parts.append(((-D + 16, y, z0), (D, y + 16, z1)))
    for a, b in parts: rbox(X.mesh(ph if a[2] == b[2] - 16 else pn), a, b, r=2, k=1, tile=256)
    # books: rows in every compartment except the walk-in nook (bay 2, bottom)
    bays = [(-L + 16, -328), (-312, -8), (8, 312), (328, L - 16)]
    levels = [(16, 320), (336, 624), (640, H - 16)]
    rng = np.random.default_rng(21)
    blocks = []
    for bi, (y0, y1) in enumerate(bays):
        for li, (z0, z1) in enumerate(levels):
            if bi == 2 and li == 0:
                # a few books leaning in the nook (low, at the back)
                rbox(X.mesh(M_['book2']), (-D + 18, y0 + 10, z0), (-D + 220, y0 + 50, z0 + 210), r=3, k=1)
                rbox(X.mesh(M_['book5']), (-D + 18, y0 + 52, z0), (-D + 200, y0 + 84, z0 + 190), r=3, k=1)
                blocks.append(((-D + 16, y0, z0), (-D + 222, y0 + 86, z0 + 212)))
                continue
            y = y0 + 4
            hmax = 0
            while y < y1 - 30:
                t = rng.integers(22, 44); h = rng.integers(int((z1 - z0) * 0.62), int((z1 - z0) * 0.9))
                dep = rng.integers(200, 260)
                if y + t > y1 - 4: break
                rbox(X.mesh(M_[f'book{rng.integers(0, 8)}']), (-D + 18, y, z0), (-D + 18 + dep, y + t, z0 + h), r=3, k=1, tile=128)
                y += t + 2; hmax = max(hmax, h)
            blocks.append(((-D + 16, y0, z0), (-D + 280, y1, z0 + hmax)))
    ML.save('bookcase', X)
    coll('bookcase', parts + blocks)


def tank_cabinet():
    """the fish tank's cabinet: origin footprint centre, doors face +x"""
    X = ML.Model(); D, L, H = 240, 720, TANK_CAB_H
    body = ((-D, -L, 0), (D, L, H))
    rbox(X.mesh(M_['oak']), (-D, -L, 20), (D, L, H), r=4, k=1, tile=256)
    rbox(X.mesh(M_['black']), (-D + 10, -L + 10, 0), (D - 10, L - 10, 20), r=2, k=1)
    for k in range(4):
        y0 = -L + 12 + k * 357
        rbox(X.mesh(M_['oakh']), (D, y0, 36), (D + 8, y0 + 345, H - 16), r=3, k=1)
        rbox(X.mesh(M_['steel']), (D + 8, y0 + 300, 220), (D + 18, y0 + 314, 320), r=4, k=1)
    ML.save('tank_cabinet', X)
    coll('tank_cabinet', [body])


def castle():
    """aquarium castle at the north end of the tank: model space x across the tank (wall at -x), y along it (+y =
    north), z 0 = gravel top. The walkable top (CASTLE_TOP over the gravel) continues the ramp onto the bookcase.
    Collision is added by the build (tower box + platform) - this is the visual."""
    X = ML.Model(); c = M_['castle']
    H = 976 - 432
    rbox(X.mesh(c), (-144, -40, 0), (144, 40, H - 16), r=6, k=2, tile=128)       # tower block under the platform
    rbox(X.mesh(c), (-144, -40, H - 16), (144, 72, H), r=3, k=1, tile=128)       # platform slab (over the glass)
    revolve(X.mesh(c), [(44, H), (44, H + 140), (56, H + 140), (56, H + 190), (0, H + 190)], n=16, u_tiles=2,
            cx=TURRET[0], cy=TURRET[1])                                            # wall-side turret over the platform
    revolve(X.mesh(M_['crayon_red']), [(58, H + 190), (0, H + 310)], n=16, cx=TURRET[0], cy=TURRET[1])
    for z in (120, 300):                                                           # arched windows (dark)
        for x in (-80, 0, 80):
            pic(X.mesh(M_['castle_dark']), (x, -40.8, z), (0, -1, 0), 40, 70)
    pic(X.mesh(M_['castle_dark']), (40, -40.9, 40), (0, -1, 0), 90, 110)        # gate
    ML.save('castle', X)


def chest():
    """open treasure chest on the tank floor (the secret): origin footprint centre, lid hinged at +y, opening -y"""
    X = ML.Model(); W, D, H = 80, 56, 64
    wl = [((-W, -D, 0), (W, -D + 8, H)), ((-W, D - 8, 0), (W, D, H)), ((-W, -D + 8, 0), (-W + 8, D - 8, H)),
          ((W - 8, -D + 8, 0), (W, D - 8, H)), ((-W + 8, -D + 8, 0), (W - 8, D - 8, 8))]
    for a, b in wl: rbox(X.mesh(M_['chest']), a, b, r=2, k=1, tile=64)
    pic(X.mesh(M_['coins']), (0, 0, 40), (0, 0, 1), 2 * W - 16, 2 * D - 16, up=(0, 1, 0))
    # lid tilted back ~110 degrees round the hinge at (y=D, z=H)
    L = ML.Model()
    rbox(L.mesh(M_['chest']), (-W, -2 * D, 0), (W, 0, 10), r=3, k=1, tile=64)
    a = math.radians(-110)
    R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    X.add_model(L, R, (0, D, H))
    for x in (-W, W - 6):
        rbox(X.mesh(M_['brass']), (x, -D - 2, 0), (x + 6, D + 2, H + 2), r=1, k=1)
    ML.save('chest', X)
    coll('chest', wl)


def cupboard():
    """walk-in stationery cupboard: origin footprint centre, front -x; north door closed, south door swung open 90
    degrees (it lies along -x from the south-front hinge); shelves of paper and supplies, floor free to walk in"""
    X = ML.Model(); W, H, T = CB_W / 2, CB_H, 24
    lam, oak = M_['laminate'], M_['oak']
    parts = [((-W, -W, 0), (W, W, T)), ((-W, -W, H - T), (W, W, H)), ((W - T, -W, T), (W, W, H - T)),
             ((-W, -W, T), (W - T, -W + T, H - T)), ((-W, W - T, T), (W - T, W, H - T))]
    shelves = [((-W + T, -W + T, z), (W - T, W - T, z + 16)) for z in (424, 824, 1224)]
    for a, b in parts: rbox(X.mesh(M_['cupboard']), a, b, r=3, k=1, tile=512)
    for a, b in shelves: rbox(X.mesh(lam), a, b, r=3, k=1, tile=256)
    pic(X.mesh(M_['cb_sign']), (-W - 0.8, W / 2 - T / 2, 1300), (-1, 0, 0), 240, 120)
    for z in (T, H - T - 40):                                                     # trim bands round the carcass
        rbox(X.mesh(oak), (-W - 4, -W - 4, z), (W + 4, W + 4, z + 40), r=3, k=1, faces='nsew')
    door_closed = ((-W, 0, T), (-W + T, W - T, H - T))
    door_open = ((-2 * W, -W - T, T), (-W, -W, H - T))
    for a, b in (door_closed, door_open): rbox(X.mesh(oak), a, b, r=4, k=1, tile=256)
    rbox(X.mesh(M_['steel']), (-W - 12, 40, 760), (-W, 56, 900), r=4, k=1)
    rbox(X.mesh(M_['steel']), (-2 * W + 40, -W - T - 12, 760), (-2 * W + 56, -W - T, 900), r=4, k=1)
    # shelf contents (on the three shelves)
    stuff = []
    for k, z in enumerate((440, 840, 1240)):
        for j in range(3):
            y0 = -W + 40 + j * 190
            h = 80 + 40 * ((k + j) % 3)
            rbox(X.mesh(M_['ream']), (-W + 60, y0, z), (W - 60, y0 + 160, z + h), r=3, k=1, tile=256)
            stuff.append(((-W + 60, y0, z), (W - 60, y0 + 160, z + h)))
    ML.save('cupboard', X)
    coll('cupboard', parts + shelves + [door_closed, door_open] + stuff)


def globe_stand():
    """floor globe stand: wooden base plate, column, brass half meridian. The sphere spins on its own func_rotating."""
    X = ML.Model()
    revolve(X.mesh(M_['oakh']), [(200, 0), (200, 24), (186, 32), (0, 32)], n=32, inward=True)
    revolve(X.mesh(M_['oak']), [(30, 32), (24, 200), (34, 260), (24, 330), (30, GLOBE_Z - GLOBE_R - 30), (0, GLOBE_Z - GLOBE_R - 30)], n=16)
    pts = [(math.cos(a) * (GLOBE_R + 22), 0, GLOBE_Z + math.sin(a) * (GLOBE_R + 22)) for a in np.linspace(-math.pi / 2, math.pi / 2, 20)]
    tube(X.mesh(M_['brass']), [(0, 0, GLOBE_Z - GLOBE_R - 30)] + pts + [(0, 0, GLOBE_Z + GLOBE_R + 40)], 10, nseg=8)
    ML.save('globe_stand', X)
    coll('globe_stand', cyls=[(0, 0, 200, 0, 32), (0, 0, 32, 32, GLOBE_Z - GLOBE_R - 30),
                              (0, 0, 150, GLOBE_Z - GLOBE_R + 20, GLOBE_Z - GLOBE_R + 90),
                              (0, 0, 230, GLOBE_Z - GLOBE_R + 90, GLOBE_Z + GLOBE_R - 90),
                              (0, 0, 150, GLOBE_Z + GLOBE_R - 90, GLOBE_Z + GLOBE_R - 20)])


def globe_ball():
    """the sphere alone, centred on its origin (func_rotating model2)"""
    X = ML.Model()
    sphere(X.mesh(M_['globe']), (0, 0, 0), GLOBE_R, nu=32, nv=18)
    ML.save('globe_ball', X)


def tipped_bin():
    """waste-paper bin lying on its side, open end -x, origin at the footprint centre on the floor"""
    k = math.cos(math.pi / 12)
    ro, ri = BIN_R * k, BIN_R * k - BIN_T
    X = ML.Model()
    prof = [(ro, 0), (ro, BIN_L), (ro - 6, BIN_L + 6), (ri, BIN_L + 6), (ri, BIN_T), (0, BIN_T)]
    revolve(X.mesh(M_['bin_blue']), prof, n=40, u_tiles=4)
    disc(X.mesh(M_['bin_blue']), ro, 0, up=False, n=40)
    # rotate: revolve axis +z -> -x so the open rim (z = L) ends up at -x
    Rm = np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])
    Y = ML.Model(); Y.add_model(X, Rm, (BIN_L / 2, 0, ro))
    # a few paper balls inside
    rng = np.random.default_rng(9)
    for j in range(3):
        crumple(Y.mesh(M_['crumple']), (rng.uniform(-120, 160), rng.uniform(-60, 60), BIN_T + 34), 34, 900 + j)
    ML.save('tipped_bin', Y)


def crumple(M, c, r, seed):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6, 6)
    ellipsoid(M, c, r, r * 0.9, r * 0.85, nu=12, nv=8,
              bump=lambda p, t: 1 + 0.16 * math.sin(3 * t + ph[0]) * math.cos(4 * p + ph[1]) + 0.1 * math.sin(5 * p + ph[2]))


def paper_balls():
    """crumpled paper balls spilling out of the bin (decor, no collision)"""
    X = ML.Model(); rng = np.random.default_rng(31)
    for j in range(9):
        r = rng.uniform(26, 42)
        crumple(X.mesh(M_['crumple']), (rng.uniform(-200, 200), rng.uniform(-160, 160), r * 0.85), r, 50 + j)
    ML.save('paper_balls', X)


def pencil_mesh(X, col, length, r, tip=None, eraser=True):
    """hexagonal pencil along +z from 0 to length (sharpened end at +z) - returned in model X"""
    tip = tip or r * 3.2
    hexp = [(r * math.cos(math.radians(30 + 60 * k)), r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    z0 = (r * 1.6) if eraser else 0
    mprism(X.mesh(M_[f'pencil_{col}']), hexp, z0, length - tip, tile=r * 6, top=False, bot=not eraser)
    revolve(X.mesh(M_['pencil_wood']), [(r, length - tip), (r * 0.28, length - tip * 0.22)], n=12)
    revolve(X.mesh(M_['graphite']), [(r * 0.28, length - tip * 0.22), (0, length)], n=12)
    if eraser:
        revolve(X.mesh(M_['ferrule']), [(r * 1.02, z0), (r * 1.02, z0 + r * 0.9)], n=12)
        revolve(X.mesh(M_['eraser']), [(r * 0.95, z0), (r * 0.95, r * 0.5), (r * 0.6, 0), (0, 0)], n=12)


def pencil_bridge():
    """six jumbo pencils side by side, 400 long along x, the bundle 160 wide; collision is one flat box with its top
    16 above the desk top (the pencils' tops stand 10 proud of it)"""
    X = ML.Model(); r = 13
    cols = ['yellow', 'red', 'blue', 'green', 'orange', 'purple']
    for k, c in enumerate(cols):
        P = ML.Model(); pencil_mesh(P, c, 440, r)
        y = -65 + k * 26
        flip = -1 if k % 2 else 1
        R = RY90 if flip > 0 else np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])
        X.add_model(P, R, (-220 * flip, y, r))
    ML.save('pencil_bridge', X)
    coll('pencil_bridge', [((-200, -78, 0), (200, 78, 16))])


def ruler_bridge():
    """a flat wooden ruler, 440 long along y, 160 wide, 16 thick"""
    X = ML.Model()
    rbox(X.mesh(M_['ruler_m']), (-80, -220, 0), (80, 220, 16), r=2, k=1, faces='nsew')
    pic(X.mesh(M_['ruler_m']), (0, 0, 16.4), (0, 0, 1), 160, 440, up=(0, 1, 0))
    pic(X.mesh(M_['ruler_m']), (0, 0, -0.4), (0, 0, -1), 160, 440, up=(0, 1, 0))
    ML.save('ruler_bridge', X)
    coll('ruler_bridge', [((-80, -220, 0), (80, 220, 16))])


def spiral_steps():
    """(angle, top z) of every step - the same sequence K.spiral_stairs builds for the collision"""
    n = int(round(SPIRAL_TOP / 16))
    return [(SPIRAL_END - (n - 1 - i) * SPIRAL_STEP, (i + 1) * 16) for i in range(n)]


def spiral_books():
    """the exercise-book spiral round the jumbo pencil: one book per step (angle, top z from K.spiral_stairs)"""
    X = ML.Model(); rng = np.random.default_rng(17)
    SPIRAL_STEPS = spiral_steps()
    w = 2 * SPIRAL_ROUT * math.tan(math.radians(SPIRAL_STEP) / 2) * 1.15
    for i, (a, zt) in enumerate(SPIRAL_STEPS):
        B = ML.Model()
        col = M_[f'book{rng.integers(0, 8)}']
        L0, L1 = SPIRAL_RIN + 2, SPIRAL_ROUT
        rbox(B.mesh(col), (L0, -w / 2, -16), (L1, w / 2, -12), r=1, k=1, tile=256)
        rbox(B.mesh(col), (L0, -w / 2, -4), (L1, w / 2, 0), r=1, k=1, tile=256)
        rbox(B.mesh(M_['pages']), (L0 + 4, -w / 2 + 4, -12), (L1 - 6, w / 2 - 6, -4), r=0.5, k=1, tile=64)
        X.add_model(B, rot_z(math.radians(a)), (0, 0, zt))
    ML.save('spiral_books', X)


def jumbo_pencil():
    """the upright jumbo pencil the book spiral winds round: r 46, sharpened tip up to 980"""
    X = ML.Model(); pencil_mesh(X, 'yellow', 980, 46, tip=150)
    ML.save('jumbo_pencil', X)
    coll('jumbo_pencil', cyls=[(0, 0, 44, 0, 900)])


def pencil_case():
    """zip pencil case lying on a desk, open end -x (walk in), origin footprint centre"""
    k = math.cos(math.pi / 12)
    ro, ri = PCASE_R * k, PCASE_R * k - PCASE_T
    X = ML.Model()
    revolve(X.mesh(M_['pcase']), [(ro, 0), (ro, PCASE_L), (ri, PCASE_L), (ri, PCASE_T), (0, PCASE_T)], n=32, u_tiles=3)
    disc(X.mesh(M_['pcase']), ro, 0, up=False, n=32)
    Rm = np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]])
    Y = ML.Model(); Y.add_model(X, Rm, (PCASE_L / 2, 0, ro))
    tube(Y.mesh(M_['zip']), [(-PCASE_L / 2, 0, 2 * ro + 1), (PCASE_L / 2, 0, 2 * ro + 1)], 5, nseg=6)
    rbox(Y.mesh(M_['zip']), (-PCASE_L / 2 - 30, -10, 2 * ro - 6), (-PCASE_L / 2 + 6, 10, 2 * ro + 4), r=2, k=1)
    # pencils peeking out of the open end
    for j, c in enumerate(('red', 'blue', 'green')):
        P = ML.Model(); pencil_mesh(P, c, 150, 6, eraser=False)
        Y.add_model(P, np.array([[0, 0, -1.0], [0, 1, 0], [1, 0, 0]]), (-PCASE_L / 2 + 80, -30 + j * 30, PCASE_T + 6))
    ML.save('pencil_case', Y)


def lunchbox():
    """lunchbox, origin footprint centre, 320 x 200 x 150 with a carry handle"""
    X = ML.Model()
    body = ((-160, -100, 0), (160, 100, 150))
    rbox(X.mesh(M_['lunch']), (-160, -100, 0), (160, 100, 120), r=16, k=3, tile=256)
    rbox(X.mesh(M_['plastic_red']), (-164, -104, 112), (164, 104, 150), r=14, k=3)
    tube(X.mesh(M_['plastic_red']), [(-80, 0, 150), (-60, 0, 200), (60, 0, 200), (80, 0, 150)], 8, nseg=8)
    ML.save('lunchbox', X)
    coll('lunchbox', [body])


def crayon_box():
    """jumbo crayon box lying with its open end +x (walk in), crayons spilling out. 560 x 320 x 240."""
    X = ML.Model(); L, W, H, T = 280, 160, 240, 12
    walls = [((-L, -W, 0), (L, W, T)), ((-L, -W, H - T), (L, W, H)), ((-L, -W, T), (L, -W + T, H - T)),
             ((-L, W - T, T), (L, W, H - T)), ((-L, -W + T, T), (-L + T, W - T, H - T))]
    for a, b in walls: rbox(X.mesh(M_['cardboard']), a, b, r=2, k=1, tile=128)
    pic(X.mesh(M_['crayon_box']), (0, -W - 0.6, H / 2), (0, -1, 0), 2 * L - 20, H - 20)
    pic(X.mesh(M_['crayon_box']), (0, W + 0.6, H / 2), (0, 1, 0), 2 * L - 20, H - 20)
    pic(X.mesh(M_['crayon_box']), (0, 0, H + 0.6), (0, 0, 1), 2 * L - 20, 2 * W - 20, up=(0, 1, 0))
    cols = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'teal']
    rng = np.random.default_rng(12)
    spill = []
    for j, c in enumerate(cols):                                            # spilled crayons on the floor outside
        x, y = L + 60 + rng.uniform(0, 260), rng.uniform(-180, 180)
        a = rng.uniform(0, math.pi)
        C = ML.Model()
        revolve(C.mesh(M_[f'crayon_{c}']), [(18, 0), (18, 150), (6, 190), (0, 192)], n=12)
        disc(C.mesh(M_[f'crayon_{c}']), 18, 0, up=False, n=12)
        R = rot_z(a) @ RY90
        X.add_model(C, R, (x - math.cos(a) * 96, y - math.sin(a) * 96, 18))
    for j, c in enumerate(cols[:5]):                                        # still inside
        C = ML.Model()
        revolve(C.mesh(M_[f'crayon_{c}']), [(18, 0), (18, 150), (6, 190), (0, 192)], n=12)
        X.add_model(C, RY90, (-L + 40, -110 + j * 52, T + 18))
    ML.save('crayon_box', X)
    coll('crayon_box', walls + [((-L + T, -W + T, T), (-L + 240, W - T, T + 36))])


def radiator():
    """panel radiator under a window, origin centre of its footprint on the floor, 600 wide (x), against the wall +y"""
    X = ML.Model()
    for k in range(20):
        x = -290 + k * 30
        rbox(X.mesh(M_['radiator']), (x, -26, 110), (x + 22, 26, 600), r=8, k=2, tile=128)
    tube(X.mesh(M_['radiator']), [(-300, 0, 130), (300, 0, 130)], 14, nseg=8)
    tube(X.mesh(M_['radiator']), [(-300, 0, 580), (300, 0, 580)], 14, nseg=8)
    for x in (-270, 270):
        tube(X.mesh(M_['steel']), [(x, 30, 110), (x, 30, 0)], 10, nseg=8)
    ML.save('radiator', X)
    coll('radiator', [((-300, -26, 110), (300, 26, 600)), ((-280, 20, 0), (-260, 40, 110)), ((260, 20, 0), (280, 40, 110))])


def fluoro_panel():
    """ceiling light panel, hung from z=0 downwards (origin on the ceiling)"""
    X = ML.Model()
    rbox(X.mesh(M_['white']), (-280, -90, -24), (280, 90, 0), r=4, k=1)
    pic(X.mesh(M_['fluoro_m']), (0, 0, -24.6), (0, 0, -1), 520, 150, up=(1, 0, 0))
    ML.save('fluoro', X)


def clock():
    """wall clock facing -y, origin at its centre on the wall"""
    X = ML.Model()
    Rm = RX90
    C = ML.Model()
    revolve(C.mesh(M_['clock_red']), [(130, 0), (130, 24), (118, 28)], n=40)
    disc(C.mesh(M_['clock']), 120, 18, up=True, n=40, uvscale=None)
    X.add_model(C, Rm, (0, 0, 0))
    ML.save('clock', X)


def clock_hand():
    """second hand, centred on its pivot, lying in the x/z plane just in front of the face (spins about y)"""
    X = ML.Model()
    rbox(X.mesh(M_['clock_red']), (-3, -2, -20), (3, 2, 100), r=1, k=1)
    ML.save('clock_hand', X)


def plane_mobile():
    """paper-plane mobile, centred on its hanging point (spins about z): two crossed sticks, four planes on strings"""
    X = ML.Model()
    tube(X.mesh(M_['pine']), [(-360, 0, 0), (360, 0, 0)], 5, nseg=6)
    tube(X.mesh(M_['pine']), [(0, -360, -20), (0, 360, -20)], 5, nseg=6)
    tube(X.mesh(M_['string']), [(0, 0, 0), (0, 0, 300)], 1.5, nseg=4)
    for k, (x, y) in enumerate(((-340, 0), (340, 0), (0, -340), (0, 340))):
        drop = 120 + 40 * k
        z = -20 if y else 0
        tube(X.mesh(M_['string']), [(x, y, z), (x, y, z - drop)], 1.5, nseg=4)
        a = math.atan2(y, x) + math.pi / 2                                       # planes fly round the circle
        P = ML.Model()
        pts = [(80, 0, 0), (-60, -50, 4), (-50, 0, -14), (-60, 50, 4)]
        Mp = P.mesh(M_['plane'])
        q = [np.array(p, float) for p in pts]
        Mp.poly([q[0], q[1], q[2]], (0, -0.3, 1), [(1, 0.5), (0, 0), (0.1, 0.5)])
        Mp.poly([q[0], q[2], q[3]], (0, 0.3, 1), [(1, 0.5), (0.1, 0.5), (0, 1)])
        X.add_model(P, rot_z(a), (x, y, z - drop - 6))
    ML.save('plane_mobile', X)


def fish_ring(name, R, n, mat, sc):
    """fish swimming round a circle of radius R (centred on the origin, spins about z): body, tail, eyes"""
    X = ML.Model(); rng = np.random.default_rng(len(name))
    for k in range(n):
        a = 2 * math.pi * k / n
        F = ML.Model()
        ellipsoid(F.mesh(M_[mat]), (0, 0, 0), 34 * sc, 12 * sc, 22 * sc, nu=12, nv=8)
        t = [np.array(p, float) * sc for p in ((-28, 0, 0), (-56, 0, 22), (-56, 0, -22))]
        F.mesh(M_[mat]).poly(t, (0, 1, 0), [(0, 0.5), (1, 0), (1, 1)])
        for s in (-1, 1):
            sphere(F.mesh(M_['fish_eye']), (20 * sc, s * 9 * sc, 6 * sc), 4 * sc, nu=6, nv=4)
        z = rng.uniform(-40, 40)
        X.add_model(F, rot_z(a + math.pi / 2), (R * math.cos(a), R * math.sin(a), z))
    ML.save(name, X)


def bubbler():
    """air stone + a rising column of bubbles (crossed additive quads, scrolling)"""
    X = ML.Model()
    revolve(X.mesh(M_['castle']), [(30, 0), (26, 30), (0, 30)], n=12, inward=False)
    for a in (0, math.pi / 2):
        c = (0, 0, 30 + 230)
        n = (math.cos(a), math.sin(a), 0)
        pic(X.mesh(M_['bubbles']), c, n, 60, 460)
    ML.save('bubbler', X)


def schoolbag(col):
    """school backpack standing on the floor, origin footprint centre, straps at +y"""
    X = ML.Model(); f = M_[f'bag_{col}']
    rbox(X.mesh(f), (-120, -70, 0), (120, 70, 300), r=40, k=4, tile=256)
    rbox(X.mesh(f), (-100, -110, 30), (100, -60, 190), r=24, k=3, tile=256)
    for x in (-60, 60):
        tube(X.mesh(M_['black']), [(x, 70, 280), (x, 110, 220), (x, 100, 60), (x, 70, 30)], 8, nseg=6)
    tube(X.mesh(M_['zip']), [(-100, -110, 150), (100, -110, 150)], 3, nseg=4)
    ML.save(f'bag_{col}', X)
    coll(f'bag_{col}', [((-112, -100, 0), (112, 66, 290))])
    return f'bag_{col}'


def paper_stack():
    """a stack of exercise books / marking on the teacher's desk"""
    X = ML.Model(); rng = np.random.default_rng(3)
    z = 0
    for k in range(6):
        a = rng.uniform(-0.2, 0.2)
        B = ML.Model()
        rbox(B.mesh(M_[f'book{k % 8}']), (-110, -80, 0), (110, 80, 14), r=2, k=1)
        X.add_model(B, rot_z(a), (rng.uniform(-6, 6), rng.uniform(-6, 6), z))
        z += 14
    ML.save('paper_stack', X)
    coll('paper_stack', [((-100, -70, 0), (100, 70, z))])


def pencil_cup():
    X = ML.Model()
    revolve(X.mesh(M_['bin_blue']), [(44, 0), (46, 110), (40, 110), (38, 6), (0, 6)], n=20)
    disc(X.mesh(M_['bin_blue']), 44, 0, up=False, n=20)
    for k, c in enumerate(('red', 'green', 'yellow', 'blue')):
        P = ML.Model(); pencil_mesh(P, c, 190, 5)
        a = k * math.pi / 2
        R = rot_z(a) @ np.array([[math.cos(0.18), 0, math.sin(0.18)], [0, 1, 0], [-math.sin(0.18), 0, math.cos(0.18)]])
        X.add_model(P, R, (math.cos(a) * 12, math.sin(a) * 12, 8))
    ML.save('pencil_cup', X)
    coll('pencil_cup', cyls=[(0, 0, 40, 0, 110)])


def duster():
    """blackboard eraser: wooden back, grey felt"""
    X = ML.Model()
    rbox(X.mesh(M_['pine']), (-96, -40, 16), (96, 40, 56), r=10, k=2)
    rbox(X.mesh(M_['felt']), (-92, -36, 0), (92, 36, 18), r=4, k=1)
    ML.save('duster', X)
    coll('duster', [((-96, -40, 0), (96, 40, 56))])


def chalk_sticks():
    X = ML.Model()
    cols = ['chalk', 'chalk', 'crayon_yellow', 'crayon_pink', 'crayon_blue', 'chalk']
    for k, c in enumerate(cols):
        C = ML.Model()
        revolve(C.mesh(M_[c]), [(6, 0), (6, 70), (0, 72)], n=8)
        X.add_model(C, rot_z(0.3 * k) @ RY90, (-200 + k * 70, (k % 2) * 30, 6))
    ML.save('chalk_sticks', X)


def eraser():
    X = ML.Model()
    rbox(X.mesh(M_['eraser']), (-40, -24, 0), (40, 24, 24), r=6, k=2)
    rbox(X.mesh(M_['bin_blue']), (-10, -25, 0), (40, 25, 25), r=4, k=1)
    ML.save('eraser', X)


def glue_bottle():
    X = ML.Model()
    revolve(X.mesh(M_['glue']), [(30, 0), (30, 90), (14, 110), (0, 110)], n=16)
    revolve(X.mesh(M_['glue_cap']), [(14, 110), (14, 130), (4, 150), (0, 150)], n=12)
    ML.save('glue', X)


def open_book():
    """an open picture book lying on a desk (pages fan up a little)"""
    X = ML.Model()
    rbox(X.mesh(M_['book4']), (-200, -140, 0), (200, 140, 6), r=2, k=1)
    for s in (-1, 1):
        P = [np.array(p, float) for p in ((0, -130, 8), (s * 190, -130, 18), (s * 190, 130, 18), (0, 130, 8))]
        if s < 0: P = [P[0], P[3], P[2], P[1]]
        X.mesh(M_['pages']).poly(P, (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('open_book', X)
    coll('open_book', [((-200, -140, 0), (200, 140, 12))])


def detention_desk():
    X = ML.Model()
    rbox(X.mesh(M_['desk_top2']), (-200, -140, 360), (200, 140, 380), r=4, k=1)
    for (x, y) in ((-180, -120), (180, -120), (-180, 120), (180, 120)):
        tube(X.mesh(M_['steel']), [(x, y, 0), (x, y, 360)], 9, nseg=8)
    ML.save('det_desk', X)
    coll('det_desk', [((-200, -140, 360), (200, 140, 380))] + [((x - 10, y - 10, 0), (x + 10, y + 10, 360)) for (x, y) in ((-180, -120), (180, -120), (-180, 120), (180, 120))])


# ------------------------------------------------------------------------------------------------ cover props
def chair_mesh(X, col, z=0.0):
    """the school chair mesh added into X at height z (for stacks)"""
    S = CHAIR_SEAT
    pl, st = M_[f'plastic_{col}'], M_['steel']
    rbox(X.mesh(pl), (-180, -180, z + S - 24), (180, 170, z + S), r=12, k=3)
    rbox(X.mesh(pl), (-170, 150, z + S + 60), (170, 176, z + S + 340), r=12, k=3)
    for (x, y) in ((-160, -160), (160, -160), (-160, 160), (160, 160)):
        tube(X.mesh(st), [(x, y, z + 6), (x, y, z + S - 24)], 11, nseg=8)
    for x in (-160, 160):
        tube(X.mesh(st), [(x, 163, z + S), (x, 163, z + S + 300)], 10, nseg=8)


def cover_props():
    X = ML.Model()                                                                 # stack of four chairs
    for k, c in enumerate(('blue', 'red', 'yellow', 'green')):
        chair_mesh(X, c, k * 70)
    ML.save('chair_stack', X)
    coll('chair_stack', [((-180, -180, 0), (180, 176, CHAIR_SEAT + 210)), ((-170, 150, CHAIR_SEAT + 210), (170, 176, CHAIR_SEAT + 550))])

    X = ML.Model()                                                                 # art trolley with coloured trays
    body = ((-240, -160, 40), (240, 160, 600))
    rbox(X.mesh(M_['white']), *body, r=10, k=2)
    cols = ['red', 'blue', 'green', 'yellow', 'orange', 'purple']
    for j in range(2):
        for k in range(3):
            c = cols[(j * 3 + k) % 6]
            rbox(X.mesh(M_[f'crayon_{c}']), (-224 + j * 228, -168, 70 + k * 172), (-12 + j * 228, -158, 220 + k * 172), r=6, k=2)
    for (x, y) in ((-200, -120), (200, -120), (-200, 120), (200, 120)):
        tube(X.mesh(M_['black']), [(x, y - 12, 20), (x, y + 12, 20)], 20, nseg=10)
    ML.save('art_trolley', X)
    coll('art_trolley', [((-240, -160, 0), (240, 160, 600))])

    X = ML.Model()                                                                 # toy box: open carton with toys
    L, W, H, T = 220, 160, 260, 10
    walls = [((-L, -W, 0), (L, W, T)), ((-L, -W, T), (L, -W + T, H)), ((-L, W - T, T), (L, W, H)),
             ((-L, -W + T, T), (-L + T, W - T, H)), ((L - T, -W + T, T), (L, W - T, H))]
    for a, b in walls: rbox(X.mesh(M_['cardboard']), a, b, r=2, k=1, tile=128)
    pic(X.mesh(M_['crayon_box']), (0, -W - 0.6, H / 2), (0, -1, 0), 2 * L - 40, H - 60)
    rng = np.random.default_rng(77)
    for j in range(7):                                                             # balls and blocks poking out
        c = cols[j % 6]
        if j % 2:
            sphere(X.mesh(M_[f'crayon_{c}']), (rng.uniform(-150, 150), rng.uniform(-90, 90), H - 30 + rng.uniform(0, 30)), 50, nu=14, nv=8)
        else:
            x, y = rng.uniform(-150, 150), rng.uniform(-90, 90)
            rbox(X.mesh(M_[f'crayon_{c}']), (x - 40, y - 40, H - 60), (x + 40, y + 40, H + 20), r=6, k=2)
    ML.save('toy_box', X)
    coll('toy_box', [((-L, -W, 0), (L, W, H))])

    X = ML.Model()                                                                 # gym ball
    sphere(X.mesh(M_['crayon_red']), (0, 0, 170), 170, nu=28, nv=16)
    ML.save('gym_ball', X)
    coll('gym_ball', cyls=[(0, 0, 110, 0, 40), (0, 0, 160, 40, 300), (0, 0, 110, 300, 340)])

    X = ML.Model()                                                                 # pile of big atlases (32u steps)
    rng = np.random.default_rng(5)
    bx = []
    for k in range(4):
        w, d = 420 - k * 70, 300 - k * 40
        a, b = (-w / 2 + k * 30, -d / 2, k * 40), (w / 2 + k * 30, d / 2, k * 40 + 40)
        col = M_[f'book{(k * 3) % 8}']
        rbox(X.mesh(col), (a[0], a[1], a[2]), (b[0], b[1], a[2] + 6), r=2, k=1)
        rbox(X.mesh(col), (a[0], a[1], b[2] - 6), (b[0], b[1], b[2]), r=2, k=1)
        rbox(X.mesh(M_['pages']), (a[0] + 6, a[1] + 6, a[2] + 6), (b[0] - 4, b[1] - 6, b[2] - 6), r=1, k=1)
        rbox(X.mesh(col), (a[0], a[1], a[2]), (a[0] + 8, b[1], b[2]), r=2, k=1)
        bx.append((a, b))
    ML.save('atlas_pile', X)
    coll('atlas_pile', bx)


def more_cover():
    for c in ('blue', 'green'):                                                     # beanbags
        X = ML.Model()
        ellipsoid(X.mesh(M_[f'bag_{c}']), (0, 0, 90), 210, 190, 100, nu=24, nv=12,
                  bump=lambda p, t: 1 + 0.08 * math.sin(3 * p) * math.cos(2 * t))
        ellipsoid(X.mesh(M_[f'bag_{c}']), (-60, 0, 170), 150, 160, 90, nu=20, nv=10)
        ML.save(f'beanbag_{c}', X)
        coll(f'beanbag_{c}', cyls=[(0, 0, 170, 0, 150), (-60, 0, 120, 150, 230)])
    X = ML.Model()                                                                  # recycling box under the bridges
    L, W, H, T = 150, 150, 300, 10
    walls = [((-L, -W, 0), (L, W, T)), ((-L, -W, T), (L, -W + T, H)), ((-L, W - T, T), (L, W, H)),
             ((-L, -W + T, T), (-L + T, W - T, H)), ((L - T, -W + T, T), (L, W - T, H))]
    for a, b in walls: rbox(X.mesh(M_['bin_blue']), a, b, r=3, k=1)
    for s in (-1, 1):
        pic(X.mesh(M_['recycle']), (0, s * (W + 0.6), H / 2), (0, s, 0), 220, 220)
    for j in range(5):
        crumple(X.mesh(M_['crumple']), (-80 + j * 40, (j % 2) * 50 - 25, H - 40), 40, 300 + j)
    ML.save('recycle_box', X)
    coll('recycle_box', [((-L, -W, 0), (L, W, H))])


# ------------------------------------------------------------------------------------------------ themed jump pads
PAD_SKINS = {}         # name -> dict(w, d, h) for K.jumppad(skin=...)


def pad_skins():
    """jump pads dressed as classroom things lying on the floor/desks, each with a bright JUMP! sticker on top.
    Decks are <= 16u so players step on and bots walk on; footprints cover the 48u trigger at any angle."""
    for col, bi in (('blue', 1), ('red', 0), ('green', 2), ('yellow', 3)):           # exercise books
        X = ML.Model(); W, D, H = 88, 64, 14
        cov = M_[f'book{bi}']
        rbox(X.mesh(cov), (-W, -D, 0), (W, D, 3), r=1, k=1, tile=256)
        rbox(X.mesh(cov), (-W, -D, H - 3), (W, D, H), r=1, k=1, tile=256)
        rbox(X.mesh(M_['pages']), (-W + 3, -D + 3, 3), (W - 4, D - 4, H - 3), r=0.5, k=1, tile=64)
        rbox(X.mesh(cov), (-W, -D, 0), (-W + 8, D, H), r=1, k=1)                          # spine
        pic(X.mesh(M_['sticker']), (6, 0, H + 0.6), (0, 0, 1), 100, 100, up=(1, 0, 0))
        name = f'pad_book_{col}'
        ML.save(name, X); PAD_SKINS[name] = dict(w=2 * W, d=2 * D, h=H)
    X = ML.Model(); W, D, H = 84, 48, 16                                                # eraser with a paper sleeve
    rbox(X.mesh(M_['eraser']), (-W, -D, 0), (W, D, H), r=6, k=2)
    rbox(X.mesh(M_['bin_blue']), (-W * 0.35, -D - 1, 0), (W + 1, D + 1, H + 1), r=4, k=1)
    pic(X.mesh(M_['sticker']), (-W * 0.25, 0, H + 0.8), (0, 0, 1), 84, 84, up=(1, 0, 0))
    ML.save('pad_eraser', X); PAD_SKINS['pad_eraser'] = dict(w=2 * W, d=2 * D, h=H)
    X = ML.Model(); W, D, H = 96, 56, 16                                                # flat zip pencil case
    rbox(X.mesh(M_['pcase']), (-W, -D, 0), (W, D, H), r=8, k=3, tile=128)
    tube(X.mesh(M_['zip']), [(-W + 10, D - 12, H - 1), (W - 10, D - 12, H - 1)], 3, nseg=6)
    rbox(X.mesh(M_['zip']), (W - 14, D - 18, H - 4), (W + 14, D - 6, H + 2), r=2, k=1)
    pic(X.mesh(M_['sticker']), (-20, 0, H + 1.2), (0, 0, 1), 92, 92, up=(1, 0, 0))
    ML.save('pad_pcase', X); PAD_SKINS['pad_pcase'] = dict(w=2 * W, d=2 * D, h=H)


def pad_skin(name, pad, land):
    """skin for K.jumppad, turned so the sticker's arrows (+x) point at the landing"""
    s = PAD_SKINS[name]
    angle = round(math.degrees(math.atan2(land[1] - pad[1], land[0] - pad[0])))
    return dict(place=ML.PLACE[name], h=s['h'], angle=angle,
                boxes=[((-s['w'] / 2, -s['d'] / 2, 0), (s['w'] / 2, s['d'] / 2, s['h']))])
