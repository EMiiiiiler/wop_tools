#!/usr/bin/env python3
"""Midnight Snack (wop_padfridge) - FFA inside a giant open French-door fridge at midnight, built on woplib.

    OUT=<dir> python3 build_padfridge.py          (names come from mapinfo.json; wopbuild.py padfridge all)

Levels (see README.md for the design sheet):
  kitchen floor (z 0)   between the two open doors: a milk carton lying on its side (walk-through tunnel, pad onto the
                        roof, Boaster), a spilled-milk puddle, a giant apple, the jelly pad up to shelf 1
  crisper (z 0)         two clear crisper drawers (the east one pulled out into the kitchen) with lettuce, carrots and
                        tomatoes; Splasher inside the closed west drawer
  shelf 1 (z 448)       glass shelf: Swiss cheese wedge (walk through the tunnel, walk up the slope), jelly, yogurt pots
  shelf 2 (z 896)       glass shelf: egg box, pickle jar, cake; Pumper west, Betty east
  freezer (z 1344)      frosted tray with a slick ice patch, ice cubes, ice cream tub, frozen peas; Imperius (pad only)
  door bins             each door has three bins; the lower two join shelves 1 and 2, the top ones are pad-only
                        (Balloony east, the butter compartment west = the secret door to the Deep Freeze)
  back lane             the airflow gap behind the shelves: a chocolate-bar ramp, a butter block, a cracker ramp and a
                        cheese stack climb from the floor to shelf 2; a lift pad goes from there into the freezer
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import wopmap
from wopmap import box, cyl, hull, sub_rects, sign_box
from woplib.kit import MapKit, write_kit_textures, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                     # hull inner faces: -1728 -3584 1728 1088
ZTOP = 1920                                           # kitchen ceiling
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '14', '_color': '0.8 0.88 1'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout constants
IX0, IX1, IY0, IY1 = -1536, 1536, -768, 1024        # fridge interior (front opening at IY0)
IZ1 = 1792                                            # fridge interior ceiling
DOOR_IN = 1600                                        # inner face of each door (x = +-1600)
SHELF_Z = (448, 896, 1344)                            # shelf 1, shelf 2, freezer tray (walk surface)
SHELF_Y1 = 768                                        # shelves end here; the airflow lane runs 768..1024 behind them
LANE = (SHELF_Y1, IY1)
BIN_X = 1344                                          # door bins span x 1344..1600 (mirrored west)
BIN_Y0 = -2240
RAMP1 = (-1408, -544); LAND1 = (-544, -160); RAMP2 = (-160, 768); LAND2 = (768, 1152)
CARTON = (-1200, -1952, -368, -1632, 320)             # milk carton lying on its side: x0 y0 x1 y1 height
PUDDLE = (-368, -2032, 16, -1552)
DRAWER_W = (-1472, -704, -128, 640, 224)              # closed west crisper: x0 y0 x1 y1 rim height
DRAWER_E = (128, -1344, 1472, 64, 224)                # east crisper, pulled out into the kitchen
CHEESE = (400, -400, 1040, 48)
CEREAL = (-620, -1440, 20, -1248, 1400)             # cereal box standing in the kitchen                        # shelf 1 cheese wedge footprint
VAULT = (-320, -320, 320, 320); VAULT_Z = -1600       # the Deep Freeze (sealed, below the world)
CELLAR = (-512, -384, 512, 384); CELLAR_Z = -3200     # the Root Cellar (second secret, sealed)
DOOR_Y0 = -2368                                       # south end of both doors
CY0, CY1, CZ = Y0, -2944, 896                         # kitchen counter along the south wall: y range, worktop height
SINK = (-448, -3456, 448, -3072, 640)                 # sink basin x0 y0 x1 y1, basin floor
CUPBOARD = (512, -3520, 1152, CY1, 768)               # open cupboard under the worktop (walk in)
LIFT = (-1216, CY1, -1024, CY1 + 192)                 # breadbox lift (func_plat) in front of the counter
WINDOW = (-640, 640, 1152, 1696)                      # window over the sink: x0 x1 z0 z1


# ------------------------------------------------------------------------------------------------ textures
def textures():
    TD = os.path.join(OUT, 'textures', NS)

    def W(name, a, alpha=None): ML.save_img(os.path.join(TD, name), a, alpha)
    W('kfloor', kfloor()); W('liner', liner()); W('frame', ML.fill(256, (214, 218, 222), 3, 5))
    W('trim', ML.fill(128, (236, 240, 244), 2, 7)); W('shelfglass', shelfglass()); W('binglass', ML.fill(64, (170, 210, 230), 2, 9))
    W('doorliner', doorliner()); W('bin', ML.fill(128, (224, 232, 238), 3, 11)); W('cabinet', cabinet())
    W('ceiling', ML.fill(256, (120, 124, 140), 4, 13)); W('choc', choc()); W('butter', butter()); W('cracker', cracker())
    W('cheeseslab', cheeseslab()); W('frost', frost()); W('ice', ice()); W('milk_water', ML.fill(128, (246, 246, 240), 3, 15))
    W('vault', vaultwall()); W('wall', ML.fill(256, (150, 160, 188), 4, 17)); W('jelly', ML.fill(128, (210, 30, 50), 6, 19))
    W('magnetboard', magnets()); W('granite', granite()); W('steel', ML.fill(128, (170, 176, 184), 3, 91))
    W('cupwood', ML.fill(256, (150, 110, 70), 6, 92) + ML.N3(256, 18, 93, 10)); W('board', board())
    W('splash', splash()); W('dirt', dirt()); W('frostwall', frostwall()); W('sinkwater', ML.fill(128, (120, 160, 180), 4, 106))
    W('neon_snack', neon('MIDNIGHT\nSNACK', (255, 60, 150), 512, 256)); W('neon_temp', neon('-18\u00b0C', (80, 200, 255), 256, 128))
    W('neon_clock', neon('00:00', (255, 50, 40), 256, 128)); W('neon_veg', neon('ROOT\nCELLAR', (120, 255, 90), 256, 256))
    write_kit_textures(OUT, NS, pad_rgb=(255, 80, 110))
    return ['kfloor', 'liner', 'frame', 'trim', 'doorliner', 'bin', 'cabinet', 'ceiling', 'choc', 'butter', 'cracker',
            'cheeseslab', 'vault', 'wall', 'jelly', 'magnetboard', 'granite', 'steel', 'cupwood', 'board', 'splash', 'dirt',
            'frostwall']


def neon(text, rgb, w, h):
    """glowing tube lettering on a near-black board (additive neon washes out on a bright backing)"""
    return ML.text_img(text, w, h, (8, 8, 14), rgb, serif=False, glow=rgb, border=tuple(int(v * 0.6) for v in rgb))


def granite(n=256):
    c = ML.fill(n, (58, 60, 66), 10, 94) + ML.N3(n, 0.6, 95, 18)
    r = np.random.default_rng(96).random((n, n)) > 0.985
    return np.where(r[..., None], ML.C((210, 210, 220)), c)


def board(n=256):
    """end-grain chopping board: warm strips"""
    x, y = ML.xy(n)
    strip = np.floor(x * 6) % 3
    c = ML.fill(n, (186, 140, 90), 5, 97) + (strip[..., None] - 1) * 14
    return c + np.sin((y * 30 + ML.noise(n, 5, 98) * 0.4) * math.pi)[..., None] * 6


def splash(n=256):
    """white subway tiles behind the counter"""
    x, y = ML.xy(n)
    row = np.floor(y * 8)
    j = ((y * 8) % 1 < 0.06) | (((x * 4 + (row % 2) * 0.5) % 1) < 0.03)
    return np.where(j[..., None], ML.C((150, 156, 164)), ML.fill(n, (226, 232, 236), 3, 99))


def dirt(n=256):
    return ML.fill(n, (96, 70, 46), 10, 101) + ML.N3(n, 3, 102, 14)


def frostwall(n=256):
    """liner furred with frost: white crystals over the pale plastic"""
    idx, edge = ML.voronoi(n, 40, 103)
    c = ML.fill(n, (226, 238, 246), 4, 104) + ML.N3(n, 0.7, 105, 12)
    return np.where((edge < 0.008)[..., None], ML.C((255, 255, 255)), c)


def kfloor(n=256):
    """black and white kitchen tiles"""
    x, y = ML.xy(n)
    chk = ((np.floor(x * 4) + np.floor(y * 4)) % 2).astype(bool)
    c = np.where(chk[..., None], ML.C((228, 226, 220)), ML.C((40, 42, 48))) + ML.N3(n, 1.5, 21, 5)
    grout = ((x * 4) % 1 < 0.02) | ((y * 4) % 1 < 0.02)
    return np.where(grout[..., None], ML.C((120, 118, 112)), c)


def liner(n=256):
    """white fridge liner with faint moulded ribs"""
    x, y = ML.xy(n)
    rib = (np.abs(((y * 4) % 1) - 0.5) < 0.03)
    return ML.fill(n, (238, 242, 246), 2, 23) - rib[..., None] * 14


def shelfglass(n=128):
    x, y = ML.xy(n)
    edge = (x < 0.02) | (y < 0.02)
    return ML.fill(n, (150, 200, 210), 3, 25) + edge[..., None] * 60


def doorliner(n=256):
    x, y = ML.xy(n)
    return ML.fill(n, (230, 234, 238), 2, 27) - (np.abs(((x * 2) % 1) - 0.5) < 0.02)[..., None] * 18


def cabinet(n=256):
    """kitchen cabinet doors (night blue) with handles"""
    x, y = ML.xy(n)
    c = ML.fill(n, (52, 62, 92), 4, 29)
    frame = ((x % 0.5) < 0.03) | ((x % 0.5) > 0.47) | (y < 0.03) | (y > 0.97)
    c = np.where(frame[..., None], ML.C((34, 40, 60)), c)
    handle = (np.abs((x % 0.5) - 0.42) < 0.012) & (np.abs(y - 0.5) < 0.12)
    return np.where(handle[..., None], ML.C((190, 190, 196)), c)


def choc(n=256):
    """chocolate bar: square segments with bevels"""
    x, y = ML.xy(n)
    fx, fy = (x * 4) % 1, (y * 4) % 1
    b = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    sh = np.clip(b * 10, 0, 1)
    return ML.lerp(ML.C((56, 30, 18)), ML.C((104, 60, 36)), sh[..., None]) + ML.N3(n, 1, 31, 3)


def butter(n=256):
    return ML.fill(n, (250, 226, 130), 4, 33) + ML.N3(n, 16, 34, 6)


def cracker(n=256):
    x, y = ML.xy(n)
    holes = (((x * 6) % 1 - 0.5) ** 2 + ((y * 6) % 1 - 0.5) ** 2) < 0.012
    c = ML.fill(n, (214, 164, 96), 6, 35) + ML.N3(n, 3, 36, 8)
    return np.where(holes[..., None], ML.C((150, 100, 52)), c)


def cheeseslab(n=256):
    x, y = ML.xy(n)
    lines = (y * 8) % 1 < 0.05
    return ML.fill(n, (246, 196, 70), 4, 37) - lines[..., None] * 30


def frost(n=256):
    return ML.fill(n, (214, 230, 240), 6, 39) + ML.N3(n, 0.8, 40, 10)


def ice(n=256):
    """slick ice patch: pale blue with scratches"""
    x, y = ML.xy(n)
    c = ML.fill(n, (170, 210, 236), 5, 41)
    for k in range(9):
        a = k * 0.7
        d = np.abs((x - 0.5) * math.sin(a) - (y - 0.5) * math.cos(a) - (k - 4) * 0.08)
        c = c + (d < 0.003)[..., None] * 50
    return c


def vaultwall(n=256):
    idx, edge = ML.voronoi(n, 18, 43)
    c = ML.fill(n, (150, 196, 230), 5, 44) + (idx[..., None] % 5) * 6
    return np.where((edge < 0.012)[..., None], ML.C((220, 240, 252)), c)


def magnets(n=256):
    """the outside of a fridge door covered in magnets and a child's drawing (all original)"""
    c = ML.fill(n, (226, 230, 234), 3, 45)
    r = np.random.default_rng(46)
    x, y = ML.xy(n)
    for _ in range(9):
        cx, cy, rr = r.random(), r.random(), 0.03 + r.random() * 0.04
        col = ML.C(r.integers(40, 250, 3))
        c = np.where((((x - cx) ** 2 + (y - cy) ** 2) < rr * rr)[..., None], col, c)
    return c


