"""Custom MD3s / IQMs and textures for wop_padarcade (Midnight Arcade). All geometry, art and game names are original.
Origin = floor centre unless noted; "front" faces -y (toward the viewer standing south) unless noted.

    import ar_models as AM
    AM.init(TX); AM.make_textures(); AM.make_all()
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, grid_normals
from woplib import models as ML, texlib as TL
import layout as L

TX = None
xy, C, N3, noise, lerp = ML.xy, ML.C, ML.N3, ML.noise, ML.lerp
Model = ML.Model


def init(tx):
    global TX
    TX = tx


# ================================================================================================= textures
def carpet(n=512, seed=3):
    """cosmic arcade carpet: deep navy with neon triangles, squiggles, rings and stars (tileable)"""
    rng = np.random.default_rng(seed)
    im = Image.new('RGB', (n, n), (14, 12, 40))
    d = ImageDraw.Draw(im)
    cols = [(255, 60, 170), (40, 220, 255), (255, 220, 40), (120, 255, 90), (170, 90, 255)]
    for k in range(70):
        x, y = rng.uniform(0, n, 2); c = cols[k % 5]; s = rng.uniform(10, 26); kind = k % 4; a = rng.uniform(0, 6.28)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                X, Y = x + ox, y + oy
                if kind == 0:
                    d.polygon([(X + s * math.cos(a + i * 2.094), Y + s * math.sin(a + i * 2.094)) for i in range(3)], outline=c, width=3)
                elif kind == 1:
                    d.ellipse((X - s, Y - s, X + s, Y + s), outline=c, width=3)
                elif kind == 2:
                    d.line([(X + i * 6, Y + 8 * math.sin(i)) for i in range(7)], fill=c, width=3)
                else:
                    d.line((X - s * 0.5, Y, X + s * 0.5, Y), fill=c, width=2); d.line((X, Y - s * 0.5, X, Y + s * 0.5), fill=c, width=2)
    return np.asarray(im, np.float32) + N3(n, 0.6, seed + 1, 6)


def wall_tex(n=256):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((34, 18, 52)) + N3(n, 2, 7, 4)
    c = np.where((np.abs(y - 0.12) < 0.02)[..., None], C((255, 60, 170)), c)
    c = np.where((np.abs(y - 0.18) < 0.01)[..., None], C((40, 220, 255)), c)
    return c


def screen(game, n=256):
    """original pixel-game screen art for the cabinets"""
    rng = np.random.default_rng(len(game) * 7 + ord(game[0]))
    im = Image.new('RGB', (n, n), (6, 6, 16))
    d = ImageDraw.Draw(im)
    for k in range(40): d.point((rng.integers(0, n), rng.integers(0, n)), fill=(200, 200, 255))
    if game == 'blastronaut':
        for r in range(4):
            for c in range(7):
                x, y = 30 + c * 30, 40 + r * 24
                d.rectangle((x, y, x + 16, y + 10), fill=[(255, 80, 80), (255, 200, 40), (80, 255, 120), (80, 200, 255)][r])
        d.polygon([(118, 220), (138, 220), (128, 200)], fill=(240, 240, 255))
    elif game == 'padpong':
        d.rectangle((20, 90, 28, 150), fill=(255, 255, 255)); d.rectangle((228, 60, 236, 120), fill=(255, 255, 255))
        d.rectangle((120, 110, 130, 120), fill=(255, 255, 255))
        for y in range(0, n, 16): d.rectangle((126, y, 130, y + 8), fill=(120, 120, 120))
    else:   # duckdash
        for k in range(6):
            x = 20 + k * 40; y = 160 - (k % 2) * 30
            d.ellipse((x, y, x + 26, y + 20), fill=(255, 220, 40)); d.polygon([(x + 26, y + 8), (x + 36, y + 12), (x + 26, y + 14)], fill=(255, 140, 20))
        d.rectangle((0, 200, n, n), fill=(40, 120, 220))
    return np.asarray(im, np.float32)


def marquee(text, rgb, w=512, h=128):
    return ML.text_img(text, w, h, (12, 8, 24), rgb, serif=False, glow=rgb)


def fur(rgb, seed):
    return ML.fill(128, rgb, 12, seed) * (0.9 + 0.1 * noise(128, 0.5, seed + 3)[..., None])


def make_textures():
    TX.add('carpet', carpet(), steps='carpetsteps')
    TX.add('wall', wall_tex())
    TX.add('ceiling', TL.tiles((30, 28, 36), (20, 18, 26), cols=4, rows=4, grout_w=0.03))
    TX.add('cab_red', TL.solid((190, 30, 40), 3, 5, 128))
    TX.add('cab_black', TL.solid((24, 22, 30), 2, 7, 128))
    TX.add('chrome', TL.metal((200, 204, 212)))
    TX.add('lane_wood', TL.planks((200, 150, 90), n_planks=8, vertical=False), steps='woodsteps')
    TX.add('felt_blue', TL.solid((30, 70, 160), 3, 9, 128))
    TX.add('shelf', TL.planks((230, 220, 200), n_planks=3))
    TX.add('glass', TL.solid((170, 200, 210), 2, 61, 64), 'glass')
    TX.add('hockey', hockey_tex(), 'raw', check_tile=False, shader=(
        f'textures/{TX.ns}/hockey\n{{\n\tqer_editorimage textures/{TX.ns}/hockey\n\tsurfaceparm nomarks\n\tq3map_surfacelight 40\n'
        '\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
        f'\t{{\n\t\tmap textures/{TX.ns}/hockey\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
        f'\t{{\n\t\tmap textures/{TX.ns}/hockey\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.1 0 0.5\n\t}}\n}}\n\n'))
    TX.add('neon_sign', TL.neon('MIDNIGHT ARCADE', (255, 70, 190), w=1024, h=256), 'neon', rgb=(1, 0.3, 0.75), light=300, check_tile=False)
    TX.add('neon_prizes', TL.neon('PRIZES', (60, 230, 255), w=512, h=128), 'neon', rgb=(0.25, 0.9, 1), light=250, check_tile=False)
    TX.add('neon_scores', TL.neon('HALL OF HIGH SCORES', (255, 220, 40), w=1024, h=256), 'neon', rgb=(1, 0.85, 0.2), light=300, check_tile=False)
    TX.add('marq_skee', marquee('ROLL-A-BALL', (255, 200, 40)), 'sign', check_tile=False)
    TX.add('marq_claw', marquee('CLAW KING', (255, 80, 180)), 'sign', check_tile=False)
    TX.add('scoreboard', score_tex(), 'sign', check_tile=False)


def hockey_tex(n=256):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((210, 230, 250))
    holes = (np.hypot(((x * 16) % 1) - 0.5, ((y * 16) % 1) - 0.5) < 0.12)
    c = np.where(holes[..., None], C((120, 140, 170)), c)
    c = np.where((np.abs(x - 0.5) < 0.006)[..., None], C((230, 40, 60)), c)
    c = np.where((np.abs(np.hypot(x - 0.5, y - 0.5) - 0.15) < 0.006)[..., None], C((40, 90, 230)), c)
    return c


def score_tex():
    return ML.text_img('1  PADMAN   999990\n2  PADGIRL  871200\n3  BEACHBOY  640050\n4  ???       000000', 512, 256,
                       (8, 8, 20), (80, 255, 120), serif=False)


# ================================================================================================= helpers
def bar(M, a, b, r, n=8):
    tube(M, [np.asarray(a, float), np.asarray(b, float)], r, nseg=n)


def quad_img(M, c, nrm, right, *a):
    """a w x h picture quad centred on c, facing nrm (u runs along `right`, v down):
    quad_img(M, c, nrm, right, w, h) for upright pictures, quad_img(M, c, nrm, right, up, w, h) otherwise"""
    up, w, h = ((0, 0, 1),) + tuple(a) if len(a) == 2 else a
    c = np.asarray(c, float); r = np.asarray(right, float) * w / 2; u = np.asarray(up, float) * h / 2
    M.poly([c - r - u, c + r - u, c + r + u, c - r + u], nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


# ================================================================================================= claw machine
def claw_case():
    """Claw King upper half: chrome corner posts, glass panes (case z BASE_H..GLASS_TOP), the gantry under the roof,
    the roof box with the marquee. Origin = floor centre of the machine."""
    ch = TX.material('chrome_m', TL.metal((200, 204, 212)), 'lms', v=0.3)
    gl = TX.material('case_glass', TL.solid((160, 200, 220), 2, 11, 64), 'glass', c='0.07 0.09 0.11')
    rd = TX.material('cab_red_m', TL.solid((190, 30, 40), 3, 5, 128), 'lms', v=0.12)
    mq = TX.material('marquee_claw', marquee('CLAW KING', (255, 80, 180)), 'glow')
    X = Model()
    x0, y0, x1, y1 = L.CLAW
    z0, z1, zr = L.BASE_H, L.GLASS_TOP, L.ROOF_TOP
    for (x, y) in ((x0 + 16, y0 + 16), (x1 - 16, y0 + 16), (x0 + 16, y1 - 16), (x1 - 16, y1 - 16)):
        rbox(X.mesh(ch), (x - 18, y - 18, z0), (x + 18, y + 18, z1), r=6, k=2)
    for (a, b) in (((x0 + 34, y0 + 12), (x1 - 34, y0 + 12)), ((x0 + 34, y1 - 12), (x1 - 34, y1 - 12)),
                   ((x0 + 12, y0 + 34), (x0 + 12, y1 - 34)), ((x1 - 12, y0 + 34), (x1 - 12, y1 - 34))):
        X.mesh(gl).quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), tile=256)
    rbox(X.mesh(rd), (x0, y0, z1), (x1, y1, zr), r=10, k=2, tile=256)
    # marquee box on the back edge of the roof
    rbox(X.mesh(rd), (x0 + 40, y1 - 80, zr), (x1 - 40, y1 - 20, zr + 200), r=8, k=2, tile=256)
    quad_img(X.mesh(mq), (0, y1 - 81, zr + 100), (0, -1, 0), (1, 0, 0), 1000, 180)
    # gantry rails under the roof
    for x in (x0 + 60, x1 - 60):
        rbox(X.mesh(ch), (x - 10, y0 + 40, z1 - 40), (x + 10, y1 - 40, z1 - 20), r=4, k=1)
    rbox(X.mesh(ch), (x0 + 50, 80, z1 - 60), (x1 - 50, 120, z1 - 40), r=4, k=1)
    return ML.save('claw_case', X)


def claw_base_trim():
    """decoration on the base: coin door, joystick panel on the front (-y), the prize flap frame on the east face"""
    ch = TX.material('chrome_m', TL.metal((200, 204, 212)), 'lms', v=0.3)
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128))
    bt = TX.material('button_red', TL.solid((240, 40, 40), 2, 13, 64), 'glow')
    X = Model()
    x0, y0, x1, y1 = L.CLAW
    rbox(X.mesh(bk), (-200, y0 - 120, 300), (200, y0, 380), r=8, k=2)                   # control panel
    bar(X.mesh(ch), (-100, y0 - 70, 380), (-100, y0 - 70, 450), 6, 6); sphere(X.mesh(bt), (-100, y0 - 70, 456), 16, nu=10, nv=6)
    for x in (40, 100): sphere(X.mesh(bt), (x, y0 - 60, 384), 18, nu=10, nv=6)
    rbox(X.mesh(ch), (-80, y0 - 6, 120), (80, y0, 240), r=4, k=1)                       # coin door
    # flap frame on the east face round the opening (y FLAP, z 0..208)
    f0, f1 = L.FLAP
    for (a, b) in (((f0 - 16, 0), (f0, 224)), ((f1, 0), (f1 + 16, 224))):
        rbox(X.mesh(ch), (x1, a[0], a[1]), (x1 + 8, b[0], b[1]), r=2, k=1)
    rbox(X.mesh(ch), (x1, f0 - 16, 208), (x1 + 8, f1 + 16, 224), r=2, k=1)
    return ML.save('claw_trim', X)


def claw():
    """the claw on its cable (func_pendulum model2, pivot at the origin under the gantry); IQM"""
    ch = TX.material('chrome_dyn', TL.metal((200, 204, 212)), 'dyn')
    X = Model()
    bar(X.mesh(ch), (0, 0, 0), (0, 0, -300), 4, 6)
    revolve(X.mesh(ch), [(0, -300), (40, -310), (46, -350), (30, -370), (0, -372)], n=16)
    for k in range(3):
        a = 2 * math.pi * k / 3
        c, s = math.cos(a), math.sin(a)
        tube(X.mesh(ch), [(c * 36, s * 36, -360), (c * 90, s * 90, -420), (c * 70, s * 70, -500), (c * 40, s * 40, -520)], 9, nseg=6)
    ML.save_iqm('claw', X)


def teddy(name, rgb, s=1.0):
    """plush bear ~200 tall sitting (origin floor centre, faces -y)"""
    f = TX.material('fur_' + name, fur(rgb, len(name)), shade=89)
    bk = TX.material('eye_black', TL.solid((10, 10, 12), 1, 3, 32), 'lms', v=0.4)
    X = Model()
    M = X.mesh(f)
    ellipsoid(M, (0, 0, 70 * s), 60 * s, 52 * s, 70 * s, nu=14, nv=8)
    sphere(M, (0, -6 * s, 160 * s), 50 * s, nu=14, nv=8)
    for sx in (-1, 1):
        sphere(M, (sx * 40 * s, 0, 200 * s), 18 * s, nu=8, nv=5)
        ellipsoid(M, (sx * 58 * s, -20 * s, 90 * s), 20 * s, 18 * s, 36 * s, nu=8, nv=5, R=rot_axis((0, 1, 0), sx * 0.5))
        ellipsoid(M, (sx * 30 * s, -46 * s, 20 * s), 22 * s, 34 * s, 20 * s, nu=8, nv=5)
        sphere(X.mesh(bk), (sx * 16 * s, -50 * s, 170 * s), 6 * s, nu=6, nv=4)
    ellipsoid(M, (0, -50 * s, 150 * s), 18 * s, 12 * s, 14 * s, nu=8, nv=5)
    sphere(X.mesh(bk), (0, -62 * s, 154 * s), 6 * s, nu=6, nv=4)
    return X


def plush_pile():
    """the heap of prizes inside the claw case: teddies and balls sitting on the 16u collision plates (layout.PILE)"""
    X = Model()
    rng = np.random.default_rng(5)
    cols = [('pink', (250, 140, 190)), ('blue', (90, 150, 250)), ('yellow', (250, 220, 80)), ('green', (120, 220, 120)), ('purple', (180, 120, 240))]
    zb = L.BASE_H
    for li, ((x0, y0, x1, y1), h) in enumerate(L.PILE):
        z = zb + 16 * (li + 1)
        for k in range(10 - li * 2):
            nm, rgb = cols[(k + li) % 5]
            x = rng.uniform(x0 + 50, x1 - 50); y = rng.uniform(y0 + 50, y1 - 50)
            T = teddy(nm, rgb, rng.uniform(0.7, 1.0))
            X.add_model(T, rot_z(rng.uniform(-0.6, 0.6)), (x, y, z))
    return ML.save('plush_pile', X)


# ================================================================================================= skee-ball
def skee_rings():
    """target rings on the deck in front of a backboard (rings 40/100/200 points), origin = deck centre; faces -x"""
    rd = TX.material('ring_red', TL.solid((220, 40, 50), 2, 15, 64), 'lms', v=0.12)
    yl = TX.material('ring_yellow', TL.solid((250, 210, 40), 2, 17, 64), 'lms', v=0.12)
    X = Model()
    for (r, m) in ((150, rd), (100, yl), (54, rd)):
        tube(X.mesh(m), [(r * math.cos(a), r * math.sin(a), 8) for a in np.linspace(0, 2 * math.pi, 33)], 8, nseg=6, caps=(False, False))
    return ML.save('skee_rings', X)


def skee_balls():
    w = TX.material('ball_wood', TL.planks((210, 160, 100), n_planks=3), 'lms', v=0.08)
    X = Model()
    for k in range(9):
        sphere(X.mesh(w), ((k % 3) * 70 - 70, (k // 3) * 70 - 70, 34), 34, nu=10, nv=6)
    return ML.save('skee_balls', X)


# ================================================================================================= air hockey
def hockey_bits():
    """puck (r 90) and two mallets (r 110 with knobs) on the table; origin = table centre top"""
    bk = TX.material('puck', TL.solid((20, 20, 24), 2, 19, 64), 'lms', v=0.2)
    rd = TX.material('mallet_red', TL.solid((230, 40, 50), 2, 21, 64), 'lms', v=0.15)
    bl = TX.material('mallet_blue', TL.solid((40, 90, 230), 2, 23, 64), 'lms', v=0.15)
    X = Model()
    revolve(X.mesh(bk), [(0, 0), (90, 0), (90, 24), (0, 24)], n=24)
    for (x, m) in ((-320, rd), (320, bl)):
        m2 = Mesh(); revolve(m2, [(0, 0), (110, 0), (110, 30), (40, 40), (36, 110), (50, 130), (40, 150), (0, 152)], n=24)
        X.mesh(m).add(m2, np.eye(3), (x, 0, 0))
    return ML.save('hockey_bits', X)


# ================================================================================================= cabinets
def cabinet(game, title, rgb):
    """upright arcade cabinet (L.CAB_W x L.CAB_D x L.CAB_H): side panels, sloped screen, control panel, glowing
    marquee. Origin floor centre, faces -y."""
    sd = TX.material('cab_side_' + game, TL.stripes((30, 24, 50), tuple(int(v * 0.6) for v in rgb), n_stripes=4, vertical=False), shade=30)
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    sc = TX.material('screen_' + game, screen(game), 'glow')
    mq = TX.material('marquee_' + game, marquee(title, rgb), 'glow')
    bt = TX.material('button_red', TL.solid((240, 40, 40), 2, 13, 64), 'glow')
    ch = TX.material('chrome_m', TL.metal((200, 204, 212)), 'lms', v=0.3)
    X = Model()
    w, d, h = L.CAB_W / 2, L.CAB_D / 2, L.CAB_H
    # body: back box + front lower cabinet + side panels
    rbox(X.mesh(bk), (-w + 20, -d + 140, 0), (w - 20, d, h), r=6, k=1, tile=256)
    rbox(X.mesh(bk), (-w + 20, -d, 0), (w - 20, -d + 140, 540), r=6, k=1, tile=256)
    for sx in (-1, 1):
        m = Mesh()
        outline = [(-d, 0), (d, 0), (d, h), (-d + 110, h), (-d + 110, 1040), (-d + 40, 880), (-d + 150, 600), (-d, 560)]
        prism(m, outline, -10, 10, tile=256)
        X.mesh(sd).add(m, np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]]), (sx * (w - 10), 0, 0))
    # control panel and buttons
    P = [(-w + 20, -d + 0, 560), (w - 20, -d + 0, 560), (w - 20, -d + 150, 600), (-w + 20, -d + 150, 600)]
    X.mesh(bk).poly([np.array(p, float) for p in P], (0, -0.3, 0.95), [(0, 0), (1, 0), (1, 1), (0, 1)])
    bar(X.mesh(ch), (-100, -d + 60, 575), (-100, -d + 60, 640), 6, 6); sphere(X.mesh(bt), (-100, -d + 60, 646), 16, nu=8, nv=5)
    for k in range(3): sphere(X.mesh(bt), (40 + k * 50, -d + 70, 582), 14, nu=8, nv=5)
    # sloped screen
    a = np.array([0, -d + 150, 600.0]); b = np.array([0, -d + 40 + 70, 880.0])
    nrm = np.cross(b - a, (1, 0, 0)); nrm = nrm / np.linalg.norm(nrm)
    if nrm[1] > 0: nrm = -nrm
    c = (a + b) / 2 + nrm * 2
    up = (b - a) / np.linalg.norm(b - a)
    quad_img(X.mesh(sc), c, nrm, (1, 0, 0), up, 2 * w - 60, np.linalg.norm(b - a) - 20)
    # marquee
    quad_img(X.mesh(mq), (0, -d + 108, 1120), (0, -1, 0), (1, 0, 0), 2 * w - 50, 130)
    return ML.save('cab_' + game, X)


def racer():
    """sit-in racing cabinet: seat bucket, steering wheel, big screen and a marquee; origin floor centre, faces -y"""
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    rd = TX.material('cab_red_m', TL.solid((190, 30, 40), 3, 5, 128), 'lms', v=0.12)
    sc = TX.material('screen_race', race_tex(), 'glow')
    mq = TX.material('marquee_race', marquee('TURBO PAD', (80, 220, 255)), 'glow')
    X = Model()
    rbox(X.mesh(rd), (-300, -560, 0), (300, 560, 120), r=20, k=2, tile=256)              # base plinth (walkable)
    rbox(X.mesh(bk), (-300, 260, 120), (300, 560, 1100), r=10, k=2, tile=256)           # screen tower at the back (+y)
    quad_img(X.mesh(sc), (0, 258, 640), (0, -1, 0), (1, 0, 0), 520, 400)
    quad_img(X.mesh(mq), (0, 258, 960), (0, -1, 0), (1, 0, 0), 560, 140)
    rbox(X.mesh(rd), (-160, -360, 120), (160, -120, 220), r=30, k=3)                     # seat
    rbox(X.mesh(rd), (-160, -380, 220), (160, -320, 460), r=30, k=3)                     # seat back
    rbox(X.mesh(bk), (-200, 60, 120), (200, 240, 420), r=10, k=2)                        # dashboard
    m = Mesh(); tube(m, [(110 * math.cos(a), 0, 110 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)], 12, nseg=6, caps=(False, False))
    X.mesh(bk).add(m, rot_axis((1, 0, 0), -0.4), (0, 40, 470))
    return ML.save('racer', X)


def race_tex(n=256):
    x, y = xy(n)
    c = np.where((y < 0.45)[..., None], lerp(C((40, 20, 90)), C((250, 120, 60)), (y / 0.45)[..., None]), C((30, 30, 40)))
    road = (y > 0.45) & (np.abs(x - 0.5) < (y - 0.45) * 0.9)
    c = np.where(road[..., None], C((70, 70, 80)), c)
    c = np.where((road & (np.abs(x - 0.5) < 0.01) & (((y * 20) % 1) < 0.5))[..., None], C((250, 250, 250)), c)
    return c


def change_machine():
    gr = TX.material('change_grey', TL.metal((150, 156, 166)), 'lms', v=0.15)
    sc = TX.material('marquee_change', marquee('TOKENS', (255, 220, 40), 256, 64), 'glow')
    X = Model()
    rbox(X.mesh(gr), (-160, -140, 0), (160, 140, 900), r=10, k=2, tile=256)
    quad_img(X.mesh(sc), (0, -141, 760), (0, -1, 0), (1, 0, 0), 260, 70)
    return ML.save('change_machine', X)


# ================================================================================================= prize wheel, dance machine
def wheel():
    """prize wheel r 700 in the x-z plane facing -y (func_rotating about y); 16 coloured segments, pegs; IQM"""
    cols = [(240, 60, 60), (250, 210, 40), (60, 180, 240), (120, 220, 100)]
    X = Model()
    for k in range(16):
        m = TX.material(f'wheel_{k % 4}', TL.solid(cols[k % 4], 2, 31 + k % 4, 64), 'dyn')
        a0 = 2 * math.pi * k / 16; a1 = a0 + 2 * math.pi / 16
        P = [(0, -2, 0), (L.WHEEL_R * math.cos(a0), -2, L.WHEEL_R * math.sin(a0)), (L.WHEEL_R * math.cos(a1), -2, L.WHEEL_R * math.sin(a1))]
        X.mesh(m).poly([np.array(p, float) for p in P], (0, -1, 0), [(0.5, 0.5), (0, 0), (1, 0)])
        bar(X.mesh(TX.material('peg', TL.metal((220, 220, 230)), 'dyn')), (L.WHEEL_R * 0.95 * math.cos(a0), -2, L.WHEEL_R * 0.95 * math.sin(a0)),
            (L.WHEEL_R * 0.95 * math.cos(a0), -40, L.WHEEL_R * 0.95 * math.sin(a0)), 8, 5)
    rim = TX.material('wheel_rim', TL.metal((230, 200, 80)), 'dyn')
    tube(X.mesh(rim), [(L.WHEEL_R * math.cos(a), 0, L.WHEEL_R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)], 22, nseg=8, caps=(False, False))
    sphere(X.mesh(rim), (0, -20, 0), 80, nu=12, nv=8)
    ML.save_iqm('wheel', X)


def wheel_frame():
    """the static pointer + backing disc behind the wheel; origin = wheel centre"""
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    yl = TX.material('pointer', TL.solid((250, 230, 60), 2, 37, 64), 'glow')
    X = Model()
    m = Mesh(); revolve(m, [(0, 0), (L.WHEEL_R + 60, 0), (L.WHEEL_R + 60, 40), (0, 40)], n=48)
    X.mesh(bk).add(m, rot_axis((1, 0, 0), -math.pi / 2), (0, 58, 0))
    p = Mesh(); prism(p, [(-50, 0), (50, 0), (0, -130)], -20, 20, tile=128)
    X.mesh(yl).add(p, rot_axis((1, 0, 0), math.pi / 2), (0, -60, L.WHEEL_R + 120))
    return ML.save('wheel_frame', X)


def dance():
    """dance machine: a raised platform (L.DANCE_Z) with two players' 3x3 glowing arrow pads, a screen cabinet behind
    (+y) with a marquee; origin = platform centre floor"""
    x0, y0, x1, y1 = L.DANCE
    W, D = (x1 - x0) / 2, (y1 - y0) / 2
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    sc = TX.material('screen_dance', screen('duckdash'), 'glow')
    mq = TX.material('marquee_dance', marquee('PAD STEP', (120, 255, 120)), 'glow')
    X = Model()
    rbox(X.mesh(bk), (-W, -D, 0), (W, D - 160, L.DANCE_Z), r=4, k=1, tile=256)
    for p, cx in enumerate((-W / 2, W / 2)):
        for i in range(3):
            for j in range(3):
                if (i + j) % 2 == 0 and not (i == 1 and j == 1): continue
                if i == 1 and j == 1: continue
                arrow = TX.material(f'arrow_{p}_{i}{j}', arrow_tex((i, j)), 'glow', wave=f'wave square 0.5 0.5 {0.25 * ((i + j) % 4)} 1.2', tag=f'_{p}{i}{j}')
                c = (cx + (i - 1) * 120, -D + 260 + (j - 1) * 120, L.DANCE_Z + 1)
                quad_img(X.mesh(arrow), c, (0, 0, 1), (1, 0, 0), (0, 1, 0), 110, 110)
    rbox(X.mesh(bk), (-W, D - 160, 0), (W, D, 1300), r=10, k=2, tile=256)
    quad_img(X.mesh(sc), (0, D - 162, 760), (0, -1, 0), (1, 0, 0), 2 * W - 120, 500)
    quad_img(X.mesh(mq), (0, D - 162, 1160), (0, -1, 0), (1, 0, 0), 2 * W - 120, 160)
    return ML.save('dance', X)


def arrow_tex(ij, n=128):
    rgb = {(0, 1): (255, 60, 170), (2, 1): (255, 60, 170), (1, 0): (40, 220, 255), (1, 2): (40, 220, 255)}.get(ij, (255, 220, 40))
    im = Image.new('RGB', (n, n), (10, 10, 20)); d = ImageDraw.Draw(im)
    ang = {(0, 1): 180, (2, 1): 0, (1, 0): 270, (1, 2): 90}.get(ij, 45)
    a = math.radians(ang)
    pts = [(n / 2 + 44 * math.cos(a), n / 2 - 44 * math.sin(a)), (n / 2 + 30 * math.cos(a + 2.4), n / 2 - 30 * math.sin(a + 2.4)),
           (n / 2 + 30 * math.cos(a - 2.4), n / 2 - 30 * math.sin(a - 2.4))]
    d.polygon(pts, fill=rgb)
    return np.asarray(im, np.float32)


# ================================================================================================= photo booth
def booth():
    """photo booth (L.BOOTH footprint), red curtain over the doorway on its west side; origin floor centre"""
    x0, y0, x1, y1 = L.BOOTH
    W, D = (x1 - x0) / 2, (y1 - y0) / 2
    sd = TX.material('booth_side', TL.stripes((250, 220, 60), (40, 40, 50), n_stripes=6, vertical=True), shade=30)
    cu = TX.material('curtain', ML.fill(128, (170, 20, 30), 10, 41), shade=89, two=True)
    sc = TX.material('marquee_photo', marquee('PHOTOS 4 TOKENS', (255, 240, 120)), 'glow')
    X = Model()
    rbox(X.mesh(sd), (-W, -D, 0), (W, D, 1100), r=12, k=2, tile=512)
    # curtain: wavy sheet across the doorway (west face, y -120..120, z 40..900), nonsolid
    P = np.zeros((6, 13, 3)); UV = np.zeros((6, 13, 2))
    for i in range(6):
        for j in range(13):
            y = -130 + 260 * j / 12; z = 900 - 860 * i / 5
            P[i, j] = (-W - 6 - 12 * math.sin(j * 1.6), y, z); UV[i, j] = (j / 4, i / 2)
    X.mesh(cu).grid(P, grid_normals(P), UV)
    quad_img(X.mesh(sc), (-W - 2, 0, 1000), (-1, 0, 0), (0, -1, 0), 380, 90)
    return ML.save('booth', X)


def make_all():
    claw_case(); claw_base_trim(); claw(); plush_pile()
    skee_rings(); skee_balls(); hockey_bits()
    for g, t, rgb in (('blastronaut', 'BLASTRONAUT', (80, 220, 255)), ('padpong', 'PAD PONG', (255, 255, 255)),
                      ('duckdash', 'DUCK DASH', (255, 220, 40))):
        cabinet(g, t, rgb)
    racer(); change_machine(); wheel(); wheel_frame(); dance(); booth()
    for nm, rgb in (('pink', (250, 140, 190)), ('blue', (90, 150, 250)), ('yellow', (250, 220, 80))):
        ML.save('teddy_' + nm, teddy(nm, rgb, 1.0))
