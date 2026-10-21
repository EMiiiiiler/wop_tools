#!/usr/bin/env python3
"""Backyard BBQ - World of Padman FFA map generator (map 'wop_padbbq').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_bbq.py

Writes <OUT>/maps/wop_padbbq.map, textures/padbbq/*, models/padbbq/*, scripts/padbbq.shader and scripts/wop_padbbq.arena.

A Kiwi backyard on a summer afternoon at Padman scale (5u per cm, Padman an 11 cm toy). x east, y north, lawn z 0.

  Deck + pergola    north-west, against the weatherboard house: outdoor setting, planters, a lattice skirt with gaps to
                    crawl under the deck (Bubble G, Boomies, spiders). A pad onto the pergola's slat roof (Imperius) among
                    the grapevine and festoon lights; a fling pad back down.
  Kettle barbecue   centre: walk up a pile of briquettes into the ash catcher (Splasher), pad onto the grate (Betty on the
                    cool edge; the middle over the coals burns); the chilly bin and the charcoal bag beside it.
  Paddling pool     west: foam-block steps up and over the rim and down inside, Pumper on the bottom, a swim ring and a
                    rubber duck drifting round.
  Dad's shed        south-west: walk in (mower, shelves, tools), pad onto the workbench; pad onto the roof (Balloony).
  Kennel            north-east: Boaster inside, a pad onto the ridge (Speedy).
  Picnic table      south-east under the parasol: lunch, a pad onto the table (Pad shield).
  Sun lounger       south: a beach towel is the ramp up, Floater on the seat.
  Vege bed          east fence: brick steps up into the tomatoes and lettuces (BamBam).
  Lawn              a rotary clothesline turning in the breeze, a sprinkler, the hose, gnomes, backyard cricket, toys.
  SECRET            walk into the ant hill by the south fence -> the ant colony (sealed under the world): the queen,
                    larvae, a seed larder; Pad Power, Revival, Killer Ducks; a teleporter back.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import bb_textures as TX
import bblib

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padbbq'
T = lambda n: 'padbbq/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'grass': (1.0, 1.0), 'weatherboard': (0.75, 0.75), 'weatherboard_green': (0.75, 0.75), 'palings': (1.0, 1.0), 'decking': (0.75, 0.75),
             'soil': (0.75, 0.75), 'soil_wall': (1.0, 1.0), 'soil_floor': (1.0, 1.0), 'brick': (0.5, 0.5), 'corrugated_red': (1.0, 1.0),
             'shed_floor': (0.75, 0.75), 'shed_wall_in': (0.75, 0.75), 'sleeper': (0.5, 0.5), 'water': (1.0, 1.0), 'curtain': (1.0, 1.0),
             'curtain_b': (1.0, 1.0)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '18', '_color': '1 0.97 0.92', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
KEEP_OUT = []


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x, 1), round(y, 1), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    """catalog model centred (by its bounds) on x, y, resting on zsurf"""
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def mdl_box(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, top_cut=2, clip=True, **kw):
    """catalog model centred on x, y with a weapclip box from its rotated bounds"""
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
    if not clip: return e
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    pts = []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            pts.append((ox + (px * ca - py * sa) * scale, oy + (px * sa + py * ca) * scale))
    c = np.mean(pts, 0)
    pts = [tuple(c + (np.array(p) - c) * (1 - shrink)) for p in pts]
    z1 = oz + b['max'][2] * scale - top_cut
    A(hull([(p[0], p[1], zsurf) for p in pts] + [(p[0], p[1], z1) for p in pts], WCLIP, round_pts=False))
    return e


def custom(name, x, y, zbase, angle=0, lit=True, mul=1.0, angles=None, **kw):
    """one of our own MD3s (models/paddollhouse), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = bblib.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, angles=angles, **extra)


def lbox(x, y, z, ang, mn, mx, tex=WCLIP):
    """box given in a model's local frame (mn, mx) placed at (x, y, z) turned by ang degrees"""
    a = math.radians(ang); ca, sa = math.cos(a), math.sin(a)
    pts = []
    for px in (mn[0], mx[0]):
        for py in (mn[1], mx[1]):
            for pz in (mn[2], mx[2]):
                pts.append((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))
    b = hull(pts, tex, round_pts=False)
    A(b)
    return b


def furn(name, x, y, z, ang=0, boxes=(), mul=1.0, lit=True, **kw):
    """custom model + its weapclip boxes (local frame, before mul)"""
    e = custom(name, x, y, z, ang, lit=lit, mul=mul, **kw)
    for (mn, mx) in boxes:
        lbox(x, y, z, ang, [v * mul for v in mn], [v * mul for v in mx])
    return e


def light(x, y, z, val, color='1 0.9 0.75', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
    M.ent('func_timer', (round(x), round(y), round(z + 64)), target=name, wait=wait, random=rnd, spawnflags=1)


def trigger_sound(mn, mx, noise, name, wait=4, **kw):
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    speaker(c[0], c[1], c[2] + 40, noise, loop=False, targetname=name, **kw)
    M.ent('trigger_multiple', brushes=[box(mn, mx, TRIG)], target=name, wait=wait)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))
    KEEP_OUT.append((x, y, 40))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((x, y, floor))


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)


def jumppad(x, y, z, land, apex, name, glow=True):
    """daisy pad (r 34 disc) + trigger_push + target_position (AimAtTarget: the target is the apex, measured from the
    trigger centre; it sits t_up/(t_up+t_down) of the way to `land`)"""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    oz = z + 38
    tx, ty = pad_target((x, y, oz), land, apex)
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (x, y, oz), (round(tx), round(ty), round(apex)), land))
    if glow: light(x, y, z + 48, 90, '1 0.6 0.8')
    KEEP_OUT.append((x, y, 70))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def route(name, a, b):
    ROUTES.append((name, a, b))


def clip_half(b, axis, lo=None, hi=None):
    big = 100000
    cut = []
    if lo is not None:
        mn = [-big] * 3; mx = [big] * 3; mx[axis] = lo
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    if hi is not None:
        mn = [-big] * 3; mx = [big] * 3; mn[axis] = hi
        cut.append(box(tuple(mn), tuple(mx), CAULK))
    return carve(b, cut)


def tex_box(mn, mx, top, side, bot=CAULK, **dirs):
    t = {'top': top, 'side': side, 'bot': bot}
    t.update(dirs)
    return box(mn, mx, t)


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'jumppad_ns', 'origin', 'water', 'botclip')


def fix_items():
    """nudge items / weapons / spawns that ended up inside a solid or clip brush to the nearest free spot (same height)"""
    sol = []
    for b in M.world + [bb for e in M.ents if e['classname'] not in ('trigger_push', 'trigger_multiple', 'trigger_teleport') for bb in e['_brushes']]:
        ts = b.textures()
        if all(any(h in t for h in NONSOLID_TEX) for t in ts): continue
        mn, mx = b.bounds()
        sol.append((mn, mx, b.planes()))
    smn = np.array([s[0] for s in sol]); smx = np.array([s[1] for s in sol])
    def blocked(o, lo, hi):
        bmn, bmx = o + lo, o + hi
        cand = np.where(np.all(smn < bmx - 0.25, 1) & np.all(smx > bmn + 0.25, 1))[0]
        if len(cand) == 0: return False
        pts = [o + np.array([x, y, z]) for x in (lo[0], 0, hi[0]) for y in (lo[1], 0, hi[1]) for z in (lo[2] + 1, 0, hi[2])]
        for k in cand:
            P = sol[k][2]
            if any(all(np.dot(n, p) - d < -0.25 for n, d in P) for p in pts): return True
        return False
    moved = []
    for e in M.ents:
        c = e['classname']
        if not c.startswith(('weapon_', 'ammo_', 'item_', 'holdable_', 'info_player_deathmatch')): continue
        o = np.array([float(v) for v in e['origin'].split()])
        lo, hi = (np.array([-16, -16, -24]), np.array([16, 16, 32])) if c.startswith('info_') else (np.array([-16, -16, -15.5]), np.array([16, 16, 16]))
        if not blocked(o, lo, hi): continue
        done = False
        for d in range(16, 260, 16):
            for k in range(16):
                a = k * math.pi / 8
                p = o + np.array([d * math.cos(a), d * math.sin(a), 0])
                if not blocked(p, lo, hi) and blocked(p + np.array([0, 0, lo[2] - 8]), np.array([-4, -4, -2]), np.array([4, 4, 2])):
                    e['origin'] = ' '.join(fmt([v]) for v in np.round(p)); moved.append((c, o.astype(int).tolist(), np.round(p).astype(int).tolist()))
                    done = True; break
            if done: break
        if not done: moved.append((c, o.astype(int).tolist(), 'STUCK'))
    return moved


