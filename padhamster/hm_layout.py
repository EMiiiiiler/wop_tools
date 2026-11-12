"""PadHamster (wop_padhamster) - layout constants shared by the generator and the model module.

Padman scale (~8u per cm, catalog models at 1.0). Room x -2048..2048, y -1792..1792 (north = +y), floor 0, ceiling 2048.
"""
X0, Y0, X1, Y1 = -2048, -1792, 2048, 1792
ZC = 2048

# ---- cage wall: wooden shelf unit on the north wall carrying three stacked cages and the bottle shelf
SX0, SX1 = -1728, 704            # outer x of the shelf unit (side panels 32 thick)
SPW = 32
SY0 = 1216                       # shelf front
CY0 = 1376                       # cage front (the board in front of it is an open ledge, 160 deep)
LV = (480, 960, 1440, 1760)      # burrow, wheel, penthouse floor, bottle shelf (board tops)
BT = 32                          # board thickness
IX0, IX1 = SX0 + SPW, SX1 - SPW  # inside the side panels

# ---- tube lifts inside the cages (pad up through a hole in the board above, collar round the hole)
LIFT_A = (480, 1584)             # burrow -> wheel
LIFT_B = (-1440, 1584)           # wheel -> penthouse
HOLE = 112                        # half size of the hole
COLLAR_H = 48

# ---- burrow cage contents
TUNNEL = (-1000, -600, 1520)     # x0, x1, centre y of the cardboard crawl tube
NEST_C = (-1640, 1740)           # the nest pile in the dark west-back corner (secret)

# ---- wheel cage contents
WHEEL_C = (-100, 1600)           # wheel centre (x, y); axis along y
WHEEL_R = 200
HOUSE = (-1200, 1520, -912, 1760)   # hide-house x0 y0 x1 y1
HOUSE_H = 208

# ---- feed corner: seed sack stairs up to the burrow level, slide down from the penthouse
STAIR = (-1888, 96, -1696, 1056)    # 16u stairs rising north to LV[0]
LANDING = (-1888, 1056, -1440, SY0)
DECK = (-2048, 1056, -1600, SY0)     # slide entry deck at LV[2]
SLIDE_X = -1952
SLIDE = [(SLIDE_X, 1056, 1440), (SLIDE_X, -720, 16), (SLIDE_X, -880, 16)]
FEEDBIN = (-1660, -300, -1340, 20)
FEEDBIN_H = 360

# ---- shop counter (north-east) and the mid shelf over the back aisle
COUNTER = (1088, 896, 2048, 1408); COUNTER_Z = 560
MIDSHELF = (SX1, 1600, 2048, 1792); MID_Z = 1160

# ---- cat tree (room centre)
CT_BASE = (-400, -400, 400, 400)
CT_P1 = (-400, -400, 0, 0); P1_Z = 400          # cubby roof
CT_P2 = (16, 16, 400, 400); P2_Z = 800
CT_P3 = (-328, -328, -72, -72); P3_Z = 1200
POST_A = (208, 208, 48)
POST_B = (-200, -200, 40)
BALL_R = 760                                    # exercise ball loop radius round the cat tree

# ---- bird cage tower (south-east)
CAB = (1248, -1632, 1952, -928); CAB_Z = 700
BIRD_C = (1600, -1280); BIRD_R = 208; BIRD_TOP = 1484   # roof slab 1484..1500

# ---- pet carrier + bed (south-west)
CARRIER = (-1760, -1600, -1200, -1104); CARRIER_Z = 520
BED_C = (-1450, -650); BED_R = 230

# ---- window (south wall)
WIN = (-1024, 1024, 800, 1700)
SILL = (-1100, -1792, 1100, -1600); SILL_Z = 760

VAULT = (-512, -384, 512, 384); VAULT_Z = -1536
