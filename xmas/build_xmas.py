#!/usr/bin/env python3
"""Padman's Christmas - World of Padman map generator (map 'wop_padxmas').

    OUT=/path/to/out python3 build_xmas.py

Writes <OUT>/maps/wop_padxmas.map, textures/padxmas/*, scripts/padxmas.shader, scripts/wop_padxmas.arena.

A living room on Christmas Eve at Padman scale (about 8u per cm, catalog models at native scale 1.0).
x east, y north, floor z 0, room x -2176..2176, y -1792..1792, ceiling z 2112.
  centre-north  the Christmas tree: 5 stacked fir tiers on a trunk + stand, presents under the lowest boughs,
                jump-pad chain up the tiers, weapons and powerups get better with height (Imperius + Pad Power on top)
  west          brick fireplace: mantel (pad), stockings, fire -> walk into the flames = up the chimney to the roof (secret)
  roof          snowy roof terrace under the night sky: Santa's sleigh, reindeer, sack, snowman, teleporter home
  NW            armchair, side table with cocoa and cookies, grandfather clock with a swinging pendulum
  NE            sideboard (pad): rotating Christmas pyramid, snow globe, nutcrackers; advent calendar
  east          sofa (pad seat -> pad back), coffee table with an Advent wreath
  SE            gingerbread house you can walk into, candy-cane ramp onto its iced roof
  south         window seat (pad) looking out on a snowy garden, curtains, bells
  SW / centre   rocking horse, toy drum, Santa's sack, toy train on an oval track, present stacks
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import xmas_textures as TX
import xmas_models as XM
from contextlib import contextmanager

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padxmas'
T = lambda n: 'padxmas/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW = 'common/nodraw'; NODRAW_NS = T('nodraw_ns')

for k, v in {'floor_oak': (2, 2), 'wallpaper': (2, 2), 'wainscot': (1, 2.5), 'ceiling': (2, 2), 'brick': (1, 1), 'brick_soot': (1, 1),
             'stone': (1, 1), 'needles': (1, 1), 'needles_top': (1, 1), 'needles_under': (1, 1), 'bark': (1, 1),
             'treeskirt': (2, 2), 'snow': (2, 2), 'snow_drift': (2, 2), 'roof_tiles_snow': (1, 1), 'velvet_green': (1, 1),
             'velvet_red': (1, 1), 'tartan': (0.75, 0.75), 'knit': (1, 1), 'wood_dark': (1, 1), 'wood_mid': (1, 1),
             'wood_light': (1, 1), 'gingerbread': (1, 1), 'ginger_roof': (1, 1), 'ginger_wall': (1.25, 1.25), 'curtain': (1, 2),
             'track': (0.5, 0.5), 'house_wall': (2, 2), 'fence': (1, 1), 'burlap': (1, 1), 'marble': (1, 1), 'candystripe': (0.5, 0.5),
             'sleigh_red': (1, 1), 'reindeer': (1, 1), 'log_bark': (0.5, 0.5), 'trim_white': (1, 1), 'trim_gold': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': "Padman's Christmas", '_ambient': '7', '_color': '1 0.9 0.8', 'gridsize': '96 96 96', '_blocksize': '0'})
_CLIP = [False]


def A(*bs, tag=None):
    """add brushes to the world; inside `with as_clip():` they become invisible weapon clip (collision of an MD3)"""
    if _CLIP[0]:
        for b in _flat(bs):
            for f in b.faces: f.tex = WCLIP
    return M.add(*bs, tag=tag)


def _flat(bs):
    for b in bs:
        if isinstance(b, (list, tuple)): yield from _flat(b)
        else: yield b


@contextmanager
def as_clip():
    _CLIP[0] = True
    try: yield
    finally: _CLIP[0] = False


def xm(name, x, y, z, angle=0, key=None, scale=1.0, lm=1.0, **kw):
    """place one of our MD3 models (xmas_models.py), lightmapped (spawnflags 4); origin = model base point"""
    path, sc = XM.get(name, key=key, **kw)
    z = z + XM.ZOFF.get(path, 0.0) * scale          # tall models are stored round their mid-height
    return M.model(path, (round(x, 2), round(y, 2), round(z, 2)), scale=sc * scale, angle=angle, spawnflags=4,
                   _lightmapscale=lm, _castshadows=1, _receiveshadows=1)
RX0, RX1, RY0, RY1, CZ = -2176, 2176, -1792, 1792, 2112
RZ = CZ + 16                                  # roof terrace floor (top of the ceiling slab)
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
TC = (0, 512)                                 # tree centre
RUG = (-1024, -1536, 512, -420)               # big rug x0, y0, x1, y1 (4u high)


def fz(x, y):
    """floor height at (x, y): 4 on the rug, else 0"""
    return 4 if RUG[0] <= x <= RUG[2] and RUG[1] <= y <= RUG[3] else 0


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x), round(y), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """(x,y) = where the model's bounding-box centre should land (several models have off-centre origins)"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, **kw):
    """mdl_c + a weapon-clip box around the model's rotated bounds so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    z1 = oz + b['max'][2] * scale
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - 4)), WCLIP))
    return e


def light(x, y, z, val, color='1 0.85 0.65', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), floor + 25), angle=ang)
    SPOTS['spawn'].append((x, y, floor))


def fit_top(b, x0, y0, x1, y1, tw, th, tex=None):
    for f in b.faces:
        if f.n[2] > 0.9:
            if tex: f.tex = tex
            sx = (x1 - x0) / tw; sy = (y1 - y0) / th
            f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def sign(mn, mx, tex, facing, tw, th, back=T('wallframe')):
    A(sign_box(mn, mx, T(tex), tw, th, back=back, facing=facing))


def ring_pts(cx, cy, r, z, n=16, ph=None):
    return [(x, y, z) for (x, y) in ngon(cx, cy, r, n, ph)]


def frustum(cx, cy, zb, zt, rb, rt, tex, n=16, ph=None):
    return hull(ring_pts(cx, cy, rb, zb, n, ph) + ring_pts(cx, cy, rt, zt, n, ph), tex, round_pts=False)


def sphere(cx, cy, cz, r, tex, n=8):
    pts = [(cx, cy, cz - r), (cx, cy, cz + r)]
    for zf, rf in ((-0.7, 0.71), (0, 1.0), (0.7, 0.71)):
        pts += [(cx + r * rf * math.cos(2 * math.pi * k / n), cy + r * rf * math.sin(2 * math.pi * k / n), cz + r * zf) for k in range(n)]
    return hull(pts, tex, round_pts=False)


def polar(r, ang_deg, c=TC):
    a = math.radians(ang_deg)
    return c[0] + r * math.cos(a), c[1] + r * math.sin(a)


def jumppad(x, y, z, land, apex, name, glow=True):
    """pad (r 34) + trigger_push + target_position. Q3 AimAtTarget: target = apex of the flight, measured from the trigger
    centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way to `land` (x, y, floor z)."""
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
    if glow: light(x, y, z + 48, 80, '1 0.6 0.3')


def gift(x0, y0, z0, x1, y1, z1, pat, bow=True, lidless=False):
    """wrapped present: an MD3 (rounded paper box, raised satin ribbons, looped bow) on an invisible clip box.
    lidless: an opened present (low walls with folded-out flaps, tissue inside); returns the inner floor height."""
    path, sc = XM.gift_model(x1 - x0, y1 - y0, z1 - z0 if not lidless else 96, pat, bow=bow, open=lidless)
    M.model(path, ((x0 + x1) / 2, (y0 + y1) / 2, z0), scale=sc, angle=0, spawnflags=4, _castshadows=1, _receiveshadows=1)
    if not lidless:
        A(box((x0, y0, z0), (x1, y1, z1), WCLIP))
        return z1
    w = 12
    z1 = z0 + 32
    for mn, mx in (((x0, y0, z0), (x1, y0 + w, z1)), ((x0, y1 - w, z0), (x1, y1, z1)), ((x0, y0 + w, z0), (x0 + w, y1 - w, z1)),
                   ((x1 - w, y0 + w, z0), (x1, y1 - w, z1))):
        A(box(mn, mx, WCLIP))
    fl = z0 + 16
    A(box((x0 + w, y0 + w, z0), (x1 - w, y1 - w, fl), WCLIP))
    return fl


def plate(x, y, z, r):
    """flat porcelain plate (a brush, so food models rest on a real surface)"""
    A(cyl(x, y, r, z, z + 6, {'top': T('porcelain'), 'side': T('porcelain'), 'bot': T('porcelain')}, 12))


def candle(x, y, z, r=14, h=96, tex='candle_red'):
    """MD3 candlestick (brass holder + dripping candle) with a flame sprite; total height h"""
    holder = h > 70
    ch = h - 30 if holder else h
    xm('candlestick', x, y, z, key=f'candle_{tex}_{r}_{ch}' + ('' if holder else '_nh'), h=ch, r=r, col=tex, holder=holder)
    flame(x, y, z + h + 4)


def flame(x, y, z):
    A(box((x - 1, y - 7, z), (x + 1, y + 7, z + 30), {'e': T('flame'), 'w': T('flame'), 'side': NODRAW, 'top': NODRAW, 'bot': NODRAW}))


# =================================================================================================== shell
def room_shell():
    W = 32
    def wall(mn, mx, inner):
        for (za, zb, tex) in ((0, 48, 'trim_white'), (48, 640, 'wainscot'), (640, 672, 'trim_white'), (672, CZ - 48, 'wallpaper'),
                              (CZ - 48, CZ, 'trim_white')):
            a, b = max(za, mn[2]), min(zb, mx[2])
            if b <= a: continue
            A(box((mn[0], mn[1], a), (mx[0], mx[1], b), {'side': CAULK, 'top': CAULK, 'bot': CAULK, inner: T(tex)}, detail=False))
    A(box((RX0 - W, RY0 - W, -16), (RX1 + W, RY1 + W, 0), {'top': T('floor_oak'), 'side': CAULK, 'bot': CAULK}, detail=False))
    # ceiling slab = roof terrace floor; hole for the chimney flue (x -2112..-1984, y -128..128)
    for r in sub_rects((RX0 - W, RY0 - W, RX1 + W, RY1 + W), [(-2112, -128, -1984, 128)]):
        A(box((r[0], r[1], CZ), (r[2], r[3], RZ), {'bot': T('ceiling'), 'side': CAULK, 'top': T('snow')}, detail=False))
    wall((RX0 - W, RY1, 0), (RX1 + W, RY1 + W, CZ), 's')
    wall((RX1, RY0, 0), (RX1 + W, RY1, CZ), 'w')
    wall((RX0 - W, RY0, 0), (RX0, RY1, CZ), 'e')
    # south wall with the window opening x -768..768, z 416..1600
    WX0, WX1, WZ0, WZ1 = -768, 768, 416, 1600
    wall((RX0 - W, RY0 - W, 0), (WX0, RY0, CZ), 'n')
    wall((WX1, RY0 - W, 0), (RX1 + W, RY0, CZ), 'n')
    wall((WX0, RY0 - W, 0), (WX1, RY0, WZ0 - 16), 'n')
    A(box((WX0, RY0 - W, WZ0 - 16), (WX1, RY0, WZ0), T('window_frame'), detail=False))          # sill
    wall((WX0, RY0 - W, WZ1), (WX1, RY0, CZ), 'n')


# =================================================================================================== the tree
TIERS = [  # zb, zt, r_bottom (lip), r_top (walkable ring edge)
    (352, 512, 960, 872),
    (672, 832, 760, 672),
    (992, 1152, 560, 472),
    (1312, 1472, 360, 288),
    (1632, 1712, 200, 168)]
NECKS = [256, 200, 144, 96]
RING = [((TIERS[i][3] + TIERS[i + 1][2]) / 2) for i in range(4)] + [0]      # centre of each open ring (sky above)


def ring_floor(i):
    return TIERS[i][1]


def tree():
    """the tree is one MD3 (xmas_models.tree): stand, trunk, five layered tiers with baubles, lights and tinsel.
    Collision = the old brush shapes as invisible weapon clip (walkable rings, lips, necks); the tree skirt stays a brush."""
    cx, cy = TC
    xm('tree', cx, cy, 0, tiers=tuple(TIERS), necks=tuple(NECKS), lm=2.0)
    with as_clip():
        A(cyl(cx, cy, 256, 0, 144, CAULK, 16))
        A(cyl(cx, cy, 112, 144, TIERS[0][0] - 32, CAULK, 12))
        for i, (zb, zt, rb, rt) in enumerate(TIERS):
            A(frustum(cx, cy, zb - 32, zb, rb, rb, CAULK, 16))
            A(frustum(cx, cy, zb, zt, rb, rt, CAULK, 16))
            if i < 4:
                A(cyl(cx, cy, NECKS[i], zt, TIERS[i + 1][0] - 32, CAULK, 12))
    # tree skirt (felt disc) around the stand
    inner, outer = ngon(cx, cy, 256, 16), ngon(cx, cy, 900, 16)
    for k in range(16):
        q = [inner[k], inner[(k + 1) % 16], outer[k], outer[(k + 1) % 16]]
        A(hull([(x, y, z) for (x, y) in q for z in (0, 4)], {'top': T('treeskirt'), 'side': T('rug_edge'), 'bot': CAULK}, round_pts=False))
    # ---- star on top: spinning MD3 (model2 of a func_rotating with a tiny nonsolid brush + origin brush)
    sz = TIERS[4][1] + 236
    path, _ = XM.get('star')
    M.ent('func_rotating', None, brushes=[box((cx - 8, cy - 8, sz - 8), (cx + 8, cy + 8, sz + 8), ORIGIN),
                                         box((cx - 4, cy - 4, sz - 4), (cx + 4, cy + 4, sz + 4), NODRAW_NS)],
          model2=path, speed=30, spawnflags=0)
    light(cx, cy - 100, sz, 700, '1 0.85 0.5')
    light(cx, cy + 100, sz, 500, '1 0.85 0.5')


def star_outline(cx, cz, r1, r2):
    """10 points of a 5-point star in the x-z plane, point up"""
    return [(cx + (r1 if k % 2 == 0 else r2) * math.sin(k * math.pi / 5), cz + (r1 if k % 2 == 0 else r2) * math.cos(k * math.pi / 5))
            for k in range(10)]


def tree_pads_and_loot():
    cx, cy = TC
    # floor -> tier 1 (four pads around the tree)
    for ang in (-90, 0, 180, 90):
        px, py = polar(1104, ang); lx, ly = polar(RING[0], ang)
        jumppad(px, py, fz(px, py), (lx, ly, ring_floor(0)), ring_floor(0) + 170, 'jp_t1_%d' % (ang % 360))
    # tier i -> tier i+1
    plan = {0: (45, 135, 225, 315), 1: (0, 180), 2: (90, 270), 3: (0,)}
    for i, angs in plan.items():
        for ang in angs:
            px, py = polar(RING[i], ang)
            if i < 3:
                lx, ly = polar(RING[i + 1], ang)
            else:
                lx, ly = polar(52, ang)
            jumppad(px, py, ring_floor(i), (lx, ly, ring_floor(i + 1)), ring_floor(i + 1) + (230 if i == 3 else 150), 'jp_t%d_%d' % (i + 2, ang), glow=False)
    # way down for bots (humans can also just jump): one pad per upper ring flings you out to the floor
    for (i, ang, r) in ((1, 240, None), (2, 315, None), (3, 225, None), (4, 225, 110)):
        px, py = polar(r or RING[i], ang)
        lx, ly = polar(1320, ang)
        jumppad(px, py, ring_floor(i), (lx, ly, fz(lx, ly)), ring_floor(i) + 90, 'jp_down%d' % (i + 1), glow=False)
    # loot: deeper under the boughs of each tier (ring floor, under the next tier's lip) + open ring spots
    U = lambda i: (NECKS[i] + TIERS[i + 1][2]) / 2        # radius under the next tier's lip
    # tier 1: Bubble G + armour shards + ammo
    weapon('bubbleg', *polar(U(0), -67), ring_floor(0), marker='orange')
    item('item_armor_shard', *polar(RING[0], 112), ring_floor(0))
    item('item_armor_shard', *polar(RING[0], 292), ring_floor(0))
    item('ammo_balloony', *polar(U(0), 157), ring_floor(0))
    item('ammo_pumper', *polar(U(0), 22), ring_floor(0))
    spawn(*polar(U(0), 247), ring_floor(0), 247 + 180)
    # tier 2: Boaster + Pad shield
    weapon('boaster', *polar(U(1), 90), ring_floor(1), marker='green')
    item('item_armor_padshield', *polar(U(1), 270), ring_floor(1))
    item('ammo_splasher', *polar(RING[1], 120), ring_floor(1))
    item('ammo_bubbleg', *polar(RING[1], 300), ring_floor(1))
    # tier 3: Splasher + Speedy
    weapon('splasher', *polar(U(2), 0), ring_floor(2), marker='blue')
    item('item_speedy', *polar(U(2), 180), ring_floor(2))
    item('ammo_betty', *polar(RING[2], 45), ring_floor(2))
    item('ammo_boaster', *polar(RING[2], 225), ring_floor(2))
    # tier 4: Betty + Visionless
    weapon('betty', *polar(RING[3], 180), ring_floor(3), marker='black')
    item('item_visionless', *polar(RING[3], 270 + 40), ring_floor(3))
    item('ammo_imperius', *polar(RING[3], 90 + 40), ring_floor(3))
    # top: Imperius + Pad Power
    weapon('imperius', *polar(96, 180), ring_floor(4), marker='purple')
    item('item_padpower', *polar(96, 270), ring_floor(4))


def under_tree():
    """presents under the lowest boughs (z 4..352), with walking lanes between them and a few opened ones"""
    cx, cy = TC
    z = 4
    pats = list(TX.GIFTS)
    taken = []                                  # footprints (x0, y0, x1, y1) incl. a walking margin
    def free(x0, y0, x1, y1, m=36):
        r_in = 256 + 24; r_out = 900 - 20        # stay on the skirt, off the stand
        for (cx_, cy_) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            d = math.hypot(cx_ - cx, cy_ - cy)
            if d < r_in or d > r_out: return False
        return all(x1 + m <= a0 or x0 - m >= a1 or y1 + m <= b0 or y0 - m >= b1 for (a0, b0, a1, b1) in taken)
    def place(ang, r, w, d):
        for dr in (0, 40, -40, 80, -80, 120, -120, 160, -160, 200):
            for da in (0, 6, -6, 12, -12, 18, -18, 24, -24, 30, -30):
                x, y = polar(r + dr, ang + da)
                x0, y0 = round(x - w / 2), round(y - d / 2)
                if free(x0, y0, x0 + w, y0 + d):
                    taken.append((x0, y0, x0 + w, y0 + d)); return x0, y0
        return None
    # opened presents first (they hold loot), then the wrapped ones around them
    for (ang, r, w, p, cls) in ((-160, 560, 192, 'trees', 'weapon_bubbleg'), (52, 440, 176, 'stripe', 'ammo_imperius'),
                                (215, 420, 160, 'blue', 'holdable_bambam')):
        pos = place(ang, r, w, w)
        if not pos: continue
        x0, y0 = pos
        fl = gift(x0, y0, z, x0 + w, y0 + w, z + 96, p, lidless=True)
        if cls.startswith('weapon_'): weapon(cls[7:], x0 + w / 2, y0 + w / 2, fl, marker='orange')
        else: item(cls, x0 + w / 2, y0 + w / 2, fl)
    # keep the loot / spawn spots below clear too
    for (ang, r) in ((100, 350), (270, 820), (-20, 830), (-80, 840), (60, 850), (200, 850)):
        x, y = polar(r, ang); taken.append((x - 40, y - 40, x + 40, y + 40))
    # unwrapped gifts lying around (catalog models), reserved with their real rotated footprint
    for (path, ang, r, rot) in (('pad_radio_car/radio_control.md3', -40, 400, 30), ('pad_actionfigures/fig_lilly.md3', -95, 860, 250),
                                ('pad_actionfigures/fig_girl.md3', 140, 870, 320), ('pad_nascars/padcar_muster_rc.md3', 250, 700, 60),
                                ('pad_ball/pad_soccerball.md3', 45, 860, 0), ('pad_ddmix/attic/kaspad.md3', 140, 380, 200),
                                ('gummybears/ldredbear.md3', 300, 400, 10)):
        b = BOUNDS['models/mapobjects/' + path]
        a = math.radians(rot)
        hx = abs((b['max'][0] - b['min'][0]) / 2 * math.cos(a)) + abs((b['max'][1] - b['min'][1]) / 2 * math.sin(a))
        hy = abs((b['max'][0] - b['min'][0]) / 2 * math.sin(a)) + abs((b['max'][1] - b['min'][1]) / 2 * math.cos(a))
        pos = place(ang, r, 2 * hx + 8, 2 * hy + 8)
        if pos: mdl_c(path, pos[0] + hx + 4, pos[1] + hy + 4, z, angle=rot)
    layout = [  # angle, radius, w, d, h, pattern
        (-110, 520, 224, 192, 176, 'red'), (-60, 600, 160, 160, 128, 'stripe'), (-20, 470, 256, 192, 208, 'green'),
        (30, 640, 192, 160, 144, 'gold'), (75, 480, 224, 224, 192, 'blue'), (120, 620, 176, 144, 112, 'dots'),
        (160, 470, 256, 176, 200, 'trees'), (200, 640, 160, 192, 160, 'kraft'), (245, 520, 192, 192, 240, 'red'),
        (290, 660, 144, 144, 96, 'green'), (-140, 740, 128, 128, 112, 'blue'), (95, 760, 128, 112, 96, 'gold'),
        (180, 780, 112, 128, 80, 'stripe'), (10, 800, 144, 112, 96, 'dots'), (320, 520, 160, 128, 144, 'gold'),
        (-5, 640, 128, 128, 160, 'kraft'), (90, 420, 192, 160, 176, 'stripe'), (110, 560, 160, 160, 144, 'green'),
        (65, 700, 160, 128, 128, 'red'), (135, 800, 128, 128, 112, 'blue'), (-30, 330, 128, 128, 160, 'gold'),
        (230, 760, 144, 128, 128, 'dots'), (175, 330, 128, 112, 144, 'red')]
    for (ang, r, w, d, h, p) in layout:
        pos = place(ang, r, w, d)
        if not pos: continue
        x0, y0 = pos
        stack = (p == 'red' and h > 200)
        gift(x0, y0, z, x0 + w, y0 + d, z + h, p, bow=not stack)
        if stack:     # a little one on top
            gift(x0 + 32, y0 + 40, z + h, x0 + 32 + 96, y0 + 40 + 80, z + h + 64, 'gold')
    item('ammo_pumper', *polar(350, 100), z)
    item('item_armor_shard', *polar(820, 270), z)
    item('ammo_nipper', *polar(830, -20), z)
    # fairy lights under the boughs (the tree MD3 casts shadows, so the cave needs its own light)
    for k, col in enumerate(('1 0.6 0.4', '1 0.85 0.5', '0.6 0.8 1', '1 0.5 0.5', '0.7 1 0.6', '1 0.75 0.45')):
        a = math.radians(30 + 60 * k)
        light(cx + 560 * math.cos(a), cy + 560 * math.sin(a), 300, 520, col)
    light(cx, cy, 300, 400, '1 0.8 0.6')
    for (ang, r) in ((-80, 840), (60, 850), (200, 850)):
        spawn(*polar(r, ang), z, (ang + 180) % 360)


# =================================================================================================== fireplace + roof
FB = dict(x0=-2112, x1=-1888, y0=-320, y1=320, z1=480)          # firebox interior
FLUE = (-2112, -128, -1984, 128)


def fireplace():
    BX0, BX1, BY0, BY1 = RX0, -1888, -704, 704
    br = T('brick')
    bt = {'side': br, 'top': br, 'bot': br}
    A(box((BX0, BY0, 0), (BX1, FB['y0'], CZ), bt))                    # left of the opening
    A(box((BX0, FB['y1'], 0), (BX1, BY1, CZ), bt))                    # right
    A(box((BX0, FB['y0'], 0), (FB['x0'], FB['y1'], CZ), {'side': T('brick_soot'), 'top': br, 'bot': br}))   # back
    # lintel with the flue hole
    A(box((FLUE[2], FB['y0'], FB['z1']), (BX1, FB['y1'], CZ), {'side': br, 'bot': T('brick_soot'), 'w': T('brick_soot')}))
    A(box((FB['x0'], FB['y0'], FB['z1']), (FLUE[2], FLUE[1], CZ), {'side': br, 'bot': T('brick_soot'), 'n': T('brick_soot')}))
    A(box((FB['x0'], FLUE[3], FB['z1']), (FLUE[2], FB['y1'], CZ), {'side': br, 'bot': T('brick_soot'), 's': T('brick_soot')}))
    # firebox floor + hearth
    A(box((FB['x0'], FB['y0'], 0), (FB['x1'], FB['y1'], 16), {'top': T('soot'), 'side': T('stone')}))
    A(box((BX1, -608, 0), (-1632, 608, 16), T('stone')))
    # carved mantel (MD3: shelf, moulding, scroll corbels, fluted pilasters down to the hearth); clip = shelf + pilasters
    xm('mantel', BX1, 0, 560, lm=1.0)
    A(box((BX1, -768, 640), (-1792, 768, 688), WCLIP))
    for (ya, yb) in ((-406, -314), (314, 406)):
        A(box((BX1, ya, 16), (BX1 + 30, yb, 560), WCLIP))
    # painting above the mantel in a gilt MD3 frame
    sign((BX1, -384, 880), (BX1 + 8, 384, 1360), 'painting', 'e', 512, 320, back=T('wallframe'))
    xm('frame', BX1, 0, 880, key='frame_painting', w=768, h=480)
    # iron fire basket with logs (MD3, nonsolid - you can walk into the fire), fire sprites, embers
    xm('fire_grate', -2010, 0, 16)
    A(box((-2060, -150, 16), (-1950, 150, 20), T('embers')))
    for (x, y0, y1, z0, z1) in ((-2016, -150, -50, 30, 250), (-2010, -60, 60, 36, 300), (-2016, 50, 150, 30, 240),
                                (-1996, -110, -10, 40, 220), (-1996, 10, 110, 40, 230)):
        A(box((x - 1, y0, z0), (x + 1, y1, z1), {'e': T('fire'), 'w': T('fire'), 'side': NODRAW, 'top': NODRAW, 'bot': NODRAW}))
    light(-1940, 0, 160, 1400, '1 0.5 0.18')
    light(-1820, 0, 260, 900, '1 0.55 0.25')
    light(-1700, -400, 200, 400, '1 0.55 0.25'); light(-1700, 400, 200, 400, '1 0.55 0.25')
    speaker(-2000, 0, 100, 'sound/world/ambient/fire_crackling.ogg')
    # walk into the flames -> up the chimney (teleport to the roof terrace)
    M.ent('trigger_teleport', brushes=[box((-2096, -144, 20), (-1960, 144, 120), TRIG)], target='tp_roof')
    M.ent('misc_teleporter_dest', (-1700, 0, RZ + 24), targetname='tp_roof', angle=0)
    # hearth pad up onto the mantel
    jumppad(-1700, 420, 16, (-1830, 420, 688), 880, 'jp_mantel')
    weapon('pumper', -1720, -400, 16, marker='green')
    item('ammo_nipper', -1680, 120, 16)
    # mantel: candles, clock, nutcrackers, cards, stockings, garland
    Z = 688
    for y in (-720, -640, 640, 720):
        candle(-1866, y, Z, 12, 80 + (abs(y) % 3) * 12, 'candle_white')
    xm('mantel_clock', -1868, 0, Z)                                                  # arched mantel clock
    A(box((-1888, -80, Z), (-1848, 80, Z + 120), WCLIP))
    nutcracker(-1863, -300, Z, 0.6)
    nutcracker(-1863, 300, Z, 0.6, coat='nut_blue')
    for (y, c) in ((-200, 0), (180, 1), (230, 2)):
        A(sign_box((-1880, y - 24, Z), (-1876, y + 24, Z + 72), T('card%d' % c), 128, 192, back=T('wood_light'), facing='e'))
    mdl_c('pad_ddmix/jail/matches_closed.md3', -1845, -470, Z, angle=0)
    item('holdable_boomies', -1815, -160, Z)
    item('ammo_bubbleg', -1815, 540, Z)
    item('ammo_splasher', -1815, 140, Z)
    # stockings hanging from brass hooks on the mantel edge (MD3, nonsolid)
    for (y, col, toe) in ((-660, 'velvet_red', 1), (-540, 'velvet_green', 1), (560, 'velvet_green', -1), (680, 'velvet_red', -1)):
        xm('stocking', -1792, y, 640, key=f'stocking_{col}_{toe}', col=col, toe=toe)
    # pine garland swagging along the mantel front
    xm('garland', -1786, 0, 646)
    # Santa's milk and cookies on a little stool by the hearth + fire tools
    xm('stool', -1560, -760, 0)
    A(cyl(-1560, -760, 96, 0, 200, WCLIP, 12))
    plate(-1565, -740, 200, 60)
    mdl_c('pad_ddmix/diner/muffin_choco.md3', -1575, -735, 206)
    mdl_c('pad_ddmix/diner/muffin_blueberry.md3', -1545, -760, 206, angle=90)
    mdl_c('pad_ddmix/diner/glass_simple.md3', -1530, -800, 200)
    A(box((-1600, -856, 200), (-1520, -820, 202), T('letter')))
    xm('fire_tools', -1700, 760, 0)
    A(cyl(-1700, 760, 40, 0, 24, WCLIP, 8)); A(box((-1716, 744, 24), (-1684, 776, 380), WCLIP))


def nutcracker(x, y, z, s=1.0, coat='nut_red'):
    """wooden nutcracker soldier (MD3, 300 tall at s 1) facing into the room (+x) + a clip block"""
    xm('nutcracker', x, y, z, key=f'nutcracker_{coat}', coat=coat, scale=s, angle=0)
    q = lambda v: round(v * s)
    A(box((x - q(40), y - q(40), z), (x + q(40), y + q(40), z + q(300)), WCLIP))


def roof():
    """snowy roof terrace above the fireplace (sky box: x -2560..-640, y -1536..1536, z RZ..3200)"""
    S = T('sky')
    x0, x1, y0, y1, z1 = -2560, -640, -1536, 1536, 3200
    A(box((x0 - 16, y0 - 16, CZ), (RX0 - 32, y1 + 16, RZ), S, detail=False))          # sky floor west of the house
    for mn, mx in (((x0 - 16, y0 - 16, RZ), (x0, y1 + 16, z1)), ((x1, y0 - 16, RZ), (x1 + 16, y1 + 16, z1)),
                   ((x0, y0 - 16, RZ), (x1, y0, z1)), ((x0, y1, RZ), (x1, y1 + 16, z1)),
                   ((x0 - 16, y0 - 16, z1), (x1 + 16, y1 + 16, z1 + 16))):
        A(box(mn, mx, S, detail=False))
    # terrace x -2176..-960, y -1088..1088; sloped roofs falling away around it
    TX0, TX1, TY0, TY1 = RX0, -960, -1088, 1088
    rt = {'top': T('roof_tiles_snow'), 'side': T('house_wall'), 'bot': CAULK}
    A(ramp(TX1, y0, x1, y1, RZ, RZ + 64, RZ, 'e', rt))
    A(ramp(x0, TY1, TX1, y1, RZ, RZ + 64, RZ, 'n', rt))
    A(ramp(x0, y0, TX1, TY0, RZ, RZ + 64, RZ, 's', rt))
    A(ramp(x0, TY0, TX0 - 32, TY1, RZ, RZ + 64, RZ, 'w', rt))
    # parapet (48 high, never blocks shots) + clip above it
    P = {'side': T('house_wall'), 'top': T('snow')}
    A(box((TX1 - 32, TY0, RZ + 64), (TX1, TY1, RZ + 112), P))
    A(box((TX0 - 32, TY1 - 32, RZ + 64), (TX1 - 32, TY1, RZ + 112), P))
    A(box((TX0 - 32, TY0, RZ + 64), (TX1 - 32, TY0 + 32, RZ + 112), P))
    A(box((TX0 - 64, TY0 + 32, RZ + 64), (TX0 - 32, TY1 - 32, RZ + 112), P))
    for mn, mx in (((TX1 - 32, TY0, RZ + 112), (TX1, TY1, RZ + 600)), ((TX0 - 64, TY1 - 32, RZ + 112), (TX1 - 32, TY1, RZ + 600)),
                   ((TX0 - 64, TY0, RZ + 112), (TX1 - 32, TY0 + 32, RZ + 600)), ((TX0 - 64, TY0 + 32, RZ + 112), (TX0 - 32, TY1 - 32, RZ + 600))):
        A(box(mn, mx, CLIP))
    # the terrace floor west strip x -2208..-2176 (over the wall) is the ceiling slab; walls of the room end at CZ.
    # chimney stack around the flue
    br = T('brick')
    for mn, mx in (((RX0, -320, RZ), (FLUE[0], 320, RZ + 368)), ((FLUE[2], -320, RZ), (-1888, 320, RZ + 368)),
                   ((FLUE[0], -320, RZ), (FLUE[2], FLUE[1], RZ + 368)), ((FLUE[0], FLUE[3], RZ), (FLUE[2], 320, RZ + 368))):
        A(box(mn, mx, {'side': br, 'top': T('snow'), 'bot': br}))
    A(box((-2048 - 1, -60, RZ + 380), (-2048 + 1, 60, RZ + 620), {'e': T('smoke'), 'w': T('smoke'), 'side': NODRAW, 'top': NODRAW, 'bot': NODRAW}))
    # Santa's sleigh (step in from the back), sack, two reindeer, snowman
    sleigh(-2000, -880, -1440, -560)
    reindeer(-1220, -800, rudolph=True)
    reindeer(-1220, -640)
    for yy in (-800, -640):
        A(box((-1400, yy - 3, RZ + 150), (-1304, yy + 3, RZ + 156), T('wire_ns')))         # harness lines
    solid_mdl('pad_ddmix/jail/snowman.md3', -1400, 700, RZ, scale=2.0, angle=200)
    for (x, y) in ((-1100, 200), (-1900, 900), (-1150, -200)):
        A(hull([(x - 90, y - 60, RZ), (x + 90, y - 60, RZ), (x - 90, y + 60, RZ), (x + 90, y + 60, RZ), (x - 40, y - 20, RZ + 36), (x + 40, y + 20, RZ + 36)],
               T('snow_drift')))
    # teleporter home (lands under the tree's east side)
    mdl_c('pad_teleporter/padtp_blue.md3', -1150, 700, RZ, scale=0.6)
    M.ent('trigger_teleport', brushes=[box((-1190, 660, RZ), (-1110, 740, RZ + 80), TRIG)], target='tp_home')
    M.ent('misc_teleporter_dest', (1250, 900, 24), targetname='tp_home', angle=180)
    # secret found jingle on arrival
    speaker(-1600, 0, RZ + 80, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret')
    M.ent('trigger_multiple', brushes=[box((-1600, -120, RZ), (-1560, 120, RZ + 96), TRIG)], target='secret', wait=20)
    speaker(-1500, 0, RZ + 300, 'sound/world/ambient/wind_icy.ogg')
    speaker(-1300, -600, RZ + 200, 'sound/world/misc/wind_chimes.ogg', loop=False, targetname='jingle')
    M.ent('func_timer', (-1300, -600, RZ + 260), target='jingle', wait=20, random=8, spawnflags=1)
    # loot
    item('holdable_killerducks', -1772, -720, RZ + 64)
    item('item_revival', -1300, 300, RZ)
    item('ammo_imperius', -1800, 700, RZ)
    item('ammo_boaster', -1200, -300, RZ)
    item('ammo_betty', -1880, -720, RZ + 64)
    spawn(-1200, 0, RZ, 180)
    light(-1550, 0, RZ + 420, 900, '0.7 0.8 1')
    light(-1550, -700, RZ + 300, 500, '1 0.85 0.6')
    snowfall_sheets([(-2400, -1400, -800, -1400), (-2400, 1400, -800, 1400), (-800, -1400, -800, 1400)], RZ, RZ + 900)


def sleigh(x0, y0, x1, y1):
    """Santa's sleigh: MD3 (xmas_models.sleigh) + sack MD3 + a present; collision = the old brush shapes as clip"""
    xm('sleigh', (x0 + x1) / 2, (y0 + y1) / 2, RZ, lm=1.0)
    fz = RZ + 64
    sx, sy = x1 - 190, (y0 + y1) / 2
    xm('sack', sx, sy, fz, key='sack_sleigh', rx=88, ry=106, h=200, gifts=False, seed=3)
    with as_clip():
        sleigh_collision(x0, y0, x1, y1)
    gift(round(sx - 24), round(sy - 22), fz + 200, round(sx + 24), round(sy + 22), fz + 252, 'red', bow=False)


