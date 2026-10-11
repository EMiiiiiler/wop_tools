#!/usr/bin/env python3
"""Generates wop_cratercrust.map  (World of Padman, 1:4 human scale: 1 m = 128 u).

v2 condensed layout (top view, +x = east, +y = north):
  x -2560..-1792  kitchen (south/west) + storeroom (north)      | red CTL base
  x -1760.. -256  dining floor (booths, tables, service counter)
  x  -256.. 1536  arcade hall (lander playhouse, cabinets, claw machine,
                   prize shelves, ball-pit crater, ceiling duct w/ iMPERiUS)
  x  1568.. 3584  parking lot (delivery van, statue, trees, dumpster)  | blue CTL base
  roof z 800 over the whole building, reached by jump pad from the lot or the arcade hatch.
"""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, math
sys.path.insert(0, _HERE)
from mapgen_lib import *

T = lambda n: 'cratercrust/' + n
CAULK, CLIP, TRIG, SKY, NODRAW = 'common/caulk', 'common/clip', 'common/trigger', T('cc_sky'), 'common/nodraw'
WEAPCLIP = 'common/weapclip'

world = []          # brushes for worldspawn
ents = []           # point / brush entities
models = []         # (path, origin, scale, angle, clip)
pads = []           # jump pads
notes = []

CEIL, ROOF = 768, 800


def W(b):
    world.append(b); return b


def S(*a, **k):      # structural
    k.setdefault('detail', False)
    return W(box(*a, **k))


def D(*a, **k):      # detail
    k.setdefault('detail', True)
    return W(box(*a, **k))


# ======================================================================== helpers
CRATE, PIZZABOX, WOOD, VINYL = T('cc_crate'), T('cc_pizzabox'), T('cc_wood'), T('cc_vinyl')
STEEL = T('cc_steel')


def stairs(x0, y0, x1, y1, z0, n, rise, axis, up_dir, tex=CRATE, tag='stairs'):
    """n steps of `rise` inside rectangle; axis 'x' or 'y' is the climbing axis; up_dir +1/-1."""
    if axis == 'x':
        run = (x1 - x0) / n
        for i in range(n):
            k = i if up_dir > 0 else n - 1 - i
            D(x0 + run*k, y0, z0, x0 + run*(k+1), y1, z0 + rise*(i+1), tex, scale=0.25, tag='%s%d' % (tag, i))
    else:
        run = (y1 - y0) / n
        for i in range(n):
            k = i if up_dir > 0 else n - 1 - i
            D(x0, y0 + run*k, z0, x1, y0 + run*(k+1), z0 + rise*(i+1), tex, scale=0.25, tag='%s%d' % (tag, i))


def shelf_unit(x0, y0, x1, y1, levels, top, tex=STEEL, panel=16, tag='shelf'):
    """Two side panels (x0..x0+panel, x1-panel..x1) and slabs between them. levels = list of slab tops."""
    D(x0, y0, 0, x0 + panel, y1, top, tex, tag=tag + '_pw')
    D(x1 - panel, y0, 0, x1, y1, top, tex, tag=tag + '_pe')
    for i, z in enumerate(levels):
        D(x0 + panel, y0, z - 8, x1 - panel, y1, z, tex, tag='%s_s%d' % (tag, i))


def wedge(x1, y1, z1, x2, y2, z2, high, tex, tag, kind='solid', top_tex=None):
    """Ramp filling the box; top surface rises from z1 to z2 toward side `high` (n/s/e/w)."""
    top_tex = top_tex or tex
    pts = []
    pts.append(((x1, y1, z1), (x2, y1, z1), (x2, y2, z1), tex))  # bottom
    if high == 'n':
        slope = ((x1, y1, z1), (x2, y1, z1), (x1, y2, z2), top_tex)
        sides = [((x1, 0, 0), (x1, 1, 0), (x1, 0, 1)), ((x2, 0, 0), (x2, 1, 0), (x2, 0, 1)), ((0, y2, 0), (1, y2, 0), (0, y2, 1))]
        inside = ((x1+x2)/2, y2 - (y2-y1)*0.25, z1 + (z2-z1)*0.25)
    elif high == 's':
        slope = ((x1, y2, z1), (x2, y2, z1), (x1, y1, z2), top_tex)
        sides = [((x1, 0, 0), (x1, 1, 0), (x1, 0, 1)), ((x2, 0, 0), (x2, 1, 0), (x2, 0, 1)), ((0, y1, 0), (1, y1, 0), (0, y1, 1))]
        inside = ((x1+x2)/2, y1 + (y2-y1)*0.25, z1 + (z2-z1)*0.25)
    elif high == 'e':
        slope = ((x1, y1, z1), (x1, y2, z1), (x2, y1, z2), top_tex)
        sides = [((0, y1, 0), (1, y1, 0), (0, y1, 1)), ((0, y2, 0), (1, y2, 0), (0, y2, 1)), ((x2, 0, 0), (x2, 1, 0), (x2, 0, 1))]
        inside = (x2 - (x2-x1)*0.25, (y1+y2)/2, z1 + (z2-z1)*0.25)
    else:  # 'w'
        slope = ((x2, y1, z1), (x2, y2, z1), (x1, y1, z2), top_tex)
        sides = [((0, y1, 0), (1, y1, 0), (0, y1, 1)), ((0, y2, 0), (1, y2, 0), (0, y2, 1)), ((x1, 0, 0), (x1, 1, 0), (x1, 0, 1))]
        inside = (x1 + (x2-x1)*0.25, (y1+y2)/2, z1 + (z2-z1)*0.25)
    pts.append(slope)
    for s in sides:
        pts.append((s[0], s[1], s[2], tex))
    return brush_from_points(pts, inside=inside, kind=kind, tag=tag)


def model(path, x, y, z, scale, angle=0, clip=False, tag=''):
    models.append(dict(path='models/mapobjects/' + path, origin=(x, y, z), scale=scale, angle=angle, clip=clip, tag=tag))


def pad(x, y, z, lx, ly, lz, apex, name, size=96):
    """Jump pad at (x,y) on surface z that lands the player on (lx,ly) at surface height lz.
    The trigger_push aims at an apex; players keep their horizontal speed after the apex,
    so the target_position is placed part-way along the line according to rise/fall times."""
    h = size // 2
    D(x - h, y - h, z, x + h, y + h, z + 8, T('cc_pad_side'), faces={'top': T('cc_jumppad')}, scale=0.375, tag='pad_' + name)
    e = Entity('trigger_push', target='tp_' + name)
    e.brushes.append(box(x - h + 8, y - h + 8, z + 8, x + h - 8, y + h - 8, z + 40, TRIG, kind='trigger', detail=False, tag='trig_' + name))
    ents.append(e)
    g = 800.0
    t_up = math.sqrt(2 * (apex - (z + 24)) / g)
    t_dn = math.sqrt(2 * (apex + 8 - (lz + 24)) / g)
    f = t_up / (t_up + t_dn)
    tx, ty = round(x + (lx - x) * f), round(y + (ly - y) * f)
    ents.append(Entity('target_position', targetname='tp_' + name, origin=(tx, ty, apex)))
    pads.append(dict(name=name, trig=e.brushes[0], target=(tx, ty, apex), land=(lx, ly, lz)))


items = []
def item(cls, x, y, z, note='', **kv):
    """z = surface height the item rests on; origin is placed 24u above."""
    items.append(dict(cls=cls, origin=(x, y, z + 24), note=note, kv=kv))


