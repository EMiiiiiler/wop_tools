"""Custom MD3 architecture for wop_padbakery (Sweet Padman's Bakery): the deck oven, the counters, the show cake and
its missing slice, the commercial floor mixer (+ its turning paddle), the display cabinet, the cool room, the cooling
racks and the flour bin. All geometry and art is original and generated here. Props live in bk_props.py.

Architecture is drawn from the convex solids in bk_shapes.py (or matches them exactly), so the weapclip collision in
build_bakery.py matches the visible surfaces. Models are stored with their origin at the footprint centre, z 0."""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from bk_mesh import *
import layout as L
import bk_shapes as SH

CENTRES = {}        # model name -> world (x, y) of its origin


def SB(img, shade=30, **kw): return S(BT(img), 'lm', shade=shade, **kw)
def SM(img, shade=60, **kw): return S(img, 'lm', shade=shade, **kw)
def SC(img='steel', v=0.18, **kw): return S(img, 'lms', v=v, shade=kw.pop('shade', 40), **kw)


def place_save(name, X, cx, cy, local=False):
    if not local: X.shift((cx, cy, 0))
    CENTRES[name] = (cx, cy)
    return save(name, X)


# ================================================================================================= deck oven
def oven():
    X = Model()
    xi0, xi1 = L.OV_X0 + L.OV_SIDE, L.OV_FRONT - L.OV_FRONT_T
    yi0, yi1 = L.OV_Y0 + L.OV_SIDE, L.OV_Y1 - L.OV_SIDE
    st, sd, br, hs = SC('steel', 0.16, tag='ov'), SM('steel_d', tag='ov'), SM('brick', 40, tag='ov'), SM('hearth', 40, tag='ov')

    def fn(part, c, n, poly):
        if part == 'ov_flue': return None
        if n[2] < -0.9 and c[2] < 1: return None
        if c[0] < L.OV_X0 + 0.5 and n[0] < -0.9: return None                 # against the room wall
        q = c + n * 3
        inside = xi0 < q[0] < xi1 + 1 and yi0 < q[1] < yi1 and q[2] < L.OV_TOP - 1
        if inside:
            if q[2] < L.PROOF_TOP: return sd, planar_uv(n, 128)
            if n[2] > 0.9: return hs, planar_uv(n, 256)
            return br, uvz(n, 256)
        if part == 'ov_door': return (sd if n[2] > 0.9 else st), planar_uv(n, 128)
        return st, planar_uv(n, 256)
    solids_parts(X, SH.oven(), fn)
    xf = L.OV_FRONT
    # door handles along each door's front edge, hinge pins
    for zd in (L.DECK1, L.DECK2):
        for (ya, yb) in L.MOUTHS:
            tube(X.mesh(SC('steel', 0.3, tag='ovh')), [(xf + L.DOOR_D - 10, ya + 40, zd + 2), (xf + L.DOOR_D - 10, ya + 40, zd + 12),
                                                     (xf + L.DOOR_D - 10, yb - 40, zd + 12), (xf + L.DOOR_D - 10, yb - 40, zd + 2)], 4, nseg=8)
            for yy in (ya + 14, yb - 14):
                cylm(X.mesh(SM('black', tag='ov')), (xf + 2, yy, zd - L.DOOR_T), 6, L.DOOR_T, n=8)
    # glowing heating elements under each deck ceiling and in the proofer, pilot lights
    gl = S('glow_o', 'glow', wave='sin 0.9 0.1 0 0.3', tag='ov')
    for zc in (L.DECK1 + L.DECK_H, L.DECK2 + L.DECK_H):
        for yy in np.linspace(yi0 + 80, yi1 - 80, 5):
            tube(X.mesh(gl), [(xi0 + 40, yy, zc - 6), (xi1 - 40, yy, zc - 6)], 3, nseg=6)
    for yy in np.linspace(yi0 + 120, yi1 - 120, 3):
        tube(X.mesh(S('glow_w', 'glow', tag='ov')), [(xi0 + 60, yy, L.PROOF_TOP - 5), (xi1 - 60, yy, L.PROOF_TOP - 5)], 3, nseg=6)
    # proofer: a wire rack inside, the glass door swung open against the side
    wr = S('wire', 'alpha', tag='ovw')
    for zz in (100, 200):
        quad_uv(X.mesh(wr), (xi0 + 20, yi0 + 20, zz), (xi1 - 20, yi0 + 20, zz), (xi1 - 20, yi1 - 20, zz), (xi0 + 20, yi1 - 20, zz),
                [(0, 0), (8, 0), (8, 16), (0, 16)], (0, 0, 1))
        for (yy) in (yi0 + 8, yi1 - 12):
            boxm(X.mesh(SC('steel', 0.3, tag='ovh')), (xi0 + 10, yy, zz - 4), (xi1 - 10, yy + 4, zz), r=0.5, tile=32)
    # control panel on the front of the proofer slab: dials, a display, the PADMAN OVENS plate
    zp = (L.PROOF_TOP + L.DECK1) / 2
    for k, yy in enumerate((-480, -360, -240, 240, 360, 480)):
        m = Mesh(); cylm(m, (0, 0, 0), 20, 10, n=16)
        X.mesh(SM('black', tag='ov')).add(m, rot_axis((0, 1, 0), math.pi / 2), (xf, yy, zp))
        picture(X.mesh(SM('dial', tag='ov')), (xf + 10.5, yy, zp), 34, 34, (1, 0, 0))
    picture(X.mesh(S('screen', 'glow', tag='ov')), (xf + 0.6, 0, zp + 10), 180, 70, (1, 0, 0))
    for k, yy in enumerate((-120, 120)):
        sphere(X.mesh(S('glow_o' if k else 'glow_y', 'glow', tag='ovl')), (xf, yy, zp - 30), 8, nu=8, nv=5)
    picture(X.mesh(SM('plate_ov', tag='ov')), (xf + 0.6, 0, (L.DECK2 + L.DECK_H + L.OV_TOP) / 2), 420, 56, (1, 0, 0))
    # steel kick strip and a chrome rail round the top edge
    tube(X.mesh(SC('steel', 0.3, tag='ovh')), [(xf + 2, L.OV_Y0 + 4, L.OV_TOP - 4), (xf + 2, L.OV_Y1 - 4, L.OV_TOP - 4)], 4, nseg=8)
    return place_save('oven', X, (L.OV_X0 + xf) / 2, 0)


