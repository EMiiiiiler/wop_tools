"""Custom MD3/IQM map objects for wop_padpirate (Skull Rock Bay). All geometry and art is original and generated here.
    make() -> writes models/padpirate/*.md3/*.iqm and their images (shaders are registered in pplib.REG)

Scale ~32u per metre. Architecture (fort, dive tower, tavern, shop, shacks, the skull's stair and balcony) is drawn
from the convex solids in pp_shapes.py, so the weapclip collision in build_pirate.py matches the visible surfaces;
props have their origin at the floor centre. The galleon lives in pp_ship.py.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube as _tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from pplib import *
import pplib
import layout as L
import pp_shapes as SH

TXD = 'textures/padpirate/'


def BT(name): return TXD + name


# ================================================================================================= mesh helpers
def tube(M, path, radii, **kw):
    path = np.asarray(path, float)
    r = np.atleast_1d(np.asarray(radii, float))
    if len(r) > 1 and len(r) != len(path):
        r = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(r)), r)
    _tube(M, path, r, **kw)


def cylm(M, c, r, h, n=16, caps=True, tile=128.0):
    c = np.asarray(c, float)
    revolve(M, [(0, c[2]), (r, c[2]), (r, c[2] + h), (0, c[2] + h)] if caps else [(r, c[2]), (r, c[2] + h)], n=n, cx=c[0], cy=c[1], vlen=tile)


def boxm(M, mn, mx, r=1.0, tile=64.0, k=1, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def torus(M, c, R, r, axis=(0, 0, 1), n=32, m=10, utile=4.0):
    c = np.asarray(c, float); ax = np.asarray(axis, float); ax /= np.linalg.norm(ax)
    b1, b2 = frame(ax)
    path = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * R for t in np.linspace(0, 2 * math.pi, n + 1)]
    _tube(M, np.array(path), np.full(n + 1, r), nseg=m, caps=(False, False), utiles=1, vlen=2 * math.pi * R / utile)


def cone(M, base, tip, r, n=8):
    base = np.asarray(base, float); tip = np.asarray(tip, float)
    _tube(M, np.array([base, base + (tip - base) * 0.5, tip]), np.array([r, r * 0.55, 0.3]), nseg=n, caps=(True, False))


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture(M, c, w, h, nrm, up=(0, 0, 1)):
    """textured quad centred at c facing nrm, u left->right as seen from the front"""
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm); up = np.asarray(up, float)
    right = np.cross(up, nrm); right /= np.linalg.norm(right)            # the viewer's right, so text reads correctly
    upv = np.cross(nrm, right)
    p = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2, c - right * w / 2 + upv * h / 2]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


def leaf_quads(M, base, d, length, width, droop=0.4, segs=5, twist=0.0):
    base = np.asarray(base, float); d = np.asarray(d, float); d = d / np.linalg.norm(d)
    side = np.array([-d[1], d[0], 0.0])
    o = len(M.V)
    for i in range(segs + 1):
        t = i / segs
        p = base + d * length * t + np.array([0, 0, length * (0.35 * t - droop * t * t)])
        w = width * (0.25 + 0.75 * math.sin(math.pi * min(1.0, t * 1.1 + 0.05)))
        nrm = np.array([0, 0, 1.0]) + side * twist
        for s_ in (-1, 1):
            M.add_v(p + side * s_ * w / 2, nrm, ((s_ + 1) / 2, 1 - t))
    for i in range(segs):
        a = o + 2 * i
        M.tri(a, a + 1, a + 2); M.tri(a + 1, a + 3, a + 2)


def sweep(M, path, prof, closed=False, vlen=128.0, inward=False, utile=1.0):
    P0 = np.asarray(path, float)
    n = len(P0)
    Tg = np.gradient(P0, axis=0)
    Th = Tg[:, :2] / np.maximum(np.linalg.norm(Tg[:, :2], axis=1, keepdims=True), 1e-9)
    lat = np.stack([-Th[:, 1], Th[:, 0], np.zeros(n)], 1)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P0, axis=0), axis=1))])
    pr = list(prof) + ([prof[0]] if closed else [])
    m = len(pr)
    P = np.zeros((n, m, 3)); UV = np.zeros((n, m, 2))
    cl = np.concatenate([[0], np.cumsum([math.hypot(pr[k + 1][0] - pr[k][0], pr[k + 1][1] - pr[k][1]) for k in range(m - 1)])])
    for i in range(n):
        for j, (u, v) in enumerate(pr):
            P[i, j] = P0[i] + lat[i] * u + np.array([0, 0, v])
            UV[i, j] = (cl[j] / max(cl[-1], 1e-6) * utile, Ls[i] / vlen)
    N = grid_normals(P)
    cu = np.mean([p[0] for p in prof]); cv = np.mean([p[1] for p in prof])
    cen = P0[:, None, :] + lat[:, None, :] * cu + np.array([0, 0, cv])
    if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
    if inward: N = -N
    M.grid(P, N, UV)
    return P


def circle_prof(r, n=16):
    return [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def densify(path, step=40.0):
    out_ = [np.asarray(path[0], float)]
    for a, b in zip(path, path[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for t in np.linspace(0, 1, k + 1)[1:]: out_.append(a + (b - a) * t)
    return out_


def SB(img, shade=30, **kw):
    """architecture shader on a brush texture image"""
    return S(BT(img), 'lm', shade=shade, **kw)


def ring(M, c, r0, r1, z0, z1, n=24, tile=64.0):
    """thick ring (annulus extruded): outer, inner, top, bottom"""
    revolve(M, [(r0, z0), (r1, z0), (r1, z1), (r0, z1), (r0, z0)], n=n, cx=c[0], cy=c[1], vlen=tile)


# ================================================================================================= textures (models)
def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((70, 120, 150)), C((226, 238, 244)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_bone_rock(n=512, seed=1):
    """sun-bleached coral limestone: pale bone colour, pitted, dark cracks, green-grey weathering streaks"""
    c = np.zeros((n, n, 3), np.float32) + C((222, 210, 182)) + N3(n, 1, seed, 10) + N3(n, 8, seed + 1, 14)
    pits = np.clip(noise(n, 0.6, seed + 2) - 1.4, 0, 1)
    c = c * (1 - pits * 0.45)[..., None]
    cr = np.clip(1 - np.abs(noise(n, 4, seed + 3)) * 9, 0, 1) * np.clip(noise(n, 12, seed + 4) + 0.3, 0, 1)
    c = c * (1 - cr * 0.55)[..., None]
    x, y = xy(n)
    st = np.asarray(img(noise(n, 1, seed + 5) * 40 + 128).resize((n // 12, n)).resize((n, n)), np.float32) / 255
    c = lerp(c, C((120, 126, 104)), (np.clip(st - 0.58, 0, 1) * 1.6)[..., None])
    return c


def tex_cave(n=256, seed=3):
    c = np.zeros((n, n, 3), np.float32) + C((120, 108, 92)) + N3(n, 1, seed, 10) + N3(n, 6, seed + 1, 14)
    return c * (1 - np.clip(noise(n, 0.7, seed + 2) - 1.5, 0, 1) * 0.4)[..., None]


def tex_felt(n=256, seed=5):
    return fill(n, (30, 26, 30), 4, seed) + N3(n, 0.6, seed + 1, 6)


def tex_emblem(w=256, h=192, seed=7):
    """skull and crossbones on black felt for the hat"""
    im = Image.new('RGB', (w, h), (30, 26, 30)); d = ImageDraw.Draw(im)
    wh = (236, 228, 206)
    cx, cy = w / 2, h * 0.42
    for s in (-1, 1):
        d.line([(cx - 80, cy + 20 + s * 50), (cx + 80, cy + 20 - s * 50)], fill=wh, width=18)
        for (ex, ey) in ((cx - 80, cy + 20 + s * 50), (cx + 80, cy + 20 - s * 50)):
            d.ellipse((ex - 14, ey - 14, ex + 4, ey + 4), fill=wh); d.ellipse((ex - 4, ey - 4, ex + 14, ey + 14), fill=wh)
    d.ellipse((cx - 46, cy - 54, cx + 46, cy + 30), fill=wh)
    d.rectangle((cx - 28, cy + 12, cx + 28, cy + 46), fill=wh)
    d.ellipse((cx - 32, cy - 22, cx - 7, cy + 4), fill=(30, 26, 30)); d.ellipse((cx + 7, cy - 22, cx + 32, cy + 4), fill=(30, 26, 30))
    d.polygon([(cx, cy + 6), (cx - 7, cy + 18), (cx + 7, cy + 18)], fill=(30, 26, 30))
    for k in range(4):
        d.line([(cx - 18 + k * 12, cy + 30), (cx - 18 + k * 12, cy + 46)], fill=(30, 26, 30), width=3)
    return np.asarray(im, np.float32)


def tex_gold(n=64, seed=9):
    return fill(n, (220, 172, 62), 10, seed) + N3(n, 0.5, seed + 1, 14)


def tex_coins(n=256, seed=11):
    """heap of gold coins (gold heaps, chest contents)"""
    c = fill(n, (170, 120, 40), 8, seed)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(420):
        x, y, s = r.uniform(0, n), r.uniform(0, n), r.uniform(5, 10)
        col = tuple(int(v) for v in np.array((236, 190, 70)) * r.uniform(0.75, 1.15))
        d.ellipse((x - s, y - s * 0.75, x + s, y + s * 0.75), fill=col, outline=(140, 96, 30))
    for _ in range(14):
        x, y, s = r.uniform(0, n), r.uniform(0, n), r.uniform(4, 7)
        d.ellipse((x - s, y - s, x + s, y + s), fill=[(200, 30, 40), (40, 180, 90), (60, 90, 220)][r.integers(3)])
    return np.asarray(im, np.float32)


def tex_wood(n=128, seed=13, base=(120, 80, 50)):
    return fill(n, base, 8, seed) + np.asarray(img(noise(n, 1, seed + 1) * 50 + 128).resize((n // 16, n)).resize((n, n)), np.float32)[..., None] * 0.2 - 25


def tex_barrel(w=256, h=256, seed=15):
    """staves (u round the barrel) with dark iron hoops near the ends and the middle"""
    x, y = xy(w, h)
    k = np.floor(x * 16).astype(int)
    tone = np.random.default_rng(seed).uniform(-18, 18, 16)[k % 16]
    c = np.zeros((h, w, 3), np.float32) + C((150, 100, 56)) + tone[..., None] + N3(w, 1, seed + 1, 6, h)
    c = np.where(((x * 16 % 1) < 0.06)[..., None], c * 0.55, c)
    for (y0, y1) in ((0.08, 0.16), (0.42, 0.48), (0.52, 0.58), (0.84, 0.92)):
        c = np.where(((y > y0) & (y < y1))[..., None], C((46, 44, 46)) + N3(w, 0.6, seed + 2, 6, h), c)
    return c


def tex_crate(n=256, seed=17):
    """crate face: planks with an X brace and a frame, stencilled RUM"""
    c = np.zeros((n, n, 3), np.float32) + C((176, 132, 80)) + N3(n, 1, seed, 8)
    x, y = xy(n)
    c = np.where((((y * 5) % 1.0) < 0.05)[..., None], c * 0.6, c)
    fr = (x < 0.09) | (x > 0.91) | (y < 0.09) | (y > 0.91) | (np.abs(x - y) < 0.06) | (np.abs(x + y - 1) < 0.06)
    c = np.where(fr[..., None], C((140, 98, 58)) + N3(n, 1, seed + 1, 8), c)
    c = np.where(((x < 0.095) | (x > 0.905) | (y < 0.095) | (y > 0.905))[..., None] & ~((x < 0.085) | (x > 0.915) | (y < 0.085) | (y > 0.915))[..., None], c * 0.5, c)
    return c


def tex_chest(w=256, h=128, seed=19):
    """treasure chest: dark red-brown planks with iron bands and rivets"""
    c = np.zeros((h, w, 3), np.float32) + C((110, 50, 34)) + N3(w, 1, seed, 8, h)
    x, y = xy(w, h)
    c = np.where((((y * 4) % 1.0) < 0.05)[..., None], c * 0.6, c)
    for xx in (0.1, 0.5, 0.9):
        band = np.abs(x - xx) < 0.035
        c = np.where(band[..., None], C((60, 58, 60)), c)
        riv = band & ((((y * 6) % 1.0) - 0.5) ** 2 < 0.01)
        c = np.where(riv[..., None], C((170, 150, 110)), c)
    return c


def tex_stripes(cols, n=128, k=6, seed=27):
    x, y = xy(n)
    i = (np.floor(x * k) % len(cols)).astype(int)
    c = np.zeros((n, n, 3), np.float32)
    for j, col in enumerate(cols):
        c = np.where((i == j)[..., None], C(col), c)
    return c + N3(n, 1, seed, 4)


def tex_thatch(w=256, h=256, seed=13):
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.6, seed, h) * 60 + 128).resize((w, h // 12)).resize((w, h)), np.float32) / 255
    c = lerp(C((150, 120, 66)), C((206, 176, 108)), st[..., None])
    rows = (y * 6) % 1.0
    c = c * (0.65 + 0.35 * rows)[..., None]
    return c + N3(w, 1, seed + 1, 6, h)


def tex_fringe(w=256, h=128, seed=15):
    x, y = xy(w, h)
    cut = 0.55 + 0.4 * np.abs(noise(w, 1.5, seed, h)[0])[None, :] * 0.6
    a = (y < cut).astype(np.float32)
    st = np.asarray(img(noise(w, 0.6, seed + 1, h) * 60 + 128).resize((w, max(2, h // 16))).resize((w, h)), np.float32) / 255
    c = lerp(C((140, 110, 60)), C((210, 180, 110)), st[..., None])
    return c, a * 255


def tex_bamboo(w=256, h=256, seed=21):
    """bamboo wall: vertical canes with nodes"""
    x, y = xy(w, h)
    k = np.floor(x * 10).astype(int)
    f = (x * 10) % 1.0
    c = np.zeros((h, w, 3), np.float32) + C((200, 170, 100)) * (0.7 + 0.3 * np.sin(f * math.pi))[..., None]
    off = np.random.default_rng(seed).uniform(0, 1, 10)[k % 10]
    node = np.abs(((y * 3 + off) % 1.0) - 0.5) < 0.02
    c = np.where(node[..., None], C((130, 100, 50)), c)
    return c + N3(w, 1, seed + 1, 6, h)


def tex_palm_trunk(w=128, h=256, seed=17):
    x, y = xy(w, h)
    rings = (y * 8) % 1.0
    return lerp(C((96, 76, 54)), C((150, 124, 92)), np.clip(rings * 1.4, 0, 1)[..., None]) + N3(w, 1, seed, 10, h)


def tex_frond(w=256, h=512, seed=19):
    x, y = xy(w, h)
    cx = 0.5
    leaf = np.abs(np.sin((y * 40 - np.abs(x - cx) * 18) * math.pi)) > 0.25
    env = np.abs(x - cx) < (0.48 * np.sin(np.clip(y, 0, 1) * math.pi) ** 0.5 + 0.02)
    a = (leaf & env).astype(np.float32)
    a = np.where(np.abs(x - cx) < 0.025, 1.0, a)
    c = lerp(C((40, 110, 40)), C((110, 170, 60)), np.clip(np.abs(x - cx) * 2, 0, 1)[..., None]) + N3(w, 1, seed, 10, h)
    c = np.where((np.abs(x - cx) < 0.025)[..., None], C((170, 170, 90)), c)
    return c, a * 255


def tex_flame(w=64, h=128, seed=23):
    x, y = xy(w, h)
    cx = 0.5 + 0.06 * np.sin(y * 9)
    width = 0.42 * (y ** 0.7)
    core = np.clip(1 - np.abs(x - cx) / np.maximum(width, 1e-3), 0, 1) * np.clip((y - 0.05) * 3, 0, 1)
    return np.zeros((h, w, 3), np.float32) + C((255, 120, 20)) * core[..., None] + C((255, 230, 140)) * (core ** 3)[..., None]


def tex_shark(w=256, h=128, seed=29):
    """shark skin: grey back, white belly (v: 0 top .. 1 bottom)"""
    x, y = xy(w, h)
    c = lerp(C((96, 110, 124)), C((236, 236, 230)), np.clip((y - 0.45) * 6, 0, 1)[..., None])
    return c + N3(w, 1, seed, 5, h)


def tex_map(w=256, h=256, seed=31):
    """treasure map: parchment, an island outline, a dotted trail to a red X, a compass"""
    c = np.zeros((h, w, 3), np.float32) + C((226, 200, 150)) + N3(w, 2, seed, 10, h)
    x, y = xy(w, h)
    c = lerp(c, C((150, 110, 70)), (np.clip(np.hypot(x - 0.5, y - 0.5) * 2 - 0.6, 0, 1) * 0.8)[..., None])
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    pts = [(60 + 70 * math.cos(t) * (1 + 0.25 * math.sin(3 * t)), 130 + 60 * math.sin(t) * (1 + 0.2 * math.cos(4 * t))) for t in np.linspace(0, 2 * math.pi, 40)]
    d.polygon(pts, outline=(90, 60, 30), fill=(196, 176, 120))
    for k in range(10):
        d.ellipse((40 + k * 13, 150 - k * 5, 44 + k * 13, 154 - k * 5), fill=(110, 70, 40))
    d.line([(160, 90), (180, 110)], fill=(190, 30, 20), width=6); d.line([(180, 90), (160, 110)], fill=(190, 30, 20), width=6)
    d.ellipse((190, 190, 240, 240), outline=(90, 60, 30), width=3); d.line([(215, 185), (215, 245)], fill=(90, 60, 30), width=2)
    d.line([(185, 215), (245, 215)], fill=(90, 60, 30), width=2)
    return np.asarray(im, np.float32)


def tex_wanted(w=256, h=320, seed=33):
    c = np.zeros((h, w, 3), np.float32) + C((226, 206, 160)) + N3(w, 2, seed, 10, h)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    f = font(46); f2 = font(26)
    d.text((w / 2, 40), 'WANTED', fill=(60, 30, 20), font=f, anchor='mm')
    d.rectangle((48, 76, w - 48, 236), outline=(60, 30, 20), width=4)
    cx, cy = w / 2, 150
    d.ellipse((cx - 50, cy - 56, cx + 50, cy + 44), fill=(200, 160, 110), outline=(60, 30, 20), width=3)
    d.polygon([(cx - 80, cy - 40), (cx, cy - 90), (cx + 80, cy - 40), (cx, cy - 56)], fill=(30, 26, 30))
    d.ellipse((cx - 26, cy - 20, cx - 6, cy), fill=(30, 26, 30)); d.rectangle((cx + 4, cy - 22, cx + 30, cy - 4), fill=(30, 26, 30))
    d.arc((cx - 24, cy + 4, cx + 24, cy + 30), 0, 180, fill=(60, 30, 20), width=4)
    d.text((w / 2, 266), 'DEAD OR ALIVE', fill=(60, 30, 20), font=f2, anchor='mm')
    d.text((w / 2, 298), '1000 DOUBLOONS', fill=(150, 30, 20), font=f2, anchor='mm')
    return np.asarray(im, np.float32)


def tex_chalk(w=256, h=256, seed=35):
    a = text_img('GROG  2\nRUM  3\nFISH PIE  4\nHARDTACK  1', w, h, (34, 40, 36), (236, 236, 220), True)
    return a + N3(w, 1, seed, 4, h)


def tex_parrot(n=128, seed=37):
    x, y = xy(n)
    c = lerp(C((40, 180, 70)), C((220, 40, 30)), np.clip((y - 0.55) * 5, 0, 1)[..., None])
    c = np.where((x > 0.8)[..., None], C((40, 90, 220)), c)
    return c + N3(n, 1, seed, 6)


def tex_gull(n=64, seed=39):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((240, 240, 236))
    c = np.where((x > 0.85)[..., None], C((40, 40, 44)), c)
    return c + N3(n, 1, seed, 4)


def tex_bronze(n=64, seed=41):
    return fill(n, (150, 104, 54), 8, seed) + N3(n, 0.5, seed + 1, 12)


def tex_fruit(n=128, seed=43):
    """crate of mixed tropical fruit seen from above"""
    c = fill(n, (120, 80, 40), 4, seed)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(40):
        x, y, s = r.uniform(0, n), r.uniform(0, n), r.uniform(8, 14)
        d.ellipse((x - s, y - s, x + s, y + s), fill=[(250, 160, 30), (240, 210, 40), (200, 40, 40), (120, 180, 50)][r.integers(4)])
    return np.asarray(im, np.float32)


def tex_fish(n=128, seed=45):
    c = fill(n, (200, 200, 210), 4, seed)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    for k in range(6):
        y = 12 + k * 20
        d.ellipse((10, y, 100, y + 14), fill=(150, 170, 190), outline=(90, 100, 120))
        d.polygon([(100, y + 7), (118, y), (118, y + 14)], fill=(150, 170, 190))
    return np.asarray(im, np.float32)


def make_textures():
    T('env', tex_env())
    T('bone_rock', tex_bone_rock()); T('cave', tex_cave()); T('cave_dark', tex_cave(256, 77) * 0.55); T('felt', tex_felt()); T('emblem', tex_emblem())
    T('gold', tex_gold()); T('coins', tex_coins()); T('wood', tex_wood()); T('wood_dark', tex_wood(128, 47, (80, 52, 34)))
    T('wood_light', tex_wood(128, 49, (176, 134, 88))); T('barrel', tex_barrel()); T('crate', tex_crate()); T('chest', tex_chest())
    T('canvas_rw', tex_stripes([(200, 40, 34), (244, 236, 216)], 128, 8)); T('canvas_bw', tex_stripes([(30, 50, 100), (244, 236, 216)], 128, 8))
    T('canvas_gy', tex_stripes([(60, 120, 70), (230, 200, 90)], 128, 8)); T('canvas', fill(64, (232, 222, 196), 4, 51))
    T('thatch', tex_thatch()); f, a = tex_fringe(); T('fringe', f, a); T('bamboo', tex_bamboo())
    T('palm_trunk', tex_palm_trunk()); f, a = tex_frond(); T('frond', f, a); T('flame', tex_flame()); T('shark', tex_shark())
    T('map', tex_map()); T('wanted', tex_wanted()); T('chalk', tex_chalk()); T('parrot', tex_parrot()); T('gull', tex_gull())
    T('bronze', tex_bronze()); T('fruit', tex_fruit()); T('fish', tex_fish())
    T('iron', fill(64, (44, 44, 48), 4, 53) + N3(64, 0.5, 54, 8)); T('black', fill(64, (22, 20, 20), 2, 55)); T('white', fill(64, (240, 236, 226), 3, 56))
    T('red', fill(64, (176, 44, 36), 4, 57)); T('bone', fill(64, (232, 222, 196), 5, 58) + N3(64, 0.5, 59, 8)); T('rope', fill(64, (176, 146, 96), 6, 60) + N3(64, 0.5, 61, 10))
    T('lantern', fill(32, (255, 214, 130), 2, 62)); T('glass_g', fill(32, (60, 140, 80), 3, 63)); T('glass_b', fill(32, (110, 60, 30), 3, 64))
    T('coconut', fill(64, (110, 80, 50), 8, 65)); T('sand_m', fill(64, (226, 206, 156), 6, 66)); T('orange', fill(64, (240, 130, 30), 4, 67))
    T('yellow', fill(64, (250, 204, 40), 4, 68)); T('rock_m', fill(128, (130, 122, 108), 10, 69) + N3(128, 3, 70, 14))
    T('moss_rock', lerp(fill(128, (130, 122, 108), 10, 71), C((70, 110, 50)), np.clip(noise(128, 6, 72) * 0.6, 0, 1)[..., None]))
    T('water_strip', *(lambda f_a: f_a)(water_strip()))
    T('slide_in', fill(128, (60, 180, 196), 4, 73) + N3(128, 6, 74, 6))
    T('glow_red', fill(32, (255, 60, 30), 2, 75))


def water_strip(w=64, h=256, seed=37):
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.8, seed, h) * 60 + 128).resize((w, h // 16)).resize((w, h)), np.float32) / 255
    a = np.clip(0.35 + (st - 0.5) * 1.6, 0, 1) * np.clip(1 - np.abs(x - 0.5) * 1.6, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((200, 236, 245)) + (st * 40)[..., None]
    return c, a * 255


# ================================================================================================= Skull Rock
def skull_rock():
    """the hollow skull (carved shell: mouth door, nose, eye windows), teeth, the inner stair and balcony, and the
    tricorn hat with its gold braid, emblem and the shaft through the crown. Origin = base centre."""
    X = Model()
    cx, cy = L.SK
    out_sh = S('bone_rock', 'lm', shade=70); in_sh = S('cave', 'lm', shade=70); jam_sh = S('cave_dark', 'lm', shade=70, tag='j')
    polys = L.sk_face_polys()
    zs = sorted(set([z for (_, z) in L.SK_ROWS] + list(range(0, L.SK_TOP + 1, 20))))
    rows = [(L.sk_profile(z), float(z)) for z in zs]
    carved_shell(X.mesh(out_sh), X.mesh(in_sh), X.mesh(jam_sh), rows, 128, L.SK_THICK, polys, L.SK_FACE, L.SK_RR, deform=L.sk_deform,
                 u_tiles=6, vlen=300, close_top=True, depth=3, jstep=8)
    # dark socket shading: soot-dark ring quads just inside the eye and nose openings are part of the cave texture;
    # teeth hanging from the upper lip and a few at the corners of the lower jaw
    th = X.mesh(S('bone', 'lm', shade=60, tag='t'))
    for u in np.linspace(-132, 132, 9):
        a = L.SK_FACE + math.degrees(u / L.SK_RR)
        ztop = 150 - 22 * (abs(u) / 150) ** 3
        r = L.sk_deform(math.radians(a), L.sk_profile(ztop), ztop)
        c = np.array(L.ang_pt(0, 0, r - 14, a) + (ztop - 12,))
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0])
        t_ = np.array([-d[1], d[0], 0])
        m = Mesh(); rbox(m, (-13, -11, -22), (13, 11, 14), r=6, k=3, tile=32)
        R = np.stack([t_, d, [0, 0, 1.0]], 1)
        th.add(m, R, c)
    for u in (-128, -100, 100, 128):
        a = L.SK_FACE + math.degrees(u / L.SK_RR)
        r = L.sk_deform(math.radians(a), L.sk_profile(10), 10)
        c = np.array(L.ang_pt(0, 0, r - 14, a) + (0,))
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0]); t_ = np.array([-d[1], d[0], 0])
        m = Mesh(); rbox(m, (-11, -10, 0), (11, 10, 22), r=5, k=3, tile=32)
        th.add(m, np.stack([t_, d, [0, 0, 1.0]], 1), c)
    # inner stair + balcony (exact collision shapes), cave rock
    st = S('cave', 'lm', shade=30, tag='st'); tr = S(BT('rock'), 'lm', shade=30, tag='st')
    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if n[2] > 0.9: return tr, planar_uv(n, 128)
        return st, planar_uv(n, 128)
    I = Model()
    solids_mesh(I, SH.skull_interior(), texfn)
    I.shift((cx, cy, 0))
    X.add_model(I)
    # the tricorn hat: brim (flat walk to BRIM_R1, curling up toward three points beyond it), crown, braid, emblem
    felt = S('felt', 'lm', shade=70); gd = S('gold', 'lms', v=0.3, tag='hat'); em = S('emblem', 'lm', tag='hat')
    def brim_lift(a):
        da = [abs(((math.degrees(a) - p + 180) % 360) - 180) for p in (L.SK_FACE, L.SK_FACE + 120, L.SK_FACE - 120)]
        k = min(da) / 60.0
        notch = min(abs(((math.degrees(a) - q + 180) % 360) - 180) for q in (0.0, 180.0))     # flat where the slides leave
        return max(0.0, 1 - k) ** 1.5 * min(1.0, (notch / 28.0) ** 2)
    nB = 96
    angs = np.linspace(0, 2 * math.pi, nB + 1)
    rs = [L.BRIM_R0 - 20, 360, 420, L.BRIM_R1]
    def brim_r_out(a): return L.BRIM_R1 + 24 + 50 * brim_lift(a)
    def brim_z_out(a): return L.BRIM_Z + 10 + 54 * brim_lift(a)
    # top surface: flat ring BRIM_R0-20 .. BRIM_R1 at BRIM_Z, then the curl up to the edge
    P = np.zeros((6, nB + 1, 3)); N = np.zeros_like(P); UV = np.zeros((6, nB + 1, 2))
    for j, a in enumerate(angs):
        c_, s_ = math.cos(a), math.sin(a)
        prof = [(rs[0], L.BRIM_Z), (rs[1], L.BRIM_Z), (rs[2], L.BRIM_Z), (rs[3], L.BRIM_Z + 0.5),
                (L.BRIM_R1 + 12, L.BRIM_Z + 3 + 20 * brim_lift(a)), (brim_r_out(a), brim_z_out(a))]
        for i, (r, z) in enumerate(prof):
            P[i, j] = (r * c_, r * s_, z); UV[i, j] = (a / (2 * math.pi) * 24, r / 128)
    N = grid_normals(P)
    if N[0, 0, 2] < 0: N = -N
    X.mesh(felt).grid(P, N, UV)
    # underside of the brim (outside the skull) and its edge
    P2 = np.zeros((3, nB + 1, 3)); UV2 = np.zeros((3, nB + 1, 2))
    for j, a in enumerate(angs):
        c_, s_ = math.cos(a), math.sin(a)
        for i, (r, z) in enumerate(((L.sk_profile(L.SK_TOP) * 0.98, L.HAT_Z0), (L.BRIM_R1 - 10, L.HAT_Z0 + 2), (brim_r_out(a) - 4, brim_z_out(a) - 14))):
            P2[i, j] = (r * c_, r * s_, z); UV2[i, j] = (a / (2 * math.pi) * 24, r / 128)
    N2 = grid_normals(P2)
    if N2[0, 0, 2] > 0: N2 = -N2
    X.mesh(felt).grid(P2, N2, UV2)
    P3 = np.zeros((2, nB + 1, 3)); UV3 = np.zeros((2, nB + 1, 2))
    for j, a in enumerate(angs):
        c_, s_ = math.cos(a), math.sin(a)
        P3[0, j] = ((brim_r_out(a) - 4) * c_, (brim_r_out(a) - 4) * s_, brim_z_out(a) - 14)
        P3[1, j] = (brim_r_out(a) * c_, brim_r_out(a) * s_, brim_z_out(a))
        UV3[:, j, 0] = a / (2 * math.pi) * 24; UV3[:, j, 1] = (0, 0.1)
    N3_ = grid_normals(P3)
    if (N3_[0, 0, :2] @ np.array([1.0, 0])) < 0: N3_ = -N3_
    X.mesh(felt).grid(P3, N3_, UV3)
    # gold braid along the brim edge
    edge = [np.array([brim_r_out(a) * math.cos(a), brim_r_out(a) * math.sin(a), brim_z_out(a) - 3]) for a in angs]
    tube(X.mesh(gd), edge, 5, nseg=6, caps=(False, False), vlen=64)
    # crown: frustum with a rounded top edge, flat top with the shaft hole, a hat band, the shaft walls
    crown = [(L.BRIM_R0, L.BRIM_Z), (L.BRIM_R0 - 6, L.BRIM_Z + 40), (L.BRIM_R0 - 30, L.BRIM_Z + 90), (L.CROWN_R + 14, L.CROWN_Z - 10),
             (L.CROWN_R, L.CROWN_Z)]
    revolve(X.mesh(felt), crown, n=64, u_tiles=16, vlen=128)
    disc(X.mesh(felt), L.CROWN_R, L.CROWN_Z, up=True, n=64, r_in=L.SHAFT_R)
    revolve(X.mesh(gd), [(L.BRIM_R0 + 2, L.BRIM_Z + 2), (L.BRIM_R0 + 3, L.BRIM_Z + 14), (L.BRIM_R0 - 1, L.BRIM_Z + 26)], n=64, u_tiles=32, vlen=32)
    revolve(X.mesh(S('cave', 'lm', tag='shaft')), [(L.SHAFT_R, L.CROWN_Z), (L.SHAFT_R, L.HAT_Z0)], n=24, vlen=128, inward=True)
    # ceiling of the cave (underside of the brim slab inside the skull)
    disc(X.mesh(S('cave', 'lm', tag='ceil')), L.sk_profile(L.SK_TOP) - L.SK_THICK + 2, L.HAT_Z0 - 0.5, up=False, n=64, r_in=L.SHAFT_R)
    # emblem on the front of the crown
    a = math.radians(L.SK_FACE)
    rface = L.BRIM_R0 - 18
    c = np.array([rface * math.cos(a), rface * math.sin(a), L.BRIM_Z + 60])
    picture(X.mesh(em), c + np.array([math.cos(a), math.sin(a), 0]) * 4, 150, 112, (math.cos(a), math.sin(a), 0.35))
    # a feather plume on the side of the hat
    pl = S('parrot', 'lm', tag='plume')
    base = np.array(L.ang_pt(0, 0, L.BRIM_R0 - 30, L.SK_FACE + 60) + (L.BRIM_Z + 70,))
    pts = [base + np.array([0, 0, 0]), base + np.array([30, 40, 80]), base + np.array([60, 120, 120]), base + np.array([40, 190, 110])]
    tube(X.mesh(pl), pts, [14, 18, 12, 2], nseg=8, ry=[6, 6, 4, 1])
    return save('skull_rock', X)


# ================================================================================================= Fort San Padro
FORT_O = (-1760.0, 1216.0)


def fort():
    X = Model()
    sw = SB('fort_stone', 30, tag='f'); sf = SB('fort_floor', 30, tag='f'); sc = SB('coping', 30, tag='f'); dark = S('black', 'lm', tag='f')
    allb = SH.fort()
    mg = L.MAG
    def in_mag(p): return mg[0] - 0.5 <= p[0] <= mg[2] + 0.5 and mg[1] - 0.5 <= p[1] <= mg[3] + 0.5 and p[2] <= L.MAG_H + 0.5
    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        q = c + n * 2
        if n[2] > 0.9:
            if c[2] > L.FORT_H + 1 or abs(c[2] - L.TOWER_H) < 1: return sc, planar_uv(n, 128)
            return sf, planar_uv(n, 256)
        if n[2] < -0.9: return sw, planar_uv(n, 256)
        return sw, planar_uv(n, 256)
    solids_mesh(X, allb, texfn)
    # coping strip along the rampart's inner edge, gate: open wooden doors + raised portcullis, sign, arrow slits on the tower
    x0, y0, x1, y1 = L.FORT
    gx = (x0 + x1) / 2; ghw, gh = L.FORT_GATE
    wd = S('wood_dark', 'lm', tag='f'); ir = S('iron', 'lm', tag='f')
    for s in (-1, 1):                     # doors swung inward against the passage walls
        xx = gx + s * (ghw - 6)
        boxm(X.mesh(wd), (min(xx, xx - s * 8), y0 + L.FORT_W - 4, 0), (max(xx, xx - s * 8), y0 + L.FORT_W + 120, gh - 8), r=1, tile=128)
        for z in (30, gh - 50):
            boxm(X.mesh(ir), (min(xx - s * 8, xx - s * 10), y0 + L.FORT_W, z), (max(xx - s * 8, xx - s * 10), y0 + L.FORT_W + 116, z + 8), r=0.5, tile=32)
    for k in range(7):                    # portcullis tips hanging below the lintel
        xx = gx - ghw + 10 + k * (2 * ghw - 20) / 6
        tube(X.mesh(ir), [(xx, y0 + 48, gh + 30), (xx, y0 + 48, gh - 18)], 3, nseg=6)
        cone(X.mesh(ir), (xx, y0 + 48, gh - 18), (xx, y0 + 48, gh - 32), 4, 6)
    boxm(X.mesh(ir), (gx - ghw, y0 + 44, gh - 4), (gx + ghw, y0 + 52, gh + 2), r=0.5, tile=32)
    sg = S(BT('sign_fort'), 'lm', tag='f')
    picture(X.mesh(sg), (gx, y0 - 1, gh + 30), 300, 38, (0, -1, 0))
    tx, ty = L.TOWER
    for k in range(6):
        a = math.radians(-120 + k * 50)
        for z in (140, 300):
            p = np.array([tx + (L.TOWER_R + 0.6) * math.cos(a), ty + (L.TOWER_R + 0.6) * math.sin(a), z])
            picture(X.mesh(dark), p, 10, 44, (math.cos(a), math.sin(a), 0))
    # flagpole on the tower with the Jolly Roger
    fl = S('jolly', 'flag', div=60, amp=6, freq=0.8, tag='ft')
    tube(X.mesh(wd), [(tx, ty, L.TOWER_H), (tx, ty, L.TOWER_H + 300)], [5, 3], nseg=8)
    P = [np.array([tx, ty, L.TOWER_H + 196]), np.array([tx + 150, ty, L.TOWER_H + 196]), np.array([tx + 150, ty, L.TOWER_H + 290]), np.array([tx, ty, L.TOWER_H + 290])]
    X.mesh(fl).poly(P, (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    X.mesh(fl).poly(P[::-1], (0, 1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    # magazine: barrels are props; a dark arch over its door
    md = (mg[0] + mg[2]) / 2
    boxm(X.mesh(wd), (md - 46, y1 - L.FORT_NW - 3, 0), (md - 40, y1 - L.FORT_NW + 1, 136), r=0.5, tile=32)
    boxm(X.mesh(wd), (md + 40, y1 - L.FORT_NW - 3, 0), (md + 46, y1 - L.FORT_NW + 1, 136), r=0.5, tile=32)
    boxm(X.mesh(wd), (md - 46, y1 - L.FORT_NW - 3, 128), (md + 46, y1 - L.FORT_NW + 1, 136), r=0.5, tile=32)
    X.shift((FORT_O[0], FORT_O[1], 0))
    return save('fort', X)


# ================================================================================================= dive tower
def dive_tower():
    X = Model()
    cx, cy = L.DIVE
    pl = SB('boardwalk', 30, tag='dv'); wd = S('wood', 'lm', tag='dv'); rp = S('rope', 'lm', tag='dv'); ir = S('iron', 'lm', tag='dv')
    blist, steps, holes = SH.dive_tower()
    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        return pl, planar_uv(n, 128)
    solids_mesh(X, blist, texfn)
    h = L.DIVE_HALF
    # four corner posts (masts) from the ground to above the top, with cross braces
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        px, py = cx + sx * (h - 6), cy + sy * (h - 6)
        tube(X.mesh(wd), [(px, py, 0), (px, py, L.DIVE_TOP + 120)], [9, 7], nseg=10)
    for z in (100, 220, 330):
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            pa = np.array([cx + a[0] * (h - 6), cy + a[1] * (h - 6), z]); pb = np.array([cx + b[0] * (h - 6), cy + b[1] * (h - 6), z + 50])
            tube(X.mesh(wd), [pa, pb], 3.5, nseg=6)
    # rope rails round the top (the collision rail is common/clip, 40 high)
    for (a, b) in (((-1, 1), (1, 1)), ((1, 1), (1, -1)), ((0, -1), (1, -1)), ((-1, 1), (-1, 0.36)), ((-1, 0.86), (-1, 1))):
        for z in (L.DIVE_TOP + 20, L.DIVE_TOP + 40):
            pa = np.array([cx + a[0] * (h - 4), cy + a[1] * (h - 4), z]); pb = np.array([cx + b[0] * (h - 4), cy + b[1] * (h - 4), z])
            tube(X.mesh(rp), [pa, (pa + pb) / 2 - [0, 0, 4], pb], 1.6, nseg=5)
    # the plank (walk the plank!) over the pool, iron strap where it is bolted on
    py0, py1 = cy + 64, cy + 112
    boxm(X.mesh(S(BT('planks'), 'lm', tag='plk')), (cx - h - 224, py0, L.DIVE_TOP - 8), (cx - h, py1, L.DIVE_TOP), r=1, tile=128)
    boxm(X.mesh(ir), (cx - h - 10, py0 - 2, L.DIVE_TOP - 9), (cx - h + 10, py1 + 2, L.DIVE_TOP + 1), r=0.5, tile=32)
    # crow's nest decoration and a flag on top of the north-east post
    fl = S('jolly', 'flag', div=60, amp=5, freq=1.1, tag='dv')
    px, py = cx + h - 6, cy + h - 6
    P = [np.array([px, py, L.DIVE_TOP + 40]), np.array([px - 110, py, L.DIVE_TOP + 40]), np.array([px - 110, py, L.DIVE_TOP + 110]), np.array([px, py, L.DIVE_TOP + 110])]
    X.mesh(fl).poly(P, (0, -1, 0), [(1, 1), (0, 1), (0, 0), (1, 0)])
    X.mesh(fl).poly(P[::-1], (0, 1, 0), [(1, 0), (0, 0), (0, 1), (1, 1)])
    X.shift((cx, cy, 0))
    return save('dive_tower', X)


# ================================================================================================= buildings
def building(name, blist, rect, ext, inn, roof_top='planks', trim='wood_dark'):
    """walls from pp_shapes: faces looking out of the footprint get the exterior texture, the rest the interior one"""
    X = Model()
    x0, y0, x1, y1 = rect
    se = SB(ext, 30, tag=name); si = SB(inn, 30, tag=name + 'i'); sr = SB(roof_top, 30, tag=name + 'r'); st = S(trim, 'lm', tag=name)
    sfl = SB('planks', 30, tag=name + 'f')
    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        inside = x0 + 23 < c[0] < x1 - 23 and y0 + 23 < c[1] < y1 - 23
        beyond = not (x0 - 10 < c[0] < x1 + 10 and y0 - 10 < c[1] < y1 + 10)
        if beyond: return sfl, planar_uv(n, 128)                       # outside stairs
        if n[2] > 0.9:
            return sr, planar_uv(n, 256)
        if n[2] < -0.9:
            return (si if inside else st), planar_uv(n, 256)
        q = c + n * 3
        out_ = not (x0 < q[0] < x1 and y0 < q[1] < y1)
        if out_: return se, planar_uv(n, 256)
        return si, planar_uv(n, 256)
    solids_mesh(X, blist, texfn)
    return X


def tavern():
    x0, y0, x1, y1 = L.TAV
    X = building('tav', SH.tavern(), L.TAV, 'timber_wall', 'plaster', 'boardwalk')
    wd = S('wood_dark', 'lm', tag='tv'); ir = S('iron', 'lm', tag='tv'); gd = S('gold', 'lms', v=0.25, tag='tv')
    yc = (y0 + y1) / 2
    # hanging sign over the door on an iron bracket, an anchor on the gable
    sg = S(BT('sign_tavern'), 'lm', tag='tv')
    picture(X.mesh(sg), (x0 - 2, yc, 214), 280, 52, (-1, 0, 0))
    # window frames + shutters, door frame
    for (side, c, hw, zb, zt) in (('w', yc - 170, 44, 72, 168), ('w', yc + 170, 44, 72, 168), ('s', x0 + 140, 44, 72, 168),
                                  ('n', x0 + 140, 44, 72, 168), ('n', x1 - 160, 44, 72, 168), ('e', yc, 44, 96, 168)):
        win_frame(X, side, c, hw, zb, zt, L.TAV, wd, shutters=S('canvas_bw', 'lm', tag='sh'))
    win_frame(X, 'w', yc, 60, 0, 168, L.TAV, wd, shutters=None, door=True)
    # roof terrace dressing: rope rail on wooden posts above the clip rail, two lanterns on poles
    rp = S('rope', 'lm', tag='tv')
    H = L.TAV_H
    posts = []
    for x in np.linspace(x0 - 4, x1 + 4, 7):
        posts += [(x, y0 - 4), (x, y1 + 4)]
    for y in np.linspace(y0 - 4, y1 + 4, 6)[1:-1]:
        posts += [(x0 - 4, y), (x1 + 4, y)]
    for (px, py) in posts:
        if py < y0 and px > x1 - 130: continue
        cylm(X.mesh(wd), (px, py, H), 3.5, 38, n=8)
    # bar counter top, shelves on the back wall (bottles are props)
    for z in (84, 124, 164):
        boxm(X.mesh(wd), (x1 - 24 - 30, yc - 180, z), (x1 - 24, yc + 180, z + 4), r=0.5, tile=64)
    # chandelier: a wagon wheel with candles hanging from the ceiling
    ch = np.array([(x0 + x1) / 2 - 60, yc, H - 80])
    torus(X.mesh(wd), ch, 60, 4, n=24, m=6)
    for k in range(8):
        a = 2 * math.pi * k / 8
        tube(X.mesh(wd), [ch, ch + [60 * math.cos(a), 60 * math.sin(a), 0]], 2, nseg=5)
        cylm(X.mesh(S('white', 'lm', tag='cdl')), ch + [60 * math.cos(a), 60 * math.sin(a), 2], 2.5, 12, n=6)
    for s in (-1, 1):
        tube(X.mesh(ir), [ch + [0, 0, 0], ch + [s * 30, 0, 64]], 1, nseg=4)
    # porch over the door: posts, a slanted plank roof, hanging lanterns
    for s in (-1, 1):
        tube(X.mesh(wd), [(x0 - 86, yc + s * 112, 0), (x0 - 86, yc + s * 112, 152)], 6, nseg=8)
    pr = S(BT('boardwalk'), 'lm', tag='porch', two=True)
    P_ = [np.array([x0 - 1, yc - 130, 186.0]), np.array([x0 - 1, yc + 130, 186.0]), np.array([x0 - 100, yc + 130, 150.0]), np.array([x0 - 100, yc - 130, 150.0])]
    nn = np.cross(P_[1] - P_[0], P_[3] - P_[0]); nn /= np.linalg.norm(nn)
    if nn[2] < 0: nn = -nn
    X.mesh(pr).poly(P_, nn, [(0, 0), (2, 0), (2, 0.8), (0, 0.8)])
    boxm(X.mesh(wd), (x0 - 92, yc - 130, 144), (x0 - 80, yc + 130, 152), r=1, tile=64)
    lan = S('lantern', 'glow', tag='tvl')
    for s in (-1, 1):
        tube(X.mesh(ir), [(x0 - 86, yc + s * 90, 150), (x0 - 86, yc + s * 90, 132)], 1, nseg=4)
        revolve(X.mesh(lan), [(0, 106), (7, 110), (8, 120), (6, 130), (0, 132)], n=8, cx=x0 - 86, cy=yc + s * 90, vlen=16)
    # wanted posters and the treasure map on the walls
    wp = S('wanted', 'lm', tag='tv'); mp = S('map', 'lm', tag='tv')
    picture(X.mesh(wp), (x0 + 24.6, yc - 70, 120), 40, 50, (1, 0, 0))
    picture(X.mesh(wp), (x0 + 140, y1 - 24.6, 120), 40, 50, (0, -1, 0))
    picture(X.mesh(mp), ((x0 + x1) / 2 + 60, y0 + 24.6, 120), 90, 90, (0, 1, 0))
    picture(X.mesh(S('chalk', 'lm', tag='tv')), (x1 - 24.6, yc + 230, 120), 60, 60, (-1, 0, 0))
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('tavern', X)


def win_frame(X, side, c, hw, zb, zt, rect, sh, shutters=None, door=False):
    x0, y0, x1, y1 = rect
    t = 4
    if side in 'ns':
        y = y0 if side == 's' else y1
        o = -1 if side == 's' else 1
        for xx in (c - hw - t, c + hw):
            boxm(X.mesh(sh), (xx, min(y, y + o * 6), zb if not door else 0), (xx + t, max(y, y + o * 6), zt + t), r=0.5, tile=32)
        boxm(X.mesh(sh), (c - hw - t, min(y, y + o * 6), zt), (c + hw + t, max(y, y + o * 6), zt + t), r=0.5, tile=32)
        if not door: boxm(X.mesh(sh), (c - hw - 8, min(y, y + o * 10), zb - 6), (c + hw + 8, max(y, y + o * 10), zb), r=0.5, tile=32)
        if shutters:
            for s in (-1, 1):
                xa = c + s * (hw + t); xb = xa + s * hw * 0.9
                boxm(X.mesh(shutters), (min(xa, xb), min(y + o * 2, y + o * 5), zb), (max(xa, xb), max(y + o * 2, y + o * 5), zt), r=0.5, tile=64)
    else:
        x = x0 if side == 'w' else x1
        o = -1 if side == 'w' else 1
        for yy in (c - hw - t, c + hw):
            boxm(X.mesh(sh), (min(x, x + o * 6), yy, zb if not door else 0), (max(x, x + o * 6), yy + t, zt + t), r=0.5, tile=32)
        boxm(X.mesh(sh), (min(x, x + o * 6), c - hw - t, zt), (max(x, x + o * 6), c + hw + t, zt + t), r=0.5, tile=32)
        if not door: boxm(X.mesh(sh), (min(x, x + o * 10), c - hw - 8, zb - 6), (max(x, x + o * 10), c + hw + 8, zb), r=0.5, tile=32)
        if shutters:
            for s in (-1, 1):
                ya = c + s * (hw + t); yb = ya + s * hw * 0.9
                boxm(X.mesh(shutters), (min(x + o * 2, x + o * 5), min(ya, yb), zb), (max(x + o * 2, x + o * 5), max(ya, yb), zt), r=0.5, tile=64)


def shop():
    x0, y0, x1, y1 = L.SHOP
    X = building('shp', SH.shop(), L.SHOP, 'shop_wall', 'plaster', 'boardwalk')
    wd = S('wood_dark', 'lm', tag='sp')
    yc = (y0 + y1) / 2
    picture(X.mesh(S(BT('sign_shop'), 'lm', tag='sp')), (x0 - 2, yc, 168), 300, 46, (-1, 0, 0))
    for (side, c, hw, zb, zt) in (('w', yc - 120, 36, 64, 140), ('w', yc + 120, 36, 64, 140), ('s', (x0 + x1) / 2, 40, 64, 140), ('n', (x0 + x1) / 2, 40, 64, 140)):
        win_frame(X, side, c, hw, zb, zt, L.SHOP, wd, shutters=S('canvas_rw', 'lm', tag='ssh'))
    win_frame(X, 'w', yc, 56, 0, 152, L.SHOP, wd, door=True)
    # striped awning over the door on two posts
    cv = S('canvas_rw', 'lm', tag='aw', two=True)
    P = [np.array([x0, yc - 110, 158]), np.array([x0, yc + 110, 158]), np.array([x0 - 70, yc + 110, 132]), np.array([x0 - 70, yc - 110, 132])]
    X.mesh(cv).poly(P, (-0.35, 0, 0.94), [(0, 0), (4, 0), (4, 1), (0, 1)])
    for s in (-1, 1):
        cylm(X.mesh(wd), (x0 - 68, yc + s * 106, 0), 3, 132, n=8)
    picture(X.mesh(S('map', 'lm', tag='sp')), (x0 + 24.6, yc + 100, 110), 70, 70, (1, 0, 0))
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('shop', X)


def shack(name, rect, door):
    x0, y0, x1, y1 = rect
    X = building(name, SH.shack(rect, door), rect, 'bamboo_w', 'bamboo_w', 'thatch_t')
    fr = S('fringe', 'alpha', tag=name)
    H = L.SHACK_H
    # bamboo corner posts and a palm-thatch roll round the roof edge
    bp = S('bamboo', 'lm', tag=name + 'p'); th = S('thatch', 'lm', shade=70, tag=name + 't')
    for (px, py) in ((x0 - 4, y0 - 4), (x1 + 4, y0 - 4), (x1 + 4, y1 + 4), (x0 - 4, y1 + 4)):
        tube(X.mesh(bp), [(px, py, 0), (px, py, H + 26)], 7, nseg=8, vlen=64)
    for (a, b) in (((x0 - 8, y0 - 8), (x1 + 8, y0 - 8)), ((x1 + 8, y0 - 8), (x1 + 8, y1 + 8)), ((x1 + 8, y1 + 8), (x0 - 8, y1 + 8)), ((x0 - 8, y1 + 8), (x0 - 8, y0 - 8))):
        tube(X.mesh(th), [(a[0], a[1], H + 2), (b[0], b[1], H + 2)], 10, nseg=8, vlen=64, caps=(False, False))
    # thatch fringe round the roof edge
    for (a, b, nrm) in (((x0 - 8, y0 - 8), (x1 + 8, y0 - 8), (0, -1, 0)), ((x1 + 8, y0 - 8), (x1 + 8, y1 + 8), (1, 0, 0)),
                        ((x1 + 8, y1 + 8), (x0 - 8, y1 + 8), (0, 1, 0)), ((x0 - 8, y1 + 8), (x0 - 8, y0 - 8), (-1, 0, 0))):
        Ln = math.hypot(b[0] - a[0], b[1] - a[1])
        P = [np.array([a[0], a[1], H]), np.array([b[0], b[1], H]), np.array([b[0], b[1], H - 40]), np.array([a[0], a[1], H - 40])]
        quad_uv(X.mesh(fr), *P, [(0, 0), (Ln / 128, 0), (Ln / 128, 1), (0, 1)], nrm)
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save(name, X)


# ================================================================================================= slides
def cannon_tube(path, sup):
    """Cannonball Run: a black bronze-banded tube on timber trestles, turquoise inside, running water. World coords."""
    X = Model()
    body = S('iron', 'lm', shade=60, tag='ct'); inner = S('slide_in', 'lm', shade=60); band = S('bronze', 'lms', v=0.2, tag='ct')
    wat = S('water_strip', 'flow', speed=-1.4); wd = S('wood_dark', 'lm', tag='ct')
    P = densify(path[1:], 40)
    C3 = [np.array([p[0], p[1], p[2] + L.TUBE_ZC]) for p in P]
    sweep(X.mesh(body), C3, circle_prof(L.TUBE_R, 20), closed=True, vlen=192)
    sweep(X.mesh(inner), C3, circle_prof(L.TUBE_R - 4, 20), closed=True, vlen=256, inward=True)
    sweep(X.mesh(wat), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-34, 0), (34, 0)], vlen=200)
    for i in range(2, len(C3) - 2, 4):
        d = C3[i + 1] - C3[i - 1]; d /= np.linalg.norm(d)
        tor = Mesh(); revolve(tor, [(L.TUBE_R + 0.5, -5), (L.TUBE_R + 4, -3), (L.TUBE_R + 4, 3), (L.TUBE_R + 0.5, 5)], n=20, vlen=16)
        b1, b2 = frame(d)
        X.mesh(band).add(tor, np.stack([b1, b2, d], 1), C3[i])
    for (x, y, z) in sup:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        for s in (-1, 1):
            tube(X.mesh(wd), [(x + s * 26, y, 0), (x + s * 12, y, zt - 8)], 6, nseg=6)
        boxm(X.mesh(wd), (x - 40, y - 10, zt - 16), (x + 40, y + 10, zt), r=1, tile=64)
    return save('cannon_tube', X)


def tube_mouth():
    """the tube entrance on the brim: a giant cannon muzzle (players walk into the barrel); faces +x, origin floor centre"""
    X = Model()
    br = S('bronze', 'lms', v=0.22, tag='tm'); ir = S('iron', 'lm', tag='tm')
    R = L.TUBE_R
    zc = L.TUBE_ZC
    m = Mesh()
    revolve(m, [(R + 2, 0), (R + 22, 0), (R + 30, 14), (R + 30, 30), (R + 20, 40), (R + 20, 120), (R + 26, 130), (R + 26, 140), (R + 2, 140)], n=24, vlen=128)
    X.mesh(br).add(m, rot_axis((0, 1, 0), -math.pi / 2), (40, 0, zc))
    for s in (-1, 1):
        tube(X.mesh(ir), [(-60, s * (R + 26), zc - 40), (-60, s * (R + 26), zc + 6)], 8, nseg=8)
    return save('tube_mouth', X)


def log_flume(path, sup):
    """Plank Plunge: an open wooden trough with iron bands on timber trestles. World coords."""
    X = Model()
    r = 52; lip = 46
    zc = r * 0.55
    wd = SB('planks', 60, tag='lf'); inn = S('slide_in', 'lm', shade=60, tag='f'); ir = S('iron', 'lm', tag='lf'); tw = S('wood_dark', 'lm', tag='lf')
    prof_out = [(-(r + 6), lip)] + [((r + 6) * math.cos(a), zc + (r + 6) * math.sin(a)) for a in np.radians(np.linspace(180, 360, 9))] + [((r + 6), lip)]
    prof_in = [(-r, lip)] + [(r * math.cos(a), zc + r * math.sin(a)) for a in np.radians(np.linspace(180, 360, 9))] + [(r, lip)]
    P = densify(path[1:], 40)
    sweep(X.mesh(wd), P, prof_out, vlen=128)
    sweep(X.mesh(inn), P, prof_in, vlen=256, inward=True)
    sweep(X.mesh(tw), P, [(-(r + 6), lip), (-(r + 6), lip + 3), (-r, lip + 3)], vlen=128)
    sweep(X.mesh(tw), P, [(r, lip + 3), (r + 6, lip + 3), (r + 6, lip)], vlen=128)
    sweep(X.mesh(S('water_strip', 'flow', speed=-1.4, tag='f')), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-r * 0.6, 0), (r * 0.6, 0)], vlen=200)
    for i in range(3, len(P) - 2, 3):
        d = P[i + 1] - P[i - 1]; d = d / np.linalg.norm(d)
        lat = np.array([-d[1], d[0], 0]); lat /= max(1e-6, np.linalg.norm(lat))
        pts = [P[i] + lat * (r + 7) * math.cos(a) + np.array([0, 0, zc + (r + 7) * math.sin(a)]) for a in np.radians(np.linspace(180, 360, 9))]
        pts = [P[i] + lat * -(r + 7) + [0, 0, lip]] + pts + [P[i] + lat * (r + 7) + [0, 0, lip]]
        tube(X.mesh(ir), pts, 2.2, nseg=5)
    bot = zc - r - 6
    for (x, y, z) in sup:
        zt = z + bot + 4
        for s in (-1, 1):
            tube(X.mesh(tw), [(x + s * 30, y, 0), (x + s * 14, y, zt)], 6, nseg=6)
        tube(X.mesh(tw), [(x - 26, y, zt * 0.45), (x + 26, y, zt * 0.45)], 3.5, nseg=6)
        boxm(X.mesh(tw), (x - r, y - 12, zt - 12), (x + r, y + 12, zt), r=1, tile=64)
    return save('log_flume', X)


def flume_gate():
    """little arch at the flume start: two posts, a cross beam with a hanging sign; faces -x, flume runs +x"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='fg'); rp = S('rope', 'lm', tag='fg')
    for s in (-1, 1):
        tube(X.mesh(wd), [(0, s * 74, 0), (0, s * 74, 150)], 7, nseg=8)
    tube(X.mesh(wd), [(0, -90, 146), (0, 90, 146)], 7, nseg=8)
    picture(X.mesh(S('wanted', 'lm', tag='fg')), (-8, 0, 118), 34, 42, (-1, 0, 0))
    return save('flume_gate', X)


