"""Respawn Room (wop_padden) - textures (woplib.texlib registry) and custom MD3s. All art is original and procedural.

Padman scale ~8u per cm (catalog models at 1.0). Every model is built in model space with z = 0 on the surface it
stands on and its front as described per function; COLL[name] holds the weapclip collision (boxes / cylinders in
model space) that build_padden.py places with it, so what bots path over is what players see.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_z

TX = None            # texlib.Textures (set by textures())
M_ = {}              # material key -> model shader name
COLL = {}            # model name -> dict(boxes=[(mn, mx)], cyls=[(cx, cy, r, z0, z1)])


# ================================================================================================= helpers
def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n (towards the viewer), w x h, never mirrored: u runs to the viewer's right,
    v down the image (Q3 t runs downward)"""
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


def ramp_rgb(n=256, w=None):
    """horizontal RGB rainbow (gamer lighting)"""
    x, y = TL.xy(n)
    h = x * 6.0
    r = np.clip(np.abs(h - 3) - 1, 0, 1); g = np.clip(2 - np.abs(h - 2), 0, 1); b = np.clip(2 - np.abs(h - 4), 0, 1)
    return np.stack([r, g, b], -1) * 255


# ================================================================================================= textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('carpet', TL.fabric((84, 86, 96), weave=96), steps='carpetsteps', scale=1.0)
    a('wall', TL.solid((46, 52, 74), 5, 11, 256) + TL.N3(256, 4, 12, 3), scale=1.0)
    a('wall_b', TL.solid((58, 46, 74), 5, 13, 256) + TL.N3(256, 4, 14, 3), scale=1.0)
    a('ceiling', TL.solid((150, 150, 158), 4, 15, 256), scale=1.0)
    a('skirting', TL.solid((26, 26, 32), 2, 16, 64))
    a('rug', hex_rug(), steps='carpetsteps', scale=1.0)
    a('sill', TL.solid((226, 226, 230), 3, 17, 128))
    a('frame', TL.solid((240, 240, 244), 2, 18, 64))
    a('shelf', TL.planks((40, 40, 46), n_planks=2, gap=(20, 20, 24), grain=4), steps='woodsteps')
    a('cardboard', cardboard(), scale=0.75)
    a('monbox', monitor_box_art(), 'sign', check_tile=False)
    a('pixel_brick', pixel_brick(), scale=2.0)
    a('pixel_sky', pixel_sky(), check_tile=False, scale=(1.0, 1.75))
    a('pixel_floor', pixel_floor(), scale=2.0)
    a('neon_purple', TL.solid((220, 90, 255), 2, 19, 64), 'neon', rgb=(0.8, 0.35, 1.0), light=260)
    a('neon_cyan', TL.solid((70, 230, 255), 2, 20, 64), 'neon', rgb=(0.3, 0.9, 1.0), light=260)
    a('sky', TL.solid((20, 22, 40), 2, 21, 64), 'raw', shader=sky_stanza(K.ns), check_tile=False)
    for i, (title, sub, c1, c2) in enumerate(POSTERS):
        a(f'poster{i}', poster(title, sub, c1, c2), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(80, 230, 255), rubber=(34, 34, 44))
    materials()
    return TX


POSTERS = [('PAD QUEST II', 'THE DUCK STRIKES BACK', (30, 20, 70), (255, 200, 60)),
           ('BALLOONY BLAST', 'CHAMPIONSHIP 2026', (120, 20, 60), (120, 240, 255)),
           ('RESPAWN', 'GG  NO  RE', (10, 10, 14), (90, 255, 140)),
           ('KILLER DUCKS', 'THEY WILL FIND YOU', (250, 210, 40), (40, 20, 20))]


def sky_stanza(ns):
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 0.55 0.62 1 60 100 30\n\tq3map_skylight 40 3\n\tskyparms env/pc-friday-13th-512 - -\n}}\n\n')


def hex_rug(n=256):
    """tileable hexagon rug: dark cells with a glowing purple/cyan edge"""
    x, y = TL.xy(n)
    # tileable hex-like lattice from three cosines (wave vectors on the integer grid so it wraps)
    k = 2 * math.pi * 4
    f = (np.cos(k * 2 * y) + np.cos(k * (x + y)) + np.cos(k * (x - y)))
    edge = np.clip(1 - np.abs(f + 0.6) * 2.5, 0, 1)
    base = TL.fill(n, (34, 30, 48), 6, 71)
    col = TL.lerp(ML.C((140, 70, 220)), ML.C((70, 200, 240)), y[..., None])
    return base * (1 - edge[..., None]) + col * edge[..., None]


def cardboard(n=256):
    c = TL.fill(n, (176, 136, 92), 6, 72) + TL.N3(n, 0.5, 73, 6)
    x, y = TL.xy(n)
    return c + (np.sin(x * 2 * math.pi * 24) * 3)[..., None]


def monitor_box_art(w=512, h=1024):
    """the printed side of the monitor box that serves as the ramp onto the desk"""
    a = np.array(Image.fromarray(np.uint8(np.clip(TL.fill(1024, (176, 136, 92), 6, 74), 0, 255))).resize((w, h)), np.float32)
    im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    d = ImageDraw.Draw(im)
    d.rectangle((40, 120, w - 40, h - 260), fill=(20, 20, 26), outline=(240, 240, 240), width=6)
    sc = screen_art_platformer(w - 100, h - 400)
    im.paste(Image.fromarray(np.uint8(np.clip(sc, 0, 255))), (50, 130))
    f = ML.font(64, serif=False)
    d.text((44, 24), 'PADVIEW 27"', font=f, fill=(30, 20, 20))
    d.text((44, h - 230), '240 Hz  |  1 ms', font=ML.font(48, serif=False), fill=(30, 20, 20))
    d.text((44, h - 150), 'THIS SIDE UP  ^^', font=ML.font(40, serif=False), fill=(150, 30, 30))
    return np.asarray(im, np.float32)


