#!/usr/bin/env python3
"""PadHamster (wop_padhamster) - FFA in a sunny pet shop at Padman scale, built on woplib + texlib.

    OUT=<dir> python3 build_padhamster.py          (wopbuild.py padhamster preview / all)

Room x -2048..2048, y -1792..1792 (north = +y), floor 0, ceiling 2048. Levels: floor 0, burrow cage 480, carrier roof
520, counter 560, bird cabinet 700, sill 760, cat tree 400/800/1200, wheel cage 960, mid shelf 1160, penthouse 1440,
bird cage roof 1500, bottle shelf 1760. Layout constants in hm_layout.py, models in hm_models.py, design in README.md.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, cyl, hull, sign_box, sub_rects, stairs
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL
import hm_models as HM
from hm_layout import *

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '30', '_color': '1 0.98 0.94'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
M_ = HM.M_


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def tf(top, side=None, bot=None, tile=256.0, skip=None):
    """solid_piece texture function: material keys for tops / sides / bottoms, planar never-mirrored UVs"""
    def f(c, n, poly):
        if skip and skip(c, n): return None
        k = top if n[2] > 0.7 else (bot or side or top) if n[2] < -0.7 else (side or top)
        return M_[k], ML.planar_uv(n, tile)
    return f


def place(name, x, y, z, angle=0, **kw):
    c = HM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def prop(name, x, y, z, angle=0):
    """custom MD3 at the nearest spot where its rotated collision fits (K.prop)"""
    c = HM.COLL.get(name, {})
    return K.prop(ML.PLACE[name], x, y, z, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), angle=angle)


def md3_stairs(name, x0, y0, x1, y1, z0, ztop, d, texfn, route=None):
    """16u-riser stairs whose visible faces are an MD3 and whose collision is the same step brushes (weapclip)"""
    st = stairs(x0, y0, x1, y1, z0, ztop, d, 'x/x', step_h=16)
    K.solid_piece(name, st, texfn)
    K.spots['stairs'].append(dict(rect=[x0, y0, x1, y1], z0=z0, ztop=ztop, dir=d, name=route))
    if route:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        v = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[d]
        half = ((y1 - y0) if d in 'ns' else (x1 - x0)) / 2
        K.route(route, (cx - v[0] * (half + 48), cy - v[1] * (half + 48), z0), (cx + v[0] * (half + 48), cy + v[1] * (half + 48), ztop))
    return st


def collar(cx, cy, z, h=COLLAR_H, hole=HOLE, t=8):
    """invisible weapclip collar round a lift hole so nobody drops back into the tube"""
    a, b = hole, hole + t
    for mn, mx in (((cx - b, cy - b, z), (cx + b, cy - a, z + h)), ((cx - b, cy + a, z), (cx + b, cy + b, z + h)),
                   ((cx - b, cy - a, z), (cx - a, cy + a, z + h)), ((cx + a, cy - a, z), (cx + b, cy + a, z + h))):
        K.add(box(mn, mx, WCLIP))
    K.occupy(cx - b, cy - b, cx + b, cy + b, z, z + h)


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """one structural hull: floor, walls (window + sealed sunny sky box in the south wall), ceiling"""
    K.add(box((X0 - 32, Y0 - 32, -32), (X1 + 32, Y1 + 32, 0), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZC), tex6(e=T('wall')), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZC), tex6(s=T('wall')), detail=False))
    K.sky_window((X0, Y0 - 32, 0), (X1, Y0, ZC), WIN, T('wall'), T('sky'), jamb_tex=T('frame'), glass_tex=T('glass'), face='n')
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # fluorescent strip lights on the ceiling
    for x in (-1400, -500, 400, 1300):
        for y in (-1100, 0, 1000):
            K.add(box((x - 192, y - 12, ZC - 10), (x + 192, y + 12, ZC), {'bot': T('tubelight'), 'side': T('frame'), 'top': CAULK}))
    # signs and posters (fitted, never mirrored)
    K.add(sign_box((1100, Y1 - 4, 1300), (1900, Y1, 1500), T('shopsign'), 1024, 256, facing='s', edge=T('frame')))
    K.add(sign_box((X0, -500, 900), (X0 + 4, -100, 1500), T('poster_food'), 512, 768, facing='e', edge=T('frame')))
    K.add(sign_box((X1 - 4, -600, 900), (X1, -200, 1500), T('poster_adopt'), 512, 768, facing='w', edge=T('frame')))
    K.add(sign_box((1300, Y0, 900), (1700, Y0 + 4, 1500), T('poster_sale'), 512, 768, facing='n', edge=T('frame')))


def vault():
    """the Nest Vault under the world: a sealed burrow of hay with the powerups and a way back to the pet bed"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 384
    w, f = T('burrow'), T('hay')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': f, 'side': w, 'bot': w}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': w, 'side': w, 'top': w}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False),
          box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False),
          box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    place('nest', -300, 200, z, 0)
    place('hamster_plush', 300, 200, z, 200)
    K.item('item_padpower', 0, 200, z); K.item('item_revival', -380, -200, z); K.item('holdable_killerducks', 380, -200, z)
    K.item('item_armor_padshield', 0, -80, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(BED_C[0] + 40, BED_C[1], 20), angle=0, name='vault_exit')
    K.light(0, 0, z + 300, 700, '1 0.92 0.75'); K.light(-300, 0, z + 160, 300, '1 0.8 0.5'); K.light(300, 0, z + 160, 300, '1 0.8 0.5')


