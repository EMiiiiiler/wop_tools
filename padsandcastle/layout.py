"""Sandcastle Showdown layout: every number the generator and the models share, so the invisible weapclip collision
always sits just inside the visible MD3 surfaces. x east, y north, sand z 0. Padman scale (~8u per cm).
Mirror symmetric in x: everything below is the BLUE (east, +x) side; red is the same with x -> -x."""
import math

BOUNDS = (-2624, -1792, 2624, 1792)          # playable floor
HULL = (-3008, -3008, 3008, 2560)            # sky box (sea to the south, dunes to the north)
ZBASE = -224                                 # top of the structural base slab
ZTOP = 2624                                  # sky ceiling

# ------------------------------------------------------------------ beach + sea
BEACH_Y = -900                               # sand z 0 north of this line
SHORE_Y = -1160                              # the beach slope reaches the sea floor here
SEA_FLOOR = -48
WATER_Z = -10
POOL = (-400, -1560, 400, -1240)             # rock pool (x0, y0, x1, y1)
POOL_FLOOR = -208
POOL_STEP_RUN = 320                          # 10 x 32u treads down each end

# ------------------------------------------------------------------ castle (blue side)
CX0, CX1, CY0, CY1 = 1400, 2400, -150, 1050  # outer wall rectangle
WALL_T = 96
WALL_H = 256
GATE = (350, 550)                            # y span of the gate in the west wall
POSTERN = (1586, 1700)                       # x span of the posterns in the north and south walls
LINTEL_Z = 240                               # lolly-stick lintels over gate and posterns (top = WALL_H)
TURRET_R = 144                               # visual base radius (collision 138 -> 126)
TURRET_H = 272
TURRETS = [(CX0 + 48, CY0 + 48), (CX0 + 48, CY1 - 48), (CX1 - 48, CY0 + 48), (CX1 - 48, CY1 - 48)]
STAIR_RUN = 512                              # 16 x 32 treads up to the wall walk
STAIRS_S = (1704, CY0 + WALL_T, 1704 + STAIR_RUN, CY0 + WALL_T + 128)   # along the south wall, rising east
STAIRS_N = (1704, CY1 - WALL_T - 128, 1704 + STAIR_RUN, CY1 - WALL_T)   # along the north wall, rising east

KEEP = (1900, 450)                           # keep centre
KEEP_R0, KEEP_R1 = 256, 232                  # outer visual radius at z 40 and at the top
KEEP_THICK = 44
KEEP_H = 480                                 # wall height; roof slab 480..512, crenellations 512..536
KEEP_TOP = 512
KEEP_HOLE = 160                              # square hatch in the roof for the lift pad
KEEP_PAD = (1900, 450)                       # lift pad inside the keep, under the hatch (keep centre)
DOOR_W, DOOR_SPRING, DOOR_TOP = 96, 160, 256 # half width, arch springing line, arch top (door faces the gate)

MOAT = (1060, 1252)                          # x span (banks 64 each side of a 64 bottom)
MOAT_Y = (-760, 1300)
BRIDGE = (996, 1364, 330, 570)              # lolly-stick drawbridge x0 x1 y0 y1 (3 sticks)

# ------------------------------------------------------------------ Mount Sandy (centre)
MOUNT = (0, 300)
T1_R, T1_H = 560, 192                        # lower tier (24-gon collision, flat faces E/W/N/S)
T2_R0, T2_R1, T2_H = 300, 276, 400           # summit tier from T1_H up to T2_H
TUNNEL_W, TUNNEL_H = 112, 160                # half width, height (north-south through T1)
MSTAIR_Y = (228, 372)                        # stairs east/west onto the terrace
MSTAIR_RUN = 384                             # 12 x 32

# ------------------------------------------------------------------ picnic (north)
PARASOL = (0, 1280)
PARASOL_H, PARASOL_R = 1520, 880
TOWEL = (-560, 960, 560, 1230)
BIN = (800, 1380)                            # chilly bin centre (blue side)
BIN_W, BIN_D, BIN_H = 480, 320, 336
CONCH = (-150, 1580)
GROTTO_Z = -2048                             # Mermaid's Grotto floor (sealed under the world)


def teeth(cx, cy, r_in, r_out, z0, z1, count, phase=0.0, fill=0.5):
    """crenellation teeth round a circle: list of (polygon [(x, y)...], z0, z1); fill = tooth share of each step"""
    out = []
    for k in range(count):
        a0 = 2 * math.pi * (k + phase) / count
        a1 = a0 + 2 * math.pi * fill / count
        poly = [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in ((r_in, a0), (r_out, a0), (r_out, a1), (r_in, a1))]
        out.append((poly, z0, z1))
    return out


def wall_teeth(x0, y0, x1, y1, z0, z1, side, size=48, gap=48, depth=20):
    """crenellation teeth along the outer edge of a wall top: rect footprints (x0, y0, x1, y1) with height z0..z1.
    side = the outer side ('n', 's', 'e', 'w'); the teeth sit on that edge, `depth` deep."""
    out = []
    horiz = side in 'ns'
    lo, hi = (x0, x1) if horiz else (y0, y1)
    n = max(1, int((hi - lo + gap) // (size + gap)))
    span = n * size + (n - 1) * gap
    s0 = lo + (hi - lo - span) / 2
    for k in range(n):
        a = s0 + k * (size + gap); b = a + size
        if side == 'n': out.append((a, y1 - depth, b, y1))
        elif side == 's': out.append((a, y0, b, y0 + depth))
        elif side == 'e': out.append((x1 - depth, a, x1, b))
        else: out.append((x0, a, x0 + depth, b))
    return [(r, z0, z1) for r in out]
