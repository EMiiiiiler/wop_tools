"""Padman's Garage - the street: brush textures, model materials and MD3s for the front of the house and the street
(sectional panel doors, wall lanterns, facade trim, SUVs, neighbours' houses, roadworks barriers, cones, a pipe stack,
a skip bin, a letterbox). All art is original and procedural. Model space as in gr_models: z = 0 on the ground,
front = -y unless a docstring says otherwise. Scale 1 m = 600u.
"""
import math
import numpy as np
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, tube, prism as mprism
import gr_models as GM
from gr_models import M_, COLL, quad, loft, cap, rounded_rect

SAMPLE_FAR = 48                     # lightmap sample size for scenery-only surfaces (houses past the player clip)


# ================================================================================================= brush textures
def textures(TX):
    a = TX.add
    a('stucco', stucco((176, 172, 162)), scale=1.0)
    a('shingles', shingles((78, 80, 86)), scale=1.0)
    a('asphalt', asphalt(), scale=1.0, extra='\tq3map_lightmapSampleSize 24\n')
    a('roadline', TL.solid((226, 224, 214), 4, 140, 64), check_tile=False)
    a('footpath', slabs((168, 166, 158)), scale=2.0, extra='\tq3map_lightmapSampleSize 32\n')
    a('kerb', TL.solid((178, 176, 168), 6, 141, 128), scale=0.5)
    a('brickwall', TL.bricks((150, 82, 62), (196, 186, 170), rows=8, cols=4, vary=16), scale=0.75)
    a('lawnfar', TL.solid((58, 90, 42), 10, 142, 256) + TL.N3(256, 2, 143, 12), scale=1.5, steps='softsteps',
      extra=f'\tq3map_lightmapSampleSize {SAMPLE_FAR}\n')
    a('roadfar', asphalt(), scale=1.0, extra=f'\tq3map_lightmapSampleSize {SAMPLE_FAR}\n')


def stucco(col, n=256):
    """sand-float render: fine speckle over a soft mottle (tileable noise only)"""
    return TL.fill(n, col, 5, 120) + TL.N3(n, 3, 121, 7) + TL.N3(n, 0.4, 122, 9)


def shingles(col, rows=8, cols=4, n=256):
    """asphalt shingles: staggered tabs, a dark shadow line under each row, per-tab tone"""
    x, y = TL.xy(n)
    row = np.floor(y * rows)
    u = x * cols + (row % 2) * 0.5
    tid = np.floor(u) + row * 31
    jit = (np.sin(tid * 12.9898) * 43758.5453) % 1
    c = TL.fill(n, col, 3, 123) + (jit[..., None] - 0.5) * 22 + TL.N3(n, 0.4, 124, 10)
    fy = (y * rows) % 1
    c = c * (1 - 0.45 * np.clip((fy - 0.86) / 0.14, 0, 1))[..., None]            # shadow at the lower edge of a row
    c = np.where(((u % 1) < 0.015)[..., None], c * 0.55, c)                       # slots between tabs
    return c


def asphalt(n=256):
    return TL.fill(n, (58, 60, 64), 6, 125) + TL.N3(n, 0.3, 126, 14) + TL.N3(n, 4, 127, 6)


def slabs(col, n=256):
    """footpath: concrete with a sawn joint at the tile edge (one 512u slab per tile at scale 2)"""
    x, y = TL.xy(n)
    c = TL.fill(n, col, 6, 128) + TL.N3(n, 0.6, 129, 6)
    j = (x < 0.012) | (y < 0.012)
    return np.where(j[..., None], c * 0.62, c)


