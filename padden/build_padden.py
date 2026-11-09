#!/usr/bin/env python3
"""Respawn Room (wop_padden) - FFA in a teenage gamer's bedroom at night, built on woplib + texlib.

    OUT=<dir> python3 build_padden.py          (wopbuild.py padden preview / all)

Padman scale (~8u per cm, catalog models at 1.0). Room x -2048..2048, y -1792..1792, floor z 0, ceiling 2048.
x east, y north. Levels: floor 0, PC tower top 456, desk 600, dresser 720, window sill 760, desk shelf 1280,
loft bed 1216, wardrobe top 1760. See README.md for the design sheet.
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
import dn_models as DM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZC = 2048
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '34', '_color': '0.75 0.75 1'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)

# ------------------------------------------------------------------------------------------------ layout (world)
BED_C = (-1248, 1400)                 # loft bed x -2048..-448, y 1008..1792, duvet top 1216
WARD_C = (-1808, 496)                 # wardrobe x -2048..-1568, y 0..992, top 1760, front +x (south door open)
DRESS_C = (-176, 1584)                # chest of drawers x -432..80, y 1376..1792, top 720
DESK_C = (1728, 440)                  # desk x 1408..2048, y -560..1440, top 600
TOWER_C = (984, 1536)                 # PC tower x 880..1088, y 1296..1776, top 456, front -y, open side -x
TV_C = (-1240, 1612)                  # CRT x -1440..-1040, y 1432..1792, screen faces south (the secret)
FRIDGE_C = (-1856, -1600)             # mini fridge x -2048..-1664, y -1792..-1408, top 480
RUG = (-1200, -1000, 900, 600)        # 4u rug
WIN = (-640, 640, 760, 1720)          # window hole in the south wall x0 x1 z0 z1
SILL = (-704, -1792, 704, -1600, 760)
SHELF_Z = 1280                        # floating shelf over the desk, x 1792..2048, y -360..1240
RAMP = (1536, -1600, 1952, -560)      # the monitor box leaning on the desk (0 -> 600, rising north)
VAULT = (-512, -384, 512, 384); VAULT_Z = -1536
BED_Z, WARD_Z, DRESS_Z, DESK_Z, TOWER_Z = DM.MATT_Z, DM.WARD_H, DM.DRESS_H, DM.DESK_Z, DM.TOWER_H


def fz(x, y):
    """floor height (the rug is a 4u brush)"""
    return 4 if RUG[0] <= x <= RUG[2] and RUG[1] <= y <= RUG[3] else 0


def tex6(**faces):
    t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
    t.update(faces)
    return t


def place(name, x, y, z, angle=0, **kw):
    c = DM.COLL.get(name, {})
    return K.custom(ML.PLACE[name], x, y, z, angle, boxes=c.get('boxes', ()), cyls=c.get('cyls', ()), **kw)


# ------------------------------------------------------------------------------------------------ structure
def shell():
    """structural hull: floor slab, four walls (the south one with the window and a sealed night-sky box behind
    it), ceiling. Everything else is detail."""
    K.add(box((X0 - 32, Y0 - 32, -32), (X1 + 32, Y1 + 32, 0), {'top': T('carpet'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((X0 - 32, Y0 - 32, 0), (X0, Y1 + 32, ZC), tex6(e=T('wall')), detail=False))
    K.add(box((X1, Y0 - 32, 0), (X1 + 32, Y1 + 32, ZC), tex6(w=T('wall')), detail=False))
    K.add(box((X0, Y1, 0), (X1, Y1 + 32, ZC), tex6(s=T('wall_b')), detail=False))
    K.sky_window((X0, Y0 - 32, 0), (X1, Y0, ZC), (WIN[0], WIN[1], WIN[2], WIN[3]), T('wall_b'), T('sky'),
                 jamb_tex=T('frame'), glass_tex=T('glass'), face='n')
    K.add(box((X0 - 32, Y0 - 32, ZC), (X1 + 32, Y1 + 32, ZC + 32), tex6(bot=T('ceiling')), detail=False))
    # rug + window sill
    K.add(box((RUG[0], RUG[1], 0), (RUG[2], RUG[3], 4), {'top': T('rug'), 'side': T('rug'), 'bot': CAULK}))
    x0, y0, x1, y1, z = SILL
    K.add(box((x0, y0, z - 32), (x1, y1, z), {'top': T('sill'), 'side': T('sill'), 'bot': T('sill')}))
    K.reserve(((x0, y0, z - 32), (x1, y1, z)))
    # LED strips round the top of the walls (purple north/south, cyan east/west)
    zt = ZC - 88
    K.add(box((X0 + 8, Y1 - 12, zt), (X1 - 8, Y1 - 4, zt + 16), T('neon_purple')))
    K.add(box((X0 + 8, Y0 + 4, zt), (X1 - 8, Y0 + 12, zt + 16), T('neon_purple')))
    K.add(box((X0 + 4, Y0 + 12, zt), (X0 + 12, Y1 - 12, zt + 16), T('neon_cyan')))
    K.add(box((X1 - 12, Y0 + 12, zt), (X1 - 4, Y1 - 12, zt + 16), T('neon_cyan')))
    # posters (fitted, never mirrored)
    K.add(sign_box((200, Y1 - 4, 900), (600, Y1, 1500), T('poster0'), 512, 768, facing='s', edge=T('frame')))
    K.add(sign_box((X0, -900, 900), (X0 + 4, -500, 1500), T('poster1'), 512, 768, facing='e', edge=T('frame')))
    K.add(sign_box((X1 - 4, -1500, 900), (X1, -1100, 1500), T('poster2'), 512, 768, facing='w', edge=T('frame')))
    K.add(sign_box((1000, Y0, 900), (1400, Y0 + 4, 1500), T('poster3'), 512, 768, facing='n', edge=T('frame')))


def vault():
    """the secret: an 8-bit level under the world (sealed, so no leak) - pixel hills, brick blocks, powerups, and a
    pipe-green teleporter back to the room"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z; h = 448
    sky, brick, grass = T('pixel_sky'), T('pixel_brick'), T('pixel_floor')
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), {'top': grass, 'side': brick, 'bot': brick}, detail=False),
          box((x0 - 32, y0 - 32, z + h), (x1 + 32, y1 + 32, z + h + 32), {'bot': sky, 'side': brick, 'top': brick}, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + h), tex6(e=sky), detail=False),
          box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + h), tex6(w=sky), detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + h), tex6(n=sky), detail=False),
          box((x0, y1, z), (x1, y1 + 32, z + h), tex6(s=sky), detail=False))
    for (bx, by, bz) in ((-256, 160, 0), (-192, 160, 0), (-192, 160, 64), (256, 160, 0)):
        K.add(box((bx, by, z + bz), (bx + 64, by + 64, z + bz + 64), brick))
    K.reserve(((-256, 160, z), (-128, 224, z + 128)), ((256, 160, z), (320, 224, z + 64)))
    K.item('item_padpower', 0, 200, z); K.item('item_revival', -380, -200, z); K.item('holdable_killerducks', 380, -200, z)
    K.item('item_armor_padshield', 0, -60, z)
    K.teleporter((-48, y0, z), (48, y0 + 64, z + 96), dest=(-1250, 250, 0), angle=0, name='vault_exit')
    K.light(0, 0, z + 360, 700, '1 1 0.9'); K.light(-300, 0, z + 200, 300, '0.7 0.8 1'); K.light(300, 0, z + 200, 300, '0.7 0.8 1')


