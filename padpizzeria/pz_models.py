"""Padman's Pizza Joint (wop_padpizzeria) - textures (woplib.texlib registry) and custom MD3s.
All art is original and procedural (90s NYC slice-shop look: red booths, wood-grain laminate, rust/cream checker
tiles, a smiley-pizza mural, a red menu board).

Toy scale ~5u per cm (Padman ~11 cm): booth seat 225, table 375, booth back 560, counter 525, ceiling 1400.
Every model is built in model space with z = 0 on the surface it stands on; COLL[name] holds the weapclip collision
(boxes / cylinders in model space) that build_padpizzeria.py places with it.
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
SEAT_Z, TABLE_Z, BACK_Z = 225, 375, 560
BOOTH_L = 560                                   # wall -> aisle
SEAT_D, BACK_T = 220, 40                        # seat depth, single back thickness (double = 80)
TABLE_L, TABLE_W, TABLE_T = 550, 360, 22
COUNTER_Z, COUNTER_D = 525, 330
CASE_H = 200                                    # glass slice case on the counter
COOLER = (300, 350, 1000)                       # depth (x), width (y), height
ATM = (250, 220, 760)
OVEN = (900, 600, 850)                          # width x, depth y, height
OVEN_CH = (200, 400)                            # lower chamber floor / roof
OVEN_DOOR = (-300, 300)                         # lower chamber opening x (model space)
SINK_Z, SINK_FLOOR = 450, 258
PREP_Z = 450
TWO_TOP_Z, TWO_TOP_R = 375, 150
CHAIR_SEAT = 225
AWN_Z, AWN_D = 1280, 320
COUNTER_L, CASE_L, SHELF_L, VALANCE_L = 800, 520, 960, 1700
ARCH_W, ARCH_H, ARCH_T = 800, 760, 60            # mural arch opening (from z 560), brick ring thickness                        # awning top, depth out of the facade


# ================================================================================================= helpers
def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n, w x h, never mirrored"""
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    M.poly([c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh], n, [(0, 0), (1, 0), (1, 1), (0, 1)])


def coll(name, boxes=(), cyls=(), hulls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls), hulls=[list(h) for h in hulls])


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def bx(X, mat, mn, mx, r=3, k=1, tile=128, faces='nsewtb'):
    rbox(X.mesh(M_[mat]), mn, mx, r=r, k=k, tile=tile, faces=faces)


def draw(arr):
    im = Image.fromarray(np.uint8(np.clip(arr, 0, 255)))
    return im, ImageDraw.Draw(im)


def arr(im): return np.asarray(im, np.float32)


def cylz(X, mat, cx, cy, r, z0, z1, n=16, top=True, bot=False, u=1.0):
    revolve(X.mesh(M_[mat]), [(r, z0), (r, z1)], u_tiles=u, n=n, cx=cx, cy=cy)
    if top: disc(X.mesh(M_[mat]), r, z1, up=True, n=n, cx=cx, cy=cy)
    if bot: disc(X.mesh(M_[mat]), r, z0, up=False, n=n, cx=cx, cy=cy)


# ================================================================================================= brush textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('floor', parquet(), scale=1.0, steps='woodsteps')
    a('checker', TL.checker((168, 74, 56), (236, 222, 200), 4, grout=(200, 190, 176), grout_w=0.01), scale=1.25)
    a('brick', TL.bricks((92, 52, 40), (60, 40, 32), rows=8, cols=4, vary=14), scale=1.0)
    a('maroon', TL.solid((112, 40, 44), 4, 11, 256), scale=1.0)
    a('plaster', TL.solid((196, 132, 112), 4, 12, 256), scale=1.0)
    a('ceiling', ceiling_tiles(), scale=1.25)
    a('whitetile', TL.tiles((236, 232, 222), (190, 186, 178), cols=4, rows=4, offset=0, grout_w=0.03, vary=4), scale=0.6)
    a('wood', TL.planks((112, 66, 40), n_planks=4, gap=(70, 40, 24), grain=6), steps='woodsteps', scale=0.75)
    a('trim', TL.solid((88, 52, 34), 3, 13, 64))
    a('steel', TL.metal((186, 190, 196)), scale=0.75)
    a('quarry', TL.tiles((150, 62, 46), (90, 70, 60), cols=4, rows=4, offset=0, grout_w=0.04, vary=10), scale=1.0)
    a('subway', TL.tiles((240, 240, 236), (180, 182, 184), cols=4, rows=8, offset=0.5, grout_w=0.04, vary=3), scale=0.75)
    a('pavement', TL.tiles((196, 192, 186), (140, 136, 132), cols=2, rows=2, offset=0, grout_w=0.02, vary=8), scale=1.5)
    a('kerb', TL.solid((170, 168, 164), 5, 15, 128))
    a('road', TL.solid((70, 72, 78), 8, 19, 256) + TL.N3(256, 1, 20, 6), scale=1.0)
    a('facade', TL.bricks((150, 66, 48), (200, 190, 176), rows=8, cols=4, vary=18), scale=1.0)
    a('stone', TL.solid((204, 198, 186), 4, 16, 128))
    a('across', across_street(), 'sign', check_tile=False)
    a('black', TL.solid((34, 32, 32), 2, 17, 64))
    a('menu', menu_board(), 'sign', check_tile=False)
    a('shopsign', shop_sign(), 'sign', check_tile=False)
    a('mural', mural(), 'sign', check_tile=False)
    a('pizzasign', lightbox('PIZZA'), 'sign', check_tile=False)
    for i, fn in enumerate((still_life_fruit, still_life_jug)):
        a(f'paint{i}', fn(), 'sign', check_tile=False)
    a('poster', poster(), 'sign', check_tile=False)
    a('neon_pizza', TL.neon('PIZZA', (255, 70, 60), 512, 256), 'neon', rgb=(1, 0.3, 0.25), light=200, check_tile=False)
    a('neon_open', TL.neon('OPEN', (90, 255, 120), 512, 256), 'neon', rgb=(0.4, 1, 0.5), light=150, check_tile=False)
    a('fluor', fluor(), 'raw', check_tile=False, shader=glow_stanza(K.ns, 'fluor'))
    a('water', TL.solid((150, 176, 170), 8, 18, 128), 'water', rgb=(0.55, 0.62, 0.58), alpha=0.5)
    a('grate', grate(), check_tile=False)
    a('vault', TL.tiles((230, 210, 160), (190, 150, 100), cols=4, rows=4, offset=0.5, grout_w=0.03), scale=1.0)
    a('dough', TL.solid((236, 214, 170), 6, 21, 256) + TL.N3(256, 3, 22, 6), scale=1.0)
    TX.kit_defaults(pad_rgb=(255, 120, 40), rubber=(60, 40, 34), pad=pepperoni_pad())
    materials()
    return TX