def flue():
    X = Model()
    fx, fy, fr = L.FLUE
    st = SC('steel', 0.22, tag='fl')
    cylm(X.mesh(st), (0, 0, L.OV_TOP), fr + 2, L.CEIL - L.OV_TOP, n=24, caps=False)
    for zz in (L.OV_TOP, 1400, 1800, L.CEIL - 30):
        torus(X.mesh(st), (0, 0, zz + 6), fr + 4, 6, n=24, m=6)
    cylm(X.mesh(SM('steel_d', tag='fl')), (0, 0, L.OV_TOP), fr + 22, 20, n=24)
    return place_save('flue', X, fx, fy, local=True)


# ================================================================================================= counters
def counters():
    X = Model()
    bt, cab, wd, wdd = SM('butcher', 30, tag='ct'), SM('cabinet', 30, tag='ct'), SM('wood', 30, tag='ct'), SM('wood_d', 30, tag='ct')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[1] > L.HY - 0.5 and n[1] > 0.9: return None
        if c[0] > L.HX - 0.5 and n[0] > 0.9: return None
        if part == 'ct_top': return (bt if n[2] > -0.9 else wd), planar_uv(n, 256)
        if part == 'ws_board': return (wd if n[2] > 0.9 else wdd), planar_uv(n, 256)
        if part == 'ct_shelf': return (wd if abs(n[2]) > 0.9 else cab), planar_uv(n, 256)
        if part in ('ct_back', 'ct_closed'): return wdd, planar_uv(n, 256)
        return cab, planar_uv(n, 256)
    solids_parts(X, SH.counters(), fn)
    ch = SC('steel', 0.3, tag='cth')
    # chrome towel rail along the worktop front edges, brackets under the wall shelf, little knobs on the corner cabinet
    tube(X.mesh(ch), [(L.N_X0 + 60, L.N_FRONT - 30, L.WORK - 60), (L.E_FRONT - 60, L.N_FRONT - 30, L.WORK - 60)], 4, nseg=8)
    tube(X.mesh(ch), [(L.E_FRONT - 30, L.E_Y0 + 60, L.WORK - 60), (L.E_FRONT - 30, L.N_FRONT - 90, L.WORK - 60)], 4, nseg=8)
    for xx in np.linspace(L.N_X0 + 60, L.E_FRONT - 60, 6):
        tube(X.mesh(ch), [(xx, L.N_FRONT - 16, L.WORK - 60), (xx, L.N_FRONT - 30, L.WORK - 60)], 3, nseg=6)
    for yy in np.linspace(L.E_Y0 + 60, L.N_FRONT - 90, 4):
        tube(X.mesh(ch), [(L.E_FRONT - 16, yy, L.WORK - 60), (L.E_FRONT - 30, yy, L.WORK - 60)], 3, nseg=6)
    x0, x1, yf, zt = L.WALL_SHELF
    for xx in np.linspace(x0 + 80, x1 - 80, 5):
        prism(X.mesh(wdd), [(xx - 8, L.HY), (xx + 8, L.HY), (xx + 8, L.HY - 1), (xx - 8, L.HY - 1)], zt - 24 - 1, zt - 24, tile=64)
        P = [np.array(p, float) for p in ((xx, L.HY, zt - L.WALL_SHELF_T), (xx, yf + 20, zt - L.WALL_SHELF_T), (xx, L.HY, zt - 150))]
        for s in (-1, 1):
            Q = [p + np.array([s * 6, 0, 0]) for p in P]
            X.mesh(wdd).poly(Q if s > 0 else Q[::-1], (s, 0, 0), [(q[1] / 64, -q[2] / 64) for q in (Q if s > 0 else Q[::-1])])
    cx, cy = (L.N_X0 + L.HX) / 2, (L.E_Y0 + L.HY) / 2
    return place_save('counters', X, cx, cy)


