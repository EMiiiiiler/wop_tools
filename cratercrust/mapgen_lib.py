"""Small brush/entity library for generating Quake 3 / World of Padman .map files.

Every brush is stored as a list of planes (3 integer points each) plus its vertex set,
so we can run overlap checks, support checks for models and jump pad simulations.
"""
import math, itertools, json

DETAIL = 134217728  # CONTENTS_DETAIL flag written on brush faces
EPS = 0.01


def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a):
    l = math.sqrt(dot(a, a)); return (a[0]/l, a[1]/l, a[2]/l)


class Plane:
    def __init__(self, a, b, c, tex, scale=0.5, rot=0, off=(0, 0)):
        self.p = [tuple(a), tuple(b), tuple(c)]
        self.tex, self.scale, self.rot, self.off = tex, scale, rot, off
        self.calc()

    def calc(self):
        a, b, c = self.p
        # q3map2 PlaneFromPoints: normal = cross(c-a, b-a)
        self.n = norm(cross(sub(c, a), sub(b, a)))
        self.d = dot(self.n, a)

    def flip(self):
        self.p = [self.p[0], self.p[2], self.p[1]]
        self.calc()


class Brush:
    """kind: solid | clip | water | trigger | nodraw_decal"""
    def __init__(self, planes, kind='solid', detail=True, tag='', inside=None):
        self.planes, self.kind, self.detail, self.tag = planes, kind, detail, tag
        if inside is None:
            raise ValueError('need interior point for ' + tag)
        for p in self.planes:  # orient all normals outward (interior point on negative side)
            if dot(p.n, inside) - p.d > 0:
                p.flip()
        self.verts = self._verts()
        if len(self.verts) < 4:
            raise ValueError('degenerate brush ' + tag)
        self.mins = tuple(min(v[i] for v in self.verts) for i in range(3))
        self.maxs = tuple(max(v[i] for v in self.verts) for i in range(3))

    def _verts(self):
        out = []
        pl = self.planes
        for i, j, k in itertools.combinations(range(len(pl)), 3):
            n1, n2, n3 = pl[i].n, pl[j].n, pl[k].n
            det = dot(n1, cross(n2, n3))
            if abs(det) < 1e-9: continue
            v = add(add(mul(cross(n2, n3), pl[i].d), mul(cross(n3, n1), pl[j].d)), mul(cross(n1, n2), pl[k].d))
            v = mul(v, 1.0/det)
            if all(dot(p.n, v) - p.d < 0.05 for p in pl):
                v = tuple(round(x, 3) for x in v)
                if v not in out: out.append(v)
        return out

    def is_box(self):
        return all(abs(abs(p.n[0])+abs(p.n[1])+abs(p.n[2]) - 1) < 1e-6 for p in self.planes) and len(self.planes) == 6

    def contains_point(self, pt, margin=0.0):
        return all(dot(p.n, pt) - p.d < -margin for p in self.planes)

    def write(self, f):
        f.write('{\n')
        flag = DETAIL if (self.detail and self.kind in ('solid', 'water', 'clip', 'decor')) else 0
        for p in self.planes:
            a, b, c = p.p
            f.write('( %s ) ( %s ) ( %s ) %s %d %d %d %s %s %d 0 0\n' % (
                ' '.join(fmt(x) for x in a), ' '.join(fmt(x) for x in b), ' '.join(fmt(x) for x in c),
                p.tex, p.off[0], p.off[1], p.rot, fmt(p.scale[0] if isinstance(p.scale, tuple) else p.scale),
                fmt(p.scale[1] if isinstance(p.scale, tuple) else p.scale), flag))
        f.write('}\n')


def fmt(x):
    if abs(x - round(x)) < 1e-6: return str(int(round(x)))
    return ('%.4f' % x).rstrip('0').rstrip('.')


def sum_v(vs):
    s = (0.0, 0.0, 0.0)
    for v in vs: s = add(s, v)
    return s


