"""Convex solids shared by build_pirate.py (invisible common/weapclip collision) and pp_models.py (the visible,
lightmapped MD3 surfaces via pplib.solids_mesh): the galleon's hull stations, decks, castles, bulwarks and stairs,
Skull Rock's shell and hat, Fort San Padro, the dive tower and the buildings of Tortuga Quay and Treasure Cove.
Every function returns wopmap Brushes in world coordinates (texture 'common/caulk', replaced by the caller)."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import hull, box, carve, ngon, cyl
import layout as L

X = 'common/caulk'


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


# ================================================================================================= the galleon
def S(x, y):
    """ship-relative -> world xy"""
    return (L.SHIP[0] + x, L.SHIP[1] + y)


def ship_station_brushes():
    """hull stations (keel to deck) as convex prisms, before the rooms are carved out"""
    xs = L.ship_stations()
    out = []
    zs_low = [-272, -230, -180, -110, -60, L.WATER]
    for x0, x1 in zip(xs, xs[1:]):
        top = L.ship_deck_z((x0 + x1) / 2)
        pts = []
        for z in zs_low + [top]:
            w = L.ship_coll_halfbeam(x0, x1, z)
            if w < 6: continue
            for x in (x0, x1):
                for sy in (-1, 1):
                    px, py = S(x, sy * w)
                    pts.append((px, py, z))
        if len(pts) < 8: continue
        b = hull(pts, X, round_pts=False)
        b.station = (x0, x1, top)
        out.append(b)
    return out


def ship_cutters():
    sx, sy = L.SHIP
    cut = []
    h = L.HOLD
    cut.append(box((sx + h[0], sy + h[1], 0), (sx + h[2], sy + h[3], L.HOLD_Z1), X))
    c = L.CABIN
    cut.append(box((sx + c[0], sy + c[1], L.WAIST_Z), (sx + c[2], sy + c[3], L.QD_Z - L.DECK_T), X))
    cut.append(box((sx + c[2] - 1, sy - L.DOOR_HW, L.WAIST_Z), (sx + L.QD_X + 1, sy + L.DOOR_HW, L.WAIST_Z + L.CABIN_DOOR_H), X))
    c = L.CREW
    cut.append(box((sx + c[0], sy + c[1], L.WAIST_Z), (sx + c[2], sy + c[3], L.FC_Z - L.DECK_T), X))
    cut.append(box((sx + L.FC_X - 1, sy - L.DOOR_HW, L.WAIST_Z), (sx + c[0] + 1, sy + L.DOOR_HW, L.WAIST_Z + L.CREW_DOOR_H), X))
    hx = L.HATCH
    cut.append(box((sx + hx[0], sy + hx[1], L.HOLD_Z1 - 2), (sx + hx[2], sy + hx[3], L.WAIST_Z + 2), X))
    return cut


def ship_hull():
    out = []
    cuts = ship_cutters()
    for b in ship_station_brushes():
        for p in carve(b, cuts):
            p.station = b.station
            out.append(p)
    return out


def ship_rails():
    """bulwarks along the waist (entry ports at x +-PORT_HW), rails round the castles, the castles' front rails with
    gaps for the stairs, the transom rail"""
    out = []
    xs = L.ship_stations()
    t = L.BULW_T
    for x0, x1 in zip(xs, xs[1:]):
        xm = (x0 + x1) / 2
        top = L.ship_deck_z(xm)
        h = L.BULW_H if top == L.WAIST_Z else L.RAIL_H
        w = L.ship_coll_halfbeam(x0, x1, top)
        if w < 12: continue
        segs = [(x0, x1)]
        if top == L.WAIST_Z and x0 < L.PORT_HW and x1 > -L.PORT_HW:
            segs = [(a, b) for (a, b) in ((x0, -L.PORT_HW), (L.PORT_HW, x1)) if b - a > 1]
        for (a, b) in segs:
            for sy in (-1, 1):
                ya, yb = sorted((sy * (w - t), sy * w))
                p0 = S(a, ya); p1 = S(b, yb)
                br = box((p0[0], p0[1], top), (p1[0], p1[1], top + h), X)
                br.part = 'bulwark'
                out.append(br)
    # castle front rails (inside the castle tops), gaps where the stairs arrive
    for (xa, xb, top, sy, sa, sb) in ((L.QD_X - 16, L.QD_X, L.QD_Z, L.STAIR_Y, L.QD_X - 40, L.QD_X),
                                      (L.FC_X, L.FC_X + 16, L.FC_Z, L.STAIR_Y_FC, L.FC_X, L.FC_X + 40)):
        w = L.ship_coll_halfbeam(sa, sb, top) - t
        cuts = [-sy[1], -sy[0], sy[0], sy[1]]
        ys = [-w] + cuts + [w]
        for k in range(0, len(ys) - 1, 2):
            ya, yb = ys[k], ys[k + 1]
            if yb - ya < 2: continue
            p0 = S(xa, ya); p1 = S(xb, yb)
            br = box((p0[0], p0[1], top), (p1[0], p1[1], top + L.RAIL_H), X)
            br.part = 'front_rail'
            out.append(br)
    # transom rail
    w = L.ship_coll_halfbeam(L.SHIP_STERN, L.SHIP_STERN + 40, L.QD_Z) - t
    p0 = S(L.SHIP_STERN, -w); p1 = S(L.SHIP_STERN + t, w)
    br = box((p0[0], p0[1], L.QD_Z), (p1[0], p1[1], L.QD_Z + L.RAIL_H), X)
    br.part = 'bulwark'
    out.append(br)
    return out


def ship_stairs():
    out = []
    for side in (-1, 1):
        for (sy, flight) in ((L.STAIR_Y, L.stair_qd(side)), (L.STAIR_Y_FC, L.stair_fc(side))):
            ya, yb = sorted((side * sy[0], side * sy[1]))
            for (x0, x1, zt) in flight:
                p0 = S(x0, ya); p1 = S(x1, yb)
                out.append(box((p0[0], p0[1], L.WAIST_Z), (p1[0], p1[1], zt), X))
    for (x0, x1, zt) in L.stair_hold():
        p0 = S(x0, L.HATCH[1]); p1 = S(x1, L.HATCH[3])
        out.append(box((p0[0], p0[1], 0), (p1[0], p1[1], zt), X))
    return out


def ship_nest():
    """crow's nest (main fighting top): platform round the main mast + rail ring with no gaps"""
    mx, my = S(L.MASTS['main'][0], 0)
    out = [cyl(mx, my, L.NEST_R, L.NEST_Z - 16, L.NEST_Z, X, 24, phase=0)]
    for k in range(24):
        a0, a1 = 15 * k, 15 * (k + 1)
        out.append(ring_seg(mx, my, a0, a1, L.NEST_R - 8, L.NEST_R, L.NEST_Z, L.NEST_Z + L.NEST_RAIL))
    return out


