#!/usr/bin/env python3
"""PadClock Tower (wop_padclock) - FFA inside a giant clock tower at Padman scale, built on woplib + texlib.

    OUT=<dir> python3 build_padclock.py          (wopbuild.py padclock preview / check / ...)

Tower x -2048..2048, y -1536..1536 (north = +y), floor 0, ceiling 2816. An open atrium (x +-576, y +-704) runs the
full height with the pendulum swinging in it. Levels: ground 0, Gear Gallery 640 (ring), Escapement wings 1280 (west,
east and north), Dial balcony 1920 (south) + Cuckoo ledge 1920 (north), Movement deck 2080 (centre, bridges from both
balconies), bell crown 2560. Models + textures in pc_models.py, design sheet in README.md.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from wopmap import box, cyl, hull, sub_rects, stairs
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL
import pc_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZC = 2816
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '22', '_color': '1 0.94 0.84'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)

# ------------------------------------------------------------------------------------------------ layout
AX, AY = 576, 704                                   # atrium half sizes (open from floor to ceiling)
L1, L2, L3, DECK, CROWN = 640, 1280, 1920, 2080, 2560
SL = 32                                             # level slab thickness (top = level height)
FL01 = (1888, -640, 2048, 640)                      # (L1 hole widened 24u: HOLE01)                      # ground -> L1 flight on the east wall, rising south
FL12 = (-2048, -640, -1888, 640)                    # L1 -> L2 flight on the west wall, rising north
FL23 = (0, 968, 1280, 1120)                         # L2 -> L3 flight along the cuckoo ledge, rising east
EW = (-1504, -96, -1312, 96)                        # weight lift west: ground -> L1 (func_plat)
EE = (1312, -96, 1504, 96)                          # weight lift east: L1 -> L2
L3S = (X0, Y0, X1, -960)                            # dial balcony
L3N = [(X0, 1152, X1, Y1), (1280, 968, X1, 1152)]   # cuckoo ledge (+ landing for FL23)
DECKR = (-400, -320, 400, 320)
DIAL_C = (0, Y0, 2368); DIAL_R = 400
BARREL_C = (-1500, -1170)
CHIME = (-1700, 760, -1100, 1300); CHIME_H = 320
CUCKOO_X = -800


def grow(r, m): return (r[0] - m, r[1] - m, r[2] + m, r[3] + m)


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def void(rect, z0, z1):
    """mark empty air at a level (atrium, holes, missing wings) so scattered props never hang over it"""
    K.occupy(rect[0], rect[1], rect[2], rect[3], z0, z1, why='void')


def place(name, x, y, z, angle=0, **kw):
    c = PM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def prop(name, x, y, z, angle=None, search=96):
    c = PM.COLL.get(name, {})
    return K.prop(ML.PLACE[name], x, y, z, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), angle=angle, search=search)


def flight(rect, z0, z1, d, name, base=None):
    st = K.stairs16(*rect, z0, z1, d, {'top': T('oak'), 'side': T('oak_l')}, route=name, base=base)
    K.reserve(((rect[0], rect[1], z0), (rect[2], rect[3], z1 + 8)))
    v = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[d]
    # 96u clear landing at the foot (z0) and at the top (z1)
    x0, y0, x1, y1 = rect
    if d == 'n': K.keep_clear(x0, y0 - 112, x1, y0, z0); K.keep_clear(x0, y1, x1, y1 + 112, z1)
    if d == 's': K.keep_clear(x0, y1, x1, y1 + 112, z0); K.keep_clear(x0, y0 - 112, x1, y0, z1)
    if d == 'e': K.keep_clear(x0 - 112, y0, x0, y1, z0); K.keep_clear(x1, y0, x1 + 112, y1, z1)
    if d == 'w': K.keep_clear(x1, y0, x1 + 112, y1, z0); K.keep_clear(x0 - 112, y0, x0, y1, z1)
    return st


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: ground slab (with the west weight-lift pit), brick walls, an oak-beamed ceiling and the
    south wall built round the dial window (sealed night sky behind it)"""
    fl = {'top': T('floor0'), 'side': T('stone'), 'bot': CAULK}
    for r in sub_rects((X0 - 32, Y0 - 32, X1 + 32, Y1 + 32), [EW]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), fl, detail=False))
    K.add(box((EW[0], EW[1], -48), (EW[2], EW[3], -16), fl, detail=False))          # pit floor for the lowered plat
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZC), tex6(e=T('brick')), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZC), tex6(w=T('brick')), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZC), tex6(s=T('brick')), detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('oak_l')), detail=False))
    hx = (DIAL_C[0] - DIAL_R, DIAL_C[0] + DIAL_R, DIAL_C[2] - DIAL_R, DIAL_C[2] + DIAL_R)
    K.sky_window((X0, Y0 - 32, 0), (X1, Y0, ZC), hx, T('brick'), T('sky'), jamb_tex=T('brass'),
                 glass_tex=T('dialglass'), face='n')
    # ceiling beams (detail): oak joists across the tower, the bell beam over the centre
    for x in range(-1792, 1793, 512):
        K.add(box((x - 32, Y0, ZC - 64), (x + 32, Y1, ZC), {'bot': T('oak'), 'side': T('oak'), 'top': CAULK}))


def slab(rects, z, holes=(), top='oak', side='brass', bot='oak_l'):
    t = {'top': T(top), 'side': T(side), 'bot': T(bot)}
    out = []
    for R in rects:
        for r in sub_rects(R, list(holes)):
            if r[2] - r[0] < 8 or r[3] - r[1] < 8: continue
            b = box((r[0], r[1], z - SL), (r[2], r[3], z), t); K.add(b); out.append(b)
    return out


