"""Shared layout constants for wop_padmuseum (Midnight Museum): read by build_museum.py (brushes, entities) and
mu_models.py (MD3 geometry). Human scale, ~64u per metre (Padman a short 0.9 m). x east, y north, ground floor z 0.

  +----------+---------------+----------+
  | NW stair |   ICE AGE     | NE office|    y 1024..2048
  +----------+---------------+----------+
  |  EGYPT   |  GREAT HALL   |PLANETAR. |    y -1024..1024
  +----------+---------------+----------+
  |  GEMS    |    FOYER      |  OCEAN   |    y -2048..-1024
  +----------+---------------+----------+
     x -2304..-1024  -1024..1024  1024..2304        portico outside the foyer (south)
"""
import math

XB = [-2304, -1024, 1024, 2304]
YB = [-2048, -1024, 1024, 2048]
ROOMS = {
    'gems': (-2304, -2048, -1024, -1024), 'foyer': (-1024, -2048, 1024, -1024), 'ocean': (1024, -2048, 2304, -1024),
    'egypt': (-2304, -1024, -1024, 1024), 'hall': (-1024, -1024, 1024, 1024), 'planet': (1024, -1024, 2304, 1024),
    'stair_w': (-2304, 1024, -1024, 2048), 'ice': (-1024, 1024, 1024, 2048), 'stair_e': (1024, 1024, 2304, 2048),
}
CEIL = 640                      # room ceiling (slab CEIL..ROOF)
ROOF = 656                      # roof terrace walk height
HALL_TOP = 1280                 # great hall clerestory top (skylight)
IW = 16                         # half thickness of interior walls (32 thick, centred on the room boundaries)
OW = 64                         # outer wall thickness (outside the boundary)
PARAPET = 48
HULL = dict(x0=-2816, x1=2816, y0=-3072, y1=2560, z0=-256, z1=1920)

# interior doorways: (wall axis 'x' = wall at fixed x / 'y' = wall at fixed y, fixed, u0, u1, height)
DOORS = [('y', -1024, -320, 320, 320),            # foyer <-> hall (under the mezzanine)
         ('x', -1024, -320, 320, 320),            # hall <-> egypt
         ('x', 1024, -320, 320, 320),             # hall <-> planetarium
         ('y', 1024, -320, 320, 320),             # hall <-> ice age
         ('x', -1024, -1720, -1420, 288),         # foyer <-> gems
         ('x', 1024, -1720, -1420, 288),          # foyer <-> ocean
         ('y', -1024, -1820, -1520, 288),         # egypt <-> gems
         ('y', -1024, 1520, 1820, 288),           # planetarium <-> ocean
         ('y', 1024, -1360, -1120, 288),          # egypt <-> NW stair
         ('y', 1024, 1120, 1360, 288),            # planetarium <-> NE office
         ('x', -1024, 1180, 1460, 288),           # ice age <-> NW stair
         ('x', 1024, 1180, 1460, 288)]            # ice age <-> NE office
FRONT_DOOR = (-256, 256, 384)                     # south outer wall: x0, x1, height
PORTICO = (-832, -2560, 832, -2112)               # outside the front doors (open sky)

# ---------------------------------------------------------------- great hall
MEZZ_Z = 352                    # mezzanine walk (slab MEZZ_Z-16 .. MEZZ_Z)
MEZZ_W = 192                    # ring depth along the hall walls
FLIGHT_Y = (-832, -704)         # the two grand flights in front of the south ring (rise outward, west and east)
FLIGHT_X0 = 64                  # flights start at x = +-64 and rise outward
FLIGHT_N = MEZZ_Z // 16         # 22 steps of 32
TREX = (0.0, 120.0)             # skeleton centre (hips); faces south (-y)
TREX_PLINTH = (-260, -440, 260, 700, 16)          # x0, y0, x1, y1, height
# walkable spine path (y, z top) from the tail tip to the skull; collision width 64
TREX_PATH = [(640, 16), (470, 96), (300, 180), (150, 224), (40, 232), (-60, 238), (-150, 276), (-200, 300), (-300, 300)]
TREX_W = 64
WHALE = (0.0, 260.0)
WHALE_Z = 880                   # whale skeleton height (hanging from the skylight frame)

# mezzanine-level doors in the hall walls and the balconies behind them (x0, y0, x1, y1)
MEZZ_DOOR_H = 256
BALCONIES = {'w': (-1232, -200, -1040, 200), 'e': (1040, -200, 1232, 200), 'n': (-200, 1040, 200, 1232)}
LANDING = (-64, -816, 64, -672)                    # central landing of the imperial stair (z MEZZ_Z)
STAIR_Y = (-800, -672)                             # the two flights rise from the side walls toward the landing

# ---------------------------------------------------------------- egypt: step pyramid with a tomb inside
PYR = (-1664.0, 0.0)            # centre
PYR_BASE = 768
PYR_TIERS = 4
PYR_TIER_H = 48
PYR_INSET = 64
PYR_STEPS = 12                  # east stair (16u) from the floor up to the top platform, 128 wide
TOMB = (-1856, -160, -1536, 160, 144)             # chamber inside: x0, y0, x1, y1, height
TOMB_TUNNEL = (-1760, -1696, 112)                 # south tunnel: x0, x1, height (from the south face to the chamber)
SARC = (-1696.0, 50.0)          # scale SARC_SC
SARC_SC = 0.7          # the open sarcophagus (SECRET) in the chamber

