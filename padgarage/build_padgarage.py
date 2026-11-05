#!/usr/bin/env python3
"""Padman's Garage (wop_padgarage) - FFA in a suburban double garage at night, built on woplib + texlib.

    OUT=<dir> python3 build_padgarage.py          (wopbuild.py padgarage all)

Scale 1 m = 600u. Garage interior x -1800..1800, y 0..3600 (roller door on the south gable at y 0), driveway y < 0,
alleys east and west, a back strip behind the garage; everything inside one sealed sky hull. Levels: floor 0, car
cabin 240, car roof 920, workbench 540, shelves 400 / 800 / 1200, loft 1456, garage roof (gable, ridge 2172).
See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, cyl, hull, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import gr_models as GM
import gr_street as GS

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
PX0, PY0, PX1, PY1 = INFO['bounds']                 # playable rectangle (sightlines, prop bounds)
HX0, HY0, HX1, HY1 = INFO['hull']                   # sky hull inner faces (the street runs on past the clip)
X0, X1, Y1 = -2304, 2304, PY1                       # our lot: side fences and back fence
ZSKY = 5200
K = MapKit(MAP, NS, LONG, (PX0, PY0, PX1, PY1), worldspawn={'_ambient': '12', '_color': '0.7 0.78 1', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout
GX0, GX1, GY0, GY1 = -1800, 1800, 0, 3600            # garage interior
WT = 32                                               # wall thickness
EAVE = 1440                                           # wall top at the inner face
SLOPE = 0.4                                           # roof pitch (21.8 deg)
RIDGE_W = 60                                          # half-width of the flat ridge walk


def roof_under(x): return EAVE + (GX1 - abs(x)) * SLOPE  # roof underside height over the garage


def roof_top(x): return roof_under(x) + 32


DOOR = (-1440, 1440, 1260)                            # roller door opening x0 x1 top
PIER = 160                                            # half-width of the pier splitting it into two doors
DOOR_BOTTOM = 560                                     # curtain hangs down to here (walk under)
SIDE_DOOR = (1010, 1250, 420)                         # east wall doorway y0 y1 top
DRIVE_Y0 = -3000                                      # front property line: the footpath starts here
FOOT = (-3700, DRIVE_Y0)                              # footpath (y0, y1)
BERM = (-4100, -3700)                                 # grass verge: trees, lamps, bins
ROAD = (-7100, -4100); ROAD_Z = -16                   # road (kerb 16u: a step, no ramp needed)
FBERM = (-7500, -7100); FFOOT = (PY0, -7500)          # far verge + far footpath; the far property line is PY0
STREET_X = PX1                                        # roadworks barriers close the street at +-STREET_X
ROAD_X = 9300                                         # the road runs on to the houses at the ends of the street
BACK_Y1 = Y1                                          # back strip y 3632..Y1

CAR = (-1020, 1760)                                   # car centre (model space origin), front = -y
CAR_X0, CAR_X1, CAR_Y0, CAR_Y1 = -1530, -510, 500, 3020
CABIN_Y0, CABIN_Y1 = CAR[1] - 330, CAR[1] + 1150      # dash .. tailgate (1430 .. 2910)
FLOOR_C, BELT, ROOF_C = 240, 600, 920
PLAT = (-510, 1600, -260, 2090)                       # work-stairs platform (z 240) at the open door
STAIR = (-460, 2090, -260, 2570)                      # stairs rising south to the platform (clear of the wheel)
LOFT = (GX0 + 40, 2400, 600, GY1); LOFT_Z = 1456           # starts where the roof clears the boards
BEAMS_Y = (600, 1200, 1800, 2400, 3000)
FREEZER = (1504, 610)                                 # centre; long axis along y; 80u gap behind it
BENCH = (1440, 1300, 1800, 2400); BENCH_Z = 540
SHELF = (1530, 2600, 1800, 3560); SHELF_Z = (400, 800, 1200)
TUB = (-1400, 3200, -900, 3580); TUB_FLOOR, TUB_F, TUB_S, TUB_RIM = 280, 512, 534, 542
WASHER = (-1600, 3400)
DRAIN = (400, 500)
DEN = (-480, -400, 480, 400); DEN_Z = -2000           # the Sewer Den (sealed, below the world)
BOAT = (1100, -1500)                                  # boat centre (model rotated 180: drawbar to the north)
BOAT_DECK = 490


# ------------------------------------------------------------------------------------------------ helpers
def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def cbox(mn, mx):
    """invisible collision box (weapclip)"""
    return box(mn, mx, WCLIP)


def as_clip(brushes):
    return K.clipped(brushes, WCLIP)


# ------------------------------------------------------------------------------------------------ structure
def hull():
    """sealed sky box round the whole street (playable part + scenery): structural floor slabs by region, sky walls
    and ceiling. The road is 16u below the footpath; the verge slabs show their kerb face"""
    fl = lambda top, side=CAULK: {'top': T(top), 'side': side, 'bot': CAULK}
    def slab(x0, y0, x1, y1, tex, z=0, side=CAULK):
        if x1 - x0 > 0.5 and y1 - y0 > 0.5:
            K.add(box((x0, y0, z - 32), (x1, y1, z), fl(tex, side), detail=False))
    dr = (DRAIN[0] - 64, DRAIN[1] - 64, DRAIN[0] + 64, DRAIN[1] + 64)
    for r in sub_rects((GX0 - WT, GY0, GX1 + WT, GY1 + WT), [dr]):
        slab(*r, 'concrete')
    slab(*dr, 'drain')
    slab(GX0 - WT, DRIVE_Y0, GX1 + WT, GY0, 'drive')                                    # our driveway
    slab(X0, DRIVE_Y0, GX0 - WT, Y1, 'grass'); slab(GX1 + WT, DRIVE_Y0, X1, Y1, 'grass')
    slab(GX0 - WT, GY1 + WT, GX1 + WT, Y1, 'grass')
    # neighbours' lots (both sides of the street) with their driveways
    drives = [(x - 800, x + 800) for x in NEIGHBOUR_DRIVES]
    for (xa, xb) in ((HX0, X0), (X1, HX1)):
        holes = [(a, DRIVE_Y0, b, NEIGHBOUR_Y) for (a, b) in drives if xa <= a and b <= xb]
        for r in sub_rects((xa, DRIVE_Y0, xb, Y1), holes): slab(*r, 'lawnfar')
        for h_ in holes: slab(*h_, 'drive')
    far = [(x - 800, x + 800) for x in FAR_DRIVES]
    holes = [(a, FAR_Y, b, PY0) for (a, b) in far]
    for r in sub_rects((HX0, HY0, HX1, PY0), holes): slab(*r, 'lawnfar')
    for h_ in holes: slab(*h_, 'drive')
    # footpaths, verges (driveway crossings in concrete), road; past the road ends: the end houses' lawns
    for (y0, y1) in (FOOT, FFOOT): slab(HX0, y0, HX1, y1, 'footpath')
    for (y0, y1, ds) in ((BERM[0], BERM[1], [(GX0 - WT, GX1 + WT)] + drives), (FBERM[0], FBERM[1], far)):
        holes = [(max(a, -ROAD_X), y0, min(b, ROAD_X), y1) for (a, b) in ds if b > -ROAD_X and a < ROAD_X]
        for r in sub_rects((-ROAD_X, y0, ROAD_X, y1), holes): slab(*r, 'grass', side=T('kerb'))
        for h_ in holes: slab(*h_, 'drive', side=T('kerb'))
    for (xa, xb) in ((HX0, -ROAD_X), (ROAD_X, HX1)): slab(xa, ROAD[0] - 400, xb, BERM[1], 'lawnfar', side=T('kerb'))
    ym = (ROAD[0] + ROAD[1]) / 2
    slab(-ROAD_X, ROAD[0], ROAD_X, ym - 12, 'asphalt', ROAD_Z); slab(-ROAD_X, ym + 12, ROAD_X, ROAD[1], 'asphalt', ROAD_Z)
    x = -ROAD_X
    while x < ROAD_X:                                                                   # dashed centre line
        x2 = min(ROAD_X, x + 600)
        slab(x, ym - 12, min(x + 360, x2), ym + 12, 'roadline', ROAD_Z)
        if x + 360 < x2: slab(x + 360, ym - 12, x2, ym + 12, 'asphalt', ROAD_Z)
        x = x2
    # driveway crossing: a little ramp down the kerb
    K.add(hull_([(x_, y_, z_) for x_ in (GX0 - WT, GX1 + WT) for (y_, z_) in ((ROAD[1], 0), (ROAD[1], ROAD_Z), (ROAD[1] - 26, ROAD_Z))],
                lambda n: T('drive') if n[2] > 0.3 else (T('kerb') if abs(n[0]) > 0.9 else CAULK)))
    sky = T('sky'); zb = ROAD_Z - 32                    # walls reach the road slab's bottom: the slabs seal the floor
    K.add(box((HX0 - 32, HY0 - 32, zb), (HX0, HY1 + 32, ZSKY), tex6(e=sky), detail=False))
    K.add(box((HX1, HY0 - 32, zb), (HX1 + 32, HY1 + 32, ZSKY), tex6(w=sky), detail=False))
    K.add(box((HX0, HY0 - 32, zb), (HX1, HY0, ZSKY), tex6(n=sky), detail=False))
    K.add(box((HX0, HY1, zb), (HX1, HY1 + 32, ZSKY), tex6(s=sky), detail=False))
    K.add(box((HX0 - 32, HY0 - 32, ZSKY), (HX1 + 32, HY1 + 32, ZSKY + 32), tex6(bot=sky), detail=False))


NEIGHBOUR_Y = -300                                    # our side: house fronts (their garages face the street)
NEIGHBOUR_DRIVES = []                                 # x centres of their driveways (filled by neighbours())
FAR_Y = -9000                                         # far side: house fronts (facing +y)
FAR_DRIVES = []
NEIGHBOURS = [  # (model, x centre, side): side +1 = our side (faces -y), -1 = far side (faces +y)
    ('house_c', -3800, 1), ('house_e', -7100, 1), ('house_a', -10300, 1),
    ('house_b', 4000, 1), ('house_d', 7400, 1), ('house_a', 10500, 1),
    ('house_d', -9200, -1), ('house_a', -6000, -1), ('house_b', -2800, -1), ('house_e', 400, -1),
    ('house_c', 3600, -1), ('house_a', 6700, -1), ('house_b', 9900, -1),
]


def plan_neighbours():
    """driveway x per neighbour (from the house's garage side), before hull() lays the slabs"""
    for (nm, x, side) in NEIGHBOURS:
        a = next(h for h in GS.HOUSES if h[0] == nm)
        w, gside = a[1], a[6]
        gx = x + side * gside * (w / 2 - 200 - 750)          # model is turned 180 on the far side
        (NEIGHBOUR_DRIVES if side > 0 else FAR_DRIVES).append(gx)


def boundary():
    """our lot: paling fences on both sides and the back (open to the street at the front). The playable area ends at
    the neighbours' front walls, the far property line and the roadworks barriers at +-STREET_X: low brick walls +
    hedges with player clip up to the sky, so nobody hops into a garden they can't use (or off the garage roof)."""
    ft = {'side': T('fence'), 'top': T('fence'), 'bot': CAULK}
    K.add(box((X0, DRIVE_Y0, 0), (X0 + 24, Y1 - 24, 1000), ft))
    K.add(box((X1 - 24, DRIVE_Y0, 0), (X1, Y1 - 24, 1000), ft))
    K.add(box((HX0, Y1 - 24, 0), (HX1, Y1, 1000), dict(ft, n=CAULK)))                  # back fences (all lots)
    K.reserve(((X0, DRIVE_Y0, 0), (X0 + 24, Y1, 1000)), ((X1 - 24, DRIVE_Y0, 0), (X1, Y1, 1000)),
              ((X0 + 24, Y1 - 24, 0), (X1 - 24, Y1, 1000)))
    clip = lambda mn, mx: K.add(box(mn, mx, CLIP))
    clip((X0, DRIVE_Y0, 1000), (X0 + 24, Y1 - 24, ZSKY)); clip((X1 - 24, DRIVE_Y0, 1000), (X1, Y1 - 24, ZSKY))
    clip((X0 + 24, Y1 - 24, 1000), (X1 - 24, Y1, ZSKY))
    # neighbours' front walls (our side) and the far property line: brick wall 360 + hedge, gates over their drives
    bw = {'side': T('brickwall'), 'top': T('kerb'), 'bot': CAULK}
    ht = {'side': T('hedge'), 'top': T('hedge'), 'bot': CAULK}
    gt = {'side': T('fence'), 'top': T('fence'), 'bot': CAULK}
    for (yw, sgn, drives, xs) in ((DRIVE_Y0, 1, NEIGHBOUR_DRIVES, ((HX0, X0), (X1, HX1))),
                                  (PY0, -1, FAR_DRIVES, ((HX0, HX1),))):
        ya, yb = (yw, yw + 120) if sgn > 0 else (yw - 120, yw)
        yh0, yh1 = (yb, yb + 220) if sgn > 0 else (ya - 220, ya)
        for (xa, xb) in xs:
            gaps = sorted((d - 800, d + 800) for d in drives if xa <= d <= xb)
            x = xa
            for (g0, g1) in gaps + [(xb, xb)]:
                if g0 > x:
                    K.add(box((x, ya, 0), (g0, yb, 360), bw))
                    K.add(box((x, yh0, 0), (g0, yh1, 760), ht))
                if g1 > g0:
                    gy = (ya, ya + 40) if sgn > 0 else (yb - 40, yb)              # flush with the street side: no
                    K.add(box((g0, gy[0], 0), (g1, gy[1], 700), gt))                # walkable slot past the street end
                x = g1
            clip((xa, min(ya, yh0), 760), (xb, max(yb, yh1), ZSKY))     # above the hedge: the wall is 360 tall
            K.reserve(((xa, min(ya, yh0), 0), (xb, max(yb, yh1), ZSKY)))
    # the street ends: clip across at +-STREET_X (barriers stand just inside, roadworks() places them)
    for sx in (-1, 1):
        x0, x1 = (STREET_X, STREET_X + 32) if sx > 0 else (-STREET_X - 32, -STREET_X)
        clip((x0, PY0, 0), (x1, DRIVE_Y0, ZSKY)); clip((x0, ROAD[0], ROAD_Z), (x1, ROAD[1], 0))
    K.reserve(((X1, DRIVE_Y0, 0), (PX1, PY1, ZSKY)), ((PX0, DRIVE_Y0, 0), (X0, PY1, ZSKY)))   # neighbours' gardens


def garage_walls():
    """detail walls (the sky hull seals the map): side walls with a sloped top, gable walls with the roller-door
    opening and the east side door, roof slabs + a 4u-proud ridge walk, bottom chords (beams) across"""
    wb = T('stucco'); inner = T('wallboard'); tr = T('trim')
    # side walls: top follows the roof underside (no overlap with the slabs)
    for s in (-1, 1):
        xi, xo = s * GX1, s * (GX1 + WT)
        def wall(y0, y1, z0=0):
            pts = [(xi, y, z) for y in (y0, y1) for z in (z0, roof_under(GX1))] + \
                  [(xo, y, z) for y in (y0, y1) for z in (z0, roof_under(GX1 + WT))]
            def tf(n):
                if abs(n[0]) > 0.9: return inner if n[0] * s < 0 else wb
                return tr
            K.add(hull_(pts, tf))
        if s > 0:                                   # east wall: side doorway
            sd0, sd1, sdz = SIDE_DOOR
            wall(GY0, sd0); wall(sd1, GY1)
            K.add(box((GX1, sd0, sdz), (GX1 + WT, sd1, roof_under(GX1 + WT) - 1),
                      {'w': inner, 'e': wb, 'bot': tr, 'top': CAULK, 'n': tr, 's': tr}))
        else:
            wall(GY0, GY1)
    # gable walls: pieces round the door opening, top on the roof line (ridge flat between +-RIDGE_W)
    def gable(y0, y1, face_in, opening=None):
        def piece(xa, xb, z0, topfn):
            pts = []
            xs = sorted({xa, xb} | ({-RIDGE_W, RIDGE_W} & set(x for x in (-RIDGE_W, RIDGE_W) if xa < x < xb)))
            for x in xs:
                for y in (y0, y1):
                    pts += [(x, y, z0), (x, y, topfn(x))]
            def tf(n):
                if abs(n[1]) > 0.9: return inner if (n[1] > 0) == (face_in > 0) else wb
                return tr
            K.add(hull_(pts, tf))
        top = lambda x: min(roof_under(x), roof_under(RIDGE_W)) if abs(x) <= RIDGE_W else roof_under(x)
        if opening:
            ox0, ox1, oz = opening
            piece(GX0 - WT, ox0, 0, top); piece(ox1, GX1 + WT, 0, top)
            piece(ox0, ox1, oz, top)
            piece(-PIER, PIER, 0, lambda x: oz)           # double garage: brick pier between the two doors
        else:
            piece(GX0 - WT, GX1 + WT, 0, top)
    gable(GY0 - WT, GY0, +1, DOOR)
    gable(GY1, GY1 + WT, -1)
    # roof slabs (detail, walkable 21.8 deg) from the eave overhang to the ridge walk
    for s in (-1, 1):
        xa, xb = s * (GX1 + 100), s * RIDGE_W
        pts = []
        for x in (xa, xb):
            for y in (GY0 - 100, GY1 + 100):
                pts += [(x, y, roof_under(x)), (x, y, roof_top(x))]
        K.add(hull_(pts, lambda n: T('shingles') if n[2] > 0.5 else (T('roofunder') if n[2] < -0.5 else tr)))
    K.add(box((-RIDGE_W, GY0 - 100, roof_under(RIDGE_W)), (RIDGE_W, GY1 + 100, roof_top(RIDGE_W) + 4),
              {'top': T('shingles'), 'bot': T('roofunder'), 'side': tr}))
    K.route('roof_ridge', (0, 900, roof_top(RIDGE_W) + 4), (0, 3200, roof_top(RIDGE_W) + 4))
    K.route('roof_climb', (-1250, 900, roof_top(1250)), (-200, 900, roof_top(200)))
    # bottom chords across the garage (beams; the loft boards rest on the ones over the back third)
    for y in BEAMS_Y:
        K.add(box((GX0, y - 20, EAVE - 40), (GX1, y + 20, EAVE), T('rafter')))
    # sign over the roller door
    K.add(sign_box((-280, GY0 - WT - 6, 1335), (280, GY0 - WT, 1475), T('sign'), 1024, 256, back=CAULK, facing='s', edge=T('trim')))
    K.reserve(((GX0 - WT, GY0 - WT, 0), (GX1 + WT, GY0, 2200)), ((GX0 - WT, GY1, 0), (GX1 + WT, GY1 + WT, 2200)),
              ((GX0 - WT, GY0, 0), (GX0, GY1, 1440)), ((GX1, GY0, 0), (GX1 + WT, GY1, 1440)))
    K.keep_clear(DOOR[0], GY0 - 200, DOOR[1], GY0 + 200, 0)
    K.keep_clear(GX1 - 150, SIDE_DOOR[0], GX1 + 250, SIDE_DOOR[1], 0)
    K.route('door_in', (300, -300, 0), (300, 300, 0))
    K.route('side_door', (2050, (SIDE_DOOR[0] + SIDE_DOOR[1]) / 2, 0), (1500, (SIDE_DOOR[0] + SIDE_DOOR[1]) / 2, 0))


def hull_(pts, tf):
    return wopmap.hull([tuple(p) for p in pts], tf, round_pts=False)


def roller_door():
    for s_ in (-1, 1):                                  # sectional panel doors, raised to DOOR_BOTTOM
        K.custom(ML.PLACE['paneldoor'], s_ * (PIER + DOOR[1]) / 2, GY0 + 4, DOOR_BOTTOM, lit=True, occupy=False)
    K.reserve(((-PIER, GY0 - WT, 0), (PIER, GY0, DOOR[2])))
    as_clip([cbox((DOOR[0], GY0 + 4, DOOR_BOTTOM), (-PIER, GY0 + 24, DOOR[2])),
             cbox((PIER, GY0 + 4, DOOR_BOTTOM), (DOOR[1], GY0 + 24, DOOR[2])),
             cbox((DOOR[0] - 30, GY0 + 24, DOOR[2]), (DOOR[1] + 30, GY0 + 200, EAVE - 41))])


def loft():
    lx0, ly0, lx1, ly1 = LOFT
    K.add(box((lx0, ly0, EAVE), (lx1, ly1, LOFT_Z), {'top': T('loftboard'), 'bot': T('loftboard'), 'side': T('rafter')}))
    K.reserve(((lx0, ly0, EAVE - 40), (lx1, ly1, LOFT_Z)))
    # botclip along the open edges; gaps: over the car roof (walk-off exit for bots: a 1456u drop to the floor is
    # beyond bspc's 1000u walk-off trace), the loft pad and ladder, the plank bridge from shelf 3
    for s_ in (-1, 1):
        K.crawl((min(s_ * 1500, s_ * GX1), GY0, EAVE), (max(s_ * 1500, s_ * GX1), GY1, EAVE + 120))
    K.crawl((CAR_X0, CABIN_Y0, BELT), (CAR_X0 + 60, CABIN_Y1, BELT + 60))
    K.botclip_rect(lx0, ly0, lx1, ly1, LOFT_Z, sides='se', gaps=[('s', -1420, -620), ('s', 120, 620), ('e', 3180, 3380)])
    K.custom(ML.PLACE['ladder'], 520, ly0 - 40, 0, angle=0, lit=True, occupy=False, angles=(-8, 90, 0))
    lad = box((440, ly0 - 64, 0), (600, ly0 - 40, LOFT_Z - 1), T('ladderclip'))
    K.add(lad)


def car():
    """the station wagon MD3 + its collision (weapclip): floor pan, bonnet, cabin walls round the open door, dash,
    seats, roof, windscreen; wheels and stands under it; the open door panel"""
    cx, cy = CAR
    K.custom(ML.PLACE['car'], cx, cy, 0, lit=True, occupy=False)
    L2 = 1260
    yd0, yd1 = cy - 330, cy + 330                      # door opening y range
    B = []
    B.append(cbox((CAR_X0, CAR_Y0, 200), (CAR_X1, CAR_Y1, FLOOR_C)))                     # floor pan
    B.append(cbox((CAR_X0 + 10, CAR_Y0, FLOOR_C), (CAR_X1 - 10, CABIN_Y0, 580)))         # bonnet / engine bay
    B.append(cbox((CAR_X0, CABIN_Y0, FLOOR_C), (CAR_X0 + 60, CABIN_Y1, BELT)))           # west cabin side
    B.append(cbox((CAR_X1 - 60, yd1, FLOOR_C), (CAR_X1, CABIN_Y1, BELT)))                # east side behind the door
    B.append(cbox((CAR_X1 - 60, yd0, FLOOR_C), (CAR_X1, yd1, FLOOR_C + 16)))            # sill: one 16u step
    B.append(cbox((CAR_X0 + 60, CABIN_Y0, FLOOR_C), (CAR_X1 - 60, CABIN_Y0 + 140, BELT - 60)))   # dash
    B.append(cbox((CAR_X0 + 10, CABIN_Y1, FLOOR_C), (CAR_X1 - 10, CAR_Y1, BELT)))        # tailgate / rear
    for sx in (-1, 1):                                                                 # bucket seats
        xa, xb = (cx + 60, cx + 400) if sx > 0 else (cx - 400, cx - 60)
        B.append(cbox((xa, cy + 40, FLOOR_C), (xb, cy + 240, FLOOR_C + 150)))
        B.append(cbox((xa, cy + 240, FLOOR_C), (xb, cy + 320, FLOOR_C + 470)))
    B.append(cbox((cx - 440, CABIN_Y0 + 300, 880), (cx + 440, CABIN_Y1, ROOF_C)))        # roof
    B.append(cbox((CAR_X0, CABIN_Y0 + 300, BELT), (CAR_X0 + 40, CABIN_Y1, 880)))         # west glass
    B.append(cbox((CAR_X1 - 40, yd1, BELT), (CAR_X1, CABIN_Y1, 880)))                    # east glass behind door
    B.append(cbox((CAR_X0 + 40, CABIN_Y1 - 20, BELT), (CAR_X1 - 40, CABIN_Y1, 880)))     # tailgate glass
    B.append(hull_([(x, CABIN_Y0, z) for x in (CAR_X0, CAR_X1) for z in (BELT, BELT + 20)] +
                   [(x, CABIN_Y0 + 300, z) for x in (CAR_X0 + 40, CAR_X1 - 40) for z in (880, 900)], WCLIP))   # windscreen
    for (wx, wy) in GM.CAR_WHEELS:                                                     # wheels below the body
        x = cx + wx + (40 if wx > 0 else -40)
        B.append(cbox((x - 75, cy + wy - 190, 0), (x + 75, cy + wy + 190, 200)))   # to the floor: no crouch slot
    for (sx, sy) in ((-300, -560), (300, -560), (-300, 600), (300, 600)):              # axle stands
        B.append(cbox((cx + sx - 60, cy + sy - 60, 0), (cx + sx + 60, cy + sy + 60, 200)))
    as_clip(B)
    # the open driver's door (hinged at the front of the opening, swung out 62 deg)
    a = math.radians(62)
    hx, hy = CAR_X1, yd0
    door_pts = []
    for t in (0, 1):
        for w in (2, 32):
            px = hx + t * 660 * math.sin(a) + w * math.cos(a); py = hy + t * 660 * math.cos(a) - w * math.sin(a)
            door_pts += [(px, py, 220), (px, py, 860)]
    as_clip([hull_(door_pts, WCLIP)])
    K.reserve(((CAR_X0 - 70, CAR_Y0 - 60, 0), (CAR_X1 + 70, CAR_Y1 + 60, ROOF_C)))
    K.reserve(((hx - 40, hy - 40, 0), (hx + 600, hy + 330, 900)))
    K.route('car_inside', (-360, 1700, FLOOR_C), (cx, CABIN_Y0 + 240, FLOOR_C))
    K.route('under_car', (CAR_X1 + 150, 1200, 0), (cx, 1300, 0))
    # spare-parts boxes stored under the car (200 tall, flush with the floor pan): the 200u gap under the body was
    # one long open view at eye height (sightlines)
    for (x, y, a) in ((-1020, 1000, 0), (-1300, 1550, 90), (-750, 2050, 0), (-1150, 2850, 0)):
        K.custom(ML.PLACE['xmas3'], x, y, 0, angle=a, boxes=GM.COLL['xmas3']['boxes'])


def work_stairs():
    """rolling steel work stairs up to the open door: 16u risers, platform at the cabin floor"""
    st = {'top': T('rubberfloor'), 'side': T('steel'), 'bot': T('steel')}
    K.stairs16(STAIR[0], STAIR[1], STAIR[2], STAIR[3], 0, FLOOR_C, 's', st, route='car_stairs')
    K.add(box((PLAT[0], PLAT[1], 0), (PLAT[2], PLAT[3], FLOOR_C), st))
    K.reserve(((PLAT[0] - 8, PLAT[1] - 8, 0), (PLAT[2] + 8, STAIR[3] + 8, FLOOR_C)))
    K.keep_clear(STAIR[0] - 40, STAIR[3], STAIR[2] + 40, STAIR[3] + 120, 0)


def workshop():
    """freezer (gap behind), workbench + pegboard + vice, toolbox, steel shelving, plank ramps"""
    fx, fy = FREEZER
    K.custom(ML.PLACE['freezer'], fx, fy, 0, angle=90, boxes=GM.COLL['freezer']['boxes'])
    # workbench as solid pieces: top slab and four legs (timber), collision = the same brushes
    bx0, by0, bx1, by1 = BENCH
    br = [cbox((bx0, by0, BENCH_Z - 40), (bx1, by1, BENCH_Z))]
    for (x, y) in ((bx0 + 20, by0 + 20), (bx1 - 80, by0 + 20), (bx0 + 20, by1 - 80), (bx1 - 80, by1 - 80)):
        br.append(cbox((x, y, 0), (x + 60, y + 60, BENCH_Z - 40)))
    K.solid_piece('bench', br, GM.solids_tex('bench', 'benchleg'))
    K.custom(ML.PLACE['pegtools'], GX1 - 2, (by0 + by1) / 2, 600, lit=True, occupy=False)
    K.custom(ML.PLACE['vice'], bx0 + 70, by0 + 120, BENCH_Z, angle=180, boxes=[((-60, -100, 0), (60, 100, 180))])
    K.catalog('pad_lamps/gooseneck.md3', bx0 + 200, by1 - 200, BENCH_Z, 1.0, angle=180, clip=False)
    K.custom(ML.PLACE['toolbox'], 1150, 2250, 0, angle=270, boxes=GM.COLL['toolbox']['boxes'])
    # steel shelving against the east wall (three shelves), solid pieces
    sx0, sy0, sx1, sy1 = SHELF
    sb = []
    for z in SHELF_Z:
        sb.append(cbox((sx0, sy0, z - 16), (sx1, sy1, z)))
    for y in (sy0, (sy0 + sy1) / 2 - 20, sy1 - 40):
        for x in (sx0, sx1 - 40):
            for (za, zb) in zip((0,) + SHELF_Z, SHELF_Z):
                sb.append(cbox((x, y, za), (x + 40, y + 40, zb - 16)))
    K.solid_piece('shelving', sb, GM.solids_tex('shelfsteel'))
    # plank ramps: bench -> shelf 2, floor -> shelf 1, shelf 3 -> loft (bridge); planks are MD3s, ramps weapclip
    K.ramp(1560, 2150, 1760, sy0, BENCH_Z, SHELF_Z[1], 'n', WCLIP, route='bench_shelf2')
    K.custom(ML.PLACE['plank_a'], 1660, 2150, BENCH_Z + 2, angle=90, lit=True, occupy=False,
             angles=(round(-math.degrees(math.atan2(SHELF_Z[1] - BENCH_Z, sy0 - 2150)), 1), 90, 0))
    K.ramp(900, 3380, sx0, 3560, 0, SHELF_Z[0], 'e', WCLIP, route='floor_shelf1')
    K.custom(ML.PLACE['plank_b'], 900, 3470, 2, angle=0, lit=True, occupy=False,
             angles=(round(-math.degrees(math.atan2(SHELF_Z[0], sx0 - 900)), 1), 0, 0))
    K.ramp(LOFT[2], 3200, sx0, 3360, SHELF_Z[2], LOFT_Z, 'w', WCLIP, base=SHELF_Z[2] - 24, route='shelf3_loft')
    K.custom(ML.PLACE['plank_c'], sx0, 3280, SHELF_Z[2] + 2, angle=180, lit=True, occupy=False,
             angles=(round(-math.degrees(math.atan2(LOFT_Z - SHELF_Z[2], sx0 - LOFT[2])), 1), 180, 0))
    K.botclip_rect(sx0, sy0, sx1, sy1, SHELF_Z[2], sides='ws', gaps=[('w', 2950, 3150), ('w', 3200, 3360)])
    K.keep_clear(830, 3360, 920, 3580, 0)


def laundry():
    """washing machine (leaking a puddle), concrete laundry tub full of soapy water with a ramp out, mop bucket"""
    K.custom(ML.PLACE['washer'], WASHER[0], WASHER[1], 0, boxes=GM.COLL['washer']['boxes'])
    tx0, ty0, tx1, ty1 = TUB
    w = 30
    tb = [cbox((tx0, ty0, 0), (tx1, ty1, TUB_FLOOR)),
          cbox((tx0, ty0, TUB_FLOOR), (tx1, ty0 + w, TUB_RIM)), cbox((tx0, ty1 - w, TUB_FLOOR), (tx1, ty1, TUB_RIM)),
          cbox((tx0, ty0 + w, TUB_FLOOR), (tx0 + w, ty1 - w, TUB_RIM)), cbox((tx1 - w, ty0 + w, TUB_FLOOR), (tx1, ty1 - w, TUB_RIM))]
    K.solid_piece('tub', tb, GM.solids_tex('concretetub'))
    ix0, iy0, ix1, iy1 = tx0 + w, ty0 + w, tx1 - w, ty1 - w
    rmp = K.ramp(ix0, iy1 - 160, ix1 - 80, iy1, TUB_FLOOR, TUB_F, 'e', T('concrete'), base=TUB_FLOOR)
    top = box((ix1 - 80, iy1 - 160, TUB_FLOOR), (ix1, iy1, TUB_F), {'top': T('concrete'), 'side': T('concrete'), 'bot': CAULK})
    K.add(top)
    K.water_box((ix0, iy0, TUB_FLOOR), (ix1, iy1, TUB_S), T('soapwater'), cutters=[rmp, top])
    K.water_box((-1420, 3030, 0), (-1000, 3190, 12), T('puddle'))
    K.custom(ML.PLACE['bucket'], -740, 3390, 0, boxes=(), cyls=GM.COLL['bucket']['cyls'])
    K.catalog('pad_tins/pad_milk_s.md3', -1720, 3500, 510, 1.4, clip=False)
    K.speaker(WASHER[0], WASHER[1], 300, 'ambient/water_drippling')


def aisle_props():
    K.custom(ML.PLACE['hoist'], 350, 1150, 0, boxes=GM.COLL['hoist']['boxes'], cyls=GM.COLL['hoist']['cyls'])
    K.prop(ML.PLACE['mower'], -180, 520, 0, boxes=GM.COLL['mower']['boxes'], angle=180)
    K.prop(ML.PLACE['tyres'], 420, 3050, 0, cyls=GM.COLL['tyres']['cyls'], angle=0)
    for (x, y, a) in ((900, 2600, 30), (-200, 3300, 0)):
        K.catalog('pad_ddmix/backyard/tire.md3', x, y, 0, 1.3, angle=a)
    K.catalog('pad_ddmix/gallery/fire_extinguisher.md3', GX1 - 40, 1300 - 60, 0, 1.4, angle=180, clip=False)
    for (x, y) in ((1520, 1500), (1600, 1650), (1700, 2100)):
        K.catalog('pad_tins/pad_paint1.md3', x, y, 0, 1.0, clip=False)
    for (x, y, z) in ((1600, 2750, 400), (1700, 3000, 400), (1600, 3300, 800), (1700, 2700, 800), (1650, 3450, 1200),
                      (1600, 2700, 1200), (1700, 3200, 800)):
        K.catalog('pad_tins/pad_paint2.md3' if z != 800 else 'pad_tins/pad_paint1_tl.md3', x, y, z, 1.0, clip=z == 0, nudge=False)
    K.catalog('pad_radio_car/radio_control.md3', 1650, 2000, BENCH_Z, 1.4, angle=200, clip=False)
    K.catalog('pad_train/hammer.md3', 1560, 1900, BENCH_Z, 1.0, angle=70, clip=False)
    K.catalog('padmousetrap/padjumptrap.md3', -400, 3200, 0, 1.6, clip=False)


def loft_props():
    """boxes only where the sloping roof leaves headroom (roof_under(|x| + half-width) >= top + 16)"""
    lz = LOFT_Z
    for (nm, x, y, a) in (('tentbag', -600, 3430, 0), ('xmas1', 350, 3420, 90), ('chilly', -150, 2700, 200)):
        bx = GM.COLL[nm]['boxes']
        hw = max(math.hypot(max(abs(m[0]), abs(M[0])), max(abs(m[1]), abs(M[1]))) for m, M in bx)
        top = lz + max(M[2] for m, M in bx)
        if roof_under(abs(x) + hw) < top + 16:
            K.warn(f'loft prop {nm} at x {x}: too tall for the roof there'); continue
        K.prop(ML.PLACE[nm], x, y, lz, boxes=bx, angle=a)
    K.custom(ML.PLACE['rods'], -400, 3510, lz, angle=0, lit=True, occupy=False)


def driveway():
    """dinghy on its trailer (plank ramp up the side onto the deck boards), bin, bike, hose reel, barrow, lamp, hoop"""
    bx, by = BOAT
    K.custom(ML.PLACE['dinghy'], bx, by, 0, angle=180, boxes=GM.COLL['dinghy']['boxes'], cyls=GM.COLL['dinghy']['cyls'])
    as_clip([hull_([(bx - x, by - y, z) for (x, y, z) in pts], lambda n: WCLIP) for pts in GM.COLL['dinghy']['solids']])   # tapered deck + sides (model turned 180)
    K.ramp(bx + 320, by - 550, 2150, by - 350, 0, 520, 'w', WCLIP, route='boat_ramp')
    K.custom(ML.PLACE['plank_b'], 2150, by - 450, 2, angle=180, lit=True, occupy=False,
             angles=(round(-math.degrees(math.atan2(520, 2150 - bx - 310)), 1), 180, 0))
    for y in (by + 450, by, by - 500):                 # boxes stored under the boat (hull bottom 240): eye-level cover
        K.custom(ML.PLACE['xmas2'], bx, y, 0, angle=0, boxes=GM.COLL['xmas2']['boxes'])   # 240 tall: no crouch slot
    K.reserve(((bx - 420, by - 900, 0), (bx + 420, by + 900, 560)), ((bx + 300, by - 620, 0), (2200, by - 280, 560)))
    K.custom(ML.PLACE['suv_white'], -820, -1620, 0, angle=180, boxes=GM.COLL['suv_white']['boxes'])  # nose to the garage
    K.prop(ML.PLACE['bin'], -1550, -350, 0, boxes=GM.COLL['bin']['boxes'], angle=15)
    K.prop(ML.PLACE['reel'], -2040, -700, 0, boxes=GM.COLL['reel']['boxes'], angle=0)
    K.custom(ML.PLACE['hoop'], 0, GY0 - WT + 10, 1490, angle=0, lit=True, occupy=False)
    K.catalog('pad_ddmix/trashcan/tree_summer.md3', -2010, -2050, 0, 1.2, lit=True, clip=False)
    as_clip([cyl(-2010, -2050, 44, 0, 640, WCLIP, 8)])                 # trunk only (the canopy was a walkable box)
    K.catalog('animated/raven_sitting_1.md3', 0, 3300, roof_top(RIDGE_W) + 4, 1.0, angle=90, clip=False, nudge=False)
    # back strip and alleys
    K.prop(ML.PLACE['firewood'], -800, 3855, 0, boxes=GM.COLL['firewood']['boxes'], angle=0)
    K.prop(ML.PLACE['firewood'], 900, 3855, 0, boxes=GM.COLL['firewood']['boxes'], angle=0)
    K.catalog('pad_ddmix/trashcan/garbage_bag_group.md3', 2100, 3880, 0, 1.8)
    K.catalog('pad_ddmix/trashcan/bush.md3', -2068, 1000, 0, 0.9)
    K.catalog('pad_ddmix/trashcan/bush.md3', 2068, 2600, 0, 0.9)


def trailer(cx, cy):
    """box trailer parked on the drive (long axis x, drawbar to -x), a load of garden-waste bags; one solid_piece
    (visible MD3 + the same brushes as weapclip). Driveway cover: the apron is one big open space otherwise."""
    L, W, DZ, SZ, T_ = 500, 280, 110, 380, 24        # low deck: nobody stands or crawls under it
    def B(a, b): return cbox((cx + a[0], cy + a[1], a[2]), (cx + b[0], cy + b[1], b[2]))
    br = [B((-L, -W, 30), (L, W, DZ)),
          B((-L, -W, DZ), (L, -W + T_, SZ)), B((-L, W - T_, DZ), (L, W, SZ)), B((-L, -W + T_, DZ), (-L + T_, W - T_, SZ)),
          B((L - T_, -W + T_, DZ), (L, W - T_, DZ + 120)),                       # tailgate (low: you see the load)
          B((-L - 330, -24, 60), (-L, 24, 90)), B((-L - 300, -14, 0), (-L - 270, 14, 60))]
    K.solid_piece('trailer', br, GM.solids_tex('trailer'))
    wh = []                                                                  # wheels: octagon prisms, drawn only;
    for sy in (-1, 1):                                                       # collision = one box per wheel (no
        pts = []                                                             # crouch slots under the round)
        for k in range(8):
            t = (k + 0.5) * math.pi / 4
            for y in (sy * (W + 8), sy * (W + 88)):
                pts.append((cx + 115 * math.cos(t), cy + y, 115 + 115 * math.sin(t)))
        wh.append(hull_(pts, lambda n: WCLIP))
        as_clip([B((-115, min(sy * (W + 8), sy * (W + 88)), 0), (115, max(sy * (W + 8), sy * (W + 88)), 221))])
    K.solid_piece('trailer_wheels', wh, GM.solids_tex('tyre'), clip=None)
    K.reserve(((cx - L - 330, cy - W - 90, 0), (cx + L, cy + W + 90, SZ)))
    K.catalog('pad_ddmix/trashcan/garbage_bag_group.md3', cx - 120, cy, DZ, 1.6, clip=False, nudge=False)


def facade():
    """the photo's front: white trim round both door openings with a keystone over each, coach lanterns either side
    and on the pier (stucco walls + shingle roof come from garage_walls)"""
    yf = GY0 - WT                                                                        # facade face (y -32)
    br = []
    for (a, b) in ((DOOR[0], -PIER), (PIER, DOOR[1])):
        br += [cbox((a - 70, yf - 10, 0), (a, yf, DOOR[2] + 70)), cbox((b, yf - 10, 0), (b + 70, yf, DOOR[2] + 70)),
               cbox((a, yf - 10, DOOR[2]), (b, yf, DOOR[2] + 70))]
        m = (a + b) / 2
        br.append(hull_([(x, y, z) for y in (yf - 16, yf) for (x, z) in ((m - 70, DOOR[2] + 70), (m + 70, DOOR[2] + 70),
                                                                          (m + 90, DOOR[2] + 190), (m - 90, DOOR[2] + 190))], WCLIP))
    K.solid_piece('facadetrim', br, GM.TX.texfn('trimm'))
    for x in (DOOR[0] - 230, 0, DOOR[1] + 230):
        K.custom(ML.PLACE['lantern'], x, yf, 760, angle=0, lit=True, occupy=False)
        K.light(x, yf - 200, 880, 260, '1 0.82 0.55')


def street():
    """a clear street (user: the props made it too busy): only ROAD CLOSED barriers at both ends, where the player clip
    stops you, street trees and lamps on the verges, our front garden wall"""
    zr = ROAD_Z
    ym = (ROAD[0] + ROAD[1]) / 2
    for sx in (-1, 1):
        xb = sx * (STREET_X - 170)
        for y in (ROAD[1] - 600, ROAD[1] - 1800):
            K.custom(ML.PLACE['barrier'], xb, y, zr, angle=90, boxes=GM.COLL['barrier']['boxes'])
        K.custom(ML.PLACE['closedsign'], xb - sx * 230, ym, zr, angle=90, boxes=GM.COLL['closed']['boxes'])
        for y in ((FOOT[0] + FOOT[1]) / 2, (FFOOT[0] + FFOOT[1]) / 2):
            K.custom(ML.PLACE['barrier'], sx * (STREET_X - 650), y, 0, angle=0, boxes=GM.COLL['barrier']['boxes'])
    # verges: street trees, lamps (arms over the road), wheelie bins out for collection, our letterbox
    bm, fm = (BERM[0] + BERM[1]) / 2, (FBERM[0] + FBERM[1]) / 2
    for (x, y) in ((-2900, bm), (3300, bm), (-1500, fm), (1500, fm)):
        K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, 1.2, lit=True, clip=False)
        as_clip([cyl(x, y, 44, 0, 640, WCLIP, 8)])
    for (x, y, a) in ((-3700, bm, 0), (3750, bm, 0), (-300, fm, 180), (3300, fm, 180)):
        K.custom(ML.PLACE['streetlamp'], x, y, 0, angle=a, cyls=GM.COLL['lamp']['cyls'])
        off = -380 if a == 0 else 380
        K.light(x, y + off, LAMP_H + 110, 2600, '1 0.78 0.5')
    for (x, y, z, i) in ((-1600, DRIVE_Y0 - 60, 650, 1000), (1600, DRIVE_Y0 - 60, 650, 1000)):
        K.light(x, y, z, i, '1 0.72 0.35')                                 # spill from the garden wall lamps
    # our front garden wall: low brick with pillars either side of the driveway (the drive itself stays open)
    br = []
    for (xa, xb) in ((X0 + 24, GX0 - WT), (GX1 + WT, X1 - 24)):
        xp = xb if xa < 0 else xa
        px0, px1 = (xp - 80, xp) if xa < 0 else (xp, xp + 80)
        wa, wb_ = (xa, px0) if xa < 0 else (px1, xb)
        br += [cbox((wa, DRIVE_Y0, 0), (wb_, DRIVE_Y0 + 100, 360)), cbox((px0, DRIVE_Y0 - 10, 0), (px1, DRIVE_Y0 + 110, 480))]
        K.reserve(((xa, DRIVE_Y0 - 10, 0), (xb, DRIVE_Y0 + 110, 480)))
    K.solid_piece('frontwall', br, lambda c, n, poly: (GM.M_['capm'] if n[2] > 0.7 else GM.M_['brickm'], ML.planar_uv(n, 300.0)))
    K.route('street', (600, DRIVE_Y0 + 300, 0), (600, ROAD[1] - 300, ROAD_Z))