def levels():
    atrium = (-AX, -AY, AX, AY)
    # L1 Gear Gallery: a ring round the atrium; holes for the east flight, the west lift and the east lift pit
    slab([(X0, Y0, X1, Y1)], L1, [atrium, (FL01[0] - 24, FL01[1], FL01[2], FL01[3]), grow(EW, 8), EE])
    K.add(box((EE[0], EE[1], L1 - SL), (EE[2], EE[3], L1 - 16), {'top': T('iron'), 'side': T('brass'), 'bot': T('oak_l')}))
    # L2 Escapement wings: everything north of the atrium's south edge (the south band stays open up to the dial)
    slab([(X0, -AY, X1, Y1)], L2, [atrium, (FL12[0], FL12[1], FL12[2] + 24, FL12[3]), grow(EE, 8)])
    # L3: dial balcony (south) and cuckoo ledge (north)
    slab([L3S] + L3N, L3)
    # bridges to the movement deck: flat run, then 16u stairs up 160u
    t = {'top': T('oak'), 'side': T('brass'), 'bot': T('oak_l')}
    K.add(box((-112, -960, L3 - SL), (112, -640, L3), t)); K.add(box((-112, 640, L3 - SL), (112, 1152, L3), t))
    flight((-112, -640, 112, -320), L3, DECK, 'n', 'bridge_s', base=L3 - SL)
    flight((-112, 320, 112, 640), L3, DECK, 's', 'bridge_n', base=L3 - SL)
    K.add(box((DECKR[0], DECKR[1], DECK - 16), (DECKR[2], DECKR[3], DECK), {'top': T('brass'), 'side': T('brass'), 'bot': CAULK}))
    # flights between levels (16u risers: bots skip 32u steps)
    flight(FL01, 0, L1, 's', 'stairs_01')
    flight(FL12, L1, L2, 'n', 'stairs_12')
    flight(FL23, L2, L3, 'e', 'stairs_23')
    # weight lifts (func_plat, bot-usable): brass weight pans with hazard-striped edges
    K.elevator(*EW, 0, L1, {'top': T('brass'), 'side': T('stripe'), 'bot': T('iron')}, speed=180)
    K.elevator(*EE, L1, L2, {'top': T('brass'), 'side': T('stripe'), 'bot': T('iron')}, speed=180)
    K.keep_clear(*grow(EW, 112), 0, L1 + 96); K.keep_clear(*grow(EE, 112), L1, L2 + 96)
    # empty air no prop may hang over
    for z0 in (L1, L2):
        void(atrium, z0, z0 + 400)
    void(atrium, L3, DECK - SL - 320)
    void(FL01, L1, L1 + 200); void(FL12, L2, L2 + 200)
    void((X0, Y0, X1, -AY), L2, L2 + 400)                     # no L2 south band
    void((X0, -960, X1, DECKR[1] - 16), L3, L3 + 140); void((X0, DECKR[3] + 16, X1, 992), L3, L3 + 140)
    void((X0, DECKR[1] - 16, DECKR[0] - 16, DECKR[3] + 16), L3, L3 + 140); void((DECKR[2] + 16, DECKR[1] - 16, X1, DECKR[3] + 16), L3, L3 + 140)                   # L3 only has the balcony and the ledge
    void((X0, 968, 1280, 1152), L3, L3 + 140)


# ------------------------------------------------------------------------------------------------ partitions
WT = 32                                              # partition wall thickness


def partition(axis, c, a0, a1, z0, z1, doors=(), door_h=192, name='wall'):
    """brick partition wall with oak doorways: runs along x at y = c (axis 'x') or along y at x = c (axis 'y'),
    32 thick, z0..z1. doors = [(lo, hi)] along the run, each door_h tall with a lintel above. Splits each level into
    rooms so eye-level sightlines stay short."""
    t = {'side': T('brick'), 'top': T('oak'), 'bot': T('oak_l')}
    dj = {'side': T('oak'), 'top': T('oak'), 'bot': T('oak')}
    cuts = sorted(doors)
    segs, lo = [], a0
    for (d0, d1) in cuts:
        if d0 > lo: segs.append((lo, d0))
        lo = d1
    if lo < a1: segs.append((lo, a1))

    def bx(p0, p1, za, zb, tex):
        if axis == 'x': mn, mx = (p0, c - WT / 2, za), (p1, c + WT / 2, zb)
        else: mn, mx = (c - WT / 2, p0, za), (c + WT / 2, p1, zb)
        b = box(mn, mx, tex); K.add(b); K.reserve((mn, mx))
    for (p0, p1) in segs:
        bx(p0, p1, z0, z1, t)
    for i, (d0, d1) in enumerate(cuts):
        if z1 - z0 > door_h + 16:
            bx(d0, d1, z0 + door_h, z1, dj)
        m = (d0 + d1) / 2
        if axis == 'x':
            K.keep_clear(d0, c - 112, d1, c + 112, z0)
            K.route(f'{name}_d{i}', (m, c - 96, z0), (m, c + 96, z0))
        else:
            K.keep_clear(c - 112, d0, c + 112, d1, z0)
            K.route(f'{name}_d{i}', (c - 96, m, z0), (c + 96, m, z0))