spawns = []
def spawn(cls, x, y, z, angle):
    spawns.append(dict(cls=cls, origin=(x, y, z + 24), angle=angle))


lights = []
def light(x, y, z, val, color=(1, 1, 1)):
    lights.append(dict(origin=(x, y, z), light=val, color=color))


# ======================================================================== CONDENSED LAYOUT (v2)
# Building x -1824..1248, y -1056..1056 (walls 32). Lot x 1248..2656.
#   kitchen  x -1792..-1184, y -1024..64      storeroom x -1792..-1184, y 96..1024
#   dining   x -1152..  -64                   arcade    x   -64..1216
#   lot      x  1248.. 2624

# ======================================================================== hull
for b in [
    box(-1856, -1088, -320, -1824, 1088, 1568, SKY, tag='sky_w'),
    box(2656, -1088, -320, 2688, 1088, 1568, SKY, tag='sky_e'),
    box(-1824, 1056, -320, 2656, 1088, 1568, SKY, tag='sky_n'),
    box(-1824, -1088, -320, 2656, -1056, 1568, SKY, tag='sky_s'),
    box(-1824, -1056, 1536, 2656, 1056, 1568, SKY, tag='sky_top'),
    box(-1824, -1056, -320, 2656, 1056, -288, CAULK, tag='hull_bottom'),
]:
    b.detail = False; W(b)

# ======================================================================== ground
FOAM = T('cc_foam')
PX1, PX2, PY1, PY2 = 640, 1088, 128, 768          # ball pit
S(-1824, -1056, -288, -1168, 80, 0, CAULK, faces={'top': T('cc_kitchen_floor')}, scale=1.0, tag='g_kitchen')
S(-1824, 80, -288, -1168, 1056, 0, CAULK, faces={'top': T('cc_concrete')}, tag='g_store')
S(-1168, -1056, -288, -64, 1056, 0, CAULK, faces={'top': T('cc_floor_tile')}, tag='g_dining')
S(-64, -1056, -288, PX1, 1056, 0, CAULK, faces={'top': T('cc_carpet'), 'e': FOAM}, tag='g_arcade_w')
S(PX2, -1056, -288, 1232, 1056, 0, CAULK, faces={'top': T('cc_carpet'), 'w': FOAM}, tag='g_arcade_e')
S(PX1, -1056, -288, PX2, PY1, 0, CAULK, faces={'top': T('cc_carpet'), 'n': FOAM}, tag='g_arcade_s')
S(PX1, PY2, -288, PX2, 1056, 0, CAULK, faces={'top': T('cc_carpet'), 's': FOAM}, tag='g_arcade_n')
S(PX1, PY1, -288, PX2, PY2, -192, CAULK, faces={'top': FOAM}, tag='g_pit_floor')
S(1232, -1056, -288, 2656, 1056, 0, CAULK, faces={'top': T('cc_asphalt')}, tag='g_lot')

# ======================================================================== building shell
MURAL, KTILE, FACADE, STEEL = T('cc_wall_mural'), T('cc_kitchen_tile'), T('cc_facade'), T('cc_steel')
SW = T('cc_store_wall')
S(-1824, -1056, 0, -1792, 80, CEIL, CAULK, faces={'e': KTILE}, scale=1.0, tag='wall_w')
S(-1824, 80, 0, -1792, 1056, CEIL, CAULK, faces={'e': SW}, tag='wall_w_store')
S(-1792, 1024, 0, -1184, 1056, CEIL, CAULK, faces={'s': SW}, tag='wall_n_store')
S(-1184, 1024, 0, 1216, 1056, CEIL, CAULK, faces={'s': MURAL}, scale=1.0, tag='wall_n_main')
S(-1792, -1056, 0, -1184, -1024, CEIL, CAULK, faces={'n': KTILE}, scale=1.0, tag='wall_s_kitchen')
S(-1184, -1056, 0, 1216, -1024, CEIL, CAULK, faces={'n': MURAL}, scale=1.0, tag='wall_s_main')
fac = {'w': MURAL, 'e': FACADE}
def east_wall(y1, y2, z1, z2, tag):
    S(1216, y1, z1, 1248, y2, z2, CAULK, faces=fac, scale=1.0 if z2 - z1 > 200 else 0.5, tag=tag)
east_wall(-1056, -896, 0, CEIL, 'fac1')
east_wall(-896, -448, 0, 96, 'fac_win1_lo'); east_wall(-896, -448, 320, CEIL, 'fac_win1_hi')
east_wall(-448, -192, 0, CEIL, 'fac2')
east_wall(-192, 192, 384, CEIL, 'fac_door_hi')
east_wall(192, 320, 0, CEIL, 'fac3')
east_wall(320, 640, 0, 96, 'fac_win2_lo'); east_wall(320, 640, 320, CEIL, 'fac_win2_hi')
east_wall(640, 704, 0, CEIL, 'fac4')
east_wall(704, 864, 288, CEIL, 'fac_door2_hi')
east_wall(864, 1056, 0, CEIL, 'fac5')
GLASS = T('cc_glass')
D(1224, -896, 96, 1240, -448, 320, GLASS, tag='glass1')
D(1224, 320, 96, 1240, 640, 320, GLASS, tag='glass2')

# partition P1 (x -1184..-1152): kitchen/storeroom | dining
P1F = {'w': KTILE, 'e': MURAL}
def p1(y1, y2, z1, z2, tag, wtex=KTILE):
    S(-1184, y1, z1, -1152, y2, z2, CAULK, faces={'w': wtex, 'e': MURAL}, scale=1.0, tag=tag)
p1(-1024, -800, 0, CEIL, 'p1_a'); p1(-800, -608, 320, CEIL, 'p1_kdoor')
p1(-608, -448, 0, CEIL, 'p1_b'); p1(-448, -64, 0, 112, 'p1_win_lo'); p1(-448, -64, 352, CEIL, 'p1_win_hi')
p1(-64, 448, 0, CEIL, 'p1_c', SW)
p1(448, 640, 320, CEIL, 'p1_sdoor', SW)
p1(640, 1024, 0, CEIL, 'p1_d', SW)
# partition P2 (y 64..96): kitchen | storeroom, door x -1504..-1312
P2F = {'s': KTILE, 'n': SW}
S(-1792, 64, 0, -1504, 96, CEIL, CAULK, faces=P2F, scale=1.0, tag='p2_a')
S(-1504, 64, 320, -1312, 96, CEIL, CAULK, faces=P2F, scale=1.0, tag='p2_door')
S(-1312, 64, 0, -1184, 96, CEIL, CAULK, faces=P2F, scale=1.0, tag='p2_b')

# roof slab with a hatch above the arcade light rig (x 800..992, y -96..96)
RF = {'top': T('cc_roof'), 'bottom': T('cc_ceiling')}
HX1, HX2 = 800, 992
S(-1824, -1056, CEIL, HX1, 1056, ROOF, CAULK, faces=RF, tag='roof_w')
S(HX2, -1056, CEIL, 1248, 1056, ROOF, CAULK, faces=RF, tag='roof_e')
S(HX1, -1056, CEIL, HX2, -96, ROOF, CAULK, faces=RF, tag='roof_s')
S(HX1, 96, CEIL, HX2, 1056, ROOF, CAULK, faces=RF, tag='roof_n')

