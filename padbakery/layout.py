"""Shared layout constants for wop_padbakery (Sweet Padman's Bakery).

Padman scale: ~8u per cm, catalog models at their native scale 1.0 (a muffin is as tall as Padman).
x east, y north, kitchen floor z 0. All numbers in game units."""
import math

HX, HY = 2304, 2048          # interior half sizes (room 4608 x 4096)
CEIL = 2048                  # ceiling height
WALL_T = 32
FLOOR_T = 64

# ------------------------------------------------------------------ deck oven (west wall), front plane at x = OV_FRONT
OV_X0, OV_FRONT = -HX, -1632
OV_Y0, OV_Y1 = -640, 640
OV_SIDE = 32                 # side and back wall thickness
OV_FRONT_T = 32
PROOF_TOP = 320              # proofer cabinet interior z 0..320, slab 320..448
DECK1 = 448                  # deck 1 floor, interior 448..608, slab 608..720
DECK2 = 720                  # deck 2 floor, interior 720..880, slab 880..960
DECK_H = 160
OV_TOP = 960
MOUTHS = [(-576, -64), (64, 576)]     # y spans of the two mouths of each deck
PROOF_MOUTH = (-576, 576)
DOOR_D = 120                 # hinged-down doors stick out this far in front of each mouth
DOOR_T = 20
FLUE = (-2176, 0, 64)        # flue pipe on the oven top: x, y, r

# ------------------------------------------------------------------ counters (worktop z 720)
WORK = 720
WORK_T = 32                  # worktop slab 688..720
SHELF = 352                  # mid shelf top (slab 336..352)
SHELF_T = 16
LOW_TOP = SHELF - SHELF_T    # lower cubby z 0..336
N_FRONT = 1440               # north counter front face (worktop overhangs to N_FRONT - 16)
N_X0 = -1408
N_BACK = 32
N_DIVS = [(-1408, -1376), (-416, -384), (576, 608), (1664, 1696)]   # end panel + dividers (x spans)
N_CORNER = (1664, HX)        # closed corner cabinet x span (the east counter meets here)
E_FRONT = 1696               # east counter front face (x)
E_Y0 = -768                  # east counter south end
E_DIVS = [(-768, -736), (320, 352)]   # end panel + divider (y spans)
OVERHANG = 16
DOORWAY = (1600, 1856)       # tunnel openings through the north dividers (y span); east: x span
DOORWAY_E = (1840, 2096)
DOOR_LOW_TOP = 240           # lower tunnel opening top, upper opening SHELF..SHELF+240
WALL_SHELF = (-448, 1600, 1840, 1296)   # wall shelf over the north counter: x0, x1, y0 (front), top z (to the wall)
WALL_SHELF_T = 24

# ------------------------------------------------------------------ the show cake (centre)
CAKE = (0, 300)
CAKE_N = 24
CAKE_PHASE = 7.5             # a flat face of the 24-gon points south (the sugar-cube stair)
TIERS = [(480, 0, 224), (340, 224, 432), (200, 432, 624)]    # radius, z0, z1
CAVE = (-22.5, 22.5)         # the missing slice (east): sectors removed from tier 1
STAIR_W = 160

# ------------------------------------------------------------------ commercial floor mixer (west of the cake)
MIX = (-1050, 880)           # bowl centre
BOWL_R0, BOWL_R1 = 150, 200  # inner radius at the bottom / rim
BOWL_Z0, BOWL_Z1 = 320, 640  # bowl inner bottom, rim top
BOWL_T = 16
MIX_COL = (-1210, 1110, -890, 1410)      # column footprint
MIX_HEAD = (-1170, 780, -930, 1410, 900, 1150)   # head box x0,y0,x1,y1,z0,z1

# ------------------------------------------------------------------ display cabinet (shop counter)
DC = (-1100, -1520, 1000, -960)          # x0, y0 (glass front, south), x1, y1 (open back, north)
DC_PLINTH = 128
DC_SHELF = 448                            # glass shelf top (432..448)
DC_TOP = 784                              # counter top (752..784)
DC_GLASS_T = 16
DC_STEPS = [(-1068, -948), (868, 988)]   # x spans of the 16u step stools at the back (rising south)

# ------------------------------------------------------------------ cool room (south-east)
CR = (1312, -2048, 2304, -1088)
CR_H = 960
CR_T = 32
CR_DOOR = (1900, 96, 320)                # door in the north wall: centre x, half width, height

# ------------------------------------------------------------------ cooling racks (south-west)
RACKS = [(-1980, -1050, 0), (-1560, -1700, 90)]   # centre x, y, yaw
RACK_W, RACK_D = 528, 416
RACK_TRAYS = [16, 240, 464, 688]
RACK_TOP = 912

# ------------------------------------------------------------------ flour bin (north-west, the secret entrance)
BIN = (-2240, 1520, -1760, 1952)         # outer footprint
BIN_H = 160
BIN_T = 24
BIN_FLOOR = 32
BIN_STAIR = (-2080, 1200, -1920, 1520)   # 10 steps rising north onto the rim

# ------------------------------------------------------------------ the secret Sugar Vault (sealed, below the world)
VAULT = (-640, -512, 640, 512, -1600, -1088)     # x0, y0, x1, y1, z0 (floor), z1 (ceiling)

# ------------------------------------------------------------------ shop windows (south wall) + street backdrop
WINDOWS = [(-1000, -150, 260, 1300), (150, 1000, 260, 1300)]    # x0, x1, z0, z1
STREET_D = 480               # backdrop distance behind the south wall


def ngon_pts(cx, cy, r, n=CAKE_N, phase=CAKE_PHASE):
    return [(cx + r * math.cos(math.radians(phase + 360 * k / n)), cy + r * math.sin(math.radians(phase + 360 * k / n))) for k in range(n)]


def apothem(r, n=CAKE_N):
    return r * math.cos(math.pi / n)
