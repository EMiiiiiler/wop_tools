#!/usr/bin/env python3
"""Tiny mesh kit for building custom MD3 map objects out of lathes, sweeps, boxes and discs.

    from meshkit import Mesh, rot, trans
    m = Mesh()
    m.lathe('red', [(0, 0), (40, 0), (40, 30), (0, 30)], segs=32, xf=trans(0, 0, 10))
    m.sweep('chrome', [(0, 0, 0), (0, 0, 50), (30, 0, 80)], radius=4)
    m.save('models/mapobjects/foo/bar.md3', shader_prefix='models/mapobjects/foo/')

Every part is wound in Quake order (clockwise seen from outside) automatically: each triangle is compared with
the outward direction the generator knows (profile normal for lathes, tube normal for sweeps, face normal for
boxes) and flipped if needed. Repeating a lathe profile point makes a hard edge there.
One MD3 surface per material name; shader = shader_prefix + name.
"""
import numpy as np
from md3write import save as md3save, vertex_normals


def trans(x, y, z):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m


def rot(axis, deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    m = np.eye(4)
    if axis == 'x': m[1:3, 1:3] = [[c, -s], [s, c]]
    elif axis == 'y': m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c
    else: m[:2, :2] = [[c, -s], [s, c]]
    return m


def scale(sx, sy, sz):
    return np.diag([sx, sy, sz, 1.0])


class Mesh:
    def __init__(self):
        self.parts = {}     # material -> list of (V, UV, T, N)

    # ------------------------------------------------------------------ core
    def _add(self, mat, V, UV, T, want, xf, smooth=True):
        """V (n,3) local, T (m,3), want (m,3) desired outward normal per triangle (local)"""
        V = np.asarray(V, float); T = np.asarray(T, int); want = np.asarray(want, float)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        quake = np.cross(c - a, b - a)                      # outward for Quake (clockwise) order
        flip = (quake * want).sum(1) < 0
        T = T.copy(); T[flip] = T[flip][:, [0, 2, 1]]
        if xf is not None:
            V = (np.c_[V, np.ones(len(V))] @ xf.T)[:, :3]
        N = vertex_normals(V, T)
        self.parts.setdefault(mat, []).append((V, np.asarray(UV, float), T, N))

    def lathe(self, mat, profile, segs=32, xf=None, a0=0.0, a1=360.0, uscale=1.0, closed=None):
        """revolve [(r, z), ...] around local z. Profile should run bottom-centre -> out -> up -> top-centre
        (counter-clockwise in the r/z half plane); outward is then (dz, -dr)."""
        P = np.asarray(profile, float)
        closed = abs(a1 - a0) >= 359.999 if closed is None else closed
        ns = segs + 1
        ang = np.radians(np.linspace(a0, a1, ns))
        L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; L = L / max(L[-1], 1e-9)
        V, UV = [], []
        for i, (r, z) in enumerate(P):
            for j, t in enumerate(ang):
                V.append((r * np.cos(t), r * np.sin(t), z)); UV.append((j / segs * uscale, L[i]))
        T, W = [], []
        for i in range(len(P) - 1):
            dr, dz = P[i + 1] - P[i]
            if abs(dr) < 1e-9 and abs(dz) < 1e-9: continue           # repeated point = hard edge
            for j in range(segs):
                p00, p01 = i * ns + j, i * ns + j + 1
                p10, p11 = (i + 1) * ns + j, (i + 1) * ns + j + 1
                tm = (ang[j] + ang[j + 1]) / 2
                w = (dz * np.cos(tm), dz * np.sin(tm), -dr)
                T += [(p00, p10, p11), (p00, p11, p01)]; W += [w, w]
        self._add(mat, V, UV, T, W, xf)

    def sweep(self, mat, path, radius, sides=12, xf=None, caps=True):
        """tube of `radius` along a polyline path (list of 3D points), smooth-ish frames"""
        P = np.asarray(path, float)
        tang = np.gradient(P, axis=0); tang /= np.linalg.norm(tang, axis=1, keepdims=True)
        up = np.array([0, 0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0, 0])
        n0 = np.cross(tang[0], up); n0 /= np.linalg.norm(n0)
        frames = []; n = n0
        for t in tang:                                   # parallel transport
            n = n - t * (n @ t); n /= np.linalg.norm(n); frames.append((n, np.cross(t, n)))
        V, UV, T, W = [], [], [], []
        ns = sides + 1
        rr = np.broadcast_to(np.asarray(radius, float), (len(P),))
        for i, (p, (n, bnm)) in enumerate(zip(P, frames)):
            for j in range(ns):
                a = 2 * np.pi * j / sides
                d = np.cos(a) * n + np.sin(a) * bnm
                V.append(p + rr[i] * d); UV.append((j / sides, i / (len(P) - 1)))
        for i in range(len(P) - 1):
            for j in range(sides):
                p00, p01, p10, p11 = i * ns + j, i * ns + j + 1, (i + 1) * ns + j, (i + 1) * ns + j + 1
                mid = (V[p00] + V[p01] + V[p10] + V[p11]) / 4
                ctr = (P[i] + P[i + 1]) / 2
                T += [(p00, p10, p11), (p00, p11, p01)]; W += [mid - ctr] * 2
        if caps:
            for end, sgn in ((0, -1), (len(P) - 1, 1)):
                c = len(V); V.append(P[end]); UV.append((0.5, 0.5))
                for j in range(sides):
                    T.append((c, end * ns + j, end * ns + j + 1)); W.append(sgn * tang[end])
        self._add(mat, V, UV, T, W, xf)

    def box(self, mat, mn, mx, xf=None):
        x0, y0, z0 = mn; x1, y1, z1 = mx
        V, UV, T, W = [], [], [], []
        faces = [((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
                 ((-1, 0, 0), [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)]),
                 ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
                 ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
                 ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
                 ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)])]
        for nrm, q in faces:
            c = len(V); V += q; UV += [(0, 1), (1, 1), (1, 0), (0, 0)]
            T += [(c, c + 1, c + 2), (c, c + 2, c + 3)]; W += [nrm, nrm]
        self._add(mat, V, UV, T, W, xf)

    def disc(self, mat, r, segs=48, xf=None, normal_up=True, uv_square=True):
        """flat disc in local xy at z 0 facing +z (or -z); UV maps the square [-r, r] to [0, 1] (t downward)"""
        V = [(0, 0, 0)]; UV = [(0.5, 0.5)]
        for j in range(segs + 1):
            a = 2 * np.pi * j / segs
            V.append((r * np.cos(a), r * np.sin(a), 0)); UV.append((0.5 + 0.5 * np.cos(a), 0.5 - 0.5 * np.sin(a)))
        T = [(0, j + 1, j + 2) for j in range(segs)]
        W = [(0, 0, 1 if normal_up else -1)] * segs
        self._add(mat, V, UV, T, W, xf)

    # ------------------------------------------------------------------ output
    def surfaces(self, shader_prefix):
        out = []
        for mat, parts in self.parts.items():
            V, UV, T, N, off = [], [], [], [], 0
            for (v, uv, t, n) in parts:
                V.append(v); UV.append(uv); T.append(t + off); N.append(n); off += len(v)
            out.append(dict(name=mat, shader=shader_prefix + mat, verts=np.concatenate(V), normals=np.concatenate(N),
                            st=np.concatenate(UV), tris=np.concatenate(T)))
        return out

    def bounds(self):
        V = np.concatenate([v for parts in self.parts.values() for (v, _, _, _) in parts])
        return V.min(0), V.max(0)

    def save(self, path, shader_prefix, name='model'):
        return md3save(path, self.surfaces(shader_prefix), name=name)