# ------------------------------------------------------------------------------------------------ the cage wall
def shelf_unit():
    """wooden shelf unit: side panels, three cage boards (ledge in front of each cage) with lift holes, the bottle shelf
    on top. One solid_piece: the visible MD3 and the same brushes as weapclip."""
    B = []
    top = LV[3] - BT
    B.append(box((SX0, SY0, 0), (SX0 + SPW, Y1, top), 'x/x'))
    B.append(box((SX1 - SPW, SY0, 0), (SX1, Y1, top), 'x/x'))
    holes = {960: LIFT_A, 1440: LIFT_B}
    for Lz in LV[:3]:
        B.append(box((IX0, SY0, Lz - BT), (IX1, CY0, Lz), 'x/x'))
        hl = [(holes[Lz][0] - HOLE, holes[Lz][1] - HOLE, holes[Lz][0] + HOLE, holes[Lz][1] + HOLE)] if Lz in holes else []
        for r in sub_rects((IX0, CY0, IX1, Y1), hl):
            B.append(box((r[0], r[1], Lz - BT), (r[2], r[3], Lz), 'x/x'))
    B.append(box((SX0, SY0, top), (SX1, Y1, LV[3]), 'x/x'))
    floors = {480: 'shavings', 960: 'shavings', 1440: 'hay'}

    def f(c, n, poly):
        if n[2] > 0.7 and c[1] > CY0 and round(c[2]) in floors: return M_[floors[round(c[2])]], ML.planar_uv(n, 256)
        return (M_['pine'] if abs(n[2]) > 0.7 or abs(n[1]) > 0.7 else M_['pinev']), ML.planar_uv(n, 256)
    K.solid_piece('shelf_unit', B, f)
    # slide deck at the penthouse level, west of the shelf (to the slide) and the landing on top of the sack stairs
    K.solid_piece('deck', [box((DECK[0], DECK[1], LV[2] - BT), (DECK[2], DECK[3], LV[2]), 'x/x')], tf('pine', 'pinev'))
    for Lz in LV[:3]:          # ledges: keep the walk in front of the cages free of props
        K.keep_clear(IX0, SY0, IX1, CY0, Lz, Lz + 96)


def cages():
    """three cages: tray rim (weapclip) + wire (clip: shots fly through), open doors to the ledges"""
    common = dict(sides='nsew', clip_sides='s', rim=40, tile=32.0)
    mnx, mxx, myy = IX0 + 2, IX1 - 2, Y1 - 2
    K.cage_box('cage_burrow', (mnx, CY0, LV[0]), (mxx, myy, LV[1] - BT), M_['wire'], rim_sh=M_['tray_blue'],
               doors=[('s', -1600, -1440), ('s', 200, 360)], **common)
    K.cage_box('cage_wheel', (mnx, CY0, LV[1]), (mxx, myy, LV[2] - BT), M_['wire'], rim_sh=M_['tray_pink'],
               doors=[('s', -400, -240), ('s', 160, 320)], **common)
    K.cage_box('cage_pent', (mnx, CY0, LV[2]), (mxx, myy, LV[3] - BT), M_['wire'], rim_sh=M_['tray_purple'],
               doors=[('s', -1640, -1480), ('s', 200, 360)], **common)
    for (a, b), Lz in ((((-1600, -1440)), LV[0]), ((200, 360), LV[0]), ((-400, -240), LV[1]), ((160, 320), LV[1]),
                       ((-1640, -1480), LV[2]), ((200, 360), LV[2])):
        K.keep_clear(a - 16, CY0, b + 16, CY0 + 112, Lz)
        K.route(f'door_{Lz}_{a}', ((a + b) / 2, SY0 + 64, Lz), ((a + b) / 2, CY0 + 120, Lz))


def lifts():
    """two glass tube lifts up through the boards (pads, never ladders), collars round the holes above"""
    g, r = M_['glass'], M_['chrome']
    ax, ay = LIFT_A
    K.tube_lift(ax, ay, LV[0], (ax - 220, ay, LV[1]), 1300, 'lift_a', g, r, top=LV[1] + COLLAR_H, r=64, mouth=r,
                ceiling=LV[2] - BT, edges=[(ax - HOLE - 8, ay, LV[1] + COLLAR_H)])
    collar(ax, ay, LV[1])
    bx, by = LIFT_B
    K.tube_lift(bx, by, LV[1], (bx + 230, by, LV[2]), 1680, 'lift_b', g, r, top=LV[2] + COLLAR_H, r=64, mouth=r,
                ceiling=LV[3] - BT, edges=[(bx + HOLE + 8, by, LV[2] + COLLAR_H)])
    collar(bx, by, LV[2])
    K.light(ax, ay, LV[0] + 300, 250, '0.8 0.9 1'); K.light(bx, by, LV[1] + 300, 250, '0.8 0.9 1')


