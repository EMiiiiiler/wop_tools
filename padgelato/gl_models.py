"""Custom MD3 architecture for wop_padgelato (Padman's Gelato Parlour): the giant triple-scoop cone, the gelato counter
with its tubs, the soft-serve machine (+ its turning swirls), the milkshake bar, the giant milkshake glass, the walk-in
freezer with the Mystery Flavour tub, the chest freezer, the ice cream cart and the topping jars. All geometry and art
is original and generated here.

Architecture is drawn from the convex solids in gl_shapes.py (or covers them closely), so the weapclip collision in
build_gelato.py matches the visible surfaces."""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from gl_mesh import *
import layout as L
import gl_shapes as SH

CENTRES = {}
TUB_FLAVOURS = ['fl_straw', 'fl_choc', 'fl_mint', 'fl_pist', 'fl_lemon', 'fl_blue', 'fl_cookie', 'fl_bubble']
TUB_NAMES = ['STRAWBERRY', 'DOUBLE CHOC', 'MINT CHIP', 'PISTACHIO', 'LEMON', 'BLUEBERRY', 'COOKIES', 'BUBBLEGUM']


def SB(img, shade=30, **kw): return S(BT(img), 'lm', shade=shade, **kw)
def SM(img, shade=60, **kw): return S(img, 'lm', shade=shade, **kw)
def SC(img='steel', v=0.22, **kw): return S(img, 'lms', v=v, shade=kw.pop('shade', 40), **kw)


def place_save(name, X, cx, cy, local=False):
    if not local: X.shift((cx, cy, 0))
    CENTRES[name] = (cx, cy)
    return save(name, X)


def scoop_bump(seed, amp=0.06):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 4)
    return lambda p, t: 1 + amp * math.sin(5 * t + ph[0]) * math.cos(3 * p + ph[1]) + amp * 0.6 * math.sin(9 * t + ph[2]) * (p > -0.3)


def drips(M, c, r, z, n, seed, lmin=20, lmax=70, w=10):
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / n
        Ld = rng.uniform(lmin, lmax)
        ellipsoid(M, (c[0] + r * math.cos(a), c[1] + r * math.sin(a), z - Ld * 0.45), w, w, Ld * 0.55, nu=8, nv=6)


# ================================================================================================= the giant cone
def tower():
    X = Model()
    sr0, sr1, sh = L.STAND
    ch = SC('steel', 0.32, tag='tw')
    revolve(X.mesh(ch), [(sr0 + 6, 0), (sr0 + 8, 8), (sr1 + 6, sh - 10), (sr1 + 18, sh - 4), (sr1 + 14, sh), (L.CONE_R0, sh)], n=48, u_tiles=8)
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(X.mesh(ch), [((sr0 + 8) * math.cos(a), (sr0 + 8) * math.sin(a), 6), ((sr1 + 8) * math.cos(a), (sr1 + 8) * math.sin(a), sh - 8)], 6, nseg=6)
    # waffle cone (a little outside the 24-gon collision), paper sleeve round the bottom
    wf = SM('waffle', 50, tag='tw')
    zz = np.linspace(L.CONE_Z0, L.CONE_Z1, 12)
    revolve(X.mesh(wf), [(L.cone_r(z) + 8, z) for z in zz], n=48, u_tiles=10, vlen=160)
    sl = SM('sleeve', 50, tag='tw')
    revolve(X.mesh(sl), [(L.cone_r(z) + 12, z) for z in np.linspace(L.CONE_Z0 + 20, 420, 6)], n=48, u_tiles=3, vlen=400)
    # wafer rim: a rolled edge round the deck, melted vanilla on the deck, drips down the cone
    torus(X.mesh(SM('waffle', 50, tag='twr')), (0, 0, L.RIM_Z - 20), L.RIM_R - 18, 20, n=64, m=10, utile=128)
    va = SM('fl_vanilla', 60, tag='tw')
    annulus(X.mesh(va), 0, 0, L.SCOOP_R - 20, L.RIM_R - 30, L.RIM_Z, 0, 360, n=64)
    drips(X.mesh(va), (0, 0), L.RIM_R - 4, L.RIM_Z - 30, 26, 3, 30, 110, 12)
    # the scoops: vanilla (big, on the deck), strawberry, mint; chocolate sauce, a cherry, a wafer stick, sprinkles
    ellipsoid(X.mesh(SM('fl_vanilla', 60, tag='tws')), (0, 0, L.RIM_Z), L.SCOOP_R, L.SCOOP_R, L.SCOOP_H, nu=40, nv=16,
              bump=scoop_bump(1), flat_bottom=0, u1=8, v1=4)
    sphere(X.mesh(SM('fl_straw', 60, tag='tws')), (0, 0, 1440), 212, nu=32, nv=14, bump=scoop_bump(2), u1=6, v1=3)
    drips(X.mesh(SM('fl_straw', 60, tag='tws')), (0, 0), 196, 1340, 14, 4, 30, 80, 14)
    sphere(X.mesh(SM('fl_mint', 60, tag='tws')), (0, 0, 1730), 152, nu=28, nv=12, bump=scoop_bump(3), u1=4, v1=2)
    cs = SM('choc_sauce', 60, tag='tws')
    ellipsoid(X.mesh(cs), (0, 0, 1805), 128, 128, 84, nu=24, nv=10, flat_bottom=20)
    drips(X.mesh(cs), (0, 0), 132, 1800, 12, 5, 30, 90, 10)
    sphere(X.mesh(SM('cherry', 70, tag='tws')), (0, 0, 1925), 46, nu=16, nv=10)
    tube(X.mesh(SM('leaf', tag='tws')), [(0, 0, 1965), (10, 6, 1990), (30, 12, 2010)], 3, nseg=6)
    m = Mesh(); rbox(m, (-24, -8, -170), (24, 8, 170), r=4, k=1, tile=64)
    X.mesh(SM('wafer', 50, tag='tws')).add(m, rot_axis((0, 1, 0), 0.5) @ rot_axis((1, 0, 0), 0.2), (120, -40, 1640))
    rng = np.random.default_rng(9)
    spr = [SM(c, 70, tag='twsp') for c in ('red', 'enamel_teal', 'fl_lemon', 'white', 'fl_blue')]
    for k in range(70):
        th = rng.uniform(0, 2 * math.pi); ph = rng.uniform(0.15, 1.2)
        r0 = 152
        p = np.array([r0 * math.cos(ph) * math.cos(th), r0 * math.cos(ph) * math.sin(th), 1730 + r0 * math.sin(ph)])
        d = rot_z(rng.uniform(0, 6.28)) @ np.array([8, 0, 0])
        tube(X.mesh(spr[k % 5]), [p - d, p + d], 2.5, nseg=4)
    return place_save('tower', X, *L.TOWER, local=True)


