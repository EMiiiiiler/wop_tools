"""Padman's Garage - textures (woplib.texlib registry) and custom MD3s. All art is original and procedural.

Models are built in model space (z = 0 on the surface they stand on) and placed by build_padgarage.py with their
collision (COLL[name] = boxes / cylinders in model space) or with K.solid_piece. Scale: 1 m = 600u.
"""
import math
import numpy as np
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism as mprism, rot_z, rot_axis

TX = None           # texlib.Textures (set by textures())
M_ = {}             # material key -> model shader name
COLL = {}           # model name -> dict(boxes=[(mn, mx)], cyls=[(cx, cy, r, z0, z1)])


# ================================================================================================= textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('concrete', concrete(), steps=None, scale=1.0)
    a('drive', concrete((150, 148, 142), stains=10, cracks=True), scale=1.0)
    a('wallboard', TL.planks((196, 186, 160), n_planks=4, gap=(120, 112, 96), grain=4, vertical=True), steps='woodsteps')
    a('block', TL.bricks((178, 176, 170), (140, 138, 132), rows=6, cols=3, vary=10), scale=0.75)
    a('weatherboard', TL.planks((214, 222, 218), n_planks=8, gap=(150, 160, 156), grain=2), scale=1.0)
    a('trim', TL.solid((238, 236, 228), 3, 7, 64))
    a('rafter', TL.planks((170, 132, 88), n_planks=2, grain=12), steps='woodsteps')
    a('loftboard', TL.planks((182, 150, 104), n_planks=6, grain=8), steps='woodsteps')
    a('roofiron', corrugated((116, 124, 128)), scale=1.0)
    a('roofunder', corrugated((150, 156, 158), dark=True), scale=1.0)
    a('grass', TL.solid((62, 96, 44), 10, 21, 256) + TL.N3(256, 2, 22, 14), steps='softsteps', scale=1.0)
    a('fence', TL.planks((132, 104, 74), n_planks=10, gap=(70, 52, 38), grain=8, vertical=True, stagger=False), steps='woodsteps')
    a('hedge', hedge(), scale=1.0)
    a('steel', TL.metal((150, 156, 162)), scale=0.5)
    a('rubberfloor', TL.dots((52, 52, 56), (70, 70, 76), n_dots=12, r=0.2))
    a('drain', grate(), check_tile=False)
    a('sewer', TL.bricks((96, 92, 80), (60, 58, 50), rows=10, cols=4, vary=14), scale=0.75)
    a('sewerfloor', TL.grime(TL.stone((92, 96, 88), cells=20), 0.4), steps='splashsteps')
    a('doorpanel', corrugated((212, 214, 210), ribs=16), scale=1.0)
    a('soapwater', TL.solid((180, 214, 226), 6, 31, 128), 'water', rgb=(0.75, 0.85, 0.9), alpha=0.6)
    a('puddle', TL.solid((120, 130, 136), 6, 32, 128), 'water', rgb=(0.35, 0.4, 0.45), alpha=0.5)
    a('glass', TL.solid((170, 200, 210), 2, 61, 64), 'glass', rgb='0.08 0.10 0.11', shadow=False)
    a('sky', TL.solid((20, 24, 40), 2, 33, 64), 'raw', shader=sky_stanza(K.ns), check_tile=False)
    a('stripglow', TL.solid((240, 248, 255), 1, 34, 64), 'raw', shader=glow_stanza(K.ns, 'stripglow'), check_tile=False)
    TX.add('sign', TL.label("PAD'S GARAGE", 1024, 256, (40, 44, 52), (250, 200, 60), border=(250, 200, 60)), 'sign', check_tile=False)
    import gr_street as GS
    GS.textures(TX)
    TX.kit_defaults(pad_rgb=(255, 170, 40), rubber=(40, 40, 44))
    materials(); GS.materials()
    return TX


def concrete(col=(168, 166, 160), stains=6, cracks=False, n=256):
    c = TL.fill(n, col, 7, 41) + TL.N3(n, 0.5, 42, 6)
    rng = np.random.default_rng(43)
    x, y = TL.xy(n)
    for _ in range(stains):                        # oil stains (tileable: wrap the distance)
        cx, cy, r = rng.random(), rng.random(), 0.04 + rng.random() * 0.08
        dx = np.minimum(np.abs(x - cx), 1 - np.abs(x - cx)); dy = np.minimum(np.abs(y - cy), 1 - np.abs(y - cy))
        d = (dx * dx + dy * dy) / (r * r)
        c = c * (1 - np.clip(0.45 - d * 0.3, 0, 0.45)[..., None])
    if cracks:
        idx, e = ML.voronoi(n, 6, 44)
        c = np.where((e < 0.004)[..., None], c * 0.6, c)
    return c


def corrugated(col, ribs=8, dark=False, n=256):
    x, y = TL.xy(n)
    s = np.sin(x * ribs * 2 * math.pi)
    c = TL.fill(n, col, 3, 45) + s[..., None] * (14 if not dark else 20)
    return c


def hedge(n=256):
    idx, e = ML.voronoi(n, 90, 46)
    c = TL.fill(n, (40, 78, 34), 10, 47) + ((idx % 7)[..., None] - 3) * 6
    return np.where((e < 0.01)[..., None], c * 0.55, c)


def grate(n=128):
    x, y = TL.xy(n)
    bars = ((x * 10) % 1 < 0.45) | (np.abs(x - 0.5) > 0.46) | (np.abs(y - 0.5) > 0.46)
    return np.where(bars[..., None], ML.C((80, 84, 86)), ML.C((8, 8, 10))) + TL.N3(n, 1, 48, 5)


def sky_stanza(ns):
    t = f'textures/{ns}/sky'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n\tsurfaceparm sky\n'
            f'\tq3map_sun 0.55 0.65 1 120 120 40\n\tq3map_skylight 110 3\n\tskyparms env/pf-garden512 - -\n}}\n\n')


def glow_stanza(ns, name):
    t = f'textures/{ns}/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
            f'\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t}}\n}}\n\n')


