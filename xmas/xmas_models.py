"""MD3 models for wop_padxmas (Padman's Christmas). All geometry and art is original and generated here.

    import xmas_models as XM
    XM.init(OUT)                       # where models/padxmas/*.md3 go
    path, scale = XM.get('tree')       # build (once) and return (model path, modelscale)
    path, scale = XM.gift(w, d, h, 'red', bow=True)
    XM.shaders()                       # shader text for every model surface (append to padxmas.shader)

Conventions: origin = bottom centre on the floor (z 0) unless noted; the "front" faces +x (misc_model angle turns it).
Models taller or wider than MD3's +-512 are stored at 1/2 or 1/4 size and placed with modelscale (save_md3 picks it).
Every model is lightmapped in the map (misc_model spawnflags 4); collision is separate invisible clip brushes in
build_xmas.py, matching the old brush shapes, so jump pads, routes and bot paths don't change.
Textures come from textures/padxmas (xmas_textures.py) so the models match the room.
"""
import os, sys, math, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, arc_path, save_md3, grid_normals

MD = 'models/padxmas'
OUT = None
REG = {}            # shader name -> (image, kind, options)
CACHE = {}          # model name -> (path, scale)


def init(out):
    global OUT
    OUT = out
    os.makedirs(os.path.join(out, MD), exist_ok=True)


def S(img, kind='lm', **opt):
    """register a model shader using textures/padxmas/<img>; kinds: lm (lightmapped), shiny (lm + env sheen),
    glow (fullbright, optional rgbGen wave), glass (additive env), tinsel (lm + twinkling env)"""
    name = f'{MD}/{img}' if kind == 'lm' else f'{MD}/{img}_{kind}{opt.get("tag", "")}'
    REG[name] = (img, kind, opt)
    return name


class Model:
    def __init__(self): self.m = {}
    def mesh(self, shader):
        if shader not in self.m: self.m[shader] = Mesh()
        return self.m[shader]
    def surfaces(self):
        return [M.surface(f's{i}', sh) for i, (sh, M) in enumerate(self.m.items()) if len(M)]


ZOFF = {}           # model path -> z offset of its stored origin above the model's base point


def _save(name, X):
    path = f'{MD}/{name}.md3'
    sc, zo = save_md3(os.path.join(OUT, path), X.surfaces(), name, with_offset=True)
    CACHE[name] = (path, sc); ZOFF[path] = zo
    return path, sc


def get(name, key=None, **kw):
    """build model `name` (BUILDERS) once with kw and return (path, modelscale); key = file name (default name)"""
    key = key or name
    if key not in CACHE:
        X = BUILDERS[name](**kw)
        p, sc = _save(key, X)
        CACHE[key] = (p, sc)
    return CACHE[key]


def tip_wave(nt, seed):
    """spiky 0..1 modulation round a turn with nt tips of slightly random size"""
    rr = random.Random(seed)
    amp = [rr.uniform(0.7, 1.15) for _ in range(nt)]
    ph = rr.uniform(0, 2 * math.pi)
    def f(a):
        x = (a * nt / (2 * math.pi) + ph) % nt
        k = int(x); fr = x - k
        return amp[k % nt] * (math.sin(math.pi * fr) ** 2.2)
    return f


def lathe_grid(M, prof, n, tipf=None, amp_r=0.0, amp_z=0.0, pull=0.0, u_tiles=8.0, vlen=192.0, cx=0.0, cy=0.0):
    """revolve [(r, z, w[, phase])...] with spiky tips: r += w*amp_r*tip - w*pull*(1-tip), z -= w*amp_z*tip, the tip
    pattern shifted by `phase` (radians) per row so layered boughs interleave; outward normals"""
    prof = [tuple(p) + (0.0,) * (4 - len(p)) for p in prof]
    phs = [p[3] for p in prof]
    prof = np.asarray([p[:3] for p in prof], float)
    angs = np.linspace(0, 2 * math.pi, n + 1)
    P = np.zeros((len(prof), n + 1, 3)); UV = np.zeros((len(prof), n + 1, 2))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof[:, :2], axis=0), axis=1))])
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        for i, (r, z, w) in enumerate(prof):
            t = tipf((a + phs[i]) % (2 * math.pi)) if tipf else 0.0
            rr = r + w * amp_r * t - w * pull * (1 - t)
            zz = z - w * amp_z * t
            P[i, j] = (cx + rr * c, cy + rr * s, zz)
            UV[i, j] = (j / n * u_tiles, L[i] / vlen)
    N = grid_normals(P)
    # orientation: compare with the 2D profile normal of the undeformed lathe
    tg = np.gradient(prof[:, :2], axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1)
    want = np.stack([pn[:, 0], np.zeros(len(prof)), pn[:, 1]], 1)       # at angle 0
    if np.sum(N[:, 0] * want) < 0: N = -N
    M.grid(P, N, UV)


# ================================================================================================= the tree
def tree(tiers, necks, trunk_r=112, stand_r=256, stand_h=144, pole=128):
    """the whole Christmas tree as one model (origin = trunk base on the floor): stand, trunk, 5 tiers with drooping
    bough tips, walkable flat rings, bushy necks, baubles, light chain with blinking bulbs, tinsel swags, star pole"""
    X = Model()
    nd, und, topm = X.mesh(S('needles')), X.mesh(S('needles_under')), X.mesh(S('needles_top'))
    # ---- stand: red enamel bucket with a rolled rim, 4 feet, 4 wing screws
    st = X.mesh(S('stand_red', 'shiny'))
    revolve(st, [(0, 0.5), (stand_r - 40, 0.5), (stand_r - 30, 6), (stand_r - 14, 110), (stand_r - 6, 128)], n=48, u_tiles=6)
    tube(st, arc_path((0, 0, 0), stand_r - 8, 0, 360, n=49, z=132), 9, nseg=10, caps=(False, False), utiles=1)
    revolve(st, [(stand_r - 14, 128), (trunk_r + 30, stand_h - 4), (trunk_r + 4, stand_h)], n=48, u_tiles=6)
    ft = X.mesh(S('paint_green', 'shiny'))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        R = rot_z(a)
        f = Mesh(); rbox(f, (stand_r - 70, -26, 0), (stand_r - 8, 26, 22), r=8, tile=64)
        ft.add(f, R)
        # wing screw through the bucket wall
        sc = Mesh(); tube(sc, [(stand_r - 20, 0, 100), (stand_r + 10, 0, 100)], 7, nseg=8)
        tube(sc, [(stand_r + 10, -22, 100), (stand_r + 10, 22, 100)], 6, nseg=8)
        ft.add(sc, rot_z(a + math.radians(45)))
    # ---- trunk
    bark = X.mesh(S('bark'))
    revolve(bark, [(trunk_r + 6, stand_h - 2), (trunk_r, stand_h + 20), (trunk_r - 4, tiers[0][0] - 10)], n=20, u_tiles=3,
            rfun=lambda a, r, z: r + 4 * math.sin(7 * a + z / 40))
    # ---- tiers
    cols = ['bauble_red', 'bauble_gold', 'bauble_blue', 'bauble_silver', 'bauble_green', 'bauble_purple']
    bulbs = ['bulb_red', 'bulb_yellow', 'bulb_green', 'bulb_blue']
    wire = X.mesh(S('wire'))
    for i, (zb, zt, rb, rt) in enumerate(tiers):
        base = zb - 32
        r_in = (necks[i - 1] if i > 0 else trunk_r) - 6
        nt = max(14, int(2 * math.pi * rb / 78))
        n = nt * 4
        half = math.pi / nt                  # half a tip: the next layer's tips sit between this layer's
        tipf = tip_wave(nt, 100 + i)
        under = [(r_in, base + 22, 0.0), (r_in + (rb - r_in) * 0.45, base + 12, 0.15), (rb - 80, base + 2, 0.5), (rb - 14, base - 8, 1.0)]
        outer = [(rb - 14, base - 8, 1.0), (rb + 2, base + 10, 1.0)]
        nl = 3 if rb > 300 else 2
        for k in range(nl):
            t0, t1 = k / nl, (k + 1) / nl
            ph = half * (k + 1)
            outer.append((rb + (rt - rb) * t0 - 34, zb + (zt - zb) * t0 + 10, 0.0, ph))
            if k < nl - 1:
                outer.append((rb + (rt - rb) * t1 - 6, zb + (zt - zb) * t1 - 22, 1.0, ph))
                outer.append((rb + (rt - rb) * t1 + 2, zb + (zt - zb) * t1 - 8, 0.8, ph))
        outer += [(rt - 2, zt - 14, 0.9, half * (nl + 1)), (rt + 2, zt - 4, 0.6, half * (nl + 1)), (rt - 14, zt + 1, 0.0)]
        kw = dict(tipf=tipf, amp_r=40, amp_z=26, pull=14, u_tiles=round(2 * math.pi * rb / 192), vlen=160)
        lathe_grid(und, under, n, **kw)
        lathe_grid(nd, outer, n, **kw)
        # flat walkable ring (two rows only, so no vertices sit inside the jump pads)
        r_neck = necks[i] if i < 4 else 0.0
        if r_neck > 0:
            lathe_grid(topm, [(rt - 14, zt + 1, 0), (r_neck - 2, zt + 1, 0)], nt * 2, u_tiles=round(2 * math.pi * rt / 256), vlen=256)
        else:
            disc(topm, rt - 14, zt + 1, n=nt * 2, uvscale=256)
        # bushy neck up to the next tier's underside
        if i < 4:
            ztop = tiers[i + 1][0] - 32 + 22
            revolve(und, [(r_neck + 4, zt), (r_neck, (zt + ztop) / 2), (r_neck - 4, ztop + 2)], n=32, u_tiles=4,
                    rfun=lambda a, r, z, i=i: r + 9 * math.sin(11 * a + i) * math.sin(z / 23))
        # baubles hanging under the lip
        nb = [14, 12, 10, 8, 6][i]; br = [30, 22, 20, 18, 16][i]
        wl = 14 if i == 0 else 6
        for k in range(nb):
            a = math.radians(360 * (k + 0.5) / nb + i * 13)
            R0 = rb - br - 18
            c = np.array([R0 * math.cos(a), R0 * math.sin(a), base - wl - 6 - br])
            sphere(X.mesh(S(cols[(k + i) % 6], 'shiny')), c, br, nu=16, nv=10)
            cap = Mesh(); revolve(cap, [(0, br - 2), (6.5, br - 2), (6.5, br + 6), (2.5, br + 9), (0, br + 9)], n=10)
            X.mesh(S('brass', 'shiny')).add(cap, t=c)
            tube(wire, [c + [0, 0, br + 8], c + [0, 0, br + 6 + wl + 10]], 0.9, nseg=4, caps=(False, False))
        # light chain swagging round the lip with blinking bulbs
        nbu = [32, 26, 20, 14, 8][i]
        rc = rb + 2
        path = []
        for k in range(nbu * 8 + 1):
            a = 2 * math.pi * k / (nbu * 8)
            sag = math.sin(math.pi * ((k % 8) / 8)) * 10
            path.append((rc * math.cos(a), rc * math.sin(a), base + 8 - sag))
        tube(wire, path, 1.2, nseg=4, caps=(False, False))
        for k in range(nbu):
            a = 2 * math.pi * (k + 0.5) / nbu
            p = np.array([rc * math.cos(a), rc * math.sin(a), base - 2])
            b = Mesh(); ellipsoid(b, (0, 0, -7), 5, 5, 8, nu=8, nv=6)
            X.mesh(S(bulbs[k % 4], 'glow', tag=str(k % 4))).add(b, t=p)
            sk = Mesh(); revolve(sk, [(0, 0), (3.5, 0), (3.5, 5), (0, 5)], n=6)
            X.mesh(S('paint_green')).add(sk, t=p)
        # tinsel swags round the middle of the skirt
        tin = X.mesh(S('tinsel' if i % 2 == 0 else 'tinsel_silver', 'tinsel'))
        nsw = max(6, int(2 * math.pi * rb / 360))
        path = []
        tz = 0.45
        for k in range(nsw * 12 + 1):
            a = 2 * math.pi * k / (nsw * 12) + i * 0.3
            sag = math.sin(math.pi * ((k % 12) / 12))
            t = tz + 0.12 * sag
            r = rb + (rt - rb) * t + 30 - 4 * sag
            path.append((r * math.cos(a), r * math.sin(a), zb + (zt - zb) * tz - 30 * sag))
        tube(tin, path, 7, nseg=8, caps=(False, False), utiles=1, vlen=48)
    # ---- star pole
    top = tiers[4][1]
    revolve(X.mesh(S('brass', 'shiny')), [(7, top), (5, top + pole - 20), (9, top + pole - 10), (0, top + pole)], n=10)
    return X


