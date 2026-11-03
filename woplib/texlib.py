"""woplib.texlib - procedural texture generators + one registry that writes each image AND its shader.

Every map used to declare a brush texture three times (the image write, a TEX name list, a steps dict in shader())
and model textures twice (ML.T + ML.S, with a hand-rolled lathe flip). One call now does all of it:

    from woplib import texlib as TL
    TX = TL.Textures(K)                                  # after ML.configure / SH.configure
    TX.add('floor', TL.checker((228, 226, 220), (40, 42, 48), 4), steps='woodsteps', scale=1.0)
    TX.add('ice', TL.stone((170, 210, 236), cells=30), kind='slick', steps='snowsteps')
    TX.add('neon_bar', TL.neon('OPEN', (255, 60, 150)), kind='neon', rgb=(1, 0.3, 0.6), light=300)
    cola = TX.material('cola', TL.label('PAD COLA', 256, 512, (60, 24, 14), (255, 255, 255), band=(0.4, 0.65)),
                       'lms', v=0.25, lathe=True)        # -> model shader name for X.mesh(cola)
    ...
    TX.write_shader(extra=[SH.sky(...)])                 # brush shaders + model shaders + levelshots, then the arena

Generators return float RGB arrays (H, W, 3), tileable unless noted, all original procedural art. Pass `seed` for a
different variant of the same look; colours are always parameters, so maps keep their own palette.
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from . import models as ML, shaders as SH
import wopmap

C, fill, N3, xy, noise, lerp = ML.C, ML.fill, ML.N3, ML.xy, ML.noise, ML.lerp


# ================================================================================================= generators
def solid(col, grain=4, seed=0, n=128):
    """plain colour with fine + broad noise (plastic, paint, liner)"""
    return fill(n, col, grain, seed)


def checker(c1, c2, n_tiles=4, grout=(120, 118, 112), grout_w=0.02, seed=21, n=256):
    """checkerboard tiles (kitchen, diner, chess floor)"""
    x, y = xy(n)
    chk = ((np.floor(x * n_tiles) + np.floor(y * n_tiles)) % 2).astype(bool)
    c = np.where(chk[..., None], C(c1), C(c2)) + N3(n, 1.5, seed, 5)
    g = ((x * n_tiles) % 1 < grout_w) | ((y * n_tiles) % 1 < grout_w)
    return np.where(g[..., None], C(grout), c)


def tiles(col, grout=(150, 156, 164), cols=4, rows=8, offset=0.5, grout_w=0.04, vary=6, seed=31, n=256):
    """rectangular tiles in rows; offset 0.5 = subway/running bond, 0 = grid. vary = per-tile colour jitter"""
    x, y = xy(n)
    row = np.floor(y * rows)
    u = x * cols + (row % 2) * offset
    tid = np.floor(u) + row * 97
    jit = (np.sin(tid * 12.9898) * 43758.5453) % 1
    c = fill(n, col, 3, seed) + (jit[..., None] - 0.5) * vary * 2
    g = ((y * rows) % 1 < grout_w * rows / cols) | ((u % 1) < grout_w)
    return np.where(g[..., None], C(grout), c)


def bricks(col=(150, 70, 52), mortar=(190, 180, 166), rows=8, cols=4, vary=18, seed=41, n=256):
    """running-bond brick with per-brick tone and soot noise"""
    c = tiles(col, mortar, cols, rows, 0.5, 0.05, vary, seed, n)
    return c + N3(n, 0.8, seed + 1, 8)


def planks(col=(150, 104, 62), n_planks=6, gap=(70, 46, 28), grain=10, stagger=True, vertical=False, seed=51, n=256):
    """floorboards / wall boarding: grain along the planks, dark seams, staggered butt joints"""
    x, y = xy(n)
    p = np.floor(y * n_planks)
    tone = ((np.sin(p * 7.31) * 4375.85) % 1 - 0.5) * 22
    g = np.sin((x * 3 + noise(n, 6, seed) * 0.15 + p * 0.37) * 2 * math.pi * 6) * grain * 0.5
    c = fill(n, col, 4, seed + 1) + (tone + g)[..., None] + N3(n, 0.6, seed + 2, 5)
    seam = (y * n_planks) % 1 < 0.04
    if stagger: seam |= (np.abs(((x + (p % 3) / 3.0) % 1) - 0.5) < 0.006)
    c = np.where(seam[..., None], C(gap), c)
    return np.transpose(c, (1, 0, 2)) if vertical else c


def stone(col=(150, 146, 140), cells=24, edge=(90, 86, 82), edge_w=0.012, vary=14, seed=61, n=256):
    """irregular flagstones / crazy paving / ice cells (Voronoi). edge brighter than col = frost or crackle glaze"""
    idx, d = ML.voronoi(n, cells, seed)
    c = fill(n, col, 6, seed + 1) + (((idx * 37) % 11) / 10.0 - 0.5)[..., None] * vary * 2
    return np.where((d < edge_w)[..., None], C(edge), c)


def metal(col=(186, 190, 198), brushed=True, seed=71, n=256):
    """brushed or plain metal (use the 'lms' model kind or a chrome stage for shine)"""
    if not brushed: return fill(n, col, 3, seed) + N3(n, 30, seed + 1, 6)
    st = noise(n, 0.5, seed) * 0.2 + np.repeat(noise(n, 3, seed + 1)[:, :1], n, 1) * 0.8
    return np.zeros((n, n, 3), np.float32) + C(col) + st[..., None] * 10 + N3(n, 30, seed + 2, 6)


def fabric(col=(120, 60, 70), weave=64, seed=81, n=256):
    """woven cloth / carpet / towel"""
    x, y = xy(n)
    w = (np.sin(x * weave * math.pi) * np.sin(y * weave * math.pi))
    return fill(n, col, 5, seed) + w[..., None] * 10 + N3(n, 0.5, seed + 1, 8)


def stripes(c1, c2, n_stripes=8, vertical=True, soft=0.0, seed=91, n=256):
    """awnings, wallpaper, deck chairs, candy"""
    x, y = xy(n)
    t = (x if vertical else y) * n_stripes
    s = (np.floor(t) % 2)
    if soft: s = np.clip(0.5 + 0.5 * np.sin(t * math.pi) / soft, 0, 1)
    return lerp(C(c1), C(c2), s[..., None]) + N3(n, 1, seed, 3)


def dots(base, dot, n_dots=6, r=0.18, seed=95, n=256):
    """polka dots on a grid (r as a fraction of the cell)"""
    x, y = xy(n)
    fx, fy = (x * n_dots) % 1 - 0.5, (y * n_dots + (np.floor(x * n_dots) % 2) * 0.5) % 1 - 0.5
    m = fx * fx + fy * fy < r * r
    return np.where(m[..., None], C(dot), fill(n, base, 3, seed))


def frost(col=(226, 238, 246), seed=103, n=256):
    """frosty liner / snow crust: pale noise with white crystal edges"""
    return stone(col, 40, (255, 255, 255), 0.008, 6, seed, n) + N3(n, 0.7, seed + 2, 12)


def grime(arr, amount=0.25, seed=111, dark=(40, 34, 28)):
    """darken an existing texture with blotchy dirt (used, lived-in look)"""
    n = arr.shape[0]
    m = np.clip(noise(arr.shape[1], 10, seed, arr.shape[0]) * 0.5 + 0.3, 0, 1)[..., None] * amount
    return arr * (1 - m) + C(dark) * m


def neon(text, rgb, w=512, h=256, board=(8, 8, 14), serif=False):
    """glowing tube lettering on a near-black board (additive neon on a bright backing washes out). NOT tileable."""
    return ML.text_img(text, w, h, board, rgb, serif=serif, glow=rgb, border=tuple(int(v * 0.6) for v in rgb))


def label(text, w, h, bg, fg, band=None, band_bg=None, serif=False, border=None):
    """product label / sign, text auto-fitted on one line per '\\n' (one line on a 4:1 sign). band = (v0, v1): put
    the text only in that vertical band of a taller image (bottle/can wrap); band_bg fills the band. NOT tileable."""
    if band is None:
        return ML.text_img(text, w, h, bg, fg, serif=serif, border=border)
    out = np.zeros((h, w, 3), np.float32) + C(bg) + N3(w, 1, 7, 3, h)
    r0, r1 = int(band[0] * h), int(band[1] * h)
    out[r0:r1] = ML.text_img(text, w, r1 - r0, band_bg or bg, fg, serif=serif, border=border)
    return out


def jumppad_disc(rgb=(90, 200, 255), rubber=(60, 60, 70), n=256):
    """the kit's default pad top (rings + arrows); override per theme (donut, flower, hatch...)"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C(rubber)
    ring = (np.abs(rr - 0.40) < 0.04) | (np.abs(rr - 0.22) < 0.03)
    c = np.where(ring[..., None], C(rgb), c)
    arrows = (np.sin(a * 6) > 0.75) & (rr > 0.26) & (rr < 0.36)
    c = np.where(arrows[..., None], C(rgb) * 0.8 + 50, c)
    return np.where((rr < 0.1)[..., None], C((250, 250, 250)), c) + N3(n, 1, 3, 4)


