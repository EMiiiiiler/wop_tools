"""PadClock Tower - textures (brush + model) and every custom MD3/IQM.

    import pc_models as PM; PM.textures(TX); PM.models(TX)
All models are original procedural meshes (meshlib); collision shapes live in COLL (model space, for K.custom/K.prop).
"""
import math
import numpy as np
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, prism, tube, ellipsoid

# palette: warm brass, dark iron, smoked oak, red brick, cream dial
BRASS = (196, 152, 64); BRASS_D = (140, 102, 40); IRON = (62, 64, 70); OAK = (104, 70, 44); OAK_L = (150, 106, 66)
BRICK = (128, 62, 46); MORTAR = (170, 150, 128); CREAM = (244, 228, 188); RED = (150, 40, 34)

R_ZY = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)     # model z axis -> -y (gear faces north/south)
R_ZYP = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)    # model z axis -> +y (faces into the room from a south wall)
R_ZX = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)     # model z axis -> +x (gear faces east/west)

COLL = {}           # name -> dict(boxes=[(mn, mx)], cyls=[(cx, cy, r, z0, z1)])
M_ = {}             # material key -> model shader


# ------------------------------------------------------------------------------------------------ textures
def textures(TX):
    TX.add('oak', TL.planks(OAK, n_planks=6, gap=(50, 32, 20), grain=12), steps='woodsteps')
    TX.add('oak_l', TL.planks(OAK_L, n_planks=4, gap=(80, 54, 32), grain=8, vertical=True), steps='woodsteps')
    TX.add('brick', TL.bricks(BRICK, MORTAR, rows=8, cols=4, vary=20))
    TX.add('stone', TL.tiles((120, 112, 104), (70, 64, 60), cols=4, rows=4, offset=0.5, grout_w=0.03, vary=10))
    TX.add('floor0', TL.checker((150, 138, 120), (70, 60, 52), n_tiles=4, grout=(40, 36, 32)))
    TX.add('brass', TL.metal(BRASS))
    TX.add('iron', TL.metal(IRON, brushed=False))
    TX.add('stripe', TL.stripes((40, 40, 44), (220, 170, 40), n_stripes=8, vertical=False), check_tile=False)
    TX.add('dialglass', TL.solid((250, 236, 200), 2, 7, 64), 'glass', rgb='0.18 0.16 0.10', shadow=False)
    TX.kit_defaults(pad_rgb=(255, 190, 70))