# ================================================================================================= props
def cannon(name='cannon', length=110.0, r=11.0):
    """naval cannon on a wooden truck carriage, muzzle +x; origin floor centre (barrel axis z ~ 34)"""
    X = Model()
    ir = X.mesh(S('iron', 'lm', shade=60, tag='cn')); wd = X.mesh(S('wood_dark', 'lm', tag='cn')); rd = X.mesh(S('red', 'lm', tag='cn'))
    zc = 34
    m = Mesh()
    revolve(m, [(0, -40), (r * 0.6, -44), (r * 1.25, -36), (r * 1.3, -20), (r * 1.15, 10), (r * 0.95, length - 46), (r * 1.15, length - 44),
                (r * 1.1, length - 36), (r * 0.55, length - 36)], n=16, vlen=64)
    ir.add(m, rot_axis((0, 1, 0), math.pi / 2), (0, 0, zc))
    boxm(rd, (-46, -22, 10), (40, 22, 24), r=2, tile=64)
    for s in (-1, 1):
        boxm(rd, (-46, s * 22 - (5 if s > 0 else -5) - 2.5, 10), (6, s * 22 + 2.5, 34), r=1, tile=64)
    for x in (-34, 28):
        for s in (-1, 1):
            m2 = Mesh(); revolve(m2, [(0, -4), (10, -4), (10, 4), (0, 4)], n=12, vlen=32)
            wd.add(m2, rot_axis((1, 0, 0), math.pi / 2), (x, s * 26, 10))
    return save(name, X)


