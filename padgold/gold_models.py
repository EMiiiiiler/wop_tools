"""Gold Rush Gulch - textures (brush + model) and custom MD3/IQM pieces.

Everything is procedural (woplib.texlib / woplib.models / meshlib). The geometry constants shared with the builder
(water tower, carts, steamer) come in as arguments so the weapclip collision always matches the meshes.
"""
import math
import numpy as np
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, tube, prism, ellipsoid, rot_z

C = ML.C

# ------------------------------------------------------------------------------------------------ palette
SAND = (196, 150, 104); DIRT = (170, 120, 80); ROCK = (176, 92, 58); ROCK_D = (128, 62, 40)
WOOD = (150, 104, 62); WOOD_D = (98, 66, 40); WOOD_G = (140, 130, 116); IRON = (70, 66, 64)
PAINT = {'red': (150, 52, 40), 'white': (226, 218, 198), 'blue': (88, 112, 132), 'yellow': (206, 164, 84),
         'green': (92, 118, 82), 'brick': (150, 74, 54), 'grey': (150, 146, 136), 'teal': (70, 130, 128)}


# ================================================================================================= texture art
def strata(n=512, seed=3):
    """red canyon sandstone: soft horizontal bedding that wanders, pale bands, vertical weathering streaks (tiles;
    use it at 2 world units per texel so one tile covers ~1000u)"""
    x, y = ML.xy(n)
    w = ML.noise(n, 30, seed) * 0.04
    yy = y + w + 0.015 * np.sin(x * 2 * math.pi * 2)
    band = (np.sin(yy * 2 * math.pi * 5) * 0.5 + 0.5) * 0.6 + (np.sin(yy * 2 * math.pi * 11 + 1.3) * 0.5 + 0.5) * 0.4
    a = ML.lerp(C(ROCK_D), C(ROCK), band[..., None])
    a = ML.lerp(a, C((222, 168, 118)), (np.clip(band - 0.8, 0, 1) * 3)[..., None])
    streak = ML.noise(n, 4, seed + 5)
    streak = np.repeat(streak.mean(0, keepdims=True), n, 0)              # vertical desert-varnish streaks
    a = a * (1 - 0.12 * np.clip(streak, 0, 2)[..., None])
    return a + ML.N3(n, 2, seed + 1, 8) + ML.N3(n, 16, seed + 2, 12)


def sand(n=256, seed=5, col=SAND):
    a = ML.fill(n, col, 6, seed) + ML.N3(n, 18, seed + 2, 10)
    x, y = ML.xy(n)
    ripple = np.sin((y + 0.05 * np.sin(x * 6.28 * 2)) * 6.28 * 10) * 4
    return a + ripple[..., None]


def street(n=256, seed=7):
    """packed dirt with wagon ruts running along x"""
    a = sand(n, seed, DIRT)
    x, y = ML.xy(n)
    rut = np.exp(-((y - 0.3) / 0.05) ** 2) + np.exp(-((y - 0.7) / 0.05) ** 2)
    return a - rut[..., None] * 18


def siding(col, n=256, seed=11):
    """horizontal clapboard, weathered"""
    a = TL.planks(col, n_planks=8, gap=tuple(int(v * 0.55) for v in col), grain=8, stagger=False, seed=seed, n=n)
    return TL.grime(a, 0.18, seed + 1)


def boards(col=WOOD, n=256, seed=13, vertical=False, k=6):
    return TL.planks(col, n_planks=k, gap=tuple(int(v * 0.5) for v in col), grain=12, vertical=vertical, seed=seed, n=n)


def tin_roof(n=256, seed=17):
    a = TL.stripes((150, 146, 140), (110, 106, 100), n_stripes=16, vertical=True, soft=0.6, seed=seed, n=n)
    return TL.grime(a, 0.35, seed, dark=(120, 70, 40))


def shingles(col=(110, 76, 52), n=256, seed=19):
    return TL.tiles(col, tuple(int(v * 0.55) for v in col), cols=8, rows=12, offset=0.5, grout_w=0.05, vary=16, seed=seed, n=n)


def water_tex(n=128, seed=23, col=(70, 150, 170)):
    return ML.fill(n, col, 8, seed) + ML.N3(n, 6, seed + 1, 16)


def flume_water(n=128, seed=29):
    """streaky white-water (scrolled along the flume)"""
    x, y = ML.xy(n)
    s = ML.noise(n, 3, seed)
    streak = np.clip(np.sin(x * 6.28 * 9 + s * 2) * 0.5 + 0.5, 0, 1) ** 4
    return C((60, 140, 170)) + streak[..., None] * C((150, 110, 80)) + ML.N3(n, 2, seed + 2, 10)