# ======================================================================== KITCHEN
BRICK = T('cc_brick')
# pizza oven against the west wall, door facing east
D(-1792, -608, 0, -1472, -576, 352, BRICK, scale=0.25, tag='oven_s')
D(-1792, -64, 0, -1472, -32, 352, BRICK, scale=0.25, tag='oven_n')
D(-1504, -576, 0, -1472, -416, 352, BRICK, scale=0.25, tag='oven_front_a')
D(-1504, -224, 0, -1472, -64, 352, BRICK, scale=0.25, tag='oven_front_b')
D(-1504, -416, 192, -1472, -224, 352, BRICK, scale=0.25, tag='oven_lintel')
D(-1792, -608, 352, -1472, -32, 384, BRICK, faces={'top': T('cc_oven_top')}, scale=0.25, tag='oven_top')
D(-1696, -384, 384, -1600, -288, CEIL, BRICK, scale=0.25, tag='chimney')
D(-1760, -544, 0, -1664, -96, 8, T('cc_coals'), scale=0.25, tag='coals')
light(-1640, -320, 120, 220, (1, 0.55, 0.2))
# tall rack right behind the oven: walk from the oven roof onto its top shelf
shelf_unit(-1760, -32, -1536, 64, [128, 256, 392], 392, tag='krack')

# south prep counter with the deep sink
CTOP = {'top': T('cc_counter_top')}
D(-1792, -1024, 0, -1664, -832, 112, STEEL, faces=CTOP, tag='kc1')
D(-1664, -1024, 0, -1408, -832, 16, STEEL, tag='sink_floor')
D(-1664, -1024, 16, -1408, -992, 112, STEEL, tag='sink_back')
D(-1664, -864, 16, -1408, -832, 112, STEEL, tag='sink_front')
D(-1664, -992, 16, -1632, -864, 112, STEEL, tag='sink_w')
D(-1440, -992, 16, -1408, -864, 112, STEEL, tag='sink_e')
D(-1408, -1024, 0, -1184, -832, 112, STEEL, faces=CTOP, tag='kc2')
W(wedge(-1552, -992, 16, -1440, -864, 112, 'e', T('cc_cuttingboard'), 'sink_ramp'))
W(brush_from_points([
    ((-1632, -992, 96), (-1632, -864, 96), (-1440, -864, 96), T('cc_water')),
    ((-1632, -992, 16), (-1440, -992, 16), (-1440, -864, 16), T('cc_water')),
    ((-1632, 0, 0), (-1632, 1, 0), (-1632, 0, 1), T('cc_water')),
    ((-1440, 0, 0), (-1440, 1, 0), (-1440, 0, 1), T('cc_water')),
    ((0, -992, 0), (1, -992, 0), (0, -992, 1), T('cc_water')),
    ((0, -864, 0), (1, -864, 0), (0, -864, 1), T('cc_water')),
    ((-1552, -992, 16), (-1552, -864, 16), (-1440, -992, 112), T('cc_water')),
], inside=(-1596, -928, 50), kind='water', tag='sink_water'))
light(-1536, -928, 300, 200, (0.8, 0.9, 1.0))
stairs(-1408, -832, -1232, -768, 0, 7, 16, 'x', -1, tag='kstair')
# pass-through counter under the service window
D(-1312, -448, 0, -1184, -64, 112, STEEL, faces=CTOP, tag='kpass')
# little prep table between the oven and the pass
D(-1408, -32, 0, -1344, 32, 72, WOOD, tag='ktable')

# ======================================================================== STOREROOM
shelf_unit(-1728, 288, -1344, 384, [128, 256, 392], 392, tag='srack1')
shelf_unit(-1728, 640, -1344, 736, [128, 256, 392], 392, tag='srack2')
D(-1760, 864, 0, -1568, 992, 72, WOOD, tag='desk')
D(-1696, 784, 0, -1632, 832, 32, VINYL, tag='desk_stool')
for i, (x, y, h) in enumerate([(-1296, 128, 48), (-1248, 960, 80), (-1776, 448, 64), (-1296, 960, 32), (-1248, 128, 96)]):
    D(x, y, 0, x + 48, y + 48, h, PIZZABOX, scale=0.25, tag='pbox%d' % i)

# ======================================================================== DINING
def booth(x0, side):
    if side < 0:
        ya, yb = -1024, -784
    else:
        ya, yb = 784, 1024
    D(x0, ya, 0, x0 + 96, yb, 32, VINYL, tag='bench%d_%d' % (x0, side))
    D(x0, ya, 32, x0 + 24, yb, 112, VINYL, tag='back%d_%d' % (x0, side))
    D(x0 + 352, ya, 0, x0 + 448, yb, 32, VINYL, tag='bench%db_%d' % (x0, side))
    D(x0 + 424, ya, 32, x0 + 448, yb, 112, VINYL, tag='back%db_%d' % (x0, side))
    ta, tb = (ya, yb - 16) if side < 0 else (ya + 16, yb)
    D(x0 + 128, ta, 56, x0 + 320, tb, 64, WOOD, tag='btable%d_%d' % (x0, side))
    pc = (ta + tb) // 2
    D(x0 + 208, pc - 16, 0, x0 + 240, pc + 16, 56, STEEL, tag='bped%d_%d' % (x0, side))
    return (x0 + 224, pc)


booth_tables = []
for x0 in (-1120, -608):
    booth_tables.append(booth(x0, -1)); booth_tables.append(booth(x0, 1))

table_centres = []
for cx in (-800, -352):
    for cy in (-560, -200, 200, 560):
        D(cx - 96, cy - 96, 56, cx + 96, cy + 96, 64, WOOD, tag='table%d_%d' % (cx, cy))
        D(cx - 16, cy - 16, 0, cx + 16, cy + 16, 56, STEEL, tag='tped%d_%d' % (cx, cy))
        for sx in (-1, 1):
            xa = cx + sx * 104; xb = cx + sx * 160
            x1, x2 = min(xa, xb), max(xa, xb)
            D(x1, cy - 32, 0, x2, cy + 32, 32, VINYL, tag='chair%d_%d_%d' % (cx, cy, sx))
            bx1, bx2 = (x2 - 16, x2) if sx > 0 else (x1, x1 + 16)
            D(bx1, cy - 32, 32, bx2, cy + 32, 104, VINYL, tag='chairb%d_%d_%d' % (cx, cy, sx))
        table_centres.append((cx, cy))
# dining-side service counter under the window
D(-1152, -448, 0, -1056, -64, 112, T('cc_counter_front'), faces=CTOP, tag='dcounter')
# jukebox against the partition (north of the counter)
D(-1152, 224, 0, -1088, 352, 192, T('cc_cab_side'), faces={'e': T('cc_screen3'), 'top': T('cc_cab_top')}, tag='jukebox')
# dining light rig
TRUSS = T('cc_truss')
D(-1088, -64, 496, -688, 64, 512, TRUSS, tag='drig')
D(-1072, 48, 512, -1056, 64, CEIL, STEEL, tag='drig_rod_w')
D(-720, -64, 512, -704, -48, CEIL, STEEL, tag='drig_rod_e')

# ======================================================================== LANDER playhouse
FOIL, LWHITE = T('cc_foil'), T('cc_lander')
LX1, LX2, LY1, LY2, LH = -32, 416, -224, 224, 288
LCX, LCY = (LX1 + LX2) // 2, (LY1 + LY2) // 2
def lwall_x(y1, y2, tag):  # wall running along x at y1..y2, door in the middle
    D(LX1, y1, 0, LCX - 80, y2, LH, FOIL, tag=tag + 'a'); D(LCX + 80, y1, 0, LX2, y2, LH, FOIL, tag=tag + 'b')
    D(LCX - 80, y1, 192, LCX + 80, y2, LH, FOIL, tag=tag + 'c')