def write_routes():
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padbbq/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_bbq.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, tex):
    """wedge between angles a0..a1 (deg) and radii r0..r1, z0..z1"""
    pts = []
    for a in (a0, a1):
        for r in (r0, r1):
            px, py = L.ang_pt(cx, cy, r, a)
            pts += [(px, py, z0), (px, py, z1)]
    return hull(pts, tex, round_pts=False)


def ring(cx, cy, r0, r1, z0, z1, tex, n=24, skip=None):
    for k in range(n):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        if skip and skip(a0, a1): continue
        A(ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, tex))


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, 0)] + [(x, y, z1) for (x, y) in ngon(cx, cy, max(r1, 1), n, 0)], tex, round_pts=False)


# =================================================================================================== hull, ground, house, fences
def hull_and_ground():
    H = L.HULL
    x0, x1, y0, y1, z0, z1 = H['x0'], H['x1'], H['y0'], H['y1'], H['z0'], H['z1']
    W = 16
    sk = T('sky')
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), CAULK, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': sk, 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), {'s': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), {'n': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), {'w': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), {'e': sk, 'side': CAULK, 'top': CAULK, 'bot': CAULK}, detail=False))
    # ground: lawn inside the fences, the neighbours' grass outside (detail slabs on the structural floor)
    for (a, b, c, d) in sub_rects((x0, y0, x1, L.YN), [(-L.XW, L.YS, L.XW, L.YN)]):
        A(box((a, b, z0), (c, d, 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK}))
    step = 1152
    for xa in range(-L.XW, L.XW, step):
        for ya in range(L.YS, L.YN, 1024):
            A(box((xa, ya, z0), (min(xa + step, L.XW), min(ya + 1024, L.YN), 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK}))
    # under the house
    A(box((x0, L.YN, z0), (x1, y1, 0), CAULK))


def house():
    y = L.YN; t = L.HOUSE_T
    H = L.HULL
    wins = [L.WIN_W, L.WIN_E, L.WIN_S]
    holes = [(a, c, b, d) for (a, b, c, d) in wins]
    for (a, za, b, zb) in sub_rects((H['x0'], 0, H['x1'], L.HOUSE_EAVE), holes):
        bb = box((a, y, za), (b, y + t, zb), CAULK)
        for f in bb.faces:
            if f.n[1] < -0.9: f.tex = T('weatherboard')
            elif abs(f.n[1]) < 0.1 and abs(f.n[2]) < 0.1 or abs(f.n[2]) > 0.9 and za > 0: f.tex = T('paint_white')
            f.sc = wopmap.default_scale(f.tex)
        A(bb)
    for (k, (a, b, c, d)) in enumerate(wins):
        A(box((a, y + 24, c), (b, y + 28, d), T('glass')))
        A(box((a, y + 28, c), (b, y + t, d), {'s': T('curtain' if k != 1 else 'curtain_b'), 'side': CAULK, 'top': CAULK, 'bot': CAULK}))
    # roof above the eave: a corrugated iron slope rising north into the hull, set back behind the gutter
    ze = L.HOUSE_EAVE
    A(hull([(x, yy, z) for x in (H['x0'], H['x1']) for (yy, z) in ((y - 120, ze), (y - 120, ze + 12), (H['y1'], ze + 12 + (H['y1'] - y + 120) * 0.42),
                                                                     (H['y1'], ze))], {'top': T('corrugated_red'), 'side': CAULK, 'bot': T('paint_white')}))
    # players stay off the roof
    A(box((-L.XW, y - 200, ze - 40), (L.XW, y - 120, H['z1']), CLIP))
    custom('house_trim', 0, 0, 0)
    # outdoor tap, heat pump
    custom('heat_pump', 2010, y - 82, 0, 90)
    lbox(2010, y - 82, 0, 90, (-80, -210, 0), (80, 210, 360))


def fences():
    t = L.FENCE_T; H = L.HULL; Fh = L.FENCE_H
    pal = T('palings')
    def ft(inner):
        def f(n):
            if n[2] > 0.9: return T('pine')
            if n[2] < -0.9: return CAULK
            d = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[inner]
            return pal if (n[0] * d[0] + n[1] * d[1]) > 0.9 else (pal if abs(n[2]) < 0.1 else CAULK)
        return f
    A(box((-L.XW - t, L.YS - t, 0), (-L.XW, L.YN, Fh), ft('e')))
    A(box((L.XW, L.YS - t, 0), (L.XW + t, L.YN, Fh), ft('w')))
    A(box((-L.XW, L.YS - t, 0), (L.XW, L.YS, Fh), ft('n')))
    for side in ('w', 'e', 's'):
        custom(f'fence_{side}', 0, 0, 0)
    # player clip from the fence tops up to the sky
    A(box((-L.XW - t, L.YS - t, Fh), (-L.XW, L.YN - 120, H['z1']), CLIP), box((L.XW, L.YS - t, Fh), (L.XW + t, L.YN - 120, H['z1']), CLIP))
    A(box((-L.XW, L.YS - t, Fh), (L.XW, L.YS, H['z1']), CLIP))
    # the neighbours' trees and a cabbage tree or two, outside the fence
    rng = np.random.default_rng(4)
    spots = [(-2570, -2300), (-2570, -1300), (-2570, -200), (-2570, 900), (-2570, 1700), (2570, -2300), (2570, -1200), (2570, 0), (2570, 1100),
             (2570, 1700), (-1700, -2300), (-500, -2290), (700, -2300), (1800, -2300)]
    trees = ['pad_ddmix/trashcan/tree_summer.md3', 'pad_ddmix/trashcan/tree_spring.md3', 'pad_ddmix/trashcan/tree_summer.md3']
    for k, (x, yy) in enumerate(spots):
        if k % 4 == 3:
            custom(f'cabbage_tree_{k % 2}', x, yy, 0, int(rng.uniform(0, 360)))
        else:
            mdl_c(trees[k % 3], x, yy, 0, rng.uniform(0.9, 0.95), int(rng.uniform(0, 360)))
    for k in range(16):
        side = k % 3
        if side == 0: x, yy = -2440 - rng.uniform(0, 160), rng.uniform(-2000, 2000)
        elif side == 1: x, yy = 2440 + rng.uniform(0, 160), rng.uniform(-2000, 2000)
        else: x, yy = rng.uniform(-2200, 2200), -2200 - rng.uniform(0, 140)
        mdl_c('pad_ddmix/trashcan/bush.md3', x, yy, 0, 0.9, int(rng.uniform(0, 360)))


