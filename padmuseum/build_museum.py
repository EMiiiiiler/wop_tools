#!/usr/bin/env python3
"""Midnight Museum - World of Padman FFA map generator (map 'wop_padmuseum').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_museum.py

Writes <OUT>/maps/wop_padmuseum.map, textures/padmuseum/*, models/padmuseum/*, scripts/padmuseum.shader and
scripts/wop_padmuseum.arena.

A natural history museum after closing time, human scale (64u per metre). x east, y north, ground floor z 0. Nine rooms
on a 3 x 3 grid round the great hall, a roof terrace over them all, the portico and forecourt to the south.

  Great hall      a T. rex you can walk up from the tail tip to the skull (Betty), a whale skeleton hanging under the
                  glass roof, an imperial stair up to the mezzanine ring, balconies into the side galleries.
  Ancient Egypt   a step pyramid (stair up the east face, Pumper on top) with a tunnel into the tomb (BamBam). SECRET:
                  walk into the open, glowing sarcophagus -> the pharaoh's treasury (sealed under the world).
  Planetarium     the copper dome rises through the roof; star projector, seats, an orrery turning in the dome. A pad
                  from the roof onto the dome top (Imperius), a fling pad back down.
  Ice Age         a woolly mammoth (pad onto its back, Boaster), moa skeletons, a sabre-tooth, Haast's eagle overhead.
  Gems            a walk-in geode lined with glowing amethyst (Splasher), a pad onto its top.
  Deep ocean      a giant squid in a glass tank (pad onto the tank, Balloony), sharks overhead.
  Foyer           ticket desk, gift shop (Bubble G), the front doors out to the portico.
  Stair towers    the night guard's security office (NW) and the staff room (NE); stairs up to the roof terrace.
  Roof terrace    plant, a water tank, a telescope; a pad up onto the great hall's glass roof.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import mu_textures as TX
import mulib

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padmuseum'
T = lambda n: 'padmuseum/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'marble_checker': (1.0, 1.0), 'marble': (1.0, 1.0), 'marble_dark': (1.0, 1.0), 'limestone': (1.0, 1.0), 'sandstone': (1.0, 1.0),
             'hieroglyphs': (1.0, 1.0), 'star_carpet': (0.75, 0.75), 'snow': (1.0, 1.0), 'roof_gravel': (1.0, 1.0), 'coffer': (1.0, 1.0),
             'ocean_wall': (1.0, 1.0), 'gem_wall': (0.75, 0.75), 'tomb_stone': (1.0, 1.0), 'gold_floor': (0.75, 0.75), 'concrete': (1.0, 1.0),
             'terrazzo': (1.0, 1.0), 'parquet': (0.5, 0.5), 'water': (1.0, 1.0), 'paint_red': (0.75, 0.75), 'paint_green': (0.75, 0.75),
             'paint_blue': (0.75, 0.75), 'paint_white': (0.75, 0.75), 'paint_dark': (0.75, 0.75), 'carpet_red': (0.75, 0.75),
             'wainscot': (0.75, 0.75), 'stair_tread': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '10', '_color': '0.8 0.85 1', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
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
    """one of our own MD3s (models/padmuseum), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = mulib.PLACE[name]
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
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padmuseum/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_museum.py\n')
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




# =================================================================================================== room skins
FLOOR = {'gems': 'marble_dark', 'foyer': 'marble_checker', 'ocean': 'terrazzo', 'egypt': 'sandstone', 'hall': 'marble_checker',
         'planet': 'star_carpet', 'stair_w': 'parquet', 'ice': 'snow', 'stair_e': 'parquet'}
WALL = {'gems': 'gem_wall', 'foyer': 'limestone', 'ocean': 'ocean_wall', 'egypt': 'hieroglyphs', 'hall': 'limestone', 'planet': 'paint_dark',
        'stair_w': 'paint_green', 'ice': 'paint_blue', 'stair_e': 'paint_red', 'out': 'limestone'}
CEILT = {'hall': 'coffer', 'foyer': 'coffer', 'planet': 'paint_dark', 'egypt': 'sandstone'}
HALL_OUT = (-1040, -1040, 1040, 1040)          # hall walls' outer faces


def room_at(x, y, z):
    if abs(x) < 1008 and abs(y) < 1008 and z < L.HALL_TOP: return 'hall'
    if z > L.CEIL + 1: return 'out'
    for nm, (a, b, c, d) in L.ROOMS.items():
        if nm != 'hall' and a < x < c and b < y < d: return nm
    return 'out'


def face_pts(b, f, V=None):
    V = b.verts() if V is None else V
    on = V[np.abs(V @ np.array(f.n) - f.d) < 0.5]
    return on if len(on) else V


def skin(b, top=None, bot=None, side=None):
    """walls: each side face gets the wall texture of the room it faces"""
    V = b.verts()
    for f in b.faces:
        on = face_pts(b, f, V); c = on.mean(0); n = np.array(f.n)
        if n[2] > 0.7: t = top or CAULK
        elif n[2] < -0.7: t = bot or CAULK
        elif side: t = side
        else:
            p = c + n * 40
            t = T(WALL[room_at(p[0], p[1], c[2])])
        f.tex = t; f.sc = wopmap.default_scale(t)
    return b


def texby(b, fn):
    """fn(sample points on the face, normal) -> texture"""
    V = b.verts()
    for f in b.faces:
        on = face_pts(b, f, V); c = on.mean(0)
        smp = [c] + [c + (p - c) * 0.8 for p in on]
        f.tex = fn(smp, np.array(f.n)); f.sc = wopmap.default_scale(f.tex)
    return b


