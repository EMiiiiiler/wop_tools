"""Shared layout constants for wop_padpirate (Skull Rock Bay): read by build_pirate.py (brushes, entities),
pp_shapes.py (convex collision solids) and pp_models.py (MD3 geometry), so the models and the collision line up.

A pirate water park on a tropical island on a sunny afternoon, human scale (~32u per metre, Padman 56u).
x east, y north, plaza z 0, water surface z -16. The sea surrounds the park on three sides, a jungle cliff closes
the north.

   y 2048 +--------------------------------------------------------------------+
          | FORT SAN PADRO  |        SKULL ROCK              | SHARK DIVE POOL  |
          | (walls, ramparts|  (hollow skull in a tricorn,   | + walk-the-plank |
          |  tower, cannon  |   balcony behind the eyes,     |   dive tower     |
          |  launcher)      |   slides W and E off the brim) |                  |
      400 +-----------------+--------------------------------+------------------+
          | TREASURE COVE   |   GALLEON BAY (lagoon)         | TORTUGA QUAY     |
          | (beach pool,    |   the galleon in the middle,   | (Rusty Anchor    |
          |  shacks, wreck) |   jetties north + south        |  tavern, shop,   |
          |                 |                                |  market)         |
   y-2048 +--------------------------------------------------------------------+
          x -2304                                                         x 2304
"""
import math
import numpy as np

HX, HY = 2304, 2048
SKY = dict(x0=-2944, x1=2944, y0=-2688, y1=2944, z0=-896, z1=2304)
WATER = -16
SLAB_BOT = -384
SHALLOW = -64
DEEP = -272
SEA_Z = -112                     # the open sea beyond the quay walls (decor, unreachable)
BANK_W, BANK_H = 352, 384        # north jungle cliff: slope from the plaza edge up to BANK_H


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def octagon(rect, cut, inset=0.0):
    x0, y0, x1, y1 = rect
    x0 += inset; y0 += inset; x1 -= inset; y1 -= inset
    c = max(0.0, cut - inset * (math.sqrt(2) - 1))
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


# ================================================================================================ Galleon Bay (lagoon)
LAG = (-1344.0, -1792.0, 1344.0, -192.0)
LAG_CUT = 352
SHALLOW_BAND = 192
SLOPE_W = 160
ISLETS = [(-900.0, -560.0, 96), (930.0, -1450.0, 96), (-980.0, -1500.0, 80), (960.0, -540.0, 80)]   # rock islets (cover)
LAG_STEPS = [(-1344, -1250, -1280, -1000, 'w'), (1280, -1100, 1344, -850, 'e'), (-760, -1792, -520, -1728, 's'),
             (520, -1792, 760, -1728, 's')]
BEACH = (-920, -416, -480, -192)          # sandy beach ramp (north shore, west of the jetty), 0 down to -64

# ================================================================================================ the galleon
SHIP = (0.0, -992.0)                       # midship on the centre line; the ship lies along x, bow east
SHIP_STERN = -640.0                        # transom
SHIP_BOW = 600.0                           # stem at the main deck
WAIST_Z = 112                              # main deck (waist) walk
QD_Z = 256                                 # quarterdeck walk (stern castle)
FC_Z = 224                                 # forecastle walk (bow)
QD_X = -360.0                              # front of the stern castle
FC_X = 360.0                               # front of the forecastle
DECK_T = 16
CW = 144.0                                 # collision half-beam above the waterline (vertical sides)
BULW_T = 8
BULW_H = 40                                # waist bulwark height
RAIL_H = 32                                # castle rails
HOLD = (-320.0, -112.0, 320.0, 112.0)      # hold (below the waist): x0, y0, x1, y1 relative to SHIP, z 0 .. 96
HOLD_Z1 = WAIST_Z - DECK_T                 # 96
CABIN = (-624.0, -100.0, -376.0, 100.0)    # captain's cabin under the quarterdeck, z 112 .. 240
CREW = (376.0, -72.0, 520.0, 72.0)         # crew quarters under the forecastle, z 112 .. 208
DOOR_HW = 40
CABIN_DOOR_H = 96
CREW_DOOR_H = 80
PORT_HW = 64                               # entry ports in the waist bulwarks (jetties land there), x +-64
STAIR_Y = (64.0, 128.0)                    # quarterdeck stairs run along both sides, |y| 64..128
STAIR_Y_FC = (52.0, 116.0)                 # forecastle stairs (the bow is narrower)
STAIR_RUN = 24
HATCH = (88.0, -40.0, 216.0, 40.0)         # hold hatch in the waist (stair descends toward -x from x 216)
MASTS = {'fore': (440.0, FC_Z, 760.0, 11.0), 'main': (0.0, WAIST_Z, 900.0, 15.0), 'mizzen': (-500.0, QD_Z, 720.0, 10.0)}
NEST_Z = 560                               # crow's nest (main fighting top) walk
NEST_R = 120
NEST_RAIL = 36
PAD_NEST = (-420.0, 0.0)                   # quarterdeck pad to the crow's nest (relative to SHIP)
JETTY_HW = 80