def gear_face_img(n=512, base=BRASS, holes=6, hole_r=0.085, ring=0.3):
    """brass gear face: lightening holes on a ring, a scribed rim line, hub ring. Centre of the gear = image corner
    (rolled by n/2), so prism()'s planar UVs (u = x / 2R) put the pattern round the model origin."""
    x, y = ML.xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = TL.metal(base, n=n).astype(np.float32)
    for k in range(holes):
        t = 2 * math.pi * k / holes
        h = np.hypot(dx - ring * math.cos(t), dy - ring * math.sin(t))
        c = np.where((h < hole_r)[..., None], ML.C((26, 20, 14)), c)
        c = np.where(((h >= hole_r) & (h < hole_r + 0.012))[..., None], ML.C(BRASS_D), c)
    for r0 in (0.43, 0.12):
        c = np.where((np.abs(rr - r0) < 0.006)[..., None], ML.C(BRASS_D), c)
    c = np.where((rr < 0.06)[..., None], ML.C(IRON), c)
    return np.roll(np.roll(c, n // 2, 0), n // 2, 1)


def dial_img(n=1024):
    """the back-lit opal dial: cream glass, minute ticks, bold hour bars (no numerals: seen from inside they would
    read mirrored), a brass chapter ring"""
    x, y = ML.xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy) * 2; a = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    c = np.zeros((n, n, 3), np.float32) + ML.C(CREAM) + ML.N3(n, 6, 3, 6)
    c = c * (1.0 - 0.18 * np.clip(rr, 0, 1)[..., None] ** 2)          # glow brighter in the middle
    minute = (np.abs(((a + 3) % 6) - 3) < 0.35) & (rr > 0.84) & (rr < 0.92)
    hour = (np.abs(((a + 15) % 30) - 15) < 1.4) & (rr > 0.72) & (rr < 0.92)
    c = np.where((minute | hour)[..., None], ML.C((30, 24, 20)), c)
    c = np.where(((rr > 0.94) & (rr < 1.0))[..., None], ML.C(BRASS), c)
    c = np.where((np.abs(rr - 0.70) < 0.006)[..., None], ML.C((60, 50, 40)), c)
    return c


def cog_crate_img(n=256):
    c = TL.planks((150, 112, 70), n_planks=4, stagger=False, n=n).astype(np.float32)
    x, y = ML.xy(n)
    edge = (x < 0.07) | (x > 0.93) | (y < 0.07) | (y > 0.93)
    c = np.where(edge[..., None], ML.C((96, 64, 36)), c)
    # stencilled cog in the middle
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    cog = ((rr < 0.22 + 0.04 * (np.sin(a * 8) > 0)) & (rr > 0.09))
    return np.where(cog[..., None], ML.C((60, 40, 24)), c)


def mats(TX):
    """every model material, registered BEFORE any model is saved (late registrations draw black)"""
    M_['brass'] = TX.material('brass', TL.metal(BRASS), 'lms', shade=30, v=0.15)
    M_['brass_d'] = TX.material('brass_d', TL.metal(BRASS_D), shade=30)
    M_['iron'] = TX.material('iron', TL.metal(IRON, brushed=False), shade=30)
    M_['gear'] = TX.material('gear', gear_face_img(), shade=20)
    M_['gear_i'] = TX.material('gear_i', gear_face_img(base=(120, 122, 128), holes=5), shade=20)
    M_['oak'] = TX.material('oak', TL.planks(OAK, n_planks=5), shade=30)
    M_['oak_l'] = TX.material('oak_l', TL.planks(OAK_L, n_planks=4, vertical=True), shade=30)
    M_['bronze'] = TX.material('bronze', TL.metal((150, 100, 52)), 'lms', shade=80, v=0.2)
    M_['dial'] = TX.material('dial', dial_img(), 'glow')
    M_['hands'] = TX.material('hands', TL.solid((22, 20, 22), 3, 5, 64), shade=30)
    M_['red'] = TX.material('red', TL.tiles(RED, (100, 26, 22), cols=6, rows=10, offset=0.5), shade=30)
    M_['cream'] = TX.material('cream', TL.solid((232, 214, 176), 4, 9, 128), shade=30)
    M_['dark'] = TX.material('dark', TL.solid((14, 12, 12), 2, 11, 64), 'glow')
    M_['crate'] = TX.material('crate', cog_crate_img(), shade=30)
    M_['oilcan'] = TX.material('oilcan', TL.stripes((40, 90, 60), (30, 70, 46), n_stripes=12), 'lms', shade=80, v=0.1, lathe=True)
    M_['bird'] = TX.material('bird', TL.dots((176, 108, 52), (110, 64, 30), n_dots=6), shade=80)
    M_['beak'] = TX.material('beak', TL.solid((240, 180, 40), 2, 13, 64), shade=80)
    M_['spring'] = TX.material('spring', TL.metal((90, 96, 110)), 'lms', shade=80, v=0.2)
    # --- props round 2 (alive: lanterns, wall clocks, workbenches, hourglasses, webs ...)
    M_['flame'] = TX.material('flame', lantern_glass_img(), 'flicker', ph=0.3)
    M_['flame2'] = TX.material('flame2', lantern_glass_img(), 'flicker', ph=0.7, image='flame_m')
    M_['hglass'] = TX.material('hglass', TL.solid((200, 220, 230), 2, 17, 64), 'glass', c='0.10 0.11 0.12')
    M_['sand'] = TX.material('sand', TL.solid((222, 186, 120), 10, 19, 128), shade=80)
    _wc, _wa = cobweb_img(); M_['web'] = TX.material('web', _wc, 'alpha', alpha=_wa)
    M_['redmetal'] = TX.material('redmetal', TL.metal((170, 34, 30), brushed=False), 'lms', shade=30, v=0.12)
    M_['drawer'] = TX.material('drawer', drawer_img(), shade=30)
    M_['wood_barrel'] = TX.material('wood_barrel', TL.planks((126, 84, 48), n_planks=10, vertical=True), shade=80, lathe=True)
    M_['face_old'] = TX.material('face_old', dial_img(512) * 0.82, shade=30)


# ------------------------------------------------------------------------------------------------ gears
def gear_poly(R, teeth, depth=None, pointed=False):
    """2D gear outline (counter-clockwise): root circle R - depth, tips at R"""
    depth = depth or max(16.0, R * 0.09)
    pts = []
    for k in range(teeth):
        a0 = 2 * math.pi * k / teeth; da = 2 * math.pi / teeth
        if pointed:      # escape-wheel teeth: a ramp up and a sheer drop
            for (f, r) in ((0.0, R - depth), (0.75, R), (0.8, R - depth)):
                pts.append(((r) * math.cos(a0 + f * da), (r) * math.sin(a0 + f * da)))
        else:
            for (f, r) in ((0.0, R - depth), (0.12, R - depth), (0.22, R), (0.48, R), (0.58, R - depth)):
                pts.append(((r) * math.cos(a0 + f * da), (r) * math.sin(a0 + f * da)))
    return pts


def gear(X, R, teeth, t, face='gear', z0=0.0, hub=True, pointed=False, Rm=np.eye(3), off=(0, 0, 0)):
    """a gear disc (teeth, lightening-hole face texture, hub boss) centred on the z axis from z0 to z0 + t, then
    rotated by Rm (R_ZY / R_ZX for wall gears) and moved by off"""
    G = ML.Model()
    prism(G.mesh(M_[face]), gear_poly(R, teeth, pointed=pointed), z0, z0 + t, tile=2 * R)
    if hub:
        hr = max(20.0, R * 0.12)
        revolve(G.mesh(M_['iron']), [(hr, z0 - 10), (hr, z0 + t + 10)], n=16)
        disc(G.mesh(M_['iron']), hr, z0 + t + 10, up=True, n=16); disc(G.mesh(M_['iron']), hr, z0 - 10, up=False, n=16)
    X.add_model(G, Rm, off)
    return X


def wall_gear(name, R, teeth, axis, t=36):
    """rotating wall gear for K.rotating_model2: centred on its own axis (origin = axis centre)"""
    X = ML.Model()
    gear(X, R, teeth, t, z0=-t / 2, Rm=R_ZX if axis == 'x' else R_ZY)
    return ML.save(name, X)


def gear_stack(name, radii, step=32):
    """flat spare gears stacked into a 32u-step pyramid (players hop up; collision = cylinders)"""
    X = ML.Model()
    cyls = []
    for i, (r, n) in enumerate(radii):
        gear(X, r, n, step, face='gear' if i % 2 == 0 else 'gear_i', z0=i * step, hub=False)
        cyls.append((0, 0, r - 14, i * step, (i + 1) * step))
    revolve(X.mesh(M_['iron']), [(36, len(radii) * step), (36, len(radii) * step + 24)], n=16)
    disc(X.mesh(M_['iron']), 36, len(radii) * step + 24, up=True, n=16)
    COLL[name] = dict(cyls=cyls)
    return ML.save(name, X)


# ------------------------------------------------------------------------------------------------ big pieces
def pendulum(length=1400, bob_r=170):
    """rod + lens bob, pivot at the origin, hanging down -z; the bob faces east/west so it swings north/south.
    IQM: far beyond the MD3 +-512 limit."""
    X = ML.Model()
    tube(X.mesh(M_['brass_d']), [(0, 0, 10), (0, 0, -length + bob_r * 0.6)], 9, nseg=10)
    tube(X.mesh(M_['iron']), [(-14, 0, 30), (14, 0, 30)], 30, nseg=14)                     # suspension block
    B = ML.Model()                                       # lens: two shallow domes back to back, axis z -> x
    revolve(B.mesh(M_['brass']), [(0.01, 34), (bob_r * 0.5, 30), (bob_r * 0.85, 18), (bob_r, 0)], n=36, inward=True)
    revolve(B.mesh(M_['brass']), [(bob_r, 0), (bob_r * 0.85, -18), (bob_r * 0.5, -30), (0.01, -34)], n=36, inward=True)
    X.add_model(B, R_ZX, (0, 0, -length))
    return ML.save_iqm('pendulum', X)


def anchor():
    """escapement anchor (rocks over the escape wheel on a func_pendulum): pivot at the origin"""
    X = ML.Model()
    tube(X.mesh(M_['iron']), [(0, -12, 0), (0, 12, 0)], 14, nseg=12)
    tube(X.mesh(M_['brass_d']), [(0, 0, 0), (0, 0, -60)], 7, nseg=8)
    for s in (1, -1):
        tube(X.mesh(M_['brass_d']), [(0, 0, -60), (0, s * 90, -70), (0, s * 112, -112)], 7, nseg=8)
    return ML.save('anchor', X)


MOVE = dict(hx=400, hy=320, h=304)          # movement block half sizes / height (deck plate goes on top)


def movement():
    """the clock movement: two pierced brass plates (north/south), four pillars, an iron core, barrel arbors
    sticking out. Origin at the bottom centre."""
    hx, hy, h = MOVE['hx'], MOVE['hy'], MOVE['h']
    X = ML.Model()
    for s in (1, -1):
        rbox(X.mesh(M_['brass']), (-hx, s * hy - (24 if s > 0 else 0), 0), (hx, s * hy + (0 if s > 0 else 24), h), r=10, k=2, tile=256)
    rbox(X.mesh(M_['iron']), (-hx + 30, -hy + 24, 20), (hx - 30, hy - 24, h - 20), r=6, k=2, tile=256)
    for sx in (1, -1):
        for sy in (1, -1):
            revolve(X.mesh(M_['brass_d']), [(30, 0), (34, 20), (26, 60), (26, h - 60), (34, h - 20), (30, h)], n=16,
                    cx=sx * (hx - 34), cy=sy * (hy - 48))
    for (cx, cz, r) in ((-200, 150, 40), (160, 110, 30), (40, 220, 24)):           # arbors through the plates
        tube(X.mesh(M_['iron']), [(cx, -hy - 40, cz), (cx, hy + 40, cz)], r, nseg=14)
    COLL['movement'] = dict(boxes=[((-hx, -hy, 0), (hx, hy, h))])
    return ML.save('movement', X)


BELL = [(205, 0), (200, 14), (186, 60), (172, 120), (155, 200), (132, 262), (116, 298), (102, 314), (98, 320)]


def bell():
    """the tower bell: bronze shell, flat crown you can stand on (Imperius), rod to the ceiling beam.
    Origin at the lip."""
    X = ML.Model()
    revolve(X.mesh(M_['bronze']), BELL, n=48, u_tiles=4)
    disc(X.mesh(M_['bronze']), 98, 320, up=True, n=48, uvscale=256)
    revolve(X.mesh(M_['bronze']), [(178, 0), (160, 140), (120, 250), (70, 290)], n=48, inward=True)
    disc(X.mesh(M_['bronze']), 70, 290, up=False, n=48)
    disc(X.mesh(M_['bronze']), 205, 0, up=False, n=48, r_in=178)
    revolve(X.mesh(M_['brass_d']), [(214, 40), (216, 52), (214, 64)], n=48)                       # sound bow ring
    tube(X.mesh(M_['iron']), [(0, 0, 250), (0, 0, 60)], 14, nseg=10)                               # clapper rod
    ellipsoid(X.mesh(M_['iron']), (0, 0, 40), 40, 40, 46, nu=14, nv=8)                            # clapper ball
    COLL['bell'] = dict(cyls=[(0, 0, 200, 0, 60), (0, 0, 180, 60, 140), (0, 0, 155, 140, 230), (0, 0, 122, 230, 300),
                              (0, 0, 98, 300, 320)])
    return ML.save('bell', X)


def bell_rod(h):
    X = ML.Model()
    tube(X.mesh(M_['iron']), [(0, 0, 0), (0, 0, h)], 12, nseg=10)
    rbox(X.mesh(M_['oak']), (-300, -40, h - 60), (300, 40, h), r=6, k=2, tile=128)                 # headstock beam
    COLL['bell_rod'] = dict(cyls=[(0, 0, 12, 0, h - 60)])
    return ML.save('bell_rod', X)


def dial(r=400, half=400):
    """dial assembly for the south wall window (x -half..half, z -half..half round its centre; faces +y into the
    room): glowing opal disc, brass bezel filling the square corners, centre boss"""
    X = ML.Model()
    n = 64
    D = X.mesh(M_['dial']); Bz = X.mesh(M_['brass'])
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = (r * math.cos(a0), 0, r * math.sin(a0)); p1 = (r * math.cos(a1), 0, r * math.sin(a1))
        D.poly([(0, 0, 0), p1, p0], (0, 1, 0), [(0.5, 0.5), (0.5 + 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1)),
                                                 (0.5 + 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0))])
        # bezel: from the circle out to the square, along the same rays
        q = []
        for a in (a0, a1):
            c, s = math.cos(a), math.sin(a)
            m = half / max(abs(c), abs(s))
            q.append((m * c, 2, m * s))
        Bz.poly([(p0[0], 2, p0[2]), (p1[0], 2, p1[2]), q[1], q[0]], (0, 1, 0),
                [(p0[0] / 256, -p0[2] / 256), (p1[0] / 256, -p1[2] / 256), (q[1][0] / 256, -q[1][2] / 256), (q[0][0] / 256, -q[0][2] / 256)])
    G = ML.Model()                                                              # chapter ring lip
    revolve(G.mesh(M_['brass']), [(r + 6, 0), (r + 10, 10), (r - 2, 22), (r - 12, 14)], n=n)
    X.add_model(G, R_ZYP, (0, 0, 0))
    B = ML.Model()
    revolve(B.mesh(M_['iron']), [(40, 0), (40, 30), (24, 44), (0.01, 48)], n=24)
    X.add_model(B, R_ZYP, (0, 0, 0))
    return ML.save('dial', X)


