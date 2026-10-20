"""Buildings of Pumpkin Hollow: wall specs shared by the brush collision (build_halloween.py) and the MD3 facades.

A Wall is an axis-aligned slab with rectangular openings. Collision = the slab minus the openings (sub_rects in the
wall's (u, z) plane); the MD3 facade = siding quads on the outer face over the same pieces plus trims, window
frames, shutters, corner boards. Interiors are brushes (wallpaper, floorboards) so they light well.

  manor      Blackwood Manor: two floors + mansard roof deck + cupola, porch with a balcony on its roof
  maus       the mausoleum over the crypt stair
  cottage    the witch's cottage (half-timbered, crooked)
  hut        the treehouse hut
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, tube, rbox, sphere, ellipsoid, disc, prism, rot_z, rot_axis
from wopmap import sub_rects
from hwlib import *
import layout as L


class Hole:
    def __init__(self, u0, u1, z0, z1, kind='win', glass=True, shutters=True):
        self.u0, self.u1, self.z0, self.z1, self.kind, self.glass, self.shutters = u0, u1, z0, z1, kind, glass, shutters


class Wall:
    """axis 'x': runs along x (a south/north wall, outer face at y = fixed); axis 'y': runs along y (outer face x = fixed).
    out = +1/-1: outward direction along the other axis. u0..u1 collision run, vu visual run (corners), z0..z1.
    interior walls: out=0, fixed = the low face (occupies fixed..fixed+thick), both faces are 'in'."""
    def __init__(self, axis, fixed, out, u0, u1, z0, z1, holes=(), thick=16, vu=None, skip=(), name=''):
        self.axis, self.fixed, self.out, self.u0, self.u1, self.z0, self.z1 = axis, fixed, out, u0, u1, z0, z1
        self.holes = list(holes); self.thick = thick; self.vu = vu or (u0, u1); self.skip = list(skip); self.name = name

    def span(self):
        """(p0, p1) along the perpendicular axis"""
        if self.out > 0: return self.fixed - self.thick, self.fixed
        if self.out < 0: return self.fixed, self.fixed + self.thick
        return self.fixed, self.fixed + self.thick

    def pieces(self):
        """collision boxes (mn, mx) of the wall minus its openings"""
        p0, p1 = self.span()
        rects = sub_rects((self.u0, self.z0, self.u1, self.z1), [(h.u0, h.z0, h.u1, h.z1) for h in self.holes])
        out_ = []
        for (ua, za, ub, zb) in rects:
            if self.axis == 'x': out_.append(((ua, p0, za), (ub, p1, zb)))
            else: out_.append(((p0, ua, za), (p1, ub, zb)))
        return out_

    def face_kind(self, n):
        """'out' / 'in' / 'jamb' / 'top' / 'bot' for a brush face normal of one of the pieces"""
        perp = n[1] if self.axis == 'x' else n[0]
        if abs(perp) > 0.9:
            if self.out == 0: return 'in'
            return 'out' if perp * self.out > 0 else 'in'
        if n[2] > 0.9: return 'top'
        if n[2] < -0.9: return 'bot'
        return 'jamb'

    def P(self, u, z, off=0.0):
        """world point on the outer face plane (pushed out by off) at run coordinate u, height z"""
        f = self.fixed + self.out * off
        return np.array([u, f, z], float) if self.axis == 'x' else np.array([f, u, z], float)

    def normal(self):
        return np.array([0, self.out, 0.0]) if self.axis == 'x' else np.array([self.out, 0, 0.0])


# ================================================================================================= facade MD3 builder
def facade(X, w, st, origin, tile=128.0, base_h=24, frieze=24):
    """siding + trims for wall w into model X (coordinates relative to origin). st: dict of shader names
    siding, trim, frame, shutter, base, sill"""
    o = np.asarray(origin, float)
    nrm = w.normal()
    vu0, vu1 = w.vu
    holes = [(h.u0, h.z0, h.u1, h.z1) for h in w.holes] + [tuple(s) for s in w.skip]
    rects = sub_rects((vu0, w.z0 + base_h, vu1, w.z1 - frieze), [(a, max(b, w.z0 + base_h), c, min(d, w.z1 - frieze)) for (a, b, c, d) in holes
                                                                  if d > w.z0 + base_h and b < w.z1 - frieze])
    M = X.mesh(st['siding'])
    sg = 1 if (w.axis == 'x' and w.out < 0) or (w.axis == 'y' and w.out > 0) else -1   # u direction as seen from outside
    for (ua, za, ub, zb) in rects:
        p = [w.P(ua, za, 1.0) - o, w.P(ub, za, 1.0) - o, w.P(ub, zb, 1.0) - o, w.P(ua, zb, 1.0) - o]
        M.poly(p, nrm, [(sg * ua / tile, -za / tile), (sg * ub / tile, -za / tile), (sg * ub / tile, -zb / tile), (sg * ua / tile, -zb / tile)])
    # base band (stone) and frieze (trim), split round door openings and skips
    def band(z0, z1, sh, protrude, skip_doors):
        cuts = [(h.u0, h.u1) for h in w.holes if (h.kind == 'door' or not skip_doors) and h.z0 < z1 and h.z1 > z0]
        cuts += [(s[0], s[2]) for s in w.skip if s[1] < z1 and s[3] > z0]
        spans = sub_rects((vu0, 0, vu1, 1), [(a, 0, b, 1) for (a, b) in cuts])
        for (ua, _, ub, _) in spans:
            if ub - ua < 2: continue
            a = w.P(ua, z0, 0) - o; b = w.P(ub, z1, protrude) - o
            rbox(X.mesh(sh), np.minimum(a, b), np.maximum(a, b), r=1.0, k=1, tile=64)
    if base_h: band(w.z0, w.z0 + base_h, st['base'], 3, True)
    if frieze: band(w.z1 - frieze, w.z1, st['trim'], 4, False)
    # openings: frames, sills, headers, shutters
    for h in w.holes:
        fw = 9
        fr = st['frame']
        def strip(ua, za, ub, zb, prot, sh=fr):
            a = w.P(ua, za, 0.5) - o; b = w.P(ub, zb, prot) - o
            rbox(X.mesh(sh), np.minimum(a, b), np.maximum(a, b), r=0.8, k=1, tile=64)
        if h.kind != 'open':
            strip(h.u0 - fw, h.z0, h.u0, h.z1 + fw, 4)
            strip(h.u1, h.z0, h.u1 + fw, h.z1 + fw, 4)
            strip(h.u0 - fw, h.z1, h.u1 + fw, h.z1 + fw, 4)
            strip(h.u0 - fw - 6, h.z1 + fw, h.u1 + fw + 6, h.z1 + fw + 8, 8, st['trim'])      # header cap
            if h.kind == 'win':
                strip(h.u0 - fw - 4, h.z0 - 8, h.u1 + fw + 4, h.z0, 9, st['trim'])           # sill
                if h.shutters and 'shutter' in st:
                    sw = (h.u1 - h.u0) / 2
                    for (ua, ub, crooked) in ((h.u0 - fw - sw - 2, h.u0 - fw - 2, 1), (h.u1 + fw + 2, h.u1 + fw + sw + 2, -1)):
                        a = w.P(ua, h.z0 + 4, 1.0) - o; b = w.P(ub, h.z1 - 2, 3.5) - o
                        m = Mesh(); rbox(m, np.minimum(a, b), np.maximum(a, b), r=0.5, k=1, tile=64)
                        if (int(h.u0) // 7) % 3 == 0 and crooked > 0:          # one shutter hangs askew
                            c = w.P(ub, h.z1 - 2, 2) - o
                            Rm = rot_axis(nrm, math.radians(9) * sg)
                            m.V = [Rm @ (v - c) + c for v in m.V]; m.N = [Rm @ nn for nn in m.N]
                        X.mesh(st['shutter']).add(m)
    return X


def corner_post(X, sh, x, y, z0, z1, o, s=10):
    o = np.asarray(o, float)
    rbox(X.mesh(sh), np.array([x - s, y - s, z0]) - o, np.array([x + s, y + s, z1]) - o, r=1.5, k=2, tile=64)


# ================================================================================================= the manor
MX0, MY0, MX1, MY1 = L.MAN
F0, F1, C1, EAVE = L.MAN_F0, L.MAN_F1, L.MAN_C1, L.MAN_EAVE
WT = L.WALL
MCX, MCY = (MX0 + MX1) / 2, (MY0 + MY1) / 2
STAIR_E = dict(x0=MX1 - WT - 96, x1=MX1 - WT, y0=MY0 + WT + 16, n=14, run=28)     # east-room staircase (rises north)
WINS_G = [(-400, -304), (-256, -160), (160, 256), (304, 400)]


def stair_e_hole():
    s = STAIR_E
    # the steps are shallower than the player box (28 < 30), so a standing player always overlaps the next step up;
    # open the slab two steps before the headroom rule would
    k0 = next(k for k in range(s['n']) if F0 + 16 * (k + 2) + 56 > F1 - 16) - 1
    return (s['x0'], s['y0'] + s['run'] * k0, s['x1'], s['y0'] + s['run'] * s['n'])


def manor_walls():
    g = L.WIN_G; u = L.WIN_U
    S_ = Wall('x', MY0, -1, MX0, MX1, 0, EAVE, name='south',
              holes=[Hole(-64, 64, F0, F0 + 160, 'door')] + [Hole(a, b, g[0], g[1]) for (a, b) in WINS_G] +
                    [Hole(-56, 56, F1, F1 + 128, 'door')] + [Hole(a, b, u[0], u[1]) for (a, b) in WINS_G],
              skip=[(L.PORCH[0] - 16, F1 - 16, L.PORCH[2] + 16, F1), (L.PORCH[0], 0, L.PORCH[2], F0)])
    N_ = Wall('x', MY1, 1, MX0, MX1, 0, EAVE, name='north',
              holes=[Hole(-48, 48, F0, F0 + 144, 'door')] + [Hole(a, b, g[0], g[1]) for (a, b) in ((-352, -256), (256, 352))] +
                    [Hole(a, b, u[0], u[1]) for (a, b) in ((-352, -256), (-48, 48), (256, 352))])
    wins = [(1440, 1568)]
    W_ = Wall('y', MX0, -1, MY0 + WT, MY1 - WT, 0, EAVE, vu=(MY0, MY1), name='west',
              holes=[Hole(a, b, g[0], g[1]) for (a, b) in wins] + [Hole(a, b, u[0], u[1]) for (a, b) in wins])
    E_ = Wall('y', MX1, 1, MY0 + WT, MY1 - WT, 0, EAVE, vu=(MY0, MY1), name='east',
              holes=[Hole(a, b, u[0], u[1]) for (a, b) in wins] + [Hole(1360, 1440, g[0], g[1])])
    return [S_, N_, W_, E_]


def manor_inner_walls():
    hx = L.HALL_X
    out_ = []
    for (x, nm) in ((-hx - 8, 'w'), (hx - 8, 'e')):
        out_.append(Wall('y', x, 0, MY0 + WT, MY1 - WT, F0, F1 - 16, [Hole(1360, 1456, F0, F0 + 136, 'door')], name='g' + nm))
        dh = (1360, 1456) if nm == 'w' else (1560, 1656)
        out_.append(Wall('y', x, 0, MY0 + WT, MY1 - WT, F1, C1, [Hole(dh[0], dh[1], F1, F1 + 136, 'door')], name='u' + nm))
    return out_


def manor_models():
    o = (MCX, MCY, 0)
    st = dict(siding=S('siding', 'lm'), trim=S('trim', 'lm'), frame=S('trim_dark', 'lm'), shutter=S('shutter', 'lm'),
              base=S('textures/padhalloween/stone_dark', 'lm', tag='mb'))
    X = Model()
    for w in manor_walls(): facade(X, w, st, o)
    for (x, y) in ((MX0, MY0), (MX1, MY0), (MX0, MY1), (MX1, MY1)):
        corner_post(X, st['trim'], x, y, 0, EAVE, o, 12)
    # belt course between the floors (outside), skipping the porch roof
    for w in manor_walls():
        spans = [(w.vu[0], w.vu[1])]
        if w.name == 'south': spans = [(w.vu[0], L.PORCH[0] - 16), (L.PORCH[2] + 16, w.vu[1])]
        for (ua, ub) in spans:
            a = w.P(ua, F1 - 16, 0) - o; b = w.P(ub, F1, 5) - o
            rbox(X.mesh(st['trim']), np.minimum(a, b), np.maximum(a, b), r=1, k=1, tile=64)
    # eave brackets under the cornice
    for w in manor_walls():
        n = int((w.vu[1] - w.vu[0]) / 96)
        for k in range(n + 1):
            uu = w.vu[0] + 24 + (w.vu[1] - w.vu[0] - 48) * k / max(1, n)
            a = w.P(uu - 6, EAVE - 44, 0) - o; b = w.P(uu + 6, EAVE - 4, 14) - o
            rbox(X.mesh(st['trim']), np.minimum(a, b), np.maximum(a, b), r=2, k=2, tile=64)
    save('manor_shell', X)
    manor_roof(); manor_porch(); cupola(); chimney()


def manor_roof():
    """mansard: slate slopes from the eave rectangle (overhang) at EAVE up to the deck at MAN_DECK, cornice at the eave,
    dormers, iron cresting round the deck"""
    X = Model()
    o = np.array([MCX, MCY, 0.0])
    sl = S('slate', 'lm'); tr = S('trim', 'lm', tag='r'); ir = S('iron', 'lms', v=0.12, tag='r'); gl = S('win_glow', 'flicker', ph=0.2)
    ov, inn, D = L.MAN_OVER, L.MAN_IN, L.MAN_DECK
    E = [(MX0 - ov, MY0 - ov), (MX1 + ov, MY0 - ov), (MX1 + ov, MY1 + ov), (MX0 - ov, MY1 + ov)]
    Tp = [(MX0 + inn, MY0 + inn), (MX1 - inn, MY0 + inn), (MX1 - inn, MY1 - inn), (MX0 + inn, MY1 - inn)]
    for k in range(4):
        a, b = np.array([*E[k], EAVE + 1.0]), np.array([*E[(k + 1) % 4], EAVE + 1.0])
        c, d = np.array([*Tp[(k + 1) % 4], D + 0.5]), np.array([*Tp[k], D + 0.5])
        # push the slope 1u outward so it sits on the brush face
        n = np.cross(b - a, d - a); n /= np.linalg.norm(n)
        if n @ (np.array([*(np.array(E[k]) + np.array(E[(k + 1) % 4])) / 2, 0]) - np.array([MCX, MCY, 0])) < 0: n = -n
        P = [p + n * 1.0 - o for p in (a, b, c, d)]
        Ln = np.linalg.norm(b - a); H = np.linalg.norm(d - a)
        X.mesh(sl).poly(P, n, [(0, H / 128), (Ln / 128, H / 128), (Ln / 128 - 0.0, 0), (0, 0)])
    # cornice band under the eave, against the wall tops (outside the walls, under the roof brush)
    rb = lambda mn, mx, sh: rbox(X.mesh(sh), np.array(mn) - o, np.array(mx) - o, r=1.5, k=1, tile=64)
    zc0, zc1 = EAVE - 28, EAVE - 1
    rb((MX0 - 22, MY0 - 22, zc0), (MX1 + 22, MY0 - 1, zc1), tr)
    rb((MX0 - 22, MY1 + 1, zc0), (MX1 + 22, MY1 + 22, zc1), tr)
    rb((MX0 - 22, MY0 - 1, zc0), (MX0 - 1, MY1 + 1, zc1), tr)
    rb((MX1 + 1, MY0 - 1, zc0), (MX1 + 22, MY1 + 1, zc1), tr)
    # dormers: on the steep slope, front face vertical
    def slope_at(z):
        """horizontal distance of the slope surface from the eave line at height z"""
        return (inn + ov) * (z - EAVE) / (D - EAVE)
    def dormer(u, side):
        """a dormer standing out of the steep slope: vertical front with a glowing window, cheeks back to the slope,
        a little gable roof; nothing goes inside the roof brush"""
        zb, zt, zr = EAVE + 30, EAVE + 112, EAVE + 140
        hw = 40
        # local frame: e_u along the side, e_n outward normal (horizontal), base point on the eave line
        if side == 's': base, eu, en = np.array([0, MY0 - ov, 0.0]), np.array([1.0, 0, 0]), np.array([0, -1.0, 0])
        elif side == 'n': base, eu, en = np.array([0, MY1 + ov, 0.0]), np.array([-1.0, 0, 0]), np.array([0, 1.0, 0])
        elif side == 'w': base, eu, en = np.array([MX0 - ov, 0, 0.0]), np.array([0, -1.0, 0]), np.array([-1.0, 0, 0])
        else: base, eu, en = np.array([MX1 + ov, 0, 0.0]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0])
        def Q(uu, d, z):
            """point at run offset uu from the dormer centre, depth d inward from the eave line, height z"""
            p = np.array([u, base[1], z]) if side in 'sn' else np.array([base[0], u, z])
            return p + eu * uu - en * d
        front = slope_at(zb) - 18                                      # front face stands proud of the slope
        def back(z): return slope_at(z) + 0.5
        # front face (glowing window framed by trim)
        fq = [Q(-hw, front, zb), Q(hw, front, zb), Q(hw, front, zt), Q(-hw, front, zt)]
        X.mesh(tr).poly([p - o for p in fq], en, [(0, 1), (1, 1), (1, 0), (0, 0)])
        X.mesh(gl).poly([p - o + en * 0.6 for p in (Q(-26, front, zb + 14), Q(26, front, zb + 14), Q(26, front, zt - 18), Q(-26, front, zt - 18))],
                        en, [(0, 1), (1, 1), (1, 0), (0, 0)])
        # cheeks from the front edge back to the slope
        for sg in (-1, 1):
            cq = [Q(sg * hw, front, zb), Q(sg * hw, back(zb), zb), Q(sg * hw, back(zt), zt), Q(sg * hw, front, zt)]
            X.mesh(tr).poly([p - o for p in cq], eu * sg, [(0, 1), (1, 1), (1, 0), (0, 0)])
        # gable roof: two slopes from the ridge (u = 0, zr) to the eaves (u = +-hw-8, zt - 4), running back to the slope
        for sg in (-1, 1):
            a_ = Q(sg * (hw + 8), front - 6, zt - 4); b_ = Q(0, front - 6, zr); c_ = Q(0, back(zr), zr); d_ = Q(sg * (hw + 8), back(zt - 4), zt - 4)
            nn = np.cross(b_ - a_, d_ - a_); nn /= np.linalg.norm(nn)
            if nn[2] < 0: nn = -nn
            X.mesh(sl).poly([p - o for p in (a_, b_, c_, d_)], nn, [(0, 1), (0.6, 1), (0.6, 0), (0, 0)])
        X.mesh(tr).poly([p - o + en * 0.5 for p in (Q(-hw - 4, front - 0.5, zt - 2), Q(hw + 4, front - 0.5, zt - 2), Q(0, front - 0.5, zr - 2))], en,
                        [(0, 1), (1, 1), (0.5, 0)])
    for uu in (-352, -176, 176, 352): dormer(uu, 's'); dormer(uu, 'n')
    for uu in (MCY - 100, MCY + 100): dormer(uu, 'w'); dormer(uu, 'e')
    # iron cresting round the deck edge (spikes) - low, nothing to hide behind
    pts = [(*Tp[k], D) for k in range(4)] + [(*Tp[0], D)]
    for k in range(4):
        a, b = np.array(pts[k], float), np.array(pts[k + 1], float)
        tube(X.mesh(ir), [a + [0, 0, 26] - o, b + [0, 0, 26] - o], 1.8, nseg=4)
        tube(X.mesh(ir), [a + [0, 0, 6] - o, b + [0, 0, 6] - o], 1.8, nseg=4)
        n = int(np.linalg.norm(b - a) / 20)
        for i in range(n):
            p = a + (b - a) * i / n
            tube(X.mesh(ir), [p - o, p + [0, 0, 34] - o], 1.0, nseg=3, caps=(False, False))
            sphere(X.mesh(ir), p + [0, 0, 36] - o, 2.2, 5, 4) if i % 4 == 0 else None
    save('manor_roof', X)


def manor_porch():
    """porch posts, railings and spandrels; balcony railing on the porch roof; fascia (origin = manor centre)"""
    X = Model()
    o = np.array([MCX, MCY, 0.0])
    tr = S('trim', 'lm', tag='p'); dk = S('trim_dark', 'lm', tag='p')
    px0, py0, px1, py1 = L.PORCH
    posts = [-376, -176, 176, 376]
    for x in posts:
        p = np.array([x, py0 + 8, 0.0])
        lathe_post(X.mesh(tr), p - o, F0, F1 - 16)
    # fascia board round the porch roof slab
    for (a, b) in (((px0 - 16, py0 - 16), (px1 + 16, py0 - 16)), ((px0 - 16, py0 - 16), (px0 - 16, py1)), ((px1 + 16, py0 - 16), (px1 + 16, py1))):
        mn = np.array([min(a[0], b[0]) - 2, min(a[1], b[1]) - 2, F1 - 18]); mx = np.array([max(a[0], b[0]) + 2, max(a[1], b[1]) + 2, F1 + 2])
        rbox(X.mesh(tr), mn - o, mx - o, r=1, k=1, tile=64)
    # spandrels (a scalloped beam) between posts
    for (a, b) in zip(posts, posts[1:]):
        for k in range(8):
            u0 = a + 10 + (b - a - 20) * k / 8; u1 = a + 10 + (b - a - 20) * (k + 1) / 8
            for (uu0, uu1, dz) in ((u0, u1, 0),):
                arc = [(u0 + (u1 - u0) * t, py0 + 8, F1 - 30 - 10 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 6)]
                tube(X.mesh(dk), [np.array(p) - o for p in arc], 1.6, nseg=4, caps=(False, False))
        tube(X.mesh(tr), [np.array([a, py0 + 8, F1 - 24]) - o, np.array([b, py0 + 8, F1 - 24]) - o], 3, nseg=5)
    # porch railing (front, both sides of the steps, and the sides)
    runs = [[(px0 + 8, py0 + 8), (-176, py0 + 8)], [(176, py0 + 8), (px1 - 8, py0 + 8)],
            [(px0 + 8, py0 + 8), (px0 + 8, py1 - 4)], [(px1 - 8, py0 + 8), (px1 - 8, py1 - 4)]]
    for run in runs: balustrade(X, dk, tr, run, F0, 44, o)
    # balcony railing on the porch roof
    runs = [[(px0 - 8, py0 - 8), (px1 + 8, py0 - 8)], [(px0 - 8, py0 - 8), (px0 - 8, py1 - 4)], [(px1 + 8, py0 - 8), (px1 + 8, py1 - 4)]]
    for run in runs: balustrade(X, dk, tr, run, F1, 36, o)
    save('manor_porch', X)


def lathe_post(M, p, z0, z1):
    from hw_models import lathe
    m = Mesh()
    rows = [(9, z0), (9, z0 + 20), (6, z0 + 26), (6, z1 - 40), (8, z1 - 30), (5, z1 - 24), (8, z1 - 8), (10, z1)]
    lathe(m, rows, 10)
    M.add(m, np.eye(3), (p[0], p[1], 0))


def balustrade(X, posts_sh, rail_sh, run, z, h, o):
    a = np.array([*run[0], z], float); b = np.array([*run[1], z], float)
    tube(X.mesh(rail_sh), [a + [0, 0, h] - o, b + [0, 0, h] - o], 3, nseg=5)
    tube(X.mesh(rail_sh), [a + [0, 0, 4] - o, b + [0, 0, 4] - o], 2.5, nseg=5)
    n = max(1, int(np.linalg.norm(b - a) / 12))
    for k in range(n + 1):
        p = a + (b - a) * k / n
        tube(X.mesh(posts_sh), [p + [0, 0, 5] - o, p + [0, 0, h] - o], 1.4, nseg=4, caps=(False, False))


def cupola():
    """open belvedere on the roof deck: plinth trim, 4 turned posts, railings, onion dome with a finial
    (origin = cupola centre at the deck height)"""
    X = Model()
    tr = S('trim', 'lm', tag='c'); sl = S('slate', 'lm', tag='c'); ir = S('iron', 'lms', v=0.12, tag='c'); dk = S('trim_dark', 'lm', tag='c')
    x0, y0, x1, y1 = L.CUPOLA
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    o = np.array([cx, cy, L.MAN_DECK], float)
    Z, T = L.CUPOLA_Z, L.CUPOLA_TOP
    hw = (x1 - x0) / 2
    # plinth cladding (the plinth is a brush): skirting board on each side
    for (mn, mx) in (((x0 - 2, y0 - 2, L.MAN_DECK), (x1 + 2, y0 + 2, Z)), ((x0 - 2, y1 - 2, L.MAN_DECK), (x1 + 2, y1 + 2, Z)),
                     ((x0 - 2, y0 + 2, L.MAN_DECK), (x0 + 2, y1 - 2, Z)), ((x1 - 2, y0 + 2, L.MAN_DECK), (x1 + 2, y1 - 2, Z))):
        rbox(X.mesh(tr), np.array(mn) - o, np.array(mx) - o, r=0.6, k=1, tile=64)
    for (px, py) in ((x0 + 8, y0 + 8), (x1 - 8, y0 + 8), (x1 - 8, y1 - 8), (x0 + 8, y1 - 8)):
        lathe_post(X.mesh(tr), np.array([px, py, 0]) - [o[0], o[1], 0], Z - o[2], T - o[2])
    # railings between the posts (open at the south for the stair)
    for (a, b) in (((x0 + 8, y1 - 8), (x1 - 8, y1 - 8)), ((x0 + 8, y0 + 8), (x0 + 8, y1 - 8)), ((x1 - 8, y0 + 8), (x1 - 8, y1 - 8)),
                   ((x0 + 8, y0 + 8), (cx - 56, y0 + 8)), ((cx + 56, y0 + 8), (x1 - 8, y0 + 8))):
        balustrade(X, dk, tr, [a, b], Z, 30, o)
    # roof slab cladding + onion dome
    rbox(X.mesh(tr), np.array([x0 - 16, y0 - 16, T]) - o, np.array([x1 + 16, y1 + 16, T + 16]) - o, r=2, k=1, tile=64)
    from hw_models import lathe
    R0 = hw + 8
    rows = [(R0, T + 16), (R0 * 1.08, T + 50), (R0 * 1.02, T + 90), (R0 * 0.75, T + 140), (R0 * 0.4, T + 180), (R0 * 0.16, T + 210),
            (6, T + 240), (2, T + 250)]
    m = Mesh(); lathe(m, rows, 32, u_tiles=8, vlen=128)
    X.mesh(sl).add(m, np.eye(3), (cx - o[0], cy - o[1], -o[2]))
    tube(X.mesh(ir), [np.array([cx, cy, T + 244]) - o, np.array([cx, cy, T + 300]) - o], 2.5, nseg=6)
    sphere(X.mesh(ir), np.array([cx, cy, T + 270]) - o, 6, 8, 6)
    save('cupola', X)


CUPOLA_SPIRE = L.CUPOLA_TOP + 300


def chimney():
    """chimney cap + pots for the brick chimney brushes on the roof deck (origin = top centre of the brush stack)"""
    X = Model()
    st = S('stone_m', 'lm', tag='ch'); tc = S('copper', 'lm', tag='ch')
    rbox(X.mesh(st), (-38, -46, 0), (38, 46, 12), r=2, k=1, tile=64)
    from hw_models import lathe
    for dx in (-16, 16):
        m = Mesh(); lathe(m, [(12, 12), (11, 30), (9, 40), (11, 44), (10, 46)], 10)
        X.mesh(tc).add(m, np.eye(3), (dx, 0, 0))
    save('chimney_cap', X)


# ================================================================================================= mausoleum
MAX0, MAY0, MAX1, MAY1 = L.MAUS
MT = 24


def maus_walls():
    dx0, dx1 = L.MAUS_STAIR
    return [Wall('x', MAY0, -1, MAX0, MAX1, 0, L.MAUS_H, [Hole(dx0 + 16, dx1 - 16, L.MAUS_F, L.MAUS_F + 192, 'door')], thick=MT, name='s'),
            Wall('x', MAY1, 1, MAX0, MAX1, 0, L.MAUS_H, [Hole(-1632, -1568, 120, 200, 'win', shutters=False)], thick=MT, name='n'),
            Wall('y', MAX0, -1, MAY0 + MT, MAY1 - MT, 0, L.MAUS_H, [Hole(1500, 1560, 120, 220, 'win', shutters=False)], thick=MT, vu=(MAY0, MAY1), name='w'),
            Wall('y', MAX1, 1, MAY0 + MT, MAY1 - MT, 0, L.MAUS_H, [Hole(1500, 1560, 120, 220, 'win', shutters=False)], thick=MT, vu=(MAY0, MAY1), name='e')]


MAUS_RIDGE = L.MAUS_H + 112


def maus_models():
    X = Model()
    cx, cy = (MAX0 + MAX1) / 2, (MAY0 + MAY1) / 2
    o = (cx, cy, 0)
    st = dict(siding=S('textures/padhalloween/stone', 'lm', tag='ma'), trim=S('marble', 'lm', tag='ma'), frame=S('marble', 'lm', tag='maf'),
              base=S('mossstone', 'lm', tag='ma'))
    for w in maus_walls(): facade(X, w, st, o, tile=256, base_h=32, frieze=32)
    o = np.array(o, float)
    mb = S('marble', 'lm', tag='mac')
    # pilasters at the corners and either side of the door
    for (x, y) in ((MAX0, MAY0), (MAX1, MAY0), (MAX0, MAY1), (MAX1, MAY1)):
        rbox(X.mesh(mb), np.array([x - 18, y - 18, 0]) - o, np.array([x + 18, y + 18, L.MAUS_H]) - o, r=3, tile=96)
    dx0, dx1 = L.MAUS_STAIR
    from hw_models import lathe
    for x in (dx0 - 26, dx1 + 26, MAX0 + 60, MAX1 - 60):          # half columns on the front
        m = Mesh(); lathe(m, [(20, 32), (20, 44), (15, 50), (14, L.MAUS_H - 40), (18, L.MAUS_H - 30), (20, L.MAUS_H - 24)], 16,
                          deform=lambda a, r, z: r + 1.2 * math.cos(a * 16) * (40 < z < L.MAUS_H - 40))
        X.mesh(mb).add(m, np.eye(3), (x - o[0], MAY0 - 12 - o[1], 0))
    # pediment (front and back gables) + roof slabs (collision: the roof hull brush)
    tile = S('textures/padhalloween/stone_dark', 'lm', tag='mr')
    ov = 16
    for (y, sg) in ((MAY0 - ov, -1), (MAY1 + ov, 1)):
        a = np.array([MAX0 - ov, y, L.MAUS_H]); b = np.array([MAX1 + ov, y, L.MAUS_H]); c = np.array([cx, y, MAUS_RIDGE])
        X.mesh(mb).poly([p + [0, sg * 1.0, 0] - o for p in (a, b, c)],
                        (0, sg, 0), [(0, 1), (1, 1), (0.5, 0)])
        # raking cornices
        for (p, q) in ((a, c), (c, b)):
            tube(X.mesh(mb), [p + [0, sg * 4, 4] - o, q + [0, sg * 4, 4] - o], 6, nseg=6)
        tube(X.mesh(mb), [a + [0, sg * 4, 2] - o, b + [0, sg * 4, 2] - o], 6, nseg=6)
    for (x0, sx) in ((MAX0 - ov, -1), (MAX1 + ov, 1)):
        p0 = np.array([x0, MAY0 - ov, L.MAUS_H]); p1 = np.array([x0, MAY1 + ov, L.MAUS_H])
        p2 = np.array([cx, MAY1 + ov, MAUS_RIDGE]); p3 = np.array([cx, MAY0 - ov, MAUS_RIDGE])
        n = np.cross(p1 - p0, p3 - p0); n /= np.linalg.norm(n)
        if n[2] < 0: n = -n
        X.mesh(tile).poly([p + n * 1.0 - o for p in (p0, p1, p2, p3)], n, [(0, 2), (2, 2), (2, 0), (0, 0)])
    # urns on the front corners of the roof (sitting on the wall tops at the eave)
    # iron door leaves, folded open against the inside of the walls
    ir = S('iron', 'lms', v=0.12, tag='md')
    for (x, sg) in ((dx0 + 16, -1), (dx1 - 16, 1)):
        a = np.array([x + sg * 2, MAY0 + MT + 2, L.MAUS_F + 2]); b = np.array([x + sg * 58, MAY0 + MT + 6, L.MAUS_F + 190])
        rbox(X.mesh(ir), np.minimum(a, b) - o, np.maximum(a, b) - o, r=1, k=1, tile=64)
    save('mausoleum', X)


def crypt_vault():
    """ribbed vault decoration hanging under the crypt ceiling (arches springing from wall pilasters); origin = crypt
    centre at the ceiling height"""
    X = Model()
    x0, y0, x1, y1 = L.CRYPT
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    o = np.array([cx, cy, L.CRYPT_C])
    st = S('textures/padhalloween/stone_dark', 'lm', tag='cv')
    for x in np.arange(x0 + 128, x1 - 64, 192):
        arc = [(x, y0 + 18 + (y1 - y0 - 36) * t, L.CRYPT_C - 2 - 40 * (1 - math.sin(math.pi * t))) for t in np.linspace(0, 1, 13)]
        tube(X.mesh(st), [np.array(p) - o for p in arc], 9, nseg=6)
        for y in (y0 + 18, y1 - 18):
            rbox(X.mesh(st), np.array([x - 14, y - 6 if y < cy else y - 8, L.CRYPT_F]) - o, np.array([x + 14, y + 8 if y < cy else y + 6, L.CRYPT_C - 40]) - o, r=2, k=1, tile=96)
    save('crypt_vault', X)


# ================================================================================================= the witch's cottage
CX0, CY0, CX1, CY1 = L.COT
CT = 16


def cottage_walls():
    f = L.COT_F
    return [Wall('x', CY0, -1, CX0, CX1, 0, L.COT_EAVE, [Hole(-1712, -1632, 64, 144), Hole(-1440, -1360, 64, 144)], thick=CT, name='s'),
            Wall('x', CY1, 1, CX0, CX1, 0, L.COT_EAVE, [Hole(-1600, -1520, 64, 144)], thick=CT, name='n'),
            Wall('y', CX0, -1, CY0 + CT, CY1 - CT, 0, L.COT_EAVE, [Hole(-1272, -1208, 80, 144, shutters=False)], thick=CT, vu=(CY0, CY1), name='w'),
            Wall('y', CX1, 1, CY0 + CT, CY1 - CT, 0, L.COT_EAVE, [Hole(-1280, -1184, f, f + 144, 'door'), Hole(-1376, -1320, 64, 136)],
                 thick=CT, vu=(CY0, CY1), name='e')]


COT_OV = 32
COT_RIDGE_HW = 48


def cottage_models():
    X = Model()
    cx, cy = (CX0 + CX1) / 2, (CY0 + CY1) / 2
    o = np.array([cx, cy, 0.0])
    st = dict(siding=S('plaster_c', 'lm'), trim=S('beam', 'lm'), frame=S('beam', 'lm', tag='f'), shutter=S('shutter', 'lm', tag='c'),
              base=S('mossstone', 'lm', tag='c'))
    for w in cottage_walls(): facade(X, w, st, o, tile=128, base_h=32, frieze=16)
    bm = st['trim']
    # half-timbering: posts and braces on the outside
    for w in cottage_walls():
        n = int((w.vu[1] - w.vu[0]) / 128)
        for k in range(n + 1):
            uu = w.vu[0] + (w.vu[1] - w.vu[0]) * k / max(1, n)
            if any(h.u0 - 12 < uu < h.u1 + 12 for h in w.holes): continue
            a = w.P(uu - 6, 32, 0.5) - o; b = w.P(uu + 6, L.COT_EAVE - 16, 3) - o
            rbox(X.mesh(bm), np.minimum(a, b), np.maximum(a, b), r=1, k=1, tile=64)
        for k in range(n):
            ua = w.vu[0] + (w.vu[1] - w.vu[0]) * k / max(1, n); ub = w.vu[0] + (w.vu[1] - w.vu[0]) * (k + 1) / max(1, n)
            if any(h.u0 - 12 < (ua + ub) / 2 + 30 and (ua + ub) / 2 - 30 < h.u1 + 12 for h in w.holes): continue
            p = w.P(ua + 6, 40, 2) - o; q = w.P(ub - 6, L.COT_EAVE - 24, 2) - o
            if k % 2: p, q = w.P(ub - 6, 40, 2) - o, w.P(ua + 6, L.COT_EAVE - 24, 2) - o
            tube(X.mesh(bm), [p, q], 4.5, nseg=4)
        a = w.P(w.vu[0], 120, 0.5) - o; b = w.P(w.vu[1], 132, 3) - o
        rbox(X.mesh(bm), np.minimum(a, b), np.maximum(a, b), r=1, k=1, tile=64)
    # sagging shingle roof (collision: the roof hull), gables in plaster with beams
    sh = S('shingle_moss', 'lm')
    E0, E1 = CY0 - COT_OV, CY1 + COT_OV
    Rz = L.COT_RIDGE
    rs0, rs1 = cy - COT_RIDGE_HW, cy + COT_RIDGE_HW
    xs = np.linspace(CX0 - COT_OV, CX1 + COT_OV, 9)
    for (ya, yb, sg) in ((E0, rs0, -1), (E1, rs1, 1)):
        P = np.zeros((2, len(xs), 3)); N = np.zeros_like(P); UV = np.zeros((2, len(xs), 2))
        for j, x in enumerate(xs):
            sag = -3 * math.sin(math.pi * (x - xs[0]) / (xs[-1] - xs[0]))
            P[0, j] = (x, ya, L.COT_EAVE + 1.5); P[1, j] = (x, yb, Rz + 1.5 + sag)
            UV[0, j] = (x / 128, abs(yb - ya) * 1.2 / 128); UV[1, j] = (x / 128, 0)
        n = np.array([0, sg * (Rz - L.COT_EAVE), abs(yb - ya)]); n /= np.linalg.norm(n)
        N[:] = n
        m = Mesh(); m.grid(P - o, N, UV); X.mesh(sh).add(m)
    P = np.zeros((2, len(xs), 3)); N = np.zeros_like(P); UV = np.zeros((2, len(xs), 2))
    for j, x in enumerate(xs):
        sag = -3 * math.sin(math.pi * (x - xs[0]) / (xs[-1] - xs[0]))
        P[0, j] = (x, rs0, Rz + 1.5 + sag); P[1, j] = (x, rs1, Rz + 1.5 + sag); UV[0, j] = (x / 128, 0.75); UV[1, j] = (x / 128, 0)
    N[:] = (0, 0, 1)
    m = Mesh(); m.grid(P - o, N, UV); X.mesh(sh).add(m)
    # ridge beam + gable triangles (plaster) with a crossed beam
    for (x, sx) in ((CX0 - COT_OV - 1, -1), (CX1 + COT_OV + 1, 1)):
        q = [np.array(p) - o for p in ((x, E0, L.COT_EAVE), (x, E1, L.COT_EAVE), (x, rs1, Rz), (x, rs0, Rz))]
        X.mesh(st['siding']).poly(q if sx > 0 else q, (sx, 0, 0), [(0, 1.3), (3.2, 1.3), (2.0, 0), (1.2, 0)])
        tube(X.mesh(bm), [np.array([x + sx * 6, E0 + 30, L.COT_EAVE + 8]) - o, np.array([x + sx * 6, rs1 - 10, Rz - 16]) - o], 5, nseg=4)
        tube(X.mesh(bm), [np.array([x + sx * 6, E1 - 30, L.COT_EAVE + 8]) - o, np.array([x + sx * 6, rs0 + 10, Rz - 16]) - o], 5, nseg=4)
        tube(X.mesh(bm), [np.array([x + sx * 7, E0 + 6, L.COT_EAVE + 7]) - o, np.array([x + sx * 7, E1 - 6, L.COT_EAVE + 7]) - o], 6, nseg=4)
    save('cottage', X)
    # crooked stone chimney on the west gable (collision: brush column x CHIM)
    Y = Model()
    stn = S('stone_m', 'lm', tag='chm')
    c0 = np.array([(CHIM[0] + CHIM[2]) / 2, (CHIM[1] + CHIM[3]) / 2, 0.0])
    hx, hy = (CHIM[2] - CHIM[0]) / 2, (CHIM[3] - CHIM[1]) / 2
    for k, (z0, z1, dx) in enumerate(((0, 120, 0), (120, 260, -3), (260, 380, -7), (380, CHIM_H, -12))):
        rbox(Y.mesh(stn), np.array([-hx - 3 + dx, -hy - 3, z0]), np.array([hx + 3 + dx, hy + 3, z1]), r=3, tile=96)
    rbox(Y.mesh(stn), np.array([-hx - 8 - 12, -hy - 8, CHIM_H]), np.array([hx + 8 - 12, hy + 8, CHIM_H + 12]), r=2, tile=96)
    save('cottage_chimney', Y)
    CHIM_O[:] = list(c0)


CHIM = (CX0 - COT_OV - 64, -1276, CX0 - COT_OV, -1188)
CHIM_H = 452
CHIM_O = [0, 0, 0]


# ================================================================================================= treehouse hut
def hut_rect():
    tx, ty = L.TREE
    x0, y0, x1, y1 = L.TH_HUT
    return (tx + x0, ty + y0, tx + x1, ty + y1)


HUT_T = 12


def hut_walls():
    x0, y0, x1, y1 = hut_rect()
    Z = L.PLAT_Z; H = Z + L.TH_HUT_H
    cy = (y0 + y1) / 2
    return [Wall('y', x0, -1, y0 + HUT_T, y1 - HUT_T, Z, H, [Hole(cy - 48, cy + 48, Z, Z + 128, 'door')], thick=HUT_T, vu=(y0, y1), name='w'),
            Wall('y', x1, 1, y0 + HUT_T, y1 - HUT_T, Z, H, [Hole(cy - 40, cy + 40, Z + 56, Z + 120)], thick=HUT_T, vu=(y0, y1), name='e'),
            Wall('x', y0, -1, x0, x1, Z, H, [Hole((x0 + x1) / 2 - 36, (x0 + x1) / 2 + 36, Z + 56, Z + 120, shutters=False)], thick=HUT_T, name='s'),
            Wall('x', y1, 1, x0, x1, Z, H, [Hole((x0 + x1) / 2 - 36, (x0 + x1) / 2 + 36, Z + 56, Z + 120, shutters=False)], thick=HUT_T, name='n')]


def hut_models():
    X = Model()
    x0, y0, x1, y1 = hut_rect()
    o = np.array([(x0 + x1) / 2, (y0 + y1) / 2, L.PLAT_Z])
    st = dict(siding=S('textures/padhalloween/planks_v', 'lm', tag='h'), trim=S('wood_dark', 'lm', tag='h'), frame=S('wood_dark', 'lm', tag='hf'),
              shutter=S('wood_grey', 'lm', tag='h'), base=S('wood_dark', 'lm', tag='hb'))
    for w in hut_walls(): facade(X, w, st, o, tile=128, base_h=0, frieze=12)
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        corner_post(X, st['trim'], x, y, L.PLAT_Z, L.PLAT_Z + L.TH_HUT_H + 2, o, 7)
    save('hut', X)


# ================================================================================================= textures + make
def make_textures():
    pass


def make_models():
    manor_models(); maus_models(); crypt_vault(); cottage_models(); hut_models()
