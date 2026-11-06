"""Neon Tide (wop_padwave) - shared layout constants (builder + models). x = port(-)/starboard(+), y = stern(-)/bow(+).
The ship is mirrored about y = 0: bow (+y) = red / hot pink, stern (-y) = blue / electric cyan. Every per-half
feature is written for the bow with |y| and mirrored with s = -1 for the stern."""
import math

# ---- deck heights (floor tops); slabs are SLAB thick under each floor
D14, D15, D16, D17, CROWN = -416, 0, 384, 768, 1152
SLAB = 32
SEA = -1536

# ---- the ship
HX, HY = 1152, 2304                 # playable half beam / half length (deck 15)
WALL = 32                           # deck 14 hull + end walls
SKY = (-3584, -4352, 3584, 4352, SEA - 64, 2560)    # sky hull x0 y0 x1 y1 z0 z1 (sea slab at the bottom)

# ---- superstructure blocks (per half, |y| ranges)
B1_Y = 1664                         # block 1 front wall (deck 15 lounge; its roof = deck 16 terrace)
B2_Y = 1984                         # block 2 front wall (deck 16 sky lounge; its roof = deck 17 sky terrace)
BW = 32                             # block wall thickness

# ---- funnel + crown
FUN_R0, FUN_R1 = 288, 256           # outer radius at the base / under the crown
FUN_T = 24                          # wall thickness (collision ring)
FUN_N = 16                          # collision wedges
FUN_DOOR = (80, 176)                # door half-width (u along the wall) and height
CROWN_R = 296                       # crown deck radius (walkable, no parapet)
CROWN_HOLE = 88                     # lift hole in the crown
BRIDGE_HW = 96                      # sky bridge half width (x)

# ---- pools (per half)
POOL = (-448, 768, 448, 1472)       # x0 |y|0 x1 |y|1
POOL_FLOOR = -56                    # basin floor top
WATER = -8                          # water surface

# ---- stairs
UP_X = (656, 816)                   # deck 15 -> 16 flights (|x|), rising toward the block
UP_Y = (896, 1664)
DN_X = (848, 1008)                  # deck 15 -> 14 flights under the promenade, top at the funnel end
DN_Y = (352, 1184)
TER_STAIR_Y = (1824, 1984)          # deck 16 -> 17 flights on the terrace, rising outward
TER_STAIR_X = (160, 928)

# ---- promenade (deck 16 side strips)
PROM_X = (864, 1152)
PORT_GAP = 448                      # port strip opens above the Wave Rider for |y| < PORT_GAP
WALKWAY_X = (-960, -704)            # inboard walkway over the Wave Rider

# ---- Wave Rider (port, midships) and Sky Pool (starboard, midships)
WR = dict(x0=-1152, lip_x=-1024, ramp_x=-704, hy=320, lip_z=224, stair_x=(-1152, -1056), stair_y=(320, 768))
SP = dict(x0=1152, x1=1664, hy=448, floor=-192, water=-8, step_x=(1152, 1408), step_y=(64, 448))

# ---- elevators (starboard, one per half)
ELEV = (704, 832, 2112, 2240)       # x0 x1 |y|0 |y|1

# ---- deck 14 rooms
ATRIUM_Y = 704                      # walls at |y| 704..736 between the atrium and the disco / arcade
DOOR_X = 256                        # centre doorway half width in those walls

# ---- slides (per half): start on the deck 17 front edge
SLIDE_X = 560                       # |x| of the slide starts (port = open flume, starboard = black-light tube)


def flume_xy():
    """bow half, port: start on deck 17 at (-SLIDE_X, B2_Y + 16), down over the terrace and deck 15 into the pool"""
    from woplib.geom import bezier
    xy = [(-SLIDE_X, B2_Y + 40), (-SLIDE_X, B2_Y - 40)]
    xy += [tuple(p) for p in bezier((-SLIDE_X, B2_Y - 40), (-SLIDE_X, 1500), (-560, 1250), (-260, 1180), 14)[1:]]
    xy += [tuple(p) for p in bezier((-260, 1180), (-120, 1145), (-60, 1100), (-60, 1000), 6)[1:]]
    return xy


def tube_xy():
    """bow half, starboard: a wider S through the air into the pool from the east"""
    from woplib.geom import bezier
    xy = [(SLIDE_X, B2_Y + 40), (SLIDE_X, B2_Y - 40)]
    xy += [tuple(p) for p in bezier((SLIDE_X, B2_Y - 40), (SLIDE_X, 1560), (340, 1650), (300, 1420), 12)[1:]]
    xy += [tuple(p) for p in bezier((300, 1420), (280, 1250), (150, 1160), (120, 1040), 8)[1:]]
    return xy


VORTEX = dict(R=416, a0=0.0, sweep=-540.0, z0=CROWN - 8, z1=16)


def mirror_y(p, s):
    return (p[0], p[1] * s) + tuple(p[2:])