def ship_section(z):
    """visual hull half-beam (before the plan taper) at height z"""
    zs = [-272, -230, -180, -110, -40, 20, 70, 130, 200, 300]
    ws = [44, 92, 124, 146, 156, 160, 160, 156, 150, 144]
    return float(np.interp(z, zs, ws))


def ship_sheer(x):
    """height of the visual hull's top edge (rail cap) at station x (relative to SHIP)"""
    if x <= QD_X: return QD_Z + RAIL_H
    if x >= FC_X: return FC_Z + RAIL_H
    return WAIST_Z + BULW_H


def ship_bow_x(z):
    """stem x at height z (raked)"""
    return SHIP_BOW + 0.32 * (z - WAIST_Z)


def ship_plan(x, z):
    """plan taper factor (0..1) of the hull at station x, height z"""
    if x < SHIP_STERN - 0.5: return 0.0
    if x < -420:                                                   # stern: slight narrowing to the transom
        t = (x - SHIP_STERN) / (-420 - SHIP_STERN)
        f = 0.80 + 0.20 * math.sin(t * math.pi / 2)
    else:
        f = 1.0
    xb = ship_bow_x(z)
    x0 = 180.0
    if x > x0:
        if x >= xb: return 0.0
        f *= math.sqrt(max(0.0, 1 - ((x - x0) / (xb - x0)) ** 2))
    # the run aft below the waterline narrows toward the rudder
    if z < -40 and x < -300:
        k = min(1.0, (-40 - z) / 230.0)
        f *= 1 - 0.35 * k * ((-300 - x) / 340.0)
    return f


def ship_halfbeam(x, z):
    return ship_section(z) * ship_plan(x, z)


def ship_coll_halfbeam(x0, x1, z):
    """collision half-beam over the station [x0, x1] at height z: vertical sides (CW) above the waterline, always
    inside the visual hull (min over the station, minus 6)"""
    xs = np.linspace(x0, x1, 5)
    if z >= WATER:
        vis = min(ship_section(zz) * ship_plan(x, zz) for x in xs for zz in (WATER, 60.0, z))
        return max(0.0, min(CW * min(ship_plan(x, z) for x in xs), vis - 6))
    vis = min(ship_section(z) * ship_plan(x, z) for x in xs)
    return max(0.0, min(vis - 8, CW * min(ship_plan(x, z) for x in xs)))


def ship_deck_z(x):
    if x <= QD_X: return QD_Z
    if x >= FC_X: return FC_Z
    return WAIST_Z


def ship_stations():
    """collision station boundaries (relative x): every 40u, split at the castle fronts"""
    xs = sorted(set([SHIP_STERN] + list(np.arange(-600, 560, 40)) + [QD_X, FC_X, 560.0, 600.0]))
    return [x for x in xs if SHIP_STERN <= x <= 600]


def stair_qd(side):
    """quarterdeck stair steps [(x0, x1, z_top)] (relative x), side +1 = north (port), -1 = south; rising toward -x"""
    n = (QD_Z - WAIST_Z) // 16
    out = []
    for j in range(n):
        xa = QD_X + STAIR_RUN * (n - 1 - j)
        out.append((xa, xa + STAIR_RUN, WAIST_Z + 16 * (j + 1)))
    return out


def stair_fc(side):
    n = (FC_Z - WAIST_Z) // 16
    out = []
    for j in range(n):
        xb = FC_X - STAIR_RUN * (n - 1 - j)
        out.append((xb - STAIR_RUN, xb, WAIST_Z + 16 * (j + 1)))
    return out


def stair_hold():
    """hold stair: [(x0, x1, z_top)] descending toward -x from the hatch's east edge (tops 96 .. 16)"""
    out = []
    for j in range(6):
        xb = HATCH[2] - STAIR_RUN * j
        out.append((xb - STAIR_RUN, xb, WAIST_Z - 16 * (j + 1)))
    return out


# ================================================================================================ Skull Rock
SK = (0.0, 1088.0)
SK_FACE = 270.0                            # the face looks south over the plaza toward the galleon
SK_ROWS = [(312, 0), (326, 30), (350, 90), (384, 150), (410, 210), (424, 270), (424, 330), (414, 380), (396, 420),
           (368, 456), (344, 480)]
