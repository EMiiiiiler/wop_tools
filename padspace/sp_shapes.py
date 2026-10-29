"""Convex solids shared by build_space.py (invisible common/weapclip collision) and sp_models.py (the visible,
lightmapped MD3 surfaces via splib.solids_mesh): the rocket's shell, stair, decks, balcony and fins; the lunar lander;
Planet Padurn's sphere, ring and stair; the satellite dive tower; the buildings of Star Boulevard and the habitat pods.
Every function returns wopmap Brushes in world coordinates (texture 'common/caulk', replaced by the caller)."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import hull, box, carve, ngon, cyl, sub_rects
import layout as L

X = 'common/caulk'


def tag(b, part):
    b.part = part
    return b


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, r1_top=None, r0_top=None, tex=X):
    """annulus wedge between angles a0..a1 (deg), radii r0..r1, z0..z1; r1_top / r0_top give sloped faces"""
    pts = []
    for a in (a0, a1):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        for (r, z) in ((r0, z0), (r1, z0), (r0 if r0_top is None else r0_top, z1), (r1 if r1_top is None else r1_top, z1)):
            if r < 0.5:
                pts.append((cx, cy, z))
            else:
                pts.append((cx + r * c, cy + r * s, z))
    return hull(pts, tex, round_pts=False)


def frustum(cx, cy, r0, r1, z0, z1, n=16, phase=0.0, tex=X):
    pts = []
    for k in range(n):
        a = math.radians(phase + 360 * k / n)
        pts += [(cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0), (cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1)]
    return hull(pts, tex, round_pts=False)


def pip(poly, x, y):
    inside = False
    n = len(poly)
    for k in range(n):
        (x0, y0), (x1, y1) = poly[k], poly[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0: inside = not inside
    return inside


# ================================================================================================= the rocket
RK_ZS = [0, 40, 80, 120, 160, 200, 240, 280, 320, 352, 400, 448, 496, 544, 592, 624, 672, 720, 768, 816, 864, 912, 960, 1008, 1056, 1104]
RK_NW = 48


def rk_open_cell(a0, a1, z0, z1, polys=None):
    polys = polys or L.rk_open_polys()
    for a in np.linspace(a0, a1, 4):
        da = (a - L.RK_FACE + 180) % 360 - 180
        u = math.radians(da) * L.RK_RR
        for z in np.linspace(z0, z1, 4):
            if not any(pip(p, uu, z) for p in polys for uu in (u, u + 2 * math.pi * L.RK_RR, u - 2 * math.pi * L.RK_RR)): return False
    return True


def rk_outer(z): return L.rk_profile(z)


def rocket_shell():
    """shell wedges between the inner and outer surfaces (6u inside both), openings left out; a solid cone caps the
    tip above the last layer"""
    cx, cy = L.RK
    polys = L.rk_open_polys()
    out = []
    for i in range(len(RK_ZS) - 1):
        z0, z1 = RK_ZS[i], RK_ZS[i + 1]
        for k in range(RK_NW):
            a0, a1 = 360 * k / RK_NW, 360 * (k + 1) / RK_NW
            if rk_open_cell(a0, a1, z0, z1, polys): continue
            zz = np.linspace(z0, z1, 5)
            ro = [min(rk_outer(z) for z in zz) - 6] * 2 if z0 >= L.RK_BODY_TOP - 1 else [rk_outer(z0) - 6, rk_outer(z1) - 6]
            if z0 < 140: ro = [min(rk_outer(z0), rk_outer(z1)) - 6] * 2
            ri = [max(L.rk_inner_r(z) for z in zz) + 6] * 2
            if ro[0] - ri[0] < 4: ri = [ro[0] - 12] * 2
            pts = []
            for a in (a0, a1):
                c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
                for (r, z) in ((ro[0], z0), (ro[1], z1), (ri[0], z0), (ri[1], z1)):
                    pts.append((cx + r * c, cy + r * s_, z))
            out.append(tag(hull(pts, X, round_pts=False), 'shell'))
    z0 = RK_ZS[-1]
    out.append(tag(frustum(cx, cy, rk_outer(z0) - 6, 6, z0, L.RK_TIP - 30, 16), 'shell'))
    return out


def rk_stair_hole(j):
    """steps whose head room reaches the cockpit deck slab"""
    a0, a1, zt = L.rk_step(j)
    return zt + 56 + 40 > L.COCK_Z - L.SLAB_T


def rocket_interior():
    """the stair round the inside wall (counter-clockwise up to the cockpit deck), the cockpit deck (centre hole for the
    pad, open over the stairwell), the nose deck (centre hole)"""
    cx, cy = L.RK
    out = []
    rin0 = L.rk_inner_r(200) - 2
    hole_secs = []
    for j in range(L.RK_STAIR_N):
        a0, a1, zt = L.rk_step(j)
        rin = min(L.rk_inner_r(z) for z in (0, 60, 120, 160, zt)) + 6 - 0.0
        rr = min(rin0, rin)
        out.append(tag(ring_seg(cx, cy, a0, a1, rr - L.RK_STAIR_W, rr * math.cos(math.radians(L.RK_STAIR_DA / 2)) + 0.0, 0, zt), 'stair'))
        if rk_stair_hole(j): hole_secs.append((a0 % 360, a1 % 360 if a1 % 360 > a0 % 360 else a1 % 360 + 360))
    # cockpit deck: 24 sectors of 15 deg aligned with the stair; sectors over the top of the stairwell are left open
    z1 = L.COCK_Z; z0 = z1 - L.SLAB_T
    rdeck = L.rk_inner_r(z1) + 6
    for k in range(24):
        a0 = L.RK_STAIR_A0 + 15 * k; a1 = a0 + 15
        if any(abs(((a0 - h0) + 180) % 360 - 180) < 1 for (h0, h1) in hole_secs):
            # leave the stair part open, keep the inner part of the sector (inside the stair's inner radius)
            out.append(tag(ring_seg(cx, cy, a0, a1, L.RK_HOLE, rin0 - L.RK_STAIR_W, z0, z1), 'cdeck'))
            continue
        out.append(tag(ring_seg(cx, cy, a0, a1, L.RK_HOLE, rdeck, z0, z1), 'cdeck'))
    # nose deck
    z1 = L.NOSE_Z; z0 = z1 - L.SLAB_T
    rn = min(L.rk_inner_r(z0), L.rk_inner_r(z1)) + 6
    for k in range(24):
        a0 = 15 * k; a1 = a0 + 15
        out.append(tag(ring_seg(cx, cy, a0, a1, 0, rn, z0, z1), 'ndeck'))
    return out


def rocket_balcony():
    """outer balcony ring at the cockpit deck height; low rail round it with gaps where the slides start (W and E)"""
    cx, cy = L.RK
    out = []
    z1 = L.COCK_Z; z0 = z1 - L.SLAB_T
    n = 32
    for k in range(n):
        a0 = 360 * k / n + 180 / n; a1 = a0 + 360 / n
        out.append(tag(ring_seg(cx, cy, a0, a1, L.BALC_R0, L.BALC_R1, z0, z1), 'balcony'))
        am = (a0 + a1) / 2
        if min(abs(((am - g) + 180) % 360 - 180) for g in (0, 180)) < 12: continue
        out.append(tag(ring_seg(cx, cy, a0, a1, L.BALC_R1 - 8, L.BALC_R1, z1, z1 + L.BALC_RAIL), 'rail'))
    return out


def rocket_fins():
    """four fins: a slanted slab from the skirt out to the tip at the ground, top edge under the balcony"""
    cx, cy = L.RK
    out = []
    for a in L.FIN_A:
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        t = (-s, c)
        pts = []
        prof = [(L.RK_R - 20, 0), (L.FIN_R1, 0), (L.FIN_R1, 24), (L.RK_R + 120, 300), (L.RK_R - 20, 320)]
        for (r, z) in prof:
            for w in (-L.FIN_T / 2, L.FIN_T / 2):
                pts.append((cx + r * c + w * t[0], cy + r * s + w * t[1], z))
        b = hull(pts, X, round_pts=False)
        # cut away what lies inside the shell's outer surface (the shell wedges are their own brushes)
        for p in carve(b, [cyl(cx, cy, L.RK_SKIRT + 2, -1, 400, X, 48, phase=0)]):
            out.append(tag(p, 'fin'))
    return out


# ================================================================================================= the lunar lander
def lander_stage():
    """descent stage: an octagonal prism from the lagoon floor to the deck"""
    return [tag(hull([(x, y, z) for (x, y) in L.lander_oct() for z in (L.DEEP, L.DECK_Z)], X, round_pts=False), 'stage')]


def walls_rect(x0, y0, x1, y1, z0, z1, t, openings=(), part='wall'):
    """four walls of thickness t inside the footprint; openings [(side, c, half_w, zb, zt)] (side n/s/e/w, c = centre
    coordinate along the wall). Corners belong to the n/s walls."""
    out = []
    spec = {'s': (x0, x1, y0, y0 + t, 'x'), 'n': (x0, x1, y1 - t, y1, 'x'), 'w': (x0, x0 + t, y0 + t, y1 - t, 'y'),
            'e': (x1 - t, x1, y0 + t, y1 - t, 'y')}
    for side, (ax0, ax1, ay0, ay1, ax) in spec.items():
        ops = sorted([(c - hw, c + hw, zb, zt) for (s_, c, hw, zb, zt) in openings if s_ == side])
        lo, hi = (ax0, ax1) if ax == 'x' else (ay0, ay1)
        cuts = sorted(set([lo, hi] + [v for o in ops for v in o[:2] if lo < v < hi]))
        for a, b in zip(cuts, cuts[1:]):
            m = (a + b) / 2
            spans = [(z0, z1)]
            for (oa, ob, zb, zt) in ops:
                if oa <= m <= ob:
                    nxt = []
                    for (za, zb_) in spans:
                        if zb > za: nxt.append((za, min(zb, zb_)))
                        if zt < zb_: nxt.append((max(zt, za), zb_))
                    spans = [s for s in nxt if s[1] - s[0] > 0.5]
            for (za, zb_) in spans:
                if ax == 'x': br = box((a, ay0, za), (b, ay1, zb_), X)
                else: br = box((ax0, a, za), (ax1, b, zb_), X)
                br.part = part; br.side = side
                out.append(br)
    return out


def stair_run(x0, y0, x1, y1, z0, ztop, run_dir, part='stair', base=None):
    """straight flight on the footprint rising toward run_dir; solid steps from `base` (default z0)"""
    n = int(round((ztop - z0) / 16))
    out = []
    Ln = (y1 - y0) if run_dir in 'ns' else (x1 - x0)
    d = Ln / n
    for i in range(n):
        zt = z0 + 16 * (i + 1)
        if run_dir == 'n': r = (x0, y0 + d * i, x1, y0 + d * (i + 1))
        elif run_dir == 's': r = (x0, y1 - d * (i + 1), x1, y1 - d * i)
        elif run_dir == 'e': r = (x0 + d * i, y0, x0 + d * (i + 1), y1)
        else: r = (x1 - d * (i + 1), y0, x1 - d * i, y1)
        zb = z0 if base is None else max(z0, zt - base)
        out.append(tag(box((r[0], r[1], zb), (r[2], r[3], zt), X), part))
    return out


def roof_slab(x0, y0, x1, y1, z1, t=16, over=8, holes=()):
    out = []
    for r in sub_rects((x0 - over, y0 - over, x1 + over, y1 + over), list(holes)):
        out.append(tag(box((r[0], r[1], z1 - t), (r[2], r[3], z1), X), 'roof'))
    return out


def roof_rail(x0, y0, x1, y1, z1, h=32, t=8, gaps=()):
    """low rail round a roof edge (collision, below eye height so it never blocks shots), gaps [(side, a, b)]"""
    out = []
    for side, (ax0, ax1, ay0, ay1, ax) in {'s': (x0, x1, y0, y0 + t, 'x'), 'n': (x0, x1, y1 - t, y1, 'x'),
                                          'w': (x0, x0 + t, y0 + t, y1 - t, 'y'), 'e': (x1 - t, x1, y0 + t, y1 - t, 'y')}.items():
        lo, hi = (ax0, ax1) if ax == 'x' else (ay0, ay1)
        segs = [(lo, hi)]
        for (s_, a, b) in gaps:
            if s_ != side: continue
            nxt = []
            for (p, q) in segs:
                if b <= p or a >= q: nxt.append((p, q)); continue
                if a > p: nxt.append((p, a))
                if b < q: nxt.append((b, q))
            segs = nxt
        for (p, q) in segs:
            if q - p < 2: continue
            br = box((p, ay0, z1), (q, ay1, z1 + h), X) if ax == 'x' else box((ax0, p, z1), (ax1, q, z1 + h), X)
            out.append(tag(br, 'rail'))
    return out


def lander_cabin():
    """ascent cabin on the deck: walls with doors north and south and a window each side, flat roof"""
    lx, ly = L.LANDER
    c = L.CAB
    x0, y0, x1, y1 = lx + c[0], ly + c[1], lx + c[2], ly + c[3]
    ops = [('n', lx, L.CAB_DOOR_HW, L.DECK_Z, L.DECK_Z + L.CAB_DOOR_H), ('s', lx, L.CAB_DOOR_HW, L.DECK_Z, L.DECK_Z + L.CAB_DOOR_H),
           ('e', ly, 44, L.DECK_Z + 64, L.DECK_Z + 140), ('w', ly, 44, L.DECK_Z + 64, L.DECK_Z + 140)]
    out = walls_rect(x0, y0, x1, y1, L.DECK_Z, L.CAB_TOP - 16, L.CAB_T, ops)
    out += roof_slab(x0, y0, x1, y1, L.CAB_TOP, over=0)
    return out


# ================================================================================================= Planet Padurn
PL_ZS = [130, 160, 200, 250, 288, 330, 380, 430, 480, 530, 570, 600]


def planet_sphere():
    """stacked 16-gon frusta 6u inside the sphere, flat top = the polar cap walk; the pedestal cone under it"""
    cx, cy = L.PL
    out = []
    for z0, z1 in zip(PL_ZS, PL_ZS[1:]):
        out.append(tag(frustum(cx, cy, max(8, L.pl_sphere_r(z0) - 6), max(8, L.pl_sphere_r(z1) - 6), z0, z1, 16, 11.25), 'sphere'))
    out.append(tag(frustum(cx, cy, L.PED_R0, L.PED_R1, 0, 130, 16, 11.25), 'pedestal'))
    return out


def planet_ring():
    """the walkable ring round the planet (32 wedges)"""
    cx, cy = L.PL
    out = []
    n = 32
    for k in range(n):
        a0 = 360 * k / n + 180 / n; a1 = a0 + 360 / n
        out.append(tag(ring_seg(cx, cy, a0, a1, L.RING_R0, L.RING_R1, L.RING_Z - 16, L.RING_Z), 'ring'))
    return out


def planet_stair():
    """straight stair from the plaza (east) up to the ring's outer edge, crossing the river as a bridge"""
    cx, cy = L.PL
    n = L.RING_Z // 16
    out = []
    hw = L.PL_STAIR_W / 2
    xr = cx + L.RING_R1 * math.cos(math.radians(180 / 32))       # the ring's flat chord facing east
    for i in range(n):
        zt = L.RING_Z - 16 * i
        xa = xr + 32 * i; xb = xa + 32
        r_mid = (xa + xb) / 2 - cx
        over_water = r_mid < L.RIVER_R1 + 24
        zb = zt - 24 if over_water else 0
        out.append(tag(box((xa, cy - hw, zb), (xb, cy + hw, zt - 0), X), 'stair'))
    return out


