"""Padman's Tabletop Quest (wop_padtabletop) - textures (woplib.texlib registry) and custom MD3s. All art is procedural.

Scale: Padman is a tabletop miniature. One battle-mat square (1 inch) = 128u, so the player (56u) stands a bit shorter
than the 28 mm heroes, dungeon walls are 2 inches (256u), the gaming table's wooden rail is 4.5 inches above the mat.
Every model is built in model space with z = 0 on the surface it stands on, origin at the centre of its footprint.
COLL[name] holds the weapclip collision (boxes / cylinders in model space) placed with it by the build script.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism

TX = None
M_ = {}
COLL = {}
PAD_SKINS = {}

G = 128                     # one battle-mat square
WH, WT = 256, 32            # dungeon wall height / thickness
TERR_Z, PLAT_Z, RZ = 256, 512, 576
BASE_H = 10                 # miniature base height

PAINT = {'red': (196, 52, 44), 'blue': (52, 92, 190), 'green': (70, 140, 70), 'brown': (120, 78, 44),
         'tan': (200, 160, 110), 'ogre': (128, 150, 86), 'gob': (110, 160, 70), 'steel': (176, 182, 192),
         'gold': (222, 176, 60), 'purple': (120, 64, 160), 'bone': (226, 218, 190), 'black': (30, 30, 34),
         'white': (236, 234, 228), 'orange': (230, 120, 40), 'beard': (200, 80, 30), 'grey': (120, 120, 126)}


# ================================================================================================= helpers
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


def pic(M, c, n, w, h, up=(0, 0, 1)):
    """picture quad centred at c facing n, w x h, never mirrored"""
    c, n, up = (np.asarray(v, float) for v in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    M.poly([c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh], n, [(0, 0), (1, 0), (1, 1), (0, 1)])


def Rz(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def Ry(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def Rx(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])


def polyhedron(M, verts, faces, uvs=None):
    """flat-shaded convex polyhedron (outward faces); uvs[k] = list of uv per face vertex"""
    V = np.asarray(verts, float)
    ctr = V.mean(0)
    for k, f in enumerate(faces):
        P = [V[i] for i in f]
        n = np.cross(P[1] - P[0], P[2] - P[0]); n /= np.linalg.norm(n)
        if n @ (np.mean(P, 0) - ctr) < 0: n = -n
        uv = uvs[k] if uvs else [(0.5 + 0.5 * math.cos(2 * math.pi * i / len(f)), 0.5 + 0.5 * math.sin(2 * math.pi * i / len(f))) for i in range(len(f))]
        M.poly(P, n, uv)


# ================================================================================================= textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('mat_grass', mat_tex((86, 140, 74), (60, 100, 54), seed=3), scale=0.5)                 # 256 px = 128u = one square
    a('mat_stone', flag_tex(), scale=0.5)
    a('mat_dirt', mat_tex((132, 112, 84), (96, 80, 60), seed=5, grid=False), scale=0.5)
    a('flock', flock_tex(), scale=0.5, steps='softsteps')
    a('rock', rock_tex(), scale=1.0)
    a('cave_floor', TL.stone((96, 90, 84), cells=14), scale=1.0)
    a('maple', TL.planks((214, 150, 84), n_planks=3, grain=10, vertical=False), scale=1.0, steps='woodsteps')
    a('maple_v', TL.planks((200, 136, 74), n_planks=3, grain=10, vertical=True), scale=1.0)
    a('led', TL.solid((255, 210, 90), 1, 9, 64), 'neon', rgb=(1.0, 0.78, 0.35), light=160)
    a('water', TL.solid((60, 120, 150), 10, 12, 128), 'water', rgb=(0.25, 0.5, 0.6), alpha=0.5)
    a('brick_b', brick_tex(), scale=0.5)
    a('cap_b', TL.stone((168, 168, 172), cells=10), scale=0.5)
    a('det_wall', TL.planks((96, 60, 38), n_planks=4, grain=10, vertical=True), scale=1.0)
    a('det_floor', TL.planks((150, 100, 60), n_planks=6, grain=8), scale=1.0, steps='woodsteps')
    for i, fn in enumerate((dm_note_map, dm_note_plot, dm_note_monsters)):
        a(f'dmnote{i}', fn(), 'sign', check_tile=False)
    a('sky', TL.solid((120, 90, 70), 2, 21, 64), 'raw', shader=sky_stanza(K.ns), check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 200, 80), rubber=(60, 50, 40))
    materials()
    return TX


def sky_stanza(ns):
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 1 0.88 0.7 95 140 68\n\tq3map_skylight 55 3\n\tskyparms env/{ns}/room - -\n}}\n\n')


def mat_tex(c1, c2, seed=3, grid=True, n=256):
    """flocked battle mat: mottled colour with a dark grid line at the edge (one tile = one square)"""
    rng = np.random.default_rng(seed)
    base = TL.fill(n, c1, 10, seed) * 0.6 + TL.fill(n, c2, 22, seed + 1) * 0.4
    if grid:
        x, y = TL.xy(n)
        line = (np.minimum(x, 1 - x) < 0.008) | (np.minimum(y, 1 - y) < 0.008)
        base[line] = base[line] * 0.45
    return base + ML.N3(n, 1, seed + 9, 10)


def flag_tex(n=256):
    """grey flagstone dungeon floor, one square per tile, light grid line"""
    a_ = TL.stone((150, 148, 146), cells=6, edge=(90, 88, 86), edge_w=0.02, vary=18, seed=7)
    x, y = TL.xy(n)
    line = (np.minimum(x, 1 - x) < 0.006) | (np.minimum(y, 1 - y) < 0.006)
    a_[line] = (230, 230, 226)
    return TL.grime(a_, 0.2, seed=8)


def flock_tex(n=256):
    return TL.fill(n, (92, 150, 60), 3, 31) + ML.N3(n, 1, 32, 26)


def rock_tex(n=256):
    a_ = TL.stone((110, 108, 106), cells=26, edge=(50, 50, 52), edge_w=0.02, vary=26, seed=41)
    spk = ML.noise(n, 1, 44)
    a_ = a_ + (spk[..., None] > 0.82) * 60          # white dry-brush speckles of the painted foam
    return a_


def brick_tex(n=256):
    return TL.grime(TL.bricks((138, 138, 140), (106, 106, 110), rows=8, cols=4, vary=12, seed=45), 0.15, seed=46)


def dm_note_map(w=1024, h=512):
    im, d = canvas(w, h, (236, 222, 180))
    rng = np.random.default_rng(3)
    for _ in range(14):                                                    # hand-drawn dungeon map on graph paper
        for k in range(0, w, 32): d.line((k, 0, k, h), fill=(200, 210, 230), width=1)
        break
    for k in range(0, h, 32): d.line((0, k, w, k), fill=(200, 210, 230), width=1)
    for _ in range(9):
        x, y = rng.integers(40, w - 240), rng.integers(40, h - 160)
        d.rectangle((x, y, x + rng.integers(96, 220), y + rng.integers(64, 140)), outline=(40, 40, 70), width=5)
    d.text((30, 20), 'LEVEL 1 - THE PADMAN CRYPTS', font=ML.font(40, serif=True), fill=(120, 30, 30))
    d.text((700, 440), 'X = DRAGON', font=ML.font(36, serif=False), fill=(200, 40, 40))
    return arr(im)


def dm_note_plot(w=1024, h=512):
    im, d = canvas(w, h, (246, 240, 214))
    f = ML.font(38, serif=False)
    lines = ['SESSION 12 NOTES', '- party splits up (again)', '- ogres at the campfire = ambush!',
             '- the well leads HERE (shh)', '- dragon wakes on a nat 1', '- pizza at 8']
    for k, s in enumerate(lines):
        d.text((40, 30 + k * 76), s, font=f, fill=(30, 40, 90) if k else (160, 30, 30))
    return arr(im)


def dm_note_monsters(w=1024, h=512):
    im, d = canvas(w, h, (230, 236, 222))
    f = ML.font(36, serif=False)
    rows = [('MONSTER', 'HP', 'AC'), ('Ogre', '59', '11'), ('Goblin', '7', '15'), ('Skeleton', '13', '13'),
            ('Ancient Dragon', '546', '22'), ('Padman', '???', '20')]
    for k, (a_, b, c) in enumerate(rows):
        y = 30 + k * 74
        col = (150, 30, 30) if k == 0 else (30, 30, 30)
        d.text((40, y), a_, font=f, fill=col); d.text((620, y), b, font=f, fill=col); d.text((820, y), c, font=f, fill=col)
        d.line((30, y + 60, w - 30, y + 60), fill=(150, 150, 150), width=2)
    return arr(im)


# ---- skybox: the games room around the table, painted soft (photo bokeh). rt=+x lf=-x bk=+y ft=-y up dn
def room_faces(n=512):
    """six 512 px cube faces. Horizon in the middle row. Walls: warm plaster, bookshelves, a window, a door."""
    rng = np.random.default_rng(77)
    faces = {}

    def wall(kind):
        im, d = canvas(n, n, (150, 112, 82))
        d.rectangle((0, n * 0.62, n, n), fill=(84, 54, 34))                          # floor boards (far)
        for k in range(14):
            yy = int(n * 0.62 + k * (n * 0.38) / 14)
            d.line((0, yy, n, yy), fill=(66, 42, 26), width=2)
        d.rectangle((0, n * 0.6, n, n * 0.62), fill=(60, 40, 28))                    # skirting
        if kind == 'shelf':
            x0, x1 = int(n * 0.08), int(n * 0.92)
            d.rectangle((x0, int(n * 0.08), x1, int(n * 0.6)), fill=(90, 40, 40))
            for r in range(5):
                y0 = int(n * 0.1 + r * n * 0.1)
                xx = x0 + 8
                while xx < x1 - 12:
                    wdt = int(rng.integers(6, 16)); hh = int(rng.integers(int(n * 0.06), int(n * 0.09)))
                    col = tuple(int(0.55 * c + 0.45 * b) for c, b in zip(rng.integers(40, 220, 3), (120, 70, 40)))
                    d.rectangle((xx, y0 + n * 0.095 - hh, xx + wdt, y0 + n * 0.095), fill=col)
                    xx += wdt + 1
                d.rectangle((x0, y0 + int(n * 0.095), x1, y0 + int(n * 0.1)), fill=(70, 30, 30))
            for r in range(3):                                                        # little figures on a shelf
                d.ellipse((x0 + 60 + r * 90, int(n * 0.03), x0 + 90 + r * 90, int(n * 0.08)), fill=(220, 220, 220))
        elif kind == 'window':
            d.rectangle((int(n * 0.25), int(n * 0.12), int(n * 0.75), int(n * 0.52)), fill=(60, 50, 44))
            d.rectangle((int(n * 0.27), int(n * 0.14), int(n * 0.73), int(n * 0.5)), fill=(40, 60, 100))
            for k in range(40):
                x, y = rng.integers(int(n * 0.28), int(n * 0.72)), rng.integers(int(n * 0.3), int(n * 0.49))
                d.rectangle((x, y, x + 3, y + 3), fill=(255, 220, 140))
            d.line((n / 2, n * 0.14, n / 2, n * 0.5), fill=(60, 50, 44), width=6)
            d.rectangle((int(n * 0.05), int(n * 0.35), int(n * 0.18), int(n * 0.6)), fill=(50, 70, 50))   # plant
            d.ellipse((int(n * 0.02), int(n * 0.18), int(n * 0.22), int(n * 0.4)), fill=(60, 120, 60))
        elif kind == 'door':
            d.rectangle((int(n * 0.55), int(n * 0.16), int(n * 0.8), int(n * 0.6)), fill=(110, 70, 40))
            d.ellipse((int(n * 0.76), int(n * 0.4), int(n * 0.78), int(n * 0.42)), fill=(230, 200, 100))
            d.rectangle((int(n * 0.1), int(n * 0.2), int(n * 0.4), int(n * 0.42)), fill=(30, 30, 40))      # poster
            d.polygon([(n * 0.15, n * 0.4), (n * 0.25, n * 0.24), (n * 0.35, n * 0.4)], fill=(200, 90, 40))
        elif kind == 'chairs':
            d.rectangle((int(n * 0.1), int(n * 0.15), int(n * 0.45), int(n * 0.55)), fill=(90, 40, 40))
            for r in range(4):
                d.rectangle((int(n * 0.12), int(n * 0.18 + r * n * 0.09), int(n * 0.43), int(n * 0.24 + r * n * 0.09)), fill=tuple(int(c) for c in rng.integers(60, 200, 3)))
            d.ellipse((int(n * 0.6), int(n * 0.05), int(n * 0.9), int(n * 0.2)), fill=(255, 230, 170))   # lamp glow
        # a chair back close by (dark, blurred): every face gets one
        cx = int(n * (0.3 + 0.4 * rng.random()))
        d.rectangle((cx - 70, int(n * 0.45), cx + 70, int(n * 0.85)), fill=(70, 40, 22))
        d.rectangle((cx - 60, int(n * 0.48), cx + 60, int(n * 0.56)), fill=(150, 90, 50))
        im = im.filter(ImageFilter.GaussianBlur(3.5))
        return arr(im)
    faces['bk'] = wall('shelf')          # +y (north, behind the cliffs)
    faces['rt'] = wall('window')         # +x
    faces['ft'] = wall('chairs')         # -y
    faces['lf'] = wall('door')           # -x
    up, d = canvas(n, n, (196, 170, 140))
    d.ellipse((n * 0.38, n * 0.38, n * 0.62, n * 0.62), fill=(255, 240, 200))
    faces['up'] = arr(up.filter(ImageFilter.GaussianBlur(10)))
    dn, d = canvas(n, n, (70, 46, 30))
    faces['dn'] = arr(dn)
    return faces


def write_sky(out):
    import os
    p = os.path.join(out, 'env', TX.ns)
    os.makedirs(p, exist_ok=True)
    for k, a_ in room_faces().items():
        ML.save_img(os.path.join(p, f'room_{k}'), a_)


# ================================================================================================= model materials
def materials():
    m('brick', brick_tex(), shade=30)
    m('cap', TL.stone((172, 172, 176), cells=10), shade=30)
    m('post', TL.solid((196, 196, 198), 2, 3, 64), shade=30)
    m('cstone', TL.grime(TL.bricks((168, 156, 136), (130, 120, 104), rows=6, cols=3, vary=16, seed=47), 0.2, seed=48), shade=30)
    m('rock', rock_tex(), shade=80)
    m('flock_m', flock_tex(), shade=80)
    m('wood', TL.planks((140, 92, 52), n_planks=4, grain=10, vertical=True), shade=30)
    m('woodh', TL.planks((140, 92, 52), n_planks=4, grain=10), shade=30, tag='h')
    m('wood_dark', TL.planks((86, 56, 34), n_planks=3, grain=8, vertical=True), shade=30)
    m('maple_m', TL.planks((214, 150, 84), n_planks=3, grain=10), shade=30)
    m('iron', TL.metal((70, 72, 78), brushed=False), 'lms', v=0.12, shade=40)
    m('steel', TL.metal((176, 182, 192)), 'lms', v=0.25, shade=50)
    m('gold', TL.metal((222, 176, 60), brushed=False), 'lms', v=0.45, shade=60)
    m('coins', coins_tex(), 'lms', v=0.35, shade=80)
    m('straw', TL.stripes((206, 176, 96), (170, 140, 70), n_stripes=24), shade=60)
    m('rope', TL.stripes((180, 150, 100), (140, 110, 70), n_stripes=12, vertical=False), shade=60)
    m('cloth_red', TL.fabric((160, 50, 40), weave=64), shade=60)
    m('cloth_blue', TL.fabric((50, 80, 150), weave=64), shade=60)
    m('cloth_green', TL.fabric((60, 110, 60), weave=64), shade=60)
    m('cloth_brown', TL.fabric((120, 84, 50), weave=64), shade=60)
    m('fire', fire_tex(), 'add', deform='wave 40 sin 0 3 0 2.5')
    m('ember', TL.solid((255, 120, 30), 2, 5, 64), 'glow')
    m('ash', TL.solid((50, 46, 42), 3, 6, 64), shade=40)
    m('bone_m', TL.solid(PAINT['bone'], 3, 7, 64), shade=60)
    m('parch', TL.solid((232, 216, 170), 3, 8, 64), shade=20, two=True)
    for k, c in PAINT.items():
        m(f'p_{k}', TL.solid(c, 2, 50 + len(k), 64), shade=60, tag='p' + k)
    m('base', TL.solid((26, 26, 28), 1, 11, 64), 'lms', v=0.08, shade=40)
    m('base_rim', TL.solid((60, 120, 50), 2, 12, 64), shade=40)
    m('scale', dragon_scale_tex(), shade=70)
    m('belly', TL.stripes((90, 96, 92), (60, 66, 64), n_stripes=16, vertical=False), shade=70)
    m('wing', wing_tex(), shade=70, two=True)
    m('horn', TL.solid((210, 196, 160), 3, 13, 64), shade=60)
    m('eye', TL.solid((255, 200, 40), 1, 14, 32), 'glow')
    m('maw', TL.solid((150, 30, 30), 2, 15, 64), shade=60)
    m('needles', needle_tex(), shade=70)
    m('bark', TL.planks((96, 70, 50), n_planks=6, grain=14, vertical=True, gap=(60, 44, 30)), shade=70)
    m('felt', TL.fabric((120, 30, 40), weave=96), shade=40)
    m('ceramic', TL.solid((236, 232, 222), 2, 16), 'lms', v=0.15, shade=70)
    m('mug_logo', mug_label(), 'lms', v=0.1, shade=70, lathe=True)
    m('coffee', TL.solid((60, 34, 18), 2, 17, 64), 'lms', v=0.3, shade=60)
    m('paper', TL.solid((246, 244, 236), 2, 18, 64), shade=40, two=True)
    m('csheet', char_sheet_tex(), shade=20)
    m('screen_front', screen_art(), shade=20)
    m('screen_back', screen_tables(), shade=20)
    m('screen_edge', TL.solid((40, 30, 26), 2, 19, 64), shade=30)
    for i, (t, col) in enumerate(BOOKS):
        m(f'book_c{i}', book_cover(t, col), shade=20)
        m(f'book_s{i}', TL.solid(col, 3, 60 + i, 64), shade=20)
    m('pages', TL.stripes((244, 238, 220), (220, 212, 190), n_stripes=32, vertical=False), shade=20)
    m('pencil_y', TL.solid((240, 190, 40), 2, 20, 64), shade=60)
    m('pencil_tip', TL.solid((220, 190, 150), 2, 21, 64), shade=60)
    m('graphite', TL.solid((50, 50, 56), 2, 22, 64), shade=60)
    m('eraser', TL.solid((236, 130, 150), 2, 23, 64), shade=60)
    m('chips', TL.solid((236, 196, 90), 4, 24, 64) + ML.N3(64, 1, 25, 20), shade=80)
    m('bowl', TL.solid((40, 90, 160), 2, 26), 'lms', v=0.15, shade=70)
    for nm, col in DICE_COLS.items():
        m(f'd20_{nm}', d20_atlas(col), 'lms', v=0.2, shade=1)
        m(f'd6_{nm}', d6_face(col), 'lms', v=0.2, shade=1)
    m('stone_light', TL.stone((190, 184, 172), cells=8), shade=30)
    m('stone_dark', TL.stone((90, 86, 84), cells=10), shade=30)
    m('rune', rune_tex(), 'glow')
    m('cork', TL.fill(128, (176, 132, 84), 2, 27) + ML.N3(128, 1, 28, 24), shade=40)
    m('sticker', TL.pad_sticker(bg=(250, 200, 60), fg=(150, 40, 30), text='LEAP!'), 'alpha', alpha=TL.disc_alpha())
    m('web', web_tex(), 'add')
    m('shadow', TL.solid((10, 10, 12), 1, 29, 32), shade=30)
    m('led_m', TL.solid((255, 214, 120), 1, 30, 32), 'glow')
    m('sign_tt', TL.label('DICE TOWER', 512, 128, (60, 40, 24), (240, 200, 110), border=(200, 160, 80)), shade=20)
    m('water_m', TL.solid((50, 110, 140), 2, 31, 64), 'lms', v=0.3, shade=60)


BOOKS = [("PADVENTURER'S HANDBOOK", (150, 40, 36)), ("PADMASTER'S GUIDE", (40, 60, 120)),
         ("COMPENDIUM OF MONSTERS", (50, 100, 50)), ('DUCKS & DRAGONS', (110, 60, 130))]
DICE_COLS = {'red': (190, 40, 40), 'blue': (40, 80, 190), 'purple': (120, 50, 170), 'green': (40, 150, 80),
             'white': (230, 226, 216), 'black': (40, 40, 44)}


def coins_tex(n=128):
    rng = np.random.default_rng(5)
    im, d = canvas(n, n, (150, 100, 20))
    for _ in range(70):
        x, y, r = rng.integers(0, n), rng.integers(0, n), rng.integers(5, 11)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=(250, 206, 70), outline=(176, 126, 20))
    return arr(im)


def fire_tex(n=128):
    x, y = TL.xy(n)
    t = np.clip(1 - y, 0, 1)
    w = 1 - np.abs(x - 0.5) * 2
    f = np.clip(w * 1.4 - (1 - t) * 0.9, 0, 1)
    c = np.zeros((n, n, 3), np.float32)
    c[..., 0] = 255 * np.clip(f * 1.6, 0, 1)
    c[..., 1] = 230 * np.clip(f * 1.2 - 0.2, 0, 1)
    c[..., 2] = 120 * np.clip(f - 0.6, 0, 1)
    return c


def dragon_scale_tex(n=256):
    """dark slate scales with orange spots along rows (the photo dragon)"""
    x, y = TL.xy(n)
    base = TL.fill(n, (58, 66, 72), 4, 33)
    rows = 16
    yy = y * rows; xx = x * rows + (np.floor(yy) % 2) * 0.5
    fx, fy = xx % 1 - 0.5, yy % 1
    edge = (fx ** 2 * 3 + (fy - 0.15) ** 2) > 0.3
    base[edge] *= 0.55
    spot = ((np.floor(xx) % 5 == 2) & (np.floor(yy) % 3 == 1)) & ~edge
    base[spot] = (230, 120, 30)
    return base + ML.N3(n, 1, 34, 8)


def wing_tex(n=256):
    x, y = TL.xy(n)
    c = TL.fill(n, (70, 58, 56), 8, 35)
    v = (np.abs(np.sin(x * math.pi * 6)) < 0.05)
    c[v] *= 0.6
    c[(y > 0.9)] = (220, 110, 40)
    return c


def needle_tex(n=128):
    rng = np.random.default_rng(9)
    im, d = canvas(n, n, (36, 70, 40))
    for _ in range(500):
        x, y = rng.integers(0, n), rng.integers(0, n)
        c = (int(rng.integers(30, 70)), int(rng.integers(80, 130)), int(rng.integers(40, 70)))
        d.line((x, y, x + rng.integers(-4, 5), y + rng.integers(6, 14)), fill=c, width=2)
    return arr(im)


def mug_label(w=512, h=256):
    im, d = canvas(w, h, (236, 232, 222))
    d.rectangle((0, 90, w, 170), fill=(150, 30, 30))
    ctext(d, w / 2, 100, 'I ROLLED A NAT 20', ML.font(46, serif=True), (250, 230, 160))
    return arr(im)


def char_sheet_tex(w=512, h=512):
    im, d = canvas(w, h, (246, 242, 228))
    d.text((24, 16), 'CHARACTER SHEET', font=ML.font(36, serif=True), fill=(60, 30, 30))
    d.text((24, 66), 'Name: Padman   Class: Hero   Lvl 20', font=ML.font(20, serif=False), fill=(30, 30, 60))
    for k, s in enumerate(('STR 18', 'DEX 20', 'CON 16', 'INT 12', 'WIS 10', 'CHA 19')):
        y = 110 + k * 62
        d.rectangle((24, y, 140, y + 54), outline=(60, 60, 60), width=3)
        d.text((36, y + 12), s, font=ML.font(24, serif=False), fill=(30, 30, 30))
    for k in range(12):
        d.line((170, 120 + k * 30, w - 24, 120 + k * 30), fill=(170, 170, 170), width=2)
    d.text((170, 92), 'Equipment: Balloony, Pumper, 3 duckies', font=ML.font(18, serif=False), fill=(30, 30, 60))
    return arr(im)


def screen_art(w=1024, h=512):
    """the players' side of the DM screen: an invented landscape with a dragon silhouette and the title"""
    im, d = canvas(w, h, (60, 40, 70))
    for k in range(h):
        t = k / h
        d.line((0, k, w, k), fill=(int(240 - 120 * t), int(150 - 80 * t), int(80 + 40 * t)))
    d.polygon([(0, h), (0, 300), (180, 200), (360, 320), (560, 180), (760, 300), (1024, 220), (1024, h)], fill=(50, 40, 60))
    d.polygon([(0, h), (0, 400), (300, 340), (600, 420), (1024, 360), (1024, h)], fill=(30, 26, 40))
    d.polygon([(600, 140), (660, 110), (700, 130), (760, 60), (740, 140), (820, 120), (720, 170), (640, 170)], fill=(30, 20, 30))
    ctext(d, w / 2, 20, 'DUCKS & DRAGONS', ML.font(84, serif=True), (250, 210, 120), stroke_width=4, stroke_fill=(60, 20, 20))
    ctext(d, w / 2, 120, 'Padmaster Screen', ML.font(40, serif=True), (250, 230, 190))
    return arr(im)