# =================================================================================================== hull, ground, outside
FC = (-1536, -2944, 1536, -2112)               # forecourt in front of the portico
FOOT = (-2368, -2112, 2368, 2112)              # building footprint (outer wall faces)


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
    # outside ground (the city park round the museum), forecourt paving, room floors
    for r in sub_rects((x0, y0, x1, y1), [FOOT, FC]):
        A(box((r[0], r[1], z0), (r[2], r[3], 0), {'top': T('concrete'), 'side': CAULK, 'bot': CAULK}))
    A(box((FC[0], FC[1], z0), (FC[2], FC[3], 0), {'top': T('terrazzo'), 'side': CAULK, 'bot': CAULK}))
    for nm, (a, b, c, d) in L.ROOMS.items():
        A(box((a, b, z0), (c, d, 0), {'top': T(FLOOR[nm]), 'side': CAULK, 'bot': CAULK}))
    for r in sub_rects(FOOT, [(-2304, -2048, 2304, 2048)]):
        A(box((r[0], r[1], z0), (r[2], r[3], 0), {'top': T('limestone'), 'side': CAULK, 'bot': CAULK}))
    # players stay in the forecourt and on the museum (clip round everything else, up to the sky)
    for r in sub_rects((x0, y0, x1, y1), [FOOT, FC]):
        A(box((r[0], r[1], 0), (r[2], r[3], z1), CLIP))
    # forecourt balustrade (low wall) along its three open sides
    bal = {'top': T('marble'), 'side': T('limestone'), 'bot': CAULK}
    A(box((FC[0], FC[1], 0), (FC[0] + 32, FC[3], 64), bal))
    A(box((FC[2] - 32, FC[1], 0), (FC[2], FC[3], 64), bal))
    A(box((FC[0] + 32, FC[1], 0), (FC[2] - 32, FC[1] + 32, 64), bal))


# =================================================================================================== building shell
def wall_x(x, y0, y1, z0, z1, holes=(), t=16):
    for (a, za, c, zb) in sub_rects((y0, z0, y1, z1), list(holes)):
        A(skin(box((x - t, a, za), (x + t, c, zb), CAULK)))


def wall_y(y, x0, x1, z0, z1, holes=(), t=16):
    for (a, za, c, zb) in sub_rects((x0, z0, x1, z1), list(holes)):
        A(skin(box((a, y - t, za), (c, y + t, zb), CAULK)))


CLER = [(-700, -420), (-150, 150), (420, 700)]    # clerestory windows (u ranges) in the hall walls above the roof
CLER_Z = (800, 1150)


def door_holes(axis, fixed):
    out = [(u0, 0, u1, h) for (ax, f, u0, u1, h) in L.DOORS if ax == axis and f == fixed]
    return out


def shell():
    C_, R_, HT = L.CEIL, L.ROOF, L.HALL_TOP
    mz = L.MEZZ_Z; mh = L.MEZZ_DOOR_H
    # interior walls at x = +-1024
    for x in (-1024, 1024):
        holes = door_holes('x', x)
        wall_x(x, -2048, -1040, 0, C_, holes)
        wall_x(x, 1040, 2048, 0, C_, holes)
        tall = holes + [(-160, mz, 160, mz + mh)] + [(a, CLER_Z[0], b, CLER_Z[1]) for (a, b) in CLER]
        wall_x(x, -1040, 1040, 0, HT, tall)
        for (a, b) in CLER:
            A(box((x - 4, a, CLER_Z[0]), (x + 4, b, CLER_Z[1]), T('glass')))
    for y in (-1024, 1024):
        holes = door_holes('y', y)
        wall_y(y, -2304, -1040, 0, C_, holes)
        wall_y(y, 1040, 2304, 0, C_, holes)
        tall = holes + [(a, CLER_Z[0], b, CLER_Z[1]) for (a, b) in CLER]
        if y > 0: tall.append((-160, mz, 160, mz + mh))
        wall_y(y, -1008, 1008, 0, HT, tall)
        for (a, b) in CLER:
            A(box((a, y - 4, CLER_Z[0]), (b, y + 4, CLER_Z[1]), T('glass')))
    # outer walls (64 thick outside the rooms), parapet to ROOF + 32; the portico joins the south roof
    top = R_ + 32
    px0, py0, px1, py1 = L.PORTICO
    fd = L.FRONT_DOOR
    # (one piece per room so each inner face takes that room's wall texture)
    xs = [(-2368, -1024), (-1024, 1024), (1024, 2368)]; ys = [(-2048, -1024), (-1024, 1024), (1024, 2048)]
    for (u0, u1) in xs:
        for (a, za, c, zb) in sub_rects((u0, 0, u1, top), [(fd[0], 0, fd[1], fd[2]), (px0, R_, px1, top)]):
            A(skin(box((a, -2112, za), (c, -2048, zb), CAULK), top=T('roof_gravel') if zb == R_ else T('marble')))
        A(skin(box((u0, 2048, 0), (u1, 2112, top), CAULK), top=T('marble')))
    for (u0, u1) in ys:
        A(skin(box((-2368, u0, 0), (-2304, u1, top), CAULK), top=T('marble')))
        A(skin(box((2304, u0, 0), (2368, u1, top), CAULK), top=T('marble')))
    # ceilings / roof terrace slab (per room, minus the hall, stair holes and the dome)
    holes = [HALL_OUT]
    for s in (-1, 1):
        holes.append(L.tower_flights(s)[3])
    dx, dy = L.DOME
    dome_sq = (dx - L.DOME_R - 16, dy - L.DOME_R - 16, dx + L.DOME_R + 16, dy + L.DOME_R + 16)
    for nm, rect in L.ROOMS.items():
        if nm == 'hall': continue
        for r in sub_rects(rect, holes + ([dome_sq] if nm == 'planet' else [])):
            A(box((r[0], r[1], C_), (r[2], r[3], R_), {'top': T('roof_gravel'), 'bot': T(CEILT.get(nm, 'paint_white')), 'side': T('paint_white')}))
    sq = box((dome_sq[0], dome_sq[1], C_), (dome_sq[2], dome_sq[3], R_), {'top': T('roof_gravel'), 'bot': T('paint_dark'), 'side': T('paint_dark')})
    for p in carve(sq, [cyl(dx, dy, L.DOME_R, C_ - 8, R_ + 8, CAULK, 32)]):
        A(texby(p, lambda smp, n: T('roof_gravel') if n[2] > 0.7 else T('paint_dark')))
    # the great hall's skylight (walkable glass roof)
    A(box((-1040, -1040, HT), (1040, 1040, HT + 16), T('glass')))
    custom('skylight_frame', 0, 0, 0)