# ------------------------------------------------------------------------------------------------- model materials
def materials():
    m = lambda key, arr, kind='lm', **o: M_.__setitem__(key, TX.material(key, arr, kind, **o))
    m('paint', TL.solid((40, 120, 124), 3, 51), 'lms', v=0.22, shade=70, two=True)
    m('paintside', woodie_band(), 'lms', v=0.18, shade=70, two=True)
    m('cream', TL.solid((236, 228, 204), 3, 52), 'lms', v=0.15, shade=70, two=True)
    m('chrome', TL.metal((200, 204, 210), brushed=False), 'lms', v=0.5, shade=60)
    m('tyre', TL.solid((26, 26, 28), 4, 53), shade=60)
    m('whitewall', TL.solid((236, 236, 230), 2, 54), shade=60)
    m('carglass', TL.solid((150, 180, 190), 2, 55), 'glass', c='0.06 0.08 0.09', two=True)
    m('vinyl', TL.fabric((150, 52, 40), weave=48), shade=50)
    m('carpet', TL.fabric((60, 56, 52), weave=96), shade=50)
    m('dash', TL.solid((110, 70, 44), 4, 56), shade=40)
    m('glovebox', TL.solid((150, 104, 66), 3, 94, 64), shade=40)
    m('grille', grille_tex(), 'lms', v=0.3, shade=30)
    m('headlight', TL.solid((255, 250, 220), 1, 57), 'glow')
    m('taillight', TL.solid((220, 30, 30), 2, 58), 'glow')
    m('stand', TL.solid((200, 40, 30), 3, 59), shade=30)
    m('rust', TL.grime(TL.metal((120, 110, 100)), 0.5, 60), shade=40)
    m('engine', TL.grime(TL.metal((90, 96, 100)), 0.4, 61), 'lms', v=0.1, shade=40)
    m('hoist', TL.solid((220, 160, 30), 3, 62), shade=30)
    m('chain', TL.metal((120, 122, 126)), shade=60)
    m('mower', TL.solid((200, 40, 30), 3, 63), 'lms', v=0.12, shade=40)
    m('black', TL.solid((30, 30, 32), 2, 64), shade=50)
    m('toolred', TL.solid((196, 30, 28), 2, 65), 'lms', v=0.2, shade=20)
    m('drawerfront', drawer_tex(), 'lms', v=0.15, shade=20)
    m('bench', TL.planks((176, 130, 80), n_planks=5, grain=10), shade=20)
    m('benchleg', TL.planks((150, 110, 70), n_planks=2, grain=10, vertical=True), shade=20)
    m('pegboard', pegboard_tex(), shade=20)
    m('shelfsteel', TL.metal((110, 120, 130), brushed=True), shade=20)
    m('white', TL.solid((240, 240, 236), 2, 66), 'lms', v=0.08, shade=30)
    m('panel', TL.label('HEAVY DUTY', 256, 64, (60, 64, 70), (220, 220, 220)), shade=20)
    m('cardboard', TL.solid((176, 140, 96), 6, 67), shade=20)
    m('xmasbox', TL.label('XMAS\nDECOS', 256, 256, (176, 140, 96), (180, 30, 30)), shade=20)
    m('boxlabel', TL.label('FRAGILE', 256, 128, (176, 140, 96), (40, 40, 40)), shade=20)
    m('tent', TL.fabric((40, 110, 60), weave=40), shade=60)
    m('sleeping', TL.stripes((40, 70, 160), (30, 50, 120), n_stripes=6, vertical=False), shade=60)
    m('chilly', TL.label('CHILLY BIN', 256, 128, (230, 236, 240), (30, 80, 200)), 'lms', v=0.1, shade=20)
    m('chillylid', TL.solid((40, 90, 200), 3, 68), 'lms', v=0.1, shade=20)
    m('rod', TL.solid((40, 40, 46), 2, 69), shade=70)
    m('concretetub', TL.grime(TL.solid((178, 176, 170), 8, 70, 256), 0.3), shade=20)
    m('washer', TL.solid((244, 244, 240), 2, 71), 'lms', v=0.1, shade=25)
    m('porthole', TL.solid((120, 150, 170), 2, 72), 'glass', c='0.10 0.12 0.15')
    m('knobs', TL.label('WASH  RINSE  SPIN', 256, 64, (210, 214, 216), (40, 40, 40)), shade=20)
    m('yellow', TL.solid((246, 200, 40), 3, 73), 'lms', v=0.1, shade=60)
    m('mopwater', TL.solid((150, 170, 160), 6, 74), 'add', wave='sin 0.5 0.06 0 0.3')
    m('mophead', TL.fabric((220, 216, 200), weave=24), shade=80)
    m('wood', TL.planks((170, 130, 84), n_planks=3, grain=10), shade=20)
    m('ladder', TL.metal((170, 176, 182)), shade=30)
    m('rollerdoor', corrugated((206, 208, 204), ribs=1, n=64), shade=20)
    m('alu', TL.metal((176, 182, 186)), 'lms', v=0.25, shade=40, two=True)
    m('trailer', TL.solid((40, 44, 50), 3, 75), shade=40)
    m('bin', TL.solid((40, 100, 50), 3, 76), shade=30)
    m('binlid', TL.solid((200, 50, 40), 3, 77), shade=30)
    m('bikeframe', TL.solid((40, 140, 220), 2, 78), 'lms', v=0.2, shade=60)
    m('hose', TL.solid((40, 150, 60), 3, 79), shade=70)
    m('reel', TL.solid((220, 140, 30), 3, 80), shade=40)
    m('log', TL.planks((120, 84, 52), n_planks=2, grain=14), shade=70)
    m('logend', TL.stone((190, 150, 100), cells=6, edge=(120, 84, 52)), shade=20)
    m('lamp', TL.solid((50, 54, 58), 3, 81), shade=50)
    m('lampglow', TL.solid((255, 210, 140), 1, 82), 'glow')
    m('bulb', TL.solid((255, 246, 220), 1, 83), 'glow')
    m('stripglow', TL.solid((240, 248, 255), 1, 84), 'glow')
    m('housing', TL.solid((220, 222, 224), 2, 85), shade=30)
    m('backboard', TL.solid((240, 240, 240), 2, 95, 64), shade=20)
    m('hoop', TL.solid((230, 90, 30), 2, 86), shade=60)
    m('net', TL.solid((240, 240, 240), 1, 87), 'add')
    m('sardine', TL.label('SARDINES', 256, 128, (200, 40, 40), (250, 230, 120)), 'lms', v=0.25, shade=30)
    m('tin', TL.metal((190, 194, 198)), 'lms', v=0.3, shade=40)
    m('cap', TL.solid((200, 30, 30), 2, 88), 'lms', v=0.2, shade=40)
    m('candle', TL.solid((240, 236, 220), 2, 89), shade=60)
    m('flame', TL.solid((255, 190, 80), 1, 90), 'glow')
    m('felt', TL.fabric((40, 100, 50), weave=64), shade=20)


def woodie_band(n=256):
    """lower-body side: teal paint below, a woodgrain panel band with chrome trim above (row 0 = top of the body)"""
    c = TL.solid((40, 120, 124), 3, 91, n)
    w = TL.planks((150, 96, 52), n_planks=1, grain=14, n=n)
    y = np.arange(n)[:, None] / n
    band = (y > 0.12) & (y < 0.55)
    c = np.where(band[..., None], w, c)
    trim = (np.abs(y - 0.12) < 0.02) | (np.abs(y - 0.55) < 0.02)
    return np.where(trim[..., None], ML.C((220, 224, 228)), c)


def grille_tex(n=128):
    x, y = TL.xy(n)
    m = ((x * 12) % 1 < 0.25) | ((y * 4) % 1 < 0.2)
    return np.where(m[..., None], ML.C((210, 214, 220)), ML.C((20, 20, 24)))


def drawer_tex(n=256):
    x, y = TL.xy(n)
    c = TL.solid((196, 30, 28), 2, 92, n)
    seam = (y * 6) % 1 < 0.04
    handle = (np.abs(((y * 6) % 1) - 0.5) < 0.06) & (np.abs(x - 0.5) < 0.3)
    c = np.where(seam[..., None], ML.C((60, 10, 10)), c)
    return np.where(handle[..., None], ML.C((210, 214, 220)), c)


def pegboard_tex(n=256):
    x, y = TL.xy(n)
    holes = (((x * 16) % 1 - 0.5) ** 2 + ((y * 16) % 1 - 0.5) ** 2) < 0.02
    c = TL.solid((178, 140, 96), 4, 93, n)
    return np.where(holes[..., None], ML.C((40, 30, 20)), c)


# ================================================================================================= helpers
def quad(M, p0, p1, p2, p3, uv=((0, 1), (1, 1), (1, 0), (0, 0)), n=None):
    """p0..p3 = bottom-left, bottom-right, top-right, top-left as seen from the front; image row 0 = top"""
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n = n / max(np.linalg.norm(n), 1e-9)
    M.poly(P, n, list(uv))