def barrel(name='barrel', h=58.0, r=22.0):
    X = Model()
    b = X.mesh(S('barrel', 'lm', shade=70, tag='br')); t = X.mesh(S('wood', 'lm', tag='brt'))
    prof = [(r * 0.86, 0), (r * 0.95, h * 0.2), (r, h * 0.5), (r * 0.95, h * 0.8), (r * 0.86, h)]
    revolve(b, prof, n=18, u_tiles=1, v_of=lambda rr, zz: 1 - zz / h)
    disc(t, r * 0.84, h - 1.5, up=True, n=18)
    revolve(t, [(r * 0.86, h), (r * 0.84, h - 1.5)], n=18, vlen=8)
    return save(name, X)


def barrel_lying(name='barrel_lying', h=58.0, r=22.0):
    X = Model()
    b = Mesh(); revolve(b, [(r * 0.86, -h / 2), (r * 0.95, -h * 0.3), (r, 0), (r * 0.95, h * 0.3), (r * 0.86, h / 2)], n=18, v_of=lambda rr, zz: 0.5 - zz / h)
    X.mesh(S('barrel', 'lm', shade=70, tag='bl')).add(b, rot_axis((0, 1, 0), math.pi / 2), (0, 0, r))
    for s in (-1, 1):
        d = Mesh(); disc(d, r * 0.85, 0, up=True, n=18)
        X.mesh(S('wood', 'lm', tag='blt')).add(d, rot_axis((0, 1, 0), s * math.pi / 2), (s * h / 2, 0, r))
    return save(name, X)