# ================================================================================================= the show cake
def bead_ring(M, cx, cy, r, z, br, n=None, lift=0.0):
    n = n or max(12, int(2 * math.pi * r / (br * 1.8)))
    for k in range(n):
        a = 2 * math.pi * k / n
        sphere(M, (cx + r * math.cos(a), cy + r * math.sin(a), z + lift), br, nu=8, nv=5)


def sugar_rose(M, c, r=22.0, R=np.eye(3), leaf=None):
    """rose: a central bud and two rings of cupped petals"""
    c = np.asarray(c, float)
    ellipsoid(M, c + R @ np.array([0, 0, r * 0.55]), r * 0.35, r * 0.35, r * 0.45, nu=10, nv=6, R=R)
    for ring, (k, rr, zz, sz) in enumerate(((5, 0.45, 0.4, 0.42), (7, 0.8, 0.25, 0.48))):
        for j in range(k):
            a = 2 * math.pi * (j + 0.5 * ring) / k
            p = np.array([math.cos(a) * rr * r, math.sin(a) * rr * r, zz * r])
            ellipsoid(M, c + R @ p, sz * r, sz * r * 0.5, sz * r * 0.9, nu=8, nv=5, R=R @ rot_z(a + math.pi / 2))


def cake():
    cx, cy = 0.0, 0.0
    X = Model()
    (r1, _, z1), (r2, _, z2), (r3, _, z3) = L.TIERS
    a0, a1 = 22.5, 337.5
    w1, w2, w3 = SM('bc_white', 50, tag='ck'), SM('dots', 50, tag='ck'), SM('bc_lilac', 50, tag='ck')
    ch = SM('bc_choc', 60, tag='ckd')
    # tier 1 (white with a chocolate drip), the missing slice cut out of the east
    revolve(X.mesh(w1), [(r1, 0), (r1, z1)], n=60, a0=a0, a1=a1, u_tiles=12, vlen=256)
    annulus(X.mesh(w1), cx, cy, r2 - 8, r1, z1, a0, a1, n=60)
    lay = SM('layers', 40, tag='ck'); spg = SM('sponge', 40, tag='ck')
    for a in (a0, a1):
        t = math.radians(a)
        rad = np.array([math.cos(t), math.sin(t), 0])
        nn = np.array([-math.sin(t), math.cos(t), 0]) * (-1 if a == a0 else 1)
        P = [np.array([cx, cy, 0.0]), rad * r1, rad * r1 + [0, 0, z1], np.array([cx, cy, z1])]
        uv = [(0, 1), (r1 / 224, 1), (r1 / 224, 0), (0, 0)]
        X.mesh(lay).poly(P, nn, uv)
    annulus(X.mesh(spg), cx, cy, 0, r2 + 4, z1, -22.5, 22.5, n=8, up=False)
    # chocolate drip round tier 1's top edge
    revolve(X.mesh(ch), [(r1 + 3, z1 - 14), (r1 + 4, z1 - 2), (r1 - 6, z1 + 3), (r1 - 24, z1 + 3)], n=60, a0=a0, a1=a1, u_tiles=12)
    rng = np.random.default_rng(3)
    for k in range(64):
        a = math.radians(a0 + (a1 - a0) * (k + 0.5) / 64 + rng.uniform(-1.5, 1.5))
        Ld = rng.uniform(26, 92)
        ellipsoid(X.mesh(ch), (math.cos(a) * (r1 + 1), math.sin(a) * (r1 + 1), z1 - 10 - Ld * 0.45), 9, 9, Ld * 0.55, nu=8, nv=6)
    # piped borders
    pip = SM('bc_white', 60, tag='ckp')
    bead_ring(X.mesh(pip), cx, cy, r1 + 2, 9, 11)
    bead_ring(X.mesh(SM('pearl', 70, tag='ckp')), cx, cy, r2 + 1, z1 + 8, 9)
    # tier 2: pink with white dots, a pearl string at mid height, piped top edge
    revolve(X.mesh(w2), [(r2, z1), (r2, z2)], n=60, u_tiles=10, vlen=96)
    annulus(X.mesh(w2), cx, cy, r3 - 8, r2, z2, 0, 360, n=60)
    bead_ring(X.mesh(SM('pearl', 70, tag='ckp')), cx, cy, r2 + 4, (z1 + z2) / 2, 6)
    bead_ring(X.mesh(SM('bc_pink', 60, tag='ckp')), cx, cy, r2 - 4, z2 + 2, 8)
    # tier 3: lilac, sugar roses round its foot, white piping on top
    revolve(X.mesh(w3), [(r3, z2), (r3, z3)], n=48, u_tiles=8, vlen=128)
    disc(X.mesh(w3), r3, z3, up=True, n=48)
    bead_ring(X.mesh(pip), cx, cy, r3 - 5, z3 + 2, 9)
    rs, lf = SM('bc_pink', 70, tag='ckr'), SM('leaf', 60, tag='ckr')
    for k in range(14):
        a = 2 * math.pi * k / 14
        p = np.array([math.cos(a) * (r3 + 24), math.sin(a) * (r3 + 24), z2])
        sugar_rose(X.mesh(rs), p, 20, rot_z(a))
        for s in (-1, 1):
            q = p + np.array([math.cos(a + s * 0.22), math.sin(a + s * 0.22), 0]) * 8
            ellipsoid(X.mesh(lf), q + [0, 0, 3], 16, 6, 3, nu=6, nv=4, R=rot_z(a + s * 0.9))
    # chocolate plaque on top (north half) + strawberries
    zt = z3
    pl = SM('plaque', 40, tag='ck')
    boxm(X.mesh(SM('choc', 40, tag='ck')), (-122, 58, zt), (122, 78, zt + 152), r=3, tile=64)
    picture(X.mesh(pl), (0, 57.4, zt + 76), 236, 144, (0, -1, 0))
    picture(X.mesh(pl), (0, 78.6, zt + 76), 236, 144, (0, 1, 0))
    sb = SM('strawberry', 60, tag='ck')
    for (dx, dy) in ((-120, -40), (130, -10), (0, 130)):
        revolve(X.mesh(sb), [(0, zt), (22, zt + 6), (34, zt + 30), (30, zt + 56), (14, zt + 72), (0, zt + 76)], n=14, u_tiles=2, vlen=64, cx=dx, cy=dy)
        for k in range(5):
            a = 2 * math.pi * k / 5
            ellipsoid(X.mesh(lf), (dx + math.cos(a) * 12, dy + math.sin(a) * 12, zt + 74), 14, 5, 3, nu=6, nv=4, R=rot_z(a))
    # sugar-cube stair (white sparkling cubes, the edges softened)
    sg = SM('sugar', 30, tag='cks')
    for b in SH.cake():
        if getattr(b, 'part', '') != 'cake_stair': continue
        mn, mx = b.bounds()
        mn = mn - [L.CAKE[0], L.CAKE[1], 0]; mx = mx - [L.CAKE[0], L.CAKE[1], 0]
        boxm(X.mesh(sg), tuple(mn), tuple(mx), r=2, tile=64)
    return place_save('cake', X, *L.CAKE, local=True)