def box(x1, y1, z1, x2, y2, z2, tex, faces=None, scale=0.5, kind='solid', detail=True, tag='', scales=None, offs=None):
    """Axis aligned box. faces: dict top/bottom/n/s/e/w -> texture."""
    assert x2 > x1 and y2 > y1 and z2 > z1, (tag, x1, y1, z1, x2, y2, z2)
    faces = faces or {}; scales = scales or {}
    t = lambda k: faces.get(k, tex)
    s = lambda k: scales.get(k, scale)
    offs = offs or {}
    P = [
        Plane((x1, y1, z2), (x1, y2, z2), (x2, y2, z2), t('top'), s('top')),      # top z2
        Plane((x1, y1, z1), (x2, y1, z1), (x2, y2, z1), t('bottom'), s('bottom')),
        Plane((x1, y2, z1), (x2, y2, z1), (x2, y2, z2), t('n'), s('n')),           # north y2
        Plane((x1, y1, z1), (x1, y1, z2), (x2, y1, z2), t('s'), s('s')),
        Plane((x2, y1, z1), (x2, y1, z2), (x2, y2, z2), t('e'), s('e')),           # east x2
        Plane((x1, y1, z1), (x1, y2, z1), (x1, y2, z2), t('w'), s('w')),
    ]
    for p, k in zip(P, ('top', 'bottom', 'n', 's', 'e', 'w')):
        if k in offs: p.off = offs[k]
    return Brush(P, kind, detail, tag, inside=((x1+x2)/2, (y1+y2)/2, (z1+z2)/2))


def brush_from_points(planes_pts, inside, kind='solid', detail=True, tag='', scale=0.5):
    """planes_pts: list of (a,b,c,tex[,scale])"""
    P = []
    for item in planes_pts:
        a, b, c, tex = item[:4]
        sc = item[4] if len(item) > 4 else scale
        P.append(Plane(a, b, c, tex, sc))
    return Brush(P, kind, detail, tag, inside=inside)


# ---------------------------------------------------------------- overlap (SAT)
def _proj(verts, axis):
    vals = [dot(v, axis) for v in verts]
    return min(vals), max(vals)


def _edges(b):
    es = set()
    vs = b.verts
    for i in range(len(vs)):
        for j in range(i+1, len(vs)):
            # an edge lies on >= 2 planes
            on = [p for p in b.planes if abs(dot(p.n, vs[i])-p.d) < 0.05 and abs(dot(p.n, vs[j])-p.d) < 0.05]
            if len(on) >= 2:
                e = norm(sub(vs[j], vs[i]))
                es.add(tuple(round(x, 4) for x in e))
    return list(es)


def overlap(a, b, tol=0.05):
    """True if the interiors of two convex brushes intersect (touching is fine)."""
    for i in range(3):
        if a.maxs[i] <= b.mins[i] + tol or b.maxs[i] <= a.mins[i] + tol:
            return False
    if a.is_box() and b.is_box():
        return True
    axes = [p.n for p in a.planes] + [p.n for p in b.planes]
    for e1 in _edges(a):
        for e2 in _edges(b):
            c = cross(e1, e2)
            if dot(c, c) > 1e-6: axes.append(norm(c))
    for ax in axes:
        a0, a1 = _proj(a.verts, ax)
        b0, b1 = _proj(b.verts, ax)
        if a1 <= b0 + tol or b1 <= a0 + tol:
            return False
    return True


def aabb_brush_overlap(mins, maxs, b, tol=0.05):
    bx = box(mins[0], mins[1], mins[2], maxs[0], maxs[1], maxs[2], 'x')
    return overlap(bx, b, tol)


# ---------------------------------------------------------------- entities
class Entity:
    def __init__(self, classname, **kv):
        self.kv = {'classname': classname}
        for k, v in kv.items():
            self.kv[k] = v
        self.brushes = []

    def write(self, f):
        f.write('{\n')
        for k, v in self.kv.items():
            if isinstance(v, (tuple, list)):
                v = ' '.join(fmt(x) for x in v)
            f.write('"%s" "%s"\n' % (k, v))
        for b in self.brushes:
            b.write(f)
        f.write('}\n')


# ---------------------------------------------------------------- bridge to wop_tools/wopmap.py
def from_wop(wb, kind='solid', detail=True, tag=''):
    """Convert a wopmap.Brush (convex hull of points) into a mapgen_lib Brush."""
    P = []
    for f in wb.faces:
        sc = tuple(f.sc) if isinstance(f.sc, (tuple, list)) else f.sc
        pl = Plane(f.pts[0], f.pts[1], f.pts[2], f.tex, sc, f.rot, f.off)
        P.append(pl)
    v = wb.verts()
    inside = tuple(float(x) for x in v.mean(0))
    return Brush(P, kind, detail, tag, inside=inside)
