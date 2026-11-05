"""Custom MD3s, textures and the sky for wop_padsandcastle (Sandcastle Showdown). All geometry and art is original and
generated here. Origin = floor centre unless noted; "front" faces +x (misc_model angle turns it).

    import sc_models as SM
    SM.init(TX)            # the map's woplib.texlib.Textures
    SM.make_all()          # writes models/padsandcastle/*.md3 and their images, registers every model shader
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, grid_normals
from woplib import models as ML, texlib as TL
import layout as L

TX = None
xy, C, N3, noise, lerp = ML.xy, ML.C, ML.N3, ML.noise, ML.lerp


def init(tx):
    global TX
    TX = tx


# ================================================================================================= textures
def sand(base=(224, 198, 150), seed=1, ripple=0.0, n=256, specks=True, freq=5):
    """dry beach sand: grain, mottling, optional wind ripples, shell specks (tileable)"""
    x, y = xy(n)
    g = noise(n, 0.6, seed); m = noise(n, 7, seed + 1); big = noise(n, 22, seed + 2)
    c = np.zeros((n, n, 3), np.float32) + C(base) + g[..., None] * 9 + m[..., None] * 9 + big[..., None] * 7
    if ripple:
        r = np.sin(2 * math.pi * (freq * y + 0.22 * big + 0.05 * m))
        c += (np.clip(r, -1, 1) * ripple)[..., None] * C((1.0, 0.95, 0.85))
    if specks:
        sp = noise(n, 0.5, seed + 3)
        c = np.where((sp > 2.5)[..., None], c * 0.62, c)
        c = np.where((sp < -2.6)[..., None], c + C((40, 36, 30)), c)
    return c


def packed(base=(212, 180, 130), seed=11, n=256):
    """moulded castle sand: damp, fine strata and pat marks"""
    x, y = xy(n)
    big = noise(n, 18, seed); m = noise(n, 4, seed + 1)
    c = sand(base, seed + 2, 0, n, specks=True)
    strata = np.sin(2 * math.pi * (14 * y + 0.5 * big)) * 5
    c += strata[..., None]
    c *= ML.emboss(noise(n, 3, seed + 3) * 0.12 + m * 0.03, 1.0)[..., None] ** 0.5
    return c


def wood_stick(n=256, seed=21):
    """birch ice-block stick: pale wood, grain along u"""
    x, y = xy(n)
    w = noise(n, 6, seed)
    grain = np.sin(2 * math.pi * (28 * y + 1.5 * w)) * 0.5 + 0.5
    c = lerp(C((232, 208, 160)), C((206, 176, 126)), (grain ** 6)[..., None])
    return c + N3(n, 0.7, seed + 1, 5)


def paper(col, seed=31, n=128):
    return ML.fill(n, col, 4, seed) * (0.95 + 0.05 * noise(n, 1, seed + 2)[..., None])


def rock_tex(n=256, seed=41, base=(128, 118, 108)):
    idx, edge = ML.voronoi(n, 14, seed)
    tone = np.random.default_rng(seed).uniform(-18, 18, 14)[idx]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 1, seed + 1, 10) + N3(n, 8, seed + 2, 12)
    c = np.where((edge < 0.012)[..., None], c * 0.55, c)
    # barnacles and algae near the bottom of each tile
    alg = noise(n, 3, seed + 3)
    c = np.where((alg > 1.4)[..., None], lerp(c, C((70, 96, 52)), 0.6), c)
    bar = noise(n, 0.6, seed + 4)
    return np.where((bar > 2.3)[..., None], C((214, 210, 196)), c)


def gores(n=256):
    """beach ball: six coloured gores (u around), white caps"""
    x, y = xy(n)
    cols = [C(c) for c in ((230, 40, 40), (250, 250, 250), (40, 110, 230), (250, 210, 40), (250, 250, 250), (40, 170, 80))]
    k = np.minimum((x * 6).astype(int), 5)
    c = np.zeros((n, n, 3), np.float32)
    for i, col in enumerate(cols): c = np.where((k == i)[..., None], col, c)
    c = np.where(((y < 0.07) | (y > 0.93))[..., None], C((250, 250, 250)), c)
    return c + N3(n, 1, 3, 3)


def make_textures():
    """brush textures (TX.add) - model materials are registered in each builder through TX.material"""
    TX.add('sand', sand(seed=1, ripple=7))
    TX.add('sand_wet', sand((176, 150, 110), seed=2, ripple=5))
    TX.add('sand_sea', sand((190, 176, 136), seed=3, ripple=10, freq=4))
    TX.add('sand_packed', packed())
    TX.add('sand_dark', packed((168, 140, 100), seed=13))
    TX.add('stick', wood_stick())
    TX.add('rock', rock_tex())
    TX.add('grotto', rock_tex(seed=43, base=(70, 92, 110)))
    TX.add('water', ML.fill(128, (40, 120, 140), 6, 5), 'water', rgb=(0.20, 0.50, 0.58), alpha=0.55)
    foam = np.clip(noise(256, 1.2, 7) * 60 + noise(256, 5, 8) * 50 + 40, 0, 255)
    x, y = xy(256)
    foam = foam * (0.55 + 0.45 * np.sin(2 * math.pi * 3 * y) ** 2)
    TX.add('foam', np.repeat(foam[..., None], 3, 2), 'raw', check_tile=False, shader=(
        f'textures/{TX.ns}/foam\n{{\n\tqer_editorimage textures/{TX.ns}/foam\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n'
        '\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n\tcull none\n'
        f'\t{{\n\t\tmap textures/{TX.ns}/foam\n\t\tblendFunc GL_ONE GL_ONE\n\t\ttcMod scroll 0.01 0.07\n'
        '\t\trgbGen wave sin 0.5 0.25 0 0.18\n\t}\n}\n\n'))
    TX.add('towel', towel_tex(), check_tile=False)
    TX.add('sign_grotto', TL.label('MERMAID\'S GROTTO', 512, 128, (40, 70, 90), (240, 220, 160), serif=True), 'sign', check_tile=False)


# ================================================================================================= small mesh helpers
def bar(M, a, b, r, n=8):
    tube(M, [np.asarray(a, float), np.asarray(b, float)], r, nseg=n)


def stick_mesh(M, length, w=80, t=16, along='x'):
    """an ice-block stick lying flat, centred on the origin, rounded ends"""
    pts = []
    h = length / 2 - w / 2
    for a in np.linspace(-math.pi / 2, math.pi / 2, 9): pts.append((h + w / 2 * math.cos(a), w / 2 * math.sin(a)))
    for a in np.linspace(math.pi / 2, 3 * math.pi / 2, 9): pts.append((-h + w / 2 * math.cos(a), w / 2 * math.sin(a)))
    if along == 'y': pts = [(-y, x) for x, y in pts]
    prism(M, pts, -t / 2, t / 2, tile=length)


def teeth_mesh(M, tlist, tile=64):
    for poly, z0, z1 in tlist: prism(M, poly, z0, z1, tile=tile, bot=False)


# ================================================================================================= castle
def keep_shell():
    """the bucket-moulded keep: ribbed tapered shell with an arched door at +x and four arrow slits, the roof with its
    square hatch, crenellations on the rim. Origin = floor centre."""
    ps = TX.material('sand_castle', packed(), shade=60)
    pin = TX.material('sand_castle_in', packed((176, 146, 104), seed=17), shade=60)
    X = Model()
    Mo, Mi, Mj = X.mesh(ps), X.mesh(pin), X.mesh(ps)
    rows = [(266, 0), (266, 22), (256, 34), (254, 48), (244, 250), (236, 440), (232, 470), (240, 478), (240, 512)]

    def ribs(a, r, z):
        band = min(1.0, max(0.0, (z - 50) / 30)) * min(1.0, max(0.0, (440 - z) / 30))
        return r + 6.0 * max(0.0, math.cos(24 * a)) ** 4 * band
    Rr = 250.0
    door = [(-L.DOOR_W, 0), (L.DOOR_W, 0)] + [(L.DOOR_W * math.cos(t), L.DOOR_SPRING + L.DOOR_W * math.sin(t))
                                               for t in np.linspace(0, math.pi, 13)]
    polys = [door]
    for ang in (50, 130, -130, -50):
        u = Rr * math.radians(ang)
        polys.append([(u - 13, 290), (u + 13, 290), (u + 13, 380), (u, 398), (u - 13, 380)])
    ML.carved_shell(Mo, Mi, Mj, rows, 96, L.KEEP_THICK, polys, 0.0, Rr, deform=ribs, u_tiles=6, vlen=256,
                    close_top=False, close_bottom=False)
    # roof: a disc r 240 with the square hatch, top at 512, ceiling at 480, hatch sides
    h = L.KEEP_HOLE / 2
    for z, up, sh in ((L.KEEP_TOP, True, ps), (L.KEEP_H, False, pin)):
        P = np.zeros((2, 65, 3)); N = np.zeros_like(P); UV = np.zeros((2, 65, 2))
        for j, a in enumerate(np.linspace(0, 2 * math.pi, 65)):
            c, s = math.cos(a), math.sin(a)
            k = h / max(abs(c), abs(s))
            for i, rr in enumerate((k, 238.0)):
                P[i, j] = (rr * c, rr * s, z); N[i, j] = (0, 0, 1 if up else -1); UV[i, j] = (rr * c / 256, -rr * s / 256)
        X.mesh(sh).grid(P, N, UV)
    for (a, b) in (((-h, -h), (h, -h)), ((h, -h), (h, h)), ((h, h), (-h, h)), ((-h, h), (-h, -h))):
        X.mesh(pin).quad((a[0], a[1], L.KEEP_H), (b[0], b[1], L.KEEP_H), (b[0], b[1], L.KEEP_TOP), (a[0], a[1], L.KEEP_TOP), tile=128)
    teeth_mesh(X.mesh(ps), L.teeth(0, 0, 212, 240, L.KEEP_TOP, L.KEEP_TOP + 24, 16, 0.25))
    # pressed shells round the base band (decor, flush with the shell)
    sc = shell_material()
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        if abs(((a + math.pi) % (2 * math.pi)) - math.pi) < 0.5: continue          # not over the door
        scallop_mesh(X.mesh(sc), 26, R=rot_z(a) @ rot_axis((0, 1, 0), math.pi / 2 - 0.1), t=(253 * math.cos(a), 253 * math.sin(a), 70))
    return ML.save('keep', X)


def turret():
    """a small bucket turret with ribs and a crenellated rim (solid, walkable top at TURRET_H)"""
    ps = TX.material('sand_castle', packed(), shade=60)
    X = Model()
    rows = [(156, 0), (156, 16), (146, 28), (144, 40), (134, 262), (140, 268), (140, 272), (0, 272)]

    def ribs(a, r, z):
        if z < 44 or z > 258: return r
        return r + 5.0 * max(0.0, math.cos(16 * a)) ** 4
    revolve(X.mesh(ps), rows, u_tiles=4, n=64, rfun=ribs)
    teeth_mesh(X.mesh(ps), L.teeth(0, 0, 118, 140, L.TURRET_H, L.TURRET_H + 24, 12, 0.25))
    return ML.save('turret', X)


def stick(name, length, w=80, t=16):
    m = TX.material('stick_m', wood_stick())
    X = Model(); stick_mesh(X.mesh(m), length, w, t)
    X.shift((0, 0, -t / 2))
    return ML.save(name, X)


def flag(team, rgb):
    """team flag on a tall ice-block stick: origin = foot of the stick (stuck 0..16 into the surface below)"""
    st = TX.material('stick_m', wood_stick())
    fl = TX.material('flag_' + team, flag_tex(rgb), shade=80, two=True, deform='wave 120 sin 0 6 0 0.9')
    X = Model()
    H = 640
    m = Mesh(); stick_mesh(m, H, 40, 12); X.mesh(st).add(m, rot_axis((0, 1, 0), -math.pi / 2), (0, 0, H / 2))
    # pennant: a grid so the wave deform bends it
    P = np.zeros((5, 9, 3)); Nn = np.zeros_like(P); UV = np.zeros((5, 9, 2))
    for i in range(5):
        for j in range(9):
            u = j / 8; v = i / 4
            P[i, j] = (8 + 300 * u, 0, H - 30 - 200 * v + (200 * v - 100) * u * 0.85)
            Nn[i, j] = (0, -1, 0); UV[i, j] = (u, v)
    X.mesh(fl).grid(P, Nn, UV)
    return ML.save('flag_' + team, X)


def flag_tex(rgb, n=256):
    c = paper(rgb, n=n)
    x, y = xy(n)
    c = np.where((np.abs(y - 0.5) < 0.07)[..., None], C((250, 246, 230)), c)
    c = np.where((((x - 0.22) ** 2 + (y - 0.5) ** 2) < 0.012)[..., None], C((250, 220, 60)), c)
    return c


# ================================================================================================= Mount Sandy
def mount():
    """two-tier sand mountain with the north-south tunnel. Origin = floor centre of the mountain."""
    ps = TX.material('sand_mount', packed((214, 186, 138), seed=23), shade=60)
    pd = TX.material('sand_tunnel', packed((160, 134, 96), seed=27), shade=40)
    st = TX.material('stick_m', wood_stick())
    X = Model()
    W, Ht = L.TUNNEL_W, L.TUNNEL_H
    rows = [(572, 0), (570, 10), (564, 24), (558, 168), (550, 184), (540, 192)]

    def lump(a, r, z):
        return r + 4 * math.sin(5 * a + 1.3) * math.sin(math.pi * min(1, z / 192))
    Rr = 560.0
    mouth = [(-W, 0), (W, 0), (W, Ht - 30), (W - 30, Ht), (-W + 30, Ht), (-W, Ht - 30)]
    junk = Model()
    back = [(u + math.pi * Rr, z) for (u, z) in mouth]                  # the south mouth, half a turn round
    ML.carved_shell(X.mesh(ps), junk.mesh('x'), junk.mesh('y'), rows, 120, 40, [mouth, back], 90.0, Rr, deform=lump,
                    u_tiles=10, vlen=256, close_top=False, close_bottom=False)
    disc(X.mesh(ps), 540, L.T1_H, up=True, n=96, r_in=296, uvscale=512)
    revolve(X.mesh(ps), [(306, L.T1_H), (302, L.T1_H + 12), (288, 380), (278, 394), (264, 400), (0, 400)], u_tiles=6, n=72)
    # tunnel: walls + a ceiling of ice-block sticks, shoring frames every 200u
    yl = math.sqrt(560 ** 2 - W ** 2) - 2
    for sx in (-1, 1):
        X.mesh(pd).quad((sx * W, -yl, 0), (sx * W, yl, 0), (sx * W, yl, Ht), (sx * W, -yl, Ht), tile=256, n=(-sx, 0, 0))
    X.mesh(pd).quad((-W, -yl, Ht), (W, -yl, Ht), (W, yl, Ht), (-W, yl, Ht), tile=256, n=(0, 0, -1))
    for yc in np.arange(-yl + 60, yl - 40, 200):
        for sx in (-1, 1):
            m = Mesh(); stick_mesh(m, Ht - 6, 40, 10)
            X.mesh(st).add(m, rot_axis((0, 1, 0), -math.pi / 2), (sx * (W - 6), yc, (Ht - 6) / 2))
        m = Mesh(); stick_mesh(m, 2 * W, 40, 10)
        X.mesh(st).add(m, np.eye(3), (0, yc, Ht - 6))
    return ML.save('mount', X)


# ================================================================================================= picnic
def parasol():
    """giant beach umbrella: striped canopy (r 880) on a white pole, origin = pole foot"""
    top = TX.material('parasol_top', TL.stripes((236, 70, 60), (250, 244, 232), n_stripes=2), shade=80)
    und = TX.material('parasol_under', TL.stripes((170, 52, 46), (190, 186, 176), n_stripes=2), shade=80)
    pole = TX.material('pole_white', TL.metal((236, 236, 232)), 'lms', v=0.12)
    X = Model()
    H, R = L.PARASOL_H, L.PARASOL_R
    zr = H - 230

    def scal(a, r, z): return r * (1 - 0.035 * (1 - abs(math.cos(4 * a))) * (r / R))
    revolve(X.mesh(top), [(R, zr), (R * 0.66, zr + 120), (R * 0.33, zr + 196), (40, H - 6), (0, H)], u_tiles=8, n=96, rfun=scal)
    revolve(X.mesh(und), [(0, H - 16), (40, H - 22), (R * 0.33, zr + 182), (R * 0.66, zr + 106), (R - 4, zr - 12)], u_tiles=8, n=96, rfun=scal)
    revolve(X.mesh(pole), [(22, 0), (22, H + 10), (34, H + 18), (30, H + 40), (0, H + 44)], u_tiles=1, n=16)
    revolve(X.mesh(pole), [(60, 0), (60, 24), (34, 40), (22, 44)], u_tiles=1, n=16)        # sand anchor collar
    for k in range(8):
        a = 2 * math.pi * k / 8
        c, s = math.cos(a), math.sin(a)
        bar(X.mesh(pole), (c * 24, s * 24, zr - 260), (c * R * 0.55, s * R * 0.55, zr + 92), 6, 6)
    return ML.save('parasol', X)


def towel_tex(n=512):
    x, y = xy(n)
    k = (x * 8).astype(int) % 4
    cols = [C((40, 160, 200)), C((250, 240, 200)), C((250, 150, 40)), C((250, 240, 200))]
    c = np.zeros((n, n, 3), np.float32)
    for i, col in enumerate(cols): c = np.where((k == i)[..., None], col, c)
    c *= (0.92 + 0.08 * np.sin(2 * math.pi * 128 * y)[..., None])          # terry weave
    return c + N3(n, 0.8, 9, 6)


def chilly_bin():
    """Kiwi chilly bin: blue body, white lid with handles, PADMAN label. Origin floor centre, long side along x."""
    bl = TX.material('bin_blue', TL.solid((36, 96, 190), 4, 3, 128), 'lms', v=0.10)
    wh = TX.material('bin_white', TL.solid((240, 240, 236), 3, 5, 128))
    lb = TX.material('bin_label', ML.text_img('PADMAN', 512, 128, (36, 96, 190), (250, 250, 250), serif=False))
    X = Model()
    w, d, h = L.BIN_W / 2, L.BIN_D / 2, L.BIN_H
    rbox(X.mesh(bl), (-w + 6, -d + 6, 0), (w - 6, d - 6, h - 36), r=18, k=3, tile=256)
    rbox(X.mesh(wh), (-w, -d, h - 40), (w, d, h), r=12, k=3, tile=256)
    for sy in (-1, 1):
        X.mesh(lb).quad((-150 * sy, sy * (d - 6) + sy * 0.6, 120), (150 * sy, sy * (d - 6) + sy * 0.6, 120),
                        (150 * sy, sy * (d - 6) + sy * 0.6, 195), (-150 * sy, sy * (d - 6) + sy * 0.6, 195), n=(0, sy, 0))
    for sx in (-1, 1):
        x0 = sx * (w - 6); x1 = x0 + sx * 18
        rbox(X.mesh(wh), (min(x0, x1), -60, h - 110), (max(x0, x1), 60, h - 82), r=5, k=2)          # side handle
    return ML.save('chilly_bin', X)


def bodyboard(length, rise, w=256, t=20):
    """bodyboard leaning as a ramp: its low end on the sand at x 0, rising toward -x by `rise` over `length`.
    Returns the save info; the builder adds a matching weapclip slab."""
    bd = TX.material('board', board_tex(), shade=40)
    X = Model()
    m = Mesh()
    L_ = math.hypot(length, rise)
    pts = []
    for a in np.linspace(-math.pi / 2, math.pi / 2, 9): pts.append((L_ - w / 2 + w / 2 * math.cos(a) * 0.6, w / 2 * math.sin(a)))
    pts += [(0, w / 2), (0, -w / 2)]
    prism(m, pts, -t, 0, tile=L_)
    ang = math.atan2(rise, length)
    X.mesh(bd).add(m, rot_z(math.pi) @ rot_axis((0, 1, 0), -ang), (0, 0, 0))
    return ML.save('bodyboard', X)


def board_tex(n=256):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((250, 210, 40))
    c = np.where((np.abs(y - 0.5) < 0.12)[..., None], C((30, 30, 40)), c)
    c = np.where((np.abs(y - 0.5) < 0.04)[..., None], C((230, 60, 120)), c)
    return c + N3(n, 1, 4, 4)


def beach_bag():
    f = TX.material('bag', TL.stripes((40, 70, 150), (240, 236, 220), n_stripes=6, vertical=False))
    rope = TX.material('rope', TL.solid((210, 190, 150), 6, 7, 64))
    X = Model()
    rbox(X.mesh(f), (-150, -70, 0), (150, 70, 230), r=40, k=3, tile=230)
    for sx in (-1, 1):
        tube(X.mesh(rope), [(sx * 90, -60, 220), (sx * 70, -40, 330), (sx * 70, 40, 330), (sx * 90, 60, 220)], 7, nseg=6)
    return ML.save('beach_bag', X)


def sunscreen():
    lb = TX.material('sunscreen', sunscreen_tex())
    cap = TX.material('cap_orange', TL.solid((250, 140, 30), 3, 9, 64))
    X = Model()
    rbox(X.mesh(lb), (-80, -32, 0), (80, 32, 52), r=22, k=3, tile=160)
    rbox(X.mesh(cap), (80, -24, 4), (120, 24, 48), r=10, k=2, tile=64)
    return ML.save('sunscreen', X)


def sunscreen_tex():
    c = ML.text_img('SPF 50', 256, 128, (250, 250, 245), (250, 120, 20), serif=False)
    return c


def sunnies():
    fr = TX.material('sunnies_frame', TL.solid((30, 30, 34), 2, 11, 64), 'lms', v=0.2)
    gl = TX.material('sunnies_lens', TL.solid((20, 40, 60), 2, 13, 64), 'lms', v=0.45)
    X = Model()
    for sx in (-1, 1):
        rbox(X.mesh(gl), (sx * 70 - 52, -38, 0), (sx * 70 + 52, 38, 8), r=3, k=1)
        rbox(X.mesh(fr), (sx * 70 - 58, -44, 0), (sx * 70 + 58, -36, 12), r=2, k=1)
    rbox(X.mesh(fr), (-22, 26, 4), (22, 34, 12), r=2, k=1)
    for sx in (-1, 1): rbox(X.mesh(fr), (sx * 128 - 4, -40, 0), (sx * 128 + 4, 200, 8), r=2, k=1)
    return ML.save('sunnies', X)


# ================================================================================================= beach props
def spade():
    """kid's spade stuck in the sand: blade buried 40u, handle leaning 12 deg toward +x. Origin = where it enters."""
    rd = TX.material('spade_red', TL.solid((220, 40, 40), 3, 15, 64), 'lms', v=0.12)
    yl = TX.material('spade_yellow', TL.solid((250, 200, 40), 3, 17, 64), 'lms', v=0.10)
    X = Model()
    R = rot_axis((0, 1, 0), math.radians(12))
    m = Mesh()
    # blade: a shallow scoop 120 wide, 140 tall (its lower part under the sand)
    P = np.zeros((6, 9, 3)); Nn = np.zeros_like(P); UV = np.zeros((6, 9, 2))
    for i in range(6):
        for j in range(9):
            u = j / 8 * 2 - 1; v = i / 5
            w = 60 * (1 - 0.25 * v ** 2)
            P[i, j] = (-14 * (1 - u * u), u * w, -40 + 150 * v)
            Nn[i, j] = (1, 0, 0); UV[i, j] = (u, v)
    m.grid(P, -grid_normals(P), UV)
    m2 = Mesh(); m2.grid(P + [2, 0, 0], grid_normals(P), UV)
    m.add(m2)
    X.mesh(rd).add(m, R, (0, 0, 0))
    h = Mesh()
    tube(h, [(0, 0, 100), (0, 0, 470)], 14, nseg=10)
    tube(h, [(0, -50, 470), (0, 50, 470)], 12, nseg=8)
    X.mesh(yl).add(h, R, (0, 0, 0))
    return ML.save('spade', X)