LAMP_H = 3200


def neighbours():
    """the neighbours' houses (scenery past the player clip, no collision), the houses closing both ends of the
    street, trees in their gardens and scenery street lamps down the road"""
    for (nm, x, side) in NEIGHBOURS:
        y = NEIGHBOUR_Y if side > 0 else FAR_Y
        K.custom(ML.PLACE[nm], x, y, 0, angle=0 if side > 0 else 180, lit=True, occupy=False)
    for (nm, sx) in (('house_c', 1), ('house_e', -1)):
        K.custom(ML.PLACE[nm], sx * (ROAD_X + 700), (ROAD[0] + ROAD[1]) / 2, 0, angle=270 if sx > 0 else 90, lit=True, occupy=False)
    for (x, y) in ((-5600, -1600), (5800, -1700), (-8700, -2100), (8900, -1900), (-4400, -9900), (2000, -10300),
                   (-7600, -10100), (5200, -10000), (8300, -9800), (11300, -1900), (-11400, -1900)):
        K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, 1.4, lit=True, clip=False, nudge=False)
    bm, fm = (BERM[0] + BERM[1]) / 2, (FBERM[0] + FBERM[1]) / 2
    for x in (-8200, -5600, 5600, 8200):
        for (y, a) in ((bm, 0), (fm, 180)):
            K.custom(ML.PLACE['streetlamp'], x + (0 if a == 0 else 1300), y, 0, angle=a, lit=True, occupy=False)
            K.light(x + (0 if a == 0 else 1300), y + (-380 if a == 0 else 380), LAMP_H + 110, 2600, '1 0.78 0.5')
    for (nm, x, side) in NEIGHBOURS:                                                     # porch lights
        y = NEIGHBOUR_Y - 300 if side > 0 else FAR_Y + 300
        K.light(x, y, 900, 500, '1 0.82 0.55')


