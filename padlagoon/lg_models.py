"""Couch Lock Lagoon (wop_padlagoon) - brush textures (texlib registry) and the map's own MD3/IQM models.

Couch Lock's props (bong, lava lamps, plants, bean bag, ashtray, grinder, jar, chips, hookah) are reused from
lounge/lounge_models.py (written to models/padlounge by LM.make). This module adds the water-park pieces.
Every model: z = 0 on the surface it stands on; COLL[name] = weapclip boxes/cylinders in model space.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_z
import balcony_textures as BT          # Couch Lock balcony: facade, brick, deck boards, street, night sky

TX = None
M_ = {}
COLL = {}

# shared layout sizes (model space)
COUCH_X = 1400                     # seat half length
SEAT_Y0, BACK_Y0, COUCH_Y1 = 900, 1520, 1792
SEAT_Z, BACK_Z, ARM_Z, LEG_Z = 400, 1000, 640, 64
ARM_W = 300
# the Couch Tub: seat cushions pulled off, the base lined with a tarp and filled by the garden hose
TUB_Y0, TUB_FLOOR, TUB_WATER = 948, 240, 384     # inner face of the front lip, tub floor (frame top), water top
LAND_X = 1100                                    # the end cushions left in place: landings at SEAT_Z beyond +-LAND_X
SPILL_X, SPILL_Z = 280, 368                      # the notch in the front lip the water falls over
TABLE = (-520, -520, 520, 120)     # coffee table top rect (world == model, origin at 0, 0)
TABLE_Z = 320
TV_STAND = (-2040, -400, -1648, 700, 560)


def coll(name, boxes=(), cyls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls))


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def pic(M, c, n, w, h, up=(0, 0, 1)):
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    M.poly([c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh], n, [(0, 0), (1, 0), (1, 1), (0, 1)])


# ================================================================================================= textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('carpet', np.asarray(BT.deck_boards(), np.float32), steps='woodsteps', scale=1.0)      # the balcony deck
    fc, fg = BT.facade()
    a('facade_glow', np.asarray(fg, np.float32), check_tile=False, scale=BT.FACADE_TILE[0] / 1024 * 2)
    a('facade', np.asarray(fc, np.float32), 'raw', check_tile=False, scale=BT.FACADE_TILE[0] / 1024 * 2,
      shader=facade_stanza(K.ns))
    a('brick', np.asarray(BT.brick(), np.float32), scale=1.0, extra='\tq3map_lightmapSampleSize 32\n')
    a('concrete', np.asarray(BT.concrete(), np.float32), scale=1.0)
    a('street', np.asarray(BT.street(), np.float32), 'raw', shader=selflit_stanza(K.ns, 'street'), scale=2.0)
    a('far_a', np.asarray(BT.far_building(), np.float32), 'raw', shader=selflit_stanza(K.ns, 'far_a'), scale=4.0)
    a('far_b', np.asarray(BT.far_building(415, (34, 28, 36)), np.float32), 'raw', shader=selflit_stanza(K.ns, 'far_b'), scale=4.0)
    a('slider_door', np.asarray(BT.nb_door(), np.float32), 'neon', rgb=(1, 0.8, 0.55), light=120, check_tile=False)
    a('rail_glass', TL.solid((170, 210, 220), 2, 61, 64), 'glass', rgb=(0.12, 0.16, 0.18), shadow=False)
    a('rail_steel', TL.metal((200, 204, 210)))
    a('sky', TL.solid((20, 22, 40), 2, 21, 64), 'raw', shader=sky_stanza(K.ns), check_tile=False)
    a('wall', wallpaper(), scale=1.25)
    a('ceiling', TL.solid((150, 140, 126), 4, 15, 256), scale=1.0)
    a('pool_tile', TL.tiles((70, 170, 205), grout=(210, 235, 240), cols=8, rows=8, offset=0.0, grout_w=0.05, seed=31), scale=0.5)
    a('pool_floor', pool_floor(), scale=0.75)
    a('coping', TL.tiles((236, 232, 220), grout=(150, 150, 140), cols=2, rows=1, offset=0.0, grout_w=0.03, seed=33), scale=0.5)
    a('drain', drain_tex(), check_tile=False)
    a('slide', slide_tex(), 'slick', glint=True)
    a('slipslide', slipslide_tex(), 'slick', glint=True)           # the yellow Slip'n'Slide sheet
    a('slip_edge', TL.solid((40, 120, 220), 3, 62, 64))
    a('gutter', TL.metal((226, 230, 234)), 'slick', glint=True)    # white PVC guttering: the shelf flume
    a('gutter_side', TL.solid((206, 210, 216), 3, 63, 64))
    a('cushion', TL.fabric((92, 46, 34), weave=96), steps='carpetsteps', scale=1.0)
    a('slide_side', TL.solid((240, 120, 40), 3, 41, 128))
    a('support', TL.metal((220, 220, 226)))
    a('skirting', TL.solid((60, 44, 30), 2, 16, 64))
    a('water', TL.solid((60, 150, 170), 6, 43, 128) + TL.N3(128, 3, 44, 8), 'water', rgb=(0.3, 0.62, 0.62), alpha=0.5,
      fog=(0.12, 0.32, 0.30, 1400))
    a('fog_haze', TL.solid((200, 200, 190), 2, 45, 64), 'fog', rgb=(0.22, 0.22, 0.2), dist=11000)
    a('neon_purple', TL.solid((220, 90, 255), 2, 19, 64), 'neon', rgb=(0.8, 0.35, 1.0), light=240)
    a('neon_green', TL.solid((120, 255, 120), 2, 20, 64), 'neon', rgb=(0.4, 1.0, 0.45), light=240)
    a('stash', TL.planks((120, 80, 46), n_planks=6, grain=10, seed=57), steps='woodsteps', scale=1.0)
    a('stash_lid', stash_lid(), check_tile=False)
    for i, art in enumerate(POSTERS):
        a(f'poster{i}', poster(*art), 'sign', check_tile=False)
    a('sign_lagoon', TL.neon('LAGOON', (0.4, 1.0, 0.8), w=1024, h=256), 'neon', rgb=(0.4, 1.0, 0.8), light=200, check_tile=False)
    TX.kit_defaults(pad_rgb=(120, 255, 150), rubber=(40, 50, 44))
    materials()
    return TX


def facade_stanza(ns):
    t = f'textures/{ns}/facade'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tq3map_lightmapSampleSize 64\n'
            f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            f'\t{{\n\t\tmap {t}_glow\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen identity\n\t}}\n}}\n\n')


def selflit_stanza(ns, nm):
    t = f'textures/{ns}/{nm}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
            f'\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t}}\n}}\n\n')


def sky_stanza(ns):
    """Couch Lock's painted night city (env/padlounge/night_*, written by BT.make_sky)"""
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 0.6 0.65 1 50 220 45\n\tq3map_skylight 55 3\n\tskyparms env/padlounge/night - -\n}}\n\n')


