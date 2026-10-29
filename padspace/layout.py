"""Shared layout constants for wop_padspace (Starsplash Station): read by build_space.py (brushes, entities),
sp_shapes.py (convex collision solids) and sp_models.py (MD3 geometry), so the models and the collision line up.

An outer-space water park on a moon, human scale (~32u per metre, Padman 56u), under a starry sky with a ringed
gas giant and the Earth rising. x east, y north, park deck z 0, water surface z -16. The lunar plain lies 112u below
the park's rim wall on three sides, a crater ridge closes the north.

   y 2048 +--------------------------------------------------------------------+
          | PLANET PADURN   |      ROCKET "PADSTAR I"         | THE BLACK HOLE   |
          | (ringed planet, |  (walk in, spiral stair to the  | (gravity-well    |
          |  walkable ring, |   cockpit, balcony, nose deck,  |  dive bowl,      |
          |  lazy river)    |   slides W and E off balcony)   |  satellite tower)|
      400 +-----------------+--------------------------------+------------------+
          | CRATER SPRINGS  |   CRATER LAGOON                 | STAR BOULEVARD   |
          | (beach pool,    |   the lunar lander standing in  | (Cosmic Cafe,    |
          |  habitat pods)  |   the middle, jetties N + S     |  Mission Control,|
          |                 |                                 |  Zero-G Loo)     |
   y-2048 +--------------------------------------------------------------------+
          x -2304                                                         x 2304
"""
import math
import numpy as np

HX, HY = 2304, 2048
SKY = dict(x0=-2944, x1=2944, y0=-2688, y1=2944, z0=-896, z1=2560)
WATER = -16
SLAB_BOT = -384
SHALLOW = -64
DEEP = -272
PLAIN_Z = -112                   # the lunar plain beyond the rim walls (decor, unreachable)
BANK_W, BANK_H = 352, 384        # north crater ridge: slope from the park edge up to BANK_H


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def octagon(rect, cut, inset=0.0):
    x0, y0, x1, y1 = rect
    x0 += inset; y0 += inset; x1 -= inset; y1 -= inset
    c = max(0.0, cut - inset * (math.sqrt(2) - 1))
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


# ================================================================================================ Crater Lagoon
LAG = (-1344.0, -1792.0, 1344.0, -192.0)
LAG_CUT = 352
SHALLOW_BAND = 192
SLOPE_W = 160
ISLETS = [(-900.0, -560.0, 96), (930.0, -1450.0, 96), (-980.0, -1500.0, 80), (960.0, -540.0, 80)]   # moon-rock islets (cover)
LAG_STEPS = [(-1344, -1250, -1280, -1000, 'w'), (1280, -1100, 1344, -850, 'e'), (-760, -1792, -520, -1728, 's'),
             (520, -1792, 760, -1728, 's')]
BEACH = (-920, -416, -480, -192)          # regolith beach ramp (north shore, west of the jetty), 0 down to -64
JETTY_HW = 80

# ================================================================================================ the lunar lander
LANDER = (0.0, -992.0)
LD_HALF = 208.0                            # descent stage: octagon half-size
LD_CUT = 80.0
DECK_Z = 128                               # descent stage deck walk
CAB = (-96.0, -80.0, 96.0, 80.0)         # ascent cabin footprint (relative), walls 16
CAB_T = 16
CAB_TOP = 320                              # cabin roof walk
CAB_DOOR_HW = 40
CAB_DOOR_H = 104
LEG_R0, LEG_R1 = 200.0, 352.0              # landing legs: from the stage corners out to the footpads


def lander_oct(inset=0.0):
    x, y = LANDER
    return [(x + px, y + py) for (px, py) in octagon((-LD_HALF, -LD_HALF, LD_HALF, LD_HALF), LD_CUT, inset)]


# ================================================================================================ the rocket
RK = (0.0, 1150.0)
RK_R = 260.0                               # body radius
RK_T = 32                                  # shell thickness
RK_SKIRT = 296.0                           # flared skirt radius at the ground
RK_BODY_TOP = 690.0                        # the ogive nose starts here
RK_TIP = 1200.0
COCK_Z = 352                               # cockpit deck walk
NOSE_Z = 640                               # nose observation deck walk
SLAB_T = 16
RK_STAIR_W = 96
RK_STAIR_A0 = 290.0                        # stair: from here counter-clockwise up to the cockpit deck
RK_STAIR_N = COCK_Z // 16                  # 22 steps
RK_STAIR_DA = 15.0
RK_HOLE = 72.0                             # centre holes in the cockpit and nose decks (pads)
BALC_R0, BALC_R1 = RK_R + 2, 432.0         # outer balcony ring at COCK_Z
BALC_RAIL = 36
RK_FACE = 270.0                            # the door looks south
RK_RR = RK_R                               # reference radius for the openings (u = arc length at this radius)
FIN_A = (45.0, 135.0, 225.0, 315.0)
FIN_R1 = 560.0                             # fin tip radius at the ground
FIN_T = 24
SIDE_DOORS = (0.0, 180.0)                  # cockpit doors out to the balcony (deg)