def star(r1=96, r2=40, t=26):
    """5-point star (origin = its centre), faceted front and back pyramids, glowing gold; model2 of a func_rotating"""
    X = Model(); m = X.mesh(S('star_gold', 'glow'))
    pts = [np.array([(r1 if k % 2 == 0 else r2) * math.sin(k * math.pi / 5), 0, (r1 if k % 2 == 0 else r2) * math.cos(k * math.pi / 5)])
           for k in range(10)]
    for sgn in (-1, 1):
        apex = np.array([0, sgn * t, 0])
        for k in range(10):
            a, b = pts[k], pts[(k + 1) % 10]
            n = np.cross(b - a, apex - a); n /= np.linalg.norm(n)
            if n[1] * sgn < 0: n = -n
            m.poly([a, b, apex], n, [(0.5 + a[0] / 200, 0.5 - a[2] / 200), (0.5 + b[0] / 200, 0.5 - b[2] / 200), (0.5, 0.5)])
    return X


# ================================================================================================= presents
def gift(w, d, h, pat, bow=True, open=False):
    """wrapped present w (x) x d (y) x h, origin bottom centre: rounded box in paper, raised satin ribbons crossing
    over the top and down all four sides, a looped bow with tails. open=True: low box with flaps folded out over the
    sides and crumpled tissue paper inside (floor at 16, walls 32)"""
    X = Model()
    paper, rib = S('paper_' + pat), S('ribbon_' + pat, 'shiny')
    pm, rm = X.mesh(paper), X.mesh(rib)
    hw, hd = w / 2, d / 2
    if not open:
        r = min(6, w / 10, d / 10, h / 10)
        rbox(pm, (-hw, -hd, 0), (hw, hd, h), r=r, k=3, tile=max(w, d, 128))
        bw = max(14, min(36, 0.16 * min(w, d)))
        e = 1.6
        # ribbon along x: over the top and down the +-x ends; along y: over the top and down the +-y ends
        rbox(rm, (-hw - e, -bw / 2, h - 1), (hw + e, bw / 2, h + e), r=0, k=1, tile=64, faces='tnsb')
        rbox(rm, (-bw / 2, -hd - e, h - 1), (bw / 2, hd + e, h + e), r=0, k=1, tile=64, faces='tewb')
        rbox(rm, (hw - 1, -bw / 2, 0), (hw + e, bw / 2, h + e), r=0, k=1, tile=64, faces='ens')
        rbox(rm, (-hw - e, -bw / 2, 0), (-hw + 1, bw / 2, h + e), r=0, k=1, tile=64, faces='wns')
        rbox(rm, (-bw / 2, hd - 1, 0), (bw / 2, hd + e, h + e), r=0, k=1, tile=64, faces='new')
        rbox(rm, (-bw / 2, -hd - e, 0), (bw / 2, -hd + 1, h + e), r=0, k=1, tile=64, faces='sew')
        if bow and min(w, d) >= 80:
            make_bow(rm, (0, 0, h + e), min(w, d) * 0.3, bw)
        return X
    # ---- opened box
    wall, fl = 12, 16
    inside = X.mesh(S('box_inside'))
    for (mn, mx) in (((-hw, -hd, 0), (hw, -hd + wall, 32)), ((-hw, hd - wall, 0), (hw, hd, 32)),
                     ((-hw, -hd + wall, 0), (-hw + wall, hd - wall, 32)), ((hw - wall, -hd + wall, 0), (hw, hd - wall, 32))):
        rbox(pm, mn, mx, r=2, k=2, tile=max(w, d), faces='nsewb')
        rbox(inside, mn, mx, r=2, k=2, tile=64, faces='t')
    rbox(inside, (-hw + wall, -hd + wall, 0), (hw - wall, hd - wall, fl - 6), r=1, k=2, tile=128, faces='t')
    # flaps folded out and down over the sides (thin, 1u off the walls)
    for ax in range(4):
        R = rot_z(ax * math.pi / 2)
        L = (d if ax % 2 == 0 else w) - 8; ext = (hw if ax % 2 == 0 else hd)
        f = Mesh()
        P = np.zeros((2, 6, 3)); UV = np.zeros((2, 6, 2))
        for j, s in enumerate(np.linspace(0, 1, 6)):
            ang = s * math.pi * 0.85
            for i, y in enumerate((-L / 2, L / 2)):
                P[i, j] = (ext + 1 + 3 * math.sin(ang) * 2 + 18 * math.sin(ang) * 0.4, y, 32 - 0 + 6 * math.cos(ang) - 24 * s)
                UV[i, j] = (y / 128, s)
        N = grid_normals(P)
        if N[0, 0, 0] < 0: N = -N
        f.grid(P, N, UV); pm.add(f, R)
    # crumpled tissue paper
    ti = X.mesh(S('tissue'))
    nx, ny = 9, 9
    P = np.zeros((ny, nx, 3)); UV = np.zeros((ny, nx, 2)); rr = random.Random(int(w * 7 + d * 3 + h))
    for i in range(ny):
        for j in range(nx):
            x = -hw + wall + (w - 2 * wall) * j / (nx - 1); y = -hd + wall + (d - 2 * wall) * i / (ny - 1)
            edge = min(i, j, ny - 1 - i, nx - 1 - j)
            z = fl + (rr.uniform(4, 30) if edge > 0 else 8)
            P[i, j] = (x, y, z); UV[i, j] = (x / 96, y / 96)
    N = grid_normals(P)
    if N[ny // 2, nx // 2, 2] < 0: N = -N
    ti.grid(P, N, UV)
    return X


def make_bow(m, c, size, bw):
    """two satin loops, two tails and a knot on top of a present (centre c on the lid)"""
    c = np.asarray(c, float)
    size = max(26, min(size, 80))
    for sg in (-1, 1):
        # loop: teardrop in the x-z plane leaning out
        path = []
        for t in np.linspace(0, 1, 22):
            a = 2 * math.pi * t
            x = sg * (size * 0.55) * (1 - math.cos(a)) * 0.9
            z = size * 0.42 * math.sin(a) * (1 - math.cos(a)) * 0.6 + 2
            path.append(c + [x, 0, z])
        tube(m, path, 2.2, nseg=6, ry=bw * 0.42, caps=(False, False), vlen=64)
        # tail lying on the lid
        tail = [c + [sg * 4, sg * 6, 2], c + [sg * size * 0.35, sg * size * 0.5, 2.5], c + [sg * size * 0.55, sg * size * 0.85, 2]]
        tube(m, tail, 1.6, nseg=6, ry=bw * 0.38, caps=(True, True), vlen=64)
    ellipsoid(m, c + [0, 0, 4], bw * 0.32, bw * 0.38, 7, nu=10, nv=6)


# ================================================================================================= small helpers
def turned(M, h, r, z0=0.0, n=16, bulbs=((0.15, 1.35), (0.55, 1.15)), foot=1.25):
    """turned wooden leg / spindle profile (bulbs = (height fraction, radius factor))"""
    prof = [(0, z0), (r * foot, z0), (r * foot, z0 + h * 0.04), (r * 0.8, z0 + h * 0.07)]
    for (f, k) in bulbs:
        prof += [(r * 0.85, z0 + h * (f - 0.06)), (r * k, z0 + h * f), (r * 0.8, z0 + h * (f + 0.06))]
    prof += [(r, z0 + h * 0.93), (r * 1.2, z0 + h * 0.97), (r * 1.2, z0 + h), (0, z0 + h)]
    revolve(M, prof, n=n, u_tiles=1, vlen=max(64, h))


def cushion(M, mn, mx, puff=10.0, r=14.0, k=4, tile=128.0):
    """pillowy box: faces bulge out by up to `puff` in the middle"""
    mn = np.asarray(mn, float); mx = np.asarray(mx, float); c = (mn + mx) / 2; H = (mx - mn) / 2
    def inf(x, y, z, n):
        u = [(x - c[0]) / H[0], (y - c[1]) / H[1], (z - c[2]) / H[2]]
        ax = int(np.argmax(np.abs(n)))
        o = [a for i, a in enumerate(u) if i != ax]
        return puff * max(0.0, (1 - o[0] ** 2)) * max(0.0, (1 - o[1] ** 2))
    rbox(M, mn, mx, r=r, k=k, tile=tile, inflate=inf)


CYC = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]])      # (u, v, w) -> (w, u, v): a polygon drawn in (y, z), extruded along x


def rot_y(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])


def rot_x(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])


def side_prism(M, poly_xz, y0, y1, tile=128.0):
    """extrude a polygon given in the x-z plane between y0 and y1 (rotation, so winding stays right)"""
    t = Mesh()
    prism(t, [(x, z) for (x, z) in poly_xz], 0, y1 - y0, tile=tile)
    # prism builds in x-y with z up; rotate +90 about x: (x, y, z) -> (x, -z, y), then shift so it spans y0..y1
    t.transform(rot_x(math.pi / 2), (0, y1, 0))
    M.add(t)


def icing(M, path, r=5.0, bumps=True):
    path = np.asarray(path, float)
    if bumps and len(path) > 1:
        # resample and make a piped "bead" line
        L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
        n = max(4, int(L[-1] / 4))
        t = np.linspace(0, L[-1], n)
        P = np.stack([np.interp(t, L, path[:, k]) for k in range(3)], 1)
        R = r * (0.75 + 0.25 * np.abs(np.sin(t / (r * 1.4) * math.pi)))
        tube(M, P, R, nseg=8, vlen=64)
    else:
        tube(M, path, r, nseg=8, vlen=64)


def loop_path(c, a, b, n=32, plane='xz', a0=0.0):
    c = np.asarray(c, float); out = []
    for t in np.linspace(0, 2 * math.pi, n + 1):
        u, v = a * math.cos(t + a0), b * math.sin(t + a0)
        out.append(c + ([u, 0, v] if plane == 'xz' else [0, u, v] if plane == 'yz' else [u, v, 0]))
    return np.array(out)


def bell_mesh(M, c, h, r):
    """hand bell (open mouth down) at c (top)"""
    c = np.asarray(c, float)
    prof = [(0, 0), (r * 0.25, -h * 0.05), (r * 0.42, -h * 0.35), (r * 0.62, -h * 0.75), (r * 0.95, -h * 0.95), (r, -h),
            (r * 0.9, -h * 0.98), (r * 0.55, -h * 0.72), (r * 0.36, -h * 0.3), (0, -h * 0.12)]
    t = Mesh(); revolve(t, prof, n=20); M.add(t, t=c)


# ================================================================================================= fireplace set
def mantel(L=1536, D=96, z_shelf=80, t_shelf=48, corbels=(-736, -512, 480, 704), pil=((-400, -320), (320, 400)), pil_h=544):
    """carved mantel: origin = wall face at the shelf's bottom-centre minus z_shelf (x = out of the wall). Shelf
    (local z 80..128) with a moulded edge, frieze, scroll corbels and two fluted pilasters down to the hearth."""
    X = Model(); W = X.mesh(S('wood_dark')); G = X.mesh(S('trim_gold', 'shiny'))
    zs = z_shelf
    rbox(W, (0, -L / 2, zs + 8), (D, L / 2, zs + t_shelf), r=6, k=3, tile=192)                 # shelf
    rbox(W, (0, -L / 2 + 8, zs - 4), (D - 6, L / 2 - 8, zs + 10), r=5, k=3, tile=192)          # moulding step
    tube(G, [(D - 4, -L / 2 + 10, zs + 4), (D - 4, L / 2 - 10, zs + 4)], 3, nseg=8)           # gilt bead
    rbox(W, (0, -L / 2 + 40, zs - 72), (14, L / 2 - 40, zs - 4), r=3, k=2, tile=192)          # frieze board
    for y in corbels:
        poly = [(0, zs - 80), (6, zs - 80), (14, zs - 64), (22, zs - 40), (34, zs - 22), (52, zs - 10), (74, zs - 6), (86, zs - 2),
                (88, zs), (0, zs)]
        side_prism(W, poly, y, y + 32, tile=64)
        tube(G, arc_path((40, y + 16, zs - 30), 12, 0, 300, n=14, axis='y'), 2.4, nseg=6)
    zp = zs - 80 - pil_h                       # pilaster foot (hearth top)
    for (ya, yb) in pil:
        rbox(W, (0, ya, zp + 24), (22, yb, zs - 80), r=3, k=2, tile=128)
        rbox(W, (0, ya - 6, zp), (30, yb + 6, zp + 24), r=4, k=2, tile=64)                     # base block
        rbox(W, (0, ya - 6, zs - 104), (30, yb + 6, zs - 80), r=4, k=2, tile=64)               # capital
        for k in range(3):
            yy = ya + (yb - ya) * (k + 1) / 4
            tube(G, [(23, yy, zp + 40), (23, yy, zs - 120)], 2.2, nseg=6)                       # flutes
    return X


