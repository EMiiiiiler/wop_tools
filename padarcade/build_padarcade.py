#!/usr/bin/env python3
"""Midnight Arcade (wop_padarcade) - FFA in an amusement arcade after closing time, Padman scale (~8u per cm).

    OUT=<dir> python3 build_padarcade.py        (or: wopbuild.py padarcade gen / preview / check / all)

  Claw King      centre: in through the prize flap (east side), up the prize-chute ramp inside the base, out through the
                 prize hole into the glass case: Imperius on the plush pile under the swinging claw; pad onto the roof
  Roll-a-Ball    east: three skee-ball lanes up to the target decks, the 100-ring pads onto the backboards (Balloony)
  air hockey     west: a glowing table to fight on (Pumper), 16u stairs up its north side, a pad from the south
  prize wall     south-west: 16u stairs onto the first shelf, a pad to the top shelf (Betty), prize counter in front
  north          prize wheel over a stage (Bubble G), cabinet rows (pads onto their tops), dance machine (Boaster)
  secret         behind the photo booth curtain -> the Hall of High Scores -> teleporter back
The hall is the only structural brush set (one box); everything else is detail (low portal count).
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
from wopmap import box, cyl, hull, carve, sub_rects, sign_box, ngon
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL
import layout as L
import ar_models as AM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = L.BOUNDS
K = MapKit(MAP, NS, LONG, L.BOUNDS, worldspawn={'_ambient': '22', '_color': '0.85 0.8 1'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
AM.init(TX)


def tx(top, side=None, bot=CAULK):
    return {'top': T(top), 'side': T(side or top), 'bot': bot}


def place(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, **kw)


def side_tex(outer, inner, top, bottom, centre):
    """texfn for solid_piece boxes: outward faces `outer`, faces pointing at `centre` `inner`, tops/bottoms"""
    def f(c, n, poly):
        if n[2] > 0.7: return top, ML.planar_uv(n, 256)
        if n[2] < -0.7: return bottom, ML.planar_uv(n, 256)
        d = np.array([centre[0] - c[0], centre[1] - c[1], 0])
        return (inner if np.dot(d, n) > 0 else outer), ML.planar_uv(n, 256)
    return f


# ================================================================================================= the hall
def hall():
    w = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: T('wall')})
    K.add(box((X0 - 32, Y0 - 32, -32), (X1 + 32, Y1 + 32, 0), {'top': T('carpet'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, L.CEIL), w('e'), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, L.CEIL), w('w'), detail=False))
    K.add(box((X0, Y0 - 32, 0), (X1, Y0, L.CEIL), w('n'), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, L.CEIL), w('s'), detail=False))
    K.add(box((X0 - 32, Y0 - 32, L.CEIL), (X1 + 32, Y1 + 32, L.CEIL + 32), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    # neon signs on dark backing boards
    K.add(sign_box((X0, -500, 1500), (X0 + 4, 500, 1750), T('neon_sign'), 1024, 256, back=CAULK, facing='e', edge=T('cab_black')))
    K.add(sign_box((-1700, Y0, 1000), (-1100, Y0 + 4, 1200), T('neon_prizes'), 512, 128, back=CAULK, facing='n', edge=T('cab_black')))
    K.light_grid(X0, Y0, X1, Y1, 1700, 900, 520, '0.85 0.75 1')
    for (x, y, c) in ((-1500, 0, '0.4 0.9 1'), (1500, -400, '1 0.8 0.3'), (0, 1700, '1 0.4 0.8'), (-1500, -1700, '0.5 1 0.6')):
        K.light(x, y, 900, 600, c)
    K.speaker(0, 0, 600, 'machine/fan_pc'); K.speaker(1800, -400, 400, 'machine/transformer')
    K.speaker(-1800, 1100, 400, 'machine/electric_sizzle')


# ================================================================================================= Claw King
def claw_king():
    x0, y0, x1, y1 = L.CLAW
    bh, wl = L.BASE_H, L.WALL
    f0, f1 = L.FLAP
    h0, h1, hy0, hy1 = L.HOLE
    base = [box((x0, y0, 0), (x1, y0 + wl, bh), WCLIP), box((x0, y1 - wl, 0), (x1, y1, bh), WCLIP),
            box((x0, y0 + wl, 0), (x0 + wl, y1 - wl, bh), WCLIP),
            box((x1 - wl, f1, 0), (x1, y1 - wl, bh), WCLIP), box((x1 - wl, y0 + wl, 208), (x1, f1, bh), WCLIP)]
    for r in sub_rects((x0 + wl, y0 + wl, x1 - wl, y1 - wl), [(h0, hy0, h1, hy1)]):
        base.append(box((r[0], r[1], bh - 16), (r[2], r[3], bh), WCLIP))
    rd = TX.material('cab_red_m', TL.solid((190, 30, 40), 3, 5, 128), 'lms', v=0.12)
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    bed = TX.material('prize_bed', AM.fur((120, 60, 160), 61), shade=30)
    K.solid_piece('claw_base', base, side_tex(rd, bk, bed, bk, (0, 0)))
    place('claw_trim', 0, 0, 0, 0, occupy=False)
    # the prize chute: a 28-degree ramp from the flap up to the prize hole (bots walk it)
    K.ramp(h0, y0 + wl, x1 - wl, f1, 0, bh, 'w', tx('cab_black'), route='prize_chute')
    # glass case, roof and marquee
    place('claw_case', 0, 0, 0, 0, occupy=False)
    for b in (box((x0, y0, bh), (x1, y0 + 24, L.GLASS_TOP), WCLIP), box((x0, y1 - 24, bh), (x1, y1, L.GLASS_TOP), WCLIP),
              box((x0, y0 + 24, bh), (x0 + 24, y1 - 24, L.GLASS_TOP), WCLIP), box((x1 - 24, y0 + 24, bh), (x1, y1 - 24, L.GLASS_TOP), WCLIP),
              box((x0, y0, L.GLASS_TOP), (x1, y1, L.ROOF_TOP), WCLIP), box((x0 + 40, y1 - 80, L.ROOF_TOP), (x1 - 40, y1 - 20, L.ROOF_TOP + 200), WCLIP)):
        K.add(b)
    # the plush pile: 16u plates under the teddies
    for i, ((a, b, c, d), h) in enumerate(L.PILE):
        K.add(box((a, b, bh + 16 * i), (c, d, bh + 16 * (i + 1)), WCLIP))
    place('plush_pile', 0, 0, 0, 0, occupy=False)
    K.pendulum_model2(ML.IQM['claw'], (0, 100, L.GLASS_TOP - 40), 8, 520)
    K.occupy(x0 - 130, y0 - 130, x1 + 10, y1 + 10, 0, L.ROOF_TOP + 200)
    K.keep_clear(x1, f0 - 20, x1 + 140, f1 + 20, 0)
    K.light(200, 200, 1150, 380, '1 0.85 0.95'); K.light(-300, -200, 300, 160, '0.6 0.6 1')
    K.speaker(0, 0, 900, 'machine/mechanics', loop=False, targetname='claw_whirr')
    K.M.ent('func_timer', (0, -700, 900), target='claw_whirr', wait=20, random=8, spawnflags=1)
    K.jumppad(0, y0 - 560, 0, land=(0, -150, L.ROOF_TOP), apex=L.ROOF_TOP + 250, name='pad_clawroof',
              edges=[(0, y0, L.ROOF_TOP)])


# ================================================================================================= Roll-a-Ball alley
def skee():
    rd = TX.material('cab_red_m', TL.solid((190, 30, 40), 3, 5, 128), 'lms', v=0.12)
    bk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    yA, yB = L.LANES[0][0] - 80, L.LANES[-1][1] + 80
    # side panels: 80 wide, 140 over the lane surface, following the ramp
    panels = [(yA, L.LANES[0][0])] + [(L.LANES[i][1], L.LANES[i + 1][0]) for i in range(len(L.LANES) - 1)] + [(L.LANES[-1][1], yB)]
    pb = []
    for (a, b) in panels:
        pts = []
        for (x, z) in ((L.LANE_X0, 140), (L.RAMP_X0, 140), (L.RAMP_X1, L.DECK_Z + 140), (L.DECK_X1, L.DECK_Z + 140)):
            for y in (a, b): pts += [(x, y, 0), (x, y, z)]
        for (xa, xb, za, zb) in ((L.LANE_X0, L.RAMP_X0, 140, 140), (L.RAMP_X0, L.RAMP_X1, 140, L.DECK_Z + 140), (L.RAMP_X1, L.DECK_X1, L.DECK_Z + 140, L.DECK_Z + 140)):
            pb.append(hull([(x, y, z) for (x, zz) in ((xa, za), (xb, zb)) for y in (a, b) for z in (0, zz)], WCLIP))
    pb.append(box((L.DECK_X1, yA, 0), (X1, yB, L.BOARD_TOP), WCLIP))
    K.solid_piece('skee_cabinets', pb, side_tex(rd, rd, bk, bk, (0, -400)))
    K.reserve(*pb)
    for i, (a, b) in enumerate(L.LANES):
        yc = (a + b) / 2
        K.ramp(L.RAMP_X0, a, L.RAMP_X1, b, 0, L.DECK_Z, 'e', tx('lane_wood'))
        K.add(box((L.RAMP_X1, a, 0), (L.DECK_X1, b, L.DECK_Z), tx('lane_wood')))
        K.add(box((L.LANE_X0, a, 0), (L.RAMP_X0, b, 2), tx('lane_wood')))
        place('skee_rings', (L.RAMP_X1 + L.DECK_X1) / 2 + 40, yc, L.DECK_Z, 0, occupy=False)
        K.add(sign_box((L.DECK_X1 - 4, a + 10, 640), (L.DECK_X1, b - 10, 760), T('marq_skee'), 512, 128, back=CAULK, facing='w', edge=T('cab_black')))
        K.jumppad(L.RAMP_X1 + 70, yc, L.DECK_Z, land=(2190, yc, L.BOARD_TOP), apex=L.BOARD_TOP + 300, name=f'pad_skee{i}',
                  edges=[(L.DECK_X1, yc, L.BOARD_TOP)])
        K.route(f'skee_lane{i}', (L.LANE_X0 - 80, yc, 0), (L.RAMP_X1 + 140, yc + 100, L.DECK_Z))
        K.keep_clear(L.LANE_X0 - 120, a, L.LANE_X0, b, 0)
        K.light(L.RAMP_X1 + 120, yc, L.DECK_Z + 400, 220, '1 0.85 0.4')
    K.speaker(1700, -400, 200, 'misc/bicycle_bell', loop=False, targetname='skee_bell')
    K.M.ent('func_timer', (1700, -400, 1500), target='skee_bell', wait=25, random=10, spawnflags=1)


# ================================================================================================= air hockey
def air_hockey():
    x0, y0, x1, y1 = L.TABLE
    z = L.TABLE_Z
    blk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    bl = TX.material('hockey_blue', TL.solid((30, 70, 160), 2, 63, 64), 'lms', v=0.12)
    body = [box((x0, y0, 0), (x1, y1, z - 8), WCLIP)]
    K.solid_piece('hockey_body', body, side_tex(bl, bl, blk, blk, ((x0 + x1) / 2, 0)))
    K.add(box((x0, y0, z - 8), (x1, y1, z), {'top': T('hockey'), 'side': T('chrome'), 'bot': CAULK}))
    rims = [box((x0, y0, z), (x1, y0 + 24, z + 24), WCLIP), box((x0, y1 - 24, z), (-1300, y1, z + 24), WCLIP),
            box((-1180, y1 - 24, z), (x1, y1, z + 24), WCLIP)]
    for xa in (x0, x1 - 24):
        rims += [box((xa, y0 + 24, z), (xa + 24, -150, z + 24), WCLIP), box((xa, 150, z), (xa + 24, y1 - 24, z + 24), WCLIP)]
    ch = TX.material('chrome_m', TL.metal((200, 204, 212)), 'lms', v=0.3)
    K.solid_piece('hockey_rims', rims, side_tex(ch, ch, ch, ch, (0, 0)))
    K.reserve(((x0, y0, 0), (x1, y1, z)))
    cx = (x0 + x1) / 2
    place('hockey_bits', cx, 0, z, 0, occupy=False)
    K.add(cyl(cx, 0, 86, z, z + 24, WCLIP, 12))
    for x in (cx - 320, cx + 320):
        K.add(cyl(x, 0, 104, z, z + 30, WCLIP, 12)); K.add(cyl(x, 0, 44, z + 30, z + 150, WCLIP, 8))
    sx0, sy0, sx1, sy1 = L.TSTAIR
    K.stairs16(sx0, sy0, sx1, sy1, 0, z, 'e', tx('cab_black'), route='hockey_stairs')
    K.reserve(((sx0, sy0, 0), (sx1, sy1, z)))
    K.keep_clear(sx0 - 110, sy0, sx0, sy1, 0)
    K.jumppad(cx, y0 - 300, 0, land=(cx, -200, z), apex=z + 170, name='pad_hockey', edges=[(cx, y0, z + 24)])
    K.light(cx, 0, z + 500, 420, '0.6 0.85 1')


# ================================================================================================= prize wall
def prize_wall():
    x0, y0, x1, y1 = L.SHELF
    sh = TX.material('shelf_m', TL.planks((230, 220, 200), n_planks=3), shade=30)
    pieces = [box((x0, y0, L.SHELF1_Z - 16), (x1, y1, L.SHELF1_Z), WCLIP),
              box((x0, y0, L.SHELF2_Z - 16), (L.SHELF2_X1, y1, L.SHELF2_Z), WCLIP),
              box((x1 - 24, y0, 0), (x1, y1, L.SHELF1_Z - 16), WCLIP),
              box((L.SHELF2_X1 - 24, y0, L.SHELF1_Z), (L.SHELF2_X1, y1, L.SHELF2_Z - 16), WCLIP)]
    K.solid_piece('prize_shelves', pieces, side_tex(sh, sh, sh, sh, (0, 0)))
    K.reserve(*pieces)
    sx0, sy0, sx1, sy1 = L.PSTAIR
    K.stairs16(sx0, sy0, sx1, sy1, 0, L.SHELF1_Z, 'w', tx('shelf'), route='prize_stairs')
    K.reserve(((sx0, sy0, 0), (sx1, sy1, L.SHELF1_Z)))
    K.keep_clear(sx1, sy0, sx1 + 110, sy1, 0)
    ym = (y0 + y1) / 2
    K.jumppad(-1000, ym, L.SHELF1_Z, land=(-1620, ym, L.SHELF2_Z), apex=L.SHELF2_Z + 160, name='pad_topshelf',
              edges=[(L.SHELF2_X1, ym, L.SHELF2_Z)])
    # prizes on the shelves
    for (x, z, nm, sc) in ((-2200, L.SHELF1_Z, 'gummybears/redbear.md3', 1.0), (-1900, L.SHELF1_Z, 'pad_ducks/pad_duck.md3', 0.8),
                           (-1250, L.SHELF1_Z, 'pad_ball/pad_basketball.md3', 1.4), (-2200, L.SHELF2_Z, 'pad_statues/statue_super.md3', 0.9),
                           (-2030, L.SHELF2_Z, 'gummybears/greenbear.md3', 1.0), (-760, L.SHELF1_Z, 'gummybears/yellowbear.md3', 1.0)):
        K.catalog(nm, x, ym - 40, z, scale=sc, lit=True, search=80)
    for (x, z, nm) in ((-1650, L.SHELF1_Z, 'teddy_pink'), (-2000, L.SHELF1_Z, 'teddy_blue'), (-1350, 0, 'teddy_yellow')):
        K.prop(ML.PLACE[nm], x, ym, z, boxes=[((-60, -50, 0), (60, 50, 200))], angle=0, search=80)
    # prize counter in front
    cx0, cy0, cx1, cy1 = L.COUNTER
    gl = TX.material('case_glass', TL.solid((160, 200, 220), 2, 11, 64), 'glass', c='0.07 0.09 0.11')
    blk = TX.material('cab_black_m', TL.solid((24, 22, 30), 2, 7, 128), shade=30)
    K.solid_piece('prize_counter', [box((cx0, cy0, 0), (cx1, cy1, 140), WCLIP)], side_tex(blk, blk, blk, blk, (0, 0)))
    K.add(box((cx0, cy0, 140), (cx1, cy1, L.COUNTER_H), {'top': T('glass'), 'side': T('glass'), 'bot': CAULK}))
    K.reserve(((cx0, cy0, 0), (cx1, cy1, L.COUNTER_H)))
    K.light(-1500, -1900, 1200, 300, '0.5 1 0.9'); K.light(-1000, -1250, 600, 260)


# ================================================================================================= north: wheel, cabinets, dance
def north():
    sx0, sy0, sx1, sy1 = L.STAGE
    K.add(box((sx0, sy0, 0), (sx1, sy1, L.STAGE_Z), tx('felt_blue', 'cab_black')))
    K.reserve(((sx0, sy0, 0), (sx1, sy1, L.STAGE_Z)))
    K.stairs16(-300, sy0 - 6 * 32, 300, sy0, 0, L.STAGE_Z, 'n', tx('cab_black'), route='stage_steps')
    K.keep_clear(-300, sy0 - 6 * 32 - 110, 300, sy0 - 6 * 32, 0)
    wx, wy, wz = L.WHEEL
    place('wheel_frame', wx, wy, wz, 0, occupy=False)
    K.add(box((wx - 760, wy + 18, wz - 760), (wx + 760, Y1, wz + 760), WCLIP))
    K.rotating_model2(ML.IQM['wheel'], (wx, wy - 40, wz), 12, axis='y')
    K.light(0, 1500, 1500, 500, '1 0.6 0.9')
    # cabinet rows facing south, pads onto their tops
    games = ['blastronaut', 'padpong', 'duckdash']
    for (rx0, ry0, n) in L.CAB_ROWS:
        cy = ry0 + L.CAB_D / 2
        for k in range(n):
            cx = rx0 + L.CAB_W / 2 + k * L.CAB_W
            place('cab_' + games[(k + (rx0 > 0)) % 3], cx, cy, 0, 0, boxes=[((-L.CAB_W / 2 + 4, -L.CAB_D / 2 + 4, 0), (L.CAB_W / 2 - 4, L.CAB_D / 2 - 4, L.CAB_H))])
        mid = rx0 + n * L.CAB_W / 2
        K.jumppad(mid, ry0 - 300, 0, land=(mid, cy + 40, L.CAB_H), apex=L.CAB_H + 260, name=f'pad_cabs_{"w" if rx0 < 0 else "e"}',
                  edges=[(mid, ry0, L.CAB_H)])
    for (x, g) in ((-380, 'duckdash'), (380, 'blastronaut')):
        place('cab_' + g, x, 1000, 0, 0, boxes=[((-L.CAB_W / 2 + 4, -L.CAB_D / 2 + 4, 0), (L.CAB_W / 2 - 4, L.CAB_D / 2 - 4, L.CAB_H))])
    # dance machine
    dx0, dy0, dx1, dy1 = L.DANCE
    place('dance', (dx0 + dx1) / 2, (dy0 + dy1) / 2, 0, 0, occupy=False)
    K.add(box((dx0, dy0, 0), (dx1, dy1 - 160, L.DANCE_Z), WCLIP))
    K.add(box((dx0, dy1 - 160, 0), (dx1, dy1, 1300), WCLIP))
    K.reserve(((dx0, dy0, 0), (dx1, dy1, L.DANCE_Z)), ((dx0, dy1 - 160, 0), (dx1, dy1, 1300)))
    K.stairs16(dx0, dy0 - 96, dx1, dy0, 0, L.DANCE_Z, 'n', tx('cab_black'), route='dance_steps')
    K.light((dx0 + dx1) / 2, (dy0 + dy1) / 2, 600, 300, '0.6 1 0.6')
    K.speaker((dx0 + dx1) / 2, dy1 - 200, 400, 'machine/tv_upstairs')


# ================================================================================================= south-east: booth, racer
def south():
    bx0, by0, bx1, by1 = L.BOOTH
    place('booth', (bx0 + bx1) / 2, (by0 + by1) / 2, 0, 0, occupy=False)
    w, H = 24, 1100
    for b in (box((bx0, by0, 0), (bx1, by0 + w, H), WCLIP), box((bx0, by1 - w, 0), (bx1, by1, H), WCLIP),
              box((bx1 - w, by0 + w, 0), (bx1, by1 - w, H), WCLIP),
              box((bx0, by0 + w, 0), (bx0 + w, -1770, H), WCLIP), box((bx0, -1530, 0), (bx0 + w, by1 - w, H), WCLIP),
              box((bx0, -1770, 920), (bx0 + w, -1530, H), WCLIP), box((bx0 + w, by0 + w, H - 24), (bx1 - w, by1 - w, H), WCLIP)):
        K.add(b)
    K.reserve(((bx0, by0, 0), (bx1, by1, H)))
    K.secret((bx1 - 200, -1730, 0), (bx1 - w - 4, -1570, 120), dest=(0, -200, L.SECRET_Z), angle=90, name='photobooth',
             approach='w')
    K.keep_clear(bx0 - 120, -1770, bx0, -1530, 0)
    K.jumppad(bx0 - 260, by1 + 140, 0, land=((bx0 + bx1) / 2 + 60, (by0 + by1) / 2, H), apex=H + 320, name='pad_booth',
              edges=[(bx0, (by0 + by1) / 2, H)])
    # racing cabinet: walk onto the plinth and sit in the seat; change machine; a cabinet by the booth
    rx, ry = L.RACER
    place('racer', rx, ry, 0, 0, boxes=[((-296, -556, 0), (296, 556, 120)), ((-296, 264, 120), (296, 556, 1100)),
                                        ((-196, 64, 120), (196, 236, 420)), ((-156, -376, 120), (156, -316, 460))])
    place('change_machine', -300, -1860, 0, 0, boxes=[((-156, -136, 0), (156, 136, 900))])
    place('cab_padpong', 1150, -1800, 0, 0, boxes=[((-L.CAB_W / 2 + 4, -L.CAB_D / 2 + 4, 0), (L.CAB_W / 2 - 4, L.CAB_D / 2 - 4, L.CAB_H))])


def secret_hall():
    z = L.SECRET_Z
    x0, y0, x1, y1 = -512, -384, 512, 384
    t = {'side': T('wall'), 'top': T('carpet'), 'bot': T('ceiling')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 512), (x1 + 32, y1 + 32, z + 544), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 512), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 512), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 512), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 512), t, detail=False))
    K.add(sign_box((-360, y1 - 4, z + 330), (360, y1, z + 470), T('neon_scores'), 1024, 256, back=CAULK, facing='s', edge=T('cab_black')))
    K.add(sign_box((-260, y1 - 8, z + 100), (260, y1 - 4, z + 300), T('scoreboard'), 512, 256, back=CAULK, facing='s', edge=T('cab_black')))
    for (x, y, nm, sc) in ((-380, 220, 'ente/padstatue_gold.md3', 1.0), (380, 220, 'ente/padstatue_gold.md3', 1.0),
                           (-380, -220, 'pad_statues/statue_super.md3', 0.8), (380, -220, 'pad_statues/statue_super.md3', 0.8)):
        K.catalog(nm, x, y, z, scale=sc, angle=270, lit=True, search=60)
    K.item('item_padpower', -150, 60, z); K.item('item_revival', 150, 60, z); K.item('holdable_killerducks', 0, 160, z)
    K.item('item_armor_padshield', 0, -40, z); K.ammo('imperius', -200, -120, z)
    K.teleporter((-48, y0, z), (48, y0 + 48, z + 96), dest=(1100, -1150, 0), angle=180, name='hall_exit')
    K.light(0, 0, z + 420, 500, '1 0.9 0.5'); K.light(0, 200, z + 150, 200, '1 0.85 0.4')
    K.trigger_sound((-150, -200, z), (150, -100, z + 64), 'human/applause', 'hall_cheer', wait=10)


# ================================================================================================= loot + spawns
def items():
    K.weapon('imperius', 280, 330, L.BASE_H + 64, marker='purple')
    K.weapon('splasher', 200, -250, L.ROOF_TOP, marker='blue')
    K.weapon('balloony', 2150, -380, L.BOARD_TOP, marker='orange')
    K.weapon('pumper', -1500, 250, L.TABLE_Z, marker='green')
    ym = (L.SHELF[1] + L.SHELF[3]) / 2
    K.weapon('betty', -1830, ym, L.SHELF2_Z, marker='black')
    K.weapon('bubbleg', 0, 1720, L.STAGE_Z, marker='green')
    K.weapon('boaster', 1500, 1600, L.DANCE_Z, marker='orange')
    ammo = {'imperius': [(-200, 300, L.BASE_H + 32), (2150, 0, L.BOARD_TOP), (-1380, 1150, L.CAB_H)],
            'splasher': [(-300, 300, L.ROOF_TOP), (900, -700, 0), (-800, -900, 0)],
            'balloony': [(2150, 200, L.BOARD_TOP), (800, 1500, 0), (-900, 1600, 0)],
            'pumper': [(-1900, -250, L.TABLE_Z), (-1700, 700, 0), (-600, -1500, 0)],
            'betty': [(-1200, ym, L.SHELF1_Z), (1380, 1150, L.CAB_H), (-2100, -1000, 0)],
            'bubbleg': [(500, 1720, L.STAGE_Z), (800, -250, 0), (-1000, 500, 0)],
            'boaster': [(1800, 1600, L.DANCE_Z), (300, -900, 0), (1000, 1300, 0), (-2100, 1700, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((-2100, 300, 0), (2100, 600, 0), (0, -1700, 0)): K.ammo('nipper', x, y, z)
    K.item('item_armor_shard', 2150, -800, L.BOARD_TOP); K.item('item_armor_shard', -1700, ym, L.SHELF1_Z)
    K.item('item_armor_padshield', 400, 420, L.BASE_H + 16)
    K.item('item_speedy', 900, 300, 0); K.item('holdable_floater', -1500, -250, L.TABLE_Z); K.item('item_jumper', 1850, -1650, 1100)
    K.station(-2150, -600, 0, 0); K.station(2150, 1200, 0, 180)


def spawns():
    for (x, y, a) in ((-900, -300, 0), (900, -300, 180), (-900, 700, 0), (850, 700, 180), (0, -1000, 90), (0, 1200, 270),
                      (-2100, -1200, 45), (-2100, 1700, 315), (2000, 1100, 225), (1300, -1300, 135), (-500, -1300, 90),
                      (2100, -1100, 90), (-1500, -800, 90), (1500, 600, 270), (-300, 1500, 270), (700, -1000, 90)):
        K.spawn(x, y, 0, a)
    K.ent('info_player_intermission', (2000, -1800, 1500), angles='25 135 0')


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    AM.make_textures()
    TX.kit_defaults(pad_rgb=(255, 70, 190))
    AM.make_all()
    hall(); claw_king(); skee(); air_hockey(); prize_wall(); north(); south(); secret_hall()
    items(); spawns()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
