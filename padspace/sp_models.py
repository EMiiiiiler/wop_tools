"""Custom MD3 architecture for wop_padspace (Starsplash Station): the rocket, the lunar lander, Planet Padurn, the
satellite dive tower, the buildings of Star Boulevard, the habitat pods, the Zero-G Loo and both slides. All geometry
and art is original and generated here. Props and movers live in sp_props.py.

Scale ~32u per metre. Architecture is drawn from the convex solids in sp_shapes.py, so the weapclip collision in
build_space.py matches the visible surfaces."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube as _tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from splib import *
import splib
import layout as L
import sp_shapes as SH

TXD = 'textures/padspace/'


def BT(name): return TXD + name


# ================================================================================================= mesh helpers
def tube(M, path, radii, **kw):
    path = np.asarray(path, float)
    r = np.atleast_1d(np.asarray(radii, float))
    if len(r) > 1 and len(r) != len(path):
        r = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(r)), r)
    _tube(M, path, r, **kw)


def cylm(M, c, r, h, n=16, caps=True, tile=128.0):
    c = np.asarray(c, float)
    revolve(M, [(0, c[2]), (r, c[2]), (r, c[2] + h), (0, c[2] + h)] if caps else [(r, c[2]), (r, c[2] + h)], n=n, cx=c[0], cy=c[1], vlen=tile)


def boxm(M, mn, mx, r=1.0, tile=64.0, k=1, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def torus(M, c, R, r, axis=(0, 0, 1), n=32, m=10, utile=4.0):
    c = np.asarray(c, float); ax = np.asarray(axis, float); ax /= np.linalg.norm(ax)
    b1, b2 = frame(ax)
    path = [c + (b1 * math.cos(t) + b2 * math.sin(t)) * R for t in np.linspace(0, 2 * math.pi, n + 1)]
    _tube(M, np.array(path), np.full(n + 1, r), nseg=m, caps=(False, False), utiles=1, vlen=2 * math.pi * R / utile)


def cone(M, base, tip, r, n=8):
    base = np.asarray(base, float); tip = np.asarray(tip, float)
    _tube(M, np.array([base, base + (tip - base) * 0.5, tip]), np.array([r, r * 0.55, 0.3]), nseg=n, caps=(True, False))


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture(M, c, w, h, nrm, up=(0, 0, 1)):
    """textured quad centred at c facing nrm, u left->right as seen from the front (text reads correctly)"""
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm); up = np.asarray(up, float)
    right = np.cross(up, nrm); right /= np.linalg.norm(right)
    upv = np.cross(nrm, right)
    p = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2, c - right * w / 2 + upv * h / 2]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name


def sweep(M, path, prof, closed=False, vlen=128.0, inward=False, utile=1.0):
    P0 = np.asarray(path, float)
    n = len(P0)
    Tg = np.gradient(P0, axis=0)
    Th = Tg[:, :2] / np.maximum(np.linalg.norm(Tg[:, :2], axis=1, keepdims=True), 1e-9)
    lat = np.stack([-Th[:, 1], Th[:, 0], np.zeros(n)], 1)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P0, axis=0), axis=1))])
    pr = list(prof) + ([prof[0]] if closed else [])
    m = len(pr)
    P = np.zeros((n, m, 3)); UV = np.zeros((n, m, 2))
    cl = np.concatenate([[0], np.cumsum([math.hypot(pr[k + 1][0] - pr[k][0], pr[k + 1][1] - pr[k][1]) for k in range(m - 1)])])
    for i in range(n):
        for j, (u, v) in enumerate(pr):
            P[i, j] = P0[i] + lat[i] * u + np.array([0, 0, v])
            UV[i, j] = (cl[j] / max(cl[-1], 1e-6) * utile, Ls[i] / vlen)
    N = grid_normals(P)
    cu = np.mean([p[0] for p in prof]); cv = np.mean([p[1] for p in prof])
    cen = P0[:, None, :] + lat[:, None, :] * cu + np.array([0, 0, cv])
    if ((N * (P - cen)).sum(-1) < 0).mean() > 0.5: N = -N
    if inward: N = -N
    M.grid(P, N, UV)
    return P


def circle_prof(r, n=16):
    return [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def densify(path, step=40.0):
    out_ = [np.asarray(path[0], float)]
    for a, b in zip(path, path[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        k = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for t in np.linspace(0, 1, k + 1)[1:]: out_.append(a + (b - a) * t)
    return out_


def SB(img, shade=30, **kw):
    """architecture shader on a brush texture image"""
    return S(BT(img), 'lm', shade=shade, **kw)


def radial(c, n):
    """normal points away from the vertical axis through c"""
    d = np.array([n[0], n[1]])
    return d


# ================================================================================================= model textures
def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((40, 30, 80)), C((220, 226, 250)), np.clip(1 - y * 1.3, 0, 1)[..., None])
    st = np.random.default_rng(seed).random((n, n)) > 0.985
    return np.where(st[..., None], C((255, 255, 255)), c + N3(n, 8, seed, 14))


def tex_panels(n=256, seed=1, base=(236, 238, 244), seam=(150, 156, 168), rows=4, cols=4):
    x, y = xy(n)
    rng = np.random.default_rng(seed)
    k = (np.floor(x * cols) + cols * np.floor(y * rows)).astype(int)
    c = np.zeros((n, n, 3), np.float32) + C(base) + rng.uniform(-7, 7, rows * cols + 1)[k][..., None] + N3(n, 0.6, seed, 3)
    u = (x * cols) % 1; v = (y * rows) % 1
    sm = (np.minimum(u, 1 - u) < 0.012) | (np.minimum(v, 1 - v) < 0.012)
    return np.where(sm[..., None], C(seam), c)


def rocket_skin(rows, W=1024, H=2048):
    """the rocket's outer skin, painted by height: grey skirt with a hazard band, black/white roll pattern, white body
    with PADSTAR lettering and a star band, a red nose with a white ring. v follows the profile arc length (0..1)."""
    rows = np.asarray(rows, float)
    Ls = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=1))])
    vz = np.interp(np.linspace(0, Ls[-1], H), Ls, rows[:, 1])          # z for each image row
    x = (np.arange(W) + 0.5) / W
    Z = np.repeat(vz[:, None], W, 1); U = np.repeat(x[None, :], H, 0)
    c = np.zeros((H, W, 3), np.float32) + C((238, 240, 246)) + N3(W, 0.8, 3, 3, H)
    # panel seams: horizontal every 80u, vertical every 1/16 turn
    c = np.where(((Z % 80) < 1.6)[..., None], C((170, 176, 188)), c)
    c = np.where((((U * 16) % 1) < 0.006)[..., None], C((176, 182, 194)), c)
    sk = Z < 140
    c = np.where(sk[..., None], C((150, 156, 166)) + N3(W, 0.8, 5, 4, H), c)
    hz = (Z < 30) & ((((U * 64) + Z / 40) % 1) < 0.5)
    c = np.where(hz[..., None], C((240, 200, 30)), c)
    c = np.where(((Z < 30) & ~hz)[..., None], C((30, 30, 32)), c)
    roll = (Z >= 140) & (Z < 300)
    q = (np.floor(U * 4) + np.floor((Z - 140) / 80)) % 2 == 0
    c = np.where((roll & q)[..., None], C((26, 26, 30)), c)
    c = np.where(((Z >= 296) & (Z < 312))[..., None], C((200, 36, 36)), c)
    # star band
    band = (Z >= 630) & (Z < 680)
    c = np.where(band[..., None], C((30, 50, 140)), c)
    rng = np.random.default_rng(9)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    rz = lambda z: int(np.interp(z, vz, np.arange(H)))
    for _ in range(60):
        px = rng.uniform(0, W); pz = rng.uniform(636, 674)
        d.ellipse((px - 2, rz(pz) - 3, px + 2, rz(pz) + 3), fill=(255, 255, 240))
    # nose: red, with a white ring
    c = np.asarray(im, np.float32)
    nose = Z >= L.RK_BODY_TOP
    c = np.where(nose[..., None], C((210, 36, 40)) + N3(W, 0.8, 7, 4, H), c)
    c = np.where(((Z > 880) & (Z < 905))[..., None], C((240, 240, 244)), c)
    c = np.where(((Z > 676) & (Z < L.RK_BODY_TOP))[..., None], C((60, 64, 74)), c)
    # lettering: PADSTAR on the south (u 0.75) and north (u 0.25) faces, reading upward along the body
    circ = 2 * math.pi * L.RK_R
    for uc in (0.75, 0.25):
        tw, th = 620.0, 84.0                                  # world size of the text block
        pw = int(tw / circ * W); r0, r1 = rz(470), rz(470 + th)
        ph = max(8, r1 - r0)
        t = text_img('PADSTAR', 1240, 168, (238, 240, 246), (30, 36, 60), False)
        t = np.asarray(img(t).resize((pw, ph)), np.float32)[::-1]       # rows run upward on the rocket
        x0 = int(uc * W - pw / 2)
        c[r0:r0 + ph, x0:x0 + pw] = t
        # a red "I" below
        t2 = text_img('I', 200, 168, (238, 240, 246), (200, 36, 36), False)
        p2w = int(70 / circ * W); a0, a1 = rz(380), rz(450)
        t2 = np.asarray(img(t2).resize((p2w, a1 - a0)), np.float32)[::-1]
        c[a0:a1, int(uc * W - p2w / 2):int(uc * W - p2w / 2) + p2w] = t2
    return c, Ls[-1]


def tex_bands(n=256, cols=((200, 140, 80), (240, 210, 160), (170, 100, 60), (230, 190, 130)), seed=3, k=11, wob=0.08):
    x, y = xy(n)
    t = y * k + np.sin(x * 2 * math.pi * 2 + y * 6) * wob * k + noise(n, 8, seed) * 0.15
    idx = np.floor(t).astype(int) % len(cols)
    c = np.array(cols, np.float32)[idx]
    f = (t % 1)
    c = c * (0.85 + 0.15 * np.sin(f * math.pi))[..., None]
    return c + N3(n, 1, seed + 1, 5)


def tex_ring(w=64, h=256, seed=5):
    """planet ring: radial bands (v = radius), gaps"""
    x, y = xy(w, h)
    r = np.random.default_rng(seed)
    t = y * 22
    base = np.array([(226, 206, 170), (190, 166, 130), (240, 226, 200), (160, 140, 110)], np.float32)[np.floor(t).astype(int) % 4]
    gap = (np.abs(y - 0.62) < 0.02) | (np.abs(y - 0.2) < 0.01)
    c = np.where(gap[..., None], C((70, 60, 70)), base)
    return c + N3(w, 1, seed, 6, h)


def tex_ice(n=128, seed=7):
    c = fill(n, (230, 240, 250), 4, seed) + N3(n, 3, seed + 1, 10)
    cr = np.clip(np.abs(noise(n, 2, seed + 2)) < 0.04, 0, 1)
    return c * (1 - cr * 0.2)[..., None]


def tex_crystal(n=64, seed=9, col=(170, 90, 255)):
    x, y = xy(n)
    return np.zeros((n, n, 3), np.float32) + C(col) * (0.7 + 0.3 * y)[..., None] + N3(n, 2, seed, 10)


def tex_hazard(n=64):
    x, y = xy(n)
    s = ((x + y) * 4 % 1) < 0.5
    return np.where(s[..., None], C((240, 200, 30)), C((30, 30, 32))) + N3(n, 0.6, 3, 4)


def tex_screen(w=512, h=256, seed=11):
    """mission control wall screen: dark blue map of the park's orbit, trajectory, numbers"""
    im = Image.new('RGB', (w, h), (8, 20, 40)); d = ImageDraw.Draw(im)
    for k in range(0, w, 32): d.line([(k, 0), (k, h)], fill=(16, 40, 70))
    for k in range(0, h, 32): d.line([(0, k), (w, k)], fill=(16, 40, 70))
    d.ellipse((60, 60, 200, 200), outline=(80, 200, 255), width=3); d.ellipse((110, 110, 150, 150), fill=(60, 120, 220))
    pts = [(130 + 140 * math.cos(t), 130 + 60 * math.sin(t) - t * 4) for t in np.linspace(0, 9, 80)]
    d.line(pts, fill=(255, 200, 60), width=3)
    d.ellipse((380, 40, 470, 130), fill=(210, 160, 90)); d.ellipse((350, 78, 500, 92), outline=(230, 210, 170), width=2)
    f = font(22, False)
    for i, tx in enumerate(('T-00:42  GO', 'FUEL 98%', 'DUCKS 7/7', 'SPLASH OK')):
        d.text((250, 150 + i * 24), tx, font=f, fill=(120, 255, 160))
    return np.asarray(im, np.float32)