def sleigh_collision(x0, y0, x1, y1):
    R, G = T('sleigh_red'), T('trim_gold')
    fz = RZ + 64                    # sleigh floor top (+48 step at the back = 2 x 32u steps for bots... 16+48)
    # runners
    for (ya, yb) in ((y0 + 24, y0 + 48), (y1 - 48, y1 - 24)):
        A(box((x0, ya, RZ), (x1 + 40, yb, RZ + 16), G))
        A(hull([(x1 + 40, ya, RZ), (x1 + 40, yb, RZ), (x1 + 40, ya, RZ + 16), (x1 + 40, yb, RZ + 16), (x1 + 120, ya, RZ + 96), (x1 + 120, yb, RZ + 96),
                (x1 + 104, ya, RZ + 112), (x1 + 104, yb, RZ + 112)], G))
        for xs in (x0 + 64, (x0 + x1) / 2, x1 - 64):
            A(box((round(xs) - 8, ya, RZ + 16), (round(xs) + 8, yb, fz - 16), G))
    A(box((x0, y0, fz - 16), (x1, y1, fz), {'side': G, 'top': T('velvet_red'), 'bot': G}))          # floor
    A(box((x0, y0, fz), (x1, y0 + 24, fz + 160), R)); A(box((x0, y1 - 24, fz), (x1, y1, fz + 160), R))   # sides
    A(hull([(x1 - 96, y0 + 24, fz), (x1 - 96, y1 - 24, fz), (x1, y0 + 24, fz), (x1, y1 - 24, fz), (x1 - 96, y0 + 24, fz + 160),
            (x1 - 96, y1 - 24, fz + 160), (x1 + 40, y0 + 24, fz + 240), (x1 + 40, y1 - 24, fz + 240)], R))                # curled front
    A(box((x0, y0, fz + 160), (x1, y0 + 24, fz + 176), G)); A(box((x0, y1 - 24, fz + 160), (x1, y1, fz + 176), G))
    for (ya, yb) in ((y0 + 24, y0 + 56), (y1 - 56, y1 - 24)):                                   # side cushions
        A(box((x0 + 96, ya, fz), (x0 + 256, yb, fz + 48), T('velvet_red')))
    # step at the open back
    A(box((x0 - 64, y0 + 64, RZ), (x0, y1 - 64, RZ + 32), G))
    # sack of presents at the front
    sx, sy = x1 - 190, (y0 + y1) / 2
    pts = []
    for (zf, rf) in ((0, 0.8), (0.4, 1.0), (0.8, 0.8), (1.0, 0.55)):
        pts += [(sx + 90 * rf * math.cos(2 * math.pi * k / 10), sy + 110 * rf * math.sin(2 * math.pi * k / 10), fz + 200 * zf) for k in range(10)]
    A(hull(pts, T('burlap'), round_pts=False))