def big_barrel(name='big_barrel'):
    """the secret: a giant rum barrel lying on its side with the +x end knocked out, dark inside (r 42, 110 long);
    origin floor centre"""
    X = Model()
    R = 42.0; H = 110.0
    b = Mesh(); revolve(b, [(R * 0.88, -H / 2), (R * 0.96, -H * 0.3), (R, 0), (R * 0.96, H * 0.3), (R * 0.88, H / 2)], n=24, v_of=lambda rr, zz: 0.5 - zz / H)
    X.mesh(S('barrel', 'lm', shade=70, tag='bb')).add(b, rot_axis((0, 1, 0), math.pi / 2), (0, 0, R))
    bi = Mesh(); revolve(bi, [(R * 0.80, H / 2 - 2), (R * 0.86, 0), (R * 0.80, -H / 2 + 6)], n=24, vlen=64, inward=True)
    X.mesh(S('wood_dark', 'lm', tag='bbi')).add(bi, rot_axis((0, 1, 0), math.pi / 2), (0, 0, R))
    d = Mesh(); disc(d, R * 0.86, 0, up=True, n=24)
    X.mesh(S('wood', 'lm', tag='bbc')).add(d, rot_axis((0, 1, 0), -math.pi / 2), (-H / 2, 0, R))
    di = Mesh(); disc(di, R * 0.8, 0, up=True, n=24)
    X.mesh(S('black', 'lm', tag='bbc')).add(di, rot_axis((0, 1, 0), math.pi / 2), (-H / 2 + 6, 0, R))
    rim = Mesh(); revolve(rim, [(R * 0.80, 0), (R * 0.88, 0)], n=24, vlen=16)
    X.mesh(S('wood', 'lm', tag='bbr')).add(rim, rot_axis((0, 1, 0), math.pi / 2), (H / 2, 0, R))
    # a spilled puddle of rum in front of it and a few staves lying about
    disc(X.mesh(S('glass_b', 'lms', v=0.3, tag='rum')), 30, 0.6, up=True, n=16, cx=H / 2 + 26)
    for k, (x, y, a) in enumerate(((H / 2 + 50, 34, 0.4), (H / 2 + 30, -40, -0.7))):
        m = Mesh(); rbox(m, (-28, -5, 0), (28, 5, 3), r=1, tile=32)
        X.mesh(S('barrel', 'lm', tag='bbs')).add(m, rot_z(a), (x, y, 0))
    return save(name, X)