def partitions():
    """rooms on every level. Ground: the pendulum pit gets an arcaded enclosure and the ring is cut along the atrium
    edge lines into eight rooms. Gallery and wings: the same cuts. Balcony and ledge: cross walls with doors."""
    G1 = L1 - SL
    # ground: pendulum pit enclosure (under the Gallery slab edge)
    partition('y', -AX - WT / 2, -AY - WT, AY + WT, 0, G1, [(-480, -288), (288, 480)], name='pit_w')
    partition('y', AX + WT / 2, -AY - WT, AY + WT, 0, G1, [(-480, -288), (288, 480)], name='pit_e')
    partition('x', AY + WT / 2, -AX, AX, 0, G1, [(-400, -208), (208, 400)], name='pit_n')
    partition('x', -AY - WT / 2, -AX, AX, 0, G1, [(-400, -208), (208, 400)], name='pit_s')
    # ground ring: radial cuts
    partition('y', -AX - WT / 2, AY + WT, Y1, 0, G1, [(1000, 1192)], name='g_nw')
    partition('y', AX + WT / 2, AY + WT, Y1, 0, G1, [(1240, 1432)], name='g_ne')
    partition('y', -AX - WT / 2, Y0, -AY - WT, 0, G1, [(-1300, -1108)], name='g_sw')
    partition('y', AX + WT / 2, Y0, -AY - WT, 0, G1, [(-1100, -908)], name='g_se')
    partition('x', AY + WT / 2, X0, -AX - WT, 0, G1, [(-1400, -1208)], name='g_wn')
    partition('x', -AY - WT / 2, X0, -AX - WT, 0, G1, [(-1000, -808)], name='g_ws')
    partition('x', AY + WT / 2, AX + WT, FL01[0] - 24, 0, G1, [(1000, 1192)], name='g_en')
    partition('x', -AY - WT / 2, AX + WT, X1, 0, G1, [(1400, 1592)], name='g_es')
    # Gallery (640): radial cuts; the south band cuts stand free under the dial balcony
    H1 = L2 - SL
    partition('y', -AX - WT / 2, AY + WT, Y1, L1, H1, [(1150, 1342)], name='l1_nw')
    partition('y', AX + WT / 2, AY + WT, Y1 - 66, L1, H1, [(900, 1092)], name='l1_ne')
    partition('y', -AX - WT / 2, Y0 + 66, -AY - WT, L1, L1 + 600, [(-1150, -958)], name='l1_sw')
    partition('y', AX + WT / 2, Y0, -AY - WT, L1, L1 + 600, [(-1350, -1158)], name='l1_se')
    partition('x', AY + WT / 2, FL12[2], -AX, L1, H1, [(-1100, -908)], name='l1_wn')
    partition('x', -AY - WT / 2, FL12[2] + 24, -AX - WT, L1, L1 + 600, [(-1000, -808)], name='l1_ws')
    partition('x', AY + WT / 2, AX, X1, L1, H1, [(1500, 1692)], name='l1_en')
    partition('x', -AY - WT / 2, AX + WT, X1, L1, L1 + 600, [(900, 1092)], name='l1_es')
    # wings (1280): a cross wall through each wing, the north strip cut either side of the atrium
    partition('x', 400, X0 + 88, -AX - 16, L2, L2 + 600, [(-1000, -808)], name='l2_w')
    partition('x', 400, AX + 16, X1 - 88, L2, L2 + 600, [(900, 1092)], name='l2_e')
    partition('y', -AX - WT / 2, AY, Y1, L2, L3 - SL, [(800, 992)], name='l2_nw')
    partition('y', AX + WT / 2, AY, FL23[1] - 16, L2, L2 + 600, [], name='l2_ne')
    partition('y', AX + WT / 2, 1152, Y1, L2, L3 - SL, [(1250, 1442)], name='l2_ne2')
    # dial balcony + cuckoo ledge (1920): cross walls with doors
    for x in (-800, 800):
        partition('y', x, Y0, -960, L3, L3 + 480, [(-1250, -1058)], name=f'l3s_{x}')
    partition('y', -300, 1152, Y1, L3, L3 + 480, [(1320, 1512)], name='l3n_w')       # doors staggered: no ray
    partition('y', 700, 1152, Y1, L3, L3 + 480, [(1170, 1362)], name='l3n_e')         # runs the whole ledge


def rail(axis, c, a0, a1, z, gaps=(), name='rail'):
    """oak balustrade with a brass cap, 64 high (above eye height, so it cuts the long views across the atrium),
    16 thick, centred on line c; gaps = [(lo, hi)] where players drop down and jump pads cross"""
    t = {'side': T('oak'), 'top': T('brass'), 'bot': T('oak_l')}
    lo = a0
    for (g0, g1) in sorted(gaps) + [(a1, a1)]:
        if g0 - lo > 8:
            if axis == 'x': mn, mx = (lo, c - 8, z), (g0, c + 8, z + 64)
            else: mn, mx = (c - 8, lo, z), (c + 8, g0, z + 64)
            K.add(box(mn, mx, t)); K.reserve((mn, mx))
        lo = max(lo, g1)


def rails():
    """balustrades round the atrium on the Gallery and the wings, along the wings' open south edge and along the
    fronts of the dial balcony and the cuckoo ledge"""
    for z, gw, ge, gn, gs in ((L1, [(-500, -340), (200, 400)], [(-400, -200), (340, 500)], [(-300, -140), (200, 360)],
                               [(-360, -200), (140, 300)]),
                              (L2, [(-200, -40), (300, 460)], [(-460, -300), (100, 260)], [(-400, -180), (250, 410)], None)):
        y0 = -AY if z == L1 else -AY + 16              # the wings' south rail takes the corner on L2
        rail('y', -AX - 8, y0, AY, z, gw, f'rail_w{z}')
        rail('y', AX + 8, y0, AY, z, ge, f'rail_e{z}')
        rail('x', AY + 8, -AX, AX, z, gn, f'rail_n{z}')
        if gs: rail('x', -AY - 8, -AX, AX, z, gs, f'rail_s{z}')
    rail('x', -AY + 8, FL12[2] + 24, -AX, L2, [(-1660, -1460), (-1000, -840)])
    rail('x', -AY + 8, AX, X1, L2, [(840, 1000), (1460, 1660)])
    rail('x', -968, X0, X1, L3, [(-1660, -1460), (-830, -770), (-600, -440), (-130, 130), (440, 600), (770, 830), (1460, 1660)])
    rail('x', 1160, X0, 1280, L3, [(-1500, -1340), (-330, -270), (-130, 130), (670, 730)])
    rail('x', 976, 1280, X1, L3, [(1440, 1640), (1700, 1860)])


# ------------------------------------------------------------------------------------------------ centrepiece
def movement_and_bell():
    """the movement block hangs in the atrium top: deck plate on it, escape wheel + anchor on its east face, a train
    wheel on the west face, the pendulum underneath, the bell above (Imperius on its crown)"""
    place('movement', 0, 0, DECK - 16 - PM.MOVE['h'])
    K.speaker(0, 0, 1900, 'machine/clock_ticking')
    K.rotating_model2(f'models/{NS}/escape.md3', (424, 0, 1912), 18, axis='x')
    K.pendulum_model2(f'models/{NS}/anchor.md3', (428, 0, 2048), 7, 140)
    K.rotating_model2(f'models/{NS}/train.md3', (-424, 0, 1900), 6, axis='x', reverse=True)
    K.pendulum_model2(f'models/{NS}/pendulum.iqm', (0, 0, 1740), 9, 1400)
    zb = 2240
    place('bell', 0, 0, zb)
    place('bell_rod', 0, 0, CROWN)
    K.jumppad(300, -150, DECK, land=(0, -56, CROWN), apex=CROWN + 110, name='pad_bell', ceiling=ZC,
              edges=[(195, -116, zb + 14), (150, -102, zb + 200)])
    K.route('deck_s', (0, -800, L3), (-280, -160, DECK))
    K.route('deck_n', (0, 900, L3), (-280, 160, DECK))


