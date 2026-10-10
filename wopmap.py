#!/usr/bin/env python3
"""wopmap - small brush/entity library for generating Quake 3 / World of Padman .map files.

Brushes are convex hulls of integer points, so any shape you can describe by its corners works
(boxes, wedges, ramps, n-gon prisms, slide segments, leaning palm trunks...). Texture alignment is
q3map2's axial projection; `sign` faces get exact fit/mirroring for readable text.

    from wopmap import *
    M = Map()
    M.add(box((0,0,-16), (512,512,0), 'mymap/deck'))
    M.ent('info_player_deathmatch', (64,64,24), angle=90)
    M.model('pad_ducks/pad_duck.md3', (100,100,0), scale=0.5, angle=30)
    open('maps/test.map','w').write(M.text())
"""
import math
import numpy as np
from scipy.spatial import ConvexHull

DETAIL = 134217728
# shaders whose brushes are not "solid" for overlap checks (prefix match after textures/)
NONSOLID_HINTS = ('rainbow', 'foam', 'water', 'trigger', 'clip', 'origin', 'hint', 'skip', 'spray', 'waterfall', 'frond', 'fog',
                  'nodraw_ns', 'cable', 'glassns', 'sail', 'caustic', 'beam_ns')


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Face:
    __slots__ = ('pts', 'tex', 'sc', 'off', 'rot', 'n', 'd')

    def __init__(self, pts, tex, sc=(0.5, 0.5), off=(0, 0), rot=0):
        self.pts = pts; self.tex = tex; self.sc = sc; self.off = off; self.rot = rot
        n = _cross(_sub(pts[0], pts[1]), _sub(pts[2], pts[1]))
        l = math.sqrt(_dot(n, n))
        self.n = (n[0] / l, n[1] / l, n[2] / l)
        self.d = _dot(self.n, pts[0])


TEXSCALE = {}     # tex name -> (sx, sy) world units per texel; default 0.5


def default_scale(tex):
    return TEXSCALE.get(tex, (0.5, 0.5))


class Brush:
    def __init__(self, faces, detail=True):
        self.faces = faces; self.detail = detail

    # --------------------------------------------------------------- queries
    def planes(self):
        return [(f.n, f.d) for f in self.faces]

    def verts(self):
        P = self.planes(); out = []
        m = len(P)
        for i in range(m):
            for j in range(i + 1, m):
                for k in range(j + 1, m):
                    A = np.array([P[i][0], P[j][0], P[k][0]])
                    if abs(np.linalg.det(A)) < 1e-9: continue
                    p = np.linalg.solve(A, np.array([P[i][1], P[j][1], P[k][1]]))
                    if all(np.dot(n, p) - d <= 0.01 for n, d in P):
                        out.append(p)
        return np.array(out)

    def bounds(self):
        v = self.verts()
        return v.min(0), v.max(0)

    def textures(self):
        return {f.tex for f in self.faces}

    def is_solid(self):
        ts = self.textures()
        return not all(any(h in t for h in NONSOLID_HINTS) for t in ts)

    def text(self):
        s = '{\n'
        for f in self.faces:
            a, b, c = f.pts
            s += (f'( {fmt(a)} ) ( {fmt(b)} ) ( {fmt(c)} ) {f.tex} {f.off[0]:g} {f.off[1]:g} {f.rot:g} '
                  f'{f.sc[0]:g} {f.sc[1]:g} {DETAIL if self.detail else 0} 0 0\n')
        return s + '}\n'


def fmt(p):
    return ' '.join(str(int(round(v))) if abs(v - round(v)) < 1e-6 else f'{v:.3f}'.rstrip('0') for v in p)


# ------------------------------------------------------------------ texture helpers
def axial_axes(n):
    """q3map2 TextureAxisFromPlane -> (s axis, t axis, index)"""
    base = [((0, 0, 1), (1, 0, 0), (0, -1, 0)), ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
            ((1, 0, 0), (0, 1, 0), (0, 0, -1)), ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
            ((0, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, -1, 0), (1, 0, 0), (0, 0, -1))]
    best, bi = -1, 0
    for i, (nn, s, t) in enumerate(base):
        d = _dot(n, nn)
        if d > best + 1e-6: best, bi = d, i
    return base[bi][1], base[bi][2], bi


def fit_face(face, umin, umax, zmin, zmax, tw, th):
    """Make a texture of tw x th pixels exactly cover a vertical face: umin..umax along the face's
    axial s-axis (world x or y), zmin..zmax in height. Uses a negative s-scale when the text would
    otherwise read mirrored from outside (faces whose normal is +y or -x)."""
    s_ax, t_ax, bi = axial_axes(face.n)
    assert bi >= 2, 'fit_face is for walls'
    sx = (umax - umin) / tw; sy = (zmax - zmin) / th
    right = (-face.n[1], face.n[0], 0)       # viewer looks along -n with z up
    if _dot(right, s_ax) >= 0:
        face.sc = (sx, sy); offx = -umin / sx
    else:
        face.sc = (-sx, sy); offx = umax / sx
    face.off = (round(offx % tw, 3), round((zmax / sy) % th, 3))
    return face