POSTERS = [('SPLASH OUT', 'NO RUNNING', (20, 60, 90), (120, 240, 255)),
           ('CHILL ZONE', 'EST. ON THE COUCH', (40, 20, 60), (190, 120, 255)),
           ('LIFEGUARD', 'OFF DUTY (NAPPING)', (150, 30, 30), (255, 230, 120))]


def shag(n=256):
    """dark olive shag carpet"""
    rng = np.random.default_rng(71)
    base = TL.fill(n, (78, 70, 44), 6, 71)
    tufts = rng.random((n // 2, n // 2))
    t = np.kron(tufts, np.ones((2, 2)))[..., None]
    return base * (0.8 + 0.35 * t)


def wallpaper(n=256):
    """retro wallpaper: teal with soft orange ovals"""
    x, y = TL.xy(n)
    base = TL.fill(n, (40, 84, 86), 4, 72)
    d = ((np.cos(x * 2 * math.pi * 4) + np.cos(y * 2 * math.pi * 4)) * 0.5)
    ring = np.clip(1 - np.abs(d - 0.55) * 8, 0, 1)[..., None]
    return base * (1 - ring) + ML.C((206, 120, 60)) * ring


def pool_floor(n=256):
    c = TL.tiles((90, 190, 220), grout=(200, 230, 236), cols=8, rows=8, offset=0.0, grout_w=0.05, seed=35, n=n)
    x, y = TL.xy(n)                                  # caustics
    k = 2 * math.pi
    ca = np.abs(np.sin(k * 3 * x + np.sin(k * 2 * y) * 1.5) * np.sin(k * 3 * y + np.sin(k * 2 * x) * 1.5))
    return c + (ca ** 4 * 60)[..., None]


def drain_tex(n=256):
    im = Image.new('RGB', (n, n), (180, 186, 190)); d = ImageDraw.Draw(im)
    d.ellipse((8, 8, n - 8, n - 8), fill=(60, 64, 70), outline=(230, 230, 230), width=6)
    for k in range(9):
        y = 40 + k * 22
        d.rounded_rectangle((44, y, n - 44, y + 10), 4, fill=(16, 18, 20))
    return np.asarray(im, np.float32)


def slide_tex(n=256):
    x, y = TL.xy(n)
    c = TL.fill(n, (40, 170, 230), 3, 46)
    return c + (np.sin(y * 2 * math.pi * 2) * 10)[..., None]


def slipslide_tex(n=256):
    """wet yellow plastic sheet with printed blue wave bands"""
    x, y = TL.xy(n)
    c = TL.fill(n, (250, 214, 40), 3, 64)
    w = (np.sin(y * 2 * math.pi * 4 + np.sin(x * 2 * math.pi * 2) * 1.2) > 0.86)[..., None]
    return np.where(w, ML.C((40, 150, 230)), c)


def tarp_tex(n=256):
    """blue polytarp: woven grid, crease lines"""
    x, y = TL.xy(n)
    c = TL.fill(n, (36, 100, 196), 3, 65)
    g = ((np.floor(x * 32) + np.floor(y * 32)) % 2)[..., None]
    c = c * (0.94 + 0.06 * g)
    cr = np.abs(np.sin((x * 3 + y * 2 + 0.15 * np.sin(x * 20)) * 2 * math.pi)) ** 24
    return c + (cr * 46)[..., None]


def falls_tex(w=128, h=256):
    """falling water: white-blue streaks, alpha from the streaks (tileable both ways)"""
    rng = np.random.default_rng(66)
    col = rng.random(w)
    col = (col + np.roll(col, 1) + np.roll(col, -1)) / 3
    x, y = np.meshgrid(np.arange(w) / w, np.arange(h) / h)
    st = 0.5 + 0.5 * np.sin(y * 2 * math.pi * 3 + col[None, :] * 20)
    a = np.clip(0.35 + 0.5 * col[None, :] * 1.6 * (0.6 + 0.4 * st), 0.25, 0.92)
    rgb = np.zeros((h, w, 3), np.float32) + ML.C((170, 225, 245))
    rgb = rgb + (st * col[None, :] * 80)[..., None]
    return np.clip(rgb, 0, 255), np.uint8(a * 255)


def swirl_tex(n=256):
    """whirlpool spiral (additive) for the water over the drain"""
    x, y = TL.xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    s = (np.sin(a * 3 + r * 34) * 0.5 + 0.5) ** 3
    f = np.clip(1 - r * 2, 0, 1) * np.clip(r * 14, 0, 1)
    return (s * f)[..., None] * ML.C((150, 235, 235))


def stash_lid(w=512, h=512):
    im = Image.fromarray(np.uint8(np.clip(TL.planks((120, 80, 46), n_planks=6, grain=10, seed=57, n=512), 0, 255)))
    d = ImageDraw.Draw(im)
    d.text((70, 200), 'STASH', font=ML.font(110, serif=True), fill=(250, 220, 120), stroke_width=4, stroke_fill=(40, 20, 10))
    return np.asarray(im, np.float32)


def poster(title, sub, bg, fg, w=512, h=768):
    im = Image.new('RGB', (w, h), tuple(bg)); d = ImageDraw.Draw(im)
    for k in range(12):                                         # waves
        y = h * 0.45 + k * 18
        d.arc((-40, y - 60, w + 40, y + 60), 200, 340, fill=tuple(int(v * (0.5 + k / 24)) for v in fg), width=6)
    d.ellipse((w * 0.3, h * 0.12, w * 0.7, h * 0.4), fill=(255, 220, 90))
    f = ML.font(int(w / max(6, len(title)) * 1.45), serif=False)
    tw = d.textlength(title, font=f)
    d.text(((w - tw) / 2, h * 0.70), title, font=f, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    f2 = ML.font(28, serif=False); tw = d.textlength(sub, font=f2)
    d.text(((w - tw) / 2, h * 0.86), sub, font=f2, fill=tuple(fg))
    d.rectangle((6, 6, w - 7, h - 7), outline=(250, 250, 250), width=6)
    return np.asarray(im, np.float32)


def stripe_tex(c1, c2, k=6, n=256):
    x, y = TL.xy(n)
    s = (np.floor(x * k) % 2)[..., None]
    return ML.C(c1) * s + ML.C(c2) * (1 - s)


# ================================================================================================= materials
def materials():
    m('velvet', TL.fabric((92, 46, 34), weave=96), shade=70)          # rust corduroy couch
    m('velvet_dark', TL.fabric((70, 34, 26), weave=96), shade=60)
    m('wood', TL.planks((110, 72, 40), n_planks=4, grain=10, vertical=True), shade=20)
    m('woodh', TL.planks((110, 72, 40), n_planks=4, grain=10), shade=20, tag='h')
    m('black', TL.solid((26, 26, 30), 2, 31), shade=40)
    m('steel', TL.metal((176, 180, 188)), 'lms', v=0.3, shade=50)
    m('tv_screen', tv_screen(), 'glow')
    m('canvas', TL.fabric((40, 42, 40), weave=80), shade=40)
    m('mylar', TL.metal((210, 214, 220), brushed=False), 'lms', v=0.5, shade=30)
    m('grow', TL.solid((255, 120, 230), 1, 47, 32), 'glow')
    m('zip', TL.solid((20, 20, 22), 2, 48, 64), shade=20)
    m('float_pink', donut_tex(), shade=80)
    m('float_yellow', TL.solid((255, 214, 40), 2, 49, 64), 'lms', v=0.2, shade=80)
    m('float_orange', TL.solid((255, 120, 30), 2, 50, 64), 'lms', v=0.2, shade=80)
    m('float_white', TL.solid((245, 245, 245), 2, 51, 64), 'lms', v=0.2, shade=80)
    m('lounger', stripe_tex((40, 160, 170), (240, 240, 230)), shade=60)
    m('umbrella', umbrella_tex(), shade=40, two=True)
    m('towel', stripe_tex((230, 70, 90), (250, 220, 120), k=8), shade=80)
    m('tarp', tarp_tex(), shade=40)
    frgb, fa = falls_tex()
    m('falls', frgb, 'flow', alpha=fa, speed=-1.5)
    m('swirl', swirl_tex(), 'add', tcmod='rotate 40')
    m('hose', TL.solid((40, 150, 60), 3, 67, 64), shade=80)
    m('brass', TL.metal((200, 160, 70), brushed=False), 'lms', v=0.4, shade=60)
    m('stone', TL.tiles((236, 232, 220), grout=(150, 150, 140), cols=4, rows=1, offset=0.0, grout_w=0.03, seed=33), shade=20)
    m('fairy', TL.solid((255, 210, 140), 1, 85, 32), 'glow', wave='wave sin 0.85 0.15 0 0.3')
    m('tile_m', TL.tiles((70, 170, 205), grout=(210, 235, 240), cols=8, rows=8, offset=0.0, grout_w=0.05, seed=31), shade=20)


def tv_screen(w=512, h=288):
    """a nature doc about dolphins on the telly"""
    im = Image.new('RGB', (w, h), (20, 70, 120)); d = ImageDraw.Draw(im)
    for k in range(h // 2, h):
        t = (k - h / 2) / (h / 2)
        d.line((0, k, w, k), fill=(int(10 + 20 * t), int(60 + 40 * t), int(110 + 50 * t)))
    for k in range(h // 2):
        t = k / (h / 2)
        d.line((0, k, w, k), fill=(int(120 + 100 * t), int(180 + 50 * t), 250))
    d.ellipse((w * 0.36, h * 0.38, w * 0.66, h * 0.62), fill=(130, 150, 170))
    d.polygon([(w * 0.62, h * 0.48), (w * 0.74, h * 0.36), (w * 0.72, h * 0.6)], fill=(130, 150, 170))
    d.polygon([(w * 0.5, h * 0.4), (w * 0.54, h * 0.28), (w * 0.58, h * 0.4)], fill=(120, 140, 160))
    d.ellipse((w * 0.4, h * 0.45, w * 0.43, h * 0.48), fill=(10, 10, 10))
    d.text((10, h - 40), 'DEEP BLUE CHILL', font=ML.font(28, serif=False), fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def donut_tex(n=256):
    x, y = TL.xy(n)
    c = TL.fill(n, (255, 140, 190), 2, 52)
    rng = np.random.default_rng(53)
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255))); d = ImageDraw.Draw(im)
    cols = [(255, 255, 255), (120, 220, 255), (255, 240, 90), (140, 240, 140)]
    for _ in range(60):
        px, py = rng.integers(0, n, 2); a = rng.random() * math.pi
        d.line((px, py, px + 10 * math.cos(a), py + 10 * math.sin(a)), fill=cols[rng.integers(4)], width=4)
    return np.asarray(im, np.float32)


def umbrella_tex(n=256):
    x, y = TL.xy(n)
    s = (np.floor(x * 8) % 2)[..., None]
    return ML.C((240, 80, 60)) * s + ML.C((250, 240, 220)) * (1 - s)


# ================================================================================================= models
def all_models():
    couch(); couch_stuff(); waterfall(); cushion(); hose(); coping_ring(); festoon(); rail_posts(); coffee_table(); tv_stand(); wall_shelf(); grow_tent(); floats(); lounger(); umbrella(); towel()


def tquad(M, P, n, tile=256.0):
    """a quad with planar UVs in `tile` units (P = four corners in order, n = facing normal)"""
    P = [np.asarray(p, float) for p in P]
    n = np.asarray(n, float)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a); u /= np.linalg.norm(u); v = np.cross(n, u)
    M.poly(P, n, [(float(p @ u) / tile, float(p @ v) / tile) for p in P])


def couch():
    """the Couch Tub (model origin = world 0, 0, 0): the giant 70s corduroy couch with its seat cushions pulled off,
    lined with a blue tarp and filled with water. Back top 1000 (walkable), arms 640, an end cushion left at each
    end (landings at 400), a rolled tarp lip along the front (400) with a spill notch in the middle where the
    water falls onto the steps below. Short legs: the 64u crawl cave under it is behind that waterfall."""
    X = ML.Model(); v, vd, tp = M_['velvet'], M_['velvet_dark'], M_['tarp']
    L = COUCH_X
    legs = [((x - 40, y - 40, 0), (x + 40, y + 40, LEG_Z)) for x in (-L + 60, -480, 480, L - 60) for y in (SEAT_Y0 + 60, COUCH_Y1 - 60)]
    for a, b in legs: rbox(X.mesh(M_['wood']), a, b, r=8, k=2, tile=128)
    frame = ((-L, SEAT_Y0, LEG_Z), (L, COUCH_Y1, TUB_FLOOR))
    rbox(X.mesh(vd), *frame, r=16, k=2, tile=256)
    back = ((-L, BACK_Y0, TUB_FLOOR), (L, COUCH_Y1, BACK_Z))
    for k in range(3):
        x0 = -L + k * (2 * L / 3); x1 = x0 + 2 * L / 3
        rbox(X.mesh(v), (x0 + 4, BACK_Y0, TUB_FLOOR), (x1 - 4, COUCH_Y1, BACK_Z), r=50, k=4, tile=320,
             inflate=lambda x, y, z, n: 18 * max(0, -n[1]))
    arms = [((-L - ARM_W, SEAT_Y0, 0), (-L, COUCH_Y1, ARM_Z)), ((L, SEAT_Y0, 0), (L + ARM_W, COUCH_Y1, ARM_Z))]
    for a, b in arms: rbox(X.mesh(v), a, b, r=60, k=4, tile=320, inflate=lambda x, y, z, n: 12 * max(0, n[2]))
    lands = [((-L, TUB_Y0, TUB_FLOOR), (-LAND_X, BACK_Y0, SEAT_Z)), ((LAND_X, TUB_Y0, TUB_FLOOR), (L, BACK_Y0, SEAT_Z))]
    for a, b in lands:
        rbox(X.mesh(v), (a[0] + 2, a[1], a[2]), (b[0] - 2, b[1], b[2]), r=30, k=3, tile=320)
    lips = [((-L, SEAT_Y0, TUB_FLOOR), (-SPILL_X, TUB_Y0, SEAT_Z)), ((SPILL_X, SEAT_Y0, TUB_FLOOR), (L, TUB_Y0, SEAT_Z)),
            ((-SPILL_X, SEAT_Y0, TUB_FLOOR), (SPILL_X, TUB_Y0, SPILL_Z))]
    for a, b in lips: rbox(X.mesh(tp), a, b, r=14, k=3, tile=256)
    # the tarp: tub floor, up the back cushions and the end cushions, hanging a little over the front
    e = 0.8
    tquad(X.mesh(tp), [(-LAND_X, TUB_Y0, TUB_FLOOR + e), (LAND_X, TUB_Y0, TUB_FLOOR + e), (LAND_X, BACK_Y0, TUB_FLOOR + e),
                       (-LAND_X, BACK_Y0, TUB_FLOOR + e)], (0, 0, 1))
    tquad(X.mesh(tp), [(-LAND_X, BACK_Y0 - 19, TUB_FLOOR), (LAND_X, BACK_Y0 - 19, TUB_FLOOR), (LAND_X, BACK_Y0 - 19, SEAT_Z + 40),
                       (-LAND_X, BACK_Y0 - 19, SEAT_Z + 40)], (0, -1, 0))
    for sx in (-1, 1):
        x = sx * (LAND_X - e)
        tquad(X.mesh(tp), [(x, TUB_Y0, TUB_FLOOR), (x, BACK_Y0, TUB_FLOOR), (x, BACK_Y0, SEAT_Z + e), (x, TUB_Y0, SEAT_Z + e)], (-sx, 0, 0))
    tquad(X.mesh(tp), [(-L, SEAT_Y0 - e, 300), (L, SEAT_Y0 - e, 300), (L, SEAT_Y0 - e, SEAT_Z - 10), (-L, SEAT_Y0 - e, SEAT_Z - 10)], (0, -1, 0))
    for x in range(-L + 100, L, 200):                                   # brass grommets along the hanging edge
        tube(X.mesh(M_['brass']), [(x, SEAT_Y0 - 3, 316), (x, SEAT_Y0 - 0.5, 316)], 9, nseg=8)
    ML.save('couch', X)
    coll('couch', legs + [frame, back] + arms + lands + lips)


def waterfall():
    """Couch Falls: the sheet of water spilling over the lip notch down to the steps in front of the couch, plus the
    wet film running over the notch. World coordinates; nonsolid (you walk through it into the cave)."""
    X = ML.Model()
    prof = [(TUB_Y0 + 30, TUB_WATER + 1), (TUB_Y0, TUB_WATER + 1), (SEAT_Y0 + 20, TUB_WATER - 2), (SEAT_Y0 - 4, SPILL_Z + 6),
            (SEAT_Y0 - 16, SPILL_Z - 20), (SEAT_Y0 - 22, 300), (SEAT_Y0 - 24, 200), (SEAT_Y0 - 24, 100), (SEAT_Y0 - 24, 0),
            (SEAT_Y0 - 24, -14)]
    xs = np.linspace(-SPILL_X + 8, SPILL_X - 8, 9)
    P = np.zeros((len(prof), len(xs), 3)); UV = np.zeros((len(prof), len(xs), 2))
    d = 0.0
    for i, (y, z) in enumerate(prof):
        if i: d += math.hypot(y - prof[i - 1][0], z - prof[i - 1][1])
        for j, x in enumerate(xs):
            P[i, j] = (x, y + 5 * math.sin(j * 2.1 + i * 0.7) * min(1, i / 4), z)
            UV[i, j] = (x / 140.0, d / 256.0)
    from meshlib import grid_normals
    N = grid_normals(P)
    if N[..., 1].mean() > 0: N = -N
    X.mesh(M_['falls']).grid(P, N, UV)
    for k, x in enumerate(np.linspace(-SPILL_X + 40, SPILL_X - 40, 7)):       # foam where it lands
        sphere(X.mesh(M_['float_white']), (x, SEAT_Y0 - 30 + 8 * math.sin(k * 2.3), -12), 26 + 6 * math.sin(k * 1.7), nu=8, nv=5)
    ML.save('waterfall', X)


def cushion():
    """one of the seat cushions pulled off the couch (lying flat; origin footprint centre)"""
    X = ML.Model()
    b = ((-466, -310, 0), (466, 310, 160))
    rbox(X.mesh(M_['velvet']), *b, r=40, k=4, tile=320, inflate=lambda x, y, z, n: 14 * max(0, n[2]))
    ML.save('cushion', X)
    coll('cushion', [b])


HOSE = [(1890, 1786, 560), (1890, 1730, 540), (1880, 1690, 300), (1840, 1700, 30), (1760, 1740, 16), (1730, 1750, 300),
        (1690, 1740, 650), (1560, 1750, 656), (1440, 1730, 700), (1390, 1690, 1010), (1300, 1600, 1016), (1250, 1500, 900),
        (1215, 1300, 520), (1180, 1100, 418), (1160, 1010, 416)]


def hose():
    """the garden hose that started it all: from the tap on the facade, over the couch's east arm and back, down
    onto the east end cushion. World coordinates."""
    X = ML.Model()
    P = [np.array(p, float) for p in HOSE]
    pts = []
    for i in range(len(P) - 1):                                         # Catmull-Rom so it bends like a hose
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for t in np.linspace(0, 1, 5, endpoint=False):
            pts.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    pts.append(tuple(P[-1]))
    tube(X.mesh(M_['hose']), pts, 13, nseg=8)
    a, b = np.array(pts[-1]), np.array(pts[-1]) + (np.array(pts[-1]) - np.array(pts[-3])) / np.linalg.norm(np.array(pts[-1]) - np.array(pts[-3])) * 46
    tube(X.mesh(M_['brass']), [tuple(a), tuple(b)], [15, 9], 8)
    rbox(X.mesh(M_['brass']), (1868, 1770, 540), (1912, 1792, 584), r=4, k=1)            # the tap
    tube(X.mesh(M_['brass']), [(1890, 1770, 590), (1890, 1770, 620)], 6, nseg=6)
    rbox(X.mesh(M_['float_orange']), (1860, 1762, 620), (1920, 1778, 630), r=3, k=1)
    ML.save('hose', X)


POOL_C, POOL_A = (0, -200), 864                 # round pool: centre, apothem (16-gon, flat edges on the axes)
POOL_R = POOL_A / math.cos(math.pi / 16)


def coping_ring():
    """pale stone coping round the pool (a flat ring just proud of the deck), open at the north where the steps
    come down from the couch. World coordinates."""
    X = ML.Model()
    revolve(X.mesh(M_['stone']), [(POOL_R + 6, 1.0), (POOL_R + 62, 1.0)], 13.0, n=13, a0=123.75, a1=416.25, inward=True,
            cx=POOL_C[0], cy=POOL_C[1], v_of=lambda r, z: (r - POOL_R) / 64.0)
    ML.save('coping_ring', X)


def couch_stuff():
    """what lives on the couch: throw pillows, a crumpled blanket, an open pizza box, a remote, a games controller,
    a popcorn bowl (each its own MD3 so they sit on their own surfaces)"""
    arts = [pillow_sunburst(), pillow_palms(), pillow_tiedye(), pillow_chill()]
    for k, art in enumerate(arts):
        key = f'pillow{k}'
        m(key, np.roll(art, art.shape[1] // 2, axis=1), shade=80, tag=key)     # rbox u = x / tile is 0 at the centre
        X = ML.Model()
        rbox(X.mesh(M_[key]), (-130, -45, 0), (130, 45, 250), r=40, k=4, tile=264,
             inflate=lambda x, y, z, n: 22 * abs(n[1]) * (1 - min(1, (abs(x) / 130) ** 2)) * (1 - min(1, ((z - 125) / 125) ** 2)))
        ML.save(key, X)
        coll(key, [((-130, -45, 0), (130, 45, 250))])
    m('blanket', TL.fabric((150, 60, 40), weave=48), shade=90, tag='bl')
    X = ML.Model()
    for k, (x, y, rx, ry, h) in enumerate(((0, 0, 260, 200, 70), (180, 80, 160, 150, 90), (-170, -60, 170, 160, 60), (60, -150, 150, 110, 50))):
        ellipsoid(X.mesh(M_['blanket']), (x, y, 0), rx, ry, h, nu=16, nv=8, flat_bottom=0,
                  bump=lambda p, t, s=k: 1 + 0.10 * math.sin(5 * t + s) * math.cos(3 * p))
    ML.save('blanket', X)
    coll('blanket', [((-300, -220, 0), (330, 220, 70))])
    m('pizza_box', pizza_box_tex(), shade=10, tag='pb')
    m('pizza', pizza_tex(), shade=20, tag='pz')
    X = ML.Model()
    rbox(X.mesh(M_['pizza_box']), (-160, -160, 0), (160, 160, 24), r=2, k=1, tile=320)
    revolve(X.mesh(M_['pizza']), [(0.01, 24.6), (140, 24.6), (146, 30), (146, 33)], n=24, inward=True)
    lid = [(-160, 160, 24), (160, 160, 24), (160, 220, 330), (-160, 220, 330)]
    P = [np.array(v, float) for v in lid]
    X.mesh(M_['pizza_box']).poly(P, (0, -0.98, 0.18), [(0, 1), (1, 1), (1, 0), (0, 0)])
    X.mesh(M_['pizza_box']).poly(P[::-1], (0, 0.98, -0.18), [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('pizza_box', X)
    coll('pizza_box', [((-160, -160, 0), (160, 160, 34))])
    X = ML.Model()                                          # TV remote
    rbox(X.mesh(M_['black']), (-90, -24, 0), (90, 24, 18), r=8, k=2)
    for k in range(6):
        sphere(X.mesh(M_['float_orange' if k == 0 else 'float_white']), (-60 + k * 22, 0, 18), 6, nu=8, nv=4, flat_bottom=-1)
    ML.save('remote', X)
    X = ML.Model()                                          # games controller with its cable
    for sx in (-1, 1):
        ellipsoid(X.mesh(M_['black']), (0, sx * 46, 14), 38, 36, 14, nu=12, nv=6, flat_bottom=-14)
    rbox(X.mesh(M_['black']), (-28, -48, 0), (28, 48, 24), r=10, k=2)
    for (x, y) in ((10, 50), (-8, 58), (2, 66), (2, 42)):
        sphere(X.mesh(M_['grow']), (x, y, 26), 5, nu=8, nv=4)
    tube(X.mesh(M_['black']), [(-28, 0, 8), (-90, 10, 3), (-200, -40, 3), (-300, 20, 3)], 3, nseg=5)
    ML.save('controller', X)
    m('popcorn', popcorn_tex(), shade=60, tag='pc')
    X = ML.Model()
    revolve(X.mesh(M_['float_white']), [(60, 0), (110, 110), (104, 110), (56, 8), (0, 8)], n=24, u_tiles=4)
    rng = np.random.default_rng(97)
    for _ in range(22):
        a = rng.random() * 2 * math.pi; d = rng.random() * 85
        sphere(X.mesh(M_['popcorn']), (math.cos(a) * d, math.sin(a) * d, 100 + rng.random() * 28), 18, nu=8, nv=5,
               bump=lambda p, t: 1 + 0.25 * math.sin(4 * t) * math.sin(3 * p))
    ML.save('popcorn', X)
    coll('popcorn', cyls=[(0, 0, 110, 0, 110)])


# ------------------------------------------------------------------------------------------------- pillow covers
# one 256 texel tile = one pillow face (rbox tile=264), so each motif reads whole; a woven grain over every cover
def _weave(a, k=0.10, seed=0):
    x, y = TL.xy(a.shape[0])
    w = (np.sin(x * 2 * math.pi * 96) * np.sin(y * 2 * math.pi * 96)) * 0.5 + 0.5
    return a * (1 - k + k * w[..., None]) * (0.96 + 0.08 * TL.N3(a.shape[0], 1, 90 + seed, 4) / 255)


def _piping(d, n, col):
    d.rectangle((2, 2, n - 3, n - 3), outline=col, width=5)


def pillow_sunburst(n=256):
    """70s mustard: concentric orange/brown rings in quarter circles from each corner, cream piping"""
    im = Image.new('RGB', (n, n), (232, 178, 52)); d = ImageDraw.Draw(im)
    cols = [(196, 92, 32), (120, 60, 30), (244, 220, 160), (210, 120, 40)]
    for (cx, cy) in ((0, 0), (n, 0), (0, n), (n, n)):
        for k, r in enumerate(range(150, 20, -26)):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=cols[k % 4])
    d.ellipse((n / 2 - 34, n / 2 - 34, n / 2 + 34, n / 2 + 34), fill=(120, 60, 30))
    d.ellipse((n / 2 - 18, n / 2 - 18, n / 2 + 18, n / 2 + 18), fill=(244, 220, 160))
    _piping(d, n, (244, 220, 160))
    return _weave(np.asarray(im, np.float32), seed=1)


def pillow_palms(n=256):
    """tropical print for the lagoon: palm and monstera leaves on teal, with a few hibiscus flowers"""
    im = Image.new('RGB', (n, n), (36, 120, 118)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(91)
    greens = [(40, 160, 90), (90, 200, 110), (20, 100, 70)]
    for _ in range(9):                                            # palm fronds: a stem + leaflets
        x, y = rng.uniform(0, n, 2); a = rng.uniform(0, 2 * math.pi); L = rng.uniform(70, 120)
        col = greens[rng.integers(3)]
        for t in np.linspace(0.1, 1, 9):
            px, py = x + math.cos(a) * L * t, y + math.sin(a) * L * t
            for s in (-1, 1):
                b = a + s * 1.0
                ln = 34 * (1 - t * 0.6)
                d.line((px, py, px + math.cos(b) * ln, py + math.sin(b) * ln), fill=col, width=6)
        d.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(20, 80, 50), width=3)
    for _ in range(4):                                            # hibiscus
        x, y = rng.uniform(20, n - 20, 2)
        for k in range(5):
            b = k * 2 * math.pi / 5
            d.ellipse((x + math.cos(b) * 12 - 11, y + math.sin(b) * 12 - 11, x + math.cos(b) * 12 + 11, y + math.sin(b) * 12 + 11),
                      fill=(240, 70, 100))
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 220, 60))
    _piping(d, n, (250, 236, 200))
    return _weave(np.asarray(im, np.float32), seed=2)


def pillow_tiedye(n=256):
    """spiral tie-dye in pink, purple, orange and lime"""
    x, y = TL.xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    t = (a / (2 * math.pi) * 3 + r * 6 + 0.15 * np.sin(r * 40)) % 1.0
    pal = np.array([(255, 80, 160), (150, 70, 220), (255, 150, 40), (170, 240, 60), (255, 80, 160)], np.float32)
    idx = t * 4; i0 = np.floor(idx).astype(int); f = (idx - i0)[..., None]
    c = pal[i0] * (1 - f) + pal[np.minimum(i0 + 1, 4)] * f
    c *= (0.85 + 0.15 * np.cos(a * 12 + r * 30))[..., None]          # crinkle streaks
    c = np.where((r < 0.05)[..., None], np.array((255, 255, 255), np.float32), c)
    return _weave(c, k=0.08, seed=3)


def pillow_chill(n=256):
    """purple-and-green plaid with a stitched patch that says CHILL"""
    x, y = TL.xy(n)
    c = np.zeros((n, n, 3), np.float32) + ML.C((90, 50, 140))
    for (k, col, w) in ((4, (60, 30, 100), 0.18), (4, (120, 200, 90), 0.05), (8, (170, 130, 220), 0.025)):
        sx = (np.abs((x * k) % 1 - 0.5) < w); sy = (np.abs((y * k) % 1 - 0.5) < w)
        c = np.where((sx | sy)[..., None], c * 0.5 + ML.C(col) * 0.5, c)
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255))); d = ImageDraw.Draw(im)
    d.rounded_rectangle((34, 88, n - 34, 168), 14, fill=(250, 236, 200), outline=(60, 30, 100), width=4)
    for xx in range(44, n - 40, 10):                               # stitching
        d.line((xx, 96, xx + 5, 96), fill=(150, 90, 200), width=2); d.line((xx, 160, xx + 5, 160), fill=(150, 90, 200), width=2)
    f = ML.font(52, serif=False); tw = d.textlength('CHILL', font=f)
    d.text(((n - tw) / 2, 100), 'CHILL', font=f, fill=(90, 50, 140))
    _piping(d, n, (120, 200, 90))
    return _weave(np.asarray(im, np.float32), seed=4)


