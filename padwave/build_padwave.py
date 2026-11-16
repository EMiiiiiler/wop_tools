#!/usr/bin/env python3
"""Padman's Wave World (wop_padwave): an indoor water park under a glass barrel vault, after a photo of a real one.

    OUT=<dir> python3 build_padwave.py          (names come from mapinfo.json next to this file)

Zones: Blue Thunder wave pool (beach ramp, Coconut Island, secret wave-machine intake), Twister Tower (three decks,
crow's nest, purple Sky Screamer flume with the loop, blue Twister helix), Splashdown lagoon, sun terrace + Banana Hut,
Surf Shop, lifeguard tower, palm garden.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from wopmap import box, cyl, hull, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP
from woplib import models as ML, shaders as SH, texlib as TL
from meshlib import Mesh, revolve, rbox, tube, ellipsoid, sphere, arc_path, rot_z, rot_axis

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = -2240, -1728, 2240, 1728            # the hall; INFO['bounds'] also covers Volcano Bay
ZTOP = 1408
K = MapKit(MAP, NS, LONG, tuple(INFO['bounds']), worldspawn={'_ambient': '22', '_color': '0.95 0.98 1', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
P_ = 'x/x'                                            # placeholder texture for solid_piece brushes

# ------------------------------------------------------------------------------------------------ layout constants
WALL_H = 512                                          # panel wall under the glass
ARC_R, ARC_ZC = 2224.0, -880.0                        # barrel vault: circle in the y/z plane
WAVE = (-1536, Y0, 1536, -448); WAVE_Z = -160; WATER = -8; BEACH_Y = -1088
ISLE = (0, -1380)
LAGOON = (1280, 256, 2112, 1024); PLUNGE = (-1536, 1216, -960, 1632); SHALLOW = -48
CORE = (-576, 448, -64, 960); LV = (256, 512, 768); NEST_Z = 1024
TERR = (1344, 1216, X1, Y1); TERR_Z = 128
SHACK = (1824, 1392, 2192, 1696); SHACK_H = 208
SHOP = (X0, -160, -1888, 352); SHOP_H = 224
GUARD = (1760, -1216, 2016, -960); GUARD_Z = 160; HUT_H = 128
VAULT_C = (0, 0); VAULT_Z = -1280
# Volcano Bay (the annex north of the hall, through two arches in the north wall)
AX0, AX1, AY0, AY1 = -1600, 1600, Y1 + 32, 3840
ARCHES = ((-900, -644), (644, 900)); ARCH_H = 256; CLIFF_H = 896
RIV_O = (-896, 1968, 896, 3760); RIV_I = (-672, 2192, 672, 3536)
VC = (0, 2864); TIER_A = (592, 480, 368, 256, 144); TIER_Z = (128, 256, 384, 512, 640)
CHUTE = [(VC[0] + x, VC[1] + y, z) for (x, y, z) in ((40, 258, 512), (40, 420, 462), (0, 560, 415), (-140, 680, 365), (-340, 760, 310),
                                                     (-560, 740, 255), (-740, 620, 200), (-790, 440, 118), (-790, 300, 46))]
CHUTE_POSTS = [(VC[0], VC[1] + 560, 415, TIER_Z[0]), (VC[0] - 340, VC[1] + 760, 310, SHALLOW), (VC[0] - 740, VC[1] + 620, 200, SHALLOW)]
DIVE = (-1920, -1408, -1664, -1152); DIVE_Z = (128, 256, 384)
TIKI = (-1500, 2500, -1180, 2860); TIKI_H = 176
YELLOW = [(1700, 1214, 128), (1700, 1120, 70), (1700, 1030, 36), (1700, 960, 28)]
BLIMP_R, BLIMP_Z = 1120, 930
HW, WALLH = 48, 56                                    # flume half width, wall height
PURPLE = [(-448, 320, 768), (-448, 160, 716), (-400, 0, 668), (-256, -112, 622), (0, -160, 556), (400, -160, 470),
          (800, -160, 380), (1150, -128, 292), (1400, 0, 212), (1560, 180, 132), (1620, 330, 66), (1620, 430, 30)]
LOOP = (600, -160); LOOP_R = 330; LOOP_T = 46
HELIX_C = (-1000, 928); HELIX_R = 224


def arc_z(y): return ARC_ZC + math.sqrt(ARC_R ** 2 - y * y)


def twister_path():
    pts = [(-578, 704, 512), (-800, 704, 484)]
    z0, z1 = 464, 114
    n = 15                                              # 1.25 turns in 30 degree steps, clockwise from the south point
    for k in range(n + 1):
        a = math.radians(-90 - 30 * k)
        pts.append((HELIX_C[0] + HELIX_R * math.cos(a), HELIX_C[1] + HELIX_R * math.sin(a), z0 + (z1 - z0) * k / n))
    pts += [(-1224, 1100, 66), (-1224, 1214, 45), (-1224, 1300, 30)]
    return pts


TWIST = twister_path()
PURPLE_S = [tuple(np.round(p, 1)) for p in ML.spline(PURPLE, 3)]
PURPLE_S[1] = (PURPLE_S[0][0], PURPLE_S[1][1] - 4, PURPLE_S[1][2])      # leave the deck edge square
PURPLE_S[0] = (PURPLE_S[0][0], PURPLE_S[0][1] - 2, PURPLE_S[0][2])
CHUTE_S = [tuple(np.round(p, 1)) for p in ML.spline(CHUTE, 3)]
CHUTE_S[1] = (CHUTE_S[0][0], CHUTE_S[1][1], CHUTE_S[1][2])


# ------------------------------------------------------------------------------------------------ textures
def wall_tex(n=512):
    """white wall panels with an aqua wave band and a tiled skirting"""
    x, y = ML.xy(n)
    c = np.zeros((n, n, 3), np.float32) + ML.C((236, 240, 240)) + ML.N3(n, 2, 5, 3)
    seam = ((x * 4) % 1 < 0.012) | ((y * 4) % 1 < 0.012)
    c = np.where(seam[..., None], ML.C((196, 204, 206)), c)
    w1 = 0.62 + 0.035 * np.sin(x * 2 * math.pi * 2); w2 = 0.70 + 0.035 * np.sin(x * 2 * math.pi * 2 + 1.3)
    c = np.where(((y > w1) & (y < w1 + 0.05))[..., None], ML.C((40, 170, 200)), c)
    c = np.where(((y > w2) & (y < w2 + 0.035))[..., None], ML.C((250, 200, 60)), c)
    c = np.where((y > 0.9)[..., None], ML.C((60, 150, 180)) + ML.N3(n, 1, 9, 6), c)
    return c


def grille_tex(n=256):
    x, y = ML.xy(n)
    c = np.zeros((n, n, 3), np.float32) + ML.C((210, 214, 216))
    slat = ((y * 10) % 1 < 0.55) & (x > 0.06) & (x < 0.94) & (y > 0.06) & (y < 0.94)
    return np.where(slat[..., None], ML.C((30, 60, 80)) + ML.N3(n, 1, 3, 5), c)


def lattice_tex(n=256):
    """glazing bars: white lines, transparent panes (alpha tested)"""
    x, y = ML.xy(n)
    bar = (x < 0.04) | (x > 0.96) | (y < 0.04) | (y > 0.96) | (np.abs(x - 0.5) < 0.012) | (np.abs(y - 0.5) < 0.012)
    c = np.zeros((n, n, 3), np.float32) + ML.C((244, 246, 248))
    return c, np.where(bar, 255, 0).astype(np.uint8)


def leaf_tex(n=256):
    x, y = ML.xy(n)
    d = np.abs(x - 0.5) * 2
    edge = 0.92 - 0.4 * ((y * 16) % 1) - 0.25 * y
    c = ML.lerp(ML.C((40, 130, 50)), ML.C((120, 190, 70)), (1 - d)[..., None]) + ML.N3(n, 2, 77, 8)
    c = np.where((d < 0.05)[..., None], ML.C((170, 200, 90)), c)
    return c, np.where(d < edge, 255, 0).astype(np.uint8)


def lava_tex(n=256):
    d = np.abs(ML.noise(n, 14, 5) + 0.5 * ML.noise(n, 6, 9))[..., None]
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    return ML.lerp(ML.C((255, 210, 60)), ML.C((150, 30, 10)), np.clip(d * 1.6, 0, 1)) + ML.N3(n, 3, 8, 10)


def cloud_tex(n=256):
    c = np.clip((ML.noise(n, 24, 3) + 0.5 * ML.noise(n, 10, 4)) * 1.4 - 0.25, 0, 1)
    return np.repeat((c * 90)[..., None], 3, 2)


def fall_tex(n=128):
    x, y = ML.xy(n)
    st = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 9 + np.sin(y * 2 * math.pi * 2) * 1.5)
    c = ML.lerp(ML.C((150, 215, 240)), ML.C((250, 255, 255)), st[..., None])
    a = np.clip(120 + st * 110 + ML.noise(n, 3, 6) * 40, 0, 255).astype(np.uint8)
    return c, a


def textures():
    TX.add('deck', TL.tiles((226, 208, 172), (176, 160, 132), cols=4, rows=4, offset=0.5, grout_w=0.03))
    TX.add('pooltile', TL.tiles((120, 214, 226), (236, 246, 246), cols=8, rows=8, offset=0, grout_w=0.07), steps='splashsteps')
    TX.add('beach', TL.solid((232, 214, 160), 9, 13, 256), steps='sandsteps')
    TX.add('wall', wall_tex(), check_tile=False, scale=1.0)
    TX.add('grille', grille_tex(), check_tile=False)
    TX.add('steel', TL.metal((236, 240, 244)), steps='latticesteps')
    TX.add('teal', TL.metal((40, 150, 150)))
    TX.add('grate', TL.tiles((214, 220, 224), (120, 128, 134), cols=8, rows=8, offset=0, grout_w=0.12), steps='latticesteps')
    TX.add('water', TL.solid((120, 220, 236), 10, 11, 128), 'water', rgb=(0.35, 0.8, 0.9), alpha=0.5)
    TX.add('slick_nd', TL.solid((200, 120, 220), 2, 5, 64), 'raw', shader=(
        f'textures/{NS}/slick_nd\n{{\n\tqer_editorimage textures/{NS}/slick_nd\n\tqer_trans 0.5\n\tsurfaceparm slick\n'
        '\tsurfaceparm nodraw\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n}\n\n'))
    TX.add('sign_wave', TL.neon('WAVE WORLD', (80, 230, 255), 1024, 256), 'neon', rgb=(0.3, 0.9, 1.0), light=200, check_tile=False)
    TX.add('sign_snack', TL.label('BANANA HUT', 512, 128, (250, 210, 60), (120, 60, 20), border=(120, 60, 20)), 'sign', check_tile=False)
    TX.add('sign_shop', TL.label('SURF SHOP', 512, 128, (40, 150, 170), (250, 250, 240), border=(250, 250, 240)), 'sign', check_tile=False)
    TX.add('sign_guard', TL.label('LIFEGUARD', 512, 128, (220, 40, 40), (255, 255, 255), border=(255, 255, 255)), 'sign', check_tile=False)
    TX.add('sign_deep', TL.label('DEEP END', 512, 128, (250, 250, 250), (220, 40, 40), border=(220, 40, 40)), 'sign', check_tile=False)
    TX.add('cliff', TL.stone((176, 150, 120), cells=10, vary=22), scale=1.0)
    TX.add('facade', TL.tiles((150, 200, 220), (240, 244, 246), cols=4, rows=4, offset=0, grout_w=0.06), scale=1.0)
    TX.add('lava', lava_tex(), 'neon', rgb=(1.0, 0.45, 0.1), light=160)
    TX.add('sign_bay', TL.neon('VOLCANO BAY', (255, 150, 40), 512, 128), 'neon', rgb=(1.0, 0.6, 0.2), light=120, check_tile=False)
    TX.add('sign_scream', TL.neon('SKY SCREAMER', (230, 90, 255), 512, 128), 'neon', rgb=(0.9, 0.4, 1.0), light=100, check_tile=False)
    TX.add('sign_twist', TL.neon('TWISTER', (90, 150, 255), 512, 128), 'neon', rgb=(0.4, 0.6, 1.0), light=100, check_tile=False)
    TX.add('sign_tiki', TL.label('TIKI BAR', 512, 128, (96, 60, 30), (255, 220, 90), border=(255, 220, 90)), 'sign', check_tile=False)
    ML.save_img(TX.path('clouds'), cloud_tex())
    TX.kit_defaults(pad_rgb=(255, 200, 60))
    # model materials
    m = TX.material
    m('steelw', TL.metal((238, 242, 246)), shade=40)
    m('steelw_vl', None, 'vl', image='steelw_m')
    m('tealm', TL.metal((40, 150, 150)), shade=40)
    m('gratem', TL.tiles((224, 228, 232), (130, 138, 144), cols=8, rows=8, offset=0, grout_w=0.12), shade=30, steps='latticesteps')
    m('purple', TL.stripes((170, 60, 190), (200, 90, 215), 4, soft=0.6), 'lms', v=0.14)
    m('blue', TL.stripes((40, 90, 210), (70, 130, 235), 4, soft=0.6), 'lms', v=0.14)
    la, lal = lattice_tex(); m('lattice', la, 'alpha', alpha=lal)
    m('bark', TL.stripes((150, 116, 78), (112, 84, 54), 10, vertical=False, soft=0.4), 'vl')
    lf, lfa = leaf_tex(); m('leaf', lf, 'alpha', alpha=lfa, deform='wave 96 sin 0 3 0 0.35')
    m('coco', TL.solid((96, 64, 36), 6, 3, 64), 'vl')
    m('plastic', TL.solid((244, 244, 240), 3, 9, 64), shade=50)
    m('towel_r', TL.stripes((230, 60, 70), (250, 240, 230), 6, vertical=False))
    m('towel_b', TL.stripes((50, 120, 220), (250, 240, 230), 6, vertical=False))
    m('canopy_r', TL.stripes((230, 50, 60), (250, 250, 245), 4), two=True, shade=60)
    m('canopy_y', TL.stripes((250, 200, 40), (250, 250, 245), 4), two=True, shade=60)
    m('ring_o', TL.stripes((250, 130, 30), (250, 240, 220), 6, vertical=False), shade=80)
    m('ring_g', TL.stripes((60, 200, 110), (250, 240, 220), 6, vertical=False), shade=80)
    m('rock', TL.stone((150, 140, 128), cells=12), shade=70)
    m('planks', TL.planks((196, 150, 96)), shade=30, steps='woodsteps')
    m('hutwall', TL.stripes((250, 214, 70), (250, 246, 230), 8), shade=30)
    m('shopwall', TL.stripes((50, 160, 180), (240, 248, 248), 8), shade=30)
    m('redwhite', TL.stripes((224, 50, 50), (250, 250, 250), 6), shade=30)
    m('roofm', TL.tiles((70, 170, 180), (40, 110, 120), cols=6, rows=10, offset=0.5), shade=30)
    m('deckm', TL.tiles((226, 208, 172), (176, 160, 132), cols=4, rows=4, offset=0.5, grout_w=0.03), shade=30)
    m('panelm', TL.solid((236, 240, 240), 3, 15, 128), shade=30)
    m('wheel', TL.solid((40, 40, 46), 3, 19, 64), shade=60)
    m('orange', TL.stripes((250, 110, 30), (255, 150, 60), 4, soft=0.6), 'lms', v=0.14)
    m('glass', TL.solid((150, 220, 240), 4, 3, 64), 'glass')
    m('chrome', TL.metal((200, 210, 220)), 'lms')
    m('yellow', TL.stripes((250, 200, 40), (255, 226, 90), 4, soft=0.6), 'lms', v=0.14)
    m('sandrock', TL.stone((206, 178, 136), cells=12, vary=18), shade=40, steps='sandsteps')
    m('cliffm', TL.stone((150, 118, 92), cells=9, vary=24), shade=40)
    m('thatch', TL.stripes((196, 164, 90), (150, 118, 60), 24, soft=0.3), shade=30)
    m('bamboo', TL.stripes((170, 140, 70), (120, 92, 44), 10), shade=30)
    fl, fla = fall_tex(); m('fall', fl, 'flow', alpha=fla, speed=-1.4)
    for k, (c1, c2) in dict(blimp_r=((230, 50, 60), (250, 250, 245)), blimp_b=((40, 120, 230), (250, 250, 245)),
                            blimp_y=((250, 205, 50), (250, 150, 30)), blimp_g=((60, 200, 110), (250, 250, 245))).items():
        m(k, TL.stripes(c1, c2, 6), 'dyn')
    m('black_d', TL.solid((20, 20, 24), 2, 3, 32), 'dyn')


# ------------------------------------------------------------------------------------------------ custom MD3 props
def models():
    M = TX.mats
    # ---- barrel vault: one rib and one glazing bay (vertex lit, no shadows: the sun shines through)
    half = math.asin(Y1 / ARC_R)
    angs = np.linspace(-half, half, 29)
    arc = lambda R: [np.array([0.0, R * math.sin(a), ARC_ZC + R * math.cos(a)]) for a in angs]
    X = ML.Model()
    outer, inner = arc(ARC_R - 4), arc(ARC_R - 90)
    tube(X.mesh(M['steelw_vl']), outer, 20, nseg=8, vlen=128); tube(X.mesh(M['steelw_vl']), inner, 12, nseg=8, vlen=128)
    for i in range(0, 28):
        a, b = (outer[i], inner[i + 1]) if i % 2 == 0 else (inner[i], outer[i + 1])
        tube(X.mesh(M['steelw_vl']), [a, b], 6, nseg=6, caps=(False, False))
    ML.save('vault_rib', X)
    X = ML.Model()
    BAY = 640.0
    Pg = np.zeros((29, 5, 3)); Ng = np.zeros_like(Pg); UV = np.zeros((29, 5, 2))
    for i, a in enumerate(angs):
        for j in range(5):
            Pg[i, j] = (j * BAY / 4, (ARC_R + 6) * math.sin(a), ARC_ZC + (ARC_R + 6) * math.cos(a))
            Ng[i, j] = (0, -math.sin(a), -math.cos(a)); UV[i, j] = (j, i)
    X.mesh(M['lattice']).grid(Pg, Ng, UV)
    for i in range(2, 28, 4):
        tube(X.mesh(M['steelw_vl']), [outer[i], outer[i] + [BAY, 0, 0]], 8, nseg=6, caps=(False, False))
    ML.save('vault_bay', X)

    # ---- palm (vertex-lit trunk, alpha fronds that sway)
    X = ML.Model()
    path = [np.array([18 * math.sin(z / 150.0), 0, z]) for z in np.linspace(0, 330, 9)]
    tube(X.mesh(M['bark']), path, np.linspace(17, 10, 9), nseg=8, vlen=48)
    top = path[-1]
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.2
        d = np.array([math.cos(a), math.sin(a), 0]); s = np.array([-d[1], d[0], 0])
        rows = 7; Pf = np.zeros((rows, 3, 3)); Nf = np.zeros_like(Pf); Uf = np.zeros((rows, 3, 2))
        for i in range(rows):
            t = i / (rows - 1)
            c = top + d * (190 * t) + np.array([0, 0, 60 * t - 150 * t * t + (10 if k % 2 else 0)])
            w = 42 * (1 - 0.6 * t)
            for j, sj in enumerate((-1, 0, 1)):
                Pf[i, j] = c + s * sj * w - np.array([0, 0, 12 * abs(sj)])
                Nf[i, j] = (0, 0, 1); Uf[i, j] = (j / 2, t)
        X.mesh(M['leaf']).grid(Pf, Nf, Uf)
    for k in range(3):
        a = 2.1 * k
        sphere(X.mesh(M['coco']), top + [12 * math.cos(a), 12 * math.sin(a), -14], 9, 8, 6)
    ML.save('palm', X)

    # ---- sun lounger (two towel colours)
    for nm, tw in (('lounger_r', 'towel_r'), ('lounger_b', 'towel_b')):
        X = ML.Model(); pl = X.mesh(M['plastic'])
        rbox(pl, (-22, -62, 14), (22, 22, 20), r=3, k=2)
        back = Mesh(); rbox(back, (-22, 0, 0), (22, 54, 6), r=3, k=2)
        pl.add(back, rot_axis((1, 0, 0), math.radians(38)), (0, 20, 15))
        for (lx, ly) in ((-18, -56), (18, -56), (-18, 16), (18, 16)):
            rbox(pl, (lx - 3, ly - 3, 0), (lx + 3, ly + 3, 14), r=1.5, k=2)
        rbox(X.mesh(M[tw]), (-18, -58, 20), (18, 18, 22.5), r=1.2, k=2, tile=48)
        ML.save(nm, X)

    # ---- parasol (two colours)
    for nm, cn in (('parasol_r', 'canopy_r'), ('parasol_y', 'canopy_y')):
        X = ML.Model()
        tube(X.mesh(M['steelw']), [(0, 0, 0), (0, 0, 172)], 3.5, nseg=8)
        revolve(X.mesh(M['plastic']), [(22, 0), (22, 6), (5, 10), (0, 10)], n=16)
        revolve(X.mesh(M[cn]), [(112, 132), (60, 156), (0, 170)], u_tiles=8, n=16)
        ML.save(nm, X)

    # ---- swim rings
    for nm, sh in (('ring_o', 'ring_o'), ('ring_g', 'ring_g')):
        X = ML.Model()
        tube(X.mesh(M[sh]), arc_path((0, 0, 16), 42, 0, 360, n=25), 16, nseg=10, caps=(False, False), utiles=1, vlen=40)
        ML.save(nm, X)

    # ---- rock
    rng = np.random.default_rng(4)
    ph = rng.uniform(0, 6.28, 6)
    bump = lambda p, t: 1 + 0.10 * math.sin(3 * t + ph[0]) + 0.08 * math.sin(5 * p + ph[1]) + 0.06 * math.sin(7 * t + 2 * p + ph[2])
    X = ML.Model()
    ellipsoid(X.mesh(M['rock']), (0, 0, 20), 70, 56, 64, nu=14, nv=10, bump=bump, flat_bottom=-20, u1=3, v1=2)
    ML.save('rock', X)

    # ---- ice-cream cart (cover prop)
    X = ML.Model()
    rbox(X.mesh(M['redwhite']), (-56, -30, 22), (56, 30, 84), r=6, k=2, tile=64)
    rbox(X.mesh(M['plastic']), (-60, -34, 84), (60, 34, 90), r=3, k=2)
    for sx in (-40, 40):
        for sy in (-34, 34):
            tube(X.mesh(M['wheel']), [(sx, sy - 4, 22), (sx, sy + 4, 22)], 22, nseg=12)
    tube(X.mesh(M['steelw']), [(0, 0, 90), (0, 0, 196)], 3, nseg=8)
    revolve(X.mesh(M['canopy_y']), [(96, 160), (50, 182), (0, 194)], u_tiles=8, n=16)
    ML.save('cart', X)

    # ---- flumes
    X = ML.Model()
    ML.flume(X, PURPLE_S, HW, WALLH, M['purple'])
    for (x, y, z) in PURPLE[3:9]:
        post(X, x, y, z)
    ring = arc_path((LOOP[0], LOOP[1], loop_cz()), LOOP_R, 0, 360, n=49, axis='y')
    tube(X.mesh(M['purple']), ring, LOOP_T, nseg=14, caps=(False, False), vlen=256)
    mx, my = LOOP[0], LOOP[1] - 150
    tube(X.mesh(M['steelw']), [(mx, my, 0), (mx, my, loop_cz())], 16, nseg=8)
    tube(X.mesh(M['steelw']), [(mx, my, loop_cz()), (LOOP[0], LOOP[1], loop_cz())], 10, nseg=8)
    for a in range(0, 360, 45):
        r = math.radians(a)
        tube(X.mesh(M['steelw']), [(LOOP[0], LOOP[1], loop_cz()),
                                   (LOOP[0] + (LOOP_R - 44) * math.cos(r), LOOP[1], loop_cz() + (LOOP_R - 44) * math.sin(r))], 5, nseg=6)
    o = np.array([500.0, 0.0, 0.0]); X.shift(o)
    FLUMES['purple'] = (ML.save('flume_purple', X), o)
    X = ML.Model()
    ML.flume(X, TWIST, HW, WALLH, M['blue'])
    hx, hy = HELIX_C
    tube(X.mesh(M['steelw']), [(hx, hy, 0), (hx, hy, 540)], 18, nseg=10)
    for (x, y, z) in TWIST[2:18:2]:
        tube(X.mesh(M['steelw']), [(hx, hy, z - 50), (x, y, z - 30)], 6, nseg=6)
    post(X, -800, 704, 484)
    o = np.array([-1000.0, 928.0, 0.0]); X.shift(o)
    FLUMES['blue'] = (ML.save('flume_blue', X), o)


FLUMES = {}


def RAMP(*a, **k):
    """K.ramp + reserve (props were nudged onto unreserved ramps)"""
    r = K.ramp(*a, **k); K.reserve(r); return r


def STAIRS(*a, **k):
    """K.stairs16 + reserve the flight so scattered props never land on it"""
    st = K.stairs16(*a, **k); K.reserve(st); return st


def loop_cz():
    """the loop ring stands over the flume: you slide under its lowest point where the flume passes x = LOOP x"""
    zs = [p[2] for p in PURPLE_S if abs(p[0] - LOOP[0]) < 60]
    return (sum(zs) / len(zs) if zs else 425) + WALLH + 8 + LOOP_T + LOOP_R


def post(X, x, y, z, z0=0):
    """flume support: column up to a fork under the channel (collision cylinder added in slides())"""
    M = TX.mats
    tube(X.mesh(M['steelw']), [(x, y, z0), (x, y, z - 60)], 13, nseg=8)
    tube(X.mesh(M['steelw']), [(x, y, z - 62), (x, y, z - 27)], 22, nseg=8)


# ------------------------------------------------------------------------------------------------ structure
def basin(rect, floor_z, tl, south_wall=True):
    """structural tiled basin under a hole in the floor slab"""
    x0, y0, x1, y1 = rect
    K.add(box((x0 - 16, y0 - 16, floor_z - 16), (x1 + 16, y1 + 16, floor_z), tl, detail=False))
    walls = [box((x0 - 16, y0, floor_z), (x0, y1, -32), tl, detail=False), box((x1, y0, floor_z), (x1 + 16, y1, -32), tl, detail=False),
             box((x0 - 16, y1, floor_z), (x1 + 16, y1 + 16, -32), tl, detail=False)]
    if south_wall: walls.append(box((x0 - 16, y0 - 16, floor_z), (x1 + 16, y0, -32), tl, detail=False))
    K.add(*walls)


def shell():
    deck = {'top': T('deck'), 'side': T('pooltile'), 'bot': CAULK}
    for r in sub_rects((X0 - 32, Y0 - 32, X1 + 32, Y1 + 32), [WAVE, LAGOON, PLUNGE]):                  # hall slab
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), deck, detail=False))
    # north wall: shared with Volcano Bay, two arches through it
    cut = [X0] + [v for a in ARCHES for v in a] + [X1]
    nw = lambda a, b, z0, z1, **t: K.add(box((a, Y1, z0), (b, Y1 + 32, z1), dict(
        {k: CAULK for k in ('top', 'bot')}, s=T('wall'), n=T('facade'), e=T('wall'), w=T('wall'), **t), detail=False))
    for a, b in zip(cut[0::2], cut[1::2]): nw(a, b, 0, WALL_H)
    for (a, b) in ARCHES:
        nw(a, b, ARCH_H, WALL_H, bot=T('wall'))
        K.keep_clear(a - 32, Y1 - 160, b + 32, Y1, 0); K.keep_clear(a - 32, AY0, b + 32, AY0 + 160, 0)
        K.add(sign_box((a, Y1 - 6, ARCH_H + 24), (b, Y1, ARCH_H + 88), T('sign_bay'), 512, 128, back=CAULK, facing='s', edge=T('teal')))
        K.route(f'arch_{a}', ((a + b) / 2, Y1 - 120, 0), ((a + b) / 2, AY0 + 120, 0))
    K.add(box((X0, Y1, WALL_H), (X1, Y1 + 32, ZTOP), dict({k: CAULK for k in ('e', 'w', 'top', 'bot')}, s=T('sky'), n=T('facade')),
              detail=False))
    for (side, mn, mx) in (('e', (X0 - 32, Y0 - 32), (X0, Y1 + 32)), ('w', (X1, Y0 - 32), (X1 + 32, Y1 + 32)),
                           ('n', (X0, Y0 - 32), (X1, Y0))):
        for z0, z1, tex in ((0, WALL_H, T('wall')), (WALL_H, ZTOP, T('sky'))):
            t = dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{side: tex})
            K.add(box((mn[0], mn[1], z0), (mx[0], mx[1], z1), t, detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZTOP), (X1 + 32, Y1 + 32, ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))
    # the vault: ribs every 640u, glazing bays between them (models: sun and shots pass through)
    for i in range(8):
        K.custom(ML.PLACE['vault_rib'], X0 + 640 * i + (24 if i == 0 else -24 if i == 7 else 0), 0, 0, lit=False, occupy=False, _structure=1)
    for i in range(7):
        K.custom(ML.PLACE['vault_bay'], X0 + 640 * i, 0, 0, lit=False, occupy=False, _structure=1)
    K.add(sign_box((-640, Y1 - 8, 224), (640, Y1, 480), T('sign_wave'), 1024, 256, back=CAULK, facing='s', edge=T('teal')))


def wave_pool():
    """Blue Thunder: beach ramp from the promenade down to the deep end, Coconut Island, the wave machine's intake
    (the secret) in the south wall under water"""
    x0, y0, x1, y1 = WAVE
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': T('pooltile')}
    basin(WAVE, WAVE_Z, tl, south_wall=False)
    # south wall below the deck: thick, with the intake recess in the middle
    rx0, rx1, rb, rz = -64, 64, -112, -40       # intake recess: sill at rb, top at rz (just under the surface: bots
                                                # never dived to the deep floor, 0 probe visits in a 3-minute match)
    K.add(box((x0 - 16, Y0 - 128, WAVE_Z - 16), (x1 + 16, Y0 - 16, WAVE_Z), tl, detail=False),
          box((x0 - 16, Y0 - 112, WAVE_Z), (rx0, Y0, -32), tl, detail=False), box((rx1, Y0 - 112, WAVE_Z), (x1 + 16, Y0, -32), tl, detail=False),
          box((rx0, Y0 - 112, rz), (rx1, Y0, -32), tl, detail=False), box((rx0, Y0 - 112, WAVE_Z), (rx1, Y0 - 64, rz), tl, detail=False),
          box((rx0, Y0 - 64, WAVE_Z), (rx1, Y0, rb), tl, detail=False))
    beach = {'top': T('beach'), 'side': T('pooltile'), 'bot': CAULK}
    ramp = RAMP(x0, BEACH_Y, x1, y1, WAVE_Z, 0, 'n', beach, base=WAVE_Z)
    ix, iy = ISLE
    sand = {'top': T('beach'), 'side': T('pooltile'), 'bot': CAULK}
    isle = [cyl(ix, iy, 264, WAVE_Z, -26, sand, 16), cyl(ix, iy, 216, -26, -10, sand, 16), cyl(ix, iy, 168, -10, 6, sand, 16)]
    K.add(*isle)
    K.reserve(((x0, y0, WAVE_Z), (x1, y1, 0)))                        # nothing gets scattered into the pool
    drain = box((-1436, -1706, WAVE_Z), (-1364, -1634, WAVE_Z + 8), P_)              # the Drain Pipe's pad disc (dive_tower)
    K.water_box((x0, y0, WAVE_Z), (x1, y1, WATER), T('water'), cutters=[ramp, drain] + isle)
    K.add(box((rx0, Y0 - 64, rb), (rx1, Y0, rz), T('water_nd')))
    K.spots.setdefault('water', []).append(dict(mn=[rx0, Y0 - 64, rb], mx=[rx1, Y0, rz], depth=0))
    K.secret((rx0 + 8, Y0 - 56, rb + 4), (rx1 - 8, Y0 - 16, rz - 8), dest=(VAULT_C[0], VAULT_C[1] - 128, VAULT_Z), angle=90,
             name='intake', approach='n')
    # wave machine grilles on the south wall + the deep end sign
    for gx in (-1280, -768, -256, 256, 768, 1280):
        K.add(sign_box((gx - 112, Y0, 16), (gx + 112, Y0 + 6, 176), T('grille'), 256, 256, back=CAULK, facing='n', edge=T('steel')))
    K.add(sign_box((-128, Y0, 224), (128, Y0 + 6, 288), T('sign_deep'), 512, 128, back=CAULK, facing='n', edge=T('steel')))
    K.speaker(0, -900, 64, 'ambient/water_rippling'); K.speaker(0, -1600, 64, 'ambient/water_flowing')
    K.route('beach', (0, -380, 0), (530, -400, 0))                       # clear of the loop post (600, -310) and a ring (400, -360)


def shallow_pool(rect, step_sides):
    x0, y0, x1, y1 = rect
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': CAULK}
    basin(rect, SHALLOW, tl)
    cut = []
    for s in step_sides:
        if s == 'w': cut += STAIRS(x0, y0, x0 + 64, y1, SHALLOW, -16, 'w', tl)
        if s == 'e': cut += STAIRS(x1 - 64, y0, x1, y1, SHALLOW, -16, 'e', tl)
        if s == 's': cut += STAIRS(x0 + (64 if 'w' in step_sides else 0), y0, x1 - (64 if 'e' in step_sides else 0), y0 + 64, SHALLOW, -16, 's', tl)
        if s == 'n': cut += STAIRS(x0 + (64 if 'w' in step_sides else 0), y1 - 64, x1 - (64 if 'e' in step_sides else 0), y1, SHALLOW, -16, 'n', tl)
    K.reserve(((x0, y0, SHALLOW), (x1, y1, 0)))
    K.water_box((x0, y0, SHALLOW), (x1, y1, WATER), T('water'), cutters=cut)
    K.speaker((x0 + x1) / 2, (y0 + y1) / 2, 48, 'ambient/water_flowing')


def tower():
    """Twister Tower: three decks round a core, 16u stair flights wrapping it (west, north, east), crow's nest on top"""
    x0, y0, x1, y1 = CORE
    br = []
    slab = lambda r, z: br.append(box((r[0], r[1], z - 16), (r[2], r[3], z), P_))
    slab(CORE, LV[0]); slab((x0 - 128, y1, x1, y1 + 128), LV[0])                 # L1 + north strip
    slab(CORE, LV[1]); slab((x1, y0, x1 + 128, y1 + 128), LV[1])                 # L2 + east strip
    slab(CORE, LV[2]); slab((x0, y0 - 128, x1 + 128, y0), LV[2])                 # L3 + south strip
    def col(cx, cy, top):
        for a, b in ((0, 240), (256, 496), (512, 752)):
            if a < top: br.append(box((cx, cy, a), (cx + 32, cy + 32, min(b, top - 16)), P_))
    for (cx, cy) in ((x0, y0), (x1 - 32, y0), (x0, y1 - 32), (x1 - 32, y1 - 32)): col(cx, cy, LV[2])
    col(x0 - 128, y1 + 96, LV[0]); col(x1 - 32, y1 + 96, LV[0])
    col(x1 + 96, y1 + 96, LV[1]); col(x1 + 96, y0, LV[1])
    col(x0, y0 - 128, LV[2]); col(x1 + 96, y0 - 128, LV[2])
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    br.append(box((cx - 16, cy - 16, LV[2]), (cx + 16, cy + 16, NEST_Z - 16), P_))
    br.append(box((cx - 96, cy - 96, NEST_Z - 16), (cx + 96, cy + 96, NEST_Z), P_))
    K.solid_piece('tower', br, TX.texfn('gratem', 'tealm'))
    st = {'top': T('grate'), 'side': T('teal'), 'bot': T('teal')}
    STAIRS(x0 - 128, y0, x0 - 16, y1, 0, LV[0], 'n', st, route='tower_1')
    STAIRS(x0, y1 + 64, x1, y1 + 128, LV[0], LV[1], 'e', st)
    STAIRS(x1 + 64, y0, x1 + 128, y1, LV[1], LV[2], 's', st)
    K.keep_clear(x0 - 128, y0 - 128, x0, y0, 0)
    K.route('tower_2', (x0 - 64, y1 + 64, LV[0]), (x1 + 32, y1 + 64, LV[1]))
    K.route('tower_3', (x1 + 32, y1 + 64, LV[1]), (cx, cy - 120, LV[2]))
    K.jumppad(cx, y0 - 248, 0, land=(cx, y0 + 112, LV[0]), apex=LV[0] + 110, name='pad_tower', ceiling=LV[1] - 16,
              edges=[(cx, y0, LV[0])])
    K.jumppad(cx, cy - 170, LV[2], land=(cx, cy - 30, NEST_Z), apex=NEST_Z + 96, name='pad_nest', edges=[(cx, cy - 96, NEST_Z)])
    K.trigger_sound((cx - 90, cy - 90, NEST_Z), (cx + 90, cy + 90, NEST_Z + 72), 'human/applause', 'nest_applause', wait=20)
    K.light(cx, cy, 150, 300); K.light(cx, cy, LV[0] + 150, 300); K.light(cx, cy, LV[1] + 150, 300)
    for z in LV: K.keep_clear(x0, y0, x1, y1, z, z + 8)