def loft(X, sections, shader_fn, uv_fn, skip=None, centre_fn=None):
    """surface through matching closed cross-sections (lists of 3D points, same count). shader_fn(normal) -> shader,
    uv_fn(point) -> (u, v), skip(centre, normal) -> True drops a quad (door holes). Normals point away from
    centre_fn(point) (default: the section's own centroid)."""
    S = [np.asarray(s, float) for s in sections]
    m = len(S[0])
    for i in range(len(S) - 1):
        a, b = S[i], S[i + 1]
        ca, cb = a.mean(0), b.mean(0)
        for j in range(m):
            k = (j + 1) % m
            P = [a[j], a[k], b[k], b[j]]
            c = sum(P) / 4
            n = np.cross(P[1] - P[0], P[3] - P[0])
            if np.linalg.norm(n) < 1e-6: n = np.cross(P[2] - P[1], P[0] - P[1])
            if np.linalg.norm(n) < 1e-6: continue
            n = n / np.linalg.norm(n)
            ref = centre_fn(c) if centre_fn else (ca + cb) / 2
            if n @ (c - ref) < 0: n = -n
            if skip and skip(c, n): continue
            X.mesh(shader_fn(n, c)).poly(P, n, [uv_fn(p, n) for p in P])


def cap(X, sec, shader, normal, uv_fn):
    sec = np.asarray(sec, float); c = sec.mean(0)
    m = len(sec)
    for j in range(m):
        k = (j + 1) % m
        P = [c, sec[j], sec[k]]
        X.mesh(shader).poly(P, normal, [uv_fn(p, normal) for p in P])


def rounded_rect(cx, w, zb, zt, r, n=4):
    """closed section in the xz plane at the given y (added by caller): half-width w, bottom zb, top zt, corner r"""
    r = min(r, w - 1, (zt - zb) / 2 - 1)
    pts = []
    for (ox, oz, a0) in ((w - r, zb + r, -90), (w - r, zt - r, 0), (-w + r, zt - r, 90), (-w + r, zb + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + ox + r * math.cos(a), oz + r * math.sin(a)))
    return pts


def wheel(X, c, r=200, w=150, axis='x'):
    """tyre with whitewall and a chrome hubcap, axis along x (car wheels) or y"""
    W = ML.Model()
    prof = [(r * 0.62, -w / 2), (r * 0.9, -w / 2 - 4), (r, -w / 2 + 20), (r, w / 2 - 20), (r * 0.9, w / 2 + 4), (r * 0.62, w / 2)]
    revolve(W.mesh(M_['tyre']), [(p[0], p[1]) for p in prof], n=28)
    revolve(W.mesh(M_['whitewall']), [(r * 0.62, w / 2 + 0.5), (r * 0.86, w / 2 + 4.5)], n=28, inward=False)
    revolve(W.mesh(M_['whitewall']), [(r * 0.86, -w / 2 - 4.5), (r * 0.62, -w / 2 - 0.5)], n=28)
    revolve(W.mesh(M_['chrome']), [(r * 0.62, w / 2 + 1), (r * 0.4, w / 2 + 14), (0, w / 2 + 18)], n=24, inward=True)
    revolve(W.mesh(M_['chrome']), [(0, -w / 2 - 18), (r * 0.4, -w / 2 - 14), (r * 0.62, -w / 2 - 1)], n=24, inward=True)
    R = rot_axis((0, 1, 0), math.pi / 2) if axis == 'x' else rot_axis((1, 0, 0), math.pi / 2)
    X.add_model(W, R, c)


# ================================================================================================= the car
CAR = dict(L=2520, W=510, zb=200, belt=600, roof=920, ws=-330, rear=1150, door=(-330, 330), sill=290, floor=240)
CAR_WHEELS = [(-430, -800), (430, -800), (-430, 820), (430, 820)]