def slice_model():
    """the slice cut out of tier 1, standing on the floor beside the cake (tip toward -x)"""
    X = Model()
    r1, _, z1 = L.TIERS[0]
    h = math.radians(22.5)
    w1, lay, ch = SM('bc_white', 50, tag='ck'), SM('layers', 40, tag='ck'), SM('bc_choc', 60, tag='ckd')
    # the slice's apex at the origin, arc toward +x
    revolve(X.mesh(w1), [(r1, 0), (r1, z1)], n=10, a0=-22.5, a1=22.5, u_tiles=2, vlen=256)
    annulus(X.mesh(w1), 0, 0, 0, r1, z1, -22.5, 22.5, n=10)
    for s in (-1, 1):
        rad = np.array([math.cos(s * h), math.sin(s * h), 0])
        nn = np.array([-math.sin(s * h), math.cos(s * h), 0]) * s
        X.mesh(lay).poly([np.zeros(3), rad * r1, rad * r1 + [0, 0, z1], np.array([0, 0, z1])], nn, [(0, 1), (r1 / 224, 1), (r1 / 224, 0), (0, 0)])
    revolve(X.mesh(ch), [(r1 + 3, z1 - 14), (r1 + 4, z1 - 2), (r1 - 6, z1 + 3), (r1 - 24, z1 + 3)], n=10, a0=-22.5, a1=22.5, u_tiles=2)
    rng = np.random.default_rng(5)
    for k in range(8):
        a = math.radians(-20 + 40 * (k + 0.5) / 8)
        Ld = rng.uniform(26, 80)
        ellipsoid(X.mesh(ch), (math.cos(a) * (r1 + 1), math.sin(a) * (r1 + 1), z1 - 10 - Ld * 0.45), 9, 9, Ld * 0.55, nu=8, nv=6)
    X.shift((r1 * 0.55, 0, 0))
    return save('slice', X)