def pizza_box_tex(n=256):
    im = Image.fromarray(np.uint8(np.clip(TL.fill(n, (176, 136, 92), 6, 81), 0, 255))); d = ImageDraw.Draw(im)
    d.ellipse((40, 40, 216, 216), outline=(170, 30, 30), width=8)
    d.text((66, 104), 'PADDYS', font=ML.font(30), fill=(170, 30, 30))
    d.text((84, 140), 'PIZZA', font=ML.font(26), fill=(30, 110, 40))
    return np.asarray(im, np.float32)


def pizza_tex(n=256):
    """top view of a pizza with two slices gone (u/v = disc projection from revolve: v runs out from the centre)"""
    x, y = TL.xy(n)
    c = TL.fill(n, (236, 170, 60), 6, 82)
    rng = np.random.default_rng(83)
    im = Image.fromarray(np.uint8(np.clip(c, 0, 255))); d = ImageDraw.Draw(im)
    for _ in range(26):
        px, py = rng.integers(0, n), rng.integers(0, int(n * 0.85))
        d.ellipse((px - 10, py - 7, px + 10, py + 7), fill=(170, 40, 30))
    d.rectangle((0, int(n * 0.88), n, n), fill=(200, 130, 60))
    return np.asarray(im, np.float32)


def popcorn_tex(n=64):
    return TL.fill(n, (250, 240, 200), 8, 84)


