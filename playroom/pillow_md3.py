#!/usr/bin/env python3
"""Soft pillow as an MD3 (models/mapobjects/playroom/pillow.md3) + its pillowcase texture.

    python3 pillow_md3.py <out pk3dir>

Shape: a stuffed rectangle. Seen from above the edges bow inward a little and the four corners poke out
("dog ears"); the top is a full rounded dome that falls off steeply at the seam, the bottom is flatter
(it rests on the mattress), there is a shallow head dent, and soft wrinkles radiate from the corners.
Size 284 x 216 x ~72 at modelscale 1 (origin at the centre of the base, base at z 0).
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from md3write import save, vertex_normals

SHADER = 'models/mapobjects/playroom/pillow'
A, B = 142.0, 108.0        # half length / half width
T_TOP, T_BOT = 58.0, 12.0  # dome height above / below the seam


def grid(n):
    """parameter samples in [-1, 1], denser near the seam so the rounded edge stays smooth"""
    u = np.linspace(-1, 1, n)
    return np.sign(u) * (1 - (1 - np.abs(u)) ** 1.6)


def surface(side, n=44, seed=3):
    s = grid(n); t = grid(n)
    S, Tt = np.meshgrid(s, t, indexing='ij')
    pinch = 0.075
    X = A * S * (1 - pinch * (1 - Tt ** 2))
    Y = B * Tt * (1 - pinch * (1 - S ** 2))
    f = ((1 - S ** 2) * (1 - Tt ** 2)).clip(0) ** 0.42          # fat in the middle, steep at the seam
    if side == 'top':
        Z = T_TOP * f
        dent = 13 * np.exp(-((X + 10) ** 2 / 70 ** 2 + Y ** 2 / 55 ** 2)) * f   # where a head has been
        Z -= dent
        # wrinkles fanning out from each corner, fading toward the middle
        ang = np.arctan2(Tt, S)
        corner = (np.abs(S) * np.abs(Tt)) ** 2
        Z += 2.6 * np.sin(ang * 22 + seed) * corner * (1 - f) * 2.2
        Z += 1.2 * np.sin(X / 23 + Y / 31) * f * (1 - f) * 2
    else:
        Z = -T_BOT * f ** 1.8
    Z = Z + T_BOT                                               # base at z 0
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    # texture: one pillowcase image over each face, s along x, t along y (t downward = -y)
    UV = np.stack([(S + 1) / 2, (1 - Tt) / 2], -1).reshape(-1, 2)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    if side == 'top':   # Quake order: clockwise seen from outside
        tris = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([a, d, c], -1).reshape(-1, 3)])
    else:
        tris = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    return V, UV, tris


def build():
    Vt, UVt, Tt = surface('top')
    Vb, UVb, Tb = surface('bot')
    V = np.concatenate([Vt, Vb]); UV = np.concatenate([UVt, UVb]); T = np.concatenate([Tt, Tb + len(Vt)])
    N = vertex_normals(V, T)
    # the seam ring is shared by top and bottom: give both copies the averaged sideways normal so it shades soft
    n = int(math.sqrt(len(Vt)))
    edge = np.zeros((n, n), bool); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    e = edge.reshape(-1)
    avg = N[:len(Vt)][e] + N[len(Vt):][e]
    avg /= np.linalg.norm(avg, axis=1, keepdims=True)
    N[:len(Vt)][e] = avg; N[len(Vt):][e] = avg
    return V, N, UV, T


def texture(path, size=512):
    """white cotton pillowcase: soft weave, faint blue ticking stripes, piped seam border, tiny stitched star"""
    r = np.random.default_rng(7)
    base = np.full((size, size, 3), (246, 246, 241), np.float32)
    nz = Image.fromarray((r.random((size, size)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14))
    base += (np.asarray(nz, np.float32)[..., None] - 128) * 0.18
    weave = (np.indices((size, size)).sum(0) % 4 < 2).astype(np.float32)[..., None]
    base -= weave * 3
    for i in range(0, size, 64):
        base[:, i + 22:i + 42] *= np.array((0.92, 0.95, 1.0), np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, size - 1, size - 1), outline=(150, 190, 235), width=10)         # piping
    for k in range(0, size, 14):                                                      # stitches inside the piping
        for (x0, y0, x1, y1) in ((k, 16, k + 7, 16), (k, size - 17, k + 7, size - 17), (16, k, 16, k + 7), (size - 17, k, size - 17, k + 7)):
            d.line((x0, y0, x1, y1), fill=(170, 175, 185), width=2)
    cx, cy = size * 0.8, size * 0.78                                                  # little embroidered star
    pts = [(cx + (18 if j % 2 == 0 else 8) * math.cos(math.pi / 2 + j * math.pi / 5),
            cy - (18 if j % 2 == 0 else 8) * math.sin(math.pi / 2 + j * math.pi / 5)) for j in range(10)]
    d.polygon(pts, fill=(255, 205, 70))
    im.save(path, quality=92)


def main(out):
    mdir = os.path.join(out, 'models', 'mapobjects', 'playroom')
    os.makedirs(mdir, exist_ok=True)
    V, N, UV, T = build()
    save(os.path.join(mdir, 'pillow.md3'), [dict(name='pillow', shader=SHADER, verts=V, normals=N, st=UV, tris=T)],
         name='pillow')
    texture(os.path.join(mdir, 'pillow.jpg'))
    print('pillow.md3', len(V), 'verts', len(T), 'tris', 'bounds', V.min(0).round(1), V.max(0).round(1))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out'))
