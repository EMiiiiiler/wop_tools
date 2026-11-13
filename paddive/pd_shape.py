"""Pad Deep Dive - shape constants shared by the MD3s (pd_models) and the collision/layout (build_paddive)."""
import math
import numpy as np

BC = (0, 640)                 # building centre (world)
DRUM_RO, DRUM_RV, DRUM_RI = 612.0, 604.0, 596.0      # vertex radii: outer face, glass line, inner face (apothem ~0.98x)
MEZZ_Z = 256                  # gallery inside = top terrace outside
ROOF_X = 944                  # the roof runs local x -944..944
ROOF_BOT = 560                # collision underside (flat); the visible soffit follows the wave
FACE_KIND = {12: 'ground', 4: 'ground', 0: 'upper', 8: 'upper'}     # face i looks toward 22.5*i degrees


def roof_f(x):
    """top of the shell roof over local x: crest in the middle, troughs at +-480, wing tips rising again"""
    return 672.0 + 64.0 * math.cos(math.pi * x / 480.0)


def roof_w(x):
    """half width (local y) of the lens-shaped roof plan"""
    return 700.0 * max(0.0, 1.0 - (x / 980.0) ** 2) ** 0.65


def roof_top(x, strip=32):
    """walk surface of the collision strip under local x (4u grid; neighbours differ by < 16u)"""
    i = math.floor((x + ROOF_X) / strip)
    xm = -ROOF_X + (i + 0.5) * strip
    return round(roof_f(xm) / 4.0) * 4


def face_pts(i, rv):
    """end points (local, numpy) of drum face i at vertex radius rv"""
    a0, a1 = math.radians(22.5 * i - 11.25), math.radians(22.5 * i + 11.25)
    return np.array([rv * math.cos(a0), rv * math.sin(a0)]), np.array([rv * math.cos(a1), rv * math.sin(a1)])


def ngon16(r):
    return [(BC[0] + r * math.cos(math.radians(11.25 + 22.5 * k)), BC[1] + r * math.sin(math.radians(11.25 + 22.5 * k))) for k in range(16)]


def lobe(cx, cy, r, flats=(), n=28, sx=1):
    """round pool terrace outline: a circle clipped by flat chords. flats = [('s'|'n'|'e'|'w', coordinate)].
    sx=-1 mirrors the result in x (west side). Returns a CCW polygon."""
    poly = [(cx + r * math.cos(2 * math.pi * (k + 0.5) / n), cy + r * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    for side, v in flats:
        nx, ny, d = {'s': (0, -1, -v), 'n': (0, 1, v), 'e': (1, 0, v), 'w': (-1, 0, -v)}[side]
        out = []
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            da, db = a[0] * nx + a[1] * ny - d, b[0] * nx + b[1] * ny - d
            if da <= 0: out.append(a)
            if (da < 0) != (db < 0) and da != db:
                t = da / (da - db); out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        poly = out
    poly = [(round(sx * x), round(y)) for x, y in poly]
    return poly[::-1] if sx < 0 else poly