def is_tileable(arr, tol=6.0):
    """does the wrap seam look like any other column/row boundary in the image? (grout and plank seams on the edge are
    fine; a hard colour jump that appears nowhere else means the generator forgot to wrap)"""
    a = np.asarray(arr, np.float32)
    cols = np.abs(np.diff(a, axis=1)).mean(axis=(0, 2)); rows = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    sx = np.abs(a[:, 0] - a[:, -1]).mean(); sy = np.abs(a[0] - a[-1]).mean()
    return sx <= np.percentile(cols, 99) + tol and sy <= np.percentile(rows, 99) + tol


# ================================================================================================= registry
BRUSH_KINDS = ('lm', 'sign', 'slick', 'neon', 'glass', 'water', 'fog', 'pulse', 'jumppad', 'raw')


class Textures:
    """writes each texture once and remembers how to shade it. kinds for brush textures:
       lm (default; steps=), sign (no decals), slick (ice; glint=), neon (rgb=, light=), glass (rgb=, shadow=, solid=),
       water (rgb=, alpha=, fog=; also writes <name>_nd for internal faces), fog (rgb=, dist=), pulse (phase=, freq=),
       jumppad (rgb=), raw (shader=<stanza text> you write yourself).
    scale=(sx, sy) or a number sets wopmap.TEXSCALE (world units per texel) for every brush face using it."""

    def __init__(self, K=None, ns=None, out=None):
        self.ns = ns or (K.ns if K else SH.CFG['ns'])
        self.out = out or ML.STATE['out']
        assert self.out, 'call ML.configure(ns, out) first (or pass out=)'
        self.brush = {}            # name -> (kind, opts, size)
        self.mats = {}             # key -> model shader name
        self.extra = []

    def path(self, name): return os.path.join(self.out, 'textures', self.ns, name)

    def add(self, name, arr, kind='lm', alpha=None, scale=None, check_tile=True, **opt):
        """brush texture <ns>/<name>; returns the .map texture name"""
        assert name == name.lower(), f'texture names must be lower case: {name}'
        assert kind in BRUSH_KINDS, f'kind {kind} not in {BRUSH_KINDS}'
        if name in self.brush: raise ValueError(f'texture {name} added twice')
        if check_tile and kind in ('lm', 'slick') and not is_tileable(arr):
            print(f'  note: texture {name} does not tile (visible seams on big faces); pass check_tile=False if intended')
        size = ML.save_img(self.path(name), arr, alpha)
        self.brush[name] = (kind, opt, size, alpha is not None)
        if scale is not None:
            wopmap.TEXSCALE[f'{self.ns}/{name}'] = (scale, scale) if np.isscalar(scale) else tuple(scale)
        return f'{self.ns}/{name}'

    def material(self, key, arr, kind='lm', alpha=None, lathe=False, image=None, **opt):
        """model texture + its shader in one call (ML.T + ML.S); returns the shader name for X.mesh(...).
        lathe=True flips the image vertically: revolve() runs v up the profile while image rows run down, so labels on
        bottles/tubs/cans came out upside down (padfridge)."""
        a = np.ascontiguousarray(np.asarray(arr)[::-1]) if lathe else arr
        if alpha is not None and lathe: alpha = np.ascontiguousarray(np.asarray(alpha)[::-1])
        img = image or f'{key}_m'
        if img not in ML.MTEX: ML.T(img, a, alpha)
        self.mats[key] = ML.S(img, kind, **opt)
        return self.mats[key]

    def __getitem__(self, key): return self.mats[key]

    def texfn(self, key, side_key=None, tile=256.0):
        """per-face texture function for K.solid_piece / ML.solids_mesh: material `key` on tops and bottoms (and
        everywhere without side_key), `side_key` on vertical faces, planar UVs that never mirror"""
        def f(c, n, poly):
            k = side_key if (side_key and abs(n[2]) < 0.7) else key
            return self.mats[k], ML.planar_uv(n, tile)
        return f

    def stanzas(self):
        out = []
        for name, (kind, o, size, has_alpha) in sorted(self.brush.items()):
            ed = f'textures/{self.ns}/{name}'
            if kind == 'lm': out.append(SH.lm(name, steps=o.get('steps'), extra=o.get('extra', '')))
            elif kind == 'sign': out.append(SH.sign(name, steps=o.get('steps')))
            elif kind == 'slick': out.append(SH.slick(name, steps=o.get('steps'), glint=o.get('glint', True)))
            elif kind == 'neon': out.append(SH.neon(name, o.get('rgb', (1, 0.35, 0.7)), o.get('light', 300)))
            elif kind == 'glass': out.append(SH.glass(name, o.get('rgb', '0.10 0.12 0.13'), solid=o.get('solid', True),
                                                      shadow=o.get('shadow', True)))
            elif kind == 'water': out.append(SH.water(name, o.get('rgb', (0.3, 0.55, 0.65)), o.get('alpha', 0.55), o.get('fog')))
            elif kind == 'fog': out.append(SH.fog(name, o.get('rgb', (0.16, 0.40, 0.56)), o.get('dist', 4800)))
            elif kind == 'pulse': out.append(SH.pulse(name, o.get('phase', 0), o.get('freq', 1)))
            elif kind == 'jumppad': out.append(SH.jumppad(name, o.get('rgb', (1, 0.6, 0.8))))
            elif kind == 'raw': out.append(o['shader'])
        return out

    def kit_defaults(self, pad_rgb=(90, 200, 255), rubber=(60, 60, 70), pad=None):
        """jumppad / rubber / nodraw_ns / glass the kit's helpers use (pad = your own themed pad-top image)"""
        rgb = tuple(v / 255 for v in pad_rgb)
        self.add('jumppad', pad if pad is not None else jumppad_disc(pad_rgb, rubber), 'jumppad', rgb=rgb, check_tile=False)
        self.add('rubber', solid(rubber, 3, 59, 64))
        ML.save_img(self.path('nodraw_ns'), fill(64, (200, 60, 200), 2, 69)); self.extra.append(SH.nodraw_ns())
        if 'glass' not in self.brush: self.add('glass', solid((170, 200, 210), 2, 61, 64), 'glass')

    def write_shader(self, extra=(), arena_types=None, ents=None):
        """the map's .shader (brush stanzas + extra + model shaders + levelshots) and, with arena_types, the .arena.
        Raises when a model shader has no image or an alpha kind has no alpha."""
        parts = self.stanzas() + list(self.extra) + list(extra) + [ML.model_shaders(), SH.levelshot_anim()]
        path = SH.write_shader(self.out, parts)
        probs = ML.check_registry()
        if probs: raise SystemExit('model shader problems:\n  ' + '\n  '.join(probs))
        if arena_types: SH.write_arena(self.out, arena_types, ents=ents)
        return path
