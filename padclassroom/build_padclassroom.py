#!/usr/bin/env python3
"""Padman's Classroom (wop_padclassroom) - FFA in a primary-school classroom on a sunny morning, built on woplib.

    OUT=<dir> python3 build_padclassroom.py          (wopbuild.py padclassroom preview / all)

Padman scale (~8u per cm, catalog models at 1.0). Room x -2304..2304, y -1920..1920, floor z 0, ceiling 2304.
x east, y north (the blackboard wall), windows in the south wall. Levels: chairs 320, tank floor 432, student desks 560,
teacher's desk 608, sill 720, chalk ledge 800, bookcase/tank rim 960, castle 976, cupboard top 1600.
See README.md for the design sheet.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wopmap
from wopmap import box, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH
import cl_models as CM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZC = 2304
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '30', '_color': '1 0.97 0.9'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
DESK_Z, TD_Z = CM.DESK_Z, CM.TD_Z
DESKS = [(-480, -80, 180), (480, -80, 180), (-480, -800, 0), (480, -800, 0)]      # x, y, angle (chair side -y at 0)
CHAIRS = [(-480, 310, 0), (480, 310, 0), (-480, -1190, 180), (480, -1190, 180)]
TD_C = (0, 1100)                         # teacher's desk x -640..640, y 800..1400, top 608
TCHAIR_C = (0, 1560)
SPIRAL_C = (-978, 1100)                  # exercise-book spiral round the jumbo pencil, top step meets the desk (x -640)
LEDGE = (-1440, 1760, 1440, 1920, 800)   # chalk tray: x0 y0 x1 y1 top
BOARD = (-1440, 1856, 832)               # board x half-width at x0..x1, z0..z1
BK_C = (-2144, 640)                      # bookcase x -2304..-1984, y 0..1280, top 960
TANK = (-2304, -1440, -1824, 0)          # cabinet + tank footprint
TANK_IN = (-2288, -1424, -1840, -16)     # inside the glass
GRAVEL_Z, WATER_Z, RIM_Z = 432, 920, 960
CASTLE_TOP = 976
RAMP_T = (-2240, -1000, -2032, -96)      # castle ramp inside the tank (rises north)
CHEST_C = (-1940, -850)
CB_C = (1984, 1600)                      # stationery cupboard x 1664..2304, y 1280..1920, top 1600
GLOBE_C = (1750, -900)
BIN_C = (1000, -1640)                    # tipped bin, axis x, open end -x
CRAYON_C = (-2000, -1680)
SILL = (-1760, -1920, 1760, -1728, 720)
WINDOWS = [(-1560, -860), (-350, 350), (860, 1560)]
WIN_Z = (760, 1880)
RAMP_W = (-1700, -880, -800, -720)       # giant ruler onto the desk group (rises east)
VAULT = (-640, -480, 640, 480); VAULT_Z = -1536
PCASE_C = (480, 20)
CB_TOP = CM.CB_H


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = CM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


def deco(name, x, y, z, angle=0, **kw):
    """custom MD3 without collision (paper balls, chalk, fish, lights)"""
    return K.custom(ML.PLACE[name], x, y, z, angle, occupy=False, **kw)


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: floor slab, walls (south wall in three pieces, each with a window and a sealed sky box behind),
    ceiling. Everything else is detail."""
    K.add(box((X0 - 32, Y0 - 32, -32), (X1 + 32, Y1 + 32, 0), {'top': T('lino'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZC), tex6(e=T('wall')), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZC), tex6(s=T('wall')), detail=False))
    cuts = [X0, -605, 605, X1]
    for k, (hx0, hx1) in enumerate(WINDOWS):
        K.sky_window((cuts[k], Y0 - 32, 0), (cuts[k + 1], Y0, ZC), (hx0, hx1, WIN_Z[0], WIN_Z[1]), T('wall'), T('sky'),
                     jamb_tex=T('frame'), glass_tex=T('glass'), face='n')
        cx, cz = (hx0 + hx1) / 2, (WIN_Z[0] + WIN_Z[1]) / 2
        fr = {'top': T('frame'), 'bot': T('frame'), 'side': T('frame')}
        K.add(box((cx - 10, Y0 - 3, WIN_Z[0]), (cx + 10, Y0 + 2, WIN_Z[1]), fr))                       # mullion
        K.add(box((hx0, Y0 - 3, cz - 10), (cx - 10, Y0 + 2, cz + 10), fr))                             # transoms
        K.add(box((cx + 10, Y0 - 3, cz - 10), (hx1, Y0 + 2, cz + 10), fr))
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # window sill (one long white board)
    x0, y0, x1, y1, z = SILL
    K.add(box((x0, y0, z - 32), (x1, y1, z), {'top': T('sill'), 'side': T('sill'), 'bot': T('sill')}))
    K.reserve(((x0, y0, z - 32), (x1, y1, z)))
    # blackboard (fitted art, never mirrored) + posters
    bx = BOARD[0]
    K.add(sign_box((bx, Y1 - 16, BOARD[2]), (-bx, Y1, BOARD[1]), T('board'), 2048, 728, facing='s', edge=T('ledge')))
    K.reserve(((bx, Y1 - 16, BOARD[2]), (-bx, Y1, BOARD[1])))
    K.add(sign_box((-2100, Y0, 1980), (-52, Y0 + 4, 2236), T('poster0'), 2048, 256, facing='n', edge=T('frame')))
    K.add(sign_box((52, Y0, 1980), (2100, Y0 + 4, 2236), T('poster1'), 2048, 256, facing='n', edge=T('frame')))
    K.add(sign_box((X0, 160, 1150), (X0 + 4, 1184, 1790), T('poster2'), 1024, 640, facing='e', edge=T('frame')))
    K.add(sign_box((X1 - 4, -1500, 900), (X1, -1000, 1600), T('poster3'), 640, 896, facing='w', edge=T('frame')))
    K.add(sign_box((X1 - 4, -800, 900), (X1, -300, 1600), T('poster4'), 640, 896, facing='w', edge=T('frame')))
    for k, y in enumerate((-100, 360, 820)):
        K.add(sign_box((X1 - 4, y, 1000), (X1, y + 360, 1450), T(f'poster{5 + k}'), 512, 640, facing='w', edge=T('frame')))
    K.add(sign_box((-2000, Y1 - 4, 1000), (-1600, Y1, 1500), T('poster8'), 512, 640, facing='s', edge=T('frame')))


