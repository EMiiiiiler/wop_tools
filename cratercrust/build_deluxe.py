#!/usr/bin/env python3
"""Crater Crust Deluxe (wop_cratercrust_deluxe).

Takes the v2 Crater Crust layout (same footprint, same 1:4 heights), makes a few surgical edits, then adds:
  lot     hovering saucer X-7 with a tractor-beam lift through its hub, rotating radar dish, raven on the van,
          OPEN LATE pylon sign, BEAM ME UP sign
  arcade  rocket carousel (func_rotating), tube slide from the lander roof into the ball pit, bobbing claw,
          photo booth = secret teleporter to the saucer, GAME ZONE / PRIZES signs, lander console
  dining  stage with curtains, mascot, spotlights and an applause trigger, aquarium, rotating planet mobile, DINER sign
  kitchen conveyor pass under heat lamps, hanging pot rack, STAFF ONLY sign
  store   walk-in freezer (ice walls, snow footsteps) holding the red CTL lolly
  roof    greenhouse (enterable + climbable), giant rotating logo sign
  all     ambient sounds, doorbell, drifting cloud layer
"""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, os, re
sys.path.insert(0, _os.path.dirname(_HERE)); sys.path.insert(0, _HERE)
import wopmap as WM
import numpy as np, math

_src = open(_os.path.join(_HERE, 'build_map.py')).read()
EDITS = [
    ("T = lambda n: 'cratercrust/' + n", "T = lambda n: 'ccdeluxe/' + n"),
    # storeroom ground / walls split for the freezer
    ("S(-1824, 80, -288, -1168, 1056, 0, CAULK, faces={'top': T('cc_concrete')}, tag='g_store')",
     "S(-1824, 80, -288, -1168, 768, 0, CAULK, faces={'top': T('cc_concrete')}, tag='g_store')\n"
     "S(-1488, 768, -288, -1168, 1056, 0, CAULK, faces={'top': T('cc_concrete')}, tag='g_store_b')\n"
     "S(-1824, 768, -288, -1488, 1056, 0, CAULK, faces={'top': T('ccd_frost_floor')}, tag='g_freezer')"),
    ("S(-1824, 80, 0, -1792, 1056, CEIL, CAULK, faces={'e': SW}, tag='wall_w_store')",
     "S(-1824, 80, 0, -1792, 768, CEIL, CAULK, faces={'e': SW}, tag='wall_w_store')\n"
     "S(-1824, 768, 0, -1792, 1056, CEIL, CAULK, faces={'e': T('ccd_ice_wall')}, tag='wall_w_freezer')"),
    ("S(-1792, 1024, 0, -1184, 1056, CEIL, CAULK, faces={'s': SW}, tag='wall_n_store')",
     "S(-1792, 1024, 0, -1488, 1056, CEIL, CAULK, faces={'s': T('ccd_ice_wall')}, tag='wall_n_freezer')\n"
     "S(-1488, 1024, 0, -1184, 1056, CEIL, CAULK, faces={'s': SW}, tag='wall_n_store')"),
    # desk + stool + pizza boxes move out of the freezer corner
    ("D(-1760, 864, 0, -1568, 992, 72, WOOD, tag='desk')", "D(-1376, 880, 0, -1216, 1008, 72, WOOD, tag='desk')"),
    ("D(-1696, 784, 0, -1632, 832, 32, VINYL, tag='desk_stool')", "D(-1312, 832, 0, -1248, 880, 32, VINYL, tag='desk_stool')"),
    ("(-1248, 960, 80), (-1776, 448, 64), (-1296, 960, 32)", "(-1776, 512, 48), (-1776, 448, 64), (-1776, 576, 32)"),
    ("model('pad_pc/pad_tft.md3', -1700, 940, 72, 0.23, angle=270)", "model('pad_pc/pad_tft.md3', -1316, 956, 72, 0.23, angle=270)"),
    ("model('pad_lamps/gooseneck.md3', -1620, 920, 72, 0.35, angle=270)", "model('pad_lamps/gooseneck.md3', -1236, 936, 72, 0.35, angle=270)"),
    # kitchen pass becomes a conveyor
    ("D(-1312, -448, 0, -1184, -64, 112, STEEL, faces=CTOP, tag='kpass')",
     "D(-1312, -448, 0, -1184, -64, 112, STEEL, faces={'top': T('ccd_belt')}, tag='kpass')"),
    # north booth by the arcade makes way for the stage
    ("for x0 in (-1120, -608):\n    booth_tables.append(booth(x0, -1)); booth_tables.append(booth(x0, 1))",
     "for x0 in (-1120, -608):\n    booth_tables.append(booth(x0, -1))\nbooth_tables.append(booth(-1120, 1))"),
    # claw becomes a func_bobbing (added below)
    ("D(CLX + 92, CLY + 92, 216, CLX + 100, CLY + 100, 288, STEEL, tag='claw_rod')\n", ""),
    ("D(CLX + 80, CLY + 80, 200, CLX + 112, CLY + 112, 216, STEEL, tag='claw_head')\n", ""),
    # air hockey makes way for the carousel
    ("D(672, -192, 0, 928, -64, 80, T('cc_claw_base'), faces={'top': T('cc_neon_cyan')}, tag='airhockey')\n", ""),
    ("light(800, -128, 160, 120, (0.5, 0.9, 1.0))\n", ""),
    ("model('pad_ball/pad_soccerball.md3', 740, -128, 80, 0.2)\n", ""),
    # slide path / photo booth spots
    ("model('pad_ddmix/cabin/telescope.md3', 520, 400, 0, 0.4, angle=90, clip=True)\n", ""),
    ("model('pad_ddmix/padshop/cardboard_standup.md3', 1180, -660, 0, 0.65, angle=90, clip=True)",
     "model('pad_ddmix/padshop/cardboard_standup.md3', 1170, -690, 0, 0.65, angle=90, clip=True)"),
    ("pad(1136, -800, 0, 960, -976, 256, 430, 'southrow')", "pad(1136, -820, 0, 960, -976, 256, 430, 'southrow')"),
    ("model('pad_ddmix/padshop/cardboard_standup.md3', 1120, 960, 0, 0.65, angle=180, clip=True)\n", ""),
    # autumn tree canopy no longer pokes through the south fence
    ("    model('pad_ddmix/trashcan/%s.md3' % m, cx, cy, 32, 1.0, clip='trunk')",
     "    model('pad_ddmix/trashcan/%s.md3' % m, cx, cy, 32, 1.0, angle=(180 if cy < 0 else 0), clip='trunk')"),
    # pickups that move
    ("item('item_padpower', -1560, -150, 384, 'oven top (hard)', wait='120')",
     "item('item_padpower', 1860, -60, 496, 'saucer deck', wait='120')"),
    ("item('item_visionless', -1740, 560, 0, 'storeroom corner')", "item('item_visionless', -1640, 560, 0, 'storeroom')"),
    ("item('holdable_floater', -500, 400, ROOF, 'roof')", "item('holdable_floater', -400, 400, ROOF, 'greenhouse')"),
    ("item('holdable_killerducks', -1480, 920, 0, 'storeroom')", "item('holdable_killerducks', -1680, 850, 0, 'freezer')"),
    ("(-576, 400, 0, 'dining N')", "(-384, 940, 32, 'on the stage')"),
    ("(-1240, 820, 0, 'storeroom')", "(-1240, 780, 0, 'storeroom')"),
    ("(2000, 0, 0, 'lot')", "(1880, -240, 0, 'lot')"),
    ("(880, -40, 0, 180)", "(900, 40, 0, 180)"),
    ("(-1640, 480), (-1740, 760)):", "(-1640, 480), (-1700, 590)):"),
    ("Entity('team_CTL_redlolly', origin=(-1440, 960, 24))", "Entity('team_CTL_redlolly', origin=(-1600, 960, 24))"),
]
for a, b in EDITS:
    assert _src.count(a) == 1, ('edit not found / ambiguous', a[:70])
    _src = _src.replace(a, b)