# ================================================================================================= the satellite tower
def sat_path():
    """square spiral stair round the core: [(x0, y0, x1, y1, z_top)], from the south-west corner rising east"""
    cx, cy = L.SAT
    h = L.SAT_HALF; f = L.SAT_FLIGHT; c = h - f
    steps = []
    seq = [('corner', (-h, -h)), ('run', 's'), ('corner', (h - f, -h)), ('run', 'e'), ('corner', (h - f, h - f)), ('run', 'n'),
           ('corner', (-h, h - f)), ('run', 'w')]
    k = 0; z = 0
    while z < L.SAT_TOP:
        kind, d = seq[k % len(seq)]
        if kind == 'corner':
            z += 16
            steps.append((cx + d[0], cy + d[1], cx + d[0] + f, cy + d[1] + f, z))
        else:
            nrun = 3; run = 2 * c / nrun
            for i in range(nrun):
                if z >= L.SAT_TOP: break
                z += 16
                if d == 's': steps.append((cx - c + run * i, cy - h, cx - c + run * (i + 1), cy - h + f, z))
                elif d == 'e': steps.append((cx + c, cy - c + run * i, cx + h, cy - c + run * (i + 1), z))
                elif d == 'n': steps.append((cx + c - run * (i + 1), cy + c, cx + c - run * i, cy + h, z))
                else: steps.append((cx - h, cy + c - run * (i + 1), cx - h + f, cy + c - run * i, z))
        k += 1
    return steps


