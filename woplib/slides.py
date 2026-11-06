"""woplib.slides - water slides: invisible collision along a centreline + the visible MD3 (open flume or closed tube).
Promoted from the copies in moosefalls, padpirate, padaztec and padspace (slide_brushes / comet_flume / wormhole_tube).

    from woplib import slides as SL
    path = SL.path_xy(xy_points, z_top, z_end)             # or geom.helix(...) / your own [(x, y, floor_z)]
    SL.collision(K, path, hw=44, wall_h=48, floor_tex=K.T('slide_clip'))   # slick player-clip floor + weapclip walls
    X = ML.Model(); SL.flume(X, path, shell, inner, rim, water); ...; ML.save('my_slide', X)
    K.custom(ML.PLACE['my_slide'], 0, 0, 0)               # the MD3 is built in world coordinates

The floor texture must be a slick nodraw player clip (`SH.slide_clip()` writes it): players slide down, shots and
items pass through the visible model, and the MD3 never needs collision of its own. Keep the swept band (hw + wall +
~40u) free of props (`K.keep_clear` along the path, `reserve_path()` does it) and put supports only on open floor.
"""
import math
import numpy as np
from wopmap import hull
from .geom import sweep, circle_prof, densify, torus, tube, boxm, with_z
from meshlib import Mesh, revolve, frame

WCLIP = 'common/weapclip'


def path_xy(xy, z0, z1, ease=None):
    """centreline from 2D points with heights z0 -> z1 by arc length (floor top of the slide)"""
    return with_z(xy, z0, z1, ease)


def _joints(P):
    n = len(P)
    dirs = []
    for i in range(n - 1):
        d = P[i + 1][:2] - P[i][:2]; dirs.append(d / np.linalg.norm(d))
    perps = [np.array([-d[1], d[0]]) for d in dirs]
    jl = []
    for k in range(n):
        if k == 0: m = perps[0]
        elif k == n - 1: m = perps[-1]
        else:
            m = perps[k - 1] + perps[k]; m = m / np.linalg.norm(m)
        ref = perps[min(k, n - 2)]
        jl.append((m, 1.0 / max(0.5, float(m @ ref))))
    return jl


def collision(K, pts, hw, wall_h, floor_tex, roof=False, floor_t=16, wall_t=8, wall_tex=WCLIP):
    """slide collision along centreline pts [(x, y, floor_z)]: a floor of triangle prisms (floor_tex: slick player
    clip), side walls (weapclip) wall_h tall, and a roof for tubes. Mitred joints, so curves have no gaps."""
    P = [np.array(p, float) for p in pts]
    jl = _joints(P)
    out = []
    for i in range(len(P) - 1):
        (ma, fa), (mb, fb) = jl[i], jl[i + 1]
        ca, cb = P[i], P[i + 1]
        za, zb = ca[2], cb[2]
        def edge(c, m, f, off): return c[:2] + m * off * f
        La, Ra = edge(ca, ma, fa, hw), edge(ca, ma, fa, -hw)
        Lb, Rb = edge(cb, mb, fb, hw), edge(cb, mb, fb, -hw)
        for (p1, p2, p3, z1, z2, z3) in ((La, Ra, Lb, za, za, zb), (Ra, Rb, Lb, za, zb, zb)):
            out.append(hull([(p1[0], p1[1], z1), (p2[0], p2[1], z2), (p3[0], p3[1], z3),
                             (p1[0], p1[1], z1 - floor_t), (p2[0], p2[1], z2 - floor_t), (p3[0], p3[1], z3 - floor_t)],
                            floor_tex, round_pts=False))
        for side in (1, -1):
            ia, ib = edge(ca, ma, fa, side * hw), edge(cb, mb, fb, side * hw)
            oa, ob = edge(ca, ma, fa, side * (hw + wall_t)), edge(cb, mb, fb, side * (hw + wall_t))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - floor_t), (p[0], p[1], zz + wall_h)]
            out.append(hull(pw, wall_tex, round_pts=False))
        if roof:
            oLa, oRa = edge(ca, ma, fa, hw + wall_t), edge(ca, ma, fa, -hw - wall_t)
            oLb, oRb = edge(cb, mb, fb, hw + wall_t), edge(cb, mb, fb, -hw - wall_t)
            for (p1, p2, p3, z1, z2, z3) in ((oLa, oRa, oLb, za, za, zb), (oRa, oRb, oLb, za, zb, zb)):
                out.append(hull([(p1[0], p1[1], z1 + wall_h), (p2[0], p2[1], z2 + wall_h), (p3[0], p3[1], z3 + wall_h),
                                 (p1[0], p1[1], z1 + wall_h + 6), (p2[0], p2[1], z2 + wall_h + 6),
                                 (p3[0], p3[1], z3 + wall_h + 6)], wall_tex, round_pts=False))
    K.add(*out)
    K.spots.setdefault('slides', []).append(dict(path=[[round(v, 1) for v in p] for p in pts], hw=hw, roof=roof))
    return out