# ================================================================================================= floor mixer
def mixer():
    X = Model()
    cx, cy = L.MIX
    en, ch = SM('enamel', 40, tag='mx'), SC('steel', 0.28, tag='mxc')
    x0, y0, x1, y1 = L.MIX_COL
    boxm(X.mesh(SM('steel_d', tag='mx')), (x0 - 30, y0 - 20, 0), (x1 + 30, y1 + 10, 40), r=6, tile=128)
    boxm(X.mesh(en), (x0, y0, 40), (x1, y1, L.MIX_HEAD[4] + 2), r=14, tile=256)
    hx0, hy0, hx1, hy1, hz0, hz1 = L.MIX_HEAD
    boxm(X.mesh(en), (hx0, hy0, hz0), (hx1, hy1, hz1), r=30, tile=256)
    # gearbox hub over the bowl and a chrome guard ring
    cylm(X.mesh(ch), (cx, cy, hz0 - 40), 44, 42, n=24)
    torus(X.mesh(ch), (cx, cy, hz0 - 44), 60, 5, n=32, m=6)
    # bowl: outer + inner skins, rolled rim, batter
    bo = SC('steel', 0.3, tag='mxb')
    b0, b1, t = L.BOWL_R0, L.BOWL_R1, L.BOWL_T
    revolve(X.mesh(bo), [(0, L.BOWL_Z0 - 16), (b0 + t, L.BOWL_Z0 - 16), (b1 + t, L.BOWL_Z1)], n=48, cx=cx, cy=cy, u_tiles=6)
    revolve(X.mesh(bo), [(b1, L.BOWL_Z1), (b0, L.BOWL_Z0), (0, L.BOWL_Z0)], n=48, cx=cx, cy=cy, u_tiles=6, inward=True)
    torus(X.mesh(bo), (cx, cy, L.BOWL_Z1), b1 + t / 2, t / 2 + 2, n=48, m=8)
    revolve(X.mesh(SM('batter', 70, tag='mx')), [(b0 + 4, L.BOWL_Z0 + 2), (b0 * 0.6, L.BOWL_Z0 + 10), (0, L.BOWL_Z0 + 12)], n=32, cx=cx, cy=cy,
            u_tiles=4, inward=True)
    # cradle arms + yoke, bowl clamps
    for s in (-1, 1):
        xa = cx + s * 214
        boxm(X.mesh(ch), (min(xa, xa + s * 24), cy - 60, 470), (max(xa, xa + s * 24), y0 - 24, 506), r=4, tile=64)
        cylm(X.mesh(ch), (xa + s * 12, cy - 40, 440), 14, 40, n=12)
    boxm(X.mesh(ch), (cx - 238, y0 - 24, 470), (cx + 238, y0, 506), r=4, tile=64)
    # controls on the column's east side + the name plate
    picture(X.mesh(SM('plate_mx', tag='mx')), (x1 + 0.6, (y0 + y1) / 2, 760), 220, 60, (1, 0, 0))
    for k, (dy, col) in enumerate(((-60, 'glow_y'), (0, 'red'), (60, 'black'))):
        m = Mesh(); cylm(m, (0, 0, 0), 16, 10, n=12)
        X.mesh(S(col, 'glow' if col.startswith('glow') else 'lm', tag='mxk')).add(m, rot_axis((0, 1, 0), math.pi / 2), (x1, (y0 + y1) / 2 + dy, 660))
    m = Mesh(); cylm(m, (0, 0, 0), 30, 12, n=16)
    X.mesh(ch).add(m, rot_axis((0, 1, 0), math.pi / 2), (x1, (y0 + y1) / 2, 560))
    return place_save('mixer', X, cx, cy)