# ------------------------------------------------------------------------------------------------ custom MD3s
SH_ = {}


def mtex():
    """model textures + shader registrations (all before the .shader file is written)"""
    def reg(key, name, arr, kind='lm', alpha=None, lathe=False, **o):
        # revolve() runs v up the profile while image rows run down: lathe labels come out upside down, flip them
        if lathe: arr = np.ascontiguousarray(np.asarray(arr)[::-1])
        ML.T(name, arr, alpha); SH_[key] = ML.S(name, kind, **o)
    x, y = ML.xy(256)
    holes = ML.fill(256, (250, 204, 80), 4, 51)
    rr = np.random.default_rng(52)
    for _ in range(14):
        cx, cy, r = rr.random(), rr.random(), 0.03 + rr.random() * 0.06
        d = ((x - cx) ** 2 + (y - cy) ** 2) / (r * r)
        holes = np.where((d < 1)[..., None], ML.lerp(ML.C((200, 150, 40)), ML.C((240, 190, 70)), d[..., None]), holes)
    reg('cheese', 'cheese_m', holes, shade=25)
    reg('rind', 'rind_m', ML.fill(128, (236, 176, 50), 5, 53), shade=25)
    reg('drawer', 'drawer_m', ML.fill(64, (150, 200, 220), 2, 54), 'glass', c='0.07 0.10 0.12')
    reg('drawer_rim', 'drawer_rim_m', ML.fill(64, (232, 238, 242), 2, 55), shade=30)
    carton = ML.text_img('MILK', 512, 256, (250, 250, 248), (40, 90, 200), serif=False)
    carton[200:, :] = ML.C((40, 90, 200))
    reg('carton', 'carton_m', carton, shade=20)
    reg('carton_in', 'carton_in_m', ML.fill(128, (200, 196, 186), 4, 56), shade=20)
    reg('butterbox', 'butterbox_m', ML.text_img('BUTTER', 256, 128, (250, 220, 90), (140, 90, 20), serif=False), shade=20)
    reg('eggbox', 'eggbox_m', ML.fill(128, (170, 150, 120), 7, 57), shade=40)
    reg('egg', 'egg_m', ML.fill(128, (244, 232, 214), 3, 58))
    reg('jelly', 'jelly_m', ML.fill(128, (200, 24, 44), 5, 59), deform='wave 64 sin 0 2.5 0 0.7')
    reg('jellyplate', 'jellyplate_m', ML.fill(64, (240, 240, 244), 2, 60))
    reg('yogurt', 'yogurt_m', ML.text_img('YO!', 256, 128, (250, 246, 236), (230, 110, 150), serif=False), lathe=True)
    reg('foil', 'foil_m', ML.fill(64, (200, 200, 210), 6, 61), 'lms', v=0.35)
    reg('apple', 'apple_m', ML.fill(256, (196, 26, 30), 6, 62) + ML.N3(256, 20, 63, 18))
    reg('stem', 'stem_m', ML.fill(64, (90, 60, 30), 4, 64))
    reg('leaf', 'leaf_m', ML.fill(128, (70, 150, 50), 6, 65), two=True)
    reg('lettuce', 'lettuce_m', ML.fill(256, (120, 190, 70), 10, 66) + ML.N3(256, 4, 67, 20), shade=60)
    reg('carrot', 'carrot_m', ML.fill(128, (236, 120, 30), 6, 68))
    reg('tomato', 'tomato_m', ML.fill(128, (220, 40, 30), 4, 69))
    reg('icecube', 'icecube_m', ML.fill(64, (180, 220, 240), 3, 70), 'glass', c='0.14 0.18 0.22')
    reg('tub', 'tub_m', ML.text_img('VANILLA\nDREAM', 512, 256, (250, 236, 210), (120, 70, 40)), lathe=True)
    reg('scoop', 'scoop_m', ML.fill(128, (252, 240, 214), 5, 71), shade=60)
    reg('peas', 'peas_m', ML.text_img('PEAS', 256, 256, (40, 140, 60), (250, 250, 250), serif=False))
    reg('ketchup', 'ketchup_m', ML.fill(128, (200, 20, 20), 3, 72), 'lms', v=0.12)
    reg('mustard', 'mustard_m', ML.fill(128, (240, 200, 30), 3, 73), 'lms', v=0.12)
    reg('cap', 'cap_m', ML.fill(64, (250, 250, 250), 2, 74))
    reg('juice', 'juice_m', ML.text_img('OJ', 256, 256, (250, 160, 30), (255, 255, 255), serif=False))
    reg('jar', 'jar_m', ML.fill(64, (160, 210, 180), 2, 75), 'glass', c='0.08 0.12 0.10')
    reg('pickle', 'pickle_m', ML.fill(128, (90, 130, 40), 6, 76))
    reg('lid', 'lid_m', ML.fill(64, (210, 40, 40), 3, 77), 'lms', v=0.2)
    cb = ML.text_img('PAD\nFLAKES', 512, 1024, (230, 60, 40), (255, 230, 80), serif=False)
    reg('cereal', 'cereal_m', cb, shade=10)
    reg('cereal_top', 'cereal_top_m', ML.fill(64, (200, 50, 30), 3, 79), shade=10)
    cl = ML.fill(256, (60, 24, 14), 4, 80, m=512)
    lab = ML.text_img('PAD COLA', 256, 128, (200, 20, 30), (255, 255, 255), serif=False)
    cl[200:328] = lab
    reg('cola', 'cola_m', cl, 'lms', v=0.25, lathe=True)
    reg('colacap', 'colacap_m', ML.fill(64, (200, 20, 30), 3, 81))
    reg('celery', 'celery_m', ML.fill(128, (150, 200, 90), 6, 82) - (np.abs(((ML.xy(128)[0] * 8) % 1) - 0.5) < 0.06)[..., None] * 25)
    reg('chrome', 'chrome_m', ML.fill(64, (190, 194, 200), 2, 110), 'lms', v=0.45)
    reg('toaster', 'toaster_m', ML.fill(128, (200, 60, 50), 3, 111), 'lms', v=0.2, shade=30)
    reg('slot', 'slot_m', ML.fill(64, (30, 30, 34), 2, 112))
    reg('bowl', 'bowl_m', ML.fill(128, (40, 120, 170), 4, 113))
    reg('banana', 'banana_m', ML.fill(128, (246, 214, 60), 5, 114))
    reg('orange', 'orange_m', ML.fill(128, (246, 140, 30), 7, 115) + ML.N3(128, 0.6, 116, 10))
    reg('cookies', 'cookies_m', ML.fill(128, (180, 120, 60), 8, 117) + ML.N3(128, 2, 118, 20))
    reg('cjar', 'cjar_m', ML.fill(64, (170, 200, 210), 2, 119), 'glass', c='0.09 0.11 0.12')
    reg('potato', 'potato_m', ML.fill(128, (170, 130, 80), 8, 120) + ML.N3(128, 3, 121, 16), shade=60)
    reg('onion', 'onion_m', ML.fill(128, (190, 120, 60), 6, 122) - (np.abs(((ML.xy(128)[0] * 10) % 1) - 0.5) < 0.05)[..., None] * 30)
    reg('sack', 'sack_m', ML.fill(128, (160, 130, 90), 9, 123) + ML.N3(128, 1, 124, 18), shade=60)
    reg('pizza', 'pizza_m', pizza_tex())
    reg('crust', 'crust_m', ML.fill(64, (200, 140, 70), 6, 125))
    reg('bread', 'bread_m', ML.fill(128, (236, 206, 150), 6, 126), shade=30)
    reg('lettuceleaf', 'lettuceleaf_m', ML.fill(64, (110, 190, 70), 8, 127))
    reg('ham', 'ham_m', ML.fill(64, (230, 140, 150), 5, 128))
    reg('pancake', 'pancake_m', ML.fill(128, (214, 160, 80), 6, 129) + ML.N3(128, 4, 130, 14), shade=60)
    reg('syrup', 'syrup_m', ML.fill(64, (140, 70, 20), 3, 131), 'lms', v=0.3)
    x, y = ML.xy(256)
    reg('roll', 'roll_m', ML.fill(256, (244, 244, 240), 3, 135) - (((y * 12) % 1) < 0.03)[..., None] * 30
        + (np.abs(((x * 8) % 1) - 0.5) < 0.04)[..., None] * -10, shade=80)
    reg('rollcore', 'rollcore_m', ML.fill(64, (170, 130, 90), 4, 136))
    reg('pizzabox', 'pizzabox_m', ML.text_img('PAD\nPIZZA', 256, 256, (214, 180, 130), (180, 40, 30), serif=False), shade=10)
    reg('crock', 'crock_m', ML.fill(128, (60, 90, 140), 5, 137) + ML.N3(128, 8, 138, 12))
    reg('spoonwood', 'spoonwood_m', ML.fill(64, (190, 140, 80), 5, 139))
    reg('mill', 'mill_m', ML.fill(256, (90, 50, 30), 5, 140) + np.sin((ML.xy(256)[1] * 40) * math.pi)[..., None] * 8, shade=70)
    reg('bulb', 'bulb_m', ML.fill(64, (255, 250, 236), 1, 78), 'glow')