def car():
    """1960s station wagon ('woodie' band), driver's door (+x side) swung open, on red axle stands.
    Model space: x across (+x = the open-door side), y along (front = -y), z up from the garage floor."""
    X = ML.Model()
    L2, W, zb, belt, roof = CAR['L'] / 2, CAR['W'], CAR['zb'], CAR['belt'], CAR['roof']
    d0, d1 = CAR['door']
    # lower body: rounded-rect sections along y; nose and tail rounded by shrinking the end sections
    ys = [-L2, -L2 + 20, -L2 + 60, -L2 + 140] + list(np.linspace(-L2 + 240, L2 - 240, 22)) + [L2 - 140, L2 - 60, L2 - 20, L2]
    secs = []
    for y in ys:
        e = min(y + L2, L2 - y)                      # distance from the nearest end
        k = min(1.0, (e + 30) / 170) ** 0.35
        top = belt - 40 + 40 * min(1, max(0, (y - (-L2 + 900)) / 600)) if y < 0 else belt   # bonnet slopes down
        top = top - (1 - k) * 60
        bot = zb + (1 - k) * 60
        pts = rounded_rect(0, W * (0.86 + 0.14 * k), bot, top, 70 + 40 * (1 - k))
        secs.append([(px, y, pz) for (px, pz) in pts])

    def skip(c, n):          # door opening on the +x side (cut where the door was), sill to belt; and the body
        if n[0] > 0.6 and d0 < c[1] < d1 and CAR['sill'] < c[2] < belt + 5:   # section's flat top over the cabin
            return True        # (it closed the cabin like a lid at the belt line: dark lightmaps, no interior)
        return n[2] > 0.8 and CAR['ws'] + 60 < c[1] < CAR['rear'] - 30 and abs(c[0]) < W * 0.86 - 60

    loft(X, secs, lambda n, c: M_['paintside'] if abs(n[2]) < 0.55 else M_['paint'],
         lambda p, n: (p[1] / 600.0, 1 - (p[2] - zb) / (belt - zb)) if abs(n[2]) < 0.55 else (p[1] / 600.0, p[0] / 600.0),
         skip=skip, centre_fn=lambda c: np.array([0, c[1], (zb + belt) / 2]))
    cap(X, secs[0], M_['paint'], (0, -1, 0), lambda p, n: (p[0] / 600, p[2] / 600))
    cap(X, secs[-1], M_['paint'], (0, 1, 0), lambda p, n: (p[0] / 600, p[2] / 600))
    # greenhouse: pillars + roof in cream, windows glass (two-sided); windscreen raked, tailgate vertical
    gw0, gw1 = W - 40, W - 110                       # half-width at the belt and at the roof
    yb0, yt0, y1 = CAR['ws'], CAR['ws'] + 300, CAR['rear']
    cr, gl = M_['cream'], M_['carglass']
    pil = [(yb0, yt0, 60), (d1 - 30, d1 - 30, 60), (620, 620, 60), (y1 - 50, y1 - 50, 50)]   # (y at belt, y at roof, width)
    for s in (-1, 1):
        def P(yb, yt, t):   # point on the side plane: t=0 belt, t=1 roof
            return np.array([s * (gw0 + (gw1 - gw0) * t), yb + (yt - yb) * t, belt + (roof - belt) * t])
        # windows between pillars (front, rear, cargo) and the pillars themselves
        edges = [(yb0, yt0)] + [(p[0], p[1]) for p in pil[1:]]
        for i in range(len(pil)):
            yb, yt, wd = pil[i]
            quad(X.mesh(cr), P(yb, yt, 0), P(yb + wd, yt + wd, 0), P(yb + wd, yt + wd, 1), P(yb, yt, 1))
            if i + 1 < len(pil):
                nb, nt, _ = pil[i + 1]
                g = X.mesh(gl) if not (s > 0 and i == 0) else None          # driver's window: down (door open)
                if g is not None:
                    quad(g, P(yb + wd, yt + wd, 0), P(nb, nt, 0), P(nb, nt, 1), P(yb + wd, yt + wd, 1))
        # roof rail strip
        quad(X.mesh(cr), P(yb0, yt0, 0.93), P(y1, y1, 0.93), P(y1, y1, 1), P(yb0, yt0, 1))
    # roof
    quad(X.mesh(cr), (-gw1, yt0, roof), (gw1, yt0, roof), (gw1, y1, roof), (-gw1, y1, roof), n=(0, 0, 1),
         uv=((0, 0), (1.6, 0), (1.6, 2.4), (0, 2.4)))
    # windscreen (glass) and tailgate (glass over a cream panel)
    quad(X.mesh(gl), (-gw0, yb0, belt), (gw0, yb0, belt), (gw1, yt0, roof), (-gw1, yt0, roof))
    quad(X.mesh(gl), (-gw0 + 50, y1, belt + 40), (gw0 - 50, y1, belt + 40), (gw1 - 50, y1, roof - 40), (-gw1 + 50, y1, roof - 40))
    for (a, b) in (((-gw0, belt), (-gw0 + 50, roof)), ((gw0 - 50, belt), (gw0, roof))):
        quad(X.mesh(cr), (a[0], y1, a[1]), (b[0], y1, a[1]), (b[0], y1, b[1]), (a[0], y1, b[1]))
    quad(X.mesh(cr), (-gw0, y1, belt), (gw0, y1, belt), (gw0, y1, belt + 40), (-gw0, y1, belt + 40))
    # open door: lower panel + window frame, hinged at the front edge, swung out 62 deg
    D = ML.Model()
    dl = d1 - d0
    rbox(D.mesh(M_['paintside']), (-30, 0, CAR['sill'] - 70), (0, dl, belt), r=8, k=2, tile=600)
    for (a, b) in (((0, 0), (40, 1)), ((dl - 40, 0), (dl, 1))):
        rbox(D.mesh(cr), (-26, a[0], belt), (-4, b[0], belt + (roof - belt) * 0.9), r=4, k=1)
    rbox(D.mesh(cr), (-26, 0, belt + (roof - belt) * 0.85), (-4, dl, belt + (roof - belt) * 0.9), r=4, k=1)
    quad(D.mesh(gl), (-15, 40, belt), (-15, dl - 40, belt), (-15, dl - 40, belt + (roof - belt) * 0.85), (-15, 40, belt + (roof - belt) * 0.85))
    tube(D.mesh(M_['chrome']), [(4, dl - 120, belt - 40), (4, dl - 40, belt - 40)], [8, 8], nseg=6)
    ang = math.radians(62)
    X.add_model(D, rot_z(-ang), (W, d0, 0))
    # interior: carpet floor, trim panels, dash with glovebox, two bucket seats, folded rear bench, steering wheel
    fl = CAR['floor']
    cf = fl + 2                                    # carpet 2u above the collision floor pan's top
    quad(X.mesh(M_['carpet']), (-W + 50, yb0, cf), (W - 50, yb0, cf), (W - 50, y1, cf), (-W + 50, y1, cf), n=(0, 0, 1),
         uv=((0, 0), (2, 0), (2, 3), (0, 3)))
    rbox(X.mesh(M_['dash']), (-W + 60, yb0, fl), (W - 60, yb0 + 140, belt - 60), r=20, k=2, tile=300)
    quad(X.mesh(M_['glovebox']), (-330, yb0 + 141, belt - 200), (-130, yb0 + 141, belt - 200), (-130, yb0 + 141, belt - 110),
         (-330, yb0 + 141, belt - 110), n=(0, 1, 0))
    sw = [(250 + 110 * math.cos(a), yb0 + 230, 560 + 110 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(X.mesh(M_['black']), sw, [12] * len(sw), nseg=6, caps=(False, False))
    tube(X.mesh(M_['black']), [(250, yb0 + 230, 560), (250, yb0 + 140, 500)], [16, 16], nseg=6)
    for sx in (-1, 1):
        x0, x1 = (60, 400) if sx > 0 else (-400, -60)
        rbox(X.mesh(M_['vinyl']), (x0, 40, fl), (x1, 260, fl + 150), r=30, k=3, tile=200)
        rbox(X.mesh(M_['vinyl']), (x0, 240, fl + 120), (x1, 320, fl + 470), r=30, k=3, tile=200)
    rbox(X.mesh(M_['vinyl']), (-W + 70, 520, fl), (W - 70, 760, fl + 16), r=6, k=1, tile=200)
    for s in (-1, 1):                                # inner trim below the belt (not over the door hole)
        x = s * (W - 46)
        for (ya, yb_) in ((yb0, y1),) if s < 0 else ((yb0, d0), (d1, y1)):
            quad(X.mesh(M_['vinyl']), (x, ya, fl), (x, yb_, fl), (x, yb_, belt), (x, ya, belt), n=(-s, 0, 0),
                 uv=((0, 0), ((yb_ - ya) / 300, 0), ((yb_ - ya) / 300, 1), (0, 1)))
    # front: grille, headlights, bumpers; rear: tail lights, bumper
    quad(X.mesh(M_['grille']), (-300, -L2 - 2, zb + 120), (300, -L2 - 2, zb + 120), (300, -L2 - 2, zb + 300), (-300, -L2 - 2, zb + 300), n=(0, -1, 0))
    for s in (-1, 1):
        disc_y(X, M_['headlight'], (s * 390, -L2 + 12, zb + 230), 64, -1)
        quad(X.mesh(M_['taillight']), (s * 470 - 40, L2 + 2, zb + 200), (s * 470 + 40, L2 + 2, zb + 200),
             (s * 470 + 40, L2 + 2, zb + 340), (s * 470 - 40, L2 + 2, zb + 340), n=(0, 1, 0))
    for yy, sg in ((-L2 - 30, -1), (L2 + 30, 1)):
        tube(X.mesh(M_['chrome']), [(-W + 10, yy - sg * 40, zb + 90), (-W + 40, yy, zb + 90), (W - 40, yy, zb + 90),
                                    (W - 10, yy - sg * 40, zb + 90)], [34, 36, 36, 34], nseg=10)
    # wheels (hanging just off the floor) + axle stands
    for (wx, wy) in CAR_WHEELS:
        wheel(X, (wx + (40 if wx > 0 else -40), wy, 240), 200, 150)
    for (sx, sy) in ((-300, -560), (300, -560), (-300, 600), (300, 600)):
        stand(X, (sx, sy, 0), zb)
    # exhaust under the body
    tube(X.mesh(M_['rust']), [(-260, -700, zb - 20), (-260, 600, zb - 20), (-260, L2 + 60, zb - 10)], [30, 30, 30], nseg=8)
    return ML.save('car', X)


def disc_y(X, sh, c, r, sgn):
    pts = [(c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
    X.mesh(sh).poly(pts, (0, sgn, 0), [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)])


def stand(X, base, top):
    """red pyramid axle stand from the floor up to `top` under the sill"""
    x, y, z = base
    mprism(X.mesh(M_['stand']), [(x - 60, y - 60), (x + 60, y - 60), (x + 60, y + 60), (x - 60, y + 60)], z, z + 16)
    for (a, b) in (((-60, -60), (-14, -14)), ((60, -60), (14, -14)), ((60, 60), (14, 14)), ((-60, 60), (-14, 14))):
        tube(X.mesh(M_['stand']), [(x + a[0], y + a[1], z + 16), (x + b[0], y + b[1], top - 30)], [10, 8], nseg=6)
    rbox(X.mesh(M_['stand']), (x - 20, y - 20, top - 40), (x + 20, y + 20, top), r=4, k=1)


# ================================================================================================= garage props
def engine_hoist():
    """yellow engine crane: legs on the floor (16u, walk over), mast, boom, chain, engine block hanging"""
    X = ML.Model(); h = M_['hoist']
    for s in (-1, 1):
        rbox(X.mesh(h), (s * 220 - 30, -420, 0), (s * 220 + 30, 420, 16), r=4, k=1)
        for yy in (-420, 420): wheel_small(X, (s * 220, yy, 0))
    rbox(X.mesh(h), (-250, -440, 0), (250, -380, 16), r=4, k=1)
    tube(X.mesh(h), [(0, -410, 16), (0, -410, 1150)], [44, 40], nseg=10)
    tube(X.mesh(h), [(0, -450, 1100), (0, 120, 1240), (0, 520, 1260)], [30, 26, 22], nseg=8)
    tube(X.mesh(h), [(0, -410, 360), (0, -100, 1170)], [18, 16], nseg=8)
    for k in range(24):
        z = 1240 - 30 * k
        tube(X.mesh(M_['chain']), [(0, 520, z), (0, 520, z - 24)], [5, 5], nseg=4)
    rbox(X.mesh(M_['engine']), (-200, 320, 160), (200, 720, 500), r=20, k=2, tile=300)
    for k in range(4):
        rbox(X.mesh(M_['engine']), (-150 + 100 * k - 30, 360, 500), (-150 + 100 * k + 30, 680, 540), r=6, k=1)
    tube(X.mesh(M_['rust']), [(220, 400, 280), (300, 400, 240), (300, 680, 240)], [24, 24, 24], nseg=6)
    COLL['hoist'] = dict(cyls=[(0, -410, 48, 16, 1150)], boxes=[((-210, 310, 150), (210, 730, 540))])
    return ML.save('hoist', X)


def wheel_small(X, c, r=26):
    W = ML.Model()
    revolve(W.mesh(M_['black']), [(r * 0.5, -10), (r, -10), (r, 10), (r * 0.5, 10)], n=12)
    X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), (c[0], c[1], c[2] + r))


def mower():
    X = ML.Model()
    rbox(X.mesh(M_['mower']), (-180, -230, 70), (180, 230, 230), r=40, k=3, tile=300)
    rbox(X.mesh(M_['black']), (-100, -60, 230), (100, 120, 330), r=20, k=2)
    for (x, y) in ((-190, -170), (190, -170), (-190, 170), (190, 170)):
        W = ML.Model(); revolve(W.mesh(M_['black']), [(30, -20), (70, -20), (70, 20), (30, 20)], n=16)
        X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), (x, y, 70))
    for s in (-1, 1):
        tube(X.mesh(M_['black']), [(s * 150, 200, 200), (s * 150, 520, 620)], [14, 14], nseg=6)
    tube(X.mesh(M_['black']), [(-150, 520, 620), (150, 520, 620)], [16, 16], nseg=6)
    COLL['mower'] = dict(boxes=[((-200, -250, 0), (200, 250, 330))])
    return ML.save('mower', X)


