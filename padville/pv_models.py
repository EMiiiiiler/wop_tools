"""Custom MD3/IQM models for wop_padville (Padville Junction). All art is original and generated here.

Two scales live in this map:
  * the MODEL WORLD (the layout): 48u per model metre - you are the size of a model-railway figure. Buildings, the
    train, trees and the mountain are life-size around you.
  * the GIANT WORLD (the hobbyist's workbench): 42u per real centimetre - a mug is 400u tall, a ruler is a bridge.

Car space for rolling stock: x forward, y left, z = 0 on the rail top (woplib.railway.Car).
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import Mesh, rbox, tube, revolve, disc, prism, ellipsoid, rot_z, rot_axis, sphere

TX = None          # woplib.texlib.Textures, set by setup()
COLL = {}          # model name -> dict(boxes=[(mn, mx)], cyls=[(cx, cy, r, z0, z1)]) in model space


def setup(tx):
    global TX
    TX = tx


def C(c): return np.array(c, np.float32)


def _img(w, h, bg):
    return Image.new('RGB', (w, h), tuple(int(v) for v in bg))


def _arr(im): return np.asarray(im, np.float32)


def font(sz, serif=False): return ML.font(sz, serif)


# ================================================================================================ textures (model)
def mats():
    """every model material, registered once before any model is built"""
    M = TX.material
    M('loco_side', loco_side_tex(), 'dyn')
    M('loco_end', loco_end_tex(), 'dyn')
    M('coach_side', coach_side_tex((126, 34, 40), (232, 214, 170), 'PADVILLE PULLMAN'), 'dyn')
    M('coach_side2', coach_side_tex((40, 70, 120), (220, 220, 214), 'FIRST CLASS'), 'dyn')
    M('coach_end', TL.solid((70, 40, 36), 4, 3, 128), 'dyn')
    M('roof_grey', TL.grime(TL.solid((92, 94, 98), 5, 5, 128), 0.25, 3), 'dyn')
    M('bogie', TL.grime(TL.metal((52, 50, 48), True, 7), 0.4, 9), 'dyn')
    M('wheel', wheel_tex(), 'dyn')
    M('buffer', TL.metal((150, 150, 156), False, 11), 'dyn')
    M('tr_dark', TL.solid((40, 42, 44), 4, 12, 128), 'dyn')
    M('headlamp', TL.solid((255, 250, 210), 2, 13, 64), 'glow')
    M('warn_yellow', TL.solid((236, 196, 32), 4, 15, 128), shade=30)
    # railway scenery
    M('rail', TL.metal((120, 104, 92), True, 17), 'lms', shade=40, v=0.12)
    M('sleeper', TL.grime(TL.planks((92, 70, 52), 2, (50, 38, 28), 6, False, False, 19), 0.3, 21), shade=40)
    M('stone_m', TL.stone((168, 156, 136), 30, (110, 100, 88), seed=23), shade=35)
    M('stone_dark', TL.stone((112, 104, 96), 22, (70, 64, 60), seed=25), shade=35)
    M('iron_green', TL.grime(TL.solid((46, 92, 62), 4, 27, 128), 0.2, 29), shade=35)
    M('iron_dark', TL.solid((40, 42, 44), 4, 31, 128), shade=35)
    M('cream', TL.solid((232, 220, 186), 4, 33, 128), shade=35)
    M('timber', TL.planks((140, 98, 60), 4, (80, 54, 32), 8, False, True, 35), shade=35)
    M('timber_dark', TL.planks((96, 64, 40), 4, (56, 36, 22), 8, False, True, 37), shade=35)
    M('water_m', TL.solid((80, 150, 180), 6, 39, 128), 'add', tcmod='scroll 0.05 0.12')
    M('leaf', leaf_tex(), 'alpha', alpha=leaf_alpha())
    M('pine_bark', TL.grime(TL.stripes((92, 64, 44), (70, 48, 34), 12, True, 0.4, 41), 0.2, 43), shade=60)
    M('sail_cloth', TL.solid((236, 230, 214), 3, 45, 128), 'dyn', two=True)
    M('sail_wood', TL.planks((120, 84, 52), 3, (70, 48, 30), 6, False, True, 47), 'dyn')
    M('wheel_wood', TL.planks((110, 80, 52), 3, (64, 44, 28), 6, False, True, 49), 'dyn')
    M('deck_dyn', TL.planks((126, 96, 66), 8, (62, 44, 30), 8, False, True, 51), 'dyn')
    M('rail_dyn', TL.metal((120, 104, 92), True, 53), 'dyn')
    M('sign_station', TL.label('PADVILLE JUNCTION', 1024, 128, (24, 52, 110), (250, 250, 250), border=(250, 250, 250)), shade=30)
    M('fountain_water', TL.solid((120, 190, 220), 6, 55, 128), 'add', tcmod='scroll 0 -0.6')
    M('xing_light', TL.solid((255, 40, 30), 2, 57, 64), 'glow', wave='square 0 1 0 1')
    M('xing_board', xing_tex(), shade=30)
    # giant workbench things
    M('mug', mug_tex(), shade=60)
    M('mug_in', TL.solid((246, 244, 238), 3, 59, 128), shade=60)
    M('lamp_red', TL.solid((196, 36, 30), 3, 61, 128), 'lms', shade=60, v=0.18)
    M('lamp_steel', TL.metal((176, 178, 184), True, 63), 'lms', shade=50, v=0.3)
    M('lamp_glow', TL.solid((255, 246, 214), 2, 65, 64), 'glow')
    M('ctrl_body', controller_tex(), shade=30)
    M('ctrl_black', TL.solid((30, 30, 34), 4, 67, 128), shade=40)
    M('knob', TL.solid((180, 34, 30), 3, 69, 128), 'lms', shade=60, v=0.2)
    M('led_green', TL.solid((60, 255, 90), 2, 71, 64), 'glow', wave='sin 0.7 0.3 0 0.5')
    M('screw_handle', TL.solid((240, 190, 30), 4, 73, 128), 'lms', shade=60, v=0.2)
    M('steel', TL.metal((190, 192, 198), True, 75), 'lms', shade=60, v=0.35)
    M('glue_tube', glue_tex(), shade=60)
    M('battery', battery_tex(), shade=30)
    M('battery_top', TL.metal((176, 176, 180), False, 77), 'lms', shade=30, v=0.2)
    M('cable_red', TL.solid((190, 40, 36), 3, 79, 64), shade=70)
    M('cable_black', TL.solid((34, 34, 36), 3, 81, 64), shade=70)
    M('cable_yellow', TL.solid((220, 190, 40), 3, 83, 64), shade=70)
    M('motor', TL.grime(TL.solid((40, 70, 46), 4, 85, 128), 0.3, 87), shade=30)
    M('copper', TL.metal((196, 120, 70), True, 89), 'lms', shade=40, v=0.2)
    M('locobox', locobox_tex(), shade=30)
    M('sprue', TL.solid((150, 150, 156), 4, 91, 128), shade=40)
    M('hatchlid', TL.grime(TL.solid((92, 140, 62), 6, 93, 128), 0.2, 95), shade=30)
    M('plywood_m', TL.planks((190, 160, 120), 3, (150, 120, 86), 14, False, False, 97), shade=30)
    M('pliers_grip', TL.solid((40, 90, 190), 4, 99, 128), shade=50)
    M('bulb', TL.solid((255, 240, 200), 2, 101, 64), 'glow')
    M('web', web_tex(), 'alpha', alpha=web_alpha())
    M('bench_wood', TL.planks((150, 110, 70), 4, (90, 60, 36), 8, False, False, 103), shade=30)
    M('sandstone', TL.stone((196, 176, 140), 20, (150, 132, 100), seed=105), shade=30)


# ---- texture painters (original procedural art)
def loco_side_tex(w=1024, h=256):
    im = _img(w, h, (34, 110, 62)); d = ImageDraw.Draw(im)
    d.rectangle((0, int(h * 0.72), w, int(h * 0.8)), fill=(236, 196, 32))            # yellow lining band
    d.rectangle((0, int(h * 0.86), w, h), fill=(30, 34, 32))                         # solebar
    for x0 in (40, w - 200):                                                       # cab windows + doors
        d.rounded_rectangle((x0, 30, x0 + 150, 110), 10, fill=(30, 40, 50), outline=(220, 220, 220), width=4)
        d.rectangle((x0 + 30, 120, x0 + 120, int(h * 0.7)), outline=(20, 70, 40), width=4)
    for k in range(6):                                                             # engine-room grilles
        x = 260 + k * 85
        for j in range(8): d.line((x, 40 + j * 10, x + 60, 40 + j * 10), fill=(22, 80, 44), width=3)
    d.text((w // 2, int(h * 0.62)), 'PADVILLE FLYER  D7001', font=font(26), fill=(240, 220, 120), anchor='mm')
    return _arr(im)


def loco_end_tex(n=256):
    im = _img(n, n, (236, 196, 32)); d = ImageDraw.Draw(im)
    d.polygon([(30, 20), (226, 20), (210, 110), (46, 110)], fill=(30, 40, 50), outline=(40, 40, 40))
    d.line((128, 20, 128, 110), fill=(230, 230, 230), width=6)
    for x in (52, 204): d.ellipse((x - 14, 160, x + 14, 188), fill=(255, 250, 210), outline=(60, 60, 60), width=3)
    d.rectangle((96, 170, 160, 200), fill=(30, 30, 30))
    return _arr(im)


def coach_side_tex(body, panel, word, w=1024, h=256):
    im = _img(w, h, body); d = ImageDraw.Draw(im)
    d.rectangle((0, 18, w, 150), fill=panel)                                       # window panel
    for k in range(9):
        x = 30 + k * 110
        d.rounded_rectangle((x, 34, x + 84, 132), 12, fill=(255, 226, 150), outline=(80, 60, 40), width=4)
        d.line((x + 42, 34, x + 42, 132), fill=(80, 60, 40), width=3)
    d.rectangle((0, 160, w, 168), fill=(214, 180, 90))
    d.text((w // 2, 196), word, font=font(30, True), fill=(240, 214, 130), anchor='mm')
    d.rectangle((0, int(h * 0.88), w, h), fill=(30, 30, 30))
    return _arr(im)


def wheel_tex(n=128):
    x, y = ML.xy(n); r = np.hypot(x - 0.5, y - 0.5)
    c = np.zeros((n, n, 3), np.float32) + C((50, 48, 46))
    c = np.where((r > 0.42)[..., None], C((170, 170, 176)), c)
    c = np.where((r < 0.12)[..., None], C((120, 30, 30)), c)
    return c


def leaf_tex(n=256):
    x, y = ML.xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((40, 92, 52))
    return c + ML.N3(n, 2, 107, 22)


def leaf_alpha(n=256):
    a = ML.noise(n, 3, 109)
    return np.where(a > -0.35, 255, 0).astype(np.uint8)


def web_tex(n=128): return np.zeros((n, n, 3), np.float32) + C((230, 230, 236))


def web_alpha(n=128):
    x, y = ML.xy(n); dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    spokes = np.abs(np.sin(a * 6)) < 0.04
    rings = np.abs(np.sin(r * 60)) < 0.08
    return np.where((spokes | rings) & (r < 0.5), 255, 0).astype(np.uint8)


def xing_tex(n=256):
    im = _img(n, n, (250, 250, 250)); d = ImageDraw.Draw(im)
    d.line((20, 20, n - 20, n - 20), fill=(200, 30, 30), width=40); d.line((n - 20, 20, 20, n - 20), fill=(200, 30, 30), width=40)
    return _arr(im)


def mug_tex(w=1024, h=512):
    im = _img(w, h, (246, 244, 238)); d = ImageDraw.Draw(im)
    d.rectangle((0, 40, w, 70), fill=(30, 110, 200)); d.rectangle((0, h - 70, w, h - 40), fill=(30, 110, 200))
    d.text((w * 0.25, h / 2), "WORLD'S BEST", font=font(54), fill=(30, 110, 200), anchor='mm')
    d.text((w * 0.25, h / 2 + 70), "MODELLER", font=font(64), fill=(220, 60, 40), anchor='mm')
    for k in range(5):                                                             # little steam engines
        x = w * 0.62 + k * 70
        d.rounded_rectangle((x, h / 2 - 20, x + 50, h / 2 + 20), 6, fill=(40, 40, 40))
        d.ellipse((x + 4, h / 2 + 14, x + 20, h / 2 + 30), fill=(200, 40, 40)); d.ellipse((x + 30, h / 2 + 14, x + 46, h / 2 + 30), fill=(200, 40, 40))
    return _arr(im)


def controller_tex(w=512, h=512):
    im = _img(w, h, (36, 36, 40)); d = ImageDraw.Draw(im)
    d.rectangle((20, 20, w - 20, 120), fill=(200, 196, 180))
    d.text((w / 2, 70), 'PADMATIC 2000 CONTROLLER', font=font(28), fill=(30, 30, 30), anchor='mm')
    for k in range(4):
        d.text((90 + k * 110, 200), ('A', 'B', 'C', 'D')[k], font=font(40), fill=(230, 230, 230), anchor='mm')
        d.rectangle((60 + k * 110, 240, 120 + k * 110, 300), outline=(230, 230, 230), width=4)
    d.text((w / 2, 420), '12V DC  -  16V AC', font=font(30), fill=(230, 200, 60), anchor='mm')
    return _arr(im)


def glue_tex(w=512, h=256):
    im = _img(w, h, (236, 236, 230)); d = ImageDraw.Draw(im)
    d.rectangle((0, 60, w, 196), fill=(230, 40, 40))
    d.text((w / 2, 128), 'POLY-CEMENT', font=font(48), fill=(250, 250, 250), anchor='mm')
    return _arr(im)


def battery_tex(w=512, h=256):
    im = _img(w, h, (30, 30, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w * 0.4, h), fill=(230, 120, 30))
    d.text((w * 0.7, h / 2), '9V', font=font(110), fill=(240, 240, 240), anchor='mm')
    d.text((w * 0.2, h / 2), 'PADCELL', font=font(36), fill=(30, 30, 30), anchor='mm')
    return _arr(im)


def locobox_tex(w=1024, h=256):
    im = _img(w, h, (240, 236, 222)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 50), fill=(200, 30, 36)); d.rectangle((0, h - 30, w, h), fill=(200, 30, 36))
    d.text((40, 25), 'PADMAN MODELS', font=font(30), fill=(250, 250, 250), anchor='lm')
    d.rounded_rectangle((300, 70, 980, 210), 10, fill=(170, 200, 214), outline=(90, 90, 90), width=4)
    d.text((150, 140), 'H0 1:87', font=font(40), fill=(30, 30, 30), anchor='mm')
    return _arr(im)


# ================================================================================================ rolling stock
def _car_body(X, L, W, z0, z1, roof_h, side, end, roof, nose=0.0, end_sh=None):
    """box body with a curved roof; side texture fitted to each side, `nose` = slope of the end faces (loco cabs)"""
    hw = W / 2; hl = L / 2
    # sides (fitted texture: u along length, v down)
    for sgn in (1, -1):
        y = sgn * hw
        pts = [(-hl + nose, y, z1), (hl - nose, y, z1), (hl, y, z0), (-hl, y, z0)]
        if sgn < 0: pts = [pts[1], pts[0], pts[3], pts[2]]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)] if sgn > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)]
        X.mesh(side).poly([np.array(p, float) for p in pts], (0, sgn, 0), uv)
    # ends (sloped by nose)
    for sgn in (1, -1):
        xe0, xe1 = sgn * hl, sgn * (hl - nose)
        pts = [(xe0, -hw, z0), (xe0, hw, z0), (xe1, hw, z1), (xe1, -hw, z1)]
        nrm = np.array([sgn * (z1 - z0), 0, nose], float); nrm /= np.linalg.norm(nrm)
        if sgn < 0: pts = [pts[1], pts[0], pts[3], pts[2]]
        uv = [(0, 1), (1, 1), (1, 0), (0, 0)] if sgn > 0 else [(1, 1), (0, 1), (0, 0), (1, 0)]
        X.mesh(end_sh or end).poly([np.array(p, float) for p in pts], nrm, uv)
    # curved roof (grid along x)
    nseg = 8
    xs = [-hl + nose, hl - nose]
    P = np.zeros((2, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, nseg + 1, 2))
    for j in range(nseg + 1):
        a = math.pi * j / nseg
        yy = hw * math.cos(a); zz = z1 + roof_h * math.sin(a)
        for i, xx in enumerate(xs):
            P[i, j] = (xx, yy, zz); N[i, j] = (0, math.cos(a), math.sin(a)); UV[i, j] = (xx / 128, j / nseg)
    X.mesh(roof).grid(P, N, UV)
    for i, sgn in ((0, -1), (1, 1)):                                    # roof end caps
        pts = [P[i, j] for j in range(nseg + 1)]
        X.mesh(roof).poly(pts if sgn > 0 else pts[::-1], (sgn, 0, 0), [(p[1] / 128, p[2] / 128) for p in (pts if sgn > 0 else pts[::-1])])


def _bogie(X, xc, gauge=69.0):
    rbox(X.mesh(TX['bogie']), (xc - 70, -46, 14), (xc + 70, 46, 46), r=4, k=1, tile=64)
    for dx in (-44, 44):
        for sg in (1, -1):
            y = sg * gauge / 2
            path = [(xc + dx, y - 5 * sg, 22), (xc + dx, y + 5 * sg, 22)]
            tube(X.mesh(TX['wheel']), path, 22, nseg=14, caps=(True, True))


def _buffers(X, x, sgn):
    for y in (-44, 44):
        tube(X.mesh(TX['buffer']), [(x, y, 56), (x + sgn * 26, y, 56)], 9, nseg=10)
    rbox(X.mesh(TX['tr_dark']), (min(x, x + sgn * 6), -66, 42), (max(x, x + sgn * 6), 66, 70), r=2, k=1, tile=32)


def loco():
    X = ML.Model()
    L, W = 600.0, 140.0
    _car_body(X, L, W, 52, 168, 26, TX['loco_side'], TX['loco_end'], TX['roof_grey'], nose=22)
    rbox(X.mesh(TX['tr_dark']), (-L / 2 + 10, -64, 40), (L / 2 - 10, 64, 52), r=2, k=1, tile=64)      # underframe
    rbox(X.mesh(TX['tr_dark']), (-120, -50, 26), (120, 50, 42), r=4, k=1, tile=64)                    # fuel tank
    for xc in (-200, 200): _bogie(X, xc)
    for sgn in (1, -1): _buffers(X, sgn * L / 2, sgn)
    for xx in (-90, 0, 90):                                                                               # roof fans
        revolve(X.mesh(TX['tr_dark']), [(30, 190), (30, 197), (0, 197)], n=16, cx=xx)
    for sgn in (1, -1):                                                                                   # headlamps
        for y in (-40, 40):
            tube(X.mesh(TX['headlamp']), [(sgn * L / 2, y, 80), (sgn * (L / 2 + 3), y, 80)], 7, nseg=10)
    ML.save('loco', X)
    return X


def coach(side_key):
    X = ML.Model()
    L, W = 580.0, 140.0
    _car_body(X, L, W, 52, 172, 24, TX[side_key], TX['coach_end'], TX['roof_grey'])
    rbox(X.mesh(TX['tr_dark']), (-L / 2 + 10, -62, 40), (L / 2 - 10, 62, 52), r=2, k=1, tile=64)
    for xc in (-200, 200): _bogie(X, xc)
    for sgn in (1, -1): _buffers(X, sgn * L / 2, sgn)
    for xx in np.linspace(-220, 220, 5):                                                                  # roof vents
        revolve(X.mesh(TX['tr_dark']), [(10, 192), (12, 202), (0, 204)], n=10, cx=float(xx))
    ML.save(f'coach_{side_key}', X)
    return X


def parked_loco():
    """the same loco body standing in the engine shed (static MD3)"""
    return loco()


# ================================================================================================ railway scenery
def tunnel_portal(half, h_open, depth=24.0, frame=64.0, top_z=None):
    """stone facade round the bore, in the plane x = 0..depth (local +x = out of the hill). Opening y -half..half,
    z 0..h_open. Pilasters, a lintel with voussoir blocks drawn on, a cornice; nothing inside the opening."""
    X = ML.Model()
    st, dk = TX['stone_m'], TX['stone_dark']
    top = top_z if top_z is not None else h_open + frame + 40
    for sg in (1, -1):
        y0, y1 = (half, half + frame) if sg > 0 else (-half - frame, -half)
        rbox(X.mesh(st), (0.5, y0, 0), (depth, y1, top - 24), r=3, k=1, tile=96)
    n = 11
    for k in range(n):                                                         # voussoir blocks over the opening
        ya = -half + 2 * half * k / n; yb = -half + 2 * half * (k + 1) / n
        rbox(X.mesh(st if k % 2 else dk), (0.5, ya, h_open), (depth + 4, yb, top - 24), r=2, k=1, tile=96)
    rbox(X.mesh(dk), (0.5, -half - frame - 10, top - 24), (depth + 10, half + frame + 10, top), r=3, k=1, tile=96)
    ML.save('tunnel_portal', X)
    COLL['tunnel_portal'] = dict(boxes=[((0.5, half, 0), (depth, half + frame, top - 24)),
                                        ((0.5, -half - frame, 0), (depth, -half, top - 24)),
                                        ((0.5, -half, h_open), (depth, half, top))])
    return X


def canopy(L, D, h, posts_every=240.0):
    """platform canopy: green iron posts with brackets, a ridged roof slab drawn as an MD3 (the walkable slab is a
    brush laid by the caller at z h..h+12). local x along the platform, y 0 (building wall) .. D (platform edge)."""
    X = ML.Model()
    g, cr = TX['iron_green'], TX['cream']
    n = max(1, int(L / posts_every))
    for k in range(n + 1):
        x = -L / 2 + L * k / n
        tube(X.mesh(g), [(x, D - 30, 0), (x, D - 30, h)], 7, nseg=10)
        tube(X.mesh(g), [(x, D - 30, h - 70), (x, D - 90, h - 2)], 4, nseg=8)
        tube(X.mesh(g), [(x, D - 30, h - 70), (x, D - 2, h - 20)], 4, nseg=8)
    # valance (fretted edge)
    for k in range(int(L / 24)):
        x0 = -L / 2 + k * 24
        X.mesh(cr).poly([np.array(p, float) for p in ((x0, D + 0.5, h), (x0 + 24, D + 0.5, h), (x0 + 12, D + 0.5, h - 22))],
                        (0, 1, 0), [(0, 0), (1, 0), (0.5, 1)])
    ML.save('canopy', X)
    return X


def turntable_deck(r, thick=16):
    """rotating deck MD3 drawn round the entity origin (z 0 = mid-thickness): planks, two rails, rail guard, a
    little operator hut at one end. Nothing pokes out of the disc."""
    X = ML.Model()
    disc(X.mesh(TX['deck_dyn']), r, thick / 2, up=True, n=32, uvscale=128)
    revolve(X.mesh(TX['deck_dyn']), [(r, -thick / 2), (r, thick / 2)], n=32, u_tiles=16)
    for y in (-34.5, 34.5):
        rbox(X.mesh(TX['rail_dyn']), (-r + 10, y - 4, thick / 2), (r - 10, y + 4, thick / 2 + 10), r=1, k=1, tile=64)
    for x in (-r + 40, r - 40):
        rbox(X.mesh(TX['rail_dyn']), (x - 8, -70, thick / 2), (x + 8, 70, thick / 2 + 40), r=2, k=1, tile=64)
    ML.save('tt_deck', X)
    return X


def buffer_stop():
    X = ML.Model()
    for y in (-34, 34):
        tube(X.mesh(TX['iron_dark']), [(0, y, 0), (-50, y, 70)], 6, nseg=8)
        tube(X.mesh(TX['iron_dark']), [(-60, y, 0), (-50, y, 70)], 6, nseg=8)
    rbox(X.mesh(TX['warn_yellow']), (-58, -70, 56), (-42, 70, 86), r=3, k=1, tile=64)
    for y in (-44, 44): tube(X.mesh(TX['buffer']), [(-42, y, 70), (-20, y, 70)], 9, nseg=10)
    ML.save('buffer_stop', X)
    COLL['buffer_stop'] = dict(boxes=[((-62, -72, 0), (-18, 72, 88))])
    return X


def xing_post():
    X = ML.Model()
    tube(X.mesh(TX['iron_dark']), [(0, 0, 0), (0, 0, 200)], 6, nseg=10)
    rbox(X.mesh(TX['xing_board']), (-2, -40, 150), (2, 40, 200), r=1, k=1, tile=80)
    rbox(X.mesh(TX['iron_dark']), (-6, -36, 100), (6, 36, 124), r=2, k=1, tile=32)
    for y in (-24, 24): tube(X.mesh(TX['xing_light']), [(6, y, 112), (10, y, 112)], 9, nseg=10)
    ML.save('xing_post', X)
    COLL['xing_post'] = dict(cyls=[(0, 0, 10, 0, 200)])
    return X


def platform_bench():
    X = ML.Model()
    w = TX['timber']; ir = TX['iron_green']
    rbox(X.mesh(w), (-60, -14, 22), (60, 14, 26), r=1, k=1, tile=64)
    rbox(X.mesh(w), (-60, 10, 30), (60, 14, 52), r=1, k=1, tile=64)
    for x in (-50, 50):
        rbox(X.mesh(ir), (x - 3, -14, 0), (x + 3, 14, 26), r=1, k=1, tile=32)
        rbox(X.mesh(ir), (x - 3, 10, 26), (x + 3, 14, 52), r=1, k=1, tile=32)
    ML.save('pbench', X)
    COLL['pbench'] = dict(boxes=[((-60, -14, 0), (60, 14, 28))])
    return X


def fountain():
    X = ML.Model()
    st = TX['sandstone']
    revolve(X.mesh(st), [(150, 0), (150, 40), (138, 48), (124, 48), (124, 14)], u_tiles=8, n=40)
    revolve(X.mesh(st), [(26, 14), (26, 110), (60, 124), (60, 132), (0, 134)], u_tiles=3, n=24)
    revolve(X.mesh(st), [(10, 134), (10, 190), (30, 200), (0, 204)], u_tiles=2, n=16)
    disc(X.mesh(TX['fountain_water']), 124, 34, up=True, n=40)
    tube(X.mesh(TX['fountain_water']), [(0, 0, 204), (0, 0, 236)], 6, nseg=8)
    ML.save('fountain', X)
    COLL['fountain'] = dict(cyls=[(0, 0, 150, 0, 48), (0, 0, 30, 48, 200)])
    return X


def waterwheel(R=140, W=44):
    """rotates round local x (func_rotating axis x): spokes + paddles in the y-z plane, model origin = hub"""
    X = ML.Model()
    wd = TX['wheel_wood']
    for xs in (-W / 2, W / 2):
        pts = [(xs, R * math.cos(a), R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 33)]
        tube(X.mesh(wd), pts, 5, nseg=6, caps=(False, False))
        for k in range(8):
            a = 2 * math.pi * k / 8
            tube(X.mesh(wd), [(xs, 0, 0), (xs, R * math.cos(a), R * math.sin(a))], 4, nseg=6)
    for k in range(16):
        a = 2 * math.pi * k / 16
        c, s = math.cos(a), math.sin(a)
        M = Mesh(); rbox(M, (-W / 2, R - 46, -6), (W / 2, R, 6), r=1, k=1, tile=64)
        X.mesh(wd).add(M, np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), (0, 0, 0))
    tube(X.mesh(TX['tr_dark']), [(-W / 2 - 30, 0, 0), (W / 2 + 4, 0, 0)], 10, nseg=10)
    ML.save('waterwheel', X)
    return X


def windmill_sails(R=300):
    """sails in the y-z plane (rotates round x), origin = hub"""
    X = ML.Model()
    for k in range(4):
        a = math.pi / 2 * k + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        Rm = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        M = Mesh(); rbox(M, (-6, -6, 0), (6, 6, R), r=1, k=1, tile=64)
        X.mesh(TX['sail_wood']).add(M, Rm)
        S = Mesh(); S.poly([np.array(p, float) for p in ((-2, 8, 70), (-2, 70, 70), (-2, 70, R - 10), (-2, 8, R - 10))], (-1, 0, 0),
                           [(0, 0), (1, 0), (1, 1), (0, 1)])
        X.mesh(TX['sail_cloth']).add(S, Rm)
    revolve(X.mesh(TX['sail_wood']), [(0, -30), (24, -30), (24, 10), (0, 18)], n=12)
    ML.save('windmill_sails', X)
    return X


def windmill_tower(h=520, r0=120, r1=80):
    X = ML.Model()
    revolve(X.mesh(TX['cream']), [(r0, 0), (r1, h)], n=24, u_tiles=4)
    revolve(X.mesh(TX['timber_dark']), [(r1 + 14, h), (r1 + 14, h + 10), (r1 * 0.6, h + 90), (0, h + 104)], n=24, u_tiles=4)
    ML.save('windmill_tower', X)
    COLL['windmill_tower'] = dict(cyls=[(0, 0, r0 - 8, 0, h * 0.5), (0, 0, (r0 + r1) / 2 - 12, h * 0.5, h)])
    return X


def pine(h=420, r=120, seed=1):
    rng = np.random.default_rng(seed)
    X = ML.Model()
    tube(X.mesh(TX['pine_bark']), [(0, 0, 0), (0, 0, h * 0.95)], [14, 6], nseg=8)
    tiers = 5
    for k in range(tiers):
        z0 = h * (0.18 + 0.15 * k); rr = r * (1 - k / (tiers + 0.6))
        prof = [(rr, z0), (rr * 0.25, z0 + h * 0.24), (0, z0 + h * 0.26)]
        revolve(X.mesh(TX['leaf']), prof, n=10, u_tiles=3, rfun=lambda a, r_, z_, j=rng.uniform(0, 6): r_ * (0.85 + 0.15 * math.sin(a * 5 + j)))
    ML.save(f'pine{seed}', X)
    COLL[f'pine{seed}'] = dict(cyls=[(0, 0, 18, 0, h * 0.5)])
    return X


def hatch_lid(w=224, h=224, t=12):
    """the lifted-out access panel, leaning (local: lies in the x-z plane leaning back toward +y)"""
    X = ML.Model()
    M = Mesh(); rbox(M, (-w / 2, 0, 0), (w / 2, t, h), r=2, k=1, tile=128)
    a = math.radians(-14)
    Rm = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    X.mesh(TX['hatchlid']).add(M, Rm, (0, 0, 0))
    ML.save('hatchlid', X)
    COLL['hatchlid'] = dict(boxes=[((-w / 2, 0, 0), (w / 2, 64, 120))])
    return X


# ================================================================================================ giant workbench objects
def mug_lying(R=170.0, L=400.0, t=14.0, n=24):
    """a tipped-over mug, axis along local y, open end at y = 0, base at y = L. Outer surface printed, inside white.
    Lies on z = 0 (axis at z = R). Collision: a ring of slab hulls (built by the caller from mug_slabs())."""
    X = ML.Model()
    ang = np.linspace(0, 2 * math.pi, n * 2 + 1)
    for (rr, sh, sgn) in ((R, TX['mug'], 1), (R - t, TX['mug_in'], -1)):
        P = np.zeros((2, len(ang), 3)); N = np.zeros_like(P); UV = np.zeros((2, len(ang), 2))
        for j, a in enumerate(ang):
            for i, yy in enumerate((0.0, L)):
                P[i, j] = (rr * math.cos(a), yy, R + rr * math.sin(a)); N[i, j] = (sgn * math.cos(a), 0, sgn * math.sin(a))
                UV[i, j] = (j / (len(ang) - 1), 1 - i)
        X.mesh(sh).grid(P, N, UV)
    # rim
    pts = []
    for k in range(len(ang) - 1):
        a0, a1 = ang[k], ang[k + 1]
        q = [np.array([rr * math.cos(a), 0, R + rr * math.sin(a)]) for rr, a in ((R - t, a0), (R, a0), (R, a1), (R - t, a1))]
        X.mesh(TX['mug_in']).poly(q, (0, -1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    # base (outside + inside)
    disc_pts = [np.array([R * math.cos(a), L, R + R * math.sin(a)]) for a in ang[:-1]]
    X.mesh(TX['mug']).poly(disc_pts[::-1], (0, 1, 0), [(0.5, 0.5)] * len(disc_pts))
    disc_in = [np.array([(R - t) * math.cos(a), L - t, R + (R - t) * math.sin(a)]) for a in ang[:-1]]
    X.mesh(TX['mug_in']).poly(disc_in, (0, -1, 0), [(0.5, 0.5)] * len(disc_in))
    # handle (on top, in the x = 0 plane)
    hp = [(0, L * 0.2 + L * 0.6 * (0.5 - 0.5 * math.cos(a)), 2 * R + 6 + 120 * math.sin(a)) for a in np.linspace(0, math.pi, 13)]
    tube(X.mesh(TX['mug']), hp, 24, nseg=12, caps=(False, False))
    ML.save('mug', X)
    return X


def mug_slabs(R=170.0, L=400.0, t=14.0, n=24):
    """convex hull point sets (model space) of the mug wall segments + base, for weapclip"""
    out = []
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        pts = []
        for a in (a0, a1):
            for rr in (R - t - 2, R - 2):
                for yy in (2.0, L - t):
                    pts.append((rr * math.cos(a), yy, R + rr * math.sin(a)))
        out.append(pts)
    base = []
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        for yy in (L - t, L - 2):
            base.append(((R - 4) * math.cos(a), yy, R + (R - 4) * math.sin(a)))
    out.append(base)
    return out


def desk_lamp(base_c, head_c, head_top, base_r=210.0):
    """anglepoise-style lamp from a weighted base up two arms to a cone shade whose flat top you stand on.
    Model space: origin at the base centre on the bench. head_c = (dx, dy) of the shade centre, head_top = z of its
    flat top. Returns (Model, shade radius)."""
    X = ML.Model()
    red, st = TX['lamp_red'], TX['lamp_steel']
    revolve(X.mesh(red), [(base_r, 0), (base_r, 36), (base_r - 30, 60), (40, 70), (0, 72)], n=32, u_tiles=4)
    hx, hy = head_c
    elbow = np.array([hx * 0.15, hy * 0.15, head_top + 420])
    p0 = np.array([0, 0, 70.0])
    shade_top = np.array([hx, hy, head_top])
    joint = shade_top + np.array([0, 0, 40.0])
    for off in (-18, 18):
        d = np.array([0, off, 0]) if abs(hy) < abs(hx) else np.array([off, 0, 0])
        tube(X.mesh(st), [p0 + d, elbow + d], 9, nseg=8)
        tube(X.mesh(st), [elbow + d, joint + d], 9, nseg=8)
    for p in (elbow, joint):
        ML_sphere(X.mesh(red), p, 26)
    # springs
    for off in (-34, 34):
        d = np.array([0, off, 0]) if abs(hy) < abs(hx) else np.array([off, 0, 0])
        tube(X.mesh(st), [p0 + d + np.array([0, 0, 40]), (p0 + elbow) / 2 + d], 4, nseg=6)
    rs = 130.0
    # shade: flat top disc r rs, cone down to r 230 over 200
    revolve(X.mesh(red), [(rs, head_top), (rs + 10, head_top - 30), (230, head_top - 210), (236, head_top - 216)],
            n=32, u_tiles=4, cx=hx, cy=hy)
    revolve(X.mesh(TX['lamp_steel']), [(226, head_top - 212), (rs - 6, head_top - 26)], n=32, u_tiles=4, cx=hx, cy=hy)
    disc(X.mesh(red), rs, head_top, up=True, n=32, cx=hx, cy=hy)
    ML_sphere(X.mesh(TX['lamp_glow']), np.array([hx, hy, head_top - 120]), 60)
    return X, rs


def ML_sphere(M, c, r):
    from meshlib import sphere
    sphere(M, tuple(c), r, nu=12, nv=8)


def controller(w=600.0, d=400.0, h=300.0):
    """train controller box: body with printed top, big speed knob, toggles, LED. origin = base centre"""
    X = ML.Model()
    rbox(X.mesh(TX['ctrl_black']), (-w / 2, -d / 2, 0), (w / 2, d / 2, h), r=18, k=3, tile=128, faces='nsewb')
    X.mesh(TX['ctrl_body']).poly([np.array(p, float) for p in ((-w / 2 + 18, -d / 2 + 18, h), (w / 2 - 18, -d / 2 + 18, h),
                                                               (w / 2 - 18, d / 2 - 18, h), (-w / 2 + 18, d / 2 - 18, h))],
                                 (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(TX['ctrl_black']), (-w / 2 + 18, -d / 2 + 18, h - 18), (w / 2 - 18, d / 2 - 18, h - 1), r=4, k=1, tile=128, faces='nsew')
    # knob
    kx, ky = w * 0.2, -d * 0.08
    revolve(X.mesh(TX['knob']), [(96, h), (96, h + 60), (80, h + 76), (0, h + 80)], n=24, cx=kx, cy=ky)
    rbox(X.mesh(TX['steel']), (kx - 8, ky, h + 80), (kx + 8, ky + 80, h + 86), r=1, k=1, tile=32)
    for k in range(3):                                                                    # toggle switches
        x = -w * 0.32 + k * 60
        tube(X.mesh(TX['steel']), [(x, d * 0.2, h), (x + 8, d * 0.2, h + 50)], 6, nseg=8)
    tube(X.mesh(TX['led_green']), [(-w * 0.32, -d * 0.25, h), (-w * 0.32, -d * 0.25, h + 8)], 12, nseg=10)
    ML.save('controller', X)
    COLL['controller'] = dict(boxes=[((-w / 2 + 2, -d / 2 + 2, 0), (w / 2 - 2, d / 2 - 2, h))], cyls=[(kx, ky, 90, h, h + 76)])
    return X


def screwdriver(L1=420.0, L2=440.0, r1=63.0, r2=14.0):
    """lies along local x on z = 0: fluted handle x 0..L1, steel shaft L1..L1+L2"""
    X = ML.Model()
    path = [(0, 0, r1), (L1, 0, r1)]
    tube(X.mesh(TX['screw_handle']), path, r1, nseg=12, caps=(True, False))
    tube(X.mesh(TX['steel']), [(L1, 0, r1), (L1 + L2, 0, r1)], r2, nseg=8, caps=(False, True))
    ML.save('screwdriver', X)
    COLL['screwdriver'] = dict(boxes=[((4, -r1 + 8, 0), (L1 - 4, r1 - 8, 2 * r1 - 6))])
    return X


def glue_tube(L=420.0, r=52.0):
    X = ML.Model()
    tube(X.mesh(TX['glue_tube']), [(0, 0, r), (L, 0, r)], [r, r], nseg=14, caps=(False, True))
    # crimped end
    rbox(X.mesh(TX['steel']), (-30, -r - 6, r - 8), (0, r + 6, r + 8), r=2, k=1, tile=32)
    revolve_x(X.mesh(TX['steel']), [(r * 0.5, L), (r * 0.25, L + 60), (8, L + 120), (0, L + 124)], r)
    ML.save('glue_tube', X)
    COLL['glue_tube'] = dict(boxes=[((0, -r + 6, 0), (L, r - 6, 2 * r - 6))])
    return X


def revolve_x(M, prof, zc):
    """profile [(radius, x)] revolved round the x axis at height zc"""
    tmp = Mesh(); revolve(tmp, [(r_, x_) for r_, x_ in prof], n=12)
    Rm = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)      # rotation (det +1): local z -> world x
    M.add(tmp, Rm, (0, 0, zc))


def battery9v(w=110.0, d=200.0, h=74.0):
    X = ML.Model()
    rbox(X.mesh(TX['battery']), (-d / 2, -w / 2, 0), (d / 2, w / 2, h), r=6, k=2, tile=200)
    for y in (-25, 25):
        tube(X.mesh(TX['battery_top']), [(d / 2, y, h * 0.5), (d / 2 + 18, y, h * 0.5)], 12, nseg=10)
    ML.save('battery9v', X)
    COLL['battery9v'] = dict(boxes=[((-d / 2 + 2, -w / 2 + 2, 0), (d / 2 - 2, w / 2 - 2, h))])
    return X


def locobox(L=840.0, w=220.0, h=220.0):
    X = ML.Model()
    rbox(X.mesh(TX['locobox']), (-L / 2, -w / 2, 0), (L / 2, w / 2, h), r=3, k=1, tile=L)
    ML.save('locobox', X)
    COLL['locobox'] = dict(boxes=[((-L / 2 + 2, -w / 2 + 2, 0), (L / 2 - 2, w / 2 - 2, h))])
    return X


def point_motor():
    """solenoid point motor screwed under the baseboard (hangs from z 0 down)"""
    X = ML.Model()
    rbox(X.mesh(TX['motor']), (-90, -50, -120), (90, 50, 0), r=4, k=1, tile=64)
    for x in (-50, 50):
        tube(X.mesh(TX['copper']), [(x, -50, -60), (x, -50, -100)], 26, nseg=12)
    for k, sh in enumerate((TX['cable_red'], TX['cable_black'], TX['cable_yellow'])):
        tube(X.mesh(sh), [(70, 30 - k * 14, -110), (70, 30 - k * 14, -180), (160, 30 - k * 14, -240)], 5, nseg=6)
    ML.save('point_motor', X)
    return X


def cable_run(pts, key, name, r=14.0):
    X = ML.Model()
    tube(X.mesh(TX[key]), pts, r, nseg=8)
    ML.save(name, X)
    return X


def pliers(L=600.0):
    """hanging on the pegboard (local: lies in the y-z plane, flat against x = 0)"""
    X = ML.Model()
    st, gr = TX['steel'], TX['pliers_grip']
    for sg in (1, -1):
        tube(X.mesh(gr), [(10, sg * 20, 0), (10, sg * 60, -L * 0.55)], 18, nseg=8)
        tube(X.mesh(st), [(10, sg * 20, 0), (10, -sg * 14, L * 0.3)], 12, nseg=8)
    ML_sphere(X.mesh(st), np.array([10, 0, 10]), 22)
    ML.save('pliers', X)
    return X


def saw(L=900.0):
    X = ML.Model()
    X.mesh(TX['steel']).poly([np.array(p, float) for p in ((6, -L / 2, 0), (6, L / 2 - 200, 0), (6, L / 2 - 200, 160), (6, -L / 2, 60))],
                             (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(TX['bench_wood']), (2, L / 2 - 200, -20), (18, L / 2, 200), r=6, k=2, tile=128)
    ML.save('saw', X)
    return X


def sprue(w=520.0, d=360.0, bar=26.0):
    """a kit sprue frame lying flat with parts attached (cover / step inside the kit box)"""
    X = ML.Model()
    sp = TX['sprue']
    for (x0, y0, x1, y1) in ((-w / 2, -d / 2, w / 2, -d / 2 + bar), (-w / 2, d / 2 - bar, w / 2, d / 2),
                             (-w / 2, -d / 2, -w / 2 + bar, d / 2), (w / 2 - bar, -d / 2, w / 2, d / 2), (-bar / 2, -d / 2, bar / 2, d / 2)):
        rbox(X.mesh(sp), (x0, y0, 0), (x1, y1, bar), r=4, k=1, tile=64)
    for (cx, cy, sx, sy) in ((-130, -60, 90, 140), (-130, 90, 110, 50), (120, -40, 140, 70), (130, 80, 60, 60)):
        rbox(X.mesh(sp), (cx - sx / 2, cy - sy / 2, 2), (cx + sx / 2, cy + sy / 2, 20), r=3, k=1, tile=64)
    ML.save('sprue', X)
    return X


def bulb_hanging(drop=180.0):
    X = ML.Model()
    tube(X.mesh(TX['cable_black']), [(0, 0, 0), (0, 0, -drop)], 4, nseg=6)
    revolve(X.mesh(TX['iron_dark']), [(14, -drop), (18, -drop - 20), (0, -drop - 22)], n=12)
    ML_sphere(X.mesh(TX['bulb']), np.array([0, 0, -drop - 46]), 28)
    ML.save('bulb', X)
    return X


def cobweb(s=200.0):
    X = ML.Model()
    X.mesh(TX['web']).poly([np.array(p, float) for p in ((0, 0, 0), (s, 0, 0), (s * 0.7, s * 0.7, -s * 0.5), (0, s, 0))],
                           (0, 0, -1), [(0.5, 0.5), (1, 0.5), (1, 1), (0.5, 1)])
    ML.save('cobweb', X)
    return X


def station_sign(L=700.0, h=90.0):
    X = ML.Model()
    rbox(X.mesh(TX['sign_station']), (-L / 2, -4, 0), (L / 2, 4, h), r=2, k=1, tile=L)
    for x in (-L / 2 + 30, L / 2 - 30):
        tube(X.mesh(TX['iron_green']), [(x, 0, -150), (x, 0, 0)], 6, nseg=8)
    ML.save('station_sign', X)
    return X


# ================================================================================================ the basement beyond the acrylic
# Seen from the layout across the acrylic guard, standing on the basement floor (z 0 local = the void floor). These
# replace the old painted wall: washing machine, boiler + pipes, wooden stairs up to the house door, metal shelving
# with stored boxes, a high window with a sunbeam, laundry basket, bucket + mop, a bare bulb.
def basement_mats():
    M = TX.material
    M('enamel', TL.solid((236, 236, 232), 3, 201, 128), 'lms', shade=40, v=0.12)
    M('chrome', TL.metal((200, 204, 210), False, 202), 'lms', shade=60, v=0.45)
    M('porthole', TL.solid((40, 60, 80), 2, 203, 64), 'glass', c='0.18 0.22 0.28')
    M('washer_panel', washer_panel_tex(), shade=30)
    M('drum', TL.metal((150, 154, 160), True, 204), shade=40)
    M('boiler', boiler_tex(), lathe=True, shade=60)
    M('gauge', gauge_tex(), shade=30)
    M('pipe_copper', TL.metal((190, 112, 64), True, 205), 'lms', shade=60, v=0.2)
    M('pipe_grey', TL.solid((150, 150, 148), 3, 206, 64), shade=60)
    M('tread', TL.planks((168, 124, 80), 1, (110, 76, 46), 10, False, False, 207), shade=30)
    M('stringer', TL.grime(TL.solid((214, 208, 196), 3, 208, 128), 0.25, 209), shade=30)
    M('handrail', TL.planks((120, 80, 48), 1, (80, 52, 30), 12, False, False, 210), shade=60)
    M('door_paint', door_tex(), shade=30)
    M('door_frame', TL.solid((230, 226, 214), 3, 211, 64), shade=30)
    M('brass', TL.metal((200, 160, 70), False, 212), 'lms', shade=60, v=0.35)
    M('door_glow', TL.solid((255, 230, 170), 2, 213, 64), 'glow')
    M('shelf_metal', TL.grime(TL.metal((120, 126, 132), True, 214), 0.2, 215), shade=30)
    M('box_xmas', box_label_tex('XMAS DECS', (200, 40, 40)), shade=30)
    M('box_photos', box_label_tex('PHOTOS', (40, 90, 160)), shade=30)
    M('box_trains', box_label_tex('SPARE TRACK', (30, 120, 60)), shade=30)
    M('box_misc', box_label_tex('KEEP!', (140, 90, 30)), shade=30)
    M('paintcan', paintcan_tex(), lathe=True, shade=60)
    M('window_sky', TL.solid((210, 232, 250), 2, 216, 64), 'glow')
    M('window_frame', TL.solid((224, 220, 210), 3, 217, 64), shade=30)
    M('sunbeam', sunbeam_tex(), 'add')
    M('basket', TL.grime(TL.dots((80, 150, 200), (40, 90, 140), 10, 0.2, 218), 0.1, 219), shade=60)
    M('bucket', TL.solid((200, 50, 40), 3, 220, 64), 'lms', shade=60, v=0.12)
    M('mophead', TL.fabric((220, 214, 196), 24, 221), shade=60)
    M('laundry', TL.fabric((90, 120, 190), 32, 222), shade=60)


def washer_panel_tex(w=512, h=128):
    im = _img(w, h, (230, 230, 226)); d = ImageDraw.Draw(im)
    d.rectangle((20, 30, 150, 98), fill=(200, 200, 196), outline=(150, 150, 150), width=3)        # detergent drawer
    d.rectangle((60, 58, 110, 70), fill=(120, 120, 120))
    d.rounded_rectangle((210, 40, 330, 88), 8, fill=(30, 50, 40)); d.text((270, 64), '1:24', font=font(30), fill=(90, 255, 140), anchor='mm')
    for k, t in enumerate(('30', '40', '60', '90')): d.text((360 + k * 30, 30), t, font=font(14), fill=(60, 60, 60))
    d.ellipse((380, 46, 470, 116), fill=(200, 200, 204), outline=(120, 120, 120), width=4)
    d.text((40, 110), 'PADWASH 9000', font=font(14), fill=(80, 80, 80))
    return _arr(im)


def boiler_tex(w=512, h=512):
    im = _img(w, h, (232, 230, 222)); d = ImageDraw.Draw(im)
    for y in (40, h - 40): d.rectangle((0, y - 6, w, y + 6), fill=(180, 176, 168))
    d.rectangle((150, 180, 360, 300), fill=(250, 250, 246), outline=(160, 160, 160), width=3)
    d.text((255, 210), 'HOT WATER', font=font(26), fill=(200, 40, 40), anchor='mm')
    d.text((255, 260), '180 L  /  3 kW', font=font(20), fill=(60, 60, 60), anchor='mm')
    return _arr(im)


def gauge_tex(n=128):
    im = _img(n, n, (240, 240, 236)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), outline=(40, 40, 40), width=6)
    for k in range(9):
        a = math.radians(225 - k * 33.75)
        d.line((n / 2 + 40 * math.cos(a), n / 2 - 40 * math.sin(a), n / 2 + 52 * math.cos(a), n / 2 - 52 * math.sin(a)), fill=(30, 30, 30), width=3)
    d.line((n / 2, n / 2, n / 2 + 40 * math.cos(math.radians(60)), n / 2 - 40 * math.sin(math.radians(60))), fill=(200, 30, 30), width=4)
    return _arr(im)


def door_tex(w=256, h=512):
    im = _img(w, h, (110, 140, 120)); d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in ((30, 30, 226, 230), (30, 270, 226, 482)):
        d.rectangle((x0, y0, x1, y1), outline=(80, 104, 88), width=10)
        d.rectangle((x0 + 18, y0 + 18, x1 - 18, y1 - 18), outline=(136, 166, 146), width=4)
    return _arr(im)


def box_label_tex(text, col, w=512, h=256):
    im = _img(w, h, (190, 152, 104)); d = ImageDraw.Draw(im)
    d.rectangle((0, 110, w, 146), fill=(210, 190, 150))                                         # parcel tape
    d.text((w / 2, 70), text, font=font(56), fill=col, anchor='mm')
    d.text((w / 2, 200), 'THIS WAY UP  ^', font=font(22), fill=(70, 50, 30), anchor='mm')
    return _arr(im)


def paintcan_tex(w=512, h=256):
    im = _img(w, h, (200, 200, 204)); d = ImageDraw.Draw(im)
    d.rectangle((0, 60, w, 200), fill=(250, 250, 246))
    d.rectangle((0, 60, w, 90), fill=(40, 120, 200))
    d.text((w / 2, 150), 'EMULSION  MAGNOLIA', font=font(30), fill=(40, 40, 40), anchor='mm')
    return _arr(im)


def sunbeam_tex(n=128):
    x, y = ML.xy(n)
    a = np.clip(1 - np.abs(x - 0.5) * 2, 0, 1) ** 1.5 * (0.35 + 0.65 * (1 - y))
    return np.stack([a * 120, a * 110, a * 80], -1).astype(np.float32)


def washing_machine(w=650.0, d=620.0, h=1400.0):
    """front faces -y (local), origin at the base centre"""
    X = ML.Model()
    rbox(X.mesh(TX['enamel']), (-w / 2, -d / 2, 30), (w / 2, d / 2, h), r=24, k=3, tile=512)
    rbox(X.mesh(TX['pipe_grey']), (-w / 2 + 20, -d / 2 + 20, 0), (w / 2 - 20, d / 2 - 20, 30), r=4, k=1, tile=256)
    for x in (-w / 2 + 50, w / 2 - 50):                                                              # feet
        for y in (-d / 2 + 50, d / 2 - 50):
            tube(X.mesh(TX['pipe_grey']), [(x, y, 0), (x, y, 30)], 16, nseg=8)
    # control panel strip (fitted label) on the front top
    X.mesh(TX['washer_panel']).poly([np.array(p, float) for p in ((-w / 2 + 30, -d / 2 - 0.6, h - 220), (w / 2 - 30, -d / 2 - 0.6, h - 220),
                                                                  (w / 2 - 30, -d / 2 - 0.6, h - 40), (-w / 2 + 30, -d / 2 - 0.6, h - 40))],
                                    (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    # porthole door: chrome ring + tinted glass + drum behind
    cz = h * 0.47; R = 230
    ring = Mesh(); revolve(ring, [(R - 40, 0), (R, 0), (R + 10, 30), (R - 50, 34)], n=40)
    X.mesh(TX['chrome']).add(ring, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (0, -d / 2, cz))
    g = Mesh(); disc(g, R - 44, 28, up=True, n=40)
    X.mesh(TX['porthole']).add(g, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (0, -d / 2, cz))
    dr = Mesh(); disc(dr, R - 50, -60, up=True, n=32)
    X.mesh(TX['drum']).add(dr, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (0, -d / 2, cz))
    rbox(X.mesh(TX['chrome']), (R - 10, -d / 2 - 46, cz - 50), (R + 30, -d / 2 - 2, cz + 50), r=8, k=2, tile=64)  # handle
    # knob
    kn = Mesh(); revolve(kn, [(42, 0), (42, 36), (30, 46), (0, 48)], n=20)
    X.mesh(TX['chrome']).add(kn, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (w / 2 - 110, -d / 2, h - 150))
    # hoses to the wall
    tube(X.mesh(TX['pipe_grey']), [(-w / 2 + 120, d / 2, h - 300), (-w / 2 + 120, d / 2 + 60, h - 260), (-w / 2 + 160, d / 2 + 70, h + 200)], 18, nseg=8)
    ML.save('washer', X)
    return X


def laundry_basket(r=200.0, h=330.0):
    X = ML.Model()
    revolve(X.mesh(TX['basket']), [(r * 0.85, 0), (r, h), (r + 10, h + 14), (r - 10, h + 14), (r * 0.85 - 10, 12), (0, 12)], n=28, u_tiles=6)
    ellipsoid(X.mesh(TX['laundry']), (0, 0, h - 30), r * 0.85, r * 0.8, 90, nu=14, nv=6)
    tube(X.mesh(TX['laundry']), [(r * 0.6, 0, h), (r + 40, 30, h - 60), (r + 60, 60, 4)], [26, 22, 18], nseg=8)
    ML.save('laundry_basket', X)
    return X


def water_boiler(r=260.0, h=1900.0, ceil=3400.0):
    """cylinder on legs with a gauge, copper pipes up to the ceiling (local z 0 = floor, ceil = height of the ceiling)"""
    X = ML.Model()
    for a in (45, 165, 285):
        tube(X.mesh(TX['pipe_grey']), [(r * 0.7 * math.cos(math.radians(a)), r * 0.7 * math.sin(math.radians(a)), 0),
                                       (r * 0.7 * math.cos(math.radians(a)), r * 0.7 * math.sin(math.radians(a)), 160)], 18, nseg=8)
    revolve(X.mesh(TX['boiler']), [(r - 30, 140), (r, 170), (r, h - 140), (r - 40, h - 60), (r * 0.5, h - 10), (0, h)], n=40, u_tiles=1)
    revolve(X.mesh(TX['pipe_grey']), [(0, 150), (r - 30, 150), (r - 30, 140)], n=40, inward=True)
    g = Mesh(); disc(g, 70, 0, up=True, n=24)
    X.mesh(TX['gauge']).add(g, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (0, -r - 12, h * 0.55))
    tube(X.mesh(TX['chrome']), [(0, -r + 4, h * 0.55), (0, -r - 12, h * 0.55)], 78, nseg=20, caps=(False, False))
    for (x, y, rr) in ((-90, 60, 30), (90, 60, 30), (0, 150, 22)):                                 # pipes up to the ceiling
        tube(X.mesh(TX['pipe_copper']), [(x, y, h - 40), (x, y, ceil)], rr, nseg=10, caps=(False, False))
    tube(X.mesh(TX['pipe_copper']), [(-90, 60, h + 500), (-90, 400, h + 500)], 30, nseg=10)
    for z in (h + 300, h + 900):                                                                    # pipe clips
        for x in (-90, 90):
            tube(X.mesh(TX['pipe_grey']), [(x, 60, z - 20), (x, 60, z + 20)], 40, nseg=10)
    ML.save('water_boiler', X)
    return X


def basement_stairs(run=2200.0, rise=2400.0, width=440.0, n=16, landing=600.0):
    """open wooden basement stairs rising toward +x along a wall at local y = +width/2 (the wall side), stringers,
    handrail with balusters on the open (-y) side, and a top landing on posts. local z 0 = floor, x 0 = first riser."""
    X = ML.Model()
    tr, st, hr = TX['tread'], TX['stringer'], TX['handrail']
    dx = run / n; dz = rise / n
    for i in range(n):
        x0 = i * dx; z = (i + 1) * dz
        x1 = x0 + dx + (4 if i < n - 1 else -1)
        rbox(X.mesh(tr), (x0 - 10, -width / 2 + 12, z - 36), (x1, width / 2 - 12, z), r=3, k=1, tile=256)
    T = 50.0
    for y in (-width / 2, width / 2 - 24):                                                          # stringers
        pts2 = [(0, 0), (run, rise - 40), (run, rise + 40), (0, 100)]
        q = [np.array([p[0], y, p[1]], float) for p in pts2]
        X.mesh(st).poly(q, (0, -1, 0), [(p[0] / 256, -p[1] / 256) for p in pts2])
        q2 = [np.array([p[0], y + 24, p[1]], float) for p in pts2[::-1]]
        X.mesh(st).poly(q2, (0, 1, 0), [(p[0] / 256, -p[1] / 256) for p in pts2[::-1]])
        X.mesh(st).poly([np.array(p, float) for p in ((0, y, 100), (run, y, rise + 40), (run, y + 24, rise + 40), (0, y + 24, 100))],
                        (-0.73, 0, 0.68), [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
    if landing > 0:                                                                                  # landing on posts
        rbox(X.mesh(tr), (run, -width / 2, rise - 50), (run + landing, width / 2, rise), r=3, k=1, tile=256)
        for x in (run + 20, run + landing - 30):
            rbox(X.mesh(st), (x - 25, -width / 2 + 5, 0), (x + 25, -width / 2 + 55, rise - 50), r=3, k=1, tile=256)
    # handrail + balusters
    y = -width / 2 + 10
    for i in range(0, n + 1, 2):
        x = i * dx + dx / 2; z = (i + 1) * dz
        tube(X.mesh(hr), [(x, y, z), (x, y, z + 520)], 9, nseg=6, caps=(False, False))
    end = run + landing - 10 if landing > 0 else run - 30
    tube(X.mesh(hr), [(dx / 2, y, dz + 540), (end, y, rise + 540)], 18, nseg=8)
    tube(X.mesh(hr), [(end, y, rise - (0 if landing > 0 else dz)), (end, y, rise + 540)], 16, nseg=8)
    ML.save('basement_stairs', X)
    return X


def house_door(w=440.0, h=850.0):
    """panelled door in its frame on a wall (local: wall face at y = 0, door faces -y), light leaking under it"""
    X = ML.Model()
    fr = TX['door_frame']
    for (x0, x1) in ((-w / 2 - 50, -w / 2), (w / 2, w / 2 + 50)):
        rbox(X.mesh(fr), (x0, -26, 0), (x1, 0.5, h + 50), r=4, k=1, tile=128)
    rbox(X.mesh(fr), (-w / 2 - 60, -30, h), (w / 2 + 60, 0.5, h + 70), r=4, k=1, tile=128)
    X.mesh(TX['door_paint']).poly([np.array(p, float) for p in ((-w / 2, -10, 14), (w / 2, -10, 14), (w / 2, -10, h), (-w / 2, -10, h))],
                                  (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    X.mesh(TX['door_glow']).poly([np.array(p, float) for p in ((-w / 2, -8, 0), (w / 2, -8, 0), (w / 2, -8, 14), (-w / 2, -8, 14))],
                                 (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    kn = Mesh(); revolve(kn, [(22, 0), (14, 20), (30, 44), (0, 56)], n=16)
    X.mesh(TX['brass']).add(kn, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float), (w / 2 - 60, -10, h * 0.48))
    ML.save('house_door', X)
    return X


def metal_shelving(w=700.0, d=420.0, h=1500.0, levels=(20, 480, 940, 1400)):
    X = ML.Model()
    m = TX['shelf_metal']
    for x in (-w / 2, w / 2 - 30):
        for y in (-d / 2, d / 2 - 30):
            rbox(X.mesh(m), (x, y, 0), (x + 30, y + 30, h), r=2, k=1, tile=128)
    for z in levels:
        rbox(X.mesh(m), (-w / 2, -d / 2, z), (w / 2, d / 2, z + 16), r=2, k=1, tile=256)
    # stored things: labelled boxes, paint cans, an old suitcase
    boxes = [(levels[0] + 16, -300, -40, 'box_trains'), (levels[0] + 16, -10, 310, 'box_photos'),
             (levels[1] + 16, -320, 0, 'box_xmas'), (levels[2] + 16, -60, 300, 'box_misc')]
    for (z, x0, x1, key) in boxes:
        hh = 300 if key != 'box_photos' else 260
        rbox(X.mesh(TX[key]), (x0, -d / 2 + 30, z), (x1, d / 2 - 30, z + hh), r=6, k=1, tile=x1 - x0)
    for k, x in enumerate((90, 200, 300)):
        revolve(X.mesh(TX['paintcan']), [(48, 0), (48, 120), (44, 124), (0, 124)], n=16, u_tiles=1, cx=x, cy=-40)
    # (cans stand on the middle shelf)
    M = X.mesh(TX['paintcan'])
    off = levels[1] + 16
    M.V = [v + np.array([0, 0, off]) if i >= len(M.V) - 3 * 17 * 4 else v for i, v in enumerate(M.V)]
    rbox(X.mesh(TX['laundry']), (-320, -d / 2 + 40, levels[2] + 16), (-80, d / 2 - 40, levels[2] + 16 + 120), r=20, k=2, tile=128)
    ML.save('shelving', X)
    return X


def basement_window(w=500.0, h=450.0):
    """high window in the wall (local: wall face y = 0, room at -y): frame, mullion, glowing daylight panes, a sill"""
    X = ML.Model()
    fr = TX['window_frame']
    X.mesh(TX['window_sky']).poly([np.array(p, float) for p in ((-w / 2, -2, 0), (w / 2, -2, 0), (w / 2, -2, h), (-w / 2, -2, h))],
                                  (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    for (x0, z0, x1, z1) in ((-w / 2 - 30, -30, -w / 2, h + 30), (w / 2, -30, w / 2 + 30, h + 30), (-w / 2, h, w / 2, h + 30),
                             (-w / 2, -30, w / 2, 0), (-10, 0, 10, h), (-w / 2, h / 2 - 8, w / 2, h / 2 + 8)):
        rbox(X.mesh(fr), (x0, -24, z0), (x1, 0.5, z1), r=2, k=1, tile=128)
    rbox(X.mesh(fr), (-w / 2 - 50, -90, -60), (w / 2 + 50, 0.5, -30), r=3, k=1, tile=128)               # sill
    ML.save('basement_window', X)
    return X


def sunbeam(top_w=500.0, drop=2400.0, reach=1300.0):
    """additive dusty light shaft from the window (local origin at the window bottom centre) down and out into the room"""
    X = ML.Model()
    sb = TX['sunbeam']
    q = [np.array(p, float) for p in ((-top_w / 2, -4, 420), (top_w / 2, -4, 420), (top_w / 2 + 60, -reach, -drop), (-top_w / 2 - 60, -reach, -drop))]
    X.mesh(sb).poly(q, (0, -0.9, 0.4), [(0, 0), (1, 0), (1, 1), (0, 1)])
    q = [np.array(p, float) for p in ((-top_w / 2, -4, 0), (top_w / 2, -4, 0), (top_w / 2 + 60, -reach + 300, -drop), (-top_w / 2 - 60, -reach + 300, -drop))]
    X.mesh(sb).poly(q, (0, -0.9, 0.4), [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('sunbeam', X)
    return X


def bucket_mop():
    X = ML.Model()
    revolve(X.mesh(TX['bucket']), [(110, 0), (140, 260), (146, 270), (134, 270), (104, 12), (0, 12)], n=24, u_tiles=2)
    tube(X.mesh(TX['chrome']), [(-130, 0, 250), (0, 0, 380), (130, 0, 250)], 5, nseg=6)
    tube(X.mesh(TX['handrail']), [(40, 20, 40), (180, 140, 1300)], 14, nseg=8)
    ellipsoid(X.mesh(TX['mophead']), (40, 20, 70), 90, 90, 70, nu=12, nv=6)
    ML.save('bucket_mop', X)
    return X


# ================================================================================================ themed jump pads
# Dressing for K.jumppad(dress=...): local +y = flight direction, z 0 = the floor, radius ~40 (the trigger is 48x48).
def pad_mats():
    M = TX.material
    M('manhole', manhole_tex(), shade=60)
    M('iron_rim', TL.grime(TL.metal((70, 70, 74), False, 301), 0.3, 302), shade=60)
    M('vent_rock', TL.stone((120, 112, 100), 10, (80, 74, 66), seed=303), shade=60)
    M('steam', steam_tex(), 'add', wave='sin 0.6 0.3 0 0.7', tcmod='scroll 0 0.4', two=True)
    M('vent_glow', TL.solid((255, 170, 70), 2, 304, 64), 'glow', wave='sin 0.8 0.2 0 0.5')
    M('trapdoor', TL.planks((126, 86, 52), 5, (70, 46, 28), 8, False, False, 305), shade=60)
    M('coil', TL.metal((196, 128, 70), True, 306), 'lms', shade=80, v=0.3)
    M('btn_red', TL.solid((220, 30, 26), 2, 307, 64), 'lms', shade=80, v=0.3)
    M('btn_glow', TL.solid((255, 80, 60), 2, 308, 64), 'glow', wave='sin 0.7 0.3 0 0.6')
    M('sewbutton', TL.solid((240, 200, 60), 3, 309, 64), 'lms', shade=80, v=0.2)


def manhole_tex(n=256):
    im = _img(n, n, (70, 70, 72)); d = ImageDraw.Draw(im)
    c = n / 2
    for r in (120, 100): d.ellipse((c - r, c - r, c + r, c + r), outline=(110, 110, 112), width=6)
    for k in range(-4, 5):
        d.line((c - 90, c + k * 20, c + 90, c + k * 20), fill=(100, 100, 102), width=5)
    d.rectangle((c - 70, c - 16, c + 70, c + 16), fill=(70, 70, 72))
    d.text((c, c), 'PADVILLE', font=font(22), fill=(140, 140, 140), anchor='mm')
    return _arr(im)


def steam_tex(n=128):
    x, y = ML.xy(n)
    a = np.clip(1 - np.abs(x - 0.5) * 2, 0, 1) * (1 - y) * (0.6 + 0.4 * ML.noise(n, 4, 310))
    a = np.clip(a, 0, 1)
    return np.stack([a * 200] * 3, -1).astype(np.float32)


def pad_manhole():
    X = ML.Model()
    revolve(X.mesh(TX['iron_rim']), [(46, 0), (46, 4), (40, 6)], n=24)
    disc(X.mesh(TX['manhole']), 40, 6, up=True, n=24)
    ML.save('pad_manhole', X)


def pad_vent():
    X = ML.Model()
    rng = np.random.default_rng(7)
    for k in range(9):
        a = 2 * math.pi * k / 9
        r = 40 + rng.uniform(-3, 3)
        ellipsoid(X.mesh(TX['vent_rock']), (r * math.cos(a), r * math.sin(a), 0), 16, 16, rng.uniform(12, 20), nu=8, nv=5, flat_bottom=0)
    disc(X.mesh(TX['vent_glow']), 30, 2, up=True, n=16)
    for ang in (0, 60, 120):                                                                # crossed steam sheets
        a = math.radians(ang); c, s_ = math.cos(a), math.sin(a)
        q = [np.array(p, float) for p in ((-26 * c, -26 * s_, 4), (26 * c, 26 * s_, 4), (44 * c, 44 * s_, 150), (-44 * c, -44 * s_, 150))]
        X.mesh(TX['steam']).poly(q, (-s_, c, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save('pad_vent', X)


def pad_trapdoor():
    """open wooden trapdoor: frame flush on the floor, the lid swung up and back (hinge at -y)"""
    X = ML.Model()
    for (x0, y0, x1, y1) in ((-46, -46, 46, -38), (-46, 38, 46, 46), (-46, -38, -38, 38), (38, -38, 46, 38)):
        rbox(X.mesh(TX['iron_rim']), (x0, y0, 0), (x1, y1, 3), r=0.5, k=1, tile=64)
    lid = Mesh(); rbox(lid, (-40, 0, 0), (40, 6, 80), r=1, k=1, tile=96)
    a = math.radians(-18)
    X.mesh(TX['trapdoor']).add(lid, np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]), (0, -52, 0))
    for x in (-28, 28):
        rbox(X.mesh(TX['iron_rim']), (x - 3, -52, 0), (x + 3, -40, 3), r=0.5, k=1, tile=32)
    ML.save('pad_trapdoor', X)


def pad_spring():
    """giant compression spring on a steel plate (the under-board world is at real-world scale)"""
    X = ML.Model()
    revolve(X.mesh(TX['steel']), [(44, 0), (44, 6), (0, 6)], n=24, inward=False)
    disc(X.mesh(TX['steel']), 44, 6, up=True, n=24)
    pts = [(30 * math.cos(t), 30 * math.sin(t), 12 + t * 3.2) for t in np.linspace(0, 2 * math.pi * 6, 150)]
    tube(X.mesh(TX['coil']), pts, 5, nseg=6)
    ML.save('pad_spring', X)


def pad_button():
    """the controller's big red push button: chrome bezel + glowing red cap"""
    X = ML.Model()
    revolve(X.mesh(TX['chrome']), [(46, 0), (46, 8), (38, 12), (34, 10)], n=24)
    revolve(X.mesh(TX['btn_red']), [(34, 8), (34, 20), (28, 26), (0, 27)], n=24)
    revolve(X.mesh(TX['btn_glow']), [(36, 8.5), (34.5, 9.5)], n=24)
    ML.save('pad_button', X)