def tex_console(w=256, h=128, seed=13):
    im = Image.new('RGB', (w, h), (50, 54, 64)); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for i in range(14):
        x, y = r.uniform(10, w - 20), r.uniform(10, h - 20)
        col = [(255, 60, 60), (60, 255, 120), (255, 210, 40), (80, 180, 255)][i % 4]
        d.ellipse((x, y, x + 9, y + 9), fill=col)
    d.rectangle((20, 20, 110, 80), fill=(10, 30, 20)); d.line([(24, 60), (50, 30), (70, 55), (106, 26)], fill=(90, 255, 120), width=2)
    for i in range(4): d.rectangle((140 + i * 24, 70, 156 + i * 24, 110), fill=(30, 30, 34), outline=(150, 150, 160))
    return np.asarray(im, np.float32)


def tex_solar(n=128):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((30, 50, 120))
    g = ((x * 8) % 1 < 0.05) | ((y * 8) % 1 < 0.05)
    return np.where(g[..., None], C((190, 196, 210)), c + N3(n, 4, 3, 12))


def tex_flag(w=256, h=160):
    """the Padman space flag: navy with a golden duck-rocket and stars"""
    im = Image.new('RGB', (w, h), (24, 30, 90)); d = ImageDraw.Draw(im)
    d.ellipse((80, 40, 176, 136), fill=(250, 210, 50)); d.ellipse((150, 30, 196, 76), fill=(250, 210, 50))
    d.polygon([(190, 50), (222, 58), (190, 66)], fill=(250, 140, 30)); d.ellipse((168, 42, 178, 52), fill=(20, 20, 20))
    r = np.random.default_rng(4)
    for _ in range(14):
        x, y = r.uniform(5, w - 5), r.uniform(5, h - 5)
        d.text((x, y), '*', fill=(255, 255, 255))
    return np.asarray(im, np.float32)