def den():
    """the Sewer Den: sealed brick room below the world; leave by popping up out of the drain grate"""
    x0, y0, x1, y1 = DEN; z = DEN_Z
    wt = {'side': T('sewer'), 'top': T('sewerfloor'), 'bot': T('sewer')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), wt, detail=False),
          box((x0 - 32, y0 - 32, z + 480), (x1 + 32, y1 + 32, z + 512), wt, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 480), wt, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 480), wt, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 480), wt, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 480), wt, detail=False))
    K.reserve(((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 480)), ((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 480)),
              ((x0, y0 - 32, z), (x1, y0, z + 480)), ((x0, y1, z), (x1, y1 + 32, z + 480)))
    K.prop(ML.PLACE['sardinebed'], -250, 200, z, boxes=GM.COLL['sardinebed']['boxes'], angle=0)
    K.prop(ML.PLACE['captable'], 200, 100, z, cyls=GM.COLL['captable']['cyls'], angle=0)
    K.catalog('pad_ddmix/trashcan/lamp_sewer_lit.md3', -380, -300, z, 1.6, clip=False)
    K.catalog('pad_ddmix/trashcan/cannedfish.md3', 350, -250, z, 2.0)
    K.item('item_padpower', 0, -100, z); K.item('item_revival', -100, -250, z)
    K.item('holdable_killerducks', 250, -100, z)
    K.teleporter((-60, y0 + 20, z), (60, y0 + 100, z + 96), dest=(DRAIN[0], DRAIN[1] + 40, 0), angle=90, name='den_exit')
    K.light(0, 0, z + 380, 260, '1 0.8 0.5'); K.light(200, 100, z + 200, 120, '1 0.7 0.4')
    K.speaker(0, 0, z + 200, 'ambient/water_drippling')