def hand(name, length, w, tail):
    """clock hand in the x-z plane pointing +z, pivot at the origin (rotates about y on a func_rotating)"""
    X = ML.Model()
    H = X.mesh(M_['hands'])
    pts = [(-w * 0.35, -tail), (w * 0.35, -tail), (w * 0.5, 0), (w * 0.3, length * 0.7), (w * 0.9, length * 0.78),
           (0, length), (-w * 0.9, length * 0.78), (-w * 0.3, length * 0.7), (-w * 0.5, 0)]
    for y, nrm in ((4, (0, 1, 0)), (-4, (0, -1, 0))):
        H.poly([(x, y, z) for x, z in pts], nrm, [(x / 128, -z / 128) for x, z in pts])
    for (a, b) in zip(pts, pts[1:] + pts[:1]):
        H.quad((a[0], -4, a[1]), (b[0], -4, b[1]), (b[0], 4, b[1]), (a[0], 4, a[1]), tile=64)
    return ML.save(name, X)


CUCKOO = dict(hw=176, d=208, h=300)        # half width, depth (from the wall), wall height


def cuckoo_house():
    """carved cuckoo house on the north ledge: oak walls, red shingle gable roof, a dark doorway at floor level
    (the secret entry) and the bird window above. Origin at the floor, back face at y = 0, front at y = -d."""
    hw, d, h = CUCKOO['hw'], CUCKOO['d'], CUCKOO['h']
    X = ML.Model()
    O = X.mesh(M_['oak_l'])
    dw, dh = 56, 136                    # doorway half width, height
    wy = -d
    # front wall with the doorway and a window (z 190..260)
    for (x0, x1, z0, z1) in ((-hw, -dw, 0, h), (dw, hw, 0, h), (-dw, dw, dh, 186), (-dw, dw, 262, h)):
        O.quad((x0, wy, z0), (x1, wy, z0), (x1, wy, z1), (x0, wy, z1), tile=128, n=(0, -1, 0))
    for s in (1, -1):                   # side walls
        O.quad((s * hw, wy, 0), (s * hw, 0, 0), (s * hw, 0, h), (s * hw, wy, h), tile=128, n=(s, 0, 0))
        X.mesh(M_['oak_l']).poly([(s * hw, wy, h), (s * hw, 0, h), (s * hw, -d / 2, h + 150)], (s, 0, 0),
                                 [(0, 0), (d / 128, 0), (d / 256, -150 / 128)])
    # dark interior seen through the doorway and window
    Dk = X.mesh(M_['dark'])
    Dk.quad((-dw, wy + 60, 0), (dw, wy + 60, 0), (dw, wy + 60, dh), (-dw, wy + 60, dh), n=(0, -1, 0))
    Dk.quad((-dw, wy + 30, 186), (dw, wy + 30, 186), (dw, wy + 30, 262), (-dw, wy + 30, 262), n=(0, -1, 0))
    for s in (1, -1):
        Dk.quad((s * dw, wy, 0), (s * dw, wy + 60, 0), (s * dw, wy + 60, dh), (s * dw, wy, dh), n=(-s, 0, 0))
    Dk.quad((-dw, wy, dh), (dw, wy, dh), (dw, wy + 60, dh), (-dw, wy + 60, dh), n=(0, 0, -1))
    # roof slopes (overhang 30)
    Rf = X.mesh(M_['red'])
    for s in (1, -1):
        a = (s * (hw + 30), wy - 30, h - 20); b = (s * (hw + 30), 0, h - 20); c = (0, 0, h + 162); e = (0, wy - 30, h + 162)
        Rf.quad(a, b, c, e, tile=128)
    # carved trim: balcony shelf under the window, two pine-cone weights hanging on chains
    rbox(X.mesh(M_['oak']), (-90, wy - 40, 176), (90, wy, 190), r=4, k=2, tile=64)
    for s in (1, -1):
        tube(X.mesh(M_['iron']), [(s * 120, wy - 16, 176), (s * 120, wy - 16, 70)], 3, nseg=6)
        ellipsoid(X.mesh(M_['brass_d']), (s * 120, wy - 16, 46), 16, 16, 30, nu=10, nv=6)
    COLL['cuckoo'] = dict(boxes=[((-hw, wy, 0), (-dw, 0, h)), ((dw, wy, 0), (hw, 0, h)), ((-dw, wy + 60, 0), (dw, 0, h)),
                                 ((-dw, wy, dh), (dw, wy + 60, h))])
    return ML.save('cuckoo', X)


