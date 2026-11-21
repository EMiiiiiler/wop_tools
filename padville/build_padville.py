#!/usr/bin/env python3
"""Padville Junction (wop_padville) - FFA on a hobbyist's model railway in a basement, built on woplib.

    OUT=<dir> python3 build_padville.py          (wopbuild.py padville preview / all)

You are a model-railway figure. The LAYOUT (x < 1152) is the model world at 48u per model metre: a circular main line
(R 1500 round (-832, 0)) with a working train you can ride, Padville station, the town (church + tower, shops, houses,
fountain plaza), a lake with a water mill, a three-tier mountain with the tunnel, a farm with a windmill, a goods
yard + signal box and an engine shed with a turntable you can ride. Under the town, a lift-out access hatch drops
you into the joists and wiring under the baseboard. The WORKBENCH (x > 1152) is the giant world at 42u per real cm: a
tipped-over mug, the controller, a ruler ramp, the desk lamp (Imperius on its shade), a station kit box, tools and a
pegboard shelf. An acrylic guard runs along the open south edge; painted backdrops close the north and west.

x east, y north, z 0 = baseboard / bench top. Levels: underworld -600 | lake bed -112 | ground 0 | platforms 48 |
T1 400 | T2 640 | T3 832 | tower roof 736 | lamp shade 960 | pegboard shelf 716. See README.md.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, hull, cyl, carve, sub_rects, sign_box, ngon, prism
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL, town, railway as RW, shopbits as SB
import pv_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                # -2816 -2048 2304 2048
BX = 1152                                      # layout | workbench seam
ZC = 2600                                      # basement ceiling
VY, VZ = -3900, -800                           # the basement beyond the acrylic guard (floor, modelled corner)
C = (-832.0, 0.0); R = 1500.0                  # main line circle
BAL = (1380, 1620)                             # ballast band
RAIL_Z = 30                                    # rail top
U = (-1300, -1150, -150, -250); UZ = -600      # underworld under the town
H1 = (-560, -560); H2 = (-1180, -560); HH = 112   # drop hatch / exit hatch centres, half size
LAKE_C = (-1700.0, -100.0); LRX, LRY = 330.0, 520.0
LAKE = (-2046, -636, -1354, 436); LBED, LWAT = -112, -32
TT_C = (880.0, -1620.0); TT_R = 250.0
VAULT = (1400, 300, 1900, 800); VAZ = -1400

K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '30', '_color': '1 0.95 0.88', 'gridsize': '160 160 192'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
PM.setup(TX)


def P(a_deg, r):
    a = math.radians(a_deg)
    return (C[0] + r * math.cos(a), C[1] + r * math.sin(a))


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces); return t


def place(name, x, y, z, angle=0, occupy=True, **kw):
    c = PM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), occupy=occupy, **kw)


def deco(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


def sector(r0, r1, a0, a1, z0, z1, tex, step=7.5, detail=True):
    """annular sector as convex pieces (chords), each <= step degrees"""
    n = max(1, int(math.ceil((a1 - a0) / step)))
    out = []
    for k in range(n):
        aa = a0 + (a1 - a0) * k / n; ab = a0 + (a1 - a0) * (k + 1) / n
        pts = []
        for a in (aa, ab):
            for r in (r0, r1):
                x, y = P(a, r); pts += [(x, y, z0), (x, y, z1)]
        out.append(hull(pts, tex, detail=detail, round_pts=False))
    return out


# ================================================================================================ textures
def grass_tex(n=256, seed=1):
    a = TL.solid((88, 128, 60), 6, seed, n)
    x, y = ML.xy(n)
    fl = ML.noise(n, 1, seed + 1)
    a = a + np.where((fl > 1.6)[..., None], ML.C((60, 50, 20)), 0) + np.where((fl < -1.8)[..., None], ML.C((40, 50, 10)), 0)
    return a


def mat_tex(n=512):
    """self-healing cutting mat: green with a 1 cm grid (42u) and heavier 5 cm lines"""
    a = TL.solid((40, 120, 86), 3, 5, n)
    x, y = ML.xy(n)
    g = ((x * 12) % 1 < 0.035) | ((y * 12) % 1 < 0.035)
    G = ((x * 12 / 5 * 2.5) % 1 < 0.012) | ((y * 12 / 5 * 2.5) % 1 < 0.012)
    a = np.where(g[..., None], ML.C((200, 230, 210)), a)
    a = np.where(G[..., None], ML.C((250, 250, 240)), a)
    return a


def backdrop_tex(w=2048, h=512, seed=3, hills=True):
    """painted scenic backdrop: sky gradient, soft clouds, distant blue hills, nearer green hills, a few trees"""
    from PIL import Image, ImageDraw, ImageFilter
    x = np.linspace(0, 1, w)[None, :]; y = np.linspace(0, 1, h)[:, None]
    sky = ML.lerp(ML.C((120, 170, 225)), ML.C((214, 230, 244)), np.clip(y * 1.2, 0, 1)[..., None]) * np.ones((h, w, 1))
    rng = np.random.default_rng(seed)
    im = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    for k in range(18):
        cx, cy = rng.uniform(0, w), rng.uniform(30, h * 0.35)
        for j in range(6):
            r = rng.uniform(20, 55); ox, oy = cx + rng.uniform(-80, 80), cy + rng.uniform(-14, 14)
            d.ellipse((ox - r, oy - r * 0.6, ox + r, oy + r * 0.6), fill=(255, 255, 255, 150))
    im = im.filter(ImageFilter.GaussianBlur(2))
    d = ImageDraw.Draw(im, 'RGBA')
    if hills:
        for (base, amp, col, f) in ((0.58, 0.10, (130, 150, 178), 3.1), (0.70, 0.08, (96, 138, 82), 5.3), (0.82, 0.05, (74, 120, 58), 7.7)):
            pts = [(0, h)]
            for i in range(0, w + 16, 16):
                t = i / w
                yy = h * (base - amp * (0.6 * math.sin(t * f * 6.283 + seed) + 0.4 * math.sin(t * f * 2.3 * 6.283 + seed * 2)))
                pts.append((i, yy))
            pts.append((w, h)); d.polygon(pts, fill=col)
        for k in range(70):
            tx, ty = rng.uniform(0, w), h * rng.uniform(0.72, 0.95)
            s = rng.uniform(6, 14)
            d.ellipse((tx - s, ty - 2.2 * s, tx + s, ty), fill=(50, 92, 46))
    return np.asarray(im, np.float32)


def basement_view_tex(w=2048, h=1024):
    """what you see past the acrylic guard: the dim basement - boiler, stairs, shelves, washing machine"""
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (46, 44, 42)); d = ImageDraw.Draw(im)
    for yy in range(0, h, 40): d.line((0, yy, w, yy), fill=(54, 52, 50), width=2)
    d.rectangle((0, int(h * 0.82), w, h), fill=(64, 60, 56))
    d.rectangle((160, 380, 420, 840), fill=(140, 140, 136)); d.rectangle((190, 420, 390, 600), outline=(90, 90, 90), width=6)
    d.ellipse((230, 640, 350, 760), fill=(60, 60, 64))                                   # washing machine
    for k in range(10):                                                                  # stairs up to the house
        d.rectangle((760 + k * 50, 840 - k * 46, 1000 + k * 50, 860 - k * 46), fill=(96, 70, 46))
    d.rectangle((1500, 200, 1900, 840), fill=(70, 60, 50))
    for k in range(4):
        d.rectangle((1500, 260 + k * 150, 1900, 272 + k * 150), fill=(110, 90, 70))
        for j in range(5): d.rectangle((1520 + j * 74, 200 + k * 150, 1570 + j * 74, 258 + k * 150), fill=(120 + j * 20, 80, 60))
    d.rectangle((1150, 80, 1350, 200), fill=(150, 170, 190)); d.rectangle((1150, 80, 1350, 200), outline=(90, 90, 90), width=8)
    return np.asarray(im, np.float32)


def pegboard_tex(n=256):
    a = TL.solid((176, 140, 100), 3, 7, n)
    x, y = ML.xy(n)
    holes = (np.hypot((x * 8) % 1 - 0.5, (y * 8) % 1 - 0.5) < 0.12)
    return np.where(holes[..., None], ML.C((40, 30, 22)), a)


def ruler_tex(w=1024, h=128):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (222, 196, 140)); d = ImageDraw.Draw(im)
    for k in range(301):
        x = int(k * w / 300); L = 50 if k % 10 == 0 else (32 if k % 5 == 0 else 18)
        d.line((x, 0, x, L), fill=(30, 26, 20), width=2)
        if k % 10 == 0 and 0 < k < 300: d.text((x + 3, 52), str(k // 10), font=ML.font(22, False), fill=(30, 26, 20))
    d.text((w - 220, 96), 'PADMAN  30cm', font=ML.font(20, False), fill=(120, 30, 30))
    return np.asarray(im, np.float32)


def kitbox_tex(w=1024, h=512):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (232, 226, 210)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 90), fill=(30, 70, 140)); d.rectangle((0, h - 60, w, h), fill=(30, 70, 140))
    d.text((40, 45), 'PADMAN MODELS', font=ML.font(48, False), fill=(250, 250, 250), anchor='lm')
    d.text((w - 40, 45), 'H0 1:87', font=ML.font(48, False), fill=(250, 220, 80), anchor='rm')
    d.rectangle((60, 130, 640, 400), fill=(150, 190, 220))
    d.rectangle((140, 250, 560, 380), fill=(150, 80, 60)); d.polygon([(120, 250), (350, 160), (580, 250)], fill=(80, 84, 96))
    for k in range(4): d.rectangle((180 + k * 95, 290, 230 + k * 95, 350), fill=(250, 230, 160))
    d.text((840, 210), 'PADVILLE', font=ML.font(64, True), fill=(30, 30, 30), anchor='mm')
    d.text((840, 290), 'STATION', font=ML.font(64, True), fill=(30, 30, 30), anchor='mm')
    d.text((840, 360), 'kit  no. 5520', font=ML.font(34, False), fill=(80, 80, 80), anchor='mm')
    return np.asarray(im, np.float32)


def shop_sign(text, bg, fg):
    return TL.label(text, 1024, 128, bg, fg, serif=True, border=fg)


def textures():
    TX.add('grass', grass_tex(), steps='softsteps')
    TX.add('grass2', grass_tex(seed=9) * np.array([1.06, 1.0, 0.82]), steps='softsteps')
    TX.add('road', TL.grime(TL.solid((70, 70, 74), 8, 11, 256), 0.2, 12))
    TX.add('paving', TL.tiles((176, 168, 152), (120, 112, 100), cols=6, rows=6, offset=0.5, grout_w=0.04, vary=10))
    TX.add('footpath', TL.tiles((150, 144, 136), (110, 104, 98), cols=4, rows=4, offset=0.0, grout_w=0.03, vary=6, seed=14))
    TX.add('ballast', TL.stone((120, 112, 104), cells=60, edge=(70, 66, 62), edge_w=0.02, vary=22, seed=15), steps='sandsteps')
    TX.add('platform', TL.tiles((196, 192, 182), (150, 146, 140), cols=4, rows=4, offset=0.0, grout_w=0.025, vary=6, seed=16))
    TX.add('platedge', TL.stripes((236, 210, 60), (210, 206, 196), 2, True, 0.0, 17))
    TX.add('rock', TL.grime(TL.stone((150, 138, 120), cells=14, edge=(96, 86, 74), edge_w=0.02, vary=18, seed=18), 0.3, 19))
    TX.add('rock_top', grass_tex(seed=21) * np.array([0.92, 1.0, 0.86]), steps='softsteps')
    TX.add('rock_dark', TL.grime(TL.stone((92, 86, 80), cells=12, edge=(56, 52, 48), seed=22), 0.4, 23))
    TX.add('snow', TL.frost((236, 240, 246), 24), steps='snowsteps')
    TX.add('mat', mat_tex(), scale=1.0)
    TX.add('bench', TL.planks((206, 170, 120), 5, (150, 116, 76), 10, True, False, 25), steps='woodsteps')
    TX.add('fascia', TL.solid((40, 70, 46), 4, 26, 128))
    TX.add('plywood', TL.planks((196, 168, 126), 3, (160, 130, 92), 16, False, False, 27))
    TX.add('joist', TL.planks((206, 176, 130), 2, (170, 140, 100), 16, False, False, 28))
    TX.add('wallb', TL.grime(TL.bricks((150, 148, 142), (120, 118, 112), rows=8, cols=3, vary=8, seed=29), 0.25, 30))
    TX.add('ceiling', TL.planks((214, 212, 204), 4, (170, 168, 160), 6, False, False, 31))
    TX.add('voidfloor', TL.solid((48, 46, 44), 6, 32, 128))
    TX.add('lakebed', TL.stone((150, 136, 100), cells=40, edge=(110, 98, 70), seed=33), steps='sandsteps')
    TX.add('stairtread', TL.planks((150, 112, 72), 2, (90, 64, 40), 8, False, False, 34), steps='woodsteps')
    TX.add('stairside', TL.solid((120, 90, 60), 4, 35, 128))
    TX.add('ruler_top', ruler_tex(), check_tile=False)
    TX.add('ruler_side', TL.solid((200, 172, 120), 3, 36, 128))
    TX.add('shelf', TL.planks((186, 150, 104), 3, (130, 100, 66), 8, False, False, 37), steps='woodsteps')
    TX.add('tin', TL.metal((176, 178, 184), True, 38))
    TX.add('steelrule', TL.metal((200, 202, 206), True, 39))
    TX.add('water', TL.solid((60, 120, 140), 10, 40, 128), 'water', rgb=(0.28, 0.48, 0.52), alpha=0.6)
    TX.add('coffee', TL.solid((70, 40, 24), 6, 41, 128), 'water', rgb=(0.28, 0.16, 0.08), alpha=0.85)
    TX.add('acrylic', TL.solid((200, 220, 230), 2, 42, 64), 'glass', rgb='0.06 0.07 0.08')
    TX.add('tube', TL.solid((250, 250, 240), 2, 43, 64), 'neon', rgb=(1.0, 0.98, 0.9), light=0)
    TX.add('backdrop_n', backdrop_tex(seed=3), 'sign', check_tile=False)
    TX.add('backdrop_w', backdrop_tex(seed=7), 'sign', check_tile=False)
    TX.add('pegboard', pegboard_tex())
    TX.add('rock_fake', TL.grime(TL.stone((92, 86, 80), cells=12, edge=(56, 52, 48), seed=22), 0.4, 23), 'raw',
           shader=SH.fake_wall('rock_fake', f'textures/{NS}/rock_fake'), check_tile=False)
    TX.add('vault', TL.grime(TL.metal((168, 170, 176), True, 44), 0.2, 45))
    for key, text, bg, fg in (('sign_bakery', 'PAD BAKERY', (120, 40, 30), (250, 230, 170)),
                              ('sign_toys', 'TOYS & MODELS', (30, 60, 120), (250, 240, 200)),
                              ('sign_post', 'POST OFFICE', (180, 30, 30), (250, 220, 90)),
                              ('sign_goods', 'PADVILLE COAL & TIMBER', (40, 40, 40), (240, 230, 200)),
                              ('sign_shed', 'PADVILLE LOCO DEPOT', (30, 60, 40), (240, 230, 200)),
                              ('sign_farm', 'DUCKPOND FARM', (120, 70, 30), (250, 240, 210)),
                              ('sign_mill', 'OLD MILL', (60, 50, 40), (240, 230, 200))):
        TX.add(key, shop_sign(text, bg, fg), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(250, 200, 60), rubber=(50, 54, 60))


def building_mats():
    M = TX.material
    M('brick', TL.bricks((150, 70, 52), (190, 180, 166), rows=8, cols=4, vary=18, seed=46), shade=20)
    M('brick_y', TL.bricks((196, 170, 120), (220, 210, 190), rows=8, cols=4, vary=14, seed=47), shade=20)
    M('render', TL.solid((232, 222, 196), 5, 48, 128), shade=20)
    M('render_pink', TL.solid((228, 190, 180), 5, 49, 128), shade=20)
    M('stone_ch', TL.stone((168, 164, 156), 18, (120, 116, 110), seed=50), shade=20)
    M('slate', TL.tiles((70, 74, 84), (44, 46, 54), cols=6, rows=12, offset=0.5, vary=10, seed=51), shade=20)
    M('tile_red', TL.tiles((156, 72, 52), (96, 44, 32), cols=6, rows=10, offset=0.5, vary=14, seed=52), shade=20)
    M('trim', TL.solid((240, 238, 230), 3, 53, 64), shade=20)
    M('plaster', TL.solid((236, 230, 216), 4, 54, 128), shade=20)
    M('wallpaper', TL.stripes((214, 200, 170), (196, 180, 150), 10, True, 0.3, 55), shade=20)
    M('boards', TL.planks((160, 116, 74), 6, (96, 66, 40), 10, True, False, 56), shade=20, steps='woodsteps')
    M('barn_red', TL.planks((150, 50, 40), 6, (90, 30, 24), 8, False, True, 57), shade=20)
    M('shed_brick', TL.bricks((110, 60, 46), (150, 140, 128), rows=8, cols=4, vary=16, seed=58), shade=20)
    M('roof_felt', TL.grime(TL.solid((74, 76, 80), 6, 59, 128), 0.2, 60), shade=20)
    M('card_out', kitbox_tex(), shade=20)
    M('card_in', TL.solid((176, 140, 96), 5, 61, 128), shade=20)
    M('card_edge', TL.stripes((196, 160, 110), (170, 134, 90), 16, False, 0.4, 62), shade=20)
    M('canvas_r', TL.stripes((200, 40, 40), (240, 236, 226), 8, True, 0.0, 63), shade=60, two=True)
    M('canvas_b', TL.stripes((40, 80, 170), (240, 236, 226), 8, True, 0.0, 64), shade=60, two=True)
    M('canvas_g', TL.stripes((40, 130, 70), (240, 236, 226), 8, True, 0.0, 65), shade=60, two=True)
    M('metal', TL.metal((120, 122, 126), True, 66), shade=40)


# ================================================================================================ structure
def shell():
    """structural hull: baseboard slab (holes: lake, hatches, turntable pit), basement walls, ceiling, the void past
    the acrylic guard with the basement painted on its far wall. Everything else is detail."""
    holes = [LAKE, (H1[0] - HH, H1[1] - HH, H1[0] + HH, H1[1] + HH), (H2[0] - HH, H2[1] - HH, H2[0] + HH, H2[1] + HH),
             (TT_C[0] - TT_R, TT_C[1] - TT_R, TT_C[0] + TT_R, TT_C[1] + TT_R)]
    side = T('fascia')
    for r in sub_rects((X0, Y0, BX, Y1), holes):
        K.add(box((r[0], r[1], -48), (r[2], r[3], 0), {'top': T('grass'), 'side': side, 'bot': T('plywood')}, detail=False))
    MAT = (1200, -1000, 2200, 900)
    for r in sub_rects((BX, Y0, X1, Y1), [MAT]):
        K.add(box((r[0], r[1], -48), (r[2], r[3], 0), {'top': T('bench'), 'side': T('bench'), 'bot': T('bench')}, detail=False))
    K.add(box((MAT[0], MAT[1], -48), (MAT[2], MAT[3], 0), {'top': T('mat'), 'side': T('bench'), 'bot': T('bench')}, detail=False))
    # basement walls (north, west, east) + the void walls
    K.add(box((X0 - 32, Y1, -48), (X1 + 32, Y1 + 32, ZC), tex6(s=T('wallb')), detail=False))
    K.add(box((X0 - 32, VY - 32, VZ - 32), (X0, Y1, ZC), tex6(e=T('wallb')), detail=False))
    K.add(box((X1, VY - 32, VZ - 32), (X1 + 32, Y1, ZC), tex6(w=T('wallb')), detail=False))
    K.add(box((X0, VY - 32, VZ - 32), (X1, VY, ZC), tex6(n=T('wallb')), detail=False))
    K.add(box((X0, VY, VZ - 32), (X1, Y0, VZ), tex6(top=T('voidfloor')), detail=False))
    K.add(box((X0, Y0, VZ - 32), (X1, Y0 + 16, -48), tex6(s=T('fascia')), detail=False))      # benchwork front: seals under the slab
    K.add(box((X0 - 32, VY - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # painted scenery: backdrops behind the layout, the basement beyond the acrylic
    K.add(sign_box((X0, Y1 - 8, 0), (BX, Y1, 1500), T('backdrop_n'), 2048, 768, facing='s', edge=T('fascia')))
    K.add(sign_box((X0, Y0 + 8, 0), (X0 + 8, Y1 - 8, 1500), T('backdrop_w'), 2048, 768, facing='e', edge=T('fascia')))
    # acrylic safety guard along the open south edge + player clip to the ceiling
    K.add(box((X0, Y0, 0), (X1, Y0 + 8, 320), T('acrylic')))
    K.add(box((X0, Y0, 320), (X1, Y0 + 8, ZC), CLIP))
    K.reserve(((X0, Y0, 0), (X1, Y0 + 24, 320)))
    # fluorescent tubes on the ceiling
    for x in range(-2400, 1800, 900):
        for y in (-1200, 0, 1200):
            K.add(box((x, y - 12, ZC - 24), (x + 480, y + 12, ZC), {'bot': T('tube'), 'side': T('tube'), 'top': CAULK}))
    # the layout's front fascia shows below the acrylic as a painted edge (the slab's south face)


def underworld():
    """under the baseboard: a storage shelf at z -600 between the joists, wiring, point motors, stored boxes"""
    x0, y0, x1, y1 = U; z = UZ
    t = {'side': T('wallb'), 'top': T('plywood'), 'bot': CAULK}
    K.add(box((x0 - 16, y0 - 16, z - 16), (x1 + 16, y1 + 16, z), {'top': T('plywood'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((x0 - 16, y0 - 16, z), (x0, y1 + 16, -48), tex6(e=T('wallb')), detail=False))
    K.add(box((x1, y0 - 16, z), (x1 + 16, y1 + 16, -48), tex6(w=T('wallb')), detail=False))
    K.add(box((x0, y0 - 16, z), (x1, y0, -48), tex6(n=T('wallb')), detail=False))
    K.add(box((x0, y1, z), (x1, y1 + 16, -48), tex6(s=T('wallb')), detail=False))
    # joists (hang from the baseboard; 256u headroom under them)
    for jx in (-950, -400):
        b = box((jx - 42, y0, -344), (jx + 42, y1, -48), {'side': T('joist'), 'bot': T('joist'), 'top': CAULK})
        K.add(b); K.reserve(b)
    # point motors, cables, a bulb, cobwebs (hanging decoration)
    for (x, y) in ((-1150, -950), (-700, -1000), (-250, -800), (-700, -350)):
        deco('point_motor', x, y, -48, angle=30)
    for nm, (cx, cy) in CABLES.items(): deco(nm, cx, cy, 0)
    for (x, y) in ((-680, -880), (-1120, -400)):
        deco('bulb', x, y, -48, lit=False)
        K.light(x, y, -330, 1100, '1 0.85 0.6')
    # stored boxes + a 9V battery as cover, a giant spider in the corner
    place('locobox', -760, -1020, z, 0)
    place('battery9v', -1050, -760, z, 20)
    place('battery9v', -560, -420, z, -35)
    K.catalog('spider/spider.md3', -300, -650, z, scale=4.5, angle=135, lit=True)
    K.catalog('pad_ddmix/backyard/screw_nut.md3', -900, -380, z, scale=4.0, lit=True)
    for (x, y) in ((-1150, -1000), (-300, -350), (-300, -1050)):
        K.light(x, y, -380, 700, '0.9 0.8 0.7')
    K.speaker(-700, -700, -400, 'machine/electric_sizzle')
    K.speaker(-300, -900, -400, 'machine/transformer')


def hatches():
    """lift-out access panels: H1 is a drop into the underworld, H2 has the lift pad back up under it"""
    for (cx, cy), ang in ((H1, 200), (H2, 160)):
        K.keep_clear(cx - HH - 40, cy - HH - 40, cx + HH + 40, cy + HH + 40, 0)
    place('hatchlid', H1[0] + 20, H1[1] + HH + 60, 2, 0)
    place('hatchlid', H2[0] - 30, H2[1] - HH - 72, 2, 180)
    K.jumppad(H2[0] - 60, H2[1], UZ, land=(H2[0] + 280, H2[1], 2), apex=400, name='pad_hatch', dress=ML.PLACE['pad_spring'],
              edges=[(H2[0] + HH, H2[1], 0)])


def lake():
    """lake sunk into the baseboard: structural basin, detail shore carved round an elliptical water body, 16u steps
    out at the north-east, a jetty, the water mill wheel turning in it"""
    x0, y0, x1, y1 = LAKE
    K.add(box((x0 - 16, y0 - 16, LBED - 16), (x1 + 16, y1 + 16, LBED), {'top': T('lakebed'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((x0 - 16, y0 - 16, LBED), (x0, y1 + 16, -48), tex6(e=T('rock')), detail=False))
    K.add(box((x1, y0 - 16, LBED), (x1 + 16, y1 + 16, -48), tex6(w=T('rock')), detail=False))
    K.add(box((x0, y0 - 16, LBED), (x1, y0, -48), tex6(n=T('rock')), detail=False))
    K.add(box((x0, y1, LBED), (x1, y1 + 16, -48), tex6(s=T('rock')), detail=False))
    poly = [(LAKE_C[0] + LRX * math.cos(a), LAKE_C[1] + LRY * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
    water_hull = prism(poly, LBED, LWAT, T('water'))
    cut_hull = prism(poly, LBED, 8, T('water'))
    st = K.stairs16(-1612, 80, -1356, 200, LBED, 0, 'e', {'top': T('stairtread'), 'side': T('rock')})
    shore = box((x0, y0, LBED), (x1, y1, 0), {'top': T('grass2'), 'side': T('rock'), 'bot': CAULK})
    for p in carve(shore, [cut_hull] + st):
        for f in p.faces:
            f.tex = T('grass2') if (f.n[2] > 0.7 and abs(f.d) < 0.5) else (CAULK if f.n[2] < -0.7 else T('rock'))
        K.add(p)
    for p in carve(water_hull, st):
        for f in p.faces: f.tex = T('water') if (f.n[2] > 0.9 and abs(f.d - LWAT) < 0.5) else T('water_nd')
        K.add(p)
    K.spots.setdefault('water', []).append(dict(mn=[LAKE[0], LAKE[1], LBED], mx=[LAKE[2], LAKE[3], LWAT], depth=LWAT - LBED))
    K.reserve(((x0, y0, LBED), (x1, y1, 8)))
    K.keep_clear(-1356, 60, -1260, 220, 0)
    K.speaker(-1400, -170, 40, 'ambient/water_rippling')
    # lily pads + a reed bed as catalog plants
    for (x, y) in ((-1850, 150), (-1600, -420), (-1780, -300)):
        K.catalog('pad_ddmix/plants/water_lily.md3', x, y, LWAT, scale=0.6, clip=False, nudge=False)


# ================================================================================================ the railway
def railway():
    """ballast ring, track MD3 arcs, the two platforms with their step bands, the station plinth"""
    for b in sector(BAL[0], BAL[1], 0, 360, 0, 12, {'top': T('ballast'), 'side': T('ballast'), 'bot': CAULK}, step=7.5):
        K.add(b)
    RW.track_ring(K, 'track_arc', C, R, 12, TX['rail'], TX['sleeper'], gauge=69.0, n=24)
    plinth = box((-1302, -1150, 0), (-362, -850, 48), {'top': T('platform'), 'side': T('platedge'), 'bot': CAULK})
    K.add(plinth); K.reserve(plinth)
    ptex = {'top': T('platform'), 'side': T('platedge'), 'bot': CAULK}
    stx = {'top': T('footpath'), 'side': T('platedge'), 'bot': CAULK}
    pieces = sector(1150, 1376, 232, 308, 0, 48, ptex, step=4) + sector(1118, 1150, 232, 308, 0, 32, stx, step=4) + \
        sector(1086, 1118, 232, 308, 0, 16, stx, step=4)
    for p in pieces:
        top = next(f.tex for f in p.faces if f.n[2] > 0.7)
        for q in carve(p, [plinth]):
            for f in q.faces: f.tex = top if f.n[2] > 0.7 else (CAULK if f.n[2] < -0.7 else T('platedge'))
            K.add(q); K.reserve(q)
    outer = sector(1624, 1780, 240, 300, 0, 48, ptex, step=4) + sector(1780, 1812, 240, 300, 0, 32, stx, step=4) + \
        sector(1812, 1844, 240, 300, 0, 16, stx, step=4)
    for p in outer:
        K.add(p); K.reserve(p)
    K.route('plat_in', (P(238, 1040)[0], P(238, 1040)[1], 0), (P(238, 1260)[0], P(238, 1260)[1], 48))
    K.route('plat_out', (P(285, 1900)[0], P(285, 1900)[1], 0), (P(285, 1700)[0], P(285, 1700)[1], 48))
    # station steps from the plaza
    K.reserve(K.stairs16(-1000, -850, -640, -754, 0, 48, 's', {'top': T('footpath'), 'side': T('platedge')}))
    K.route('station_steps', (-820, -650, 2), (-744, -950, 52))
    # level crossing posts + buffer stops in the depot
    place('xing_post', P(0, 1340)[0], 140, 0, 180)
    place('xing_post', P(0, 1660)[0], -140, 0, 0)
    K.timer_sound(C[0] + R, 0, 100, 'machine/dingdong', 'xing_bell', 30, 15)


def train():
    cars = [RW.Car('loco', PM.loco(), -300, 300, 196, 72)]
    for k in range(3):
        cars.append(RW.Car('coach', PM.coach('coach_side' if k != 1 else 'coach_side2'), -290, 290, 198, 72))
    TR = RW.CircleTrain(K, 'express', C, R, RAIL_Z, cars, front_deg=200.0, speed=6.0)
    TR.build()
    for a in (100, 270, 30, 160):
        x, y = P(a, R)
        K.speaker(x, y, 260, 'machine/mechanics')
    K.timer_sound(C[0], C[1], 600, 'ambient/train_intercity', 'train_horn', 40, 20)
    return TR


def mountain():
    """three rock tiers (flat tops: bots walk them) north of the town, the tunnel bored through T1 along the circle,
    stone portals at both mouths, 16u stairs between tiers, the secret refuge niche in the tunnel"""
    A = P(125, 900 / math.sin(math.radians(125))); B = P(55, 900 / math.sin(math.radians(55)))
    Cc = P(55, 1800); Fp = P(125, 1800)
    t1 = [A, B, Cc, (Cc[0], 2040), (-1924, 2040), Fp]
    t2 = [(-1650, 1450), (-150, 1450), (-60, 1650), (-60, 2040), (-1780, 2040), (-1790, 1650)]
    t3 = [(-1200, 1700), (-600, 1700), (-560, 1800), (-560, 2040), (-1240, 2040), (-1240, 1800)]
    rock = lambda top: (lambda n: top if n[2] > 0.7 else (CAULK if n[2] < -0.7 else T('rock')))
    b1 = prism(t1, 0, 400, rock(T('rock_top'))); b2 = prism(t2, 400, 640, rock(T('rock_top')))
    b3 = prism(t3, 640, 832, rock(T('snow')))
    # tunnel bore along the circle, 50..130 deg, R 1350..1650, z 0..320 (roof >= car top + 80 for riders)
    cut = []
    for a in np.arange(50, 130, 5.0):
        pts = []
        for aa in (a - 0.2, a + 5.2):
            for r in (1350, 1650 / math.cos(math.radians(2.7))):
                x, y = P(aa, r); pts += [(x, y, -1), (x, y, 320)]
        cut.append(hull(pts, T('rock_dark'), round_pts=False))
    # secret refuge niche (north wall at 90 deg) + the passage behind the fake wall
    niche = box((C[0] - 48, 1640, -1), (C[0] + 48, 1730, 128), T('rock_dark'))
    passage = box((C[0] - 48, 1746, -1), (C[0] + 48, 1960, 128), T('rock_dark'))
    slot = box((C[0] - 48, 1730, -1), (C[0] + 48, 1746, 128), T('rock_dark'))
    for p in carve(b1, cut + [niche, slot, passage]):
        for f in p.faces:
            if f.n[2] > 0.7 and abs(f.d - 400) < 0.5: f.tex = T('rock_top')
            elif f.n[2] > 0.7: f.tex = T('ballast')
            elif f.n[2] < -0.7: f.tex = CAULK if abs(f.d) < 0.5 else T('rock_dark')
            else:
                v = p.verts(); onf = v[np.abs(v @ np.array(f.n) - f.d) < 0.1]
                f.tex = T('rock') if onf[:, 2].max() > 330 else T('rock_dark')
        K.add(p)
    K.add(b2, b3)
    for b in (b1, b2, b3): K.reserve(b)
    K.add(box((C[0] - 48, 1730, 0), (C[0] + 48, 1746, 128), T('rock_fake')))
    K.secret((C[0] - 40, 1860, 0), (C[0] + 40, 1950, 96), dest=(VAULT[0] + 120, (VAULT[1] + VAULT[3]) / 2, VAZ), angle=0,
             name='refuge', approach='s')
    K.light(C[0], 1800, 100, 160, '1 0.8 0.5')
    # tunnel lamps
    for a in range(56, 126, 7):
        x, y = P(a, 1500)
        K.light(x, y, 300, 650, '1 0.85 0.55')
    # portals (outside each radial face)
    for (a, sgn) in ((55, -1), (125, 1)):
        ar = math.radians(a)
        nrm = (sgn * -math.sin(ar), sgn * math.cos(ar))          # out of the hill
        ang = math.degrees(math.atan2(nrm[1], nrm[0]))
        x, y = P(a, R)
        place('tunnel_portal', x, y, 0, ang)
    # stairs: ground -> T1 (north-east), T1 -> T2, T2 -> T3
    rt = {'top': T('rock_top'), 'side': T('rock')}
    K.stairs16(200, 1900, 1000, 2020, 0, 400, 'w', rt)
    K.route('stairs_t1', (1060, 1960, 0), (140, 1960, 400))
    K.keep_clear(1000, 1880, 1100, 2030, 0)
    K.stairs16(-400, 970, -280, 1450, 400, 640, 'n', rt)
    K.route('stairs_t2', (-340, 930, 400), (-340, 1500, 640))
    K.stairs16(-1624, 1760, -1240, 1880, 640, 832, 'e', rt)
    K.route('stairs_t3', (-1680, 1820, 640), (-1180, 1820, 832))
    for (x0, y0, x1, y1, z) in ((-400, 900, -280, 970, 400), (-1690, 1760, -1624, 1880, 640)):
        K.keep_clear(x0, y0, x1, y1, z)
    # pads: churchyard -> T1, T1 -> T2, T2 -> T3, farm -> T1 west
    K.jumppad(-832, 760, 0, land=(-832, 1150, 400), apex=720, name='pad_t1', dress=ML.PLACE['pad_manhole'], edges=[(-832, 900, 400)])
    K.jumppad(-1100, 1080, 400, land=(-1100, 1600, 640), apex=800, name='pad_t2', dress=ML.PLACE['pad_vent'], dress_light=140, dress_rgb='1 0.6 0.3', edges=[(-1100, 1450, 640)])
    K.jumppad(-900, 1520, 640, land=(-900, 1860, 832), apex=990, name='pad_t3', dress=ML.PLACE['pad_vent'], dress_light=140, dress_rgb='1 0.6 0.3', edges=[(-900, 1700, 832)])
    K.jumppad(-2100, 1250, 0, land=(-1620, 1300, 400), apex=600, name='pad_t1w', dress=ML.PLACE['pad_manhole'], edges=[(-1740, 1290, 400)])


# ================================================================================================ buildings
def awning_dress(name, wall_x, spans, z_top, key):
    D = SB.Dress(K, name, origin=(wall_x, 0, 0))
    w = D.wall((wall_x, 0), 'w')
    for (a, b) in spans:
        SB.awning(D, w, TX[key], TX['metal'], w.uof(b), w.uof(a), z_top, depth=80, drop=26)
    D.finish()


def buildings():
    mk = lambda **m: {k: TX[v] for k, v in m.items()}
    # ---- Padville station (on its plinth, 2 storeys, flat roof with stairs up through a hatch)
    st = town.Building(K, 'station', (-1286, -1134, -378, -866), 48, (192, 160),
                       mk(ext='brick_y', int='wallpaper', trim='trim', floor='boards', roofflat='roof_felt', ceil='plaster'),
                       doors=[('n', -800, -688), ('s', -800, -688), ('s', -560, -448)],
                       stairs=[(-1200, -1000, -816, -882, 'e')], roof='flat', roof_stairs=(-792, -1118, -440, -1000, 'e'))
    st.build()
    # canopy: walkable slab over the inner platform (posts as MD3)
    can = box((-1286, -1300, 240), (-378, -1134, 252), {'top': T('platform'), 'bot': T('fascia'), 'side': T('fascia')})
    K.add(can); K.reserve(can)
    for x in np.linspace(-1240, -420, 5):
        K.add(cyl(x, -1280, 8, 48, 240, WCLIP, 8))
        deco('canopy_post', x, -1280, 48, 0)
    K.speaker(-900, -1000, 140, 'machine/clock_ticking')
    # ---- church nave + tower
    ch = town.Building(K, 'church', (-1250, 260, -610, 580), 0, (256,),
                       mk(ext='stone_ch', int='plaster', trim='trim', floor='boards', roof='slate', ceil='plaster', gable='stone_ch'),
                       doors=[('w', 364, 476), ('s', -980, -868), ('e', 364, 476)], roof='gable_x', gable_ext=(16, 0),
                       windows={'n': [(-1150, -1080, 0, 80, 220), (-980, -910, 0, 80, 220), (-810, -740, 0, 80, 220)],
                                's': [(-1150, -1080, 0, 80, 220), (-780, -710, 0, 80, 220)]})
    ch.build()
    tw = town.Building(K, 'tower', (-610, 228, -226, 612), 0, (720,),
                       mk(ext='stone_ch', int='plaster', trim='trim', floor='boards', roofflat='slate', ceil='plaster'),
                       doors=[('w', 364, 476), ('s', -500, -388)], roof='flat', hatch=(-578, 308, -354, 532),
                       windows={'n': [(-470, -366, 0, 520, 640)], 's': [(-300, -250, 0, 520, 640)], 'e': [(368, 472, 0, 520, 640)]})
    tw.build()
    K.jumppad(-560, 420, 4, land=(-290, 420, 736), apex=1000, name='pad_tower', dress=ML.PLACE['pad_trapdoor'], edges=[(-354, 420, 736)])
    K.jumppad(-1180, 700, 0, land=(-1000, ch.ridge[1], ch.roof_top), apex=ch.roof_top + 140, name='pad_nave', dress=ML.PLACE['pad_manhole'],
              edges=[(-1100, 580, 256)])
    K.timer_sound(-418, 420, 650, 'machine/dingdong', 'church_bell', 45, 20)
    # pews inside the nave
    for x in (-1180, -1080, -780, -700):
        for y in (340, 500):
            b = box((x, y - 40, 4), (x + 36, y + 40, 40), {'top': T('stairtread'), 'side': T('stairside'), 'bot': CAULK})
            K.add(b); K.reserve(b)
    # ---- houses (2 storeys, gable roofs, stairs inside)
    h1 = town.Building(K, 'house1', (-130, 240, 318, 560), 0, (160, 160),
                       mk(ext='brick', int='wallpaper', trim='trim', floor='boards', roof='tile_red', ceil='plaster', gable='brick'),
                       doors=[('s', 30, 142), ('e', 300, 412)], stairs=[(-66, 440, 254, 544, 'e')], roof='gable_x', no_windows='n')
    h1.build()
    h2 = town.Building(K, 'house2', (800, 380, 1100, 828), 0, (160, 160),
                       mk(ext='render_pink', int='wallpaper', trim='trim', floor='boards', roof='slate', ceil='plaster', gable='render_pink'),
                       doors=[('w', 440, 552), ('s', 900, 1012)], stairs=[(990, 444, 1084, 764, 'n')], roof='gable_y', no_windows='e')
    h2.build()
    K.jumppad(60, 680, 0, land=(100, h1.ridge[1], h1.roof_top), apex=h1.roof_top + 140, name='pad_house1', dress=ML.PLACE['pad_manhole'], edges=[(80, 560, 320)])
    K.jumppad(1070, 230, 0, land=(h2.ridge[1], 500, h2.roof_top), apex=h2.roof_top + 160, name='pad_house2', dress=ML.PLACE['pad_manhole'],
              edges=[(1000, 364, h2.roof_top)])
    # ---- shop row (flat roof, stairs inside, awnings + signs on the plaza side)
    sh = town.Building(K, 'shops', (-100, -800, 200, -150), 0, (176, 160),
                       mk(ext='render', int='plaster', trim='trim', floor='boards', roofflat='roof_felt', ceil='plaster'),
                       doors=[('w', -700, -588), ('w', -420, -308)], stairs=[(80, -716, 184, -364, 'n')],
                       roof='flat', roof_stairs=(-84, -652, 20, -300, 's'),
                       windows={'w': [(-560, -440, 0, 48, 136), (-280, -180, 0, 48, 136), (-760, -720, 0, 48, 136),
                                      (-700, -600, 1), (-420, -320, 1), (-260, -180, 1)],
                                'e': [(-700, -620, 1), (-400, -320, 1)], 'n': [(10, 90, 1)], 's': [(10, 90, 1)]})
    sh.build()
    for (y0, y1, key) in ((-790, -560, 'sign_bakery'), (-520, -330, 'sign_toys'), (-300, -165, 'sign_post')):
        K.add(sign_box((-106, y0, 182), (-100, y1, 226), T(key), 1024, 128, facing='w', edge=T('fascia')))
    awning_dress('shop_awnings', -100, [(-790, -560), (-520, -330), (-300, -165)], 172, 'canvas_r')
    # ---- water mill by the lake
    ml = town.Building(K, 'mill', (-1340, -300, -1120, -40), 0, (176,),
                       mk(ext='stone_ch', int='plaster', trim='timber', floor='boards', roof='tile_red', ceil='plaster', gable='stone_ch'),
                       doors=[('e', -230, -118)], roof='gable_y', no_windows='w')
    ml.build()
    K.rotating_model2(ML.PLACE['waterwheel'][0], (-1395, -170, 90), 20, axis='x')
    K.add(sign_box((-1120, -260, 126), (-1116, -120, 162), T('sign_mill'), 1024, 128, facing='e', edge=T('fascia')))
    K.speaker(-1395, -170, 60, 'ambient/water_flowing')
    # ---- signal box (flat roof, outside stairs)
    sb = town.Building(K, 'sigbox', (-2400, -1300, -2160, -1060), 0, (192,),
                       mk(ext='brick', int='plaster', trim='trim', floor='boards', roofflat='roof_felt', ceil='plaster'),
                       doors=[('e', -1236, -1124)], roof='flat',
                       windows={'n': [(-2370, -2190, 0, 70, 160)], 's': [(-2370, -2190, 0, 70, 160)], 'w': [(-1240, -1120, 0, 70, 160)]})
    sb.build()
    K.stairs16(-2528, -1476, -2400, -1060, 0, 208, 'n', {'top': T('stairtread'), 'side': T('stairside')})
    K.route('sigbox_roof', (-2464, -1530, 0), (-2280, -1180, 208))
    K.keep_clear(-2528, -1540, -2400, -1476, 0)
    # ---- goods shed (coal & timber yard)
    gs = town.Building(K, 'goods', (-2760, -1960, -2380, -1600), 0, (224,),
                       mk(ext='brick', int='plaster', trim='timber', floor='boards', roof='slate', ceil='timber', gable='brick'),
                       doors=[('e', -1880, -1720), ('n', -2640, -2500)], roof='gable_x', door_h=160)
    gs.build()
    K.add(sign_box((-2380, -1940, 180), (-2376, -1620, 220), T('sign_goods'), 1024, 128, facing='e', edge=T('fascia')))
    K.jumppad(-2300, -1500, 0, land=(-2570, gs.ridge[1], gs.roof_top), apex=gs.roof_top + 150, name='pad_goods', dress=ML.PLACE['pad_manhole'],
              edges=[(-2380, -1700, 240)])
    # ---- barn (hayloft) + windmill
    bn = town.Building(K, 'barn', (-2780, 1300, -2280, 1700), 0, (176, 160),
                       mk(ext='barn_red', int='timber_dark', trim='trim', floor='boards', roof='slate', ceil='timber', gable='barn_red'),
                       doors=[('s', -2600, -2440), ('e', 1440, 1552)], stairs=[(-2720, 1560, -2368, 1680, 'w')], roof='gable_x',
                       door_h=150, no_windows='n')
    bn.build()
    K.add(sign_box((-2690, 1294, 196), (-2370, 1300, 236), T('sign_farm'), 1024, 128, facing='s', edge=T('fascia')))
    place('windmill_tower', -2560, 880, 0, 0)
    K.rotating_model2(ML.PLACE['windmill_sails'][0], (-2450, 880, 560), 18, axis='x')
    K.jumppad(-2350, 1150, 0, land=(-2400, bn.ridge[1], bn.roof_top), apex=bn.roof_top + 190, name='pad_barn', dress=ML.PLACE['pad_manhole'],
              edges=[(-2400, 1280, 352)])
    # ---- engine shed + turntable
    es = town.Building(K, 'loco_shed', (760, -1300, 1120, -620), 0, (256,),
                       mk(ext='shed_brick', int='shed_brick', trim='timber', floor='boards', roof='slate', ceil='timber', gable='shed_brick'),
                       doors=[('s', 900, 1080)], roof='gable_y', door_h=232, floor_mat=False, no_windows='s')
    es.build()
    K.add(sign_box((800, -1306, 240), (1080, -1300, 270), T('sign_shed'), 1024, 128, facing='s', edge=T('fascia')))
    place('loco_static', 860, -936, 0, 90)
    pit = cyl(TT_C[0], TT_C[1], TT_R + 2, -16, 0, T('ballast'), 16)
    K.add(box((TT_C[0] - TT_R, TT_C[1] - TT_R, -48), (TT_C[0] + TT_R, TT_C[1] + TT_R, -16),
              {'top': T('ballast'), 'side': CAULK, 'bot': CAULK}, detail=False))
    corner = box((TT_C[0] - TT_R, TT_C[1] - TT_R, -16), (TT_C[0] + TT_R, TT_C[1] + TT_R, 0),
                 {'top': T('ballast'), 'side': T('rock'), 'bot': CAULK})
    for p in carve(corner, [pit]):
        for f in p.faces: f.tex = T('ballast') if f.n[2] > 0.7 else (CAULK if f.n[2] < -0.7 else T('rock'))
        K.add(p)
    RW.turntable(K, 'turntable', TT_C, TT_R, 0, ML.PLACE['tt_deck'][0], speed=7)
    K.reserve(((TT_C[0] - TT_R, TT_C[1] - TT_R, -16), (TT_C[0] + TT_R, TT_C[1] + TT_R, 60)))
    return dict(station=st, church=ch, tower=tw, house1=h1, house2=h2, shops=sh, mill=ml, sigbox=sb, goods=gs, barn=bn, shed=es)


# ================================================================================================ workbench (giant world)
def workbench():
    # controller + ruler ramp
    place('controller', 1700, 1300, 0, 0)
    K.ramp(1640, 340, 1766, 1100, 0, 300, 'n', {'top': T('ruler_top'), 'side': T('ruler_side'), 'bot': CAULK}, route='ruler')
    K.reserve(((1640, 340, 0), (1766, 1100, 300)))
    K.keep_clear(1640, 240, 1766, 340, 0)
    K.speaker(1700, 1300, 360, 'machine/transformer')
    # desk lamp (Imperius on the shade)
    lamp_base = (2050, 1780); head = (1700, 1000); HT = 960
    X, rs = PM.desk_lamp(lamp_base, (head[0] - lamp_base[0], head[1] - lamp_base[1]), HT)
    mid = ((head[0] - lamp_base[0]) / 2, (head[1] - lamp_base[1]) / 2)
    X.shift((mid[0], mid[1], 0)); ML.save('desk_lamp', X)
    hx, hy = head[0] - lamp_base[0] - mid[0], head[1] - lamp_base[1] - mid[1]
    K.custom(ML.PLACE['desk_lamp'], lamp_base[0] + mid[0], lamp_base[1] + mid[1], 0, 0,
             cyls=[(-mid[0], -mid[1], 200, 0, 60), (hx, hy, rs, HT - 60, HT), (hx, hy, rs + 26, HT - 150, HT - 60),
                   (hx, hy, rs + 60, HT - 214, HT - 150)])
    K.light(head[0], head[1], HT - 260, 2600, '1 0.95 0.8')
    K.jumppad(1560, 1330, 300, land=(head[0], head[1], HT), apex=HT + 120, name='pad_lamp', dress=ML.PLACE['pad_button'], dress_light=110, dress_rgb='1 0.6 0.3', edges=[(head[0], head[1] + rs, HT)])
    # tipped-over mug + spilled coffee
    mx, my = 1650, -760
    K.custom(ML.PLACE['mug'], mx, my, 0, 0, occupy=False)
    for pts in PM.mug_slabs():
        K.add(hull([(mx + p[0], my + p[1], p[2]) for p in pts], WCLIP, round_pts=False))
    K.add(box((mx - 24, my + 400 * 0.2, 2 * 170 + 6), (mx + 24, my + 400 * 0.8, 2 * 170 + 130), WCLIP))
    K.occupy(mx - 172, my, mx + 172, my + 400, 0, 470)
    K.keep_clear(mx - 140, my - 160, mx + 140, my, 0)
    K.water_box((mx - 150, my - 150, 0), (mx + 150, my - 4, 10), T('coffee'))
    # kit box (walk-in cardboard box: torn opening west, open top) with sprues inside
    kb = town.Building(K, 'kitbox', (1300, -1750, 2000, -1150), 0, (300,),
                       {k: TX[v] for k, v in dict(ext='card_out', int='card_in', trim='card_edge', floor='card_in').items()},
                       doors=[('w', -1560, -1400)], roof=None, no_windows='nsew', floor_mat=False, door_h=200, tile=700)
    kb.build()
    place('sprue', 1500, -1320, 0, 0)
    place('sprue', 1820, -1540, 0, 90)
    # tools + bits as cover along the bench (long sightlines run north-south here)
    place('screwdriver', 1180, 60, 0, 0)
    place('glue_tube', 2100, -180, 0, 270)
    place('battery9v', 1300, -560, 0, 75)
    place('locobox', 2050, 600, 0, 90)
    K.catalog('pad_tins/pad_paint1.md3', 2060, -900, 0, scale=4.0, lit=True)
    K.catalog('pad_tins/pad_paint2.md3', 1360, 740, 0, scale=4.0, lit=True)
    K.catalog('pad_ddmix/backyard/screw_nut.md3', 1420, 980, 0, scale=4.5, lit=True)
    K.catalog('pad_radio_car/radio_control_fl.md3', 1600, 1850, 0, scale=3.0, angle=-30, lit=True)
    for (x, y, s, path) in ((1500, -150, 0.95, 'pad_tins/pad_paint1.md3'), (1560, -60, 0.95, 'pad_tins/pad_paint2.md3'),
                            (2180, 900, 0.95, 'pad_tins/pad_paint1.md3'), (1240, -1050, 0.95, 'pad_tins/pad_paint2.md3')):
        K.catalog(path, x, y, 0, scale=s, lit=True)
    # pegboard + shelf on the east wall
    K.add(sign_box((X1 - 8, -1100, 0), (X1, 760, 1500), T('pegboard'), 512, 512, facing='w', edge=T('shelf')))
    shelf = box((2048, -720, 700), (X1 - 8, 320, 716), {'top': T('shelf'), 'side': T('shelf'), 'bot': T('shelf')})
    K.add(shelf); K.reserve(shelf)
    for y in (-600, 200):
        K.add(hull([(X1 - 8, y - 8, 700), (X1 - 8, y + 8, 700), (2120, y - 8, 700), (2120, y + 8, 700),
                    (X1 - 8, y - 8, 520), (X1 - 8, y + 8, 520)], {'top': T('shelf'), 'side': T('shelf'), 'bot': T('shelf')}, round_pts=False))
    for (y, s, path) in ((-640, 0.95, 'pad_tins/pad_paint1.md3'), (-520, 0.95, 'pad_tins/pad_paint2.md3'), (240, 0.95, 'pad_tins/pad_paint1.md3')):
        K.catalog(path, 2200, y, 716, scale=s, lit=True)
    K.jumppad(1880, -200, 0, land=(2176, -200, 716), apex=860, name='pad_shelf', dress=ML.PLACE['pad_sewbutton'], edges=[(2048, -200, 716)])
    # the seam: layout fascia edge strip (a low lip you step over)
    K.timer_sound(1800, 0, 400, 'animal/blackbird', 'basement_bird', 50, 30)


# ================================================================================================ scenery props
def scenery():
    # trees, bushes, cars, lamps, benches, the plaza statue + fountain
    place('fountain', -820, -260, 2)
    K.speaker(-820, -260, 120, 'ambient/water_flowing')
    for (x, y) in ((-1500, 800), (-2600, -700), (520, -1250), (-1900, -1500)):
        p = K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, scale=0.85, lit=True, search=200, clip=False)
        if p: K.add(cyl(p[0], p[1], 26, 0, 240, WCLIP, 8))
    for (x, y) in ((-1020, 620), (-560, 800), (-1050, 60), (250, 650), (-300, 760), (-160, 760), (-2600, 0), (-2600, -1000), (500, 1300)):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, scale=0.5, lit=True)
    for (x, y, a) in ((0, 0, 0), (400, -40, 180), (-1700, -1900, 90), (950, 0, 0)):
        K.catalog('pad_nascars/padcar_black_rc.md3' if a % 180 else 'pad_nascars/padcar_orange_rc.md3', x, y, 2, scale=0.6, angle=a, lit=True)
    for (x, y) in ((-980, -80), (-600, -150), (-300, -700), (980, 200), (980, -200)):
        K.catalog('pad_ddmix/padship/shiplamp.md3', x, y, 2, scale=1.5, lit=True)
    for (x, y, a) in ((-400, -400, 90),):
        place('pbench', x, y, 2, a)
    for a in (245, 262, 280, 296):
        x, y = P(a, 1720)
        place('pbench', x, y, 48, a + 90)
    K.catalog('pad_statues/statue_super.md3', -500, -260, 2, scale=0.7, lit=True)
    # churchyard tombstones
    for (x, y) in ((-1200, 680), (-1100, 720), (-980, 690), (-760, 700), (-660, 660)):
        K.catalog('pad_westernset/tombstone2.md3', x, y, 0, scale=0.55, angle=90, lit=True)
    # mountain pines
    for (x, y, z, k) in ((-1600, 1200, 400, 1), (-1300, 1150, 400, 2), (-100, 1200, 400, 3), (0, 1320, 400, 1), (-700, 1250, 400, 2),
                         (-1500, 1600, 640, 3), (-300, 1600, 640, 1), (-400, 1850, 640, 2), (-1680, 1950, 640, 1),
                         (600, 1500, 0, 2), (850, 1650, 0, 3), (400, 1750, 0, 1), (950, 1300, 0, 2), (-2500, 1850, 0, 3),
                         (-2050, 1950, 0, 1), (-2200, 1700, 0, 2)):
        place(f'pine{k}', x, y, z, angle=(x * 7) % 360)
    # farm: sunflowers, a duck by the barn
    for k in range(5):
        K.catalog('pad_sunflower/pad_sunflower3.md3', -2700 + (k % 5) * 90, 1030 + (k // 5) * 85, 0, scale=0.9, lit=True, clip=False)
    K.catalog('pad_ducks/pad_duck.md3', -2200, 1080, 0, scale=0.5, angle=200, lit=True)
    # goods yard: crates of coal/timber
    for (x, y) in ((-2250, -1850), (-2600, -1450)):
        K.catalog('pad_ddmix/anteroom/metal_suitcase.md3', x if x > -2500 else -2700, y if x > -2500 else -1250, 0, scale=1.6, lit=True)
    # NE camp: tents as books leaning? -> catalog standup + tyre
    K.catalog('pad_ddmix/backyard/tire.md3', 700, 1100, 0, scale=0.6, lit=True)
    K.catalog('pad_ddmix/padshop/cardboard_standup.md3', 1000, 1100, 0, scale=0.7, angle=200, lit=True)
    # the lane along the acrylic guard: hedges, a parked van, a spool of thread on the bench (sightline cover)
    for x in (-1950, -1250, -300, 160, 420):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, -1912, 0, scale=0.6, angle=0, lit=True)
    K.catalog('pad_toiletroll/pad_toiletroll.md3', 1700, -1888, 0, scale=2.4, lit=True, nudge=False)
    K.catalog('pad_tins/pad_pupsi.md3', 2150, -1700, 0, scale=3.0, lit=True)
    # depot: buffer stops
    x, y = P(262, 1700)
    deco('station_sign', x, y, 198, 262 + 90)


def decals():
    """roads, plaza paving, footpaths (2u decal brushes on the grass)"""
    holes = [(H1[0] - HH, H1[1] - HH, H1[0] + HH, H1[1] + HH), (H2[0] - HH, H2[1] - HH, H2[0] + HH, H2[1] + HH)]
    for r in sub_rects((-1100, -754, -300, -120), holes):
        K.add(box((r[0], r[1], 0), (r[2], r[3], 2), {'top': T('paving'), 'side': T('paving'), 'bot': CAULK}))
    rd = {'top': T('road'), 'side': T('road'), 'bot': CAULK}
    for (x0, x1) in ((-300, 540), (796, BX)):
        K.add(box((x0, -96, 0), (x1, 96, 2), rd))
    fp = {'top': T('footpath'), 'side': T('footpath'), 'bot': CAULK}
    K.add(box((-740, -120, 0), (-640, 228, 2), fp))              # plaza -> church


# ================================================================================================ items
def items(B):
    # weapons on the hardest spots
    K.weapon('imperius', 1700, 1000, 960, marker='purple')
    K.weapon('balloony', -900, 1900, 832, marker='orange')
    K.weapon('betty', -270, 560, 736, marker='black')
    K.weapon('pumper', -560, -600, UZ, marker='green')
    K.weapon('splasher', -1800, -250, LBED, marker='blue')
    K.weapon('boaster', -700, -420, 2, marker='orange')
    K.item('item_armor_shard', 1650, -500, 24)
    K.weapon('bubbleg', -1060, -1260, 48, marker='green')
    ammo = {
        'imperius': [(-250, -1080, UZ), (-700, 1980, 832), (1650, -1450, 0), (-1100, -1000, 416)],
        'balloony': [(-1500, 1850, 640), (-2500, 1500, 176), (950, 600, 160), (C[0], 1690, 0)],
        'betty': [(-900, 420, 4), (-418, 300, 4), (-1150, 720, 0), (2200, -100, 716)],
        'pumper': [(-1150, -400, UZ), (-300, -1100, UZ), (-2600, -1700, 4), (1040, -700, 0), (100, 300, 160)],
        'splasher': [(-1230, -220, 4), (-1450, 280, 0), (-1000, -380, 2), (1650, -860, 0)],
        'boaster': [(1500, 1180, 300), (1650, -600, 24), (1700, -1500, 0), (100, -500, 176), (950, 450, 4)],
        'bubbleg': [(-600, -1040, 52), (P(270, 1700)[0], P(270, 1700)[1], 48), (700, 1600, 0), (-2280, -1180, 208)],
    }
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((-400, 0, 2), (1300, -600, 0), (-2200, 1000, 0)): K.ammo('nipper', x, y, z)
    K.item('item_armor_padshield', 2176, -480, 716)
    K.item('item_speedy', 2176, 120, 716)
    for (x, y, z) in ((1700, -1300, 0), (-1000, -1060, 240), (-600, 1150, 400), (-2600, 1480, 176)):
        K.item('item_armor_shard', x, y, z)
    K.item('holdable_floater', -1500, 1300, 400)
    K.station(-560, -1230, 48, ang=90)
    K.station(1350, 450, 0, ang=180)
    K.station(-2200, 1040, 0, ang=0)
    # spawns
    for (x, y, z, a) in ((-850, -560, 2, 90), (-400, -400, 2, 180), (-1500, -900, 0, 45), (-2200, -200, 0, 0),
                         (-2500, 1100, 0, 300), (-1000, 1180, 400, 0), (-600, 1300, 400, 180), (700, 1350, 0, 225),
                         (450, 400, 0, 180), (950, -350, 0, 120), (500, -1400, 0, 90), (-1000, -1700, 48, 90),
                         (1450, -350, 0, 180), (1950, 400, 0, 200), (1500, 1650, 0, 270), (2000, -1300, 0, 90)):
        K.spawn(x, y, z, a)


# ================================================================================================ vault (secret)
def vault():
    """the spare-parts tin: sealed room far below the bench, reached through the tunnel refuge's fake wall"""
    x0, y0, x1, y1 = VAULT; z = VAZ
    t = lambda **f: tex6(**f)
    K.add(box((x0 - 16, y0 - 16, z - 16), (x1 + 16, y1 + 16, z), t(top=T('vault')), detail=False),
          box((x0 - 16, y0 - 16, z + 320), (x1 + 16, y1 + 16, z + 336), t(bot=T('vault')), detail=False),
          box((x0 - 16, y0, z), (x0, y1, z + 320), t(e=T('vault')), detail=False),
          box((x1, y0, z), (x1 + 16, y1, z + 320), t(w=T('vault')), detail=False),
          box((x0 - 16, y0 - 16, z), (x1 + 16, y0, z + 320), t(n=T('vault')), detail=False),
          box((x0 - 16, y1, z), (x1 + 16, y1 + 16, z + 320), t(s=T('vault')), detail=False))
    K.item('item_padpower', x0 + 260, y0 + 120, z)
    K.item('item_revival', x0 + 260, y1 - 120, z)
    K.item('holdable_killerducks', x1 - 120, (y0 + y1) / 2, z)
    for (x, y) in ((x0 + 120, y0 + 90), (x1 - 100, y1 - 90)):
        K.catalog('pad_ddmix/backyard/screw_nut.md3', x, y, z, scale=3.5, lit=True)
    K.teleporter((x1 - 64, y0 + 24, z), (x1 - 8, y0 + 120, z + 96), dest=(1300, -120, 0), angle=0, name='vault_exit')
    K.light((x0 + x1) / 2, (y0 + y1) / 2, z + 250, 700, '0.9 0.95 1')


