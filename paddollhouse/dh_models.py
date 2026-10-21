"""Custom MD3/IQM map objects for wop_paddollhouse (Padman's Dollhouse). All geometry and art is original and
generated here.

    make() -> writes models/paddollhouse/*.md3/*.iqm and their images (shaders are registered in dhlib.REG)

Two scales live in this map:
  bedroom pieces (bookshelf, bed, toy chest, toys)  ~12u per cm
  dollhouse furniture (1:12 doll furniture)         1u per real-life cm (a doll table is 75u tall, Padman 56u)
Origin = floor centre unless noted, "front" faces +x (misc_model angle turns it). build_dollhouse.py reads the
geometry constants (and layout.py) so the invisible weapclip collision sits just inside the visible surfaces.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from dhlib import *
import dhlib
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


def tex_floral(n=256, bg=(255, 244, 248), seed=3, cols=((236, 120, 160), (250, 170, 196), (250, 210, 120)), leaf=(130, 186, 130), k=16, size=(8, 14)):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(k):
        cx, cy = r.uniform(0, n), r.uniform(0, n)
        col = tuple(int(v) for v in cols[r.integers(len(cols))]); rr = r.uniform(*size)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                x0, y0 = cx + ox, cy + oy
                for a in np.linspace(0, 2 * math.pi, 4)[:-1]:
                    d.ellipse((x0 + math.cos(a) * rr * 1.3 - 6, y0 + math.sin(a) * rr * 1.3 - 3, x0 + math.cos(a) * rr * 1.3 + 6, y0 + math.sin(a) * rr * 1.3 + 3), fill=leaf)
                for j in range(5):
                    a = j * 2 * math.pi / 5
                    d.ellipse((x0 + math.cos(a) * rr * 0.6 - rr * 0.55, y0 + math.sin(a) * rr * 0.6 - rr * 0.55, x0 + math.cos(a) * rr * 0.6 + rr * 0.55,
                               y0 + math.sin(a) * rr * 0.6 + rr * 0.55), fill=col)
                d.ellipse((x0 - rr * 0.3, y0 - rr * 0.3, x0 + rr * 0.3, y0 + rr * 0.3), fill=(255, 230, 120))
    return np.asarray(im, np.float32) + N3(n, 0.7, seed + 1, 4)


def tex_gingham(n=128, col=(240, 140, 170), k=8, seed=5):
    x, y = xy(n)
    a = ((x * k) % 1.0) < 0.5; b = ((y * k) % 1.0) < 0.5
    base = C((255, 252, 250))
    c = np.where((a & b)[..., None], C(col) * 0.9, np.where((a | b)[..., None], lerp(base, C(col), 0.5), base))
    return c + N3(n, 0.6, seed, 4)


def tex_fur(n=128, col=(196, 140, 84), seed=7):
    c = fill(n, col, 10, seed) + N3(n, 0.5, seed + 1, 18)
    st = np.asarray(img(noise(n, 0.5, seed + 2) * 40 + 128).resize((n, n // 8)).resize((n, n)), np.float32) - 128
    return c + st[..., None] * 0.3


def tex_letters(letter, bg, fg, n=128, seed=9):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, n - 7, n - 7), outline=tuple(fg), width=6)
    f = font(int(n * 0.66), serif=False)
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((n - (bb[2] - bb[0])) / 2 - bb[0], (n - (bb[3] - bb[1])) / 2 - bb[1]), letter, font=f, fill=tuple(fg))
    return np.asarray(im, np.float32) + N3(n, 0.8, seed, 4)


def tex_spines(w=256, h=256, seed=11, pal=None):
    r = np.random.default_rng(seed)
    pal = pal or [(200, 60, 80), (60, 120, 190), (250, 200, 60), (90, 170, 110), (160, 90, 190), (240, 140, 60), (60, 60, 90), (230, 230, 220)]
    im = Image.new('RGB', (w, h), (40, 30, 30)); d = ImageDraw.Draw(im)
    x = 0
    while x < w:
        bw = int(r.uniform(14, 34))
        col = tuple(int(v) for v in pal[r.integers(len(pal))])
        d.rectangle((x, 0, x + bw - 2, h), fill=col)
        for yy in (int(h * 0.12), int(h * 0.86)):
            d.rectangle((x + 2, yy, x + bw - 4, yy + 5), fill=(240, 220, 140))
        d.rectangle((x + 4, int(h * 0.35), x + bw - 6, int(h * 0.55)), fill=tuple(min(255, v + 50) for v in col))
        x += bw
    return np.asarray(im, np.float32) + N3(w, 0.8, seed + 1, 4, h)


def tex_stars(n=128, bg=(110, 160, 220), fg=(255, 230, 120), seed=13, k=7):
    im = Image.new('RGB', (n, n), tuple(bg)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(k):
        cx, cy, s = r.uniform(0, n), r.uniform(0, n), r.uniform(6, 12)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                p = []
                for j in range(10):
                    rr = s if j % 2 == 0 else s * 0.45
                    a = j * math.pi / 5 - math.pi / 2
                    p.append((cx + ox + rr * math.cos(a), cy + oy + rr * math.sin(a)))
                d.polygon(p, fill=tuple(fg))
    return np.asarray(im, np.float32) + N3(n, 0.8, seed, 3)


def tex_painting(kind, w=128, h=160, seed=15):
    im = Image.new('RGB', (w, h), (240, 230, 210)); d = ImageDraw.Draw(im)
    if kind == 'pad':            # a portrait of Padman: yellow face, red cap
        d.rectangle((0, 0, w, h), fill=(150, 190, 220))
        d.ellipse((w * 0.22, h * 0.25, w * 0.78, h * 0.72), fill=(250, 210, 60))
        d.pieslice((w * 0.18, h * 0.12, w * 0.82, h * 0.5), 180, 360, fill=(220, 40, 40))
        for ex in (0.4, 0.6): d.ellipse((w * ex - 6, h * 0.45 - 8, w * ex + 6, h * 0.45 + 8), fill=(255, 255, 255)); d.ellipse((w * ex - 3, h * 0.45 - 3, w * ex + 3, h * 0.45 + 3), fill=(0, 0, 0))
        d.arc((w * 0.38, h * 0.5, w * 0.62, h * 0.62), 20, 160, fill=(120, 40, 20), width=3)
        d.rectangle((w * 0.3, h * 0.72, w * 0.7, h), fill=(60, 90, 180))
    elif kind == 'sea':
        d.rectangle((0, 0, w, h * 0.55), fill=(170, 210, 240)); d.rectangle((0, h * 0.55, w, h), fill=(60, 120, 170))
        d.polygon([(w * 0.3, h * 0.55), (w * 0.5, h * 0.2), (w * 0.5, h * 0.55)], fill=(250, 250, 250))
        d.rectangle((w * 0.25, h * 0.55, w * 0.6, h * 0.6), fill=(150, 80, 40))
        d.ellipse((w * 0.7, h * 0.1, w * 0.85, h * 0.22), fill=(255, 230, 120))
    elif kind == 'flowers':
        d.rectangle((0, 0, w, h), fill=(60, 50, 60))
        d.polygon([(w * 0.35, h), (w * 0.65, h), (w * 0.6, h * 0.62), (w * 0.4, h * 0.62)], fill=(170, 130, 90))
        r = np.random.default_rng(seed)
        for _ in range(9):
            cx, cy = r.uniform(w * 0.25, w * 0.75), r.uniform(h * 0.2, h * 0.6)
            col = [(230, 80, 120), (250, 200, 80), (250, 250, 250), (200, 120, 220)][r.integers(4)]
            d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=col)
    elif kind == 'lady':
        d.rectangle((0, 0, w, h), fill=(80, 110, 90))
        d.ellipse((w * 0.32, h * 0.18, w * 0.68, h * 0.5), fill=(240, 210, 190))
        d.pieslice((w * 0.26, h * 0.1, w * 0.74, h * 0.62), 180, 360, fill=(120, 70, 40))
        d.polygon([(w * 0.15, h), (w * 0.85, h), (w * 0.62, h * 0.52), (w * 0.38, h * 0.52)], fill=(200, 80, 120))
    else:                        # stars chart
        d.rectangle((0, 0, w, h), fill=(20, 30, 70))
        r = np.random.default_rng(seed)
        pts = [(r.uniform(8, w - 8), r.uniform(8, h - 8)) for _ in range(30)]
        for (px, py) in pts: d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 220))
        d.line(pts[:7], fill=(160, 180, 255), width=1)
        d.ellipse((w * 0.6, h * 0.15, w * 0.9, h * 0.35), outline=(250, 230, 160), width=2)
    return np.asarray(im, np.float32) + N3(w, 0.8, seed, 3, h)


def tex_clockface(n=128):
    im = Image.new('RGB', (n, n), (250, 246, 230)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), outline=(40, 30, 20), width=4)
    for k in range(12):
        a = k * math.pi / 6
        d.line([(n / 2 + math.cos(a) * n * 0.36, n / 2 + math.sin(a) * n * 0.36), (n / 2 + math.cos(a) * n * 0.44, n / 2 + math.sin(a) * n * 0.44)], fill=(40, 30, 20), width=4)
    d.line([(n / 2, n / 2), (n / 2 + n * 0.22, n / 2 - n * 0.1)], fill=(20, 20, 20), width=5)
    d.line([(n / 2, n / 2), (n / 2 - n * 0.05, n / 2 - n * 0.34)], fill=(20, 20, 20), width=3)
    return np.asarray(im, np.float32)


def tex_globe(w=256, h=128, seed=17):
    x, y = xy(w, h)
    land = noise(w, 10, seed, h) > 0.5
    c = np.where(land[..., None], C((120, 170, 90)), C((90, 150, 210))) + N3(w, 1, seed + 1, 6, h)
    c = np.where(((x * 12 % 1) < 0.02)[..., None] | ((y * 6 % 1) < 0.03)[..., None], c * 0.8, c)
    return c


def tex_braid(n=512, seed=19):
    """braided round rug: concentric rings of twisted braid in pastel colours (fitted to a disc)"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy) * 2; a = np.arctan2(dy, dx)
    ring = rr * 22
    k = np.floor(ring).astype(int)
    pal = np.array([(240, 150, 180), (250, 220, 150), (170, 210, 220), (250, 250, 240), (200, 170, 220), (160, 210, 170)], np.float32)
    c = pal[k % len(pal)]
    tw = np.sin((a * (12 + k * 6)) + (ring % 1.0) * 6) * 0.5 + 0.5
    c = c * (0.75 + 0.3 * tw)[..., None]
    c = np.where(((ring % 1.0) < 0.08)[..., None], c * 0.7, c)
    return c + N3(n, 0.7, seed, 5)