def cuckoo_bird():
    """the bird that pops out of the window (func_door model2): faces -y, origin at its belly"""
    X = ML.Model()
    ellipsoid(X.mesh(M_['bird']), (0, 0, 20), 22, 34, 20, nu=14, nv=8)
    ellipsoid(X.mesh(M_['bird']), (0, -30, 40), 15, 15, 15, nu=12, nv=7)
    tube(X.mesh(M_['beak']), [(0, -42, 42), (0, -62, 40)], [6, 0.5], nseg=8)
    for s in (1, -1):
        ellipsoid(X.mesh(M_['bird']), (s * 20, 8, 22), 6, 24, 12, nu=8, nv=5)
    tube(X.mesh(M_['oak']), [(0, 30, 6), (0, -8, 6)], 4, nseg=6)                 # perch stick
    return ML.save('bird', X)


BARREL = dict(r=300, t=24, h=400, door=(-22.5, 22.5), door_h=136)


def barrel():
    """the mainspring barrel (walk-in drum on the ground floor): brass shell with teeth round the top rim, a door slot
    facing +x, iron arbor inside with the coiled spring round it. Origin at the floor centre."""
    r, t, h = BARREL['r'], BARREL['t'], BARREL['h']
    d0, d1 = BARREL['door']; dh = BARREL['door_h']
    X = ML.Model()
    B = X.mesh(M_['brass']); Bi = X.mesh(M_['brass_d'])
    revolve(B, [(r, 0), (r, h)], n=40, a0=d1, a1=360 + d0, u_tiles=6)
    revolve(Bi, [(r - t, 0), (r - t, h - 16)], n=40, a0=d1, a1=360 + d0, inward=True, u_tiles=6)
    revolve(B, [(r, dh), (r, h)], n=4, a0=d0, a1=d1)                                      # lintel outer face
    revolve(Bi, [(r - t, dh), (r - t, h - 16)], n=4, a0=d0, a1=d1, inward=True)
    for a in (d0, d1):                                                                    # door jambs
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        B.quad(((r - t) * c, (r - t) * s, 0), (r * c, r * s, 0), (r * c, r * s, dh), ((r - t) * c, (r - t) * s, dh), tile=64)
    ar = [math.radians(a) for a in np.linspace(d0, d1, 5)]
    for a0, a1 in zip(ar, ar[1:]):                                                        # lintel underside
        B.quad(((r - t) * math.cos(a0), (r - t) * math.sin(a0), dh), (r * math.cos(a0), r * math.sin(a0), dh),
               (r * math.cos(a1), r * math.sin(a1), dh), ((r - t) * math.cos(a1), (r - t) * math.sin(a1), dh), tile=64,
               n=(0, 0, -1))
    # lid (walkable top) with gear teeth round the rim
    G = ML.Model()
    gear(G, r + 26, 48, 16, z0=h - 16, hub=False)
    X.add_model(G)
    revolve(X.mesh(M_['iron']), [(46, 0), (46, h - 16)], n=16)                             # arbor
    # mainspring: a flat spiral ribbon on an iron plate, 16 tall (a step; collision = one weapclip cylinder)
    S = X.mesh(M_['spring'])
    pts = [((60 + 9 * a / (2 * math.pi) * 10) * math.cos(a), (60 + 9 * a / (2 * math.pi) * 10) * math.sin(a)) for a in np.linspace(0, 2 * math.pi * 1.6, 70)]
    for p, q in zip(pts, pts[1:]):
        S.quad((p[0], p[1], 0), (q[0], q[1], 0), (q[0], q[1], 16), (p[0], p[1], 16), tile=64)
        S.quad((q[0], q[1], 0), (p[0], p[1], 0), (p[0], p[1], 16), (q[0], q[1], 16), tile=64)
    disc(X.mesh(M_['iron']), 205, 15.5, up=True, n=32, uvscale=256)          # spring plate under the coil
    return ML.save('barrel', X)