def secret():
    """the glovebox in the passenger footwell: walk in -> secret_found -> the Sewer Den"""
    cx, cy = CAR
    mn = (cx - 340, CABIN_Y0 + 141, FLOOR_C + 1); mx = (cx - 120, CABIN_Y0 + 200, FLOOR_C + 90)
    K.secret(mn, mx, dest=(0, -200, DEN_Z), angle=90, name='glovebox', approach='n')


# ------------------------------------------------------------------------------------------------ gameplay
def woodshed():
    """open lean-to woodshed in the west alley: posts along the fence, a flat corrugated roof at 800 over the alley
    (walk under it), firewood stacked beneath. Its roof is the bots' stepping stone onto the garage roof: no pad from
    the floor clears the eave inside bspc's 3 s flight (pad_aas.py)."""
    sx0, sx1, sy0, sy1 = X0 + 24, GX0 - WT - 4, 2480, 3320
    br = [cbox((sx0, sy0, 760), (sx1, sy1, SHED_Z))]
    for y in (sy0 + 20, (sy0 + sy1) / 2 - 20, sy1 - 60):
        br.append(cbox((sx0 + 4, y, 0), (sx0 + 44, y + 40, 760)))
    K.solid_piece('woodshed', br, GM.solids_tex('alu', 'wood'))
    K.route('shed_roof', (sx0 + 120, sy0 + 120, SHED_Z), (sx1 - 60, sy1 - 120, SHED_Z))