def tyre_stack(n=4):
    X = ML.Model()
    for k in range(n):
        W = ML.Model()
        prof = [(120, 0), (180, 4), (200, 30), (200, 110), (180, 136), (120, 140)]
        revolve(W.mesh(M_['tyre']), [(p[0], p[1]) for p in prof], n=28)
        revolve(W.mesh(M_['tyre']), [(120, 140), (120, 0)], n=28, inward=True)
        X.add_model(W, rot_z(k * 0.4), (k * 6 - 9, (k % 2) * 8, k * 140))
    COLL['tyres'] = dict(cyls=[(0, 0, 196, 0, n * 140)])
    return ML.save('tyres', X)


def toolbox():
    """red rolling toolbox, two drawers pulled out"""
    X = ML.Model()
    rbox(X.mesh(M_['toolred']), (-210, -130, 50), (210, 130, 640), r=10, k=2, tile=420)
    quad(X.mesh(M_['drawerfront']), (-200, -131, 70), (200, -131, 70), (200, -131, 620), (-200, -131, 620), n=(0, -1, 0))
    for (z, out) in ((450, 120), (250, 60)):
        rbox(X.mesh(M_['toolred']), (-190, -130 - out, z), (190, -130, z + 70), r=4, k=1)
    for (x, y) in ((-170, -100), (170, -100), (-170, 100), (170, 100)): wheel_small(X, (x, y, 0), 25)
    tube(X.mesh(M_['chrome']), [(-230, -100, 560), (-260, -100, 560), (-260, 100, 560), (-230, 100, 560)], [10] * 4, nseg=6)
    COLL['toolbox'] = dict(boxes=[((-220, -140, 0), (220, 140, 640))])
    return ML.save('toolbox', X)


def freezer():
    X = ML.Model()
    rbox(X.mesh(M_['white']), (-360, -210, 20), (360, 210, 490), r=24, k=3, tile=720)
    rbox(X.mesh(M_['white']), (-366, -216, 490), (366, 216, 520), r=10, k=2, tile=720)
    rbox(X.mesh(M_['black']), (-120, -232, 440), (120, -216, 470), r=4, k=1)
    rbox(X.mesh(M_['black']), (-360, -210, 0), (360, 210, 20), r=4, k=1)
    COLL['freezer'] = dict(boxes=[((-366, -216, 0), (366, 216, 520))])
    return ML.save('freezer', X)


def washer():
    X = ML.Model()
    rbox(X.mesh(M_['washer']), (-180, -180, 20), (180, 180, 510), r=16, k=2, tile=360)
    quad(X.mesh(M_['knobs']), (-170, -181, 430), (170, -181, 430), (170, -181, 500), (-170, -181, 500), n=(0, -1, 0))
    revolve_y(X, M_['chrome'], (0, -181, 230), [(130, 0), (130, -10), (110, -14)])
    disc_yy(X, M_['porthole'], (0, -190, 230), 110)
    rbox(X.mesh(M_['black']), (-170, -170, 0), (170, 170, 20), r=4, k=1)
    COLL['washer'] = dict(boxes=[((-182, -182, 0), (182, 182, 510))])
    return ML.save('washer', X)


def revolve_y(X, sh, c, prof):
    W = ML.Model(); revolve(W.mesh(sh), prof, n=28)
    X.add_model(W, rot_axis((1, 0, 0), math.pi / 2), c)


def disc_yy(X, sh, c, r):
    disc_y(X, sh, c, r, -1)


def mop_bucket():
    X = ML.Model()
    revolve(X.mesh(M_['yellow']), [(110, 0), (140, 260)], n=28)
    revolve(X.mesh(M_['yellow']), [(140, 260), (130, 264), (106, 6)], n=28)
    disc(X.mesh(M_['yellow']), 108, 6, up=True, n=28)
    disc(X.mesh(M_['mopwater']), 128, 200, up=True, n=28)
    tube(X.mesh(M_['wood']), [(30, 0, 150), (90, 40, 900)], [12, 12], nseg=6)
    for k in range(10):
        a = k * 2 * math.pi / 10
        tube(X.mesh(M_['mophead']), [(30, 0, 160), (30 + 60 * math.cos(a), 60 * math.sin(a), 60)], [14, 10], nseg=5)
    COLL['bucket'] = dict(cyls=[(0, 0, 140, 0, 264)])
    return ML.save('bucket', X)


def plank(name, length, width=200, thick=24):
    """a timber plank lying along +x from x 0 (pitch it when placing; collision is the ramp brush)"""
    X = ML.Model()
    rbox(X.mesh(M_['wood']), (0, -width / 2, -thick), (length, width / 2, 0), r=3, k=1, tile=400)
    return ML.save(name, X)


def ladder(name, height, width=180):
    X = ML.Model()
    for s in (-1, 1):
        rbox(X.mesh(M_['ladder']), (s * width / 2 - 12, -12, 0), (s * width / 2 + 12, 12, height), r=3, k=1)
    for z in np.arange(80, height - 20, 100):
        tube(X.mesh(M_['ladder']), [(-width / 2, 0, z), (width / 2, 0, z)], [8, 8], nseg=6)
    return ML.save(name, X)