def burrow():
    z = LV[0]
    x0, x1, ty = TUNNEL
    place('tunnel', (x0 + x1) / 2, ty, z)
    K.crawl((x0, ty - 44, z), (x1, ty + 44, z + 48))
    K.keep_clear(x0 - 96, ty - 48, x0, ty + 48, z); K.keep_clear(x1, ty - 48, x1 + 96, ty + 48, z)
    K.route('tunnel', (x0 - 64, ty, z), (x1 + 64, ty, z))
    nx, ny = NEST_C
    place('nest', nx, ny, z)
    place('hopper', -1250, 1700, z)
    place('bowl', -1080, 1690, z); place('bowl', 60, 1700, z)
    place('humps', -300, 1600, z); place('humps', -1300, 1480, z, 180)
    place('chew_blocks', 120, 1520, z, 20)
    for (x, y, a) in ((-200, 1700, 30), (-420, 1660, 100), (650 - 60, 1740, 0)):
        K.catalog('pad_fruits/hazelnut.md3', x, y, z, angle=a, clip=False)
    K.catalog('pad_toiletroll/pad_toiletroll.md3', -500, 1480, z, angle=90)
    K.catalog('pad_fruits/apple.md3', 300, 1720, z, clip=False)
    K.light(-800, 1600, z + 330, 380, '1 0.95 0.85'); K.light(200, 1600, z + 330, 380, '1 0.95 0.85')
    K.light(-1300, 1500, z + 330, 260, '1 0.95 0.85')         # the nest corner stays the darkest


def wheel_cage():
    z = LV[1]
    wx, wy = WHEEL_C; zc = z + WHEEL_R + 24
    K.rotating_model2(f'models/{NS}/wheel.md3', (wx, wy, zc), 45, axis='y')
    place('wheel_stand', wx, wy, z)
    # clip round the spinning wheel (players can't walk into it; shots fly through the rungs)
    pts = []
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8; rr = (WHEEL_R + 10) / math.cos(math.pi / 8)
        for y in (wy - 70, wy + 70): pts.append((wx + rr * math.cos(a), y, zc + rr * math.sin(a)))
    K.add(box((wx - WHEEL_R - 12, wy - 70, z), (wx + WHEEL_R + 12, wy + 70, LV[2] - BT), CLIP))   # whole column: no crouch slots
    K.occupy(wx - WHEEL_R - 20, wy - 80, wx + WHEEL_R + 20, wy + 92, z, zc + WHEEL_R + 20)
    K.speaker(wx, wy, zc, 'machine/mechanics', volume=0.5)
    # hide-house (walk in through the south door, 16u chew-block stairs onto its flat roof)
    hx0, hy0, hx1, hy1 = HOUSE; h = HOUSE_H; t = 16
    d0, d1 = hx0 + 100, hx0 + 196
    hb = [box((hx0, hy0, z), (hx0 + t, hy1, z + h - t), 'x/x'), box((hx1 - t, hy0, z), (hx1, hy1, z + h - t), 'x/x'),
          box((hx0 + t, hy1 - t, z), (hx1 - t, hy1, z + h - t), 'x/x'),
          box((hx0 + t, hy0, z), (d0, hy0 + t, z + h - t), 'x/x'), box((d1, hy0, z), (hx1 - t, hy0 + t, z + h - t), 'x/x'),
          box((d0, hy0, z + 128), (d1, hy0 + t, z + h - t), 'x/x'),
          box((hx0 - 8, hy0 - 8, z + h - t), (hx1, hy1, z + h), 'x/x')]
    K.solid_piece('hide_house', hb, tf('chew', 'pinev'))
    K.keep_clear(d0 - 16, hy0 - 112, d1 + 16, hy0 + 96, z)
    K.route('house_door', ((d0 + d1) / 2, hy0 - 90, z), ((d0 + d1) / 2, hy0 + 100, z))
    md3_stairs('house_stairs', hx1, 1680, hx1 + 13 * 32, Y1 - 16, z, z + h, 'w', tf('chew', 'chew'), route='house_roof')
    K.keep_clear(hx1 + 13 * 32, 1660, hx1 + 13 * 32 + 96, Y1 - 16, z)
    K.light(-1056, 1640, z + 150, 180, '1 0.9 0.7')
    K.light(-600, 1580, z + 330, 380, '1 0.95 0.85'); K.light(300, 1600, z + 330, 380, '1 0.95 0.85')
    K.catalog('pad_ball/pad_tennisball.md3', 520, 1720, z, clip=False)
    place('bowl', -700, 1520, z)