def fire_grate():
    """iron fire basket with three logs (nonsolid decoration, origin on the firebox floor centre)"""
    X = Model(); I = X.mesh(S('metal_black', 'shiny')); B = X.mesh(S('log_bark')); E = X.mesh(S('log_end'))
    for y in (-150, 150):
        tube(I, [(-40, y, 0), (-40, y, 40), (-30, y, 46)], 4, nseg=8)
        tube(I, [(40, y, 0), (40, y, 40), (50, y, 60), (44, y, 70)], 4, nseg=8)
        I.add(_ball(7), t=(44, y, 72))
    for x in (-30, -10, 10, 30):
        tube(I, [(x, -160, 30), (x, 160, 30)], 3, nseg=6)
    for (x, z, y0, y1, r) in ((-24, 52, -150, 150, 22), (22, 50, -140, 160, 20), (0, 86, -120, 130, 19)):
        tube(B, [(x, y0, z), (x, y1, z)], r, nseg=12, caps=(False, False), utiles=1, vlen=128)
        for y, sg in ((y0, -1), (y1, 1)):
            disc_axis(E, (x, y, z), r, (0, sg, 0))
    return X


def _ball(r, n=10):
    m = Mesh(); sphere(m, (0, 0, 0), r, nu=n, nv=n // 2 + 2); return m


def disc_axis(M, c, r, nrm, n=16):
    nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm)
    a = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(nrm, a); u /= np.linalg.norm(u); v = np.cross(nrm, u)
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = [np.asarray(c) + r * (math.cos(t) * u + math.sin(t) * v) for t in angs]
    M.poly(pts, nrm, [(0.5 + 0.5 * math.cos(t), 0.5 + 0.5 * math.sin(t)) for t in angs])


def stocking(col='velvet_red', toe=1):
    """Christmas stocking hanging from a brass hook; origin = hook on the mantel front (stocking hangs down -z, toe +y)"""
    X = Model(); F = X.mesh(S(col)); C = X.mesh(S('knit')); H = X.mesh(S('brass', 'shiny'))
    path = [(10, 0, -40), (10, 0, -110), (10, 0, -150), (10, toe * 8, -175), (10, toe * 30, -190), (10, toe * 60, -196), (10, toe * 78, -192)]
    rad = [26, 26, 25, 25, 23, 20, 12]
    tube(F, path, rad, nseg=14, ry=[16, 16, 16, 16, 15, 14, 10], caps=(False, True), vlen=96)
    tube(C, [(10, 0, -6), (10, 0, -46)], 30, nseg=14, ry=20, caps=(True, True), vlen=64)
    tube(H, [(0, 0, 2), (6, 0, 2), (10, 0, -2), (10, 0, -6)], 2.5, nseg=6)
    return X


