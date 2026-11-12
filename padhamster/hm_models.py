"""PadHamster (wop_padhamster) - textures (woplib.texlib registry) and custom MD3/IQM models. All art is original and
procedural. Every model is built in model space with z = 0 on the surface it stands on; COLL[name] holds the weapclip
collision (boxes / cylinders in model space) that build_padhamster.py places with it.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_axis
import hm_layout as L

TX = None
M_ = {}
COLL = {}


def coll(name, boxes=(), cyls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls))


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n, never mirrored: u runs to the viewer's right, v down the image"""
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    P = [c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh]
    M.poly(P, n, [(0, 0), (1, 0), (1, 1), (0, 1)])


# ================================================================================================= textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('floor', TL.checker((238, 234, 222), (186, 214, 228), 4, grout=(200, 200, 196)), scale=2.0)
    a('wall', TL.stripes((198, 232, 214), (184, 222, 204), 16), scale=2.0)
    a('wall_low', TL.tiles((250, 214, 120), (230, 230, 226), cols=4, rows=4, offset=0, grout_w=0.03), scale=1.5)
    a('ceiling', TL.tiles((244, 244, 240), (206, 206, 200), cols=2, rows=2, offset=0, grout_w=0.02), scale=4.0)
    a('frame', TL.solid((246, 246, 244), 2, 18, 64))
    a('slide', TL.stripes((80, 170, 240), (110, 200, 255), 4, soft=0.6), 'slick', steps=None)
    a('tubelight', TL.solid((255, 255, 248), 1, 19, 64), 'neon', rgb=(1.0, 1.0, 0.95), light=500)
    a('hay', TL.stripes((222, 196, 120), (200, 170, 96), 24, vertical=False, soft=0.4) + TL.N3(256, 0.6, 5, 10), scale=1.0)
    a('burrow', TL.stone((150, 112, 74), cells=30, edge=(110, 80, 52)), scale=1.5)
    a('shopsign', shop_sign(), 'sign', check_tile=False)
    a('poster_food', poster('FRESH SEEDS', 'for happy hamsters', (250, 200, 60), (120, 60, 20)), 'sign', check_tile=False)
    a('poster_sale', poster('SALE', 'all chew toys -30%', (230, 60, 80), (255, 255, 255)), 'sign', check_tile=False)
    a('poster_adopt', poster('ADOPT ME', 'ask at the counter', (90, 180, 230), (255, 255, 255)), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 170, 60), rubber=(70, 60, 60))
    materials()
    return TX


def shop_sign(w=1024, h=256):
    return ML.text_img('PADMAN PETS', w, h, (40, 120, 90), (255, 236, 140), serif=False, border=(255, 255, 255))


def poster(title, sub, bg, fg, w=512, h=768):
    im = Image.new('RGB', (w, h), tuple(bg))
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.2, h * 0.12, w * 0.8, h * 0.56), fill=(240, 190, 120), outline=(255, 255, 255), width=8)   # hamster face
    for ex in (0.38, 0.62):
        d.ellipse((w * (ex - 0.04), h * 0.27, w * (ex + 0.04), h * 0.33), fill=(20, 20, 20))
    d.ellipse((w * 0.47, h * 0.36, w * 0.53, h * 0.40), fill=(230, 110, 130))
    for ex in (0.22, 0.78):
        d.ellipse((w * (ex - 0.08), h * 0.10, w * (ex + 0.08), h * 0.22), fill=(240, 190, 120), outline=(255, 255, 255), width=6)
    f = ML.font(int(w / max(5, len(title)) * 1.5), serif=False)
    tw = d.textlength(title, font=f)
    d.text(((w - tw) / 2, h * 0.62), title, font=f, fill=tuple(fg), stroke_width=4, stroke_fill=(0, 0, 0))
    f2 = ML.font(32, serif=False); tw = d.textlength(sub, font=f2)
    d.text(((w - tw) / 2, h * 0.85), sub, font=f2, fill=tuple(fg))
    d.rectangle((6, 6, w - 7, h - 7), outline=(250, 250, 250), width=6)
    return np.asarray(im, np.float32)


def wire_tex(n=64):
    x, y = TL.xy(n)
    bar = ((x * 1.0) % 1 < 0.07) | ((y * 1.0) % 1 < 0.05)
    c = np.zeros((n, n, 3), np.float32) + ML.C((215, 220, 228)) + (np.sin(x * 40) * 12)[..., None]
    return c, np.where(bar, 255, 0).astype(np.float32)


def grille_tex(n=64):
    x, y = TL.xy(n)
    bar = ((x * 2) % 1 < 0.14) | ((y * 1) % 1 < 0.08)
    return np.zeros((n, n, 3), np.float32) + ML.C((180, 186, 196)), np.where(bar, 255, 0).astype(np.float32)


def shavings(n=256, base=(236, 214, 160)):
    rng = np.random.default_rng(4)
    im = Image.fromarray(np.uint8(np.clip(TL.fill(n, base, 6, 77), 0, 255)))
    d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = rng.random(2) * n; a = rng.random() * math.pi; ln = 6 + rng.random() * 14
        c = tuple(int(v) for v in np.array(base) * (0.75 + rng.random() * 0.35))
        d.line((x, y, x + math.cos(a) * ln, y + math.sin(a) * ln), fill=c, width=3)
    return np.asarray(im, np.float32)


