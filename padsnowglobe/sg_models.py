"""Custom MD3s for wop_padsnowglobe (Padman's Snow Globe). All art original and procedural.

Scale: 48u per metre inside the globe (you are a villager). Outside the glass is a giant's desk at roughly 300u per cm
(mug, books, pencil, desk lamp, the window) - scenery only, out of reach. Local frames: z 0 = the surface a model
stands on. Mover models (train, sails, music-box drum) use 'dyn' shaders: they are model2 and get no lightmap.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import Mesh, rbox, tube, revolve, disc, prism, ellipsoid, sphere

TX = None
COLL = {}


def setup(tx):
    global TX
    TX = tx


def _img(w, h, bg): return Image.new('RGB', (w, h), tuple(int(v) for v in bg))
def _arr(im): return np.asarray(im, np.float32)
def font(sz, serif=True): return ML.font(sz, serif)
RX90 = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)        # local +z -> -y (det +1)
RY90 = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)        # local +z -> +x (det +1)


def rz(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def quad(M, pts, n, uv=((0, 1), (1, 1), (1, 0), (0, 0))):
    M.poly([np.array(p, float) for p in pts], n, list(uv))


def cone(M, r0, z0, r1, z1, n=16, u=2, cx=0.0, cy=0.0, cap=True):
    """frustum side (outward) + top cap when r1 > 0"""
    revolve(M, [(r0, z0), (r1, z1)] + ([(0, z1)] if cap and r1 > 0 else []), n=n, u_tiles=u, cx=cx, cy=cy)


def cylinder(M, r, z0, z1, n=16, u=2, cx=0.0, cy=0.0, top=True, bot=False):
    revolve(M, [(r, z0), (r, z1)] + ([(0, z1)] if top else []), n=n, u_tiles=u, cx=cx, cy=cy)
    if bot: disc(M, r, z0, up=False, n=n, cx=cx, cy=cy)


# ================================================================================================ textures
def sign_tex(text, bg, fg, w=1024, h=256, sub=None):
    im = _img(w, h, bg); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, w - 10, h - 10), 28, outline=fg, width=8)
    d.text((w / 2, h * (0.42 if sub else 0.5)), text, font=font(int(h * 0.4)), fill=fg, anchor='mm')
    if sub: d.text((w / 2, h * 0.78), sub, font=font(int(h * 0.16)), fill=fg, anchor='mm')
    return _arr(im)


def snow_tex(n=256, seed=1, base=(232, 238, 246)):
    a = TL.solid(base, 5, seed, n)
    fl = ML.noise(n, 3, seed + 1)
    a = a + fl[..., None] * ML.C((6, 6, 4))
    sp = ML.noise(n, 0.6, seed + 2)
    return np.clip(a + np.where((sp > 2.6)[..., None], ML.C((20, 20, 20)), 0), 0, 255)


def flakes_tex(n=256, seed=7, count=120):
    """additive snowflake dots (black = invisible)"""
    im = Image.new('RGB', (n, n), (0, 0, 0)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(count):
        x, y = r.uniform(0, n), r.uniform(0, n); s = r.uniform(0.8, 2.6); v = int(r.uniform(120, 255))
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x + ox - s, y + oy - s, x + ox + s, y + oy + s), fill=(v, v, v))
    return _arr(im)


def wallpaper_tex(n=256):
    a = TL.stripes((120, 40, 46), (104, 34, 40), 8, True, 0.2, 5, n)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for (x, y) in ((n / 4, n / 4), (3 * n / 4, 3 * n / 4)):
        d.ellipse((x - 10, y - 10, x + 10, y + 10), outline=(190, 150, 80), width=3)
    return _arr(im)


def plaque_tex(w=1024, h=256):
    im = _img(w, h, (190, 150, 70)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 12, w - 12, h - 12), 30, outline=(110, 80, 30), width=10)
    d.text((w / 2, h * 0.4), 'PADVILLE', font=font(110), fill=(80, 56, 20), anchor='mm')
    d.text((w / 2, h * 0.78), 'A WINTER SOUVENIR', font=font(40), fill=(80, 56, 20), anchor='mm')
    return _arr(im)


def clock_tex(n=256):
    im = _img(n, n, (236, 230, 210)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, n - 6, n - 6), outline=(40, 34, 30), width=10)
    for k in range(12):
        a = 2 * math.pi * k / 12
        d.line((n / 2 + 0.36 * n * math.cos(a), n / 2 + 0.36 * n * math.sin(a), n / 2 + 0.44 * n * math.cos(a),
                n / 2 + 0.44 * n * math.sin(a)), fill=(40, 34, 30), width=8)
    d.line((n / 2, n / 2, n / 2, n * 0.2), fill=(20, 20, 20), width=9)
    d.line((n / 2, n / 2, n * 0.7, n / 2), fill=(20, 20, 20), width=7)
    return _arr(im)


def present_tex(c1, c2, n=128):
    a = TL.solid(c1, 3, int(sum(c1)), n)
    a[:, n * 7 // 16: n * 9 // 16] = c2; a[n * 7 // 16: n * 9 // 16, :] = c2
    return a


def stained_tex(w=128, h=256, seed=3):
    """stained glass window (glow): leaded panes in reds/blues/golds with a pointed arch outline"""
    r = np.random.default_rng(seed)
    im = _img(w, h, (20, 16, 20)); d = ImageDraw.Draw(im)
    cols = [(200, 40, 40), (40, 70, 200), (230, 180, 40), (40, 150, 80), (150, 60, 170)]
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            c = cols[r.integers(len(cols))]
            d.rectangle((x + 2, y + 2, x + 30, y + 30), fill=c)
    return _arr(im)


def mats():
    M = TX.material
    # dome + room
    M('glassdome', TL.solid((40, 46, 52), 3, 1, 64), 'glass', c='0.07 0.08 0.09')
    M('flakes', flakes_tex(), 'add', tcmod='scroll 0.006 -0.05')
    M('flakes2', flakes_tex(seed=9, count=80), 'add', tcmod='scroll -0.004 -0.035')
    M('plinth_wood', TL.planks((96, 52, 30), 3, (60, 30, 16), 10, False, True, 2), 'lms', shade=60, v=0.18, sample=32)
    M('brass', TL.metal((200, 160, 70), False, 3), 'lms', shade=60, v=0.3)
    M('plaque', plaque_tex(), shade=30)
    M('mug', TL.solid((210, 70, 60), 3, 4, 128), 'lms', shade=80, v=0.2, sample=48)
    M('mug_in', TL.solid((60, 36, 24), 3, 5, 128), shade=80, sample=48)
    M('book1', TL.label('THE PADMAN ALMANAC', 1024, 128, (40, 70, 130), (230, 210, 140)), shade=20, sample=48)
    M('book2', TL.label('WINTER TALES', 1024, 128, (130, 40, 40), (240, 220, 160)), shade=20, sample=48)
    M('book3', TL.label('SNOW & ICE', 1024, 128, (40, 110, 70), (240, 230, 190)), shade=20, sample=48)
    M('pages', TL.stripes((236, 228, 206), (214, 206, 186), 32, False, 0.4, 6), shade=20, sample=48)
    M('pencil', TL.stripes((240, 190, 40), (220, 170, 30), 6, True, 0.3, 7), shade=50, sample=48)
    M('pencil_wood', TL.solid((220, 180, 130), 3, 8, 64), shade=50, sample=48)
    M('graphite', TL.solid((40, 40, 44), 3, 9, 64), shade=50, sample=48)
    M('lamp_green', TL.metal((40, 110, 70), False, 10), 'lms', shade=60, v=0.25, sample=48)
    M('lamp_bulb', TL.solid((255, 240, 200), 2, 11, 64), 'glow')
    M('frame_white', TL.solid((228, 224, 214), 3, 12, 128), shade=30, sample=48)
    # village
    M('snow_m', snow_tex(seed=13), shade=70)
    M('rock_m', TL.grime(TL.stone((120, 118, 126), cells=30, edge=(80, 78, 86), seed=14), 0.2, 15), shade=30)
    M('chapel_stone', TL.stone((178, 170, 156), cells=40, edge=(130, 122, 110), edge_w=0.02, seed=16), shade=30)
    M('slate', TL.tiles((70, 76, 90), (50, 54, 64), cols=6, rows=10, offset=0.5, vary=10, seed=17), shade=30)
    M('roof_snow', snow_tex(seed=18, base=(240, 244, 250)), shade=30)
    M('plaster', TL.solid((236, 226, 204), 4, 19, 128), shade=30)
    M('plaster_blue', TL.solid((150, 180, 210), 4, 20, 128), shade=30)
    M('plaster_pink', TL.solid((226, 170, 170), 4, 21, 128), shade=30)
    M('timber', TL.planks((120, 76, 44), 4, (70, 44, 24), 8, False, True, 22), shade=30)
    M('logs', TL.stripes((126, 82, 48), (96, 60, 34), 10, False, 0.5, 23), shade=30)
    M('boards_m', TL.planks((150, 108, 66), 6, (90, 62, 36), 10, True, False, 24), shade=30, steps='woodsteps')
    M('trim_white', TL.solid((240, 238, 232), 3, 25, 64), shade=30)
    M('trim_green', TL.solid((40, 110, 70), 3, 26, 64), shade=30)
    M('trim_red', TL.solid((180, 40, 40), 3, 27, 64), shade=30)
    M('gingerbread', TL.grime(TL.solid((170, 104, 52), 6, 28, 128), 0.15, 29), shade=30)
    M('icing', TL.solid((250, 250, 250), 2, 30, 64), shade=60)
    M('candy', TL.stripes((230, 40, 50), (250, 250, 250), 6, False, 0.1, 31), shade=60)
    M('window_glow', TL.solid((255, 210, 130), 2, 32, 64), 'glow')
    M('stained', stained_tex(), 'glow')
    M('clock', clock_tex(), shade=30)
    M('bronze', TL.metal((150, 110, 60), False, 33), 'lms', shade=60, v=0.25)
    M('iron', TL.metal((50, 52, 56), False, 34), 'lms', shade=60, v=0.15)
    M('lamp_glass', TL.solid((255, 226, 150), 2, 35, 64), 'glow')
    M('pine', TL.grime(TL.fabric((40, 86, 54), 48, 36), 0.25, 37), shade=60)
    M('bark', TL.stripes((90, 60, 40), (70, 46, 30), 10, True, 0.4, 38), shade=60)
    M('coal', TL.solid((26, 26, 28), 3, 39, 64), shade=60)
    M('carrot', TL.solid((240, 120, 30), 3, 40, 64), shade=60)
    M('scarf', TL.stripes((200, 30, 40), (240, 240, 240), 8, False, 0.1, 41), shade=60)
    M('hat_black', TL.fabric((30, 30, 34), 48, 42), shade=60)
    M('sail', TL.grime(TL.fabric((226, 216, 196), 32, 43), 0.15, 44), 'dyn', two=True)
    M('sail_frame', TL.planks((110, 74, 44), 2, (70, 46, 26), 8, False, True, 45), 'dyn')
    M('mill_white', TL.planks((236, 232, 222), 8, (180, 176, 168), 6, False, True, 46), shade=40)
    M('mill_cap', TL.tiles((60, 70, 90), (40, 46, 60), cols=8, rows=8, offset=0.5, seed=47), shade=40)
    M('millstone', TL.stone((150, 146, 140), cells=20, seed=48), shade=60)
    M('bauble_r', TL.solid((230, 40, 50), 2, 49, 32), 'glow')
    M('bauble_g', TL.solid((240, 200, 60), 2, 50, 32), 'glow', wave='sin 0.8 0.2 0 0.5')
    M('bauble_b', TL.solid((70, 140, 255), 2, 51, 32), 'glow', wave='sin 0.8 0.2 0.5 0.5')
    M('star', TL.solid((255, 230, 120), 2, 52, 32), 'glow', wave='sin 0.85 0.15 0 0.3')
    for k, (c1, c2) in enumerate((((200, 40, 50), (240, 210, 70)), ((40, 120, 70), (230, 40, 50)), ((50, 80, 190), (240, 240, 240)),
                                  ((230, 200, 60), (180, 40, 40)))):
        M(f'present{k}', present_tex(c1, c2), shade=40)
    M('sled', TL.planks((170, 110, 60), 3, (100, 60, 30), 8, False, False, 53), shade=40)
    M('runner', TL.metal((180, 40, 40), False, 54), 'lms', shade=60, v=0.2)
    M('ski', TL.stripes((220, 40, 40), (250, 250, 250), 4, False, 0.0, 55), shade=60)
    M('granite', TL.grime(TL.stone((120, 120, 130), cells=60, edge=(90, 90, 100), seed=56), 0.1, 57), shade=80)
    M('gravestone', TL.grime(TL.stone((150, 150, 156), cells=16, seed=58), 0.3, 59), shade=30)
    M('pew', TL.planks((110, 70, 40), 3, (70, 44, 24), 8, False, False, 60), shade=30)
    M('organ_pipe', TL.metal((200, 196, 186), False, 61), 'lms', shade=60, v=0.25)
    M('altar_cloth', TL.fabric((180, 30, 40), 32, 62), shade=30)
    M('wood_dark', TL.planks((80, 50, 30), 4, (50, 30, 18), 8, False, True, 63), shade=30)
    M('sack', TL.fabric((200, 180, 140), 32, 64), shade=60)
    M('fabric_green', TL.fabric((50, 110, 70), 32, 65), shade=60)
    M('garland', TL.grime(TL.fabric((40, 100, 50), 24, 66), 0.3, 67), shade=60)
    # mover models (dyn)
    M('loco_green', TL.solid((40, 110, 70), 3, 68, 128), 'dyn')
    M('loco_black', TL.metal((40, 40, 44), False, 69), 'dyn')
    M('loco_red', TL.solid((190, 40, 40), 3, 70, 128), 'dyn')
    M('brass_dyn', TL.metal((200, 160, 70), False, 71), 'dyn')
    M('wagon_wood', TL.planks((150, 104, 62), 4, (90, 60, 34), 8, False, False, 72), 'dyn')
    M('drum_brass', TL.metal((200, 160, 70), True, 73), 'dyn')
    M('pins', TL.metal((230, 230, 236), False, 74), 'dyn')
    M('gear_dyn', TL.metal((170, 140, 70), False, 75), 'dyn')
    # secret room
    M('velvet', TL.fabric((90, 20, 50), 32, 76), shade=30)
    M('comb', TL.metal((210, 210, 216), True, 77), 'lms', shade=60, v=0.3)


# ================================================================================================ the globe + the giant's desk
def glass_dome(R, cz, n=48):
    """the sphere above the snow (two-sided additive glass + reflection). Origin = sphere centre projected to z 0."""
    X = ML.Model()
    e0 = -math.asin(cz / R)
    rows = [(R * math.cos(e), cz + R * math.sin(e)) for e in np.linspace(e0, math.pi / 2, 18)]
    rows[-1] = (0.0, cz + R)
    ML.lathe(X.mesh(TX['glassdome']), rows, n=n, u_tiles=8)
    ML.save('glass_dome', X)
    return X


def snowfall(rs=(700, 1400, 2050), h=1700):
    """drifting snow: concentric additive cylinders of flakes scrolling down at two speeds (no collision)"""
    X = ML.Model()
    for k, r in enumerate(rs):
        ML.lathe(X.mesh(TX['flakes' if k % 2 == 0 else 'flakes2']), [(r, 40), (r, h)], n=32, u_tiles=max(2, round(2 * math.pi * r / 700)),
                 vlen=700)
    ML.save('snowfall', X)
    return X


def plinth(r_glass, z_desk):
    """the turned wooden base the globe sits in, brass rings and the PADVILLE plaque on the south side. Origin z 0 =
    the snow level (the base reaches down to the desk at z_desk)."""
    X = ML.Model()
    r0 = r_glass + 46
    prof = [(r0, 30), (r0 + 90, 30), (r0 + 110, -60), (r0 + 230, -90), (r0 + 250, z_desk + 20), (r0 + 290, z_desk)]
    revolve(X.mesh(TX['plinth_wood']), prof[::-1], n=64, u_tiles=24)
    revolve(X.mesh(TX['brass']), [(r0 + 92, 34), (r0 + 92, 26)][::-1], n=64, u_tiles=24)
    revolve(X.mesh(TX['brass']), [(r0 + 253, -260), (r0 + 253, -240)], n=64, u_tiles=24)
    # inner lip, flush with the glass foot, down under the snow
    revolve(X.mesh(TX['plinth_wood']), [(r0, -40), (r0, 30)], n=64, u_tiles=24, inward=True)
    # the plaque on the south face (flat panel just outside the conical side)
    zc = (-60 + z_desk) / 2 - 20; rr = r0 + 238
    w, hh = 900, 220
    quad(X.mesh(TX['plaque']), [(-w / 2, -rr - 30, zc - hh / 2), (w / 2, -rr - 30, zc - hh / 2), (w / 2, -rr - 30, zc + hh / 2),
                                (-w / 2, -rr - 30, zc + hh / 2)], (0, -1, 0))
    rbox(X.mesh(TX['brass']), (-w / 2 - 16, -rr - 28, zc - hh / 2 - 16), (w / 2 + 16, -rr + 40, zc + hh / 2 + 16), r=4, k=1, tile=256,
         faces='ewtb')
    ML.save('plinth', X)
    return X


def giant_mug(r=620.0, h=1500.0):
    X = ML.Model()
    revolve(X.mesh(TX['mug']), [(r - 30, 0), (r, 20), (r, h - 20), (r - 10, h), (r - 50, h)], n=40, u_tiles=4)
    revolve(X.mesh(TX['mug_in']), [(r - 50, h), (r - 50, 120)], n=40, u_tiles=4, inward=True)
    disc(X.mesh(TX['mug_in']), r - 50, h - 160, up=True, n=40)
    ring = [(r + 30 + 260 * math.sin(t), 0, h * 0.5 + 420 * math.cos(t)) for t in np.linspace(0.1, math.pi - 0.1, 20)]
    tube(X.mesh(TX['mug']), ring, 60, nseg=12)
    ML.save('giant_mug', X)
    return X


def book_stack():
    X = ML.Model()
    z = 0
    for k, (L, W, H, a) in enumerate(((2400, 1700, 360, 0), (2200, 1500, 300, 8), (2000, 1400, 260, -6))):
        b = Mesh()
        key = ('book1', 'book2', 'book3')[k]
        rbox(b, (-L / 2, -W / 2, 0), (L / 2, W / 2, H), r=20, k=2, tile=L, faces='tb')
        quad(b, [(-L / 2, -W / 2, 0), (L / 2, -W / 2, 0), (L / 2, -W / 2, H), (-L / 2, -W / 2, H)], (0, -1, 0))
        X.mesh(TX[key]).add(b, rz(a), (0, 0, z))
        p = Mesh()
        for (pts, n) in (([(L / 2, -W / 2, 0), (L / 2, W / 2, 0), (L / 2, W / 2, H), (L / 2, -W / 2, H)], (1, 0, 0)),
                         ([(-L / 2, W / 2, 0), (-L / 2, -W / 2, 0), (-L / 2, -W / 2, H), (-L / 2, W / 2, H)], (-1, 0, 0)),
                         ([(L / 2, W / 2, 0), (-L / 2, W / 2, 0), (-L / 2, W / 2, H), (L / 2, W / 2, H)], (0, 1, 0))):
            quad(p, pts, n)
        X.mesh(TX['pages']).add(p, rz(a), (0, 0, z))
        z += H
    ML.save('book_stack', X)
    return X


def giant_pencil(L=4200.0, r=150.0):
    """lying on the desk along local x, hexagonal body, sharpened tip at +x"""
    X = ML.Model()
    tmp = Mesh(); revolve(tmp, [(0, -L / 2), (r, -L / 2), (r, L / 2 - 500), (0, L / 2 - 500)], n=6, u_tiles=6)
    X.mesh(TX['pencil']).add(tmp, RY90, (0, 0, r))
    tmp = Mesh(); revolve(tmp, [(r, L / 2 - 500), (40, L / 2 - 60)], n=6, u_tiles=6)
    X.mesh(TX['pencil_wood']).add(tmp, RY90, (0, 0, r))
    tmp = Mesh(); revolve(tmp, [(40, L / 2 - 60), (0, L / 2)], n=6, u_tiles=2)
    X.mesh(TX['graphite']).add(tmp, RY90, (0, 0, r))
    ML.save('giant_pencil', X)
    return X


def desk_lamp(elbow=(0, -200, 3900), head=(1500, 1250, 4500)):
    """banker-style arm lamp: round base on the desk, two arm sections, a green shade with a glowing bulb.
    Origin = the base centre on the desk."""
    X = ML.Model()
    revolve(X.mesh(TX['lamp_green']), [(700, 0), (700, 80), (520, 160), (120, 220), (0, 220)], n=32, u_tiles=4)
    tube(X.mesh(TX['brass']), [(0, 0, 200), elbow], 70, nseg=10)
    tube(X.mesh(TX['brass']), [elbow, head], 60, nseg=10)
    sphere(X.mesh(TX['brass']), elbow, 110, nu=10, nv=8)
    d = np.array(head, float) - np.array(elbow, float); d /= np.linalg.norm(d)
    shade = Mesh(); revolve(shade, [(700, -500), (600, -440), (260, -60), (120, 0), (0, 40)], n=24, u_tiles=4)
    revolve(shade, [(0, 30), (110, -10), (250, -70), (590, -450), (690, -500)], n=24, u_tiles=4)
    # tilt the shade so it points down toward the globe (local -z = mostly down and toward -x -y)
    a = math.radians(35); tilt = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Rm = rz(225) @ tilt
    X.mesh(TX['lamp_green']).add(shade, Rm, head)
    b = Mesh(); sphere(b, (0, 0, -300), 160, nu=12, nv=8)
    X.mesh(TX['lamp_bulb']).add(b, Rm, head)
    ML.save('desk_lamp', X)
    return X


def window_frame(w, h, depth=160.0, bars=(3, 3)):
    """the giant room's window: white frame, sill and glazing bars, flat against the wall (origin = bottom centre)"""
    X = ML.Model()
    f = TX['frame_white']
    t = 120
    rbox(X.mesh(f), (-w / 2 - 60, -depth, 0), (w / 2 + 60, 40, t), r=10, k=1, tile=512)           # sill on the desk
    rbox(X.mesh(f), (-w / 2, 0, h - t), (w / 2, 30, h), r=6, k=1, tile=512)
    for x in (-w / 2, w / 2 - t):
        rbox(X.mesh(f), (x, 0, t), (x + t, 30, h - t), r=6, k=1, tile=512)
    for i in range(1, bars[0]):
        x = -w / 2 + w * i / bars[0]
        rbox(X.mesh(f), (x - 30, 4, t), (x + 30, 26, h - t), r=4, k=1, tile=512)
    for j in range(1, bars[1]):
        z = h * j / bars[1]
        rbox(X.mesh(f), (-w / 2 + t, 4, z - 30), (w / 2 - t, 26, z + 30), r=4, k=1, tile=512)
    ML.save('window_frame', X)
    return X