def bucket(name, col, lying=False):
    """kid's bucket (r 110 top, 86 bottom, 176 tall) with a handle, full of sand; lying=True: on its side, mouth +x"""
    b = TX.material('bucket_' + name, TL.solid(col, 3, 19, 64), 'lms', v=0.10)
    sd = TX.material('sand_fill', sand((200, 172, 126), seed=5, n=128))
    X = Model()
    m = Mesh()
    revolve(m, [(0, 0), (86, 0), (110, 176), (116, 180), (116, 186), (104, 186), (100, 176), (80, 6), (0, 6)], u_tiles=2, n=32)
    tube(m, [(0, -108, 160)] + [(0, -108 * math.cos(t), 160 + 90 * math.sin(t)) for t in np.linspace(0.1, math.pi - 0.1, 9)] + [(0, 108, 160)], 5, nseg=6)
    s = Mesh(); disc(s, 100, 150, up=True, n=32)
    if lying:
        R = rot_axis((0, 1, 0), math.pi / 2)
        X.mesh(b).add(m, R, (-90, 0, 116)); X.mesh(sd).add(s, R, (-90, 0, 116))
    else:
        X.mesh(b).add(m); X.mesh(sd).add(s)
    return ML.save('bucket_' + name + ('_lying' if lying else ''), X)