def burlap_label(w=512, h=256):
    c = TL.fabric((196, 160, 110), weave=96, n=512)[:h, :w]
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255)))
    d = ImageDraw.Draw(im)
    d.rectangle((40, 40, w - 40, h - 40), outline=(120, 40, 30), width=6)
    f = ML.font(80, serif=True)
    tw = d.textlength('SEEDS', font=f)
    d.text(((w - tw) / 2, 60), 'SEEDS', font=f, fill=(120, 40, 30))
    f2 = ML.font(30, serif=False); tw = d.textlength('PADMAN PREMIUM MIX', font=f2)
    d.text(((w - tw) / 2, 160), 'PADMAN PREMIUM MIX', font=f2, fill=(60, 80, 30))
    return np.asarray(im, np.float32)


def kibble(n=128, cols=((150, 90, 40), (190, 120, 50), (110, 70, 30), (220, 170, 80))):
    rng = np.random.default_rng(9)
    im = Image.fromarray(np.uint8(np.clip(TL.fill(n, (90, 60, 30), 4, 78), 0, 255)))
    d = ImageDraw.Draw(im)
    for _ in range(160):
        x, y = rng.random(2) * n; r = 4 + rng.random() * 5
        d.ellipse((x - r, y - r, x + r, y + r), fill=cols[rng.integers(len(cols))])
    return np.asarray(im, np.float32)


def till_keys(w=256, h=256):
    im = Image.new('RGB', (w, h), (70, 74, 82))
    d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            x0, y0 = 20 + i * 58, 20 + j * 58
            d.rounded_rectangle((x0, y0, x0 + 46, y0 + 46), 6, fill=(230, 230, 220) if (i + j) % 3 else (230, 120, 90))
            d.text((x0 + 15, y0 + 10), '0123456789+-=C.%'[i * 4 + j], font=ML.font(24, serif=False), fill=(30, 30, 30))
    return np.asarray(im, np.float32)


def jar_label(w=512, h=256):
    return TL.label('YUMMY TREATS', w, h, (250, 240, 220), (200, 60, 60), border=(200, 60, 60))