def penthouse():
    z = LV[2]
    place('hammock', 80, 1640, z)
    place('chew_blocks', -300, 1630, z, 75)
    K.catalog('pad_toiletroll/pad_toiletroll.md3', -900, 1680, z, angle=0)
    K.catalog('pad_toiletroll/pad_toiletroll.md3', 450, 1700, z, angle=40)
    K.catalog('pad_fruits/walnut.md3', -800, 1500, z, clip=False)
    place('bowl', -1100, 1700, z)
    K.light(-900, 1600, z + 220, 320, '1 0.95 0.85'); K.light(100, 1560, z + 220, 320, '1 0.95 0.85')


def bottle_shelf():
    z = LV[3]
    for x in (-1100, -300, 300):
        place('bottle', x, 1600, z)
    K.catalog('pad_books/pad_cb_fl_lg.md3', -700, 1620, z, angle=10)
    K.catalog('pad_tins/carrots_tl.md3', -1500, 1650, z, angle=20)
    K.catalog('pad_ducks/pad_duck.md3', 560, 1660, z, angle=220)


# ------------------------------------------------------------------------------------------------ feed corner + slide
def feed_corner():
    x0, y0, x1, y1 = STAIR
    sack = tf('burlap', 'burlap', tile=128)
    md3_stairs('sack_stairs', x0, y0, x1, y1, 0, LV[0], 'n', sack, route='sack_stairs')
    lx0, ly0, lx1, ly1 = LANDING
    K.solid_piece('sack_landing', [box((lx0, ly0, 0), (lx1, ly1, LV[0]), 'x/x')], tf('burlap', 'burlap_label', tile=256))
    K.keep_clear(x0, y0 - 112, x1, y0, 0)
    K.keep_clear(lx0, ly0, lx1, ly1, LV[0])
    K.route('to_burrow', ((lx0 + lx1) / 2 + 100, ly0 + 80, LV[0]), (-1520, CY0 + 140, LV[0]))
    place('sack_pile', -1620, 300, 0, 0)
    place('sack_pile', -1620, 640, 0, 10)
    # feed bin (walk in from the east; open top)
    fx0, fy0, fx1, fy1 = FEEDBIN; h = FEEDBIN_H; t = 20
    fb = [box((fx0, fy0, 0), (fx0 + t, fy1, h), 'x/x'), box((fx0 + t, fy0, 0), (fx1, fy0 + t, h), 'x/x'),
          box((fx0 + t, fy1 - t, 0), (fx1, fy1, h), 'x/x'),
          box((fx1 - t, fy0 + t, 0), (fx1, fy0 + 80, h), 'x/x'), box((fx1 - t, fy1 - 80, 0), (fx1, fy1 - t, h), 'x/x'),
          box((fx1 - t, fy0 + 80, 240), (fx1, fy1 - 80, h), 'x/x')]
    K.solid_piece('feed_bin', fb, tf('bin', 'bin'))
    K.keep_clear(fx1, fy0 + 60, fx1 + 112, fy1 - 60, 0)
    K.route('feed_bin', (fx1 + 90, (fy0 + fy1) / 2, 0), (fx1 - 100, (fy0 + fy1) / 2, 0))
    K.catalog('pad_fruits/walnut.md3', fx0 + 90, fy0 + 90, 0, clip=False)
    K.catalog('pad_fruits/hazelnut.md3', fx0 + 140, fy1 - 90, 0, clip=False)


def slide():
    """glass slide tube from the penthouse deck down the west wall (slick, 39 deg)"""
    K.slide(SLIDE, 48, 64, T('slide'))
    X = ML.Model()
    path = [np.array(p, float) + [0, 0, 44] for p in SLIDE]
    dense = []
    for i in range(len(path) - 1):
        for f in np.linspace(0, 1, 8, endpoint=False): dense.append(path[i] + (path[i + 1] - path[i]) * f)
    dense.append(path[-1])
    ML.glass_tube(X, dense, 62, M_['glass'], M_['chrome'], ring_every=320)
    o = np.array([SLIDE_X, 0.0, 0.0])
    X.shift(o)
    K.custom(ML.save('slide_tube', X), SLIDE_X, 0, 0, lit=False, occupy=False)
    for y in (0, 500):                 # supports under the slide
        zz = 16 + (y + 720) / 1776 * 1424 - 40
        K.solid_piece(f'slide_post{y}', [box((SLIDE_X - 20, y - 20, 0), (SLIDE_X + 20, y + 20, round(zz) - 4), 'x/x')], tf('steel', 'steel'))
    K.keep_clear(SLIDE_X - 60, -1000, SLIDE_X + 60, -880, 0)
    # fill under the low end of the slide (it left a crouch-only slot): a wedge following the slide floor's underside
    y0, y1 = -720, -300
    zt = lambda y: (y + 720) / 1776 * 1424
    wedge = hull([(SLIDE_X + sx, y, 0) for sx in (-56, 56) for y in (y0, y1)] +
                 [(SLIDE_X + sx, y, zt(y)) for sx in (-56, 56) for y in (-720, y1)], 'x/x', round_pts=False)
    K.solid_piece('slide_foot', [wedge], tf('steel', 'white'))
    K.keep_clear(DECK[0], DECK[1], DECK[2], DECK[3], LV[2])


