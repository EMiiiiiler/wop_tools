"""Shared layout constants for wop_moosefalls (Moose Mountain Falls): used by build_moose.py (brushes, entities)
and moose_models.py (MD3 geometry), so the visible models and the invisible collision line up.

Human scale (~32u per metre, player 56u). x east, y north, deck z 0, water surface z -16.
"""
import math
import numpy as np

# ---------------------------------------------------------------- the lodge hall
HX, HY = 2048, 1664            # inner half extents (walls at x +-HX, y +-HY)
WALL = 32
EAVE, RIDGE = 576, 1344        # roof underside z at the long walls and at the ridge (y 0)
SKY_Y = 320                    # ridge skylight strip y -SKY_Y..SKY_Y
ROOF_T = 16


def roof_z(y):
    """underside of the roof at y"""
    return RIDGE - (RIDGE - EAVE) * min(abs(y), HY) / HY


WATER = -16                    # water surface everywhere
SLAB_BOT = -256

# ---------------------------------------------------------------- tree island + lazy river
C = (0.0, -64.0)               # island centre
R_ISL, R_RIV = 448, 736        # island edge, river outer edge
RIV_FLOOR = -64                # 48 deep: wading
TRUNK_VIS = [(0, 90), (24, 76), (90, 64), (300, 58), (600, 52), (900, 42), (1100, 30), (1260, 10), (1300, 0)]  # (z, r) MD3
TRUNK_COL = 48                 # collision radius (16-gon) up to TRUNK_COL_Z
TRUNK_COL_Z = 1000
STAIR_R = (112, 232)
STAIR_N = 28                   # 16u steps -> nest deck at 448
STAIR_A0 = 120.0               # angle (deg, CCW from +x) of the first step's start edge
STAIR_DA = 12.0                # degrees per step
NEST_Z = 448                   # treehouse deck top
NEST_R = (64, 384)
NEST_HATCH = (STAIR_A0 + 21 * STAIR_DA, STAIR_A0 + 28 * STAIR_DA + 8)   # hatch sector over the last steps (deg)
NEST_HATCH_R = 248
CROW_Z = 832                   # crow's nest top
CROW_R = (56, 176)

# ---------------------------------------------------------------- activity pool + grotto (north-west)
POOL_A = [(-1952, 256, -1536, 1088), (-1536, 256, -832, 1472)]        # convex pieces (x0, y0, x1, y1)
POOL_DEEP = -224
POOL_SHALLOW = -64
DEEP_X1, SHALLOW_X0 = -1472, -1152                                     # slope between deep and shallow floors
BEACH_X0 = -960                                                        # beach ramp from shallow floor up to the deck at x -832
ROCK = (-2048, 1088, -1536, 1664)                                      # grotto rock mass footprint
ROCK_TOP = 448
CAVE = (-1952, 1184, -1632, 1600)                                      # cave chamber (floor 0, ceiling CAVE_Z)
CAVE_Z = 160
MOUTH = (-1856, 1088, -1696, 1184)                                     # swim-in mouth behind the waterfall
CAVE_EXIT = (-1632, 1472, -1536, 1600)                                 # dry tunnel east to the deck

# ---------------------------------------------------------------- plunge pool (east)
POOL_P = (1216, -480, 1824, 400)
POOL_P_FLOOR = -176

# ---------------------------------------------------------------- Timber Peak slide tower (north-east)
TW = (1152, 896, 1536, 1280)                                           # log core
TW_Z = 480                                                             # platform top
TW_BAND = 96
TW_ROOF_EAVE, TW_ROOF_RIDGE = 608, 704

# ---------------------------------------------------------------- snack bar (north)
SB = (-448, 1344, 448, HY)                                             # building
SB_H = 256                                                             # roof deck top
SB_PORCH = (-448, 1152, 448, 1344)
SB_PORCH_EAVE = 192