def screen_tables(w=1024, h=512):
    im, d = canvas(w, h, (230, 220, 196))
    f = ML.font(26, serif=False)
    for c in range(3):
        x = 30 + c * 330
        d.text((x, 20), ['CONDITIONS', 'COVER', 'ENCOUNTERS'][c], font=ML.font(30, serif=True), fill=(120, 30, 30))
        for k in range(10):
            d.text((x, 70 + k * 42), f'{k + 1:2d}. ' + ['Prone', 'Stunned', 'Ducked', 'Inspired', 'Dizzy'][k % 5], font=f, fill=(30, 30, 30))
    return arr(im)


def book_cover(title, col, w=512, h=512):
    im, d = canvas(w, h, col)
    d.rectangle((24, 24, w - 24, h - 24), outline=(230, 190, 90), width=8)
    words = title.split()
    lines, cur = [], ''
    for wd in words:
        if len(cur) + len(wd) > 12: lines.append(cur.strip()); cur = ''
        cur += wd + ' '
    lines.append(cur.strip())
    for k, s in enumerate(lines):
        ctext(d, w / 2, 120 + k * 80, s, ML.font(56, serif=True), (240, 210, 120))
    d.ellipse((w / 2 - 60, 360, w / 2 + 60, 470), outline=(240, 210, 120), width=6)
    return arr(im)