def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((90, 80, 100)), C((250, 245, 240)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_cardboard(n=128, seed=27):
    c = fill(n, (190, 150, 100), 6, seed)
    x, y = xy(n)
    return np.where((np.abs(x - 0.5) < 0.04)[..., None], C((210, 190, 140)), c)


def tex_label(text, w, h, bg, fg, serif=False):
    return text_img(text, w, h, bg, fg, serif)


def tex_tartan(n=128, a=(160, 40, 50), b=(40, 60, 50), seed=29):
    x, y = xy(n)
    s = (np.sin(x * math.pi * 8) > 0.4).astype(np.float32) + (np.sin(y * math.pi * 8) > 0.4)
    c = lerp(C(a), C(b), (s / 2)[..., None])
    c = np.where(((np.abs(np.sin(x * math.pi * 16)) < 0.1) | (np.abs(np.sin(y * math.pi * 16)) < 0.1))[..., None], C((230, 200, 90)), c)
    return c + N3(n, 0.6, seed, 4)


def tex_keys(w=256, h=32):
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + 240
    c[(x * 26 % 1) < 0.06] = 40
    blk = ((x * 26) % 7)
    bl = np.isin(np.floor(x * 26) % 7, [0, 1, 3, 4, 5]) & ((x * 26 % 1) > 0.6) & (y < 0.6)
    c[bl] = 20
    return c


def make_textures():
    T('env', tex_env())
    T('wood_white', tex_wood(128, (244, 240, 232), 31, 6)); T('wood_honey', tex_wood(128, (200, 150, 96), 33)); T('wood_dark', tex_wood(128, (96, 60, 40), 35))
    T('wood_red', tex_wood(128, (190, 70, 70), 37, 4)); T('wood_mint', tex_wood(128, (160, 214, 196), 39, 4)); T('wood_pink', tex_wood(128, (240, 170, 196), 41, 4))
    T('wood_blue', tex_wood(128, (120, 160, 220), 43, 4)); T('wood_yellow', tex_wood(128, (250, 214, 100), 45, 4))
    T('floral', tex_floral()); T('floral_big', tex_floral(256, (250, 236, 244), 47, k=9, size=(16, 26))); T('gingham', tex_gingham())
    T('gingham_blue', tex_gingham(128, (120, 170, 230))); T('linen', fill(128, (250, 248, 242), 4, 49) + N3(128, 0.6, 50, 3))
    T('velvet_rose', fill(64, (190, 80, 110), 6, 51)); T('velvet_green', fill(64, (70, 130, 100), 6, 53)); T('velvet_blue', fill(64, (80, 100, 170), 6, 55))
    T('fur_tan', tex_fur()); T('fur_white', tex_fur(128, (246, 240, 236), 57)); T('fur_pink', tex_fur(128, (246, 190, 206), 59))
    T('felt_dark', fill(64, (40, 30, 30), 3, 61)); T('chrome', fill(64, (200, 204, 210), 4, 63)); T('brass', fill(64, (210, 170, 80), 8, 65))
    T('porcelain', fill(64, (250, 250, 248), 2, 67)); T('iron', fill(64, (40, 40, 46), 4, 69)); T('gold', fill(64, (220, 180, 80), 8, 71))
    T('red', fill(64, (220, 50, 60), 4, 73)); T('blue', fill(64, (60, 110, 210), 4, 75)); T('yellow', fill(64, (250, 210, 60), 4, 77))
    T('green', fill(64, (80, 170, 90), 4, 79)); T('pink', fill(64, (250, 150, 190), 4, 81)); T('purple', fill(64, (150, 100, 200), 4, 83))
    T('orange', fill(64, (250, 140, 50), 4, 85)); T('white', fill(64, (250, 250, 250), 2, 87)); T('black', fill(64, (24, 24, 28), 2, 89))
    T('cream', fill(64, (246, 234, 210), 3, 91)); T('brown', fill(64, (120, 76, 44), 5, 93)); T('leather', fill(64, (110, 60, 36), 6, 95) + N3(64, 0.5, 96, 6))
    T('cardboard', tex_cardboard()); T('stone_m', fill(128, (170, 166, 156), 8, 97) + N3(128, 3, 98, 10))
    T('soil', fill(128, (90, 64, 44), 8, 99) + N3(128, 0.6, 100, 10)); T('grass_m', fill(64, (100, 160, 70), 8, 101))
    for i, (lt, bg, fg) in enumerate((('A', (230, 70, 80), (255, 240, 240)), ('B', (70, 130, 220), (240, 248, 255)), ('C', (250, 210, 60), (90, 60, 20)),
                                      ('D', (90, 180, 110), (250, 255, 240)), ('E', (250, 150, 60), (255, 250, 230)), ('F', (170, 110, 210), (255, 245, 255)))):
        T(f'block_{lt}', tex_letters(lt, bg, fg, seed=110 + i))
    T('spines', tex_spines()); T('spines2', tex_spines(256, 256, 113)); T('spines_old', tex_spines(256, 256, 115, [(110, 40, 40), (40, 70, 50), (80, 60, 40), (40, 40, 70), (150, 120, 60)]))
    T('stars_blue', tex_stars()); T('stars_pink', tex_stars(128, (240, 160, 190), (255, 250, 220), 117))
    for k in ('pad', 'sea', 'flowers', 'lady', 'chart'): T('paint_' + k, tex_painting(k, seed=len(k) * 7))
    T('clockface', tex_clockface()); T('globe', tex_globe()); T('braid', tex_braid()); T('tartan', tex_tartan()); T('keys', tex_keys())
    T('glow_warm', fill(32, (255, 226, 160), 2, 119)); T('glow_white', fill(32, (255, 255, 240), 2, 121)); T('glow_eye', fill(32, (220, 255, 120), 2, 123))
    T('candle', fill(32, (250, 244, 226), 2, 125)); T('glass_t', fill(64, (200, 230, 240), 3, 127)); T('water_t', fill(64, (140, 200, 230), 6, 129))
    T('label_cocoa', tex_label('COCOA', 128, 64, (180, 60, 60), (255, 240, 220))); T('label_tea', tex_label('TEA', 128, 64, (60, 120, 90), (255, 250, 230)))
    T('mailbox_sign', tex_label('PAD', 128, 64, (60, 90, 170), (255, 255, 255)))
    T('pennant', fill(64, (230, 70, 120), 3, 131))
    T('stripe_ball', np.asarray(Image.fromarray(np.concatenate([np.full((32, 256, 3), c, np.uint8) for c in
                                                                 ((240, 60, 70), (255, 255, 255), (60, 120, 230), (255, 220, 60), (255, 255, 255), (80, 190, 110), (240, 60, 70), (255, 255, 255))], 0)), np.float32))
    T('top_swirl', np.asarray(Image.fromarray(np.concatenate([np.full((16, 128, 3), c, np.uint8) for c in
                                                               ((250, 80, 120), (255, 220, 70), (90, 170, 240), (130, 220, 130)) * 2], 0)), np.float32))


# ================================================================================================= bedroom-scale pieces
SH_BOOK = dict(depth=384, back=L.SHELF_BACK, t=L.SHELF_T)


def bookshelf():
    """the big white bookcase on the west wall: origin = floor centre of its front edge... no: floor centre of the
    footprint; the back is at -x, the open front at +x. 2400 long (y), 384 deep, shelves at layout.SHELF_Z."""
    X = Model()
    W = X.mesh(S('wood_white', 'lm', shade=40)); P = X.mesh(S('wood_pink', 'lm', shade=40))
    D = 384.0; hd = D / 2
    y0, y1 = L.SHELF[1], L.SHELF[3]; ym = (y0 + y1) / 2; hl = (y1 - y0) / 2
    t = L.SHELF_T
    zt = L.SHELF_Z
    # plinth (recessed toe kick) and shelf boards
    box(W, (-hd, -hl, 0), (hd - 24, hl, zt[0]), r=3)
    for z in zt[1:]:
        box(W, (-hd + L.SHELF_BACK, -hl + 16, z - t), (hd, hl - 16, z), r=4)
    # top + crown moulding
    box(W, (-hd, -hl - 16, zt[-1] - t), (hd + 24, hl + 16, zt[-1]), r=4)
    box(W, (-hd, -hl - 24, zt[-1]), (hd + 32, hl + 24, zt[-1] + 24), r=8)
    # back panel (pink), sides, dividers
    box(P, (-hd, -hl, zt[0]), (-hd + L.SHELF_BACK, hl, zt[-1] - t), r=1, tile=256)
    for yd in L.SHELF_DIV:
        yy = yd - ym
        box(W, (-hd + L.SHELF_BACK, yy - 16, zt[0]), (hd, yy + 16, zt[-1] - t), r=3)
    # scalloped valance under the top shelf front
    for k in range(int(2 * hl / 96)):
        yy = -hl + 48 + k * 96
        ellipsoid(W, (hd - 6, yy, zt[-1] - t - 4), 6, 46, 22, nu=12, nv=6, flat_bottom=None)
    return X


def book_row(name, length=640, seed=1, tex='spines', hmin=220, hmax=360, depth=200, lean=0.0):
    """row of standing books along y (spines face +x), origin = floor centre of the row's back edge"""
    X = Model()
    r = np.random.default_rng(seed)
    Sp = X.mesh(S(tex, 'lm', shade=30)); Pg = X.mesh(S('cream', 'lm'))
    y = -length / 2
    while y < length / 2 - 20:
        bw = r.uniform(24, 56); bh = r.uniform(hmin, hmax); bd = r.uniform(depth * 0.8, depth)
        u0 = r.uniform(0, 0.8)
        m = Mesh()
        rbox(m, (0, 0, 0), (bd, bw - 2, bh), r=2, k=1, tile=256)
        # pages at the top
        Pg.add(Mesh(), t=(0, 0, 0))
        R = np.eye(3)
        if lean and r.random() < 0.15:
            R = rot_axis((1, 0, 0), -lean)
        Sp.add(m, R, (0, y, 0))
        y += bw
    return X


def bed():
    """the girl's bed: white painted frame with turned posts, a headboard with a heart cut-out (against the north
    wall at +y), mattress, floral duvet folded back, two pillows. Origin = floor centre of the footprint."""
    X = Model()
    W = X.mesh(S('wood_white', 'lm', shade=50)); Mt = X.mesh(S('linen', 'lm')); Du = X.mesh(S('floral_big', 'lm', shade=80))
    Pi = X.mesh(S('gingham', 'lm')); Pk = X.mesh(S('wood_pink', 'lm'))
    x0, y0, x1, y1 = L.BED
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    z0r, z1r = L.BED_RAIL
    leg = L.BED_LEG
    for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = sx * (hx - leg / 2), sy * (hy - leg / 2)
        h = 720 if sy > 0 else 640
        box(W, (px - leg / 2, py - leg / 2, 0), (px + leg / 2, py + leg / 2, h), r=10, tile=128)
        ellipsoid(W, (px, py, h + 30), 50, 50, 40, nu=14, nv=8)
    # side rails and end rails
    box(W, (-hx, -hy + leg, z0r), (-hx + 40, hy - leg, z1r), r=6, tile=128)
    box(W, (hx - 40, -hy + leg, z0r), (hx, hy - leg, z1r), r=6, tile=128)
    box(W, (-hx + leg, -hy, z0r), (hx - leg, -hy + 40, z1r + 120), r=6, tile=128)                  # low footboard
    # headboard with a pink heart panel
    box(W, (-hx + leg, hy - 40, z0r), (hx - leg, hy, 1080), r=8, tile=128)
    m = Mesh()
    heart = [(math.sin(t) ** 3 * 220, 760 + (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * 16) for t in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    prism(m, heart, -8, 0, tile=256)
    m.transform(RX90, (0, hy - 48, 0))
    Pk.add(m)
    # slats + mattress + duvet + pillows
    box(Mt, (-hx + 40, -hy + 40, z1r), (hx - 40, hy - 40, L.BED_TOP - 8), r=40, tile=256)
    cushion(Du, (-hx + 30, -hy + 30, L.BED_TOP - 40), (hx - 30, hy * 0.25, L.BED_TOP + 6), puff=14, r=36, tile=320)
    # folded-back turnover
    cushion(Du, (-hx + 30, hy * 0.25 - 60, L.BED_TOP - 4), (hx - 30, hy * 0.25 + 60, L.BED_TOP + 44), puff=10, r=30, tile=320)
    for sx in (-1, 1):
        cushion(Pi, (sx * 300 - 220, hy - 380, L.BED_TOP - 10), (sx * 300 + 220, hy - 80, L.BED_TOP + 110), puff=40, r=60, tile=256)
    return X


def plush_bunny():
    """floppy-eared plush bunny sitting (about 520 tall), origin floor centre, faces +x"""
    X = Model()
    F = X.mesh(S('fur_white', 'lm', shade=80)); Pk = X.mesh(S('fur_pink', 'lm', shade=80)); E = X.mesh(S('black', 'lm'))
    ellipsoid(F, (0, 0, 150), 150, 140, 150, nu=18, nv=10)
    ellipsoid(F, (20, 0, 360), 120, 115, 110, nu=18, nv=10)
    for s in (-1, 1):
        ellipsoid(F, (-10, s * 50, 520), 40, 26, 130, nu=10, nv=8, R=rot_axis((1, 0, 0), s * 0.35))
        ellipsoid(Pk, (6, s * 52, 520), 22, 14, 100, nu=10, nv=8, R=rot_axis((1, 0, 0), s * 0.35))
        ellipsoid(F, (90, s * 90, 40), 70, 50, 40, nu=12, nv=6)            # feet
        ellipsoid(F, (60, s * 130, 200), 40, 40, 80, nu=10, nv=6, R=rot_axis((0, 1, 0), 0.5))
        sphere(E, (125, s * 42, 380), 12, nu=8, nv=5)
    sphere(Pk, (138, 0, 345), 14, nu=8, nv=5)
    ellipsoid(Pk, (120, 0, 230), 30, 70, 50, nu=10, nv=6)                   # belly patch
    return X


def toy_chest():
    """painted toy chest against the south wall (back at -x), lid propped open against the wall, a broken front plank
    to crawl through. Origin = floor centre. 720 (y) x 432 (x) x 432."""
    X = Model()
    W = X.mesh(S('wood_blue', 'lm', shade=40)); St = X.mesh(S('stars_blue', 'lm', shade=40)); B = X.mesh(S('brass', 'lms')); In = X.mesh(S('wood_honey', 'lm'))
    hx = (L.CHEST[3] - L.CHEST[1]) / 2; hy = (L.CHEST[2] - L.CHEST[0]) / 2
    t = L.CHEST_T; H = L.CHEST_H
    # floor
    box(In, (-hx + t, -hy + t, 0), (hx - t, hy - t, 16), r=1)
    # back, sides
    box(W, (-hx, -hy, 0), (-hx + t, hy, H), r=3)
    for s in (-1, 1):
        box(W, (-hx, s * hy - (t if s > 0 else 0), 0), (hx, s * hy + (0 if s > 0 else t), H), r=3)
    # front with the broken plank (hole along y between CHEST_HOLE x0..x1 in world -> chest y)
    cx = (L.CHEST[0] + L.CHEST[2]) / 2
    h0, h1, hz = L.CHEST_HOLE[0] - cx, L.CHEST_HOLE[1] - cx, L.CHEST_HOLE[2]
    for (ya, yb, za, zb) in ((-hy + t, h0, 0, H), (h1, hy - t, 0, H), (h0, h1, hz, H)):
        box(W, (hx - t, ya, za), (hx, yb, zb), r=2)
        # star panel on the front face
        St.poly([(hx + 0.6, ya + 4, za + 4), (hx + 0.6, yb - 4, za + 4), (hx + 0.6, yb - 4, zb - 4), (hx + 0.6, ya + 4, zb - 4)], (1, 0, 0),
                [(ya / 200, -za / 200), (yb / 200, -za / 200), (yb / 200, -zb / 200), (ya / 200, -zb / 200)])
    # splintered edges round the hole
    r = np.random.default_rng(5)
    for k in range(6):
        yy = h0 + (h1 - h0) * (k + 0.5) / 6
        box(W, (hx - t + 2, yy - 6, hz - r.uniform(14, 34)), (hx - 2, yy + 6, hz), r=1)
    # rim band + brass corners
    box(W, (-hx - 4, -hy - 4, H - 24), (hx + 4, hy + 4, H), r=4)
    for (sx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        box(B, (sx * hx - 10, sy * hy - 10, 0), (sx * hx + 10, sy * hy + 10, 40), r=4)
        box(B, (sx * hx - 10, sy * hy - 10, H - 40), (sx * hx + 10, sy * hy + 10, H + 2), r=4)
    # the lid: hinged at the back top edge, swung open ~100 degrees so it leans on the wall behind (-x)
    lid = Mesh(); rbox(lid, (0, -hy - 8, 0), (2 * hx + 16, hy + 8, 32), r=6, k=2, tile=128)
    R = rot_axis((0, 1, 0), math.radians(-92))
    W.add(lid, R, (-hx + 50, 0, H))
    return X


def tea_table():
    """round toy tea table (pink, scalloped cloth) r 220 h 168"""
    X = Model()
    W = X.mesh(S('wood_pink', 'lm')); Cl = X.mesh(S('gingham', 'lm', two=True))
    R, H = L.TEA_R, L.TEA_H
    revolve(W, [(0, H - 12), (R, H - 12), (R + 4, H - 6), (R, H), (0, H)], n=40)
    for a in range(4):
        x, y = math.cos(a * math.pi / 2 + math.pi / 4) * R * 0.62, math.sin(a * math.pi / 2 + math.pi / 4) * R * 0.62
        turned(W, H - 12, 14, cx=x, cy=y, n=10)
    # cloth draping over the edge with a scalloped hem
    revolve(Cl, [(0, H + 1), (R + 6, H + 1), (R + 14, H - 10), (R + 18, H - 46)], n=48,
            rfun=lambda a, r, z: r + (6 * math.sin(a * 10) if z < H - 20 else 0))
    return X


def toy_chair():
    """little wooden chair facing +x, seat 96, back 220"""
    X = Model()
    W = X.mesh(S('wood_white', 'lm')); C_ = X.mesh(S('gingham', 'lm'))
    for (x, y) in ((-44, -44), (-44, 44), (44, -44), (44, 44)):
        turned(W, 90, 7, cx=x, cy=y, n=8)
    box(W, (-56, -56, 86), (56, 56, 100), r=3)
    cushion(C_, (-50, -50, 100), (50, 50, 112), puff=4, r=6)
    for y in (-48, 48):
        bar(W, (-50, y, 100), (-54, y, 230), 6)
    box(W, (-58, -54, 180), (-50, 54, 228), r=3)
    return X


def teddy(fur='fur_tan', bow='red'):
    """sitting teddy bear ~330 tall (origin floor centre, faces +x)"""
    X = Model()
    F = X.mesh(S(fur, 'lm', shade=80)); M_ = X.mesh(S('cream', 'lm', shade=80)); E = X.mesh(S('black', 'lm')); Bw = X.mesh(S(bow, 'lm'))
    ellipsoid(F, (0, 0, 110), 100, 95, 110, nu=18, nv=10)
    ellipsoid(M_, (60, 0, 110), 50, 60, 70, nu=12, nv=8)
    ellipsoid(F, (10, 0, 262), 82, 80, 76, nu=18, nv=10)
    ellipsoid(M_, (80, 0, 248), 30, 34, 26, nu=12, nv=8)
    sphere(E, (106, 0, 256), 9, nu=8, nv=5)
    for s in (-1, 1):
        sphere(F, (0, s * 60, 326), 30, nu=12, nv=8); sphere(M_, (8, s * 60, 326), 18, nu=10, nv=6)
        sphere(E, (76, s * 30, 284), 8, nu=8, nv=5)
        ellipsoid(F, (70, s * 60, 34), 70, 38, 34, nu=12, nv=8)
        ellipsoid(M_, (136, s * 60, 34), 4, 28, 26, nu=8, nv=6)
        ellipsoid(F, (30, s * 100, 150), 36, 34, 72, nu=10, nv=8, R=rot_axis((0, 1, 0), -0.5))
    # bow tie
    for s in (-1, 1):
        ellipsoid(Bw, (70, s * 24, 196), 14, 24, 16, nu=10, nv=6)
    sphere(Bw, (76, 0, 196), 10, nu=8, nv=5)
    return X


BLOCK = 144


def letter_block(letter):
    X = Model()
    B = X.mesh(S(f'block_{letter}', 'lm', shade=30))
    rbox(B, (-BLOCK / 2, -BLOCK / 2, 0), (BLOCK / 2, BLOCK / 2, BLOCK), r=8, k=2, tile=BLOCK)
    return X


def spinning_top():
    """spinning top mover model (origin at its tip on the floor)"""
    X = Model()
    Sw = X.mesh(S('top_swirl', 'dyn')); W = X.mesh(S('wood_red', 'dyn'))
    revolve(Sw, [(0, 0), (20, 10), (80, 60), (140, 110), (150, 130), (120, 160), (40, 176)], n=32, u_tiles=4, vlen=200)
    revolve(W, [(40, 176), (30, 200), (16, 210), (16, 300), (24, 310), (0, 316)], n=16)
    return X


def beach_ball(r=150):
    X = Model()
    m = Mesh(); sphere(m, (0, 0, r), r, nu=32, nv=16)
    m.ST = [(u, v) for (u, v) in m.ST]
    X.mesh(S('stripe_ball', 'lm', shade=80)).add(m)
    return X


def pram():
    """doll's pram: hooded basket on four big spoked wheels with a handle (faces +x), ~640 long, 560 tall"""
    X = Model()
    Bd = X.mesh(S('wood_pink', 'lm')); Hd = X.mesh(S('gingham', 'lm', two=True)); Ch = X.mesh(S('chrome', 'lms')); Bk = X.mesh(S('black', 'lm'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = np.array([sx * 200, sy * 150, 90])
            tube(Bk, arc_path(c, 86, 0, 360, n=29, axis='y'), 9, nseg=8, caps=(False, False))
            for a in range(0, 180, 30):
                aa = math.radians(a)
                bar(Ch, c + [86 * math.cos(aa), 0, 86 * math.sin(aa)], c - [86 * math.cos(aa), 0, 86 * math.sin(aa)], 2.5, n=5)
        bar(Ch, (sx * 200, -150, 90), (sx * 200, 150, 90), 5)
    for s in (-1, 1):
        bar(Ch, (-200, s * 110, 90), (0, s * 110, 220), 5); bar(Ch, (200, s * 110, 90), (0, s * 110, 220), 5)
    # basket body
    cushion(Bd, (-240, -130, 210), (230, 130, 400), puff=10, r=60, tile=256)
    # hood (quarter shell over the back half)
    for k in range(6):
        a0, a1 = math.radians(90 + k * 15), math.radians(90 + (k + 1) * 15)
    revolve(Hd, [(0.1, 400), (120, 410), (200, 470), (230, 560)], n=24, a0=-90, a1=90, cx=-60)
    m = Mesh()
    # handle
    bar(Ch, (230, -110, 380), (360, -110, 540), 5); bar(Ch, (230, 110, 380), (360, 110, 540), 5)
    bar(Bk, (360, -120, 540), (360, 120, 540), 10)
    return X


def rug_round():
    X = Model()
    m = Mesh()
    R = L.RUG[2]
    disc(m, R, 2, up=True, n=64, uvscale=2 * R)
    revolve(m, [(R, 2), (R + 4, 0)], n=64)
    X.mesh(S('braid', 'lm', shade=10)).add(m)
    return X


def ceiling_lamp(drop=420):
    """pendant lamp: cord from the ceiling rose (z 0 = ceiling, hangs down), pleated pink shade with a glowing inside"""
    X = Model()
    W = X.mesh(S('white', 'lm')); Sh = X.mesh(S('pink', 'lm', two=True)); G = X.mesh(S('glow_warm', 'glow'))
    revolve(W, [(0, 0), (60, 0), (50, -20), (0, -24)], n=20)
    tube(W, [(0, 0, -20), (0, 0, -drop + 120)], 4, nseg=6)
    revolve(Sh, [(80, -drop + 120), (200, -drop - 20)], n=40, rfun=lambda a, r, z: r + 6 * abs(math.sin(a * 12)))
    disc(G, 70, -drop - 10, up=False, n=24)
    sphere(G, (0, 0, -drop + 40), 40, nu=12, nv=6)
    return X


def curtain(w=300, h=1150, folds=6, col='floral'):
    """gathered curtain hanging from z 0 (rod) down h, folds along y; origin at the rod"""
    X = Model()
    C_ = X.mesh(S(col, 'lm', two=True, shade=80))
    nu, nv = folds * 6, 10
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        z = -h * i / nv
        for j in range(nu + 1):
            y = -w / 2 + w * j / nu
            x = 20 * (math.sin(j / nu * folds * 2 * math.pi) + 0.87) * (1 + 0.3 * i / nv) + 0.3
            P[i, j] = (x, y, z); UV[i, j] = (y / 256, -z / 256)
    X.mesh(S(col, 'lm', two=True, shade=80)).grid(P, grid_normals(P), UV)
    return X


def curtain_rod(L_=2800):
    X = Model()
    B = X.mesh(S('brass', 'lms'))
    tube(B, [(28, -L_ / 2, 0), (28, L_ / 2, 0)], 10, nseg=10)
    for s in (-1, 1):
        sphere(B, (28, s * (L_ / 2 + 20), 0), 22, nu=12, nv=6)
        bar(B, (0, s * (L_ / 2 - 80), 0), (28, s * (L_ / 2 - 80), 0), 8)
        box(B, (0, s * (L_ / 2 - 80) - 20, -30), (6, s * (L_ / 2 - 80) + 20, 30), r=2)
    return X


def window_frame():
    """north window: white frame, glazing bars and the sill board edge (in the wall plane y = RYN, faces -y)"""
    X = Model()
    W = X.mesh(S('wood_white', 'lm', shade=40))
    x0, x1, z0, z1 = L.WIN
    t = 40
    yy = L.RYN
    box(W, (x0 - t, yy - 24, z0 - 8), (x0, yy + 32, z1), r=4)
    box(W, (x1, yy - 24, z0 - 8), (x1 + t, yy + 32, z1), r=4)
    box(W, (x0 - t, yy - 24, z1), (x1 + t, yy + 32, z1 + t), r=4)
    # mullions + transom
    for x in np.linspace(x0, x1, 5)[1:-1]:
        box(W, (x - 10, yy + 8, z0), (x + 10, yy + 24, z1), r=2)
    box(W, (x0, yy + 8, z1 - 300), (x1, yy + 24, z1 - 280), r=2)
    # sill nose + apron
    box(W, (x0 - t - 24, yy - L.SILL_D - 12, z0 - 16), (x1 + t + 24, yy - L.SILL_D + 4, z0 + 2), r=6)
    box(W, (x0 - t, yy - L.SILL_D + 4, z0 - 120), (x1 + t, yy - L.SILL_D + 16, z0 - 16), r=3)
    return X


def plant_pot(h=200, r=90, plant='tulip'):
    """terracotta pot (origin floor centre); the plant itself is a catalog model on the soil top (h - 16)"""
    X = Model()
    T_ = X.mesh(S('orange', 'lm')); So = X.mesh(S('soil', 'lm'))
    revolve(T_, [(0, 0), (r * 0.75, 0), (r, h - 30), (r + 10, h - 28), (r + 10, h), (r - 4, h), (r - 8, h - 20)], n=24)
    disc(So, r - 8, h - 16, n=24)
    return X


# ================================================================================================= garden (on the board)
def picket_fence(length=640, h=150):
    """white picket fence section along y, origin at its floor centre"""
    X = Model()
    W = X.mesh(S('wood_white', 'lm'))
    n = int(length / 36)
    for k in range(n):
        y = -length / 2 + 18 + k * 36
        m = Mesh(); prism(m, [(-10, 0), (10, 0), (10, h - 20), (0, h), (-10, h - 20)], -4, 4, tile=64)
        m.transform(np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]]))       # polygon (y, z) extruded along x
        W.add(m, t=(0, y, 0))
    for z in (40, h - 50):
        box(W, (-10, -length / 2, z), (-4, length / 2, z + 14), r=2)
    return X


def pond_rim():
    """stone rim round the oval pond + stone steps down into it (the steps are brushes too)"""
    X = Model()
    St = X.mesh(S('stone_m', 'lm', shade=60))
    cx, cy, rx, ry = L.POND
    r = np.random.default_rng(3)
    n = 30
    for k in range(n):
        a = 2 * math.pi * k / n
        x = cx + (rx + 30) * math.cos(a); y = cy + (ry + 30) * math.sin(a)
        s = r.uniform(26, 38)
        ellipsoid(St, (x - cx, y - cy, L.BOARD_Z + 6), s * 1.3, s, 16, nu=10, nv=6, flat_bottom=-6, R=rot_z(a + math.pi / 2))
    return X


def swing():
    """garden swing frame (A-frame posts along y, crossbar along y at z 520); the seat is a separate pendulum model"""
    X = Model()
    W = X.mesh(S('wood_red', 'lm')); Y = X.mesh(S('wood_yellow', 'lm'))
    for s in (-1, 1):
        for d in (-1, 1):
            bar(W, (d * 150, s * 260, 0), (0, s * 240, 540), 14)
        bar(Y, (-80, s * 252, 260), (80, s * 252, 260), 8)
    bar(Y, (0, -270, 540), (0, 270, 540), 18)
    for s in (-1, 1):
        sphere(Y, (0, s * 276, 540), 22, nu=10, nv=6)
    return X


def swing_seat():
    """the swinging seat + ropes (origin = pivot on the crossbar)"""
    X = Model()
    R_ = X.mesh(S('cream', 'dyn')); Y = X.mesh(S('wood_yellow', 'dyn'))
    for s in (-1, 1):
        bar(R_, (s * 70, 0, 0), (s * 70, 0, -440), 3, n=6)
    box(Y, (-90, -40, -452), (90, 40, -436), r=3)
    return X


def bench():
    X = Model()
    W = X.mesh(S('wood_mint', 'lm')); I = X.mesh(S('iron', 'lm'))
    for s in (-1, 1):
        side_prism(I, [(-50, 0), (-40, 0), (-20, 80), (40, 0), (50, 0), (10, 90), (50, 90), (50, 100), (-40, 100), (-46, 220), (-56, 220)], s * 180 - 4, s * 180 + 4)
    for k in range(4):
        box(W, (-44 + k * 24, -200, 90), (-24 + k * 24, 200, 100), r=2)
    for k in range(3):
        box(W, (-52, -200, 120 + k * 32), (-42, 200, 140 + k * 32), r=2)
    return X


def mailbox():
    X = Model()
    P = X.mesh(S('wood_white', 'lm')); B = X.mesh(S('blue', 'lm')); Fl = X.mesh(S('red', 'lm')); Lb = X.mesh(S('mailbox_sign', 'lm'))
    box(P, (-8, -8, 0), (8, 8, 220), r=2)
    box(B, (-50, -24, 220), (50, 24, 260), r=4)
    m = Mesh(); prism(m, [(-24 + 48 * (0.5 - 0.5 * math.cos(a)), 260 + 22 * math.sin(a)) for a in np.linspace(0, math.pi, 12)], -50, 50, tile=64)
    m.transform(np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]]))
    B.add(m)
    box(Fl, (-8, 24, 250), (0, 28, 300), r=1)
    Lb.poly([(50.5, -18, 226), (50.5, 18, 226), (50.5, 18, 254), (50.5, -18, 254)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def gnome():
    """garden gnome ~170 tall"""
    X = Model()
    R_ = X.mesh(S('red', 'lm')); Bl = X.mesh(S('blue', 'lm')); Sk = X.mesh(S('cream', 'lm')); Wh = X.mesh(S('white', 'lm'))
    ellipsoid(Bl, (0, 0, 50), 34, 34, 50, nu=12, nv=8)
    ellipsoid(Sk, (6, 0, 104), 22, 22, 22, nu=12, nv=8)
    ellipsoid(Wh, (18, 0, 90), 16, 22, 30, nu=10, nv=6)
    revolve(R_, [(0.1, 170), (26, 116), (0, 116)], n=14)
    sphere(Sk, (28, 0, 104), 6, nu=8, nv=5)
    return X


def sailboat():
    """toy sailboat for the pond (mover; origin at the waterline centre)"""
    X = Model()
    H = X.mesh(S('wood_red', 'dyn')); Sl = X.mesh(S('white', 'dyn', two=True)); M_ = X.mesh(S('wood_honey', 'dyn'))
    ellipsoid(H, (0, 0, 0), 90, 30, 24, nu=16, nv=6, flat_bottom=None)
    bar(M_, (0, 0, 10), (0, 0, 190), 3, n=6)
    Sl.poly([(4, 0, 30), (4, 0, 185), (80, 0, 30)], (0, -1, 0), [(0, 1), (0, 0), (1, 1)])
    Sl.poly([(-4, 0, 40), (-4, 0, 170), (-60, 0, 40)], (0, -1, 0), [(0, 1), (0, 0), (1, 1)])
    return X


def stone_step(r=56):
    X = Model()
    m = Mesh(); ellipsoid(m, (0, 0, 0), r * 1.2, r, 8, nu=12, nv=4, flat_bottom=0)
    X.mesh(S('stone_m', 'lm')).add(m)
    return X


def sailboat_ring(R=170):
    """the sailboat placed on a circle round the origin, sailing clockwise (for a func_rotating with negative speed)"""
    X = sailboat()
    for M_ in X.m.values():
        M_.transform(rot_z(-math.pi / 2), (R, 0, 0))
    return X


def ring_stack():
    """baby's stacking rings: coloured rings on a cone post (r 120 base, 330 tall)"""
    X = Model()
    W = X.mesh(S('wood_white', 'lm'))
    revolve(W, [(0, 0), (124, 0), (124, 24), (0, 24)], n=32)
    tube(W, [(0, 0, 24), (0, 0, 300)], [26, 14], nseg=16)
    sphere(X.mesh(S('red', 'lm')), (0, 0, 312), 34, nu=16, nv=8)
    cols = ('purple', 'blue', 'green', 'yellow', 'orange', 'red')
    z = 24
    for k, c in enumerate(cols):
        R = 110 - k * 13; t = 22 - k * 1.2
        m = Mesh(); tube(m, arc_path((0, 0, z + t), R - t, 0, 360, n=33), t, nseg=12, caps=(False, False))
        X.mesh(S(c, 'lm', shade=80)).add(m)
        z += 2 * t
    return X


def toy_drum(r=120, h=160):
    X = Model()
    Sd = X.mesh(S('red', 'lm')); W = X.mesh(S('white', 'lm')); G = X.mesh(S('gold', 'lms')); Y = X.mesh(S('wood_yellow', 'lm'))
    revolve(Sd, [(r, 8), (r, h - 8)], n=32)
    revolve(W, [(0, h), (r - 2, h), (r + 4, h - 2)], n=32, inward=True)
    revolve(G, [(r + 4, 0), (r + 6, 4), (r + 6, 14), (r + 2, 16)], n=32)
    revolve(G, [(r + 2, h - 16), (r + 6, h - 14), (r + 6, h - 4), (r + 4, h)], n=32)
    revolve(G, [(0, 0), (r + 4, 0)], n=32, inward=True)
    for k in range(10):
        a0 = k * 2 * math.pi / 10; a1 = a0 + math.pi / 10
        bar(G, (math.cos(a0) * (r + 3), math.sin(a0) * (r + 3), 16), (math.cos(a1) * (r + 3), math.sin(a1) * (r + 3), h - 16), 2.5, n=5)
    bar(Y, (-40, -50, h + 4), (60, 30, h + 10), 6); Y.add(_ball(12), t=(60, 30, h + 12))
    return X


def beanbag():
    X = Model()
    m = Mesh()
    sphere(m, (0, 0, 0), 1, nu=24, nv=12)
    V = []
    for v in m.V:
        x, y, z = v
        r = 280 * (1 + 0.08 * math.sin(math.atan2(y, x) * 3))
        zz = (z + 1) / 2
        rr = r * (0.75 + 0.35 * math.sin(zz * math.pi * 0.85)) * math.sqrt(max(0.0, 1 - z * z)) / max(1e-6, math.sqrt(max(1e-9, 1 - z * z)))
        V.append(np.array([x * rr, y * rr, max(0.0, zz * 300 - 20 * (1 - zz) - (40 if zz > 0.85 else 0) * (zz - 0.85) / 0.15)]))
    m.V = V
    X.mesh(S('velvet_rose', 'lm', shade=90)).add(m)
    return X


def toy_truck():
    """wooden toy truck (faces +x), 440 long"""
    X = Model()
    R_ = X.mesh(S('wood_red', 'lm')); Y = X.mesh(S('wood_yellow', 'lm')); B = X.mesh(S('wood_blue', 'lm')); Bk = X.mesh(S('black', 'lm'))
    box(R_, (-220, -100, 50), (220, 100, 80), r=6)
    box(B, (90, -96, 80), (210, 96, 220), r=12)
    box(X.mesh(S('glass_t', 'lm')), (150, -98, 150), (212, 98, 200), r=4)
    box(Y, (-210, -100, 80), (80, -86, 170), r=4); box(Y, (-210, 86, 80), (80, 100, 170), r=4); box(Y, (-210, -100, 80), (-196, 100, 170), r=4)
    for (x, y) in ((-140, -104), (-140, 104), (140, -104), (140, 104)):
        m = Mesh(); tube(m, [(0, -16, 0), (0, 16, 0)], 50, nseg=20)
        Bk.add(m, t=(x, y + (8 if y > 0 else -8), 50))
        disc_axis(Y, (x, y + (25 if y > 0 else -25), 50), 22, (0, 1 if y > 0 else -1, 0), n=16)
    for k in range(3):
        box(X.mesh(S(('red', 'green', 'blue')[k], 'lm')), (-180 + k * 80, -50, 80), (-110 + k * 80, 20, 150), r=6)
    return X


def book_pile(seed=3):
    """pile of four giant picture books (origin floor centre)"""
    X = Model()
    r = np.random.default_rng(seed)
    z = 0
    cols = ('wood_red', 'wood_blue', 'wood_yellow', 'wood_mint', 'wood_pink')
    for k in range(4):
        w, d, t = r.uniform(380, 460), r.uniform(280, 330), r.uniform(48, 70)
        a = r.uniform(-0.25, 0.25)
        m = Mesh(); rbox(m, (-w / 2, -d / 2, 0), (w / 2, d / 2, t), r=6, k=2, tile=256)
        X.mesh(S(cols[(k + seed) % 5], 'lm')).add(m, rot_z(a), (r.uniform(-20, 20), r.uniform(-20, 20), z))
        pg = Mesh(); rbox(pg, (-w / 2 + 8, -d / 2 + 4, 6), (w / 2 - 2, d / 2 - 4, t - 6), r=2, k=1, tile=64)
        X.mesh(S('cream', 'lm')).add(pg, rot_z(a), (r.uniform(-2, 2), 0, z))
        z += t
    return X


# ================================================================================================= under the bed
def shoebox(lid_off=False, col='pink'):
    X = Model()
    B = X.mesh(S(col, 'lm')); Ld = X.mesh(S('white', 'lm'))
    box(B, (-180, -110, 0), (180, 110, 140), r=3)
    if not lid_off: box(Ld, (-184, -114, 120), (184, 114, 150), r=3)
    return X


def suitcase():
    X = Model()
    B = X.mesh(S('leather', 'lm')); Br = X.mesh(S('brass', 'lms'))
    box(B, (-320, -110, 0), (320, 110, 200), r=24, tile=192)
    for s in (-1, 1):
        box(Br, (s * 160 - 12, 108, 60), (s * 160 + 12, 116, 140), r=2)
    bar(Br, (-60, 112, 120), (60, 112, 120), 8)
    return X


def dust_bunny(r=60, seed=1):
    X = Model()
    m = Mesh()
    rng = np.random.default_rng(seed)
    sphere(m, (0, 0, r), r, nu=14, nv=8)
    m.V = [v * [1, 1, 0.6] + (rng.normal(0, r * 0.08, 3) if v[2] > 2 else 0) for v in m.V]
    X.mesh(S('fur_white', 'lm', shade=80)).add(m)
    return X


def monster_eyes():
    """two glowing eyes in the dark under the bed (flat on a little box so they rest on the floor)"""
    X = Model()
    G = X.mesh(S('glow_eye', 'glow')); B = X.mesh(S('black', 'lm'))
    box(B, (-12, -60, 0), (0, 60, 60), r=4)
    for s in (-1, 1):
        ellipsoid(G, (0, s * 30, 40), 2, 14, 9, nu=10, nv=5)
    return X


# ================================================================================================= dollhouse furniture (1u = 1 cm)
def table(w=140, d=80, h=75, wood='wood_honey', cloth=None):
    X = Model()
    W = X.mesh(S(wood, 'lm'))
    box(W, (-d / 2, -w / 2, h - 5), (d / 2, w / 2, h), r=1.5)
    box(W, (-d / 2 + 5, -w / 2 + 5, h - 14), (d / 2 - 5, w / 2 - 5, h - 5), r=1)
    for (x, y) in ((-d / 2 + 6, -w / 2 + 6), (-d / 2 + 6, w / 2 - 6), (d / 2 - 6, -w / 2 + 6), (d / 2 - 6, w / 2 - 6)):
        turned(W, h - 5, 3.2, cx=x, cy=y, n=8)
    if cloth:
        C_ = X.mesh(S(cloth, 'lm', two=True))
        rbox(C_, (-d / 2 - 3, -w / 2 - 3, h), (d / 2 + 3, w / 2 + 3, h + 0.8), r=0.4, k=1, tile=64)
        for s in (-1, 1):
            C_.poly([(-d / 2 - 3, s * (w / 2 + 3), h), (d / 2 + 3, s * (w / 2 + 3), h), (d / 2 + 3, s * (w / 2 + 3), h - 22), (-d / 2 - 3, s * (w / 2 + 3), h - 22)],
                    (0, s, 0), [(0, 0), (1, 0), (1, 0.3), (0, 0.3)])
    return X


def chair(wood='wood_honey', seat='gingham'):
    """dining chair facing +x, seat 45, back 95"""
    X = Model()
    W = X.mesh(S(wood, 'lm')); C_ = X.mesh(S(seat, 'lm'))
    for (x, y) in ((-17, -18), (-17, 18), (17, -18), (17, 18)):
        turned(W, 42, 1.8, cx=x, cy=y, n=6, bulbs=((0.5, 1.4),))
    box(W, (-21, -22, 41), (21, 22, 45), r=1)
    cushion(C_, (-19, -20, 45), (19, 20, 48), puff=1.2, r=1.5, k=2)
    for y in (-19, 19):
        bar(W, (-19, y, 45), (-21, y, 98), 1.8, n=6)
    box(W, (-23, -20, 78), (-19, 20, 96), r=1)
    for z in (55, 66): box(W, (-22, -19, z), (-20, 19, z + 3), r=0.5)
    return X


def range_cooker():
    """cream enamel range cooker against the wall (back at -x): ovens, hotplates with lids, a rail, a hood + chimney"""
    X = Model()
    E = X.mesh(S('cream', 'lms', v=0.12)); Ch = X.mesh(S('chrome', 'lms')); Bk = X.mesh(S('black', 'lm')); R_ = X.mesh(S('red', 'lm'))
    box(E, (-30, -50, 0), (30, 50, 88), r=3)
    box(Bk, (-30, -50, 88), (30, 50, 90), r=0.5)
    for y in (-25, 25):
        box(E, (30, y - 21, 12), (32, y + 21, 62), r=2)
        bar(Ch, (34, y - 15, 66), (34, y + 15, 66), 1.2)
        ellipsoid(Ch, (5, y, 92), 18, 18, 6, nu=14, nv=4, flat_bottom=0)
    bar(Ch, (36, -46, 80), (36, 46, 80), 1.5)
    box(E, (-30, -50, 90), (-24, 50, 130), r=2)
    # copper kettle on a hotplate
    revolve(R_, [(0, 98), (10, 98), (12, 106), (9, 116), (3, 120), (0, 121)], n=14, cx=5, cy=-25)
    bar(R_, (13, -25, 108), (22, -25, 116), 1.4)
    # hood + chimney
    box(E, (-30, -55, 150), (20, 55, 166), r=3)
    box(E, (-30, -22, 166), (-6, 22, 205), r=2)
    return X


def dresser():
    """kitchen dresser: cupboard base, shelves with plates on top (back at -x), 120 wide, 205 tall"""
    X = Model()
    W = X.mesh(S('wood_mint', 'lm')); Pl = X.mesh(S('porcelain', 'lms', v=0.15)); B = X.mesh(S('blue', 'lm')); Br = X.mesh(S('brass', 'lms'))
    box(W, (-22, -60, 0), (22, 60, 90), r=1.5)
    box(W, (-24, -62, 88), (25, 62, 92), r=1)
    for y in (-30, 30):
        box(W, (22, y - 26, 8), (24, y + 26, 80), r=1)
        Br.add(_ball(1.8), t=(25.5, y + (18 if y < 0 else -18), 50))
    box(W, (-22, -60, 92), (-18, 60, 205), r=1)
    for y in (-60, 58):
        box(W, (-20, y, 92), (-2, y + 2, 205), r=0.5)
    for z in (120, 152, 184):
        box(W, (-20, -58, z - 2), (0, 58, z), r=0.5)
        for k in range(5):
            yy = -46 + k * 23
            m = Mesh(); disc_axis(m, (0, 0, 0), 10, (1, 0, 0), n=14)
            Pl.add(m, t=(-14, yy, z + 10))
            m2 = Mesh(); disc_axis(m2, (0, 0, 0), 6, (1, 0, 0), n=14)
            B.add(m2, t=(-13.6, yy, z + 10))
    box(W, (-22, -62, 205), (2, 62, 210), r=1.5)
    return X


def sink_unit():
    X = Model()
    W = X.mesh(S('wood_white', 'lm')); P = X.mesh(S('porcelain', 'lms', v=0.15)); Ch = X.mesh(S('chrome', 'lms'))
    box(W, (-28, -50, 0), (28, 50, 82), r=1.5)
    for y in (-25, 25):
        box(W, (28, y - 22, 8), (29.5, y + 22, 74), r=1)
    box(P, (-30, -52, 82), (30, 52, 90), r=2)
    box(P, (-20, -34, 90), (20, 34, 96), r=3)
    for y in (-10, 10):
        revolve(Ch, [(0, 90), (2, 90), (1.5, 104), (0, 104)], n=8, cx=-22, cy=y)
    bar(Ch, (-22, 0, 104), (-10, 0, 112), 1.4)
    bar(Ch, (-10, 0, 112), (-6, 0, 104), 1.4)
    return X


def apple_basket():
    X = Model()
    Wk = X.mesh(S('wood_honey', 'lm')); R_ = X.mesh(S('red', 'lm')); G = X.mesh(S('green', 'lm'))
    revolve(Wk, [(0, 0), (16, 0), (20, 14), (21, 15), (19, 15), (15, 2), (0, 2)], n=16)
    r = np.random.default_rng(4)
    for k in range(6):
        a = k * math.pi / 3; rr = 9 if k else 0
        sphere(R_ if k % 3 else G, (rr * math.cos(a), rr * math.sin(a), 12 + (k == 0) * 6), 6, nu=8, nv=5)
    tube(Wk, arc_path((0, 0, 15), 18, 0, 180, n=12, axis='y'), 1.2, nseg=5)
    return X


def grandfather_clock():
    """long-case clock 210 tall (faces +x) with a brass pendulum behind glass"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.1)); B = X.mesh(S('brass', 'lms')); F = X.mesh(S('clockface', 'lm')); Gl = X.mesh(S('glass_t', 'glass'))
    box(W, (-15, -24, 0), (15, 24, 20), r=1.5)
    box(W, (-13, -18, 20), (13, 18, 150), r=1)
    box(W, (-16, -24, 150), (16, 24, 200), r=1.5)
    revolve(W, [(0, 200), (24, 200), (20, 208), (0, 214)], n=4, a0=45, a1=405)
    disc_axis(F, (16.2, 0, 175), 17, (1, 0, 0), n=24)
    disc_axis(B, (16.0, 0, 175), 19, (1, 0, 0), n=24)
    Gl.quad((13.2, -13, 40), (13.2, 13, 40), (13.2, 13, 140), (13.2, -13, 140), tile=64, n=(1, 0, 0))
    bar(B, (8, 0, 145), (8, 0, 70), 0.8, n=5)
    disc_axis(B, (8.5, 0, 65), 8, (1, 0, 0), n=14)
    for y in (-20, 0, 20):
        B.add(_ball(2.2), t=(0, y, 216 if y == 0 else 208))
    return X


def coat_stand():
    X = Model()
    W = X.mesh(S('wood_dark', 'lm')); C_ = X.mesh(S('red', 'lm')); H_ = X.mesh(S('blue', 'lm'))
    for a in range(3):
        aa = a * 2 * math.pi / 3
        bar(W, (0, 0, 20), (math.cos(aa) * 22, math.sin(aa) * 22, 0), 1.6)
    bar(W, (0, 0, 0), (0, 0, 180), 2.2)
    for a in range(4):
        aa = a * math.pi / 2 + 0.4
        bar(W, (0, 0, 170), (math.cos(aa) * 12, math.sin(aa) * 12, 178), 1.2)
    W.add(_ball(3), t=(0, 0, 182))
    cushion(C_, (4, -8, 100), (14, 8, 168), puff=3, r=3)                    # coat hanging on a hook
    revolve(H_, [(0, 176), (9, 176), (9, 178), (6, 186), (0, 188)], n=12, cx=-8, cy=8)
    return X


def console_table():
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.1)); V = X.mesh(S('porcelain', 'lms')); Fl = X.mesh(S('pink', 'lm')); G = X.mesh(S('green', 'lm'))
    box(W, (-18, -50, 76), (18, 50, 80), r=1.5)
    for (x, y) in ((-14, -44), (-14, 44), (14, -44), (14, 44)):
        turned(W, 76, 2.2, cx=x, cy=y, n=6)
    revolve(V, [(0, 80), (5, 80), (8, 88), (6, 100), (3, 108), (4, 112), (0, 112)], n=14, cx=0, cy=20)
    for k in range(5):
        a = k * 2 * math.pi / 5
        bar(G, (0, 20, 110), (math.cos(a) * 9, 20 + math.sin(a) * 9, 126), 0.6, n=4)
        sphere(Fl, (math.cos(a) * 9, 20 + math.sin(a) * 9, 127), 3.5, nu=8, nv=5)
    return X


def fireplace():
    """marble fireplace with a mantel, a brass fender, glowing coals and a gilt mirror above (back at -x)"""
    X = Model()
    M_ = X.mesh(S('porcelain', 'lms', v=0.12)); Bk = X.mesh(S('black', 'lm')); Br = X.mesh(S('brass', 'lms')); Co = X.mesh(S('glow_warm', 'glow'))
    G = X.mesh(S('gold', 'lms')); Mi = X.mesh(S('chrome', 'lms', v=0.4))
    box(M_, (-14, -65, 0), (16, -45, 110), r=1.5); box(M_, (-14, 45, 0), (16, 65, 110), r=1.5)
    box(M_, (-14, -65, 90), (16, 65, 110), r=1.5)
    box(M_, (-16, -72, 110), (22, 72, 118), r=2)
    box(Bk, (-14, -45, 0), (4, 45, 90), r=0.5)
    for k in range(6):
        sphere(Co, (-2, -30 + k * 12, 14 + (k % 2) * 3), 6, nu=8, nv=5)
    box(Br, (20, -50, 0), (24, 50, 10), r=1)
    box(M_, (-10, -75, 0), (40, 75, 3), r=1)
    box(G, (-14, -50, 126), (-8, 50, 200), r=2)
    Mi.quad((-7.6, -42, 133), (-7.6, 42, 133), (-7.6, 42, 193), (-7.6, -42, 193), tile=64, n=(1, 0, 0))
    for y in (-55, 55):
        revolve(Br, [(0, 118), (5, 118), (2, 124), (3, 140), (0, 141)], n=10, cx=5, cy=y)
        revolve(X.mesh(S('candle', 'lm')), [(1.6, 141), (1.6, 152), (0, 153)], n=8, cx=5, cy=y)
    return X


def sofa(L_=190, D=85, fab='velvet_rose'):
    X = Model()
    V = X.mesh(S(fab, 'lm', shade=70)); W = X.mesh(S('wood_dark', 'lm')); P = X.mesh(S('floral', 'lm'))
    hd, hl = D / 2, L_ / 2
    for (x, y) in ((-hd + 6, -hl + 6), (-hd + 6, hl - 6), (hd - 6, -hl + 6), (hd - 6, hl - 6)):
        turned(W, 10, 2.6, cx=x, cy=y, n=8, bulbs=((0.5, 1.3),))
    rbox(V, (-hd, -hl, 10), (hd, hl, 40), r=5, k=3, tile=96)
    rbox(V, (-hd, -hl + 14, 38), (-hd + 22, hl - 14, 88), r=9, k=3, tile=96)
    for k in range(3):
        y0 = -hl + 16 + (L_ - 32) * k / 3; y1 = -hl + 16 + (L_ - 32) * (k + 1) / 3
        cushion(V, (-hd + 20, y0 + 1, 40), (hd - 2, y1 - 1, 48), puff=2.5, r=3)
    for s in (-1, 1):
        rbox(V, (-hd, s * hl - (16 if s > 0 else 0), 38), (hd - 4, s * hl + (0 if s > 0 else 16), 62), r=6, k=3, tile=96)
        tube(V, [(-hd + 8, s * (hl - 8), 64), (hd - 2, s * (hl - 8), 64)], 9, nseg=12)
    cushion(P, (-hd + 22, -50, 48), (-hd + 34, -20, 74), puff=4, r=4)
    return X


def armchair(fab='velvet_green'):
    X = Model()
    V = X.mesh(S(fab, 'lm', shade=70)); W = X.mesh(S('wood_dark', 'lm'))
    D, Wd = 42, 42
    for (x, y) in ((-D + 6, -Wd + 6), (-D + 6, Wd - 6), (D - 6, -Wd + 6), (D - 6, Wd - 6)):
        turned(W, 10, 2.4, cx=x, cy=y, n=8, bulbs=((0.5, 1.3),))
    rbox(V, (-D, -Wd, 10), (D, Wd, 40), r=5, k=3, tile=96)
    cushion(V, (-D + 18, -Wd + 14, 40), (D - 2, Wd - 14, 48), puff=2.5, r=3)
    rbox(V, (-D, -Wd, 38), (-D + 18, Wd, 98), r=8, k=3, tile=96)
    for s in (-1, 1):
        rbox(V, (-D, s * Wd - (14 if s > 0 else 0), 38), (D - 4, s * Wd + (0 if s > 0 else 14), 64), r=6, k=3, tile=96)
    return X


def piano():
    """upright piano (back at -x) 150 wide, 130 tall, with a stool"""
    X = Model()
    Bk = X.mesh(S('black', 'lms', v=0.25)); K = X.mesh(S('keys', 'lm')); Br = X.mesh(S('brass', 'lms'))
    box(Bk, (-30, -75, 0), (0, 75, 130), r=1.5)
    box(Bk, (0, -72, 62), (26, 72, 74), r=1)
    K.poly([(0.5, -70, 74.2), (24, -70, 74.2), (24, 70, 74.2), (0.5, 70, 74.2)], (0, 0, 1), [(0, 1), (0, 0), (1, 0), (1, 1)])
    box(Bk, (-2, -72, 74), (6, 72, 86), r=1)
    for y in (-68, 68):
        box(Bk, (0, y - 4, 0), (24, y + 4, 74), r=1)
    for y in (-30, 30):
        revolve(Br, [(0, 130), (5, 130), (2, 136), (3, 150), (0, 151)], n=10, cx=-15, cy=y)
        revolve(X.mesh(S('candle', 'lm')), [(1.6, 151), (1.6, 162), (0, 163)], n=8, cx=-15, cy=y)
    # stool
    revolve(X.mesh(S('velvet_rose', 'lm')), [(0, 46), (16, 46), (17, 49), (15, 52), (0, 52)], n=16, cx=50)
    for k in range(3):
        a = k * 2 * math.pi / 3
        turned(X.mesh(S('wood_dark', 'lm')), 46, 2, cx=50 + math.cos(a) * 10, cy=math.sin(a) * 10, n=6)
    return X


def coffee_table():
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.1)); B = X.mesh(S('spines', 'lm')); T_ = X.mesh(S('porcelain', 'lms'))
    box(W, (-30, -50, 40), (30, 50, 45), r=1.5)
    for (x, y) in ((-26, -46), (-26, 46), (26, -46), (26, 46)):
        turned(W, 40, 2.4, cx=x, cy=y, n=6)
    box(B, (-14, -30, 45), (10, -6, 50), r=0.6)
    revolve(T_, [(0, 45), (6, 45), (8, 52), (6, 58), (0, 60)], n=14, cx=10, cy=20)
    bar(T_, (18, 20, 54), (24, 20, 58), 1)
    return X


def floor_lamp(h=160):
    X = Model()
    B = X.mesh(S('brass', 'lms')); Sh = X.mesh(S('pink', 'lm', two=True)); G = X.mesh(S('glow_warm', 'glow'))
    revolve(B, [(0, 0), (14, 0), (14, 2), (6, 5), (2, 8)], n=14)
    bar(B, (0, 0, 6), (0, 0, h), 1.3)
    revolve(Sh, [(22, h - 10), (12, h + 20)], n=24, rfun=lambda a, r, z: r + 0.8 * abs(math.sin(a * 10)))
    disc(G, 20, h - 9, up=False, n=16)
    return X


def wall_lamp():
    """little wall sconce (back at -x) with a glowing tulip shade"""
    X = Model()
    B = X.mesh(S('brass', 'lms')); G = X.mesh(S('glow_warm', 'glow'))
    box(B, (0, -5, -8), (2, 5, 8), r=1)
    bar(B, (2, 0, 0), (12, 0, 6), 1)
    revolve(G, [(0, 4), (6, 6), (8, 14), (0, 12)], n=12, cx=12)
    return X


def chandelier(r=34, arms=6, drop=50):
    """(placed at mul 2 in the rooms)"""
    """small brass chandelier with candle bulbs, origin at the ceiling (hangs down)"""
    X = Model()
    B = X.mesh(S('brass', 'lms')); G = X.mesh(S('glow_warm', 'glow')); Cn = X.mesh(S('candle', 'lm'))
    revolve(B, [(0, 0), (8, 0), (6, -3), (0, -4)], n=12)
    bar(B, (0, 0, -3), (0, 0, -drop + 6), 0.8, n=5)
    revolve(B, [(0, -drop + 8), (6, -drop + 4), (8, -drop - 4), (4, -drop - 10), (0, -drop - 12)], n=14)
    for k in range(arms):
        a = k * 2 * math.pi / arms
        p = np.array([math.cos(a) * r, math.sin(a) * r, -drop])
        tube(B, [(0, 0, -drop - 4), p * [0.5, 0.5, 1] + [0, 0, -6], p], 1.0, nseg=5)
        revolve(B, [(0, 0), (3, 0), (3.5, 2), (0, 2)], n=8, cx=p[0], cy=p[1]) if False else None
        revolve(Cn, [(1.2, p[2]), (1.2, p[2] + 8), (0, p[2] + 8.5)], n=6, cx=p[0], cy=p[1])
        sphere(G, p + [0, 0, 11], 2.2, nu=6, nv=4)
    return X


def picture(kind='pad', w=48, h=60, frame='gold'):
    """framed picture for a wall (back plane at x 0, faces +x)"""
    X = Model()
    F = X.mesh(S(frame, 'lms' if frame == 'gold' else 'lm')); P = X.mesh(S('paint_' + kind, 'lm'))
    b = 5
    box(F, (0, -w / 2 - b, -h / 2 - b), (3, w / 2 + b, -h / 2), r=0.8)
    box(F, (0, -w / 2 - b, h / 2), (3, w / 2 + b, h / 2 + b), r=0.8)
    box(F, (0, -w / 2 - b, -h / 2), (3, -w / 2, h / 2), r=0.8)
    box(F, (0, w / 2, -h / 2), (3, w / 2 + b, h / 2), r=0.8)
    P.poly([(1.5, -w / 2, -h / 2), (1.5, w / 2, -h / 2), (1.5, w / 2, h / 2), (1.5, -w / 2, h / 2)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def rug_rect(w=160, d=110, tex='tartan'):
    X = Model()
    m = Mesh(); rbox(m, (-d / 2, -w / 2, 0), (d / 2, w / 2, 1.2), r=0.5, k=1, tile=max(w, d))
    X.mesh(S(tex, 'lm', shade=10)).add(m)
    return X


# --------------------------------------------------------------------------------------------- bathroom
def clawfoot_tub():
    """roll-top bath 240 x 110, rim 86, inner floor 18 (origin floor centre, long axis y). The water surface is a brush."""
    X = Model()
    P = X.mesh(S('porcelain', 'lms', v=0.18)); Out = X.mesh(S('pink', 'lms', v=0.1)); G = X.mesh(S('gold', 'lms'))
    hl, hw, H = 120, 55, 86
    prof_o = [(0.0, 18), (1.0, 12), (0.97, 50), (1.0, H - 6), (1.04, H)]
    def oval(t, s):
        return [(math.cos(a) * hw * s, math.sin(a) * hl * s) for a in np.linspace(0, 2 * math.pi, 41)]
    # outer shell as stacked rings
    rings = [(0.82, 14), (0.9, 18), (0.98, 40), (1.0, 70), (1.04, H)]
    def ring_grid(rings, inward=False):
        n = 40
        Pp = np.zeros((len(rings), n + 1, 3)); UV = np.zeros((len(rings), n + 1, 2))
        for i, (s, z) in enumerate(rings):
            for j in range(n + 1):
                a = 2 * math.pi * j / n
                Pp[i, j] = (math.cos(a) * hw * s, math.sin(a) * hl * s, z); UV[i, j] = (j / n * 4, -z / 64)
        return Pp, UV
    Pp, UV = ring_grid(rings)
    Out.grid(Pp, grid_normals(Pp), UV)
    inner = [(1.0, H), (0.92, H - 4), (0.88, 50), (0.8, 24), (0.7, 18)]
    Pi, UVi = ring_grid(inner)
    P.grid(Pi, -grid_normals(Pi) if False else grid_normals(Pi, True), UVi)
    disc_pts = [(math.cos(a) * hw * 0.7, math.sin(a) * hl * 0.7, 18) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    P.poly(disc_pts, (0, 0, 1), [(p[0] / 64, p[1] / 64) for p in disc_pts])
    tube(P, [(math.cos(a) * hw * 1.02, math.sin(a) * hl * 1.02, H) for a in np.linspace(0, 2 * math.pi, 41)], 3.2, nseg=8, caps=(False, False))
    # claw feet
    for (sx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        c = (sx * hw * 0.62, sy * hl * 0.72)
        revolve(G, [(0, 0), (8, 0), (9, 4), (5, 10), (6, 16), (0, 18)], n=10, cx=c[0], cy=c[1])
    # taps at the north end
    for x in (-10, 10):
        revolve(G, [(0, H), (2.5, H), (2, H + 16), (0, H + 16)], n=8, cx=x, cy=hl * 0.95)
        bar(G, (x, hl * 0.95, H + 16), (x, hl * 0.85, H + 12), 1.4)
    return X


def toilet():
    """old high-cistern toilet (back at -x), bowl seat 45"""
    X = Model()
    P = X.mesh(S('porcelain', 'lms', v=0.18)); W = X.mesh(S('wood_honey', 'lm')); Ch = X.mesh(S('chrome', 'lms'))
    revolve(P, [(0, 0), (12, 0), (10, 10), (14, 30), (20, 40), (0, 40)], n=20)
    m = Mesh(); revolve(m, [(0, 0), (20, 40)], n=4)
    ellipsoid(W, (6, 0, 42), 24, 19, 3, nu=16, nv=4)
    box(W, (-20, -12, 42), (-14, 12, 80), r=2)
    box(P, (-24, -24, 150), (-10, 24, 175), r=2)
    bar(Ch, (-17, 0, 150), (-17, 0, 42), 1.5)
    bar(Ch, (-12, 18, 162), (-6, 22, 120), 0.6, n=4)
    Ch.add(_ball(2.5), t=(-6, 22, 118))
    return X


def basin():
    """pedestal washbasin with a mirror above (back at -x)"""
    X = Model()
    P = X.mesh(S('porcelain', 'lms', v=0.18)); Ch = X.mesh(S('chrome', 'lms')); G = X.mesh(S('gold', 'lms')); Mi = X.mesh(S('chrome', 'lms', v=0.45))
    revolve(P, [(0, 0), (14, 0), (10, 6), (7, 50), (9, 70), (0, 70)], n=16)
    ellipsoid(P, (4, 0, 78), 24, 30, 10, nu=18, nv=6)
    for y in (-8, 8):
        revolve(Ch, [(0, 84), (1.6, 84), (1.4, 92), (0, 92)], n=8, cx=-14, cy=y)
    ellipsoid(G, (0, 0, 140), 2, 26, 34, nu=16, nv=6)
    m = Mesh(); disc_axis(m, (2.2, 0, 140), 1, (1, 0, 0), n=3)
    Mi.add(Mesh())
    pts = [(2.3, math.cos(a) * 22, 140 + math.sin(a) * 30) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    Mi.poly(pts, (1, 0, 0), [(0.5 + p[1] / 50, 0.5 - (p[2] - 140) / 70) for p in pts])
    return X


def towel_rail():
    X = Model()
    Ch = X.mesh(S('chrome', 'lms')); T_ = X.mesh(S('pink', 'lm'))
    for y in (-30, 30):
        bar(Ch, (8, y, 0), (8, y, 100), 1.4)
        revolve(Ch, [(0, 0), (5, 0), (2, 3), (0, 3)], n=8, cx=8, cy=y)
    for z in (60, 95): bar(Ch, (8, -30, z), (8, 30, z), 1.2)
    box(T_, (5, -24, 40), (11, 24, 96), r=2)
    return X


# --------------------------------------------------------------------------------------------- bedroom (doll)
def four_poster():
    """four-poster bed 200 x 150 (long axis x, head at -x), mattress top 55, canopy at 210 (posts only, open top)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.08)); Ln = X.mesh(S('linen', 'lm')); Q = X.mesh(S('floral', 'lm', shade=80)); C_ = X.mesh(S('velvet_rose', 'lm', two=True))
    hl, hw = 100, 75
    for (sx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        turned(W, 210, 3.2, cx=sx * (hl - 4), cy=sy * (hw - 4), n=8, bulbs=((0.2, 1.6), (0.6, 1.2)))
    for s in (-1, 1):
        box(W, (-hl, s * (hw - 4) - 2.5, 205), (hl, s * (hw - 4) + 2.5, 212), r=1)
        box(W, (s * (hl - 4) - 2.5, -hw, 205), (s * (hl - 4) + 2.5, hw, 212), r=1)
    box(W, (-hl, -hw, 18), (hl, hw, 32), r=2)
    box(W, (-hl, -hw + 6, 32), (-hl + 6, hw - 6, 120), r=2)
    rbox(Ln, (-hl + 4, -hw + 4, 32), (hl - 4, hw - 4, 50), r=5, k=3, tile=96)
    cushion(Q, (-hl + 40, -hw + 2, 46), (hl - 2, hw - 2, 56), puff=3, r=4, tile=128)
    for y in (-35, 35):
        cushion(Ln, (-hl + 8, y - 28, 48), (-hl + 40, y + 28, 64), puff=5, r=6)
    # tied-back curtains at the foot posts
    for s in (-1, 1):
        revolve(C_, [(9, 205), (5, 140), (8, 70), (12, 60)], n=10, cx=hl - 4, cy=s * (hw - 4))
    return X


def chest_of_drawers(w=100, d=50, h=100, wood='wood_white'):
    X = Model()
    W = X.mesh(S(wood, 'lm')); Br = X.mesh(S('brass', 'lms'))
    box(W, (-d / 2, -w / 2, 6), (d / 2, w / 2, h), r=1.5)
    box(W, (-d / 2 - 1, -w / 2 - 1, h - 3), (d / 2 + 2, w / 2 + 1, h + 1), r=1.5)
    for (x, y) in ((-d / 2 + 4, -w / 2 + 4), (-d / 2 + 4, w / 2 - 4), (d / 2 - 4, -w / 2 + 4), (d / 2 - 4, w / 2 - 4)):
        revolve(W, [(0, 0), (4, 0), (3, 6), (0, 6)], n=8, cx=x, cy=y)
    n = 4
    for k in range(n):
        z0 = 10 + (h - 16) * k / n; z1 = 10 + (h - 16) * (k + 1) / n - 2
        box(W, (d / 2, -w / 2 + 4, z0), (d / 2 + 1.5, w / 2 - 4, z1), r=0.6)
        for y in (-w / 4, w / 4):
            Br.add(_ball(1.6), t=(d / 2 + 2.6, y, (z0 + z1) / 2))
    return X


def dressing_table():
    X = Model()
    W = X.mesh(S('wood_white', 'lm')); Mi = X.mesh(S('chrome', 'lms', v=0.45)); G = X.mesh(S('gold', 'lms')); P = X.mesh(S('pink', 'lm'))
    box(W, (-22, -55, 70), (22, 55, 75), r=1.5)
    for (x, y) in ((-18, -50), (-18, 50), (18, -50), (18, 50)):
        turned(W, 70, 2.2, cx=x, cy=y, n=6)
    box(W, (-22, -12, 75), (-16, 12, 85), r=1)
    pts = [(-18.5, math.cos(a) * 26, 125 + math.sin(a) * 36) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    Mi.poly(pts, (1, 0, 0), [(0.5 + p[1] / 60, 0.5 - (p[2] - 125) / 80) for p in pts])
    tube(G, [(-19, math.cos(a) * 27.5, 125 + math.sin(a) * 37.5) for a in np.linspace(0, 2 * math.pi, 29)], 1.6, nseg=6, caps=(False, False))
    bar(W, (-20, 0, 85), (-20, 0, 89), 2)
    for k, c in enumerate(('pink', 'purple', 'gold')):
        revolve(X.mesh(S(c, 'lms')), [(0, 75), (2.6, 75), (2.6, 82), (1.4, 84), (1.4, 87), (0, 87)], n=10, cx=6, cy=-30 + k * 9)
    # stool
    revolve(P, [(0, 42), (14, 42), (15, 45), (13, 48), (0, 48)], n=16, cx=46)
    for k in range(3):
        a = k * 2 * math.pi / 3
        turned(W, 42, 1.8, cx=46 + math.cos(a) * 9, cy=math.sin(a) * 9, n=6)
    return X


# --------------------------------------------------------------------------------------------- nursery
def crib():
    X = Model()
    W = X.mesh(S('wood_white', 'lm')); Ln = X.mesh(S('gingham_blue', 'lm')); T_ = X.mesh(S('fur_tan', 'lm'))
    hl, hw, H = 60, 34, 100
    for (sx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        box(W, (sx * hl - 3, sy * hw - 3, 0), (sx * hl + 3, sy * hw + 3, H + 6), r=1)
        W.add(_ball(3.5), t=(sx * hl, sy * hw, H + 9))
    for s in (-1, 1):
        for z in (30, H):
            box(W, (-hl, s * hw - 2, z - 3), (hl, s * hw + 2, z), r=0.8)
            box(W, (s * hl - 2, -hw, z - 3), (s * hl + 2, hw, z), r=0.8)
        for k in range(1, 12):
            x = -hl + 2 * hl * k / 12
            bar(W, (x, s * hw, 30), (x, s * hw, H - 3), 1.0, n=5)
        for k in range(1, 6):
            y = -hw + 2 * hw * k / 6
            bar(W, (s * hl, y, 30), (s * hl, y, H - 3), 1.0, n=5)
    rbox(Ln, (-hl + 2, -hw + 2, 30), (hl - 2, hw - 2, 40), r=3, k=2, tile=64)
    ellipsoid(T_, (20, 0, 50), 9, 8, 10, nu=10, nv=6); sphere(T_, (20, 0, 64), 7, nu=10, nv=6)
    return X


def rocking_horse():
    """dappled rocking horse on curved rockers, 110 long, ~90 tall (faces +x)"""
    X = Model()
    Wh = X.mesh(S('white', 'lm', shade=70)); R_ = X.mesh(S('wood_red', 'lm')); Bk = X.mesh(S('black', 'lm')); Sd = X.mesh(S('red', 'lm')); G = X.mesh(S('gold', 'lms'))
    for s in (-1, 1):
        tube(R_, arc_path((0, s * 16, 160), 160, 243, 297, n=16, axis='y'), 3, nseg=8)
    for s in (-1, 1):
        for d in (-1, 1):
            bar(Wh, (d * 26, s * 8, 46), (d * 36, s * 16, 6), 3.4)
    ellipsoid(Wh, (0, 0, 52), 34, 13, 15, nu=16, nv=8)
    tube(Wh, [(26, 0, 58), (36, 0, 74), (40, 0, 86)], [9, 8, 7], nseg=10)
    ellipsoid(Wh, (48, 0, 86), 13, 7, 8, nu=12, nv=6, R=rot_axis((0, 1, 0), 0.5))
    for s in (-1, 1):
        sphere(Bk, (50, s * 6, 92), 1.6, nu=6, nv=4)
        ellipsoid(Wh, (38, s * 4, 98), 2, 2, 5, nu=6, nv=4)
    for k in range(7):
        sphere(Bk, (36 - k * 3, 0, 96 - k * 4), 4, nu=6, nv=4)
    tube(Bk, [(-34, 0, 56), (-44, 0, 48), (-48, 0, 30)], [3, 4, 2], nseg=6)
    box(Sd, (-12, -14, 64), (12, 14, 68), r=2)
    for s in (-1, 1): G.add(_ball(1.5), t=(0, s * 14, 56))
    return X


def mini_dollhouse():
    """the tiny dollhouse on the nursery floor (faces +x): 220 wide (y) x 120 deep x 260 tall, with an open door
    (64 x 96) that leads... somewhere. The inside is dark."""
    X = Model()
    Sd = X.mesh(S('wood_yellow', 'lm')); Rf = X.mesh(S('wood_blue', 'lm')); Tr = X.mesh(S('wood_white', 'lm')); D = X.mesh(S('black', 'lm'))
    Gw = X.mesh(S('glow_warm', 'glow')); Dr = X.mesh(S('wood_red', 'lm'))
    hw, hd, H = 110, 60, 180
    dw, dh = 32, 96
    # walls (front with door hole)
    box(Sd, (-hd, -hw, 0), (-hd + 6, hw, H), r=1)
    for s in (-1, 1): box(Sd, (-hd, s * hw - (6 if s > 0 else 0), 0), (hd, s * hw + (0 if s > 0 else 6), H), r=1)
    box(Sd, (hd - 6, -hw, 0), (hd, -dw, H), r=1); box(Sd, (hd - 6, dw, 0), (hd, hw, H), r=1); box(Sd, (hd - 6, -dw, dh), (hd, dw, H), r=1)
    # dark inside (floor + ceiling)
    box(D, (-hd + 6, -hw + 6, 0), (hd - 6, hw - 6, 2), r=0.5)
    box(D, (-hd + 6, -hw + 6, H - 8), (hd - 6, hw - 6, H - 4), r=0.5)
    # roof: two slopes + gable triangles
    for s in (-1, 1):
        q = [(-hd - 8, s * (hw + 10), H - 6), (hd + 8, s * (hw + 10), H - 6), (hd + 8, 0, H + 80), (-hd - 8, 0, H + 80)]
        Rf.poly(q, (0, s * 0.8, 0.6), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for xx in (-hd, hd):
        Sd.poly([(xx, -hw, H), (xx, hw, H), (xx, 0, H + 74)], (1 if xx > 0 else -1, 0, 0), [(0, 0), (1, 0), (0.5, 1)])
    # windows glowing, trims, a door leaf swung open
    for y in (-70, 70):
        for z in (40, 120):
            Gw.quad((hd + 0.5, y - 14, z), (hd + 0.5, y + 14, z), (hd + 0.5, y + 14, z + 30), (hd + 0.5, y - 14, z + 30), tile=32, n=(1, 0, 0))
            box(Tr, (hd, y - 17, z - 4), (hd + 2, y + 17, z), r=0.5)
    box(Tr, (hd, -dw - 4, 0), (hd + 2, -dw, dh), r=0.5); box(Tr, (hd, dw, 0), (hd + 2, dw + 4, dh), r=0.5); box(Tr, (hd, -dw - 4, dh), (hd + 2, dw + 4, dh + 4), r=0.5)
    box(Dr, (hd, dw + 4, 0), (hd + 60, dw + 8, dh - 2), r=1)
    Gw.add(_ball(3), t=(hd + 3, 0, dh + 14))
    return X


def toy_shelf():
    """low nursery toy shelf (back at -x) with a few little toys"""
    X = Model()
    W = X.mesh(S('wood_mint', 'lm'))
    box(W, (-18, -60, 0), (18, 60, 4), r=1); box(W, (-18, -60, 44), (18, 60, 48), r=1); box(W, (-18, -60, 86), (18, 60, 90), r=1)
    for y in (-60, 56): box(W, (-18, y, 0), (18, y + 4, 90), r=1)
    box(W, (-18, -60, 0), (-15, 60, 90), r=0.5)
    for k, c in enumerate(('red', 'blue', 'yellow', 'green')):
        box(X.mesh(S(c, 'lm')), (-6, -50 + k * 18, 48), (8, -36 + k * 18, 62), r=1.5)
    sphere(X.mesh(S('stripe_ball', 'lm')), (0, 30, 56), 8, nu=12, nv=6)
    ellipsoid(X.mesh(S('fur_tan', 'lm')), (0, -30, 12), 9, 8, 9, nu=10, nv=6); sphere(X.mesh(S('fur_tan', 'lm')), (0, -30, 26), 7, nu=10, nv=6)
    return X


def mobile():
    """nursery mobile (mover, origin at the ceiling hook): stars and a moon on a cross"""
    X = Model()
    W = X.mesh(S('wood_white', 'dyn')); Y = X.mesh(S('yellow', 'dyn')); P = X.mesh(S('pink', 'dyn')); B = X.mesh(S('blue', 'dyn'))
    bar(W, (0, 0, 0), (0, 0, -40), 0.4, n=4)
    bar(W, (-30, 0, -40), (30, 0, -40), 0.8, n=5); bar(W, (0, -30, -40), (0, 30, -40), 0.8, n=5)
    for k, (x, y) in enumerate(((-30, 0), (30, 0), (0, -30), (0, 30))):
        bar(W, (x, y, -40), (x, y, -60 - (k % 2) * 10), 0.3, n=3)
        m = Mesh()
        p = [(0, 0, 0)]
        pts = []
        for j in range(10):
            rr = 8 if j % 2 == 0 else 3.6
            a = j * math.pi / 5
            pts.append((0, rr * math.sin(a), rr * math.cos(a)))
        m.poly(pts, (1, 0, 0), [(0.5, 0.5)] * 10)
        m.poly(pts[::-1], (-1, 0, 0), [(0.5, 0.5)] * 10)
        (Y, P, B, Y)[k].add(m, t=(x, y, -68 - (k % 2) * 10))
    return X


def wardrobe(w=120, d=60, h=200):
    """wardrobe with its doors standing open (back at -x): dresses on a rail inside"""
    X = Model()
    W = X.mesh(S('wood_white', 'lm')); Br = X.mesh(S('brass', 'lms')); In = X.mesh(S('wood_pink', 'lm'))
    hd, hw = d / 2, w / 2
    box(W, (-hd, -hw, 0), (hd, -hw + 3, h), r=1); box(W, (-hd, hw - 3, 0), (hd, hw, h), r=1)
    box(W, (-hd, -hw, 0), (hd, hw, 8), r=1); box(W, (-hd, -hw, h - 6), (hd + 3, hw, h + 4), r=1.5)
    box(In, (-hd, -hw + 3, 8), (-hd + 2, hw - 3, h - 6), r=0.5)
    bar(Br, (0, -hw + 3, h - 30), (0, hw - 3, h - 30), 1)
    cols = ('pink', 'blue', 'yellow', 'purple', 'green')
    for k in range(5):
        y = -hw + 14 + k * (w - 28) / 4
        revolve(X.mesh(S(cols[k], 'lm', two=True)), [(1, h - 34), (6, h - 50), (14, h - 120), (18, h - 130)], n=10, cx=0, cy=y)
    for (y, sg) in ((-hw, -1), (hw, 1)):
        box(W, (hd, y + sg * 2 - (0 if sg > 0 else 2), 4), (hd + w / 2 - 4, y + sg * 4 + (0 if sg > 0 else -0), h - 8), r=1) if False else None
        a = np.array([hd, y, 4.0]); b = np.array([hd + w / 2 - 4, y + sg * 3, h - 8])
        box(W, np.minimum(a, b), np.maximum(a, b), r=1)
        Br.add(_ball(2), t=(hd + w / 2 - 10, y + sg * 5, h / 2))
    return X


def bedside(col='wood_white'):
    X = Model()
    W = X.mesh(S(col, 'lm')); Br = X.mesh(S('brass', 'lms')); Sh = X.mesh(S('pink', 'lm', two=True)); G = X.mesh(S('glow_warm', 'glow'))
    box(W, (-20, -22, 4), (20, 22, 55), r=1.5)
    for (x, y) in ((-17, -19), (-17, 19), (17, -19), (17, 19)):
        revolve(W, [(0, 0), (3, 0), (2.4, 4), (0, 4)], n=6, cx=x, cy=y)
    box(W, (20, -18, 30), (21.5, 18, 50), r=0.5); Br.add(_ball(1.5), t=(22.5, 0, 40))
    revolve(Br, [(0, 55), (6, 55), (2, 58), (1.5, 76), (0, 76)], n=10)
    revolve(Sh, [(12, 72), (7, 90)], n=16)
    disc(G, 10, 73, up=False, n=12)
    return X


def side_table():
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.08)); V = X.mesh(S('porcelain', 'lms')); Fl = X.mesh(S('red', 'lm')); G = X.mesh(S('green', 'lm'))
    revolve(W, [(0, 0), (16, 0), (16, 2), (6, 5), (3, 10), (4, 40), (2.5, 52), (0, 52)], n=16)
    revolve(W, [(0, 52), (20, 52), (21, 55), (20, 57), (0, 57)], n=24)
    revolve(V, [(0, 57), (4, 57), (6, 64), (4, 72), (2.5, 78), (3.5, 82), (0, 82)], n=12)
    for k in range(5):
        a = k * 2 * math.pi / 5
        bar(G, (0, 0, 80), (math.cos(a) * 7, math.sin(a) * 7, 94), 0.5, n=4)
        sphere(Fl, (math.cos(a) * 7, math.sin(a) * 7, 95), 3, nu=8, nv=5)
    return X


def laundry_basket():
    X = Model()
    Wk = X.mesh(S('wood_honey', 'lm')); C_ = X.mesh(S('pink', 'lm')); B = X.mesh(S('blue', 'lm'))
    revolve(Wk, [(0, 0), (18, 0), (22, 40), (23, 42), (21, 42), (17, 2), (0, 2)], n=18)
    ellipsoid(C_, (0, 0, 40), 18, 16, 8, nu=12, nv=6)
    ellipsoid(B, (8, 6, 44), 10, 8, 5, nu=10, nv=5)
    return X


def wall_clock():
    """round wall clock (back plane at x 0, faces +x)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lm')); F = X.mesh(S('clockface', 'lm'))
    m = Mesh(); revolve(m, [(0, 0), (16, 0), (16, 3), (14, 4), (0, 4)], n=24)
    W.add(m, rot_axis((0, 1, 0), math.pi / 2))
    disc_axis(F, (4.2, 0, 0), 13.5, (1, 0, 0), n=24)
    return X


def wall_shelf(w=80, col='wood_white', what='plates'):
    """little wall shelf with brackets (back at x 0, faces +x), plates or jars on it"""
    X = Model()
    W = X.mesh(S(col, 'lm')); P = X.mesh(S('porcelain', 'lms', v=0.15)); B = X.mesh(S('blue', 'lm'))
    box(W, (0, -w / 2, 0), (16, w / 2, 3), r=0.8)
    for y in (-w / 2 + 8, w / 2 - 8):
        side_prism(W, [(0, 0), (12, 0), (0, -14)], y - 1.5, y + 1.5)
    for k in range(int(w / 20)):
        y = -w / 2 + 10 + k * 20
        if what == 'plates':
            m = Mesh(); disc_axis(m, (0, 0, 0), 8, (1, 0, 0), n=14); P.add(m, t=(4, y, 11))
            m2 = Mesh(); disc_axis(m2, (0, 0, 0), 5, (1, 0, 0), n=14); B.add(m2, t=(4.4, y, 11))
        else:
            revolve(X.mesh(S(('red', 'yellow', 'green', 'purple')[k % 4], 'lms')), [(0, 3), (4, 3), (4, 12), (2, 14), (0, 14)], n=10, cx=8, cy=y)
    return X


def pot_plant(h=60, r=20):
    """doll-size flower pot with a little leafy plant (vertex lit leaves)"""
    X = Model()
    T_ = X.mesh(S('orange', 'lm')); So = X.mesh(S('soil', 'lm')); G = X.mesh(S('green', 'lm', shade=80)); Fl = X.mesh(S('pink', 'lm'))
    revolve(T_, [(0, 0), (r * 0.7, 0), (r, h * 0.5), (r + 3, h * 0.52), (r + 3, h * 0.6), (r - 2, h * 0.6)], n=16)
    disc(So, r - 2, h * 0.56, n=16)
    rng = np.random.default_rng(int(h))
    for k in range(9):
        a = k * 2 * math.pi / 9 + rng.uniform(-0.2, 0.2)
        L_ = rng.uniform(h * 0.5, h * 0.9)
        tip = (math.cos(a) * L_ * 0.5, math.sin(a) * L_ * 0.5, h * 0.56 + L_)
        ellipsoid(G, ((tip[0]) / 2, (tip[1]) / 2, h * 0.56 + L_ * 0.55), 5, 3, L_ * 0.45, nu=8, nv=5, R=rot_axis((-math.sin(a), math.cos(a), 0), 0.45))
        if k % 3 == 0: sphere(Fl, tip, 4.5, nu=8, nv=5)
    return X


def rag_doll():
    """little rag doll sitting (origin floor centre, faces +x), ~70 tall"""
    X = Model()
    Sk = X.mesh(S('cream', 'lm')); D_ = X.mesh(S('gingham_blue', 'lm')); H_ = X.mesh(S('orange', 'lm')); E = X.mesh(S('black', 'lm'))
    ellipsoid(D_, (0, 0, 16), 16, 14, 16, nu=12, nv=8)
    sphere(Sk, (2, 0, 44), 12, nu=12, nv=8)
    for s in (-1, 1):
        sphere(E, (13, s * 4, 46), 1.5, nu=6, nv=4)
        tube(H_, [(-6, s * 10, 54), (-8, s * 14, 40), (-4, s * 15, 28)], 3, nseg=6)
        tube(Sk, [(4, s * 6, 4), (24, s * 7, 3)], 3.5, nseg=6)
        tube(D_, [(0, s * 13, 26), (10, s * 18, 14)], 3, nseg=6)
    ellipsoid(H_, (-2, 0, 52), 12, 12, 6, nu=12, nv=6)
    return X


# --------------------------------------------------------------------------------------------- library / study
def bookcase(w=100, d=34, h=208):
    X = Model()
    W = X.mesh(S('wood_dark', 'lm'));
    box(W, (-d / 2, -w / 2, 0), (d / 2, w / 2, 8), r=1)
    box(W, (-d / 2, -w / 2, h - 8), (d / 2 + 3, w / 2 + 3, h), r=1.5)
    for y in (-w / 2, w / 2 - 3): box(W, (-d / 2, y, 0), (d / 2, y + 3, h), r=0.6)
    box(W, (-d / 2, -w / 2, 0), (-d / 2 + 2, w / 2, h), r=0.4)
    nsh = 5
    for k in range(nsh):
        z = 8 + (h - 16) * k / nsh
        if k: box(W, (-d / 2, -w / 2, z - 2), (d / 2, w / 2, z), r=0.4)
        sp = X.mesh(S(('spines_old', 'spines2', 'spines')[k % 3], 'lm'))
        hb = (h - 16) / nsh - 8
        sp.poly([(d / 2 - 8, -w / 2 + 4, z + 0.2), (d / 2 - 8, w / 2 - 4, z + 0.2), (d / 2 - 8, w / 2 - 4, z + hb), (d / 2 - 8, -w / 2 + 4, z + hb)], (1, 0, 0),
                [(0, 1), (1, 1), (1, 0.15), (0, 0.15)])
        box(X.mesh(S('cream', 'lm')), (-d / 2 + 2, -w / 2 + 4, z), (d / 2 - 8.2, w / 2 - 4, z + hb), r=0.5, faces='t')
    return X


def desk():
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.08)); Lt = X.mesh(S('leather', 'lm')); Br = X.mesh(S('brass', 'lms'))
    box(W, (-30, -60, 72), (30, 60, 77), r=1.5)
    Lt.poly([(-24, -50, 77.2), (24, -50, 77.2), (24, 50, 77.2), (-24, 50, 77.2)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for s in (-1, 1):
        box(W, (-28, s * 60 - (30 if s > 0 else 0), 0), (28, s * 60 + (0 if s > 0 else 30), 72), r=1)
        for k in range(3):
            z0 = 6 + k * 22
            box(W, (28, s * 45 - 13, z0), (29.5, s * 45 + 13, z0 + 18), r=0.5)
            Br.add(_ball(1.4), t=(30.5, s * 45, z0 + 9))
    # green banker's lamp
    revolve(Br, [(0, 77), (6, 77), (6, 79), (1.2, 80)], n=10, cx=-12, cy=-30)
    bar(Br, (-12, -30, 80), (-12, -30, 104), 0.9, n=5)
    m = Mesh(); tube(m, [(-12, -42, 104), (-12, -18, 104)], 6, nseg=12)
    X.mesh(S('green', 'lms')).add(m)
    disc(X.mesh(S('glow_warm', 'glow')), 4, 99, up=False, n=10, cx=-12, cy=-30)
    # open book + ink pot
    box(X.mesh(S('cream', 'lm')), (-4, 4, 77), (12, 30, 78.5), r=0.4)
    revolve(X.mesh(S('black', 'lms')), [(0, 77), (3, 77), (3, 82), (1, 83), (0, 83)], n=8, cx=10, cy=40)
    return X


def globe():
    X = Model()
    W = X.mesh(S('wood_dark', 'lm')); G = X.mesh(S('globe', 'lm')); Br = X.mesh(S('brass', 'lms'))
    for k in range(3):
        a = k * 2 * math.pi / 3
        bar(W, (math.cos(a) * 18, math.sin(a) * 18, 0), (math.cos(a) * 8, math.sin(a) * 8, 50), 1.8)
    revolve(W, [(0, 48), (14, 48), (14, 52), (0, 52)], n=16)
    sphere(G, (0, 0, 76), 20, nu=20, nv=12)
    tube(Br, arc_path((0, 0, 76), 22, -110, 110, n=16, axis='y'), 1, nseg=5, caps=(False, False))
    return X


# --------------------------------------------------------------------------------------------- attic
def trunk(w=90, d=50, h=55, col='wood_red'):
    X = Model()
    W = X.mesh(S(col, 'lm')); Br = X.mesh(S('brass', 'lms')); Lt = X.mesh(S('leather', 'lm'))
    box(W, (-d / 2, -w / 2, 0), (d / 2, w / 2, h * 0.75), r=2)
    m = Mesh(); prism(m, [(-d / 2 + d * (0.5 - 0.5 * math.cos(a)), h * 0.75 + h * 0.25 * math.sin(a)) for a in np.linspace(0, math.pi, 10)], -w / 2, w / 2, tile=64)
    m.transform(RX90)
    W.add(m, t=(0, 0, 0))
    for y in (-w / 2 + 12, w / 2 - 12):
        box(Lt, (-d / 2 - 1, y - 3, 0), (d / 2 + 1, y + 3, h * 0.75 + 1), r=0.6)
    box(Br, (d / 2, -6, h * 0.6), (d / 2 + 1.5, 6, h * 0.75), r=0.5)
    return X


def cardboard_box(w=70, d=60, h=50, open_=False):
    X = Model()
    B = X.mesh(S('cardboard', 'lm'))
    box(B, (-d / 2, -w / 2, 0), (d / 2, w / 2, h), r=0.8)
    if open_:
        for s in (-1, 1):
            q = [(-d / 2, s * w / 2, h), (d / 2, s * w / 2, h), (d / 2, s * (w / 2 + 22), h + 18), (-d / 2, s * (w / 2 + 22), h + 18)]
            B.poly(q, (0, s * 0.6, 0.8), [(0, 0), (1, 0), (1, 0.4), (0, 0.4)])
    return X


def dress_form():
    X = Model()
    W = X.mesh(S('wood_dark', 'lm')); Fb = X.mesh(S('floral', 'lm')); Rb = X.mesh(S('pink', 'lm'))
    for k in range(3):
        a = k * 2 * math.pi / 3
        bar(W, (0, 0, 20), (math.cos(a) * 26, math.sin(a) * 26, 0), 1.6)
    bar(W, (0, 0, 0), (0, 0, 100), 1.8)
    revolve(Fb, [(0.1, 96), (16, 100), (14, 116), (18, 136), (14, 150), (5, 156), (0, 158)], n=18,
            rfun=lambda a, r, z: r * (1 - 0.25 * abs(math.sin(a))))
    revolve(Rb, [(17, 112), (26, 98), (28, 80)], n=20)
    W.add(_ball(3), t=(0, 0, 161))
    return X


def rocking_chair():
    X = Model()
    W = X.mesh(S('wood_honey', 'lm')); C_ = X.mesh(S('tartan', 'lm'))
    for s in (-1, 1):
        tube(W, arc_path((0, s * 20, 120), 120, 248, 292, n=14, axis='y'), 1.8, nseg=6)
        for d in (-1, 1):
            bar(W, (d * 16, s * 20, 6), (d * 16, s * 20, 44), 1.6)
        bar(W, (-20, s * 20, 44), (-28, s * 20, 110), 1.6)
    box(W, (-20, -22, 42), (20, 22, 46), r=1)
    cushion(C_, (-18, -20, 46), (18, 20, 50), puff=1.5, r=2)
    for k in range(5):
        y = -16 + k * 8
        bar(W, (-22, y, 46), (-28, y, 106), 0.9, n=5)
    box(W, (-30, -22, 104), (-26, 22, 112), r=1)
    return X


def birdcage():
    X = Model()
    G = X.mesh(S('gold', 'lms')); Y = X.mesh(S('yellow', 'lm'))
    revolve(G, [(0, 0), (20, 0), (20, 4), (0, 4)], n=20)
    for k in range(16):
        a = k * 2 * math.pi / 16
        tube(G, [(math.cos(a) * 19, math.sin(a) * 19, 4), (math.cos(a) * 19, math.sin(a) * 19, 50), (math.cos(a) * 8, math.sin(a) * 8, 66), (0, 0, 70)], 0.5, nseg=4)
    tube(G, arc_path((0, 0, 78), 7, 0, 360, n=13, axis='y'), 0.7, nseg=4, caps=(False, False))
    bar(G, (-17, 0, 26), (17, 0, 26), 0.6, n=4)
    ellipsoid(Y, (0, 0, 32), 5, 4, 5, nu=10, nv=6); sphere(Y, (3, 0, 39), 3.2, nu=8, nv=5)
    return X


def lamp_old():
    """dusty standard lamp with a fringed shade (attic)"""
    X = Model()
    B = X.mesh(S('brass', 'lms')); Sh = X.mesh(S('cream', 'lm', two=True))
    revolve(B, [(0, 0), (16, 0), (8, 6), (2, 10)], n=14)
    bar(B, (0, 0, 8), (0, 0, 150), 1.4)
    revolve(Sh, [(26, 140), (14, 172)], n=24)
    for k in range(48):
        a = k * 2 * math.pi / 48
        bar(Sh, (math.cos(a) * 26, math.sin(a) * 26, 140), (math.cos(a) * 26.5, math.sin(a) * 26.5, 132), 0.4, n=3)
    return X


def telescope_stand():
    X = Model()
    Br = X.mesh(S('brass', 'lms')); W = X.mesh(S('wood_dark', 'lm'))
    for k in range(3):
        a = k * 2 * math.pi / 3
        bar(W, (math.cos(a) * 30, math.sin(a) * 30, 0), (0, 0, 110), 2)
    tube(Br, [(-40, 0, 104), (60, 0, 140)], [4, 7], nseg=14)
    tube(X.mesh(S('black', 'lm')), [(56, 0, 138.5), (62, 0, 141)], 7.5, nseg=14)
    return X


# --------------------------------------------------------------------------------------------- ballroom (secret)
def music_box_base():
    """giant music box: lacquered pink box with gold trim, the stage disc on top (the ballerina spins separately)"""
    X = Model()
    P = X.mesh(S('pink', 'lms', v=0.18)); G = X.mesh(S('gold', 'lms')); Mi = X.mesh(S('chrome', 'lms', v=0.45))
    box(P, (-160, -160, 0), (160, 160, 120), r=10, tile=128)
    box(G, (-166, -166, 112), (166, 166, 128), r=6)
    box(G, (-166, -166, 0), (166, 166, 12), r=6)
    for (sx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        G.add(_ball(14), t=(sx * 150, sy * 150, 140))
    # key on the side
    bar(G, (160, 0, 60), (200, 0, 60), 6)
    tube(G, arc_path((216, 0, 60), 18, 0, 360, n=17, axis='x'), 5, nseg=6, caps=(False, False))
    return X


def ballerina():
    """ballerina figurine (mover, origin at the centre of the stage disc)"""
    X = Model()
    Sk = X.mesh(S('cream', 'dynenv')); Tu = X.mesh(S('pink', 'dynenv')); G = X.mesh(S('gold', 'dynenv')); H_ = X.mesh(S('brown', 'dyn'))
    revolve(G, [(0, 0), (100, 0), (100, 8), (0, 8)], n=32)
    bar(Sk, (0, 0, 8), (0, 0, 120), 5, n=8)                                   # standing leg on pointe
    tube(Sk, [(0, 0, 110), (40, 0, 150), (80, 0, 150)], 5, nseg=8)            # arabesque leg
    revolve(Tu, [(0.1, 150), (70, 150), (90, 140), (60, 160), (20, 170)], n=32, rfun=lambda a, r, z: r * (1 + 0.08 * math.sin(a * 9)))
    ellipsoid(Tu, (0, 0, 196), 20, 16, 34, nu=14, nv=8)
    sphere(Sk, (0, 0, 246), 18, nu=14, nv=8)
    sphere(H_, (-4, 0, 262), 10, nu=10, nv=6)
    tube(Sk, [(0, -16, 214), (-10, -40, 250), (0, -30, 290)], 3.5, nseg=6)
    tube(Sk, [(0, 16, 214), (-10, 40, 250), (0, 30, 290)], 3.5, nseg=6)
    return X


def chandelier_big():
    X = chandelier(r=150, arms=10, drop=200)
    return X


# ================================================================================================= make
PLACE_INFO = {}


def put(name, X):
    p = save(name, X)
    return p


def make():
    os.makedirs(out(MD), exist_ok=True)
    make_textures()
    import dh_house
    dh_house.make_textures()
    # bedroom scale
    put('bookshelf', bookshelf())
    for i, (ln, sd, tx) in enumerate(((680, 1, 'spines'), (520, 2, 'spines2'), (720, 3, 'spines'), (460, 4, 'spines_old'), (600, 5, 'spines2'))):
        put(f'books_{i}', book_row(f'books_{i}', ln, sd, tx))
    put('bed', bed()); put('bunny', plush_bunny()); put('toy_chest', toy_chest()); put('tea_table', tea_table()); put('toy_chair', toy_chair())
    put('teddy', teddy()); put('teddy_pink', teddy('fur_pink', 'blue'))
    for lt in 'ABCDEF': put(f'block_{lt}', letter_block(lt))
    save_iqm('top', spinning_top()); put('ball', beach_ball()); put('pram', pram()); put('rug', rug_round())
    put('ceiling_lamp', ceiling_lamp()); put('curtain', curtain()); put('curtain_rod', curtain_rod())
    X = window_frame(); X.shift((0, L.RYN, L.WIN[2])); put('window', X)
    put('pot', plant_pot()); put('pot_small', plant_pot(130, 60))
    # garden
    put('fence', picket_fence()); put('fence_s', picket_fence(320)); put('pond_rim', pond_rim()); put('swing', swing()); save_iqm('swing_seat', swing_seat())
    put('bench', bench()); put('mailbox', mailbox()); put('gnome', gnome()); save_iqm('sailboat_ring', sailboat_ring()); put('stone_step', stone_step())
    # under the bed
    put('shoebox', shoebox()); put('shoebox_b', shoebox(True, 'blue')); put('suitcase', suitcase()); put('dust_a', dust_bunny(60, 1)); put('dust_b', dust_bunny(90, 2))
    put('eyes', monster_eyes())
    # dollhouse furniture
    put('k_table', table(140, 80, 75, 'wood_honey', 'gingham')); put('k_chair', chair()); put('range', range_cooker()); put('dresser', dresser())
    put('sink', sink_unit()); put('apples', apple_basket())
    put('gclock', grandfather_clock()); put('coat_stand', coat_stand()); put('console', console_table()); put('runner', rug_rect(400, 70, 'velvet_rose'))
    put('fireplace', fireplace()); put('sofa', sofa()); put('armchair', armchair()); put('armchair_r', armchair('velvet_rose')); put('piano', piano())
    put('coffee_table', coffee_table()); put('floor_lamp', floor_lamp()); put('wall_lamp', wall_lamp()); put('chandelier', chandelier())
    put('rug_parlour', rug_rect(260, 200, 'tartan')); put('rug_bed', rug_rect(220, 160, 'floral')); put('rug_nursery', rug_rect(200, 200, 'stars_blue'))
    for k in ('pad', 'sea', 'flowers', 'lady', 'chart'): put(f'pic_{k}', picture(k))
    put('pic_big', picture('pad', 90, 110))
    put('tub', clawfoot_tub()); put('toilet', toilet()); put('basin', basin()); put('towel_rail', towel_rail()); put('bathmat', rug_rect(80, 50, 'pink'))
    put('fourposter', four_poster()); put('drawers', chest_of_drawers()); put('dressing', dressing_table())
    put('crib', crib()); put('rhorse', rocking_horse()); put('mini_house', mini_dollhouse()); put('toyshelf', toy_shelf()); save_iqm('mobile', mobile())
    put('bookcase', bookcase()); put('desk', desk()); put('globe', globe()); put('d_chair', chair('wood_dark', 'velvet_green'))
    put('trunk', trunk()); put('trunk_b', trunk(110, 55, 60, 'wood_blue')); put('cbox', cardboard_box()); put('cbox_o', cardboard_box(80, 60, 44, True))
    put('dress_form', dress_form()); put('rchair', rocking_chair()); put('birdcage', birdcage()); put('lamp_old', lamp_old()); put('telescope', telescope_stand())
    put('drawers_b', chest_of_drawers(80, 40, 70, 'wood_mint'))
    put('book_pile', book_pile()); put('book_pile_b', book_pile(7)); put('rings', ring_stack()); put('drum', toy_drum()); put('beanbag', beanbag()); put('truck', toy_truck())
    put('wardrobe', wardrobe()); put('bedside', bedside()); put('side_table', side_table()); put('laundry', laundry_basket())
    put('wall_clock', wall_clock()); put('wall_shelf', wall_shelf()); put('wall_jars', wall_shelf(64, 'wood_mint', 'jars')); put('pot_plant', pot_plant())
    put('pot_plant_b', pot_plant(80, 26)); put('rag_doll', rag_doll()); put('larder', chest_of_drawers(90, 50, 200, 'wood_mint'))
    put('rug_kitchen', rug_rect(180, 140, 'gingham')); put('runner_long', rug_rect(560, 110, 'velvet_rose'))
    put('musicbox', music_box_base()); save_iqm('ballerina', ballerina()); put('chandelier_big', chandelier_big())
    put('kchair_tea', toy_chair())
    import dh_house as DH
    return DH.make_models()
