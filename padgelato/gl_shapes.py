"""Convex solids shared by build_gelato.py (invisible common/weapclip collision) and gl_models.py (the visible,
lightmapped MD3 surfaces via bklib.solids_mesh): the giant cone, gelato counter, soft-serve machine, milkshake bar,
walk-in freezer, chest freezer, cart and jars. Every function returns wopmap Brushes in world coordinates with a
`part` tag (texture 'common/caulk', replaced by the caller)."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import hull, box, sub_rects
import layout as L

X = 'common/caulk'


def tag(b, part):
    b.part = part
    return b


def tbox(mn, mx, part):
    return tag(box(mn, mx, X), part)


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, r1_top=None, r0_top=None, part='ring'):
    pts = []
    for a in (a0, a1):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        for (r, z) in ((r0, z0), (r1, z0), (r0 if r0_top is None else r0_top, z1), (r1 if r1_top is None else r1_top, z1)):
            pts.append((cx, cy, z) if r < 0.5 else (cx + r * c, cy + r * s, z))
    return tag(hull(pts, X, round_pts=False), part)


def prism_n(cx, cy, r, z0, z1, n=16, phase=0.0, part='cyl'):
    pts = []
    for k in range(n):
        a = math.radians(phase + 360 * k / n)
        pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z0), (cx + r * math.cos(a), cy + r * math.sin(a), z1)]
    return tag(hull(pts, X, round_pts=False), part)


def stair_run(x0, y0, x1, y1, z0, ztop, run_dir, part='stair'):
    """straight flight rising toward run_dir (n/s/e/w), solid steps down to z0"""
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
        b = tbox((round(r[0], 2), round(r[1], 2), z0), (round(r[2], 2), round(r[3], 2), zt), part)
        b.step = i
        out.append(b)
    return out


def walls_rect(x0, y0, x1, y1, z0, z1, t, openings=(), part='wall', skip=()):
    """four walls of thickness t inside the footprint; openings [(side, c, half_w, zb, zt)]; corners belong to n/s"""
    out = []
    spec = {'s': (x0, x1, y0, y0 + t, 'x'), 'n': (x0, x1, y1 - t, y1, 'x'), 'w': (x0, x0 + t, y0 + t, y1 - t, 'y'),
            'e': (x1 - t, x1, y0 + t, y1 - t, 'y')}
    for side, (ax0, ax1, ay0, ay1, ax) in spec.items():
        if side in skip: continue
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
                br = box((a, ay0, za), (b, ay1, zb_), X) if ax == 'x' else box((ax0, a, za), (ax1, b, zb_), X)
                br.part = part; br.side = side
                out.append(br)
    return out




def frustum(cx, cy, r0, r1, z0, z1, n=24, phase=0.0, part='frustum'):
    pts = []
    for k in range(n):
        a = math.radians(phase + 360 * k / n)
        pts += [(cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0), (cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1)]
    return tag(hull(pts, X, round_pts=False), part)


# ================================================================================================= the giant cone
def tower():
    cx, cy = L.TOWER
    n, ph = L.TW_N, 7.5
    sr0, sr1, sh = L.STAND
    out = [frustum(cx, cy, sr0, sr1, 0, sh, n, ph, 'stand'),
           frustum(cx, cy, L.CONE_R0, L.CONE_R1, L.CONE_Z0, L.CONE_Z1, n, ph, 'cone'),
           prism_n(cx, cy, L.RIM_R, L.CONE_Z1, L.RIM_Z, n, ph, 'rim')]
    for (z0, z1, r) in L.SCOOP_TERR:
        out.append(prism_n(cx, cy, r, z0, z1, n, ph, 'scoop'))
    out.append(prism_n(cx, cy, 170, 1330, 1560, 16, 11.25, 'scoop2'))
    out.append(prism_n(cx, cy, 110, 1640, 1820, 12, 15, 'scoop3'))
    return out


# ================================================================================================= gelato counter
def gelato_counter():
    x0, y0, x1, y1 = L.GC
    g, t = 16.0, 16.0
    out = [tbox((x0, y0, 0), (x1, y1, L.GC_PLINTH), 'gc_plinth')]
    out.append(tbox((x0, y0, L.GC_PLINTH), (x1, y0 + g, L.GC_TUB), 'gc_glass'))
    out.append(tbox((x0, y0 + g, L.GC_PLINTH), (x0 + t, y1, L.GC_TUB), 'gc_end'))
    out.append(tbox((x1 - t, y0 + g, L.GC_PLINTH), (x1, y1, L.GC_TUB), 'gc_end'))
    out.append(tbox((x0 + t, y1 - t, L.GC_PLINTH), (x1 - t, y1, L.GC_TUB), 'gc_back'))
    holes = [(xa, L.GC_TUB_Y[0], xb, L.GC_TUB_Y[1]) for (xa, xb) in L.GC_TUBS]
    for r in sub_rects((x0, y0, x1, y1), holes):
        out.append(tbox((r[0], r[1], L.GC_TUB), (r[2], r[3], L.GC_DECK), 'gc_deck'))
    for k, (xa, xb) in enumerate(L.GC_TUBS):
        b = tbox((xa, L.GC_TUB_Y[0], L.GC_PAN_Z), (xb, L.GC_TUB_Y[1], L.GC_TUB), 'gc_tub')
        b.tub = k
        out.append(b)
    sx0, sy0, sx1, sy1 = L.GC_STAIR_W
    out += stair_run(sx0, sy0, sx1, sy1, 0, L.GC_DECK, 'e', part='gc_stair')
    sx0, sy0, sx1, sy1 = L.GC_STAIR_E
    out += stair_run(sx0, sy0, sx1, sy1, 0, L.GC_DECK, 'w', part='gc_stair')
    hx0, hx1, hy, hz = L.SHELF
    out.append(tbox((hx0, hy, hz - L.SHELF_T), (hx1, L.HY, hz), 'shelf'))
    for zz in (300, 600):
        out.append(tbox((-1300, 1888, zz - 16), (1300, L.HY, zz), 'aisle_shelf'))
    for xx in (-1300, -650, 0, 650, 1284):
        for (za, zb) in ((0, 284), (300, 584)):
            out.append(tbox((xx, 2032, za), (xx + 16, L.HY, zb), 'aisle_post'))
    return out


# ================================================================================================= soft-serve machine
def softserve():
    x0, y0, x1, y1 = L.SS
    t = L.SS_T
    m0, m1, mh = L.SS_MOUTH
    out = [tbox((x0, y0, 0), (x1, y0 + t, L.SS_CAB), 'ss_wall'), tbox((x0, y1 - t, 0), (x1, y1, L.SS_CAB), 'ss_wall'),
           tbox((x0, y0 + t, 0), (x0 + t, y1 - t, L.SS_CAB), 'ss_wall')]
    for (ya, yb) in ((y0 + t, m0), (m1, y1 - t)):
        out.append(tbox((x1 - t, ya, 0), (x1, yb, mh), 'ss_post'))
    out.append(tbox((x1 - t, y0 + t, mh), (x1, y1 - t, L.SS_CAB), 'ss_post'))
    out.append(tbox((x0, y0, L.SS_CAB), (L.SS_LEDGE, y1, L.SS_DECK), 'ss_deck'))
    out.append(tbox((x0, y0, L.SS_DECK), (L.SS_BODY_X, y1, L.SS_TOP), 'ss_body'))
    for y in L.SS_NOZZLES:
        out.append(tbox((L.SS_BODY_X, y - 60, 700), (L.SS_BODY_X + 90, y + 60, 800), 'ss_nozzle'))
    for y in (L.SS_NOZZLES[0], L.SS_NOZZLES[2]):
        out.append(prism_n(-1790, y, 96, L.SS_DECK, L.SS_DECK + 260, 12, 15, 'ss_cone'))
    out.append(prism_n(-1790, 0, 76, L.SS_DECK, L.SS_DECK + 150, 12, 15, 'ss_cup'))
    sx0, sy0, sx1, sy1 = L.SS_STAIR
    out += stair_run(sx0, sy0, sx1, sy1, 0, L.SS_DECK, 's', part='ss_stair')
    return out


# ================================================================================================= milkshake bar + glass
def bar():
    x0, y0, x1, y1 = L.BAR
    return [tbox((x0 + 16, y0, 0), (x1, y1, L.BAR_Z - 32), 'bar_body'),
            tbox((x0 - 20, y0, L.BAR_Z - 32), (x1, y1, L.BAR_Z), 'bar_top')]


def glass():
    gx, gy = L.GLASS
    out = [prism_n(gx, gy, L.GLASS_R, 0, L.GLASS_H, 24, 7.5, 'glass')]
    for (z0, z1, r) in L.GLASS_TERR:
        out.append(prism_n(gx, gy, r, z0, z1, 24, 7.5, 'cream'))
    return out


# ================================================================================================= walk-in freezer
def freezer():
    x0, y0, x1, y1 = L.FZ
    t = L.FZ_T
    dx, dhw, dh = L.FZ_DOOR
    out = walls_rect(x0, y0, x1, y1, 0, L.FZ_H - 32, t, [('n', dx, dhw, 0, dh)], part='fz_wall')
    out.append(tbox((x0, y0, L.FZ_H - 32), (x1, y1, L.FZ_H), 'fz_roof'))
    out.append(tbox((dx + dhw + 8, y1, 0), (dx + 3 * dhw + 8, y1 + 12, dh + 16), 'fz_door'))
    sx0, sx1 = x1 - t - 176, x1 - t - 16
    sy0, sy1 = y0 + t + 400, y1 - t - 120
    for zz in (240, 480):
        out.append(tbox((sx0, sy0, zz - 8), (sx1, sy1, zz), 'fz_shelf'))
    for (px, py) in ((sx0, sy0), (sx1 - 8, sy0), (sx0, sy1 - 8), (sx1 - 8, sy1 - 8)):
        for (za, zb) in ((0, 232), (240, 472), (480, 560)):
            out.append(tbox((px, py, za), (px + 8, py + 8, zb), 'fz_post'))
    mx, my, mr, mh = L.MYSTERY
    for k in range(16):
        out.append(ring_seg(mx, my, 22.5 * k, 22.5 * (k + 1), mr - 20, mr, 0, mh, part='mys_wall'))
    out.append(prism_n(mx, my, mr - 20, 0, 8, 16, 0, 'mys_floor'))
    return out


# ================================================================================================= chest freezer
def chest():
    x0, y0, x1, y1 = L.CF
    out = walls_rect(x0, y0, x1, y1, 0, L.CF_RIM, L.CF_T, part='cf_wall')
    out.append(tbox((x0 + L.CF_T, y0 + L.CF_T, 0), (x1 - L.CF_T, y1 - L.CF_T, L.CF_FLOOR), 'cf_floor'))
    sx0, sy0, sx1, sy1 = L.CF_STAIR_OUT
    out += stair_run(sx0, sy0, sx1, sy1, 0, L.CF_RIM, "s", part="cf_stair")
    sx0, sy0, sx1, sy1 = L.CF_STAIR_IN
    out += stair_run(sx0, sy0, sx1, sy1, L.CF_FLOOR, L.CF_RIM, 'n', part='cf_stair_in')
    out.append(tbox((x0, y0, L.CF_RIM), (x1, y0 + L.CF_T, L.CF_RIM + 400), 'cf_lid'))
    return out


# ================================================================================================= cart + jars
def cart():
    cx, cy = L.CART
    w, d, h = L.CART_W, L.CART_D, L.CART_H
    return [tbox((cx - w / 2, cy - d / 2, 0), (cx + w / 2, cy + d / 2, h), 'cart'),
            prism_n(cx, cy, 10, h, 1000, 8, 22.5, 'cart_pole')]


def jars():
    return [prism_n(x, y, L.JAR_R, 0, L.JAR_H, 16, 0, 'jar') for (x, y) in L.JARS]