def dial():
    """the dial from behind: glowing opal face in the south window, brass bezel, hands turning on func_rotating"""
    cx, cy, cz = DIAL_C
    place('dial', cx, cy + 2, cz, lit=False, occupy=False)
    K.rotating_model2(f'models/{NS}/hand_min.md3', (cx, cy + 28, cz), 6, axis='y')
    K.rotating_model2(f'models/{NS}/hand_hr.md3', (cx, cy + 16, cz), 0.5, axis='y')
    K.light(cx, cy + 60, cz, 900, '1 0.9 0.7')
    K.light(cx, cy + 260, cz - 220, 700, '1 0.88 0.66')
    K.reserve(((cx - DIAL_R, Y0, L3), (cx + DIAL_R, Y0 + 40, cz + DIAL_R)))
    K.timer_sound(cx, cy + 100, cz, 'ambient/wind_night', 'wind', 30, 20, volume=0.5)


def wall_gears():
    """big decorative gears turning on the walls (func_rotating model2); weapclip slabs over their swept discs keep
    players from walking into the teeth"""
    def g(model, c, speed, axis, rev, clip):
        K.rotating_model2(f'models/{NS}/{model}.md3', c, speed, axis=axis, reverse=rev)
        K.add(box(clip[0], clip[1], WCLIP)); K.reserve(clip)
    g('gear_w', (X0 + 40, 0, 1900), 4, 'x', False, ((X0, -440, 1460), (X0 + 72, 440, 2340)))
    g('gear_e', (X1 - 40, 0, 1900), 4, 'x', True, ((X1 - 72, -440, 1460), (X1, 440, 2340)))
    g('gear_s1', (-700, Y0 + 30, 1240), 5, 'y', False, ((-1100, Y0, L1), (-370, Y0 + 66, L3 - SL)))
    g('gear_s2', (-100, Y0 + 30, 1240), 5 * 380 / 250, 'y', True, ((-370, Y0, L1), (170, Y0 + 66, L3 - SL)))
    g('gear_n1', (700, Y1 - 30, 940), 7, 'y', True, ((420, Y1 - 66, L1), (920, Y1, L2 - SL)))
    g('gear_n2', (1126, Y1 - 30, 940), 7 * 260 / 190, 'y', False, ((920, Y1 - 66, L1), (1340, Y1, L2 - SL)))
    for (x, y, z) in ((X0 + 200, 0, 1700), (X1 - 200, 0, 1700), (-400, Y0 + 200, 1100), (900, Y1 - 200, 900)):
        K.speaker(x, y, z, 'machine/mechanics', volume=0.35)


# ------------------------------------------------------------------------------------------------ zones
def barrel():
    """ground floor SW: the mainspring barrel, a walk-in brass drum (door east), pad onto its toothed lid"""
    cx, cy = BARREL_C
    r, t, h = PM.BARREL['r'], PM.BARREL['t'], PM.BARREL['h']
    dh = PM.BARREL['door_h']
    place('barrel', cx, cy, 0, occupy=False)
    n = 16
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        mid = (a0 + a1) / 2
        door = (mid > 337.5 or mid < 22.5)
        z0 = dh if door else 0
        pts = [(cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))) for a in (a0, a1) for rr in (r - t, r)]
        K.add(hull([(p[0], p[1], z0) for p in pts] + [(p[0], p[1], h - 16) for p in pts], WCLIP, round_pts=False))
    K.add(cyl(cx, cy, r + 18, h - 16, h, WCLIP, 16))
    K.add(cyl(cx, cy, 46, 16, h - 16, WCLIP, 8))
    K.add(cyl(cx, cy, 206, 0, 16, WCLIP, 16))                   # the coiled mainspring: a 16u step
    K.occupy(cx - r - 26, cy - r - 26, cx + r + 26, cy + r + 26, 0, h)
    K.keep_clear(cx + r, cy - 80, cx + r + 120, cy + 80, 0)
    K.route('barrel_door', (cx + r + 96, cy, 0), (cx + 120, cy, 0))
    K.jumppad(cx + 560, cy + 190, 0, land=(cx - 30, cy + 150, h), apex=h + 150, name='pad_barrel', ceiling=L1 - SL,
              edges=[(cx + r + 26, cy + 160, h)])


def chime_house():
    """L2 west wing: the chime house, walk-in (door south), 16u stairs up its east side, pad onto the roof"""
    x0, y0, x1, y1 = CHIME
    br = K.building(CHIME, L2, CHIME_H, openings=[('s', -1460, -1340, 0, 136)], tex='x/x')
    K.solid_piece('chime', br, lambda c, n, p: (PM.M_['brass'] if n[2] > 0.7 else PM.M_['oak_l'], ML.planar_uv(n, 256.0)))
    K.keep_clear(-1480, y0 - 112, -1320, y0 + 112, L2)
    K.route('chime_door', (-1400, y0 - 96, L2), (-1400, y0 + 120, L2))
    top = L2 + CHIME_H + 16
    flight((x1, y1 - 21 * 32 - 28, x1 + 128, y1 - 28), L2, top, 'n', None)
    K.route('chime_stairs', (x1 + 64, y1 - 21 * 32 - 28 - 80, L2), (x1 - 120, y1 - 120, top))
    K.jumppad(-1180, 470, L2, land=(-1300, 1060, top), apex=top + 140, name='pad_chime',
              edges=[(-1290, y0, top)])
    K.timer_sound(-1400, 1000, top + 200, 'misc/wind_chimes', 'chimes', 20, 12)