# =================================================================================================== deck + pergola
def deck():
    x0, y0, x1, y1 = L.DECK
    z = L.DECK_Z
    A(box((x0, y0, z - L.DECK_T), (x1, y1, z), {'top': T('decking'), 'bot': T('pine'), 'side': T('pine')}))
    # posts under the deck
    for px in range(x0 + 160, x1, L.DECK_POSTS):
        for py in (y0 + 40, (y0 + y1) // 2 + 40):
            A(box((px - 16, py - 16, 0), (px + 16, py + 16, z - L.DECK_T), T('pine')))
    # steps
    for st in ('s', 'e'):
        for (a, b, c, d, zt) in L.deck_steps(st):
            A(box((a, b, 0), (c, d, zt), {'top': T('decking'), 'side': T('pine'), 'bot': CAULK}))
    custom('deck_trim', 0, 0, 0)
    # lattice skirt along the front and the east side: alpha brush + player clip, with crawl gaps
    fs = [(a, b) for (k, a, b) in L.DECK_STEPS if k == 's']
    holes = [(a, 0, b, 1) for (a, b) in fs] + [(a, 0, b, 1) for (a, b) in L.LATTICE_GAPS]
    for (a, _, b, _) in sub_rects((x0, 0, x1, 1), holes):
        lt = box((a, y0 + 6, 0), (b, y0 + 10, z - L.DECK_T), T('lattice'))
        for f in lt.faces: f.sc = (0.5, 0.5)
        A(lt); A(box((a, y0 + 10, 0), (b, y0 + 14, z - L.DECK_T), CLIP))
    es = [(a, b) for (k, a, b) in L.DECK_STEPS if k == 'e']
    for (a, _, b, _) in sub_rects((y0 + 14, 0, y1, 1), [(a, 0, b, 1) for (a, b) in es]):
        lt = box((x1 - 10, a, 0), (x1 - 6, b, z - L.DECK_T), T('lattice'))
        for f in lt.faces: f.sc = (0.5, 0.5)
        A(lt); A(box((x1 - 14, a, 0), (x1 - 10, b, z - L.DECK_T), CLIP))
    for (a, b) in L.LATTICE_GAPS:
        route(f'under_deck_{a}', ((a + b) / 2, y0 - 120, 0), ((a + b) / 2, y0 + 260, 0))
    for (a, b) in fs:
        route(f'deck_front_{a}', ((a + b) / 2, y0 - 360, 0), ((a + b) / 2, y0 + 120, z))
    for (a, b) in es:
        route('deck_side', (x1 + 360, (a + b) / 2, 0), (x1 - 120, (a + b) / 2, z))
    # under the deck: dim, spiders, lost things, Bubble G
    weapon('bubbleg', -1600, 1800, 0)
    item('holdable_boomies', 200, 1850, 0)
    item('ammo_betty', -1000, 1650, 0)
    item('ammo_pumper', 450, 1600, 0)
    item('item_visionless', -2150, 1900, 0)
    for (x, yy) in ((-1300, 1900), (-200, 1700), (500, 1950)):
        mdl_c('spider/spider.md3', x, yy, 0, 2.0, int(x) % 360)
    mdl_c('pad_ddmix/trashcan/garbage_bag_lying.md3', -1900, 1650, 0, 1.4, 30)
    mdl_c('pad_ball/pad_tennisball.md3', -700, 1900, 0, 2.0, 0)
    mdl_c('pad_ddmix/attic/kaspad.md3', 300, 1720, 0, 0.9, 200)
    for (x, yy) in ((-1700, 1700), (-500, 1800), (300, 1650)):
        light(x, yy, 100, 70, '0.8 0.85 1')
    # on the deck: the outdoor setting under the pergola, planters, Imperius ammo, health station
    furn('deck_setting', 40, 1740, z, 0, [((-182, -182, 0), (182, 182, 376)), ((200, -100, 0), (400, 100, 226)), ((-400, -100, 0), (-200, 100, 226))])
    furn('planter_lemon', -2180, 1900, z, 0, [((-110, -110, 0), (110, 110, 220))])
    furn('planter_flax', -560 - 120, 1460, z, 0, [((-100, -100, 0), (100, 100, 200))])
    furn('planter_flax', -2080, 1560, z, 0, [((-100, -100, 0), (100, 100, 200))])
    station(-1500, 1700, z, 270)
    item('ammo_imperius', -1800, 1980, z)
    item('ammo_boaster', -1200, 1560, z)
    item('ammo_bubbleg', -1000, 1950, z)
    spawn(-1300, 1850, z, 270)
    spawn(400, 1500, z, 225)
    # pergola: posts + walkable slat roof (player clip: shots go through the gaps), grapevine, festoon lights
    px0, py0, px1, py1 = L.PERGOLA
    p = L.PERG_POST
    custom('pergola', 0, 0, 0)
    for (x, yy) in ((px0 + p, py0 + p), ((px0 + px1) / 2, py0 + p), (px1 - p, py0 + p)):
        A(box((x - p, yy - p, z), (x + p, yy + p, L.PERG_TOP - 96), WCLIP))
    A(box((px0 - 24, py0 - 40, L.PERG_TOP - 96), (px1 + 24, py0 + 2 * p, L.PERG_TOP - 16), WCLIP))
    A(box((px0 - 24, py0 - 40, L.PERG_TOP - 16), (px1 + 24, py1, L.PERG_TOP), CLIP))
    for (x, yy) in ((px0 + 200, py0 - 6), (px1 - 200, py0 - 6)):
        light(x, yy, L.PERG_TOP - 180, 160, '1 0.8 0.5')
    jumppad(-900, 1800, z, (-260, 1800, L.PERG_TOP), L.PERG_TOP + 270, 'pad_pergola')
    jumppad(420, 1600, L.PERG_TOP, (760, 760, 0), L.PERG_TOP + 160, 'pad_pergola_down')
    # the slat roof is player clip (shots pass the gaps) and items drop with MASK_SOLID: keep them suspended (spawnflags 1)
    weapon('imperius', 0, 1860, L.PERG_TOP, spawnflags=1)
    item('ammo_balloony', -300, 1600, L.PERG_TOP, spawnflags=1)
    trigger_sound((-400, 1700, L.PERG_TOP + 2), (300, 2040, L.PERG_TOP + 90), 'sound/world/misc/wind_chimes.ogg', 'chimes', 15, volume=0.6)


# =================================================================================================== the kettle barbecue
def grill():
    gx, gy = L.GRILL
    custom('kettle', gx, gy, 0)
    R, Rz, Bz, Gz = L.G_RIM_R, L.G_RIM_Z, L.G_BOT_Z, L.G_GRATE_Z
    def rz(z):
        c = (Rz - z) / (Rz - Bz)
        return R * math.sqrt(max(0.0, 1 - c * c))
    zs = [Bz, 270, 300, 325, Gz]
    for za, zb in zip(zs, zs[1:]):
        A(frustum(gx, gy, max(rz(za), 20) - 4, za, rz(zb) - 4, zb, WCLIP, 16))
    ring(gx, gy, 134, R + 2, Gz, Rz, WCLIP, 16)
    # legs (thin clip posts) + ash pan + lid
    for a in (90, 210, 330):
        top = (*L.ang_pt(gx, gy, 132, a), 0); foot = L.ang_pt(gx, gy, L.G_LEG_R, a)
        pts = []
        for (cx, cy, z) in ((foot[0], foot[1], 0), (top[0], top[1], Bz + 20)):
            pts += [(cx + dx, cy + dy, z) for dx in (-7, 7) for dy in (-7, 7)]
        A(hull(pts, WCLIP, round_pts=False))
    A(cyl(gx, gy, L.G_PAN_R, L.G_PAN_Z - 12, L.G_PAN_Z, WCLIP, 16))
    la = 150
    nrm = np.array([math.cos(math.radians(la)), math.sin(math.radians(la)), 0.0]); tg = np.array([-nrm[1], nrm[0], 0])
    c = np.array([*L.ang_pt(gx, gy, R + 18, la), Rz - 150])
    pts = [c + nrm * d_ + tg * u + np.array([0, 0, v]) for d_ in (4, 120) for u in (-120, 120) for v in (-120, 120)]
    A(hull(pts, WCLIP, round_pts=False))
    # hot zone over the glowing coal heap; Betty on the cool edge of the grate, Splasher in the ash pan
    M.ent('trigger_hurt', brushes=[cyl(gx, gy, L.G_HOT_R, Gz + 1, Gz + 64, TRIG, 12)], dmg=6, spawnflags=16)
    weapon('betty', *L.ang_pt(gx, gy, 98, 82), Gz)
    weapon('splasher', gx - 40, gy, L.G_PAN_Z)
    speaker(gx, gy, Gz + 40, 'sound/world/ambient/fire_sizzling.ogg', volume=0.7)
    light(gx, gy, Gz + 60, 220, '1 0.5 0.2')
    light(gx, gy, L.G_PAN_Z + 70, 90, '1 0.85 0.7')
    # briquette steps up to the ash pan, the charcoal bag, tongs, the chilly bin
    custom('briq_steps', gx, gy, 0)
    for (x0, y0, x1, y1, zt) in L.briq_steps():
        A(box((x0, y0, 0), (x1, y1, zt), WCLIP))
    route('briquettes', (gx + 420, gy, 0), (gx + 20, gy, L.G_PAN_Z))
    furn('charcoal_bag', gx - 120, gy - 300, 0, 60, [((-50, -82, 0), (50, 82, 280))])
    custom('tongs', gx + 300, gy - 120, 0, 20)
    furn('esky', -760, 1040, 0, 15, [((-150, -90, 0), (150, 90, 196))])
    item('ammo_betty', -800, 1220, 0)
    jumppad(gx, gy - 430, 0, (gx, gy - 92, Gz), Gz + 200, 'pad_grill')
    spawn(gx + 500, gy - 260, 0, 160)


# =================================================================================================== paddling pool
def paddling_pool():
    cx, cy = L.POOL
    custom('pool', cx, cy, 0)
    ring(cx, cy, L.POOL_R_IN + 2, L.POOL_R_OUT - 2, 0, L.POOL_WALL_Z, WCLIP, 24)
    # outside foam steps (rising west, toward the rim) and inside steps down to the floor
    n_o, n_i = 8, 7
    custom('foam_8', cx + L.POOL_R_OUT + 28 * n_o, cy, 0, 180)
    for j in range(n_o):
        xa = cx + L.POOL_R_OUT + 28 * (n_o - 1 - j)
        A(box((round(xa), cy - 48, 0), (round(xa + 28), cy + 48, 16 * (j + 1)), WCLIP))
    xi = cx + L.POOL_R_IN - 8 - 28 * n_i
    custom('foam_7', xi, cy, 0, 0)
    ins = []
    for j in range(n_i):
        xa = xi + 28 * j
        b = box((round(xa), cy - 48, 0), (round(xa + 28), cy + 48, 16 * (j + 1)), WCLIP)
        ins.append(b); A(b)
    poly = ngon(cx, cy, L.POOL_R_IN, 24, 0)
    water = prism(poly, 0, L.POOL_WATER, T('water_nodraw'))
    for p in carve(water, ins):
        for f in p.faces:
            f.tex = T('water') if (f.n[2] > 0.9 and abs(max(q[2] for q in f.pts) - L.POOL_WATER) < 0.5) else T('water_nodraw')
            f.sc = wopmap.default_scale(f.tex)
        A(p)
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, L.POOL_WATER - 8), (cx + 8, cy + 8, L.POOL_WATER + 8), ORIGIN),
                                    box((cx - 4, cy - 4, L.POOL_WATER + 40), (cx + 4, cy + 4, L.POOL_WATER + 48), NODRAW_NS)],
          model2=bblib.IQM['pool_floaters'], speed=8, spawnflags=0, dmg=0)
    weapon('pumper', cx - 120, cy + 40, 0)
    item('ammo_pumper', cx + 30, cy - 160, 0)
    route('pool_steps', (cx + L.POOL_R_OUT + 300, cy, 0), (cx + L.POOL_R_OUT - 20, cy, L.POOL_WALL_Z))
    speaker(cx, cy, L.POOL_WATER + 20, 'sound/world/ambient/water_rippling.ogg', volume=0.4)
    station(cx + 420, cy - 300, 0, 180)
    custom('ball', cx - 300, cy - 520, 0)
    A(hull([(cx - 300 + px * math.cos(ph), cy - 520 + py * math.cos(ph), 60 + 58 * math.sin(ph)) for ph in np.linspace(-1.3, 1.3, 6)
            for (px, py) in [(math.cos(a) * 58, math.sin(a) * 58) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]] + [(cx - 300, cy - 520, 1)], WCLIP, round_pts=False))
    spawn(cx - 100, cy - 600, 0, 45)
    spawn(cx + 200, cy + 520, 0, 300)


