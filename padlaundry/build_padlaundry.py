#!/usr/bin/env python3
"""Spin Cycle (wop_padlaundry) - Padman in a coin laundromat at night.

    OUT=<dir> python3 build_padlaundry.py          (or: wopbuild.py padlaundry preview / check / all)

West: five front-loaders on a pedestal; walk into any drum (the perforated drum spins round you, shallow suds in the
bottom); soap-bubble lifts to the machine tops. East: stacked dryers on a stepped plinth, the lower drums walk-in, the
top of the stack is the high ground. North: the giant utility sink (soap-bar steps inside). South: the shopfront onto
the night street, change and soap machines, chairs. Centre: folding tables, Mount Laundry, carts.
Secret: the lint screen at the back of the first dryer -> the Lost Sock Dimension.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from wopmap import box, cyl, hull, carve, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL
from woplib.geom import axis_prism, disc_brush
import layout as L
import lm_models as LM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
K = MapKit(MAP, NS, LONG, tuple(INFO['bounds']), worldspawn={'_ambient': '16', '_color': '0.9 0.95 1'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
LM.setup(TX)


# ================================================================================================= room
def shell():
    """structural room: vinyl floor, tiled lower walls / cream upper walls, acoustic ceiling, shop windows in the south
    wall onto the night street (sealed sky boxes behind them)"""
    X0, Y0, X1, Y1, Z = L.X0, L.Y0, L.X1, L.Y1, L.CEIL
    K.add(box((X0 - 32, Y0 - 32, -32), (X1 + 32, Y1 + 32, 0), {'top': T('vinyl'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, Z), (X1 + 32, Y1 + 32, Z + 32), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))

    def wall(mn, mx, face):
        for (z0, z1, tex) in ((0, 1024, T('wall_tile')), (1024, Z, T('wall_upper'))):
            t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t[face] = tex
            K.add(box((mn[0], mn[1], z0), (mx[0], mx[1], z1), t, detail=False))
    wall((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, Z), 'e')
    wall((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, Z), 'w')
    wall((X0, Y1, 0), (X1, Y1 + 32, Z), 's')
    # south wall: windows + the glass entrance as sky windows, plain wall between them
    holes = sorted(L.WIN + [L.DOOR_X])
    xs = [X0]
    for a, b in holes: xs += [a - 32, b + 32]
    xs.append(X1)
    for a, b in zip(xs[0::2], xs[1::2]):
        if b - a > 1: wall((a, Y0 - 32, 0), (b, Y0, Z), 'n')
    sky = T('sky')
    for (a, b) in holes:
        z0 = 16 if (a, b) == tuple(L.DOOR_X) else L.WIN_Z[0]
        z1 = 1180 if (a, b) == tuple(L.DOOR_X) else L.WIN_Z[1]
        K.sky_window((a - 32, Y0 - 32, 0), (b + 32, Y0, Z), (a, b, z0, z1), T('wall_tile'), sky,
                     jamb_tex=T('steel'), glass_tex=T('glass'), depth=384, face='n')
    # OPEN neon in the window and the shop name over the door (signs inside the glass)
    K.add(sign_box((-1900, L.Y0 + 8, 1180), (-1440, L.Y0 + 12, 1300), T('neon_open'), 512, 128, back=T('steel'), facing='n', edge=T('steel')))
    K.add(sign_box((-400, L.Y0 + 8, 1260), (400, L.Y0 + 12, 1460), T('sign_spin'), 512, 128, back=T('steel'), facing='n', edge=T('steel')))
    K.keep_clear(L.DOOR_X[0], L.Y0, L.DOOR_X[1], L.Y0 + 200, 0)


# ================================================================================================= washers (west)
def washers():
    px0, px1 = L.PED_X
    py0, py1 = L.PED_Y
    drums = [axis_prism('x', L.W_DRUM_X[0], L.W_DRUM_X[1], yc, L.W_DRUM_Z, L.W_DRUM_R, WCLIP) for yc in L.W_YC]
    # pedestal, carved by the drum sumps
    ped = box((px0, py0, 0), (px1, py1, L.PED), {'top': T('mat_floor'), 'side': T('steel'), 'bot': CAULK})
    ped_pieces = carve(ped, drums, WCLIP)
    K.add(*ped_pieces)
    K.reserve(((px0, py0, 0), (L.W_X[1], py1, L.PED + L.W_H)))
    for i, yc in enumerate(L.W_YC):
        body = box((L.W_X[0], yc - L.W_HALF, L.PED), (L.W_X[1], yc + L.W_HALF, L.PED + L.W_H), WCLIP)
        door = axis_prism('x', L.W_DRUM_X[1] - 4, L.W_X[1] + 4, yc, L.W_DRUM_Z, L.W_DOOR_R, WCLIP)
        pieces = carve(body, [drums[i], door], WCLIP)
        K.add(*pieces)
        K.custom(ML.PLACE['washer'], L.W_X[1], yc, L.PED, occupy=False)
        # sudsy water in the bottom of the drum (42 deep: wade out up the drum's 22-degree facets)
        cut = pieces + [p for p in ped_pieces if p.bounds()[0][1] < yc + L.W_HALF and p.bounds()[1][1] > yc - L.W_HALF]
        K.water_box((L.W_DRUM_X[0], yc - L.W_DRUM_R - 6, L.W_DRUM_Z - L.W_DRUM_R), (L.W_DRUM_X[1], yc + L.W_DRUM_R + 6, L.W_WATER),
                    T('water_suds'), cutters=[p for p in cut if overlaps(p, L.W_DRUM_X, yc)])
        # the spinning drum (visual only) and the open door
        K.rotating_model2(ML.IQM['washer_drum'], ((L.W_DRUM_X[0] + L.W_DRUM_X[1]) / 2, yc, L.W_DRUM_Z), 12 + 3 * i, axis='x',
                          reverse=bool(i % 2))
        hy = yc + L.W_DOOR_R + 30
        K.custom(ML.PLACE['door'], L.W_X[1] + 4, hy, L.W_DRUM_Z, angle=0, boxes=LM.DOOR_BOX)
        K.keep_clear(L.W_X[1], yc - 150, L.W_X[1] + 120, yc + 150, L.PED)
        K.speaker(L.W_X[1] - 200, yc, L.PED + 60, 'ambient/water_bubbling', volume=0.35)
        K.route(f'washer{i}', (L.W_X[1] + 200, yc - 100, L.PED), (L.W_DRUM_X[1] - 80, yc, L.PED))
    # stairs: both pedestal ends (along y) and one flight down the middle of the front
    for s in (1, -1):
        y0, y1 = (py1, py1 + 448) if s > 0 else (py0 - 448, py0)
        K.stairs16(-1600, y0, -1440, y1, 0, L.PED, 's' if s > 0 else 'n', {'top': T('mat_floor'), 'side': T('steel')},
                   route=f'ped_end_{"n" if s > 0 else "s"}')
        K.reserve(((-1600, y0, 0), (-1440, y1, L.PED)), pad=4)
    K.stairs16(px1, -80, px1 + 448, 80, 0, L.PED, 'w', {'top': T('mat_floor'), 'side': T('steel')}, route='ped_front')
    K.reserve(((px1, -80, 0), (px1 + 448, 80, L.PED)), pad=4)
    K.keep_clear(px1 + 448, -100, px1 + 560, 100, 0)
    # soap-bubble lifts onto the machine tops
    for y in (-840, 840):
        K.jumppad(-1290, y, L.PED, land=(-2010, y, L.PED + L.W_H), apex=L.PED + L.W_H + 160, name=f'pad_washer_{"n" if y > 0 else "s"}',
                  edges=[(L.W_X[1], y, L.PED + L.W_H)])
        K.rotating_model2(ML.IQM['bubbles'], (-1290, y, L.PED + 40), 20)


def overlaps(b, xr, yc):
    mn, mx = b.bounds()
    return mn[0] < xr[1] and mx[0] > xr[0] and mn[1] < yc + L.W_DRUM_R + 6 and mx[1] > yc - L.W_DRUM_R - 6 and mn[2] < L.W_WATER


# ================================================================================================= dryers (east)
def dryers():
    x0, x1 = L.D_X
    K.stairs16(L.PLINTH_X[0], L.PED_Y[0], L.PLINTH_X[1], L.PED_Y[1], 0, L.PLINTH, 'e', {'top': T('mat_floor'), 'side': T('steel')})
    K.reserve(((L.PLINTH_X[0], L.PED_Y[0], 0), (x1, L.PED_Y[1], L.D_TOP)), pad=4)
    for i, yc in enumerate(L.D_YC):
        drum = axis_prism('x', x0 - 4, L.D_DRUM_X[1], yc, L.D_DRUM_Z, L.D_DRUM_R, WCLIP)
        low = box((x0, yc - L.D_HALF, 0), (x1, yc + L.D_HALF, L.D_LOW_H), WCLIP)
        K.add(*carve(low, [drum], WCLIP))
        K.add(box((x0, yc - L.D_HALF, L.D_LOW_H), (x1, yc + L.D_HALF, L.D_TOP), WCLIP))
        K.custom(ML.PLACE['dryer_low'], x0, yc, 0, angle=180, occupy=False)
        K.custom(ML.PLACE['dryer_up'], x0, yc, L.D_LOW_H, angle=180, occupy=False)
        K.rotating_model2(ML.IQM['dryer_drum'], ((L.D_DRUM_X[0] + L.D_DRUM_X[1]) / 2, yc, L.D_DRUM_Z), 25, axis='x', reverse=bool(i % 2))
        K.keep_clear(L.PLINTH_X[0] - 112, yc - 120, x0, yc + 120, 0)
        K.route(f'dryer{i}', (L.PLINTH_X[0] - 120, yc, 0), (x0 + 120, yc, L.PLINTH))
    # dryer stack top (the high ground): pad from the floor in front of the plinth
    K.jumppad(1280, 0, 0, land=(2010, 0, L.D_TOP), apex=L.D_TOP + 140, name='pad_dryers', edges=[(x0, 0, L.D_TOP)])
    K.speaker(2000, 0, 400, 'machine/aircon', volume=0.4)


# ================================================================================================= sink (north)
def sink():
    x0, y0, x1, y1 = L.SINK
    t = L.SINK_T; zb, zt = L.SINK_Z
    st = {'top': T('enamel'), 'side': T('sink_white'), 'bot': T('enamel')}
    for mn, mx in (((x0, y0, zb), (x1, y0 + t, zt)), ((x0, y1 - t, zb), (x1, y1, zt)),
                   ((x0, y0 + t, zb), (x0 + t, y1 - t, zt)), ((x1 - t, y0 + t, zb), (x1, y1 - t, zt))):
        K.add(box(mn, mx, WCLIP))
    K.add(box((x0 + t, y0 + t, zb), (x1 - t, y1 - t, L.SINK_FLOOR), WCLIP))
    for x in (x0 + 50, x1 - 50):
        for y in (y0 + 50, y1 - 50):
            K.add(cyl(x, y, 22, 0, zb, WCLIP, 12))
    K.custom(ML.PLACE['sink'], (x0 + x1) / 2, (y0 + y1) / 2, 0, occupy=False)
    K.reserve(((x0, y0, zb), (x1, y1, zt)))
    for x in (x0 + 50, x1 - 50):
        for y in (y0 + 50, y1 - 50):
            K.occupy_r(x, y, 30, 0, zb)
    # soap-bar steps inside, west end, out of the deep water onto the west rim
    ix0, iy0, ix1, iy1 = x0 + t, y0 + t, x1 - t, y1 - t
    steps = K.stairs16(ix0, iy0, ix0 + 17 * 32, iy0 + 160, L.SINK_FLOOR, L.SINK_WATER, 'w', WCLIP)
    K.custom(ML.PLACE['soap_steps'], ix0 + 17 * 32, iy0 + 80, L.SINK_FLOOR, angle=180, occupy=False)
    K.water_box((ix0, iy0, L.SINK_FLOOR), (ix1, iy1, L.SINK_WATER), T('water'), cutters=steps)
    K.speaker(0, (y0 + y1) / 2, L.SINK_WATER, 'ambient/water_drippling', volume=0.6)
    # drainboard counter (top = rim height) and the pad onto it
    bx0, by0, bx1, by1 = L.BOARD

    def btex(c, n, poly):
        if n[2] > 0.7: return LM.MAT['laminate'], (lambda p: (p[0] / 256, -p[1] / 256))
        if n[2] < -0.7: return None
        return LM.MAT['teal'], (lambda p: ((p[0] + p[1]) / 256, -p[2] / 256))
    K.solid_piece('drainboard', [box((bx0, by0, 0), (bx1, by1, zt), CAULK)], btex)
    K.jumppad(830, 1150, 0, land=(830, 1800, zt), apex=zt + 150, name='pad_board', edges=[(830, by0, zt)])
    K.route('board_rim', (830, 1800, zt), (x1 - t / 2, 1800, zt))


# ================================================================================================= centre
def tables():
    for i, (x0, y0, x1, y1) in enumerate(L.TABLES):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        K.add(box((x0, y0, L.TABLE_Z - L.TABLE_T), (x1, y1, L.TABLE_Z), WCLIP))
        for (lx, ly, r, z0, z1) in LM.TABLE_LEGS:
            K.add(cyl(cx + lx, cy + ly, r, z0, z1, WCLIP, 10))
            K.occupy_r(cx + lx, cy + ly, r + 8, z0, z1)
        K.custom(ML.PLACE['table'], cx, cy, 0, occupy=False)
        K.occupy(x0, y0, x1, y1, L.TABLE_Z - L.TABLE_T - 24, L.TABLE_Z + 4, why='table top')
        # pad at the far end onto the top
        s = -1 if i == 0 else 1
        py = (y0 - 300) if s < 0 else (y1 + 300)
        land_y = (y0 + 300) if s < 0 else (y1 - 300)
        K.jumppad(cx, py, 0, land=(cx, land_y, L.TABLE_Z), apex=L.TABLE_Z + 230, name=f'pad_table{i}',
                  edges=[(cx, y0 if s < 0 else y1, L.TABLE_Z)])


def mount_laundry():
    cx, cy = L.PILE
    for i in range(L.PILE_TIERS):
        r = L.PILE_R0 - i * L.PILE_STEP_R
        K.add(disc_brush(cx, cy, r, i * 16, (i + 1) * 16, WCLIP, n=16))
    K.custom(ML.PLACE['pile'], cx, cy, 0, occupy=False)
    K.occupy_r(cx, cy, L.PILE_R0 + 8, 0, L.PILE_TIERS * 16 + 40)
    K.route('pile', (cx + L.PILE_R0 + 120, cy, 0), (cx, cy, L.PILE_TIERS * 16))


def south_side():
    # change machine (Betty on top) and the soap machine, against the shopfront
    for (x0, y0, x1, y1, top), name in ((L.CHANGE, 'change_machine'), (L.SOAPVEND, 'soap_machine')):
        K.add(box((x0 + 4, y0 + 4, 0), (x1 - 4, y1 - 4, top), WCLIP))
        K.custom(ML.PLACE[name], (x0 + x1) / 2, (y0 + y1) / 2 + 2, 0, occupy=False)
        K.reserve(((x0, y0, 0), (x1, y1, top)), pad=8)
        cx = (x0 + x1) / 2
        K.jumppad(cx, y1 + 300, 0, land=(cx, (y0 + y1) / 2 - 20, top), apex=top + 150,
                  name=f'pad_{name.split("_")[0]}', edges=[(cx, y1, top)])
    # chairs along the windows, facing the room
    for x in (-560, -400, 400, 560, 1820, 2000):
        K.prop(ML.PLACE['chair_orange' if x < 0 else 'chair_teal'], x, L.Y0 + 140, 0, boxes=LM.CHAIR_BOXES, angle=0, search=40)
    K.catalog('padtv/padtv2.md3', -2050, -1750, 0, angle=45, scale=1.0)
    K.station(1500, L.Y0 + 150, 0, ang=90)
    K.station(-900, 1900, 0, ang=270)


def props():
    for (x, y) in ((0, 300), (-1000, -150), (1050, 420), (-200, 1300)):
        K.prop(ML.PLACE['cart'], x, y, 0, boxes=LM.CART_BOXES, angle=None, search=200)
    for (x, y) in ((-1000, 1000), (1100, -1100), (0, -400)):
        K.prop(ML.PLACE['detergent'], x, y, 0, cyls=[(0, 0, 158, 0, 640)], angle=None, search=200)
    # catalog things people leave in laundromats
    for (path, x, y, z, a) in (('pad_cups/pad_cup03.md3', -500, 0, L.TABLE_Z, 30), ('pad_cups/pad_cup05.md3', 500, 300, L.TABLE_Z, 200),
                               ('pad_books/pad_cb_fl_md.md3', -600, 300, L.TABLE_Z, 10), ('pad_phones/pad_padika2.md3', 600, -300, L.TABLE_Z, 70),
                               ('gummybears/redbear.md3', -1000, 1500, 0, 20), ('gummybears/yellowbear.md3', 1200, 1400, 0, 200),
                               ('pad_ddmix/trashcan/garbage_bag_group.md3', 2050, 1700, 0, 0),
                               ('pad_ddmix/plants/bonsai.md3', -2050, 1800, 0, 0), ('pad_ducks/pad_duck.md3', 200, 1850, L.SINK_FLOOR, 160)):
        K.catalog(path, x, y, z, angle=a, lit=True, clip=(z == 0), nudge=(z == 0))


# ================================================================================================= secret
def lost_sock_dimension():
    S = L.SOCK
    z = S['z0']
    t = {'side': T('sock_wall'), 'top': T('sock_floor'), 'bot': T('sock_wall')}
    x0, x1, y0, y1, h = S['x0'], S['x1'], S['y0'], S['y1'], S['h']
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + h), t, detail=False))
    for (x, y, rr) in ((-380, 250, 120), (400, -250, 100)):
        for i in range(5):
            K.add(disc_brush(x, y, rr - i * 20, z + i * 16, z + (i + 1) * 16, {'top': T('sock_floor'), 'side': T('sock_wall'), 'bot': CAULK}, n=12))
        K.occupy_r(x, y, rr + 8, z, z + 96)
    K.item('item_padpower', -380, 250, z + 80); K.item('item_revival', 400, -250, z + 80)
    K.item('holdable_killerducks', 300, 250, z); K.item('item_armor_padshield', -300, -250, z)
    K.teleporter((-48, y1 - 96, z + 4), (48, y1 - 32, z + 96), dest=(-900, -700, 0), angle=90, name='sock_exit')
    K.add(box((-56, y1 - 104, z), (56, y1 - 24, z + 4), {'top': T('jumppad'), 'side': T('rubber'), 'bot': CAULK}))
    for (x, y) in ((-300, 0), (300, 0)):
        K.light(x, y, z + 520, 520, '1 0.8 1')
    K.speaker(0, 0, z + 300, 'misc/wind_chimes', volume=0.5)
    # entry: the lint screen at the back of the first dryer's drum
    yc = L.SECRET_DRYER
    K.custom(ML.PLACE['lint_screen'], L.D_DRUM_X[1] - 1, yc, L.PLINTH, angle=180, occupy=False)
    K.secret((L.D_DRUM_X[1] - 34, yc - 56, L.PLINTH + 14), (L.D_DRUM_X[1] - 4, yc + 56, L.PLINTH + 150),
             dest=(0, -300, z), angle=90, name='lint_screen', approach='w')


# ================================================================================================= items, spawns, lights
def items():
    K.weapon('imperius', 2010, 0, L.D_TOP, marker='purple')
    K.weapon('splasher', 300, 1800, L.SINK_FLOOR, marker='blue')
    K.weapon('betty', (L.CHANGE[0] + L.CHANGE[2]) / 2, (L.CHANGE[1] + L.CHANGE[3]) / 2 - 20, L.CHANGE[4], marker='black')
    K.weapon('balloony', -2010, 0, L.PED + L.W_H, marker='orange')
    K.weapon('pumper', L.PILE[0], L.PILE[1], L.PILE_TIERS * 16, marker='green')
    K.weapon('boaster', (L.W_DRUM_X[0] + L.W_DRUM_X[1]) / 2, 0, L.W_DRUM_Z - L.W_DRUM_R, marker='orange')
    K.weapon('bubbleg', 560, 100, 0, marker='green')
    A = {'imperius': [(2010, 1000, L.D_TOP), (-560, 300, L.TABLE_Z), (1300, 1900, 0)],
         'splasher': [(830, 1900, L.SINK_Z[1]), (-1984, -1120, L.W_DRUM_Z - L.W_DRUM_R), (-1300, 1700, 0)],
         'betty': [(L.CHANGE[0] + 60, -1700, 0), (2010, -1000, L.D_TOP), (-1300, 300, L.PED), (1300, -400, 0)],
         'balloony': [(-2010, -1000, L.PED + L.W_H), (-2010, 1000, L.PED + L.W_H), (560, -300, L.TABLE_Z), (-1700, -1900, 0)],
         'pumper': [(0, -680, 0), (1300, -1600, 0), (-1984, 560, L.W_DRUM_Z - L.W_DRUM_R)],
         'boaster': [(-1984, 1120, L.W_DRUM_Z - L.W_DRUM_R), (1964, 560, L.PLINTH), (-200, 900, 0)],
         'bubbleg': [(-560, -300, 0), (1964, -560, L.PLINTH), (0, 1600, 0), (-1300, -1300, L.PED)]}
    for w, spots in A.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((0, 0, 0), (1900, 1800, 0), (-1900, -1700, 0)):
        K.ammo('nipper', x, y, z)
    K.item('item_armor_padshield', (L.SOAPVEND[0] + L.SOAPVEND[2]) / 2 + 80, -1920, L.SOAPVEND[4])
    K.item('item_speedy', 560, 500, L.TABLE_Z)
    K.item('holdable_floater', 2010, 1000 - 200, L.D_TOP)
    for (x, y, z) in ((-560, -500, L.TABLE_Z), (-1400, 600, L.PED), (1964, 0, L.PLINTH), (0, 1450, 0)):
        K.item('item_armor_shard', x, y, z)


def spawns():
    for (x, y, a) in ((-900, -1500, 45), (900, -1500, 135), (-1000, 600, 0), (1000, 900, 180), (0, 900, 270), (0, -700, 90),
                      (-300, 1600, 270), (1300, 1500, 225), (-1700, 1800, 315), (1700, -1800, 135), (-1700, -1700, 45),
                      (1250, -300, 180), (-900, 100, 0), (300, -500, 90), (1400, 600, 180), (-500, -1800, 90)):
        K.spawn(x, y, 0, a)
    for (x, y, a) in ((-1300, -1000, 0), (-1300, 1000, 0)):
        K.spawn(x, y, L.PED, a)


def lights_and_sound():
    # fluorescent panels on the ceiling + their light, a dimmer street glow at the windows
    for x in (-1600, -800, 0, 800, 1600):
        for y in (-1400, -500, 400, 1300):
            K.custom(ML.PLACE['light_panel'], x, y, L.CEIL, lit=False, occupy=False)
            K.light(x, y, L.CEIL - 200, 900, '0.92 0.97 1')
    for x in (-1800, -700, 700, 1800):
        K.light(x, L.Y0 + 120, 900, 500, '1 0.5 0.6')
    for yc in L.W_YC:
        K.light(-1450, yc, L.PED + 400, 300, '0.9 0.95 1')
        K.light(-1984, yc, L.W_DRUM_Z, 160, '0.7 0.9 1')
        K.light(1964, yc, L.D_DRUM_Z, 160, '1 0.85 0.6')
    K.light(0, 1776, 900, 400, '0.9 0.95 1')
    for x in (-800, 800):
        K.rotating_model2(ML.IQM['fan'], (x, 0, L.CEIL - 48), 60)
    K.speaker(0, 0, 1800, 'machine/transformer', volume=0.25)
    K.speaker(0, L.Y0 + 200, 400, 'ambient/wind_night', volume=0.25)
    K.timer_sound(-1984, 0, L.PED + 300, 'machine/dingdong', 'cycle_done', 40, 20)
    K.trigger_sound((L.DOOR_X[0], L.Y0 + 16, 0), (L.DOOR_X[1], L.Y0 + 120, 96), 'misc/door_buzzer', 'door_buzz', wait=6)
    K.trigger_sound((1900, -200, L.D_TOP + 8), (2120, 200, L.D_TOP + 96), 'human/applause', 'top_applause', wait=12)


# ================================================================================================= textures, models, shader
def textures():
    LM.make_brush_textures()


def models():
    LM.make_all()


def shader():
    TX.write_shader(extra=[SH.sky('env/pc-friday-13th-512', sun=(250, 30), sun_int=10, skylight=(20, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    textures()
    models()
    shell()
    washers(); dryers(); sink(); tables(); mount_laundry(); south_side(); lost_sock_dimension()
    items(); spawns(); props(); lights_and_sound()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