def d20_atlas(col, cell=128):
    """5 x 4 cells, number k+1 in cell k, light numbers on the die colour"""
    w, h = cell * 5, cell * 4
    im, d = canvas(w, h, col)
    light = (250, 246, 230) if sum(col) < 500 else (40, 40, 40)
    f = ML.font(48, serif=False)
    for k in range(20):
        cx, cy = (k % 5) * cell + cell / 2, (k // 5) * cell + cell / 2
        s = str(k + 1)
        ctext(d, cx, cy - 22, s, f, light)
        if s in ('6', '9'): d.line((cx - 14, cy + 30, cx + 14, cy + 30), fill=light, width=4)
    return arr(im)


def d6_face(col, n=256):
    """one texture with six faces in a 3 x 2 atlas (pips 1-6)"""
    cell = n // 2
    im, d = canvas(cell * 3, cell * 2, col)
    light = (250, 246, 230) if sum(col) < 500 else (40, 40, 40)
    P = {1: [(0.5, 0.5)], 2: [(0.25, 0.25), (0.75, 0.75)], 3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
         4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
         5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
         6: [(0.25, 0.22), (0.75, 0.22), (0.25, 0.5), (0.75, 0.5), (0.25, 0.78), (0.75, 0.78)]}
    for k in range(6):
        ox, oy = (k % 3) * cell, (k // 3) * cell
        d.rounded_rectangle((ox + 3, oy + 3, ox + cell - 3, oy + cell - 3), 20, outline=tuple(int(c * 0.7) for c in col), width=4)
        for (u, v) in P[k + 1]:
            r = cell * 0.08
            d.ellipse((ox + u * cell - r, oy + v * cell - r, ox + u * cell + r, oy + v * cell + r), fill=light)
    return arr(im)


def rune_tex(n=256):
    im, d = canvas(n, n, (0, 0, 0))
    c = n / 2
    for r, wd in ((118, 6), (96, 3)):
        d.ellipse((c - r, c - r, c + r, c + r), outline=(80, 200, 255), width=wd)
    for k in range(6):
        a = k * math.pi / 3
        d.line((c + math.cos(a) * 96, c + math.sin(a) * 96, c + math.cos(a + 2 * math.pi / 3) * 96,
                c + math.sin(a + 2 * math.pi / 3) * 96), fill=(80, 200, 255), width=3)
    return arr(im)


def web_tex(n=128):
    im, d = canvas(n, n, (0, 0, 0))
    for k in range(8):
        a = k * math.pi / 8
        d.line((0, 0, n * math.cos(a) * 1.5, n * math.sin(a) * 1.5), fill=(120, 120, 120), width=1)
    for r in range(16, n * 2, 18):
        d.arc((-r, -r, r, r), 0, 90, fill=(110, 110, 110), width=1)
    return arr(im)


# ================================================================================================= models
def all_models():
    dragon(); hoard()
    for kind in ('ogre', 'dwarf', 'wizard', 'knight', 'goblin', 'skeleton', 'rogue'):
        mini(kind)
    campfire(); bedroll(); barrel(); crate(); table(); bench(); bed(); shelf(); weapon_rack(); anvil(); brazier()
    well(); coffin(); chest(); pedestal(); rubble(); dummy(); pine(); door_leaf(); torch_bracket(); stool()
    d20s(); d6s(); mug(); dice_tower(); dm_screen(); book_stack(); char_sheet(); pencil(); snack_bowl(); dice_tray()
    cobweb(); bones(); pad_skins()


# ---------------------------------------------------------------- the dragon (centrepiece)
def dragon():
    """an ancient dragon miniature, head at -x, rearing a little with the jaw open and wings raised. Footprint ~1300 x
    600 (wing tips higher up reach +-420 in y). Feet and tail tip rest on z 0."""
    X = ML.Model(); sc, bl, wg = M_['scale'], M_['belly'], M_['wing']
    # body
    ellipsoid(X.mesh(sc), (0, 0, 270), 270, 150, 140, nu=28, nv=16,
              bump=lambda p, t: 1 + 0.06 * math.sin(6 * t) * math.cos(p))
    ellipsoid(X.mesh(bl), (-40, 0, 205), 230, 110, 80, nu=20, nv=10)
    ellipsoid(X.mesh(sc), (-170, 0, 320), 150, 130, 130, nu=20, nv=12)              # chest
    # neck (S curve up and forward) + head
    neck = [(-200, 0, 360), (-290, 0, 440), (-350, 0, 530), (-400, 0, 600), (-460, 0, 630)]
    tube(X.mesh(sc), neck, [105, 92, 80, 70, 62], nseg=18)
    hx, hz = -540, 630
    ellipsoid(X.mesh(sc), (hx, 0, hz), 110, 62, 58, nu=20, nv=12)                   # skull
    ellipsoid(X.mesh(sc), (hx - 110, 0, hz + 6), 90, 44, 34, nu=16, nv=10)          # upper snout
    ellipsoid(X.mesh(bl), (hx - 90, 0, hz - 58), 100, 40, 20, nu=16, nv=8, R=Ry(-22))   # open lower jaw
    ellipsoid(X.mesh(M_['maw']), (hx - 80, 0, hz - 26), 80, 34, 14, nu=12, nv=6)
    for s in (-1, 1):
        sphere(X.mesh(M_['eye']), (hx - 40, s * 46, hz + 26), 13, nu=10, nv=6)
        tube(X.mesh(M_['horn']), [(hx + 30, s * 40, hz + 40), (hx + 100, s * 70, hz + 90), (hx + 190, s * 90, hz + 110), (hx + 250, s * 80, hz + 90)],
             [18, 14, 9, 2], nseg=10)
        for k in range(4):                                                              # teeth
            tube(X.mesh(M_['bone_m']), [(hx - 170 + k * 26, s * 30, hz - 20), (hx - 170 + k * 26, s * 30, hz - 46)], [5, 1], nseg=6)
    # spikes along neck, back and tail
    spine = [(-460, 690), (-380, 650), (-300, 520), (-200, 460), (-80, 420), (40, 415), (160, 400), (260, 360)]
    for (x, z) in spine:
        tube(X.mesh(M_['horn']), [(x, 0, z - 20), (x + 30, 0, z + 50)], [22, 2], nseg=8)
    # tail: curls round to the +y side and rests on the ground
    tail = [(240, 0, 260), (380, 40, 190), (520, 130, 110), (660, 230, 50), (800, 210, 26), (900, 100, 18), (940, -20, 14)]
    tube(X.mesh(sc), tail, [110, 92, 70, 50, 34, 22, 6], nseg=16)
    for k in range(1, 6):
        x, y, z = tail[k]
        tube(X.mesh(M_['horn']), [(x, y, z + [90, 70, 50, 34, 22, 14][k - 1] - 10), (x + 20, y, z + [90, 70, 50, 34, 22, 14][k - 1] + 36)], [16, 1], nseg=6)
    # legs (front + hind), feet with claws
    for s in (-1, 1):
        fl = [(-170, s * 110, 300), (-200, s * 150, 190), (-210, s * 160, 90), (-240, s * 170, 30)]
        tube(X.mesh(sc), fl, [64, 52, 42, 36], nseg=14)
        ellipsoid(X.mesh(sc), (-260, s * 172, 22), 66, 44, 22, nu=14, nv=8, flat_bottom=-22)
        hl = [(120, s * 120, 290), (170, s * 170, 200), (110, s * 190, 90), (140, s * 190, 30)]
        ellipsoid(X.mesh(sc), (130, s * 130, 250), 120, 70, 100, nu=16, nv=10)
        tube(X.mesh(sc), hl, [70, 58, 44, 38], nseg=14)
        ellipsoid(X.mesh(sc), (120, s * 192, 22), 76, 48, 22, nu=14, nv=8, flat_bottom=-22)
        for fx, fy in ((-320, s * 150), (-325, s * 172), (-320, s * 196), (40, s * 168), (35, s * 192), (40, s * 218)):
            tube(X.mesh(M_['horn']), [(fx + 20, fy, 14), (fx - 12, fy, 6), (fx - 20, fy, 0.5)], [9, 6, 1], nseg=6)
    # wings: arm bone + four fingers, membrane quads between them (two-sided)
    for s in (-1, 1):
        sh = np.array([-80, s * 120, 400.0])
        wrist = np.array([60, s * 330, 760.0])
        tips = [np.array(p, float) for p in ((420, s * 420, 820), (520, s * 400, 600), (460, s * 330, 430), (300, s * 220, 380))]
        tube(X.mesh(sc), [sh, (sh + wrist) / 2 + np.array([0, 0, 40]), wrist], [34, 26, 20], nseg=10)
        for t in tips:
            tube(X.mesh(M_['horn']), [wrist, (wrist + t) / 2 + np.array([0, 0, 20]), t], [14, 9, 3], nseg=8)
        root = [np.array([200, s * 110, 360.0]), np.array([60, s * 120, 420.0])]
        chain = [wrist] + tips + [root[0]]
        for k in range(len(tips)):
            a, b = tips[k], tips[k + 1] if k + 1 < len(tips) else root[0]
            mid = (a + b) / 2 + np.array([-30, 0, -30])            # scalloped edge
            for tri in ((wrist, a, mid), (wrist, mid, b)):
                n = np.cross(tri[1] - tri[0], tri[2] - tri[0]); n /= np.linalg.norm(n)
                X.mesh(wg).poly(list(tri), n, [(0, 0), (1, 0), (0.5, 1)])
        tri = (wrist, root[0], root[1])
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0]); n /= np.linalg.norm(n)
        X.mesh(wg).poly(list(tri), n, [(0, 0), (1, 0), (0.5, 1)])
        tri = (wrist, root[1], sh)
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0]); n /= np.linalg.norm(n)
        X.mesh(wg).poly(list(tri), n, [(0, 0), (1, 0), (0.5, 1)])
    ML.save('dragon', X)
    coll('dragon', boxes=[((-300, -150, 150), (260, 150, 400)), ((-480, -70, 300), (-300, 70, 600)),
                          ((-650, -60, 600), (-480, 60, 700)),
                          ((-330, -190, 0), (-170, -110, 150)), ((-330, 110, 0), (-170, 190, 150)),
                          ((40, -220, 0), (210, -110, 150)), ((40, 110, 0), (210, 220, 150)),
                          ((260, -40, 0), (560, 200, 220)), ((560, 120, 0), (840, 280, 80))])