# =================================================================================================== great hall
def great_hall():
    mz = L.MEZZ_Z; e = 1008 - L.MEZZ_W            # ring inner edge 816
    slab = {'top': T('parquet'), 'bot': T('coffer'), 'side': T('marble')}
    A(box((-1008, -1008, mz - 16), (1008, -e, mz), slab))
    A(box((-1008, e, mz - 16), (1008, 1008, mz), slab))
    A(box((-1008, -e, mz - 16), (-e, e, mz), slab))
    A(box((e, -e, mz - 16), (1008, e, mz), slab))
    lx0, ly0, lx1, ly1 = L.LANDING
    A(box((lx0, ly0, mz - 16), (lx1, ly1, mz), slab))
    # imperial stair: two flights rising from the side walls to the central landing, open underneath
    y0, y1 = L.STAIR_Y
    for s in (-1, 1):
        for (x0, x1, zt) in L.flight_steps(s):
            def zb(x): return max(0.0, (768 - abs(x)) / 2 - 24)
            pts = []
            for x in (x0, x1):
                for y in (y0, y1):
                    pts += [(x, y, zb(x)), (x, y, zt)]
            A(hull(pts, {'top': T('carpet_red'), 'side': T('marble'), 'bot': T('marble')}, round_pts=False))
        route(f'grand_{"w" if s < 0 else "e"}', (s * 900, -736, 0), (s * 300, -912, mz))
    # balustrade (low, shoot over it) round the ring's inner edge and the landing
    rail = {'top': T('marble'), 'side': T('marble'), 'bot': CAULK}
    rz = (mz, mz + 40)
    A(box((-e, -e - 8, rz[0]), (lx0, -e, rz[1]), rail)); A(box((lx1, -e - 8, rz[0]), (e, -e, rz[1]), rail))
    A(box((-e, e, rz[0]), (e, e + 8, rz[1]), rail))
    A(box((-e - 8, -e - 8, rz[0]), (-e, e + 8, rz[1]), rail)); A(box((e, -e - 8, rz[0]), (e + 8, e + 8, rz[1]), rail))
    A(box((lx0, ly1 - 8, rz[0]), (lx1, ly1, rz[1]), rail))
    # columns under the ring
    for (x, y) in ((-e - 40, -e - 40), (e + 40, -e - 40), (-e - 40, e + 40), (e + 40, e + 40), (-e - 40, -400), (e + 40, -400), (-e - 40, 400),
                   (e + 40, 400), (-400, e + 40), (400, e + 40)):
        custom('column_s', x, y, 0, mul=(mz - 16) / 384)
        A(cyl(x, y, 28, 0, mz - 16, WCLIP, 12))
    # T. rex on its plinth, walkable from the tail tip to the skull
    tx, ty = L.TREX
    px0, py0, px1, py1, ph = L.TREX_PLINTH
    A(box((px0, py0, 0), (px1, py1, ph), {'top': T('marble_dark'), 'side': T('marble'), 'bot': CAULK}))
    custom('trex', tx, ty, 0)
    P = L.TREX_PATH; w = L.TREX_W / 2
    for (ya, za), (yb, zb_) in zip(P, P[1:]):
        pts = []
        for (y, z) in ((ya, za), (yb, zb_)):
            pts += [(tx + sx * w, y, max(ph, z - 16)) for sx in (-1, 1)] + [(tx + sx * w, y, z) for sx in (-1, 1)]
        A(hull(pts, WCLIP, round_pts=False))
    A(box((tx - 56, -60, 64), (tx + 56, 100, 196), WCLIP))                  # rib cage
    for s in (-1, 1):
        a, b = sorted((tx + s * 24, tx + s * 72))
        A(box((a, 110, ph), (b, 180, 170), WCLIP))                           # legs
    A(box((tx - 28, -330, 232), (tx + 28, -205, 284), WCLIP))                # skull
    weapon('betty', tx, -250, 300)
    route('trex_spine', (tx, 760, 0), (tx, -250, 300))
    custom('whale', L.WHALE[0], L.WHALE[1], L.WHALE_Z)
    # floor exhibits, benches
    for (o, x, y, a) in (('case_skull', -600, 560, 0), ('case_ammonite', 600, 560, 0), ('case_trilobite', -620, -300, 90), ('case_egg', 620, -300, 90)):
        furn(o, x, y, 0, a, [((-40, -60, 0), (40, 60, 200))])
    for (x, y, a) in ((-560, 150, 90), (560, 150, 90)):
        furn('bench', x, y, 0, a, [((-130, -36, 0), (130, 36, 40))])
    PB = [((-10, -124, 0), (10, 124, 236))]
    for (x, y, a) in ((-240, -580, 90), (240, -580, 90), (-720, 200, 0), (720, -200, 0), (0, 880, 90), (900, 140, 0), (-900, -140, 0)):
        furn('panel_dino', x, y, 0, a, PB)
    mdl_c('ente/bonea.md3', -330, 800, 0, 10.0, 30); mdl_c('ente/boneb.md3', 360, 840, 0, 10.0, 300)
    # mezzanine: more cases + benches
    for (o, x, y, a) in (('case_crystal', -912, 560, 0), ('case_skull', 912, -560, 180), ('case_egg', -912, -400, 0), ('case_ammonite', 600, 912, 90)):
        furn(o, x, y, mz, a, [((-40, -60, 0), (40, 60, 200))])
    furn('bench', -400, 900, mz, 0, [((-130, -36, 0), (130, 36, 40))])
    furn('bench', 912, 400, mz, 90, [((-130, -36, 0), (130, 36, 40))])
    mdl_box('ente/padstatue_gold.md3', 560, -912, mz, 0.7, 90)
    # items
    item('item_armor_padshield', 0, 912, mz)
    item('ammo_betty', -560, -912, mz); item('ammo_betty', -300, -736, 0)
    item('ammo_boaster', 700, 0, 0); item('ammo_splasher', 912, 0, mz)
    item('item_armor_shard', -700, 800, 0); item('item_armor_shard', 700, 800, 0)
    item('ammo_nipper', -912, 100, mz)
    station(-680, 440, 0, 0)
    for (x, y, a) in ((-700, 300, 0), (700, -100, 180), (0, -900, 90), (-600, 912, 270), (912, -200, 180)):
        spawn(x, y, mz if abs(y) > 816 or abs(x) > 816 else 0, a)