def vault():
    """the secret: Detention - a sealed room under the world with lines on the board, three lonely desks and the
    goodies; a teleporter back to the front of the class"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 448
    wl, fl = T('det_wall'), T('det_floor')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': fl, 'side': wl, 'bot': wl}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': T('ceiling'), 'side': wl, 'top': wl}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=wl), detail=False),
          box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=wl), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=wl), detail=False),
          box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=wl), detail=False))
    K.add(sign_box((-400, y1 - 8, z + 100), (400, y1, z + 400), T('det_board'), 1024, 512, facing='s', edge=T('ledge')))
    K.reserve(((-400, y1 - 8, z + 100), (400, y1, z + 400)))
    for x in (-440, 0, 440):
        place('det_desk', x, 100, z)
    K.item('item_padpower', 0, -120, z); K.item('item_revival', -440, -200, z); K.item('holdable_killerducks', 440, -200, z)
    K.item('item_armor_padshield', 0, 330, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(0, 640, 0), angle=270, name='vault_exit')
    K.light(0, 0, z + 380, 650, '1 1 0.92'); K.light(-450, 0, z + 220, 280, '1 0.9 0.8'); K.light(450, 0, z + 220, 280, '1 0.9 0.8')


# ------------------------------------------------------------------------------------------------ furniture
def front_of_class():
    """blackboard ledge, teacher's desk + chair, the book spiral, the giant ruler from the east, cupboard"""
    x0, y0, x1, y1, z = LEDGE
    place('chalk_tray', 0, Y1, z)
    place('duster', 420, 1850, z, angle=8)
    deco('chalk_sticks', -260, 1820, z)
    K.catalog('pad_fruits/apple.md3', 980, 1860, z, angle=40)
    tx, ty = TD_C
    place('teacher_desk', tx, ty, 0)
    K.keep_clear(-230, 640, 230, 800, 0, 400); K.keep_clear(-230, 1400, 230, 1440, 0, 360)
    K.route('kneehole', (0, 660, 0), (0, 1340, 0))
    place('teacher_chair', *TCHAIR_C, 0)
    place('paper_stack', 240, 1000, TD_Z, angle=10)
    place('pencil_cup', 560, 880, TD_Z)
    K.catalog('pad_fruits/apple.md3', 330, 1260, TD_Z, angle=20)
    K.catalog('pad_cups/pad_cup01.md3', -520, 960, TD_Z, angle=200)
    K.catalog('pad_lamps/gooseneck.md3', -540, 1300, TD_Z, angle=300)
    K.catalog('pad_books/pad_cb_fl_lg.md3', -150, 1290, TD_Z, angle=95)
    K.catalog('pad_pencils/pad_pencilsr_lg.md3', 60, 940, TD_Z, angle=30, clip=False)
    # the spiral of exercise books round an upright jumbo pencil, top step at the desk's west edge
    sx, sy = SPIRAL_C
    K.spiral_stairs(sx, sy, 0, TD_Z, CM.SPIRAL_RIN, CM.SPIRAL_ROUT, CM.SPIRAL_STEP, CM.SPIRAL_END, route='spiral')
    deco('spiral_books', sx, sy, 0)
    place('jumbo_pencil', sx, sy, 0)
    st = CM.spiral_steps()
    a0 = math.radians(st[0][0] - CM.SPIRAL_STEP)
    K.keep_clear(sx + 190 * math.cos(a0) - 80, sy + 190 * math.sin(a0) - 80, sx + 190 * math.cos(a0) + 80,
                 sy + 190 * math.sin(a0) + 80, 0, 96)
    # stationery cupboard (walk in through the open south door)
    place('cupboard', *CB_C, 0)
    K.keep_clear(1450, 1300, 1664, 1600, 0, 120)
    K.route('cupboard_in', (1460, 1450, 0), (1920, 1450, 24))
    deco('glue', 1820, 1840, 24 + 400 + 16)