def crate(name, w, dz):
    X = ML.Model()
    rbox(X.mesh(M_['crate']), (-w / 2, -w / 2, 0), (w / 2, w / 2, dz), r=4, k=2, tile=w)
    COLL[name] = dict(boxes=[((-w / 2 + 2, -w / 2 + 2, 0), (w / 2 - 2, w / 2 - 2, dz - 2))])
    return ML.save(name, X)


def crate_stack(name):
    X = ML.Model()
    B = [((-64, -64, 0), (64, 64, 128)), ((64, -48, 0), (160, 48, 96)), ((-48, -48, 128), (48, 48, 224))]
    for mn, mx in B:
        rbox(X.mesh(M_['crate']), mn, mx, r=4, k=2, tile=mx[0] - mn[0])
    COLL[name] = dict(boxes=[((a[0] + 2, a[1] + 2, a[2]), (b[0] - 2, b[1] - 2, b[2] - 2)) for a, b in B])
    return ML.save(name, X)


def oilcan():
    """big oil can: stepped body, domed shoulder, long spout - cover"""
    X = ML.Model()
    revolve(X.mesh(M_['oilcan']), [(90, 0), (96, 6), (96, 150), (90, 160)], n=32, u_tiles=1, vlen=170)
    revolve(X.mesh(M_['brass']), [(90, 160), (70, 190), (30, 206), (30, 236), (34, 240), (0.01, 242)], n=32)
    tube(X.mesh(M_['brass']), [(40, 0, 200), (110, 0, 240), (190, 0, 300)], [16, 10, 5], nseg=10)
    disc(X.mesh(M_['oilcan']), 96, 0, up=False, n=32)
    COLL['oilcan'] = dict(cyls=[(0, 0, 92, 0, 200)])
    return ML.save('oilcan', X)


def screw():
    """giant screw lying on its side: thread ribbon + head - low cover you can hop over"""
    X = ML.Model()
    L = 420; r = 34
    pts = [(x, r * 1.3 * math.cos(x / 22), r * 1.3 * math.sin(x / 22) + 50) for x in np.linspace(-L / 2, L / 2 - 40, 120)]
    tube(X.mesh(M_['spring']), [(-L / 2, 0, 50), (L / 2 - 40, 0, 50)], r, nseg=16)
    tube(X.mesh(M_['spring']), pts, 7, nseg=6)
    H = ML.Model()
    revolve(H.mesh(M_['spring']), [(0.01, -20), (64, -20), (64, 4), (50, 16), (0.01, 20)], n=24)
    X.add_model(H, R_ZX, (L / 2 - 20, 0, 64))
    COLL['screw'] = dict(boxes=[((-L / 2, -44, 0), (L / 2, 44, 96))])
    return ML.save('screw', X)


def chain(name, length, link=40):
    """hanging chain of oval links (decor, no collision) from z 0 down to -length"""
    X = ML.Model()
    k = 0
    z = 0.0
    while z > -length:
        a = 0 if k % 2 == 0 else math.pi / 2
        pts = [(14 * math.cos(t) * math.cos(a), 14 * math.cos(t) * math.sin(a), z - link / 2 + (link / 2) * math.sin(t))
               for t in np.linspace(0, 2 * math.pi, 13)]
        tube(X.mesh(M_['iron']), pts, 4, nseg=6, caps=(False, False))
        z -= link * 0.8; k += 1
    return ML.save_iqm(name, X) if length > 900 else ML.save(name, X)



# ------------------------------------------------------------------------------------------------ props round 2
def lantern_glass_img(n=128):
    """warm lantern glass: bright core fading to amber at the edges (flicker kind: rgbGen wave noise)"""
    x, y = ML.xy(n)
    r = np.hypot((x - 0.5) * 1.6, (y - 0.62) * 1.0)
    c = np.zeros((n, n, 3), np.float32)
    core = np.clip(1.15 - r * 1.3, 0, 1)[..., None]
    return np.clip(ML.C((150, 70, 16)) * 0.9 + ML.C((255, 220, 140)) * core, 0, 255)


def cobweb_img(n=256):
    """corner cobweb on a transparent ground: radial threads from the corner (0, 0) and sagging rings"""
    x, y = ML.xy(n)
    r = np.hypot(x, y); a = np.arctan2(y, x)
    k = 9
    radial = np.abs(((a / (math.pi / 2)) * k + 0.5) % 1 - 0.5) < 0.035 / np.maximum(r, 0.05)
    ring = np.zeros_like(r, bool)
    for r0 in np.linspace(0.12, 0.95, 8):
        sag = r0 * (1 + 0.06 * np.sin(((a / (math.pi / 2)) * k) * math.pi) ** 2)
        ring |= np.abs(r - sag) < 0.006
    m = (radial | ring) & (r < 0.98)
    c = np.zeros((n, n, 3), np.float32) + ML.C((225, 225, 230))
    alpha = np.where(m, 255, 0).astype(np.uint8)
    return c, alpha


def drawer_img(n=256):
    """bench front: three drawers with brass pulls on dark oak"""
    c = TL.planks(OAK, n_planks=3, stagger=False, n=n).astype(np.float32)
    x, y = ML.xy(n)
    for k in range(3):
        y0 = k / 3
        edge = (np.abs(y - y0) < 0.012) | (np.abs(y - y0 - 1 / 3) < 0.012)
        c = np.where(edge[..., None], ML.C((40, 26, 16)), c)
        pull = (np.abs(x - 0.5) < 0.09) & (np.abs(y - (y0 + 1 / 6)) < 0.025)
        c = np.where(pull[..., None], ML.C(BRASS), c)
    return c


def lantern(name, chain_len):
    """hanging oil lantern: iron cap + ring, four posts, flickering glass, iron base; the chain runs up chain_len to
    the ceiling. Origin at the TOP of the chain (the ceiling surface): everything hangs below z 0."""
    X = ML.Model()
    zb = -chain_len - 120                         # lantern base
    I = X.mesh(M_['iron'])
    revolve(I, [(34, zb), (34, zb + 10), (26, zb + 14)], n=8)
    disc(I, 34, zb, up=False, n=8)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tube(I, [(28 * math.cos(a), 28 * math.sin(a), zb + 10), (28 * math.cos(a), 28 * math.sin(a), zb + 90)], 3, nseg=6)
    revolve(X.mesh(M_['flame']), [(22, zb + 12), (26, zb + 50), (22, zb + 90)], n=8)
    revolve(I, [(36, zb + 88), (30, zb + 104), (12, zb + 114), (0.01, zb + 118)], n=8)
    tube(I, [(0, -10, zb + 118), (0, 0, zb + 128), (0, 10, zb + 118)], 3, nseg=6)
    z = zb + 120.0; k = 0
    while z < -6:                                 # chain links up to the ceiling
        a = 0 if k % 2 == 0 else math.pi / 2
        L = min(26.0, -z)
        pts = [(8 * math.cos(t) * math.cos(a), 8 * math.cos(t) * math.sin(a), z + L / 2 + (L / 2) * math.sin(t))
               for t in np.linspace(0, 2 * math.pi, 9)]
        tube(I, pts, 2, nseg=5, caps=(False, False))
        z += 20; k += 1
    rbox(I, (-20, -20, -6), (20, 20, 0), r=2, k=1, tile=64)                       # ceiling plate
    return ML.save(name, X)