def balconies():
    mz = L.MEZZ_Z
    rail = {'top': T('marble'), 'side': T('marble'), 'bot': CAULK}
    slab = {'top': T('parquet'), 'bot': T('coffer'), 'side': T('marble')}
    for k, (x0, y0, x1, y1) in L.BALCONIES.items():
        A(box((x0, y0, mz - 16), (x1, y1, mz), slab))
        if k == 'n':
            A(box((x0, y1 - 8, mz), (x1, y1, mz + 40), rail)); A(box((x0, y0, mz), (x0 + 8, y1 - 8, mz + 40), rail)); A(box((x1 - 8, y0, mz), (x1, y1 - 8, mz + 40), rail))
            route('balcony_n', (0, 912, mz), (0, 1150, mz))
        else:
            s = -1 if k == 'w' else 1
            xo = x0 if s < 0 else x1 - 8
            A(box((xo, y0, mz), (xo + 8, y1, mz + 40), rail))
            ia, ib = (x0 + 8, x1) if s < 0 else (x0, x1 - 8)
            A(box((ia, y0, mz), (ib, y0 + 8, mz + 40), rail)); A(box((ia, y1 - 8, mz), (ib, y1, mz + 40), rail))
            route(f'balcony_{k}', (s * 912, 0, mz), (s * 1140, 0, mz))
    item('ammo_pumper', -1150, 120, mz)
    item('ammo_betty', 1150, -120, mz)
    item('ammo_balloony', 100, 1150, mz)


# =================================================================================================== egypt: step pyramid + tomb
def egypt():
    cx, cy = L.PYR
    tx0, ty0, tx1, ty1, th = L.TOMB
    ux0, ux1, uh = L.TOMB_TUNNEL
    st = L.pyr_stairs()
    cut_st = box((st[-1][0], -64, 0), (st[0][2] + 1, 64, 400), CAULK)
    cut_ch = box((tx0, ty0, 0), (tx1, ty1, th), CAULK)
    cut_tu = box((ux0, cy - L.PYR_BASE / 2 - 16, 0), (ux1, ty0 + 1, uh), CAULK)
    def inside(p):
        for (a, b, c, d, z) in ((tx0, ty0, tx1, ty1, th), (ux0, -1000, ux1, ty0, uh)):
            if a - 0.5 <= p[0] <= c + 0.5 and b - 0.5 <= p[1] <= d + 0.5 and p[2] <= z + 0.5: return True
        return False
    def tx_(smp, n):
        q = [p + n * 4 for p in smp]
        if any(inside(p) for p in q): return T('tomb_stone')
        if n[2] > 0.7: return T('sandstone')
        if n[2] < -0.7: return CAULK
        return T('limestone')
    for k in range(L.PYR_TIERS):
        x0, y0, x1, y1, z0, z1 = L.pyr_tier(k)
        b = box((x0, y0, z0), (x1, y1, z1), CAULK)
        for p in carve(b, [cut_st, cut_ch, cut_tu]):
            A(texby(p, tx_))
    for (x0, y0, x1, y1, z) in st:
        A(box((x0, y0, 0), (x1, y1, z), {'top': T('sandstone'), 'side': T('limestone'), 'bot': CAULK}))
    route('pyramid', (-1100, 0, 0), (-1600, 0, 192))
    route('tomb', (ux0 + 32, -560, 0), (-1640, -60, 0))
    custom('pyr_cap', -1780, 100, 192, mul=0.6)
    A(box((-1808, 72, 192), (-1752, 128, 230), WCLIP))
    weapon('pumper', -1580, -40, 192)
    # tomb chamber: the open sarcophagus is the way into the treasury
    sx, sy = L.SARC; k = L.SARC_SC
    custom('sarc_open', sx, sy, 0, mul=k)
    A(box((sx - 130 * k, sy - 56 * k, 0), (sx + 130 * k, sy + 56 * k, 40 * k), WCLIP))
    M.ent('trigger_teleport', brushes=[box((sx - 85, sy - 40, 40 * k + 1), (sx + 85, sy + 40, 100), TRIG)], target='treasury_in')
    custom('canopic', tx1 - 50, ty0 + 70, 0, 90)
    custom('treasure_b', tx0 + 70, ty0 + 70, 0, 30, mul=0.6)
    item('holdable_bambam', tx1 - 70, -60, 0)
    trigger_sound((ux0, ty0 - 100, 2), (ux1, ty0 - 20, 100), 'sound/world/misc/secret_found.ogg', 'tomb_secret', 30, volume=0.6)
    speaker(-1696, 0, 100, 'sound/world/ambient/droplets_echoing.ogg', volume=0.5)
    light(-1696, -100, 110, 140, '1 0.7 0.4'); light(sx, sy, 70, 90, '0.4 1 0.6')
    light(-1728, -300, 90, 80, '1 0.7 0.4')
    # gallery pieces
    for y in (-700, 700):
        furn('pharaoh', -2190, y, 0, 0, [((-70, -60, 0), (70, 60, 300))])
    furn('anubis', -1500, -820, 0, 90, [((-114, -54, 0), (114, 54, 210))])
    for y in (-860, 860):
        furn('obelisk', -1180, y, 0, 0, [((-60, -60, 0), (60, 60, 40)), ((-36, -36, 40), (36, 36, 540))])
    furn('sarc', -1440, 700, 0, 0, [((-130, -56, 0), (130, 56, 100))])
    for y in (-300, 300):
        furn('lotus_column', -2200, y, 0, 0, [((-50, -50, 0), (50, 50, 640 - 40))])
    for x in (-1960, -1720):
        furn('mummy_case', x, 950, 0, 270, [((-50, -50, 0), (50, 50, 250))])
    furn('case_scarab', -2190, 0, 0, 0, [((-40, -60, 0), (40, 60, 200))])
    mdl_box('pad_ddmix/anteroom/vase.md3', -2210, -940, 0, 0.5, 0)
    mdl_box('pad_ddmix/anteroom/vase.md3', -1380, 950, 0, 0.5, 0)
    item('ammo_pumper', -2150, -500, 0); item('ammo_boaster', -1250, -500, 0); item('ammo_imperius', -2250, 940, 0)
    item('item_armor_shard', -1660, 0, 192)
    for (x, y, a) in ((-1300, 500, 180), (-2000, -800, 45), (-1900, 600, 300)):
        spawn(x, y, 0, a)


