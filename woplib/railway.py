"""woplib.railway - model-railway pieces any map can reuse (promoted from padattic, generalised on wop_padville).

    from woplib import railway as RW
    RW.track_ring(K, 'track', centre, R, z, sh_rail, sh_tie, gauge=69)      # MD3 arcs of ties + rails on a circle
    car = RW.Car('loco', model, x0=-300, x1=320, top=200, half_w=70)          # a ML.Model in car space (see below)
    T = RW.CircleTrain(K, 'express', centre, R, rail_z, [car, ...], front_deg=200, speed=6)
    T.build()                       # one func_rotating: IQM model2 of the whole train + weapclip box per car
    T.sweep_check()                 # no static solid inside the swept band (the train would stop against it)
    RW.turntable(K, 'tt', centre, r, z_top, deck_model_place, speed=8)       # a deck you can ride (func_rotating)

Car space: x forward (along the track), y left, z = 0 on the rail top. The train runs counter-clockwise (or clockwise
with reverse=True), so local +x is the CCW tangent.

Rules baked in:
  * WoP common/nodraw is NONSOLID: car collision is common/weapclip (players ride on the roofs)
  * func_rotating takes an origin brush and NO origin key (q3map2 adds both -> leak)
  * model2 can't be scaled and MD3 can't hold geometry beyond +-512u, so the train is ONE IQM at the circle centre
  * a rotating pusher never crushes; it moves anyone in its path along the circle - but if a rider on a roof is wedged
    under a ceiling (tunnel) the whole train stops: keep tunnel ceilings >= car top + 80
"""
import math
import numpy as np
from wopmap import box, hull, cyl
from .kit import CAULK, WCLIP, ORIGIN
from . import models as ML
from meshlib import Mesh, rbox