def wall_clock(name, r=96):
    """round wall clock (dial faces -y, back on the wall at y = 0): brass rim, glowing dial; the hands are separate
    func_rotating models. Origin at the dial centre on the wall."""
    X = ML.Model()
    D = X.mesh(M_['dial']); n = 40
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = (r * math.cos(a0), -22, r * math.sin(a0)); p1 = (r * math.cos(a1), -22, r * math.sin(a1))
        D.poly([(0, -22, 0), p0, p1], (0, -1, 0), [(0.5, 0.5), (0.5 - 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0)),
                                                    (0.5 - 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1))])
    G = ML.Model()                                # rim: a revolve round z, turned so z -> -y
    revolve(G.mesh(M_['brass']), [(r + 14, 0), (r + 14, 18), (r + 6, 26), (r - 2, 22)], n=n)
    disc(G.mesh(M_['oak']), r + 14, 0.5, up=False, n=n)
    X.add_model(G, R_ZY, (0, 0, 0))
    B = ML.Model()
    revolve(B.mesh(M_['iron']), [(10, 0), (10, 8), (0.01, 10)], n=12)
    X.add_model(B, R_ZY, (0, -22, 0))
    return ML.save(name, X)


def small_hand(name, length, w, axis):
    """little clock hand for a wall clock: in the x-z plane (axis y) or the y-z plane (axis x), pivot at the origin,
    drawn on both sides"""
    X = ML.Model()
    H = X.mesh(M_['hands'])
    pts = [(-w * 0.4, -length * 0.18), (w * 0.4, -length * 0.18), (w * 0.5, length * 0.75), (0, length), (-w * 0.5, length * 0.75)]
    uv = [(x / 64, -z / 64) for x, z in pts]
    P = (lambda u, s, z: (u, s, z)) if axis == 'y' else (lambda u, s, z: (s, u, z))
    front = [P(x, 2, z) for x, z in pts]
    back = [P(x, -2, z) for x, z in pts]
    nf = np.cross(np.subtract(front[1], front[0]), np.subtract(front[2], front[0])); nf = tuple(nf / np.linalg.norm(nf))
    H.poly(front, nf, uv)
    H.poly(back[::-1], tuple(-c for c in nf), uv[::-1])
    return ML.save(name, X)