# ================================================================================================ village landmarks
def bandstand(r=170.0, floor=32.0, roof_z=272.0, roof_r=212.0, n=8, open_sides=(0, 2, 4, 6)):
    """octagonal Victorian bandstand: stepped base, 8 cast-iron posts, railings on the closed sides, a flat walkable
    roof (no parapet) with a scalloped valance and a tiny weathervane. Origin = ground at the centre."""
    X = ML.Model()
    a0 = math.pi / n
    poly = lambda rr: [(rr * math.cos(a0 + 2 * math.pi * k / n), rr * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]
    prism(X.mesh(TX['chapel_stone']), poly(r + 24), 0, floor - 16, tile=128)
    prism(X.mesh(TX['boards_m']), poly(r), floor - 16, floor, tile=128)
    post_r = r - 14
    for k in range(n):
        a = a0 + 2 * math.pi * k / n
        px, py = post_r * math.cos(a), post_r * math.sin(a)
        tube(X.mesh(TX['iron']), [(px, py, floor), (px, py, roof_z)], 6, nseg=8)
        sphere(X.mesh(TX['iron']), (px, py, floor + 4), 10, nu=8, nv=4)
        # scroll bracket under the roof
        tube(X.mesh(TX['iron']), [(px, py, roof_z - 50), (px * 1.12, py * 1.12, roof_z - 8)], 3, nseg=5)
    for k in range(n):
        if k in open_sides: continue
        a1 = a0 + 2 * math.pi * k / n; a2 = a0 + 2 * math.pi * (k + 1) / n
        p1 = np.array([post_r * math.cos(a1), post_r * math.sin(a1)]); p2 = np.array([post_r * math.cos(a2), post_r * math.sin(a2)])
        for z in (floor + 10, floor + 30):
            tube(X.mesh(TX['iron']), [(p1[0], p1[1], z), (p2[0], p2[1], z)], 2.5, nseg=5)
        for t in np.linspace(0.1, 0.9, 7):
            q = p1 + (p2 - p1) * t
            tube(X.mesh(TX['iron']), [(q[0], q[1], floor), (q[0], q[1], floor + 32)], 1.6, nseg=4)
    prism(X.mesh(TX['trim_white']), poly(roof_r), roof_z, roof_z + 16, tile=128, top=False)
    prism(X.mesh(TX['roof_snow']), poly(roof_r), roof_z + 15.5, roof_z + 16, tile=256, sides=False, bot=False)
    disc(X.mesh(TX['trim_green']), roof_r, roof_z, up=False, n=n, r_in=0)
    for k in range(n * 6):                                                          # scalloped valance
        a = a0 + 2 * math.pi * (k + 0.5) / (n * 6)
        rr = roof_r * math.cos(math.pi / n) - 2
        sphere(X.mesh(TX['trim_red']), (rr * math.cos(a), rr * math.sin(a), roof_z - 6), 10, nu=6, nv=4)
    tube(X.mesh(TX['iron']), [(0, 0, roof_z + 16), (0, 0, roof_z + 90)], 3, nseg=5)  # weathervane (thin)
    rbox(X.mesh(TX['iron']), (-26, -1, roof_z + 74), (26, 1, roof_z + 84), r=0.5, k=1, tile=64)
    ML.save('bandstand', X)
    COLL['bandstand'] = dict(cyls=[], posts=[(post_r * math.cos(a0 + 2 * math.pi * k / n), post_r * math.sin(a0 + 2 * math.pi * k / n))
                                             for k in range(n)])
    return X


def tower_dress(w=240.0, h=720.0, belfry=(500.0, 640.0)):
    """chapel tower dressing over the stone solid_piece: clock faces, belfry louvres, coping, corner pinnacles,
    weathervane on the NE pinnacle, and the bell inside. Origin = ground at the tower centre."""
    X = ML.Model()
    hw = w / 2
    for k in range(4):
        R = rz(90 * k)
        cl = Mesh(); disc(cl, 54, 0, up=True, n=24)
        X.mesh(TX['clock']).add(cl, R @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float).T, R @ np.array([0, -hw - 2.5, 420]))
        rim = Mesh(); revolve(rim, [(60, -2), (60, 2), (54, 2)], n=24)
        X.mesh(TX['bronze']).add(rim, R @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float).T, R @ np.array([0, -hw - 2.5, 420]))
        lv = Mesh()
        for z in np.arange(belfry[0] + 12, belfry[1] - 8, 18):
            rbox(lv, (-48, -hw + 10, z), (48, -hw + 14, z + 10), r=1, k=1, tile=64)
        X.mesh(TX['wood_dark']).add(lv, R, (0, 0, 0))
    prism(X.mesh(TX['chapel_stone']), [(-hw - 8, -hw - 8), (hw + 8, -hw - 8), (hw + 8, hw + 8), (-hw - 8, hw + 8)], h - 10, h, tile=128,
          bot=True, top=False)
    prism(X.mesh(TX['roof_snow']), [(-hw - 8, -hw - 8), (hw + 8, -hw - 8), (hw + 8, hw + 8), (-hw - 8, hw + 8)], h - 0.5, h, tile=256,
          sides=False, bot=False)
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cx, cy = sx * (hw - 6), sy * (hw - 6)
        cone(X.mesh(TX['chapel_stone']), 9, h, 0, h + 34, n=8, u=1, cx=cx, cy=cy, cap=False)
    cx, cy = hw - 6, hw - 6
    tube(X.mesh(TX['iron']), [(cx, cy, h + 40), (cx, cy, h + 110)], 2.5, nseg=5)
    rbox(X.mesh(TX['iron']), (cx - 22, cy - 1, h + 92), (cx + 22, cy + 1, h + 100), r=0.5, k=1, tile=64)
    sphere(X.mesh(TX['bronze']), (cx, cy, h + 80), 6, nu=8, nv=6)
    # the bell hanging in the belfry on a beam
    rbox(X.mesh(TX['wood_dark']), (-hw + 16, -8, belfry[1] - 4), (hw - 16, 8, belfry[1] + 8), r=1, k=1, tile=128)
    revolve(X.mesh(TX['bronze']), [(52, belfry[0] + 20), (46, belfry[0] + 30), (34, belfry[0] + 80), (30, belfry[1] - 20),
                                   (14, belfry[1] - 6), (0, belfry[1] - 6)], n=20)
    revolve(X.mesh(TX['bronze']), [(0, belfry[0] + 40), (50, belfry[0] + 22)], n=20, inward=True)
    ML.save('tower_dress', X)
    return X