def across_street(w=1024, h=512):
    """the buildings across the road: brick walk-ups with windows over a row of shop fronts (painted backdrop)"""
    c = np.zeros((h, w, 3), np.float32)
    im, d = draw(c)
    cols = [(150, 70, 52), (120, 96, 80), (170, 110, 70), (110, 60, 56)]
    shops = [('DELI', (40, 110, 60)), ('LAUNDROMAT', (40, 70, 140)), ('BARBER', (150, 30, 30)), ('VIDEO', (200, 140, 30))]
    bw = w // 4
    for k in range(4):
        x0 = k * bw
        d.rectangle((x0, 0, x0 + bw, h), fill=cols[k])
        for j in range(4):
            for i in range(3):
                wx = x0 + 22 + i * (bw - 44) // 3; wy = 30 + j * 72
                d.rectangle((wx, wy, wx + 48, wy + 50), fill=(60, 70, 84)); d.rectangle((wx - 3, wy + 50, wx + 51, wy + 56), fill=(210, 200, 190))
                d.line((wx + 24, wy, wx + 24, wy + 50), fill=(200, 196, 190), width=2)
        name, sc = shops[k]
        d.rectangle((x0 + 8, 330, x0 + bw - 8, 372), fill=sc)
        f = ML.font(26, serif=False); tw = d.textlength(name, font=f)
        d.text((x0 + (bw - tw) / 2, 336), name, font=f, fill=(250, 250, 240))
        d.rectangle((x0 + 12, 380, x0 + bw - 12, h - 4), fill=(50, 60, 70))
        d.rectangle((x0 + bw // 2 - 26, 400, x0 + bw // 2 + 26, h - 4), fill=(30, 34, 40))
        d.line((x0, 0, x0, h), fill=(70, 50, 40), width=4)
    return arr(im)


def glow_stanza(ns, name):
    t = f'textures/{ns}/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
            f'\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t}}\n}}\n\n')


def parquet(n=256):
    """tan basket-weave vinyl floor tiles from the photo (pairs of planks alternating direction)"""
    x, y = TL.xy(n)
    cell = 4
    cx, cy = (x * cell).astype(int), (y * cell).astype(int)
    fx, fy = (x * cell) % 1, (y * cell) % 1
    horiz = ((cx + cy) % 2) == 0
    along = np.where(horiz, fy, fx)          # across the planks
    strip = (along * 3).astype(int)
    tone = np.array([0, 12, -10])[strip]
    base = TL.fill(n, (186, 150, 102), 3, 31) + tone[..., None]
    grain = TL.N3(n, 1, 32, 8)
    g1 = (np.abs((along * 3) % 1 - 0.0) < 0.04) | (np.abs((along * 3) % 1 - 1.0) < 0.04)
    edge = (fx < 0.02) | (fy < 0.02)
    c = base + grain
    c = np.where(g1[..., None], c - 30, c)
    c = np.where(edge[..., None], C((120, 92, 60)), c)
    return c


def ceiling_tiles(n=256):
    c = TL.fill(n, (92, 58, 40), 3, 33) + TL.N3(n, 1, 34, 10)
    x, y = TL.xy(n)
    g = ((x * 2) % 1 < 0.03) | ((y * 2) % 1 < 0.03)
    rng = np.random.default_rng(35)
    pits = rng.random((n, n)) > 0.9
    c = c - pits[..., None] * 18
    return np.where(g[..., None], C((60, 40, 30)), c)


def fluor(n=128):
    x, y = TL.xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((250, 250, 244))
    g = ((x * 8) % 1 < 0.12) | ((y * 8) % 1 < 0.12)
    c = np.where(g[..., None], C((214, 216, 214)), c)
    edge = (x < 0.04) | (x > 0.96) | (y < 0.04) | (y > 0.96)
    return np.where(edge[..., None], C((200, 200, 196)), c)


def grate(n=128):
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    holes = (((x * 6) % 1 - 0.5) ** 2 + ((y * 6) % 1 - 0.5) ** 2) < 0.08
    c = np.where(holes[..., None], C((20, 20, 22)), C((170, 172, 176)))
    return np.where((r > 0.48)[..., None], C((140, 142, 146)), c)


def pepperoni_pad(n=256):
    """the jump-pad top is a pepperoni"""
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    c = TL.fill(n, (170, 40, 30), 4, 36) + TL.N3(n, 2, 37, 14)
    rng = np.random.default_rng(38)
    for _ in range(26):
        px, py = rng.random(2) * 0.7 + 0.15
        rr = rng.random() * 0.03 + 0.012
        c = np.where(((np.hypot(x - px, y - py) < rr) & (r < 0.45))[..., None], C((236, 200, 170)), c)
    c = np.where((r > 0.45)[..., None], C((120, 26, 20)), c)
    return c


def menu_board(w=1024, h=256):
    """the red menu board over the counter (two panels, white type, like the photo)"""
    c = np.zeros((h, w, 3), np.float32) + C((196, 24, 30)) + TL.N3(w, 2, 40, 4, h)
    im, d = draw(c)
    left = ['SPAGHETTI ........ 9.25', 'MEATBALL HERO .... 8.50', 'SAUSAGE & PEPPERS  8.75', 'EGGPLANT PARM ... 10.50',
            'CHICKEN CUTLET ... 9.75', 'BAKED ZITI ....... 9.00', 'STUFFED SHELLS ... 9.50']
    right = ['CHEESE SLICE ..... 2.75', 'PEPPERONI SLICE .. 3.50', 'SICILIAN SQUARE .. 3.25', 'WHITE PIE ....... 18.00',
             'GARLIC KNOTS (6) . 3.00', 'CALZONE .......... 7.50', 'FOUNTAIN SODA .... 1.75']
    f_t = ML.font(30, serif=False); f = ML.font(19, serif=False)
    for k, (title, lines) in enumerate((('ITALIAN DISHES', left), ('PIZZA & MORE', right))):
        x0 = 16 + k * (w // 2)
        d.rectangle((x0, 10, x0 + w // 2 - 32, h - 10), outline=(250, 236, 220), width=4)
        tw = d.textlength(title, font=f_t)
        d.text((x0 + (w // 2 - 32 - tw) / 2, 18), title, font=f_t, fill=(255, 236, 160))
        for i, l in enumerate(lines):
            d.text((x0 + 18, 62 + i * 26), l, font=f, fill=(250, 250, 244))
    return arr(im)


def shop_sign(w=1024, h=192):
    c = np.zeros((h, w, 3), np.float32) + C((30, 110, 70)) + TL.N3(w, 2, 41, 4, h)
    im, d = draw(c)
    d.rectangle((6, 6, w - 7, h - 7), outline=(250, 236, 200), width=8)
    f = ML.font(96); t = "PADMAN'S PIZZA"; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2 + 4, 30), t, font=f, fill=(120, 20, 20))
    d.text(((w - tw) / 2, 26), t, font=f, fill=(252, 240, 210))
    f2 = ML.font(30, serif=False); t2 = 'SLICES  *  HEROS  *  SINCE 1994'; tw2 = d.textlength(t2, font=f2)
    d.text(((w - tw2) / 2, 140), t2, font=f2, fill=(250, 200, 80))
    return arr(im)


def mural(w=512, h=512):
    """original smiley-pizza mural: a big orange pie on maroon with a cream slice cut out, two eyes and a grin, painted
    inside the arch opening; the rest of the sign is brick like the wall round it. The sign spans 920 x 780 units
    (arch outer width, z 560..1340)."""
    SW, SH_ = 920.0, 780.0
    x, y = TL.xy(w)
    u = (x - 0.5) * SW; v = (1 - y) * SH_                    # u along the wall from the centre, v up from z 560
    zc = ARCH_H - ARCH_W / 2; r = ARCH_W / 2
    inside = (np.abs(u) < r) & ((v < zc) | (np.hypot(u, v - zc) < r))
    brick = TL.bricks((92, 52, 40), (60, 40, 32), rows=8, cols=4, vary=14, n=w)
    c = np.where(inside[..., None], C((112, 40, 44)) + TL.N3(w, 4, 42, 5), brick)
    im, d = draw(c)
    px = lambda uu, vv: (w / 2 + uu / SW * w, h - vv / SH_ * h)
    cx, cy = px(0, zc + 20)
    R = 300 / SW * w
    d.ellipse((cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8), fill=(150, 60, 40))
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(226, 104, 50))
    d.pieslice((cx - R, cy - R, cx + R, cy + R), -90, -30, fill=(236, 214, 170))
    d.line((cx, cy, cx, cy - R), fill=(150, 60, 40), width=5)
    d.line((cx, cy, cx + R * math.cos(math.radians(-30)), cy + R * math.sin(math.radians(-30))), fill=(150, 60, 40), width=5)
    for (ex, ey) in ((cx - R * 0.42, cy - R * 0.18), (cx + R * 0.10, cy - R * 0.18)):
        d.ellipse((ex - 18, ey - 30, ex + 18, ey + 30), fill=(244, 230, 200))
    d.arc((cx - R * 0.55, cy - R * 0.35, cx + R * 0.45, cy + R * 0.62), 25, 155, fill=(70, 24, 20), width=8)
    for (qx, qy) in ((cx - R * 0.6, cy + R * 0.35), (cx + R * 0.55, cy + R * 0.3), (cx - R * 0.1, cy + R * 0.72)):
        d.ellipse((qx - 16, qy - 16, qx + 16, qy + 16), fill=(170, 40, 34))
    return arr(im)


def lightbox(text, w=512, h=128):
    c = np.zeros((h, w, 3), np.float32) + C((240, 236, 226))
    im, d = draw(c)
    d.rectangle((4, 4, w - 5, h - 5), outline=(196, 24, 30), width=10)
    f = ML.font(84); tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, 12), text, font=f, fill=(196, 24, 30))
    return arr(im)


def _framed(fn, w=256, h=320, bg=(40, 34, 28)):
    c = np.zeros((h, w, 3), np.float32) + C(bg) + TL.N3(w, 3, 43, 8, h)
    im, d = draw(c)
    fn(d, w, h)
    d.rectangle((0, 0, w - 1, h - 1), outline=(176, 140, 60), width=18)
    d.rectangle((18, 18, w - 19, h - 19), outline=(120, 90, 40), width=4)
    return arr(im)


def still_life_fruit():
    def f(d, w, h):
        d.rectangle((18, 230, w - 18, h - 18), fill=(80, 52, 34))
        d.polygon([(70, 120), (186, 120), (176, 236), (80, 236)], fill=(70, 90, 120))          # jug
        d.ellipse((100, 96, 156, 130), fill=(80, 100, 132))
        for (x, y, r, col) in ((60, 236, 28, (200, 60, 40)), (110, 246, 24, (230, 170, 50)), (160, 238, 30, (120, 150, 50)),
                               (200, 244, 22, (110, 40, 80)), (136, 222, 18, (230, 200, 90))):
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return _framed(f)


def still_life_jug():
    def f(d, w, h):
        d.rectangle((18, 220, w - 18, h - 18), fill=(70, 46, 30))
        d.ellipse((60, 110, 200, 236), fill=(220, 214, 196)); d.rectangle((110, 70, 150, 130), fill=(220, 214, 196))
        d.arc((170, 120, 220, 200), 270, 90, fill=(220, 214, 196), width=10)
        d.line((70, 170, 190, 170), fill=(60, 80, 140), width=8)
        for k in range(5):
            d.ellipse((40 + k * 40, 236, 64 + k * 40, 262), fill=(90, 30, 90) if k % 2 else (150, 170, 60))
    return _framed(f)


def poster(w=256, h=384):
    """a 90s 'slice of the day' poster for the kitchen door side"""
    c = np.zeros((h, w, 3), np.float32) + C((250, 220, 90))
    im, d = draw(c)
    d.polygon([(w / 2, 70), (40, 300), (w - 40, 300)], fill=(226, 104, 50))
    d.polygon([(w / 2, 90), (60, 290), (w - 60, 290)], fill=(244, 200, 90))
    for (x, y) in ((110, 200), (150, 240), (128, 150), (90, 260), (170, 270)):
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=(176, 40, 34))
    f = ML.font(38); t = 'HOT SLICE'; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 16), t, font=f, fill=(176, 24, 30))
    f2 = ML.font(26, serif=False); t2 = '2 SLICES + SODA'; tw2 = d.textlength(t2, font=f2)
    d.text(((w - tw2) / 2, 316), t2, font=f2, fill=(40, 30, 20))
    d.text(((w - d.textlength('$5.99', font=f)) / 2, 340), '$5.99', font=f, fill=(176, 24, 30))
    return arr(im)


