"""Round-2 dressing MD3s for wop_padxmas3: landmark toys (nutcracker, snow globe, rocking horse, teddy, jack-in-the-box,
Christmas pyramid, toy sleigh, drum), the candy village (lollipops, gumdrop trees, icing fence), floor life (fairy-light
strings, tinsel, chocolate coins, spilled bauble box, stocking, fallen needles), a mouse hole in the skirting board and
extra hanging ornaments for the canopy. Original geometry; origin = bottom centre unless noted."""
import math, random
import numpy as np
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, grid_normals
from woplib import models as ML
import xm3_art as A
import xm3_models as XM

M = A.M
Model = ML.Model
rot_y, rot_x = XM.rot_y, XM.rot_x


def put(X, other, R=np.eye(3), t=(0, 0, 0)):
    for sh, mm in other.m.items(): X.mesh(sh).add(mm, R=R, t=t)


# ------------------------------------------------------------------------------------------------ extra materials
def materials(TX):
    from woplib import texlib as TL
    m = lambda key, arr, kind='lm', **o: M.__setitem__(key, TX.material(key, arr, kind, **o))
    m('nut_red', TL.solid((176, 22, 34), 2, 401), 'lms', v=0.2, shade=60)
    m('nut_blue', TL.solid((30, 50, 130), 2, 402), 'lms', v=0.2, shade=60)
    m('nut_black', TL.solid((22, 22, 26), 2, 403), 'lms', v=0.3, shade=60)
    m('nut_skin', TL.solid((236, 200, 170), 2, 404), shade=60)
    m('nut_face', nut_face(), shade=60)
    m('fluff', TL.solid((236, 230, 220), 10, 405), shade=80)
    m('teddy', TL.fabric((160, 110, 60), weave=128), shade=80)
    m('teddy_l', TL.fabric((214, 180, 130), weave=128), shade=80)
    m('dapple', dapple(), shade=70)
    m('globe_snow', TL.solid((246, 248, 252), 4, 406), shade=80)
    flecks = np.zeros((256, 256, 3), np.float32)
    rng = np.random.default_rng(407)
    for _ in range(160):
        x, y = rng.integers(2, 254, 2); r = rng.integers(1, 3)
        flecks[y - r:y + r, x - r:x + r] = 230
    m('snowfall', flecks, 'add', tcmod='scroll 0.01 0.18')
    m('lolly_swirl', swirl(), 'lms', v=0.3, shade=70)
    m('lolly_swirl2', swirl(((40, 160, 220), (250, 240, 240), (250, 200, 40))), 'lms', v=0.3, shade=70)
    m('coin', coin(), 'lms', v=0.5, shade=70)
    m('tinsel_gold', TL.stripes((240, 200, 90), (150, 100, 30), n_stripes=24, vertical=True), 'lms', v=0.7, shade=80, two=True)
    m('tinsel_silver', TL.stripes((230, 234, 240), (120, 126, 140), n_stripes=24, vertical=True), 'lms', v=0.7, shade=80, two=True)
    m('orange', TL.dots((236, 128, 30), (210, 100, 20), n_dots=14, r=0.08), shade=80)
    m('stocking', stocking_knit(), shade=70)
    m('mousehole', TL.solid((14, 10, 8), 2, 408), 'vl')
    m('mousewin', TL.solid((255, 210, 120), 2, 409), 'glow')
    m('candle', TL.solid((246, 236, 210), 2, 410), shade=70)
    m('flame', flame(), 'glow', wave='wave noise 0.85 0.15 0 6')
    # mover shaders (model2 on func_rotating is not lightmapped): lightingDiffuse variants of existing images
    for k, img in (('wood_dyn', 'wood_m'), ('paint_red_dyn', 'paint_red_m'), ('paint_green_dyn', 'paint_green_m'),
                   ('brass_dyn', 'brass_m'), ('white_dyn', 'white_m'), ('candle_dyn', 'candle_m')):
        M[k] = ML.S(img, 'dyn')
    M['flame_dyn'] = ML.S('flame_m', 'glow', tag='mv')
    nd, na = XM.A.needles(128, 64)
    m('fallen', nd, 'alpha', alpha=na)


def nut_face(n=128):
    a = ML.fill(n, (236, 200, 170), 2, 420)
    from PIL import ImageDraw
    im = ML.img(a); d = ImageDraw.Draw(im)
    for cx in (44, 84):
        d.ellipse((cx - 8, 40, cx + 8, 56), fill=(250, 250, 250)); d.ellipse((cx - 4, 44, cx + 4, 54), fill=(30, 40, 90))
        d.line((cx - 12, 34, cx + 10, 30 if cx < 64 else 38), fill=(40, 30, 20), width=4)
    d.ellipse((54, 58, 74, 78), fill=(220, 120, 110))
    d.rectangle((30, 84, 98, 96), fill=(250, 250, 250))
    for x in range(34, 98, 8): d.line((x, 84, x, 96), fill=(200, 200, 200))
    d.arc((40, 70, 88, 104), 200, 340, fill=(140, 30, 30), width=3)
    return np.asarray(im, np.float32)


