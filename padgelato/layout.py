"""Shared layout constants for wop_padgelato (Padman's Gelato Parlour).

Padman scale (~8u per cm, catalog models at 1.0). x east, y north, floor z 0, ceiling z 2048."""
import math

HX, HY = 2304, 2048
CEIL = 2048
WALL_T = 32
FLOOR_T = 64

# ------------------------------------------------------------------ the giant cone (centre)
TOWER = (0.0, 250.0)
TW_N = 24
STAND = (250.0, 290.0, 170.0)        # chrome cup: r bottom, r top, height
CONE_R0, CONE_R1 = 150.0, 430.0      # waffle cone radius at the stand top / at the rim
CONE_Z0, CONE_Z1 = 170.0, 960.0
RIM_R, RIM_Z = 470.0, 1000.0         # wafer rim (walkable deck z 1000)
SCOOP_TERR = [(1000, 1080, 300), (1080, 1160, 270), (1160, 1230, 210), (1230, 1270, 140)]   # z0, z1, r collision terraces
SCOOP_R, SCOOP_H = 330.0, 300.0      # visible big scoop (ellipsoid centred on the deck)
LIFT_A = 270.0                       # the scoop lift stands south of the cone
LIFT_D = 574.0                       # distance from the tower centre
LIFT_R = 96.0

# ------------------------------------------------------------------ the gelato counter (north)
GC = (-1400.0, 1450.0, 1400.0, 1750.0)   # x0, y0 (glass front), x1, y1 (back)
GC_PLINTH = 60.0
GC_TUB = 368.0                       # ice cream surface in the tubs
GC_DECK = 400.0                      # walkable frame
GC_TUBS = [(-1150.0 + k * 290.0, -1150.0 + k * 290.0 + 220.0) for k in range(8)]   # x spans
GC_TUB_Y = (1500.0, 1700.0)
GC_PAN_Z = 240.0                     # pan bottoms (seen through the glass)
GC_STAIR_W = (-2200.0, 1470.0, -1400.0, 1730.0)   # rising east onto the deck
GC_STAIR_E = (1400.0, 1470.0, 2200.0, 1730.0)     # rising west
SHELF = (-1200.0, 1200.0, 1850.0, 1150.0)         # wall shelf x0, x1, front y, top z (to the wall)
SHELF_T = 24.0

# ------------------------------------------------------------------ soft-serve machine (west wall)
SS = (-2304.0, -520.0, -1720.0, 520.0)   # cabinet footprint
SS_T = 32.0
SS_CAB = 280.0                       # cabinet interior height, slab to SS_DECK
SS_DECK = 320.0
SS_LEDGE = -1560.0                   # drip-tray deck front edge (overhangs the cabinet)
SS_BODY_X = -1900.0                  # upper body front face
SS_TOP = 1180.0
SS_MOUTH = (-440.0, 440.0, 240.0)    # cabinet opening y span + height
SS_NOZZLES = [-360.0, 0.0, 360.0]
SS_STAIR = (-1900.0, 520.0, -1700.0, 1160.0)      # rising south onto the deck

# ------------------------------------------------------------------ milkshake bar (east wall) + the giant glass
BAR = (1840.0, -700.0, 2304.0, 1050.0)
BAR_Z = 420.0
GLASS = (1250.0, -380.0)
GLASS_R = 230.0
GLASS_H = 800.0
GLASS_TERR = [(800, 816, 246), (816, 832, 200), (832, 848, 140)]

# ------------------------------------------------------------------ walk-in freezer (south-east)
FZ = (1312.0, -2048.0, 2304.0, -1088.0)
FZ_H = 960.0
FZ_T = 32.0
FZ_DOOR = (1800.0, 100.0, 320.0)     # centre x, half width, height (north wall)
MYSTERY = (1640.0, -1760.0, 150.0, 32.0)   # the Mystery Flavour tub: x, y, r, rim height

# ------------------------------------------------------------------ chest freezer (south-west)
CF = (-2000.0, -1600.0, -1360.0, -1200.0)
CF_T = 24.0
CF_RIM = 128.0
CF_FLOOR = 32.0
CF_STAIR_OUT = (-1760.0, -1200.0, -1600.0, -944.0)   # rising south to the rim (x0, y0, x1, y1)
CF_STAIR_IN = (-1760.0, -1416.0, -1600.0, -1224.0)   # inside, rising north to the rim

# ------------------------------------------------------------------ ice cream cart (shop)
CART = (0.0, -1380.0)
CART_W, CART_D, CART_H = 520.0, 320.0, 440.0

# ------------------------------------------------------------------ toppings jars
JARS = [(600.0, -760.0), (800.0, -760.0), (1000.0, -760.0), (-1000.0, -560.0), (-800.0, -560.0)]
JAR_R, JAR_H = 90.0, 280.0

# ------------------------------------------------------------------ the secret Frozen Vault (sealed, below the world)
VAULT = (-640.0, -512.0, 640.0, 512.0, -1700.0, -880.0)

# ------------------------------------------------------------------ shop windows (south wall) + street backdrop
WINDOWS = [(-1000, -150, 260, 1300), (150, 1000, 260, 1300)]
STREET_D = 480


def lift_xy():
    a = math.radians(LIFT_A)
    return TOWER[0] + LIFT_D * math.cos(a), TOWER[1] + LIFT_D * math.sin(a)


def cone_r(z):
    return CONE_R0 + (CONE_R1 - CONE_R0) * (z - CONE_Z0) / (CONE_Z1 - CONE_Z0)