def crate(name='crate', s=48.0):
    X = Model()
    boxm(X.mesh(S('crate', 'lm', shade=30, tag=name)), (-s / 2, -s / 2, 0), (s / 2, s / 2, s), r=1.5, tile=s)
    return save(name, X)


def chest(name='chest', open_=True):
    """treasure chest (60 x 36 x 32), lid open with heaped gold, or shut with a padlock; faces -y; origin floor centre"""
    X = Model()
    ch = X.mesh(S('chest', 'lm', shade=40, tag='ch')); ir = X.mesh(S('iron', 'lm', tag='ch')); gd = X.mesh(S('coins', 'lms', v=0.25, tag='ch'))
    boxm(ch, (-30, -18, 0), (30, 18, 24), r=1.5, tile=64)
    if open_:
        m = Mesh(); rbox(m, (-30, 0, 0), (30, 36, 12), r=1.5, tile=64)
        ch.add(m, rot_axis((1, 0, 0), 1.4), (0, 18, 24))
        ellipsoid(gd, (0, 0, 22), 28, 16, 12, nu=14, nv=6, flat_bottom=0)
        for k in range(6):
            a = k * 1.1
            cylm(gd, (20 * math.cos(a), -22 + 6 * math.sin(a), 0), 4, 1.2, n=8)
    else:
        rv = Mesh(); revolve(rv, [(0, -30), (18, -30), (18, 30), (0, 30)], n=16, a0=90, a1=270, vlen=64)
        ch.add(rv, rot_axis((0, 1, 0), math.pi / 2), (0, 0, 24))
        boxm(ir, (-5, -20, 16), (5, -17, 28), r=1, tile=16)
    return save(name, X)