def hoard():
    """the dragon's treasure: a low heap of gold coins with goblets and a crown. Walkable (16u high rim, gentle hill)."""
    X = ML.Model()
    ellipsoid(X.mesh(M_['coins']), (0, 0, 0), 230, 170, 30, nu=24, nv=8, flat_bottom=0,
              bump=lambda p, t: 1 + 0.08 * math.sin(5 * t))
    for (x, y, a) in ((-120, 60, 0), (90, -70, 40), (40, 90, 80)):
        revolve(X.mesh(M_['gold']), [(18, 0), (6, 6), (5, 30), (22, 44), (24, 70), (20, 70), (0, 46)], n=14, cx=x, cy=y)
    revolve(X.mesh(M_['gold']), [(40, 30), (40, 50), (48, 66), (36, 58), (26, 70), (20, 56), (0, 56)], n=10, cx=-20, cy=-40)
    ML.save('hoard', X)


# ---------------------------------------------------------------- miniatures
def mini(kind):
    """28 mm miniature on a black base (base 10u: a step). Faces -y. Collision = one box round the figure."""
    X = ML.Model()
    big = kind == 'ogre'
    R = 110 if big else 60
    revolve(X.mesh(M_['base']), [(R, 0), (R, BASE_H - 2), (R - 2, BASE_H), (0, BASE_H)], n=32, inward=True)
    disc(X.mesh(M_['base_rim']), R - 6, BASE_H + 0.5, n=32)
    z0 = BASE_H
    P = lambda c: M_[f'p_{c}']
    S = {'ogre': 1.45, 'dwarf': 0.82, 'goblin': 0.7}.get(kind, 1.0)

    def body(skin, cloth, legs, hz=None):
        h = 150 * S
        for s in (-1, 1):
            tube(X.mesh(P(legs)), [(s * 14 * S, 0, z0), (s * 14 * S, 0, z0 + h * 0.45)], [10 * S, 12 * S], nseg=8)
            ellipsoid(X.mesh(P('brown')), (s * 14 * S, -6 * S, z0 + 6 * S), 12 * S, 18 * S, 8 * S, nu=8, nv=4, flat_bottom=-6 * S)
        ellipsoid(X.mesh(P(cloth)), (0, 0, z0 + h * 0.62), 26 * S, 18 * S, 30 * S, nu=14, nv=8)
        sphere(X.mesh(P(skin)), (0, 0, z0 + h * 0.9), 15 * S, nu=12, nv=8)
        return h
    if kind == 'ogre':
        h = body('ogre', 'brown', 'ogre')
        sphere(X.mesh(P('ogre')), (0, -4, z0 + h * 0.58), 32 * S, nu=14, nv=8)        # belly
        for s in (-1, 1):
            tube(X.mesh(P('ogre')), [(s * 30 * S, 0, z0 + h * 0.76), (s * 44 * S, -10, z0 + h * 0.55), (s * 46 * S, -20, z0 + h * 0.4)], [10 * S, 9 * S, 8 * S], nseg=8)
        tube(X.mesh(M_['wood']), [(46 * S, -20, z0 + h * 0.4), (60 * S, -40, z0 + h * 0.95)], [6, 16], nseg=8)      # club
        for s in (-1, 1):
            tube(X.mesh(P('bone')), [(s * 6 * S, -12 * S, z0 + h * 0.86), (s * 9 * S, -16 * S, z0 + h * 0.94)], [3, 0.5], nseg=5)
        for s in (-1, 1):
            sphere(X.mesh(P('black')), (s * 8 * S, -13 * S, z0 + h * 0.93), 3.5 * S, nu=6, nv=4)
        ellipsoid(X.mesh(P('brown')), (0, -8, z0 + h * 0.42), 30 * S, 22 * S, 12 * S, nu=12, nv=6)
        top = z0 + h + 10
    elif kind == 'dwarf':
        h = body('tan', 'red', 'brown')
        ellipsoid(X.mesh(P('beard')), (0, -10, z0 + h * 0.75), 16 * S, 10 * S, 22 * S, nu=10, nv=6)
        X2 = ML.Model(); revolve(X2.mesh(P('steel')), [(17 * S, 0), (14 * S, 12 * S), (0, 18 * S)], n=12)
        X.add_model(X2, np.eye(3), (0, 0, z0 + h * 0.92))
        tube(X.mesh(M_['wood']), [(30, -10, z0 + 20), (34, -14, z0 + 130)], 4, nseg=6)
        rbox(X.mesh(P('steel')), (22, -18, z0 + 110), (56, -10, z0 + 140), r=2, k=1)  # axe head
        for s in (-1, 1):
            tube(X.mesh(P('red')), [(s * 20 * S, 0, z0 + h * 0.78), (s * 30 * S, -10, z0 + h * 0.55)], 8 * S, nseg=8)
        top = z0 + 150
    elif kind == 'wizard':
        h = 150
        revolve(X.mesh(P('blue')), [(34, z0), (30, z0 + 30), (20, z0 + 110), (0, z0 + 120)], n=14)       # robe
        sphere(X.mesh(P('tan')), (0, 0, z0 + 132), 14, nu=12, nv=8)
        ellipsoid(X.mesh(P('white')), (0, -10, z0 + 112), 10, 7, 20, nu=8, nv=6)                         # beard
        revolve(X.mesh(P('blue')), [(30, z0 + 140), (18, z0 + 146), (4, z0 + 200), (0, z0 + 204)], n=14)  # hat
        tube(X.mesh(M_['wood']), [(32, -6, z0), (34, -8, z0 + 210)], 4, nseg=6)
        sphere(X.mesh(M_['eye']), (34, -8, z0 + 218), 10, nu=8, nv=6)
        tube(X.mesh(P('blue')), [(14, 0, z0 + 100), (32, -6, z0 + 90)], 7, nseg=6)
        top = z0 + 230
    elif kind == 'knight':
        h = body('steel', 'steel', 'steel')
        rbox(X.mesh(P('red')), (-30, -20, z0 + 40), (30, -8, z0 + 110), r=4, k=1)                    # tabard
        X2 = ML.Model(); revolve(X2.mesh(P('steel')), [(17, -4), (17, 14), (12, 22), (0, 24)], n=12)
        X.add_model(X2, np.eye(3), (0, 0, z0 + h * 0.88))
        rbox(X.mesh(P('blue')), (-48, -30, z0 + 50), (-40, 10, z0 + 110), r=4, k=1)                 # shield
        tube(X.mesh(P('steel')), [(36, -10, z0 + 70), (40, -40, z0 + 170)], [4, 2], nseg=6)
        rbox(X.mesh(P('gold')), (28, -18, z0 + 64), (50, -2, z0 + 72), r=1, k=1)
        top = z0 + 175
    elif kind == 'goblin':
        h = body('gob', 'brown', 'gob')
        for s in (-1, 1):
            tube(X.mesh(P('gob')), [(s * 12, 0, z0 + h * 0.92), (s * 32, 6, z0 + h * 0.98)], [5, 0.5], nseg=5)   # ears
        tube(X.mesh(M_['wood']), [(26, -6, z0), (28, -10, z0 + 170)], 3, nseg=6)
        X2 = ML.Model(); revolve(X2.mesh(P('steel')), [(6, 0), (0, 22)], n=6)
        X.add_model(X2, np.eye(3), (28, -10, z0 + 170))
        top = z0 + 190
    elif kind == 'skeleton':
        bn = 'bone'
        for s in (-1, 1):
            tube(X.mesh(P(bn)), [(s * 12, 0, z0), (s * 12, 0, z0 + 70)], 5, nseg=6)
            tube(X.mesh(P(bn)), [(s * 18, 0, z0 + 120), (s * 26, -14, z0 + 80)], 4, nseg=6)
        for k in range(5):
            tube(X.mesh(P(bn)), [(-18, -2, z0 + 82 + k * 10), (18, -2, z0 + 82 + k * 10)], 3, nseg=5)
        tube(X.mesh(P(bn)), [(0, 0, z0 + 70), (0, 0, z0 + 130)], 4, nseg=6)
        sphere(X.mesh(P(bn)), (0, 0, z0 + 142), 15, nu=10, nv=8)
        sphere(X.mesh(P('black')), (-6, -12, z0 + 146), 4, nu=6, nv=4); sphere(X.mesh(P('black')), (6, -12, z0 + 146), 4, nu=6, nv=4)
        tube(X.mesh(P('steel')), [(26, -14, z0 + 80), (30, -50, z0 + 150)], [3, 1.5], nseg=6)
        rbox(X.mesh(P('grey')), (-40, -24, z0 + 60), (-34, 10, z0 + 110), r=3, k=1)
        top = z0 + 160
    else:   # rogue
        h = body('tan', 'green', 'black')
        revolve(X.mesh(P('green')), [(30, z0 + 60), (22, z0 + 100), (16, z0 + 140), (0, z0 + 166)], n=12)    # cloak + hood
        for s in (-1, 1):
            tube(X.mesh(P('steel')), [(s * 26, -12, z0 + 80), (s * 30, -40, z0 + 110)], [3, 1], nseg=5)
        top = z0 + 166
    ML.save(f'mini_{kind}', X)
    w = 30 * S + 20
    coll(f'mini_{kind}', boxes=[((-R + 4, -R + 4, 0), (R - 4, R - 4, BASE_H)), ((-w, -w, BASE_H), (w, w, top))])


