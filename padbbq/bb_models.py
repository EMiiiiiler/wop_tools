"""Custom MD3/IQM map objects for wop_padbbq (Backyard BBQ). All geometry and art is original and 
    make() -> writes models/padbbq/*.md3/*.iqm and their images (shaders are registered in bblib.REG)

Scale 5u per cm (Padman 56u = an 11 cm toy). Origin = floor centre unless noted, "front" faces +x (misc_model angle
turns it); pieces that only make sense in place (pergola, house trim, shed trim, kennel, hose) are built in world
coordinates. build_bbq.py reads layout.py so the invisible weapclip collision sits just inside the visible surfaces.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from bblib import *
import bblib
import layout as L


# ================================================================================================= mesh helpers
def _ball(r, n=10):
    m = Mesh(); sphere(m, (0, 0, 0), r, nu=n, nv=max(4, n // 2)); return m


def turned(M, h, r, z0=0.0, n=12, bulbs=((0.15, 1.35), (0.55, 1.15)), foot=1.25, cx=0.0, cy=0.0):
    """turned wooden leg / spindle"""
    prof = [(0, z0), (r * foot, z0), (r * foot, z0 + h * 0.04), (r * 0.8, z0 + h * 0.07)]
    for (f, k) in bulbs:
        prof += [(r * 0.85, z0 + h * (f - 0.06)), (r * k, z0 + h * f), (r * 0.8, z0 + h * (f + 0.06))]
    prof += [(r, z0 + h * 0.93), (r * 1.2, z0 + h * 0.97), (r * 1.2, z0 + h), (0, z0 + h)]
    revolve(M, prof, n=n, u_tiles=1, vlen=max(64, h), cx=cx, cy=cy)


def cushion(M, mn, mx, puff=10.0, r=14.0, k=4, tile=128.0):
    mn = np.asarray(mn, float); mx = np.asarray(mx, float); c = (mn + mx) / 2; H = (mx - mn) / 2
    def inf(x, y, z, n):
        u = [(x - c[0]) / H[0], (y - c[1]) / H[1], (z - c[2]) / H[2]]
        ax = int(np.argmax(np.abs(n)))
        o = [a for i, a in enumerate(u) if i != ax]
        return puff * max(0.0, (1 - o[0] ** 2)) * max(0.0, (1 - o[1] ** 2))
    rbox(M, mn, mx, r=r, k=k, tile=tile, inflate=inf)


CYC = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]])      # (u, v, w) -> (w, u, v): polygon in (y, z), extruded along x
RX90 = np.array([[1.0, 0, 0], [0, 0, -1], [0, 1, 0]])     # (x, y, z) -> (x, -z, y): rotation about x by +90 degrees


def side_prism(M, poly_xz, y0, y1, tile=128.0):
    """polygon in the (x, z) plane extruded along y from y0 to y1"""
    m = Mesh(); prism(m, [(x, z) for (x, z) in poly_xz], -y1, -y0, tile=tile)
    m.transform(RX90)               # prism z (extrusion) -> -y, prism y (profile) -> z
    M.add(m)


def disc_axis(M, c, r, nrm, n=16, tex_scale=None):
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm)
    b1, b2 = frame(nrm)
    pts = [c + b1 * r * math.cos(a) + b2 * r * math.sin(a) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    M.poly(pts, nrm, [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def cyl(M, c, r, h, n=16, caps=True, tile=128.0):
    """vertical cylinder from c (bottom centre) up h"""
    c = np.asarray(c, float)
    revolve(M, [(0, c[2]), (r, c[2]), (r, c[2] + h), (0, c[2] + h)] if caps else [(r, c[2]), (r, c[2] + h)], n=n, cx=c[0], cy=c[1], vlen=tile)


def bar(M, a, b, r, n=8):
    tube(M, [a, b], r, nseg=n)


def box(M, mn, mx, r=2.0, tile=64.0, k=2, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture_quad(M, cx, cy, cz, w, h, nrm):
    """textured quad (u left->right as seen from the front), normal nrm (axis-aligned in xy)"""
    nrm = np.asarray(nrm, float)
    right = np.array([-nrm[1], nrm[0], 0.0])           # viewer looks along -nrm with z up: right = up x (-n)... = (-ny, nx)
    c = np.array([cx, cy, cz], float)
    p = [c - right * w / 2 - [0, 0, h / 2], c + right * w / 2 - [0, 0, h / 2], c + right * w / 2 + [0, 0, h / 2], c - right * w / 2 + [0, 0, h / 2]]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


class Mdl(Model):
    pass


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


# ================================================================================================= textures (models)
def tex_wood(n=128, col=(196, 150, 100), seed=1, lines=10):
    x, y = xy(n)
    g = noise(n, 1, seed)
    streak = np.asarray(img(g * 50 + 128).resize((n, max(4, n // 24))).resize((n, n)), np.float32) - 128
    c = np.zeros((n, n, 3), np.float32) + C(col) + streak[..., None] * 0.3
    c += (np.sin(y * lines * 2 * math.pi + noise(n, 14, seed + 1) * 2) * 6)[..., None]
    return c + N3(n, 0.8, seed + 2, 3)


def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((120, 140, 160)), C((250, 250, 245)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_stripes(w=256, h=64, cols=((240, 70, 70), (250, 250, 245)), k=8, vertical=True, seed=1):
    x, y = xy(w, h)
    t = x if vertical else y
    idx = np.floor(t * k).astype(int) % len(cols)
    c = np.array(cols, np.float32)[idx]
    return c + N3(w, 0.8, seed, 3, h)


def tex_label(text, w, h, bg, fg, serif=False):
    return text_img(text, w, h, bg, fg, serif)


def tex_print_fish(n=256, seed=3):
    """paddling-pool floor print: bubbles and little fish on blue"""
    im = Image.new('RGB', (n, n), (80, 160, 226)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(30):
        x, y, s_ = r.uniform(0, n), r.uniform(0, n), r.uniform(3, 8)
        d.ellipse((x - s_, y - s_, x + s_, y + s_), outline=(220, 240, 255), width=2)
    for _ in range(9):
        x, y = r.uniform(16, n - 16), r.uniform(16, n - 16)
        col = [(250, 150, 40), (250, 220, 60), (240, 90, 120)][r.integers(3)]
        d.ellipse((x - 14, y - 7, x + 10, y + 7), fill=col)
        d.polygon([(x + 8, y), (x + 18, y - 8), (x + 18, y + 8)], fill=col)
        d.ellipse((x - 9, y - 3, x - 5, y + 1), fill=(20, 20, 30))
    return np.asarray(im, np.float32)


def tex_corn(n=128, seed=5):
    x, y = xy(n)
    k = 14
    c = np.zeros((n, n, 3), np.float32) + C((250, 210, 70))
    u = (x * k) % 1.0; v = (y * k * 2) % 1.0
    bump = np.clip(1 - np.hypot(u - 0.5, v - 0.5) * 2.2, 0, 1)
    return c * (0.7 + 0.35 * bump)[..., None] + N3(n, 0.8, seed, 4)


def tex_sausage(n=64, seed=7):
    x, y = xy(n)
    c = fill(n, (150, 70, 40), 6, seed)
    stripes = (np.abs(((x + y * 0.3) * 6) % 1.0 - 0.5) < 0.06)
    return np.where(stripes[..., None], C((60, 30, 20)), c)


def tex_patty(n=64, seed=9):
    c = fill(n, (110, 64, 40), 10, seed) + N3(n, 0.5, seed + 1, 14)
    x, y = xy(n)
    marks = (np.abs((x * 5) % 1.0 - 0.5) < 0.07)
    return np.where(marks[..., None], C((40, 24, 16)), c)


def tex_ember(n=64, seed=11):
    c = fill(n, (60, 40, 36), 6, seed)
    hot = np.clip(noise(n, 3, seed + 1) - 0.3, 0, 1)[..., None]
    return lerp(c, C((255, 120, 30)), hot) + N3(n, 0.5, seed + 2, 6)


def tex_shirt(col, n=128, seed=13, stripe=None):
    c = fill(n, col, 4, seed)
    if stripe is not None:
        x, y = xy(n)
        c = np.where((((y * 6) % 1.0) < 0.3)[..., None], C(stripe), c)
    return c


def tex_leaf(n=128, seed=15, col=(70, 120, 50)):
    """alpha leaf cluster for the pergola vine"""
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(26):
        x, y = r.uniform(10, n - 10), r.uniform(10, n - 10); s_ = r.uniform(8, 16); a = r.uniform(0, math.pi)
        c2 = tuple(int(v) for v in (C(col) + r.uniform(-25, 25))) + (255,)
        pts = [(x + math.cos(a + t) * s_ * (1 if k % 2 == 0 else 0.45), y + math.sin(a + t) * s_ * (1 if k % 2 == 0 else 0.45))
               for k, t in enumerate(np.linspace(0, 2 * math.pi, 10, endpoint=False))]
        d.polygon(pts, fill=c2)
    a = np.asarray(im, np.float32)
    return a[..., :3], a[..., 3]


def tex_spray(n=64, seed=17):
    """sprinkler water jet (additive streaks)"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32)
    streak = np.clip(1 - np.abs(x - 0.5) * 3, 0, 1) * (0.5 + 0.5 * noise(n, 1, seed)) * (1 - y * 0.6)
    return c + (streak * 200)[..., None] * C((0.8, 0.9, 1.0))


def tex_seedpacket(n=128):
    return text_img('TOMATO\nSEEDS', n, n, (240, 80, 60), (255, 250, 230), False)