def sign_box(mn, mx, sign_tex, tw, th, back='common/caulk', facing=None, edge=None, detail=True):
    """thin box whose face(s) pointing `facing` ('n','s','e','w' or 'ns'/'ew' for both) show sign_tex fitted."""
    b = box(mn, mx, edge or back, detail)
    for f in b.faces:
        for k in facing:
            v = {'e': (1, 0), 'w': (-1, 0), 'n': (0, 1), 's': (0, -1)}[k]
            if f.n[0] * v[0] + f.n[1] * v[1] > 0.99:
                f.tex = sign_tex
                if k in 'ns': fit_face(f, mn[0], mx[0], mn[2], mx[2], tw, th)
                else: fit_face(f, mn[1], mx[1], mn[2], mx[2], tw, th)
    return b


# ------------------------------------------------------------------ brush constructors
def hull(points, tex, detail=True, sides=None, round_pts=True):
    """Convex hull of points -> Brush. tex: name or dict with keys 'top','bot','side' or callable(normal)->name."""
    P = np.array(points, dtype=np.float64)
    if round_pts: P = np.round(P)
    P = np.unique(P, axis=0)
    h = ConvexHull(P)
    planes = []
    for eq in h.equations:
        n = eq[:3]; d = -eq[3]
        if any(np.allclose(n, q[0], atol=1e-7) and abs(d - q[1]) < 1e-5 for q in planes): continue
        planes.append((n, d))
    faces = []
    for n, d in planes:
        on = P[np.abs(P @ n - d) < 1e-4]
        # choose 3 well-spread points on the facet, ordered so cross(a-b, c-b) points outward
        c0 = on.mean(0)
        a = on[np.argmax(((on - c0) ** 2).sum(1))]
        b = on[np.argmax(((on - a) ** 2).sum(1))]
        ab = b - a
        c = on[np.argmax(np.abs(np.cross(on - a, ab) @ n))]
        pts = [tuple(a), tuple(b), tuple(c)]
        nn = _cross(_sub(pts[0], pts[1]), _sub(pts[2], pts[1]))
        if _dot(nn, n) < 0: pts = [pts[2], pts[1], pts[0]]
        t = _pick_tex(tex, n)
        faces.append(Face(pts, t, default_scale(t)))
    return Brush(faces, detail)


def _pick_tex(tex, n):
    if callable(tex): return tex(n)
    if isinstance(tex, dict):
        if n[2] > 0.7 and 'top' in tex: return tex['top']
        if n[2] < -0.7 and 'bot' in tex: return tex['bot']
        if abs(n[2]) <= 0.7:
            for k, v in (('e', (1, 0)), ('w', (-1, 0)), ('n', (0, 1)), ('s', (0, -1))):
                if k in tex and n[0] * v[0] + n[1] * v[1] > 0.7: return tex[k]
        return tex.get('side', tex.get('top'))
    return tex


def box(mn, mx, tex, detail=True):
    x0, y0, z0 = mn; x1, y1, z1 = mx
    assert x1 > x0 and y1 > y0 and z1 > z0, (mn, mx, tex)
    pts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return hull(pts, tex, detail)


