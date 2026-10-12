#!/usr/bin/env python3
"""Padman's Playroom - World of Padman map generator (map 'wop_padplayroom').

    OUT=/path/to/out python3 build_playroom.py

Writes <OUT>/maps/wop_padplayroom.map, textures/playroom/*, scripts/playroom.shader, scripts/wop_padplayroom.arena.

A kid's bedroom at Padman scale (about 8u per cm, so catalog models sit at their native scale 1.0).
x east, y north, floor z 0, room x -1792..1792, y -1536..1536, ceiling z 1600.
  NW bed (jump pad up, pillow, under-bed stash)    N nightstand + jump pad up to the desk
  NE desk, PC, chair                              E shelf cabinet + hutch (top shelf = Imperius)
  SE dresser + aquarium (jump pad in, teleporter out, Splasher on the gravel)
  S  window sill with sunbeam, radiator, ruler bridge to the dresser
  SW walk-in wardrobe (Betty on top, pad from the bed)    W mouse hole -> Pad's Hideout (secret)
  centre rug playmat: dollhouse (2 floors + roof deck), brick ziggurat, toy box, ABC blocks, chess, mobile overhead
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import textures

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padplayroom'
T = lambda n: 'playroom/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floor_wood': (2, 2), 'wallpaper': (2, 2), 'dado': (1, 1), 'ceiling': (2, 2), 'duvet': (1, 1), 'mattress': (1, 1),
             'pine': (1, 1), 'birch': (1, 1), 'walnut': (1, 1), 'wood_white': (1, 1), 'wood_mint': (1, 1), 'laminate': (1, 1),
             'dh_clapboard': (0.75, 0.75), 'dh_floor': (1, 1), 'roof_tiles': (1, 1), 'wardrobe': (1, 1), 'track': (0.75, 0.75),
             'track_side': (1, 1), 'radiator': (1, 1), 'sill_marble': (1, 1), 'frame_white': (1, 1), 'plaster_rough': (1, 1),
             'old_boards': (1, 1), 'grass': (4, 4), 'hedge': (2, 2), 'fence': (1, 1), 'pages': (0.5, 0.5), 'cardboard': (1, 1),
             'dust': (1, 1), 'tank_frame': (1, 1), 'gravel': (1, 1), 'water': (1, 1), 'rug_edge': (1, 1), 'beanbag': (1, 1),
             'plastic_black': (1, 1), 'plastic_grey': (1, 1), 'metal_chrome': (1, 1), 'pillow': (1, 1), 'sheet': (1, 1),
             'dh_wall_flower': (0.75, 0.75), 'dh_wall_stripe': (0.75, 0.75), 'dh_trim': (1, 1), 'skirting': (1, 1),
             'dado_rail': (1, 1), 'rubber': (1, 1), 'lampshade': (1, 1), 'star_yellow': (1, 1), 'cheese': (1, 1),
             'brick_red': (1, 1), 'brick_blue': (1, 1), 'brick_yellow': (1, 1), 'brick_green': (1, 1), 'brick_white': (1, 1),
             'brick_red_top': (1, 1), 'brick_blue_top': (1, 1), 'brick_yellow_top': (1, 1), 'brick_green_top': (1, 1),
             'brick_white_top': (1, 1), 'toybox_plain': (1, 1), 'track_support': (1, 1), 'chest': (0.5, 0.5),
             'fabric_red': (1, 1), 'fabric_blue': (1, 1), 'fabric_green': (1, 1), 'fabric_yellow': (1, 1),
             'fabric_denim': (1, 1), 'fabric_orange': (1, 1), 'fabric_stripe': (0.5, 0.5), 'fabric_check': (0.5, 0.5), 'fabric_dots': (0.5, 0.5), 'book_red': (1, 1), 'book_blue': (1, 1), 'book_green': (1, 1),
             'book_yellow': (1, 1), 'book_purple': (1, 1), 'book_orange': (1, 1), 'pc_case': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v
for _b in 'abcdp':
    wopmap.TEXSCALE[T('block_' + _b)] = (1, 1)       # 128px over a 128u block face

CLOCK = os.environ.get('CLOCK', 'md3')          # 'md3' = twin-bell alarm clock model (clock_md3.py), 'brush' = old box clock
PILLOW = os.environ.get('PILLOW', 'md3')        # 'md3' = curved MD3 pillows (pillow_md3.py), 'brush' = old brush pillows
M = Map({'message': "Padman's Playroom", '_ambient': '6', 'gridsize': '96 96 96', '_blocksize': '0'})
A = M.add
RX0, RX1, RY0, RY1, CZ = -1792, 1792, -1536, 1536, 1600
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """misc_model resting on a surface at height zsurf (origin z from the model's real lowest vertex)"""
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p) or next((v for k, v in BOUNDS.items() if k.lower() == p.lower()), None)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """like mdl, but (x,y) is where the model's bounding-box centre should land (several models have off-centre origins)"""
    p = 'models/mapobjects/' + path
    b = BOUNDS[p]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, **kw):
    """mdl_c + a weapon-clip box around the model's rotated bounds (shrunk a little) so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    z0 = zsurf; z1 = oz + b['max'][2] * scale
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(z0)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - 4)), WCLIP))
    return e


def light(x, y, z, val, color='1 0.95 0.85', **kw):
    M.ent('light', (x, y, z), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (x, y, z), **kv)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (x, y, floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (x, y, floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (x, y, floor + 25), angle=ang)
    SPOTS['spawn'].append((x, y, floor))


def clip(mn, mx, tex=CLIP):
    A(box(mn, mx, tex))


JUMPPADS = []


def jumppad(x, y, z, land, apex, name):
    """pad (r 32) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of the flight, measured from
    the trigger's centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way to `land`
    (land = (x, y, floor z)). apex = absolute origin height at the top of the arc."""
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:     # fit the round pad texture on the top face
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38                                      # trigger centre
    lx, ly, lz = land
    lz_o = lz + 24                                   # standing origin at landing
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - lz_o) / 800)
    f = tu / (tu + td)
    tx, ty = x + (lx - x) * f, y + (ly - y) * f
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    light(x, y, z + 48, 90, '1 0.7 0.3')


def drawer_box(mn, mx, face, rows, tex='drawer_mint', body=T('wood_white')):
    """cabinet box whose `face` side ('n','s','e','w') shows `rows` fitted drawer fronts (stacked boxes)"""
    out = []
    h = (mx[2] - mn[2]) / rows
    for r in range(rows):
        z0 = round(mn[2] + h * r); z1 = round(mn[2] + h * (r + 1))
        b = box((mn[0], mn[1], z0), (mx[0], mx[1], z1), body)
        for fc in b.faces:
            v = {'e': (1, 0), 'w': (-1, 0), 'n': (0, 1), 's': (0, -1)}[face]
            if fc.n[0] * v[0] + fc.n[1] * v[1] > 0.99:
                fc.tex = T(tex)
                if face in 'ns': fit_face(fc, mn[0], mx[0], z0, z1, 256, 128)
                else: fit_face(fc, mn[1], mx[1], z0, z1, 256, 128)
        out.append(b)
    A(out)
    return out


def sign(mn, mx, tex, facing, tw, th, back=T('wood_white')):
    A(sign_box(mn, mx, T(tex), tw, th, back=back, facing=facing))


def fit_top(b, x0, y0, x1, y1, tw, th):
    """fit a texture of tw x th px exactly over the rectangle on the brush's top face"""
    for f in b.faces:
        if f.n[2] > 0.9:
            sx = (x1 - x0) / tw; sy = (y1 - y0) / th
            f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def book(x0, y0, x1, y1, z0, z1, col):
    """a lying book: cover on top/bottom, page edges on the sides"""
    return box((x0, y0, z0), (x1, y1, z1), {'top': T('book_' + col), 'bot': T('book_' + col), 'side': T('pages')})