# =================================================================================================== planetarium
def dome_shell():
    dx, dy = L.DOME; R_ = L.ROOF
    hs = [0, 120, 220, 300, 360]
    n = 32
    for (ha, hb) in zip(hs, hs[1:]):
        for kk in range(n):
            a0, a1 = 360 * kk / n, 360 * (kk + 1) / n
            pts = []
            for h in (ha, hb):
                ro = L.dome_r(h) - 2; ri = max(4.0, ro - 16)
                for a in (a0, a1):
                    for r in (ri, ro):
                        x, y = L.ang_pt(dx, dy, r, a)
                        pts.append((x, y, R_ + h))
            A(hull(pts, WCLIP, round_pts=False))
    # top: a solid frustum to the lantern platform
    A(hull([(x, y, R_ + 360) for (x, y) in ngon(dx, dy, L.dome_r(360) - 2, n, 0)] +
           [(x, y, R_ + L.DOME_H) for (x, y) in ngon(dx, dy, L.DOME_TOP_R, n, 0)], WCLIP, round_pts=False))


def planetarium():
    dx, dy = L.DOME; R_ = L.ROOF
    custom('dome', dx, dy, R_)
    dome_shell()
    custom('projector', dx, dy, 0)
    A(cyl(dx, dy, 50, 0, 100, WCLIP, 12))
    lbox(dx, dy, 100, 0, (-44, -140, 30), (44, 140, 110))
    custom('seats_a', dx, dy, 0, 180); custom('seats_b', dx, dy, 0, 180)
    M.ent('func_rotating', brushes=[box((dx - 8, dy - 8, L.ORRERY_Z - 8), (dx + 8, dy + 8, L.ORRERY_Z + 8), ORIGIN),
                                    box((dx - 4, dy - 4, L.ORRERY_Z + 40), (dx + 4, dy + 4, L.ORRERY_Z + 48), NODRAW_NS)],
          model2=mulib.IQM['orrery'], speed=4, spawnflags=0, dmg=0)
    furn('meteorite', 2160, 860, 0, 0, [((-50, -50, 0), (50, 50, 170))])
    mdl_c('ente/deadalienA.md3', 2160, 620, 0, 2.0, 200)
    furn('case_crystal', 2190, -860, 0, 180, [((-40, -60, 0), (40, 60, 200))])
    for (x, y, a) in ((1180, -620, 0), (1180, 620, 0)):
        furn('panel_space', x, y, 0, a, [((-10, -124, 0), (10, 124, 236))])
    # dome top (Imperius): pad up from the roof, a fling pad back down
    # (bots land where they first touch the top - the north edge - so the fling pad sits on the far, south-east side)
    jumppad(dx, 880, R_, (dx, dy + 40, R_ + L.DOME_H), R_ + L.DOME_H + 150, 'pad_dome')
    weapon('imperius', dx - 60, dy - 20, R_ + L.DOME_H)
    jumppad(dx + 90, dy - 90, R_ + L.DOME_H, (2050, -1350, R_), R_ + L.DOME_H + 80, 'pad_dome_off', glow=False)
    item('ammo_splasher', 1300, 700, 0); item('ammo_betty', 2150, 0, 0); item('item_armor_shard', 1250, -700, 0)
    speaker(dx, dy, 300, 'sound/world/machine/fan_pc.ogg', volume=0.4)
    for (x, y, a) in ((1250, 300, 0), (2150, -500, 135), (1700, -800, 90)):
        spawn(x, y, 0, a)


# =================================================================================================== ice age
def ice_age():
    mx, my = L.MAMMOTH; bk = L.MAMMOTH_BACK
    custom('mammoth', mx, my, 0)
    for (y0, y1) in ((-90, -30), (80, 140)):
        for s in (-1, 1):
            a, b = sorted((mx + s * 20, mx + s * 76))
            A(box((a, my + y0, 0), (b, my + y1, 100), WCLIP))
    A(box((mx - 70, my - 130, 100), (mx + 70, my + 150, bk), WCLIP))
    weapon('boaster', mx, my + 30, bk)
    jumppad(mx - 320, my + 80, 0, (mx, my - 10, bk), bk + 140, 'pad_mammoth')
    for (nm, x, y, a) in (('moa', 250, 1720, 300), ('moa_s', 380, 1640, 250)):
        custom(nm, x, y, 0, a)
        A(cyl(x, y, 28, 0, 180, WCLIP, 8))
    custom('sabretooth', 700, 1420, 0, 200)
    lbox(700, 1420, 0, 200, (-80, -80, 0), (80, 120, 64))
    lbox(700, 1420, 0, 200, (-34, -80, 64), (34, 110, 140))
    for x in (-450, 450):
        custom('dio_rocks', x, 1880, 0)
        A(box((x - 310, 1810, 0), (x + 310, 2040, 110), WCLIP))
    custom('eagle', 100, 1380, L.CEIL)
    custom('dio_rocks', 0, 1430, 0)
    A(box((-310, 1360, 0), (310, 1590, 110), WCLIP))
    for (x, y, a) in ((-760, 1250, 0), (800, 1700, 90)):
        furn('panel_ice', x, y, 0, a, [((-10, -124, 0), (10, 124, 236))])
    A(sign_box((-256, 2044, 470), (256, 2048, 534), T('sign_ice'), 512, 128, facing='s'))
    item('ammo_bubbleg', -800, 1300, 0); item('ammo_pumper', 800, 1200, 0); item('ammo_boaster', 0, 1700, 0); item('item_speedy', -850, 1900, 0)
    speaker(0, 1600, 300, 'sound/world/ambient/wind_icy.ogg', volume=0.35)
    for (x, y, a) in ((-700, 1250, 0), (650, 1850, 225), (0, 1500, 90)):
        spawn(x, y, 0, a)


