"""Shared helpers for the Skull Rock Bay model/texture generators: MD3 shader registry, Model container, procedural
image helpers (tileable noise etc.). All art is original and generated here."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, save_md3, grid_normals
import iqmtool

NS = 'padpirate'
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


# ================================================================================================= brush solids -> MD3 surfaces
def face_polys(b):
    """[(normal, polygon points ordered CCW seen from outside)] of a wopmap Brush"""
    V = b.verts()
    out = []
    for f in b.faces:
        n = np.array(f.n, float)
        on = V[np.abs(V @ n - f.d) < 0.05]
        if len(on) < 3: continue
        on = np.unique(np.round(on, 4), axis=0)
        if len(on) < 3: continue
        c = on.mean(0)
        u = on[0] - c; u /= max(1e-9, np.linalg.norm(u)); v = np.cross(n, u)
        ang = np.arctan2((on - c) @ v, (on - c) @ u)
        out.append((n, on[np.argsort(ang)]))
    return out


def _inside_any(p, solids, eps=0.25):
    for (mn, mx, P) in solids:
        if np.any(p < mn - eps) or np.any(p > mx + eps): continue
        if all(np.dot(nn, p) - d <= eps for nn, d in P): return True
    return False


def solid_index(brushes):
    return [(b.bounds()[0], b.bounds()[1], [(np.array(nn, float), d) for nn, d in b.planes()]) for b in brushes]


def planar_uv(n, tile=256.0):
    """Quake-style axial projection (continuous across faces of the same orientation)"""
    a = int(np.argmax(np.abs(n)))
    if a == 2: s, t = np.array([1.0, 0, 0]), np.array([0, -1.0, 0])
    elif a == 0: s, t = np.array([0, 1.0, 0]), np.array([0, 0, -1.0])
    else: s, t = np.array([1.0, 0, 0]), np.array([0, 0, -1.0])
    if (a == 0 and n[0] < 0) or (a == 1 and n[1] > 0): s = -s          # never mirrored seen from outside
    return lambda p: (float(p @ s) / tile, float(p @ t) / tile)


def solids_mesh(X, brushes, texfn, hidden=None, drop=None):
    """add the visible faces of convex brushes to Model X. texfn(centre, normal, poly) -> (shader, uvfn) or None (skip).
    A face is hidden (dropped) when points just outside it lie inside any brush of `hidden` (default: the same set)
    or drop(centre, normal) says so."""
    idx = solid_index(hidden if hidden is not None else brushes)
    for b in brushes:
        for (n, poly) in face_polys(b):
            c = poly.mean(0)
            smp = [c] + [c + (p - c) * 0.7 for p in poly]
            if all(_inside_any(p + n * 1.0, idx) for p in smp): continue
            if drop is not None and drop(c, n): continue
            r = texfn(c, n, poly)
            if r is None: continue
            sh, uvf = r
            X.mesh(sh).poly([p for p in poly], n, [uvf(p) for p in poly])
    return X


# ================================================================================================= lathe + carved shells (from padhalloween/hw_models.py)
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