def pizza_tex(n=256):
    """cheese + tomato with pepperoni rounds"""
    x, y = ML.xy(n)
    c = ML.fill(n, (240, 196, 90), 6, 132) + ML.N3(n, 2, 133, 14)
    rr = np.random.default_rng(134)
    for _ in range(7):
        cx, cy, r = rr.random(), rr.random(), 0.08
        c = np.where((((x - cx) ** 2 + (y - cy) ** 2) < r * r)[..., None], ML.C((180, 40, 30)), c)
    return c


def solids_tex(key, side_key=None, tile=256.0):
    """texfn for K.solid_piece: shader `key` everywhere (or side_key on vertical faces), planar UVs"""
    def f(c, n, poly):
        k = side_key if (side_key and abs(n[2]) < 0.7) else key
        return SH_[k], ML.planar_uv(n, tile)
    return f


def models():
    mtex()
    # jelly on a plate: a wobbling dome (deformVertexes wave on a lightmapped shader)
    X = ML.Model()
    revolve(X.mesh(SH_['jelly']), [(160, 12), (150, 60), (130, 110), (90, 150), (40, 168), (0, 172)], u_tiles=3, n=40)
    revolve(X.mesh(SH_['jellyplate']), [(200, 0), (200, 6), (196, 12), (0, 12)], n=40, inward=True)
    ML.save('jelly', X)
    # yogurt pot with a foil lid
    X = ML.Model()
    revolve(X.mesh(SH_['yogurt']), [(64, 0), (80, 150), (84, 154)], u_tiles=1, n=32)
    revolve(X.mesh(SH_['foil']), [(86, 154), (0, 156)], n=32, inward=True)
    ML.save('yogurt', X)
    # apple
    X = ML.Model()
    revolve(X.mesh(SH_['apple']), [(0.1, 0), (70, 6), (140, 60), (160, 150), (140, 250), (90, 300), (40, 292), (0.1, 280)],
            u_tiles=3, n=40)
    tube(X.mesh(SH_['stem']), [(0, 0, 276), (6, 4, 320), (16, 8, 350)], [7, 6, 5], nseg=8)
    ellipsoid(X.mesh(SH_['leaf']), (40, 10, 336), 34, 12, 4)
    ML.save('apple', X)
    # lettuce head (lumpy ellipsoid), carrot, tomato
    X = ML.Model()
    ellipsoid(X.mesh(SH_['lettuce']), (0, 0, 120), 170, 160, 120, nu=24, nv=14, flat_bottom=-112,
              bump=lambda u, v: 1 + 0.07 * math.sin(u * 17) * math.sin(v * 11))
    ML.save('lettuce', X)
    X = ML.Model()
    tube(X.mesh(SH_['carrot']), [(-200, 0, 34), (0, 0, 32), (180, 0, 20), (240, 0, 8)], [34, 32, 18, 3], nseg=14)
    for k in range(3):
        a = k * 2.1
        tube(X.mesh(SH_['leaf']), [(-200, 0, 34), (-260, 20 * math.cos(a), 60 + 10 * k), (-300, 40 * math.cos(a), 90)], [8, 6, 2], nseg=6)
    ML.save('carrot', X)
    X = ML.Model()
    sphere(X.mesh(SH_['tomato']), (0, 0, 70), 72, nu=20, nv=12)
    for k in range(5):
        a = k * 2 * math.pi / 5
        tube(X.mesh(SH_['leaf']), [(0, 0, 140), (30 * math.cos(a), 30 * math.sin(a), 144)], [5, 2], nseg=5)
    ML.save('tomato', X)
    # egg (one) - eggs stand in the egg box cups
    X = ML.Model()
    revolve(X.mesh(SH_['egg']), [(0.1, 0), (38, 10), (50, 50), (44, 100), (24, 132), (0.1, 140)], n=24)
    ML.save('egg', X)
    # ice cube (translucent), ice cream tub, peas bag
    X = ML.Model(); rbox(X.mesh(SH_['icecube']), (-80, -80, 0), (80, 80, 150), r=16, k=3, tile=160); ML.save('icecube', X)
    X = ML.Model()
    revolve(X.mesh(SH_['tub']), [(170, 0), (200, 220)], u_tiles=1, n=40)
    ellipsoid(X.mesh(SH_['scoop']), (0, 0, 220), 190, 190, 60, nu=28, nv=8, flat_bottom=0,
              bump=lambda u, v: 1 + 0.05 * math.sin(u * 9 + v * 5))
    ML.save('tub', X)
    X = ML.Model(); rbox(X.mesh(SH_['peas']), (-200, -140, 0), (200, 140, 70), r=30, k=4, tile=400); ML.save('peas', X)
    # door-bin bottles: ketchup, mustard, juice carton
    for key, h in (('ketchup', 300), ('mustard', 270)):
        X = ML.Model()
        revolve(X.mesh(SH_[key]), [(54, 0), (60, 20), (60, h * 0.65), (34, h * 0.85), (20, h * 0.88)], u_tiles=1, n=28)
        revolve(X.mesh(SH_['cap']), [(22, h * 0.88), (22, h), (0, h)], n=20, inward=False)
        ML.save(key, X)
    X = ML.Model()
    rbox(X.mesh(SH_['juice']), (-64, -64, 0), (64, 64, 300), r=4, k=1, tile=128)
    mprism(X.mesh(SH_['cap']), [(-64, -64), (64, -64), (64, 64), (-64, 64)], 300, 304)
    ML.save('juice', X)
    # pickle jar: glass with pickles inside and a red lid
    X = ML.Model()
    revolve(X.mesh(SH_['jar']), [(150, 0), (160, 20), (160, 260), (130, 300)], u_tiles=1, n=36)
    for k in range(7):
        a = k * 2 * math.pi / 7
        tube(X.mesh(SH_['pickle']), [(80 * math.cos(a), 80 * math.sin(a), 20), (70 * math.cos(a), 70 * math.sin(a), 240)],
             [34, 30], nseg=10)
    revolve(X.mesh(SH_['lid']), [(134, 300), (134, 330), (0, 330)], n=36, inward=True)
    ML.save('jar', X)
    # a giant 2-litre cola bottle standing in the kitchen (sightline cover across the open middle)
    X = ML.Model()
    revolve(X.mesh(SH_['cola']), [(150, 0), (170, 40), (172, 300), (164, 360), (172, 420), (172, 820), (150, 940),
                                  (90, 1080), (62, 1160)], u_tiles=2, n=36, vlen=1300)
    revolve(X.mesh(SH_['colacap']), [(66, 1160), (66, 1230), (0, 1230)], n=24, inward=True)
    ML.save('cola', X)
    # a bunch of celery standing up in the pulled-out drawer (tall cover over the east side of the kitchen)
    X = ML.Model()
    rr = np.random.default_rng(83)
    for k in range(7):
        a = k * 2 * math.pi / 7
        bx, by = 70 * math.cos(a), 70 * math.sin(a)
        tx, ty = bx * 2.2 + rr.uniform(-30, 30), by * 2.2 + rr.uniform(-30, 30)
        h = 1000 + rr.uniform(0, 150)
        tube(X.mesh(SH_['celery']), [(bx, by, 0), (bx * 1.4, by * 1.4, h * 0.5), (tx, ty, h)], [40, 36, 30], nseg=10)
        for j in range(4):
            b2 = a + j * 1.6
            tube(X.mesh(SH_['leaf']), [(tx, ty, h), (tx + 80 * math.cos(b2), ty + 80 * math.sin(b2), h + 70)], [16, 4], nseg=6)
    ML.save('celery', X)
    # ---- counter pieces
    X = ML.Model()                                                    # kettle (chrome) with a handle
    revolve(X.mesh(SH_['chrome']), [(150, 0), (170, 30), (170, 220), (120, 300), (60, 330)], u_tiles=1, n=36)
    revolve(X.mesh(SH_['slot']), [(62, 330), (62, 350), (0, 350)], n=24, inward=True)
    tube(X.mesh(SH_['slot']), [(-160, 0, 80), (-240, 0, 140), (-240, 0, 260), (-150, 0, 290)], [16, 16, 16, 16], nseg=8)
    tube(X.mesh(SH_['chrome']), [(150, 0, 120), (230, 0, 220), (260, 0, 250)], [34, 22, 16], nseg=10)
    ML.save('kettle', X)
    X = ML.Model()                                                    # toaster with two slots and a lever
    rbox(X.mesh(SH_['toaster']), (-220, -120, 0), (220, 120, 240), r=40, k=4, tile=256)
    for sx in (-80, 80):
        rbox(X.mesh(SH_['slot']), (sx - 30, -90, 236), (sx + 30, 90, 244), r=4, k=1, tile=64)
    rbox(X.mesh(SH_['slot']), (220, -20, 150), (250, 20, 180), r=6, k=1, tile=64)
    ML.save('toaster', X)
    X = ML.Model()                                                    # fruit bowl with oranges and bananas
    revolve(X.mesh(SH_['bowl']), [(110, 0), (230, 90), (250, 110), (236, 112), (0, 30)], u_tiles=2, n=36)
    for k in range(5):
        a = k * 2 * math.pi / 5
        sphere(X.mesh(SH_['orange']), (110 * math.cos(a), 110 * math.sin(a), 130), 62, nu=16, nv=10)
    for k in range(3):
        tube(X.mesh(SH_['banana']), [(-120, -40 + k * 40, 150), (0, -60 + k * 40, 220), (120, -40 + k * 40, 160)],
             [18, 30, 16], nseg=10)
    ML.save('fruitbowl', X)
    X = ML.Model()                                                    # cookie jar (glass) full of cookies
    revolve(X.mesh(SH_['cjar']), [(140, 0), (150, 20), (150, 300), (110, 330)], u_tiles=1, n=36)
    for k in range(9):
        a = k * 2.4
        rr_ = 30 + (k % 3) * 35
        zc = 22 + k * 28
        revolve(X.mesh(SH_['cookies']), [(48, zc), (48, zc + 14), (0, zc + 16)], n=16, inward=True,
                cx=rr_ * math.cos(a), cy=rr_ * math.sin(a))
    revolve(X.mesh(SH_['chrome']), [(112, 330), (112, 360), (0, 370)], n=36, inward=True)
    ML.save('cookiejar', X)
    X = ML.Model()                                                    # sink tap: rises from the worktop and arcs over
    tube(X.mesh(SH_['chrome']), [(0, 0, 0), (0, 0, 280), (0, 40, 360), (0, 140, 360), (0, 200, 300)], [30, 26, 24, 22, 20], nseg=12)
    rbox(X.mesh(SH_['chrome']), (-50, -50, 0), (50, 50, 40), r=10, k=2, tile=64)
    ML.save('tap', X)
    # ---- root cellar
    X = ML.Model()                                                    # potato pile
    rr = np.random.default_rng(141)
    for k in range(14):
        a, d = rr.uniform(0, 6.3), rr.uniform(0, 130)
        z = 34 + (130 - d) * 0.6
        ellipsoid(X.mesh(SH_['potato']), (d * math.cos(a), d * math.sin(a), z), 52, 38, 32, nu=12, nv=8,
                  R=np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]))
    ML.save('potatoes', X)
    X = ML.Model()                                                    # burlap sack of onions
    revolve(X.mesh(SH_['sack']), [(120, 0), (150, 60), (150, 200), (110, 280), (60, 300)], u_tiles=2, n=24)
    for k in range(5):
        a = k * 1.3
        sphere(X.mesh(SH_['onion']), (40 * math.cos(a), 40 * math.sin(a), 320), 40, nu=12, nv=8)
    ML.save('sack', X)
    # ---- extra food for the shelves
    X = ML.Model()                                                    # pizza slice (wedge with a crust rim)
    pts = [(0, 0), (380, -110), (380, 110)]
    mprism(X.mesh(SH_['pizza']), pts, 0, 24)
    tube(X.mesh(SH_['crust']), [(380, -116, 22), (392, 0, 26), (380, 116, 22)], [18, 20, 18], nseg=10)
    ML.save('pizza', X)
    X = ML.Model()                                                    # club sandwich
    for k, (key, h) in enumerate((('bread', 40), ('lettuceleaf', 10), ('ham', 22), ('bread', 40), ('ham', 22), ('bread', 40))):
        z0 = sum(hh for _, hh in (('bread', 40), ('lettuceleaf', 10), ('ham', 22), ('bread', 40), ('ham', 22), ('bread', 40))[:k])
        grow = 10 if key in ('lettuceleaf', 'ham') else 0
        rbox(X.mesh(SH_[key]), (-150 - grow, -150 - grow, z0), (150 + grow, 150 + grow, z0 + h), r=8 if key == 'bread' else 3, k=2, tile=300)
    tube(X.mesh(SH_['stem']), [(0, 0, 150), (0, 0, 230)], [5, 5], nseg=6)
    ML.save('sandwich', X)
    X = ML.Model()                                                    # pancake stack with syrup
    for k in range(6):
        revolve(X.mesh(SH_['pancake']), [(150 - (k % 2) * 6, k * 30), (156, k * 30 + 14), (150, k * 30 + 28), (0, k * 30 + 30)],
                n=32, inward=True)
    revolve(X.mesh(SH_['syrup']), [(120, 180), (100, 190), (0, 194)], n=32, inward=True)
    ML.save('pancakes', X)
    X = ML.Model()                                                    # utensil crock with spoons and a whisk
    revolve(X.mesh(SH_['crock']), [(110, 0), (130, 30), (130, 300), (120, 320)], u_tiles=2, n=32)
    for k in range(5):
        a = k * 1.25
        bx, by = 50 * math.cos(a), 50 * math.sin(a)
        tube(X.mesh(SH_['spoonwood']), [(bx, by, 40), (bx * 2.2, by * 2.2, 560 + k * 40)], [12, 10], nseg=6)
        ellipsoid(X.mesh(SH_['spoonwood']), (bx * 2.3, by * 2.3, 620 + k * 40), 40, 26, 60, nu=10, nv=6)
    ML.save('crock', X)
    X = ML.Model()                                                    # pepper mill
    revolve(X.mesh(SH_['mill']), [(120, 0), (125, 60), (90, 300), (80, 520), (110, 760), (120, 880), (70, 980), (40, 1040)],
            u_tiles=2, n=32, vlen=1040)
    revolve(X.mesh(SH_['chrome']), [(42, 1040), (42, 1080), (0, 1090)], n=20, inward=True)
    ML.save('peppermill', X)
    X = ML.Model()                                                    # kitchen roll standing on end
    revolve(X.mesh(SH_['roll']), [(150, 0), (150, 1180)], u_tiles=3, n=40, vlen=1180)
    revolve(X.mesh(SH_['rollcore']), [(150, 1180), (50, 1180), (50, 1170)], n=40, inward=True)
    ML.save('kitchenroll', X)
    # fridge light bulb housing (glow) - hangs under the fridge ceiling at the back
    X = ML.Model(); ellipsoid(X.mesh(SH_['bulb']), (0, 0, 0), 120, 60, 40, nu=20, nv=8); ML.save('bulb', X)


