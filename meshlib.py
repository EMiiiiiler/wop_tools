#!/usr/bin/env python3
"""Mesh building helpers for custom MD3 map objects (shared by the model generators).

    from meshlib import *
    M = Mesh()
    rbox(M, (-64, -64, 0), (64, 64, 96), r=8, tile=128)        # rounded box, planar UVs in 128u tiles
    tube(M, path, radii)                                        # swept tube along a polyline
    revolve(M, [(r, z), ...])                                   # lathe round z
    ellipsoid(M, c, a, b, h)
    surfs = [M.surface('body', 'models/mymap/wood')]
    scale = save_md3('models/mymap/thing.md3', surfs)         # halves the geometry until it fits +-512; place the
                                                                # misc_model with modelscale = scale

Winding is handled per triangle from the vertex normals (Quake order: clockwise seen from the front), so build every
surface with outward normals and the triangles come out right.
"""
import math
import numpy as np
import md3write


class Mesh:
    def __init__(self):
        self.V, self.N, self.ST, self.T = [], [], [], []

    def __len__(self): return len(self.T)

    def add_v(self, p, n, uv):
        n = np.asarray(n, float); n = n / max(1e-9, np.linalg.norm(n))
        self.V.append(np.asarray(p, float)); self.N.append(n); self.ST.append(tuple(uv))
        return len(self.V) - 1

    def tri(self, a, b, c):
        V = self.V
        fn = np.cross(V[c] - V[a], V[b] - V[a])
        if np.linalg.norm(fn) < 1e-9: return
        want = self.N[a] + self.N[b] + self.N[c]
        self.T.append((a, b, c) if fn @ want >= 0 else (a, c, b))

    def grid(self, P, N, UV):
        rows, cols = P.shape[:2]
        o = len(self.V)
        for i in range(rows):
            for j in range(cols):
                self.add_v(P[i, j], N[i, j], UV[i, j])
        for i in range(rows - 1):
            for j in range(cols - 1):
                a, b, c, d = o + i * cols + j, o + i * cols + j + 1, o + (i + 1) * cols + j, o + (i + 1) * cols + j + 1
                self.tri(a, b, c); self.tri(b, d, c)

    def poly(self, pts, n, uvs):
        o = len(self.V)
        for p, uv in zip(pts, uvs): self.add_v(p, n, uv)
        for k in range(1, len(pts) - 1): self.tri(o, o + k, o + k + 1)

    def quad(self, p0, p1, p2, p3, tile=128.0, n=None):
        """planar quad p0..p3 (any order round the edge), UVs projected on its own plane in `tile` units"""
        P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
        if n is None:
            n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
        u = P[1] - P[0]; u /= max(1e-9, np.linalg.norm(u)); v = np.cross(n, u)
        self.poly(P, n, [((p - P[0]) @ u / tile, -((p - P[0]) @ v) / tile) for p in P])

    def add(self, other, R=np.eye(3), t=(0, 0, 0), sc=1.0):
        o = len(self.V)
        R = np.asarray(R, float); sc = np.asarray(sc, float) * np.ones(3)
        for v, n, st in zip(other.V, other.N, other.ST):
            nn = R @ (np.asarray(n) / sc); nn /= max(1e-9, np.linalg.norm(nn))
            self.V.append(R @ (np.asarray(v) * sc) + np.asarray(t, float)); self.N.append(nn); self.ST.append(st)
        self.T += [(a + o, b + o, c + o) for (a, b, c) in other.T]
        return self

    def transform(self, R=np.eye(3), t=(0, 0, 0)):
        R = np.asarray(R, float)
        self.V = [R @ v + np.asarray(t, float) for v in self.V]; self.N = [R @ n for n in self.N]
        return self

    def surface(self, name, shader):
        return dict(name=name, shader=shader, verts=np.array(self.V), normals=np.array(self.N), st=np.array(self.ST),
                    tris=np.array(self.T, np.int64))


# ------------------------------------------------------------------------------------------------ rotations
def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rot_axis(axis, a):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def frame(d):
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    b1 = np.cross(d, a); b1 /= np.linalg.norm(b1)
    return b1, np.cross(d, b1)