def dapple(n=256):
    a = ML.fill(n, (238, 232, 220), 3, 430)
    x, y = ML.xy(n)
    sp = ML.noise(n, 6, 431) > 0.9
    return np.where(sp[..., None], ML.C((150, 140, 130)), a)


def swirl(cols=((220, 30, 40), (250, 240, 240), (40, 170, 80)), n=256):
    x, y = ML.xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    k = ((a / (2 * math.pi) * 3 + r * 9) % 1)
    out = np.zeros((n, n, 3), np.float32)
    for i, c in enumerate(cols):
        out = np.where(((k * len(cols)).astype(int) == i)[..., None], ML.C(c), out)
    return out


def coin(n=128):
    x, y = ML.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    a = ML.fill(n, (226, 180, 60), 2, 440)
    ring = (np.abs(r - 0.42) < 0.03) | (np.abs(r - 0.2) < 0.02)
    return np.where(ring[..., None], a * 0.75, a)


def stocking_knit(n=256):
    x, y = ML.xy(n)
    band = ((y * 6) % 1) < 0.18
    a = np.where(band[..., None], ML.C((246, 244, 236)), ML.C((190, 24, 34)))
    knit = 0.88 + 0.12 * np.sin((x * 32 + np.abs(((y * 32) % 1) - 0.5)) * math.pi * 2)
    return a * knit[..., None]


def flame(n=64):
    x, y = ML.xy(n)
    r = np.hypot((x - 0.5) * 2.2, (y - 0.62) * 1.3)
    a = np.clip(1 - r, 0, 1)[..., None]
    return np.clip(a * ML.C((255, 200, 90)) * 1.5, 0, 255)


# ------------------------------------------------------------------------------------------------ landmark toys
def nutcracker(h=760):
    X = Model()
    s = h / 760
    red, blue, blk, gold = X.mesh(M['nut_red']), X.mesh(M['nut_blue']), X.mesh(M['nut_black']), X.mesh(M['brass'])
    revolve(X.mesh(M['wood']), [(150 * s, 0), (150 * s, 30 * s), (130 * s, 40 * s), (0.1, 40 * s)], n=24)
    for sx in (-1, 1):                                   # boots + legs
        rbox(blk, (sx * 52 * s - 34 * s, -40 * s, 40 * s), (sx * 52 * s + 34 * s, 50 * s, 120 * s), r=10 * s, k=2)
        revolve(blue, [(32 * s, 120 * s), (34 * s, 300 * s), (0.1, 300 * s)], n=12, cx=sx * 50 * s)
    revolve(red, [(96 * s, 290 * s), (104 * s, 330 * s), (92 * s, 520 * s), (70 * s, 540 * s), (0.1, 540 * s)], n=20)
    revolve(blk, [(106 * s, 330 * s), (106 * s, 356 * s)], n=20)          # belt
    for z in (380, 420, 460, 500):                       # gold buttons + braid
        sphere(gold, (0, -96 * s, z * s), 9 * s, nu=8, nv=5)
    for sx in (-1, 1):                                   # arms
        tube(red, [(sx * 96 * s, 0, 520 * s), (sx * 130 * s, -20 * s, 420 * s), (sx * 120 * s, -60 * s, 340 * s)], 30 * s, nseg=10)
        ellipsoid(X.mesh(M['white']), (sx * 120 * s, -64 * s, 322 * s), 24 * s, 24 * s, 22 * s, nu=8, nv=5)
        ellipsoid(gold, (sx * 104 * s, 0, 540 * s), 40 * s, 34 * s, 14 * s, nu=10, nv=4)   # epaulettes
    revolve(X.mesh(M['nut_skin']), [(30 * s, 540 * s), (30 * s, 560 * s)], n=12)
    hd = Mesh(); ellipsoid(hd, (0, 0, 0), 64 * s, 66 * s, 74 * s, nu=16, nv=10)
    X.mesh(M['nut_face']).add(hd, R=rot_z(-math.pi / 2) @ np.eye(3), t=(0, 0, 620 * s))
    ellipsoid(X.mesh(M['fluff']), (0, -40 * s, 584 * s), 54 * s, 34 * s, 40 * s, nu=10, nv=6)        # beard
    revolve(blk, [(72 * s, 670 * s), (76 * s, 760 * s * 0.99), (0.1, 760 * s * 0.99)], n=20)    # shako
    revolve(gold, [(77 * s, 676 * s), (77 * s, 690 * s)], n=20)
    ellipsoid(X.mesh(M['nut_red']), (0, -74 * s, 740 * s), 14 * s, 8 * s, 24 * s, nu=8, nv=5)
    return X


