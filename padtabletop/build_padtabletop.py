#!/usr/bin/env python3
"""Padman's Tabletop Quest (wop_padtabletop) - FFA on a Dungeons & Dragons gaming table, built on woplib.

    OUT=<dir> python3 build_padtabletop.py          (wopbuild.py padtabletop preview / all)

Padman is a miniature: one battle-mat square = 128u, dungeon walls 2 inches (256u). x east, y north (the cliffs).
Mat x -2304..2304, y -1920..1920, floor z 0. Wooden table rail round it, top z 576 (walkable, 384 wide).
Zones: forest strip (south, ruined cottage, pond), modular stone dungeon (centre, 13 rooms, campfire hall), east
clearing, lower cliff terrace z 256 with a crenellated rampart and a tunnel through it, upper plateau z 512 with the
dragon and its hoard, and the rail with dice, mug, rulebooks, Padmaster screen and the dice tower.
Secret: hop into the well (north-west room) -> "Behind the Padmaster's Screen".
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, sign_box, hull
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
from meshlib import grid_normals
import tt_models as TM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
G, WH, WT = TM.G, TM.WH, TM.WT
X0, Y0, X1, Y1 = -2304, -1920, 2304, 1920             # the mat (inside the rail)
RX, RY = 2688, 2304                                  # walkable edge of the rail top
HX, HY, HZ = 2816, 2432, 3200                        # sky hull
RZ, TZ, PZ = TM.RZ, TM.TERR_Z, TM.PLAT_Z
DX0, DY0, DC, DR = -2048, -1280, 28, 18              # dungeon origin, columns, rows (squares)
YC = DY0 + DR * G                                    # 1024: the lower cliff face (dungeon north edge)
YP = 1408                                            # upper cliff face
XP = -640                                            # upper plateau west face
K = MapKit(MAP, NS, LONG, (-RX, -RY, RX, RY), worldspawn={'_ambient': '22', '_color': '1 0.92 0.8', 'gridsize': '128 128 192'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)


def cx(c): return DX0 + c * G
def cy(r): return DY0 + r * G


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, search=200, **kw):
    """custom MD3 + weapclip collision at the nearest free spot (K.prop nudges it out of walls and keep-clear zones)"""
    c = TM.COLL.get(name, {})
    return K.prop(ML.PLACE[name], x, y, z, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), angle=angle, search=search, **kw)


def deco(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


def world_model(name, X, lit=True):
    """a mesh built in world coordinates -> MD3 stored round its footprint centre, placed back (decor, no collision)"""
    V = np.concatenate([np.array(mm.V) for mm in X.m.values() if len(mm.V)])
    mn, mx = V.min(0), V.max(0)
    o = np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
    X.shift(o)
    pl = ML.save(name, X)
    return K.custom(pl, float(o[0]), float(o[1]), float(o[2]), lit=lit, occupy=False)


# ================================================================================================= structure
def shell():
    """sky hull (the games room is the sky box), structural seal under the table, the mat floor, the wooden rail"""
    sk = T('sky')
    K.add(box((-HX - 32, -HY - 32, -224), (HX + 32, HY + 32, -192), tex6(), detail=False))
    K.add(box((-HX - 32, -HY - 32, HZ), (HX + 32, HY + 32, HZ + 32), tex6(bot=sk), detail=False))
    K.add(box((-HX - 32, -HY - 32, -192), (-HX, HY + 32, HZ), tex6(e=sk), detail=False))
    K.add(box((HX, -HY - 32, -192), (HX + 32, HY + 32, HZ), tex6(w=sk), detail=False))
    K.add(box((-HX, -HY - 32, -192), (HX, -HY, HZ), tex6(n=sk), detail=False))
    K.add(box((-HX, HY, -192), (HX, HY + 32, HZ), tex6(s=sk), detail=False))
    # the table under everything (detail), split by mat print
    K.add(box((-HX, -HY, -192), (HX, HY, -160), tex6()))
    stone, grass = T('mat_stone'), T('mat_grass')
    floors = [((DX0, DY0), (cx(DC), YC), stone),
              ((X0, DY0), (DX0, YC), grass), ((cx(DC), DY0), (X1, YC), grass),
              ((X0, Y0), (X1, DY0), grass), ((X0, YC), (X1, Y1), T('cave_floor'))]
    FLOORS.clear()
    for (a, b, t) in floors:
        FLOORS.append(box((a[0], a[1], -160), (b[0], b[1], 0), tex6(top=t)))
    # rail: four wooden blocks, top 576, LED strip + lip on the inner face
    mp, mv = T('maple'), T('maple_v')
    K.add(box((-HX, -HY, -160), (HX, Y0, RZ), tex6(top=mp, n=mv)),
          box((-HX, Y1, -160), (HX, HY, RZ), tex6(top=mp, s=mv)),
          box((-HX, Y0, -160), (X0, Y1, RZ), tex6(top=mp, e=mv)),
          box((X1, Y0, -160), (HX, Y1, RZ), tex6(top=mp, w=mv)))
    K.reserve(((-HX, -HY, 0), (HX, Y0, RZ)), ((-HX, Y1, 0), (HX, HY, RZ)), ((-HX, Y0, 0), (X0, Y1, RZ)), ((X1, Y0, 0), (HX, Y1, RZ)))
    led, lip = T('led'), {'top': mp, 'bot': mv, 'side': mv}
    for (a, b, side) in (((X0, Y0), (X1, Y0), 's'), ((X0, Y0), (X0, 1280), 'w'), ((X1, Y0), (X1, YP - 32), 'e'), ((X0 + 192, Y1), (XP - 32, Y1), 'n')):
        if side == 's':
            K.add(box((a[0], Y0, 504), (b[0], Y0 + 4, 520), led))
        elif side == 'n':
            K.add(box((a[0], Y1 - 4, 504), (b[0], Y1, 520), led))
        elif side == 'w':
            K.add(box((X0, a[1] + 20, 504), (X0 + 4, b[1] - 20, 520), led))
        else:
            K.add(box((X1 - 4, a[1] + 20, 504), (X1, b[1], 520), led))
    # player clip at the outer edge of the rail top (the last 128u is table edge seen against the room)
    for (a, b) in (((-HX, -HY, RZ), (HX, -RY, HZ)), ((-HX, RY, RZ), (HX, HY, HZ)),
                   ((-HX, -RY, RZ), (-RX, RY, HZ)), ((RX, -RY, RZ), (HX, RY, HZ))):
        K.add(box(a, b, CLIP))


FLOORS = []


def floors_carved():
    """floor slabs with the pond and the well shaft cut out (written after those features are known)"""
    for f in FLOORS:
        cut = [c for c in CUTS if all(c.bounds()[0][i] < f.bounds()[1][i] and c.bounds()[1][i] > f.bounds()[0][i] for i in range(3))]
        if cut:
            top = [fc.tex for fc in f.faces if fc.n[2] > 0.9][0]
            for p in wopmap.carve(f, cut, tex=T('cave_floor')):
                for fc in p.faces:
                    fc.tex = top if (fc.n[2] > 0.9 and abs(fc.d) < 0.5) else (CAULK if fc.n[2] < -0.9 else T('cave_floor'))
                K.add(p)
        else:
            K.add(f)


CUTS = []


# ================================================================================================= dungeon walls
# (c0, r0, c1, r1, [(a, b, kind)])  kind: arch (door, lintel above 176), ruin (jagged collapse, open in the middle)
WALLS = [
    (0, 0, 28, 0, [(3, 4, 'arch'), (10, 12, 'ruin'), (17, 18, 'arch'), (24, 25, 'arch')]),
    (0, 0, 0, 18, [(9, 10, 'arch'), (15, 16, 'arch')]),
    (28, 0, 28, 18, [(3, 4, 'arch'), (9, 11, 'ruin'), (15, 16, 'arch')]),
    (0, 6, 6, 6, [(2, 3, 'arch')]),
    (0, 12, 13, 12, [(2, 3, 'arch'), (7.5, 8.5, 'arch')]),
    (17, 12, 28, 12, [(23, 24, 'arch')]),
    (6, 5, 21, 5, [(7, 8, 'arch'), (11, 13, 'ruin'), (17, 18, 'arch')]),
    (21, 6, 28, 6, [(24, 25, 'arch')]),
    (6, 0, 6, 12, [(2, 3, 'arch'), (9, 10, 'arch')]),
    (14, 0, 14, 5, [(2, 3, 'arch')]),
    (21, 0, 21, 12, [(2, 3, 'arch'), (8, 9, 'arch')]),
    (9, 5, 9, 12, [(6, 8, 'ruin'), (10, 11, 'arch')]),
    (19, 5, 19, 12, [(7, 8, 'arch'), (10, 11, 'arch')]),
    (7, 12, 7, 18, [(14, 15, 'arch')]),
    (13, 12, 13, 18, [(15, 16, 'arch')]),
    (17, 12, 17, 18, [(13, 14, 'arch')]),
]
POST = 24          # half width of a connector post
ARCH_TOP = 176
RUIN_H = [216, 176, 136, 96, 56, 24]      # jagged heights stepping down into a ruin gap (32u slices)
ARCHES = []        # (x, y, angle) of every arch opening (spandrel models, doors)


def wall_line_brushes(p0, p1, openings, posts, gaps=(), z0=0, h=WH, thick=WT):
    """convex brushes for one straight wall line (world coords, along x or y). posts = positions where this line
    owns a connector post (48u square, 8u taller); gaps = positions of posts owned by another line (the wall stops at
    their faces). Returns (groups, post brushes); a group = the brushes up to and including a post (one MD3 each)."""
    horiz = p0[1] == p1[1]
    a0, a1 = (p0[0], p1[0]) if horiz else (p0[1], p1[1])
    c = p0[1] if horiz else p0[0]
    t = thick / 2

    def B(lo, hi, zlo, zhi, half=t):
        if horiz: return box((lo, c - half, zlo), (hi, c + half, zhi), WCLIP)
        return box((c - half, lo, zlo), (c + half, hi, zhi), WCLIP)
    events = [(p - POST, p + POST, 'post') for p in posts] + [(p - POST, p + POST, 'gap') for p in gaps]
    events += [(a, b, k) for (a, b, k) in openings]
    events = sorted((max(lo, a0), min(hi, a1), k) for (lo, hi, k) in events if hi > a0 and lo < a1)
    groups, cur, pbs, pos = [], [], [], a0
    for (lo, hi, k) in events:
        if lo > pos + 0.5: cur.append(B(pos, lo, z0, z0 + h))
        if k == 'post':
            pb = B(lo, hi, z0, z0 + h + 8, POST)
            cur.append(pb); pbs.append(pb)
            groups.append(cur); cur = []
        elif k == 'gap':
            if cur: groups.append(cur)
            cur = []
        elif k == 'arch':
            cur.append(B(lo, hi, z0 + ARCH_TOP, z0 + h))
            mid = (lo + hi) / 2
            ARCHES.append(((mid, c) if horiz else (c, mid)) + (0 if horiz else 90,))
        elif k == 'ruin':
            n = int(round((hi - lo) / 32))
            for i in range(n):
                if (n - 1) / 2 - 1.6 <= i <= (n - 1) / 2 + 1.6: continue          # the open gap (~96-128u)
                d = min(i, n - 1 - i)
                cur.append(B(lo + i * 32, lo + (i + 1) * 32, z0, z0 + RUIN_H[min(d, len(RUIN_H) - 1)]))
            RUINS.append((((lo + hi) / 2, c) if horiz else (c, (lo + hi) / 2)) + (0 if horiz else 90,))
        pos = max(pos, hi)
    if pos < a1 - 0.5: cur.append(B(pos, a1, z0, z0 + h))
    if cur: groups.append(cur)
    return [g for g in groups if g], pbs


RUINS = []


def dungeon():
    """the modular dungeon: walls as grey brick MD3 pieces with weapclip, connector posts at ends and junctions"""
    ends = set()
    for (c0, r0, c1, r1, _) in WALLS: ends.add((c0, r0)); ends.add((c1, r1))
    owned = set()
    k = 0
    for (c0, r0, c1, r1, ops) in WALLS:
        horiz = r0 == r1
        pts = sorted(p for p in ends if p[1] != DR and ((horiz and p[1] == r0 and c0 <= p[0] <= c1) or
                                                         (not horiz and p[0] == c0 and r0 <= p[1] <= r1)))
        mine = [p for p in pts if p not in owned]
        other = [p for p in pts if p in owned]
        owned.update(mine)
        coord = (lambda p: cx(p[0])) if horiz else (lambda p: cy(p[1]))
        ops_w = [((cx(a) if horiz else cy(a)), (cx(b) if horiz else cy(b)), kind) for (a, b, kind) in ops]
        groups, pbs = wall_line_brushes((cx(c0), cy(r0)), (cx(c1), cy(r1)), ops_w, [coord(p) for p in mine],
                                        [coord(p) for p in other])
        prects = [b.bounds() for b in pbs]
        for g in groups:
            K.solid_piece(f'wall{k:02d}', g, wall_texfn(prects)); k += 1
    for (x, y, a) in ARCHES:
        deco('arch', x, y, 0, angle=a)
        if a == 0: K.keep_clear(x - 64, y - 112, x + 64, y + 112, 0, 180)
        else: K.keep_clear(x - 112, y - 64, x + 112, y + 64, 0, 180)
    for i, (x, y, a) in enumerate(RUINS):
        if a == 0: K.keep_clear(x - 60, y - 112, x + 60, y + 112, 0, 180)
        else: K.keep_clear(x - 112, y - 60, x + 112, y + 60, 0, 180)
        for s in (-1, 1):
            dx, dy = (0, s * 60) if a == 0 else (s * 60, 0)
            deco('rubble', x + dx * 0 + (s * 120 if a == 0 else dx), y + (dy if a == 0 else s * 120), 0, angle=a + 90 * (i % 2)) if False else None
        deco('rubble', x + (0 if a == 0 else 70), y + (70 if a == 0 else 0), 0, angle=a + 30 * i)


def wall_texfn(prects):
    def f(c, n, poly):
        if n[2] < -0.5: return None
        for (mn, mx) in prects:
            if all(mn[i] - 1 <= c[i] <= mx[i] + 1 for i in range(3)):
                return TM.M_['post'], ML.planar_uv(n, 128)
        if n[2] > 0.5: return TM.M_['cap'], ML.planar_uv(n, 128)
        return TM.M_['brick'], ML.planar_uv(n, 128)
    return f


def arch_model():
    """spandrels above a 128u door opening: semicircle r 64 springing at 112, crown at the lintel (176)"""
    X = ML.Model()
    from meshlib import prism
    for s in (-1, 1):
        pts = [(s * 64, 112)] + [(s * 64 * math.cos(t), 112 + 64 * math.sin(t)) for t in np.linspace(0.1, math.pi / 2, 7)] + [(s * 64, 176)]
        pts = [(x, z) for (x, z) in pts]
        if s < 0: pts = pts[::-1]
        M = ML.Model(); prism(M.mesh(TM.M_['brick']), pts, -WT / 2, WT / 2, tile=128)
        X.add_model(M, np.array([[1.0, 0, 0], [0, 0, -1], [0, 1, 0]]), (0, 0, 0))
    ML.save('arch', X)


# ================================================================================================= cliffs
def rock_skin(name, a, b, z0, z1, axis, sign, holes=(), amp=22, step=32, seed=0):
    """lumpy painted-foam rock over a flat cliff face. axis 'y': the face is the plane y = const (a, b = x range),
    sign = outward normal direction. holes = [(u0, u1, z0, z1)] cells skipped (caves, stairs). Displacement only
    outward, zero at the top and bottom rows so the grass edge and the floor line stay clean."""
    rng = np.random.default_rng(seed)
    nu = max(2, int(round((b - a) / step))); nv = max(2, int(round((z1 - z0) / step)))
    ph = rng.uniform(0, 6.3, 8)

    def disp(u, v):
        t = (v - z0) / (z1 - z0)
        env = math.sin(math.pi * t) ** 0.7
        return amp * env * (0.55 + 0.25 * math.sin(u / 47 + ph[0]) * math.cos(v / 31 + ph[1]) +
                            0.2 * math.sin(u / 13 + v / 17 + ph[2]) + 0.15 * math.cos(u / 7.3 + ph[3]))
    X = ML.Model(); sh = TM.M_['rock']
    P = np.zeros((nv + 1, nu + 1, 3)); UV = np.zeros((nv + 1, nu + 1, 2))
    plane = sign_pos = None
    for i in range(nv + 1):
        z = z0 + (z1 - z0) * i / nv
        for j in range(nu + 1):
            u = a + (b - a) * j / nu
            d = disp(u, z) * sign
            P[i, j] = (u, PLANE[0] + d, z) if axis == 'y' else (PLANE[0] + d, u, z)
            UV[i, j] = (u / 256, -z / 256)
    N = grid_normals(P)
    want = np.array([0, sign, 0.0]) if axis == 'y' else np.array([sign, 0, 0.0])
    if (N.reshape(-1, 3) @ want).mean() < 0: N = -N
    M = X.mesh(sh)
    idx = {}

    def vid(i, j):                       # only vertices used by a kept cell go into the mesh
        if (i, j) not in idx: idx[(i, j)] = M.add_v(P[i, j], N[i, j], UV[i, j])
        return idx[(i, j)]
    for i in range(nv):
        for j in range(nu):
            uc = a + (b - a) * (j + 0.5) / nu; zc = z0 + (z1 - z0) * (i + 0.5) / nv
            if any(h0 <= uc <= h1 and hz0 <= zc <= hz1 for (h0, h1, hz0, hz1) in holes): continue
            q = (vid(i, j), vid(i, j + 1), vid(i + 1, j), vid(i + 1, j + 1))
            M.tri(q[0], q[1], q[2]); M.tri(q[1], q[3], q[2])
    world_model(name, X)


PLANE = [0]


def cliffs():
    """lower terrace (z 256) with the tunnel cut through it, upper plateau (z 512), rock skins, the rampart"""
    st, gr, rk = T('mat_stone'), T('flock'), T('rock')
    t1 = box((X0, YC, 0), (X1, YP, TZ), tex6(top=st))
    t2 = box((X0, YP, 0), (XP, Y1, TZ), tex6(top=st, e=rk))
    up = box((XP, YP, 0), (X1, Y1, PZ), tex6(top=gr))
    # tunnel: crypt mouth (A) -> corridor -> clearing mouth (B), roof at 160
    tun = [box((1152, YC - 8, 0), (1312, 1312, 160), rk), box((1152, 1152, 0), (1984, 1312, 160), rk),
           box((1824, YC - 8, 0), (1984, 1312, 160), rk)]
    for p in wopmap.carve(t1, tun, tex=rk): K.add(p)
    K.add(t2, up)
    K.reserve(((X0, YC, 0), (X1, YP, TZ)), ((X0, YP, 0), (XP, Y1, TZ)), ((XP, YP, 0), (X1, Y1, PZ)))
    for b in tun: K.keep_clear(*b.bounds()[0][:2], *b.bounds()[1][:2], 0, 160)
    K.route('tunnel', (1232, 900, 0), (1904, 900, 0))
    # rock skins (holes: tunnel mouths, the stair flight, the west ramp)
    PLANE[0] = YC
    rock_skin('cliff_lo', X0, X1, 0, TZ, 'y', -1, holes=[(1152, 1312, 0, 160), (1824, 1984, 0, 160), (STAIR[0] - 32, STAIR[1] + 32, 0, TZ),
                                                     (X0, RAMP_W[2], 0, TZ)], seed=1)
    PLANE[0] = YP
    rock_skin('cliff_hi', XP, X1, TZ, PZ, 'y', -1, seed=2)
    PLANE[0] = XP
    rock_skin('cliff_hw', YP, Y1, TZ, PZ, 'x', -1, holes=[(PSTAIR[1] - 32, PSTAIR[3] + 32, TZ, PZ)], seed=3)
    # tunnel mouth frames: a few boulders either side
    for x in (1120, 1344, 1792, 2016):
        deco('boulder', x, YC - 96, 0, angle=x % 360)
    # rampart on the terrace edge (crenellated, gap where the stairs arrive)
    for (a, b) in ((RAMP_W[2] + 32, STAIR[0] - 32), (STAIR[1] + 32, X1)):
        brushes, posts = [], []
        x = a
        brushes.append(box((a, YC, TZ), (b, YC + 32, TZ + 40), WCLIP))
        xs = np.arange(a + 40, b - 40, 128)
        for xm in xs:
            brushes.append(box((xm - 24, YC, TZ + 40), (xm + 24, YC + 32, TZ + 104), WCLIP))
        K.solid_piece(f'rampart{int(a > 0)}', brushes, wall_texfn([]))
    K.botclip_rect(X0, YC + 32, X1, YC + 56, TZ, sides='s', gaps=[('s', X0, RAMP_W[2] + 32), ('s', STAIR[0] - 32, STAIR[1] + 32),
                                                                 ('s', 1600, 1800)])


STAIR = (-288, -32)                         # dungeon -> terrace flight (x range), y 512..1024
RAMP_W = (-2296, 640, -2072, YC)            # west yard rubble ramp onto the terrace (rises north)
PSTAIR = (-1152, 1600, XP, 1792)            # terrace -> plateau flight (rises east)


def climbs():
    st = {'top': T('cap_b'), 'side': T('brick_b'), 'bot': CAULK}
    K.stairs16(STAIR[0], 512, STAIR[1], YC, 0, TZ, 'n', st, route='grand_stairs')
    K.keep_clear(STAIR[0] - 16, 400, STAIR[1] + 16, 512, 0, 96)
    rk = {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}
    K.ramp(*RAMP_W, 0, TZ, 'n', rk, route='west_ramp')
    K.keep_clear(RAMP_W[0], RAMP_W[1] - 100, RAMP_W[2], RAMP_W[1], 0)
    K.stairs16(*PSTAIR, TZ, PZ, 'e', rk, route='plateau_stairs')
    K.keep_clear(PSTAIR[0] - 100, PSTAIR[1], PSTAIR[0], PSTAIR[3], TZ)
    # terrace -> north rail (west end), plateau -> rail (east end)
    K.stairs16(X0, 1280, X0 + 192, Y1, TZ, RZ, 'n', rk, route='rail_stairs_w')
    K.stairs16(1984, 1792, 2240, Y1, PZ, RZ, 'n', rk, route='rail_stairs_e')


# ================================================================================================= forest + clearing
COT = (-2176, -1856, -1600, -1408)          # ruined cottage footprint
COT_T, COT_DECK, COT_TOP = 48, 192, 224
POND = (960, -1840, 1640, -1440, -112)


def cottage():
    """ruined stone cottage: door on the north side, windows, a wooden upper deck (the top) reached by stairs inside,
    walls only 32u above the deck (clear line of fire), a chimney stub at the north-west corner"""
    x0, y0, x1, y1 = COT; t = COT_T; h = COT_TOP
    B = []
    door = (-1952, -1824)
    B += [box((x0, y1 - t, 0), (door[0], y1, h), WCLIP), box((door[1], y1 - t, 0), (x1, y1, h), WCLIP),
          box((door[0], y1 - t, 160), (door[1], y1, h), WCLIP)]
    B += [box((x0, y0, 0), (x1, y0 + t, h), WCLIP)]                         # south wall (the stairs run along it)
    ew = (-1720, -1580)                                                     # east window
    B += [box((x1 - t, y0 + t, 0), (x1, ew[0], h), WCLIP), box((x1 - t, ew[1], 0), (x1, y1 - t, h), WCLIP),
          box((x1 - t, ew[0], 0), (x1, ew[1], 64), WCLIP), box((x1 - t, ew[0], 150), (x1, ew[1], h), WCLIP)]
    B += [box((x0, y0 + t, 0), (x0 + t, y1 - t, h), WCLIP)]
    B += [box((x0, y1 - 112, h), (x0 + 112, y1, 352), WCLIP)]               # chimney stub
    K.solid_piece('cottage', B, lambda c, n, p: None if n[2] < -0.5 else (TM.M_['cstone'], ML.planar_uv(n, 128)))
    # deck at 176..192 over the interior except the stairwell (inside the south wall, rising west)
    sw = (x0 + t + 96, y0 + t + 8, x1 - t, y0 + t + 136)                    # stairwell (8u off the window wall)
    dk = {'top': T('det_floor'), 'bot': T('det_wall'), 'side': T('det_wall')}
    K.add(box((x0 + t, y0 + t + 168, COT_DECK - 16), (x1 - t, y1 - t, COT_DECK), dk),
          box((x0 + t, y0 + t, COT_DECK - 16), (sw[0], y0 + t + 168, COT_DECK), dk))
    K.reserve(((x0 + t, y0 + t, COT_DECK - 16), (x1 - t, y1 - t, COT_DECK)))
    K.stairs16(sw[0], sw[1], sw[2], sw[3], 0, COT_DECK, 'w', dk, route=None)
    K.route('cottage_up', (x1 - t - 40, y0 + t + 260, 0), (x0 + t + 48, y0 + t + 72, COT_DECK))
    K.route('cottage_in', ((door[0] + door[1]) / 2, y1 + 80, 0), ((door[0] + door[1]) / 2, y1 - 160, 0))
    K.keep_clear(door[0], y1, door[1], y1 + 100, 0)
    K.keep_clear(x1 - t - 80, y0 + t, x1 - t, y0 + t + 128, 0)


def forest():
    # trees: catalog summer/spring/autumn trees and the custom model-railway firs
    for (p, x, y, s, a) in (('tree_summer', -1250, -1560, 0.8, 20), ('tree_spring', -300, -1500, 0.75, 140),
                            ('tree_autumn', 300, -1700, 0.8, 70), ('tree_summer', 1950, -1650, 0.9, 200),
                            ('tree_summer', 1950, 480, 0.9, 10)):
        K.catalog(f'pad_ddmix/trashcan/{p}.md3', x, y, 0, scale=s, angle=a)
    for (x, y) in ((-1450, -1360), (-950, -1790), (-150, -1370), (650, -1450), (760, -1720), (1780, -1380),
                   (2120, -980), (1720, 100), (2150, 820)):
        place('pine', x, y, 0, angle=(x * 3) % 360)
    for (x, y, a, sc) in ((-850, -1350, 30, 0.7), (650, -1640, 300, 0.7), (1700, -1100, 90, 0.7), (2150, -300, 150, 0.7), (-2190, 300, 0, 0.5)):
        K.catalog('pad_ddmix/trashcan/bush.md3', x, y, 0, scale=sc, angle=a)
    for (x, y) in ((-1150, -1450), (-300, -1650), (480, -1580), (1850, -500), (1650, 650)):
        K.catalog('pad_ddmix/trashcan/grass.md3', x, y, 0, scale=0.6, clip=False)
    # freestanding ruined wall in the forest (the photo's long wall)
    groups, pbs = wall_line_brushes((-1000, -1720), (-400, -1720), [(-780, -620, 'ruin')], [-1000 + POST, -400 - POST])
    for i, g in enumerate(groups): K.solid_piece(f'fwall{i}', g, wall_texfn([b.bounds() for b in pbs]))
    deco('rubble', -700, -1630, 0); deco('rubble', -690, -1810, 0, angle=150)
    # pond with steps out at its west end
    x0, y0, x1, y1, zb = POND
    CUTS.append(box((x0, y0, zb), (x1, y1, 0), CAULK))
    steps = K.stairs16(x0, y0 + 96, x0 + 224, y1 - 96, zb, 0, 'w', {'top': T('rock'), 'side': T('rock'), 'bot': CAULK}, route=None)
    K.water_box((x0, y0, zb), (x1, y1, -8), T('water'), cutters=steps)
    for (x, y) in ((x0 - 60, y0 + 30), (x1 + 50, y1 - 60), (x1 - 100, y1 + 60)):
        deco('boulder', x, y, 0, angle=x % 360)
    # props round the cottage and the clearing
    place('barrel', -1530, -1330, 0); place('barrel', -1540, -1440, 0, angle=40); place('crate', -2120, -1330, 0, angle=12)
    place('dummy', 1900, -760, 0, angle=200)
    place('mini_wizard', 1750, -200, 0, angle=250)
    place('mini_knight', 2100, 50, 0, angle=200)
    place('mini_rogue', 160, -1430, 0, angle=160)
    place('mini_goblin', -1000, -1820, 0, angle=60)
    place('crate', 1700, 300, 0, angle=30); place('crate', 1810, 300, 0, angle=5)


# ================================================================================================= rooms
def rooms():
    # storage (SW): crates, barrels, shelf
    for (x, y, a) in ((-1920, -1150, 0), (-1800, -1150, 8), (-1920, -1030, 15), (-1500, -1150, 30)):
        place('crate', x, y, 0, angle=a)
    for (x, y) in ((-1900, -650), (-1780, -640), (-1900, -770)):
        place('barrel', x, y, 0)
    place('shelf', -1600, -572, 0, angle=0)
    # tavern: table, benches, stools, barrels, dwarf
    place('table', -1664, -150, 0, angle=0)
    place('bench', -1664, -300, 0); place('bench', -1664, 0, 0)
    place('stool', -1420, -150, 0); place('barrel', -1940, 170, 0); place('barrel', -1950, -260, 0)
    place('mini_dwarf', -1400, 120, 0, angle=200)
    # well room (secret) + table
    deco('well', *WELL, 0)
    place('table', -1860, 800, 0, angle=90); place('stool', -1720, 960, 0); place('stool', -1930, 560, 0)
    place('shelf', -1350, 955, 0, angle=0)
    # barracks: three beds, a chest
    for x in (-1060, -880, -460):
        place('bed', x, -1060, 0, angle=180)
    place('chest', -850, -730, 0, angle=0)
    # forge: braziers, anvil, weapon rack
    place('brazier', 0, -860, 0); place('brazier', 420, -860, 0)
    place('anvil', -100, -1150, 0, angle=20)
    place('weapon_rack', 500, -1200, 0, angle=0)
    # armory: racks, knight, chest
    place('weapon_rack', 1300, -1200, 0, angle=0); place('weapon_rack', 1460, -1100, 0, angle=90)
    place('mini_knight', 900, -1000, 0, angle=45); place('chest', 1400, -600, 0)
    # great hall: campfire, ogres, bedrolls
    hx, hy = HALL
    place('campfire', hx, hy, 0)
    for (dx, dy, a) in ((-330, 120, 300), (300, -40, 120), (40, 330, 200)):
        place('mini_ogre', hx + dx, hy + dy, 0, angle=a)
    for (dx, dy, a) in ((-200, -260, 20), (180, 240, 110), (-380, -100, 80)):
        deco('bedroll', hx + dx, hy + dy, 0, angle=a)
    place('barrel', -600, 180, 0); place('crate', -700, -500, 0, angle=10)
    place('mini_skeleton', 150, 180, 0, angle=230)
    # shrine: statue on its plinth, braziers
    sx, sy = SHRINE
    place('pedestal', sx, sy, 0)
    K.catalog('pad_statues/statue_super.md3', sx, sy, 64, angle=180, clip=True, nudge=False)
    place('brazier', sx - 260, sy + 230, 0); place('brazier', sx + 260, sy + 230, 0)
    # library: shelves along the walls, table + wizard
    for x in (-1000, -720):
        place('shelf', x, 955, 0)
    place('shelf', -442, 420, 0, angle=270)
    place('table', -760, 600, 0, angle=90); place('mini_wizard', -560, 470, 0, angle=200)
    K.catalog('pad_books/pad_ob_fl_md.md3', -760, 560, 96, angle=10, clip=False, nudge=False)
    # crypt: coffins, bones, skeletons, skull
    for x in (400, 620, 840):
        place('coffin', x, 850, 0)
    deco('bones', 600, 450, 0); deco('bones', 1000, 700, 0, angle=90)
    place('mini_skeleton', 900, 450, 0, angle=200); place('mini_skeleton', 300, 700, 0, angle=330)
    K.catalog('pad_ddmix/jail/skull.md3', 1400, 600, 0, scale=0.7, angle=200)
    # torches on walls (decor + lights)
    for (x, y, a) in TORCHES:
        deco('torch', x, y, 150, angle=a)
        K.light(x + 24 * math.cos(math.radians(a - 90)), y + 24 * math.sin(math.radians(a - 90)), 210, 180, '1 0.7 0.4')


HALL = (cx(14), cy(8.5))
SHRINE = (cx(24.5), cy(9))
WELL = (cx(3.5), cy(15))
TORCHES = [(cx(4.5), cy(12) - WT / 2, 0), (cx(15.5), cy(5) + WT / 2, 180), (cx(11), cy(5) + WT / 2, 180),
           (cx(25.5), cy(12) - WT / 2, 0), (cx(10.5), cy(12) + WT / 2, 180), (cx(22.5), cy(6) + WT / 2, 180),
           (cx(20), cy(12) + WT / 2, 180), (cx(3), cy(6) - WT / 2, 0)]


# ================================================================================================= upper level + rail
def plateau():
    """dragon on the upper plateau with its hoard (Betty), bones, ferns; boulders"""
    dx, dy = DRAGON
    place('dragon', dx, dy, PZ, angle=0)
    deco('hoard', HOARD[0], HOARD[1], PZ)
    deco('bones', dx - 820, dy - 120, PZ); deco('bones', dx + 950, dy - 150, PZ, angle=120)
    K.catalog('pad_ddmix/jail/skull.md3', dx - 700, dy + 160, PZ, scale=0.8, angle=150)
    for (x, y) in ((2150, 1500), (-400, 1850), (1550, 1480), (300, 1500)):
        K.catalog('pad_ddmix/trashcan/grass.md3', x, y, PZ, scale=0.5, clip=False)
    K.catalog('pad_ddmix/plants/fern.md3', 1850, 1820, PZ, scale=0.3, clip=False)
    # terrace dressing: crates, barrels, a goblin lookout, west terrace pines
    place('mini_goblin', -1200, 1250, TZ, angle=270); place('mini_dwarf', 800, 1200, TZ, angle=280)
    place('barrel', -1900, 1150, TZ); place('crate', 500, 1300, TZ, angle=20)
    place('pine', -1800, 1650, TZ); place('pine', -1350, 1700, TZ, angle=40)
    K.catalog('pad_ddmix/trashcan/bush.md3', -900, 1500, TZ, scale=0.6, angle=60)


DRAGON = (900, 1664)
HOARD = (200, 1640)


def rail_things():
    """real-world objects on the wooden rail: dice, mug, rulebooks, character sheet, pencil, snack bowl, dice tray,
    Padmaster screen (north), dice tower (north-east corner)"""
    s = (Y0 + -RY) / 2              # middle of the south rail band
    deco('char_sheet', -1500, s, RZ, angle=8); deco('pencil', -1150, s - 40, RZ, angle=-20)
    place('dice_tray', 300, s, RZ, angle=0)
    place('d6_white', 220, s - 30, RZ + 4, angle=20); place('d6_red', 380, s + 40, RZ + 4, angle=60)
    place('snack_bowl', 1500, s, RZ)
    place('d20_red', -400, s + 40, RZ, angle=30); place('d20_blue', 950, s - 60, RZ, angle=80)
    e = (X1 + RX) / 2
    place('mug', e, -900, RZ, angle=90)
    place('d20_purple', e, 300, RZ, angle=10); place('d6_black', e - 40, 950, RZ, angle=30)
    w = (X0 - RX) / 2
    place('book_stack', w, BOOKS_Y, RZ, angle=90)
    place('d20_green', w, -1400, RZ, angle=200); place('d6_blue', w + 30, 900, RZ, angle=70)
    n = (Y1 + RY) / 2
    place('dm_screen', 0, Y1 + 300, RZ, angle=0)
    place('dice_tower', *TOWER, RZ)
    place('d20_blue', -1500, n, RZ, angle=140); place('d6_red', 1500, n - 30, RZ, angle=15)
    # spare minis waiting their turn along the rail (cover on the long rail runs)
    for (nm, x, y, ang) in (('mini_knight', -900, s, 90), ('mini_wizard', 700, s + 30, 100), ('mini_ogre', e, -1600, 180),
                            ('mini_dwarf', e - 20, 1250 - 330, 200), ('mini_goblin', w, 300, 0), ('mini_rogue', w + 10, 1500, 330),
                            ('mini_skeleton', -2100, n, 270), ('mini_knight', 1900, n + 20, 250)):
        place(nm, x, y, RZ, angle=ang)


BOOKS_Y = -400
TOWER = (2496, 2112)


# ================================================================================================= secret
VAULT = (-640, -448, 640, 448); VAULT_Z = -1408


def secret():
    """hop into the well -> a sealed room "Behind the Padmaster's Screen": giant notes on the walls, a huge d20,
    minis waiting their turn, the goodies; a teleporter back to the well room door"""
    wx, wy = WELL
    r_in, r_out = TM.WELL_RI, TM.WELL_R
    n = 12
    ring = []
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pts = []
        for r in (r_in, r_out):
            for a in (a0, a1):
                for z in (0, TM.WELL_H):
                    pts.append((wx + r * math.cos(a), wy + r * math.sin(a), z))
        ring.append(hull(pts, WCLIP))
    K.add(*ring)
    K.occupy(wx - r_out - 8, wy - r_out - 8, wx + r_out + 8, wy + r_out + 8, 0, 280)
    CUTS.append(wopmap.cyl(wx, wy, r_in - 1, -128, 0, CAULK, 16))
    K.secret((wx - 40, wy - 40, -126), (wx + 40, wy + 40, -70), dest=(0, -120, VAULT_Z), angle=90, name='well')
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 448
    wl, fl = T('det_wall'), T('det_floor')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': fl, 'side': wl, 'bot': wl}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': wl, 'side': wl, 'top': wl}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=wl), detail=False),
          box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=wl), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=wl), detail=False),
          box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=wl), detail=False))
    K.add(sign_box((-560, y1 - 4, z + 80), (-40, y1, z + 340), T('dmnote0'), 1024, 512, facing='s', edge=wl))
    K.add(sign_box((40, y1 - 4, z + 80), (560, y1, z + 340), T('dmnote1'), 1024, 512, facing='s', edge=wl))
    K.add(sign_box((x1 - 4, -300, z + 80), (x1, 220, z + 340), T('dmnote2'), 1024, 512, facing='w', edge=wl))
    place('d20_red', -420, 250, z, angle=30)
    place('mini_ogre', 420, 230, z, angle=200); place('mini_dwarf', 250, 300, z, angle=220)
    K.item('item_padpower', 0, 120, z); K.item('item_revival', -350, -150, z); K.item('holdable_killerducks', 350, -150, z)
    K.item('item_armor_padshield', 0, 300, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(wx + 260, wy - 200, 0), angle=0, name='vault_exit')
    K.light(0, 0, z + 380, 650, '1 0.9 0.75'); K.light(-450, 0, z + 220, 280, '1 0.85 0.7'); K.light(450, 0, z + 220, 280, '1 0.85 0.7')


# ================================================================================================= pads, loot, spawns
def pads():
    S = TM.pad_skin
    K.jumppad(0, -1580, 0, land=(0, -2140, RZ), apex=RZ + 200, name='pad_forest_rail',
              skin=S('pad_plate', (0, -1580), (0, -2140)), edges=[(0, Y0 + 20, RZ)])
    K.jumppad(2060, -500, 0, land=(2480, -500, RZ), apex=RZ + 180, name='pad_clearing_rail',
              skin=S('pad_plate', (2060, -500), (2480, -500)), edges=[(X1, -500, RZ)])
    K.jumppad(1700, 760, 0, land=(1700, 1230, TZ), apex=TZ + 200, name='pad_clearing_terrace',
              skin=S('pad_plate', (1700, 760), (1700, 1230)), edges=[(1700, YC + 32, TZ + 104)])
    K.jumppad(2080, 1200, TZ, land=(2080, 1650, PZ), apex=PZ + 170, name='pad_terrace_plateau',
              skin=S('pad_rune', (2080, 1200), (2080, 1650)), edges=[(2080, YP, PZ)])
    K.jumppad(2496, 1250, RZ, land=(2496, 2112, RZ + TM.TOWER_H), apex=RZ + TM.TOWER_H + 80, name='pad_tower',
              skin=S('pad_coaster', (2496, 1250), (2496, 2112)), edges=[(2496, 1656, RZ + 24), (2496, 1952, RZ + TM.TOWER_H)])
    K.jumppad((X0 - RX) / 2, BOOKS_Y - 560, RZ, land=((X0 - RX) / 2, BOOKS_Y + 150, RZ + 4 * TM.BOOK_T), apex=RZ + 4 * TM.BOOK_T + 120,
              name='pad_books', skin=S('pad_coaster', ((X0 - RX) / 2, BOOKS_Y - 560), ((X0 - RX) / 2, BOOKS_Y)))
    K.jumppad(-2176, BOOKS_Y + 60, 0, land=((X0 - RX) / 2, BOOKS_Y + 150, RZ + 4 * TM.BOOK_T), apex=RZ + 4 * TM.BOOK_T + 330,
              name='pad_yard_books', skin=S('pad_plate', (-2176, BOOKS_Y + 60), ((X0 - RX) / 2, BOOKS_Y + 150)),
              edges=[(X0 + 20, BOOKS_Y + 120, RZ)])
    K.jumppad(-1700, 1300, TZ, land=(-480, 1520, PZ), apex=PZ + 180, name='pad_west_plateau',
              skin=S('pad_rune', (-1700, 1300), (-560, 1500)), edges=[(XP, 1480, PZ)])


def items():
    K.weapon('imperius', 2496, 2112, RZ + TM.TOWER_H, marker='purple')
    K.weapon('betty', HOARD[0] - 40, HOARD[1], PZ + 30, marker='black')
    K.weapon('balloony', (X0 - RX) / 2, BOOKS_Y + 150, RZ + 4 * TM.BOOK_T, marker='orange')
    K.weapon('pumper', 1560, 1232, 0, marker='green')
    K.weapon('splasher', 1400, -1640, POND[4], marker='blue')
    K.weapon('boaster', HALL[0] + 200, HALL[1] + 200, 0, marker='orange')
    K.weapon('bubbleg', -1888, -1632, 0, marker='green')
    ammo = {'imperius': [(0, 1300, TZ), (-1888, -1632, COT_DECK), (2500, -1500, RZ)],
            'betty': [(1700, 1720, PZ), (-1664, -420, 0), (300, -2110, RZ + 4), (cx(24.5), cy(3), 0)],
            'balloony': [(-2496, 1200, RZ), (cx(10), cy(15), 0), (1904, 1150, 0), (-1600, 1700, TZ)],
            'pumper': [(cx(22), cy(15), 0), (2100, -1000, 0), (-900, 1300, TZ), (cx(3), cy(3), 0)],
            'splasher': [(POND[0] + 300, POND[1] - 70, 0), (-1950, -1450, 0), (cx(20), cy(8.5), 0), (2496, 600, RZ)],
            'boaster': [(cx(7.5), cy(8.5), 0), (cx(17.5), cy(1.5), 0), (-300, -1450, 0), (1000, 1250, TZ), (cx(10), cy(2.5), 0)],
            'bubbleg': [(-2176, 0, 0), (cx(3), cy(9), 0), (1950, 300, 0), (-1000, -1750, 0), (cx(14), cy(13), 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', cx(12), cy(9), 0); K.ammo('nipper', 1700, -800, 0); K.ammo('nipper', -2176, -700, 0)
    K.item('item_armor_padshield', cx(26), cy(1.5), 0)
    K.item('item_armor_shard', -1500, 1800, TZ); K.item('item_armor_shard', 2500, 300, RZ); K.item('item_armor_shard', cx(8), cy(15), 0)
    K.item('item_speedy', -1200, 1150, TZ)
    K.item('item_jumper', 1900, -150, 0)
    K.item('holdable_floater', -1500, -150, 0)
    K.station(SHRINE[0] + 250, SHRINE[1] - 230, 0, ang=90)
    K.station(-2176, -1000, 0, ang=0)
    for (x, y, z, a) in ((cx(3), cy(4), 0, 90), (cx(3), cy(10), 0, 0), (cx(10), cy(3.5), 0, 0), (cx(17.5), cy(3.5), 0, 180),
                         (cx(24.5), cy(1.5), 0, 90), (cx(11), cy(10.5), 0, 270), (cx(17), cy(7), 0, 180), (cx(24.5), cy(10.5), 0, 270),
                         (cx(10), cy(13.5), 0, 0), (cx(22), cy(13.5), 0, 90), (cx(4), cy(13.5), 0, 0), (-1700, -1250, 0, 90),
                         (300, -1450, 0, 90), (1900, -1200, 0, 90), (1900, 200, 0, 180), (-600, 1200, TZ, 270),
                         (1200, 1850, PZ, 180), (-2200, 900, 0, 270)):
        K.spawn(x, y, z, a)


def lights_sounds():
    K.light_grid(X0, Y0, X1, Y1, 950, 640, 1100, color='1 0.9 0.75')
    hx, hy = HALL
    K.light(hx, hy, 120, 420, '1 0.6 0.25')                                           # campfire
    for (x, y) in ((0, -860), (420, -860), (SHRINE[0] - 260, SHRINE[1] + 230), (SHRINE[0] + 260, SHRINE[1] + 230)):
        K.light(x, y, 220, 260, '1 0.65 0.3')                                         # braziers
    K.light(1568, 1232, 120, 300, '0.8 0.85 1'); K.light(1232, 1150, 120, 220, '0.8 0.85 1'); K.light(1904, 1150, 120, 220, '0.8 0.85 1')
    K.light(-1888, -1632, 120, 260, '1 0.9 0.75')                                    # cottage
    K.light(DRAGON[0] - 640, DRAGON[1], PZ + 200, 300, '1 0.8 0.5')                  # hoard glow
    K.speaker(hx, hy, 80, 'ambient/fire_crackling')
    K.speaker(1568, 1232, 80, 'ambient/water_drippling')
    K.speaker(1300, -1640, 0, 'ambient/water_rippling')
    K.timer_sound(-1000, -1700, 300, 'animal/bird_owl1', 'owl', 30, 15)
    K.timer_sound(DRAGON[0], DRAGON[1], PZ + 520, 'ambient/wind_night', 'dragon_breath', 25, 10)
    K.trigger_sound((2400, 2000, RZ + TM.TOWER_H), (2600, 2220, RZ + TM.TOWER_H + 96), 'human/applause', 'summit', wait=8)


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


def extra_models():
    arch_model()
    X = ML.Model()                                    # boulder
    from meshlib import ellipsoid as ell
    ell(X.mesh(TM.M_['rock']), (0, 0, 0), 70, 56, 60, nu=12, nv=8, flat_bottom=0,
        bump=lambda p, t: 1 + 0.18 * math.sin(3 * t) * math.cos(2 * p) + 0.08 * math.sin(7 * t + 1))
    ML.save('boulder', X)


if __name__ == '__main__':
    TX = TM.textures(K)
    TM.all_models(); extra_models()
    TM.write_sky(OUT)
    shell(); cliffs(); climbs(); dungeon(); cottage(); secret()
    pads()
    rooms(); forest(); plateau(); rail_things()
    items(); lights_sounds()
    floors_carved()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