# ================================================================================================= model materials
def materials():
    TX = GM.TX
    m = lambda key, arr, kind='lm', **o: M_.__setitem__(key, TX.material(key, arr, kind, **o))
    m('paneldoor', panel_door_tex((214, 206, 188)), shade=20)
    m('trimm', TL.solid((240, 238, 230), 2, 130), shade=20)
    m('lanternblk', TL.metal((34, 34, 38), brushed=False), 'lms', v=0.15, shade=30)
    m('lanternglow', TL.solid((255, 214, 150), 2, 131, 64), 'glow')
    for key, col in (('suvwhite', (232, 232, 228)), ('suvblue', (52, 84, 140)), ('suvred', (160, 30, 34)),
                     ('suvsilver', (150, 154, 160))):
        m(key, TL.solid(col, 2, 132), 'lms', v=0.25, shade=70, two=True)
    m('suvglass', TL.solid((22, 26, 30), 2, 133), 'lms', v=0.45, shade=70, two=True)
    m('alloy', TL.metal((170, 172, 176), brushed=False), 'lms', v=0.35, shade=50)
    m('suvtrim', TL.solid((34, 34, 36), 2, 134), shade=50)
    m('plate', TL.label('PAD 4U', 256, 64, (240, 236, 210), (30, 30, 34), border=(30, 30, 34)), shade=20)
    m('barrier', TL.stripes((220, 40, 36), (236, 236, 230), n_stripes=6, vertical=True), shade=30)
    m('coneorange', TL.solid((240, 110, 30), 2, 135), shade=50)
    m('conewhite', TL.solid((240, 240, 236), 2, 136), shade=50)
    m('pipe', TL.grime(TL.solid((160, 158, 152), 8, 137, 256), 0.3, 138), shade=60)
    m('skip', TL.grime(TL.solid((230, 180, 30), 4, 139), 0.35, 144), shade=20)
    m('rubble', TL.stone((128, 120, 110), cells=24), shade=40)
    m('closed', TL.label('ROAD CLOSED', 512, 128, (240, 240, 236), (200, 30, 30), border=(200, 30, 30)), shade=20)
    m('mailbox', TL.label('12', 128, 128, (40, 70, 60), (236, 230, 200)), shade=20)
    m('post', TL.planks((120, 96, 70), n_planks=2, grain=8, vertical=True), shade=20)
    m('cabinet', TL.grime(TL.solid((70, 96, 76), 3, 149), 0.2, 150), shade=20)
    m('cabinetlbl', TL.label('DANGER\n400 V', 256, 256, (70, 96, 76), (250, 210, 40)), shade=20)
    m('shelterframe', TL.metal((60, 64, 70), brushed=False), 'lms', v=0.15, shade=30)
    m('shelterback', TL.dots((96, 100, 108), (60, 62, 68), n_dots=24, r=0.3), shade=20)
    m('advert', TL.label("PADMAN\nCOLA", 256, 512, (200, 30, 40), (255, 240, 200), border=(255, 240, 200)), 'glow')
    m('shelterroof', TL.metal((140, 146, 150)), shade=30)
    m('benchwood', TL.planks((150, 104, 60), n_planks=4, grain=10), shade=20)
    m('brickm', TL.bricks((150, 82, 62), (196, 186, 170), rows=8, cols=4, vary=16), shade=20)
    m('capm', TL.solid((178, 176, 168), 6, 151, 128), shade=20)
    m('hedgem', GM.hedge(), shade=80)
    m('couch', TL.fabric((120, 96, 70), weave=56), shade=40)
    m('couchleg', TL.solid((50, 36, 26), 2, 152), shade=20)
    m('fridge', TL.grime(TL.solid((232, 230, 222), 2, 153), 0.25, 154), 'lms', v=0.1, shade=20)
    m('freesign', TL.label('FREE!', 256, 128, (250, 240, 200), (30, 30, 34), border=(30, 30, 34)), shade=20)
    # neighbours' houses (scenery past the player clip: coarse lightmaps)
    for key, col in (('h_grey', (178, 174, 166)), ('h_beige', (196, 180, 150)), ('h_cream', (220, 210, 180)),
                     ('h_blue', (160, 176, 186)), ('h_sage', (162, 172, 146))):
        m(key, stucco(col), shade=20, sample=SAMPLE_FAR)
    m('h_roof', shingles((70, 72, 78)), shade=20, sample=SAMPLE_FAR)
    m('h_roof2', shingles((96, 70, 58)), shade=20, sample=SAMPLE_FAR)
    m('h_fascia', TL.solid((236, 234, 226), 2, 145), shade=20, sample=SAMPLE_FAR)
    m('h_door', panel_door_tex((200, 194, 180)), shade=20, sample=SAMPLE_FAR)
    m('h_front', front_door_tex(), shade=20, sample=SAMPLE_FAR)
    ML.T('winglow_m', window_tex(lit=True, glow=True))
    m('h_winlit', window_tex(lit=True), shade=20, glowmap='winglow_m', sample=SAMPLE_FAR, image='h_winlit_m')
    m('h_windark', window_tex(lit=False), 'lms', v=0.2, shade=20, sample=SAMPLE_FAR)


def panel_door_tex(col, cols=4, rows=4, n=256):
    """sectional garage door: raised panels (light top/left bevel, dark bottom/right), a groove between sections"""
    x, y = TL.xy(n)
    c = TL.fill(n, col, 3, 146) + TL.N3(n, 0.5, 147, 4)
    fx, fy = (x * cols) % 1, (y * rows) % 1
    inside = (fx > 0.1) & (fx < 0.9) & (fy > 0.16) & (fy < 0.84)
    hi = inside & ((fx < 0.16) | (fy < 0.22))
    lo = inside & ((fx > 0.84) | (fy > 0.78))
    c = np.where(hi[..., None], c * 1.08, c); c = np.where(lo[..., None], c * 0.8, c)
    c = np.where((fy < 0.03)[..., None], c * 0.55, c)                                # section joint
    return c