def lwall_y(x1, x2, tag):
    D(x1, LY1 + 32, 0, x2, LCY - 80, LH, FOIL, tag=tag + 'a'); D(x1, LCY + 80, 0, x2, LY2 - 32, LH, FOIL, tag=tag + 'b')
    D(x1, LCY - 80, 192, x2, LCY + 80, LH, FOIL, tag=tag + 'c')
lwall_x(LY1, LY1 + 32, 'ld_s'); lwall_x(LY2 - 32, LY2, 'ld_n')
lwall_y(LX1, LX1 + 32, 'ld_w'); lwall_y(LX2 - 32, LX2, 'ld_e')
D(LX1, LY1, LH, LX2, LY2, LH + 32, LWHITE, tag='ld_roof')
for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
    cx = LX1 if sx < 0 else LX2
    cy = LY1 if sy < 0 else LY2
    fx1, fx2 = sorted((cx, cx + sx * 80)); fy1, fy2 = sorted((cy, cy + sy * 80))
    D(fx1, fy1, 0, fx2, fy2, 16, STEEL, tag='ld_foot%d%d' % (sx, sy))
    lx1, lx2 = sorted((cx, cx + sx * 32)); ly1, ly2 = sorted((cy, cy + sy * 32))
    D(lx1, ly1, 16, lx2, ly2, 256, STEEL, tag='ld_leg%d%d' % (sx, sy))
light(LCX, LCY, 160, 220, (0.6, 0.9, 1.0))

# ======================================================================== ARCADE
CSIDE, CFRONT = T('cc_cab_side'), T('cc_cab_front')


def cabinet(x0, y0, facing, i):
    SCREEN = T(('cc_screen', 'cc_screen2', 'cc_screen3')[i % 3]); MARQ = T(('cc_marquee', 'cc_marquee2', 'cc_marquee3')[i % 3])
    if facing == 'n':
        fs = {'n': (-0.5, 0.5)}
        D(x0, y0, 0, x0 + 128, y0 + 96, 112, CSIDE, faces={'n': CFRONT}, scales=fs, offs={'n': (0, 224)}, tag='cab%d_lo' % i)
        D(x0, y0 + 96, 96, x0 + 128, y0 + 128, 128, T('cc_panel'), tag='cab%d_panel' % i)
        D(x0, y0, 112, x0 + 128, y0 + 80, 224, CSIDE, faces={'n': SCREEN}, scales=fs, offs={'n': (0, 192)}, tag='cab%d_up' % i)
        D(x0, y0, 224, x0 + 128, y0 + 96, 256, CSIDE, faces={'n': MARQ, 'top': T('cc_cab_top')}, scales=fs, offs={'n': (0, 0)}, tag='cab%d_mq' % i)
    else:
        D(x0, y0 - 96, 0, x0 + 128, y0, 112, CSIDE, faces={'s': CFRONT}, offs={'s': (128, 224)}, tag='cab%d_lo' % i)
        D(x0, y0 - 128, 96, x0 + 128, y0 - 96, 128, T('cc_panel'), tag='cab%d_panel' % i)
        D(x0, y0 - 80, 112, x0 + 128, y0, 224, CSIDE, faces={'s': SCREEN}, offs={'s': (128, 192)}, tag='cab%d_up' % i)
        D(x0, y0 - 96, 224, x0 + 128, y0, 256, CSIDE, faces={'s': MARQ, 'top': T('cc_cab_top')}, offs={'s': (128, 0)}, tag='cab%d_mq' % i)


ci = 0
for k in range(8):                       # south wall row  x 32..1056
    cabinet(32 + 128 * k, -1024, 'n', ci); ci += 1
for k in range(4):                       # back-to-back island x 128..640, y -704..-512
    cabinet(128 + 128 * k, -608, 'n', ci); ci += 1
    cabinet(128 + 128 * k, -608, 's', ci); ci += 1

# claw machine
CLX, CLY = 992, -320
D(CLX, CLY, 0, CLX + 192, CLY + 192, 96, T('cc_claw_base'), tag='claw_base')
D(CLX, CLY, 96, CLX + 8, CLY + 192, 288, GLASS, tag='claw_gw'); D(CLX + 184, CLY, 96, CLX + 192, CLY + 192, 288, GLASS, tag='claw_ge')
D(CLX + 8, CLY, 96, CLX + 184, CLY + 8, 288, GLASS, tag='claw_gs'); D(CLX + 8, CLY + 184, 96, CLX + 184, CLY + 192, 288, GLASS, tag='claw_gn')
D(CLX, CLY, 288, CLX + 192, CLY + 192, 304, T('cc_claw_base'), faces={'s': T('cc_marquee'), 'n': T('cc_marquee')}, tag='claw_top')
D(CLX + 92, CLY + 92, 216, CLX + 100, CLY + 100, 288, STEEL, tag='claw_rod')
D(CLX + 80, CLY + 80, 200, CLX + 112, CLY + 112, 216, STEEL, tag='claw_head')

# air-hockey table (cover in the middle of the hall)
D(672, -192, 0, 928, -64, 80, T('cc_claw_base'), faces={'top': T('cc_neon_cyan')}, tag='airhockey')
light(800, -128, 160, 120, (0.5, 0.9, 1.0))
# coin-op moon buggy ride
D(960, -560, 0, 1152, -432, 32, T('cc_claw_base'), tag='ride_base')
D(992, -544, 32, 1120, -448, 96, T('cc_van'), tag='ride_body')
D(992, -544, 96, 1024, -448, 144, VINYL, tag='ride_seatback')
for (wx, wy) in ((1000, -560), (1080, -560), (1000, -448), (1080, -448)):
    D(wx, wy, 32, wx + 32, wy + 16, 64, T('cc_rubber'), tag='ride_wheel_%d_%d' % (wx, wy))

# ball-pit crater (ramps 256 long, flat 128)
W(wedge(PX1, PY1, -192, PX2, PY1 + 256, 0, 's', FOAM, 'pit_ramp_s'))
W(wedge(PX1, PY2 - 256, -192, PX2, PY2, 0, 'n', FOAM, 'pit_ramp_n'))
D(PX1 - 32, PY1, 0, PX1, PY2, 32, FOAM, tag='pit_rim_w'); D(PX2, PY1, 0, PX2 + 32, PY2, 32, FOAM, tag='pit_rim_e')
W(brush_from_points([
    ((PX1, PY1, -48), (PX1, PY2, -48), (PX2, PY2, -48), T('cc_ballpit')),
    ((PX1, PY1, -192), (PX2, PY1, -192), (PX2, PY2, -192), T('cc_ballpit')),
    ((PX1, 0, 0), (PX1, 1, 0), (PX1, 0, 1), T('cc_ballpit')),
    ((PX2, 0, 0), (PX2, 1, 0), (PX2, 0, 1), T('cc_ballpit')),
    ((PX1, PY1 + 256, -192), (PX2, PY1 + 256, -192), (PX1, PY1, 0), T('cc_ballpit')),
    ((PX1, PY2 - 256, -192), (PX2, PY2 - 256, -192), (PX1, PY2, 0), T('cc_ballpit')),
], inside=((PX1 + PX2) / 2, (PY1 + PY2) / 2, -150), kind='water', tag='ballpit'))
light((PX1 + PX2) / 2, (PY1 + PY2) / 2, 120, 260, (1.0, 0.6, 0.9))