# ------------------------------------------------------------------------------------------------ brushes
def shell():
    """structural hull (one sealed box) - everything else is detail. No sky: a sealed kitchen at night."""
    fl = {'top': T('kfloor'), 'side': CAULK, 'bot': CAULK}
    for r in sub_rects((X0 - 32, Y0 - 32, X1 + 32, IY0), [LIFT]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), fl, detail=False))
    K.add(box((LIFT[0], LIFT[1], -48), (LIFT[2], LIFT[3], -16), {'top': T('steel'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, IY0, -32), (X1 + 32, Y1 + 32, 0), {'top': T('liner'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZTOP), (X1 + 32, Y1 + 32, ZTOP + 32), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    wall = lambda inner, tx: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: tx})
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZTOP), wall('e', T('wall')), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZTOP), wall('w', T('wall')), detail=False))
    # south wall: tiled backsplash with a window over the sink onto the night sky (sealed sky box behind it)
    K.sky_window((X0, Y0 - 32, 0), (X1, Y0, ZTOP), WINDOW, T('splash'), T('sky'), jamb_tex=T('frame'),
                 glass_tex=T('glass'), face='n')
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZTOP), wall('s', T('wall')), detail=False))


def fridge():
    """carcass (side walls, back, roof), liner floor, glass shelves with plastic front trim"""
    lin = {'side': T('liner'), 'top': T('liner'), 'bot': T('liner'), 's': T('frame')}
    K.add(box((X0, IY0, 0), (IX0, Y1, ZTOP), dict(lin, w=CAULK, n=CAULK)))           # west side wall (front face = frame)
    K.add(box((IX1, IY0, 0), (X1, Y1, ZTOP), dict(lin, e=CAULK, n=CAULK)))
    K.add(box((IX0, IY1, 0), (IX1, Y1, ZTOP), dict(lin, n=CAULK)))                   # back wall
    K.add(box((IX0, IY0, IZ1), (IX1, IY1, ZTOP), dict(lin, top=CAULK)))              # roof
    K.reserve(((IX0, IY1 - 8, 0), (IX1, IY1, IZ1)))
    for i, z in enumerate(SHELF_Z):
        top = T('frost') if i == 2 else T('shelfglass')
        if i == 2:
            # freezer tray: frosted metal with a slick ice patch in the middle (sub_rects keeps the top flush)
            ICE = (-560, -440, 400, 360)
            for r in sub_rects((IX0, IY0 + 32, IX1, SHELF_Y1), [ICE]):
                K.add(box((r[0], r[1], z - 16), (r[2], r[3], z), {'top': top, 'side': T('trim'), 'bot': T('trim')}))
            K.add(box((ICE[0], ICE[1], z - 16), (ICE[2], ICE[3], z), {'top': T('ice'), 'side': T('trim'), 'bot': T('trim')}))
        else:
            K.add(box((IX0, IY0 + 32, z - 16), (IX1, SHELF_Y1, z), T('shelfglass')))
        K.add(box((IX0, IY0, z - 40), (IX1, IY0 + 32, z), T('trim')))                 # front trim band
        K.reserve(((IX0, IY0, z - 40), (IX1, SHELF_Y1, z)))
    # the light: glowing housing under the roof at the back, lots of cool light on every level
    K.custom(ML.PLACE['bulb'], 0, IY1 - 200, IZ1 - 40, lit=False, occupy=False)