def pad_sewbutton():
    """a sewing button dropped on the bench: four holes and a raised rim"""
    X = ML.Model()
    revolve(X.mesh(TX['sewbutton']), [(42, 0), (42, 6), (38, 9), (30, 7), (30, 5)], n=28)
    disc(X.mesh(TX['sewbutton']), 30, 5, up=True, n=28)
    for (hx, hy) in ((-9, -9), (9, -9), (-9, 9), (9, 9)):
        disc(X.mesh(TX['iron_rim']), 4.5, 5.4, up=True, n=10, cx=hx, cy=hy)
    ML.save('pad_sewbutton', X)


# ================================================================================================ viewing gallery (basement side of the acrylic)
def gallery_mats():
    M = TX.material
    M('stool_seat', TL.fabric((150, 34, 30), 40, 401), shade=80)
    M('stool_seat2', TL.fabric((30, 70, 120), 40, 402), shade=80)
    M('stool_wood', TL.planks((120, 80, 46), 1, (80, 52, 30), 14, False, True, 403), shade=60)


def bar_stool(seat_h=1240.0, seat_r=280.0, key='stool_seat', name='bar_stool', back=False):
    """chrome bar stool: weighted round base, post, footrest ring, padded round seat (optionally a low wooden back).
    Origin on the floor at the post."""
    X = ML.Model()
    ch = TX['chrome']
    revolve(X.mesh(ch), [(300, 0), (300, 14), (240, 40), (60, 60), (40, 70)], n=32, u_tiles=2)
    tube(X.mesh(ch), [(0, 0, 60), (0, 0, seat_h - 90)], 34, nseg=14, caps=(False, False))
    ring = [(210 * math.cos(t), 210 * math.sin(t), seat_h * 0.42) for t in np.linspace(0, 2 * math.pi, 33)]
    tube(X.mesh(ch), ring, 13, nseg=8, caps=(False, False))
    for a in (0, 120, 240):
        c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        tube(X.mesh(ch), [(34 * c, 34 * s_, seat_h * 0.42 + 40), (205 * c, 205 * s_, seat_h * 0.42)], 9, nseg=6)
    revolve(X.mesh(ch), [(120, seat_h - 96), (200, seat_h - 70), (0, seat_h - 70)], n=24, inward=True)
    revolve(X.mesh(TX[key]), [(seat_r - 30, seat_h - 72), (seat_r, seat_h - 40), (seat_r - 6, seat_h + 10),
                              (seat_r - 50, seat_h + 34), (0, seat_h + 40)], n=32, u_tiles=4)
    if back:
        for a in (150, 210):
            c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
            tube(X.mesh(TX['stool_wood']), [((seat_r - 40) * c, (seat_r - 40) * s_, seat_h), ((seat_r - 20) * c, (seat_r - 20) * s_, seat_h + 420)], 16, nseg=8)
        arc = [((seat_r - 10) * math.cos(t), (seat_r - 10) * math.sin(t), seat_h + 400) for t in np.radians(np.linspace(130, 230, 12))]
        tube(X.mesh(TX['stool_wood']), arc, 34, nseg=8, ry=[60] * 12)
    ML.save(name, X)
    return X