SK_THICK = 40
SK_TOP = 480                               # the shell ends here; the hat sits on it
SK_RR = 420.0                              # reference radius for the face polygons (u = arc length at this radius)
BALC_Z = 272                               # balcony behind the eyes
BALC_A = (196.0, 344.0)                    # balcony arc (deg)
BALC_W = 96
SK_STAIR_A0 = 20.0                         # inner stair: from here CCW up to the balcony start
SK_STAIR_N = BALC_Z // 16                  # 17 steps
HAT_Z0 = 480                               # hat brim slab 480 .. 512
BRIM_Z = 512                               # brim walk
BRIM_R0, BRIM_R1 = 300.0, 468.0
BRIM_EDGE = BRIM_R1 * math.cos(math.radians(180 / 32)) + 12   # slides start just beyond the brim collision's flat chord
CROWN_Z = 640                              # crown top walk
CROWN_R = 210.0                            # crown top radius (frustum from BRIM_R0 at BRIM_Z)
SHAFT_R = 64.0                             # shaft up through the hat (the centre pad)


def sk_deform(a, r, z):
    """skull radius at angle a (rad), profile radius r, height z: deeper front-to-back, flatter face, cheekbones, brow
    ridge over the eye sockets, temple hollows, a narrower jaw"""
    ad = math.degrees(a)
    d = math.radians((ad - SK_FACE + 180) % 360 - 180)      # 0 = straight at the face
    cd = math.cos(d)
    f = 1.0 + 0.10 * math.sin(a) ** 2                       # skulls are deeper (y) than wide (x)
    if abs(d) < math.pi / 2:
        f -= 0.10 * cd ** 2                                  # flat face
        if 180 <= z <= 270: f += 0.08 * math.exp(-((abs(math.degrees(d)) - 34) / 14) ** 2) * math.sin((z - 180) / 90 * math.pi)  # cheekbones
        if 392 <= z <= 450: f += 0.09 * max(0.0, cd) ** 6 * math.sin((z - 392) / 58 * math.pi)                                 # brow ridge
    if z < 150:
        f -= 0.10 * (1 - z / 150) * max(0.0, cd) ** 2         # jaw / chin
    if 280 <= z <= 400:
        f -= 0.035 * math.exp(-((abs(math.degrees(d)) - 82) / 18) ** 2) * math.sin((z - 280) / 120 * math.pi)                # temples
    return r * f


def sk_profile(z):
    zs = [p[1] for p in SK_ROWS]; rs = [p[0] for p in SK_ROWS]
    return float(np.interp(z, zs, rs))


def sk_face_polys():
    """openings in (u, z): u = arc length at SK_RR from the face direction (+ = counter-clockwise = toward east... the
    skull's left), z = height. Mouth (the door), nose, two eye sockets (windows from the balcony)."""
    mouth = []
    for u in np.linspace(-150, 150, 13):
        mouth.append((u, -12))
    for u in np.linspace(150, -150, 25):
        z = 150 - 22 * (abs(u) / 150) ** 3
        mouth.append((u, z))
    nose = []
    for t in np.linspace(0, 2 * math.pi, 18, endpoint=False):
        # an upside-down heart: wide at the top, pointed at the bottom
        x = 40 * math.sin(t) * (0.75 + 0.25 * math.cos(t))
        z = 240 + 42 * math.cos(t) - 8 * math.cos(2 * t)
        nose.append((x, z))
    eyes = []
    for s in (-1, 1):
        e = []
        for t in np.linspace(0, 2 * math.pi, 28, endpoint=False):
            x = s * 118 + 72 * math.cos(t) * (1 + 0.12 * s * math.sin(t))
            z = 344 + 54 * math.sin(t) + (8 if math.sin(t) > 0 else 0) * math.sin(t) ** 3
            e.append((x, z))
        eyes.append(e)
    return [mouth, nose] + eyes


def sk_balc_step(j):
    """inner stair step j: (a0, a1, z_top), climbing counter-clockwise from SK_STAIR_A0 to the balcony start"""
    span = (BALC_A[0] + 360 - SK_STAIR_A0) % 360
    da = span / SK_STAIR_N
    a0 = SK_STAIR_A0 + da * j
    return (a0, a0 + da, 16 * (j + 1))


# ================================================================================================ Fort San Padro (NW)
FORT = (-2176.0, 896.0, -1408.0, 1536.0)   # outer footprint
FORT_H = 224                               # rampart walk
FORT_W = 96                                # wall thickness (rampart walk width)
FORT_NW = 224                              # north wall thickness (holds the powder magazine)
FORT_GATE = (64, 160)                      # gate half width, height (south wall, centre)
MAG = (-1952.0, 1344.0, -1632.0, 1504.0)   # powder magazine inside the north wall (z 0..160), door south
MAG_H = 160
TOWER = (-1408.0, 896.0)                   # watchtower on the south-east corner
TOWER_R = 136
TOWER_H = 448
MERLON_H = 40
MORTAR = (-1456.0, 1236.0)                 # the mortar launcher on the east rampart