def beach_ball(r=150):
    b = TX.material('ball', gores(), shade=89)
    X = Model(); sphere(X.mesh(b), (0, 0, r), r, nu=32, nv=16)
    return ML.save('beach_ball', X)


def jandal(team, col):
    """a pair of jandals (flip-flops): origin floor centre"""
    so = TX.material('jandal_' + team, TL.solid(col, 3, 23, 64))
    stp = TX.material('jandal_strap', TL.solid((245, 245, 240), 2, 25, 64))
    X = Model()
    for k, (y, a) in enumerate(((-70, 0.12), (75, -0.08))):
        m = Mesh()
        outline = [(math.cos(t) * 112 + 6 * math.cos(2 * t), math.sin(t) * (42 if math.cos(t) > 0 else 34)) for t in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
        prism(m, outline, 0, 14, tile=224)
        st = Mesh()
        tube(st, [(-30, -30, 14), (50, 0, 30), (-30, 30, 14)], 5, nseg=6)
        X.mesh(so).add(m, rot_z(a), (0, y, 0)); X.mesh(stp).add(st, rot_z(a), (0, y, 0))
    return ML.save('jandals_' + team, X)


def crab():
    """red-orange shore crab ~260 wide, body 70..150 over the sand, faces +x"""
    sh = TX.material('crab', crab_tex(), shade=70)
    dk = TX.material('crab_dark', TL.solid((120, 30, 20), 3, 27, 64))
    ey = TX.material('eye_black', TL.solid((12, 12, 14), 1, 29, 32), 'lms', v=0.4)
    X = Model()
    ellipsoid(X.mesh(sh), (0, 0, 110), 90, 120, 42, nu=24, nv=10, bump=lambda p, t: 1 + 0.04 * math.sin(6 * t))
    for sy in (-1, 1):
        for k in range(4):
            a = math.radians(-60 + k * 36) * 1.0
            base = np.array([-10 + 30 * math.cos(a) * 0, sy * 100, 100])
            mid = base + np.array([math.sin(a) * 60, sy * 90, 30])
            foot = base + np.array([math.sin(a) * 110, sy * 170, -100])
            tube(X.mesh(sh), [base, mid, foot], [12, 9, 3], nseg=6)
        # claws
        arm = [(60, sy * 70, 100), (130, sy * 110, 110), (180, sy * 80, 120)]
        tube(X.mesh(sh), arm, [14, 12, 10], nseg=8)
        ellipsoid(X.mesh(sh), (215, sy * 74, 124), 46, 28, 26, nu=12, nv=6)
        ellipsoid(X.mesh(dk), (262, sy * 62, 128), 18, 10, 9, nu=8, nv=4)
        ellipsoid(X.mesh(dk), (254, sy * 88, 118), 16, 9, 8, nu=8, nv=4)
        bar(X.mesh(sh), (70, sy * 24, 140), (84, sy * 30, 180), 5, 6)
        sphere(X.mesh(ey), (86, sy * 31, 186), 9, nu=8, nv=5)
    return ML.save('crab', X)


def crab_tex(n=128):
    c = ML.fill(n, (220, 80, 40), 8, 31)
    sp = noise(n, 1.5, 33)
    return np.where((sp > 1.6)[..., None], C((250, 170, 90)), c)


def seagull():
    """standing gull ~330 tall, faces +x"""
    wh = TX.material('gull_white', TL.solid((246, 246, 242), 3, 35, 64), shade=80)
    gr = TX.material('gull_grey', TL.solid((150, 156, 166), 3, 37, 64), shade=80)
    bk = TX.material('gull_black', TL.solid((26, 26, 30), 2, 39, 32))
    yl = TX.material('gull_beak', TL.solid((240, 190, 40), 2, 41, 32))
    lg = TX.material('gull_leg', TL.solid((230, 150, 120), 2, 43, 32))
    ey = TX.material('eye_black', TL.solid((12, 12, 14), 1, 29, 32), 'lms', v=0.4)
    X = Model()
    R = rot_axis((0, 1, 0), math.radians(-18))
    ellipsoid(X.mesh(wh), (0, 0, 180), 110, 60, 64, nu=20, nv=10, R=R)
    sphere(X.mesh(wh), (92, 0, 268), 42, nu=16, nv=8)
    revolve(Mtmp := Mesh(), [(0, 0), (12, 0), (8, 40), (0, 56)], n=10)
    X.mesh(yl).add(Mtmp, rot_axis((0, 1, 0), math.pi / 2 + 0.15), (126, 0, 262))
    for sy in (-1, 1):
        ellipsoid(X.mesh(gr), (-20, sy * 56, 196), 112, 16, 40, nu=16, nv=6, R=R)
        ellipsoid(X.mesh(bk), (-128, sy * 46, 218), 40, 10, 18, nu=10, nv=4, R=R)
        sphere(X.mesh(ey), (118, sy * 26, 280), 6, nu=6, nv=4)
        bar(X.mesh(lg), (0, sy * 22, 130), (8, sy * 26, 4), 7, 6)
        for a in (-0.5, 0, 0.5):
            bar(X.mesh(lg), (8, sy * 26, 4), (8 + 40 * math.cos(a), sy * 26 + 40 * math.sin(a), 3), 4, 5)
    ellipsoid(X.mesh(wh), (-120, 0, 168), 60, 30, 18, nu=10, nv=5, R=R)
    return ML.save('seagull', X)


def shell_material():
    return TX.material('scallop', scallop_tex(), shade=70)


def scallop_tex(n=128):
    x, y = xy(n)
    ribs = 0.5 + 0.5 * np.cos(2 * math.pi * 12 * x)
    c = lerp(C((240, 170, 150)), C((250, 226, 210)), ribs[..., None])
    return c * (0.85 + 0.15 * y[..., None]) + N3(n, 1, 45, 5)


def scallop_mesh(M, r, R=np.eye(3), t=(0, 0, 0)):
    """fan-shaped ribbed scallop shell lying flat (hinge at the origin, opening toward +x), radius r"""
    P = np.zeros((6, 17, 3)); UV = np.zeros((6, 17, 2))
    for i in range(6):
        for j in range(17):
            a = math.radians(-70 + 140 * j / 16); rr = r * i / 5
            rib = 0.05 * r * math.cos(12 * math.radians(-70 + 140 * j / 16) * 3) * (i / 5)
            P[i, j] = (rr * math.cos(a), rr * math.sin(a), 0.32 * r * math.sin(math.pi * i / 5 * 0.9) + rib)
            UV[i, j] = (j / 16, i / 5)
    m = Mesh(); m.grid(P, grid_normals(P) * (1 if grid_normals(P)[2, 8, 2] > 0 else -1), UV)
    M.add(m, R, t)


def scallop():
    X = Model(); scallop_mesh(X.mesh(shell_material()), 110)
    return ML.save('scallop', X)


def starfish():
    s = TX.material('starfish', star_tex(), shade=70)
    X = Model()
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = 130 if k % 2 == 0 else 46
        pts.append((r * math.cos(a), r * math.sin(a)))
    m = Mesh(); prism(m, pts, 0, 16, tile=260)
    for p in pts[::2]:
        sphere(m, (p[0] * 0.98, p[1] * 0.98, 10), 10, nu=8, nv=4)
    ellipsoid(m, (0, 0, 14), 50, 50, 14, nu=12, nv=5)
    X.mesh(s).add(m)
    return ML.save('starfish', X)


def star_tex(n=128):
    c = ML.fill(n, (240, 130, 60), 8, 47)
    sp = noise(n, 0.7, 49)
    return np.where((sp > 1.5)[..., None], C((250, 220, 160)), c)


def conch():
    """giant conch lying on its side, spire toward -x, the mouth (a tunnel 120 wide, 140 tall) opening at +x.
    Origin = floor centre. Collision: the builder adds weapclip round the body leaving the mouth open."""
    sh = TX.material('conch', conch_tex(), shade=70)
    pk = TX.material('conch_lip', TL.solid((246, 190, 170), 3, 51, 64), shade=70)
    dk = TX.material('conch_in', TL.solid((120, 70, 70), 3, 53, 64), shade=70)
    X = Model()
    # body: a lathe along x (spiral cone + whorls), then the flared lip round the mouth
    prof = []
    for k in range(41):
        x = -260 + 520 * k / 40
        t = k / 40
        r = 30 + 170 * t ** 0.8 * (1 + 0.08 * math.sin(t * 40))
        prof.append((r, x))
    m = Mesh()
    revolve(m, prof[:-1] + [(prof[-1][0] * 0.98, prof[-1][1])], u_tiles=3, n=40)
    Rx = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])        # lathe z -> world x (rotation, det +1)
    X.mesh(sh).add(m, Rx, (0, 0, 178))
    # mouth: flared lip ring + dark inner tube
    lip = Mesh(); revolve(lip, [(200, 0), (240, 12), (226, 30), (150, 26), (110, 10)], n=40, u_tiles=2)
    X.mesh(pk).add(lip, Rx, (262, 0, 178))
    inner = Mesh(); revolve(inner, [(110, 270), (100, 120), (70, 0)], n=32, inward=True)
    X.mesh(dk).add(inner, Rx, (0, 0, 178))
    # it lies half sunk in the sand: the axis sits 68u up and everything below the sand is flattened onto it, so the
    # base rests on the beach and the mouth's floor is flush with the sand (walk straight in)
    for M in X.m.values():
        for i, v in enumerate(M.V):
            v = v - (0, 0, 110)
            if v[2] < 0: v = np.array([v[0], v[1], 0.0]); M.N[i] = np.array([0, 0, 1.0]) if M is X.mesh(dk) else np.array([0, 0, -1.0])
            M.V[i] = v
    return ML.save('conch', X)


