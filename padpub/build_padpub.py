#!/usr/bin/env python3
"""The Padman's Arms (wop_padpub) - FFA in a Victorian London pub, built on woplib + texlib.

    OUT=<dir> python3 build_padpub.py          (wopbuild.py padpub preview / all)

Toy scale (~5u per cm). x east, y north. Saloon bar x -1600..1600, y -1200..1600 (bar on the north wall, street door
south); the snug x -2560..-1632, y -200..1600; beer garden x -2560..-1632, y -1232..-232 (open sky); pavement
y -2100..-1232 with the road beyond. Floor 0, ceiling 1600.
Levels: floor 0 | settle seats 225 | stools 375 | tables 380 | back counter 500 | counter 550 | piano 650 |
phone box roof 1250 | gantry cornice 1360 | overmantel 1380. See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, hull, sign_box, sub_rects
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import pub_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, YP, X1, Y1 = INFO['bounds']                 # playable: -2560 -2100 1600 1600
SX0, SX1, SY0, SY1 = -1600, 1600, -1200, 1600   # saloon inner faces
YFO = -1232                                     # front wall outer face (pavement side)
NX0, NX1, NY0, NYO = -2560, -1632, -200, -232   # snug: west face, partition (snug side), south wall inner/outer
YR = -2400                                      # far side of the road
ZC, ZSKY = PM.ZC, 2300
K = MapKit(MAP, NS, LONG, (X0, YP, X1, Y1), worldspawn={'_ambient': '40', '_color': '1 0.92 0.8'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
FRONT_DOOR = (-200, 200, 900)                   # x0 x1 top
WINDOWS = ((-1400, -500), (500, 1400)); WZ = (260, 1200)
SIDE_DOOR = (-900, -620, 900)                   # saloon west wall -> garden: y0 y1 top
SNUG_DOOR = (250, 530, 900)                     # partition: y0 y1 top
BACK_DOOR = (-2300, -2020, 900)                 # snug south wall -> garden: x0 x1 top
SNUG_WIN = (-1950, -1700); SNUG_WZ = (300, 1100)
GATE = (-2300, -1900)                           # garden gate onto the pavement
CY0, CY1 = 700, 1000                            # counter front / staff side
CX0, CX1 = -1100, 900                           # straight counter run
RET_X1, RET_Y1 = 1200, 1360                     # return counter east face, back-bar front
BAYS = [(-980, 'gantry_a'), (-540, 'gantry_b'), (-100, 'gantry_c'), (340, 'gantry_b'), (780, 'gantry_a')]
GEND_X = -1400                                  # gantry end piece (x -1600..-1200)
TILES = (-1400, 300, 1300, CY0)                 # encaustic strip in front of the bar
ISLANDS = (-650, 650); ISLAND_Y = -150
FIRE_Y = 250                                    # fireplace centre on the east wall
CLOCK_Y = -800                                  # longcase clock on the east wall
VAULT = (-500, -500, 500, 500); VZ = -1800      # secret cellar
CZ, BZ, KZ = PM.COUNTER_Z, PM.BACK_Z, PM.CORNICE_Z
HEARTH = 12
OMZ = PM.OVERMANTEL_Z + HEARTH                 # the fireplace stands on the tiled hearth
PHONE = (1050, -1750)
PIANO_Y = 400


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = PM.COLL.get(name, {})
    e = K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    for h in c.get('hulls', ()):
        pts = [(round(x + px * ca - py * sa, 2), round(y + px * sa + py * ca, 2), z + pz) for (px, py, pz) in h]
        K.add(hull(pts, WCLIP, round_pts=False))
        K.occupy(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts),
                 min(p[2] for p in pts), max(p[2] for p in pts))
    return e


def deco(name, x, y, z, angle=0, **kw):
    """a custom MD3 with no collision (wall-mounted / overhead / tiny tabletop things)"""
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


def wall(axis, c0, c1, s0, s1, z0, z1, faces, openings=(), detail=False):
    """structural wall slab, thickness c0..c1 across `axis` ('y': runs along x, faces n/s; 'x': runs along y, faces
    e/w), length s0..s1, height z0..z1, split round openings [(a, b, zlo, zhi)]; jambs, sills, lintels get T('jamb')"""
    jt = T('jamb')
    lo_face, hi_face = ('w', 'e') if axis == 'y' else ('s', 'n')
    cuts = sorted({s0, s1} | {o[0] for o in openings} | {o[1] for o in openings})
    for a, b in zip(cuts, cuts[1:]):
        hole = [o for o in openings if o[0] <= a and o[1] >= b]
        spans = [(z0, z1)] if not hole else [(z0, hole[0][2]), (hole[0][3], z1)]
        for (za, zb) in spans:
            if zb - za < 1: continue
            t = tex6(**faces)
            if hole:
                if za > z0: t['bot'] = jt
                if zb < z1: t['top'] = jt
            else:
                if any(abs(o[0] - b) < 0.5 for o in openings): t[hi_face] = jt
                if any(abs(o[1] - a) < 0.5 for o in openings): t[lo_face] = jt
            K.add(box((a, c0, za), (b, c1, zb), t, detail=detail) if axis == 'y' else box((c0, a, za), (c1, b, zb), t, detail=detail))


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: floors, walls with door/window openings, ceilings, the outdoor sky box. Everything else is detail."""
    S = T('sky')
    fl = lambda top: {'top': top, 'side': CAULK, 'bot': CAULK}
    # floors: boards with the encaustic strip in front of the bar; snug boards; garden flags; pavement; road
    for r in sub_rects((SX0 - 32, SY0, SX1 + 32, SY1 + 32), [TILES]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), fl(T('boards')), detail=False))
    K.add(box((TILES[0], TILES[1], -32), (TILES[2], TILES[3], 0), fl(T('encaustic')), detail=False))
    K.add(box((SX0 - 32, YFO, -32), (SX1 + 32, SY0, 0), fl(T('stone')), detail=False))            # thresholds
    K.add(box((NX0 - 32, NYO, -32), (SX0 - 32, SY1 + 32, 0), fl(T('boards')), detail=False))
    K.add(box((NX0 - 32, YFO, -32), (SX0 - 32, NYO, 0), fl(T('flags')), detail=False))
    K.add(box((NX0 - 32, YP, -32), (SX1 + 32, YFO, 0), {'top': T('pavement'), 'side': T('kerb'), 'bot': CAULK}, detail=False))
    K.add(box((NX0 - 32, YR, -48), (SX1 + 32, YP - 8, -16), fl(T('road')), detail=False))
    K.add(box((NX0 - 32, YP - 8, -48), (SX1 + 32, YP, 0), tex6(top=T('kerb'), s=T('kerb')), detail=False))
    # saloon north + east walls, snug north + west walls
    K.add(box((SX0, SY1, 0), (SX1 + 32, SY1 + 32, ZC), tex6(s=T('wall')), detail=False))
    K.add(box((SX1, SY0, 0), (SX1 + 32, SY1, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((NX0 - 32, SY1, 0), (SX0, SY1 + 32, ZC), tex6(s=T('wall_snug')), detail=False))
    K.add(box((NX0 - 32, NY0, 0), (NX0, SY1, ZC), tex6(e=T('wall_snug')), detail=False))
    # front wall: the band with the door and two windows, the band to the ceiling, the facade above the ceiling
    wall('y', YFO, SY0, SX0 - 32, SX1 + 32, 0, WZ[1], {'n': T('wall'), 's': T('facade'), 'w': T('brick')},
         [(FRONT_DOOR[0], FRONT_DOOR[1], 0, FRONT_DOOR[2])] + [(a, b, WZ[0], WZ[1]) for (a, b) in WINDOWS])
    K.add(box((SX0 - 32, YFO, WZ[1]), (SX1 + 32, SY0, ZC), tex6(n=T('wall'), s=T('facade'), w=T('brick')), detail=False))
    K.add(box((SX0 - 32, YFO, ZC), (SX1 + 32, SY0, ZSKY), tex6(s=T('facade'), w=T('brick')), detail=False))
    # saloon west wall: garden side (brick outside, rises to the sky lid above the ceiling) and the snug partition
    wall('x', SX0 - 32, SX0, SY0, NYO, 0, ZC, {'e': T('wall'), 'w': T('brick')}, [(SIDE_DOOR[0], SIDE_DOOR[1], 0, SIDE_DOOR[2])])
    K.add(box((SX0 - 32, SY0, ZC), (SX0, NYO, ZSKY), tex6(w=T('brick')), detail=False))
    wall('x', SX0 - 32, SX0, NY0, SY1, 0, ZC, {'e': T('wall'), 'w': T('wall_snug')}, [(SNUG_DOOR[0], SNUG_DOOR[1], 0, SNUG_DOOR[2])])
    # snug south wall (garden outside): back door + window, brick above the ceiling up to the sky lid
    wall('y', NYO, NY0, NX0 - 32, SX0, 0, ZC, {'n': T('wall_snug'), 's': T('brick'), 'e': T('wall')},
         [(BACK_DOOR[0], BACK_DOOR[1], 0, BACK_DOOR[2]), (SNUG_WIN[0], SNUG_WIN[1], SNUG_WZ[0], SNUG_WZ[1])])
    K.add(box((NX0 - 32, NYO, ZC), (SX0, NY0, ZSKY), tex6(s=T('brick')), detail=False))
    # ceilings
    K.add(box((SX0, SY0, ZC), (SX1 + 32, SY1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    K.add(box((NX0 - 32, NY0, ZC), (SX0, SY1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # outdoor sky box: west wall (garden + pavement), east end, the far side of the road, the lid
    K.add(box((NX0 - 64, YR - 32, -48), (NX0 - 32, NY0, ZSKY), tex6(e=S), detail=False))
    K.add(box((SX1 + 32, YR - 32, -48), (SX1 + 64, SY0, ZSKY), tex6(w=S), detail=False))
    K.add(box((NX0 - 32, YR - 32, -48), (SX1 + 32, YR, ZSKY), tex6(n=S), detail=False))
    K.add(box((NX0 - 64, YR - 32, ZSKY), (SX1 + 64, SY0, ZSKY + 32), tex6(bot=S), detail=False))
    K.add(box((NX0 - 64, SY0, ZSKY), (SX0, NY0, ZSKY + 32), tex6(bot=S), detail=False))
    # backdrops: the terrace across the road, the neighbour's brick wall over the garden and at the street ends
    K.add(sign_box((NX0 - 32, YR, -16), (SX1 + 32, YR + 8, ZSKY), T('across'), 1024, 512, facing='n', edge=T('across')))
    K.add(sign_box((NX0 - 32, YFO, 0), (NX0 - 24, NYO, ZSKY), T('neighbour'), 1024, 512, facing='e', edge=T('brick')))
    for (y0, y1, z0) in ((YR + 8, YP - 16, -16), (YP, YFO, 0)):
        K.add(sign_box((NX0 - 32, y0, z0), (NX0 - 24, y1, ZSKY), T('neighbour'), 1024, 512, facing='e', edge=T('brick')))
        K.add(sign_box((SX1 + 24, y0, z0), (SX1 + 32, y1, ZSKY), T('neighbour'), 1024, 512, facing='w', edge=T('brick')))
    K.add(box((NX0 - 24, YP - 16, 0), (SX1 + 24, YP, ZSKY), CLIP))                  # players stay on the pavement
    # glass: front windows (etched lower band), snug window
    for (a, b) in WINDOWS:
        K.add(box((a, YFO + 12, WZ[0]), (b, YFO + 20, 560), T('etched')))
        K.add(box((a, YFO + 12, 560), (b, YFO + 20, WZ[1]), T('glass')))
        K.reserve(((a, YFO, WZ[0]), (b, SY0, WZ[1])))
    K.add(box((SNUG_WIN[0], NYO + 12, SNUG_WZ[0]), (SNUG_WIN[1], NYO + 20, SNUG_WZ[1]), T('glass')))
    # keep every doorway clear on both sides
    K.keep_clear(FRONT_DOOR[0] - 40, YFO - 140, FRONT_DOOR[1] + 40, SY0 + 160, 0)
    K.keep_clear(SX0 - 140, SIDE_DOOR[0] - 30, SX0 + 140, SIDE_DOOR[1] + 30, 0)
    K.keep_clear(SX0 - 180, SNUG_DOOR[0] - 30, SX0 + 140, SNUG_DOOR[1] + 30, 0)
    K.keep_clear(BACK_DOOR[0] - 40, NYO - 140, BACK_DOOR[1] + 40, NY0 + 140, 0)
    K.keep_clear(GATE[0] - 30, YFO - 120, GATE[1] + 30, YFO + 120, 0)
    K.route('front_door', (0, YFO - 150, 0), (0, SY0 + 150, 0))
    K.route('side_door', (SX0 - 150, (SIDE_DOOR[0] + SIDE_DOOR[1]) / 2, 0), (SX0 + 150, (SIDE_DOOR[0] + SIDE_DOOR[1]) / 2, 0))
    K.route('snug_door', (SX0 - 180, (SNUG_DOOR[0] + SNUG_DOOR[1]) / 2, 0), (SX0 + 150, (SNUG_DOOR[0] + SNUG_DOOR[1]) / 2, 0))
    K.route('back_door', ((BACK_DOOR[0] + BACK_DOOR[1]) / 2, NYO - 150, 0), ((BACK_DOOR[0] + BACK_DOOR[1]) / 2, NY0 + 150, 0))
    K.route('gate', ((GATE[0] + GATE[1]) / 2, YFO - 200, 0), ((GATE[0] + GATE[1]) / 2, YFO + 200, 0))


def facade():
    """the pub front: green glazed tiles, maroon stall risers, pilasters, the gilt fascia, upper storey, window boxes,
    window frames, the open double doors and the swinging pub sign"""
    K.add(sign_box((SX0 - 32, YFO - 20, 1270), (SX1 + 24, YFO, 1450), T('fascia'), 1024, 128, facing='s', edge=T('jamb')))
    K.add(box((SX0 - 40, YFO - 40, 1450), (SX1 + 24, YFO, 1480), {'top': T('stone'), 'side': T('stone'), 'bot': T('stone')}))
    K.add(sign_box((SX0 - 32, YFO - 8, 1480), (SX1 + 24, YFO, ZSKY), T('upper'), 1024, 512, facing='s', edge=T('brick')))
    for (a, b) in WINDOWS:
        K.add(box((a, YFO - 8, 0), (b, YFO, WZ[0] - 30), {'s': T('stallriser'), 'top': T('stone'), 'side': T('stone'), 'bot': CAULK}))
        K.add(box((a, YFO - 120, WZ[0] - 30), (b, YFO, WZ[0]), {'side': T('stone'), 'top': T('stone'), 'bot': T('stone')}))
        K.occupy(a, YFO - 120, b, YFO, 0, WZ[0])
        deco('window_box', (a + b) / 2, YFO - 4, WZ[0], 0)
        deco('window_frame', (a + b) / 2, YFO + 16, WZ[0], 0)
    for x in (SX0 + 40, -460, 460, SX1 - 40):
        deco('pilaster', x, YFO - 8, 0, 0)
        K.add(box((x - 40, YFO - 38, 0), (x + 40, YFO - 8, 300), WCLIP))
        K.occupy(x - 40, YFO - 38, x + 40, YFO - 8, 0, 300)
    deco('door_leaf', FRONT_DOOR[0], SY0 + 24, 0, 180)
    deco('door_leaf', FRONT_DOOR[1], SY0 + 24, 0, 0)
    # hanging pub sign on a wrought-iron bracket over the pavement (the board swings in the breeze)
    deco('sign_bracket', -800, YFO - 8, 1640, 0)
    K.add(box((-808, YFO - 388, 1632), (-792, YFO - 8, 1648), WCLIP))
    K.pendulum_model2(ML.PLACE['pub_sign_board'][0], (-800, YFO - 300, 1640), 4, 520)
    for x in (-1350, 1000):                                    # flower baskets hung from their own iron brackets
        deco('sign_bracket', x, YFO - 8, 1640, 0)
        K.add(box((x - 8, YFO - 388, 1632), (x + 8, YFO - 8, 1648), WCLIP))     # the bracket arm (the basket hangs off it)
        deco('basket', x, YFO - 8 - 300, 1632, lit=False)


# ------------------------------------------------------------------------------------------------ the bar
def bar():
    """the counter (three straight modules, a quarter-round corner, a return to the back-bar) and the five-bay gantry"""
    L = (CX1 - CX0) / 3
    for k in range(3):
        place('counter_run', CX0 + L * (k + 0.5), CY1, 0, 0)
    place('counter_corner', CX1, CY1, 0, 0)
    place('counter_return', CX1, (CY1 + RET_Y1) / 2, 0, 90)
    for (x, name) in BAYS:
        place(name, x, SY1, 0, 0)
    place('gantry_end', GEND_X, SY1, 0, 0)
    K.reserve(((CX0, CY0 - 50, 0), (RET_X1 + 50, CY1, 80)))                 # the foot rail
    K.route('staff_floor', (-1350, 500, 0), (-500, 1180, 0))
    # on the counter: pumps, lager font, till, wine, snacks board, lilies, hurricane jar, glass rack
    place('beer_pumps', -660, 850, CZ, 0)
    place('lager_font', -380, 860, CZ, 0)
    place('beer_pumps3', 620, 850, CZ, 0)
    place('hurricane', 340, 780, CZ)
    place('wine_display', 120, 930, CZ, 0)
    place('till', 840, 880, CZ, 0)
    place('coffee_machine', 1050, 1110, CZ, 90)
    deco('coffee_stand', 720, 760, CZ, 340)
    deco('snacks_stand', -1040, 760, CZ, 20)
    deco('lilies', -900, 800, CZ)
    deco('glass_rack', -880, 920, CZ, 0)
    # the coffee machine on the gantry end's back counter, kegs + a crate on the staff floor (cover)
    place('keg', 760, 1180, 0); place('crate', -880, 1220, 0, 0)
    for (x, sd) in ((-1000, 'stool_red'), (-800, 'stool_green'), (-560, 'stool_red'), (-330, 'stool_green'),
                    (430, 'stool_red'), (650, 'stool_green')):
        place(sd, x, CY0 - 95, 0)
    for (y, sd) in ((1040, 'stool_red'), (1180, 'stool_green')):
        place(sd, RET_X1 + 95, y, 0)
    for x in (-820, 480):
        deco('pendant', x, 780, ZC, lit=False)
        K.light(x, 780, ZC - 420, 300, '1 0.85 0.6')


def saloon():
    """seating: settle-booth islands under chandeliers, front banquettes under the windows with round tables, a
    banquette along the west wall, the fireplace, the longcase clock (secret), the fruit machine, wall art"""
    for cx in ISLANDS:
        place('settle', cx, ISLAND_Y + 370, 0, 0)
        place('settle', cx, ISLAND_Y - 370, 0, 180)
        place('booth_table', cx, ISLAND_Y, 0, 0)
        deco('chandelier', cx, ISLAND_Y, ZC, lit=False)
        K.light(cx, ISLAND_Y, ZC - 300, 700, '1 0.85 0.6')
    for (a, b) in WINDOWS:
        place('banquette', (a + b) / 2, SY0, 0, 180)
    for (x, t) in ((-1200, 'pub_table'), (-750, 'pub_table1'), (750, 'pub_table'), (1200, 'pub_table1')):
        place(t, x, -820, 0)
    for (x, sd) in ((-975, 'stool_green'), (975, 'stool_red')):
        place(sd, x, -790, 0)
    # west wall banquette between the side door and the snug door, with tables
    place('banquette_long', SX0, -185, 0, 90)
    for (y, t) in ((-370, 'pub_table1'), (30, 'pub_table')):
        place(t, -1235, y, 0)
    # fireplace on a tiled hearth (east wall)
    K.add(box((SX1 - 260, FIRE_Y - 420, 0), (SX1, FIRE_Y + 420, HEARTH), {'top': T('hearth'), 'side': T('hearth'), 'bot': CAULK}))
    K.occupy(SX1 - 260, FIRE_Y - 420, SX1, FIRE_Y + 420, 0, HEARTH)
    place('fireplace', SX1, FIRE_Y, HEARTH, 270)
    for sx in (-1, 1):
        deco('sconce', SX1, FIRE_Y + sx * 540, 900, 270, lit=False)
        K.light(SX1 - 90, FIRE_Y + sx * 540, 950, 200, '1 0.85 0.6')
    K.light(SX1 - 260, FIRE_Y, 120, 300, '1 0.55 0.25')
    K.speaker(SX1 - 100, FIRE_Y, 120, 'ambient/fire_crackling')
    # longcase clock: walk into its open trunk -> the cellar
    place('longcase', SX1, CLOCK_Y, 0, 270)
    K.speaker(SX1 - 80, CLOCK_Y, 800, 'machine/clock_ticking')
    tw, td, th = PM.CLOCK_TRUNK
    D = PM.CLOCK[1]
    x0, x1 = SX1 - D + 4, SX1 - D + td - 4
    K.secret((x0, CLOCK_Y - tw / 2 + 6, 20), (x1, CLOCK_Y + tw / 2 - 6, th - 60), dest=(0, -300, VZ), angle=90, name='clock', approach='w')
    K.pendulum_model2(ML.PLACE['pendulum'][0], (SX1 - D + td / 2 + 4, CLOCK_Y, th + 20), 6, 360)
    # fruit machine in the NE corner, coat stand by the front door, plants
    place('fruit_machine', 1400, SY1, 0, 0)
    K.light(1400, SY1 - 400, 500, 180, '0.8 0.6 1')
    place('coat_stand', -1480, SY0 + 130, 0)
    K.catalog('pad_ddmix/plants/cane5.md3', 1500, -1100, 0, scale=1.6, angle=0)
    place('umbrella_stand', 1480, 880, 0)
    # wall art: oval mirrors with sconces and hunting prints on the west wall; prints on the east wall, notices north
    for (y, kind) in ((-450, 'mirror'), (-20, 'print0'), (700, 'mirror'), (1150, 'print1')):
        if kind == 'mirror':
            K.add(sign_box((SX0, y - 110, 640), (SX0 + 3, y + 110, 970), T('oval_mirror'), 256, 384, facing='e', edge=T('jamb')))
            deco('frame_mirror', SX0 + 3, y, 805, 90)
            for sx in (-1, 1):
                deco('sconce', SX0, y + sx * 200, 900, 90, lit=False)
            K.light(SX0 + 90, y, 950, 220, '1 0.85 0.6')
        else:
            K.add(sign_box((SX0, y - 100, 700), (SX0 + 3, y + 100, 850), T(kind), 256, 192, facing='e', edge=T('jamb')))
            deco('frame_print', SX0 + 3, y, 775, 90)
    for (y, kind) in ((-380, 'print2'), (-1080, 'print3')):
        K.add(sign_box((SX1 - 3, y - 100, 800), (SX1, y + 100, 950), T(kind), 256, 192, facing='w', edge=T('jamb')))
        deco('frame_print', SX1 - 3, y, 875, 270)
    K.add(sign_box((1250, SY1 - 3, 1000), (1550, SY1, 1300), T('notice'), 256, 256, facing='s', edge=T('jamb')))


def snug():
    """the snug: upright piano (top reachable by a pad), jukebox, dartboard + oche + scores, settle against the
    partition, tables, health station"""
    place('piano', NX0, PIANO_Y, 0, 90)
    place('piano_stool', NX0 + 390, PIANO_Y, 0, 90)
    place('jukebox', -1850, SY1, 0, 0)
    K.light(-1850, SY1 - 300, 500, 200, '1 0.5 0.8')
    deco('dartboard', -2295, SY1, 650, 0)
    deco('oche', -2295, SY1 - 620, 0, 0)
    K.keep_clear(-2395, SY1 - 650, -2195, SY1, 0)                                  # the throwing lane                                  # the throwing lane
    place('settle', NX1, 950, 0, 270)
    place('pub_table1', -1990, 950, 0)
    place('pub_table', -2050, 40, 0)
    K.station(-2440, -100, 0, ang=0)
    place('coat_stand', -1720, -110, 0)
    deco('chandelier', -2100, 700, ZC, lit=False)
    K.light(-2100, 700, ZC - 300, 650, '1 0.85 0.6')
    K.light(-2100, 1300, 900, 300, '1 0.85 0.6'); K.light(-2100, 50, 900, 300, '1 0.85 0.6')
    K.add(sign_box((NX0, 1150, 700), (NX0 + 3, 1350, 850), T('print3'), 256, 192, facing='e', edge=T('jamb')))
    deco('frame_print', NX0 + 3, 1250, 775, 90)
    K.route('snug_length', (-1900, 1150, 0), (-1900, -60, 0))


def garden():
    """beer garden: picnic table under a parasol, barrels as standing tables, flowers, low walls either side of the gate"""
    place('picnic_table', -2230, -720, 0, 90)
    deco('parasol', -2230, -720, PM.PICNIC_Z)
    place('barrel', -1770, -390, 0); place('barrel', -1770, -1070, 0)
    lw = {'side': T('brick'), 'top': T('stone'), 'bot': CAULK}
    K.add(box((NX0, YFO - 16, 0), (GATE[0] - 40, YFO + 16, 200), lw), box((GATE[1] + 40, YFO - 16, 0), (SX0 - 32, YFO + 16, 200), lw))
    for x in (GATE[0] - 40, GATE[1]):
        K.add(box((x, YFO - 24, 0), (x + 40, YFO + 24, 320), lw))
        deco('pier_cap', x + 20, YFO, 320)
    K.occupy(NX0, YFO - 24, SX0 - 32, YFO + 24, 0, 320)
    K.timer_sound(-2100, -700, 600, 'animal/blackbird', 'birds', 25, 15)
    K.timer_sound(-2300, -400, 900, 'animal/bird_blackcap', 'birds2', 35, 20)


def pavement():
    """the street side: phone box (walk in; pad to the roof), pillar box, lamps, A-board, picnic table"""
    place('phone_box', *PHONE, 0, 270)
    place('pillar_box', -600, -1500, 0)
    place('street_lamp', -1250, -2010, 0); place('street_lamp', 420, -2010, 0)
    place('a_board', 330, -1420, 0, 20)
    place('picnic_table', -1150, -1700, 0, 0)
    deco('parasol', -1150, -1700, PM.PICNIC_Z)
    K.catalog('pad_ddmix/trashcan/garbage_bag_group.md3', 1480, -1350, 0, scale=1.6, angle=20)
    K.catalog('pad_ddmix/plants/flower_pink.md3', -1950, -1400, 0, scale=1.2, angle=0)
    K.route('phone_box', (520, PHONE[1] - 120, 0), (PHONE[0], PHONE[1], 16))
    K.timer_sound(0, -1950, 400, 'ambient/police_pass', 'siren', 70, 30)
    K.timer_sound(-1000, -1950, 200, 'misc/bicycle_bell', 'bike', 40, 20)
    K.timer_sound(500, -1950, 200, 'animal/dog_bark2', 'dog', 55, 25)
    K.trigger_sound((FRONT_DOOR[0], YFO, 0), (FRONT_DOOR[1], SY0, 200), 'machine/dingdong', 'doorbell', wait=3)


def cellar():
    """the secret barrel cellar (sealed, below the world): Pad Power, Revival, Killer Ducks, Pad shield; back to the bar"""
    x0, y0, x1, y1 = VAULT; z = VZ; h = 480
    w, f = T('cellar'), T('cellar_floor')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': f, 'side': CAULK, 'bot': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': w, 'side': CAULK, 'top': CAULK}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=w), detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=w), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=w), detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=w), detail=False))
    place('barrel_rack', 0, 280, z, 0)
    place('keg', -380, -150, z); place('keg', -380, -380, z); place('crate', 330, -300, z, 10); place('barrel_plain', 360, -40, z)
    K.item('item_padpower', 0, 20, z); K.item('item_revival', -180, -120, z); K.item('holdable_killerducks', 180, -120, z)
    K.item('item_armor_padshield', 0, -220, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(-620, 1180, 0), angle=0, name='cellar_exit')
    K.light(0, 0, z + 400, 700, '1 0.85 0.6'); K.light(-300, 0, z + 200, 250, '1 0.7 0.4'); K.light(300, 0, z + 200, 250, '1 0.7 0.4')
    K.speaker(0, 0, z + 200, 'ambient/water_drippling')


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    """every pad is a theme object: the 6u disc becomes an invisible nonsolid brush (trigger, aim and bot links are
    unchanged) and the dressing model sits on the floor, turned so its 'business end' points along the flight"""
    def P(x, y, z, land, apex, name, dress, glow=None, **kw):
        K.jumppad(x, y, z, land=land, apex=apex, name=name, glow=False, top_tex=T('nodraw_ns'), side_tex=T('nodraw_ns'), **kw)
        yaw = math.degrees(math.atan2(land[1] - y, land[0] - x))
        deco(dress, x, y, z, round(yaw - 90) % 360, lit=True)
        if glow: K.light(x, y, z + 24, glow, '1 0.7 0.4')
    P(200, 430, 0, (200, 860, CZ), CZ + 220, 'pad_counter', 'pad_tray', edges=[(200, CY0, CZ)])
    P(-100, 850, CZ, (-100, 1480, KZ), KZ + 150, 'pad_topshelf', 'pad_spill', ceiling=ZC, edges=[(-100, RET_Y1, KZ)])
    P(340, 1150, 0, (340, 1418, BZ), BZ + 170, 'pad_backbar', 'pad_trapdoor', glow=90, ceiling=KZ - 76, edges=[(340, RET_Y1, BZ)])
    P(1050, FIRE_Y, 0, (1515, FIRE_Y, OMZ), OMZ + 150, 'pad_overmantel', 'pad_bellows', ceiling=ZC,
      edges=[(SX1 - PM.OVERMANTEL_D - 10, FIRE_Y, OMZ)])
    P(-1960, PIANO_Y, 0, (NX0 + 90, PIANO_Y, PM.PIANO[2]), PM.PIANO[2] + 200, 'pad_piano', 'pad_tambourine', ceiling=ZC,
      edges=[(NX0 + 180, PIANO_Y, PM.PIANO[2])])
    P(560, PHONE[1], 0, (PHONE[0] - 30, PHONE[1], PM.PHONE[1]), PM.PHONE[1] + 190, 'pad_phone', 'pad_coalhole', glow=70,
      edges=[(PHONE[0] - 160, PHONE[1], PM.PHONE[1])])
    # exits for bots off the tall tops (bspc only traces walk-offs 1000u down): fling pads on the far side
    P(GEND_X, SY1 - 60, KZ, (-880, 820, CZ), KZ + 110, 'fling_topshelf', 'pad_corks', ceiling=ZC)
    P(PHONE[0] + 110, PHONE[1], PM.PHONE[1], (PHONE[0] - 760, PHONE[1] + 80, 0), PM.PHONE[1] + 170, 'fling_phone', 'pad_puddle')


def items():
    W, A = K.weapon, K.ammo
    W('imperius', 120, 1480, KZ, marker='purple')
    W('betty', -540, 1418, BZ, marker='black')
    W('balloony', 1510, FIRE_Y - 220, OMZ, marker='orange')
    W('pumper', PHONE[0] - 60, PHONE[1] - 60, PM.PHONE[1], marker='green')
    W('splasher', NX0 + 90, PIANO_Y - 200, PM.PIANO[2], marker='blue')
    W('boaster', 380, 900, CZ, marker='orange')
    W('bubbleg', -1900, -560, 0, marker='green')
    ammo = {'imperius': [(780, 1480, KZ), (ISLANDS[0], ISLAND_Y, 0), (PHONE[0], PHONE[1] + 60, 16), (-2440, -1000, 0)],
            'betty': [(-980, 1418, BZ), (100, 1180, 0), (-2002, 40, 0), (-200, -1960, 0), (1248, -820, 0)],
            'balloony': [(1510, FIRE_Y + 220, OMZ), (1424, -1049, 0), (-1187, -370, 0), (1350, 1180, 0)],
            'pumper': [(PHONE[0] + 60, PHONE[1] + 60, PM.PHONE[1]), (-1900, -1950, 0), (1400, -1950, 0), (-1873, 1173, 0)],
            'splasher': [(NX0 + 90, PIANO_Y + 200, PM.PIANO[2]), (-2200, 1200, 0), (-1960, -900, 0), (ISLANDS[1], ISLAND_Y, 0)],
            'boaster': [(-1000, 830, CZ), (0, -900, 0), (798, -820, 0), (-2300, -1180, 0)],
            'bubbleg': [(-2050, 700, 0), (0, -350, 0), (-600, -1900, 0), (1320, 662, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: A(w, x, y, z)
    A('nipper', 0, 300, 0); A('nipper', -1400, 1180, 0); A('nipper', 200, -1700, 0); A('nipper', -2300, 1000, 0)
    K.item('item_armor_shard', -1400, 1480, KZ); K.item('item_armor_shard', 20, 770, CZ)
    K.item('item_armor_shard', NX0 + 90, PIANO_Y, PM.PIANO[2]); K.item('item_armor_shard', -1187, 30, 0)
    K.item('item_speedy', -1950, -1650, 0)
    K.item('item_jumper', -2200, 1300, 0)
    K.item('holdable_floater', -2230, -720, PM.PICNIC_Z)
    K.item('item_visionless', 600, 1180, 0)
    for (x, y, a) in ((-300, -900, 90), (300, -600, 90), (0, 0, 90), (-1100, -500, 0), (1150, -300, 180), (-200, 500, 270),
                      (1300, 900, 225), (-1350, 1000, 315), (-300, 1180, 0), (-2300, 800, 0), (-1900, 300, 180),
                      (-2100, -400, 270), (-1900, -1000, 90), (-1900, -1800, 0), (-300, -1650, 90), (700, -1450, 180),
                      (1300, -1950, 135)):
        K.spawn(x, y, 0, a)


def lights_sounds():
    K.light_grid(SX0, SY0, SX1, SY1, 1350, 640, 1300, color='1 0.88 0.68')
    K.light_grid(NX0, NY0, NX1, SY1, 1350, 640, 1000, color='1 0.86 0.66')
    for (x, y) in ((-1235, -370), (-1235, 30), (-1200, -820), (-750, -820), (750, -820), (1200, -820), (-2050, 40), (-1990, 950)):
        K.light(x, y, 230, 140, '1 0.85 0.65')                  # under the tables
    for (x, _) in BAYS:
        K.light(x, SY1 - 160, 1100, 260, '1 0.8 0.55')           # back-bar shelf lights
        K.light(x, SY1 - 150, 620, 160, '0.9 0.95 1')
    K.light(GEND_X, SY1 - 300, 900, 200, '1 0.85 0.6')
    K.light(PHONE[0], PHONE[1], 900, 220, '1 0.95 0.85')
    for x in (-1250, 420):
        K.light(x, -2010, 1300, 260, '1 0.9 0.7')
    K.speaker(-1850, SY1 - 200, 600, 'machine/tv_upstairs')
    K.speaker(0, 200, 300, 'ambient/floor_creaking')
    K.trigger_sound((-200, 1380, KZ), (0, 1580, KZ + 80), 'human/applause', 'topshelf', wait=8)


def shader():
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(200, 50), sun_int=110, skylight=(60, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = PM.textures(K)
    PM.all_models()                    # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); facade(); bar(); saloon(); snug(); garden(); pavement(); cellar(); pads(); items(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