def facade(text, col, trim=(232, 224, 204), sign_bg=(40, 30, 24), sign_fg=(236, 200, 110), w=512, h=320, seed=31,
           band=(0.06, 0.26)):
    """false-front facade: clapboard in `col`, trim boards, a painted sign band near the top (real windows/doors are
    holes in the wall, so none are painted). Fitted across the whole front of a building."""
    a = TL.planks(col, n_planks=int(h / 24), gap=tuple(int(v * 0.55) for v in col), grain=8, stagger=False, seed=seed,
                  n=w)[:h] if h <= w else np.vstack([TL.planks(col, n_planks=10, stagger=False, seed=seed, n=w)] * 2)[:h]
    a = TL.grime(a, 0.15, seed + 3)
    r0, r1 = int(band[0] * h), int(band[1] * h)
    a[r0:r1, int(w * 0.06):int(w * 0.94)] = ML.text_img(text, int(w * 0.94) - int(w * 0.06), r1 - r0, sign_bg, sign_fg,
                                                          serif=True, border=sign_fg)
    a[:max(3, int(h * 0.03))] = C(trim); a[-max(3, int(h * 0.02)):] = C(trim)
    a[:, :6] = C(trim); a[:, -6:] = C(trim)
    return a


def poster(text, w=128, h=176, seed=37):
    a = ML.fill(w, (222, 200, 150), 3, seed, h) + ML.N3(w, 4, seed, 8, h)
    top = ML.text_img('WANTED', w, int(h * 0.25), (222, 200, 150), (60, 30, 20), serif=True)
    a[:top.shape[0]] = top
    face = ML.text_img(':(', w - 30, int(h * 0.4), (180, 160, 120), (60, 40, 30), serif=False)
    a[int(h * 0.27):int(h * 0.27) + face.shape[0], 15:15 + face.shape[1]] = face
    b = ML.text_img(text, w, int(h * 0.25), (222, 200, 150), (100, 30, 20), serif=True)
    a[-b.shape[0]:] = b
    return a


def hull_paint(w=64, h=256):
    """steamer hull: white topsides, red boot stripe, dark red bottom (v runs down from the deck)"""
    a = np.zeros((h, w, 3), np.float32)
    v = np.linspace(0, 1, h)[:, None]
    a[:] = C((236, 232, 222))
    a[(v[:, 0] > 0.18) & (v[:, 0] < 0.24)] = C((40, 40, 46))
    a[v[:, 0] >= 0.24] = C((150, 40, 32))
    return a + ML.N3(w, 2, 41, 4, h)


def gold_rock(n=256, seed=43):
    """quartz rock with gold veins for the Mother Lode"""
    x, y = ML.xy(n)
    base = ML.fill(n, (110, 84, 64), 6, seed) + ML.N3(n, 14, seed + 1, 18)
    s = ML.noise(n, 5, seed + 2)
    vein = np.clip(1 - np.abs(s) * 4, 0, 1) ** 3
    return ML.lerp(base, C((250, 206, 80)), vein[..., None])


# ================================================================================================= brush textures
def brush_textures(TX):
    TX.add('sand', sand(), steps='sandsteps')
    TX.add('street', street(), steps='sandsteps')
    TX.add('strata', strata(), scale=2.0)
    TX.add('lakebed', sand(seed=9, col=(150, 128, 96)), steps='splashsteps')
    TX.add('rock', TL.stone(ROCK, cells=10, edge=ROCK_D, vary=18))
    TX.add('boardwalk', boards(WOOD_G, k=8, vertical=True), steps='woodsteps')
    TX.add('planks', boards(WOOD), steps='woodsteps')
    TX.add('planks_d', boards(WOOD_D, seed=14), steps='woodsteps')
    TX.add('timber', boards((122, 86, 54), seed=15, k=3, vertical=True))
    TX.add('tile', TL.tiles((90, 160, 180), (230, 236, 236), cols=8, rows=8, offset=0, grout_w=0.06))
    TX.add('pool_wall', TL.stone((156, 120, 96), cells=12, edge=(110, 84, 64)))
    TX.add('creekbed', TL.stone((150, 128, 100), cells=40, edge=(110, 90, 70), vary=24), steps='splashsteps')
    TX.add('gold_rock', gold_rock())
    TX.add('iron', TL.metal(IRON, brushed=False))
    TX.add('water', water_tex(), 'water', rgb=(0.28, 0.55, 0.62), alpha=0.6)
    TX.add('creek', water_tex(col=(110, 150, 140)), 'water', rgb=(0.4, 0.55, 0.5), alpha=0.45)
    fl = flume_water()
    TX.add('flume', fl, 'raw', shader=(
        'textures/{ns}/flume\n{{\n\tqer_editorimage textures/{ns}/flume\n\tsurfaceparm nomarks\n\tsurfaceparm splashsteps\n'
        '\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap textures/{ns}/flume\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n'
        '\t\ttcMod scroll 0 -1.4\n\t}}\n\t{{\n\t\tmap textures/{ns}/flume\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.25 0.25 0.25 )\n'
        '\t\ttcMod scroll 0.05 -2.0\n\t}}\n}}\n\n').format(ns=TX.ns))
    TX.add('sign_town', ML.text_img('GOLD RUSH GULCH', 1024, 192, (40, 28, 20), (240, 200, 100), border=(240, 200, 100)),
           'sign', check_tile=False)
    TX.add('sign_mine', ML.text_img('LUCKY STRIKE MINE', 1024, 192, (60, 44, 30), (230, 220, 200), border=(150, 110, 70)),
           'sign', check_tile=False)
    TX.add('sign_dredge', ML.text_img('GOLD DREDGE No.1', 512, 128, (60, 44, 30), (240, 200, 100)), 'sign', check_tile=False)
    TX.add('sign_flume', ML.text_img('FLUME', 512, 128, (40, 28, 20), (240, 200, 100)), 'sign', check_tile=False)
    TX.add('poster1', poster('$500'), 'sign', check_tile=False)
    TX.add('poster2', poster('PADMAN'), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(250, 200, 90), rubber=(80, 54, 36))


