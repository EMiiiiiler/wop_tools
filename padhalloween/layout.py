"""Shared layout constants for wop_padhalloween (Pumpkin Hollow): read by build_halloween.py (brushes, entities) and
hw_models.py (MD3 geometry), so the visible models and the invisible collision line up.

Scale: ~64u per metre (Padman 56u ~ a small Padman), giant fantasy pumpkins. x east, y north, ground z 0.
"""
import math

# ---------------------------------------------------------------- the hollow
HX = 2304                      # playable ground x = -HX..HX
YS, YN = -2048, 2048           # playable ground y
SKY = dict(x0=-3328, x1=3328, y0=-3072, y1=3072, z0=-768, z1=2560)
SLAB_BOT = -512
BANK_Z = 352                   # top of the earth banks round the hollow
BANK_RUN = 176                 # horizontal run of the steep inner bank face

# ---------------------------------------------------------------- the manor (north centre): Second Empire house
MAN = (-512, 1280, 512, 1728)          # main block footprint (outer wall faces)
MAN_F0 = 32                            # ground floor level
MAN_F1 = 256                           # upper floor level (slab 240..256)
MAN_C1 = 464                           # upper floor ceiling (slab 464..480)
MAN_EAVE = 480                         # top of the walls / foot of the mansard roof
MAN_DECK = 640                         # flat top of the mansard roof (widow's walk)
MAN_IN = 48                            # mansard inset (lower slope run)
MAN_OVER = 16                          # eave overhang
WALL = 16                              # timber wall thickness (inside the MD3 siding)
PORCH = (-384, 1152, 384, 1280)        # porch deck (z 0..MAN_F0), roof = balcony at MAN_F1
PORCH_STEPS = (-160, 1088, 160, 1152)  # two steps up to the porch
HALL_X = 128                           # interior walls at x = +-HALL_X (hall in the middle)
CUPOLA = (-112, 1408, 112, 1632)       # cupola on the roof deck: plinth 64 high, posts, onion roof
CUPOLA_Z = MAN_DECK + 64               # cupola floor
CUPOLA_TOP = CUPOLA_Z + 160            # top of the posts (roof starts)
# ground floor openings (u along the wall, z) per wall; 'door' entries are walk-through
WIN_G = (MAN_F0 + 64, MAN_F0 + 192)    # ground-floor window z range
WIN_U = (MAN_F1 + 64, MAN_F1 + 176)    # upper-floor window z range
# hall stair (U): flight 1 north along the west half, landing, flight 2 south along the east half
STAIR1 = (-112, -16, 1312)             # x0, x1, y start (rises north from MAN_F0)
STAIR2 = (16, 112)                     # x0, x1 (rises south to MAN_F1)

# ---------------------------------------------------------------- the hanging tree (centre) + treehouse
TREE = (0.0, -160.0)
TRUNK_R = 112                          # collision radius of the trunk
SPIRAL_R = (TRUNK_R, 248)              # spiral stair inner/outer radius
SPIRAL_A0 = 200.0                      # angle of the first step (deg), counter-clockwise rise
PLAT_Z = 384                           # treehouse deck height
PLAT_R = 352                           # round deck outer radius
TH_DECK = (112, -400, 560, 80)         # rectangular deck east of the trunk (x0, y0, x1, y1) relative to TREE
TH_HUT = (264, -336, 520, -112)        # hut footprint (relative to TREE), door west
TH_HUT_H = 160

# ---------------------------------------------------------------- graveyard + mausoleum + crypt (north-west)
GRAVE = (-2304, 320, -768, 2048)       # fenced graveyard (fence on the south + east sides)
GRAVE_GATES = [('s', -1600, 192), ('s', -1000, 160), ('e', 900, 192)]   # (side, centre coordinate, width)
MAUS = (-1824, 1312, -1376, 1760)      # mausoleum (stone walls 24), door south, podium z 32
MAUS_F = 32
MAUS_H = 288                           # wall top (eaves) above ground
MAUS_STAIR = (-1680, -1520)            # the stair down the middle (x0, x1), 16 steps of 24 north from y 1376
CRYPT = (-2048, 1760, -1152, 1984)     # vault under the graveyard (z CRYPT_F .. CRYPT_C)
CRYPT_F, CRYPT_C = -224, -16

# ---------------------------------------------------------------- pumpkin patch + the Great Pumpkin (north-east)
PATCH = (768, 320, 2304, 2048)
GPUMP = (1480.0, 1200.0)
GP_R = 448                             # widest radius
GP_H = 560
GP_FACE = 215.0                        # direction the carved face looks (deg): towards the hollow centre
GP_LID = 150                           # radius of the lid hole at the top
GP_TOPZ = 548                          # walkable top ring height

# ---------------------------------------------------------------- witch's cottage + cauldron (south-west)
COT = (-1792, -1408, -1280, -1056)     # cottage footprint, door east, floor z 16
COT_F = 16
COT_EAVE = 224
COT_RIDGE = 360                        # flat ridge walk (96 wide) on top of the 40-degree roof
CAUL = (-760.0, -1200.0)
CAUL_R = 288                           # widest outer radius of the pot
CAUL_RIM_R = 236                       # outer radius at the rim
CAUL_IN = 212                          # inner radius (water) at the rim
CAUL_BOT = 40                          # pot sits on fire logs; inner floor
CAUL_FLOOR = 64
CAUL_RIM = 304
CAUL_WATER = 264

# ---------------------------------------------------------------- corn maze (south-east)
MAZE = (960, -2048, 2304, -704)        # 7 x 7 cells of 192
MAZE_CELL = 192
MAZE_H = 208

# ---------------------------------------------------------------- gate plaza (south) + misc
GATE = (0.0, -1660.0)                  # stone arch over the path
GATE_W = 320
BONFIRE = (-1480.0, -280.0)
STAND = (1500.0, -330.0)               # pumpkin market stand + hay wagon
WELL = (-620.0, 620.0)

# ---------------------------------------------------------------- secret: the witch's lair (sealed, under the world)
LAIR = dict(x0=-448, x1=448, y0=-384, y1=384, z0=-2560, z1=-2048)


SPIRAL_DA = 13.0                       # angle per spiral step (deg)
SPIRAL_N = PLAT_Z // 16


def spiral_steps():
    """treehouse spiral stair round the trunk: [(a0, a1, z_top)] for each 16u step, counter-clockwise from SPIRAL_A0"""
    return [(SPIRAL_A0 + SPIRAL_DA * k, SPIRAL_A0 + SPIRAL_DA * (k + 1), 16 * (k + 1)) for k in range(SPIRAL_N)]


def deck_gap():
    """angular range (deg, may exceed 360) the round deck leaves open over the top of the spiral (headroom rule)"""
    st = spiral_steps()
    k0 = next(k for k, (a0, a1, z) in enumerate(st) if z + 56 > PLAT_Z - 16)
    return st[k0][0] - 4, st[-1][1] + 10


CAUL_STEPS = 15                        # steps inside the cauldron from its floor up to the rim
CAUL_STEP_DA = 10.5
CAUL_STEP_A0 = 30.0


def caul_steps():
    return [(CAUL_STEP_A0 + CAUL_STEP_DA * k, CAUL_STEP_A0 + CAUL_STEP_DA * (k + 1), CAUL_FLOOR + 16 * (k + 1)) for k in range(CAUL_STEPS)]


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))