def conch_tex(n=256):
    x, y = xy(n)
    band = np.sin(2 * math.pi * (6 * y + 0.4 * noise(n, 10, 55)))
    c = lerp(C((236, 206, 170)), C((190, 130, 90)), (band > 0.4)[..., None] * 0.7)
    return c + N3(n, 1, 57, 6)


def boulder(name, r, seed, squash=0.6):
    rk = TX.material('rock_m', rock_tex(seed=61), shade=80)
    X = Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    bump = lambda p, t: 1 + 0.10 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]) + 0.06 * math.sin(5 * t + ph[2])
    ellipsoid(X.mesh(rk), (0, 0, r * squash * 0.5), r, r * 0.82, r * squash, nu=20, nv=10, bump=bump, flat_bottom=-r * squash * 0.5)
    return ML.save(name, X)


def driftwood():
    """bleached driftwood log 900 long along x, r 46..30, with two broken branch stubs; origin floor centre"""
    bk = TX.material('drift', drift_tex(), shade=70)
    X = Model()
    path = [(-450 + 900 * t, 30 * math.sin(t * 3), 46 - 14 * t) for t in np.linspace(0, 1, 12)]
    tube(X.mesh(bk), path, np.linspace(46, 30, 12), nseg=12, vlen=256)
    tube(X.mesh(bk), [(-120, 20, 50), (-60, 110, 120)], [20, 8], nseg=8)
    tube(X.mesh(bk), [(200, -10, 40), (280, -90, 70)], [16, 6], nseg=8)
    return ML.save('driftwood', X)