def rail_posts():
    """round steel posts on the deck side of the glass railings (south y -1792, east x 2048), world coordinates"""
    X = ML.Model(); st = M_['steel']
    pts = [(x, -1792 + 16) for x in range(-1536, 2048, 512)] + [(2048 - 16, y) for y in range(-1280, 1792, 512)] + [(2032, -1776)]
    for (x, y) in pts:
        tube(X.mesh(st), [(x, y, 0), (x, y, 424)], 14, nseg=10)
        revolve(X.mesh(st), [(26, 0), (26, 10), (14, 14), (0.01, 14)], n=12, cx=x, cy=y, inward=True)
    ML.save('rail_posts', X)


FESTOON = [(-1990, 1780, 1700), (-1990, -1760, 1400), (1450, -1760, 1400), (1990, 1780, 1700)]


def festoon():
    """festoon string lights: two tall poles at the south railing corners, strings to hooks on the building (north
    side) and between the poles, sagging, with warm bulbs. World coordinates (origin 0, 0, 0)."""
    X = ML.Model()
    for (x, y, z) in FESTOON[1:3]:
        tube(X.mesh(M_['steel']), [(x, y, 0), (x, y, z + 20)], 10, nseg=8)
        revolve(X.mesh(M_['black']), [(40, 0), (40, 12), (12, 16), (0.01, 16)], n=12, cx=x, cy=y, inward=True)
    for (x, y, z) in (FESTOON[0], FESTOON[3]):
        rbox(X.mesh(M_['steel']), (x - 10, y - 12, z - 10), (x + 10, y + 12, z + 10), r=3, k=1)
    for (a, b) in ((0, 1), (1, 2), (2, 3), (0, 2), (3, 1)):
        A, B = np.array(FESTOON[a], float), np.array(FESTOON[b], float)
        L = np.linalg.norm(B - A); n = max(8, int(L / 220))
        pts = []
        for i in range(n + 1):
            t = i / n
            p = A + (B - A) * t; p[2] -= 4 * 160 * t * (1 - t)
            pts.append(tuple(p))
        tube(X.mesh(M_['black']), pts, 2.5, nseg=4, caps=(False, False))
        for p in pts[1:-1]:
            sphere(X.mesh(M_['fairy']), (p[0], p[1], p[2] - 26), 14, nu=8, nv=5)
            tube(X.mesh(M_['black']), [p, (p[0], p[1], p[2] - 14)], 3, nseg=4)
    ML.save('festoon', X)