def pew(L=160.0):
    X = ML.Model()
    w = TX['pew']
    rbox(X.mesh(w), (-L / 2, -20, 26), (L / 2, 20, 32), r=1.5, k=1, tile=128)
    rbox(X.mesh(w), (-L / 2, 16, 32), (L / 2, 22, 70), r=1.5, k=1, tile=128)
    for x in (-L / 2, L / 2 - 6):
        rbox(X.mesh(w), (x, -22, 0), (x + 6, 24, 72), r=1.5, k=1, tile=64)
    ML.save('pew', X)
    COLL['pew'] = dict(boxes=[((-L / 2, -22, 0), (L / 2, 24, 32)), ((-L / 2, 14, 32), (L / 2, 24, 70))])
    return X


def organ(w=240.0, d=80.0, h=300.0, gap=40.0):
    """pipe organ case against a wall (back at local +y = 0, front at -d). The open arch at the bottom centre (2*gap
    wide, 100 high) is the secret way in."""
    X = ML.Model()
    wd = TX['wood_dark']
    for (x0, x1) in ((-w / 2, -gap), (gap, w / 2)):
        rbox(X.mesh(wd), (x0, -d, 0), (x1, 0, 140), r=2, k=1, tile=128)
    rbox(X.mesh(wd), (-gap, -d, 100), (gap, 0, 140), r=2, k=1, tile=128)
    rbox(X.mesh(TX['coal']), (-gap, -8, 0), (gap, 0, 100), r=0.5, k=1, tile=64, faces='s')       # the dark recess
    rbox(X.mesh(wd), (-w / 2, -d * 0.8, 140), (w / 2, 0, 160), r=2, k=1, tile=128)
    for k in range(13):
        x = -w / 2 + 14 + k * (w - 28) / 12
        top = 200 + 80 * (1 - abs(k - 6) / 6)
        tube(X.mesh(TX['organ_pipe']), [(x, -d * 0.5, 160), (x, -d * 0.5, top + 60)], 8 + (1 - abs(k - 6) / 6) * 3, nseg=8)
    rbox(X.mesh(wd), (-w / 2, -d * 0.6, h - 20), (w / 2, 0, h), r=2, k=1, tile=128)
    rbox(X.mesh(wd), (-w / 2 - 8, -d - 40, 60), (w / 2 + 8, -d, 72), r=2, k=1, tile=128)            # keyboard shelf
    ML.save('organ', X)
    COLL['organ'] = dict(boxes=[((-w / 2, -d, 0), (-gap, 0, 160)), ((gap, -d, 0), (w / 2, 0, 160)), ((-gap, -d, 100), (gap, 0, 160)),
                                ((-w / 2, -d * 0.8, 160), (w / 2, 0, h))])
    return X