def xmas_box(name, w, d, h, label='xmasbox'):
    X = ML.Model()
    rbox(X.mesh(M_['cardboard']), (-w / 2, -d / 2, 0), (w / 2, d / 2, h), r=4, k=1, tile=400, faces='newtb')
    quad(X.mesh(M_[label]), (-w / 2, -d / 2 - 1, 0), (w / 2, -d / 2 - 1, 0), (w / 2, -d / 2 - 1, h), (-w / 2, -d / 2 - 1, h), n=(0, -1, 0))
    COLL[name] = dict(boxes=[((-w / 2, -d / 2, 0), (w / 2, d / 2, h))])
    return ML.save(name, X)


def tent_bag():
    X = ML.Model()
    tube(X.mesh(M_['tent']), [(-260, 0, 90), (260, 0, 90)], [90, 90], nseg=16)
    for k in range(3):
        tube(X.mesh(M_['sleeping']), [(-200 + 200 * k, -260, 80), (-200 + 200 * k, -100, 80)], [80, 80], nseg=16)
    COLL['tentbag'] = dict(boxes=[((-350, -350, 0), (350, 100, 180))])
    return ML.save('tentbag', X)


def chilly_bin():
    X = ML.Model()
    rbox(X.mesh(M_['white']), (-220, -140, 0), (220, 140, 260), r=20, k=2, tile=440)
    quad(X.mesh(M_['chilly']), (-190, -141, 60), (190, -141, 60), (190, -141, 230), (-190, -141, 230), n=(0, -1, 0))
    rbox(X.mesh(M_['chillylid']), (-226, -146, 260), (226, 146, 300), r=14, k=2, tile=440)
    COLL['chilly'] = dict(boxes=[((-226, -146, 0), (226, 146, 300))])
    return ML.save('chilly', X)


def fishing_rods():
    X = ML.Model()
    for k in range(3):
        tube(X.mesh(M_['rod']), [(-600, -40 + 40 * k, 10), (600, -40 + 40 * k + 20, 14)], [8, 3], nseg=5)
        tube(X.mesh(M_['chrome']), [(-420, -40 + 40 * k, 18), (-420, -40 + 40 * k, 40)], [14, 14], nseg=8)
    return ML.save('rods', X)


def roller_door(w, h, drum_y=90):
    """corrugated door curtain (front face at y 0) and the drum housing above it"""
    X = ML.Model()
    ribs = int(h / 60)
    for k in range(ribs):
        z0, z1 = k * h / ribs, (k + 1) * h / ribs
        quad(X.mesh(M_['rollerdoor']), (-w / 2, 0, z0), (w / 2, 0, z0), (w / 2, 4, (z0 + z1) / 2), (-w / 2, 4, (z0 + z1) / 2), n=(0, -1, 0.3))
        quad(X.mesh(M_['rollerdoor']), (-w / 2, 4, (z0 + z1) / 2), (w / 2, 4, (z0 + z1) / 2), (w / 2, 0, z1), (-w / 2, 0, z1), n=(0, -1, -0.3))
    rbox(X.mesh(M_['rollerdoor']), (-w / 2, 0, -20), (w / 2, 20, 0), r=4, k=1, tile=600)
    tube(X.mesh(M_['housing']), [(-w / 2 - 30, drum_y, h + 90), (w / 2 + 30, drum_y, h + 90)], [90, 90], nseg=16)
    return ML.save('rollerdoor', X)


def dinghy():
    """aluminium dinghy (tinny) on a road trailer; the trailer drawbar is the walk-up (collision = ramp brush)"""
    X = ML.Model()
    L, B, H, z0 = 1500, 300, 260, 260                # length, half-beam, side height, keel z
    ys = np.linspace(-L / 2, L / 2, 14)
    outer, inner = [], []

    def beam(y):                                     # outer half-beam at the gunwale and keel height along the boat
        t = (y + L / 2) / L
        bw = B * (0.35 + 0.65 * math.sin(min(1, t * 1.25) * math.pi / 2)) if t < 0.8 else B
        return bw, z0 + (max(0, 0.22 - t) / 0.22) ** 2 * 140

    def inner_w(y, z):                               # inside half-width of the hull at height z (deck boards, seats)
        bw, zk = beam(y)
        zc, zt = zk + 54, z0 + H + 14
        f = min(1.0, max(0.0, (z - zc) / max(1.0, zt - zc)))
        return bw * 0.92 * (0.9 + 0.1 * f) - 4
    for y in ys:
        bw, zk = beam(y)
        sec = [(-bw, y, z0 + H), (-bw * 0.9, y, zk + 40), (0, y, zk), (bw * 0.9, y, zk + 40), (bw, y, z0 + H)]
        outer.append(sec); inner.append([(p[0] * 0.92, p[1], p[2] + 14) for p in sec])
    for S, cf in ((outer, lambda c: np.array([0, c[1], z0 + H + 200])), (inner, lambda c: np.array([0, c[1], z0 + H + 900]))):
        for i in range(len(S) - 1):
            for j in range(4):
                P = [np.array(S[i][j]), np.array(S[i][j + 1]), np.array(S[i + 1][j + 1]), np.array(S[i + 1][j])]
                c = sum(P) / 4; n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(np.linalg.norm(n), 1e-9)
                if S is outer and n @ (c - cf(c)) < 0: n = -n
                if S is inner and n @ (cf(c) - c) < 0: n = -n
                X.mesh(M_['alu']).poly(P, n, [(p[1] / 400, p[2] / 400) for p in P])
    # transom (flat stern), seats, gunwale
    st = outer[-1]
    X.mesh(M_['alu']).poly([np.array(p) for p in st], (0, 1, 0), [(p[0] / 400, p[2] / 400) for p in st])
    for yy in (-200, 300):                           # thwarts: trapezoids that follow the narrowing hull
        za = z0 + 170
        wa, wb = inner_w(yy - 60, za + 20), inner_w(yy + 60, za + 20)
        mprism(X.mesh(M_['wood']), [(-wa, yy - 60), (wa, yy - 60), (wb, yy + 60), (-wb, yy + 60)], za, za + 20, tile=200)
    # trailer: frame, axle, wheels, drawbar, winch post
    for s in (-1, 1):
        tube(X.mesh(M_['trailer']), [(s * 200, -L / 2 - 200, 200), (s * 200, L / 2, 200)], [20, 20], nseg=6)
    tube(X.mesh(M_['trailer']), [(-200, -L / 2 - 200, 200), (0, -L / 2 - 700, 200), (200, -L / 2 - 200, 200)], [20, 20, 20], nseg=6)
    tube(X.mesh(M_['trailer']), [(0, -L / 2 - 300, 200), (0, -L / 2 - 300, 420)], [18, 18], nseg=6)
    for s in (-1, 1): wheel(X, (s * 380, 150, 150), 150, 100)
    tube(X.mesh(M_['trailer']), [(-380, 150, 150), (380, 150, 150)], [16, 16], nseg=6)
    # collision pieces only touch: wheels below the hull, deck boards (z 490) inside the side and end walls
    # collision: a flat bottom box under the hull, then per hull section a tapered deck slab (z 274..490) and two
    # tapered side walls up to the gunwale (convex point sets, model space): the bow narrows in play as it looks
    sol = []
    for y0, y1 in zip(ys[:-1], ys[1:]):
        w0, w1 = inner_w(y0, 490), inner_w(y1, 490)
        o0, o1 = beam(y0)[0] + 6, beam(y1)[0] + 6
        sol.append([(sx * w, y, z) for (w, y) in ((w0, y0), (w1, y1)) for sx in (-1, 1) for z in (z0 + 14, 490)])
        for sx in (-1, 1):
            sol.append([(sx * a, y, z) for (a, b_, y) in ((w0, o0, y0), (w1, o1, y1)) for a in (a, b_) for z in (z0 + 14, z0 + H)])
    COLL['dinghy'] = dict(boxes=[((-B - 20, -L / 2, 240), (B + 20, L / 2, z0 + 14))],
                          cyls=[(s * 380, 150, 150, 0, 240) for s in (-1, 1)], solids=sol)
    yb = np.linspace(-L / 2 + 50, L / 2 - 50, 10)                    # deck boards across the boat (the walk-on floor),
    for ya, yc in zip(yb[:-1] + 4, yb[1:] - 4):                      # each one cut to the hull's width at both ends
        wa, wc = inner_w(ya, 490), inner_w(yc, 490)
        mprism(X.mesh(M_['wood']), [(-wa, ya), (wa, ya), (wc, yc), (-wc, yc)], 482, 490, tile=200)
    return ML.save('dinghy', X)