def coffee_table():
    """the island: low teak coffee table standing on the pool floor (z -192), top TABLE_Z. Model origin at the pool
    floor under the table centre."""
    X = ML.Model(); x0, y0, x1, y1 = TABLE; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    H = TABLE_Z + 192
    top = ((-hx, -hy, H - 32), (hx, hy, H))
    rbox(X.mesh(M_['woodh']), *top, r=8, k=2, tile=512)
    legs = [((sx * (hx - 40) - 40, sy * (hy - 40) - 40, 0), (sx * (hx - 40) + 40, sy * (hy - 40) + 40, H - 32))
            for sx in (-1, 1) for sy in (-1, 1)]
    for a, b in legs: rbox(X.mesh(M_['wood']), a, b, r=10, k=2, tile=256)
    apron = [((-hx + 80, -hy + 40, H - 96), (hx - 80, -hy + 64, H - 32)), ((-hx + 80, hy - 64, H - 96), (hx - 80, hy - 40, H - 32))]
    for a, b in apron: rbox(X.mesh(M_['wood']), a, b, r=4, k=1)
    ML.save('coffee_table', X)
    coll('coffee_table', [top] + legs + apron)
    return (cx, cy)


def tv_stand():
    """teak sideboard against the west wall with a flat telly on it (screen faces +x). Model origin = stand footprint
    centre on the floor."""
    X = ML.Model(); x0, y0, x1, y1, h = TV_STAND
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    body = ((-hx, -hy, 48), (hx, hy, h))
    rbox(X.mesh(M_['woodh']), *body, r=8, k=2, tile=512)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(X.mesh(M_['black']), [(sx * (hx - 40), sy * (hy - 40), 0), (sx * (hx - 30), sy * (hy - 30), 48)], 12, nseg=8)
    for k in range(3):
        y = -hy + 60 + k * (2 * hy - 120) / 3
        rbox(X.mesh(M_['wood']), (hx, y + 10, 90), (hx + 6, y + (2 * hy - 120) / 3 - 10, h - 40), r=2, k=1)
    tv = ((-hx + 40, -300, h + 20), (-hx + 70, 300, h + 360))
    rbox(X.mesh(M_['black']), *tv, r=6, k=2)
    rbox(X.mesh(M_['black']), (-hx + 30, -60, h), (-hx + 110, 60, h + 20), r=4, k=1)
    pic(X.mesh(M_['tv_screen']), (-hx + 70.6, 0, h + 190), (1, 0, 0), 570, 320)
    ML.save('tv_stand', X)
    coll('tv_stand', [((-hx, -hy, 0), (hx, hy, h)), tv])


