"""Shared layout constants for wop_padaztec (Tlaloc's Lagoon): read by build_aztec.py (brushes, entities) and
az_models.py (MD3 geometry), so the visible models and the invisible collision line up.

An Aztec temple water park in the jungle, human scale (~32u per metre, Padman 56u). x east, y north, plaza z 0,
water surface z -16.

   y 2048 +-------------------------------------------------------------------+
          | CENOTE (sinkhole, spiral   | HALL OF THE EAGLE WARRIORS  | TLALOC HEAD |
          |  stair, waterfall, secret) | (colonnade, roof)           | fountain    |
     1408 |                +-----------+-----------------------------+             |
          | JAGUAR TEMPLE  |      GREAT PYRAMID OF TLALOC            | PLUNGE POOL |
          | (platform,     |  4 tiers, N + S stairs, shrine on top,  | (Eagle      |
          |  shrine, roof) |  tunnel + tomb inside; Serpent tube W,  |  flume in)  |
        0 |                |  Eagle flume E                          |             |
          +----------------+-----------------------------------------+-------------+
          | CANTINA        |   LAGOON (two lakes, island with the    | BALL COURT  |
          | (bar, roof     |   Sun Stone, causeways N and S)         | (tlachtli)  |
          |  terrace)      |                                          |             |
   y-2048 +-------------------------------------------------------------------+
          x -2304                                                         x 2304
"""
import math
import numpy as np

HX, HY = 2304, 2048            # playable half extents (the jungle banks start here)
BANK_W, BANK_H = 352, 320      # jungle bank: rises from the plaza edge to BANK_H over BANK_W
SKY = dict(x0=-2944, x1=2944, y0=-2688, y1=2688, z0=-896, z1=2304)
WATER = -16
SLAB_BOT = -384
SHALLOW = -64                  # 48 deep: wading
DEEP = -272

# ---------------------------------------------------------------- the Great Pyramid of Tlaloc
PC = (0.0, 704.0)              # centre
NT = 4                         # tiers
TIER_H = 112
H0 = 704                       # tier 0 half size (talud foot)
TALUD_W, TALUD_H = 40, 32      # sloped base of each tier (walkable, 38.7 deg), then the vertical tablero
TOP_Z = NT * TIER_H            # 448
STAIR_HW = 112                 # half width of the N and S stairs
STAIR_RUN = 16                 # 45-degree Aztec stair: 28 steps of 16 x 16
STAIR_N = TOP_Z // 16


def tier_half(k):
    """talud foot half size of tier k"""
    return H0 - TIER_H * k


def tablero_half(k):
    return tier_half(k) - TALUD_W


TOP_HALF = tablero_half(NT - 1)                      # 328: flat top platform half size
TOP = (PC[0] - TOP_HALF, PC[1] - TOP_HALF, PC[0] + TOP_HALF, PC[1] + TOP_HALF)


def stair_steps(side):
    """[(y0, y1, z_top)] of the south (side -1) or north (+1) stair; the last step meets the top platform edge"""
    out = []
    edge = PC[1] + side * TOP_HALF
    for j in range(STAIR_N):
        a = edge + side * STAIR_RUN * (STAIR_N - j)
        b = a - side * STAIR_RUN
        out.append((min(a, b), max(a, b), 16 * (j + 1)))
    return out


# tunnel + tomb inside the pyramid
TUNNEL_HW, TUNNEL_H = 64, 112                       # E-W tunnel through tier 0 (y = PC[1] +- 64, z 0..112)
TOMB_HALF, TOMB_H = 192, 208                         # central chamber (x, y +- 192 round PC, z 0..208)

# the shrine on top (walk in from the south, roof walkable: Imperius)
SHRINE = (PC[0] - 192, PC[1] - 48, PC[0] + 192, PC[1] + 180)   # outer walls
SHRINE_WALL = 32
SHRINE_DOOR = (-64, 64, 160)                         # x range (relative to PC) and height of the south door
SHRINE_ROOF = TOP_Z + 224                            # roof walk 672 (slab 208 .. 224 above the platform)

# ---------------------------------------------------------------- the lagoon (south): an octagon, island + causeways
LAG = (-1184.0, -1824.0, 1184.0, -480.0)            # bounding rect
LAG_CUT = 352                                        # corner chamfer
SHALLOW_BAND = 192                                   # 48-deep ring round the edge, then a slope down to DEEP
SLOPE_W = 160
ISLAND = (0.0, -1152.0)
ISLAND_R = 272
CAUSE_HW = 112                                       # causeways x +- 112 from the island to the north and south shores
ISLETS = [(-640.0, -1400.0, 104), (640.0, -950.0, 104)]   # rock islets in the lakes (cover)
SUN_R = 224                                          # the Sun Stone (upright disc on the island)


def octagon(rect, cut, inset=0.0):
    x0, y0, x1, y1 = rect
    x0 += inset; y0 += inset; x1 -= inset; y1 -= inset
    c = max(0.0, cut - inset * (math.sqrt(2) - 1))
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


# exits: 16u steps from the shallow floor (z -64) up to the plaza, (x0, y0, x1, y1, rise direction)
LAG_STEPS = [(-700, -1824, -500, -1760, 's'), (500, -1824, 700, -1760, 's'),
             (-1184, -1250, -1120, -1050, 'w'), (1120, -1250, 1184, -1050, 'e')]
BEACH = (320, -672, 832, -480)                       # beach ramp (north shore of the east lake) from 0 down to -64

# ---------------------------------------------------------------- Serpent tube (closed, west) + Eagle flume (open, east)
TUBE_R = 52                                          # tube radius; collision corridor half width 40, height 96
TUBE_ZC = 46