def snow_globe(r=260, base_h=110):
    X = Model()
    revolve(X.mesh(M['wood']), [(r + 60, 0), (r + 60, 20), (r + 40, base_h * 0.6), (r + 10, base_h), (0.1, base_h)], n=32)
    revolve(X.mesh(M['brass']), [(r + 44, base_h * 0.5), (r + 44, base_h * 0.62)], n=32)
    c = base_h + r * 0.75
    # scene inside: snowy mound, a fir, a tiny house with a lit window
    revolve(X.mesh(M['globe_snow']), [(r * 0.95, base_h + 2), (r * 0.7, base_h + 30), (0.1, base_h + 40)], n=24)
    revolve(X.mesh(M['needle_mass']), [(70, base_h + 30), (60, base_h + 80), (45, base_h + 90), (40, base_h + 140), (25, base_h + 150),
                                       (0.1, base_h + 220)], n=12, cx=-60, cy=40)
    rbox(X.mesh(M['ginger']), (30, -60, base_h + 32), (130, 20, base_h + 110), r=2, k=1, tile=64)
    prism(X.mesh(M['icing']), [(20, -70), (140, -70), (140, 30), (20, 30)], base_h + 110, base_h + 118)
    rbox(X.mesh(M['mousewin']), (60, -62, base_h + 60), (90, -60, base_h + 90), r=0, k=1, tile=32, faces='s')
    # falling snow column + glass dome (most of a sphere)
    revolve(X.mesh(M['snowfall']), [(r * 0.8, base_h + 30), (r * 0.8, c + r * 0.55)], n=24, u_tiles=4, vlen=180)
    prof = [(r * math.cos(e), c + r * math.sin(e)) for e in np.linspace(-0.85, math.pi / 2, 14)]
    prof[-1] = (0.1, prof[-1][1])
    revolve(X.mesh(M['glass']), prof, n=32)
    return X


def rocking_horse(L=640):
    X = Model()
    s = L / 640
    wd = X.mesh(M['wood']); dp = X.mesh(M['dapple']); blk = X.mesh(M['nut_black'])
    for sy in (-1, 1):                                    # rockers: arcs in the xz plane
        pts = [(x, sy * 90 * s, 24 * s + 70 * s * (x / (320 * s)) ** 2) for x in np.linspace(-320 * s, 320 * s, 16)]
        tube(wd, pts, 14 * s, nseg=8, ry=6 * s)
    for x in (-150, 150):
        for sy in (-1, 1):
            tube(wd, [(x * s, sy * 90 * s, 34 * s), (x * s * 0.8, sy * 40 * s, 230 * s)], 12 * s, nseg=8)
    rbox(wd, (-200 * s, -100 * s, 40 * s), (200 * s, 100 * s, 60 * s), r=4, k=2, tile=128)   # cross bars hidden-ish
    ellipsoid(dp, (0, 0, 290 * s), 170 * s, 70 * s, 70 * s, nu=16, nv=10)           # body
    tube(dp, [(130 * s, 0, 320 * s), (200 * s, 0, 420 * s), (230 * s, 0, 470 * s)], [44 * s, 36 * s, 30 * s], nseg=12)   # neck
    hd = Mesh(); ellipsoid(hd, (0, 0, 0), 70 * s, 34 * s, 36 * s, nu=12, nv=8)
    dp.add(hd, R=rot_y(0.5), t=(270 * s, 0, 470 * s))
    for sy in (-1, 1):
        ellipsoid(dp, (236 * s, sy * 18 * s, 520 * s), 10 * s, 6 * s, 22 * s, nu=6, nv=4)          # ears
        sphere(blk, (290 * s, sy * 30 * s, 490 * s), 7 * s, nu=6, nv=4)                      # eyes
    for k in range(9):                                    # mane
        t = k / 8
        p = np.array([130 * s + 100 * s * t, 0, 350 * s + 140 * s * t])
        tube(X.mesh(M['nut_black']), [p, p + [-30 * s, 0, -60 * s]], 10 * s, nseg=6)
    tube(X.mesh(M['nut_black']), [(-160 * s, 0, 300 * s), (-220 * s, 0, 260 * s), (-240 * s, 0, 160 * s)], [16 * s, 14 * s, 6 * s], nseg=8)   # tail
    rbox(X.mesh(M['nut_red']), (-60 * s, -74 * s, 320 * s), (60 * s, 74 * s, 366 * s), r=10 * s, k=2, tile=128)  # saddle
    for x in (-110, 110):                                 # legs to the stand
        for sy in (-1, 1):
            tube(dp, [(x * s, sy * 40 * s, 250 * s), (x * s * 1.1, sy * 50 * s, 240 * s)], 18 * s, nseg=8)
    return X


