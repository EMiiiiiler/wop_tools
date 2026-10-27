"""Convex solids shared by build_aztec.py (as invisible common/weapclip collision) and az_models.py (as the visible,
lightmapped MD3 surfaces, see azlib.solids_mesh): the pyramid, the shrine, the jaguar temple, the ball court, the
eagle hall and the cantina. Every function returns a list of wopmap Brushes (texture 'x', replaced by the caller)
in world coordinates."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import hull, box, carve, ngon
import layout as L

X = 'common/caulk'


def frustum_box(cx, cy, hx0, hy0, z0, hx1, hy1, z1):
    """truncated rectangular pyramid: half sizes (hx0, hy0) at z0 and (hx1, hy1) at z1"""
    pts = [(cx + sx * hx0, cy + sy * hy0, z0) for sx in (-1, 1) for sy in (-1, 1)] + \
          [(cx + sx * hx1, cy + sy * hy1, z1) for sx in (-1, 1) for sy in (-1, 1)]
    return hull(pts, X, round_pts=False)


# ================================================================================================= great pyramid
def pyramid_cutters():
    cx, cy = L.PC
    cuts = []
    for side in (-1, 1):
        edge = cy + side * L.TOP_HALF
        far = cy + side * (L.H0 + 200)
        cuts.append(box((cx - L.STAIR_HW, min(edge, far), -8), (cx + L.STAIR_HW, max(edge, far), L.TOP_Z + 8), X))
    cuts.append(box((cx - L.H0 - 50, cy - L.TUNNEL_HW, -8), (cx + L.H0 + 50, cy + L.TUNNEL_HW, L.TUNNEL_H), X))
    cuts.append(box((cx - L.TOMB_HALF, cy - L.TOMB_HALF, -8), (cx + L.TOMB_HALF, cy + L.TOMB_HALF, L.TOMB_H), X))
    return cuts


def pyramid_tiers():
    """tier solids (talud frustum + tablero block per tier), carved by the stair notches, the tunnel and the tomb"""
    cx, cy = L.PC
    out = []
    cuts = pyramid_cutters()
    for k in range(L.NT):
        z0 = k * L.TIER_H
        h = L.tier_half(k); t = L.tablero_half(k)
        talud = frustum_box(cx, cy, h, h, z0, t, t, z0 + L.TALUD_H)
        tab = box((cx - t, cy - t, z0 + L.TALUD_H), (cx + t, cy + t, z0 + L.TIER_H), X)
        for b in (talud, tab):
            out += carve(b, cuts)
    return out


def pyramid_steps():
    cx, cy = L.PC
    out = []
    for side in (-1, 1):
        for (y0, y1, z) in L.stair_steps(side):
            out.append(box((cx - L.STAIR_HW, y0, 0), (cx + L.STAIR_HW, y1, z), X))
    return out


def in_pyr_interior(p):
    """point p (world) inside the tunnel or the tomb"""
    cx, cy = L.PC
    x, y, z = p
    if abs(y - cy) <= L.TUNNEL_HW + 0.5 and z <= L.TUNNEL_H + 0.5 and abs(x - cx) <= L.H0 + 1: return True
    if abs(x - cx) <= L.TOMB_HALF + 0.5 and abs(y - cy) <= L.TOMB_HALF + 0.5 and z <= L.TOMB_H + 0.5: return True
    return False


# ================================================================================================= shrine on the summit
def shrine():
    x0, y0, x1, y1 = L.SHRINE
    w = L.SHRINE_WALL; z0 = L.TOP_Z; zr = L.SHRINE_ROOF
    dx0, dx1, dh = L.SHRINE_DOOR
    cx = L.PC[0]
    out = []
    # walls (door in the south wall)
    out.append(box((x0, y0, z0), (cx + dx0, y0 + w, zr - 16), X))
    out.append(box((cx + dx1, y0, z0), (x1, y0 + w, zr - 16), X))
    out.append(box((cx + dx0, y0, z0 + dh), (cx + dx1, y0 + w, zr - 16), X))
    out.append(box((x0, y1 - w, z0), (x1, y1, zr - 16), X))
    out.append(box((x0, y0 + w, z0), (x0 + w, y1 - w, zr - 16), X))
    out.append(box((x1 - w, y0 + w, z0), (x1, y1 - w, zr - 16), X))
    # roof slab (overhangs 16)
    out.append(box((x0 - 16, y0 - 16, zr - 16), (x1 + 16, y1 + 16, zr), X))
    return out


def shrine_inside(p):
    x0, y0, x1, y1 = L.SHRINE; w = L.SHRINE_WALL
    return x0 + w - 0.5 <= p[0] <= x1 - w + 0.5 and y0 + w - 0.5 <= p[1] <= y1 - w + 0.5 and L.TOP_Z <= p[2] <= L.SHRINE_ROOF - 15


# ================================================================================================= jaguar temple
def jaguar():
    """platform (talud + tablero), stair east, building with a door east and a flat roof"""
    cx, cy = L.JAG
    hx, hy, H = L.JAG_PLAT
    out = []
    talud = frustum_box(cx, cy, hx, hy, 0, hx - 32, hy - 32, 40)
    tab = box((cx - hx + 32, cy - hy + 32, 40), (cx + hx - 32, cy + hy - 32, H), X)
    out += carve(talud, [box((cx + hx - 33, cy - 96, -8), (cx + hx + 8, cy + 96, 48), X)]) + [tab]
    # stair east (10 steps of 16 rising west to the tablero edge)
    n = H // 16
    xe = cx + hx - 32
    for j in range(n):
        xa = xe + L.JAG_STAIR_RUN * (n - j - 1); xb = xa + L.JAG_STAIR_RUN
        out.append(box((xa, cy - 96, 0), (xb, cy + 96, 16 * (j + 1)), X))
    # building
    bx0, by0, bx1, by1 = (cx + L.JAG_BLD[0], cy + L.JAG_BLD[1], cx + L.JAG_BLD[2], cy + L.JAG_BLD[3])
    w = 32; zr = L.JAG_ROOF; z0 = H
    out.append(box((bx0, by0, z0), (bx1, by0 + w, zr - 16), X))
    out.append(box((bx0, by1 - w, z0), (bx1, by1, zr - 16), X))
    out.append(box((bx0, by0 + w, z0), (bx0 + w, by1 - w, zr - 16), X))
    # east wall with a door (96 wide, 128 high)
    out.append(box((bx1 - w, by0 + w, z0), (bx1, cy - 48, zr - 16), X))
    out.append(box((bx1 - w, cy + 48, z0), (bx1, by1 - w, zr - 16), X))
    out.append(box((bx1 - w, cy - 48, z0 + 128), (bx1, cy + 48, zr - 16), X))
    out.append(box((bx0 - 16, by0 - 16, zr - 16), (bx1 + 16, by1 + 16, zr), X))
    return out


def jag_inside(p):
    cx, cy = L.JAG
    bx0, by0, bx1, by1 = (cx + L.JAG_BLD[0] + 32, cy + L.JAG_BLD[1] + 32, cx + L.JAG_BLD[2] - 32, cy + L.JAG_BLD[3] - 32)
    return bx0 - 0.5 <= p[0] <= bx1 + 0.5 and by0 - 0.5 <= p[1] <= by1 + 0.5 and L.JAG_PLAT[2] - 0.5 <= p[2] <= L.JAG_ROOF - 15


# ================================================================================================= ball court
def ballcourt():
    """two long side structures (sloped bench + vertical wall + walkable top) along the alley, outer stairs up each,
    low end-zone walls"""
    ax0, ay0, ax1, ay1 = L.BC_ALLEY
    bd, br = L.BC_BENCH; Z = L.BC_WALL_Z; T = L.BC_TOP_W
    out = []
    for s in (-1, 1):
        ye = ay1 if s > 0 else ay0                      # alley edge
        yb = ye + s * bd; yo = yb + s * T              # bench top edge (wall face), outer face
        # bench: wedge from the alley edge (z 0) up to br at the wall face
        out.append(hull([(x, y, z) for x in (ax0, ax1) for (y, z) in ((ye, 0), (yb, 0), (yb, br))], X, round_pts=False))
        out.append(box((ax0, min(yb, yo), 0), (ax1, max(yb, yo), Z), X))
        # outer stair (rising toward the court centre in x), outside the wall
        n = Z // 16
        ys = (yo, yo + s * 80)
        for j in range(n):
            xa = L.BC[0] - 64 - 24 * (n - j); xb = xa + 24
            out.append(box((xa, min(ys), 0), (xb, max(ys), 16 * (j + 1)), X))
        out.append(box((L.BC[0] - 64, min(ys), 0), (L.BC[0] + 64, max(ys), Z), X))       # landing
    # end zones: low walls (cover) at the far ends
    for xe in (ax0 - L.BC_END, ax1 + L.BC_END):
        xs = (xe - 32, xe) if xe < ax0 else (xe, xe + 32)
        out.append(box((xs[0], ay0 - 192, 0), (xs[1], ay1 + 192, 64), X))
    return out


# ================================================================================================= hall of the eagle warriors
HALL_COLS_X = list(range(-576, 577, 192))


def hall():
    x0, y0, x1, y1 = L.HALL
    Z = L.HALL_Z
    out = [box((x0, y0, Z - 24), (x1, y1, Z), X)]              # roof slab
    out.append(box((x0, y1 - 32, 0), (x1, y1, Z - 24), X))       # back wall (north)
    # bench along the back wall (cover inside)
    out.append(box((x0 + 32, y1 - 96, 0), (x1 - 32, y1 - 32, 32), X))
    # stair at the east end rising north, outside the hall
    n = Z // 16
    for j in range(n):
        ya = y0 + 22 * j - 0; yb = ya + 22
        out.append(box((x1, ya, 0), (x1 + 96, yb, 16 * (j + 1)), X))
    return out


def hall_columns():
    """(x, y) of the serpent columns under the front edge and the middle of the roof"""
    x0, y0, x1, y1 = L.HALL
    out = []
    for x in HALL_COLS_X:
        out.append((x, y0 + 48))
    return out


# ================================================================================================= cantina
def cantina():
    x0, y0, x1, y1 = L.CAN
    Z = L.CAN_H; w = 24
    out = []
    # walls: open serving window on the east side, door on the north side
    out.append(box((x0, y0, 0), (x1, y0 + w, Z - 16), X))                        # south
    out.append(box((x0, y0 + w, 0), (x0 + w, y1, Z - 16), X))                    # west
    out.append(box((x0 + w, y1 - w, 0), (x0 + 200, y1, Z - 16), X))              # north, left of the door
    out.append(box((x0 + 296, y1 - w, 0), (x1, y1, Z - 16), X))                  # north, right of the door
    out.append(box((x0 + 200, y1 - w, 144), (x0 + 296, y1, Z - 16), X))          # lintel
    out.append(box((x1 - w, y0 + w, 0), (x1, y0 + 120, Z - 16), X))              # east: pier, window, pier
    out.append(box((x1 - w, y1 - 120, 0), (x1, y1 - w, Z - 16), X))
    out.append(box((x1 - w, y0 + 120, 0), (x1, y1 - 120, 64), X))                # counter under the window
    out.append(box((x1 - w, y0 + 120, 160), (x1, y1 - 120, Z - 16), X))          # header over the window
    out.append(box((x0 - 8, y0 - 8, Z - 16), (x1 + 8, y1 + 8, Z), X))            # roof terrace slab
    # outside stair up the west side, rising north, along x0 - 104 .. x0 - 8
    n = Z // 16
    for j in range(n):
        ya = y0 - 64 + 24 * j; yb = ya + 24
        out.append(box((x0 - 104, ya, 0), (x0 - 8, yb, 16 * (j + 1)), X))
    return out


def cantina_inside(p):
    x0, y0, x1, y1 = L.CAN
    return x0 + 23.5 <= p[0] <= x1 - 23.5 and y0 + 23.5 <= p[1] <= y1 - 23.5 and 0 <= p[2] <= L.CAN_H - 15
