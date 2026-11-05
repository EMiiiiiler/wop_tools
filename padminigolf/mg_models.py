"""Custom MD3s / IQMs and textures for wop_padminigolf (Mini Golf Madness). All geometry and art is original and
generated here. Origin = floor centre unless noted; "front" faces +x (misc_model angle turns it).

    import mg_models as MM
    MM.init(TX); MM.make_textures(); MM.make_all()
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, rot_z, rot_axis, grid_normals
from woplib import models as ML, texlib as TL
import layout as L

TX = None
xy, C, N3, noise, lerp = ML.xy, ML.C, ML.N3, ML.noise, ML.lerp
Model = ML.Model


def init(tx):
    global TX
    TX = tx


# ================================================================================================= textures
def turf(n=256, seed=1, base=(78, 140, 58)):
    g = noise(n, 0.6, seed); m = noise(n, 6, seed + 1); big = noise(n, 24, seed + 2)
    c = np.zeros((n, n, 3), np.float32) + C(base) + g[..., None] * C((10, 16, 8)) + m[..., None] * 8 + big[..., None] * C((10, 12, 4))
    return c


def felt(n=128, seed=11, base=(40, 160, 80)):
    return ML.fill(n, base, 3, seed) + N3(n, 0.5, seed + 3, 4)


def lava(n=256, seed=21):
    a = noise(n, 6, seed); b = noise(n, 1.5, seed + 1)
    t = np.clip(a * 0.5 + b * 0.25 + 0.5, 0, 1)[..., None]
    return lerp(C((120, 20, 0)), C((255, 200, 40)), t ** 1.5)


def rock(n=256, seed=31, base=(84, 74, 70)):
    idx, edge = ML.voronoi(n, 16, seed)
    tone = np.random.default_rng(seed).uniform(-14, 14, 16)[idx]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 1, seed + 1, 8) + N3(n, 6, seed + 2, 10)
    return np.where((edge < 0.01)[..., None], c * 0.6, c)


def leaves(n=256, seed=41, base=(46, 110, 40)):
    a = noise(n, 1.2, seed); b = noise(n, 4, seed + 1)
    c = np.zeros((n, n, 3), np.float32) + C(base) + (a * 18 + b * 10)[..., None] * C((0.6, 1.0, 0.5))
    return np.where((a > 1.3)[..., None], c + C((40, 50, 20)), c)


def bands(c1, c2, n=128, k=2):
    x, y = xy(n)
    return np.where((((y * k) % 1) < 0.5)[..., None], C(c1), C(c2)) + N3(n, 1, 5, 3)


def dimples(n=256):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((246, 246, 244))
    d = np.hypot(((x * 10) % 1) - 0.5, ((y * 10 + 0.5 * (np.floor(x * 10) % 2)) % 1) - 0.5)
    return c - (np.clip(0.32 - d, 0, 1) * 90)[..., None]


def shingles(n=256, seed=51):
    return TL.tiles((120, 84, 56), (70, 48, 32), cols=8, rows=8, offset=0.5, grout_w=0.05, vary=16, seed=seed)


def make_textures():
    TX.add('turf', turf())
    TX.add('felt', felt())
    TX.add('felt_red', felt(base=(170, 40, 40), seed=12))
    TX.add('rail_blue', TL.planks((40, 90, 180), n_planks=2, grain=4))
    TX.add('rail_white', TL.planks((236, 236, 230), n_planks=2, grain=3))
    TX.add('tee', TL.dots((30, 30, 34), (60, 60, 66), n_dots=16, r=0.2))
    TX.add('path', TL.stone((196, 186, 168), cells=20))
    TX.add('brick', TL.bricks((226, 220, 206), (170, 164, 152), rows=8, cols=4, vary=8))
    TX.add('planks', TL.planks((150, 104, 62)), steps='woodsteps')
    TX.add('stucco', TL.solid((236, 224, 196), 5, 7, 128))
    TX.add('roof_flat', TL.tiles((120, 120, 124), (100, 100, 104), cols=4, rows=4, grout_w=0.02))
    TX.add('rock', rock())
    TX.add('sand', ML.fill(128, (214, 192, 150), 6, 9))
    TX.add('water', ML.fill(128, (50, 130, 150), 6, 5), 'water', rgb=(0.22, 0.52, 0.55), alpha=0.55)
    TX.add('cup', TL.solid((14, 14, 14), 2, 3, 64))
    TX.add('lava', lava(), 'raw', check_tile=False, shader=(
        f'textures/{TX.ns}/lava\n{{\n\tqer_editorimage textures/{TX.ns}/lava\n\tsurfaceparm nolightmap\n\tsurfaceparm noimpact\n'
        '\tq3map_surfacelight 120\n\tq3map_lightRGB 1 0.45 0.1\n'
        f'\t{{\n\t\tmap textures/{TX.ns}/lava\n\t\ttcMod turb 0 0.03 0 0.08\n\t\ttcMod scroll 0.02 0.01\n\t}}\n}}\n\n'))
    TX.add('cavern', rock(seed=33, base=(70, 64, 60)))
    TX.add('sign_club', TL.label('PUTT-PUTT PARADISE', 1024, 256, (30, 90, 50), (250, 240, 200), serif=True), 'sign', check_tile=False)
    TX.add('sign_score', score_tex(), 'sign', check_tile=False)
    TX.add('sign_cavern', TL.label('LOST BALL CAVERN', 512, 128, (40, 36, 30), (240, 220, 140), serif=True), 'sign', check_tile=False)


def score_tex():
    im = ML.text_img('HOLE  1 2 3 4 5 6 | 19\nPAR   2 3 2 3 4 3 | ??', 512, 256, (20, 50, 30), (240, 240, 230), serif=False)
    return im


# ================================================================================================= helpers
def bar(M, a, b, r, n=8):
    tube(M, [np.asarray(a, float), np.asarray(b, float)], r, nseg=n)


def ring_disc(M, r_in, r_out, z, up=True, n=64, tile=512):
    disc(M, r_out, z, up=up, n=n, r_in=r_in, uvscale=tile)


# ================================================================================================= windmill
def windmill():
    """octagonal Dutch mill: brick plinth, shingled tower with the hole-1 tunnel through its base (N-S), the stage deck
    round it at STAGE_Z on struts, the cap with a flat lookout on top. Origin = floor centre of the tower."""
    sh = TX.material('shingle', shingles(), shade=30)
    br = TX.material('mill_brick', TL.bricks((226, 220, 206), (170, 164, 152), rows=8, cols=4, vary=8), shade=30)
    wd = TX.material('mill_wood', TL.planks((150, 104, 62)), shade=40)
    cap = TX.material('mill_cap', shingles(seed=53), shade=60)
    dk = TX.material('mill_dark', TL.solid((30, 26, 22), 2, 3, 32))
    wh = TX.material('trim_white', TL.solid((240, 240, 236), 2, 5, 64))
    X = Model()
    W, H = L.TUNNEL_W, L.TUNNEL_H
    rows = [(L.MILL_R0, 0), (L.MILL_R0, 24), (L.MILL_R0 - 14, 40), (L.MILL_R1, L.MILL_H - 10), (L.MILL_R1 + 8, L.MILL_H)]
    arch = [(-W, 0), (W, 0), (W, H - 50)] + [(W * math.cos(t), H - 50 + 50 * math.sin(t)) for t in np.linspace(0, math.pi, 9)] + [(-W, H - 50)]
    back = [(u + math.pi * 300, z) for (u, z) in arch]
    junk = Model()
    ML.carved_shell(X.mesh(sh), junk.mesh('a'), junk.mesh('b'), rows, 8, 30, [arch, back], 90.0, 300.0, u_tiles=8, vlen=256,
                    close_top=False, close_bottom=False)
    # brick plinth band (0..140) a little proud, with the same arches
    prow = [(L.MILL_R0 + 6, 0), (L.MILL_R0 + 6, 140), (L.MILL_R0 - 8, 150)]
    ML.carved_shell(X.mesh(br), junk.mesh('a'), junk.mesh('b'), prow, 8, 20, [arch, back], 90.0, 300.0, u_tiles=8, vlen=256,
                    close_top=False, close_bottom=False)
    # tunnel lining
    yl = 310
    for sx in (-1, 1):
        X.mesh(br).quad((sx * W, -yl, 0), (sx * W, yl, 0), (sx * W, yl, H - 50), (sx * W, -yl, H - 50), tile=256, n=(-sx, 0, 0))
    P = np.zeros((9, 2, 3)); UV = np.zeros((9, 2, 2))
    for i, t in enumerate(np.linspace(0, math.pi, 9)):
        for j, y in enumerate((-yl, yl)):
            P[i, j] = (W * math.cos(t), y, H - 50 + 50 * math.sin(t)); UV[i, j] = (i / 8, y / 256)
    N = -grid_normals(P)
    if N[4, 0, 2] > 0: N = -N
    X.mesh(br).grid(P, N, UV)
    # stage deck: plank ring on struts, a white edge board, door + windows on the tower
    ring_disc(X.mesh(wd), 270, L.STAGE_R, L.STAGE_Z, up=True, n=8)
    ring_disc(X.mesh(wd), 270, L.STAGE_R, L.STAGE_Z - 16, up=False, n=8)
    revolve(X.mesh(wh), [(L.STAGE_R, L.STAGE_Z - 16), (L.STAGE_R, L.STAGE_Z + 2)], n=8, u_tiles=16)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        c, s = math.cos(a), math.sin(a)
        bar(X.mesh(wd), (c * 300, s * 300, 180), (c * (L.STAGE_R - 30), s * (L.STAGE_R - 30), L.STAGE_Z - 16), 10, 6)
    for k, a in enumerate((0, 180)):
        ar = math.radians(a)
        c, s = math.cos(ar), math.sin(ar)
        r = 296 + 2
        # stage door (dark, with a white frame) and a window higher up
        for (z0, z1, hw, rr) in ((L.STAGE_Z, L.STAGE_Z + 180, 50, 290), (620, 700, 34, 274)):
            p = lambda u, z: (c * rr - s * u, s * rr + c * u, z)
            X.mesh(dk).quad(p(-hw, z0), p(hw, z0), p(hw, z1), p(-hw, z1), tile=128, n=(c, s, 0))
    # cap + lookout
    revolve(X.mesh(cap), [(L.MILL_R1 + 30, L.MILL_H), (L.MILL_R1 + 10, L.MILL_H + 20), (230, 970), (160, 1080), (138, 1150),
                          (138, L.CAP_TOP - 16)], n=48, u_tiles=8)
    revolve(X.mesh(cap), [(0, L.MILL_H + 1), (L.MILL_R1 + 30, L.MILL_H + 1)], n=48, u_tiles=8)   # underside rim faces down
    disc(X.mesh(wd), 150, L.CAP_TOP, up=True, n=32, uvscale=300)
    revolve(X.mesh(wh), [(150, L.CAP_TOP - 16), (150, L.CAP_TOP)], n=32)
    disc(X.mesh(wh), 150, L.CAP_TOP - 16, up=False, n=32)
    # weather vane at the lookout's north edge
    bar(X.mesh(dk), (0, 120, L.CAP_TOP), (0, 120, L.CAP_TOP + 200), 4, 6)
    v = Mesh(); prism(v, [(-60, 0), (60, 0), (40, 30), (-40, 30)], -2, 2, tile=64)
    X.mesh(dk).add(v, rot_axis((1, 0, 0), math.pi / 2), (0, 120, L.CAP_TOP + 170))
    return ML.save('windmill', X)


def sails():
    """four lattice sails round the hub, in the x-z plane (func_rotating about the y axis); IQM because r > 512"""
    wd = TX.material('sail_wood', TL.planks((170, 130, 90)), 'dyn')
    cv = TX.material('sail_canvas', TL.stripes((246, 240, 226), (220, 70, 60), n_stripes=2), 'dyn', two=True)
    X = Model()
    sphere(X.mesh(wd), (0, -20, 0), 46, nu=12, nv=8)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = np.array([math.cos(a), 0, math.sin(a)]); side = np.array([-math.sin(a), 0, math.cos(a)])
        bar(X.mesh(wd), d * 30, d * L.SAIL_R, 10, 6)
        p = lambda r, w: d * r + side * w + np.array([0, -12, 0])
        X.mesh(cv).quad(p(120, 14), p(L.SAIL_R - 20, 14), p(L.SAIL_R - 20, 150), p(120, 150), tile=256, n=(0, -1, 0))
        for r in np.linspace(140, L.SAIL_R - 30, 8):
            bar(X.mesh(wd), p(r, 10), p(r, 154), 4, 4)
        bar(X.mesh(wd), p(120, 154), p(L.SAIL_R - 20, 154), 5, 5)
    ML.save_iqm('sails', X)


# ================================================================================================= lighthouse
def lighthouse():
    """red/white striped lighthouse: walk-in keeper's room (door +x), gallery deck at LIGHT_GAL, glass lamp room with a
    door onto the gallery (+x), red dome. Origin = floor centre."""
    st = TX.material('light_stripes', bands((236, 236, 232), (200, 40, 40)), shade=60)
    wh = TX.material('light_white', TL.solid((236, 236, 230), 2, 7, 64), shade=60)
    ir = TX.material('iron_dark', TL.metal((50, 54, 60)), 'lms', v=0.15)
    rd = TX.material('dome_red', TL.solid((200, 40, 40), 2, 9, 64), 'lms', v=0.12)
    gl = TX.material('lamp_glass', TL.solid((160, 200, 220), 2, 11, 64), 'glass', c='0.10 0.14 0.16')
    lp = TX.material('lamp_glow', TL.solid((255, 240, 180), 2, 13, 64), 'glow')
    X = Model()
    rows = [(L.LIGHT_R0, 0), (L.LIGHT_R0, 20), (L.LIGHT_R0 - 8, 32), (L.LIGHT_R1, L.LIGHT_GAL - 20), (L.LIGHT_R1, L.LIGHT_GAL)]
    door = [(-56, 0), (56, 0), (56, 150)] + [(56 * math.cos(t), 150 + 56 * math.sin(t)) for t in np.linspace(0, math.pi, 9)] + [(-56, 150)]
    win = [[(u - 18, z), (u + 18, z), (u + 18, z + 60), (u - 18, z + 60)] for (u, z) in ((170 * 1.5, 420), (-170 * 1.5, 620), (170 * 3.0, 300))]
    ML.carved_shell(X.mesh(st), X.mesh(wh), X.mesh(wh), rows, 32, 26, [door] + win, 0.0, 175.0, u_tiles=1,
                    vlen=200, close_top=False, close_bottom=False)
    # keeper's room ceiling / lamp-room floor
    disc(X.mesh(wh), L.LIGHT_R1 - 20, L.LIGHT_GAL - 20, up=False, n=32)
    # gallery deck (iron) with a kick plate, brackets underneath
    ring_disc(X.mesh(ir), 120, L.GAL_R, L.LIGHT_GAL, up=True, n=48, tile=256)
    ring_disc(X.mesh(ir), L.LIGHT_R1, L.GAL_R, L.LIGHT_GAL - 14, up=False, n=48, tile=256)
    revolve(X.mesh(ir), [(L.GAL_R, L.LIGHT_GAL - 14), (L.GAL_R, L.LIGHT_GAL + 10)], n=48)
    for k in range(12):
        a = 2 * math.pi * k / 12
        c, s = math.cos(a), math.sin(a)
        bar(X.mesh(ir), (c * L.LIGHT_R1, s * L.LIGHT_R1, L.LIGHT_GAL - 120), (c * (L.GAL_R - 10), s * (L.GAL_R - 10), L.LIGHT_GAL - 14), 6, 5)
    # lamp room: glass panes between 8 iron mullions, open between the two mullions facing +x (the door)
    z0, z1 = L.LIGHT_GAL, 1040
    for k in range(8):
        a0 = 2 * math.pi * (k + 0.5) / 8; a1 = 2 * math.pi * (k + 1.5) / 8
        p0 = (120 * math.cos(a0), 120 * math.sin(a0)); p1 = (120 * math.cos(a1), 120 * math.sin(a1))
        bar(X.mesh(ir), (p0[0], p0[1], z0), (p0[0], p0[1], z1), 5, 5)
        if k == 7: continue                                         # the door pane (+x)
        X.mesh(gl).quad((p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1), tile=128)
    revolve(X.mesh(lp), [(0, 930), (34, 940), (40, 970), (34, 1000), (0, 1010)], n=16)
    revolve(X.mesh(ir), [(26, z0), (26, 930)], n=12)
    revolve(X.mesh(rd), [(140, z1), (140, z1 + 12), (110, z1 + 50), (40, L.LAMP_TOP - 10), (0, L.LAMP_TOP)], n=32)
    sphere(X.mesh(ir), (0, 0, L.LAMP_TOP + 12), 14, nu=10, nv=6)
    revolve(X.mesh(ir), [(0, z1 - 1), (140, z1 - 1)], n=32)              # ceiling under the dome
    return ML.save('lighthouse', X)


# ================================================================================================= volcano
def volcano():
    """rock volcano: lower terrace (walkable), cone up to the rim (walkable ring), crater with lava at CRATER_Z"""
    rk = TX.material('volc_rock', rock(), shade=50)
    rd = TX.material('volc_red', rock(seed=37, base=(110, 60, 46)), shade=50)
    lv = TX.material('lava_m', lava(), 'glow', tcmod='turb 0 0.03 0 0.08')
    X = Model()

    def lump(a, r, z): return r + 6 * math.sin(7 * a + z * 0.02) + 4 * math.sin(13 * a + 1.1)
    revolve(X.mesh(rk), [(L.V1_R + 18, 0), (L.V1_R + 8, 30), (L.V1_R, L.V1_H - 20), (L.V1_R - 16, L.V1_H)], n=72, u_tiles=10, rfun=lump)
    ring_disc(X.mesh(rk), L.V2_R0, L.V1_R - 16, L.V1_H, up=True, n=72, tile=512)
    revolve(X.mesh(rd), [(L.V2_R0 + 10, L.V1_H), (L.V2_R0, L.V1_H + 20), (L.V2_R1 + 6, L.V2_H - 16), (L.V2_R1, L.V2_H)], n=72, u_tiles=8, rfun=lump)
    ring_disc(X.mesh(rd), L.CRATER_R, L.V2_R1, L.V2_H, up=True, n=48, tile=256)
    revolve(X.mesh(rd), [(L.CRATER_R, L.V2_H), (L.CRATER_R - 6, L.CRATER_Z)], n=48, inward=True)
    disc(X.mesh(lv), L.CRATER_R, L.CRATER_Z + 2, up=True, n=32, uvscale=200)
    # lava streaks down the cone (glowing ribbons on the surface)
    for k, a in enumerate((0.4, 2.1, 3.6, 5.0)):
        P = []
        for t in np.linspace(0, 1, 8):
            r = L.V2_R1 + (L.V2_R0 - L.V2_R1) * t + 3
            z = L.V2_H - (L.V2_H - L.V1_H) * t
            aa = a + 0.08 * math.sin(t * 6)
            P.append((r * math.cos(aa), r * math.sin(aa), z))
        tube(X.mesh(lv), P, np.linspace(14, 6, 8), nseg=6, caps=(False, False))
    return ML.save('volcano', X)


# ================================================================================================= clown
def clown():
    """giant clown head facing +y: walk in at the mouth (front, +y), out at the back; top hat with a flat walkable top"""
    sk = TX.material('clown_skin', TL.solid((246, 238, 230), 3, 15, 64), shade=80)
    rd = TX.material('clown_red', TL.solid((220, 30, 40), 2, 17, 64), 'lms', v=0.12)
    hr = TX.material('clown_hair', ML.fill(128, (240, 120, 30), 10, 19), shade=80)
    bk = TX.material('clown_black', TL.solid((26, 24, 28), 2, 21, 64), shade=60)
    yl = TX.material('clown_yellow', TL.solid((250, 210, 40), 2, 23, 64))
    wh = TX.material('clown_white', TL.solid((250, 250, 250), 2, 25, 64), 'lms', v=0.1)
    bl = TX.material('clown_blue', TL.solid((40, 90, 220), 2, 27, 64))
    X = Model()
    W, H = L.MOUTH_W, L.MOUTH_H
    rows = [(400, 0), (412, 40), (432, 250), (414, 470), (350, 610), (300, 690), (290, L.HEAD_H)]
    mouth = [(-W, 0), (W, 0), (W, H - 60)] + [(W * math.cos(t), H - 60 + 60 * math.sin(t)) for t in np.linspace(0, math.pi, 9)] + [(-W, H - 60)]
    back = [(u + math.pi * 420, z) for (u, z) in mouth]
    junk = Model()
    ML.carved_shell(X.mesh(sk), junk.mesh('a'), junk.mesh('b'), rows, 64, 30, [mouth, back], 90.0, 420.0, u_tiles=4, vlen=256,
                    close_top=False, close_bottom=False)
    disc(X.mesh(sk), 290, L.HEAD_H, up=True, n=48)
    # tunnel through the head (dark red throat)
    ty = 400
    for sx in (-1, 1):
        X.mesh(rd).quad((sx * W, -ty, 0), (sx * W, ty, 0), (sx * W, ty, H - 60), (sx * W, -ty, H - 60), tile=256, n=(-sx, 0, 0))
    P = np.zeros((9, 2, 3)); UV = np.zeros((9, 2, 2))
    for i, t in enumerate(np.linspace(0, math.pi, 9)):
        for j, y in enumerate((-ty, ty)): P[i, j] = (W * math.cos(t), y, H - 60 + 60 * math.sin(t)); UV[i, j] = (i / 8, y / 256)
    N = -grid_normals(P)
    if N[4, 0, 2] > 0: N = -N
    X.mesh(rd).grid(P, N, UV)
    # face (front = +y): lips round the mouth, nose, eyes, cheeks, eyebrows
    path = []
    for t in np.linspace(-0.1, math.pi + 0.1, 17):
        x = (W + 34) * math.cos(t); z = H - 40 + 74 * math.sin(t)
        r = 438 if z < 250 else 430
        y = math.sqrt(max(1.0, r * r - x * x))
        path.append((x, y - 6, z))
    tube(X.mesh(rd), path, 18, nseg=8)
    for sx in (-1, 1):
        tube(X.mesh(rd), [(sx * (W + 36), math.sqrt(438 ** 2 - (W + 36) ** 2) - 6, -2), (sx * (W + 34), math.sqrt(438 ** 2 - (W + 34) ** 2) - 6, H - 40)], 18, nseg=8)
    sphere(X.mesh(rd), (0, 446, 380), 74, nu=16, nv=10)
    for sx in (-1, 1):
        ellipsoid(X.mesh(wh), (sx * 140, 380, 500), 70, 30, 84, nu=14, nv=8)
        ellipsoid(X.mesh(bk), (sx * 132, 404, 486), 30, 14, 38, nu=10, nv=6)
        ellipsoid(X.mesh(bl), (sx * 140, 360, 610), 70, 16, 14, nu=10, nv=4, R=rot_axis((0, 1, 0), sx * 0.25))
        ellipsoid(X.mesh(rd), (sx * 250, 352, 340), 60, 14, 46, nu=10, nv=6, R=rot_z(-sx * 0.6))
        # hair puffs over the ears
        for (dx, dz, r) in ((0, 0, 130), (40, 120, 110), (-30, -110, 100)):
            sphere(X.mesh(hr), (sx * (420 + dx * 0.3), dz * 0.4, 470 + dz), r, nu=14, nv=8)
    # top hat: brim, crown with a yellow band and a daisy, flat top
    revolve(X.mesh(bk), [(0, L.HEAD_H), (300, L.HEAD_H), (304, L.HEAD_H + 10), (300, L.HEAD_H + 20), (L.HAT_R, L.HEAD_H + 20)], n=48)
    revolve(X.mesh(bk), [(L.HAT_R, L.HEAD_H + 20), (L.HAT_R, L.HAT_TOP)], n=48, u_tiles=4)
    revolve(X.mesh(yl), [(L.HAT_R + 3, L.HEAD_H + 30), (L.HAT_R + 3, L.HEAD_H + 90)], n=48)
    disc(X.mesh(bk), L.HAT_R, L.HAT_TOP, up=True, n=48)
    for k in range(8):
        a = 2 * math.pi * k / 8
        ellipsoid(X.mesh(wh), (math.cos(a) * 34, L.HAT_R + 8, L.HEAD_H + 60 + math.sin(a) * 34), 22, 6, 12, nu=8, nv=4, R=rot_axis((0, 1, 0), -a))
    sphere(X.mesh(yl), (0, L.HAT_R + 14, L.HEAD_H + 60), 16, nu=8, nv=5)
    return ML.save('clown', X)


# ================================================================================================= small pieces
def flag_pin(num):
    """flag pin standing in a cup: white/red pole 360 tall, numbered pennant waving (deform)"""
    pl = TX.material('pin_pole', bands((250, 250, 250), (220, 40, 40), k=1), shade=80)
    fl = TX.material(f'flag_{num}', flag_tex(num), shade=80, two=True, deform='wave 100 sin 0 4 0 1.1')
    X = Model()
    revolve(X.mesh(pl), [(6, 0), (6, 360), (0, 366)], n=10, vlen=360)
    P = np.zeros((4, 7, 3)); N = np.zeros_like(P); UV = np.zeros((4, 7, 2))
    for i in range(4):
        for j in range(7):
            u = j / 6; v = i / 3
            P[i, j] = (6 + 150 * u, 0, 356 - 100 * v); N[i, j] = (0, -1, 0); UV[i, j] = (u, v)
    X.mesh(fl).grid(P, N, UV)
    return ML.save(f'pin_{num}', X)


def flag_tex(num, n=256):
    c = ML.text_img(str(num), n, n, (240, 40, 40) if num != 19 else (30, 30, 30), (250, 250, 250), serif=False, size=170)
    return c


def golf_ball():
    """the giant golf ball on its tee (ball r 280, tee 80 tall)"""
    bl = TX.material('ball_dimples', dimples(), shade=89)
    tt = TX.material('tee_wood', TL.solid((240, 180, 60), 3, 29, 64), 'lms', v=0.08)
    X = Model()
    revolve(X.mesh(tt), [(70, 0), (60, 10), (30, 30), (40, 60), (110, L.TEE_H - 8), (116, L.TEE_H)], n=24)
    sphere(X.mesh(bl), (0, 0, L.TEE_H - 10 + L.BALL_R), L.BALL_R, nu=40, nv=20, u1=6, v1=3)
    return ML.save('golf_ball', X)


def loop():
    """steel loop-the-loop over hole 5: two rails along a helix (ends offset +-70 in y), sleepers, A-frame supports
    standing outside the lane rails; the loop is open at the bottom. Origin = floor centre."""
    st = TX.material('steel', TL.metal((200, 206, 212)), 'lms', v=0.25)
    rd = TX.material('loop_red', TL.solid((220, 40, 40), 2, 31, 64), 'lms', v=0.12)
    X = Model()
    R, zc = 300, 340
    ts = np.linspace(math.radians(-70), math.radians(250), 48)
    for off in (-36, 36):
        P = [(R * math.cos(t), (t - math.radians(90)) / math.pi * 70 + off, zc + R * math.sin(t)) for t in ts]
        tube(X.mesh(st), P, 8, nseg=6)
    for t in ts[::3]:
        y0 = (t - math.radians(90)) / math.pi * 70
        bar(X.mesh(rd), (R * math.cos(t), y0 - 44, zc + R * math.sin(t)), (R * math.cos(t), y0 + 44, zc + R * math.sin(t)), 5, 4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar(X.mesh(rd), (sx * 330, sy * 250, 0), (sx * 300, sy * 60, zc), 12, 6)
        bar(X.mesh(rd), (sx * 300, -60, zc), (sx * 300, 60, zc), 10, 6)
    return ML.save('loop', X)


def hedge(length, name):
    """trimmed hedge block along x (length), 160 deep, 320 tall, bumpy; origin floor centre"""
    lf = TX.material('hedge', leaves(), shade=80)
    X = Model()
    bump = lambda x, y, z, n: 6 * math.sin(x * 0.05) * math.sin(z * 0.07) + 4 * math.sin(y * 0.09 + z * 0.03)
    rbox(X.mesh(lf), (-length / 2, -80, 0), (length / 2, 80, 320), r=40, k=3, tile=256, inflate=bump, faces='nsewt')
    return ML.save(name, X)


def bench():
    """park bench 400 long (along x), seat 84, back 180; origin floor centre"""
    wd = TX.material('bench_wood', TL.planks((170, 110, 60), n_planks=4), shade=40)
    ir = TX.material('iron_dark', TL.metal((50, 54, 60)), 'lms', v=0.15)
    X = Model()
    for k in range(3):
        rbox(X.mesh(wd), (-200, -60 + k * 40, 76), (200, -30 + k * 40, 86), r=3, k=1, tile=128)
    for k in range(2):
        z = 120 + k * 40
        rbox(X.mesh(wd), (-200, 54, z), (200, 62, z + 26), r=3, k=1, tile=128)
    for sx in (-1, 1):
        x = sx * 170
        bar(X.mesh(ir), (x, -56, 0), (x, -56, 76), 5, 6); bar(X.mesh(ir), (x, 56, 0), (x, 58, 180), 5, 6)
        bar(X.mesh(ir), (x, -60, 76), (x, 60, 76), 5, 6)
    return ML.save('bench', X)


def buggy():
    """golf buggy (white body, green canopy on posts, black wheels) ~520 long, faces +x; origin floor centre"""
    wh = TX.material('buggy_white', TL.solid((240, 240, 236), 2, 33, 64), 'lms', v=0.12)
    gr = TX.material('buggy_green', TL.solid((40, 120, 70), 2, 35, 64))
    bk = TX.material('tyre', TL.solid((26, 26, 28), 2, 37, 64))
    se = TX.material('buggy_seat', TL.solid((140, 40, 40), 3, 39, 64))
    X = Model()
    rbox(X.mesh(wh), (-260, -130, 50), (260, 130, 150), r=30, k=3, tile=256)
    rbox(X.mesh(wh), (110, -130, 150), (260, 130, 200), r=30, k=3, tile=256)
    rbox(X.mesh(se), (-120, -120, 150), (40, 120, 190), r=14, k=2, tile=128)
    rbox(X.mesh(se), (-140, -120, 190), (-110, 120, 290), r=10, k=2, tile=128)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m = Mesh(); revolve(m, [(0, -24), (52, -24), (56, 0), (52, 24), (0, 24)], n=16)
            X.mesh(bk).add(m, rot_axis((1, 0, 0), math.pi / 2), (sx * 170, sy * 132, 54))
            bar(X.mesh(wh), (sx * 150, sy * 120, 150), (sx * 140, sy * 120, 420), 6, 6)
    rbox(X.mesh(gr), (-200, -140, 420), (200, 140, 440), r=8, k=2, tile=256)
    bar(X.mesh(bk), (60, 0, 200), (40, 0, 260), 4, 6)
    m = Mesh(); revolve(m, [(0, -4), (34, -4), (34, 4), (0, 4)], n=12)
    X.mesh(bk).add(m, rot_axis((0, 1, 0), 0.6), (34, 0, 266))
    return ML.save('buggy', X)


def counter():
    """clubhouse counter along x (600 long, 160 deep, 150 tall) with a till and a ball dispenser"""
    wd = TX.material('counter_wood', TL.planks((120, 80, 50), n_planks=6, vertical=True), shade=30)
    tp = TX.material('counter_top', TL.solid((230, 226, 214), 3, 41, 64), 'lms', v=0.08)
    bk = TX.material('till', TL.solid((40, 40, 44), 2, 43, 64))
    bl = TX.material('ball_dimples', dimples(), shade=89)
    X = Model()
    rbox(X.mesh(wd), (-300, -80, 0), (300, 80, 140), r=4, k=1, tile=128)
    rbox(X.mesh(tp), (-310, -90, 140), (310, 90, 150), r=3, k=1, tile=256)
    rbox(X.mesh(bk), (100, -40, 150), (180, 30, 200), r=4, k=1)
    for k in range(10):
        sphere(X.mesh(bl), (-220 + (k % 5) * 22, -30 + (k // 5) * 22, 160), 10, nu=8, nv=5)
    return ML.save('counter', X)


def putter_rack():
    """rack of putters leaning on a wall (rack along x 360, putters 260 long); origin floor centre, wall at +y"""
    wd = TX.material('counter_wood', TL.planks((120, 80, 50), n_planks=6, vertical=True), shade=30)
    st = TX.material('steel', TL.metal((200, 206, 212)), 'lms', v=0.25)
    rb = TX.material('grip', TL.solid((30, 30, 34), 2, 45, 64))
    X = Model()
    rbox(X.mesh(wd), (-180, -40, 0), (180, 40, 30), r=3, k=1)
    rbox(X.mesh(wd), (-180, 28, 200), (180, 40, 230), r=3, k=1)
    for k in range(9):
        x = -150 + k * 37
        bar(X.mesh(st), (x, -20, 30), (x, 30, 260), 3, 5)
        bar(X.mesh(rb), (x, 24, 214), (x, 32, 270), 5, 5)
        rbox(X.mesh(st), (x - 22, -34, 26), (x + 4, -14, 40), r=2, k=1)
    return ML.save('putter_rack', X)


def umbrella_table():
    """roof terrace table with a striped parasol (h 420, r 260); origin floor centre"""
    wh = TX.material('table_white', TL.solid((240, 240, 236), 2, 47, 64), 'lms', v=0.08)
    cv = TX.material('parasol_g', TL.stripes((40, 140, 80), (246, 242, 230), n_stripes=2), shade=80)
    X = Model()
    revolve(X.mesh(wh), [(60, 0), (50, 8), (12, 20), (12, 110), (110, 112), (110, 122), (0, 124)], n=24)
    revolve(X.mesh(wh), [(8, 122), (8, 420)], n=8)
    revolve(X.mesh(cv), [(260, 350), (130, 400), (0, 424)], n=32, u_tiles=8)
    revolve(X.mesh(cv), [(0, 418), (130, 394), (256, 346)], n=32, u_tiles=8)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        c, s = math.cos(a), math.sin(a)
        rbox(X.mesh(wh), (c * 170 - 40, s * 170 - 40, 0), (c * 170 + 40, s * 170 + 40, 70), r=10, k=2)
    return ML.save('umbrella_table', X)


def ball_pile(name, r, seed):
    """a heap of lost golf balls (cavern), radius r; origin floor centre"""
    bl = TX.material('ball_dimples', dimples(), shade=89)
    X = Model()
    rng = np.random.default_rng(seed)
    for k in range(60):
        a = rng.uniform(0, 2 * math.pi); d = r * math.sqrt(rng.uniform(0, 1))
        h = (1 - (d / r) ** 2) * r * 0.5
        sphere(X.mesh(bl), (d * math.cos(a), d * math.sin(a), 20 + h * rng.uniform(0.6, 1.0)), 22, nu=8, nv=5)
    return ML.save(name, X)


def make_all():
    windmill(); sails(); lighthouse(); volcano(); clown(); golf_ball(); loop()
    for n in (1, 2, 3, 4, 5, 6, 19): flag_pin(n)
    hedge(1024, 'hedge_long'); hedge(512, 'hedge_short')
    bench(); buggy(); counter(); putter_rack(); umbrella_table()
    ball_pile('balls_big', 200, 1); ball_pile('balls_small', 120, 2)