def cuckoo():
    """L3 north ledge: the cuckoo house. Its dark doorway is the secret entry; the bird pops out of the window on a
    timer (func_door + model2, nonsolid) with a ding-dong"""
    x = CUCKOO_X; yb = Y1; z = L3
    place('cuckoo', x, yb, z)
    d = PM.CUCKOO['d']
    K.secret((x - 48, yb - d + 8, z), (x + 48, yb - d + 56, z + 120), dest=(0, -300, -1200), angle=90, name='cuckoo_door',
             approach='s')
    # the bird: func_door with an origin brush, a tiny nonsolid brush, model2; opens toward -y when the timer fires
    o = (x, yb - d + 30, z + 186)
    org = box((o[0] - 8, o[1] - 8, o[2] - 8), (o[0] + 8, o[1] + 8, o[2] + 8), 'common/origin')
    tiny = box((o[0] - 4, o[1] - 4, o[2] + 12), (o[0] + 4, o[1] + 4, o[2] + 20), T('nodraw_ns'))
    K.ent('func_door', brushes=[org, tiny], targetname='cuckoo', model2=f'models/{NS}/bird.md3', angle=270, lip=-104,
          speed=160, wait=3)
    K.timer_sound(x, yb - d - 40, z + 220, 'machine/dingdong', 'cuckoo', 30, 10)


def vault():
    """the Cuckoo's Nest: a sealed room under the tower, reached through the cuckoo house doorway"""
    x0, y0, x1, y1 = (-320, -480, 320, 160); z = -1200
    t = {'side': T('oak_l'), 'top': T('oak'), 'bot': T('oak_l')}
    for mn, mx in (((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z)), ((x0 - 32, y0 - 32, z + 288), (x1 + 32, y1 + 32, z + 320)),
                   ((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 288)), ((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 288)),
                   ((x0, y0 - 32, z), (x1, y0, z + 288)), ((x0, y1, z), (x1, y1 + 32, z + 288))):
        K.add(box(mn, mx, t, detail=False)); K.reserve((mn, mx))
    K.item('item_padpower', -230, -180, z); K.item('item_revival', 230, 100, z); K.item('holdable_killerducks', 230, -180, z)
    K.item('item_armor_padshield', -230, 100, z)
    K.teleporter((-48, y0, z), (48, y0 + 48, z + 96), dest=(CUCKOO_X + 260, 1260, L3), angle=270, name='nest_exit')
    K.light(0, -160, z + 220, 600, '1 0.85 0.6')
    K.speaker(0, -160, z + 100, 'machine/clock_ticking')
    # dressing: the nest with its eggs, the bird keeping watch, hourglass, barrels, a lantern, webs
    place('nest', 0, -20, z)
    place('bird', 80, 40, z + 40, 200, occupy=False)
    for (n, x, y) in (('hourglass', -215, -385), ('crate96', 250, -410)):
        prop(n, x, y, z, search=48)
    hang('lantern_60', -160, -200, z + 288, light=0); hang('lantern_60', 160, -200, z + 288, light=0)
    for (x, y, a) in ((x0, y0, 0), (x1, y0, 90), (x1, y1, 180), (x0, y1, 270)):
        place('cobweb', x, y, z + 288, a, lit=False, occupy=False)


# ------------------------------------------------------------------------------------------------ pads + props
def pads():
    K.jumppad(-440, 300, 0, land=(-800, 300, L1), apex=L1 + 320, name='pad_l1w', ceiling=L2 - SL, edges=[(-AX, 300, L1)])
    K.jumppad(440, -300, 0, land=(800, -300, L1), apex=L1 + 320, name='pad_l1e', ceiling=L2 - SL, edges=[(AX, -300, L1)])
    for s in (-1, 1):
        K.jumppad(s * 1560, -540, L2, land=(s * 1560, -1060, L3), apex=L3 + 160, name=f'pad_wing_{"we"[s > 0]}',
                  edges=[(s * 1560, -960, L3)])
    K.jumppad(-300, 860, L2, land=(-250, 140, DECK), apex=DECK + 110, name='pad_deck', edges=[(-270, 320, DECK)])
    # east wing -> cuckoo ledge east end (Pumper): bots ignored the ledge when it was stairs/bridge only
    K.jumppad(1540, 730, L2, land=(1540, 1090, L3), apex=L3 + 170, name='pad_ledge', edges=[(1540, 968, L3)])


def props():
    """cover where the long rays run: crates of cogs, oil cans, spare-gear stacks, a giant screw, books"""
    place('gearstack', 1300, 1160, 0)
    K.route('gearstack', (880, 1160, 0), (1300, 1160, 128))
    for (n, x, y, z) in (('crates', -900, 1100, 0), ('oilcan', 900, -800, 0), ('crate128', -1000, -500, 0),
                         ('screw', -200, 1100, 0), ('crate96', 1500, -1250, 0), ('oilcan', -1700, 700, 0),
                         ('crates', 1650, 500, 0), ('crate128', -350, -1250, 0),
                         ('crates', -1100, 1200, L1), ('oilcan', 1200, 1100, L1), ('gearstack_s', 1500, -1220, L1),
                         ('crate128', -1700, 500, L1), ('screw', -300, 1150, L1), ('crate96', 300, -1250, L1),
                         ('crate128', -1400, -1100, L1),
                         ('crates', 1000, 760, L2), ('oilcan', -900, -300, L2), ('crate128', 1800, -500, L2),
                         ('gearstack_s', 1650, 1290, L2), ('crate96', -800, 560, L2), ('screw', -330, 1220, L2),
                         ('oilcan', -1700, -1300, L3), ('oilcan', 1700, -1300, L3), ('crate96', 1500, 1350, L3)):
        prop(n, x, y, z)
    for (x, y, z, a) in ((-1300, 600, 0, 30), (1700, -800, L1, 80), (1700, -150, L2, 200), (400, 1380, L3, 0)):
        K.catalog('pad_books/rhodan/pdr_4books.md3', x, y, z, angle=a)
    for (x, y, z) in ((-1080, -1450, 0), (650, 1200, L1), (-1500, 1400, L3)):
        K.catalog('pad_cups/pad_cup01.md3', x, y, z)
    for (x, y, z) in ((0, 1300, L3 + 0), (-200, -1180, L1)):
        K.catalog('ente/ducka.md3', x, y, z, scale=2.0)


