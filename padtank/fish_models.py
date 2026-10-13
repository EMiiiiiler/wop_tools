"""Swimming fish for wop_padtank: procedural sharks / tangs + WoP's catalog angel fish, baked into static IQM models.

Each loop is one IQM: every fish is placed R units from the model origin, facing along its circle, so a
func_rotating with that model2 (origin brush at the circle centre) swims the whole school around the loop.
The tail fins are separate meshes with a `deformVertexes wave` shader (single-sided, normals pointing sideways),
so they wag in game. make_all(out) writes models/padtank/*.iqm + their textures and returns the shader text.

    LOOPS = list of dicts; build_padtank.py places one func_rotating per loop.
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import iqmtool, md3tool

MD = 'models/padtank'


# ------------------------------------------------------------------------------------------------ geometry helpers
def _orient(V, N, T, centre_fn):
    """flip triangles so cross(c-a, b-a) (Quake front side) points away from centre_fn(centroid)"""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(c - a, b - a)
    out = (a + b + c) / 3 - centre_fn((a + b + c) / 3)
    flip = (fn * out).sum(1) < 0
    T = T.copy(); T[flip] = T[flip][:, ::-1]
    return T


def _vnormals(V, T):
    N = np.zeros_like(V)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(c - a, b - a)
    for k in range(3): np.add.at(N, T[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)


def loft(L, hw, hh, zc, nseg=22, nring=14, u0=0.0, u1=1.0):
    """fish body along +x (tail at -L/2, nose at +L/2). hw/hh/zc: functions of t in [0,1] (0 = tail end, 1 = nose)
    giving half width, half height and centre height. Texture u = t (u0..u1), v = 0 on the back, 0.5 belly."""
    V, ST = [], []
    ts = np.linspace(0, 1, nseg + 1)
    for t in ts[:-1]:
        x = -L / 2 + L * t
        for j in range(nring + 1):
            ph = 2 * math.pi * j / nring
            V.append((x, hw(t) * math.sin(ph), zc(t) + hh(t) * math.cos(ph)))
            ST.append((u0 + (u1 - u0) * t, j / nring))
    tip = len(V); V.append((L / 2, 0, zc(1.0))); ST.append((u1, 0.25))
    T = []
    R = nring + 1
    for i in range(nseg - 1):
        for j in range(nring):
            a, b, c, d = i * R + j, i * R + j + 1, (i + 1) * R + j, (i + 1) * R + j + 1
            T += [(a, c, b), (b, c, d)]
    last = (nseg - 1) * R
    for j in range(nring): T.append((last + j, tip, last + j + 1))
    # tail-end cap (small)
    cap = len(V); V.append((-L / 2, 0, zc(0))); ST.append((u0, 0.25))
    for j in range(nring): T.append((j + 1, cap, j))
    V = np.array(V, np.float64); ST = np.array(ST, np.float64); T = np.array(T, np.int64)
    T = _orient(V, None, T, lambda p: np.stack([p[:, 0], np.zeros(len(p)), np.interp((p[:, 0] + L / 2) / L, ts, [zc(t) for t in ts])], 1))
    return V, _vnormals(V, T), ST, T


def flat(poly, uv, side=1.0):
    """planar fan polygon in the x-z plane (y = 0), single-sided, normal = +y*side (uv: per-vertex)"""
    V = np.array([(x, 0, z) for (x, z) in poly], np.float64)
    T = []
    for k in range(1, len(poly) - 1): T.append((0, k, k + 1))
    T = np.array(T, np.int64)
    fn = np.cross(V[T[:, 2]] - V[T[:, 0]], V[T[:, 1]] - V[T[:, 0]])
    if fn[0][1] * side < 0: T = T[:, ::-1]
    N = np.tile([0, side, 0], (len(V), 1)).astype(np.float64)
    return V, N, np.array(uv, np.float64), T


def flat_tris(tris_pts, uvs, side=1.0):
    """several triangles (each 3 (x,z) points) in the x-z plane, single-sided, normal +y*side"""
    V, ST, T = [], [], []
    for pts, uv in zip(tris_pts, uvs):
        o = len(V)
        for (x, z), q in zip(pts, uv): V.append((x, 0, z)); ST.append(q)
        T.append((o, o + 1, o + 2))
    V = np.array(V, np.float64); T = np.array(T, np.int64)
    fn = np.cross(V[T[:, 2]] - V[T[:, 0]], V[T[:, 1]] - V[T[:, 0]])
    flip = fn[:, 1] * side < 0
    T[flip] = T[flip][:, ::-1]
    return V, np.tile([0, side, 0], (len(V), 1)).astype(np.float64), np.array(ST, np.float64), T


def rot_x(V, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    M = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return V @ M.T


def merge(parts):
    V, N, ST, T = [], [], [], []
    o = 0
    for (v, n, st, t) in parts:
        V.append(v); N.append(n); ST.append(st); T.append(t + o); o += len(v)
    return np.concatenate(V), np.concatenate(N), np.concatenate(ST), np.concatenate(T)


# ------------------------------------------------------------------------------------------------ species
def shark(L=360.0):
    """leopard shark: returns {'body': (V,N,ST,T), 'tail': (...)}, nose along +x, centred on its body axis"""
    H, W = L * 0.12, L * 0.105
    prof = lambda t: max(0.10, math.sin(math.pi * min(1.0, t * 0.92) ** 0.75) ** 0.9) if t < 0.985 else 0.12
    hh = lambda t: H * prof(t) * (0.75 if t > 0.9 else 1.0)
    hw = lambda t: W * prof(t)
    zc = lambda t: -0.15 * H * prof(t)
    body = loft(L, hw, hh, zc, 26, 14, 0.0, 0.82)
    x = lambda t: -L / 2 + L * t
    top = lambda t: zc(t) + hh(t)
    # dorsal fins (vertical, sit on the back) and pectoral fins (angled down/out), body texture fin strip u 0.84..1
    fins = []
    d1 = [(x(0.47), top(0.47) - 4), (x(0.53), top(0.53) + L * 0.15), (x(0.62), top(0.62) - 4)]
    d2 = [(x(0.22), top(0.22) - 3), (x(0.25), top(0.25) + L * 0.06), (x(0.30), top(0.30) - 3)]
    an = [(x(0.24), zc(0.24) - hh(0.24) + 3), (x(0.27), zc(0.27) - hh(0.27) - L * 0.05), (x(0.33), zc(0.33) - hh(0.33) + 3)]
    fuv = [(0.86, 0.95), (0.93, 0.1), (0.99, 0.95)]
    fins.append(flat_tris([d1, d2, an], [fuv] * 3, 1))            # single-sided: the shader draws both sides
    # pectorals: triangles from the lower side out and back
    for sgn in (1, -1):
        t0, t1 = 0.60, 0.72
        p0 = (x(t1), sgn * hw(t1) * 0.85, zc(t1) - hh(t1) * 0.45)
        p1 = (x(t0), sgn * hw(t0) * 0.85, zc(t0) - hh(t0) * 0.45)
        p2 = (x(0.55), sgn * (hw(0.6) + L * 0.20), zc(0.6) - hh(0.6) - L * 0.08)
        V = np.array([p0, p1, p2], np.float64)
        T = np.array([[0, 1, 2]]); fn = np.cross(V[2] - V[0], V[1] - V[0])
        nz = np.cross(V[1] - V[0], V[2] - V[0]); nz = nz / np.linalg.norm(nz)
        if nz[2] < 0: nz = -nz                                         # lit from above
        if (fn @ nz) < 0: T = T[:, ::-1]
        fins.append((V, np.tile(nz, (3, 1)), np.array([(0.86, 0.9), (0.99, 0.9), (0.93, 0.15)]), T))
    # caudal fin (heterocercal: big upper lobe), single-sided, wagging
    r = x(0.0) + 6
    tail = [(r, zc(0) + hh(0.04) + 4), (r - L * 0.27, zc(0) + L * 0.24), (r - L * 0.12, zc(0) + 2),
            (r - L * 0.19, zc(0) - L * 0.12), (r, zc(0) - hh(0.04) - 2)]
    tuv = [(0.86, 0.5), (0.99, 0.05), (0.93, 0.5), (0.99, 0.95), (0.86, 0.6)]
    tv = flat_tris([[tail[0], tail[1], tail[2]], [tail[0], tail[2], tail[4]], [tail[4], tail[2], tail[3]]],
                   [[tuv[0], tuv[1], tuv[2]], [tuv[0], tuv[2], tuv[4]], [tuv[4], tuv[2], tuv[3]]], 1)
    return {'body': merge([body] + fins), 'tail': tv}


def tang(L=72.0):
    """blue tang: tall, flat oval body, yellow tail"""
    H, W = L * 0.36, L * 0.075
    prof = lambda t: max(0.16, math.sin(math.pi * min(1.0, 0.08 + t * 0.92)) ** 0.7)
    hh = lambda t: H * prof(t) * (0.8 if t > 0.85 else 1.0)
    hw = lambda t: W * max(0.35, prof(t))
    zc = lambda t: 0.0
    body = loft(L, hw, hh, zc, 14, 10, 0.0, 0.78)
    r = -L / 2 + 3
    tail = [(r, 5), (r - L * 0.30, L * 0.22), (r - L * 0.22, 0), (r - L * 0.30, -L * 0.22), (r, -5)]
    tuv = [(0.80, 0.45), (0.99, 0.05), (0.92, 0.5), (0.99, 0.95), (0.80, 0.55)]
    tv = flat_tris([[tail[0], tail[1], tail[2]], [tail[0], tail[2], tail[4]], [tail[4], tail[2], tail[3]]],
                   [[tuv[0], tuv[1], tuv[2]], [tuv[0], tuv[2], tuv[4]], [tuv[4], tuv[2], tuv[3]]], 1)
    return {'body': body, 'tail': tv}


_angel_cache = {}


def angel(md3root, name='flame_angel02', scale=1.0):
    """WoP catalog angel fish (faces -x, origin at its belly) -> nose +x, centred; keeps the catalog shaders"""
    p = os.path.join(md3root, 'models/mapobjects/pad_fish', name + '.md3')
    if p not in _angel_cache: _angel_cache[p] = md3tool.load(p)
    m = _angel_cache[p]
    out = []
    zmid = np.concatenate([s['verts'] for s in m['surfaces']])[:, 2]
    zmid = (zmid.min() + zmid.max()) / 2
    for s in m['surfaces']:
        V = s['verts'].astype(np.float64).copy(); V[:, 2] -= zmid
        V[:, 0] *= -1; V *= scale                                      # mirror x: nose to +x (mirror flips winding)
        N = s['normals'].astype(np.float64).copy(); N[:, 0] *= -1
        T = s['tris'][:, ::-1].copy()
        out.append((s['shader'], (V, N, s['st'].astype(np.float64), T)))
    return out


# ------------------------------------------------------------------------------------------------ placing fish on loops
def place(part, R, theta, dz, ccw, bank=8.0, pitch=0.0, scale=1.0):
    """move a fish part (nose +x, centred) onto the circle of radius R at angle theta (deg), height dz,
    facing along the direction of travel (ccw = counter-clockwise seen from above), banked into the turn"""
    V, N, ST, T = part
    V = V * scale
    head = math.radians(theta + (90 if ccw else -90))
    roll = bank if ccw else -bank          # lean toward the centre
    V = rot_x(V, roll); N = rot_x(N, roll)
    if pitch:
        a = math.radians(pitch); c, s = math.cos(a), math.sin(a)
        Mp = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]]); V = V @ Mp.T; N = N @ Mp.T
    c, s = math.cos(head), math.sin(head)
    Mz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    V = V @ Mz.T; N = N @ Mz.T
    th = math.radians(theta)
    V = V + np.array([R * math.cos(th), R * math.sin(th), dz])
    return V, N, ST, T


class LoopModel:
    def __init__(self, name):
        self.name = name; self.meshes = {}      # material -> list of parts
        self.extent = []                        # (R, dz, half size) per fish for sweep checks

    def add(self, material, part):
        self.meshes.setdefault(material, []).append(part)

    def save(self, out):
        meshes = []
        for mat, parts in self.meshes.items():
            cur = []; nv = 0
            for p in parts:
                if nv + len(p[0]) >= 990 and cur:
                    V, N, ST, T = merge(cur); meshes.append(dict(name=mat.split('/')[-1], material=mat, verts=V, normals=N, st=ST, tris=T))
                    cur = []; nv = 0
                cur.append(p); nv += len(p[0])
            if cur:
                V, N, ST, T = merge(cur); meshes.append(dict(name=mat.split('/')[-1], material=mat, verts=V, normals=N, st=ST, tris=T))
        path = os.path.join(out, MD, self.name + '.iqm')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        iqmtool.save(path, meshes)
        return MD + '/' + self.name + '.iqm'


def add_shark(M, R, theta, dz, ccw, L=360, kind='shark', bank=10, pitch=0):
    f = shark(L)
    M.add(f'{MD}/{kind}', place(f['body'], R, theta, dz, ccw, bank, pitch))
    M.add(f'{MD}/{kind}_tail', place(f['tail'], R, theta, dz, ccw, bank, pitch))
    M.extent.append((R, dz, L * 0.62))


def add_tang(M, R, theta, dz, ccw, L=72, bank=6):
    f = tang(L)
    M.add(f'{MD}/tang', place(f['body'], R, theta, dz, ccw, bank))
    M.add(f'{MD}/tang_tail', place(f['tail'], R, theta, dz, ccw, bank))
    M.extent.append((R, dz, L * 0.7))


def add_angel(M, md3root, R, theta, dz, ccw, name='flame_angel02', scale=1.0):
    for mat, part in angel(md3root, name, scale):
        M.add(mat, place(part, R, theta, dz, ccw, 4))
    M.extent.append((R, dz, 40 * scale))


# ------------------------------------------------------------------------------------------------ textures
def _noise(w, h, blur, seed):
    r = np.random.default_rng(seed)
    a = Image.fromarray((r.random((h, w)) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(a, np.float32); return (a - a.mean()) / (a.std() + 1e-6)


def shark_tex(seed, base, belly, spot, spots='saddle'):
    """512x256: u along the body (tail left .. nose at 0.82), v: back at the top/bottom rows, belly in the middle.
    The strip u > 0.84 is fin colour."""
    w, h = 512, 256
    v = np.linspace(0, 1, h)[:, None]
    bellyness = np.clip(1 - np.abs(v - 0.5) / 0.2, 0, 1) ** 1.5
    a = np.zeros((h, w, 3), np.float32)
    a += np.array(base, np.float32) * (1 - bellyness[..., None]) + np.array(belly, np.float32) * bellyness[..., None]
    a += _noise(w, h, 2, seed)[..., None] * 6
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    rr = random.Random(seed)
    if spots == 'saddle':                                            # leopard shark: dark saddles over the back + spots
        for k in range(9):
            u = int(40 + k * 42)
            for vv in (0, 256):
                d.ellipse((u - 10, vv - 34, u + 10, vv + 34), fill=spot)
        for _ in range(140):
            u, vv = rr.randint(10, 420), rr.choice([rr.randint(0, 80), rr.randint(176, 255)])
            r = rr.randint(3, 7); d.ellipse((u - r, vv - r, u + r, vv + r), fill=spot)
    else:                                                            # whale shark: white dots in rows + pale stripes
        for k in range(14):
            u = int(20 + k * 29)
            d.line([(u, 0), (u, 90)], fill=tuple(int(c * 0.8 + 50) for c in base), width=3)
            d.line([(u, 166), (u, 255)], fill=tuple(int(c * 0.8 + 50) for c in base), width=3)
        for _ in range(320):
            u, vv = rr.randint(5, 420), rr.choice([rr.randint(0, 92), rr.randint(164, 255)])
            r = rr.randint(2, 4); d.ellipse((u - r, vv - r, u + r, vv + r), fill=spot)
    # eyes and gill slits near the nose (sides: v .25 / .75)
    for vv in (64, 192):
        d.ellipse((392, vv - 7, 404, vv + 5), fill=(20, 20, 24)); d.ellipse((396, vv - 5, 399, vv - 2), fill=(230, 230, 230))
        for g in range(5): d.line([(330 + g * 7, vv - 16), (326 + g * 7, vv + 14)], fill=tuple(int(c * 0.6) for c in base), width=2)
    # fin strip
    fin = np.array(base, np.float32) * 0.9
    d.rectangle((430, 0, 511, 255), fill=tuple(int(c) for c in fin))
    for _ in range(30):
        u, vv = rr.randint(432, 508), rr.randint(0, 255); r = rr.randint(2, 5)
        d.ellipse((u - r, vv - r, u + r, vv + r), fill=spot)
    return im.filter(ImageFilter.GaussianBlur(0.7))


def tang_tex():
    w, h = 256, 128
    im = Image.new('RGB', (w, h), (32, 84, 214)); d = ImageDraw.Draw(im)
    a = np.asarray(im, np.float32) + _noise(w, h, 1.5, 7)[..., None] * 8
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    # black "palette" marking on each flank (v .25 and .75): from the eye back to the tail, with a loop
    for vv in (32, 96):
        d.polygon([(178, vv - 6), (120, vv - 22), (40, vv - 16), (60, vv - 4), (110, vv - 8), (150, vv + 6)], fill=(12, 14, 30))
        d.ellipse((70, vv - 2, 120, vv + 18), fill=(12, 14, 30)); d.ellipse((82, vv + 2, 108, vv + 12), fill=(36, 96, 220))
        d.ellipse((178, vv - 9, 188, vv + 1), fill=(10, 10, 10)); d.ellipse((181, vv - 7, 184, vv - 4), fill=(220, 220, 220))
    d.rectangle((0, 0, 8, 127), fill=(250, 214, 40))                 # yellow at the tail root
    d.rectangle((204, 0, 255, 127), fill=(250, 214, 40))             # tail fin strip
    d.line([(204, 0), (204, 127)], fill=(20, 30, 60), width=3)
    return im.filter(ImageFilter.GaussianBlur(0.6))


def shaders():
    S = ''
    for kind, amp, freq in (('shark', 7, 0.9), ('whaleshark', 10, 0.6), ('tang', 3, 2.2)):
        for tail in ('', '_tail'):
            deform = f'\tdeformVertexes wave 64 sin 0 {amp} 0 {freq}\n' if tail else ''
            S += (f'{MD}/{kind}{tail}\n{{\n\tqer_editorimage {MD}/{kind}\n\tcull disable\n{deform}'
                  f'\t{{\n\t\tmap {MD}/{kind}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n')
    return S


def make_textures(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    shark_tex(11, (168, 150, 118), (236, 228, 210), (70, 52, 36), 'saddle').save(os.path.join(d, 'shark.jpg'), quality=92)
    shark_tex(12, (70, 92, 116), (226, 230, 232), (236, 240, 244), 'dots').save(os.path.join(d, 'whaleshark.jpg'), quality=92)
    tang_tex().save(os.path.join(d, 'tang.jpg'), quality=92)


if __name__ == '__main__':
    M = LoopModel('test')
    add_shark(M, 1000, 0, 0, True); add_tang(M, 1000, 20, 0, True)
    make_textures('out'); print(M.save('out'))