# ------------------------------------------------------------------------------------------------ furniture
def furniture():
    bx, by = BED_C
    place('loft_bed', bx, by, 0)
    wx, wy = WARD_C
    place('wardrobe', wx, wy, 0)
    K.keep_clear(-1568, 24, -1260, 472, 0)                            # walk-in through the open south door
    K.route('wardrobe_in', (-1300, 250, 0), (-1720, 300, 16))
    place('dresser', *DRESS_C, 0)
    dx, dy = DESK_C
    place('desk', dx, dy, 0)
    place('monitors', 1880, 440, DESK_Z)
    place('keyboard', 1600, 440, DESK_Z)
    place('mouse', 1600, 820, DESK_Z, lit=True)
    place('headset', 1720, -380, DESK_Z, angle=90)
    place('can_g', 1520, 30, DESK_Z); place('can_p', 1700, 1020, DESK_Z); place('can_g', 1560, 1300, DESK_Z, angle=40)
    K.catalog('pad_lamps/gooseneck.md3', 1960, -440, DESK_Z, angle=150)
    K.catalog('pad_cups/pad_cup03.md3', 1800, 1150, DESK_Z, angle=200)
    K.catalog('gummybears/ldredbear.md3', 1560, -150, DESK_Z, angle=70)
    K.catalog('pad_tins/pad_pupsi_cr.md3', 1660, 1250, DESK_Z, angle=20)
    # desk shelf
    place('shelf', X1, 440, SHELF_Z)
    K.reserve(((1792, -360, SHELF_Z - 32), (X1, 1240, SHELF_Z)))
    place('trophy', 1920, 1120, SHELF_Z)
    place('games_row', X1, 560, SHELF_Z)
    K.catalog('pad_actionfigures/fig_girl.md3', 1940, -260, SHELF_Z, angle=180)
    K.catalog('pad_actionfigures/fig_lilly.md3', 1940, 160, SHELF_Z, angle=180)
    K.catalog('pad_statues/statue_super.md3', 1950, 980, SHELF_Z, angle=180)
    # ramp: the new monitor's box leaning on the desk
    rb = K.ramp(*RAMP, 0, DESK_Z, 'n', {'top': T('monbox'), 'side': T('cardboard'), 'bot': CAULK}, route='desk_ramp')
    for f in rb.faces:
        if f.n[2] > 0.3:
            f.sc = ((RAMP[2] - RAMP[0]) / 512, (RAMP[3] - RAMP[1]) / 1024); f.off = (-RAMP[0] / f.sc[0] % 512, (RAMP[3] / f.sc[1]) % 1024)
    K.keep_clear(RAMP[0], RAMP[1] - 96, RAMP[2], RAMP[1], 0)
    # PC tower (walk in through the open side; the glass panel lies on the floor)
    tx, ty = TOWER_C
    place('pc_tower', tx, ty, 0)
    K.add(box((tx - 80, 1296, 52), (tx + 68, 1300, 404), WCLIP))      # front mesh between the fans
    place('glass_panel', 720, 1536, 0)
    K.keep_clear(560, 1316, 880, 1756, 6, 102)
    K.route('tower_in', (520, 1450, 0), (980, 1450, 16))
    for z in (120, 240, 360):
        K.rotating_model2(f'models/{NS}/fan_y.iqm', (tx, 1312, z), 220, axis='y')
    for y in (ty - 60, ty + 80):
        K.rotating_model2(f'models/{NS}/fan_z.iqm', (tx, y, TOWER_Z - 18), 180)
    # gaming corner
    place('gaming_chair', 1100, 440, fz(1100, 440))
    place('speaker', 1300, -470, 0, angle=0); place('speaker', 1300, 1370, 0, angle=0)
    place('subwoofer', 1800, 1100, 0)
    # den under the loft bed: CRT + retro console + bean bag
    place('crt_tv', *TV_C, 0)
    place('retro_console', -860, 1640, 0, angle=10)
    place('controller', -1180, 1260, 0, angle=-20)
    place('beanbag_den', -1650, 1300, 0)
    K.catalog('pad_books/comics/pad_comic1.md3', -900, 1300, 0, angle=30, clip=False)
    # window
    place('radiator', 0, Y0, 0)
    place('curtains', 0, Y0, 0)
    K.catalog('pad_ddmix/plants/bonsai.md3', 560, -1700, SILL[4], scale=0.6, angle=0)
    # fridge (pad onto its top) + a pile of pizza boxes
    place('fridge', *FRIDGE_C, 0)
    place('pizza_pile', -1150, -1560, 0, angle=12)
    place('bed_ladder', -620, 1008, 0)
    place('ceiling_lamp', 0, 0, ZC)