# ================================================================================================= model materials
def materials(TX, facades):
    m = TX.material
    m('wood', boards(WOOD, n=128), shade=30)
    m('wood_d', boards(WOOD_D, n=128, seed=4), shade=30)
    m('wood_g', boards(WOOD_G, n=128, seed=6, vertical=True), shade=30)
    m('timber', boards((122, 86, 54), n=128, seed=8, k=3, vertical=True), shade=30)
    m('floor', boards((132, 92, 56), n=256, seed=9, k=8), shade=20, steps='woodsteps')
    m('interior', boards((168, 128, 88), n=256, seed=10, k=10), shade=20)
    m('tin', tin_roof(), shade=20)
    m('shingle', shingles(), shade=40)
    m('iron', TL.metal(IRON, brushed=False, n=128), shade=60)
    m('brass', TL.metal((200, 160, 80), n=128), 'lms', shade=60, v=0.25)
    m('staves', boards((150, 102, 60), n=256, seed=12, k=12, vertical=True), shade=80)
    m('canvas', TL.fabric((226, 214, 186), weave=48), shade=80)
    m('hay', ML.fill(128, (214, 180, 96), 2, 51) + ML.N3(128, 1, 52, 30), shade=40)
    m('rock', TL.stone(ROCK, cells=10, edge=ROCK_D, vary=18, n=128), shade=60)
    m('sinter', ML.fill(128, (226, 214, 190), 6, 53) + ML.N3(128, 3, 54, 18), shade=70)
    m('hull', hull_paint(), shade=30)
    m('white', ML.fill(128, (232, 226, 210), 3, 55), shade=30)
    m('red', ML.fill(128, PAINT['red'], 3, 56), shade=40)
    m('black', ML.fill(64, (30, 28, 28), 2, 57), shade=60)
    m('glow', ML.fill(64, (255, 220, 140), 1, 58), 'glow')
    m('steam', ML.fill(64, (255, 255, 255), 8, 59) * 0.25, 'add', tcmod='scroll 0 0.6')
    m('gold', TL.metal((230, 180, 60), n=128), 'lms', shade=60, v=0.35)
    m('felt', TL.fabric((40, 100, 60), weave=32, n=128), shade=40)
    m('bottles', TL.stripes((60, 110, 60), (120, 60, 30), n_stripes=12, vertical=True, n=128), shade=40)
    m('bars', TL.metal((50, 50, 52), n=64), shade=60)
    for key, (text, col) in facades.items():
        m('fac_' + key, facade(text, PAINT[col]), shade=20)
        m('side_' + key, siding(PAINT[col], n=256, seed=hash(key) % 97), shade=20)


# ================================================================================================= small builders
def M_(X, key): return X.mesh(TX_[key])


TX_ = None


def bind(TX):
    global TX_
    TX_ = TX


def cylz(M, x, y, z0, z1, r, n=12, caps=True, tiles=1.0):
    revolve(M, [(r, z0), (r, z1)], u_tiles=tiles, n=n, cx=x, cy=y)
    if caps: disc(M, r, z1, up=True, n=n, cx=x, cy=y)


def bar(M, a, b, r, n=8):
    tube(M, [a, b], r, nseg=n, caps=(True, True))


# ================================================================================================= models
def water_tower(R_TANK, R_CAT, Z_CAT, Z_TOP, R_CAP, Z_CAP, LEG_R):
    """trestle water tower: 4 splayed legs + X braces, plank catwalk ring, stave tank with iron hoops and a painted
    GOLD RUSH GULCH band, shingle cone roof with a flat cap (walkable) and a finial"""
    X = ML.Model()
    w, ir, st, sh = M_(X, 'timber'), M_(X, 'iron'), M_(X, 'staves'), M_(X, 'shingle')
    legs = []
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p0 = np.array([math.cos(a) * (LEG_R + 60), math.sin(a) * (LEG_R + 60), 0])
        p1 = np.array([math.cos(a) * LEG_R, math.sin(a) * LEG_R, Z_CAT - 16])
        tube(w, [p0, p1], 18, nseg=10)
        legs.append((p0, p1))
    for k in range(4):
        (a0, a1), (b0, b1) = legs[k], legs[(k + 1) % 4]
        for t0, t1 in ((0.05, 0.45), (0.5, 0.92)):
            pa0 = a0 + (a1 - a0) * t0; pa1 = a0 + (a1 - a0) * t1
            pb0 = b0 + (b1 - b0) * t0; pb1 = b0 + (b1 - b0) * t1
            tube(ir, [pa0, pb1], 4, nseg=6); tube(ir, [pb0, pa1], 4, nseg=6)
    # catwalk: plank annulus, rim, joists
    disc(M_(X, 'floor'), R_CAT, Z_CAT, up=True, n=48, r_in=R_TANK - 4)
    disc(w, R_CAT, Z_CAT - 16, up=False, n=48, r_in=R_TANK - 4)
    revolve(w, [(R_CAT, Z_CAT - 16), (R_CAT, Z_CAT)], u_tiles=16, n=48)
    # tank
    revolve(st, [(R_TANK, Z_CAT), (R_TANK, Z_TOP)], u_tiles=20, n=48, vlen=Z_TOP - Z_CAT)
    for z in (Z_CAT + 30, Z_CAT + 110, Z_TOP - 120, Z_TOP - 30):
        revolve(ir, [(R_TANK + 3, z - 4), (R_TANK + 4, z), (R_TANK + 3, z + 4)], n=48)
    revolve(M_(X, 'band'), [(R_TANK + 1, Z_CAT + 150), (R_TANK + 1, Z_CAT + 230)], u_tiles=2, n=48, vlen=80)
    # cone roof + cap
    revolve(sh, [(R_TANK + 16, Z_TOP - 4), (R_CAP, Z_CAP)], u_tiles=12, n=48)
    disc(sh, R_TANK + 16, Z_TOP - 4, up=False, n=48)
    revolve(w, [(R_CAP, Z_CAP - 2), (R_CAP + 4, Z_CAP), (R_CAP, Z_CAP + 2)], n=24)
    disc(M_(X, 'floor'), R_CAP, Z_CAP, up=True, n=24)
    cylz(ir, 0, 0, Z_CAP, Z_CAP + 4, 10, n=8)          # finial base only: the cap stays a clear fighting top
    return X