def altar():
    X = ML.Model()
    rbox(X.mesh(TX['chapel_stone']), (-80, -36, 0), (80, 36, 70), r=2, k=1, tile=128)
    rbox(X.mesh(TX['altar_cloth']), (-82, -38, 62), (82, 38, 72), r=1, k=1, tile=128)
    for x in (-50, 50):
        tube(X.mesh(TX['bronze']), [(x, 0, 72), (x, 0, 100)], 3, nseg=6)
        sphere(X.mesh(TX['lamp_glass']), (x, 0, 104), 3, nu=6, nv=4)
    ML.save('altar', X)
    COLL['altar'] = dict(boxes=[((-80, -36, 0), (80, 36, 72))])
    return X


def gravestone(k=0):
    X = ML.Model()
    g = TX['gravestone']
    if k == 0:
        rbox(X.mesh(g), (-24, -6, 0), (24, 6, 50), r=3, k=1, tile=64)
        tmp = Mesh(); revolve(tmp, [(0, -6), (24, -6), (24, 6), (0, 6)], n=12, a0=0, a1=180)
        X.mesh(g).add(tmp, RX90.T, (0, 0, 50))
    else:
        rbox(X.mesh(g), (-6, -6, 0), (6, 6, 70), r=2, k=1, tile=64)
        rbox(X.mesh(g), (-24, -6, 44), (24, 6, 56), r=2, k=1, tile=64)
    rbox(X.mesh(TX['roof_snow']), (-26, -8, 0), (26, 8, 3), r=1, k=1, tile=64)
    ML.save(f'gravestone{k}', X)
    COLL[f'gravestone{k}'] = dict(boxes=[((-24, -6, 0), (24, 6, 64))])
    return X