# ---------------------------------------------------------------- planetarium
DOME = (1664.0, 0.0)
DOME_R = 576
DOME_H = 400                    # rise above the roof (exterior and interior)
DOME_TOP_R = 160                # flat lantern platform on top
DOME_HE = DOME_H / math.sqrt(1 - (DOME_TOP_R / DOME_R) ** 2)      # ellipse height parameter (r(DOME_H) = DOME_TOP_R)
ORRERY_Z = 920                  # orrery pivot (func_rotating) inside the dome


def dome_r(h):
    """outer radius of the planetarium dome h above the roof"""
    return DOME_R * math.sqrt(max(0.0, 1 - (min(h, DOME_H) / DOME_HE) ** 2))

# ---------------------------------------------------------------- ice age hall
MAMMOTH = (-420.0, 1560.0)
MAMMOTH_BACK = 236              # walkable back (pad)

# ---------------------------------------------------------------- gems: walk-in geode
GEODE = (-1664.0, -1560.0)
GEODE_R = 300
GEODE_H = 316                   # flat top (walkable, pad up)
GEODE_HE = 360                  # ellipse height parameter


def geode_r(h):
    return GEODE_R * math.sqrt(max(0.0, 1 - (min(h, GEODE_H) / GEODE_HE) ** 2))
GEODE_DOOR = 90.0               # entrance faces north

# ---------------------------------------------------------------- ocean: giant squid tank
TANK = (1820.0, -1560.0, 220, 180, 432)           # centre x, y, half x, half y, height

# ---------------------------------------------------------------- stair towers (NW / NE): two adjacent flights along the north wall
STAIR_A_Y = (1888, 2032)        # first flight (rises toward the room's inner side)
STAIR_B_Y = (1744, 1888)        # second flight (back the other way, up to the roof)
STAIR_LAND = 160                # landing depth at the turn

# ---------------------------------------------------------------- secret: the burial chamber (sealed, under the world)
TREASURY = dict(x0=-768, x1=768, y0=-640, y1=640, z0=-2560, z1=-2112)


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def flight_steps(side):
    """imperial stair: [(x0, x1, z_top)] for the west (side -1) or east (+1) flight, from the side (x = +-768) up toward
    the central landing (x = +-64, z MEZZ_Z)"""
    out = []
    for j in range(FLIGHT_N):
        a = 768 - 32 * j; b = a - 32               # |x| range of step j
        x0, x1 = (-a, -b) if side < 0 else (b, a)
        out.append((x0, x1, 16 * (j + 1)))
    return out


def tower_flights(side):
    """stair tower in the NW (side -1) or NE (+1) room: flight A (0 -> 320) along the north wall from the outer corner
    toward the hall side, landing, flight B (320 -> 656) back toward the outer wall. Returns (stepsA, landing, stepsB, hole)
    with steps as (x0, y0, x1, y1, z) and hole = roof opening over the top of flight B."""
    xo = XB[0] + 16 if side < 0 else XB[3] - 16          # outer wall inner face
    s = 1 if side < 0 else -1                             # direction from the outer wall toward the hall side
    nA = 20; nB = (ROOF - 320) // 16                       # 20 + 21 steps
    A, B = [], []
    for j in range(nA):
        u0 = xo + s * (160 + 32 * j); u1 = u0 + s * 32
        A.append((min(u0, u1), STAIR_A_Y[0], max(u0, u1), STAIR_A_Y[1], 16 * (j + 1)))
    ue = xo + s * (160 + 32 * nA)
    land = (min(ue, ue + s * STAIR_LAND), STAIR_B_Y[0], max(ue, ue + s * STAIR_LAND), STAIR_A_Y[1], 320)
    for j in range(nB):
        u0 = ue - s * 32 * j; u1 = u0 - s * 32
        B.append((min(u0, u1), STAIR_B_Y[0], max(u0, u1), STAIR_B_Y[1], 320 + 16 * (j + 1)))
    k0 = next(j for j, st in enumerate(B) if st[4] + 56 > CEIL) - 2
    ub = ue - s * 32 * k0
    uend = ue - s * 32 * nB
    hole = (min(ub, uend), STAIR_B_Y[0], max(ub, uend), STAIR_B_Y[1])
    return A, land, B, hole


def pyr_tier(k):
    """(x0, y0, x1, y1, z0, z1) of pyramid tier k"""
    cx, cy = PYR
    h = PYR_BASE / 2 - PYR_INSET * k
    return (cx - h, cy - h, cx + h, cy + h, PYR_TIER_H * k, PYR_TIER_H * (k + 1))


def pyr_stairs():
    """east stair up the pyramid: [(x0, y0, x1, y1, z)] from the floor (east, outside the base) up to the top"""
    cx, cy = PYR
    top_edge = cx + PYR_BASE / 2 - PYR_INSET * (PYR_TIERS - 1)
    run = 26
    out = []
    for j in range(PYR_STEPS):
        x1 = top_edge + run * (PYR_STEPS - j); x0 = x1 - run
        out.append((x0, cy - 64, x1, cy + 64, 16 * (j + 1)))
    return out