def fit_ruler(b, rect, along):
    """stretch the ruler image along a ramp's long side (the art has 0..100 cm)"""
    x0, y0, x1, y1 = rect
    for f in b.faces:
        if f.n[2] > 0.3:
            if along == 'x':
                f.sc = ((x1 - x0) / 1024, (y1 - y0) / 256)
            else:
                f.sc = ((x1 - x0) / 256, (y1 - y0) / 1024)


def desk_group():
    """four desks pushed into a table group, pencil bridges east-west, ruler bridges north-south, chairs outside"""
    for i, (x, y, a) in enumerate(DESKS):
        place(f'student_desk{i}', x, y, 0, angle=a)
    for (x, y, a), c in zip(CHAIRS, CM.CHAIR_COLS):
        place(f'chair_{c}', x, y, 0, angle=a)
    place('pencil_bridge', 0, -80, DESK_Z)
    place('pencil_bridge', 0, -800, DESK_Z)
    place('ruler_bridge', -480, -440, DESK_Z)
    place('ruler_bridge', 480, -440, DESK_Z)
    K.route('bridge_ns', (-480, -820, DESK_Z), (-480, -170, DESK_Z))
    K.route('bridge_ew', (-430, -150, DESK_Z), (430, -180, DESK_Z))
    # desk tops: pencil case (walk in), lunchbox, open book, apple
    px, py = PCASE_C
    K.clipped(K.tube_brushes((px, py, DESK_Z), 'x', CM.PCASE_L, CM.PCASE_R, CM.PCASE_T, closed_end='+'))
    deco('pencil_case', px, py, DESK_Z)
    K.route('pcase_in', (210, py, DESK_Z), (560, py, DESK_Z + 8))
    place('lunchbox', -560, 0, DESK_Z, angle=4)
    place('open_book', -560, -850, DESK_Z, angle=-6)
    K.catalog('pad_fruits/apple.md3', 680, -930, DESK_Z, angle=10)
    deco('eraser', -300, -650, DESK_Z, angle=30)
    K.catalog('pad_pencils/pad_pencilsb_lg.md3' if False else 'pad_pencils/pad_pencilsg_lg.md3', 640, -700, DESK_Z, angle=80, clip=False)
    K.catalog('pad_pencils/pad_pencilsy_lg.md3', -680, -100, DESK_Z, angle=10, clip=False)
    # the giant ruler from the floor onto the group's south-west desk
    rb = K.ramp(*RAMP_W, 0, DESK_Z, 'e', {'top': T('ruler'), 'side': T('ruler'), 'bot': CAULK}, route='ruler_w')
    fit_ruler(rb, RAMP_W, 'x')
    K.keep_clear(RAMP_W[0] - 100, RAMP_W[1], RAMP_W[0], RAMP_W[3], 0)
    # bags under the desks (cover under the table group)
    for (x, y, a), c in zip(DESKS, ('red', 'blue', 'green', 'red')):
        place(f'bag_{c}', x, y, 0, angle=a + 90)