def mill_tower(r0=200.0, r1=150.0, h=520.0, door_deg=180.0):
    """smock-mill tower standing on the stage (base building roof): white boards, a door toward door_deg, a
    window strip. Origin = the stage floor at the axis."""
    X = ML.Model()
    holes = lambda a, z: abs(((a - door_deg + 180) % 360) - 180) < 18 and z < 140
    rows = [(r0, 0), (r1, h)]
    ML.lathe(X.mesh(TX['mill_white']), rows, n=16, u_tiles=8, holes=holes)
    ML.lathe(X.mesh(TX['plaster']), [(r0 - 16, 0), (r1 - 16, h)], n=16, u_tiles=8, holes=holes, inward=True)
    # door jambs
    for s in (-1, 1):
        a = math.radians(door_deg + s * 18 * 1.0)
        p0 = (r0 * math.cos(a), r0 * math.sin(a)); p1 = ((r0 - 16) * math.cos(a), (r0 - 16) * math.sin(a))
        quad(X.mesh(TX['timber']), [(p0[0], p0[1], 0), (p1[0], p1[1], 0), (p1[0], p1[1], 140), (p0[0], p0[1], 140)], (s * -math.sin(a), s * math.cos(a), 0))
    for z in (180, 340):
        a = math.radians(door_deg + 90)
        rr = r0 + (r1 - r0) * z / h + 1.5
        quad(X.mesh(TX['window_glow']), [(rr * math.cos(a - 0.12), rr * math.sin(a - 0.12), z), (rr * math.cos(a + 0.12), rr * math.sin(a + 0.12), z),
                                         (rr * math.cos(a + 0.12), rr * math.sin(a + 0.12), z + 60), (rr * math.cos(a - 0.12), rr * math.sin(a - 0.12), z + 60)],
             (math.cos(a), math.sin(a), 0))
    disc(X.mesh(TX['plaster']), r1 - 16, h - 2, up=False, n=16)
    # millstones inside
    cylinder(X.mesh(TX['millstone']), 70, 0, 30, n=16)
    cylinder(X.mesh(TX['millstone']), 66, 30, 54, n=16)
    tube(X.mesh(TX['timber']), [(0, 0, 54), (0, 0, h)], 9, nseg=8)
    ML.save('mill_tower', X)
    return X


def mill_cap(r=232.0, z0=0.0, top=50.0, hub_x=262.0, hub_z=20.0):
    """the cap: a flat-topped drum (walkable top, no railing) with a boat-shaped roof skirt and the windshaft
    sticking out east to the sail hub. Origin = cap base on the axis."""
    X = ML.Model()
    revolve(X.mesh(TX['mill_cap']), [(r - 30, z0 - 30), (r + 6, z0), (r, top - 6), (r - 4, top)], n=24, u_tiles=8)
    disc(X.mesh(TX['roof_snow']), r - 4, top, up=True, n=24)
    disc(X.mesh(TX['plaster']), r - 30, z0 - 30, up=False, n=24)
    tube(X.mesh(TX['timber']), [(r - 20, 0, hub_z), (hub_x - 6, 0, hub_z)], 18, nseg=10)
    rbox(X.mesh(TX['trim_white']), (r - 6, -40, top - 30), (r + 2, 40, top - 4), r=1, k=1, tile=64)
    ML.save('mill_cap', X)
    return X