def slides():
    """Sky Screamer (purple, from the top deck, through the loop, into the lagoon) and Twister (blue helix from the
    middle deck into the plunge pool). Collision = K.slide on the same points the flume MD3s were swept along."""
    K.slide(PURPLE_S, HW, WALLH, T('slick_nd'))
    for (x, y, z) in PURPLE[3:9]:
        K.add(cyl(x, y, 14, 0, z - 40, WCLIP, 8)); K.occupy_r(x, y, 20, 0, z)
    mx, my = LOOP[0], LOOP[1] - 150
    K.add(cyl(mx, my, 17, 0, loop_cz(), WCLIP, 8)); K.occupy_r(mx, my, 24, 0, 900)
    pl, o = FLUMES['purple']; K.custom(pl, float(o[0]), float(o[1]), 0, occupy=False)
    K.slide(TWIST, HW, WALLH, T('slick_nd'))
    in_pool = lambda x, y: PLUNGE[0] < x < PLUNGE[2] and y > PLUNGE[1]
    K.slide_skirt(TWIST, HW + 14, skip=in_pool)
    hx, hy = HELIX_C
    K.add(cyl(hx, hy, 19, 0, 540, WCLIP, 8)); K.occupy_r(hx, hy, 26, 0, 540)
    K.add(cyl(-800, 704, 14, 0, 484 - 40, WCLIP, 8)); K.occupy_r(-800, 704, 20, 0, 480)
    pl, o = FLUMES['blue']; K.custom(pl, float(o[0]), float(o[1]), 0, occupy=False)
    K.keep_clear(hx - 300, hy - 300, hx + 300, hy + 300, 0, 8)
    K.speaker(hx, hy, 300, 'ambient/water_flowing'); K.speaker(600, -160, 420, 'ambient/water_flowing')