def garland(L=1536, sag=26, nsw=6):
    """pine garland swagging along y with berries and little lights; origin at the hanging line's centre"""
    X = Model(); N = X.mesh(S('needles')); Rb = X.mesh(S('bauble_red', 'shiny'))
    path = []
    for k in range(nsw * 16 + 1):
        t = k / (nsw * 16)
        y = -L / 2 + L * t
        z = -sag * math.sin(math.pi * ((k % 16) / 16))
        path.append((0, y, z))
    rr = random.Random(3)
    radii = [11 + 3 * math.sin(k * 1.7) for k in range(len(path))]
    tube(N, path, radii, nseg=10, vlen=64)
    for k in range(0, len(path), 16):                       # brass pins into the shelf edge at the top of every swag
        y = path[k][1]
        tube(X.mesh(S('brass', 'shiny')), [(4, y, -2), (-10, y, 2)], 3, nseg=6)
        X.mesh(S('brass', 'shiny')).add(_ball(5, 8), t=(5, y, -2))
    for k in range(0, len(path), 5):
        p = np.array(path[k]) + [rr.uniform(6, 12), rr.uniform(-6, 6), rr.uniform(-8, 4)]
        Rb.add(_ball(4.5, 8), t=p)
    for k in range(8, len(path), 16):
        p = np.array(path[k]) + [12, 0, -10]
        b = Mesh(); ellipsoid(b, (0, 0, -6), 4.5, 4.5, 7, nu=8, nv=6)
        X.mesh(S(['bulb_red', 'bulb_yellow', 'bulb_green', 'bulb_blue'][(k // 16) % 4], 'glow', tag=str((k // 16) % 4))).add(b, t=p)
    return X


def candlestick(h=96, r=12, col='candle_white', holder=True):
    """brass candlestick with a dripping candle (flame is a separate sprite brush at z = total height)"""
    X = Model(); B = X.mesh(S('brass', 'shiny')); Cn = X.mesh(S(col)); Wx = X.mesh(S('wax_top'))
    z0 = 0
    if holder:
        revolve(B, [(0, 0), (r * 2.0, 0), (r * 2.0, 3), (r * 1.2, 8), (r * 0.6, 14), (r * 0.7, 22), (r * 1.4, 26), (r * 1.4, 30), (0, 30)], n=16)
        z0 = 30
    revolve(Cn, [(r, z0), (r, z0 + h - 4), (r * 0.9, z0 + h)], n=14, u_tiles=1,
            rfun=lambda a, rr, z: rr + (1.6 * max(0, math.sin(5 * a)) if z > z0 + h * 0.6 else 0))
    disc(Wx, r * 0.9, z0 + h, n=14)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        tube(Wx, [(r * math.cos(a), r * math.sin(a), z0 + h - 1), (r * 1.08 * math.cos(a), r * 1.08 * math.sin(a), z0 + h - 18 - 8 * k)],
             [2.6, 1.8], nseg=6)
    tube(X.mesh(S('metal_black')), [(0, 0, z0 + h), (0, 0, z0 + h + 6)], 0.9, nseg=4)
    return X


def nutcracker(coat='nut_red', s=1.0):
    """wooden nutcracker soldier (300 tall at s 1, origin = base centre, faces +x)"""
    X = Model()
    K, Wt, Sk, Cc, G = X.mesh(S('nut_black', 'shiny')), X.mesh(S('nut_white')), X.mesh(S('nut_skin')), X.mesh(S(coat)), X.mesh(S('trim_gold', 'shiny'))
    q = lambda v: v * s
    revolve(K, [(0, 0), (q(42), 0), (q(42), q(14)), (q(36), q(16)), (0, q(16))], n=20)                     # base
    for sg in (-1, 1):
        tube(K, [(q(4), sg * q(15), q(16)), (q(2), sg * q(15), q(40))], q(11), nseg=10)                     # boots
        tube(Wt, [(0, sg * q(15), q(40)), (0, sg * q(15), q(86))], q(10), nseg=10, caps=(False, False))     # legs
    revolve(Cc, [(0, q(84)), (q(30), q(84)), (q(34), q(110)), (q(30), q(150)), (q(26), q(176)), (0, q(178))], n=20)  # coat
    tube(K, arc_path((0, 0, q(112)), q(33), 0, 360, n=25), q(4.5), nseg=6, caps=(False, False))           # belt
    G.add(_ball(q(5)), t=(q(33), 0, q(112)))
    for sg in (-1, 1):
        tube(Cc, [(0, sg * q(30), q(166)), (q(4), sg * q(40), q(140)), (q(10), sg * q(38), q(112))], q(9), nseg=10)   # arms
        Sk.add(_ball(q(9)), t=(q(12), sg * q(37), q(104)))
        tube(G, [(q(-2), sg * q(28), q(168)), (q(2), sg * q(36), q(162))], q(7), nseg=8)                    # epaulettes
    ellipsoid(Sk, (0, 0, q(204)), q(22), q(22), q(26), nu=16, nv=10)                                        # head
    ellipsoid(Wt, (q(10), 0, q(190)), q(16), q(22), q(14), nu=14, nv=8)                                     # beard
    Sk.add(_ball(q(6)), t=(q(22), 0, q(206)))                                                               # nose
    for sg in (-1, 1): K.add(_ball(q(3)), t=(q(20), sg * q(8), q(214)))                                     # eyes
    revolve(K, [(0, q(222)), (q(24), q(222)), (q(23), q(282)), (q(20), q(290)), (0, q(292))], n=18)         # tall hat
    tube(G, arc_path((0, 0, q(232)), q(24.5), 0, 360, n=25), q(3), nseg=6, caps=(False, False))
    tube(Cc, [(q(10), 0, q(288)), (q(12), 0, q(312)), (q(4), 0, q(330))], [q(5), q(7), q(2)], nseg=8)        # plume
    return X


def mantel_clock():
    """small arched mantel clock (origin base centre, face +x), 160 wide 120 tall"""
    X = Model(); W = X.mesh(S('wood_dark', 'shiny')); B = X.mesh(S('brass', 'shiny')); F = X.mesh(S('clockface'))
    rbox(W, (-20, -80, 8), (20, 80, 70), r=6, k=3, tile=64)
    arch = Mesh(); prism(arch, [(80 * math.cos(a), 55 * math.sin(a)) for a in np.linspace(0, math.pi, 13)], -18, 18, tile=64)
    arch.transform(CYC, (0, 0, 70))
    W.add(arch)
    for y in (-64, 64):
        B.add(_ball(9), t=(0, y, 4))
    disc_axis(B, (21, 0, 68), 46, (1, 0, 0), n=24)
    disc_axis(F, (22, 0, 68), 40, (1, 0, 0), n=24)
    B.add(_ball(7), t=(0, 0, 128))
    return X


def fire_tools():
    """fireside companion set: weighted base, stand, poker, shovel, brush (origin base centre)"""
    X = Model(); I = X.mesh(S('metal_black', 'shiny')); B = X.mesh(S('brass', 'shiny')); Bk = X.mesh(S('log_bark'))
    revolve(I, [(0, 0), (40, 0), (40, 8), (30, 18), (8, 24), (0, 24)], n=16)
    tube(B, [(0, 0, 24), (0, 0, 380)], 4, nseg=8)
    B.add(_ball(8), t=(0, 0, 386))
    tube(B, [(-14, 0, 350), (14, 0, 350)], 2.5, nseg=6)
    for (dx, dy, kind) in ((-12, 0, 'poker'), (10, 8, 'shovel'), (2, -12, 'brush')):
        tube(I, [(dx, dy, 40), (dx, dy, 350)], 2.5, nseg=6)
        B.add(_ball(5), t=(dx, dy, 356))
        if kind == 'poker': tube(I, [(dx, dy, 40), (dx + 10, dy, 30)], 2.5, nseg=6)
        if kind == 'shovel': rbox(I, (dx - 14, dy - 2, 26), (dx + 14, dy + 2, 60), r=1.5, k=2, tile=32)
        if kind == 'brush': ellipsoid(Bk, (dx, dy, 52), 10, 10, 22, nu=10, nv=6)
    return X


def stool(r=96, h=200):
    X = Model(); W = X.mesh(S('wood_mid', 'shiny'))
    revolve(W, [(0, h - 16), (r, h - 16), (r + 2, h - 8), (r, h), (0, h)], n=24)
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(W, [(r * 0.55 * math.cos(a), r * 0.55 * math.sin(a), h - 16), (r * 0.85 * math.cos(a), r * 0.85 * math.sin(a), 0.5)], [9, 7], nseg=10)
    return X


def frame(w, h, d=14, b=36):
    """ornate gilt picture frame round a w x h picture on the wall (origin = wall face, picture centre at z h/2)"""
    X = Model(); G = X.mesh(S('trim_gold', 'shiny'))
    for (y0, y1, z0, z1) in ((-w / 2 - b, w / 2 + b, -b, 0), (-w / 2 - b, w / 2 + b, h, h + b), (-w / 2 - b, -w / 2, 0, h), (w / 2, w / 2 + b, 0, h)):
        rbox(G, (0, y0, z0), (d, y1, z1), r=6, k=3, tile=96)
    for (p0, p1) in (((d, -w / 2 - b / 2, -b / 2), (d, w / 2 + b / 2, -b / 2)), ((d, -w / 2 - b / 2, h + b / 2), (d, w / 2 + b / 2, h + b / 2)),
                     ((d, -w / 2 - b / 2, -b / 2), (d, -w / 2 - b / 2, h + b / 2)), ((d, w / 2 + b / 2, -b / 2), (d, w / 2 + b / 2, h + b / 2))):
        icing(G, [p0, p1], r=4)
    return X


# ================================================================================================= furniture
def armchair():
    """wingback armchair, origin = floor centre, faces +x: depth 416 (x), width 448 (y), back top 720"""
    X = Model(); V = X.mesh(S('velvet_red')); T = X.mesh(S('tartan')); W = X.mesh(S('wood_dark', 'shiny'))
    G = X.mesh(S('trim_gold', 'shiny')); Kn = X.mesh(S('knit'))
    D, Wd = 208, 224
    for (x, y) in ((-D + 30, -Wd + 30), (-D + 30, Wd - 30), (D - 30, -Wd + 30), (D - 30, Wd - 30)):
        l = Mesh(); turned(l, 40, 14, n=12, bulbs=((0.5, 1.3),)); W.add(l, t=(x, y, 0))
    rbox(V, (-D, -Wd, 40), (D, Wd, 224), r=22, k=4, tile=192)                          # base
    tube(G, [(D + 1, -Wd + 20, 60), (D + 1, Wd - 20, 60)], 3, nseg=6)                 # gilt piping
    cushion(T, (-D + 70, -Wd + 64, 222), (D - 6, Wd - 64, 276), puff=10, r=16)         # seat cushion
    rbox(V, (-D, -Wd, 222), (-D + 96, Wd, 690), r=30, k=4, tile=192)                   # back
    ellipsoid(V, (-D + 48, 0, 680), 48, Wd - 10, 48, nu=20, nv=8)                       # rounded crest
    cushion(V, (-D + 92, -Wd + 70, 270), (-D + 140, Wd - 70, 640), puff=10, r=18)      # back cushion
    for sg in (-1, 1):
        rbox(V, (-D, sg * Wd - (64 if sg > 0 else 0), 222), (D - 30, sg * Wd + (0 if sg > 0 else 64), 380), r=20, k=4, tile=192)  # arm
        tube(V, [(-D + 40, sg * (Wd - 32), 392), (D - 12, sg * (Wd - 32), 392)], 36, nseg=16, vlen=192)                     # rolled arm
        disc_axis(G, (D + 25, sg * (Wd - 32), 392), 24, (1, 0, 0), n=16)
        wing = [(-D, 380), (-D, 640), (-D + 90, 650), (-D + 170, 560), (-D + 200, 430), (-D + 190, 380)]
        side_prism(V, wing, sg * Wd - (26 if sg > 0 else 0), sg * Wd + (0 if sg > 0 else 26), tile=192)
    return X


def footstool():
    X = Model(); V = X.mesh(S('velvet_red')); T = X.mesh(S('tartan')); W = X.mesh(S('wood_dark', 'shiny'))
    rbox(V, (-130, -90, 30), (130, 90, 80), r=12, k=3, tile=128)
    cushion(T, (-126, -86, 78), (126, 86, 112), puff=8, r=14)
    for (x, y) in ((-110, -70), (-110, 70), (110, -70), (110, 70)):
        l = Mesh(); turned(l, 30, 10, n=10, bulbs=((0.5, 1.3),)); W.add(l, t=(x, y, 0))
    return X


def side_table(r=128, h=336):
    X = Model(); W = X.mesh(S('wood_dark', 'shiny'))
    revolve(W, [(0, 0), (96, 0), (96, 10), (70, 22), (30, 34), (22, 60), (30, 120), (18, 200), (26, 280), (40, h - 36), (0, h - 36)], n=24)
    revolve(W, [(0, h - 34), (r - 4, h - 34), (r + 2, h - 26), (r + 2, h - 6), (r - 2, h), (0, h)], n=36)
    return X


def floor_lamp(h=1240):
    X = Model(); B = X.mesh(S('brass', 'shiny')); Sh = X.mesh(S('cushion_white'))
    revolve(B, [(0, 0), (80, 0), (80, 8), (60, 18), (16, 30), (12, 50), (16, 60), (10, 80)], n=20)
    tube(B, [(0, 0, 80), (0, 0, h)], 9, nseg=10, caps=(False, True))
    for z in (400, 800): B.add(_ball(15, 10), t=(0, 0, z))
    revolve(Sh, [(150, h), (100, h + 160)], n=48, rfun=lambda a, r, z: r + 5 * abs(math.sin(12 * a)))
    revolve(Sh, [(100, h + 160), (150, h)], n=48, rfun=lambda a, r, z: r + 5 * abs(math.sin(12 * a)) - 3)
    tube(X.mesh(S('trim_gold', 'shiny')), arc_path((0, 0, 0), 151, 0, 360, n=49, z=h), 3, nseg=6, caps=(False, False))
    disc(X.mesh(S('lampglow', 'glow', wave='identity')), 140, h + 2, up=False, n=32)
    B.add(_ball(10), t=(0, 0, h + 175))
    return X


def sofa(L=1024, D=448):
    """three-seat green velvet sofa, origin floor centre, faces +x (seat front at x +D/2)"""
    X = Model(); V = X.mesh(S('velvet_green')); T = X.mesh(S('tartan')); W = X.mesh(S('wood_dark', 'shiny'))
    G = X.mesh(S('trim_gold', 'shiny')); R = X.mesh(S('velvet_red'))
    hd, hl = D / 2, L / 2
    for (x, y) in ((-hd + 30, -hl + 30), (-hd + 30, hl - 30), (hd - 30, -hl + 30), (hd - 30, hl - 30), (hd - 30, 0), (-hd + 30, 0)):
        l = Mesh(); turned(l, 44, 15, n=12, bulbs=((0.5, 1.3),)); W.add(l, t=(x, y, 0))
    rbox(V, (-hd, -hl, 44), (hd, hl, 256), r=24, k=4, tile=192)
    tube(G, [(hd + 1, -hl + 30, 70), (hd + 1, hl - 30, 70)], 3, nseg=6)
    rbox(V, (-hd, -hl + 100, 250), (-hd + 192, hl - 100, 640), r=60, k=5, tile=192)          # back (rounded top)
    for k in range(3):
        y0 = -hl + 128 + (L - 256) * k / 3; y1 = -hl + 128 + (L - 256) * (k + 1) / 3
        cushion(T, (-hd + 190, y0 + 4, 254), (hd - 8, y1 - 4, 296), puff=9, r=16)              # seat cushions
        cushion(V, (-hd + 186, y0 + 6, 296), (-hd + 236, y1 - 6, 560), puff=10, r=18)          # back cushions
    for sg in (-1, 1):
        rbox(V, (-hd, sg * hl - (128 if sg > 0 else 0), 250), (hd - 20, sg * hl + (0 if sg > 0 else 128), 400), r=26, k=4, tile=192)
        tube(V, [(-hd + 40, sg * (hl - 64), 410), (hd - 8, sg * (hl - 64), 410)], 58, nseg=16, vlen=192)
        disc_axis(G, (hd + 51, sg * (hl - 64), 410), 34, (1, 0, 0), n=16)
    # throw pillows leaning on the back (match the old brush pillows)
    for (yc, M_) in ((-160, R), (300, T)):
        p = Mesh(); cushion(p, (-36, -76, -76), (36, 76, 76), puff=18, r=30)
        M_.add(p, rot_y(-0.35), (-hd + 280, yc, 380))
    return X


def coffee_table(w=384, d=544, h=320):
    X = Model(); W = X.mesh(S('wood_dark', 'shiny'))
    rbox(W, (-w / 2, -d / 2, h - 32), (w / 2, d / 2, h), r=8, k=3, tile=256)
    rbox(W, (-w / 2 + 20, -d / 2 + 20, h - 64), (w / 2 - 20, d / 2 - 20, h - 30), r=4, k=2, tile=256)     # apron
    for (x, y) in ((-w / 2 + 32, -d / 2 + 32), (w / 2 - 32, -d / 2 + 32), (-w / 2 + 32, d / 2 - 32), (w / 2 - 32, d / 2 - 32)):
        l = Mesh(); turned(l, h - 32, 16, n=14); W.add(l, t=(x, y, 0))
    return X


def sideboard(L=928, D=304, H=592):
    """panelled sideboard, origin floor centre, faces +x: plinth, three cupboards with raised panels and brass
    knobs, moulded cornice, marble top (walkable, top at H)"""
    X = Model(); W = X.mesh(S('wood_mid', 'shiny')); Dk = X.mesh(S('wood_dark', 'shiny')); Mb = X.mesh(S('marble', 'shiny'))
    B = X.mesh(S('brass', 'shiny'))
    hd, hl = D / 2, L / 2
    rbox(Dk, (-hd, -hl, 0), (hd, hl, 48), r=6, k=2, tile=192)
    rbox(W, (-hd, -hl, 48), (hd - 8, hl, 560), r=4, k=2, tile=192)
    for k in range(3):
        y0 = -hl + L * k / 3 + 22; y1 = -hl + L * (k + 1) / 3 - 22
        rbox(Dk, (hd - 10, y0, 76), (hd + 4, y1, 532), r=4, k=2, tile=192)              # door
        rbox(W, (hd + 2, y0 + 30, 110), (hd + 12, y1 - 30, 500), r=6, k=3, tile=192)     # raised panel
        B.add(_ball(10), t=(hd + 18, y1 - 50 if k < 2 else y0 + 50, 310))
    rbox(Dk, (-hd, -hl - 8, 540), (hd + 8, hl + 8, 562), r=6, k=3, tile=192)            # cornice
    rbox(Mb, (-hd - 16, -hl - 16, 560), (hd + 16, hl + 0, H), r=6, k=3, tile=256)       # marble top (matches the brush)
    return X


def grandfather_clock(w=208, d=192):
    """long-case clock (origin floor centre, faces +x) 1600 tall: plinth, waist with a glazed door, hood with columns,
    arched crest and finials. The swinging pendulum stays a func_pendulum brush inside."""
    X = Model(); W = X.mesh(S('wood_dark', 'shiny')); B = X.mesh(S('brass', 'shiny')); F = X.mesh(S('clockface'))
    Gl = X.mesh(S('glass', 'glass'))
    hw, hd = d / 2, w / 2                       # x depth half, y width half
    rbox(W, (-hw, -hd, 0), (hw, hd, 160), r=8, k=3, tile=192)
    for y in (-hd + 16, hd - 16):
        for x in (-hw + 16, hw - 16): B.add(_ball(12), t=(x, y, 4))
    rbox(W, (-hw, -hd, 150), (-hw + 24, hd, 1130), r=4, k=2, tile=192)                     # back
    for sg in (-1, 1):
        rbox(W, (-hw + 24, sg * hd - (24 if sg > 0 else 0), 150), (hw, sg * hd + (0 if sg > 0 else 24), 1130), r=4, k=2, tile=192)
    for (z0, z1) in ((150, 176), (1100, 1130)):
        rbox(W, (hw - 24, -hd, z0), (hw + 4, hd, z1), r=4, k=2, tile=192)                    # door rails
    for sg in (-1, 1):
        rbox(W, (hw - 24, sg * (hd - 12) - 12, 170), (hw + 4, sg * (hd - 12) + 12, 1110), r=3, k=2, tile=192)
    Gl.quad((hw - 6, -hd + 24, 176), (hw - 6, hd - 24, 176), (hw - 6, hd - 24, 1100), (hw - 6, -hd + 24, 1100), tile=256, n=(1, 0, 0))
    rbox(W, (-hw - 12, -hd - 12, 1120), (hw + 12, hd + 12, 1160), r=6, k=3, tile=192)        # hood base moulding
    rbox(W, (-hw, -hd, 1150), (hw - 10, hd, 1460), r=4, k=2, tile=192)                       # hood
    for sg in (-1, 1):
        tube(B, [(hw - 4, sg * (hd - 12), 1160), (hw - 4, sg * (hd - 12), 1450)], 9, nseg=10)   # columns
    disc_axis(B, (hw - 9, 0, 1260), 84, (1, 0, 0), n=32)
    disc_axis(F, (hw - 8, 0, 1260), 78, (1, 0, 0), n=32)
    rbox(W, (-hw - 12, -hd - 12, 1450), (hw + 12, hd + 12, 1480), r=6, k=3, tile=192)
    crest = Mesh(); prism(crest, [(-hd - 6, 0)] + [((hd + 6) * math.cos(a), 110 * math.sin(a)) for a in np.linspace(math.pi, 0, 15)] + [(hd + 6, 0)], -hw - 6, hw + 6, tile=128)
    crest.transform(CYC, (0, 0, 1480))
    W.add(crest)
    for y in (-hd + 6, 0, hd - 6):
        z = 1480 + (110 if y == 0 else 10)
        revolve(B, [(0, z), (10, z), (12, z + 12), (6, z + 24), (9, z + 34), (0, z + 54)], n=10, cy=y)
    return X


def mesh_star(r1, r2, t):
    m = Mesh()
    pts = [np.array([(r1 if k % 2 == 0 else r2) * math.sin(k * math.pi / 5), 0, (r1 if k % 2 == 0 else r2) * math.cos(k * math.pi / 5)]) for k in range(10)]
    for sgn in (-1, 1):
        apex = np.array([0, sgn * t, 0])
        for k in range(10):
            a, b = pts[k], pts[(k + 1) % 10]
            n = np.cross(b - a, apex - a); n /= np.linalg.norm(n)
            if n[1] * sgn < 0: n = -n
            m.poly([a, b, apex], n, [(0.5 + a[0] / 200, 0.5 - a[2] / 200), (0.5 + b[0] / 200, 0.5 - b[2] / 200), (0.5, 0.5)])
    return m


def paper_star(hang=300):
    """glowing paper star on a thread from the ceiling (origin = ceiling point, hangs down -z)"""
    X = Model()
    X.mesh(S('star_gold', 'glow')).add(mesh_star(70, 30, 16), t=(0, 0, -hang - 70))
    ceiling_hook(X)
    tube(X.mesh(S('wire')), [(0, 0, -16), (0, 0, -hang + 2)], 0.9, nseg=4)
    return X


def ceiling_hook(X):
    revolve(X.mesh(S('brass', 'shiny')), [(0, 0), (14, 0), (12, -4), (5, -8), (3, -16), (0, -18)], n=12)


def mistletoe(hang=260):
    X = Model(); L = X.mesh(S('paint_green')); Bw = X.mesh(S('nut_white', 'shiny')); R = X.mesh(S('velvet_red'))
    ceiling_hook(X)
    tube(X.mesh(S('wire')), [(0, 0, -16), (0, 0, -hang)], 0.9, nseg=4)
    rr = random.Random(11)
    for k in range(14):
        a = 2 * math.pi * k / 14 + rr.uniform(-0.2, 0.2); el = rr.uniform(-0.9, 0.5)
        d = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)])
        c = np.array([0, 0, -hang - 50]) + d * 30
        e = Mesh(); ellipsoid(e, (0, 0, 0), 26, 9, 3, nu=10, nv=4)
        Rm = rot_z(a) @ rot_y(-el)
        L.add(e, Rm, c + d * 18)
        tube(L, [c - d * 20, c + d * 6], 2, nseg=5)
    for k in range(9):
        Bw.add(_ball(6, 8), t=(rr.uniform(-18, 18), rr.uniform(-18, 18), -hang - 60 + rr.uniform(-16, 10)))
    for sg in (-1, 1):
        tube(R, loop_path((sg * 14, 0, -hang - 8), 14, 10, n=16, plane='xz'), 2, nseg=6, ry=6, caps=(False, False))
    return X


# ================================================================================================= wreaths, pyramid, globe, plants
def wreath(R=140, r=32, bow=True):
    """wall wreath: origin = wall point at the ring centre, ring stands in the y-z plane in front of the wall (+x)"""
    X = Model(); N = X.mesh(S('needles')); Rb = X.mesh(S('bauble_red', 'shiny')); Pc = X.mesh(S('bark')); Rib = X.mesh(S('ribbon_gold', 'shiny'))
    path = [(r + 2, R * math.cos(a), R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 73)]
    rad = [r + 6 * math.sin(9 * a) * math.sin(5 * a + 1) for a in np.linspace(0, 2 * math.pi, 73)]
    tube(N, path, rad, nseg=14, caps=(False, False), vlen=96)
    rr = random.Random(5)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.3
        c = np.array([r * 1.6 + 6, R * math.cos(a), R * math.sin(a)])
        for j in range(3): Rb.add(_ball(7, 8), t=c + [0, rr.uniform(-9, 9), rr.uniform(-9, 9)])
        if k % 2: ellipsoid(Pc, c + [0, 18 * math.cos(a + 1), 18 * math.sin(a + 1)], 9, 9, 15, nu=10, nv=6, R=rot_axis((1, 0, 0), a))
    if bow:
        c = np.array([r * 2 + 8, 0, -R])
        for sg in (-1, 1):
            tube(Rib, loop_path(c + [0, sg * 30, 6], 30, 18, n=20, plane='yz'), 3, nseg=6, ry=14, caps=(False, False))
            tube(Rib, [c + [0, sg * 4, 0], c + [0, sg * 30, -50], c + [0, sg * 40, -84]], 3, nseg=6, ry=13)
        ellipsoid(Rib, c, 10, 14, 12, nu=10, nv=6)
    return X


def advent_wreath(R=95, r=24):
    """table Advent wreath with four red candles (flames are sprite brushes), origin = table top centre"""
    X = Model(); N = X.mesh(S('needles')); Rb = X.mesh(S('bauble_red', 'shiny')); Gd = X.mesh(S('bauble_gold', 'shiny'))
    path = [(R * math.cos(a), R * math.sin(a), r * 0.8) for a in np.linspace(0, 2 * math.pi, 49)]
    tube(N, path, [r + 4 * math.sin(7 * a) for a in np.linspace(0, 2 * math.pi, 49)], nseg=12, caps=(False, False), ry=r * 0.8)
    rr = random.Random(9)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        (Rb if k % 2 else Gd).add(_ball(7, 8), t=(R * 1.15 * math.cos(a), R * 1.15 * math.sin(a), r * 1.3 + rr.uniform(-4, 4)))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c = (round(R * math.cos(a)), round(R * math.sin(a)))
        revolve(X.mesh(S('brass', 'shiny')), [(0, 32), (18, 32), (18, 36), (14, 40), (0, 40)], n=12, cx=c[0], cy=c[1])
        revolve(X.mesh(S('candle_red')), [(12, 36), (12, 132), (10.8, 136)], n=12, cx=c[0], cy=c[1])
        disc(X.mesh(S('wax_top')), 10.8, 136, n=12, cx=c[0], cy=c[1])
    return X


def pyramid_base(r=112):
    """static base of the Christmas pyramid: turned wooden plate with four candle holders + candles (origin = base)"""
    X = Model(); W = X.mesh(S('pyramid_wood', 'shiny'))
    revolve(W, [(0, 0), (r, 0), (r + 4, 8), (r, 20), (r - 10, 24), (0, 24)], n=32)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        cx, cy = 90 * math.cos(a), 90 * math.sin(a)
        revolve(W, [(0, 24), (14, 24), (14, 30), (9, 36), (0, 36)], n=10, cx=cx, cy=cy)
        revolve(X.mesh(S('candle_white')), [(8, 34), (8, 80), (7, 82)], n=10, cx=cx, cy=cy)
    tube(W, [(0, 0, 24), (0, 0, 40)], 14, nseg=10)
    return X


def pyramid_rotor():
    """rotating part of the Christmas pyramid (model2 of a func_rotating, origin = its origin brush 208 above the
    base): mast, two carved platforms with figures (angels, shepherds, a star), and the propeller crown"""
    X = Model(); W = X.mesh(S('pyramid_wood', 'shiny')); Wh = X.mesh(S('nut_white')); Gd = X.mesh(S('trim_gold', 'shiny'))
    R = X.mesh(S('nut_red')); Gr = X.mesh(S('nut_green')); Sk = X.mesh(S('nut_skin'))
    o = -208                                     # base level relative to the origin
    tube(W, [(0, 0, o + 40), (0, 0, o + 470)], 6, nseg=10)
    for (z, r) in ((o + 180, 80), (o + 300, 64)):
        revolve(W, [(0, z), (r, z), (r + 3, z + 4), (r, z + 8), (0, z + 8)], n=32)
        tube(Gd, arc_path((0, 0, 0), r + 2, 0, 360, n=33, z=z + 4), 1.6, nseg=6, caps=(False, False))
    for k in range(4):                           # lower platform: angels in white / shepherds in green-red
        a = 2 * math.pi * k / 4 + 0.4
        c = (56 * math.cos(a), 56 * math.sin(a))
        M_ = Wh if k % 2 == 0 else (Gr if k == 1 else R)
        revolve(M_, [(0, o + 188), (12, o + 188), (9, o + 220), (6, o + 232)], n=10, cx=c[0], cy=c[1])
        Sk.add(_ball(7, 8), t=(c[0], c[1], o + 240))
        if k % 2 == 0:
            for sg in (-1, 1):
                e = Mesh(); ellipsoid(e, (0, 0, 0), 4, 12, 9, nu=8, nv=4)
                Gd.add(e, rot_z(a), (c[0] - 6 * math.cos(a) + sg * 8 * -math.sin(a), c[1] - 6 * math.sin(a) + sg * 8 * math.cos(a), o + 222))
    for k in range(3):                           # upper platform: sheep
        a = 2 * math.pi * k / 3
        c = np.array([44 * math.cos(a), 44 * math.sin(a), o + 322])
        ellipsoid(Wh, c, 13, 8, 9, nu=10, nv=6, R=rot_z(a + math.pi / 2))
        Sk.add(_ball(5, 8), t=c + [13 * -math.sin(a), 13 * math.cos(a), 4])
    Gd.add(mesh_star(22, 9, 5), t=(0, 0, o + 350))
    for k in range(6):                           # propeller blades
        a = 2 * math.pi * k / 6
        bl = Mesh(); rbox(bl, (14, -14, -2), (124, 14, 2), r=1.5, k=2, tile=64)
        W.add(bl, rot_z(a) @ rot_x(0.5), (0, 0, o + 474))
    W.add(_ball(10), t=(0, 0, o + 482))
    return X


def snow_globe(r=70):
    X = Model(); W = X.mesh(S('wood_dark', 'shiny')); G = X.mesh(S('trim_gold', 'shiny'))
    revolve(W, [(0, 0), (76, 0), (76, 4), (70, 30), (60, 40), (0, 40)], n=24)
    tube(G, arc_path((0, 0, 0), 74, 0, 360, n=25, z=20), 2, nseg=6, caps=(False, False))
    revolve(X.mesh(S('snow')), [(0, 52), (r * 0.6, 44), (r * 0.62, 40)], n=24)
    rbox(X.mesh(S('gingerbread')), (-26, -20, 44), (26, 20, 80), r=3, k=2, tile=64)
    roof = Mesh(); side_prism(roof, [(-32, 78), (32, 78), (0, 104)], -24, 24, tile=64)
    X.mesh(S('icing')).add(roof)
    revolve(X.mesh(S('needles')), [(16, 46), (0, 100)], n=10, cx=-40, cy=18)
    sph = X.mesh(S('glass', 'glass'))
    ellipsoid(sph, (0, 0, 40 + r * 0.78), r, r, r, nu=24, nv=14, flat_bottom=-r * 0.78)
    rr = random.Random(4)
    for k in range(18):
        a = rr.uniform(0, 2 * math.pi); rad = rr.uniform(0, r * 0.7); z = rr.uniform(60, 40 + r * 1.5)
        X.mesh(S('nut_white')).add(_ball(2, 6), t=(rad * math.cos(a), rad * math.sin(a), z))
    return X


def poinsettia(s=0.45):
    X = Model(); P = X.mesh(S('pot_terra', 'shiny')); L = X.mesh(S('poinsettia')); Gn = X.mesh(S('paint_green')); Y = X.mesh(S('paint_yellow'))
    q = lambda v: v * s
    revolve(P, [(0, 0), (q(70), 0), (q(92), q(120)), (q(98), q(124)), (q(98), q(134)), (q(88), q(134)), (0, q(126))], n=20)
    rr = random.Random(2)
    for ring, (rad, el, cnt, M_) in enumerate(((q(150), -0.1, 7, Gn), (q(125), 0.15, 6, L), (q(85), 0.35, 5, L))):
        for k in range(cnt):
            a = 2 * math.pi * k / cnt + ring * 0.4
            e = Mesh(); ellipsoid(e, (0, 0, 0), rad * 0.5, rad * 0.2, q(3), nu=10, nv=4)
            M_.add(e, rot_z(a) @ rot_y(-el), (math.cos(a) * rad * 0.5, math.sin(a) * rad * 0.5, q(140) + ring * q(8)))
    for k in range(5): Y.add(_ball(q(7), 6), t=(rr.uniform(-q(12), q(12)), rr.uniform(-q(12), q(12)), q(160)))
    return X


# ================================================================================================= window
def curtain(w=160, h=1720, d=48, folds=5):
    """heavy velvet curtain, wavy folds along y (width w), hangs from z h, origin = floor centre against the wall,
    room side +x (the folds stay inside the old 48-deep brush), gold tie-back at 1/3 height"""
    X = Model(); C = X.mesh(S('curtain')); G = X.mesh(S('trim_gold', 'shiny'))
    ny, nz = folds * 8 + 1, 18
    P = np.zeros((nz, ny, 3)); UV = np.zeros((nz, ny, 2))
    for i, z in enumerate(np.linspace(0, h, nz)):
        tie = math.exp(-((z - h * 0.38) / (h * 0.08)) ** 2)
        width = w * (1 - 0.45 * tie)
        for j, t in enumerate(np.linspace(0, 1, ny)):
            y = -w / 2 + width * t + (w - width) * (0.15 if True else 0)
            x = 6 + (d - 12) * (0.5 + 0.5 * math.sin(2 * math.pi * folds * t)) * (1 - 0.3 * tie)
            P[i, j] = (x, y, z); UV[i, j] = (t * folds, -z / 256)
    N = grid_normals(P)
    if N[nz // 2, ny // 2, 0] < 0: N = -N
    C.grid(P, N, UV)
    P2 = P.copy(); P2[..., 0] -= 3
    C.grid(P2, -N, UV)
    tube(G, [(d + 4, -w * 0.3, h * 0.38), (d + 8, 0, h * 0.38 - 10), (d + 4, w * 0.3, h * 0.38)], 5, nseg=8)
    for sg in (-1, 1):
        tube(G, [(d + 6, sg * 10, h * 0.38 - 10), (d + 8, sg * 16, h * 0.38 - 90)], [4, 9], nseg=8)
    return X


def curtain_rod(L=2048):
    """brass curtain rod with finials and two Christmas bells on a red bow (origin = rod centre)"""
    X = Model(); B = X.mesh(S('brass', 'shiny')); G = X.mesh(S('trim_gold', 'shiny')); R = X.mesh(S('ribbon_gold', 'shiny'))
    tube(B, [(0, -L / 2 + 16, 0), (0, L / 2 - 16, 0)], 8, nseg=10)
    for sg in (-1, 1):
        B.add(_ball(14, 10), t=(0, sg * (L / 2 - 6), 0))
        tube(B, [(-60, sg * (L / 2 - 40), 0), (0, sg * (L / 2 - 40), 0)], 6, nseg=8)
        for k in range(8):
            tube(B, arc_path((0, sg * (L / 2 - 200 - k * 60), -8), 10, 0, 360, n=13, axis='y'), 1.6, nseg=5, caps=(False, False))
    for sx in (-110, 110):
        bell_mesh(G, (28, sx, -40), 100, 70)
        G.add(_ball(14, 8), t=(28, sx, -132))
        tube(R, [(28, sx, -40), (28, sx * 0.3, 20), (28, 0, 30)], 3, nseg=6, ry=14)
    for sg in (-1, 1):
        tube(R, loop_path((28, sg * 34, 40), 34, 22, n=20, plane='yz'), 3, nseg=6, ry=16, caps=(False, False))
    ellipsoid(R, (28, 0, 36), 14, 16, 14, nu=10, nv=6)
    return X


def seat_cushion(L=1504, D=224, h=32):
    X = Model(); T = X.mesh(S('tartan'))
    cushion(T, (-D / 2, -L / 2, 0), (D / 2, L / 2, h), puff=6, r=12)
    return X


def bolster():
    X = Model(); V = X.mesh(S('velvet_green')); G = X.mesh(S('trim_gold', 'shiny'))
    p = Mesh(); cushion(p, (-24, -70, -58), (24, 70, 58), puff=14, r=22)
    V.add(p, rot_x(0) @ rot_y(0.0), (0, 0, 58))
    for sg in (-1, 1): G.add(_ball(7, 8), t=(0, sg * 66, 116))
    return X


# ================================================================================================= gingerbread house
def ginger_house(x0, x1, y0, y1, hw, door, windows, ov=48, pitch=30, th=24):
    """gingerbread house shell matching the collision boxes in build_xmas.ginger_house() (origin = house centre on the
    floor): biscuit walls with door and windows, gables, two roof slabs with piped icing scallops and drips, candy
    tiles, ridge piping, candy-cane door posts, iced window frames and gumdrop corner posts"""
    X = Model(); Gb = X.mesh(S('gingerbread')); Ic = X.mesh(S('icing', 'shiny')); Rf = X.mesh(S('ginger_roof'))
    Cs = X.mesh(S('candystripe', 'shiny'))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    L = lambda x, y: (x - cx, y - cy)
    t = 32
    DX0, DX1, DZ = door
    boxes = [((x0, y1 - t, 0), (DX0, y1, hw)), ((DX1, y1 - t, 0), (x1, y1, hw)), ((DX0, y1 - t, DZ), (DX1, y1, hw)), ((x0, y0, 0), (x1, y0 + t, hw))]
    WY0, WY1, WZ0, WZ1 = windows
    for (xa, xb) in ((x0, x0 + t), (x1 - t, x1)):
        for (ya, yb, za, zb) in ((y0 + t, WY0, 0, hw), (WY1, y1 - t, 0, hw), (WY0, WY1, 0, WZ0), (WY0, WY1, WZ1, hw)):
            boxes.append(((xa, ya, za), (xb, yb, zb)))
    for (mn, mx) in boxes:
        rbox(Gb, (mn[0] - cx, mn[1] - cy, mn[2]), (mx[0] - cx, mx[1] - cy, mx[2]), r=3, k=2, tile=160)
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    tan = math.tan(math.radians(pitch)); half = hy
    ridge_b = hw + half * tan
    for xs in (-hx, hx - t):                                   # gables
        g = Mesh(); prism(g, [(-hy, hw), (hy, hw), (0, ridge_b)], xs, xs + t, tile=160)
        g.transform(CYC)
        Gb.add(g)
    # roof slabs: built flat then tilted about the ridge
    thc = th / math.cos(math.radians(pitch))
    for sg in (1, -1):
        slab = Mesh(); rbox(slab, (-hx - ov, 0, 0), (hx + ov, (half + ov) / math.cos(math.radians(pitch)), th), r=4, k=2, tile=192, faces='nsewb')
        top = Mesh(); rbox(top, (-hx - ov, 0, 0), (hx + ov, (half + ov) / math.cos(math.radians(pitch)), th), r=4, k=2, tile=192, faces='t')
        Rm = rot_x(-sg * math.radians(pitch)) if sg > 0 else rot_z(math.pi) @ rot_x(-math.radians(pitch))
        off = (0, 0, ridge_b)
        Gb.add(slab, Rm, off); Rf.add(top, Rm, off)
        # eave scallops + drips (local slab coords -> world via Rm)
        Ly = (half + ov) / math.cos(math.radians(pitch))
        pts = [Rm @ np.array([x, Ly, th * 0.5]) + off for x in np.linspace(-hx - ov, hx + ov, 40)]
        icing(Ic, pts, r=7)
        rr = random.Random(7 + sg)
        for x in np.linspace(-hx - ov + 12, hx + ov - 12, 22):
            p = Rm @ np.array([x, Ly - 2, 2]) + off
            dl = rr.uniform(14, 34)
            ellipsoid(Ic, p + [0, 0, -dl / 2], 6, 6, dl / 2 + 3, nu=8, nv=6)
        # candy tiles: gumdrops in rows
        cols = ['gumdrop_red', 'gumdrop_green', 'gumdrop_yellow', 'gumdrop_purple']
        for i, yy in enumerate(np.linspace(Ly * 0.2, Ly * 0.85, 3)):
            for j, x in enumerate(np.linspace(-hx + 30, hx - 30, 6)):
                if sg > 0 and i == 1 and 1 <= j <= 3: continue          # keep the Balloony spot clear
                p = Rm @ np.array([x + (20 if i % 2 else 0), yy, th]) + off
                g = Mesh(); revolve(g, [(0, 0), (14, 0), (13, 6), (8, 13), (0, 15)], n=12)
                X.mesh(S(cols[(i + j) % 4], 'shiny')).add(g, Rm, p)
    # ridge piping
    icing(Ic, [(x, 0, ridge_b + thc + 4) for x in np.linspace(-hx - ov, hx + ov, 30)], r=10)
    # corner posts: candy canes
    for (x, y) in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):
        tube(Cs, [(x, y, 0), (x, y, hw)], 13, nseg=12, vlen=96)
    # door: candy-cane posts and an iced arch
    for xd in (DX0 - 8, DX1 + 8):
        tube(Cs, [(xd - cx, hy + 8, 0), (xd - cx, hy + 8, DZ)], 9, nseg=10, vlen=64)
    icing(Ic, [((DX0 - 12) - cx + (DX1 - DX0 + 24) * u, hy + 8, DZ + 4 + 20 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 16)], r=7)
    # windows: piped frames + cross bars
    for xs, nx in ((-hx - 2, -1), (hx + 2, 1)):
        y_a, y_b = WY0 - cy, WY1 - cy
        frame_ = [(xs, y_a, WZ0), (xs, y_b, WZ0), (xs, y_b, WZ1), (xs, y_a, WZ1), (xs, y_a, WZ0)]
        icing(Ic, frame_, r=6)
        icing(Ic, [(xs, (y_a + y_b) / 2, WZ0), (xs, (y_a + y_b) / 2, WZ1)], r=4, bumps=False)
        icing(Ic, [(xs, y_a, (WZ0 + WZ1) / 2), (xs, y_b, (WZ0 + WZ1) / 2)], r=4, bumps=False)
    # wall-top and base icing lines
    for (pa, pb) in (((-hx, -hy - 2, hw), (hx, -hy - 2, hw)), ((-hx, hy + 2, hw), (hx, hy + 2, hw)),
                     ((-hx - 2, -hy, 12), (-hx - 2, hy, 12)), ((hx + 2, -hy, 12), (hx + 2, hy, 12))):
        icing(Ic, [pa, pb], r=6)
    return X


def candy_cane(h=300, r=18, hook=56, flip=False):
    """standing candy cane, origin = foot; hook bends toward +x (or -x if flip)"""
    X = Model(); C = X.mesh(S('candystripe', 'shiny'))
    s_ = -1 if flip else 1
    path = [(0, 0, 0), (0, 0, h)] + [(s_ * hook * (1 - math.cos(a)), 0, h + hook * math.sin(a)) for a in np.linspace(0.15, math.pi, 12)]
    path = np.array(path)
    path = np.concatenate([np.linspace(path[0], path[1], 8), path[2:]])
    tube(C, path, r, nseg=14, vlen=128, utiles=1)
    return X


def gumdrop(r=44, h=84, col='red'):
    X = Model(); G = X.mesh(S('gumdrop_' + col, 'shiny'))
    revolve(G, [(0, 0), (r, 0), (r * 0.98, h * 0.2), (r * 0.82, h * 0.6), (r * 0.5, h * 0.9), (0, h)], n=24,
            rfun=lambda a, rr, z: rr + 1.2 * math.sin(13 * a + z / 6))
    return X


def choc_table(w=200, d=120, h=120):
    X = Model(); C = X.mesh(S('choco', 'shiny')); Cs = X.mesh(S('candystripe', 'shiny'))
    rbox(C, (-w / 2, -d / 2, h - 30), (w / 2, d / 2, h - 12), r=3, k=2, tile=96)
    for i in range(4):
        for j in range(2):
            x0 = -w / 2 + 6 + i * (w - 12) / 4; y0 = -d / 2 + 6 + j * (d - 12) / 2
            rbox(C, (x0 + 2, y0 + 2, h - 14), (x0 + (w - 12) / 4 - 2, y0 + (d - 12) / 2 - 2, h), r=4, k=2, tile=96)
    for (x, y) in ((-w / 2 + 20, -d / 2 + 20), (w / 2 - 20, -d / 2 + 20), (-w / 2 + 20, d / 2 - 20), (w / 2 - 20, d / 2 - 20)):
        tube(Cs, [(x, y, 0), (x, y, h - 30)], 10, nseg=10)
    return X


def gingerman(h=256, w=128, t=16):
    """gingerbread man cookie standing up (origin = bottom centre, faces +-x): cookie-cutter outline extruded, piped
    icing outline, smile, eyes and gumdrop buttons on both faces"""
    from skimage import measure
    n = 128
    yy, xx = np.mgrid[0:n * 2, 0:n].astype(float)
    X_ = (xx - n / 2) / (n / 2) * (w / 2); Z = (n * 2 - yy) / (n * 2) * h
    def blob(cx, cz, rx, rz): return ((X_ - cx) / rx) ** 2 + ((Z - cz) / rz) ** 2 <= 1
    def capsule(p0, p1, r):
        p0 = np.array(p0); p1 = np.array(p1); d = p1 - p0; L2 = d @ d
        tt = np.clip(((X_ - p0[0]) * d[0] + (Z - p0[1]) * d[1]) / L2, 0, 1)
        return (X_ - p0[0] - tt * d[0]) ** 2 + (Z - p0[1] - tt * d[1]) ** 2 <= r * r
    m = blob(0, h * 0.82, w * 0.24, h * 0.14) | blob(0, h * 0.5, w * 0.27, h * 0.2)
    m |= capsule((-w * 0.18, h * 0.6), (-w * 0.44, h * 0.48), w * 0.1) | capsule((w * 0.18, h * 0.6), (w * 0.44, h * 0.48), w * 0.1)
    m |= capsule((-w * 0.1, h * 0.38), (-w * 0.24, h * 0.06), w * 0.11) | capsule((w * 0.1, h * 0.38), (w * 0.24, h * 0.06), w * 0.11)
    cs = measure.find_contours(m.astype(float), 0.5)
    c = max(cs, key=len)[::3]
    outline = [((x - n / 2) / (n / 2) * (w / 2), (n * 2 - y) / (n * 2) * h) for (y, x) in c]
    zmin = min(p[1] for p in outline); outline = [(p[0], p[1] - zmin) for p in outline]
    X = Model(); G = X.mesh(S('gingerbread')); Ic = X.mesh(S('icing', 'shiny'))
    def piece(poly):
        g = Mesh(); prism(g, poly, -t / 2, t / 2, tile=96); g.transform(CYC); G.add(g)
    def ell(cx, cz, rx, rz, k=20): return [(cx + rx * math.cos(a), cz + rz * math.sin(a)) for a in np.linspace(0, 2 * math.pi, k, endpoint=False)]
    def cap(p0, p1, r, k=8):
        p0 = np.array(p0); p1 = np.array(p1); d = (p1 - p0) / np.linalg.norm(p1 - p0); nrm = np.array([-d[1], d[0]])
        a0 = math.atan2(nrm[1], nrm[0])
        pts = [tuple(p1 + r * np.array([math.cos(a0 - a), math.sin(a0 - a)])) for a in np.linspace(0, math.pi, k)]
        pts += [tuple(p0 + r * np.array([math.cos(a0 + math.pi - a), math.sin(a0 + math.pi - a)])) for a in np.linspace(0, math.pi, k)]
        return pts
    zo = -zmin
    piece(ell(0, h * 0.82 + zo, w * 0.24, h * 0.14)); piece(ell(0, h * 0.5 + zo, w * 0.27, h * 0.2))
    for sg in (-1, 1):
        piece(cap((sg * w * 0.18, h * 0.6 + zo), (sg * w * 0.44, h * 0.48 + zo), w * 0.1))
        piece(cap((sg * w * 0.1, h * 0.38 + zo), (sg * w * 0.24, h * 0.06 + zo), w * 0.11))
    for sx in (-1, 1):
        xo = sx * (t / 2 + 1)
        inset = [(p[0] * 0.86, h * 0.5 + (p[1] - h * 0.5) * 0.9) for p in outline[::2]]
        icing(Ic, [(xo, u, z) for (u, z) in inset + inset[:1]], r=3)
        for k, zz in enumerate((0.58, 0.5, 0.42)):
            X.mesh(S(['gumdrop_red', 'gumdrop_green', 'gumdrop_yellow'][k], 'shiny')).add(_ball(8, 8), t=(xo, 0, h * zz + zo))
        for ey in (-0.07, 0.07):
            X.mesh(S('choco')).add(_ball(5, 6), t=(xo, w * ey, h * 0.86 + zo))
        icing(Ic, [(xo, w * 0.11 * math.cos(a), h * 0.8 + zo - w * 0.08 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 8)], r=2.5, bumps=False)
    return X


# ================================================================================================= roof: sleigh + reindeer
def sleigh(Lx=560, W=320):
    """Santa's sleigh (origin = centre of its footprint on the roof, front +x): swan-neck sides, curled gold runners
    with struts, velvet floor and side cushions, gold trim, open back with a step (matches the collision boxes)"""
    X = Model(); R = X.mesh(S('sleigh_red', 'shiny')); G = X.mesh(S('trim_gold', 'shiny')); V = X.mesh(S('velvet_red'))
    hx, hy = Lx / 2, W / 2
    fz = 64
    side = [(-hx, fz - 16), (hx - 20, fz - 16), (hx + 20, fz + 10), (hx + 40, fz + 60), (hx + 48, fz + 120), (hx + 40, fz + 200),
            (hx + 20, fz + 250), (hx - 20, fz + 262), (hx - 44, fz + 240), (hx - 40, fz + 210), (hx - 10, fz + 220), (hx + 8, fz + 196),
            (hx + 8, fz + 150), (hx - 30, fz + 168), (hx - 140, fz + 162), (-hx + 80, fz + 158), (-hx + 20, fz + 176), (-hx, fz + 172)]
    for sg in (-1, 1):
        side_prism(R, side, sg * hy - (24 if sg > 0 else 0), sg * hy + (0 if sg > 0 else 24), tile=192)
        trim = [(x, sg * (hy + 1) if sg > 0 else -hy - 1, z + 3) for (x, z) in side[6:16]]
        icing(G, trim, r=4, bumps=False)
    # front panel between the sides (curved)
    R.add(_xz_prism([(hx - 96, fz), (hx, fz), (hx + 16, fz + 120), (hx - 6, fz + 170), (hx - 96, fz + 160)], -hy + 24, hy - 24))
    rbox(V, (-hx, -hy + 24, fz - 16), (hx - 96, hy - 24, fz), r=2, k=2, tile=128, faces='t')        # velvet floor
    rbox(G, (-hx, -hy, fz - 16), (hx - 20, hy, fz - 2), r=3, k=2, tile=128, faces='nsewb')
    for (ya, yb) in ((-hy + 24, -hy + 56), (hy - 56, hy - 24)):
        cushion(V, (-hx + 96, ya, fz), (-hx + 256, yb, fz + 48), puff=6, r=10)
    # runners with a curl at the front, struts
    for yr in (-hy + 36, hy - 36):
        path = [(-hx - 30, yr, 14), (-hx, yr, 8)] + [(x, yr, 8) for x in np.linspace(-hx + 40, hx + 30, 8)]
        path += [(hx + 40 + 50 * math.sin(a), yr, 58 - 50 * math.cos(a)) for a in np.linspace(0.3, math.pi * 1.25, 10)]
        path += [(hx + 40 + 22 * math.sin(a) + 6, yr, 70 - 22 * math.cos(a)) for a in np.linspace(math.pi * 1.3, math.pi * 2.3, 6)]
        tube(G, path, 9, nseg=10, vlen=96)
        for xs in (-hx + 64, 0, hx - 64):
            tube(G, [(xs, yr, 14), (xs, yr, fz - 16)], 7, nseg=8)
    # step at the back
    rbox(G, (-hx - 64, -hy + 64, 0), (-hx, hy - 64, 32), r=4, k=2, tile=128)
    return X


def _xz_prism(poly, y0, y1, tile=192.0):
    t = Mesh(); side_prism(t, poly, y0, y1, tile=tile); return t


def sack(rx=100, ry=110, h=210, gifts=True, seed=1):
    """lumpy burlap sack tied with rope, presents poking out of the top (origin = bottom centre)"""
    X = Model(); B = X.mesh(S('burlap')); Rp = X.mesh(S('log_end'))
    rr = random.Random(seed)
    lumps = [(rr.uniform(0, 2 * math.pi), rr.uniform(-0.6, 0.9), rr.uniform(0.06, 0.13)) for _ in range(9)]
    def bump(p, t):
        k = 1.0
        for (a, e, amp) in lumps:
            d = math.acos(max(-1, min(1, math.cos(p) * math.cos(e) * math.cos(t - a) + math.sin(p) * math.sin(e))))
            k += amp * math.exp(-(d / 0.45) ** 2)
        return k
    ellipsoid(B, (0, 0, h * 0.42), rx, ry, h * 0.45, nu=24, nv=14, bump=bump, flat_bottom=-h * 0.42)
    revolve(B, [(rx * 0.32, h * 0.8), (rx * 0.22, h * 0.9), (rx * 0.3, h * 0.97), (rx * 0.45, h * 1.02)], n=20,
            rfun=lambda a, r, z: r + 4 * math.sin(9 * a))
    tube(Rp, arc_path((0, 0, 0), rx * 0.24, 0, 360, n=17, z=h * 0.9), 5, nseg=8, caps=(False, False))
    tube(Rp, [(rx * 0.24, 0, h * 0.9), (rx * 0.32, 10, h * 0.8), (rx * 0.3, 18, h * 0.66)], 4, nseg=6)
    if gifts:
        for (dx, dy, w_, d_, hh, pat, ang) in ((-14, 6, 48, 40, 50, 'red', 0.3), (16, -10, 36, 36, 40, 'blue', -0.4), (4, 20, 30, 30, 34, 'gold', 0.1)):
            gm = Mesh(); rbox(gm, (-w_ / 2, -d_ / 2, 0), (w_ / 2, d_ / 2, hh), r=3, k=2, tile=max(w_, d_))
            X.mesh(S('paper_' + pat)).add(gm, rot_z(ang) @ rot_y(0.2), (dx, dy, h * 0.86))
    return X


def reindeer(rudolph=False):
    """reindeer standing, facing +x (origin = between its hooves): body, neck, head, ears, branching antlers, legs with
    hooves, tail, red collar with a gold bell; rudolph=True gives it a glowing red nose"""
    X = Model(); F = X.mesh(S('reindeer')); Lf = X.mesh(S('reindeer_light')); A = X.mesh(S('antler', 'shiny'))
    K = X.mesh(S('nut_black', 'shiny')); Cl = X.mesh(S('velvet_red')); G = X.mesh(S('trim_gold', 'shiny'))
    ellipsoid(F, (0, 0, 162), 92, 40, 46, nu=20, nv=12)
    ellipsoid(Lf, (4, 0, 132), 70, 30, 18, nu=16, nv=8)
    for (x, y) in ((-60, -22), (-60, 22), (58, -22), (58, 22)):
        tube(F, [(x, y, 150), (x + (4 if x > 0 else -6), y, 90), (x, y, 20)], [16, 10, 8], nseg=10)
        revolve(K, [(0, 0), (10, 0), (9, 14), (0, 20)], n=10, cx=x, cy=y)
    tube(F, [(70, 0, 180), (92, 0, 230), (100, 0, 262)], [26, 20, 17], nseg=12)
    ellipsoid(F, (112, 0, 276), 30, 18, 20, nu=14, nv=8, R=rot_y(0.35))
    ellipsoid(Lf, (138, 0, 266), 16, 13, 12, nu=12, nv=6)
    nose = X.mesh(S('nose_red', 'glow', wave='wave sin 0.75 0.25 0 1')) if rudolph else K
    nose.add(_ball(9 if rudolph else 6, 10), t=(152, 0, 268))
    for sg in (-1, 1):
        K.add(_ball(4, 8), t=(126, sg * 13, 286))
        e = Mesh(); ellipsoid(e, (0, 0, 0), 6, 4, 16, nu=8, nv=6)
        F.add(e, rot_x(sg * 0.9), (100, sg * 22, 292))
        base = np.array([96, sg * 12, 296.0])
        main = [base, base + [-4, sg * 10, 30], base + [-16, sg * 22, 58], base + [-30, sg * 30, 84]]
        tube(A, main, [5, 4.5, 3.5, 2], nseg=8)
        for (f, dx, dy, dz) in ((0.33, 16, 4, 22), (0.66, 10, 8, 24), (1.0, 4, 14, 20)):
            p = np.array(main[int(f * 3)])
            tube(A, [p, p + [dx, sg * dy, dz]], [3, 1.5], nseg=6)
    tube(F, [(-92, 0, 178), (-104, 0, 190)], [10, 4], nseg=8)
    tube(Lf, [(-100, 0, 186), (-108, 0, 194)], [7, 3], nseg=8)
    tube(Cl, loop_path((86, 0, 214), 22, 24, n=20, plane='yz'), 5, nseg=8, ry=7, caps=(False, False))
    bell_mesh(G, (108, 0, 198), 18, 10)
    return X


# ================================================================================================= toys
def rocking_horse():
    """dapple-grey rocking horse on red bow rockers (origin = floor centre, faces +x)"""
    X = Model(); H = X.mesh(S('horse_white')); Mn = X.mesh(S('horse_mane')); R = X.mesh(S('paint_red', 'shiny'))
    Wd = X.mesh(S('wood_light', 'shiny')); G = X.mesh(S('trim_gold', 'shiny')); K = X.mesh(S('nut_black', 'shiny'))
    for sg in (-1, 1):
        arc = [(390 * math.sin(a), sg * 70, 400 - 390 * math.cos(a)) for a in np.linspace(-0.62, 0.62, 18)]
        tube(R, arc, 10, nseg=8, ry=12, vlen=128)
        for x in (-130, 130):
            tube(Wd, [(x, sg * 70, 400 - math.sqrt(390 ** 2 - x ** 2) + 6), (x * 0.9, sg * 46, 196)], 7, nseg=8)
    for x in (-180, 0, 180):
        tube(Wd, [(x, -70, 400 - math.sqrt(390 ** 2 - x ** 2) + 10), (x, 70, 400 - math.sqrt(390 ** 2 - x ** 2) + 10)], 6, nseg=8)
    ellipsoid(H, (0, 0, 266), 180, 70, 66, nu=22, nv=12)
    for (x, sg) in ((-120, -1), (-120, 1), (120, -1), (120, 1)):
        tube(H, [(x, sg * 40, 240), (x + (30 if x > 0 else -30), sg * 50, 190)], [24, 16], nseg=10)
    tube(H, [(140, 0, 300), (180, 0, 380), (196, 0, 430)], [48, 40, 34], nseg=14)
    ellipsoid(H, (232, 0, 470), 70, 38, 42, nu=16, nv=10, R=rot_y(0.5))
    ellipsoid(H, (288, 0, 446), 36, 30, 28, nu=12, nv=8)
    for sg in (-1, 1):
        e = Mesh(); ellipsoid(e, (0, 0, 0), 8, 6, 20, nu=8, nv=6); H.add(e, rot_x(sg * 0.4), (212, sg * 22, 516))
        K.add(_ball(7, 8), t=(262, sg * 30, 486))
        tube(G, [(250, sg * 40, 470), (276, sg * 34, 452)], 3, nseg=6)
    for k in range(7):
        f = k / 6
        x, z = 140 + 56 * f, 300 + 130 * f
        Mn.add(_ball(18 - 2 * f, 10), t=(x - 34, 0, z + 16 + 4 * math.sin(k * 2.2)))
    Mn.add(_ball(14, 10), t=(214, 0, 512))
    tube(Mn, [(-176, 0, 280), (-210, 0, 260), (-224, 0, 200)], [16, 14, 8], nseg=10)
    rbox(R, (-60, -74, 318), (60, 74, 340), r=8, k=3, tile=128)
    tube(G, [(-60, -78, 330), (60, -78, 330)], 3, nseg=6); tube(G, [(-60, 78, 330), (60, 78, 330)], 3, nseg=6)
    tube(G, [(150, -36, 420), (150, 36, 420)], 5, nseg=8)
    return X


def drum(r=110, h=150):
    X = Model(); R = X.mesh(S('paint_red', 'shiny')); G = X.mesh(S('trim_gold', 'shiny')); Wh = X.mesh(S('cushion_white'))
    Wd = X.mesh(S('wood_light', 'shiny'))
    revolve(R, [(r, 16), (r, h - 16)], n=36)
    for (z0, z1) in ((0, 16), (h - 16, h)):
        revolve(G, [(r - 4, z0), (r + 6, z0 + 2), (r + 6, z1 - 2), (r - 4, z1)], n=36)
    disc(Wh, r - 4, h, n=36); disc(Wh, r - 4, 0.5, up=False, n=36)
    pts = []
    for k in range(17):
        a = 2 * math.pi * k / 16
        pts.append(((r + 4) * math.cos(a), (r + 4) * math.sin(a), 18 if k % 2 == 0 else h - 18))
    icing(G, pts, r=2.5, bumps=False)
    for dx in (-40, 40):
        tube(Wd, [(dx, -20, h + 6), (dx, 100, h + 6)], 5, nseg=8)
        Wd.add(_ball(9, 8), t=(dx, 100, h + 6))
    return X


def track_oval(L=640, R0=300, R1=380):
    """wooden toy train track: oval of sleepers with two steel rails (origin = oval centre, floor level of the rug)"""
    X = Model(); Wd = X.mesh(S('track')); Rl = X.mesh(S('rail', 'shiny'))
    Rm = (R0 + R1) / 2
    path = []
    for t in np.linspace(0, 1, 97):
        s_ = t * (2 * L + 2 * math.pi * Rm); path.append(_oval_point(s_, L, Rm))
    for k in range(0, 96, 2):
        p, d = path[k]
        nrm = np.array([-d[1], d[0], 0])
        sl = Mesh(); rbox(sl, (-14, -(R1 - R0) / 2 - 10, 0), (14, (R1 - R0) / 2 + 10, 8), r=2, k=2, tile=64)
        ang = math.atan2(nrm[1], nrm[0]) - math.pi / 2
        Wd.add(sl, rot_z(ang), (p[0], p[1], 0))
    for off in (-24, 24):
        pts = [(p[0] - d[1] * off, p[1] + d[0] * off, 11) for (p, d) in path]
        tube(Rl, pts, 3, nseg=6, caps=(False, False))
    return X


def _oval_point(s, L, R):
    """point and unit tangent at arc length s round a stadium oval (straights along x, length L, end radius R)"""
    per = 2 * L + 2 * math.pi * R
    s = s % per
    if s < L: return (np.array([-L / 2 + s, -R]), np.array([1.0, 0]))
    s -= L
    if s < math.pi * R:
        a = -math.pi / 2 + s / R
        return (np.array([L / 2 + R * math.cos(a), R * math.sin(a)]), np.array([-math.sin(a), math.cos(a)]))
    s -= math.pi * R
    if s < L: return (np.array([L / 2 - s, R]), np.array([-1.0, 0]))
    s -= L
    a = math.pi / 2 + s / R
    return (np.array([-L / 2 + R * math.cos(a), R * math.sin(a)]), np.array([-math.sin(a), math.cos(a)]))


def toy_engine():
    """wooden toy steam engine (origin = floor under its middle, front +x, 200 long, 96 wide, 204 tall)"""
    X = Model(); Bl = X.mesh(S('paint_blue', 'shiny')); R = X.mesh(S('paint_red', 'shiny')); Gn = X.mesh(S('paint_green', 'shiny'))
    Y = X.mesh(S('paint_yellow', 'shiny')); K = X.mesh(S('metal_black', 'shiny')); G = X.mesh(S('trim_gold', 'shiny'))
    rbox(Bl, (-100, -36, 34), (100, 36, 64), r=5, k=2, tile=96)
    rbox(R, (-100, -36, 64), (-20, 36, 184), r=6, k=3, tile=96)
    rbox(Y, (-108, -44, 184), (-12, 44, 200), r=6, k=3, tile=96)
    for sg in (-1, 1):
        rbox(X.mesh(S('glass', 'glass')), (-90, sg * 36 - 1, 120), (-30, sg * 36 + 1, 170), r=1, k=1, tile=64, faces='ns')
    tube(Gn, [(-20, 0, 98), (96, 0, 98)], 34, nseg=18, vlen=96)
    disc_axis(K, (97, 0, 98), 32, (1, 0, 0), n=18)
    for x in (10, 60): tube(G, arc_path((x, 0, 98), 35, 0, 360, n=25, axis='x'), 2.5, nseg=6, caps=(False, False))
    revolve(K, [(14, 130), (12, 170), (22, 200), (20, 206), (0, 206)], n=14, cx=70, cy=0)
    revolve(G, [(18, 128), (14, 150), (0, 156)], n=14, cx=20, cy=0)
    for x in (-70, 0, 70):
        for sg in (-1, 1):
            disc_axis(R, (x, sg * 42, 34), 26, (0, sg, 0), n=18)
            disc_axis(G, (x, sg * 43, 34), 7, (0, sg, 0), n=10)
    for sg in (-1, 1): tube(K, [(-70, sg * 45, 30), (70, sg * 45, 30)], 3, nseg=6)
    cc = Mesh(); prism(cc, [(100, -36), (130, 0), (100, 36)], 8, 40, tile=64); K.add(cc)
    return X


def toy_wagon(col='paint_green'):
    X = Model(); C = X.mesh(S(col, 'shiny')); R = X.mesh(S('paint_red', 'shiny')); G = X.mesh(S('trim_gold', 'shiny'))
    rbox(C, (-100, -36, 34), (100, 36, 64), r=5, k=2, tile=96)
    for sg in (-1, 1):
        for x in (-60, 60):
            disc_axis(R, (x, sg * 42, 34), 24, (0, sg, 0), n=16)
            disc_axis(G, (x, sg * 43, 34), 6, (0, sg, 0), n=10)
        for z in (72, 92):
            rbox(C, (-100, sg * 36 - (6 if sg > 0 else 0), z), (100, sg * 36 + (0 if sg < 0 else 0) + (0 if sg > 0 else 6), z + 10), r=2, k=2, tile=96)
    for x in (-100, 100):
        rbox(C, (x - 5, -36, 64), (x + 5, 36, 104), r=2, k=2, tile=64)
    return X


BUILDERS = {'tree': tree, 'star': star, 'gift': gift, 'mantel': mantel, 'fire_grate': fire_grate, 'stocking': stocking,
            'garland': garland, 'candlestick': candlestick, 'nutcracker': nutcracker, 'mantel_clock': mantel_clock,
            'fire_tools': fire_tools, 'stool': stool, 'frame': frame, 'armchair': armchair, 'footstool': footstool,
            'side_table': side_table, 'floor_lamp': floor_lamp, 'sofa': sofa, 'coffee_table': coffee_table,
            'sideboard': sideboard, 'grandfather_clock': grandfather_clock, 'paper_star': paper_star, 'mistletoe': mistletoe,
            'wreath': wreath, 'advent_wreath': advent_wreath, 'pyramid_base': pyramid_base, 'pyramid_rotor': pyramid_rotor,
            'snow_globe': snow_globe, 'poinsettia': poinsettia, 'curtain': curtain, 'curtain_rod': curtain_rod,
            'seat_cushion': seat_cushion, 'bolster': bolster, 'ginger_house': ginger_house, 'candy_cane': candy_cane,
            'gumdrop': gumdrop, 'choc_table': choc_table, 'gingerman': gingerman, 'sleigh': sleigh, 'sack': sack,
            'reindeer': reindeer, 'rocking_horse': rocking_horse, 'drum': drum, 'track_oval': track_oval,
            'toy_engine': toy_engine, 'toy_wagon': toy_wagon}


def gift_model(w, d, h, pat, bow=True, open=False):
    w, d, h = int(round(w)), int(round(d)), int(round(h))
    key = f'gift_{pat}_{w}x{d}x{h}' + ('' if bow else '_nb') + ('_open' if open else '')
    return get('gift', key=key, w=w, d=d, h=h, pat=pat, bow=bow, open=open)




# ================================================================================================= shaders
def shaders():
    s = '// ---- MD3 models (xmas_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        t = f'textures/padxmas/{img}'
        if kind in ('lm', 'shiny', 'tinsel'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 75\n'
            if opt.get('cull'): s += '\tcull none\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'shiny':
                s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.25 0.25 0.25 )\n\t\ttcGen environment\n\t}}\n'
            if kind == 'tinsel':
                s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.35 0.3 {opt.get("phase", 0)} 0.6\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind == 'glow':
            ph = int(opt.get('tag', '0') or 0) * 0.25
            wave = opt.get('wave') or (f'wave square 0.6 0.4 {ph:g} 0.5' if img.startswith('bulb_') else 'wave sin 0.9 0.1 0 0.5')
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\t{{\n\t\tmap {t}\n\t\trgbGen {wave}\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.16 0.18 0.2 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return s