def stair_posts(posts, z1):
    X = ML.Model(); w = M_(X, 'timber')
    for (x, y) in posts:
        rbox(w, (x - 8, y - 8, 0), (x + 8, y + 8, z1), r=1, k=1, tile=64)
    return X


def flume_trestle(points):
    """timber bents under the flume: pairs of posts with a cross beam, given (x, y, ztop, axis) per bent"""
    X = ML.Model(); w = M_(X, 'timber'); ir = M_(X, 'iron')
    for (x, y, zt, ax) in points:
        dx, dy = (0, 56) if ax == 'x' else (56, 0)
        for s in (-1, 1):
            rbox(w, (x + s * dx - 7, y + s * dy - 7, 0), (x + s * dx + 7, y + s * dy + 7, zt), r=1, k=1, tile=64)
        if zt > 120:
            bar(ir, (x - dx, y - dy, 20), (x + dx, y + dy, zt - 20), 3)
            bar(ir, (x + dx, y + dy, 20), (x - dx, y - dy, zt - 20), 3)
    return X


def smokestack(h=300, r=22):
    X = ML.Model(); b = M_(X, 'black')
    revolve(b, [(r, 0), (r, h - 40), (r * 1.6, h - 10), (r * 1.6, h), (r * 1.3, h)], n=16)
    revolve(M_(X, 'brass'), [(r + 2, h - 70), (r + 2, h - 58)], n=16)
    return X