def west_wall():
    """bookcase (walk-in nook), fish tank on its cabinet with the castle ramp, the chest (secret), crayon box"""
    place('bookcase', *BK_C, 0)
    K.route('nook_in', (-1820, 800, 0), (-2170, 800, 16))
    K.catalog('pad_books/pad_cb_fl_lg.md3', -2200, 360, CM.BK_H, angle=0)
    K.catalog('pad_books/pad_cb_ur_lg.md3', -2220, 1150, CM.BK_H, angle=0)
    K.catalog('pad_ddmix/plants/flower_pink.md3', -2180, 150, CM.BK_H)
    # tank: cabinet, glass walls, gravel, water, castle ramp, chest, bubbler, fish, plants
    tx0, ty0, tx1, ty1 = TANK
    place('tank_cabinet', (tx0 + tx1) / 2, (ty0 + ty1) / 2, 0)
    ix0, iy0, ix1, iy1 = TANK_IN
    gl = T('glass')
    z0 = CM.TANK_CAB_H
    walls = [box((tx0, ty0, z0), (ix0, ty1, RIM_Z), gl), box((ix1, ty0, z0), (tx1, ty1, RIM_Z), gl),
             box((ix0, ty0, z0), (ix1, iy0, RIM_Z), gl), box((ix0, iy1, z0), (ix1, ty1, RIM_Z), gl)]
    K.add(*walls)
    K.add(box((ix0, iy0, z0), (ix1, iy1, GRAVEL_Z), {'top': T('gravel'), 'side': T('gravel'), 'bot': CAULK}))
    K.reserve(((tx0, ty0, z0), (tx1, ty1, RIM_Z)))
    # castle at the north end: tower under a platform that runs over the glass onto the bookcase top
    cx = (ix0 - 2000) / 2 + 0
    tower = box((ix0, RAMP_T[3], GRAVEL_Z), (-2000, iy1, RIM_Z), WCLIP)
    plat = box((ix0, RAMP_T[3], RIM_Z), (-2000, 16, CASTLE_TOP), WCLIP)
    tur = wopmap.cyl(-2144 + CM.TURRET[0], -56 + CM.TURRET[1], 52, CASTLE_TOP, CASTLE_TOP + 190, WCLIP, 12)
    K.add(tower, plat, tur)
    deco('castle', -2144, -56, GRAVEL_Z)
    rx0, ry0, rx1, ry1 = RAMP_T
    ramp = K.ramp(rx0, ry0, rx1, ry1, GRAVEL_Z, CASTLE_TOP, 'n', {'top': T('stone'), 'side': T('stone'), 'bot': CAULK})
    K.route('castle_top', (-2120, 400, RIM_Z), (-2120, -60, CASTLE_TOP))
    # chest (secret) and bubbler
    chx, chy = CHEST_C
    place('chest', chx, chy, GRAVEL_Z)
    chest_b = list(K.M.world[-5:])
    deco('bubbler', -1880, -1380, GRAVEL_Z)
    K.water_box((ix0, iy0, GRAVEL_Z), (ix1, iy1, WATER_Z), T('water'), cutters=[ramp, tower] + chest_b)
    K.rotating_model2(f'models/{NS}/fish_big.md3', (-2064, -1250, 700), 18)
    K.rotating_model2(f'models/{NS}/fish_small.md3', (-2064, -1250, 560), 26, reverse=True)
    for (p, x, y) in (('waterplant1a', -1930, -300), ('waterplant1b', -2200, -1340), ('waterplant1a', -1930, -1060)):
        K.model_on(f'pad_ddmix/plants/{p}.md3', x, y, GRAVEL_Z, scale=0.6, angle=(x * 7) % 360)   # decor in the water
    # crayon box (walk in from the east)
    place('crayon_box', *CRAYON_C, 0)
    K.route('crayon_in', (-1560, CRAYON_C[1], 0), (-1960, CRAYON_C[1], 12))