def make_textures():
    T('env', tex_env())
    T('enamel_black', fill(64, (26, 26, 30), 2, 1)); T('enamel_red', fill(64, (190, 30, 34), 3, 2)); T('ash', fill(64, (120, 116, 110), 6, 3))
    T('chrome', fill(64, (200, 204, 210), 4, 4)); T('steel', fill(64, (150, 154, 160), 5, 5)); T('black', fill(64, (24, 24, 28), 2, 6))
    T('rubber_black', fill(64, (34, 34, 36), 3, 7)); T('wood_handle', tex_wood(64, (150, 100, 60), 8)); T('ember', tex_ember())
    T('briquette', fill(64, (40, 38, 38), 8, 9) + N3(64, 0.5, 10, 10)); T('sausage', tex_sausage()); T('patty', tex_patty()); T('corn', tex_corn())
    T('bun', fill(64, (214, 160, 90), 6, 11)); T('pepper_red', fill(64, (220, 40, 30), 4, 12)); T('pepper_green', fill(64, (70, 150, 40), 4, 13))
    T('onion', fill(64, (230, 220, 200), 4, 14)); T('paper_bag', fill(128, (180, 140, 90), 8, 15))
    T('label_beads', tex_label('BBQ BEADS', 256, 128, (200, 40, 30), (255, 230, 120)))
    T('esky_blue', fill(64, (40, 110, 200), 3, 16)); T('white', fill(64, (248, 248, 246), 2, 17)); T('plastic_white', fill(64, (236, 236, 230), 3, 18))
    T('pool_blue', fill(64, (60, 140, 230), 3, 19)); T('pool_white', fill(64, (245, 245, 250), 2, 20)); T('pool_yellow', fill(64, (250, 210, 60), 3, 21))
    T('pool_floor', tex_print_fish()); T('foam_red', fill(64, (230, 70, 70), 3, 22)); T('foam_green', fill(64, (90, 200, 110), 3, 23))
    T('foam_yellow', fill(64, (250, 214, 70), 3, 24)); T('foam_blue', fill(64, (70, 130, 230), 3, 25))
    T('timber', tex_wood(128, (170, 120, 76), 26)); T('timber_grey', tex_wood(128, (150, 140, 126), 27)); T('timber_pale', tex_wood(128, (214, 180, 132), 28))
    T('timber_red', tex_wood(128, (160, 60, 46), 29)); T('alu', fill(64, (196, 198, 202), 3, 30))
    T('parasol', tex_stripes(256, 64, ((230, 60, 60), (250, 248, 240)), 8)); T('lounger', tex_stripes(64, 256, ((60, 140, 200), (250, 248, 240), (250, 200, 60)), 9, False))
    T('towel', tex_stripes(256, 64, ((250, 120, 40), (250, 230, 60), (60, 180, 200)), 6, False, 3))
    T('kennel_roof', fill(128, (150, 50, 40), 6, 31) * np.where((xy(128)[1] * 6 % 1.0 < 0.08)[..., None], 0.6, 1.0))
    T('kennel_sign', tex_label('REX', 256, 96, (250, 240, 200), (150, 40, 30), True)); T('blanket', tex_stripes(128, 128, ((180, 60, 70), (220, 200, 160)), 6, True, 5))
    T('dogbowl', fill(64, (60, 120, 210), 3, 32)); T('bone', fill(64, (236, 228, 206), 4, 33))
    T('corr_roof', np.asarray(img(fill(128, (170, 176, 178), 4, 34) * (0.82 + 0.22 * np.sin(xy(128)[0] * math.pi * 16))[..., None]), np.float32))
    T('shed_trim', fill(64, (240, 236, 222), 3, 35)); T('shed_door', tex_wood(128, (100, 140, 110), 36, 3))
    T('sign_shed', tex_label("DAD'S SHED", 512, 128, (30, 70, 50), (250, 240, 200)))
    T('mower_green', fill(64, (60, 150, 60), 3, 37)); T('mower_orange', fill(64, (240, 120, 30), 3, 38)); T('pegboard', fill(128, (190, 160, 120), 4, 39))
    T('potting_mix', fill(128, (60, 100, 60), 6, 40)); T('label_mix', tex_label('POTTING\nMIX', 256, 256, (60, 110, 60), (250, 250, 230)))
    T('terracotta', fill(64, (196, 100, 60), 6, 41)); T('soil_m', fill(128, (80, 58, 40), 8, 42) + N3(128, 0.6, 43, 10))
    T('leaf_green', fill(64, (70, 140, 50), 6, 44)); T('leaf_dark', fill(64, (40, 100, 40), 6, 45)); T('leaf_lettuce', fill(64, (140, 200, 80), 6, 46))
    T('tomato', fill(64, (220, 40, 30), 3, 47)); T('lemon', fill(64, (250, 220, 50), 3, 48)); T('carrot_top', fill(64, (80, 160, 50), 5, 49))
    c, a = tex_leaf(); T('vine', c, a); c, a = tex_leaf(128, 51, (60, 130, 60)); T('vine_b', c, a)
    T('bulb_warm', fill(32, (255, 220, 150), 2, 52)); T('cable', fill(32, (30, 30, 30), 2, 53))
    T('hose_green', fill(64, (60, 170, 70), 3, 54)); T('reel_yellow', fill(64, (250, 190, 40), 3, 55)); T('spray', tex_spray())
    T('gnome_red', fill(64, (220, 40, 40), 3, 56)); T('gnome_blue', fill(64, (60, 90, 200), 3, 57)); T('skin', fill(64, (246, 206, 170), 3, 58))
    T('beard', fill(64, (250, 250, 246), 3, 59)); T('gnome_green', fill(64, (60, 140, 70), 3, 60))
    T('ant', fill(64, (36, 22, 18), 3, 61)); T('ant_red', fill(64, (140, 40, 26), 3, 62)); T('larva', fill(64, (246, 240, 226), 3, 63))
    T('seed', fill(64, (150, 110, 60), 6, 64)); T('sugar', fill(64, (252, 252, 250), 4, 65)); T('crumb', fill(64, (214, 170, 110), 10, 66))
    T('mound', fill(128, (120, 86, 58), 10, 67) + N3(128, 0.5, 68, 14))
    for k, (col, st) in enumerate((((60, 120, 200), None), ((240, 240, 236), (220, 60, 60)), ((250, 200, 60), None), ((230, 110, 160), None), ((90, 170, 110), (250, 250, 240)))):
        T(f'cloth_{k}', tex_shirt(col, 128, 70 + k, st))
    T('peg', fill(32, (250, 120, 160), 3, 76)); T('willow', tex_wood(64, (190, 160, 110), 77, 20))
    T('bat_willow', tex_wood(64, (230, 200, 150), 78, 3)); T('stumps', fill(64, (240, 230, 200), 3, 79)); T('ball_red', fill(64, (170, 30, 30), 4, 80))
    T('frisbee', fill(64, (250, 90, 40), 3, 81)); T('bucket_blue', fill(64, (70, 160, 230), 3, 82)); T('spade_red', fill(64, (230, 60, 50), 3, 83))
    T('heatpump', fill(64, (236, 236, 232), 2, 84)); T('grille', np.asarray(img(fill(64, (90, 92, 96), 2, 85) * (0.7 + 0.3 * (xy(64)[1] * 16 % 1.0 > 0.5))[..., None]), np.float32))
    T('glass_t', fill(64, (200, 230, 240), 3, 86)); T('gutter', fill(64, (230, 232, 230), 2, 87)); T('sunscreen', tex_label('SPF\n50+', 64, 128, (250, 160, 40), (255, 255, 255)))
    T('magazine', tex_label('SUMMER', 128, 160, (60, 180, 220), (255, 255, 255))); T('jandal_blue', fill(64, (40, 120, 220), 3, 88)); T('jandal_pink', fill(64, (240, 110, 170), 3, 89))
    T('cabbage_tree', fill(64, (120, 110, 90), 8, 90)); T('flax', fill(64, (70, 100, 50), 6, 91))
    T('cubby_wall', fill(128, (240, 200, 210), 4, 92) * np.where((xy(128)[0] * 6 % 1.0 < 0.05)[..., None], 0.8, 1.0))
    T('cubby_roof', fill(128, (80, 130, 200), 6, 93) * np.where((xy(128)[1] * 6 % 1.0 < 0.08)[..., None], 0.65, 1.0))
    T('cubby_in', fill(128, (250, 236, 210), 4, 94)); T('sand', fill(128, (232, 210, 160), 8, 95) + N3(128, 0.5, 96, 10))
    T('stone_m', fill(128, (150, 146, 138), 8, 97) + N3(128, 3, 98, 10)); T('bin_green', fill(64, (50, 100, 60), 3, 99))


# ================================================================================================= the kettle barbecue
G = L


def bowl_z(r):
    """outer bowl surface height at radius r"""
    a = math.asin(min(1.0, r / L.G_RIM_R))
    return L.G_RIM_Z - (L.G_RIM_Z - L.G_BOT_Z) * math.cos(a)


def kettle():
    """kettle barbecue, origin = floor centre: black enamel bowl, rim roll, chrome grate with food, glowing coals,
    three legs (two with wheels), ash catcher pan on a triangle brace, the lid hanging on the side hook"""
    X = Model()
    E = X.mesh(S('enamel_black', 'lms', v=0.22)); Ei = X.mesh(S('ash', 'lm')); Ch = X.mesh(S('chrome', 'lms'))
    St = X.mesh(S('steel', 'lms')); Rb = X.mesh(S('rubber_black', 'lm')); Wd = X.mesh(S('wood_handle', 'lm'))
    R, Rz, Bz = L.G_RIM_R, L.G_RIM_Z, L.G_BOT_Z
    prof = [(R * math.sin(a), Rz - (Rz - Bz) * math.cos(a)) for a in np.linspace(0.02, math.pi / 2, 14)]
    revolve(E, [(0, Bz)] + prof, n=40, vlen=256)
    revolve(Ei, [(r - 4, z + 2) for (r, z) in prof[::-1] if r > 6], n=40, inward=True, vlen=256)
    tube(E, arc_path((0, 0, 0), R + 1, 0, 360, n=41, z=Rz), 5, nseg=8, caps=(False, False))
    # bottom vents
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.5
        disc_axis(St, (math.cos(a) * 40, math.sin(a) * 40, bowl_z(40) - 1.0), 16, (0, 0, -1), n=12)
    # coal bed + glowing heap
    disc(Ei, 122, L.G_COAL_Z - 6, n=32)
    Em = X.mesh(S('ember', 'glow'))
    Bq = X.mesh(S('briquette', 'lm'))
    rng = np.random.default_rng(3)
    for k in range(70):
        rr = 110 * math.sqrt(rng.uniform(0, 1)); a = rng.uniform(0, 2 * math.pi)
        z = L.G_COAL_Z - 6 + 6 + max(0, 18 * (1 - rr / 80))
        m = Mesh(); ellipsoid(m, (0, 0, 0), 9, 8, 6, nu=8, nv=4)
        (Em if rr < L.G_HOT_R else Bq).add(m, rot_z(rng.uniform(0, 3)), (math.cos(a) * rr, math.sin(a) * rr, z))
    # grate: parallel bars + outer ring + two handles
    gz = L.G_GRATE_Z - 2
    for x in np.arange(-130, 131, 13):
        h = math.sqrt(max(0.0, 136 ** 2 - x * x))
        if h > 6: bar(Ch, (x, -h, gz), (x, h, gz), 1.6, n=5)
    tube(Ch, arc_path((0, 0, 0), 136, 0, 360, n=41, z=gz), 2.4, nseg=6, caps=(False, False))
    for y in (-60, 60):
        bar(Ch, (-136, y, gz - 1), (136, y, gz - 1), 2.2, n=5)
    # food on the cool edge of the grate (the middle is the hot zone)
    Sa = X.mesh(S('sausage', 'lm')); Pa = X.mesh(S('patty', 'lm')); Co = X.mesh(S('corn', 'lm')); Bn = X.mesh(S('bun', 'lm'))
    Pr = X.mesh(S('pepper_red', 'lm')); Pg = X.mesh(S('pepper_green', 'lm')); On = X.mesh(S('onion', 'lm'))
    for k, a in enumerate((20, 40, 60)):
        c = np.array(L.ang_pt(0, 0, 104, a))
        d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))])
        pts = [(c[0] + d[0] * t, c[1] + d[1] * t, gz + 7 + 1.5 * math.sin(t / 30)) for t in np.linspace(-36, 36, 7)]
        tube(Sa, pts, 7, nseg=10)
    for a in (115, 150):
        c = L.ang_pt(0, 0, 102, a)
        ellipsoid(Pa, (c[0], c[1], gz + 6), 25, 25, 6, nu=14, nv=5)
    for a in (190, 215):
        c = np.array(L.ang_pt(0, 0, 100, a)); d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))])
        ellipsoid(Co, (c[0], c[1], gz + 12), 45, 12, 12, nu=14, nv=6, R=rot_z(math.radians(a + 90)))
    for a in (260, 290, 320):
        c = np.array(L.ang_pt(0, 0, 100, a)); d = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a))])
        bar(St, (c[0] - d[0] * 50, c[1] - d[1] * 50, gz + 8), (c[0] + d[0] * 50, c[1] + d[1] * 50, gz + 8), 0.8, n=4)
        for j, M_ in enumerate((Pr, On, Pg, Pa, Pr)):
            t = -32 + j * 16
            sphere(M_, (c[0] + d[0] * t, c[1] + d[1] * t, gz + 8), 6.5, nu=8, nv=5)
    # legs, wheels, ash pan + brace
    feet = []
    for a in (90, 210, 330):
        top = np.array([*L.ang_pt(0, 0, 132, a), bowl_z(132) - 4]); foot = np.array([*L.ang_pt(0, 0, L.G_LEG_R, a), 0.0])
        tube(St, [top, foot + [0, 0, 6]], 6, nseg=8)
        feet.append(foot)
        if a != 90:
            n_ = np.array([-math.sin(math.radians(a)), math.cos(math.radians(a)), 0])
            w = Mesh(); tube(w, [(-6, 0, 0), (6, 0, 0)], 26, nseg=16)
            Rw = np.stack([n_, np.cross([0, 0, 1], n_), [0, 0, 1]], 1)
            Rb.add(w, Rw, foot + [0, 0, 26])
            disc_axis(St, foot + [0, 0, 26] + n_ * 7, 10, n_, n=10)
        else:
            revolve(Rb, [(0, 0), (9, 0), (9, 8), (0, 8)], n=10, cx=foot[0], cy=foot[1])
    pz = L.G_PAN_Z
    for f in feet:
        p = f * (L.G_PAN_R + 8) / L.G_LEG_R
        bar(St, (p[0], p[1], pz - 14), (f[0] * 0.98, f[1] * 0.98, pz - 30 + (pz - 14) * 0.0), 3, n=6)
        bar(St, (0, 0, pz - 12), (p[0], p[1], pz - 12), 3, n=6)
    revolve(St, [(0, pz - 10), (L.G_PAN_R, pz - 10), (L.G_PAN_R + 2, pz + 8), (L.G_PAN_R - 2, pz + 8), (L.G_PAN_R - 4, pz), (0, pz)], n=36)
    # side handle + lid hanging on its hook (open side toward the bowl)
    ha = 30
    c = np.array([*L.ang_pt(0, 0, R + 14, ha), Rz - 34])
    tube(Wd, [c + [0, 0, -20], c + [0, 0, 20]], 7, nseg=10)
    lid = Mesh()
    revolve(lid, [(R + 2, 0), (R * 0.95, 40), (R * 0.75, 96), (R * 0.4, 128), (0.1, 136)], n=36)
    revolve(lid, [(0.1, 132), (R * 0.4, 124), (R * 0.75, 92), (R * 0.95, 36), (R - 2, 0)], n=36)
    ln = Mesh(); tube(ln, [(-20, 0, 146), (20, 0, 146)], 7, nseg=10)
    la = 150
    nrm = np.array([math.cos(math.radians(la)), math.sin(math.radians(la)), 0.0])
    Rl = np.stack([np.cross([0, 0, 1], nrm), [0, 0, 1], nrm], 1)            # lid z axis -> outward horizontal
    pos = np.array([*L.ang_pt(0, 0, R + 18, la), Rz - 150])
    E.add(lid, Rl, pos)
    Wd.add(ln, Rl, pos)
    disc_axis(Ch, pos + nrm * 129 + [0, 0, 50], 10, nrm, n=12)               # thermometer
    return X


def briq_steps():
    """pile of charcoal briquettes forming the 7 steps up to the ash pan (world coords relative to the grill centre)"""
    X = Model()
    B = X.mesh(S('briquette', 'lm', shade=60))
    rng = np.random.default_rng(5)
    gx, gy = L.GRILL
    for (x0, y0, x1, y1, zt) in L.briq_steps():
        for zz in np.arange(10, zt + 1, 16):
            for xx in (x0 + 9, x0 + 23):
                for yy in np.arange(y0 + 10, y1 - 5, 16):
                    m = Mesh(); ellipsoid(m, (0, 0, 0), 9, 8, 8, nu=8, nv=4)
                    B.add(m, rot_z(rng.uniform(0, 3)), (xx - gx + rng.uniform(-1, 1), yy - gy, zz - 2))
    return X


