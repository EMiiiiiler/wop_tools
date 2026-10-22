"""Shared layout constants for wop_padbbq (Backyard BBQ): read by build_bbq.py (brushes, entities) and bb_models.py
(MD3 geometry), so the visible models and the invisible collision line up.

Scale: 5u per cm (Padman 56u ~ an 11 cm toy). A Kiwi backyard on a summer afternoon: weatherboard house to the north
(the sun is in the north), deck + pergola, a kettle barbecue, a paddling pool, a shed, a kennel, a picnic table under
a parasol, a raised vege bed, paling fences. x east, y north, lawn z 0.
"""
import math

# ---------------------------------------------------------------- the yard
XW = 2304                      # lawn x = -XW..XW
YS, YN = -2048, 2048           # lawn y (house wall face at YN)
HULL = dict(x0=-2816, x1=2816, y0=-2560, y1=2368, z0=-256, z1=2816)
FENCE_H = 900                  # paling fence height (1.8 m)
FENCE_T = 24
HOUSE_EAVE = 1440              # gutter line of the house wall
HOUSE_T = 64                   # house wall thickness (YN .. YN+HOUSE_T)
WIN_W = (-1900, -1060, 420, 1120)      # living room window over the deck: x0, x1, z0, z1
WIN_E = (900, 1500, 560, 1100)         # kitchen window: x0, x1, z0, z1
WIN_S = (1820, 2060, 820, 1100)        # small bathroom window
TAP = (1260.0, 230.0)                  # outdoor tap on the house wall: x, z

# ---------------------------------------------------------------- deck + pergola (north-west)
DECK = (-2304, 1408, 640, 2048)        # x0, y0, x1, y1
DECK_Z = 144                           # board top (9 steps of 16)
DECK_T = 16                            # boards + bearers slab (DECK_Z-16 .. DECK_Z)
DECK_POSTS = 640                       # post grid under the deck
DECK_STEPS = [('s', -1400, -1000), ('e', 1560, 1880)]   # front steps (x range) and side steps (y range)
LATTICE_GAPS = [(-2050, -1850), (-720, -520), (180, 380)]   # holes in the front lattice skirt (crawl under the deck)
PERGOLA = (-560, 1440, 640, 2048)      # x0, y0, x1, y1 (posts at the front corners + middle)
PERG_TOP = DECK_Z + 1040               # walkable slat roof top (2.1 m above the deck)
PERG_POST = 28

# ---------------------------------------------------------------- the kettle barbecue (centre)
GRILL = (-300.0, 760.0)
G_RIM_R = 150                          # bowl rim radius
G_RIM_Z = 378                          # rim top
G_GRATE_Z = 346                        # cooking grate (walkable)
G_COAL_Z = 300                         # charcoal surface
G_BOT_Z = 236                          # bowl bottom
G_LEG_R = 190                          # leg foot radius
G_PAN_Z = 112                          # ash catcher pan top
G_PAN_R = 120
G_HOT_R = 48                           # hurt zone over the coal heap (grate centre)
BRIQ_STEPS = 7                         # briquette steps from the lawn up to the ash pan

# ---------------------------------------------------------------- paddling pool (west)
POOL = (-1450.0, 120.0)
POOL_R_OUT = 340
POOL_R_IN = 276
POOL_WALL_Z = 128                      # top of the inflatable rings
POOL_FLOOR = 8
POOL_WATER = 96

# ---------------------------------------------------------------- shed (south-west)
SHED = (-2248, -1992, -1392, -1424)    # x0, y0, x1, y1 (outer)
SHED_WT = 24
SHED_DOOR = (-2000, -1800)             # north wall door x range
SHED_DOOR_H = 880
SHED_ROOF_N, SHED_ROOF_S = 1040, 1100  # pent roof top at the north / south eave
SHED_BENCH = (-2224, -1968, -1700, -1832)  # workbench along the south wall: x0, y0, x1, y1
SHED_BENCH_Z = 440

# ---------------------------------------------------------------- kennel (north-east)
KENNEL = (1560, 860, 1960, 1260)       # x0, y0, x1, y1
KEN_WALL = 300
KEN_DOOR = (1000, 1120, 190)           # west wall door: y0, y1, height
KEN_PITCH = 40.0
KEN_RIDGE_W = 40

# ---------------------------------------------------------------- picnic table + parasol (south-east)
TABLE = (1300.0, -1100.0)
TABLE_L, TABLE_W = 760, 360            # top size (long axis x)
TABLE_Z = 376
BENCH_Z = 224
BENCH_W = 128
BENCH_GAP = 96                         # gap between table edge and bench
PARASOL_R = 720
PARASOL_Z = 1060                       # canopy rim height