def cannonballs(name='cannonballs'):
    X = Model()
    ir = X.mesh(S('iron', 'lm', shade=70, tag='cb'))
    r = 7
    for layer, n in enumerate((4, 3, 2, 1)):
        for i in range(n):
            for j in range(n):
                sphere(ir, ((i - (n - 1) / 2) * 2 * r, (j - (n - 1) / 2) * 2 * r, r + layer * r * 1.41), r, nu=10, nv=6)
    return save(name, X)


def anchor_big(name='anchor_big'):
    """a giant anchor stuck in the sand (decor/cover), ~190 tall; origin floor centre"""
    X = Model()
    ir = X.mesh(S('iron', 'lm', shade=60, tag='an')); wd = X.mesh(S('wood_dark', 'lm', tag='an')); rp = X.mesh(S('rope', 'lm', tag='an'))
    tube(ir, [(0, 0, -10), (0, 0, 180)], [10, 9], nseg=10)
    arm = [(-70, 0, 40), (-50, 0, 12), (-20, 0, -4), (0, 0, -8), (20, 0, -4), (50, 0, 12), (70, 0, 40)]
    tube(ir, arm, 9, nseg=10)
    for s in (-1, 1):
        tube(ir, [(s * 70, 0, 40), (s * 80, 0, 60)], [12, 1], nseg=8)
    tube(wd, [(-50, 0, 150), (50, 0, 150)], 7, nseg=8)
    torus(ir, (0, 0, 196), 14, 4, axis=(0, 1, 0), n=16, m=6)
    tube(rp, [(0, 0, 210), (20, 30, 180), (40, 60, 40), (60, 70, 3), (120, 60, 3)], 4, nseg=6)
    return save(name, X)


def rope_coil(name='rope_coil'):
    X = Model()
    rp = X.mesh(S('rope', 'lm', shade=70, tag='rc'))
    pts = []
    for t in np.linspace(0, 6 * math.pi, 120):
        r = 18 - t * 0.4
        pts.append((r * math.cos(t), r * math.sin(t), 3 + (t > 4 * math.pi) * 4))
    tube(rp, pts, 3, nseg=6)
    return save(name, X)


def rowboat(name='rowboat'):
    """small rowboat with two thwarts and oars, beached (flat bottom on z 0), bow +x; ~160 long"""
    X = Model()
    sh = S('wood_light', 'lm', shade=60, tag='rb'); ins = S('wood', 'lm', shade=60, tag='rbi'); wd = S('wood_dark', 'lm', tag='rb')
    xs = np.linspace(-80, 80, 17)
    zs = [0, 10, 22, 34, 40]
    def hw(x, z):
        f = math.sqrt(max(0.0, 1 - (x / 82) ** 2)) if x > 0 else math.sqrt(max(0.0, 1 - (x / 96) ** 2 * 0.9))
        return (18 + 18 * (z / 40) ** 0.6) * f
    for s in (-1, 1):
        P = np.array([[[x, s * hw(x, z), z] for x in xs] for z in zs], float)
        UV = np.array([[[x / 64, z / 64] for x in xs] for z in zs], float)
        N = grid_normals(P)
        if (N[2, 8, 1] * s) < 0: N = -N
        X.mesh(sh).grid(P, N, UV)
        Pi = P.copy(); Pi[..., 1] -= s * 3
        Ni = -N
        X.mesh(ins).grid(Pi, Ni, UV)
    boxm(X.mesh(ins), (-70, -16, 4), (70, 16, 6), r=0.5, tile=64)
    for x in (-30, 25):
        boxm(X.mesh(wd), (x - 7, -hw(x, 30) + 3, 26), (x + 7, hw(x, 30) - 3, 29), r=0.5, tile=32)
    for s in (-1, 1):
        tube(X.mesh(wd), [(-40, s * 22, 36), (60, s * 46, 4)], 2.5, nseg=6)
        boxm(X.mesh(wd), (52, s * 44 - 7, 0), (82, s * 44 + 7, 4), r=1, tile=32)
    return save(name, X)


def life_ring(name='life_ring'):
    X = Model()
    torus(X.mesh(S('canvas_rw', 'lm', shade=70, tag='lr')), (0, 0, 22), 18, 6, axis=(0, 1, 0), n=20, m=8, utile=8)
    tube(X.mesh(S('wood_dark', 'lm', tag='lr')), [(0, 6, 0), (0, 6, 44)], 3, nseg=6)
    return save(name, X)