# =================================================================================================== shed
def shed():
    x0, y0, x1, y1 = L.SHED
    t = L.SHED_WT
    dx0, dx1 = L.SHED_DOOR
    zr = L.shed_roof_z
    def wall(mn, mx, out_dir, holes=()):
        """box wall minus holes in its plane; outer face weatherboard, inner face shed lining"""
        axis = 'x' if out_dir in 'ns' else 'y'
        u0, u1 = (mn[0], mx[0]) if axis == 'x' else (mn[1], mx[1])
        ztop = mx[2]
        for (a, za, b, zb) in sub_rects((u0, 0, u1, ztop), holes):
            if axis == 'x': bb = box((a, mn[1], za), (b, mx[1], zb), CAULK)
            else: bb = box((mn[0], a, za), (mx[0], b, zb), CAULK)
            d = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[out_dir]
            for f in bb.faces:
                dd = f.n[0] * d[0] + f.n[1] * d[1]
                if dd > 0.9: f.tex = T('weatherboard_green')
                elif dd < -0.9: f.tex = T('shed_wall_in')
                elif abs(f.n[2]) < 0.9: f.tex = T('paint_white')
                else: f.tex = CAULK
                f.sc = wopmap.default_scale(f.tex)
            A(bb)
    zs, zn = zr(y0) - 24, zr(y1) - 24
    wall((x0, y1 - t, 0), (x1, y1, int(zn)), 'n', [(dx0, 0, dx1, L.SHED_DOOR_H)])
    wall((x0, y0, 0), (x1, y0 + t, int(zn)), 's')
    wall((x0, y0 + t, 0), (x0 + t, y1 - t, int(zn)), 'w')
    wall((x1 - t, y0 + t, 0), (x1, y1 - t, int(zn)), 'e', [(-1840, 380, -1600, 700)])
    A(box((x1 - 14, -1840, 380), (x1 - 10, -1600, 700), T('glass')))
    # gable infill between the wall tops and the sloping roof underside (south is higher)
    for (xa, xb) in ((x0, x0 + t), (x1 - t, x1)):
        A(hull([(x, yy, z) for x in (xa, xb) for (yy, z) in ((y0 + t, zn), (y1, zn), (y0 + t, zs - (zs - zn) * t / (y1 - y0)))],
               {'side': T('weatherboard_green'), 'top': CAULK, 'bot': CAULK}))
    A(hull([(x, yy, z) for x in (x0, x1) for (yy, z) in ((y0, zn), (y0 + t, zn), (y0, zs), (y0 + t, zs - (zs - zn) * t / (y1 - y0)))],
           {'side': T('weatherboard_green'), 'top': CAULK, 'bot': CAULK}))
    # roof slab (walkable, sloping gently north) + floor
    ov = 40
    A(hull([(x, yy, zr(yy) + dz) for x in (x0 - ov, x1 + ov) for yy in (y0 - ov, y1 + ov) for dz in (-24, 0)],
           lambda n: CAULK if n[2] > 0.5 else (T('shed_wall_in') if n[2] < -0.5 else T('paint_white'))))
    A(box((x0 + t, y0 + t, 0), (x1 - t, y1 - t, 16), {'top': T('shed_floor'), 'side': CAULK, 'bot': CAULK}))
    custom('shed_trim', 0, 0, 0)
    # door leaf collision (open against the north wall, east of the opening)
    A(box((dx1 + 24, y1 + 8, 8), (dx1 + 24 + (dx1 - dx0), y1 + 24, L.SHED_DOOR_H - 8), WCLIP))
    # inside: workbench, shelves, mower, tools, sacks, pots, paint tins
    bx0, by0, bx1, by1 = L.SHED_BENCH
    custom('workbench', 0, 0, 0)
    A(box((bx0, by0, 16), (bx1, by1, L.SHED_BENCH_Z), WCLIP))
    furn('shelf_unit', x0 + t + 72, -1660, 16, 0, [((-70, -160, 0), (70, 160, 640))])
    for k, z in enumerate((120, 380, 640)):
        for j, yy in enumerate((-1770, -1660, -1550)):
            if (k + j) % 2 == 0:
                mdl_c(['pad_tins/pad_paint1.md3', 'pad_tins/pad_paint2.md3', 'pad_tins/pad_paint1_tl.md3'][(k + j) % 3], x0 + t + 72, yy, 16 + z, 0.6, (k * 40 + j * 70) % 360)
    furn('lawnmower', -1580, -1600, 16, 180, [((-110, -140, 0), (130, 140, 160))])
    custom('garden_tools', x1 - t - 40, -1850, 16, 180)
    lbox(x1 - t - 40, -1850, 16, 180, (-20, -110, 0), (70, 110, 300))
    furn('pot_stack', -1620, -1905, 16, 0, [((-60, -60, 0), (60, 60, 206))])
    furn('sack', -1320, -1480, 0, 0, [((-60, -110, 0), (60, 110, 120))])
    mdl_c('pad_tins/pad_paint2.md3', -1850, -1920, L.SHED_BENCH_Z, 0.6, 30)
    light(-1840, -1730, zn - 80, 420, '1 0.92 0.8')
    item('ammo_betty', -2000, -1900, L.SHED_BENCH_Z)
    item('item_armor_shard', -2150, -1900, L.SHED_BENCH_Z)
    item('ammo_boaster', -1950, -1560, 16)
    item('ammo_balloony', -1600, -1500, 16)
    spawn(-1950, -1700, 16, 90)
    jumppad(-2050, -1700, 16, (-1960, -1900, L.SHED_BENCH_Z), L.SHED_BENCH_Z + 150, 'pad_bench')
    route('shed_door', ((dx0 + dx1) / 2, y1 + 300, 0), ((dx0 + dx1) / 2, y1 - 200, 16))
    # roof: Balloony; pad from the lawn east of the shed
    weapon('balloony', -1840, -1730, zr(-1730) + 4)
    jumppad(-900, -1720, 0, (-1820, -1720, zr(-1720)), zr(-1720) + 260, 'pad_shed_roof')
    mdl_c('pad_ddmix/trashcan/garbage_bag_group.md3', -1310, -1760, 0, 1.5, 0)
    station(-1700, -1250, 0, 90)