# ---------------------------------------------------------------- dungeon dressing
def campfire():
    X = ML.Model()
    rng = np.random.default_rng(3)
    for k in range(10):
        a = k * 2 * math.pi / 10
        ellipsoid(X.mesh(M_['stone_dark']), (math.cos(a) * 70, math.sin(a) * 70, 10), 20, 16, 14, nu=8, nv=5, flat_bottom=-10,
                  R=Rz(math.degrees(a)))
    disc(X.mesh(M_['ash']), 56, 1, n=20)
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        tube(X.mesh(M_['wood_dark']), [(math.cos(a) * 50, math.sin(a) * 50, 8), (math.cos(a) * 8, math.sin(a) * 8, 36)], 8, nseg=8)
    for k in range(3):                                                                    # crossed flame quads
        a = math.radians(k * 60)
        c, s = math.cos(a) * 34, math.sin(a) * 34
        X.mesh(M_['fire']).poly([(-c, -s, 90), (c, s, 90), (c, s, 10), (-c, -s, 10)], (-math.sin(a), math.cos(a), 0),
                                [(0, 0), (1, 0), (1, 1), (0, 1)])
    sphere(X.mesh(M_['ember']), (0, 0, 14), 22, nu=8, nv=4)
    for k in range(3):                                                                    # tripod + pot
        a = k * 2 * math.pi / 3
        tube(X.mesh(M_['wood']), [(math.cos(a) * 100, math.sin(a) * 100, 0), (0, 0, 200)], 4, nseg=6)
    tube(X.mesh(M_['iron']), [(0, 0, 200), (0, 0, 130)], 1.5, nseg=4)
    revolve(X.mesh(M_['iron']), [(0, 90), (26, 94), (34, 110), (30, 130), (32, 132)], n=16)
    ML.save('campfire', X)
    coll('campfire', cyls=[(0, 0, 80, 0, 40)])


