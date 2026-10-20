"""Shared layout constants for wop_paddollhouse (Padman's Dollhouse): read by build_dollhouse.py (brushes, entities),
dh_house.py and dh_models.py (MD3 geometry), so the visible models and the invisible collision line up.

Scale: ~12u per cm ("doll scale": Padman is a 4.7 cm toy, the 1:12 dollhouse furniture is about his size, the girl's
bedroom around it is giant). x east, y north, bedroom floor z 0.
"""
import math

# ---------------------------------------------------------------- the bedroom
RX = 2304                      # floor x = -RX..RX
RYS, RYN = -2048, 2048         # floor y
RZ = 2560                      # ceiling
WALLT = 64                     # structural wall thickness
SKIRT_H, SKIRT_D = 96, 16      # skirting board
WIN = (-1024, 1024, 1152, 2240)  # north window: x0, x1, z0 (sill), z1
SILL_D = 96                    # window sill depth (y RYN-SILL_D .. RYN)
SKYBOX = dict(x0=-1280, x1=1280, y0=RYN + WALLT, y1=RYN + WALLT + 1536, z0=896, z1=2560)

# ---------------------------------------------------------------- the dollhouse "Rosewood Manor"
DX0, DX1 = -1024, 1024         # outer wall faces x
DY0, DY1 = 384, 1280           # open back (south) .. front facade outer face (north)
WT = 16                        # wall thickness
FL = [32, 368, 704, 1040]      # floor levels: ground, first, second, attic/terrace
SLAB = 16                      # floor slab thickness (FL[i]-16 .. FL[i])
ROOM_H = 320                   # FL[i] .. FL[i+1]-16
IWX = 320                      # interior walls at x = -IWX..-IWX+WT and IWX-WT..IWX
YI0, YI1 = DY0, DY1 - WT       # inner y range (back open at YI0)
DOOR_H = 208
IDOOR_Y = (416, 544)           # interior doors (hall <-> side rooms), all floors
FRONT_DOOR = (-80, 80)         # ground floor front door (north wall), x range
BALC_DOOR = (-64, 64)          # first floor door onto the balcony
SIDE_DOOR_Y = (1000, 1128)     # kitchen (west) / parlour (east) side doors, y range
WIN_Z = (96, 256)              # window opening z above each floor level

# the board the house stands on (and the front garden)
BOARD = (-1152, 320, 1152, RYN)        # x0, y0, x1, y1; top z 32, a 16u plinth step 32 wider round the open sides
BOARD_Z = 32
PLINTH = 32

# hall staircases: 21 steps of 16 x 32 per floor, 112 wide; flight 0 west rising north, 1 east rising north,
# 2 west rising south (out onto the terrace)
ST_W = (-304, -192)
ST_E = (192, 304)
ST_N_Y0 = 560                  # flights rising north start here (first riser)
ST_S_Y1 = 1232                 # the flight rising south starts here (first riser at its north end)
ST_RUN, ST_RISE, ST_N = 32, 16, 21

# porch + balcony (front, north)
PORCH = (-224, DY1, 224, DY1 + 192)
BALC_Z = FL[1]

# roofs: two gables (ridges along y) over the side blocks, flat terrace over the hall, tower on the terrace
PITCH = 40.0
TP = math.tan(math.radians(PITCH))
ROOF_Y0 = DY0 + 64             # the roof is cut back 64u at the open back (walk-in strip into each attic)
ROOF_Y1 = DY1 + 16             # front overhang
ROOF_T = 32                    # vertical slab thickness
GABLES = [(-1024, -320), (320, 1024)]   # x ranges (outer eave .. inner eave), ridge in the middle
RIDGE_W = 48                   # flat ridge walk
TOWER = (-176, 880, 176, DY1)  # x0, y0, x1, y1 (outer)
TOWER_F = FL[3]
TOWER_TOP = FL[3] + 336        # deck level (slab TOWER_TOP-16 .. TOWER_TOP)
TOWER_HATCH = (-64, 1040, 64, 1232)
PARAPET = 24

# ---------------------------------------------------------------- garden (on the board, north of the house)
POND = (-760.0, 1700.0, 300.0, 200.0)  # centre x, y, half axes rx, ry
POND_Z = 20                    # water surface
POND_BOT = -100
SWING = (560.0, 1720.0)

# ---------------------------------------------------------------- bedroom furniture
SHELF = (-RX, -1200, -RX + 384, 1200)  # bookshelf against the west wall: x0, y0, x1 (front), y1
SHELF_Z = [96, 576, 1056, 1536, 2016]  # shelf top levels (plinth top, 3 shelves, top of the unit)
SHELF_T = 32
SHELF_DIV = [-1200, -400, 400, 1200]   # divider centre y (32 thick)
SHELF_BACK = 24

BED = (1280, -96, RX, RYN)     # x0, y0, x1, y1 (head at the north wall)
BED_RAIL = (288, 384)          # side rail z range (under-bed clearance below)
BED_TOP = 576                  # mattress top
BED_LEG = 96                   # leg size

CHEST = (680, RYS, 1400, RYS + 432)    # toy chest against the south wall
CHEST_H = 432
CHEST_T = 32
CHEST_HOLE = (960, 1120, 176)          # broken front plank: x0, x1, top z (centred on the chest)

TEA = (-1000.0, -880.0)        # toy tea table centre
TEA_R, TEA_H = 220, 168
RUG = (0.0, -880.0, 980.0)

# ---------------------------------------------------------------- secret: the ballroom (sealed, under the world)
BALL = dict(x0=-576, x1=576, y0=-576, y1=576, z0=-2560, z1=-2048)
MINI = (-720.0, 1180.0)        # the little dollhouse in the nursery (second floor, west room); its door faces south


def flight(k):
    """(x0, x1, rises, y_first_riser) of hall flight k (0: GF->FF, 1: FF->SF, 2: SF->terrace)"""
    if k == 0: return ST_W[0], ST_W[1], 'n', ST_N_Y0
    if k == 1: return ST_E[0], ST_E[1], 'n', ST_N_Y0
    return ST_W[0], ST_W[1], 's', ST_S_Y1


def steps(k):
    """[(y0, y1, z_top)] of the 21 steps of flight k"""
    x0, x1, d, y = flight(k)
    out = []
    for j in range(ST_N):
        zt = FL[k] + ST_RISE * (j + 1)
        if d == 'n': out.append((y + ST_RUN * j, y + ST_RUN * (j + 1), zt))
        else: out.append((y - ST_RUN * (j + 1), y - ST_RUN * j, zt))
    return out


def stair_hole(k):
    """(x0, y0, x1, y1) opening in the slab above flight k: from 1.5 steps before the first step whose top + 56 would
    hit the slab underside, to the top of the flight"""
    x0, x1, d, y = flight(k)
    st = steps(k)
    under = FL[k + 1] - SLAB
    j0 = next(j for j, (a, b, z) in enumerate(st) if z + 56 > under)
    if d == 'n':
        return (x0, st[j0][0] - 48, x1, st[-1][0])
    return (x0, st[-1][1], x1, st[j0][1] + 48)


def roof_top(x, g):
    """height of the roof's top surface over x for gable g = (xa, xb): rises from both eaves (FL[3]) to the ridge"""
    xa, xb = g
    xm = (xa + xb) / 2
    d = min(x - xa, xb - x)
    return FL[3] + TP * min(d, (xb - xa) / 2 - RIDGE_W / 2)


def ridge_z(g):
    return roof_top((g[0] + g[1]) / 2, g)


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))