def teddy(h=440):
    X = Model()
    s = h / 440
    f, l = X.mesh(M['teddy']), X.mesh(M['teddy_l'])
    ellipsoid(f, (0, 0, 130 * s), 120 * s, 105 * s, 130 * s, nu=16, nv=10, flat_bottom=-125 * s)   # body
    ellipsoid(l, (0, -60 * s, 130 * s), 74 * s, 50 * s, 90 * s, nu=12, nv=8)                    # tummy
    for sx in (-1, 1):
        tube(f, [(sx * 70 * s, -40 * s, 40 * s), (sx * 90 * s, -150 * s, 40 * s)], 46 * s, nseg=12)             # legs
        ellipsoid(l, (sx * 90 * s, -196 * s, 44 * s), 34 * s, 8 * s, 40 * s, nu=10, nv=6)                       # paws
        tube(f, [(sx * 100 * s, 0, 210 * s), (sx * 150 * s, -60 * s, 120 * s)], 36 * s, nseg=10)                 # arms
        sphere(f, (sx * 70 * s, 0, 400 * s), 34 * s, nu=10, nv=6)                                                # ears
        sphere(l, (sx * 70 * s, -10 * s, 400 * s), 20 * s, nu=8, nv=5)
    sphere(f, (0, 0, 320 * s), 96 * s, nu=16, nv=10)                                                          # head
    ellipsoid(l, (0, -80 * s, 300 * s), 44 * s, 36 * s, 32 * s, nu=10, nv=6)                                  # muzzle
    sphere(X.mesh(M['nut_black']), (0, -116 * s, 314 * s), 12 * s, nu=8, nv=5)
    for sx in (-1, 1): sphere(X.mesh(M['nut_black']), (sx * 36 * s, -84 * s, 350 * s), 9 * s, nu=8, nv=5)
    rm = X.mesh(M['ribbon_red'])                                                                              # bow tie
    for sx in (-1, 1):
        ellipsoid(rm, (sx * 34 * s, -90 * s, 240 * s), 30 * s, 10 * s, 20 * s, nu=8, nv=5)
    sphere(rm, (0, -96 * s, 240 * s), 12 * s, nu=8, nv=5)
    return X


def jack_in_box(s=240):
    """toy box with the lid flung open, a spring and a clown head that bobs (deform on its surfaces)"""
    X = Model()
    h = s / 2
    for f, pat in zip('nsew', ('abc_a', 'abc_b', 'abc_c', 'abc_m')):
        rbox(X.mesh(M[pat]), (-h, -h, 0), (h, h, s), r=6, k=2, tile=s, faces=f)
    rbox(X.mesh(M['cardboard_in']), (-h + 10, -h + 10, s - 12), (h - 10, h - 10, s - 10), r=0, k=1, tile=s, faces='t')
    lid = Mesh(); rbox(lid, (0, -h, 0), (s, h, 14), r=4, k=2, tile=s, faces='tbnsew')
    X.mesh(M['abc_x']).add(lid, R=rot_y(-1.9), t=(-h, 0, s))
    sp = M['slinky']
    pts = [(10 * math.cos(t * 9) * 4, 10 * math.sin(t * 9) * 4, s - 10 + t * 140 / 6.28 * 1.0) for t in np.linspace(0, 6.28, 90)]
    tube(X.mesh(sp), pts, 4, nseg=5)
    hd = s + 150
    sphere(X.mesh(M['nut_skin']), (0, 0, hd), 60, nu=14, nv=9)
    sphere(X.mesh(M['nut_red']), (0, -58, hd), 13, nu=8, nv=5)
    for sx in (-1, 1): sphere(X.mesh(M['nut_black']), (sx * 22, -50, hd + 18), 8, nu=6, nv=4)
    revolve(X.mesh(M['nut_blue']), [(56, hd + 40), (20, hd + 120), (0.1, hd + 130)], n=14)
    sphere(X.mesh(M['fluff']), (0, 0, hd + 132), 16, nu=8, nv=5)
    ellipsoid(X.mesh(M['fluff']), (0, 0, hd - 58), 80, 80, 18, nu=14, nv=5)           # ruff
    return X