# ================================================================================================= model materials
def pizza_tex(n=256, slices=8):
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    cheese = TL.fill(n, (246, 206, 120), 3, 50) + TL.N3(n, 2, 51, 18) + TL.N3(n, 6, 52, 14)
    sauce = (TL.N3(n, 3, 53, 1)[..., 0] > 0.35)
    c = np.where(sauce[..., None], C((200, 70, 40)), cheese)
    rng = np.random.default_rng(54)
    for _ in range(14):
        a = rng.random() * 2 * math.pi; rr = rng.random() * 0.32
        px, py = 0.5 + rr * math.cos(a), 0.5 + rr * math.sin(a)
        c = np.where((np.hypot(x - px, y - py) < 0.045)[..., None], C((170, 40, 30)), c)
    c = np.where((r > 0.43)[..., None], C((210, 150, 80)) + TL.N3(n, 2, 55, 10), c)
    c = np.where((r > 0.49)[..., None], C((150, 96, 50)), c)
    if slices:
        ang = (np.arctan2(y - 0.5, x - 0.5) / (2 * math.pi) * slices) % 1
        cut = (ang < 0.015) | (ang > 0.985)
        c = np.where((cut & (r < 0.49))[..., None], c * 0.75, c)
    return c


def box_tex(w=256, h=256):
    """white pizza box lid with a red chef print"""
    c = TL.fill(w, (244, 240, 230), 2, 56)
    im, d = draw(c)
    d.ellipse((60, 40, 196, 176), outline=(196, 30, 30), width=8)
    d.ellipse((104, 66, 152, 110), fill=(196, 30, 30))
    d.rectangle((92, 110, 164, 150), fill=(196, 30, 30))
    f = ML.font(36); t = 'HOT & FRESH'; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 192), t, font=f, fill=(196, 30, 30))
    return arr(im)


def arcade_art(w=256, h=256):
    """original marquee art: a pizza-slice rocket blasting tomatoes"""
    c = np.zeros((h, w, 3), np.float32) + C((20, 20, 60))
    im, d = draw(c)
    rng = np.random.default_rng(59)
    for _ in range(40):
        sx, sy = rng.integers(0, w), rng.integers(0, 180)
        d.point((int(sx), int(sy)), fill=(250, 250, 250))
    d.polygon([(40, 150), (150, 110), (150, 190)], fill=(244, 200, 90))
    d.polygon([(132, 110), (150, 110), (150, 190), (132, 190)], fill=(210, 150, 80))
    for (qx, qy) in ((110, 140), (120, 165), (95, 152)):
        d.ellipse((qx - 7, qy - 7, qx + 7, qy + 7), fill=(176, 40, 34))
    d.polygon([(150, 125), (180, 150), (150, 175)], fill=(250, 120, 40))
    for k, (tx, ty) in enumerate(((200, 60), (226, 110), (196, 160))):
        d.ellipse((tx - 16, ty - 16, tx + 16, ty + 16), fill=(220, 40, 40)); d.rectangle((tx - 4, ty - 22, tx + 4, ty - 14), fill=(60, 160, 60))
    d.line((20, 150, 34, 150), fill=(250, 250, 120), width=4)
    f = ML.font(30, serif=False); t = 'PAD BLASTER'; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 206), t, font=f, fill=(250, 90, 200))
    return arr(im)


def arcade_art2(w=256, h=256):
    """original marquee art: a pizza-delivery scooter racing down a neon road"""
    c = np.zeros((h, w, 3), np.float32) + C((60, 10, 40))
    im, d = draw(c)
    d.polygon([(0, 190), (w, 190), (170, 70), (86, 70)], fill=(40, 40, 50))
    for k in range(5):
        y = 80 + k * 24
        d.line((128, y, 128, y + 10), fill=(250, 220, 60), width=3)
    d.line((86, 70, 0, 190), fill=(255, 60, 200), width=4); d.line((170, 70, w, 190), fill=(60, 220, 255), width=4)
    d.ellipse((70, 140, 100, 170), fill=(20, 20, 20)); d.ellipse((150, 140, 180, 170), fill=(20, 20, 20))
    d.rectangle((84, 120, 168, 150), fill=(230, 40, 40)); d.rectangle((136, 96, 168, 122), fill=(244, 240, 230))
    d.ellipse((90, 92, 116, 118), fill=(250, 210, 160))
    f = ML.font(30, serif=False); t = 'DOUGH RACER'; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 206), t, font=f, fill=(250, 220, 60))
    return arr(im)


def screen_tex(w=128, h=128):
    c = np.zeros((h, w, 3), np.float32) + C((10, 14, 30))
    im, d = draw(c)
    for k in range(6):
        for j in range(8):
            if (k + j) % 3: d.rectangle((8 + j * 14, 14 + k * 12, 16 + j * 14, 20 + k * 12), fill=(250, 220, 60) if k % 2 else (90, 220, 255))
    d.rectangle((54, 100, 74, 112), fill=(250, 250, 90))
    return arr(im)


def cooler_tex(w=256, h=512):
    """glass-door soda cooler front: shelves of cans and bottles behind the glass"""
    c = np.zeros((h, w, 3), np.float32) + C((30, 34, 40))
    im, d = draw(c)
    cols = [(200, 30, 40), (40, 90, 200), (60, 170, 70), (240, 180, 40), (230, 230, 230)]
    rng = np.random.default_rng(57)
    for s in range(5):
        y = 30 + s * 96
        d.rectangle((10, y + 76, w - 10, y + 82), fill=(150, 150, 156))
        x = 16
        while x < w - 30:
            cw = 26 + int(rng.integers(0, 8)); ch = 44 + int(rng.integers(0, 26))
            col = cols[int(rng.integers(0, len(cols)))]
            d.rounded_rectangle((x, y + 76 - ch, x + cw, y + 76), 6, fill=col)
            d.rectangle((x + 4, y + 76 - ch + 14, x + cw - 4, y + 76 - ch + 24), fill=(250, 250, 250))
            x += cw + 6
    return arr(im)


def atm_tex(w=256, h=256):
    c = np.zeros((h, w, 3), np.float32) + C((170, 176, 184))
    im, d = draw(c)
    d.rectangle((40, 20, 216, 120), fill=(30, 60, 100)); d.text((70, 50), 'WELCOME', font=ML.font(30, serif=False), fill=(200, 240, 255))
    for i in range(3):
        for j in range(4): d.rectangle((70 + i * 40, 140 + j * 26, 100 + i * 40, 160 + j * 26), fill=(60, 60, 64))
    d.rectangle((40, 248 - 8, 216, 252), fill=(40, 40, 44))
    d.rectangle((0, 0, w - 1, h - 1), outline=(120, 124, 130), width=6)
    return arr(im)


def register_tex(w=128, h=64):
    c = np.zeros((h, w, 3), np.float32) + C((40, 40, 44))
    im, d = draw(c)
    d.rectangle((10, 8, 118, 30), fill=(30, 200, 90)); d.text((18, 10), '$ 3.50', font=ML.font(18, serif=False), fill=(10, 40, 20))
    for i in range(6): d.rectangle((10 + i * 18, 38, 24 + i * 18, 56), fill=(200, 200, 196))
    return arr(im)


def soda_tex(w=256, h=128):
    c = np.zeros((h, w, 3), np.float32) + C((196, 24, 30))
    im, d = draw(c)
    for k, col in enumerate(((40, 30, 30), (240, 200, 40), (60, 170, 70), (230, 120, 40), (40, 100, 200), (240, 240, 240))):
        d.rounded_rectangle((12 + k * 40, 24, 46 + k * 40, 100), 8, fill=col)
    f = ML.font(18, serif=False); d.text((60, 106), 'ICE COLD SODA', font=f, fill=(250, 250, 250))
    return arr(im)


def flag_us(w=256, h=160):
    c = np.zeros((h, w, 3), np.float32)
    im, d = draw(c)
    for k in range(13):
        d.rectangle((0, k * h / 13, w, (k + 1) * h / 13), fill=(178, 34, 52) if k % 2 == 0 else (250, 250, 250))
    d.rectangle((0, 0, w * 0.4, h * 7 / 13), fill=(60, 59, 110))
    for i in range(6):
        for j in range(5):
            x, y = 8 + i * 16, 8 + j * 16
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(250, 250, 250))
    return arr(im)


def flag_it(w=256, h=160):
    c = np.zeros((h, w, 3), np.float32)
    c[:, :w // 3] = C((0, 146, 70)); c[:, w // 3:2 * w // 3] = C((244, 245, 240)); c[:, 2 * w // 3:] = C((206, 43, 55))
    return c


def awning_tex(n=256):
    """red / white / green stripes (Italian colours)"""
    x, y = TL.xy(n)
    k = ((x * 6) % 3).astype(int)
    cols = np.array([[196, 30, 36], [244, 240, 230], [30, 130, 70]], np.float32)
    return cols[k] + TL.N3(n, 2, 58, 5)


def news_tex(w=256, h=256):
    c = np.zeros((h, w, 3), np.float32) + C((30, 80, 160))
    im, d = draw(c)
    d.rectangle((30, 30, 226, 140), fill=(230, 230, 224))
    d.text((44, 40), 'DAILY PAD', font=ML.font(32), fill=(20, 20, 20))
    for k in range(5): d.line((44, 84 + k * 10, 212, 84 + k * 10), fill=(120, 120, 120), width=3)
    d.text((70, 170), '25c', font=ML.font(40, serif=False), fill=(250, 250, 250))
    return arr(im)


def sack_tex(w=256, h=256, text='FLOUR', col=(196, 30, 30)):
    c = TL.fabric((232, 222, 200), weave=64, n=w)
    im, d = draw(c)
    f = ML.font(52); tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, 90), text, font=f, fill=col)
    d.text(((w - d.textlength('00', font=f)) / 2, 150), '00', font=f, fill=col)
    return arr(im)