def lane():
    """the airflow gap behind the shelves: ramp (chocolate bar) -> butter block -> ramp (cracker) -> cheese stack.
    Plain ramps (bspc), landings flush with the shelves, a lift pad from the cheese stack into the freezer."""
    ly0, ly1 = LANE
    ry = ly0 + 64                     # ramps keep 64u off the shelf edges: no head-bump strip under the slab above
    K.ramp(RAMP1[0], ry, RAMP1[1], ly1, 0, SHELF_Z[0], 'e', {'top': T('choc'), 'side': T('choc'), 'bot': CAULK}, route='ramp_choc')
    K.add(box((LAND1[0], ly0, 0), (LAND1[1], ly1, SHELF_Z[0]), {'top': T('butter'), 'side': T('butter'), 'bot': CAULK}))
    K.ramp(RAMP2[0], ry, RAMP2[1], ly1, SHELF_Z[0], SHELF_Z[1], 'e', {'top': T('cracker'), 'side': T('cracker'), 'bot': T('cracker')},
           route='ramp_cracker')
    K.add(box((LAND2[0], ly0, 0), (LAND2[1], ly1, SHELF_Z[1]), {'top': T('cheeseslab'), 'side': T('cheeseslab'), 'bot': CAULK}))
    K.reserve(((RAMP1[0], ly0, 0), (LAND2[1], ly1, SHELF_Z[1])))
    K.keep_clear(RAMP1[0] - 128, ly0 - 32, RAMP1[0], ly1, 0)
    # lift: pad on the cheese stack up through the gap onto the freezer tray
    cx = (LAND2[0] + LAND2[1]) / 2
    K.jumppad(cx, (ly0 + ly1) / 2 + 24, SHELF_Z[1], land=(cx, SHELF_Y1 - 200, SHELF_Z[2]), apex=SHELF_Z[2] + 260,
              name='pad_lift', ceiling=IZ1, edges=[(cx, SHELF_Y1, SHELF_Z[2])])
    # bots stay on the shelves: botclip along the back edges where the lane below is a drop
    K.botclip_rect(IX0, IY0, IX1, SHELF_Y1, SHELF_Z[0], sides='n', gaps=[('n', LAND1[0], LAND1[1])])
    K.botclip_rect(IX0, IY0, IX1, SHELF_Y1, SHELF_Z[1], sides='n', gaps=[('n', LAND2[0], LAND2[1])])
    # bspc traces walk-offs only 1000u down: the freezer's 1344u front drop gives bots no exit, so they leave over
    # the back edge onto the cracker ramp (~650u down)
    K.botclip_rect(IX0, IY0, IX1, SHELF_Y1, SHELF_Z[2], sides='n', gaps=[('n', 0, 640)])
    # front edges: open where the door bins join shelves 1 and 2
    for i, z in enumerate(SHELF_Z):
        gaps = [('s', IX0, -BIN_X), ('s', BIN_X, IX1)] if i < 2 else [('s', -320, 320)]   # freezer: walk off the middle
        K.botclip_rect(IX0, IY0, IX1, SHELF_Y1, z, sides='s', gaps=gaps)


def doors():
    """two open French doors along the kitchen sides, three bins on each inner face"""
    for s in (-1, 1):
        xo, xi = s * X1, s * DOOR_IN
        K.add(box((min(xo, xi), DOOR_Y0, 0), (max(xo, xi), IY0, 1856),
                  {'side': T('doorliner'), 'top': T('frame'), 'bot': CAULK, ('w' if s > 0 else 'e'): T('doorliner'),
                   's': T('frame')}))
        K.add(box((min(xo, xi), DOOR_Y0, 1856), (max(xo, xi), IY0, ZTOP), {'side': T('frame'), 'bot': T('frame'), 'top': CAULK}))
        bx0, bx1 = sorted((s * BIN_X, xi))
        for i, z in enumerate(SHELF_Z):
            ye = IY0 if i < 2 else IY0 - 128
            K.add(box((bx0, BIN_Y0, z - 32), (bx1, ye, z), {'top': T('bin'), 'side': T('bin'), 'bot': T('bin')}))
            lip_x = (bx0, bx0 + 16) if s > 0 else (bx1 - 16, bx1)
            gl = {'side': T('binglass'), 'top': T('trim'), 'bot': T('trim')}
            K.add(box((lip_x[0], BIN_Y0, z), (lip_x[1], ye, z + 32), gl))
            ex0, ex1 = (lip_x[1], bx1) if s > 0 else (bx0, lip_x[0])         # end lips stop at the long lip
            if i != 1: K.add(box((ex0, BIN_Y0, z), (ex1, BIN_Y0 + 16, z + 32), gl))     # bin 2's south end meets the bridge
            if i == 2: K.add(box((ex0, ye - 16, z), (ex1, ye, z + 32), gl))
            K.reserve(((bx0, BIN_Y0, z - 32), (bx1, ye, z)), ((lip_x[0], BIN_Y0, z), (lip_x[1], ye, z + 32)),
                      ((bx0, BIN_Y0, z), (bx1, BIN_Y0 + 16, z + 32)))
            if i < 2: K.route(f'bin{i}_{"e" if s > 0 else "w"}', (s * 1470, IY0 - 200, z), (s * 1440, IY0 + 160, z))
        K.keep_clear(bx0, IY0 - 96, bx1, IY0 + 96, SHELF_Z[0])
        K.keep_clear(bx0, IY0 - 96, bx1, IY0 + 96, SHELF_Z[1])


def drawers():
    """two clear crisper drawers: walk in through the handle cut-out; the east one is pulled out into the kitchen"""
    for name, (x0, y0, x1, y1, h) in (('drawer_w', DRAWER_W), ('drawer_e', DRAWER_E)):
        cx = (x0 + x1) / 2; gap = (cx - 128, cx + 128)
        t = 16
        B = [box((x0, y0, 0), (x1, y1, 16), 'x'),                                         # bottom (16u step in)
             box((x0, y0, 16), (x0 + t, y1, h), 'x'), box((x1 - t, y0, 16), (x1, y1, h), 'x'),
             box((x0 + t, y1 - t, 16), (x1 - t, y1, h), 'x'),
             box((x0 + t, y0, 16), (gap[0], y0 + t, h), 'x'), box((gap[1], y0, 16), (x1 - t, y0 + t, h), 'x')]
        K.solid_piece(name, B, lambda c, n, poly: (SH_['drawer_rim'] if (n[2] > 0.7 and c[2] > 20) else SH_['drawer'],
                                                   ML.planar_uv(n, 256)))
        K.keep_clear(gap[0] - 32, y0 - 112, gap[1] + 32, y0 + 112, 0)
        K.route(name, (cx, y0 - 120, 0), (cx, y0 + 200, 16))
        # veg inside (cover in the drawer, never in the doorway)
        if name == 'drawer_w':           # the onion sack hiding the Root Cellar corner
            K.prop(ML.PLACE['sack'], x0 + 362, y1 - 150, 16, cyls=[(0, 0, 120, 0, 300)], search=30)
        K.prop(ML.PLACE['lettuce'], cx - (x1 - x0) * 0.25, (y0 + y1) / 2 + 200, 16, cyls=[(0, 0, 150, 0, 230)])
        K.prop(ML.PLACE['carrot'], cx + (x1 - x0) * 0.22, y1 - 220, 16, boxes=[((-200, -34, 0), (240, 34, 66))], angle=10)
        K.prop(ML.PLACE['carrot'], cx + (x1 - x0) * 0.25, (y0 + y1) / 2 - 120, 16, boxes=[((-200, -34, 0), (240, 34, 66))], angle=-25)
        K.prop(ML.PLACE['tomato'], x0 + 200, y1 - 200, 16, cyls=[(0, 0, 64, 0, 140)], search=300)
        K.prop(ML.PLACE['tomato'], x1 - 220, (y0 + y1) / 2 + 300, 16, cyls=[(0, 0, 64, 0, 140)], search=300)


def carton():
    """milk carton lying on its side: a tunnel (both ends open) with a pad onto its roof, and spilled milk"""
    x0, y0, x1, y1, h = CARTON
    t = 24
    B = [box((x0, y0, 0), (x1, y1, 16), 'x'), box((x0, y0, 16), (x1, y0 + t, h), 'x'), box((x0, y1 - t, 16), (x1, y1, h), 'x'),
         box((x0, y0 + t, h - t), (x1, y1 - t, h), 'x')]

    def tf(c, n, poly):
        inside = (y0 + t - 1 < c[1] < y1 - t + 1) and c[2] < h - t + 1 and c[2] > 15
        return (SH_['carton_in'] if inside else SH_['carton']), ML.planar_uv(n, 320)
    K.solid_piece('carton', B, tf)
    cy = (y0 + y1) / 2
    K.keep_clear(x0 - 112, y0 + t, x0, y1 - t, 0); K.keep_clear(x1, y0 + t, x1 + 64, y1 - t, 0)
    K.route('carton_tunnel', (x0 - 100, cy, 0), (x1 + 100, cy, 0))
    K.jumppad((x0 + x1) / 2, DOOR_Y0 + 130, 0, land=((x0 + x1) / 2, cy, h), apex=h + 200, name='pad_carton', edges=[((x0 + x1) / 2, y0, h)])
    # spilled milk: a 12u puddle standing on the tiles (walk straight out of it)
    px0, py0, px1, py1 = PUDDLE
    K.water_box((px0, py0, 0), (px1, py1, 12), T('milk_water'))
    K.speaker((px0 + px1) / 2, (py0 + py1) / 2, 48, 'ambient/water_drippling')