def front_door_tex(n=256):
    c = TL.planks((96, 60, 40), n_planks=3, grain=10, vertical=True, n=n)
    x, y = TL.xy(n)
    glass = (np.abs(x - 0.5) < 0.18) & (y > 0.12) & (y < 0.42)
    return np.where(glass[..., None], ML.C((250, 210, 140)), c)


def window_tex(lit=True, glow=False, n=256):
    """white frame, 2 x 2 panes; lit = warm curtained glass (glow image = the panes only, for the additive stage)"""
    x, y = TL.xy(n)
    frame = (x < 0.07) | (x > 0.93) | (y < 0.07) | (y > 0.93) | (np.abs(x - 0.5) < 0.025) | (np.abs(y - 0.45) < 0.025)
    if glow:
        g = np.where(frame[..., None], ML.C((0, 0, 0)), ML.C((150, 110, 50)) * (0.7 + 0.3 * (1 - y))[..., None])
        return g
    pane = ML.C((120, 96, 60)) if lit else ML.C((28, 34, 44))
    curtain = ((x < 0.2) | (x > 0.8)) if lit else np.zeros_like(x, bool)
    c = np.where(frame[..., None], ML.C((238, 236, 230)), pane + TL.N3(n, 1, 148, 6))
    if lit: c = np.where((curtain & ~frame)[..., None], ML.C((150, 70, 60)), c)
    return c


# ================================================================================================= front of the garage
def panel_door(w, h):
    """sectional door partly raised: the panel face at y 0 (facing -y), bottom rail, side tracks running up"""
    X = ML.Model()
    rbox(X.mesh(M_['paneldoor']), (-w / 2, 0, 0), (w / 2, 20, h), r=3, k=1, tile=w / 4)
    rbox(X.mesh(M_['lanternblk']), (-w / 2, -6, -16), (w / 2, 22, 0), r=3, k=1, tile=400)
    return ML.save('paneldoor', X)


def lantern():
    """coach lantern on a wall bracket (y 0 = wall face, the lamp hangs out to -y)"""
    X = ML.Model()
    rbox(X.mesh(M_['lanternblk']), (-30, -10, -60), (30, 0, 120), r=4, k=1)                 # back plate
    tube(X.mesh(M_['lanternblk']), [(0, -5, 60), (0, -70, 60), (0, -110, 40)], [8, 8, 8], nseg=6)
    rbox(X.mesh(M_['lanternblk']), (-56, -166, 150), (56, -54, 176), r=6, k=1)                # cap
    rbox(X.mesh(M_['lanternglow']), (-44, -154, 20), (44, -66, 150), r=2, k=1)               # glass box (glow)
    for (cx, cy) in ((-46, -156), (46, -156), (-46, -64), (46, -64)):                       # corner bars
        rbox(X.mesh(M_['lanternblk']), (cx - 5, cy - 5, 10), (cx + 5, cy + 5, 152), r=1, k=1)
    rbox(X.mesh(M_['lanternblk']), (-50, -160, 0), (50, -60, 20), r=4, k=1)                  # base
    return ML.save('lantern', X)


# ================================================================================================= vehicles
def suv_wheel(X, c, r=210, w=180):
    W = ML.Model()
    prof = [(r * 0.66, -w / 2), (r * 0.92, -w / 2 - 4), (r, -w / 2 + 24), (r, w / 2 - 24), (r * 0.92, w / 2 + 4), (r * 0.66, w / 2)]
    revolve(W.mesh(M_['tyre']), prof, n=24)
    revolve(W.mesh(M_['alloy']), [(r * 0.66, w / 2 + 1), (r * 0.5, w / 2 + 10), (0, w / 2 + 14)], n=20, inward=True)
    revolve(W.mesh(M_['alloy']), [(0, -w / 2 - 14), (r * 0.5, -w / 2 - 10), (r * 0.66, -w / 2 - 1)], n=20, inward=True)
    from meshlib import rot_axis
    X.add_model(W, rot_axis((0, 1, 0), math.pi / 2), c)


SUV = dict(L=2700, W=540, zb=40, belt=560, roof=1000)