def sat_tower():
    cx, cy = L.SAT
    h = L.SAT_HALF; c = h - L.SAT_FLIGHT
    out = [tag(box((cx - c, cy - c, 0), (cx + c, cy + c, L.SAT_TOP - 16), X), 'core')]
    steps = sat_path()
    holes = []
    for (x0, y0, x1, y1, zt) in steps:
        if zt >= L.SAT_TOP: break
        out.append(tag(box((x0, y0, max(0, zt - 48)), (x1, y1, zt), X), 'step'))
        if zt + 56 + 32 > L.SAT_TOP - 16:
            holes.append((x0, y0, x1, y1))
    for b in roof_slab(cx - h, cy - h, cx + h, cy + h, L.SAT_TOP, t=16, over=0, holes=holes):
        out.append(tag(b, 'deck'))
    return out, steps, holes


def sat_arm():
    """the diving arm: from the tower's north-west corner toward the Black Hole's centre (135 deg)"""
    cx, cy = L.SAT
    h = L.SAT_HALF
    d = np.array([-1.0, 1.0]) / math.sqrt(2); t = np.array([d[1], -d[0]])
    p0 = np.array([cx - h + 20, cy + h - 20])
    pts = []
    for s in (0.0, 300.0):
        for w in (-26, 26):
            q = p0 + d * s + t * w
            for z in (L.SAT_TOP - 8, L.SAT_TOP):
                pts.append((q[0], q[1], z))
    arm = hull(pts, X, round_pts=False)
    deck = box((cx - h - 1, cy - h - 1, L.SAT_TOP - 17), (cx + h + 1, cy + h + 1, L.SAT_TOP + 1), X)
    return [tag(p, 'arm') for p in carve(arm, [deck])]