SHED_Z = 800


def pads():
    """every pad checked against bspc's own flight (pad_aas.py), not just pad_check: floor pads top out around the car
    roof; the loft and the garage roof are reached from the car roof and the woodshed roof"""
    ru = roof_under
    K.jumppad(-100, 2800, 0, land=(-1000, 2500, ROOF_C), apex=1260, name='pad_carroof', ceiling=EAVE - 40,
              edges=[(CAR_X1, 2600, ROOF_C)])
    K.jumppad(-1000, 1900, ROOF_C, land=(-1000, 2800, LOFT_Z), apex=1720, name='pad_loft', ceiling=ru(1000),
              edges=[(-1000, LOFT[1], LOFT_Z)])
    K.jumppad(1150, 1650, 0, land=(1640, 1750, BENCH_Z), apex=780, name='pad_bench')
    K.jumppad(1150, 3050, 0, land=(1665, 3050, SHELF_Z[2]), apex=1440, name='pad_shelf3', ceiling=ru(1665),
              edges=[(SHELF[0], 3050, SHELF_Z[2])])
    K.jumppad(-1650, 3110, 0, land=(-1600, 3460, 510), apex=900, name='pad_washer', ceiling=EAVE - 40)
    K.jumppad(-2050, 2270, 0, land=(-2050, 2860, SHED_Z), apex=1260, name='pad_shed', edges=[(-2050, 2480, SHED_Z)])
    K.jumppad(-2150, 3000, SHED_Z, land=(-1550, 3000, roof_top(1550)), apex=1900, name='pad_roof',
              edges=[(GX0 - 100, 3000, roof_top(GX1 + 100))])
    rz = roof_top(RIDGE_W) + 4
    K.jumppad(0, 60, rz, land=(0, -800, 0), apex=rz + 100, name='pad_ridge', edges=[(0, GY0 - 100, rz)])