def reserve_path(K, pts, hw, height=96, zmin=None, why='slide'):
    """occupy the slide's swept band so scattered props never sit inside it (one box per segment)"""
    for a, b in zip(pts, pts[1:]):
        x0, x1 = min(a[0], b[0]) - hw - 16, max(a[0], b[0]) + hw + 16
        y0, y1 = min(a[1], b[1]) - hw - 16, max(a[1], b[1]) + hw + 16
        z0 = min(a[2], b[2]) - 24 if zmin is None else zmin
        K.occupy(x0, y0, x1, y1, z0, max(a[2], b[2]) + height, why=why)


def flume(X, pts, shell, inner, rim=None, water=None, r=48, lip=44, step=40.0):
    """open half-pipe trough along pts (floor tops): outer shell, inner liner, optional glowing rim strips and a
    scrolling water strip. Model in world coordinates; returns the densified centreline."""
    P = densify(pts, step)
    zc = r * 0.55
    prof_out = [(-(r + 6), lip)] + [((r + 6) * math.cos(a), zc + (r + 6) * math.sin(a))
                                    for a in np.radians(np.linspace(180, 360, 9))] + [((r + 6), lip)]
    prof_in = [(-r, lip)] + [(r * math.cos(a), zc + r * math.sin(a)) for a in np.radians(np.linspace(180, 360, 9))] + [(r, lip)]
    Pd = [np.array([p[0], p[1], p[2] - (zc - r)]) for p in P]                # liner bottom sits on the floor top
    sweep(X.mesh(shell), Pd, prof_out, vlen=128)
    sweep(X.mesh(inner), Pd, prof_in, vlen=256, inward=True)
    if rim:
        sweep(X.mesh(rim), Pd, [(-(r + 6), lip), (-(r + 6), lip + 3), (-r, lip + 3)], vlen=128)
        sweep(X.mesh(rim), Pd, [(r, lip + 3), (r + 6, lip + 3), (r + 6, lip)], vlen=128)
    if water:
        sweep(X.mesh(water), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-r * 0.6, 0), (r * 0.6, 0)], vlen=200)
    return P


def tube_slide(X, pts, R, body, inner, bands=None, water=None, band_every=3, step=40.0, zc=None):
    """closed tube along pts (floor tops): outer body, inner liner (seen from inside), glowing rings every
    `band_every` samples and a scrolling water strip. zc = height of the tube axis over the floor (default R - 4)."""
    P = densify(pts, step)
    zc = R - 4 if zc is None else zc
    C3 = [np.array([p[0], p[1], p[2] + zc]) for p in P]
    sweep(X.mesh(body), C3, circle_prof(R, 20), closed=True, vlen=192)
    sweep(X.mesh(inner), C3, circle_prof(R - 4, 20), closed=True, vlen=256, inward=True)
    if water:
        sweep(X.mesh(water), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-R * 0.5, 0), (R * 0.5, 0)], vlen=200)
    if bands:
        for i in range(2, len(C3) - 2, band_every):
            d = C3[i + 1] - C3[i - 1]; d /= np.linalg.norm(d)
            tor = Mesh(); revolve(tor, [(R + 0.5, -4), (R + 3, -2), (R + 3, 2), (R + 0.5, 4)], n=20, vlen=16)
            b1, b2 = frame(d)
            X.mesh(bands).add(tor, np.stack([b1, b2, d], 1), C3[i])
    return P


def supports(X, pts, metal, floor_fn, every=5, zmin=110, under=0.0):
    """legs from the floor up to the slide where floor_fn(x, y) returns a floor height (None = no floor there).
    under = how far the slide's underside sits below the floor top (flume: ~10, tube: 4). Returns [(x, y, z0, z1)] so
    the builder can add weapclip posts of the same size."""
    out = []
    for i in range(2, len(pts) - 2, every):
        x, y, z = pts[i]
        if z < zmin: continue
        f = floor_fn(x, y)
        if f is None: continue
        zt = z - under - 4
        if zt - f < 48: continue
        tube(X.mesh(metal), [(x, y, f), (x, y, zt)], 7, nseg=8)
        boxm(X.mesh(metal), (x - 36, y - 10, zt - 12), (x + 36, y + 10, zt), r=1, tile=64)
        out.append((x, y, f, zt - 12))
    return out