# =================================================================================================== kennel
def little_house(spec):
    """walls (door + windows cut out), floor, two roof slope slabs and a ridge walk 4u proud of them"""
    x0, y0, x1, y1 = spec['rect']
    H = spec['H']; Hw = H - 8; t = spec['t']; ov = spec['ov']
    inner = T(spec['inner'])
    kt = lambda n: inner if abs(n[2]) < 0.5 else CAULK
    opens = {'n': [], 's': [], 'e': [], 'w': []}
    side, u0, u1, dh = spec['door']
    opens[side].append((u0, 0, u1, dh))
    for (sd, a, b, za, zb) in spec['wins']:
        opens[sd].append((a, za, b, zb))
    for (a, za, b, zb) in sub_rects((x0, 0, x1, Hw), opens['s']): A(box((a, y0, za), (b, y0 + t, zb), kt))
    for (a, za, b, zb) in sub_rects((x0, 0, x1, Hw), opens['n']): A(box((a, y1 - t, za), (b, y1, zb), kt))
    for (a, za, b, zb) in sub_rects((y0 + t, 0, y1 - t, Hw), opens['w']): A(box((x0, a, za), (x0 + t, b, zb), kt))
    for (a, za, b, zb) in sub_rects((y0 + t, 0, y1 - t, Hw), opens['e']): A(box((x1 - t, a, za), (x1, b, zb), kt))
    A(box((x0 + t, y0 + t, 0), (x1 - t, y1 - t, 4), {'top': inner, 'side': CAULK, 'bot': CAULK}))
    ym = (y0 + y1) / 2; rw = spec['ridge'] / 2
    zr = L.ridge_z(spec)
    for sg in (-1, 1):
        ye = y0 - ov if sg < 0 else y1 + ov
        yr = ym + sg * rw
        pts = []
        for yy in (ye, yr):
            ztop = L.roof_top(spec, yy)
            pts += [(x, yy, z) for x in (x0 - ov, x1 + ov) for z in (ztop, ztop - 24)]
        A(hull(pts, lambda n: CAULK if n[2] > 0.3 else (inner if n[2] < -0.3 else T('paint_white')), round_pts=False))
    A(box((x0 - ov, ym - rw, zr - 24), (x1 + ov, ym + rw, zr + 4), {'top': CAULK, 'bot': inner, 'side': T('paint_white')}))
    return zr


def kennel():
    x0, y0, x1, y1 = L.KENNEL
    dy0, dy1, dh = L.KEN_DOOR
    ym = (y0 + y1) / 2
    zr = little_house(L.KEN)
    H = L.KEN_WALL
    custom('kennel', 0, 0, 0)
    weapon('boaster', (x0 + x1) / 2 + 40, ym, 4)
    item('ammo_splasher', x1 - 60, y1 - 60, 4)
    item('item_speedy', (x0 + x1) / 2, ym, zr + 4)
    item('ammo_imperius', x0 + 40, ym, zr + 4)
    furn('dog_bowl', x0 - 110, y0 + 60, 0, 0, [((-70, -70, 0), (70, 70, 40))])
    mdl_c('pad_ball/pad_tennisball.md3', x0 - 160, y1 - 40, 0, 2.2, 0)
    light((x0 + x1) / 2, ym, H - 60, 160, '1 0.9 0.75')
    jumppad((x0 + x1) / 2, y0 - 300, 0, ((x0 + x1) / 2, ym, zr + 4), zr + 180, 'pad_kennel')
    route('kennel_door', (x0 - 300, (dy0 + dy1) / 2, 0), (x0 + 120, (dy0 + dy1) / 2, 4))
    timer_sound(2100, 1800, 400, 'sound/world/animal/dog_bark2.ogg', 'bark', 40, 20, volume=0.5)