def terrace():
    """sun terrace (z 128) in the north-east with the Banana Hut snack bar: walk in, serving hatch, flat roof by pad"""
    x0, y0, x1, y1 = TERR
    K.solid_piece('terrace', [box((x0, y0, 0), (x1, y1, TERR_Z), P_)], TX.texfn('deckm', 'panelm'))
    st = {'top': T('deck'), 'side': T('steel'), 'bot': T('steel')}
    STAIRS(x0 - 256, 1408, x0, 1568, 0, TERR_Z, 'e', st, route='terrace')
    K.keep_clear(x0 - 368, 1408, x0 - 256, 1568, 0); K.keep_clear(x0, 1392, x0 + 112, 1584, TERR_Z)
    sx0, sy0, sx1, sy1 = SHACK
    br = K.building(SHACK, TERR_Z, SHACK_H, openings=[('w', 1480, 1592, 0, 120), ('s', 1904, 2112, 48, 136)])
    br.append(box((1904, sy0 + 16, TERR_Z), (2112, sy0 + 48, TERR_Z + 48), P_))             # counter behind the hatch
    K.solid_piece('banana_hut', br, TX.texfn('roofm', 'hutwall'))
    K.add(sign_box((1880, sy0 - 4, TERR_Z + 150), (2136, sy0, TERR_Z + 200), T('sign_snack'), 512, 128, back=CAULK, facing='s', edge=T('steel')))
    K.keep_clear(sx0 - 112, 1464, sx0 + 112, 1608, TERR_Z)
    K.route('hut_door', (sx0 - 90, 1536, TERR_Z), (sx0 + 110, 1536, TERR_Z))
    K.light((sx0 + sx1) / 2, (sy0 + sy1) / 2, TERR_Z + 150, 350)
    top = TERR_Z + SHACK_H + 16
    K.jumppad(1620, 1320, TERR_Z, land=(1960, 1520, top), apex=top + 130, name='pad_hut', edges=[(sx0, 1440, top)])
    K.botclip_rect(x0, y0, x1, y1, TERR_Z, sides='sw', gaps=[('w', 1408, 1568), ('s', 1640, 1760)])
    for i, cup in enumerate(('pad_cups/pad_cup02.md3', 'pad_cups/pad_cup05.md3', 'pad_cups/pad_cup07.md3')):
        K.model_on(cup, 1940 + 64 * i, sy0 + 32, TERR_Z + 48, scale=0.25, angle=40 * i)