_src = _src[:_src.rindex('json.dump(')]
exec(_src)


# ====================================================================== deluxe helpers
def H(wb, tag='', kind='solid'):
    return W(from_wop(wb, kind=kind, tag=tag))


def sign(mn, mx, tex, facing, tw=512, th=128, tag='sign'):
    return H(WM.sign_box(mn, mx, T(tex), tw, th, back=T('cc_sign_back'), facing=facing), tag)


def mover(cls, wbs, origin_box=None, **kv):
    e = Entity(cls, **kv)
    for wb in wbs:
        e.brushes.append(from_wop(wb, kind='mover', detail=False, tag=cls))
    if origin_box:
        e.brushes.append(box(*origin_box, 'common/origin', kind='mover', detail=False, tag='origin'))
    ents.append(e)
    return e


def speaker(x, y, z, noise, loop=True, **kv):
    k = {'noise': noise}
    if loop: k['spawnflags'] = '1'
    k.update(kv)
    ents.append(Entity('target_speaker', origin=(x, y, z), **k))


def trigger(cls, mn, mx, **kv):
    e = Entity(cls, **kv)
    e.brushes.append(box(*mn, *mx, TRIG, kind='trigger', detail=False, tag=cls))
    ents.append(e)
    return e


def ext_model(path, x, y, z, angle, start, end, fps):
    models.append(dict(path='models/mapobjects/' + path, origin=(x, y, z), scale=1.0, angle=angle, clip=False, tag='',
                       external={'animationStart': start, 'animationEnd': end, 'animationFPS': fps}))