def bedroll():
    X = ML.Model()
    rbox(X.mesh(M_['cloth_green']), (-50, -110, 0), (50, 80, 8), r=3, k=1, tile=128)
    tube(X.mesh(M_['cloth_green']), [(-50, 100, 18), (50, 100, 18)], 18, nseg=12)
    tube(X.mesh(M_['rope']), [(-30, 100, 18), (-30, 100.1, 18.1)], 19, nseg=12, caps=(False, False))
    ML.save('bedroll', X)


def barrel():
    X = ML.Model()
    revolve(X.mesh(M_['wood']), [(46, 0), (54, 40), (58, 70), (54, 100), (46, 140)], n=20, u_tiles=3)
    disc(X.mesh(M_['woodh']), 46, 140, n=20)
    for z in (16, 70, 124):
        r = 47 if z != 70 else 59
        tube(X.mesh(M_['iron']), [(0, 0, z - 4), (0, 0, z + 4)], r, nseg=20, caps=(False, False))
    ML.save('barrel', X)
    coll('barrel', cyls=[(0, 0, 54, 0, 140)])


def crate():
    X = ML.Model()
    rbox(X.mesh(M_['woodh']), (-56, -56, 0), (56, 56, 112), r=3, k=1, tile=112)
    for z in (6, 106):
        for (a, b) in (((-58, -58, z - 6), (58, -54, z + 6)), ((-58, 54, z - 6), (58, 58, z + 6)),
                       ((-58, -54, z - 6), (-54, 54, z + 6)), ((54, -54, z - 6), (58, 54, z + 6))):
            rbox(X.mesh(M_['wood_dark']), a, b, r=1, k=1)
    ML.save('crate', X)
    coll('crate', boxes=[((-56, -56, 0), (56, 56, 112))])


def table():
    X = ML.Model()
    top = ((-170, -100, 84), (170, 100, 96))
    rbox(X.mesh(M_['woodh']), *top, r=3, k=1, tile=128)
    for (x, y) in ((-150, -80), (150, -80), (-150, 80), (150, 80)):
        rbox(X.mesh(M_['wood']), (x - 8, y - 8, 0), (x + 8, y + 8, 84), r=2, k=1)
    for k in range(3):                                                              # tankards
        revolve(X.mesh(M_['wood_dark']), [(10, 96), (12, 96), (12, 120), (0, 120)], n=10, cx=-90 + k * 70, cy=-30 + k * 20)
    rbox(X.mesh(M_['parch']), (20, 10, 96), (100, 70, 97), r=0.3, k=1)
    ML.save('table', X)
    coll('table', boxes=[top] + [((x - 8, y - 8, 0), (x + 8, y + 8, 84)) for (x, y) in ((-150, -80), (150, -80), (-150, 80), (150, 80))])


def bench():
    X = ML.Model()
    rbox(X.mesh(M_['woodh']), (-150, -24, 40), (150, 24, 52), r=2, k=1)
    for x in (-130, 130):
        rbox(X.mesh(M_['wood']), (x - 6, -22, 0), (x + 6, 22, 40), r=1, k=1)
    ML.save('bench', X)
    coll('bench', boxes=[((-150, -24, 0), (150, 24, 52))])


def stool():
    X = ML.Model()
    revolve(X.mesh(M_['woodh']), [(28, 40), (28, 48), (0, 48)], n=12, inward=True)
    for k in range(3):
        a = k * 2 * math.pi / 3
        tube(X.mesh(M_['wood']), [(math.cos(a) * 24, math.sin(a) * 24, 0), (math.cos(a) * 16, math.sin(a) * 16, 40)], 4, nseg=5)
    ML.save('stool', X)
    coll('stool', cyls=[(0, 0, 26, 0, 48)])


def bed():
    X = ML.Model()
    rbox(X.mesh(M_['wood']), (-70, -140, 0), (70, 140, 40), r=3, k=1)
    rbox(X.mesh(M_['straw']), (-62, -130, 40), (62, 130, 58), r=6, k=2)
    rbox(X.mesh(M_['cloth_red']), (-64, -60, 50), (64, 120, 62), r=5, k=2)
    rbox(X.mesh(M_['wood']), (-70, 130, 0), (70, 146, 110), r=3, k=1)
    ML.save('bed', X)
    coll('bed', boxes=[((-70, -140, 0), (70, 146, 58)), ((-70, 130, 58), (70, 146, 110))])


def shelf():
    """shelf against a wall (back at +y), 256 wide"""
    X = ML.Model()
    parts = [((-128, -40, 0), (-116, 40, 220)), ((116, -40, 0), (128, 40, 220)), ((-128, 28, 0), (128, 40, 220))]
    for z in (10, 80, 150, 210):
        parts.append(((-116, -40, z), (116, 28, z + 10)))
    for a, b in parts: rbox(X.mesh(M_['wood']), a, b, r=1, k=1)
    rng = np.random.default_rng(8)
    for z in (20, 90, 160):
        x = -110
        while x < 100:
            w = rng.integers(10, 22)
            col = rng.integers(0, 4)
            rbox(X.mesh(M_[f'book_s{col}']), (x, -20, z), (x + w - 2, 20, z + rng.integers(40, 56)), r=1, k=1)
            x += w
    ML.save('shelf', X)
    coll('shelf', boxes=[((-128, -40, 0), (128, 40, 220))])


def weapon_rack():
    X = ML.Model()
    for x in (-100, 100):
        rbox(X.mesh(M_['wood']), (x - 8, -8, 0), (x + 8, 8, 160), r=2, k=1)
    rbox(X.mesh(M_['woodh']), (-110, -10, 140), (110, 10, 152), r=2, k=1)
    rbox(X.mesh(M_['woodh']), (-110, -10, 20), (110, 10, 30), r=2, k=1)
    for k in range(5):
        x = -70 + k * 35
        tube(X.mesh(M_['wood']), [(x, -4, 24), (x, -4, 210)], 3, nseg=5)
        X2 = ML.Model(); revolve(X2.mesh(M_['steel']), [(6, 0), (0, 24)], n=6)
        X.add_model(X2, np.eye(3), (x, -4, 210))
    ML.save('weapon_rack', X)
    coll('weapon_rack', boxes=[((-110, -12, 0), (110, 12, 160))])


def anvil():
    X = ML.Model()
    rbox(X.mesh(M_['wood_dark']), (-40, -40, 0), (40, 40, 40), r=3, k=1)
    rbox(X.mesh(M_['iron']), (-28, -20, 40), (28, 20, 60), r=2, k=1)
    rbox(X.mesh(M_['iron']), (-60, -24, 60), (50, 24, 80), r=3, k=1)
    tube(X.mesh(M_['iron']), [(-60, 0, 72), (-90, 0, 74)], [18, 2], nseg=8)
    ML.save('anvil', X)
    coll('anvil', boxes=[((-60, -40, 0), (50, 40, 80))])