def poster(title, sub, bg, fg, w=512, h=768):
    im = Image.new('RGB', (w, h), tuple(bg))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(len(title))
    for _ in range(40):                                        # starburst
        a = rng.random() * 2 * math.pi
        d.line((w / 2, h * 0.45, w / 2 + math.cos(a) * w, h * 0.45 + math.sin(a) * w),
               fill=tuple(int(v * 0.6 + b * 0.4) for v, b in zip(fg, bg)), width=6)
    d.ellipse((w * 0.25, h * 0.27, w * 0.75, h * 0.62), fill=tuple(fg), outline=(255, 255, 255), width=8)
    d.ellipse((w * 0.36, h * 0.36, w * 0.46, h * 0.46), fill=(20, 20, 20))
    d.ellipse((w * 0.54, h * 0.36, w * 0.64, h * 0.46), fill=(20, 20, 20))
    d.arc((w * 0.36, h * 0.40, w * 0.64, h * 0.56), 20, 160, fill=(20, 20, 20), width=10)
    f = ML.font(int(w / max(6, len(title)) * 1.5), serif=False)
    tw = d.textlength(title, font=f)
    d.text(((w - tw) / 2, h * 0.70), title, font=f, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    f2 = ML.font(30, serif=False); tw = d.textlength(sub, font=f2)
    d.text(((w - tw) / 2, h * 0.86), sub, font=f2, fill=tuple(fg))
    d.rectangle((6, 6, w - 7, h - 7), outline=(250, 250, 250), width=6)
    return np.asarray(im, np.float32)


def pixel_brick(n=128):
    """8-bit brick (nearest-neighbour look: 16 x 16 cells blown up)"""
    c = np.zeros((16, 16, 3), np.float32) + ML.C((200, 76, 12))
    c[[0, 8], :] = (60, 20, 10); c[0:8, [0]] = (60, 20, 10); c[8:16, [8]] = (60, 20, 10)
    c[1, 1:7] = (250, 160, 110); c[9, 9:15] = (250, 160, 110)
    return np.kron(c, np.ones((n // 16, n // 16, 1)))


def pixel_floor(n=128):
    c = np.zeros((16, 16, 3), np.float32) + ML.C((60, 160, 40))
    c[:3] = (110, 220, 70); c[[0], :] = (20, 60, 10); c[:, [0]] = (40, 110, 30)
    c[6::5, 3::6] = (40, 110, 30)
    return np.kron(c, np.ones((n // 16, n // 16, 1)))


def pixel_sky(w=512, h=256):
    """8-bit landscape (hills, clouds, coin blocks) for the secret vault walls"""
    W, H = 128, 64
    c = np.zeros((H, W, 3), np.float32) + ML.C((92, 148, 252))
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, r in ((20, 22), (70, 30), (112, 18)):
        c[(xx - cx) ** 2 + (yy - H) ** 2 * 1.6 < r * r] = (40, 170, 60)
    for cx, cy in ((30, 12), (88, 8)):
        cl = ((xx - cx) ** 2 / 64 + (yy - cy) ** 2 / 9 < 1) | ((xx - cx - 6) ** 2 / 25 + (yy - cy + 2) ** 2 / 9 < 1)
        c[cl] = (252, 252, 252)
    for bx in (50, 58, 66):
        c[30:38, bx:bx + 8] = (240, 180, 40); c[30, bx:bx + 8] = (120, 60, 0); c[33:35, bx + 3:bx + 5] = (120, 60, 0)
    return np.kron(c, np.ones((h // H, w // W, 1)))


# ------------------------------------------------------------------------------------------------- screen art
def screen_art_platformer(w=512, h=288, seed=3):
    """an original side-scroller frame (sky, hills, platforms, a duck enemy, a little hero, a score bar)"""
    W, H = 128, 72
    c = np.zeros((H, W, 3), np.float32) + ML.C((60, 120, 240))
    yy, xx = np.mgrid[0:H, 0:W]
    c[yy > 56] = (120, 70, 30); c[(yy > 54) & (yy <= 56)] = (60, 200, 60)
    for cx, r in ((22, 20), (90, 26)):
        c[((xx - cx) ** 2 + (yy - 56) ** 2 * 2 < r * r) & (yy <= 54)] = (30, 150, 70)
    for (x0, y0, ln) in ((40, 38, 18), (78, 28, 14)):
        c[y0:y0 + 4, x0:x0 + ln] = (200, 90, 30); c[y0, x0:x0 + ln] = (250, 170, 110)
    c[(xx - 104) ** 2 + (yy - 50) ** 2 < 14] = (250, 220, 30); c[48:50, 107:110] = (250, 120, 0)       # duck
    c[44:54, 20:26] = (240, 200, 60); c[42:46, 21:25] = (250, 230, 180); c[43, 22] = c[43, 24] = (0, 0, 0)  # hero
    for k in range(5): c[20:23, 46 + k * 4:48 + k * 4] = (255, 220, 60)                                     # coins
    c[0:6] = (0, 0, 0)
    im = Image.fromarray(np.uint8(np.kron(c, np.ones((4, 4, 1))))).resize((w, h), Image.NEAREST)
    d = ImageDraw.Draw(im)
    d.text((8, 2), 'SCORE 013370   x3   WORLD 2-4', font=ML.font(max(10, h // 20), serif=False), fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def screen_art_race(w=512, h=288):
    im = Image.new('RGB', (w, h), (16, 10, 40))
    d = ImageDraw.Draw(im)
    for i in range(h // 2, h):                                         # synthwave sun + road
        t = (i - h / 2) / (h / 2)
        d.line((0, i, w, i), fill=(int(40 + 60 * t), int(10 + 20 * t), int(80 + 40 * t)))
    d.ellipse((w * 0.35, h * 0.12, w * 0.65, h * 0.62), fill=(255, 120, 60))
    for k in range(5): d.rectangle((w * 0.3, h * (0.3 + k * 0.06), w * 0.7, h * (0.32 + k * 0.06)), fill=(16, 10, 40))
    d.polygon([(w * 0.46, h * 0.5), (w * 0.54, h * 0.5), (w * 0.95, h), (w * 0.05, h)], fill=(30, 30, 40))
    for k in range(8):
        y = h * 0.5 + (h * 0.5) * (k / 8) ** 1.6
        d.line((w * 0.5, y, w * 0.5, y + 6 + k * 2), fill=(255, 240, 120), width=2 + k)
    for gx in range(-8, 9):
        d.line((w / 2 + gx * 8, h / 2, w / 2 + gx * 80, h), fill=(255, 60, 200), width=1)
    d.rounded_rectangle((w * 0.42, h * 0.78, w * 0.58, h * 0.92), 8, fill=(240, 40, 60), outline=(255, 255, 255), width=3)
    d.text((10, 8), 'LAP 2/3   POS 1ST', font=ML.font(h // 14, serif=False), fill=(120, 255, 255))
    d.text((w - 150, 8), '00:42.7', font=ML.font(h // 14, serif=False), fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def screen_art_stream(w=512, h=288):
    im = Image.new('RGB', (w, h), (18, 18, 24))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w * 0.68, h), fill=(30, 30, 44))
    d.rectangle((8, 8, w * 0.68 - 8, h * 0.72), fill=(40, 90, 60))
    for k in range(6):                                                # a little arena
        d.rectangle((20 + k * 50, h * 0.45 - k * 10, 60 + k * 50, h * 0.72 - 8), fill=(60 + k * 12, 70, 110))
    d.ellipse((w * 0.3, h * 0.3, w * 0.36, h * 0.4), fill=(255, 220, 60))
    d.rectangle((12, h * 0.76, 120, h * 0.84), fill=(230, 30, 50)); d.text((18, h * 0.765), 'LIVE', font=ML.font(h // 14, serif=False), fill=(255, 255, 255))
    d.text((132, h * 0.765), '1,337 watching', font=ML.font(h // 16, serif=False), fill=(200, 200, 210))
    names = ['duckfan99', 'padgirl', 'bettyFTW', 'noob_slayer', 'lilly_xo', 'gg_wp', 'bubbleG', 'spawncamp']
    msgs = ['GG!!', 'that pad jump', 'IMPERIUS!!', 'lol', 'clip it', 'respawn ->', 'pog', 'nice shot']
    for k in range(9):
        y = 10 + k * h / 9.5
        d.text((w * 0.70, y), names[k % 8] + ':', font=ML.font(h // 20, serif=False), fill=tuple(int(v) for v in ramp_rgb(16)[0, (k * 5) % 16]))
        d.text((w * 0.70, y + h / 22), msgs[(k * 3) % 8], font=ML.font(h // 20, serif=False), fill=(230, 230, 230))
    return np.asarray(im, np.float32)


def static_tex(n=128):
    rng = np.random.default_rng(81)
    v = rng.random((n, n)) * 200 + 30
    v = v * (0.75 + 0.25 * (np.arange(n) % 4 < 2))[:, None]
    return np.repeat(v[..., None], 3, 2)


# ================================================================================================= model materials
def materials():
    m('black', TL.solid((28, 28, 32), 2, 31), shade=40)
    m('blackgloss', TL.solid((22, 22, 26), 2, 32), 'lms', v=0.12, shade=40)
    m('steel', TL.metal((150, 156, 164)), 'lms', v=0.25, shade=50)
    m('frame', TL.metal((40, 42, 48)), 'lms', v=0.12, shade=30)
    m('oak', TL.planks((182, 146, 102), n_planks=4, grain=8, vertical=True), shade=20)
    m('oakh', TL.planks((182, 146, 102), n_planks=4, grain=8), shade=20, tag='h')
    m('white', TL.solid((232, 232, 236), 2, 33), shade=20)
    m('mattress', TL.fabric((220, 222, 230), weave=48), shade=60)
    m('duvet', duvet_tex(), shade=70)
    m('pillow', TL.fabric((250, 250, 252), weave=64), shade=80, tag='p')
    m('carbon', carbon_tex(), 'lms', v=0.1, shade=30)
    m('rgb', ramp_rgb(256), 'glow', wave='wave sin 0.8 0.2 0 0.3')
    m('rgbscroll', ramp_rgb(256), 'glow', tcmod='scroll 0.25 0')
    m('screen_a', screen_art_platformer(), 'glow')
    m('screen_b', screen_art_race(), 'glow')
    m('screen_c', screen_art_stream(), 'glow')
    m('static', static_tex(), 'glow', tcmod='scroll 7.3 -11.1')
    m('keys', keyboard_tex(), 'lm', shade=20, glowmap=None)
    m('keyglow', keyglow_tex(), 'glow', wave='wave sin 0.75 0.25 0 0.2')
    m('mesh', mesh_tex(), shade=30)
    m('mobo', mobo_tex(), shade=20)
    m('gpu', gpu_tex(), 'lms', v=0.1, shade=30)
    m('glass', TL.solid((170, 200, 220), 2, 34, 64), 'glass', c='0.06 0.08 0.10')
    m('fanblade', TL.solid((30, 30, 36), 2, 35, 64), 'dyn')
    m('fanring', ramp_rgb(128), 'glow', tcmod='scroll 0.5 0', tag='f')
    m('leather', TL.fabric((30, 30, 34), weave=96), shade=60)
    m('leather_red', TL.fabric((180, 30, 40), weave=96), shade=60)
    m('beanbag', TL.fabric((110, 50, 170), weave=80), shade=80)
    m('beanbag2', TL.fabric((40, 150, 160), weave=80), shade=80)
    m('beige', TL.solid((206, 196, 170), 3, 36), shade=40)
    m('grey', TL.solid((120, 122, 128), 3, 37), shade=40)
    m('console', console_tex(), shade=30)
    m('cable', TL.solid((24, 24, 28), 2, 38, 64), shade=80)
    m('pizza', pizza_box_tex(), shade=10)
    m('pizzaside', cardboard(), shade=10, tag='ps')
    m('case24', drinks_case_tex(), shade=20)
    m('can_g', can_tex((40, 200, 90), 'VOLT'), shade=60)
    m('can_p', can_tex((170, 60, 230), 'PADZ'), shade=60)
    m('laundry1', TL.fabric((70, 80, 120), weave=64), shade=80, tag='l1')
    m('laundry2', TL.fabric((150, 40, 40), weave=64), shade=80, tag='l2')
    m('laundry3', TL.fabric((200, 200, 200), weave=64), shade=80, tag='l3')
    m('backpack', TL.fabric((40, 90, 70), weave=80), shade=60)
    m('guitar', guitar_tex(), 'lms', v=0.15, shade=40)
    m('fretboard', TL.planks((60, 40, 30), n_planks=1, grain=6), shade=30)
    m('deck', skate_tex(), shade=20)
    m('wheel', TL.solid((240, 220, 60), 2, 39, 64), shade=60)
    m('paper', TL.solid((236, 236, 228), 3, 40, 64), shade=80)
    m('fridge', TL.solid((30, 30, 34), 2, 41), 'lms', v=0.1, shade=30, tag='fr')
    m('fridgeglow', TL.solid((140, 200, 255), 2, 42, 64), 'glow', tag='fg')
    m('speaker', speaker_tex(), shade=20)
    m('wood_dark', TL.planks((70, 50, 36), n_planks=3, grain=8), shade=20)
    m('curtain', curtain_tex(), shade=80, two=True)
    m('radiator', TL.solid((236, 236, 240), 2, 43), shade=40, tag='rad')
    m('fairy', TL.solid((255, 210, 140), 1, 44, 32), 'glow', wave='wave sin 0.8 0.2 0 0.4')
    m('lamp', TL.solid((250, 246, 236), 1, 45, 32), 'glow', tag='lamp')
    m('controller', TL.solid((40, 40, 46), 2, 46, 64), shade=60)
    m('btn', ramp_rgb(64), 'glow', tag='btn')
    m('cartridge', cartridge_tex(), shade=20)
    m('trophy', TL.metal((230, 180, 50), brushed=False), 'lms', v=0.45, shade=60)
    m('gamebox', game_box_tex(), shade=10)
    m('boxart', monitor_box_art(256, 512), shade=10)


def duvet_tex(n=256):
    """navy duvet with little controller icons"""
    c = TL.fill(n, (36, 44, 84), 4, 51)
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255))); d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            x, y = 32 + i * 64 + (j % 2) * 32, 32 + j * 64
            x %= n
            d.rounded_rectangle((x - 18, y - 9, x + 18, y + 9), 8, fill=(80, 96, 160))
            d.ellipse((x + 6, y - 4, x + 12, y + 2), fill=(240, 90, 120)); d.line((x - 12, y, x - 4, y), fill=(220, 220, 240), width=2)
            d.line((x - 8, y - 4, x - 8, y + 4), fill=(220, 220, 240), width=2)
    return np.asarray(im, np.float32)


def carbon_tex(n=128):
    x, y = TL.xy(n)
    w = ((np.floor(x * 16) + np.floor(y * 16)) % 2)
    s = np.sin((x + y) * 2 * math.pi * 16) * 0.5 + 0.5
    return (np.zeros((n, n, 3)) + 30 + (w * s * 22)[..., None]).astype(np.float32)


def keyboard_tex(w=512, h=160):
    im = Image.new('RGB', (w, h), (20, 20, 24)); d = ImageDraw.Draw(im)
    rows = [14, 14, 13, 12, 8]
    for r, nk in enumerate(rows):
        kw = (w - 16) / 15
        for k in range(nk):
            x0 = 8 + k * kw + (r * 6); y0 = 8 + r * 29
            ww = kw * (6.5 if (r == 4 and k == 3) else 1) - 4
            d.rounded_rectangle((x0, y0, x0 + ww, y0 + 25), 4, fill=(36, 36, 42), outline=(14, 14, 18))
    return np.asarray(im, np.float32)


def keyglow_tex(w=512, h=160):
    """RGB legends under the caps"""
    rgb = ramp_rgb(w)[0]
    im = Image.new('RGB', (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    rows = [14, 14, 13, 12, 8]
    letters = 'QWERTYUIOPASDFGHJKLZXCVBNM1234567890'
    for r, nk in enumerate(rows):
        kw = (w - 16) / 15
        for k in range(nk):
            x0 = 8 + k * kw + (r * 6); y0 = 8 + r * 29
            col = tuple(int(v) for v in rgb[int(min(w - 1, x0))])
            d.rounded_rectangle((x0 - 1, y0 - 1, x0 + kw - 3, y0 + 26), 4, outline=col, width=2)
            d.text((x0 + 6, y0 + 4), letters[(r * 7 + k) % len(letters)], font=ML.font(16, serif=False), fill=col)
    return np.asarray(im, np.float32)


def mesh_tex(n=128):
    x, y = TL.xy(n)
    holes = ((x * 16) % 1 - 0.5) ** 2 + ((y * 16 + (np.floor(x * 16) % 2) * 0.5) % 1 - 0.5) ** 2 < 0.09
    return np.where(holes[..., None], ML.C((8, 8, 10)), ML.C((36, 36, 42))) + ML.N3(n, 1, 52, 2)


def mobo_tex(n=256):
    c = TL.fill(n, (24, 30, 26), 3, 53)
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255))); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(54)
    for _ in range(60):
        x, y = rng.integers(0, n, 2); l = rng.integers(10, 60)
        if rng.random() < 0.5: d.line((x, y, x + l, y), fill=(160, 140, 60), width=1)
        else: d.line((x, y, x, y + l), fill=(160, 140, 60), width=1)
    for _ in range(14):
        x, y = rng.integers(10, n - 30, 2)
        d.rectangle((x, y, x + rng.integers(6, 24), y + rng.integers(6, 24)), fill=(50, 50, 56))
    d.rectangle((90, 80, 160, 150), fill=(150, 150, 160))
    return np.asarray(im, np.float32)


def gpu_tex(n=256):
    c = TL.fill(n, (40, 40, 46), 2, 55)
    x, y = TL.xy(n)
    c = np.where((np.abs(y - 0.5) < 0.04)[..., None], ML.C((200, 40, 60)), c)
    return c


def console_tex(n=128):
    c = TL.fill(n, (190, 190, 196), 3, 56)
    x, y = TL.xy(n)
    c = np.where(((y > 0.7) & (y < 0.75))[..., None], ML.C((120, 60, 160)), c)
    return c


def pizza_box_tex(n=256):
    im = Image.fromarray(np.uint8(np.clip(cardboard(n), 0, 255))); d = ImageDraw.Draw(im)
    d.ellipse((40, 40, 216, 216), outline=(170, 30, 30), width=8)
    d.text((70, 104), 'PADDYS', font=ML.font(30), fill=(170, 30, 30))
    d.text((84, 140), 'PIZZA', font=ML.font(26), fill=(30, 110, 40))
    return np.asarray(im, np.float32)


def drinks_case_tex(w=512, h=256):
    im = Image.new('RGB', (w, h), (30, 140, 70)); d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (w * 0.35, 0), (w * 0.2, h), (0, h)], fill=(10, 30, 16))
    d.text((w * 0.28, h * 0.25), 'VOLT', font=ML.font(110, serif=False), fill=(230, 255, 120), stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((w * 0.30, h * 0.72), '24 x 500 ml  ENERGY', font=ML.font(26, serif=False), fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def can_tex(col, word, w=256, h=256):
    im = Image.new('RGB', (w, h), (20, 20, 24)); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.15, w, h * 0.85), fill=tuple(col))
    for k in range(6): d.line((k * 48, h * 0.15, k * 48 + 30, h * 0.85), fill=(255, 255, 255), width=4)
    d.text((w * 0.12, h * 0.38), word, font=ML.font(64, serif=False), fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    return np.asarray(im, np.float32)


def guitar_tex(n=256):
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    c = TL.lerp(ML.C((250, 60, 40)), ML.C((40, 10, 10)), np.clip(r * 1.8, 0, 1)[..., None])
    return c


def skate_tex(w=512, h=128):
    im = Image.new('RGB', (w, h), (240, 200, 40)); d = ImageDraw.Draw(im)
    for k in range(10): d.polygon([(k * 60, 0), (k * 60 + 30, 0), (k * 60 + 60, h), (k * 60 + 30, h)], fill=(30, 30, 30))
    d.text((150, 34), 'DUCK DECKS', font=ML.font(48, serif=False), fill=(250, 60, 120), stroke_width=3, stroke_fill=(0, 0, 0))
    return np.asarray(im, np.float32)


def speaker_tex(n=256):
    c = TL.fill(n, (26, 26, 30), 3, 57)
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    cone = (r < 0.36)
    c = np.where(cone[..., None], ML.C((12, 12, 14)) + (np.cos(r * 60) * 6)[..., None], c)
    c = np.where((np.abs(r - 0.38) < 0.02)[..., None], ML.C((70, 70, 80)), c)
    return c


def curtain_tex(n=256):
    x, y = TL.xy(n)
    c = TL.fill(n, (38, 30, 58), 4, 58) + (np.sin(x * 2 * math.pi * 8) * 10)[..., None]
    return c


def cartridge_tex(w=256, h=256):
    im = Image.new('RGB', (w, h), (90, 90, 96)); d = ImageDraw.Draw(im)
    d.rectangle((30, 40, w - 30, h - 60), fill=(240, 60, 60))
    d.text((44, 90), 'PAD', font=ML.font(54, serif=False), fill=(255, 255, 255))
    d.text((44, 150), 'KART', font=ML.font(54, serif=False), fill=(255, 230, 60))
    return np.asarray(im, np.float32)


def game_box_tex(w=256, h=256):
    """spines of a row of game cases (one image, used along the shelf)"""
    im = Image.new('RGB', (w, h), (20, 20, 20)); d = ImageDraw.Draw(im)
    cols = [(30, 90, 200), (200, 40, 40), (40, 160, 70), (240, 200, 40), (120, 50, 180), (240, 120, 30), (30, 30, 30), (200, 200, 210)]
    for k in range(8):
        d.rectangle((k * 32, 0, k * 32 + 30, h), fill=cols[k])
        d.rectangle((k * 32 + 4, 10, k * 32 + 26, 40), fill=(250, 250, 250))
    return np.asarray(im, np.float32)


# ================================================================================================= models
# geometry shared with build_padden.py (world layout lives there; these are model-space sizes)
BED_L, BED_W = 1600, 784            # loft bed footprint (x by y)
DECK_Z0, MATT_Z = 704, 880          # slat deck bottom, walkable mattress/duvet top (a mid-sleeper, ~1.1 m)
WARD_D, WARD_W, WARD_H = 480, 992, 1760
DRESS_W, DRESS_D, DRESS_H = 512, 416, 720
DESK_D, DESK_L, DESK_Z = 640, 2000, 600
TOWER_W, TOWER_D, TOWER_H = 208, 480, 456
TV_W, TV_D, TV_H = 400, 360, 336
TV_SCREEN = (-152, 152, 32, 296)    # screen opening x0 x1 z0 z1 (model space, front at y = -TV_D/2)
FRIDGE = (384, 384, 480)


def all_models():
    loft_bed(); wardrobe(); dresser(); desk(); monitors(); keyboard(); mouse(); headset(); pc_tower(); fan()
    gaming_chair(); beanbag('beanbag', 'beanbag', 360, 420); beanbag('beanbag_den', 'beanbag2', 280, 330)
    crt_tv(); retro_console(); pizza_pile(); bed_ladder(); cardboard_box('pc_box', 380, 300, 300, open_top=True); cardboard_box('store_box', 300, 260, 260, open_top=False); laundry_basket(); drinks_cases(); laundry(); backpack(); guitar(); skateboard()
    trash_bin(); fridge(); speaker(); subwoofer(); radiator(); curtains(); shelf_brackets(); ceiling_lamp(); trophy()
    games_row(); energy_can('can_g'); energy_can('can_p'); glass_panel(); controller()


def loft_bed():
    """black steel loft bed, origin at the footprint centre; head end -x. Walkable duvet top at MATT_Z.
    Fairy lights under the deck light the den below."""
    X = ML.Model(); L, W = BED_L / 2, BED_W / 2
    fr = M_['frame']
    posts = [(-L, -W), (L - 64, -W), (-L, W - 64), (L - 64, W - 64)]
    for (x, y) in posts:
        rbox(X.mesh(fr), (x, y, 0), (x + 64, y + 64, MATT_Z), r=6, k=2, tile=128)
    for y0 in (-W, W - 48):                                               # long side beams
        rbox(X.mesh(fr), (-L + 64, y0, DECK_Z0), (L - 64, y0 + 48, DECK_Z0 + 96), r=6, k=2)
    for x0 in (-L + 64, L - 112):                                         # short end beams
        rbox(X.mesh(fr), (x0, -W + 64, DECK_Z0), (x0 + 48, W - 64, DECK_Z0 + 96), r=6, k=2)
    rbox(X.mesh(M_['oakh']), (-L + 64, -W + 48, DECK_Z0), (L - 64, W - 48, DECK_Z0 + 32), r=2, k=1, faces='tb')
    rbox(X.mesh(M_['mattress']), (-L + 16, -W + 16, DECK_Z0 + 32), (L - 16, W - 16, MATT_Z - 24), r=24, k=3)
    rbox(X.mesh(M_['duvet']), (-L + 24, -W + 8, MATT_Z - 40), (L - 8, W - 8, MATT_Z), r=16, k=3, tile=512)
    rbox(X.mesh(M_['pillow']), (-L + 40, -W + 60, MATT_Z), (-L + 290, W - 60, MATT_Z + 24),
         r=20, k=3, inflate=lambda x, y, z, n: 18 * max(0, n[2]) * (1 - min(1, abs(y) / W)))
    # headboard against the west wall (posts carry it)
    rbox(X.mesh(fr), (-L, -W + 64, MATT_Z - 40), (-L + 24, W - 64, MATT_Z + 240), r=8, k=2)
    # RGB strip along the south beam and fairy lights hanging in loops under the deck
    pic(X.mesh(M_['rgbscroll']), (0, -W - 0.5, DECK_Z0 + 48), (0, -1, 0), 2 * L - 160, 12)
    fy = M_['fairy']
    for k in range(18):
        x = -L + 120 + k * (2 * L - 240) / 17
        sphere(X.mesh(fy), (x, -W + 70, DECK_Z0 - 30 - 18 * math.sin(k * 1.3) ** 2), 9, nu=8, nv=5)
    tube(X.mesh(M_['cable']), [(-L + 100, -W + 70, DECK_Z0 - 4)] +
         [(-L + 120 + k * (2 * L - 240) / 17, -W + 70, DECK_Z0 - 22 - 18 * math.sin(k * 1.3) ** 2) for k in range(18)] +
         [(L - 100, -W + 70, DECK_Z0 - 4)], 2.5, nseg=5, caps=(False, False))
    ML.save('loft_bed', X)
    b = [((x, y, 0), (x + 64, y + 64, DECK_Z0)) for (x, y) in posts]
    b.append(((-L, -W, DECK_Z0), (L, W, MATT_Z)))
    coll('loft_bed', b)


def wardrobe():
    """oak wardrobe with white doors, origin at the footprint centre, front +x. The south door stands open (walk in:
    hoodies on the rail, shoe boxes, the Floater hides behind the closed north door). Walkable top at WARD_H."""
    X = ML.Model(); D, W, H = WARD_D / 2, WARD_W / 2, WARD_H
    oak, wh = M_['oak'], M_['white']
    parts = [((-D, -W, 0), (D, W, 16)),                 # plinth/floor
             ((-D, -W, H - 24), (D, W, H)),             # top
             ((-D, -W, 16), (-D + 24, W, H - 24)),      # back
             ((-D + 24, -W, 16), (D, -W + 24, H - 24)),      # south side
             ((-D + 24, W - 24, 16), (D, W, H - 24))]        # north side
    for a, b in parts: rbox(X.mesh(oak), a, b, r=3, k=1, tile=256)
    door_closed = ((D - 24, 0, 16), (D, W - 24, H - 24))
    door_open = ((D, -W - 24, 16), (D + 472, -W, H - 24))
    rbox(X.mesh(wh), *door_closed, r=4, k=1); rbox(X.mesh(wh), *door_open, r=4, k=1)
    st = M_['steel']
    rbox(X.mesh(st), (D, 30, 800), (D + 16, 46, 1000), r=6, k=2)                     # handles
    rbox(X.mesh(st), (D + 400, -W - 40, 800), (D + 416, -W - 24, 1000), r=6, k=2)
    tube(X.mesh(st), [(-20, -W + 24, 1560), (-20, W - 24, 1560)], 12, nseg=10)        # hanging rail
    cols = [M_['laundry1'], M_['laundry2'], M_['backpack'], M_['laundry3']]
    for k, y in enumerate((-380, -250, -120, 10)):                                     # hoodies
        ellipsoid(X.mesh(cols[k]), (-20, y, 1250), 200, 50, 260, nu=12, nv=8,
                  bump=lambda p, t: 1 + 0.08 * math.sin(3 * t) * math.cos(p))
        tube(X.mesh(st), [(-20, y, 1520), (-20, y, 1556)], 4, nseg=6)
    sb = [((-D + 24, -W + 24, 16), (-D + 184, -W + 224, 112)), ((-D + 24, -W + 24, 112), (-D + 184, -W + 224, 208))]
    for a, b in sb: rbox(X.mesh(M_['gamebox']), a, b, r=3, k=1, tile=160)
    ML.save('wardrobe', X)
    coll('wardrobe', parts + [door_closed, door_open] + sb)


def dresser():
    """chest of drawers, origin at the footprint centre, front -y (south)"""
    X = ML.Model(); W, D, H = DRESS_W / 2, DRESS_D / 2, DRESS_H
    rbox(X.mesh(M_['oak']), (-W, -D + 16, 24), (W, D, H - 24), r=4, k=1)
    rbox(X.mesh(M_['oakh']), (-W - 8, -D, H - 24), (W + 8, D, H), r=6, k=2)
    rbox(X.mesh(M_['black']), (-W + 16, -D + 32, 0), (W - 16, D - 16, 24), r=2, k=1)
    for k in range(3):
        z0 = 40 + k * 220
        rbox(X.mesh(M_['white']), (-W + 12, -D, z0), (W - 12, -D + 20, z0 + 206), r=4, k=1)
        rbox(X.mesh(M_['steel']), (-60, -D - 14, z0 + 96), (60, -D, z0 + 112), r=6, k=2)
    ML.save('dresser', X)
    coll('dresser', [((-W - 8, -D, 0), (W + 8, D, H))])


def desk():
    """gaming desk, origin at the footprint centre, front -x: carbon top, black end panels with RGB edges"""
    X = ML.Model(); D, L, Z = DESK_D / 2, DESK_L / 2, DESK_Z
    top = ((-D, -L, Z - 32), (D, L, Z))
    rbox(X.mesh(M_['carbon']), *top, r=6, k=2, tile=256)
    panels = [((-D + 40, -L, 0), (D, -L + 40, Z - 32)), ((-D + 40, L - 40, 0), (D, L, Z - 32))]
    for a, b in panels: rbox(X.mesh(M_['blackgloss']), a, b, r=4, k=1)
    bar = ((D - 64, -L + 40, 300), (D - 32, L - 40, 360))
    rbox(X.mesh(M_['frame']), *bar, r=4, k=1)
    pic(X.mesh(M_['rgbscroll']), (-D - 0.5, 0, Z - 16), (-1, 0, 0), 2 * L - 40, 10)
    for y in (-L, L):
        s = 1 if y < 0 else -1
        pic(X.mesh(M_['rgbscroll']), (-D + 40.5 - 0.5 * 0, y - s * 0.5, (Z - 32) / 2), (0, -s, 0), D * 2 - 60, 8, up=(1, 0, 0))
    ML.save('desk', X)
    coll('desk', [top] + panels + [bar])


def monitors():
    """triple monitor rig on one stand bar, origin centre of the bar on the desk, screens face -x"""
    X = ML.Model()
    rbox(X.mesh(M_['frame']), (-40, -120, 0), (60, 120, 14), r=6, k=2)
    rbox(X.mesh(M_['frame']), (10, -22, 14), (40, 22, 300), r=8, k=2)
    tube(X.mesh(M_['frame']), [(25, -520, 300), (25, 520, 300)], 14, nseg=8)
    for k, (y, ang, scr) in enumerate(((-500, -24, 'screen_a'), (0, 0, 'screen_b'), (500, 24, 'screen_c'))):
        S = ML.Model()
        rbox(S.mesh(M_['blackgloss']), (-12, -240, -140), (12, 240, 140), r=6, k=2)
        rbox(S.mesh(M_['frame']), (12, -60, -60), (28, 60, 60), r=4, k=1)
        pic(S.mesh(M_[scr]), (-12.6, 0, 6), (-1, 0, 0), 456, 252)
        a = math.radians(ang)
        cx = 25 - (0 if k == 1 else 70)
        X.add_model(S, rot_z(a), (cx - 40, y, 300))
    ML.save('monitors', X)
    coll('monitors', [((-40, -120, 0), (60, 120, 14)), ((10, -22, 14), (40, 22, 160)),
                      ((-60, -730, 160), (20, -280, 440)), ((-40, -240, 160), (12, 240, 440)), ((-60, 280, 160), (20, 730, 440))])


def keyboard():
    """RGB mechanical keyboard, origin centre, the long side along y, typing side -x"""
    X = ML.Model()
    rbox(X.mesh(M_['black']), (-56, -176, 0), (56, 176, 16), r=6, k=2)
    P = [(-50, 170, 22), (-50, -170, 22), (50, -170, 18), (50, 170, 18)]
    X.mesh(M_['keys']).poly([np.array(p, float) for p in P], (0.04, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    Q = [np.array(p, float) + (0, 0, 0.6) for p in P]
    X.mesh(M_['keyglow']).poly(Q, (0.04, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save('keyboard', X)
    coll('keyboard', [((-56, -176, 0), (56, 176, 20))])


def mouse():
    X = ML.Model()
    rbox(X.mesh(M_['black']), (-240, -200, 0), (240, 200, 3), r=1, k=1, tile=512)       # mouse pad
    ellipsoid(X.mesh(M_['blackgloss']), (0, 0, 3), 60, 36, 30, nu=14, nv=8, flat_bottom=0)
    pic(X.mesh(M_['rgb']), (0, 0, 33.6), (0, 0, 1), 20, 8, up=(1, 0, 0))
    ML.save('mouse', X)


def headset():
    """headset on its stand: disc base, post, the band over a cradle, two ear cups"""
    X = ML.Model()
    revolve(X.mesh(M_['blackgloss']), [(70, 0), (70, 10), (60, 16), (0, 16)], n=24, inward=True)
    tube(X.mesh(M_['frame']), [(0, 0, 16), (0, 0, 260)], 10, nseg=8)
    tube(X.mesh(M_['frame']), [(0, -50, 260), (0, 50, 260)], 12, nseg=8)
    pts = [(0, 90 * math.cos(a), 250 + 70 * math.sin(a)) for a in np.linspace(math.pi * 1.05, -0.05, 12)]
    tube(X.mesh(M_['leather']), [(p[0], -p[1], p[2]) for p in pts], 12, nseg=8)
    for s in (-1, 1):
        ellipsoid(X.mesh(M_['leather']), (0, s * 96, 190), 44, 26, 52, nu=12, nv=8)
        pic(X.mesh(M_['rgb']), (0, s * 122.5, 190), (0, s, 0), 40, 40)
    ML.save('headset', X)


def pc_tower():
    """walk-in PC tower (glass side panel removed), origin footprint centre, front -y, open side -x. Interior floor
    z 16, PSU shroud step at the back, motherboard on the +x wall with the GPU, cooler and glowing RAM. The front
    and top fans are separate movers (fan())."""
    X = ML.Model(); W, D, H = TOWER_W / 2, TOWER_D / 2, TOWER_H
    bk = M_['blackgloss']
    floor = ((-W, -D, 0), (W, D, 16)); top = ((-W, -D, H - 12), (W, D, H))
    side = ((W - 12, -D, 16), (W, D, H - 12)); back = ((-W, D - 12, 16), (W - 12, D, H - 12))
    front_l = ((-W, -D, 16), (W - 12, -D + 24, 52)); front_t = ((-W, -D, H - 52), (W - 12, -D + 24, H - 12))
    shroud = ((-W, D - 160, 16), (W - 12, D - 12, 32))
    for a, b in (floor, top, side, back, shroud): rbox(X.mesh(bk), a, b, r=3, k=1)
    for a, b in (front_l, front_t): rbox(X.mesh(M_['mesh']), a, b, r=3, k=1, tile=64)
    # front fan frame: mesh panel with three round holes is drawn as a ring plate per fan
    for z in (120, 240, 360):
        M = X.mesh(M_['mesh'])
        for k in range(24):
            a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
            q = [(math.cos(a0) * 58, -D + 4, z + math.sin(a0) * 58), (math.cos(a0) * 70, -D + 4, z + math.sin(a0) * 70),
                 (math.cos(a1) * 70, -D + 4, z + math.sin(a1) * 70), (math.cos(a1) * 58, -D + 4, z + math.sin(a1) * 58)]
            M.poly([np.array(p) for p in q], (0, -1, 0), [(p[0] / 64, -p[2] / 64) for p in q])
        rbox(X.mesh(M_['mesh']), (-W, -D, z - 60 if z == 120 else z - 60), (-W + 24, -D + 24, z + 60), r=2, k=1)
        rbox(X.mesh(M_['mesh']), (W - 36, -D, z - 60), (W - 12, -D + 24, z + 60), r=2, k=1)
    rbox(X.mesh(M_['mobo']), (W - 18, -D + 60, 50), (W - 12, D - 30, 430), r=1, k=1, tile=380, faces='w')
    gpu = ((-50, -D + 50, 190), (W - 18, D - 100, 238))
    rbox(X.mesh(M_['gpu']), *gpu, r=6, k=2, tile=256)
    pic(X.mesh(M_['rgbscroll']), (-50.6, 0, 214), (-1, 0, 0), D * 2 - 180, 8)
    for k in range(2):
        disc(X.mesh(M_['fanring']), 48, 189.4, up=False, n=20, cx=10, cy=-D + 120 + k * 120, r_in=42)
    cooler = ((40, -10, 300), (W - 18, 90, 370))
    rbox(X.mesh(M_['frame']), *cooler, r=8, k=2)
    disc(X.mesh(M_['fanring']), 38, 370.5, up=True, n=20, cx=66, cy=40, r_in=30)
    for k in range(4):
        rbox(X.mesh(M_['black']), (W - 40, 120 + k * 14, 300), (W - 18, 128 + k * 14, 400), r=1, k=1)
        pic(X.mesh(M_['rgb']), (W - 29, 124 + k * 14, 401), (0, 0, 1), 20, 8, up=(-1, 0, 0))
    pic(X.mesh(M_['rgbscroll']), (0, 0, H + 0.5), (0, 0, 1), 2 * W - 20, 8, up=(0, -1, 0))
    for y in (-60, 80):                                                            # top fan grilles (fans inside)
        disc(X.mesh(M_['fanring']), 60, H + 0.6, up=True, n=24, cy=y, r_in=54)
    ML.save('pc_tower', X)
    coll('pc_tower', [floor, top, side, back, shroud, front_l, front_t, gpu, cooler,
                      ((-W, -D, 52), (-W + 24, -D + 24, H - 52)), ((W - 36, -D, 52), (W - 12, -D + 24, H - 52))])


def fan():
    """120 mm fan blades + RGB ring for the tower movers (model2, so built in mover space round the origin);
    'fan_y' turns about y (front fans), 'fan_z' about z (top fans)"""
    for name, R in (('fan_y', np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]])), ('fan_z', np.eye(3))):
        X = ML.Model()
        B = ML.Model()
        for k in range(7):
            a = 2 * math.pi * k / 7
            pts = [(14 * math.cos(a), 14 * math.sin(a)), (52 * math.cos(a + 0.25), 52 * math.sin(a + 0.25)),
                   (52 * math.cos(a + 0.75), 52 * math.sin(a + 0.75)), (14 * math.cos(a + 0.5), 14 * math.sin(a + 0.5))]
            mprism(B.mesh(M_['fanblade']), pts, -2, 2, tile=64)
        revolve(B.mesh(M_['fanblade']), [(14, -6), (14, 6), (0, 6)], n=12, inward=True)
        revolve(B.mesh(M_['fanring']), [(54, -3), (54, 3)], n=24)
        X.add_model(B, R)
        ML.save_iqm(name, X)


def gaming_chair():
    """racing-style gaming chair, origin at the star base centre, seat faces +x"""
    X = ML.Model()
    for k in range(5):
        a = 2 * math.pi * k / 5
        tube(X.mesh(M_['frame']), [(0, 0, 46), (230 * math.cos(a), 230 * math.sin(a), 34)], 14, nseg=8)
        sphere(X.mesh(M_['black']), (240 * math.cos(a), 240 * math.sin(a), 18), 18, nu=10, nv=6)
    tube(X.mesh(M_['steel']), [(0, 0, 40), (0, 0, 300)], 22, nseg=12)
    seat = ((-190, -220, 300), (230, 220, 400))
    rbox(X.mesh(M_['leather']), *seat, r=30, k=3, inflate=lambda x, y, z, n: 10 * max(0, n[2]))
    for s in (-1, 1):
        rbox(X.mesh(M_['leather_red']), (-210, s * 200 - 20, 340), (230, s * 200 + 20, 430), r=18, k=3)
        tube(X.mesh(M_['frame']), [(-40, s * 250, 330), (-40, s * 250, 520)], 12, nseg=8)
        rbox(X.mesh(M_['leather']), (-120, s * 250 - 30, 520), (120, s * 250 + 30, 550), r=12, k=2)
    back = ((-280, -230, 380), (-190, 230, 1000))
    rbox(X.mesh(M_['leather']), *back, r=40, k=3)
    for s in (-1, 1):
        rbox(X.mesh(M_['leather_red']), (-270, s * 210 - 26, 420), (-180, s * 210 + 26, 960), r=24, k=3)
    rbox(X.mesh(M_['leather_red']), (-200, -100, 840), (-170, 100, 940), r=14, k=3)
    ML.save('gaming_chair', X)
    coll('gaming_chair', [seat, back], [(0, 0, 40, 0, 300)])


def beanbag(name, mat, r, h):
    """slouched bean bag with a dent where you sit"""
    X = ML.Model()
    def bump(p, t):
        dent = math.exp(-((t - 0.3) ** 2) * 3) * max(0, math.sin(p)) * 0.25
        return 1 + 0.06 * math.sin(3 * t + 1) * math.cos(p) - dent
    ellipsoid(X.mesh(M_[mat]), (0, 0, h / 2), r, r * 0.92, h / 2, nu=24, nv=12, bump=bump, flat_bottom=-h / 2)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, r * 0.75, 0, h * 0.7)])


def crt_tv():
    """old CRT telly, origin at the footprint centre, screen faces -y. The screen is a hole you can walk/jump into
    (the static is drawn on a nonsolid quad): the secret entry. Collision leaves the screen cavity open."""
    X = ML.Model(); W, D, H = TV_W / 2, TV_D / 2, TV_H
    x0, x1, z0, z1 = TV_SCREEN
    bz = M_['beige']
    fb = -D
    bez = [((-W, fb, 0), (W, fb + 40, z0)), ((-W, fb, z1), (W, fb + 40, H)),
           ((-W, fb, z0), (x0, fb + 40, z1)), ((x1, fb, z0), (W, fb + 40, z1))]
    for a, b in bez: rbox(X.mesh(bz), a, b, r=6, k=2, tile=128)
    # tapered rear (hull of the bezel back and a smaller back plate)
    M = X.mesh(M_['grey'])
    back = [(-150, D, 40), (150, D, 40), (150, D, 300), (-150, D, 300)]
    frontr = [(-W, fb + 40, 0), (W, fb + 40, 0), (W, fb + 40, H), (-W, fb + 40, H)]
    for k in range(4):
        q = [frontr[k], frontr[(k + 1) % 4], back[(k + 1) % 4], back[k]]
        P = [np.array(p, float) for p in q]
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= np.linalg.norm(n)
        if n @ (P[0] - np.array([0, 0, H / 2])) < 0: n = -n
        M.poly(P, n, [(p[0] / 128, -p[2] / 128) for p in q])
    M.poly([np.array(p, float) for p in back], (0, 1, 0), [(p[0] / 128, -p[2] / 128) for p in back])
    pic(X.mesh(M_['static']), (0, fb + 6, (z0 + z1) / 2), (0, -1, 0), x1 - x0, z1 - z0)
    rbox(X.mesh(M_['black']), (W - 70, fb - 6, 10), (W - 20, fb, 24), r=3, k=1)                        # buttons
    sphere(X.mesh(M_['btn']), (W - 40, fb - 2, 18), 6, nu=8, nv=5)
    for a in (-0.5, 0.5):                                                                                # rabbit ears
        tube(X.mesh(M_['steel']), [(0, 60, H), (math.sin(a) * 160, 60, H + 220)], 4, nseg=6)
    sphere(X.mesh(M_['grey']), (0, 60, H + 6), 30, nu=12, nv=6, flat_bottom=-6)
    ML.save('crt_tv', X)
    inner = ((-W, fb + 40, 0), (W, D, 32))
    coll('crt_tv', bez + [inner, ((-W, D - 24, 32), (W, D, H)), ((-W, fb + 40, 32), (x0, D - 24, H)),
                          ((x1, fb + 40, 32), (W, D - 24, H)), ((x0, fb + 40, z1), (x1, D - 24, H))])


def retro_console():
    X = ML.Model()
    rbox(X.mesh(M_['console']), (-120, -90, 0), (120, 90, 56), r=12, k=2, tile=240)
    rbox(X.mesh(M_['cartridge']), (-60, -10, 56), (60, 14, 150), r=4, k=1, tile=120)
    rbox(X.mesh(M_['grey']), (-70, -80, 56), (-30, -50, 64), r=3, k=1)
    sphere(X.mesh(M_['btn']), (80, -60, 58), 8, nu=8, nv=4, flat_bottom=-2)
    ML.save('retro_console', X)
    coll('retro_console', [((-120, -90, 0), (120, 90, 56))])


def controller():
    X = ML.Model()
    for s in (-1, 1):
        ellipsoid(X.mesh(M_['controller']), (0, s * 48, 14), 40, 38, 14, nu=12, nv=6, flat_bottom=-14)
    rbox(X.mesh(M_['controller']), (-30, -50, 0), (30, 50, 26), r=10, k=2)
    for k, (x, y) in enumerate(((10, 52), (-8, 60), (2, 70), (2, 44))):
        sphere(X.mesh(M_['btn']), (x, y, 28), 6, nu=8, nv=4)
    tube(X.mesh(M_['cable']), [(-30, 0, 8), (-90, 10, 3), (-200, -40, 3), (-320, 20, 3), (-420, 0, 3)], 3, nseg=5)
    ML.save('controller', X)


def pizza_pile():
    """four pizza boxes dumped in a pile (cover). Origin at the footprint centre."""
    X = ML.Model(); boxes = []
    for k, (dx, dy) in enumerate(((0, 0), (24, -18), (-30, 10), (12, 26))):
        z0 = k * 30
        b = ((dx - 140, dy - 140, z0), (dx + 140, dy + 140, z0 + 30))
        rbox(X.mesh(M_['pizzaside']), *b, r=2, k=1, faces='nsewb', tile=280)
        q = [(b[0][0], b[0][1], z0 + 30), (b[1][0], b[0][1], z0 + 30), (b[1][0], b[1][1], z0 + 30), (b[0][0], b[1][1], z0 + 30)]
        X.mesh(M_['pizza']).poly([np.array(p, float) for p in q], (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
        boxes.append(b)
    ML.save('pizza_pile', X)
    coll('pizza_pile', boxes)


def bed_ladder():
    """the bed's steel ladder, leaning from the floor (y -280) to hooks over the side beam (y 0). Origin at the
    bed edge on the floor; the rungs face south. Decoration (players and bots go up by the pads)."""
    X = ML.Model(); fr = M_['frame']
    top = MATT_Z + 90
    for x in (-80, 80):
        tube(X.mesh(fr), [(x, -280, 0), (x, -24, top), (x, 0, top + 20), (x, 24, top - 10)], 10, nseg=8)
    for k in range(1, 8):
        t = k / 8.0
        tube(X.mesh(M_['steel']), [(-80, -280 + 256 * t, top * t), (80, -280 + 256 * t, top * t)], 8, nseg=8)
    for x in (-80, 80):
        rbox(X.mesh(M_['black']), (x - 14, -294, 0), (x + 14, -266, 10), r=3, k=1)
    ML.save('bed_ladder', X)


def cardboard_box(name, L, W, H, open_top):
    """a cardboard box (the PC's shipping box with the flaps folded out, or a closed storage box). Origin footprint centre."""
    X = ML.Model(); c = M_['pizzaside']
    L2, W2 = L / 2, W / 2
    if open_top:
        walls = [((-L2, -W2, 0), (L2, -W2 + 8, H)), ((-L2, W2 - 8, 0), (L2, W2, H)),
                 ((-L2, -W2 + 8, 0), (-L2 + 8, W2 - 8, H)), ((L2 - 8, -W2 + 8, 0), (L2, W2 - 8, H)),
                 ((-L2 + 8, -W2 + 8, 0), (L2 - 8, W2 - 8, 8))]
        for a, b in walls: rbox(X.mesh(c), a, b, r=1, k=1, tile=256)
        for (q, n) in ((([-L2, -W2, H], [L2, -W2, H], [L2, -W2 - 110, H + 70], [-L2, -W2 - 110, H + 70]), (0, -0.54, 0.84)),
                       (([L2, W2, H], [-L2, W2, H], [-L2, W2 + 110, H + 70], [L2, W2 + 110, H + 70]), (0, 0.54, 0.84))):
            P = [np.array(v, float) for v in q]
            X.mesh(c).poly(P, n, [(v[0] / 256, v[1] / 256) for v in q])
            X.mesh(c).poly(P[::-1], tuple(-np.array(n)), [(v[0] / 256, v[1] / 256) for v in q[::-1]])
        pic(X.mesh(M_['boxart']), (0, -W2 - 0.6, H / 2), (0, -1, 0), H * 0.45, H * 0.9)
        coll(name, walls)
    else:
        b = ((-L2, -W2, 0), (L2, W2, H))
        rbox(X.mesh(c), *b, r=2, k=1, tile=256)
        tape = ((-L2 - 0.5, -24, H - 2), (L2 + 0.5, 24, H + 0.5))
        rbox(X.mesh(M_['paper']), *tape, r=0, k=1)
        coll(name, [b])
    ML.save(name, X)


def laundry_basket():
    """round plastic laundry basket overflowing with clothes. Origin at the base centre."""
    X = ML.Model()
    revolve(X.mesh(M_['white']), [(150, 0), (175, 330), (166, 330), (142, 12), (0, 12)], n=28, u_tiles=4)
    mats = ['laundry1', 'laundry2', 'laundry3']
    for k, (x, y, z) in enumerate(((0, 0, 330), (60, -40, 350), (-50, 50, 345), (120, 60, 300))):
        ellipsoid(X.mesh(M_[mats[k % 3]]), (x, y, z), 110 - k * 10, 90, 50, nu=12, nv=6,
                  bump=lambda p, t, s=k: 1 + 0.12 * math.sin(4 * t + s) * math.cos(2 * p))
    ML.save('laundry_basket', X)
    coll('laundry_basket', cyls=[(0, 0, 165, 0, 330)])


def drinks_cases():
    """energy drink cases stacked crosswise with loose cans on top. Origin footprint centre."""
    X = ML.Model()
    B = [((-320, -216, 0), (0, 0, 96)), ((0, -216, 0), (320, 0, 96)), ((-320, 0, 0), (0, 216, 96)),
         ((-160, -216, 96), (160, 0, 192)), ((-216, 0, 96), (0, 320, 192)), ((-120, -160, 192), (200, 56, 288))]
    for a, b in B: rbox(X.mesh(M_['case24']), a, b, r=4, k=1, tile=320)
    ML.save('drinks_cases', X)
    coll('drinks_cases', B)


def energy_can(name):
    X = ML.Model()
    revolve(X.mesh(M_[name]), [(26, 0), (30, 6), (30, 116), (25, 122), (22, 122)], n=20, u_tiles=1, vlen=122)
    disc(X.mesh(M_['steel']), 22, 122, up=True, n=20)
    ML.save(name, X)


def laundry():
    X = ML.Model(); rng = np.random.default_rng(91)
    mats = ['laundry1', 'laundry2', 'laundry3', 'backpack']
    for k in range(9):
        a = rng.random() * 2 * math.pi; d = rng.random() * 140
        c = (math.cos(a) * d, math.sin(a) * d, 30 + rng.random() * 40)
        ellipsoid(X.mesh(M_[mats[k % 4]]), c, 90 + rng.random() * 60, 70 + rng.random() * 40, 40 + rng.random() * 30,
                  nu=12, nv=6, R=rot_z(rng.random() * 3), flat_bottom=-c[2],
                  bump=lambda p, t, s=k: 1 + 0.12 * math.sin(4 * t + s) * math.cos(2 * p))
    ML.save('laundry', X)
    coll('laundry', cyls=[(0, 0, 170, 0, 120)])


def backpack():
    X = ML.Model()
    body = ((-90, -140, 0), (90, 140, 380))
    rbox(X.mesh(M_['backpack']), *body, r=50, k=3, inflate=lambda x, y, z, n: 14 * max(0, -n[0]))
    rbox(X.mesh(M_['backpack']), (-130, -100, 30), (-80, 100, 200), r=24, k=3)
    for y in (-80, 80):
        tube(X.mesh(M_['black']), [(95, y, 360), (115, y, 250), (100, y, 40)], 10, ry=4, nseg=8)
    pic(X.mesh(M_['rgb']), (-130.6, 0, 120), (-1, 0, 0), 120, 10)
    ML.save('backpack', X)
    coll('backpack', [body])


def guitar():
    """electric guitar on an A-frame stand, origin at the stand foot, body faces -y"""
    X = ML.Model()
    outline = [(160 * math.cos(a) * (1 - 0.18 * math.sin(2 * a) ** 2), 220 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    body = ML.Model()
    mprism(body.mesh(M_['guitar']), outline, -24, 24, tile=440)
    neck = ML.Model()
    rbox(neck.mesh(M_['fretboard']), (-22, -12, 200), (22, 12, 760), r=4, k=1)
    rbox(neck.mesh(M_['black']), (-34, -10, 760), (34, 10, 880), r=8, k=2)
    Rx = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]])
    tilt = math.radians(12)
    Rt = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
    X.add_model(body, Rt @ Rx, (0, 40, 230))
    X.add_model(neck, Rt, (0, 40, 0))
    for (a, b) in (((-120, -60, 0), (0, 60, 300)), ((120, -60, 0), (0, 60, 300)), ((0, 120, 0), (0, 60, 300))):
        tube(X.mesh(M_['frame']), [a, b], 8, nseg=6)
    ML.save('guitar', X)
    coll('guitar', cyls=[(0, 40, 150, 0, 460)])


def skateboard():
    X = ML.Model()
    outline = [(240 * np.sign(math.cos(a)) + 80 * math.cos(a), 80 * math.sin(a)) for a in np.linspace(0.01, 2 * math.pi + 0.01, 24, endpoint=False)]
    mprism(X.mesh(M_['deck']), outline, 44, 54, tile=640)
    for x in (-200, 200):
        rbox(X.mesh(M_['steel']), (x - 20, -60, 30), (x + 20, 60, 44), r=4, k=1)
        for y in (-62, 62):
            tube(X.mesh(M_['wheel']), [(x, y - 14, 24), (x, y + 14, 24)], 24, nseg=12)
    ML.save('skateboard', X)
    coll('skateboard', [((-330, -84, 0), (330, 84, 54))])


def trash_bin():
    X = ML.Model()
    revolve(X.mesh(M_['blackgloss']), [(100, 0), (124, 280), (116, 280), (94, 12), (0, 12)], n=24, u_tiles=2)
    rng = np.random.default_rng(92)
    for k in range(5):
        sphere(X.mesh(M_['paper']), (rng.uniform(-50, 50), rng.uniform(-50, 50), 250 + rng.uniform(0, 40)), 34, nu=10, nv=6,
               bump=lambda p, t, s=k: 1 + 0.18 * math.sin(5 * t + s) * math.sin(3 * p))
    ML.save('trash_bin', X)
    coll('trash_bin', cyls=[(0, 0, 110, 0, 280)])


def fridge():
    """mini fridge, origin footprint centre, glass door faces +x, lit shelves of cans inside"""
    X = ML.Model(); W, D, H = FRIDGE[0] / 2, FRIDGE[1] / 2, FRIDGE[2]
    rbox(X.mesh(M_['fridge']), (-W, -D, 0), (W - 20, D, H), r=12, k=2)
    rbox(X.mesh(M_['frame']), (W - 24, -D, 0), (W, D, 40), r=4, k=1)
    pic(X.mesh(M_['fridgeglow']), (W - 19.5, 0, 250), (1, 0, 0), 2 * D - 60, 360)
    for z in (90, 250):
        for k in range(5):
            y = -D + 60 + k * 64
            revolve(X.mesh(M_['can_g' if (k + z) % 3 else 'can_p']), [(24, z), (24, z + 110), (0, z + 110)], n=12, cx=W - 70, cy=y)
    rbox(X.mesh(M_['glass']), (W - 20, -D, 40), (W, D, H), r=4, k=1)
    rbox(X.mesh(M_['steel']), (W, D - 50, 200), (W + 16, D - 34, 380), r=6, k=2)
    ML.save('fridge', X)
    coll('fridge', [((-W, -D, 0), (W, D, H))])


def speaker():
    X = ML.Model()
    rbox(X.mesh(M_['wood_dark']), (-80, -100, 0), (80, 100, 440), r=8, k=2)
    pic(X.mesh(M_['speaker']), (-80.6, 0, 120), (-1, 0, 0), 150, 150)
    pic(X.mesh(M_['speaker']), (-80.6, 0, 320), (-1, 0, 0), 110, 110)
    ML.save('speaker', X)
    coll('speaker', [((-80, -100, 0), (80, 100, 440))])


def subwoofer():
    X = ML.Model()
    rbox(X.mesh(M_['wood_dark']), (-180, -180, 0), (180, 180, 360), r=10, k=2)
    pic(X.mesh(M_['speaker']), (-180.6, 0, 180), (-1, 0, 0), 300, 300)
    ML.save('subwoofer', X)
    coll('subwoofer', [((-180, -180, 0), (180, 180, 360))])


def radiator():
    """column radiator on feet, origin at the centre of its back edge (touching the wall), fins face +y"""
    X = ML.Model()
    for k in range(20):
        x = -475 + k * 50
        rbox(X.mesh(M_['radiator']), (x, 12, 140), (x + 40, 56, 600), r=10, k=2)
    tube(X.mesh(M_['radiator']), [(-480, 34, 160), (480, 34, 160)], 14, nseg=8)
    tube(X.mesh(M_['radiator']), [(-480, 34, 580), (480, 34, 580)], 14, nseg=8)
    for x in (-440, 440):
        rbox(X.mesh(M_['radiator']), (x - 14, 14, 0), (x + 14, 54, 140), r=4, k=1)
        rbox(X.mesh(M_['radiator']), (x - 10, 0, 500), (x + 10, 14, 520), r=2, k=1)
    ML.save('radiator', X)
    coll('radiator', [((-480, 0, 140), (480, 60, 600))])


def curtains():
    """two gathered curtains on a rod, origin at the window centre on the wall face (y = 0), hanging into +y"""
    X = ML.Model()
    for s in (-1, 1):
        nx, nz = 14, 10
        P = np.zeros((nz, nx, 3)); UV = np.zeros((nz, nx, 2))
        for i in range(nz):
            z = 1820 - i * (1820 - 760) / (nz - 1)
            g = 1 - 0.45 * math.exp(-((z - 1150) / 160) ** 2)              # tie-back pinch
            for j in range(nx):
                u = j / (nx - 1)
                x = s * (690 + u * 300 * g) if s > 0 else -(690 + (1 - u) * 300 * g)
                P[i, j] = (x, 24 + 14 * math.sin(u * math.pi * 7), z)
                UV[i, j] = (u * 3, i / (nz - 1) * 4)
        from meshlib import grid_normals
        N = grid_normals(P); N = N * (1 if N[..., 1].mean() > 0 else -1)
        X.mesh(M_['curtain']).grid(P, N, UV)
    tube(X.mesh(M_['steel']), [(-1020, 30, 1840), (1020, 30, 1840)], 10, nseg=8)
    for x in (-1000, 1000):
        rbox(X.mesh(M_['steel']), (x - 8, 0, 1830), (x + 8, 36, 1850), r=2, k=1)
    ML.save('curtains', X)


def shelf_brackets():
    """the floating shelf over the desk: board + brackets, origin at the wall face centre, shelf into -x"""
    X = ML.Model()
    board = ((-256, -800, -32), (0, 800, 0))
    rbox(X.mesh(M_['wood_dark']), *board, r=4, k=1, tile=256)
    for y in (-700, 0, 700):
        mprism(X.mesh(M_['frame']), [(0, y - 8), (0, y + 8), (-200, y + 8), (-200, y - 8)], -150, -32, tile=64)
    pic(X.mesh(M_['rgbscroll']), (-256.6, 0, -16), (-1, 0, 0), 1560, 10)
    ML.save('shelf', X)
    coll('shelf', [board])


def ceiling_lamp():
    X = ML.Model()
    revolve(X.mesh(M_['white']), [(0, -40), (300, -40), (310, -20), (310, 0)], n=32)
    disc(X.mesh(M_['lamp']), 290, -40.5, up=False, n=32)
    pic(X.mesh(M_['rgbscroll']), (0, 0, -40.6), (0, 0, -1), 10, 10, up=(1, 0, 0))
    ML.save('ceiling_lamp', X)


def trophy():
    X = ML.Model()
    revolve(X.mesh(M_['black']), [(60, 0), (60, 40), (0, 40)], n=16, inward=True)
    revolve(X.mesh(M_['trophy']), [(10, 40), (14, 100), (12, 130), (70, 170), (80, 260), (0, 260)], n=20, inward=True)
    for s in (-1, 1):
        tube(X.mesh(M_['trophy']), [(s * 70, 0, 240), (s * 110, 0, 220), (s * 100, 0, 180), (s * 60, 0, 170)], 7, nseg=6)
    ML.save('trophy', X)


def games_row():
    """a row of game cases standing on the shelf, spines facing -x. Origin back centre."""
    X = ML.Model()
    rbox(X.mesh(M_['gamebox']), (-120, -200, 0), (0, 200, 150), r=2, k=1, tile=400)
    ML.save('games_row', X)


def glass_panel():
    """the PC's tempered-glass side panel lying on the floor"""
    X = ML.Model()
    rbox(X.mesh(M_['glass']), (-120, -220, 0), (120, 220, 6), r=2, k=1)
    rbox(X.mesh(M_['frame']), (-120, -220, 0), (120, -200, 7), r=2, k=1)
    ML.save('glass_panel', X)
    coll('glass_panel', [((-120, -220, 0), (120, 220, 6))])