# ================================================================================================= buildings
def cafe():
    x0, y0, x1, y1 = L.CAFE
    H = L.CAFE_H
    yc = (y0 + y1) / 2
    ops = [('w', yc, 60, 0, 168), ('w', yc - 170, 44, 72, 168), ('w', yc + 170, 44, 72, 168),
           ('s', x0 + 140, 44, 72, 168), ('n', x0 + 140, 44, 72, 168), ('n', x1 - 160, 44, 72, 168),
           ('e', yc, 44, 96, 168)]
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 24, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    out += stair_run(x1 - 24 - 16 * 22, y0 - 8 - 96, x1 - 24, y0 - 8, 0, H, 'e')
    out += roof_rail(x0 - 8, y0 - 8, x1 + 8, y1 + 8, H, gaps=[('s', x1 - 120, x1 - 24)])
    out.append(tag(box((x1 - 24 - 150, yc - 150, 0), (x1 - 24 - 110, yc + 150, 56), X), 'counter'))
    out.append(tag(box((x1 - 24 - 162, yc - 160, 56), (x1 - 24 - 98, yc + 160, 62), X), 'counter'))
    return out


def mission_control():
    x0, y0, x1, y1 = L.MC
    H = L.MC_H
    yc = (y0 + y1) / 2
    ops = [('w', yc, 56, 0, 152), ('w', yc - 120, 36, 64, 140), ('w', yc + 120, 36, 64, 140), ('s', (x0 + x1) / 2, 40, 64, 140),
           ('n', (x0 + x1) / 2, 40, 64, 140)]
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 24, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    out += roof_rail(x0 - 8, y0 - 8, x1 + 8, y1 + 8, H)
    out.append(tag(box((x0 + 140, yc - 100, 0), (x0 + 180, yc + 100, 40), X), 'counter'))
    return out


def pod(rect):
    """habitat pod: walls with a door east and portholes, flat roof"""
    x0, y0, x1, y1 = rect
    H = L.POD_H
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    ops = [('e', yc, 48, 0, 128), ('n', xc, 32, 64, 120), ('s', xc, 32, 64, 120), ('w', yc, 32, 64, 120)]
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 16, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    return out


def loo():
    """the Zero-G Loo: a little capsule, door west"""
    lx, ly = L.LOO
    h = L.LOO_HALF
    out = walls_rect(lx - h, ly - h, lx + h, ly + h, 0, 128, 8, [('w', ly, 28, 0, 104)])
    out += roof_slab(lx - h, ly - h, lx + h, ly + h, 136, t=8, over=0)
    return out
