"""Round-5 MD3s for wop_padxmas3: the sofa corner. A three-seat ochre velvet sofa and a tartan wingback armchair at
real living-room scale (16u/cm: seat 45 cm = 720u), and the Christmas-morning mess in front of them: torn paper,
crumpled balls, opened boxes, ribbon curls, slippers, a mug of cocoa, the TV remote. Pad dressings: whoopee cushion,
throw pillow, ball of yarn. Visual geometry only (the generator owns the weapclip collision); world-space helpers
take the same numbers as the collision brushes so the two always match."""
import math, random
import numpy as np
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, grid_normals
from woplib import models as ML
import xm3_art as A
import xm3_models as XM

M = A.M
Model = ML.Model
rot_y, rot_x = XM.rot_y, XM.rot_x


def materials(TX):
    from woplib import texlib as TL
    m = lambda key, arr, kind='lm', **o: M.__setitem__(key, TX.material(key, arr, kind, **o))
    m('velvet', velvet((176, 124, 50)), shade=80)
    m('velvet_dk', velvet((140, 96, 38)), shade=80)
    m('tartan', tartan(), shade=80)
    m('tartan_g', tartan(((24, 70, 44), (150, 24, 30), (16, 30, 60), (226, 196, 90))), shade=80)
    m('cushion_deer', cushion_print(), shade=80)
    m('cushion_star', cushion_print(star=True), shade=80)
    m('legwood', TL.planks((70, 40, 22), n_planks=1, grain=8), 'lms', v=0.2, shade=60)
    m('button', TL.solid((120, 84, 30), 2, 701), 'lms', v=0.2)
    m('slipper', TL.solid((150, 30, 40), 6, 702), shade=80)
    m('cocoa', TL.solid((86, 46, 24), 2, 703), shade=60)
    m('remote', TL.solid((34, 34, 38), 2, 704), 'lms', v=0.2, shade=40)
    m('rbtn', TL.dots((34, 34, 38), (200, 60, 50), n_dots=6, r=0.12), shade=40)
    m('yarn', yarn(), shade=80)
    m('whoopee', TL.solid((220, 70, 90), 2, 705), 'lms', v=0.3, shade=80)
    m('lampshade', TL.fabric((214, 180, 120), weave=64), 'glow', wave='const 0.85')
    m('catfur', TL.stripes((210, 120, 50), (170, 86, 30), n_stripes=10, vertical=False), shade=80)


def velvet(col, n=256):
    a = ML.fill(n, col, 3, 710 + col[0])
    x, y = ML.xy(n)
    sheen = 0.9 + 0.1 * np.sin(x * 6.28 * 3 + ML.noise(n, 30, 711) * 2)
    return a * sheen[..., None] + ML.N3(n, 0.7, 712, 5)


