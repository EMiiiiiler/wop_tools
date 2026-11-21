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
from meshlib import Mesh, rbox, tube, revolve, disc, prism, ellipsoid, rot_z, rot_axis

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