def cone(cx, cy, r, z0, z1, tex, n=8):
    return WM.hull([(x, y, z0) for x, y in WM.ngon(cx, cy, r, n)] + [(cx, cy, z1)], tex)


# ====================================================================== KITCHEN deluxe
D(-1296, -432, 232, -1200, -80, 248, STEEL, faces={'bottom': T('ccd_heatlamp')}, tag='heatlamps')
D(-1252, -260, 248, -1244, -252, CEIL, STEEL, tag='heatlamp_rod')
D(-1456, -8, 352, -1296, 8, 360, STEEL, tag='potrack')
for rx in (-1452, -1308):
    D(rx, -4, 360, rx + 8, 4, CEIL, STEEL, tag='potrack_rod%d' % rx)
for px in (-1424, -1376, -1328):
    H(WM.cyl(px, 0, 22, 300, 306, {'top': T('cc_steel'), 'bot': T('cc_rubber'), 'side': T('cc_rubber')}, 10), 'pan%d' % px)
    D(px - 2, -2, 306, px + 2, 2, 352, STEEL, tag='pan_hook%d' % px)
sign((-1152, -784, 336), (-1144, -624, 376), 'ccd_sign_staff', 'e', tag='sign_staff')
light(-1248, -256, 200, 260, (1.0, 0.6, 0.25))
speaker(-1640, -320, 60, 'sound/world/ambient/fire_crackling.ogg')
speaker(-1300, -900, 150, 'sound/world/ambient/fire_sizzling.ogg')

# ====================================================================== FREEZER (storeroom NW corner)
ICE, SWT = T('ccd_ice_wall'), T('cc_store_wall')
D(-1792, 768, 0, -1488, 784, 256, ICE, faces={'s': SWT, 'top': SWT}, tag='frz_s')
D(-1504, 784, 0, -1488, 848, 256, ICE, faces={'e': SWT, 'top': SWT}, tag='frz_e1')
D(-1504, 976, 0, -1488, 1024, 256, ICE, faces={'e': SWT, 'top': SWT}, tag='frz_e2')
D(-1504, 848, 224, -1488, 976, 256, ICE, faces={'e': SWT, 'top': SWT}, tag='frz_lintel')
D(-1792, 784, 256, -1488, 1024, 272, ICE, faces={'top': T('cc_roof')}, tag='frz_roof')
D(-1792, 800, 0, -1728, 896, 64, T('ccd_iceblock'), tag='ice1')
D(-1792, 896, 0, -1728, 960, 128, T('ccd_iceblock'), tag='ice2')
D(-1792, 960, 0, -1712, 1024, 64, T('ccd_iceblock'), tag='ice3')
D(-1568, 984, 0, -1520, 1024, 96, PIZZABOX, scale=0.25, tag='frz_dough')
sign((-1728, 764, 150), (-1568, 768, 190), 'ccd_sign_freezer', 's', tag='sign_freezer')
light(-1640, 900, 200, 500, (0.6, 0.8, 1.0))
speaker(-1640, 900, 120, 'sound/world/machine/freezer.ogg')
item('item_armor_shard', -1640, 900, 272, 'freezer roof')