def mill_sails(L=430.0, w=70.0):
    """four lattice sails in the local y-z plane (model2 on a func_rotating round x). Origin = the hub."""
    X = ML.Model()
    sphere(X.mesh(TX['sail_frame']), (0, 0, 0), 26, nu=10, nv=6)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = np.array([0, math.cos(a), math.sin(a)]); p = np.array([0, -math.sin(a), math.cos(a)])
        tube(X.mesh(TX['sail_frame']), [d * 20, d * L], 6, nseg=6)
        c0 = d * 90; c1 = d * L
        q = [c0 + p * 8 + np.array([4, 0, 0]), c1 + p * 8 + np.array([4, 0, 0]), c1 + p * (8 + w) + np.array([4, 0, 0]),
             c0 + p * (8 + w) + np.array([4, 0, 0])]
        X.mesh(TX['sail']).poly(q, (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        for t in np.linspace(0, 1, 9):
            a1 = c0 + (c1 - c0) * t
            tube(X.mesh(TX['sail_frame']), [a1 + p * 8 + np.array([6, 0, 0]), a1 + p * (8 + w) + np.array([6, 0, 0])], 2, nseg=4)
    ML.save('mill_sails', X)
    return X


def snowman(z_tiers):
    """three snowballs, coal eyes and buttons, carrot nose, stick arms, striped scarf, top hat. z_tiers = list of
    (r, z0, z1) collision drums; the visual balls sit on the same drums. Origin = the hill top under it."""
    X = ML.Model()
    s = TX['snow_m']
    (r0, a0, b0), (r1, a1, b1), (r2, a2, b2), (hb, hz0, hz1), (hr, hz1b, hz2) = z_tiers
    for (r, z0, z1) in ((r0, a0, b0), (r1, a1, b1), (r2, a2, b2)):
        c = (z0 + z1) / 2; hh = (z1 - z0) / 2
        ellipsoid(X.mesh(s), (0, 0, c), r * 1.08, r * 1.08, hh * 1.12, nu=20, nv=12)
    for z in (a1 + 40, a1 + 90, a1 + 140):
        sphere(X.mesh(TX['coal']), (0, -r1 * 1.0 - 2, z), 10, nu=8, nv=6)
    for x in (-24, 24):
        sphere(X.mesh(TX['coal']), (x, -r2 * 0.92, a2 + 80), 8, nu=8, nv=6)
    tmp = Mesh(); revolve(tmp, [(12, 0), (0, 70)], n=10)
    X.mesh(TX['carrot']).add(tmp, RX90, (0, -r2 * 0.95, a2 + 60))
    for k in range(7):
        a = math.radians(200 + k * 20)
        sphere(X.mesh(TX['coal']), (r2 * 0.75 * math.cos(a), r2 * 0.75 * math.sin(a), a2 + 34 + 8 * abs(math.sin(a + 0.3))), 5, nu=6, nv=4)
    for sgn in (-1, 1):
        tube(X.mesh(TX['bark']), [(sgn * r1 * 0.9, 0, a1 + 120), (sgn * (r1 + 110), 10, a1 + 190), (sgn * (r1 + 170), 0, a1 + 250)], 6, nseg=6)
        tube(X.mesh(TX['bark']), [(sgn * (r1 + 110), 10, a1 + 190), (sgn * (r1 + 150), 30, a1 + 170)], 4, nseg=5)
    revolve(X.mesh(TX['scarf']), [(r2 * 1.02 + 6, a2 - 6), (r2 * 1.02 + 6, a2 + 22), (r2 * 0.8, a2 + 26)], n=20, u_tiles=4)
    tube(X.mesh(TX['scarf']), [(r2 * 0.6, -r2 * 0.8, a2 + 10), (r2 * 0.9, -r2 * 1.0, a2 - 60), (r2 * 0.8, -r2 * 1.05, a2 - 140)], 14, nseg=8,
         ry=5)
    revolve(X.mesh(TX['hat_black']), [(hb, hz0), (hb, hz1), (0, hz1)], n=24)
    disc(X.mesh(TX['hat_black']), hb, hz0, up=False, n=24)
    revolve(X.mesh(TX['hat_black']), [(hr, hz1), (hr, hz2), (0, hz2)], n=24)
    revolve(X.mesh(TX['trim_red']), [(hr + 1, hz1 + 4), (hr + 1, hz1 + 22)], n=24)
    ML.save('snowman', X)
    return X


def xmas_tree(h=900.0, r=280.0, tiers=6):
    """the village Christmas tree: stacked bough skirts with snow tips, glowing baubles, a star, presents under it"""
    X = ML.Model()
    tube(X.mesh(TX['bark']), [(0, 0, 0), (0, 0, h * 0.4)], 30, nseg=10)
    for k in range(tiers):
        f = k / tiers
        z0 = 70 + f * (h - 160); rr = r * (1 - f * 0.82)
        z1 = z0 + (h - 160) / tiers * 1.8
        revolve(X.mesh(TX['pine']), [(rr, z0), (rr * 0.25, z1), (0, z1)], n=16, u_tiles=4,
                rfun=lambda a, R0, zz: R0 * (1 + 0.08 * math.cos(8 * a)))
        revolve(X.mesh(TX['roof_snow']), [(rr * 0.98, z0 + 6), (rr * 0.7, z0 + 22)], n=16, u_tiles=4)
        disc(X.mesh(TX['pine']), rr, z0, up=False, n=16)
        for j in range(int(5 + rr / 40)):
            a = 2 * math.pi * j / int(5 + rr / 40) + k
            key = ('bauble_r', 'bauble_g', 'bauble_b')[(j + k) % 3]
            sphere(X.mesh(TX[key]), (rr * 0.92 * math.cos(a), rr * 0.92 * math.sin(a), z0 + 8), 10, nu=8, nv=6)
    # star
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5; rr = 46 if k % 2 == 0 else 20
        pts.append((rr * math.cos(a), 0, h + 30 + rr * math.sin(a)))
    for sgn in (-1, 1):
        for k in range(10):
            q = [np.array([0, sgn * 8, h + 30]), np.array(pts[k]), np.array(pts[(k + 1) % 10])]
            if sgn < 0: q = q[::-1]
            X.mesh(TX['star']).poly(q, (0, sgn, 0), [(0.5, 0.5), (0, 0), (1, 0)])
    ML.save('xmas_tree', X)
    COLL['xmas_tree'] = dict(cyls=[(0, 0, int(r * 0.85), 0, 380), (0, 0, int(r * 0.5), 380, 640), (0, 0, int(r * 0.25), 640, int(h - 40))])
    return X


def pine(h=420.0, r=120.0):
    X = ML.Model()
    tube(X.mesh(TX['bark']), [(0, 0, 0), (0, 0, h * 0.3)], 12, nseg=8)
    for k in range(4):
        f = k / 4; z0 = 40 + f * (h - 100); rr = r * (1 - f * 0.7); z1 = z0 + (h - 60) / 4 * 1.8
        revolve(X.mesh(TX['pine']), [(rr, z0), (rr * 0.2, z1), (0, z1)], n=12, u_tiles=3,
                rfun=lambda a, R0, zz: R0 * (1 + 0.1 * math.cos(7 * a)))
        revolve(X.mesh(TX['roof_snow']), [(rr * 0.97, z0 + 4), (rr * 0.6, z0 + 26)], n=12, u_tiles=3)
        disc(X.mesh(TX['pine']), rr, z0, up=False, n=12)
    ML.save('pine', X)
    COLL['pine'] = dict(cyls=[(0, 0, int(r * 0.6), 0, int(h * 0.75))])
    return X


def street_lamp(h=200.0):
    X = ML.Model()
    revolve(X.mesh(TX['iron']), [(18, 0), (16, 10), (8, 30), (6, h - 20), (10, h - 14), (0, h - 14)], n=10)
    revolve(X.mesh(TX['iron']), [(20, h + 34), (6, h + 52), (0, h + 52)], n=8)
    revolve(X.mesh(TX['lamp_glass']), [(10, h - 14), (16, h + 30), (0, h + 30)], n=8)
    disc(X.mesh(TX['roof_snow']), 14, h + 49, up=True, n=8)
    ML.save('street_lamp', X)
    COLL['street_lamp'] = dict(cyls=[(0, 0, 10, 0, int(h))])
    return X


def bench(L=150.0):
    X = ML.Model()
    for y0 in (-18, -6, 6):
        rbox(X.mesh(TX['timber']), (-L / 2, y0, 34), (L / 2, y0 + 10, 38), r=1, k=1, tile=128)
    for z0 in (48, 62):
        rbox(X.mesh(TX['timber']), (-L / 2, 18, z0), (L / 2, 22, z0 + 10), r=1, k=1, tile=128)
    for x in (-L / 2 + 10, L / 2 - 14):
        rbox(X.mesh(TX['iron']), (x, -20, 0), (x + 4, 22, 76), r=1, k=1, tile=64)
    rbox(X.mesh(TX['roof_snow']), (-L / 2, -18, 38), (L / 2, 16, 41), r=1, k=1, tile=128)
    ML.save('bench', X)
    COLL['bench'] = dict(boxes=[((-L / 2, -20, 0), (L / 2, 22, 40))])
    return X


def sleigh():
    """Father Padmas' red sleigh with gold trim, runners and a sack of presents (cover)"""
    X = ML.Model()
    for y in (-50, 50):
        rr = [(-120, y, 8), (90, y, 8), (130, y, 30), (126, y, 54)]
        tube(X.mesh(TX['brass']), rr, 4, nseg=6)
        for x in (-80, 40):
            tube(X.mesh(TX['brass']), [(x, y, 8), (x, y * 0.9, 34)], 3, nseg=5)
    rbox(X.mesh(TX['trim_red']), (-120, -56, 34), (70, 56, 80), r=10, k=2, tile=128)
    rbox(X.mesh(TX['trim_red']), (-130, -56, 34), (-100, 56, 120), r=10, k=2, tile=128)
    rbox(X.mesh(TX['brass']), (-121, -57, 76), (71, 57, 82), r=2, k=1, tile=64)
    rbox(X.mesh(TX['fabric_green']), (-96, -48, 70), (-40, 48, 90), r=8, k=2, tile=64)
    ellipsoid(X.mesh(TX['sack']), (10, 0, 110), 50, 40, 46, nu=12, nv=8)
    for k, (x, y, s) in enumerate(((30, -30, 22), (-10, 34, 18), (50, 20, 16))):
        rbox(X.mesh(TX[f'present{k}']), (x - s, y - s, 80), (x + s, y + s, 80 + 2 * s), r=2, k=1, tile=64)
    ML.save('sleigh', X)
    COLL['sleigh'] = dict(boxes=[((-130, -56, 0), (70, 56, 82)), ((-130, -56, 82), (-100, 56, 120))])
    return X


def woodpile(L=200.0):
    X = ML.Model()
    for row in range(4):
        for k in range(int(L / 26) - row):
            x = -L / 2 + 13 + k * 26 + row * 13
            tmp = Mesh(); revolve(tmp, [(0, -40), (12, -40), (12, 40), (0, 40)], n=8)
            X.mesh(TX['logs']).add(tmp, RX90, (x, 0, 12 + row * 22))
    rbox(X.mesh(TX['roof_snow']), (-L / 2 + 20, -40, 12 + 3 * 22 + 10), (L / 2 - 50, 40, 12 + 3 * 22 + 14), r=2, k=1, tile=128)
    ML.save('woodpile', X)
    COLL['woodpile'] = dict(boxes=[((-L / 2, -40, 0), (L / 2, 40, 84))])
    return X


def presents_pile():
    X = ML.Model()
    for k, (x, y, sx, sy, sz, a) in enumerate(((0, 0, 50, 40, 60, 10), (70, 30, 34, 34, 40, -20), (-60, 40, 30, 40, 30, 30), (20, -60, 30, 26, 44, 0),
                                               (10, 10, 26, 26, 30, 40))):
        z0 = 60 if k == 4 else 0
        b = Mesh(); rbox(b, (-sx, -sy, 0), (sx, sy, sz), r=2, k=1, tile=64)
        X.mesh(TX[f'present{k % 4}']).add(b, rz(a), (x, y, z0))
    ML.save('presents_pile', X)
    COLL['presents_pile'] = dict(boxes=[((-60, -70, 0), (100, 80, 60))])
    return X


def snow_drift(r=110.0, h=14.0, seed=1):
    X = ML.Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6)
    ellipsoid(X.mesh(TX['snow_m']), (0, 0, 0), r, r * 0.6, h, nu=16, nv=6, flat_bottom=0.0,
              bump=lambda p, t: 1 + 0.15 * math.sin(3 * t + ph))
    ML.save(f'snow_drift{seed}', X)
    return X


def market_dress(w, d, h):
    """chalet dressing: fir garland + lanterns along the gable eaves and a lantern either side of the counter"""
    X = ML.Model()
    for y in (-d / 2 - 22, d / 2 + 22):
        pts = [(x, y, h - 10 - 16 * math.sin(math.pi * (x + w / 2) / w * 3) ** 2) for x in np.linspace(-w / 2, w / 2, 25)]
        tube(X.mesh(TX['garland']), pts, 7, nseg=6)
        for x in np.linspace(-w / 2 + 20, w / 2 - 20, 6):
            sphere(X.mesh(TX['lamp_glass']), (x, y, h - 28), 5, nu=6, nv=4)
    ML.save(f'market_dress_{int(w)}_{int(d)}', X)
    return X


# ================================================================================================ themed jump pads (skins)
def sled_pad(L=150.0, w=80.0, h=16.0):
    """a wooden toboggan resting flat in the snow: its slatted deck (16u) is the pad"""
    X = ML.Model()
    for y in (-w / 2 + 6, w / 2 - 6):
        tube(X.mesh(TX['runner']), [(-L / 2, y, 3), (L / 2 - 10, y, 3), (L / 2 + 14, y, 18), (L / 2 + 8, y, 36)], 3, nseg=6)
    for k in range(6):
        x = -L / 2 + 4 + k * (L - 8) / 6
        rbox(X.mesh(TX['sled']), (x, -w / 2, 8), (x + (L - 8) / 6 - 3, w / 2, h), r=1.5, k=1, tile=64)
    tube(X.mesh(TX['scarf']), [(L / 2 + 8, -w / 2, 36), (L / 2 + 30, 0, 30), (L / 2 + 8, w / 2, 36)], 2, nseg=5)
    ML.save('sled_pad', X)
    COLL['sled_pad'] = dict(boxes=[((-L / 2, -w / 2, 0), (L / 2, w / 2, h))])
    return X


def present_pad(s=60.0, h=16.0, k=0):
    """a big flat Christmas present with a bow: step on the lid"""
    X = ML.Model()
    rbox(X.mesh(TX[f'present{k}']), (-s, -s, 0), (s, s, h), r=2, k=1, tile=2 * s)
    for a in (35, -35):
        tmp = Mesh(); ellipsoid(tmp, (0, 0, 0), 16, 6, 8, nu=8, nv=6)
        X.mesh(TX['trim_red'] if k else TX['icing']).add(tmp, rz(a), (s * 0.55, s * 0.55, h + 2))
    ML.save(f'present_pad{k}', X)
    COLL[f'present_pad{k}'] = dict(boxes=[((-s, -s, 0), (s, s, h))])
    return X


def ski_pad(r=60.0, h=16.0):
    """a packed snow mound (flat top) with a pair of skis and poles stuck in behind"""
    X = ML.Model()
    revolve(X.mesh(TX['snow_m']), [(r + 14, 0), (r, h), (0, h)], n=16)
    for (x, a) in ((-14, 8), (14, -8)):
        b = Mesh(); rbox(b, (-5, -2, 0), (5, 2, 150), r=1, k=1, tile=64)
        X.mesh(TX['ski']).add(b, np.array([[math.cos(math.radians(a)), 0, math.sin(math.radians(a))], [0, 1, 0],
                                            [-math.sin(math.radians(a)), 0, math.cos(math.radians(a))]]), (x, r + 4, 0))
    for x in (-40, 40):
        tube(X.mesh(TX['iron']), [(x, r + 10, 0), (x * 1.3, r + 16, 110)], 1.5, nseg=4)
    ML.save('ski_pad', X)
    COLL['ski_pad'] = dict(cyls=[(0, 0, r + 6, 0, h)])
    return X


def curling_pad(r=58.0, h=16.0):
    """a giant curling stone on the ice (granite body, red handle)"""
    X = ML.Model()
    revolve(X.mesh(TX['granite']), [(r - 10, 0), (r, 6), (r, h - 4), (r - 6, h), (0, h)], n=20)
    tube(X.mesh(TX['trim_red']), [(-26, 0, h), (-26, 0, h + 14), (20, 0, h + 14), (34, 0, h + 8)], 5, nseg=6)
    ML.save('curling_pad', X)
    COLL['curling_pad'] = dict(cyls=[(0, 0, r, 0, h)])
    return X


def flour_pad(w=110.0, h=16.0):
    """a heap of flat flour sacks by the mill (the top sack is the pad deck)"""
    X = ML.Model()
    rbox(X.mesh(TX['sack']), (-w / 2, -w / 2, 0), (w / 2, w / 2, h), r=6, k=2, tile=128)
    for (x, y, a) in ((w * 0.55, 10, 20), (-w * 0.6, -14, -15)):
        b = Mesh(); ellipsoid(b, (0, 0, 22), 26, 20, 26, nu=10, nv=6, flat_bottom=-22)
        X.mesh(TX['sack']).add(b, rz(a), (x, y, 0))
    ML.save('flour_pad', X)
    COLL['flour_pad'] = dict(boxes=[((-w / 2, -w / 2, 0), (w / 2, w / 2, h))])
    return X


# ================================================================================================ train (dyn, IQM via railway)
def loco():
    X = ML.Model()
    rbox(X.mesh(TX['loco_black']), (-100, -50, 6), (110, 50, 24), r=3, k=1, tile=128)
    tmp = Mesh(); revolve(tmp, [(0, -10), (38, -10), (38, 140), (0, 140)], n=16)
    X.mesh(TX['loco_green']).add(tmp, RY90, (-30, 0, 62))
    revolve(X.mesh(TX['loco_black']), [(14, 98), (16, 120), (22, 138), (0, 138)], n=10, cx=80, cy=0)
    sphere(X.mesh(TX['brass_dyn']), (30, 0, 102), 14, nu=8, nv=6)
    rbox(X.mesh(TX['loco_green']), (-100, -48, 24), (-30, 48, 112), r=4, k=1, tile=128)
    rbox(X.mesh(TX['loco_red']), (-108, -54, 112), (-24, 54, 122), r=4, k=1, tile=128)
    for x in (-70, -10, 50):
        for y in (-48, 48):
            tmp = Mesh(); revolve(tmp, [(0, -4), (20, -4), (20, 4), (0, 4)], n=12)
            X.mesh(TX['loco_red']).add(tmp, RX90, (x, y, 20))
    rbox(X.mesh(TX['loco_red']), (110, -40, 6), (124, 40, 22), r=2, k=1, tile=64)
    return X


def flatcar(k=0):
    X = ML.Model()
    rbox(X.mesh(TX['wagon_wood']), (-90, -50, 16), (90, 50, 30), r=2, k=1, tile=128)
    rbox(X.mesh(TX['loco_black']), (-84, -40, 4), (84, 40, 16), r=2, k=1, tile=128)
    for x in (-50, 50):
        for y in (-44, 44):
            tmp = Mesh(); revolve(tmp, [(0, -3), (14, -3), (14, 3), (0, 3)], n=10)
            X.mesh(TX['loco_red']).add(tmp, RX90, (x, y, 14))
    for (x0, x1) in ((-90, -84), (84, 90)):
        rbox(X.mesh(TX['loco_red']), (x0, -50, 30), (x1, 50, 44), r=1, k=1, tile=64)
    if k % 2:
        for (x, y, s) in ((-30, -10, 18), (30, 16, 14)):
            rbox(X.mesh(TX['brass_dyn']), (x - s, y - s, 30), (x + s, y + s, 30 + s), r=2, k=1, tile=64)
    return X


# ================================================================================================ the music box (secret)
def music_drum(L=420.0, r=90.0):
    """the pinned brass cylinder of the globe's music box (model2 on a func_rotating round x; origin = its axis)"""
    X = ML.Model()
    tmp = Mesh(); revolve(tmp, [(0, -L / 2), (r, -L / 2), (r, L / 2), (0, L / 2)], n=24, u_tiles=3)
    X.mesh(TX['drum_brass']).add(tmp, RY90)
    rng = np.random.default_rng(5)
    for k in range(160):
        x = rng.uniform(-L / 2 + 10, L / 2 - 10); a = rng.uniform(0, 2 * math.pi)
        p = (x, r * math.cos(a), r * math.sin(a)); q = (x, (r + 9) * math.cos(a), (r + 9) * math.sin(a))
        tube(X.mesh(TX['pins']), [p, q], 1.6, nseg=4)
    ML.save('music_drum', X)
    return X


def music_gear(r=110.0, teeth=18, t=16.0):
    X = ML.Model()
    pts = []
    for k in range(teeth * 2):
        a = math.pi * k / teeth; rr = r if k % 2 == 0 else r - 14
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    tmp = Mesh(); prism(tmp, pts, -t / 2, t / 2, tile=128)
    X.mesh(TX['gear_dyn']).add(tmp, RY90.T)
    ML.save('music_gear', X)
    return X


def music_frame(L=420.0, r=90.0, axis_z=150.0):
    """static parts: the bedplate, the steel comb whose teeth touch the drum, the spring barrel and the winding key"""
    X = ML.Model()
    rbox(X.mesh(TX['brass']), (-L / 2 - 80, -160, 0), (L / 2 + 80, 160, 20), r=3, k=1, tile=256)
    for x in (-L / 2 - 40, L / 2 + 40):
        rbox(X.mesh(TX['brass']), (x - 12, -40, 20), (x + 12, 40, axis_z + 30), r=3, k=1, tile=128)
    rbox(X.mesh(TX['comb']), (-L / 2, r + 12, axis_z - 50), (L / 2, r + 60, axis_z - 34), r=1, k=1, tile=256)
    for k in range(40):
        x = -L / 2 + 6 + k * (L - 12) / 39
        rbox(X.mesh(TX['comb']), (x - 3, r + 4, axis_z - 44), (x + 3, r + 14, axis_z - 4), r=0.5, k=1, tile=64)
    tmp = Mesh(); revolve(tmp, [(0, -60), (70, -60), (70, 60), (0, 60)], n=20)
    X.mesh(TX['brass']).add(tmp, RY90, (0, -110, 90))
    ML.save('music_frame', X)
    COLL['music_frame'] = dict(boxes=[((-L / 2 - 80, -160, 0), (L / 2 + 80, 160, 20))])
    return X


def crate_stack():
    X = ML.Model()
    for (mn, mx) in (((-60, -60, 0), (60, 60, 96)), ((60, -50, 0), (150, 40, 80)), ((-40, -40, 96), (40, 40, 170))):
        rbox(X.mesh(TX['timber']), mn, mx, r=4, k=2, tile=96)
    for (x0, y0, x1, y1, z) in ((-60, -60, 60, 60, 96), (60, -50, 150, 40, 80), (-40, -40, 40, 40, 170)):
        rbox(X.mesh(TX['roof_snow']), (x0 + 4, y0 + 4, z), (x1 - 4, y1 - 4, z + 3), r=1, k=1, tile=96)
    ML.save('crate_stack', X)
    COLL['crate_stack'] = dict(boxes=[((-58, -58, 0), (58, 58, 96)), ((60, -48, 0), (148, 38, 80)), ((-38, -38, 96), (38, 38, 168))])
    return X
