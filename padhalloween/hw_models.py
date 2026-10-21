"""Custom MD3/IQM map objects for wop_padhalloween (Pumpkin Hollow). All geometry and art is original and generated here.

    make() -> writes models/padhalloween/*.md3/*.iqm and their images (shaders are registered in hwlib.REG)

Scale ~64u per metre. Origin = base centre unless noted. build_halloween.py reads the geometry constants (and
layout.py) so the invisible collision brushes sit just inside the visible surfaces.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from hwlib import *
import hwlib
import layout as L


# ================================================================================================= mesh helpers
def lathe(M, rows, n=48, inward=False, uvf=None, u_tiles=4.0, vlen=256.0, deform=None, holes=None, cx=0.0, cy=0.0, a0=0.0, a1=360.0):
    """surface of revolution through rows [(r, z)...] (bottom to top); deform(a_rad, r, z) -> r; holes(a_deg, z) -> True
    skips that cell; uvf(P) -> (u, v) planar mapping (else u = angle, v = arc length / vlen)"""
    rows = np.asarray(rows, float)
    angs = np.linspace(a0, a1, n + 1)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=1))])
    tg = np.gradient(rows, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    P = np.zeros((len(rows), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(rows), len(angs), 2))
    for j, a in enumerate(angs):
        ar = math.radians(a); c, s = math.cos(ar), math.sin(ar)
        rr = rows[:, 0] if deform is None else np.array([deform(ar, r, z) for r, z in rows])
        P[:, j] = np.stack([cx + rr * c, cy + rr * s, rows[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = (a - a0) / 360 * u_tiles; UV[:, j, 1] = Ls / vlen
    if deform is not None:
        N2 = grid_normals(P)
        if (N2 * N).sum() < 0: N2 = -N2
        N = N2
    if uvf is not None:
        for i in range(len(rows)):
            for j in range(len(angs)): UV[i, j] = uvf(P[i, j])
    if holes is None:
        M.grid(P, N, UV); return P
    o = len(M.V)
    nc = len(angs)
    for i in range(len(rows)):
        for j in range(nc): M.add_v(P[i, j], N[i, j], UV[i, j])
    for i in range(len(rows) - 1):
        zm = (rows[i, 1] + rows[i + 1, 1]) / 2
        for j in range(nc - 1):
            if holes((angs[j] + angs[j + 1]) / 2, zm): continue
            a, b, c2, d = o + i * nc + j, o + i * nc + j + 1, o + (i + 1) * nc + j, o + (i + 1) * nc + j + 1
            M.tri(a, b, c2); M.tri(b, d, c2)
    return P


def offset_rows(rows, d):
    """profile rows [(r, z)...] moved inward by d along the profile normal (the shell's inner surface)"""
    rows = np.asarray(rows, float)
    tg = np.gradient(rows, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    inn = rows - pn * d
    inn[:, 0] = np.maximum(inn[:, 0], 2.0)
    return inn


def _grid(rows, n, deform, inward=False, u_tiles=8, vlen=256.0):
    """positions / normals / UVs of a lathe grid (rows x n+1)"""
    rows = np.asarray(rows, float)
    angs = np.linspace(0, 360, n + 1)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=1))])
    P = np.zeros((len(rows), n + 1, 3)); UV = np.zeros((len(rows), n + 1, 2))
    for j, a in enumerate(angs):
        ar = math.radians(a); c, s_ = math.cos(ar), math.sin(ar)
        rr = rows[:, 0] if deform is None else np.array([deform(ar, r, z) for r, z in rows])
        P[:, j] = np.stack([rr * c, rr * s_, rows[:, 1]], 1)
        UV[:, j, 0] = a / 360 * u_tiles; UV[:, j, 1] = Ls / vlen
    N = grid_normals(P)
    # orient outward (or inward)
    ref = P - np.array([0, 0, 1.0]) * P[..., 2:3]
    if (N * ref).sum() < 0: N = -N
    if inward: N = -N
    return P, N, UV, angs


def carved_shell(Mo, Mi, Mj, rows, n, thick, polys, face_angle, Rr, deform=None, u_tiles=8, vlen=256.0, ju=64.0, close_top=False, close_bottom=True,
                 depth=3, jstep=6.0):
    """a carved shell (pumpkin) with smooth cut-outs: outer surface, inner surface (offset inward by thick along the
    profile normal) and the cut faces (jambs) along every face polygon. polys: polygons in (u, z) where u = arc length at
    radius Rr from the face direction face_angle (deg, positive = counter-clockwise) and z = height. Cells crossed by a
    polygon edge are subdivided `depth` times (quadtree), so the outline steps are a few units at most."""
    rows = np.asarray(rows, float)
    rin = offset_rows(rows, thick)
    Po, No, UVo, angs = _grid(rows, n, deform, False, u_tiles, vlen)
    Pi, Ni, UVi, _ = _grid(rin, n, deform, True, u_tiles, vlen)
    zs = rows[:, 1]
    polys = [p if sum(p[k][0] * p[(k + 1) % len(p)][1] - p[(k + 1) % len(p)][0] * p[k][1] for k in range(len(p))) > 0 else p[::-1] for p in polys]
    def uz(a, z):
        da = (a - face_angle + 180) % 360 - 180
        return math.radians(da) * Rr, z
    def inside(a, z):
        u, zz = uz(a, z)
        if abs(u) > math.pi * Rr * 0.6: return False
        return any(pip(p, u, zz) for p in polys)
    def bil(G, i, j, s, t):
        return (G[i, j] * (1 - s) * (1 - t) + G[i, j + 1] * s * (1 - t) + G[i + 1, j] * (1 - s) * t + G[i + 1, j + 1] * s * t)
    def emit(M, P, N, UV, i, j, s0, s1, t0, t1, flip=False):
        o = len(M.V)
        for (s_, t_) in ((s0, t0), (s1, t0), (s1, t1), (s0, t1)):
            M.add_v(bil(P, i, j, s_, t_), bil(N, i, j, s_, t_), tuple(bil(UV, i, j, s_, t_)))
        M.tri(o, o + 1, o + 2); M.tri(o, o + 2, o + 3)
    def cell(i, j, s0, s1, t0, t1, d):
        a0 = angs[j] + (angs[j + 1] - angs[j]) * s0; a1 = angs[j] + (angs[j + 1] - angs[j]) * s1
        z0 = zs[i] + (zs[i + 1] - zs[i]) * t0; z1 = zs[i] + (zs[i + 1] - zs[i]) * t1
        samp = [inside(a, z) for a in (a0, (a0 + a1) / 2, a1) for z in (z0, (z0 + z1) / 2, z1)]
        if not any(samp):
            emit(Mo, Po, No, UVo, i, j, s0, s1, t0, t1); emit(Mi, Pi, Ni, UVi, i, j, s0, s1, t0, t1); return
        if all(samp) and d >= 1: return
        if d >= depth:
            if not inside((a0 + a1) / 2, (z0 + z1) / 2):
                emit(Mo, Po, No, UVo, i, j, s0, s1, t0, t1); emit(Mi, Pi, Ni, UVi, i, j, s0, s1, t0, t1)
            return
        sm, tm = (s0 + s1) / 2, (t0 + t1) / 2
        for (a_, b_, c_, d_) in ((s0, sm, t0, tm), (sm, s1, t0, tm), (s0, sm, tm, t1), (sm, s1, tm, t1)):
            cell(i, j, a_, b_, c_, d_, d + 1)
    for i in range(len(rows) - 1):
        for j in range(n):
            cell(i, j, 0.0, 1.0, 0.0, 1.0, 0)
    # jambs along the polygon outlines
    def locate(u, z):
        a = (face_angle + math.degrees(u / Rr)) % 360
        j = min(n - 1, int(a / 360 * n)); s_ = a / 360 * n - j
        z = min(max(z, zs[0]), zs[-1] - 1e-6)
        i = int(np.searchsorted(zs, z, side='right') - 1); i = min(max(i, 0), len(zs) - 2)
        t_ = (z - zs[i]) / (zs[i + 1] - zs[i])
        return i, j, s_, t_
    for p in polys:
        m = len(p)
        for k in range(m):
            (u0, z0), (u1, z1) = p[k], p[(k + 1) % m]
            Ln = math.hypot(u1 - u0, z1 - z0); ns = max(1, int(Ln / jstep))
            for q in range(ns):
                ua, za = u0 + (u1 - u0) * q / ns, z0 + (z1 - z0) * q / ns
                ub, zb = u0 + (u1 - u0) * (q + 1) / ns, z0 + (z1 - z0) * (q + 1) / ns
                if za < zs[0] - 1 and zb < zs[0] - 1: continue
                A_, B_ = locate(ua, za), locate(ub, zb)
                oa, ob = bil(Po, *A_), bil(Po, *B_); ia, ib = bil(Pi, *A_), bil(Pi, *B_)
                # normal: towards the polygon interior (left of the edge for a counter-clockwise polygon)
                lu, lz = -(zb - za), (ub - ua)
                l = math.hypot(lu, lz) + 1e-9
                C_ = locate((ua + ub) / 2 + lu / l * 2, (za + zb) / 2 + lz / l * 2)
                nrm = bil(Po, *C_) - (oa + ob) / 2
                L0 = np.linalg.norm(ob - oa)
                Mj.poly([oa, ob, ib, ia], nrm, [(0, 0), (L0 / ju, 0), (L0 / ju, thick / ju), (0, thick / ju)])
    if close_bottom:
        # the inner surface starts above the ground (offset along the bottom's outward-down normal): seal the gap so the
        # culled back of the outer shell can't be seen through from inside
        for j in range(n):
            am = (angs[j] + angs[j + 1]) / 2
            if inside(am, zs[0] + 1): continue
            a = math.radians(am)
            L0 = np.linalg.norm(Po[0, j + 1] - Po[0, j])
            Mj.poly([Po[0, j], Pi[0, j], Pi[0, j + 1], Po[0, j + 1]], (-math.cos(a), -math.sin(a), 0.6),
                    [(0, 0), (0, thick / ju), (L0 / ju, thick / ju), (L0 / ju, 0)])
    if close_top:
        for j in range(n):
            a = math.radians((angs[j] + angs[j + 1]) / 2)
            L0 = np.linalg.norm(Po[-1, j + 1] - Po[-1, j])
            Mj.poly([Po[-1, j], Po[-1, j + 1], Pi[-1, j + 1], Pi[-1, j]], (-math.cos(a), -math.sin(a), 0.3),
                    [(0, 0), (L0 / ju, 0), (L0 / ju, thick / ju), (0, thick / ju)])
    return Po, Pi