# prize counter + wall shelving (north wall)
D(0, 640, 0, 544, 768, 112, T('cc_counter_front'), faces=CTOP, tag='prize_counter')
stairs(-112, 640, 0, 768, 0, 7, 16, 'x', 1, tex=T('cc_counter_front'), tag='pstair')
D(0, 896, 0, 32, 1024, 448, T('cc_shelf_side'), tag='pshelf_w')
D(608, 896, 0, 640, 1024, 448, T('cc_shelf_side'), tag='pshelf_e')
for i, z in enumerate((16, 160, 304, 448)):
    D(32, 896, z - (16 if i == 0 else 8), 608, 1024, z, T('cc_shelf'), tag='pshelf_%d' % i)

# ceiling duct (hidden iMPERiUS) hangs z 592..768 over y 640..832
DUCT, GRATE = T('cc_duct'), T('cc_grate')
DY1, DY2 = 640, 832
D(32, DY1, 592, 864, DY2, 608, DUCT, tag='duct_f1'); D(960, DY1, 592, 1152, DY2, 608, DUCT, tag='duct_f2')
D(864, DY1, 592, 960, DY1 + 32, 608, DUCT, tag='duct_f3'); D(864, DY2 - 80, 592, 960, DY2, 608, DUCT, tag='duct_f4')
for (x1, x2) in ((32, 288), (416, 544), (672, 1152)):
    D(x1, DY1, 608, x2, DY1 + 16, CEIL, DUCT, tag='duct_s_%d' % x1)
for (x1, x2) in ((288, 416), (544, 672)):
    D(x1, DY1, 608, x2, DY1 + 16, 640, DUCT, tag='duct_slo_%d' % x1)
    D(x1, DY1, 720, x2, DY1 + 16, CEIL, DUCT, tag='duct_shi_%d' % x1)
    D(x1, DY1 + 4, 640, x2, DY1 + 12, 720, GRATE, scale=0.25, tag='duct_grate_%d' % x1)
D(32, DY2 - 16, 608, 64, DY2, CEIL, DUCT, tag='duct_n1'); D(256, DY2 - 16, 608, 1152, DY2, CEIL, DUCT, tag='duct_n2')
D(32, DY1 + 16, 608, 48, DY2 - 16, CEIL, DUCT, tag='duct_cap_w'); D(1136, DY1 + 16, 608, 1152, DY2 - 16, CEIL, DUCT, tag='duct_cap_e')
light(300, 736, 700, 220, (0.7, 0.4, 1.0))
light(640, 736, 700, 260, (0.7, 0.4, 1.0))
light(1040, 736, 700, 200, (0.7, 0.4, 1.0))

# arcade light rig under the roof hatch
D(512, -96, 496, 1088, 96, 512, TRUSS, tag='arig')
D(528, 80, 512, 544, 96, CEIL, STEEL, tag='arig_rod_w'); D(1056, -96, 512, 1072, -80, CEIL, STEEL, tag='arig_rod_e')

# neon strips
for (x1, x2) in ((-1152, -608), (-160, 0), (640, 1216)):
    D(x1, 1016, 120, x2, 1024, 128, T('cc_neon_cyan'), scale=0.25, tag='neon_n%d' % x1)
for (x1, x2) in ((-1152, -1120), (-672, -608), (1056, 1216)):
    D(x1, -1024, 120, x2, -1016, 128, T('cc_neon_magenta'), scale=0.25, tag='neon_s%d' % x1)
D(-1152, -1024, 680, 1216, -1016, 688, T('cc_neon_yellow'), scale=0.25, tag='neon_s_hi')
D(-1152, 1016, 680, 1216, 1024, 688, T('cc_neon_yellow'), scale=0.25, tag='neon_n_hi')

# ======================================================================== PARKING LOT
CONC, CURB = T('cc_concrete'), T('cc_curb')
D(1248, -1024, 0, 1440, 1024, 16, CONC, faces={'e': CURB}, tag='sidewalk')
FENCE = T('cc_fence')
D(1248, 1024, 0, 2624, 1056, 256, FENCE, tag='fence_n')
D(1248, -1056, 0, 2624, -1024, 256, FENCE, tag='fence_s')
D(2624, -1056, 0, 2656, 1056, 256, FENCE, tag='fence_e')
PLANT = {'top': T('cc_grass')}
planters = ((2400, 768), (1792, -848))
for (cx, cy) in planters:
    D(cx - 160, cy - 160, 0, cx + 160, cy + 160, 32, CURB, faces=PLANT, tag='planter_%d_%d' % (cx, cy))
