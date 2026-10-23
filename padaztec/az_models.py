"""Custom MD3/IQM map objects for wop_padaztec (Tlaloc's Lagoon). All geometry and art is original and generated here.
    make() -> writes models/padaztec/*.md3/*.iqm and their images (shaders are registered in azlib.REG)

Scale ~32u per metre. Architecture (pyramid, shrine, jaguar temple, ball court, eagle hall, cantina) is built in place
from the convex solids in az_shapes.py, so the weapclip collision in build_aztec.py matches the visible surfaces exactly;
props have their origin at the floor centre.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube as _tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from azlib import *
import azlib
import layout as L
import az_shapes as SH

TXD = 'textures/padaztec/'


def BT(name):
    """brush texture image (textures/padaztec/<name>) for use in a model shader"""
    return TXD + name


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
    right = np.cross(up, nrm); right /= np.linalg.norm(right); right = -right
    upv = np.cross(nrm, right)
    p = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2, c - right * w / 2 + upv * h / 2]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


def double_picture(M, c, w, h, nrm):
    picture(M, c, w, h, nrm); picture(M, c, w, h, -np.asarray(nrm, float))


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


def leaf_quads(M, base, d, length, width, droop=0.4, segs=5, twist=0.0):
    """a bent leaf/frond strip from base along direction d (xy), drooping; uv u across, v along"""
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


# ================================================================================================= textures (models)
def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((70, 110, 120)), C((220, 236, 240)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_tablero(kind, w=512, h=128, seed=1):
    """painted talud-tablero frieze panel: Tlaloc goggle masks or feathered serpent heads on a red ground with a
    raised frame (the frame is part of the image)"""
    im = Image.new('RGB', (w, h), (150, 60, 44)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 12), fill=(200, 186, 150)); d.rectangle((0, h - 12, w, h), fill=(200, 186, 150))
    d.rectangle((0, 12, w, 16), fill=(60, 40, 30)); d.rectangle((0, h - 16, w, h - 12), fill=(60, 40, 30))
    for k in range(2):
        cx = w * (0.25 + 0.5 * k); cy = h / 2
        if kind == 'tlaloc':
            for s in (-1, 1):
                d.ellipse((cx + s * 34 - 24, cy - 24, cx + s * 34 + 24, cy + 24), fill=(60, 150, 190), outline=(240, 240, 230), width=5)
                d.ellipse((cx + s * 34 - 9, cy - 9, cx + s * 34 + 9, cy + 9), fill=(20, 20, 24))
            d.arc((cx - 40, cy + 2, cx + 40, cy + 44), 200, 340, fill=(240, 240, 230), width=6)
            for s in (-1, 1): d.polygon([(cx + s * 14, cy + 22), (cx + s * 22, cy + 46), (cx + s * 6, cy + 30)], fill=(250, 250, 240))
            for i in range(5): d.rectangle((cx - 60 + i * 26, 18, cx - 50 + i * 26, 28), fill=(60, 150, 190))
        else:
            d.ellipse((cx - 70, cy - 34, cx + 40, cy + 34), fill=(70, 140, 90), outline=(20, 40, 30), width=4)
            d.polygon([(cx + 30, cy - 26), (cx + 96, cy - 8), (cx + 90, cy + 4), (cx + 30, cy + 14)], fill=(70, 140, 90), outline=(20, 40, 30))
            d.ellipse((cx - 20, cy - 22, cx + 2, cy), fill=(240, 220, 120)); d.ellipse((cx - 13, cy - 15, cx - 5, cy - 7), fill=(20, 20, 20))
            for i in range(4): d.polygon([(cx + 40 + i * 12, cy + 4), (cx + 46 + i * 12, cy + 22), (cx + 52 + i * 12, cy + 4)], fill=(250, 250, 240))
            for i in range(7):
                a = math.radians(110 + i * 20)
                d.ellipse((cx - 70 + 52 * math.cos(a) - 9, cy + 46 * math.sin(a) - 14, cx - 70 + 52 * math.cos(a) + 9, cy + 46 * math.sin(a) + 14),
                          fill=(60, 160, 120), outline=(20, 50, 30), width=2)
        # shells between the heads
        sx = cx + w * 0.25
        d.ellipse((sx - 16, cy - 20, sx + 16, cy + 20), fill=(236, 224, 190), outline=(90, 70, 50), width=3)
        d.line([(sx, cy - 16), (sx, cy + 16)], fill=(90, 70, 50), width=2)
    return np.asarray(im, np.float32) + N3(w, 1, seed, 6, h) + N3(w, 10, seed + 1, 8, h)


def tex_shrine(w=256, h=512, seed=3):
    """Tlaloc's shrine wall: white stucco with blue vertical bands above a red base course"""
    x, y = xy(w, h)
    c = fill(w, (236, 232, 222), 4, seed, h)
    band = ((x * 4) % 1.0) < 0.5
    c = np.where((band & (y < 0.62))[..., None], fill(w, (70, 140, 200), 4, seed + 1, h), c)
    c = np.where((y > 0.66)[..., None], fill(w, (150, 60, 44), 4, seed + 2, h), c)
    c = np.where(((y > 0.62) & (y < 0.66))[..., None], C((30, 28, 26)), c)
    return c + N3(w, 6, seed + 3, 5, h)


def tex_scales(w=256, h=256, seed=5, base=(54, 140, 90), hi=(120, 200, 120)):
    """overlapping serpent scales (feathered serpent skin)"""
    x, y = xy(w, h)
    k = 8
    u = x * k; v = y * k
    row = np.floor(v)
    uu = u + (row % 2) * 0.5
    fu = (uu % 1.0) - 0.5; fv = (v % 1.0)
    dd = np.hypot(fu, fv * 0.9)
    c = lerp(C(base), C(hi), np.clip(1 - dd * 1.6, 0, 1)[..., None])
    edge = np.abs(dd - 0.52) < 0.05
    c = np.where(edge[..., None], C((20, 50, 34)), c)
    return c + N3(w, 1, seed, 6, h)


def tex_feather(w=128, h=256, seed=7, col=(30, 150, 100), tip=(240, 200, 60)):
    """single quetzal feather on transparent (alpha)"""
    x, y = xy(w, h)
    cx = 0.5
    width = 0.42 * np.clip(np.sin(np.clip(1 - y, 0, 1) * math.pi), 0, 1) ** 0.6
    a = (np.abs(x - cx) < width).astype(np.float32)
    barb = np.sin((y * 60 + np.abs(x - cx) * 30)) * 0.5 + 0.5
    c = lerp(C(col), C(tip), np.clip((0.25 - y) * 5, 0, 1)[..., None]) * (0.75 + 0.25 * barb)[..., None]
    c = np.where((np.abs(x - cx) < 0.02)[..., None], C((230, 230, 200)), c)
    return c, a * 255


def tex_sunstone(n=1024, seed=9):
    """the Sun Stone: central face, four movement squares, ring of 20 day-sign cells, rays, two fire serpents"""
    im = Image.new('RGB', (n, n), (40, 34, 30)); d = ImageDraw.Draw(im)
    c = n / 2
    stone = (176, 160, 132); line = (70, 58, 46); paint = [(150, 60, 44), (60, 140, 160), (200, 160, 70)]
    d.ellipse((4, 4, n - 4, n - 4), fill=stone, outline=line, width=6)
    def ring(r, w=5): d.ellipse((c - r, c - r, c + r, c + r), outline=line, width=w)
    for r in (500, 470, 400, 330, 260, 200, 150, 90): ring(r)
    # fire serpents (outer band): scaled bodies
    for k in range(48):
        a = 2 * math.pi * k / 48
        x0, y0 = c + 485 * math.cos(a), c + 485 * math.sin(a)
        d.ellipse((x0 - 10, y0 - 10, x0 + 10, y0 + 10), fill=paint[0] if k % 2 else stone, outline=line, width=2)
    # rays (8 big points) between 400 and 470
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        pts = [(c + 400 * math.cos(a - 0.12), c + 400 * math.sin(a - 0.12)), (c + 468 * math.cos(a), c + 468 * math.sin(a)),
               (c + 400 * math.cos(a + 0.12), c + 400 * math.sin(a + 0.12))]
        d.polygon(pts, fill=paint[2], outline=line)
    # 20 day-sign cells between 260 and 330
    r = np.random.default_rng(seed)
    for k in range(20):
        a = 2 * math.pi * k / 20
        x0, y0 = c + 295 * math.cos(a), c + 295 * math.sin(a)
        d.rectangle((x0 - 24, y0 - 24, x0 + 24, y0 + 24), outline=line, width=3)
        kind = k % 5
        if kind == 0: d.ellipse((x0 - 12, y0 - 12, x0 + 12, y0 + 12), outline=line, width=3)
        elif kind == 1: d.polygon([(x0 - 14, y0 + 12), (x0, y0 - 14), (x0 + 14, y0 + 12)], outline=line)
        elif kind == 2: d.line([(x0 - 14, y0), (x0 + 14, y0)], fill=line, width=4); d.line([(x0, y0 - 14), (x0, y0 + 14)], fill=line, width=4)
        elif kind == 3: d.arc((x0 - 14, y0 - 14, x0 + 14, y0 + 14), 0, 270, fill=line, width=4)
        else: d.rectangle((x0 - 8, y0 - 8, x0 + 8, y0 + 8), fill=paint[1])
    # small dots ring 200..260
    for k in range(40):
        a = 2 * math.pi * k / 40
        x0, y0 = c + 230 * math.cos(a), c + 230 * math.sin(a)
        d.ellipse((x0 - 6, y0 - 6, x0 + 6, y0 + 6), fill=line)
    # four movement squares (ollin) round the face
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        x0, y0 = c + 175 * math.cos(a), c + 175 * math.sin(a)
        d.rectangle((x0 - 46, y0 - 46, x0 + 46, y0 + 46), fill=paint[k % 3], outline=line, width=4)
        d.ellipse((x0 - 18, y0 - 18, x0 + 18, y0 + 18), outline=line, width=4)
    # central face: eyes, nose, tongue (flint knife)
    d.ellipse((c - 88, c - 88, c + 88, c + 88), fill=(196, 160, 110), outline=line, width=5)
    for s in (-1, 1):
        d.ellipse((c + s * 34 - 16, c - 40, c + s * 34 + 16, c - 16), fill=(240, 240, 230), outline=line, width=3)
        d.ellipse((c + s * 34 - 6, c - 34, c + s * 34 + 6, c - 22), fill=line)
    d.polygon([(c - 10, c - 14), (c + 10, c - 14), (c + 14, c + 14), (c - 14, c + 14)], fill=(176, 140, 96), outline=line)
    d.polygon([(c - 16, c + 30), (c + 16, c + 30), (c, c + 84)], fill=paint[0], outline=line)
    for s in (-1, 1): d.ellipse((c + s * 70 - 14, c - 8, c + s * 70 + 14, c + 20), fill=paint[1], outline=line, width=3)
    a = np.asarray(im, np.float32) + N3(n, 1, seed, 6) + N3(n, 12, seed + 1, 10)
    pits = np.clip(noise(n, 0.7, seed + 2) - 2.0, 0, 1)[..., None]
    return a * (1 - pits * 0.35)