def cheese():
    """Swiss cheese wedge on shelf 1: the slope is walkable (34 deg), a tunnel runs through it along x"""
    x0, y0, x1, y1 = CHEESE
    z = SHELF_Z[0]
    zf, zb = z + 16, z + 320                     # top at the front / back edge
    top = lambda yy: zf + (zb - zf) * (yy - y0) / (y1 - y0)
    ta, tb, th = -176, -48, z + 88               # tunnel y range and roof underside
    B = [hull([(x, yy, zz) for x in (x0, x1) for (yy, zz) in ((y0, z), (ta, z), (y0, zf), (ta, top(ta)))], 'x'),
         hull([(x, yy, zz) for x in (x0, x1) for (yy, zz) in ((ta, th), (tb, th), (ta, top(ta)), (tb, top(tb)))], 'x'),
         hull([(x, yy, zz) for x in (x0, x1) for (yy, zz) in ((tb, z), (y1, z), (tb, top(tb)), (y1, zb))], 'x')]
    K.solid_piece('cheese', B, solids_tex('cheese', tile=320))
    K.route('cheese_tunnel', (x0 - 100, (ta + tb) / 2, z), (x1 + 100, (ta + tb) / 2, z))
    K.route('cheese_slope', ((x0 + x1) / 2, y0 - 100, z), ((x0 + x1) / 2, y1 - 64, zb))
    K.keep_clear(x0 - 112, ta, x0, tb, z); K.keep_clear(x1, ta, x1 + 112, tb, z)
    K.keep_clear(x0, y0 - 112, x1, y0, z)


def butterbox():
    """the butter compartment in the west door's top bin: walk in -> the Deep Freeze (secret)"""
    z = SHELF_Z[2]
    x0, x1 = -DOOR_IN, -DOOR_IN + 224
    y0, y1 = -1760, -1440
    B = [box((x0, y0, z), (x1, y0 + 16, z + 128), 'x'), box((x0, y1 - 16, z), (x1, y1, z + 128), 'x'),
         box((x0, y0, z + 128), (x1, y1, z + 144), 'x')]
    K.solid_piece('butterbox', B, solids_tex('butterbox', tile=160))
    K.secret((x0 + 8, y0 + 24, z), (x0 + 120, y1 - 24, z + 100), dest=(0, -160, VAULT_Z), angle=90, name='deepfreeze',
             approach='e')
    K.speaker(x0 + 100, (y0 + y1) / 2, z + 64, 'machine/freezer')


def vault():
    """the Deep Freeze: sealed ice cave below the world, powerups, a teleporter back to the kitchen"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z
    t = {'side': T('vault'), 'top': T('frost'), 'bot': T('vault')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 288), (x1 + 32, y1 + 32, z + 320), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 288), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 288), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 288), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 288), t, detail=False))
    K.item('item_padpower', -160, 120, z); K.item('item_revival', 0, 200, z); K.item('holdable_killerducks', 160, 120, z)
    K.teleporter((-48, y1 - 64, z), (48, y1, z + 96), dest=(-200, -1200, 0), angle=90, name='vault_exit')
    K.reserve(((x0 - 32, y0 - 32, z), (x1 + 32, y0, z + 288)), ((x0 - 32, y1, z), (x1 + 32, y1 + 32, z + 288)),
              ((x0 - 32, y0, z), (x0, y1, z + 288)), ((x1, y0, z), (x1 + 32, y1, z + 288)))
    for (x, y) in ((-220, -220), (220, -220), (-220, 0)):
        K.prop(ML.PLACE['icecube'], x, y, z, boxes=[((-80, -80, 0), (80, 80, 150))])
    K.light(0, 0, z + 220, 500, '0.7 0.85 1')
    K.speaker(0, 0, z + 100, 'ambient/wind_icy')


def face_centre(b, f):
    V = b.verts()
    n = np.array(f.n)
    on = V[np.abs(V @ n - f.d) < 0.05]
    return on.mean(0) if len(on) else V.mean(0)


def counter():
    """kitchen counter along the south wall (worktop at 896): a sink you can drop into (Betty on the dry half, a pad
    out), an open cupboard to walk into, a breadbox lift and a pad up from the floor, and chopping-board bridges to
    both doors' middle bins. Cupboard and basin are carved out of one block."""
    sx0, sy0, sx1, sy1, sz = SINK
    ux0, uy0, ux1, uy1, uz = CUPBOARD
    body = box((X0, CY0, 0), (X1, CY1, CZ - 32), 'x')
    cuts = [box((sx0, sy0, sz), (sx1, sy1, CZ), 'x'), box((ux0, uy0, 0), (ux1, uy1 + 32, uz), 'x')]
    # texture by the plane a face lies on: basin planes steel, cupboard planes wood, the front cabinet doors, else caulk
    steel = [((1, 0, 0), sx0), ((-1, 0, 0), -sx1), ((0, 1, 0), sy0), ((0, -1, 0), -sy1), ((0, 0, 1), sz)]
    wood = [((1, 0, 0), ux0), ((-1, 0, 0), -ux1), ((0, 1, 0), uy0), ((0, 0, -1), -uz)]
    on = lambda f, pl: any(np.allclose(f.n, n, atol=1e-4) and abs(f.d - d) < 0.5 for n, d in pl)
    for piece in wopmap.carve(body, cuts):
        for f in piece.faces:
            f.tex = (T('steel') if on(f, steel) else T('cupwood') if on(f, wood) else
                     T('cabinet') if on(f, [((0, 1, 0), CY1)]) else CAULK)
        K.add(piece)
    for r in sub_rects((X0, CY0, X1, CY1), [(sx0, sy0, sx1, sy1)]):
        K.add(box((r[0], r[1], CZ - 32), (r[2], r[3], CZ), {'top': T('granite'), 'side': T('steel'), 'bot': CAULK,
                                                            'n': T('granite')}))
    K.reserve(((X0, CY0, 0), (X1, CY1, CZ)), pad=0)
    FOOT_SAVE = len(K.FOOT)
    # the reserve above covers the cupboard and basin too: free those volumes again (props/items go inside)
    K.FOOT[FOOT_SAVE - 1:FOOT_SAVE] = [(X0, CY0, sx0, CY1, 0, CZ), (sx1, CY0, ux0, CY1, 0, CZ), (ux1, CY0, X1, CY1, 0, CZ),
                                       (sx0, CY0, sx1, sy0, 0, CZ), (sx0, sy1, sx1, CY1, 0, CZ), (sx0, sy0, sx1, sy1, 0, sz),
                                       (ux0, CY0, ux1, uy0, 0, CZ), (ux0, CY0, ux1, CY1, uz, CZ)]
    # sink: water in the back half, the dry half has a pad back up onto the worktop
    K.water_box((sx0, sy0, sz), (sx1, sy0 + 192, sz + 24), T('sinkwater'))
    K.jumppad(0, sy1 - 96, sz, land=(-700, -3130, CZ), apex=CZ + 190, name='pad_sink', edges=[(sx0, -3150, CZ)])
    K.custom(ML.PLACE['tap'], 0, CY0 + 64, CZ, angle=0, cyls=[(0, 0, 50, 0, 300)])
    K.speaker(0, sy0 + 100, sz + 60, 'ambient/water_drippling')
    # cupboard: walk in from the kitchen floor
    K.keep_clear(ux0 + 64, CY1, ux1 - 64, CY1 + 112, 0)
    K.route('cupboard', (ux0 + 180, CY1 + 120, 0), (ux0 + 180, uy0 + 220, 0))
    K.keep_clear(ux0 + 100, uy0 + 140, ux0 + 260, CY1, 0)
    # lift (func_plat drawn raised; lowered it sits flush with the floor over its 16u pit)
    K.elevator(LIFT[0], LIFT[1], LIFT[2], LIFT[3], 0, CZ, T('board'), name='lift_counter')
    K.keep_clear(LIFT[0] - 32, LIFT[1], LIFT[2] + 32, LIFT[3] + 112, 0)
    K.reserve(((LIFT[0], LIFT[1], 0), (LIFT[2], LIFT[3], CZ + 96)))
    K.jumppad(900, -2650, 0, land=(900, -3260, CZ), apex=CZ + 260, name='pad_counter', edges=[(900, CY1, CZ)])
    # chopping-board bridges from the worktop to the middle door bins
    for s in (-1, 1):
        bx0, bx1 = sorted((s * BIN_X, s * DOOR_IN))
        K.add(box((bx0, CY1, CZ - 32), (bx1, BIN_Y0, CZ), T('board')))
        K.botclip_rect(bx0, CY1, bx1, BIN_Y0, CZ, sides='ew')
        K.reserve(((bx0, CY1, CZ - 32), (bx1, BIN_Y0, CZ)))
        K.route(f'bridge_{"e" if s > 0 else "w"}', (s * 1472, CY1 - 140, CZ), (s * 1472, BIN_Y0 + 220, CZ))
        K.keep_clear(bx0, CY1 - 112, bx1, CY1, CZ)
    K.botclip_rect(X0, CY0, X1, CY1, CZ, sides='n',
                   gaps=[('n', -DOOR_IN, -BIN_X), ('n', BIN_X, DOOR_IN), ('n', LIFT[0], LIFT[2])])
    # worktop clutter (cover across the kitchen) and a stack of pancakes
    K.prop(ML.PLACE['kettle'], -1500, -3350, CZ, cyls=[(0, 0, 170, 0, 350)])
    K.prop(ML.PLACE['toaster'], 1300, -3330, CZ, boxes=[((-220, -120, 0), (220, 120, 240))], angle=0)
    K.prop(ML.PLACE['fruitbowl'], -1080, -3380, CZ, cyls=[(0, 0, 240, 0, 200)])
    K.prop(ML.PLACE['cookiejar'], 700, -3380, CZ, cyls=[(0, 0, 150, 0, 370)])
    K.prop(ML.PLACE['pancakes'], 300, -3500, CZ, cyls=[(0, 0, 156, 0, 194)], search=200)
    K.catalog('pad_cups/pad_cup05.md3', -400, -3500, CZ, scale=1.8, angle=200)

    K.prop(ML.PLACE['jar'], 1000, -3400, 0, cyls=[(0, 0, 158, 0, 330)], search=60)          # in the cupboard


