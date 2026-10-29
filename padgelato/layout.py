"""Shared layout constants for wop_padgelato (Padman's Gelato Parlour).

Padman scale (~8u per cm, catalog models at 1.0). x east, y north, floor z 0, ceiling z 2048.

Three bands front to back (after the reference photo): the seating area by the street windows (south, y < 0), the
long mint display counter with its curved glass across the room (y 0..300), and the ice cream kitchen behind it
(north, y > 300)."""
import math

HX, HY = 2304, 2048
CEIL = 2048
WALL_T = 32
FLOOR_T = 64

# ------------------------------------------------------------------ the giant cone (centre of the seating area)
TOWER = (0.0, -980.0)
TW_N = 24
STAND = (250.0, 290.0, 170.0)        # chrome cup: r bottom, r top, height
CONE_R0, CONE_R1 = 150.0, 430.0      # waffle cone radius at the stand top / at the rim
CONE_Z0, CONE_Z1 = 170.0, 960.0
RIM_R, RIM_Z = 470.0, 1000.0         # wafer rim (walkable deck z 1000)
SCOOP_TERR = [(1000, 1080, 300), (1080, 1160, 270), (1160, 1230, 210), (1230, 1270, 140)]   # z0, z1, r collision terraces
SCOOP_R, SCOOP_H = 330.0, 300.0      # visible big scoop (ellipsoid centred on the deck)
LIFT_A = 180.0                       # the scoop lift stands west of the cone
LIFT_D = 574.0                       # distance from the tower centre
LIFT_R = 96.0

# ------------------------------------------------------------------ the prep line (kitchen, north wall): tubs being filled
GC = (-1300.0, 1450.0, 1300.0, 1750.0)   # x0, y0 (glass front), x1, y1 (back)
GC_PLINTH = 60.0
GC_TUB = 368.0                       # ice cream surface in the tubs
GC_DECK = 400.0                      # walkable frame
GC_TUBS = [(-1150.0 + k * 290.0, -1150.0 + k * 290.0 + 220.0) for k in range(8)]   # x spans
GC_TUB_Y = (1500.0, 1700.0)
GC_PAN_Z = 240.0                     # pan bottoms (seen through the glass)
GC_STAIR_W = None                    # (no stairs: pads up)
GC_STAIR_E = None
SHELF = (-1200.0, 1200.0, 1850.0, 1150.0)         # wall shelf x0, x1, front y, top z (to the wall)
SHELF_T = 24.0

# ------------------------------------------------------------------ soft-serve machine (kitchen, west wall)
SS_DY = 820.0
SS = (-2304.0, -520.0 + SS_DY, -1720.0, 520.0 + SS_DY)   # cabinet footprint
SS_T = 32.0
SS_CAB = 280.0                       # cabinet interior height, slab to SS_DECK
SS_DECK = 320.0
SS_LEDGE = -1560.0                   # drip-tray deck front edge (overhangs the cabinet)
SS_BODY_X = -1900.0                  # upper body front face
SS_TOP = 1180.0
SS_MOUTH = (-440.0 + SS_DY, 440.0 + SS_DY, 240.0)    # cabinet opening y span + height
SS_NOZZLES = [-360.0 + SS_DY, SS_DY, 360.0 + SS_DY]
SS_STAIR = (-1900.0, 520.0 + SS_DY, -1700.0, 1160.0 + SS_DY)      # rising south onto the deck

# ------------------------------------------------------------------ milkshake bar (seating, east wall) + the giant glass
BAR = (1840.0, -1750.0, 2304.0, -350.0)
BAR_Z = 420.0
GLASS = (1250.0, -640.0)
GLASS_R = 230.0
GLASS_H = 800.0
GLASS_TERR = [(800, 816, 246), (816, 832, 200), (832, 848, 140)]

# ------------------------------------------------------------------ walk-in freezer (kitchen, east wall; door in its west wall)
FZ = (1700.0, 300.0, 2304.0, 1300.0)
FZ_H = 960.0
FZ_T = 32.0
FZ_DOOR = (900.0, 100.0, 320.0)      # centre y, half width, height (west wall)
MYSTERY = (1960.0, 520.0, 150.0, 32.0)   # the Mystery Flavour tub: x, y, r, rim height

# ------------------------------------------------------------------ chest freezer (kitchen, north-east corner)
CF = (1700.0, 1480.0, 2280.0, 1880.0)
CF_T = 24.0
CF_RIM = 128.0
CF_FLOOR = 32.0
CF_STAIR_OUT = (1444.0, 1590.0, 1700.0, 1750.0, 'e')   # rising east to the rim (x0, y0, x1, y1, dir)
CF_STAIR_IN = (1724.0, 1590.0, 1916.0, 1750.0, 'w')    # inside, rising west to the rim
CF_LID = 'n'

# ------------------------------------------------------------------ ice cream cart (seating, by the windows)
CART = (-1150.0, -1720.0)
CART_W, CART_D, CART_H = 520.0, 320.0, 440.0

# ------------------------------------------------------------------ toppings jars (kitchen, in front of the prep line)
JARS = [(-400.0, 1270.0), (-200.0, 1270.0), (0.0, 1270.0), (200.0, 1270.0), (400.0, 1270.0)]
JAR_R, JAR_H = 90.0, 280.0

# ------------------------------------------------------------------ the display counter (curved glass) across the room
DC_X0, DC_X1 = -1350.0, 1350.0       # straight run; rounded ends of radius DC_R beyond
DC_Y0, DC_Y1 = 0.0, 300.0            # front (customer side), back (kitchen side)
DC_R = 150.0
DC_BODY = 300.0                      # mint cabinet top / tub shelf
DC_TOP = 560.0                       # flat glass top (walkable)
DC_GLASS_D = 50.0                    # the slanted front glass meets the top this far back

# ------------------------------------------------------------------ batch freezer (kitchen, east of centre)
BF = (450.0, 720.0, 950.0, 1100.0)   # body footprint (front y 720 faces the counter)
BF_H = 640.0
BF_DRUM = (700.0, 380.0, 150.0)      # porthole: centre x, centre z, radius
BF_DRUM_D = 70.0                     # glass dome depth in front of the body

# ------------------------------------------------------------------ pasteuriser vat (kitchen, west of centre)
VAT = (-700.0, 920.0)
VAT_R0, VAT_R1 = 270.0, 340.0        # inner / outer radius of the walkable rim
VAT_RIM = 420.0
VAT_MILK = 390.0                     # milk surface (30 below the rim: barrier-jump out)
VAT_BEAM_Z = (620.0, 660.0)          # motor bridge over the vat

# ------------------------------------------------------------------ seating
BOOTHS = [(-2044.0, -1500.0), (-2044.0, -540.0)]   # booth centres along the west wall (bench-table-bench along y)
BOOTH_L, BOOTH_W = 900.0, 520.0

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
