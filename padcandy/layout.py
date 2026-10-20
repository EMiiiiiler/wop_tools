"""Shared layout constants for wop_padcandy (Candy Garden): used by build_candy.py (brushes, entities) and
candy_models.py (MD3 geometry), so the visible models and the invisible collision line up.

Scale: Padman is about the size of a gummy bear here (~200u per metre, player 56u = a 28 cm Padman), so a giant
fly agaric is ~450u tall and the candy trees ~1100u. x east, y north, meadow z 0, chocolate surface z WATER.
"""
import math
import numpy as np

# ---------------------------------------------------------------- the hall
HX = 2304                      # inner walls at x = +-HX
YS, YN = -1920, 1920           # south wall / north wall inner faces
ROOF = 2048                    # underside of the glass roof
WALL_T = 32
STONE_Z = 576                  # top of the stone wall band (iron-framed windows above)
SKY = dict(x0=-2800, x1=2560, y0=-2432, y1=2176, z0=-640, z1=2304)   # sky hull (inner faces)
SLAB_BOT = -512

# ---------------------------------------------------------------- chocolate river + waterfall pool
WATER = -8                     # chocolate surface
RIV_FLOOR = -56                # 48 deep: wading
RIV_W = 352                    # river width at the surface (floor is narrower, banks slope ~37 deg)
BANK = 64                      # bank slope run (from the surface edge out to the grass edge)
POOL = (700.0, 1180.0)         # waterfall plunge pool centre
POOL_R = 360                   # pool radius at the grass
POOL_FLOOR = -360
# river centreline (surface), from the pool to the tunnel in the west wall
RIVER = [(700, 1180), (520, 960), (240, 760), (-120, 620), (-560, 540), (-1000, 470), (-1420, 330), (-1800, 110),
         (-2100, -170), (-2304, -300), (-2600, -300)]
TUNNEL = dict(x0=-2700, x1=-2304, y0=-480, y1=-120, z1=288)     # chocolate tunnel through the west wall

# ---------------------------------------------------------------- the rock cliff along the north wall
CLIFF_SEGS = [   # (x0, x1, foot y, top-edge y, top z)
    (-2304, -1100, 1300, 1480, 448),     # west shoulder (joins the pump-house deck)
    (-1100, -460, 1300, 1480, 448),
    (-460, 380, 1420, 1640, 1040),       # summit
    (380, 1060, 1480, 1488, 1040),       # behind the waterfall: sheer face (cave mouth at the foot)
    (1060, 1500, 1440, 1470, 1040),
    (1500, 2304, 1320, 1500, 480),       # east shoulder
]
SUMMIT_Z = 1040
FALL_X = 700                   # waterfall centre x
FALL_LIP = (FALL_X, 1494, SUMMIT_Z)      # where the chocolate pours over the cliff edge
FALL_W = (300, 380)            # curtain width at the lip / at the pool
CHANNEL = (FALL_X - 150, 1490, FALL_X + 150, 1900)   # summit channel feeding the fall (x0, y0, x1, y1)
CHANNEL_FLOOR = SUMMIT_Z - 24
# cave behind the waterfall + spiral stair inside the cliff up to the summit
LEDGE = (440, 1400, 1060, 1480)          # dry ledge (z 0) between the falling curtain and the cliff foot
CAVE = (476, 1480, 900, 1900)            # rock-candy cave (floor 0, ceiling CAVE_Z)
CAVE_Z = 288
WELL = (924, 1516, 1308, 1900)           # square stair well (384 x 384), opening west into the cave
WELL_PILLAR = 64
WELL_DOOR = (1780, 1892, 144)            # doorway cave -> bottom landing of the stair well: y0, y1, height                          # half size of the central pillar
# ---------------------------------------------------------------- pump house on its iron deck (north-west)
DECK = (-1100, 900, -460, 1480)          # deck x0, y0, x1, y1
DECK_Z = 448
SHED = (-940, 1100, -620, 1356)          # shed footprint on the deck (door south)
SHED_H = 288
STAIR_BRIDGE = (-460, -268, 0, 896)      # stair over the river up to the deck: x0, x1, y start (z 0), y end (z DECK_Z)
# ---------------------------------------------------------------- the balcony + lobby (south)
BALC = (-1280, YS, 1280, YS + 256)
BALC_Z = 384
BALC_STAIR_W = 224
LOBBY = (-640, YS - 384, 640, YS)        # lobby behind the south wall (floor BALC_Z)
LOBBY_H = 320
LOBBY_DOOR = (-112, 112, 224)            # door x0, x1, height
# ---------------------------------------------------------------- big pieces on the meadow
REDCAP = (-120, -420)                    # red fly agaric (walk under, pad onto the cap)
YELLOW = (1380, -700)                    # yellow mushroom house (walk in, pad onto the cap)
TREE_W = (-1680, 860)                    # flower tree on its rockery mound (west)
MOUND_R0, MOUND_R1, MOUND_H = 400, 250, 80
TREE_E = (1340, 980)                     # flower tree (east of the pool)
GUMTREE = (1880, 420)                    # gumball tree
GROVE = (-1500, -1050)                   # lollipop grove
BOAT = (-1010, 300)                      # candy boat moored on the south bank
BRIDGE = (300, 820)                      # candy-cane bridge over the river
STONES = (-1760, 70)                     # peppermint stepping stones
PIPE_START = (-160, 610)                 # Augustus pipe: suction intake in the river ...
PIPE_LAND = (60, 1780)                   # ... throws you onto the summit
# ---------------------------------------------------------------- the fizzy lifting room (secret, under the world)
FIZZ = dict(x0=-448, x1=448, y0=-448, y1=448, z0=-2880, z1=-1760)


def river_points(step=48.0):
    """centreline resampled every `step` units (Catmull-Rom through RIVER)"""
    P = np.array(RIVER, float)
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, len(P) - 1)]
        L = np.linalg.norm(p2 - p1); n = max(2, int(L / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


def river_dist(x, y):
    """distance from (x, y) to the river centreline (or the pool rim), and the nearest centreline index"""
    P = river_points()
    d = np.hypot(P[:, 0] - x, P[:, 1] - y)
    i = int(np.argmin(d))
    return float(d[i]), i


def on_land(x, y, r=0.0):
    """True if a disc of radius r at (x, y) is on the dry meadow (clear of the river banks and the pool)"""
    d, _ = river_dist(x, y)
    if d < RIV_W / 2 + BANK + r: return False
    if math.hypot(x - POOL[0], y - POOL[1]) < POOL_R + r: return False
    return True


def cliff_top_y(x):
    for (x0, x1, fy, ty, tz) in CLIFF_SEGS:
        if x0 <= x <= x1: return ty, tz
    return None, 0


def cliff_foot_y(x):
    for (x0, x1, fy, ty, tz) in CLIFF_SEGS:
        if x0 <= x <= x1: return fy
    return YN


def apex_traj(start, land, apex, g=800.0, n=48):
    """points along the Q3 AimAtTarget flight from start (x,y,z) to land (x,y,z) with the given apex height"""
    sx, sy, sz = start; lx, ly, lz = land
    tu = math.sqrt(2 * (apex - sz) / g); td = math.sqrt(2 * (apex - lz) / g)
    T = tu + td; vz = g * tu
    out = []
    for t in np.linspace(0, T, n):
        f = t / T
        out.append((sx + (lx - sx) * f, sy + (ly - sy) * f, sz + vz * t - 0.5 * g * t * t))
    return np.array(out), T