def bench(name, w=320, d=144, h=112):
    """watchmaker's bench: drawer cabinet (front -y) under an overhanging oak top with an iron vice. Origin at the
    floor centre. Solid to the floor (no eye-level gap under it)."""
    X = ML.Model()
    O = X.mesh(M_['oak']); Dr = X.mesh(M_['drawer'])
    rbox(O, (-w / 2 + 8, -d / 2 + 8, 0), (w / 2 - 8, d / 2 - 8, h - 12), r=2, k=1, tile=128)
    for x0 in (-w / 2 + 8, 0):                    # two drawer stacks on the front face
        p = [(x0, -d / 2 + 7.5, 4), (x0 + w / 2 - 8, -d / 2 + 7.5, 4), (x0 + w / 2 - 8, -d / 2 + 7.5, h - 16), (x0, -d / 2 + 7.5, h - 16)]
        Dr.poly(p, (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(M_['oak_l']), (-w / 2, -d / 2, h - 12), (w / 2, d / 2, h), r=3, k=2, tile=128)
    rbox(X.mesh(M_['iron']), (w / 2 - 70, -d / 2 - 14, h), (w / 2 - 20, -d / 2 + 30, h + 30), r=3, k=1, tile=64)
    tube(X.mesh(M_['iron']), [(w / 2 - 45, -d / 2 - 30, h + 14), (w / 2 - 45, -d / 2 + 10, h + 14)], 5, nseg=8)
    COLL[name] = dict(boxes=[((-w / 2 + 4, -d / 2 + 4, 0), (w / 2 - 4, d / 2 - 4, h))])
    return ML.save(name, X)


def pocketwatch(name, r=60, upright=False):
    """pocket watch: brass case, glowing dial, crown and bow. Lying flat (dial up) or standing on its rim (dial -y,
    leaning on a little brass stand) as cover. Origin at the floor."""
    X = ML.Model()
    W = ML.Model()                                # built lying, dial up, case z 0..t
    t = max(10.0, r * 0.22)
    revolve(W.mesh(M_['brass']), [(r * 0.96, 0), (r, t * 0.3), (r, t * 0.8), (r * 0.94, t)], n=40)
    disc(W.mesh(M_['brass']), r * 0.96, 0, up=False, n=40)
    D = W.mesh(M_['dial']); n = 40
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = (r * 0.94 * math.cos(a0), r * 0.94 * math.sin(a0), t - 1); p1 = (r * 0.94 * math.cos(a1), r * 0.94 * math.sin(a1), t - 1)
        D.poly([(0, 0, t - 1), p0, p1], (0, 0, 1), [(0.5, 0.5), (0.5 + 0.47 * math.cos(a0), 0.5 - 0.47 * math.sin(a0)),
                                                   (0.5 + 0.47 * math.cos(a1), 0.5 - 0.47 * math.sin(a1))])
    hm = W.mesh(M_['hands'])                      # fixed hands (ten past ten)
    for (ang, L) in ((math.radians(50), r * 0.55), (math.radians(140), r * 0.75)):
        c, s = math.cos(ang), math.sin(ang)
        hm.poly([(-s * 2.5, c * 2.5, t + 0.5), (s * 2.5, -c * 2.5, t + 0.5), (c * L, s * L, t + 0.5)], (0, 0, 1),
                [(0, 0), (1, 0), (0.5, 1)])
    tube(W.mesh(M_['brass']), [(0, r, t / 2), (0, r * 1.18, t / 2)], r * 0.08, nseg=10)            # crown
    bow = [(r * 0.2 * math.cos(a), r * 1.2 + r * 0.2 * math.sin(a), t / 2) for a in np.linspace(math.pi, 2 * math.pi + math.pi, 17)]
    tube(W.mesh(M_['brass']), bow, r * 0.035, nseg=6, caps=(False, False))
    if upright:
        # stand it on its rim: rotate the lying watch about x by 80 degrees (dial towards -y, bow on top), lift onto a stand
        a = math.radians(80); Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        X.add_model(W, Rx, (0, 0, r + 4))
        rbox(X.mesh(M_['oak']), (-r * 0.7, -t * 0.4 - 8, 0), (r * 0.7, t * 1.6 + 8, 8), r=2, k=1, tile=64)
        COLL[name] = dict(boxes=[((-r * 0.9, -t * 0.5, 0), (r * 0.9, t * 1.5, r * 2))])
    else:
        X.add_model(W)
        COLL[name] = dict(cyls=[(0, 0, r * 0.95, 0, t)])
    return ML.save(name, X)


def hourglass(name, h=280, r=96):
    """big hourglass: oak end discs, four turned brass posts, glass bulbs, sand piled in the bottom bulb and a thin
    stream (cover; collision = one cylinder)"""
    X = ML.Model()
    for z0, z1 in ((0, 24), (h - 24, h)):
        revolve(X.mesh(M_['oak']), [(r, z0), (r + 6, (z0 + z1) / 2), (r, z1)], n=24)
        disc(X.mesh(M_['oak']), r, z1, up=True, n=24); disc(X.mesh(M_['oak']), r, z0, up=False, n=24)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        revolve(X.mesh(M_['brass']), [(7, 24), (11, 50), (7, 80), (9, h / 2), (7, h - 80), (11, h - 50), (7, h - 24)], n=8,
                cx=(r - 14) * math.cos(a), cy=(r - 14) * math.sin(a))
    g = r - 30
    prof = [(g * 0.5, 24), (g, 60), (g * 0.95, h / 2 - 40), (10, h / 2), (g * 0.95, h / 2 + 40), (g, h - 60), (g * 0.5, h - 24)]
    revolve(X.mesh(M_['hglass']), prof, n=20)
    revolve(X.mesh(M_['sand']), [(g * 0.6, 26), (g * 0.9, 52), (g * 0.6, 84), (0.01, 104)], n=20)          # bottom pile
    revolve(X.mesh(M_['sand']), [(0.01, h / 2 + 30), (g * 0.7, h / 2 + 52), (g * 0.88, h - 70), (g * 0.5, h - 30)], n=20, inward=True)
    tube(X.mesh(M_['sand']), [(0, 0, h / 2 + 10), (0, 0, 100)], 2.5, nseg=5)
    COLL[name] = dict(cyls=[(0, 0, r - 4, 0, h)])
    return ML.save(name, X)


def barrels(name):
    """three oil barrels (staves + iron hoops) huddled together, one smaller on top: cover"""
    X = ML.Model()
    spots = [(-60, -40, 0, 64, 150), (64, -30, 0, 64, 150), (0, 66, 0, 60, 140), (0, 0, 150, 52, 120)]
    cyls = []
    for (cx, cy, z0, r, h) in spots:
        revolve(X.mesh(M_['wood_barrel']), [(r * 0.86, z0), (r, z0 + h * 0.5), (r * 0.86, z0 + h)], n=20, cx=cx, cy=cy, u_tiles=2)
        D = ML.Model(); disc(D.mesh(M_['oak']), r * 0.86, h - 4, up=True, n=20); X.add_model(D, np.eye(3), (cx, cy, z0))
        for f in (0.14, 0.5, 0.86):
            rr = r * (0.86 + 0.14 * (1 - abs(f - 0.5) * 2)) + 1.5
            revolve(X.mesh(M_['iron']), [(rr, z0 + h * f - 5), (rr, z0 + h * f + 5)], n=20, cx=cx, cy=cy)
        cyls.append((cx, cy, r * 0.9, z0, z0 + h))
    COLL[name] = dict(cyls=cyls)
    return ML.save(name, X)


def toolbox(name):
    """red toolbox, lid open, with a big spanner lying across it. Origin floor centre."""
    X = ML.Model()
    w, d, h = 200, 96, 88
    rbox(X.mesh(M_['redmetal']), (-w / 2, -d / 2, 0), (w / 2, d / 2, h), r=4, k=2, tile=128)
    rbox(X.mesh(M_['redmetal']), (-w / 2, d / 2, h - 4), (w / 2, d / 2 + 10, h + 90), r=3, k=1, tile=128)        # open lid
    tube(X.mesh(M_['iron']), [(-60, 0, h), (-60, 0, h + 34), (60, 0, h + 34), (60, 0, h)], 5, nseg=8)            # handle
    sp = X.mesh(M_['spring'])                     # spanner
    rbox(sp, (-150, -60, h), (90, -40, h + 8), r=2, k=1, tile=64)
    revolve(sp, [(24, h), (24, h + 8)], n=14, cx=110, cy=-50)
    revolve(sp, [(20, h), (20, h + 8)], n=14, cx=-170, cy=-50)
    COLL[name] = dict(boxes=[((-w / 2, -d / 2, 0), (w / 2, d / 2, h))])
    return ML.save(name, X)


def big_spring(name, r=72, h=220, turns=8):
    """a huge coil spring standing on end: cover (collision cylinder)"""
    X = ML.Model()
    pts = [(r * math.cos(a), r * math.sin(a), 10 + (h - 20) * a / (2 * math.pi * turns)) for a in np.linspace(0, 2 * math.pi * turns, turns * 24)]
    tube(X.mesh(M_['spring']), pts, 10, nseg=8)
    revolve(X.mesh(M_['iron']), [(r + 12, 0), (r + 12, 10)], n=24); disc(X.mesh(M_['iron']), r + 12, 10, up=True, n=24)
    COLL[name] = dict(cyls=[(0, 0, r + 8, 0, h)])
    return ML.save(name, X)


def old_face(name, r=200):
    """a spare clock face from an older clock leaning against a wall (back towards +y): cover"""
    X = ML.Model()
    F = ML.Model()                                # flat disc dial up, z 0..14
    revolve(F.mesh(M_['brass_d']), [(r, 0), (r, 14)], n=40)
    disc(F.mesh(M_['brass_d']), r, 0, up=False, n=40)
    D = F.mesh(M_['face_old']); n = 40
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        D.poly([(0, 0, 14), (r * math.cos(a0), r * math.sin(a0), 14), (r * math.cos(a1), r * math.sin(a1), 14)], (0, 0, 1),
               [(0.5, 0.5), (0.5 + 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0)), (0.5 + 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1))])
    a = math.radians(75); Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    X.add_model(F, Rx, (0, 0, r * math.sin(math.radians(75))))
    COLL[name] = dict(boxes=[((-r * 0.8, -60, 0), (r * 0.8, 50, r * 1.7))])
    return ML.save(name, X)