def south_and_east():
    """windows: sill, radiators; the floor globe, the tipped bin, bags, notice wall"""
    for (hx0, hx1) in WINDOWS:
        place('radiator', (hx0 + hx1) / 2, Y0 + 52, 0, angle=180)
    for (x, p) in ((-1400, 'pad_sunflower/pad_sunflower.md3'), (-700, 'pad_sunflower/pad_sunflower3.md3'),
                   (700, 'pad_sunflower/pad_sunflower2.md3'), (1500, 'pad_sunflower/pad_sunflower6.md3')):
        K.catalog(p, x, -1830, SILL[4], angle=90)
    place('pencil_cup', -1000, -1830, SILL[4])
    gx, gy = GLOBE_C
    place('globe_stand', gx, gy, 0)
    K.rotating_model2(f'models/{NS}/globe_ball.md3', (gx, gy, CM.GLOBE_Z), 14)
    bx, by = BIN_C
    K.clipped(K.tube_brushes((bx, by, 0), 'x', CM.BIN_L, CM.BIN_R, CM.BIN_T, closed_end='+'))
    deco('tipped_bin', bx, by, 0)
    K.keep_clear(bx - CM.BIN_L / 2 - 110, by - 120, bx - CM.BIN_L / 2, by + 120, 0)
    K.route('bin_in', (bx - CM.BIN_L / 2 - 90, by, 0), (bx + 80, by, CM.BIN_T))
    deco('paper_balls', bx - 520, by + 20, 0)
    # cover on the open floor (sightlines): a chair stack, art trolley, toy boxes, gym ball, atlases
    place('chair_stack', 1440, 760, 0, angle=200)
    place('art_trolley', 1380, -330, 0, angle=80)
    place('toy_box', 1850, 260, 0, angle=270)
    place('toy_box', 380, -1676, 0)
    place('gym_ball', -620, -1720, 0)
    place('beanbag_blue', 1700, -1700, 0, angle=120)
    place('beanbag_green', 900, 230, 0, angle=200)
    place('recycle_box', 0, -440, 0)
    place('toy_box', -1000, 1750, 0, angle=180)
    place('recycle_box', 1000, 1760, 0, angle=90)
    place('beanbag_blue', -1050, 420, 0, angle=330)
    place('bag_green', -1250, -1470, 0, angle=30)
    place('atlas_pile', -1560, 280, 0, angle=15)
    place('bag_blue', 2150, -1250, 0, angle=270)
    place('bag_green', 2140, -350, 0, angle=260)
    place('bag_red', 2150, 450, 0, angle=280)