def tartan(cols=((150, 24, 30), (24, 70, 44), (16, 30, 60), (226, 196, 90)), n=256):
    x, y = ML.xy(n)
    def band(t):
        t = t % 1
        return np.select([t < 0.4, t < 0.55, t < 0.62, t < 0.64, t < 0.9], [0, 1, 2, 3, 1], 0)
    bx, by = band(x * 2), band(y * 2)
    C = [ML.C(c) for c in cols]
    out = np.zeros((n, n, 3), np.float32)
    for i in range(4):
        out += np.where((bx == i)[..., None], C[i], 0) * 0.5 + np.where((by == i)[..., None], C[i], 0) * 0.5
    weave = (((np.arange(n)[:, None] + np.arange(n)[None, :]) // 2) % 2)[..., None] * 10
    return out + weave


def cushion_print(star=False, n=256):
    from PIL import ImageDraw
    a = ML.fill(n, (232, 222, 200) if star else (160, 28, 36), 3, 720 + star)
    im = ML.img(a); d = ImageDraw.Draw(im)
    fg = (180, 30, 40) if star else (240, 232, 214)
    d.rectangle((14, 14, n - 15, n - 15), outline=fg, width=6)
    if star:
        d.polygon(A.star_pts(128, 128, 80, 34), fill=(200, 150, 50))
    else:                                               # a simple stag silhouette: body, legs, neck, head, antlers
        d.ellipse((70, 120, 170, 165), fill=fg)
        for x in (82, 100, 140, 158): d.rectangle((x, 155, x + 8, 205), fill=fg)
        d.polygon([(150, 130), (170, 80), (186, 84), (170, 135)], fill=fg)
        d.ellipse((164, 66, 196, 90), fill=fg)
        for s in (-1, 1):
            d.line((178, 70, 178 + s * 22, 40), fill=fg, width=5); d.line((178 + s * 12, 55, 178 + s * 26, 56), fill=fg, width=4)
    return np.asarray(im, np.float32)


def yarn(n=128):
    x, y = ML.xy(n)
    s = np.sin((x * 1.0 + y * 0.6) * 6.28 * 10) * 0.5 + 0.5
    s2 = np.sin((x * -0.7 + y * 1.0) * 6.28 * 9) * 0.5 + 0.5
    k = np.maximum(s, s2)
    return ML.C((60, 120, 190)) * (0.7 + 0.35 * k)[..., None]


# ------------------------------------------------------------------------------------------------ the sofa
SOFA = dict(x0=2880, x1=4320, y0=-560, y1=2080, leg=240, base=400, seat=720, arm_w=280, arm_h=1040, back_x=4000,
            back_h=1360, bc_x=3700, bc_h=1250)


def sofa_brushes(box, S=SOFA, tex='x/x'):
    """collision for the sofa (and the same numbers drive the visual): legs, base, two seat cushions, arms, back,
    back cushions. Seat cushions are separate brushes with a 16u dip between them (coins down the gap)."""
    x0, x1, y0, y1 = S['x0'], S['x1'], S['y0'], S['y1']
    aw, L, B, St = S['arm_w'], S['leg'], S['base'], S['seat']
    ya, yb = y0 + aw, y1 - aw
    ym = (ya + yb) / 2
    b = []
    for (lx, ly) in ((x0 + 60, y0 + 60), (x0 + 60, y1 - 60), (x1 - 60, y0 + 60), (x1 - 60, y1 - 60), (x0 + 60, ym), (x1 - 60, ym)):
        b.append(box((lx - 44, ly - 44, 0), (lx + 44, ly + 44, L), tex))
    b.append(box((x0, y0, L), (x1, y1, B), tex))
    b.append(box((x0, ya, B), (S['bc_x'], ym - 24, St), tex)); b.append(box((x0, ym + 24, B), (S['bc_x'], yb, St), tex))
    b.append(box((x0, ym - 24, B), (S['bc_x'], ym + 24, St - 16), tex))
    b.append(box((x0, y0, B), (x1, ya, S['arm_h']), tex)); b.append(box((x0, yb, B), (x1, y1, S['arm_h']), tex))
    b.append(box((S['back_x'], ya, B), (x1, yb, S['back_h']), tex))
    b.append(box((S['bc_x'], ya, St), (S['back_x'], yb, S['bc_h']), tex))
    b.append(box((S['bc_x'], ya, B), (S['back_x'], yb, St), tex))
    return b


def sofa_visual(X, S=SOFA, fab='velvet', fab2='velvet_dk', throw='tartan'):
    """rounded velvet sofa over the collision boxes: plump seat + back cushions, rolled arms, piping, buttons,
    turned legs, a tartan throw over one arm and two festive scatter cushions"""
    x0, x1, y0, y1 = S['x0'], S['x1'], S['y0'], S['y1']
    aw, L, B, St = S['arm_w'], S['leg'], S['base'], S['seat']
    ya, yb = y0 + aw, y1 - aw
    ym = (ya + yb) / 2
    f, f2 = X.mesh(M[fab]), X.mesh(M[fab2])
    rbox(f2, (x0 + 4, y0 + 4, L), (x1 - 4, y1 - 4, B), r=30, k=3, tile=512)
    for (a, b_) in ((ya, ym - 24), (ym + 24, yb)):
        rbox(f, (x0 - 10, a + 4, B - 10), (S['bc_x'] + 30, b_ - 4, St + 8), r=70, k=4, tile=512)
    for (a, b_) in ((y0, ya), (yb, y1)):                    # arms with a rolled top
        rbox(f2, (x0 + 10, a + 6, B - 4), (x1 - 4, b_ - 6, S['arm_h'] - 60), r=24, k=3, tile=512)
        roll = Mesh(); revolve(roll, [(0.1, x0 - 30), ((b_ - a) / 2 + 10, x0 - 20), ((b_ - a) / 2 + 14, x0 + 40), ((b_ - a) / 2 + 14, x1 - 8),
                                      (0.1, x1 - 8)], n=20, u_tiles=2)
        X.mesh(M[fab]).add(roll, R=rot_y(math.pi / 2) @ np.eye(3), t=(0, (a + b_) / 2, S['arm_h'] - 100))
    rbox(f2, (S['back_x'] - 10, ya - 10, B), (x1 - 6, yb + 10, S['back_h']), r=50, k=4, tile=512)
    n_bc = 3
    for i in range(n_bc):                                   # three plump back cushions, leaning back a little
        a = ya + (yb - ya) * i / n_bc + 8; b_ = ya + (yb - ya) * (i + 1) / n_bc - 8
        m = Mesh(); rbox(m, (-150, a, 0), (150, b_, S['bc_h'] - St + 40), r=90, k=4, tile=512)
        X.mesh(M[fab]).add(m, R=rot_y(-0.1), t=((S['bc_x'] + S['back_x']) / 2 + 10, 0, St - 10))
        for k in range(2):
            sphere(X.mesh(M['button']), (S['bc_x'] - 34 + 20 * k, (a + b_) / 2, St + 200 + 180 * k), 14, nu=8, nv=5)
    for (lx, ly) in ((x0 + 60, y0 + 60), (x0 + 60, y1 - 60), (x1 - 60, y0 + 60), (x1 - 60, y1 - 60), (x0 + 60, ym), (x1 - 60, ym)):
        revolve(X.mesh(M['legwood']), [(30, 0), (40, 30), (52, 80), (36, 150), (48, 210), (56, L)], n=12, cx=lx, cy=ly)
    # tartan throw draped over the north arm and spilling onto the seat
    th = X.mesh(M[throw])
    pts = []
    nx, ny = 10, 8
    P = np.zeros((ny, nx, 3)); UV = np.zeros((ny, nx, 2))
    for i in range(ny):
        for j in range(nx):
            t = j / (nx - 1); u = i / (ny - 1)
            x = x0 + 120 + 700 * u
            if t < 0.35:   y, z = yb - 300 + 300 * t / 0.35, St + 12 + 6 * math.sin(u * 9)
            elif t < 0.65: tt = (t - 0.35) / 0.3; y, z = yb + (y1 - yb) * tt, St + 12 + (S['arm_h'] - St) * math.sin(tt * math.pi / 2) + 14
            else:          tt = (t - 0.65) / 0.35; y, z = y1 + 22, S['arm_h'] + 10 - 520 * tt
            P[i, j] = (x, y, z); UV[i, j] = (u * 3, t * 3)
    N = grid_normals(P)
    if N[ny // 2, 2, 2] < 0: N = -N
    th.grid(P, N, UV)
    th2 = X.mesh(M[throw]); th2.grid(P[:, ::-1] + 0, -N[:, ::-1], UV[:, ::-1])
    for (cy, key, rot) in ((ya + 200, 'cushion_deer', 0.25), (yb - 380, 'cushion_star', -0.2)):
        m = Mesh(); rbox(m, (-40, -170, 0), (40, 170, 340), r=60, k=4, tile=340)
        X.mesh(M[key]).add(m, R=rot_z(rot) @ rot_y(-0.35), t=(S['bc_x'] - 70, cy, St))


ARM = dict(x0=2880, x1=4320, y0=-2256, y1=-856, leg=240, base=400, seat=720, arm_w=240, arm_h=1040, back_x=4000,
           back_h=1700, bc_x=3760, bc_h=1500)


def armchair_brushes(box, S=ARM, tex='x/x'):
    x0, x1, y0, y1 = S['x0'], S['x1'], S['y0'], S['y1']
    aw, L, B, St = S['arm_w'], S['leg'], S['base'], S['seat']
    ya, yb = y0 + aw, y1 - aw
    b = [box((lx - 44, ly - 44, 0), (lx + 44, ly + 44, L), tex)
         for (lx, ly) in ((x0 + 60, y0 + 60), (x0 + 60, y1 - 60), (x1 - 60, y0 + 60), (x1 - 60, y1 - 60))]
    b += [box((x0, y0, L), (x1, y1, B), tex), box((x0, ya, B), (S['bc_x'], yb, St), tex),
          box((x0, y0, B), (x1, ya, S['arm_h']), tex), box((x0, yb, B), (x1, y1, S['arm_h']), tex),
          box((S['back_x'], ya, B), (x1, yb, S['back_h']), tex), box((S['bc_x'], ya, B), (S['back_x'], yb, S['bc_h']), tex)]
    return b


def armchair_visual(X, S=ARM):
    x0, x1, y0, y1 = S['x0'], S['x1'], S['y0'], S['y1']
    aw, L, B, St = S['arm_w'], S['leg'], S['base'], S['seat']
    ya, yb = y0 + aw, y1 - aw
    f = X.mesh(M['tartan_g'])
    rbox(f, (x0 + 4, y0 + 4, L), (x1 - 4, y1 - 4, B), r=30, k=3, tile=512)
    rbox(f, (x0 - 10, ya + 4, B - 10), (S['bc_x'] + 30, yb - 4, St + 10), r=70, k=4, tile=512)
    for (a, b_) in ((y0, ya), (yb, y1)):
        rbox(f, (x0 + 10, a + 6, B - 4), (x1 - 4, b_ - 6, S['arm_h'] - 60), r=24, k=3, tile=512)
        roll = Mesh(); revolve(roll, [(0.1, x0 - 30), ((b_ - a) / 2 + 10, x0 - 20), ((b_ - a) / 2 + 14, x0 + 40), ((b_ - a) / 2 + 14, x1 - 8),
                                      (0.1, x1 - 8)], n=20, u_tiles=2)
        f.add(roll, R=rot_y(math.pi / 2), t=(0, (a + b_) / 2, S['arm_h'] - 100))
    rbox(f, (S['back_x'] - 10, ya - 10, B), (x1 - 6, yb + 10, S['back_h']), r=60, k=4, tile=512)
    for sg, yy in ((-1, ya), (1, yb)):                       # wings
        rbox(f, (S['back_x'] - 300, yy - 40 if sg < 0 else yy - 20, S['arm_h'] - 80), (S['back_x'] + 60, yy + 20 if sg < 0 else yy + 40, S['back_h'] - 60),
             r=30, k=3, tile=512)
    m = Mesh(); rbox(m, (-120, ya + 10, 0), (120, yb - 10, S['bc_h'] - St + 30), r=90, k=4, tile=512)
    f.add(m, R=rot_y(-0.08), t=((S['bc_x'] + S['back_x']) / 2, 0, St - 10))
    for (lx, ly) in ((x0 + 60, y0 + 60), (x0 + 60, y1 - 60), (x1 - 60, y0 + 60), (x1 - 60, y1 - 60)):
        revolve(X.mesh(M['legwood']), [(30, 0), (40, 30), (52, 80), (36, 150), (48, 210), (56, L)], n=12, cx=lx, cy=ly)
    m = Mesh(); rbox(m, (-40, -160, 0), (40, 160, 320), r=60, k=4, tile=320)
    X.mesh(M['cushion_star']).add(m, R=rot_y(-0.3), t=(S['bc_x'] - 60, (ya + yb) / 2, St))


# ------------------------------------------------------------------------------------------------ the unwrapping mess
def torn_paper(w, d, pat, seed):
    X = Model()
    rr = random.Random(seed)
    nx = ny = 7
    P = np.zeros((ny, nx, 3)); UV = np.zeros((ny, nx, 2))
    for i in range(ny):
        for j in range(nx):
            x = -w / 2 + w * j / (nx - 1) + rr.uniform(-14, 14); y = -d / 2 + d * i / (ny - 1) + rr.uniform(-14, 14)
            edge = min(i, j, ny - 1 - i, nx - 1 - j)
            P[i, j] = (x, y, 1.0 + (rr.uniform(4, 28) if edge else rr.uniform(0, 6))); UV[i, j] = (x / 256, y / 256)
    N = grid_normals(P)
    if N[3, 3, 2] < 0: N = -N
    X.mesh(M['paper_' + pat]).grid(P, N, UV)
    X.mesh(M['white']).grid(P - [0, 0, 0.6], -N, UV)
    return X


def paper_ball(r, pat, seed):
    X = Model()
    rr = random.Random(seed)
    lump = Mesh()
    for k in range(5):
        a = rr.uniform(0, 6.28); e = rr.uniform(-0.6, 0.6)
        c = np.array([math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)]) * r * 0.35
        ellipsoid(lump, c + [0, 0, r * 0.9], r * rr.uniform(0.6, 0.8), r * rr.uniform(0.6, 0.8), r * rr.uniform(0.55, 0.75), nu=8, nv=6)
    X.mesh(M['paper_' + pat]).add(lump)
    return X


def open_box(w, d, h, pat, seed):
    X = Model()
    pm, cb = X.mesh(M['paper_' + pat]), X.mesh(M['cardboard_in'])
    hw, hd, t = w / 2, d / 2, 8
    for (mn, mx) in (((-hw, -hd, 0), (hw, -hd + t, h)), ((-hw, hd - t, 0), (hw, hd, h)), ((-hw, -hd, 0), (-hw + t, hd, h)), ((hw - t, -hd, 0), (hw, hd, h))):
        rbox(pm, mn, mx, r=1, k=1, tile=max(w, d))
    rbox(cb, (-hw + t, -hd + t, 0), (hw - t, hd - t, 4), r=0, k=1, tile=128, faces='t')
    th = XM.tissue_heap(w - 2 * t - 4, d - 2 * t - 4, seed)
    for sh, mm in th.m.items():
        X.mesh(sh).add(mm, t=(0, 0, h * 0.55))
    return X


def lid(w, d, pat):
    X = Model()
    rbox(X.mesh(M['paper_' + pat]), (-w / 2 - 5, -d / 2 - 5, 0), (w / 2 + 5, d / 2 + 5, 18), r=2, k=1, tile=max(w, d))
    return X


def ribbon_curls(seed, col='gold', n=4):
    X = Model()
    rr = random.Random(seed)
    for k in range(n):
        cx, cy = rr.uniform(-80, 80), rr.uniform(-80, 80)
        pts = [(cx + 30 * math.cos(t) + t * 6, cy + 30 * math.sin(t), 2) for t in np.linspace(0, 12, 50)]
        tube(X.mesh(M['ribbon_' + col]), pts, 8, nseg=4, ry=1.2)
    return X


def slippers():
    X = Model()
    for sy, a in ((-1, 0.15), (1, -0.1)):
        m = Mesh()
        ellipsoid(m, (0, 0, 0), 140, 56, 40, nu=14, nv=8, flat_bottom=0)
        X.mesh(M['slipper']).add(m, R=rot_z(a), t=(0, sy * 80, 0))
        f = Mesh(); ellipsoid(f, (0, 0, 0), 50, 60, 22, nu=10, nv=6)
        X.mesh(M['fluff']).add(f, R=rot_z(a), t=(-10, sy * 80, 38))
        sphere(X.mesh(M['fluff']), (110 * math.cos(a), sy * 80 + 110 * math.sin(a), 52), 18, nu=8, nv=5)
    return X


def cocoa_mug(r=70, h=140):
    X = Model()
    revolve(X.mesh(M['nut_red']), [(r - 4, 0), (r, 6), (r, h), (r - 8, h), (r - 8, 12)], n=20)
    disc(X.mesh(M['cocoa']), r - 8, h - 18, n=20)
    tube(X.mesh(M['nut_red']), [(r - 4, 0, h * 0.75), (r + 40, 0, h * 0.7), (r + 40, 0, h * 0.3), (r - 4, 0, h * 0.25)], 10, nseg=6)
    rr = random.Random(9)
    for k in range(5):
        sphere(X.mesh(M['icing']), (rr.uniform(-34, 34), rr.uniform(-34, 34), h - 14), 13, nu=6, nv=4)
    return X


def remote():
    X = Model()
    rbox(X.mesh(M['remote']), (-110, -30, 0), (110, 30, 22), r=8, k=2, tile=64)
    rbox(X.mesh(M['rbtn']), (-80, -18, 21), (60, 18, 25), r=0, k=1, tile=64, faces='t')
    return X


# ------------------------------------------------------------------------------------------------ pad dressings
def whoopee(r=80):
    X = Model()
    revolve(X.mesh(M['whoopee']), [(r, 0), (r + 6, 6), (r, 14), (r * 0.5, 16), (0.1, 16)], n=20)
    tube(X.mesh(M['whoopee']), [(r - 4, 0, 6), (r + 30, 0, 5), (r + 50, 0, 6)], 9, nseg=8, ry=5)
    return X


def throw_pillow():
    X = Model()
    m = Mesh(); rbox(m, (-110, -110, 0), (110, 110, 16), r=7, k=2, tile=220)
    X.mesh(M['cushion_star']).add(m)
    return X


def yarn_ball(r=60):
    X = Model()
    m = Mesh(); ellipsoid(m, (0, 0, 0), r, r, 16, nu=14, nv=6, flat_bottom=0)
    X.mesh(M['yarn']).add(m)
    tube(X.mesh(M['yarn']), [(r, 0, 4), (r + 60, 30, 3), (r + 120, -10, 3), (r + 170, 20, 3)], 4, nseg=4)
    for sg in (-1, 1):
        tube(X.mesh(M['legwood']), [(-r * 0.6, sg * 20, 10), (r * 0.9, sg * 30, 14)], 4, nseg=5)
    return X


def valance_spans(S, front_gap=None, sides='nse'):
    """fabric skirt panels from the floor to the sofa base (16u thick, inside the footprint), leaving front_gap (y0, y1)
    open: returns [(mn, mx)] boxes used for both the weapclip and the visual panel"""
    x0, x1, y0, y1, L = S['x0'], S['x1'], S['y0'], S['y1'], S['leg']
    out = []
    if 'w' in sides or front_gap is not None:          # front face is -x (faces the room)
        segs = [(y0, y1)] if front_gap is None else [(y0, front_gap[0]), (front_gap[1], y1)]
        for a, b in segs:
            if b - a > 8: out.append(((x0, a, 0), (x0 + 16, b, L)))
    if 's' in sides: out.append(((x0 + 16, y0, 0), (x1, y0 + 16, L)))
    if 'n' in sides: out.append(((x0 + 16, y1 - 16, 0), (x1, y1, L)))
    return out


def valance_visual(X, spans, fab):
    m = X.mesh(M[fab])
    for (mn, mx) in spans:
        rbox(m, (mn[0] - 2, mn[1] - 2, 2), (mx[0] + 2, mx[1] + 2, mx[2] + 4), r=3, k=1, tile=256)
        # gathered pleats: shallow vertical ridges along the outward face
        hor = (mx[1] - mn[1]) > (mx[0] - mn[0])
        L = (mx[1] - mn[1]) if hor else (mx[0] - mn[0])
        for k in range(int(L // 80)):
            t = (k + 0.5) * 80
            if hor: tube(m, [(mn[0] - 2, mn[1] + t, 4), (mn[0] - 2, mn[1] + t, mx[2])], 6, nseg=5)
            else:
                yy = mn[1] - 2 if mn[1] < (mn[1] + mx[1]) / 2 + 1 and mx[1] - mn[1] < 20 and mn[1] < 0 else mx[1] + 2
                tube(m, [(mn[0] + t, yy, 4), (mn[0] + t, yy, mx[2])], 6, nseg=5)


def footstool(r=420, h=640):
    """tufted oxblood leather footstool (ottoman) on bun feet, a folded tartan blanket on top"""
    X = Model()
    lt = X.mesh(M['leather'])
    revolve(lt, [(r - 30, 70), (r, 110), (r + 6, h * 0.5), (r, h - 60), (r - 40, h - 10), (r - 90, h), (0.1, h)], n=40, u_tiles=8)
    for k in range(12):
        a = 2 * math.pi * k / 12
        for rr, zz in ((r * 0.35, h + 1), (r * 0.7, h - 8)):
            sphere(X.mesh(M['button']), (rr * math.cos(a + (0.26 if rr > 200 else 0)), rr * math.sin(a + (0.26 if rr > 200 else 0)), zz), 12, nu=6, nv=4)
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        sphere(X.mesh(M['legwood']), ((r - 90) * math.cos(a), (r - 90) * math.sin(a), 46), 48, nu=10, nv=6)
        tube(X.mesh(M['legwood']), [((r - 90) * math.cos(a), (r - 90) * math.sin(a), 0), ((r - 90) * math.cos(a), (r - 90) * math.sin(a), 80)], 34, nseg=8)
    rbox(X.mesh(M['tartan']), (-150, -220, h - 2), (150, 220, h + 40), r=14, k=3, tile=300)
    return X


def floor_lamp(h=2500, shade_r=300):
    """standing lamp: weighted brass base, a turned pole, a pleated fabric shade (glows from inside)"""
    X = Model()
    revolve(X.mesh(M['brass']), [(210, 0), (210, 30), (170, 70), (120, 100), (40, 120), (0.1, 120)], n=24)
    tube(X.mesh(M['brass']), [(0, 0, 120), (0, 0, h - 300)], 18, nseg=10)
    for z in (700, 1400): revolve(X.mesh(M['brass']), [(18, z - 20), (34, z), (18, z + 20)], n=12)
    sh = Mesh()
    revolve(sh, [(shade_r, h - 420), (shade_r * 0.62, h), (shade_r * 0.62 - 6, h), (shade_r - 6, h - 420)], n=24, u_tiles=12)
    X.mesh(M['lampshade']).add(sh)
    revolve(X.mesh(M['mousewin']), [(40, h - 330), (40, h - 250), (0.1, h - 240)], n=12)      # the bulb (glows)
    return X


def sleeping_cat(r=200):
    """a ginger cat curled up asleep on a round cushion"""
    X = Model()
    revolve(X.mesh(M['velvet_dk']), [(r, 0), (r + 10, 30), (r, 70), (r * 0.8, 84), (0.1, 80)], n=24)
    c = X.mesh(M['catfur'])
    body = Mesh(); ellipsoid(body, (0, 0, 0), 130, 100, 70, nu=16, nv=10, flat_bottom=-60)
    c.add(body, t=(0, 0, 140))
    sphere(c, (90, -60, 150), 52, nu=12, nv=8)                                   # head tucked in
    for s in (-1, 1):
        ellipsoid(c, (90 + s * 26, -66, 196), 12, 8, 22, nu=6, nv=4)            # ears
    tail = [(-110, 20, 110), (-80, 110, 100), (20, 130, 98), (110, 70, 104)]
    tube(c, tail, [26, 22, 18, 14], nseg=8, caps=(False, True))
    return X
