"""The galleon 'The Salty Padman' for wop_padpirate: hull skin, decks, castles, interiors, gunports, stern gallery,
figurehead, bowsprit, masts with furled sails, crow's nest, rigging and flags. All geometry and art is original.

The decks, castle walls, bulwarks and stairs are drawn from the same convex solids the builder uses as weapclip
(pp_shapes.ship_*), so collision and visuals match exactly; the smooth hull skin sits 6+ units outside them.
The hull is split into an aft and a fore MD3 (MD3 can't hold geometry beyond +-512 of its origin); each mast is its own
MD3 stored round its mid-height."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame
from pplib import *
import pplib
import layout as L
import pp_shapes as SH

TXD = 'textures/padpirate/'
SX, SY = L.SHIP
SPLIT_X = -40.0                       # aft / fore hull MD3 split (ship-relative)


def BT(name): return TXD + name


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


# ================================================================================================= textures
HULL_Z0, HULL_Z1 = -272.0, 304.0


def hull_v(z): return (HULL_Z1 - z) / (HULL_Z1 - HULL_Z0)


def tex_hull(w=256, h=1024, seed=1):
    """the hull strip: v maps z 304 (top) .. -272 (bottom). Castles dark brown with gold trim, ochre wale band at the
    main deck, black tarred planks, a white boot-top line at the water, red antifouling below"""
    x, y = xy(w, h)
    z = HULL_Z1 - y * (HULL_Z1 - HULL_Z0)
    c = np.zeros((h, w, 3), np.float32)
    def band(z0, z1, col):
        m = ((z >= z0) & (z < z1))[..., None]
        return np.where(m, C(col), 0)
    c += band(-400, -26, (120, 46, 34)) + band(-26, -14, (232, 226, 210)) + band(-14, 98, (34, 30, 30)) + band(98, 142, (196, 150, 60))
    c += band(142, 400, (70, 44, 30))
    # thin red line inside the ochre band and gold trim lines on the castles
    c = np.where((np.abs(z - 104) < 2.5)[..., None], C((160, 34, 28)), c)
    c = np.where((np.abs(z - 136) < 2.5)[..., None], C((160, 34, 28)), c)
    for zz in (160, 248, 284):
        c = np.where((np.abs(z - zz) < 2.2)[..., None], C((214, 170, 70)), c)
    # planks: seams every 12u, staggered butt joints
    pz = (z / 12.0)
    row = np.floor(pz).astype(int)
    seam = (pz % 1.0) < 0.12
    off = np.random.default_rng(seed).uniform(0, 1, 200)[row % 200]
    butt = (((x + off) * 2) % 1.0) < 0.012
    tone = np.random.default_rng(seed + 1).uniform(-0.08, 0.08, 200)[row % 200]
    c = c * (1 + tone)[..., None]
    c = np.where(((seam | butt) & (z > -14))[..., None], c * 0.55, c)
    grain = np.asarray(img(noise(w, 1, seed + 2, h) * 50 + 128).resize((w, h // 32)).resize((w, h)), np.float32) - 128
    c += grain[..., None] * 0.12
    # weathering + barnacles near the water
    c = lerp(c, C((90, 96, 80)), (np.clip(1 - np.abs(z + 20) / 30, 0, 1) * np.clip(noise(w, 3, seed + 3, h) * 0.5 + 0.2, 0, 1) * 0.5)[..., None])
    return c


def tex_transom(w=512, h=512, seed=3):
    """stern: dark planks, gold carved frame round the gallery, painted scrollwork"""
    c = np.zeros((h, w, 3), np.float32) + C((64, 40, 28)) + N3(w, 1, seed, 6, h)
    x, y = xy(w, h)
    c = np.where((((y * 32) % 1.0) < 0.08)[..., None], c * 0.6, c)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    gold = (214, 170, 70)
    d.rectangle((20, 40, w - 20, 210), outline=gold, width=8)
    for k in range(6):
        cx = 60 + k * (w - 120) / 5
        d.arc((cx - 40, 230, cx + 40, 300), 0, 180, fill=gold, width=6)
    d.ellipse((w / 2 - 50, 320, w / 2 + 50, 420), outline=gold, width=8)
    d.line([(w / 2 - 120, 370), (w / 2 + 120, 370)], fill=gold, width=5)
    return np.asarray(im, np.float32)


def tex_panel(w=256, h=256, seed=5, base=(110, 70, 44)):
    """raised wooden wall panels (cabin)"""
    c = np.zeros((h, w, 3), np.float32) + C(base) + N3(w, 1, seed, 6, h)
    x, y = xy(w, h)
    fx, fy = (x * 2) % 1.0, (y * 2) % 1.0
    frame_ = (fx < 0.1) | (fx > 0.9) | (fy < 0.1) | (fy > 0.9)
    bevel = ((np.abs(fx - 0.1) < 0.02) | (np.abs(fy - 0.1) < 0.02))
    c = np.where(frame_[..., None], c * 1.15, c)
    c = np.where(bevel[..., None], c * 0.7, c)
    grain = np.asarray(img(noise(w, 1, seed + 1, h) * 50 + 128).resize((w // 16, h)).resize((w, h)), np.float32) - 128
    return c + grain[..., None] * 0.15


def tex_beams(w=256, h=256, seed=7):
    """deck underside: planks with heavy beams every 128u"""
    c = np.zeros((h, w, 3), np.float32) + C((96, 66, 42)) + N3(w, 1, seed, 6, h)
    x, y = xy(w, h)
    c = np.where((((y * 8) % 1.0) < 0.06)[..., None], c * 0.6, c)
    c = np.where((((x * 2) % 1.0) < 0.16)[..., None], C((70, 46, 30)) + N3(w, 1, seed + 1, 6, h), c)
    return c


def tex_spar(w=64, h=256, seed=9):
    c = np.zeros((h, w, 3), np.float32) + C((128, 90, 52)) + N3(w, 1, seed, 8, h)
    gr = np.asarray(img(noise(w, 0.8, seed + 1, h) * 60 + 128).resize((w // 8, h)).resize((w, h)), np.float32) - 128
    return c + gr[..., None] * 0.25


def tex_canvas(w=128, h=128, seed=11):
    """furled sail canvas: creamy with folds"""
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C((226, 214, 186)) * (0.82 + 0.18 * np.sin(y * 2 * math.pi * 6))[..., None]
    return c + N3(w, 1, seed, 5, h)


def tex_net(w=128, h=128, seed=13):
    """ratlines: rope mesh (alpha)"""
    x, y = xy(w, h)
    rope = (np.abs(((x * 4) % 1.0) - 0.5) > 0.44) | (np.abs(((y * 6) % 1.0) - 0.5) > 0.43)
    c = np.zeros((h, w, 3), np.float32) + C((70, 56, 40)) + N3(w, 0.6, seed, 8, h)
    return c, rope.astype(np.float32) * 255


def tex_jolly(w=256, h=160, seed=15):
    """the Jolly Roger: skull and crossed bones on black (both faces read correctly)"""
    im = Image.new('RGB', (w, h), (14, 14, 16)); d = ImageDraw.Draw(im)
    wh = (238, 234, 222)
    cx, cy = w / 2, h * 0.42
    for s in (-1, 1):
        d.line([(cx - 70, cy + 20 + s * 40), (cx + 70, cy + 20 - s * 40)], fill=wh, width=16)
        for (ex, ey) in ((cx - 70, cy + 20 + s * 40), (cx + 70, cy + 20 - s * 40)):
            d.ellipse((ex - 12, ey - 12, ex + 4, ey + 4), fill=wh); d.ellipse((ex - 4, ey - 4, ex + 12, ey + 12), fill=wh)
    d.ellipse((cx - 40, cy - 46, cx + 40, cy + 26), fill=wh)
    d.rectangle((cx - 24, cy + 10, cx + 24, cy + 40), fill=wh)
    d.ellipse((cx - 28, cy - 18, cx - 6, cy + 4), fill=(14, 14, 16)); d.ellipse((cx + 6, cy - 18, cx + 28, cy + 4), fill=(14, 14, 16))
    d.polygon([(cx, cy + 6), (cx - 6, cy + 16), (cx + 6, cy + 16)], fill=(14, 14, 16))
    for k in range(4):
        d.line([(cx - 15 + k * 10, cy + 26), (cx - 15 + k * 10, cy + 40)], fill=(14, 14, 16), width=3)
    return np.asarray(im, np.float32) + N3(w, 1, seed, 4, h)


def tex_window(w=128, h=128, seed=17):
    """leaded stern window, warm glow"""
    x, y = xy(w, h)
    c = np.zeros((h, w, 3), np.float32) + C((255, 196, 110)) * (0.75 + 0.25 * (1 - y))[..., None]
    lead = (((x * 4) % 1.0) < 0.07) | (((y * 4) % 1.0) < 0.07) | (x > 0.95) | (y > 0.95)
    c = np.where(lead[..., None], C((40, 30, 24)), c)
    return c + N3(w, 1, seed, 6, h)


def tex_gold(n=64, seed=19):
    return fill(n, (220, 170, 60), 10, seed) + N3(n, 0.5, seed + 1, 14)


def tex_iron(n=64, seed=21):
    return fill(n, (40, 40, 44), 4, seed) + N3(n, 0.5, seed + 1, 8)


def tex_duck(n=128, seed=23):
    return fill(n, (250, 200, 40), 6, seed)


def tex_hold_port(n=64, seed=25):
    """a gunport seen from inside: dark square with light round the closed lid"""
    c = np.zeros((n, n, 3), np.float32) + C((30, 24, 20)) + N3(n, 1, seed, 4)
    x, y = xy(n)
    edge = (x < 0.08) | (x > 0.92) | (y < 0.08) | (y > 0.92)
    c = np.where(edge[..., None], C((250, 220, 160)), c)
    return c


def make_textures():
    T('hull', tex_hull()); T('transom', tex_transom()); T('panel', tex_panel()); T('panel_dark', tex_panel(256, 256, 6, (70, 46, 30)))
    T('beams', tex_beams()); T('spar', tex_spar()); T('canvas', tex_canvas()); f, a = tex_net(); T('net', f, a); T('jolly', tex_jolly())
    T('window', tex_window()); T('gold', tex_gold()); T('iron', tex_iron()); T('duck', tex_duck()); T('hold_port', tex_hold_port())
    T('rail', fill(64, (64, 38, 24), 4, 27) + N3(64, 0.5, 28, 8)); T('red', fill(64, (170, 40, 32), 4, 29)); T('black', fill(64, (22, 20, 20), 2, 30))
    T('lantern', fill(32, (255, 220, 140), 2, 31)); T('white', fill(64, (240, 236, 226), 3, 32))


# ================================================================================================= hull skin
def skin_pt(x, z, s):
    """ship-relative skin point and outward normal on side s (+1 north/port, -1 south/starboard)"""
    w = L.ship_halfbeam(x, z)
    p = np.array([x, s * w, z])
    e = 2.0
    dx = (L.ship_halfbeam(x + e, z) - L.ship_halfbeam(x - e, z)) / (2 * e)
    dz = (L.ship_halfbeam(x, z + e) - L.ship_halfbeam(x, z - e)) / (2 * e)
    n = np.array([-s * dx, 1.0 * s, -s * dz]) * np.array([1, 1, 1])
    n = np.array([-dx * s, s, -dz * s])
    n /= np.linalg.norm(n)
    return p, n


def skin_section(Mh, xs, ztop):
    """skin grid for both sides over stations xs (ship-relative) from the keel to ztop"""
    zs = sorted(set([-272, -250, -230, -205, -180, -150, -110, -75, -40, -26, -14, 20, 60, 98, 112, 130, 142, 152] +
                    [z for z in (170, 200, 230, 256, 270, 288) if z <= ztop]))
    zs = [z for z in zs if z <= ztop]
    if zs[-1] < ztop: zs.append(ztop)
    for s in (-1, 1):
        P = np.zeros((len(zs), len(xs), 3)); N = np.zeros_like(P); UV = np.zeros((len(zs), len(xs), 2))
        for i, z in enumerate(zs):
            for j, x in enumerate(xs):
                p, n = skin_pt(x, z, s)
                P[i, j] = p; N[i, j] = n
                UV[i, j] = ((x if s > 0 else -x) / 256.0, hull_v(z))
        # grid winding follows the normals (meshlib.grid orders each triangle by its vertex normals)
        Mh.grid(P, N, UV)
    return zs


def rail_cap(Mr, xs, ztop):
    """the cap strip at the top edge of the skin, from the skin inward to the bulwark's inner face"""
    sts = L.ship_stations()
    def coll_at(x):
        for a, b in zip(sts, sts[1:]):
            if a <= x <= b: return L.ship_coll_halfbeam(a, b, L.ship_deck_z((a + b) / 2))
        return 0.0
    for s in (-1, 1):
        for x0, x1 in zip(xs, xs[1:]):
            w0, w1 = L.ship_halfbeam(x0, ztop), L.ship_halfbeam(x1, ztop)
            if w0 < 1 and w1 < 1: continue
            ci = max(0.0, coll_at((x0 + x1) / 2) - L.BULW_T)
            ci0, ci1 = min(ci, w0), min(ci, w1)
            q = [np.array([x0, s * ci0, ztop + 0.4]), np.array([x1, s * ci1, ztop + 0.4]), np.array([x1, s * w1, ztop + 0.4]),
                 np.array([x0, s * w0, ztop + 0.4])]
            Mr.poly(q, (0, 0, 1), [(x0 / 64, ci0 / 64), (x1 / 64, ci1 / 64), (x1 / 64, w1 / 64), (x0 / 64, w0 / 64)])
        # a raised moulding on the outer edge
        pts = [np.array([x, s * (L.ship_halfbeam(x, ztop) + 1.5), ztop + 1.5]) for x in xs if L.ship_halfbeam(x, ztop) > 2]
        if len(pts) > 2: tube(Mr, pts, 3.5, nseg=6, caps=(False, False), vlen=64)