def materials():
    m('vinyl', TL.solid((200, 30, 30), 3, 60, 128) + TL.N3(128, 1, 61, 4), 'lms', v=0.12, shade=40)
    m('vinyl_dark', TL.solid((150, 22, 24), 3, 62, 128), 'lm', shade=40)
    m('woodlam', TL.planks((200, 168, 120), n_planks=8, gap=(176, 142, 96), grain=6, stagger=False), 'lm', shade=30)
    m('trim', TL.solid((96, 58, 34), 3, 63, 64), shade=30)
    m('chrome', TL.metal((200, 204, 210)), 'lms', v=0.35, shade=50)
    m('black', TL.solid((30, 30, 32), 2, 64, 64), shade=50)
    m('counterwood', TL.planks((150, 84, 46), n_planks=3, gap=(96, 52, 28), grain=8, vertical=True), shade=30)
    m('marble', TL.solid((44, 38, 36), 3, 65, 128) + TL.N3(128, 1, 66, 12), 'lms', v=0.1, shade=30)
    m('glass', TL.solid((180, 200, 210), 2, 67, 64), 'glass', c='0.08 0.09 0.10')
    m('pizza', pizza_tex(), shade=60)
    m('pizza_whole', pizza_tex(slices=0), shade=60)
    m('box', box_tex(), shade=30)
    m('box_side', TL.solid((236, 230, 216), 2, 68, 64), shade=30)
    m('cardboard', TL.solid((176, 140, 96), 3, 69, 128) + TL.N3(128, 1, 70, 6), shade=30)
    m('red_metal', TL.solid((190, 28, 32), 2, 71, 64), 'lms', v=0.12, shade=40)
    m('steel', TL.metal((190, 194, 200)), 'lms', v=0.18, shade=40)
    m('steel_dark', TL.metal((110, 114, 120)), 'lm', shade=40)
    m('soda', soda_tex(), shade=30)
    m('register', register_tex(), shade=30)
    m('atm', atm_tex(), shade=30)
    m('cooler', cooler_tex(), 'glow')
    m('cooler_body', TL.solid((220, 34, 40), 2, 72, 64), shade=30)
    m('arcade', arcade_art(), shade=30)
    m('arcade_body', TL.solid((40, 30, 80), 2, 73, 64), shade=30)
    m('arcade2', arcade_art2(), shade=30)
    m('arcade2_body', TL.solid((150, 20, 30), 2, 100, 64), shade=30)
    m('screen', screen_tex(), 'flicker')
    m('gum', TL.dots((240, 240, 240), (230, 60, 60), 8, r=0.3), shade=60)
    m('gumglass', TL.solid((200, 220, 230), 2, 74, 64), 'glass', c='0.12 0.13 0.15')
    m('chair_red', TL.solid((206, 36, 34), 3, 75, 64), 'lms', v=0.1, shade=40)
    m('pine', TL.planks((214, 176, 118), n_planks=4, gap=(170, 132, 86), grain=7), shade=30)
    m('brass', TL.metal((200, 160, 70)), 'lms', v=0.3, shade=50)
    m('fanwood', TL.planks((110, 64, 36), n_planks=2, gap=(80, 46, 26), grain=8, stagger=False), shade=30)
    m('lampglass', TL.solid((250, 236, 200), 2, 76, 64), 'glow')
    m('brick_oven', TL.bricks((150, 66, 48), (200, 190, 176), rows=6, cols=3), shade=30)
    m('oven_inside', TL.solid((40, 30, 26), 4, 77, 128) + TL.N3(128, 2, 78, 8), shade=30)
    m('deckstone', TL.solid((150, 120, 90), 4, 79, 128) + TL.N3(128, 1, 80, 10), shade=30)
    m('dough', TL.solid((240, 222, 186), 3, 81, 64) + TL.N3(64, 1, 82, 6), shade=60)
    m('sack', sack_tex(), shade=40)
    m('sack_plain', TL.fabric((232, 222, 200), weave=64), shade=40)
    m('plate', TL.solid((246, 246, 244), 2, 83, 64), 'lms', v=0.1, shade=60)
    m('hydrant', TL.solid((200, 36, 30), 3, 84, 64), 'lms', v=0.08, shade=50)
    m('basket', basket_tex(), 'alpha', alpha=basket_alpha())
    m('basket_rim', TL.solid((40, 90, 50), 2, 85, 64), shade=50)
    m('news', news_tex(), shade=30)
    m('newsbox', TL.solid((30, 80, 160), 2, 86, 64), shade=30)
    m('awning', awning_tex(), two=True, shade=30)
    m('flag_us', flag_us(), 'lm', two=True, deform='wave 64 sin 0 3 0 0.6')
    m('flag_it', flag_it(), 'lm', two=True, deform='wave 64 sin 0 3 0 0.6')
    m('frame_gold', TL.metal((190, 150, 70)), 'lms', v=0.25, shade=40)
    m('yellow', TL.solid((250, 210, 30), 2, 87, 64), shade=40)
    m('wetsign', wet_tex(), shade=30)
    m('tomato', TL.solid((200, 50, 36), 3, 88, 64) + TL.N3(64, 1, 89, 10), shade=60)
    m('cheese', TL.solid((250, 230, 160), 3, 90, 64) + TL.N3(64, 1, 91, 10), shade=60)
    m('jar', TL.solid((200, 214, 210), 2, 92, 64), 'glass', c='0.12 0.13 0.13')
    m('parm', TL.dots((240, 236, 220), (220, 210, 180), 10, r=0.25), shade=60)
    m('chili', TL.dots((190, 50, 30), (240, 200, 80), 10, r=0.25), shade=60)
    m('lid', TL.metal((210, 210, 214)), 'lms', v=0.3, shade=60)
    m('napkin', TL.solid((250, 250, 248), 1, 93, 64), shade=60)
    m('bucket', TL.solid((240, 210, 40), 2, 94, 64), shade=40)
    m('mopwater', TL.solid((120, 130, 110), 4, 95, 64), shade=40)
    m('rope', TL.fabric((220, 216, 200), weave=32), shade=60)
    m('green', TL.solid((40, 100, 60), 2, 96, 64), shade=40)
    m('peel', TL.planks((200, 160, 100), n_planks=6, gap=(170, 130, 80), grain=6, stagger=False), shade=30)
    m('tv_shelf', TL.solid((60, 60, 64), 2, 97, 64), shade=40)
    m('lamp', TL.solid((40, 50, 46), 2, 98, 64), shade=50)
    m('lampglow', TL.solid((255, 240, 200), 1, 99, 64), 'glow')


def basket_tex(n=128):
    return np.zeros((n, n, 3), np.float32) + C((40, 100, 56))


def basket_alpha(n=128):
    x, y = TL.xy(n)
    wire = ((x * 12) % 1 < 0.2) | ((y * 12) % 1 < 0.2)
    return np.where(wire, 255, 0).astype(np.uint8)


def wet_tex(w=256, h=256):
    c = np.zeros((h, w, 3), np.float32) + C((250, 210, 30))
    im, d = draw(c)
    d.polygon([(128, 30), (40, 170), (216, 170)], outline=(20, 20, 20), width=8)
    d.text((118, 80), '!', font=ML.font(70), fill=(20, 20, 20))
    f = ML.font(30, serif=False); t = 'WET FLOOR'; tw = d.textlength(t, font=f)
    d.text(((w - tw) / 2, 190), t, font=f, fill=(20, 20, 20))
    return arr(im)


# ================================================================================================= models
def booth(name, sides):
    """red molded booth along a wall: wall at x = 0, aisle at x = BOOTH_L, double back y -40..40 and a seat on
    each side in `sides` ('+' = seat at y 40..260, '-' = seat at y -260..-40)"""
    X = ML.Model()
    L = BOOTH_L
    bx(X, 'vinyl', (0, -BACK_T, 0), (L, BACK_T, BACK_Z), r=18, k=3, tile=128)
    boxes = [((0, -BACK_T, 0), (L - 4, BACK_T, BACK_Z))]
    for s in sides:
        g = 1 if s == '+' else -1
        y0, y1 = sorted((g * BACK_T, g * (BACK_T + SEAT_D)))
        bx(X, 'trim', (6, y0, 0), (L - 6, y1 - 6 * g if g < 0 else y1 - 6, 40), r=2)
        bx(X, 'vinyl_dark', (8, y0, 36), (L - 8, y1 - 8 if g > 0 else y1, SEAT_Z - 30), r=4)
        bx(X, 'vinyl', (0, y0, SEAT_Z - 34), (L, y1, SEAT_Z), r=14, k=3)
        # back cushion (slightly proud of the back slab) with a rolled top
        cy0, cy1 = sorted((g * BACK_T, g * (BACK_T + 26)))
        bx(X, 'vinyl', (12, cy0, SEAT_Z), (L - 12, cy1, BACK_Z - 50), r=12, k=3)
        boxes.append(((0, y0, 0), (L - 4, y1, SEAT_Z)))
    ML.save(name, X)
    coll(name, boxes)


def booth_table():
    X = ML.Model()
    L, W, T = TABLE_L, TABLE_W / 2, TABLE_T
    bx(X, 'woodlam', (0, -W, TABLE_Z - T + 4), (L, W, TABLE_Z), r=10, k=2, tile=256, faces='t')
    bx(X, 'chrome', (0, -W, TABLE_Z - T), (L, W, TABLE_Z), r=10, k=2, faces='nsewb')
    cylz(X, 'black', 330, 0, 26, 0, TABLE_Z - T, n=12, top=False)
    cylz(X, 'black', 330, 0, 120, 0, 10, n=20)
    bx(X, 'black', (0, -40, TABLE_Z - T - 30), (40, 40, TABLE_Z - T), r=2)        # wall bracket
    ML.save('booth_table', X)
    coll('booth_table', [((0, -W, TABLE_Z - T), (L, W, TABLE_Z))], [(330, 0, 26, 10, TABLE_Z - T)])