def box_art(word, col, w=256, h=256):
    im = Image.fromarray(np.uint8(np.clip(TL.fill(w, col, 4, 79), 0, 255)))
    d = ImageDraw.Draw(im)
    d.ellipse((w * 0.25, h * 0.08, w * 0.75, h * 0.5), fill=(250, 220, 170), outline=(255, 255, 255), width=5)
    d.ellipse((w * 0.38, h * 0.22, w * 0.44, h * 0.28), fill=(0, 0, 0)); d.ellipse((w * 0.56, h * 0.22, w * 0.62, h * 0.28), fill=(0, 0, 0))
    f = ML.font(int(w / max(4, len(word)) * 1.4), serif=False)
    tw = d.textlength(word, font=f)
    d.text(((w - tw) / 2, h * 0.62), word, font=f, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    return np.asarray(im, np.float32)


def can_label(w=256, h=256):
    return TL.label('PAD\nCHOW', w, h, (230, 70, 60), (255, 255, 255), band=(0.2, 0.8), band_bg=(230, 70, 60))


def price_card(text, w=256, h=128):
    return ML.text_img(text, w, h, (255, 250, 230), (200, 40, 40), serif=False, border=(200, 40, 40))


def materials():
    m('pine', TL.planks((214, 176, 120), n_planks=4, grain=8), shade=20)
    m('pinev', TL.planks((214, 176, 120), n_planks=4, grain=8, vertical=True), shade=20, tag='v')
    m('white', TL.solid((240, 240, 238), 2, 33), shade=30)
    m('tray_blue', TL.solid((90, 160, 230), 3, 34), shade=40)
    m('tray_pink', TL.solid((240, 140, 180), 3, 35), shade=40)
    m('tray_mint', TL.solid((120, 210, 170), 3, 36), shade=40)
    m('tray_purple', TL.solid((170, 130, 220), 3, 37), shade=40)
    c, a = wire_tex(); M_['wire'] = TX.material('wire', c, 'alpha', alpha=a)
    c, a = grille_tex(); M_['grille'] = TX.material('grille', c, 'alpha', alpha=a)
    m('shavings', shavings(), shade=60)
    m('hay', shavings(base=(222, 196, 110)), shade=80, tag='h')
    m('glass', TL.solid((200, 220, 230), 2, 38, 64), 'glass')
    m('water', TL.solid((120, 180, 240), 2, 39, 64), 'glass', c='0.08 0.16 0.30')
    m('chrome', TL.metal((200, 204, 210)), 'lms', v=0.3, shade=50)
    m('steel', TL.metal((160, 164, 172)), 'lms', v=0.2, shade=50, tag='s')
    m('carpet', TL.fabric((206, 188, 160), weave=80), shade=30)
    m('carpet2', TL.fabric((150, 160, 176), weave=80, seed=82), shade=30)
    m('sisal', TL.stripes((200, 170, 110), (170, 140, 86), 24, vertical=False, soft=0.5), shade=80)
    m('carrier', TL.solid((236, 226, 204), 3, 40), shade=30)
    m('carrier_top', TL.solid((80, 140, 210), 3, 41), shade=30)
    m('vent', TL.solid((40, 60, 90), 2, 48, 64), shade=30, tag='v')
    m('latch', TL.solid((250, 250, 250), 2, 49, 64), shade=40, tag='l')
    m('burlap', TL.fabric((196, 160, 110), weave=96), shade=60)
    m('burlap_label', burlap_label(), shade=60)
    m('cardboard', TL.fabric((190, 150, 100), weave=12) + TL.N3(256, 0.6, 3, 4), shade=60)
    m('hammock', TL.stripes((240, 110, 120), (250, 230, 160), 8), shade=60, two=True)
    m('plush', TL.fabric((140, 110, 170), weave=40), shade=80)
    m('cushion', TL.fabric((240, 220, 200), weave=48, seed=84), shade=80)
    m('till', TL.solid((200, 200, 206), 3, 42), shade=30)
    m('till_keys', till_keys(), shade=20)
    m('screen', ML.text_img('12.95', 256, 128, (20, 60, 30), (120, 255, 140), serif=False), 'glow')
    m('coins', TL.dots((190, 160, 70), (240, 210, 90), 8, 0.3), 'lms', v=0.25, shade=60)
    m('jar_label', jar_label(), shade=60)
    m('treats', kibble(cols=((240, 90, 90), (250, 200, 60), (120, 200, 90), (250, 150, 200))), shade=80, tag='t')
    m('kibble', kibble(), shade=80)
    m('seeds', kibble(cols=((60, 50, 40), (230, 220, 200), (200, 170, 90), (90, 80, 60))), shade=80, tag='s')
    m('bin', TL.solid((110, 190, 110), 3, 43), shade=30)
    m('box_a', box_art('KIBBLE', (220, 120, 60)), shade=20)
    m('box_b', box_art('CRUNCH', (90, 150, 220)), shade=20)
    m('can', can_label(), 'lms', v=0.15, shade=60, lathe=True)
    m('wicker', TL.planks((190, 150, 90), n_planks=16, grain=4, stagger=False), shade=60, tag='w')
    m('price', price_card('ONLY 4.99'), shade=20)
    m('sign_sale', price_card('HAMSTER SALE'), shade=20, tag='s')
    m('bowl', TL.solid((240, 120, 80), 3, 44), shade=60)
    m('chew', TL.planks((200, 150, 90), n_planks=3, grain=12), shade=20, tag='c')
    m('wheel_dyn', TL.solid((120, 200, 240), 3, 45), 'dyn')
    m('metal_dyn', TL.metal((200, 204, 210)), 'dyn', tag='d')
    m('bird_dyn', TL.solid((255, 210, 60), 3, 46), 'dyn', tag='b')
    m('wood_dyn', TL.planks((200, 150, 90), n_planks=3), 'dyn', tag='w')
    m('mobile_dyn', TL.stripes((250, 120, 160), (120, 200, 250), 6), 'dyn', tag='m')
    m('ball_glass', TL.solid((255, 180, 210), 2, 47, 64), 'glass', c='0.22 0.10 0.16', tag='b')
    m('fur', TL.fabric((230, 170, 100), weave=120, seed=85), shade=80)


# ================================================================================================= models
def all_models():
    hamster_wheel(); wheel_stand(); tunnel(); nest(); hopper(); bowl(); bottle(); hammock(); chew_blocks()
    cat_posts(); perch_bird(); grille_door(); pet_bed(); till(); treat_jar(); sacks_deco(); ball_iqm(); mobile_iqm()
    sign_board(); food_boxes(); can_pyramid(); basket(); hamster_plush(); shavings_humps(); carrier_trim(); gondola(); drum(); gondola()


def hamster_wheel():
    """the spinning wheel (model2 of a func_rotating, axis y): two rims, 40 rungs, back spokes and hub; origin = hub"""
    X = ML.Model()
    R = L.WHEEL_R; w = 60
    pl, mt = M_['wheel_dyn'], M_['metal_dyn']
    for y in (-w, w):
        ring = [(R * math.cos(a), y, R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)]
        tube(X.mesh(pl), ring, 7, nseg=8, caps=(False, False))
    for k in range(40):
        a = 2 * math.pi * k / 40
        tube(X.mesh(mt), [(R * math.cos(a), -w, R * math.sin(a)), (R * math.cos(a), w, R * math.sin(a))], 3, nseg=6, caps=(False, False))
    for k in range(8):
        a = 2 * math.pi * k / 8
        tube(X.mesh(pl), [(0, w, 0), (R * math.cos(a), w, R * math.sin(a))], 6, nseg=8, caps=(False, False))
    tube(X.mesh(pl), [(0, w - 12, 0), (0, w + 12, 0)], 26, nseg=16)
    ML.save('wheel', X)


def wheel_stand():
    """A-frame behind the wheel (+y side) up to the axle; the clip round the wheel is added by the generator"""
    X = ML.Model(); st = M_['steel']
    zc = L.WHEEL_R + 24
    for sx in (-1, 1):
        tube(X.mesh(st), [(sx * 170, 84, 0), (0, 84, zc)], 8, nseg=10)
    tube(X.mesh(st), [(-190, 84, 4), (190, 84, 4)], 6, nseg=8)
    tube(X.mesh(st), [(0, 84, zc), (0, 60, zc)], 6, nseg=8)
    ML.save('wheel_stand', X)
    coll('wheel_stand', boxes=[((-180, 76, 0), (180, 92, 40))])


def tunnel():
    """half-buried cardboard tube along x (length from layout), flat on the floor, 64u clear inside"""
    x0, x1, _ = L.TUNNEL
    Ln = x1 - x0
    X = ML.Model(); cb = M_['cardboard']
    ro, ri, zc = 76.0, 66.0, 8.0

    def arc(r):
        a0 = -math.asin(zc / r); pts = []
        for a in np.linspace(a0, math.pi - a0, 24):
            pts.append((r * math.cos(a), zc + r * math.sin(a)))
        return pts                          # (y, z) from +y floor round the top to -y floor
    for r, sgn in ((ro, 1), (ri, -1)):
        A = arc(r)
        P = np.zeros((len(A), 2, 3)); N = np.zeros_like(P); UV = np.zeros((len(A), 2, 2))
        for i, (yy, zz) in enumerate(A):
            for j, xx in enumerate((-Ln / 2, Ln / 2)):
                P[i, j] = (xx, yy, zz); N[i, j] = (0, sgn * yy / r, sgn * (zz - zc) / r)
                UV[i, j] = (xx / 128, i / 6)
        X.mesh(cb).grid(P, N, UV)
    Ao, Ai = arc(ro), arc(ri)
    for xx, nx in ((-Ln / 2, -1), (Ln / 2, 1)):
        for i in range(len(Ao) - 1):
            q = [(xx, Ao[i][0], Ao[i][1]), (xx, Ao[i + 1][0], Ao[i + 1][1]), (xx, Ai[i + 1][0], Ai[i + 1][1]), (xx, Ai[i][0], Ai[i][1])]
            X.mesh(cb).poly(q, (nx, 0, 0), [(q_[1] / 64, -q_[2] / 64) for q_ in q])
    ML.save('tunnel', X)
    coll('tunnel', boxes=[((-Ln / 2, 44, 0), (Ln / 2, 72, 80)), ((-Ln / 2, -72, 0), (Ln / 2, -44, 80)),
                          ((-Ln / 2, -44, 64), (Ln / 2, 44, 80))])


def nest():
    """hay nest pile walling off the dark west-back corner of the burrow (entry gap on the east side). Origin = the
    corner centre, 56u from the west panel and 52u from the back wall."""
    X = ML.Model(); hy = M_['hay']
    for (cx, cy, a, b, h) in ((40, -100, 95, 42, 110), (150, -95, 50, 42, 90), (126, 38, 26, 12, 60)):
        ellipsoid(X.mesh(hy), (cx, cy, 0), a, b, h, nu=18, nv=8, flat_bottom=0.0,
                  bump=lambda p, t: 1 + 0.06 * math.sin(5 * t + p * 3), u1=3, v1=2)
    ML.save('nest', X)
    coll('nest', boxes=[((-50, -132, 0), (190, -66, 90)), ((104, 30, 0), (148, 46, 50))])


def hopper():
    """free-standing food hopper: a clear column of pellets over a bowl"""
    X = ML.Model()
    revolve(X.mesh(M_['bowl']), [(70, 0), (72, 6), (78, 30), (70, 34), (62, 12), (0, 12)], n=32)
    revolve(X.mesh(M_['glass']), [(36, 34), (36, 200)], n=24)
    revolve(X.mesh(M_['kibble']), [(32, 12), (32, 160), (0, 160)], n=24, u_tiles=3)
    revolve(X.mesh(M_['tray_mint']), [(40, 200), (42, 212), (0, 214)], n=24)
    ML.save('hopper', X)
    coll('hopper', cyls=[(0, 0, 66, 0, 34), (0, 0, 34, 34, 210)])


def bowl():
    X = ML.Model()
    revolve(X.mesh(M_['bowl']), [(64, 0), (68, 4), (76, 30), (68, 34), (58, 10), (0, 10)], n=32)
    revolve(X.mesh(M_['seeds']), [(60, 18), (30, 24), (0, 26)], n=24, inward=False)
    ML.save('bowl', X)


def bottle():
    """giant drinking bottle standing on the bottle shelf (glass, water, red cap, steel spout)"""
    X = ML.Model()
    prof = [(80, 0), (92, 10), (96, 40), (96, 180), (80, 200), (40, 214), (36, 224)]
    revolve(X.mesh(M_['glass']), prof, n=32)
    revolve(X.mesh(M_['water']), [(88, 6), (90, 40), (90, 150), (0, 150)], n=32)
    revolve(X.mesh(M_['tray_pink']), [(40, 210), (44, 216), (44, 232), (0, 234)], n=24)
    tube(X.mesh(M_['chrome']), [(0, 0, 224), (0, 0, 234)], 10, nseg=10)
    revolve(X.mesh(M_['tray_pink']), [(98, 0), (100, 6), (100, 18), (0, 18)], n=32)
    ML.save('bottle', X)
    coll('bottle', cyls=[(0, 0, 92, 0, 200)])


def hammock():
    """striped hammock on its own little stand (so it rests on the cage floor)"""
    X = ML.Model(); st = M_['steel']
    Lh, W = 300, 120
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(X.mesh(st), [(sx * Lh / 2, sy * W / 2, 0), (sx * Lh / 2, 0, 200)], 4, nseg=8)
    tube(X.mesh(st), [(-Lh / 2, 0, 200), (Lh / 2, 0, 200)], 4, nseg=8)
    nx, ny = 12, 5
    P = np.zeros((ny + 1, nx + 1, 3)); UV = np.zeros((ny + 1, nx + 1, 2))
    for i in range(ny + 1):
        for j in range(nx + 1):
            u, v = j / nx - 0.5, i / ny - 0.5
            P[i, j] = (u * (Lh - 40), v * W * 0.9, 190 - 60 * math.cos(u * math.pi) - 20 * (1 - (2 * v) ** 2))
            UV[i, j] = (j / nx * 2, i / ny)
    from meshlib import grid_normals
    N = grid_normals(P)
    if N[..., 2].mean() < 0: N = -N
    X.mesh(M_['hammock']).grid(P, N, UV)
    ML.save('hammock', X)
    coll('hammock', boxes=[((-Lh / 2 - 6, -W / 2 - 6, 0), (-Lh / 2 + 6, W / 2 + 6, 40)), ((Lh / 2 - 6, -W / 2 - 6, 0), (Lh / 2 + 6, W / 2 + 6, 40))])


def chew_blocks():
    X = ML.Model()
    rbox(X.mesh(M_['chew']), (-40, -40, 0), (40, 40, 60), r=6, tile=64)
    rbox(X.mesh(M_['chew']), (50, -30, 0), (110, 30, 40), r=6, tile=64)
    rbox(X.mesh(M_['chew']), (-30, -30, 60), (30, 30, 100), r=6, tile=64)
    ML.save('chew_blocks', X)
    coll('chew_blocks', boxes=[((-36, -36, 0), (36, 36, 58)), ((54, -26, 0), (106, 26, 38))])


def cat_posts():
    """sisal-wrapped posts of the cat tree (the slabs and cubby are solid_piece brushes in the generator)"""
    for name, (r, h) in (('post_a2', (L.POST_A[2], L.P2_Z - 32 - 336)), ('post_b', (L.POST_B[2], L.P3_Z - 32 - L.P1_Z))):
        X = ML.Model()
        revolve(X.mesh(M_['sisal']), [(r, 0), (r, h)], n=20, u_tiles=2, vlen=64)
        revolve(X.mesh(M_['carpet']), [(r + 14, 0), (r + 14, 8), (r, 12)], n=20)
        ML.save(name, X)


def perch_bird():
    """swinging perch with a yellow bird; model2 of a func_pendulum, origin = the pivot at the top"""
    X = ML.Model()
    for sx in (-60, 60):
        tube(X.mesh(M_['metal_dyn']), [(sx, 0, 0), (sx, 0, -360)], 2, nseg=6, caps=(False, False))
    tube(X.mesh(M_['wood_dyn']), [(-70, 0, -360), (70, 0, -360)], 7, nseg=10)
    ellipsoid(X.mesh(M_['bird_dyn']), (0, 0, -330), 30, 18, 22, nu=14, nv=8)
    sphere(X.mesh(M_['bird_dyn']), (24, 0, -306), 14, nu=12, nv=8)
    tube(X.mesh(M_['bowl']), [(36, 0, -306), (50, 0, -308)], 4, nseg=6)
    ML.save('perch_bird', X)


def grille_door():
    """the carrier's wire grille door standing open; origin at the hinge foot"""
    X = ML.Model()
    w, h = 200, 260
    X.mesh(M_['grille']).poly([(0, 0, 1), (0, w, 1), (0, w, h), (0, 0, h)], (1, 0, 0), [(0, 0), (w / 32, 0), (w / 32, -h / 32), (0, -h / 32)])
    for (a, b) in (((0, 0, 0), (0, w, 0)), ((0, w, 0), (0, w, h)), ((0, w, h), (0, 0, h)), ((0, 0, h), (0, 0, 0))):
        tube(X.mesh(M_['steel']), [a, b], 3, nseg=6)
    ML.save('grille_door', X)


def pet_bed():
    """round plush pet bed: a soft rim round a cushion, the rim dips at the front (+x) so you walk in"""
    X = ML.Model()
    R = L.BED_R

    def rfun(a, r, z): return r
    prof = [(R - 70, 16), (R - 66, 34), (R - 50, 52), (R - 30, 56), (R - 8, 46), (R, 26), (R, 0)]
    def dip(a):
        return 1 - 0.65 * max(0.0, math.cos(a)) ** 6
    P = np.zeros((len(prof), 49, 3)); UV = np.zeros((len(prof), 49, 2))
    for j, a in enumerate(np.linspace(0, 2 * math.pi, 49)):
        f = dip(a)
        for i, (r, z) in enumerate(prof):
            zz = z if z <= 16 else 16 + (z - 16) * f
            P[i, j] = (r * math.cos(a), r * math.sin(a), zz); UV[i, j] = (j / 48 * 6, i / 4)
    from meshlib import grid_normals
    N = grid_normals(P)
    ref = P.copy(); ref[..., 2] = 0
    if (N * ref).sum() < 0: N = -N
    X.mesh(M_['plush']).grid(P, N, UV)
    revolve(X.mesh(M_['cushion']), [(R - 70, 16), (R - 120, 18), (0, 20)], n=48, u_tiles=4)
    ML.save('pet_bed', X)


def till():
    """cash register; origin at the front-centre of its base, front facing -y; the open drawer is brushes"""
    X = ML.Model()
    rbox(X.mesh(M_['till']), (-140, 0, 0), (140, 230, 120), r=10, tile=128)
    P = [(-130, 30, 120), (130, 30, 120), (130, 200, 200), (-130, 200, 200)]
    X.mesh(M_['till_keys']).poly(P, (0, -0.43, 0.9), [(0, 1), (1, 1), (1, 0), (0, 0)])
    mprism(X.mesh(M_['till']), [(-140, 200), (140, 200), (140, 230), (-140, 230)], 120, 200, tile=128)
    X.mesh(M_['till']).poly([(-130, 30, 120), (-130, 200, 200), (-130, 200, 120)], (-1, 0, 0), [(0, 0), (1, 0), (1, 1)])
    X.mesh(M_['till']).poly([(130, 30, 120), (130, 200, 120), (130, 200, 200)], (1, 0, 0), [(0, 0), (1, 0), (1, 1)])
    rbox(X.mesh(M_['till']), (-60, 190, 200), (60, 220, 280), r=6, tile=128)
    pic(X.mesh(M_['screen']), (0, 189, 245), (0, -1, 0), 100, 60)
    ML.save('till', X)
    coll('till', boxes=[((-136, 4, 0), (136, 226, 196))])


def treat_jar():
    X = ML.Model()
    revolve(X.mesh(M_['glass']), [(90, 0), (96, 12), (96, 230), (70, 250), (64, 262)], n=32)
    revolve(X.mesh(M_['treats']), [(90, 4), (90, 150), (60, 160), (0, 164)], n=32, u_tiles=3)
    revolve(X.mesh(M_['tray_blue']), [(70, 262), (74, 266), (74, 286), (0, 290)], n=32)
    for a in (0, math.pi):
        pic(X.mesh(M_['jar_label']), (97 * math.cos(a), 97 * math.sin(a), 150), (math.cos(a), math.sin(a), 0), 64, 32)
    ML.save('treat_jar', X)
    coll('treat_jar', cyls=[(0, 0, 90, 0, 280)])


def sacks_deco():
    """a few loose seed sacks slumped against the sack stairs"""
    X = ML.Model()
    def inflate(x, y, z, n): return 6 * max(0.0, n[2]) + 3
    rbox(X.mesh(M_['burlap']), (-60, -90, 0), (60, 90, 90), r=28, k=4, tile=128, inflate=inflate)
    rbox(X.mesh(M_['burlap']), (-50, -70, 90), (50, 70, 150), r=24, k=4, tile=128, inflate=inflate)
    pic(X.mesh(M_['burlap_label']), (63.5, 0, 50), (1, 0, 0), 140, 70)
    ML.save('sack_pile', X)
    coll('sack_pile', boxes=[((-52, -80, 0), (52, 80, 140))])


def ball_iqm():
    """translucent exercise ball (with a hamster inside) on its loop: IQM model2 of a func_rotating at the loop centre"""
    X = ML.Model()
    sphere(X.mesh(M_['ball_glass']), (L.BALL_R, 0, 72), 72, nu=24, nv=14)
    ellipsoid(X.mesh(M_['wood_dyn']), (L.BALL_R, 0, 30), 30, 20, 22, nu=12, nv=8)
    ML.save_iqm('ball', X)


def mobile_iqm():
    """slowly turning mobile over the pet bed: string to the ceiling, two arms, fish and stars"""
    X = ML.Model(); md, mt = M_['mobile_dyn'], M_['metal_dyn']
    tube(X.mesh(mt), [(0, 0, 0), (0, 0, L.ZC - 1400)], 2, nseg=6, caps=(False, False))
    for a in (0, math.pi / 2):
        tube(X.mesh(mt), [(-160 * math.cos(a), -160 * math.sin(a), 0), (160 * math.cos(a), 160 * math.sin(a), 0)], 3, nseg=6)
    for k in range(4):
        a = k * math.pi / 2
        x, y = 160 * math.cos(a), 160 * math.sin(a)
        tube(X.mesh(mt), [(x, y, 0), (x, y, -90)], 1.5, nseg=5, caps=(False, False))
        ellipsoid(X.mesh(md), (x, y, -120), 40, 12, 26, nu=12, nv=8)
    ML.save_iqm('mobile', X)


def sign_board():
    """A-board 'HAMSTER SALE' sign standing on the floor; faces -y (the other side too)"""
    X = ML.Model(); w = M_['white']
    for sgn in (-1, 1):
        P = [(-80, sgn * 40, 0), (80, sgn * 40, 0), (80, sgn * 4, 200), (-80, sgn * 4, 200)]
        n = np.array([0.0, sgn * 0.984, 0.177])
        X.mesh(w).poly(P, n, [(0, 1), (1, 1), (1, 0), (0, 0)])
        X.mesh(w).poly(P[::-1], -n, [(0, 0), (1, 0), (1, 1), (0, 1)])
        pic(X.mesh(M_['sign_sale']), (0, sgn * 21.5, 112), (0, sgn * 0.984, 0.177), 140, 70)
    ML.save('sign_board', X)
    coll('sign_board', boxes=[((-76, -36, 0), (76, 36, 180))])


def food_boxes():
    """stack of pet food boxes (floor cover)"""
    X = ML.Model()
    for (mn, mx, k) in (((-90, -60, 0), (90, 60, 220), 'box_a'), ((100, -50, 0), (230, 50, 160), 'box_b'),
                        ((-70, -50, 220), (70, 50, 330), 'box_b')):
        rbox(X.mesh(M_[k]), mn, mx, r=4, k=2, tile=max(mx[0] - mn[0], mx[2] - mn[2]))
    ML.save('food_boxes', X)
    coll('food_boxes', boxes=[((-86, -56, 0), (86, 56, 216)), ((104, -46, 0), (226, 46, 156)), ((-66, -46, 216), (66, 46, 326))])


def can_pyramid():
    X = ML.Model()
    r, h = 44, 110
    for lvl, xs in enumerate(((-100, 0, 100), (-50, 50), (0,))):
        for x in xs:
            revolve(X.mesh(M_['can']), [(r - 4, lvl * h), (r, lvl * h + 6), (r, lvl * h + h - 6), (r - 4, lvl * h + h), (0, lvl * h + h)],
                    n=20, u_tiles=2, vlen=h, cx=x)
    ML.save('can_pyramid', X)
    coll('can_pyramid', boxes=[((-144, -40, 0), (144, 40, 106)), ((-94, -40, 106), (94, 40, 216)), ((-40, -40, 216), (40, 40, 326))])


def basket():
    """wicker display basket with chew toys (window sill)"""
    X = ML.Model()
    revolve(X.mesh(M_['wicker']), [(90, 0), (110, 70), (116, 76), (104, 76), (84, 8), (0, 8)], n=28, u_tiles=4)
    for (x, y, k) in ((-30, 10, 'chew'), (30, -20, 'tray_pink'), (10, 40, 'tray_mint')):
        sphere(X.mesh(M_[k]), (x, y, 50), 30, nu=12, nv=8)
    ML.save('basket', X)
    coll('basket', cyls=[(0, 0, 100, 0, 72)])


def hamster_plush():
    """a fat toy hamster (shop display / cage ornament)"""
    X = ML.Model()
    ellipsoid(X.mesh(M_['fur']), (0, 0, 60), 90, 70, 62, nu=20, nv=12, flat_bottom=-60.0)
    sphere(X.mesh(M_['fur']), (70, 0, 110), 44, nu=16, nv=10)
    for sy in (-1, 1):
        ellipsoid(X.mesh(M_['tray_pink']), (70, sy * 34, 152), 14, 8, 16, nu=10, nv=6)
        sphere(X.mesh(M_['coins']), (108, sy * 18, 120), 6, nu=8, nv=6)
    ML.save('hamster_plush', X)
    coll('hamster_plush', boxes=[((-80, -60, 0), (100, 60, 120))])


def shavings_humps():
    """low loose-bedding humps (visual only, <= 10u: you wade through them)"""
    X = ML.Model()
    rng = np.random.default_rng(31)
    for _ in range(9):
        x, y = rng.uniform(-300, 300), rng.uniform(-120, 120)
        ellipsoid(X.mesh(M_['shavings']), (x, y, 0), rng.uniform(60, 120), rng.uniform(40, 80), 10, nu=12, nv=4, flat_bottom=0.0)
    ML.save('humps', X)


def carrier_trim():
    """the pet carrier's detail (model space: centre of the carrier footprint, floor z 0): a ribbed seam band round the
    shell, four clip latches, vent louvres on both long sides, a chrome frame round the door (+x face) and the handle
    folded flat on the roof (12u: you step over it, it never blocks a shot). Sizes match hm_layout.CARRIER."""
    x0, y0, x1, y1 = L.CARRIER
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    d0, d1 = -1448 - (y0 + y1) / 2, -1256 - (y0 + y1) / 2
    X = ML.Model(); top, base, ch, vent, lat = M_['carrier_top'], M_['carrier'], M_['chrome'], M_['vent'], M_['latch']
    zs, o = 260, 6
    # seam band (two ribs) round the outside, broken at the door
    for zz, mat in ((zs - 14, base), (zs + 2, top)):
        rbox(X.mesh(mat), (-hx - o, -hy - o, zz), (hx + o, -hy, zz + 12), r=3, k=2, tile=64)
        rbox(X.mesh(mat), (-hx - o, hy, zz), (hx + o, hy + o, zz + 12), r=3, k=2, tile=64)
        rbox(X.mesh(mat), (-hx - o, -hy, zz), (-hx, hy, zz + 12), r=3, k=2, tile=64)
        rbox(X.mesh(mat), (hx, -hy, zz), (hx + o, d0, zz + 12), r=3, k=2, tile=64)
        rbox(X.mesh(mat), (hx, d1, zz), (hx + o, hy, zz + 12), r=3, k=2, tile=64)
    # latches over the seam
    for sx in (-hx * 0.55, hx * 0.55):
        for sy in (-1, 1):
            yy = sy * (hy + o)
            rbox(X.mesh(lat), (sx - 22, min(yy, yy + sy * 10), zs - 30), (sx + 22, max(yy, yy + sy * 10), zs + 30), r=4, k=2, tile=64)
    # vent louvres (upper shell, both long sides)
    for sy in (-1, 1):
        for k in range(6):
            xx = -hx * 0.7 + k * hx * 0.28
            yy = sy * hy
            rbox(X.mesh(vent), (xx - 14, min(yy, yy + sy * 4), zs + 60), (xx + 14, max(yy, yy + sy * 4), zs + 200), r=3, k=2, tile=64)
    # door frame
    fr = [(hx + 3, d0, 2), (hx + 3, d0, 258), (hx + 3, d1, 258), (hx + 3, d1, 2)]
    tube(X.mesh(ch), fr + [fr[0]], 5, nseg=8, caps=(False, False))
    # handle folded flat on the roof
    H = L.CARRIER_Z
    for sy in (-60, 60):
        rbox(X.mesh(top), (-30, sy - 14, H), (30, sy + 14, H + 10), r=3, k=2, tile=64)
    tube(X.mesh(ch), [(-120, -60, H + 6), (-120, 60, H + 6), (120, 60, H + 6), (120, -60, H + 6)], 5, nseg=8, caps=(True, True))
    ML.save('carrier_trim', X)


def gondola():
    """double-sided shop display gondola (512 long along x, 112 deep, 320 high): white frame, three shelves each side
    stocked with food boxes, cans and seed bags; doubles as cover in the open middle of the shop"""
    X = ML.Model(); w, st = M_['white'], M_['steel']
    Lx, D, H = 256, 56, 320
    rbox(X.mesh(w), (-Lx, -8, 0), (Lx, 8, H), r=3, k=2, tile=128)              # back panel
    for sx in (-Lx, Lx - 12):
        rbox(X.mesh(st), (sx, -D, 0), (sx + 12, D, H + 10), r=2, k=2, tile=64)   # uprights
    rng = np.random.default_rng(5)
    for zz in (8, 112, 216):
        for sy in (-1, 1):
            rbox(X.mesh(w), (-Lx + 12, min(0, sy * D), zz - 8), (Lx - 12, max(0, sy * D), zz), r=2, k=2, tile=128)
            x = -Lx + 24
            while x < Lx - 60:
                k = rng.integers(3); wdt = (48, 40, 44)[k]
                y0, y1 = (8, D - 6) if sy > 0 else (-D + 6, -8)
                if k == 0: rbox(X.mesh(M_['box_a' if rng.random() < 0.5 else 'box_b']), (x, y0, zz), (x + wdt, y1, zz + 84), r=2, k=2, tile=96)
                elif k == 1: revolve(X.mesh(M_['can']), [(18, zz), (20, zz + 4), (20, zz + 60), (0, zz + 62)], n=12, cx=x + 20, cy=(y0 + y1) / 2)
                else:
                    def inflate(xx, yy, z, n): return 3 * max(0.0, n[2]) + 1
                    rbox(X.mesh(M_['burlap']), (x, y0, zz), (x + wdt, y1, zz + 70), r=12, k=3, tile=96, inflate=inflate)
                x += wdt + 6
    ML.save('gondola', X)
    coll('gondola', boxes=[((-Lx, -D + 2, 0), (Lx, D - 2, H))])


def drum():
    """sisal-wrapped scratching drum (cat tree base), carpet lid with a scratched rim"""
    X = ML.Model()
    revolve(X.mesh(M_['sisal']), [(120, 0), (120, 290)], n=28, u_tiles=4, vlen=64)
    ML.lathe(X.mesh(M_['carpet']), [(126, 290), (128, 296), (120, 304), (0, 306)], 28)
    ML.lathe(X.mesh(M_['carpet']), [(128, 0), (128, 12), (120, 14)], 28)
    ML.save('drum', X)