def stern_wheel(R=130, W=160):
    """paddle wheel round the local x axis (func_rotating spawnflags 4); dyn shaders for the mover"""
    X = ML.Model(); w = M_(X, 'wheel_wood'); r = M_(X, 'wheel_red')
    for sx in (-W / 2, W / 2):
        P = [(sx, R * math.cos(a), R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
        tube(r, P, 6, nseg=6, caps=(False, False))
        for k in range(8):
            a = 2 * math.pi * k / 8
            bar(r, (sx, 0, 0), (sx, R * math.cos(a), R * math.sin(a)), 4)
    tube(r, [(-W / 2 - 12, 0, 0), (W / 2 + 12, 0, 0)], 10, nseg=8)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        c, s = math.cos(a), math.sin(a)
        p = np.array([0, c * (R - 26), s * (R - 26)])
        t = np.array([0, -s, c]); rr = np.array([0, c, s])
        pts = [p + q for q in (np.array([-W / 2, 0, 0]) - rr * 26, np.array([W / 2, 0, 0]) - rr * 26,
                               np.array([W / 2, 0, 0]) + rr * 26, np.array([-W / 2, 0, 0]) + rr * 26)]
        for side in (1, -1):
            off = t * 4 * side
            q = [x + off for x in pts]
            w.poly(q if side > 0 else q[::-1], t * side, [(0, 0), (1, 0), (1, 1), (0, 1)] if side > 0 else
                   [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def ore_carts(R, n, lift):
    """n ore carts on a circle of radius R round the origin, facing along the travel direction (CCW), each heaped with
    gold-flecked ore; IQM for the func_rotating"""
    X = ML.Model()
    for k in range(n):
        a = 2 * math.pi * k / n
        Rm = rot_z(a + math.pi / 2)
        Y = ML.Model(); b = M_(Y, 'cart_iron'); o = M_(Y, 'cart_ore'); wh = M_(Y, 'cart_black')
        rbox(b, (-60, -36, lift + 14), (60, 36, lift + 70), r=4, k=2, tile=64)
        ellipsoid(o, (0, 0, lift + 68), 54, 30, 22, nu=12, nv=6)
        for sx in (-38, 38):
            for sy in (-38, 38):
                tube(wh, [(sx, sy - 5, lift + 12), (sx, sy + 5, lift + 12)], 12, nseg=10)
        X.add_model(Y, Rm, (R * math.cos(a), R * math.sin(a), 0))
    return X


def rail_ring(R, z):
    """two steel rails + sleepers on a circle (static, lightmapped)"""
    X = ML.Model(); ir = M_(X, 'iron'); w = M_(X, 'wood_d')
    for rr in (R - 38, R + 38):
        revolve(ir, [(rr - 3, z), (rr - 3, z + 8), (rr + 3, z + 8), (rr + 3, z)], n=64)
    for k in range(48):
        a = 2 * math.pi * k / 48
        Y = ML.Model(); rbox(Y.mesh(TX_['wood_d']), (-8, -56, z), (8, 56, z + 4), r=1, k=1, tile=64)
        X.add_model(Y, rot_z(a), (R * math.cos(a), R * math.sin(a), 0))
    return X


def headframe(h=420):
    """mine headframe: A-frame of timbers with a sheave wheel on top"""
    X = ML.Model(); w = M_(X, 'timber'); ir = M_(X, 'iron')
    for sx in (-70, 70):
        bar(w, (sx, -90, 0), (sx, 0, h), 9); bar(w, (sx, 90, 0), (sx, 0, h), 9)
        bar(w, (sx, -60, h * 0.35), (sx, 60, h * 0.35), 6)
        bar(w, (sx, 0, 0), (sx, 0, h), 7)
    bar(w, (-80, 0, h), (80, 0, h), 8)
    P = [(0, 60 * math.cos(a), h + 64 + 60 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(ir, P, 5, nseg=6, caps=(False, False))
    for k in range(6):
        a = 2 * math.pi * k / 6
        bar(ir, (0, 0, h + 64), (0, 60 * math.cos(a), h + 64 + 60 * math.sin(a)), 3)
    bar(ir, (0, 0, h), (0, 0, h + 64), 6)
    return X


def mine_portal(w_in, h_in):
    """timber mine entrance frame: posts, cap beam, lagging boards (local: opening along x, centred, facing -y)"""
    X = ML.Model(); t = M_(X, 'timber')
    hw = w_in / 2
    rbox(t, (-hw - 20, -14, 0), (-hw, 14, h_in), r=2, k=1, tile=64)
    rbox(t, (hw, -14, 0), (hw + 20, 14, h_in), r=2, k=1, tile=64)
    rbox(t, (-hw - 36, -18, h_in), (hw + 36, 18, h_in + 28), r=2, k=1, tile=64)
    return X


def wagon():
    """covered wagon: bed box, four spoked wheels, canvas bonnet on hoops (local: long axis x, ~300 long)"""
    X = ML.Model(); w = M_(X, 'wood'); ir = M_(X, 'iron'); cv = M_(X, 'canvas')
    rbox(w, (-150, -56, 52), (150, 56, 96), r=2, k=1, tile=96)
    for sx, rr in ((-100, 50), (100, 50)):
        for sy in (-64, 64):
            P = [(sx + rr * math.cos(a), sy, rr + rr * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 21)]
            tube(ir, P, 4, nseg=6, caps=(False, False))
            for k in range(8):
                a = 2 * math.pi * k / 8
                bar(w, (sx, sy, rr), (sx + rr * math.cos(a), sy, rr + rr * math.sin(a)), 2.5, n=5)
    # bonnet: half-ellipse tunnel
    rows = []
    for t in np.linspace(0, math.pi, 13):
        rows.append((60 * math.cos(t), 96 + 70 * math.sin(t)))
    for i in range(len(rows) - 1):
        (y0, z0), (y1, z1) = rows[i], rows[i + 1]
        n = np.array([0, (y0 + y1) / 2, (z0 + z1) / 2 - 96]); n /= np.linalg.norm(n)
        cv.poly([(-140, y0, z0), (140, y0, z0), (140, y1, z1), (-140, y1, z1)][::-1], n,
                [(0, i / 12), (2, i / 12), (2, (i + 1) / 12), (0, (i + 1) / 12)][::-1])
    bar(w, (150, 0, 70), (250, 0, 40), 4)
    return X


def barrel(r=26, h=72):
    X = ML.Model(); s = M_(X, 'staves'); ir = M_(X, 'iron')
    revolve(s, [(r * 0.86, 0), (r, h / 2), (r * 0.86, h)], n=14, u_tiles=2)
    disc(M_(X, 'wood'), r * 0.86, h, up=True, n=14)
    for z in (h * 0.12, h * 0.88):
        rr = r * (0.86 + 0.14 * (1 - abs(z - h / 2) / (h / 2)))
        revolve(ir, [(rr + 1, z - 2), (rr + 1.5, z), (rr + 1, z + 2)], n=14)
    return X


def barrel_group():
    X = ML.Model()
    for (x, y) in ((0, 0), (56, 4), (26, 48)):
        X.add_model(barrel(), np.eye(3), (x, y, 0))
    X.add_model(barrel(), np.eye(3), (28, 18, 72))
    return X


def hay_bale(stack=1):
    X = ML.Model(); hy = M_(X, 'hay')
    for i in range(stack):
        rbox(hy, (-48 + 10 * i, -28, 40 * i), (48 + 10 * i, 28, 40 * i + 40), r=6, k=2, tile=64)
    return X


def trough():
    X = ML.Model(); w = M_(X, 'wood_d')
    rbox(w, (-90, -24, 0), (90, 24, 40), r=2, k=1, tile=64)
    M_(X, 'water_m').poly([(-84, -18, 36), (84, -18, 36), (84, 18, 36), (-84, 18, 36)], (0, 0, 1),
                           [(0, 0), (2, 0), (2, 0.5), (0, 0.5)])
    return X


def crate_stack(boxes):
    X = ML.Model(); w = M_(X, 'crate')
    for (mn, mx) in boxes: rbox(w, mn, mx, r=3, k=1, tile=64)
    return X


def geyser_cone(r=150, h=60, seed=1):
    """sinter mound with a vent; the jump pad sits in the vent (cone top flat at h)"""
    X = ML.Model(); s = M_(X, 'sinter')
    rng = np.random.default_rng(seed)
    prof = [(r, 0), (r * 0.8, h * 0.45), (r * 0.55, h * 0.85), (54, h), (40, h), (40, h - 4)]
    revolve(s, prof, n=24, u_tiles=3, rfun=lambda a, rr, z: rr * (1 + 0.06 * math.sin(3 * a + seed) * (z < h - 1)))
    return X


def steam_column(h=260, r=40):
    X = ML.Model(); s = M_(X, 'steam')
    for k in range(3):
        a = k * math.pi / 3
        c, sn = math.cos(a), math.sin(a)
        s.poly([(-r * c, -r * sn, 0), (r * c, r * sn, 0), (r * 1.6 * c, r * 1.6 * sn, h), (-r * 1.6 * c, -r * 1.6 * sn, h)],
               (-sn, c, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def windmill_tower(h=420):
    """steel windpump tower (static); the wheel is a separate mover"""
    X = ML.Model(); ir = M_(X, 'iron'); w = M_(X, 'wood')
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar(ir, (sx * 70, sy * 70, 0), (sx * 14, sy * 14, h), 4)
    for z in (100, 220, 330):
        f = 70 - (70 - 14) * z / h
        for (a, b) in (((-f, -f), (f, -f)), ((f, -f), (f, f)), ((f, f), (-f, f)), ((-f, f), (-f, -f))):
            bar(ir, (a[0], a[1], z), (b[0], b[1], z), 2.5, n=5)
    rbox(w, (-24, -24, h - 4), (24, 24, h + 6), r=1, k=1, tile=64)
    bar(ir, (0, 0, h + 6), (0, 0, h + 30), 6)
    bar(ir, (0, -10, h + 30), (0, -170, h + 30), 3)
    M_(X, 'red').poly([(0, -120, h + 0), (0, -170, h + 10), (0, -170, h + 60), (0, -120, h + 50)], (1, 0, 0),
                      [(0, 0), (1, 0), (1, 1), (0, 1)])
    return X


def windmill_wheel(R=90, n=16):
    """windpump wheel round the local y axis (func_rotating spawnflags 8)"""
    X = ML.Model(); b = M_(X, 'wheel_red'); w = M_(X, 'wheel_wood')
    P = [(R * math.cos(a), 0, R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 33)]
    tube(b, P, 3, nseg=5, caps=(False, False))
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        c2, s2 = math.cos(a + 0.22), math.sin(a + 0.22)
        p = [(14 * c, 0, 14 * s), (R * c, -6, R * s), (R * c2, 6, R * s2), (14 * c2, 0, 14 * s2)]
        w.poly(p, (0, -1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
        w.poly(p[::-1], (0, 1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    tube(b, [(0, -12, 0), (0, 12, 0)], 10, nseg=8)
    return X


def bar_counter(L=360, d=56, h=64):
    """saloon bar: counter with brass rail + back bar of bottles (local: counter along y, customers on +x)"""
    X = ML.Model(); w = M_(X, 'wood_d')
    rbox(w, (-d / 2, -L / 2, 0), (d / 2, L / 2, h - 6), r=2, k=1, tile=64)
    rbox(M_(X, 'wood'), (-d / 2 - 6, -L / 2 - 4, h - 6), (d / 2 + 6, L / 2 + 4, h), r=2, k=1, tile=64)
    bar(M_(X, 'brass'), (d / 2 + 14, -L / 2, 10), (d / 2 + 14, L / 2, 10), 2.5)
    for k in range(9):
        y = -L / 2 + 20 + k * (L - 40) / 8
        cylz(M_(X, 'bottles'), -d / 2 - 2, y, h, h + 22, 4, n=6)
    return X


def back_bar(L=360, h=180):
    X = ML.Model(); w = M_(X, 'wood_d')
    rbox(w, (-24, -L / 2, 0), (0, L / 2, 70), r=2, k=1, tile=64)
    for z in (100, 140):
        rbox(M_(X, 'wood'), (-24, -L / 2, z), (0, L / 2, z + 4), r=1, k=1, tile=64)
        for k in range(14):
            y = -L / 2 + 14 + k * (L - 28) / 13
            cylz(M_(X, 'bottles'), -10, y, z + 4, z + 26, 4, n=6)
    rbox(M_(X, 'gold'), (-6, -50, 150), (0, 50, h), r=1, k=1, tile=64)
    return X


def saloon_table():
    X = ML.Model(); w = M_(X, 'wood')
    cylz(M_(X, 'felt'), 0, 0, 36, 40, 34, n=16)
    revolve(w, [(34, 34), (36, 36), (34, 40)], n=16)
    bar(w, (0, 0, 0), (0, 0, 36), 5)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        x, y = 56 * math.cos(a), 56 * math.sin(a)
        rbox(w, (x - 11, y - 11, 18), (x + 11, y + 11, 22), r=1, k=1, tile=32)
        for (dx, dy) in ((-9, -9), (9, -9), (9, 9), (-9, 9)):
            bar(w, (x + dx, y + dy, 0), (x + dx, y + dy, 18), 1.5, n=4)
    return X


def shelves(L=300, h=200, d=36):
    X = ML.Model(); w = M_(X, 'wood')
    for s in (-1, 1): rbox(w, (-d / 2, s * L / 2 - 3, 0), (d / 2, s * L / 2 + 3, h), r=1, k=1, tile=64)
    for z in (4, 56, 108, 160):
        rbox(w, (-d / 2, -L / 2, z), (d / 2, L / 2, z + 4), r=1, k=1, tile=64)
        for k in range(8):
            y = -L / 2 + 20 + k * (L - 40) / 7
            col = ['crate', 'bottles', 'hay'][k % 3]
            rbox(M_(X, col), (-10, y - 10, z + 4), (10, y + 10, z + 30), r=1, k=1, tile=32)
    return X


def jail_bars(L, h):
    """bar grille along local y (thin: vertical bars every 14u)"""
    X = ML.Model(); b = M_(X, 'bars')
    n = int(L / 14)
    for k in range(n + 1):
        y = -L / 2 + k * L / n
        bar(b, (0, y, 0), (0, y, h), 1.6, n=5)
    for z in (4, h / 2, h - 4):
        bar(b, (0, -L / 2, z), (0, L / 2, z), 2.2, n=5)
    return X


def vault_door(r=56):
    X = ML.Model(); s = M_(X, 'iron'); g = M_(X, 'brass')
    # door disc standing in the x-z plane (local), thickness along y
    angs = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    for (y, nn) in ((0, -1), (14, 1)):
        a_ = angs if nn < 0 else angs[::-1]
        s.poly([(r * math.cos(a), y, r + r * math.sin(a)) for a in a_], (0, nn, 0),
               [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in a_])
    tube(s, [(r * math.cos(a), 7, r + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)], 7, nseg=6, caps=(False, False))
    for k in range(4):
        a = k * math.pi / 2
        bar(g, (0, -6, r), (24 * math.cos(a), -6, r + 24 * math.sin(a)), 2.5)
    return X


def forge():
    X = ML.Model(); st = M_(X, 'rock'); ir = M_(X, 'iron')
    rbox(st, (-70, -50, 0), (70, 50, 48), r=4, k=1, tile=64)
    M_(X, 'glow').poly([(-46, -30, 49), (46, -30, 49), (46, 30, 49), (-46, 30, 49)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    revolve(st, [(40, 48), (30, 150), (22, 260)], n=12, cx=0, cy=20)
    # anvil
    rbox(ir, (110, -14, 0), (150, 14, 26), r=2, k=1, tile=32)
    rbox(ir, (96, -18, 26), (170, 18, 40), r=3, k=1, tile=32)
    return X


def lantern_post(h=150):
    X = ML.Model(); w = M_(X, 'timber')
    rbox(w, (-5, -5, 0), (5, 5, h), r=1, k=1, tile=64)
    bar(w, (0, 0, h - 10), (0, 30, h - 10), 2)
    rbox(M_(X, 'glow'), (-6, 24, h - 36), (6, 36, h - 20), r=2, k=1, tile=16)
    return X


def hitching_rail(L=160):
    X = ML.Model(); w = M_(X, 'timber')
    for s in (-1, 1): rbox(w, (s * L / 2 - 5, -5, 0), (s * L / 2 + 5, 5, 44), r=1, k=1, tile=64)
    rbox(w, (-L / 2 - 8, -4, 40), (L / 2 + 8, 4, 48), r=1, k=1, tile=64)
    return X


def nugget_pile(seed=1, n=9):
    X = ML.Model(); g = M_(X, 'gold')
    rng = np.random.default_rng(seed)
    for k in range(n):
        x, y = rng.uniform(-40, 40, 2); r = rng.uniform(8, 18)
        ellipsoid(g, (x, y, r * 0.5), r, r * 0.8, r * 0.6, nu=8, nv=5)
    return X


def model_textures(TX):
    """extra model-only images (cart/wheel 'dyn' shaders for movers, crates, band, water)"""
    m = TX.material
    m('cart_iron', TL.metal((90, 84, 80), brushed=False, n=64), 'dyn')
    m('cart_ore', TL.grime(TL.dots((92, 84, 80), (240, 200, 90), n_dots=10, r=0.08, n=64), 0.2, 5), 'dyn')
    m('cart_black', ML.fill(32, (28, 26, 26), 2, 7), 'dyn')
    m('wheel_wood', boards((150, 40, 32), n=64, seed=21), 'dyn', two=True)
    m('wheel_red', ML.fill(32, (170, 46, 36), 2, 22), 'dyn')
    crate = TL.planks((176, 130, 80), n_planks=4, stagger=False, n=128)
    x, y = ML.xy(128)
    edge = (x < 0.07) | (x > 0.93) | (y < 0.07) | (y > 0.93) | (np.abs(x - y) < 0.05)
    m('crate', np.where(edge[..., None], C((110, 72, 40)), crate), shade=30)
    m('water_m', water_tex(64, col=(70, 120, 120)), shade=30)
    band = ML.text_img('GOLD RUSH GULCH  *  WATER PARK  *', 1024, 96, (150, 102, 60), (250, 236, 200), serif=True)
    m('band', band, lathe=True, shade=80)


# ================================================================================================= sky
SUN = (200, 55)


def desert_sky(out_dir, ns):
    """clear desert sky: deep blue zenith, pale hazy horizon, a few cumulus, distant violet buttes, nearer red mesas
    and a sand plain below; sun glow at SUN (matches q3map_sun in the shader)"""
    from woplib import skylib as SK
    far = SK.mesas(5, 14, 1.2, h=(2.5, 6), w=(10, 30))
    near = np.maximum(SK.mesas(9, 9, 0.6, h=(1.5, 4), w=(6, 18)), SK.ridge(13, 0.8, 0.5, 1.1))

    def colour(D, el, az):
        c = SK.gradient(el, horizon=(214, 210, 200), zenith=(48, 110, 196), power=0.55)
        c = c + SK.sun_glow(D, *SUN)
        cov = SK.clouds(D, el, az, band=(16, 10), cover=0.95)
        c = ML.lerp(c, C((252, 250, 246)) * np.clip(1.15 - el / 60, 0.8, 1.15)[..., None], cov[..., None])
        fa, ne = SK.at(far, az), SK.at(near, az)
        haze = np.clip(el / 6, 0, 1)[..., None]
        c = np.where((el < fa)[..., None], ML.lerp(C((168, 120, 130)), C((190, 150, 160)), haze), c)
        c = np.where((el < ne)[..., None], ML.lerp(C((150, 78, 52)), C((176, 98, 66)), haze), c)
        c = np.where((el < 0)[..., None], C((176, 132, 92)), c)
        return c
    return SK.write_cube(out_dir, ns, 'desert', colour)


def pier_piles(L, W, z0, z1, step=128):
    """timber piles along both sides of a pier (local: pier runs along x from 0 to L, width W centred on y=0)"""
    X = ML.Model(); t = M_(X, 'timber'); ir = M_(X, 'iron')
    for x in np.arange(32, L - 16, step):
        for s in (-1, 1):
            y = s * (W / 2 + 10)
            revolve(t, [(10, z0), (10, z1), (7, z1 + 6), (0.1, z1 + 8)], n=10, u_tiles=1, cx=x, cy=y)
            revolve(ir, [(11, z1 - 40), (11.5, z1 - 34), (11, z1 - 28)], n=10, cx=x, cy=y)
    return X


def pews(n=4, L=150, gap=72):
    X = ML.Model(); w = M_(X, 'wood_d')
    for i in range(n):
        y = i * gap
        rbox(w, (-L / 2, y, 16), (L / 2, y + 28, 22), r=1, k=1, tile=64)
        rbox(w, (-L / 2, y + 24, 22), (L / 2, y + 30, 52), r=1, k=1, tile=64)
        for s in (-1, 1): rbox(w, (s * L / 2 - 4, y, 0), (s * L / 2 + 4, y + 30, 22), r=1, k=1, tile=32)
    return X


def belfry(h=120):
    """little open bell frame for the chapel roof"""
    X = ML.Model(); w = M_(X, 'white'); g = M_(X, 'brass'); sh = M_(X, 'shingle')
    for sx in (-30, 30):
        for sy in (-30, 30):
            rbox(w, (sx - 5, sy - 5, 0), (sx + 5, sy + 5, h), r=1, k=1, tile=64)
    prism(sh, [(-42, -42), (42, -42), (42, 42), (-42, 42)], h, h + 8)
    revolve(sh, [(44, h + 8), (0.1, h + 60)], n=4, a0=45, a1=405)
    revolve(g, [(4, h - 10), (14, h - 30), (20, h - 52), (0.1, h - 52)], n=12)
    return X


def sluice(L=420):
    """gold sluice box on trestles: long riffled trough with a water stage (local: along x)"""
    X = ML.Model(); w = M_(X, 'wood'); t = M_(X, 'timber')
    for x in np.linspace(-L / 2 + 20, L / 2 - 20, 4):
        for sy in (-30, 30):
            rbox(t, (x - 6, sy - 6, 0), (x + 6, sy + 6, 70 + 10 * x / L), r=1, k=1, tile=64)
    rbox(w, (-L / 2, -40, 70), (L / 2, 40, 80), r=1, k=1, tile=64)
    for s in (-1, 1): rbox(w, (-L / 2, s * 40 - 4, 80), (L / 2, s * 40 + 4, 110), r=1, k=1, tile=64)
    M_(X, 'water_m').poly([(-L / 2, -36, 92), (L / 2, -36, 92), (L / 2, 36, 92), (-L / 2, 36, 92)], (0, 0, 1),
                           [(0, 0), (6, 0), (6, 1), (0, 1)])
    return X