# =================================================================================================== gems: walk-in geode
def gems():
    gx, gy = L.GEODE
    custom('geode', gx, gy, 0)
    hs = [0, 100, 180, 240, 300]
    n = 48
    da = L.GEODE_DOOR
    for (ha, hb) in zip(hs, hs[1:]):
        for kk in range(n):
            a0, a1 = 360 * kk / n, 360 * (kk + 1) / n
            c = (a0 + a1) / 2
            if abs(((c - da + 180) % 360) - 180) < 18: continue
            pts = []
            for h in (ha, hb):
                ro = L.geode_r(h) * 0.95 - 2; ri = ro - 16
                for a in (a0, a1):
                    for r in (ri, ro):
                        x, y = L.ang_pt(gx, gy, r, a)
                        pts.append((x, y, h))
            A(hull(pts, WCLIP, round_pts=False))
    A(hull([(x, y, 300) for (x, y) in ngon(gx, gy, L.geode_r(300) * 0.95 - 2, 24, 0)] +
           [(x, y, L.GEODE_H) for (x, y) in ngon(gx, gy, L.geode_r(L.GEODE_H) * 0.95 - 2, 24, 0)], WCLIP, round_pts=False))
    weapon('splasher', gx, gy - 40, 0)
    route('geode', (gx, gy + 460, 0), (gx, gy - 40, 0))
    light(gx, gy, 160, 120, '0.8 0.4 1')
    jumppad(gx - 440, gy, 0, (gx + 30, gy, L.GEODE_H), L.GEODE_H + 140, 'pad_geode')
    jumppad(gx + 70, gy - 60, L.GEODE_H, (-1250, -1150, 0), L.GEODE_H + 90, 'pad_geode_off', glow=False)
    item('ammo_balloony', gx - 40, gy + 60, L.GEODE_H)
    for (k, x, y) in ((0, -2180, -1180), (1, -1180, -1900), (2, -2180, -1900), (3, -1180, -1180)):
        furn(f'cluster_{k}', x, y, 0, 30 * k, [((-36, -30, 0), (36, 30, 60))])
    furn('case_crystal', -2200, -1560, 0, 0, [((-40, -60, 0), (40, 60, 200))])
    A(sign_box((-1798, -1008, 300), (-1542, -1004, 364), T('sign_gems'), 512, 128, facing='n'))
    item('ammo_boaster', -2200, -1350, 0); item('ammo_splasher', -1180, -1550, 0); item('item_visionless', -2200, -1750, 0)
    speaker(gx, gy, 200, 'sound/world/machine/transformer.ogg', volume=0.25)
    for (x, y, a) in ((-1300, -1300, 225), (-2150, -1250, 300)):
        spawn(x, y, 0, a)


# =================================================================================================== ocean: giant squid tank
def ocean():
    cx, cy, hx, hy, H = L.TANK
    custom('squid_tank', cx, cy, 0)
    A(box((cx - hx, cy - hy, 0), (cx + hx, cy + hy, H), WCLIP))
    jumppad(cx - hx - 260, cy, 0, (cx, cy, H), 596, 'pad_tank')
    weapon('balloony', cx + 60, cy, H)
    custom('shark', 1450, -1250, L.CEIL, 30); custom('shark_s', 2100, -1150, L.CEIL, 160); custom('shark_s', 1350, -1850, L.CEIL, 290)
    furn('coral_case', 1200, -1880, 0, 90, [((-50, -100, 0), (50, 100, 170))])
    furn('coral_case', 2200, -1180, 0, 0, [((-50, -100, 0), (50, 100, 170))])
    A(sign_box((1542, -1008, 300), (1798, -1004, 364), T('sign_ocean'), 512, 128, facing='n'))
    item('ammo_balloony', 1250, -1300, 0); item('ammo_splasher', 2200, -1950, 0); item('ammo_betty', 1600, -1950, 0)
    speaker(cx, cy, 560, 'sound/world/machine/fishtank.ogg', volume=0.5)
    for (x, y, a) in ((1300, -1550, 0), (2150, -1450, 180)):
        spawn(x, y, 0, a)


# =================================================================================================== foyer + portico + forecourt
def foyer():
    custom('ticket_desk', -500, -1500, 0)
    for kk in range(7):
        a0 = 200 + 20 * kk
        A(ring_seg(-500, -1300, a0, a0 + 20, 262, 298, 0, 118, WCLIP))
    custom('stanchions', -500, -1700, 0)
    for (x, y, a) in ((970, -1250, 180), (740, -1080, 270)):
        furn('gift_shelf', x, y, 0, a, [((-30, -120, 0), (30, 120, 200))])
    mdl_c('gummybears/greenbear.md3', 760, -1400, 0, 0.8, 200); mdl_c('gummybears/redbear.md3', 640, -1300, 0, 0.8, 160)
    mdl_c('pad_actionfigures/fig_lilly.md3', 980, -1430, 0, 0.6, 180)
    A(sign_box((620, -1044, 400), (876, -1040, 464), T('sign_gift'), 512, 128, facing='s'))
    weapon('bubbleg', 860, -1250, 0)
    A(sign_box((-1008, -1720, 300), (-1004, -1420, 375), T('sign_gems'), 512, 128, facing='e'))
    A(sign_box((1004, -1720, 300), (1008, -1420, 375), T('sign_ocean'), 512, 128, facing='w'))
    for x in (-760, 760):
        custom('column', x, -1800, 0)
        A(cyl(x, -1800, 38, 0, L.CEIL, WCLIP, 12))
    furn('bench', 520, -1520, 0, 0, [((-130, -36, 0), (130, 36, 40))])
    A(cyl(100, -1560, 170, 0, 64, {'top': T('marble'), 'side': T('marble_dark'), 'bot': CAULK}, 24))
    mdl_box('pad_statues/statue_super.md3', 100, -1560, 64, 1.3, 90)
    custom('exit_sign', 0, -2048, 430, 90)
    for (x, a) in ((-1008, 0), (1008, 180)):
        custom('cctv', x, -1960, 560, a)
    item('ammo_bubbleg', -150, -1850, 0); item('ammo_splasher', -800, -1150, 0); item('ammo_nipper', 300, -1900, 0)
    station(-850, -1900, 0, 0)
    speaker(-500, -1350, 200, 'sound/world/machine/clock_ticking.ogg', volume=0.6)
    for (x, y, a) in ((-300, -1900, 90), (500, -1700, 135)):
        spawn(x, y, 0, a)