def items():
    cx, cy = CAR
    K.weapon('imperius', -200, 3000, LOFT_Z, marker='purple')
    K.weapon('betty', -1180, 3330, TUB_FLOOR, marker='black')
    K.weapon('balloony', 1665, 2800, SHELF_Z[2], marker='orange')
    K.weapon('pumper', -1020, 2500, ROOF_C, marker='green')
    K.weapon('splasher', cx + 200, 1700, FLOOR_C, marker='blue')     # driver's footwell, right inside the open door
    K.weapon('boaster', 1760, FREEZER[1], 0, marker='orange')
    K.weapon('bubbleg', BOAT[0], BOAT[1] - 200, BOAT_DECK, marker='green')
    ammo = {'imperius': [(-1250, 3150, LOFT_Z), (1665, 3450, SHELF_Z[2]), (1500, 3900, 0)],
            'betty': [(-1600, 3480, 510), (2050, 3000, 0), (-300, -2100, 0)],
            'balloony': [(1665, 3300, SHELF_Z[1]), (-2050, 3000, 0), (600, -2150, 0)],
            'pumper': [(1665, 3150, SHELF_Z[0]), (-1650, -1500, 0), (-1700, 3900, 0)],
            'splasher': [(1620, 2000, 0), (-300, 3200, 0), (2050, -800, 0)],
            'boaster': [(-100, 2850, LOFT_Z), (-1700, -1100, 0), (300, 3900, 0)],
            'bubbleg': [(250, -250, 0), (700, 1000, 0), (-2050, 100, 0)]}
    ym = (ROAD[0] + ROAD[1]) / 2; fp = (FFOOT[0] + FFOOT[1]) / 2; np_ = (FOOT[0] + FOOT[1]) / 2
    street_ammo = {'imperius': (-3900, fp, 0), 'betty': (-2300, ym, ROAD_Z), 'balloony': (3800, np_, 0),
                   'pumper': (1250, ROAD[1] - 250, ROAD_Z), 'splasher': (3200, ym, ROAD_Z),
                   'boaster': (-3300, ROAD[0] + 1300, ROAD_Z), 'bubbleg': (-1900, fp, 0)}
    for w, spots in ammo.items():
        for (x, y, z) in spots + [street_ammo[w]]: K.ammo(w, x, y, z)
    K.ammo('nipper', 1200, -300, 0); K.ammo('nipper', -1600, 2800, 0); K.ammo('nipper', 2050, 2200, 0)
    K.item('item_armor_padshield', cx, 1700, 0)                       # under the car
    K.item('item_armor_shard', 0, 1500, roof_top(RIDGE_W) + 4)      # garage roof: on the flat ridge walk
    K.item('item_armor_shard', 1620, 1550, BENCH_Z)
    K.item('item_speedy', -150, -1250, 0); K.item('holdable_floater', -700, 2700, LOFT_Z)
    K.station(-1600, -2250, 0, ang=45); K.station(700, 3350, 0, ang=270); K.station(0, PY0 + 260, 0, ang=90)
    K.item('item_armor_shard', 2200, ym - 300, ROAD_Z)                # out in the road beside the roadworks
    for (x, y, z, a) in ((-200, -800, 0, 90), (200, -2150, 0, 90), (500, -2250, 0, 90), (-1900, -1500, 0, 45),
                         (-300, 400, 0, 90), (800, 600, 0, 90), (900, 1900, 0, 180), (0, 2600, 0, 270), (-200, 1150, 0, 0),
                         (2050, 1800, 0, 270), (-2050, 2500, 0, 270), (-1000, 3880, 0, 0), (1200, 3880, 0, 180),
                         (-500, 3100, LOFT_Z, 270), (1640, 2100, BENCH_Z, 270),
                         (2050, (FOOT[0] + FOOT[1]) / 2 + 100, 0, 0), (600, (FFOOT[0] + FFOOT[1]) / 2, 0, 180),
                         (3600, (ROAD[0] + ROAD[1]) / 2 + 200, ROAD_Z, 180), (-3600, (ROAD[0] + ROAD[1]) / 2 - 300, ROAD_Z, 0)):
        K.spawn(x, y, z, a)