# ------------------------------------------------------------------------------------------------ counter
def counter():
    x0, y0, x1, y1 = COUNTER; z = COUNTER_Z; t = 32
    cb = [box((x0, y0, z - t), (x1, y1, z), 'x/x'), box((x0, y0, 0), (x1, y0 + t, z - t), 'x/x'),
          box((x0, y0 + t, 0), (x0 + t, y1, z - t), 'x/x'), box((x0 + t, y0 + t, 240), (x1, y1 - 64, 256), 'x/x')]
    K.solid_piece('counter', cb, tf('white', 'pinev'))
    K.keep_clear(x0 + 40, y1 - 64, x1, Y1, 0)         # the back aisle + under-counter compartments
    K.route('under_counter', (1600, 1600, 0), (1600, 1150, 0))
    # till with the open cash drawer (walk in: 8u floor, 16u rim)
    place('till', 1640, 1170, z)
    dx0, dx1, dy0, dy1 = 1520, 1760, 1020, 1168
    db = [box((dx0, dy0, z), (dx1, dy1, z + 8), 'x/x'),
          box((dx0, dy0, z + 8), (dx0 + 8, dy1, z + 24), 'x/x'), box((dx1 - 8, dy0, z + 8), (dx1, dy1, z + 24), 'x/x'),
          box((dx0 + 8, dy0, z + 8), (dx1 - 8, dy0 + 8, z + 24), 'x/x')]
    K.solid_piece('cash_drawer', db, tf('coins', 'till'))
    place('treat_jar', 1200, 1300, z)
    K.catalog('pad_pc/padshop_tft.md3', 1940, 1000, z, angle=200)
    K.light(1500, 1150, z + 400, 450)
    # mid shelf over the back aisle (second stage of the express lift)
    mx0, my0, mx1, my1 = MIDSHELF
    K.solid_piece('mid_shelf', [box((mx0, my0, MID_Z - BT), (mx1, my1, MID_Z), 'x/x')], tf('pine', 'pinev'))
    for x in (900, 1680):
        K.catalog('pad_tins/carrots_tl.md3', x, 1720, MID_Z, angle=10)
    K.catalog('pad_tins/tomatoes_tl.md3', 1250, 1730, MID_Z, angle=100)


# ------------------------------------------------------------------------------------------------ cat tree
def cat_tree():
    b = CT_BASE; p1, p2, p3 = CT_P1, CT_P2, CT_P3
    t = 24
    B = [box((b[0], b[1], 0), (b[2], b[3], 16), 'x/x')]
    cx0, cy0, cx1, cy1 = p1[0] + 16, p1[1] + 16, p1[2] - 16, p1[3] - 16
    o0, o1 = -280, -120                                         # the cubby opening (south face)
    B += [box((cx0, cy0, 16), (cx0 + t, cy1, P1_Z - 16), 'x/x'), box((cx1 - t, cy0, 16), (cx1, cy1, P1_Z - 16), 'x/x'),
          box((cx0 + t, cy1 - t, 16), (cx1 - t, cy1, P1_Z - 16), 'x/x'),
          box((cx0 + t, cy0, 16), (o0, cy0 + t, P1_Z - 16), 'x/x'), box((o1, cy0, 16), (cx1 - t, cy0 + t, P1_Z - 16), 'x/x'),
          box((o0, cy0, 240), (o1, cy0 + t, P1_Z - 16), 'x/x'),
          box((p1[0], p1[1], P1_Z - 16), (p1[2], p1[3], P1_Z), 'x/x'),
          box((p2[0], p2[1], P2_Z - 32), (p2[2], p2[3], P2_Z), 'x/x'),
          box((p3[0], p3[1], P3_Z - 32), (p3[2], p3[3], P3_Z), 'x/x')]
    K.solid_piece('cat_tree', B, tf('carpet', 'carpet2', tile=128))
    ax, ay, ar = POST_A; bx, by, br = POST_B
    K.custom(ML.PLACE['post_a'], ax, ay, 16, cyls=[(0, 0, ar - 4, 0, P2_Z - 32 - 16)])
    K.custom(ML.PLACE['post_b'], bx, by, P1_Z, cyls=[(0, 0, br - 4, 0, P3_Z - 32 - P1_Z)])
    K.keep_clear(o0 - 16, cy0 - 112, o1 + 16, cy0 + 120, 16)
    K.route('cubby', ((o0 + o1) / 2, cy0 - 100, 16), ((o0 + o1) / 2, cy0 + 110, 16))
    K.light(-200, -200, 200, 220, '1 0.92 0.8')
    K.catalog('pad_ball/pad_softball.md3', 300, -300, 16, clip=False)


def ball_loop():
    """translucent exercise ball rolling round the cat tree: one func_rotating at the loop centre, IQM model2,
    weapclip collision box riding with it (rotating pushers never crush)"""
    c = (0, 0, 64)
    wb = box((BALL_R - 56, -56, 16), (BALL_R + 56, 56, 128), WCLIP)
    K.ent('func_rotating', brushes=[K._origin_brush(c), wb], model2=f'models/{NS}/ball.iqm', speed=14)
    K.spots['movers'].append(dict(cls='func_rotating', centre=list(c), model='ball'))
    for k in range(32):                 # keep the swept ring free of props and pickups
        a = 2 * math.pi * k / 32
        K.occupy_r(BALL_R * math.cos(a), BALL_R * math.sin(a), 96, 0, 160)