def wheelie_bin():
    X = ML.Model()
    rbox(X.mesh(M_['bin']), (-180, -200, 60), (180, 200, 640), r=20, k=2, tile=400)
    rbox(X.mesh(M_['binlid']), (-196, -216, 640), (196, 216, 670), r=10, k=2, tile=400)
    for s in (-1, 1):
        W = ML.Model(); revolve(W.mesh(M_['black']), [(30, -20), (60, -20), (60, 20), (30, 20)], n=14)
        X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), (s * 200, 200, 60))
    COLL['bin'] = dict(boxes=[((-196, -216, 0), (196, 216, 670))])
    return ML.save('bin', X)


def bike():
    """kid's bike lying on its side (z up = what was the bike's left side)"""
    X = ML.Model()
    for yy in (-300, 300):
        pts = [(220 * math.cos(a), yy + 220 * math.sin(a), 30) for a in np.linspace(0, 2 * math.pi, 25)]
        tube(X.mesh(M_['black']), pts, [22] * len(pts), nseg=6, caps=(False, False))
        for k in range(8):
            a = k * math.pi / 4
            tube(X.mesh(M_['chrome']), [(0, yy, 30), (210 * math.cos(a), yy + 210 * math.sin(a), 30)], [3, 3], nseg=4)
    tube(X.mesh(M_['bikeframe']), [(0, -300, 40), (180, -60, 50), (0, 300, 40)], [18, 18, 18], nseg=8)
    tube(X.mesh(M_['bikeframe']), [(180, -60, 50), (260, -200, 50), (0, -300, 40)], [16, 16, 16], nseg=8)
    tube(X.mesh(M_['black']), [(260, -200, 50), (330, -180, 50)], [20, 20], nseg=8)
    tube(X.mesh(M_['chrome']), [(180, 200, 50), (260, 260, 50), (260, 160, 60)], [10, 10, 10], nseg=6)
    COLL['bike'] = dict(boxes=[((-250, -540, 0), (340, 540, 60))])
    return ML.save('bike', X)


def hose_reel():
    X = ML.Model()
    for s in (-1, 1):
        revolve_x(X, M_['reel'], (s * 130, 0, 260), [(240, -10), (240, 10)])
    W = ML.Model()
    for k in range(9):
        revolve(W.mesh(M_['hose']), [(150 + 20 * (k % 3), -120 + 28 * k), (150 + 20 * (k % 3), -100 + 28 * k)], n=24)
    X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), (0, 0, 260))
    for s in (-1, 1):
        tube(X.mesh(M_['reel']), [(s * 140, -200, 0), (s * 140, 0, 260), (s * 140, 200, 0)], [16, 16, 16], nseg=6)
    tube(X.mesh(M_['hose']), [(0, -150, 120), (100, -400, 20), (400, -600, 14), (700, -500, 14)], [20, 20, 20, 20], nseg=8)
    COLL['reel'] = dict(boxes=[((-150, -250, 0), (150, 250, 500))])
    return ML.save('reel', X)


def revolve_x(X, sh, c, prof):
    W = ML.Model(); revolve(W.mesh(sh), prof, n=28)
    X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), c)


def firewood(n_rows=4, per_row=3):
    X = ML.Model()
    rng = np.random.default_rng(5)
    for r in range(n_rows):
        for k in range(per_row - (r % 2)):
            y = -(per_row - 1) * 55 + k * 110 + (r % 2) * 55; z = 55 + r * 100
            tube(X.mesh(M_['log']), [(-280, y, z), (280, y + rng.uniform(-8, 8), z)], [52, 52], nseg=8, caps=(False, False))
            for xx, sg in ((-280, -1), (280, 1)):
                pts = [(xx, y + 52 * math.cos(a), z + 52 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                X.mesh(M_['logend']).poly(pts, (sg, 0, 0), [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)])
    COLL['firewood'] = dict(boxes=[((-290, -per_row * 55 - 2, 0), (290, per_row * 55 + 2, n_rows * 100 + 10))])
    return ML.save('firewood', X)


def wheelbarrow():
    X = ML.Model()
    rbox(X.mesh(M_['bin']), (-200, -260, 200), (200, 260, 420), r=40, k=3, tile=400, faces='nsewb')
    W = ML.Model(); revolve(W.mesh(M_['black']), [(40, -30), (110, -30), (110, 30), (40, 30)], n=16)
    X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), (0, -420, 110))
    for s in (-1, 1):
        tube(X.mesh(M_['trailer']), [(s * 60, -420, 110), (s * 160, 0, 200), (s * 200, 700, 380)], [12, 12, 12], nseg=6)
        tube(X.mesh(M_['trailer']), [(s * 160, 260, 200), (s * 160, 260, 0)], [10, 10], nseg=6)
    COLL['barrow'] = dict(boxes=[((-210, -540, 0), (210, 300, 420))])
    return ML.save('barrow', X)


def water_tank():
    """corrugated rainwater tank"""
    X = ML.Model()
    revolve(X.mesh(M_['alu']), [(190, 0), (190, 620)], u_tiles=6, n=32)
    revolve(X.mesh(M_['alu']), [(190, 620), (60, 680), (0, 690)], n=32, inward=True)
    tube(X.mesh(M_['chrome']), [(190, 0, 60), (240, 0, 60)], [14, 14], nseg=6)
    COLL['tank'] = dict(cyls=[(0, 0, 194, 0, 690)])
    return ML.save('tank', X)


def compost():
    X = ML.Model()
    revolve(X.mesh(M_['black']), [(200, 0), (170, 560)], u_tiles=3, n=28)
    revolve(X.mesh(M_['black']), [(174, 560), (186, 600), (0, 610)], n=28, inward=True)
    COLL['compost'] = dict(cyls=[(0, 0, 202, 0, 610)])
    return ML.save('compost', X)


def drum():
    """blue 200-litre oil drum with ribs and a bung"""
    X = ML.Model()
    revolve(X.mesh(M_['chillylid']), [(170, 0), (176, 20), (170, 40), (170, 200), (176, 220), (170, 240), (170, 400),
                                       (176, 420), (170, 440), (170, 560)], u_tiles=3, n=28)
    revolve(X.mesh(M_['chillylid']), [(170, 560), (160, 570), (0, 572)], n=28, inward=True)
    tube(X.mesh(M_['chrome']), [(90, 0, 572), (90, 0, 580)], [18, 18], nseg=8)
    COLL['drum'] = dict(cyls=[(0, 0, 178, 0, 580)])
    return ML.save('drum', X)


