"""Deluxe pass for wop_padbakery: movers, steam, neon, bunting, a sprinkle tube and more detail on top of the base layout.

make() builds the models (call after bk_models.make() / bk_props.make()); place(B) adds them to the map through the
builder module B (build_bakery). Nothing here changes the base routes or weapon spots.

  Cupcake conveyor   a ring rail hung from the ceiling over the cake, cupcakes/donuts/macarons on hangers going round
                     (func_rotating, IQM model2)
  Tempering machine  on the east counter: a chocolate curtain pouring into a tray, the enrober drum turning (X axis)
  Pot rack           hung over the east counter, ladles and whisks swinging (func_pendulum)
  Steam              rising from the oven top vents, the proofer and the mixer bowl
  Sprinkle tube      a glass tube full of tumbling sprinkles along a jump-pad flight from the floor to the wall shelf
  Neon + bunting     a SWEET PADMAN'S neon script over the flour bin, party bunting round the walls
  Bakery cat         asleep by the warm oven (and a meow now and then)
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from bk_mesh import *
import layout as L
import bk_props as BP

CONV_C = (L.CAKE[0], L.CAKE[1])
CONV_R = 1150.0
CONV_Z = 1560.0
RACK_BAR = (2010.0, -260.0, 2010.0, 860.0, 1420.0)      # x0, y0, x1, y1, z of the hanging pot rack bar
TEMPER = (2110.0, 650.0)
TUBE_PAD = (1580.0, 1080.0)
TUBE_LAND = (1440.0, 1960.0)
TUBE_APEX = 1440.0


def SM(img, shade=60, **kw): return S(img, 'lm', shade=shade, **kw)
def SD(img, **kw): return S(img, 'dyn', **kw)


# ================================================================================================= textures
def tex_steam(w=128, h=256, seed=61):
    x, y = xy(w, h)
    n = np.clip(noise(w, 8, seed, h) * 0.5 + 0.5, 0, 1) * np.clip(noise(w, 3, seed + 1, h) * 0.4 + 0.7, 0, 1)
    fade = np.exp(-((x - 0.5) / 0.28) ** 2)
    v = np.clip(n * fade, 0, 1) * 150
    return np.zeros((h, w, 3), np.float32) + v[..., None] * C((1.0, 0.98, 0.95))


def tex_neon(w=1024, h=256, text="Sweet Padman's", col=(255, 80, 170)):
    im = Image.new('RGB', (w, h), (0, 0, 0)); d = ImageDraw.Draw(im)
    sz = 150
    while sz > 20:
        f = font(sz, True)
        if d.textlength(text, font=f) < w * 0.9: break
        sz -= 6
    g = Image.new('RGB', (w, h), (0, 0, 0)); dg = ImageDraw.Draw(g)
    dg.text((w / 2, h / 2), text, font=f, fill=col, anchor='mm')
    g = g.filter(ImageFilter.GaussianBlur(10))
    d.text((w / 2, h / 2), text, font=f, fill=col, anchor='mm', stroke_width=3, stroke_fill=col)
    d.text((w / 2, h / 2), text, font=f, fill=(255, 235, 245), anchor='mm')
    a = np.asarray(im, np.float32) + np.asarray(g, np.float32) * 1.6
    return a


def tex_bunting(w=256, h=64):
    cols = [(240, 90, 140), (90, 200, 230), (250, 210, 70), (140, 220, 140), (190, 140, 240), (255, 160, 90), (250, 250, 250), (240, 90, 90)]
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    for k, c in enumerate(cols):
        d.rectangle((k * w / 8, 0, (k + 1) * w / 8, h), fill=c)
        for j in range(3):
            d.ellipse((k * w / 8 + 6 + j * 9, 20 + (j % 2) * 14, k * w / 8 + 11 + j * 9, 25 + (j % 2) * 14), fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def tex_fur(n=128, seed=63):
    c = fill(n, (230, 150, 70), 4, seed)
    x, y = xy(n)
    st = np.sin(x * 40 + noise(n, 4, seed + 1) * 3) > 0.4
    return np.where(st[..., None], c * 0.78, c) + N3(n, 0.5, seed + 2, 6)


def make_textures():
    T('steam', tex_steam()); T('neon_script', tex_neon()); T('bunting', tex_bunting()); T('fur', tex_fur())
    T('choc_flow', tex_choc(128, 64, (96, 54, 32)))


# ================================================================================================= models
def conv_rail():
    """the ring rail of the cupcake conveyor, hung from the ceiling on rods (local: ring centre at the origin)"""
    X = Model()
    ch = S('steel', 'lms', v=0.3, shade=50, tag='cv')
    torus(X.mesh(ch), (0, 0, CONV_Z), CONV_R, 9, n=120, m=8)
    torus(X.mesh(ch), (0, 0, CONV_Z + 26), CONV_R, 4, n=120, m=6)
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        p = np.array([CONV_R * math.cos(a), CONV_R * math.sin(a)])
        tube(X.mesh(ch), [(p[0], p[1], CONV_Z), (p[0], p[1], L.CEIL)], 5, nseg=8)
        cylm(X.mesh(ch), (p[0], p[1], L.CEIL - 10), 22, 10, n=12)
    return save('conv_rail', X)


def conv_carriers(n=24):
    """hangers with treats on trays, already placed round the ring (IQM model2, origin at the ring centre, z CONV_Z)"""
    X = Model()
    ch, tr = SD('steel', tag='cc2'), SD('white', tag='cc2')
    kinds = ['cup', 'donut', 'mac', 'cup', 'cake']
    fr = ['bc_pink', 'bc_choc', 'bc_mint', 'bc_lemon', 'bc_blue', 'bc_lilac']
    for k in range(n):
        a = 2 * math.pi * k / n
        c = np.array([CONV_R * math.cos(a), CONV_R * math.sin(a), 0.0])
        R = rot_z(a)
        tube(X.mesh(ch), [c + [0, 0, 10], c + [0, 0, -120]], 3, nseg=6)
        boxm(X.mesh(ch), tuple(c + [-14, -10, 2]), tuple(c + [14, 10, 22]), r=2, tile=32)
        revolve(X.mesh(tr), [(0, -128), (46, -128), (50, -122), (0, -122)], n=16, cx=c[0], cy=c[1])
        z0 = -122
        kind = kinds[k % len(kinds)]
        f = fr[k % len(fr)]
        if kind == 'cup':
            r = 26; h = r * 1.15
            revolve(X.mesh(SD('liner_p' if k % 2 else 'liner_b', tag='cc2')), [(0, z0), (r * 0.78, z0), (r, z0 + h)], n=14, cx=c[0], cy=c[1])
            pts = []; rad = []
            for j in range(31):
                t = j / 30; aa = 2 * math.pi * 2.5 * t; rr = r * 0.95 * (1 - t) ** 0.85
                pts.append(c + [rr * math.cos(aa), rr * math.sin(aa), z0 + h + r * 0.25 + r * 1.1 * t])
                rad.append(r * 0.4 * (1 - 0.65 * t))
            tube(X.mesh(SD(f, tag='cc2')), pts, rad, nseg=8)
            sphere(X.mesh(SD('red', tag='cc2')), c + [0, 0, z0 + h + r * 1.5], 7, nu=8, nv=5)
        elif kind == 'donut':
            torus(X.mesh(SD('crust', tag='cc2')), c + [0, 0, z0 + 15], 30, 14, n=20, m=8)
            torus(X.mesh(SD('sprinkles', tag='cc2')), c + [0, 0, z0 + 19], 30, 12, n=20, m=8)
        elif kind == 'mac':
            for j in range(3):
                ellipsoid(X.mesh(SD(fr[(k + j) % len(fr)], tag='cc2')), c + [0, 0, z0 + 8 + j * 20], 20, 20, 9, nu=12, nv=6)
        else:
            revolve(X.mesh(SD(f, tag='cc2')), [(0, z0), (42, z0), (42, z0 + 44), (0, z0 + 44)], n=20, cx=c[0], cy=c[1])
            sphere(X.mesh(SD('red', tag='cc2')), c + [0, 0, z0 + 52], 9, nu=8, nv=5)
    return save_iqm('conv_carriers', X)


def temper():
    """chocolate tempering machine: steel body, a hopper of melted chocolate, a curtain pouring into the tray"""
    X = Model()
    st, sd = S('steel', 'lms', v=0.25, shade=40, tag='tm'), SM('steel_d', tag='tm')
    boxm(X.mesh(st), (-140, -120, 0), (140, 120, 180), r=10, tile=128)
    revolve(X.mesh(st), [(70, 180), (130, 180), (140, 270), (134, 272), (124, 186), (0, 186)], n=28, cx=0, cy=0)
    disc(X.mesh(SM('choc', 70, tag='tm')), 130, 258, n=28)
    # spout and the flowing curtain into the tray at the front (-x side)
    boxm(X.mesh(st), (-190, -70, 150), (-130, 70, 166), r=3, tile=64)
    fl = S('choc_flow', 'glow', tcmod='scroll 0 -0.9', tag='tmf', two=True)
    quad_uv(X.mesh(fl), (-186, -60, 150), (-186, 60, 150), (-186, 60, 40), (-186, -60, 40), [(0, 0), (1, 0), (1, 2), (0, 2)], (-1, 0, 0))
    boxm(X.mesh(sd), (-240, -90, 0), (-150, 90, 40), r=4, tile=64)
    disc(X.mesh(SM('choc', 70, tag='tm')), 1, 36, n=4)
    quad_uv(X.mesh(SM('choc', 70, tag='tm')), (-236, -86, 37), (-154, -86, 37), (-154, 86, 37), (-236, 86, 37), [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, 1))
    picture(X.mesh(S('screen', 'glow', tag='tm')), (0, -120.6, 120), 120, 50, (0, -1, 0))
    # drum cradle (the drum itself is a mover)
    for s in (-1, 1):
        boxm(X.mesh(sd), (60, s * 80 - 8, 180), (110, s * 80 + 8, 300), r=3, tile=64)
    BP.BOX['temper'] = [((-236, -116, 0), (136, 116, 176)), ((-120, -120, 176), (120, 120, 268))]
    return save('temper', X)


def temper_drum():
    """the enrober drum (mover model2, rotates about x; origin at the drum axis)"""
    X = Model()
    m = Mesh(); revolve(m, [(0, -60), (64, -60), (66, -56), (66, 56), (64, 60), (0, 60)], n=24, vlen=64)
    X.mesh(SD('choc', tag='td')).add(m, rot_axis((1, 0, 0), math.pi / 2), (0, 0, 0))
    for k in range(8):
        a = 2 * math.pi * k / 8
        tube(X.mesh(SD('steel', tag='td')), [(66 * math.cos(a), -62, 66 * math.sin(a)), (66 * math.cos(a), 62, 66 * math.sin(a))], 4, nseg=5)
    return save('temper_drum', X)


def pot_rack():
    """hanging pot rack bar (local: x along the bar from 0, z 0 = bar), hung from the ceiling"""
    X = Model()
    x0, y0, x1, y1, z = RACK_BAR
    Ln = math.hypot(x1 - x0, y1 - y0)
    ch = S('copper', 'lms', v=0.3, shade=50, tag='pr')
    tube(X.mesh(ch), [(0, 0, 0), (Ln, 0, 0)], 9, nseg=10)
    for t in (0.0, Ln):
        tube(X.mesh(ch), [(t, 0, 0), (t, 0, L.CEIL - z)], 4, nseg=6)
        cylm(X.mesh(ch), (t, 0, L.CEIL - z - 10), 20, 10, n=12)
    for k in range(9):
        torus(X.mesh(ch), (60 + k * (Ln - 120) / 8, 0, -6), 9, 2.5, axis=(0, 1, 0), n=12, m=5)
    return save('potrack', X)


def ladle(name, kind):
    """utensil hanging from its hook (origin at the hook, hangs down), for func_pendulum model2"""
    X = Model()
    cu = SD('copper' if kind != 'whisk' else 'steel', tag='ld')
    if kind == 'ladle':
        tube(X.mesh(cu), [(0, 0, -6), (0, 0, -200)], 4, nseg=6)
        ellipsoid(X.mesh(cu), (0, 0, -222), 28, 28, 18, nu=12, nv=6)
    elif kind == 'whisk':
        tube(X.mesh(SD('wood_d', tag='ld')), [(0, 0, -6), (0, 0, -90)], 7, nseg=8)
        for k in range(6):
            a = k * math.pi / 6
            pts = [(math.cos(a) * 30 * math.sin(math.pi * t), math.sin(a) * 30 * math.sin(math.pi * t), -90 - 130 * t) for t in np.linspace(0, 1, 10)]
            tube(X.mesh(cu), pts, 1.6, nseg=4)
    else:
        tube(X.mesh(cu), [(0, 0, -6), (0, 0, -110)], 5, nseg=6)
        m = Mesh(); revolve(m, [(0, 0), (70, 0), (78, 34), (74, 36), (64, 6), (0, 6)], n=20)
        X.mesh(cu).add(m, rot_axis((1, 0, 0), math.pi / 2), (0, 0, -190))
    return save(name, X)


def steam_column(name='steam', w=120.0, h=420.0):
    X = Model()
    sh = S('steam', 'add', tcmod='scroll 0.02 0.22', wave='sin 0.55 0.2 0 0.25', tag='st')
    for a in (0, math.pi / 2):
        d = np.array([math.cos(a), math.sin(a), 0]) * w / 2
        quad_uv(X.mesh(sh), -d, d, d + [0, 0, h], -d + [0, 0, h], [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([-math.sin(a), math.cos(a), 0]))
    return save(name, X)


def sprinkle_tube(pad, land, apex, z0=0.0):
    """glass tube along the jump-pad flight (Q3 AimAtTarget), world coordinates, with sprinkles tumbling inside"""
    X = Model()
    ox, oy, oz = pad[0], pad[1], z0 + 38
    tu_ = math.sqrt(2 * (apex - oz) / 800); td_ = math.sqrt(2 * (apex - (land[2] + 24)) / 800)
    f_ = tu_ / (tu_ + td_)
    tx, ty = ox + (land[0] - ox) * f_, oy + (land[1] - oy) * f_
    hgt = apex - oz
    tu = math.sqrt(2 * hgt / 800)
    vx, vy = (tx - ox) / tu, (ty - oy) / tu
    vz = 800 * tu
    pts = []
    t = 0.0
    while True:
        p = np.array([ox + vx * t, oy + vy * t, oz + vz * t - 400 * t * t])
        if t > tu and p[2] < land[2] + 120: break
        pts.append(p); t += 0.05
    pts = [np.array([ox, oy, z0 + 8])] + pts
    gl = S('glass_g', 'glass', c='0.10 0.12 0.14', tag='tb')
    tube(X.mesh(gl), pts, 52, nseg=16, caps=(False, False))
    sp = S('sprinkles', 'glow', tcmod='scroll 0 -1.6', tag='tbs')
    tube(X.mesh(sp), pts[2:-2], 14, nseg=8, caps=(False, False), vlen=128)
    ch = S('steel', 'lms', v=0.3, shade=50, tag='tb')
    torus(X.mesh(ch), (ox, oy, z0 + 8), 58, 8, n=24, m=6)
    for k in range(3, len(pts) - 3, 9):
        p = pts[k]
        d = pts[k + 1] - pts[k - 1]
        torus(X.mesh(ch), p, 56, 4, axis=d, n=20, m=5)
    return save('sprinkletube', X), pts


def bunting_lines():
    """party bunting round the walls: lines strung between ceiling hooks, triangle flags below (world coordinates)"""
    X = Model()
    fl = S('bunting', 'vl', tag='bu', two=True)
    cd = SM('white', tag='bu')
    m = 220
    corners = [(-L.HX + m, -L.HY + m), (L.HX - m, -L.HY + m), (L.HX - m, L.HY - m), (-L.HX + m, L.HY - m)]
    ztop = L.CEIL - 140
    for i in range(4):
        a, b = np.array(corners[i], float), np.array(corners[(i + 1) % 4], float)
        Ln = np.linalg.norm(b - a)
        nseg = int(Ln // 64)
        pts = []
        for k in range(nseg + 1):
            t = k / nseg
            p = a + (b - a) * t
            pts.append(np.array([p[0], p[1], ztop - 160 * 4 * t * (1 - t)]))
        tube(X.mesh(cd), pts, 2, nseg=4, caps=(False, False))
        for p in (pts[0], pts[-1]):
            tube(X.mesh(cd), [p, p + [0, 0, L.CEIL - p[2]]], 2, nseg=4)
        dirv = (b - a) / Ln
        nrm = np.array([-dirv[1], dirv[0], 0])
        for k in range(1, nseg):
            p0, p1 = pts[k], pts[k + 1] if k + 1 <= nseg else pts[k]
            mid = (p0 + p1) / 2
            u0 = (k % 8) / 8; u1 = u0 + 1 / 8
            tri = [p0, p1, mid + [0, 0, -70]]
            X.mesh(fl).poly(tri, nrm, [(u0, 0), (u1, 0), ((u0 + u1) / 2, 1)])
    return save('bunting', X)


def neon_sign():
    """neon script on the west wall over the flour bin (world coordinates)"""
    X = Model()
    sh = S('neon_script', 'add', wave='sin 0.92 0.08 0 0.6', tag='ns')
    picture(X.mesh(sh), (-L.HX + 1.0, 1350, 1430), 900, 225, (1, 0, 0))
    ch = S('steel', 'lms', v=0.3, shade=50, tag='ns')
    for y in (950, 1750):
        tube(X.mesh(ch), [(-L.HX, y, 1430), (-L.HX + 14, y, 1430)], 4, nseg=6)
    return save('neon_sign', X)


def cat():
    """ginger bakery cat asleep, curled up (origin floor centre)"""
    X = Model()
    fu = SM('fur', 60, tag='cat')
    ellipsoid(X.mesh(fu), (0, 0, 26), 62, 46, 30, nu=18, nv=9, flat_bottom=-24)
    ellipsoid(X.mesh(fu), (40, 22, 30), 26, 24, 22, nu=14, nv=8)
    for s in (-1, 1):
        m = Mesh(); revolve(m, [(0, 0), (9, 0), (0, 16)], n=6)
        X.mesh(fu).add(m, rot_axis((1, 0, 0), s * 0.35), (46 + 4, 22 + s * 12, 48))
    tube(X.mesh(fu), [(-50, -20, 10), (-30, -50, 8), (10, -52, 8), (40, -30, 8)], [10, 9, 8, 6], nseg=8)
    for s in (-1, 1):
        tube(X.mesh(SM('black', tag='cat')), [(62, 22 + s * 9 - 3, 34), (62, 22 + s * 9 + 3, 34)], 1.2, nseg=4)
    BP.CYL['cat'] = [(0, 0, 50, 0, 50)]
    return save('cat', X)


def sparklers():
    """two sparkler candles on the cake top beside the plaque (flickering glow tips)"""
    X = Model()
    zt = L.TIERS[2][2]
    for dx in (-150, 150):
        tube(X.mesh(SM('pearl', tag='sp')), [(dx, 70, zt), (dx, 70, zt + 120)], 5, nseg=8)
        sphere(X.mesh(S('glow_y', 'flicker', ph=0.3 if dx < 0 else 0.7, tag='sp')), (dx, 70, zt + 132), 14, nu=10, nv=6)
        for k in range(8):
            a = 2 * math.pi * k / 8
            tube(X.mesh(S('glow_y', 'flicker', ph=0.5, tag='sp2')), [(dx, 70, zt + 132), (dx + 30 * math.cos(a), 70 + 30 * math.sin(a), zt + 132 + 18 * math.sin(a * 3))], [2.5, 0.6], nseg=4)
    return save('sparklers', X)


def make():
    make_textures()
    conv_rail(); conv_carriers(); temper(); temper_drum(); pot_rack()
    ladle('ladle', 'ladle'); ladle('whiskh', 'whisk'); ladle('panh', 'pan')
    steam_column(); bunting_lines(); neon_sign(); cat(); sparklers()
    sprinkle_tube(TUBE_PAD, (TUBE_LAND[0], TUBE_LAND[1], L.WALL_SHELF[3]), TUBE_APEX)


# ================================================================================================= placement
def place(B):
    M, A = B.M, B.A
    ORIGIN, NODRAW_NS = B.ORIGIN, B.NODRAW_NS
    box = B.box
    # cupcake conveyor
    cx, cy = CONV_C
    B.custom('conv_rail', cx, cy, 0, 0, lit=False)
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, CONV_Z - 8), (cx + 8, cy + 8, CONV_Z + 8), ORIGIN),
                                    box((cx - 4, cy - 4, CONV_Z + 40), (cx + 4, cy + 4, CONV_Z + 48), NODRAW_NS)],
          model2=IQM['conv_carriers'], speed=9, spawnflags=0, dmg=0)
    B.speaker(cx + CONV_R, cy, CONV_Z, 'machine/mechanics', volume=0.18)
    B.speaker(cx - CONV_R, cy, CONV_Z, 'machine/mechanics', volume=0.18)
    # tempering machine on the east counter (drum turning about x)
    tx, ty = TEMPER
    W = L.WORK
    B.prop('temper', tx, ty, W, ang=0, force=True)
    dz = W + 240
    M.ent('func_rotating', brushes=[box((tx + 77, ty - 8, dz - 8), (tx + 93, ty + 8, dz + 8), ORIGIN),
                                    box((tx + 81, ty - 4, dz + 30), (tx + 89, ty + 4, dz + 38), NODRAW_NS)],
          model2=bklib.PLACE['temper_drum'][0], speed=30, spawnflags=8, dmg=0)
    B.speaker(tx - 120, ty - 200, W + 120, 'machine/transformer', volume=0.2)
    # pot rack + swinging utensils (func_pendulum)
    x0, y0, x1, y1, z = RACK_BAR
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    B.custom('potrack', x0, y0, z, ang, lit=False)
    Ln = math.hypot(x1 - x0, y1 - y0)
    for k, nm in enumerate(('ladle', 'whiskh', 'panh', 'ladle', 'whiskh', 'panh', 'ladle')):
        t = 140 + k * (Ln - 280) / 6
        px, py = x0 + (x1 - x0) * t / Ln, y0 + (y1 - y0) * t / Ln
        reach = 110 + 20 * (k % 3)
        M.ent('func_pendulum', brushes=[box((px - 4, py - 4, z - 20 - reach), (px + 4, py + 4, z - 20), NODRAW_NS),
                                        box((px - 8, py - 8, z - 30), (px + 8, py + 8, z - 14), ORIGIN)],
              model2=bklib.PLACE[nm][0], speed=8 + 2 * (k % 2), phase=round(k * 0.17, 2), angle=0)
    # steam: oven top vents (back corners), the proofer mouth, the mixer bowl
    for (x, y, z0, nm) in ((-2240, -560, L.OV_TOP, 'steam'), (-2240, 560, L.OV_TOP, 'steam'), (L.MIX[0] - 40, L.MIX[1] + 60, L.BOWL_Z0, 'steam')):
        B.custom(nm, x, y, z0, 0, lit=False)
    # sprinkle tube: a new way up to the wall shelf
    zt = L.WALL_SHELF[3]
    B.jumppad(TUBE_PAD[0], TUBE_PAD[1], 0, (TUBE_LAND[0], TUBE_LAND[1], zt), TUBE_APEX, 'p_tube')
    B.custom('sprinkletube', 0, 0, 0, 0, lit=False)
    B.light(TUBE_PAD[0], TUBE_PAD[1], 200, 220, '1 0.7 0.9')
    B.custom('sparklers', CONV_C[0], CONV_C[1], 0, 0, lit=False)
    B.light(CONV_C[0], CONV_C[1] + 70, L.TIERS[2][2] + 200, 260, '1 0.85 0.5')
    # bunting, neon, cat
    B.custom('bunting', 0, 0, 0, 0, lit=False)
    B.custom('neon_sign', 0, 0, 0, 0, lit=False)
    for y in (1100, 1350, 1600):
        B.light(-L.HX + 60, y, 1430, 260, '1 0.4 0.75')
    p = B.prop('cat', -1560, -600, 0, ang=200, search=200)
    if p: B.timer_sound(p[0], p[1], 120, 'animal/kitten_meow', 'cat_meow', 45, 25, volume=0.45)
    # one-shots: shop door chime on entering the shop, a cheer on the wall shelf
    B.trigger_sound((L.DC[0] - 200, -1740, 8), (L.DC[0] - 20, L.DC[1] - 40, 120), 'misc/wind_chimes', 'shop_chime_w', wait=8, volume=0.4)
    B.trigger_sound((L.DC[2] + 20, -1740, 8), (L.DC[2] + 200, L.DC[1] - 40, 120), 'misc/wind_chimes', 'shop_chime_e', wait=8, volume=0.4)