def cubby_house():
    sp = L.CUBBY
    x0, y0, x1, y1 = sp['rect']
    zr = little_house(sp)
    custom('cubby', 0, 0, 0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    A(cyl(cx, cy, 90, 4, 162, WCLIP, 12))
    for a in (0, 2.1, 4.2):
        A(cyl(round(cx + math.cos(a) * 150), round(cy + math.sin(a) * 150), 36, 4, 92, WCLIP, 8))
    item('ammo_bubbleg', cx - 120, cy + 120, 4)
    item('item_armor_shard', cx + 160, cy - 140, 4)
    item('ammo_boaster', cx, cy, zr + 4)
    light(cx, cy, sp['H'] - 80, 220, '1 0.92 0.85')
    jumppad(cx, y0 - 320, 0, (cx, cy, zr + 4), zr + 170, 'pad_cubby')
    _, u0, u1, dh = sp['door']
    route('cubby_door', ((u0 + u1) / 2, y1 + 300, 0), ((u0 + u1) / 2, y1 - 160, 4))


def lawn_cover():
    """middle-of-the-lawn cover: clam-shell sandpit with its lid up, round garden bed with a cabbage tree, ride-on car"""
    sx, sy = L.SANDPIT
    custom('sandpit', sx, sy, 0)
    R = L.SAND_R
    ring(sx, sy, R - 18, R + 6, 0, L.SAND_RIM, WCLIP, 20)
    A(cyl(sx, sy, R - 30, 0, L.SAND_Z, {'top': T('sand'), 'side': CAULK, 'bot': CAULK}, 20))
    # the open lid: a dish standing behind the hinge, leaning back a little -> a slab of clip
    h = 2 * R * 0.98; lean = 2 * R * 0.17
    A(hull([(sx + u, sy + R + 20 + v, z) for u in (-R + 30, R - 30) for (v, z) in ((0, L.SAND_RIM), (50, L.SAND_RIM), (lean, L.SAND_RIM + h - 60), (lean + 40, L.SAND_RIM + h - 60))],
           WCLIP, round_pts=False))
    custom('bucket_spade', sx - 80, sy - 60, L.SAND_Z, 40)
    item('ammo_pumper', sx + 60, sy - 40, L.SAND_Z)
    bx, by = L.ROUND_BED
    custom('round_bed', bx, by, 0)
    A(cyl(bx, by, L.ROUND_BED_R - 40, 0, 36, {'top': T('soil'), 'side': T('soil'), 'bot': CAULK}, 20))
    custom('cabbage_tree_0', bx, by, 36, 30, mul=0.5)
    A(cyl(bx, by, 22, 140, 700, WCLIP, 8))
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        mdl_c('pad_ddmix/trashcan/bush.md3', bx + math.cos(a) * 80, by + math.sin(a) * 80, 36, 0.5, int(k * 120))
    A(cyl(bx, by, 130, 36, 140, WCLIP, 16))
    # toddler slide: walk up the chute (or take the pad... no: the chute) to the platform
    x0, y0, x1, y1 = L.SLIDE
    z = L.SLIDE_Z; run = L.SLIDE_RUN
    custom('slide', 0, 0, 0)
    A(box((x0, y0, z - 20), (x1, y1, z), WCLIP))
    for (x, y) in ((x0 + 14, y0 + 14), (x0 + 14, y1 - 14), (x1 - 14, y0 + 14), (x1 - 14, y1 - 14)):
        A(box((x - 12, y - 12, 0), (x + 12, y + 12, z - 20), WCLIP))
    A(hull([(x, y, zz) for y in (y0 + 10, y1 - 10) for (x, zz) in ((x1, z - 20), (x1, z), (x1 + run, 4), (x1 + run - 32, 0))], WCLIP, round_pts=False))
    A(hull([(x, y, zz) for y in (y0 - 14, y1 + 14) for (x, zz) in ((x0 - 160, 0), (x0 - 140, 0), (x0, z + 120), (x0 + 6, z + 120))], WCLIP, round_pts=False))
    route('slide_chute', (x1 + run + 100, (y0 + y1) / 2, 0), ((x0 + x1) / 2, (y0 + y1) / 2, z))
    item('item_armor_shard', (x0 + x1) / 2, (y0 + y1) / 2, z)
    furn('log_pile', 1020, 470, 0, 0, [((-216, -75, 0), (216, 75, 300))])
    furn('log_pile', 2160, -1250, 0, 90, [((-216, -75, 0), (216, 75, 300))])
    furn('log_pile', -2160, 720, 0, 90, [((-216, -75, 0), (216, 75, 300))])
    furn('bird_bath', -560, -1530, 0, 0, [((-60, -60, 0), (60, 60, 250)), ((-125, -125, 250), (125, 125, 312))])
    furn('compost', -120, -1560, 0, 0, [((-140, -140, 0), (140, 140, 440))])
    furn('pot_stack', 680, -1460, 0, 0, [((-60, -60, 0), (60, 60, 190))])
    # wheelie bins by the picnic table, more planters
    for (k, (x, y)) in enumerate(((1360, -560), (1360, -220))):
        furn(['bin_red', 'bin_yellow'][k], x, y, 0, 180 + k * 8, [((-160, -160, 0), (160, 160, 500))])
    for (k, (x, y)) in enumerate(((-300, -760), (-1000, -880), (-1400, -900))):
        furn(['planter_lemon', 'planter_flax', 'planter_lemon'][k], x, y, 0, k * 70, [((-110, -110, 0), (110, 110, 220))])
    cx, cy = L.TOY_CAR
    furn('toy_car', cx, cy, 0, 20, [((-260, -130, 0), (260, 130, 180)), ((-180, -120, 180), (100, 120, 300))])
    item('ammo_nipper', cx + 320, cy - 200, 0)


# =================================================================================================== picnic table
def picnic():
    tx, ty = L.TABLE
    custom('picnic_table', tx, ty, 0)
    hl, hw = L.TABLE_L / 2, L.TABLE_W / 2
    by = hw + L.BENCH_GAP
    A(box((tx - hl, ty - hw, L.TABLE_Z - 22), (tx + hl, ty + hw, L.TABLE_Z), WCLIP))
    for s_ in (-1, 1):
        A(box((tx - hl + 20, ty + s_ * by - L.BENCH_W / 2, L.BENCH_Z - 22), (tx + hl - 20, ty + s_ * by + L.BENCH_W / 2, L.BENCH_Z), WCLIP))
    for x in (tx - hl + 90, tx + hl - 90):
        for s_ in (-1, 1):
            p0 = (x, ty + s_ * (by + 40), 0); p1 = (x, ty + s_ * 60, L.TABLE_Z - 22)
            A(hull([(px + dx, py + dy, pz) for (px, py, pz) in (p0, p1) for dx in (-16, 16) for dy in (-14, 14)], WCLIP, round_pts=False))
    A(cyl(tx, ty, 12, L.TABLE_Z, L.PARASOL_Z - 100, WCLIP, 8))
    A(cyl(tx, ty, 60, 0, 30, WCLIP, 10))
    zt = L.TABLE_Z
    # lunch on the table (catalog pieces)
    for k, (dx, dy) in enumerate(((-260, -100), (-120, 110), (140, -110), (280, 100))):
        mdl_c('pad_plates/plate_hp%d.md3' % (k + 1), tx + dx, ty + dy, zt, 0.5, k * 40)
    mdl_c('pad_condiments/pad_ketchup.md3', tx - 40, ty + 60, zt, 0.9, 0)
    mdl_c('pad_condiments/pad_mustard.md3', tx + 20, ty + 70, zt, 0.9, 30)
    mdl_c('pad_tins/pad_coke.md3', tx + 200, ty + 30, zt, 0.6, 0)
    mdl_c('pad_tins/pad_pupsi.md3', tx - 200, ty - 20, zt, 0.6, 50)
    mdl_c('pad_tins/pad_coke_sd.md3', tx + 300, ty - 30, zt, 0.6, 80)
    mdl_c('pad_ddmix/diner/muffin_choco.md3', tx - 40, ty - 130, zt, 0.7, 20)
    mdl_c('pad_cake/pad_cakestand.md3', tx + 60, ty - 60, zt, 1.0, 0)
    item('item_armor_padshield', tx - 120, ty - 30, zt)
    item('ammo_balloony', tx + 200, ty + by, L.BENCH_Z)
    item('ammo_bubbleg', tx - 200, ty - by, L.BENCH_Z)
    jumppad(tx, ty - 600, 0, (tx + 60, ty - 60, zt), zt + 190, 'pad_table')
    spawn(tx + 600, ty + 300, 0, 200)
    spawn(tx - 500, ty - 600, 0, 30)


# =================================================================================================== sun lounger
def sun_lounger():
    lx, ly = L.LOUNGER
    custom('lounger', lx, ly, 0)
    hl, hw = L.LOUNGER_L / 2, L.LOUNGER_W / 2
    zs = L.LOUNGER_SEAT
    bt = math.radians(L.LOUNGER_BACK)
    back_l = 360
    xb = lx - hl + back_l * math.cos(bt)
    ztop = zs + back_l * math.sin(bt)
    A(box((round(xb), ly - hw, zs - 8), (lx + hl, ly + hw, zs), WCLIP))
    A(hull([(x, y, z) for y in (ly - hw, ly + hw) for (x, z) in ((xb, zs), (xb, zs - 8), (lx - hl, ztop), (lx - hl, ztop - 8))], WCLIP, round_pts=False))
    for x in (lx + hl - 40, xb + 50):
        for s_ in (-1, 1):
            A(box((round(x) - 8, ly + s_ * hw - 8, 0), (round(x) + 8, ly + s_ * hw + 8, zs - 8), WCLIP))
    # towel ramp from the foot end down to the lawn
    custom('towel_ramp', lx + hl, ly, 0)
    A(hull([(x, y, z) for y in (ly - 110, ly + 110) for (x, z) in ((lx + hl, zs), (lx + hl, 0), (lx + hl + L.TOWEL_RUN, 0))], WCLIP, round_pts=False))
    route('towel_ramp', (lx + hl + L.TOWEL_RUN + 120, ly, 0), (lx + hl - 100, ly, zs))
    route('lounger_back', (lx + hl - 100, ly, zs), (lx - hl + 40, ly, ztop))
    custom('lounger_bits', lx + 120, ly, zs)
    item('holdable_floater', lx + 200, ly - 40, zs)
    item('ammo_betty', lx - hl + 60, ly, ztop)
    custom('jandals', lx + 100, ly - hw - 120, 0, 20)
    spawn(lx, ly - 400, 0, 90)


# =================================================================================================== vege bed
def vege_bed():
    x0, y0, x1, y1 = L.VEGE
    t = 40
    sl = {'top': T('sleeper'), 'side': T('sleeper'), 'bot': CAULK}
    A(box((x0, y0, 0), (x1, y0 + t, L.VEGE_Z), sl)); A(box((x0, y1 - t, 0), (x1, y1, L.VEGE_Z), sl))
    A(box((x0, y0 + t, 0), (x0 + t, y1 - t, L.VEGE_Z), sl)); A(box((x1 - t, y0 + t, 0), (x1, y1 - t, L.VEGE_Z), sl))
    A(box((x0 + t, y0 + t, 0), (x1 - t, y1 - t, L.VEGE_SOIL), {'top': T('soil'), 'side': CAULK, 'bot': CAULK}))
    # brick steps up to the south rim
    for j in range(L.VEGE_STEPS):
        zt = 16 * (j + 1)
        ya = y0 - 28 * (L.VEGE_STEPS - j); yb = ya + 28
        A(box((x0 + 40, ya, 0), (x1 - 40, yb, zt), {'top': T('brick'), 'side': T('brick'), 'bot': CAULK}))
    route('vege_steps', ((x0 + x1) / 2, y0 - 28 * L.VEGE_STEPS - 160, 0), ((x0 + x1) / 2, y0 + 200, L.VEGE_SOIL))
    zs = L.VEGE_SOIL
    for k, yy in enumerate((-300, -60, 180, 400)):
        custom(f'tomato_{k % 3}', x1 - 90, yy, zs, k * 50)
        A(cyl(x1 - 90, yy, 10, zs, zs + 400, WCLIP, 6))
    for yy in (-380, -140, 100, 320):
        custom('lettuce', x0 + 110, yy, zs, int(yy) % 360)
    custom('carrots', (x0 + x1) / 2, 0, zs, 0)
    for k, yy in enumerate((-480, 470)):
        mdl_c('pad_sunflower/pad_sunflower_l.md3', x1 - 70, yy, zs, 1.05, 180 + k * 30)
    for yy in (-1100, 1200, 1700):
        mdl_c('pad_sunflower/pad_sunflower_l.md3', 2200, yy, 0, 1.1, 180)
    item('holdable_bambam', (x0 + x1) / 2, 260, zs)
    item('ammo_splasher', (x0 + x1) / 2 - 40, -300, zs)
    furn('wheelbarrow', 1650, 100, 0, 90, [((-310, -130, 0), (290, 130, 262))])
    custom('watering_can', 1500, 660, 0, 200)
    lbox(1500, 660, 0, 200, (-60, -60, 0), (60, 60, 150))


# =================================================================================================== lawn: clothesline, sprinkler, hose, ant hill, toys
def lawn():
    # rotary clothesline turning slowly in the breeze
    cx, cy = 820.0, 240.0
    custom('rotary_mast', cx, cy, 0)
    A(cyl(cx, cy, 16, 0, 860, WCLIP, 8))
    hz = 880
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, hz - 8), (cx + 8, cy + 8, hz + 8), ORIGIN), box((cx - 4, cy - 4, hz + 30), (cx + 4, cy + 4, hz + 38), NODRAW_NS)],
          model2=bblib.IQM['rotary_line'], speed=5, spawnflags=0, dmg=0)
    item('ammo_boaster', cx + 120, cy - 60, 0)
    # sprinkler + hose from the reel by the tap
    sx, sy = L.SPRINKLER
    custom('sprinkler_base', sx, sy, 0)
    A(cyl(sx, sy, 50, 0, 40, WCLIP, 10))
    M.ent('func_rotating', brushes=[box((sx - 8, sy - 8, 56), (sx + 8, sy + 8, 72), ORIGIN), box((sx - 4, sy - 4, 80), (sx + 4, sy + 4, 88), NODRAW_NS)],
          model2=bblib.IQM['sprinkler_arm'], speed=60, spawnflags=0, dmg=0)
    speaker(sx, sy, 80, 'sound/world/ambient/water_shower.ogg', volume=0.35)
    rx, ry = L.HOSE_REEL
    furn('hose_reel', rx, ry, 0, 90, [((-70, -130, 0), (70, 130, 360))])
    custom('hose_path', 0, 0, 0)
    item('ammo_splasher', rx + 220, ry - 40, 0)
    # ant hill (SECRET: walk into its entrance) + the ant trail marching round it
    ax, ay = L.ANTHILL
    custom('ant_hill', ax, ay, 0)
    corridor = box((ax - 40, ay, 0), (ax + 40, ay + L.ANT_R + 40, 70), CAULK)
    for (r0, z0, r1, z1) in ((L.ANT_R - 6, 0, L.ANT_R * 0.72, 34), (L.ANT_R * 0.72, 34, L.ANT_R * 0.42, 62), (L.ANT_R * 0.42, 62, 8, L.ANT_H - 4)):
        b = frustum(ax, ay, r0, z0, r1, z1, WCLIP, 16)
        for p in (carve(b, [corridor]) if z0 < 64 else [b]):
            A(p)
    M.ent('trigger_teleport', brushes=[box((ax - 30, ay + 10, 2), (ax + 30, ay + 70, 60), TRIG)], target='colony_in')
    M.ent('trigger_multiple', brushes=[box((ax - 30, ay + 80, 2), (ax + 30, ay + 120, 60), TRIG)], target='secret_snd', wait=2)
    speaker(ax, ay + 60, 90, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('func_rotating', brushes=[box((ax - 8, ay - 8, 0), (ax + 8, ay + 8, 16), ORIGIN), box((ax - 4, ay - 4, 40), (ax + 4, ay + 4, 48), NODRAW_NS)],
          model2=bblib.IQM['ant_trail'], speed=-4, spawnflags=0, dmg=0)
    # flower border along the south fence (brick edge, soil, flowers), leaving room round the ant hill
    for (xa, xb) in ((-1340, ax - L.ANT_R - 80), (ax + L.ANT_R + 80, 1600)):
        A(box((xa, L.YS, 0), (xb, L.YS + 120, 40), {'top': T('soil'), 'side': T('brick'), 'bot': CAULK}))
        n = int((xb - xa) // 170)
        fl = ['pad_ddmix/plants/tulip1.md3', 'pad_ddmix/plants/flower_pink.md3', 'pad_ddmix/plants/tulip2.md3', 'pad_ddmix/plants/flower_yellow.md3']
        for k in range(n):
            x = xa + 85 + k * (xb - xa - 170) / max(1, n - 1)
            mdl_c(fl[k % 4], x, L.YS + 60, 40, 0.5 if 'tulip' in fl[k % 4] else 0.42, (k * 61) % 360)
    item('ammo_pumper', -400, L.YS + 200, 0)
    # gnomes, cricket, toys, planters
    furn('gnome', ax + 260, ay + 40, 0, 120, [((-36, -36, 0), (36, 36, 200))])
    furn('gnome_b', -1900, 700, 0, 20, [((-36, -36, 0), (36, 36, 200))])
    furn('gnome', 1500, 1500, 0, 230, [((-36, -36, 0), (36, 36, 200))])
    custom('cricket', 300, 1150, 0, 270)
    A(box((285, 1100, 0), (315, 1200, 360), WCLIP))
    custom('frisbee', -1000, -600, 0)
    mdl_c('pad_ball/pad_soccerball.md3', 1400, 320, 0, 1.6, 0)
    A(cyl(1400, 320, 56, 0, 120, WCLIP, 10))
    for (k, (x, yy)) in enumerate(((-2150, 300), (-2150, -700), (1050, 1500), (-1100, -1500))):
        furn(['planter_flax', 'planter_lemon'][k % 2], x, yy, 0, k * 40, [((-100, -100, 0), (100, 100, 200))])
    mdl_c('pad_ddmix/backyard/tire.md3', 2080, -1700, 0, 0.6, 90)
    A(box((2040, -1780, 0), (2120, -1620, 150), WCLIP))
    rng = np.random.default_rng(9)
    busy = [(L.VEGE[0] - 40, L.VEGE[1] - 300, L.VEGE[2], L.VEGE[3] + 40), (L.CUBBY['rect'][0] - 60, L.CUBBY['rect'][1] - 60, L.CUBBY['rect'][2] + 60, L.CUBBY['rect'][3] + 60),
            (L.SANDPIT[0] - 280, L.SANDPIT[1] - 280, L.SANDPIT[0] + 280, L.SANDPIT[1] + 340), (L.ROUND_BED[0] - 220, L.ROUND_BED[1] - 220, L.ROUND_BED[0] + 220, L.ROUND_BED[1] + 220),
            (L.SLIDE[0] - 180, L.SLIDE[1] - 40, L.SLIDE[2] + L.SLIDE_RUN, L.SLIDE[3] + 40), (L.SHED[0], L.SHED[1], L.SHED[2] + 80, L.SHED[3] + 80),
            (L.KENNEL[0] - 80, L.KENNEL[1] - 80, L.KENNEL[2] + 80, L.KENNEL[3] + 80), (L.DECK[0], L.DECK[1] - 400, L.DECK[2] + 400, L.DECK[3])]
    nt = 0
    while nt < 40:
        x, yy = rng.uniform(-2200, 2200), rng.uniform(-1900, 1350)
        if any(a < x < c and b < yy < d for (a, b, c, d) in busy): continue
        custom(f'tuft_{nt % 3}', round(x), round(yy), 0, int(rng.uniform(0, 360)), lit=False); nt += 1
    # items + spawns on the open lawn
    weapon_ammo = [('ammo_bubbleg', 0, -900), ('ammo_boaster', -1700, -400), ('ammo_nipper', 400, 0), ('ammo_nipper', -1100, 1100),
                   ('ammo_nipper', 1700, -1700), ('ammo_nipper', 1400, 400), ('item_armor_shard', -300, 1100), ('item_armor_shard', 820, -1350),
                   ('item_armor_shard', -1900, -1000), ('item_armor_shard', 2000, 1500), ('item_jumper', -2000, 1100)]
    for (c, x, yy) in weapon_ammo:
        item(c, x, yy, 0)
    for (x, yy, a) in ((-200, -300, 90), (1600, 700, 180), (-1000, 500, 0), (200, -1500, 90), (1100, -300, 150), (-2000, -200, 0)):
        spawn(x, yy, 0, a)


# =================================================================================================== secret: the ant colony
def colony():
    F = L.COLONY
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('soil_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('soil_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('soil_wall'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    # earth pillars divide it into chambers
    for k, (x, y) in enumerate(((-420, -200), (420, -200), (-420, 330), (420, 330))):
        custom(f'pillar_{k}', x, y, z0)
        r = (100 + 15 * k)
        A(cyl(x, y, round(r * 0.95), z0, z1, WCLIP, 12))
    custom('queen', 0, 470, z0, 270)
    A(box((-80, 380, z0), (80, 620, z0 + 120), WCLIP))
    item('item_padpower', 0, 300, z0)
    custom('larvae', -680, 420, z0)
    item('item_revival', -680, 200, z0)
    custom('seed_pile', 700, 540, z0, 200)
    A(box((600, 450, z0), (780, 630, z0 + 60), WCLIP))
    item('holdable_killerducks', 680, 160, z0)
    item('ammo_imperius', 0, -300, z0)
    for (x, y, a) in ((-200, 0, 30), (250, 100, 200), (-650, -450, 60), (600, -500, 120), (100, 200, 290)):
        custom('ant', x, y, z0, a, mul=1.6)
    A(sign_box((-300, y0, z0 + 300), (300, y0 + 4, z0 + 360), T('sign_colony'), 1024, 128, facing='n'))
    M.ent('misc_teleporter_dest', (0, -100, z0 + 24), targetname='colony_in', angle=90)
    mdl_c('pad_teleporter/padtp_orange.md3', 0, -560, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -596, z0 + 2), (36, -524, z0 + 90), TRIG)], target='colony_out')
    M.ent('misc_teleporter_dest', (L.ANTHILL[0], L.ANTHILL[1] + 420, 24), targetname='colony_out', angle=90)
    for (x, y, c) in ((0, 0, '1 0.85 0.6'), (-600, 400, '1 0.9 0.7'), (600, 400, '1 0.9 0.7'), (0, 450, '1 0.8 0.5'), (0, -450, '0.9 0.9 1'),
                      (-650, -400, '1 0.9 0.75'), (650, -400, '1 0.9 0.75')):
        light(x, y, z0 + 240, 250, c)
    speaker(0, 0, z0 + 200, 'sound/world/ambient/water_drippling.ogg', volume=0.5)


# =================================================================================================== light + sound
def lights_and_sound():
    # soft fill in the house's shadow and under the pergola
    for x in (-1800, -900, 0, 900, 1800):
        light(x, 1700, 700, 700, '1 0.97 0.9')
    for x in (-1800, 0, 1800):
        for y in (-1400, 0):
            light(x, y, 1600, 900, '1 0.97 0.9')
    timer_sound(-1500, -2300, 900, 'sound/world/animal/blackbird.ogg', 'bird1', 25, 12, volume=0.6)
    timer_sound(2400, 600, 900, 'sound/world/animal/bird_blackcap.ogg', 'bird2', 31, 14, volume=0.6)
    speaker(0, -2300, 800, 'sound/world/animal/cicada_chirp.ogg', volume=0.35)
    speaker(-2500, 0, 800, 'sound/world/animal/cicada_chirp.ogg', volume=0.3)
    timer_sound(1400, 2000, 900, 'sound/world/machine/tv_upstairs.ogg', 'tv', 70, 30, volume=0.3)


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'jumppad_ns', 'origin', 'water', 'botclip', 'lattice')


def extra_models():
    pass


def main():
    bblib.STATE['out'] = OUT
    TX.make_textures()
    import bb_models
    bb_models.make()
    hull_and_ground(); house(); fences()
    deck(); grill(); paddling_pool(); shed(); kennel(); cubby_house(); lawn_cover(); picnic(); sun_lounger(); vege_bed(); lawn(); colony()
    lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (-1900, -1700, 1500), angles='20 40 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padbbq/build_bbq.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