def pip(poly, x, y):
    """point in polygon (list of (x, y))"""
    inside = False
    n = len(poly)
    for k in range(n):
        (x0, y0), (x1, y1) = poly[k], poly[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0: inside = not inside
    return inside


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def plank(M, a, b, w, t, up=(0, 0, 1), tile=128.0):
    """board from point a to b (centre line), width w (along `up` x dir), thickness t"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; Ln = np.linalg.norm(d); d /= Ln
    up = np.asarray(up, float); s = np.cross(d, up)
    if np.linalg.norm(s) < 1e-6: s = np.cross(d, [1, 0, 0])
    s /= np.linalg.norm(s); u2 = np.cross(s, d)
    m = Mesh()
    rbox(m, (-w / 2, 0, -t / 2), (w / 2, Ln, t / 2), r=min(1.0, t / 3), k=2, tile=tile)
    R = np.stack([s, d, u2], 1)
    M.add(m, R, a)


def scale_mesh(m, s):
    for i, v in enumerate(m.V): m.V[i] = v * s
    return m


def tri_up(M, p0, p1, p2, uv=((0, 0), (1, 0), (0.5, 1))):
    P = [np.asarray(p, float) for p in (p0, p1, p2)]
    n = np.cross(P[1] - P[0], P[2] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, list(uv))


# ================================================================================================= textures (models)
def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


def tex_siding(w=256, h=256, seed=1, col=(92, 86, 104)):
    """weathered clapboard: 8 overlapping boards with shadow lines and peeling paint"""
    x, y = xy(w, h)
    b = (y * 8) % 1.0
    c = np.zeros((h, w, 3), np.float32) + C(col) * (0.82 + 0.25 * b)[..., None]
    c = np.where((b > 0.93)[..., None], C(col) * 0.45, c)
    gr = np.asarray(img(noise(w, 1, seed, h) * 40 + 128).resize((w // 16, h)).resize((w, h)), np.float32) - 128
    c += gr[..., None] * 0.25
    peel = np.clip(noise(w, 4, seed + 1, h) - 1.3, 0, 1)[..., None]
    c = lerp(c, C((70, 56, 44)), np.clip(peel * 2, 0, 1))
    grime = np.clip(noise(w, 20, seed + 2, h) * 0.5, 0, 1)[..., None]
    return c * (1 - grime * 0.3)


def tex_slate(n=256, seed=3, col=(54, 52, 64)):
    """fish-scale slates"""
    x, y = xy(n)
    rows = 8
    r = np.floor(y * rows)
    off = (r % 2) * 0.5 / 6
    u = ((x + off) * 6) % 1.0
    v = (y * rows) % 1.0
    edge = np.hypot(u - 0.5, v * 1.1) > 0.55
    tone = np.random.default_rng(seed).uniform(-10, 10, (rows + 1, 7))[r.astype(int) % (rows + 1), np.floor((x + off) * 6).astype(int) % 7]
    c = np.zeros((n, n, 3), np.float32) + C(col) + tone[..., None]
    c *= (0.65 + 0.35 * (1 - v))[..., None]
    c = np.where(edge[..., None], c * 0.55, c)
    moss = np.clip(noise(n, 12, seed + 1) - 0.9, 0, 1)[..., None]
    return lerp(c + N3(n, 1, seed + 2, 5), C((60, 74, 40)), moss)


def tex_wood_shingle(n=256, seed=5, col=(84, 66, 48)):
    x, y = xy(n)
    rows = 6
    r = np.floor(y * rows).astype(int)
    off = (r % 2) * 0.09
    k = np.floor((x + off) * 7 + noise(n, 30, seed, n) * 0.3).astype(int)
    tone = np.random.default_rng(seed).uniform(-18, 18, (rows + 1, 9))[r % (rows + 1), k % 9]
    v = (y * rows) % 1.0
    c = np.zeros((n, n, 3), np.float32) + C(col) + tone[..., None]
    c *= (0.6 + 0.4 * (1 - v))[..., None]
    gap = ((x + off) * 7 + noise(n, 30, seed, n) * 0.3) % 1.0
    c = np.where((gap < 0.05)[..., None], c * 0.5, c)
    moss = np.clip(noise(n, 10, seed + 3) - 0.5, 0, 1)[..., None]
    return lerp(c + N3(n, 1, seed + 2, 6), C((64, 84, 40)), moss * 0.8)


def tex_pumpkin(w=256, h=256, seed=7, base=(232, 112, 20), groove=(150, 60, 10), ribs=1):
    """u wraps round the pumpkin (one rib per 1/ribs of u): darker in the grooves, fine vertical streaks"""
    x, y = xy(w, h)
    g = np.abs(np.cos(x * math.pi * ribs))            # 1 at crests, 0 at grooves
    c = lerp(C(groove), C(base), (g ** 0.35)[..., None])
    streak = np.asarray(img(noise(w, 0.8, seed, h) * 40 + 128).resize((w, h // 16)).resize((w, h)), np.float32) - 128
    c += streak[..., None] * 0.25 + N3(w, 6, seed + 1, 6, h)
    spot = np.clip(noise(w, 3, seed + 2, h) - 1.8, 0, 1)[..., None]
    return lerp(c, C((120, 90, 40)), spot)


def tex_flesh(n=128, seed=9):
    c = fill(n, (236, 168, 60), 8, seed) + N3(n, 2, seed + 1, 14) * C((1, 0.8, 0.3))
    return c


def tex_bark(w=256, h=512, seed=11, col0=(38, 32, 30), col1=(96, 86, 76)):
    x, y = xy(w, h)
    ridge = np.clip(np.sin(x * 2 * math.pi * 7 + noise(w, 20, seed, h) * 2.0) * 0.5 + 0.5, 0, 1)
    gro = np.asarray(img(noise(w, 2, seed + 1, h) * 50 + 128).resize((w // 6, h)).resize((w, h)), np.float32) / 255
    c = lerp(C(col0), C(col1), (ridge ** 1.5 * 0.75 + gro * 0.25)[..., None])
    lichen = np.clip(noise(w, 6, seed + 3, h) - 1.2, 0, 1)[..., None]
    return lerp(c + N3(w, 0.8, seed + 2, 6, h), C((110, 120, 90)), lichen)


def tex_tomb_face(text, w=256, h=256, seed=13, base=(128, 126, 120)):
    c = fill(w, base, 8, seed, h) + N3(w, 5, seed + 1, 8, h)
    im = img(c).convert('RGB')
    d = ImageDraw.Draw(im)
    lines = text.split('\n')
    y = h * 0.22
    for k, l in enumerate(lines):
        sz = int(h * (0.16 if k == 0 else 0.075))
        f = font(sz, True)
        bb = d.textbbox((0, 0), l, font=f)
        x = (w - (bb[2] - bb[0])) / 2 - bb[0]
        d.text((x + 1, y + 1), l, font=f, fill=(170, 168, 160))
        d.text((x, y), l, font=f, fill=(46, 44, 42))
        y += sz * 1.35
    a = np.asarray(im, np.float32)
    moss = np.clip(noise(w, 9, seed + 2, h) - 0.7, 0, 1)[..., None] * np.clip(y_ramp(w, h), 0, 1)[..., None]
    return lerp(a, C((60, 80, 40)), moss)


def y_ramp(w, h):
    return np.linspace(0, 1.3, h)[:, None] * np.ones((1, w))


def tex_corn(w=256, h=512, seed=15):
    """a dense curtain of corn stalks with long leaves and a few ears (alpha)"""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for k in range(14):
        x = (k + r.uniform(-0.3, 0.3)) * w / 13
        top = r.uniform(0, h * 0.12)
        sc = (int(r.uniform(96, 120)), int(r.uniform(88, 108)), int(r.uniform(44, 58)))
        for ox in (-w, 0, w):
            d.line([(x + ox, h), (x + ox + r.uniform(-6, 6), top)], fill=sc + (255,), width=int(r.uniform(4, 7)))
        for j in range(7):                                  # leaves arching out
            y0 = top + (h - top) * (0.15 + 0.12 * j) + r.uniform(-10, 10)
            sgn = 1 if (j + k) % 2 else -1
            L0 = r.uniform(50, 110)
            lc = (int(r.uniform(70, 110)), int(r.uniform(80, 110)), int(r.uniform(34, 52)))
            pts = [(x, y0)]
            for t in np.linspace(0.1, 1, 7):
                pts.append((x + sgn * L0 * t, y0 - 40 * math.sin(t * 2.2) + 30 * t * t))
            for ox in (-w, 0, w):
                pp = [(px + ox, py) for (px, py) in pts]
                d.line(pp, fill=lc + (255,), width=int(r.uniform(5, 9)))
        if r.random() < 0.6:                               # ear of corn
            ye = top + (h - top) * r.uniform(0.35, 0.55)
            for ox in (-w, 0, w):
                d.ellipse((x + ox + 2, ye, x + ox + 14, ye + 46), fill=(170, 130, 60, 255))
                d.line([(x + ox + 8, ye), (x + ox + 2, ye - 18)], fill=(150, 120, 60, 255), width=3)
        # tassel
        for ox in (-w, 0, w):
            for t in range(5):
                d.line([(x + ox, top), (x + ox + r.uniform(-14, 14), top - r.uniform(6, 20) + 20)], fill=(140, 112, 60, 255), width=2)
    a = np.asarray(im, np.float32)
    rgb = a[..., :3] * (0.85 + 0.15 * noise(w, 2, seed + 1, h)[..., None])
    return rgb, a[..., 3]


def tex_web(n=256, seed=17):
    """a corner cobweb (alpha): radial threads + spiral"""
    im = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(im)
    for k in range(9):
        a = math.radians(k * 90 / 8)
        d.line([(0, 0), (n * 1.2 * math.cos(a), n * 1.2 * math.sin(a))], fill=200, width=1)
    for rr in np.arange(18, n * 1.3, 16):
        pts = []
        for k in range(9):
            a = math.radians(k * 90 / 8); r2 = rr * (0.92 + 0.08 * math.sin(k * 3))
            pts.append((r2 * math.cos(a), r2 * math.sin(a)))
        d.line(pts, fill=150, width=1)
    al = np.asarray(im.filter(ImageFilter.GaussianBlur(0.4)), np.float32) * 1.2
    return np.zeros((n, n, 3), np.float32) + 230, al


def tex_leaf(n=128, seed=19, col=(46, 84, 34)):
    """pumpkin leaf (alpha): lobed, veined"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.95
    a = np.arctan2(dx, -dy); r = np.hypot(dx, dy)
    lob = 0.75 * (0.75 + 0.25 * np.cos(a * 5)) * np.clip(1 - np.abs(a) / 2.0, 0, 1)
    m = r < lob
    c = np.zeros((n, n, 3), np.float32) + C(col) + N3(n, 2, seed, 10)
    vein = (np.abs(np.sin(a * 2.5 * 2)) < 0.06) & m
    c[vein] = C((130, 150, 90))
    return c, np.where(m, 255.0, 0.0)


def tex_burlap(n=128, seed=21, col=(160, 130, 90)):
    x, y = xy(n)
    weave = (np.sin(x * n * 0.9) * np.sin(y * n * 0.9))
    return fill(n, col, 6, seed) + weave[..., None] * 14


def tex_plaid(n=128, seed=23, a=(140, 40, 30), b=(40, 30, 30)):
    x, y = xy(n)
    s = ((np.floor(x * 8) % 2) + (np.floor(y * 8) % 2)) / 2
    c = lerp(C(b), C(a), s[..., None]) + N3(n, 1, seed, 8)
    patch = (np.abs(x - 0.7) < 0.12) & (np.abs(y - 0.3) < 0.1)
    c[patch] = C((70, 90, 120)) + N3(n, 1, seed + 1, 6)[patch]
    return c


def tex_glowface(n=64, col=(255, 190, 60)):
    x, y = xy(n)
    return C(col) * (0.85 + 0.15 * np.sin(x * 9 + y * 7))[..., None]


def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((40, 30, 60)), C((190, 170, 200)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_books(w=256, h=128, seed=27):
    r = np.random.default_rng(seed)
    im = Image.new('RGB', (w, h), (30, 22, 18)); d = ImageDraw.Draw(im)
    x = 0
    while x < w:
        bw = int(r.uniform(8, 20)); bh = int(r.uniform(h * 0.65, h * 0.95))
        col = tuple(int(v) for v in r.choice([(90, 20, 20), (30, 50, 30), (40, 30, 60), (110, 80, 40), (20, 20, 24), (70, 50, 30)]))
        d.rectangle((x, h - bh, x + bw - 1, h), fill=col)
        d.line([(x + 2, h - bh + 10), (x + bw - 3, h - bh + 10)], fill=(180, 150, 70))
        d.line([(x + 2, h - 12), (x + bw - 3, h - 12)], fill=(180, 150, 70))
        x += bw
    return np.asarray(im, np.float32) + N3(w, 1, seed + 1, 6, h)


def tex_wing(n=128, seed=29):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((30, 22, 28))
    ribs = np.abs(np.sin(np.arctan2(y - 0.1, x - 0.5) * 5)) < 0.08
    c[ribs] = C((14, 10, 12))
    scallop = y > 0.85 - 0.1 * np.abs(np.sin(x * math.pi * 3))
    return c, np.where(scallop, 0.0, 255.0)


def tex_ghost(n=128, seed=31):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((170, 200, 230)) * (0.7 + 0.3 * noise(n, 6, seed)[..., None] * 0.5)
    eyes = (np.hypot((x - 0.42) * 1.0, (y - 0.3) * 0.7) < 0.05) | (np.hypot((x - 0.58), (y - 0.3) * 0.7) < 0.05)
    mouth = np.hypot((x - 0.5) * 1.2, (y - 0.45) * 0.8) < 0.05
    c[eyes | mouth] = 0
    return c


def make_textures():
    T('siding', tex_siding()); T('siding_dark', tex_siding(256, 256, 2, (58, 54, 66)))
    T('trim', fill(64, (176, 170, 156), 6, 31)); T('trim_dark', fill(64, (36, 40, 38), 5, 32))
    T('slate', tex_slate()); T('shingle', tex_wood_shingle()); T('shingle_moss', tex_wood_shingle(256, 6, (70, 70, 46)))
    T('shutter', tex_siding(128, 128, 33, (46, 58, 50)))
    T('door_red', fill(64, (90, 22, 24), 6, 34)); T('iron', fill(64, (52, 52, 58), 5, 35)); T('brass', fill(64, (180, 140, 60), 8, 36))
    T('glass_dark', fill(64, (30, 34, 40), 3, 37)); T('win_glow', tex_glowface(64, (255, 170, 70)))
    T('marble', fill(128, (190, 188, 182), 6, 38) + N3(128, 3, 39, 8)); T('stone_m', fill(128, (120, 118, 112), 9, 40))
    T('plaster_c', fill(128, (150, 156, 120), 8, 41)); T('beam', fill(64, (44, 32, 24), 6, 42))
    T('pumpkin', tex_pumpkin()); T('pumpkin_pale', tex_pumpkin(256, 256, 8, (236, 200, 150), (180, 140, 100)))
    T('pumpkin_green', tex_pumpkin(256, 256, 9, (120, 140, 60), (60, 80, 30)))
    T('pumpkin_red', tex_pumpkin(256, 256, 10, (200, 70, 24), (120, 40, 14)))
    T('flesh', tex_flesh()); T('stem', fill(64, (90, 100, 50), 8, 43)); T('glowface', tex_glowface())
    T('glowface_g', tex_glowface(64, (150, 255, 90)))
    c, a = tex_leaf(); T('leaf', c, a)
    T('bark', tex_bark()); T('bark_pale', tex_bark(256, 512, 12, (60, 56, 52), (130, 124, 116)))
    T('rope', fill(64, (150, 124, 84), 10, 44))
    for k, txt in enumerate(['R.I.P.\nHERE LIES\nA PAD WHO\nFORGOT TO DUCK', 'R.I.P.\nI TOLD YOU\nI WAS SICK', 'R.I.P.\nB. ALLOONY\n1999 - 2026',
                             'R.I.P.\nGONE BUT NOT\nFORGOTTEN']):
        T(f'tomb_{k}', tex_tomb_face(txt, seed=50 + k))
    T('tomb_side', fill(128, (124, 122, 116), 8, 55) + N3(128, 6, 56, 8))
    c, a = tex_corn(); T('corn', c, a)
    c, a = tex_web(); T('web', c, a)
    T('burlap', tex_burlap()); T('plaid', tex_plaid()); T('felt', fill(64, (40, 30, 44), 5, 57)); T('felt_brown', fill(64, (80, 60, 36), 5, 58))
    T('straw', fill(64, (200, 170, 90), 12, 59)); T('fur', fill(64, (18, 16, 20), 4, 60)); T('eye_g', tex_glowface(32, (190, 255, 80)))
    T('eye_r', tex_glowface(32, (255, 70, 30)))
    T('wax', fill(64, (230, 220, 190), 4, 61)); T('lacquer', fill(64, (14, 14, 16), 3, 62)); T('velvet', fill(64, (100, 20, 30), 6, 63))
    T('wood_dark', fill(128, (52, 36, 26), 6, 64) + N3(128, 1, 65, 6)); T('wood', fill(128, (110, 80, 50), 8, 66) + N3(128, 1, 67, 8))
    T('wood_grey', fill(128, (104, 100, 92), 8, 68)); T('books', tex_books())
    T('bottle_g', tex_glowface(32, (90, 255, 110))); T('bottle_p', tex_glowface(32, (200, 110, 255))); T('bottle_o', tex_glowface(32, (255, 140, 40)))
    T('crystal', tex_glowface(64, (190, 140, 255))); T('ember', tex_glowface(64, (200, 70, 20)))
    import hw_textures as _HT
    T('flame', _HT.flame())
    c, a = tex_wing(); T('wing', c, a); T('ghost', tex_ghost())
    T('env', tex_env()); T('cloth_black', fill(64, (22, 20, 26), 4, 69)); T('bone', fill(64, (220, 214, 190), 5, 70))
    T('copper', fill(64, (150, 80, 40), 8, 71)); T('wheel', fill(64, (70, 40, 26), 6, 72)); T('hay', __import__('hw_textures').hay())
    T('dirt_m', fill(64, (70, 54, 40), 8, 73)); T('mossstone', fill(128, (90, 96, 80), 9, 74) + N3(128, 4, 75, 10))
    T('red_cloth', fill(64, (120, 24, 30), 6, 76)); T('piano', fill(64, (10, 10, 12), 2, 77)); T('keys', tex_keys())


def tex_keys(w=256, h=32):
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + 225
    c[(x * 26 % 1) < 0.06] = 40
    blk = ((x * 26 % 7 > 0.5) & (x * 26 % 7 < 6.5)) & (y < 0.6) & (np.isin(np.floor(x * 26) % 7, [0, 1, 3, 4, 5]))
    c[blk & ((x * 26 % 1) > 0.65)] = 15
    return c


# ================================================================================================= shared geometry
GP_ROWS = [(330, 0), (372, 16), (404, 40), (430, 90), (446, 170), (448, 250), (440, 330), (416, 400), (370, 460), (300, 506),
           (230, 534), (180, 546), (L.GP_LID, 550)]
GP_THICK = 40
GP_G = 0.03                                   # rib groove depth (fraction of the radius)
GP_RIBS = 18
JACK = {'s': 40, 'm': 64, 'l': 96}           # small jack-o'-lantern radii (vertex lit, faces glow)
CAUL_PROFILE = [(L.CAUL_RIM_R - 30, L.CAUL_BOT), (250, 70), (280, 120), (L.CAUL_R, 170), (282, 220), (262, 262), (244, 290),
                (L.CAUL_RIM_R, L.CAUL_RIM - 10), (L.CAUL_RIM_R + 14, L.CAUL_RIM - 4), (L.CAUL_RIM_R + 14, L.CAUL_RIM + 6),
                (L.CAUL_IN, L.CAUL_RIM + 6)]
TOMB_KINDS = ('tomb_arch', 'tomb_cross', 'tomb_celtic', 'tomb_obelisk', 'tomb_slab', 'tomb_broken')
TOMB_DIM = {'tomb_arch': (88, 20, 118), 'tomb_cross': (70, 18, 150), 'tomb_celtic': (80, 20, 164), 'tomb_obelisk': (60, 60, 230),
            'tomb_slab': (96, 26, 92), 'tomb_broken': (84, 20, 80)}
HAY = (128, 64, 64)                           # hay bale size (x, y, z)
LAMP_H = 260
SCARE_H = 380
CORN_T = 14                                   # corn curtain half thickness (planes at +-CORN_T from the wall centre)
TREE_BIG = None


# ================================================================================================= pumpkins
def rib_deform(R_ref, g=0.06, ribs=GP_RIBS, lump=0.0, seed=0):
    ph = np.random.default_rng(seed).uniform(0, 6.28, 3)
    def f(a, r, z):
        rr = r * (1 - g * (1 - abs(math.cos(ribs * a / 2))))
        if lump: rr *= 1 + lump * math.sin(a * 2 + ph[0]) * math.sin(z / R_ref * 3 + ph[1])
        return rr
    return f


def face_polys(R_ref, s=1.0, style=0):
    """jack-o'-lantern face polygons in (u = arc length from the face centre, z) for a pumpkin of radius R_ref and
    height 2*R_ref*0.86 (z relative to the base). style 0: classic triangle eyes, jagged grin; 1: angry slit eyes"""
    H = R_ref * 1.72
    def P(pts): return [(u * R_ref, z * H) for (u, z) in pts]
    if style == 0:
        eyes = [P([(-0.62, 0.55), (-0.18, 0.55), (-0.40, 0.78)]), P([(0.18, 0.55), (0.62, 0.55), (0.40, 0.78)])]
    else:
        eyes = [P([(-0.62, 0.58), (-0.16, 0.54), (-0.20, 0.66), (-0.58, 0.72)]), P([(0.16, 0.54), (0.62, 0.58), (0.58, 0.72), (0.20, 0.66)])]
    nose = P([(-0.10, 0.44), (0.10, 0.44), (0.0, 0.54)])
    m = []
    xs = np.linspace(-0.72, 0.72, 9)
    for i, u in enumerate(xs):                                   # top lip with teeth
        m.append((u, 0.36 - (0.06 if i % 2 else 0) + 0.10 * (u / 0.72) ** 2))
    for i, u in enumerate(xs[::-1]):                             # bottom lip
        m.append((u, 0.22 + (0.05 if i % 2 == 1 and 2 < i < 6 else 0) + 0.12 * (u / 0.72) ** 2 - 0.04))
    mouth = P(m)
    return eyes + [nose, mouth]


def jack(name, R, style=0, kind='orange', lit=True, seed=1):
    """small/medium carved jack-o'-lantern (vertex lit outside, glowing flickering inside)"""
    X = Model()
    tex = {'orange': 'pumpkin', 'pale': 'pumpkin_pale', 'red': 'pumpkin_red', 'green': 'pumpkin_green'}[kind]
    out_sh = S(tex, 'vl', tag=f'j{seed}')
    in_sh = S('glowface', 'flicker', ph=round((seed * 0.37) % 1, 2)) if lit else S('flesh', 'vl')
    jam_sh = S('flesh', 'vl', tag='j')
    H = R * 1.72
    prof = [(R * 0.62, 0), (R * 0.85, H * 0.06), (R * 0.97, H * 0.22), (R, H * 0.45), (R * 0.95, H * 0.66), (R * 0.78, H * 0.86),
            (R * 0.5, H * 0.97), (R * 0.12, H)]
    zs = sorted(set(np.round(np.linspace(0, H, 14), 2)) | {round(z, 2) for (_, z) in prof})
    rows = [(float(np.interp(z, [p[1] for p in prof], [p[0] for p in prof])), z) for z in zs]
    polys = face_polys(R, style=style)
    if lit:
        carved_shell(X.mesh(out_sh), X.mesh(in_sh), X.mesh(jam_sh), rows, 40, max(3, R * 0.08), polys, 270.0, R,
                     deform=rib_deform(R, 0.08, 12, 0.02, seed), u_tiles=6, depth=2, jstep=max(3.0, R / 10))
    else:
        lathe(X.mesh(out_sh), rows, 48, deform=rib_deform(R, 0.08, 12, 0.03, seed), u_tiles=6)
    stem(X, R, H, seed)
    return save(name, X)


def stem(X, R, H, seed, sh=None):
    r = np.random.default_rng(seed)
    sh = sh or S('stem', 'vl')
    a = r.uniform(0, 6.28)
    pts = [(0, 0, H - 4), (0, 0, H + R * 0.2), (R * 0.08 * math.cos(a), R * 0.08 * math.sin(a), H + R * 0.32)]
    tube(X.mesh(sh), pts, [R * 0.11, R * 0.09, R * 0.07], nseg=7)


def plain_pumpkin(name, R, kind='orange', seed=1, squash=1.0, lit_kind='vl'):
    """uncarved pumpkin (cover); lit_kind 'lm' for big ones"""
    X = Model()
    tex = {'orange': 'pumpkin', 'pale': 'pumpkin_pale', 'red': 'pumpkin_red', 'green': 'pumpkin_green'}[kind]
    sh = S(tex, lit_kind, tag=f'p{seed}')
    H = R * 1.6 * squash
    prof = [(R * 0.55, 0), (R * 0.85, H * 0.07), (R * 0.98, H * 0.25), (R, H * 0.45), (R * 0.94, H * 0.68), (R * 0.75, H * 0.88),
            (R * 0.42, H * 0.98), (R * 0.1, H * 0.94)]
    zs = sorted(set(np.round(np.linspace(0, H * 0.98, 16), 2)) | {round(z, 2) for (_, z) in prof})
    rows = [(float(np.interp(z, [p[1] for p in prof][:7], [p[0] for p in prof][:7])), z) for z in zs]
    rows.append((R * 0.1, H * 0.94))
    lathe(X.mesh(sh), rows, 48, deform=rib_deform(R, 0.08, 12, 0.03, seed), u_tiles=6)
    stem(X, R, H * 0.94, seed, S('stem', lit_kind, tag='s'))
    return save(name, X)


def gp_face_polys():
    """the Great Pumpkin's carved face in (u, z): u = arc length at radius 440 from the face direction. The grin reaches
    the ground in the middle (the door), triangle eyes are the windows, a triangle nose."""
    top = lambda u: 196 + 46 * (u / 250) ** 2
    bot = lambda u: -10 if abs(u) < 176 else -10 + 120 * ((abs(u) - 176) / 74) ** 1.4
    mouth = []
    for u in np.linspace(-250, 250, 21):                      # bottom edge, left to right
        mouth.append((u, bot(u)))
    up = []
    for u in np.linspace(250, -250, 41):                      # top edge, right to left, with two square teeth near the corners
        z = top(u)
        if 178 < abs(u) < 222: z -= 44
        up.append((u, z))
    mouth += up
    eye_l = [(-340, 300), (-112, 300), (-200, 466)]
    eye_r = [(112, 300), (340, 300), (200, 466)]
    nose = [(-54, 250), (54, 250), (0, 336)]
    return [mouth, nose, eye_l, eye_r]


def great_pumpkin():
    """the Great Pumpkin: a hollow house-sized jack-o'-lantern. Mouth = door (2 collision wedges round GP_FACE), the eyes
    are windows, the lid is cut off (lid hole at the top), flesh inside. Origin = base centre."""
    X = Model()
    out_sh = S('pumpkin', 'lm', tag='gp'); in_sh = S('flesh', 'lm', tag='gpi'); jam_sh = S('flesh', 'lm', tag='gpj')
    face = L.GP_FACE
    Rr = 440.0
    polys = gp_face_polys()
    zs = sorted(set([z for (_, z) in GP_ROWS] + list(range(0, 470, 24))))
    rows = [(float(np.interp(z, [p[1] for p in GP_ROWS], [p[0] for p in GP_ROWS])), float(z)) for z in zs]
    carved_shell(X.mesh(out_sh), X.mesh(in_sh), X.mesh(jam_sh), rows, 96, GP_THICK, polys, face, Rr, deform=rib_deform(Rr, GP_G, GP_RIBS),
                 u_tiles=GP_RIBS / 2, vlen=600, close_top=True, depth=3, jstep=10)
    # vines curling down from the top
    vine = S('stem', 'lm', tag='gpv')
    for k in range(5):
        a = math.radians(face + 100 + k * 40)
        pts = []
        for t in np.linspace(0, 1, 14):
            z = 548 - t * 300
            r = float(np.interp(z, [p[1] for p in GP_ROWS], [p[0] for p in GP_ROWS])) + 6
            aa = a + 0.25 * math.sin(t * 6 + k)
            pts.append((r * math.cos(aa), r * math.sin(aa), z))
        tube(X.mesh(vine), pts, np.linspace(9, 4, 14), nseg=6)
    # floor inside (flesh-coloured boards are brushes); a few seeds stuck to the inner wall
    seed_sh = S('trim', 'lm', tag='seed')
    rng = np.random.default_rng(4)
    for k in range(40):
        a = rng.uniform(0, 2 * math.pi); z = rng.uniform(60, 420)
        if abs(((math.degrees(a) - face + 180) % 360) - 180) < 70: continue
        r = float(np.interp(z, [p[1] for p in GP_ROWS], [p[0] for p in GP_ROWS])) - GP_THICK - 3
        ellipsoid(X.mesh(seed_sh), (r * math.cos(a), r * math.sin(a), z), 7, 4, 2.5, 6, 4, R=rot_z(a) @ rot_axis((0, 1, 0), math.pi / 2))
    return save('great_pumpkin', X)


def gp_lid():
    """the cut-off lid lying on the ground beside the Great Pumpkin, stem and all (origin = base centre)"""
    X = Model()
    sh = S('pumpkin', 'lm', tag='lid'); fl = S('flesh', 'lm', tag='lid')
    rows = [(L.GP_LID + 10, 0), (L.GP_LID - 10, 30), (100, 46), (40, 54), (0, 56)]
    lathe(X.mesh(sh), rows, 48, deform=rib_deform(440, GP_G, GP_RIBS), u_tiles=GP_RIBS / 2 * (L.GP_LID / 440))
    disc(X.mesh(fl), L.GP_LID + 10, 0.5, up=False, n=48)
    tube(X.mesh(S('stem', 'lm', tag='lid')), [(0, 0, 50), (0, 0, 120), (20, 6, 160), (46, 10, 170)], [30, 26, 20, 16], nseg=10)
    return save('gp_lid', X)


def pumpkin_leaves(name, seed=3, n=9, R=150):
    X = Model()
    sh = S('leaf', 'alpha', tag='')
    vine = S('stem', 'vl', tag='v')
    r = np.random.default_rng(seed)
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(R * 0.2, R)
        cx, cy = d * math.cos(a), d * math.sin(a)
        s = r.uniform(40, 70); rot = r.uniform(0, 2 * math.pi)
        z = 2 + k * 0.4
        c, s_ = math.cos(rot), math.sin(rot)
        P = [(cx + (-s * c - 0 * s_), cy + (-s * s_), z + 4), (cx + s * c, cy + s * s_, z + 4),
             (cx + s * c - 2 * s * s_, cy + s * s_ + 2 * s * c, z + 16), (cx - s * c - 2 * s * s_, cy - s * s_ + 2 * s * c, z + 16)]
        X.mesh(sh).poly([np.array(p) for p in P], (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
        tube(X.mesh(vine), [(0, 0, 3), (cx * 0.5 + r.uniform(-20, 20), cy * 0.5 + r.uniform(-20, 20), 4), (cx, cy, 5)], 3, nseg=5)
    return save(name, X)


# ================================================================================================= trees
def gnarl_path(p0, d0, length, seg, rng, bend=0.35, up=0.0):
    pts = [np.asarray(p0, float)]
    d = np.asarray(d0, float); d /= np.linalg.norm(d)
    for i in range(seg):
        d = d + rng.normal(0, bend, 3) * np.array([1, 1, 0.6]) + np.array([0, 0, up])
        d /= np.linalg.norm(d)
        pts.append(pts[-1] + d * length / seg)
    return np.array(pts)


def dead_tree(name, H=900, seed=1, spread=1.0, trunk_r=60, lanterns=(), ropes=(), kind='lm', branches=7, avoid=None, t0=0.45):
    """gnarled dead tree: noisy trunk, flaring roots on the ground, forking crooked branches with twigs.
    lanterns: [(branch index, t along it, drop)] hang glowing lanterns; ropes: same, a noose-free rope stub"""
    X = Model()
    rng = np.random.default_rng(seed)
    bark = S('bark', kind, tag=name[:4]) if kind == 'lm' else S('bark', 'vl', tag=name[:4])
    # trunk: leaning, twisting tube
    tp = [np.array([0, 0, -2.0])]
    d = np.array([0, 0, 1.0])
    for i in range(10):
        d = d + rng.normal(0, 0.12, 3) * np.array([1, 1, 0]); d /= np.linalg.norm(d)
        tp.append(tp[-1] + d * H * 0.6 / 10)
    tp = np.array(tp)
    tr = np.linspace(trunk_r, trunk_r * 0.55, len(tp))
    tr[0] *= 1.35; tr[1] *= 1.12
    tube(X.mesh(bark), tp, tr, nseg=10, utiles=3, vlen=512, caps=(False, True))
    # roots flaring out along the ground
    for k in range(6):
        a = k * 2 * math.pi / 6 + rng.uniform(-0.3, 0.3)
        L0 = trunk_r * rng.uniform(1.8, 2.8)
        pts = [(math.cos(a) * trunk_r * 0.6, math.sin(a) * trunk_r * 0.6, trunk_r * 0.9)]
        for t in np.linspace(0.25, 1, 5):
            rr = trunk_r * 0.6 + L0 * t
            pts.append((math.cos(a + 0.2 * t * rng.uniform(-1, 1)) * rr, math.sin(a + 0.2 * t) * rr, max(trunk_r * 0.35 * (1 - t) ** 1.4, 0) + trunk_r * 0.22 * (1 - t) * 0 + 2 + (1 - t) * trunk_r * 0.2))
        radii = np.linspace(trunk_r * 0.42, trunk_r * 0.07, len(pts))
        P = np.array(pts, float)
        P[:, 2] = np.maximum(P[:, 2], radii * 0.75 + 0.0)             # the root's underside rests on z >= 0
        tube(X.mesh(bark), P, radii, nseg=6, utiles=1, vlen=256, ry=radii * 0.75)
    # branches from the upper trunk
    BR = []
    for k in range(branches):
        t = t0 + (1 - t0) * k / max(1, branches - 1)
        i = int(t * (len(tp) - 1)); p0 = tp[i]
        a = k * 2.4 + rng.uniform(-0.3, 0.3)
        if avoid is not None:
            ad = (math.degrees(a) + 180) % 360 - 180
            if avoid[0] <= ad <= avoid[1]:
                a = math.radians(avoid[0] - 15 if ad - avoid[0] < avoid[1] - ad else avoid[1] + 15)
        d0 = np.array([math.cos(a), math.sin(a), rng.uniform(0.25, 0.9)])
        Lb = H * spread * rng.uniform(0.42, 0.62) * (1.1 - 0.4 * t)
        pts = gnarl_path(p0, d0, Lb, 7, rng, 0.28, -0.02)
        rad = np.linspace(tr[i] * 0.55, 4, len(pts))
        tube(X.mesh(bark), pts, rad, nseg=6, utiles=1, vlen=256)
        BR.append((pts, rad))
        for j in (3, 5):                                  # forks
            d1 = (pts[j + 1] - pts[j]); d1 /= np.linalg.norm(d1)
            side = np.cross(d1, [0, 0, 1.0]); side /= max(1e-6, np.linalg.norm(side))
            q = gnarl_path(pts[j], d1 + side * rng.choice([-1, 1]) * 0.9 + [0, 0, 0.3], Lb * 0.45, 5, rng, 0.35)
            tube(X.mesh(bark), q, np.linspace(rad[j] * 0.6, 2, len(q)), nseg=4, utiles=1, vlen=256)
            for m in (2, 4):                              # twigs
                d2 = q[m + 1] - q[m]; d2 /= np.linalg.norm(d2)
                tw = gnarl_path(q[m], d2 + rng.normal(0, 0.8, 3), Lb * 0.18, 3, rng, 0.5)
                tube(X.mesh(bark), tw, np.linspace(2.5, 0.8, len(tw)), nseg=3, caps=(False, False))
    # crown twigs at the top of the trunk
    for k in range(4):
        q = gnarl_path(tp[-1], [math.cos(k * 1.6), math.sin(k * 1.6), 1.2], H * 0.25, 5, rng, 0.4)
        tube(X.mesh(bark), q, np.linspace(tr[-1] * 0.5, 2, len(q)), nseg=4)
    for Mm in X.m.values():
        Mm.V = [np.array([v[0], v[1], max(v[2], 0.0)]) for v in Mm.V]
    rope = S('rope', 'vl'); lan_i = S('iron', 'vl', tag='lan'); lan_g = S('win_glow', 'flicker', ph=0.3)
    for (bi, t, drop) in lanterns:
        pts, rad = BR[bi % len(BR)]
        p = pts[int(t * (len(pts) - 1))]
        bottom = p - [0, 0, drop]
        tube(X.mesh(rope), [p - [0, 0, rad[int(t * (len(pts) - 1))] * 0.8], bottom + [0, 0, 26]], 1.5, nseg=4)
        lantern_into(X, bottom, lan_i, lan_g, 0.8)
    return save(name, X), BR, tp, tr


def lantern_into(X, base, iron, glow, s=1.0):
    b = np.asarray(base, float)
    rbox(X.mesh(iron), b + [-10 * s, -10 * s, 0], b + [10 * s, 10 * s, 3 * s], r=1, k=2)
    for (dx, dy) in ((-9, -9), (9, -9), (9, 9), (-9, 9)):
        tube(X.mesh(iron), [b + [dx * s, dy * s, 2 * s], b + [dx * s, dy * s, 24 * s]], 1.2 * s, nseg=4)
    M = X.mesh(glow)
    for k in range(4):
        a0 = k * math.pi / 2 + math.pi / 4; a1 = a0 + math.pi / 2
        p = [b + [8.5 * s * math.cos(a0) * 1.414 * 0.75, 8.5 * s * math.sin(a0) * 1.414 * 0.75, 3 * s],
             b + [8.5 * s * math.cos(a1) * 1.414 * 0.75, 8.5 * s * math.sin(a1) * 1.414 * 0.75, 3 * s]]
        p += [p[1] + [0, 0, 20 * s], p[0] + [0, 0, 20 * s]]
        am = (a0 + a1) / 2
        M.poly(p, (math.cos(am), math.sin(am), 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    _cap(X.mesh(iron), b + [0, 0, 23 * s], 13 * s, 12 * s)
    tube(X.mesh(iron), [b + [0, 0, 34 * s], b + [0, 0, 40 * s]], 2.5 * s, nseg=5)


def _cap(M, c, r, h):
    c = np.asarray(c, float)
    rows = [(r, 0), (r * 0.5, h * 0.6), (1, h)]
    m = Mesh(); lathe(m, rows, 8)
    M.add(m, np.eye(3), c)


# ================================================================================================= graveyard
def tombstone(name, kind, face_tex):
    X = Model()
    side = S('tomb_side', 'lm'); front = S(face_tex, 'lm')
    w, t, h = TOMB_DIM[kind]
    def slab(M_side, x0, x1, z0, z1, top_r=False, y0=-t / 2, y1=t / 2, face=True):
        rbox(X.mesh(side), (x0, y0, z0), (x1, y1, z1), r=2, k=2, tile=64, faces='nsewtb' if not face else 'nsewtb')
    if kind in ('tomb_arch', 'tomb_broken'):
        hh = h if kind == 'tomb_arch' else h
        body = h - w / 2 if kind == 'tomb_arch' else h
        rbox(X.mesh(side), (-w / 2 - 8, -t / 2 - 6, 0), (w / 2 + 8, t / 2 + 6, 12), r=2, k=2, tile=64)     # plinth
        # arch-topped slab as a prism with a round top (front/back faces get the face texture)
        poly = [(-w / 2, 12), (w / 2, 12), (w / 2, body)]
        for k in range(1, 12):
            a = math.pi * k / 12
            poly.append((w / 2 * math.cos(a), body + w / 2 * math.sin(a) * (1 if kind == 'tomb_arch' else 0)))
        poly.append((-w / 2, body))
        if kind == 'tomb_broken':
            poly = [(-w / 2, 12), (w / 2, 12), (w / 2, h * 0.8), (w * 0.2, h * 0.65), (-w * 0.1, h), (-w / 2, h * 0.9)]
        slab_prism(X, poly, -t / 2, t / 2, side, front, w, h)
    elif kind == 'tomb_slab':
        rbox(X.mesh(side), (-w / 2 - 6, -t / 2 - 6, 0), (w / 2 + 6, t / 2 + 6, 10), r=2, k=2, tile=64)
        poly = [(-w / 2, 10), (w / 2, 10), (w / 2, h - 14), (w / 2 - 14, h), (-w / 2 + 14, h), (-w / 2, h - 14)]
        slab_prism(X, poly, -t / 2, t / 2, side, front, w, h)
    elif kind in ('tomb_cross', 'tomb_celtic'):
        rbox(X.mesh(side), (-w / 2, -t, 0), (w / 2, t, 34), r=3, k=2, tile=64)                 # base block
        bw = 18 if kind == 'tomb_cross' else 20
        slab_prism(X, [(-bw / 2, 34), (bw / 2, 34), (bw / 2, h), (-bw / 2, h)], -t / 2, t / 2, side, side, w, h)
        ay = h - 46
        slab_prism(X, [(-w / 2 + 4, ay), (w / 2 - 4, ay), (w / 2 - 4, ay + bw), (-w / 2 + 4, ay + bw)], -t / 2, t / 2, side, side, w, h)
        if kind == 'tomb_celtic':
            ring = [(0 + 30 * math.cos(a), ay + bw / 2 + 30 * math.sin(a), 0) for a in np.linspace(0, 2 * math.pi, 25)]
            tube(X.mesh(side), [(p[0], 0, p[1]) for p in ring], 4.5, nseg=6, caps=(False, False))
        # plaque on the base
        X.mesh(front).poly([np.array(p) for p in ((-w / 2 + 6, -t - 0.5, 6), (w / 2 - 6, -t - 0.5, 6), (w / 2 - 6, -t - 0.5, 30), (-w / 2 + 6, -t - 0.5, 30))],
                           (0, -1, 0), [(0.1, 1.0), (0.9, 1.0), (0.9, 0.55), (0.1, 0.55)])
    elif kind == 'tomb_obelisk':
        rbox(X.mesh(side), (-w / 2 - 10, -w / 2 - 10, 0), (w / 2 + 10, w / 2 + 10, 20), r=2, k=2, tile=64)
        rbox(X.mesh(side), (-w / 2, -w / 2, 20), (w / 2, w / 2, 60), r=2, k=2, tile=64)
        top = h - 20
        q = w * 0.32
        pts = [(-w / 2 + 6, -w / 2 + 6, 60), (w / 2 - 6, -w / 2 + 6, 60), (w / 2 - 6, w / 2 - 6, 60), (-w / 2 + 6, w / 2 - 6, 60)]
        tp = [(-q, -q, top), (q, -q, top), (q, q, top), (-q, q, top)]
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]; c2, d2 = tp[(k + 1) % 4], tp[k]
            sh = front if k == 0 else side
            quad_uv(X.mesh(sh), a, b, c2, d2, [(0, 1), (1, 1), (1, 0), (0, 0)])
        for k in range(4):
            tri_up(X.mesh(side), tp[k], tp[(k + 1) % 4], (0, 0, h))
    return save(name, X)


def slab_prism(X, poly, y0, y1, side, front, w, h):
    """vertical slab: polygon (x, z) extruded along y from y0 (front, faces -y) to y1 (back); front/back get the face
    texture fitted to the w x h box, the edges the side texture"""
    from meshlib import triangulate
    P = [np.asarray(p, float) for p in poly]
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    if area < 0: P = P[::-1]
    tris = triangulate(P)
    for (yy, nrm, sh, flip) in ((y0, (0, -1, 0), front, False), (y1, (0, 1, 0), side, True)):
        M = X.mesh(sh)
        for (i, j, k) in tris:
            o = len(M.V)
            for idx in (i, j, k):
                x, z = P[idx]
                u = (x + w / 2) / w if not flip else (w / 2 - x) / w
                M.add_v((x, yy, z), nrm, (u, 1 - z / h))
            M.tri(o, o + 1, o + 2)
    Ms = X.mesh(side)
    for k in range(n):
        a, b = P[k], P[(k + 1) % n]
        e = b - a; ln = np.linalg.norm(e)
        nrm = np.array([e[1], 0, -e[0]]) / max(1e-9, ln)
        Ms.poly([np.array([a[0], y0, a[1]]), np.array([b[0], y0, b[1]]), np.array([b[0], y1, b[1]]), np.array([a[0], y1, a[1]])],
                nrm, [(0, 0), (ln / 64, 0), (ln / 64, (y1 - y0) / 64), (0, (y1 - y0) / 64)])


def iron_fence(name, pts, h=112, post_every=96, gaps=()):
    """wrought-iron fence along a polyline (world coords): rails, spear-tipped bars, square posts with ball caps;
    gaps: [(start, end)] distances along the line left open. Returns (path, scale, zoff, origin)"""
    X = Model()
    iron = S('iron', 'lms', v=0.12, tag='f')
    P = np.array([(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in pts], float)
    o = P[0].copy()
    P = P - o
    seg_len = [np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)]
    s0 = 0.0
    def in_gap(s): return any(a - 1 <= s <= b + 1 for (a, b) in gaps)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; Ln = seg_len[i]; d = (b - a) / Ln
        # rails in the open spans
        cuts = [0.0]
        for (ga, gb) in gaps:
            if s0 < gb and s0 + Ln > ga: cuts += [max(0, ga - s0), min(Ln, gb - s0)]
        cuts.append(Ln)
        cuts = sorted(cuts)
        for (ca, cb) in zip(cuts[0::2], cuts[1::2]):
            if cb - ca < 4 or in_gap(s0 + (ca + cb) / 2): continue
            for z in (14, h - 22):
                tube(X.mesh(iron), [a + d * ca + [0, 0, z], a + d * cb + [0, 0, z]], 2.2, nseg=5)
            nb = max(1, int((cb - ca) / 12))
            for k in range(nb + 1):
                p = a + d * (ca + (cb - ca) * k / nb)
                tube(X.mesh(iron), [p + [0, 0, 2], p + [0, 0, h - 8]], 1.4, nseg=4, caps=(False, False))
                tri_up(X.mesh(iron), p + [-3 * d[0], -3 * d[1], h - 8], p + [3 * d[0], 3 * d[1], h - 8], p + [0, 0, h + 4])
                tri_up(X.mesh(iron), p + [3 * d[0], 3 * d[1], h - 8], p + [-3 * d[0], -3 * d[1], h - 8], p + [0, 0, h + 4])
        npost = max(1, int(round(Ln / post_every)))
        for k in range(npost + (1 if i == len(P) - 2 else 0)):
            s = Ln * k / npost
            if in_gap(s0 + s) and not any(abs(s0 + s - g) < 2 for gp in gaps for g in gp): continue
            p = a + d * s
            rbox(X.mesh(iron), p + [-5, -5, 0], p + [5, 5, h + 6], r=1.5, k=2, tile=64)
            sphere(X.mesh(iron), p + [0, 0, h + 12], 6, 8, 5)
        s0 += Ln
    path = f'{MD}/{name}.md3'
    from meshlib import save_md3
    sc, zo = save_md3(out(path), X.surfaces(), name, with_offset=True)
    return path, sc, zo, tuple(o)


def gate_pillar():
    """stone gate pillar with a carved jack-o'-lantern on top (origin base centre, 64 x 64 x 240)"""
    X = Model()
    st = S('stone_m', 'lm', tag='gp'); cap = S('mossstone', 'lm', tag='gp')
    rbox(X.mesh(st), (-36, -36, 0), (36, 36, 24), r=3, tile=96)
    rbox(X.mesh(st), (-30, -30, 24), (30, 30, 210), r=2, tile=96)
    rbox(X.mesh(cap), (-38, -38, 210), (38, 38, 226), r=3, tile=96)
    rbox(X.mesh(cap), (-28, -28, 226), (28, 28, 236), r=2, tile=96)
    return save('gate_pillar', X)


def coffin(name, standing=False, open_=False):
    """hexagonal coffin, dark wood, brass handles. lying: origin base centre, long axis x. standing: upright against a
    wall behind it (+y), lid open to the side; open_ shows the glowing purple inside"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='cof'); br = S('brass', 'lms', v=0.25, tag='cof'); inner = S('velvet', 'lm', tag='cof')
    Lc, W0, W1, Hc = 200, 44, 64, 52
    poly = [(-Lc / 2, -W0 / 2), (Lc * 0.22, -W1 / 2), (Lc / 2, -W0 * 0.42), (Lc / 2, W0 * 0.42), (Lc * 0.22, W1 / 2), (-Lc / 2, W0 / 2)]
    m = Mesh()
    if open_:
        prism(m, poly, 0, 6, tile=64)                              # back board
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            e = np.array(b) - np.array(a); ln = np.linalg.norm(e); nn = np.array([e[1], -e[0]]) / ln
            q = Mesh(); prism(q, [a, b, (b[0] - nn[0] * 5, b[1] - nn[1] * 5), (a[0] - nn[0] * 5, a[1] - nn[1] * 5)], 6, Hc, tile=64)
            m.add(q)
        mi = Mesh()
        inset = [(x * 0.9, y * 0.82) for (x, y) in poly]
        from meshlib import triangulate
        for (i, j, k) in triangulate(inset):
            o = len(mi.V)
            for idx in (i, j, k): mi.add_v((inset[idx][0], inset[idx][1], 6.5), (0, 0, 1), (inset[idx][0] / 64, inset[idx][1] / 64))
            mi.tri(o, o + 1, o + 2)
    else:
        prism(m, poly, 0, Hc, tile=64)
        mi = None
        hp = Mesh(); prism(hp, [(x * 1.04, y * 1.04) for (x, y) in poly], Hc, Hc + 8, tile=64); m.add(hp)
    if standing:
        # long axis x -> z (head up), the lid side (+z) -> -y (faces the room), the back board against +y
        t = np.array([0, Hc + 1, Lc / 2])
        X.mesh(wd).add(m, _Rstand(), t)
        if mi is not None: X.mesh(S('velvet', 'glow', tag='cof') if open_ else inner).add(mi, _Rstand(), t)
    else:
        X.mesh(wd).add(m)
        if mi is not None: X.mesh(inner).add(mi)
        for sx in (-1, 1):
            for x in (-50, 10, 60):
                tube(X.mesh(br), [(x - 10, sx * (W1 / 2 * 0.95 if -20 < x < 40 else W0 / 2 + 2), 26), (x + 10, sx * (W1 / 2 * 0.95 if -20 < x < 40 else W0 / 2 + 2), 26)], 2, nseg=5)
        # cross on the lid
        if not open_:
            rbox(X.mesh(br), (-60, -4, Hc + 8), (20, 4, Hc + 10), r=0.5, k=1)
            rbox(X.mesh(br), (-36, -16, Hc + 8), (-28, 16, Hc + 10), r=0.5, k=1)
    return save(name, X)


def _Rstand():
    """maps the lying coffin frame (long axis x, lid +z) to standing: x -> z, y -> x, z -> -y (columns = images of the axes)"""
    return np.array([[0, 1, 0], [0, 0, -1], [1, 0, 0]], float)


def sarcophagus(name, open_=False):
    """stone sarcophagus (origin base centre, long axis x, 240 x 104 x 96) with a carved lid"""
    X = Model()
    st = S('stone_m', 'lm', tag='sar'); mo = S('mossstone', 'lm', tag='sar')
    rbox(X.mesh(st), (-124, -56, 0), (124, 56, 14), r=2, tile=96)
    rbox(X.mesh(st), (-116, -48, 14), (116, 48, 80), r=3, tile=96)
    for x in np.linspace(-96, 96, 5):                   # carved panels
        rbox(X.mesh(mo), (x - 14, -50, 26), (x + 14, -48, 68), r=1, k=1, tile=64)
        rbox(X.mesh(mo), (x - 14, 48, 26), (x + 14, 50, 68), r=1, k=1, tile=64)
    if open_:
        rbox(X.mesh(mo), (-30, -60, 80), (130, 50, 96), r=3, tile=96)    # lid pushed aside
    else:
        rbox(X.mesh(mo), (-122, -54, 80), (122, 54, 92), r=3, tile=96)
        rbox(X.mesh(mo), (-100, -36, 92), (100, 36, 100), r=6, tile=96)
    return save(name, X)


def candles(name, n=5, seed=1, h=(30, 70), spread=26):
    """cluster of wax candles with dripping wax and flame sprites (origin base centre)"""
    X = Model()
    wax = S('wax', 'vl'); fl = S('flame', 'add', deform='autosprite2', wave='noise 0.85 0.2 0 7')
    r = np.random.default_rng(seed)
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0, spread) if k else 0
        x, y = d * math.cos(a), d * math.sin(a)
        hh = r.uniform(*h); rr = r.uniform(4, 7)
        lathe(X.mesh(wax), [(rr + 2.5, 0), (rr + 0.8, 3), (rr, hh * 0.3), (rr * 1.05, hh * 0.7), (rr, hh), (rr * 0.6, hh + 1)], 10, cx=x, cy=y,
              deform=lambda aa, r0, z, ph=r.uniform(0, 6): r0 * (1 + 0.08 * math.sin(aa * 3 + ph + z * 0.2)))
        X.mesh(fl).poly([np.array(p) for p in ((x - 4, y, hh + 1), (x + 4, y, hh + 1), (x + 4, y, hh + 15), (x - 4, y, hh + 15))],
                        (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return save(name, X)


def cobweb(name, s=80):
    """corner cobweb: a quarter disc in a corner (origin = the corner, web spans +x/+y... sits in the x-z plane)"""
    X = Model()
    sh = S('web', 'web')
    X.mesh(sh).poly([np.array(p) for p in ((0, 0, 0), (s, 0, 0), (s, 0, -s), (0, 0, -s))], (0, -1, 0), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return save(name, X)


def zombie_hand():
    """a rotting hand reaching out of a dirt mound (origin base centre)"""
    X = Model()
    sk = S('pumpkin_green', 'vl', tag='zh'); dirt = S('dirt_m', 'vl', tag='zh')
    ellipsoid(X.mesh(dirt), (0, 0, 0), 46, 34, 14, 12, 6, flat_bottom=0)
    tube(X.mesh(sk), [(0, 0, 6), (2, 1, 30), (4, 0, 44)], [7, 6, 5.5], nseg=8)
    ellipsoid(X.mesh(sk), (4, 0, 50), 7, 4, 9, 8, 6)
    for k, (dx, ln) in enumerate(((-6, 18), (-2, 22), (2, 22), (6, 18))):
        tube(X.mesh(sk), [(4 + dx, 0, 56), (4 + dx * 1.3, -2, 56 + ln * 0.6), (4 + dx * 1.4, -6, 56 + ln)], [2.2, 1.9, 1.5], nseg=5)
    tube(X.mesh(sk), [(-3, 0, 48), (-10, -2, 56), (-14, -6, 62)], [2.2, 2, 1.6], nseg=5)
    return save('zombie_hand', X)


def grave_mound(name, seed=1):
    X = Model()
    dirt = S('dirt_m', 'lm', tag='gm')
    ellipsoid(X.mesh(dirt), (0, 0, 0), 56, 104, 18, 14, 6, flat_bottom=0,
              bump=lambda p, t, ph=seed: 1 + 0.06 * math.sin(t * 5 + ph) * math.cos(p * 3))
    return save(name, X)


# ================================================================================================= props: hay, scarecrow, lamps, cauldron ...
def hay_bale():
    X = Model()
    hy = S('hay', 'lm', tag='hb'); tw = S('rope', 'lm', tag='hb')
    w, d, h = HAY
    rbox(X.mesh(hy), (-w / 2, -d / 2, 0), (w / 2, d / 2, h), r=8, tile=128,
         inflate=lambda x, y, z, n: 1.5 * math.sin(x * 0.3 + z * 0.2) * math.cos(y * 0.25))
    for x in (-w / 4, w / 4):
        pts = [(x, -d / 2 - 1.5, 0.5), (x, -d / 2 - 1.5, h + 1.5), (x, d / 2 + 1.5, h + 1.5), (x, d / 2 + 1.5, 0.5)]
        tube(X.mesh(tw), pts, 1.4, nseg=4, caps=(False, False))
    return save('hay_bale', X)


def scarecrow():
    """scarecrow on a pole: burlap head with a stitched grin, straw hat, plaid shirt, straw tufts (origin pole foot)"""
    X = Model()
    wd = S('wood', 'lm', tag='sc'); bur = S('burlap', 'lm', tag='sc'); pl = S('plaid', 'lm', tag='sc'); st = S('straw', 'lm', tag='sc')
    hat = S('felt_brown', 'lm', tag='sc'); eye = S('cloth_black', 'lm', tag='sc'); jeans = S('felt', 'lm', tag='sc')
    H = SCARE_H
    tube(X.mesh(wd), [(0, 0, 0), (0, 0, H - 40)], 6, nseg=8)
    tube(X.mesh(wd), [(-120, 0, H - 120), (120, 0, H - 120)], 5, nseg=8)
    # torso (shirt) + arms
    ellipsoid(X.mesh(pl), (0, 0, H - 150), 40, 26, 60, 14, 9)
    for sx in (-1, 1):
        tube(X.mesh(pl), [(sx * 20, 0, H - 120), (sx * 70, 0, H - 122), (sx * 108, 0, H - 126)], [17, 15, 13], nseg=10)
        for k in range(5):
            a = k * 1.2
            tube(X.mesh(st), [(sx * 106, 0, H - 126), (sx * (124 + 6 * math.cos(a)), 10 * math.sin(a), H - 136 + 8 * math.cos(a * 2))], 2, nseg=4)
    # trousers
    for sx in (-1, 1):
        tube(X.mesh(jeans), [(sx * 14, 0, H - 196), (sx * 18, 0, H - 250), (sx * 20, 2, H - 290)], [16, 14, 13], nseg=9)
        for k in range(4):
            tube(X.mesh(st), [(sx * 20, 0, H - 288), (sx * 20 + 8 * math.cos(k * 1.6), 8 * math.sin(k * 1.6), H - 306)], 2, nseg=4)
    # head
    ellipsoid(X.mesh(bur), (0, 0, H - 52), 30, 28, 34, 14, 9)
    tube(X.mesh(st), [(0, 0, H - 92), (0, 0, H - 84)], 18, nseg=10)
    for (dx) in (-11, 11):
        rbox(X.mesh(eye), (dx - 6, -29, H - 48), (dx + 6, -26, H - 38), r=1, k=1)
    for k in range(7):                                     # stitched grin
        x = -16 + k * 5.3
        tube(X.mesh(eye), [(x, -28.5, H - 66 + 3 * math.sin(k * 0.9) - 0.1 * x * x / 10), (x + 4, -28.5, H - 66)], 1.0, nseg=3)
    # straw hat
    lathe(X.mesh(hat), [(62, H - 30), (60, H - 26), (34, H - 24), (28, H - 6), (20, H), (0, H + 2)], 20, deform=lambda a, r, z: r + (3 * math.sin(a * 5) if r > 50 else 0))
    lathe(X.mesh(hat), [(0, H - 32), (34, H - 31), (62, H - 31)], 20)
    return save('scarecrow', X)


def lamppost():
    """black iron gas lamp with a flickering glass lantern (origin base centre)"""
    X = Model()
    iron = S('iron', 'lms', v=0.15, tag='lp'); glow = S('win_glow', 'flicker', ph=0.6)
    H = LAMP_H
    lathe(X.mesh(iron), [(16, 0), (16, 8), (10, 14), (8, 40), (6, 60), (5, H - 50), (7, H - 44), (5, H - 40)], 10)
    for k in range(4):
        a = k * math.pi / 2
        tube(X.mesh(iron), [(5 * math.cos(a), 5 * math.sin(a), H - 80), (20 * math.cos(a), 20 * math.sin(a), H - 60), (14 * math.cos(a), 14 * math.sin(a), H - 42)], 1.6, nseg=4)
    lantern_into(X, (0, 0, H - 42), iron, glow, 1.6)
    return save('lamppost', X)


def cauldron_big():
    """the big witch's cauldron: iron pot (CAUL_PROFILE), rim lip, three stubby legs, stacked fire logs underneath with
    glowing embers and flames (origin = ground centre)"""
    X = Model()
    iron = S('iron', 'lms', v=0.14, tag='cb'); log = S('bark', 'lm', tag='cb'); ember = S('ember', 'glow', light=200, rgb='1 0.5 0.15')
    fl = S('flame', 'add', deform='autosprite2', wave='noise 0.9 0.2 0 6')
    rows = refine_rows(CAUL_PROFILE, 10)
    lathe(X.mesh(iron), rows, 48, u_tiles=6, vlen=256)
    # inner wall (visible above the brew) down to below the surface
    lathe(X.mesh(iron), [(L.CAUL_IN, L.CAUL_WATER - 40), (L.CAUL_IN, L.CAUL_RIM + 6)], 48, inward=True, u_tiles=6)
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.5
        p = np.array([200 * math.cos(a), 200 * math.sin(a), 0])
        tube(X.mesh(iron), [p + [0, 0, 0.5], p * 1.08 + [0, 0, 34]], [22, 16], nseg=8)
    # handles (rings) on two sides
    for a in (0, math.pi):
        c = np.array([292 * math.cos(a), 292 * math.sin(a), 262])
        ring = [c + np.array([math.cos(a) * 20 * math.cos(t), math.sin(a) * 20 * math.cos(t), 20 * math.sin(t) - 10]) for t in np.linspace(0, 2 * math.pi, 17)]
        tube(X.mesh(iron), ring, 4, nseg=6, caps=(False, False))
    # logs: two layers of crossed logs round the base
    r = np.random.default_rng(3)
    for k in range(10):
        a = k * 2 * math.pi / 10 + r.uniform(-0.1, 0.1)
        p0 = np.array([150 * math.cos(a), 150 * math.sin(a), 13]); p1 = np.array([330 * math.cos(a + 0.25), 330 * math.sin(a + 0.25), 13])
        tube(X.mesh(log), [p0, p1], 13, nseg=8)
    for k in range(14):
        a = k * 2 * math.pi / 14
        X.mesh(fl).poly([np.array(q) for q in ((300 * math.cos(a) - 10 * math.sin(a), 300 * math.sin(a) + 10 * math.cos(a), 10),
                                                (300 * math.cos(a) + 10 * math.sin(a), 300 * math.sin(a) - 10 * math.cos(a), 10),
                                                (300 * math.cos(a) + 10 * math.sin(a), 300 * math.sin(a) - 10 * math.cos(a), 70),
                                                (300 * math.cos(a) - 10 * math.sin(a), 300 * math.sin(a) + 10 * math.cos(a), 70))],
                        (math.cos(a), math.sin(a), 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    disc(X.mesh(ember), 300, 1.0, n=32, r_in=210)
    return save('cauldron_big', X)


def refine_rows(rows, step):
    out_ = [rows[0]]
    for (a, b) in zip(rows, rows[1:]):
        Ln = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(Ln / step))
        for k in range(1, n + 1): out_.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    return out_


def small_cauldron():
    X = Model()
    iron = S('iron', 'lms', v=0.14, tag='sc'); brew = S('bottle_g', 'glow')
    lathe(X.mesh(iron), [(30, 6), (46, 20), (54, 40), (50, 62), (44, 72), (48, 76), (40, 78)], 20)
    disc(X.mesh(brew), 40, 70, n=20)
    for k in range(3):
        a = k * 2.1
        tube(X.mesh(iron), [(34 * math.cos(a), 34 * math.sin(a), 0.5), (38 * math.cos(a), 38 * math.sin(a), 14)], 5, nseg=5)
    return save('small_cauldron', X)


def broom():
    """witch's broom leaning (origin = foot of the bristles; the broom leans against +y)"""
    X = Model()
    wd = S('wood', 'vl', tag='br'); st = S('straw', 'vl', tag='br'); tw = S('rope', 'vl', tag='br')
    lean = math.radians(16)
    d = np.array([0, math.sin(lean), math.cos(lean)])
    tube(X.mesh(wd), [d * 40, d * 200 + [4, 0, 0], d * 250], [4, 3.5, 3], nseg=6)
    for k in range(18):
        a = k * 2 * math.pi / 18
        tube(X.mesh(st), [d * 48 + [3 * math.cos(a), 3 * math.sin(a), 0], [16 * math.cos(a), 12 * math.sin(a) + 2, 1.0]], 1.6, nseg=3)
    tube(X.mesh(tw), [d * 42 + [6 * math.cos(a), 6 * math.sin(a), 0] for a in np.linspace(0, 2 * math.pi, 9)], 1.4, nseg=3, caps=(False, False))
    return save('broom', X)


def witch_hat():
    X = Model()
    f = S('felt', 'vl', tag='wh'); b = S('brass', 'vl', tag='wh')
    lathe(X.mesh(f), [(46, 0.5), (44, 3), (20, 4), (16, 30), (10, 52), (4, 66), (0.5, 70)], 20,
          deform=lambda a, r, z: r + (2.5 * math.sin(a * 4) if r > 36 else 0))
    disc(X.mesh(f), 44, 0.5, up=False, n=20)
    lathe(X.mesh(b), [(20.5, 6), (20, 12)], 16)
    return save('witch_hat', X)


def black_cat():
    """sitting black cat with glowing green eyes (origin base centre, faces -y)"""
    X = Model()
    fur = S('fur', 'vl'); eye = S('eye_g', 'glow')
    ellipsoid(X.mesh(fur), (0, 4, 18), 15, 18, 20, 12, 8)
    ellipsoid(X.mesh(fur), (0, -2, 44), 11, 10, 10, 12, 8)
    for sx in (-1, 1):
        tri_up(X.mesh(fur), (sx * 4, -4, 50), (sx * 10, -4, 49), (sx * 8, -3, 62))
        tri_up(X.mesh(fur), (sx * 10, -2, 49), (sx * 4, -2, 50), (sx * 8, -3, 62))
        ellipsoid(X.mesh(eye), (sx * 4.5, -10.5, 46), 2.4, 1.2, 1.8, 6, 4)
        tube(X.mesh(fur), [(sx * 7, -6, 4), (sx * 7, -8, 20)], 3.4, nseg=5)
    tube(X.mesh(fur), [(0, 20, 6), (10, 30, 4), (22, 26, 8), (26, 14, 22), (22, 8, 30)], [5, 4.5, 4, 3.5, 3], nseg=6)
    return save('black_cat', X)


def potion_shelf():
    """wall shelf with potion bottles (origin = base centre at the wall, shelf runs along x, wall at +y)"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='ps')
    bot = [S('bottle_g', 'glow'), S('bottle_p', 'glow'), S('bottle_o', 'glow')]
    for (x0, x1) in ((-90, -86), (86, 90)):
        rbox(X.mesh(wd), (x0, -36, 0), (x1, 0, 200), r=1, k=1)
    r = np.random.default_rng(5)
    for z in (60, 120, 180):
        rbox(X.mesh(wd), (-92, -36, z - 4), (92, 0, z), r=1, k=1)
        x = -78
        while x < 74:
            b = bot[r.integers(3)]; h = r.uniform(14, 30); rr = r.uniform(5, 9)
            lathe(X.mesh(b), [(rr * 0.7, z), (rr, z + 2), (rr, z + h * 0.6), (rr * 0.4, z + h * 0.8), (rr * 0.35, z + h), (0.5, z + h + 0.5)], 10, cx=x, cy=-18)
            x += rr * 2 + r.uniform(2, 8)
    return save('potion_shelf', X)


def table_chair():
    """rough wooden table with candles + 2 stools (origin centre)"""
    X = Model()
    wd = S('wood', 'lm', tag='tc')
    rbox(X.mesh(wd), (-80, -44, 52), (80, 44, 60), r=2, k=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rbox(X.mesh(wd), (sx * 70 - 5, sy * 34 - 5, 0), (sx * 70 + 5, sy * 34 + 5, 52), r=1, k=1)
    for sx in (-1, 1):
        lathe(X.mesh(wd), [(16, 34), (16, 38), (0, 38)], 12, cx=sx * 120, cy=0)
        for k in range(3):
            a = k * 2.1
            tube(X.mesh(wd), [(sx * 120 + 10 * math.cos(a), 10 * math.sin(a), 34), (sx * 120 + 14 * math.cos(a), 14 * math.sin(a), 0.5)], 2.4, nseg=4)
    return save('table_chair', X)


def lectern_book():
    X = Model()
    wd = S('wood_dark', 'lm', tag='lb'); pg = S('trim', 'lm', tag='lb'); cov = S('velvet', 'lm', tag='lb')
    lathe(X.mesh(wd), [(24, 0), (24, 4), (8, 8), (6, 70), (10, 74)], 10)
    tilt = math.radians(20)
    R = rot_axis((1, 0, 0), tilt)
    m = Mesh(); rbox(m, (-30, -22, 0), (30, 22, 4), r=1, k=1)
    X.mesh(wd).add(m, R, (0, 0, 74))
    m2 = Mesh(); rbox(m2, (-26, -18, 4), (26, 18, 8), r=1.5, k=1)
    X.mesh(pg).add(m2, R, (0, 0, 74))
    m3 = Mesh(); rbox(m3, (-27, -19, 3.5), (27, 19, 4.5), r=0.5, k=1)
    X.mesh(cov).add(m3, R, (0, 0, 74))
    return save('lectern_book', X)


def bed():
    """rickety bed with a patchwork quilt (origin centre, long axis y)"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='bd'); q = S('plaid', 'lm', tag='bd'); pil = S('trim', 'lm', tag='bd')
    rbox(X.mesh(wd), (-56, -100, 16), (56, 100, 30), r=2, k=2)
    for sx in (-1, 1):
        for (sy, h) in ((-1, 60), (1, 100)):
            rbox(X.mesh(wd), (sx * 56 - 6, sy * 100 - 6, 0), (sx * 56 + 6, sy * 100 + 6, h), r=2, k=2)
    rbox(X.mesh(wd), (-56, 96, 50), (56, 102, 90), r=1, k=1)
    rbox(X.mesh(q), (-58, -96, 30), (58, 70, 44), r=6, tile=96, inflate=lambda x, y, z, n: 2 * math.sin(x * 0.1) * math.sin(y * 0.07))
    rbox(X.mesh(pil), (-40, 66, 30), (40, 96, 48), r=8, tile=64)
    return save('bed', X)


def bookshelf():
    """tall bookshelf (origin base centre, back against +y), 192 x 40 x 256"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='bs'); bk = S('books', 'lm', tag='bs')
    for (x0, x1) in ((-96, -88), (88, 96)):
        rbox(X.mesh(wd), (x0, -40, 0), (x1, 0, 256), r=1, k=1)
    rbox(X.mesh(wd), (-96, -4, 0), (96, 0, 256), r=0.5, k=1)
    for z in (0, 60, 120, 180, 240):
        rbox(X.mesh(wd), (-96, -40, z), (96, 0, z + 8 if z else 12), r=1, k=1)
        if z < 240:
            z0 = z + (8 if z else 12)
            quad_uv(X.mesh(bk), (-88, -30, z0), (88, -30, z0), (88, -30, z0 + 48), (-88, -30, z0 + 48),
                    [(0, 1), (1.4, 1), (1.4, 0.1), (0, 0.1)], n=(0, -1, 0))
            rbox(X.mesh(bk), (-88, -30, z0), (88, -4, z0 + 1), r=0.2, k=1, faces='t')
    return save('bookshelf', X)


def armchair():
    X = Model()
    v = S('velvet', 'lm', tag='ac'); wd = S('wood_dark', 'lm', tag='ac')
    rbox(X.mesh(v), (-44, -40, 20), (44, 40, 44), r=8, tile=64, inflate=lambda x, y, z, n: 2.0 * math.sin(x * 0.06))
    rbox(X.mesh(v), (-44, 28, 44), (44, 44, 130), r=10, tile=64)
    for sx in (-1, 1):
        rbox(X.mesh(v), (sx * 44 - (16 if sx > 0 else 0), -40, 44), (sx * 44 + (0 if sx > 0 else 16), 30, 76), r=7, tile=64)
        for sy in (-1, 1):
            tube(X.mesh(wd), [(sx * 36, sy * 32, 20), (sx * 38, sy * 34, 0.5)], 4, nseg=5)
    return save('armchair', X)


def dining_table():
    """dining table with a candelabra, a chair at each end (origin centre, long axis x, 220 x 112, height 60)"""
    X = Model()
    wd = S('wood_dark', 'lm', tag='dt'); br = S('brass', 'lms', v=0.25, tag='dt'); cl = S('red_cloth', 'lm', tag='dt')
    rbox(X.mesh(wd), (-110, -56, 54), (110, 56, 62), r=2, k=2)
    rbox(X.mesh(cl), (-80, -16, 62), (80, 16, 62.8), r=0.3, k=1, faces='t')
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(X.mesh(wd), [(6, 0), (8, 6), (5, 20), (7, 36), (5, 54)], 8, cx=sx * 96, cy=sy * 44)
    # candelabra
    lathe(X.mesh(br), [(14, 62), (12, 66), (3, 70), (3, 104), (5, 106)], 10)
    for sx in (-1, 1):
        tube(X.mesh(br), [(0, 0, 96), (sx * 18, 0, 100), (sx * 24, 0, 108)], 1.8, nseg=4)
    for x in (-24, 0, 24):
        zt = 108 if x else 106
        lathe(X.mesh(S('wax', 'vl', tag='dt')), [(3, zt), (3, zt + 22), (1, zt + 23)], 8, cx=x, cy=0)
    fl = S('flame', 'add', deform='autosprite2', wave='noise 0.85 0.2 0 7')
    for x in (-24, 0, 24):
        zt = (108 if x else 106) + 23
        X.mesh(fl).poly([np.array(p) for p in ((x - 4, 0, zt), (x + 4, 0, zt), (x + 4, 0, zt + 14), (x - 4, 0, zt + 14))], (0, -1, 0),
                        [(0, 1), (1, 1), (1, 0), (0, 0)])
    # a chair at each end of the table
    for sx in (-1, 1):
        x0 = sx * 140
        rbox(X.mesh(wd), (x0 - 18, -18, 34), (x0 + 18, 18, 40), r=1, k=1)
        rbox(X.mesh(wd), (x0 + sx * 14 - 3, -18, 40), (x0 + sx * 14 + 3, 18, 100), r=1, k=1)
        for (dx, dy) in ((-14, -14), (14, -14), (14, 14), (-14, 14)):
            tube(X.mesh(wd), [(x0 + dx, dy, 34), (x0 + dx, dy, 0.5)], 2, nseg=4)
    return save('dining_table', X)


def fireplace():
    """stone fireplace with mantel, fire logs and flames, a skull on the mantel (origin base centre, back to +y)
    256 wide, 64 deep, 200 tall"""
    X = Model()
    st = S('stone_m', 'lm', tag='fp'); wd = S('wood_dark', 'lm', tag='fp'); log = S('bark', 'lm', tag='fp')
    fl = S('flame', 'add', deform='autosprite2', wave='noise 0.9 0.2 0 6'); ember = S('ember', 'glow', light=200, rgb='1 0.5 0.15')
    soot = S('cloth_black', 'lm', tag='fp')
    rbox(X.mesh(st), (-128, -64, 0), (-72, 0, 150), r=2, tile=96)
    rbox(X.mesh(st), (72, -64, 0), (128, 0, 150), r=2, tile=96)
    rbox(X.mesh(st), (-128, -64, 112), (128, 0, 150), r=2, tile=96)
    rbox(X.mesh(wd), (-140, -76, 150), (140, 0, 162), r=2, tile=96)
    rbox(X.mesh(soot), (-72, -2, 0), (72, 0, 112), r=0.2, k=1, faces='s')
    rbox(X.mesh(st), (-140, -84, 0), (140, -60, 4), r=1, k=1)
    for k in range(3):
        a = -0.3 + k * 0.3
        tube(X.mesh(log), [(-40, -30 + k * 8, 8), (40, -24 + k * 6, 10 + k * 4)], 8, nseg=7)
    for x in (-28, 0, 26):
        X.mesh(fl).poly([np.array(p) for p in ((x - 14, -30, 8), (x + 14, -30, 8), (x + 14, -30, 70), (x - 14, -30, 70))], (0, -1, 0),
                        [(0, 1), (1, 1), (1, 0), (0, 0)])
    disc(X.mesh(ember), 46, 4.5, n=16, cx=0, cy=-30)
    return save('fireplace', X)


def piano():
    """haunted grand piano with the lid up (origin centre, keys face -y)"""
    X = Model()
    p = S('piano', 'lms', v=0.3, tag='pn'); k = S('keys', 'lm', tag='pn')
    poly = [(-80, -60), (80, -60), (80, 30), (40, 90), (-10, 110), (-60, 100), (-80, 60)]
    prism(X.mesh(p), poly, 40, 70, tile=64)
    for (x, y) in ((-70, -50), (70, -50), (-50, 90)):
        lathe(X.mesh(p), [(7, 0), (6, 20), (8, 40)], 8, cx=x, cy=y)
    rbox(X.mesh(p), (-78, -76, 54), (78, -60, 62), r=1, k=1)
    quad_uv(X.mesh(k), (-74, -76, 62.2), (74, -76, 62.2), (74, -62, 62.2), (-74, -62, 62.2), [(0, 1), (1, 1), (1, 0), (0, 0)], n=(0, 0, 1))
    m = Mesh(); prism(m, [(-78, -40), (78, -40), (78, 28), (38, 86), (-10, 106), (-60, 96), (-78, 58)], 0, 3, tile=64)
    X.mesh(p).add(m, rot_axis((0, 1, 0), math.radians(40)), (78, 0, 70))
    rbox(X.mesh(p), (-40, -50, 0), (40, -40, 4), r=1, k=1)
    return save('piano', X)


def chandelier():
    """iron chandelier with candles, hanging from the ceiling at z 0 (origin = ceiling point, model hangs below)"""
    X = Model()
    iron = S('iron', 'lms', v=0.15, tag='ch'); wax = S('wax', 'vl', tag='ch')
    fl = S('flame', 'add', deform='autosprite2', wave='noise 0.85 0.2 0 7')
    tube(X.mesh(iron), [(0, 0, 0), (0, 0, -70)], 2, nseg=5)
    ring = [(60 * math.cos(a), 60 * math.sin(a), -80) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(X.mesh(iron), ring, 2.5, nseg=5, caps=(False, False))
    for k in range(6):
        a = k * math.pi / 3
        tube(X.mesh(iron), [(0, 0, -70), (60 * math.cos(a), 60 * math.sin(a), -80)], 1.6, nseg=4)
        c = np.array([60 * math.cos(a), 60 * math.sin(a), -80])
        lathe(X.mesh(wax), [(3, -79), (3, -62), (1, -61)], 6, cx=c[0], cy=c[1])
        X.mesh(fl).poly([c + [-4, 0, 19], c + [4, 0, 19], c + [4, 0, 32], c + [-4, 0, 32]], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(iron), (-8, -8, -2), (8, 8, 0), r=0.5, k=1)
    return save('chandelier', X)


def hearse():
    """black horse-drawn hearse with glass sides and a coffin inside (origin base centre, long axis x) 320 x 120 x 220"""
    X = Model()
    lq = S('lacquer', 'lms', v=0.22, tag='hs'); gl = S('glass_dark', 'glass', c='0.08 0.08 0.1'); br = S('brass', 'lms', v=0.3, tag='hs')
    wh = S('wheel', 'lm', tag='hs'); cl = S('cloth_black', 'lm', tag='hs')
    rbox(X.mesh(lq), (-130, -56, 50), (130, 56, 70), r=3, tile=96)
    for x0, x1 in ((-130, -110), (110, 130)):
        rbox(X.mesh(lq), (x0, -56, 70), (x1, 56, 190), r=3, tile=96)
    for sy in (-1, 1):
        for x in (-60, 0, 60):
            rbox(X.mesh(lq), (x - 4, sy * 56 - 4, 70), (x + 4, sy * 56 + 4, 190), r=1, k=1)
        quad_uv(X.mesh(gl), (-110, sy * 54, 70), (110, sy * 54, 70), (110, sy * 54, 186), (-110, sy * 54, 186), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(lq), (-140, -64, 190), (140, 64, 204), r=4, tile=96)
    for x in (-120, -40, 40, 120):
        lathe(X.mesh(br), [(8, 204), (6, 214), (2, 224)], 8, cx=x, cy=0)
    for (x, r) in ((-90, 50), (90, 50)):
        for sy in (-1, 1):
            ring = [(x + r * math.cos(a), sy * 64, r + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
            tube(X.mesh(wh), ring, 4, nseg=6, caps=(False, False))
            for k in range(8):
                a = k * math.pi / 4
                tube(X.mesh(wh), [(x, sy * 64, r), (x + r * math.cos(a), sy * 64, r + r * math.sin(a))], 2, nseg=4)
    tube(X.mesh(lq), [(-90, -66, 50), (-90, 66, 50)], 3, nseg=5); tube(X.mesh(lq), [(90, -66, 50), (90, 66, 50)], 3, nseg=5)
    for sy in (-1, 1):                                   # shafts for the (absent) horse
        tube(X.mesh(wd_sh()), [(-130, sy * 40, 60), (-300, sy * 40, 50), (-310, sy * 40, 0.5)], 3, nseg=5)
    rbox(X.mesh(cl), (-100, -30, 70), (100, 30, 74), r=1, k=1)
    return save('hearse', X)


def wd_sh(): return S('wood_dark', 'lm', tag='g')


def well():
    """stone well with a little shingle roof, crank and bucket (origin centre) r 80, roof 260"""
    X = Model()
    st = S('stone_m', 'lm', tag='wl'); wd = S('wood', 'lm', tag='wl'); sh = S('shingle', 'lm', tag='wl'); dark = S('cloth_black', 'lm', tag='wl')
    lathe(X.mesh(st), [(80, 0), (82, 40), (84, 70), (86, 76), (64, 76), (64, 40)], 24, u_tiles=4, vlen=128,
          deform=lambda a, r, z: r + 2 * math.sin(a * 12) * (r > 70))
    disc(X.mesh(dark), 64, 40, n=24)
    for sx in (-1, 1):
        rbox(X.mesh(wd), (sx * 74 - 6, -6, 76), (sx * 74 + 6, 6, 220), r=1, k=1)
    tube(X.mesh(wd), [(-80, 0, 180), (80, 0, 180)], 4, nseg=6)
    tube(X.mesh(S('rope', 'lm', tag='wl')), [(0, 0, 180), (0, 0, 110)], 1.2, nseg=4)
    lathe(X.mesh(wd), [(10, 96), (12, 112), (11, 112)], 10)
    for sgn in (-1, 1):
        quad_uv(X.mesh(sh), (-100, 0, 262), (100, 0, 262), (100, sgn * 90, 200), (-100, sgn * 90, 200),
                [(0, 0), (1.6, 0), (1.6, 0.9), (0, 0.9)])
        quad_uv(X.mesh(sh), (100, 0, 260), (-100, 0, 260), (-100, sgn * 90, 198), (100, sgn * 90, 198),
                [(0, 0), (1.6, 0), (1.6, 0.9), (0, 0.9)])
    return save('well', X)


def market_stand():
    """pumpkin market stand: two-tier wooden shelves with pumpkins, striped awning (origin base centre, front -y)
    256 x 128 x 240"""
    X = Model()
    wd = S('wood_grey', 'lm', tag='ms'); aw = S('plaid', 'lm', tag='ms'); pk = S('pumpkin', 'lm', tag='ms')
    rbox(X.mesh(wd), (-128, -64, 60), (128, 64, 68), r=1, k=1)
    rbox(X.mesh(wd), (-128, 0, 110), (128, 64, 118), r=1, k=1)
    for x in (-124, 124):
        for y in (-60, 60):
            rbox(X.mesh(wd), (x - 4, y - 4, 0), (x + 4, y + 4, 200 if y > 0 else 170), r=1, k=1)
    quad_uv(X.mesh(aw), (-140, -90, 160), (140, -90, 160), (140, 70, 206), (-140, 70, 206), [(0, 1), (2, 1), (2, 0), (0, 0)])
    quad_uv(X.mesh(aw), (140, -90, 159), (-140, -90, 159), (-140, 70, 205), (140, 70, 205), [(0, 1), (2, 1), (2, 0), (0, 0)])
    r = np.random.default_rng(2)
    for (z, y, n) in ((68, -30, 5), (118, 32, 5)):
        for k in range(n):
            x = -100 + k * 50 + r.uniform(-6, 6); R = r.uniform(17, 23)
            lathe(X.mesh(pk), [(R * 0.5, z), (R, z + R * 0.5), (R * 0.95, z + R * 1.1), (R * 0.3, z + R * 1.45)], 12, cx=x, cy=y,
                  deform=lambda a, rr, zz: rr * (1 - 0.07 * (1 - abs(math.cos(6 * a)))), u_tiles=2)
    return save('market_stand', X)


def hay_wagon():
    """farm wagon loaded with hay and pumpkins (origin base centre, long axis x) 320 x 160"""
    X = Model()
    wd = S('wood', 'lm', tag='hw'); wh = S('wheel', 'lm', tag='hw'); hy = S('hay', 'lm', tag='hw2'); ir = S('iron', 'lm', tag='hw')
    rbox(X.mesh(wd), (-160, -80, 56), (160, 80, 68), r=2, tile=96)
    for sy in (-1, 1):
        rbox(X.mesh(wd), (-160, sy * 80 - (6 if sy > 0 else 0), 68), (160, sy * 80 + (0 if sy > 0 else 6), 110), r=1, tile=96)
    for sx in (-1, 1):
        rbox(X.mesh(wd), (sx * 160 - (6 if sx > 0 else 0), -80, 68), (sx * 160 + (0 if sx > 0 else 6), 80, 110), r=1, tile=96)
    rbox(X.mesh(hy), (-150, -72, 68), (150, 72, 140), r=24, tile=128, inflate=lambda x, y, z, n: 6 * math.sin(x * 0.04) * math.cos(y * 0.05) if n[2] > 0.5 else 0)
    for x in (-110, 110):
        for sy in (-1, 1):
            ring = [(x + 46 * math.cos(a), sy * 90, 46 + 46 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
            tube(X.mesh(wh), ring, 5, nseg=6, caps=(False, False))
            for k in range(10):
                a = k * math.pi / 5
                tube(X.mesh(wh), [(x, sy * 90, 46), (x + 46 * math.cos(a), sy * 90, 46 + 46 * math.sin(a))], 2.4, nseg=4)
        tube(X.mesh(ir), [(x, -92, 46), (x, 92, 46)], 4, nseg=5)
    tube(X.mesh(wd), [(-160, 0, 60), (-300, 0, 40), (-310, 0, 0.5)], 4, nseg=5)
    return save('hay_wagon', X)


def bonfire():
    """bonfire: teepee of logs in a ring of stones, flames and embers (origin centre) r ~110"""
    X = Model()
    log = S('bark', 'lm', tag='bf'); st = S('stone_m', 'lm', tag='bf'); ember = S('ember', 'glow', light=200, rgb='1 0.5 0.15')
    fl = S('flame', 'add', deform='autosprite2', wave='noise 0.9 0.25 0 5')
    r = np.random.default_rng(9)
    for k in range(12):
        a = k * 2 * math.pi / 12
        ellipsoid(X.mesh(st), (100 * math.cos(a), 100 * math.sin(a), 0), 20, 16, 14, 8, 5, R=rot_z(a), flat_bottom=0)
    for k in range(8):
        a = k * 2 * math.pi / 8 + r.uniform(-0.15, 0.15)
        tube(X.mesh(log), [(70 * math.cos(a), 70 * math.sin(a), 8), (6 * math.cos(a), 6 * math.sin(a), 120)], [9, 6], nseg=7)
    disc(X.mesh(ember), 72, 1.0, n=16)
    for k in range(5):
        a = k * 2 * math.pi / 5
        x, y = 30 * math.cos(a), 30 * math.sin(a)
        X.mesh(fl).poly([np.array(p) for p in ((x - 26, y, 4), (x + 26, y, 4), (x + 26, y, 150), (x - 26, y, 150))], (0, -1, 0),
                        [(0, 1), (1, 1), (1, 0), (0, 0)])
    return save('bonfire', X)


def log_bench():
    X = Model()
    log = S('bark', 'lm', tag='lg'); end = S('wood', 'lm', tag='lg')
    tube(X.mesh(log), [(-110, 0, 22), (110, 0, 22)], 22, nseg=12, caps=(False, False))
    for sx in (-1, 1):
        m = Mesh(); disc(m, 22, 0, n=12)
        X.mesh(end).add(m, rot_axis((0, 1, 0), sx * math.pi / 2), (sx * 110, 0, 22))
    return save('log_bench', X)


def corn_wall(name, length, h=None):
    """a curtain of corn along x from -length/2 to +length/2: alpha cards on both sides (+-CORN_T) and a ragged top,
    plus a few 3D stalks (origin = wall centre at ground)"""
    X = Model()
    sh = S('corn', 'alpha', vs=1.0)
    h = h or L.MAZE_H + 24
    hl = length / 2 + 6
    for (y, sgn) in ((-CORN_T, -1), (CORN_T, 1), (-CORN_T / 3, -1), (CORN_T / 3, 1)):
        nseg = max(1, int(length / 96))
        for k in range(nseg):
            x0 = -hl + 2 * hl * k / nseg; x1 = -hl + 2 * hl * (k + 1) / nseg
            yy0 = y + 3 * math.sin(x0 * 0.05 + y); yy1 = y + 3 * math.sin(x1 * 0.05 + y)
            u0 = (x0 + 1000 + y * 7) / 128; u1 = (x1 + 1000 + y * 7) / 128
            X.mesh(sh).poly([np.array(p) for p in ((x0, yy0, 0.5), (x1, yy1, 0.5), (x1, yy1, h), (x0, yy0, h))], (0, sgn, 0),
                            [(u0, 1), (u1, 1), (u1, 0), (u0, 0)])
    for (x, sgn) in ((-hl, -1), (hl, 1)):
        X.mesh(sh).poly([np.array(p) for p in ((x, -CORN_T - 2, 0.5), (x, CORN_T + 2, 0.5), (x, CORN_T + 2, h), (x, -CORN_T - 2, h))],
                        (sgn, 0, 0), [(0, 1), (0.25, 1), (0.25, 0), (0, 0)])
    return save(name, X)


def corn_clump(name, seed=1, r=60, n=7):
    X = Model()
    sh = S('corn', 'alpha', vs=1.0)
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = rng.uniform(0, math.pi); x, y = rng.uniform(-r, r, 2); w = rng.uniform(50, 80); h = rng.uniform(180, 240)
        c, s = math.cos(a) * w / 2, math.sin(a) * w / 2
        u0 = rng.uniform(0, 1)
        X.mesh(sh).poly([np.array(p) for p in ((x - c, y - s, 0.5), (x + c, y + s, 0.5), (x + c, y + s, h), (x - c, y - s, h))],
                        (-math.sin(a), math.cos(a), 0), [(u0, 1), (u0 + 0.3, 1), (u0 + 0.3, 0), (u0, 0)])
    return save(name, X)


CRATE = 96


def crate(name, full=False, seed=1):
    """wooden crate (CRATE cube, origin base centre); full: open top heaped with little pumpkins"""
    X = Model()
    wd = S('textures/padhalloween/planks_v', 'lm', tag='cr'); fr = S('wood_dark', 'lm', tag='cr'); pk = S('pumpkin', 'lm', tag='cr')
    h = CRATE / 2
    rbox(X.mesh(wd), (-h + 3, -h + 3, 0), (h - 3, h - 3, CRATE - (3 if full else 3)), r=1, k=1, tile=96, faces='nsewb' + ('' if full else 't'))
    for (x0, y0, x1, y1) in ((-h, -h, -h + 8, -h + 8), (h - 8, -h, h, -h + 8), (h - 8, h - 8, h, h), (-h, h - 8, -h + 8, h)):
        rbox(X.mesh(fr), (x0, y0, 0), (x1, y1, CRATE), r=1, k=1, tile=64)
    for z in (0, CRATE - 8):
        for (a, b) in (((-h, -h), (h, -h + 8)), ((-h, h - 8), (h, h)), ((-h, -h), (-h + 8, h)), ((h - 8, -h), (h, h))):
            rbox(X.mesh(fr), (a[0], a[1], z), (b[0], b[1], z + 8), r=1, k=1, tile=64)
    if full:
        X.mesh(wd).poly([np.array(p) for p in ((-h + 3, -h + 3, CRATE - 30), (h - 3, -h + 3, CRATE - 30), (h - 3, h - 3, CRATE - 30), (-h + 3, h - 3, CRATE - 30))],
                        (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
        r = np.random.default_rng(seed)
        for k in range(6):
            x, y = r.uniform(-h + 18, h - 18, 2); R = r.uniform(14, 19)
            lathe(X.mesh(pk), [(R * 0.5, CRATE - 30), (R, CRATE - 30 + R * 0.5), (R * 0.95, CRATE - 30 + R * 1.1), (R * 0.3, CRATE - 30 + R * 1.45)], 12,
                  cx=x, cy=y, deform=lambda a, rr, zz: rr * (1 - 0.07 * (1 - abs(math.cos(6 * a)))), u_tiles=2)
    return save(name, X)


def pitchfork():
    X = Model()
    wd = S('wood', 'vl', tag='pf'); ir = S('iron', 'vl', tag='pf')
    lean = math.radians(14)
    d = np.array([math.sin(lean), 0, math.cos(lean)])
    tube(X.mesh(wd), [d * 1, d * 200], 3, nseg=6)
    top = d * 200
    for k in (-1, 0, 1):
        tube(X.mesh(ir), [top + [0, k * 8, 0], top + [0, k * 8, 0] + d * 40], 1.2, nseg=4)
    tube(X.mesh(ir), [top + [0, -9, 0], top + [0, 9, 0]], 1.6, nseg=4)
    return save('pitchfork', X)


def crystal_ball():
    """crystal ball on a claw stand (for a func_rotating model2: origin at its centre of rotation = stand foot)"""
    X = Model()
    gl = S('crystal', 'glow', tag='cb'); ir = S('brass', 'dyn', tag='cb')
    lathe(X.mesh(ir), [(26, 0), (26, 4), (12, 10), (10, 30), (20, 40), (24, 46)], 12)
    sphere(X.mesh(gl), (0, 0, 76), 34, 18, 12)
    return save_iqm('crystal_ball', X)


def bats_iqm(name, n=7, R=520, seed=3, z_spread=90):
    """a colony of bats round a circle of radius R (func_rotating centre at the origin), wings flap via deformVertexes"""
    X = Model()
    body = S('fur', 'dyn', tag='bat'); wing = S('wing', 'batwing')
    r = np.random.default_rng(seed)
    for k in range(n):
        a = 2 * math.pi * k / n + r.uniform(-0.2, 0.2)
        rr = R + r.uniform(-60, 60); z = r.uniform(-z_spread, z_spread)
        c = np.array([rr * math.cos(a), rr * math.sin(a), z])
        fwd = np.array([-math.sin(a), math.cos(a), 0])           # counter-clockwise travel
        side = np.cross(fwd, [0, 0, 1])
        s = r.uniform(0.8, 1.2)
        m = Mesh(); ellipsoid(m, (0, 0, 0), 5 * s, 9 * s, 5 * s, 8, 6)
        R3 = np.stack([side, fwd, [0, 0, 1]], 1)
        X.mesh(body).add(m, R3, c)
        for sg in (-1, 1):
            p0 = c + side * sg * 3 * s; p1 = c + side * sg * 34 * s + fwd * 6 * s + [0, 0, 6 * s]; p2 = c + side * sg * 30 * s - fwd * 14 * s
            p3 = c - fwd * 8 * s
            X.mesh(wing).poly([p0, p1, p2, p3], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return save_iqm(name, X)


def ghost_iqm(name, R=640, n=2, seed=4):
    """sheet ghosts drifting round a circle of radius R (func_rotating centre at the origin)"""
    X = Model()
    sh = S('ghost', 'ghost')
    r = np.random.default_rng(seed)
    for k in range(n):
        a = 2 * math.pi * k / n
        c = np.array([R * math.cos(a), R * math.sin(a), 0])
        fwd = np.array([-math.sin(a), math.cos(a), 0])
        m = Mesh()
        rows = [(2, 120), (26, 114), (36, 96), (38, 70), (40, 40), (46, 10), (52, 0)]
        lathe(m, rows, 20, deform=lambda aa, rr, z: rr + (6 * math.sin(aa * 5 + k) if z < 20 else 0), uvf=lambda p: (0.5 + p[0] / 100, 0.9 - p[2] / 130))
        # turn so the face (texture centre, +x... uv x) looks along the travel direction
        R3 = np.stack([np.cross(fwd, [0, 0, 1]), fwd, [0, 0, 1]], 1) @ rot_z(-math.pi / 2)
        X.mesh(sh).add(m, R3, c)
        for sg in (-1, 1):                                       # arms
            m2 = Mesh(); tube(m2, [(0, 0, 70), (sg * 36, 6, 74), (sg * 54, 18, 70)], [10, 8, 5], nseg=6)
            X.mesh(sh).add(m2, np.stack([np.cross(fwd, [0, 0, 1]), fwd, [0, 0, 1]], 1), c)
    return save_iqm(name, X)


def weathervane():
    """iron weathervane: arrow with a bat cut-out on a spindle (func_rotating model2, origin = spindle foot)"""
    X = Model()
    ir = S('iron', 'dyn', tag='wv')
    tube(X.mesh(ir), [(0, 0, 0), (0, 0, 60)], 2, nseg=5)
    tube(X.mesh(ir), [(-60, 0, 50), (60, 0, 50)], 1.6, nseg=4)
    for sgn in (-1, 1):
        X.mesh(ir).poly([np.array((x, 0, z)) for (x, z) in ((60, 42), (80, 50), (60, 58))][::sgn], (0, -sgn, 0), [(0, 0), (1, 0.5), (0, 1)])
        X.mesh(ir).poly([np.array((x, 0, z)) for (x, z) in ((-60, 40), (-40, 50), (-60, 60), (-76, 60), (-64, 50), (-76, 40))][::sgn],
                        (0, -sgn, 0), [(0, 0), (1, 0.5), (0, 1), (0, 1), (0, 0.5), (0, 0)])
    # bat silhouette above the arrow
    bat = [(0, 70), (10, 78), (24, 74), (34, 84), (20, 88), (8, 82), (0, 90), (-8, 82), (-20, 88), (-34, 84), (-24, 74), (-10, 78)]
    for sgn in (-1, 1):
        from meshlib import triangulate
        P = bat if sgn > 0 else bat[::-1]
        for (i, j, k) in triangulate(P):
            o = len(X.mesh(ir).V)
            for idx in (i, j, k): X.mesh(ir).add_v((P[idx][0], 0, P[idx][1]), (0, -sgn, 0), (0, 0))
            X.mesh(ir).tri(o, o + 1, o + 2)
    return save_iqm('weathervane', X)


def tire_swing():
    """tyre on a rope for a func_pendulum (origin = the pivot at the branch; rope hangs down ROPE)"""
    X = Model()
    rope = S('rope', 'dyn', tag='ts'); tire = S('lacquer', 'dyn', tag='ts')
    Lr = TIRE_ROPE
    tube(X.mesh(rope), [(0, 0, 0), (0, 0, -Lr)], 1.8, nseg=5)
    for sg in (-1, 1):
        tube(X.mesh(rope), [(0, 0, -Lr), (sg * 26, 0, -Lr - 30)], 1.5, nseg=4)
    c = np.array([0, 0, -Lr - 36])
    ring = [c + [30 * math.cos(a), 0, 30 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 21)]
    tube(X.mesh(tire), ring, 10, nseg=10, ry=8, caps=(False, False))
    return save_iqm('tire_swing', X)


TIRE_ROPE = 220


def swing_lantern():
    """lantern on a chain for a func_pendulum (origin = pivot; hangs CHAIN below)"""
    X = Model()
    ir = S('iron', 'dyn', tag='sl'); gl = S('win_glow', 'glow', tag='sl')
    tube(X.mesh(ir), [(0, 0, 0), (0, 0, -60)], 1.4, nseg=4)
    lantern_into(X, (0, 0, -100), ir, gl, 1.4)
    return save_iqm('swing_lantern', X)


def gate_arch():
    """wrought-iron arch spanning the gate between the two pillars (origin = path centre at ground; span along x,
    springing at z 236 from x = +-GATE_W/2 - 32)"""
    X = Model()
    ir = S('iron', 'lms', v=0.12, tag='ga')
    hw = L.GATE_W / 2 + 32
    base = 236
    arc = [(hw * math.cos(a), 0, base + 110 * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
    tube(X.mesh(ir), arc, 3.5, nseg=6)
    arc2 = [(hw * 0.92 * math.cos(a), 0, base + 12 + 90 * math.sin(a)) for a in np.linspace(0.06, math.pi - 0.06, 25)]
    tube(X.mesh(ir), arc2, 2.4, nseg=5)
    for k in range(-5, 6):                                         # vertical scroll bars
        x = k * hw / 6
        zt = base + 110 * math.sqrt(max(0, 1 - (x / hw) ** 2))
        tube(X.mesh(ir), [(x, 0, base), (x, 0, zt)], 1.6, nseg=4)
    for sx in (-1, 1):                                             # curls
        c = np.array([sx * hw * 0.55, 0, base + 40])
        curl = [c + [sx * 14 * t * math.cos(6 * t), 0, 14 * t * math.sin(6 * t)] for t in np.linspace(0.2, 1.6, 20)]
        tube(X.mesh(ir), curl, 1.6, nseg=4, caps=(False, False))
    # chains for the sign
    for x in (-180, 180):
        zt = base + 110 * math.sqrt(max(0, 1 - (x / hw) ** 2))
        tube(X.mesh(ir), [(x, 0, zt), (x, 0, base - 10)], 1.4, nseg=4)
    return save('gate_arch', X)


# ================================================================================================= the treehouse (planks)
def treehouse():
    """planks, rope rails and posts for the treehouse round the hanging tree (collision = weapclip brushes in the
    builder): spiral stair, round deck, the east deck under the hut, its posts. Origin = tree foot (TREE, z 0)."""
    X = Model()
    pl = S('textures/padhalloween/planks', 'lm', tag='th'); dk = S('wood_dark', 'lm', tag='th'); rp = S('rope', 'lm', tag='th')
    r0, r1 = L.SPIRAL_R
    for (a0, a1, z) in L.spiral_steps():
        for k in range(3):                                         # three boards per step, radial
            aa0 = a0 + (a1 - a0) * k / 3 + 0.4; aa1 = a0 + (a1 - a0) * (k + 1) / 3 - 0.4
            q = []
            for (r, a) in ((r0 - 6, aa0), (r1, aa0), (r1, aa1), (r0 - 6, aa1)):
                q.append((r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
            m = Mesh(); prism(m, q, z - 6, z + 0.5, tile=64)
            X.mesh(pl).add(m)
        # bracket under the step into the trunk
        am = math.radians((a0 + a1) / 2)
        tube(X.mesh(dk), [((r0 - 4) * math.cos(am), (r0 - 4) * math.sin(am), z - 70), (r1 * 0.85 * math.cos(am), r1 * 0.85 * math.sin(am), z - 7)], 4, nseg=5)
    # rope rail on the outer edge of the spiral: posts every second step
    posts = []
    for i, (a0, a1, z) in enumerate(L.spiral_steps()):
        if i % 2 == 0:
            am = math.radians(a0 + 2)
            p = np.array([(r1 - 8) * math.cos(am), (r1 - 8) * math.sin(am), z])
            tube(X.mesh(dk), [p, p + [0, 0, 52]], 3, nseg=5)
            posts.append(p + [0, 0, 48])
    tube(X.mesh(rp), posts, 1.6, nseg=4, caps=(False, False))
    # round deck boards (radial strips) except over the stair gap
    g0, g1 = L.deck_gap()
    Z = L.PLAT_Z
    n = 48
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        am = (a0 + a1) / 2
        if any(g0 <= am + off <= g1 for off in (0, 360)): continue
        q = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for (r, a) in ((r0 - 6, a0 + 0.3), (L.PLAT_R, a0 + 0.3), (L.PLAT_R, a1 - 0.3), (r0 - 6, a1 - 0.3))]
        m = Mesh(); prism(m, q, Z - 8, Z + 0.5, tile=64); X.mesh(pl).add(m)
        if k % 4 == 0:                                             # strut under the deck into the trunk
            amr = math.radians(am)
            tube(X.mesh(dk), [((r0 - 4) * math.cos(amr), (r0 - 4) * math.sin(amr), Z - 130), (L.PLAT_R * 0.8 * math.cos(amr), L.PLAT_R * 0.8 * math.sin(amr), Z - 10)], 5, nseg=5)
    # rail round the outer edge of the round deck (open over the stair gap and where it joins the east deck)
    pts = []
    def flush():
        if len(pts) > 1: tube(X.mesh(rp), pts, 1.8, nseg=4, caps=(False, False))
    for k in range(97):
        a = 360 * k / 96
        open_ = any(g0 - 6 <= a + off <= g1 + 6 for off in (0, 360)) or (-72 <= ((a + 180) % 360 - 180) <= 14)
        if open_:
            flush(); pts = []; continue
        p = np.array([(L.PLAT_R - 6) * math.cos(math.radians(a)), (L.PLAT_R - 6) * math.sin(math.radians(a)), Z + 44])
        if k % 4 == 0: tube(X.mesh(dk), [p - [0, 0, 44], p + [0, 0, 6]], 3, nseg=5)
        pts.append(p)
    flush()
    # east deck: boards along x, posts to the ground, rail on the south/east/north edges
    x0, y0, x1, y1 = L.TH_DECK
    for yy in np.arange(y0, y1, 32):
        q = [(x0 + 8 if abs(yy + 16) > 120 else r0 + 8, yy + 1), (x1, yy + 1), (x1, yy + 31), (x0 + 8 if abs(yy + 16) > 120 else r0 + 8, yy + 31)]
        q = [(max(px, math.sqrt(max(0, L.PLAT_R ** 2 - (py) ** 2)) - 4) if px < 300 else px, py) for (px, py) in q]
        m = Mesh(); prism(m, q, Z - 8, Z + 0.5, tile=64); X.mesh(pl).add(m)
    for (px, py) in TH_POSTS:
        tube(X.mesh(dk), [(px, py, 0.5), (px, py, Z - 8)], 11, nseg=8)
        tube(X.mesh(dk), [(px, py, Z - 150), (px - 70 if px > 300 else px + 70, py, Z - 10)], 4, nseg=5)
    for run in (((x0 + 200, y0 + 6), (x1 - 6, y0 + 6)), ((x1 - 6, y0 + 6), (x1 - 6, y1 - 6)), ((x1 - 6, y1 - 6), (x0 + 200, y1 - 6))):
        a = np.array([*run[0], Z]); b = np.array([*run[1], Z])
        tube(X.mesh(rp), [a + [0, 0, 44], b + [0, 0, 44]], 1.8, nseg=4)
        nn = max(1, int(np.linalg.norm(b - a) / 96))
        for k in range(nn + 1):
            p = a + (b - a) * k / nn
            tube(X.mesh(dk), [p, p + [0, 0, 50]], 3, nseg=5)
    return save('treehouse', X)


TH_POSTS = [(L.TH_DECK[2] - 24, L.TH_DECK[1] + 24), (L.TH_DECK[2] - 24, L.TH_DECK[3] - 24), (380, L.TH_DECK[1] + 24), (380, L.TH_DECK[3] - 24)]


# ================================================================================================= make
def make():
    os.makedirs(out(MD), exist_ok=True)
    make_textures()
    import hw_houses
    hw_houses.make_textures()
    # pumpkins
    great_pumpkin(); gp_lid()
    for (nm, R, st, kd, sd) in (('jack_s0', JACK['s'], 0, 'orange', 1), ('jack_s1', JACK['s'], 1, 'orange', 2), ('jack_m0', JACK['m'], 0, 'orange', 3),
                                ('jack_m1', JACK['m'], 1, 'red', 4), ('jack_l0', JACK['l'], 0, 'orange', 5), ('jack_l1', JACK['l'], 1, 'pale', 6),
                                ('jack_g', JACK['m'], 1, 'green', 7)):
        jack(nm, R, st, kd, True, sd)
    for (nm, R, kd, sd, sq, lk) in (('pump_a', 100, 'orange', 11, 1.0, 'lm'), ('pump_b', 140, 'orange', 12, 0.9, 'lm'), ('pump_c', 80, 'pale', 13, 1.0, 'vl'),
                                    ('pump_d', 60, 'green', 14, 1.1, 'vl'), ('pump_e', 120, 'red', 15, 0.85, 'lm'), ('pump_f', 46, 'orange', 16, 1.0, 'vl')):
        plain_pumpkin(nm, R, kd, sd, sq, lk)
    pumpkin_leaves('leaves_a', 3); pumpkin_leaves('leaves_b', 5, 12, 200)
    # trees
    global TREE_BIG
    TREE_BIG = dead_tree('tree_big', 1500, 7, 1.0, 120, lanterns=[(0, 0.55, 140), (2, 0.6, 120), (4, 0.5, 160), (5, 0.7, 110)], branches=8,
                         avoid=(-75, 25), t0=0.62)
    treehouse()
    dead_tree('tree_a', 760, 11, 0.9, 46, branches=6)
    dead_tree('tree_b', 620, 13, 1.1, 40, branches=5)
    dead_tree('tree_c', 880, 17, 0.8, 54, lanterns=[(1, 0.6, 90)], branches=6)
    # graveyard
    for i, k in enumerate(TOMB_KINDS):
        tombstone(k, k, f'tomb_{i % 4}')
    tombstone('tomb_arch_b', 'tomb_arch', 'tomb_2'); tombstone('tomb_slab_b', 'tomb_slab', 'tomb_1')
    gate_pillar(); coffin('coffin'); coffin('coffin_stand', standing=True); coffin('coffin_open', standing=True, open_=True)
    sarcophagus('sarcophagus'); sarcophagus('sarcophagus_open', True)
    candles('candles_a', 5, 1); candles('candles_b', 3, 2, (20, 46), 14); candles('candles_c', 7, 3, (40, 90), 34)
    cobweb('cobweb'); zombie_hand(); grave_mound('mound_a', 1); grave_mound('mound_b', 2)
    # farm + witch
    hay_bale(); scarecrow(); lamppost(); cauldron_big(); small_cauldron(); broom(); witch_hat(); black_cat(); potion_shelf()
    table_chair(); lectern_book(); bed(); bookshelf(); armchair(); dining_table(); fireplace(); piano(); chandelier()
    hearse(); well(); market_stand(); hay_wagon(); bonfire(); log_bench(); pitchfork(); gate_arch()
    crate('crate_a'); crate('crate_p', True, 3)
    for ln in (192, 384, 576, 768):
        corn_wall(f'corn_{ln}', ln)
    corn_clump('corn_clump_a', 1); corn_clump('corn_clump_b', 2, 80, 9)
    # movers (IQM)
    crystal_ball(); bats_iqm('bats_manor', 7, 360, 3, 60); bats_iqm('bats_lair', 5, 260, 5, 40); ghost_iqm('ghosts', 520, 2)
    weathervane(); tire_swing(); swing_lantern()
    hw_houses.make_models()