def prism(poly, z0, z1, tex, detail=True):
    """extrude a convex 2D polygon (list of (x,y)) between z0 and z1"""
    return hull([(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly], tex, detail)


def ngon(cx, cy, r, n, phase=None):
    ph = math.pi / n if phase is None else math.radians(phase)
    return [(cx + r * math.cos(ph + 2 * math.pi * i / n), cy + r * math.sin(ph + 2 * math.pi * i / n)) for i in range(n)]


def cyl(cx, cy, r, z0, z1, tex, n=8, detail=True, phase=None):
    return prism(ngon(cx, cy, r, n, phase), z0, z1, tex, detail)


def ramp(x0, y0, x1, y1, z0, zlow, zhigh, rise, tex, detail=True):
    """solid wedge on footprint rect, bottom at z0, top sloping from zlow to zhigh toward `rise` ('n','s','e','w')"""
    def zt(x, y):
        if rise == 'n': return zlow + (zhigh - zlow) * (y - y0) / (y1 - y0)
        if rise == 's': return zlow + (zhigh - zlow) * (y1 - y) / (y1 - y0)
        if rise == 'e': return zlow + (zhigh - zlow) * (x - x0) / (x1 - x0)
        return zlow + (zhigh - zlow) * (x1 - x) / (x1 - x0)
    pts = []
    for x in (x0, x1):
        for y in (y0, y1):
            pts.append((x, y, z0))
            if zt(x, y) > z0: pts.append((x, y, zt(x, y)))
    return hull(pts, tex, detail)


def stairs(x0, y0, x1, y1, z0, ztop, run_dir, tex, step_h=16, base=None, detail=True, top_tex=None, thick=None):
    """straight flight on footprint rect rising toward run_dir ('n','s','e','w') from z0 to ztop.
    Each step is a solid block from `base` (default z0) up to its tread. Returns list of brushes."""
    nsteps = int(round((ztop - z0) / step_h))
    out = []
    L = (y1 - y0) if run_dir in 'ns' else (x1 - x0)
    d = L / nsteps
    b = z0 if base is None else base
    for i in range(nsteps):
        zt = z0 + step_h * (i + 1)
        if run_dir == 'n': r = (x0, y0 + d * i, x1, y0 + d * (i + 1))
        elif run_dir == 's': r = (x0, y1 - d * (i + 1), x1, y1 - d * i)
        elif run_dir == 'e': r = (x0 + d * i, y0, x0 + d * (i + 1), y1)
        else: r = (x1 - d * (i + 1), y0, x1 - d * i, y1)
        t = tex if top_tex is None else {'top': top_tex, 'side': tex}
        bb = b if thick is None else max(b, zt - thick)
        out.append(box((round(r[0]), round(r[1]), bb), (round(r[2]), round(r[3]), zt), t, detail))
    return out


def sub_rects(outer, holes):
    """axis-aligned rectangle minus rectangular holes -> list of rects (x0,y0,x1,y1)"""
    x0, y0, x1, y1 = outer
    ys = sorted({y0, y1} | {h[1] for h in holes if y0 < h[1] < y1} | {h[3] for h in holes if y0 < h[3] < y1})
    out = []
    for ya, yb in zip(ys, ys[1:]):
        iv = sorted((max(h[0], x0), min(h[2], x1)) for h in holes if h[1] < yb and h[3] > ya and h[0] < x1 and h[2] > x0)
        cur = x0
        for a, b in iv:
            if a > cur: out.append((cur, ya, a, yb))
            cur = max(cur, b)
        if cur < x1: out.append((cur, ya, x1, yb))
    # merge vertically adjacent identical spans
    merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            for j in range(len(out)):
                if i != j and out[i][0] == out[j][0] and out[i][2] == out[j][2] and out[i][3] == out[j][1]:
                    out[i] = (out[i][0], out[i][1], out[i][2], out[j][3]); out.pop(j); merged = True; break
            if merged: break
    return out


# ------------------------------------------------------------------ map
class Map:
    def __init__(self, worldspawn=None):
        self.world = []
        self.ents = []
        self.ws = worldspawn or {}
        self.models = []          # (path, origin, scale, angles)
        self.tags = {}            # brush id -> tag for audits

    def add(self, *bs, tag=None):
        for b in bs:
            if isinstance(b, (list, tuple)):
                self.add(*b, tag=tag); continue
            self.world.append(b)
            if tag: self.tags[id(b)] = tag
        return bs

    def ent(self, cls, origin=None, brushes=None, **kv):
        e = {'classname': cls}
        if origin is not None: e['origin'] = ' '.join(fmt([v]) for v in origin)
        for k, v in kv.items(): e[k] = str(v)
        e['_brushes'] = brushes or []
        self.ents.append(e)
        return e

    def model(self, path, origin, scale=1.0, angle=0, angles=None, **kv):
        p = path if path.startswith('models/') else 'models/mapobjects/' + path
        extra = dict(kv)
        if angles: extra['angles'] = ' '.join(f'{a:g}' for a in angles)
        else: extra['angle'] = f'{angle:g}'
        e = self.ent('misc_model', origin, model=p, modelscale=f'{scale:g}', **extra)
        self.models.append(e)
        return e

    def text(self, header=''):
        s = header + '// entity 0\n{\n"classname" "worldspawn"\n'
        for k, v in self.ws.items(): s += f'"{k}" "{v}"\n'
        for i, b in enumerate(self.world):
            s += f'// brush {i}\n' + b.text()
        s += '}\n'
        for i, e in enumerate(self.ents):
            s += f'// entity {i + 1}\n{{\n'
            for k, v in e.items():
                if k.startswith('_brushes'): continue
                s += f'"{k}" "{v}"\n'
            for j, b in enumerate(e['_brushes']):
                s += f'// brush {j}\n' + b.text()
            s += '}\n'
        return s
