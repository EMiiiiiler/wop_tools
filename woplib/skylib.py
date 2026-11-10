"""woplib.skylib - custom sky cubes from a direction function (promoted from padaztec/az_textures + padspace/sp_textures).

    from woplib import skylib
    def colour(D, el, az): ...            # D: unit directions (n, n, 3); el/az in degrees -> (n, n, 3) RGB 0-255
    skylib.write_cube(out_dir, ns, 'desert', colour)          # env/<ns>/desert_rt.jpg ... (engine face order)
    SH.sky(f'env/{ns}/desert', sun=(yaw, elev), ...)          # skyparms name for the shader

Face orientation is the engine's (tr_sky.c): rt=+x, lf=-x, bk=+y, ft=-y, up, dn; seams match (checked on padshroom,
padaztec, padspace). Helpers: sun glow, horizon ridges (elevation by azimuth), cloud noise sampled on (az, el).
"""
import os, math
import numpy as np
from . import models as ML

C = ML.C


def faces(n=512):
    """{face: (x, y, z) direction grids} in engine order"""
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V
    one = np.ones_like(s)
    return {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}


def sdir(yaw, elev):
    y, e = math.radians(yaw), math.radians(elev)
    return np.array([math.cos(e) * math.cos(y), math.cos(e) * math.sin(y), math.sin(e)])


def gradient(el, horizon=(186, 214, 232), zenith=(52, 112, 200), power=0.6):
    up = np.clip(np.sin(np.radians(el)), 0, 1)
    return ML.lerp(C(horizon), C(zenith), (up ** power)[..., None])


def sun_glow(D, yaw, elev, rgb=(1.0, 0.95, 0.8), halo=120, disc=400):
    cs = np.clip(D @ sdir(yaw, elev), 0, 1)
    return (cs ** 40 * halo + cs ** 600 * disc)[..., None] * C(rgb)


AZ = np.linspace(-180, 180, 4097)


def ridge(seed, base, amp, rough=1.0, terms=40):
    """horizon profile: elevation (deg) by azimuth AZ, a random Fourier series (rough > 1 = smoother)"""
    g = np.random.default_rng(seed)
    v = np.full_like(AZ, float(base))
    for k in range(1, terms):
        v += g.normal() * amp / k ** rough * np.sin(np.radians(AZ) * k + g.uniform(0, 6.28))
    return v


def mesas(seed, n, base, h=(3, 8), w=(8, 24)):
    """flat-topped buttes/mesas on the horizon: elevation (deg) by azimuth"""
    g = np.random.default_rng(seed)
    v = np.full_like(AZ, float(base))
    for _ in range(n):
        c = g.uniform(-180, 180); hw = g.uniform(*w) / 2; hh = g.uniform(*h); sl = g.uniform(1.5, 4)
        d = np.abs(((AZ - c) + 180) % 360 - 180)
        prof = np.clip((hw + sl - d) / sl, 0, 1) * hh
        v = np.maximum(v, base + prof)
    return v


def at(profile, az):
    return np.interp(az, AZ, profile)


def clouds(D, el, az, seeds=(21, 22), band=(14, 9), cover=0.75, n=512):
    """cumulus coverage 0..1 sampled on (az, el): a band round `band` = (centre elevation, width)"""
    N0 = ML.noise(n, 10, seeds[0]); N1 = ML.noise(n, 3.5, seeds[1])
    uu = (az + 180) / 360 * 4; vv = np.clip(el / 40, 0, 0.999)
    ci = (np.floor(uu * n) % n).astype(int); cj = (np.floor(vv * (n - 1))).astype(int)
    cn = N0[cj, ci] * 0.6 + N1[(cj * 3) % n, (ci * 3) % n] * 0.4
    b = np.exp(-((el - band[0]) / band[1]) ** 2)
    return np.clip(cn * 0.9 + b * 0.9 - cover, 0, 1) * (el > 1)


def write_cube(out_dir, ns, name, colour, n=512, quality=94):
    """render the six faces of env/<ns>/<name>_<face>.jpg from colour(D, el, az) -> RGB array. Returns the skyparms
    name (env/<ns>/<name>) for shaders.sky()."""
    d = os.path.join(out_dir, 'env', ns); os.makedirs(d, exist_ok=True)
    for k, (x, y, z) in faces(n).items():
        D = np.stack([x, y, z], -1)
        D = D / np.linalg.norm(D, axis=-1, keepdims=True)
        el = np.degrees(np.arcsin(np.clip(D[..., 2], -1, 1)))
        az = np.degrees(np.arctan2(D[..., 1], D[..., 0]))
        ML.img(colour(D, el, az)).save(os.path.join(d, f'{name}_{k}.jpg'), quality=quality)
    return f'env/{ns}/{name}'