def in_ship_room(p, m=0.5):
    """point inside the hold, the cabin or the crew quarters (world coords)"""
    x, y, z = p[0] - L.SHIP[0], p[1] - L.SHIP[1], p[2]
    h = L.HOLD
    if h[0] - m <= x <= h[2] + m and h[1] - m <= y <= h[3] + m and -m <= z <= L.HOLD_Z1 + m: return 'hold'
    c = L.CABIN
    if c[0] - m <= x <= c[2] + m and c[1] - m <= y <= c[3] + m and L.WAIST_Z - m <= z <= L.QD_Z - L.DECK_T + m: return 'cabin'
    c = L.CREW
    if c[0] - m <= x <= c[2] + m and c[1] - m <= y <= c[3] + m and L.WAIST_Z - m <= z <= L.FC_Z - L.DECK_T + m: return 'crew'
    if L.CABIN[2] - m <= x <= L.QD_X + m and abs(y) <= L.DOOR_HW + m and z <= L.WAIST_Z + L.CABIN_DOOR_H + m: return 'door'
    if L.FC_X - m <= x <= L.CREW[0] + m and abs(y) <= L.DOOR_HW + m and z <= L.WAIST_Z + L.CREW_DOOR_H + m: return 'door'
    hx = L.HATCH
    if hx[0] - m <= x <= hx[2] + m and hx[1] - m <= y <= hx[3] + m and L.HOLD_Z1 - m <= z <= L.WAIST_Z + m: return 'hatch'
    return None


# ================================================================================================= Skull Rock
def sk_inner_r(a_deg, z):
    """inner (cave) surface radius of the shell at angle a, height z"""
    rows = np.array(L.SK_ROWS, float)
    import pplib
    rin = pplib.offset_rows(rows, L.SK_THICK)
    r = float(np.interp(z, rin[:, 1], rin[:, 0]))
    return L.sk_deform(math.radians(a_deg), r, z)


def sk_outer_r(a_deg, z):
    return L.sk_deform(math.radians(a_deg), L.sk_profile(z), z)