# ---------------------------------------------------------------- Tiny Timbers play structure (south-east)
TT_PAD = (512, -1600, 1856, -640)                                      # splash pad floor
TT_BASE = (896, -1280, 1376, -960)
TT_DECK = 160
TT_TOWER = (1088, -1168, 1184, -1072)
TT_TOP = 384                                                           # tower top platform

# ---------------------------------------------------------------- hollow stump lookout (south-west)
ST_C = (-1280.0, -960.0)
ST_R, ST_RIN, ST_H = 336, 256, 576
ST_DOOR = (1, 2, 240)                                                  # 16-gon segments of the doorway (faces ENE), height

# ---------------------------------------------------------------- columns + rafters
RAFTER_X = (-1536, -768, 0, 768, 1536)
COLUMNS = [(-768, 1280), (768, 1280), (-768, -1280), (0, -1280), (768, -1280), (1536, -1312), (-1792, -320), (-1792, -1088),
           (1856, 1500)]
DUCT_Y = (1440, -1440)
DUCT_Z = 600


# ---------------------------------------------------------------- slide paths (floor centre line)
def _bez(p0, p1, p2, p3, n):
    out = []
    for t in np.linspace(0, 1, n):
        out.append(((1 - t) ** 3) * np.array(p0) + 3 * ((1 - t) ** 2) * t * np.array(p1) + 3 * (1 - t) * t * t * np.array(p2) + t ** 3 * np.array(p3))
    return out


def _with_z(xy, z0, z1, ease_end=0.0):
    """assign floor z by arc length (linear from z0 to z1)"""
    xy = [np.asarray(p, float) for p in xy]
    L = np.concatenate([[0], np.cumsum([np.linalg.norm(b - a) for a, b in zip(xy, xy[1:])])])
    return [(float(p[0]), float(p[1]), float(z0 + (z1 - z0) * (l / L[-1]))) for p, l in zip(xy, L)]


def yellow_path():
    """Yellow Jacket: closed tube from the tower's west deck, round the tree island (CCW, radius 820) into the river"""
    R = 820.0
    a0, a1 = 64.0, 246.0
    start = (TW[0] - TW_BAND - 6, 1040.0)
    j = (C[0] + R * math.cos(math.radians(a0)), C[1] + R * math.sin(math.radians(a0)))
    tg = (-math.sin(math.radians(a0)), math.cos(math.radians(a0)))
    lead = _bez(start, (start[0] - 320, start[1]), (j[0] - tg[0] * 300, j[1] - tg[1] * 300), j, 12)
    arc = [(C[0] + R * math.cos(math.radians(a)), C[1] + R * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 40)][1:]
    # exit: turn in toward the island and run out over the river
    ae = math.radians(a1)
    e0 = arc[-1]
    tg = (-math.sin(ae), math.cos(ae)); inw = (-math.cos(ae), -math.sin(ae))
    ex = _bez(e0, (e0[0] + tg[0] * 160, e0[1] + tg[1] * 160), (C[0] + 600 * math.cos(ae + 0.30), C[1] + 600 * math.sin(ae + 0.30)),
              (C[0] + 560 * math.cos(ae + 0.36), C[1] + 560 * math.sin(ae + 0.36)), 7)[1:]
    xy = [start] + lead[1:] + arc + ex
    pts = _with_z(xy, TW_Z, 8)
    return [(start[0] + 70, start[1], TW_Z)] + pts            # first point on the deck (launch)


def green_path():
    """Green Gulch: open flume from the tower's south deck, east and down the east wall, into the plunge pool"""
    xy = [(1488, 794)]
    xy += _bez((1488, 794), (1488, 620), (1640, 560), (1790, 560), 8)[1:]
    xy += _bez((1790, 560), (1890, 560), (1920, 480), (1920, 400), 6)[1:]
    xy += [(1920, 320)]
    xy += _bez((1920, 320), (1920, 200), (1830, 140), (1720, 140), 7)[1:]
    xy += [(1640, 140)]
    pts = _with_z(xy, TW_Z, 4)
    return [(1488, 860, TW_Z)] + pts