def suv(name, paint):
    """modern SUV (photo reference: a white crossover on the driveway). Tinted glass all round (no interior), roof
    rails, alloys. Collision: body box to the ground (nobody fits under a 40u gap) + the greenhouse."""
    X = ML.Model()
    L2, W, zb, belt, roof = SUV['L'] / 2, SUV['W'], SUV['zb'], SUV['belt'], SUV['roof']
    P = M_[paint]
    ys = [-L2, -L2 + 20, -L2 + 70, -L2 + 150] + list(np.linspace(-L2 + 260, L2 - 260, 18)) + [L2 - 150, L2 - 70, L2 - 20, L2]
    secs = []
    for y in ys:
        e = min(y + L2, L2 - y)
        k = min(1.0, (e + 30) / 200) ** 0.4
        top = belt - (70 if y < -L2 + 820 else 0) * min(1, (-L2 + 820 - y) / 300) if y < -L2 + 820 else belt
        top = top - (1 - k) * 90
        bot = zb + (1 - k) * 90
        secs.append([(px, y, pz) for (px, pz) in rounded_rect(0, W * (0.88 + 0.12 * k), bot, top, 90)])
    uvb = lambda p, n: (p[1] / 600.0, p[2] / 600.0) if abs(n[0]) > 0.5 else (p[0] / 600.0, p[1] / 600.0)
    loft(X, secs, lambda n, c: P, uvb, centre_fn=lambda c: np.array([0, c[1], (zb + belt) / 2]))
    cap(X, secs[0], P, (0, -1, 0), lambda p, n: (p[0] / 600, p[2] / 600))
    cap(X, secs[-1], P, (0, 1, 0), lambda p, n: (p[0] / 600, p[2] / 600))
    # greenhouse: raked windscreen, slight tumblehome, dark glass sides, painted roof
    g0, g1 = -L2 + 820, L2 - 140
    gs = []
    for y in np.linspace(g0, g1, 16):
        tf = min(1, max(0, (y - g0) / 620)); tr = min(1, max(0, (g1 - y) / 260))
        t = min(tf, tr); t = t * t * (3 - 2 * t)
        top = belt + max(10, (roof - belt) * t)
        hw = W - 40 - 80 * (top - belt) / (roof - belt)
        gs.append([(px, y, pz) for (px, pz) in rounded_rect(0, hw, belt - 2, top, 50)])
    loft(X, gs, lambda n, c: P if n[2] > 0.8 else M_['suvglass'], uvb,
         centre_fn=lambda c: np.array([0, c[1], belt + 100]))
    cap(X, gs[-1], M_['suvglass'], (0, 1, 0), lambda p, n: (p[0] / 600, p[2] / 600))
    for s in (-1, 1):                                                                      # roof rails
        tube(X.mesh(M_['alloy']), [(s * 300, g0 + 760, roof + 4), (s * 300, g0 + 820, roof + 40),
                                   (s * 300, g1 - 260, roof + 40), (s * 300, g1 - 200, roof + 4)], [12] * 4, nseg=6)
    for s in (-1, 1):                                                                      # wheels, dark arches
        for wy in (-L2 + 520, L2 - 520):
            suv_wheel(X, (s * (W - 70), wy, 210))
            quad(X.mesh(M_['suvtrim']), (s * (W + 1), wy - 260, zb), (s * (W + 1), wy + 260, zb),
                 (s * (W + 1), wy + 200, 420), (s * (W + 1), wy - 200, 420)) if s > 0 else \
                quad(X.mesh(M_['suvtrim']), (s * (W + 1), wy + 260, zb), (s * (W + 1), wy - 260, zb),
                     (s * (W + 1), wy - 200, 420), (s * (W + 1), wy + 200, 420))
    for s in (-1, 1):                                                                      # lights
        xa, xb = (W - 170, W - 40) if s > 0 else (-W + 40, -W + 170)
        quad(X.mesh(M_['taillight']), (xb, L2 + 2, 560), (xa, L2 + 2, 560), (xa, L2 + 2, 660), (xb, L2 + 2, 660))
        quad(X.mesh(M_['headlight']), (xa, -L2 - 2, 380), (xb, -L2 - 2, 380), (xb, -L2 - 2, 450), (xa, -L2 - 2, 450))
    quad(X.mesh(M_['plate']), (90, L2 + 3, 330), (-90, L2 + 3, 330), (-90, L2 + 3, 390), (90, L2 + 3, 390))
    rbox(X.mesh(M_['suvtrim']), (-W + 20, -L2 - 10, 120), (W - 20, -L2 + 40, 260), r=20, k=2)    # bumpers
    rbox(X.mesh(M_['suvtrim']), (-W + 20, L2 - 40, 120), (W - 20, L2 + 10, 250), r=20, k=2)
    COLL[name] = dict(boxes=[((-W, -L2, 0), (W, L2, belt)), ((-W + 60, g0 + 200, belt), (W - 60, g1, roof))])
    return ML.save(name, X)