# ================================================================================================ shop row interiors (48u/m)
def loaf_tex(n=128):
    a = TL.grime(TL.solid((196, 132, 64), 8, 501, n), 0.2, 502)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(4):
        x = n * (k + 0.5) / 4
        d.line((x - 10, n * 0.2, x + 10, n * 0.8), fill=(236, 200, 140), width=5)       # scored crust
    return _arr(im)


def stamps_tex(n=256):
    im = _img(n, n, (110, 76, 46)); d = ImageDraw.Draw(im)
    for i in range(6):
        for j in range(4):
            x0, y0 = 6 + i * 41, 6 + j * 62
            d.rectangle((x0, y0, x0 + 37, y0 + 58), fill=(60, 40, 24))
            r = np.random.default_rng(i * 7 + j)
            for k in range(int(r.integers(0, 4))):
                c = [(236, 230, 214), (210, 196, 160), (180, 60, 50), (60, 90, 150)][int(r.integers(0, 4))]
                d.rectangle((x0 + 4 + k * 3, y0 + 8 + k * 10, x0 + 33, y0 + 30 + k * 10), fill=c)
    return _arr(im)


def shop_mats():
    M = TX.material
    M('loaf', loaf_tex(), shade=80)
    M('crust_dark', TL.grime(TL.solid((140, 84, 40), 8, 503, 64), 0.2, 504), shade=80)
    M('icing_pink', TL.solid((250, 180, 200), 3, 505, 64), shade=80)
    M('icing_white', TL.solid((250, 248, 240), 2, 506, 64), shade=80)
    M('cake_sponge', TL.solid((236, 200, 130), 6, 507, 64), shade=80)
    M('cherry', TL.solid((200, 20, 30), 2, 508, 32), shade=80)
    M('counter_wood', TL.planks((150, 96, 56), 3, (100, 60, 30), 10, False, True, 509), shade=40)
    M('counter_top', TL.stone((214, 210, 200), cells=30, edge=(170, 166, 160), edge_w=0.02, seed=510), shade=40)
    M('display_glass', TL.solid((40, 50, 56), 3, 511, 64), 'glass', c='0.06 0.07 0.08')
    M('shelf_wood', TL.planks((170, 120, 76), 2, (110, 74, 44), 8, False, True, 512), shade=40)
    M('toy_red', TL.solid((210, 40, 40), 3, 513, 64), shade=60)
    M('toy_blue', TL.solid((40, 90, 200), 3, 514, 64), shade=60)
    M('toy_yellow', TL.solid((240, 200, 40), 3, 515, 64), shade=60)
    M('toy_green', TL.solid((40, 150, 70), 3, 516, 64), shade=60)
    M('teddy', TL.fabric((160, 110, 60), 32, 517), shade=80)
    M('felt_green', TL.fabric((50, 120, 60), 32, 518), shade=40)
    M('stamps', stamps_tex(), shade=40)
    M('parcel', TL.grime(TL.solid((190, 150, 100), 6, 519, 64), 0.15, 520), shade=40)
    M('string', TL.solid((230, 220, 190), 2, 521, 32), shade=40)
    M('mailsack', TL.fabric((150, 140, 110), 32, 522), shade=80)
    M('post_red', TL.solid((200, 30, 30), 3, 523, 64), shade=40)
    M('grille', TL.metal((190, 160, 80), False, 524), 'lms', shade=60, v=0.25)
    M('flour_sack', TL.fabric((230, 222, 200), 32, 525), shade=80)