def cellar():
    """second secret: squeeze behind the onion sack in the closed crisper drawer's back corner -> the Root Cellar"""
    z = DRAWER_W[4]
    ex0, ey0 = DRAWER_W[0] + 16, DRAWER_W[3] - 16 - 160
    K.secret((ex0, ey0, 16), (ex0 + 150, ey0 + 160, 120), dest=(0, -180, CELLAR_Z), angle=90, name='rootcellar', approach='e')
    K.keep_clear(ex0, ey0 - 140, ex0 + 150, ey0, 16)
    x0, y0, x1, y1 = CELLAR; zc = CELLAR_Z
    t = {'side': T('dirt'), 'top': T('dirt'), 'bot': T('cupwood')}
    K.add(box((x0 - 32, y0 - 32, zc - 32), (x1 + 32, y1 + 32, zc), t, detail=False),
          box((x0 - 32, y0 - 32, zc + 448), (x1 + 32, y1 + 32, zc + 480), t, detail=False),
          box((x0 - 32, y0 - 32, zc), (x0, y1 + 32, zc + 448), t, detail=False), box((x1, y0 - 32, zc), (x1 + 32, y1 + 32, zc + 448), t, detail=False),
          box((x0, y0 - 32, zc), (x1, y0, zc + 448), t, detail=False), box((x0, y1, zc), (x1, y1 + 32, zc + 448), t, detail=False))
    K.reserve(((x0 - 32, y0 - 32, zc), (x1 + 32, y0, zc + 448)), ((x0 - 32, y1, zc), (x1 + 32, y1 + 32, zc + 448)),
              ((x0 - 32, y0, zc), (x0, y1, zc + 448)), ((x1, y0, zc), (x1 + 32, y1, zc + 448)))
    K.add(sign_box((-180, y1 - 8, zc + 150), (180, y1, zc + 300), T('neon_veg'), 256, 256, back=CAULK, facing='s', edge=T('frame')))
    K.item('item_climber', -120, 160, zc); K.item('holdable_boomies', 0, 220, zc); K.item('holdable_bambam', 120, 160, zc)
    K.item('item_jumper', 0, 40, zc)
    K.teleporter((-48, y0, zc), (48, y0 + 64, zc + 96), dest=(0, -2720, 0), angle=270, name='cellar_exit')
    for (x, y, m, r) in ((-330, -220, 'potatoes', 150), (330, -220, 'potatoes', 150), (-360, 170, 'sack', 150), (360, 170, 'sack', 150)):
        K.prop(ML.PLACE[m], x, y, zc, cyls=[(0, 0, r, 0, 200 if m == 'potatoes' else 340)], search=60)
    K.light(0, 0, zc + 260, 450, '1 0.8 0.55')
    K.speaker(0, 0, zc + 100, 'animal/cricket_chirp1')


def signs_frost():
    """neon: MIDNIGHT SNACK over the counter, a 00:00 clock, the freezer's -18 C display; frost furring the freezer"""
    K.add(sign_box((760, Y0, 1080), (1640, Y0 + 8, 1520), T('neon_snack'), 512, 256, back=CAULK, facing='n', edge=T('frame')))
    K.add(sign_box((-1560, Y0, 1180), (-900, Y0 + 8, 1460), T('neon_clock'), 256, 128, back=CAULK, facing='n', edge=T('frame')))
    z0, z1 = SHELF_Z[2], IZ1
    fr = T('frostwall')
    K.add(box((IX0, IY0, z0), (IX0 + 4, IY1 - 4, z1 - 4), fr), box((IX1 - 4, IY0, z0), (IX1, IY1 - 4, z1 - 4), fr),
          box((IX0, IY1 - 4, z0), (IX1, IY1, z1 - 4), fr), box((IX0, IY0 + 32, z1 - 4), (IX1, IY1, z1), fr))
    K.add(sign_box((-320, IY1 - 12, 1560), (320, IY1 - 4, 1720), T('neon_temp'), 256, 128, back=CAULK, facing='s', edge=T('frame')))


def props():
    """custom pieces + catalog models on real surfaces; cover goes where sightlines --hot says"""
    s1, s2, s3 = SHELF_Z
    # kitchen floor
    K.prop(ML.PLACE['apple'], 780, -2180, 0, cyls=[(0, 0, 150, 0, 290)], angle=30)
    K.catalog('gummybears/redbear.md3', -1300, -1150, 0, angle=60, lit=True)
    K.catalog('gummybears/greenbear.md3', -1060, -1792, CARTON[4], angle=15, lit=True)
    K.catalog('gummybears/ldgreenbear.md3', 1250, -2150, 0, angle=200, lit=True)
    K.catalog('gummybears/yellowbear.md3', 200, -2250, 0, angle=110, lit=True)
    K.catalog('pad_cups/pad_cup03_side.md3', -1350, -2150, 0, scale=1.6, angle=20)
    K.catalog('pad_cutlery/pad_spoon.md3', 300, -1500, 0, scale=1.5, angle=75, clip=False)
    # shelf 1
    K.prop(ML.PLACE['jelly'], -950, -250, s1, cyls=[(0, 0, 150, 0, 170)])
    for (x, y) in ((-400, 300), (-250, 420), (1250, 380), (220, -560), (-1150, -560), (-330, -620), (-720, -640), (-250, -200), (-900, -690)):
        K.prop(ML.PLACE['yogurt'], x, y, s1, cyls=[(0, 0, 80, 0, 156)])
    K.catalog('pad_ddmix/diner/muffin_choco.md3', -1250, 450, s1, scale=2.0)
    K.catalog('pad_ddmix/diner/muffin_blueberry.md3', 150, -300, s1, scale=2.0)
    K.catalog('pad_ddmix/diner/muffin_choco.md3', -560, -60, s1, scale=2.4)
    K.catalog('pad_ddmix/diner/muffin_blueberry.md3', -150, 150, s1, scale=2.4)
    K.prop(ML.PLACE['sandwich'], 700, 520, s1, boxes=[((-160, -160, 0), (160, 160, 174))], angle=15)
    # shelf 2
    eb = (-1200, -100, -480, 380)
    B = [box((eb[0], eb[1], s2), (eb[2], eb[3], s2 + 80), 'x')]
    K.solid_piece('eggbox', B, solids_tex('eggbox', tile=200))
    for i in range(4):
        for j in range(2):
            ex, ey = eb[0] + 90 + i * 180, eb[1] + 120 + j * 240
            K.custom(ML.PLACE['egg'], ex, ey, s2 + 80, angle=i * 40 + j * 15, occupy=False)
            K.add(cyl(ex, ey, 40, s2 + 80, s2 + 210, WCLIP, 8))
    K.prop(ML.PLACE['jar'], 64, -520, s2, cyls=[(0, 0, 158, 0, 330)])
    K.prop(ML.PLACE['yogurt'], 650, 350, s2, cyls=[(0, 0, 80, 0, 156)])
    K.catalog('pad_cake/pad_cakestand.md3', 50, 100, s2, scale=2.4, lit=True)
    K.catalog('pad_ddmix/trashcan/cannedfish.md3', 704, -192, s2, scale=2.0)
    K.prop(ML.PLACE['jar'], 800, -540, s2, cyls=[(0, 0, 158, 0, 330)])
    K.prop(ML.PLACE['yogurt'], -620, -620, s2, cyls=[(0, 0, 80, 0, 156)])
    K.prop(ML.PLACE['yogurt'], -1100, -660, s2, cyls=[(0, 0, 80, 0, 156)])
    for (x, y) in ((-320, -220), (1088, -64), (704, 120)):
        K.prop(ML.PLACE['yogurt'], x, y, s2, cyls=[(0, 0, 80, 0, 156)])
    K.prop(ML.PLACE['yogurt'], 1250, 500, s2, cyls=[(0, 0, 80, 0, 156)])
    K.prop(ML.PLACE['pancakes'], -1300, 520, s2, cyls=[(0, 0, 156, 0, 194)])
    K.prop(ML.PLACE['pizza'], 850, 400, s2, boxes=[((0, -110, 0), (395, 110, 46))], angle=200, search=300)
    K.prop(ML.PLACE['sandwich'], 350, 480, s2, boxes=[((-160, -160, 0), (160, 160, 174))], angle=-20)
    # freezer
    for (x, y) in ((-1100, -300), (-900, 300), (700, -450), (1100, 200), (-200, 550), (300, 520), (160, 20), (-830, -450), (-500, -80), (-260, -640), (420, -620), (-700, -650), (450, -380)):
        K.prop(ML.PLACE['icecube'], x, y, s3, boxes=[((-80, -80, 0), (80, 80, 150))])
    K.prop(ML.PLACE['tub'], 64, -470, s3, cyls=[(0, 0, 200, 0, 280)])
    K.prop(ML.PLACE['peas'], 1150, -350, s3, boxes=[((-200, -140, 0), (200, 140, 70))], angle=-30)
    K.prop(ML.PLACE['peas'], -1150, 500, s3, boxes=[((-200, -140, 0), (200, 140, 70))], angle=20)
    # door bins: bottles
    for s in (-1, 1):
        bx = s * 1472
        for i, z in enumerate(SHELF_Z):
            kinds = (('ketchup', 60, 300), ('juice', 70, 304), ('mustard', 60, 270))
            for k, (nm, r, hh) in enumerate(kinds):
                y = -2050 + k * 420 + (i * 130) % 260
                if i == 2 and s < 0 and -1850 < y < -1350: continue          # the butter compartment
                if nm == 'juice': K.prop(ML.PLACE['juice'], bx, y, z, boxes=[((-64, -64, 0), (64, 64, 304))], angle=0, search=80)
                else: K.prop(ML.PLACE[nm], bx, y, z, cyls=[(0, 0, r, 0, hh)], search=80)