# ================================================================================================= roadworks + street furniture
def barrier():
    """water-filled road barrier, 1200 long, red/white; y 0 = centre"""
    X = ML.Model()
    poly = [(-600, -150), (600, -150), (600, 150), (-600, 150)]
    mprism(X.mesh(M_['barrier']), poly, 0, 120, tile=1200)
    prof = [(-150, 120), (-80, 560), (80, 560), (150, 120)]
    for j in range(3):
        a0, a1 = prof[j], prof[j + 1]
        quad(X.mesh(M_['barrier']), (-600, a0[0], a0[1]), (600, a0[0], a0[1]), (600, a1[0], a1[1]), (-600, a1[0], a1[1]),
             uv=((0, 1), (1, 1), (1, 0), (0, 0)))
        quad(X.mesh(M_['barrier']), (600, a0[0], a0[1]), (-600, a0[0], a0[1]), (-600, a1[0], a1[1]), (600, a1[0], a1[1]),
             uv=((0, 1), (1, 1), (1, 0), (0, 0)))
    for x in (-600, 600):                                                                  # end caps
        sgn = 1 if x > 0 else -1
        P = [(x, p[0], p[1]) for p in [(-150, 0), (150, 0), (150, 120), (80, 560), (-80, 560), (-150, 120)]]
        if sgn < 0: P = P[::-1]
        X.mesh(M_['barrier']).poly([np.array(p, float) for p in P], (sgn, 0, 0), [(0.5 + p[1] / 600, 1 - p[2] / 600) for p in P])
    COLL['barrier'] = dict(boxes=[((-600, -150, 0), (600, 150, 560))])
    return ML.save('barrier', X)


def closed_sign():
    """ROAD CLOSED board on two legs (stands on the barrier line), board faces -y and +y"""
    X = ML.Model()
    for s in (-1, 1):
        rbox(X.mesh(M_['lanternblk']), (s * 420 - 15, -15, 0), (s * 420 + 15, 15, 900), r=3, k=1)
    quad(X.mesh(M_['closed']), (-480, -18, 640), (480, -18, 640), (480, -18, 880), (-480, -18, 880))
    quad(X.mesh(M_['closed']), (480, 18, 640), (-480, 18, 640), (-480, 18, 880), (480, 18, 880))
    COLL['closed'] = dict(boxes=[((-440, -20, 0), (-400, 20, 900)), ((400, -20, 0), (440, 20, 900))])
    return ML.save('closedsign', X)


def cone():
    X = ML.Model()
    rbox(X.mesh(M_['suvtrim']), (-90, -90, 0), (90, 90, 16), r=4, k=1)
    revolve(X.mesh(M_['coneorange']), [(70, 16), (40, 160)], n=16)
    revolve(X.mesh(M_['conewhite']), [(40, 160), (28, 220)], n=16)
    revolve(X.mesh(M_['coneorange']), [(28, 220), (10, 300)], n=16)
    disc(X.mesh(M_['coneorange']), 10, 300, n=12)
    COLL['cone'] = dict(cyls=[(0, 0, 70, 0, 300)])
    return ML.save('cone', X)


def pipes():
    """three concrete drainage pipes stacked 2 + 1 along x (roadworks)"""
    X = ML.Model()
    R, r, L = 220, 180, 1200
    from meshlib import rot_axis
    for (py, pz) in ((-226, R), (226, R), (0, R + 390)):
        Pm = ML.Model()
        revolve(Pm.mesh(M_['pipe']), [(R, -L / 2), (R, L / 2)], n=20)
        revolve(Pm.mesh(M_['pipe']), [(r, L / 2), (r, -L / 2)], n=20, inward=True)
        revolve(Pm.mesh(M_['pipe']), [(r, L / 2), (R, L / 2)], n=20)
        revolve(Pm.mesh(M_['pipe']), [(R, -L / 2), (r, -L / 2)], n=20)
        X.add_model(Pm, rot_axis((0, 1, 0), math.pi / 2), (0, py, pz))
    COLL['pipes'] = dict(boxes=[((-L / 2, -446, 0), (L / 2, 446, 2 * R)), ((-L / 2, -R, 2 * R), (L / 2, R, 2 * R + 390))])
    return ML.save('pipes', X)


def skip_bin():
    """builder's skip, 1800 x 1000, sloped ends, full of rubble"""
    X = ML.Model()
    L, Wd, H = 900, 500, 820
    bot, top = 620, 900
    outer = [(-bot, -Wd, 0), (bot, -Wd, 0), (top, -Wd, H), (-top, -Wd, H)]
    for s in (-1, 1):
        y = s * Wd
        P = [(p[0], y, p[2]) for p in outer]
        if s > 0: P = [P[1], P[0], P[3], P[2]]
        quad(X.mesh(M_['skip']), *P, uv=((0, 1), (1, 1), (1, 0), (0, 0)))
    for s in (-1, 1):
        a = (s * bot, -Wd, 0); b = (s * bot, Wd, 0); c = (s * top, Wd, H); d = (s * top, -Wd, H)
        quad(X.mesh(M_['skip']), *((b, a, d, c) if s < 0 else (a, b, c, d)))
    quad(X.mesh(M_['skip']), (-bot, Wd, 0), (bot, Wd, 0), (bot, -Wd, 0), (-bot, -Wd, 0), n=(0, 0, -1))
    quad(X.mesh(M_['rubble']), (-top + 40, -Wd + 20, H - 60), (top - 40, -Wd + 20, H - 60), (top - 40, Wd - 20, H - 60),
         (-top + 40, Wd - 20, H - 60), n=(0, 0, 1))
    rbox(X.mesh(M_['skip']), (-top - 10, -Wd - 12, H - 40), (top + 10, Wd + 12, H), r=4, k=1)
    COLL['skip'] = dict(boxes=[((-bot, -Wd, 0), (bot, Wd, H))])
    return ML.save('skip', X)


