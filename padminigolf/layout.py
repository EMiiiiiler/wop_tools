"""Mini Golf Madness layout: numbers shared by the generator and the models (x east, y north, turf z 0, ~4u per cm)."""
BOUNDS = (-2304, -2048, 2304, 2048)
HULL = (-3200, -2944, 3200, 2944)
ZBASE = -128
ZTOP = 2304

# ------------------------------------------------------------------ holes: lane rect (x0, y0, x1, y1), direction tee->cup
LANE_W = 360
RAIL_T, RAIL_H = 32, 24
FELT_Z = 4
HOLES = [
    (1, (-180, 220, 180, 1720), 'n'),          # windmill: through the tunnel in the base
    (2, (300, -560, 880, -200), 'e'),          # volcano approach
    (3, (-2040, -460, -1120, -100), 'w'),      # lake shore
    (4, (-180, -1940, 180, -660), 's'),        # clown: in at the mouth, out the back
    (5, (980, 1120, 2140, 1480), 'e'),         # loop-the-loop
    (6, (440, -1700, 1900, -1340), 'e'),       # rolling hills
]

# ------------------------------------------------------------------ windmill
MILL = (0, 1000)
MILL_R0, MILL_R1, MILL_H = 330, 262, 850       # octagon tower, foot / top radius, cap starts at MILL_H
STAGE_Z, STAGE_R = 400, 540                    # octagon ring (vertex at 0 deg like the tower)
CAP_TOP = 1200                                  # lookout deck top (flat, r 130)
TUNNEL_W, TUNNEL_H = 224, 224                   # half width, height
HUB_Z, SAIL_R = 1100, 560
MSTAIR = (541, 920, 1341, 1080)                 # x0 y0 x1 y1, 25 x 32 rising west onto the stage

# ------------------------------------------------------------------ lighthouse lake
LAKE = (-2150, 0, -850, 1260)
LAKE_FLOOR, LAKE_WATER = -40, -4
ISLAND = (-1560, 700)
LIGHT_R0, LIGHT_R1, LIGHT_GAL = 190, 150, 900   # tower radii, gallery deck top
GAL_R = 300
LAMP_TOP = 1100
BRIDGE = (-1300, 620, -850, 780)                # footbridge x0 y0 x1 y1 (island edge -> east bank)

# ------------------------------------------------------------------ volcano
VOLC = (1560, -340)
V1_R, V1_H = 640, 192                           # terrace
V2_R0, V2_R1, V2_H = 420, 300, 480              # cone up to the rim
CRATER_R, CRATER_Z = 170, 400
VSTAIR = (1488, 296, 1632, 680)                 # 12 x 32 rising south onto the terrace (north face)

# ------------------------------------------------------------------ clown
CLOWN = (0, -1300)
HEAD_R, HEAD_H = 420, 720
HAT_R, HAT_TOP = 200, 1000
MOUTH_W, MOUTH_H = 224, 224

# ------------------------------------------------------------------ clubhouse
CLUB = (-1960, -1640, -1080, -1000)             # x0 y0 x1 y1
CLUB_H = 320
CLUB_DOOR = (-1600, -1440)                      # door x span in the north wall
CSTAIR = (-1080, -1640, -920, -968)             # 21 x 32 rising south up the east side (top next to the roof)

BALL = (0, -150)
BALL_R, TEE_H = 280, 80
LOOP = (1700, 1300)
SECRET = (-640, 1830)                           # the 19th hole
CAVERN_Z = -2048
