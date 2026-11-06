"""woplib.geom - mesh + path helpers that every map's *_models.py kept copying (padpirate, padbakery, padspace,
moosefalls, padhalloween). Import these instead of pasting them again:

    from woplib.geom import tube, cylm, boxm, torus, quad_uv, picture, annulus, frustum_m, sweep, circle_prof, densify,
                            bezier, with_z, ang_pt, ring_seg, ring_tex, disc_brush

Mesh helpers take a meshlib.Mesh (X.mesh(shader)) first. Brush helpers return wopmap Brushes (add them with K.add).
"""
import math
import numpy as np
from meshlib import Mesh, revolve, disc, tube as _tube, rbox, grid_normals, frame
from wopmap import hull


# ================================================================================================= meshes
def tube(M, path, radii, **kw):
    """meshlib.tube with a scalar or per-point (interpolated) radius"""
    path = np.asarray(path, float)
    r = np.atleast_1d(np.asarray(radii, float))
    if len(r) == 1: r = np.full(len(path), float(r[0]))
    elif len(r) != len(path):
        r = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(r)), r)
    _tube(M, path, r, **kw)


def cylm(M, c, r, h, n=16, caps=True, tile=128.0, top=True):
    """upright cylinder at c (base centre); caps run inward over the top so they face UP"""
    c = np.asarray(c, float)
    if caps:
        prof = [(0, c[2]), (r, c[2]), (r, c[2] + h)] + ([(0, c[2] + h)] if top else [])
    else:
        prof = [(r, c[2]), (r, c[2] + h)]
    revolve(M, prof, n=n, cx=c[0], cy=c[1], vlen=tile, u_tiles=max(1, round(2 * math.pi * r / tile)))


def boxm(M, mn, mx, r=1.0, tile=64.0, k=1, faces='nsewtb'):
    """rounded box (sharp-ish by default: thin r=1 rounding on long ribbons gave 'Duplicate or Flipped triangle')"""
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def torus(M, c, R, r, axis=(0, 0, 1), n=32, m=10, utile=4.0, a0=0.0, a1=2 * math.pi):
    c = np.asarray(c, float); ax = np.asarray(axis, float); ax /= np.linalg.norm(ax)
    b1, b2 = frame(ax)
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    path = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * R for t in np.linspace(a0, a1, n + 1)]
    _tube(M, np.array(path), np.full(n + 1, r), nseg=m, caps=(not full, not full), utiles=1,
          vlen=max(1.0, (a1 - a0) * R / utile))


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture(M, c, w, h, nrm, up=(0, 0, 1), two=False):
    """textured quad centred at c facing nrm; u runs left -> right as seen from the front, so text never mirrors"""
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm); up = np.asarray(up, float)
    right = np.cross(up, nrm); right /= np.linalg.norm(right)
    upv = np.cross(nrm, right)
    p = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2,
         c - right * w / 2 + upv * h / 2]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])
    if two: M.poly(p[::-1], -nrm, [(0, 0), (1, 0), (1, 1), (0, 1)][::-1])


def annulus(M, cx, cy, r0, r1, z, a0=0.0, a1=360.0, n=48, up=True, tile=256.0):
    """flat ring (or pie when r0 = 0) between angles a0..a1, planar UVs; up=True faces +z"""
    angs = np.radians(np.linspace(a0, a1, n + 1))
    nn = (0, 0, 1 if up else -1)
    for k in range(n):
        ta, tb = angs[k], angs[k + 1]
        pts = [(cx + r1 * math.cos(ta), cy + r1 * math.sin(ta), z), (cx + r1 * math.cos(tb), cy + r1 * math.sin(tb), z)]
        if r0 > 0.5: pts += [(cx + r0 * math.cos(tb), cy + r0 * math.sin(tb), z), (cx + r0 * math.cos(ta), cy + r0 * math.sin(ta), z)]
        else: pts += [(cx, cy, z)]
        if not up: pts = pts[::-1]
        M.poly(pts, nn, [(p[0] / tile, -p[1] / tile) for p in pts])