def ceiling_things():
    for x in (-1500, 0, 1500):
        for y in (-900, 700):
            deco('fluoro', x, y, ZC, lit=False)
    deco('clock', 0, Y1, 2080, lit=False)
    K.rotating_model2(f'models/{NS}/clock_hand.md3', (0, Y1 - 32, 2080), 6, axis='y')
    K.rotating_model2(f'models/{NS}/plane_mobile.md3', (0, -440, 2000), 10)


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    K.jumppad(1250, -800, 0, land=(600, -800, DESK_Z), apex=DESK_Z + 260, name='pad_desks', skin=CM.pad_skin('pad_book_blue', (1250, -800), (600, -800, DESK_Z)), edges=[(800, -800, DESK_Z)])
    K.jumppad(-400, 1250, TD_Z, land=(-400, 1850, LEDGE[4]), apex=LEDGE[4] + 150, name='pad_ledge', skin=CM.pad_skin('pad_eraser', (-400, 1250), (-400, 1850, LEDGE[4])),
              edges=[(-400, 1760, LEDGE[4])])
    K.jumppad(-1400, 1500, 0, land=(-1400, 1850, LEDGE[4]), apex=LEDGE[4] + 170, name='pad_ledge_w', skin=CM.pad_skin('pad_book_red', (-1400, 1500), (-1400, 1850, LEDGE[4])),
              edges=[(-1400, 1760, LEDGE[4])])
    K.jumppad(760, 1840, LEDGE[4], land=(1990, 1620, CB_TOP), apex=CB_TOP + 230, name='pad_cupboard', skin=CM.pad_skin('pad_eraser', (760, 1840), (1990, 1620, CB_TOP)), ceiling=ZC,
              edges=[(1664, 1700, CB_TOP)])
    K.jumppad(500, 1250, TD_Z, land=(1980, 1480, CB_TOP), apex=CB_TOP + 200, name='pad_cupboard2', skin=CM.pad_skin('pad_book_green', (500, 1250), (1980, 1480, CB_TOP)), ceiling=ZC,
              edges=[(1664, 1430, CB_TOP)])
    K.jumppad(-1700, 640, 0, land=(-2150, 640, CM.BK_H), apex=CM.BK_H + 170, name='pad_bookcase', skin=CM.pad_skin('pad_pcase', (-1700, 640), (-2150, 640, CM.BK_H)), edges=[(-1984, 640, CM.BK_H)])
    K.jumppad(0, -1450, 0, land=(0, -1830, SILL[4]), apex=SILL[4] + 150, name='pad_sill', skin=CM.pad_skin('pad_book_yellow', (0, -1450), (0, -1830, SILL[4])), edges=[(0, SILL[3], SILL[4])])
    K.jumppad(-1540, -1180, 0, land=(-2010, -1180, GRAVEL_Z), apex=RIM_Z + 110, name='pad_tank',
              skin=CM.pad_skin('pad_book_red', (-1540, -1180), (-2010, -1180)), edges=[(-1824, -1180, RIM_Z)])
    K.jumppad(1100, 700, 0, land=(450, 1000, TD_Z), apex=TD_Z + 220, name='pad_teacher', skin=CM.pad_skin('pad_pcase', (1100, 700), (450, 1000, TD_Z)), edges=[(640, 950, TD_Z)])