def reindeer(x, y, rudolph=False):
    """reindeer MD3 facing +x, collision = the old blocky shape as clip"""
    xm('reindeer', x, y, RZ, key='rudolph' if rudolph else 'reindeer', rudolph=rudolph)
    with as_clip():
        reindeer_collision(x, y)


def reindeer_collision(x, y):
    B, L = T('reindeer'), T('reindeer_light')
    z = RZ
    for (dx, dy) in ((-60, -24), (-60, 24), (60, -24), (60, 24)):
        A(box((x + dx - 10, y + dy - 10, z), (x + dx + 10, y + dy + 10, z + 104), B))
    A(box((x - 70, y - 36, z + 104), (x + 70, y + 36, z + 120), L))
    A(box((x - 84, y - 40, z + 120), (x + 84, y + 40, z + 200), B))
    A(hull([(x + 50, y - 18, z + 200), (x + 50, y + 18, z + 200), (x + 84, y - 18, z + 200), (x + 84, y + 18, z + 200),
            (x + 80, y - 16, z + 260), (x + 80, y + 16, z + 260), (x + 104, y - 16, z + 260), (x + 104, y + 16, z + 260)], B))
    A(box((x + 76, y - 22, z + 260), (x + 132, y + 22, z + 300), B))
    A(box((x + 132, y - 8, z + 270), (x + 148, y + 8, z + 286), T('nose_red')))
    for sg in (-1, 1):
        A(box((x + 84, y + sg * 22 - 4, z + 300), (x + 92, y + sg * 22 + 4, z + 360), T('antler')))
        A(box((x + 70, y + sg * 22 - 4, z + 340), (x + 84, y + sg * 22 + 4, z + 348), T('antler')))
        A(box((x + 92, y + sg * 22 - 4, z + 330), (x + 110, y + sg * 22 + 4, z + 338), T('antler')))
    A(box((x - 98, y - 8, z + 170), (x - 84, y + 8, z + 196), L))