# ================================================================================================ lights + shader
def lights():
    K.light_grid(X0 + 200, Y0 + 200, X1 - 200, Y1 - 200, 1300, 700, 2600, color='1 0.97 0.9')
    for (x, y, z) in ((-832, -1000, 180), (-832, -1000, 350), (-930, 420, 200), (-418, 420, 200), (-418, 420, 600),
                      (94, 400, 120), (94, 400, 280), (950, 600, 120), (950, 600, 280), (50, -480, 130), (50, -480, 300),
                      (-1230, -170, 130), (-2280, -1180, 140), (-2570, -1780, 160), (-2530, 1500, 130), (-2530, 1500, 290),
                      (940, -960, 200), (1650, -1450, 220), (1650, -560, 200)):
        K.light(x, y, z, 380)
    # mountain tops and the shelf sit high: extra lights above them
    for (x, y) in ((-900, 1880), (-1500, 1700), (-300, 1750)):
        K.light(x, y, 1250, 900)


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


CABLES = {}


def viewing_gallery():
    """the visitors' side of the acrylic: a drinks ledge on brackets along the guard and a row of bar stools facing
    the layout, so people can sit and watch the trains go by. Unreachable (behind the guard + clip): decoration only."""
    z = VZ
    lt = {'top': T('shelf'), 'side': T('shelf'), 'bot': T('shelf')}
    K.add(box((X0 + 40, Y0 - 300, 170), (X1 - 40, Y0, 200), lt))                  # the ledge, its back against the guard
    for x in range(-2600, 2200, 700):                                              # brackets down the fascia
        K.add(hull([(x - 16, Y0, 170), (x + 16, Y0, 170), (x - 16, Y0 - 280, 170), (x + 16, Y0 - 280, 170),
                    (x - 16, Y0, -40), (x + 16, Y0, -40)], lt, round_pts=False))
    stools = [(-2350, 15, 'bar_stool'), (-1500, -10, 'bar_stool_b'), (-650, 30, 'bar_stool'), (250, -20, 'bar_stool_back'),
              (1100, 5, 'bar_stool'), (1950, -35, 'bar_stool_b')]
    for (x, a, nm) in stools:
        deco(nm, x, Y0 - 560, z, 90 + a)
    # drinks and a programme left on the ledge
    for (x, path, sc) in ((-2300, 'pad_cups/pad_cup03.md3', 2.0), (-1480, 'pad_ddmix/diner/glass_betty.md3', 2.2),
                          (300, 'pad_cups/pad_cup05.md3', 2.0), (1150, 'pad_ddmix/diner/glass_diner.md3', 2.4),
                          (1900, 'pad_tins/pad_pupsi.md3', 1.5)):
        K.catalog(path, x, Y0 - 150, 200, scale=sc, clip=False, nudge=False, lit=True)
    K.catalog('pad_books/pad_ob_fl_md.md3', -700, Y0 - 160, 200, scale=1.4, angle=80, clip=False, nudge=False, lit=True)
    for x in (-2000, -400, 1300):
        K.light(x, Y0 - 700, z + 1700, 1300, '1 0.92 0.8')