# =================================================================================================== shell
def room_shell():
    W = 32
    def wall_tex(face):
        return {'n': CAULK, 's': CAULK, 'e': CAULK, 'w': CAULK, 'top': CAULK, 'bot': CAULK, face: None}

    def wall(mn, mx, inner, bands=True, outer=CAULK):
        """vertical wall split into skirting (0..48), dado (48..512), rail (512..528), wallpaper (528..ceiling).
        outer: texture for the other faces (the west wall shows its back and hole jambs inside the hideout)"""
        for (za, zb, tex) in ((0, 48, 'skirting'), (48, 512, 'dado'), (512, 528, 'dado_rail'), (528, CZ, 'wallpaper')):
            a, b = max(za, mn[2]), min(zb, mx[2])
            if b <= a: continue
            t = {'side': outer, 'top': CAULK, 'bot': outer if za == mn[2] else CAULK, inner: T(tex)}
            A(box((mn[0], mn[1], a), (mx[0], mx[1], b), t, detail=False))

    # floor + ceiling (structural)
    A(box((RX0 - W, RY0 - W, -16), (RX1 + W, RY1 + W, 0), {'top': T('floor_wood'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((RX0 - W, RY0 - W, CZ), (RX1 + W, RY1 + W, CZ + 16), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    # north + east walls: plain
    wall((RX0 - W, RY1, 0), (RX1 + W, RY1 + W, CZ), 's')
    wall((RX1, RY0, 0), (RX1 + W, RY1, CZ), 'w')
    # west wall with the mouse hole (y -640..-544, z 0..112)
    MH = (-640, -544, 112)
    PL = T('plaster_rough')
    wall((RX0 - W, RY0, 0), (RX0, MH[0], CZ), 'e', outer=PL)
    wall((RX0 - W, MH[1], 0), (RX0, RY1, CZ), 'e', outer=PL)
    wall((RX0 - W, MH[0], MH[2]), (RX0, MH[1], CZ), 'e', outer=PL)
    # arch corners of the mouse hole (detail wedges)
    for (ya, yb, sgn) in ((MH[0], MH[0] + 24, 1), (MH[1] - 24, MH[1], -1)):
        pts = []
        for x in (RX0 - W, RX0):
            if sgn > 0: pts += [(x, ya, MH[2]), (x, yb, MH[2]), (x, ya, MH[2] - 24)]
            else: pts += [(x, ya, MH[2]), (x, yb, MH[2]), (x, yb, MH[2] - 24)]
        A(hull(pts, {'side': T('plaster_rough'), 'e': T('skirting')}))
    # south wall with the window opening x -384..896, z 576..1408; sill board spans the wall depth
    WX0, WX1, WZ0, WZ1 = -384, 896, 576, 1408
    wall((RX0 - W, RY0 - W, 0), (-448, RY0, CZ), 'n')
    wall((960, RY0 - W, 0), (RX1 + W, RY0, CZ), 'n')
    wall((-448, RY0 - W, 0), (960, RY0, 560), 'n')
    wall((-448, RY0 - W, WZ1), (960, RY0, CZ), 'n')
    for (xa, xb) in ((-448, WX0), (WX1, 960)):         # jambs
        A(box((xa, RY0 - W, WZ0), (xb, RY0, WZ1), {'side': T('frame_white'), 'n': T('frame_white')}, detail=False))
    return MH


def window_and_outside():
    WX0, WX1, WZ0, WZ1 = -384, 896, 576, 1408
    Y = RY0
    # deep marble sill (spans the wall depth and protrudes 176 into the room)
    A(box((-448, Y - 32, 560), (960, Y + 176, 576), T('sill_marble'), detail=False))
    # frame bars + 4 glass panes (glass: trans, lets the sun through)
    MX0, MX1, TZ0, TZ1 = 240, 272, 976, 1008
    fr = T('frame_white')
    A(box((MX0, Y - 28, WZ0), (MX1, Y - 4, WZ1), fr))
    A(box((WX0, Y - 28, TZ0), (MX0, Y - 4, TZ1), fr)); A(box((MX1, Y - 28, TZ0), (WX1, Y - 4, TZ1), fr))
    for (xa, xb) in ((WX0, MX0), (MX1, WX1)):
        for (za, zb) in ((WZ0, TZ0), (TZ1, WZ1)):
            A(box((xa, Y - 18, za), (xb, Y - 14, zb), T('glass')))
    # radiator under the window: fins + brackets (stands on the floor on two feet)
    for (fx) in (-288, 784):
        A(box((fx, Y + 8, 0), (fx + 32, Y + 56, 96), T('metal_chrome')))
    A(box((-320, Y + 8, 96), (832, Y + 64, 448), T('radiator')))
    # ---- outside: sky box + garden far below
    S = T('sky'); x0, x1, y0, y1, z0, z1 = -1200, 1700, -2600, Y - 32, -600, 2400
    for mn, mx in (((x0 - 16, y0 - 16, z0 - 16), (x1 + 16, y1, z0)), ((x0 - 16, y0 - 16, z1), (x1 + 16, y1, z1 + 16)),
                   ((x0 - 16, y0, z0), (x0, y1, z1)), ((x1, y0, z0), (x1 + 16, y1, z1)),
                   ((x0 - 16, y0 - 16, z0), (x1 + 16, y0, z1))):
        A(box(mn, mx, S, detail=False))
    # the room's outer face (house wall) seen from outside
    FAC = {'s': T('dh_clapboard'), 'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((x0, y1 - 16, z0), (WX0, y1, z1), FAC, detail=False))
    A(box((WX1, y1 - 16, z0), (x1, y1, z1), FAC, detail=False))
    A(box((WX0, y1 - 16, z0), (WX1, y1, WZ0), FAC, detail=False))
    A(box((WX0, y1 - 16, WZ1), (WX1, y1, z1), FAC, detail=False))
    speaker(250, -2000, 800, 'sound/world/animal/blackbird.ogg')
    speaker(-700, -2300, 600, 'sound/world/animal/bird_blackcap.ogg')
    # dust motes in the sunbeam (nonsolid additive slab)
    A(hull([(WX0 + 40, Y + 180, 1300), (WX1 - 40, Y + 180, 1300), (WX0 + 40, Y + 180, 700), (WX1 - 40, Y + 180, 700),
            (WX0 - 40, Y + 1500, 400), (WX1 - 140, Y + 1500, 400), (WX0 - 40, Y + 1500, 60), (WX1 - 140, Y + 1500, 60)],
           T('dustmotes')))
    # sill decoration
    solid_mdl('pad_westernset/cactus.md3', -360, Y + 90, 576, scale=1.2, angle=30)
    mdl_c('pad_ddmix/plants/flower_pink.md3', 60, Y + 100, 576, scale=0.6, angle=0)
    mdl_c('pad_sunflower/pad_sunflower3.md3', 520, Y + 90, 576, scale=1.5, angle=200)
    mdl_c('pad_ddmix/plants/bonsai.md3', 840, Y + 96, 576, scale=0.55, angle=90)
    item('item_armor_shard', -150, Y + 100, 576)
    weapon('balloony', 330, Y + 110, 576, marker='orange')
    item('ammo_pumper', 700, Y + 120, 576)
    spawn(-250, Y + 110, 576, 90)
    light(250, Y + 300, 900, 900, '1 0.95 0.85')
    # floor pad up to the sill (in front of the radiator)
    jumppad(-140, Y + 520, 0, (-200, Y + 110, 576), 760, 'jp_sill')


# =================================================================================================== bed + nightstand
def bed():
    X0, X1, Y0, Y1 = -1792, -1152, 64, 1536
    pine = T('pine')
    A(box((X0, Y1 - 64, 0), (X1, Y1, 704), {'side': pine, 'top': pine}))                     # headboard
    A(box((X0 + 16, Y1 - 64, 704), (X1 - 16, Y1, 736), {'side': pine, 'top': pine}))          # rounded-ish cap
    for (lx) in (X0, X1 - 64):
        A(box((lx, Y0, 0), (lx + 64, Y0 + 64, 176), pine))                                     # foot legs
    A(box((X0, Y0, 176), (X1, Y1 - 64, 224), pine))                                            # frame / slats
    A(box((X0 + 8, Y0, 224), (X1 - 8, Y1 - 64, 368), {'side': T('mattress'), 'top': T('sheet'), 'bot': T('mattress')}))
    A(box((X0 + 8, Y0, 368), (X1 - 8, 1200, 384), {'top': T('duvet'), 'side': T('duvet'), 'bot': T('duvet')}))
    # two puffy pillows: domed hulls with rounded corners (soft 41-deg top slopes, steep plump sides)
    def pillow(x0, x1, y0, y1, z):
        prof = [(0, 0, 40), (10, 14, 44), (26, 30, 52), (44, 50, 64), (56, 80, 72)]   # (dz, inset, corner)
        pts = []
        for dz, ins, c in prof:
            ax0, ax1, ay0, ay1 = x0 + ins, x1 - ins, y0 + ins, y1 - ins
            c = min(c, (ax1 - ax0) / 2 - 1, (ay1 - ay0) / 2 - 1)
            for k in range(16):
                ang = 2 * math.pi * (k + 0.5) / 16
                cx = ax1 - c if math.cos(ang) > 0 else ax0 + c
                cy = ay1 - c if math.sin(ang) > 0 else ay0 + c
                pts.append((cx + c * math.cos(ang), cy + c * math.sin(ang), z + dz))
        A(hull(pts, T('pillow'), round_pts=False))
    if PILLOW == 'md3':
        # curved MD3 pillows (pillow_md3.py) + a matching invisible weapclip dome each, 60u high like the model
        for (cx, ang) in ((-1626, 4), (-1318, -3)):
            M.model('models/mapobjects/playroom/pillow.md3', (cx, 1348, 368), scale=1, angle=ang)
            pts = []
            for dz, ins, c in ((0, 2, 40), (8, 14, 44), (22, 30, 52), (37, 50, 64), (47, 80, 72)):
                ax0, ax1, ay0, ay1 = cx - 142 + ins, cx + 142 - ins, 1240 + ins, 1456 - ins
                c = min(c, (ax1 - ax0) / 2 - 1, (ay1 - ay0) / 2 - 1)
                for k in range(16):
                    an = 2 * math.pi * (k + 0.5) / 16
                    px = ax1 - c if math.cos(an) > 0 else ax0 + c
                    py = ay1 - c if math.sin(an) > 0 else ay0 + c
                    pts.append((px + c * math.cos(an), py + c * math.sin(an), 368 + dz))
            A(hull(pts, WCLIP, round_pts=False))
    else:
        pillow(X0 + 24, -1484, 1240, 1456, 368)
        pillow(-1460, X1 - 24, 1240, 1456, 368)
    # duvet hanging over the foot end (short flap, stays clear of the floor) + jump pad up onto the bed
    A(box((X0 + 8, Y0 - 8, 232), (X1 - 8, Y0, 384), T('duvet')))
    jumppad(-1470, -220, 0, (-1470, 520, 384), 560, 'jp_bedup')
    jumppad(-960, 960, 0, (-1450, 760, 384), 560, 'jp_bedside')      # alongside the bed, east side
    # under the bed (z 0..176): shoebox, comics, socks, lost ball; dim night light
    A(box((-1660, 1000, 0), (-1400, 1240, 96), {'side': T('shoebox'), 'top': T('cardboard')}))
    mdl('pad_books/comics/pad_comic1.md3', -1300, 700, 0, angle=20)
    mdl('pad_books/comics/pad_comic1.md3', -1560, 420, 0, angle=95)
    mdl('pad_clothes/sock_grey.md3', -1700, 860, 0, angle=60)
    mdl('pad_clothes/sock_grey2.md3', -1290, 1100, 0, angle=0)
    mdl('pad_ball/pad_tennisball.md3', -1500, 1350, 0)
    weapon('boaster', -1480, 760, 0, marker='green')
    item('ammo_betty', -1620, 1360, 0)
    item('ammo_nipper', -1300, 380, 0)
    light(-1460, 900, 120, 120, '0.5 0.6 1')
    speaker(-1500, 800, 80, 'sound/world/animal/kitten_meow.ogg', loop=False, targetname='meow')
    # on the bed
    item('item_jumper', -1626, 1348, 424 if PILLOW != 'md3' else 415)
    item('ammo_pumper', -1620, 900, 384)
    spawn(-1300, 1000, 384, 270)
    jumppad(-1472, 320, 384, (-1500, -1330, 1152), 1290, 'jp_bed')
    mdl('pad_books/kids/mbook_fl_2.md3', -1300, 600, 384, angle=75)
    mdl('gummybears/ldyellowbear.md3', -1700, 600, 384, angle=10)


def nightstand():
    X0, X1, Y0, Y1 = -1152, -768, 1152, 1536
    drawer_box((X0, Y0, 0), (X1, Y1, 368), 's', 3, 'drawer_sky')
    A(box((X0, Y0, 368), (X1, Y1, 384), T('wood_white')))
    if CLOCK == 'md3':
        # twin-bell wind-up alarm clock (clock_md3.py), dial facing the room, + an invisible weapclip around the drum/bells
        M.model('models/mapobjects/playroom/alarmclock.md3', (-1050, 1460, 384), scale=1, angle=0)
        A(box((-1112, 1434, 384), (-988, 1490, 552), WCLIP))
    else:
        # alarm clock with a face on the south side
        A(box((-1110, 1420, 384), (-990, 1500, 488), T('plastic_grey')))
        A(sign_box((-1100, 1416, 394), (-1000, 1420, 478), T('clock'), 128, 128, back=T('plastic_grey'), facing='s'))
        A(box((-1092, 1440, 488), (-1060, 1480, 504), T('metal_chrome'))); A(box((-1040, 1440, 488), (-1008, 1480, 504), T('metal_chrome')))
    mdl_c('pad_lamps/small_gooseneck.md3', -850, 1460, 384, angle=225)
    mdl('pad_cups/pad_cup03.md3', -900, 1240, 384, angle=30)
    item('ammo_splasher', -1040, 1260, 384)
    speaker(-1050, 1400, 470, 'sound/world/machine/clock_ticking.ogg')
    light(-860, 1400, 560, 260, '1 0.85 0.6')


# =================================================================================================== desk access + desk
def desk_pad():
    """jump pad on the floor west of the desk (replaces the old race-track ramp: much quicker up)"""
    jumppad(260, 1300, 0, (660, 1290, 576), 760, 'jp_deskup')
    item('ammo_boaster', 100, 1300, 0)
    item('item_armor_shard', -220, 1340, 0)
    speaker(0, 1296, 300, 'sound/world/misc/toy_squeeze.ogg', loop=False, targetname='squeak')


def loop_arch(cx, cy, r_in=192, r_out=224, w=160, n=20):
    """decorative loop-the-loop standing on the rug: you run through it"""
    zc = r_in + 8
    for k in range(n):
        a0 = -math.pi / 2 + 2 * math.pi * k / n; a1 = -math.pi / 2 + 2 * math.pi * (k + 1) / n
        if k in (0, n - 1): continue           # bottom: flat strip on the floor instead
        pts = []
        for a in (a0, a1):
            for r in (r_in, r_out):
                for x in (cx - w / 2, cx + w / 2):
                    pts.append((x, cy + r * math.cos(a), zc + r * math.sin(a)))
        if min(p[2] for p in pts) < 4: continue
        A(hull(pts, {'side': T('track_side'), 'top': T('track'), 'bot': T('track')}, round_pts=False))
    A(box((cx - w / 2, cy - 160, 4), (cx + w / 2, cy + 160, 12), {'top': T('track'), 'side': T('track_side')}))


def desk():
    X0, X1, Y0, Y1 = 448, 1408, 1056, 1536
    A(box((X0, Y0, 552), (X1, Y1, 576), {'top': T('laminate'), 'side': T('laminate'), 'bot': T('wood_white')}))
    for (ya, yb) in ((Y0, Y0 + 64), (Y1 - 64, Y1)):
        A(box((X0, ya, 0), (X0 + 64, yb, 552), T('metal_chrome')))
    drawer_box((1152, Y0 + 16, 32), (X1, Y1 - 16, 552), 's', 4, 'drawer_mint')
    A(box((1152, Y0 + 16, 0), (X1, Y1 - 16, 32), T('wood_white')))
    # knee space: PC tower, waste paper bin, cables
    A(box((560, 1300, 0), (752, 1520, 448), T('pc_case')))
    A(box((600, 1296, 380), (712, 1300, 388), T('pc_led')))
    A(cyl(1020, 1380, 72, 0, 220, {'side': T('plastic_grey'), 'top': T('pages'), 'bot': T('plastic_grey')}, 10))
    speaker(656, 1400, 200, 'sound/world/machine/fan_pc.ogg')
    M.ent('station_health', (860, 1180, 0), angle=270)
    item('holdable_boomies', 880, 1440, 0)
    item('ammo_bubbleg', 600, 1150, 0)
    # desk top
    Z = 576
    solid_mdl('pad_pc/pad_tft.md3', 860, 1440, Z, angle=270)
    mdl_c('pad_pc/keyboard.md3', 860, 1230, Z, angle=270)
    mdl_c('pad_pc/mousea.md3', 1080, 1220, Z, angle=270)
    mdl_c('pad_lamps/gooseneck.md3', 1300, 1430, Z, angle=200)
    mdl_c('pad_cups/pad_cup02.md3', 560, 1450, Z, angle=0)
    mdl_c('pad_pencils/pad_pencilsr_lg.md3', 640, 1140, Z, angle=20)
    mdl_c('pad_pencils/pad_pencilsg_lg.md3', 660, 1110, Z, angle=-10)
    mdl_c('pad_phones/pad_padika2.md3', 1180, 1320, Z, angle=80)
    solid_mdl('gummybears/redbear.md3', 1100, 1460, Z, angle=250)
    mdl_c('pad_tins/pad_coke.md3', 1360, 1110, Z, angle=0)
    mdl_c('pad_objects/pad_fdisk.md3', 700, 1330, Z, angle=12)
    weapon('pumper', 1000, 1120, Z, marker='green')
    item('ammo_splasher', 520, 1150, Z)
    spawn(560, 1300, Z, 0)
    speaker(1180, 1320, 610, 'sound/world/misc/mobile_ring.ogg', loop=False, targetname='phone')
    M.ent('func_timer', (1180, 1320, 640), target='phone', wait=55, random=25, spawnflags=1)
    light(1260, 1380, 760, 450, '1 0.9 0.7')
    # pad to the shelf ledge
    jumppad(1290, 1140, Z, (1552, 880, 832), 960, 'jp_desk')


def chair(cx=900, cy=760):
    """office chair facing the desk: 5-star base, post, round seat, backrest"""
    A(cyl(cx, cy, 40, 40, 64, T('plastic_black'), 10))
    for k in range(5):
        a = math.radians(90 + 72 * k)
        ex, ey = cx + 150 * math.cos(a), cy + 150 * math.sin(a)
        sx, sy = cx + 40 * math.cos(a), cy + 40 * math.sin(a)
        nx, ny = -math.sin(a) * 14, math.cos(a) * 14
        A(hull([(sx + nx, sy + ny, 40), (sx - nx, sy - ny, 40), (ex + nx, ey + ny, 40), (ex - nx, ey - ny, 40),
                (sx + nx, sy + ny, 64), (sx - nx, sy - ny, 64), (ex + nx, ey + ny, 56), (ex - nx, ey - ny, 56)], T('plastic_black')))
        A(cyl(ex, ey, 20, 0, 40, T('plastic_black'), 8))
    A(cyl(cx, cy, 26, 64, 320, T('metal_chrome'), 8))
    A(cyl(cx, cy, 176, 320, 368, {'top': T('fabric_blue'), 'side': T('fabric_blue'), 'bot': T('plastic_black')}, 16))
    A(box((cx - 24, cy - 196, 368), (cx + 24, cy - 168, 440), T('metal_chrome')))
    A(box((cx - 150, cy - 220, 440), (cx + 150, cy - 168, 740), {'side': T('fabric_blue'), 'top': T('fabric_blue')}))
    item('ammo_balloony', cx - 260, cy - 120, 0)


# =================================================================================================== shelf cabinet + hutch
def shelf():
    X0, X1, Y0, Y1 = 1472, 1792, 192, 992
    W = T('wood_white')
    for (ya, yb) in ((Y0, Y0 + 32), (Y1 - 32, Y1)):
        A(box((X0, ya, 0), (X1, yb, 816), W))
    A(box((X0, Y0 + 32, 0), (X1, Y1 - 32, 16), {'side': T('wood_mint'), 'top': W}))
    A(box((X0, Y0 + 32, 432), (X1, Y1 - 32, 448), W))
    A(box((X0, Y0, 816), (X1, Y1, 832), W))
    HX = 1632
    for (ya, yb) in ((Y0, Y0 + 32), (Y1 - 32, Y1)):
        A(box((HX, ya, 832), (X1, yb, 1424), W))
    A(box((HX, Y0 + 32, 1200), (X1, Y1 - 32, 1216), W))
    A(box((HX - 16, Y0 - 16, 1424), (X1, Y1 + 16, 1440), W))
    # bottom compartment (64..432): dark nook
    item('ammo_imperius', 1660, 620, 16)
    mdl_c('pad_tins/pad_paint1.md3', 1700, 300, 16, angle=40)
    mdl_c('pad_tins/pad_paint2.md3', 1700, 420, 16, angle=10)
    mdl_c('pad_ball/pad_basketball.md3', 1680, 860, 16)
    light(1560, 600, 300, 140, '0.9 0.9 1')
    # middle compartment (448..816): books, figures, toy car
    mdl_c('pad_books/rhodan/pdr_4books.md3', 1700, 330, 448, angle=0)
    mdl('pad_books/pad_cb_ur_lg.md3', 1700, 470, 448, angle=0)
    mdl('pad_books/pad_cb_ur_lg_wop.md3', 1700, 520, 448, angle=0)
    solid_mdl('pad_actionfigures/fig_lilly.md3', 1700, 860, 448, angle=180)
    item('ammo_balloony', 1560, 700, 448)
    item('ammo_boaster', 1560, 400, 448)
    spawn(1580, 560, 448, 180)
    # ledge (832) + hutch lower compartment
    mdl_c('pad_books/pad_cb_fl_lg.md3', 1700, 860, 832, angle=0)
    solid_mdl('pad_ddmix/cabin/telescope.md3', 1700, 340, 832, angle=180)
    item('item_revival', 1700, 600, 832)    # not item_berserker: Pickup_Powerup passes the item's NULL client (crash in current WoP main)
    item('ammo_nipper', 1520, 340, 832)
    light(1560, 600, 1100, 300)
    # top compartment (1216..1424): the prize
    weapon('imperius', 1712, 592, 1216, marker='purple')
    mdl_c('pad_books/rhodan/pdr_4books.md3', 1710, 330, 1216, angle=0)
    solid_mdl('pad_statues/statue_super.md3', 1712, 840, 1216, scale=0.75, angle=180)
    light(1680, 600, 1380, 160, '0.9 0.6 1')
    # pads: floor -> middle compartment, ledge -> top compartment
    jumppad(1300, 600, 0, (1600, 600, 448), 640, 'jp_shelf_mid')
    jumppad(1506, 592, 832, (1712, 592, 1216), 1360, 'jp_shelf_top')


# =================================================================================================== dresser + aquarium
def dresser_tank():
    X0, X1, Y0, Y1 = 1152, 1792, -1536, -1056
    drawer_box((X0, Y0, 48), (X1, Y1, 560), 'n', 3, 'drawer_sun')
    A(box((X0, Y0, 0), (X1, Y1, 48), T('wood_white')))
    A(box((X0, Y0, 560), (X1, Y1, 576), T('wood_white')))
    # tank on the dresser: frame base, gravel, 4 glass walls, water
    TX0, TX1, TY0, TY1 = 1280, 1744, -1504, -1232
    A(box((TX0, TY0, 576), (TX1, TY1, 592), T('tank_frame')))
    A(box((TX0 + 8, TY0 + 8, 592), (TX1 - 8, TY1 - 8, 608), T('gravel')))
    G = T('tankglass')
    A(box((TX0, TY0, 592), (TX1, TY0 + 8, 880), G)); A(box((TX0, TY1 - 8, 592), (TX1, TY1, 880), G))
    A(box((TX0, TY0 + 8, 592), (TX0 + 8, TY1 - 8, 880), G)); A(box((TX1 - 8, TY0 + 8, 592), (TX1, TY1 - 8, 880), G))
    A(box((TX0 + 8, TY0 + 8, 608), (TX1 - 8, TY1 - 8, 872), T('water')))
    # jump pad on the front ledge: over the glass and splash down into the tank
    jumppad(1380, -1144, 576, (1500, -1380, 608), 1000, 'jp_tank')
    # tank contents
    mdl_c('pad_ddmix/plants/waterplant1a.md3', 1480, -1400, 608, scale=0.5, angle=0)
    mdl_c('pad_ddmix/plants/waterplant1b.md3', 1590, -1320, 608, scale=0.6, angle=90)
    mdl_c('pad_ddmix/padship/amphora.md3', 1350, -1290, 608, scale=0.5, angle=40)
    mdl_c('pad_teleporter/padtp_blue.md3', 1686, -1448, 608, scale=0.5, angle=0)
    M.ent('trigger_teleport', brushes=[box((1656, -1488, 608), (1720, -1408, 680), TRIG)], target='tp_tank')
    M.ent('misc_teleporter_dest', (1040, -760, 24), targetname='tp_tank', angle=135)
    weapon('splasher', 1520, -1380, 608, marker='blue')
    item('ammo_imperius', 1390, -1330, 608)
    fish = ['pad_fish/flame_angel.md3', 'pad_fish/flame_angel02.md3', 'pad_fish/flame_angel05.md3', 'pad_fish/flame_angel_r.md3']
    for i, (fx, fy, fz) in enumerate(((1400, -1380, 780), (1600, -1440, 720), (1500, -1300, 820), (1660, -1320, 760))):
        M.ent('func_pendulum', (fx, fy, fz), brushes=[box((fx - 8, fy - 8, fz - 24), (fx + 8, fy + 8, fz + 8), NODRAW_NS)],
              model2='models/mapobjects/' + fish[i], speed=12, phase=round(i / 4, 2), angle=(i * 90 + 30) % 360)
    light(1512, -1368, 860, 260, '0.5 0.8 1')
    light(1512, -1368, 680, 160, '0.4 0.7 1')
    speaker(1512, -1368, 700, 'sound/world/machine/fishtank.ogg')
    # dresser top west strip
    item('ammo_pumper', 1216, -1180, 576)
    solid_mdl('pad_ducks/pad_duck.md3', 1210, -1340, 576, scale=0.5, angle=60)
    spawn(1216, -1140, 576, 180)
    # ruler bridge from the sill to the dresser
    rb = box((900, -1504, 576), (1232, -1424, 592), T('ruler'))
    for f in rb.faces:
        if f.n[2] > 0.9: f.sc = (332 / 512, 80 / 64); f.off = ((-900 / (332 / 512)) % 512, ((-1424) / (80 / 64)) % 64)
    A(rb)
    jumppad(1000, -880, 0, (1216, -1180, 576), 760, 'jp_dresser')


# =================================================================================================== wardrobe
def wardrobe():
    X0, X1, Y0, Y1 = -1792, -1216, -1536, -1088
    W = T('wardrobe')
    A(box((X0, Y0, 0), (X0 + 32, Y1, 1152), W))
    A(box((X1 - 32, Y0, 0), (X1, Y1, 1152), W))
    A(box((X0 + 32, Y0, 1120), (X1 - 32, Y1, 1152), {'side': W, 'top': T('dust'), 'bot': W}))
    A(box((X0 + 32, Y1 - 32, 1040), (X1 - 32, Y1, 1120), W))                    # lintel
    A(box((X0 + 32, Y0, 0), (X1 - 32, Y1, 16), {'side': W, 'top': T('dh_floor')}))
    A(box((X0 + 32, Y0, 880), (X1 - 32, Y1 - 32, 896), W))                      # hat shelf
    A(box((X0 + 32, Y0, 16), (X1 - 32, Y0 + 16, 880), W))                       # back panel
    # open doors (hinged at the front corners, swung 90 deg)
    for (xa, xb) in ((X0 + 8, X0 + 32), (X1 - 32, X1 - 8)):
        b = box((xa, Y1, 16), (xb, Y1 + 256, 1100), W)
        for f in b.faces:
            if abs(f.n[0]) > 0.99:
                f.tex = T('wardrobe_door'); fit_face(f, Y1, Y1 + 256, 16, 1100, 128, 512)
        A(b)
    # clothes rail + hanging clothes (well above head height)
    A(box((X0 + 32, -1330, 780), (X1 - 32, -1314, 796), T('metal_chrome')))
    # garments on hangers, hanging flat in the y-z plane (front faces the open doors), well above head height
    RY = -1322                                   # rail centre (y)
    def hanger(x):
        A(box((x - 2, RY - 2, 796), (x + 2, RY + 2, 812), T('metal_chrome')))                        # hook over the rail
        for sg in (-1, 1):                                                                              # wire shoulders
            A(hull([(xx, RY + sg * dy, z) for xx in (x - 2, x + 2) for (dy, z) in ((4, 780), (4, 775), (74, 750), (74, 745))],
                   T('metal_chrome'), round_pts=False))
    def slab(x, pts2d, tex, t=10):
        """extrude a convex outline [(dy, z)...] around the rail by +-t/2 in x"""
        A(hull([(xx, RY + dy, z) for xx in (x - t / 2, x + t / 2) for (dy, z) in pts2d], T(tex), round_pts=False))
    def shirt(x, tex, long=False, hood=False):
        hanger(x)
        bot = 520 if long else 580
        slab(x, [(-80, 742), (80, 742), (-26, 752), (26, 752), (-72, bot), (72, bot)], tex, 14)       # body + collar
        for sg in (-1, 1):                                                                              # sleeves hang down
            sl = 560 if long else 680
            slab(x, [(sg * 80, 742), (sg * 100, 728), (sg * 104, sl), (sg * 82, sl + 6)], tex, 12)
        if hood:
            slab(x + 9, [(-34, 748), (34, 748), (-26, 690), (26, 690)], tex, 4)
    def trousers(x, tex):
        A(box((x - 2, RY - 2, 796), (x + 2, RY + 2, 812), T('metal_chrome')))
        A(box((x - 2, RY - 70, 760), (x + 2, RY + 70, 768), T('metal_chrome')))                     # clip bar
        slab(x, [(-66, 760), (66, 760), (-66, 720), (66, 720)], tex, 12)                               # waistband
        for sg in (-1, 1):
            slab(x, [(sg * 4, 720), (sg * 66, 720), (sg * 8, 470), (sg * 64, 470)], tex, 12)        # legs
    def dress(x, tex):
        hanger(x)
        slab(x, [(-60, 742), (60, 742), (-46, 640), (46, 640)], tex, 12)                               # bodice
        slab(x, [(-46, 640), (46, 640), (-100, 470), (100, 470)], tex, 10)                             # flared skirt
    shirt(-1736, 'fabric_stripe')
    trousers(-1676, 'fabric_denim')
    dress(-1614, 'fabric_dots')
    shirt(-1554, 'fabric_green', long=True, hood=True)
    shirt(-1494, 'fabric_check')
    trousers(-1434, 'fabric_orange')
    shirt(-1374, 'fabric_red', long=True)
    shirt(-1314, 'fabric_yellow')
    # floor inside: shoe boxes, socks, armour
    for (bx, by, bz, h) in ((-1720, -1500, 16, 96), (-1720, -1500, 112, 96), (-1580, -1500, 16, 96)):
        A(box((bx, by, bz), (bx + 128, by + 200, bz + h), {'side': T('shoebox'), 'top': T('cardboard'), 'bot': T('cardboard')}))
    mdl('pad_clothes/sock_grey3.md3', -1380, -1250, 16, angle=30)
    item('item_armor_padshield', -1450, -1200, 16)
    item('ammo_boaster', -1320, -1450, 16)
    item('holdable_bambam', -1620, -1200, 16)
    light(-1504, -1250, 700, 220)
    # top: dusty boxes, the Betty
    for (bx, by, w, d, h) in ((-1760, -1520, 192, 160, 128), (-1440, -1520, 160, 192, 96)):
        A(box((bx, by, 1152), (bx + w, by + d, 1152 + h), T('cardboard')))
    weapon('betty', -1500, -1250, 1152, marker='black')
    item('ammo_bubbleg', -1300, -1160, 1152)
    light(-1500, -1300, 1400, 260)
    solid_mdl('pad_ddmix/padshop/cardboard_standup.md3', -1330, -660, 0, angle=135)


# =================================================================================================== dollhouse
def dollhouse():
    X0, X1, Y0, Y1 = -1088, -416, -1056, -608           # back (south, y0) open
    CL, TR = T('dh_clapboard'), T('dh_trim')
    def wtex(inner_dir, inner):
        return {'side': CL, 'top': TR, 'bot': TR, inner_dir: T(inner)}
    # front wall (north) with door x -592..-496 (z 0..152), upper windows
    FY0, FY1 = Y1 - 16, Y1
    up_win = [(-1000, -904), (-800, -704)]
    def front_strip(z0, z1, holes, inner):
        xs = [X0] + [v for h in holes for v in h] + [X1]
        for i in range(0, len(xs), 2):
            if xs[i + 1] > xs[i]:
                A(box((xs[i], FY0, z0), (xs[i + 1], FY1, z1), wtex('s', inner)))
    front_strip(0, 152, [(-592, -496)], 'dh_wall_flower')
    front_strip(152, 208, [], 'dh_wall_flower')
    A(box((X0, FY0, 208), (X1, FY1, 224), TR))
    front_strip(224, 288, [], 'dh_wall_stripe')
    front_strip(288, 384, up_win, 'dh_wall_stripe')
    front_strip(384, 432, [], 'dh_wall_stripe')
    # side walls (west x0, east x1) with a window each on the ground floor (y -880..-784, z 64..160)
    for (xa, xb, inner_dir) in ((X0, X0 + 16, 'e'), (X1 - 16, X1, 'w')):
        for (ya, yb, za, zb) in ((Y0, -880, 0, 208), (-784, FY0, 0, 208), (-880, -784, 0, 64), (-880, -784, 160, 208)):
            A(box((xa, ya, za), (xb, yb, zb), wtex(inner_dir, 'dh_wall_flower')))
        A(box((xa, Y0, 208), (xb, FY0, 224), TR))
        A(box((xa, Y0, 224), (xb, FY0, 432), wtex(inner_dir, 'dh_wall_stripe')))
    # window decals around openings (frames as thin trim)
    A(box((-608, FY1, 152), (-480, FY1 + 8, 168), TR))                 # door lintel trim
    A(sign_box((-680, FY1, 168), (-408, FY1 + 6, 204), T('dh_sign'), 256, 64, back=TR, facing='n'))
    # upper floor slab with the stairwell hole (x -1072..-680, y -720..-624)
    for r in sub_rects((X0 + 16, Y0, X1 - 16, FY0), [(-1072, -720, -680, FY0), (-528, -1048 - 8, -432, -656)]):
        A(box((r[0], r[1], 208), (r[2], r[3], 224), {'top': T('dh_floor'), 'bot': TR, 'side': TR}))
    # roof slab with the roof hatch hole (x -528..-432, y -1056..-656)
    for r in sub_rects((X0, Y0, X1, FY1), [(-528, Y0, -432, -656)]):
        A(box((r[0], r[1], 432), (r[2], r[3], 448), {'top': T('roof_tiles'), 'bot': TR, 'side': TR}))
    # roof rim (16 high, never blocks shots) except over the hatch
    for (mn, mx) in (((X0, FY1 - 8, 448), (X1, FY1, 464)), ((X0, Y0 + 8, 448), (X0 + 8, FY1 - 8, 464)),
                     ((X1 - 8, -656, 448), (X1, FY1 - 8, 464)), ((X0, Y0, 448), (-528, Y0 + 8, 464))):
        A(box(mn, mx, TR))
    A(box((-1000, -720, 448), (-936, -656, 576), {'side': T('brick_red'), 'top': T('plastic_black')}))      # chimney
    # stairs ground -> upper (rising east, against the front wall)
    A(stairs(-1072, -720, -680, FY0, 0, 224, 'e', T('dh_trim'), top_tex=T('dh_floor')))
    # stairs upper -> roof (rising north along the east wall)
    A(stairs(-528, -1048, -432, -656, 224, 448, 'n', T('dh_trim'), base=224, top_tex=T('dh_floor')))
    # balcony rail along the open back of the upper floor
    A(box((-1072, Y0, 224), (-560, Y0 + 8, 256), TR))
    # interior decor
    A(box((-900, -980, 0), (-760, -860, 64), T('pine'))); A(box((-912, -992, 64), (-748, -848, 72), T('pine')))
    mdl_c('pad_cake/pad_cakestand.md3', -830, -920, 72, scale=0.5)
    item('ammo_balloony', -1000, -900, 0)
    item('item_armor_shard', -600, -820, 0)
    spawn(-640, -960, 0, 90)
    # upper floor: little bed + rewards
    A(box((-1056, -1040, 224), (-912, -880, 256), {'side': T('pine'), 'top': T('duvet')}))
    item('item_visionless', -760, -900, 224)
    item('holdable_killerducks', -980, -800, 224)
    item('ammo_splasher', -650, -1000, 224)
    light(-750, -880, 400, 220)
    light(-750, -880, 170, 200)
    # roof deck
    weapon('bubbleg', -760, -840, 448, marker='orange')
    item('ammo_betty', -1020, -980, 448)
    spawn(-640, -760, 448, 180)


# =================================================================================================== TV corner + beanbag
def tv_corner():
    X0, X1, Y0, Y1 = -1056, -512, -1536, -1280
    A(box((X0, Y0, 0), (X1, Y1, 32), T('walnut')))
    A(box((X0, Y0, 32), (X0 + 32, Y1, 192), T('walnut'))); A(box((X1 - 32, Y0, 32), (X1, Y1, 192), T('walnut')))
    A(box((X0, Y0, 192), (X1, Y1, 224), T('walnut')))
    A(box((X0 + 32, Y0, 32), (X1 - 32, Y0 + 16, 192), T('walnut')))
    # console inside the bench + TV on top
    A(box((-860, -1500, 32), (-700, -1400, 80), T('plastic_black')))
    solid_mdl('padtv/padtv2.md3', -784, -1408, 224, angle=270)
    mdl_c('pad_radio_car/radio_control_fl.md3', -930, -1440, 224, angle=200)
    speaker(-784, -1450, 360, 'sound/world/machine/tv_upstairs.ogg')
    item('ammo_betty', -620, -1380, 32)
    # beanbag in front (rounded hull)
    bx, by = -900, 600
    pts = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        pts += [(bx + 150 * math.cos(a), by + 110 * math.sin(a), 0), (bx + 120 * math.cos(a), by + 90 * math.sin(a), 120),
                (bx + 60 * math.cos(a), by + 40 * math.sin(a), 150)]
    A(hull(pts, T('beanbag')))
    M.ent('station_health', (-1120, -560, 0), angle=0)
    light(-784, -1350, 380, 220, '0.6 0.7 1')


# =================================================================================================== centre: rug, ziggurat, blocks, toy box, chess, loop
def centre():
    # playmat rug (4u high, fitted texture)
    rug = box((-400, -640, 0), (768, 272, 4), {'top': T('rug'), 'side': T('rug_edge'), 'bot': CAULK})
    fit_top(rug, -400, -640, 768, 272, 1024, 768)
    A(rug)
    # brick ziggurat: 7 levels of 32u (bots and players hop up)
    cx, cy = 250, -200
    tops = ['brick_red', 'brick_yellow', 'brick_blue', 'brick_green', 'brick_red', 'brick_white', 'brick_yellow']
    for i in range(7):
        h = 208 - 26 * i
        z0 = 4 + 32 * i
        A(box((cx - h, cy - h, z0), (cx + h, cy + h, z0 + 32), {'top': T(tops[i] + '_top'), 'side': T(tops[i])}))
    item('item_speedy', cx, cy, 4 + 32 * 7)
    # ABC blocks (128 cubes) as cover
    for (bx, by, bz, t) in ((-384, -512, 4, 'a'), (-256, -512, 4, 'b'), (-384, -512, 132, 'c'), (-128, 128, 4, 'd'),
                            (-1, 128, 4, 'p'), (-128, 128, 132, 'a'), (624, 96, 4, 'b'), (1152, -320, 0, 'c'), (-1040, -360, 0, 'd'),
                            (-1040, -360, 128, 'p'), (64, -1100, 0, 'a')):
        A(box((bx, by, bz), (bx + 128, by + 128, bz + 128), T('block_' + t)))
    item('ammo_nipper', -256, -590, 4)
    # toy box with leaning lid ramp (north of the rug)
    TX0, TX1, TY0, TY1 = -256, 256, 640, 960
    PB = T('toybox_plain')
    A(box((TX0, TY0, 0), (TX1, TY0 + 24, 240), {'side': PB, 'top': PB, 's': T('toybox')}))
    for f in M.world[-1].faces:
        if f.n[1] < -0.99: fit_face(f, TX0, TX1, 0, 240, 512, 256)
    A(box((TX0, TY1 - 24, 0), (TX1, TY1, 240), PB))
    A(box((TX0, TY0 + 24, 0), (TX0 + 24, TY1 - 24, 240), PB)); A(box((TX1 - 24, TY0 + 24, 0), (TX1, TY1 - 24, 240), PB))
    A(box((TX0 + 24, TY0 + 24, 0), (TX1 - 24, TY1 - 24, 208), {'top': T('fabric_yellow'), 'side': PB}))   # toys inside
    A(ramp(-160, 280, 160, TY0, 0, 0, 240, 'n', {'top': PB, 'side': PB, 'bot': CAULK}))                  # lid as a ramp
    mdl('pad_ball/pad_soccerball.md3', -140, 860, 208)
    mdl_c('gummybears/ldgreenbear.md3', 80, 740, 208, angle=20)
    item('holdable_floater', 0, 860, 208)
    item('ammo_balloony', -120, 740, 208)
    # chess board on the rug + pieces
    cb = box((480, -620, 4), (736, -364, 12), {'top': T('chessboard'), 'side': T('walnut')})
    fit_top(cb, 480, -620, 736, -364, 256, 256)
    A(cb)
    for (px, py, m) in ((528, -588, 'chess_white_king'), (592, -588, 'chess_white_dame'), (656, -572, 'chess_white_tower'),
                        (560, -420, 'chess_black_king'), (624, -404, 'chess_black_dame'), (688, -420, 'chess_black_tower')):
        mdl_c('pad_ddmix/chess/' + m + '.md3', px, py, 12)
    item('ammo_bubbleg', 576, -200, 4)
    # loop-the-loop arch on the west half of the rug
    loop_arch(-300, -60)
    # standing gummy bears + rubber duck + balls (sightline breakers)
    solid_mdl('gummybears/greenbear.md3', 120, -560, 4, angle=60)
    solid_mdl('gummybears/orangebear.md3', -1000, 300, 0, angle=200)
    solid_mdl('gummybears/yellowbear.md3', 1100, 200, 0, angle=150)
    solid_mdl('pad_ducks/pad_duck.md3', -520, 520, 0, angle=300)
    M.ent('trigger_multiple', brushes=[box((-660, 380, 0), (-380, 416, 120), TRIG), box((-660, 624, 0), (-380, 646, 120), TRIG),
                                       box((-660, 416, 0), (-635, 624, 120), TRIG), box((-404, 416, 0), (-380, 624, 120), TRIG)],
          target='squeak', wait=3)
    mdl('pad_ball/pad_basketball.md3', 1000, -300, 0)
    mdl('pad_ball/pad_soccerball.md3', -1100, -120, 0)
    mdl_c('pad_books/pad_ob_fl_lg_wop.md3', 860, 380, 0, angle=15)
    solid_mdl('pad_tins/pad_pupsi_sd.md3', -600, 700, 0, angle=35)
    solid_mdl('pad_toiletroll/pad_toiletroll.md3', 1260, -560, 0)
    # RC cars driving up and down (nonsolid eye candy, func_train)
    for (nm, x, ya, yb, mdlp, spd) in (('rc_a', 1380, -680, 100, 'pad_nascars/padcar_orange_rc.md3', 260),):
        br = [box((x - 8, ya - 8, 0 + 16), (x + 8, ya + 8, 32), ORIGIN), box((x - 16, ya - 16, 34), (x + 16, ya + 16, 50), NODRAW_NS)]
        M.ent('func_train', brushes=br, target=nm + '1', speed=spd, model2='models/mapobjects/' + mdlp)
        M.ent('path_corner', (x, ya, 24), targetname=nm + '1', target=nm + '2', wait=1.5)
        M.ent('path_corner', (x, yb, 24), targetname=nm + '2', target=nm + '1', wait=1.5)
    # floor items/spawns
    for (cls, x, y, z) in (('item_armor_shard', 0, -200, 4), ('item_armor_shard', 1200, 600, 0), ('item_armor_shard', -900, 800, 0),
                           ('ammo_bubbleg', -1100, 120, 0), ('ammo_pumper', 1250, -800, 0),
                           ('ammo_splasher', 200, -1250, 0), ('ammo_boaster', -400, 900, 0), 
                           ('ammo_bubbleg', 700, 520, 0)):
        item(cls, x, y, z)
    for (x, y, z, a) in ((0, -350, 4, 90), (-1000, 0, 0, 0), (1100, 400, 0, 180), (300, 1000, 0, 270), (-600, -1250, 0, 0),
                         (1040, -1180, 0, 90), (-200, 1100, 0, 0), (1200, -80, 0, 135), (-700, 300, 0, 300), (-1550, -800, 0, 45)):
        spawn(x, y, z, a)


# =================================================================================================== floor clutter (sightline breakers)
def clutter():
    # laundry basket with clothes heaped on top
    A(cyl(700, -1050, 140, 0, 200, {'side': T('rope'), 'top': T('fabric_denim'), 'bot': T('rope')}, 14))
    A(hull([(700 + 110 * math.cos(a), -1050 + 110 * math.sin(a), 200) for a in [k * math.pi / 5 for k in range(10)]] +
           [(690, -1040, 250), (730, -1070, 244)], T('fabric_red')))
    mdl('pad_clothes/sock_grey.md3', 820, -880, 0, angle=200)
    # staggered stack of picture books (32u steps, climbable)
    cols = ['red', 'blue', 'yellow', 'green', 'purple']
    for i in range(5):
        x0 = 820 + 28 * i; y0 = -120 + 18 * i
        A(book(x0, y0, x0 + 320 - 56 * i, y0 + 240 - 36 * i, 32 * i, 32 * (i + 1), cols[i]))
    item('ammo_balloony', 980, 0, 160)
    # toy rocket standing on its fins
    rx, ry = 100, -800
    for k in range(3):
        a = math.radians(90 + 120 * k)
        A(hull([(rx + 64 * math.cos(a) + 6 * math.sin(a) * sg, ry + 64 * math.sin(a) - 6 * math.cos(a) * sg, z) for sg in (-1, 1) for z in (0, 220)] +
               [(rx + 130 * math.cos(a) + 6 * math.sin(a) * sg, ry + 130 * math.sin(a) - 6 * math.cos(a) * sg, z) for sg in (-1, 1) for z in (0, 90)],
               T('fabric_red')))
    A(cyl(rx, ry, 60, 0, 200, T('brick_white'), 12))
    A(cyl(rx, ry, 60, 200, 260, T('fabric_red'), 12))
    A(cyl(rx, ry, 60, 260, 470, T('brick_white'), 12))
    A(hull([(rx + 60 * math.cos(a), ry + 60 * math.sin(a), 470) for a in [k * math.pi / 6 for k in range(12)]] + [(rx, ry, 640)], T('fabric_red')))
    # big shoe box (cover, west floor)
    b = box((-820, -300, 0), (-580, -60, 192), {'side': T('cardboard'), 'top': T('cardboard')})
    A(b)


# =================================================================================================== posters (2u thin, flat on the walls)
def posters():
    P = T('wood_white')
    A(sign_box((150, RY1 - 2, 900), (406, RY1, 1284), T('poster_hero'), 256, 384, back=P, facing='s'))
    A(sign_box((-460, RY1 - 2, 760), (-204, RY1, 952), T('drawing'), 256, 192, back=P, facing='s'))
    A(sign_box((RX0, 300, 800), (RX0 + 2, 556, 1184), T('poster_space'), 256, 384, back=P, facing='e'))
    A(sign_box((RX1 - 2, -760, 900), (RX1, -504, 1284), T('poster_duck'), 256, 384, back=P, facing='w'))
    A(sign_box((-1150, RY0, 760), (-894, RY0 + 2, 1144), T('poster_map'), 256, 384, back=P, facing='n'))


# =================================================================================================== more floor toys
def floor_toys():
    # cardboard play tunnel lying on its side (octagon tube along y, flat 16u floor inside): run through it
    cx, cz, ro, ri, y0, y1 = 500, 128, 128, 112, 620, 980
    def oct_pt(r, k):          # apothem r, flat face at the bottom
        a = k * math.pi / 4 - math.pi / 2 - math.pi / 8
        R = r / math.cos(math.pi / 8)
        return (cx + R * math.cos(a), cz + R * math.sin(a))
    for k in range(8):
        pts = []
        for r in (ri, ro):
            for kk in (k, k + 1):
                xx, zz = oct_pt(r, kk)
                pts += [(xx, y0, zz), (xx, y1, zz)]
        A(hull(pts, {'side': T('cardboard'), 'top': T('cardboard'), 'bot': T('cardboard')}, round_pts=False))
    item('ammo_nipper', 500, 800, 16)
    light(500, 800, 90, 90, '1 0.85 0.6')

    # open picture book lying face down as a tent (walk underneath along y)
    tx0, tx1, ty0, ty1, rz, th = -1640, -1300, -440, -120, 200, 12
    xm = (tx0 + tx1) / 2
    for (xa, xb) in ((tx0, xm), (tx1, xm)):
        pts = []
        for y in (ty0, ty1):
            pts += [(xa, y, 0), (xa + (th if xa < xb else -th), y, 0), (xb, y, rz), (xb, y, rz - th * 1.6)]
        A(hull(pts, {'side': T('book_purple'), 'bot': T('pages'), 'top': T('book_purple')}, round_pts=False))
    item('item_armor_shard', -1470, -280, 0)
    mdl_c('pad_pencils/pad_pencilsr_lg.md3', -1180, -160, 0, angle=70)
    mdl_c('pad_pencils/pad_pencilsbl_lg.md3', -1150, -220, 0, angle=95)
    mdl_c('pad_pencils/pad_pencilsy_lg.md3', -1210, -260, 0, angle=40)

    # wooden toy train along the north wall: engine + two wagons of blocks (cover and a little climb)
    def wheel(x, y0, y1, r=28):
        pts = []
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            for y in (y0, y1):
                pts.append((x + r * math.cos(a), y, r + r * math.sin(a)))
        A(hull(pts, {'side': T('fabric_red'), 'n': T('walnut'), 's': T('walnut')}, round_pts=False))
    Y0, Y1 = 1400, 1520
    cars = ((-660, -460, 'engine'), (-440, -260, 'wagon'), (-240, -60, 'wagon2'))
    for (xa, xb, kind) in cars:
        for wx in (xa + 40, xb - 40):
            wheel(wx, Y0, Y0 + 14); wheel(wx, Y1 - 14, Y1)
        A(box((xa, Y0 + 14, 22), (xb, Y1 - 14, 56), {'side': T('pine'), 'top': T('pine'), 'bot': T('pine')}))
        if kind == 'engine':
            A(box((xa, Y0 + 14, 56), (xa + 90, Y1 - 14, 176), {'side': T('fabric_red'), 'top': T('fabric_red')}))
            A(box((xa - 8, Y0 + 6, 176), (xa + 98, Y1 - 6, 192), T('fabric_yellow')))
            pts = []
            for k in range(8):
                a = 2 * math.pi * (k + 0.5) / 8
                for x in (xa + 90, xb):
                    pts.append((x, (Y0 + Y1) / 2 + 46 * math.cos(a), 56 + 46 + 46 * math.sin(a)))
            A(hull(pts, {'side': T('fabric_blue'), 'e': T('fabric_yellow')}, round_pts=False))
            A(cyl(xb - 40, (Y0 + Y1) / 2, 16, 146, 220, T('plastic_black'), 8))
        else:
            for (ya, yb) in ((Y0 + 14, Y0 + 26), (Y1 - 26, Y1 - 14)):
                A(box((xa, ya, 56), (xb, yb, 104), T('fabric_green' if kind == 'wagon' else 'fabric_orange')))
            A(box((xa, Y0 + 26, 56), (xa + 12, Y1 - 26, 104), T('fabric_green' if kind == 'wagon' else 'fabric_orange')))
            A(box((xb - 12, Y0 + 26, 56), (xb, Y1 - 26, 104), T('fabric_green' if kind == 'wagon' else 'fabric_orange')))
    for (bx, t) in ((-420, 'a'), (-340, 'c')):
        A(box((bx, 1430, 56), (bx + 64, 1494, 120), T('block_' + t)))
    item('ammo_balloony', 20, 1460, 0)
    mdl_c('pad_radio_car/radio_control.md3', -690, 1130, 0, angle=300)
    mdl_c('pad_ball/pad_tennisball.md3', 60, 1180, 0)
    mdl_c('pad_ball/pad_softball.md3', 140, 1120, 0)
    speaker(-560, 1460, 140, 'sound/world/misc/bicycle_bell.ogg', loop=False, targetname='trainbell')
    M.ent('func_timer', (-560, 1460, 200), target='trainbell', wait=40, random=20, spawnflags=1)


# =================================================================================================== ceiling: lamp + mobile
def ceiling():
    cx, cy = 0, -160
    A(box((cx - 3, cy - 3, 1380), (cx + 3, cy + 3, CZ), T('string')))
    A(hull([(cx + 100 * math.cos(a), cy + 100 * math.sin(a), 1380) for a in [k * math.pi / 6 for k in range(12)]] +
           [(cx + 40 * math.cos(a), cy + 40 * math.sin(a), 1440) for a in [k * math.pi / 6 for k in range(12)]],
           {'side': T('lampshade'), 'top': T('lampshade'), 'bot': T('lamp_glow')}))
    light(cx, cy, 1340, 9000, '1 0.94 0.8')
    # mobile: rotating ring of stars/planets hanging from its own string (func_rotating, nothing static in its sweep)
    mx, my, mz = 600, 500, 1180
    A(box((mx - 2, my - 2, mz + 120), (mx + 2, my + 2, CZ), T('string')))
    br = [box((mx - 8, my - 8, mz + 100), (mx + 8, my + 8, mz + 116), ORIGIN),
          box((mx - 260, my - 4, mz + 108), (mx + 260, my + 4, mz + 116), T('pine')),
          box((mx - 4, my - 260, mz + 100), (mx + 4, my + 260, mz + 108), T('pine'))]
    for (ex, ey, r, tex) in ((260, 0, 48, 'star_yellow'), (-260, 0, 40, 'fabric_red'), (0, 260, 44, 'fabric_blue'), (0, -260, 36, 'fabric_green')):
        br.append(box((mx + ex - 2, my + ey - 2, mz + 40), (mx + ex + 2, my + ey + 2, mz + 100), T('string')))
        ball = [(mx + ex, my + ey, mz + 40), (mx + ex, my + ey, mz + 40 - 2 * r)]
        for (zf, rf) in ((0.3, 0.75), (1.0, 1.0), (1.7, 0.75)):
            ball += [(mx + ex + r * rf * math.cos(a), my + ey + r * rf * math.sin(a), mz + 40 - r * zf) for a in [k * math.pi / 4 for k in range(8)]]
        br.append(hull(ball, T(tex), round_pts=False))
    M.ent('func_rotating', None, brushes=br, speed=12, spawnflags=0)
    # fill lights for the big room
    for (x, y) in ((-1200, 900), (0, 900), (1100, 600), (-1200, -400), (0, -700), (1100, -600), (-400, 200)):
        light(x, y, 1050, 3200, '1 0.96 0.9')


# =================================================================================================== secret: mouse hole -> hideout
def hideout(MH):
    HX0, HX1, HY0, HY1, HZ = -2272, -1824, -768, -320, 224
    W = 32
    # shell (structural) around the hideout
    for mn, mx, t in (((HX0 - W, HY0 - W, -16), (HX1, HY1 + W, 0), {'top': T('old_boards'), 'side': CAULK, 'bot': CAULK}),
                      ((HX0 - W, HY0 - W, HZ), (HX1, HY1 + W, HZ + 16), {'bot': T('plaster_rough'), 'side': CAULK, 'top': CAULK}),
                      ((HX0 - W, HY0 - W, 0), (HX0, HY1 + W, HZ), {'e': T('plaster_rough'), 'side': CAULK}),
                      ((HX0, HY0 - W, 0), (HX1, HY0, HZ), {'n': T('plaster_rough'), 'side': CAULK}),
                      ((HX0, HY1, 0), (HX1, HY1 + W, HZ), {'s': T('plaster_rough'), 'side': CAULK})):
        A(box(mn, mx, t, detail=False))
    # the room's west wall is the hideout's east wall above z 0; fill the strip between hideout and room wall
    # furniture: matchbox bed, cheese, candle light, sign
    mdl_c('pad_ddmix/jail/matches_closed.md3', -2180, -680, 0, angle=0)
    A(hull([(-2000, -400, 0), (-1900, -400, 0), (-2000, -352, 0), (-1900, -352, 0), (-2000, -400, 64), (-2000, -352, 64)], T('cheese')))
    A(sign_box((-2120, -324, 96), (-1992, -320, 160), T('secret_sign'), 256, 128, back=T('old_boards'), facing='s'))
    mdl_c('pad_books/comics/pad_comic1.md3', -2150, -470, 0, angle=40)
    item('item_padpower', -2050, -560, 0)
    item('ammo_imperius', -2200, -420, 0)
    light(-2040, -540, 180, 220, '1 0.8 0.5')
    # secret sound when you crawl in, teleporter home (onto the toy box toys)
    speaker(-1840, -592, 60, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret')
    M.ent('trigger_multiple', brushes=[box((-1880, MH[0] + 8, 0), (-1840, MH[1] - 8, 96), TRIG)], target='secret', wait=30)
    M.ent('trigger_teleport', brushes=[box((-2240, -744, 0), (-2176, -680, 72), TRIG)], target='tp_hide')
    M.ent('misc_teleporter_dest', (0, 800, 232), targetname='tp_hide', angle=270)
    mdl_c('pad_teleporter/padtp_orange.md3', -2208, -712, 0, scale=0.5)


# =================================================================================================== main
def main():
    textures.make_all(OUT)
    if PILLOW == 'md3':
        import pillow_md3
        pillow_md3.main(OUT)
    if CLOCK == 'md3':
        import clock_md3
        clock_md3.main(OUT)
    os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
    MH = room_shell()
    window_and_outside(); bed(); nightstand(); desk_pad(); desk(); chair(); shelf(); dresser_tank(); wardrobe()
    dollhouse(); tv_corner(); centre(); clutter(); floor_toys(); posters(); ceiling(); hideout(MH)
    M.ent('info_player_intermission', (-1200, -1000, 1300), angles='25 40 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text("// Padman's Playroom - generated by wop_tools/playroom/build_playroom.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', land)


if __name__ == '__main__':
    main()