def snowfall_sheets(segs, z0, z1):
    for (xa, ya, xb, yb) in segs:
        if xa == xb: A(box((xa - 1, min(ya, yb), z0), (xa + 1, max(ya, yb), z1), T('snowfall')))
        else: A(box((min(xa, xb), ya - 1, z0), (max(xa, xb), ya + 1, z1), T('snowfall')))


# =================================================================================================== window + garden
def window_garden():
    WX0, WX1, WZ0, WZ1 = -768, 768, 416, 1600
    Y = RY0
    fr = T('window_frame')
    A(box((-16, Y - 28, WZ0), (16, Y - 4, WZ1), fr))
    A(box((WX0, Y - 28, 992), (-16, Y - 4, 1024), fr)); A(box((16, Y - 28, 992), (WX1, Y - 4, 1024), fr))
    for (xa, xb) in ((WX0, -16), (16, WX1)):
        for (za, zb) in ((WZ0, 992), (1024, WZ1)):
            A(box((xa, Y - 18, za), (xb, Y - 14, zb), T('glass')))
    # window seat (panelled box) with an MD3 tartan cushion + velvet pillows
    A(box((WX0, Y, 0), (WX1, Y + 256, 352), {'side': T('wood_light'), 'top': T('wood_light')}))
    xm('seat_cushion', 0, Y + 128, 352, angle=90, L=WX1 - WX0 - 32, D=224, h=32)
    A(box((WX0 + 16, Y + 16, 352), (WX1 - 16, Y + 240, 384), WCLIP))
    for xc in (-600, 560):
        xm('bolster', xc, Y + 44, 384, angle=90)
    item('item_climber', -200, Y + 140, 384)
    item('ammo_splasher', 300, Y + 150, 384)
    item('ammo_pumper', -420, Y + 150, 384)
    spawn(100, Y + 150, 384, 90)
    jumppad(0, -1478, 4, (0, Y + 140, 384), 600, 'jp_window')
    # velvet curtains with gold tie-backs (MD3) on a brass rod with two Christmas bells on a red bow
    for (xa, xb) in ((-960, -800), (800, 960)):
        xm('curtain', (xa + xb) / 2, Y, 0, angle=90)
        A(box((xa, Y, 0), (xb, Y + 48, 1720), WCLIP))
    xm('curtain_rod', 0, Y + 60, 1728, angle=90)
    # ---- garden outside (sky box y -3600..-1824)
    S = T('sky')
    gx0, gx1, gy0, gy1, gz0, gz1 = -2800, 2800, -3800, RY0 - 32, -112, 2700
    for mn, mx in (((gx0 - 16, gy0 - 16, gz0 - 16), (gx1 + 16, gy1, gz0)), ((gx0 - 16, gy0 - 16, gz1), (gx1 + 16, gy1, gz1 + 16)),
                   ((gx0 - 16, gy0, gz0), (gx0, gy1, gz1)), ((gx1, gy0, gz0), (gx1 + 16, gy1, gz1)),
                   ((gx0 - 16, gy0 - 16, gz0), (gx1 + 16, gy0, gz1))):
        A(box(mn, mx, S, detail=False))
    A(box((gx0, gy1 - 16, gz0), (gx1, gy1, gz1), {'s': T('house_wall'), 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((gx0, gy0, gz0), (gx1, gy1 - 16, -64), {'top': T('snow'), 'side': CAULK, 'bot': CAULK}))
    for (x, y, w, h) in ((-1400, -2500, 500, 120), (900, -2300, 700, 90), (-320, -3050, 500, 140)):
        A(hull([(x - w, y - w * 0.6, -64), (x + w, y - w * 0.6, -64), (x - w, y + w * 0.6, -64), (x + w, y + w * 0.6, -64),
                (x - w * 0.4, y - w * 0.2, -64 + h), (x + w * 0.4, y + w * 0.2, -64 + h)], T('snow_drift')))
    mdl_c('pad_ddmix/jail/snowman.md3', 0, -2450, -64, scale=6.0, angle=250)
    mdl_c('pad_ddmix/trashcan/tree_winter.md3', -1500, -3000, -64, scale=3.4, angle=30)
    mdl_c('pad_ddmix/trashcan/tree_winter.md3', 2150, -2450, -64, scale=2.2, angle=200)
    mdl_c('pad_ddmix/trashcan/tree_winter.md3', -2300, -2300, -64, scale=2.6, angle=120)
    mdl_c('pad_ddmix/trashcan/lamp_house_night.md3', -500, -2350, -64, scale=3.0, angle=270)
    for k in range(14):                                          # garden fence
        fx = -2600 + k * 380
        A(box((fx, -3500, -64), (fx + 40, -3460, 420), T('fence')))
        if k < 13:
            for (za, zb) in ((120, 170), (300, 350)):
                A(box((fx + 40, -3500, za), (fx + 380, -3480, zb), T('fence')))
    snowfall_sheets([(-1500, -2000, 1500, -2000), (-2400, -2600, 2400, -2600), (-2600, -3300, 2600, -3300)], -64, 2600)
    light(0, -2400, 1500, 2600, '0.6 0.7 1')


# =================================================================================================== NW: armchair, side table, clock
def nw_corner():
    # wingback armchair facing south (MD3), footstool, side table with cocoa, floor lamp, grandfather clock
    X0, X1, Y0, Y1 = -1760, -1312, 960, 1376
    xm('armchair', (X0 + X1) / 2, (Y0 + Y1) / 2, 0, angle=270, lm=1.0)
    with as_clip():
        A(box((X0, Y0, 0), (X1, Y1, 224), CAULK))
        A(box((X0 + 64, Y0 + 16, 224), (X1 - 64, Y1 - 96, 272), CAULK))
        A(box((X0, Y1 - 96, 224), (X1, Y1, 720), CAULK))
        for (xa, xb) in ((X0, X0 + 64), (X1 - 64, X1)):
            A(box((xa, Y0, 224), (xb, Y1 - 96, 400), CAULK))
    item('ammo_betty', -1200, 1050, 0)
    xm('footstool', -1530, 810, 0)
    A(box((-1660, 720, 0), (-1400, 900, 112), WCLIP))
    item('ammo_boaster', -1300, 760, 0)
    # side table: cocoa, cookies, pipe, poinsettia
    xm('side_table', -1140, 1300, 0)
    with as_clip():
        A(cyl(-1140, 1300, 128, 304, 336, CAULK, 16))
        A(cyl(-1140, 1300, 24, 32, 304, CAULK, 8))
        A(cyl(-1140, 1300, 96, 0, 32, CAULK, 12))
    mdl_c('pad_cups/pad_cup05.md3', -1100, 1240, 336, angle=200)
    plate(-1170, 1350, 336, 56)
    for (dx, dy) in ((-20, 10), (20, -10), (5, 30)):
        mdl_c('pad_fruits/walnut.md3', -1170 + dx, 1350 + dy, 342)
    mdl_c('pad_ddmix/padlibrary/pipe.md3', -1100, 1370, 336, angle=60)
    xm('poinsettia', -1190, 1236, 336)
    # floor lamp (warm glow) behind the chair
    xm('floor_lamp', -1600, 1600, 0)
    A(cyl(-1600, 1600, 80, 0, 24, WCLIP, 12)); A(box((-1610, 1590, 24), (-1590, 1610, 1240), WCLIP))
    light(-1600, 1600, 1200, 900, '1 0.8 0.55')
    # grandfather clock in the corner (face south) with a swinging pendulum behind glass
    cx0, cx1, cy0, cy1 = -2144, -1936, 1568, 1760
    xm('grandfather_clock', (cx0 + cx1) / 2, (cy0 + cy1) / 2, 0, angle=270, w=cx1 - cx0, d=cy1 - cy0)
    with as_clip():
        A(box((cx0, cy0, 0), (cx1, cy1, 160), CAULK))
        A(box((cx0, cy0, 1120), (cx1, cy1, 1480), CAULK))
        A(hull([(cx0 - 16, cy0 - 16, 1480), (cx1 + 16, cy0 - 16, 1480), (cx0 - 16, cy1, 1480), (cx1 + 16, cy1, 1480),
                (cx0 + 40, cy0 - 16, 1600), (cx1 - 40, cy0 - 16, 1600), (cx0 + 40, cy1, 1600), (cx1 - 40, cy1, 1600)], CAULK))
        A(box((cx0, cy1 - 24, 160), (cx1, cy1, 1120), CAULK))
        A(box((cx0, cy0 + 24, 160), (cx0 + 24, cy1 - 24, 1120), CAULK)); A(box((cx1 - 24, cy0 + 24, 160), (cx1, cy1 - 24, 1120), CAULK))
        A(box((cx0, cy0, 160), (cx1, cy0 + 8, 1120), CAULK))
        A(box((cx0, cy0 + 8, 160), (cx0 + 24, cy0 + 24, 1120), CAULK)); A(box((cx1 - 24, cy0 + 8, 160), (cx1, cy0 + 24, 1120), CAULK))
    px, py, pz = (cx0 + cx1) / 2, (cy0 + cy1) / 2, 1100
    br = [box((round(px) - 8, round(py) - 8, pz - 8), (round(px) + 8, round(py) + 8, pz + 8), ORIGIN),
          box((round(px) - 3, round(py) - 3, 420), (round(px) + 3, round(py) + 3, pz - 8), T('brass_ns')),
          cyl(round(px), round(py), 44, 380, 420, T('brass_ns'), 10)]
    M.ent('func_pendulum', None, brushes=br, speed=18, angle=90)
    speaker(px, py - 120, 900, 'sound/world/machine/clock_ticking.ogg')
    light(px, cy0 - 60, 700, 120, '1 0.85 0.6')
    spawn(-1700, 700, 0, 315)
    M.ent('station_health', (-1240, 900, 0), angle=225)


# =================================================================================================== NE: sideboard
def sideboard():
    X0, X1, Y0, Y1 = 1216, 2144, 1488, 1792
    xm('sideboard', (X0 + X1) / 2, (Y0 + Y1) / 2, 0, angle=270, L=X1 - X0, D=Y1 - Y0, lm=1.0)
    with as_clip():
        A(box((X0, Y0, 0), (X1, Y1, 560), CAULK))
        A(box((X0 - 16, Y0 - 16, 560), (X1, Y1, 592), CAULK))
    Z = 592
    # Christmas pyramid: static base with candles (MD3) + a rotating carousel (MD3 model2 on a func_rotating)
    pcx, pcy = 1680, 1650
    xm('pyramid_base', pcx, pcy, Z)
    A(cyl(pcx, pcy, 112, Z, Z + 24, WCLIP, 12))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        flame(round(pcx + 90 * math.cos(a)), round(pcy + 90 * math.sin(a)), Z + 84)
    path, _ = XM.get('pyramid_rotor')
    M.ent('func_rotating', None, brushes=[box((pcx - 8, pcy - 8, Z + 200), (pcx + 8, pcy + 8, Z + 216), ORIGIN),
                                         box((pcx - 4, pcy - 4, Z + 204), (pcx + 4, pcy + 4, Z + 212), NODRAW_NS)],
          model2=path, speed=24, spawnflags=0)
    # snow globe
    gx, gy = 1380, 1640
    xm('snow_globe', gx, gy, Z)
    A(cyl(gx, gy, 72, Z, Z + 180, WCLIP, 12))
    nutcracker(1980, 1640, Z, 0.9)
    nutcracker(2080, 1640, Z, 0.9, coat='nut_blue')
    mdl_c('pad_cake/pad_cakestand.md3', 1540, 1560, Z)
    item('holdable_floater', 1840, 1560, Z)
    item('ammo_splasher', 1300, 1540, Z)
    jumppad(1680, 1260, 0, (1840, 1560, Z), Z + 170, 'jp_sideboard')
    # advent calendar + wreath on the north wall
    sign((1500, RY1 - 6, 900), (1884, RY1, 1412), 'advent', 's', 384, 512)
    wreath(1100, RY1, 1300, 270)
    light(1680, 1500, 980, 600, '1 0.8 0.6')
    speaker(1680, 1650, 700, 'sound/world/misc/wind_chimes.ogg', loop=False, targetname='chime_ne')
    M.ent('func_timer', (1680, 1650, 760), target='chime_ne', wait=45, random=15, spawnflags=1)


def wreath(x, y, z, angle):
    """MD3 pine wreath with berries, cones and a red bow; (x, y) = point on the wall, angle = direction into the room"""
    xm('wreath', x, y, z, angle=angle)


# =================================================================================================== east: sofa + coffee table
def sofa_corner():
    X0, X1, Y0, Y1 = 1728, 2176, -448, 576
    xm('sofa', (X0 + X1) / 2, (Y0 + Y1) / 2, 0, angle=180, L=Y1 - Y0, D=X1 - X0, lm=1.0)
    with as_clip():
        A(box((X0, Y0, 0), (X1, Y1, 256), CAULK))
        A(box((1984, Y0 + 128, 256), (X1, Y1 - 128, 640), CAULK))                     # back
        for (ya, yb) in ((Y0, Y0 + 128), (Y1 - 128, Y1)):
            A(box((X0, ya, 256), (X1, yb, 416), CAULK))                             # arms
        A(box((X0 + 16, Y0 + 128, 256), (1984, Y1 - 128, 288), CAULK))              # seat cushion
    item('ammo_boaster', 1850, 60, 288)
    spawn(1860, -200, 288, 180)
    jumppad(1830, 140, 288, (2080, 140, 640), 820, 'jp_sofaback', glow=False)
    jumppad(1520, -620, 0, (1850, 400, 288), 470, 'jp_sofa')
    item('ammo_betty', 2080, -150, 640)
    item('item_jumper', 2080, 400, 640)
    # wreath above the sofa
    wreath(RX1, 64, 1200, 180)
    # coffee table with an Advent wreath (4 candles), cocoa, cookies (decoration only)
    TX0, TX1, TY0, TY1 = 1216, 1600, -224, 320
    xm('coffee_table', (TX0 + TX1) / 2, (TY0 + TY1) / 2, 0, w=TX1 - TX0, d=TY1 - TY0)
    with as_clip():
        for (x, y) in ((TX0 + 16, TY0 + 16), (TX1 - 48, TY0 + 16), (TX0 + 16, TY1 - 48), (TX1 - 48, TY1 - 48)):
            A(box((x, y, 0), (x + 32, y + 32, 288), CAULK))
        A(box((TX0, TY0, 288), (TX1, TY1, 320), CAULK))
    acx, acy = 1408, 60
    xm('advent_wreath', acx, acy, 320)
    for k, lit in enumerate((True, True, True, False)):
        a = math.radians(45 + 90 * k)
        if lit: flame(round(acx + 95 * math.cos(a)), round(acy + 95 * math.sin(a)), 320 + 138)
    light(acx, acy, 560, 260, '1 0.7 0.4')
    mdl_c('pad_cups/pad_cup02.md3', 1280, -150, 320, angle=40)
    mdl_c('pad_cups/pad_cup04.md3', 1540, 260, 320, angle=200)
    plate(1300, 220, 320, 72)
    for (dx, dy, m) in ((-24, 0, 'orange'), (22, 14, 'apple'), (0, -30, 'hazelnut'), (28, -24, 'walnut')):
        mdl_c('pad_fruits/%s.md3' % m, 1300 + dx, 220 + dy, 326)
    mdl_c('pad_ddmix/diner/coffe_pot.md3', 1540, -140, 320, angle=120)
    item('ammo_splasher', 1408, 60, 0)          # hidden under the table
    M.ent('station_health', (1400, -560, 0), angle=90)
    light(1700, 60, 900, 900, '1 0.85 0.6')


# =================================================================================================== SE: gingerbread house
GH = dict(x0=1280, x1=1920, y0=-1600, y1=-1088, hw=288)


def ginger_house():
    x0, x1, y0, y1, hw = GH['x0'], GH['x1'], GH['y0'], GH['y1'], GH['hw']
    t = 32
    xm('ginger_house', (x0 + x1) / 2, (y0 + y1) / 2, 0, x0=x0, x1=x1, y0=y0, y1=y1, hw=hw, door=(1536, 1664, 192),
       windows=(-1400, -1288, 96, 192), lm=1.0)
    _CLIP[0] = True                       # every brush below up to the ramp is collision for the MD3 house
    Wt = lambda inner: CAULK
    # north wall with the door (x 1536..1664, z 0..192)
    DX0, DX1, DZ = 1536, 1664, 192
    A(box((x0, y1 - t, 0), (DX0, y1, hw), Wt('s'))); A(box((DX1, y1 - t, 0), (x1, y1, hw), Wt('s')))
    A(box((DX0, y1 - t, DZ), (DX1, y1, hw), Wt('s')))
    A(box((x0, y0, 0), (x1, y0 + t, hw), Wt('n')))                       # south wall
    # side walls with a window each (y -1400..-1288, z 96..192)
    for (xa, xb, inner) in ((x0, x0 + t, 'e'), (x1 - t, x1, 'w')):
        for (ya, yb, za, zb) in ((y0 + t, -1400, 0, hw), (-1288, y1 - t, 0, hw), (-1400, -1288, 0, 96), (-1400, -1288, 192, hw)):
            A(box((xa, ya, za), (xb, yb, zb), Wt(inner)))
    # gable ends + pitched roof (30 deg, eaves overhang 48): slabs meet at the ridge over yc
    yc = (y0 + y1) / 2
    half = (y1 - y0) / 2
    tan = math.tan(math.radians(30))
    ridge_b = hw + half * tan                    # slab underside at the ridge
    for (xa, xb) in ((x0, x0 + t), (x1 - t, x1)):
        A(hull([(xa, y0, hw), (xb, y0, hw), (xa, y1, hw), (xb, y1, hw), (xa, yc, ridge_b), (xb, yc, ridge_b)],
               {'side': T('ginger_wall'), 'e': T('gingerbread'), 'w': T('gingerbread')}))
    th = 24 / math.cos(math.radians(30))
    ov = 48
    RF = {'top': T('ginger_roof'), 'side': T('icing'), 'bot': T('gingerbread')}
    for sg, ye in ((1, y1 + ov), (-1, y0 - ov)):
        zb_e = hw - ov * tan
        A(hull([(x0 - ov, ye, zb_e), (x1 + ov, ye, zb_e), (x0 - ov, ye, zb_e + th), (x1 + ov, ye, zb_e + th),
                (x0 - ov, yc, ridge_b), (x1 + ov, yc, ridge_b), (x0 - ov, yc, ridge_b + th), (x1 + ov, yc, ridge_b + th)], RF, round_pts=False))
    # icing ridge cap (low, does not block shots)
    A(box((x0 - ov, round(yc) - 12, round(ridge_b + th)), (x1 + ov, round(yc) + 12, round(ridge_b + th) + 12), T('icing')))
    _CLIP[0] = False
    # candy-cane ramp up to the north eave (38 deg) + a standing candy cane
    eave_top = hw - ov * tan + th
    run = round(eave_top / tan)                  # ~30 deg like the roof; ends 8u above the eave (a seam bspc can walk across)
    A(ramp(1736, y1 + ov, 1864, y1 + ov + run, 0, round(eave_top) + 8, 0, 's', {'top': T('candystripe'), 'side': T('candystripe'), 'bot': CAULK}))
    jumppad(1420, -880, 0, (1420, -1190, round(eave_top + (y1 + ov + 1190) * tan)), 560, 'jp_ginger')   # bots can't cross the ramp/eave seam
    candycane(1180, -980, 0, 300)
    candycane(2060, -860, 0, 360, flip=True)
    # gumdrops along the walls outside (cover)
    for (gx, gy, c) in ((1220, -1200, 'red'), (1220, -1450, 'green'), (1980, -1250, 'yellow'), (1980, -1500, 'purple')):
        xm('gumdrop', gx, gy, 0, key='gumdrop_' + c, col=c)
        A(frustum(gx, gy, 0, 72, 44, 26, WCLIP, 10)); A(cyl(gx, gy, 26, 72, 84, WCLIP, 10))
    # inside: chocolate table, gumdrop stools, a cookie man on the wall
    xm('choc_table', 1600, -1390, 0)
    A(box((1500, -1450, 0), (1700, -1330, 120), WCLIP))
    for (sx, c) in ((1440, 'red'), (1760, 'green')):
        xm('gumdrop', sx, -1390, 0, key='stool_' + c, r=40, h=64, col=c)
        A(frustum(sx, -1390, 0, 64, 40, 24, WCLIP, 10))
    A(sign_box((x0 + t, -1560, 40), (x0 + t + 4, -1480, 200), T('gingerman'), 128, 256, back=T('gingerbread'), facing='e'))
    item('holdable_bambam', 1600, -1220, 0)
    item('ammo_balloony', 1380, -1500, 0)
    item('ammo_pumper', 1820, -1500, 0)
    light(1600, -1344, 230, 260, '1 0.75 0.45')
    # roof: the Balloony on the north slope
    z_at = lambda y: hw - (abs(y - yc) - half) * tan + th if abs(y - yc) <= half + ov else None
    weapon('balloony', 1600, yc + 100, round(hw + (half - 100) * tan + th) + 10, marker='orange')
    item('ammo_bubbleg', 1360, yc + 160, round(hw + (half - 160) * tan + th) + 10)
    spawn(1450, yc + 120, round(hw + (half - 120) * tan + th) + 10, 90)
    # gingerbread men cut-outs in the garden of the house
    for (gx, gy, ang) in ((1150, -1300, 'e'), (2050, -1350, 'w')):
        xa = gx if ang == 'e' else gx - 16
        xm('gingerman', xa + 8, gy, 0, angle=0 if ang == 'e' else 180)
        A(box((xa, gy - 56, 0), (xa + 16, gy + 56, 240), WCLIP))


def candycane(x, y, z, h, flip=False):
    """standing candy cane: MD3 (striped tube with a hook) + clip pole"""
    xm('candy_cane', x, y, z, key=f'candy_cane_{h}' + ('_f' if flip else ''), h=h, flip=flip)
    A(cyl(x, y, 18, z, z + h, WCLIP, 8))


# =================================================================================================== SW + centre: toys
def toys():
    # rocking horse on red bow rockers (SW): MD3 + the old blocky shape as clip
    hx, hy = -1500, -1150
    xm('rocking_horse', hx, hy, 0)
    with as_clip():
        A(box((hx - 180, hy - 80, 200), (hx + 180, hy + 80, 330), CAULK))
        A(box((hx + 130, hy - 50, 330), (hx + 230, hy + 50, 450), CAULK))
        A(box((hx + 170, hy - 46, 450), (hx + 320, hy + 46, 530), CAULK))
        for (dx, sg) in ((-130, -1), (130, -1), (-130, 1), (130, 1)):
            A(box((hx + dx - 10, hy + sg * 70 - 8, 48), (hx + dx + 10, hy + sg * 70 + 8, 200), CAULK))
    item('ammo_betty', -1500, -900, 0)
    # Santa's sack + presents spilling out (SW corner)
    sx, sy = -1850, -1450
    xm('sack', sx, sy, 0, key='sack_big', rx=200, ry=180, h=420, gifts=True, seed=7)
    pts = []
    for (zf, rf) in ((0, 0.8), (0.4, 1.0), (0.8, 0.7), (1.0, 0.3)):
        pts += [(sx + 200 * rf * math.cos(2 * math.pi * k / 12), sy + 180 * rf * math.sin(2 * math.pi * k / 12), 420 * zf) for k in range(12)]
    A(hull(pts, WCLIP, round_pts=False))
    gift(-1640, -1700, 0, -1480, -1560, 128, 'gold')
    gift(-1470, -1740, 0, -1270, -1580, 192, 'dots', bow=False)
    gift(-1440, -1720, 192, -1310, -1610, 272, 'red', bow=True)
    gift(-2120, -1100, 0, -1960, -940, 160, 'stripe')
    item('ammo_bubbleg', -1720, -1180, 0)
    # toy drum
    dx_, dy_ = -1150, -1600
    xm('drum', dx_, dy_, 0)
    A(cyl(dx_, dy_, 116, 0, 150, WCLIP, 14))
    item('ammo_nipper', dx_ + 170, dy_, 0)
    # toy train on an oval wooden track (centre south)
    train_set(-80, -1050)
    # present stacks as cover in the open floor (sightline breakers)
    gift(-1250, -420, 0, -1040, -220, 224, 'green', bow=False)
    gift(-1230, -400, 224, -1080, -260, 320, 'gold', bow=False)
    gift(820, -1650, 0, 1060, -1460, 256, 'blue')
    gift(1100, -1640, 0, 1240, -1500, 128, 'kraft')
    gift(-1300, 300, 0, -1140, 460, 160, 'trees')
    gift(1000, 1500, 0, 1180, 1700, 208, 'red')
    gift(-900, 1500, 0, -700, 1700, 176, 'stripe')
    gift(-660, 1560, 0, -540, 1680, 96, 'dots')
    item('ammo_balloony', -1145, -500, 0)
    # ceiling: glowing paper stars and a bunch of mistletoe on threads (MD3)
    for (x, y, h, ang) in ((-300, -900, 300, 0), (900, -800, 360, 40), (-900, -300, 260, 80), (1200, 1100, 320, 120), (-1000, 1300, 280, 160)):
        xm('paper_star', x, y, CZ, key=f'paper_star_{h}', hang=h, angle=ang)
    xm('mistletoe', 300, -600, CZ)


def train_set(cx, cy):
    """wooden toy train set (MD3): oval track of sleepers and rails, a steam engine and two wagons carrying presents;
    collision = the old boxes as clip (track 8u high, so you can walk over it)"""
    L, R0, R1 = 640, 300, 380
    xm('track_oval', cx, cy, 4, L=L, R0=R0, R1=R1)
    with as_clip():
        for sg in (-1, 1):
            y0 = cy + sg * R0 if sg > 0 else cy - R1
            y1 = cy + R1 if sg > 0 else cy - R0
            A(box((cx - L // 2, y0, 4), (cx + L // 2, y1, 12), CAULK))
        for sg in (-1, 1):
            ex = cx + sg * L // 2
            for k in range(8):
                a0 = -math.pi / 2 + math.pi * k / 8; a1 = -math.pi / 2 + math.pi * (k + 1) / 8
                pts = []
                for a in (a0, a1):
                    for r in (R0, R1):
                        pts += [(ex + sg * r * math.cos(a), cy + r * math.sin(a), 4), (ex + sg * r * math.cos(a), cy + r * math.sin(a), 12)]
                A(hull(pts, CAULK, round_pts=False))
    yb = cy - (R0 + R1) // 2
    y0, y1 = yb - 48, yb + 48
    ex0 = cx + 120
    xm('toy_engine', ex0 + 100, yb, 0)
    with as_clip():
        A(box((ex0, y0 + 12, 12), (ex0 + 200, y1 - 12, 64), CAULK))
        A(box((ex0, y0 + 12, 64), (ex0 + 80, y1 - 12, 200), CAULK))
        A(box((ex0 + 80, yb - 34, 64), (ex0 + 200, yb + 34, 132), CAULK))
    for (xa, pat, col) in ((cx - 120, 'red', 'paint_green'), (cx - 360, 'gold', 'paint_yellow')):
        xm('toy_wagon', xa + 100, yb, 0, key='wagon_' + col, col=col)
        A(box((xa, y0 + 12, 12), (xa + 200, y1 - 12, 64), WCLIP))
        gift(xa + 40, y0 + 18, 64, xa + 160, y1 - 18, 154, pat)
    item('ammo_pumper', cx + 200, cy, 4)
    item('ammo_nipper', cx - 230, cy - 200, 4)
    light(cx, cy, 500, 400, '1 0.8 0.6')


# =================================================================================================== cover (breaks the long sightlines)
def cover():
    # north strip behind the tree
    gift(-760, 1240, 0, -560, 1420, 192, 'blue', bow=False); gift(-730, 1270, 192, -600, 1390, 288, 'dots')
    gift(300, 1500, 0, 500, 1700, 224, 'gold')
    gift(-460, 1540, 0, -300, 1700, 144, 'kraft')
    gift(1260, 1180, 0, 1440, 1360, 208, 'green', bow=False); gift(1290, 1210, 208, 1410, 1330, 272, 'red')
    solid_mdl('gummybears/redbear.md3', 900, 1450, 0, angle=200)
    # east: big present by the coffee table, a padman cardboard stand-up
    gift(900, -260, 0, 1090, -70, 240, 'stripe')
    solid_mdl('pad_ddmix/padshop/cardboard_standup.md3', 1000, -720, 0, angle=120)
    # west, between the fireplace and the tree
    gift(-1500, -300, 0, -1300, -110, 224, 'red', bow=False); gift(-1470, -270, 224, -1340, -140, 300, 'trees')
    solid_mdl('gummybears/greenbear.md3', -1000, 900, 0, angle=330)
    # south half: present tower in the train oval, piles near the rug edges, a golden Padman statue (somebody's gift)
    gift(-190, -1160, 4, 30, -940, 196, 'green', bow=False); gift(-150, -1120, 196, -10, -980, 324, 'gold')
    gift(-1150, -1400, 0, -1040, -1250, 160, 'blue')
    gift(520, -640, 0, 680, -480, 176, 'kraft')
    gift(-860, -400, 0, -700, -240, 144, 'gold')
    gift(240, -540, 4, 360, -424, 112, 'dots')
    gift(-400, -1030, 4, -270, -900, 150, 'stripe')
    gift(1480, 840, 0, 1620, 980, 176, 'blue')
    gift(600, -900, 0, 760, -760, 160, 'red')
    gift(-1180, -960, 0, -1040, -820, 192, 'gold')
    gift(-1000, -200, 0, -840, 0, 176, 'green')
    gift(-640, -640, 4, -480, -480, 128, 'red')
    solid_mdl('ente/padstatue_gold.md3', 760, -1250, 0, angle=150)
    solid_mdl('pad_ducks/pad_duck.md3', -560, 1060, 4, scale=0.7, angle=300)


# =================================================================================================== lights, spawns, misc floor
def room_lights_and_floor():
    # warm fill (evening: low, cosy)
    for (x, y) in ((-1300, -900), (-300, -1100), (800, -1000), (1500, -300), (-1300, 300), (1400, 1000), (-900, 1200), (900, 1300)):
        light(x, y, 1500, 2200, '1 0.82 0.6')
    # big rug centre south (fitted)
    rug = box(RUG[:2] + (0,), RUG[2:] + (4,), {'top': T('rug'), 'side': T('rug_edge'), 'bot': CAULK})
    fit_top(rug, RUG[0], RUG[1], RUG[2], RUG[3], 512, 384)
    A(rug)
    for (x, y, z, a) in ((-700, -700, 4, 45), (300, -1450, 4, 90), (1000, -400, 0, 135), (-1600, -600, 0, 0), (1100, 1200, 0, 225),
                         (-400, 1500, 0, 270), (1500, 700, 0, 180), (-900, 200, 0, 0), (420, -1230, 4, 90), (-1500, 300, 0, 300)):
        spawn(x, y, z, a)
    for (cls, x, y, z) in (('item_armor_shard', -400, -500, 4), ('item_armor_shard', 1200, 1350, 0), ('ammo_imperius', 1980, 1300, 0),
                           ('ammo_boaster', -500, 1450, 0), ('ammo_balloony', 900, -1100, 0), ('ammo_betty', -2000, 1300, 0),
                           ('ammo_bubbleg', 1300, 1000 - 400, 0)):
        item(cls, x, y, z)
    # ambient sounds
    speaker(0, 0, 1800, 'sound/world/ambient/wind_night.ogg')
    speaker(0, -1700, 900, 'sound/world/ambient/wind_icy.ogg')
    # a cat somewhere in the presents
    speaker(400, 300, 100, 'sound/world/animal/kitten_meow.ogg', loop=False, targetname='meow')
    M.ent('func_timer', (1100, -200, 200), target='meow', wait=50, random=25, spawnflags=1)
    # footsteps on the roof (Santa?) now and then
    speaker(-600, 0, CZ - 40, 'sound/world/human/footsteps_m.ogg', loop=False, targetname='santa')
    M.ent('func_timer', (-600, 0, CZ - 100), target='santa', wait=75, random=30, spawnflags=1)
    # applause when you reach the top of the tree
    speaker(TC[0], TC[1], TIERS[4][1] + 100, 'sound/world/human/applause.ogg', loop=False, targetname='topclap')
    M.ent('trigger_multiple', brushes=[box((TC[0] - 40, TC[1] - 150, TIERS[4][1]), (TC[0] + 40, TC[1] - 120, TIERS[4][1] + 64), TRIG)],
          target='topclap', wait=30)


# =================================================================================================== main
def main():
    W = TX.make_all(OUT)
    XM.init(OUT)
    room_shell(); tree(); tree_pads_and_loot(); under_tree(); fireplace(); roof(); window_garden(); nw_corner(); sideboard()
    sofa_corner(); ginger_house(); toys(); cover(); room_lights_and_floor()
    M.ent('info_player_intermission', (-1400, -1200, 1500), angles='18 40 0')
    with open(os.path.join(OUT, 'scripts', TX.NS + '.shader'), 'a') as f:
        f.write(XM.shaders())
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text("// Padman's Christmas - generated by wop_tools/xmas/build_xmas.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