def palm(name, h, lean=(0.25, 0.0), nf=11, seed=1):
    X = Model()
    tr = X.mesh(S('palm_trunk', 'lm', shade=70)); fr = X.mesh(S('frond', 'alpha', vs=1.1)); co = X.mesh(S('coconut', 'lm'))
    rng = np.random.default_rng(seed)
    lx, ly = lean
    P = [np.array([lx * h * (t ** 1.6), ly * h * (t ** 1.6), h * t]) for t in np.linspace(0, 1, 12)]
    tube(tr, P, np.linspace(13, 8, 12), nseg=10, vlen=64)
    top = P[-1]
    for k in range(nf):
        a = 2 * math.pi * k / nf + rng.uniform(-0.2, 0.2)
        d = np.array([math.cos(a), math.sin(a), 0])
        leaf_quads(fr, top + d * 4, d, h * rng.uniform(0.42, 0.55), 52, droop=rng.uniform(0.55, 0.85), segs=6)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        sphere(co, top + [8 * math.cos(a), 8 * math.sin(a), -10], 6, nu=8, nv=5)
    return save(name, X)


def parasol(name='parasol', h=150.0, r=96.0, cv='canvas_rw'):
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='pa')); th = X.mesh(S(cv, 'lm', shade=60, tag='pa'))
    cylm(wd, (0, 0, 0), 3.5, h + 30, n=8)
    revolve(th, [(0, h + 40), (r * 0.5, h + 22), (r, h)], n=16, u_tiles=8, vlen=64)
    revolve(th, [(r, h), (r * 0.5, h + 22), (0, h + 40)], n=16, u_tiles=8, vlen=64)
    return save(name, X)


def lounger(name='lounger', cv='canvas_rw'):
    X = Model()
    wd = X.mesh(S('wood_light', 'lm', tag='lo')); cu = X.mesh(S(cv, 'lm', tag='lo'))
    for x in (-30, 30):
        for y in (-12, 12):
            cylm(wd, (x, y, 0), 2, 10, n=6)
    boxm(wd, (-34, -14, 10), (34, 14, 13), r=1, tile=64)
    boxm(cu, (-32, -13, 13), (14, 13, 16), r=1.5, tile=64)
    P = [np.array(p, float) for p in ((14, -13, 14), (14, 13, 14), (34, 13, 34), (34, -13, 34))]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    if nn[2] < 0: nn = -nn
    cu.poly(P, nn, [(0, 0), (0.4, 0), (0.4, 0.3), (0, 0.3)])
    cu.poly(P[::-1], -nn, [(0, 0.3), (0.4, 0.3), (0.4, 0), (0, 0)])
    return save(name, X)


def boulder(name, r=60.0, seed=7, tex='moss_rock'):
    X = Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    bump = lambda p, t: 1 + 0.12 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]) + 0.08 * math.sin(5 * t + ph[2])
    ellipsoid(X.mesh(S(tex, 'lm', shade=70)), (0, 0, r * 0.45), r, r * 0.8, r * 0.6, nu=18, nv=10, bump=bump, flat_bottom=-r * 0.45)
    return save(name, X)


def torch_post(name='torch_post', h=130.0):
    """pirate torch: a tarred pole with an iron basket and fire; origin base"""
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='tp')); ir = X.mesh(S('iron', 'lm', tag='tp'))
    fl = X.mesh(S('flame', 'add', wave='wave sin 0.85 0.15 0 2.3'))
    tube(wd, [(0, 0, 0), (0, 0, h)], [5, 4], nseg=8)
    revolve(ir, [(4, h - 4), (12, h + 4), (14, h + 18), (13, h + 20)], n=10, vlen=32)
    for k in range(2):
        a = k * math.pi / 2
        d = np.array([math.cos(a), math.sin(a), 0]) * 12
        quad_uv(fl, np.array([0, 0, h + 8]) - d, np.array([0, 0, h + 8]) + d, np.array([0, 0, h + 56]) + d, np.array([0, 0, h + 56]) - d,
                [(0, 1), (1, 1), (1, 0), (0, 0)], np.cross(d, [0, 0, 1.0]) / 12)
    return save(name, X)


def lantern_post(name='lantern_post', h=150.0):
    """harbour lamp post: wooden post, iron arm, a glowing ship's lantern; origin base"""
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='lp')); ir = X.mesh(S('iron', 'lm', tag='lp')); gl = X.mesh(S('lantern', 'glow', tag='lp'))
    boxm(wd, (-5, -5, 0), (5, 5, h), r=1, tile=64)
    tube(ir, [(0, 0, h - 10), (30, 0, h + 4), (34, 0, h - 6)], 2, nseg=5)
    revolve(gl, [(0, h - 34), (8, h - 30), (10, h - 18), (8, h - 8), (0, h - 6)], n=10, cx=34, vlen=16)
    revolve(ir, [(0, h - 6), (11, h - 8), (2, h + 2), (0, h + 4)], n=8, cx=34, vlen=16)
    return save(name, X)


def ship_wheel(name='ship_wheel'):
    """ship's wheel on its pedestal (spokes in the y-z plane, faces -x) + binnacle; origin floor centre"""
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='sw')); br = X.mesh(S('bronze', 'lms', v=0.2, tag='sw'))
    boxm(wd, (-8, -12, 0), (8, 12, 46), r=2, tile=32)
    c = np.array([-12, 0, 66])
    torus(wd, c, 26, 2.5, axis=(1, 0, 0), n=24, m=6)
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = np.array([0, math.cos(a), math.sin(a)])
        tube(wd, [c + d * 4, c + d * 36], [2.2, 1.6], nseg=5)
    tube(br, [c + [-4, 0, 0], c + [6, 0, 0]], 6, nseg=10)
    revolve(br, [(0, 0), (10, 0), (8, 36), (14, 40), (12, 50), (0, 52)], n=12, cx=-60, vlen=32)
    return save(name, X)


def capstan(name='capstan'):
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='cp')); ir = X.mesh(S('iron', 'lm', tag='cp'))
    revolve(wd, [(0, 0), (24, 0), (16, 10), (14, 34), (22, 40), (22, 48), (0, 50)], n=12, vlen=32)
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(wd, [(14 * math.cos(a), 14 * math.sin(a), 44), (56 * math.cos(a), 56 * math.sin(a), 44)], 2.5, nseg=5)
    return save(name, X)


def stall(name, cv, goods):
    """market stall: counter with goods, four posts and a striped canopy (w 160, d 80); faces -x; origin floor centre"""
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='stl')); cvm = X.mesh(S(cv, 'lm', tag='stl' + cv, two=True))
    boxm(wd, (-40, -80, 0), (40, 80, 50), r=1, tile=64)
    boxm(X.mesh(S(goods, 'lm', tag='stl' + goods)), (-36, -76, 50), (36, 76, 56), r=1, tile=128)
    for (x, y) in ((-40, -80), (40, -80), (-40, 80), (40, 80)):
        cylm(wd, (x, y, 0), 3, 150 if x > 0 else 132, n=6)
    P = [np.array([44, -90, 150.0]), np.array([44, 90, 150.0]), np.array([-60, 90, 128.0]), np.array([-60, -90, 128.0])]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    if nn[2] < 0: nn = -nn
    cvm.poly(P, nn, [(0, 0), (4, 0), (4, 1), (0, 1)])
    return save(name, X)


def signpost(name='signpost'):
    """wooden signpost with three arrow boards"""
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='sgp'))
    tube(wd, [(0, 0, 0), (0, 0, 150)], [4, 3.5], nseg=8)
    for k, (z, a) in enumerate(((132, 20), (112, 160), (92, -70))):
        aa = math.radians(a)
        d = np.array([math.cos(aa), math.sin(aa), 0]); n = np.array([-d[1], d[0], 0])
        m = Mesh(); rbox(m, (0, -2, -7), (60, 2, 7), r=0.5, tile=32)
        X.mesh(S('wood_light', 'lm', tag='sgp')).add(m, np.stack([d, n, [0, 0, 1.0]], 1), (0, 0, z))
    return save(name, X)


def wreck_mast(name='wreck_mast'):
    """the broken mast of a sunken ship sticking out of the lagoon: tilted spar, a yard, a smashed crow's nest, tattered
    flag; origin at the lagoon floor, ~420 tall"""
    X = Model()
    sp = X.mesh(S('wood_dark', 'lm', shade=70, tag='wm')); fl = X.mesh(S('jolly', 'flag', div=40, amp=6, freq=0.7, tag='wm'))
    tube(sp, [(0, 0, 0), (12, 4, 200), (26, 8, 420)], [14, 12, 9], nseg=10)
    tube(sp, [(20, -110, 330), (24, 6, 334), (18, 120, 340)], [5, 6, 5], nseg=8)
    ring(sp, (24, 7), 30, 38, 290, 310, n=16)
    P = [np.array([26, 8, 412]), np.array([26 - 100, 8, 400]), np.array([26 - 96, 8, 340]), np.array([26, 8, 350])]
    fl.poly(P, (0, -1, 0), [(1, 0), (0, 0.1), (0.05, 1), (1, 0.9)])
    fl.poly(P[::-1], (0, 1, 0), [(1, 0.9), (0.05, 1), (0, 0.1), (1, 0)])
    return save(name, X)


def captain_statue(name='captain_statue'):
    """bronze statue of a cartoon pirate captain on a stone plinth: tricorn, coat, peg leg, hook, telescope, a parrot
    on the shoulder; origin floor centre, faces -y; ~330 tall"""
    X = Model()
    br = X.mesh(S('bronze', 'lms', v=0.22, tag='cs')); st = X.mesh(SB('fort_stone', 30, tag='cs')); gd = X.mesh(S('gold', 'lms', v=0.3, tag='cs'))
    boxm(st, (-60, -60, 0), (60, 60, 90), r=2, tile=128)
    boxm(st, (-68, -68, 82), (68, 68, 96), r=2, tile=128)
    z0 = 96
    tube(br, [(-14, 0, z0), (-14, 0, z0 + 70)], [9, 10], nseg=10)                                   # leg
    tube(br, [(14, 0, z0), (14, 0, z0 + 70)], [4, 6], nseg=8)                                       # peg leg
    ellipsoid(br, (0, 0, z0 + 112), 38, 28, 52, nu=16, nv=10)                                       # coat / body
    revolve(br, [(40, z0 + 64), (34, z0 + 90), (0, z0 + 92)], n=16, vlen=64)                          # coat tails
    sphere(br, (0, -4, z0 + 186), 26, nu=16, nv=10)                                                 # head
    ellipsoid(br, (0, -22, z0 + 168), 18, 10, 16, nu=12, nv=6)                                      # beard
    revolve(br, [(52, z0 + 204), (44, z0 + 210), (24, z0 + 214), (22, z0 + 240), (0, z0 + 244)], n=3, a0=-30, a1=330, vlen=64)  # tricorn
    tube(br, [(-34, 0, z0 + 140), (-56, -26, z0 + 112), (-60, -50, z0 + 130)], 8, nseg=8)            # arm with telescope
    tube(gd, [(-60, -50, z0 + 130), (-62, -100, z0 + 150)], [6, 4], nseg=8)
    tube(br, [(34, 0, z0 + 140), (52, -10, z0 + 110)], 8, nseg=8)
    tube(gd, [(52, -10, z0 + 110), (60, -22, z0 + 100), (54, -30, z0 + 108)], 2.5, nseg=6)          # hook
    ellipsoid(br, (30, 4, z0 + 168), 9, 8, 14, nu=10, nv=6)                                         # parrot
    sphere(br, (30, 0, z0 + 186), 7, nu=10, nv=6)
    return save(name, X)


def parrot_perch(name='parrot_perch'):
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='pp')); pr = X.mesh(S('parrot', 'vl', tag='pp'))
    tube(wd, [(0, 0, 0), (0, 0, 120)], 3, nseg=6)
    tube(wd, [(-24, 0, 120), (24, 0, 120)], 2.5, nseg=6)
    ellipsoid(pr, (0, 0, 134), 7, 6, 13, nu=10, nv=6)
    sphere(pr, (0, -2, 150), 6, nu=10, nv=6)
    tube(pr, [(0, 4, 126), (0, 14, 104)], [4, 1], nseg=5)
    return save(name, X)