def clutter():
    """the lived-in floor: cover that breaks the long lines across the room"""
    place('beanbag', -300, -150, 4, angle=200)
    place('drinks_cases', 450, -820, 4, angle=15)
    place('laundry', -1000, -880, 4)
    place('backpack', 850, -380, 4, angle=30)
    place('guitar', -1520, -760, 0, angle=70)
    place('skateboard', 250, -1380, 0, angle=12)
    place('trash_bin', 1250, -1150, 0)
    place('pc_box', 380, 300, 4, angle=8)
    place('laundry_basket', -850, 140, 4)
    place('store_box', -160, -560, 4, angle=20)
    place('subwoofer', 120, 1090, 0, angle=270)              # the guitar amp
    place('store_box', 1640, -260, 0, angle=90); place('store_box', 1640, 760, 0, angle=85)
    K.catalog('pad_ddmix/padshop/cardboard_standup.md3', -1700, -1150, 0, angle=40)
    K.catalog('pad_ball/pad_basketball.md3', -1250, -350, 0, clip=True)
    K.catalog('pad_nascars/padcar_orange_rc.md3', 380, 700, 4, angle=200)
    K.catalog('pad_radio_car/radio_control_fl.md3', 520, 1000, 0, angle=160, clip=False)
    for (x, y, a) in ((-600, -500, 10), (700, 100, 80), (-200, 900, 140), (1200, -800, 30), (-1500, 500, 200)):
        K.catalog('pad_tins/pad_coke_cr.md3', x, y, fz(x, y), angle=a, clip=False)
    for (x, y, a) in ((-800, -300, 20), (100, 450, 100)):
        K.catalog('pad_clothes/sock_grey.md3', x, y, fz(x, y), angle=a, clip=False)
    K.catalog('pad_books/comics/pad_comic1.md3', 200, -500, 4, angle=60, clip=False)
    K.catalog('pad_ducks/pad_duck.md3', -700, 1500, BED_Z, angle=230)
    K.catalog('pad_phones/pad_padika2.md3', -1500, 1600, BED_Z, angle=10, clip=False)