def drift_tex(n=256):
    x, y = xy(n)
    g = np.sin(2 * math.pi * (16 * y + 2 * noise(n, 8, 63))) * 0.5 + 0.5
    return lerp(C((196, 186, 170)), C((150, 140, 126)), (g ** 4)[..., None]) + N3(n, 1, 65, 6)


def grass_tuft(seed):
    g = TX.material('marram', TL.solid((150, 168, 90), 6, 67, 64), 'vl', two=True)
    X = Model()
    rng = np.random.default_rng(seed)
    for k in range(16):
        a = rng.uniform(0, 2 * math.pi); h = rng.uniform(160, 300); lean = rng.uniform(0.15, 0.6)
        base = np.array([math.cos(a) * 14, math.sin(a) * 14, -4])
        d = np.array([math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)])
        side = np.array([-math.sin(a), math.cos(a), 0]) * 5
        X.mesh(g).poly([base - side, base + side, base + d * h], np.cross(side, d), [(0, 0), (1, 0), (0.5, 1)])
    return ML.save(f'marram{seed}', X)


def dunes(name, x0, x1, y0, y1, h_of, seed, step=96):
    """heightfield dune sheet (scenery behind the clip). h_of(x, y) -> base height; noise added. Origin (0,0,0) world."""
    d = TX.material('dune', sand((228, 204, 158), seed=71, ripple=9, freq=6), sample=48)
    X = Model()
    xs = np.arange(x0, x1 + 1, step); ys = np.arange(y0, y1 + 1, step)
    nz = noise(128, 6, seed)
    P = np.zeros((len(ys), len(xs), 3)); UV = np.zeros((len(ys), len(xs), 2))
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            hz = h_of(x, y)
            if hz > 0:
                hz += 40 * nz[int(y / 23) % 128, int(x / 23) % 128] * min(1, hz / 120)
            P[i, j] = (x, y, max(0.0, hz)); UV[i, j] = (x / 512, -y / 512)
    N = grid_normals(P)
    if N[..., 2].mean() < 0: N = -N
    X.mesh(d).grid(P, N, UV)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    X.shift((cx, cy, 0))
    p = ML.save(name, X)
    return p, (cx, cy)