def tex_comet(w=64, h=256):
    x, y = xy(w, h)
    a = np.exp(-((x - 0.5) / (0.08 + 0.35 * y)) ** 2) * (1 - y) ** 1.5
    return np.zeros((h, w, 3), np.float32) + (a * 255)[..., None] * C((0.6, 0.9, 1.0))


def tex_portal(n=256):
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy) * 2; a = np.arctan2(dy, dx)
    s = np.sin(a * 4 + np.log(rr + 0.05) * 6) * 0.5 + 0.5
    c = lerp(C((120, 40, 255)), C((80, 240, 255)), s[..., None]) * np.clip(1.1 - rr, 0, 1)[..., None]
    return c


def tex_tire(n=128):
    x, y = xy(n)
    c = fill(n, (36, 36, 40), 3, 9)
    return np.where((((x * 16) % 1) < 0.3)[..., None], c * 0.6, c)


def make_textures():
    T('env', tex_env())
    T('panels', tex_panels()); T('panels_d', tex_panels(256, 3, (70, 74, 86), (40, 42, 50))); T('panels_g', tex_panels(256, 5, (190, 196, 206), (120, 124, 136), 2, 2))
    T('white', fill(64, (238, 238, 242), 3, 56)); T('black', fill(64, (20, 20, 24), 2, 55)); T('red', fill(64, (200, 36, 40), 4, 57))
    T('metal', fill(64, (150, 156, 168), 4, 53) + N3(64, 0.5, 54, 6)); T('metal_d', fill(64, (64, 66, 76), 4, 58)); T('orange', fill(64, (245, 130, 30), 4, 67))
    T('gold', tex_bands(64, ((214, 168, 60), (236, 196, 90)), 61, 6, 0.3)); T('blue', fill(64, (40, 90, 200), 4, 62)); T('yellow', fill(64, (250, 204, 40), 4, 68))
    T('bands', tex_bands()); T('bands_g', tex_bands(256, ((90, 160, 120), (150, 220, 170), (60, 120, 100)), 5, 9))
    T('bands_p', tex_bands(256, ((160, 80, 200), (220, 160, 240), (110, 60, 160)), 7, 7)); T('ring', tex_ring()); T('ice', tex_ice())
    T('crystal', tex_crystal()); T('crystal_c', tex_crystal(64, 10, (60, 220, 255))); T('crystal_g', tex_crystal(64, 12, (120, 255, 120)))
    T('hazard', tex_hazard()); T('screen', tex_screen()); T('console', tex_console()); T('solar', tex_solar()); T('flag', tex_flag())
    T('comet', tex_comet()); T('portal', tex_portal()); T('tire', tex_tire())
    for nm, col in (('glow_c', (90, 240, 255)), ('glow_m', (255, 80, 210)), ('glow_y', (255, 220, 90)), ('glow_g', (140, 255, 120)),
                    ('glow_w', (255, 250, 240)), ('glow_r', (255, 60, 50)), ('glow_v', (170, 100, 255)), ('glow_o', (255, 150, 40))):
        T(nm, fill(32, col, 2, hash(nm) % 97))
    T('rock_m', fill(128, (130, 128, 132), 10, 69) + N3(128, 3, 70, 14))
    T('slide_in', fill(128, (120, 200, 255), 4, 73) + N3(128, 6, 74, 6))
    T('tube_p', tex_bands(128, ((90, 40, 170), (120, 60, 210)), 75, 4, 0.0))
    x, y = xy(64, 256)
    st = np.asarray(img(noise(64, 0.8, 37, 256) * 60 + 128).resize((64, 16)).resize((64, 256)), np.float32) / 255
    a = np.clip(0.35 + (st - 0.5) * 1.6, 0, 1) * np.clip(1 - np.abs(x - 0.5) * 1.6, 0, 1)
    T('water_strip', np.zeros((256, 64, 3), np.float32) + C((160, 230, 255)) + (st * 50)[..., None], a * 255)


# ================================================================================================= the rocket
def rocket():
    """the hollow rocket: carved shell (door, portholes, balcony doors, panorama window), interior stair and decks,
    the balcony ring, fins, porthole rims, consoles and seats are props. Origin = base centre."""
    X = Model()
    cx, cy = L.RK
    rows = L.rk_rows()
    skin, Ltot = rocket_skin(rows)
    T('rocket_skin', skin)
    out_sh = S('rocket_skin', 'lm', shade=80); in_sh = SB('panel_w', 60, tag='rki'); jam_sh = S('metal_d', 'lm', shade=50, tag='rkj')
    carved_shell(X.mesh(out_sh), X.mesh(in_sh), X.mesh(jam_sh), rows, 96, L.RK_T, L.rk_open_polys(), L.RK_FACE, L.RK_RR,
                 u_tiles=1, vlen=Ltot, close_top=False, depth=3, jstep=8)
    # interior: stair (grating treads, dark sides), decks (plate on top, panels underneath)
    tr = SB('plate', 30, tag='rkt'); sd = SB('panel_d', 30, tag='rks'); un = SB('panel_w', 30, tag='rku'); cp = SB('carpet', 30, tag='rkc')
    def tf_int(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if n[2] > 0.9: return (cp if c[2] > L.COCK_Z - 2 else tr), planar_uv(n, 128)
        if n[2] < -0.9: return un, planar_uv(n, 128)
        return sd, planar_uv(n, 128)
    I = Model()
    solids_mesh(I, SH.rocket_interior(), tf_int)
    # balcony: plate top, red edge, hidden inner face dropped
    bt = SB('plate', 30, tag='rkb'); be = SB('panel_red', 30, tag='rkb')
    def tf_balc(c, n, poly):
        d = np.array([c[0] - cx, c[1] - cy]); d /= max(1e-6, np.linalg.norm(d))
        if abs(n[2]) < 0.3 and (n[0] * d[0] + n[1] * d[1]) < -0.8 and math.hypot(c[0] - cx, c[1] - cy) < L.BALC_R0 + 4: return None
        if n[2] > 0.9: return bt, planar_uv(n, 128)
        return be, planar_uv(n, 128)
    solids_mesh(I, [b for b in SH.rocket_balcony() if b.part == 'balcony'], tf_balc)
    # fins: red panels with a white leading edge band
    fin = SB('panel_red', 40, tag='rkf')
    def tf_fin(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        return fin, planar_uv(n, 128)
    solids_mesh(I, SH.rocket_fins(), tf_fin)
    I.shift((cx, cy, 0))
    X.add_model(I)
    # balcony rail: chrome posts + two tubes, gaps at the slides (the collision rail is common/clip, 36 high)
    ch = S('metal', 'lms', v=0.3, tag='rkr')
    n = 32
    for k in range(n):
        a0 = 360 * k / n + 180 / n; a1 = a0 + 360 / n
        am = (a0 + a1) / 2
        if min(abs(((am - g) + 180) % 360 - 180) for g in (0, 180)) < 12: continue
        r = L.BALC_R1 - 4
        pa = np.array([r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0))])
        pb = np.array([r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1))])
        cylm(X.mesh(ch), (pa[0], pa[1], L.COCK_Z), 2.5, L.BALC_RAIL, n=6)
        for z in (L.COCK_Z + 18, L.COCK_Z + L.BALC_RAIL):
            tube(X.mesh(ch), [(pa[0], pa[1], z), (pb[0], pb[1], z)], 1.6, nseg=6)
    # balcony underside struts down to the fins
    for a in L.FIN_A:
        c_, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        tube(X.mesh(ch), [(c_ * (L.RK_R + 110), s_ * (L.RK_R + 110), 300), (c_ * (L.BALC_R1 - 20), s_ * (L.BALC_R1 - 20), L.COCK_Z - 16)], 5, nseg=8)
    # porthole rims (chrome) and the panorama window frame
    q = L.RK_RR * math.pi / 2
    for (uc, zc, rr) in ((0.0, 450, 44), (L.RK_RR * math.pi, 450, 44), (-q * 0.5, 450, 34), (q * 0.5, 450, 34), (-q * 1.5, 450, 34), (q * 1.5, 450, 34),
                         (-q, 760, 40), (q, 760, 40), (L.RK_RR * math.pi, 760, 40)):
        a = math.radians(L.RK_FACE + math.degrees(uc / L.RK_RR))
        rr_out = L.rk_profile(zc) + 1
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c3 = d * rr_out + np.array([0, 0, zc])
        torus(X.mesh(ch), c3, rr + 3, 4, axis=d, n=20, m=6)
    # main door frame: chrome arch tube round the opening
    a_f = math.radians(L.RK_FACE)
    def on_shell(u, z, off=1.0):
        a = a_f + u / L.RK_RR
        r = L.rk_profile(z) + off
        return np.array([r * math.cos(a), r * math.sin(a), z])
    hw = 72
    pts = [on_shell(-hw - 4, 0)] + [on_shell(-hw - 4, 116)] + [on_shell((hw + 4) * math.cos(t), 116 + 30 * math.sin(t)) for t in np.linspace(math.pi, 0, 11)[1:-1]] + \
          [on_shell(hw + 4, 116), on_shell(hw + 4, 0)]
    tube(X.mesh(ch), pts, 4, nseg=6)
    # engine bells peeking out under the skirt edge (decor, flush with the ground) + glowing ignition ring
    gl = S('glow_o', 'glow', wave='sin 0.8 0.2 0 0.6', tag='rkg')
    revolve(X.mesh(gl), [(L.RK_SKIRT + 2, 2), (L.RK_SKIRT + 6, 2), (L.RK_SKIRT + 6, 10), (L.RK_SKIRT + 2, 10)], n=48, vlen=32)
    # the antenna on the tip
    tube(X.mesh(ch), [(0, 0, L.RK_TIP - 40), (0, 0, L.RK_TIP + 60)], [5, 2], nseg=6)
    sphere(X.mesh(S('glow_r', 'glow', wave='square 0 1 0 0.8', tag='rkt')), (0, 0, L.RK_TIP + 64), 6, nu=8, nv=6)
    X.shift((0, 0, 0))
    return save('rocket', X)