def letterbox():
    X = ML.Model()
    rbox(X.mesh(M_['post']), (-30, -30, 0), (30, 30, 620), r=3, k=1)
    rbox(X.mesh(M_['mailbox']), (-110, -150, 620), (110, 150, 820), r=30, k=3, tile=300)
    COLL['letterbox'] = dict(boxes=[((-30, -30, 0), (30, 30, 620)), ((-110, -150, 620), (110, 150, 820))])
    return ML.save('letterbox', X)


def cabinet():
    """green power/telecom cabinet on the verge"""
    X = ML.Model()
    rbox(X.mesh(M_['cabinet']), (-260, -160, 0), (260, 160, 960), r=10, k=1, tile=400)
    rbox(X.mesh(M_['cabinet']), (-280, -180, 960), (280, 180, 1000), r=8, k=1, tile=400)
    quad(X.mesh(M_['cabinetlbl']), (-120, -161, 560), (120, -161, 560), (120, -161, 800), (-120, -161, 800))
    quad(X.mesh(M_['cabinetlbl']), (120, 161, 560), (-120, 161, 560), (-120, 161, 800), (120, 161, 800))
    COLL['cabinet'] = dict(boxes=[((-260, -160, 0), (260, 160, 1000))])
    return ML.save('cabinet', X)


def bus_shelter():
    """bus shelter, open to -y (the road): perforated back panel, a lit PADMAN COLA advert as the +x side panel,
    an open -x side, a flat roof, a bench. Walk in; the roof is out of reach (1400)."""
    X = ML.Model()
    L, D, H = 1400, 500, 1400
    for (x, y) in ((-L / 2, -D / 2), (L / 2, -D / 2), (-L / 2, D / 2), (L / 2, D / 2)):
        rbox(X.mesh(M_['shelterframe']), (x - 20, y - 20, 0), (x + 20, y + 20, H), r=4, k=1)
    rbox(X.mesh(M_['shelterback']), (-L / 2 + 20, D / 2 - 12, 60), (L / 2 - 20, D / 2, H - 60), r=2, k=1, tile=600)
    rbox(X.mesh(M_['shelterframe']), (L / 2 - 12, -D / 2 + 20, 60), (L / 2, D / 2 - 20, H - 60), r=2, k=1)
    quad(X.mesh(M_['advert']), (L / 2 - 13, -D / 2 + 30, 120), (L / 2 - 13, D / 2 - 30, 120), (L / 2 - 13, D / 2 - 30, H - 120),
         (L / 2 - 13, -D / 2 + 30, H - 120))
    quad(X.mesh(M_['advert']), (L / 2 + 1, D / 2 - 30, 120), (L / 2 + 1, -D / 2 + 30, 120), (L / 2 + 1, -D / 2 + 30, H - 120),
         (L / 2 + 1, D / 2 - 30, H - 120))
    rbox(X.mesh(M_['shelterroof']), (-L / 2 - 60, -D / 2 - 80, H), (L / 2 + 60, D / 2 + 40, H + 40), r=6, k=1, tile=600)
    rbox(X.mesh(M_['benchwood']), (-L / 2 + 120, D / 2 - 200, 260), (L / 2 - 160, D / 2 - 20, 290), r=4, k=1, tile=400)
    for x in (-L / 2 + 200, L / 2 - 240):
        rbox(X.mesh(M_['shelterframe']), (x - 15, D / 2 - 180, 0), (x + 15, D / 2 - 40, 260), r=2, k=1)
    COLL['shelter'] = dict(boxes=[((-L / 2 - 20, D / 2 - 12, 0), (L / 2 + 20, D / 2 + 20, H)),
                                  ((L / 2 - 12, -D / 2 - 20, 0), (L / 2 + 20, D / 2 - 12, H)),
                                  ((-L / 2 - 20, -D / 2 - 20, 0), (-L / 2 + 20, -D / 2 + 20, H)),
                                  ((-L / 2 + 120, D / 2 - 200, 0), (L / 2 - 160, D / 2 - 12, 290)),
                                  ((-L / 2 - 60, -D / 2 - 80, H), (L / 2 + 60, D / 2 + 40, H + 40))])
    return ML.save('shelter', X)