# ====================================================================== DINING deluxe
# stage (replaces the north booth next to the arcade)
D(-592, 832, 0, -176, 1024, 32, T('cc_counter_front'), faces={'top': WOOD}, tag='stage')
D(-560, 800, 0, -208, 832, 16, T('cc_counter_front'), faces={'top': WOOD}, tag='stage_step')
CUR = T('ccd_curtain')
D(-608, 832, 0, -592, 1024, 352, CUR, tag='stage_tower_w')
D(-176, 832, 0, -160, 1024, 352, CUR, tag='stage_tower_e')
D(-592, 1016, 32, -176, 1024, 352, CUR, tag='stage_backdrop')
sign((-608, 992, 352), (-160, 1024, 448), 'ccd_sign_live', 's', tag='sign_live')
H(WM.cyl(-440, 880, 3, 32, 128, T('cc_steel'), 6), 'mic_stand')
H(WM.cyl(-440, 880, 6, 128, 142, T('cc_rubber'), 8), 'mic')
model('pad_ddmix/padshop/cardboard_standup.md3', -300, 950, 32, 0.65, angle=270, clip=True)
trigger('trigger_multiple', (-560, 840, 32), (-208, 872, 96), target='applause', wait='20')
speaker(-384, 900, 220, 'sound/world/human/applause.ogg', loop=False, targetname='applause')
for (lx, tx, col) in ((-520, -440, (1.0, 0.3, 0.8)), (-240, -320, (0.3, 0.9, 1.0))):
    nm = 'spot%d' % abs(lx)
    lights.append(dict(origin=(lx, 560, 560), light=700, color=col, target=nm, radius=72))
    ents.append(Entity('info_null', targetname=nm, origin=(tx, 930, 34)))
# aquarium on the partition (dining side)
D(-1152, -32, 0, -1104, 192, 56, WOOD, tag='aqua_base')
D(-1152, -32, 56, -1112, 192, 232, STEEL, faces={'e': T('ccd_aquarium')}, scales={'e': (0.875, 1.375)}, tag='aqua_tank')
D(-1112, -32, 56, -1104, 192, 232, T('cc_glass'), tag='aqua_glass')
D(-1152, -32, 232, -1104, 192, 248, STEEL, tag='aqua_lid')
speaker(-1090, 80, 120, 'sound/world/machine/fishtank.ogg')
speaker(-1104, -380, 150, 'sound/world/machine/coffee_maker.ogg')
# planet mobile over the tables (func_rotating)
MCX, MCY, MZ = -352, 380, 640
D(MCX - 4, MCY - 4, 664, MCX + 4, MCY + 4, CEIL, STEEL, tag='mobile_rod')
mob = [WM.cyl(MCX, MCY, 24, 616, 664, T('ccd_sun'), 10)]
for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    if dx:
        x1, x2 = sorted((MCX + dx * 24, MCX + dx * 128))
        mob.append(WM.box((x1, MCY - 4, 636), (x2, MCY + 4, 644), T('cc_steel')))
    else:
        y1, y2 = sorted((MCY + dy * 24, MCY + dy * 128))
        mob.append(WM.box((MCX - 4, y1, 636), (MCX + 4, y2, 644), T('cc_steel')))
    mob.append(WM.cyl(MCX + dx * 152, MCY + dy * 152, 24, 616, 664, T('ccd_planet'), 10))