def stem_fill(Mh, Mc):
    """vertical end caps where the sheer steps at the castle fronts (skin edge to bulwark face)"""
    for (x, z0, z1) in ((L.QD_X, L.WAIST_Z + L.BULW_H, L.QD_Z + L.RAIL_H), (L.FC_X, L.WAIST_Z + L.BULW_H, L.FC_Z + L.RAIL_H)):
        sgn = 1 if x > 0 else -1          # the face looks toward the waist
        sts = L.ship_stations()
        for s in (-1, 1):
            q = []
            for z in (z0, z1):
                w = L.ship_halfbeam(x, z)
                q.append((w, z))
            wi = L.ship_coll_halfbeam(x - 20 if x < 0 else x, x if x < 0 else x + 20, z1) - L.BULW_T
            P = [np.array([x, s * wi, z0]), np.array([x, s * q[0][0], z0]), np.array([x, s * q[1][0], z1]), np.array([x, s * wi, z1])]
            Mc.poly(P, (-sgn * -1 if False else (1 if x < 0 else -1), 0, 0), [(p[1] / 64, -p[2] / 64) for p in P])


def transom(X):
    """flat stern panel with the gallery windows, name board, carvings and three stern lanterns"""
    x = L.SHIP_STERN
    sh = S('transom', 'lm', shade=30); win = S('window', 'glow'); gd = S('gold', 'lms', v=0.25, tag='tr')
    zs = sorted(set([-272, -250, -230, -205, -180, -150, -110, -75, -40, -14, 20, 60, 98, 130, 152, 200, 256, 288]))
    pts = [np.array([x, -L.ship_halfbeam(x, z), z]) for z in zs] + [np.array([x, L.ship_halfbeam(x, z), z]) for z in zs[::-1]]
    pts = [p for p in pts if abs(p[1]) > 0.5 or True]
    c = np.mean(pts, axis=0)
    M = X.mesh(sh)
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        uv = lambda p: ((-p[1] + 160) / 320.0, (304 - p[2]) / 576.0 * 1.0)
        M.poly([c, b, a], (-1, 0, 0), [uv(c), uv(b), uv(a)])
    # gallery windows (5 across) between z 150 and 220, and the inside view (cabin)
    for k in range(5):
        yy = -84 + k * 42
        quad = [np.array([x - 1.5, yy - 15, 152]), np.array([x - 1.5, yy + 15, 152]), np.array([x - 1.5, yy + 15, 214]), np.array([x - 1.5, yy - 15, 214])]
        X.mesh(win).poly(quad[::-1], (-1, 0, 0), [(1, 1), (0, 1), (0, 0), (1, 0)][::-1])
        qi = [np.array([L.CABIN[0] + 1.0, yy - 15, 152]), np.array([L.CABIN[0] + 1.0, yy + 15, 152]), np.array([L.CABIN[0] + 1.0, yy + 15, 214]),
              np.array([L.CABIN[0] + 1.0, yy - 15, 214])]
        X.mesh(win).poly(qi, (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        rbox(X.mesh(gd), (x - 4, yy - 19, 148), (x - 1, yy + 19, 152), r=0.5, tile=32)
        rbox(X.mesh(gd), (x - 4, yy - 19, 214), (x - 1, yy + 19, 218), r=0.5, tile=32)
    # name board under the windows
    nb = S(BT('sign_ship'), 'lm', tag='nb')
    X.mesh(nb).poly([np.array([x - 2, 96, 112]), np.array([x - 2, -96, 112]), np.array([x - 2, -96, 136]), np.array([x - 2, 96, 136])], (-1, 0, 0),
                    [(0, 1), (1, 1), (1, 0), (0, 0)])
    # carved gold frame posts at the quarters and three stern lanterns on brackets
    for s in (-1, 1):
        y = s * (L.ship_halfbeam(x, 200) - 6)
        tube(X.mesh(gd), [(x - 4, y, 100), (x - 6, y * 1.02, 200), (x - 4, y * 0.98, 290)], [7, 5, 6], nseg=8)
    lan = S('lantern', 'glow', tag='sl')
    ir = S('iron', 'lm', tag='sl')
    for (yy, zz) in ((0, 320), (-96, 312), (96, 312)):
        tube(X.mesh(ir), [(x + 2, yy, 288), (x - 24, yy, 300), (x - 30, yy, zz - 18)], 2.5, nseg=6)
        cylm = Mesh(); revolve(cylm, [(0, zz - 14), (6, zz - 11), (7, zz), (6, zz + 9), (1.5, zz + 14), (0, zz + 15)], n=10, vlen=32)
        X.mesh(lan).add(cylm, np.eye(3), (x - 30, yy, 0))
    # rudder
    rd = S('rail', 'lm', tag='rud')
    rbox(X.mesh(rd), (x - 26, -9, -250), (x - 2, 9, 40), r=3, tile=64)
    for z in (-200, -100, 0):
        rbox(X.mesh(ir), (x - 28, -11, z), (x - 1, 11, z + 8), r=1, tile=32)


def gunports(X):
    """gunports on the hold level (closed lids hinged up, muzzles poking out) and painted ports on the bulwarks behind
    the deck guns; the matching ports inside the hold"""
    fr = S('rail', 'lm', tag='gp'); lid = S('red', 'lm', tag='gp'); ir = S('iron', 'lm', tag='gp'); dk = S('black', 'lm', tag='gp')
    hp = S('hold_port', 'glow')
    for xc in HOLD_GUNS:
        for s in (-1, 1):
            p, n = skin_pt(xc, 46, s)
            t_ = np.array([1.0, 0, 0]); up = np.cross(n, t_) * s
            up = up / np.linalg.norm(up)
            if up[2] < 0: up = -up
            def q(du, dz, off):
                return p + t_ * du + up * dz + n * off
            # frame (4 bars), dark opening, lid hinged up and out
            for (a, b, c, d) in (((-22, -22), (22, -22), (22, -16), (-22, -16)), ((-22, 16), (22, 16), (22, 22), (-22, 22)),
                                 ((-22, -16), (-16, -16), (-16, 16), (-22, 16)), ((16, -16), (22, -16), (22, 16), (16, 16))):
                P = [q(a[0], a[1], 2.5), q(b[0], b[1], 2.5), q(c[0], c[1], 2.5), q(d[0], d[1], 2.5)]
                X.mesh(fr).poly(P if s > 0 else P[::-1], n, [(0, 0), (1, 0), (1, 1), (0, 1)])
            P = [q(-16, -16, 1.0), q(16, -16, 1.0), q(16, 16, 1.0), q(-16, 16, 1.0)]
            X.mesh(dk).poly(P if s > 0 else P[::-1], n, [(0, 0), (1, 0), (1, 1), (0, 1)])
            hinge = q(0, 18, 2.5)
            lid_dir = up * 0.35 + n * 0.94
            P = [hinge - t_ * 18, hinge + t_ * 18, hinge + t_ * 18 + lid_dir * 34, hinge - t_ * 18 + lid_dir * 34]
            nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
            X.mesh(lid).poly(P, nn, [(0, 0), (1, 0), (1, 1), (0, 1)])
            X.mesh(lid).poly(P[::-1], -nn, [(0, 1), (1, 1), (1, 0), (0, 0)])
            # muzzle
            m0 = q(0, 0, -2); m1 = q(0, 0, 22)
            tube(X.mesh(ir), [m0, m0 + (m1 - m0) * 0.8, m1], [7, 7, 8.5], nseg=10)
            # inside: the port seen from the hold
            yi = s * (L.HOLD[3] - 0.8)
            P = [np.array([xc - 16, yi, 30]), np.array([xc + 16, yi, 30]), np.array([xc + 16, yi, 62]), np.array([xc - 16, yi, 62])]
            X.mesh(hp).poly(P if s < 0 else P[::-1], (0, -s, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    # deck gun ports painted on the bulwarks (inside and out)
    for xc in DECK_GUNS:
        for s in (-1, 1):
            p, n = skin_pt(xc, 132, s)
            P = [p + np.array([-18, 0, -10]) + n * 1.2, p + np.array([18, 0, -10]) + n * 1.2, p + np.array([18, 0, 14]) + n * 1.2,
                 p + np.array([-18, 0, 14]) + n * 1.2]
            X.mesh(dk).poly(P if s > 0 else P[::-1], n, [(0, 0), (1, 0), (1, 1), (0, 1)])
            wi = L.CW - L.BULW_T - 0.8
            P = [np.array([xc - 18, s * wi, 120]), np.array([xc + 18, s * wi, 120]), np.array([xc + 18, s * wi, 146]), np.array([xc - 18, s * wi, 146])]
            X.mesh(dk).poly(P if s < 0 else P[::-1], (0, -s, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])


HOLD_GUNS = [-170.0, -70.0, 270.0]
DECK_GUNS = [-104.0, 128.0]


def wales(X):
    """mouldings along the hull: a gold wale at the main deck line, a black one over the gunports"""
    gd = S('gold', 'lms', v=0.25, tag='wl'); bk = S('black', 'lm', tag='wl')
    for (z, sh, r) in ((142, gd, 3.0), (98, bk, 3.5), (-14, S('white', 'lm', tag='wl'), 2.0)):
        for s in (-1, 1):
            pts = []
            for x in np.arange(L.SHIP_STERN + 2, 700, 12):
                w = L.ship_halfbeam(x, z)
                if w < 6: break
                p, n = skin_pt(x, z, s)
                pts.append(p + n * (r - 0.5))
            if len(pts) > 2: tube(X.mesh(sh), pts, r, nseg=6, caps=(True, True), vlen=64)


def bow(X):
    """stem post curling up into the figurehead (a golden rubber duck), bowsprit + jib boom, catheads, the anchor"""
    rl = S('rail', 'lm', tag='bw'); gd = S('gold', 'lms', v=0.3, tag='bw'); sp = S('spar', 'lm', tag='bw'); ir = S('iron', 'lm', tag='bw')
    dk = S('duck', 'lms', v=0.15, tag='bw'); bk = S('black', 'lm', tag='bw'); org = S('red', 'lm', tag='bw')
    pts = []
    for z in np.linspace(-272, L.FC_Z + 20, 16):
        pts.append(np.array([L.ship_bow_x(z) + 2, 0, z]))
    pts.append(np.array([L.ship_bow_x(L.FC_Z + 20) + 24, 0, L.FC_Z + 44]))
    tube(X.mesh(rl), pts, np.linspace(9, 12, len(pts)), nseg=8, vlen=96)
    # figurehead: a rubber duck leaning out under the bowsprit
    bx = L.ship_bow_x(170) + 34
    ellipsoid(X.mesh(dk), (bx, 0, 170), 36, 24, 22, nu=16, nv=10, R=rot_axis((0, 1, 0), -0.35))
    sphere(X.mesh(dk), (bx + 34, 0, 206), 19, nu=14, nv=8)
    ellipsoid(X.mesh(org), (bx + 56, 0, 202), 12, 8, 4, nu=10, nv=5)
    for s in (-1, 1):
        sphere(X.mesh(bk), (bx + 47, s * 11, 214), 3.5, nu=6, nv=4)
    tube(X.mesh(gd), [(bx - 30, 0, 150), (bx - 50, 0, 140), (L.ship_bow_x(140), 0, 140)], 6, nseg=8)
    # bowsprit and jib boom
    b0 = np.array([L.FC_X + 120, 0, L.FC_Z + 22])
    d = np.array([math.cos(math.radians(22)), 0, math.sin(math.radians(22))])
    tube(X.mesh(sp), [b0, b0 + d * 180, b0 + d * 300], [11, 10, 8], nseg=10, vlen=128)
    tube(X.mesh(sp), [b0 + d * 260, b0 + d * 380], [6, 4.5], nseg=8, vlen=128)
    for k in (150, 270):
        rbox(X.mesh(ir), tuple(b0 + d * k - [5, 13, 13]), tuple(b0 + d * k + [5, 13, 13]), r=2, tile=32)
    # catheads and the anchor hanging on the starboard bow
    for s in (-1, 1):
        x = 420; z = L.FC_Z + 18
        w = L.ship_halfbeam(x, z)
        rbox(X.mesh(rl), (x - 8, min(s * (w - 10), s * (w + 34)), z - 8), (x + 8, max(s * (w - 10), s * (w + 34)), z + 8), r=2, tile=32)
    ax, az = 420.0, L.FC_Z + 6
    ay = -(L.ship_halfbeam(ax, 60) + 26)
    tube(X.mesh(ir), [(ax, ay, az), (ax, ay, az - 150)], 4, nseg=8)                       # shank
    tube(X.mesh(ir), [(ax - 46, ay, az - 128), (ax - 20, ay, az - 156), (ax, ay, az - 162), (ax + 20, ay, az - 156), (ax + 46, ay, az - 128)], 4.5, nseg=8)
    for sx in (-1, 1):
        cone_pts = [(ax + sx * 46, ay, az - 128), (ax + sx * 52, ay, az - 112)]
        tube(X.mesh(ir), cone_pts, [7, 0.5], nseg=6)
    tube(X.mesh(sp), [(ax - 30, ay, az - 14), (ax + 30, ay, az - 14)], 4, nseg=6)
    torus_ring = Mesh(); revolve(torus_ring, [(8, -2), (10, 0), (8, 2), (6, 0), (8, -2)], n=12, vlen=16)
    X.mesh(ir).add(torus_ring, rot_axis((1, 0, 0), math.pi / 2), (ax, ay, az + 8))


def deck_details(X):
    """hatch coaming, door frames on the castle fronts, cabin sign, belaying rails"""
    rl = S('rail', 'lm', tag='dd'); gd = S('gold', 'lms', v=0.25, tag='dd'); ir = S('iron', 'lm', tag='dd')
    hx = L.HATCH
    for (a, b) in (((hx[0] - 6, hx[1] - 6), (hx[2] + 6, hx[1])), ((hx[0] - 6, hx[3]), (hx[2] + 6, hx[3] + 6)), ((hx[0] - 6, hx[1]), (hx[0], hx[3]))):
        rbox(X.mesh(rl), (a[0], a[1], L.WAIST_Z), (b[0], b[1], L.WAIST_Z + 3), r=0.5, tile=64)
    for (xf, h, sgn) in ((L.QD_X, L.CABIN_DOOR_H, 1), (L.FC_X, L.CREW_DOOR_H, -1)):
        x0 = xf + sgn * 0.5
        for s in (-1, 1):
            rbox(X.mesh(gd), (min(x0, x0 + sgn * 4), s * L.DOOR_HW - 4 if s > 0 else -L.DOOR_HW - 4, L.WAIST_Z),
                 (max(x0, x0 + sgn * 4), L.DOOR_HW + 4 if s > 0 else -L.DOOR_HW + 4, L.WAIST_Z + h + 4), r=1, tile=32)
        rbox(X.mesh(gd), (min(x0, x0 + sgn * 4), -L.DOOR_HW - 4, L.WAIST_Z + h), (max(x0, x0 + sgn * 4), L.DOOR_HW + 4, L.WAIST_Z + h + 6), r=1, tile=32)
    # belaying-pin rails inside the waist bulwarks
    for s in (-1, 1):
        y = s * (L.CW - L.BULW_T - 4)
        for x0 in (-300, 100):
            rbox(X.mesh(rl), (x0, min(y, y - s * 6), L.WAIST_Z + 26), (x0 + 120, max(y, y - s * 6), L.WAIST_Z + 30), r=1, tile=32)
            for k in range(8):
                xx = x0 + 8 + k * 15
                tube(X.mesh(ir if k % 2 else rl), [(xx, y - s * 3, L.WAIST_Z + 22), (xx, y - s * 3, L.WAIST_Z + 38)], 1.4, nseg=5)


def decks_mesh(X):
    """decks, castle fronts, interiors, bulwark/rail inner faces and stairs from the collision solids"""
    sd = S(BT('deck'), 'lm', shade=20, tag='sd'); sw = S('panel', 'lm', shade=20); sk = S('panel_dark', 'lm', shade=20)
    sb = S('beams', 'lm', shade=20); sr = S('rail', 'lm', shade=20); sh = S('panel_dark', 'lm', shade=20, tag='h')
    hull_b = SH.ship_hull(); rails = SH.ship_rails(); stairs = SH.ship_stairs()
    allb = hull_b + rails + stairs
    def coll_w(x):
        for a, b in zip(L.ship_stations(), L.ship_stations()[1:]):
            if a <= x <= b: return L.ship_coll_halfbeam(a, b, L.ship_deck_z((a + b) / 2))
        return 0.0

    def texfn(c, n, poly):
        x, y, z = c[0] - SX, c[1] - SY, c[2]
        q = c + n * 2
        room = SH.in_ship_room(q, 0.0)
        if n[2] > 0.9:                                    # walkable tops
            top_rail = abs(z - L.ship_sheer(x)) < 0.6 and abs(y) > coll_w(x) - L.BULW_T - 0.6
            if top_rail and abs(x - L.QD_X + 8) > 9 and abs(x - L.FC_X - 8) > 9: return None     # under the skin's cap strip
            if abs(z - L.ship_sheer(x)) < 0.6 or (z > L.WAIST_Z + 1 and abs(z - (L.ship_deck_z(x) + L.RAIL_H)) < 0.6): return sr, planar_uv(n, 64)
            return sd, planar_uv(n, 256)
        if n[2] < -0.9:
            if room in ('hold', 'cabin', 'crew', 'door', 'hatch') or z > 1: return sb, planar_uv(n, 256)
            return None
        if room in ('hold',): return sh, planar_uv(n, 256)
        if room in ('cabin', 'crew', 'door'): return sw, planar_uv(n, 256)
        if room == 'hatch': return sb, planar_uv(n, 128)
        # side walls: outer faces hidden by the skin
        if abs(n[1]) > 0.7 and n[1] * y > 0 and abs(y) > 40: return None
        if abs(n[0]) > 0.7:
            if z > L.WAIST_Z + 0.5 and (abs(x - L.QD_X) < 1 or abs(x - L.FC_X) < 1 or abs(x - (L.QD_X - 16)) < 1 or abs(x - (L.FC_X + 16)) < 1):
                return sk, planar_uv(n, 256)
            if z > L.WAIST_Z + 0.5 and abs(y) < L.STAIR_Y[1] + 1: return sk, planar_uv(n, 128)       # stair risers / rail ends
            if abs(x - L.SHIP_STERN) < 1: return None
            return None
        # bulwark / rail inner faces, stair sides
        return sk, planar_uv(n, 128)
    solids_mesh(X, allb, texfn)


def make_hull():
    X = Model()
    Mh = X.mesh(S('hull', 'lm', shade=60))
    xs_st = list(np.arange(L.SHIP_STERN, L.QD_X, 20)) + [L.QD_X]
    xs_w = list(np.arange(L.QD_X, L.FC_X, 20)) + [L.FC_X]
    bx = L.ship_bow_x(L.FC_Z + L.RAIL_H)
    xs_b = list(np.arange(L.FC_X, bx, 12)) + [bx]
    skin_section(Mh, xs_st, L.QD_Z + L.RAIL_H)
    skin_section(Mh, xs_w, L.WAIST_Z + L.BULW_H)
    skin_section(Mh, xs_b, L.FC_Z + L.RAIL_H)
    cap = X.mesh(S('rail', 'lm', shade=30, tag='cap'))
    rail_cap(cap, xs_st, L.QD_Z + L.RAIL_H); rail_cap(cap, xs_w, L.WAIST_Z + L.BULW_H); rail_cap(cap, xs_b, L.FC_Z + L.RAIL_H)
    stem_fill(Mh, cap)
    # transom rail cap
    w = L.ship_halfbeam(L.SHIP_STERN, L.QD_Z + L.RAIL_H)
    zt = L.QD_Z + L.RAIL_H + 0.4
    cap.poly([np.array([L.SHIP_STERN, -w, zt]), np.array([L.SHIP_STERN + L.BULW_T, -w, zt]), np.array([L.SHIP_STERN + L.BULW_T, w, zt]),
              np.array([L.SHIP_STERN, w, zt])], (0, 0, 1), [(0, 0), (0.1, 0), (0.1, 4), (0, 4)])
    transom(X); gunports(X); wales(X); bow(X); deck_details(X)
    D = Model()
    decks_mesh(D)
    D.shift((SX, SY, 0))
    X.add_model(D)
    # split into aft and fore MD3s at SPLIT_X (ship-relative); origins on the centre line
    A_, B_ = Model(), Model()
    for sh, Mm in X.m.items():
        V = np.array(Mm.V); Tt = np.array(Mm.T)
        if not len(Tt): continue
        cxs = V[Tt].mean(1)[:, 0]
        for part, sel in ((A_, cxs < SPLIT_X), (B_, cxs >= SPLIT_X)):
            idx = np.where(sel)[0]
            if not len(idx): continue
            used = np.unique(Tt[idx].ravel()); remap = {v: i for i, v in enumerate(used)}
            mm = part.mesh(sh)
            o = len(mm.V)
            for v in used: mm.add_v(Mm.V[v], Mm.N[v], Mm.ST[v])
            for t in Tt[idx]: mm.T.append(tuple(o + remap[v] for v in t))
    A_.shift((HULL_ORIGIN['aft'], 0, 0)); B_.shift((HULL_ORIGIN['fore'], 0, 0))
    save('ship_aft', A_); save('ship_fore', B_)


HULL_ORIGIN = {'aft': -340.0, 'fore': 320.0}


# ================================================================================================= masts, yards, sails, rigging
def mast(name, key, yards, top=None, nest=False, flag=None):
    """one mast with its yards (furled sails), a top platform, shrouds down to the chainplates, a flag; origin at the
    mast foot on its deck"""
    X = Model()
    x0, zdeck, h, r = L.MASTS[key]
    sp = S('spar', 'lm', shade=70, tag=name); cv = S('canvas', 'lm', shade=70, tag=name); nt = S('net', 'alpha', tag=name)
    ir = S('iron', 'lm', tag=name); rope = S(BT('rope'), 'lm', tag=name); rl = S('rail', 'lm', tag=name)
    H = h
    tube(X.mesh(sp), [(0, 0, 0), (0, 0, H * 0.55), (0, 0, H)], [r, r * 0.8, r * 0.45], nseg=12, vlen=128)
    for k in range(int(H // 90)):
        z = 60 + k * 90
        if z > H - 30: break
        rr = r * (1 - 0.55 * z / H) + 1.5
        cyl_m = Mesh(); revolve(cyl_m, [(rr, z - 3), (rr, z + 3)], n=12, vlen=16)
        X.mesh(ir).add(cyl_m)
    for (zy, half, rr) in yards:
        tube(X.mesh(sp), [(4, -half, zy), (6, 0, zy), (4, half, zy)], [rr * 0.5, rr, rr * 0.5], nseg=8, vlen=128)
        # the furled sail: a fat lumpy roll tied along the yard
        pts = [np.array([10, yy, zy - rr - 4 - 6 * math.cos(yy / half * math.pi / 2)]) for yy in np.linspace(-half * 0.92, half * 0.92, 14)]
        rad = [7 + 8 * math.cos(t * math.pi / 2) for t in np.linspace(-1, 1, 14)]
        tube(X.mesh(cv), pts, rad, nseg=10, vlen=64)
        for yy in np.linspace(-half * 0.8, half * 0.8, 6):
            c = np.array([10, yy, zy - rr - 4 - 6 * math.cos(yy / half * math.pi / 2)])
            rad_ = 7 + 8 * math.cos(yy / half * math.pi / 2) + 1
            tor = Mesh(); revolve(tor, [(rad_, -1.5), (rad_ + 1.2, 0), (rad_, 1.5)], n=10, vlen=8)
            X.mesh(rope).add(tor, rot_axis((1, 0, 0), math.pi / 2), c)
    if top is not None:
        zt, rt = top
        cylm = Mesh(); revolve(cylm, [(0, zt - 12), (rt, zt - 12), (rt, zt), (0, zt)], n=16, vlen=64)
        X.mesh(rl).add(cylm)
    if nest:
        zt = L.NEST_Z - zdeck
        R = L.NEST_R
        P = Mesh(); revolve(P, [(0, zt - 16), (R, zt - 16), (R, zt), (r + 1, zt)], n=32, vlen=128)
        X.mesh(S(BT('deck'), 'lm', tag='nest')).add(P)
        # barrel-stave basket round the rim (rail collision is 36 high)
        bs = S('rail', 'lm', shade=60, tag='nestb')
        prof = [(R - 8, zt), (R + 1, zt), (R + 4, zt + 18), (R + 1, zt + 38), (R - 8, zt + 38), (R - 9, zt + 18)]
        bm = Mesh(); revolve(bm, prof + [prof[0]], n=40, vlen=48, u_tiles=20)
        X.mesh(bs).add(bm)
        for zz in (zt + 6, zt + 31):
            hm = Mesh(); revolve(hm, [(R + 3.5, zz - 2.5), (R + 4.5, zz), (R + 3.5, zz + 2.5)], n=40, vlen=16)
            X.mesh(ir).add(hm)
        # supports under the platform
        for k in range(8):
            a = 2 * math.pi * k / 8
            tube(X.mesh(sp), [(r * math.cos(a), r * math.sin(a), zt - 120), ((R - 20) * math.cos(a), (R - 20) * math.sin(a), zt - 16)], 3.5, nseg=6)
    # shrouds: ratline nets from the hull sides up to the top / below the lowest yard
    hz = (top[0] if top else (L.NEST_Z - zdeck if nest else H * 0.6)) - 2
    for s in (-1, 1):
        wdeck = L.ship_halfbeam(x0, zdeck + 30) + 6
        base_z = (L.ship_sheer(x0) - zdeck) - 2
        for (xa, xb) in ((-34, 30),):
            p0 = np.array([xa, s * wdeck, base_z]); p1 = np.array([xb, s * wdeck, base_z])
            p2 = np.array([xb * 0.2, s * (r + 12), hz]); p3 = np.array([xa * 0.2, s * (r + 12), hz])
            nn = np.cross(p1 - p0, p3 - p0); nn /= np.linalg.norm(nn)
            ln = np.linalg.norm(p3 - p0)
            X.mesh(nt).poly([p0, p1, p2, p3], nn, [(0, ln / 40), (1.6, ln / 40), (1.6 * 0.3, 0), (0, 0)])
            for (pa, pb) in ((p0, p3), (p1, p2)):
                tube(X.mesh(rope), [pa, pb], 1.6, nseg=5, caps=(False, False))
            # deadeyes / chainplate on the hull side
            rbox(X.mesh(rl), (xa - 4, s * wdeck - 4, base_z - 8), (xb + 4, s * wdeck + 4, base_z + 2), r=1, tile=32)
    if flag:
        fz = H - 4
        fl = S('jolly', 'flag', div=60, amp=5, freq=0.9)
        w, hgt = flag
        tube(X.mesh(sp), [(0, 0, H - 2), (0, 0, H + 26)], 2, nseg=6)
        P = [np.array([2, 0, H + 24 - hgt]), np.array([2 - w, 0, H + 24 - hgt]), np.array([2 - w, 0, H + 24]), np.array([2, 0, H + 24])]
        X.mesh(fl).poly(P, (0, -1, 0), [(1, 1), (0, 1), (0, 0), (1, 0)])
        X.mesh(fl).poly(P[::-1], (0, 1, 0), [(1, 0), (0, 0), (0, 1), (1, 1)])
    return save(name, X)


def stays(X):
    """fore-and-aft stays between the mast tops and the bowsprit (one model in ship coordinates, origin midship)"""
    rope = S(BT('rope'), 'lm', tag='stay')
    fx, fz0, fh, _ = L.MASTS['fore']; mx, mz0, mh, _ = L.MASTS['main']; zx, zz0, zh, _ = L.MASTS['mizzen']
    b0 = np.array([L.FC_X + 120, 0, L.FC_Z + 22]); d = np.array([math.cos(math.radians(22)), 0, math.sin(math.radians(22))])
    for (a, b) in (((fx, 0, fz0 + fh * 0.85), tuple(b0 + d * 300)), ((fx, 0, fz0 + fh * 0.6), tuple(b0 + d * 160)),
                   ((mx, 0, mz0 + mh * 0.9), (fx, 0, fz0 + fh * 0.7)), ((zx, 0, zz0 + zh * 0.9), (mx, 0, mz0 + mh * 0.62)),
                   ((zx, 0, zz0 + zh * 0.75), (L.SHIP_STERN + 30, 0, L.QD_Z + L.RAIL_H))):
        a = np.array(a, float); b = np.array(b, float)
        mid = (a + b) / 2 - [0, 0, 10]
        tube(X.mesh(rope), [a, mid, b], 1.8, nseg=5, caps=(False, False))
    return save('ship_stays', X)


def make():
    make_textures()
    make_hull()
    mast('mast_main', 'main', [(330, 230, 7), (630, 160, 5.5)], top=None, nest=True, flag=(150, 94))
    mast('mast_fore', 'fore', [(250, 200, 6), (500, 140, 5)], top=(330, 56), flag=None)
    mast('mast_mizzen', 'mizzen', [(240, 150, 5), (470, 110, 4)], top=(300, 48), flag=None)
    stays(Model())