def wall_shelf():
    """long floating shelf on the west wall (origin at the wall face centre, top at z 0, shelf into +x)"""
    X = ML.Model()
    board = ((0, -675, -32), (320, 675, 0))
    rbox(X.mesh(M_['woodh']), *board, r=4, k=1, tile=512)
    for y in (-560, 0, 560):
        mprism(X.mesh(M_['steel']), [(0, y - 10), (0, y + 10), (260, y + 10), (260, y - 10)], -200, -32, tile=64)
    ML.save('wall_shelf', X)
    coll('wall_shelf', [board])


TENT = (1496, -1784, 2040, -1096, 1000)      # x0 y0 x1 y1 height (world)
TENT_DOOR = (-1540, -1340, 600)              # door on the west side: y0 y1 top


def grow_tent():
    """grow tent turned changing cabin: black canvas outside, mylar inside, zip door on the west side, walkable roof.
    Built as convex wall slabs (also the weapclip). Model origin = tent footprint centre on the floor."""
    x0, y0, x1, y1, H = TENT; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    t = 16; dy0, dy1, dz = TENT_DOOR
    B = [((x0, y0, 0), (x1, y0 + t, H)), ((x0, y1 - t, 0), (x1, y1, H)),           # south / north walls
         ((x1 - t, y0 + t, 0), (x1, y1 - t, H)),                                    # east wall
         ((x0, y0 + t, 0), (x0 + t, dy0, H)), ((x0, dy1, 0), (x0 + t, y1 - t, H)),   # west wall with the door
         ((x0, dy0, dz), (x0 + t, dy1, H)),
         ((x0, y0, H), (x1, y1, H + 16))]                                            # roof
    X = ML.Model()
    for (a, b) in B:
        a = (a[0] - cx, a[1] - cy, a[2]); b = (b[0] - cx, b[1] - cy, b[2])
        rbox(X.mesh(M_['canvas']), a, b, r=3, k=1, tile=256)
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    pic(X.mesh(M_['mylar']), (hx - t - 0.6, 0, H / 2), (-1, 0, 0), 2 * hy - 2 * t - 4, H - 4)    # mylar lining
    pic(X.mesh(M_['mylar']), (0, -hy + t + 0.6, H / 2), (0, 1, 0), 2 * hx - 2 * t - 4, H - 4)
    pic(X.mesh(M_['mylar']), (0, hy - t - 0.6, H / 2), (0, -1, 0), 2 * hx - 2 * t - 4, H - 4)
    pic(X.mesh(M_['mylar']), (0, 0, H - 0.6), (0, 0, -1), 2 * hx - 2 * t - 4, 2 * hy - 2 * t - 4, up=(1, 0, 0))
    for (yy) in ((dy0 - cy) - 8, (dy1 - cy) + 8):            # zip strips round the door
        rbox(X.mesh(M_['zip']), (-hx - 4, yy - 4, 0), (-hx, yy + 4, dz), r=1, k=1)
    rbox(X.mesh(M_['zip']), (-hx - 4, dy0 - cy - 8, dz), (-hx, dy1 - cy + 8, dz + 8), r=1, k=1)
    for sx in (-1, 1):                                      # frame poles on the roof edges
        tube(X.mesh(M_['steel']), [(sx * (hx - 8), -hy + 8, H + 16), (sx * (hx - 8), hy - 8, H + 16)], 6, nseg=6)
    # grow light hanging inside
    rbox(X.mesh(M_['black']), (-120, -200, H - 80), (120, 200, H - 60), r=4, k=1)
    pic(X.mesh(M_['grow']), (0, 0, H - 80.6), (0, 0, -1), 220, 380, up=(1, 0, 0))
    for sx in (-1, 1):
        tube(X.mesh(M_['steel']), [(sx * 100, 0, H - 60), (sx * 100, 0, H)], 2, nseg=4)
    ML.save('grow_tent', X)
    coll('grow_tent', [((a[0] - cx, a[1] - cy, a[2]), (b[0] - cx, b[1] - cy, b[2])) for a, b in B])