def shop():
    """Surf Shop against the west wall: door + window east, roof by the 16u stairs on its south side or the pad"""
    x0, y0, x1, y1 = SHOP
    br = K.building(SHOP, 0, SHOP_H, openings=[('e', 32, 160, 0, 128), ('e', 208, 304, 48, 136)])
    br.append(box((x0 + 16, 200, 0), (x0 + 72, 320, 48), P_))                                # counter
    K.solid_piece('surf_shop', br, TX.texfn('roofm', 'shopwall'))
    st = {'top': T('deck'), 'side': T('teal'), 'bot': T('teal')}
    STAIRS(x0, y0 - 128, x0 + 480, y0, 0, SHOP_H + 16, 'w', st)
    K.route('shop_roof', (x0 + 540, y0 - 64, 0), (x0 + 80, y0 + 96, SHOP_H + 16))     # top tread is in the corner: step north onto the roof
    K.keep_clear(x0 + 480, y0 - 128, x0 + 592, y0, 0)
    K.add(sign_box((x1, 0, 150), (x1 + 4, 256, 206), T('sign_shop'), 512, 128, back=CAULK, facing='e', edge=T('steel')))
    K.keep_clear(x1 - 112, 16, x1 + 112, 176, 0)
    K.route('shop_door', (x1 + 90, 96, 0), (x1 - 110, 96, 0))
    K.light((x0 + x1) / 2, (y0 + y1) / 2, 150, 350)
    K.jumppad(x1 + 200, 440, 0, land=(x1 - 140, 240, SHOP_H + 16), apex=SHOP_H + 16 + 130, name='pad_shop',
              edges=[(x1, 300, SHOP_H + 16)])
    for i, m in enumerate(('pad_items/towelstack.md3', 'pad_items/towelstack_2.md3')):
        K.model_on(m, x0 + 44, 232 + 56 * i, 48, scale=0.6, angle=90)