def _bez(p0, p1, p2, p3, n):
    out = []
    for t in np.linspace(0, 1, n):
        out.append(((1 - t) ** 3) * np.array(p0, float) + 3 * ((1 - t) ** 2) * t * np.array(p1, float)
                   + 3 * (1 - t) * t * t * np.array(p2, float) + t ** 3 * np.array(p3, float))
    return out


def _with_z(xy, z0, z1):
    xy = [np.asarray(p, float) for p in xy]
    Ls = np.concatenate([[0], np.cumsum([np.linalg.norm(b - a) for a, b in zip(xy, xy[1:])])])
    return [(float(p[0]), float(p[1]), float(z0 + (z1 - z0) * (l / Ls[-1]))) for p, l in zip(xy, Ls)]


def serpent_path():
    """from the west edge of the top platform (enter the serpent's mouth), west over the terraces, south past the
    jaguar temple's east side and into the north-west corner of the west lake"""
    xy = [(-TOP_HALF, 980.0)]
    xy += _bez((-TOP_HALF, 980), (-700, 980), (-1000, 900), (-1000, 560), 14)[1:]
    xy += _bez((-1000, 560), (-1000, 200), (-1000, -60), (-980, -260), 10)[1:]
    xy += _bez((-980, -260), (-960, -440), (-880, -560), (-800, -680), 6)[1:]
    pts = _with_z(xy, TOP_Z, -4)
    return [(-TOP_HALF + 72, 980.0, float(TOP_Z))] + pts


def flume_path():
    """Eagle flume: from the east edge of the top platform, north-east and round into the plunge pool"""
    xy = [(TOP_HALF + 2, 1000.0)]
    xy += _bez((TOP_HALF + 2, 1000), (760, 1000), (1000, 1260), (1240, 1260), 14)[1:]
    xy += _bez((1240, 1260), (1500, 1260), (1560, 1120), (1500, 980), 9)[1:]
    xy += [(1440, 860)]
    pts = _with_z(xy, TOP_Z, -4)
    return [(TOP_HALF - 72, 1000.0, float(TOP_Z))] + pts


# ---------------------------------------------------------------- plunge pool (east of the pyramid)
POOL_P = (1088, 448, 1728, 1088)
POOL_P_FLOOR = -304
POOL_P_STEPS = 12                                    # 16u steps up the south end, 32 deep

# ---------------------------------------------------------------- cenote (north-west): sinkhole with a spiral stair
CEN = (-1600.0, 1472.0)
CEN_R = 400                                          # shaft radius
CEN_WATER = -304                                     # water surface down the shaft
CEN_FLOOR = -656
CEN_SLAB = -800                                      # slab bottom of the cenote tile
CEN_TILE = (-2112, 960, -1088, 1984)
CEN_STAIR_W = 104                                    # stair ring width along the wall
CEN_STAIR_A0 = 300.0                                 # angle of the top step (deg CCW from +x); stair descends CCW
CEN_STAIR_DA = 11.0
CEN_STAIR_N = 24                                     # tops -16 ... -384 (the last 5 under water)
CEN_SECRET_A = 250.0                                 # underwater serpent-mouth tunnel (angle), floor z
CEN_SECRET_Z = -560

# ---------------------------------------------------------------- jaguar temple (west)
JAG = (-1632.0, 224.0)
JAG_PLAT = (320, 256, 160)                           # half x, half y, height (talud + tablero)
JAG_BLD = (-176, -144, 144, 144)                     # building outer walls, relative to JAG (door east)
JAG_ROOF = 160 + 192                                 # roof walk
JAG_STAIR_RUN = 24                                   # 10 steps east of the platform (x JAG+320 .. +560), y +-96

# ---------------------------------------------------------------- cantina (south-west)
CAN = (-2048, -1856, -1504, -1344)                   # building footprint
CAN_H = 208                                          # roof terrace walk
CAN_STAIR = 13                                       # 16u steps up the east side, rising north

# ---------------------------------------------------------------- ball court (south-east)
BC = (1760.0, -1472.0)                               # centre
BC_ALLEY = (1440, -1568, 2080, -1376)                # plaza-level alley (x0, y0, x1, y1)
BC_END = 128                                         # end zones: 128 deep beyond the alley, 512 wide
BC_BENCH = (64, 32)                                  # sloped bench: depth, rise
BC_WALL_Z = 192                                      # wall top (walkable)
BC_TOP_W = 192                                       # wall top depth
BC_STAIR = 12                                        # 16u steps up each outer wall face

# ---------------------------------------------------------------- Tlaloc head fountain (north-east)
HEAD = (1632.0, 1640.0)                              # head centre on its plinth
HEAD_PLINTH = (224, 160, 64)                         # half x, half y, height
HEAD_TOP = 512                                       # walkable crown of the headdress
HEAD_POOL = (1392, 1216, 1872, 1440)                 # splash pool in front (48 deep)

# ---------------------------------------------------------------- hall of the eagle warriors (north)
HALL = (-704, 1680, 704, 1984)                       # roof footprint
HALL_Z = 224                                         # roof walk
HALL_STAIR = 14

# ---------------------------------------------------------------- secret: Moctezuma's treasure (sealed, under the world)
TREASURE = dict(x0=-704, x1=704, y0=-576, y1=576, z0=-2560, z1=-2144)

# ---------------------------------------------------------------- the feathered serpent flying round the pyramid
QUETZ_R = 1500
QUETZ_Z = 1150


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def cen_step(j):
    """cenote spiral step j: (a0, a1, z_top); the stair descends counter-clockwise from CEN_STAIR_A0"""
    a1 = CEN_STAIR_A0 + CEN_STAIR_DA * j
    return (a1, a1 + CEN_STAIR_DA, -16 * (j + 1))