FLOAT_R = 640


def floats():
    """pool floats circling the coffee table: a sprinkled donut ring, a rubber duck, a pizza-slice lilo and a
    flamingo-ish orange ring. One IQM (radius beyond the MD3 limit); geometry 76 below the mover origin so the
    origin brush stays out of the water."""
    X = ML.Model(); z = -76
    def place(mm, a):
        X.add_model(mm, rot_z(a), (FLOAT_R * math.cos(a), FLOAT_R * math.sin(a), z))
    D = ML.Model()                                     # donut ring
    revolve(D.mesh(M_['float_pink']), [(70 + 50 * math.cos(t), 18 + 30 * math.sin(t)) for t in np.linspace(-math.pi, math.pi, 13)],
            n=24, u_tiles=3)
    place(D, 0.0)
    Du = ML.Model()                                    # duck
    ellipsoid(Du.mesh(M_['float_yellow']), (0, 0, 40), 120, 90, 60, nu=16, nv=8, flat_bottom=-40)
    sphere(Du.mesh(M_['float_yellow']), (70, 0, 130), 55, nu=14, nv=8)
    ellipsoid(Du.mesh(M_['float_orange']), (130, 0, 125), 34, 22, 10, nu=10, nv=5)
    for s in (-1, 1): sphere(Du.mesh(M_['black']), (105, s * 26, 148), 8, nu=8, nv=4)
    place(Du, math.pi / 2)
    P = ML.Model()                                     # pizza-slice lilo
    mprism(P.mesh(M_['float_orange']), [(-160, -110), (-160, 110), (180, 0)], 0, 30, tile=200)
    for (x, y) in ((-60, -30), (-80, 50), (30, 10)):
        disc(P.mesh(M_['float_pink']), 26, 30.6, up=True, n=12, cx=x, cy=y)
    place(P, math.pi)
    O = ML.Model()
    revolve(O.mesh(M_['float_white']), [(60 + 40 * math.cos(t), 16 + 26 * math.sin(t)) for t in np.linspace(-math.pi, math.pi, 13)],
            n=24, u_tiles=3)
    place(O, 3 * math.pi / 2)
    tquad(X.mesh(M_['swirl']), [(-340, -340, -58), (340, -340, -58), (340, 340, -58), (-340, 340, -58)], (0, 0, 1), tile=680.0)
    ML.save_iqm('floats', X)