def condiments():
    """the table set: parmesan and chili-flake jars (glass with steel lids), salt, napkin dispenser"""
    X = ML.Model()
    for (cx, cy, fill) in ((0, 0, 'parm'), (44, 6, 'chili')):
        revolve(X.mesh(M_[fill]), [(15, 0), (15, 46)], n=12, cx=cx, cy=cy)
        revolve(X.mesh(M_['jar']), [(17, 0), (17, 52)], n=12, cx=cx, cy=cy)
        revolve(X.mesh(M_['lid']), [(17, 52), (17, 62), (12, 68), (0, 68)], n=12, cx=cx, cy=cy)
    bx(X, 'chrome', (-30, 40, 0), (60, 80, 70), r=6, k=2)
    bx(X, 'napkin', (-24, 34, 30), (54, 40, 64), r=1)
    ML.save('condiments', X)


def pizza_tray(name, slices=8, missing=0, r=140):
    """a pizza on a raised steel tray (missing = slices already sold)"""
    X = ML.Model()
    cylz(X, 'steel', 0, 0, 16, 0, 40, n=10, top=False)
    revolve(X.mesh(M_['steel']), [(r + 10, 40), (r + 14, 48), (r + 10, 48), (0, 46)], n=32)
    revolve(X.mesh(M_['steel']), [(0, 40), (r + 10, 40)], n=32, inward=True)
    sh = M_['pizza']
    a_skip = 2 * math.pi * missing / slices
    revolve(X.mesh(sh), [(r, 48), (r, 56)], n=32, a0=math.degrees(a_skip), a1=360)
    Mp = X.mesh(sh)
    n = 32
    for k in range(n):
        a0 = a_skip + (2 * math.pi - a_skip) * k / n; a1 = a_skip + (2 * math.pi - a_skip) * (k + 1) / n
        p0 = (0, 0, 56); p1 = (r * math.cos(a0), r * math.sin(a0), 56); p2 = (r * math.cos(a1), r * math.sin(a1), 56)
        uv = lambda p: (0.5 + p[0] / (2 * r) * 0.98, 0.5 - p[1] / (2 * r) * 0.98)
        Mp.poly([p0, p1, p2], (0, 0, 1), [uv(p0), uv(p1), uv(p2)])
    ML.save(name, X)