def paddle():
    """flat beater for the mixer's func_rotating (origin = rotation centre at z L.BOWL_Z1)"""
    X = Model()
    ch = S('steel', 'dyn', tag='pd')
    zc = L.BOWL_Z1
    top = L.MIX_HEAD[4] - 40 - zc
    tube(X.mesh(ch), [(0, 0, top), (0, 0, 120)], 9, nseg=10)
    # paddle loop: two curved arms from the shaft hub down to the foot
    for s in (-1, 1):
        pts = []
        for t in np.linspace(0, 1, 9):
            pts.append((s * (40 + 70 * math.sin(t * math.pi) * (1 - 0.3 * t)), 0, 120 - t * (120 + L.BOWL_Z1 - L.BOWL_Z0 - 46)))
        tube(X.mesh(ch), pts, 8, nseg=8)
    tube(X.mesh(ch), [(-40, 0, 120), (40, 0, 120)], 8, nseg=8)
    tube(X.mesh(ch), [(-40, 0, -(L.BOWL_Z1 - L.BOWL_Z0 - 46)), (40, 0, -(L.BOWL_Z1 - L.BOWL_Z0 - 46))], 8, nseg=8)
    tube(X.mesh(ch), [(0, 0, 120), (0, 0, -(L.BOWL_Z1 - L.BOWL_Z0 - 46))], 6, nseg=8)
    batter = S('batter', 'dyn', tag='pd')
    for k in range(6):
        ellipsoid(X.mesh(batter), (((k % 3) - 1) * 50, 0, -60 - (k // 3) * 80), 14, 9, 12, nu=8, nv=5)
    return save('paddle', X)


# ================================================================================================= display cabinet
def display_cabinet():
    X = Model()
    x0, y0, x1, y1 = L.DC
    pk, mb, gl, wd = SM('cab_pink', 30, tag='dc'), SM('marble', 30, tag='dc'), S('glass_g', 'glass', tag='dc'), SM('wood', 30, tag='dc')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if part in ('dc_glass', 'dc_shelf'): return gl, planar_uv(n, 128)
        if part == 'dc_top': return mb, planar_uv(n, 256)
        if part == 'dc_step': return wd, planar_uv(n, 128)
        return (mb if n[2] > 0.9 else pk), planar_uv(n, 256)
    solids_parts(X, SH.display_cabinet(), fn)
    ch = SC('steel', 0.3, tag='dch')
    zt = L.DC_TOP - 32
    for (a, b) in (((x0, y0, L.DC_PLINTH), (x0, y0, zt)), ((x1, y0, L.DC_PLINTH), (x1, y0, zt)), ((x0, y1, L.DC_PLINTH), (x0, y1, zt)),
                   ((x1, y1, L.DC_PLINTH), (x1, y1, zt)), ((x0, y0, L.DC_PLINTH), (x1, y0, L.DC_PLINTH))):
        tube(X.mesh(ch), [a, b], 5, nseg=8)
    # warm light strip under the counter top
    quad_uv(X.mesh(S('glow_w', 'glow', tag='dc')), (x0 + 30, y0 + 30, zt - 1), (x1 - 30, y0 + 30, zt - 1), (x1 - 30, y0 + 50, zt - 1),
            (x0 + 30, y0 + 50, zt - 1), [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, -1))
    # the bakery sign on the customer side of the plinth
    picture(X.mesh(SB('sign_bakery', tag='dc')), ((x0 + x1) / 2, y0 - 0.6, L.DC_PLINTH / 2 + 4), 560, 112, (0, -1, 0))
    return place_save('display', X, (x0 + x1) / 2, (y0 + y1) / 2)


# ================================================================================================= cool room
def cool_room():
    X = Model()
    x0, y0, x1, y1 = L.CR
    t = L.CR_T
    st, wh, sd = SC('coolpanel', 0.1, tag='cr'), SM('coolpanel', 30, tag='cri'), SM('steel_d', tag='cr')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if (c[0] > L.HX - 0.5 and n[0] > 0.9) or (c[1] < -L.HY + 0.5 and n[1] < -0.9): return None
        if part == 'cr_roof':
            if n[2] > 0.9: return sd, planar_uv(n, 256)
            return (wh if n[2] < -0.9 else st), planar_uv(n, 256)
        if part in ('cr_shelf', 'cr_post'): return SC('steel', 0.3, tag='crs'), planar_uv(n, 64)
        if part == 'cr_door': return st, planar_uv(n, 128)
        q = c + n * 3
        inside = x0 + t < q[0] < x1 - t and y0 + t < q[1] < y1 - t
        return (wh if inside else st), planar_uv(n, 256)
    solids_parts(X, SH.cool_room(), fn)
    dx, dhw, dh = L.CR_DOOR
    # strip curtain in the doorway (alpha, nonsolid), the door rail, the sign
    cu = S('curtain', 'glass', c='0.10 0.13 0.15', tag='crc')
    for k in range(8):
        xa = dx - dhw + k * 2 * dhw / 8 + 2
        quad_uv(X.mesh(cu), (xa, y1 - t / 2, 6), (xa + 2 * dhw / 8 - 3, y1 - t / 2, 6), (xa + 2 * dhw / 8 - 3, y1 - t / 2, dh),
                (xa, y1 - t / 2, dh), [(0, 1), (1, 1), (1, 0), (0, 0)], (0, 1, 0))
    tube(X.mesh(SC('steel', 0.3, tag='crs')), [(dx - dhw - 20, y1 + 10, dh + 30), (dx + 3 * dhw + 40, y1 + 10, dh + 30)], 5, nseg=8)
    picture(X.mesh(SB('sign_cool', tag='cr')), (dx - dhw - 170, y1 + 0.6, 260), 200, 76, (0, 1, 0))
    tube(X.mesh(SC('steel', 0.3, tag='crs')), [(dx + dhw + 40, y1 + 14, 140), (dx + dhw + 40, y1 + 20, 150), (dx + dhw + 40, y1 + 20, 230), (dx + dhw + 40, y1 + 14, 240)], 4, nseg=8)
    return place_save('coolroom', X, (x0 + x1) / 2, (y0 + y1) / 2)


# ================================================================================================= cooling racks
def rack():
    X = Model()
    w, d = L.RACK_W, L.RACK_D
    ch, tn = SC('steel', 0.3, tag='rk'), SC('tin', 0.15, tag='rkt')
    for (px, py) in ((-w / 2, -d / 2), (w / 2 - 16, -d / 2), (-w / 2, d / 2 - 16), (w / 2 - 16, d / 2 - 16)):
        tube(X.mesh(ch), [(px + 8, py + 8, 12), (px + 8, py + 8, L.RACK_TOP)], 8, nseg=8)
        m = Mesh(); cylm(m, (0, 0, -3), 10, 6, n=12)
        X.mesh(SM('rubber_b', tag='rk')).add(m, rot_axis((1, 0, 0), math.pi / 2), (px + 8, py + 8, 10))
    for zl in L.RACK_TRAYS + [L.RACK_TOP]:
        boxm(X.mesh(tn), (-w / 2, -d / 2, zl - 8), (w / 2, d / 2, zl), r=1, tile=128)
        for s in (-1, 1):
            boxm(X.mesh(tn), (-w / 2, s * d / 2 - (6 if s > 0 else 0), zl), (w / 2, s * d / 2 + (0 if s > 0 else 6), zl + 6), r=1, tile=64)
    return save('rack', X)


# ================================================================================================= flour bin
def flour_bin():
    X = Model()
    x0, y0, x1, y1 = L.BIN
    wd, wdd = SM('wood', 30, tag='bn'), SM('wood_d', 30, tag='bn')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if part == 'bin_floor': return None
        if part == 'bin_stair': return wd, planar_uv(n, 128)
        q = c + n * 3
        inside = x0 + L.BIN_T < q[0] < x1 - L.BIN_T and y0 + L.BIN_T < q[1] < y1 - L.BIN_T
        return (wdd if inside else wd), planar_uv(n, 128)
    solids_parts(X, SH.flour_bin(), fn)
    # iron bands round the bin
    for zz in (30, L.BIN_H - 30):
        for (a, b) in (((x0 - 2, y0 - 2), (x1 + 2, y0 - 2)), ((x1 + 2, y0 - 2), (x1 + 2, y1 + 2)), ((x1 + 2, y1 + 2), (x0 - 2, y1 + 2)),
                       ((x0 - 2, y1 + 2), (x0 - 2, y0 - 2))):
            tube(X.mesh(SM('black', tag='bn')), [(a[0], a[1], zz), (b[0], b[1], zz)], 3, nseg=6)
    # the flour heap inside (soft mound, nonsolid; the secret trigger sits in it)
    fl = SM('flour', 70, tag='bn')
    ix0, iy0, ix1, iy1 = x0 + L.BIN_T, y0 + L.BIN_T, x1 - L.BIN_T, y1 - L.BIN_T
    nx, ny = 18, 16
    P = np.zeros((ny + 1, nx + 1, 3)); UV = np.zeros((ny + 1, nx + 1, 2))
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = ix0 + (ix1 - ix0) * u, iy0 + (iy1 - iy0) * v
            e = min(u, 1 - u, v, 1 - v)
            z = L.BIN_FLOOR + 50 + 54 * math.sin(math.pi * u) * math.sin(math.pi * v) + 6 * math.sin(u * 17) * math.cos(v * 13)
            if e == 0: z = L.BIN_FLOOR + 60
            P[j, i] = (x, y, z); UV[j, i] = (x / 128, -y / 128)
    N = grid_normals(P)
    if N[ny // 2, nx // 2, 2] < 0: N = -N
    X.mesh(fl).grid(P, N, UV)
    picture(X.mesh(SM('sign_flour', tag='bn')), (x1 + 0.6, (y0 + y1) / 2, L.BIN_H / 2), 300, 100, (1, 0, 0))
    # a scoop stuck in the flour
    sc = SC('steel', 0.3, tag='bnc')
    tube(X.mesh(sc), [((x0 + x1) / 2 + 60, (y0 + y1) / 2, 150), ((x0 + x1) / 2 + 100, (y0 + y1) / 2 + 20, 230)], 6, nseg=8)
    ellipsoid(X.mesh(sc), ((x0 + x1) / 2 + 52, (y0 + y1) / 2 - 4, 140), 26, 20, 14, nu=10, nv=6)
    return place_save('flourbin', X, (x0 + x1) / 2, (y0 + y1) / 2)


def wall_deco():
    """framed posters on the kitchen walls and an OPEN neon in the shop window (one model, world coordinates)"""
    X = Model()
    for (img_, c, nrm) in (('poster_a', (L.HX - 0.6, -400, 1450), (-1, 0, 0)), ('poster_b', (L.HX - 0.6, 800, 1450), (-1, 0, 0)),
                           ('poster_c', (-L.HX + 0.6, 1300, 1450), (1, 0, 0)), ('poster_a', (-L.HX + 0.6, -1400, 1450), (1, 0, 0))):
        picture(X.mesh(SM(img_, 40, tag='pst')), c, 256, 320, nrm)
    nx = (L.WINDOWS[1][0] + L.WINDOWS[1][1]) / 2
    picture(X.mesh(S('neon_open', 'glow', wave='sin 0.9 0.1 0 0.5', tag='neon')), (nx, -L.HY + 30, 900), 300, 110, (0, 1, 0))
    tube(X.mesh(SM('black', tag='neon')), [(nx - 120, -L.HY + 32, 960), (nx - 120, -L.HY + 32, L.WINDOWS[1][3])], 1.5, nseg=4)
    tube(X.mesh(SM('black', tag='neon')), [(nx + 120, -L.HY + 32, 960), (nx + 120, -L.HY + 32, L.WINDOWS[1][3])], 1.5, nseg=4)
    return save('walldeco', X)


def make_plates():
    """name plates and labels drawn as model textures"""
    T('plate_ov', tex_label(512, 64, 'PADMAN OVENS  -  DECK 3000', (40, 40, 44), (236, 200, 120)))
    T('plate_mx', tex_label(512, 128, 'PADMIX 60', (40, 44, 42), (236, 236, 230), 'PLANETARY MIXER'))
    T('neon_open', tex_label(512, 192, 'OPEN', (20, 10, 16), (255, 90, 170)))
    T('sign_flour', tex_label(512, 160, 'FLOUR', (232, 216, 180), (90, 50, 30), "BAKER'S OWN - DO NOT CLIMB IN"))


def make():
    make_textures(); make_plates()
    oven(); flue(); counters(); cake(); slice_model(); mixer(); paddle(); display_cabinet(); cool_room(); rack(); flour_bin(); wall_deco()
