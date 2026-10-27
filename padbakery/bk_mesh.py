"""Mesh helpers and model textures shared by bk_models.py (architecture) and bk_props.py (props, movers).
All art is original and generated here."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube as _tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame
from bklib import *
import bklib

TXD = 'textures/padbakery/'


def BT(name): return TXD + name


# ================================================================================================= mesh helpers
def tube(M, path, radii, **kw):
    path = np.asarray(path, float)
    r = np.atleast_1d(np.asarray(radii, float))
    if len(r) == 1: r = np.full(len(path), float(r[0]))
    elif len(r) != len(path):
        r = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(r)), r)
    _tube(M, path, r, **kw)


def cylm(M, c, r, h, n=16, caps=True, tile=128.0, top=True):
    c = np.asarray(c, float)
    if caps:
        prof = [(0, c[2]), (r, c[2]), (r, c[2] + h)] + ([(0, c[2] + h)] if top else [])
    else:
        prof = [(r, c[2]), (r, c[2] + h)]
    revolve(M, prof, n=n, cx=c[0], cy=c[1], vlen=tile, u_tiles=max(1, round(2 * math.pi * r / tile)))


def boxm(M, mn, mx, r=1.0, tile=64.0, k=1, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def torus(M, c, R, r, axis=(0, 0, 1), n=32, m=10, utile=4.0, a0=0.0, a1=2 * math.pi):
    c = np.asarray(c, float); ax = np.asarray(axis, float); ax /= np.linalg.norm(ax)
    b1, b2 = frame(ax)
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    path = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * R for t in np.linspace(a0, a1, n + 1)]
    _tube(M, np.array(path), np.full(n + 1, r), nseg=m, caps=(not full, not full), utiles=1, vlen=max(1.0, (a1 - a0) * R / utile))


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture(M, c, w, h, nrm, up=(0, 0, 1), two=False):
    """textured quad centred at c facing nrm, u left->right as seen from the front (text reads correctly)"""
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm); up = np.asarray(up, float)
    right = np.cross(up, nrm); right /= np.linalg.norm(right)
    upv = np.cross(nrm, right)
    p = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2, c - right * w / 2 + upv * h / 2]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])
    if two: M.poly(p[::-1], -nrm, [(0, 0), (1, 0), (1, 1), (0, 1)][::-1])


def annulus(M, cx, cy, r0, r1, z, a0=0.0, a1=360.0, n=48, up=True, tile=256.0):
    """flat ring (or pie when r0 = 0) between angles a0..a1, planar UVs"""
    angs = np.radians(np.linspace(a0, a1, n + 1))
    nn = (0, 0, 1 if up else -1)
    for k in range(n):
        ta, tb = angs[k], angs[k + 1]
        pts = [(cx + r1 * math.cos(ta), cy + r1 * math.sin(ta), z), (cx + r1 * math.cos(tb), cy + r1 * math.sin(tb), z)]
        if r0 > 0.5: pts += [(cx + r0 * math.cos(tb), cy + r0 * math.sin(tb), z), (cx + r0 * math.cos(ta), cy + r0 * math.sin(ta), z)]
        else: pts += [(cx, cy, z)]
        M.poly(pts, nn, [(p[0] / tile, -p[1] / tile) for p in pts])


def frustum_m(M, c, r0, r1, h, n=24, tile=128.0, top=True, bottom=False):
    c = np.asarray(c, float)
    prof = ([(0, c[2])] if bottom else []) + [(r0, c[2]), (r1, c[2] + h)] + ([(0, c[2] + h)] if top else [])
    revolve(M, prof, n=n, cx=c[0], cy=c[1], vlen=tile, u_tiles=max(1, round(2 * math.pi * max(r0, r1) / tile)))


def solids_parts(X, brushes, fn, hidden=None):
    """visible faces of convex brushes -> Model X; fn(part, centre, normal, poly) -> (shader, uvfn) or None.
    A face is skipped when points just outside it lie inside any brush of `hidden` (default: the same set)."""
    idx = solid_index(hidden if hidden is not None else brushes)
    for b in brushes:
        for (n, poly) in face_polys(b):
            c = poly.mean(0)
            smp = [c] + [c + (p - c) * 0.7 for p in poly]
            if all(bklib._inside_any(p + n * 1.0, idx) for p in smp): continue
            r = fn(getattr(b, 'part', ''), c, n, poly)
            if r is None: continue
            sh, uvf = r
            X.mesh(sh).poly([p for p in poly], n, [uvf(p) for p in poly])
    return X


def uvz(n, tile=256.0, u_off=0.0):
    """planar UVs where v runs down the height (for vertical faces whose texture has an up direction)"""
    nn = np.asarray(n, float)
    if abs(nn[2]) > 0.7: return planar_uv(nn, tile)
    h = np.array([-nn[1], nn[0], 0.0]); h /= max(1e-9, np.linalg.norm(h))
    return lambda p: (float(p @ h) / tile + u_off, -float(p[2]) / tile)


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


# ================================================================================================= model textures
def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((90, 80, 70)), C((250, 246, 240)), np.clip(1 - y * 1.3, 0, 1)[..., None])
    return c + N3(n, 8, seed, 14)


def tex_steel(n=256, seed=1, base=(196, 198, 204)):
    """brushed stainless: fine horizontal streaks"""
    x, y = xy(n)
    st = noise(n, 0.5, seed) * 0.2 + np.repeat(noise(n, 3, seed + 1)[:, :1], n, 1) * 0.8
    return np.zeros((n, n, 3), np.float32) + C(base) + st[..., None] * 10 + N3(n, 30, seed + 2, 6)


def tex_brick(n=256, seed=3):
    """firebrick oven lining, soot toward the top"""
    x, y = xy(n)
    u = x * 4 + (np.floor(y * 8) % 2) * 0.5; v = y * 8
    g = (np.minimum(u % 1, 1 - u % 1) < 0.03) | (np.minimum(v % 1, 1 - v % 1) < 0.05)
    rng = np.random.default_rng(seed)
    tone = rng.uniform(-20, 20, (16, 16))[np.floor(u).astype(int) % 16, np.floor(v).astype(int) % 16]
    c = np.zeros((n, n, 3), np.float32) + C((176, 96, 60)) + tone[..., None] * C((1, 0.6, 0.4)) + N3(n, 1, seed, 8)
    c = np.where(g[..., None], C((120, 110, 100)), c)
    return c * (0.7 + 0.3 * y)[..., None]


def tex_hearth(n=256, seed=5):
    """oven deck stone, floured"""
    c = fill(n, (190, 170, 140), 4, seed) + N3(n, 0.7, seed, 8)
    fl = np.clip(noise(n, 6, seed + 1) - 0.4, 0, 2)[..., None] * 40
    x, y = xy(n)
    g = (np.minimum(x * 2 % 1, 1 - x * 2 % 1) < 0.008) | (np.minimum(y * 2 % 1, 1 - y * 2 % 1) < 0.008)
    return np.where(g[..., None], C((110, 96, 80)), c + fl)


def tex_glow(n=64, col=(255, 140, 50)):
    x, y = xy(n)
    v = np.exp(-((y - 0.5) / 0.25) ** 2)
    return np.zeros((n, n, 3), np.float32) + C(col) * (0.55 + 0.45 * v)[..., None]


def tex_butcher(n=256, seed=7):
    """butcher-block worktop: strips of maple/walnut"""
    x, y = xy(n)
    k = np.floor(x * 12).astype(int)
    rng = np.random.default_rng(seed)
    tone = rng.uniform(-18, 18, 12)[k % 12]
    c = np.zeros((n, n, 3), np.float32) + C((214, 170, 116)) + tone[..., None] + N3(n, 1, seed, 5)
    c = c + (np.sin(y * 80 + noise(n, 4, seed + 1) * 3) * 6)[..., None]
    sm = np.minimum((x * 12) % 1, 1 - (x * 12) % 1) < 0.03
    return np.where(sm[..., None], c * 0.78, c)


def tex_cabinet(n=256, seed=9, base=(244, 236, 220)):
    """cream painted cabinet panel with a raised frame"""
    x, y = xy(n)
    e = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    sh = np.where(e < 0.05, 8, np.where(e < 0.08, -16, 0))
    return np.zeros((n, n, 3), np.float32) + C(base) + sh[..., None] + N3(n, 1, seed, 3)


def tex_wood(n=256, seed=11, base=(196, 146, 96)):
    x, y = xy(n)
    return np.zeros((n, n, 3), np.float32) + C(base) + (np.sin(y * 50 + noise(n, 6, seed) * 2.5) * 10)[..., None] + N3(n, 1, seed + 1, 5)


def buttercream(n=256, seed=13, col=(252, 248, 240), swirl=10):
    """buttercream: soft palette-knife swirls"""
    c = np.zeros((n, n, 3), np.float32) + C(col)
    s = noise(n, 10, seed) * 0.6 + noise(n, 3, seed + 1) * 0.4
    return c + (s * swirl)[..., None] + N3(n, 0.6, seed + 2, 2)


def tex_sponge(n=256, seed=15, col=(242, 206, 140)):
    """cake crumb: little air holes"""
    c = fill(n, col, 3, seed)
    h = np.clip(noise(n, 1.2, seed + 1) - 1.1, 0, 2)
    return c - h[..., None] * 60 + N3(n, 0.5, seed + 2, 6)


def tex_layers(w=256, h=256, seed=17):
    """the cut face of the show cake: sponge / buttercream / jam layers (v runs down from the top)"""
    c = np.zeros((h, w, 3), np.float32)
    sp = tex_sponge(w, seed)
    bands = [(0.0, 0.06, 'cream'), (0.06, 0.3, 'sponge'), (0.3, 0.36, 'jam'), (0.36, 0.42, 'cream'), (0.42, 0.66, 'sponge_c'),
             (0.66, 0.72, 'cream'), (0.72, 0.96, 'sponge'), (0.96, 1.0, 'cream')]
    _, y = xy(w, h)
    for (a, b, k) in bands:
        m = (y >= a) & (y < b)
        if k == 'cream': col = C((252, 246, 236)) + N3(w, 2, seed + 3, 4, h)
        elif k == 'jam': col = C((196, 30, 60)) + N3(w, 2, seed + 4, 12, h)
        elif k == 'sponge_c': col = tex_sponge(w, seed + 5, (120, 72, 44))
        else: col = sp
        c = np.where(m[..., None], col, c)
    return c


def tex_sprinkles(n=256, seed=19, base=(252, 248, 244)):
    im = img(buttercream(n, seed, base)).convert('RGB'); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    cols = [(240, 60, 90), (60, 170, 240), (250, 210, 50), (90, 200, 90), (170, 80, 220), (255, 140, 40)]
    for k in range(260):
        x, y = rng.uniform(0, n), rng.uniform(0, n); a = rng.uniform(0, math.pi); L_ = rng.uniform(3, 6)
        d.line([(x - L_ * math.cos(a), y - L_ * math.sin(a)), (x + L_ * math.cos(a), y + L_ * math.sin(a))], fill=cols[k % 6], width=3)
    return np.asarray(im, np.float32)


def tex_dots(n=128, base=(250, 180, 204), dot=(255, 255, 255), k=4):
    x, y = xy(n)
    c = buttercream(n, 21, base, 6)
    d = np.hypot(((x * k) % 1) - 0.5, ((y * k) % 1) - 0.5)
    return np.where((d < 0.16)[..., None], C(dot), c)


def tex_strawberry(n=128, seed=23):
    c = fill(n, (214, 30, 50), 6, seed)
    x, y = xy(n)
    s = (np.hypot((x * 8 + (np.floor(y * 8) % 2) * 0.5) % 1 - 0.5, (y * 8) % 1 - 0.5) < 0.09)
    return np.where(s[..., None], C((250, 220, 120)), c + (np.clip(1 - y * 3, 0, 1) * 30)[..., None])


def tex_choc(n=128, seed=27, col=(92, 52, 32)):
    return fill(n, col, 6, seed) + N3(n, 0.6, seed + 1, 3)


def tex_plaque(w=512, h=256):
    a = tex_choc(w, 29)
    a = np.asarray(img(a).resize((w, h)), np.float32)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, w - 10, h - 10), 30, outline=(250, 236, 210), width=8)
    f = font(70, True)
    d.text((w / 2, h * 0.36), 'HAPPY', font=f, fill=(252, 240, 224), anchor='mm')
    d.text((w / 2, h * 0.68), 'FRAG DAY', font=f, fill=(255, 190, 210), anchor='mm')
    return np.asarray(im, np.float32)


def tex_liner(w=256, h=128, col=(250, 200, 220)):
    """pleated cupcake liner (u round the case)"""
    x, y = xy(w, h)
    pl = np.sin(x * math.pi * 2 * 16)
    c = np.zeros((h, w, 3), np.float32) + C(col) + pl[..., None] * 18
    return np.where((((x * 32) % 1) < 0.08)[..., None], c * 0.85, c)


def tex_crust(n=256, seed=31, col=(200, 128, 56)):
    """bread crust, golden with flour dusting"""
    c = fill(n, col, 6, seed) + N3(n, 0.8, seed + 1, 10)
    fl = np.clip(noise(n, 4, seed + 2) - 0.8, 0, 2)[..., None] * 60
    return c + fl


def tex_burlap(w=256, h=256, seed=33, text='FLOUR', sub='TYPE 550 - 25 KG', ink=(40, 90, 170)):
    x, y = xy(w, h)
    weave = (np.sin(x * w * 0.9) * np.sin(y * h * 0.9)) * 10
    c = np.zeros((h, w, 3), np.float32) + C((222, 206, 170)) + weave[..., None] + N3(w, 1, seed, 8, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    f1 = font(int(h * 0.2), True); f2 = font(int(h * 0.07), False)
    d.text((w / 2, h * 0.42), text, font=f1, fill=ink, anchor='mm')
    d.text((w / 2, h * 0.62), sub, font=f2, fill=ink, anchor='mm')
    d.ellipse((w / 2 - 22, h * 0.14, w / 2 + 22, h * 0.14 + 44), outline=ink, width=4)
    return np.asarray(im, np.float32)


def tex_box(w=256, h=256, seed=35):
    """pink cake box with white stripes and the bakery roundel"""
    x, y = xy(w, h)
    st = ((x * 10) % 1) < 0.5
    c = np.where(st[..., None], C((246, 170, 200)), C((252, 226, 236))) + N3(w, 1, seed, 3, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    d.ellipse((w * 0.25, h * 0.25, w * 0.75, h * 0.75), fill=(250, 244, 230), outline=(196, 40, 90), width=6)
    f = font(int(h * 0.12), True)
    d.text((w / 2, h * 0.46), 'SWEET', font=f, fill=(196, 40, 90), anchor='mm')
    d.text((w / 2, h * 0.58), 'PADMAN', font=f, fill=(196, 40, 90), anchor='mm')
    return np.asarray(im, np.float32)


def tex_label(w=256, h=128, text='BUTTER', bg=(250, 232, 150), fg=(30, 80, 40), sub=None):
    a = text_img(text, w, h if not sub else int(h * 0.65), bg, fg, True)
    if sub: a = np.concatenate([a, text_img(sub, w, h - a.shape[0], bg, fg, False)], 0)
    return a


def tex_clock(n=256):
    im = Image.new('RGB', (n, n), (250, 246, 236)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), outline=(60, 40, 30), width=10)
    f = font(26, True)
    for h_ in range(1, 13):
        a = math.radians(90 - h_ * 30)
        d.text((n / 2 + 0.36 * n * math.cos(a), n / 2 - 0.36 * n * math.sin(a)), str(h_), font=f, fill=(40, 30, 30), anchor='mm')
    d.line([(n / 2, n / 2), (n / 2 + 0.2 * n * math.cos(math.radians(30)), n / 2 - 0.2 * n * math.sin(math.radians(30)))], fill=(30, 20, 20), width=8)
    d.line([(n / 2, n / 2), (n / 2, n / 2 - 0.32 * n)], fill=(30, 20, 20), width=5)
    return np.asarray(im, np.float32)


def tex_curtain(w=64, h=256):
    """clear plastic strip curtain (alpha)"""
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C((210, 230, 240))
    a = np.where(np.minimum(x, 1 - x) < 0.08, 220, 150) * np.ones_like(y)
    return c, a


def tex_wire(n=64):
    """chrome wire grid (alpha cut-out)"""
    x, y = xy(n)
    m = (np.minimum((x * 8) % 1, 1 - (x * 8) % 1) < 0.12) | (np.minimum((y * 2) % 1, 1 - (y * 2) % 1) < 0.06)
    return np.zeros((n, n, 3), np.float32) + C((220, 224, 232)), np.where(m, 255, 0)


def tex_flour(n=256, seed=37):
    return fill(n, (250, 248, 242), 3, seed) + N3(n, 6, seed + 1, 5)


def tex_shell(n=128, seed=39, col=(236, 206, 170)):
    return fill(n, col, 4, seed) + N3(n, 0.5, seed + 1, 4)


def tex_coolpanel(n=256, seed=49):
    """cool-room insulated panels: white steel, vertical seams, a blue kick band"""
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((232, 236, 240)) + N3(n, 1, seed, 3) + np.repeat(noise(n, 3, seed + 1)[:1], n, 0)[..., None] * 3
    sm = np.minimum((x * 2) % 1, 1 - (x * 2) % 1) < 0.012
    c = np.where(sm[..., None], C((150, 156, 166)), c)
    rv = (np.abs(((x * 2) % 1) - 0.05) < 0.006) & ((y * 12) % 1 < 0.25)
    return np.where(rv[..., None], c * 0.8, c)


def tex_poster(w=256, h=320, title='CUPCAKES', col=(250, 182, 204), seed=51):
    """framed retro bakery poster: a big cupcake / cake drawing and a title"""
    im = Image.new('RGB', (w, h), (250, 244, 230)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(90, 56, 36), width=14)
    d.rectangle((20, 20, w - 21, h - 80), fill=col)
    cx, cy = w / 2, h * 0.42
    d.polygon([(cx - 60, cy + 10), (cx + 60, cy + 10), (cx + 44, cy + 80), (cx - 44, cy + 80)], fill=(250, 220, 120))
    for j in range(-3, 4): d.line([(cx + j * 16, cy + 12), (cx + j * 12, cy + 78)], fill=(220, 180, 80), width=3)
    d.ellipse((cx - 70, cy - 40, cx + 70, cy + 24), fill=(255, 250, 252)); d.ellipse((cx - 44, cy - 84, cx + 44, cy - 14), fill=(255, 250, 252))
    d.ellipse((cx - 14, cy - 110, cx + 14, cy - 80), fill=(214, 40, 70))
    f = font(int(h * 0.1), True)
    d.text((w / 2, h - 46), title, font=f, fill=(150, 40, 80), anchor='mm')
    return np.asarray(im, np.float32)


def tex_screen(w=256, h=128):
    im = Image.new('RGB', (w, h), (20, 40, 30)); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), '12.50', font=font(64, False), fill=(120, 255, 150), anchor='mm')
    return np.asarray(im, np.float32)


def tex_dial(n=128):
    im = Image.new('RGB', (n, n), (30, 30, 34)); d = ImageDraw.Draw(im)
    d.ellipse((6, 6, n - 6, n - 6), fill=(236, 236, 232), outline=(60, 60, 64), width=6)
    for k in range(9):
        a = math.radians(225 - k * 33.75)
        d.line([(n / 2 + 0.3 * n * math.cos(a), n / 2 - 0.3 * n * math.sin(a)), (n / 2 + 0.4 * n * math.cos(a), n / 2 - 0.4 * n * math.sin(a))], fill=(30, 30, 30), width=3)
    d.line([(n / 2, n / 2), (n / 2 + 0.34 * n * math.cos(math.radians(60)), n / 2 - 0.34 * n * math.sin(math.radians(60)))], fill=(220, 40, 30), width=4)
    return np.asarray(im, np.float32)


def tex_fountain(w=64, h=256, seed=41):
    """chocolate flow streaks (alpha)"""
    x, y = xy(w, h)
    s = np.clip(np.sin(x * 40 + noise(w, 3, seed, h) * 2) * 0.5 + 0.6, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((110, 60, 34)) + (s * 40)[..., None]
    return c, np.clip(140 + s * 115, 0, 255)


def make_textures():
    T('env', tex_env())
    T('steel', tex_steel()); T('steel_d', tex_steel(256, 3, (110, 112, 118))); T('enamel', tex_steel(256, 5, (150, 170, 160)))
    T('brick', tex_brick()); T('hearth', tex_hearth()); T('glow_o', tex_glow()); T('glow_w', tex_glow(64, (255, 236, 200)))
    T('glow_p', tex_glow(64, (255, 120, 190))); T('glow_y', tex_glow(64, (255, 210, 110)))
    T('black', fill(64, (24, 24, 26), 2, 1)); T('white', fill(64, (246, 246, 244), 2, 2)); T('red', fill(64, (210, 40, 50), 2, 3))
    T('butcher', tex_butcher()); T('cabinet', tex_cabinet()); T('cab_pink', tex_cabinet(256, 10, (246, 196, 212))); T('wood', tex_wood())
    T('wood_d', tex_wood(256, 12, (120, 76, 46)))
    for nm, col in (('bc_white', (252, 248, 240)), ('bc_pink', (250, 182, 204)), ('bc_choc', (112, 66, 40)), ('bc_mint', (186, 236, 210)),
                    ('bc_lemon', (252, 236, 150)), ('bc_lilac', (210, 180, 236)), ('bc_blue', (170, 214, 246)), ('bc_caramel', (214, 150, 80))):
        T(nm, buttercream(256, sum(map(ord, nm)) % 97, col))
    T('sponge', tex_sponge()); T('sponge_c', tex_sponge(256, 16, (120, 72, 44))); T('layers', tex_layers())
    T('sprinkles', tex_sprinkles()); T('sprinkles_c', tex_sprinkles(256, 20, (112, 66, 40))); T('dots', tex_dots())
    T('strawberry', tex_strawberry()); T('leaf', fill(64, (70, 150, 60), 3, 4)); T('choc', tex_choc()); T('choc_d', tex_choc(128, 28, (60, 32, 20)))
    T('plaque', tex_plaque()); T('pearl', fill(64, (250, 246, 236), 2, 5)); T('sugar', fill(128, (252, 252, 250), 2, 6) + N3(128, 0.5, 7, 8))
    T('liner_p', tex_liner()); T('liner_b', tex_liner(256, 128, (150, 200, 240))); T('liner_g', tex_liner(256, 128, (236, 200, 90)))
    T('crust', tex_crust()); T('crust_d', tex_crust(256, 32, (150, 84, 38))); T('dough', fill(128, (240, 220, 180), 4, 8))
    T('sack_flour', tex_burlap()); T('sack_sugar', tex_burlap(256, 256, 34, 'SUGAR', 'FINE CASTER - 10 KG', (190, 40, 80)))
    T('box_pink', tex_box()); T('ribbon', fill(64, (196, 40, 90), 2, 9))
    T('butter', tex_label(256, 128, 'BUTTER', (250, 232, 150), (30, 80, 40), 'UNSALTED 250 G')); T('shell', tex_shell()); T('shell_w', tex_shell(128, 40, (248, 244, 236)))
    T('carton', fill(128, (190, 184, 172), 4, 10) + N3(128, 0.6, 11, 8))
    T('milk_label', tex_label(256, 128, 'MILK', (250, 250, 250), (40, 110, 200), 'FULL CREAM 1 L')); T('glass_g', fill(64, (200, 230, 236), 2, 12))
    T('copper', tex_steel(256, 13, (200, 120, 70))); T('clock', tex_clock()); T('screen', tex_screen()); T('dial', tex_dial())
    c, a = tex_curtain(); T('curtain', c, a)
    c, a = tex_wire(); T('wire', c, a)
    c, a = tex_fountain(); T('fountain', c, a)
    T('flour', tex_flour()); T('batter', buttercream(128, 42, (246, 226, 160), 14)); T('gold', tex_steel(128, 43, (230, 180, 60)))
    T('coolpanel', tex_coolpanel()); T('poster_a', tex_poster()); T('poster_b', tex_poster(256, 320, 'FRESH BREAD', (176, 226, 206), 52))
    T('poster_c', tex_poster(256, 320, 'CAKE OF THE DAY', (210, 180, 236), 53))
    T('marble', fill(256, (236, 232, 228), 6, 44) + (np.abs(noise(256, 8, 45)) < 0.06)[..., None] * -40)
    T('crate', tex_wood(256, 46, (60, 120, 200))); T('rubber_b', fill(64, (40, 40, 44), 2, 13)); T('cushion', fill(128, (240, 120, 160), 4, 14))
    T('jam', fill(64, (196, 30, 60), 3, 15)); T('candy', fill(64, (250, 160, 200), 2, 16)); T('tin', tex_steel(128, 47, (230, 232, 236)))