def items():
    K.weapon('imperius', -800, 1840, LEDGE[4], marker='purple')
    K.weapon('betty', 1950, 1700, CB_TOP, marker='black')
    K.weapon('balloony', -2150, 880, CM.BK_H, marker='orange')
    K.weapon('splasher', -1960, -1300, GRAVEL_Z, marker='blue')
    K.weapon('pumper', -80, 1150, TD_Z, marker='green')
    K.weapon('boaster', BIN_C[0] + 110, BIN_C[1], CM.BIN_T, marker='orange')
    K.weapon('bubbleg', 380, -880, DESK_Z, marker='green')
    ammo = {'imperius': [(1300, 1840, LEDGE[4]), (-2170, 760, 16), (2150, 1450, CB_TOP)],
            'betty': [(1900, 1500, 24), (1350, -1830, SILL[4]), (-2080, -1680, 12), (150, 1250, TD_Z)],
            'balloony': [(-2120, -50, CASTLE_TOP), (-1650, 1350, 0), (GLOBE_C[0], GLOBE_C[1] - 150, 32), (-400, -850, DESK_Z)],
            'splasher': [(-1930, -620, GRAVEL_Z), (-1350, -1830, SILL[4]), (-1500, -150, 0), (-700, 1850, LEDGE[4])],
            'pumper': [(-560, -180, DESK_Z), (1450, 1400, 0), (-1900, -1500, 0), (0, 1100, 0)],
            'boaster': [(PCASE_C[0] + 60, PCASE_C[1], DESK_Z + 8), (580, -150, DESK_Z), (-1350, 300, 0), (1300, -400, 0)],
            'bubbleg': [(-580, -760, DESK_Z), (1500, 250, 0), (-1200, -1450, 0), (300, -1830, SILL[4]), (0, -1300, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', 1200, 1000, 0); K.ammo('nipper', -1000, 500, 0); K.ammo('nipper', 1700, -1500, 0)
    K.item('item_armor_padshield', 1960, 1380, 24)
    K.item('item_armor_shard', 400, 1850, LEDGE[4]); K.item('item_armor_shard', -2150, 1000, CM.BK_H)
    K.item('item_speedy', 120, -1830, SILL[4])
    K.item('item_jumper', -380, -60, DESK_Z)
    K.item('holdable_floater', 0, 1180, 0)
    K.station(2150, 950, 0, ang=180)
    for (x, y, z, a) in ((-1500, -350, 0, 0), (-1250, 650, 0, 330), (0, 420, 0, 270), (1300, 350, 0, 180),
                         (1950, -100, 0, 180), (1500, -1350, 0, 135), (-350, -1580, 0, 90), (350, -1580, 0, 90),
                         (-1500, -1150, 0, 45), (-1650, 1000, 0, 300), (1250, 600, 0, 225), (-850, -440, 0, 0),
                         (1700, 1050, 0, 200), (480, -200, DESK_Z, 270)):
        K.spawn(x, y, z, a)


def secret():
    """swim into the open treasure chest at the bottom of the fish tank -> Detention"""
    chx, chy = CHEST_C
    K.secret((chx - 68, chy - 44, GRAVEL_Z + 10), (chx + 68, chy + 44, GRAVEL_Z + 60), dest=(0, -200, VAULT_Z), angle=90,
             name='chest')


def lights_sounds():
    K.light_grid(X0, Y0, X1, Y1, 1950, 768, 3300, color='1 0.98 0.92')
    for (hx0, hx1) in WINDOWS:                                                   # daylight spilling off the sill
        K.light((hx0 + hx1) / 2, -1600, 900, 500, '1 0.95 0.8')
    K.light(0, 1100, 300, 380, '1 0.9 0.8')                                       # under the teacher's desk
    K.light(1990, 1450, 300, 420, '1 0.95 0.85')                                  # inside the cupboard
    K.light(-2060, 800, 160, 260, '1 0.9 0.8')                                    # bookcase nook
    K.light(-2064, -720, 1080, 600, '0.6 0.85 1'); K.light(-2064, -1150, 700, 420, '0.5 0.8 1')   # tank
    K.light(BIN_C[0] - 60, BIN_C[1], 150, 260, '0.8 0.9 1')                       # inside the bin
    K.light(CRAYON_C[0], CRAYON_C[1], 130, 240, '1 0.95 0.7')                     # inside the crayon box
    K.light(0, -440, 300, 600, '1 0.95 0.9')                                      # under the table group
    K.light(-1300, 1850, 1000, 350, '1 0.95 0.9'); K.light(1300, 1850, 1000, 350, '1 0.95 0.9')   # ledge
    K.light(-2144, 640, 1350, 260, '1 0.95 0.9')                                  # over the bookcase
    K.speaker(0, Y1 - 60, 2080, 'machine/clock_ticking')
    K.speaker(-2064, -720, 800, 'machine/fishtank')
    K.timer_sound(0, -1800, 1500, 'animal/blackbird', 'birds', 25, 12)
    K.timer_sound(-900, -1800, 1500, 'animal/bird_blackcap', 'birds2', 35, 15)
    K.timer_sound(0, 0, 2200, 'machine/dingdong', 'school_bell', 90, 30)
    K.trigger_sound((1800, 1450, CB_TOP), (2200, 1850, CB_TOP + 96), 'human/applause', 'summit', wait=8)


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = CM.textures(K)
    CM.all_models()                    # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); vault(); front_of_class(); west_wall(); desk_group(); south_and_east(); ceiling_things()
    secret(); pads(); items(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
