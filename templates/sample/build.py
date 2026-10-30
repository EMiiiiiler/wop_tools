#!/usr/bin/env python3
"""Sample WoP map generator built on woplib - the starting point `newmap.py` copies for every new map.

    OUT=<dir> python3 build_<ns>.py          (names come from mapinfo.json next to this file)

It is deliberately small but complete, so every pipeline step has something to check:
  * structural hull (caulk outside, sky ceiling) + detail everything else  -> 0-5 portals
  * a house you can walk into, 16u stairs to its roof and a jump pad onto it (Betty on the roof)
  * a pool with 16u steps into shallow water (Splasher on the bottom) and a secret drain teleport to a sealed vault
  * a tower reached only by a pad (Imperius), a ledge up 16u stairs (Balloony), a platform (Pumper)
  * a custom lightmapped MD3 fountain with weapclip collision, catalog props on real surfaces, lights, sounds
  * 3 ammo spots per weapon, 12 spawns, routes for aas_check, spots.json for lint/botreport
Replace the layout functions with the real map; keep the structure (layout -> models -> brushes -> items -> write).
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from wopmap import box, cyl, hull, carve, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL
from meshlib import revolve, disc, rbox

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']                    # playable floor
ZTOP = 1280                                          # sky ceiling
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '18', '_color': '1 0.97 0.92'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout constants
HOUSE = (-256, 256, 256, 640); HOUSE_H = 256; WALL = 16; DOOR = (-48, 48, 128)      # x0 y0 x1 y1, door x0 x1 top
POOL = (-1280, -1088, -768, -704); POOL_FLOOR = -96; WATER_TOP = -8
TOWER = (960, -1024, 1152, -832); TOWER_H = 512
LEDGE = (X0, 0, X0 + 224, 512); LEDGE_Z = 128
PLAT = (1088, 640, 1408, 960); PLAT_Z = 160
VAULT = (-256, -256, 256, 256); VAULT_Z = -1024


# ------------------------------------------------------------------------------------------------ textures
TX = TL.Textures(K)


def textures():
    """one TX.add per brush texture: writes the image, its shader (kind/steps) and its world scale together.
    Use the texlib generators with this map's palette; write your own function for anything unique to the theme."""
    TX.add('paving', TL.tiles((180, 176, 168), (110, 104, 98), cols=4, rows=4, offset=0.5, grout_w=0.03))
    TX.add('plaster', TL.solid((214, 196, 168), 6, 3, 256))
    TX.add('stone', TL.stone((150, 146, 140), cells=18))
    TX.add('tile', TL.tiles((90, 170, 200), (235, 240, 240), cols=8, rows=8, offset=0, grout_w=0.06))
    TX.add('roof', TL.tiles((150, 70, 52), (96, 44, 32), cols=6, rows=10, offset=0.5, vary=14))
    TX.add('wood', TL.planks((150, 104, 62)), steps='woodsteps')
    TX.add('grate', grate(), check_tile=True)
    TX.add('water', TL.solid((60, 140, 170), 10, 11, 128), 'water')
    TX.kit_defaults(pad_rgb=(90, 200, 255))


def grate(n=128):
    """a theme-specific texture stays a local function"""
    x, y = ML.xy(n)
    bars = ((x * 8) % 1 < 0.35)
    return np.where(bars[..., None], ML.C((70, 74, 78)), ML.C((14, 14, 16))) + ML.N3(n, 1, 47, 4)


# ------------------------------------------------------------------------------------------------ custom MD3s
def models():
    """main pieces are custom MD3s (user rule). Look at every model on a contact sheet (preview/md3sheet.py) first."""
    st = TX.material('stone', TL.stone((176, 170, 160), cells=14), shade=40)       # image + model shader in one call
    X = ML.Model()
    # basin wall: profile from the ground out, up over the rim and down inside (one lathe, normals outward)
    revolve(X.mesh(st), [(150, 0), (150, 40), (142, 48), (126, 48), (126, 12)], u_tiles=6, n=48)
    revolve(X.mesh(st), [(24, 0), (24, 120), (40, 132), (40, 140), (0, 140)], u_tiles=2, n=24)    # column; cap runs inward = faces up
    wat = TX.material('water', TL.solid((80, 170, 210), 12, 53), 'add', wave='sin 0.6 0.1 0 0.5', tcmod='scroll 0.03 0.02')
    disc(X.mesh(wat), 126, 30, up=True)
    ML.save('fountain', X)
    # cover: a stack of crates (rounded boxes); collision boxes are kept in CRATES for K.prop()
    cr = TX.material('crate', crate_tex(), shade=30)
    X = ML.Model()
    for (mn, mx) in CRATES:
        rbox(X.mesh(cr), mn, mx, r=4, k=2, tile=96)
    ML.save('crates', X)


