"""Convex solids shared by build_bakery.py (invisible common/weapclip collision) and bk_models.py (the visible,
lightmapped MD3 surfaces via bklib.solids_mesh): deck oven, counters, show cake, floor mixer, display cabinet,
cool room, cooling racks and the flour bin. Every function returns wopmap Brushes in world coordinates with a
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


# ================================================================================================= deck oven
def oven():
    x0, xf = L.OV_X0, L.OV_FRONT
    y0, y1 = L.OV_Y0, L.OV_Y1
    t = L.OV_SIDE
    xi = x0 + t                      # inner back face
    xfi = xf - L.OV_FRONT_T          # inner face of the front posts
    out = []
    out.append(tbox((x0, y0, 0), (xf, y0 + t, L.OV_TOP), 'ov_side'))
    out.append(tbox((x0, y1 - t, 0), (xf, y1, L.OV_TOP), 'ov_side'))
    out.append(tbox((x0, y0 + t, 0), (xi, y1 - t, L.OV_TOP), 'ov_back'))
    for (za, zb) in ((L.PROOF_TOP, L.DECK1), (L.DECK1 + L.DECK_H, L.DECK2), (L.DECK2 + L.DECK_H, L.OV_TOP)):
        out.append(tbox((xi, y0 + t, za), (xf, y1 - t, zb), 'ov_slab'))
    # front posts: proofer (sides only), decks (sides + centre pillar)
    pm = L.PROOF_MOUTH
    for (ya, yb) in ((y0 + t, pm[0]), (pm[1], y1 - t)):
        if yb - ya > 0.5: out.append(tbox((xfi, ya, 0), (xf, yb, L.PROOF_TOP), 'ov_post'))
    for zd in (L.DECK1, L.DECK2):
        cuts = [y0 + t] + [v for m in L.MOUTHS for v in m] + [y1 - t]
        for k in range(0, len(cuts), 2):
            ya, yb = cuts[k], cuts[k + 1]
            if yb - ya > 0.5: out.append(tbox((xfi, ya, zd), (xf, yb, zd + L.DECK_H), 'ov_post'))
    # hinged-down open doors in front of each mouth (walkable ledges)
    for zd in (L.DECK1, L.DECK2):
        for (ya, yb) in L.MOUTHS:
            out.append(tbox((xf, ya + 8, zd - L.DOOR_T), (xf + L.DOOR_D, yb - 8, zd), 'ov_door'))
    fx, fy, fr = L.FLUE
    out.append(prism_n(fx, fy, fr, L.OV_TOP, L.CEIL, 16, 11.25, 'ov_flue'))
    return out


# ================================================================================================= counters
def _divider_x(xa, xb, doors=True):
    """north-counter divider panel (x span xa..xb) from the front face to the back panel, with tunnel doorways"""
    yf, yb = L.N_FRONT, L.HY - L.N_BACK
    d0, d1 = L.DOORWAY
    top = L.WORK - L.WORK_T
    if not doors:
        return [tbox((xa, yf, 0), (xb, yb, top), 'ct_side')]
    return [tbox((xa, yf, 0), (xb, d0, top), 'ct_side'), tbox((xa, d1, 0), (xb, yb, top), 'ct_side'),
            tbox((xa, d0, L.DOOR_LOW_TOP), (xb, d1, L.SHELF), 'ct_side'),
            tbox((xa, d0, L.SHELF + 240), (xb, d1, top), 'ct_side')]


def _divider_y(ya, yb, doors=True):
    xf, xb = L.E_FRONT, L.HX - L.N_BACK
    d0, d1 = L.DOORWAY_E
    top = L.WORK - L.WORK_T
    if not doors:
        return [tbox((xf, ya, 0), (xb, yb, top), 'ct_side')]
    return [tbox((xf, ya, 0), (d0, yb, top), 'ct_side'), tbox((d1, ya, 0), (xb, yb, top), 'ct_side'),
            tbox((d0, ya, L.DOOR_LOW_TOP), (d1, yb, L.SHELF), 'ct_side'),
            tbox((d0, ya, L.SHELF + 240), (d1, yb, top), 'ct_side')]


def n_bays():
    """x spans of the north counter bays between the dividers"""
    d = L.N_DIVS
    return [(d[k][1], d[k + 1][0]) for k in range(len(d) - 1)]


def e_bays():
    d = L.E_DIVS + [(L.N_FRONT, L.N_FRONT)]
    return [(d[k][1], d[k + 1][0]) for k in range(len(d) - 1)]


def counters():
    out = []
    top = L.WORK - L.WORK_T
    # north counter: back panel, dividers, shelves, the closed corner cabinet, worktop
    out.append(tbox((L.N_X0, L.HY - L.N_BACK, 0), (L.N_CORNER[0], L.HY, top), 'ct_back'))
    for k, (xa, xb) in enumerate(L.N_DIVS):
        out += _divider_x(xa, xb, doors=(k < len(L.N_DIVS) - 1))
    for (xa, xb) in n_bays():
        out.append(tbox((xa, L.N_FRONT, L.SHELF - L.SHELF_T), (xb, L.HY - L.N_BACK, L.SHELF), 'ct_shelf'))
    out.append(tbox((L.N_CORNER[0] + 32, L.N_FRONT, 0), (L.HX, L.HY, top), 'ct_closed'))
    out.append(tbox((L.N_X0 - L.OVERHANG, L.N_FRONT - L.OVERHANG, top), (L.HX, L.HY, L.WORK), 'ct_top'))
    # east counter
    out.append(tbox((L.HX - L.N_BACK, L.E_Y0, 0), (L.HX, L.N_FRONT, top), 'ct_back'))
    for (ya, yb) in L.E_DIVS:
        out += _divider_y(ya, yb)
    for (ya, yb) in e_bays():
        out.append(tbox((L.E_FRONT, ya, L.SHELF - L.SHELF_T), (L.HX - L.N_BACK, yb, L.SHELF), 'ct_shelf'))
    out.append(tbox((L.E_FRONT - L.OVERHANG, L.E_Y0 - L.OVERHANG, top), (L.HX, L.N_FRONT - L.OVERHANG, L.WORK), 'ct_top'))
    # the wall shelf over the north counter
    x0, x1, yf, zt = L.WALL_SHELF
    out.append(tbox((x0, yf, zt - L.WALL_SHELF_T), (x1, L.HY, zt), 'ws_board'))
    return out


# ================================================================================================= the show cake
def cake():
    cx, cy = L.CAKE
    n, ph = L.CAKE_N, L.CAKE_PHASE
    out = []
    r1, z0, z1 = L.TIERS[0]
    for k in range(n):
        a0 = ph + 360 * k / n; a1 = a0 + 360 / n
        am = ((a0 + a1) / 2 + 180) % 360 - 180
        if L.CAVE[0] < am < L.CAVE[1]: continue
        out.append(ring_seg(cx, cy, a0, a1, 0, r1, z0, z1, part='tier1'))
    for i, (r, za, zb) in enumerate(L.TIERS[1:]):
        out.append(prism_n(cx, cy, r, za, zb, n, ph, part=f'tier{i + 2}'))
    # sugar-cube stair up to tier 1 (south)
    yt = cy - L.apothem(r1)
    out += stair_run(cx - L.STAIR_W / 2, yt - 448, cx + L.STAIR_W / 2, yt, 0, z1, 'n', part='cake_stair')
    # topper: the chocolate plaque on two posts (north half of the top) and three strawberries
    zt = L.TIERS[2][2]
    out.append(tbox((cx - 120, cy + 60, zt), (cx + 120, cy + 76, zt + 150), 'topper'))
    for (dx, dy) in ((-120, -40), (130, -10), (0, 130)):
        out.append(prism_n(cx + dx, cy + dy, 30, zt, zt + 70, 8, 22.5, part='berry'))
    return out


def cake_cave_rect():
    """the wedge footprint of the missing slice (for keep-outs)"""
    cx, cy = L.CAKE
    return (cx, cy - 200, cx + L.TIERS[0][0], cy + 200)


# ================================================================================================= floor mixer
def mixer():
    cx, cy = L.MIX
    out = []
    n = 24
    for k in range(n):
        a0 = 360 * k / n; a1 = a0 + 360 / n
        out.append(ring_seg(cx, cy, a0, a1, L.BOWL_R0, L.BOWL_R0 + L.BOWL_T, L.BOWL_Z0, L.BOWL_Z1,
                            r0_top=L.BOWL_R1, r1_top=L.BOWL_R1 + L.BOWL_T, part='bowl'))
    out.append(prism_n(cx, cy, L.BOWL_R0 + L.BOWL_T, L.BOWL_Z0 - 16, L.BOWL_Z0, n, 0, part='bowl_bot'))
    x0, y0, x1, y1 = L.MIX_COL
    out.append(tbox((x0 - 30, y0 - 20, 0), (x1 + 30, y1 + 10, 40), 'mx_base'))
    out.append(tbox((x0, y0, 40), (x1, y1, L.MIX_HEAD[4]), 'mx_col'))
    hx0, hy0, hx1, hy1, hz0, hz1 = L.MIX_HEAD
    out.append(tbox((hx0, hy0, hz0), (hx1, hy1, hz1), 'mx_head'))
    # cradle arms from the column round both sides of the bowl
    for s in (-1, 1):
        xa = cx + s * 214
        out.append(tbox((min(xa, xa + s * 24), cy - 60, 470), (max(xa, xa + s * 24), y0 - 24, 506), 'mx_arm'))
    out.append(tbox((cx - 238, y0 - 24, 470), (cx + 238, y0, 506), 'mx_arm'))
    return out


# ================================================================================================= display cabinet
def display_cabinet():
    x0, y0, x1, y1 = L.DC
    g = L.DC_GLASS_T
    out = [tbox((x0, y0, 0), (x1, y1, L.DC_PLINTH), 'dc_plinth')]
    out.append(tbox((x0, y0, L.DC_PLINTH), (x1, y0 + g, L.DC_TOP - 32), 'dc_glass'))
    for (xa, xb) in ((x0, x0 + g), (x1 - g, x1)):
        out.append(tbox((xa, y0 + g, L.DC_PLINTH), (xb, y1, L.DC_TOP - 32), 'dc_glass'))
    out.append(tbox((x0 + g, y0 + g, L.DC_SHELF - 16), (x1 - g, y1 - 40, L.DC_SHELF), 'dc_shelf'))
    out.append(tbox((x0 - 16, y0 - 16, L.DC_TOP - 32), (x1 + 16, y1 + 16, L.DC_TOP), 'dc_top'))
    for (xa, xb) in L.DC_STEPS:
        out += stair_run(xa, y1, xb, y1 + 256, 0, L.DC_PLINTH, 's', part='dc_step')
    return out


# ================================================================================================= cool room
def cool_room():
    x0, y0, x1, y1 = L.CR
    t = L.CR_T
    dx, dhw, dh = L.CR_DOOR
    out = walls_rect(x0, y0, x1, y1, 0, L.CR_H - 32, t, [('n', dx, dhw, 0, dh)], part='cr_wall')
    out.append(tbox((x0, y0, L.CR_H - 32), (x1, y1, L.CR_H), 'cr_roof'))
    out.append(tbox((dx + dhw + 8, y1, 0), (dx + 3 * dhw + 8, y1 + 12, dh + 16), 'cr_door'))      # the sliding door, pushed open
    # wire shelving along the east wall (two shelves) on four posts
    sx0, sx1 = x1 - t - 176, x1 - t - 16
    sy0, sy1 = y0 + t + 80, y1 - t - 200
    for zz in (240, 480):
        out.append(tbox((sx0, sy0, zz - 8), (sx1, sy1, zz), 'cr_shelf'))
    for (px, py) in ((sx0, sy0), (sx1 - 8, sy0), (sx0, sy1 - 8), (sx1 - 8, sy1 - 8)):
        for (za, zb) in ((0, 232), (240, 472), (480, 560)):
            out.append(tbox((px, py, za), (px + 8, py + 8, zb), 'cr_post'))
    return out


# ================================================================================================= cooling racks
def rack(cx, cy, yaw):
    w, d = (L.RACK_W, L.RACK_D) if yaw % 180 == 0 else (L.RACK_D, L.RACK_W)
    x0, y0, x1, y1 = cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2
    out = []
    levels = L.RACK_TRAYS + [L.RACK_TOP]
    for (px, py) in ((x0, y0), (x1 - 16, y0), (x0, y1 - 16), (x1 - 16, y1 - 16)):
        zprev = 0
        for zl in levels:
            if zl - 8 - zprev > 0.5: out.append(tbox((px, py, zprev), (px + 16, py + 16, zl - 8), 'rk_post'))
            zprev = zl
    for zl in levels:
        out.append(tbox((x0, y0, zl - 8), (x1, y1, zl), 'rk_tray' if zl != L.RACK_TOP else 'rk_top'))
    return out


def racks():
    out = []
    for (x, y, a) in L.RACKS: out += rack(x, y, a)
    return out


def rack_rect(i):
    cx, cy, yaw = L.RACKS[i]
    w, d = (L.RACK_W, L.RACK_D) if yaw % 180 == 0 else (L.RACK_D, L.RACK_W)
    return (cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)


# ================================================================================================= flour bin
def flour_bin():
    x0, y0, x1, y1 = L.BIN
    out = walls_rect(x0, y0, x1, y1, 0, L.BIN_H, L.BIN_T, part='bin_wall')
    out.append(tbox((x0 + L.BIN_T, y0 + L.BIN_T, 0), (x1 - L.BIN_T, y1 - L.BIN_T, L.BIN_FLOOR), 'bin_floor'))
    sx0, sy0, sx1, sy1 = L.BIN_STAIR
    out += stair_run(sx0, sy0, sx1, sy1, 0, L.BIN_H, 'n', part='bin_stair')
    return out
