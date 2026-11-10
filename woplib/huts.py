"""woplib.huts - simple enterable buildings as convex brushes for MapKit.solid_piece (promoted from padgold).

    bs = huts.brushes(x0, y0, x1, y1, z0, H, {'n': [(a, b, zlo, zhi)], 'e': [...]})     # walls with openings, floor, roof
    K.solid_piece('store', bs + extra, huts.texfn(TX, x0, y0, x1, y1, z0, H, front='n', fac='fac_store',
                                                    side='side_store'), hidden=bs + extra)

One call gives the visible MD3 and the same shapes as weapclip, so doors, windows and roofs always match what bots
walk on. Openings are (a, b, zlo, zhi) with a..b along x for the n/s walls and along y for the e/w walls, in world
coordinates. `Row` lays buildings out along a street that runs north-south (fronts facing east or west), so a
generator can describe interiors once in street coordinates (u along the street, v = depth behind the front).
"""
from wopmap import box, sub_rects
from . import models as ML

CAULK = 'common/caulk'
WALL = 16


def brushes(x0, y0, x1, y1, z0, H, openings=None, floor=True, roof=True, t=WALL, tex=CAULK):
    op = openings or {}
    out = []
    walls = {'n': (x0, y1 - t, x1, y1), 's': (x0, y0, x1, y0 + t),
             'e': (x1 - t, y0 + t, x1, y1 - t), 'w': (x0, y0 + t, x0 + t, y1 - t)}
    for k, (a0, b0, a1, b1) in walls.items():
        horiz = k in 'ns'
        u0, u1 = (a0, a1) if horiz else (b0, b1)
        holes = [(a, zl, b, zh) for (a, b, zl, zh) in op.get(k, [])]
        for (ua, za, ub, zb) in sub_rects((u0, z0, u1, z0 + H), holes):
            out.append(box((ua, b0, za), (ub, b1, zb), tex) if horiz else box((a0, ua, za), (a1, ub, zb), tex))
    if floor: out.append(box((x0 + t, y0 + t, z0), (x1 - t, y1 - t, z0 + 16), tex))
    if roof: out.append(box((x0, y0, z0 + H), (x1, y1, z0 + H + 16), tex))
    return out


def texfn(TX, x0, y0, x1, y1, z0, H, front='n', fac=None, side='wood', roof='tin', floor='floor', inner='interior',
          jamb='timber', t=WALL):
    """per-face material for brushes(): the facade image `fac` fitted once across the whole front (never mirrored),
    `side` on the other outer faces, `jamb` in door/window reveals, `inner` inside, roof/floor tops; faces resting on
    the ground are dropped. Keys are TX.material names."""
    ztop = z0 + H + 16

    def f(c, n, poly):
        nx, ny, nz = n
        if nz > 0.7:
            return TX[roof if c[2] >= z0 + H + 15 else floor], ML.planar_uv(n, 256)
        if nz < -0.7:
            if c[2] <= z0 + 0.5: return None
            return TX[inner], ML.planar_uv(n, 256)
        outer = ((ny > 0.7 and c[1] >= y1 - 0.5, 'n'), (ny < -0.7 and c[1] <= y0 + 0.5, 's'),
                 (nx > 0.7 and c[0] >= x1 - 0.5, 'e'), (nx < -0.7 and c[0] <= x0 + 0.5, 'w'))
        for ok, k in outer:
            if not ok: continue
            if k == front and fac:
                W = x1 - x0 if k in 'ns' else y1 - y0
                hz = ztop - z0
                if k == 'n': uf = lambda p: ((x1 - p[0]) / W, (ztop - p[2]) / hz)
                elif k == 's': uf = lambda p: ((p[0] - x0) / W, (ztop - p[2]) / hz)
                elif k == 'e': uf = lambda p: ((p[1] - y0) / W, (ztop - p[2]) / hz)
                else: uf = lambda p: ((y1 - p[1]) / W, (ztop - p[2]) / hz)
                return TX[fac], uf
            return TX[side], ML.planar_uv(n, 256)
        jam = ((abs(nx) > 0.7 and (y1 - t < c[1] < y1 or y0 < c[1] < y0 + t)) or
               (abs(ny) > 0.7 and (x1 - t < c[0] < x1 or x0 < c[0] < x0 + t)))
        return TX[jamb if jam else inner], ML.planar_uv(n, 128 if jam else 256)
    return f


class Row:
    """street coordinates for a building whose front faces a north-south street: u = world y along the street,
    v = depth behind the front plane (negative = out in the street). side 'E' = east of the street (front faces west),
    'W' = west of it (front faces east)."""

    def __init__(self, side, front_x, depth):
        self.s = 1 if side == 'E' else -1
        self.fx = front_x * self.s; self.depth = depth
        self.front = 'w' if side == 'E' else 'e'
        self.back = 'e' if side == 'E' else 'w'
        self.into = 'e' if side == 'E' else 'w'          # compass direction of increasing v
        self.out = 'w' if side == 'E' else 'e'
        self.ang = 180 if side == 'E' else 0             # model authored with its back to -x (west-row orientation)

    def x(self, v): return self.fx + self.s * v

    def rect(self, u0, u1):
        xa, xb = sorted((self.x(0), self.x(self.depth)))
        return xa, u0, xb, u1

    def box(self, u0, v0, z0, u1, v1, z1, tex=CAULK):
        xa, xb = sorted((self.x(v0), self.x(v1)))
        return box((xa, min(u0, u1), z0), (xb, max(u0, u1), z1), tex)

    def span(self, v0, v1):
        """(x0, x1) sorted for a v range - for stairs16/keep_clear rectangles"""
        return tuple(sorted((self.x(v0), self.x(v1))))