def outboard():
    """outboard motor clamped to a wooden stand"""
    X = ML.Model()
    for (x, y) in ((-160, -120), (160, -120), (-160, 120), (160, 120)):
        rbox(X.mesh(M_['wood']), (x - 20, y - 20, 0), (x + 20, y + 20, 560), r=3, k=1)
    rbox(X.mesh(M_['wood']), (-200, -160, 520), (200, 160, 560), r=3, k=1)
    rbox(X.mesh(M_['black']), (-120, -90, 580), (120, 150, 860), r=40, k=3, tile=300)
    rbox(X.mesh(M_['white']), (-125, -95, 760), (125, 155, 880), r=40, k=3, tile=300)
    tube(X.mesh(M_['black']), [(0, 0, 580), (0, 0, 120)], [40, 34], nseg=10)
    rbox(X.mesh(M_['black']), (-30, -60, 60), (30, 80, 140), r=10, k=2)
    tube(X.mesh(M_['chrome']), [(0, -110, 100), (0, -150, 100)], [12, 12], nseg=6)
    COLL['outboard'] = dict(boxes=[((-200, -160, 0), (200, 160, 880))])
    return ML.save('outboard', X)


def street_lamp(h=1800):
    X = ML.Model()
    tube(X.mesh(M_['lamp']), [(0, 0, 0), (0, 0, h), (0, -100, h + 120), (0, -380, h + 160)], [30, 24, 20, 18], nseg=10)
    rbox(X.mesh(M_['lamp']), (-60, -480, h + 120), (60, -280, h + 180), r=10, k=2)
    rbox(X.mesh(M_['lampglow']), (-50, -470, h + 110), (50, -290, h + 122), r=4, k=1)
    COLL['lamp'] = dict(cyls=[(0, 0, 32, 0, h)])
    return ML.save('streetlamp', X)


def hoop():
    """basketball backboard + ring + net, mounted on the gable (y 0 = wall face, facing -y)"""
    X = ML.Model()
    rbox(X.mesh(M_['backboard']), (-240, -40, 0), (240, -10, 330), r=6, k=1, tile=480)
    rbox(X.mesh(M_['hoop']), (-90, -42, 60), (90, -40, 200), r=2, k=1, faces='s')
    ring = [(115 * math.cos(a), -170 + 115 * math.sin(a), 40) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(X.mesh(M_['hoop']), ring, [8] * len(ring), nseg=6, caps=(False, False))
    for k in range(10):
        a = k * 2 * math.pi / 10
        tube(X.mesh(M_['net']), [(115 * math.cos(a), -170 + 115 * math.sin(a), 40), (70 * math.cos(a + 0.4), -170 + 70 * math.sin(a + 0.4), -110)], [3, 3], nseg=3)
    return ML.save('hoop', X)


def strip_light(length=720):
    X = ML.Model()
    rbox(X.mesh(M_['housing']), (-length / 2, -50, 20), (length / 2, 50, 50), r=6, k=1, tile=400)
    tube(X.mesh(M_['stripglow']), [(-length / 2 + 20, 0, 12), (length / 2 - 20, 0, 12)], [12, 12], nseg=8)
    for s in (-1, 1): tube(X.mesh(M_['chain']), [(s * length * 0.4, 0, 50), (s * length * 0.4, 0, 140)], [3, 3], nseg=4)
    return ML.save('striplight', X)


def bulb():
    X = ML.Model()
    tube(X.mesh(M_['black']), [(0, 0, 0), (0, 0, -200)], [4, 4], nseg=4)
    sphere(X.mesh(M_['bulb']), (0, 0, -230), 30, nu=12, nv=8)
    return ML.save('bulb', X)


def sewer_props():
    """the rats' den: sardine-tin bed, bottle-cap table, candle"""
    X = ML.Model()
    rbox(X.mesh(M_['sardine']), (-300, -180, 0), (300, 180, 90), r=30, k=3, tile=600)
    rbox(X.mesh(M_['felt']), (-280, -160, 90), (280, 160, 120), r=20, k=2, tile=600)
    ML.save('sardinebed', X)
    COLL['sardinebed'] = dict(boxes=[((-300, -180, 0), (300, 180, 120))])
    X = ML.Model()
    revolve(X.mesh(M_['cap']), [(150, 0), (150, 40), (0, 40)], n=24, inward=True)
    for k in range(21):
        a = k * 2 * math.pi / 21
        tube(X.mesh(M_['cap']), [(150 * math.cos(a), 150 * math.sin(a), 0), (156 * math.cos(a), 156 * math.sin(a), 40)], [6, 6], nseg=3)
    tube(X.mesh(M_['tin']), [(0, 0, 40), (0, 0, 160)], [20, 20], nseg=8)
    revolve(X.mesh(M_['candle']), [(30, 160), (30, 260), (0, 260)], n=12, inward=True)
    ellipsoid(X.mesh(M_['flame']), (0, 0, 280), 10, 10, 24)
    ML.save('captable', X)
    COLL['captable'] = dict(cyls=[(0, 0, 156, 0, 160)])


def pegboard_tools():
    """pegboard panel with tool silhouettes (wrenches, screwdrivers, a saw) standing proud of it; faces -x"""
    X = ML.Model()
    quad(X.mesh(M_['pegboard']), (0, -700, 0), (0, 700, 0), (0, 700, 700), (0, -700, 700), n=(-1, 0, 0),
         uv=((0, 1), (2, 1), (2, 0), (0, 0)))
    for k in range(6):
        y = -600 + k * 60; L_ = 160 + k * 30
        tube(X.mesh(M_['chrome']), [(-14, y, 600), (-14, y, 600 - L_)], [14, 12], nseg=6)
        rbox(X.mesh(M_['chrome']), (-16, y - 20, 600), (-4, y + 20, 630), r=3, k=1)
    for k in range(5):
        y = 0 + k * 70
        tube(X.mesh(M_['toolred']), [(-12, y, 620), (-12, y, 520)], [14, 14], nseg=6)
        tube(X.mesh(M_['chrome']), [(-12, y, 520), (-12, y, 400)], [4, 4], nseg=4)
    quad(X.mesh(M_['chrome']), (-8, 380, 200), (-8, 680, 160), (-8, 680, 260), (-8, 380, 280), n=(-1, 0, 0))
    rbox(X.mesh(M_['wood']), (-20, 340, 180), (-6, 400, 300), r=3, k=1)
    return ML.save('pegtools', X)


def vice():
    X = ML.Model()
    rbox(X.mesh(M_['shelfsteel']), (-60, -100, 0), (60, 100, 60), r=6, k=1)
    rbox(X.mesh(M_['shelfsteel']), (-50, -90, 60), (50, -40, 180), r=6, k=1)
    rbox(X.mesh(M_['shelfsteel']), (-50, 40, 60), (50, 90, 180), r=6, k=1)
    tube(X.mesh(M_['chrome']), [(0, -90, 120), (0, -260, 120)], [10, 10], nseg=6)
    tube(X.mesh(M_['chrome']), [(-80, -260, 120), (80, -260, 120)], [8, 8], nseg=6)
    return ML.save('vice', X)


def solids_tex(key, side_key=None, tile=256.0):
    def f(c, n, poly):
        k = side_key if (side_key and abs(n[2]) < 0.7) else key
        return M_[k], ML.planar_uv(n, tile)
    return f


DOOR_W = 1280                     # each of the two roller doors (build_padgarage DOOR / PIER)


def build_all():
    import gr_street as GS
    GS.build_all()
    car(); engine_hoist(); mower(); tyre_stack(); toolbox(); freezer(); washer(); mop_bucket()
    plank('plank_a', 520); plank('plank_b', 780); plank('plank_c', 960); ladder('ladder', 1520)
    xmas_box('xmas1', 420, 300, 300); xmas_box('xmas2', 300, 300, 240, 'boxlabel'); xmas_box('xmas3', 360, 260, 200)
    tent_bag(); chilly_bin(); fishing_rods(); dinghy(); wheelie_bin(); bike(); hose_reel()
    firewood(); wheelbarrow(); water_tank(); compost(); drum(); outboard(); street_lamp(3200); hoop(); strip_light(); bulb(); sewer_props(); pegboard_tools(); vice()