def pilot_seat():
    X = Model()
    sh = X.mesh(S('white', 'lm', tag='seat')); cu = X.mesh(S('blue', 'lm', tag='seat')); mt = X.mesh(S('metal', 'lm', tag='seat'))
    cylm(mt, (0, 0, 0), 6, 18, n=8)
    boxm(cu, (-18, -16, 18), (18, 16, 26), r=3, k=2, tile=32)
    P = [(-18, 12, 24), (18, 12, 24), (18, 20, 70), (-18, 20, 70)]
    boxm(cu, (-18, 12, 24), (18, 20, 72), r=3, k=2, tile=32)
    boxm(sh, (-20, 18, 20), (20, 24, 76), r=3, k=2, tile=32)
    for s in (-1, 1): boxm(sh, (s * 18 - 3, -12, 26), (s * 18 + 3, 14, 40), r=2, k=1, tile=32)
    return save('pilot_seat', X)


def console():
    """flight console desk (faces -y), 120 wide, sloped panel with buttons, origin floor centre"""
    X = Model()
    bd = X.mesh(S('panels_d', 'lm', tag='con')); pn = X.mesh(S('console', 'lm', tag='con'))
    boxm(bd, (-60, -10, 0), (60, 30, 40), r=2, k=1, tile=64)
    quad_uv(pn, (-58, -14, 40), (58, -14, 40), (58, 22, 62), (-58, 22, 62), [(0, 1), (1, 1), (1, 0), (0, 0)])
    boxm(bd, (-60, 22, 40), (60, 30, 64), r=1, k=1, tile=64)
    return save('console', X)