def drum(r=200, h=220):
    X = Model()
    revolve(X.mesh(M['nut_red']), [(r, 16), (r, h - 16)], n=32, u_tiles=1)
    for z in (0, h - 16):
        revolve(X.mesh(M['brass']), [(r + 8, z), (r + 8, z + 16), (r, z + 16), (r, z)], n=32)
    disc(X.mesh(M['skin']), r, h, n=32)
    for k in range(10):                                  # zigzag cords
        a0, a1 = 2 * math.pi * k / 10, 2 * math.pi * (k + 0.5) / 10
        tube(X.mesh(M['white']), [((r + 2) * math.cos(a0), (r + 2) * math.sin(a0), 18), ((r + 2) * math.cos(a1), (r + 2) * math.sin(a1), h - 18),
                                  ((r + 2) * math.cos(a0 + 2 * math.pi / 10), (r + 2) * math.sin(a0 + 2 * math.pi / 10), 18)], 3, nseg=4)
    for sx in (-1, 1):                                   # drumsticks lying on the skin
        tube(X.mesh(M['wood']), [(sx * 30 - 120, sx * 40, h + 7), (sx * 30 + 120, sx * 40 + sx * 30, h + 7)], 7, nseg=6)
        sphere(X.mesh(M['white']), (sx * 30 + 126, sx * 40 + sx * 32, h + 8), 12, nu=8, nv=5)
    return X