def hedge_clump(name, w, d, h):
    """overgrown hedge spilling over a front wall: a soft rounded block (y 0 = the wall face, grows to -y)"""
    X = ML.Model()
    rbox(X.mesh(M_['hedgem']), (-w / 2, -d, 0), (w / 2, 0, h), r=min(140, d / 2 - 1), k=3, tile=300)
    COLL[name] = dict(boxes=[((-w / 2, -d, 0), (w / 2, 0, h))])
    return ML.save(name, X)


def couch():
    """old three-seater put out on the berm for the inorganic collection (with a FREE! sign)"""
    X = ML.Model()
    C = M_['couch']
    for (x0, x1) in ((-600, -500), (500, 600)): rbox(X.mesh(C), (x0, -240, 40), (x1, 240, 420), r=40, k=3, tile=300)  # arms
    rbox(X.mesh(C), (-500, -240, 40), (500, 240, 220), r=30, k=2, tile=300)                                         # base
    rbox(X.mesh(C), (-500, 120, 220), (500, 240, 560), r=40, k=3, tile=300)                                         # back
    for x in (-330, 0, 330): rbox(X.mesh(C), (x - 160, -230, 220), (x + 160, 120, 290), r=30, k=2, tile=300)       # cushions
    for (x, y) in ((-560, -200), (560, -200), (-560, 200), (560, 200)):
        rbox(X.mesh(M_['couchleg']), (x - 20, y - 20, 0), (x + 20, y + 20, 40), r=4, k=1)
    quad(X.mesh(M_['freesign']), (-140, -232, 300), (140, -232, 300), (140, -232, 440), (-140, -232, 440))
    COLL['couch'] = dict(boxes=[((-600, -240, 0), (600, 120, 290)), ((-600, 120, 0), (600, 240, 560))])
    return ML.save('couch', X)


def fridge():
    """old fridge, door taped shut (inorganic collection)"""
    X = ML.Model()
    rbox(X.mesh(M_['fridge']), (-300, -300, 0), (300, 300, 1100), r=30, k=2, tile=600)
    rbox(X.mesh(M_['suvtrim']), (-290, -306, 700), (290, -300, 712), r=2, k=1)
    rbox(X.mesh(M_['alloy']), (220, -330, 780), (250, -300, 1000), r=8, k=1)
    COLL['fridge'] = dict(boxes=[((-300, -300, 0), (300, 300, 1100))])
    return ML.save('fridge', X)