# ================================================================================================= the lunar lander
def lander():
    """descent stage (gold foil octagon down into the water, landing legs and footpads), ascent cabin (panels, doors N/S,
    windows E/W, roof walk), dish antenna, RCS thrusters, ladder. Origin = lander centre at z 0."""
    X = Model()
    lx, ly = L.LANDER
    gf = SB('gold_foil', 40, tag='ld'); dk = SB('plate', 30, tag='ld'); ext = SB('panel_w', 30, tag='ldc'); inn = SB('panel_d', 30, tag='ldi')
    def tf_stage(c, n, poly):
        if n[2] < -0.9: return None
        if n[2] > 0.9: return dk, planar_uv(n, 128)
        return gf, planar_uv(n, 128)
    solids_mesh(X, SH.lander_stage(), tf_stage)
    c0 = L.CAB
    def tf_cab(c, n, poly):
        if n[2] < -0.9 and c[2] < L.DECK_Z + 1: return None
        if n[2] > 0.9: return dk, planar_uv(n, 128)
        x, y = c[0] - lx, c[1] - ly
        q = np.array([x, y]) + np.array(n[:2]) * 3
        outside = not (c0[0] < q[0] < c0[2] and c0[1] < q[1] < c0[3])
        if n[2] < -0.9: return inn, planar_uv(n, 128)
        return (ext if outside else inn), planar_uv(n, 128)
    solids_mesh(X, SH.lander_cabin(), tf_cab)
    X.shift((lx, ly, 0))
    mt = S('metal', 'lms', v=0.25, tag='ld'); bk = S('black', 'lm', tag='ld'); gd = S('gold', 'lms', v=0.3, tag='ld')
    # black band under the deck edge
    oc = L.octagon((-L.LD_HALF - 1, -L.LD_HALF - 1, L.LD_HALF + 1, L.LD_HALF + 1), L.LD_CUT)
    prism(X.mesh(bk), oc, L.DECK_Z - 14, L.DECK_Z - 4, tile=64, top=False, bot=False)
    # landing legs: a main strut from the stage corner to the footpad + two braces; footpads on the lagoon floor
    for a in (45, 135, 225, 315):
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0])
        t_ = np.array([-d[1], d[0], 0])
        top = d * (L.LD_HALF * 0.86) + np.array([0, 0, 70])
        foot = d * L.LEG_R1 + np.array([0, 0, L.DEEP + 14])
        tube(X.mesh(mt), [top, foot], [9, 7], nseg=10)
        for s in (-1, 1):
            tube(X.mesh(mt), [d * (L.LD_HALF * 0.7) + t_ * s * 60 + [0, 0, L.WATER - 20], foot + [0, 0, 30]], 4, nseg=6)
        revolve(X.mesh(gd), [(0, L.DEEP), (30, L.DEEP), (34, L.DEEP + 4), (28, L.DEEP + 14), (0, L.DEEP + 14)], n=16, cx=foot[0], cy=foot[1], vlen=32)
    # ladder down the north leg (decor: bots and players use the jetty stairs)
    # cabin trim: gold window frames, RCS quads, dish antenna and a small mast on the roof
    for (side, sgn) in (('e', 1), ('w', -1)):
        x = sgn * (c0[2] + 1)
        for (yy, zz, w_, h_) in ((0, L.DECK_Z + 102, 96, 84),):
            boxm(X.mesh(gd), (min(x, x + sgn * 4), -w_ / 2 - 4, zz - h_ / 2 - 4), (max(x, x + sgn * 4), w_ / 2 + 4, zz - h_ / 2), r=1, tile=32)
            boxm(X.mesh(gd), (min(x, x + sgn * 4), -w_ / 2 - 4, zz + h_ / 2), (max(x, x + sgn * 4), w_ / 2 + 4, zz + h_ / 2 + 4), r=1, tile=32)
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = np.array([sx * (c0[2] - 4), sy * (c0[3] - 4), L.CAB_TOP - 40])
        boxm(X.mesh(mt), p - [10, 10, 10] + [sx * 10, sy * 10, 0], p + [10, 10, 10] + [sx * 10, sy * 10, 0], r=2, k=1, tile=32)
        for d_ in ((sx, 0, 0), (0, sy, 0), (0, 0, 1)):
            cone(X.mesh(bk), p + [sx * 10, sy * 10, 0] + np.array(d_) * 10, p + [sx * 10, sy * 10, 0] + np.array(d_) * 22, 5, n=6)
    # roof mast + dish (north-east corner; collision: a thin weapclip post)
    mx, my = c0[2] - 26, c0[3] - 26
    tube(X.mesh(mt), [(mx, my, L.CAB_TOP), (mx, my, L.CAB_TOP + 96)], 3, nseg=6)
    dish = Mesh(); revolve(dish, [(0, 0), (20, 2), (34, 8), (40, 14)], n=16, vlen=32)
    revolve(dish, [(40, 14), (34, 8), (20, 2), (0, 0)], n=16, vlen=32, inward=False)
    X.mesh(S('white', 'lm', tag='dish', two=True)).add(dish, rot_axis((1, -1, 0), math.radians(50)), (mx, my, L.CAB_TOP + 96))
    # hatch frames
    for sgn in (-1, 1):
        y = sgn * (c0[3] + 1)
        for xx in (-L.CAB_DOOR_HW - 4, L.CAB_DOOR_HW):
            boxm(X.mesh(gd), (xx, min(y, y + sgn * 4), L.DECK_Z), (xx + 4, max(y, y + sgn * 4), L.DECK_Z + L.CAB_DOOR_H + 4), r=0.5, tile=32)
        boxm(X.mesh(gd), (-L.CAB_DOOR_HW - 4, min(y, y + sgn * 4), L.DECK_Z + L.CAB_DOOR_H), (L.CAB_DOOR_HW + 4, max(y, y + sgn * 4), L.DECK_Z + L.CAB_DOOR_H + 4), r=0.5, tile=32)
    # the name board over the north hatch
    picture(X.mesh(S(BT('sign_lander'), 'lm', tag='ld')), (0, c0[3] + 1.5, L.DECK_Z + 140), 128, 32, (0, 1, 0))
    picture(X.mesh(S(BT('sign_lander'), 'lm', tag='ld')), (0, c0[1] - 1.5, L.DECK_Z + 140), 128, 32, (0, -1, 0))
    return save('lander', X)