def charcoal_bag():
    """paper sack of charcoal beads slumped against the grill, origin floor centre (front +x)"""
    X = Model()
    P = X.mesh(S('paper_bag', 'lm', shade=80)); Lb = X.mesh(S('label_beads', 'lm'))
    cushion(P, (-50, -80, 0), (50, 80, 260), puff=14, r=26, tile=128)
    rbox(P, (-30, -82, 250), (30, 82, 290), r=10, k=2, tile=64)
    Lb.poly([(57, -60, 90), (57, 60, 90), (57, 60, 180), (57, -60, 180)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def tongs():
    X = Model()
    St = X.mesh(S('steel', 'lms')); W = X.mesh(S('wood_handle', 'lm'))
    for s_ in (-1, 1):
        bar(St, (0, s_ * 3, 4), (120, s_ * 9, 4), 2.4, n=5)
    bar(W, (-60, 0, 4), (0, 0, 4), 5, n=8)
    return X


def esky():
    """chilly bin: blue body, white lid with handles, origin floor centre"""
    X = Model()
    Bl = X.mesh(S('esky_blue', 'lms', v=0.12)); Wh = X.mesh(S('plastic_white', 'lm'))
    box(Bl, (-150, -90, 0), (150, 90, 170), r=10, tile=128)
    box(Wh, (-156, -96, 168), (156, 96, 200), r=10, tile=128)
    for s_ in (-1, 1):
        box(Wh, (s_ * 152 - 6, -40, 120), (s_ * 152 + 6, 40, 140), r=4)
        bar(Wh, (-60, s_ * 90, 200), (60, s_ * 90, 200), 4)
    return X


# ================================================================================================= paddling pool
def pool():
    """inflatable paddling pool: two blue/white rings, printed floor (the water surface is a brush)"""
    X = Model()
    Bl = X.mesh(S('pool_blue', 'lms', v=0.2)); Wh = X.mesh(S('pool_white', 'lms', v=0.2)); Fl = X.mesh(S('pool_floor', 'lm'))
    rc = (L.POOL_R_OUT + L.POOL_R_IN) / 2; rt = (L.POOL_R_OUT - L.POOL_R_IN) / 2
    tube(Bl, arc_path((0, 0, 0), rc, 0, 360, n=65, z=rt), rt, nseg=16, caps=(False, False), utiles=1)
    tube(Wh, arc_path((0, 0, 0), rc, 0, 360, n=65, z=L.POOL_WALL_Z - rt), rt, nseg=16, caps=(False, False), utiles=1)
    disc(Fl, L.POOL_R_IN + 8, 4, n=48, uvscale=600)
    # valve plug on the outside
    revolve(Wh, [(0, 0), (8, 0), (8, 6), (0, 8)], n=10) if False else None
    v = Mesh(); revolve(v, [(0, 0), (8, 0), (8, 8), (0, 10)], n=10)
    Wh.add(v, np.stack([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]], 1), (L.POOL_R_OUT - 2, 0, L.POOL_WALL_Z - rt))
    return X


def foam_steps(n, run=28, w=96, top=None):
    """stack of coloured foam play blocks as steps rising toward +x, origin = floor centre of the lowest step's
    outer edge (steps from x 0 to x n*run)"""
    X = Model()
    cols = ('foam_red', 'foam_yellow', 'foam_green', 'foam_blue')
    for j in range(n):
        zt = 16 * (j + 1)
        rbox(X.mesh(S(cols[j % 4], 'lm')), (run * j, -w / 2, 0), (run * (j + 1), w / 2, zt), r=3, k=2, tile=64)
    return X


def swim_ring():
    X = Model()
    tube(X.mesh(S('pool_yellow', 'dynenv')), arc_path((0, 0, 0), 46, 0, 360, n=33, z=0), 18, nseg=12, caps=(False, False))
    return X


def pool_floaters(R=170):
    """swim ring + rubber duck bobbing round the pool (one IQM for a func_rotating at the pool centre)"""
    X = Model()
    Y = X.mesh(S('pool_yellow', 'dynenv')); O = X.mesh(S('foam_red', 'dyn')); Bk = X.mesh(S('black', 'dyn'))
    tube(Y, arc_path((R, 0, 0), 46, 0, 360, n=33, z=0), 18, nseg=12, caps=(False, False))
    c = np.array([-R, 0, 0])
    ellipsoid(Y, c + [0, 0, 8], 30, 22, 18, nu=14, nv=8)
    sphere(Y, c + [0, 18, 36], 16, nu=12, nv=8)
    ellipsoid(O, c + [0, 34, 34], 6, 10, 4, nu=8, nv=5)
    for s_ in (-1, 1):
        sphere(Bk, c + [s_ * 8, 28, 42], 2.5, nu=6, nv=4)
    return X


def beach_ball(r=60):
    X = Model()
    m = Mesh(); sphere(m, (0, 0, r), r, nu=24, nv=12)
    X.mesh(S('parasol', 'lm', shade=80, tag='ball')).add(m)
    return X


# ================================================================================================= deck, pergola, house bits
def pergola():
    """pergola over the east half of the deck: posts with knee braces, two beams, rafters back to the house wall,
    slats on top, a grapevine over it and festoon lights along the front beam. Origin (0,0,0) = world."""
    X = Model()
    W = X.mesh(S('timber', 'lm', shade=40)); Wg = X.mesh(S('timber_grey', 'lm'))
    x0, y0, x1, y1 = L.PERGOLA
    z0 = L.DECK_Z; zt = L.PERG_TOP
    p = L.PERG_POST
    posts = [(x0 + p, y0 + p), ((x0 + x1) / 2, y0 + p), (x1 - p, y0 + p)]
    for (x, y) in posts:
        rbox(W, (x - p, y - p, z0), (x + p, y + p, zt - 48), r=3, k=2, tile=128)
        rbox(Wg, (x - p - 6, y - p - 6, z0), (x + p + 6, y + p + 6, z0 + 16), r=2, k=1, tile=64)           # post shoe
        for s_ in (-1, 1):
            if (s_ < 0 and x <= x0 + p + 1) or (s_ > 0 and x >= x1 - p - 1): continue
            bar(W, (x + s_ * p, y, zt - 220), (x + s_ * 180, y, zt - 70), 8, n=6)                           # knee brace
    rbox(W, (x0, y0, zt - 96), (x1, y0 + 2 * p, zt - 32), r=3, k=2, tile=128)                              # front beam
    rbox(W, (x0, y1 - 40, zt - 96), (x1, y1, zt - 32), r=3, k=2, tile=128)                                 # ledger on the wall
    for x in np.linspace(x0 + 12, x1 - 12, 9):
        rbox(W, (x - 12, y0 - 40, zt - 64), (x + 12, y1 - 40, zt - 16), r=2, k=1, tile=128)                # rafters
    for y in np.arange(y0 + 8, y1 - 8, 40):
        rbox(Wg, (x0 - 24, y, zt - 16), (x1 + 24, y + 22, zt), r=1.5, k=1, tile=128)                       # slats
    # grapevine: leaf cards on top and dangling along the front
    V = X.mesh(S('vine', 'alpha', vs=1.2)); Vb = X.mesh(S('vine_b', 'alpha', vs=1.2))
    rng = np.random.default_rng(7)
    for k in range(60):
        x = rng.uniform(x0, x1); y = rng.uniform(y0, y1 - 40); s_ = rng.uniform(70, 120); a = rng.uniform(0, math.pi)
        M_ = V if k % 2 else Vb
        q = [np.array([x + math.cos(a + t) * s_, y + math.sin(a + t) * s_, zt + 3 + rng.uniform(0, 6)]) for t in (0, math.pi / 2, math.pi, 1.5 * math.pi)]
        M_.poly(q, (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in range(14):
        x = x0 + 40 + (x1 - x0 - 80) * k / 13 + rng.uniform(-20, 20)
        h = rng.uniform(120, 260)
        M_ = V if k % 2 else Vb
        M_.poly([(x - 50, y0 - 2, zt - 40), (x + 50, y0 - 2, zt - 40), (x + 50, y0 - 2, zt - 40 - h), (x - 50, y0 - 2, zt - 40 - h)], (0, -1, 0),
                [(0, 0), (1, 0), (1, h / 100), (0, h / 100)])
    # festoon lights: sagging cable along the front beam with warm bulbs
    Cb = X.mesh(S('cable', 'lm')); Bu = X.mesh(S('bulb_warm', 'glow'))
    for (xa, xb) in ((x0 + p, (x0 + x1) / 2), ((x0 + x1) / 2, x1 - p)):
        pts = [(xa + (xb - xa) * t, y0 - 6, zt - 110 - 70 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 13)]
        tube(Cb, pts, 1.4, nseg=4, caps=(False, False))
        for q in pts[1:-1:2]:
            sphere(Bu, (q[0], q[1], q[2] - 12), 7, nu=8, nv=5)
    return X


def deck_trim():
    """deck fascia board along the front + side edges and nosings on the steps (world coords)"""
    X = Model()
    W = X.mesh(S('timber', 'lm'))
    x0, y0, x1, y1 = L.DECK
    z = L.DECK_Z
    rbox(W, (x0, y0 - 8, z - 40), (x1 + 8, y0 + 1, z + 2), r=2, k=2, tile=128)
    rbox(W, (x1 - 1, y0, z - 40), (x1 + 8, y1, z + 2), r=2, k=2, tile=128)
    for st in ('s', 'e'):
        for (a, b, c, d, zt) in L.deck_steps(st):
            if st == 's': rbox(W, (a, b - 4, zt - 6), (c, b + 6, zt + 1), r=1.5, k=1, tile=64)
            else: rbox(W, (c - 6, b, zt - 6), (c + 4, d, zt + 1), r=1.5, k=1, tile=64)
    return X


def house_trim():
    """window frames + sills, gutter, downpipes, eave soffit, outdoor tap, wall light, power socket (world coords)"""
    X = Model()
    A_ = X.mesh(S('white', 'lm', tag='frame')); Gt = X.mesh(S('gutter', 'lm')); Ch = X.mesh(S('chrome', 'lms')); Bk = X.mesh(S('black', 'lm'))
    y = L.YN
    for (x0, x1, z0, z1) in (L.WIN_W, L.WIN_E, L.WIN_S):
        f = 14
        rbox(A_, (x0 - f, y - 8, z0 - f), (x0, y + 4, z1 + f), r=1.5, k=1, tile=64)
        rbox(A_, (x1, y - 8, z0 - f), (x1 + f, y + 4, z1 + f), r=1.5, k=1, tile=64)
        rbox(A_, (x0, y - 8, z1), (x1, y + 4, z1 + f), r=1.5, k=1, tile=64)
        rbox(A_, (x0 - f - 10, y - 24, z0 - f - 8), (x1 + f + 10, y + 4, z0), r=2, k=1, tile=64)            # sill
        n = max(1, int((x1 - x0) / 300))
        for k in range(1, n + 1):
            xm = x0 + (x1 - x0) * k / (n + 1)
            rbox(A_, (xm - 6, y - 4, z0), (xm + 6, y + 4, z1), r=1, k=1, tile=64)                            # mullions
        rbox(A_, (x0, y - 4, z1 - (z1 - z0) * 0.32 - 6), (x1, y + 4, z1 - (z1 - z0) * 0.32 + 6), r=1, k=1, tile=64)
    # soffit + fascia + gutter along the eave
    ze = L.HOUSE_EAVE
    rbox(A_, (-L.XW - 400, y - 120, ze - 12), (L.XW + 400, y + 2, ze), r=1, k=1, tile=256)
    rbox(Gt, (-L.XW - 400, y - 150, ze - 30), (L.XW + 400, y - 120, ze + 24), r=6, k=2, tile=256)
    for x in (-2240, 2200):
        tube(Gt, [(x, y - 135, ze - 30), (x, y - 26, ze - 120), (x, y - 26, 40), (x, y - 70, 6)], 16, nseg=10)
    # outdoor tap
    tx, tz = L.TAP
    tube(Ch, [(tx, y + 1, tz + 30), (tx, y - 30, tz + 30), (tx, y - 30, tz)], 8, nseg=10)
    bar(Ch, (tx - 20, y - 30, tz + 42), (tx + 20, y - 30, tz + 42), 4, n=6)
    revolve(Ch, [(0, tz + 30), (6, tz + 30), (6, tz + 46), (0, tz + 46)], n=8, cx=tx, cy=y - 30)
    # wall light + power socket
    rbox(Bk, (-560, y - 30, 1220), (-500, y, 1300), r=6, k=2, tile=64)
    rbox(A_, (1700, y - 6, 300), (1780, y + 1, 380), r=4, k=2, tile=64)
    return X


def heat_pump():
    """heat-pump outdoor unit on its stand (front +x), 400 x 160 x 300"""
    X = Model()
    W = X.mesh(S('heatpump', 'lms', v=0.1)); Gr = X.mesh(S('grille', 'lm')); Bk = X.mesh(S('black', 'lm')); St = X.mesh(S('steel', 'lm'))
    rbox(St, (-70, -210, 0), (70, -180, 60), r=3); rbox(St, (-70, 180, 0), (70, 210, 60), r=3)
    rbox(W, (-80, -200, 60), (80, 200, 360), r=8, tile=128)
    m = Mesh(); disc_axis(m, (0, 0, 0), 100, (1, 0, 0), n=32)
    Gr.add(m, t=(81, -60, 210))
    tube(Bk, arc_path((81, -60, 210), 100, 0, 360, n=33, axis='x'), 4, nseg=6, caps=(False, False))
    return X


def deck_setting():
    """outdoor table (round, 480 r? no: 90 cm round = r 225) + 4 chairs around it, origin floor centre"""
    X = Model()
    A_ = X.mesh(S('alu', 'lms')); T_ = X.mesh(S('timber_pale', 'lm')); C_ = X.mesh(S('lounger', 'lm', tag='chair'))
    revolve(T_, [(0, 360), (180, 360), (183, 366), (180, 376), (0, 376)], n=40)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        bar(A_, (math.cos(a) * 120, math.sin(a) * 120, 360), (math.cos(a) * 160, math.sin(a) * 160, 0), 7)
    for k in (0, 2):
        a = k * math.pi / 2
        cx, cy = math.cos(a) * 300, math.sin(a) * 300
        Rz = rot_z(a + math.pi)
        ch = Mesh()
        for (x, y) in ((-90, -90), (-90, 90), (90, -90), (90, 90)):
            bar(ch, (x, y, 0), (x, y, 220), 6)
        rbox(ch, (-100, -100, 210), (100, 100, 226), r=4, k=2, tile=128)
        for y in (-90, 90): bar(ch, (100, y, 226), (130, y, 460), 6)
        rbox(ch, (110, -100, 300), (124, 100, 450), r=4, k=2, tile=128)
        A_.add(ch, Rz, (cx, cy, 0))
    return X


def planter(h=220, r=110, plant='lemon'):
    """big terracotta planter (origin floor centre) with a lemon tree or a flax"""
    X = Model()
    T_ = X.mesh(S('terracotta', 'lm')); So = X.mesh(S('soil_m', 'lm'))
    revolve(T_, [(0, 0), (r * 0.72, 0), (r, h - 24), (r + 12, h - 20), (r + 12, h), (r - 6, h), (r - 10, h - 16)], n=28)
    disc(So, r - 8, h - 14, n=28)
    rng = np.random.default_rng(int(h + r))
    if plant == 'lemon':
        W = X.mesh(S('timber', 'lm')); Lf = X.mesh(S('leaf_dark', 'lm', shade=90)); Le = X.mesh(S('lemon', 'lm'))
        tube(W, [(0, 0, h - 14), (6, 0, h + 200), (0, 6, h + 330)], [14, 10, 8], nseg=10)
        for k in range(9):
            a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(40, 110); z = h + 330 + rng.uniform(-60, 120)
            ellipsoid(Lf, (math.cos(a) * rr * 0.6, math.sin(a) * rr * 0.6, z), 90, 90, 70, nu=12, nv=7,
                      bump=lambda p, t: 1 + 0.12 * math.sin(5 * t + 3 * p))
        for k in range(10):
            a = rng.uniform(0, 2 * math.pi); z = h + 300 + rng.uniform(-40, 140)
            ellipsoid(Le, (math.cos(a) * 140, math.sin(a) * 140, z), 15, 12, 12, nu=8, nv=5)
    else:
        F = X.mesh(S('flax', 'lm', shade=90, two=True))
        for k in range(16):
            a = k * 2 * math.pi / 16 + rng.uniform(-0.1, 0.1); L_ = rng.uniform(220, 330); lean = rng.uniform(0.12, 0.38)
            base = np.array([math.cos(a) * 20, math.sin(a) * 20, h - 14])
            d = np.array([math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)])
            side = np.array([-math.sin(a), math.cos(a), 0]) * 14
            tip = base + d * L_ + np.array([math.cos(a), math.sin(a), 0]) * L_ * 0.12
            F.poly([base - side, base + side, tip], np.cross(side, tip - base), [(0, 0), (1, 0), (0.5, 1)])
    return X


def rotary_line():
    """rotary clothesline (mover, origin at the head on top of the mast): four arms, line rings and washing on pegs"""
    X = Model()
    St = X.mesh(S('steel', 'dynenv')); Ln = X.mesh(S('white', 'dyn', tag='line')); Pg = X.mesh(S('peg', 'dyn'))
    revolve(St, [(0, -40), (26, -40), (26, 10), (0, 20)], n=16)
    for k in range(4):
        a = k * math.pi / 2
        d = np.array([math.cos(a), math.sin(a), 0])
        bar(St, d * 20, d * 640 + [0, 0, 70], 5, n=6)
        bar(St, [0, 0, -260], d * 300 + [0, 0, 20], 3.5, n=5)            # struts down to the mast collar
    for R in (220, 340, 460, 580):
        pts = [(R * math.cos(a), R * math.sin(a), 70 * R / 640) for a in np.linspace(0, 2 * math.pi, 49)]
        tube(Ln, pts, 1.2, nseg=4, caps=(False, False))
    # washing: shirts, towels, socks hanging from the line rings
    rng = np.random.default_rng(11)
    items = [(340, 20, 'shirt', 0), (460, 70, 'towel', 1), (580, 120, 'shirt', 2), (340, 110, 'sock', 3), (460, 160, 'sock', 0),
             (580, 200, 'towel', 4), (460, 250, 'shirt', 3), (580, 290, 'shirt', 1), (340, 300, 'towel', 2), (460, 340, 'sock', 4)]
    for (R, ang, kind, col) in items:
        a = math.radians(ang)
        c = np.array([R * math.cos(a), R * math.sin(a), 70 * R / 640])
        t = np.array([-math.sin(a), math.cos(a), 0])
        n = np.array([math.cos(a), math.sin(a), 0])
        Cm = X.mesh(S(f'cloth_{col}', 'dyn', two=True))
        if kind == 'shirt': w, h = 150, 200
        elif kind == 'towel': w, h = 200, 300
        else: w, h = 40, 90
        nu = 6
        P = np.zeros((5, nu + 1, 3)); UV = np.zeros((5, nu + 1, 2))
        for i in range(5):
            for j in range(nu + 1):
                u = j / nu - 0.5; v = i / 4
                sway = 8 * math.sin(j * 1.7 + i) * v
                P[i, j] = c + t * u * w + n * sway - [0, 0, v * h]
                UV[i, j] = (j / nu, v)
        Cm.grid(P, grid_normals(P), UV)
        for s_ in (-0.4, 0.4):
            m = Mesh(); rbox(m, (-3, -2, -14), (3, 2, 4), r=1, k=1, tile=16)
            Pg.add(m, np.stack([t, n, [0, 0, 1]], 1), c + t * s_ * w)
    return X


def rotary_mast(h=900):
    X = Model()
    St = X.mesh(S('steel', 'lms'))
    tube(St, [(0, 0, 0), (0, 0, h - 40)], 14, nseg=12)
    revolve(St, [(0, 0), (40, 0), (30, 12), (16, 24), (0, 24)], n=16)
    revolve(St, [(0, h - 300), (22, h - 300), (22, h - 260), (0, h - 260)], n=16)
    return X


# ================================================================================================= shed
def shed_trim():
    """shed: corrugated iron pent roof with overhang, barge/corner boards, door frame + open door leaf, window frame,
    sign (world coords)"""
    X = Model()
    R = X.mesh(S('corr_roof', 'lms', v=0.12, shade=30)); Tr = X.mesh(S('shed_trim', 'lm')); D = X.mesh(S('shed_door', 'lm'))
    Sg = X.mesh(S('sign_shed', 'lm')); Br = X.mesh(S('chrome', 'lms'))
    x0, y0, x1, y1 = L.SHED
    ov = 40
    zn, zs = L.shed_roof_z(y1 + ov), L.shed_roof_z(y0 - ov)
    nu = 12
    Pp = np.zeros((nu + 1, nu + 1, 3)); UV = np.zeros_like(Pp[..., :2]); NN = np.zeros_like(Pp)
    nrm = np.array([0, zs - zn, (y1 - y0 + 2 * ov)]); nrm = nrm / np.linalg.norm(nrm)
    for i in range(nu + 1):
        for j in range(nu + 1):
            x = x0 - ov + (x1 - x0 + 2 * ov) * j / nu; y = y1 + ov - (y1 - y0 + 2 * ov) * i / nu
            Pp[i, j] = (x, y, L.shed_roof_z(y) + 3); UV[i, j] = (x / 128, y / 256); NN[i, j] = nrm
    R.grid(Pp, NN, UV)
    for (ya, za) in ((y1 + ov, zn), (y0 - ov, zs)):
        rbox(Tr, (x0 - ov, ya - 6, za - 50), (x1 + ov, ya + 6, za + 4), r=2, k=1, tile=128)
    for xa in (x0 - ov, x1 + ov):
        q = [(xa, y0 - ov, zs - 50), (xa, y1 + ov, zn - 50), (xa, y1 + ov, zn + 4), (xa, y0 - ov, zs + 4)]
        R.poly([np.array(v) for v in q], (1 if xa > 0 else -1, 0, 0), [(0, 0), (1, 0), (1, 0.1), (0, 0.1)]) if False else None
        rbox(Tr, (xa - 6, y0 - ov, zs - 50), (xa + 6, y1 + ov, zs + 4), r=2, k=1, tile=128) if False else None
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        rbox(Tr, (x - 14, y - 14, 0), (x + 14, y + 14, L.shed_roof_z(y) - 8), r=2, k=1, tile=128)
    # door frame + door leaf swung open outward against the north wall (east of the opening)
    dx0, dx1 = L.SHED_DOOR; H = L.SHED_DOOR_H
    rbox(Tr, (dx0 - 20, y1 - 4, 0), (dx0, y1 + 8, H + 20), r=2, k=1, tile=128)
    rbox(Tr, (dx1, y1 - 4, 0), (dx1 + 20, y1 + 8, H + 20), r=2, k=1, tile=128)
    rbox(Tr, (dx0 - 20, y1 - 4, H), (dx1 + 20, y1 + 8, H + 20), r=2, k=1, tile=128)
    rbox(D, (dx1 + 24, y1 + 8, 8), (dx1 + 24 + (dx1 - dx0), y1 + 24, H - 8), r=3, k=2, tile=256)
    for z in (160, H - 160):
        rbox(D, (dx1 + 34, y1 + 24, z - 20), (dx1 + 14 + (dx1 - dx0), y1 + 30, z + 20), r=2, k=1, tile=128)
    Br.add(_ball(8), t=(dx1 + (dx1 - dx0) - 4, y1 + 34, H / 2))
    # window frame on the east wall
    wy0, wy1, wz0, wz1 = -1840, -1600, 380, 700
    for (a, b, c, d) in ((wy0 - 16, wy0, wz0 - 16, wz1 + 16), (wy1, wy1 + 16, wz0 - 16, wz1 + 16), (wy0, wy1, wz0 - 16, wz0), (wy0, wy1, wz1, wz1 + 16)):
        rbox(Tr, (x1 - 4, a, c), (x1 + 8, b, d), r=1.5, k=1, tile=64)
    rbox(Tr, (x1 - 4, (wy0 + wy1) / 2 - 5, wz0), (x1 + 6, (wy0 + wy1) / 2 + 5, wz1), r=1, k=1, tile=64)
    Sg.poly([(dx0 - 40, y1 + 9, H + 40), (dx1 + 40, y1 + 9, H + 40), (dx1 + 40, y1 + 9, H + 110), (dx0 - 40, y1 + 9, H + 110)], (0, 1, 0),
            [(1, 1), (0, 1), (0, 0), (1, 0)])
    return X


def workbench():
    """workbench (back at -y... no: built in world coords along the shed's south wall), pegboard with tools"""
    X = Model()
    W = X.mesh(S('timber_pale', 'lm')); Pb = X.mesh(S('pegboard', 'lm')); St = X.mesh(S('steel', 'lms')); Rd = X.mesh(S('spade_red', 'lm'))
    Wh = X.mesh(S('wood_handle', 'lm'))
    x0, y0, x1, y1 = L.SHED_BENCH
    z = L.SHED_BENCH_Z
    rbox(W, (x0, y0, z - 24), (x1, y1, z), r=2, k=1, tile=128)
    for (x, y) in ((x0 + 16, y0 + 10), (x1 - 16, y0 + 10), (x0 + 16, y1 - 16), (x1 - 16, y1 - 16)):
        rbox(W, (x - 12, y - 12, 0), (x + 12, y + 12, z - 24), r=2, k=1, tile=128)
    rbox(W, (x0 + 10, y0 + 10, 90), (x1 - 10, y1 - 10, 106), r=2, k=1, tile=128)                               # lower shelf
    Pb.poly([(x0, y0 + 1, z + 40), (x1, y0 + 1, z + 40), (x1, y0 + 1, z + 400), (x0, y0 + 1, z + 400)], (0, 1, 0), [(0, 1), (2, 1), (2, 0), (0, 0)])
    # tools on the pegboard: hammer, saw, spanners, a hand trowel
    bar(Wh, (x0 + 80, y0 + 8, z + 120), (x0 + 80, y0 + 8, z + 300), 7); rbox(St, (x0 + 50, y0 + 2, z + 290), (x0 + 110, y0 + 14, z + 320), r=3, k=2)
    q = [(x0 + 170, y0 + 6, z + 140), (x0 + 330, y0 + 6, z + 150), (x0 + 330, y0 + 6, z + 230), (x0 + 170, y0 + 6, z + 300)]
    St.poly([np.array(v) for v in q], (0, 1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    rbox(Wh, (x0 + 120, y0 + 2, z + 230), (x0 + 175, y0 + 12, z + 320), r=4, k=2)
    for k in range(4):
        bar(St, (x0 + 400 + k * 40, y0 + 6, z + 140 + k * 8), (x0 + 400 + k * 40, y0 + 6, z + 260 + k * 16), 4, n=5)
    bar(Rd, (x0 + 340, y0 + 30, z + 6), (x0 + 450, y0 + 60, z + 6), 6)
    return X


def lawnmower():
    """push mower (handle toward -x), origin floor centre, 420 long"""
    X = Model()
    G_ = X.mesh(S('mower_green', 'lms', v=0.12)); Bk = X.mesh(S('rubber_black', 'lm')); St = X.mesh(S('steel', 'lms')); O = X.mesh(S('mower_orange', 'lm'))
    rbox(G_, (-110, -130, 30), (130, 130, 110), r=26, k=3, tile=128)
    revolve(St, [(0, 110), (50, 110), (40, 150), (0, 156)], n=20, cx=10)
    rbox(O, (40, -40, 110), (90, 40, 160), r=10, k=2)
    for (x, y) in ((-90, -140), (-90, 140), (100, -140), (100, 140)):
        w = Mesh(); tube(w, [(0, -10, 0), (0, 10, 0)], 30, nseg=14)
        Bk.add(w, t=(x, y, 30))
    for s_ in (-1, 1):
        bar(St, (-100, s_ * 90, 100), (-330, s_ * 110, 420), 6)
    bar(Bk, (-330, -120, 420), (-330, 120, 420), 9)
    rbox(St, (-300, -130, 120), (-110, 130, 260), r=40, k=3) if False else None
    return X


def shelf_unit():
    """steel shelves (back at -x... built facing +x), 3 levels with paint tins and pots; origin floor centre"""
    X = Model()
    St = X.mesh(S('steel', 'lms')); W = X.mesh(S('timber_pale', 'lm'))
    for (x, y) in ((-60, -150), (-60, 150), (60, -150), (60, 150)):
        bar(St, (x, y, 0), (x, y, 760), 6)
    for z in (120, 380, 640):
        rbox(W, (-70, -160, z - 12), (70, 160, z), r=1.5, k=1, tile=128)
    return X


def garden_tools():
    """spade, rake and fork leaning on a wall (back at -x), origin floor centre"""
    X = Model()
    Wh = X.mesh(S('wood_handle', 'lm')); St = X.mesh(S('steel', 'lms'))
    for k, (y, kind) in enumerate(((-90, 'spade'), (0, 'rake'), (90, 'fork'))):
        top = np.array([-14, y + 20, 640]); bot = np.array([60, y, 120])
        bar(Wh, bot, top, 7)
        if kind == 'spade':
            q = [bot + [-6, -40, 0], bot + [-6, 40, 0], bot + [8, 34, -120], bot + [8, -34, -120]]
            St.poly(q, (1, 0, 0.1), [(0, 0), (1, 0), (1, 1), (0, 1)])
            St.poly(q[::-1], (-1, 0, -0.1), [(0, 1), (1, 1), (1, 0), (0, 0)])
        else:
            bar(St, bot + [0, -70, 0], bot + [0, 70, 0], 4, n=5)
            for t in np.linspace(-64, 64, 9 if kind == 'rake' else 4):
                bar(St, bot + [0, t, 0], bot + [8, t, -(30 if kind == 'rake' else 110)], 2.5, n=4)
    return X


def sack(label='label_mix'):
    X = Model()
    P = X.mesh(S('potting_mix', 'lm', shade=80)); Lb = X.mesh(S(label, 'lm'))
    cushion(P, (-60, -110, 0), (60, 110, 120), puff=16, r=30, tile=128)
    Lb.poly([(66, -70, 20), (66, 70, 20), (66, 70, 110), (66, -70, 110)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def pot_stack():
    X = Model()
    T_ = X.mesh(S('terracotta', 'lm'))
    for k in range(5):
        z = k * 34
        revolve(T_, [(40, z), (62, z + 60), (66, z + 62), (66, z + 70), (60, z + 70)], n=20)
    revolve(T_, [(0, 0), (40, 0)], n=20, inward=True)
    return X


# ================================================================================================= kennel
def little_house(spec):
    """gabled little house (world coords): board walls with door/window openings (arched door), shingled roof with
    overhang and a flat ridge walk, trims, optional sign over the door"""
    X = Model()
    W = X.mesh(S(spec['wall'], 'lm', shade=40)); Rf = X.mesh(S(spec['roof'], 'lm', shade=40)); Tr = X.mesh(S('white', 'lm', tag='ken'))
    x0, y0, x1, y1 = spec['rect']
    H = spec['H']; Hs = H - 8
    ov = spec['ov']
    from wopmap import sub_rects
    opens = {'n': [], 's': [], 'e': [], 'w': []}
    side, u0, u1, dh = spec['door']
    opens[side].append((u0, 0, u1, dh))
    for (sd, a, b, za, zb) in spec['wins']:
        opens[sd].append((a, za, b, zb))
    def wall_quads(axis, fixed, out, a0, a1, holes):
        for (ua, za, ub, zb) in sub_rects((a0, 0, a1, Hs), holes):
            if axis == 'x': q = [(ua, fixed, za), (ub, fixed, za), (ub, fixed, zb), (ua, fixed, zb)]; n = (0, out, 0)
            else: q = [(fixed, ua, za), (fixed, ub, za), (fixed, ub, zb), (fixed, ua, zb)]; n = (out, 0, 0)
            W.poly([np.array(v, float) for v in q], n, [(ua / 96, -za / 96), (ub / 96, -za / 96), (ub / 96, -zb / 96), (ua / 96, -zb / 96)])
    wall_quads('x', y0 - 1, -1, x0 - 1, x1 + 1, opens['s'])
    wall_quads('x', y1 + 1, 1, x0 - 1, x1 + 1, opens['n'])
    wall_quads('y', x1 + 1, 1, y0 - 1, y1 + 1, opens['e'])
    wall_quads('y', x0 - 1, -1, y0 - 1, y1 + 1, opens['w'])
    zr = L.ridge_z(spec)
    t = math.tan(math.radians(spec['pitch']))
    ym = (y0 + y1) / 2; rw = spec['ridge'] / 2
    for (xx, sg_) in ((x0 - 1, -1), (x1 + 1, 1)):
        W.poly([np.array([xx, y0, Hs]), np.array([xx, y1, Hs]), np.array([xx, ym + rw, zr - 30]), np.array([xx, ym - rw, zr - 30])], (sg_, 0, 0),
               [(0, 0), (1, 0), (0.55, 0.6), (0.45, 0.6)])
    # trims round the openings (door gets an arch)
    def P(sd, u, z, off=3):
        if sd == 'n': return np.array([u, y1 + off, z])
        if sd == 's': return np.array([u, y0 - off, z])
        if sd == 'e': return np.array([x1 + off, u, z])
        return np.array([x0 - off, u, z])
    cu = (u0 + u1) / 2; rr = (u1 - u0) / 2
    tube(Tr, [P(side, cu + (rr + 6) * math.cos(a), dh - rr + (rr + 6) * math.sin(a)) for a in np.linspace(0, math.pi, 15)], 6, nseg=8)
    for uu in (u0 - 6, u1 + 6):
        bar(Tr, P(side, uu, 0), P(side, uu, dh - rr), 6)
    for (sd, a, b, za, zb) in spec['wins']:
        for (p0, p1) in ((P(sd, a - 5, za - 5), P(sd, b + 5, za - 5)), (P(sd, a - 5, zb + 5), P(sd, b + 5, zb + 5)),
                         (P(sd, a - 5, za - 5), P(sd, a - 5, zb + 5)), (P(sd, b + 5, za - 5), P(sd, b + 5, zb + 5))):
            bar(Tr, p0, p1, 5, n=6)
        bar(Tr, P(sd, a - 10, za - 12, 8), P(sd, b + 10, za - 12, 8), 6, n=6)
    # roof: two shingled slopes + ridge cap
    for sg_ in (-1, 1):
        ye = y0 - ov if sg_ < 0 else y1 + ov
        yr = ym + sg_ * rw
        nu = 8
        Pp = np.zeros((nu + 1, nu + 1, 3)); UV = np.zeros_like(Pp[..., :2]); NN = np.zeros_like(Pp)
        nrm = np.array([0, sg_ * t, 1.0]); nrm /= np.linalg.norm(nrm)
        for i in range(nu + 1):
            for j in range(nu + 1):
                x = x0 - ov + (x1 - x0 + 2 * ov) * j / nu; y = yr + (ye - yr) * i / nu
                Pp[i, j] = (x, y, L.roof_top(spec, y) + 2); UV[i, j] = (x / 96, abs(y - yr) / 96); NN[i, j] = nrm
        Rf.grid(Pp, NN, UV)
        rbox(Tr, (x0 - ov, min(ye, ye - sg_ * 6), L.roof_top(spec, ye) - 20), (x1 + ov, max(ye, ye - sg_ * 6), L.roof_top(spec, ye) + 2), r=1.5, k=1, tile=64)
    Rf.poly([np.array([x0 - ov, ym - rw, zr + 6]), np.array([x1 + ov, ym - rw, zr + 6]), np.array([x1 + ov, ym + rw, zr + 6]), np.array([x0 - ov, ym + rw, zr + 6])],
            (0, 0, 1), [(0, 0), (4, 0), (4, 0.4), (0, 0.4)])
    for sg_ in (-1, 1):
        tube(Tr, [(x0 - ov, ym + sg_ * rw, zr + 6), (x1 + ov, ym + sg_ * rw, zr + 6)], 5, nseg=8)
    if spec.get('sign'):
        Sg = X.mesh(S(spec['sign'], 'lm'))
        c = P(side, cu, dh + 42, 4)
        if side == 'w':
            Sg.poly([c + [0, 60, -22], c + [0, -60, -22], c + [0, -60, 22], c + [0, 60, 22]], (-1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        else:
            Sg.poly([c + [-60, 0, -22], c + [60, 0, -22], c + [60, 0, 22], c + [-60, 0, 22]], (0, 1, 0), [(1, 1), (0, 1), (0, 0), (1, 0)])
    return X


def kennel():
    X = little_house(L.KEN)
    x0, y0, x1, y1 = L.KENNEL
    cushion(X.mesh(S('blanket', 'lm', shade=80)), (x0 + 120, y0 + 40, 0), (x1 - 40, y1 - 40, 14), puff=4, r=8, tile=128)
    return X


def cubby():
    """kids' cubby house: pastel boards, blue shingles, window boxes, a little table and stools inside"""
    X = little_house(L.CUBBY)
    x0, y0, x1, y1 = L.CUBBY['rect']
    W = X.mesh(S('timber_pale', 'lm')); Fl = X.mesh(S('tomato', 'lm', tag='flower')); Lf = X.mesh(S('leaf_green', 'lm', tag='box'))
    for (sd, a, b, za, zb) in L.CUBBY['wins']:
        if sd == 's':
            rbox(W, (a - 10, y0 - 40, za - 50), (b + 10, y0 - 2, za - 14), r=3, k=2, tile=64)
            for k in range(6):
                sphere(Fl if k % 2 else Lf, (a + (b - a) * (k + 0.5) / 6, y0 - 21, za - 10 + 4 * (k % 2)), 12, nu=8, nv=5)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    revolve(W, [(0, 150), (90, 150), (92, 156), (90, 162), (0, 162)], n=24, cx=cx, cy=cy)
    tube(W, [(cx, cy, 0), (cx, cy, 150)], 10, nseg=8)
    for a in (0, 2.1, 4.2):
        revolve(W, [(0, 80), (36, 80), (36, 92), (0, 92)], n=16, cx=cx + math.cos(a) * 150, cy=cy + math.sin(a) * 150)
        tube(W, [(cx + math.cos(a) * 150, cy + math.sin(a) * 150, 0), (cx + math.cos(a) * 150, cy + math.sin(a) * 150, 80)], 6, nseg=6)
    return X


def sandpit():
    """clam-shell sandpit: green plastic shell with sand, the lid standing open behind it (origin floor centre;
    the hinge is at the north (+y) edge)"""
    X = Model()
    G_ = X.mesh(S('mower_green', 'lms', v=0.12, tag='shell')); Sd = X.mesh(S('sand', 'lm'))
    R, Hr, Zs = L.SAND_R, L.SAND_RIM, L.SAND_Z
    sc = lambda a, r, z: r * (1 + 0.05 * abs(math.sin(a * 7)))
    revolve(G_, [(R - 30, 0), (R, 10), (R + 8, Hr - 10), (R + 4, Hr), (R - 14, Hr), (R - 18, Zs)], n=48, rfun=sc)
    disc(Sd, R - 16, Zs, n=48)
    lid = Mesh()
    revolve(lid, [(0.1, 60), (R * 0.6, 50), (R - 8, 22), (R + 4, 0)], n=48, rfun=sc, cy=-R - 4)
    revolve(lid, [(R - 4, 0), (R - 14, 18), (R * 0.6, 42), (0.1, 52)], n=48, rfun=sc, cy=-R - 4)
    Rl = rot_axis((1, 0, 0), math.radians(-100))            # lid hinged at the north edge, swung up past vertical
    X.mesh(S('mower_green', 'lms', v=0.12, tag='shell')).add(lid, Rl, (0, R + 10, Hr - 6))
    return X


def toy_car():
    """red ride-on toy car (front +x), 520 long, roof at 300"""
    X = Model()
    Rd = X.mesh(S('enamel_red', 'lms', v=0.18, tag='car')); Bk = X.mesh(S('rubber_black', 'lm')); Y = X.mesh(S('pool_yellow', 'lm', tag='car'))
    Gl = X.mesh(S('glass_t', 'glass', tag='car')); Wh = X.mesh(S('white', 'lm', tag='car'))
    rbox(Rd, (-260, -130, 40), (260, 130, 180), r=40, k=3, tile=256)
    rbox(Rd, (-180, -120, 170), (100, 120, 300), r=30, k=3, tile=256)
    Gl.poly([np.array([102, -96, 190]), np.array([102, 96, 190]), np.array([70, 96, 286]), np.array([70, -96, 286])], (0.95, 0, 0.3),
            [(0, 1), (1, 1), (1, 0), (0, 0)])
    for (x, y) in ((-170, -130), (-170, 130), (170, -130), (170, 130)):
        w = Mesh(); tube(w, [(0, -18, 0), (0, 18, 0)], 50, nseg=16)
        Bk.add(w, t=(x, y + (6 if y > 0 else -6), 50))
        disc_axis(Y, (x, y + (26 if y > 0 else -26), 50), 24, (0, 1 if y > 0 else -1, 0), n=12)
    for y in (-80, 80):
        sphere(Y, (262, y, 130), 18, nu=10, nv=6)
    rbox(Wh, (250, -90, 70), (266, 90, 100), r=6, k=2)
    return X


def round_bed():
    """round garden bed edged with stones: soil mound, shrubs and a cabbage tree in the middle (world-centred)"""
    X = Model()
    St = X.mesh(S('stone_m', 'lm', shade=60, tag='bed')); So = X.mesh(S('soil_m', 'lm'))
    R = L.ROUND_BED_R
    rng = np.random.default_rng(7)
    for k in range(22):
        a = 2 * math.pi * k / 22
        ellipsoid(St, (math.cos(a) * R, math.sin(a) * R, 14), 30, 24, 22, nu=10, nv=5, flat_bottom=-14, R=rot_z(a + math.pi / 2))
    return X


def slide():
    """toddler slide (world coords): platform on four legs, a ladder at the back (west), the yellow chute down to the
    east, side rails"""
    X = Model()
    Y = X.mesh(S('pool_yellow', 'lms', v=0.15, tag='slide')); Bl = X.mesh(S('pool_blue', 'lms', v=0.15, tag='slide')); Rd = X.mesh(S('enamel_red', 'lms', v=0.15, tag='slide'))
    x0, y0, x1, y1 = L.SLIDE
    z = L.SLIDE_Z; run = L.SLIDE_RUN
    rbox(Bl, (x0, y0, z - 20), (x1, y1, z), r=4, k=2, tile=128)
    for (x, y) in ((x0 + 14, y0 + 14), (x0 + 14, y1 - 14), (x1 - 14, y0 + 14), (x1 - 14, y1 - 14)):
        tube(Rd, [(x, y, 0), (x, y, z - 18)], 12, nseg=10)
    for y in (y0 + 14, y1 - 14):
        tube(Rd, [(x0 + 14, y, z), (x0 + 14, y, z + 140), (x1 - 14, y, z + 140), (x1 - 14, y, z)], 8, nseg=8)
    for y in (y0 - 6, y1 + 6):
        bar(Rd, (x0 - 160, y, 0), (x0 + 6, y, z + 120), 8)
    for k in range(1, 9):
        t = k / 9
        bar(Bl, (x0 - 160 + 166 * t, y0 - 6, (z + 120) * t), (x0 - 160 + 166 * t, y1 + 6, (z + 120) * t), 6)
    nu = 16
    P = np.zeros((nu + 1, 7, 3)); UV = np.zeros((nu + 1, 7, 2))
    for i in range(nu + 1):
        t = i / nu
        x = x1 + run * t; zz = z * (1 - t) + 2 + 30 * (t > 0.92) * (t - 0.92) / 0.08 * 0
        for j in range(7):
            a = math.pi * j / 6
            P[i, j] = (x, (y0 + y1) / 2 - 56 * math.cos(a), zz + 4 + 30 * (1 - math.sin(a)))
            UV[i, j] = (j / 6, t * 4)
    Y.grid(P, grid_normals(P, True), UV)
    tube(Rd, [(x1 + run * 0.6, y0 + 10, z * 0.4 + 6), (x1 + run * 0.6, y0 + 10, 0)], 8, nseg=8)
    tube(Rd, [(x1 + run * 0.6, y1 - 10, z * 0.4 + 6), (x1 + run * 0.6, y1 - 10, 0)], 8, nseg=8)
    return X


def log_pile(L_=420, D=150, H=300, seed=3):
    """stack of split firewood between two posts (origin floor centre, long axis x)"""
    X = Model()
    W = X.mesh(S('timber', 'lm', shade=60, tag='logs')); E = X.mesh(S('timber_pale', 'lm', tag='logend')); Pst = X.mesh(S('timber_grey', 'lm', tag='logs'))
    rng = np.random.default_rng(seed)
    r = 24
    for row in range(int(H / (2 * r * 0.87))):
        z = r + row * 2 * r * 0.87
        off = (row % 2) * r
        y = -D / 2 + r + off
        while y < D / 2 - r + 1:
            rr = r * rng.uniform(0.85, 1.05)
            tube(W, [(-L_ / 2 + 10, y, z), (L_ / 2 - 10, y, z)], rr, nseg=8, caps=(False, False))
            for xe, sg in ((-L_ / 2 + 10, -1), (L_ / 2 - 10, 1)):
                disc_axis(E, (xe, y, z), rr, (sg, 0, 0), n=8)
            y += 2 * r
    for xe in (-L_ / 2 - 6, L_ / 2 + 6):
        rbox(Pst, (xe - 8, -D / 2, 0), (xe + 8, D / 2, H + 30), r=2, k=1, tile=128)
    return X


def bird_bath():
    """concrete bird bath on a fluted pedestal, a sparrow on the rim (origin floor centre)"""
    X = Model()
    C_ = X.mesh(S('stone_m', 'lm', tag='bath')); Wt = X.mesh(S('pool_blue', 'lms', v=0.3, tag='bathw')); Bd = X.mesh(S('timber', 'lm', tag='bird'))
    revolve(C_, [(0, 0), (70, 0), (70, 16), (40, 30), (26, 60), (30, 180), (22, 250), (40, 270), (120, 290), (130, 310), (110, 314), (40, 300), (0, 300)], n=24,
            rfun=lambda a, r, z: r * (1 + (0.06 * math.cos(a * 10) if 60 < z < 240 else 0)))
    disc(Wt, 108, 306, n=24)
    ellipsoid(Bd, (100, 0, 326), 14, 9, 10, nu=10, nv=6); sphere(Bd, (110, 0, 338), 7, nu=8, nv=5)
    return X


def compost_bin():
    X = Model()
    B = X.mesh(S('rubber_black', 'lms', v=0.08, tag='compost'))
    revolve(B, [(0, 0), (150, 0), (150, 6), (110, 420), (120, 430), (80, 460), (0, 470)], n=24)
    return X


def wheelie_bin(lid='enamel_red'):
    """wheelie bin (front +x, wheels at the back -x), 300 x 300 x 520"""
    X = Model()
    G_ = X.mesh(S('bin_green', 'lms', v=0.1)); Ld = X.mesh(S(lid, 'lms', v=0.12, tag='bin')); Bk = X.mesh(S('rubber_black', 'lm'))
    hull_ = Mesh()
    revolve(hull_, [(0, 24), (120, 24), (150, 470), (0, 470)], n=4, a0=45, a1=405)
    G_.add(hull_, np.diag([1.0, 1.0, 1.0]))
    rbox(Ld, (-160, -160, 470), (160, 160, 500), r=8, k=2, tile=128)
    bar(Ld, (-170, -120, 490), (-170, 120, 490), 10)
    for s_ in (-1, 1):
        w = Mesh(); tube(w, [(0, -14, 0), (0, 14, 0)], 40, nseg=14)
        Bk.add(w, t=(-120, s_ * 130, 40))
    return X


def dog_bowl():
    X = Model()
    B = X.mesh(S('dogbowl', 'lms', v=0.15)); Bn = X.mesh(S('bone', 'lm'))
    revolve(B, [(0, 0), (60, 0), (74, 40), (70, 42), (56, 8), (0, 8)], n=28)
    bar(Bn, (-50, 90, 10), (50, 90, 10), 10)
    for s_ in (-1, 1):
        for t in (-12, 12):
            Bn.add(_ball(12), t=(s_ * 56, 90 + t, 10))
    return X


# ================================================================================================= picnic table + parasol
def picnic_table():
    """timber picnic table with attached benches + the parasol through the middle (origin floor centre)"""
    X = Model()
    W = X.mesh(S('timber', 'lm', shade=40)); Wg = X.mesh(S('timber_grey', 'lm')); P = X.mesh(S('parasol', 'lm', two=True, shade=30))
    A_ = X.mesh(S('alu', 'lms'))
    hl, hw = L.TABLE_L / 2, L.TABLE_W / 2
    zt, zb = L.TABLE_Z, L.BENCH_Z
    by = hw + L.BENCH_GAP
    n = 5
    for k in range(n):
        y0 = -hw + k * (2 * hw) / n + 3; y1 = -hw + (k + 1) * (2 * hw) / n - 3
        rbox(W, (-hl, y0, zt - 22), (hl, y1, zt), r=3, k=2, tile=256)
    for s_ in (-1, 1):
        for k in range(2):
            y0 = s_ * by + (k - 1) * (L.BENCH_W / 2) + (0 if s_ > 0 else 0)
            ya, yb = (s_ * by - L.BENCH_W / 2 + k * L.BENCH_W / 2 + 3, s_ * by - L.BENCH_W / 2 + (k + 1) * L.BENCH_W / 2 - 3)
            rbox(W, (-hl + 20, ya, zb - 22), (hl - 20, yb, zb), r=3, k=2, tile=256)
    # A-frames at each end: legs from the bench ends up to the table, cross bearers
    for x in (-hl + 90, hl - 90):
        for s_ in (-1, 1):
            bar(Wg, (x, s_ * (by + 30), 0), (x, s_ * (hw - 60), zt - 22), 12, n=6) if False else None
            rbox(Wg, (x - 18, s_ * (by + 40) - 18, 0), (x + 18, s_ * (by + 40) + 18, zb - 22), r=2, k=1, tile=128) if False else None
        legs = Mesh()
        for s_ in (-1, 1):
            q0 = np.array([x, s_ * (by + 40), 0.0]); q1 = np.array([x, s_ * 60, zt - 22])
            d = q1 - q0; ln = np.linalg.norm(d); d /= ln
            side = np.cross(d, [1, 0, 0]); side /= np.linalg.norm(side)
            rbox(legs, (-16, -14, 0), (16, 14, ln), r=2, k=1, tile=128)
            Rm = np.stack([[1, 0, 0], np.cross(d, [1, 0, 0]) * -1, d], 1)
            Wg.add(legs, Rm, q0); legs = Mesh()
        rbox(Wg, (x - 16, -by - L.BENCH_W / 2, zb - 54), (x + 16, by + L.BENCH_W / 2, zb - 22), r=2, k=1, tile=128)      # bench bearer
        rbox(Wg, (x - 16, -hw, zt - 54), (x + 16, hw, zt - 22), r=2, k=1, tile=128)                                     # table bearer
    # parasol: pole, crank, canopy panels (alternating), ribs, finial; base under the table
    Ph = L.PARASOL_Z
    revolve(A_, [(0, 0), (60, 0), (50, 20), (14, 30), (0, 30)], n=20)
    tube(A_, [(0, 0, 20), (0, 0, Ph + 190)], 10, nseg=10)
    rbox(A_, (-6, -6, Ph - 380), (30, 6, Ph - 340), r=4, k=2)
    for k in range(8):
        a0, a1 = k * 45, (k + 1) * 45
        Pk = P if k % 2 == 0 else X.mesh(S('pool_white', 'lm', two=True, shade=30, tag='canopy'))
        revolve(Pk, [(L.PARASOL_R, Ph), (L.PARASOL_R * 0.5, Ph + 130), (8, Ph + 200)], n=6, a0=a0, a1=a1, vlen=512)
        a = math.radians(a0)
        bar(A_, (0, 0, Ph + 196), (L.PARASOL_R * math.cos(a), L.PARASOL_R * math.sin(a), Ph - 2), 3, n=5)
        bar(A_, (0, 0, Ph - 300), (L.PARASOL_R * 0.45 * math.cos(a), L.PARASOL_R * 0.45 * math.sin(a), Ph + 140), 2.4, n=4)
    revolve(W, [(0, Ph + 196), (16, Ph + 200), (12, Ph + 224), (0, Ph + 236)], n=12)
    return X


# ================================================================================================= sun lounger
def lounger():
    """aluminium sun lounger, origin floor centre, long axis x, backrest raised at the west (-x) end, striped sling"""
    X = Model()
    A_ = X.mesh(S('alu', 'lms')); Cl = X.mesh(S('lounger', 'lm', two=True, shade=60))
    hl, hw = L.LOUNGER_L / 2, L.LOUNGER_W / 2
    zs = L.LOUNGER_SEAT
    back_l = 360
    bt = math.radians(L.LOUNGER_BACK)
    xb = -hl + back_l * math.cos(bt)                 # backrest hinge x
    top = (-hl, zs + back_l * math.sin(bt))
    for s_ in (-1, 1):
        y = s_ * hw
        tube(A_, [(hl, y, zs), (xb, y, zs), (top[0], y, top[1])], 7, nseg=8)
        bar(A_, (hl - 30, y, zs), (hl - 50, y, 0), 7); bar(A_, (xb + 40, y, zs), (xb + 60, y, 0), 7)
        bar(A_, (xb + 20, y, 0), (xb + 20 - 120, y, zs + 60), 5)
    for x in (hl, xb):
        bar(A_, (x, -hw, zs), (x, hw, zs), 7)
    bar(A_, (top[0], -hw, top[1]), (top[0], hw, top[1]), 7)
    Cl.poly([np.array([hl - 10, -hw + 8, zs + 2]), np.array([hl - 10, hw - 8, zs + 2]), np.array([xb, hw - 8, zs + 2]), np.array([xb, -hw + 8, zs + 2])],
            (0, 0, 1), [(0, 0), (1, 0), (1, 2.5), (0, 2.5)])
    Cl.poly([np.array([xb, -hw + 8, zs + 2]), np.array([xb, hw - 8, zs + 2]), np.array([top[0] + 8, hw - 8, top[1] + 2]),
             np.array([top[0] + 8, -hw + 8, top[1] + 2])], (math.sin(bt), 0, math.cos(bt)), [(0, 2.5), (1, 2.5), (1, 3.6), (0, 3.6)])
    return X


def towel_ramp():
    """beach towel hanging from the lounger's foot down to the lawn (world-relative: origin = foot end top centre,
    runs +x down to the lawn over TOWEL_RUN)"""
    X = Model()
    T_ = X.mesh(S('towel', 'lm', two=True, shade=80))
    zs = L.LOUNGER_SEAT
    nu, nv = 6, 10
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        t = i / nv
        for j in range(nu + 1):
            y = -110 + 220 * j / nu
            P[i, j] = (t * L.TOWEL_RUN, y, zs * (1 - t) + 2 + 3 * math.sin(j * 1.3 + i))
            UV[i, j] = (j / nu, t * 3)
    T_.grid(P, grid_normals(P), UV)
    return X


def lounger_bits():
    X = Model()
    Sc = X.mesh(S('sunscreen', 'lm')); Mg = X.mesh(S('magazine', 'lm')); Bk = X.mesh(S('black', 'lms'))
    revolve(Sc, [(0, 0), (16, 0), (16, 60), (8, 70), (8, 80), (0, 80)], n=12)
    rbox(Mg, (60, -50, 0), (140, 50, 3), r=0.5, k=1, tile=100)
    for s_ in (-1, 1):
        ellipsoid(Bk, (-60, s_ * 14, 6), 12, 12, 3, nu=10, nv=4)
    bar(Bk, (-60, -4, 8), (-60, 4, 8), 1.5, n=4)
    return X


def jandals():
    X = Model()
    for k, (x, y, a, col) in enumerate(((0, 0, 0.2, 'jandal_blue'), (20, 60, -0.1, 'jandal_blue'))):
        m = Mesh()
        prism(m, [(math.cos(t) * 60, math.sin(t) * 22 * (1 if math.cos(t) > 0 else 0.85)) for t in np.linspace(0, 2 * math.pi, 18, endpoint=False)], 0, 6, tile=64)
        tube(m, [(-20, -18, 6), (24, 0, 14), (-20, 18, 6)], 2.5, nseg=5)
        X.mesh(S(col, 'lm')).add(m, rot_z(a), (x, y, 0))
    return X


# ================================================================================================= vege bed, garden
def tomato_plant(h=520, seed=1):
    X = Model()
    W = X.mesh(S('wood_handle', 'lm')); Lf = X.mesh(S('leaf_green', 'lm', shade=90)); To = X.mesh(S('tomato', 'lm'))
    bar(W, (0, 0, 0), (0, 0, h), 5, n=6)
    rng = np.random.default_rng(seed)
    for k in range(10):
        z = 60 + (h - 80) * k / 10
        a = rng.uniform(0, 2 * math.pi)
        ellipsoid(Lf, (math.cos(a) * 40, math.sin(a) * 40, z), 50, 40, 26, nu=10, nv=5, bump=lambda p, t: 1 + 0.2 * math.sin(4 * t))
        if k % 3 == 1:
            for j in range(3):
                sphere(To, (math.cos(a + 1) * 30 + j * 10, math.sin(a + 1) * 30, z - 30 - j * 12), 12, nu=8, nv=5)
    return X


def lettuce(r=60):
    X = Model()
    Lf = X.mesh(S('leaf_lettuce', 'lm', shade=90))
    for k in range(9):
        a = k * 2 * math.pi / 9
        ellipsoid(Lf, (math.cos(a) * r * 0.45, math.sin(a) * r * 0.45, 18), r * 0.55, r * 0.35, 22, nu=10, nv=5, R=rot_z(a))
    ellipsoid(Lf, (0, 0, 26), r * 0.4, r * 0.4, 28, nu=10, nv=6)
    return X


def carrot_row(n=6):
    X = Model()
    F = X.mesh(S('carrot_top', 'lm', shade=90, two=True)); O = X.mesh(S('mower_orange', 'lm', tag='carrot'))
    for k in range(n):
        y = -n * 25 + k * 50
        revolve(O, [(0, 0), (10, 0), (8, 12), (0, 14)], n=8, cy=y)
        for j in range(5):
            a = j * 2 * math.pi / 5
            F.poly([(0, y, 12), (math.cos(a) * 30, y + math.sin(a) * 30, 80), (math.cos(a + 0.3) * 30, y + math.sin(a + 0.3) * 30, 80)], (0, 0, 1),
                   [(0, 0), (1, 1), (0, 1)])
    return X


def wheelbarrow():
    """wheelbarrow (wheel at +x), origin floor centre"""
    X = Model()
    Rd = X.mesh(S('spade_red', 'lms', v=0.1)); Bk = X.mesh(S('rubber_black', 'lm')); St = X.mesh(S('steel', 'lm')); So = X.mesh(S('soil_m', 'lm'))
    revolve(Rd, [(0, 120), (150, 120), (210, 260), (204, 262), (144, 126), (0, 126)], n=24, rfun=lambda a, r, z: r * (1.25 if abs(math.cos(a)) > 0.7 else 1.0))
    disc(So, 180, 240, n=24)
    w = Mesh(); tube(w, [(0, -16, 0), (0, 16, 0)], 60, nseg=16)
    Bk.add(w, t=(250, 0, 60))
    for s_ in (-1, 1):
        bar(St, (250, s_ * 20, 60), (-300, s_ * 110, 220), 6)
        bar(St, (-100, s_ * 100, 150), (-120, s_ * 110, 0), 6)
    return X


def watering_can():
    X = Model()
    G_ = X.mesh(S('mower_green', 'lms', v=0.12, tag='can'))
    revolve(G_, [(0, 0), (60, 0), (60, 140), (50, 150), (0, 150)], n=20)
    tube(G_, [(50, 0, 40), (120, 0, 150), (150, 0, 180)], [10, 7, 7], nseg=8)
    tube(G_, arc_path((-20, 0, 150), 50, 0, 180, n=10, axis='y'), 5, nseg=6, caps=(False, False))
    return X


def bucket_spade():
    X = Model()
    B = X.mesh(S('bucket_blue', 'lm')); Rd = X.mesh(S('spade_red', 'lm'))
    revolve(B, [(0, 0), (50, 0), (64, 110), (60, 112), (46, 4), (0, 4)], n=20)
    bar(Rd, (90, 30, 6), (200, 70, 6), 4)
    q = [np.array([70, 20, 4]), np.array([100, 0, 4]), np.array([110, 30, 4]), np.array([80, 50, 4])]
    Rd.poly(q, (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return X


def cricket_set():
    """backyard cricket: three stumps with bails, a bat lying on the grass, a ball (origin floor centre of the stumps)"""
    X = Model()
    S_ = X.mesh(S('stumps', 'lm')); W = X.mesh(S('bat_willow', 'lm')); B = X.mesh(S('ball_red', 'lms'))
    for y in (-22, 0, 22):
        tube(S_, [(0, y, 0), (0, y, 360)], 9, nseg=10)
    for y in (-11, 11):
        bar(S_, (0, y - 10, 364), (0, y + 10, 364), 4, n=5)
    rbox(W, (120, -160, 0), (160, 120, 22), r=8, k=2)
    bar(X.mesh(S('rubber_black', 'lm')), (140, 120, 11), (140, 290, 11), 10)
    B.add(_ball(18, 12), t=(-200, 140, 18))
    return X


def frisbee():
    X = Model()
    revolve(X.mesh(S('frisbee', 'lm')), [(0, 18), (100, 18), (108, 10), (104, 0), (96, 8), (0, 12)], n=28)
    return X


def gnome(hat='gnome_red', coat='gnome_blue', s=1.0, fishing=False):
    """garden gnome ~170 tall (origin floor centre, faces +x)"""
    X = Model()
    R_ = X.mesh(S(hat, 'lm')); Bl = X.mesh(S(coat, 'lm')); Sk = X.mesh(S('skin', 'lm')); Wh = X.mesh(S('beard', 'lm')); Bk = X.mesh(S('black', 'lm'))
    revolve(Bk, [(0, 0), (34, 0), (34, 10), (0, 10)], n=16)
    ellipsoid(Bl, (0, 0, 60), 36, 34, 52, nu=14, nv=8)
    ellipsoid(Bk, (0, 0, 54), 37, 35, 5, nu=14, nv=3)
    ellipsoid(Sk, (6, 0, 118), 24, 24, 24, nu=12, nv=8)
    ellipsoid(Wh, (20, 0, 100), 18, 24, 32, nu=10, nv=6)
    sphere(Sk, (30, 0, 118), 6, nu=8, nv=5)
    revolve(R_, [(0.1, 200), (28, 128), (0, 128)], n=14)
    for s_ in (-1, 1):
        tube(Bl, [(0, s_ * 34, 90), (24, s_ * 30, 60)], 10, nseg=8)
        sphere(Sk, (28, s_ * 26, 58), 8, nu=8, nv=5)
    if fishing:
        bar(X.mesh(S('wood_handle', 'lm')), (30, -20, 60), (140, -40, 230), 3, n=5)
    X2 = Model()
    for sh, M_ in X.m.items():
        X2.mesh(sh).add(M_, sc=s)
    return X2


def sprinkler_base():
    X = Model()
    G_ = X.mesh(S('mower_green', 'lm', tag='spr')); Y = X.mesh(S('reel_yellow', 'lm'))
    revolve(G_, [(0, 0), (70, 0), (60, 14), (20, 24), (14, 60), (0, 64)], n=20)
    tube(Y, [(70, 0, 4), (120, 0, 4)], 8, nseg=8)
    return X


def sprinkler_arm():
    """rotating sprinkler head + water jets (IQM mover, origin at the pivot)"""
    X = Model()
    Y = X.mesh(S('reel_yellow', 'dyn')); Sp = X.mesh(S('spray', 'add'))
    tube(Y, [(-60, 0, 10), (60, 0, 10)], 6, nseg=8)
    for s_ in (-1, 1):
        tube(Y, [(s_ * 60, 0, 10), (s_ * 66, s_ * 10, 18)], 5, nseg=6)
        base = np.array([s_ * 66, s_ * 10, 18])
        for k in range(3):
            d = np.array([s_ * 1.0, s_ * (0.3 + 0.2 * k), 0.0]); d /= np.linalg.norm(d)
            side = np.array([-d[1], d[0], 0]) * 10
            pts = [base + d * t * 240 + [0, 0, 240 * t - 300 * t * t] for t in np.linspace(0, 1, 7)]
            for a_, b_ in zip(pts, pts[1:]):
                Sp.poly([a_ - side, a_ + side, b_ + side, b_ - side], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
                Sp.poly([a_ - [0, 0, 10], a_ + [0, 0, 10], b_ + [0, 0, 10], b_ - [0, 0, 10]], (d[1], -d[0], 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return X


def hose_reel():
    """hose reel cart with the hose wound on (origin floor centre, handle at -x)"""
    X = Model()
    Y = X.mesh(S('reel_yellow', 'lms', v=0.1)); H = X.mesh(S('hose_green', 'lm', shade=60)); Bk = X.mesh(S('rubber_black', 'lm'))
    for s_ in (-1, 1):
        m = Mesh(); disc_axis(m, (0, 0, 0), 150, (0, 1, 0), n=24)
        Y.add(m, t=(0, s_ * 100, 200))
        bar(Y, (0, s_ * 110, 200), (-60, s_ * 110, 0), 7); bar(Y, (0, s_ * 110, 200), (60, s_ * 110, 0), 7)
        w = Mesh(); tube(w, [(0, -10, 0), (0, 10, 0)], 40, nseg=14)
        Bk.add(w, t=(60, s_ * 124, 40))
        bar(Y, (-60, s_ * 110, 0), (-160, s_ * 100, 380), 6)
    bar(Bk, (-160, -110, 380), (-160, 110, 380), 9)
    m = Mesh(); tube(m, [(0, -96, 0), (0, 96, 0)], 112, nseg=24)
    H.add(m, t=(0, 0, 200))
    return X


def hose_path():
    """garden hose from the tap... from the reel snaking across the lawn to the sprinkler (world coords)"""
    X = Model()
    H = X.mesh(S('hose_green', 'lm', tag='hose'))
    rx, ry = L.HOSE_REEL; sx, sy = L.SPRINKLER
    ctrl = [(rx, ry - 100), (rx - 120, ry - 500), (900, 1100), (1000, 600), (760, 260), (620, 0), (sx + 120, sy)]
    pts = []
    for (a, b) in zip(ctrl, ctrl[1:]):
        for t in np.linspace(0, 1, 8, endpoint=False):
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    pts.append(ctrl[-1])
    sm = [pts[0]] + [tuple((np.array(pts[i - 1]) + 2 * np.array(pts[i]) + np.array(pts[i + 1])) / 4) for i in range(1, len(pts) - 1)] + [pts[-1]]
    tube(H, [(x, y, 8) for (x, y) in sm], 8, nseg=8)
    return X


# ================================================================================================= ants
def ant(s=1.0):
    """one ant ~50 long (5 mm... at 5u/cm a 1 cm ant), faces +x, origin floor centre"""
    X = Model()
    A_ = X.mesh(S('ant', 'lms', v=0.15))
    ellipsoid(A_, (-18 * s, 0, 12 * s), 14 * s, 10 * s, 10 * s, nu=10, nv=6)
    ellipsoid(A_, (0, 0, 11 * s), 7 * s, 5 * s, 5 * s, nu=8, nv=5)
    sphere(A_, (14 * s, 0, 12 * s), 8 * s, nu=10, nv=6)
    for s_ in (-1, 1):
        tube(A_, [(18 * s, s_ * 3 * s, 16 * s), (26 * s, s_ * 10 * s, 26 * s), (34 * s, s_ * 12 * s, 24 * s)], 0.9 * s, nseg=4)
        for k, dx in enumerate((-6, 0, 6)):
            tube(A_, [(dx * s, s_ * 4 * s, 10 * s), (dx * s * 1.6, s_ * 16 * s, 14 * s), (dx * s * 2.4, s_ * 22 * s, 0.8)], 1.1 * s, nseg=4)
    return X


def ant_trail(R=260, n=22):
    """ants marching round the ant hill (IQM for a func_rotating at its centre)"""
    X = Model()
    one = ant()
    rng = np.random.default_rng(5)
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.05, 0.05)
        rr = R + rng.uniform(-12, 12)
        Rm = rot_z(a + math.pi / 2)
        for sh, M_ in one.m.items():
            X.mesh(sh.replace('_lms', '_dyn') if False else S('ant', 'dynenv')).add(M_, Rm, (rr * math.cos(a), rr * math.sin(a), 0))
        if k % 4 == 0:
            X.mesh(S('crumb', 'dyn')).add(_ball(8, 8), t=((rr) * math.cos(a) + 14 * math.cos(a + math.pi / 2), rr * math.sin(a) + 14 * math.sin(a + math.pi / 2), 30))
    return X


def ant_hill():
    """mound of fine soil with an entrance tunnel facing north (origin floor centre)"""
    X = Model()
    Mo = X.mesh(S('mound', 'lm', shade=80)); Dk = X.mesh(S('black', 'lm', tag='hole'))
    R, H = L.ANT_R, L.ANT_H
    da = L.ANT_DOOR
    prof = [(R * (1 - t) + 0.1, H * math.sin((1 - (1 - t) ** 2) * math.pi / 2) if t < 1 else H) for t in np.linspace(0, 1, 9)]
    rng = np.random.default_rng(3)
    ofs = rng.uniform(-1, 1, 12)
    revolve(Mo, prof, n=48, rfun=lambda a, r, z: r * (1 + 0.06 * math.sin(5 * a + 1)) * (0.55 if abs(((math.degrees(a) - da + 180) % 360) - 180) < 14 and z < 52 else 1.0))
    # entrance: dark arch on the north face
    c = np.array(L.ang_pt(0, 0, R * 0.62, da))
    n_ = np.array([math.cos(math.radians(da)), math.sin(math.radians(da)), 0])
    t_ = np.array([-n_[1], n_[0], 0])
    pts = [np.array([*c, 0]) + t_ * 30 * math.cos(a) + np.array([0, 0, 50 * math.sin(a)]) + n_ * 2 for a in np.linspace(0, math.pi, 11)]
    Dk.poly(pts, n_, [(0.5, 0.5)] * len(pts))
    for k in range(18):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(R * 0.9, R * 1.3)
        Mo.add(_ball(rng.uniform(4, 9), 6), t=(rr * math.cos(a), rr * math.sin(a), 1))
    return X


def queen_ant():
    X = ant(4.0)
    W = X.mesh(S('glass_t', 'glass', two=True, tag='wing'))
    for s_ in (-1, 1):
        W.poly([(-10, s_ * 10, 70), (-110, s_ * 80, 90), (-170, s_ * 60, 80), (-60, s_ * 10, 66)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return X


def larvae(n=7):
    X = Model()
    Lv = X.mesh(S('larva', 'lm', shade=80))
    rng = np.random.default_rng(9)
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, 90)
        ellipsoid(Lv, (rr * math.cos(a), rr * math.sin(a), 16), 30, 18, 16, nu=12, nv=6, R=rot_z(a))
    return X


def seed_pile():
    X = Model()
    Sd = X.mesh(S('seed', 'lm')); Su = X.mesh(S('sugar', 'lm')); Cr = X.mesh(S('crumb', 'lm', shade=80))
    rng = np.random.default_rng(13)
    for k in range(30):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, 80)
        ellipsoid(Sd, (rr * math.cos(a), rr * math.sin(a), 8 + max(0, 30 - rr * 0.3)), 12, 7, 6, nu=8, nv=4, R=rot_z(rng.uniform(0, 3)))
    rbox(Su, (90, -40, 0), (170, 40, 80), r=4, k=2, tile=80)
    cushion(Cr, (-180, -60, 0), (-60, 60, 60), puff=10, r=20, tile=64)
    return X


def colony_pillar(h=448, r=110, seed=1):
    """knobbly earth pillar from floor to roof (origin floor centre)"""
    X = Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6, 3)
    revolve(X.mesh(S('mound', 'lm', shade=80, tag='pillar')), [(r * 1.5, 0), (r * 1.1, h * 0.2), (r, h * 0.5), (r * 1.1, h * 0.8), (r * 1.5, h)], n=24,
            rfun=lambda a, rr, z: rr * (1 + 0.1 * math.sin(3 * a + ph[0] + z / 60) + 0.05 * math.sin(7 * a + ph[1])))
    return X


# ================================================================================================= outside the fence
def cabbage_tree(h=900, seed=1):
    """NZ cabbage tree: slim trunk forking into tufts of strap leaves (origin floor centre)"""
    X = Model()
    T_ = X.mesh(S('cabbage_tree', 'lm')); F = X.mesh(S('flax', 'lm', shade=90, two=True, tag='ct'))
    rng = np.random.default_rng(seed)
    tube(T_, [(0, 0, 0), (10, 0, h * 0.5), (0, 0, h * 0.7)], [26, 20, 18], nseg=10)
    for k in range(3):
        a = k * 2 * math.pi / 3 + rng.uniform(-0.3, 0.3)
        tip = np.array([math.cos(a) * 160, math.sin(a) * 160, h + rng.uniform(-60, 60)])
        tube(T_, [(0, 0, h * 0.7), tip * [0.5, 0.5, 1] + [0, 0, -h * 0.15], tip], [16, 12, 10], nseg=8)
        for j in range(18):
            b = j * 2 * math.pi / 18; lean = rng.uniform(0.3, 1.6)
            d = np.array([math.cos(b) * math.sin(lean), math.sin(b) * math.sin(lean), math.cos(lean)])
            side = np.array([-math.sin(b), math.cos(b), 0]) * 7
            e = tip + d * rng.uniform(140, 220)
            F.poly([tip - side, tip + side, e], np.cross(side, e - tip), [(0, 0), (1, 0), (0.5, 1)])
    return X


def fence_rails(side):
    """horizontal rails + posts on the yard side of one fence run (world coords). side: 'w', 'e', 's'"""
    X = Model()
    W = X.mesh(S('timber_grey', 'lm', shade=40))
    t = L.FENCE_T
    if side == 's':
        run = [(x, L.YS + t) for x in (-L.XW, L.XW)]
    elif side == 'w':
        run = [(-L.XW + t, y) for y in (L.YS, L.YN)]
    else:
        run = [(L.XW - t, y) for y in (L.YS, L.YN)]
    (ax, ay), (bx, by) = run
    n_ = (0, 1) if side == 's' else ((1, 0) if side == 'w' else (-1, 0))
    for z in (160, 760):
        if side == 's': rbox(W, (ax, ay, z), (bx, ay + 22, z + 70), r=2, k=1, tile=256)
        elif side == 'w': rbox(W, (ax, ay, z), (ax + 22, by, z + 70), r=2, k=1, tile=256)
        else: rbox(W, (ax - 22, ay, z), (ax, by, z + 70), r=2, k=1, tile=256)
    L_ = (bx - ax) if side == 's' else (by - ay)
    for k in range(1, int(L_ // 1150)):
        u = (ax if side == 's' else ay) + k * L_ / int(L_ // 1150)
        if side == 's': rbox(W, (u - 30, ay, 0), (u + 30, ay + 50, L.FENCE_H + 20), r=3, k=1, tile=256)
        elif side == 'w': rbox(W, (ax, u - 30, 0), (ax + 50, u + 30, L.FENCE_H + 20), r=3, k=1, tile=256)
        else: rbox(W, (ax - 50, u - 30, 0), (ax, u + 30, L.FENCE_H + 20), r=3, k=1, tile=256)
    return X


def grass_tuft(seed=1):
    X = Model()
    G_ = X.mesh(S('leaf_green', 'lm', two=True, shade=90, tag='tuft'))
    rng = np.random.default_rng(seed)
    for k in range(14):
        a = rng.uniform(0, 2 * math.pi); h = rng.uniform(30, 70); lean = rng.uniform(0.1, 0.5)
        base = np.array([math.cos(a) * 8, math.sin(a) * 8, 0])
        d = np.array([math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)])
        side = np.array([-math.sin(a), math.cos(a), 0]) * 3
        G_.poly([base - side, base + side, base + d * h], np.cross(side, d), [(0, 0), (1, 0), (0.5, 1)])
    return X


# ================================================================================================= make
def make():
    os.makedirs(out(MD), exist_ok=True)
    make_textures()
    save('kettle', kettle()); save('briq_steps', briq_steps()); save('charcoal_bag', charcoal_bag()); save('tongs', tongs()); save('esky', esky())
    save('pool', pool()); save_iqm('pool_floaters', pool_floaters()); save('ball', beach_ball())
    for n in (8, 7):
        save(f'foam_{n}', foam_steps(n))
    save('pergola', pergola()); save('deck_trim', deck_trim()); save('house_trim', house_trim()); save('heat_pump', heat_pump())
    save('deck_setting', deck_setting()); save('planter_lemon', planter()); save('planter_flax', planter(200, 100, 'flax'))
    save_iqm('rotary_line', rotary_line()); save('rotary_mast', rotary_mast())
    save('shed_trim', shed_trim()); save('workbench', workbench()); save('lawnmower', lawnmower()); save('shelf_unit', shelf_unit())
    save('garden_tools', garden_tools()); save('sack', sack()); save('pot_stack', pot_stack())
    save('kennel', kennel()); save('dog_bowl', dog_bowl()); save('cubby', cubby()); save('sandpit', sandpit()); save('toy_car', toy_car())
    save('round_bed', round_bed()); save('slide', slide()); save('log_pile', log_pile()); save('compost', compost_bin()); save('bird_bath', bird_bath()); save('bin_red', wheelie_bin()); save('bin_yellow', wheelie_bin('pool_yellow'))
    save('picnic_table', picnic_table())
    save('lounger', lounger()); save('towel_ramp', towel_ramp()); save('lounger_bits', lounger_bits()); save('jandals', jandals())
    for k in range(3): save(f'tomato_{k}', tomato_plant(480 + 60 * k, k + 1))
    save('lettuce', lettuce()); save('carrots', carrot_row()); save('wheelbarrow', wheelbarrow()); save('watering_can', watering_can())
    save('bucket_spade', bucket_spade()); save('cricket', cricket_set()); save('frisbee', frisbee())
    save('gnome', gnome()); save('gnome_b', gnome('gnome_green', 'gnome_red', 1.0, True))
    save('sprinkler_base', sprinkler_base()); save_iqm('sprinkler_arm', sprinkler_arm()); save('hose_reel', hose_reel()); save('hose_path', hose_path())
    save('ant', ant()); save_iqm('ant_trail', ant_trail()); save('ant_hill', ant_hill()); save('queen', queen_ant()); save('larvae', larvae())
    save('seed_pile', seed_pile())
    for k in range(4): save(f'pillar_{k}', colony_pillar(448, 100 + 15 * k, k + 1))
    for k in range(2): save(f'cabbage_tree_{k}', cabbage_tree(860 + 160 * k, k + 1))
    for sd in ('w', 'e', 's'): save(f'fence_{sd}', fence_rails(sd))
    for k in range(3): save(f'tuft_{k}', grass_tuft(k + 1))