def clam():
    """giant clam with a glowing pearl (grotto centrepiece): a fluted bowl 420 x 300 resting on the floor, the lid open
    behind it. Origin = floor centre of the bowl (bowl spans y -50..250 in model space after the shift)."""
    sh = TX.material('clam', TL.stripes((170, 140, 196), (232, 212, 238), n_stripes=12), shade=70)
    pl = TX.material('pearl', TL.solid((250, 246, 240), 2, 73, 64), 'lms', v=0.5)
    X = Model()
    flute = lambda p, t: 1 + 0.05 * math.cos(12 * t)
    ellipsoid(X.mesh(sh), (0, 100, 50), 210, 150, 54, nu=48, nv=12, bump=flute, flat_bottom=-50)
    lid = Mesh()
    ellipsoid(lid, (0, 0, 0), 206, 146, 26, nu=48, nv=8, bump=flute)
    X.mesh(sh).add(lid, rot_axis((1, 0, 0), 1.15), (0, 250, 150))
    sphere(X.mesh(pl), (0, 100, 132), 30, nu=20, nv=10)
    return ML.save('clam', X)


Model = ML.Model


def make_all():
    """every model, in an order that registers all shaders before the .shader file is written"""
    keep_shell(); turret()
    stick('stick_bridge', 448); stick('stick_gate', 220, 96, 16); stick('stick_postern', 160, 96, 16)
    for team, rgb in (('red', (220, 40, 40)), ('blue', (40, 90, 220)), ('yellow', (250, 200, 30))): flag(team, rgb)
    mount(); parasol(); chilly_bin(); beach_bag(); sunscreen(); sunnies()
    spade(); bucket('yellow', (250, 200, 40)); bucket('green', (60, 180, 90), lying=True); bucket('pink', (240, 100, 160))
    beach_ball(); jandal('red', (220, 50, 50)); jandal('blue', (50, 100, 220)); crab(); seagull(); scallop(); starfish()
    conch(); driftwood(); clam()
    for k, (r, s) in enumerate(((150, 1), (110, 2), (190, 3), (90, 4), (130, 5))): boulder(f'rock{k}', r, s)
    for s in range(1, 5): grass_tuft(s)