# ---------------------------------------------------------------- sun lounger (south-centre)
LOUNGER = (-760.0, -1180.0)            # centre of the frame, long axis x (backrest at the west end)
LOUNGER_L, LOUNGER_W = 960, 300
LOUNGER_SEAT = 176
LOUNGER_BACK = 38.0                    # backrest slope (deg, walkable)
TOWEL_RUN = 300                        # towel ramp from the foot end down to the lawn

# ---------------------------------------------------------------- raised vege bed (east fence)
VEGE = (1880, -560, 2256, 520)         # x0, y0, x1, y1 (outer)
VEGE_Z = 160                           # sleeper top
VEGE_SOIL = 136

# ---------------------------------------------------------------- lawn bits
SPRINKLER = (120.0, -420.0)
HOSE_REEL = (1240.0, 1840.0)
ANTHILL = (560.0, -1780.0)
ANT_R = 150
ANT_H = 80
ANT_DOOR = 90.0                        # direction (deg) the ant hill's entrance faces: north

# ---------------------------------------------------------------- secret: the ant colony (sealed, under the world)
COLONY = dict(x0=-896, x1=896, y0=-704, y1=704, z0=-2560, z1=-2112)


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


# little gabled houses (ridge along x): the kennel and the kids' cubby house
#   rect, wall height, pitch, ridge walk width, overhang, door (side, u0, u1, height), windows [(side, u0, u1, z0, z1)]
KEN = dict(rect=KENNEL, H=KEN_WALL, pitch=KEN_PITCH, ridge=KEN_RIDGE_W, ov=24, door=('w', KEN_DOOR[0], KEN_DOOR[1], KEN_DOOR[2]), wins=[],
           wall='timber', roof='kennel_roof', inner='kennel_in', sign='kennel_sign', t=16)
CUBBY = dict(rect=(180, -1200, 740, -680), H=480, pitch=34.0, ridge=48, ov=40, door=('n', 390, 530, 300),
             wins=[('w', -1020, -860, 200, 340), ('e', -1020, -860, 200, 340), ('s', 380, 540, 200, 340)],
             wall='cubby_wall', roof='cubby_roof', inner='cubby_in', sign=None, t=16)


def roof_top(spec, y):
    """top surface height of a little house's roof over y (ridge along x)"""
    x0, y0, x1, y1 = spec['rect']
    d = min(y - y0, y1 - y)
    t = math.tan(math.radians(spec['pitch']))
    return spec['H'] + t * min(d + spec['ov'], (y1 - y0) / 2 + spec['ov'] - spec['ridge'] / 2)


def ridge_z(spec):
    x0, y0, x1, y1 = spec['rect']
    t = math.tan(math.radians(spec['pitch']))
    return spec['H'] + t * ((y1 - y0) / 2 + spec['ov'] - spec['ridge'] / 2)


def ken_roof_top(y): return roof_top(KEN, y)
def ken_ridge_z(): return ridge_z(KEN)


SANDPIT = (-560.0, -260.0)
SAND_R = 250
SAND_RIM = 32
SAND_Z = 16
ROUND_BED = (980.0, -380.0)
ROUND_BED_R = 190
TOY_CAR = (-80.0, 180.0)
SLIDE = (260, 600, 420, 700)          # platform x0, y0, x1, y1 (the chute runs east down to the lawn)
SLIDE_Z = 480
SLIDE_RUN = 760


def shed_roof_z(y):
    x0, y0, x1, y1 = SHED
    return SHED_ROOF_N + (SHED_ROOF_S - SHED_ROOF_N) * (y1 + 40 - y) / (y1 - y0 + 80)


def deck_steps(which):
    """[(x0, y0, x1, y1, z_top)] for a deck stair: 's' front (falls south), 'e' side (falls east)"""
    out = []
    n = DECK_Z // 16
    for kind, a, b in DECK_STEPS:
        if kind != which: continue
        for j in range(n - 1):
            zt = 16 * (j + 1)
            if kind == 's':
                y1 = DECK[1] - 32 * (n - 2 - j); y0 = y1 - 32
                out.append((a, y0, b, y1, zt))
            else:
                x0 = DECK[2] + 32 * (n - 2 - j); x1 = x0 + 32
                out.append((x0, a, x1, b, zt))
    return out


def briq_steps():
    """briquette steps up to the ash pan, rising toward the grill from the south-east: [(x0, y0, x1, y1, z)]"""
    gx, gy = GRILL
    out = []
    for j in range(BRIQ_STEPS):
        zt = 16 * (j + 1)
        x0 = gx + G_PAN_R + 4 + 32 * (BRIQ_STEPS - 1 - j)
        out.append((x0, gy - 48, x0 + 32, gy + 48, zt))
    return out