# ------------------------------------------------------------------------------------------------ bird cage tower
def bird_tower():
    x0, y0, x1, y1 = CAB; z = CAB_Z; t = 24
    d0, d1 = -1400, -1160
    cb = [box((x0, y0, 0), (x1, y0 + t, z - t), 'x/x'), box((x0, y1 - t, 0), (x1, y1, z - t), 'x/x'),
          box((x1 - t, y0 + t, 0), (x1, y1 - t, z - t), 'x/x'),
          box((x0, y0 + t, 0), (x0 + t, d0, z - t), 'x/x'), box((x0, d1, 0), (x0 + t, y1 - t, z - t), 'x/x'),
          box((x0, d0, 320), (x0 + t, d1, z - t), 'x/x'),
          box((x0 + t, y0 + t, 300), (x1 - t, y1 - t, 320), 'x/x'),
          box((x0, y0, z - t), (x1, y1, z), 'x/x')]
    K.solid_piece('cabinet', cb, tf('white', 'pinev'))
    K.keep_clear(x0 - 112, d0 - 16, x0 + 120, d1 + 16, 0)
    K.route('cabinet_in', (x0 - 90, (d0 + d1) / 2, 0), (x0 + 110, (d0 + d1) / 2, 0))
    cx, cy = BIRD_C
    K.cage_round('bird_cage', (cx, cy), BIRD_R, z, BIRD_TOP, M_['wire'], rim_sh=M_['tray_mint'], floor_sh=M_['hay'],
                 roof_sh=M_['tray_mint'], n=16, door=(180, 150), rim=16)
    K.keep_clear(x0, cy - 90, cx - BIRD_R + 40, cy + 90, z)
    K.route('bird_door', (x0 + 60, cy, z), (cx - 60, cy, z))
    K.pendulum_model2(f'models/{NS}/perch_bird.md3', (cx + 40, cy, BIRD_TOP - 20), 20, 360)
    K.timer_sound(cx, cy, z + 300, 'animal/blackbird', 'bird_song', 14, 8)
    K.light(cx, cy, z + 500, 300, '1 0.97 0.85')
    K.catalog('pad_ddmix/plants/bonsai2.md3', x1 - 120, y0 + 130, z, scale=0.5, angle=0)


# ------------------------------------------------------------------------------------------------ pet carrier + bed
def carrier():
    x0, y0, x1, y1 = CARRIER; z = CARRIER_Z; t = 24
    d0, d1 = -1448, -1256
    cb = [box((x0, y0, 0), (x0 + t, y1, z - t), 'x/x'), box((x0 + t, y0, 0), (x1, y0 + t, z - t), 'x/x'),
          box((x0 + t, y1 - t, 0), (x1, y1, z - t), 'x/x'),
          box((x1 - t, y0 + t, 0), (x1, d0, z - t), 'x/x'), box((x1 - t, d1, 0), (x1, y1 - t, z - t), 'x/x'),
          box((x1 - t, d0, 256), (x1, d1, z - t), 'x/x'),
          box((x0, y0, z - t), (x1, y1, z), 'x/x')]
    K.solid_piece('carrier', cb, tf('carrier_top', 'carrier'))
    K.custom(ML.PLACE['grille_door'], x1 + 2, d1, 0, angle=80, occupy=False)
    K.keep_clear(x1, d0 - 16, x1 + 140, d1 + 230, 0)
    K.route('carrier_in', (x1 + 100, (d0 + d1) / 2, 0), (x1 - 120, (d0 + d1) / 2, 0))
    K.light((x0 + x1) / 2, (y0 + y1) / 2, 300, 250, '1 0.95 0.85')
    # pet bed (cushion is a 16u step, the rim dips at the front +x) and the mobile above it
    bx, by = BED_C
    K.custom(ML.PLACE['pet_bed'], bx, by, 0, occupy=False)
    K.add(cyl(bx, by, BED_R - 70, 0, 16, WCLIP, 16))
    for k in range(12):
        a0, a1 = 2 * math.pi * k / 12, 2 * math.pi * (k + 1) / 12
        if math.cos((a0 + a1) / 2) > 0.8: continue
        pts = [(bx + rr * math.cos(a), by + rr * math.sin(a)) for a in (a0, a1) for rr in (BED_R - 64, BED_R - 8)]
        K.add(hull([(p[0], p[1], 0) for p in pts] + [(p[0], p[1], 40) for p in pts], WCLIP, round_pts=False))
        K.occupy(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts), 0, 56)
    K.keep_clear(bx + BED_R - 40, by - 90, bx + BED_R + 100, by + 90, 0)
    K.rotating_model2(f'models/{NS}/mobile.iqm', (bx, by, 1400), 10)
    K.timer_sound(bx, by, 300, 'animal/kitten_meow', 'meow', 25, 15)