# ------------------------------------------------------------------------------------------------ pads, loot, spawns
def pads():
    bx, by = BED_C
    K.jumppad(-900, 760, 0, land=(-950, 1300, BED_Z), apex=BED_Z + 340, name='pad_bed', edges=[(-1000, 1008, BED_Z)])
    K.jumppad(-1350, 760, 0, land=(-1450, 1300, BED_Z), apex=BED_Z + 340, name='pad_bed2', edges=[(-1500, 1008, BED_Z)])
    K.jumppad(-1700, 1500, BED_Z, land=(-1808, 600, WARD_Z), apex=WARD_Z + 240, name='pad_wardrobe',
              ceiling=ZC, edges=[(-1808, 992, WARD_Z)])
    K.jumppad(-176, 1180, 0, land=(-176, 1620, DRESS_Z), apex=DRESS_Z + 320, name='pad_dresser', edges=[(-176, 1376, DRESS_Z)])
    K.jumppad(984, 1000, 0, land=(984, 1600, TOWER_Z), apex=TOWER_Z + 260, name='pad_tower', edges=[(984, 1296, TOWER_Z)])
    K.jumppad(0, -1240, 0, land=(0, -1690, SILL[4]), apex=SILL[4] + 140, name='pad_sill', edges=[(0, SILL[3], SILL[4])])
    K.jumppad(1480, -400, DESK_Z, land=(1930, -150, SHELF_Z), apex=SHELF_Z + 130, name='pad_shelf', ceiling=ZC,
              edges=[(1792, -200, SHELF_Z)])
    K.jumppad(-1440, -1600, 0, land=(-1860, -1600, 480), apex=480 + 200, name='pad_fridge', edges=[(-1664, -1600, 480)])
    K.jumppad(1200, 1000, 0, land=(1680, 1000, DESK_Z), apex=DESK_Z + 240, name='pad_desk', edges=[(1408, 1000, DESK_Z)])