def _loaf(Mh, x, y, z, L=14.0, w=7.0, h=6.0, a=0.0):
    tmp = Mesh(); ellipsoid(tmp, (0, 0, 0), L / 2, w / 2, h, nu=12, nv=6, flat_bottom=0.0)
    Mh.add(tmp, rot_z(a), (x, y, z))


def bakery_display(L=130.0, d=36.0, h=44.0):
    """bakery: glass-fronted display counter with loaves, cakes and buns, and a wall rack of bread behind it (local
    +y = the wall it stands against, customers at -y). Origin = floor at the counter's centre front."""
    X = ML.Model()
    rbox(X.mesh(TX['counter_wood']), (-L / 2, 0, 0), (L / 2, d, h - 18), r=1.5, k=1, tile=96)
    rbox(X.mesh(TX['counter_top']), (-L / 2 - 2, -2, h - 4), (L / 2 + 2, d + 2, h), r=1, k=1, tile=96)
    for x in (-L / 2, L / 2 - 2):                                                       # glass case ends
        rbox(X.mesh(TX['counter_wood']), (x, 0, h - 18), (x + 2, d * 0.7, h - 4), r=0.4, k=1, tile=32)
    quad = lambda Mh, p: Mh.poly([np.array(q, float) for q in p], (0, -1, 0.3), [(0, 1), (1, 1), (1, 0), (0, 0)])
    quad(X.mesh(TX['display_glass']), [(-L / 2, 0, h - 18), (L / 2, 0, h - 18), (L / 2, d * 0.7, h - 4), (-L / 2, d * 0.7, h - 4)])
    for i, x in enumerate(np.linspace(-L / 2 + 12, L / 2 - 12, 8)):                     # loaves + buns inside the case
        if i % 3 == 2:
            for k in range(3): sphere(X.mesh(TX['crust_dark']), (x - 4 + 4 * k, d * 0.45, h - 15), 2.6, nu=8, nv=5)
        else:
            _loaf(X.mesh(TX['loaf']), x, d * 0.45, h - 18, a=0.3 * (i % 2))
    for (x, key) in ((-L / 2 + 20, 'icing_pink'), (L / 2 - 22, 'icing_white')):        # cakes on stands on top
        X.add_model(cake_on_stand(key), np.eye(3), (x, d * 0.75, h))
    # wall rack: three slatted shelves of bread on the wall behind
    for z in (64, 92, 120):
        rbox(X.mesh(TX['shelf_wood']), (-L / 2 + 6, d - 14, z), (L / 2 - 6, d, z + 2.5), r=0.5, k=1, tile=64)
        for i, x in enumerate(np.linspace(-L / 2 + 16, L / 2 - 16, 7)):
            _loaf(X.mesh(TX['loaf' if (i + z) % 2 else 'crust_dark']), x, d - 7, z + 2.5, L=13, w=7, h=6, a=0.5 * ((i + z // 28) % 2))
    for x in (-L / 2 + 4, L / 2 - 8):
        rbox(X.mesh(TX['shelf_wood']), (x, d - 16, 50), (x + 4, d, 132), r=0.5, k=1, tile=64)
    ML.save('bakery_display', X)
    COLL['bakery_display'] = dict(boxes=[((-L / 2, 0, 0), (L / 2, d, h))])
    return X


def cake_on_stand(key='icing_pink'):
    X = ML.Model()
    revolve(X.mesh(TX['chrome']), [(7, 0), (2, 1), (2, 8), (9, 9), (0, 9)], n=12)
    revolve(X.mesh(TX['cake_sponge']), [(8, 9), (8, 14), (0, 14)], n=16)
    revolve(X.mesh(TX[key]), [(8.4, 13), (8.4, 18), (0, 18)], n=16)
    sphere(X.mesh(TX['cherry']), (0, 0, 19.5), 1.6, nu=6, nv=4)
    return X


def toy_table(L=120.0, w=60.0, h=30.0):
    """toy shop display table: green felt top with a little oval train set, a rocking horse, a teddy bear, building
    blocks and a spinning top (origin = floor at the table centre)"""
    X = ML.Model()
    rbox(X.mesh(TX['counter_wood']), (-L / 2, -w / 2, h - 4), (L / 2, w / 2, h), r=1, k=1, tile=96)
    rbox(X.mesh(TX['felt_green']), (-L / 2 + 2, -w / 2 + 2, h), (L / 2 - 2, w / 2 - 2, h + 0.6), r=0.2, k=1, tile=64, faces='t')
    for (x, y) in ((-L / 2 + 3, -w / 2 + 3), (L / 2 - 6, -w / 2 + 3), (-L / 2 + 3, w / 2 - 6), (L / 2 - 6, w / 2 - 6)):
        rbox(X.mesh(TX['counter_wood']), (x, y, 0), (x + 3, y + 3, h - 4), r=0.5, k=1, tile=32)
    z = h + 0.6
    oval = [(-L * 0.18 + 16 * math.cos(t) * 1.8, -w * 0.12 + 12 * math.sin(t), z + 0.6) for t in np.linspace(0, 2 * math.pi, 33)]
    tube(X.mesh(TX['steel']), oval, 0.6, nseg=4)
    rbox(X.mesh(TX['toy_red']), (-L * 0.18 + 22, -w * 0.12 - 3, z), (-L * 0.18 + 30, -w * 0.12 + 3, z + 5), r=0.6, k=1, tile=16)
    rbox(X.mesh(TX['toy_blue']), (-L * 0.18 + 10, -w * 0.12 + 8, z), (-L * 0.18 + 17, -w * 0.12 + 13, z + 4), r=0.6, k=1, tile=16)
    # rocking horse
    hx, hy = L * 0.22, w * 0.1
    for s in (-1, 1):
        tube(X.mesh(TX['toy_red']), [(hx + 12 * math.sin(t), hy + s * 4, z + 3.4 - 3 * math.cos(t)) for t in np.linspace(-1.2, 1.2, 9)], 0.8, nseg=5)
        for xx in (-6, 6): tube(X.mesh(TX['shelf_wood']), [(hx + xx, hy + s * 4, z + 1.5), (hx + xx * 0.6, hy + s * 2, z + 9)], 0.7, nseg=4)
    ellipsoid(X.mesh(TX['shelf_wood']), (hx, hy, z + 11), 8, 3.2, 3.4, nu=10, nv=6)
    tube(X.mesh(TX['shelf_wood']), [(hx + 6, hy, z + 12), (hx + 9, hy, z + 18)], 2.0, nseg=6)
    ellipsoid(X.mesh(TX['shelf_wood']), (hx + 11, hy, z + 18), 3.5, 1.8, 2, nu=8, nv=5)
    tube(X.mesh(TX['toy_yellow']), [(hx + 7, hy, z + 19), (hx + 2, hy, z + 15)], 0.9, nseg=4)
    # teddy bear sitting at the back corner
    tx, ty = -L * 0.38, w * 0.25
    sphere(X.mesh(TX['teddy']), (tx, ty, z + 5), 5, nu=10, nv=7)
    sphere(X.mesh(TX['teddy']), (tx, ty, z + 12.5), 3.6, nu=10, nv=7)
    for s in (-1, 1):
        sphere(X.mesh(TX['teddy']), (tx + s * 2.6, ty, z + 15.5), 1.3, nu=6, nv=4)
        sphere(X.mesh(TX['teddy']), (tx + s * 4.5, ty - 2, z + 6), 1.8, nu=6, nv=4)
        sphere(X.mesh(TX['teddy']), (tx + s * 2.5, ty - 4, z + 1.5), 1.9, nu=6, nv=4)
    sphere(X.mesh(TX['ctrl_black']), (tx, ty - 3.4, z + 12), 0.7, nu=6, nv=4)
    # building blocks and a spinning top
    for i, (x, y, zz, key) in enumerate(((10, 18, 0, 'toy_red'), (16, 18, 0, 'toy_blue'), (13, 18, 5, 'toy_yellow'), (22, 14, 0, 'toy_green'))):
        rbox(X.mesh(TX[key]), (x - 2.5, y - 2.5, z + zz), (x + 2.5, y + 2.5, z + zz + 5), r=0.4, k=1, tile=8)
    revolve(X.mesh(TX['toy_yellow']), [(0.2, z), (5, z + 3), (4, z + 5), (0.8, z + 6), (0.8, z + 9), (0, z + 9)], n=12, cx=-4, cy=w * 0.3)
    ML.save('toy_table', X)
    COLL['toy_table'] = dict(boxes=[((-L / 2, -w / 2, 0), (L / 2, w / 2, h))])
    return X


def post_counter(L=144.0, d=24.0, h=44.0):
    """post office counter with a brass grille, a parcel scale and a stamp drawer unit (customers at -y)"""
    X = ML.Model()
    rbox(X.mesh(TX['counter_wood']), (-L / 2, -d / 2, 0), (L / 2, d / 2, h - 4), r=1.5, k=1, tile=96)
    rbox(X.mesh(TX['counter_top']), (-L / 2 - 2, -d / 2 - 2, h - 4), (L / 2 + 2, d / 2 + 2, h), r=1, k=1, tile=96)
    rbox(X.mesh(TX['post_red']), (-L / 2 + 6, -d / 2 - 0.5, 8), (L / 2 - 6, -d / 2, 12), r=0.3, k=1, tile=64, faces='s')
    for x in np.linspace(-L / 2 + 6, L / 2 - 50, 10):                                      # grille bars
        tube(X.mesh(TX['grille']), [(x, 0, h), (x, 0, h + 30)], 0.6, nseg=4)
    tube(X.mesh(TX['grille']), [(-L / 2 + 6, 0, h + 30), (L / 2 - 50, 0, h + 30)], 0.9, nseg=4)
    revolve(X.mesh(TX['chrome']), [(6, h), (6, h + 2), (1.2, h + 3), (1.2, h + 8), (7, h + 9), (7, h + 10), (0, h + 10)], n=14, cx=L / 2 - 30)
    rbox(X.mesh(TX['parcel']), (L / 2 - 36, -5, h + 10), (L / 2 - 24, 5, h + 18), r=0.5, k=1, tile=16)
    for x in (L / 2 - 14, ):
        rbox(X.mesh(TX['post_red']), (x - 6, -4, h), (x + 6, 4, h + 14), r=1, k=1, tile=16)
    ML.save('post_counter', X)
    COLL['post_counter'] = dict(boxes=[((-L / 2, -d / 2, 0), (L / 2, d / 2, h))])
    return X


def pigeonholes(L=150.0, h=100.0, d=12.0):
    """wall of sorting pigeonholes with letters in them (back at local y = 0, against a wall at +y)"""
    X = ML.Model()
    rbox(X.mesh(TX['shelf_wood']), (-L / 2, -d, 0), (L / 2, 0, 30), r=1, k=1, tile=64)
    X.mesh(TX['stamps']).poly([np.array(p, float) for p in ((-L / 2, -d - 0.2, 30), (L / 2, -d - 0.2, 30), (L / 2, -d - 0.2, h), (-L / 2, -d - 0.2, h))],
                              (0, -1, 0), [(0, 1), (3, 1), (3, 0), (0, 0)])
    rbox(X.mesh(TX['shelf_wood']), (-L / 2 - 2, -d, h), (L / 2 + 2, 0, h + 3), r=0.5, k=1, tile=64)
    for x in (-L / 2 - 2, L / 2):
        rbox(X.mesh(TX['shelf_wood']), (x, -d, 0), (x + 2, 0, h), r=0.4, k=1, tile=32)
    ML.save('pigeonholes', X)
    COLL['pigeonholes'] = dict(boxes=[((-L / 2 - 2, -d, 0), (L / 2 + 2, 0, h + 3))])
    return X


def parcel_pile():
    """parcels tied with string and two mail sacks (cover-sized clutter for a corner)"""
    X = ML.Model()
    for (x, y, z, sx, sy, sz, a) in ((0, 0, 0, 14, 10, 10, 0), (2, 1, 10, 10, 8, 7, 20), (24, -4, 0, 9, 9, 12, -10), (-20, 6, 0, 8, 12, 8, 35)):
        b = Mesh(); rbox(b, (-sx, -sy, 0), (sx, sy, sz), r=0.6, k=1, tile=24)
        X.mesh(TX['parcel']).add(b, rot_z(a), (x, y, z))
        s = Mesh(); rbox(s, (-0.5, -sy - 0.3, 0), (0.5, sy + 0.3, sz + 0.3), r=0.1, k=1, tile=8); rbox(s, (-sx - 0.3, -0.5, 0), (sx + 0.3, 0.5, sz + 0.3), r=0.1, k=1, tile=8)
        X.mesh(TX['string']).add(s, rot_z(a), (x, y, z))
    for (x, y) in ((-6, 30), (26, 26)):
        ellipsoid(X.mesh(TX['mailsack']), (x, y, 13), 11, 9, 13, nu=12, nv=7, flat_bottom=-13)
        tube(X.mesh(TX['string']), [(x, y, 25), (x, y, 30)], 2.2, nseg=6)
    ML.save('parcel_pile', X)
    COLL['parcel_pile'] = dict(boxes=[((-30, -14, 0), (38, 40, 26))])
    return X


def flour_store():
    """bakery store room: stacked flour sacks on a pallet and a sack trolley"""
    X = ML.Model()
    rbox(X.mesh(TX['shelf_wood']), (-36, -24, 0), (36, 24, 5), r=0.5, k=1, tile=64)
    for (x, y, z, a) in ((-18, -11, 5, 0), (18, -11, 5, 0), (-18, 11, 5, 0), (18, 11, 5, 0), (0, -11, 15, 90), (0, 11, 15, 90), (-6, 0, 25, 10)):
        b = Mesh(); ellipsoid(b, (0, 0, 5), 17, 10, 5.5, nu=10, nv=6, flat_bottom=-5)
        X.mesh(TX['flour_sack']).add(b, rot_z(a), (x, y, z))
    ML.save('flour_store', X)
    COLL['flour_store'] = dict(boxes=[((-36, -24, 0), (36, 24, 34))])
    return X
