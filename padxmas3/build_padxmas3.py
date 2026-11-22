#!/usr/bin/env python3
"""Padman's Christmas: Under the Tree (wop_padxmas3) - padxmas re-imagined from underneath the tree.

    OUT=<dir> python3 build_padxmas3.py          (wopbuild.py padxmas3 preview / check / all)

Scale ~16u per cm: Padman is 3.5 cm tall, the presents are buildings. x east, y north, floor 0 (carpet).
The tree (trunk at TC) stands in a green plastic stand full of water; its boughs are the sky of the arena, the room's
cream wall closes the north side, the rest of the living room is a blurred custom skybox beyond invisible clip.
Zones: tree stand + walkable lowest branch (centre) | present tower (NE) | gingerbread house (SW) | fallen bauble (SE)
| wrapping-paper tube + unrolled sheet (W) | toy train + present tunnel (S) | milk & cookies for Santa (NW).
Levels: floor 0 | train cab roof 336 | stand rim 320 | ginger roof 368 | tube top 400 | tunnel roof 416 |
box A lid 576 | box B lid 864 | branch 1104 -> 984 at the tip. See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, cyl, hull, carve, sub_rects, sign_box, ramp as wramp
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL
import xm3_art as A
import xm3_models as XM
import xm3_more as XR

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                    # the room: -3328 -2304 2560 2304, walls on all four sides
ZTOP = 3840                                         # ceiling (2.4 m at 16u/cm)
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '22', '_color': '1 0.86 0.7', 'gridsize': '128 128 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
MA = A.M

# ------------------------------------------------------------------------------------------------ layout (world)
TC = (0.0, 600.0)                                  # trunk axis
ST = (-416, 184, 416, 1016); RIM, SFL, WTOP, SW = 320, 160, 272, 32   # stand box, rim top, bowl floor, water top, wall
TRUNK_R = 128
BR_ANG = math.atan2(800, 1500)                     # walkable branch heads ENE toward the present tower
BR_NODES = [(128, 1104), (480, 1088), (840, 1040), (1180, 984)]   # (distance from axis, walk surface z)
BR_W = [120, 120, 128, 192]
BOXA = (1120, 1088, 1888, 1728); A_H = 576; A_DOOR = (1424, 1584, 240); A_HATCH = (1168, 1456, 1360, 1648)
BOXB = (1440, 1280, 1824, 1664); B_H = 288
GH = (-2048, -1664, -1344, -1088); GH_H = 352; GH_DOOR = (-1760, -1632, 192)
BAUB = (1500.0, -1250.0, 300.0); BAUB_R, BAUB_T = 340, 24
TUBE_X, TUBE_Y0, TUBE_Y1, TUBE_A, TUBE_IN = -2850, 1100, 2050, 200, 184
TRAIN_Y = -1800
TUN = (640, -1952, 1040, -1648); TUN_H = 400
PLATE = (-1500, 1520, 360)
FP = (-3328, -600, -3072, 1000); FP_OPEN = (-280, 680, 960); MANTEL_Z, MANTEL_D = 1216, 288
WINDOW = (-1400, 1400, 1500, 3300)
VAULT = (-384, -384, 384, 384); VZ = -1600


def bpt(d, z=0.0):
    return (TC[0] + d * math.cos(BR_ANG), TC[1] + d * math.sin(BR_ANG), z)


def branch_z(d):
    for (d0, z0), (d1, z1) in zip(BR_NODES[:-1], BR_NODES[1:]):
        if d0 <= d <= d1: return z0 + (z1 - z0) * (d - d0) / (d1 - d0)
    return BR_NODES[-1][1]


def tex6(**kw):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t.update(kw); return t


# ------------------------------------------------------------------------------------------------ helpers
def tf_by(fn):
    """texfn for solid_piece from fn(centre, normal) -> material key"""
    def f(c, n, poly):
        k = fn(np.asarray(c), np.asarray(n))
        if k is None: return None
        return MA[k], ML.planar_uv(n, 256.0)
    return f


def place(name, X, x, y, z, angle=0, boxes=(), cyls=(), lit=True, occupy=True):
    if name not in ML.PLACE: ML.save(name, X)
    return K.custom(ML.PLACE[name], x, y, z, angle=angle, boxes=boxes, cyls=cyls, lit=lit, occupy=occupy)


def model(name, builder, *a, **kw):
    if name not in ML.PLACE: ML.save(name, builder(*a, **kw))
    return ML.PLACE[name]


# ------------------------------------------------------------------------------------------------ shell
def shell():
    """the living room itself: structural floor, four wallpapered walls with skirting boards, a ceiling at real room
    height (2.4 m = 3840u) and a big south window onto the snowy night (sealed sky box behind it)"""
    fl = {'top': T('carpet'), 'side': CAULK, 'bot': CAULK}
    K.add(box((X0 - 64, Y0 - 64, -32), (X1 + 64, Y1 + 64, 0), fl, detail=False))
    K.add(box((X0 - 64, Y1, 0), (X1 + 64, Y1 + 64, ZTOP), tex6(s=T('wall')), detail=False))
    K.add(box((X0 - 64, Y0 - 64, 0), (X0, Y1, ZTOP), tex6(e=T('wall')), detail=False))
    K.add(box((X1, Y0 - 64, 0), (X1 + 64, Y1, ZTOP), tex6(w=T('wall')), detail=False))
    K.add(box((X0 - 64, Y0 - 64, ZTOP), (X1 + 64, Y1 + 64, ZTOP + 32), tex6(bot=T('ceiling')), detail=False))
    WX0, WX1, WZ0, WZ1 = WINDOW
    K.sky_window((X0, Y0 - 64, 0), (X1, Y0, ZTOP), (WX0, WX1, WZ0, WZ1), T('wall'), T('sky'), jamb_tex=T('sill'),
                 glass_tex=T('glass'), face='n')
    wt = {'side': T('sill'), 'top': T('sill'), 'bot': T('sill')}
    for x in (WX0 + (WX1 - WX0) / 3, WX0 + 2 * (WX1 - WX0) / 3):
        K.add(box((x - 20, Y0 - 28, WZ0), (x + 20, Y0, WZ1), wt))
    zm = (WZ0 + WZ1) / 2
    for (xa, xb) in ((WX0, WX0 + (WX1 - WX0) / 3 - 20), (WX0 + (WX1 - WX0) / 3 + 20, WX0 + 2 * (WX1 - WX0) / 3 - 20),
                     (WX0 + 2 * (WX1 - WX0) / 3 + 20, WX1)):
        K.add(box((xa, Y0 - 28, zm - 16), (xb, Y0, zm + 16), wt))
    K.add(box((WX0 - 80, Y0, WZ0 - 60), (WX1 + 80, Y0 + 96, WZ0), wt))
    # skirting boards (the west one stops at the chimney breast)
    sk = {'n': T('skirting'), 's': T('skirting'), 'e': T('skirting'), 'w': T('skirting'), 'top': T('skirting'), 'bot': CAULK}
    K.add(box((X0, Y1 - 24, 0), (X1, Y1, 160), sk), box((X0, Y0, 0), (X1, Y0 + 24, 160), sk),
          box((X1 - 24, Y0 + 24, 0), (X1, Y1 - 24, 160), sk),
          box((X0, Y0 + 24, 0), (X0 + 24, FP[1], 160), sk), box((X0, FP[3], 0), (X0 + 24, Y1 - 24, 160), sk))
    # the wall socket the fairy lights are plugged into
    K.add(sign_box((-580, Y1 - 32, 216), (-420, Y1 - 24, 376), T('socket'), 128, 128, back=CAULK, facing='s', edge=T('china')))


# ------------------------------------------------------------------------------------------------ the fireplace (W)
def fireplace():
    """chimney breast on the west wall with a lit fire, a stone hearth (one 16u step), a painted surround and a deep
    mantel shelf (walk surface MANTEL_Z): bellows pads from the floor at both ends, the flames teleport you up onto it
    (Santa's way in, reversed), a gold-bow fling pad takes you back down"""
    bx0, by0, bx1, by1 = FP                 # breast x -3328..-3072
    oy0, oy1, oz = FP_OPEN
    fx0 = bx0 + 64                          # firebox back face
    hx1 = bx1 + 320                         # hearth front
    br = [box((bx0, by0, 0), (fx0, by1, ZTOP), 'x/x'),                                     # back wall
          box((fx0, by0, 16), (bx1, oy0, ZTOP), 'x/x'), box((fx0, oy1, 16), (bx1, by1, ZTOP), 'x/x'),   # jambs
          box((fx0, oy0, oz), (bx1, oy1, ZTOP), 'x/x'),                                    # lintel + breast above
          box((fx0, by0, 0), (hx1, by1, 16), 'x/x')]                                       # hearth (into the firebox)
    pil = [box((bx1, by0, 16), (bx1 + 80, by0 + 160, MANTEL_Z - 32), 'x/x'), box((bx1, by1 - 160, 16), (bx1 + 80, by1, MANTEL_Z - 32), 'x/x')]
    shelf = [box((bx1, by0 - 160, MANTEL_Z - 32), (bx1 + MANTEL_D, by1 + 160, MANTEL_Z), 'x/x')]

    def tex(c, n):
        if c[2] < 17 and n[2] > 0.5: return 'hearth_tile'
        if c[2] < 17: return 'hearth_tile'
        inside = fx0 - 1 < c[0] < bx1 + 1 and oy0 - 1 < c[1] < oy1 + 1 and c[2] < oz + 1
        if inside: return 'sootbrick'
        if c[0] > bx1 - 0.5 and c[2] < MANTEL_Z + 1: return 'mantel_paint'
        return 'plaster'

    def ext(X):
        wm = X.mesh(MA['mantel_paint'])
        for y in (by0 + 20, by0 + 140, by1 - 140, by1 - 20):              # corbels under the shelf
            XM.rbox(wm, (bx1 + 80, y - 20, MANTEL_Z - 132), (bx1 + 150, y + 20, MANTEL_Z - 32), r=8, k=2, tile=128)
        XM.rbox(wm, (bx1 + MANTEL_D - 6, by0 - 166, MANTEL_Z - 40), (bx1 + MANTEL_D + 6, by1 + 166, MANTEL_Z - 4), r=4, k=2, tile=128)
        XM.rbox(wm, (bx1 - 1, oy0 - 40, oz), (bx1 + 30, oy1 + 40, oz + 60), r=6, k=2, tile=128)          # lintel moulding
    K.solid_piece('fireplace', br + pil + shelf, tf_by(tex), extra=ext)
    fc = ((fx0 + bx1) / 2, (oy0 + oy1) / 2)
    place('fire', XR.grate_logs(520), fc[0], fc[1], 16, angle=90, occupy=False, lit=False)
    K.light(bx1 + 40, fc[1], 260, 1100, '1 0.55 0.2'); K.light(bx1 + 400, fc[1], 120, 500, '1 0.6 0.3')
    K.speaker(fc[0], fc[1], 120, 'ambient/fire_crackling')
    md = (bx1 + 190, 520, MANTEL_Z)
    K.teleporter((fx0 + 20, fc[1] - 300, 17), (bx1 - 30, fc[1] + 300, 200), dest=md, angle=0, name='chimney')
    K.keep_clear(bx1, oy0, hx1 + 160, oy1, 0)
    # mantel dressing (clock against the breast, candles, stockings + garland on the front, the painting above)
    mz = MANTEL_Z
    place('mantel_clock', XR.mantel_clock(), bx1 + 80, 200, mz, boxes=[((-70, -150, 0), (70, 150, 340))])
    cs = model('candlestick', XR.candlestick)
    for y in (-690, 660):
        K.custom(cs, bx1 + 60, y, mz, cyls=[(0, 0, 40, 0, 180)])
    for y, col in ((-520, 'gold'), (-160, 'red'), (560, 'green'), (900, 'gold')):
        place(f'stocking_{col}', XR.stocking_hang(col), bx1 + MANTEL_D - 46, y, mz - 32, angle=0, occupy=False)
    place('garland', XR.garland(by1 - by0 + 300), bx1 + MANTEL_D + 6, (by0 + by1) / 2, mz - 2, occupy=False, lit=False)
    place('painting', XR.picture(900, 680), bx1, 200, mz + 220, occupy=False)
    for k, (y, a) in enumerate(((-480, 8), (-340, -10), (420, 6), (560, -12), (790, 4))):
        place(f'card{k % 3}', XR.xmas_card(k % 3), bx1 + 60, y, mz, angle=a, boxes=[((-40, -40, 0), (40, 40, 140))])
    K.botclip_rect(bx1, by0 - 160, bx1 + MANTEL_D, by1 + 160, mz, sides='nse', gaps=[('e', -650, -470), ('e', 730, 910), ('n', -2900, -2790)])
    # hearth-side dressing on the floor
    K.prop(model('log_basket', XR.log_basket), -2950, -1250, 0, cyls=[(0, 0, 182, 0, 200)])
    K.prop(model('fire_tools', XR.fire_tools), -2900, -900, 0, cyls=[(0, 0, 88, 0, 30), (0, 0, 40, 30, 680)])


# ------------------------------------------------------------------------------------------------ the tree
def tree():
    x0, y0, x1, y1 = ST
    # --- stand (plastic tub): body, four walls, two sloped feet (ramps), clamp screws, wing knobs
    b = [box((x0, y0, 0), (x1, y1, SFL), 'x/x'),
         box((x0, y0, SFL), (x1, y0 + SW, RIM), 'x/x'), box((x0, y1 - SW, SFL), (x1, y1, RIM), 'x/x'),
         box((x0, y0 + SW, SFL), (x0 + SW, y1 - SW, RIM), 'x/x'), box((x1 - SW, y0 + SW, SFL), (x1, y1 - SW, RIM), 'x/x')]
    feet = [wramp(x1, 232, x1 + 480, 424, 0, 0, RIM, 'w', 'x/x'), wramp(x0 - 480, 232, x0, 424, 0, 0, RIM, 'e', 'x/x')]
    screws = [box((-24, TC[1] + TRUNK_R, 256), (24, y1 - SW, 304), 'x/x'), box((-24, y0 + SW, 256), (24, TC[1] - TRUNK_R, 304), 'x/x'),
              box((TRUNK_R, TC[1] - 24, 256), (x1 - SW, TC[1] + 24, 304), 'x/x'), box((x0 + SW, TC[1] - 24, 256), (-TRUNK_R, TC[1] + 24, 304), 'x/x')]
    knobs = [box((-24, y1, 264), (24, y1 + 56, 312), 'x/x'), box((-80, y1 + 56, 236), (80, y1 + 80, 340), 'x/x'),
             box((-24, y0 - 56, 264), (24, y0, 312), 'x/x'), box((-80, y0 - 80, 236), (80, y0 - 56, 340), 'x/x'),
             box((x1, TC[1] - 24, 264), (x1 + 56, TC[1] + 24, 312), 'x/x'), box((x1 + 56, TC[1] - 80, 236), (x1 + 80, TC[1] + 80, 340), 'x/x'),
             box((x0 - 56, TC[1] - 24, 264), (x0, TC[1] + 24, 312), 'x/x'), box((x0 - 80, TC[1] - 80, 236), (x0 - 56, TC[1] + 80, 340), 'x/x')]

    def stand_tex(c, n):
        if n[2] > 0.9 and abs(c[2] - RIM) < 1: return 'plastic_r'
        return 'plastic_g'

    def stand_extra(X):
        rm = X.mesh(MA['plastic_r'])
        XM.rbox(rm, (x0 - 6, y0 - 6, RIM - 22), (x1 + 6, y1 + 6, RIM - 8), r=4, k=2, tile=256, faces='nsewb')
        for s in screws:
            mn, mx = s.bounds()
            c = (np.asarray(mn) + np.asarray(mx)) / 2
            ax = 0 if (mx[0] - mn[0]) > (mx[1] - mn[1]) else 1
            p0 = c.copy(); p1 = c.copy(); p0[ax] = mn[ax]; p1[ax] = mx[ax]
            XM.tube(X.mesh(MA['chrome']), [p0 + [0, 0, -2], p1 + [0, 0, -2]], 20, nseg=12, vlen=64)
    K.solid_piece('stand', b + feet + screws + knobs, tf_by(stand_tex), extra=stand_extra)
    K.route('stand_east_foot', (x1 + 560, 328, 0), (x1 - 16, 328, RIM))
    K.route('stand_west_foot', (x0 - 560, 328, 0), (x0 + 16, 328, RIM))
    K.keep_clear(x1 + 470, 200, x1 + 620, 456, 0); K.keep_clear(x0 - 620, 200, x0 - 470, 456, 0)
    # steps out of the water (south inside), the water itself, the trunk
    steps = K.stairs16(x0 + 64, y0 + SW, x0 + 384, y0 + SW + 96, SFL, RIM, 'e', {'top': T('stand'), 'side': T('stand'), 'bot': CAULK},
                       route='stand_steps')
    tr = cyl(TC[0], TC[1], TRUNK_R, SFL, ZTOP, WCLIP, 16)
    K.add(tr)
    K.water_box((x0 + SW, y0 + SW, SFL), (x1 - SW, y1 - SW, WTOP), T('water'), cutters=steps + [tr] + screws)
    place('trunk', XM.trunk(ZTOP - SFL - 40), TC[0], TC[1], SFL, occupy=False)
    K.speaker(0, 860, 300, 'ambient/water_rippling')
    # secret: the drain grate on the bowl floor (under water) -> the inside of a present
    g = (240, 820)
    K.add(cyl(g[0], g[1], 40, SFL, SFL + 1, {'top': T('grate'), 'side': T('grate'), 'bot': CAULK}, 12))
    K.secret((g[0] - 32, g[1] - 32, SFL + 1), (g[0] + 32, g[1] + 32, SFL + 49), dest=(0, -200, VZ), angle=90, name='drain')

    # --- canopy above (no collision) and the walkable branch
    X, lights = XM.canopy(SFL, [(1450 - SFL, 2300, 300, 11), (1950 - SFL, 1900, 300, 9), (2450 - SFL, 1500, 260, 8),
                                (2950 - SFL, 1100, 220, 7)], wall_y=Y1 - TC[1], skip_angle=BR_ANG,
                          hang=lambda X, p, k, rr: XR.ornament_mix(X, p, KINDS[k % len(KINDS)], rr))
    ML.save('canopy', X)
    K.custom(ML.PLACE['canopy'], TC[0], TC[1], SFL, lit=False, occupy=False)
    CANOPY_LIGHTS.extend([(TC[0] + p[0], TC[1] + p[1], SFL + p[2]) for p in lights])
    place('topper', XR.topper(), TC[0], TC[1], 3330, angle=270, occupy=False)
    K.light(TC[0], TC[1] - 300, 3500, 400, '1 0.9 0.6')
    walk_branch()


CANOPY_LIGHTS = []
KINDS = ['icicle', 'cane', 'star', 'gingerman', 'bell', 'pinecone', 'icicle', 'star']


def walk_branch():
    """lowest bough as a bark walkway: one convex slab per segment between shared cross-sections"""
    ca, sa = math.cos(BR_ANG), math.sin(BR_ANG)
    side = np.array([-sa, ca, 0.0])
    secs = []
    for (d, z), w in zip(BR_NODES, BR_W):
        c = np.array(bpt(d, z))
        secs.append([c + side * w / 2, c - side * w / 2])
    bs = []
    for i in range(len(secs) - 1):
        pts = []
        for p in secs[i] + secs[i + 1]:
            pts += [tuple(p), tuple(p - [0, 0, 56])]
        bs.append(hull(pts, 'x/x', round_pts=False))
    nodes = [bpt(d, z) for d, z in BR_NODES]

    def ext(X):
        bm = X.mesh(MA['bark'])
        XM.tube(bm, [np.array(p) - [0, 0, 34] for p in nodes], [62, 60, 58, 70], nseg=12, caps=(False, True), vlen=256)
        XM.walk_branch_extras(X, nodes, BR_W)

    K.solid_piece('branch', bs, tf_by(lambda c, n: 'bark' if n[2] > 0.5 else None), extra=ext)
    for i in range(len(BR_NODES) - 1):
        a, b_ = BR_NODES[i], BR_NODES[i + 1]
        # bot clip along both edges of the walkway
        for sg in (-1, 1):
            p0 = np.array(bpt(a[0], a[1])) + side * sg * (BR_W[i] / 2 - 12)
            p1 = np.array(bpt(b_[0], b_[1])) + side * sg * (BR_W[i + 1] / 2 - 12)
            q = [p0, p1, p1 - side * sg * 16, p0 - side * sg * 16]
            pts = [tuple(v) for v in q] + [tuple(v + [0, 0, 64]) for v in q]
            K.add(hull(pts, 'common/botclip', round_pts=False))
    K.route('branch_walk', bpt(300, branch_z(300)), bpt(1100, branch_z(1100)))


# ------------------------------------------------------------------------------------------------ present tower (NE)
def tower():
    ax0, ay0, ax1, ay1 = BOXA
    t = 24
    walls = K.building(BOXA, 0, A_H - t, openings=[('s', A_DOOR[0], A_DOOR[1], 0, A_DOOR[2])], wall_t=t, roof=False, tex='x/x')
    hx0, hy0, hx1, hy1 = A_HATCH
    lid = [box((r[0], r[1], A_H - t), (r[2], r[3], A_H), 'x/x') for r in sub_rects((ax0, ay0, ax1, ay1), [A_HATCH])]
    bx0, by0, bx1, by1 = BOXB
    bb = [box((bx0, by0, A_H), (bx1, by1, A_H + B_H), 'x/x')]

    def tex(c, n):
        inside = (ax0 + t - 1 < c[0] < ax1 - t + 1) and (ay0 + t - 1 < c[1] < ay1 - t + 1) and c[2] < A_H - 1
        if inside or (n[2] < -0.5 and c[2] < A_H): return 'cardboard_in'
        if c[2] > A_H + 1 or (n[2] > 0.5 and c[2] > A_H + B_H - 1): return 'paper_green'
        return 'paper_red'

    def ext(X):
        XM.big_box_extras(X, (ax0, ay0, 0), (ax1, ay1, A_H), 'red', bx=1260, by=1210, door=A_DOOR)
        XM.big_box_extras(X, (bx0, by0, A_H), (bx1, by1, A_H + B_H), 'green', bx=(bx0 + bx1) / 2, by=(by0 + by1) / 2,
                          top_bow=((bx0 + bx1) / 2 + 60, (by0 + by1) / 2 + 60, A_H + B_H + 2))
    K.solid_piece('tower', walls + lid + bb, tf_by(tex), extra=ext)
    K.keep_clear(A_DOOR[0] - 48, ay0 - 128, A_DOOR[1] + 48, ay0 + 128, 0)
    K.route('tower_door', ((A_DOOR[0] + A_DOOR[1]) / 2, ay0 - 96, 0), ((A_DOOR[0] + A_DOOR[1]) / 2, ay0 + 120, 0))
    place('tissue_a', XM.tissue_heap(320, 260, 3), 1700, 1250, 0, occupy=False)
    K.catalog('pad_radio_car/radio_control.md3', 1720, 1560, 0, scale=1.6, angle=200)
    K.light(1500, 1400, 420, 520, '1 0.85 0.7')


# ------------------------------------------------------------------------------------------------ gingerbread house (SW)
def ginger():
    gx0, gy0, gx1, gy1 = GH
    t = 24
    walls = K.building(GH, 0, GH_H, openings=[('n', GH_DOOR[0], GH_DOOR[1], 0, GH_DOOR[2]),
                                              ('e', -1460, -1300, 130, 260), ('w', -1460, -1300, 130, 260),
                                              ('n', -1980, -1860, 140, 260), ('n', -1520, -1420, 140, 260)],
                       wall_t=t, roof_t=16, tex='x/x')
    chim = [box((-1460, -1210, GH_H + 16), (-1380, -1130, GH_H + 136), 'x/x')]

    def tex(c, n):
        if n[2] > 0.5 and c[2] > GH_H: return 'icing'
        return 'ginger'

    def ext(X):
        ic = X.mesh(MA['icing'])
        z = GH_H + 16
        for (p, q) in (((gx0, gy0), (gx1, gy0)), ((gx1, gy0), (gx1, gy1)), ((gx1, gy1), (gx0, gy1)), ((gx0, gy1), (gx0, gy0))):
            pts = [(p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s, z - 4 - 10 * abs(math.sin(s * 24))) for s in np.linspace(0, 1, 48)]
            XM.tube(ic, pts, 7, nseg=6, caps=(False, False))
            for s in np.linspace(0.03, 0.97, 16):
                x_, y_ = p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s
                col = ['red', 'green', 'yellow', 'purple', 'orange'][int(s * 16) % 5]
                g = XM.gumdrop(16, 26, col)
                for sh, mm in g.m.items(): X.mesh(sh).add(mm, t=(x_, y_, z))
        for (cx, cy) in ((gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)):
            XM.tube(X.mesh(MA['candy']), [(cx, cy, 0), (cx, cy, GH_H + 10)], 20, nseg=12, vlen=160)
        # door frame + window icing
        d0, d1, dt = GH_DOOR
        XM.tube(ic, [(d0, gy1 + 2, 0), (d0, gy1 + 2, dt), ((d0 + d1) / 2, gy1 + 2, dt + 30), (d1, gy1 + 2, dt), (d1, gy1 + 2, 0)], 8, nseg=6)
        XM.chimney_top(X, (-1460, -1210, GH_H + 16), (-1380, -1130, GH_H + 136))
    K.solid_piece('ginger_house', walls + chim, tf_by(tex), extra=ext)
    K.stairs16(gx0 - 32, gy0 - 128, gx1, gy0, 0, GH_H + 16, 'e', {'top': T('choc'), 'side': T('choc'), 'bot': CAULK}, route='ginger_stairs')
    K.keep_clear(gx0 - 160, gy0 - 128, gx0 - 32, gy0, 0)
    K.keep_clear(GH_DOOR[0] - 48, gy1 - 128, GH_DOOR[1] + 48, gy1 + 128, 0)
    K.route('ginger_door', ((GH_DOOR[0] + GH_DOOR[1]) / 2, gy1 + 96, 0), ((GH_DOOR[0] + GH_DOOR[1]) / 2, gy1 - 120, 0))
    place('choc_table', table_model(), -1850, -1450, 0, boxes=[((-90, -60, 0), (90, 60, 96))])
    K.light(-1700, -1380, 260, 380, '1 0.8 0.6')


def table_model():
    X = XM.Model()
    XM.rbox(X.mesh(MA['cookie_side']), (-96, -64, 76), (96, 64, 96), r=4, k=2, tile=128)
    for sx in (-1, 1):
        for sy in (-1, 1):
            XM.tube(X.mesh(MA['candy']), [(sx * 74, sy * 44, 0), (sx * 74, sy * 44, 78)], 10, nseg=8)
    return X


# ------------------------------------------------------------------------------------------------ fallen bauble (SE)
def bauble():
    cx, cy, cz = BAUB
    ro, ri = BAUB_R, BAUB_R - BAUB_T
    nl, nb = 16, 10
    hole_az = math.atan2(-cy, -cx)                      # the broken side faces the middle of the map
    bs = []
    for i in range(nb):
        e0 = -math.pi / 2 + math.pi * i / nb; e1 = e0 + math.pi / nb
        for j in range(nl):
            a0 = 2 * math.pi * j / nl; a1 = a0 + 2 * math.pi / nl
            am = (a0 + a1) / 2
            dd = abs(math.atan2(math.sin(am - hole_az), math.cos(am - hole_az)))
            if dd < 0.9 and (e0 + e1) / 2 < 0.62 - dd * 0.4: continue
            pts = []
            for e in (e0, e1):
                for a in (a0, a1):
                    for r in (ro, ri):
                        z = cz + r * math.sin(e)
                        pts.append((cx + r * math.cos(e) * math.cos(a), cy + r * math.cos(e) * math.sin(a), max(z, 0.0)))
            zs = [p[2] for p in pts]
            if max(zs) - min(zs) < 2: continue
            try:
                hb = hull(pts, 'x/x', round_pts=False)
            except Exception:
                continue
            if hb.bounds()[1][2] < 4: continue
            bs.append(hb)

    def tex(c, n):
        d = np.asarray(c) - [cx, cy, cz]
        r = np.linalg.norm(d)
        if abs(np.dot(n, d / r)) < 0.5: return 'white'
        return 'bauble_red' if np.dot(n, d) > 0 else 'mirror'

    def ext(X):
        cap = XM.bauble_cap(100, 90)
        for sh, mm in cap.m.items(): X.mesh(sh).add(mm, t=(cx + ro - 12, cy, cz))
        # gold band round the equator (outside)
        XM.revolve(X.mesh(MA['bauble_gold']), [(ro + 3, cz - 40), (ro + 3, cz + 40)], n=nl * 2, cx=cx, cy=cy, a0=math.degrees(hole_az) + 52,
                   a1=math.degrees(hole_az) + 308)
    K.solid_piece('bauble', bs, tf_by(tex), extra=ext)
    K.crawl((cx - ro, cy - ro, 0), (cx + ro, cy + ro, 140))      # the shell curving in over the floor inside
    K.add(box((cx + ro + 2, cy - 70, cz - 70), (cx + ro + 84, cy + 70, cz + 70), WCLIP))
    K.keep_clear(cx + ri * 0.7 * math.cos(hole_az) - 80, cy + ri * 0.7 * math.sin(hole_az) - 80,
                 cx + ri * 0.7 * math.cos(hole_az) + 80, cy + ri * 0.7 * math.sin(hole_az) + 80, 0)
    hx, hy = cx + (ro + 200) * math.cos(hole_az), cy + (ro + 200) * math.sin(hole_az)
    K.route('bauble_in', (hx, hy, 0), (cx, cy, 0))
    # shards lying round it (standing slivers = cover)
    for k, (dx, dy, yaw, h) in enumerate(((-520, 120, 20, 150), (-380, -330, 75, 110), (-90, 420, 140, 180), (300, -460, 200, 120))):
        sx, sy = cx + dx, cy + dy
        ar = math.radians(yaw)
        u = np.array([math.cos(ar), math.sin(ar), 0]); v = np.array([-math.sin(ar), math.cos(ar), 0])
        tri = [(-90, 0), (100, 0), (10, h)]
        pts = []
        for (a, z) in tri:
            for w in (-8, 8):
                p = np.array([sx, sy, 0]) + u * a + v * (w + 0.12 * z) + [0, 0, z]
                pts.append(tuple(p))
        K.solid_piece(f'shard{k}', [hull(pts, 'x/x', round_pts=False)], tf_by(lambda c, n: 'shard'))
    K.light(cx, cy, cz, 420, '1 0.75 0.7')


# ------------------------------------------------------------------------------------------------ wrapping paper tube (W)
def wrap_tube():
    cx, cz = TUBE_X, TUBE_A
    n = 12
    ro, ri = TUBE_A / math.cos(math.pi / n), TUBE_IN / math.cos(math.pi / n)
    bs = []
    for k in range(n):
        a0 = -math.pi / 2 + (k - 0.5) * 2 * math.pi / n; a1 = a0 + 2 * math.pi / n
        pts = []
        for a in (a0, a1):
            for r in (ro, ri):
                for y in (TUBE_Y0, TUBE_Y1):
                    pts.append((cx + r * math.cos(a), y, cz + r * math.sin(a)))
        bs.append(hull(pts, 'x/x', round_pts=False))

    def tex(c, n_):
        if abs(n_[1]) > 0.9: return 'cardboard'
        r = math.hypot(c[0] - cx, c[2] - cz)
        return 'cardboard' if r > (ro + ri) / 2 else 'cardboard_in'

    K.solid_piece('tube', bs, tf_by(tex))
    # the half-unrolled sheet: a sloped paper slab from the tube's shoulder down to the floor (players + bots walk up it)
    xs, zt = TUBE_X + 140, 376
    xe = xs + 540
    xb = xe - 16 * (xe - xs) / zt
    sy0, sy1 = 1440, 1780
    pts = []
    for y in (sy0, sy1):
        pts += [(xs, y, zt), (xs, y, zt - 16), (xe, y, 0), (xb, y, 0)]
    sheet = hull(pts, {'top': T('paper_sheet'), 'side': T('paper_back'), 'bot': T('paper_back')}, round_pts=False)
    for f in sheet.faces:
        f.tex = T('paper_sheet') if f.n[2] > 0.3 else T('paper_back')
    K.add(sheet)
    K.reserve(sheet)
    K.route('tube_sheet', (xe + 96, (sy0 + sy1) / 2, 0), (cx, (sy0 + sy1) / 2, TUBE_A * 2))
    K.route('tube_inside', (cx, TUBE_Y0 - 120, 0), (cx, TUBE_Y1 + 120, 0))
    K.keep_clear(cx - 160, TUBE_Y0 - 160, cx + 160, TUBE_Y0, 0); K.keep_clear(cx - 160, TUBE_Y1, cx + 160, TUBE_Y1 + 160, 0)
    K.keep_clear(xe, sy0, xe + 140, sy1, 0)
    K.crawl((xs, sy0, 0), (xe, sy1, zt))
    K.crawl((cx - ro - 8, TUBE_Y0 - 8, 0), (cx - ro + 120, TUBE_Y1 + 8, 64)); K.crawl((cx + ro - 120, TUBE_Y0 - 8, 0), (cx + ro + 8, TUBE_Y1 + 8, 64))


# ------------------------------------------------------------------------------------------------ toy train + tunnel (S)
def train():
    y0, y1 = TRAIN_Y - 96, TRAIN_Y + 96
    place('rails', XM.rails(2400), 0, TRAIN_Y, 0, occupy=False, lit=True)
    # engine cab (walk in through either side door), chassis + boiler, chimney
    cab = K.building((-120, y0, 40, y1), 16, 304, openings=[('n', -100, -20, 0, 200), ('s', -100, -20, 0, 200)], wall_t=16,
                     roof_t=16, tex='x/x')
    fl = [box((-120, y0, 0), (40, y1, 16), 'x/x')]
    body = [box((40, y0 + 16, 0), (320, y1 - 16, 96), 'x/x'), box((56, y0 + 32, 96), (320, y1 - 32, 240), 'x/x'),
            box((260, TRAIN_Y - 20, 240), (300, TRAIN_Y + 20, 330), 'x/x')]
    tender = [box((-360, y0 + 16, 0), (-140, y1 - 16, 176), 'x/x')]
    flat = [box((-700, y0 + 16, 0), (-380, y1 - 16, 64), 'x/x')]

    def tex(c, n):
        if c[2] > 300 and c[0] < 50: return 'paint_black'
        if c[0] > 40 and c[2] > 96 and c[2] < 245: return 'paint_green'
        if c[0] < -140: return 'paint_blue'
        return 'paint_red'

    def ext(X):
        wm, hm = X.mesh(MA['paint_black']), X.mesh(MA['brass'])
        for x in (-320, -180, -660, -420):
            for y in (y0 + 10, y1 - 10):
                XM.wheel(wm, hm, (x, y, 36), 36)
        for x in (90, 180, 270, -60):
            for y in (y0 + 10, y1 - 10):
                XM.wheel(wm, hm, (x, y, 48), 48 if x > 0 else 40)
        for x in (120, 200, 280):                         # brass boiler bands
            XM.rbox(X.mesh(MA['brass']), (x - 6, y0 + 30, 94), (x + 6, y1 - 30, 242), r=0, k=1, tile=64, faces='tnsew')
        # coal heap on the tender, presents on the flatcar
        XM.ellipsoid(X.mesh(MA['paint_black']), (-250, TRAIN_Y, 176), 100, 70, 40, nu=12, nv=6, flat_bottom=0)
        for (gx, gw, gh, pat) in ((-620, 120, 120, 'gold'), (-470, 140, 96, 'blue')):
            g = XM.gift(gw, gw, gh, pat)
            for sh, mm in g.m.items(): X.mesh(sh).add(mm, t=(gx, TRAIN_Y, 64))
    K.solid_piece('train', cab + fl + body + tender + flat, tf_by(tex), extra=ext)
    K.keep_clear(-130, y1, 50, y1 + 120, 0); K.keep_clear(-130, y0 - 120, 50, y0, 0)
    K.route('cab_door', (-60, y1 + 96, 0), (-60, y0 - 96, 0))
    # tunnel present over the track
    tx0, ty0, tx1, ty1 = TUN
    tw = K.building(TUN, 0, TUN_H, openings=[('w', -1880, -1720, 0, 300), ('e', -1880, -1720, 0, 300)], wall_t=24, roof_t=16, tex='x/x')

    def ttex(c, n):
        inside = tx0 + 23 < c[0] < tx1 - 23 and ty0 + 23 < c[1] < ty1 - 23 and c[2] < TUN_H
        return 'cardboard_in' if inside or n[2] < -0.5 else 'paper_blue'

    def text(X):
        XM.big_box_extras(X, (tx0, ty0, 0), (tx1, ty1, TUN_H + 16), 'blue', bx=None, by=(ty0 + ty1) / 2 + 100,
                          top_bow=(tx0 + 120, ty0 + 90, TUN_H + 18))
    K.solid_piece('tunnel', tw, tf_by(ttex), extra=text)
    K.route('tunnel_through', (tx0 - 120, TRAIN_Y, 0), (tx1 + 120, TRAIN_Y, 0))
    K.keep_clear(tx0 - 140, TRAIN_Y - 96, tx0, TRAIN_Y + 96, 0); K.keep_clear(tx1, TRAIN_Y - 96, tx1 + 140, TRAIN_Y + 96, 0)


# ------------------------------------------------------------------------------------------------ milk & cookies (NW)
def cookies():
    px, py, pr = PLATE
    pl = [cyl(px, py, pr, 0, 16, 'x/x', 24)]

    def ext(X):
        XM.revolve(X.mesh(MA['china_rim']), [(pr + 1, 0), (pr + 4, 10), (pr - 2, 17), (pr - 40, 16)], n=48, cx=px, cy=py)
    K.solid_piece('plate', pl, tf_by(lambda c, n: 'china'), extra=ext)
    place('cookies3', XM.cookie_stack(110, 36, 3, 1), px - 120, py + 110, 16, cyls=[(0, 0, 112, 0, 108)])
    place('cookies2', XM.cookie_stack(100, 36, 2, 2), px + 150, py - 80, 16, cyls=[(0, 0, 102, 0, 72)])
    place('milk', XM.milk_glass(150, 500), -1950, 2060, 0, cyls=[(0, 0, 156, 0, 500)])
    K.add(box((-1300, 1960, 0), (-1000, 2140, 3), {'top': T('letter'), 'side': T('paper_back'), 'bot': CAULK}))
    # plug in the wall socket and the fairy-light cable along the floor to the stand and up the trunk
    path = [(-500, Y1 - 80, 260), (-500, Y1 - 120, 140), (-500, Y1 - 150, 9), (-420, 1500, 9), (-200, 1200, 9), (-80, 1100, 9),
            (-60, ST[3] + 90, 9)]
    X = XM.plug_and_cable([(0, -56, 0)] + [(p[0] + 500, p[1] - (Y1 - 32), p[2] - 280) for p in path[1:]])
    place('plug', X, -500, Y1 - 32, 280, occupy=False)
    K.speaker(-500, Y1 - 120, 300, 'machine/electric_sizzle')


# ------------------------------------------------------------------------------------------------ the secret
def vault():
    """inside a present: gold paper walls and floor, tissue paper, the good stuff, a teleporter home"""
    x0, y0, x1, y1 = VAULT; z = VZ; h = 448
    w, f = T('secret_wall'), T('secret_floor')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': f, 'side': CAULK, 'bot': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': w, 'side': CAULK, 'top': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    place('tissue_v', XM.tissue_heap(560, 300, 9), 0, 180, z, occupy=False)
    K.item('item_padpower', 0, 60, z); K.item('item_revival', -220, -60, z); K.item('holdable_killerducks', 220, -60, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(-1100, 1150, 0), angle=315, name='vault_exit')
    K.light(0, 0, z + 360, 700, '1 0.9 0.7')
    K.speaker(0, 0, z + 200, 'human/snoring')


# ------------------------------------------------------------------------------------------------ pads
def pads():
    tam = model('pad_tambourine', XM.tambourine)
    sl = model('pad_slinky', XM.slinky)
    bw_r = model('pad_bow_red', XM.flat_bow, 'red')
    bw_g = model('pad_bow_gold', XM.flat_bow, 'gold')
    bw_s = model('pad_bow_silver', XM.flat_bow, 'silver')
    gp = model('pad_gum', XM.gum_pad, 'green')
    sp = model('pad_spool', XM.spool)
    ax0, ay0, ax1, ay1 = BOXA; bx0, by0, bx1, by1 = BOXB
    # floor -> branch root
    lb = bpt(440, branch_z(440))
    K.themed_pad(1000, 560, 0, land=lb, apex=lb[2] + 80, name='pad_branch', place=tam, glow=160)
    # floor -> box A lid (west strip), inside A up through the hatch, A lid -> B lid, B lid -> branch tip
    K.themed_pad(860, 1460, 0, land=(1240, 1190, A_H), apex=A_H + 170, name='pad_boxa', place=sl, glow=140,
                 edges=[(ax0, 1300, A_H)])
    hx0, hy0, hx1, hy1 = A_HATCH
    K.themed_pad((hx0 + hx1) / 2, (hy0 + hy1) / 2 + 20, 0, land=((hx0 + hx1) / 2, 1330, A_H), apex=A_H + 190, name='pad_hatch',
                 place=sl, glow=120, edges=[((hx0 + hx1) / 2, hy0, A_H)])
    K.themed_pad(1640, 1170, A_H, land=(1640, 1470, A_H + B_H), apex=A_H + B_H + 150, name='pad_boxb', place=bw_r, glow=120,
                 edges=[(1640, by0, A_H + B_H)])
    tip = bpt(1110, branch_z(1110))
    K.themed_pad(bx0 + 50, 1380, A_H + B_H, land=tip, apex=tip[2] + 110, name='pad_tip', place=bw_g, glow=120)
    # floor -> mantel (bellows at both ends), mantel -> floor (fling)
    bel = model('pad_bellows', XR.bellows)
    mx = FP[2] + 190
    for (y, nm) in ((-560, 'pad_mantel_s'), (820, 'pad_mantel_n')):
        K.themed_pad(-2560, y, 0, land=(mx, y, MANTEL_Z), apex=MANTEL_Z + 90, name=nm, place=bel, glow=140,
                     edges=[(FP[2] + MANTEL_D, y, MANTEL_Z)], turn=-90)
    K.themed_pad(FP[2] + 140, 1080, MANTEL_Z, land=(-2350, 1120, 0), apex=MANTEL_Z + 60, name='fling_mantel', place=bw_g)
    # floor -> gingerbread roof, floor -> cab roof, floor -> tunnel roof, floor -> tube top
    gx0, gy0, gx1, gy1 = GH
    K.themed_pad(-1520, -760, 0, land=(-1520, -1260, GH_H + 16), apex=GH_H + 16 + 170, name='pad_ginger', place=gp, glow=140,
                 edges=[(-1520, gy1, GH_H + 16)])
    K.themed_pad(-40, -1440, 0, land=(-40, TRAIN_Y, 336), apex=336 + 160, name='pad_cab', place=bw_s, glow=120,
                 edges=[(-40, TRAIN_Y + 96, 336)])
    tx0, ty0, tx1, ty1 = TUN
    K.themed_pad(840, -1400, 0, land=(840, -1830, TUN_H + 16), apex=TUN_H + 16 + 170, name='pad_tunnel', place=sp, glow=120,
                 edges=[(840, ty1, TUN_H + 16)])
    K.themed_pad(-2380, 1250, 0, land=(TUBE_X, 1300, TUBE_A * 2), apex=TUBE_A * 2 + 150, name='pad_tube', place=gp, glow=120,
                 edges=[(TUBE_X + TUBE_A, 1290, TUBE_A * 2)])


# ------------------------------------------------------------------------------------------------ cover + props
def props():
    place('skirt', XM.skirt(1500, 470), TC[0], TC[1] - 60, 0, occupy=False, lit=True)
    gifts = [((-700, -300), (176, 160, 150), 'blue', 20), ((-560, -520), (112, 112, 112), 'gold', 50), ((520, -260), (200, 176, 170), 'stripe', -15),
             ((300, -700), (128, 128, 220), 'purple', 30), ((-1000, 300), (190, 150, 140), 'kraft', 10), ((900, -500), (150, 150, 120), 'green', 40),
             ((-300, -1150), (160, 140, 130), 'red', 5), ((-1200, -350), (130, 130, 130), 'stripe', 60),
             ((2150, 700), (180, 180, 200), 'purple', 15), ((-800, 1900), (200, 160, 150), 'blue', 0), ((450, 1900), (150, 150, 260), 'red', 35),
             ((1100, 300), (140, 120, 110), 'kraft', 70), ((-1350, 700), (150, 150, 200), 'green', 20)]
    for i, ((x, y), (w, d, h), pat, ang) in enumerate(gifts):
        nm = f'gift_{pat}_{w}x{d}x{h}'
        if nm not in ML.PLACE: ML.save(nm, XM.gift(w, d, h, pat))
        K.prop(ML.PLACE[nm], x, y, 0, boxes=[((-w / 2 + 4, -d / 2 + 4, 0), (w / 2 - 4, d / 2 - 4, h - 4))], angle=ang)
    pc = model('pinecone', XM.pinecone)
    for (x, y) in ((600, 250), (-650, 120), (200, -1300), (-2300, -800), (2200, -1900), (2300, 1300)):
        K.prop(pc, x, y, 0, cyls=[(0, 0, 70, 0, 250)])
    cc = model('candy_cane', XM.candy_cane_lying)
    for (x, y, a) in ((-200, -500, 30), (1200, -500, 110), (-1000, -620, 75), (1900, 300, 160)):
        K.prop(cc, x, y, 0, boxes=[((-260, -24, 0), (180, 24, 48)), ((180, -24, 0), (264, 150, 48))], angle=a)
    for i, (x, y, a) in enumerate(((-100, -800, 15), (100, -860, 50), (0, -760, 30), (1400, 400, 20), (-1650, -250, 40))):
        p = model('abc_block', XM.abc_block)
        K.prop(p, x, y, 0, boxes=[((-60, -60, 0), (60, 60, 124))], angle=a)
    for (x, y, r, col) in ((-450, 1450, 90, 'blue'), (700, -1100, 80, 'gold'), (2300, -900, 100, 'silver'), (-2000, 1150, 85, 'green')):
        p = model(f'bauble_s_{col}', XM.lying_bauble, r, col)
        K.prop(p, x, y, 0, cyls=[(0, 0, r - 4, 0, 2 * r - 4)])
    gm = model('ginger_man', XM.ginger_man)
    for (x, y, a) in ((700, -1500, 20), (-1700, -2100, 70), (300, 600 - 900, 0)):
        K.prop(gm, x, y, 0, boxes=[((-60, -150, 0), (60, 150, 16))], angle=a)
    for (x, y) in ((-1000, -700), (1700, 700), (-2200, -1300)):
        K.catalog('gummybears/redbear.md3' if x < 0 else 'gummybears/greenbear.md3', x, y, 0, scale=1.5, search=320)
    K.catalog('gummybears/ldyellowbear.md3', 500, -1500, 0, scale=1.5, angle=40)
    K.catalog('pad_ddmix/jail/snowman.md3', -1250, 1050, 0, scale=1.4, angle=60, lit=True)
    K.catalog('pad_actionfigures/fig_lilly.md3', 2000, -800, 0, scale=1.6, angle=200, lit=True)
    K.catalog('pad_ball/pad_soccerball.md3', 1300, -2000, 0, scale=2.0)
    K.catalog('pad_ducks/pad_duck.md3', -2300, 300, 0, scale=0.9, angle=0, lit=True)
    for (x, y) in ((-900, -1900), (2350, 1900), (-2400, -400)):
        K.catalog('pad_fruits/walnut.md3', x, y, 0, scale=2.5)


# ------------------------------------------------------------------------------------------------ round 2: more toys + life
def more():
    """landmark toys as cover/sight blockers, the candy village round the gingerbread house, things lying about on the
    carpet, a mouse hole in the skirting board, a turning Christmas pyramid"""
    P = lambda name, fn, *a, **kw: model(name, fn, *a, **kw)
    nut = P('nutcracker', XR.nutcracker)
    for (x, y, a) in ((2150, 1050, 200), (-760, 1150, 300)):
        K.prop(nut, x, y, 0, cyls=[(0, 0, 145, 0, 40), (0, 0, 108, 40, 756)], angle=a)
    K.prop(P('snow_globe', XR.snow_globe), 2050, -380, 0, cyls=[(0, 0, 316, 0, 110), (0, 0, 262, 110, 560)], angle=150)
    K.light(2050, -380, 640, 260, '0.8 0.9 1')
    K.prop(P('rocking_horse', XR.rocking_horse), -950, -1250, 0, boxes=[((-300, -96, 0), (300, 96, 370)), ((170, -40, 370), (310, 40, 540))],
           angle=35)
    K.prop(P('teddy', XR.teddy), 2200, 1900, 0, cyls=[(0, 0, 130, 0, 430)], angle=230)
    K.prop(P('jack_box', XR.jack_in_box), 320, -480, 0, boxes=[((-120, -120, 0), (120, 120, 240))], angle=110)
    K.prop(P('drum', XR.drum), 1420, -1760, 0, cyls=[(0, 0, 206, 0, 236)], angle=20)
    K.prop(P('sleigh', XR.sleigh), 2150, -1350, 0, boxes=[((-270, -150, 0), (160, 150, 220)), ((160, -140, 0), (230, 140, 120))], angle=160)
    K.prop(P('bauble_box', XR.bauble_box), -520, -1020, 0, boxes=[((-210, -150, 0), (210, 150, 110))], angle=-20)
    K.prop(P('stocking', XR.stocking_spill), -420, -2020, 0, boxes=[((-300, -70, 0), (180, 130, 100))], angle=10)
    # Christmas pyramid: static frame + turning carousel (func_rotating model2)
    pb = P('pyramid_base', XR.pyramid_base)
    pp = K.prop(pb, 2250, 300, 0, cyls=[(0, 0, 232, 0, 480)], angle=0)
    if pp:
        rot = 'pyramid_rotor'
        if rot not in ML.PLACE: ML.save(rot, XR.pyramid_rotor())
        assert ML.PLACE[rot][1] == 1 and ML.PLACE[rot][2] == 0, 'rotor must be stored at scale 1 for model2'
        K.rotating_model2(ML.PLACE[rot][0], (pp[0], pp[1], 24), 24)
        K.light(pp[0], pp[1], 200, 300, '1 0.8 0.5')
    # candy village round the gingerbread house
    for (x, y, h, key) in ((-2380, -1250, 460, 'lolly_swirl'), (-1230, -960, 400, 'lolly_swirl2'), (-2380, -800, 380, 'lolly_swirl2'),
                           (-1180, -1560, 440, 'lolly_swirl')):
        K.prop(P(f'lolly_{h}_{key[-1]}', XR.lollipop, h, 110, key), x, y, 0, cyls=[(0, 0, 40, 0, 30), (0, 0, 14, 30, h - 2 * 110 - 10)],
               boxes=[((-112, -18, h - 220), (112, 18, h))], angle=0)
    for (x, y) in ((-2420, -1650), (-2200, -2050)):
        K.prop(P('gumdrop_tree', XR.gumdrop_tree), x, y, 0, cyls=[(0, 0, 118, 0, 380)])
    fn = P('fence', XR.fence)
    for (x, y, a) in ((-1960, -950, 0), (-1430, -950, 0)):
        K.prop(fn, x, y, 0, boxes=[((-160, -8, 0), (160, 8, 72))], angle=a, search=48)
    # things lying on the carpet (visual only)
    ring = [(TC[0] + 1520 * math.cos(t), TC[1] - 60 + 1520 * math.sin(t), 4) for t in np.linspace(0, 2 * math.pi, 120)]
    ring = [p for p in ring if p[1] < Y1 - 60]
    place('lights_skirt', XR.floor_lights(ring, seed=1), 0, 0, 0, occupy=False, lit=False)
    wall = [(x, Y1 - 50 + 12 * math.sin(x / 140), 4) for x in np.linspace(X0 + 60, X1 - 60, 90)]
    place('lights_wall', XR.floor_lights(wall, seed=2), 0, 0, 0, occupy=False, lit=False)
    helix = [(TC[0] + (TRUNK_R + 8) * math.cos(t), TC[1] + (TRUNK_R + 8) * math.sin(t), 340 + t * 26) for t in np.linspace(0, 6 * 2 * math.pi, 220)]
    place('lights_trunk', XR.floor_lights(helix, seed=3), 0, 0, 0, occupy=False, lit=False)
    for k, (pts, g) in enumerate(((((-600, -300, 3), (-420, -380, 3), (-250, -330, 3), (-60, -420, 3)), True),
                                   (((900, -900, 3), (1060, -820, 3), (1200, -900, 3), (1380, -840, 3)), False),
                                   (((-1150, 650, 3), (-1050, 520, 3), (-900, 560, 3), (-800, 420, 3)), True))):
        place(f'tinsel{k}', XR.tinsel(pts, g), 0, 0, 0, occupy=False, lit=False)
    for k, (x, y) in enumerate(((-1350, 1380), (1650, 1500), (-150, -1500), (2300, -1700))):
        place(f'coins{k}', XR.coins(9, 110, 10 + k), x, y, 0 if (x, y) != (-1350, 1380) else 16, occupy=False)
    for k, (x, y) in enumerate(((-700, -150), (700, -100), (650, 1200), (-850, 950), (300, 200), (-300, 1500))):
        place(f'needles{k}', XR.needle_scatter(36, 380, 20 + k), x, y, 0, occupy=False, lit=False)
    place('mouse_hole', XR.mouse_hole(), 640, Y1 - 24, 0, occupy=False)
    K.light(640, Y1 - 120, 60, 90, '1 0.75 0.4')
    # light from the floor strings (a few warm/coloured points low down)
    for i, p in enumerate(ring[::10]):
        K.light(p[0], p[1], 60, 160, ['1 0.4 0.35', '0.45 1 0.5', '0.5 0.6 1', '1 0.85 0.4'][i % 4])


# ------------------------------------------------------------------------------------------------ loot, spawns
def items():
    tip = bpt(1150, branch_z(1150))
    K.weapon('imperius', FP[2] + 170, -250, MANTEL_Z, marker='purple')
    K.weapon('betty', tip[0], tip[1], tip[2], marker='black')
    K.weapon('balloony', 1700, 1560, A_H + B_H, marker='orange')
    K.weapon('pumper', -250, 870, SFL, marker='green')
    K.weapon('splasher', BAUB[0] + 40, BAUB[1] + 20, 0, marker='blue')
    K.weapon('boaster', TUBE_X, 1600, TUBE_A - TUBE_IN, marker='orange')
    K.weapon('bubbleg', -1450, 1600, 16, marker='green')
    ammo = {'imperius': [(FP[2] + 170, 950, MANTEL_Z), (-2450, 1300, 0), (-2420, -2180, 0), (1600, 1650, 0), (-1450, -1200, GH_H + 16)],
            'betty': [bpt(600, branch_z(600)), (1650, 1150, 0), (2400, -2150, 0), (-260, 640, RIM)],
            'balloony': [(1700, 1350, A_H + B_H), (1300, 1200, A_H), (-1900, -1300, 0), (-2400, 2150, 0), (600, 2150, 0)],
            'pumper': [(250, 380, SFL), (0, 860, 304), (-2150, 1700, 0), (2400, 200, 0)],
            'splasher': [(BAUB[0] - 120, BAUB[1] - 100, 0), (1000, -2150, 0), (TUBE_X, 1950, TUBE_A * 2), (-600, -2100, 0)],
            'boaster': [(TUBE_X, 1180, TUBE_A - TUBE_IN), (-60, TRAIN_Y, 16), (-1300, 1350, 16), (1300, -900, 0), (-2400, 900, 0)],
            'bubbleg': [(-1650, 1450, 16), (300, 1600, 0), (-1000, -1500, 0), (2000, -1500, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y) in ((900, 950), (-900, -1250), (2200, 0)): K.ammo('nipper', x, y, 0)
    K.item('item_armor_padshield', -1700, -1400, GH_H + 16)
    K.item('item_armor_shard', 840, -1720, TUN_H + 16)
    K.item('item_armor_shard', -1600, -1500, 0); K.item('item_armor_shard', 1250, 1500, A_H); K.item('item_armor_shard', 260, 640, RIM)
    K.item('item_speedy', -60, TRAIN_Y, 336)
    K.item('item_visionless', 1500, 1300, 0)
    K.item('holdable_floater', TUBE_X, 1700, TUBE_A * 2)
    K.item('item_climber', -1450, -1350, 0)
    K.station(0, -1250, 0, ang=90)
    for (x, y, a) in ((-2200, 600, 315), (-900, 1500, 270), (300, 2000, 270), (2300, 2000, 225), (2300, 600, 180), (2300, -600, 180),
                      (1900, -2050, 135), (300, -2100, 90), (-1100, -2100, 45), (-2350, -1000, 0), (-2300, -100, 0), (-600, -400, 45),
                      (700, -200, 135), (1500, 100, 180), (-3000, -1900, 45), (-2400, 2100, 315)):
        K.spawn(x, y, 0, a)


def lights():
    for p in CANOPY_LIGHTS[::2]:
        K.light(p[0], p[1], max(p[2], 1150), 650, ['1 0.4 0.35', '0.45 1 0.5', '0.5 0.6 1', '1 0.85 0.4', '1 0.95 0.85'][int(abs(p[0] + p[1])) % 5])
    K.light_grid(X0, Y0, X1, Y1, 700, 1024, 420, '1 0.85 0.65')
    K.light(0, 600, 700, 600, '1 0.8 0.5')
    K.timer_sound(0, 0, 900, 'machine/clock_ticking', 'clock', 40, 20)
    K.timer_sound(-2000, 1800, 300, 'misc/wind_chimes', 'chimes', 35, 25)
    K.timer_sound(2400, -2000, 300, 'animal/kitten_meow', 'kitten', 60, 40)


def textures():
    A.brush(TX)
    TX.add('sky', TL.solid((40, 50, 80), 2, 21, 64), 'raw', check_tile=False,
           shader=SH.sky('env/frost-bite512', sun=(270, 25), sun_rgb=(0.6, 0.7, 1), sun_int=60, skylight=(25, 3)))
    A.fire_brush(TX)
    TX.kit_defaults(pad_rgb=(255, 120, 90))
    A.materials(TX)
    XR.materials(TX)
    XR.fire_materials(TX)
    A.fire_mats(TX)


if __name__ == '__main__':
    textures()
    shell(); fireplace(); tree(); tower(); ginger(); bauble(); wrap_tube(); train(); cookies(); vault()
    pads(); more(); props(); items(); lights()
    K.fix_items()
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