D(1600, 128, 0, 1792, 320, 48, CONC, tag='pedestal')
# delivery van  (x 1664..2304, y -608..-288)
VAN, VANL = T('cc_van'), T('cc_van_logo')
VX, VY = -704, 96
D(2464 + VX, -672 + VY, 0, 2528 + VX, -416 + VY, 48, T('cc_rubber'), tag='van_axle_f')
D(2848 + VX, -672 + VY, 0, 2912 + VX, -416 + VY, 48, T('cc_rubber'), tag='van_axle_r')
D(2368 + VX, -704 + VY, 48, 2496 + VX, -384 + VY, 176, VAN, faces={'w': T('cc_van_grille')}, tag='van_hood')
D(2496 + VX, -704 + VY, 48, 2624 + VX, -384 + VY, 288, VAN, faces={'w': T('cc_van_windshield'), 'n': T('cc_van_cabside'), 's': T('cc_van_cabside')}, tag='van_cab')
D(2624 + VX, -704 + VY, 48, 3008 + VX, -384 + VY, 64, VAN, faces={'top': T('cc_van_floor')}, tag='van_floor')
D(2624 + VX, -704 + VY, 64, 3008 + VX, -688 + VY, 288, VAN, faces={'s': VANL}, scales={'s': 0.75}, offs={'s': (85 - VX * 4 // 3, 128)}, tag='van_wall_s')
D(2624 + VX, -400 + VY, 64, 2688 + VX, -384 + VY, 288, VAN, tag='van_wall_n1')
D(2816 + VX, -400 + VY, 64, 3008 + VX, -384 + VY, 288, VAN, faces={'n': VANL}, scales={'n': (-0.75, 0.75)}, offs={'n': (85 + VX * 4 // 3, 128)}, tag='van_wall_n2')
D(2688 + VX, -400 + VY, 256, 2816 + VX, -384 + VY, 288, VAN, tag='van_wall_n3')
D(2624 + VX, -704 + VY, 288, 3008 + VX, -384 + VY, 304, VAN, tag='van_roof')
D(3008 + VX, -672 + VY, 0, 3040 + VX, -416 + VY, 32, T('cc_rubber'), tag='van_bumper')
D(2688 + VX, -384 + VY, 0, 2816 + VX, -352 + VY, 32, T('cc_rubber'), tag='van_step')
D(2640 + VX, -680 + VY, 64, 2704 + VX, -616 + VY, 128, PIZZABOX, scale=0.25, tag='van_boxes1')
D(2640 + VX, -600 + VY, 64, 2704 + VX, -536 + VY, 96, PIZZABOX, scale=0.25, tag='van_boxes2')
light(2900 + VX, -544 + VY, 240, 160, (1.0, 0.9, 0.7))
# dumpster (open top, side door) + crate steps
DUMP = T('cc_dumpster')
DX0, DY0 = 1824, 848
D(DX0, DY0, 0, DX0 + 224, DY0 + 160, 16, DUMP, tag='dump_floor')
D(DX0, DY0, 16, DX0 + 224, DY0 + 16, 160, DUMP, tag='dump_s')
D(DX0, DY0 + 144, 16, DX0 + 224, DY0 + 160, 160, DUMP, tag='dump_n')
D(DX0 + 208, DY0 + 16, 16, DX0 + 224, DY0 + 144, 160, DUMP, tag='dump_e')
D(DX0, DY0 + 16, 16, DX0 + 16, DY0 + 32, 160, DUMP, tag='dump_w1')
D(DX0, DY0 + 128, 16, DX0 + 16, DY0 + 144, 160, DUMP, tag='dump_w2')
D(DX0, DY0 + 32, 144, DX0 + 16, DY0 + 128, 160, DUMP, tag='dump_w3')
for i in range(4):
    D(1568 + 64 * i, 784, 0, 1632 + 64 * i, 848, 32 * (i + 1), CRATE, scale=0.25, tag='dcrate%d' % i)
light(DX0 + 112, DY0 + 80, 120, 120, (0.7, 1.0, 0.6))
# lamp posts
for (cx, cy) in ((1504, 512), (1504, -384), (2560, -128)):
    D(cx - 8, cy - 8, 0, cx + 8, cy + 8, 448, STEEL, tag='lamp_%d_%d' % (cx, cy))
    D(cx - 48, cy - 24, 448, cx + 48, cy + 24, 480, STEEL, faces={'bottom': T('cc_lamp_light')}, tag='lamphead_%d_%d' % (cx, cy))
    light(cx, cy, 420, 3500, (1.0, 0.85, 0.65))
# parking bay lines
for k, x in enumerate((1664, 1920, 2176)):
    D(x, -192, 0, x + 8, 64, 1, NODRAW, faces={'top': T('cc_lotline')}, tag='line%d' % k)
# stacked pallets by the east fence (cover)
D(2464, -760, 0, 2592, -632, 32, WOOD, tag='pallet1'); D(2464, -760, 32, 2592, -632, 64, WOOD, tag='pallet2')
D(2480, -744, 64, 2576, -648, 128, PIZZABOX, scale=0.25, tag='pallet_boxes')
# facade sign
D(1248, -512, 448, 1264, 512, 704, T('cc_sign_back'), faces={'e': T('cc_sign')}, scales={'e': 1.0}, offs={'e': (512, 192)}, tag='sign')

# ======================================================================== ROOF
for (x1, y1) in ((-1600, 640), (-400, -900), (-900, 300), (300, 500)):
    D(x1, y1, ROOF, x1 + 192, y1 + 128, ROOF + 96, T('cc_ac'), faces={'top': T('cc_ac_top')}, tag='ac_%d' % x1)
# water tank sniper perch over the kitchen
TX1, TY1 = -1632, -436
for (lx, ly) in ((TX1 + 16, TY1 + 16), (TX1 + 232, TY1 + 16), (TX1 + 16, TY1 + 232), (TX1 + 232, TY1 + 232)):
    D(lx, ly, ROOF, lx + 24, ly + 24, 1000, STEEL, tag='tankleg_%d_%d' % (lx, ly))
D(TX1, TY1, 1000, TX1 + 272, TY1 + 272, 1160, T('cc_tank'), faces={'top': T('cc_ac_top')}, scale=1.0, tag='tank')
for y1 in (-640, -440):
    W(wedge(-1100, y1, ROOF, -716, y1 + 128, ROOF + 48, 'n', STEEL, 'solar_%d' % y1, top_tex=T('cc_solar')))
for (x1, y1) in ((-700, 600), (200, -700)):
    D(x1, y1, ROOF, x1 + 256, y1 + 192, ROOF + 24, STEEL, faces={'top': T('cc_skylight')}, tag='skylight_%d' % x1)
for (vx, vy) in ((-1700, 900), (-200, -300), (600, -950), (1100, 900), (-1300, 300)):
    D(vx, vy, ROOF, vx + 48, vy + 48, ROOF + 96, T('cc_duct'), scale=0.25, tag='vent_%d_%d' % (vx, vy))
light(-1496, -300, 1300, 600, (0.8, 0.85, 1.0))
light(-300, 0, 1000, 900, (0.8, 0.85, 1.0))
light(-1300, 600, 1000, 900, (0.8, 0.85, 1.0))
light(700, -600, 1000, 900, (0.8, 0.85, 1.0))

# ======================================================================== JUMP PADS
pad(-1376, -560, 0, -1632, -470, 384, 600, 'k_oven')       # kitchen floor -> oven roof (-> walk onto rack top)
pad(-1536, 512, 0, -1536, 688, 392, 560, 's_rack2')        # storeroom floor -> rack 2
pad(-1424, 688, 392, -1424, 336, 392, 540, 's_rack1')      # rack 2 -> rack 1
pad(-576, 0, 0, -820, 0, 512, 680, 'd_rig')                # dining floor -> dining rig
pad(LCX, 352, 0, LCX, 96, LH + 32, 540, 'lander')          # arcade floor -> lander roof
pad(300, 0, LH + 32, 640, 0, 512, 690, 'lander_arig')      # lander roof -> arcade rig
pad(48, 0, LH + 32, -860, 0, 512, 690, 'lander_drig')      # lander roof -> dining rig
pad(848, 0, 512, 1120, 0, ROOF, 980, 'hatch')              # arcade rig -> roof (through the hatch)
pad(816, -360, 0, 480, -560, 256, 420, 'island')           # arcade -> cabinet island top
pad(1136, -800, 0, 960, -976, 256, 430, 'southrow')        # -> south cabinet row top
pad(272, 704, 112, 272, 960, 448, 520, 'prize')            # prize counter -> top shelf
pad(128, 960, 448, 160, 736, 608, 720, 'duct')             # top shelf -> duct mouth
pad(2496, -448, 0, 2144, -448, 304, 500, 'van')            # lot -> van roof
pad(1536, -864, 0, 900, -864, ROOF, 990, 'roof')           # lot -> building roof
pad(-1496, 0, ROOF, -1496, -300, 1160, 1330, 'tank')       # roof -> water tank perch

# ======================================================================== MODELS (catalog objects)
for i, (cx, cy) in enumerate(table_centres):
    model('pad_plates/plate_hp%d.md3' % (1 if i % 2 else 3), cx - 40, cy + 20, 64, 0.15)
    model('pad_ddmix/diner/glass_rings.md3', cx + 44, cy - 40, 64, 0.23)
    model('pad_condiments/salt.md3', cx + 20, cy + 60, 64, 0.4)
    model('pad_condiments/pepper.md3', cx + 44, cy + 60, 64, 0.4)
    if i % 3 == 0:
        model('pad_condiments/pad_ketchup.md3', cx - 60, cy - 56, 64, 0.38)
    if i % 3 == 1:
        model('pad_tins/pad_pupsi.md3', cx - 56, cy - 50, 64, 0.15)
for i, (cx, cy) in enumerate(booth_tables):
    side = -1 if cy < 0 else 1
    model('pad_plates/plate_hp1.md3', cx - 30, cy - side * 20, 64, 0.15)
    model('pad_condiments/sugar.md3', cx + 50, cy + side * 60, 64, 0.45)
    model('pad_condiments/pad_mustard.md3', cx + 70, cy + side * 64, 64, 0.38)
    model('pad_tins/pad_coke.md3', cx + 40, cy - side * 30, 64, 0.15)
# dining counter
model('pad_ddmix/diner/coffe_pot.md3', -1104, -380, 112, 0.27)
model('pad_cake/pad_cakestand.md3', -1104, -170, 112, 0.5)
# dining plants
model('pad_ddmix/plants/bonsai.md3', -1100, 680, 0, 0.48, clip=True)
model('pad_ddmix/plants/bonsai.md3', -1100, -680, 0, 0.48, clip=True)
model('pad_ddmix/plants/cane4.md3', -120, 990, 0, 0.68, clip=True)
# kitchen
model('pad_tins/tomatoes_tl.md3', -1736, -940, 112, 0.28)
model('pad_tins/tomatoes_tl.md3', -1716, -880, 112, 0.28)
model('pad_plates/plate_hpstack2.md3', -1240, -960, 112, 0.15)
model('pad_items/towelroll.md3', -1340, -980, 112, 0.5)
model('pad_scouringpad/scouringpad_yellow.md3', -1500, -852, 112, 0.5)
model('pad_plates/plate_hpstack2.md3', -1248, -128, 112, 0.15)
model('pad_ddmix/trashcan/garbage_bag_standing.md3', -1230, -540, 0, 0.8, clip=True)
model('padmousetrap/padjumptrap.md3', -1400, -260, 0, 1.0, angle=90)
model('pad_fridge/veg_bag.md3', -1660, 16, 128, 0.8)
model('pad_tins/tomatoes_ts.md3', -1600, 16, 256, 0.35)
model('pad_ddmix/diner/muffin_choco.md3', -1376, -60, 72, 0.5)
# storeroom
for k, x in enumerate((-1640, -1500, -1400)):
    model('pad_tins/pad_coke.md3', x, 336, 128, 0.4)
    model('pad_tins/tomatoes_ts.md3', x - 20, 688, 256, 0.35)
model('pad_fridge/veg_bag.md3', -1560, 336, 256, 0.8)
model('pad_fridge/veg_bag.md3', -1640, 688, 128, 0.8)
model('pad_pc/pad_tft.md3', -1700, 940, 72, 0.23, angle=270)
model('pad_lamps/gooseneck.md3', -1620, 920, 72, 0.35, angle=270)
model('pad_ddmix/trashcan/garbage_bag_group.md3', -1730, 140, 0, 0.8, clip=True)
# arcade
model('pad_ddmix/padshop/cardboard_standup.md3', 1120, 960, 0, 0.65, angle=180, clip=True)
model('pad_ddmix/padshop/cardboard_standup.md3', 1180, -660, 0, 0.65, angle=90, clip=True)
model('pad_ddmix/plants/cane4.md3', 1180, -40, 0, 0.68, clip=True)
model('pad_ddmix/plants/bonsai.md3', 1120, -940, 0, 0.48, clip=True)
model('pad_pc/pad_tft.md3', 440, 704, 112, 0.23, angle=90)
model('padtv/padtv2.md3', 120, 704, 112, 0.18, angle=90)
model('pad_statues/statue_super.md3', -10, -380, 0, 0.45, angle=0, clip=True)
model('pad_ddmix/cabin/telescope.md3', 520, 400, 0, 0.4, angle=90, clip=True)
for k, x in enumerate((90, 200, 310, 420, 530)):
    model(['gummybears/redbear.md3', 'gummybears/greenbear.md3', 'gummybears/yellowbear.md3', 'gummybears/redbear.md3', 'gummybears/greenbear.md3'][k], x, 930, 160, 0.33, angle=90)
    model('pad_nascars/padcar_%s.md3' % ['orange', 'black', 'muster', 'orange', 'black'][k], x + 20, 960, 16, 1.0, angle=90)
model('pad_ducks/pad_duck.md3', 80, 960, 304, 0.25, angle=270)
model('pad_ball/pad_basketball.md3', 200, 960, 304, 0.35)
model('pad_ball/pad_soccerball.md3', 310, 960, 304, 0.35)
model('pad_radio_car/radio_control.md3', 430, 960, 304, 0.5, angle=270)
model('pad_ducks/pad_duck.md3', 540, 960, 304, 0.25, angle=270)
model('ente/padstatue_gold.md3', 300, 980, 448, 0.25, angle=270)
for (x, y) in ((CLX + 24, CLY + 30), (CLX + 24, CLY + 160), (CLX + 164, CLY + 20), (CLX + 164, CLY + 160), (CLX + 84, CLY + 25)):
    model('pad_ball/pad_tennisball.md3', x, y, 96, 1.0)
model('gummybears/greenbear.md3', CLX + 114, CLY + 100, 96, 0.22)
model('gummybears/yellowbear.md3', CLX + 54, CLY + 100, 96, 0.22, angle=90)
model('pad_ducks/pad_duck.md3', CLX + 84, CLY + 150, 96, 0.12)
model('pad_ball/pad_soccerball.md3', 740, -128, 80, 0.2)
# lot
for (cx, cy), m in zip(planters, ('tree_summer', 'tree_autumn')):
    model('pad_ddmix/trashcan/%s.md3' % m, cx, cy, 32, 1.0, clip='trunk')
model('pad_statues/statue_super.md3', 1696, 224, 48, 0.9, angle=180, clip=True)
for x in (1560,):
    model('pad_ddmix/trashcan/bush.md3', x, 975, 0, 0.5, clip=True)
for x in (2200, 2500):
    model('pad_ddmix/trashcan/bush.md3', x, -975, 0, 0.5, angle=180, clip=True)
model('pad_ddmix/trashcan/garbage_bag_group.md3', 2124, 960, 0, 1.0, clip=True)
model('pad_ddmix/trashcan/garbage_bag_lying.md3', DX0 + 170, DY0 + 105, 16, 0.9)
model('pad_ddmix/trashcan/garbage_bag_standing.md3', DX0 + 170, DY0 + 43, 16, 0.8)
model('pad_ddmix/backyard/tire.md3', 2590, 500, 0, 0.33, angle=90)
model('pad_ddmix/backyard/tire.md3', 2590, 300, 0, 0.33, angle=90)
for (x, a, y) in ((2496 + VX, 0, -704 + VY), (2880 + VX, 0, -704 + VY), (2496 + VX, 180, -384 + VY), (2880 + VX, 180, -384 + VY)):
    model('pad_ddmix/backyard/tire.md3', x, y, 0, 0.33, angle=a)
model('pad_ddmix/trashcan/grass.md3', 2300, 880, 32, 0.4)
model('pad_ddmix/trashcan/grass.md3', 1880, -760, 32, 0.4)
model('pad_nascars/padcar_orange.md3', 2160, 360, 0, 7.0, clip=True)
model('pad_nascars/padcar_muster.md3', 2480, 300, 0, 7.0, angle=180, clip=True)
model('pad_tins/pad_coke_cr.md3', 2950 + VX, -600 + VY, 64, 0.3)
# roof
model('pad_ddmix/cabin/telescope.md3', 1100, -950, ROOF, 0.58, angle=180, clip=True)
model('pad_ddmix/trashcan/garbage_bag_lying.md3', -1300, 900, ROOF, 0.9)

# ======================================================================== ITEMS
M = 'purple'
item('weapon_imperius', 500, 736, 608, 'duct (secret)', marker=M, wait='120')
item('weapon_splasher', 480, 960, 448, 'prize top shelf', marker=M)
item('weapon_boaster', -1592, -928, 16, 'bottom of the kitchen sink', marker=M)
item('weapon_boaster', 240, -608, 256, 'cabinet island top', marker=M)
item('weapon_betty', -1584, -320, 0, 'inside the pizza oven', marker=M)
item('weapon_pumper', 100, 120, LH + 32, 'lander roof', marker=M)
item('weapon_pumper', 1100, -760, ROOF, 'roof by the telescope', marker=M)
item('weapon_balloony', 2176, -448, 64, 'van cargo', marker=M)
item('weapon_balloony', -1000, 0, 512, 'dining rig', marker=M)
item('weapon_bubbleg', -1600, 688, 392, 'storeroom rack top', marker=M)
item('weapon_bubbleg', DX0 + 60, DY0 + 80, 16, 'inside the dumpster', marker=M)

for (x, y, z, n) in ((-800, 0, 0, 'dining aisle'), (900, -300, 0, 'arcade'), (2000, 0, 0, 'lot'),
                     (-1300, -700, 0, 'kitchen'), (-1300, 560, 0, 'storeroom'), (165, 940, 16, 'prize bottom shelf')):
    item('ammo_nipper', x, y, z, n)
for (x, y, z, n) in ((2080, -448, 64, 'van cargo'), (-760, 0, 512, 'dining rig'), (-1060, -960, 32, 'booth seat'),
                     (2580, 980, 0, 'lot NE'), (LCX, LCY - 100, 0, 'lander inside')):
    item('ammo_balloony', x, y, z, n)
for (x, y, z, n) in ((-1600, -150, 0, 'oven inside'), (-1700, -150, 384, 'oven top'), (1696, 380, 0, 'statue'),
                     (-1080, 100, 0, 'by the jukebox')):
    item('ammo_betty', x, y, z, n)
for (x, y, z, n) in ((-1320, -880, 112, 'kitchen counter'), (500, -608, 256, 'island top'), (880, -800, 0, 'arcade SE'),
                     (-1240, 820, 0, 'storeroom'), (2560, -900, 0, 'lot SE')):
    item('ammo_boaster', x, y, z, n)
for (x, y, z, n) in ((-1680, 688, 392, 'rack2 top'), (1600, 816, 32, 'dumpster crates'), (LCX, LCY + 100, 0, 'lander inside'),
                     (-576, 400, 0, 'dining N'), (1344, 700, 16, 'sidewalk')):
    item('ammo_bubbleg', x, y, z, n)
for (x, y, z, n) in ((330, 150, LH + 32, 'lander roof'), (-384, -960, 0, 'under a booth table'), (1150, -620, ROOF, 'roof'),
                     (1150, 448, 0, 'pit rim'), (2300, 100, 0, 'lot')):
    item('ammo_pumper', x, y, z, n)
for (x, y, z, n) in ((380, 960, 448, 'top shelf'), (-1700, 16, 392, 'kitchen rack top'), (700, -976, 256, 'south row top'),
                     (2240, -448, 304, 'van roof'), (-1560, -340, 1160, 'water tank perch')):
    item('ammo_splasher', x, y, z, n)
for (x, y, z, n) in ((1060, 736, 608, 'duct beyond the drop'), ((PX1 + PX2) // 2, (PY1 + PY2) // 2, -192, 'ball-pit bottom'),
                     (-1500, 336, 392, 'storeroom rack1 top')):
    item('ammo_imperius', x, y, z, n, wait='90')
item('item_armor_padshield', -900, -40, 512, 'dining rig')
item('item_armor_padshield', 400, -976, 256, 'south row top')
item('item_armor_padshield', 2040, -360, 304, 'van roof')
for (x, y, z) in ((-576, -400, 0), (-576, 760, 0), (700, 0, 512), (LCX - 100, LCY, 0), (1344, 0, 16), (2300, -200, 0),
                  (-1400, -700, 0), (-1400, 900, 0), (-250, 0, 0), (900, 400, -192)):
    item('item_armor_shard', x, y, z)
item('item_padpower', -1560, -150, 384, 'oven top (hard)', wait='120')
item('item_speedy', 2100, 700, 0, 'lot')
item('item_jumper', 820, -560, 0, 'arcade')
item('item_visionless', -1740, 560, 0, 'storeroom corner')
item('holdable_floater', -500, 400, ROOF, 'roof')
item('holdable_killerducks', -1480, 920, 0, 'storeroom')
for (x, y) in ((-1640, -720), (1136, 0), (1900, 100)):
    ents.append(Entity('station_health', origin=(x, y, 0)))

# ======================================================================== SPAWNS
for (x, y, z, a) in ((-1300, -960 + 260, 0, 90), (-1420, -680, 0, 180), (-1640, 200, 0, 0),
                     (-1240, 400, 0, 90), (-1440, 820, 0, 180),
                     (-1000, -400, 0, 0), (-1000, 400, 0, 0), (-576, -760, 0, 90), (-576, 200, 0, 270),
                     (-250, -760, 0, 0), (800, -760, 0, 90), (880, -40, 0, 180), (1150, 600, 0, 180), (300, 500, 0, 0),
                     (800, 900, 0, 180), (-250, 400, 0, 0),
                     (1344, -900, 16, 0), (1344, 900, 16, 0), (2000, 300, 0, 180), (2560, -300, 0, 180), (2400, -900, 0, 90),
                     (2000, 750, 0, 270), (-800, -700, ROOF, 0), (300, 800, ROOF, 270)):
    spawn('info_player_deathmatch', x, y, z, a)
for (x, y) in ((-1300, -700), (-1300, 300), (-1640, 480), (-1740, 760)):
    spawn('team_redplayer', x, y, 0, 0)
for (x, y) in ((-1560, -720), (-1400, -150), (-1440, 560), (-1400, 180), (-1000, -800), (-1000, 800)):
    spawn('team_redspawn', x, y, 0, 0)
for (x, y) in ((2560, -580), (2340, 0), (2300, 540), (2000, 600)):
    spawn('team_blueplayer', x, y, 0, 180)
for (x, y) in ((2300, 560), (2100, -150), (2400, -560), (1600, 600), (2000, -900), (1700, -200)):
    spawn('team_bluespawn', x, y, 0, 180)

ents.append(Entity('team_CTL_redlolly', origin=(-1440, 960, 24)))
ents.append(Entity('team_CTL_bluelolly', origin=(2500, -60, 24)))
ents.append(Entity('info_player_intermission', origin=(2500, 900, 600), angles=(25, 200, 0)))
for (n, x, y, z) in (('Kitchen', -1300, -600, 64), ('Storeroom', -1300, 560, 64), ('Dining Floor', -600, 0, 64),
                     ('Arcade', 800, -300, 64), ('Ball Pit', 864, 448, 0), ('Parking Lot', 2100, 0, 64), ('Roof', 0, 0, ROOF + 64),
                     ('Air Duct', 500, 736, 650), ('Prize Counter', 300, 820, 64)):
    ents.append(Entity('target_location', message=n, origin=(x, y, z)))

# ======================================================================== LIGHTS (interior)
for x in (-950, -576, -220):
    for y in (-700, -300, 300, 700):
        light(x, y, 600, 1250, (1.0, 0.85, 1.0))
for x in (100, 500, 900):
    for y in (-760, -340, 340):
        light(x, y, 560, 1600, (0.75, 0.85, 1.0))
light(1150, 900, 560, 1600, (0.75, 0.85, 1.0))
light(100, 900, 560, 1200, (0.75, 0.85, 1.0))
for (x, y) in ((-1300, -900), (-1300, -300), (-1640, -720)):
    light(x, y, 600, 2400, (1.0, 0.97, 0.9))
for (x, y) in ((-1450, 200), (-1450, 520), (-1450, 880)):
    light(x, y, 600, 2000, (1.0, 0.92, 0.75))

json.dump(dict(models=models, items=items, spawns=spawns), open(_os.path.join(_os.environ.get('OUT', 'out'), 'layout_v2.json'), 'w'), indent=1, default=str)
