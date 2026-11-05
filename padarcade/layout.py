"""Midnight Arcade layout: numbers shared by the generator and the models (x east, y north, carpet z 0, ~8u per cm)."""
BOUNDS = (-2304, -2048, 2304, 2048)            # the hall's inner faces
CEIL = 2048

# ------------------------------------------------------------------ Claw King (centre)
CLAW = (-600, -600, 600, 600)                  # outer footprint
BASE_H = 480                                   # cabinet base (glass case floor = BASE_H)
GLASS_TOP, ROOF_TOP = 1280, 1344
WALL = 40
FLAP = (-560, -336)                            # y span of the prize flap in the east face, 0..208 high
HOLE = (-336, -112, -560, -336)                # prize hole x0 x1 y0 y1 (top of the chute ramp)
PILE = [((-200, -100, 560, 560), 16), ((-100, 0, 520, 540), 16), ((0, 100, 480, 520), 16), ((100, 200, 440, 500), 16)]

# ------------------------------------------------------------------ Roll-a-Ball alley (east)
LANES = [(-1000, -640), (-560, -200), (-120, 240)]     # y spans
LANE_X0, RAMP_X0, RAMP_X1, DECK_X1 = 1000, 1250, 1700, 1950
DECK_Z = 300
BOARD_TOP = 1100

# ------------------------------------------------------------------ air hockey (west)
TABLE = (-2000, -400, -1000, 400)
TABLE_Z = 400
TSTAIR = (-2000, 424, -1200, 552)              # 25 x 32 rising east along the north side

# ------------------------------------------------------------------ prize wall (south-west)
SHELF = (-2200, -2048, -700, -1768)            # x0 y0 x1 y1 (against the south wall)
SHELF1_Z, SHELF2_Z = 448, 896
SHELF2_X1 = -1300                               # the top shelf stops here (room for the pad below)
PSTAIR = (-1596, -1744, -700, -1616)           # 28 x 32 rising west along the shelf front
COUNTER = (-2000, -1350, -900, -1150)
COUNTER_H = 320

# ------------------------------------------------------------------ north side
STAGE = (-700, 1500, 700, 2048)
STAGE_Z = 96
WHEEL = (0, 1990, 1100)
WHEEL_R = 700
CAB_W, CAB_D, CAB_H = 480, 440, 1200
CAB_ROWS = [(-2100, 900, 3), (900, 900, 2)]    # x0, y0 (back), count (facing south)
DANCE = (1100, 1450, 1900, 1950)
DANCE_Z = 48

# ------------------------------------------------------------------ south-east
BOOTH = (1600, -1850, 2100, -1450)             # photo booth (curtain opening on the west side)
RACER = (500, -1400)
SECRET_Z = -2048