def rk_profile(z):
    """outer radius of the rocket at height z"""
    if z <= 140:
        return float(np.interp(z, [0, 50, 100, 140], [RK_SKIRT, 286, 268, RK_R]))
    if z <= RK_BODY_TOP: return RK_R
    Ln = RK_TIP - RK_BODY_TOP                 # tangent ogive nose
    rho = (RK_R ** 2 + Ln ** 2) / (2 * RK_R)
    x = max(0.0, RK_TIP - z)
    return max(2.0, math.sqrt(max(0.0, rho ** 2 - (Ln - x) ** 2)) + RK_R - rho)


def rk_rows():
    zs = sorted(set([0, 25, 50, 75, 100, 120, 140] + list(range(160, int(RK_BODY_TOP) + 1, 30)) + [RK_BODY_TOP] +
                    [RK_BODY_TOP + (RK_TIP - RK_BODY_TOP) * (1 - (1 - t) ** 1.4) for t in np.linspace(0, 1, 26)[1:]]))
    return [(rk_profile(z), float(z)) for z in zs]


def rk_inner_r(z):
    """inner (cabin) surface radius at height z (shell offset inward by RK_T along the profile normal)"""
    rows = np.array(rk_rows(), float)
    tg = np.gradient(rows, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    inn = rows - pn * RK_T
    inn[:, 0] = np.maximum(inn[:, 0], 2.0)
    o = np.argsort(inn[:, 1])
    return float(np.interp(z, inn[o, 1], inn[o, 0]))


def rk_open_polys():
    """openings in (u, z): u = arc length at RK_RR from the face direction (+ = counter-clockwise). Main door, the
    cockpit portholes, the two balcony doors (east u = -RK_RR*pi/2, west +...), the panorama window in the nose and
    three small nose windows"""
    P = []
    hw = 72
    door = [(-hw, -12), (hw, -12), (hw, 116)] + [(hw * math.cos(t), 116 + 26 * math.sin(t)) for t in np.linspace(0, math.pi, 9)[1:-1]] + [(-hw, 116)]
    P.append(door)
    q = RK_RR * math.pi / 2
    for uc in (-q, q):                       # balcony doors (east/west)
        P.append([(uc - 50, COCK_Z - 2), (uc + 50, COCK_Z - 2), (uc + 50, COCK_Z + 100)] +
                 [(uc + 50 * math.cos(t), COCK_Z + 100 + 18 * math.sin(t)) for t in np.linspace(0, math.pi, 7)[1:-1]] + [(uc - 50, COCK_Z + 100)])
    for uc in (0.0, RK_RR * math.pi):                         # portholes over the door (south) and north
        P.append([(uc + 44 * math.cos(t), 450 + 44 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 20, endpoint=False)])
    for uc in (-q * 0.5, q * 0.5, -q * 1.5, q * 1.5):          # four more portholes between
        P.append([(uc + 34 * math.cos(t), 450 + 34 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 18, endpoint=False)])
    # panorama window in the nose (south): wide, rounded corners
    P.append([(-96, 660), (96, 660), (112, 680), (112, 856), (92, 880), (-92, 880), (-112, 856), (-112, 680)])
    for uc in (-q, q, RK_RR * math.pi):
        P.append([(uc + 40 * math.cos(t), 760 + 48 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 20, endpoint=False)])
    return P


def rk_step(j):
    """inner stair step j: (a0, a1, z_top), climbing counter-clockwise from RK_STAIR_A0"""
    a0 = RK_STAIR_A0 + RK_STAIR_DA * j
    return (a0, a0 + RK_STAIR_DA, 16 * (j + 1))


# ================================================================================================ Planet Padurn (NW)
PL = (-1720.0, 1280.0)
PL_R = 250.0
PL_ZC = 380.0                              # sphere centre height (bottom at 130)
PL_CAP = 600                               # flat polar cap walk
RING_Z = 304                               # walkable ring deck
RING_R0, RING_R1 = 236.0, 424.0
RIVER_R0, RIVER_R1 = 384.0, 540.0          # lazy river (48 deep) round the island
RIVER_FLOOR = -64
PED_R0, PED_R1 = 150.0, 70.0               # pedestal: cone from the ground (r PED_R0) to under the sphere (r PED_R1)
PL_STAIR_A = 0.0                           # the stair bridge comes in from the east
PL_STAIR_W = 96
PL_BRIDGES = (300.0, 60.0)                 # flat footbridges over the river (deg)
RIVER_STEPS = (120.0, 240.0, 330.0, 30.0)  # 16u step exits (deg), on both banks


def pl_cap_r():
    return math.sqrt(PL_R ** 2 - (PL_CAP - PL_ZC) ** 2)


def pl_sphere_r(z):
    d = z - PL_ZC
    return math.sqrt(max(0.0, PL_R ** 2 - d * d))


# ================================================================================================ The Black Hole (NE)
BH = (1600.0, 1250.0)
BH_R = 500.0
BH_RINGS = 19                              # 16u ring steps down the gravity well, 24 deep each
BH_STEP = 24.0
BH_FLOOR = -16 - 16 * BH_RINGS             # -320
SAT = (2077.0, 773.0)                      # satellite dive tower centre
SAT_HALF = 112
SAT_TOP = 384
SAT_FLIGHT = 80


def bh_ring(k):
    """ring k: (r_inner, r_outer, z_top)"""
    return (BH_R - BH_STEP * (k + 1), BH_R - BH_STEP * k, -16 - 16 * (k + 1))


# ================================================================================================ Crater Springs (SW)
COVE = (-2176.0, -1664.0, -1536.0, -384.0)
COVE_BEACH = 224
COVE_HOLE = (-1856.0, -1150.0, 176)
COVE_HOLE_Z = -240
PODS = [(-2192.0, 0.0, -1872.0, 256.0), (-1808.0, -1984.0, -1488.0, -1760.0)]   # habitat pods (walk in, pad to roof)
POD_H = 176

# ================================================================================================ Star Boulevard (east)
CAFE = (1632.0, -896.0, 2176.0, -384.0)    # Cosmic Cafe (door west)
CAFE_H = 240                               # roof terrace walk
MC = (1696.0, -1696.0, 2112.0, -1312.0)    # Mission Control (door west)
MC_H = 192
LOO = (2160.0, -1130.0)                    # Zero-G Loo (secret): door west
LOO_HALF = 40

# ================================================================================================ slides
TUBE_R = 52
TUBE_ZC = 46
BALC_EDGE = BALC_R1 * math.cos(math.radians(180 / 32)) + 12


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
    """Wormhole (closed tube): off the west side of the balcony, a sweeping curve south-west over the plaza (south of
    the planet's stair bridge) into Crater Springs"""
    cx, cy = RK
    xy = [(cx - BALC_EDGE, cy)]
    xy += _bez((cx - BALC_EDGE, cy), (cx - 700, cy), (cx - 900, cy - 120), (-1020, 760), 12)[1:]
    xy += _bez((-1020, 760), (-1140, 520), (-1240, 320), (-1420, 60), 10)[1:]
    xy += _bez((-1420, 60), (-1600, -200), (-1700, -560), (-1700, -820), 10)[1:]
    pts = _with_z(xy, COCK_Z, 0)
    return [(cx - BALC_R1 + 100, cy, float(COCK_Z))] + pts


def flume_path():
    """Comet Run (open flume): off the east side of the balcony, east then south-east into the Black Hole"""
    cx, cy = RK
    xy = [(cx + BALC_EDGE, cy)]
    xy += _bez((cx + BALC_EDGE, cy), (cx + 700, cy), (cx + 760, cy + 560), (cx + 1000, cy + 640), 14)[1:]
    xy += _bez((cx + 1000, cy + 640), (cx + 1240, cy + 720), (1500, 1980), (1560, 1660), 10)[1:]
    pts = _with_z(xy, COCK_Z, 0)
    return [(cx + BALC_R1 - 100, cy, float(COCK_Z))] + pts


# ================================================================================================ secret: the Star Vault
VAULT = dict(x0=-768, x1=768, y0=-576, y1=576, z0=-2560, z1=-2112)

# ================================================================================================ movers
COMET_R = 1900
COMET_Z = 1500
MOON_R = 360                               # Padurn's moonlets
MOON_Z = 690