def basement_corner():
    """the real basement past the acrylic guard (it used to be a painted wall): stairs up to the house door on a
    landing, washing machine + laundry basket, hot-water boiler with copper pipes, metal shelving with stored boxes
    under a high window with a sunbeam, bucket + mop. Unreachable (behind the guard + clip), so no collision."""
    W = VY                                                        # back wall face
    z = VZ
    # stairs rise west from x 1500 to x -700; the landing + its posts are brushes so the door stands on something
    deco('basement_stairs', 1500, W + 220, z, 180)
    lt = {'top': T('ruler_side'), 'side': T('stairside'), 'bot': T('stairside')}
    K.add(box((-1300, W, z + 2350), (-700, W + 440, z + 2400), lt))
    for x in (-1290, -760):
        K.add(box((x, W + 380, z), (x + 50, W + 430, z + 2350), lt))
    deco('house_door', -1000, W, z + 2400, 180)
    deco('washer', -277, W + 330, z, 180)                          # tucked under the stairs (underside > 1550 here)
    deco('laundry_basket', 330, W + 700, z, 20)
    K.light(-277, W + 760, z + 500, 900, '1 0.9 0.75')
    deco('water_boiler', -1600, W + 280, z, 180)
    deco('shelving', -2450, W + 220, z, 180)
    deco('bucket_mop', -1950, W + 700, z, 200)
    K.add(box((-2750, W, z + 2410), (-2150, W + 90, z + 2440), {'top': T('stairside'), 'side': T('stairside'), 'bot': T('stairside')}))
    deco('basement_window', -2450, W, z + 2500, 180)
    deco('sunbeam', -2450, W, z + 2500, 180, lit=False)
    K.light(-2450, W + 300, z + 2350, 2600, '0.85 0.92 1')
    K.light(-2300, W + 800, z + 600, 1400, '0.9 0.95 1')
    K.light(300, W + 600, z + 2300, 2200, '1 0.85 0.6')
    K.light(1500, W + 800, z + 800, 1100, '1 0.9 0.75')
    K.light(-1000, W + 300, z + 2700, 600, '1 0.85 0.6')


