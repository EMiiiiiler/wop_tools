"""Spin Cycle (wop_padlaundry) - layout constants shared by the builder and the models.
Padman scale (~8u per cm, catalog models at 1.0). x = west(-)/east(+), y = south(-, the shopfront)/north(+)."""
X0, Y0, X1, Y1 = -2304, -2048, 2304, 2048
CEIL = 2048

# ---- west: front-loading washers on a pedestal
PED = 224                         # pedestal top
PED_X = (-2304, -1192)            # pedestal (washers stand on its back part)
PED_Y = (-1440, 1440)
W_X = (-2304, -1704)              # washer bodies (front at -1704)
W_H = 680                         # body height above the pedestal
W_YC = (-1120, -560, 0, 560, 1120)
W_HALF = 280                      # half width along y
W_DRUM_R = 220                    # drum cavity radius (flat floor facet at PED - 50)
W_DRUM_Z = PED + 170              # drum axis height
W_DOOR_R = 170                    # door opening (sill = pedestal top)
W_DRUM_X = (-2224, -1744)         # drum cavity x range (door hole from -1744 to the front)
W_WATER = PED - 8                 # sudsy water in the bottom of each drum
W_DOOR_W = 380                    # open door length (sticks out +x from the hinge)

# ---- east: stacked dryers on a stepped plinth
D_X = (1704, 2304)
D_YC = W_YC
D_HALF = 280
PLINTH = 112                      # plinth top (7 steps of 16 from the floor)
PLINTH_X = (1480, 1704)           # the steps (rising east)
D_LOW_H = 640                     # lower row body top; upper row up to D_TOP
D_TOP = 1280
D_DRUM_R = 200                    # lower dryer drum (floor facet at the plinth top)
D_DRUM_Z = PLINTH + D_DRUM_R
D_DRUM_X = (1704, 2224)
SECRET_DRYER = -1120              # its lint screen at the back of the drum is the secret

# ---- north: utility sink
SINK = (-560, 1504, 560, 2048)    # outer footprint
SINK_Z = (400, 720)               # basin underside, rim top
SINK_T = 48                       # wall thickness
SINK_FLOOR = 432
SINK_WATER = 704
BOARD = (560, 1504, 1104, 2048)   # drainboard counter beside the sink (top = rim height)

# ---- centre
ISLAND = (-600, -600, 600, 1080)  # back-to-back washer island (fronts face -x / +x), orange counter on top
ISLAND_YC = (-320, 240, 800)
ISLAND_TOP = 704
TABLES = [(-1100, -1700, -700, -260), (700, -1700, 1100, -260)]   # folding tables x0 y0 x1 y1
TABLE_Z = 720
TABLE_T = 32
PILE = (0, -1350)                 # Mount Laundry centre
PILE_R0, PILE_STEP_R, PILE_TIERS = 440, 22, 14

# ---- vending machines against the north wall (x0, x1); depth along y from VEND_Y to the wall
VEND_Y = 1792
VEND_TOP = 1000
SOAPVEND = (-1300, -900)          # detergent bottles behind glass
CHANGE = (1104, 1504)
SNACK = (1504, 1904)
DRINK = (1904, 2304)

# ---- south: shopfront with joined seats along the windows
DOOR_X = (-320, 320)                          # entrance (glass doors, closed)
WIN = [(-2176, -1560), (-1000, -400), (400, 1000), (1560, 2176)]   # shop windows (x ranges)
WIN_Z = (200, 1500)
BENCHES = [(-2200, -1640), (-1080, -440), (440, 1080), (1640, 2200)]   # joined seats (x ranges), 4 shells each
BENCH_Y = -1945                   # bench centre line (seats face north)

# ---- secret: the Lost Sock Dimension (sealed, under the floor)
SOCK = dict(x0=-640, x1=640, y0=-512, y1=512, z0=-1600, h=640)