def sk_open_cell(a0, a1, z0, z1):
    polys = L.sk_face_polys()
    import pplib
    for a in np.linspace(a0, a1, 4):
        da = (a - L.SK_FACE + 180) % 360 - 180
        u = math.radians(da) * L.SK_RR
        for z in np.linspace(z0, z1, 4):
            if not any(pplib.pip(p, u, z) for p in polys): return False
    return True


SK_ZS = [0, 40, 80, 120, 160, 200, 240, 280, 320, 360, 400, 440, 480]
SK_NW = 64


def skull_shell():
    """shell wedges between offset curves inside the visual shell, the carved openings left out"""
    cx, cy = L.SK
    out = []
    for i in range(len(SK_ZS) - 1):
        z0, z1 = SK_ZS[i], SK_ZS[i + 1]
        for k in range(SK_NW):
            a0, a1 = 360 * k / SK_NW, 360 * (k + 1) / SK_NW
            if sk_open_cell(a0, a1, z0, z1): continue
            angs = np.linspace(a0, a1, 3)
            ro = [min(sk_outer_r(a, z) for a in angs) - 6 for z in (z0, z1)]
            ri = [max(sk_inner_r(a, z) for a in angs) + 6 for z in (z0, z1)]
            pts = []
            for a in (a0, a1):
                c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
                for (r, z) in ((ro[0], z0), (ro[1], z1), (ri[0], z0), (ri[1], z1)):
                    pts.append((cx + r * c, cy + r * s_, z))
            b = hull(pts, X, round_pts=False)
            b.part = 'shell'
            out.append(b)
    return out


def skull_interior():
    """inner stair (along the wall, climbing counter-clockwise) and the balcony behind the eyes"""
    cx, cy = L.SK
    out = []
    for j in range(L.SK_STAIR_N):
        a0, a1, zt = L.sk_balc_step(j)
        rin = min(sk_inner_r(a, z) for a in np.linspace(a0, a1, 3) for z in (0, zt)) - 2
        b = ring_seg(cx, cy, a0, a1, rin - L.BALC_W, rin * math.cos(math.radians((a1 - a0) / 2)), 0, zt)
        b.part = 'stair'
        out.append(b)
    n = 14
    for k in range(n):
        a0 = L.BALC_A[0] + (L.BALC_A[1] - L.BALC_A[0]) * k / n
        a1 = L.BALC_A[0] + (L.BALC_A[1] - L.BALC_A[0]) * (k + 1) / n
        rin = min(sk_inner_r(a, z) for a in np.linspace(a0, a1, 3) for z in (L.BALC_Z - 24, L.BALC_Z)) - 2
        b = ring_seg(cx, cy, a0, a1, rin - L.BALC_W, rin * math.cos(math.radians((a1 - a0) / 2)), L.BALC_Z - 24, L.BALC_Z)
        b.part = 'balcony'
        out.append(b)
    return out


def skull_hat():
    """brim slab (480..512) out to BRIM_R1, crown frustum to CROWN_Z, a shaft (r SHAFT_R) through both"""
    cx, cy = L.SK
    out = []
    n = 32
    for k in range(n):
        a0, a1 = 360 * k / n + 180 / n, 360 * (k + 1) / n + 180 / n
        b = ring_seg(cx, cy, a0, a1, L.SHAFT_R, L.BRIM_R1, L.HAT_Z0, L.BRIM_Z)
        b.part = 'brim'
        out.append(b)
        b = ring_seg(cx, cy, a0, a1, L.SHAFT_R, L.BRIM_R0, L.BRIM_Z, L.CROWN_Z, r1_top=L.CROWN_R)
        b.part = 'crown'
        out.append(b)
    return out


# ================================================================================================= generic buildings
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


def stair_run(x0, y0, x1, y1, z0, ztop, run_dir, part='stair'):
    """straight flight on the footprint rising toward run_dir, solid steps from z0"""
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
        b = box((r[0], r[1], z0), (r[2], r[3], zt), X)
        b.part = part
        out.append(b)
    return out


def roof_slab(x0, y0, x1, y1, z1, t=16, over=8, holes=()):
    from wopmap import sub_rects
    out = []
    for r in sub_rects((x0 - over, y0 - over, x1 + over, y1 + over), list(holes)):
        b = box((r[0], r[1], z1 - t), (r[2], r[3], z1), X)
        b.part = 'roof'
        out.append(b)
    return out


def roof_rail(x0, y0, x1, y1, z1, h=32, t=8, gaps=()):
    """low rail round a roof edge (collision), gaps [(side, a, b)] along the side's axis"""
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
            br.part = 'rail'
            out.append(br)
    return out