def models():
    PM.mats(); building_mats(); PM.basement_mats(); PM.pad_mats()
    PM.washing_machine(); PM.laundry_basket(); PM.water_boiler(ceil=ZC - VZ); PM.basement_stairs(landing=0)
    PM.house_door(); PM.metal_shelving(); PM.basement_window(); PM.sunbeam(drop=2500, reach=1050); PM.bucket_mop()
    PM.gallery_mats(); PM.bar_stool(); PM.bar_stool(key='stool_seat2', name='bar_stool_b')
    PM.bar_stool(key='stool_seat2', name='bar_stool_back', back=True)
    PM.pad_manhole(); PM.pad_vent(); PM.pad_trapdoor(); PM.pad_spring(); PM.pad_button(); PM.pad_sewbutton()
    PM.tunnel_portal(150, 320, top_z=400)
    X = ML.Model(); from meshlib import tube as _t
    _t(X.mesh(TX['iron_green']), [(0, 0, 0), (0, 0, 192)], 7, nseg=10)
    _t(X.mesh(TX['iron_green']), [(0, 0, 130), (0, 60, 190)], 4, nseg=8)
    _t(X.mesh(TX['iron_green']), [(0, 0, 130), (0, -60, 190)], 4, nseg=8)
    ML.save('canopy_post', X)
    PM.turntable_deck(TT_R)
    PM.buffer_stop(); PM.xing_post(); PM.platform_bench(); PM.fountain(); PM.waterwheel(); PM.windmill_sails()
    PM.windmill_tower()
    for k in (1, 2, 3): PM.pine(h=380 + 50 * k, r=110 + 15 * k, seed=k)
    PM.hatch_lid(); PM.mug_lying(); PM.controller(); PM.screwdriver(); PM.glue_tube(); PM.battery9v(); PM.locobox()
    PM.point_motor(); PM.pliers(); PM.saw(); PM.sprue(360, 260); PM.bulb_hanging(); PM.cobweb(); PM.station_sign()
    PM.COLL['sprue'] = dict(boxes=[((-180, -130, 0), (180, 130, 26))])
    X = PM.loco(); ML.save('loco_static', X)
    PM.COLL['loco_static'] = dict(boxes=[((-300, -70, 0), (300, 70, 196))])
    # underworld cable runs (world coordinates baked in, placed at the origin)
    for nm, pts, key, r in (('cable_a', [(-1200, -1130, -60), (-1210, -900, -260), (-1200, -700, -300), (-1190, -480, -250), (-1200, -270, -60)], 'cable_red', 14),
                            ('cable_b', [(-760, -1130, -60), (-740, -950, -230), (-720, -700, -290), (-740, -450, -240), (-760, -270, -60)], 'cable_black', 18),
                            ):
        c = np.mean(np.array(pts, float), 0)
        PM.cable_run([tuple(np.array(p, float) - [c[0], c[1], 0]) for p in pts], key, nm, r)
        CABLES[nm] = (c[0], c[1])


if __name__ == '__main__':
    textures()
    models()
    shell(); underworld(); lake(); railway(); mountain()
    B = buildings(); hatches(); workbench(); decals(); scenery(); vault(); basement_corner(); viewing_gallery()
    TR = train()
    items(B); lights()
    K.fix_items()
    TR.sweep_check()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
