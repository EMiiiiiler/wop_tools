"""Shared helpers for the Backyard BBQ model/texture generators: MD3 shader registry, Model container, procedural
image helpers (tileable noise etc.). All art is original and generated here."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, save_md3
import iqmtool

NS = 'padbbq'
MD = f'models/{NS}'
TD = f'textures/{NS}'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
if not os.path.exists(FONTS): FONTS = FONTB

STATE = {'out': None}
REG = {}            # shader name -> (image, kind, options)
PLACE = {}          # model name -> (path, scale, zoff)
IQM = {}            # mover name -> path


def out(*p): return os.path.join(STATE['out'], *p)


def S(img, kind='lm', **opt):
    """register an MD3 shader for image `img` (models/padhalloween/<img>) of a given kind; returns the shader name"""
    key = f'{img}_{kind}{opt.get("tag", "")}'.replace('/', '_')
    name = f'{MD}/{key}'
    REG[name] = (img, kind, opt)
    return name


class Model:
    def __init__(self): self.m = {}

    def mesh(self, shader):
        if shader not in self.m: self.m[shader] = Mesh()
        return self.m[shader]

    def surfaces(self):
        return [M.surface(f's{i}', sh) for i, (sh, M) in enumerate(self.m.items()) if len(M)]

    def shift(self, o):
        o = np.asarray(o, float)
        for M in self.m.values(): M.V = [v - o for v in M.V]
        return self

    def add_model(self, other, R=np.eye(3), t=(0, 0, 0), sc=1.0):
        for sh, M in other.m.items(): self.mesh(sh).add(M, R, t, sc)
        return self


def cross_sprites(X):
    """flame quads (shaders registered with deform autosprite2) become crossed quads: q3map2 bakes misc_model
    surfaces into the BSP as one surface per shader, and autosprite2 only works on single quads"""
    for sh, M in X.m.items():
        if sh not in REG or REG[sh][2].get('deform') != 'autosprite2' or len(M.V) % 4: continue
        n0 = len(M.V)
        for o in range(0, n0, 4):
            P = [np.asarray(M.V[o + k]) for k in range(4)]
            c = sum(P) / 4
            R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
            q = [R @ (p - c) + c for p in P]
            nn = R @ np.asarray(M.N[o])
            base = len(M.V)
            for k in range(4): M.add_v(q[k], nn, M.ST[o + k])
            M.tri(base, base + 1, base + 2); M.tri(base, base + 2, base + 3)


def save(name, X):
    path = f'{MD}/{name}.md3'
    cross_sprites(X)
    os.makedirs(out(MD), exist_ok=True)
    sc, zo = save_md3(out(path), X.surfaces(), name, with_offset=True)
    PLACE[name] = (path, sc, zo)
    return path, sc, zo


def save_iqm(name, X):
    """static IQM for movers (float vertices, any extent); chunks under the renderer's ~1000-vertex limit"""
    meshes = []
    for i, (sh, Mm) in enumerate(X.m.items()):
        if not len(Mm): continue
        V, Nn, ST, T = np.array(Mm.V), np.array(Mm.N), np.array(Mm.ST), np.array(Mm.T)
        k0 = 0; part = 0
        while k0 < len(T):
            k1 = k0; used = {}
            while k1 < len(T) and len(set(used) | set(T[k1].tolist())) < 990:
                for v in T[k1].tolist(): used.setdefault(v, len(used))
                k1 += 1
            idx = np.array(sorted(used, key=used.get))
            remap = {v: j for j, v in enumerate(idx)}
            tt = np.vectorize(remap.get)(T[k0:k1])
            meshes.append(dict(name=f'{name}{i}_{part}', material=sh, verts=V[idx], normals=Nn[idx], st=ST[idx], tris=tt))
            k0 = k1; part += 1
    path = f'{MD}/{name}.iqm'
    os.makedirs(out(MD), exist_ok=True)
    iqmtool.save(out(path), meshes)
    IQM[name] = path
    return path


# ================================================================================================= image helpers
def noise(n, blur, seed, m=None):
    """tileable gaussian-blurred noise, zero mean / unit std"""
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, m * 3))
    for i in range(3):
        for j in range(3): big.paste(im, (i * n, j * m))
    a = np.asarray(big.filter(ImageFilter.GaussianBlur(blur)).crop((n, m, 2 * n, 2 * m)), np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def N3(n, blur, seed, amp, m=None): return noise(n, blur, seed, m)[..., None] * amp
def C(c): return np.array(c, np.float32)
def lerp(a, b, t): return a + (b - a) * t
def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def xy(n, m=None):
    m = m or n
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    return x / n, y / m


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def emboss(h, k=1.0):
    gx = np.roll(h, -1, 1) - np.roll(h, 1, 1); gy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    return np.clip(0.85 + k * (gx * 0.6 - gy * 0.8), 0.35, 1.4)


def voronoi(n, cells, seed, m=None):
    """tileable Voronoi: (cell id, distance to edge) per pixel"""
    m = m or n
    r = np.random.default_rng(seed)
    P = r.random((cells, 2))
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    x /= n; y /= m
    best = np.full((m, n), 9.0); second = np.full((m, n), 9.0); idx = np.zeros((m, n), int)
    for i, (px, py) in enumerate(P):
        dx = np.abs(x - px); dx = np.minimum(dx, 1 - dx)
        dy = np.abs(y - py); dy = np.minimum(dy, 1 - dy)
        d = np.hypot(dx, dy)
        mm = d < best
        second = np.where(mm, best, np.minimum(second, d)); idx = np.where(mm, i, idx); best = np.where(mm, d, best)
    return idx, second - best


def font(sz, serif=True):
    return ImageFont.truetype(FONTS if serif else FONTB, sz)


def text_img(text, w, h, bg, fg, serif=True, size=None, border=None, glow=None, wobble=0):
    im = Image.new('RGB', (w, h), tuple(int(v) for v in bg))
    d = ImageDraw.Draw(im)
    lines = text.split('\n')
    sz = size or int(h * 0.8 / len(lines))
    while sz > 8:
        f = font(sz, serif)
        wid = max(d.textbbox((0, 0), l, font=f)[2] for l in lines)
        if wid <= w * 0.9: break
        sz -= 2
    f = font(sz, serif)
    tot = len(lines) * sz * 1.15
    y = (h - tot) / 2
    for l in lines:
        bb = d.textbbox((0, 0), l, font=f)
        x = (w - (bb[2] - bb[0])) / 2 - bb[0]
        if glow is not None:
            g = Image.new('L', (w, h), 0); ImageDraw.Draw(g).text((x, y), l, font=f, fill=255)
            g = g.filter(ImageFilter.GaussianBlur(sz / 6))
            a = np.asarray(im, np.float32) + np.asarray(g, np.float32)[..., None] / 255 * C(glow) * 0.8
            im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
        d.text((x, y), l, font=f, fill=tuple(int(v) for v in fg))
        y += sz * 1.15
    if border is not None:
        d.rectangle((2, 2, w - 3, h - 3), outline=tuple(int(v) for v in border), width=max(2, h // 32))
    return np.asarray(im, np.float32)


def save_img(path, a, alpha=None, quality=92):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = a if isinstance(a, Image.Image) else img(a).convert('RGB')
    if alpha is not None:
        im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
        im.save(path + '.tga')
    else:
        im.convert('RGB').save(path + '.jpg', quality=quality)
    return im.size