def portico():
    px0, py0, px1, py1 = L.PORTICO
    R_ = L.ROOF; zb = 544
    A(box((px0, py0, zb), (px1, -2112, R_), {'top': T('roof_gravel'), 'bot': T('coffer'), 'side': T('limestone')}))
    par = {'top': T('marble'), 'side': T('limestone'), 'bot': CAULK}
    A(box((px0, py0, R_), (px0 + 32, -2112, R_ + 32), par)); A(box((px1 - 32, py0, R_), (px1, -2112, R_ + 32), par))
    A(box((px0 + 32, py0, R_), (px1 - 32, py0 + 32, R_ + 32), par))
    A(sign_box((-416, py0 - 4, 552), (416, py0, 648), T('sign_museum'), 1024, 128, facing='s'))
    for x in (-720, -432, -144, 144, 432, 720):
        custom('column', x, -2470, 0, mul=zb / 640)
        A(cyl(x, -2470, 34, 0, zb, WCLIP, 12))
    for x in (-1150, 1150):
        furn('lion', x, -2380, 0, 0, [((-70, -140, 0), (70, 140, 230))])
        furn('bench', x, -2780, 0, 0, [((-130, -36, 0), (130, 36, 40))])
    jumppad(0, -2820, 0, (0, -2300, R_), R_ + 150, 'pad_portico')
    item('holdable_floater', 500, -2300, R_); item('item_jumper', -1300, -2600, 0); item('ammo_nipper', 1300, -2600, 0)
    item('ammo_imperius', -500, -2300, R_)
    route('front_door', (0, -1300, 0), (0, -2700, 0))
    for (x, y, a) in ((-900, -2800, 60), (900, -2800, 120)):
        spawn(x, y, 0, a)
    speaker(0, -2900, 300, 'sound/world/ambient/city_traffic.ogg', volume=0.5)
    timer_sound(1300, -2900, 200, 'sound/world/ambient/police_pass.ogg', 'police', 70, 30, volume=0.5)


# =================================================================================================== stair towers (security office NW, staff room NE)
def towers():
    for s in (-1, 1):
        A_, land, B_, hole = L.tower_flights(s)
        tt = {'top': T('stair_tread'), 'side': T('wainscot'), 'bot': CAULK}
        for (x0, y0, x1, y1, z) in A_ + B_:
            A(box((x0, y0, 0), (x1, y1, z), tt))
        x0, y0, x1, y1, z = land
        A(box((x0, y0, 0), (x1, y1, z), tt))
        nm = 'nw' if s < 0 else 'ne'
        top = B_[-1]
        xr = top[0] - 60 if s < 0 else top[2] + 60
        route(f'tower_{nm}', (s * 1700, 1450, 0), (xr, (top[1] + top[3]) / 2, L.ROOF))
        item('ammo_imperius' if s < 0 else 'ammo_balloony', (x0 + x1) / 2, (y0 + y1) / 2, 320)
        custom('exit_sign', s * 1040, 1320, 400, 90 - 90 * s)
    # NW: the night guard's security office
    furn('security_desk', -1650, 1330, 0, 0, [((-40, -150, 0), (40, 150, 136))])
    furn('lockers', -2268, 1300, 0, 0, [((-30, -120, 0), (30, 120, 190))])
    mdl_c('pad_lamps/gooseneck.md3', -1650, 1220, 76, 0.4, 180)
    mdl_c('pad_cups/pad_cup01.md3', -1670, 1440, 76, 0.4, 0)
    custom('cctv', -2304, 1100, 560, 0)
    item('ammo_boaster', -2200, 1550, 0); item('item_armor_shard', -1400, 1150, 0)
    speaker(-1700, 1330, 120, 'sound/world/human/snoring.ogg', volume=0.5)
    timer_sound(-1800, 1600, 100, 'sound/world/human/footsteps_m.ogg', 'guard', 40, 20, volume=0.5)
    spawn(-1300, 1400, 0, 180)
    # NE: staff room / storage
    furn('lockers', 2268, 1300, 0, 180, [((-30, -120, 0), (30, 120, 190))])
    mdl_box('pad_ddmix/anteroom/metal_suitcase.md3', 1700, 1300, 0, 1.0, 20)
    mdl_box('pad_ddmix/anteroom/medical_case.md3', 1850, 1150, 0, 1.0, 70)
    furn('case_egg', 1400, 1550, 0, 90, [((-40, -60, 0), (40, 60, 200))])
    A(sign_box((1120, 1004, 300), (1360, 1008, 360), T('sign_staff'), 512, 128, facing='s'))
    item('holdable_boomies', 2150, 1150, 0); item('ammo_bubbleg', 1300, 1250, 0)
    speaker(1800, 1300, 200, 'sound/world/machine/coffee_maker.ogg', volume=0.3)
    spawn(1300, 1400, 0, 0)


# =================================================================================================== roof terrace
def roof():
    R_ = L.ROOF
    for (x, y, a) in ((-1650, -400, 0), (1650, -1500, 90), (-500, -1550, 0)):
        furn('hvac', x, y, R_, a, [((-70, -110, 0), (70, 110, 150))])
    custom('water_tank', -1700, 1250, R_)
    A(cyl(-1700, 1250, 96, R_ + 120, R_ + 330, WCLIP, 16))
    for (dx_, dy_) in ((-60, -60), (-60, 60), (60, -60), (60, 60)):
        A(box((-1700 + dx_ - 6, 1250 + dy_ - 6, R_), (-1700 + dx_ + 6, 1250 + dy_ + 6, R_ + 120), WCLIP))
    custom('dish', 2100, -600, R_)
    A(cyl(2100, -600, 10, R_, R_ + 120, WCLIP, 8))
    mdl_box('pad_ddmix/cabin/telescope.md3', 1250, 1500, R_, 0.6, 210)
    for (x, y) in ((-1650, -1500), (2000, 700), (600, -1600), (-700, 1500), (700, 1600)):
        furn('hvac', x, y, R_, 90 if x > 0 else 0, [((-70, -110, 0), (70, 110, 150))], mul=0.7)
    # the glass roof over the great hall: a pad up from the Egypt roof
    jumppad(-1400, 300, R_, (-760, 300, L.HALL_TOP + 16), L.HALL_TOP + 150, 'pad_skylight')
    item('ammo_imperius', -500, 300, L.HALL_TOP + 16); item('item_armor_shard', 500, -300, L.HALL_TOP + 16)
    item('ammo_pumper', 0, 0, L.HALL_TOP + 16)
    item('ammo_bubbleg', -1300, -1300, R_); item('ammo_balloony', 1300, 1250, R_); item('ammo_splasher', -1900, 600, R_)
    for (x, y, a) in ((-1900, -1000, 90), (1900, -1000, 90), (0, -1700, 90), (-1300, 1700, 0)):
        spawn(x, y, R_, a)
    speaker(0, -1700, R_ + 200, 'sound/world/ambient/wind_night.ogg', volume=0.4)
    timer_sound(-2000, 1800, R_ + 300, 'sound/world/animal/bird_owl1.ogg', 'owl1', 35, 15, volume=0.6)
    timer_sound(2000, -1800, R_ + 300, 'sound/world/animal/bird_owl2.ogg', 'owl2', 45, 20, volume=0.5)


