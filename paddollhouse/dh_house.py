"""Rosewood Manor, the dollhouse: wall specs shared by the brush collision (build_dollhouse.py) and the MD3 facade.

A Wall is an axis-aligned slab with rectangular openings (windows, doors). Collision = the slab minus the openings
(sub_rects in the wall's (u, z) plane), textured per face with the wallpaper of the room it faces; the MD3 facade =
pink clapboard on the outer faces plus white trims, window casings, shutters, belt courses, cornice and brackets.
The house is cut away at the back (south, y = DY0) like a real dollhouse: every room is open to the bedroom.

  ground floor   kitchen (west) | hall + front door + stair (centre) | parlour (east)
  first floor    bathroom       | landing + balcony door             | master bedroom
  second floor   nursery        | upper landing (stair to the roof)   | library
  roof           west attic     | terrace + tower (pad to its deck)   | east attic, two gables with walkable slopes
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, tube, rbox, sphere, ellipsoid, disc, prism, rot_z, rot_axis, revolve
from wopmap import sub_rects
from dhlib import *
import layout as L

TX = lambda n: 'paddollhouse/' + n
CAULK = 'common/caulk'

# room finishes: (floor index, column) -> wall, floor, ceiling textures
ROOMS = {
    (0, 'W'): ('wp_kitchen', 'checker', 'dh_ceiling'), (0, 'C'): ('wp_hall', 'parquet', 'dh_ceiling'), (0, 'E'): ('wp_parlour', 'carpet_rose', 'dh_ceiling'),
    (1, 'W'): ('wp_bath', 'checker', 'dh_ceiling'), (1, 'C'): ('wp_hall', 'parquet', 'dh_ceiling'), (1, 'E'): ('wp_bedroom', 'carpet_blue', 'dh_ceiling'),
    (2, 'W'): ('wp_nursery', 'boards_pale', 'dh_ceiling'), (2, 'C'): ('wp_hall', 'parquet', 'dh_ceiling'), (2, 'E'): ('wp_library', 'parquet', 'dh_ceiling'),
    (3, 'W'): ('attic_boards', 'attic_boards', 'attic_boards'), (3, 'C'): ('paint_cream', 'stone', 'dh_ceiling'), (3, 'E'): ('attic_boards', 'attic_boards', 'attic_boards'),
}
COLS = {'W': (L.DX0 + L.WT, -L.IWX), 'C': (-L.IWX, L.IWX), 'E': (L.IWX, L.DX1 - L.WT)}


def col_of(x):
    return 'W' if x < -L.IWX else ('E' if x > L.IWX else 'C')


def floor_of(z):
    for i in (3, 2, 1, 0):
        if z >= L.FL[i] - 8: return i
    return 0


class Hole:
    def __init__(self, u0, u1, z0, z1, kind='win', glass=True, shutters=True, arch=False):
        self.u0, self.u1, self.z0, self.z1, self.kind, self.glass, self.shutters, self.arch = u0, u1, z0, z1, kind, glass, shutters, arch


class Wall:
    """axis 'x': runs along x (outer face at y = fixed); axis 'y': runs along y (outer face x = fixed).
    out = +1/-1 outward direction; out = 0: interior wall occupying fixed..fixed+thick.
    tin: texture of the inside face (or (low-side, high-side) textures for interior walls)."""
    def __init__(self, axis, fixed, out, u0, u1, z0, z1, holes=(), thick=16, tin=CAULK, tout=CAULK, name='', vu=None, floor=0):
        self.axis, self.fixed, self.out, self.u0, self.u1, self.z0, self.z1 = axis, fixed, out, u0, u1, z0, z1
        self.holes = list(holes); self.thick = thick; self.tin = tin; self.tout = tout; self.name = name
        self.vu = vu or (u0, u1); self.floor = floor

    def span(self):
        if self.out > 0: return self.fixed - self.thick, self.fixed
        if self.out < 0: return self.fixed, self.fixed + self.thick
        return self.fixed, self.fixed + self.thick

    def pieces(self):
        p0, p1 = self.span()
        rects = sub_rects((self.u0, self.z0, self.u1, self.z1), [(h.u0, h.z0, h.u1, h.z1) for h in self.holes])
        out_ = []
        for (ua, za, ub, zb) in rects:
            if self.axis == 'x': out_.append(((ua, p0, za), (ub, p1, zb)))
            else: out_.append(((p0, ua, za), (p1, ub, zb)))
        return out_

    def face_tex(self, n, centre):
        perp = n[1] if self.axis == 'x' else n[0]
        if abs(perp) > 0.9:
            if self.out == 0:
                return self.tin[0] if perp < 0 else self.tin[1]
            return self.tout if perp * self.out > 0 else self.tin
        if n[2] > 0.9 or n[2] < -0.9: return CAULK
        # jambs: the cut edge at the open back is painted, door/window reveals take the room paper
        along = n[0] if self.axis == 'x' else n[1]
        if self.axis == 'y' and along < -0.9 and centre[1] <= L.DY0 + 1: return TX('dh_edge')
        if self.out == 0 and self.axis == 'y' and along < -0.9 and centre[1] <= L.DY0 + 1: return TX('dh_edge')
        return TX('paint_white')

    def P(self, u, z, off=0.0):
        f = self.fixed + self.out * off
        return np.array([u, f, z], float) if self.axis == 'x' else np.array([f, u, z], float)

    def normal(self):
        return np.array([0, self.out, 0.0]) if self.axis == 'x' else np.array([self.out, 0, 0.0])


# ================================================================================================= wall specs
def win(u0, u1, f, **kw):
    return Hole(u0, u1, L.FL[f] + L.WIN_Z[0], L.FL[f] + L.WIN_Z[1], **kw)


def door(u0, u1, f, **kw):
    return Hole(u0, u1, L.FL[f], L.FL[f] + L.DOOR_H, 'door', glass=False, shutters=False, **kw)


def wall_z(f):
    """outer wall band of floor f: from its floor level to the next floor level (the slab band belongs to the wall)"""
    return L.FL[f], L.FL[f + 1]


def outer_walls():
    """per floor and room: the outer walls of the house (west, north, east); the back (south) is open"""
    out_ = []
    for f in range(3):
        z0, z1 = wall_z(f)
        # west wall (kitchen / bathroom / nursery)
        hw = [win(640, 768, f)]
        hw.append(door(*L.SIDE_DOOR_Y, f) if f == 0 else win(960, 1088, f))
        out_.append(Wall('y', L.DX0, -1, L.DY0, L.DY1 - L.WT, z0, z1, hw, tin=TX(ROOMS[(f, 'W')][0]), name=f'w{f}', floor=f, vu=(L.DY0, L.DY1)))
        he = [win(640, 768, f)]
        he.append(door(*L.SIDE_DOOR_Y, f) if f == 0 else win(960, 1088, f))
        out_.append(Wall('y', L.DX1, 1, L.DY0, L.DY1 - L.WT, z0, z1, he, tin=TX(ROOMS[(f, 'E')][0]), name=f'e{f}', floor=f, vu=(L.DY0, L.DY1)))
        # north (front) wall in three runs
        for c, (ua, ub) in (('W', (L.DX0, -L.IWX)), ('C', (-L.IWX, L.IWX)), ('E', (L.IWX, L.DX1))):
            hs = []
            if c == 'W': hs = [win(-896, -768, f), win(-576, -448, f)]
            elif c == 'E': hs = [win(448, 576, f), win(768, 896, f)]
            else:
                if f == 0: hs = [door(*L.FRONT_DOOR, f), win(-256, -176, f, shutters=False), win(176, 256, f, shutters=False)]
                elif f == 1: hs = [door(*L.BALC_DOOR, f), win(-256, -176, f, shutters=False), win(176, 256, f, shutters=False)]
                else: hs = [Hole(-96, 96, L.FL[f] + 80, L.FL[f] + 272, arch=True, shutters=False)]
            out_.append(Wall('x', L.DY1, 1, ua, ub, z0, z1, hs, tin=TX(ROOMS[(f, c)][0]), name=f'n{c}{f}', floor=f))
    return out_


def inner_walls():
    """the two interior walls per floor (between the side rooms and the hall), doors near the open back"""
    out_ = []
    for f in range(3):
        z0, z1 = L.FL[f], L.FL[f + 1] - L.SLAB
        for (x, lo, hi) in ((-L.IWX, 'W', 'C'), (L.IWX - L.WT, 'C', 'E')):
            hs = [Hole(L.IDOOR_Y[0], L.IDOOR_Y[1], L.FL[f], L.FL[f] + L.DOOR_H, 'door', glass=False, shutters=False)]
            out_.append(Wall('y', x, 0, L.DY0, L.DY1 - L.WT, z0, z1, hs, tin=(TX(ROOMS[(f, lo)][0]), TX(ROOMS[(f, hi)][0])), name=f'i{lo}{f}', floor=f))
    return out_


def tower_walls():
    x0, y0, x1, y1 = L.TOWER
    z0, z1 = L.TOWER_F, L.TOWER_TOP
    t = TX('paint_cream')
    wz = (z0 + 96, z0 + 256)
    S_ = Wall('x', y0, -1, x0, x1, z0, z1, [Hole(-64, 64, z0, z0 + L.DOOR_H, 'door', glass=False, shutters=False)], tin=t, name='ts')
    N_ = Wall('x', y1, 1, x0, x1, z0, z1, [Hole(-64, 64, wz[0], wz[1], shutters=False)], tin=t, name='tn')
    W_ = Wall('y', x0, -1, y0 + L.WT, y1 - L.WT, z0, z1, [Hole(1016, 1144, wz[0], wz[1], shutters=False)], tin=t, name='tw', vu=(y0, y1))
    E_ = Wall('y', x1, 1, y0 + L.WT, y1 - L.WT, z0, z1, [Hole(1016, 1144, wz[0], wz[1], shutters=False)], tin=t, name='te', vu=(y0, y1))
    return [S_, N_, W_, E_]


def gable_wall_pts(g, y0, y1):
    """front gable triangle (above the attic floor) as a convex point set between y0..y1, under the roof underside"""
    xa, xb = g
    xm = (xa + xb) / 2
    zr = L.ridge_z(g) - L.ROOF_T
    za = L.FL[3]
    pts = []
    for y in (y0, y1):
        pts += [(xa, y, za), (xb, y, za), (xm - L.RIDGE_W / 2, y, zr), (xm + L.RIDGE_W / 2, y, zr)]
    return pts


GABLE_WIN = 112                 # round window in each front gable: square collision hole, circle in the MD3


# ================================================================================================= facade MD3
def facade(X, w, st, o, tile=96.0, top_trim=True, base=False, belt=True):
    """clapboard over the outer face of wall w (minus its openings), casings, sills, shutters, belt course"""
    o = np.asarray(o, float)
    nrm = w.normal()
    vu0, vu1 = w.vu
    holes = [(h.u0, h.z0, h.u1, h.z1) for h in w.holes]
    rects = sub_rects((vu0, w.z0, vu1, w.z1), holes)
    M = X.mesh(st['siding'])
    sg = 1 if (w.axis == 'x' and w.out < 0) or (w.axis == 'y' and w.out > 0) else -1
    for (ua, za, ub, zb) in rects:
        p = [w.P(ua, za, 1.0) - o, w.P(ub, za, 1.0) - o, w.P(ub, zb, 1.0) - o, w.P(ua, zb, 1.0) - o]
        M.poly(p, nrm, [(sg * ua / tile, -za / tile), (sg * ub / tile, -za / tile), (sg * ub / tile, -zb / tile), (sg * ua / tile, -zb / tile)])

    def strip(ua, za, ub, zb, prot, sh, r=1.0):
        a = w.P(ua, za, 0.5) - o; b = w.P(ub, zb, prot) - o
        rbox(X.mesh(sh), np.minimum(a, b), np.maximum(a, b), r=r, k=2, tile=64)

    def band(z0, z1, prot, sh):
        cuts = [(h.u0 - 8, h.u1 + 8) for h in w.holes if h.z0 < z1 and h.z1 > z0]
        for (ua, _, ub, _) in sub_rects((vu0, 0, vu1, 1), [(a, 0, b, 1) for (a, b) in cuts]):
            if ub - ua > 4: strip(ua, z0, ub, z1, prot, sh, 1.5)
    if base: band(w.z0, w.z0 + 24, 4, st['base'])
    if belt: band(w.z1 - 10, w.z1 + 6, 5, st['trim'])
    for h in w.holes:
        fw = 10
        if h.arch:
            # arched window: casing up the sides, round top as a tube
            strip(h.u0 - fw, h.z0, h.u0, h.z1 - (h.u1 - h.u0) / 2, 4, st['trim'])
            strip(h.u1, h.z0, h.u1 + fw, h.z1 - (h.u1 - h.u0) / 2, 4, st['trim'])
            rr = (h.u1 - h.u0) / 2; cu = (h.u0 + h.u1) / 2; cz = h.z1 - rr
            pts = [w.P(cu + (rr + fw / 2) * math.cos(a), cz + (rr + fw / 2) * math.sin(a), 3) - o for a in np.linspace(0, math.pi, 17)]
            tube(X.mesh(st['trim']), pts, 6, nseg=8)
            strip(h.u0 - fw - 6, h.z0 - 10, h.u1 + fw + 6, h.z0, 9, st['trim'])
            continue
        strip(h.u0 - fw, h.z0, h.u0, h.z1 + fw, 4, st['trim'])
        strip(h.u1, h.z0, h.u1 + fw, h.z1 + fw, 4, st['trim'])
        strip(h.u0 - fw, h.z1, h.u1 + fw, h.z1 + fw, 4, st['trim'])
        strip(h.u0 - fw - 8, h.z1 + fw, h.u1 + fw + 8, h.z1 + fw + 10, 9, st['trim'])           # header cap
        # little pediment over the header
        cu = (h.u0 + h.u1) / 2; zt = h.z1 + fw + 10
        tri = [w.P(h.u0 - fw - 4, zt, 0.5) - o, w.P(h.u1 + fw + 4, zt, 0.5) - o, w.P(cu, zt + 22, 0.5) - o]
        m = Mesh()
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            q = [a, b, b + nrm * 6, a + nrm * 6]
            m.quad(*q, tile=64)
        m.poly([p + nrm * 6 for p in tri], nrm, [(0, 0), (1, 0), (0.5, 0.4)])
        X.mesh(st['trim']).add(m)
        if h.kind == 'win':
            strip(h.u0 - fw - 6, h.z0 - 10, h.u1 + fw + 6, h.z0, 10, st['trim'])                 # sill
            # glazing bars (cross)
            cu = (h.u0 + h.u1) / 2; cz = (h.z0 + h.z1) / 2
            strip(cu - 2.5, h.z0, cu + 2.5, h.z1, 2, st['trim'], 0.6)
            strip(h.u0, cz - 2.5, h.u1, cz + 2.5, 2, st['trim'], 0.6)
            if h.shutters and 'shutter' in st:
                sw = (h.u1 - h.u0) * 0.42
                for (ua, ub) in ((h.u0 - fw - sw - 2, h.u0 - fw - 2), (h.u1 + fw + 2, h.u1 + fw + sw + 2)):
                    a = w.P(ua, h.z0 + 2, 1.0) - o; b = w.P(ub, h.z1 + 4, 3.5) - o
                    rbox(X.mesh(st['shutter']), np.minimum(a, b), np.maximum(a, b), r=0.8, k=1, tile=64)
                    # louvre slats
                    for z in np.arange(h.z0 + 14, h.z1 - 6, 14):
                        a = w.P(ua + 4, z, 3.5) - o; b = w.P(ub - 4, z + 5, 5.0) - o
                        rbox(X.mesh(st['shutter']), np.minimum(a, b), np.maximum(a, b), r=0.5, k=1, tile=64)
            # window box with flowers on the ground-floor front windows
            if w.floor == 0 and w.axis == 'x' and 'box' in st and abs(cu) > L.IWX:
                a = w.P(h.u0 - 4, h.z0 - 40, 1) - o; b = w.P(h.u1 + 4, h.z0 - 12, 26) - o
                rbox(X.mesh(st['box']), np.minimum(a, b), np.maximum(a, b), r=2, k=2, tile=64)
                for k in range(7):
                    uu = h.u0 + 4 + (h.u1 - h.u0 - 8) * (k + 0.5) / 7
                    c = w.P(uu, h.z0 - 4 + 5 * (k % 2), 13) - o
                    sphere(X.mesh(st['flower'] if k % 2 else st['flower2']), c, 9, nu=8, nv=5)
        else:
            # transom light over doors
            pass
    return X


def corner_board(X, sh, x, y, z0, z1, o, s=12):
    o = np.asarray(o, float)
    rbox(X.mesh(sh), np.array([x - s, y - s, z0]) - o, np.array([x + s, y + s, z1]) - o, r=2, k=2, tile=64)


def house_shaders():
    return dict(siding=S('siding_pink', 'lm'), trim=S('trim_white', 'lm'), shutter=S('shutter_mint', 'lm'), base=S('trim_white', 'lm'),
                box=S('trim_white', 'lm'), flower=S('flower_red', 'lm'), flower2=S('flower_yellow', 'lm'))


def house_facade():
    """the main facade model: clapboard + trims on the three outer walls, corner boards, cornice with brackets"""
    st = house_shaders()
    X = Model()
    o = (0, (L.DY0 + L.DY1) / 2, 0)
    for w in outer_walls():
        facade(X, w, st, o, base=(w.floor == 0), belt=(w.floor < 2))
    oo = np.asarray(o, float)
    for (x, y) in ((L.DX0, L.DY1), (L.DX1, L.DY1)):
        corner_board(X, st['trim'], x, y, L.FL[0], L.FL[3] + 4, oo, 14)
    for x in (L.DX0, L.DX1):
        corner_board(X, st['trim'], x, L.DY0 + 10, L.FL[0], L.FL[3] + 4, oo, 10)
    # cornice at the top of the walls (under the eaves)
    for w in outer_walls():
        if w.floor != 2: continue
        a = w.P(w.vu[0], L.FL[3] - 22, 0) - oo; b = w.P(w.vu[1], L.FL[3], 12) - oo
        rbox(X.mesh(st['trim']), np.minimum(a, b), np.maximum(a, b), r=3, k=2, tile=64)
        n = int((w.vu[1] - w.vu[0]) / 88)
        for k in range(n + 1):
            uu = w.vu[0] + 24 + (w.vu[1] - w.vu[0] - 48) * k / max(1, n)
            a = w.P(uu - 5, L.FL[3] - 58, 0) - oo; b = w.P(uu + 5, L.FL[3] - 22, 10) - oo
            rbox(X.mesh(st['trim']), np.minimum(a, b), np.maximum(a, b), r=2, k=2, tile=64)
    # cut edge trim along the open back (white boards on the wall ends and slab edges)
    E = X.mesh(S('trim_white', 'lm'))
    for f in (1, 2, 3):
        rbox(E, np.array([L.DX0, L.DY0 - 2, L.FL[f] - L.SLAB - 4]) - oo, np.array([L.DX1, L.DY0 + 1, L.FL[f] + 2]) - oo, r=1, k=1, tile=64)
    return X


def window_glass_brushes(w):
    """(mn, mx, w, h) glass slabs for the window holes of wall w (centred in the wall)"""
    out_ = []
    p0, p1 = w.span(); pm = (p0 + p1) / 2
    for h in w.holes:
        if h.kind != 'win' or not h.glass: continue
        if w.axis == 'x': out_.append(((h.u0, pm - 1, h.z0), (h.u1, pm + 1, h.z1)))
        else: out_.append(((pm - 1, h.u0, h.z0), (pm + 1, h.u1, h.z1)))
    return out_


# ================================================================================================= roofs
def roof_model(g):
    """one gable roof: fish-scale shingles on both slopes (overhanging 32 at the eaves and the front), a rounded
    ridge cap, scalloped gingerbread bargeboards and a finial on the front gable, a painted cut edge at the back"""
    X = Model()
    Sh = X.mesh(S('shingle_lilac', 'lm', shade=60)); Tr = X.mesh(S('trim_white', 'lm')); Cut = X.mesh(S('trim_white', 'lm'))
    xa, xb = g; xm = (xa + xb) / 2
    hw = (xb - xa) / 2
    zr = L.ridge_z(g)
    y0, y1 = L.ROOF_Y0, L.ROOF_Y1 + 16
    o = np.array([xm, (y0 + y1) / 2, L.FL[3]])
    over = 32
    rw = L.RIDGE_W / 2
    for sgn in (-1, 1):
        # slope from the ridge edge (x = xm + sgn*rw, zr) out to the eave + overhang
        xe = xm + sgn * (hw + over)
        ze = L.FL[3] - over * L.TP
        xr = xm + sgn * rw
        p = [np.array([xr, y0, zr + 2]), np.array([xe, y0, ze + 2]), np.array([xe, y1, ze + 2]), np.array([xr, y1, zr + 2])]
        nrm = np.array([sgn * L.TP, 0, 1.0]); nrm /= np.linalg.norm(nrm)
        slope_len = math.hypot(hw + over - rw, zr - ze)
        nu, nv = 10, 12
        G = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2)); NN = np.zeros_like(G)
        for i in range(nv + 1):
            for j in range(nu + 1):
                a = p[0] + (p[1] - p[0]) * j / nu
                G[i, j] = a + (p[3] - p[0]) * i / nv - o
                UV[i, j] = (slope_len / 192 * j / nu, (y1 - y0) / 192 * i / nv)
                NN[i, j] = nrm
        Sh.grid(G, NN, UV)
        # underside of the overhang + fascia
        pu = [np.array([xm + sgn * hw, y0, L.FL[3] - 6]), np.array([xe, y0, ze - 6]), np.array([xe, y1, ze - 6]), np.array([xm + sgn * hw, y1, L.FL[3] - 6])]
        Tr.poly([q - o for q in pu], (0, 0, -1), [(0, 0), (1, 0), (1, 4), (0, 4)])
        a = np.array([min(xe, xe + sgn * 6), y0, ze - 14]); b = np.array([max(xe, xe + sgn * 6), y1, ze + 4])
        rbox(Tr, a - o, b - o, r=2, k=2, tile=64)
        # flat ridge walk (shingled)
    nv = 12
    for i in range(nv):
        ya_, yb_ = y0 + (y1 - y0) * i / nv, y0 + (y1 - y0) * (i + 1) / nv
        Sh.poly([np.array([xm - rw, ya_, zr + 6]) - o, np.array([xm + rw, ya_, zr + 6]) - o, np.array([xm + rw, yb_, zr + 6]) - o,
                 np.array([xm - rw, yb_, zr + 6]) - o], (0, 0, 1), [(0, i / 3), (0.25, i / 3), (0.25, (i + 1) / 3), (0, (i + 1) / 3)])
    # ridge cap rolls along both ridge edges (cover the 4u step up onto the ridge walk)
    for sgn in (-1, 1):
        tube(Tr, [np.array([xm + sgn * rw, y0, zr + 5]) - o, np.array([xm + sgn * rw, y1, zr + 5]) - o], 5, nseg=8)
    # gable ends: thickness of the slates (front y1 and the cut back y0)
    for (yy, mesh) in ((y1, Tr), (y0, Cut)):
        for sgn in (-1, 1):
            xe = xm + sgn * (hw + over); ze = L.FL[3] - over * L.TP; xr = xm + sgn * rw
            q = [np.array([xr, yy, zr + 2]), np.array([xe, yy, ze + 2]), np.array([xe, yy, ze - 6 - L.ROOF_T * 0.3]), np.array([xr, yy, zr - L.ROOF_T])]
            mesh.poly([v - o for v in q], (0, 1 if yy == y1 else -1, 0), [(0, 0), (1, 0), (1, 0.2), (0, 0.2)])
    # gingerbread bargeboards on the front gable: scalloped boards following both rakes + a finial
    B = X.mesh(S('trim_white', 'lm', tag='gb'))
    yb = y1 - 4
    for sgn in (-1, 1):
        xe = xm + sgn * (hw + over); ze = L.FL[3] - over * L.TP
        n = 14
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            pa = np.array([xm + (xe - xm) * t0, yb, zr + (ze - zr) * t0]); pb = np.array([xm + (xe - xm) * t1, yb, zr + (ze - zr) * t1])
            mid = (pa + pb) / 2 - np.array([0, 0, 18])
            m = Mesh()
            poly = [pa, pb, pb - [0, 0, 8], mid, pa - [0, 0, 8]]
            for v in range(len(poly)):
                a_, b_ = poly[v], poly[(v + 1) % len(poly)]
                m.quad(a_, b_, b_ + [0, 6, 0], a_ + [0, 6, 0], tile=48)
            m.poly([v_ for v_ in poly], (0, -1, 0), [(0, 0), (1, 0), (1, 0.2), (0.5, 0.5), (0, 0.2)])
            m.poly([v_ + [0, 6, 0] for v_ in poly], (0, 1, 0), [(0, 0), (1, 0), (1, 0.2), (0.5, 0.5), (0, 0.2)])
            B.add(m, t=-o)
            # drilled holes read as dark dots
            sphere(X.mesh(S('trim_dark', 'lm')), mid + np.array([0, 7, 10]) - o, 2.5, nu=6, nv=4)
    revolve(B, [(0, zr + 2), (10, zr + 2), (12, zr + 14), (6, zr + 26), (10, zr + 40), (4, zr + 60), (0, zr + 76)], n=10, cx=xm - o[0], cy=yb - o[1])
    tube(B, [np.array([xm, yb + 2, zr + 2]) - o, np.array([xm, yb + 2, zr - 70]) - o], 4, nseg=8)
    return X, o


def gable_wall_model(g):
    """front gable triangle: fish-scale shingles in pink with a round window and its white frame"""
    X = Model()
    Sh = X.mesh(S('scale_pink', 'lm')); Tr = X.mesh(S('trim_white', 'lm'))
    xa, xb = g; xm = (xa + xb) / 2
    zr = L.ridge_z(g) - L.ROOF_T
    za = L.FL[3]
    o = np.array([xm, L.DY1, za])
    yy = L.DY1 + 1
    cz = za + 150
    R = GABLE_WIN / 2 + 4
    # triangle minus the circle: fan of quads from the circle to the triangle edge
    dx = L.ROOF_T / L.TP
    tri = [np.array([xa + dx, za]), np.array([xb - dx, za]), np.array([xm + L.RIDGE_W / 2, zr]), np.array([xm - L.RIDGE_W / 2, zr])]
    nseg = 48
    for k in range(nseg):
        a0, a1 = 2 * math.pi * k / nseg, 2 * math.pi * (k + 1) / nseg
        def edge(a):
            d = np.array([math.cos(a), math.sin(a)]); c = np.array([xm, cz])
            best = 1e9
            for i in range(4):
                p, q = tri[i], tri[(i + 1) % 4]
                e = q - p
                den = d[0] * (-e[1]) - d[1] * (-e[0])
                if abs(den) < 1e-9: continue
                rel = p - c
                t = (rel[0] * (-e[1]) - rel[1] * (-e[0])) / den
                s = (d[0] * rel[1] - d[1] * rel[0]) / den
                if t > 0 and -1e-6 <= s <= 1 + 1e-6: best = min(best, t)
            return np.array([xm, cz]) + d * best
        c0 = np.array([xm + R * math.cos(a0), cz + R * math.sin(a0)]); c1 = np.array([xm + R * math.cos(a1), cz + R * math.sin(a1)])
        e0, e1 = edge(a0), edge(a1)
        q = [np.array([p_[0], yy, p_[1]]) - o for p_ in (c0, e0, e1, c1)]
        Sh.poly(q, (0, 1, 0), [(-p_[0] / 96, -p_[1] / 96) for p_ in (c0, e0, e1, c1)])
    pts = [np.array([xm + (R + 3) * math.cos(a), yy + 3, cz + (R + 3) * math.sin(a)]) - o for a in np.linspace(0, 2 * math.pi, 33)]
    tube(Tr, pts, 7, nseg=8, caps=(False, False))
    for a in (0, math.pi / 2):
        p0 = np.array([xm + R * math.cos(a), yy + 1, cz + R * math.sin(a)]) - o; p1 = np.array([xm - R * math.cos(a), yy + 1, cz - R * math.sin(a)]) - o
        tube(Tr, [p0, p1], 2.5, nseg=6)
    return X, o


def tower_model():
    """the tower: clapboard + trims, cornice, a crenellated parapet with white caps, corner boards, a flag pole"""
    st = house_shaders()
    X = Model()
    x0, y0, x1, y1 = L.TOWER
    o = np.array([0, (y0 + y1) / 2, L.TOWER_F])
    for w in tower_walls():
        facade(X, w, st, o, belt=False)
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        corner_board(X, st['trim'], x, y, L.TOWER_F, L.TOWER_TOP, o, 12)
    T_ = X.mesh(st['trim'])
    rbox(T_, np.array([x0 - 14, y0 - 14, L.TOWER_TOP - 26]) - o, np.array([x1 + 14, y1 + 14, L.TOWER_TOP - 6]) - o, r=3, k=2, tile=64)
    # parapet: siding band + white cap; merlons only on the corners so the deck stays open to fire
    P_ = X.mesh(st['siding'])
    z0, z1 = L.TOWER_TOP - 6, L.TOWER_TOP + L.PARAPET
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        a = np.array([*a, 0.0]); b = np.array([*b, 0.0])
        d = b - a; d /= np.linalg.norm(d); n = np.array([d[1], -d[0], 0])
        q = [a + n * 1 + [0, 0, z0], b + n * 1 + [0, 0, z0], b + n * 1 + [0, 0, z1], a + n * 1 + [0, 0, z1]]
        P_.poly([v - o for v in q], n, [(0, 0), (np.linalg.norm(b - a) / 96, 0), (np.linalg.norm(b - a) / 96, -0.3), (0, -0.3)])
    for (a, b) in (((x0, y0), (x1, y0 + 16)), ((x0, y1 - 16), (x1, y1)), ((x0, y0), (x0 + 16, y1)), ((x1 - 16, y0), (x1, y1))):
        rbox(T_, np.array([a[0] - 4, a[1] - 4, z1]) - o, np.array([b[0] + 4, b[1] + 4, z1 + 8]) - o, r=2, k=2, tile=64)
    for (x, y) in ((x0 + 8, y0 + 8), (x1 - 8, y0 + 8), (x0 + 8, y1 - 8), (x1 - 8, y1 - 8)):
        revolve(T_, [(0, z1 + 8), (16, z1 + 8), (16, z1 + 30), (20, z1 + 34), (0, z1 + 34)], n=12, cx=x - o[0], cy=y - o[1])
        sphere(X.mesh(S('gold', 'lms')), np.array([x, y, z1 + 46]) - o, 10, nu=10, nv=6)
    return X, o


def flag_model():
    """flag pole for a tower corner post (origin at the post top) with a waving pennant"""
    X = Model()
    tube(X.mesh(S('trim_white', 'lm')), [(0, 0, 0), (0, 0, 300)], 4, nseg=8)
    sphere(X.mesh(S('gold', 'lms')), (0, 0, 304), 8, nu=10, nv=6)
    F = X.mesh(S('pennant', 'flag', two=True))
    m = Mesh()
    pts = [(0, 0, 290), (0, 0, 220), (150, 0, 255)]
    m.poly(pts, (0, -1, 0), [(0, 0), (0, 1), (1, 0.5)])
    F.add(m)
    return X


def porch_model():
    """front porch: turned posts, beam with brackets and spandrel scrolls, the balcony balustrade on its roof,
    deck boards, and the open front door leaf"""
    X = Model()
    W = X.mesh(S('trim_white', 'lm')); Dk = X.mesh(S('porch_boards', 'lm', steps='woodsteps')); Dr = X.mesh(S('door_teal', 'lm'))
    G = X.mesh(S('gold', 'lms'))
    x0, y0, x1, y1 = L.PORCH
    o = np.array([0, y0, L.FL[0]])
    zf, zr = L.FL[0], L.FL[1] - L.SLAB
    # deck boards over the board top (2u)
    rbox(Dk, np.array([x0, y0, zf]) - o, np.array([x1, y1, zf + 2]) - o, r=0.5, k=1, tile=96)
    for x in (x0 + 16, x1 - 16):
        for y in (y1 - 16,):
            prof = [(0, zf + 2), (12, zf + 2), (12, zf + 14), (8, zf + 20), (8, zf + 80), (11, zf + 100), (7, zf + 120), (7, zr - 40), (10, zr - 30), (12, zr)]
            revolve(W, [(r, z - o[2]) for (r, z) in prof], n=12, cx=x, cy=y - o[1])
    # beam + fascia under the balcony slab
    rbox(W, np.array([x0, y1 - 24, zr - 24]) - o, np.array([x1, y1, zr]) - o, r=2, k=2, tile=64)
    rbox(W, np.array([x0, y0, zr - 24]) - o, np.array([x0 + 24, y1, zr]) - o, r=2, k=2, tile=64)
    rbox(W, np.array([x1 - 24, y0, zr - 24]) - o, np.array([x1, y1, zr]) - o, r=2, k=2, tile=64)
    rbox(W, np.array([x0 - 4, y0, zr]) - o, np.array([x1 + 4, y1 + 4, zr + L.SLAB]) - o, r=2, k=2, tile=64, faces='nsewb')
    # spandrel: row of spindles under the beam
    for x in np.arange(x0 + 40, x1 - 30, 18):
        tube(W, [np.array([x, y1 - 12, zr - 60]) - o, np.array([x, y1 - 12, zr - 24]) - o], 2.5, nseg=6)
    rbox(W, np.array([x0 + 16, y1 - 16, zr - 66]) - o, np.array([x1 - 16, y1 - 8, zr - 60]) - o, r=1, k=1, tile=64)
    # balcony balustrade (3 sides, 40 high) on the porch roof
    zb = L.FL[1]
    for (a, b) in (((x0 + 4, y0 + 8), (x0 + 4, y1 - 4)), ((x0 + 4, y1 - 4), (x1 - 4, y1 - 4)), ((x1 - 4, y1 - 4), (x1 - 4, y0 + 8))):
        a = np.array([*a, 0.0]); b = np.array([*b, 0.0])
        rbox(W, np.minimum(a, b) + [-5, -5, zb + 34] - o, np.maximum(a, b) + [5, 5, zb + 42] - o, r=2, k=2, tile=64)
        rbox(W, np.minimum(a, b) + [-4, -4, zb] - o, np.maximum(a, b) + [4, 4, zb + 6] - o, r=1, k=1, tile=64)
        n = int(np.linalg.norm(b - a) / 16)
        for k in range(1, n):
            p = a + (b - a) * k / n
            revolve(W, [(0, zb + 6), (3, zb + 6), (5, zb + 14), (3, zb + 24), (4, zb + 30), (3, zb + 34), (0, zb + 34)], n=6, cx=p[0] - o[0], cy=p[1] - o[1])
    for (x, y) in ((x0 + 4, y1 - 4), (x1 - 4, y1 - 4)):
        rbox(W, np.array([x - 8, y - 8, zb]) - o, np.array([x + 8, y + 8, zb + 52]) - o, r=2, k=2, tile=64)
        G.add(_ball(7), t=np.array([x, y, zb + 58]) - o)
    # front door: open leaf swung inwards against the hall side of the wall (hinge at x -80), with panels and a knob
    fx0, fx1 = L.FRONT_DOOR
    yd = L.DY1 - L.WT
    lw = (fx1 - fx0) / 2
    for (hx, sg) in ((fx0, 1), (fx1, -1)):
        a = np.array([hx + sg * 2, yd - lw, zf]); b = np.array([hx + sg * 8, yd - 2, zf + L.DOOR_H - 4])
        rbox(Dr, np.minimum(a, b) - o, np.maximum(a, b) - o, r=1.5, k=2, tile=96)
        for (zz0, zz1) in ((zf + 24, zf + 96), (zf + 116, zf + 190)):
            a = np.array([hx + sg * 8, yd - lw + 10, zz0]); b = np.array([hx + sg * 10, yd - 12, zz1])
            rbox(W, np.minimum(a, b) - o, np.maximum(a, b) - o, r=0.5, k=1, tile=96)
        G.add(_ball(5), t=np.array([hx + sg * 13, yd - lw + 12, zf + 104]) - o)
    # transom fan light over the door (outside)
    pts = [np.array([math.cos(a) * 88, L.DY1 + 3, zf + L.DOOR_H + 2 + math.sin(a) * 40]) - o for a in np.linspace(0, math.pi, 17)]
    tube(W, pts, 5, nseg=8)
    return X, o


def _ball(r, n=10):
    m = Mesh(); sphere(m, (0, 0, 0), r, nu=n, nv=max(4, n // 2)); return m


def balcony_rail_boxes():
    """collision boxes (mn, mx) for the balcony balustrade"""
    x0, y0, x1, y1 = L.PORCH
    zb = L.FL[1]
    return [((x0, y0 + 4, zb), (x0 + 8, y1, zb + 42)), ((x0 + 8, y1 - 8, zb), (x1 - 8, y1, zb + 42)), ((x1 - 8, y0 + 4, zb), (x1, y1, zb + 42))]


def make_textures():
    def siding(w=256, h=256, seed=1, col=(240, 168, 190)):
        x, y = xy(w, h)
        b = (y * 8) % 1.0
        c = np.zeros((h, w, 3), np.float32) + C(col) * (0.86 + 0.18 * b)[..., None]
        c = np.where((b > 0.94)[..., None], C(col) * 0.62, c)
        gr = np.asarray(img(noise(w, 1, seed, h) * 40 + 128).resize((w // 16, h)).resize((w, h)), np.float32) - 128
        return c + gr[..., None] * 0.12 + N3(w, 1, seed + 3, 3, h)

    def scales(n=256, seed=3, col=(176, 160, 214), rows=8, cols=6):
        x, y = xy(n)
        r = np.floor(y * rows)
        off = (r % 2) * 0.5 / cols
        u = ((x + off) * cols) % 1.0
        v = (y * rows) % 1.0
        edge = np.hypot(u - 0.5, v * 1.1) > 0.56
        tone = np.random.default_rng(seed).uniform(-12, 12, (rows + 1, cols + 1))[r.astype(int) % (rows + 1), np.floor((x + off) * cols).astype(int) % (cols + 1)]
        c = np.zeros((n, n, 3), np.float32) + C(col) + tone[..., None]
        c *= (0.72 + 0.28 * (1 - v))[..., None]
        return np.where(edge[..., None], c * 0.6, c) + N3(n, 1, seed + 2, 4)

    save_img(out(MD, 'siding_pink'), siding())
    save_img(out(MD, 'trim_white'), fill(64, (250, 248, 244), 3, 31))
    save_img(out(MD, 'trim_dark'), fill(64, (60, 50, 60), 3, 32))
    save_img(out(MD, 'shutter_mint'), siding(128, 128, 33, (150, 210, 186)))
    save_img(out(MD, 'shingle_lilac'), scales())
    save_img(out(MD, 'scale_pink'), scales(256, 5, (236, 150, 176), 10, 8))
    save_img(out(MD, 'door_teal'), fill(64, (60, 150, 150), 4, 34))
    save_img(out(MD, 'porch_boards'), np.asarray(img(fill(128, (236, 232, 222), 3, 35)), np.float32) * np.where((xy(128)[1] * 8 % 1.0 < 0.06)[..., None], 0.8, 1.0))
    save_img(out(MD, 'pennant'), fill(64, (230, 70, 120), 3, 36))
    save_img(out(MD, 'flower_red'), fill(32, (230, 60, 90), 6, 37)); save_img(out(MD, 'flower_yellow'), fill(32, (250, 220, 70), 6, 38))
    save_img(out(MD, 'gold'), fill(64, (220, 180, 80), 8, 39))


def make_models():
    """returns {name: (path, scale, zoff, origin)} for the house pieces"""
    out_ = {}
    X = house_facade(); p = save('house_facade', X); out_['house_facade'] = (*p, (0, (L.DY0 + L.DY1) / 2, 0))
    for i, g in enumerate(L.GABLES):
        X, o = roof_model(g); p = save(f'roof_{i}', X); out_[f'roof_{i}'] = (*p, tuple(o))
        X, o = gable_wall_model(g); p = save(f'gable_{i}', X); out_[f'gable_{i}'] = (*p, tuple(o))
    X, o = tower_model(); p = save('tower', X); out_['tower'] = (*p, tuple(o))
    X = flag_model(); p = save('flag', X); out_['flag'] = (*p, (0, 0, 0))
    X, o = porch_model(); p = save('porch', X); out_['porch'] = (*p, tuple(o))
    return out_