def brazier():
    X = ML.Model()
    for k in range(3):
        a = k * 2 * math.pi / 3
        tube(X.mesh(M_['iron']), [(math.cos(a) * 40, math.sin(a) * 40, 0), (math.cos(a) * 30, math.sin(a) * 30, 70)], 5, nseg=6)
    revolve(X.mesh(M_['iron']), [(20, 60), (50, 76), (56, 100), (52, 100), (0, 92)], n=16)
    sphere(X.mesh(M_['ember']), (0, 0, 96), 34, nu=10, nv=4)
    for k in range(3):
        a = math.radians(k * 60)
        c, s = math.cos(a) * 30, math.sin(a) * 30
        X.mesh(M_['fire']).poly([(-c, -s, 170), (c, s, 170), (c, s, 96), (-c, -s, 96)], (-math.sin(a), math.cos(a), 0),
                                [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('brazier', X)
    coll('brazier', cyls=[(0, 0, 50, 0, 100)])


WELL_R, WELL_RI, WELL_H = 104, 72, 32


def well():
    """stone well: ring 32 high (hop in), two posts, a crossbar with rope and bucket; the shaft is cut in the floor"""
    X = ML.Model()
    revolve(X.mesh(M_['stone_light']), [(WELL_R, 0), (WELL_R, WELL_H), (WELL_RI, WELL_H), (WELL_RI, 0), (WELL_RI - 6, 0), (WELL_RI - 6, -96)], n=24, u_tiles=4)
    for s in (-1, 1):
        rbox(X.mesh(M_['wood']), (s * 90 - 8, -8, WELL_H), (s * 90 + 8, 8, 230), r=2, k=1)
    tube(X.mesh(M_['wood']), [(-100, 0, 220), (100, 0, 220)], 7, nseg=8)
    tube(X.mesh(M_['rope']), [(10, 0, 220), (10, 0, 120)], 1.5, nseg=4)
    revolve(X.mesh(M_['wood_dark']), [(14, 96), (18, 120), (0, 120)], n=10, cx=10)
    # little roof
    for s in (-1, 1):
        X.mesh(M_['wood_dark']).quad((-120, 0, 270), (120, 0, 270), (120, s * 80, 226), (-120, s * 80, 226), tile=64)
    disc(X.mesh(M_['shadow']), WELL_RI - 6, -95, n=24)
    ML.save('well', X)


def coffin():
    X = ML.Model()
    poly = [(-50, -130), (-62, -60), (-50, 130), (50, 130), (62, -60), (50, -130)]
    mprism(X.mesh(M_['wood_dark']), poly, 0, 60, tile=64)
    lid = ML.Model()
    mprism(lid.mesh(M_['wood']), poly, 0, 10, tile=64)
    X.add_model(lid, Rz(12), (14, 6, 60))
    tube(X.mesh(M_['gold']), [(0, -60, 70.5), (0, 40, 70.5)], 3, nseg=4)
    ML.save('coffin', X)
    coll('coffin', boxes=[((-55, -125, 0), (55, 125, 70))])


def chest():
    X = ML.Model()
    rbox(X.mesh(M_['wood']), (-60, -40, 0), (60, 40, 50), r=3, k=1)
    tube(X.mesh(M_['wood']), [(-60, 0, 50), (60, 0, 50)], 40, nseg=12, caps=(True, True))
    for x in (-50, 0, 50):
        rbox(X.mesh(M_['gold']), (x - 4, -42, 0), (x + 4, 42, 52), r=1, k=1)
    ML.save('chest', X)
    coll('chest', boxes=[((-60, -40, 0), (60, 40, 80))])


def pedestal():
    """stepped stone plinth for the catalog statue: 16u step, then a 48u block (top 64)"""
    X = ML.Model()
    rbox(X.mesh(M_['stone_light']), (-110, -110, 0), (110, 110, 16), r=2, k=1, tile=128)
    rbox(X.mesh(M_['stone_light']), (-80, -80, 16), (80, 80, 64), r=2, k=1, tile=128)
    rbox(X.mesh(M_['cap']), (-88, -88, 56), (88, 88, 64), r=1, k=1)
    ML.save('pedestal', X)
    coll('pedestal', boxes=[((-110, -110, 0), (110, 110, 16)), ((-88, -88, 16), (88, 88, 64))])


def rubble():
    """loose bricks fallen from a broken wall (decor, < 30u high)"""
    X = ML.Model()
    rng = np.random.default_rng(12)
    for k in range(14):
        x, y = rng.uniform(-110, 110), rng.uniform(-60, 60)
        R = Rz(rng.uniform(0, 180)) @ Rx(rng.uniform(-20, 20))
        sub = ML.Model(); rbox(sub.mesh(M_['brick']), (-16, -8, -6), (16, 8, 6), r=2, k=1, tile=64)
        X.add_model(sub, R, (x, y, 7 + (k % 3) * 8))
    ML.save('rubble', X)


def dummy():
    """the red Y-frame in the photo: a wooden training stand with a straw dummy"""
    X = ML.Model()
    rbox(X.mesh(M_['wood']), (-60, -40, 0), (60, 40, 12), r=2, k=1)
    tube(X.mesh(M_['wood']), [(0, 0, 12), (0, 0, 120)], 9, nseg=8)
    for s in (-1, 1):
        tube(X.mesh(M_['wood']), [(0, 0, 120), (s * 50, 0, 190)], 8, nseg=8)
    ellipsoid(X.mesh(M_['straw']), (0, 0, 150), 24, 20, 36, nu=12, nv=8)
    sphere(X.mesh(M_['straw']), (0, 0, 200), 16, nu=10, nv=6)
    ML.save('dummy', X)
    coll('dummy', boxes=[((-60, -40, 0), (60, 40, 12)), ((-14, -14, 12), (14, 14, 210))])


def pine():
    """model-railway fir tree on a flock base: 4 cone tiers, ~520 tall"""
    X = ML.Model()
    tube(X.mesh(M_['bark']), [(0, 0, 0), (0, 0, 120)], [16, 12], nseg=10)
    for k, (z, r, h) in enumerate(((90, 150, 170), (190, 122, 160), (290, 92, 150), (380, 60, 140))):
        revolve(X.mesh(M_['needles']), [(r, z), (r * 0.6, z + h * 0.4), (0, z + h)], n=16, u_tiles=4,
                rfun=lambda a, rr, zz, k=k: rr * (1 + 0.12 * math.sin(7 * a + k)))
        disc(X.mesh(M_['needles']), r, z, up=False, n=16)
    revolve(X.mesh(M_['flock_m']), [(60, 0), (50, 8), (0, 10)], n=14, inward=True)
    ML.save('pine', X)
    coll('pine', cyls=[(0, 0, 18, 0, 400)])


def door_leaf():
    """open dungeon door: hinge at the origin, the leaf runs along +x (128 wide, 176 high)"""
    X = ML.Model()
    rbox(X.mesh(M_['wood']), (0, -5, 0), (124, 5, 176), r=2, k=1, tile=128)
    for z in (30, 140):
        rbox(X.mesh(M_['iron']), (0, -7, z), (110, 7, z + 10), r=1, k=1)
    sphere(X.mesh(M_['iron']), (110, -9, 90), 5, nu=8, nv=6)
    ML.save('door_leaf', X)
    coll('door_leaf', boxes=[((0, -5, 0), (124, 5, 176))])


def torch_bracket():
    """wall torch: bracket at the wall (origin, wall at +y), flame at z 40 above the origin"""
    X = ML.Model()
    rbox(X.mesh(M_['iron']), (-6, -2, -20), (6, 0, 10), r=1, k=1)
    tube(X.mesh(M_['wood_dark']), [(0, -4, -30), (0, -18, 30)], [4, 6], nseg=6)
    a = 0
    for k in range(2):
        a = math.radians(k * 90)
        c, s = math.cos(a) * 12, math.sin(a) * 12
        X.mesh(M_['fire']).poly([(-c, -18 - s, 70), (c, -18 + s, 70), (c, -18 + s, 26), (-c, -18 - s, 26)],
                                (-math.sin(a), math.cos(a), 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('torch', X)


def cobweb():
    X = ML.Model()
    X.mesh(M_['web']).poly([(0, 0, 0), (0, -120, 0), (0, -120, -0.01)], (1, 0, 0), [(0, 0), (1, 0), (1, 1)])
    X.mesh(M_['web']).poly([(0, 0, 0), (-110, 0, 0), (-110, 0, -110), (0, 0, -110)], (0, -1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    ML.save('cobweb', X)


def bones():
    X = ML.Model()
    rng = np.random.default_rng(4)
    for k in range(7):
        a = rng.uniform(0, math.pi)
        x, y = rng.uniform(-60, 60), rng.uniform(-40, 40)
        d = np.array([math.cos(a), math.sin(a), 0]) * 28
        tube(X.mesh(M_['bone_m']), [np.array([x, y, 5]) - d, np.array([x, y, 5]) + d], 4, nseg=6)
    sphere(X.mesh(M_['bone_m']), (40, 30, 14), 14, nu=10, nv=6)
    ML.save('bones', X)


# ---------------------------------------------------------------- things on the table rail (real-world objects)
D20_R = 80


def d20s():
    """icosahedron dice, numbers 1-20 from an atlas. Rests on a face (rotated so one face is flat on z 0)."""
    t = (1 + 5 ** 0.5) / 2
    V = np.array([(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                  (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)], float)
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = V / np.linalg.norm(V[0]) * D20_R
    # rotate so face 0's normal points down
    f0 = V[list(F[0])].mean(0); n0 = f0 / np.linalg.norm(f0)
    tgt = np.array([0, 0, -1.0])
    ax = np.cross(n0, tgt); s = np.linalg.norm(ax); c = n0 @ tgt
    K_ = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    R = np.eye(3) + K_ + K_ @ K_ * ((1 - c) / (s * s))
    V = V @ R.T
    V[:, 2] -= V[:, 2].min()
    uvs = []
    for k in range(20):
        cu, cv = (k % 5 + 0.5) / 5, (k // 5 + 0.5) / 4
        uvs.append([(cu, cv - 0.11), (cu - 0.09, cv + 0.08), (cu + 0.09, cv + 0.08)])
    for nm in ('red', 'blue', 'purple', 'green'):
        X = ML.Model()
        polyhedron(X.mesh(M_[f'd20_{nm}']), V, F, uvs)
        ML.save(f'd20_{nm}', X)
        coll(f'd20_{nm}', cyls=[(0, 0, D20_R * 0.85, 0, float(V[:, 2].max()) - 8)])


def d6s():
    s = 44
    V = [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0), (-s, -s, 2 * s), (s, -s, 2 * s), (s, s, 2 * s), (-s, s, 2 * s)]
    F = [(4, 5, 6, 7), (0, 3, 2, 1), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]
    uvs = []
    for k in range(6):
        u0, v0 = (k % 3) / 3, (k // 3) / 2
        uvs.append([(u0, v0), (u0 + 1 / 3, v0), (u0 + 1 / 3, v0 + 0.5), (u0, v0 + 0.5)])
    for nm in ('white', 'black', 'red', 'blue'):
        X = ML.Model()
        polyhedron(X.mesh(M_[f'd6_{nm}']), V, F, uvs)
        ML.save(f'd6_{nm}', X)
        coll(f'd6_{nm}', boxes=[((-s, -s, 0), (s, s, 2 * s))])


MUG_R, MUG_H = 190, 460


def mug():
    X = ML.Model()
    revolve(X.mesh(M_['mug_logo']), [(MUG_R, 0), (MUG_R, MUG_H)], n=40, u_tiles=1)
    revolve(X.mesh(M_['ceramic']), [(MUG_R, MUG_H), (MUG_R - 14, MUG_H), (MUG_R - 14, MUG_H - 60)], n=40)
    disc(X.mesh(M_['coffee']), MUG_R - 14, MUG_H - 60, n=40)
    pts = [(MUG_R - 6, 0, 380), (MUG_R + 90, 0, 370), (MUG_R + 130, 0, 260), (MUG_R + 90, 0, 140), (MUG_R - 6, 0, 120)]
    tube(X.mesh(M_['ceramic']), pts, 26, nseg=12)
    ML.save('mug', X)
    coll('mug', cyls=[(0, 0, MUG_R, 0, MUG_H)], boxes=[((MUG_R + 2, -26, 110), (MUG_R + 150, 26, 390))])


TOWER_W, TOWER_H = 320, 896


def dice_tower():
    """dice tower: wooden box with a dice tray in front (open south side), crenellated top lip 16u (shoot over it)"""
    X = ML.Model(); W, H = TOWER_W / 2, TOWER_H
    wd, wh = M_['wood'], M_['woodh']
    rbox(X.mesh(wd), (-W, -W, 0), (W, W, H), r=6, k=2, tile=256)
    pic(X.mesh(M_['sign_tt']), (0, -W - 0.8, H - 140), (0, -1, 0), 280, 70)
    pic(X.mesh(M_['shadow']), (0, -W - 0.6, 90), (0, -1, 0), 220, 160)                      # exit slot
    for x in np.linspace(-W + 20, W - 20, 5):
        for y in (-W + 20, W - 20):
            rbox(X.mesh(wh), (x - 20, y - 20, H), (x + 20, y + 20, H + 16), r=2, k=1)
    for y in np.linspace(-W + 60, W - 60, 3):
        for x in (-W + 20, W - 20):
            rbox(X.mesh(wh), (x - 20, y - 20, H), (x + 20, y + 20, H + 16), r=2, k=1)
    # dice tray in front
    rbox(X.mesh(M_['felt']), (-W, -W - 280, 0), (W, -W, 8), r=2, k=1)
    for (a, b) in (((-W, -W - 296, 0), (W, -W - 280, 24)), ((-W - 16, -W - 296, 0), (-W, -W, 24)), ((W, -W - 296, 0), (W + 16, -W, 24))):
        rbox(X.mesh(wh), a, b, r=2, k=1)
    ML.save('dice_tower', X)
    coll('dice_tower', boxes=[((-W, -W, 0), (W, W, H)), ((-W, -W - 280, 0), (W, -W, 8)), ((-W, -W - 296, 0), (W, -W - 280, 24)),
                              ((-W - 16, -W - 296, 0), (-W, -W, 24)), ((W, -W - 296, 0), (W + 16, -W, 24))])


SCREEN_W, SCREEN_H = 560, 720


def dm_screen():
    """three-panel Padmaster screen; panels 16 thick, middle panel along x, wings angled 30 degrees toward -y.
    Players' art faces -y (the table)."""
    X = ML.Model()
    W, H, T = SCREEN_W, SCREEN_H, 16
    panels = []
    for k, ang in ((-1, -30), (0, 0), (1, 30)):
        P = ML.Model()
        rbox(P.mesh(M_['screen_edge']), (-W / 2, 0, 0), (W / 2, T, H), r=2, k=1)
        pic(P.mesh(M_['screen_front']), (0, -0.6, H / 2), (0, -1, 0), W - 16, H - 16)
        pic(P.mesh(M_['screen_back']), (0, T + 0.6, H / 2), (0, 1, 0), W - 16, H - 16)
        if k == 0:
            X.add_model(P, np.eye(3), (0, 0, 0))
        else:
            R = Rz(-ang)        # wings fold toward -y
            hinge = np.array([k * W / 2, 0, 0])
            off = R @ np.array([k * W / 2, 0, 0])
            X.add_model(P, R, hinge + off)
            panels.append((hinge, R))
    ML.save('dm_screen', X)
    bx = [((-W / 2, 0, 0), (W / 2, T, H))]
    for k in (-1, 1):
        a = math.radians(30)
        cx = k * (W / 2 + math.cos(a) * W / 4 * 2) / 1.0
        # approximate each wing by three short boxes along it
        for j in range(3):
            t = (j + 0.5) / 3
            px = k * (W / 2 + math.cos(a) * W * t); py = -math.sin(a) * W * t
            bx.append(((px - 70, py - 30, 0), (px + 70, py + 30, H)))
    coll('dm_screen', boxes=bx)


BOOK_W, BOOK_D, BOOK_T = 360, 270, 32


def book_stack():
    """four rulebooks stacked like steps (each 32u: a barrier-jump step), the top book is the reward perch"""
    X = ML.Model(); boxes = []
    for i in range(4):
        x0 = -BOOK_W / 2 + i * 70; z0 = i * BOOK_T
        mn, mx = (x0, -BOOK_D / 2 + (i % 2) * 14, z0), (x0 + BOOK_W, BOOK_D / 2 + (i % 2) * 14 - 14, z0 + BOOK_T)
        rbox(X.mesh(M_['pages']), (mn[0] + 6, mn[1] + 4, mn[2] + 3), (mx[0] - 2, mx[1] - 4, mx[2] - 3), r=1, k=1, tile=64)
        for zz in (mn[2], mx[2] - 3):
            rbox(X.mesh(M_[f'book_s{i}']), (mn[0], mn[1], zz), (mx[0], mx[1], zz + 3), r=1, k=1, tile=256)
        rbox(X.mesh(M_[f'book_s{i}']), (mn[0], mn[1], mn[2]), (mn[0] + 8, mx[1], mx[2]), r=1, k=1)
        pic(X.mesh(M_[f'book_c{i}']), ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mx[2] + 0.5), (0, 0, 1), BOOK_D - 30, BOOK_D - 30, up=(-1, 0, 0))
        boxes.append((mn, mx))
    ML.save('book_stack', X)
    coll('book_stack', boxes=boxes)


def char_sheet():
    X = ML.Model()
    pic(X.mesh(M_['csheet']), (0, 0, 1), (0, 0, 1), 220, 280, up=(0, 1, 0))
    rbox(X.mesh(M_['paper']), (-112, -142, 0), (112, 142, 0.8), r=0.2, k=1)
    ML.save('char_sheet', X)


def pencil():
    X = ML.Model()
    path = [(-200, 0, 9), (160, 0, 9)]
    tube(X.mesh(M_['pencil_y']), path, 9, nseg=6)
    tube(X.mesh(M_['pencil_tip']), [(160, 0, 9), (200, 0, 9)], [9, 2], nseg=6)
    tube(X.mesh(M_['eraser']), [(-230, 0, 9), (-200, 0, 9)], 9, nseg=6)
    ML.save('pencil', X)


def snack_bowl():
    X = ML.Model()
    revolve(X.mesh(M_['bowl']), [(70, 0), (150, 40), (190, 130), (180, 130), (140, 50), (0, 30)], n=32)
    ellipsoid(X.mesh(M_['chips']), (0, 0, 110), 170, 170, 40, nu=20, nv=6,
              bump=lambda p, t: 1 + 0.1 * math.sin(9 * t) * math.cos(3 * p))
    ML.save('snack_bowl', X)
    coll('snack_bowl', cyls=[(0, 0, 180, 0, 130)])


def dice_tray():
    X = ML.Model()
    rbox(X.mesh(M_['felt']), (-200, -140, 0), (200, 140, 4), r=1, k=1)
    for (a, b) in (((-216, -156, 0), (216, -140, 24)), ((-216, 140, 0), (216, 156, 24)),
                   ((-216, -140, 0), (-200, 140, 24)), ((200, -140, 0), (216, 140, 24))):
        rbox(X.mesh(M_['woodh']), a, b, r=3, k=1)
    ML.save('dice_tray', X)
    coll('dice_tray', boxes=[((-216, -156, 0), (216, -140, 24)), ((-216, 140, 0), (216, 156, 24)),
                             ((-216, -140, 0), (-200, 140, 24)), ((200, -140, 0), (216, 140, 24))])


# ---------------------------------------------------------------- themed jump pads
def pad_skins():
    """dungeon pressure plate (square, rune glowing), terrace rune circle, cork drink coaster on the rail"""
    X = ML.Model(); W, H = 80, 12
    rbox(X.mesh(M_['stone_dark']), (-W, -W, 0), (W, W, H - 4), r=2, k=1, tile=128)
    rbox(X.mesh(M_['stone_light']), (-W + 12, -W + 12, H - 4), (W - 12, W - 12, H), r=2, k=1, tile=128)
    pic(X.mesh(M_['rune']), (0, 0, H + 0.5), (0, 0, 1), 120, 120, up=(1, 0, 0))
    pic(X.mesh(M_['sticker']), (0, 0, H + 1.0), (0, 0, 1), 70, 70, up=(1, 0, 0))
    ML.save('pad_plate', X); PAD_SKINS['pad_plate'] = dict(w=2 * W, d=2 * W, h=H)
    X = ML.Model(); R, H = 84, 8
    revolve(X.mesh(M_['stone_light']), [(R, 0), (R, H), (0, H)], n=24, inward=True)
    pic(X.mesh(M_['rune']), (0, 0, H + 0.5), (0, 0, 1), 160, 160, up=(1, 0, 0))
    pic(X.mesh(M_['sticker']), (0, 0, H + 1.0), (0, 0, 1), 70, 70, up=(1, 0, 0))
    ML.save('pad_rune', X); PAD_SKINS['pad_rune'] = dict(w=2 * R * 0.72, d=2 * R * 0.72, h=H)
    X = ML.Model(); R, H = 80, 10
    revolve(X.mesh(M_['cork']), [(R, 0), (R, H), (0, H)], n=24, inward=True)
    pic(X.mesh(M_['sticker']), (0, 0, H + 0.6), (0, 0, 1), 96, 96, up=(1, 0, 0))
    ML.save('pad_coaster', X); PAD_SKINS['pad_coaster'] = dict(w=2 * R * 0.72, d=2 * R * 0.72, h=H)


def pad_skin(name, pad, land):
    s = PAD_SKINS[name]
    angle = round(math.degrees(math.atan2(land[1] - pad[1], land[0] - pad[0])))
    return dict(place=ML.PLACE[name], h=s['h'], angle=angle,
                boxes=[((-s['w'] / 2, -s['d'] / 2, 0), (s['w'] / 2, s['d'] / 2, s['h']))])