CRATES = [((-48, -48, 0), (48, 48, 96)), ((48, -40, 0), (128, 40, 80)), ((-40, -40, 96), (40, 40, 176))]


def crate_tex(n=256):
    x, y = ML.xy(n)
    c = TL.planks((160, 112, 66), n_planks=4, stagger=False, n=n)
    edge = (x < 0.07) | (x > 0.93) | (y < 0.07) | (y > 0.93) | (np.abs(x - y) < 0.05)
    return np.where(edge[..., None], ML.C((110, 72, 40)), c)


# ------------------------------------------------------------------------------------------------ brushes
def shell():
    """structural hull: floor slab (with the pool hole), caulked outer walls with a visible inner face, sky ceiling.
    Everything else is detail, so the map compiles to a handful of portals."""
    floor_tex = {'top': T('paving'), 'side': T('tile'), 'bot': CAULK}      # sides show round the pool hole
    for r in sub_rects((X0 - 32, Y0 - 32, X1 + 32, Y1 + 32), [POOL]):
        K.add(box((r[0], r[1], -32), (r[2], r[3], 0), floor_tex, detail=False))
    wall = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: T('plaster')})
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZTOP), wall('e'), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZTOP), wall('w'), detail=False))
    K.add(box((X0, Y0 - 32, 0), (X1, Y0, ZTOP), wall('n'), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZTOP), wall('s'), detail=False))
    K.add(box((X0 - 32, Y0 - 32, ZTOP), (X1 + 32, Y1 + 32, ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))


def house():
    """walk-in house: door in the south wall, roof slab you can stand on (no parapet: clear line of fire)"""
    x0, y0, x1, y1 = HOUSE; h = HOUSE_H
    pl = {'side': T('plaster'), 'top': T('stone'), 'bot': T('plaster')}
    K.add(box((x0, y0, 0), (x0 + WALL, y1, h), pl), box((x1 - WALL, y0, 0), (x1, y1, h), pl),
          box((x0 + WALL, y1 - WALL, 0), (x1 - WALL, y1, h), pl))
    K.add(box((x0 + WALL, y0, 0), (DOOR[0], y0 + WALL, h), pl), box((DOOR[1], y0, 0), (x1 - WALL, y0 + WALL, h), pl),
          box((DOOR[0], y0, DOOR[2]), (DOOR[1], y0 + WALL, h), pl))
    K.add(box((x0, y0, h), (x1, y1, h + 16), {'top': T('roof'), 'side': T('wood'), 'bot': T('wood')}))
    K.add(sign_box((-120, y0 - 4, 160), (120, y0, 220), T('wood'), 256, 64, back=CAULK, facing='s', edge=T('wood')))
    K.reserve(((x0 - 8, y0 - 8, 0), (x1 + 8, y1 + 8, h + 16)))
    K.keep_clear(DOOR[0] - 48, y0 - 112, DOOR[1] + 48, y0 + 112, 0)              # door approach + landing inside
    # 16u stairs up the east side to the roof (bots skip 32u risers), and a pad from the west
    K.stairs16(x1, y1 - 17 * 32, x1 + 128, y1, 0, h + 16, 'n', {'top': T('stone'), 'side': T('plaster')})
    K.keep_clear(x1, y1 - 17 * 32 - 112, x1 + 128, y1 - 17 * 32, 0)
    K.route('house_door', (0, y0 - 96, 0), (0, y0 + 96, 0))
    K.route('house_stairs', (x1 + 64, y1 - 17 * 32 - 64, 0), (x1 - 96, y1 - 40, h + 16))
    K.jumppad(x0 - 224, (y0 + y1) / 2, 0, land=(x0 + 128, (y0 + y1) / 2, h + 16), apex=h + 16 + 170, name='pad_roof',
              edges=[(x0, (y0 + y1) / 2, h + 16)])


def pool():
    """pool with 16u steps into shallow water at the north end (never a sheer lip that needs a water jump).
    The water is ONE box carved by everything inside it; only its top face draws."""
    x0, y0, x1, y1 = POOL
    tl = {'top': T('tile'), 'side': T('tile'), 'bot': CAULK}
    K.add(box((x0 - 16, y0 - 16, POOL_FLOOR - 16), (x1 + 16, y1 + 16, POOL_FLOOR), tl, detail=False))
    # the basin walls seal the hole in the structural floor slab, so they are structural too (detail does not seal)
    for b in (box((x0 - 16, y0 - 16, POOL_FLOOR), (x0, y1 + 16, -32), tl, detail=False),
              box((x1, y0 - 16, POOL_FLOOR), (x1 + 16, y1 + 16, -32), tl, detail=False),
              box((x0, y0 - 16, POOL_FLOOR), (x1, y0, -32), tl, detail=False),
              box((x0, y1, POOL_FLOOR), (x1, y1 + 16, -32), tl, detail=False)):
        K.add(b)
    steps = K.stairs16(x0, y1 - 5 * 32, x1, y1, POOL_FLOOR, -16, 'n', tl)
    wb = box((x0, y0, POOL_FLOOR), (x1, y1, WATER_TOP), T('water'))
    for piece in carve(wb, steps):
        for f in piece.faces: f.tex = T('water') if f.n[2] > 0.9 and abs(f.d - WATER_TOP) < 0.5 else T('water_nd')
        K.add(piece)
    K.speaker((x0 + x1) / 2, (y0 + y1) / 2, 64, 'ambient/water_rippling')
    K.keep_clear(x0, y1, x1, y1 + 112, 0)
    # secret: the drain grate at the deep end -> sealed vault under the world
    g0 = ((x0 + x1) / 2 - 32, y0 + 32)
    K.add(box((g0[0], g0[1], POOL_FLOOR), (g0[0] + 64, g0[1] + 64, POOL_FLOOR + 1), {'top': T('grate'), 'side': T('grate'), 'bot': CAULK}))
    K.secret((g0[0], g0[1], POOL_FLOOR + 1), (g0[0] + 64, g0[1] + 64, POOL_FLOOR + 48), dest=(0, -128, VAULT_Z), angle=90, name='drain')


def vault():
    """sealed bonus room below the world (its own sealed area: no leak), powerups + a teleporter back"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z
    t = {'side': T('tile'), 'top': T('stone'), 'bot': T('stone')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 256), (x1 + 32, y1 + 32, z + 288), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 256), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 256), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 256), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 256), t, detail=False))
    K.item('item_padpower', -128, 96, z); K.item('item_revival', 0, 160, z); K.item('holdable_killerducks', 128, 96, z)
    K.teleporter((-48, y1 - 64, z), (48, y1, z + 96), dest=(-420, -60, 0), angle=0, name='vault_exit')
    K.light(0, 0, z + 200, 500, '0.8 0.9 1')


def tower_ledge_platform():
    x0, y0, x1, y1 = TOWER
    st = {'side': T('stone'), 'top': T('stone'), 'bot': CAULK}
    K.add(box((x0, y0, 0), (x1, y1, TOWER_H), st)); K.reserve(((x0, y0, 0), (x1, y1, TOWER_H)))
    K.jumppad((x0 + x1) / 2, y1 + 288, 0, land=((x0 + x1) / 2, (y0 + y1) / 2, TOWER_H), apex=TOWER_H + 150, name='pad_tower',
              edges=[((x0 + x1) / 2, y1, TOWER_H)])
    # ledge on the west wall, 16u stairs from the south
    lx0, ly0, lx1, ly1 = LEDGE
    K.add(box((lx0, ly0, 0), (lx1, ly1, LEDGE_Z), {'side': T('stone'), 'top': T('wood'), 'bot': CAULK}))
    K.stairs16(lx0, ly0 - 8 * 32, lx1, ly0, 0, LEDGE_Z, 'n', {'top': T('wood'), 'side': T('stone')})
    K.reserve(((lx0, ly0 - 8 * 32 - 96, 0), (lx1, ly1, LEDGE_Z)))
    K.route('ledge', ((lx0 + lx1) / 2, ly0 - 8 * 32 - 64, 0), ((lx0 + lx1) / 2, ly0 + 96, LEDGE_Z))
    # platform north-east, 16u stairs from the west
    px0, py0, px1, py1 = PLAT
    K.add(box((px0, py0, 0), (px1, py1, PLAT_Z), {'side': T('wood'), 'top': T('wood'), 'bot': CAULK}))
    K.stairs16(px0 - 10 * 32, py0, px0, py0 + 160, 0, PLAT_Z, 'e', {'top': T('stone'), 'side': T('stone')})
    K.reserve(((px0 - 10 * 32 - 96, py0, 0), (px1, py1, PLAT_Z)))
    K.route('platform', (px0 - 10 * 32 - 64, py0 + 80, 0), (px0 + 96, py0 + 80, PLAT_Z))


def props():
    """custom MD3 centrepiece + catalog models on real surfaces; each big model gets weapclip collision"""
    K.custom(ML.PLACE['fountain'], 0, -320, 0, cyls=[(0, 0, 146, 0, 48), (0, 0, 40, 48, 140)])
    K.speaker(0, -320, 96, 'ambient/water_flowing')
    for (x, y) in ((-1100, 900), (700, -300), (-500, -900), (1250, 200), (-900, 300)):
        K.catalog('pad_ddmix/trashcan/tree_summer.md3', x, y, 0, scale=0.6, lit=True)
    for (x, y) in ((-200, -700), (400, 1000), (1300, -300), (-1300, 1100)):
        K.catalog('pad_ducks/pad_duck.md3', x, y, 0, scale=0.5)
    for (x, y) in ((600, 400), (-700, -300)):
        K.catalog('pad_nascars/padcar_black_rc.md3', x, y, 0, scale=0.45, angle=30)
    K.catalog('pad_statues/statue_super.md3', 700, 900, 0, scale=0.6)
    for (x, y) in ((-600, 1100), (-400, 1150), (200, -1150), (500, -1150), (-1450, -300)):
        K.catalog('pad_sunflower/pad_sunflower_l.md3', x, y, 0, scale=0.4, clip=False)


def blockers():
    """sightline cover: put pieces where `sightlines.py --hot` says the most long rays cross (wopbuild sight step),
    next to paths but never on them (K.keep_clear reserves door approaches and stair feet)"""
    for (x, y) in ((-320, -560), (-320, -80), (64, -40), (-700, -560), (-320, -1060), (400, -900), (900, 300), (-1000, 600)):
        K.prop(ML.PLACE['crates'], x, y, 0, boxes=CRATES)


def items():
    """best weapons on the hardest spots, 3 ammo spots each (some hidden, some in plain sight), 12 spawns"""
    hx0, hy0, hx1, hy1 = HOUSE
    K.weapon('imperius', (TOWER[0] + TOWER[2]) / 2, (TOWER[1] + TOWER[3]) / 2, TOWER_H, marker='purple')
    K.weapon('betty', 0, (hy0 + hy1) / 2, HOUSE_H + 16, marker='black')
    K.weapon('splasher', (POOL[0] + POOL[2]) / 2 + 120, (POOL[1] + POOL[3]) / 2 - 40, POOL_FLOOR, marker='blue')
    K.weapon('balloony', (LEDGE[0] + LEDGE[2]) / 2, LEDGE[3] - 96, LEDGE_Z, marker='orange')
    K.weapon('pumper', (PLAT[0] + PLAT[2]) / 2, (PLAT[1] + PLAT[3]) / 2, PLAT_Z, marker='green')
    K.weapon('bubbleg', 0, hy1 - 96, 0, marker='green')
    K.weapon('boaster', -900, -100, 0, marker='orange')
    ammo = {'imperius': [(1056, -700, 0), (-120, hy1 - 80, 0), (-1300, 700, 0)],
            'betty': [(150, (hy0 + hy1) / 2, HOUSE_H + 16), (1300, -1150, 0), (-300, -1100, 0)],
            'splasher': [(-1150, -600, 0), (-800, -1150, 0), (900, 1150, 0)],
            'balloony': [((LEDGE[0] + LEDGE[2]) / 2, LEDGE[1] + 96, LEDGE_Z), (-1100, -150, 0), (300, -650, 0)],
            'pumper': [(PLAT[0] + 64, PLAT[3] - 64, PLAT_Z), (1200, 400, 0), (-200, 1150, 0)],
            'bubbleg': [(120, hy1 - 96, 0), (-1400, 1150, 0), (1400, -650, 0)],
            'boaster': [(-850, 50, 0), (500, 50, 0), (1000, -200, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', 1400, 1150, 0); K.ammo('nipper', -1400, -1150, 0); K.ammo('nipper', 100, 150, 0)
    K.item('item_armor_padshield', 1250, (PLAT[1] + PLAT[3]) / 2, PLAT_Z); K.item('item_armor_shard', -1350, 300, LEDGE_Z)
    K.item('holdable_floater', -150, hy0 + 96, 0); K.item('item_speedy', 1000, -1150, 0)
    K.station(-1450, 1050, 0, ang=315)
    for (x, y, a) in ((-1300, -200, 0), (-1300, 1000, 315), (-600, 1150, 270), (200, 1100, 270), (1000, 1150, 225),
                      (1400, 300, 180), (1350, -500, 135), (800, -1150, 90), (0, -1100, 90), (-500, -500, 45),
                      (-200, 0, 90), (500, -300, 135)):
        K.spawn(x, y, 0, a)


def lights():
    K.light_grid(X0, Y0, X1, Y1, 700, 768, 600)          # light_check: raw 128 = neutral, keep the median ~90-150
    K.light(0, 448, 200, 600)                                     # inside the house
    K.timer_sound(0, 0, 900, 'animal/blackbird', 'birds', 20, 10)


def shader():
    """brush shaders from TX + anything special + every model shader, then the .arena (checked against the lollies)"""
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(225, 55), sun_int=110, skylight=(60, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    textures()
    models()                          # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); house(); pool(); vault(); tower_ledge_platform()
    props(); blockers(); items(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