def blockers():
    """long eye-level sightlines across the open kitchen between the doors (bins and shelves see each other): a giant
    cereal box stands in the middle of the kitchen"""
    x0, y0, x1, y1, h = CEREAL
    K.solid_piece('cereal', [box((x0, y0, 0), (x1, y1, h), 'x')],
                  lambda c, n, poly: (SH_['cereal_top'] if n[2] > 0.7 else SH_['cereal'],
                                      ML.planar_uv(n, 1400 if abs(n[2]) < 0.7 else 256)))
    for (cx, cy) in ((720, -1740), (330, -1760)):
        K.custom(ML.PLACE['cola'], cx, cy, 0, angle=cx, cyls=[(0, 0, 165, 0, 940), (0, 0, 110, 940, 1230)])
    # south kitchen, between the door ends and the counter: a leaning tower of pizza boxes and a kitchen roll
    B, z, rr = [], 0, np.random.default_rng(151)
    for k in range(14):
        ox, oy = rr.uniform(-36, 36), rr.uniform(-36, 36)
        B.append(box((-560 - 224 + ox, -2620 - 224 + oy, z), (-560 + 224 + ox, -2620 + 224 + oy, z + 104), 'x'))
        z += 104
    K.solid_piece('pizzatower', B, lambda c, n, poly: (SH_['pizzabox'], ML.planar_uv(n, 448 if n[2] > 0.7 else 220)))
    K.custom(ML.PLACE['kitchenroll'], 520, -2580, 0, cyls=[(0, 0, 148, 0, 1180)])
    for (mx_, my_) in ((1150, -2480), (-1150, -2480)):
        K.custom(ML.PLACE['peppermill'], mx_, my_, 0, cyls=[(0, 0, 122, 0, 880), (0, 0, 80, 880, 1080)])
    for (cx, cy, a) in ((450, -1000, 0), (1100, -1100, 140)):
        K.custom(ML.PLACE['celery'], cx, cy, 16, angle=a, cyls=[(0, 0, 130, 0, 560), (0, 0, 190, 560, 1150)])


def items():
    s1, s2, s3 = SHELF_Z
    K.weapon('imperius', -700, 400, s3, marker='purple')                      # freezer: pad only
    K.weapon('balloony', 1472, -1300, s3, marker='orange')                     # east door top bin: pad only
    K.weapon('betty', 250, SINK[3] - 96, SINK[4], marker='black')                # bottom of the sink
    K.weapon('pumper', -1300, -550, s2, marker='green')
    K.weapon('splasher', (DRAWER_W[0] + DRAWER_W[2]) / 2, (DRAWER_W[1] + DRAWER_W[3]) / 2 - 150, 16, marker='blue')
    K.weapon('boaster', (CARTON[0] + CARTON[2]) / 2, (CARTON[1] + CARTON[3]) / 2, CARTON[4], marker='orange')
    K.weapon('bubbleg', -450, -2150, 0, marker='green')
    ammo = {'imperius': [(400, -350, s3), (-1472, -1800, s2), (1350, 900, 0)],
            'balloony': [(1472, -2050, s3), (1350, 300, s1), (-1500, -2250, 0)],
            'betty': [(-200, -550, s2), (-1472, -1000, s1), (1500, -1000, 0), (1150, -380, s2)],
            'pumper': [(1450, -3480, CZ), (-150, 550, s1), (-1350, 300, 16), ((CARTON[0] + CARTON[2]) / 2 + 200, (CARTON[1] + CARTON[3]) / 2, CARTON[4])],
            'splasher': [(-1480, -3480, CZ), (-150, -1800, 0), (800, -700, 16), (-1300, 100, s1)],
            'boaster': [((CUPBOARD[0] + CUPBOARD[2]) / 2 - 150, -3350, 0), ((CARTON[0] + CARTON[2]) / 2 - 200, (CARTON[1] + CARTON[3]) / 2, 16), (1300, -2250, 0), (-600, 500, s1)],
            'bubbleg': [(400, 300, 0), (1472, -1000, s1), (300, -350, s2)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', 1000, -2200, 0); K.ammo('nipper', -1250, -400, 16); K.ammo('nipper', 0, 500, s2)
    K.item('item_armor_padshield', (CHEESE[0] + CHEESE[2]) / 2, -112, s1)         # in the cheese tunnel
    K.item('item_armor_shard', -1472, -1300, s1); K.item('item_armor_shard', 1472, -1600, s2)
    K.item('item_speedy', 900, 150, s1); K.item('holdable_floater', 400, -2150, 0)
    K.item('item_visionless', 0, 300, s3)
    K.station(1000, -1500, 0, ang=90)
    for (x, y, z, a) in ((-900, -2200, 0, 90), (0, -2100, 0, 90), (1150, -2200, 0, 90), (-1350, -1500, 0, 0),
                         (950, -900, 16, 180), (-1300, -500, 0, 0), (300, 600, 0, 270), (1300, 600, 0, 225),
                         (-300, -300, s1, 90), (1300, -400, s1, 180), (900, -500, s2, 135), (-700, 600, s2, 270),
                         (-1000, -3150, CZ, 90), (1100, -3120, CZ, 90), (-300, -2750, 0, 90), (400, -2650, 0, 90)):
        K.spawn(x, y, z, a)


def pads():
    """kitchen floor pads: the jelly pad onto shelf 1, shelf 2 west, both top door bins"""
    s1, s2, s3 = SHELF_Z
    jelly = T('jelly')
    K.jumppad(-1100, -1520, 0, land=(-1100, -560, s1), apex=s1 + 312, name='pad_jelly', ceiling=s2 - 16,
              edges=[(-1100, IY0, s1)], top_tex=jelly, side_tex=jelly)
    K.jumppad(-900, -1420, 0, land=(-900, -480, s2), apex=s2 + 354, name='pad_shelf2', ceiling=s3 - 16, edges=[(-900, IY0, s2)])
    for s in (-1, 1):
        px, py, ly = (1000, -1900, -1650) if s > 0 else (-1150, -2250, -1300)
        K.jumppad(px, py, 0, land=(s * 1472, ly, s3), apex=s3 + 256,
                  name=f'pad_bin_{"e" if s > 0 else "w"}', ceiling=ZTOP, edges=[(s * BIN_X, ly, s3 + 32)])


def lights():
    """inside: the fridge light (cool white, bright); kitchen: dim moonlight blue with warm spill near the fridge"""
    for z in (380, 830, 1280, 1720):
        K.light_grid(IX0 + 64, IY0 + 64, IX1 - 64, IY1 - 64, z, 620, 520, '0.92 0.97 1')
    K.light_grid(X0 + 300, Y0 + 100, X1 - 300, IY0 - 100, 1500, 700, 900, '0.55 0.65 1')
    for s in (-1, 1):
        for z in (700, 1150, 1600):
            K.light(s * 1450, -1500, z, 380, '0.9 0.95 1')
    K.light(0, IY0 - 200, 300, 900, '0.9 0.97 1')
    K.light_grid(X0 + 200, CY0 + 100, X1 - 200, CY1 - 60, CZ + 420, 640, 520, '1 0.86 0.66')      # under-cabinet glow
    K.light((CUPBOARD[0] + CUPBOARD[2]) / 2, -3250, 600, 260, '1 0.85 0.6')
    for z in (s + 60 for s in (0,) + SHELF_Z):
        K.speaker(0, 600, z, 'machine/freezer')
    K.speaker(0, Y0 + 200, 1600, 'machine/clock_ticking')
    K.timer_sound(0, -1800, 900, 'animal/cricket_chirp1', 'crickets', 25, 15)


def shader():
    parts = [SH.lm(n, steps={'cracker': 'softsteps', 'butter': 'softsteps', 'cheeseslab': 'softsteps', 'board': 'woodsteps',
                             'cupwood': 'woodsteps', 'dirt': 'sandsteps'}.get(n)) for n in TEX if n != 'frostwall']
    parts += [SH.lm('frost', steps='snowsteps'), SH.slick('ice', steps='snowsteps'),
              SH.glass('shelfglass', rgb='0.10 0.14 0.15', shadow=False), SH.glass('binglass', rgb='0.10 0.13 0.15', shadow=False),
              SH.water('milk_water', rgb=(0.95, 0.95, 0.9), alpha=0.85), SH.water('sinkwater', rgb=(0.5, 0.65, 0.75), alpha=0.5),
              SH.sky('env/pf-garden512', sun=(270, 30), sun_rgb=(0.6, 0.7, 1), sun_int=80, skylight=(25, 3)),
              SH.neon('neon_snack', (1, 0.3, 0.65), 350), SH.neon('neon_clock', (1, 0.25, 0.2), 250),
              SH.neon('neon_temp', (0.35, 0.8, 1), 250), SH.neon('neon_veg', (0.5, 1, 0.4), 250),
              SH.lm('frostwall', steps='snowsteps'), SH.nodraw_ns(), SH.jumppad(), SH.glass(),
              ML.model_shaders(), SH.levelshot_anim()]
    SH.write_shader(OUT, parts)
    SH.write_arena(OUT, INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})
    probs = ML.check_registry()
    if probs: raise SystemExit('model shader problems:\n  ' + '\n  '.join(probs))


if __name__ == '__main__':
    TEX = textures()
    models()                          # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); fridge(); lane(); doors(); counter()
    cellar(); drawers(); carton(); cheese(); butterbox(); vault(); blockers(); signs_frost()
    pads(); items(); props(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