mover('func_rotating', mob, (MCX - 8, MCY - 8, MZ - 8, MCX + 8, MCY + 8, MZ + 8), speed='12', dmg='1')
sign((-1120, 1016, 320), (-672, 1024, 432), 'ccd_sign_diner', 's', tag='sign_diner')
# rocket floor lamps in the dining aisle (break the long south/north aisle sightlines)
for ly in (-690, 690):
    H(WM.cyl(-576, ly, 20, 0, 160, T('ccd_rocket'), 8), 'rocketlamp%d' % ly)
    H(cone(-576, ly, 20, 160, 208, T('cc_neon_magenta'), 8), 'rocketlamp_tip%d' % ly)
    light(-576, ly, 240, 160, (1.0, 0.4, 0.8))

# ====================================================================== ARCADE deluxe
# lander cockpit console (also breaks the long E-W aisle sightline)
D(160, -64, 0, 224, 64, 96, T('cc_cab_side'), faces={'top': T('cc_panel'), 'w': T('cc_screen2')}, tag='lander_console')
# rocket carousel
CX, CY = 800, -150
car = [WM.cyl(CX, CY, 128, 0, 16, {'top': T('ccd_carousel'), 'side': T('cc_claw_base'), 'bot': CAULK}, 12),
       WM.cyl(CX, CY, 10, 16, 208, T('cc_steel'), 8),
       WM.cyl(CX, CY, 112, 208, 224, {'top': T('ccd_carousel'), 'bot': T('ccd_carousel'), 'side': T('cc_neon_cyan')}, 12)]
for k in range(3):
    a = math.radians(90 + 120 * k)
    rx, ry = CX + 82 * math.cos(a), CY + 82 * math.sin(a)
    car.append(WM.cyl(rx, ry, 20, 16, 84, T('ccd_rocket'), 8))
    car.append(cone(rx, ry, 20, 84, 124, T('cc_neon_magenta'), 8))
mover('func_rotating', car, (CX - 8, CY - 8, 100, CX + 8, CY + 8, 116), speed='24', dmg='1',
      noise='sound/world/machine/mechanics.ogg')
light(CX, CY, 300, 300, (1.0, 0.5, 0.9))
# bobbing claw in the claw machine
mover('func_bobbing', [WM.box((CLX + 92, CLY + 92, 216), (CLX + 100, CLY + 100, 280), T('cc_steel')),
                       WM.box((CLX + 80, CLY + 80, 200), (CLX + 112, CLY + 112, 216), T('cc_steel'))],
      height='8', speed='3', noise='sound/world/machine/harddisk.ogg')


# tube slide: lander roof -> ball pit
def slide(pts, width, wall_h=24, wall_t=8, floor_t=16):
    P_ = [np.array(p, float) for p in pts]
    n = len(P_)
    dirs = []
    for i in range(n - 1):
        d = P_[i + 1][:2] - P_[i][:2]; dirs.append(d / np.linalg.norm(d))
    perps = [np.array([-d[1], d[0]]) for d in dirs]
    jl = []
    for k in range(n):
        if k == 0: m = perps[0]
        elif k == n - 1: m = perps[-1]
        else:
            m = perps[k - 1] + perps[k]; m = m / np.linalg.norm(m)
        jl.append((m, 1.0 / max(0.5, float(m @ perps[min(k, n - 2)]))))
    hw = width / 2
    for i in range(n - 1):
        (ma, fa), (mb, fb) = jl[i], jl[i + 1]
        ca, cb = P_[i], P_[i + 1]
        za, zb = ca[2], cb[2]
        e = lambda c, m, f, off: c[:2] + m * off * f
        La, Ra, Lb, Rb = e(ca, ma, fa, hw), e(ca, ma, fa, -hw), e(cb, mb, fb, hw), e(cb, mb, fb, -hw)
        quad = [(La, za), (Ra, za), (Rb, zb), (Lb, zb)]
        pts3 = [(p[0], p[1], z) for p, z in quad] + [(p[0], p[1], z - floor_t) for p, z in quad]
        H(WM.hull(pts3, {'top': T('ccd_slide'), 'side': T('ccd_slide_wall'), 'bot': T('ccd_slide_wall')}, round_pts=False), 'slide%d' % i)
        for s in (1, -1):
            ia, ib = e(ca, ma, fa, s * hw), e(cb, mb, fb, s * hw)
            oa, ob = e(ca, ma, fa, s * (hw + wall_t)), e(cb, mb, fb, s * (hw + wall_t))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - floor_t), (p[0], p[1], zz + wall_h)]
            H(WM.hull(pw, T('ccd_slide_wall'), round_pts=False), 'slidewall%d_%d' % (i, s))