# ================================================================================================= Planet Padurn
def planet():
    """the banded planet sphere with an icy polar cap walk, the walkable ring, the crystal pedestal and the stair bridge"""
    X = Model()
    cx, cy = L.PL
    bs = S('bands', 'lm', shade=80, tag='pl')
    zc, R = L.PL_ZC, L.PL_R
    zs = np.linspace(130, L.PL_CAP, 40)
    prof = [(max(0.5, L.pl_sphere_r(z)), float(z)) for z in zs]
    prof[0] = (0.0, prof[0][1])
    revolve(X.mesh(bs), prof, n=64, u_tiles=4, v_of=lambda r, z: (z - 130) / 470, vlen=256)
    disc(X.mesh(S('ice', 'lm', tag='pl')), L.pl_cap_r(), L.PL_CAP, up=True, n=64, uvscale=180)
    # frosty rim round the cap (low ridge, under head height - no cover)
    revolve(X.mesh(S('ice', 'lm', tag='plr')), [(L.pl_cap_r() - 2, L.PL_CAP), (L.pl_cap_r() + 4, L.PL_CAP - 4)], n=64, vlen=32)
    # ring: top/bottom/edges, bands follow the radius
    rs = S('ring', 'lm', shade=20, tag='pl')
    revolve(X.mesh(rs), [(L.RING_R0, L.RING_Z), (L.RING_R1, L.RING_Z)], n=64, u_tiles=12, v_of=lambda r, z: (r - L.RING_R0) / (L.RING_R1 - L.RING_R0), inward=False)
    revolve(X.mesh(rs), [(L.RING_R1, L.RING_Z - 16), (L.RING_R0, L.RING_Z - 16)], n=64, u_tiles=12, v_of=lambda r, z: (r - L.RING_R0) / (L.RING_R1 - L.RING_R0))
    revolve(X.mesh(S('metal', 'lm', tag='plr')), [(L.RING_R1, L.RING_Z - 16), (L.RING_R1, L.RING_Z)], n=64, u_tiles=12, vlen=32)
    # fine outer rings drawn flat on the deck edge as glowing lines
    gl = S('glow_y', 'glow', wave='sin 0.8 0.2 0 0.3', tag='plg')
    revolve(X.mesh(gl), [(L.RING_R1 - 6, L.RING_Z + 0.6), (L.RING_R1 - 2, L.RING_Z + 0.6)], n=64, vlen=32)
    # pedestal: faceted crystal column
    cr = S('crystal', 'lm', shade=10, tag='pl')
    revolve(X.mesh(cr), [(L.PED_R0 + 6, 0), (L.PED_R1 + 6, 130), (0, 150)], n=8, vlen=128)
    # stair bridge: steps from the shapes, two side stringers, glowing step edges
    sd = SB('panel_d', 30, tag='pls'); tp = SB('plate', 30, tag='pls')
    def tf(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if n[2] > 0.9: return tp, planar_uv(n, 128)
        return sd, planar_uv(n, 128)
    X.shift((0, 0, 0))
    save('planet', X)
    # the stair bridge is its own model (it reaches ~1000u from the planet's centre)
    X = Model()
    solids_mesh(X, SH.planet_stair(), tf)
    X.shift((cx, cy, 0))
    xr = L.RING_R1 * math.cos(math.radians(180 / 32))
    n = L.RING_Z // 16
    mt = S('metal', 'lms', v=0.25, tag='pls')
    for s in (-1, 1):
        y = s * (L.PL_STAIR_W / 2 + 4)
        tube(X.mesh(mt), [(xr, y, L.RING_Z - 30), (xr + 32 * n, y, -14)], [5, 5], nseg=6)
        tube(X.mesh(mt), [(xr, y, L.RING_Z + 34), (xr + 32 * n, y, 34)], [2.5, 2.5], nseg=6)
        for i in range(0, n, 3):
            x = xr + 32 * i + 16; z = L.RING_Z - 16 * i
            tube(X.mesh(mt), [(x, y, z), (x, y, z + 34)], 2, nseg=6)
    X.shift((xr + 16 * n, 0, 0))
    return save('planet_stair', X)


# ================================================================================================= the satellite tower
def sat_tower():
    X = Model()
    cx, cy = L.SAT
    pl = SB('plate', 30, tag='st'); sd = SB('panel_w', 30, tag='st')
    blist, steps, holes = SH.sat_tower()
    def tf(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        if n[2] > 0.9: return pl, planar_uv(n, 128)
        return sd, planar_uv(n, 128)
    solids_mesh(X, blist + SH.sat_arm(), tf)
    h = L.SAT_HALF
    mt = S('metal', 'lms', v=0.25, tag='st'); rd = S('red', 'lm', tag='st')
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        px, py = cx + sx * (h - 6), cy + sy * (h - 6)
        tube(X.mesh(rd), [(px, py, 0), (px, py, L.SAT_TOP + 44)], [8, 6], nseg=8)
    for z in (90, 200, 310):
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            pa = np.array([cx + a[0] * (h - 6), cy + a[1] * (h - 6), z]); pb = np.array([cx + b[0] * (h - 6), cy + b[1] * (h - 6), z + 60])
            tube(X.mesh(mt), [pa, pb], 3, nseg=6)
    # rails (tubes over the clip rails) round the top except the stair opening and the arm
    for (a, b) in (((1, 1), (1, -1)), ((1, -1), (-1, -1)), ((-1, -1), (-1, 0.3)), ((0.3, 1), (1, 1))):
        for z in (L.SAT_TOP + 20, L.SAT_TOP + 40):
            pa = np.array([cx + a[0] * (h - 4), cy + a[1] * (h - 4), z]); pb = np.array([cx + b[0] * (h - 4), cy + b[1] * (h - 4), z])
            tube(X.mesh(mt), [pa, pb], 1.8, nseg=6)
    # hazard stripes along the arm's edges
    d = np.array([-1.0, 1.0]) / math.sqrt(2); t_ = np.array([d[1], -d[0]])
    p0 = np.array([cx - h + 20, cy + h - 20])
    hz = S('hazard', 'lm', tag='st')
    for w in (-26, 26):
        a = p0 + t_ * w; b = a + d * 300
        nrm = np.array([t_[0], t_[1], 0]) * (1 if w > 0 else -1)
        quad_uv(X.mesh(hz), (a[0], a[1], L.SAT_TOP - 8), (b[0], b[1], L.SAT_TOP - 8), (b[0], b[1], L.SAT_TOP + 0.5), (a[0], a[1], L.SAT_TOP + 0.5),
                [(0, 0), (6, 0), (6, 0.2), (0, 0.2)], nrm * (1.0001))
    # solar panel wings on the south-east post
    so = S('solar', 'lm', tag='st', two=True)
    px, py = cx + h - 6, cy - h + 6
    for s_ in (-1, 1):
        a = np.array([px, py, L.SAT_TOP + 44]); b = a + np.array([s_ * 0.0, 0, 0])
        quad_uv(X.mesh(so), (px + s_ * 10, py - 4, L.SAT_TOP - 10 + 40), (px + s_ * 90, py - 4, L.SAT_TOP - 10 + 40),
                (px + s_ * 90, py - 4, L.SAT_TOP + 70), (px + s_ * 10, py - 4, L.SAT_TOP + 70), [(0, 1), (1, 1), (1, 0), (0, 0)], (0, -1, 0))
    X.shift((cx, cy, 0))
    return save('sat_tower', X)


# ================================================================================================= buildings
def building(name, blist, rect, ext, inn, roof_top='plate', trim='metal'):
    X = Model()
    x0, y0, x1, y1 = rect
    se = SB(ext, 30, tag=name); si = SB(inn, 30, tag=name + 'i'); sr = SB(roof_top, 30, tag=name + 'r'); st = S(trim, 'lm', tag=name)
    sfl = SB('plate', 30, tag=name + 'f')
    def texfn(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        inside = x0 + 23 < c[0] < x1 - 23 and y0 + 23 < c[1] < y1 - 23
        beyond = not (x0 - 10 < c[0] < x1 + 10 and y0 - 10 < c[1] < y1 + 10)
        if beyond: return sfl, planar_uv(n, 128)
        if n[2] > 0.9: return sr, planar_uv(n, 256)
        if n[2] < -0.9: return (si if inside else st), planar_uv(n, 256)
        q = c + n * 3
        out_ = not (x0 < q[0] < x1 and y0 < q[1] < y1)
        return (se if out_ else si), planar_uv(n, 256)
    solids_mesh(X, blist, texfn)
    return X


def win_frame(X, side, c, hw, zb, zt, rect, sh, door=False, t=4):
    x0, y0, x1, y1 = rect
    if side in 'ns':
        y = y0 if side == 's' else y1
        o = -1 if side == 's' else 1
        for xx in (c - hw - t, c + hw):
            boxm(X.mesh(sh), (xx, min(y, y + o * 6), zb if not door else 0), (xx + t, max(y, y + o * 6), zt + t), r=0.5, tile=32)
        boxm(X.mesh(sh), (c - hw - t, min(y, y + o * 6), zt), (c + hw + t, max(y, y + o * 6), zt + t), r=0.5, tile=32)
        if not door: boxm(X.mesh(sh), (c - hw - 8, min(y, y + o * 10), zb - 6), (c + hw + 8, max(y, y + o * 10), zb), r=0.5, tile=32)
    else:
        x = x0 if side == 'w' else x1
        o = -1 if side == 'w' else 1
        for yy in (c - hw - t, c + hw):
            boxm(X.mesh(sh), (min(x, x + o * 6), yy, zb if not door else 0), (max(x, x + o * 6), yy + t, zt + t), r=0.5, tile=32)
        boxm(X.mesh(sh), (min(x, x + o * 6), c - hw - t, zt), (max(x, x + o * 6), c + hw + t, zt + t), r=0.5, tile=32)
        if not door: boxm(X.mesh(sh), (min(x, x + o * 10), c - hw - 8, zb - 6), (max(x, x + o * 10), c + hw + 8, zb), r=0.5, tile=32)


def cafe():
    """Cosmic Cafe: googie walls, a boomerang canopy over the door, neon trim, the sign pylon with a sputnik star"""
    x0, y0, x1, y1 = L.CAFE
    X = building('cafe', SH.cafe(), L.CAFE, 'googie', 'panel_w', 'plate')
    ch = S('metal', 'lms', v=0.3, tag='cf')
    yc = (y0 + y1) / 2
    for (side, c, hw, zb, zt) in (('w', yc - 170, 44, 72, 168), ('w', yc + 170, 44, 72, 168), ('s', x0 + 140, 44, 72, 168),
                                  ('n', x0 + 140, 44, 72, 168), ('n', x1 - 160, 44, 72, 168), ('e', yc, 44, 96, 168)):
        win_frame(X, side, c, hw, zb, zt, L.CAFE, ch)
    win_frame(X, 'w', yc, 60, 0, 168, L.CAFE, ch, door=True)
    # neon band round the roof edge (glows, no collision)
    nm = S('glow_m', 'glow', wave='sin 0.85 0.15 0 0.5', tag='cfn')
    for (a, b, nrm) in (((x0 - 2, y0 - 2), (x1 + 2, y0 - 2), (0, -1, 0)), ((x1 + 2, y0 - 2), (x1 + 2, y1 + 2), (1, 0, 0)),
                        ((x1 + 2, y1 + 2), (x0 - 2, y1 + 2), (0, 1, 0)), ((x0 - 2, y1 + 2), (x0 - 2, y0 - 2), (-1, 0, 0))):
        quad_uv(X.mesh(nm), (a[0], a[1], L.CAFE_H - 30), (b[0], b[1], L.CAFE_H - 30), (b[0], b[1], L.CAFE_H - 20), (a[0], a[1], L.CAFE_H - 20),
                [(0, 0), (1, 0), (1, 1), (0, 1)], nrm)
    # boomerang canopy over the door on two slanted posts
    cv = S('white', 'lm', tag='cfc', two=True)
    P = [np.array([x0, yc - 150, 196.0]), np.array([x0, yc + 150, 196.0]), np.array([x0 - 120, yc + 90, 176.0]), np.array([x0 - 120, yc - 90, 176.0])]
    nn = np.cross(P[1] - P[0], P[3] - P[0]); nn /= np.linalg.norm(nn)
    if nn[2] < 0: nn = -nn
    X.mesh(cv).poly(P, nn, [(0, 0), (1, 0), (1, 1), (0, 1)])
    boxm(X.mesh(S('red', 'lm', tag='cf')), (x0 - 124, yc - 92, 170), (x0 - 116, yc + 92, 178), r=1, tile=32)
    for s in (-1, 1):
        tube(X.mesh(ch), [(x0 - 100, yc + s * 70, 0), (x0 - 110, yc + s * 80, 176)], 4, nseg=8)
    # sign over the canopy
    picture(X.mesh(S(BT('sign_cafe'), 'glow', tag='cf')), (x0 - 2, yc, 214), 300, 56, (-1, 0, 0))
    # the googie pylon at the north-west corner: a tall tapered fin with a sputnik star on top
    gx, gy = x0 - 70, y1 + 70
    pyl = S('panels', 'lm', tag='cfp')
    prism(X.mesh(pyl), [(gx - 14, gy - 40), (gx + 14, gy - 40), (gx + 8, gy + 40), (gx - 8, gy + 40)], 0, 360, tile=64)
    boxm(X.mesh(S('red', 'lm', tag='cfp')), (gx - 10, gy - 44, 0), (gx + 10, gy - 38, 360), r=1, tile=32)
    star = S('glow_y', 'glow', wave='sin 0.8 0.2 0 1', tag='cfs')
    sphere(X.mesh(star), (gx, gy, 384), 12, nu=10, nv=6)
    for k in range(8):
        d = rot_axis((0.3, 0.6, 1), k * math.pi / 4) @ np.array([1.0, 0, 0])
        tube(X.mesh(ch), [np.array([gx, gy, 384]), np.array([gx, gy, 384]) + d * 48], [2, 0.8], nseg=5)
    picture(X.mesh(S(BT('sign_cafe'), 'glow', tag='cf')), (gx - 15, gy, 270), 150, 30, (-1, 0, 0), up=(0, 0, 1))
    picture(X.mesh(S(BT('sign_cafe'), 'glow', tag='cf')), (gx + 15, gy, 270), 150, 30, (1, 0, 0), up=(0, 0, 1))
    # interior: a jukebox and wall posters
    picture(X.mesh(S('screen', 'lm', tag='cf')), ((x0 + x1) / 2 + 40, y0 + 24.6, 120), 120, 60, (0, 1, 0))
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('cafe', X)


def mission_control():
    """Mission Control: white walls with a blue band, the big wall screen inside, a radar dome on the roof"""
    x0, y0, x1, y1 = L.MC
    X = building('mc', SH.mission_control(), L.MC, 'mc_wall', 'panel_d', 'plate')
    ch = S('metal', 'lms', v=0.3, tag='mc')
    yc = (y0 + y1) / 2
    picture(X.mesh(S(BT('sign_mc'), 'lm', tag='mc')), (x0 - 2, yc, 172), 320, 44, (-1, 0, 0))
    for (side, c, hw, zb, zt) in (('w', yc - 120, 36, 64, 140), ('w', yc + 120, 36, 64, 140), ('s', (x0 + x1) / 2, 40, 64, 140), ('n', (x0 + x1) / 2, 40, 64, 140)):
        win_frame(X, side, c, hw, zb, zt, L.MC, ch)
    win_frame(X, 'w', yc, 56, 0, 152, L.MC, ch, door=True)
    # the big screen on the east wall
    picture(X.mesh(S('screen', 'glow', tag='mcs')), (x1 - 24.6, yc, 110), 240, 120, (-1, 0, 0))
    # radar dome on the roof (north-east corner)
    dx, dy = x1 - 70, y1 - 70
    revolve(X.mesh(S('white', 'lm', tag='mcd')), [(0, L.MC_H + 76), (34, L.MC_H + 66), (54, L.MC_H + 40), (56, L.MC_H)], n=24, cx=dx, cy=dy, vlen=64)
    revolve(X.mesh(S('metal_d', 'lm', tag='mcd')), [(62, L.MC_H), (62, L.MC_H + 10), (54, L.MC_H + 10)], n=24, cx=dx, cy=dy, vlen=32)
    X.shift(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return save('mission_control', X)


def pod(name, rect):
    """habitat pod: white/orange panels, rounded corner columns, porthole frames, a glowing roof rim, antenna"""
    x0, y0, x1, y1 = rect
    X = building(name, SH.pod(rect), rect, 'pod_wall', 'panel_w', 'plate')
    H = L.POD_H
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    ch = S('metal', 'lms', v=0.3, tag=name)
    for (px, py) in ((x0 - 4, y0 - 4), (x1 + 4, y0 - 4), (x1 + 4, y1 + 4), (x0 - 4, y1 + 4)):
        tube(X.mesh(S('orange', 'lm', tag=name)), [(px, py, 0), (px, py, H + 8)], 9, nseg=10, vlen=64)
    gl = S('glow_c', 'glow', wave='sin 0.8 0.2 0 0.4', tag=name)
    for (a, b, nrm) in (((x0 - 8, y0 - 8), (x1 + 8, y0 - 8), (0, -1, 0)), ((x1 + 8, y0 - 8), (x1 + 8, y1 + 8), (1, 0, 0)),
                        ((x1 + 8, y1 + 8), (x0 - 8, y1 + 8), (0, 1, 0)), ((x0 - 8, y1 + 8), (x0 - 8, y0 - 8), (-1, 0, 0))):
        quad_uv(X.mesh(gl), (a[0], a[1], H - 12), (b[0], b[1], H - 12), (b[0], b[1], H - 4), (a[0], a[1], H - 4), [(0, 0), (1, 0), (1, 1), (0, 1)], nrm)
    for (side, c) in (('n', xc), ('s', xc), ('w', yc)):
        win_frame(X, side, c, 32, 64, 120, rect, ch)
    win_frame(X, 'e', yc, 48, 0, 128, rect, ch, door=True)
    tube(X.mesh(ch), [(x0 + 30, y1 - 30, H), (x0 + 30, y1 - 30, H + 90)], 2.5, nseg=6)
    sphere(X.mesh(S('glow_r', 'glow', wave='square 0 1 0 0.7', tag=name)), (x0 + 30, y1 - 30, H + 94), 4, nu=6, nv=4)
    X.shift((xc, yc, 0))
    return save(name, X)


def loo():
    """the Zero-G Loo: a white capsule with a rounded top and a blue door frame"""
    X = Model()
    lx, ly = L.LOO
    h = L.LOO_HALF
    def tf(c, n, poly):
        if n[2] < -0.9 and c[2] < 1: return None
        return SB('pod_wall', 30, tag='loo'), planar_uv(n, 64)
    solids_mesh(X, SH.loo(), tf)
    X.shift((lx, ly, 0))
    bl = S('blue', 'lm', tag='loo')
    revolve(X.mesh(S('white', 'lm', tag='loo')), [(h + 4, 136), (h - 6, 160), (0, 170)], n=16, vlen=64)
    for yy in (-28 - 4, 28):
        boxm(X.mesh(bl), (-h - 4, yy, 0), (-h, yy + 4, 108), r=0.5, tile=32)
    boxm(X.mesh(bl), (-h - 4, -32, 104), (-h, 32, 108), r=0.5, tile=32)
    picture(X.mesh(S(BT('sign_loo'), 'lm', tag='loo')), (-h - 1.5, 0, 124), 72, 18, (-1, 0, 0))
    return save('loo', X)


# ================================================================================================= slides
def wormhole_tube(path, sup):
    """Wormhole: a purple tube with glowing rings, starry blue inside, running water. World coords."""
    X = Model()
    body = S('tube_p', 'lm', shade=60, tag='wt'); inner = S('slide_in', 'lm', shade=60, tag='wt')
    band = S('glow_c', 'glow', wave='sin 0.7 0.3 0 0.5', tag='wtb')
    wat = S('water_strip', 'flow', speed=-1.4, tag='wt'); mt = S('metal', 'lms', v=0.2, tag='wt')
    P = densify(path[1:], 40)
    C3 = [np.array([p[0], p[1], p[2] + L.TUBE_ZC]) for p in P]
    sweep(X.mesh(body), C3, circle_prof(L.TUBE_R, 20), closed=True, vlen=192)
    sweep(X.mesh(inner), C3, circle_prof(L.TUBE_R - 4, 20), closed=True, vlen=256, inward=True)
    sweep(X.mesh(wat), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-34, 0), (34, 0)], vlen=200)
    for i in range(2, len(C3) - 2, 3):
        d = C3[i + 1] - C3[i - 1]; d /= np.linalg.norm(d)
        tor = Mesh(); revolve(tor, [(L.TUBE_R + 0.5, -4), (L.TUBE_R + 3, -2), (L.TUBE_R + 3, 2), (L.TUBE_R + 0.5, 4)], n=20, vlen=16)
        b1, b2 = frame(d)
        X.mesh(band).add(tor, np.stack([b1, b2, d], 1), C3[i])
    for (x, y, z) in sup:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        tube(X.mesh(mt), [(x, y, 0), (x, y, zt - 8)], 7, nseg=8)
        boxm(X.mesh(mt), (x - 40, y - 10, zt - 16), (x + 40, y + 10, zt), r=1, tile=64)
        revolve(X.mesh(mt), [(0, 0), (20, 0), (16, 8), (0, 8)], n=12, cx=x, cy=y, vlen=32)
    return save('wormhole_tube', X)


def wormhole_mouth():
    """the tube entrance on the balcony: a glowing portal ring round the tube mouth; faces +x, origin floor centre"""
    X = Model()
    R = L.TUBE_R; zc = L.TUBE_ZC
    pr = S('portal', 'add', tcmod='rotate 60', tag='wm')
    ring_ = S('glow_v', 'glow', wave='sin 0.8 0.2 0 0.7', tag='wm'); mt = S('metal', 'lms', v=0.25, tag='wm')
    torus(X.mesh(ring_), (40, 0, zc), R + 14, 7, axis=(1, 0, 0), n=28, m=8)
    torus(X.mesh(mt), (40, 0, zc), R + 26, 4, axis=(1, 0, 0), n=28, m=6)
    for s in (-1, 1):
        tube(X.mesh(mt), [(40, s * (R + 26), 0), (40, s * (R + 26), zc)], 5, nseg=8)
    return save('wormhole_mouth', X)


def comet_flume(path, sup):
    """Comet Run: an open cyan trough with a white rim on chrome legs. World coords."""
    X = Model()
    r = 52; lip = 46
    zc = r * 0.55
    wd = S('white', 'lm', shade=60, tag='cf'); inn = S('slide_in', 'lm', shade=60, tag='cfi'); mt = S('metal', 'lms', v=0.2, tag='cfl')
    prof_out = [(-(r + 6), lip)] + [((r + 6) * math.cos(a), zc + (r + 6) * math.sin(a)) for a in np.radians(np.linspace(180, 360, 9))] + [((r + 6), lip)]
    prof_in = [(-r, lip)] + [(r * math.cos(a), zc + r * math.sin(a)) for a in np.radians(np.linspace(180, 360, 9))] + [(r, lip)]
    P = densify(path[1:], 40)
    sweep(X.mesh(wd), P, prof_out, vlen=128)
    sweep(X.mesh(inn), P, prof_in, vlen=256, inward=True)
    sweep(X.mesh(S('glow_c', 'glow', tag='cfr')), P, [(-(r + 6), lip), (-(r + 6), lip + 3), (-r, lip + 3)], vlen=128)
    sweep(X.mesh(S('glow_c', 'glow', tag='cfr')), P, [(r, lip + 3), (r + 6, lip + 3), (r + 6, lip)], vlen=128)
    sweep(X.mesh(S('water_strip', 'flow', speed=-1.4, tag='f')), [np.array([p[0], p[1], p[2] + 1.5]) for p in P], [(-r * 0.6, 0), (r * 0.6, 0)], vlen=200)
    bot = zc - r - 6
    for (x, y, z) in sup:
        zt = z + bot + 4
        for s in (-1, 1):
            tube(X.mesh(mt), [(x + s * 30, y, 0), (x + s * 14, y, zt)], 5, nseg=6)
        boxm(X.mesh(mt), (x - r, y - 12, zt - 12), (x + r, y + 12, zt), r=1, tile=64)
    return save('comet_flume', X)


def comet_gate():
    """arch at the flume start: two posts and a beam with a comet sign; faces -x"""
    X = Model()
    mt = S('metal', 'lms', v=0.25, tag='cg')
    for s in (-1, 1):
        tube(X.mesh(mt), [(0, s * 74, 0), (0, s * 74, 150)], 6, nseg=8)
    tube(X.mesh(mt), [(0, -90, 146), (0, 90, 146)], 6, nseg=8)
    cm = S('comet', 'add', tag='cg')
    quad_uv(X.mesh(cm), (-2, -60, 100), (-2, 60, 100), (-2, 60, 136), (-2, -60, 136), [(0, 1), (0, 0), (1, 0), (1, 1)], (-1, 0, 0))
    sphere(X.mesh(S('glow_c', 'glow', tag='cg')), (-4, -60, 118), 12, nu=10, nv=6)
    return save('comet_gate', X)


SUPPORTS = {'tube': [], 'flume': []}


def make():
    make_textures()
    rocket(); pilot_seat(); console(); lander(); planet(); sat_tower(); cafe(); mission_control()
    for i, r in enumerate(L.PODS):
        pod(f'pod_{i}', r)
    loo()
    wormhole_tube(L.tube_path(), SUPPORTS['tube']); wormhole_mouth(); comet_flume(L.flume_path(), SUPPORTS['flume']); comet_gate()