# =================================================================================================== secret: the pharaoh's treasury
def treasury():
    F = L.TREASURY
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('tomb_stone'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('gold_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('sandstone'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    custom('treasure', -450, 380, z0, 20); custom('treasure', 450, 380, z0, 160); custom('treasure_b', 0, 480, z0, 270)
    for (x, y) in ((-450, 380), (450, 380)):
        A(cyl(x, y, 100, z0, z0 + 40, WCLIP, 12))
    A(cyl(0, 480, 70, z0, z0 + 30, WCLIP, 12))
    furn('death_mask', 0, 250, z0, 270, [((-40, -40, 0), (40, 40, 110))])
    for x in (-600, 600):
        furn('pharaoh', x, -150, z0, 0 if x < 0 else 180, [((-70, -60, 0), (70, 60, 300))], mul=0.8)
    for x in (-300, 300):
        furn('obelisk', x, -500, z0, 0, [((-60, -60, 0), (60, 60, 40)), ((-36, -36, 40), (36, 36, 400))], mul=0.75)
    item('item_padpower', 0, 120, z0); item('item_revival', -300, 200, z0); item('holdable_killerducks', 300, 200, z0)
    item('ammo_imperius', -600, 200, z0); item('ammo_balloony', 600, 200, z0)
    A(sign_box((-300, y1 - 4, z0 + 320), (300, y1, z0 + 380), T('sign_treasury'), 1024, 128, facing='s'))
    M.ent('misc_teleporter_dest', (0, -300, z0 + 24), targetname='treasury_in', angle=90)
    mdl_c('pad_teleporter/padtp_orange.md3', 0, -540, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -576, z0 + 2), (36, -504, z0 + 90), TRIG)], target='treasury_out')
    M.ent('misc_teleporter_dest', (-1250, -600, 24), targetname='treasury_out', angle=90)
    for (x, y, c) in ((0, 0, '1 0.85 0.5'), (-500, 400, '1 0.8 0.4'), (500, 400, '1 0.8 0.4'), (0, -450, '1 0.9 0.7'), (-600, -400, '1 0.8 0.5'), (600, -400, '1 0.8 0.5')):
        light(x, y, z0 + 300, 260, c)
    speaker(0, 0, z0 + 200, 'sound/world/ambient/water_drippling.ogg', volume=0.4)


# =================================================================================================== light + sound
def lights_and_sound():
    # warm gallery lamps, cool moon fill in the great hall, coloured rooms (night: pools of light, dark corners)
    for (x, y) in ((-600, -600), (600, -600), (-600, 600), (600, 600), (0, 0)):
        light(x, y, 300, 240, '1 0.85 0.65')
    for (x, y) in ((-900, 0), (900, 0), (0, 900), (0, -900)):
        light(x, y, 560, 220, '0.8 0.85 1')
    for (x, y) in ((-900, -600), (900, -600), (-900, 600), (900, 600), (-500, -900), (500, -900), (-500, 900), (500, 900)):
        light(x, y, 250, 170, '1 0.85 0.65')
    light(0, 0, 1150, 400, '0.6 0.7 1')
    for (x, y) in ((-1300, -700), (-1300, 700), (-2100, -700), (-2100, 700), (-1700, -800), (-1700, 800), (-2150, 0), (-1200, 0)):
        light(x, y, 420, 300, '1 0.75 0.45')
    for (x, y) in ((-1450, -450), (-1450, 450), (-1900, -450), (-1900, 450)):
        light(x, y, 260, 200, '1 0.7 0.4')
    light(-1664, 0, 450, 260, '1 0.8 0.5')
    for (x, y) in ((1300, -800), (1300, 800), (2100, -800), (2100, 800), (1180, 0), (2200, 0)):
        light(x, y, 420, 200, '0.5 0.55 1')
    light(1664, 0, 560, 200, '0.6 0.6 1')
    for (x, y) in ((-600, 1300), (600, 1300), (-600, 1800), (600, 1800), (0, 1250), (0, 1900)):
        light(x, y, 480, 290, '0.75 0.85 1')
    for (x, y) in ((-2050, -1300), (-1300, -1850), (-2050, -1850), (-1300, -1250), (-1664, -1150), (-1664, -1950)):
        light(x, y, 420, 250, '0.75 0.45 1')
    for (x, y) in ((1300, -1300), (2100, -1300), (1300, -1850), (2100, -1850)):
        light(x, y, 450, 220, '0.35 0.7 1')
    light(1820, -1560, 560, 160, '0.3 0.8 1')
    for (x, y) in ((-600, -1300), (600, -1300), (-600, -1850), (600, -1850), (0, -1450)):
        light(x, y, 500, 230, '1 0.85 0.6')
    for (x, y) in ((-1700, 1300), (-1900, 1600), (1700, 1300), (1900, 1600), (-1400, 1600), (1400, 1600), (-2150, 1200), (2150, 1200),
                   (-1800, 1950, ), (1800, 1950)):
        light(x, y, 450, 240, '1 0.9 0.7')
    for (x, y) in ((-1900, 1816), (1900, 1816)):
        light(x, y, 700, 200, '1 0.9 0.7')
    for (x, y) in ((-400, -2500), (400, -2500)):
        light(x, y, 480, 220, '1 0.85 0.6')
    for (x, y) in ((-1100, -2700), (1100, -2700), (0, -2900)):
        light(x, y, 300, 220, '1 0.8 0.55')
    speaker(0, 0, 900, 'sound/world/machine/ventilation.ogg', volume=0.3)


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'jumppad_ns', 'origin', 'water', 'botclip')


def main():
    mulib.STATE['out'] = OUT
    TX.make_textures()
    import mu_models
    mu_models.make()
    hull_and_ground(); shell(); great_hall(); balconies(); egypt(); planetarium(); ice_age(); gems(); ocean(); foyer(); portico(); towers()
    roof(); treasury()
    lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (0, -2900, 420), angles='5 90 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padmuseum/build_museum.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