# ------------------------------------------------------------------------------------------------ window
def window():
    x0, y0, x1, y1 = SILL
    K.solid_piece('sill', [box((x0, y0, SILL_Z - 32), (x1, y1, SILL_Z), 'x/x')], tf('white', 'white'))
    place('basket', -700, -1680, SILL_Z, 0); place('basket', 650, -1680, SILL_Z, 90)
    K.catalog('pad_ddmix/plants/bonsai.md3', -300, -1700, SILL_Z, scale=0.6, angle=0)
    K.catalog('pad_ddmix/plants/cane2.md3', 950, -1720, SILL_Z, angle=0)
    K.keep_clear(-200, -1792, 300, -1600, SILL_Z)
    K.timer_sound(0, -1750, 1300, 'animal/dog_bark2', 'dog', 40, 25, volume=0.4)
    K.timer_sound(0, -1700, 400, 'machine/dingdong', 'chime', 50, 30)
    K.light(0, -1500, 1000, 600, '1 0.96 0.85')


# ------------------------------------------------------------------------------------------------ props + cover
def props():
    prop('food_boxes', 550, -1000, 0, 20)
    prop('can_pyramid', -1000, 650, 0, 80)
    prop('food_boxes', -900, -1100, 0, 110)
    prop('can_pyramid', 1000, 300, 0, 0)
    prop('sign_board', 300, -1300, 0, 10)
    prop('hamster_plush', 1050, -200, 0, 150)
    prop('food_boxes', 300, 1050, 0, 0)
    K.catalog('pad_ddmix/padshop/cardboard_standup.md3', 1100, -1500, 0, angle=120)
    K.catalog('pad_ducks/pad_duck.md3', -1100, 300, 0, angle=60)
    K.catalog('pad_ddmix/plants/flower_yellow.md3', 1900, -500, 0, angle=0)
    K.catalog('pad_ddmix/plants/fern.md3', 1800, 200, 0, scale=0.5, angle=0)
    K.catalog('gummybears/redbear.md3', -300, -1100, 0, angle=70)
    K.catalog('padmousetrap/padjumptrap.md3', -400, 1100, 0, angle=0, clip=False)
    K.catalog('pad_ball/pad_basketball.md3', 1200, -600, 0)
    K.catalog('pad_ddmix/backyard/tire.md3', -1000, -350, 0, angle=0)
    K.catalog('pad_tins/carrots_tl.md3', -1200, 1100, 0, angle=40)
    for (x, y) in ((-1300, 1300), (-200, 1300)):              # under the shelf unit
        K.catalog('pad_tins/pad_milk_s.md3', x, y, 0, clip=False)
    for (x, y, a) in ((600, -900, 20), (-500, 700, 120), (900, 800, 200)):
        K.catalog('pad_fruits/hazelnut.md3', x, y, 0, angle=a, clip=False)


# ------------------------------------------------------------------------------------------------ pads
def pads():
    K.jumppad(-200, -560, 0, land=(-60, -120, P1_Z), apex=P1_Z + 220, name='pad_tree1', edges=[(-130, CT_P1[1], P1_Z)])
    K.jumppad(560, 200, 0, land=(260, 150, P2_Z), apex=P2_Z + 220, name='pad_tree2', edges=[(CT_P2[2], 170, P2_Z)])
    K.jumppad(330, 330, P2_Z, land=(-170, -170, P3_Z), apex=P3_Z + 180, name='pad_tree3', edges=[(-72, -72, P3_Z)], ceiling=ZC)
    K.jumppad(-290, -290, P3_Z, land=(-320, 1300, LV[1]), apex=P3_Z + 120, name='pad_tree_wheel', ceiling=ZC,
              edges=[(-300, SY0, LV[1])])
    K.jumppad(-600, 1290, LV[3], land=(150, 220, P2_Z), apex=1950, name='pad_shelf_tree', ceiling=ZC)
    K.jumppad(300, 900, 0, land=(300, 1290, LV[0]), apex=LV[0] + 180, name='pad_burrow', edges=[(300, SY0, LV[0])])
    K.jumppad(1300, 560, 0, land=(1300, 1160, COUNTER_Z), apex=COUNTER_Z + 220, name='pad_counter',
              edges=[(1300, COUNTER[1], COUNTER_Z)])
    g, r = M_['glass'], M_['chrome']
    K.tube_lift(1880, 1330, COUNTER_Z, (1880, 1700, MID_Z), MID_Z + 160, 'lift_mid', g, r, arc=True, mouth=r,
                ceiling=ZC, edges=[(1880, MIDSHELF[1], MID_Z)])
    K.tube_lift(1500, 1696, MID_Z, (420, 1450, LV[3]), 1930, 'lift_top', g, r, arc=True, mouth=r,
                ceiling=ZC, edges=[(SX1, 1560, LV[3])])
    K.jumppad(1000, -1000, 0, land=(1320, -1020, CAB_Z), apex=CAB_Z + 200, name='pad_cabinet', edges=[(CAB[0], -1010, CAB_Z)])
    K.jumppad(1320, -1560, CAB_Z, land=(1600, -1300, BIRD_TOP + 16), apex=BIRD_TOP + 220, name='pad_birdroof', ceiling=ZC,
              edges=[(1440, -1430, BIRD_TOP + 16)])
    K.jumppad(-1000, -1500, 0, land=(-1480, -1350, CARRIER_Z), apex=CARRIER_Z + 200, name='pad_carrier',
              edges=[(CARRIER[2], -1380, CARRIER_Z)])
    K.jumppad(0, -1250, 0, land=(0, -1690, SILL_Z), apex=SILL_Z + 150, name='pad_sill', edges=[(0, SILL[3], SILL_Z)])