def guard():
    """lifeguard tower by the deep end: ramp up to the porch, open hut, roof by pad"""
    x0, y0, x1, y1 = GUARD; z = GUARD_Z
    br = [box((x0, y0, z - 16), (x1, y1, z), P_)]
    for (cx, cy) in ((x0, y0), (x1 - 24, y0), (x0, y1 - 24), (x1 - 24, y1 - 24)):
        br.append(box((cx, cy, 0), (cx + 24, cy + 24, z - 16), P_))
    hut = (x0, y0, x1, y0 + 160)
    br += K.building(hut, z, HUT_H, openings=[('n', x0 + 72, x1 - 72, 0, 104), ('s', x0 + 40, x1 - 40, 40, 104),
                                              ('e', y0 + 40, y0 + 120, 40, 104), ('w', y0 + 40, y0 + 120, 40, 104)], wall_t=8)
    K.solid_piece('lifeguard', br, TX.texfn('planks', 'redwhite'))
    RAMP(x0 + 64, y1, x1 - 64, y1 + 320, 0, z, 's', {'top': T('grate'), 'side': T('steel'), 'bot': T('steel')}, route='guard_ramp')
    K.keep_clear(x0 + 64, y1 + 320, x1 - 64, y1 + 432, 0)
    K.add(sign_box((x0 + 16, y1 - 164, z + 106), (x1 - 16, y1 - 160, z + 126), T('sign_guard'), 512, 128, back=CAULK,
                   facing='n', edge=T('steel')))
    top = z + HUT_H + 16
    K.jumppad(x0 - 150, y0 + 80, 0, land=(x0 + 128, y0 + 80, top), apex=top + 130, name='pad_guard', edges=[(x0, y0 + 80, top)])
    K.botclip_rect(x0, y0 + 160, x1, y1, z, sides='ew')


def vault():
    """sealed pump room below the world: the secret's loot and a teleporter back to the beach"""
    x0, y0, x1, y1 = VAULT_C[0] - 256, VAULT_C[1] - 256, VAULT_C[0] + 256, VAULT_C[1] + 256; z = VAULT_Z
    t = {'side': T('pooltile'), 'top': T('grate'), 'bot': T('steel')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 256), (x1 + 32, y1 + 32, z + 288), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 256), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 256), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 256), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 256), t, detail=False))
    K.item('item_padpower', -128, 96, z); K.item('item_revival', 0, 160, z); K.item('holdable_killerducks', 128, 96, z)
    K.item('item_armor_padshield', 0, 0, z)
    K.teleporter((-48, y1 - 64, z), (48, y1, z + 96), dest=(0, -330, 0), angle=90, name='vault_exit')
    K.light(0, 0, z + 200, 500, '0.6 0.9 1')
    K.speaker(0, 0, z + 100, 'machine/mechanics')
    for (x, y) in ((-190, -190), (190, -190)):
        K.catalog('pad_bath/deocan1.md3', x, y, z, scale=1.0)


# ------------------------------------------------------------------------------------------------ Volcano Bay
def river_rects():
    ox0, oy0, ox1, oy1 = RIV_O; ix0, iy0, ix1, iy1 = RIV_I
    return [(ox0, oy0, ox1, iy0), (ox0, iy1, ox1, oy1), (ox0, iy0, ix0, iy1), (ix1, iy0, ox1, iy1)]