def cobweb(name, s=180):
    """corner web: one alpha quad across a wall/ceiling corner (two-sided). Origin at the corner, web spans +x/+y/-z"""
    X = ML.Model()
    W = X.mesh(M_['web'])
    for tri in (((0, 0, 0), (s, 0, 0), (0, s, -s * 0.5)), ((0, 0, 0), (s * 0.9, 0, -s * 0.6), (0, s * 0.9, 0))):
        nn = np.cross(np.subtract(tri[1], tri[0]), np.subtract(tri[2], tri[0])); nn = tuple(nn / np.linalg.norm(nn))
        W.poly(list(tri), nn, [(0, 0), (1, 0), (0, 1)])
    return ML.save(name, X)


def hang_weight(name, chain_len, r=90, h=300):
    """big brass clock weight hanging on a chain (decor high in the wings; no collision). Origin at the ceiling."""
    X = ML.Model()
    zb = -chain_len - h
    revolve(X.mesh(M_['brass']), [(r * 0.8, zb), (r, zb + 20), (r, zb + h - 30), (r * 0.6, zb + h), (0.01, zb + h + 4)], n=24)
    disc(X.mesh(M_['brass']), r * 0.8, zb, up=False, n=24)
    tube(X.mesh(M_['iron']), [(0, -12, zb + h + 4), (0, 0, zb + h + 24), (0, 12, zb + h + 4)], 5, nseg=6)
    z = zb + h + 20.0; k = 0
    I = X.mesh(M_['iron'])
    while z < -6:
        a = 0 if k % 2 == 0 else math.pi / 2
        L = min(40.0, -z)
        pts = [(12 * math.cos(t) * math.cos(a), 12 * math.cos(t) * math.sin(a), z + L / 2 + (L / 2) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 9)]
        tube(I, pts, 3.5, nseg=5, caps=(False, False))
        z += 32; k += 1
    rbox(I, (-24, -24, -8), (24, 24, 0), r=2, k=1, tile=64)
    return ML.save(name, X)


def chimes(name, lengths=(820, 760, 700, 640, 580, 520), gap=72):
    """tubular chimes hanging from a ceiling joist (decor high over the chime house roof). Origin at the ceiling."""
    X = ML.Model()
    n = len(lengths); y0 = -gap * (n - 1) / 2
    rbox(X.mesh(M_['oak']), (-30, y0 - 50, -40), (30, -y0 + 50, 0), r=4, k=2, tile=128)
    for i, L in enumerate(lengths):
        y = y0 + i * gap
        tube(X.mesh(M_['iron']), [(0, y, -40), (0, y, -90)], 2, nseg=5)
        revolve(X.mesh(M_['brass']), [(16, -90 - L), (16, -90)], n=12, cx=0, cy=y)
    return ML.save(name, X)


def shaft(name, length, r=14):
    """leading-off rod from the movement to the dial: iron rod with bevel gears at both ends and a universal joint.
    Axis y, centred on the origin (IQM: longer than the MD3 +-512 limit)."""
    X = ML.Model()
    tube(X.mesh(M_['iron']), [(0, -length / 2, 0), (0, length / 2, 0)], r, nseg=12)
    for s in (1, -1):
        G = ML.Model(); gear(G, 70, 20, 20, z0=-10)
        X.add_model(G, R_ZY, (0, s * (length / 2 - 30), 0))
    for yy in (-length / 4, length / 4):
        tube(X.mesh(M_['brass_d']), [(0, yy - 20, 0), (0, yy + 20, 0)], r + 9, nseg=12)
    return ML.save_iqm(name, X)


def nest(name, r=150):
    """the cuckoo's nest: a ring of twig coils with three big speckled eggs in it (secret room centrepiece)"""
    X = ML.Model()
    rng = np.random.default_rng(7)
    for k in range(9):
        rr = r * (0.55 + 0.05 * k); zz = 10 + 7 * k - 0.4 * (k - 4) ** 2 * 3
        pts = [((rr + rng.uniform(-8, 8)) * math.cos(a), (rr + rng.uniform(-8, 8)) * math.sin(a), max(6.0, zz) + rng.uniform(-4, 4))
               for a in np.linspace(0, 2 * math.pi, 25)]
        pts[-1] = pts[0]
        tube(X.mesh(M_['oak']), pts, 7, nseg=6, caps=(False, False))
    disc(X.mesh(M_['oak']), r * 0.62, 8, up=True, n=20)
    for (x, y, a) in ((-30, -20, 0), (35, -10, 0), (0, 40, 0)):
        ellipsoid(X.mesh(M_['cream']), (x, y, 44), 28, 28, 38, nu=14, nv=8)
    COLL[name] = dict(cyls=[(0, 0, r * 0.9, 0, 40)])
    return ML.save(name, X)


# ------------------------------------------------------------------------------------------------ all models
def models(TX):
    mats(TX)
    wall_gear('gear_w', 420, 40, 'x'); wall_gear('gear_e', 420, 40, 'x')
    wall_gear('gear_s1', 380, 36, 'y'); wall_gear('gear_s2', 250, 24, 'y')
    wall_gear('gear_n1', 260, 26, 'y'); wall_gear('gear_n2', 190, 18, 'y')
    X = ML.Model(); gear(X, 150, 30, 24, z0=-12, pointed=True, Rm=R_ZX); ML.save('escape', X)
    X = ML.Model(); gear(X, 160, 32, 24, z0=-12, Rm=R_ZX); ML.save('train', X)
    gear_stack('gearstack', [(360, 36), (280, 28), (200, 20), (130, 14)])
    gear_stack('gearstack_s', [(240, 24), (160, 16), (100, 10)])
    pendulum(); anchor(); movement(); bell(); bell_rod(256); dial(); barrel()
    hand('hand_min', 340, 34, 70); hand('hand_hr', 230, 46, 50)
    cuckoo_house(); cuckoo_bird()
    crate('crate96', 96, 96); crate('crate128', 128, 128); crate_stack('crates')
    oilcan(); screw()
    # round 2
    for L in (60, 120, 200, 400, 640):
        lantern(f'lantern_{L}', L)
    wall_clock('wallclock')
    for ax in ('x', 'y'):
        small_hand(f'shand_m_{ax}', 78, 10, ax); small_hand(f'shand_h_{ax}', 54, 13, ax)
    wall_gear('gear_t1', 130, 16, 'y'); wall_gear('gear_t2', 90, 12, 'y'); wall_gear('gear_t3', 130, 16, 'x'); wall_gear('gear_t4', 90, 12, 'x')
    bench('bench'); pocketwatch('watch', 48); pocketwatch('bigwatch', 150, upright=True)
    hourglass('hourglass'); barrels('barrels'); toolbox('toolbox'); big_spring('bigspring')
    nest('nest'); old_face('oldface'); cobweb('cobweb'); hang_weight('weight_hang', 520); chimes('chimes'); shaft('shaft', 1140)