def pyramid_base(r=200, h=470):
    """Christmas pyramid frame: round base with candles, corner posts, an axle up to the fan (static part)"""
    X = Model()
    revolve(X.mesh(M['wood']), [(r + 30, 0), (r + 30, 24), (0.1, 24)], n=24)
    for k in range(6):
        a = 2 * math.pi * k / 6
        x, y = (r + 10) * math.cos(a), (r + 10) * math.sin(a)
        tube(X.mesh(M['paint_green']), [(x, y, 24), (x * 0.8, y * 0.8, h - 40)], 10, nseg=8)
        tube(X.mesh(M['candle']), [(x, y, 24), (x, y, 120)], 9, nseg=8)
        q = XM.Mesh(); q.poly([(x - 8, y, 120), (x + 8, y, 120), (x + 8, y, 150), (x - 8, y, 150)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        X.mesh(M['flame']).add(q)
        q2 = XM.Mesh(); q2.poly([(x, y - 8, 120), (x, y + 8, 120), (x, y + 8, 150), (x, y - 8, 150)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        X.mesh(M['flame']).add(q2)
    tube(X.mesh(M['brass']), [(0, 0, 24), (0, 0, h)], 8, nseg=8)
    return X


def pyramid_rotor(r=180, h=470):
    """the turning part (func_rotating model2, lightingDiffuse shaders, origin at the axle bottom): two tiers of
    figures (angels, trees, reindeer), the fan of wooden blades at the top"""
    X = Model()
    for z, rr in ((60, r), (250, r * 0.75)):
        revolve(X.mesh(M['wood_dyn']), [(rr, z), (rr, z + 12), (0.1, z + 12)], n=24)
        for k in range(8):
            a = 2 * math.pi * k / 8
            x, y = rr * 0.78 * math.cos(a), rr * 0.78 * math.sin(a)
            if k % 2:
                revolve(X.mesh(M['paint_green_dyn']), [(28, z + 12), (14, z + 60), (20, z + 60), (6, z + 100), (0.1, z + 110)], n=8, cx=x, cy=y)
            else:
                revolve(X.mesh(M['white_dyn']), [(20, z + 12), (14, z + 70), (0.1, z + 74)], n=8, cx=x, cy=y)
                sphere(X.mesh(M['white_dyn']), (x, y, z + 86), 12, nu=6, nv=4)
                for sg in (-1, 1):
                    q = XM.Mesh()
                    q.poly([(x, y, z + 60), (x + sg * 30 * math.cos(a + 1.57), y + sg * 30 * math.sin(a + 1.57), z + 80),
                            (x + sg * 24 * math.cos(a + 1.57), y + sg * 24 * math.sin(a + 1.57), z + 50)], (math.cos(a), math.sin(a), 0),
                           [(0, 0), (1, 0), (1, 1)])
                    X.mesh(M['brass_dyn']).add(q)
    for k in range(8):                                    # fan blades
        a = 2 * math.pi * k / 8
        c, sn = math.cos(a), math.sin(a)
        p = [(30 * c, 30 * sn, h - 6), (r * 1.1 * c - 30 * sn, r * 1.1 * sn + 30 * c, h + 10), (r * 1.15 * c + 30 * sn, r * 1.15 * sn - 30 * c, h - 10),
             (30 * c, 30 * sn, h - 20)]
        q = XM.Mesh(); q.poly(p, (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
        X.mesh(M['wood_dyn']).add(q)
        q = XM.Mesh(); q.poly(p[::-1], (0, 0, -1), [(0, 1), (1, 1), (1, 0), (0, 0)])
        X.mesh(M['wood_dyn']).add(q)
    sphere(X.mesh(M['brass_dyn']), (0, 0, h), 20, nu=8, nv=5)
    return X


def sleigh(L=560, W=300):
    X = Model()
    red, gold = X.mesh(M['paint_red']), X.mesh(M['brass'])
    for sy in (-1, 1):                                    # runners with a curl at the front
        pts = [(-L / 2, sy * W * 0.42, 8), (L / 2 - 60, sy * W * 0.42, 8)]
        for a in np.linspace(0, math.pi * 1.3, 10)[1:]:
            pts.append((L / 2 - 60 + 60 * math.sin(a), sy * W * 0.42, 68 - 60 * math.cos(a)))
        tube(gold, pts, 9, nseg=8)
        for x in (-L * 0.3, L * 0.2):
            tube(gold, [(x, sy * W * 0.42, 8), (x, sy * W * 0.4, 90)], 7, nseg=6)
    rbox(red, (-L / 2 + 20, -W / 2, 90), (L / 2 - 120, W / 2, 130), r=10, k=2, tile=256)               # floor
    rbox(red, (-L / 2 + 20, -W / 2, 130), (-L / 2 + 70, W / 2, 330), r=16, k=3, tile=256)              # back
    rbox(red, (-L / 2 + 20, -W / 2, 130), (L / 2 - 120, -W / 2 + 18, 220), r=8, k=2, tile=256)
    rbox(red, (-L / 2 + 20, W / 2 - 18, 130), (L / 2 - 120, W / 2, 220), r=8, k=2, tile=256)
    rbox(red, (L / 2 - 160, -W / 2, 130), (L / 2 - 120, W / 2, 260), r=12, k=2, tile=256)               # front dash
    XM.rbox(X.mesh(M['felt']), (-L / 2 + 70, -W / 2 + 20, 130), (-L / 2 + 190, W / 2 - 20, 170), r=12, k=3, tile=128)
    sack = Mesh(); ellipsoid(sack, (0, 0, 0), 90, 80, 110, nu=12, nv=8, flat_bottom=-80)
    X.mesh(M['cardboard']).add(sack, t=(-L / 2 + 140, 0, 250))
    for (x, y, w, pat) in ((10, -60, 90, 'gold'), (60, 50, 80, 'green'), (-60, 70, 70, 'purple')):
        put(X, XM.gift(w, w, w, pat), t=(x, y, 130))
    return X


# ------------------------------------------------------------------------------------------------ candy village
def lollipop(h=420, r=110, swirl_key='lolly_swirl'):
    X = Model()
    tube(X.mesh(M['white']), [(0, 0, 0), (0, 0, h - r)], 12, nseg=8)
    revolve(X.mesh(M['white']), [(40, 0), (12, 14)], n=12)
    d = Mesh()
    disc(d, r, 16, n=32, uvscale=2 * r); disc(d, r, -16, up=False, n=32, uvscale=2 * r)
    revolve(d, [(r, -16), (r + 4, 0), (r, 16)], n=32, u_tiles=8)
    X.mesh(M[swirl_key]).add(d, R=rot_x(math.pi / 2), t=(0, 0, h - r))
    rm = X.mesh(M['ribbon_red'])
    ellipsoid(rm, (0, -14, h - 2 * r - 6), 24, 10, 14, nu=8, nv=4)
    return X


def gumdrop_tree(h=380):
    X = Model()
    tube(X.mesh(M['cookie_side']), [(0, 0, 0), (0, 0, 80)], 18, nseg=8)
    revolve(X.mesh(M['cookie_side']), [(60, 0), (60, 14), (0.1, 14)], n=12)
    cols = ['red', 'green', 'yellow', 'purple', 'orange']
    k = 0
    for i, z in enumerate(np.linspace(80, h - 40, 6)):
        rr = 110 * (1 - (z - 80) / (h - 40)) + 10
        n = max(1, int(2 * math.pi * rr / 46))
        for j in range(n):
            a = 2 * math.pi * (j + 0.5 * (i % 2)) / n
            g = XM.gumdrop(22, 36, cols[k % 5]); k += 1
            put(X, g, t=(rr * math.cos(a), rr * math.sin(a), z))
    put(X, XM.gumdrop(26, 44, 'red'), t=(0, 0, h - 44))
    return X


def fence(L=320, h=64):
    X = Model()
    ic = X.mesh(M['icing'])
    for x in np.arange(-L / 2 + 8, L / 2, 40):
        rbox(ic, (x - 7, -7, 0), (x + 7, 7, h), r=3, k=2, tile=64)
        revolve(ic, [(9, h), (5, h + 10), (0.1, h + 12)], n=8, cx=x)
    for z in (h * 0.35, h * 0.75):
        rbox(X.mesh(M['candy']), (-L / 2, -4, z - 5), (L / 2, 4, z + 5), r=2, k=1, tile=64)
    return X


# ------------------------------------------------------------------------------------------------ floor life
def floor_lights(pts, nb=None, seed=0):
    """fairy-light string lying across the floor (world space path, visual only)"""
    X = Model()
    rr = random.Random(seed)
    pts = np.asarray(pts, float)
    tube(X.mesh(M['cable']), pts, 4, nseg=5, caps=(True, True))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    for s in np.arange(30, L[-1], 70):
        i = max(0, min(np.searchsorted(L, s) - 1, len(pts) - 2))
        p = pts[i] + (pts[i + 1] - pts[i]) * (s - L[i]) / max(1, L[i + 1] - L[i])
        col = 'rgbyw'[rr.randint(0, 4)]
        ellipsoid(X.mesh(M['bulb_' + col]), p + [0, 0, 8], 7, 7, 10, nu=8, nv=5)
        tube(X.mesh(M['cable']), [p + [0, 0, 1], p + [0, 0, 3]], 6, nseg=6)
    return X


def tinsel(pts, gold=True):
    X = Model()
    tube(X.mesh(M['tinsel_gold' if gold else 'tinsel_silver']), np.asarray(pts, float), 10, nseg=6, utiles=3, vlen=40)
    return X


def coins(n, r_spread, seed):
    X = Model()
    rr = random.Random(seed)
    for k in range(n):
        x, y = rr.uniform(-r_spread, r_spread), rr.uniform(-r_spread, r_spread)
        cr = rr.uniform(26, 36)
        revolve(X.mesh(M['coin']), [(cr, 0.5), (cr, 6)], n=16, cx=x, cy=y)
        disc(X.mesh(M['coin']), cr, 6, n=16, cx=x, cy=y, uvscale=2 * cr)
    return X


def bauble_box(w=420, d=300, h=110):
    X = Model()
    cb = X.mesh(M['cardboard']); ci = X.mesh(M['cardboard_in'])
    hw, hd = w / 2, d / 2
    for (mn, mx) in (((-hw, -hd, 0), (hw, -hd + 8, h)), ((-hw, hd - 8, 0), (hw, hd, h)), ((-hw, -hd, 0), (-hw + 8, hd, h)), ((hw - 8, -hd, 0), (hw, hd, h))):
        rbox(cb, mn, mx, r=1, k=1, tile=128)
    rbox(ci, (-hw + 8, -hd + 8, 0), (hw - 8, hd - 8, 6), r=0, k=1, tile=128, faces='t')
    for x in np.linspace(-hw, hw, 5)[1:-1]: rbox(ci, (x - 3, -hd, 6), (x + 3, hd, h * 0.7), r=0, k=1, tile=64)
    rbox(ci, (-hw, -3, 6), (hw, 3, h * 0.7), r=0, k=1, tile=64)
    lid = Mesh(); rbox(lid, (0, -hd, 0), (w * 0.0 + d * 0.9, hd, 6), r=1, k=1, tile=128)
    cb.add(lid, R=rot_y(-0.25) @ rot_z(math.pi), t=(-hw - 2, 0, 4))
    cols = list(A.BAUBLES)
    k = 0
    for i, x in enumerate(np.linspace(-hw, hw, 5)[:-1]):
        for j, y in enumerate((-hd, 0)):
            if (i, j) in ((3, 0),): continue
            cx, cy = x + w / 8, y + d / 4
            sphere(X.mesh(M['bauble_' + cols[k % 6]]), (cx, cy, 44), 40, nu=14, nv=8); k += 1
    return X


def stocking_spill():
    X = Model()
    st = X.mesh(M['stocking'])
    pts = [(-240, 0, 68), (-60, 0, 64), (60, 0, 62), (130, 30, 60), (160, 90, 58)]
    tube(st, pts, [64, 60, 58, 54, 48], nseg=12, ry=[44, 42, 40, 38, 36], caps=(False, True), vlen=200)
    cuff = Mesh(); revolve(cuff, [(72, -30), (78, 0), (72, 30), (60, 30)], n=16, u_tiles=4)
    X.mesh(M['fluff']).add(cuff, R=rot_y(math.pi / 2), t=(-250, 0, 82))
    for (x, y, r) in ((-340, 40, 40), (-400, -60, 36)):
        sphere(X.mesh(M['orange']), (x, y, r + 1), r, nu=14, nv=8)
    put(X, coins(7, 70, 5), t=(-420, 60, 0))
    put(X, XM.candy_cane_lying(160, 9, 26), R=rot_z(0.6), t=(-330, -150, 1))
    return X


def needle_scatter(n, spread, seed):
    """fallen pine needles on the carpet: tiny flat alpha cards (visual only)"""
    X = Model()
    rr = random.Random(seed)
    for _ in range(n):
        x, y, a = rr.uniform(-spread, spread), rr.uniform(-spread, spread), rr.uniform(0, 6.28)
        d = np.array([math.cos(a), math.sin(a), 0]); sd = np.array([-math.sin(a), math.cos(a), 0])
        L, w = rr.uniform(60, 110), rr.uniform(26, 40)
        p = np.array([x, y, 0.8])
        X.mesh(M['fallen']).poly([p - sd * w / 2, p + d * L - sd * w / 2, p + d * L + sd * w / 2, p + sd * w / 2], (0, 0, 1),
                                 [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def mouse_hole(w=110, h=140):
    """arched mouse hole in the skirting board, a tiny door ajar with a lit gap and a doormat; origin = bottom centre
    of the hole on the board face, facing -y (model -y = into the room)"""
    X = Model()
    arch = [(-w / 2, 0)] + [(w / 2 * math.cos(t), h - w / 2 + w / 2 * math.sin(t)) for t in np.linspace(math.pi, 0, 12)] + [(w / 2, 0)]
    q = Mesh()
    pts = [(x, -0.6, z) for (x, z) in arch]
    c = (0, -0.6, h * 0.45)
    for a, b in zip(pts[:-1], pts[1:]):
        q.poly([c, b, a], (0, -1, 0), [(0.5, 0.5), (0, 0), (1, 0)])
    X.mesh(M['mousehole']).add(q)
    for (a, b) in zip(arch[:-1], arch[1:]):                # wooden frame round the arch
        tube(X.mesh(M['wood']), [(a[0], -3, a[1]), (b[0], -3, b[1])], 5, nseg=6)
    dr = Mesh(); rbox(dr, (0, -6, 0), (w * 0.8, 0, h * 0.85), r=2, k=1, tile=64)
    X.mesh(M['paint_green']).add(dr, R=rot_z(-0.9), t=(w / 2 - 4, -2, 2))
    sphere(X.mesh(M['brass']), (w / 2 + 34, -40, h * 0.45), 4, nu=6, nv=4)
    rbox(X.mesh(M['mousewin']), (-w / 2 + 10, -1.2, 2), (-w / 2 + 16, -1.0, h - w / 2), r=0, k=1, tile=32, faces='s')
    rbox(X.mesh(M['felt']), (-60, -70, 0.5), (60, -10, 3), r=1, k=1, tile=64, faces='t')
    return X


# ------------------------------------------------------------------------------------------------ canopy ornaments
def ornament_mix(X, top, kind, rr):
    """more ornaments to hang from boughs (world/model coords of the hanging point): icicles, candy canes, stars,
    gingerbread men, pinecones, little bells"""
    top = np.asarray(top, float)
    L = rr.uniform(40, 120)
    tube(X.mesh(M['thread']), [top, top + [0, 0, -L]], 1.2, nseg=4, caps=(False, False))
    p = top + [0, 0, -L]
    if kind == 'icicle':
        m = Mesh(); revolve(m, [(0.1, 0), (16, -4), (12, -60), (6, -130), (0.1, -170)], n=8)
        X.mesh(M['mirror']).add(m, t=p)
    elif kind == 'cane':
        cc = XM.candy_cane_lying(180, 9, 30)
        put(X, cc, R=rot_y(math.pi / 2) @ rot_z(0), t=p + [0, 0, -90])
    elif kind == 'star':
        pts = A.star_pts(0, 0, 60, 26)
        m = Mesh(); prism(m, [(x, -y) for x, y in pts][::-1], -6, 6, tile=128)
        X.mesh(M['brass']).add(m, R=rot_x(math.pi / 2) @ rot_z(rr.uniform(0, 3)), t=p + [0, 0, -60])
    elif kind == 'gingerman':
        g = XM.ginger_man(150, 10)
        put(X, g, R=rot_x(math.pi / 2) @ rot_z(math.pi), t=p + [0, 0, -150 * 0.0])
    elif kind == 'pinecone':
        pc = XM.pinecone(110, 40)
        put(X, pc, R=rot_x(math.pi), t=p)
    elif kind == 'bell':
        m = Mesh(); revolve(m, [(0.1, 0), (14, -6), (22, -40), (34, -64), (36, -70), (0.1, -66)], n=14)
        X.mesh(M['brass']).add(m, t=p)
        sphere(X.mesh(M['brass']), p + [0, 0, -72], 8, nu=6, nv=4)