# ------------------------------------------------------------------------------------------------ track
def track_arc_model(R, deg, gauge, sh_rail, sh_tie, sh_chair=None, tie_len=None, tie_w=18.0, tie_h=8.0, tie_pitch=44.0,
                    rail_w=7.0, rail_h=10.0, nseg=None):
    """ties + two rails along an arc of `deg` degrees centred on local +x at radius R (origin on the circle at
    mid-arc, the arc bends toward -x). z = 0 is the top of the ballast."""
    X = ML.Model()
    tie_len = tie_len or gauge * 1.8
    half = math.radians(deg) / 2
    L = R * 2 * half
    nt = max(2, int(L / tie_pitch))
    for i in range(nt):
        a = -half + (i + 0.5) * 2 * half / nt
        c, s = math.cos(a), math.sin(a)
        M = Mesh(); rbox(M, (-tie_len / 2, -tie_w / 2, 0), (tie_len / 2, tie_w / 2, tie_h), r=1.5, k=1, tile=64)
        Rm = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
        X.mesh(sh_tie).add(M, Rm, (R * c - R, R * s, 0))
    nseg = nseg or max(4, int(deg / 2))
    for side in (-1, 1):
        r = R + side * gauge / 2
        P = []
        for k in range(nseg + 1):
            a = -half + 2 * half * k / nseg
            P.append((r * math.cos(a) - R, r * math.sin(a)))
        M = X.mesh(sh_rail)
        for k in range(nseg):
            (ax, ay), (bx, by) = P[k], P[k + 1]
            d = np.array([bx - ax, by - ay]); d /= np.linalg.norm(d); nrm = np.array([d[1], -d[0]])
            for (o0, o1, n3) in ((-rail_w / 2, rail_w / 2, (0, 0, 1)),):
                q = [np.array([ax + nrm[0] * o0, ay + nrm[1] * o0, tie_h + rail_h]), np.array([bx + nrm[0] * o0, by + nrm[1] * o0, tie_h + rail_h]),
                     np.array([bx + nrm[0] * o1, by + nrm[1] * o1, tie_h + rail_h]), np.array([ax + nrm[0] * o1, ay + nrm[1] * o1, tie_h + rail_h])]
                M.poly(q, n3, [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
            for o in (-rail_w / 2, rail_w / 2):
                sg = 1 if o > 0 else -1
                q = [np.array([ax + nrm[0] * o, ay + nrm[1] * o, tie_h]), np.array([bx + nrm[0] * o, by + nrm[1] * o, tie_h]),
                     np.array([bx + nrm[0] * o, by + nrm[1] * o, tie_h + rail_h]), np.array([ax + nrm[0] * o, ay + nrm[1] * o, tie_h + rail_h])]
                M.poly(q, (nrm[0] * sg, nrm[1] * sg, 0), [(0, 0), (1, 0), (1, 0.15), (0, 0.15)])
    return X


def track_ring(K, name, centre, R, z, sh_rail, sh_tie, gauge=69.0, n=16, skip=(), **kw):
    """n MD3 arcs round a circle (identical arcs share one MD3). skip = arc indices left out (e.g. inside a building
    that draws its own track). Returns the rail-top z (z + tie_h + rail_h)."""
    deg = 360.0 / n
    X = track_arc_model(R, deg, gauge, sh_rail, sh_tie, **kw)
    place = ML.save(name, X)
    for i in range(n):
        if i in skip: continue
        a = deg * (i + 0.5)
        ar = math.radians(a)
        K.custom(place, centre[0] + R * math.cos(ar), centre[1] + R * math.sin(ar), z, angle=a, occupy=False)
    return z + kw.get('tie_h', 8.0) + kw.get('rail_h', 10.0)


# ------------------------------------------------------------------------------------------------ the train
class Car:
    def __init__(self, name, model, x0, x1, top, half_w, gap=14.0):
        self.name, self.model = name, model
        self.x0, self.x1, self.top, self.half_w, self.gap = x0, x1, top, half_w, gap


class CircleTrain:
    def __init__(self, K, name, centre, R, rail_z, cars, front_deg=0.0, speed=6.0, reverse=False, origin_dz=300):
        self.K, self.name = K, name
        self.c = (float(centre[0]), float(centre[1])); self.R = float(R); self.rail_z = float(rail_z)
        self.cars = cars; self.front = front_deg; self.speed = speed; self.reverse = reverse
        self.oz = self.rail_z + origin_dz              # origin brush height (inside the world, above the floor)

    def layout(self):
        """[(car, centre angle deg)] travelling CCW (front car at front_deg)"""
        out = []; s = 0.0
        sg = -1 if not self.reverse else 1
        for car in self.cars:
            L = car.x1 - car.x0
            out.append((car, self.front + sg * math.degrees((s + L / 2) / self.R)))
            s += L + car.gap
        return out

    def length(self):
        return sum(c.x1 - c.x0 + c.gap for c in self.cars)

    def band(self):
        """(r_in, r_out, z0, z1) swept by the cars (straight cars on a curve bulge out at the ends)"""
        r_out = max(math.hypot(self.R + c.half_w, max(abs(c.x0), abs(c.x1))) for c in self.cars)
        r_in = min(self.R - c.half_w for c in self.cars)
        return r_in, r_out, self.rail_z, self.rail_z + max(c.top for c in self.cars)

    def build(self):
        K = self.K
        X = ML.Model()
        cx, cy = self.c
        for car, ang in self.layout():
            th = math.radians(ang)
            yaw = th + (math.pi / 2 if not self.reverse else -math.pi / 2)
            ca, sa = math.cos(yaw), math.sin(yaw)
            Rm = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1.0]])
            xc = (car.x0 + car.x1) / 2
            pos = np.array([self.R * math.cos(th), self.R * math.sin(th), self.rail_z - self.oz])
            for sh, M in car.model.m.items():
                MM = Mesh(); MM.add(M, np.eye(3), (-xc, 0, 0))
                X.mesh(sh).add(MM, Rm, pos)
        path = ML.save_iqm(self.name, X)
        o = (round(cx), round(cy), round(self.oz))
        brushes = [box((o[0] - 8, o[1] - 8, o[2] - 8), (o[0] + 8, o[1] + 8, o[2] + 8), ORIGIN)]
        for car, ang in self.layout():
            th = math.radians(ang)
            t = np.array([-math.sin(th), math.cos(th)]) * (1 if not self.reverse else -1)
            rad = np.array([math.cos(th), math.sin(th)])
            cpos = np.array([cx, cy]) + rad * self.R
            xc = (car.x0 + car.x1) / 2
            pts = []
            for lx in (car.x0 + 6, car.x1 - 6):
                for ly in (-car.half_w + 6, car.half_w - 6):
                    p = cpos + t * (lx - xc) + rad * ly
                    pts += [(p[0], p[1], self.rail_z + 4), (p[0], p[1], self.rail_z + car.top)]
            brushes.append(hull(pts, WCLIP, round_pts=False))
        sf = 2 if self.reverse else 0
        K.ent('func_rotating', brushes=brushes, model2=path, speed=self.speed, spawnflags=sf, dmg=0)
        K.spots['movers'].append(dict(cls='func_rotating', centre=list(o), model=path, train=self.name,
                                      band=list(self.band())))
        return path

    def sweep_check(self, extra_margin=8):
        """static solids inside the swept band: the train would stop against them (rotating pushers can't crush)"""
        K = self.K
        r_in, r_out, z0, z1 = self.band()
        r_in -= extra_margin; r_out += extra_margin
        cx, cy = self.c
        sol = []
        for b in K.M.world:
            if not b.is_solid(): continue
            ts = b.textures()
            if all(any(h in (t or '') for h in ('trigger', 'clip', 'nodraw_ns', 'origin', 'water', 'fog')) for t in ts):
                continue
            mn, mx = b.bounds()
            if mx[2] <= z0 + 1 or mn[2] >= z1 - 1: continue
            sol.append((b, mn, mx))
        bad = []
        for a in np.arange(0, 360, 0.75):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            for r in np.linspace(r_in, r_out, 6):
                for z in (z0 + 6, (z0 + z1) / 2, z1 - 4):
                    p = (cx + r * ca, cy + r * sa, z)
                    for (b, mn, mx) in sol:
                        if mn[0] < p[0] < mx[0] and mn[1] < p[1] < mx[1] and mn[2] < p[2] < mx[2] and \
                           all(n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - d < -0.5 for (n, d) in b.planes()):
                            bad.append((round(a, 1), round(r), round(z), tuple(np.round(mn).astype(int)))); break
        print(f'train {self.name} sweep R {r_in:.0f}..{r_out:.0f} z {z0:.0f}..{z1:.0f}:',
              'OK' if not bad else f'{len(bad)} hits, e.g. {bad[:6]}')
        if bad: K.warn(f'train {self.name}: {len(bad)} static solid hits in the swept band, e.g. {bad[:3]}')
        return bad


# ------------------------------------------------------------------------------------------------ turntable
def turntable(K, name, centre, r, z_top, deck_place, speed=8.0, thick=16, n=16, reverse=False):
    """a rideable deck: func_rotating with an n-gon weapclip disc (thick, top at z_top) + origin brush + model2 deck.
    Build a pit floor at z_top - thick under it yourself (bspc ignores movers: the AAS walks on the pit floor, 16u
    lower, so bots still cross it)."""
    cx, cy = centre
    o = (round(cx), round(cy), round(z_top - thick / 2))
    brushes = [box((o[0] - 4, o[1] - 4, o[2] - 4), (o[0] + 4, o[1] + 4, o[2] + 4), ORIGIN),
               cyl(cx, cy, r, z_top - thick + 0.0, z_top, WCLIP, n)]
    K.ent('func_rotating', brushes=brushes, model2=deck_place, speed=speed, spawnflags=2 if reverse else 0, dmg=0)
    K.spots['movers'].append(dict(cls='func_rotating', centre=list(o), model=deck_place, turntable=name))