def counter():
    """the curved wood counter (front at y = 0, back at y = COUNTER_D, x 0..L) with a rounded west end"""
    L, D, H = COUNTER_L, COUNTER_D, COUNTER_Z
    X = ML.Model()
    r = D / 2
    bx(X, 'counterwood', (0, 0, 30), (L, D, H - 30), r=4, tile=256, faces='nseb')
    bx(X, 'black', (0, 12, 0), (L, D - 12, 30), r=1, faces='nse')
    revolve(X.mesh(M_['counterwood']), [(r, 30), (r, H - 30)], n=24, cx=0, cy=r, a0=90, a1=270, u_tiles=2)
    revolve(X.mesh(M_['black']), [(r - 12, 0), (r - 12, 30)], n=24, cx=0, cy=r, a0=90, a1=270)
    # marble top with a rounded end
    bx(X, 'marble', (0, -14, H - 30), (L + 14, D + 6, H), r=4, faces='nsetb')
    revolve(X.mesh(M_['marble']), [(r + 14, H - 30), (r + 14, H)], n=24, cx=0, cy=r, a0=90, a1=270)
    disc(X.mesh(M_['marble']), r + 14, H, up=True, n=24, cx=0, cy=r)
    # chrome kick rail and raised panel trims
    tube(X.mesh(M_['chrome']), [(0, -24, 60), (L, -24, 60)], [6, 6], nseg=8)
    for k in range(int((L - 60) // 290)):
        x0 = 60 + k * 290
        bx(X, 'trim', (x0, -4, 90), (x0 + 220, 2, H - 70), r=3)
    ML.save('counter', X)
    half = [(r * math.cos(a), r + r * math.sin(a)) for a in np.linspace(math.pi / 2, 3 * math.pi / 2, 9)]
    coll('counter', [((0, 0, 0), (L + 14, D, H))], hulls=[[(x, y, z) for (x, y) in half for z in (0, H)]])


def display_case():
    """glass slice case on the counter: steel base, glass front and top, pizzas on trays inside"""
    L, D, H = CASE_L, 280, CASE_H
    X = ML.Model()
    bx(X, 'steel', (0, 0, 0), (L, D, 24), r=3)
    for x in (0, L - 14):
        bx(X, 'steel', (x, 0, 24), (x + 14, D, H), r=2)
    bx(X, 'steel', (0, D - 10, 24), (L, D, H), r=1)
    G = X.mesh(M_['glass'])
    G.quad((14, 4, 24), (L - 14, 4, 24), (L - 14, 40, H), (14, 40, H))
    G.quad((14, 40, H), (L - 14, 40, H), (L - 14, D - 10, H), (14, D - 10, H))
    bx(X, 'steel', (0, 30, H - 4), (L, D, H), r=1, faces='t')
    for (x, miss) in ((L * 0.27, 2), (L * 0.73, 3)):
        Y = ML.Model()
        X.add_model(PIZ[miss], t=(x, 150, 24), sc=0.75)
    ML.save('display_case', X)
    coll('display_case', [((0, 0, 0), (L, D, H))])


PIZ = {}


def pizzas():
    for miss in (0, 2, 3):
        pizza_tray(f'pizza_tray{miss}', missing=miss)
        X = ML.Model()
        # keep a copy as a sub-model for the case (re-run the builder into a fresh model)
        PIZ[miss] = _tray_model(missing=miss)


def _tray_model(missing=0, r=140, slices=8):
    X = ML.Model()
    cylz(X, 'steel', 0, 0, 16, 0, 40, n=10, top=False)
    revolve(X.mesh(M_['steel']), [(r + 10, 40), (r + 14, 48), (r + 10, 48), (0, 46)], n=32)
    sh = M_['pizza']
    a_skip = 2 * math.pi * missing / slices
    Mp = X.mesh(sh)
    n = 32
    for k in range(n):
        a0 = a_skip + (2 * math.pi - a_skip) * k / n; a1 = a_skip + (2 * math.pi - a_skip) * (k + 1) / n
        p0 = (0, 0, 56); p1 = (r * math.cos(a0), r * math.sin(a0), 56); p2 = (r * math.cos(a1), r * math.sin(a1), 56)
        uv = lambda p: (0.5 + p[0] / (2 * r) * 0.98, 0.5 - p[1] / (2 * r) * 0.98)
        Mp.poly([p0, p1, p2], (0, 0, 1), [uv(p0), uv(p1), uv(p2)])
    revolve(X.mesh(sh), [(r, 48), (r, 56)], n=32, a0=math.degrees(a_skip), a1=360)
    return X


def register():
    X = ML.Model()
    bx(X, 'black', (-90, -70, 0), (90, 70, 70), r=6)
    P = X.mesh(M_['register'])
    pic(P, (0, -78, 50), (0, -1, 0.4), 160, 60)
    bx(X, 'black', (-60, 20, 70), (60, 60, 150), r=6)
    pic(X.mesh(M_['screen']), (0, 19, 120), (0, -1, 0), 100, 50)
    bx(X, 'black', (-80, -60, -0), (80, -20, 16), r=2)
    ML.save('register', X)
    coll('register', [((-90, -70, 0), (90, 70, 150))])


def soda_fountain():
    X = ML.Model()
    W, D, H = 280, 160, 340
    bx(X, 'red_metal', (0, 0, 0), (W, D, H), r=10, k=2)
    pic(X.mesh(M_['soda']), (W / 2, -1, H - 90), (0, -1, 0), W - 30, 120)
    bx(X, 'steel', (10, -60, 0), (W - 10, 10, 20), r=4)                  # drip tray
    for k in range(6):
        cylz(X, 'chrome', 30 + k * 44, -22, 7, 140, 168, n=8)
    bx(X, 'steel', (0, -40, 168), (W, 10, 200), r=4)
    ML.save('soda_fountain', X)
    coll('soda_fountain', [((0, -40, 0), (W, D, H))])


def pizza_boxes(name, n, rot=0.0, seed=1):
    """a stack of n pizza boxes (each 26u, 240u square), slightly skewed"""
    X = ML.Model()
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = math.radians(rot + rng.uniform(-6, 6))
        z0 = k * 26
        Y = ML.Model()
        bx(Y, 'box_side', (-120, -120, 0), (120, 120, 24), r=2, faces='nsewb')
        Y.mesh(M_['box']).quad((-118, -118, 25), (118, -118, 25), (118, 118, 25), (-118, 118, 25), tile=236)
        X.add_model(Y, R=rot_z(a), t=(rng.uniform(-6, 6), rng.uniform(-6, 6), z0))
    ML.save(name, X)
    coll(name, [((-110, -110, 0), (110, 110, n * 26))])


def menu_shelf():
    """steel bracket shelf for the pizza boxes under the menu board (x 0..L along the back wall, y 0..D out)"""
    X = ML.Model()
    L, D = SHELF_L, 260
    bx(X, 'steel', (0, 0, -20), (L, D, 0), r=2)
    for x in (40, L / 2, L - 40):
        X.mesh(M_['steel_dark']).quad((x - 4, 0, -110), (x + 4, 0, -110), (x + 4, D - 10, -20), (x - 4, D - 10, -20), tile=64,
                                       n=(0, -0.7, 0.7))
    ML.save('menu_shelf', X)


def cooler():
    """glass-door soda cooler: x 0..d (wall at x = d), y -w/2..w/2, glowing shelves behind the glass"""
    d, w, h = COOLER
    X = ML.Model()
    bx(X, 'cooler_body', (0, -w / 2, 0), (d, w / 2, h), r=8, k=2, faces='nstb')
    bx(X, 'cooler_body', (0, -w / 2, h - 140), (6, w / 2, h), r=2, faces='w')
    bx(X, 'cooler_body', (0, -w / 2, 0), (6, w / 2, 80), r=2, faces='w')
    pic(X.mesh(M_['cooler']), (-1, 0, (80 + h - 140) / 2), (-1, 0, 0), w - 40, h - 220)
    bx(X, 'chrome', (-30, w / 2 - 50, 300), (-6, w / 2 - 34, 700), r=6)               # handle
    pic(X.mesh(M_['soda']), (-1, 0, h - 70), (-1, 0, 0), w - 30, 110)
    ML.save('cooler', X)
    coll('cooler', [((-30, -w / 2, 0), (d, w / 2, h))])


def atm():
    d, w, h = ATM
    X = ML.Model()
    bx(X, 'steel_dark', (0, -w / 2, 0), (d, w / 2, h), r=8, k=2)
    P = X.mesh(M_['atm'])
    P.poly([(-1, w / 2 - 15, h - 80), (-1, -w / 2 + 15, h - 80), (-60, -w / 2 + 15, h - 330), (-60, w / 2 - 15, h - 330)],
           (-0.97, 0, 0.24), [(0, 0), (1, 0), (1, 1), (0, 1)])
    bx(X, 'steel_dark', (-60, -w / 2, 0), (0, w / 2, h - 330), r=6)
    bx(X, 'black', (-20, -w / 2 + 10, h - 70), (0, w / 2 - 10, h - 10), r=2)
    ML.save('atm', X)
    coll('atm', [((-60, -w / 2, 0), (d, w / 2, h))])


def arcade(name='arcade', art='arcade', body='arcade_body'):
    """upright arcade cabinet (front faces -x), 150 x 170 x 860"""
    X = ML.Model()
    bx(X, body, (0, -85, 0), (150, 85, 860), r=6, faces='nsetb')
    bx(X, body, (60, -85, 0), (150, 85, 860), r=6, faces='w')
    bx(X, body, (-10, -85, 0), (60, 85, 420), r=6, faces='w')
    pic(X.mesh(M_[art]), (59, 0, 760), (-1, 0, 0), 160, 150)
    pic(X.mesh(M_['screen']), (59, 0, 560), (-1, 0, 0.25), 140, 130)
    bx(X, 'black', (-40, -85, 420), (60, 85, 450), r=4)
    for (y, col) in ((-30, 'red_metal'), (20, 'yellow'), (45, 'chair_red')):
        cylz(X, col, -10, y, 8, 450, 460, n=8)
    cylz(X, 'black', -14, -50, 4, 450, 490, n=6)
    sphere(X.mesh(M_['red_metal']), (-14, -50, 494), 9, nu=8, nv=6)
    ML.save(name, X)
    coll(name, [((-40, -85, 0), (150, 85, 860))])


def gumball():
    X = ML.Model()
    revolve(X.mesh(M_['red_metal']), [(60, 0), (60, 10), (20, 20), (18, 140), (46, 150), (46, 200), (0, 204)], n=16)
    sphere(X.mesh(M_['gum']), (0, 0, 262), 52, nu=14, nv=10)
    sphere(X.mesh(M_['gumglass']), (0, 0, 262), 58, nu=14, nv=10)
    revolve(X.mesh(M_['red_metal']), [(30, 314), (30, 330), (0, 334)], n=12)
    bx(X, 'chrome', (-14, -52, 160), (14, -44, 190), r=2)
    ML.save('gumball', X)
    coll('gumball', cyls=[(0, 0, 60, 0, 334)])


def two_top():
    """round café table for two (top r 150)"""
    X = ML.Model()
    revolve(X.mesh(M_['woodlam']), [(TWO_TOP_R, TWO_TOP_Z), (0, TWO_TOP_Z)], n=24, inward=True)
    revolve(X.mesh(M_['chrome']), [(TWO_TOP_R - 2, TWO_TOP_Z - 20), (TWO_TOP_R, TWO_TOP_Z - 20), (TWO_TOP_R, TWO_TOP_Z), (TWO_TOP_R - 2, TWO_TOP_Z)], n=24)
    disc(X.mesh(M_['black']), TWO_TOP_R, TWO_TOP_Z - 20, up=False, n=24)
    cylz(X, 'black', 0, 0, 20, 0, TWO_TOP_Z - 20, n=10, top=False)
    revolve(X.mesh(M_['black']), [(100, 0), (100, 8), (20, 18), (0, 18)], n=16)
    ML.save('two_top', X)
    coll('two_top', [((-TWO_TOP_R + 12, -TWO_TOP_R + 12, TWO_TOP_Z - 20), (TWO_TOP_R - 12, TWO_TOP_R - 12, TWO_TOP_Z))],
         [(0, 0, 20, 8, TWO_TOP_Z - 20)])


def chair():
    """red molded café chair facing +x (seat 225)"""
    X = ML.Model()
    s = 110
    for (x, y) in ((-s + 10, -s + 10), (s - 10, -s + 10), (-s + 10, s - 10), (s - 10, s - 10)):
        cylz(X, 'chrome', x, y, 7, 0, CHAIR_SEAT - 24, n=8, top=False)
    bx(X, 'chair_red', (-s, -s, CHAIR_SEAT - 24), (s, s, CHAIR_SEAT), r=10, k=2)
    bx(X, 'chair_red', (-s, -s, CHAIR_SEAT), (-s + 24, s, CHAIR_SEAT + 230), r=10, k=2)
    for y in (-s + 12, s - 12):
        cylz(X, 'chrome', -s + 12, y, 6, CHAIR_SEAT, CHAIR_SEAT + 210, n=6, top=False)
    ML.save('chair', X)
    coll('chair', [((-s, -s, 0), (s, s, CHAIR_SEAT)), ((-s, -s, CHAIR_SEAT), (-s + 24, s, CHAIR_SEAT + 230))])


def high_chair():
    X = ML.Model()
    h = 400
    for (x, y) in ((-70, -70), (70, -70), (-70, 70), (70, 70)):
        tube(X.mesh(M_['pine']), [(x * 1.3, y * 1.3, 0), (x * 0.8, y * 0.8, h)], [8, 7], nseg=8)
    bx(X, 'pine', (-70, -70, h - 20), (70, 70, h), r=4)
    bx(X, 'pine', (-70, 52, h), (70, 70, h + 160), r=4)
    for y in (-70, 70):
        bx(X, 'pine', (-70, y - 8, h + 80), (70, y + 8, h + 92), r=3)
    bx(X, 'pine', (-110, -110, 160), (110, 110, 176), r=3)            # foot ring shelf
    ML.save('high_chair', X)
    coll('high_chair', [((-80, -80, 0), (80, 80, h)), ((-70, 52, h), (70, 70, h + 160))])


def ceiling_fan():
    """the static mount (downrod + motor + light) and the rotating blades (model2, centred on the axis)"""
    X = ML.Model()
    cylz(X, 'brass', 0, 0, 40, -16, 0, n=16)
    cylz(X, 'brass', 0, 0, 7, -120, -16, n=8, top=False)
    revolve(X.mesh(M_['brass']), [(0, -190), (44, -185), (56, -160), (50, -130), (30, -120), (0, -120)], n=20)
    revolve(X.mesh(M_['lampglass']), [(0, -250), (34, -240), (44, -210), (40, -190), (0, -190)], n=16, inward=True)
    ML.save('fan_mount', X)
    B = ML.Model()
    for k in range(4):
        a = k * math.pi / 2
        R = rot_z(a)
        Y = ML.Model()
        bx(Y, 'fanwood', (60, -34, -6), (330, 34, 2), r=3)
        bx(Y, 'brass', (20, -10, -8), (80, 10, 4), r=2)
        B.add_model(Y, R=R)
    revolve(B.mesh(M_['brass']), [(0, -14), (40, -12), (40, 8), (0, 10)], n=16)
    ML.save('fan_blades', B)


def oven():
    """two-deck pizza oven (front at y = 0, x -W/2..W/2): stainless body on legs, the lower deck door open so you
    can walk into the chamber, flat top you can stand on"""
    W, D, H = OVEN
    ch0, ch1 = OVEN_CH
    dx0, dx1 = OVEN_DOOR
    X = ML.Model()
    t = 40
    for x in (-W / 2 + 20, W / 2 - 60):
        for y in (20, D - 60):
            bx(X, 'steel_dark', (x, y, 0), (x + 40, y + 40, ch0 - 40), r=3)
    bx(X, 'steel', (-W / 2, 0, ch0 - 40), (W / 2, D, ch0), r=3)                      # lower deck floor slab
    bx(X, 'deckstone', (dx0, t, ch0 - 1), (dx1, D - t, ch0), r=0, faces='t')
    # walls of the lower chamber
    bx(X, 'steel', (-W / 2, 0, ch0), (dx0, D, ch1), r=3, faces='nsewt')
    bx(X, 'steel', (dx1, 0, ch0), (W / 2, D, ch1), r=3, faces='nsewt')
    bx(X, 'steel', (dx0, D - t, ch0), (dx1, D, ch1), r=2, faces='nstb')
    bx(X, 'oven_inside', (dx0, D - t - 1, ch0), (dx1, D - t, ch1), r=0, faces='s')
    X.mesh(M_['oven_inside']).quad((dx0 + 1, t, ch0), (dx0 + 1, D - t, ch0), (dx0 + 1, D - t, ch1), (dx0 + 1, t, ch1), n=(1, 0, 0))
    X.mesh(M_['oven_inside']).quad((dx1 - 1, D - t, ch0), (dx1 - 1, t, ch0), (dx1 - 1, t, ch1), (dx1 - 1, D - t, ch1), n=(-1, 0, 0))
    # upper body (closed upper deck + crown)
    bx(X, 'steel', (-W / 2, 0, ch1), (W / 2, D, H), r=6, k=2)
    X.mesh(M_['oven_inside']).quad((dx1, t, ch1 - 1), (dx0, t, ch1 - 1), (dx0, D - t, ch1 - 1), (dx1, D - t, ch1 - 1), n=(0, 0, -1))
    bx(X, 'black', (-W / 2 + 60, -6, ch1 + 120), (W / 2 - 60, 0, ch1 + 300), r=3)    # upper door
    tube(X.mesh(M_['chrome']), [(-W / 2 + 120, -30, ch1 + 270), (W / 2 - 120, -30, ch1 + 270)], [10, 10], nseg=8)
    for x in (-W / 2 + 120, W / 2 - 120):
        tube(X.mesh(M_['chrome']), [(x, 0, ch1 + 270), (x, -30, ch1 + 270)], [6, 6], nseg=6, caps=(False, False))
    for k in range(3):
        cylz(X, 'black', -W / 2 + 80 + k * 40, -6, 12, ch1 + 40, ch1 + 52, n=8)
    # pizzas baking inside
    X.add_model(PIZ[0], t=(-140, 300, ch0), sc=0.8)
    X.add_model(PIZ[0], t=(150, 360, ch0), sc=0.8)
    # flue at the back right
    cylz(X, 'steel_dark', W / 2 - 100, D - 100, 50, H, H + 2, n=12)
    ML.save('oven', X)
    coll('oven', [((-W / 2, 0, 0), (W / 2, D, ch0)), ((-W / 2, 0, ch0), (dx0, D, ch1)), ((dx1, 0, ch0), (W / 2, D, ch1)),
                  ((dx0, D - t, ch0), (dx1, D, ch1)), ((-W / 2, 0, ch1), (W / 2, D, H))])


def peel():
    """giant pizza peel leaning on the open oven mouth: a ramp from the floor (y = 0) to the deck (y = L, z = ch0)"""
    L, W = 330, 300
    z1 = OVEN_CH[0]
    X = ML.Model()
    n = (0, -z1, L); nn = np.array(n, float) / np.linalg.norm(n)
    off = nn * 3
    P = X.mesh(M_['peel'])
    P.poly([tuple(np.array(p) + off) for p in ((-W / 2, 0, 0), (W / 2, 0, 0), (W / 2, L, z1), (-W / 2, L, z1))], tuple(nn),
           [(0, 0), (W / 128, 0), (W / 128, L / 128), (0, L / 128)])
    tube(X.mesh(M_['peel']), [(0, -4, 6), (0, -90, 6)], [10, 10], nseg=8)
    ML.save('peel', X)


def prep_table():
    """stainless prep table (x -300..300, y -150..150, top 450) with an under-shelf of tins, dough balls on top"""
    X = ML.Model()
    for x in (-280, 260):
        for y in (-130, 110):
            bx(X, 'steel', (x, y, 0), (x + 20, y + 20, PREP_Z - 20), r=2)
    bx(X, 'steel', (-300, -150, PREP_Z - 20), (300, 150, PREP_Z), r=3)
    bx(X, 'steel', (-290, -140, 130), (290, 140, 140), r=1)
    for k in range(5):
        ellipsoid(X.mesh(M_['dough']), (-200 + k * 90, -40, PREP_Z + 10), 38, 38, 26, nu=12, nv=6, flat_bottom=-10)
    revolve(X.mesh(M_['steel']), [(70, PREP_Z), (80, PREP_Z + 80), (0, PREP_Z + 80)], n=16, cx=170, cy=70, inward=False)
    disc(X.mesh(M_['tomato']), 72, PREP_Z + 70, n=16, cx=170, cy=70)
    revolve(X.mesh(M_['steel']), [(60, PREP_Z), (70, PREP_Z + 60), (0, PREP_Z + 60)], n=16, cx=-60, cy=80)
    disc(X.mesh(M_['cheese']), 62, PREP_Z + 52, n=16, cx=-60, cy=80)
    ML.save('prep_table', X)
    coll('prep_table', [((-300, -150, PREP_Z - 20), (300, 150, PREP_Z))],
         [(x + 10, y + 10, 12, 0, PREP_Z - 20) for x in (-280, 260) for y in (-130, 110)])


def mixer():
    """floor dough mixer (front faces -y), 360 x 300, 700 tall"""
    X = ML.Model()
    bx(X, 'steel_dark', (-180, -150, 0), (180, 150, 80), r=6)
    bx(X, 'steel', (-60, 40, 80), (60, 150, 700), r=20, k=3)
    bx(X, 'steel', (-80, -120, 560), (80, 150, 700), r=30, k=3)
    revolve(X.mesh(M_['steel']), [(0, 200), (120, 210), (140, 380), (146, 390), (140, 392), (118, 230), (0, 222)], n=24, cy=-30)
    ellipsoid(X.mesh(M_['dough']), (0, -30, 330), 110, 110, 50, nu=16, nv=8)
    cylz(X, 'steel', 0, -30, 10, 380, 560, n=8, top=False)
    ML.save('mixer', X)
    coll('mixer', [((-180, -150, 0), (180, 150, 80)), ((-60, 112, 80), (60, 150, 560)), ((-80, -120, 560), (80, 150, 700))],
         [(0, -30, 140, 80, 392)])


def flour_sacks():
    X = ML.Model()
    for (x, y, z, a) in ((0, 0, 0, 0), (130, 20, 0, 0.3), (60, 10, 90, 0.15)):
        Y = ML.Model()
        rbox(Y.mesh(M_['sack_plain']), (-70, -100, 0), (70, 100, 90), r=30, k=3, faces='nswtb')
        rbox(Y.mesh(M_['sack']), (-70, -100, 0), (70, 100, 90), r=30, k=3, faces='e')
        X.add_model(Y, R=rot_z(a), t=(x, y, z))
    ML.save('flour_sacks', X)
    coll('flour_sacks', [((-70, -100, 0), (200, 120, 90)), ((-10, -90, 90), (130, 110, 180))])


def tomato_case():
    """open cardboard case of big tomato tins"""
    X = ML.Model()
    bx(X, 'cardboard', (-120, -90, 0), (120, 90, 60), r=2, faces='nsewb')
    for i in range(3):
        for j in range(2):
            revolve(X.mesh(M_['tomato']), [(36, 0), (36, 110)], n=12, cx=-80 + i * 80, cy=-45 + j * 90)
            disc(X.mesh(M_['lid']), 36, 110, n=12, cx=-80 + i * 80, cy=-45 + j * 90)
    ML.save('tomato_case', X)
    coll('tomato_case', [((-120, -90, 0), (120, 90, 110))])


def can_rack():
    """steel wire rack of tins and boxes (x 0..W along the wall, y 0..D out, wall at y = D), shelves 300/600/900"""
    W, D = 320, 250
    X = ML.Model()
    for x in (0, W - 12):
        for y in (0, D - 12):
            bx(X, 'chrome', (x, y, 0), (x + 12, y + 12, 1000), r=2)
    for z in (60, 360, 660, 960):
        bx(X, 'chrome', (0, 0, z - 8), (W, D, z), r=1)
    for k, z in enumerate((60, 360, 660)):
        for i in range(3):
            revolve(X.mesh(M_['tomato']), [(36, z), (36, z + 110)], n=12, cx=60 + i * 100, cy=D / 2)
            disc(X.mesh(M_['lid']), 36, z + 110, n=12, cx=60 + i * 100, cy=D / 2)
    bx(X, 'cardboard', (20, 30, 960), (300, 220, 1080), r=2)
    ML.save('can_rack', X)
    coll('can_rack', [((0, 0, 0), (W, D, 1080))])


def sink_dress():
    """faucet + plate stack art for the sink (the basin itself is brushes): plates as the stair out of the water"""
    X = ML.Model()
    # gooseneck faucet on the back rim (x local 0 = wall side)
    tube(X.mesh(M_['chrome']), [(0, 0, 0), (0, 0, 180), (-40, 0, 230), (-110, 0, 220), (-130, 0, 180)], [12, 11, 10, 9, 9], nseg=10)
    revolve(X.mesh(M_['chrome']), [(22, 0), (22, 12), (0, 14)], n=12)
    for y in (-50, 50):
        revolve(X.mesh(M_['chrome']), [(10, 0), (10, 40), (16, 46), (0, 48)], n=8, cy=y)
    ML.save('faucet', X)


def plate_steps(n_steps, step_h, tread, width):
    """stacks of plates, one per stair tread (stack k is k+1 steps tall), running +y"""
    X = ML.Model()
    for k in range(n_steps):
        top = (k + 1) * step_h
        y0 = k * tread
        z = 0
        while z < top - 1:
            zz = min(z + 8, top)
            revolve(X.mesh(M_['plate']), [(width / 2 - 4, z), (width / 2, zz - 2), (width / 2 - 2, zz), (0, zz)], n=20,
                    cx=0, cy=y0 + tread / 2)
            z = zz
    ML.save('plate_steps', X)


def hydrant():
    X = ML.Model()
    revolve(X.mesh(M_['hydrant']), [(46, 0), (46, 14), (34, 20), (34, 210), (40, 216), (40, 230), (28, 250), (20, 270), (6, 286), (0, 288)], n=16)
    for a in (0, math.pi):
        tube(X.mesh(M_['hydrant']), [(0, 0, 150), (54 * math.cos(a), 54 * math.sin(a), 150)], [16, 16], nseg=10)
    tube(X.mesh(M_['hydrant']), [(0, 0, 140), (0, -58, 140)], [22, 22], nseg=10)
    ML.save('hydrant', X)
    coll('hydrant', cyls=[(0, 0, 44, 0, 288)])


def trash_basket():
    X = ML.Model()
    revolve(X.mesh(M_['basket']), [(110, 0), (130, 420)], n=20, u_tiles=4)
    revolve(X.mesh(M_['basket_rim']), [(126, 400), (138, 410), (138, 430), (126, 430)], n=20)
    disc(X.mesh(M_['basket_rim']), 110, 6, n=20)
    ellipsoid(X.mesh(M_['black']), (0, 0, 300), 100, 100, 110, nu=12, nv=6)
    ML.save('trash_basket', X)
    coll('trash_basket', cyls=[(0, 0, 125, 0, 430)])


def newsbox():
    X = ML.Model()
    bx(X, 'newsbox', (-100, -90, 120), (100, 90, 440), r=10, k=2, faces='nsewt')
    for (x, y) in ((-80, -70), (70, -70), (-80, 60), (70, 60)):
        bx(X, 'black', (x, y, 0), (x + 10, y + 10, 120), r=1)
    pic(X.mesh(M_['news']), (0, -91, 300), (0, -1, 0), 180, 180)
    ML.save('newsbox', X)
    coll('newsbox', [((-100, -90, 0), (100, 90, 440))])


def street_lamp():
    X = ML.Model()
    revolve(X.mesh(M_['lamp']), [(40, 0), (40, 60), (20, 80), (14, 1700), (0, 1702)], n=12)
    tube(X.mesh(M_['lamp']), [(0, 0, 1650), (0, 120, 1720), (0, 300, 1720)], [10, 9, 8], nseg=8)
    bx(X, 'lamp', (-50, 260, 1680), (50, 400, 1730), r=10)
    X.mesh(M_['lampglow']).quad((-40, 270, 1678), (40, 270, 1678), (40, 390, 1678), (-40, 390, 1678), n=(0, 0, -1))
    ML.save('street_lamp', X)
    coll('street_lamp', cyls=[(0, 0, 30, 0, 1700)])


def wet_sign():
    """yellow A-frame wet-floor sign; both faces read the right way round"""
    X = ML.Model()
    L = math.hypot(74, 300)
    for s in (-1, 1):
        n = np.array([0, s * 300, 74]) / L
        up = np.array([0, -s * 74, 300]) / L
        pic(X.mesh(M_['wetsign']), (0, s * 43, 150), n, 140, L, up=up)
    ML.save('wet_sign', X)
    coll('wet_sign', [((-70, -60, 0), (70, 60, 290))])


def flags():
    for key, name in (('flag_us', 'flag_us'), ('flag_it', 'flag_it')):
        X = ML.Model()
        tube(X.mesh(M_['brass']), [(0, 0, 0), (130, 0, 130)], [5, 5], nseg=6)          # pole out of the wall (x = out)
        sphere(X.mesh(M_['brass']), (134, 0, 134), 9, nu=8, nv=6)
        P = X.mesh(M_[key])
        top = [(30 + t * 100, 0, 30 + t * 100) for t in (0, 1)]
        P.poly([top[0], top[1], (top[1][0], 0, top[1][2] - 130), (top[0][0], 0, top[0][2] - 130)], (0, -1, 0),
               [(0, 0), (1, 0), (1, 1), (0, 1)])
        ML.save(name, X)


def frame_gold(w, h, name):
    X = ML.Model()
    b = 18
    for (a, c) in (((0, -w / 2, 0), (8, w / 2, b)), ((0, -w / 2, h - b), (8, w / 2, h)), ((0, -w / 2, 0), (8, -w / 2 + b, h)),
                   ((0, w / 2 - b, 0), (8, w / 2, h))):
        bx(X, 'frame_gold', a, c, r=3)
    ML.save(name, X)


def arch():
    """brick arch frame round the mural on the west wall (x = out of the wall, y along it), opening w x h"""
    w, h, t, d = ARCH_W, ARCH_H, ARCH_T, 24
    X = ML.Model()
    m_ = M_['brick_oven']
    r = w / 2
    zc = h - r
    # two legs
    for y0 in (-r - t, r):
        rbox(X.mesh(m_), (0, y0, 0), (d, y0 + t, zc), r=2, k=1, tile=128)
    # the arch ring
    n = 18
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        pts = []
        for (rr, a) in ((r, a0), (r + t, a0), (r + t, a1), (r, a1)):
            pts.append((0, rr * math.cos(a), zc + rr * math.sin(a)))
        q = [np.array(p) for p in pts]
        P = X.mesh(m_)
        front = [tuple(p + np.array([d, 0, 0])) for p in q]
        P.poly(front[::-1], (1, 0, 0), [(p[1] / 128, -p[2] / 128) for p in front[::-1]])
        # inner and outer soffits
        for (i0, i1, s) in ((0, 3, -1), (1, 2, 1)):
            A, B = q[i0], q[i1]
            nrm = (0, s * math.cos((a0 + a1) / 2), s * math.sin((a0 + a1) / 2))
            quad = [tuple(A), tuple(B), tuple(B + [d, 0, 0]), tuple(A + [d, 0, 0])]
            if s < 0: quad = quad[::-1]
            P.poly(quad, nrm, [(0, 0), (1, 0), (1, 0.2), (0, 0.2)])
    ML.save('arch', X)


def awning_valance():
    """scalloped striped valance hanging under the awning's front edge (x along the facade, y = out)"""
    L = VALANCE_L
    X = ML.Model()
    P = X.mesh(M_['awning'])
    n = 24
    for k in range(n):
        x0 = -L / 2 + L * k / n; x1 = x0 + L / n
        xm = (x0 + x1) / 2
        P.poly([(x0, 0, 0), (x1, 0, 0), (x1, 0, -60), (xm, 0, -80), (x0, 0, -60)], (0, -1, 0),
               [(x0 / 256, 0), (x1 / 256, 0), (x1 / 256, 0.24), (xm / 256, 0.32), (x0 / 256, 0.24)])
    ML.save('valance', X)


def door_leaf():
    """propped-open glass shop door with a chrome frame (lies flat against the facade, x along it)"""
    W, H = 500, 1080
    X = ML.Model()
    for (a, b) in (((0, 0, 0), (W, 10, 50)), ((0, 0, H - 50), (W, 10, H)), ((0, 0, 0), (40, 10, H)), ((W - 40, 0, 0), (W, 10, H)),
                   ((0, 0, 480), (W, 10, 520))):
        bx(X, 'chrome', a, b, r=2)
    G = X.mesh(M_['glass'])
    G.quad((40, 5, 50), (W - 40, 5, 50), (W - 40, 5, H - 50), (40, 5, H - 50))
    bx(X, 'chrome', (60, -30, 560), (80, 0, 760), r=4)
    ML.save('door_leaf', X)


def tv_bracket():
    """wall shelf for the CRT TV (x = out of the wall)"""
    X = ML.Model()
    bx(X, 'tv_shelf', (0, -130, -16), (200, 130, 0), r=2)
    for y in (-110, 110):
        X.mesh(M_['tv_shelf']).quad((0, y, -150), (0, y, -16), (190, y, -16), (0, y, -150), n=(0, -1, 0))
    ML.save('tv_bracket', X)


def mop_bucket():
    X = ML.Model()
    revolve(X.mesh(M_['bucket']), [(90, 0), (110, 150), (104, 150), (86, 10), (0, 10)], n=16)
    disc(X.mesh(M_['mopwater']), 100, 120, n=16)
    tube(X.mesh(M_['pine']), [(40, 0, 20), (60, 0, 620)], [8, 8], nseg=6)
    ML.save('mop_bucket', X)
    coll('mop_bucket', cyls=[(0, 0, 105, 0, 150)])


def bus_bin():
    """grey bus tub of dirty dishes on the kitchen floor"""
    X = ML.Model()
    bx(X, 'steel_dark', (-130, -90, 0), (130, 90, 90), r=8, faces='nsewb')
    for k in range(4):
        revolve(X.mesh(M_['plate']), [(70, 60 + k * 6), (70, 64 + k * 6), (0, 64 + k * 6)], n=16, cx=-50, cy=0)
    ML.save('bus_bin', X)
    coll('bus_bin', [((-130, -90, 0), (130, 90, 90))])


def all_models():
    booth('booth_double', '+-'); booth('booth_end_n', '+'); booth('booth_end_s', '-')
    booth_table(); condiments()
    pizzas()
    counter(); display_case(); register(); soda_fountain()
    for k, (n, rot) in enumerate(((4, 0), (3, 20), (5, 8), (2, 35), (6, 4))):
        pizza_boxes(f'boxes{n}', n, rot, seed=k + 1)
    menu_shelf(); cooler(); atm(); arcade(); arcade('arcade2', 'arcade2', 'arcade2_body'); gumball(); two_top(); chair(); high_chair(); ceiling_fan()
    oven(); peel(); prep_table(); mixer(); flour_sacks(); tomato_case(); can_rack(); sink_dress()
    plate_steps(12, 16, 32, 150)
    hydrant(); trash_basket(); newsbox(); street_lamp(); wet_sign(); flags()
    frame_gold(300, 380, 'frame_a'); arch(); awning_valance(); door_leaf(); tv_bracket(); mop_bucket(); bus_bin()