# ------------------------------------------------------------------------------------------------ primitives
def revolve(M, prof, u_tiles=1.0, v_of=None, n=48, a0=0.0, a1=360.0, inward=False, cx=0.0, cy=0.0, vlen=256.0, rfun=None):
    """surface of revolution of prof [(r, z)...] round the z axis; v = arc length / vlen unless v_of given.
    rfun(angle_rad, r, z) -> r lets the radius vary round the turn (scalloped bough tips)."""
    prof = np.asarray(prof, float)
    tg = np.gradient(prof, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    angs = np.radians(np.linspace(a0, a1, n + 1))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
    P = np.zeros((len(prof), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        r = prof[:, 0] if rfun is None else np.array([rfun(a, rr, zz) for rr, zz in prof])
        P[:, j] = np.stack([cx + r * c, cy + r * s, prof[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = (a - angs[0]) / (2 * math.pi) * u_tiles
        UV[:, j, 1] = [v_of(rr, zz) for (rr, zz) in prof] if v_of else L / vlen
    if rfun is not None:          # recompute normals from the deformed grid
        N = grid_normals(P, inward)
    M.grid(P, N, UV)


def grid_normals(P, flip=False):
    du = np.gradient(P, axis=1); dv = np.gradient(P, axis=0)
    N = np.cross(du, dv)
    N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-9)
    return -N if flip else N


def disc(M, r, z, up=True, n=48, cx=0.0, cy=0.0, uvscale=None, r_in=0.0):
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    us = uvscale or 2 * r
    if r_in <= 0:
        pts = [(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in angs]
        M.poly(pts, (0, 0, 1 if up else -1), [(0.5 + (x - cx) / us, 0.5 - (y - cy) / us) for (x, y, _) in pts])
        return
    for k in range(n):
        a0, a1 = angs[k], angs[(k + 1) % n] if k + 1 < n else 2 * math.pi
        q = [(cx + rr * math.cos(a), cy + rr * math.sin(a), z) for rr, a in ((r_in, a0), (r, a0), (r, a1), (r_in, a1))]
        M.poly(q, (0, 0, 1 if up else -1), [(0.5 + (x - cx) / us, 0.5 - (y - cy) / us) for (x, y, _) in q])


def tube(M, path, radii, nseg=16, caps=(True, True), utiles=1.0, vlen=256.0, twist=0.0, ry=None):
    """tube along a polyline path [(x,y,z)...] with radius per point (parallel-transported frames).
    twist: extra u offset per unit length (candy-cane spirals). ry: second radius per point (flat ribbons)."""
    path = np.asarray(path, float); radii = np.asarray(radii, float) * np.ones(len(path))
    ry = radii if ry is None else np.asarray(ry, float) * np.ones(len(path))
    n = len(path)
    T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    b1, _ = frame(T[0]); B1 = [b1]
    for i in range(1, n):
        b = B1[-1] - T[i] * (B1[-1] @ T[i]); b /= np.linalg.norm(b); B1.append(b)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    P = np.zeros((n, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((n, nseg + 1, 2))
    for i in range(n):
        b2 = np.cross(T[i], B1[i])
        for j in range(nseg + 1):
            a = 2 * math.pi * j / nseg
            P[i, j] = path[i] + B1[i] * math.cos(a) * radii[i] + b2 * math.sin(a) * ry[i]
            nn = B1[i] * math.cos(a) / max(radii[i], 1e-3) + b2 * math.sin(a) / max(ry[i], 1e-3)
            N[i, j] = nn / np.linalg.norm(nn)
            UV[i, j] = (j / nseg * utiles + L[i] * twist, L[i] / vlen)
    M.grid(P, N, UV)
    for k, (i, sgn) in enumerate(((0, -1), (n - 1, 1))):
        if not caps[k] or radii[i] < 0.5: continue
        b2 = np.cross(T[i], B1[i])
        angs = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
        pts = [path[i] + B1[i] * math.cos(a) * radii[i] + b2 * math.sin(a) * ry[i] for a in angs]
        M.poly(pts, T[i] * sgn, [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in angs])


def ellipsoid(M, c, a, b, h, nu=16, nv=10, R=np.eye(3), bump=None, u0=0.0, u1=1.0, v0=0.0, v1=1.0, flat_bottom=None):
    """ellipsoid with semi-axes a, b, h; bump(phi, theta) scales the radius; flat_bottom = z (local) to clamp to"""
    c = np.asarray(c, float)
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nv + 1):
        p = math.pi * i / nv - math.pi / 2
        for j in range(nu + 1):
            t = 2 * math.pi * j / nu
            k = 1.0 if bump is None else bump(p, t)
            v = np.array([a * math.cos(p) * math.cos(t), b * math.cos(p) * math.sin(t), h * math.sin(p)]) * k
            if flat_bottom is not None: v[2] = max(v[2], flat_bottom)
            P[i, j] = R @ v + c; UV[i, j] = (u0 + (u1 - u0) * j / nu, v0 + (v1 - v0) * i / nv)
    N = grid_normals(P)
    # poles: average
    for i in (0, nv):
        n = (P[1 if i == 0 else nv - 1].mean(0) - P[i].mean(0)) * -1
        N[i, :] = n / max(1e-9, np.linalg.norm(n))
    M.grid(P, N, UV)


def sphere(M, c, r, nu=16, nv=10, **kw):
    ellipsoid(M, c, r, r, r, nu, nv, **kw)


def _edge_samples(h, r, k):
    """coordinates from -h to h, dense where the rounded edge bends"""
    r = min(r, h)
    if r <= 0: return np.array([-h, h])
    arc = [-h + r * (1 - math.cos(a)) for a in np.linspace(0, math.pi / 2, k)]
    out = arc + [-x for x in arc[::-1]]
    out = np.array(sorted(set(np.round(out, 6))))
    return out


def rbox(M, mn, mx, r=8.0, k=4, tile=128.0, faces='nsewtb', inflate=None):
    """rounded box between corners mn and mx (corner radius r, k samples per quarter arc), planar UVs in `tile` units.
    faces: which sides to build ('t' top, 'b' bottom, 'n' +y, 's' -y, 'e' +x, 'w' -x).
    inflate(x, y, z, n) -> extra outward offset (pillowy cushions)."""
    mn = np.asarray(mn, float); mx = np.asarray(mx, float)
    c = (mn + mx) / 2; H = (mx - mn) / 2
    r = min(r, *(H - 1e-3))
    Hi = H - r
    for key, ax, sgn in (('e', 0, 1), ('w', 0, -1), ('n', 1, 1), ('s', 1, -1), ('t', 2, 1), ('b', 2, -1)):
        if key not in faces: continue
        ua, va = [a for a in range(3) if a != ax]
        us = _edge_samples(H[ua], r, k); vs = _edge_samples(H[va], r, k)
        P = np.zeros((len(vs), len(us), 3)); N = np.zeros_like(P); UV = np.zeros((len(vs), len(us), 2))
        for i, v in enumerate(vs):
            for j, u in enumerate(us):
                p = np.zeros(3); p[ax] = sgn * H[ax]; p[ua] = u; p[va] = v
                q = np.clip(p, -Hi, Hi)
                d = p - q
                # face interior: normal = face axis; edge band: rounded direction
                n = d / np.linalg.norm(d) if np.linalg.norm(d) > 1e-9 else np.eye(3)[ax] * sgn
                pos = q + n * r
                if inflate is not None:
                    pos = pos + n * inflate(*(pos + c), n)
                P[i, j] = pos + c; N[i, j] = n
                us_ = {('e'): pos[1], ('w'): -pos[1], ('n'): -pos[0], ('s'): pos[0], ('t'): pos[0], ('b'): pos[0]}[key]
                vs_ = -pos[1] if ax == 2 else -pos[2]
                UV[i, j] = ((us_ + c[ua]) / tile, (vs_ - (c[1] if ax == 2 else c[2])) / tile)
        if inflate is not None: N = grid_normals(P) * (1 if _orient_ok(P, sgn, ax) else -1)
        M.grid(P, N, UV)


def _orient_ok(P, sgn, ax):
    du = np.gradient(P, axis=1); dv = np.gradient(P, axis=0)
    n = np.cross(du, dv).reshape(-1, 3).mean(0)
    return n[ax] * sgn > 0


def prism(M, poly, z0, z1, tile=128.0, top=True, bot=True, sides=True):
    """vertical extrusion of a convex or concave 2D polygon (counter-clockwise); flat-shaded sides"""
    poly = [np.asarray(p, float) for p in poly]
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    if area < 0: poly = poly[::-1]                      # counter-clockwise, so the side normals point outward
    if sides:
        L = 0.0
        for k in range(n):
            a, b = poly[k], poly[(k + 1) % n]
            e = b - a; ln = np.linalg.norm(e)
            nrm = np.array([e[1], -e[0], 0]) / max(1e-9, ln)
            q = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
            M.poly(q, nrm, [(L / tile, -z0 / tile), ((L + ln) / tile, -z0 / tile), ((L + ln) / tile, -z1 / tile), (L / tile, -z1 / tile)])
            L += ln
    tris = triangulate(poly)
    for z, up, flag in ((z1, 1, top), (z0, -1, bot)):
        if not flag: continue
        for (i, j, k) in tris:
            o = len(M.V)
            for idx in (i, j, k):
                M.add_v((poly[idx][0], poly[idx][1], z), (0, 0, up), (poly[idx][0] / tile, -poly[idx][1] / tile))
            M.tri(o, o + 1, o + 2)


def triangulate(poly):
    """ear clipping for a simple counter-clockwise polygon -> index triples"""
    idx = list(range(len(poly)))
    P = [np.asarray(p, float)[:2] for p in poly]
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    if area < 0: idx = idx[::-1]
    out = []
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i, j, l = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if cross(P[i], P[j], P[l]) <= 1e-9: continue
            if any(cross(P[i], P[j], P[m]) > 0 and cross(P[j], P[l], P[m]) > 0 and cross(P[l], P[i], P[m]) > 0
                   for m in idx if m not in (i, j, l)): continue
            out.append((i, j, l)); idx.pop(k); break
        else:
            break
    if len(idx) == 3: out.append(tuple(idx))
    return out


def arc_path(c, R, a0, a1, n=24, axis='z', z=0.0):
    """points on a circular arc (degrees) round centre c in the plane normal to axis"""
    c = np.asarray(c, float); out = []
    for a in np.radians(np.linspace(a0, a1, n)):
        if axis == 'z': out.append(c + [R * math.cos(a), R * math.sin(a), z])
        elif axis == 'y': out.append(c + [R * math.cos(a), z, R * math.sin(a)])
        else: out.append(c + [z, R * math.cos(a), R * math.sin(a)])
    return np.array(out)


# ------------------------------------------------------------------------------------------------ save
def save_md3(path, surfaces, name=None, with_offset=False):
    """write an MD3, halving the geometry until it fits MD3's +-512 range. Returns the modelscale to place it with.
    with_offset=True: tall models may be stored around their mid-height (z offset) when that needs less scaling;
    returns (scale, zoff) then, and the misc_model origin must be raised by zoff."""
    surfaces = [s for s in surfaces if len(s['tris'])]
    def need(zo):
        ext = max(np.abs(np.asarray(s['verts']) - [0, 0, zo]).max() for s in surfaces)
        sc = 1
        while ext / sc >= 511.0: sc *= 2
        return sc
    scale, zoff = need(0.0), 0.0
    if with_offset and scale > 1:
        allz = np.concatenate([np.asarray(s['verts'])[:, 2] for s in surfaces])
        zo = round(float(allz.min() + allz.max()) / 2)
        if need(zo) < scale: scale, zoff = need(zo), float(zo)
    out = []
    for s in surfaces:
        s = dict(s); s['verts'] = (np.asarray(s['verts']) - [0, 0, zoff]) / scale
        # drop triangles that collapse once MD3 rounds the vertices to 1/64 (q3map2 warns about them)
        V, T = s['verts'], np.asarray(s['tris'])
        Q = np.round(V * 64) / 64 * scale                 # world units after modelscale
        ar = np.linalg.norm(np.cross(Q[T[:, 1]] - Q[T[:, 0]], Q[T[:, 2]] - Q[T[:, 0]]), axis=1)
        e = np.max([np.linalg.norm(Q[T[:, a]] - Q[T[:, b]], axis=1) for a, b in ((0, 1), (1, 2), (2, 0))], axis=0)
        T = T[(ar > 0.1) & (e > 1.0)]; s['tris'] = T
        # split surfaces over the MD3 limits
        if len(V) < 4000 and len(T) < 8000:
            out.append(s); continue
        # greedy chunks that stay under 4000 vertices and 8000 triangles each
        k0, part = 0, 0
        while k0 < len(T):
            seen = set(); k1 = k0
            while k1 < len(T) and k1 - k0 < 7900:
                new = set(T[k1].tolist()) - seen
                if len(seen) + len(new) > 3990: break
                seen |= new; k1 += 1
            tt = T[k0:k1]; used = np.unique(tt); remap = {v: i for i, v in enumerate(used)}
            out.append(dict(name=f"{s['name']}{part}", shader=s['shader'], verts=V[used], normals=np.asarray(s['normals'])[used],
                            st=np.asarray(s['st'])[used], tris=np.vectorize(remap.get)(tt)))
            k0 = k1; part += 1
    md3write.save(path, out, name or path.rsplit('/', 1)[-1].split('.')[0])
    return (scale, zoff) if with_offset else scale
