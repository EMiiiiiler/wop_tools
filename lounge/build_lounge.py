#!/usr/bin/env python3
"""Couch Lock - World of Padman FFA map generator (map 'wop_padlounge').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_lounge.py

Writes <OUT>/maps/wop_padlounge.map, textures/padlounge/*, models/padlounge/*, scripts/padlounge.shader and
scripts/wop_padlounge.arena.

A stoner's living room at Padman scale (~8u per cm, catalog models at their native scale 1.0), late at night, the air
hazy with smoke (one fog volume fills the room). x east, y north, floor z 0, ceiling z 2048.

  couch          north wall: olive corduroy three-seater (seat 360, arms 560, back 760). A falsa blanket draped off the
                 seat is a ramp up; a pad on the seat and one on the side table reach the back (Splasher). Under the couch
                 is a 64u crawl space (crouch) with the Boaster, lost lighters and socks, and a mouse hole in the skirting
                 board: the secret teleport up to the stash shelf above the couch (Pad Power, Killer Ducks).
  coffee table   centre, on a 70s shag rug: the giant glass bong (MD3), ashtray with a smouldering joint, grinder,
                 rolling papers, lighter, Bubble G. A skateboard leaning on the table edge is the ramp up; a pad too.
  TV stand       west wall: three open compartments (health station, Pad shield, console), the flat screen showing a
                 psychedelic visualiser, floor speakers either side, "chill out" neon above. Pad to the top (Splasher).
  bookshelf      east wall, 1600 tall: walk-in bottom shelf (records, green lava lamp), a pad into the second shelf
                 (Jumper, stash jar), a pad to the very top (Imperius).
  grow tent      south-west corner: black canvas tent with the door unzipped, mylar inside, three cannabis plants under a
                 purple LED panel, carbon filter (Pumper inside). Pad to the roof (Betty).
  mini fridge    north-east: door wide open, walk inside (Speedy, munchies on the glass shelf), pad to the top.
  props          big potted cannabis plant (MD3), purple bean bag (MD3), lava lamps (MD3, wax rises and sinks),
                 crisp bags (MD3), pizza box stairs to the side table, pizza stacks, tie-dye curtains, tapestry and
                 black-light posters, fairy lights round the walls, floor lamp, window onto the night city.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import lounge_textures as TX
import lounge_models as LM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padlounge'
T = lambda n: 'padlounge/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floor': (1, 1), 'rug': (1, 1), 'wall': (1, 1), 'ceiling': (1, 1), 'baseboard': (1, 1), 'dust': (1, 1), 'couch': (0.75, 0.75),
             'couch_h': (0.75, 0.75), 'couch_dark': (1, 1), 'blanket': (1, 1), 'walnut': (1, 1), 'pine': (1, 1), 'black': (1, 1),
             'tent_out': (1, 1), 'mylar': (1, 1), 'chrome': (1, 1), 'filter': (1, 1), 'pizza_side': (0.5, 0.5), 'fridge': (1, 1),
             'fridge_in': (1, 1), 'window_frame': (1, 1), 'rubber': (1, 1), 'book_top': (1, 1), 'duct': (1, 1), 'cable': (1, 1),
             'lampshade': (1, 1), 'wheel': (0.5, 0.5), 'leather': (1, 1), 'crate': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '16', '_color': '1 0.9 0.8', 'gridsize': '96 96 128', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
XW, YN, YS, ZC = 2048, 1792, -1792, 2048
RUG = (-1088, -560, 1088, 1088, 8)                 # x0, y0, x1, y1, top
# couch
CX, CY0 = 1088, 1088                                # outer x +-CX, front y CY0 (back against the north wall)
SEAT, ARM, BACK = 360, 560, 760
CLEAR = 64                                          # crawl space under the couch (crouch only)
ARM_W, BACK_Y = 200, 1592
SEAT_DEPTH_Y = 1448                                 # back cushions lean forward to here
SHELF = (-720, 1472, 720, YN, 1328, 1360)           # secret stash shelf above the couch
# coffee table
TBL = (-480, 160, 480, 640, 360)
BONG = (80, 430)
# TV stand
TVS = (-XW, -576, -1664, 576, 400)
TV_X = -1924                                        # screen face
# bookshelf
BK = (1792, -384, XW, 384)
BK_SH = [(16, 448), (480, 864), (896, 1280), (1312, 1568)]   # compartment floor/ceiling
BK_TOP = 1600
# grow tent
TENT = (-XW, YS, -1088, -960, 1280)
TDOOR = (-1520, -1232, 960)                        # door y range in the east wall, opening height
# mini fridge
FR = (1376, 1312, 1856, YN, 704)
# side table (NW) + pizza stairs
SIDE = (-1408, 1472, -1088, YN, 320)
WIN = (-560, 560, 640, 1440)                        # south wall window x0, x1, z0, z1
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """(x,y) = where the model's bounding-box centre should land"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, round_n=0):
    """mdl_c + a weapon-clip box (or n-gon for round things) around the model so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    z1 = oz + b['max'][2] * scale
    if round_n:
        r = (b['max'][0] - b['min'][0]) * scale / 2 * (1 - shrink)
        A(cyl(round(x), round(y), round(r), round(zsurf), round(z1 - 4), WCLIP, round_n))
        return e
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - 4)), WCLIP))
    return e


def custom(name, x, y, z, angle=0, lit=True, scale=1.0, **kw):
    """one of our own MD3s (models/padlounge), origin given directly"""
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
    extra.update(kw)
    return M.model(f'models/padlounge/{name}.md3', (round(x), round(y), round(z, 2)), scale=scale, angle=angle, **extra)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n)], tex)


def light(x, y, z, val, color='1 0.85 0.65', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd):
    speaker(x, y, z, noise, loop=False, targetname=name)
    M.ent('func_timer', (round(x), round(y), round(z + 40)), target=name, wait=wait, random=rnd, spawnflags=1)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), floor + 25), angle=ang % 360)
    SPOTS['spawn'].append((x, y, floor))


def hfit(b, x0, y0, x1, y1, tw, th, tex):
    """top face(s) with `tex`: exactly one copy of a tw x th texture over the rectangle (north = texture top)"""
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.7: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def vfit(b, ztop, zbot, th, tw=None, tex=None):
    for f in b.faces:
        if abs(f.n[2]) > 0.1: continue
        if tex and f.tex != tex: continue
        sy = (ztop - zbot) / th
        sx = abs(f.sc[0]) if tw is None else tw
        f.sc = (sx, sy); f.off = (f.off[0], round((ztop / sy) % th, 3))
    return b


def jumppad(x, y, z, land, apex, name, glow=True):
    """pad disc (r 34) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of the flight measured from
    the trigger centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way to `land`."""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38
    lx, ly, lz = land
    lz_o = lz + 24
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - lz_o) / 800)
    f = tu / (tu + td)
    tx, ty = x + (lx - x) * f, y + (ly - y) * f
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    if glow: light(x, y, z + 48, 110, '0.5 1 0.55')


def sprite(x, y, z0, z1, tex, w, ang=0):
    """thin vertical autosprite2 slab (taller than wide), shader on both broad faces"""
    a = math.radians(ang); dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2; nx, ny = -math.sin(a), math.cos(a)
    q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx * 2, y + dy + ny * 2), (x - dx + nx * 2, y - dy + ny * 2)]
    def tf(n, nx=nx, ny=ny):
        return T(tex) if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS
    b = hull([(px, py, zz) for (px, py) in q for zz in (z0, z1)], tf, round_pts=False)
    for f in b.faces:
        if f.tex == T(tex): f.sc = (w / 128, (z1 - z0) / 256); f.off = (0, 0)
    return b


def poster(mn, mx, tex, tw, th, facing):
    return sign_box(mn, mx, T(tex), tw, th, back=T('black'), facing=facing)


def deco(mn, mx, tex):
    """nonsolid decoration box (cables, little bits that should not block players)"""
    d = {'side': NODRAW_NS}
    if isinstance(tex, dict): d.update(tex)
    else: d = {'side': tex, 'top': tex, 'bot': tex}
    b = box(mn, mx, d)
    return b


# =================================================================================================== room shell
def shell():
    W = 16
    A(box((-XW - W, YS - W, -W), (XW + W, YN + W, 0), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((-XW - W, YS - W, ZC), (XW + W, YN + W, ZC + W), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((-XW - W, YN, 0), (XW + W, YN + W, ZC), {'side': CAULK, 's': T('wall')}, detail=False))
    A(box((-XW - W, YS, 0), (-XW, YN, ZC), {'side': CAULK, 'e': T('wall')}, detail=False))
    A(box((XW, YS, 0), (XW + W, YN, ZC), {'side': CAULK, 'w': T('wall')}, detail=False))
    # south wall with the window opening + sky pocket behind it
    x0, x1, z0, z1 = WIN
    sw = {'side': CAULK, 'n': T('wall')}
    for (xa, xb, za, zb) in ((-XW - W, XW + W, 0, z0), (-XW - W, XW + W, z1, ZC), (-XW - W, x0, z0, z1), (x1, XW + W, z0, z1)):
        A(box((xa, YS - W, za), (xb, YS, zb), sw, detail=False))
    SKY = T('sky')
    A(box((x0 - 160, YS - 416, z0 - 160), (x1 + 160, YS - 400, z1 + 160), SKY, detail=False))
    A(box((x0 - 160, YS - 400, z0 - 160), (x0 - 144, YS - W, z1 + 160), SKY, detail=False))
    A(box((x1 + 144, YS - 400, z0 - 160), (x1 + 160, YS - W, z1 + 160), SKY, detail=False))
    A(box((x0 - 144, YS - 400, z0 - 160), (x1 + 144, YS - W, z0 - 144), SKY, detail=False))
    A(box((x0 - 144, YS - 400, z1 + 144), (x1 + 144, YS - W, z1 + 160), SKY, detail=False))
    # window: frame, mullion, transom, glass, sill sticking into the room
    fr = T('window_frame')
    A(box((x0 - 16, YS, z0 - 16), (x1 + 16, YS + 24, z0), fr))
    A(box((x0, YS - W, z1 - 16), (x1, YS, z1), fr))
    A(box((x0, YS - W, z0), (x0 + 16, YS, z1 - 16), fr)); A(box((x1 - 16, YS - W, z0), (x1, YS, z1 - 16), fr))
    xm = (x0 + x1) // 2
    A(box((xm - 8, YS - W, z0), (xm + 8, YS - 4, z1 - 16), fr))
    zm = (z0 + z1) // 2
    for (xa, xb) in ((x0 + 16, xm - 8), (xm + 8, x1 - 16)):
        A(box((xa, YS - W, zm - 8), (xb, YS - 4, zm + 8), fr))
        for (za, zb) in ((z0, zm - 8), (zm + 8, z1 - 16)):
            A(box((xa, YS - 12, za), (xb, YS - 8, zb), T('glass')))
    # curtain rod + tie-dye curtains hanging either side of the window (floor length)
    A(deco((x0 - 320, YS + 24, 1640), (x1 + 320, YS + 40, 1656), T('chrome_ns')))
    for (xa, xb) in ((x0 - 288, x0 - 64), (x1 + 64, x1 + 288)):
        b = box((xa, YS, 0), (xb, YS + 32, 1632), {'n': T('curtain'), 'side': T('curtain'), 'top': T('curtain'), 'bot': CAULK})
        for f in b.faces:
            if f.tex == T('curtain') and abs(f.n[2]) < 0.1:
                if abs(f.n[1]) > 0.9: fit_face(f, xa, xb, 0, 1632, 256, 1024)
                else: fit_face(f, YS, YS + 32, 0, 1632, 256, 1024)
        A(b)


# =================================================================================================== rug + couch
def rug():
    x0, y0, x1, y1, top = RUG
    b = box((x0, y0, 0), (x1, y1, top), {'top': T('rug'), 'side': T('rug'), 'bot': CAULK})
    hfit(b, x0, y0, x1, y1, 512, 512, T('rug'))
    for f in b.faces:
        if f.tex == T('rug') and f.n[2] > 0.9: f.sc = (f.sc[0] / 2, f.sc[1] / 2)     # 2 x 2 repeats of the pattern
    A(b)


def couch():
    cz = T('couch'); ch = T('couch_h')
    # legs (dark wood) - the only thing under the couch body
    for x in (-1064, -24, 1016):
        for y in (1112, 1720):
            A(box((x, y, 0), (x + 48, y + 48, CLEAR), T('walnut')))
    # body / base frame: z CLEAR..240, the underside dark
    A(box((-CX, CY0, CLEAR), (CX, YN, 240), {'side': ch, 'bot': T('couch_dark'), 'top': T('couch_dark')}))
    # arms with a rounded front-top edge
    for s in (-1, 1):
        xa, xb = sorted((s * CX, s * (CX - ARM_W)))
        A(hull([(x, y, z) for x in (xa, xb) for (y, z) in ((CY0, 240), (CY0, ARM - 60), (CY0 + 24, ARM - 18), (CY0 + 60, ARM),
                                                           (YN, ARM), (YN, 240))], cz))
    # back with a rounded top
    bx = CX - ARM_W
    A(hull([(x, y, z) for x in (-bx, bx) for (y, z) in ((BACK_Y, 240), (BACK_Y, BACK - 40), (BACK_Y + 14, BACK - 12), (BACK_Y + 40, BACK),
                                                        (YN, BACK), (YN, 240))], cz))
    # seat cushions: three, 8u apart, rounded front edge, fitted cushion texture on top
    for (xa, xb) in ((-bx, -304), (-296, 296), (304, bx)):
        b = hull([(x, y, z) for x in (xa, xb) for (y, z) in ((CY0, 240), (CY0, SEAT - 26), (CY0 + 10, SEAT - 6), (CY0 + 28, SEAT),
                                                             (BACK_Y, SEAT), (BACK_Y, 240))], {'top': T('cushion'), 'side': ch})
        hfit(b, xa, CY0, xb, BACK_Y, 512, 256, T('cushion')); A(b)
        # back cushion leaning against the back
        A(hull([(x, y, z) for x in (xa + 6, xb - 6) for (y, z) in ((SEAT_DEPTH_Y, SEAT), (SEAT_DEPTH_Y + 30, SEAT + 230),
                                                                   (SEAT_DEPTH_Y + 70, SEAT + 320), (BACK_Y, SEAT + 340), (BACK_Y, SEAT))], cz))
    # falsa blanket draped from the east seat cushion down to the rug: the ramp up (37 deg)
    bxa, bxb, by0 = 520, 840, 620
    A(hull([(x, y, z) for x in (bxa, bxb) for (y, z) in ((by0, RUG[4]), (CY0, RUG[4]), (CY0, SEAT + 8))], T('blanket')))
    A(box((bxa, CY0, SEAT), (bxb, 1320, SEAT + 8), T('blanket')))
    # throw pillows (cover on the seat), leaning in the west corner
    A(hull([(x, y, z) for (x, y) in ((-880, 1300), (-860, 1440), (-700, 1440), (-720, 1300)) for z in (SEAT, SEAT + 40)] +
           [(-870, 1350, SEAT + 170), (-860, 1440, SEAT + 180), (-780, 1440, SEAT + 170)], T('blanket')))
    # loot + decoration on the couch
    weapon('balloony', 0, 1712, BACK, 'green')
    item('ammo_balloony', 640, 1400, SEAT + 8)
    item('ammo_pumper', 420, 1250, SEAT)
    item('holdable_floater', -988, 1400, ARM)
    item('ammo_splasher', 988, 1500, ARM)
    custom('chips', -500, 1270, SEAT, angle=90, scale=0.45)
    mdl_c('pad_radio_car/radio_control_fl.md3', 200, 1180, SEAT, 1.0, 200)
    mdl_c('pad_phones/pad_padika2.md3', 1000, 1250, ARM, 1.0, 80)
    jumppad(150, 960, RUG[4], (-150, 1712, BACK), BACK + 220, 'couch_back')
    # under the couch: dust, the Boaster, socks, a lost lighter, the mouse hole (secret)
    A(box((-1000, 1176, 0), (1000, 1700, 1), T('dust')))
    weapon('boaster', 260, 1460, 1, 'orange')
    item('ammo_boaster', -420, 1560, 1)
    item('ammo_imperius', 760, 1320, 1)
    mdl_c('pad_clothes/sock_grey.md3', -820, 1300, 1, 1.0, 30)
    mdl_c('pad_clothes/sock_grey2.md3', 540, 1640, 1, 1.0, 110)
    mdl_c('pad_objects/pad_fdisk.md3', -150, 1600, 1, 1.0, 20)
    for (bx0, by0, bx1, by1, h) in ((-320, 1240, -80, 1480, 56), (0, 1560, 200, 1700, 48), (480, 1240, 680, 1400, 52)):
        A(box((bx0, by0, 1), (bx1, by1, 1 + h), {'side': T('pizza_side'), 'top': T('pizza_side'), 'bot': CAULK}))
    mdl_c('pad_ddmix/mix/matchbook_closed.md3', 860, 1500, 1, 1.0, 70)
    light(0, 1450, 40, 140, '1 0.8 0.6'); light(-700, 1450, 40, 120, '1 0.8 0.6'); light(700, 1450, 40, 120, '1 0.8 0.6')
    timer_sound(0, 1300, 440, 'sound/world/human/snoring.ogg', 'snore', 70, 30)


def secret():
    """mouse hole in the skirting board behind the crawl space -> the stash shelf above the couch"""
    hx0, hx1 = -760, -664
    b = box((hx0, YN - 2, 1), (hx1, YN, 57), {'s': T('mousehole'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS})
    for f in b.faces:
        if f.tex == T('mousehole'): fit_face(f, hx0, hx1, 1, 57, 128, 128)
    A(b)
    M.ent('trigger_multiple', brushes=[box((hx0 - 40, 1600, 1), (hx1 + 40, 1690, 60), TRIG)], target='secret_snd', wait=6)
    speaker((hx0 + hx1) / 2, 1650, 40, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('trigger_teleport', brushes=[box((hx0 - 10, 1692, 1), (hx1 + 10, 1788, 60), TRIG)], target='stash')
    x0, y0, x1, y1, z0, z1 = SHELF
    A(box((x0, y0, z0), (x1, y1, z1), T('walnut')))
    for x in (-560, 528):                                   # brackets under the shelf
        A(hull([(x, y1, z0 - 160), (x + 32, y1, z0 - 160), (x, y1, z0), (x + 32, y1, z0), (x, y0 + 40, z0), (x + 32, y0 + 40, z0)], T('black')))
    M.ent('misc_teleporter_dest', (-500, 1660, z1 + 24), targetname='stash', angle=0)
    item('item_padpower', 0, 1700, z1)
    item('holdable_killerducks', 300, 1700, z1)
    item('ammo_bubbleg', -560, 1730, z1)
    custom('jar', 600, 1690, z1, angle=20)
    mdl_c('gummybears/ldredbear.md3', -640, 1560, z1, 1.0, 20)
    mdl_c('pad_ddmix/mix/matchbook_padman.md3', 160, 1560, z1, 1.0, 330)
    jumppad(-220, 1600, z1, (-760, 860, RUG[4]), z1 + 160, 'stash_down')
    light(0, 1600, z1 + 220, 260, '1 0.8 0.6')


# =================================================================================================== side table + pizza stairs (NW)
def side_table():
    x0, y0, x1, y1, top = SIDE
    A(box((x0, y0, top - 32), (x1, y1, top), T('walnut')))
    for (lx, ly) in ((x0 + 16, y0 + 16), (x1 - 56, y0 + 16), (x0 + 16, y1 - 56), (x1 - 56, y1 - 56)):
        A(box((lx, ly, 0), (lx + 40, ly + 40, top - 32), T('walnut')))
    custom('lava_purple', -1320, 1690, top, lit=False)
    A(cyl(-1320, 1690, 52, top, top + 330, WCLIP, 12))
    light(-1320, 1690, top + 200, 420, '0.85 0.35 1')
    speaker(-1320, 1690, top + 150, 'sound/world/ambient/slime_bubbling.ogg', volume=0.4)
    mdl_c('pad_cups/pad_cup05.md3', -1180, 1730, top, 1.0, 140)
    item('ammo_splasher', -1340, 1520, top)
    jumppad(-1170, 1540, top, (-760, 1712, BACK), BACK + 220, 'side_back')
    # pizza box stairs climbing north to the side table: each box 288 square, 32 thick, 40 further north than the last
    n = top // 32
    for k in range(n):
        ya = y0 - 288 - 40 * (n - 1 - k) + 0
        b = box((-1400, ya, 32 * k), (-1112, ya + 288, 32 * k + 32), {'top': T('pizza_top'), 'side': T('pizza_side'), 'bot': CAULK})
        hfit(b, -1400, ya, -1112, ya + 288, 512, 512, T('pizza_top'))
        A(b)
    item('ammo_bubbleg', -1550, 1300, 0)


# =================================================================================================== coffee table
def coffee_table():
    x0, y0, x1, y1, top = TBL
    b = box((x0, y0, top - 32), (x1, y1, top), {'top': T('table_top'), 'side': T('walnut'), 'bot': T('walnut')})
    hfit(b, x0, y0, x1, y1, 1024, 512, T('table_top')); A(b)
    for (lx, ly) in ((x0 + 16, y0 + 16), (x1 - 80, y0 + 16), (x0 + 16, y1 - 80), (x1 - 80, y1 - 80)):
        A(box((lx, ly, RUG[4]), (lx + 64, ly + 64, top - 32), T('walnut')))
    # the bong (MD3) + its weapon-clip collision
    bx, by = BONG
    custom('bong', bx, by, top + LM.BONG_OFS, angle=0)
    A(frustum(bx, by, 166, top, 92, top + 256, WCLIP))
    A(frustum(bx, by, 92, top + 256, 74, top + 330, WCLIP))
    A(cyl(bx, by, 74, top + 330, top + 690, WCLIP, 16))
    A(frustum(bx, by, 74, top + 690, 86, top + 716, WCLIP))
    speaker(bx, by, top + 150, 'sound/world/ambient/water_bubble.ogg', loop=False, targetname='bong')
    M.ent('func_timer', (bx, by, top + 900), target='bong', wait=14, random=8, spawnflags=1)
    # smoke curling out of the mouthpiece and off the bowl, the ashtray joint
    A(sprite(bx, by, top + 730, top + 1050, 'smoke', 150))
    A(sprite(bx - 141, by, top + 312, top + 560, 'smoke', 90))
    custom('ashtray', -110, 290, top, angle=200)
    A(sprite(-137, 267, top + 50, top + 300, 'smoke', 80))
    custom('grinder', -380, 520, top, angle=290)
    custom('lighter', -230, 580, top, angle=10)
    # rolling papers pack + TV remote (thin brushes), pipe + matchbook from the catalog
    b = box((150, 200, top), (246, 248, top + 6), {'top': T('papers'), 'side': T('papers'), 'bot': CAULK})
    hfit(b, 150, 200, 246, 248, 256, 128, T('papers')); A(b)
    b = box((330, 520, top), (370, 600, top + 10), {'top': T('remote'), 'side': T('black'), 'bot': CAULK})
    hfit(b, 330, 520, 370, 600, 128, 256, T('remote')); A(b)
    mdl_c('pad_ddmix/padlibrary/pipe.md3', 420, 470, top, 1.0, 0)
    mdl_c('pad_ddmix/mix/matchbook_padman.md3', 420, 230, top, 1.0, 20)
    weapon('bubbleg', 360, 330, top, 'blue')
    light(0, 400, top + 900, 900, '1 0.85 0.65')
    light(bx, by, top + 120, 160, '0.5 1 0.6')
    # skateboard leaning on the south edge: the ramp up (30 deg). Deck + trucks + wheels (decoration under the deck)
    sx0, sx1, ys, zs = -400, -240, -440, RUG[4]
    A(hull([(x, y, z) for x in (sx0, sx1) for (y, z) in ((ys, zs), (y0, top), (y0, top - 14), (ys + 26, zs))],
           {'top': T('skate_grip'), 'bot': T('skate_bottom'), 'side': T('black')}))
    def zb(y): return zs + (y - (ys + 26)) / (y0 - ys - 26) * (top - 14 - zs)
    for yc in (-250, 60):
        zt = math.floor(zb(yc - 22)) - 1
        A(deco((sx0 + 20, yc - 16, zt - 16), (sx1 - 20, yc + 16, zt), T('chrome_ns')))
        for xw in (sx0 - 8, sx1 - 20):
            A(deco((xw, yc - 22, zt - 60), (xw + 28, yc + 22, zt - 16), T('wheel_ns')))
    # under the table: comics, a pizza box, ammo
    b = box((-160, 300, RUG[4]), (160, 500, 240), {'side': T('crate'), 'top': T('records'), 'bot': CAULK})
    hfit(b, -160, 300, 160, 500, 512, 256, T('records')); A(b)
    mdl_c('pad_books/comics/pad_comic1.md3', -340, 420, RUG[4], 1.0, 80)
    item('ammo_pumper', 320, 420, RUG[4])
    item('ammo_splasher', 0, 220, RUG[4])
    jumppad(760, 380, RUG[4], (400, 440, top), top + 200, 'table')


# =================================================================================================== TV stand + speakers (W)
def tv_stand():
    x0, y0, x1, y1, top = TVS
    bl = T('black')
    A(box((x0 + 16, y0, 0), (x1, y1, 16), {'top': T('walnut'), 'side': bl, 'bot': CAULK}))
    A(box((x0, y0, 0), (x0 + 16, y1, top - 48), bl))
    for (ya, yb) in ((y0, y0 + 32), (-208, -176), (176, 208), (y1 - 32, y1)):
        A(box((x0 + 16, ya, 16), (x1, yb, top - 48), {'side': bl, 'top': bl, 'bot': bl, 'e': T('walnut')}))
    A(box((x0, y0, top - 48), (x1, y1, top), {'top': T('walnut'), 'side': T('walnut'), 'bot': bl}))
    # TV: foot, neck, panel; screen face fitted with the visualiser
    A(box((-1990, -200, top), (-1890, 200, top + 12), bl))
    A(box((-1956, -40, top + 12), (-1924, 40, 520), bl))
    b = box((-1972, -560, 520), (TV_X, 560, 1150), {'side': bl, 'e': T('tv_screen')})
    for f in b.faces:
        if f.tex == T('tv_screen'): fit_face(f, -560, 560, 520, 1150, 512, 288)
    A(b)
    light(-1700, 0, 840, 700, '0.55 0.5 1')
    speaker(-1800, 0, 800, 'sound/world/machine/tv_upstairs.ogg', volume=0.6)
    # compartments: N = health station, middle = console, S = Pad shield
    M.ent('station_health', (-1890, 376, 16), angle=0)
    b = box((-2010, -120, 16), (-1850, 120, 80), {'side': bl, 'e': T('console'), 'top': bl, 'bot': CAULK})
    for f in b.faces:
        if f.tex == T('console'): fit_face(f, -120, 120, 16, 80, 512, 128)
    A(b)
    light(-1760, 376, 300, 160, '0.8 0.9 1'); light(-1760, -376, 300, 160, '0.8 0.9 1'); light(-1760, 0, 300, 140, '0.6 0.8 1')
    mdl_c('pad_radio_car/radio_control_fl.md3', -1760, 60, 80 - 64, 1.0, 10)
    item('ammo_betty', -1740, -60, 16)
    item('item_armor_padshield', -1800, -376, 16)
    item('ammo_balloony', -1740, -470, 16)
    mdl_c('pad_books/comics/pad_comic1_upr.md3', -2010, -300, 16, 1.0, 90)
    # top: Balloony in front of the screen, ammo; pad up from the floor
    weapon('splasher', -1770, 360, top, 'orange')
    item('ammo_bubbleg', -1770, -380, top)
    jumppad(-1360, 0, 0, (-1770, 0, top), top + 220, 'tv')
    # floor speakers either side
    for (ya, yb) in ((y1, y1 + 240), (y0 - 240, y0)):
        b = box((x0 + 16, ya, 0), (x0 + 256, yb, 880), {'e': T('speaker'), 'side': T('black'), 'top': T('black'), 'bot': CAULK})
        for f in b.faces:
            if f.tex == T('speaker'): fit_face(f, ya, yb, 0, 880, 256, 1024)
        A(b)
    # neon sign above the TV
    b = poster((-XW, -480, 1290), (-XW + 4, 480, 1530), 'neon', 1024, 256, 'e'); A(b)
    light(-1900, 0, 1410, 500, '1 0.35 0.85')


# =================================================================================================== bookshelf (E)
def bookshelf():
    x0, y0, x1, y1 = BK
    pw = T('pine')
    A(box((x1 - 16, y0, 0), (x1, y1, BK_TOP), {'side': pw, 'w': T('pine')}))
    for (ya, yb) in ((y0, y0 + 32), (y1 - 32, y1)):
        A(box((x0, ya, 0), (x1 - 16, yb, BK_TOP - 32), pw))
    A(box((x0, y0 + 32, 0), (x1 - 16, y1 - 32, 16), pw))
    for (za, zb) in zip([s[1] for s in BK_SH[:-1]], [s[0] for s in BK_SH[1:]]):
        A(box((x0, y0 + 32, za), (x1 - 16, y1 - 32, zb), pw))
    A(box((x0, y0, BK_TOP - 32), (x1 - 16, y1, BK_TOP), pw))
    def books(ya, yb, z, h, tex='books', depth=200):
        b = box((x1 - 16 - depth, ya, z), (x1 - 16, yb, z + h), {'w': T(tex), 'top': T('book_top'), 'side': T('book_top'), 'bot': CAULK})
        for f in b.faces:
            if f.tex == T(tex): fit_face(f, ya, yb, z, z + h, 512, 256)
        A(b)
    # C1 (walk in): records along the south half, green lava lamp in the north half
    books(y0 + 32, -40, 16, 300, 'records', 220)
    custom('lava_green', 1930, 230, 16, lit=False)
    A(cyl(1930, 230, 52, 16, 346, WCLIP, 12))
    light(1880, 230, 220, 380, '0.45 1 0.45')
    speaker(1930, 230, 150, 'sound/world/ambient/slime_bubbling.ogg', volume=0.4)
    item('ammo_betty', 1880, 40, 16)
    # C2 (pad): books north, jar + Jumper
    books(120, y1 - 32, BK_SH[1][0], 300)
    custom('jar', 1930, -250, BK_SH[1][0], angle=60)
    item('item_jumper', 1880, -80, BK_SH[1][0])
    item('ammo_pumper', 1880, 40, BK_SH[1][0])
    jumppad(1440, -120, 0, (1890, -120, BK_SH[1][0]), BK_SH[1][0] + 200, 'shelf2')
    # C3, C4: books, bookend, comics (out of reach, decoration)
    books(y0 + 32, 160, BK_SH[2][0], 320, 'books2')
    mdl_c('pad_ddmix/padlibrary/bookend.md3', 1920, 260, BK_SH[2][0], 1.0, 180)
    books(-120, y1 - 32, BK_SH[3][0], 230)
    mdl_c('gummybears/greenbear.md3', 1920, -240, BK_SH[3][0], 1.0, 160)
    # top: Imperius
    weapon('imperius', 1920, 120, BK_TOP, 'purple')
    item('ammo_imperius', 1920, -220, BK_TOP)
    mdl_c('pad_ddmix/padship/rumbottle2.md3', 1960, -60, BK_TOP, 1.0, 0)
    jumppad(1340, 240, 0, (1910, 200, BK_TOP), BK_TOP + 200, 'shelf_top')
    light(1700, 0, 1500, 600, '1 0.85 0.65'); light(1880, 0, 700, 260, '1 0.85 0.65')


# =================================================================================================== grow tent (SW)
def grow_tent():
    x0, y0, x1, y1, top = TENT
    out_, in_ = T('tent_out'), T('mylar')
    dy0, dy1, dz = TDOOR
    W = 8
    A(box((x0 + W, y0 + W, 0), (x1 - W, y1 - W, 8), {'top': T('black'), 'side': T('black'), 'bot': CAULK}))
    # walls: west and south against the room walls, north, east with the door
    A(box((x0, y0, 0), (x0 + W, y1, top - 16), {'side': out_, 'e': in_}))
    A(box((x0 + W, y0, 0), (x1, y0 + W, top - 16), {'side': out_, 'n': in_}))
    A(box((x0 + W, y1 - W, 0), (x1, y1, top - 16), {'side': out_, 's': in_}))
    for (ya, yb, za, zb) in ((y0 + W, dy0, 0, top - 16), (dy1, y1 - W, 0, top - 16), (dy0, dy1, dz, top - 16)):
        A(box((x1 - W, ya, za), (x1, yb, zb), {'side': out_, 'w': in_}))
    A(box((x0, y0, top - 16), (x1, y1, top), {'top': out_, 'side': out_, 'bot': in_}))
    # zipper trim round the door + rolled-up flap over the opening (outside)
    b = box((x1, dy0 - 24, 0), (x1 + 4, dy0, dz), {'e': T('tent_door'), 'side': out_})
    A(b); A(box((x1, dy1, 0), (x1 + 4, dy1 + 24, dz), {'e': T('tent_door'), 'side': out_}))
    A(hull([(x1 + 4 + 28 + 28 * math.cos(a), y, dz + 28 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False) for y in (dy0 - 24, dy1 + 24)],
           out_))
    # corner poles (outside corner at the room side)
    A(box((x1, y1, 0), (x1 + 24, y1 + 24, top), T('chrome')))
    # LED panel hanging from the roof, cables, carbon filter + duct
    A(box((-1900, -1700, 1000), (-1236, -1052, 1028), {'bot': T('led'), 'side': T('black'), 'top': T('black')}))
    for (cx, cy) in ((-1880, -1680), (-1256, -1680), (-1880, -1072), (-1256, -1072)):
        A(deco((cx - 2, cy - 2, 1028), (cx + 2, cy + 2, top - 16), T('cable')))
    A(cyl(-1164, -1720, 64, 860, 1180, {'side': T('filter'), 'top': T('chrome'), 'bot': T('chrome')}, 16))
    A(cyl(-1164, -1720, 30, 1180, top - 16, T('duct'), 12))
    light(-1568, -1376, 900, 800, '1 0.4 0.9'); light(-1568, -1376, 420, 380, '1 0.45 0.9')
    speaker(-1164, -1720, 1000, 'sound/world/machine/ventilation.ogg', volume=0.5)
    # three plants in pots (MD3, pot collision only)
    pr = 0.16 * 620; ph = 0.25 * 620
    for (px, py, ang) in ((-1820, -1560, 0), (-1820, -1190, 120), (-1440, -1600, 240)):
        custom('plant_small', px, py, 8 + LM.PLANT_SMALL_OFS, angle=ang)
        A(cyl(px, py, round(pr), 8, round(8 + ph), WCLIP, 16))
    weapon('pumper', -1420, -1230, 8, 'green')
    item('ammo_boaster', -1640, -1380, 8)
    item('ammo_betty', -1300, -1500, 8)
    # roof: Betty, pad up from outside the door
    weapon('betty', -1600, -1376, top, 'black')
    item('ammo_betty', -1300, -1080, top)
    item('item_armor_shard', -1900, -1700, top)
    jumppad(-760, -1376, 0, (-1450, -1376, top), top + 320, 'tent_roof')
    light(-1568, -1376, top + 300, 500, '1 0.85 0.65')


# =================================================================================================== mini fridge (NE)
def mini_fridge():
    x0, y0, x1, y1, top = FR
    fw, fi = T('fridge'), T('fridge_in')
    A(box((x0, y0, 0), (x1, y1 - 32, 16), {'top': fi, 'side': fw, 'bot': CAULK}))
    A(box((x0, y0, 16), (x0 + 32, y1 - 32, top - 32), {'side': fw, 'e': fi}))
    A(box((x1 - 32, y0, 16), (x1, y1 - 32, top - 32), {'side': fw, 'w': fi}))
    A(box((x0, y1 - 32, 0), (x1, y1, top - 32), {'side': fw, 's': fi}))
    A(box((x0, y0, top - 32), (x1, y1, top), {'top': fw, 'side': fw, 'bot': fi}))
    A(box((x0 + 160, y1 - 160, top - 36), (x1 - 160, y1 - 96, top - 32), {'bot': T('fridge_light'), 'side': fi, 'top': CAULK}))
    # glass shelf at the back with munchies on it
    A(box((x0 + 32, y1 - 200, 336), (x1 - 32, y1 - 32, 344), T('fridge_in')))
    mdl_c('pad_tins/pad_coke.md3', 1480, 1680, 344, 1.0, 0)
    mdl_c('pad_tins/pad_pupsi.md3', 1580, 1690, 344, 1.0, 30)
    mdl_c('pad_ddmix/diner/muffin_choco.md3', 1720, 1680, 344, 1.0, 0)
    mdl_c('pad_cake/pad_cakesliceup.md3', 1640, 1700, 16, 1.0, 0)
    mdl_c('pad_ddmix/diner/muffin_blueberry.md3', 1460, 1690, 16, 1.0, 0)
    light(1616, 1500, 500, 260, '0.85 0.95 1')
    speaker(1616, 1600, 300, 'sound/world/machine/freezer.ogg', volume=0.5)
    item('item_speedy', 1616, 1430, 16)
    item('ammo_boaster', 1500, 1560, 16)
    item('ammo_imperius', 1730, 1430, 16)
    # door standing wide open (hinged at the west front corner): inside face with door shelves
    A(box((x0 - 32, y0 - 480, 16), (x0, y0, top - 8), {'side': fw, 'w': fi, 'top': fw}))
    for zz in (200, 420):
        A(box((x0 - 96, y0 - 460, zz), (x0 - 32, y0 - 20, zz + 12), fi))
        A(box((x0 - 96, y0 - 460, zz + 12), (x0 - 88, y0 - 20, zz + 60), fi))
    mdl_c('pad_condiments/pad_ketchup.md3', x0 - 62, y0 - 380, 212, 1.0, 0)
    mdl_c('pad_condiments/pad_mustard.md3', x0 - 62, y0 - 300, 212, 1.0, 0)
    mdl_c('pad_tins/pad_milk_s.md3', x0 - 64, y0 - 120, 432, 1.0, 0)
    # top: pad up, loot, bottles
    item('ammo_pumper', 1560, 1600, top)
    item('item_armor_shard', 1760, 1480, top)
    mdl_c('pad_ddmix/padship/rumbottle1.md3', 1440, 1720, top, 1.0, 0)
    jumppad(1616, 1060, 0, (1640, 1560, top), top + 200, 'fridge')
    # floor lamp between the couch arm and the fridge
    lx, ly = 1232, 1560
    A(cyl(lx, ly, 90, 0, 16, T('chrome'), 16))
    A(cyl(lx, ly, 12, 16, 1300, T('chrome'), 8))
    sh = hull([(x, y, 1300) for (x, y) in ngon(lx, ly, 190, 16)] + [(x, y, 1560) for (x, y) in ngon(lx, ly, 130, 16)], T('lampshade'))
    A(sh)
    light(lx, ly, 1240, 1600, '1 0.8 0.55'); light(lx, ly, 1640, 500, '1 0.8 0.55')


# =================================================================================================== props round the room
def props():
    # big potted cannabis plant (SE corner) + its pot collision
    px, py = 1480, -1360
    custom('plant_big', px, py, LM.PLANT_OFS, angle=30)
    A(cyl(px, py, round(0.16 * 880), 0, round(0.25 * 880), WCLIP, 16))
    light(px, py, 1300, 500, '0.8 1 0.7')
    # purple bean bag under the window
    custom('beanbag', 250, -1270, 0, angle=90)
    A(cyl(250, -1270, 330, 0, 290, WCLIP, 16))
    item('ammo_boaster', 250, -800, 16)
    M.ent('station_health', (720, -1480, 0), angle=90)
    mdl_c('gummybears/ldyellowbear.md3', 760, -1560, 0, 1.0, 200)
    # crisp bags + spills on the floor (cover)
    for (cx, cy, cz, ang) in ((-800, 250, RUG[4], 80), (-700, -1000, 0, 15)):
        custom('chips', cx, cy, cz, angle=ang)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        A(hull([(cx + c * ca - d * sa, cy + c * sa + d * ca, z) for (c, d) in ((-330, -200), (330, -200), (330, 200), (-330, 200))
                for z in (cz, cz + 108)], WCLIP))
    custom('crisps', 1000, -1150, 0, angle=10, lit=False)
    # pizza box stacks (cover) + an open box
    for (cx, cy, n) in ((880, -760, 3), (-400, -1640, 2)):
        for k in range(n):
            ox = 18 * ((k * 5) % 3 - 1)
            b = box((cx - 144 + ox, cy - 144, 32 * k), (cx + 144 + ox, cy + 144, 32 * k + 32), {'top': T('pizza_top'), 'side': T('pizza_side'), 'bot': CAULK})
            hfit(b, cx - 144 + ox, cy - 144, cx + 144 + ox, cy + 144, 512, 512, T('pizza_top'))
            A(b)
    ox, oy = 250, -760                                     # open box: base with the pizza, lid standing up at the back
    b = box((ox - 144, oy - 144, 0), (ox + 144, oy + 144, 16), {'top': T('pizza_in'), 'side': T('pizza_side'), 'bot': CAULK})
    hfit(b, ox - 144, oy - 144, ox + 144, oy + 144, 512, 512, T('pizza_in')); A(b)
    b = box((ox - 144, oy + 144, 0), (ox + 144, oy + 160, 288), {'s': T('pizza_side'), 'n': T('pizza_top'), 'side': T('pizza_side')})
    for f in b.faces:
        if f.tex == T('pizza_top'): fit_face(f, ox - 144, ox + 144, 0, 288, 512, 512)
    A(b)
    item('ammo_nipper', 250, -420, RUG[4])
    item('ammo_nipper', -360, -1350, 0)
    item('ammo_nipper', 1700, 700, 0)
    item('ammo_balloony', 1300, -900, 0)
    item('item_armor_shard', -400, -1460, 0)
    item('item_armor_shard', 440, 900, RUG[4])
    item('ammo_pumper', 1200, 800, 0)
    item('ammo_bubbleg', 1600, -500, 0)
    # catalog clutter: RC car parked by the bookshelf, crushed cans, ball, trash bags by the fridge, comics
    mdl_c('pad_nascars/padcar_orange_rc.md3', 1500, -760, 0, 1.0, 100)
    A(box((1500 - 190, -760 - 80, 0), (1500 + 190, -760 + 80, 100), WCLIP))
    mdl_c('pad_tins/pad_coke_cr.md3', -620, -980, 0, 1.0, 20)
    mdl_c('pad_tins/pad_pupsi_cr.md3', 440, 780, RUG[4], 1.0, 200)
    mdl_c('pad_tins/pad_coke_sd.md3', -980, 300, RUG[4], 1.0, 70)
    mdl_c('pad_ball/pad_soccerball.md3', 1900, -1650, 0, 1.0, 0)
    mdl_c('pad_ddmix/trashcan/garbage_bag_group.md3', 1950, 1050, 0, 1.0, 180)
    mdl_c('pad_ddmix/trashcan/garbage_bag_lying.md3', 1900, 880, 0, 1.0, 120)
    mdl_c('pad_books/comics/pad_comic1.md3', -1200, -300, 0, 1.0, 30)
    mdl_c('pad_ddmix/padship/rumbottle1.md3', -1000, -1500, 0, 1.0, 0)
    mdl_c('pad_cups/pad_cup01_side.md3', 1150, 300, 0, 1.0, 40)


def floor_blockers():
    # hookah on the floor between the TV and the tent (MD3 + weapon-clip base and stem), smoke over the coals
    hx, hy = -1300, -600
    custom('hookah', hx, hy, LM.HOOKAH_OFS, angle=90)
    A(frustum(hx, hy, 112, 0, 116, 120, WCLIP)); A(frustum(hx, hy, 116, 120, 40, 240, WCLIP))
    A(cyl(hx, hy, 30, 240, 400, WCLIP, 12)); A(cyl(hx, hy, 106, 400, 436, WCLIP, 16)); A(cyl(hx, hy, 30, 436, 640, WCLIP, 12))
    A(sprite(hx, hy, 660, 900, 'smoke', 90))
    light(hx, hy, 700, 220, '1 0.5 0.2')
    speaker(hx, hy, 150, 'sound/world/ambient/water_bubbling.ogg', volume=0.3)
    # subwoofer (gummy bear on top)
    b = box((-310, -900, 0), (10, -580, 320), {'n': T('subwoofer'), 'side': T('black'), 'top': T('black'), 'bot': CAULK})
    for f in b.faces:
        if f.tex == T('subwoofer'): fit_face(f, -310, 10, 0, 320, 512, 512)
    A(b)
    mdl_c('gummybears/ldgreenbear.md3', -150, -740, 320, 1.0, 30)
    # leather pouf on the rug
    A(cyl(850, -250, 170, RUG[4], 300, {'side': T('leather'), 'top': T('leather'), 'bot': CAULK}, 16))
    item('ammo_bubbleg', 640, -480, RUG[4])
    # second (smaller) floor cushion between the couch and the table
    A(cyl(-250, 870, 130, RUG[4], 220, {'side': T('leather'), 'top': T('leather'), 'bot': CAULK}, 16))
    # laundry basket with a hoodie spilling out
    A(cyl(-700, -420, 130, RUG[4], 250, {'side': T('crate'), 'top': T('blanket'), 'bot': CAULK}, 12))
    # guitar amp by the bookshelf
    b = box((1150, -580, 0), (1350, -420, 280), {'w': T('subwoofer'), 'side': T('black'), 'top': T('black'), 'bot': CAULK})
    for f in b.faces:
        if f.tex == T('subwoofer'): fit_face(f, -580, -420, 0, 280, 512, 512)
    A(b)
    mdl_c('pad_cups/pad_cup02.md3', 1250, -500, 280, 1.0, 60)
    # milk crates of records: one on the rug south of the table, a stack of two by the fridge
    for (x0, y0, x1, y1, z0, n) in ((40, -330, 320, -130, RUG[4], 1), (1180, 520, 1420, 760, 0, 2)):
        for k in range(n):
            za, zb = z0 + 128 * k, z0 + 128 * (k + 1)
            b = box((x0, y0, za), (x1, y1, zb), {'side': T('crate'), 'top': T('records'), 'bot': CAULK})
            hfit(b, x0, y0, x1, y1, 512, 256, T('records')); A(b)
    # a giant rubber duck in the north-west corner (catalog, weapon-clip)
    solid_mdl('pad_ducks/pad_duck.md3', -1760, 1180, 0, 1.0, 300)


def posters():
    A(poster((-1980, YN - 4, 760), (-1430, YN, 1310), 'tapestry', 1024, 1024, 's'))
    A(poster((1400, YN - 4, 820), (1780, YN, 1326), 'poster_420', 768, 1024, 's'))
    light(1590, 1650, 1080, 300, '0.7 0.3 1')
    A(poster((XW - 4, -1160, 700), (XW, -780, 1206), 'poster_mush', 768, 1024, 'w'))


def fairy_lights():
    """a string of coloured bulbs round the top of the walls (nonsolid, glowing, gently pulsing)"""
    cols = ['bulb_r', 'bulb_g', 'bulb_b', 'bulb_y', 'bulb_p']
    k = 0
    runs = [((-XW + 64, YN - 8), (XW - 64, YN - 8), 'x'), ((-XW + 8, -1700), (-XW + 8, 1700), 'y'), ((XW - 8, -1700), (XW - 8, 1700), 'y'),
            ((-XW + 64, YS + 8), (WIN[0] - 360, YS + 8), 'x'), ((WIN[1] + 360, YS + 8), (XW - 64, YS + 8), 'x')]
    for (a, b, ax) in runs:
        L = abs((b[0] - a[0]) if ax == 'x' else (b[1] - a[1]))
        n = int(L // 160)
        for i in range(n + 1):
            t = i / max(n, 1)
            x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            z = 1880 - 40 * abs(math.sin(i * math.pi / 2))
            A(deco((round(x) - 8, round(y) - 8, round(z) - 22), (round(x) + 8, round(y) + 8, round(z)), T(cols[k % 5])))
            k += 1


def lights_and_sound():
    for (x, y) in ((-1200, -900), (0, -900), (1200, -900), (-1200, 250), (1200, 250), (0, -150), (-600, 1000), (600, 1000)):
        light(x, y, 950, 1350, '1 0.84 0.62')
    light(0, -1500, 1100, 500, '0.55 0.65 1')         # moonlight through the window
    speaker(0, YS + 60, 1100, 'sound/world/animal/cricket_chirp1.ogg', volume=0.4)
    timer_sound(0, YS + 60, 1000, 'sound/world/ambient/police_pass.ogg', 'police', 75, 40)
    timer_sound(-1500, YS + 80, 900, 'sound/world/animal/dog_bark2.ogg', 'dog', 50, 30)
    timer_sound(1800, YN - 80, 900, 'sound/world/misc/door_buzzer.ogg', 'pizza', 90, 40)


def spawns():
    for (x, y, z, a) in ((-1000, -450, RUG[4], 45), (980, -1000, 0, 135), (-1450, -300, 0, 0), (1200, 120, 0, 180), (0, -320, RUG[4], 90),
                         (480, -450, RUG[4], 135), (-900, 760, RUG[4], 315), (-150, -1440, 0, 60), (1200, 900, 0, 225),
                         (300, 1250, SEAT, 270), (-1600, -1100, 8, 0), (1500, -500, 0, 160), (-1820, 1580, 0, 300)):
        spawn(x, y, z, a)


def fog():
    A(box((-XW, YS, 0), (XW, YN, ZC), T('fog')))


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    shell(); rug(); couch(); secret(); side_table(); coffee_table(); tv_stand(); bookshelf(); grow_tent(); mini_fridge()
    props(); floor_blockers(); posters(); fairy_lights(); lights_and_sound(); spawns(); fog()
    M.ent('info_player_intermission', (-300, -1600, 1300), angles='20 70 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/lounge/build_lounge.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