def lights():
    """measured against light_check (raw 128 = neutral): a dense grid under the chords (cold fluorescent), the car,
    cabin and shelves lit on their own, warm loft bulbs; outside blue moonlight (sky) + a warm street lamp and porch
    lights. Trouble lights under the car and the boat."""
    over_car = lambda x, y: CAR_X0 - 150 < x < CAR_X1 + 150 and CAR_Y0 - 100 < y < CAR_Y1 + 100
    K.light_grid(GX0 + 100, GY0 + 100, GX1 - 100, LOFT[1] - 50, 1150, 600, 5200, '0.9 0.96 1', skip=over_car)
    K.light_grid(GX0 + 100, LOFT[1] + 50, GX1 - 100, GY1 - 100, 1260, 600, 4000, '0.92 0.96 1', skip=over_car)
    for y in (800, 1500, 2200):
        K.light(CAR[0], y, ROOF_C + 420, 850, '0.9 0.96 1')
    for y in (CABIN_Y0 + 350, CABIN_Y0 + 1000):
        K.light(CAR[0], y, 720, 1000, '1 0.92 0.8')                      # dome lights in the cabin
    for x in (-1300, -650, 0, 450):
        for y in (2700, 3300):
            z = min(roof_under(abs(x) + 100) - 60, LOFT_Z + 340)
            K.light(x, y, z, 900, '1 0.85 0.6')
    for z in SHELF_Z:
        for y in (2800, 3350):
            K.light(SHELF[0] - 40, y, z + 260, 420, '0.95 0.97 1')
    for y in (600, 1200, 1800):
        for x in (-1000, 0, 1000):
            K.custom(ML.PLACE['striplight'], x, y, EAVE - 40 - 140, angle=0, lit=False, occupy=False)
    for (x, y) in ((-1100, 3000), (-200, 3300)):
        K.custom(ML.PLACE['bulb'], x, y, roof_under(x) - 2, lit=False, occupy=False)
    K.light(1650, 2150, 900, 420, '1 0.85 0.6')                            # gooseneck lamp
    K.light(1700, FREEZER[1], 700, 500, '0.9 0.96 1')                      # over the gap behind the freezer
    K.light(1740, -2250, 1900, 2800, '1 0.75 0.45')                        # street lamp head (model turned 270)
    K.light(0, GY0 - 200, 1300, 1600, '1 0.9 0.7')                         # over the roller door
    K.light(2050, (SIDE_DOOR[0] + SIDE_DOOR[1]) / 2, 600, 900, '1 0.9 0.7')
    for (x, y) in ((-2050, 1000), (-2050, 2800), (2050, 2900), (2050, 2100), (2050, -400), (-2050, -1350),
                   (-1100, 3860), (100, 3860), (1300, 3860), (2050, 3800), (-2050, 3700), (-2050, 150), (2050, 1300), (1950, 0)):
        K.light(x, y, 520, 1100, '1 0.88 0.7')                             # porch / garden lights
    for (x, y) in ((-2050, 2000), (-1400, -850)):
        K.light(x, y, 900, 1300, '1 0.88 0.7')                             # above the water tank / wheelie bin
    for y in (1000, 1700, 2400):
        K.light(GX0 + 90, y, 1000, 1100, '0.9 0.96 1')                     # the strip between the car and the west wall
    K.light_grid(X0 + 300, DRIVE_Y0 + 200, X1 - 300, GY0 - 200, 900, 1000, 2300, '0.6 0.7 1')
    K.light_grid(PX0 + 400, FFOOT[0] + 250, PX1 - 400, FOOT[1] - 100, 1200, 1200, 4500, '0.62 0.7 1')   # the street (moonlight fill)
    for (x, y) in ((-1250, 1300), (-800, 1750), (-1250, 2250), (-800, 2650), (-1250, 750), (BOAT[0], BOAT[1] - 150),
                   (BOAT[0] - 200, BOAT[1] - 300), (BOAT[0] + 200, BOAT[1] + 300)):
        K.light(x, y, 150, 1000, '1 0.85 0.6')                              # trouble lights under the car / boat
    for (x, y) in ((-1000, 1200), (1000, 1200)):
        K.speaker(x, y, 1250, 'machine/transformer')
    K.timer_sound(0, -1800, 800, 'animal/cricket_chirp1', 'crickets', 20, 12)
    K.timer_sound(2000, 3800, 1200, 'animal/bird_owl1', 'owl', 35, 20)
    K.timer_sound(-2000, -2300, 600, 'animal/dog_bark2', 'dog', 45, 25)