def tex_stone(n=256, seed=11, base=(186, 172, 140)):
    return fill(n, base, 8, seed) + N3(n, 0.6, seed + 1, 12) + N3(n, 6, seed + 2, 10)


def tex_thatch(w=256, h=256, seed=13):
    """palm thatch: overlapping rows of dry fronds"""
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.6, seed, h) * 60 + 128).resize((w, h // 12)).resize((w, h)), np.float32) / 255
    c = lerp(C((150, 120, 66)), C((206, 176, 108)), st[..., None])
    rows = (y * 6) % 1.0
    c = c * (0.65 + 0.35 * rows)[..., None]
    return c + N3(w, 1, seed + 1, 6, h)


def tex_fringe(w=256, h=128, seed=15):
    """ragged thatch fringe (alpha)"""
    x, y = xy(w, h)
    r = np.random.default_rng(seed)
    cut = 0.55 + 0.4 * np.abs(noise(w, 1.5, seed, h)[0])[None, :] * 0.6
    a = (y < cut).astype(np.float32)
    st = np.asarray(img(noise(w, 0.6, seed + 1, h) * 60 + 128).resize((w, max(2, h // 16))).resize((w, h)), np.float32) / 255
    c = lerp(C((140, 110, 60)), C((210, 180, 110)), st[..., None])
    return c, a * 255


def tex_palm_trunk(w=128, h=256, seed=17):
    x, y = xy(w, h)
    rings = (y * 8) % 1.0
    c = lerp(C((96, 76, 54)), C((150, 124, 92)), np.clip(rings * 1.4, 0, 1)[..., None]) + N3(w, 1, seed, 10, h)
    return c


def tex_frond(w=256, h=512, seed=19):
    """palm frond: midrib + many leaflets (alpha)"""
    x, y = xy(w, h)
    cx = 0.5
    leaf = np.abs(np.sin((y * 40 - np.abs(x - cx) * 18) * math.pi)) > 0.25
    env = np.abs(x - cx) < (0.48 * np.sin(np.clip(y, 0, 1) * math.pi) ** 0.5 + 0.02)
    a = (leaf & env).astype(np.float32)
    a = np.where(np.abs(x - cx) < 0.025, 1.0, a)
    c = lerp(C((40, 110, 40)), C((110, 170, 60)), np.clip(np.abs(x - cx) * 2, 0, 1)[..., None]) + N3(w, 1, seed, 10, h)
    c = np.where((np.abs(x - cx) < 0.025)[..., None], C((170, 170, 90)), c)
    return c, a * 255


def tex_monstera(n=256, seed=21):
    """split-leaf jungle plant leaf (alpha)"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx / 0.48, dy / 0.46)
    ang = np.arctan2(dy, dx)
    slits = (np.abs(np.sin(ang * 5)) < 0.12) & (rr > 0.45)
    holes = (np.abs(np.sin(ang * 5 + 0.3)) < 0.08) & (np.abs(rr - 0.35) < 0.06)
    a = ((rr < 1.0) & ~slits & ~holes).astype(np.float32)
    c = C((40, 110, 50)) + N3(n, 1, seed, 8)
    veins = np.abs(np.sin(ang * 5 + 1.57)) < 0.05
    c = np.where(veins[..., None], C((90, 160, 80)), c)
    return c, a * 255


def tex_flame(w=64, h=128, seed=23):
    x, y = xy(w, h)
    cx = 0.5 + 0.06 * np.sin(y * 9)
    width = 0.42 * (y ** 0.7)
    core = np.clip(1 - np.abs(x - cx) / np.maximum(width, 1e-3), 0, 1) * np.clip((y - 0.05) * 3, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((255, 120, 20)) * core[..., None] + C((255, 230, 140)) * (core ** 3)[..., None]
    return c


def tex_fret_ceramic(w=256, h=128, seed=25):
    """red-orange ceramic with a black fret band (braziers, pots)"""
    im = Image.new('RGB', (w, h), (180, 90, 50)); d = ImageDraw.Draw(im)
    d.rectangle((0, 36, w, 92), fill=(230, 210, 170))
    for k in range(8):
        x0 = k * w / 8
        d.line([(x0 + 4, 86), (x0 + 4, 46), (x0 + 24, 46), (x0 + 24, 70), (x0 + 14, 70)], fill=(30, 26, 22), width=5)
    return np.asarray(im, np.float32) + N3(w, 1, seed, 6, h)


def tex_stripes(cols, n=128, k=6, seed=27):
    x, y = xy(n)
    i = (np.floor(x * k) % len(cols)).astype(int)
    c = np.zeros((n, n, 3), np.float32)
    for j, col in enumerate(cols):
        c = np.where((i == j)[..., None], C(col), c)
    return c + N3(n, 1, seed, 4)


def tex_jaguar(n=128, seed=29):
    """jaguar pelt: ochre with rosettes"""
    c = fill(n, (214, 160, 70), 8, seed)
    idx, ed = voronoi(n, 24, seed + 1)
    ros = (ed > 0.04) & (ed < 0.07)
    spot = ed > 0.1
    c = np.where(ros[..., None], C((40, 30, 20)), c)
    c = np.where((spot & (noise(n, 2, seed + 2) > 0.8))[..., None], C((60, 40, 24)), c)
    return c + N3(n, 0.6, seed + 3, 8)


def tex_gold(n=64, seed=31):
    return fill(n, (230, 180, 70), 10, seed) + N3(n, 0.6, seed + 1, 12)


def tex_jade(n=64, seed=33):
    return fill(n, (60, 150, 100), 8, seed) + N3(n, 3, seed + 1, 14)


def tex_eagle(n=128, seed=35):
    """eagle feathers: brown with light edges"""
    x, y = xy(n)
    v = (y * 10 + np.abs(np.sin(x * 12)) * 0.6) % 1.0
    c = lerp(C((80, 56, 34)), C((190, 160, 110)), np.clip((v - 0.7) * 4, 0, 1)[..., None])
    return c + N3(n, 1, seed, 6)


def tex_water_strip(w=64, h=256, seed=37):
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.8, seed, h) * 60 + 128).resize((w, h // 12)).resize((w, h)), np.float32) / 255
    a = np.clip(0.45 + (st - 0.5) * 1.4, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((200, 240, 250))
    return c, a * 255


def tex_vine(w=64, h=256, seed=39):
    """hanging vine with leaves (alpha)"""
    x, y = xy(w, h)
    cx = 0.5 + 0.08 * np.sin(y * 20)
    stem = np.abs(x - cx) < 0.06
    lv = (np.abs(np.sin(y * 32)) > 0.6) & (np.abs(x - cx) < 0.4 * np.abs(np.sin(y * 16)))
    a = (stem | lv).astype(np.float32)
    c = np.where(stem[..., None], C((80, 70, 40)), C((50, 120, 50))) + N3(w, 1, seed, 10, h)
    return c, a * 255


def make_textures():
    T('env', tex_env())
    T('tab_tlaloc', tex_tablero('tlaloc')); T('tab_serpent', tex_tablero('serpent', seed=2)); T('shrine_wall', tex_shrine())
    T('scales', tex_scales()); T('scales_gold', tex_scales(256, 256, 6, (180, 130, 40), (250, 210, 90)))
    f, a = tex_feather(); T('feather', f, a); f, a = tex_feather(128, 256, 8, (200, 40, 40), (250, 220, 80)); T('feather_red', f, a)
    T('sunstone', tex_sunstone()); T('stone', tex_stone()); T('stone_dark', tex_stone(256, 12, (120, 112, 98))); T('stone_blue', tex_stone(256, 14, (110, 150, 170)))
    T('stone_green', tex_stone(256, 16, (100, 130, 96))); T('thatch', tex_thatch()); f, a = tex_fringe(); T('fringe', f, a)
    T('palm_trunk', tex_palm_trunk()); f, a = tex_frond(); T('frond', f, a); f, a = tex_monstera(); T('monstera', f, a)
    T('flame', tex_flame()); T('ceramic', tex_fret_ceramic()); T('jaguar', tex_jaguar()); T('gold', tex_gold()); T('jade', tex_jade())
    T('eagle', tex_eagle()); f, a = tex_water_strip(); T('water_strip', f, a); f, a = tex_vine(); T('vine', f, a)
    T('white', fill(64, (240, 238, 232), 3, 41)); T('black', fill(64, (24, 22, 22), 2, 42)); T('red', fill(64, (176, 50, 40), 4, 43))
    T('turq', fill(64, (40, 170, 170), 4, 44)); T('ochre', fill(64, (210, 160, 60), 6, 45)); T('wood', fill(128, (120, 80, 50), 8, 46) + N3(128, 0.5, 47, 12))
    T('wood_light', fill(128, (170, 124, 80), 8, 48) + N3(128, 0.5, 49, 12)); T('rubber', fill(64, (30, 30, 34), 3, 50))
    T('canvas_a', tex_stripes([(230, 70, 60), (250, 236, 210), (40, 160, 160), (250, 236, 210)])); T('canvas_b', tex_stripes([(240, 180, 40), (250, 236, 210)]))
    T('tube_a', tex_stripes([(240, 90, 60), (250, 210, 60)], 64, 8)); T('tube_b', tex_stripes([(40, 170, 170), (250, 250, 250)], 64, 8))
    T('agave', fill(64, (90, 140, 120), 6, 51) + N3(64, 0.5, 52, 8)); T('rock', fill(128, (120, 116, 104), 10, 53) + N3(128, 3, 54, 14))
    T('moss_rock', lerp(fill(128, (120, 116, 104), 10, 55), C((70, 110, 50)), np.clip(noise(128, 6, 56) * 0.6, 0, 1)[..., None]))
    T('bottle_g', fill(32, (60, 160, 90), 3, 57)); T('bottle_b', fill(32, (120, 70, 40), 3, 58)); T('lime', fill(32, (140, 200, 60), 3, 59))
    T('coconut', fill(64, (110, 80, 50), 8, 60)); T('flow', np.zeros((8, 8, 3)) + 200)
    T('obsidian', fill(64, (30, 30, 36), 3, 61) + N3(64, 0.5, 62, 10)); T('slide_in', fill(128, (60, 190, 190), 4, 63) + N3(128, 6, 64, 6))
    T('flume_ochre', fill(128, (220, 160, 60), 6, 65) + N3(128, 6, 66, 8)); T('menu', text_img('TACOS  2\nNACHOS  3\nHORCHATA  1', 256, 256, (30, 34, 30), (240, 240, 220)))


# ================================================================================================= shader shortcuts
def SB(img, tile=256.0, shade=30, **kw):
    """architecture shader on a brush texture image + planar uv"""
    return S(BT(img), 'lm', shade=shade, **kw)


def arch_uv(n, tile=256.0):
    return planar_uv(n, tile)


# ================================================================================================= great pyramid
def pyramid():
    """the whole pyramid (tiers, both stairs, tunnel + tomb surfaces) from az_shapes, plus cornices, mouldings and
    painted friezes. Built in world coordinates; placed at the pyramid centre."""
    X = Model()
    cx, cy = L.PC
    tiers = SH.pyramid_tiers(); steps = SH.pyramid_steps()
    allb = tiers + steps
    tab = {0: S('tab_tlaloc', 'lm', shade=20), 1: S('tab_serpent', 'lm', shade=20), 2: S('tab_tlaloc', 'lm', shade=20, tag='b'), 3: S('tab_serpent', 'lm', shade=20, tag='b')}
    s_top = SB('pavers'); s_talud = SB('ashlar'); s_notch = SB('ashlar_red'); s_tread = SB('coping'); s_riser = SB('stucco_red')
    s_tunnel = SB('glyph_wall'); s_tomb = SB('painted_wall'); s_ceil = SB('stucco')

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None                      # sits on the ground slab
        q = c + n * 2
        if SH.in_pyr_interior(q):
            if n[2] < -0.5: return s_ceil, arch_uv(n, 256)
            if abs(c[1] - cy) > L.TOMB_HALF - 1 or abs(c[0] - cx) <= L.TOMB_HALF + 1:
                return (s_tomb if abs(c[0] - cx) <= L.TOMB_HALF + 1 and abs(c[1] - cy) <= L.TOMB_HALF + 1 else s_tunnel), arch_uv(n, 256 if abs(c[0] - cx) > L.TOMB_HALF else 512)
            return s_tunnel, arch_uv(n, 256)
        in_stair = abs(c[0] - cx) <= L.STAIR_HW + 0.5 and abs(c[1] - cy) > L.TOP_HALF - 0.5
        if in_stair:
            if n[2] > 0.9: return s_tread, arch_uv(n, 128)
            if abs(n[1]) > 0.9: return s_riser, arch_uv(n, 128)
            return s_notch, arch_uv(n, 256)
        if abs(abs(c[0] - cx) - L.STAIR_HW) < 1 and abs(n[0]) > 0.9 and abs(c[1] - cy) > L.TOP_HALF - 1:
            return s_notch, arch_uv(n, 256)                            # notch side walls
        if n[2] > 0.95: return s_top, arch_uv(n, 512)
        if n[2] > 0.3: return s_talud, arch_uv(n, 256)
        # tablero: frieze fitted to the band (u along the face, v over the band height)
        k = int(min(L.NT - 1, max(0, (c[2]) // L.TIER_H)))
        z1 = (k + 1) * L.TIER_H; z0 = k * L.TIER_H + L.TALUD_H
        a = int(np.argmax(np.abs(n[:2])))
        sgn = 1 if n[a] > 0 else -1
        u_ax = np.array([0.0, 1.0, 0]) if a == 0 else np.array([1.0, 0, 0])
        if (a == 0 and sgn < 0) or (a == 1 and sgn > 0): u_ax = -u_ax
        return tab[k], (lambda p, u_ax=u_ax, z0=z0, z1=z1: (float(p @ u_ax) / 320.0, (z1 - p[2]) / (z1 - z0)))
    solids_mesh(X, allb, texfn)
    # cornices (projecting lip at each terrace edge) and mouldings where the talud meets the tablero
    cor = SB('fret_jade', shade=20); mould = SB('coping', shade=20, tag='m')
    for k in range(L.NT):
        t = L.tablero_half(k); zt = (k + 1) * L.TIER_H; zm = k * L.TIER_H + L.TALUD_H
        for side in range(4):                                  # 0 south, 1 east, 2 north, 3 west
            if side in (0, 2): gaps = (-L.STAIR_HW, L.STAIR_HW)
            elif k == 0: gaps = (-L.TUNNEL_HW, L.TUNNEL_HW)
            else: gaps = None
            spans = [(-t - 8, gaps[0]), (gaps[1], t + 8)] if gaps else [(-t - 8, t + 8)]
            for (u0, u1) in spans:
                for (za, zb, d0, d1, sh, fc) in ((zt - 18, zt, -2, 8, cor, 'nsewb'), (zm, zm + 10, -1, 6, mould, 'nsewt')):
                    if sh is mould and k == 0 and side in (1, 3): continue
                    if side == 0: mn, mx = (cx + u0, cy - t - d1, za), (cx + u1, cy - t - d0, zb)
                    elif side == 2: mn, mx = (cx + u0, cy + t + d0, za), (cx + u1, cy + t + d1, zb)
                    elif side == 1: mn, mx = (cx + t + d0, cy + u0, za), (cx + t + d1, cy + u1, zb)
                    else: mn, mx = (cx - t - d1, cy + u0, za), (cx - t - d0, cy + u1, zb)
                    boxm(X.mesh(sh), mn, mx, r=1, tile=128, faces=fc)
    X.shift((cx, cy, 0))
    return save('pyramid', X)


# ================================================================================================= serpent heads
def serpent_head(name, L_=160.0, W_=96.0, H_=96.0, open_mouth=True, col='scales', plume=True):
    """stylised feathered-serpent head (Kukulkan balustrade head) facing +x, base on z 0, back at x 0"""
    X = Model()
    sk = X.mesh(S(col, 'lm', shade=50)); wt = X.mesh(S('white', 'lm')); bk = X.mesh(S('black', 'lm')); rd = X.mesh(S('red', 'lm'))
    st = X.mesh(S('stone', 'lm', tag='h'))
    # skull block (upper jaw) + snout
    boxm(sk, (0, -W_ / 2, H_ * 0.42), (L_ * 0.82, W_ / 2, H_), r=10, k=3, tile=96)
    boxm(sk, (L_ * 0.55, -W_ * 0.42, H_ * 0.46), (L_, W_ * 0.42, H_ * 0.86), r=12, k=3, tile=96)
    # lower jaw (dropped open)
    if open_mouth:
        boxm(sk, (L_ * 0.05, -W_ * 0.44, 0), (L_ * 0.95, W_ * 0.44, H_ * 0.2), r=8, k=2, tile=96)
        boxm(rd, (L_ * 0.15, -W_ * 0.36, H_ * 0.18), (L_ * 0.85, W_ * 0.36, H_ * 0.22), r=1, tile=64)       # tongue / mouth
        boxm(rd, (L_ * 0.12, -W_ * 0.36, H_ * 0.40), (L_ * 0.80, W_ * 0.36, H_ * 0.44), r=1, tile=64)
        for s in (-1, 1):
            cone(wt, (L_ * 0.86, s * W_ * 0.3, H_ * 0.46), (L_ * 0.86, s * W_ * 0.3, H_ * 0.16), 7, 6)        # fangs
            cone(wt, (L_ * 0.70, s * W_ * 0.34, H_ * 0.46), (L_ * 0.70, s * W_ * 0.34, H_ * 0.28), 5, 6)
            cone(wt, (L_ * 0.80, s * W_ * 0.3, H_ * 0.2), (L_ * 0.80, s * W_ * 0.3, H_ * 0.34), 5, 6)
        boxm(sk, (0, -W_ * 0.46, 0), (L_ * 0.25, W_ * 0.46, H_ * 0.45), r=6, k=2, tile=96)                  # hinge
    else:
        boxm(sk, (0, -W_ * 0.46, 0), (L_ * 0.95, W_ * 0.46, H_ * 0.45), r=8, k=2, tile=96)
    for s in (-1, 1):
        sphere(wt, (L_ * 0.55, s * W_ * 0.47, H_ * 0.8), W_ * 0.14, nu=12, nv=6)
        sphere(bk, (L_ * 0.58, s * W_ * 0.53, H_ * 0.8), W_ * 0.06, nu=8, nv=4)
        boxm(st, (L_ * 0.4, s * W_ * 0.5 - (6 if s > 0 else 0), H_ * 0.9), (L_ * 0.72, s * W_ * 0.5 + (0 if s > 0 else 6), H_ * 1.02), r=2, tile=64)   # brow
        sphere(bk, (L_ * 0.96, s * W_ * 0.2, H_ * 0.78), 5, nu=6, nv=4)                                         # nostrils
    if plume:
        fe = X.mesh(S('feather', 'alpha', vs=1.0))
        for k in range(9):
            a = math.radians(-70 + k * 17.5)
            base = np.array([L_ * 0.12, math.sin(a) * W_ * 0.45, H_ * 0.7 + math.cos(a) * H_ * 0.3])
            dirv = np.array([-0.55, math.sin(a) * 0.8, math.cos(a) * 0.8]); dirv /= np.linalg.norm(dirv)
            side = np.cross(dirv, [1, 0, 0]); side /= max(1e-6, np.linalg.norm(side))
            w = H_ * 0.18; ln = H_ * 0.75
            p0 = base - side * w; p1 = base + side * w; p2 = p1 + dirv * ln; p3 = p0 + dirv * ln
            nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
            quad_uv(fe, p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    return save(name, X)


# ================================================================================================= shrine on the summit
def shrine():
    X = Model()
    cx, cy = L.PC
    s_out = S('shrine_wall', 'lm', shade=20); s_in = SB('painted_wall'); s_roof = SB('pavers', tag='r'); s_edge = SB('fret_jade', tag='r')
    s_jamb = SB('ashlar_red', tag='r'); s_ceil = SB('stucco_turq')
    x0, y0, x1, y1 = L.SHRINE; zr = L.SHRINE_ROOF

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < L.TOP_Z + 1: return None
        q = c + n * 2
        if c[2] > zr - 16.5:                                           # roof slab
            if n[2] > 0.9: return s_roof, arch_uv(n, 512)
            if n[2] < -0.9: return s_ceil, arch_uv(n, 256)
            return s_edge, (lambda p, n=n: ((p[0] + p[1]) / 256.0, (zr - p[2]) / 16.0 * 0.25))
        if SH.shrine_inside(q): return (s_ceil if n[2] < -0.5 else s_in), arch_uv(n, 512)
        if abs(abs(c[0] - cx) - 64) < 1 and c[1] < y0 + 33: return s_jamb, arch_uv(n, 128)
        if n[2] < -0.9: return s_jamb, arch_uv(n, 128)                # door lintel underside
        if n[2] > 0.9: return s_roof, arch_uv(n, 256)
        hgt = zr - 16 - L.TOP_Z
        a = int(np.argmax(np.abs(n[:2]))); u_ax = np.array([0.0, 1, 0]) if a == 0 else np.array([1.0, 0, 0])
        if (a == 0 and n[0] < 0) or (a == 1 and n[1] > 0): u_ax = -u_ax
        return s_out, (lambda p, u_ax=u_ax: (float(p @ u_ax) / 128.0, (zr - 16 - p[2]) / hgt))
    solids_mesh(X, SH.shrine(), texfn)
    # Tlaloc mask over the door: goggle rings, fangs, a moustache scroll (relief on the south face)
    bl = X.mesh(S('stone_blue', 'lm')); wt = X.mesh(S('white', 'lm', tag='s')); bk = X.mesh(S('black', 'lm', tag='s'))
    yf = y0 - 1
    for s in (-1, 1):
        torus(bl, (cx + s * 40, yf - 6, L.TOP_Z + 196), 22, 7, axis=(0, 1, 0), n=20, m=8, utile=2)
        sphere(bk, (cx + s * 40, yf - 4, L.TOP_Z + 196), 9, nu=10, nv=5)
        cone(wt, (cx + s * 14, yf - 6, L.TOP_Z + 170), (cx + s * 16, yf - 8, L.TOP_Z + 146), 6, 6)
    tube(bl, [(cx - 60, yf - 6, L.TOP_Z + 170), (cx - 30, yf - 10, L.TOP_Z + 180), (cx, yf - 10, L.TOP_Z + 174),
              (cx + 30, yf - 10, L.TOP_Z + 180), (cx + 60, yf - 6, L.TOP_Z + 170)], 7, nseg=8)
    # roof crest: low cloud scrolls at the back corners only (keeps the roof open for shooting)
    for sx in (-1, 1):
        for k in range(2):
            xx = cx + sx * (x1 - cx - 24 - 56 * k)
            torus(wt, (xx, y1 - 12, zr + 22), 18, 6, axis=(0, 1, 0), n=16, m=6, utile=2)
            boxm(X.mesh(SB('stucco', tag='c')), (xx - 22, y1 - 22, zr), (xx + 22, y1 - 2, zr + 6), r=1, tile=64)
    X.shift((cx, cy, L.TOP_Z))
    return save('shrine', X)


def idol():
    """Tlaloc idol inside the shrine (seated figure with goggles, holding a lightning staff); origin floor centre, faces -y"""
    X = Model()
    bl = X.mesh(S('stone_blue', 'lm', tag='i')); wt = X.mesh(S('white', 'lm', tag='i')); bk = X.mesh(S('black', 'lm', tag='i'))
    gd = X.mesh(S('gold', 'lms', v=0.25)); st = X.mesh(S('stone_dark', 'lm'))
    boxm(st, (-48, -40, 0), (48, 40, 32), r=3, tile=64)                                  # pedestal
    boxm(bl, (-34, -26, 32), (34, 26, 96), r=10, k=3, tile=64)                           # body
    boxm(bl, (-28, -24, 96), (28, 24, 150), r=10, k=3, tile=64)                          # head
    for s in (-1, 1):
        torus(wt, (s * 12, -25, 128), 9, 3, axis=(0, 1, 0), n=14, m=6, utile=1)
        sphere(bk, (s * 12, -24, 128), 4, nu=8, nv=4)
        cone(wt, (s * 6, -25, 110), (s * 6, -26, 100), 3, 6)
        boxm(bl, (s * 34 - 6, -18, 40), (s * 34 + 6, 4, 92), r=4, k=2, tile=64)           # arms
    boxm(gd, (-36, -18, 150), (36, 18, 186), r=4, k=2, tile=64)                          # headdress
    for k in range(5):
        boxm(gd, (-30 + 15 * k - 4, -8, 186), (-30 + 15 * k + 4, 8, 206 + 6 * (k % 2)), r=2, tile=64)
    tube(gd, [(36, -30, 40), (40, -32, 90), (32, -34, 130), (44, -36, 170)], 3, nseg=6)     # lightning staff
    return save('idol', X)


def chacmool():
    """reclining Chacmool figure holding a bowl on its belly (offering altar); origin floor centre, head toward -x"""
    X = Model()
    st = X.mesh(S('stone', 'lm', tag='c')); dk = X.mesh(S('stone_dark', 'lm', tag='c')); gd = X.mesh(S('gold', 'lms', v=0.25, tag='c'))
    boxm(dk, (-90, -40, 0), (90, 40, 16), r=3, tile=64)                                   # base slab
    ellipsoid(st, (0, 0, 36), 52, 26, 20, nu=16, nv=8)                                   # torso
    ellipsoid(st, (-64, 0, 52), 22, 20, 30, nu=12, nv=8)                                 # shoulders up
    sphere(st, (-70, 0, 92), 18, nu=12, nv=8)                                            # head, turned to the side
    for s in (-1, 1):
        tube(st, [(30, s * 16, 28), (64, s * 16, 64), (86, s * 16, 22)], 10, nseg=8)      # bent legs
        tube(st, [(-58, s * 22, 60), (-30, s * 26, 46), (-6, s * 14, 56)], 7, nseg=8)      # arms to the bowl
    revolve(gd, [(0, 54), (18, 56), (22, 66), (16, 64), (0, 62)], n=16, cx=-4, cy=0)        # bowl
    return save('chacmool', X)


def brazier(name='brazier', h=72.0, r=34.0):
    """ceramic fire bowl on a stone drum with flames (crossed quads: q3map2 merges misc_model surfaces)"""
    X = Model()
    st = X.mesh(S('stone', 'lm', tag='b')); ce = X.mesh(S('ceramic', 'lm')); bk = X.mesh(S('black', 'lm', tag='b'))
    fl = X.mesh(S('flame', 'add', wave='wave sin 0.85 0.15 0 3.2', tag='f'))
    revolve(st, [(0, 0), (r * 0.8, 0), (r * 0.7, h * 0.15), (r * 0.5, h * 0.55), (r * 0.6, h * 0.6), (0, h * 0.6)], n=16, vlen=64)
    revolve(ce, [(r * 0.5, h * 0.58), (r, h * 0.75), (r * 1.05, h), (r * 0.92, h), (r * 0.6, h * 0.82), (0, h * 0.82)], n=20, vlen=h * 0.5,
            v_of=lambda rr, zz: (h - zz) / (h * 0.45))
    disc(bk, r * 0.9, h * 0.9, n=16)
    for k in range(3):
        a = math.radians(60 * k)
        w = r * (1.0 - 0.15 * k); hh = r * 2.2 * (1 - 0.15 * k)
        d = np.array([math.cos(a), math.sin(a), 0])
        c = np.array([0, 0, h * 0.88 + hh / 2])
        quad_uv(fl, c - d * w - [0, 0, hh / 2], c + d * w - [0, 0, hh / 2], c + d * w + [0, 0, hh / 2], c - d * w + [0, 0, hh / 2],
                [(0, 1), (1, 1), (1, 0), (0, 0)])
    return save(name, X)


# ================================================================================================= slides
def sweep(M, path, prof, closed=False, vlen=128.0, inward=False, utile=1.0):
    """2D cross-section prof [(u, v)] swept along a 3D path; frames keep 'up' = world z"""
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


def serpent_tube(path, sup):
    """Quetzalcoatl tube slide: scaled green body, feather collars, a turquoise inside, running water; stone pillars
    under it. World coordinates (placed at the origin)."""
    X = Model()
    body = S('scales', 'lm', shade=60, tag='t'); inner = S('slide_in', 'lm', shade=60)
    fe = S('feather', 'alpha', tag='t'); fr = S('feather_red', 'alpha', tag='t'); wat = S('water_strip', 'flow', speed=-1.4)
    st = S('stone', 'lm', tag='p'); fret = SB('fret', tag='p')
    P = densify(path[1:], 40)
    C3 = [np.array([p[0], p[1], p[2] + L.TUBE_ZC]) for p in P]
    sweep(X.mesh(body), C3, circle_prof(L.TUBE_R, 20), closed=True, vlen=192)
    sweep(X.mesh(inner), C3, circle_prof(L.TUBE_R - 4, 20), closed=True, vlen=256, inward=True)
    sweep(X.mesh(wat), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-34, 0), (34, 0)], vlen=200)
    for i in range(6, len(C3) - 3, 9):
        c = C3[i]; d = C3[i + 1] - C3[i - 1]; d /= np.linalg.norm(d)
        b1, b2 = frame(d)
        for k in range(14):
            a = 2 * math.pi * k / 14
            rv = b1 * math.cos(a) + b2 * math.sin(a)
            if rv[2] < -0.5: continue
            base = c + rv * (L.TUBE_R - 2)
            tipd = rv * 0.8 - d * 0.6; tipd /= np.linalg.norm(tipd)
            side = np.cross(tipd, rv); side /= max(1e-6, np.linalg.norm(side))
            w = 9; ln = 46
            p0 = base - side * w; p1 = base + side * w; p2 = p1 + tipd * ln; p3 = p0 + tipd * ln
            nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
            quad_uv(X.mesh(fr if k % 3 == 0 else fe), p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    for (x, y, z) in sup:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        boxm(X.mesh(st), (x - 22, y - 22, 0), (x + 22, y + 22, zt - 16), r=2, tile=128)
        boxm(X.mesh(fret), (x - 26, y - 26, zt - 16), (x + 26, y + 26, zt), r=1, tile=128)
    return save('serpent_tube', X)


def tube_head():
    """the serpent's head round the tube mouth on the summit: open jaws, fangs, goggle eyes, a feather crown.
    Origin at the tube entrance floor centre, faces +x (players walk in going -x)."""
    X = Model()
    sk = X.mesh(S('scales', 'lm', shade=50, tag='hd')); wt = X.mesh(S('white', 'lm', tag='hd')); bk = X.mesh(S('black', 'lm', tag='hd'))
    rd = X.mesh(S('red', 'lm', tag='hd')); gd = X.mesh(S('gold', 'lms', v=0.25, tag='hd'))
    R = L.TUBE_R; zc = L.TUBE_ZC
    # collar ring round the mouth (lathe about z, turned onto the x axis)
    ring = Mesh()
    revolve(ring, [(R + 2, -40), (R + 30, -30), (R + 34, 0), (R + 28, 30), (R + 2, 40)], n=24, vlen=128)
    sk.add(ring, rot_axis((0, 1, 0), math.pi / 2), (0, 0, zc))
    # upper jaw: a broad snout over the opening, lower jaw under the floor line
    boxm(sk, (-10, -R - 34, zc + R - 6), (150, R + 34, zc + R + 48), r=18, k=3, tile=128)
    boxm(sk, (90, -R - 20, zc + R - 14), (190, R + 20, zc + R + 30), r=16, k=3, tile=128)
    boxm(sk, (-10, -R - 34, -14), (170, R + 34, 0), r=6, k=2, tile=128)
    boxm(rd, (0, -R + 4, 0), (160, R - 4, 2), r=0.5, tile=64)
    for s in (-1, 1):
        for (xx, ln) in ((170, 46), (120, 30), (70, 22)):
            cone(wt, (xx, s * (R - 6), zc + R - 8), (xx + 4, s * (R - 6), zc + R - 8 - ln), 7, 6)
        cone(wt, (150, s * (R - 10), 0), (150, s * (R - 10), 26), 6, 6)
        torus(gd, (60, s * (R + 30), zc + R + 30), 20, 6, axis=(0, 1, 0), n=18, m=6, utile=2)
        sphere(bk, (60, s * (R + 30), zc + R + 30), 10, nu=10, nv=5)
        sphere(bk, (186, s * 14, zc + R + 16), 5, nu=6, nv=4)
    # feather crown fanned behind the head
    fe = X.mesh(S('feather', 'alpha', tag='hd')); fr = X.mesh(S('feather_red', 'alpha', tag='hd'))
    for k in range(13):
        a = math.radians(-80 + k * 160 / 12)
        base = np.array([0, math.sin(a) * (R + 30), zc + math.cos(a) * (R + 30) + 10])
        dirv = np.array([-0.35, math.sin(a), math.cos(a)]); dirv /= np.linalg.norm(dirv)
        side = np.cross(dirv, [1, 0, 0]); side /= max(1e-6, np.linalg.norm(side))
        w = 18; ln = 120
        p0 = base - side * w; p1 = base + side * w; p2 = p1 + dirv * ln; p3 = p0 + dirv * ln
        nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
        quad_uv(fr if k % 2 else fe, p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    return save('tube_head', X)


def flume(path, sup):
    """Eagle flume: open U channel, ochre outside with a fret band on the lip, turquoise inside, running water"""
    X = Model()
    r = 52; lip = 46
    zc = r * 0.55
    col = S('flume_ochre', 'lm', shade=60); inn = S('slide_in', 'lm', shade=60, tag='f'); band = SB('fret', tag='f')
    prof_out = [(-(r + 4), lip)] + [((r + 4) * math.cos(a), zc + (r + 4) * math.sin(a)) for a in np.radians(np.linspace(180, 360, 13))] + [((r + 4), lip)]
    prof_in = [(-r, lip)] + [(r * math.cos(a), zc + r * math.sin(a)) for a in np.radians(np.linspace(180, 360, 13))] + [(r, lip)]
    P = densify(path[1:], 40)
    sweep(X.mesh(col), P, prof_out, vlen=256)
    sweep(X.mesh(inn), P, prof_in, vlen=256, inward=True)
    sweep(X.mesh(band), P, [(-(r + 5), lip - 16), (-(r + 5), lip + 2)], vlen=256)
    sweep(X.mesh(band), P, [((r + 5), lip + 2), ((r + 5), lip - 16)], vlen=256)
    sweep(X.mesh(col), P, [(-(r + 5), lip + 2), (-r, lip + 2)], vlen=256)
    sweep(X.mesh(col), P, [(r, lip + 2), (r + 5, lip + 2)], vlen=256)
    sweep(X.mesh(S('water_strip', 'flow', speed=-1.4, tag='f')), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-r * 0.6, 0), (r * 0.6, 0)], vlen=200)
    st = X.mesh(S('stone', 'lm', tag='fp'))
    bot = zc - r - 4
    for (x, y, z) in sup:
        zt = z + bot + 4
        boxm(st, (x - 18, y - 18, 0), (x + 18, y + 18, zt), r=2, tile=128)
        boxm(st, (x - r, y - 14, zt - 12), (x + r, y + 14, zt), r=2, tile=128)
    return save('eagle_flume', X)


def eagle_head():
    """eagle-warrior head at the flume start (faces -x toward the platform; flume runs +x); origin floor centre"""
    X = Model()
    eg = X.mesh(S('eagle', 'lm')); gd = X.mesh(S('gold', 'lms', v=0.25, tag='e')); bk = X.mesh(S('black', 'lm', tag='e')); wt = X.mesh(S('white', 'lm', tag='e'))
    # an arch over the flume entrance shaped like the eagle's head and open beak
    for s in (-1, 1):
        boxm(eg, (-20, s * 74 - 14, 0), (20, s * 74 + 14, 150), r=6, k=2, tile=96)
    boxm(eg, (-30, -92, 140), (40, 92, 210), r=24, k=3, tile=96)
    boxm(gd, (-70, -26, 140), (-20, 26, 186), r=10, k=2, tile=64)
    cone(gd, (-60, 0, 160), (-108, 0, 132), 22, 8)                                       # hooked beak
    for s in (-1, 1):
        sphere(wt, (-24, s * 44, 186), 12, nu=10, nv=5); sphere(bk, (-32, s * 46, 186), 6, nu=8, nv=4)
    fe = X.mesh(S('feather', 'alpha', tag='e'))
    for k in range(9):
        a = math.radians(-60 + k * 15)
        base = np.array([20, math.sin(a) * 60, 200 + math.cos(a) * 10])
        dirv = np.array([0.4, math.sin(a), math.cos(a) + 0.4]); dirv /= np.linalg.norm(dirv)
        side = np.cross(dirv, [1, 0, 0]); side /= max(1e-6, np.linalg.norm(side))
        p0 = base - side * 12; p1 = base + side * 12; p2 = p1 + dirv * 80; p3 = p0 + dirv * 80
        nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
        quad_uv(fe, p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    return save('eagle_head', X)


# ================================================================================================= the Sun Stone
def sunstone():
    """upright calendar disc (both faces carved) in a stone cradle; origin floor centre, faces +-y"""
    X = Model()
    R = L.SUN_R; th = 22.0
    zc = 64 + R
    fac = X.mesh(S('sunstone', 'lm', shade=30)); rim = X.mesh(S('stone', 'lm', tag='ss')); cr = X.mesh(SB('ashlar_red', tag='ss'))
    n = 64
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    for sgn in (-1, 1):
        pts = [np.array([R * math.cos(a), sgn * th, zc + R * math.sin(a)]) for a in angs]
        # u left->right as seen from the front: front (sgn -1, facing -y) sees +x on the right
        uvs = [(0.5 + (0.5 * math.cos(a)) * (1 if sgn < 0 else -1), 0.5 - 0.5 * math.sin(a)) for a in angs]
        fac.poly(pts, (0, sgn, 0), uvs)
    ring = Mesh()
    revolve(ring, [(R, -th), (R + 4, -th + 4), (R + 4, th - 4), (R, th)], n=n, vlen=128)
    rim.add(ring, np.array([[1.0, 0, 0], [0, 0, 1], [0, -1, 0]]), (0, 0, zc))     # axis z -> y (rotation)
    # cradle: stepped stone block with a curved saddle the disc sits in
    boxm(cr, (-R * 0.8, -60, 0), (R * 0.8, 60, 40), r=2, tile=128)
    boxm(cr, (-R * 0.55, -44, 40), (R * 0.55, 44, 72), r=2, tile=128)
    return save('sunstone', X)


# ================================================================================================= Tlaloc head fountain
def tlaloc_head():
    """giant stone head of the rain god facing -y: goggle eyes, curled moustache lip, fangs, ear spools, a stepped
    headdress with a flat walkable crown (z HEAD_TOP above the plaza when placed on the plinth), water pouring from
    the mouth. Origin = plinth top centre (z HEAD_PLINTH[2])."""
    X = Model()
    zb = L.HEAD_PLINTH[2]; ztop = L.HEAD_TOP - zb
    bl = X.mesh(S('stone_blue', 'lm', tag='th')); wt = X.mesh(S('white', 'lm', tag='th')); bk = X.mesh(S('black', 'lm', tag='th'))
    tq = X.mesh(S('turq', 'lm', tag='th')); rd = X.mesh(S('red', 'lm', tag='th')); st = X.mesh(S('stone', 'lm', tag='th'))
    gd = X.mesh(S('gold', 'lms', v=0.25, tag='th')); tb = X.mesh(S('tab_tlaloc', 'lm', tag='th'))
    W = 168; D = 140
    boxm(bl, (-W, -D, 0), (W, D, ztop - 120), r=40, k=4, tile=128)                       # face block
    for s in (-1, 1):
        torus(wt, (s * 74, -D - 8, 250), 52, 16, axis=(0, 1, 0), n=28, m=10, utile=3)   # goggles
        sphere(bk, (s * 74, -D - 2, 250), 30, nu=16, nv=8)
        sphere(wt, (s * 74 + 8, -D - 26, 262), 7, nu=8, nv=4)
        cylm(gd, (s * (W + 2), -10, 170), 44, 4, n=20)                                      # ear spools (vertical discs approx.)
        torus(gd, (s * (W + 8), -10, 200), 34, 9, axis=(1, 0, 0), n=20, m=8, utile=2)
        # fangs
        for (xx, ln) in ((30, 70), (64, 50)):
            cone(wt, (s * xx, -D - 10, 132), (s * xx, -D - 14, 132 - ln), 12, 8)
    tube(bl, [(-120, -D - 6, 150), (-70, -D - 24, 168), (0, -D - 30, 160), (70, -D - 24, 168), (120, -D - 6, 150)], 20, nseg=10)   # moustache lip
    tube(bl, [(-120, -D - 6, 150), (-140, -D - 2, 120), (-118, -D - 2, 104)], 14, nseg=8)
    tube(bl, [(120, -D - 6, 150), (140, -D - 2, 120), (118, -D - 2, 104)], 14, nseg=8)
    boxm(rd, (-80, -D - 4, 64), (80, -D + 6, 136), r=10, k=2, tile=64)                     # open mouth (red)
    boxm(bl, (-W + 10, -D + 10, 0), (W - 10, D - 10, 64), r=10, k=2, tile=128)             # chin / neck
    # headdress: band of frieze, stepped crown, turquoise discs
    zh = ztop - 120
    boxm(tb, (-W - 16, -D - 16, zh), (W + 16, D + 16, zh + 64), r=4, k=2, tile=320)
    boxm(st, (-W - 4, -D - 4, zh + 64), (W + 4, D + 4, zh + 96), r=3, tile=128)
    boxm(tq, (-W + 12, -D + 12, zh + 96), (W - 12, D - 12, ztop), r=3, tile=128)
    for k in range(5):
        sphere(gd, (-120 + 60 * k, -D - 18, zh + 32), 14, nu=10, nv=5)
    fe = X.mesh(S('feather', 'alpha', tag='th'))
    for k in range(11):
        a = math.radians(-75 + k * 15)
        base = np.array([math.sin(a) * W, D - 10, zh + 60])
        dirv = np.array([math.sin(a) * 0.7, 0.45, math.cos(a)]); dirv /= np.linalg.norm(dirv)
        side = np.cross(dirv, [0, 1, 0]); side /= max(1e-6, np.linalg.norm(side))
        p0 = base - side * 26; p1 = base + side * 26; p2 = p1 + dirv * 170; p3 = p0 + dirv * 170
        nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
        quad_uv(fe, p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    # water pouring from the mouth (front of the lip down to the pool surface)
    wf = X.mesh(S('water_strip', 'flow', speed=-1.8, tag='th'))
    zw = L.WATER - zb + 2
    P = [np.array([0, -D - 30 - 10 * t - 60 * t * t, 120 - (120 - zw) * t]) for t in np.linspace(0, 1, 10)]
    sweep(wf, P, [(-46, 0), (46, 0)], vlen=128)
    return save('tlaloc_head', X)


# ================================================================================================= jaguar temple
def jaguar_temple():
    X = Model()
    cx, cy = L.JAG
    hx, hy, H = L.JAG_PLAT
    s_tab = S('tab_serpent', 'lm', shade=20, tag='j'); s_talud = SB('ashlar_moss', tag='j'); s_top = SB('pavers', tag='j')
    s_tread = SB('coping', tag='j'); s_riser = SB('stucco_red', tag='j'); s_wall = SB('painted_wall', tag='j')
    s_in = SB('glyph_wall', tag='j'); s_roof = SB('pavers', tag='jr'); s_edge = SB('fret', tag='j'); s_jamb = SB('ashlar_red', tag='j')
    zr = L.JAG_ROOF

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        q = c + n * 2
        if c[2] > zr - 16.5:
            if n[2] > 0.9: return s_roof, arch_uv(n, 512)
            if n[2] < -0.9: return SB('stucco', tag='j'), arch_uv(n, 256)
            return s_edge, (lambda p: ((p[0] + p[1]) / 128.0, (zr - p[2]) / 64.0))
        if SH.jag_inside(q): return (SB('stucco', tag='j') if n[2] < -0.5 else s_in), arch_uv(n, 256)
        if c[2] > H - 0.5:                                             # building walls on the platform
            if n[2] < -0.9: return s_jamb, arch_uv(n, 128)
            if abs(c[1] - cy) <= 49 and n[2] < 0.5 and abs(n[1]) > 0.9: return s_jamb, arch_uv(n, 128)
            hh = zr - 16 - H
            return s_wall, (lambda p: ((p[0] + p[1]) / 256.0, (zr - 16 - p[2]) / hh * 0.75 + 0.25 * 0))
        if c[0] > cx + hx - 33 and abs(c[1] - cy) <= 96.5:               # stair
            if n[2] > 0.9: return s_tread, arch_uv(n, 128)
            if abs(n[0]) > 0.9: return s_riser, arch_uv(n, 128)
            return s_jamb, arch_uv(n, 128)
        if n[2] > 0.95: return s_top, arch_uv(n, 512)
        if n[2] > 0.3: return s_talud, arch_uv(n, 256)
        a = int(np.argmax(np.abs(n[:2]))); u_ax = np.array([0.0, 1, 0]) if a == 0 else np.array([1.0, 0, 0])
        if (a == 0 and n[0] < 0) or (a == 1 and n[1] > 0): u_ax = -u_ax
        return s_tab, (lambda p, u_ax=u_ax: (float(p @ u_ax) / 320.0, (H - p[2]) / (H - 40)))
    solids_mesh(X, SH.jaguar(), texfn)
    X.shift((cx, cy, 0))
    return save('jaguar_temple', X)


def jaguar_statue(name='jaguar', sc=1.0):
    """crouching stone jaguar with painted rosettes (faces +x); origin floor centre"""
    X = Model()
    jg = X.mesh(S('jaguar', 'lm')); st = X.mesh(S('stone_dark', 'lm', tag='js')); wt = X.mesh(S('white', 'lm', tag='js')); bk = X.mesh(S('black', 'lm', tag='js'))
    s = sc
    boxm(st, (-70 * s, -36 * s, 0), (70 * s, 36 * s, 20 * s), r=3, tile=64)
    ellipsoid(jg, (-6 * s, 0, 58 * s), 62 * s, 28 * s, 30 * s, nu=16, nv=8)
    sphere(jg, (58 * s, 0, 82 * s), 28 * s, nu=14, nv=8)
    ellipsoid(jg, (82 * s, 0, 74 * s), 14 * s, 16 * s, 12 * s, nu=10, nv=6)
    for sy in (-1, 1):
        sphere(jg, (58 * s, sy * 20 * s, 108 * s), 9 * s, nu=8, nv=4)                     # ears
        sphere(wt, (78 * s, sy * 12 * s, 90 * s), 6 * s, nu=8, nv=4); sphere(bk, (82 * s, sy * 12 * s, 90 * s), 3 * s, nu=6, nv=3)
        tube(jg, [(40 * s, sy * 18 * s, 50 * s), (56 * s, sy * 18 * s, 26 * s), (70 * s, sy * 18 * s, 22 * s)], 10 * s, nseg=8)   # front legs
        ellipsoid(jg, (-44 * s, sy * 22 * s, 40 * s), 26 * s, 12 * s, 22 * s, nu=10, nv=6)                                    # haunches
    tube(jg, [(-66 * s, 0, 50 * s), (-96 * s, 10 * s, 30 * s), (-100 * s, 30 * s, 24 * s), (-80 * s, 40 * s, 22 * s)], [8 * s, 6 * s, 5 * s, 4 * s], nseg=8)
    return save(name, X)


# ================================================================================================= ball court
def ballcourt():
    X = Model()
    s_bench = SB('stucco_red', tag='bc'); s_wall = SB('glyph_wall', tag='bc'); s_top = SB('pavers', tag='bc'); s_out = SB('ashlar', tag='bc')
    s_tread = SB('coping', tag='bc'); s_riser = SB('stucco_red', tag='bcr'); s_end = SB('fret', tag='bc')
    ax0, ay0, ax1, ay1 = L.BC_ALLEY

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[2] < 70 and (c[0] < ax0 - 60 or c[0] > ax1 + 60): return (s_top if n[2] > 0.9 else s_end), arch_uv(n, 128 if n[2] < 0.9 else 512)
        inside = ay0 - L.BC_BENCH[0] - 1 < c[1] < ay1 + L.BC_BENCH[0] + 1
        if 0.3 < n[2] < 0.95: return s_bench, arch_uv(n, 256)
        if n[2] > 0.9:
            if abs(c[1] - L.BC[1]) > L.BC_BENCH[0] + 96 + L.BC_TOP_W + 1: return s_tread, arch_uv(n, 128)
            return s_top, arch_uv(n, 512)
        if abs(n[1]) > 0.9 and abs(c[1] - L.BC[1]) < 96 + L.BC_BENCH[0] + 1: return s_wall, arch_uv(n, 256)
        if abs(c[1] - L.BC[1]) > L.BC_BENCH[0] + 96 + L.BC_TOP_W + 1: return s_riser, arch_uv(n, 128)
        return s_out, arch_uv(n, 256)
    solids_mesh(X, SH.ballcourt(), texfn)
    # stone rings on both walls, facing the alley
    rg = X.mesh(S('stone', 'lm', tag='ring')); gd = X.mesh(S('gold', 'lms', v=0.2, tag='ring'))
    for s in (-1, 1):
        yw = (ay1 if s > 0 else ay0) + s * L.BC_BENCH[0]
        torus(rg, (L.BC[0], yw - s * 10, 150), 30, 10, axis=(0, 1, 0), n=24, m=10, utile=2)
        boxm(gd, (L.BC[0] - 40, yw - s * 2 - 2, 108), (L.BC[0] + 40, yw - s * 2 + 2, 112), r=0.5, tile=64)
    X.shift((L.BC[0], L.BC[1], 0))
    return save('ballcourt', X)


def rubber_ball():
    X = Model()
    sphere(X.mesh(S('rubber', 'lm')), (0, 0, 14), 14, nu=14, nv=8)
    return save('rubber_ball', X)


# ================================================================================================= hall of the eagle warriors
def hall():
    X = Model()
    x0, y0, x1, y1 = L.HALL
    s_roof = SB('pavers', tag='h'); s_ceil = SB('stucco', tag='h'); s_edge = SB('fret_jade', tag='h'); s_wall = SB('painted_wall', tag='h')
    s_back = SB('ashlar_moss', tag='h'); s_tread = SB('coping', tag='h'); s_riser = SB('stucco_red', tag='h'); s_bench = SB('stucco_turq', tag='h')

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[0] > x1 - 0.5:                                            # stair
            if n[2] > 0.9: return s_tread, arch_uv(n, 128)
            return s_riser, arch_uv(n, 128)
        if c[2] > L.HALL_Z - 24.5:
            if n[2] > 0.9: return s_roof, arch_uv(n, 512)
            if n[2] < -0.9: return s_ceil, arch_uv(n, 256)
            return s_edge, (lambda p: ((p[0] + p[1]) / 128.0, (L.HALL_Z - p[2]) / 24.0 * 0.4))
        if c[2] < 33 and c[1] < y1 - 31: return s_bench, arch_uv(n, 128)
        if n[1] < -0.9: return s_wall, (lambda p: (p[0] / 256.0, (L.HALL_Z - 24 - p[2]) / 200.0))
        return s_back, arch_uv(n, 256)
    solids_mesh(X, SH.hall(), texfn)
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('hall', X)


def make_serpent_column(name, h):
    X = Model()
    sc_ = X.mesh(S('scales', 'lm', shade=50, tag='col')); st = X.mesh(S('stone', 'lm', tag='col'))
    revolve(sc_, [(0, 56), (26, 56), (24, h * 0.5), (26, h - 40), (0, h - 40)], n=16, vlen=96)
    boxm(st, (-38, -38, h - 40), (38, 38, h), r=3, tile=64)
    # head at the base: jaws facing -y
    hm = _head_mesh(118, 76, 60)
    R = np.array([[0, 1.0, 0], [-1.0, 0, 0], [0, 0, 1]])                # +x -> -y
    X.add_model(hm, R, (0, 40, 0))
    return save(name, X)


def _head_mesh(L_, W_, H_):
    """serpent head (as serpent_head) returned as a Model without saving"""
    X = Model()
    sk = X.mesh(S('scales', 'lm', shade=50)); wt = X.mesh(S('white', 'lm')); bk = X.mesh(S('black', 'lm')); rd = X.mesh(S('red', 'lm'))
    boxm(sk, (0, -W_ / 2, H_ * 0.42), (L_ * 0.82, W_ / 2, H_), r=10, k=3, tile=96)
    boxm(sk, (L_ * 0.55, -W_ * 0.42, H_ * 0.46), (L_, W_ * 0.42, H_ * 0.86), r=12, k=3, tile=96)
    boxm(sk, (L_ * 0.05, -W_ * 0.44, 0), (L_ * 0.95, W_ * 0.44, H_ * 0.2), r=8, k=2, tile=96)
    boxm(rd, (L_ * 0.15, -W_ * 0.36, H_ * 0.18), (L_ * 0.85, W_ * 0.36, H_ * 0.22), r=1, tile=64)
    boxm(sk, (0, -W_ * 0.46, 0), (L_ * 0.25, W_ * 0.46, H_ * 0.45), r=6, k=2, tile=96)
    for s in (-1, 1):
        cone(wt, (L_ * 0.86, s * W_ * 0.3, H_ * 0.46), (L_ * 0.86, s * W_ * 0.3, H_ * 0.16), 6, 6)
        sphere(wt, (L_ * 0.55, s * W_ * 0.47, H_ * 0.8), W_ * 0.14, nu=10, nv=5)
        sphere(bk, (L_ * 0.58, s * W_ * 0.53, H_ * 0.8), W_ * 0.06, nu=8, nv=4)
    return X


# ================================================================================================= cantina
def cantina():
    X = Model()
    x0, y0, x1, y1 = L.CAN
    Z = L.CAN_H
    s_out = SB('stucco', tag='cn'); s_in = SB('stucco_turq', tag='cn'); s_roof = SB('planks', tag='cn'); s_edge = SB('fret', tag='cn')
    s_tread = SB('red_path', tag='cn'); s_riser = SB('ashlar_red', tag='cn'); s_ctr = SB('turq_mosaic', tag='cn'); s_base = SB('painted_wall', tag='cn')

    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[0] < x0 - 7.5:                                            # outside stair
            if n[2] > 0.9: return s_tread, arch_uv(n, 128)
            return s_riser, arch_uv(n, 128)
        if c[2] > Z - 16.5:
            if n[2] > 0.9: return s_roof, arch_uv(n, 256)
            if n[2] < -0.9: return SB('planks', tag='cnc'), arch_uv(n, 256)
            return s_edge, (lambda p: ((p[0] + p[1]) / 128.0, (Z - p[2]) / 64.0))
        if SH.cantina_inside(c + n * 2): return s_in, arch_uv(n, 256)
        if c[2] < 65 and c[0] > x1 - 25 and y0 + 119 < c[1] < y1 - 119: return s_ctr, arch_uv(n, 128)
        return s_base, (lambda p: ((p[0] + p[1]) / 512.0, (Z - 16 - p[2]) / (Z - 16)))
    solids_mesh(X, SH.cantina(), texfn)
    # thatched awnings over the serving window (east) and the door (north)
    th = X.mesh(S('thatch', 'lm', shade=60)); fr = X.mesh(S('fringe', 'alpha', tag='cn')); wd = X.mesh(S('wood', 'lm', tag='cn'))
    for (a0, a1, side) in (((y0 + 100, y1 - 100), None, 'e'), ((x0 + 170, x0 + 326), None, 'n')):
        u0, u1 = a0
        if side == 'e':
            p = [(x1, u0, 176), (x1, u1, 176), (x1 + 120, u1, 140), (x1 + 120, u0, 140)]
            fp = [(x1 + 120, u0, 140), (x1 + 120, u1, 140), (x1 + 120, u1, 104), (x1 + 120, u0, 104)]
            for yy in (u0 + 8, u1 - 8): cylm(wd, (x1 + 112, yy, 0), 5, 140, n=8)
        else:
            p = [(u0, y1, 176), (u1, y1, 176), (u1, y1 + 110, 144), (u0, y1 + 110, 144)]
            fp = [(u0, y1 + 110, 144), (u1, y1 + 110, 144), (u1, y1 + 110, 108), (u0, y1 + 110, 108)]
            for xx in (u0 + 8, u1 - 8): cylm(wd, (xx, y1 + 102, 0), 5, 144, n=8)
        P = [np.array(q, float) for q in p]
        nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
        if nn[2] < 0: nn = -nn
        th.poly(P, nn, [(0, 0), (np.linalg.norm(P[1] - P[0]) / 128, 0), (np.linalg.norm(P[1] - P[0]) / 128, 1), (0, 1)])
        th.poly(P[::-1], -nn, [(0, 1), (np.linalg.norm(P[1] - P[0]) / 128, 1), (np.linalg.norm(P[1] - P[0]) / 128, 0), (0, 0)])
        F = [np.array(q, float) for q in fp]
        fn = np.cross(F[1] - F[0], F[3] - F[0]); fn /= np.linalg.norm(fn)
        ln = np.linalg.norm(F[1] - F[0]) / 128
        fr.poly(F, fn, [(0, 0), (ln, 0), (ln, 1), (0, 1)])
    # counter top + bottles on the back shelf, menu board
    boxm(X.mesh(S('wood_light', 'lm', tag='cn')), (x1 - 40, y0 + 120, 64), (x1 + 16, y1 - 120, 70), r=1, tile=128)
    sh = X.mesh(S('wood', 'lm', tag='cs'))
    boxm(sh, (x0 + 24, y0 + 120, 120), (x0 + 48, y1 - 120, 126), r=1, tile=128)
    for k in range(12):
        yy = y0 + 140 + k * ((y1 - y0 - 280) / 11)
        revolve(X.mesh(S('bottle_g' if k % 3 else 'bottle_b', 'lm', tag='cn')), [(0, 126), (6, 126), (6, 146), (2, 152), (2, 158), (0, 158)],
                n=8, cx=x0 + 36, cy=yy)
    picture(X.mesh(S('menu', 'lm')), (x0 + 25, (y0 + y1) / 2, 160), 120, 64, (1, 0, 0))
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('cantina', X)


def stool():
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='st')); cu = X.mesh(S('canvas_a', 'lm', tag='st'))
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(wd, [(10 * math.cos(a), 10 * math.sin(a), 0), (4 * math.cos(a), 4 * math.sin(a), 40)], 2.5, nseg=6)
    cylm(cu, (0, 0, 40), 13, 5, n=14)
    return save('stool', X)


# ================================================================================================= props
def palm(name, h, lean=(0.25, 0.0), nf=11, seed=1):
    """coconut palm: curved ringed trunk, fronds (alpha, vertex lit) and coconuts; origin trunk base"""
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


def agave(name, r=60.0, seed=3):
    """maguey (agave): rosette of thick tapering leaves; origin base"""
    X = Model()
    ag = X.mesh(S('agave', 'lm', shade=50))
    rng = np.random.default_rng(seed)
    for ring_, (n, tilt, ln) in enumerate(((9, 0.35, 1.0), (7, 0.9, 0.8), (5, 1.3, 0.6))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * ring_) / n + rng.uniform(-0.1, 0.1)
            d = np.array([math.cos(a) * math.cos(tilt), math.sin(a) * math.cos(tilt), math.sin(tilt)])
            L_ = r * ln * rng.uniform(0.85, 1.15)
            base = np.array([0, 0, 6])
            path = [base + d * L_ * t + np.array([0, 0, -L_ * 0.15 * t * t]) for t in np.linspace(0, 1, 5)]
            tube(ag, path, np.linspace(8 * ln + 3, 0.6, 5), nseg=4, ry=np.linspace(3, 0.4, 5), vlen=64)
    return save(name, X)


def monstera(name, n=7, h=80.0, seed=5):
    X = Model()
    lv = X.mesh(S('monstera', 'alpha', vs=1.1)); stg = X.mesh(S('agave', 'lm', tag='m'))
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
        d = np.array([math.cos(a), math.sin(a), 0])
        hh = h * rng.uniform(0.6, 1.0)
        top = d * hh * 0.4 + np.array([0, 0, hh])
        tube(stg, [(0, 0, 0), top * 0.5 + [0, 0, hh * 0.1], top], 1.6, nseg=4)
        s = hh * 0.55
        side = np.array([-d[1], d[0], 0])
        tip = top + d * s * 0.9 - np.array([0, 0, s * 0.3])
        p0 = top - side * s / 2; p1 = top + side * s / 2; p2 = tip + side * s / 2; p3 = tip - side * s / 2
        nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
        if nn[2] < 0: nn = -nn
        quad_uv(lv, p0, p1, p2, p3, [(0, 0), (1, 0), (1, 1), (0, 1)], nn)
    return save(name, X)


def parasol(name='parasol', h=150.0, r=96.0):
    """palapa parasol: wooden pole, thatched cone with a ragged fringe; origin pole base"""
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='pa')); th = X.mesh(S('thatch', 'lm', shade=60, tag='pa')); fr = X.mesh(S('fringe', 'alpha', tag='pa'))
    cylm(wd, (0, 0, 0), 4, h + 30, n=8)
    revolve(th, [(0, h + 46), (r * 0.5, h + 24), (r, h)], n=16, u_tiles=4, vlen=64)
    revolve(th, [(r, h), (r * 0.5, h + 24), (0, h + 46)], n=16, u_tiles=4, vlen=64)
    n = 16
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = np.array([r * math.cos(a0), r * math.sin(a0), h]); p1 = np.array([r * math.cos(a1), r * math.sin(a1), h])
        nn = np.array([math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0])
        quad_uv(fr, p0, p1, p1 - [0, 0, 26], p0 - [0, 0, 26], [(0, 0), (1, 0), (1, 1), (0, 1)], nn)
    return save(name, X)


def lounger(name='lounger', cv='canvas_a'):
    """wooden sun lounger with a striped pad (64 long along x); origin floor centre"""
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


def innertube(name, img_):
    X = Model()
    torus(X.mesh(S(img_, 'lm', shade=70)), (0, 0, 9), 24, 9, n=24, m=10, utile=6)
    return save(name, X)


def tube_rack():
    """stack of inner tubes on a wooden rack; origin floor centre"""
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='tr'))
    for (x, y) in ((-34, -34), (34, -34), (-34, 34), (34, 34)):
        cylm(wd, (x, y, 0), 3, 100, n=6)
    for k in range(5):
        torus(X.mesh(S('tube_a' if k % 2 else 'tube_b', 'lm', shade=70, tag='tr')), (0, 0, 9 + 18 * k), 26, 9, n=20, m=8, utile=6)
    return save('tube_rack', X)


def lifeguard():
    """lifeguard tower painted like a little temple (seat, ladder, sun shade); origin floor centre"""
    X = Model()
    wd = X.mesh(S('wood', 'lm', tag='lg')); rd = X.mesh(S('red', 'lm', tag='lg')); cv = X.mesh(S('canvas_b', 'lm', tag='lg'))
    for (x, y) in ((-24, -24), (24, -24), (-24, 24), (24, 24)):
        tube(wd, [(x * 1.3, y * 1.3, 0), (x, y, 90)], 3, nseg=6)
    boxm(rd, (-30, -30, 90), (30, 30, 96), r=1, tile=64)
    boxm(wd, (-20, -20, 96), (20, 20, 120), r=2, tile=64)
    for k in range(6):
        boxm(wd, (-14, -40 - k * 6, 15 * k), (14, -36 - k * 6, 15 * k + 3), r=0.5, tile=32)
    for (x, y) in ((-26, -26), (26, -26), (-26, 26), (26, 26)):
        cylm(wd, (x, y, 96), 1.5, 70, n=6)
    revolve(cv, [(0, 180), (40, 166)], n=4, a0=45, a1=405, u_tiles=4, vlen=64)
    revolve(cv, [(40, 166), (0, 180)], n=4, a0=45, a1=405, u_tiles=4, vlen=64)
    return save('lifeguard', X)


def stele(name, h=200.0, w=80.0, glyph='glyph_wall'):
    """carved stone stela with a relief panel on both faces; origin floor centre, faces +-y"""
    X = Model()
    st = X.mesh(S('stone', 'lm', tag='se'))
    boxm(st, (-w / 2 - 10, -20, 0), (w / 2 + 10, 20, 16), r=2, tile=64)
    boxm(st, (-w / 2, -12, 16), (w / 2, 12, h), r=3, k=2, tile=64)
    g = X.mesh(SB(glyph, tag='se'))
    for s in (-1, 1):
        picture(g, (0, s * 12.5, 16 + (h - 16) / 2), w - 12, h - 30, (0, s, 0))
    return save(name, X)


def boulder(name, r=60.0, seed=7, tex='moss_rock'):
    X = Model()
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    bump = lambda p, t: 1 + 0.12 * math.sin(3 * t + ph[0]) * math.cos(2 * p + ph[1]) + 0.08 * math.sin(5 * t + ph[2])
    ellipsoid(X.mesh(S(tex, 'lm', shade=70)), (0, 0, r * 0.45), r, r * 0.8, r * 0.6, nu=18, nv=10, bump=bump, flat_bottom=-r * 0.45)
    return save(name, X)


def ruin_block(name, seed=9):
    """fallen carved blocks / column drums (cover); origin floor centre, roughly 160 x 90 x 80"""
    X = Model()
    st = X.mesh(SB('ashlar_moss', tag='rb')); gl = X.mesh(SB('glyph_wall', tag='rb')); cl = X.mesh(S('stone', 'lm', tag='rb'))
    boxm(st, (-80, -44, 0), (40, 44, 64), r=4, k=2, tile=128)
    boxm(gl, (-30, -36, 64), (50, 36, 104), r=3, k=2, tile=128)
    rr = Mesh(); revolve(rr, [(0, 0), (30, 0), (30, 70), (0, 70)], n=16, vlen=64)
    cl.add(rr, rot_axis((1, 0, 0), math.pi / 2), (70, 40, 30))
    return save(name, X)


def vines(name, n=10, length=300.0, r=380.0, a0=0.0, a1=360.0, seed=11):
    """hanging vines round a circular rim (cenote): crossed alpha strips; origin = rim centre at the rim height"""
    X = Model()
    vn = X.mesh(S('vine', 'alpha', vs=1.1, deform='wave 100 sin 0 3 0 0.4'))
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * (k + rng.uniform(0.1, 0.9)) / n)
        ln = length * rng.uniform(0.6, 1.0)
        p = np.array([r * math.cos(a), r * math.sin(a), 0])
        inw = -np.array([math.cos(a), math.sin(a), 0])
        side = np.array([-math.sin(a), math.cos(a), 0])
        w = 16
        for d in (side, (side + inw) / np.linalg.norm(side + inw)):
            quad_uv(vn, p - d * w + inw * 6, p + d * w + inw * 6, p + d * w + inw * 14 - [0, 0, ln], p - d * w + inw * 14 - [0, 0, ln],
                    [(0, 0), (1, 0), (1, ln / 256), (0, ln / 256)], inw)
    return save(name, X)


def waterspout():
    """stone serpent head poking out of the cenote wall, water arcing out of its mouth (faces +x); origin at the wall"""
    X = _head_mesh(110, 70, 64)
    wf = X.mesh(S('water_strip', 'flow', speed=-1.8, tag='ws'))
    P = [np.array([110 + 60 * t, 0, 28 - 280 * t * t]) for t in np.linspace(0, 1, 12)]
    sweep(wf, P, [(-22, 0), (22, 0)], vlen=128)
    return save('waterspout', X)


def secret_mouth():
    """serpent jaws framing the 96 x 96 underwater tunnel (faces +x, the tunnel runs -x into the wall): upper jaw over the
    opening with fangs, eyes and brow above, lower jaw lip on the floor; origin = tunnel floor centre at the wall"""
    X = Model()
    sk = X.mesh(S('scales_gold', 'lm', shade=50)); wt = X.mesh(S('white', 'lm', tag='sm')); bk = X.mesh(S('black', 'lm', tag='sm'))
    gl = X.mesh(S('jade', 'glow' if False else 'lm', tag='sm'))
    boxm(sk, (0, -84, 96), (60, 84, 150), r=14, k=3, tile=96)                             # upper jaw
    boxm(sk, (0, -84, 0), (54, 84, 12), r=4, k=2, tile=96)                                 # lower jaw lip
    for s in (-1, 1):
        boxm(sk, (0, s * 66 - 18, 12), (40, s * 66 + 18, 96), r=8, k=2, tile=96)          # cheeks
        for yy in (30, 10):
            cone(wt, (44, s * yy, 98), (46, s * yy, 70 - (10 if yy > 20 else 0)), 7, 6)
        sphere(wt, (40, s * 46, 160), 18, nu=12, nv=6); sphere(bk, (52, s * 46, 160), 8, nu=8, nv=4)
        boxm(sk, (20, s * 46 - 26, 176), (64, s * 46 + 26, 190), r=4, tile=64)
    return save('secret_mouth', X)


# ================================================================================================= treasure (secret room)
def gold_heap(name='gold_heap', r=80.0, seed=13):
    X = Model()
    gd = X.mesh(S('gold', 'lms', v=0.3, tag='gh')); jd = X.mesh(S('jade', 'lms', v=0.2, tag='gh'))
    rng = np.random.default_rng(seed)
    ellipsoid(gd, (0, 0, 0), r, r * 0.8, r * 0.45, nu=18, nv=8, flat_bottom=0)
    for k in range(14):
        a = rng.uniform(0, 6.28); d = rng.uniform(0.2, 0.85) * r
        z = r * 0.45 * math.sqrt(max(0, 1 - (d / r) ** 2))
        cylm(gd if k % 3 else jd, (d * math.cos(a), d * math.sin(a) * 0.8, z - 2), rng.uniform(8, 14), 3, n=10)
    return save(name, X)


def gold_mask():
    """turquoise mosaic mask on a gold stand (faces -y); origin floor centre"""
    X = Model()
    tq = X.mesh(SB('turq_mosaic', tag='gm')); gd = X.mesh(S('gold', 'lms', v=0.3, tag='gm')); wt = X.mesh(S('white', 'lm', tag='gm')); bk = X.mesh(S('black', 'lm', tag='gm'))
    boxm(gd, (-30, -30, 0), (30, 30, 60), r=3, tile=64)
    ellipsoid(tq, (0, 0, 110), 40, 18, 50, nu=16, nv=10)
    for s in (-1, 1):
        sphere(wt, (s * 15, -14, 122), 7, nu=8, nv=4); sphere(bk, (s * 15, -19, 122), 3, nu=6, nv=3)
    boxm(wt, (-14, -18, 86), (14, -14, 92), r=1, tile=32)
    return save('gold_mask', X)


# ================================================================================================= the feathered serpent (mover, IQM)
def quetzalcoatl():
    """Quetzalcoatl flying a circle round the pyramid: a long undulating body with scales and feathers, a plumed head
    and wings of feathers, already placed on the circle (radius QUETZ_R round the func_rotating origin, z 0 = the
    origin height). Positive func_rotating speed turns it counter-clockwise, so it faces along +angle."""
    X = Model()
    body = S('scales', 'dyn', tag='q'); fe = S('feather', 'dynalpha', tag='q'); fr = S('feather_red', 'dynalpha', tag='q')
    gd = S('gold', 'dyn', tag='q'); wt = S('white', 'dyn', tag='q'); bk = S('black', 'dyn', tag='q')
    R = L.QUETZ_R
    a_head = 0.0; span = math.radians(48)                         # body trails behind the head (clockwise)
    N = 60
    P = []; rad = []
    for i in range(N):
        t = i / (N - 1)
        a = a_head - span * t
        rr = R + 60 * math.sin(t * 4 * math.pi)
        z = 70 * math.sin(t * 3 * math.pi + 0.6)
        P.append(np.array([rr * math.cos(a), rr * math.sin(a), z]))
        rad.append(26 * (1 - 0.75 * t) + 4)
    tube(X.mesh(body), P, rad, nseg=12, vlen=96)
    # feather tufts along the back
    for i in range(3, N - 4, 4):
        c = P[i]; d = P[i + 1] - P[i - 1]; d /= np.linalg.norm(d)
        up = np.array([0, 0, 1.0]); side = np.cross(d, up); side /= np.linalg.norm(side)
        for s in (-1, 1):
            base = c + side * s * rad[i] * 0.8 + up * rad[i] * 0.4
            dirv = side * s * 0.8 + up * 0.5 - d * 0.4; dirv /= np.linalg.norm(dirv)
            w = 10; ln = 60 * (1 - i / N) + 24
            q = np.cross(dirv, d); q /= np.linalg.norm(q)
            p0 = base - d * w; p1 = base + d * w; p2 = p1 + dirv * ln; p3 = p0 + dirv * ln
            nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
            quad_uv(X.mesh(fr if (i // 4) % 3 == 0 else fe), p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    # wings (two big feather fans behind the head)
    c = P[6]; d = P[0] - P[12]; d /= np.linalg.norm(d)
    side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
    for s in (-1, 1):
        for k in range(9):
            a = math.radians(-20 + k * 12)
            dirv = side * s * math.cos(a) + np.array([0, 0, 1.0]) * math.sin(a) * 0.8 - d * 0.3; dirv /= np.linalg.norm(dirv)
            base = c + side * s * 20
            p0 = base - d * 16; p1 = base + d * 16; p2 = p1 + dirv * 190; p3 = p0 + dirv * 190
            nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
            quad_uv(X.mesh(fe if k % 2 else fr), p0, p1, p2, p3, [(0, 1), (1, 1), (1, 0), (0, 0)], nn)
    # head: snout box aligned with the travel direction, open jaws, gold plume crown
    h = P[0]; fwd = np.array([-math.sin(a_head), math.cos(a_head), 0.0])
    Rh = np.stack([fwd, np.cross([0, 0, 1.0], fwd), [0, 0, 1.0]], 1)       # local x -> fwd
    hm = _head_mesh(110, 70, 64)
    for sh, Mm in hm.m.items():
        k = sh.split('/')[-1]
        tgt = body if 'scales' in k else (wt if 'white' in k else (bk if 'black' in k else gd))
        X.mesh(tgt).add(Mm, Rh, h - fwd * 30 - [0, 0, 30])
    return save_iqm('quetzalcoatl', X)


# ================================================================================================= make all
def make():
    make_textures()
    pyramid(); shrine(); idol(); chacmool(); brazier(); brazier('brazier_big', 110, 52)
    serpent_head('serpent_head'); tube_head(); eagle_head()
    serpent_tube(L.serpent_path(), SUPPORTS['tube']); flume(L.flume_path(), SUPPORTS['flume'])
    sunstone(); tlaloc_head(); jaguar_temple(); jaguar_statue(); ballcourt(); rubber_ball(); hall()
    make_serpent_column('serpent_col', L.HALL_Z - 24)
    cantina(); stool()
    palm('palm_a', 300, (0.22, 0.05), 11, 1); palm('palm_b', 380, (-0.05, 0.25), 12, 2); palm('palm_c', 240, (0.15, -0.18), 10, 3)
    agave('agave_a', 60, 3); agave('agave_b', 90, 4); monstera('monstera_a', 7, 80, 5); monstera('monstera_b', 9, 110, 6)
    parasol(); lounger('lounger_a', 'canvas_a'); lounger('lounger_b', 'canvas_b'); innertube('itube_a', 'tube_a'); innertube('itube_b', 'tube_b')
    tube_rack(); lifeguard(); stele('stele_a'); stele('stele_b', 260, 96, 'glyph_wall')
    boulder('boulder_a', 60, 7); boulder('boulder_b', 90, 8); boulder('boulder_c', 130, 9); ruin_block('ruin_a', 9)
    vines('cenote_vines', 9, 260, L.CEN_R - 6, 132, 292, 11); waterspout(); secret_mouth()
    gold_heap('gold_heap', 80, 13); gold_heap('gold_heap_s', 50, 14); gold_mask()
    quetzalcoatl()


SUPPORTS = {'tube': [], 'flume': []}