# ================================================================================================= sky
SUN = (80, 58)          # yaw toward the sun (north-east: a Kiwi summer afternoon), elevation


def make_sky(out_dir, ns, n=512):
    """beach sky: soft blue, a few fair-weather cumulus, the sea to the southern horizon with sun glitter, green
    headlands and pohutukawa-dark dunes along the northern half. Faces rt=+x lf=-x bk=+y ft=-y."""
    d = os.path.join(out_dir, 'env', ns); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    Uu, Vv = np.meshgrid(u, u)
    s = 2 * Uu - 1; t = 1 - 2 * Vv
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}
    A = np.linspace(-180, 180, 4097)
    land = np.zeros_like(A)
    for (ca, h, w) in ((40, 3.0, 40), (90, 1.6, 50), (140, 4.5, 30), (10, 2.2, 18), (170, 2.6, 22), (-178, 1.2, 8)):
        land = np.maximum(land, h * np.clip(1 - ((A - ca) / w) ** 2, 0, 1) ** 0.6 * (1 + 0.12 * np.sin(A * 0.4 + ca)))
    sy, se = math.radians(SUN[0]), math.radians(SUN[1])
    sd = np.array([math.cos(se) * math.cos(sy), math.cos(se) * math.sin(sy), math.sin(se)])
    cl = [noise(512, 10, 21 + k) for k in range(3)]
    gl = noise(512, 0.6, 33)
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        zz = Dn[..., 2]
        az = np.degrees(np.arctan2(Dn[..., 1], Dn[..., 0]))
        el = np.degrees(np.arcsin(np.clip(zz, -1, 1)))
        up = np.clip(zz, 0, 1)
        c = lerp(C((190, 222, 240)), C((52, 126, 214)), (up ** 0.5)[..., None])
        cs = np.clip(Dn @ sd, 0, 1)
        c = c + (cs ** 40 * 90 + cs ** 600 * 420)[..., None] * C((1.0, 0.96, 0.84))
        uu = (az + 180) / 360 * 4; vv = el / 40
        ci = (np.floor(uu * 512) % 512).astype(int); cj = (np.floor(np.clip(vv, 0, 0.999) * 511)).astype(int)
        cn = cl[0][cj, ci] * 0.6 + cl[1][(cj * 3) % 512, (ci * 3) % 512] * 0.4
        band = np.exp(-((el - 14) / 9) ** 2)
        cov = np.clip(cn * 0.9 + band * 0.7 - 0.85, 0, 1)
        shade = np.clip(1.15 - (el - 6) / 40, 0.75, 1.15)
        c = lerp(c, C((252, 252, 250)) * shade[..., None], (cov * (el > 0.8))[..., None])
        # northern land: dunes + green headlands above and below the horizon (az 0..180 is the north half)
        lh = np.interp(az, A, land)
        north = (az > -5) & (az < 185)
        landc = lerp(C((74, 110, 70)), C((120, 150, 120)), np.clip(el[..., None] / 5, 0, 1))
        c = np.where(((el < lh) & (el >= 0) & north)[..., None], landc, c)
        dunec = lerp(C((214, 196, 150)), C((120, 130, 90)), np.clip(-el[..., None] / 20, 0, 1))
        c = np.where(((el < 0) & north)[..., None], dunec, c)
        # the sea in the south half, sun glitter
        sea = (el < 0) & ~north
        depth = np.clip(-el / 25, 0, 1)
        seac = lerp(C((96, 170, 196)), C((24, 86, 128)), depth[..., None])
        # sun glitter: fine speckle concentrated toward the sun's azimuth, fading with depth
        gi = (np.floor((az + 180) / 360 * 2048) % 512).astype(int); gj = (np.floor(np.clip(-el, 0, 89.9) * 23) % 512).astype(int)
        da = np.abs(((az - SUN[0] + 180) + 180) % 360 - 180)
        glit = np.clip(gl[gj, gi] - 1.2, 0, 2) * 60 * (1 - depth) * (0.3 + 0.7 * np.exp(-(da / 40) ** 2))
        c = np.where(sea[..., None], seac + glit[..., None], c)
        ML.img(c).save(os.path.join(d, f'beach_{k}.jpg'), quality=94)
    cloud = np.clip(noise(512, 14, 41) * 0.7 + noise(512, 4, 42) * 0.3 - 0.45, 0, 2)
    ML.img(np.repeat((cloud * 180)[..., None], 3, 2)).save(os.path.join(d, 'clouds.jpg'), quality=90)
    return f'env/{ns}/beach'