def blockers():
    """sightline cover where sightlines --hot pointed: inside the roller door, staggered along both alleys and the
    back strip, the middle of the driveway"""
    for (nm, x, y, a) in (('xmas1', 900, 450, 15), ('xmas2', 760, 860, -10)):           # boxes just inside the door
        K.prop(ML.PLACE[nm], x, y, 0, boxes=GM.COLL[nm]['boxes'], angle=a)
    K.prop(ML.PLACE['drum'], 0, 2200, 0, cyls=GM.COLL['drum']['cyls'], angle=0)
    K.prop(ML.PLACE['outboard'], 2020, -1150, 0, boxes=GM.COLL['outboard']['boxes'], angle=90)
    # the door axis: rolling toolbox mid-aisle, tyre stack on the threshold, bin and boxes on the apron
    K.prop(ML.PLACE['toolbox'], 170, 860, 0, boxes=GM.COLL['toolbox']['boxes'], angle=20)
    K.prop(ML.PLACE['toolbox'], 850, 1450, 0, boxes=GM.COLL['toolbox']['boxes'], angle=-15)
    K.prop(ML.PLACE['tyres'], 380, -1450, 0, cyls=GM.COLL['tyres']['cyls'], angle=0)
    K.custom(ML.PLACE['xmas3'], -760, 335, 0, angle=0, boxes=GM.COLL['xmas3']['boxes'])   # in front of the bonnet
    K.prop(ML.PLACE['xmas1'], 2060, 250, 0, boxes=GM.COLL['xmas1']['boxes'], angle=90)  # east alley mouth
    for (x, y, sc) in ((2056, 700, 1.15), (2056, 3350, 1.15)):          # plants down the side (one bin per house: the drive's)
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, sc)
    for (x, y, nm, a) in ((2030, 2250, 'tank', 0),
                          (-2030, 2000, 'tank', 0), (-2000, 3300, 'firewood', 90), (2068, -350, 'reel', 0),
                          (-200, 3855, 'compost', 0), (1700, 3880, 'tank', 0)):
        c = GM.COLL[nm]
        K.prop(ML.PLACE[nm], x, y, 0, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), angle=a)


def shader():
    GM.TX.write_shader(extra=[ladder_stanza()], arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'),
                       ents={e['classname'] for e in K.M.ents})


def ladder_stanza():
    t = f'textures/{NS}/ladderclip'
    return (f'{t}\n{{\n\tqer_editorimage textures/{NS}/steel\n\tqer_trans 0.4\n\tsurfaceparm nodraw\n\tsurfaceparm nonsolid\n'
            f'\tsurfaceparm playerclip\n\tsurfaceparm ladder\n\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n}}\n\n')


if __name__ == '__main__':
    GM.textures(K)
    GM.build_all()                     # every MD3 (and its shaders) BEFORE the shader file is written
    plan_neighbours(); hull(); boundary(); garage_walls(); roller_door(); facade(); loft(); car(); work_stairs()
    workshop(); laundry(); woodshed(); aisle_props(); loft_props(); driveway(); street(); neighbours(); den(); secret()
    blockers()
    pads(); items(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