def lounger():
    """poolside sun lounger (origin footprint centre, head end +x)"""
    X = ML.Model()
    seat = ((-260, -90, 90), (160, 90, 120))
    rbox(X.mesh(M_['lounger']), *seat, r=10, k=2, tile=420)
    P = [(160, -90, 120), (160, 90, 120), (300, 90, 300), (300, -90, 300)]
    tube(X.mesh(M_['steel']), [(-250, -90, 0), (-250, -90, 90)], 8, nseg=6)
    tube(X.mesh(M_['steel']), [(-250, 90, 0), (-250, 90, 90)], 8, nseg=6)
    tube(X.mesh(M_['steel']), [(150, -90, 0), (150, -90, 90)], 8, nseg=6)
    tube(X.mesh(M_['steel']), [(150, 90, 0), (150, 90, 90)], 8, nseg=6)
    back = ML.Model()
    rbox(back.mesh(M_['lounger']), (0, -90, 0), (220, 90, 30), r=10, k=2, tile=420)
    a = math.radians(-50)
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    X.add_model(back, R, (160, 0, 100))
    ML.save('lounger', X)
    # collision = the seat slab and the raised backrest only: 90u clear underneath, so you can walk under it
    coll('lounger', [((-260, -90, 90), (160, 90, 120)), ((160, -90, 100), (232, 90, 200)), ((232, -90, 184), (300, 90, 290))])


def umbrella():
    """beach umbrella stuck in a bucket of sand (origin bucket base)"""
    X = ML.Model()
    revolve(X.mesh(M_['float_white']), [(70, 0), (84, 110), (78, 110), (66, 8), (0, 8)], n=20)
    disc(X.mesh(M_['woodh']), 76, 96, up=True, n=20)
    tube(X.mesh(M_['steel']), [(0, 0, 96), (0, 0, 820)], 8, nseg=8)
    prof = [(0.01, 840), (300, 760), (420, 700), (430, 690)]
    revolve(X.mesh(M_['umbrella']), prof, n=16, u_tiles=1)
    ML.save('umbrella', X)
    coll('umbrella', cyls=[(0, 0, 84, 0, 110)])


def towel():
    X = ML.Model()
    rbox(X.mesh(M_['towel']), (-180, -110, 0), (180, 110, 6), r=2, k=1, tile=360)
    ML.save('towel', X)