def bay_shell():
    """open-air annex: sand floor with the lazy-river ring cut out, rock cliffs, sky"""
    sand = {'top': T('beach'), 'side': T('pooltile'), 'bot': CAULK}
    for r in sub_rects((AX0 - 32, AY0, AX1 + 32, AY1 + 32), river_rects()):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), sand, detail=False))
    ox0, oy0, ox1, oy1 = RIV_O; ix0, iy0, ix1, iy1 = RIV_I
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': CAULK}
    K.add(box((ox0 - 16, oy0 - 16, SHALLOW - 16), (ox1 + 16, oy1 + 16, SHALLOW), tl, detail=False),
          box((ox0 - 16, oy0 - 16, SHALLOW), (ox0, oy1 + 16, -32), tl, detail=False), box((ox1, oy0 - 16, SHALLOW), (ox1 + 16, oy1 + 16, -32), tl, detail=False),
          box((ox0, oy0 - 16, SHALLOW), (ox1, oy0, -32), tl, detail=False), box((ox0, oy1, SHALLOW), (ox1, oy1 + 16, -32), tl, detail=False),
          box((ix0, iy0, SHALLOW), (ix1, iy1, -32), tl, detail=False))
    for (side, mn, mx) in (('e', (AX0 - 32, AY0), (AX0, AY1 + 32)), ('w', (AX1, AY0), (AX1 + 32, AY1 + 32)), ('s', (AX0, AY1), (AX1, AY1 + 32))):
        for z0, z1, tex in ((0, CLIFF_H, T('cliff')), (CLIFF_H, ZTOP, T('sky'))):
            t = dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{side: tex})
            K.add(box((mn[0], mn[1], z0), (mx[0], mx[1], z1), t, detail=False))
    K.add(box((AX0 - 32, AY0, ZTOP), (AX1 + 32, AY1 + 32, ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))


def river():
    """Rio Loco: a 40u-deep lazy river round the volcano island with a gentle current, steps out on every straight,
    three humpback bridges you can float under"""
    ox0, oy0, ox1, oy1 = RIV_O; ix0, iy0, ix1, iy1 = RIV_I
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': CAULK}
    cut = []
    cut += STAIRS(-400, oy0, -272, oy0 + 64, SHALLOW, -16, 's', tl) + STAIRS(-400, iy0 - 64, -272, iy0, SHALLOW, -16, 'n', tl)
    cut += STAIRS(272, oy1 - 64, 400, oy1, SHALLOW, -16, 'n', tl) + STAIRS(272, iy1, 400, iy1 + 64, SHALLOW, -16, 's', tl)
    cut += STAIRS(ox0, 3100, ox0 + 64, 3228, SHALLOW, -16, 'w', tl) + STAIRS(ix0 - 64, 3100, ix0, 3228, SHALLOW, -16, 'e', tl)
    cut += STAIRS(ox1 - 64, 2400, ox1, 2528, SHALLOW, -16, 'e', tl) + STAIRS(ix1, 2400, ix1 + 64, 2528, SHALLOW, -16, 'w', tl)
    for (x, y, z, zb) in CHUTE_POSTS:
        pc = cyl(x, y, 14, zb, z - 40, WCLIP, 8); K.add(pc); K.occupy_r(x, y, 20, zb, z)
        if zb < 0: cut.append(pc)
    for r in river_rects():
        K.reserve(((r[0], r[1], SHALLOW), (r[2], r[3], 0)))
        K.water_box((r[0], r[1], SHALLOW), (r[2], r[3], WATER), T('water'), cutters=cut)
    # humpback bridges (deck 72: 104u over the river bed)
    br = []; bz = 72
    st = {'top': T('grate'), 'side': T('teal'), 'bot': T('teal')}
    cy = VC[1]
    # west and east bridges sit off the volcano's diagonals (south-west, north-east) where the island is widest
    for (a, b, by) in ((ox0, ix0, cy - 520), (ix1, ox1, cy + 520)):
        br.append(box((a, by - 80, bz - 16), (b, by + 80, bz), P_))
        RAMP(a - 128, by - 80, a, by + 80, 0, bz, 'e', st); RAMP(b, by - 80, b + 128, by + 80, 0, bz, 'w', st)
        K.keep_clear(a - 240, by - 80, a - 128, by + 80, 0); K.keep_clear(b + 128, by - 80, b + 240, by + 80, 0)
        K.route(f'bridge_{a}', (a - 190, by, 0), (b + 190, by, 0))
    br.append(box((380, oy0, bz - 16), (540, iy0, bz), P_))                                      # south bridge
    RAMP(380, oy0 - 128, 540, oy0, 0, bz, 'n', st); RAMP(380, iy0, 540, iy0 + 128, 0, bz, 's', st)
    K.keep_clear(380, iy0 + 128, 540, iy0 + 240, 0)
    K.route('bridge_s', (460, oy0 - 150, 0), (460, iy0 + 190, 0))
    K.solid_piece('bridges', br, TX.texfn('planks', 'tealm'))
    # the current runs anticlockwise; short jets in the middle of each straight
    K.current((-100, oy0 + 8, SHALLOW), (100, iy0 - 8, 0), 0, 240, 'cur_s')
    K.current((ix1 + 8, 2900, SHALLOW), (ox1 - 8, 3100, 0), 90, 240, 'cur_e')
    K.current((-100, iy1 + 8, SHALLOW), (100, oy1 - 8, 0), 180, 240, 'cur_n')
    K.current((ox0 + 8, 2600 - 40, SHALLOW), (ix0 - 8, 2760, 0), 270, 240, 'cur_w')
    for (x, y) in ((0, 2080), (0, 3650), (-784, 2864), (784, 2864)): K.speaker(x, y, 40, 'ambient/water_flowing')


def volcano():
    """Mount Kaboom: five rock terraces (flat, walkable, bot friendly) up to the lava cap at z 640. 16u flights spiral
    up tiers 1-4 (south, east, north, west), a pad from tier 4 to the summit, a geyser from the island straight to the
    summit and one from the east beach to tier 2, a waterfall down the south, and the Lava Chute flume from tier 4
    round the north-west into the river"""
    cx, cy = VC; c = math.cos(math.pi / 8); A = TIER_A; Z = TIER_Z
    tiers = [cyl(cx, cy, A[i] / c, 0 if i == 0 else Z[i - 1], Z[i], P_, 8) for i in range(5)]
    K.solid_piece('volcano', tiers, TX.texfn('sandrock', 'cliffm'))
    K.add(cyl(cx, cy, 90, Z[4], Z[4] + 4, {'top': T('lava'), 'side': T('lava'), 'bot': CAULK}, 8))
    st = {'top': T('beach'), 'side': T('cliff'), 'bot': T('cliff')}
    STAIRS(cx - 10, cy - A[0] - 64, cx + 246, cy - A[0], 0, Z[0], 'e', st)
    STAIRS(cx + A[1], cy - 128, cx + A[1] + 64, cy + 128, Z[0], Z[1], 'n', st)
    STAIRS(cx - 128, cy + A[2], cx + 128, cy + A[2] + 64, Z[1], Z[2], 'w', st)
    STAIRS(cx - A[3] - 64, cy - 106, cx - A[3], cy + 150, Z[2], Z[3], 's', st)
    K.keep_clear(cx - 122, cy - A[0] - 64, cx - 10, cy - A[0], 0)
    K.route('volcano_1', (cx - 70, cy - A[0] - 32, 0), (cx + 200, cy - A[0] + 50, Z[0]))
    K.route('volcano_2', (cx + A[1] + 50, cy - 190, Z[0]), (cx + A[1] - 50, cy + 110, Z[1]))
    K.route('volcano_3', (cx + 190, cy + A[2] + 50, Z[1]), (cx - 100, cy + A[2] - 50, Z[2]))
    K.route('volcano_4', (cx - A[3] - 50, cy + 200, Z[2]), (cx - A[3] + 50, cy - 80, Z[3]))
    K.jumppad(cx + 60, cy - 200, Z[3], land=(cx + 60, cy - 60, Z[4]), apex=Z[4] + 96, name='pad_summit', edges=[(cx + 60, cy - A[4], Z[4])])
    K.jumppad(cx + 620, cy + 320, 0, land=(cx + 80, cy + 60, Z[4]), apex=Z[4] + 150, name='geyser_crater',
              edges=[(cx + A[4], cy + 70, Z[4])], light_rgb='0.5 0.8 1')
    K.jumppad(1180, cy - 150, 0, land=(cx + 424, cy - 150, Z[1]), apex=Z[1] + 190, name='geyser_bay',
              edges=[(cx + A[1], cy - 150, Z[1])], light_rgb='0.5 0.8 1')
    K.trigger_sound((cx - 80, cy - 80, Z[4] + 4), (cx + 80, cy + 80, Z[4] + 76), 'human/applause', 'crater_applause', wait=20)
    # waterfall: sheets down the south faces (visual only)
    X = ML.Model(); f = X.mesh(TX.mats['fall'])
    for i in range(5):
        y = -(A[i] + 3); z1 = Z[i]; z0 = 0 if i == 0 else Z[i - 1]
        f.poly([(-30, y, z0), (-150, y, z0), (-150, y, z1), (-30, y, z1)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        if i < 4: f.poly([(-150, y, z1 + 3), (-30, y, z1 + 3), (-30, -(A[i + 1] + 3), z1 + 3), (-150, -(A[i + 1] + 3), z1 + 3)], (0, 0, 1),
                         [(0, 1), (1, 1), (1, 0), (0, 0)])
    K.custom(ML.save('waterfall', X), cx, cy, 0, lit=False, occupy=False)
    K.speaker(cx - 90, cy - A[0] - 40, 80, 'ambient/water_flowing')
    K.light(cx, cy, Z[4] + 120, 300, '1 0.5 0.2')
    for (dx, dy, z) in ((-340, -610, 0), (379, 379, Z[0]), (-300, 300, Z[1]), (220, -220, Z[2])):
        K.custom(ML.PLACE['rock'], cx + dx, cy + dy, z, angle=(dx * 7) % 360, cyls=[(0, 0, 48, 0, 70)])
    # Lava Chute
    K.slide(CHUTE_S, HW, WALLH, T('slick_nd'))
    X = ML.Model(); ML.flume(X, CHUTE_S, HW, WALLH, TX.mats['orange'])
    for (x, y, z, zb) in CHUTE_POSTS: post(X, x, y, z, zb)
    o = np.array([cx - 400.0, cy + 500.0, 0.0]); X.shift(o)
    K.custom(ML.save('flume_orange', X), float(o[0]), float(o[1]), 0, occupy=False)
    K.speaker(cx - 560, cy + 740, 300, 'ambient/water_flowing')


def dive_tower():
    """The Plank: dive tower on the west deck by the deep end. Three levels (16u flights wrapping west, north, east),
    boards out over the pool from levels 2 and 3, Bam Bam on top; a ground pad and the Drain Pipe (a glass suction
    tube from the deep floor) are the quick ways up"""
    x0, y0, x1, y1 = DIVE; Z = DIVE_Z
    br = []
    slab = lambda r, z: br.append(box((r[0], r[1], z - 16), (r[2], r[3], z), P_))
    slab(DIVE, Z[0]); slab((x0 - 80, y1, x1, y1 + 128), Z[0])
    slab(DIVE, Z[1]); slab((x1, y0, x1 + 128, y1 + 128), Z[1])
    slab(DIVE, Z[2]); slab((x0, y0 - 128, x1 + 128, y0), Z[2])
    slab((x1 + 128, y1 + 40, x1 + 380, y1 + 88), Z[1])                              # board, level 2
    slab((x1 + 128, y0 - 100, x1 + 420, y0 - 36), Z[2])                             # board, level 3 (64 wide: over water, no botclip)
    def col(cx, cy, top):
        for a, b in ((0, Z[0] - 16), (Z[0], Z[1] - 16), (Z[1], Z[2] - 16)):
            if a < top: br.append(box((cx, cy, a), (cx + 24, cy + 24, min(b, top - 16)), P_))
    for (cx, cy) in ((x0, y0), (x1 - 24, y0), (x0, y1 - 24), (x1 - 24, y1 - 24)): col(cx, cy, Z[2])
    col(x1 - 24, y1 + 104, Z[0]); col(x1 + 104, y1 + 104, Z[1]); col(x1 + 104, y0, Z[1])
    col(x0, y0 - 128, Z[2]); col(x1 + 104, y0 - 128, Z[2])
    K.solid_piece('dive_tower', br, TX.texfn('gratem', 'steelw'))
    st = {'top': T('grate'), 'side': T('steel'), 'bot': T('steel')}
    STAIRS(x0 - 80, y0, x0 - 16, y1, 0, Z[0], 'n', st, route='dive_1')
    STAIRS(x0, y1 + 64, x1, y1 + 128, Z[0], Z[1], 'e', st)
    STAIRS(x1 + 64, y0, x1 + 128, y1, Z[1], Z[2], 's', st)
    K.keep_clear(x0 - 80, y0 - 112, x0 - 16, y0, 0)
    K.route('dive_3', (x0 - 48, y1 + 64, Z[0]), ((x0 + x1) / 2, (y0 + y1) / 2, Z[2]))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    K.jumppad(x0 - 220, cy, 0, land=(cx, cy, Z[2]), apex=Z[2] + 130, name='pad_dive', edges=[(x0, cy, Z[2])])
    M = TX.mats
    K.tube_lift(-1400, -1670, WAVE_Z, (x1 - 60, y0 - 70, Z[2]), Z[2] + 170, 'drain_pipe', M['glass'], M['chrome'], arc=True,
                mouth=M['chrome'], edges=[(x1 + 128, y0 - 100, Z[2])])
    K.item('holdable_bambam', cx + 40, cy + 40, Z[2])
    for i in range(3): K.item('item_armor_shard', x1 + 200 + 70 * i, y0 - 68, Z[2])
    K.ammo('imperius', x1 + 330, y1 + 64, Z[1])


def tiki():
    """Tiki Bar on the west beach: door east, serving hatch south, thatch roof up the 16u flight on its north side"""
    x0, y0, x1, y1 = TIKI
    br = K.building(TIKI, 0, TIKI_H, openings=[('e', y0 + 120, y0 + 232, 0, 120), ('s', x0 + 60, x1 - 60, 48, 136)])
    br.append(box((x0 + 60, y0 + 16, 0), (x1 - 60, y0 + 48, 48), P_))
    K.solid_piece('tiki_bar', br, TX.texfn('thatch', 'bamboo'))
    STAIRS(x0, y1, x0 + 384, y1 + 128, 0, TIKI_H + 16, 'w', {'top': T('beach'), 'side': T('cliff'), 'bot': T('cliff')}, route='tiki_roof')
    K.keep_clear(x0 + 384, y1, x0 + 496, y1 + 128, 0); K.keep_clear(x1 - 112, y0 + 104, x1 + 112, y0 + 248, 0)
    K.route('tiki_door', (x1 + 90, y0 + 176, 0), (x1 - 110, y0 + 176, 0))
    K.add(sign_box((x0 + 40, y0 - 4, 142), (x1 - 40, y0, 176), T('sign_tiki'), 512, 128, back=CAULK, facing='s', edge=T('teal')))
    K.light((x0 + x1) / 2, (y0 + y1) / 2, 120, 300, '1 0.8 0.5')
    for i, cup in enumerate(('pad_cups/pad_cup01.md3', 'pad_cups/pad_cup04.md3', 'pad_cups/pad_cup08.md3')):
        K.model_on(cup, x0 + 100 + 50 * i, y0 + 32, 48, scale=0.25, angle=70 * i)
    K.model_on('pad_ddmix/padship/rumbottle1.md3', x0 + 250, y0 + 32, 48, scale=0.35)


def bay_dressing():
    for i, (x, y) in enumerate(((-1450, 1900), (-1100, 2250), (-1380, 3250), (-1150, 3600), (1380, 1990), (1150, 2300),
                                (1450, 3300), (1100, 3620), (-420, 2250), (560, 3480), (-600, 3180), (600, 2620), (-1250, 2060))):
        K.prop(ML.PLACE['palm'], x, y, 0, cyls=[(0, 0, 15, 0, 300)], angle=(i * 83) % 360, lit=False)
    for i, (x, y, a) in enumerate(((-1300, 2200, 100), (-1300, 2300, 100), (1350, 3050, 270), (1350, 3150, 270), (1350, 3250, 270),
                                   (-1350, 3400, 90), (-1350, 3500, 90), (1300, 2100, 250))):
        K.prop(ML.PLACE['lounger_r' if i % 2 else 'lounger_b'], x, y, 0, boxes=[((-22, -62, 0), (22, 40, 30))], angle=a)
    for i, (x, y) in enumerate(((-1380, 2250), (1420, 3150), (-1420, 3450), (1380, 2100))):
        K.prop(ML.PLACE['parasol_r' if i % 2 else 'parasol_y'], x, y, 0, cyls=[(0, 0, 6, 0, 150)], angle=0)
    for (x, y, a) in ((1250, 3450, 20), (-1100, 3050, 80), (1050, 1880, 0)):
        K.prop(ML.PLACE['cart'], x, y, 0, boxes=[((-58, -32, 0), (58, 32, 88))], angle=a)
    for (x, y) in ((-1250, 1850), (1300, 2700), (-1050, 3350), (1480, 3600), (-1500, 2200)):
        K.prop(ML.PLACE['rock'], x, y, 0, cyls=[(0, 0, 48, 0, 70)])
    # island rocks: only the corners between the volcano's octagon and the river have room (K.prop would nudge them out
    # over the water: the volcano occupies its whole bounding square)
    for (dx, dy, a) in ((600, -602, 90), (-560, 560, 30)):
        K.custom(ML.PLACE['rock'], VC[0] + dx, VC[1] + dy, 0, angle=a, cyls=[(0, 0, 48, 0, 70)])
    for i, (x, y) in enumerate(((-1000, 2100), (1050, 3200), (-1050, 2700), (1000, 2450), (1200, 2000))):
        K.prop(ML.PLACE['ring_o' if i % 2 else 'ring_g'], x, y, 0, cyls=[(0, 0, 56, 0, 30)], angle=0)
    for (x, y) in ((-1540, 2000), (-1540, 3050), (1540, 2450), (1540, 3450), (-1540, 3700)):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, scale=0.5, angle=90)
    for (x, y) in ((-1400, 2380), (1400, 2880), (-300, 1850), (200, 1850), (-1200, 3720), (900, 3790), (-600, 3790)):
        K.catalog('pad_sunflower/pad_sunflower_l.md3', x, y, 0, scale=0.45, clip=False)
    for (x, y) in ((1450, 2250), (-1100, 2560), (1100, 2900)):
        K.catalog('pad_ddmix/plants/waterplant1b.md3', x, y, 0, scale=0.5, clip=False)
    for (x, y) in ((-1150, 1880), (1250, 3600), (-560, 2700)):
        K.catalog('pad_ducks/pad_duck.md3', x, y, 0, scale=0.3)
    K.catalog('pad_statues/statue_super.md3', 1450, 2640, 0, scale=0.7, angle=180)
    K.timer_sound(VC[0], VC[1], 600, 'ambient/slime_bubbling', 'lava_bubbles', 12, 6)
    # fill lights: the hall wall shades the bay's south beach and the west cliff shades its west strip (light_check)
    for x in range(-1400, 1401, 400): K.light(x, 1900, 220, 380, '1 0.95 0.85')
    for y in range(2300, 3701, 450): K.light(-1480, y, 220, 340, '1 0.95 0.85')


def hall_extras():
    """the second helping: Banana Drop kiddie flume off the terrace, blimps orbiting under the vault, neon over the
    flume entries"""
    M = TX.mats
    # Banana Drop
    K.slide(YELLOW, HW, WALLH, T('slick_nd'))
    K.slide_skirt(YELLOW, HW + 14, skip=lambda x, y: y < LAGOON[3])
    X = ML.Model(); ML.flume(X, YELLOW, HW, WALLH, M['yellow'])
    o = np.array([1700.0, 1100.0, 0.0]); X.shift(o)
    K.custom(ML.save('flume_yellow', X), 1700, 1100, 0, occupy=False)
    K.keep_clear(1640, 1216, 1760, 1330, TERR_Z)
    # blimps: one IQM on a func_rotating under the vault
    X = ML.Model()
    for k, (kind, mat) in enumerate((('duck', 'blimp_y'), ('ball', 'blimp_r'), ('ring', 'blimp_g'), ('ball', 'blimp_b'),
                                     ('ring', 'blimp_r'), ('duck', 'blimp_y'))):
        a = 2 * math.pi * k / 6
        c = np.array([BLIMP_R * math.cos(a), BLIMP_R * math.sin(a), (k % 2) * 20 - 10.0])
        d = np.array([-math.sin(a), math.cos(a), 0]); side = np.array([math.cos(a), math.sin(a), 0]); up = np.array([0, 0, 1.0])
        R = np.stack([side, d, up], 1)
        if kind == 'ball': sphere(X.mesh(M[mat]), c, 52, 14, 10, u1=2)
        elif kind == 'ring':
            ring = [c + up * 44 * math.sin(t) + d * 44 * math.cos(t) for t in np.linspace(0, 2 * math.pi, 21)]
            tube(X.mesh(M[mat]), ring, 15, nseg=10, caps=(False, False), vlen=40)
        else:
            ellipsoid(X.mesh(M[mat]), c, 34, 56, 34, nu=12, nv=8, R=R)
            sphere(X.mesh(M[mat]), c + d * 44 + up * 34, 24, 10, 8)
            ellipsoid(X.mesh(M['blimp_r']), c + d * 70 + up * 30, 10, 14, 6, nu=8, nv=6, R=R)
            for sg in (-1, 1): sphere(X.mesh(M['black_d']), c + d * 58 + up * 42 + side * sg * 14, 4, 6, 4)
    K.rotating_model2(ML.save_iqm('blimps', X), (0, 0, BLIMP_Z), speed=7)
    # (the rocking floats on the wave pool were removed: with five func_pendulum movers on the water, bots never
    #  entered the pool in four matches - 0 probe visits - and never found the secret; without them they did)
    # neon over the flume entries (hung under the deck edges)
    x0, y0, x1, y1 = CORE
    K.add(sign_box((x0 + 250, y0 - 128, LV[2] - 80), (x1 + 90, y0 - 124, LV[2] - 16), T('sign_scream'), 512, 128, back=CAULK,
                   facing='s', edge=T('teal')))
    K.add(sign_box((x0 - 4, y1 - 230, LV[1] - 80), (x0, y1 - 20, LV[1] - 16), T('sign_twist'), 512, 128, back=CAULK,
                   facing='w', edge=T('teal')))


def bay_items():
    cx, cy = VC
    K.weapon('betty', cx, cy, TIER_Z[4] + 4, marker='black')
    K.weapon('boaster', TIKI[0] + 160, TIKI[1] + 250, 0, marker='orange')
    K.weapon('splasher', 0, 3648, SHALLOW, marker='blue')
    K.weapon('bubbleg', 1300, 3000, 0, marker='green')
    for w, (x, y, z) in (('betty', (cx - 379, cy + 379, TIER_Z[0])), ('boaster', (-1100, 3200, 0)), ('splasher', (-784, 2400, SHALLOW)),
                         ('bubbleg', (1200, 2200, 0)), ('splasher', (cx - 300, cy - 300, TIER_Z[1])), ('pumper', (784, 3300, SHALLOW)),
                         ('balloony', (-1300, 3650, 0)), ('balloony', (cx - 536, cy - 100, TIER_Z[0]))):
        K.ammo(w, x, y, z)
    K.ammo('nipper', 0, 1880, 0); K.ammo('nipper', 1400, 3700, 0)
    K.item('holdable_boomies', TIKI[0] + 100, TIKI[1] + 120, TIKI_H + 16)
    K.item('item_armor_padshield', cx + 312, cy + 40, TIER_Z[2])
    K.item('item_speedy', cx - 200, cy + 60, TIER_Z[3])
    K.item('item_climber', -1450, 3780, 0)
    for (x, y) in ((-600, 2080), (600, 2080), (784, 2700), (-784, 3350), (-500, 3648), (500, 3648)):
        K.item('item_armor_shard', x, y, SHALLOW)
    K.station(1500, 3000, 0, ang=180)
    for (x, y, a) in ((-1300, 2000, 45), (1300, 1900, 135), (-1350, 3700, 315), (1350, 3720, 225), (0, 2260, 270), (-600, 3200, 0)):
        K.spawn(x, y, 0, a)


# ------------------------------------------------------------------------------------------------ dressing
PALMS = [(-1700, -520), (-1900, -880), (-2040, -1000), (1650, -520), (2000, -700), (1750, -1480), (-900, -300),
         (-150, -330), (700, -330), (1300, -300), (300, 600), (760, 1000), (180, 1500), (1000, 1380), (-1900, 700),
         (-1750, 1480), (-700, 1500), (1150, 1100), (2000, 120)]
LOUNGERS = [(-1640, -700, 90), (-1640, -800, 90), (-1640, -900, 90),
            (1640, -700, 270), (1640, -800, 270), (1640, -1300, 270), (1640, -1400, 270),
            (420, 900, 200), (520, 900, 200), (620, 900, 200), (500, 1380, 170), (600, 1380, 170), (700, 1380, 170),
            (-300, 1560, 180), (-200, 1560, 180), (1500, 1560, 180), (1600, 1620, 180)]
PARASOLS = [(-1700, -750), (1700, -750), (1700, -1350), (470, 960), (650, 1440), (-250, 1590), (1560, 1580)]
CARTS = [(-1000, 60, 0), (1000, 150, 90), (240, 1150, 30), (-1500, 300, 60), (1900, -200, 0),
         (-1620, -610, 90), (1620, -610, 90)]          # the last two end the 3000u sightline along the beach


def dressing():
    for i, (x, y) in enumerate(PALMS):
        K.prop(ML.PLACE['palm'], x, y, 0, cyls=[(0, 0, 15, 0, 300)], angle=(i * 67) % 360, lit=False)
    ix, iy = ISLE
    K.custom(ML.PLACE['palm'], ix - 90, iy + 40, 6, angle=30, lit=False, cyls=[(0, 0, 15, 0, 300)])
    K.custom(ML.PLACE['palm'], ix + 70, iy - 90, 6, angle=200, lit=False, cyls=[(0, 0, 15, 0, 300)])
    K.custom(ML.PLACE['rock'], ix + 80, iy + 70, 6, angle=40, cyls=[(0, 0, 48, 0, 70)])
    K.catalog('pad_ducks/pad_duck.md3', ix - 30, iy - 40, 6, scale=0.55, angle=20, nudge=False)
    for i, (x, y, a) in enumerate(LOUNGERS):
        zs = TERR_Z if (x > TERR[0] and y > TERR[1]) else 0
        K.prop(ML.PLACE['lounger_r' if i % 2 else 'lounger_b'], x, y, zs, boxes=[((-22, -62, 0), (22, 40, 30))], angle=a)
    for i, (x, y) in enumerate(PARASOLS):
        zs = TERR_Z if (x > TERR[0] and y > TERR[1]) else 0
        K.prop(ML.PLACE['parasol_r' if i % 2 else 'parasol_y'], x, y, zs, cyls=[(0, 0, 6, 0, 150)], angle=0)
    for (x, y, a) in CARTS:
        K.prop(ML.PLACE['cart'], x, y, 0, boxes=[((-58, -32, 0), (58, 32, 88))], angle=a)
    for i, (x, y) in enumerate(((-1200, -330), (-500, -350), (400, -360), (1100, -340), (1760, 150), (-1700, 1100),
                                (-880, 1400), (2000, 1100), (-1750, -380), (1500, -900))):
        K.prop(ML.PLACE['ring_o' if i % 2 else 'ring_g'], x, y, 0, cyls=[(0, 0, 56, 0, 30)], angle=0)
    for (x, y) in ((-1300, 500), (1200, 620), (-60, 1300), (2100, -1500), (-2100, -1000)):
        K.prop(ML.PLACE['rock'], x, y, 0, cyls=[(0, 0, 48, 0, 70)])
    # catalog objects: bushes and flowers along the walls and round the garden, ducks, balls, towels, statue
    for (x, y) in ((-2170, 1500), (-1750, 1670), (-400, 1670), (500, 1670), (2176, 900), (2176, 500),
                   (2176, -1000), (-2176, -600), (-2176, -1350), (-2176, 1000)):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, scale=0.5, angle=90 if abs(x) > 2000 else 0)
    for (x, y) in ((100, 1250), (640, 1180), (900, 700), (150, 760), (-1500, 60), (1900, 1120), (-1100, 1670), (800, 1300)):
        K.catalog('pad_sunflower/pad_sunflower_l.md3', x, y, 0, scale=0.45, clip=False)
    for (x, y) in ((380, 1250), (1000, 1250), (-2100, 600), (2140, -400), (40, 420)):
        K.catalog('pad_ddmix/plants/flower_yellow.md3', x, y, 0, scale=0.3, clip=False)
    for (x, y) in ((-150, 1430), (1000, 480), (-1850, 1300)):
        K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, scale=0.6, lit=True)
    for (x, y) in ((-1350, -340), (760, -380), (1900, 200), (-820, 1300), (1500, 1120), (-1700, -330)):
        K.catalog('pad_ducks/pad_duck.md3', x, y, 0, scale=0.3)
    for (x, y, m) in ((-650, -200, 'pad_ball/pad_soccerball.md3'), (900, -320, 'pad_ball/pad_basketball.md3'),
                      (60, 1000, 'pad_ball/pad_soccerball.md3'), (1700, 1400, 'pad_ball/pad_basketball.md3')):
        zs = TERR_Z if (x > TERR[0] and y > TERR[1]) else 0
        K.catalog(m, x, y, zs, scale=0.4, clip=False)
    K.catalog('ente/padstatue_gold.md3', 0, 1520, 0, scale=0.9, angle=270)
    # cover where the promenade's east-west sightlines cross in front of Twister Tower (sight --hot)
    K.custom(ML.PLACE['cart'], 0, 200, 0, angle=90, boxes=[((-58, -32, 0), (58, 32, 88))])
    K.custom(ML.PLACE['rock'], -520, 40, 0, angle=70, cyls=[(0, 0, 48, 0, 70)])
    K.catalog('pad_statues/statue_super.md3', -1960, -700, 0, scale=0.7, angle=0)
    K.timer_sound(0, 0, 900, 'human/applause', 'crowd', 45, 20)