# ================================================================================================= neighbours' houses
def house(name, w, d, h, wall, roof='h_roof', garage=1, lit=(1, 0, 1)):
    """single-storey stucco house with a hip roof and an attached double garage (the photo's style). Scenery past the
    player clip, no collision. Model space: front wall at y 0 facing -y, body y 0..d, x -w/2..w/2, z 0 = ground.
    garage = +1 / -1: garage on the +x / -x end. lit = which of the front windows (+ side windows) glow."""
    X = ML.Model()
    W2 = w / 2
    S = M_[wall]
    def wallq(a, b, z0, z1):           # vertical quad from a to b (xy), facing to the left of a->b
        quad(X.mesh(S), (a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1),
             uv=((a[0] / 600 + a[1] / 600, -z0 / 600), (b[0] / 600 + b[1] / 600, -z0 / 600),
                 (b[0] / 600 + b[1] / 600, -z1 / 600), (a[0] / 600 + a[1] / 600, -z1 / 600)))
    wallq((-W2, 0), (W2, 0), 0, h); wallq((W2, 0), (W2, d), 0, h); wallq((W2, d), (-W2, d), 0, h); wallq((-W2, d), (-W2, 0), 0, h)
    # hip roof
    o, pitch = 160, 0.42
    ex0, ex1, ey0, ey1 = -W2 - o, W2 + o, -o, d + o
    rise = (ey1 - ey0) / 2 * pitch
    zr = h + rise; ym = (ey0 + ey1) / 2
    rx = max(0.0, (ex1 - ex0) / 2 - (ey1 - ey0) / 2)
    R = M_[roof]
    def rq(P, uvs):
        X.mesh(R).poly([np.array(p, float) for p in P], None, uvs)
    def ruv(p): return (p[0] / 500, (p[1] + p[2] * 1.5) / 500)
    F = [(ex0, ey0, h), (ex1, ey0, h), (rx, ym, zr), (-rx, ym, zr)]                       # front slope
    Bk = [(ex1, ey1, h), (ex0, ey1, h), (-rx, ym, zr), (rx, ym, zr)]
    for P in (F, Bk):
        n = np.cross(np.subtract(P[1], P[0]), np.subtract(P[3], P[0])); n = n / np.linalg.norm(n)
        X.mesh(R).poly([np.array(p, float) for p in P], n, [ruv(p) for p in P])
    for P in ([(ex1, ey0, h), (ex1, ey1, h), (rx, ym, zr)], [(ex0, ey1, h), (ex0, ey0, h), (-rx, ym, zr)]):
        n = np.cross(np.subtract(P[1], P[0]), np.subtract(P[2], P[0])); n = n / np.linalg.norm(n)
        X.mesh(R).poly([np.array(p, float) for p in P], n, [(p[1] / 500, (p[0] + p[2] * 1.5) / 500) for p in P])
    # fascia + soffit
    Fs = M_['h_fascia']
    for (a, b) in (((ex0, ey0), (ex1, ey0)), ((ex1, ey0), (ex1, ey1)), ((ex1, ey1), (ex0, ey1)), ((ex0, ey1), (ex0, ey0))):
        quad(X.mesh(Fs), (a[0], a[1], h - 70), (b[0], b[1], h - 70), (b[0], b[1], h + 2), (a[0], a[1], h + 2))
    quad(X.mesh(Fs), (ex0, ey1, h - 70), (ex1, ey1, h - 70), (ex1, ey0, h - 70), (ex0, ey0, h - 70), n=(0, 0, -1))
    # front: double garage door on one end, front door + windows on the other
    gw, gh = 1500, 1200
    gx = garage * (W2 - 200 - gw / 2)
    quad(X.mesh(M_['h_door']), (gx - gw / 2, -3, 0), (gx + gw / 2, -3, 0), (gx + gw / 2, -3, gh), (gx - gw / 2, -3, gh),
         uv=((0, 1), (1, 1), (1, 0), (0, 0)))
    quad(X.mesh(Fs), (gx - gw / 2 - 60, -2, 0), (gx + gw / 2 + 60, -2, 0), (gx + gw / 2 + 60, -2, gh + 60), (gx - gw / 2 - 60, -2, gh + 60))
    side = -garage
    dx = side * 300
    quad(X.mesh(M_['h_front']), (dx - 160, -3, 0), (dx + 160, -3, 0), (dx + 160, -3, 1080), (dx - 160, -3, 1080))
    quad(X.mesh(Fs), (dx - 210, -2, 0), (dx + 210, -2, 0), (dx + 210, -2, 1130), (dx - 210, -2, 1130))
    rbox(X.mesh(M_['lanternglow']), (dx + side * 280 - 30, -40, 760), (dx + side * 280 + 30, -4, 860), r=3, k=1)
    wins = [side * (W2 - 900), side * (W2 - 900) + side * -700] if w > 3000 else [side * (W2 - 700)]
    for i, wx in enumerate(wins):
        mat = M_['h_winlit'] if lit[i % len(lit)] else M_['h_windark']
        quad(X.mesh(Fs), (wx - 330, -2, 380), (wx + 330, -2, 380), (wx + 330, -2, 1180), (wx - 330, -2, 1180))
        quad(X.mesh(mat), (wx - 300, -3, 410), (wx + 300, -3, 410), (wx + 300, -3, 1150), (wx - 300, -3, 1150))
    for s in (-1, 1):                                                                        # one side window each
        x = s * (W2 + 3)
        mat = M_['h_winlit'] if lit[-1] and s == side else M_['h_windark']
        a, b = (d * 0.35, d * 0.35 + 600) if s > 0 else (d * 0.35 + 600, d * 0.35)
        quad(X.mesh(mat), (x, a, 410), (x, b, 410), (x, b, 1150), (x, a, 1150))
    return ML.save(name, X)


HOUSES = [  # name, frontage, depth, wall height, wall material, roof, garage side, lit windows
    ('house_a', 2800, 2400, 1560, 'h_grey', 'h_roof', -1, (1, 0, 1)),
    ('house_b', 3200, 2400, 1560, 'h_beige', 'h_roof2', 1, (0, 1, 0)),
    ('house_c', 2600, 2200, 1500, 'h_cream', 'h_roof', 1, (1, 1, 0)),
    ('house_d', 3000, 2600, 1620, 'h_blue', 'h_roof', -1, (0, 0, 1)),
    ('house_e', 3000, 2300, 1560, 'h_sage', 'h_roof2', 1, (1, 0, 0)),
]


def build_all():
    panel_door(GM.DOOR_W, 700); lantern()
    for nm, paint in (('suv_white', 'suvwhite'), ('suv_blue', 'suvblue'), ('suv_red', 'suvred'), ('suv_silver', 'suvsilver')):
        suv(nm, paint)
    barrier(); closed_sign(); cone(); pipes(); skip_bin(); letterbox(); cabinet(); bus_shelter(); hedge_clump('clump', 540, 300, 800); couch(); fridge()
    for args in HOUSES: house(*args)