# ================================================================================================= gelato counter
def tex_tag(name, col):
    a = text_img(name, 256, 64, (252, 244, 226), (60, 40, 40), False)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    d.ellipse((6, 18, 34, 46), fill=tuple(int(v) for v in col)); d.rectangle((2, 2, 253, 61), outline=(214, 36, 56), width=3)
    return np.asarray(im, np.float32)


def gelato_counter():
    X = Model()
    x0, y0, x1, y1 = L.GC
    st, te, gl, wd = SC('steel', 0.18, tag='gc'), SM('enamel_teal', 40, tag='gc'), S('glass_g', 'glass', tag='gc'), SM('wafer', 40, tag='gcs')
    flav = {k: SM(f, 60, tag='gct' + str(k)) for k, f in enumerate(TUB_FLAVOURS)}
    bars = {}

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[1] > L.HY - 0.5 and n[1] > 0.9: return None
        if part == 'gc_glass': return gl, planar_uv(n, 128)
        if part in ('gc_end', 'gc_back', 'gc_plinth'): return (te if abs(n[2]) < 0.5 else st), planar_uv(n, 256)
        if part == 'gc_deck': return st, planar_uv(n, 128)
        if part == 'gc_tub':
            return st, planar_uv(n, 128)
        if part == 'gc_stair': return wd, planar_uv(n, 128)
        if part == 'shelf': return SM('wood', 40, tag='gc'), planar_uv(n, 256)
        return st, planar_uv(n, 128)
    blist = SH.gelato_counter()
    solids_parts(X, blist, fn)
    # ice cream in the tubs: a mounded, scooped surface (flavour), slightly above the pan rim line, with a scoop in it
    for k, (xa, xb) in enumerate(L.GC_TUBS):
        ya, yb = L.GC_TUB_Y
        nx, ny = 10, 8
        P = np.zeros((ny + 1, nx + 1, 3)); UV = np.zeros((ny + 1, nx + 1, 2))
        for j in range(ny + 1):
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                x, y = xa + (xb - xa) * u, ya + (yb - ya) * v
                bump = 6 * math.sin(math.pi * u) * math.sin(math.pi * v) + 3 * math.sin(u * 11 + k) * math.cos(v * 9)
                P[j, i] = (x, y, L.GC_TUB + 0.5 + max(0, bump)); UV[j, i] = (x / 160, -y / 160)
        N = grid_normals(P)
        if N[ny // 2, nx // 2, 2] < 0: N = -N
        X.mesh(flav[k]).grid(P, N, UV)
        sc = SC('steel', 0.3, tag='gcsc')
        hx = xa + 60 + (k % 3) * 40
        tube(X.mesh(sc), [(hx, ya + 60, L.GC_TUB + 6), (hx + 10, ya + 120, L.GC_TUB + 60), (hx + 20, yb + 10, L.GC_TUB + 110)], 4, nseg=6)
        ellipsoid(X.mesh(sc), (hx - 2, ya + 52, L.GC_TUB + 10), 18, 18, 10, nu=10, nv=5)
        # the flavour tag on the glass front
        nm = f'tag_{k}'
        if nm not in bars:
            T(nm, tex_tag(TUB_NAMES[k], FLAVOURS[TUB_FLAVOURS[k]][0])); bars[nm] = 1
        picture(X.mesh(SM(nm, 40, tag='gctag')), ((xa + xb) / 2, y0 - 0.8, 300), 200, 50, (0, -1, 0))
    # chrome rail along the front top edge and along the plinth, frosty light strip inside
    tube(X.mesh(SC('steel', 0.35, tag='gch')), [(x0 + 10, y0 - 3, L.GC_DECK - 4), (x1 - 10, y0 - 3, L.GC_DECK - 4)], 4, nseg=8)
    tube(X.mesh(SC('steel', 0.35, tag='gch')), [(x0 + 10, y0 - 3, L.GC_PLINTH), (x1 - 10, y0 - 3, L.GC_PLINTH)], 4, nseg=8)
    quad_uv(X.mesh(S('glow_w', 'glow', tag='gcg')), (x0 + 40, y1 - 18, L.GC_TUB - 1), (x1 - 40, y1 - 18, L.GC_TUB - 1), (x1 - 40, y1 - 40, L.GC_TUB - 1),
            (x0 + 40, y1 - 40, L.GC_TUB - 1), [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, -1))
    # aisle stock on the shelves is placed as props; the wall shelf brackets
    hx0, hx1, hy, hz = L.SHELF
    for xx in np.linspace(hx0 + 80, hx1 - 80, 6):
        P = [np.array(p, float) for p in ((xx, L.HY, hz - L.SHELF_T), (xx, hy + 20, hz - L.SHELF_T), (xx, L.HY, hz - 150))]
        for s in (-1, 1):
            Q = [p + np.array([s * 6, 0, 0]) for p in P]
            X.mesh(SM('wood_d', 40, tag='gc')).poly(Q if s > 0 else Q[::-1], (s, 0, 0), [(q[1] / 64, -q[2] / 64) for q in (Q if s > 0 else Q[::-1])])
    return place_save('counter', X, 0, (y0 + L.HY) / 2)


# ================================================================================================= soft-serve machine
def softserve():
    X = Model()
    x0, y0, x1, y1 = L.SS
    t = L.SS_T
    rd, cr, st = SM('enamel_red', 40, tag='ss'), SM('enamel_cream', 40, tag='ss'), SC('steel', 0.25, tag='ss')

    def fn(part, c, n, poly):
        if part in ('ss_cone', 'ss_cup'): return None
        if n[2] < -0.9 and c[2] < 1: return None
        if c[0] < x0 + 0.5 and n[0] < -0.9: return None
        q = c + n * 3
        inside = x0 + t < q[0] < x1 - t + 1 and y0 + t < q[1] < y1 - t and q[2] < L.SS_CAB
        if inside: return SM('steel_d', tag='ss'), planar_uv(n, 128)
        if part == 'ss_deck': return st, planar_uv(n, 128)
        if part == 'ss_body': return (rd if n[0] > 0.9 else cr), planar_uv(n, 256)
        if part == 'ss_nozzle': return st, planar_uv(n, 64)
        if part == 'ss_stair': return st, planar_uv(n, 128)
        return cr, planar_uv(n, 256)
    solids_parts(X, SH.softserve(), fn)
    bx = L.SS_BODY_X
    # nozzle spouts, pull handles, a display, the SOFT SERVE badge, hopper lids on top, drip grate on the deck
    for y in L.SS_NOZZLES:
        revolve(X.mesh(st), [(0, 700), (34, 700), (26, 660), (12, 640), (0, 640)], n=16, cx=bx + 50, cy=y)
        tube(X.mesh(SM('black', tag='ss')), [(bx + 2, y, 860), (bx + 60, y, 880), (bx + 90, y, 960)], 9, nseg=8)
        sphere(X.mesh(SM('red', 70, tag='ss')), (bx + 92, y, 970), 18, nu=10, nv=6)
    picture(X.mesh(S('screen', 'glow', tag='ss')), (bx + 0.6, 180 + L.SS_DY, 1000), 140, 60, (1, 0, 0))
    picture(X.mesh(SM('badge_ss', 40, tag='ss')), (bx + 0.6, -40 + L.SS_DY, 1080), 360, 110, (1, 0, 0))
    for y in (-300 + L.SS_DY, L.SS_DY, 300 + L.SS_DY):
        cylm(X.mesh(st), (-2100, y, L.SS_TOP), 120, 10, n=24)
        sphere(X.mesh(SM('black', tag='ss')), (-2100, y, L.SS_TOP + 18), 12, nu=8, nv=5)
    for yy in np.linspace(y0 + 40, y1 - 40, 20):
        quad_uv(X.mesh(SM('steel_d', tag='ssg')), (bx + 10, yy - 4, L.SS_DECK + 0.6), (L.SS_LEDGE - 10, yy - 4, L.SS_DECK + 0.6),
                (L.SS_LEDGE - 10, yy + 4, L.SS_DECK + 0.6), (bx + 10, yy + 4, L.SS_DECK + 0.6), [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, 1))
    # the two big cones in chrome holders on the deck, and the cup in the middle
    for y in (L.SS_NOZZLES[0], L.SS_NOZZLES[2]):
        revolve(X.mesh(st), [(0, L.SS_DECK), (100, L.SS_DECK), (100, L.SS_DECK + 90), (92, L.SS_DECK + 96), (0, L.SS_DECK + 96)], n=24, cx=-1790, cy=y)
        revolve(X.mesh(SM('waffle', 50, tag='ssc')), [(30, L.SS_DECK + 96), (100, L.SS_DECK + 260)], n=24, cx=-1790, cy=y, u_tiles=4)
        torus(X.mesh(SM('waffle', 50, tag='ssc')), (-1790, y, L.SS_DECK + 262), 96, 8, n=24, m=6)
        ellipsoid(X.mesh(SM('cream', 60, tag='ssc')), (-1790, y, L.SS_DECK + 262), 92, 92, 30, nu=20, nv=6, flat_bottom=0)
    revolve(X.mesh(SM('sleeve', 50, tag='ssc')), [(0, L.SS_DECK), (60, L.SS_DECK), (80, L.SS_DECK + 150), (0, L.SS_DECK + 150)], n=20, cx=-1790, cy=L.SS_DY, u_tiles=1, vlen=150)
    swirl_static(X, (-1790, L.SS_DY, L.SS_DECK + 150), 70, 130)
    return place_save('softserve', X, (x0 + x1) / 2, L.SS_DY)


def swirl_static(X, c, r, h, sh=None):
    sh = sh or SM('cream', 60, tag='sw')
    c = np.asarray(c, float)
    pts, rad = [], []
    for k in range(61):
        t = k / 60; a = 2 * math.pi * 3 * t; rr = r * (1 - t) ** 0.8
        pts.append(c + [rr * math.cos(a), rr * math.sin(a), h * t * 0.8]); rad.append(r * 0.36 * (1 - 0.7 * t))
    tube(X.mesh(sh), pts, rad, nseg=10)


def swirl_mover(name, flavour='cream', r=80.0, h=130.0, drop=110.0):
    """a soft-serve swirl piling up in a cone, with the ribbon coming down from the nozzle (func_rotating model2;
    origin at the cone top)"""
    X = Model()
    sh = S(flavour, 'dyn', tag='swm' + flavour)
    swirl_static(X, (0, 0, 0), r, h, sh)
    pts = [(0, 0, h * 0.8 + drop), (8, 0, h * 0.8 + drop * 0.5), (0, 6, h * 0.8)]
    tube(X.mesh(sh), pts, [16, 15, 14], nseg=8)
    return save(name, X)


# ================================================================================================= milkshake bar + glass
def bar():
    X = Model()
    x0, y0, x1, y1 = L.BAR
    te, mb = SM('enamel_teal', 40, tag='br'), SM('marble', 40, tag='br')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if c[0] > L.HX - 0.5 and n[0] > 0.9: return None
        if part == 'bar_top': return (SM('enamel_red', 40, tag='brt') if n[2] > 0.9 else SC('steel', 0.3, tag='br')), planar_uv(n, 256)
        return te, planar_uv(n, 256)
    solids_parts(X, SH.bar(), fn)
    ch = SC('steel', 0.35, tag='brh')
    tube(X.mesh(ch), [(x0 - 30, y0 + 40, 60), (x0 - 30, y1 - 40, 60)], 6, nseg=8)
    for yy in np.linspace(y0 + 40, y1 - 40, 8):
        tube(X.mesh(ch), [(x0 - 30, yy, 60), (x0 + 16, yy, 60)], 4, nseg=6)
    for yy in np.linspace(y0 + 100, y1 - 100, 6):
        boxm(X.mesh(ch), (x0 + 14, yy - 4, 40), (x0 + 18, yy + 4, L.BAR_Z - 40), r=1, tile=32)
    # back-bar wall: mirror panel and two glass shelves with sundae glasses (decor on the wall, high up)
    picture(X.mesh(S('glass_g', 'glass', c='0.18 0.2 0.22', tag='brm')), (L.HX - 0.8, (y0 + y1) / 2, 820), y1 - y0 - 200, 300, (-1, 0, 0))
    for zz in (700, 940):
        boxm(X.mesh(S('glass_g', 'glass', tag='brs')), (L.HX - 70, y0 + 120, zz - 4), (L.HX, y1 - 120, zz), r=1, tile=64)
        for yy in np.linspace(y0 + 180, y1 - 180, 9):
            revolve(X.mesh(S('glass_g', 'glass', tag='brs')), [(0, zz), (22, zz), (6, zz + 6), (5, zz + 36), (34, zz + 60), (40, zz + 100)], n=12, cx=L.HX - 36, cy=yy)
    return place_save('bar', X, (x0 + x1) / 2, (y0 + y1) / 2)


def milkshake():
    X = Model()
    gr = L.GLASS_R
    gl = S('glass_g', 'glass', tag='mg')
    revolve(X.mesh(gl), [(gr + 6, 0), (gr + 6, L.GLASS_H)], n=48)
    revolve(X.mesh(gl), [(gr + 2, L.GLASS_H), (gr - 6, 12)], n=48, inward=True)
    revolve(X.mesh(SM('milk', 60, tag='mg')), [(0, 10), (gr - 2, 10), (gr - 2, L.GLASS_H - 6)], n=48, u_tiles=8, vlen=256)
    torus(X.mesh(S('glass_g', 'glass', tag='mg')), (0, 0, L.GLASS_H), gr + 4, 6, n=48, m=6)
    # whipped cream following the collision terraces, chocolate sprinkles, a cherry, the striped straw
    cr = SM('cream', 60, tag='mgc')
    revolve(X.mesh(cr), [(gr + 16, L.GLASS_H - 6), (gr + 20, L.GLASS_H + 4), (gr + 14, L.GLASS_H + 16), (gr - 26, L.GLASS_H + 18),
                         (gr - 30, L.GLASS_H + 26), (gr - 36, L.GLASS_H + 34), (gr - 86, L.GLASS_H + 36), (gr - 90, L.GLASS_H + 44),
                         (gr - 94, L.GLASS_H + 50), (60, L.GLASS_H + 52), (0, L.GLASS_H + 54)], n=48, u_tiles=6, inward=True)
    for k in range(18):
        a = 2 * math.pi * k / 18
        sphere(X.mesh(cr), ((gr + 6) * math.cos(a), (gr + 6) * math.sin(a), L.GLASS_H + 12), 14, nu=8, nv=5)
    rng = np.random.default_rng(4)
    for k in range(50):
        r = rng.uniform(0, gr - 10); a = rng.uniform(0, 6.28)
        z = L.GLASS_H + (52 if r < 140 else 36 if r < 200 else 18) + 1
        d = rot_z(rng.uniform(0, 6.28)) @ np.array([6, 0, 0])
        p = np.array([r * math.cos(a), r * math.sin(a), z])
        tube(X.mesh(SM('choc_d', tag='mgs')), [p - d, p + d], 2, nseg=4)
    sphere(X.mesh(SM('cherry', 70, tag='mg')), (0, 0, L.GLASS_H + 96), 40, nu=14, nv=8)
    tube(X.mesh(SM('leaf', tag='mg')), [(0, 0, L.GLASS_H + 130), (12, 8, L.GLASS_H + 160)], 3, nseg=6)
    tube(X.mesh(SM('straw', 50, tag='mgst')), [(60, 30, 400), (130, 70, L.GLASS_H + 60), (220, 120, L.GLASS_H + 360)], 16, nseg=12)
    return place_save('milkshake', X, *L.GLASS, local=True)


# ================================================================================================= walk-in freezer
def freezer():
    X = Model()
    x0, y0, x1, y1 = L.FZ
    t = L.FZ_T
    st, wh, sd = SC('coolpanel', 0.1, tag='fz'), SM('coolpanel', 30, tag='fzi'), SM('steel_d', tag='fz')

    def fn(part, c, n, poly):
        if part in ('mys_wall', 'mys_floor'): return None
        if n[2] < -0.9 and c[2] < 1: return None
        if (c[0] > L.HX - 0.5 and n[0] > 0.9) or (c[1] < -L.HY + 0.5 and n[1] < -0.9): return None
        if part == 'fz_roof': return (sd if n[2] > 0.9 else wh if n[2] < -0.9 else st), planar_uv(n, 256)
        if part in ('fz_shelf', 'fz_post'): return SC('steel', 0.3, tag='fzs'), planar_uv(n, 64)
        if part == 'fz_door': return st, planar_uv(n, 128)
        q = c + n * 3
        inside = x0 + t < q[0] < x1 - t and y0 + t < q[1] < y1 - t
        return (wh if inside else st), planar_uv(n, 256)
    solids_parts(X, SH.freezer(), fn)
    dx, dhw, dh = L.FZ_DOOR
    cu = S('curtain', 'glass', c='0.10 0.13 0.15', tag='fzc')
    for k in range(8):
        ya = dx - dhw + k * 2 * dhw / 8 + 2
        quad_uv(X.mesh(cu), (x0 + t / 2, ya, 6), (x0 + t / 2, ya + 2 * dhw / 8 - 3, 6), (x0 + t / 2, ya + 2 * dhw / 8 - 3, dh),
                (x0 + t / 2, ya, dh), [(0, 1), (1, 1), (1, 0), (0, 0)], (-1, 0, 0))
    tube(X.mesh(SC('steel', 0.3, tag='fzs')), [(x0 - 10, dx - dhw - 20, dh + 30), (x0 - 10, dx + 3 * dhw + 40, dh + 30)], 5, nseg=8)
    picture(X.mesh(SB('sign_freezer', tag='fz')), (x0 - 0.6, dx - dhw - 190, 260), 240, 90, (-1, 0, 0))
    # frost along the roof edge and icicles over the door
    fr = SM('frost', 60, tag='fzf')
    rng = np.random.default_rng(7)
    for yy in np.linspace(y0 + 30, y1 - 30, 24):
        if dx - dhw - 10 < yy < dx + dhw + 10:
            ellipsoid(X.mesh(fr), (x0 - 4, yy, dh - 6 - rng.uniform(0, 20)), 6, 6, rng.uniform(14, 34), nu=6, nv=5)
        ellipsoid(X.mesh(fr), (x0 - 2, yy, L.FZ_H - 20), 6, 26, 12, nu=8, nv=4)
    # the Mystery Flavour tub
    mx, my, mr, mh = L.MYSTERY
    revolve(X.mesh(SM('carton_vanilla', 40, tag='mys')), [(mr + 2, 0), (mr + 2, mh)], n=32, cx=mx, cy=my, u_tiles=2, vlen=mh)
    revolve(X.mesh(SM('enamel_cream', 40, tag='mys')), [(mr + 2, mh), (mr - 22, mh), (mr - 22, 8)], n=32, cx=mx, cy=my, inward=True)
    disc(X.mesh(S('fl_mystery', 'glow', wave='sin 0.8 0.2 0 0.3', tag='mys')), mr - 21, 8.5, n=32, cx=mx, cy=my)
    picture(X.mesh(SM('tag_mys', 40, tag='mys')), (mx - mr - 3, my, mh + 50), 180, 45, (-1, 0, 0))
    tube(X.mesh(SM('black', tag='mys')), [(mx - mr - 2, my - 60, mh), (mx - mr - 2, my - 60, mh + 28)], 2, nseg=4)
    tube(X.mesh(SM('black', tag='mys')), [(mx - mr - 2, my + 60, mh), (mx - mr - 2, my + 60, mh + 28)], 2, nseg=4)
    return place_save('freezer', X, (x0 + x1) / 2, (y0 + y1) / 2)


# ================================================================================================= chest freezer
def chest():
    X = Model()
    x0, y0, x1, y1 = L.CF
    wh, fr, ic = SM('enamel_cream', 40, tag='cf'), SM('frost', 50, tag='cf'), SM('icecube', 50, tag='cf')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if part in ('cf_stair', 'cf_stair_in'): return ic, planar_uv(n, 64)
        if part == 'cf_floor': return fr, planar_uv(n, 128)
        q = c + n * 3
        inside = x0 + L.CF_T < q[0] < x1 - L.CF_T and y0 + L.CF_T < q[1] < y1 - L.CF_T
        if part == 'cf_lid': return (fr if (n[1] < -0.9 if L.CF_LID == 'n' else n[1] > 0.9) else wh), planar_uv(n, 256)
        return (fr if inside else wh), planar_uv(n, 256)
    solids_parts(X, SH.chest(), fn)
    picture(X.mesh(SM('badge_cf', 40, tag='cf')), ((x0 + x1) / 2 + 60, y0 - 0.6, 70), 300, 70, (0, -1, 0))
    return place_save('chest', X, (x0 + x1) / 2, (y0 + y1) / 2)


# ================================================================================================= ice cream cart
def cart():
    X = Model()
    w, d, h = L.CART_W, L.CART_D - 40, L.CART_H
    te = SM('enamel_teal', 40, tag='ct')
    rbox(X.mesh(te), (-w / 2, -d / 2, 110), (w / 2, d / 2, h - 30), r=14, k=2, tile=256)
    for s in (-1, 1):
        picture(X.mesh(SM('cart_side', 40, tag='ct')), (0, s * (d / 2 + 0.8), (110 + h - 30) / 2 + 10), w - 60, (h - 140) * 0.9, (0, s, 0))
    boxm(X.mesh(SC('steel', 0.3, tag='ct')), (-w / 2 - 4, -d / 2 - 4, h - 30), (w / 2 + 4, d / 2 + 4, h), r=6, tile=128)
    for s in (-1, 1):
        for (cx, r_) in ((0.0, 110.0),):
            m = Mesh(); torus(m, (0, 0, 0), r_, 9, axis=(0, 1, 0), n=28, m=6)
            X.mesh(SM('black', tag='ct')).add(m, np.eye(3), (cx, s * (d / 2 + 22), r_ + 6))
            for k in range(8):
                a = k * math.pi / 8
                tube(X.mesh(SC('steel', 0.3, tag='ct')), [(cx - r_ * math.cos(a), s * (d / 2 + 22), r_ + 6 - r_ * math.sin(a)),
                                                         (cx + r_ * math.cos(a), s * (d / 2 + 22), r_ + 6 + r_ * math.sin(a))], 2.5, nseg=4)
    for xx in (-w / 2 + 20, w / 2 - 20):
        tube(X.mesh(SC('steel', 0.3, tag='ct')), [(xx, 0, 0), (xx, 0, 110)], 8, nseg=8)
    tube(X.mesh(SC('steel', 0.3, tag='ct')), [(w / 2, -d / 2 + 20, 380), (w / 2 + 110, -d / 2 + 20, 420), (w / 2 + 110, d / 2 - 20, 420), (w / 2, d / 2 - 20, 380)], 8, nseg=8)
    tube(X.mesh(SC('steel', 0.3, tag='ct')), [(0, 0, h), (0, 0, 1010)], 10, nseg=8)
    um = SM('umbrella', 50, tag='ctu', two=True)
    revolve(X.mesh(um), [(0, 1080), (220, 1036), (400, 980)], n=16, u_tiles=8, vlen=64, inward=True)
    sphere(X.mesh(SM('red', 70, tag='ct')), (0, 0, 1090), 14, nu=8, nv=5)
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        ellipsoid(X.mesh(SM('enamel_cream', 40, tag='ctu')), (400 * math.cos(a), 400 * math.sin(a), 966), 30, 30, 18, nu=8, nv=4, R=rot_z(a))
    # cones in a holder on the lid
    for k, f in enumerate(('fl_straw', 'fl_mint', 'fl_choc')):
        x = -140 + k * 140
        revolve(X.mesh(SM('waffle', 50, tag='ctc')), [(0, h), (34, h + 90)], n=12, cx=x, cy=0)
        sphere(X.mesh(SM(f, 60, tag='ctc')), (x, 0, h + 104), 36, nu=12, nv=8, bump=scoop_bump(k))
    return place_save('cart', X, *L.CART, local=True)


# ================================================================================================= topping jars
def topping_jar(name, contents):
    X = Model()
    r, h = L.JAR_R, L.JAR_H
    revolve(X.mesh(SM(contents, 60, tag='tj' + contents)), [(0, 6), (r - 6, 6), (r - 6, h * 0.72), (0, h * 0.78)], n=24, vlen=96)
    revolve(X.mesh(S('glass_g', 'glass', tag='tj')), [(0, 0), (r + 2, 0), (r + 2, h - 30), (r - 10, h - 20)], n=24)
    cylm(X.mesh(SM('red', 50, tag='tj')), (0, 0, h - 26), r - 6, 26, n=24)
    torus(X.mesh(SM('enamel_cream', 40, tag='tj')), (0, 0, h - 12), r - 4, 5, n=24, m=6)
    sphere(X.mesh(SM('enamel_cream', 40, tag='tj')), (0, 0, h + 4), 14, nu=8, nv=5)
    return save(name, X)


# ================================================================================================= the display counter
def stadium(x0, x1, yc, r, n_arc=12, inset=0.0):
    """closed outline (counter-clockwise from the front-left) of a stadium shape: [(x, y, nx, ny, part)] where part is
    'front', 'end' or 'back'; inset moves the outline inward"""
    rr = r - inset
    out = []
    for x in np.linspace(x0, x1, 12):
        out.append((x, yc - rr, 0.0, -1.0, 'front'))
    for k in range(1, n_arc):
        a = -math.pi / 2 + math.pi * k / n_arc
        out.append((x1 + rr * math.cos(a), yc + rr * math.sin(a), math.cos(a), math.sin(a), 'end'))
    for x in np.linspace(x1, x0, 12):
        out.append((x, yc + rr, 0.0, 1.0, 'back'))
    for k in range(1, n_arc):
        a = math.pi / 2 + math.pi * k / n_arc
        out.append((x0 + rr * math.cos(a), yc + rr * math.sin(a), math.cos(a), math.sin(a), 'end'))
    return out


def outline_wall(M, pts, prof, closed=True, vlen=128.0, flip=False):
    """surface swept round an outline: prof [(d, z)] with d = inward offset; normals outward"""
    P = []; UV = []
    seg = pts + ([pts[0]] if closed else [])
    Lc = 0.0
    for i, (x, y, nx, ny, _) in enumerate(seg):
        if i: Lc += math.hypot(x - seg[i - 1][0], y - seg[i - 1][1])
        P.append([(x - nx * d, y - ny * d, z) for (d, z) in prof]); UV.append([(Lc / vlen, k / max(1, len(prof) - 1)) for k in range(len(prof))])
    P = np.array(P).transpose(1, 0, 2); UV = np.array(UV).transpose(1, 0, 2)
    N = grid_normals(P)
    c = P.mean(axis=(0, 1))
    if ((N * (P - c)).sum(-1) < 0).mean() > 0.5: N = -N
    if flip: N = -N
    M.grid(P, N, UV)


def display_counter():
    X = Model()
    x0, x1, y0, y1, r = L.DC_X0, L.DC_X1, L.DC_Y0, L.DC_Y1, L.DC_R
    yc = (y0 + y1) / 2
    B, TOP, G = L.DC_BODY, L.DC_TOP, L.DC_GLASS_D
    mint, pink, ch, blk = SM('enamel_mint', 40, tag='dc'), SM('enamel_pink', 40, tag='dc'), SC('steel', 0.3, tag='dc'), SM('black', tag='dc')
    gl = S('glass_g', 'glass', c='0.08 0.1 0.11', tag='dcg', two=True)
    full = stadium(x0, x1, yc, r, 12)
    # cabinet: black kick plate, mint panels, pink rounded edge, chrome rail
    outline_wall(X.mesh(blk), stadium(x0, x1, yc, r, 12, 10), [(0, 0), (0, 40)])
    outline_wall(X.mesh(mint), full, [(0, 40), (0, B - 24)], vlen=300)
    outline_wall(X.mesh(pink), full, [(0, B - 24), (-6, B - 16), (-8, B - 6), (-2, B), (8, B + 2)], vlen=300)
    tubs_x = np.linspace(x0 + 135, x1 - 135, 11)
    for t in (tubs_x[:-1] + tubs_x[1:]) / 2:
        boxm(X.mesh(ch), (t - 5, y0 - 3, 60), (t + 5, y0 + 1, B - 30), r=1, tile=32)
    tube(X.mesh(ch), [(x0 + 20, y0 - 30, 90), (x1 - 20, y0 - 30, 90)], 6, nseg=8)
    for t in np.linspace(x0 + 60, x1 - 60, 9):
        tube(X.mesh(ch), [(t, y0 - 30, 90), (t, y0, 90)], 4, nseg=6)
    # the curved glass: front + both ends bulge out a little and lean back to the flat top; vertical at the back
    front = [p for p in full if p[4] != 'back']
    prof = [(2, B + 2), (-12, B + 70), (-8, B + 150), (10, B + 210), (G - 12, TOP - 6), (G, TOP)]
    outline_wall(X.mesh(gl), front, prof, closed=False, vlen=600)
    back = [p for p in full if p[4] == 'back']
    outline_wall(X.mesh(gl), back, [(4, B), (4, TOP)], closed=False, vlen=600)
    # the flat glass top (walkable), chrome frame round it
    inner = stadium(x0, x1, yc, r - G, 12)
    X.mesh(gl).poly([np.array([x0, y0 + G, TOP]), np.array([x1, y0 + G, TOP]), np.array([x1, y1, TOP]), np.array([x0, y1, TOP])], (0, 0, 1),
                    [(0, 0), (6, 0), (6, 1), (0, 1)])
    for (cxe, a0) in ((x0, 90.0), (x1, -90.0)):
        annulus(X.mesh(gl), cxe, yc, 0, r - G, TOP, a0, a0 + 180, n=12)
    outline_wall(X.mesh(ch), inner, [(-3, TOP - 6), (-3, TOP + 2), (3, TOP + 2)], vlen=128)
    # inside: steel shelf, eleven tubs of gelato in a row with tags, a light strip under the glass top
    annulus(X.mesh(ch), x0, yc, 0, r - 4, B + 1, 90, 270, n=12); annulus(X.mesh(ch), x1, yc, 0, r - 4, B + 1, -90, 90, n=12)
    quad_uv(X.mesh(ch), (x0, y0 + 4, B + 1), (x1, y0 + 4, B + 1), (x1, y1 - 4, B + 1), (x0, y1 - 4, B + 1), [(0, 0), (12, 0), (12, 1), (0, 1)], (0, 0, 1))
    tubs = np.linspace(x0 + 135, x1 - 135, 11)
    flv = TUB_FLAVOURS + ['fl_vanilla', 'fl_mystery', 'fl_straw']
    for k, tx in enumerate(tubs):
        f = flv[k % len(flv)]
        boxm(X.mesh(ch), (tx - 110, yc - 95, B + 1), (tx + 110, yc + 95, B + 60), r=4, tile=64)
        nx_, ny_ = 8, 6
        P = np.zeros((ny_ + 1, nx_ + 1, 3)); UV = np.zeros((ny_ + 1, nx_ + 1, 2))
        for j in range(ny_ + 1):
            for i in range(nx_ + 1):
                u, v = i / nx_, j / ny_
                x, y = tx - 104 + 208 * u, yc - 89 + 178 * v
                h = 36 * math.sin(math.pi * u) * math.sin(math.pi * v) + 6 * math.sin(u * 13 + k) * math.cos(v * 11)
                P[j, i] = (x, y, B + 58 + max(0, h)); UV[j, i] = (x / 120, -y / 120)
        Nn = grid_normals(P)
        if Nn[ny_ // 2, nx_ // 2, 2] < 0: Nn = -Nn
        X.mesh(SM(f, 60, tag='dct' + f)).grid(P, Nn, UV)
        tube(X.mesh(ch), [(tx + 40, yc + 40, B + 80), (tx + 60, yc + 80, B + 150)], 4, nseg=6)
        nm = f'tag_{k % 8}'
        picture(X.mesh(SM(nm, 40, tag='gctag')), (tx, y0 - 0.8, B - 60), 190, 48, (0, -1, 0))
    quad_uv(X.mesh(S('glow_w', 'glow', tag='dcl')), (x0, y1 - 30, TOP - 2), (x1, y1 - 30, TOP - 2), (x1, y1 - 10, TOP - 2), (x0, y1 - 10, TOP - 2),
            [(0, 0), (1, 0), (1, 1), (0, 1)], (0, 0, -1))
    # kitchen side: steel cabinet doors with chrome handles
    for t in np.linspace(x0 + 150, x1 - 150, 10):
        boxm(X.mesh(ch), (t - 60, y1 - 1, 120), (t + 60, y1 + 3, 126), r=1, tile=32)
    return place_save('display', X, 0, yc)


def batch_freezer():
    X = Model()
    x0, y0, x1, y1 = L.BF
    dx, dz, dr = L.BF_DRUM
    st, sd, ch = SC('steel', 0.2, tag='bf'), SM('steel_d', tag='bf'), SC('steel', 0.35, tag='bfc')

    def fn(part, c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if part == 'bf_drum': return None
        if part == 'bf_ledge': return st, planar_uv(n, 64)
        return st, planar_uv(n, 256)
    solids_parts(X, SH.batch_freezer(), fn)
    # porthole: chrome ring, dark drum behind, glass dome in front (the dasher turns inside: a mover)
    m = Mesh(); torus(m, (0, 0, 0), dr, 14, axis=(0, 1, 0), n=40, m=8)
    X.mesh(ch).add(m, np.eye(3), (dx, y0 - 4, dz))
    m = Mesh(); disc(m, dr, 0, up=True, n=40)
    X.mesh(SM('fl_straw', 60, tag='bfd')).add(m, rot_axis((1, 0, 0), math.pi / 2), (dx, y0 - 1, dz))
    m = Mesh(); ellipsoid(m, (0, 0, 0), dr, L.BF_DRUM_D, dr, nu=24, nv=12, v1=1.0)
    X.mesh(S('glass_g', 'glass', c='0.10 0.12 0.13', tag='bfg')).add(m, np.eye(3), (dx, y0 - 2, dz))
    # chute with gelato ribbon pouring into the tub on the ledge, control panel, name plate, top vents
    boxm(X.mesh(ch), (x1 - 90, y0 - 80, 230), (x1 - 40, y0, 270), r=6, tile=32)
    revolve(X.mesh(ch), [(0, 230), (22, 230), (16, 200), (0, 196)], n=12, cx=x1 - 65, cy=y0 - 60)
    fl = S('ribbon', 'flow', speed=-1.4, tag='bff')
    quad_uv(X.mesh(fl), (x1 - 80, y0 - 60, 200), (x1 - 50, y0 - 60, 200), (x1 - 50, y0 - 60, 120), (x1 - 80, y0 - 60, 120), [(0, 0), (1, 0), (1, 2), (0, 2)], (0, -1, 0))
    quad_uv(X.mesh(fl), (x1 - 65, y0 - 75, 200), (x1 - 65, y0 - 45, 200), (x1 - 65, y0 - 45, 120), (x1 - 65, y0 - 75, 120), [(0, 0), (1, 0), (1, 2), (0, 2)], (1, 0, 0))
    picture(X.mesh(S('screen', 'glow', tag='bf')), (x0 + 110, y0 - 0.6, 520), 140, 60, (0, -1, 0))
    for k in range(3):
        m = Mesh(); cylm(m, (0, 0, 0), 16, 10, n=12)
        X.mesh(SM(['red', 'black', 'enamel_mint'][k], 50, tag='bfk')).add(m, rot_axis((1, 0, 0), math.pi / 2), (x0 + 70 + k * 40, y0, 440))
    picture(X.mesh(SM('plate_bf', 40, tag='bf')), (dx, y0 - 0.6, 590), 300, 56, (0, -1, 0))
    for k in range(5):
        boxm(X.mesh(sd), (x0 + 60 + k * 80, y0 + 100, L.BF_H), (x0 + 100 + k * 80, y1 - 100, L.BF_H + 3), r=1, tile=32)
    for (px, py) in ((x0 + 20, y0 + 20), (x1 - 20, y0 + 20), (x0 + 20, y1 - 20), (x1 - 20, y1 - 20)):
        cylm(X.mesh(SM('rubber_b', tag='bf')), (px, py, -2), 18, 4, n=10)
    return place_save('batchfreezer', X, (x0 + x1) / 2, (y0 + y1) / 2)


def dasher():
    """the churning dasher inside the porthole (func_rotating about y; origin at the drum centre)"""
    X = Model()
    ch, ge = S('steel', 'dyn', tag='ds'), S('fl_straw', 'dyn', tag='ds')
    for k in range(3):
        a = 2 * math.pi * k / 3
        d = np.array([math.cos(a), 0, math.sin(a)])
        tube(X.mesh(ch), [d * 10, d * 128], 5, nseg=6)
        m = Mesh(); rbox(m, (-6, -20, 40), (6, 20, 126), r=2, k=1, tile=64)
        X.mesh(ch).add(m, rot_axis((0, 1, 0), -a + math.pi / 2))
        ellipsoid(X.mesh(ge), d * 90, 26, 16, 18, nu=8, nv=5)
    m = Mesh(); cylm(m, (0, 0, -20), 18, 40, n=12)
    X.mesh(ch).add(m, rot_axis((1, 0, 0), math.pi / 2))
    return save('dasher', X)


def vat():
    X = Model()
    cx, cy = L.VAT
    st, ch = SC('steel', 0.25, tag='vt'), SC('steel', 0.35, tag='vtc')
    r0, r1, R = L.VAT_R0, L.VAT_R1, L.VAT_RIM
    revolve(X.mesh(st), [(r1 + 6, 0), (r1 + 6, R - 14)], n=48, u_tiles=8, vlen=256)
    annulus(X.mesh(SM('steel_d', tag='vt')), 0, 0, r0 - 4, r1 + 6, R, 0, 360, n=48)
    torus(X.mesh(ch), (0, 0, R - 6), r1 + 4, 8, n=48, m=8)
    revolve(X.mesh(st), [(r0 - 2, R), (r0 - 2, L.VAT_MILK)], n=48, inward=True)
    disc(X.mesh(SM('cream', 70, tag='vtm')), r0 - 1, L.VAT_MILK + 0.5, n=48)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        tube(X.mesh(ch), [((r1 + 6) * math.cos(a), (r1 + 6) * math.sin(a), 80), ((r1 + 20) * math.cos(a), (r1 + 20) * math.sin(a), 80),
                          ((r1 + 20) * math.cos(a), (r1 + 20) * math.sin(a), 300), ((r1 + 6) * math.cos(a), (r1 + 6) * math.sin(a), 300)], 5, nseg=6)
    picture(X.mesh(SM('plate_vat', 40, tag='vt')), (r1 + 6.6, 0, 200), 260, 80, (1, 0, 0))
    # the motor bridge and its legs (collision in gl_shapes), the motor housing on top
    z0, z1 = L.VAT_BEAM_Z
    boxm(X.mesh(SM('enamel_mint', 40, tag='vt')), (-30, -r1 - 40, z0), (30, r1 + 40, z1), r=6, tile=128)
    for s_ in (-1, 1):
        boxm(X.mesh(ch), (-30, s_ * (r1 + 20) - 20, 0), (30, s_ * (r1 + 20) + 20, z0), r=4, tile=64)
    revolve(X.mesh(SM('enamel_mint', 40, tag='vt')), [(0, z1), (70, z1), (70, z1 + 110), (50, z1 + 140), (0, z1 + 140)], n=20)
    return place_save('vat', X, cx, cy, local=True)


def vat_paddle():
    """the vat paddle (func_rotating about z; origin at the beam underside over the vat centre)"""
    X = Model()
    ch = S('steel', 'dyn', tag='vp')
    zb = L.VAT_BEAM_Z[0]
    h = zb - (L.VAT_MILK + 20)
    tube(X.mesh(ch), [(0, 0, 0), (0, 0, -h)], 10, nseg=8)
    for s_ in (-1, 1):
        m = Mesh(); rbox(m, (30, -6, -h), (230, 6, -h + 70), r=3, k=1, tile=64)
        X.mesh(ch).add(m, rot_z(0 if s_ > 0 else math.pi))
        tube(X.mesh(ch), [(s_ * 30, 0, -h + 60), (s_ * 230, 0, -h + 60)], 4, nseg=6)
    return save('vat_paddle', X)


def make_badges():
    T('badge_ss', tex_label(512, 160, 'SOFT SERVE', (214, 36, 56), (252, 244, 226), 'TWIST - VANILLA - STRAWBERRY'))
    T('badge_cf', tex_label(512, 128, 'ICE CREAM', (252, 244, 226), (214, 36, 56)))
    T('tag_mys', tex_tag('MYSTERY ???', (50, 40, 70)))
    T('plate_bf', tex_label(512, 96, 'PADMAN BATCH 120', (40, 44, 48), (240, 240, 236)))
    T('plate_vat', tex_label(512, 160, 'PASTEURISER', (176, 226, 206), (60, 60, 64), 'MILK + CREAM - 85 C'))


def make():
    make_textures(); make_gelato_textures(); make_badges()
    tower(); gelato_counter(); softserve(); bar(); milkshake(); freezer(); chest(); cart()
    display_counter(); batch_freezer(); dasher(); vat(); vat_paddle()
    for nm, c in (('jar_spr', 'sprinkles'), ('jar_choc', 'choc_d'), ('jar_nuts', 'nuts'), ('jar_marsh', 'marsh'), ('jar_gummy', 'gummy')):
        topping_jar(nm, c)
    swirl_mover('swirl_v', 'cream'); swirl_mover('swirl_s', 'fl_straw')