def hammock(name='hammock'):
    """a hammock slung between two posts (posts at x +-110); origin floor centre"""
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='hm')); cv = X.mesh(S('canvas_gy', 'lm', tag='hm', two=True)); rp = X.mesh(S('rope', 'lm', tag='hm'))
    for s in (-1, 1):
        tube(wd, [(s * 110, 0, 0), (s * 110, 0, 110)], 5, nseg=8)
        tube(rp, [(s * 110, 0, 96), (s * 70, 0, 64)], 1.2, nseg=4)
    xs = np.linspace(-70, 70, 12); ys = np.linspace(-26, 26, 5)
    P = np.array([[[x, y, 64 - 26 * (1 - (x / 70) ** 2) + 10 * (y / 26) ** 2] for x in xs] for y in ys], float)
    UV = np.array([[[x / 64, y / 64] for x in xs] for y in ys])
    N = grid_normals(P)
    if N[2, 6, 2] < 0: N = -N
    cv.grid(P, N, UV)
    return save(name, X)


def skeleton_throne(name='skeleton_throne'):
    """Captain Padbeard himself: a skeleton in a tricorn slumped on a gilded throne (faces -y); origin floor centre"""
    X = Model()
    gd = X.mesh(S('gold', 'lms', v=0.3, tag='st')); bn = X.mesh(S('bone', 'lm', tag='st')); rd = X.mesh(S('red', 'lm', tag='st')); ft = X.mesh(S('felt', 'lm', tag='st'))
    boxm(gd, (-44, -40, 0), (44, 40, 40), r=3, tile=64)
    boxm(rd, (-36, -36, 40), (36, 34, 48), r=3, tile=64)
    boxm(gd, (-44, 26, 40), (44, 40, 180), r=4, tile=64)
    for s in (-1, 1):
        boxm(gd, (min(s * 44, s * 36), -36, 40), (max(s * 44, s * 36), 26, 80), r=2, tile=64)
    # ribcage, spine, skull, limbs
    for k in range(5):
        torus(bn, (0, 4, 80 + k * 10), 14 - k, 1.6, axis=(0, 0, 1), n=14, m=4)
    tube(bn, [(0, 14, 48), (0, 16, 130)], 2.5, nseg=6)
    sphere(bn, (0, 6, 146), 14, nu=12, nv=8)
    for s in (-1, 1):
        sphere(X.mesh(S('black', 'lm', tag='st')), (s * 5, -6, 148), 3.5, nu=6, nv=4)
        tube(bn, [(s * 16, 8, 122), (s * 34, -4, 90), (s * 38, -24, 82)], 2.2, nseg=5)
        tube(bn, [(s * 10, 0, 50), (s * 12, -40, 52), (s * 12, -44, 4)], 2.5, nseg=5)
    revolve(ft, [(30, 158), (24, 162), (14, 164), (13, 178), (0, 180)], n=3, a0=-30, a1=330, vlen=64)
    return save(name, X)


def gold_heap(name='gold_heap', r=80.0, seed=13):
    X = Model()
    gd = X.mesh(S('coins', 'lms', v=0.3, tag='gh')); gm = X.mesh(S('gold', 'lms', v=0.3, tag='gh'))
    rng = np.random.default_rng(seed)
    ellipsoid(gd, (0, 0, 0), r, r * 0.8, r * 0.45, nu=18, nv=8, flat_bottom=0)
    for k in range(10):
        a = rng.uniform(0, 6.28); d = rng.uniform(0.2, 0.8) * r
        z = r * 0.45 * math.sqrt(max(0, 1 - (d / r) ** 2))
        cylm(gm, (d * math.cos(a), d * math.sin(a) * 0.8, z - 3), rng.uniform(5, 10), 3, n=10)
    return save(name, X)


def shark_ring():
    """three sharks circling (radius SHARK_R round the func_rotating origin, z 0 = origin height), facing CCW"""
    X = Model()
    sh = S('shark', 'dyn', tag='sk'); wt = S('white', 'dyn', tag='sk'); bk = S('black', 'dyn', tag='sk')
    for k in range(3):
        a0 = 2 * math.pi * k / 3
        R = L.SHARK_R + (k - 1) * 40
        # body along the circle: spine points from tail (behind, clockwise) to snout
        pts = []; rads = []
        for i in range(12):
            t = i / 11
            a = a0 - 0.55 * (1 - t)
            pts.append(np.array([R * math.cos(a), R * math.sin(a), 8 * math.sin(t * 6)]))
            rads.append(4 + 22 * math.sin(min(1, t * 1.15) * math.pi) ** 0.7)
        tube(X.mesh(sh), pts, rads, nseg=12, vlen=128, ry=[r_ * 0.8 for r_ in rads])
        hd = pts[-1]; d = pts[-1] - pts[-2]; d /= np.linalg.norm(d)
        up = np.array([0, 0, 1.0]); side = np.cross(d, up)
        mid = pts[6]
        # dorsal fin, pectoral fins, tail fin
        quad_uv(X.mesh(sh), mid + up * 18 - d * 10, mid + up * 18 + d * 26, mid + up * 56 - d * 14, mid + up * 54 - d * 20, [(0, 0), (1, 0), (1, 1), (0, 1)], side)
        quad_uv(X.mesh(sh), mid + up * 54 - d * 20, mid + up * 56 - d * 14, mid + up * 18 + d * 26, mid + up * 18 - d * 10, [(0, 1), (1, 1), (1, 0), (0, 0)], -side)
        for s in (-1, 1):
            p = pts[7] - up * 6 + side * s * 16
            quad_uv(X.mesh(sh), p, p + d * 22, p + side * s * 36 - d * 12 - up * 8, p + side * s * 30 - d * 22 - up * 6, [(0, 0), (1, 0), (1, 1), (0, 1)], -up if s > 0 else -up)
        tl = pts[0]
        for (dz, sg) in ((40, 1), (-28, -1)):
            quad_uv(X.mesh(sh), tl, tl - d * 6, tl - d * 36 + up * dz, tl - d * 20 + up * dz * 0.9, [(0, 0), (1, 0), (1, 1), (0, 1)], side)
            quad_uv(X.mesh(sh), tl - d * 20 + up * dz * 0.9, tl - d * 36 + up * dz, tl - d * 6, tl, [(0, 1), (1, 1), (1, 0), (0, 0)], -side)
        for s in (-1, 1):
            sphere(X.mesh(bk), hd - d * 10 + side * s * 13 + up * 6, 3, nu=6, nv=4)
    return save_iqm('sharks', X)


def gull_ring():
    """five seagulls gliding round the bay (radius GULL_R), wings spread"""
    X = Model()
    g = S('gull', 'dyn', tag='gl')
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        R = L.GULL_R + (k % 3 - 1) * 260
        c = np.array([R * math.cos(a), R * math.sin(a), (k % 2) * 140 - 60])
        d = np.array([-math.sin(a), math.cos(a), 0]); side = np.array([math.cos(a), math.sin(a), 0]); up = np.array([0, 0, 1.0])
        ellipsoid(X.mesh(g), c, 8, 8, 8, nu=8, nv=5, R=np.stack([side, d, up], 1) @ np.diag([1, 2.4, 1]))
        for s in (-1, 1):
            w0 = c + side * s * 6; w1 = c + side * s * 46 + up * 12; w2 = c + side * s * 84 - d * 10 + up * 2
            quad_uv(X.mesh(g), w0 - d * 8, w0 + d * 8, w1 + d * 4, w1 - d * 12, [(0, 0), (0.5, 0), (0.5, 1), (0, 1)], up)
            quad_uv(X.mesh(g), w1 - d * 12, w1 + d * 4, w0 + d * 8, w0 - d * 8, [(0, 1), (0.5, 1), (0.5, 0), (0, 0)], -up)
            quad_uv(X.mesh(g), w1 - d * 12, w1 + d * 4, w2 + d * 2, w2 - d * 6, [(0.5, 0), (1, 0), (1, 1), (0.5, 1)], up)
            quad_uv(X.mesh(g), w2 - d * 6, w2 + d * 2, w1 + d * 4, w1 - d * 12, [(0.5, 1), (1, 1), (1, 0), (0.5, 0)], -up)
    return save_iqm('gulls', X)


def bottles(name='bottles'):
    """a row of rum bottles for the bar shelves (length 120 along y)"""
    X = Model()
    for k in range(7):
        y = -54 + k * 18
        sh = S('glass_g' if k % 2 else 'glass_b', 'lms', v=0.25, tag='bt')
        revolve(X.mesh(sh), [(0, 0), (6, 0), (6, 18), (3, 24), (2, 32), (0, 32)], n=10, cy=y, vlen=32)
    return save(name, X)


def table(name='table'):
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='tb'))
    cylm(wd, (0, 0, 32), 30, 4, n=16)
    tube(wd, [(0, 0, 0), (0, 0, 32)], 4, nseg=8)
    cylm(wd, (0, 0, 0), 14, 3, n=10)
    return save(name, X)


def stool(name='stool'):
    X = Model()
    wd = X.mesh(S('wood_dark', 'lm', tag='so'))
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(wd, [(10 * math.cos(a), 10 * math.sin(a), 0), (5 * math.cos(a), 5 * math.sin(a), 22)], 1.8, nseg=5)
    cylm(wd, (0, 0, 22), 10, 3, n=12)
    return save(name, X)


def mortar():
    """the cannon launcher on the fort's east rampart: a squat bronze mortar ring round the pad with an opening west
    (players walk in); origin floor centre"""
    X = Model()
    br = S('bronze', 'lms', v=0.22, tag='mo'); ir = S('iron', 'lm', tag='mo'); wd = S('wood_dark', 'lm', tag='mo')
    n = 24
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        am = (a0 + a1) / 2
        if abs(((am - 180) + 180) % 360 - 180) < 40: continue        # opening to the west
        m = Mesh()
        revolve(m, [(36, 0), (44, 0), (47, 20), (43, 40), (35, 40), (36, 0)], n=1, a0=a0, a1=a1, vlen=64)
        X.mesh(br).add(m)
    return save('mortar', X)


def make():
    make_textures()
    skull_rock(); fort(); dive_tower(); tavern(); shop()
    for i, r in enumerate(L.SHACKS):
        shack(f'shack_{i}', r, 'e')
    cannon_tube(L.tube_path(), SUPPORTS['tube']); tube_mouth(); log_flume(L.flume_path(), SUPPORTS['flume']); flume_gate()
    cannon(); barrel(); barrel_lying(); big_barrel(); crate('crate', 48); crate('crate_big', 72); chest('chest_open', True); chest('chest_shut', False)
    cannonballs(); anchor_big(); rope_coil(); rowboat(); life_ring()
    palm('palm_a', 300, (0.22, 0.05), 11, 1); palm('palm_b', 380, (-0.05, 0.25), 12, 2); palm('palm_c', 240, (0.15, -0.18), 10, 3)
    parasol('parasol_r', cv='canvas_rw'); parasol('parasol_b', cv='canvas_bw'); lounger('lounger_r', 'canvas_rw'); lounger('lounger_b', 'canvas_bw')
    boulder('boulder_a', 60, 7); boulder('boulder_b', 90, 8); boulder('boulder_c', 130, 9)
    torch_post(); lantern_post(); ship_wheel(); capstan(); signpost(); wreck_mast(); captain_statue(); parrot_perch(); hammock()
    stall('stall_fruit', 'canvas_gy', 'fruit'); stall('stall_fish', 'canvas_bw', 'fish'); stall('stall_rum', 'canvas_rw', 'barrel')
    skeleton_throne(); gold_heap('gold_heap', 80, 13); gold_heap('gold_heap_s', 50, 14)
    bottles(); table(); stool(); mortar()
    shark_ring(); gull_ring()


SUPPORTS = {'tube': [], 'flume': []}