def items():
    K.weapon('imperius', -1808, 260, WARD_Z, marker='purple')
    K.weapon('betty', -1150, 1500, BED_Z, marker='black')
    K.weapon('balloony', 1930, 700, SHELF_Z, marker='orange')
    K.weapon('pumper', 1520, 1180, DESK_Z, marker='green')
    K.weapon('splasher', -220, 1560, DRESS_Z, marker='blue')
    K.weapon('boaster', 960, 1430, 16, marker='orange')
    K.weapon('bubbleg', 140, -40, 4, marker='green')
    ammo = {'imperius': [(-1350, 1640, BED_Z), (-700, 1560, 0), (300, -1700, SILL[4])],
            'betty': [(-1500, 1150, BED_Z), (1700, 100, 0), (-1856, -1600, 480), (600, 1500, 0)],
            'balloony': [(1930, 300, SHELF_Z), (-500, -1500, 0), (984, 1700, TOWER_Z)],
            'pumper': [(1560, -150, DESK_Z), (-1700, 330, 16), (-1100, 300, 0), (300, 1250, 0)],
            'splasher': [(-40, 1680, DRESS_Z), (1300, -1550, 0), (-400, 500, 4)],
            'boaster': [(1030, 1400, 16), (-600, 200, 4), (650, -1300, 0)],
            'bubbleg': [(-650, -350, 4), (500, 250, 4), (-1450, -1350, 0), (1150, 0, 4)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    K.ammo('nipper', 0, 1000, 0); K.ammo('nipper', 1300, 850, 0); K.ammo('nipper', -1000, -1500, 0)
    K.item('item_armor_padshield', 984, 1450, TOWER_Z)
    K.item('item_armor_shard', -1350, 1250, BED_Z); K.item('item_armor_shard', 1720, 900, DESK_Z)
    K.item('item_speedy', -300, -1700, SILL[4])
    K.item('holdable_floater', -1720, 720, 16)
    K.item('item_jumper', -560, 1200, BED_Z)
    K.station(-760, 1250, 0, ang=180)
    for (x, y, z, a) in ((-600, -1450, 0, 90), (650, -1500, 0, 90), (1250, -300, 0, 180), (-1300, -250, 0, 0),
                         (-250, 650, 4, 270), (650, 450, 4, 180), (300, 1300, 0, 270), (-1150, 1150, 0, 270),
                         (1700, 600, DESK_Z, 180), (-850, 1450, BED_Z, 180), (-1450, -1250, 0, 45), (1000, -1050, 0, 135),
                         (-700, 150, 4, 0), (1550, 1650, 0, 200)):
        K.spawn(x, y, z, a)


def secret():
    """walk into the static on the CRT under the bed -> the 8-bit vault"""
    K.secret((-1388, 1520, 32), (-1092, 1640, 290), dest=(0, -200, VAULT_Z), angle=90, name='crt', approach='s')
    K.keep_clear(-1400, 1300, -1080, 1432, 0)


def lights_sounds():
    K.light(0, 0, ZC - 120, 1100, '1 0.95 0.9')
    K.light_grid(X0, Y0, X1, Y1, 1450, 768, 5400, color='0.8 0.75 1')
    K.light(-1808, 250, 1880, 600, '0.9 0.85 1'); K.light(-1808, 750, 1880, 600, '0.9 0.85 1')              # over the wardrobe top
    K.light(1700, 440, 1000, 600, '0.5 0.7 1')                # monitor glow
    K.light(1550, 440, 760, 350, '0.6 0.8 1')
    for y in (-200, 450, 1100):                                # RGB glow under the desk
        K.light(1600, y, 320, 750, '0.75 0.5 1')
    K.light(1301, 1486, 300, 300, '0.7 0.7 1')
    K.light(1744, -1100, 950, 700, '0.7 0.75 1')              # over the monitor-box ramp
    for x in (-1800, -1400, -1000, -650):                     # fairy lights in the den
        K.light(x, 1250, 450, 800, '1 0.8 0.55')
    K.light(-1240, 1300, 200, 200, '0.8 0.8 1')
    K.light(-1850, 1500, 400, 600, '1 0.8 0.55')               # den corner               # TV static
    K.light(-1800, 300, 900, 260, '1 0.95 0.85')              # inside the wardrobe
    K.light(984, 1536, 250, 220, '0.6 0.4 1')                 # inside the tower
    K.light(-1700, -1600, 300, 200, '0.6 0.8 1')              # fridge glow
    K.light(0, -1650, 1300, 300, '0.55 0.6 1')                # moonlight at the window
    K.speaker(984, 1536, 200, 'machine/fan_pc')
    K.speaker(-1240, 1500, 160, 'machine/electric_sizzle')
    K.speaker(-176, 1584, 800, 'machine/clock_ticking')
    K.speaker(-1856, -1600, 300, 'machine/freezer')
    K.timer_sound(0, -1700, 1300, 'ambient/police_pass', 'siren', 45, 25)
    K.timer_sound(-1900, -1700, 700, 'misc/door_buzzer', 'pizza', 60, 30)
    K.timer_sound(1700, 440, 1100, 'machine/tv_upstairs', 'stream', 40, 20)
    K.trigger_sound((-1900, 100, WARD_Z), (-1700, 400, WARD_Z + 96), 'human/applause', 'summit', wait=8)


def shader():
    TX.write_shader(arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    TX = DM.textures(K)
    DM.all_models()                    # every MD3/IQM (and its shaders) BEFORE the shader file is written
    shell(); vault(); furniture(); secret(); pads(); clutter(); items(); lights_sounds()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