# ================================================================================================= Fort San Padro
def fort():
    x0, y0, x1, y1 = L.FORT
    W, H, NW = L.FORT_W, L.FORT_H, L.FORT_NW
    gx = (x0 + x1) / 2
    ghw, gh = L.FORT_GATE
    out = []
    def B(a, b, part):
        br = box(a, b, X); br.part = part; out.append(br)
    # south wall with the gate
    B((x0, y0, 0), (gx - ghw, y0 + W, H), 'wall')
    B((gx + ghw, y0, 0), (x1, y0 + W, H), 'wall')
    B((gx - ghw, y0, gh), (gx + ghw, y0 + W, H), 'lintel')
    # east / west walls
    B((x1 - W, y0 + W, 0), (x1, y1 - NW, H), 'wall')
    B((x0, y0 + W, 0), (x0 + W, y1 - NW, H), 'wall')
    # north wall with the powder magazine carved out of it, door from the courtyard
    north = box((x0, y1 - NW, 0), (x1, y1, H), X)
    m = L.MAG
    md = (m[0] + m[2]) / 2
    cuts = [box((m[0], m[1], 0), (m[2], m[3], L.MAG_H), X), box((md - 40, y1 - NW - 1, 0), (md + 40, m[1] + 1, 128), X)]
    for p in carve(north, cuts):
        p.part = 'wall'; out.append(p)
    # stairs up the inner faces of the east and west walls, rising north to the north wall walk
    cy0, cy1 = y0 + W + 8, y1 - NW
    for (sx0, sx1) in ((x1 - W - 80, x1 - W), (x0 + W, x0 + W + 80)):
        out += stair_run(sx0, cy0, sx1, cy1, 0, H, 'n')
    # merlons on the outer edges (the tower corner is left free)
    tx, ty = L.TOWER
    def ok(px, py): return math.hypot(px - tx, py - ty) > L.TOWER_R + 30 and math.hypot(px - L.MORTAR[0], py - L.MORTAR[1]) > 80
    step = 72; mw = 36
    for s in range(int((x1 - x0) // step)):
        px = x0 + 18 + s * step
        if px + mw > x1: break
        for (py0, py1) in ((y0, y0 + 16), (y1 - 16, y1)):
            if ok(px + mw / 2, (py0 + py1) / 2):
                B((px, py0, H), (px + mw, py1, H + L.MERLON_H), 'merlon')
    for s in range(int((y1 - y0) // step)):
        py = y0 + 18 + s * step
        if py + mw > y1: break
        for (px0, px1) in ((x0, x0 + 16), (x1 - 16, x1)):
            if ok((px0 + px1) / 2, py + mw / 2):
                B((px0, py, H), (px1, py + mw, H + L.MERLON_H), 'merlon')
    # the watchtower carves the corner
    tower = cyl(tx, ty, L.TOWER_R, 0, L.TOWER_H, X, 16, phase=0)
    res = []
    for b in out:
        mn, mx = b.bounds()
        if mx[0] < tx - L.TOWER_R - 1 or mn[1] > ty + L.TOWER_R + 1:
            res.append(b); continue
        part = getattr(b, 'part', 'wall')
        for p in carve(b, [tower]):
            p.part = part; res.append(p)
    tower.part = 'tower'
    res.append(tower)
    # tower merlons
    for k in range(8):
        a0 = 45 * k + 14; a1 = a0 + 16
        b = ring_seg(tx, ty, a0, a1, L.TOWER_R - 16, L.TOWER_R, L.TOWER_H, L.TOWER_H + L.MERLON_H)
        b.part = 'merlon'
        res.append(b)
    return res


def fort_courtyard():
    x0, y0, x1, y1 = L.FORT
    return (x0 + L.FORT_W, y0 + L.FORT_W, x1 - L.FORT_W, y1 - L.FORT_NW)


# ================================================================================================= dive tower
def dive_path():
    """square spiral stair round the core: [(x0, y0, x1, y1, z_top)], step 0 at the south-west corner rising east"""
    cx, cy = L.DIVE
    h = L.DIVE_HALF; f = L.DIVE_FLIGHT; c = h - f          # core half 48
    steps = []
    # sides in order: south (west -> east), east (south -> north), north (east -> west), west (north -> south)
    seq = [('corner', (-h, -h)), ('run', 's'), ('corner', (h - f, -h)), ('run', 'e'), ('corner', (h - f, h - f)), ('run', 'n'),
           ('corner', (-h, h - f)), ('run', 'w')]
    k = 0; z = 0
    while z < L.DIVE_TOP:
        kind, d = seq[k % len(seq)]
        if kind == 'corner':
            z += 16
            steps.append((cx + d[0], cy + d[1], cx + d[0] + f, cy + d[1] + f, z))
        else:
            nrun = 4; run = 2 * c / nrun
            for i in range(nrun):
                if z >= L.DIVE_TOP: break
                z += 16
                if d == 's': steps.append((cx - c + run * i, cy - h, cx - c + run * (i + 1), cy - h + f, z))
                elif d == 'e': steps.append((cx + c, cy - c + run * i, cx + h, cy - c + run * (i + 1), z))
                elif d == 'n': steps.append((cx + c - run * (i + 1), cy + c, cx + c - run * i, cy + h, z))
                else: steps.append((cx - h, cy + c - run * (i + 1), cx - h + f, cy + c - run * i, z))
        k += 1
    return steps


def dive_tower():
    cx, cy = L.DIVE
    h = L.DIVE_HALF; c = h - L.DIVE_FLIGHT
    out = []
    core = box((cx - c, cy - c, 0), (cx + c, cy + c, L.DIVE_TOP - 16), X); core.part = 'core'; out.append(core)
    steps = dive_path()
    holes = []
    for (x0, y0, x1, y1, zt) in steps:
        if zt >= L.DIVE_TOP: break
        b = box((x0, y0, max(0, zt - 48)), (x1, y1, zt), X); b.part = 'step'; out.append(b)
        if zt + 56 + 32 > L.DIVE_TOP - 16:            # open the ceiling two steps early (steps shallower than the player box)
            holes.append((x0, y0, x1, y1))
    # top platform (slab) minus the stairwell opening
    out += [b for b in roof_slab(cx - h, cy - h, cx + h, cy + h, L.DIVE_TOP, t=16, over=0, holes=holes)]
    for b in out:
        if getattr(b, 'part', '') == 'roof': b.part = 'deck'
    return out, steps, holes


# ================================================================================================= buildings
def tavern():
    x0, y0, x1, y1 = L.TAV
    H = L.TAV_H
    yc = (y0 + y1) / 2
    ops = [('w', yc, 60, 0, 168), ('w', yc - 170, 44, 72, 168), ('w', yc + 170, 44, 72, 168),
           ('s', x0 + 140, 44, 72, 168), ('n', x0 + 140, 44, 72, 168), ('n', x1 - 160, 44, 72, 168),
           ('e', yc, 44, 96, 168)]
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 24, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    # outside stair along the south wall, rising east to the roof edge
    out += stair_run(x1 - 24 - 16 * 22, y0 - 8 - 96, x1 - 24, y0 - 8, 0, H, 'e')
    out += roof_rail(x0 - 8, y0 - 8, x1 + 8, y1 + 8, H, gaps=[('s', x1 - 120, x1 - 24)])
    # bar counter along the east wall (inside)
    b = box((x1 - 24 - 150, yc - 150, 0), (x1 - 24 - 110, yc + 150, 56), X); b.part = 'counter'; out.append(b)
    b = box((x1 - 24 - 162, yc - 160, 56), (x1 - 24 - 98, yc + 160, 62), X); b.part = 'counter'; out.append(b)
    return out


def shop():
    x0, y0, x1, y1 = L.SHOP
    H = L.SHOP_H
    yc = (y0 + y1) / 2
    ops = [('w', yc, 56, 0, 152), ('w', yc - 120, 36, 64, 140), ('w', yc + 120, 36, 64, 140), ('s', (x0 + x1) / 2, 40, 64, 140),
           ('n', (x0 + x1) / 2, 40, 64, 140)]
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 24, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    out += roof_rail(x0 - 8, y0 - 8, x1 + 8, y1 + 8, H)
    b = box((x0 + 140, yc - 100, 0), (x0 + 180, yc + 100, 48), X); b.part = 'counter'; out.append(b)
    return out


def shack(rect, door):
    x0, y0, x1, y1 = rect
    H = L.SHACK_H
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    c = {'n': xc, 's': xc, 'e': yc, 'w': yc}[door]
    ops = [(door, c, 48, 0, 128)]
    for s_ in 'nsew':
        if s_ != door:
            ops.append((s_, {'n': xc, 's': xc, 'e': yc, 'w': yc}[s_], 32, 64, 120))
    out = walls_rect(x0, y0, x1, y1, 0, H - 16, 16, ops)
    out += roof_slab(x0, y0, x1, y1, H)
    return out