def items():
    K.weapon('imperius', 0, -56, CROWN, marker='purple')
    K.weapon('betty', -300, 0, DECK, marker='black')
    K.weapon('balloony', 0, -1250, L3, marker='orange')
    K.weapon('pumper', 1650, 1300, L3, marker='green')
    K.weapon('splasher', -1560, 980, L2 + CHIME_H + 16, marker='blue')
    K.weapon('boaster', 1000, 1150, L1, marker='orange')
    K.weapon('bubbleg', BARREL_C[0] - 150, BARREL_C[1], 16, marker='green')
    ammo = {'imperius': [(300, 0, DECK), (-1500, 1350, L3), (-1880, -1450, 0)],
            'betty': [(0, 250, DECK), (1700, -300, L2), (900, -1050, 0), (-660, 900, L1)],
            'balloony': [(-700, -1100, L3), (-660, -1200, L1), (-300, 1200, 0)],
            'pumper': [(0, 1350, L3), (-200, 1350, L2), (1700, -1350, 0), (1400, 800, L1)],
            'splasher': [(-1400, 1100, L2), (-1000, 0, L2), (-1000, 600, 0)],
            'boaster': [(-1000, 1000, L1), (300, -1150, 0), (900, 250, L2), (1800, 980, 0)],
            'bubbleg': [(0, 0, 0), (600, -1200, L1), (-1000, -350, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((1300, -400, 0), (1700, 450, L1), (-1300, -400, L2)): K.ammo('nipper', x, y, z)
    K.item('item_armor_padshield', BARREL_C[0] + 70, BARREL_C[1] - 120, PM.BARREL['h'])
    K.item('item_armor_shard', 1000, 1350, L3); K.item('item_armor_shard', 1000, -1100, L1)
    K.item('item_speedy', -1600, -350, L1); K.item('holdable_floater', 1800, 250, L2)
    K.item('item_jumper', -1300, 1100, 0)
    K.station(-1800, 1300, 0, ang=315); K.station(1700, 800, L2, ang=180)
    for (x, y, z, a) in ((-1000, -200, 0, 0), (1000, 200, 0, 180), (-300, -500, 0, 90), (300, 500, 0, 270),
                         (1600, -800, 0, 135), (-1600, 800, 0, 315), (-700, 1250, 0, 270),
                         (-1200, 950, L1, 0), (1200, -1000, L1, 90), (0, 1100, L1, 270), (0, -1100, L1, 90),
                         (-800, 600, L2, 0), (1100, 650, L2, 180), (-1100, -500, L2, 90),
                         (-1000, -1250, L3, 0), (1000, -1250, L3, 180), (-1300, 1350, L3, 0)):
        K.spawn(x, y, z, a)


# ------------------------------------------------------------------------------------------------ round 2: alive
JOIST_Z = ZC - 64                                    # underside of the oak ceiling joists (x = -1792 + 512 k)


def hang(name, x, y, zc, light=280):
    """a hanging model (origin at its ceiling point) + a warm point light at the lantern glass"""
    place(name, x, y, zc, occupy=False)
    if light and name.startswith('lantern'):
        L = int(name.split('_')[1])
        K.light(x, y, zc - L - 70, light, '1 0.82 0.55')


def lanterns():
    """flickering oil lanterns on chains under every ceiling: slab undersides on the lower levels, the joists above"""
    for (x, y) in ((-1000, 900), (1000, -900), (-1000, -860), (300, 1050), (-300, -1000), (1650, -300), (-1750, 0),
                   (1150, 900), (-1650, 1250), (1650, 1250)):
        hang('lantern_60', x, y, L1 - SL)                        # ground floor, under the Gallery slab
    for (x, y) in ((-1100, 400), (1100, -400), (-700, 1200), (700, 950), (-1600, -400), (1650, 600), (-1500, 1150)):
        hang('lantern_120', x, y, L2 - SL)                       # Gallery, under the wings
    for (x, y) in ((-1600, -1250), (1600, -1250), (350, -1300), (-350, -1300)):
        hang('lantern_640', x, y, L3 - SL)                       # Gallery south band, under the dial balcony
    for (x, y) in ((-1792, 300), (-1280, -350), (1280, -350), (1792, 600), (768, 450), (-768, -560), (256, 600), (256, -600),
                   (1280, 820)):
        hang('lantern_640', x, y, JOIST_Z, light=380)            # wings + atrium, from the joists
    for (x, y) in ((-1280, -1250), (-256, -1250), (256, -1250), (1280, -1250), (-1792, 1350), (256, 1350), (1280, 1350)):
        hang('lantern_400', x, y, JOIST_Z, light=320)            # dial balcony + cuckoo ledge


def wall_clocks():
    """little round wall clocks on every level, each with its own turning hands (and its own wrong time)"""
    clocks = [  # (wall, along, z, minute speed)
        ('n', -1300, 400, 12), ('e', 1250, 380, 9), ('w', -500, 400, 15), ('s', 1300, 380, 10),
        ('w', 1000, 1000, 8), ('e', -1000, 1000, 14), ('n', -1500, 1000, 11),
        ('n', -150, 1620, 7), ('e', 1050, 1700, 13), ('w', -600, 1700, 9),
        ('n', 350, 2300, 10), ('n', 1550, 2300, 16), ('s', -1500, 2300, 12), ('s', 1500, 2300, 8)]
    for i, (w, a, z, sp) in enumerate(clocks):
        if w == 'n': pos, ang, axis, hp = (a, Y1, z), 0, 'y', (a, Y1 - 32, z)
        elif w == 's': pos, ang, axis, hp = (a, Y0, z), 180, 'y', (a, Y0 + 32, z)
        elif w == 'e': pos, ang, axis, hp = (X1, a, z), 270, 'x', (X1 - 32, a, z)
        else: pos, ang, axis, hp = (X0, a, z), 90, 'x', (X0 + 32, a, z)
        place('wallclock', pos[0], pos[1], pos[2], ang, occupy=False)
        rev = w in ('s', 'w')            # hands turn clockwise as seen from the room
        K.rotating_model2(f'models/{NS}/shand_m_{axis}.md3', hp, sp, axis=axis, reverse=rev)
        K.rotating_model2(f'models/{NS}/shand_h_{axis}.md3', (hp[0] + (0.01 if axis == 'y' else 0), hp[1], hp[2]),
                          sp / 12, axis=axis, reverse=rev)
        if i % 3 == 0: K.speaker(*hp, 'machine/clock_ticking', volume=0.4)


def small_gears():
    """pairs of little meshing gears turning on brackets high on the walls (out of reach, so no clip needed)"""
    pairs = [('w', 700, 420), ('s', 900, 440), ('e', 900, 1060), ('w', -1100, 1040), ('n', 900, 1660), ('e', 1100, 1660),
             ('e', -1250, 2350), ('w', 1350, 2350), ('n', -1400, 440)]
    for (w, a, z) in pairs:
        for k, (m, r) in enumerate((('1', 130), ('2', 90))):
            off = 0 if k == 0 else 130 + 90 - 12
            sp = 14 if k == 0 else 14 * 130 / 90
            if w in ('n', 's'):
                y = Y1 - 22 if w == 'n' else Y0 + 22
                K.rotating_model2(f'models/{NS}/gear_t{m}.md3', (a + off, y, z), sp, axis='y', reverse=bool(k))
            else:
                x = X1 - 22 if w == 'e' else X0 + 22
                K.rotating_model2(f'models/{NS}/gear_t{"3" if k == 0 else "4"}.md3', (x, a + off, z), sp, axis='x', reverse=bool(k))


def drive_shaft():
    """the leading-off rod: from the movement's south plate to the dial, turning with the minute hand"""
    K.rotating_model2(f'models/{NS}/shaft.iqm', (0, -915, DIAL_C[2]), 6, axis='y')


def ext_model(path, x, y, z, angle, start=0, end=210, fps=15):
    p = 'models/mapobjects/' + path
    b = K.md3bounds()[p] if hasattr(K, 'md3bounds') else json.load(open(os.path.join(ROOT, 'md3bounds.json')))[p]
    K.ent('misc_externalmodel', (round(x), round(y), round(z - b['min'][2], 1)), model=p, angle=angle,
          animationStart=start, animationEnd=end, animationFPS=fps)


def benches():
    """watchmaker's benches with their clutter: lamps, pocket watches, chess pieces, nuts, keys, bottles"""
    for (x, y, z, a) in ((250, 1380, 0, 0), (-800, 1400, L1, 0), (-900, 1390, L2, 0), (1300, 620, L2, 0)):
        c = PM.COLL['bench']
        if K.custom(ML.PLACE['bench'], x, y, z, a, boxes=c['boxes']) is None: continue
        top = z + 112
        s = 1 if a == 0 else -1
        K.catalog('pad_lamps/small_gooseneck.md3', x - s * 110, y + s * 20, top, angle=a + 90, nudge=False, clip=False)
        place('watch', x - s * 10, y - s * 10, top, occupy=False)
        K.catalog('pad_ddmix/backyard/screw_nut.md3', x + s * 60, y - s * 30, top, angle=30, nudge=False, clip=False)
        K.catalog('pad_ddmix/door/ancient_key_lying.md3', x + s * 30, y + s * 40, top, angle=a + 80, nudge=False, clip=False)
        K.catalog(('pad_ddmix/chess/chess_white_king.md3', 'pad_ddmix/padship/rumbottle1.md3', 'pad_ddmix/jail/matches_opened.md3',
                   'pad_ddmix/diner/tunnellamp.md3')[int(abs(x + y)) % 4], x + s * 120, y, top, angle=a, nudge=False, clip=False)


def clutter():
    """a lot more stuff on every level: hourglasses, oil barrels, toolboxes, springs, big pocket watches, old clock
    faces, paint tins, winding keys, nuts, ravens, spiders, webs - placed where the paths leave room"""
    P = [  # (model, x, y, z, angle or None)
        ('hourglass', -150, -1300, 0, None), ('hourglass', 900, -950, L1, None), ('hourglass', -900, -1100, L3, None),
        ('hourglass', 900, -1100, L3, None), ('hourglass', 1150, 1360, L3, None), ('hourglass', -1300, 300, L2, None),
        ('barrels', -1800, -380, 0, None), ('barrels', 1700, 1300, L1, None), ('barrels', -1650, -450, L2, None),
        ('barrels', 300, -1300, 0, None),
        ('toolbox', -560, 1300, 0, 20), ('toolbox', 1700, -460, L1, 90), ('toolbox', 420, 850, L2, 200),
        ('bigspring', 1700, -1000, 0, 0), ('bigspring', -1750, 1300, L1, 0), ('bigspring', 1250, -480, L2, 0),
        ('bigspring', -1800, 1380, L3, 0),
        ('bigwatch', 0, 1360, 0, 0), ('bigwatch', 0, -1360, L1, 180), ('bigwatch', 300, 1390, L2, 20),
        ('oldface', -1250, Y1 - 64, 0, 0), ('oldface', X0 + 64, -1150, L1, 90), ('oldface', X1 - 64, 900, L2, 270),
        ('oldface', 1150, Y0 + 64, L1, 180),
        ('crate96', -1250, -300, 0, None), ('crate96', 700, 560, L2, None), ('crates', 1000, -1300, L3, 90),
        ('gearstack_s', 1000, -350, 0, 0),
    ]
    for (n, x, y, z, a) in P:
        prop(n, x, y, z, angle=a, search=160)
    C = [  # catalog (path, x, y, z, scale, angle)
        ('pad_tins/pad_paint1.md3', -1100, 300, 0, 1.0, 20), ('pad_tins/pad_paint2_tl.md3', -1180, 380, 0, 1.0, 70),
        ('pad_tins/pad_paint1_tl.md3', 1500, 400, L1, 1.0, 10), ('pad_tins/pad_paint2.md3', -500, 900, L2, 1.0, 50),
        ('pad_ddmix/door/ancient_key_lying.md3', 1050, 300, 0, 4.0, 15),
        ('pad_ddmix/door/ancient_key_lying.md3', 1000, 1380, L2, 4.0, 95),
        ('pad_ddmix/backyard/screw_nut.md3', 700, -1350, 0, 3.0, 10), ('pad_ddmix/backyard/screw_nut.md3', -1350, 1000, L1, 3.0, 40),
        ('pad_ddmix/backyard/screw_nut.md3', 300, 1400, L3, 3.0, 70), ('pad_ddmix/backyard/screwnut_thin.md3', 1400, -900, 0, 3.0, 0),
        ('pad_ddmix/cabin/telescope.md3', -1300, -1320, L3, 1.0, 270),
        ('pad_ddmix/gallery/fire_extinguisher.md3', -1150, -1250, 0, 2.0, 0), ('pad_ddmix/gallery/fire_extinguisher.md3', 1850, 1000, L2, 2.0, 180),
        ('pad_ducks/pad_duck.md3', -1100, 1000, L2, 1.0, 300), ('ente/padstatue_gold.md3', 1350, 1360, L3, 1.0, 270),
        ('pad_ddmix/padship/shiplamp.md3', -1900, -1400, 0, 1.0, 0), ('pad_ddmix/padship/shiplamp.md3', 1900, 1400, L1, 1.0, 0),
        ('pad_books/rhodan/pdr_4books.md3', 1600, -450, L2, 1.0, 30), ('pad_books/rhodan/pdr_1book_fl.md3', -800, -1250, L1, 1.0, 60),
        ('pad_books/pad_cb_fl_lg.md3', 1900, -1400, L3, 1.0, 90), ('pad_cups/pad_cup03.md3', 1500, -1200, L3, 1.0, 200),
        ('pad_ddmix/padlibrary/pipe.md3', -300, 1380, L2, 1.0, 0), ('pad_train/hammer.md3', 760, 1400, 0, 1.0, 90),
        ('pad_ddmix/padship/rumbottle2.md3', -1880, 600, L1, 1.0, 0),
    ]
    for (p, x, y, z, sc, a) in C:
        K.catalog(p, x, y, z, scale=sc, angle=a)
    for (x, y, z, a) in ((360, 270, DECK, 200), (1300, 1250, 128, 260), (-1650, -1180, PM.BARREL['h'], 30),
                         (-1150, 1250, L2 + CHIME_H + 16, 180)):
        ext_model('animated/raven_sitting_2_small.md3', x, y, z, a)
    for (x, y, z, a) in ((-700, 600, 0, 30), (1500, 1000, L1, 200), (900, -1300, L3, 120), (-1700, 900, L2, 80)):
        K.catalog('spider/spiderf.md3', x, y, z, angle=a, clip=False)
    # corner cobwebs: tower ceiling corners and the corners under each slab
    for (x, y, a) in ((X0, Y0, 0), (X1, Y0, 90), (X1, Y1, 180), (X0, Y1, 270)):
        place('cobweb', x, y, ZC, a, lit=False, occupy=False)
        place('cobweb', x, y, L1 - SL, a, lit=False, occupy=False)
    for (x, y, a) in ((X0, Y1, 270), (X1, Y1, 180)):
        place('cobweb', x, y, L2 - SL, a, lit=False, occupy=False)              # Gallery corners under the wings
    for (x, y, a) in ((X0, Y0, 0), (X1, Y0, 90)):
        place('cobweb', x, y, L3 - SL, a, lit=False, occupy=False)              # under the dial balcony
    # big weights hanging high in the wings, the chimes over the chime-house roof
    for (x, y) in ((-768, -250), (768, -250), (1792, 950), (-1792, -350)):
        hang('weight_hang', x, y, JOIST_Z)
    hang('chimes', -1280, 1050, JOIST_Z)
    K.timer_sound(0, -1300, 2300, 'animal/bird_owl1', 'owl', 40, 25, volume=0.5)
    K.timer_sound(0, 900, 700, 'ambient/floor_creaking', 'creak', 25, 15, volume=0.6)


def lights():
    atrium = lambda x, y: abs(x) < AX and abs(y) < AY
    K.light_grid(X0, Y0, X1, Y1, 400, 640, 650, color='1 0.9 0.75')
    K.light_grid(X0, Y0, X1, Y1, L1 + 380, 640, 650, color='1 0.9 0.75', skip=atrium)
    K.light_grid(X0, -AY, X1, Y1, L2 + 520, 768, 1100, color='1 0.88 0.72', skip=atrium)
    K.light_grid(X0, Y0, X1, -960, L3 + 380, 700, 800, color='1 0.88 0.7')
    K.light_grid(X0, 1152, X1, Y1, L3 + 380, 700, 800, color='1 0.88 0.7')
    K.light(0, 0, 1640, 900, '1 0.85 0.6'); K.light(0, 0, 600, 900, '1 0.85 0.6')
    K.light(-300, 0, DECK + 120, 500); K.light(0, 0, CROWN + 150, 500)
    K.light(BARREL_C[0], BARREL_C[1], 260, 400)
    K.light(-1400, 1030, L2 + 200, 450)
    # fill lights where light_check found dark floor (barrel inside + lid, bridges, under the bell, corners)
    for (x, y, z, v) in ((-1560, -1170, 200, 450), (-1850, -1250, 300, 350), (-1500, -1170, 560, 300), (0, 900, 2100, 400),
                         (0, -800, 2100, 400), (250, 150, 2180, 400), (-250, -150, 2180, 300), (-1400, 1420, 1450, 380),
                         (-800, 950, 400, 320), (1800, -850, 400, 320), (1750, 300, 1500, 420), (1250, 900, 1050, 320),
                         (1800, 1400, 1050, 320), (-1800, 1400, 1050, 320), (-1800, -1400, 1050, 320)):
        K.light(x, y, z, v, '1 0.86 0.62')


def shader():
    TX.write_shader(extra=[SH.sky('env/pc-friday-13th-512', sun=(270, 30), sun_rgb=(0.7, 0.75, 1), sun_int=40, skylight=(30, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    PM.textures(TX)
    PM.models(TX)
    shell(); levels(); partitions(); rails(); movement_and_bell(); dial(); wall_gears()
    barrel(); chime_house(); cuckoo(); vault(); pads()
    items(); benches(); props()
    lanterns(); wall_clocks(); small_gears(); drive_shaft(); clutter()
    lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