def items():
    cx, cy = (CORE[0] + CORE[2]) // 2, (CORE[1] + CORE[3]) // 2
    hut_top = TERR_Z + SHACK_H + 16; shop_top = SHOP_H + 16; guard_top = GUARD_Z + HUT_H + 16
    K.weapon('imperius', cx + 50, cy + 50, NEST_Z, marker='purple')
    K.weapon('betty', -40, -1680, WAVE_Z, marker='black')                 # deep floor right in front of the secret intake
    K.weapon('balloony', 2040, 1560, hut_top, marker='orange')
    K.weapon('pumper', GUARD[0] + 128, GUARD[1] + 80, guard_top, marker='green')
    K.weapon('splasher', ISLE[0] - 20, ISLE[1] + 110, 6, marker='blue')
    K.weapon('boaster', cx, cy + 120, LV[1], marker='orange')
    K.weapon('bubbleg', 200, 80, 0, marker='green')
    ammo = {'imperius': [(cx - 150, cy - 150, LV[2]), (2100, 1300, TERR_Z), (-1200, 1560, 0)],
            'betty': [(-620, -1560, WAVE_Z), (-2060, 250, 0), (1000, 1560, 0), (-300, 120, 0)],
            'balloony': [(1500, 1300, TERR_Z), (1900, 1650, TERR_Z), (300, 1650, 0)],
            'pumper': [(GUARD[0] + 128, GUARD[1] + 80, GUARD_Z), (2100, -300, 0), (-2150, -1620, 0)],
            'splasher': [(1700, 700, SHALLOW), (-1250, 1500, SHALLOW), (0, -700, -40), (-1700, -200, 0)],
            'boaster': [(cx + 150, cy - 100, LV[0]), (-1000, 400, 0), (900, 400, 0)],
            'bubbleg': [(-700, -150, 0), (1200, -330, 0), (-150, 1150, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((1500, -330), (-1900, 1500), (600, 250)): K.ammo('nipper', x, y, 0)
    K.item('item_armor_padshield', SHOP[0] + 200, 96, 0)
    K.item('item_jumper', SHOP[0] + 150, 100, shop_top)
    K.item('item_speedy', cx - 150, cy + 150, LV[0])
    K.item('holdable_floater', GUARD[0] + 128, GUARD[1] + 60, GUARD_Z)
    K.item('item_armor_padshield', 2000, 1560, TERR_Z)
    K.item('item_visionless', -1000, 1150, 0)
    for (x, y, z) in ((cx - 100, cy, LV[1]), (cx + 100, cy, LV[1]), (-1900, 100, shop_top), (1000, -900, -22), (-1000, -900, -22)):
        K.item('item_armor_shard', x, y, z)
    K.station(700, 1640, 0, ang=270)
    for (x, y, a) in ((-2100, -760, 45), (-2000, 1200, 315), (-1300, 300, 0), (-450, 1600, 270), (-200, 200, 270),
                      (400, 1500, 270), (900, 200, 180), (1250, 1500, 180), (2100, 150, 180), (2100, -1500, 135),
                      (1650, -330, 180), (-600, -330, 0), (0, 1150, 270), (-1900, -300, 0)):
        K.spawn(x, y, 0, a)


def shader():
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(215, 62), sun_int=110, skylight=(70, 3), cloud=f'textures/{NS}/clouds')],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    textures()
    models()
    shell(); wave_pool(); shallow_pool(LAGOON, 'ws'); shallow_pool(PLUNGE, 'en'); vault()
    bay_shell(); river(); volcano(); tiki()
    tower(); slides(); terrace(); shop(); guard(); dive_tower(); hall_extras()
    dressing(); bay_dressing(); items(); bay_items()
    if os.environ.get('PROBES'):                  # bot-test diagnosis build only (target_score gives points)
        K.probe((-96, -1690, -120), (96, -1640, -12), 'intake_front')
        K.probe((-64, -220, VAULT_Z), (64, -40, VAULT_Z + 96), 'vault_arrival')
        K.probe((150, 30, 0), (250, 130, 64), 'control_bubbleg')
        K.probe((-700, -1600, WAVE_Z), (-540, -1500, -60), 'deep_ammo')
        K.probe((-140, -1340, 6), (100, -1180, 70), 'island')
        K.probe((-400, -1100, -60), (400, -1000, 0), 'pool_mid_surface')
        K.probe((-400, -800, -60), (400, -700, 0), 'beach_shallows')
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