# ------------------------------------------------------------------------------------------------ loot, spawns
def items():
    K.weapon('imperius', -300, 1752, LV[3], marker='purple')
    K.weapon('betty', -600, 1640, LV[2], marker='black')
    K.weapon('balloony', -120, -290, P3_Z, marker='orange')
    K.weapon('pumper', 1560, -1300, CAB_Z, marker='green')
    K.weapon('splasher', 1360, 1250, COUNTER_Z, marker='blue')
    K.weapon('boaster', -800, TUNNEL[2], LV[0], marker='orange')
    K.weapon('bubbleg', -1500, -1350, 0, marker='green')
    ammo = {'imperius': [(-1500, 1300, LV[0]), (1700, 1500, 0), (1150, 1700, MID_Z), (-200, -900, 0)],
            'betty': [(-1300, -1500, CARRIER_Z), (500, -1100, 0), (-1500, 1500, 0), (-1640, 1000, 0)],
            'balloony': [(250, 300, P2_Z), (-400, -480, 0), (1400, 1650, 0), (-1000, -1700, 0)],
            'pumper': [(1300, -1250, 120), (1500, 500, 0), (-1056, 1700, LV[1]), (-1300, 700, 0)],
            'splasher': [(1640, 1090, COUNTER_Z + 8), (-500, -1400, 0), (500, 1200, LV[0]), (1800, -1000, 0)],
            'boaster': [(-1460, 1730, LV[0]), (-1150, 0, 0), (700, 600, 0), (1500, 1250, 0)],
            'bubbleg': [(-1500, -140, 0), (-400, -1600, 0), (1300, 1000, 260), (1100, -900, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', 0, 1000, 0); K.ammo('nipper', 1400, -200, 0); K.ammo('nipper', -900, -700, 0)
    K.item('item_armor_padshield', -1056, 1660, LV[1])
    K.item('item_speedy', 200, -1700, SILL_Z)
    K.item('holdable_floater', 1600, -1220, BIRD_TOP + 16)
    K.item('item_armor_shard', 300, 1600, LV[2]); K.item('item_armor_shard', -1700, -200, 0)
    K.station(950, 700, 0, ang=180)
    K.station(-1100, -850, 0, ang=90)
    for (x, y, z, a) in ((-600, -1300, 0, 90), (700, -1400, 0, 90), (1500, -300, 0, 180), (-1500, 200, 0, 0),
                         (-300, 1000, 0, 270), (900, 1100, 0, 270), (1700, 100, 0, 180), (-1100, -1400, 0, 45),
                         (-1100, 1300, LV[0], 0), (-800, 1290, LV[1], 0), (400, 1290, LV[2], 180), (1500, 1100, COUNTER_Z, 180),
                         (200, -500, 0, 90), (-700, -800, 0, 45), (-1800, 1400, 0, 0), (1000, -1650, 0, 90)):
        K.spawn(x, y, z, a)


def secret():
    """walk into the darkest corner of the burrow nest -> the Nest Vault"""
    nx, ny = NEST_C
    K.secret((IX0 + 4, ny - 36, LV[0]), (IX0 + 92, Y1 - 4, LV[0] + 96), dest=(0, -200, VAULT_Z), angle=90, name='nest',
             approach='e')


def lights_sounds():
    K.light_grid(X0, Y0, X1, Y1, 1300, 768, 2600, color='1 0.98 0.92')
    K.light_grid(X0 + 200, Y0 + 200, X1 - 200, SY0 - 100, 500, 1024, 900, color='1 0.97 0.9')
    K.light(-500, 1000, 400, 500); K.light(-500, 1000, 1200, 500)      # the cage wall front
    K.light(-800, 1300, 300, 400, '1 0.95 0.85')                     # under the shelf
    K.speaker(1640, 1200, COUNTER_Z + 300, 'machine/clock_ticking')


def shader():
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(270, 50), sun_int=160, skylight=(60, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = HM.textures(K)
    HM.all_models()                    # every MD3/IQM (and its shaders) BEFORE the shader file is written
    shell(); vault(); shelf_unit(); cages(); lifts(); burrow(); wheel_cage(); penthouse(); bottle_shelf()
    feed_corner(); slide(); counter(); cat_tree(); ball_loop(); bird_tower(); carrier(); window()
    pads(); secret(); items(); props(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