SLIDE = [(370, 224, LH + 32), (370, 330, 300), (420, 420, 265), (500, 470, 225), (600, 485, 180), (700, 475, 135), (790, 455, 100)]
slide(SLIDE, 72)
H(WM.cyl(500, 470, 10, 0, 203, T('cc_steel'), 8), 'slide_pillar')
speaker(760, 450, 40, 'sound/world/misc/toy_squeeze.ogg', loop=False, targetname='squeak')
trigger('trigger_multiple', (740, 400, -40), (840, 500, 0), target='squeak', wait='3')

# photo booth: secret teleporter to the saucer
BOOTH, BIN = T('cc_claw_base'), T('ccd_curtain')
D(1072, 864, 0, 1200, 880, 256, BOOTH, faces={'n': BIN}, tag='booth_s')
D(1072, 1000, 0, 1200, 1016, 256, BOOTH, faces={'s': BIN}, tag='booth_n')
D(1184, 880, 0, 1200, 1000, 256, BOOTH, faces={'w': BIN}, tag='booth_e')
D(1072, 880, 0, 1088, 912, 256, BOOTH, faces={'e': BIN}, tag='booth_w1')
D(1072, 968, 0, 1088, 1000, 256, BOOTH, faces={'e': BIN}, tag='booth_w2')
D(1072, 912, 160, 1088, 968, 256, BOOTH, faces={'bottom': BIN}, tag='booth_lintel')
D(1072, 864, 256, 1200, 1016, 272, BOOTH, faces={'top': T('cc_cab_top'), 'bottom': BIN}, tag='booth_roof')
D(1152, 896, 0, 1184, 984, 40, VINYL, tag='booth_bench')
D(1078, 912, 0, 1082, 968, 160, T('curtain_ns'), kind='decor', tag='booth_beads')
sign((1064, 902, 176), (1072, 978, 212), 'ccd_sign_photo', 'w', tw=256, th=128, tag='sign_photo')
trigger('trigger_multiple', (1088, 912, 0), (1102, 968, 96), target='secret', wait='5')
speaker(1100, 940, 120, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret')
trigger('trigger_teleport', (1104, 880, 0), (1150, 1000, 96), target='ufo_dest')
speaker(1140, 940, 150, 'sound/world/machine/portal_idle.ogg')
light(1136, 940, 200, 220, (1.0, 0.5, 0.9))
# signs
sign((224, -1024, 320), (864, -1016, 480), 'ccd_sign_gamezone', 'n', tag='sign_gamezone')
sign((64, 1016, 480), (576, 1024, 608), 'ccd_sign_prizes', 's', tag='sign_prizes')
speaker(600, 736, 680, 'sound/world/machine/ventilation.ogg')
speaker(544, -960, 140, 'sound/world/machine/fan_pc.ogg')

# front door chime
trigger('trigger_multiple', (1216, -176, 0), (1248, 176, 96), target='doorbell', wait='3')
speaker(1200, 0, 300, 'sound/world/machine/dingdong.ogg', loop=False, targetname='doorbell')

# ====================================================================== LOT deluxe
UX, UY = 2000, -60
R_IN, R_MID, R_OUT, ZB_, ZR, ZD = 64, 160, 224, 448, 480, 496
for k in range(12):
    a0, a1 = math.radians(30 * k), math.radians(30 * (k + 1))
    am = (a0 + a1) / 2; rad = (math.cos(am), math.sin(am))
    pts = []
    for a in (a0, a1):
        c, s = math.cos(a), math.sin(a)
        for (r, z) in ((R_IN, ZB_), (R_IN, ZD), (R_MID, ZB_), (R_OUT, ZR), (R_OUT, ZD)):
            pts.append((UX + r * c, UY + r * s, z))

    def tex(n, rad=rad):
        if n[2] > 0.7: return T('ccd_saucer_deck')
        if n[2] < -0.2: return T('ccd_saucer_under')
        d = n[0] * rad[0] + n[1] * rad[1]
        if d > 0.5: return T('ccd_saucer_rim')
        if d < -0.5: return T('ccd_saucer')
        return CAULK
    H(WM.hull(pts, tex, round_pts=False), 'saucer%d' % k)
# beam emitter pad + nonsolid beam + lift
H(WM.cyl(UX, UY, 48, 0, 8, {'top': T('ccd_beam_pad'), 'side': T('cc_pad_side'), 'bot': CAULK}, 12), 'beam_pad')
H(WM.hull([(x, y, 8) for x, y in WM.ngon(UX, UY, 40, 12)] + [(x, y, ZB_) for x, y in WM.ngon(UX, UY, 58, 12)], T('beam_ns')),
  'beam', kind='decor')
_bt = box(UX - 28, UY - 28, 8, UX + 28, UY + 28, 72, TRIG, kind='trigger', detail=False, tag='trig_beam')
_be = Entity('trigger_push', target='tp_beam'); _be.brushes.append(_bt); ents.append(_be)
_land, _apex = (UX + 150, UY, ZD), 780
_tu = math.sqrt(2 * (_apex - (8 + 24)) / 800.0); _td = math.sqrt(2 * (_apex + 8 - (ZD + 24)) / 800.0)
_f = _tu / (_tu + _td)
_tgt = (round(UX + (_land[0] - UX) * _f), round(UY + (_land[1] - UY) * _f), _apex)
ents.append(Entity('target_position', targetname='tp_beam', origin=_tgt))
pads.append(dict(name='beam', trig=_bt, target=_tgt, land=_land))
# radar dish on a mast at the rim
DX_, DY_ = UX, UY - 190
H(WM.cyl(DX_, DY_, 8, ZD, 592, T('cc_steel'), 8), 'dish_mast')
mover('func_rotating', [WM.box((DX_ - 48, DY_ - 4, 592), (DX_ + 48, DY_ + 4, 600), T('cc_steel')),
                        WM.box((DX_ + 40, DY_ - 22, 600), (DX_ + 48, DY_ + 22, 640), T('ccd_saucer')),
                        WM.box((DX_ - 48, DY_ - 8, 600), (DX_ - 40, DY_ + 8, 616), T('ccd_saucer_rim'))],
      (DX_ - 8, DY_ - 8, 604, DX_ + 8, DY_ + 8, 620), speed='45', dmg='1')
ents.append(Entity('misc_teleporter_dest', targetname='ufo_dest', origin=(UX, UY + 170, ZD + 24), angle='270'))
light(UX, UY, 420, 700, (0.5, 1.0, 0.6))
light(UX, UY, 600, 250, (0.6, 1.0, 0.7))
speaker(UX, UY, 560, 'sound/world/misc/strange_signal.ogg')
sign((2076, -203, 96), (2204, -197, 128), 'ccd_sign_beam', 'ns', tag='sign_beam')
H(WM.cyl(2140, -200, 3, 0, 96, T('cc_steel'), 6), 'beam_post')
# raven on the van roof
ext_model('animated/raven_sitting_2_small.md3', 2000, -500, 304, 90, 0, 210, 15)
# OPEN LATE pylon on the sidewalk
H(WM.cyl(1344, -700, 10, 16, 352, T('cc_steel'), 8), 'pylon')
sign((1338, -828, 352), (1350, -572, 416), 'ccd_sign_open', 'ew', tag='sign_open')
speaker(2400, 768, 80, 'sound/world/animal/cricket_chirp1.ogg')
speaker(1792, -848, 80, 'sound/world/animal/cricket_chirp2.ogg')
speaker(2600, 0, 200, 'sound/world/ambient/city_traffic.ogg')
speaker(1300, 0, 600, 'sound/world/machine/electric_sizzle.ogg')
speaker(2560, 980, 60, 'sound/world/animal/dog_bark2.ogg', loop=False, targetname='dog')
ents.append(Entity('func_timer', origin=(2560, 980, 120), target='dog', wait='30', random='12', spawnflags='1'))

# ====================================================================== ROOF deluxe
# giant rotating logo sign
H(WM.cyl(1100, 640, 16, ROOF, 1040, T('cc_steel'), 8), 'logo_pylon')
_ls = WM.sign_box((972, 634, 1040), (1228, 646, 1296), T('ccd_logo_sign'), 512, 512, back=T('cc_sign_back'), facing='ns')
mover('func_rotating', [_ls], (1092, 632, 1160, 1108, 648, 1176), speed='30', dmg='1')
light(1100, 560, 1100, 400, (1.0, 0.7, 1.0)); light(1100, 720, 1100, 400, (1.0, 0.7, 1.0))
# greenhouse
GW = T('cc_glass')
for (x1, y1) in ((-560, 160), (-248, 160), (-560, 472), (-248, 472)):
    D(x1, y1, ROOF, x1 + 8, y1 + 8, 1024, STEEL, tag='gh_post%d_%d' % (x1, y1))
D(-560, 168, ROOF, -552, 472, 1024, GW, tag='gh_w')
D(-248, 168, ROOF, -240, 472, 1024, GW, tag='gh_e')
D(-552, 472, ROOF, -248, 480, 1024, GW, tag='gh_n')
D(-552, 160, ROOF, -440, 168, 1024, GW, tag='gh_s1')
D(-360, 160, ROOF, -248, 168, 1024, GW, tag='gh_s2')
D(-440, 160, 928, -360, 168, 1024, GW, tag='gh_lintel')
D(-560, 160, 1024, -240, 480, 1032, GW, tag='gh_roof')
SOIL = {'top': T('ccd_soil')}
D(-552, 168, ROOF, -488, 472, ROOF + 32, WOOD, faces=SOIL, tag='gh_bed_w')
D(-312, 168, ROOF, -248, 472, ROOF + 32, WOOD, faces=SOIL, tag='gh_bed_e')
for k, y in enumerate((200, 260, 320, 380, 440)):
    model('pad_sunflower/pad_sunflower%s.md3' % ('' if k % 2 == 0 else '2'), -520, y, ROOF + 32, 0.6, angle=90 * (k % 2))
model('pad_ddmix/plants/flower_pink.md3', -280, 200, ROOF + 32, 0.25)
model('pad_ddmix/plants/fern.md3', -280, 290, ROOF + 32, 0.1)
model('pad_tins/tomatoes_ts.md3', -280, 360, ROOF + 32, 0.35)
model('pad_ddmix/plants/flower_pink.md3', -280, 430, ROOF + 32, 0.25)
light(-400, 320, 980, 450, (1.0, 0.9, 0.7))
pad(-300, 600, ROOF, -400, 320, 1032, 1140, 'greenhouse')
item('item_armor_shard', -470, 400, 1032, 'greenhouse roof')
speaker(-804, 364, 920, 'sound/world/machine/aircon.ogg')
speaker(0, 0, 1100, 'sound/world/ambient/wind_night.ogg')

for (n, x, y, z) in (('Walk-in Freezer', -1640, 900, 64), ('Stage', -384, 920, 96), ('Saucer X-7', UX, UY, ZD + 64),
                     ('Greenhouse', -400, 320, ROOF + 64), ('Photo Booth', 1136, 940, 64), ('Carousel', CX, CY, 64)):
    ents.append(Entity('target_location', message=n, origin=(x, y, z)))

json.dump(dict(models=models, items=items, spawns=spawns), open(_os.path.join(_os.environ.get('OUT', 'out'), 'layout_deluxe.json'), 'w'), indent=1, default=str)