# ================================================================================================ Shark Dive Pool (NE)
SHARK = (1344.0, 832.0, 1920.0, 1792.0)
SHARK_FLOOR = -304
SHARK_STEPS = 14                           # 16u steps up the south end
DIVE = (2112.0, 1312.0)                    # dive tower centre
DIVE_HALF = 128
DIVE_TOP = 384
DIVE_FLIGHT = 80                           # stair width round the core

# ================================================================================================ Treasure Cove (SW)
COVE = (-2176.0, -1664.0, -1536.0, -384.0)
COVE_BEACH = 224                           # beach ramp at the north end (0 down to -64 over 224)
COVE_HOLE = (-1856.0, -1150.0, 176)        # deep hole (-240) in the middle
COVE_HOLE_Z = -240

# ================================================================================================ Tortuga Quay (east)
TAV = (1632.0, -896.0, 2176.0, -384.0)     # the Rusty Anchor tavern (door west)
TAV_H = 240                                # roof terrace walk
SHOP = (1696.0, -1696.0, 2112.0, -1312.0)  # Ye Olde Gift Shoppe (door west)
SHOP_H = 192
SHACKS = [(-2192.0, 0.0, -1872.0, 256.0), (-1808.0, -1984.0, -1488.0, -1760.0)]   # beach shacks in Treasure Cove
SHACK_H = 176

# ================================================================================================ slides
TUBE_R = 52
TUBE_ZC = 46


def _bez(p0, p1, p2, p3, n):
    out = []
    for t in np.linspace(0, 1, n):
        out.append(((1 - t) ** 3) * np.array(p0, float) + 3 * ((1 - t) ** 2) * t * np.array(p1, float)
                   + 3 * (1 - t) * t * t * np.array(p2, float) + t ** 3 * np.array(p3, float))
    return out


def _with_z(xy, z0, z1, ease=None):
    xy = [np.asarray(p, float) for p in xy]
    Ls = np.concatenate([[0], np.cumsum([np.linalg.norm(b - a) for a, b in zip(xy, xy[1:])])])
    t = Ls / Ls[-1]
    if ease is not None: t = ease(t)
    return [(float(p[0]), float(p[1]), float(z0 + (z1 - z0) * tt)) for p, tt in zip(xy, t)]


def tube_path():
    """Cannonball Run (closed tube): off the west brim of the hat, a spiral round the skull's back, then south-west
    over the plaza into Treasure Cove"""
    cx, cy = SK
    xy = [(cx - BRIM_EDGE, cy)]
    xy += _bez((cx - BRIM_EDGE, cy), (cx - 720, cy), (cx - 860, cy - 60), (cx - 920, cy - 400), 12)[1:]
    xy += _bez((cx - 920, cy - 400), (cx - 980, cy - 760), (-1240, 260), (-1500, 40), 12)[1:]
    xy += _bez((-1500, 40), (-1700, -120), (-1820, -320), (-1840, -720), 10)[1:]
    pts = _with_z(xy, BRIM_Z, 0)
    return [(cx - BRIM_R1 + 120, cy, float(BRIM_Z))] + pts


def flume_path():
    """Plank Plunge (open log flume): off the east brim, north-east round behind the dive pool and into it"""
    cx, cy = SK
    xy = [(cx + BRIM_EDGE, cy)]
    xy += _bez((cx + BRIM_EDGE, cy), (cx + 760, cy), (cx + 820, cy + 520), (cx + 1100, cy + 640), 14)[1:]
    xy += _bez((cx + 1100, cy + 640), (cx + 1340, cy + 740), (1600, 1940), (1720, 1820), 10)[1:]
    xy += _bez((1720, 1820), (1780, 1760), (1760, 1640), (1660, 1560), 6)[1:]
    pts = _with_z(xy, BRIM_Z, 0)
    return [(cx + BRIM_R1 - 120, cy, float(BRIM_Z))] + pts


# ================================================================================================ secret: Padbeard's Hoard
VAULT = dict(x0=-768, x1=768, y0=-576, y1=576, z0=-2560, z1=-2112)
SECRET_BARREL = (-262.0, 0.0)              # tipped giant rum barrel at the aft end of the hold (relative to SHIP), open end +x

# ================================================================================================ movers
SHARK_R = 230                              # sharks circling the dive pool
GULL_R = 1700                              # gulls circling the bay
GULL_Z = 1150