def frustum_m(M, c, r0, r1, h, n=24, tile=128.0, top=True, bottom=False):
    """truncated cone r0 (base) -> r1 (top); the top cap faces up"""
    c = np.asarray(c, float)
    prof = ([(0, c[2])] if bottom else []) + [(r0, c[2]), (r1, c[2] + h)] + ([(0, c[2] + h)] if top else [])
    revolve(M, prof, n=n, cx=c[0], cy=c[1], vlen=tile, u_tiles=max(1, round(2 * math.pi * max(r0, r1) / tile)))


def sweep(M, path, prof, closed=False, vlen=128.0, inward=False, utile=1.0):
    """sweep a 2D profile [(lateral, up)] along a 3D path (lateral = horizontal normal of the path). Normals point away
    from the profile centre unless inward=True. Returns the vertex grid."""
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


def circle_prof(r, n=16, a0=0.0, a1=360.0):
    if abs(a1 - a0 - 360) < 1e-6:
        return [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    return [(r * math.cos(a), r * math.sin(a)) for a in np.radians(np.linspace(a0, a1, n + 1))]


def densify(path, step=40.0):
    """resample a polyline so no segment is longer than step"""
    out_ = [np.asarray(path[0], float)]
    for a, b in zip(path, path[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for t in np.linspace(0, 1, k + 1)[1:]: out_.append(a + (b - a) * t)
    return out_


# ================================================================================================= paths
def bezier(p0, p1, p2, p3, n):
    """cubic Bezier points (2D or 3D), n samples including both ends"""
    out = []
    for t in np.linspace(0, 1, n):
        out.append(((1 - t) ** 3) * np.array(p0, float) + 3 * ((1 - t) ** 2) * t * np.array(p1, float)
                   + 3 * (1 - t) * t * t * np.array(p2, float) + t ** 3 * np.array(p3, float))
    return out


def with_z(xy, z0, z1, ease=None):
    """give a 2D polyline heights from z0 to z1 by arc length (ease(t) reshapes the descent)"""
    xy = [np.asarray(p, float)[:2] for p in xy]
    Ls = np.concatenate([[0], np.cumsum([np.linalg.norm(b - a) for a, b in zip(xy, xy[1:])])])
    t = Ls / Ls[-1]
    if ease is not None: t = ease(t)
    return [(float(p[0]), float(p[1]), float(z0 + (z1 - z0) * tt)) for p, tt in zip(xy, t)]


def helix(cx, cy, R, a0_deg, sweep_deg, z0, z1, n):
    """helix points round (cx, cy): from angle a0 sweeping sweep_deg (negative = clockwise) while dropping z0 -> z1"""
    out = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0_deg + sweep_deg * t)
        out.append((cx + R * math.cos(a), cy + R * math.sin(a), z0 + (z1 - z0) * t))
    return out


# ================================================================================================= round brushes (padshroom)
def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, tex, z0b=None, z1b=None):
    """wedge of a ring band between angles a0..a1 (deg); r0 == 0 gives a pie slice. Outer radius may span z0b..z1b
    (sloped band). Vertices on the circles."""
    z0b = z0 if z0b is None else z0b; z1b = z1 if z1b is None else z1b
    pts = []
    for a in (a0, a1):
        for (r, za, zb) in ((r0, z0, z1), (r1, z0b, z1b)):
            if r < 0.5:
                pts += [(cx, cy, za), (cx, cy, zb)]
            else:
                px, py = ang_pt(cx, cy, r, a)
                pts += [(px, py, za), (px, py, zb)]
    return hull(pts, tex, round_pts=False)


def ring_tex(amid, inner, outer, top, bot, side):
    """texture function for a ring_seg centred on angle amid: picks by face normal"""
    rx, ry = math.cos(math.radians(amid)), math.sin(math.radians(amid))

    def f(n):
        if n[2] > 0.7: return top
        if n[2] < -0.7: return bot
        d = n[0] * rx + n[1] * ry
        if d > 0.5: return outer
        if d < -0.5: return inner
        return side
    return f


def disc_brush(cx, cy, r, z0, z1, tex, n=16):
    """n-gon prism with a vertex at angle 0 (matches ring_seg wedges of the same n)"""
    pts = []
    for k in range(n):
        px, py = ang_pt(cx, cy, r, k * 360.0 / n)
        pts += [(px, py, z0), (px, py, z1)]
    return hull(pts, tex, round_pts=False)
