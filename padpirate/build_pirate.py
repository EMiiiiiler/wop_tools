#!/usr/bin/env python3
"""Skull Rock Bay - World of Padman FFA map generator (map 'wop_padpirate').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_pirate.py

Writes <OUT>/maps/wop_padpirate.map, textures/padpirate/*, env/padpirate/* (sky), models/padpirate/*,
scripts/padpirate.shader and scripts/wop_padpirate.arena.

A pirate water park on a tropical island on a sunny afternoon, human scale (~32u per metre). x east, y north, plaza
z 0, water z -16. The sea surrounds the park on three sides; a jungle cliff closes the north.

  Galleon Bay     the lagoon with 'The Salty Padman' anchored in the middle, stone jetties from the north and south
                  shores up gangway stairs to her entry ports. Walk the decks, climb to the quarterdeck and the
                  forecastle, go into the captain's cabin and the crew quarters, down the hatch into the hold
                  (Bubble G). A pad on the quarterdeck throws you into the crow's nest (Imperius).
  Skull Rock      a hollow skull wearing a tricorn: walk in through the teeth, climb the stair round the inside to the
                  balcony behind the eye sockets, ride the pad up the shaft onto the crown of the hat (Betty). Two
                  slides leave the brim: the Cannonball Run tube into Treasure Cove and the Plank Plunge flume into
                  the Shark Pool.
  Fort San Padro  walls, gate, courtyard, stairs to the ramparts, a powder magazine (BamBam), a pad onto the
                  watchtower (Pumper) and a mortar on the east wall that fires you onto Skull Rock's hat.
  Shark Pool      a deep dive pool with sharks circling; a walk-the-plank dive tower (Balloony on top), the Splasher
                  on the bottom.
  Treasure Cove   a beach pool with a deep hole (Floater), two beach shacks, rowboats, chests and palms.
  Tortuga Quay    the Rusty Anchor tavern (Boaster, roof terrace up the outside stair), Ye Olde Gift Shoppe (pad
                  to the roof), market stalls on the boardwalk.
  SECRET          the giant tipped rum barrel at the back of the galleon's hold -> Captain Padbeard's Hoard.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import pp_textures as TX
import pplib
import pp_shapes as SH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padpirate'
T = lambda n: 'padpirate/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns'); SLICK = T('slide_clip')

for k, v in {'cobbles': (1.0, 1.0), 'sand': (0.5, 0.5), 'wet_sand': (0.5, 0.5), 'grass': (1.0, 1.0), 'bank': (1.0, 1.0), 'rock': (1.0, 1.0),
             'planks': (0.5, 0.5), 'deck': (0.5, 0.5), 'boardwalk': (0.5, 0.5), 'plaster': (0.5, 0.5), 'timber_wall': (0.5, 0.5),
             'pool_tile': (0.5, 0.5), 'pool_band': (0.5, 0.5), 'coping': (0.5, 0.5), 'quay': (0.5, 0.5), 'fort_stone': (0.5, 0.5),
             'fort_floor': (1.0, 1.0), 'gold_floor': (0.5, 0.5), 'water': (1.0, 1.0), 'water_deep': (1.0, 1.0), 'sea': (2.0, 2.0), 'sky': (1, 1),
             'shop_wall': (0.5, 0.5), 'bamboo_w': (0.5, 0.5), 'thatch_t': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '6', '_color': '1 0.95 0.85', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
KEEP_OUT = []
NOGO = []
SX, SY = L.SHIP


# =================================================================================================== helpers
def mdl(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    p = path if path.startswith('models/') else 'models/mapobjects/' + path
    b = BOUNDS.get(p)
    zmin = b['min'][2] if b else 0
    return M.model(p, (round(x, 1), round(y, 1), round(zsurf - zmin * scale, 2)), scale=scale, angle=angle, **kw)


def mdl_c(path, x, y, zsurf, scale=1.0, angle=0, **kw):
    b = BOUNDS['models/mapobjects/' + path]
    cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
    a = math.radians(angle)
    ox = cx * math.cos(a) - cy * math.sin(a); oy = cx * math.sin(a) + cy * math.cos(a)
    return mdl(path, x - ox, y - oy, zsurf, scale, angle, **kw)


def mdl_box(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.15, top_cut=2, **kw):
    e = mdl_c(path, x, y, zsurf, scale, angle, **kw)
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
    path, sc, zo = pplib.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, angles=angles, **extra)


def lbox(x, y, z, ang, mn, mx, tex=WCLIP):
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
    e = custom(name, x, y, z, ang, lit=lit, mul=mul, **kw)
    for (mn, mx) in boxes:
        lbox(x, y, z, ang, [v * mul for v in mn], [v * mul for v in mx])
    return e


def light(x, y, z, val, color='1 0.9 0.75', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise if noise.startswith('sound/') else f'sound/world/{noise}.ogg'}
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
    KEEP_OUT.append((x, y, 48))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((x, y, floor))
    KEEP_OUT.append((x, y, 48))


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)
    KEEP_OUT.append((x, y, 72))


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def jumppad(x, y, z, land, apex, name, glow=True):
    """compass-rose pad (r 34) + trigger_push + target_position (the apex, t_up/(t_up+t_down) of the way to `land`)"""
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
    if glow: light(x, y, z + 48, 90, '1 0.85 0.5')
    KEEP_OUT.append((x, y, 80))


def route(name, a, b):
    ROUTES.append((name, a, b))


def face_pts(b, f, V=None):
    V = b.verts() if V is None else V
    on = V[np.abs(V @ np.array(f.n) - f.d) < 0.5]
    return on if len(on) else V


def texby(b, fn):
    V = b.verts()
    if len(V) < 4: return None
    for f in b.faces:
        on = face_pts(b, f, V); c = on.mean(0)
        smp = [c] + [c + (p - c) * 0.85 for p in on]
        f.tex = fn(smp, np.array(f.n)); f.sc = wopmap.default_scale(f.tex)
    return b


def clipped(brushes, tex=WCLIP):
    for b in brushes:
        for f in b.faces:
            f.tex = tex; f.sc = (0.5, 0.5)
        A(b)


def in_rect(x, y, r, m=0):
    return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m


def free(x, y, r):
    if abs(x) > L.HX - r - 8 or abs(y) > L.HY - r - 8: return False
    if any(in_rect(x, y, q, r) for q in NOGO): return False
    return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT)


def near_free(x, y, r, search=320):
    if free(x, y, r): return (x, y)
    for d in range(32, search + 1, 32):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if free(px, py, r): return (round(px), round(py))
    return None


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'origin', 'water', 'botclip', 'slide_clip')


def fix_items():
    sol = []
    for b in M.world + [bb for e in M.ents if e['classname'] not in ('trigger_push', 'trigger_multiple', 'trigger_teleport', 'func_rotating') for bb in e['_brushes']]:
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
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padpirate/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_pirate.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== sky hull, ground, sea, cliff
LAG_TILE = (L.LAG[0] - 32, L.LAG[1] - 32, L.LAG[2] + 32, L.LAG[3] + 32)
COVE_TILE = (L.COVE[0] - 32, L.COVE[1] - 32, L.COVE[2] + 32, L.COVE[3] + 32)
SHARK_TILE = (L.SHARK[0] - 32, L.SHARK[1] - 32, L.SHARK[2] + 32, L.SHARK[3] + 32)
TILES = [LAG_TILE, COVE_TILE, SHARK_TILE]
CY = SH.fort_courtyard()
ZONES = [((-2304, -2048, -1344, 448), 'sand'), ((-1344, -2048, 1344, -1792), 'sand'), ((-560, 512, 560, 1664), 'sand'),
         ((1344, -2048, 1600, 640), 'boardwalk'), ((-2304, 1536, -1344, 2048), 'grass'), ((-1344, 1664, 1280, 2048), 'grass'),
         ((1920, 1856, 2304, 2048), 'grass'), (CY, 'fort_floor'),
         ((-2304, -2048, 2304, -1984), 'coping'), ((-2304, -1984, -2240, 2048), 'coping'), ((2240, -1984, 2304, 2048), 'coping'),
         (L.TAV, 'planks'), (L.SHOP, 'planks')] + [(r, 'planks') for r in L.SHACKS]


def sky_hull():
    H = L.SKY
    x0, x1, y0, y1, z0, z1 = H['x0'], H['x1'], H['y0'], H['y1'], H['z0'], H['z1']
    W = 16; sk = T('sky')
    side = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), dict(side, top=sk), detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), dict(side, bot=sk), detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), dict(side, s=sk), detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), dict(side, n=sk), detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), dict(side, w=sk), detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), dict(side, e=sk), detail=False))


def ground():
    X1, Y1 = L.HX, L.HY
    cuts = list(TILES) + [z[0] for z in ZONES]
    side = {'top': T('cobbles'), 'side': T('quay'), 'bot': CAULK}
    def tx_side(r):
        d = dict(side)
        # sides on the outer edge face the sea (quay wall); the rest are hidden
        for k, cond in (('s', abs(r[1] + Y1) < 0.5), ('e', abs(r[2] - X1) < 0.5), ('w', abs(r[0] + X1) < 0.5), ('n', False)):
            d[k] = T('quay') if cond else CAULK
        return d
    for r in sub_rects((-X1, -Y1, X1, Y1), cuts):
        A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), dict(tx_side(r), top=T('cobbles'))))
    for i, (zr, tex) in enumerate(ZONES):
        later = [z[0] for z in ZONES[i + 1:]]
        for r in sub_rects(zr, later + list(TILES)):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), dict(tx_side(r), top=T(tex))))


def sea_and_cliff():
    """the open sea round the south, east and west quay walls (decor, unreachable), the jungle cliff in the north, player
    clip all round the playable edge; distant palms on the cliff shelf"""
    H = L.SKY; X1, Y1 = L.HX, L.HY; bw, bh = L.BANK_W, L.BANK_H
    sea = {'top': T('sea'), 'side': CAULK, 'bot': CAULK}
    for r in sub_rects((H['x0'], H['y0'], H['x1'], Y1), [(-X1, -Y1, X1, Y1)]):
        A(box((r[0], r[1], H['z0']), (r[2], r[3], L.SEA_Z), sea))
    bt = {'top': T('bank'), 'side': T('bank'), 'bot': CAULK}
    A(hull([(x, Y1, z) for x in (H['x0'], H['x1']) for z in (H['z0'], 0)] + [(x, Y1 + bw, z) for x in (H['x0'], H['x1']) for z in (H['z0'], bh)],
           bt, round_pts=False))
    A(box((H['x0'], Y1 + bw, H['z0']), (H['x1'], H['y1'], bh), {'top': T('bank'), 'side': CAULK, 'bot': CAULK}))
    for s in (-1, 1):
        A(box((-X1, s * Y1 - (16 if s > 0 else 0), 0), (X1, s * Y1 + (0 if s > 0 else 16), H['z1']), CLIP))
        A(box((s * X1 - (16 if s > 0 else 0), -Y1 + 16, 0), (s * X1 + (0 if s > 0 else 16), Y1 - 16, H['z1']), CLIP))
    rng = np.random.default_rng(42)
    for i in range(22):
        t = (i + rng.uniform(0.2, 0.8)) / 22
        x = H['x0'] + 260 + (H['x1'] - H['x0'] - 520) * t
        y = Y1 + bw + rng.uniform(60, 200)
        k = i % 3
        if k == 0: mdl_c('pad_ddmix/trashcan/tree_summer.md3', x, y, bh, rng.uniform(0.8, 1.1), rng.uniform(0, 360), spawnflags=0)
        elif k == 1: custom(['palm_a', 'palm_b', 'palm_c'][i % 3], x, y, bh, rng.uniform(0, 360), lit=False)
        else: mdl_c('pad_ddmix/trashcan/bush.md3', x, y, bh, 0.9, rng.uniform(0, 360))
    for i in range(10):
        x = -X1 + 200 + i * (2 * X1 - 400) / 9
        mdl_c('pad_ddmix/plants/fern.md3', x + rng.uniform(-60, 60), Y1 + bw + 40, bh, rng.uniform(0.35, 0.5), rng.uniform(0, 360))
    # palm islets out in the sea (decor beyond the clip)
    for (x, y, r) in ((-2650, -1500, 120), (2700, -400, 150), (2600, -2400, 110), (-2700, 600, 100), (900, -2380, 110), (-1300, -2480, 100)):
        A(cyl(x, y, r, L.SEA_Z, L.SEA_Z + 28, {'top': T('sand'), 'side': T('sand'), 'bot': CAULK}, 12))
        custom('palm_b' if x > 0 else 'palm_a', x, y, L.SEA_Z + 28, int(x) % 360, lit=False)


# =================================================================================================== pool helpers
def pool_tex(smp, n):
    c = smp[0]
    if n[2] > 0.99 and abs(max(p[2] for p in smp) - 0) < 0.5: return T('coping')
    if n[2] < -0.7: return CAULK
    if n[2] > 0.3: return T('pool_tile')
    return T('pool_band')


def water_faces(b, deep=False):
    wt = T('water_deep' if deep else 'water')
    for f in b.faces:
        top = f.n[2] > 0.99 and abs(max(p[2] for p in face_pts(b, f)) - L.WATER) < 0.5
        f.tex = wt if top else wt + '_nodraw'
        f.sc = (1, 1)
    return b


def edge_faces_caulk(b, tile):
    if b is None: return []
    V = b.verts()
    for f in b.faces:
        if abs(f.n[2]) > 0.01: continue
        on = face_pts(b, f, V)
        if abs(f.n[0]) > 0.99 and (np.all(np.abs(on[:, 0] - tile[0]) < 0.5) or np.all(np.abs(on[:, 0] - tile[2]) < 0.5)): f.tex = CAULK
        if abs(f.n[1]) > 0.99 and (np.all(np.abs(on[:, 1] - tile[1]) < 0.5) or np.all(np.abs(on[:, 1] - tile[3]) < 0.5)): f.tex = CAULK
    return b


# =================================================================================================== Galleon Bay + the galleon
WATER_SOLIDS = []


def lagoon():
    cut = L.LAG_CUT; sb = L.SHALLOW_BAND
    oct0 = L.octagon(L.LAG, cut); oct1 = L.octagon(L.LAG, cut, sb); oct2 = L.octagon(L.LAG, cut, sb + L.SLOPE_W)
    c1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, 64)], CAULK, round_pts=False)
    c2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, 64)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    hw = L.JETTY_HW
    keep = [box((SX - hw, SY + L.CW, -600), (SX + hw, L.LAG[3] + 64, 80), CAULK),
            box((SX - hw, L.LAG[1] - 64, -600), (SX + hw, SY - L.CW, 80), CAULK)] + \
           [cyl(x, y, r, -600, 80, CAULK, 16) for (x, y, r) in L.ISLETS]
    cutters = []
    for c in (c1, c2):
        cutters += carve(c, keep)
    tile = box((LAG_TILE[0], LAG_TILE[1], L.SLAB_BOT), (LAG_TILE[2], LAG_TILE[3], 0), CAULK)

    def tx(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(c[2]) < 0.5:
            if any(math.hypot(c[0] - x, c[1] - y) < r + 1 for (x, y, r) in L.ISLETS): return T('sand')
            if abs(c[0] - SX) < hw + 1 and L.LAG[1] - 40 < c[1] < L.LAG[3] + 40: return T('boardwalk')
            return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('pool_tile')
        if abs(abs(c[0] - SX) - hw) < 2 or abs(abs(c[1] - SY) - L.CW) < 2: return T('quay')
        if any(math.hypot(c[0] - x, c[1] - y) < r + 2 for (x, y, r) in L.ISLETS): return T('rock')
        return T('pool_band')
    for b in carve(tile, cutters):
        A(edge_faces_caulk(texby(b, tx), LAG_TILE))
    solids = []
    for (x0, y0, x1, y1, d) in L.LAG_STEPS:
        n = 3
        for j in range(n):
            if d == 's': r = (x0, y0 + (y1 - y0) * j / n, x1, y0 + (y1 - y0) * (j + 1) / n)
            elif d == 'w': r = (x0 + (x1 - x0) * j / n, y0, x0 + (x1 - x0) * (j + 1) / n, y1)
            else: r = (x1 - (x1 - x0) * (j + 1) / n, y0, x1 - (x1 - x0) * j / n, y1)
            zt = L.SHALLOW + 16 * (n - j)
            b = box((round(r[0]), round(r[1]), L.SHALLOW), (round(r[2]), round(r[3]), zt), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
            A(b); solids.append(b)
    bx0, by0, bx1, by1 = L.BEACH
    beach = hull([(x, by1, L.SHALLOW) for x in (bx0, bx1)] + [(x, by1, 0) for x in (bx0, bx1)] + [(x, by0, L.SHALLOW) for x in (bx0, bx1)],
                 {'top': T('wet_sand'), 'side': T('pool_band'), 'bot': CAULK}, round_pts=False)
    A(beach); solids.append(beach)
    W_ = L.WATER
    w1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, W_)], CAULK, round_pts=False)
    w2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, W_)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    oct1_box = hull([(x, y, z) for (x, y) in oct1 for z in (L.DEEP - 10, W_ + 10)], CAULK, round_pts=False)
    all_solids = solids + WATER_SOLIDS
    def cut_all(w):
        out_ = [w]
        for cset in (keep, all_solids):
            out_ = [pp for ww in out_ for pp in carve(ww, cset)]
        return out_
    w1p = [pp for w in cut_all(w1) for pp in carve(w, [oct1_box])]
    w2p = cut_all(w2)
    for pc in w1p + w2p:
        A(water_faces(pc))
    NOGO.append(tuple(L.LAG))
    # islets: a boulder and a palm on each (cover in the open water)
    for k, (x, y, r) in enumerate(L.ISLETS):
        custom('boulder_b' if r > 90 else 'boulder_a', x + 14, y - 10, 0, 40 + 90 * k)
        A(cyl(x + 14, y - 10, (64 if r > 90 else 42), 0, (75 if r > 90 else 48), WCLIP, 10))
        po = 50 if r > 90 else 40
        custom(['palm_a', 'palm_b', 'palm_c'][k % 3], x - po, y + po, 0, 120 * k, lit=False)
        A(cyl(x - po, y + po, 12, 0, 220, WCLIP, 8))
    # the lagoon's contents
    item('ammo_splasher', -620, -1300, L.DEEP); item('ammo_pumper', 820, -1700, L.SHALLOW); item('item_armor_shard', -1150, -300, L.SHALLOW)
    for (x, y) in ((-640, -1200), (640, -800), (-700, -700), (700, -1350)):
        light(x, y, L.DEEP + 60, 160, '0.5 0.9 1')
    speaker(-700, -1000, 0, 'ambient/water_rippling', volume=0.5); speaker(700, -1000, 0, 'ambient/water_rippling', volume=0.5)


def wreck_masts():
    for (x, y, a) in ((-560, -1430, 30), (640, -600, 200)):
        custom('wreck_mast', x, y, L.DEEP, a)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        def P(dx, dy): return (x + dx * ca - dy * sa, y + dx * sa + dy * ca)
        b = hull([(P(0, 0)[0] + 10 * math.cos(t), P(0, 0)[1] + 10 * math.sin(t), L.DEEP) for t in np.linspace(0, 6.28, 8, endpoint=False)] +
                 [(P(24, 8)[0] + 6 * math.cos(t), P(24, 8)[1] + 6 * math.sin(t), L.DEEP + 410) for t in np.linspace(0, 6.28, 8, endpoint=False)], WCLIP, round_pts=False)
        A(b); WATER_SOLIDS.append(b)


def ship():
    hull_b = SH.ship_hull()
    clipped(hull_b)
    for b in hull_b:
        if b.bounds()[0][2] < L.WATER: WATER_SOLIDS.append(b)
    clipped(SH.ship_rails()); clipped(SH.ship_stairs()); clipped(SH.ship_nest())
    custom('ship_aft', SX - 340, SY, 0, _lightmapscale=1.0)
    custom('ship_fore', SX + 320, SY, 0, _lightmapscale=1.0)
    for key, nm in (('main', 'mast_main'), ('fore', 'mast_fore'), ('mizzen', 'mast_mizzen')):
        x0, zd, h, r = L.MASTS[key]
        custom(nm, SX + x0, SY, zd)
        if key == 'main':
            A(cyl(SX + x0, SY, r - 2, zd, L.NEST_Z - 16, WCLIP, 8))
            A(cyl(SX + x0, SY, r * 0.7, L.NEST_Z, zd + h - 40, WCLIP, 8))
        else:
            A(cyl(SX + x0, SY, r - 2, zd, zd + h - 40, WCLIP, 8))
    custom('ship_stays', SX, SY, 0)
    NOGO.append((SX + L.SHIP_STERN - 40, SY - 220, SX + 860, SY + 220))
    # gangway stairs up the jetties to the entry ports
    for s in (-1, 1):
        ye = SY + s * L.CW
        for (j, zt) in enumerate(range(16, L.WAIST_Z + 1, 16)):
            n = L.WAIST_Z // 16
            ya = ye + s * 32 * (n - j); yb = ya - s * 32
            A(box((SX - L.JETTY_HW, min(ya, yb), 0), (SX + L.JETTY_HW, max(ya, yb), zt), {'top': T('boardwalk'), 'side': T('planks'), 'bot': CAULK}))
        route(f'gangway_{"n" if s > 0 else "s"}', (SX, ye + s * 340, 0), (SX - 60, SY + s * 100, L.WAIST_Z))
    # routes on board
    route('qd_stair', (SX - 30, SY + 100, L.WAIST_Z), (SX - 560, SY + 60, L.QD_Z))
    route('fc_stair', (SX + 160, SY - 96, L.WAIST_Z), (SX + 430, SY - 40, L.FC_Z))
    route('hold_stair', (SX + 250, SY, L.WAIST_Z), (SX - 20, SY - 60, 0))
    route('cabin_door', (SX - 300, SY, L.WAIST_Z), (SX - 520, SY, L.WAIST_Z))
    route('crew_door', (SX + 250, SY + 10, L.WAIST_Z), (SX + 440, SY, L.WAIST_Z))
    # deck guns, capstan, mast-foot barrels, cannonballs
    for xc in (-104, 128):
        for s in (-1, 1):
            y = SY + s * (L.CW - L.BULW_T - 42)
            furn('cannon', SX + xc, y, L.WAIST_Z, 90 if s > 0 else 270, [((-46, -22, 0), (40, 22, 40))])
    for (x, y, nm) in ((SX + 34, SY + 38, 'barrel'), (SX + 34, SY - 40, 'barrel'), (SX - 40, SY + 40, 'barrel')):
        furn(nm, x, y, L.WAIST_Z, 0, [((-20, -20, 0), (20, 20, 56))])
    furn('cannonballs', SX - 40, SY - 44, L.WAIST_Z, 0, [((-26, -26, 0), (26, 26, 30))])
    furn('rope_coil', SX + 200, SY + 100, L.WAIST_Z, 0)
    # quarterdeck: wheel + binnacle, lanterns; the pad to the crow's nest
    furn('ship_wheel', SX - 550, SY, L.QD_Z, 0, [((-14, -14, 0), (10, 14, 46)), ((-72, -14, 0), (-48, 14, 50))])
    pxn, pyn = SX + L.PAD_NEST[0], SY + L.PAD_NEST[1]
    jumppad(pxn, pyn, L.QD_Z, (SX - 72, SY, L.NEST_Z), 760, 'pad_nest')
    weapon('imperius', SX - 10, SY - 75, L.NEST_Z, 'purple')
    jumppad(SX + 72, SY - 20, L.NEST_Z, (300, -1950, 0), 760, 'pad_nest_fling')
    jumppad(SX, -560, 0, (SX, SY + 66, L.NEST_Z), 800, 'pad_nest_jetty')         # second way up, from the north jetty
    trigger_sound((SX - 104, SY - 36, L.NEST_Z + 2), (SX - 34, SY + 36, L.NEST_Z + 70), 'sound/world/human/applause.ogg', 'nest_cheer', 15, volume=0.6)
    trigger_sound((SX - 30, SY + 40, L.NEST_Z + 2), (SX + 30, SY + 104, L.NEST_Z + 70), 'sound/world/human/applause.ogg', 'nest_cheer2', 15, volume=0.6)
    item('ammo_betty', SX - 600, SY - 70, L.QD_Z); item('item_armor_shard', SX - 470, SY + 80, L.QD_Z)
    # forecastle
    furn('chest_open', SX + 410, SY + 30, L.FC_Z, 180, [((-30, -18, 0), (30, 18, 24))])
    item('ammo_pumper', SX + 520, SY - 10, L.FC_Z); item('ammo_boaster', SX + 140, SY + 100, L.WAIST_Z)
    # the hold: Bubble G, cannons at the ports, crates, the secret barrel
    weapon('bubbleg', SX - 20, SY, 0, 'green')
    for xc in (-170, -70, 270):
        for s in (-1, 1):
            furn('cannon', SX + xc, SY + s * 70, 0, 90 if s > 0 else 270, [((-46, -22, 0), (40, 22, 40))])
    for s in (-1, 1):
        furn('crate', SX + 180, SY + s * 86, 0, 0, [((-24, -24, 0), (24, 24, 48))])
    furn('barrel_lying', SX + 40, SY - 84, 0, 0, [((-29, -22, 0), (29, 22, 44))])
    item('ammo_bubbleg', SX + 260, SY, 0); item('ammo_splasher', SX - 120, SY + 0, 0)
    for x in (-200, 0, 250):
        light(SX + x, SY, 76, 150, '1 0.8 0.55')
    speaker(SX, SY, 60, 'ambient/floor_creaking', volume=0.35)
    speaker(SX + 60, SY, 300, 'ambient/metal_creaking', volume=0.25)
    timer_sound(SX + 300, SY, 220, 'misc/school_bell', 'ship_bell', 40, 20, volume=0.4)
    # captain's cabin
    c = L.CABIN
    custom('table', SX - 470, SY + 0, L.WAIST_Z, 0); A(cyl(SX - 470, SY, 28, L.WAIST_Z, L.WAIST_Z + 36, WCLIP, 10))
    furn('chest_shut', SX - 590, SY - 70, L.WAIST_Z, 90, [((-30, -18, 0), (30, 18, 40))])
    mdl_c('pad_ddmix/padship/shiplamp.md3', SX - 476, SY - 6, L.WAIST_Z + 36, 0.3, 0)
    mdl_c('pad_ddmix/padship/rumbottle1.md3', SX - 458, SY + 12, L.WAIST_Z + 36, 0.25, 40)
    mdl_c('pad_books/pad_ob_fl_md_pir1.md3', SX - 590, SY - 70, L.WAIST_Z + 40, 0.25, 30)
    mdl_c('pad_ddmix/cabin/telescope.md3', SX - 590, SY + 66, L.WAIST_Z, 0.3, 200)
    lbox(SX - 590, SY + 66, L.WAIST_Z, 0, (-20, -16, 0), (20, 16, 100))
    item('item_visionless', SX - 420, SY + 70, L.WAIST_Z); item('ammo_imperius', SX - 420, SY - 70, L.WAIST_Z)
    light(SX - 500, SY, L.QD_Z - 50, 220, '1 0.8 0.55')
    # crew quarters
    furn('barrel', SX + 470, SY + 40, L.WAIST_Z, 0, [((-20, -20, 0), (20, 20, 56))])
    furn('crate', SX + 470, SY - 40, L.WAIST_Z, 20, [((-24, -24, 0), (24, 24, 48))])
    item('holdable_boomies', SX + 410, SY, L.WAIST_Z)
    light(SX + 440, SY, L.FC_Z - 50, 160, '1 0.8 0.55')
    # the secret: a giant rum barrel lying open-end-forward at the back of the hold
    bx, by = SX + L.SECRET_BARREL[0], SY + L.SECRET_BARREL[1]
    custom('big_barrel', bx, by, 0, 0)
    for s in (-1, 1):
        lbox(bx, by, 0, 0, (-50, (34 if s > 0 else -42), 2), (50, (42 if s > 0 else -34), 82))
    lbox(bx, by, 0, 0, (-50, -34, 74), (50, 34, 82))
    lbox(bx, by, 0, 0, (-56, -42, 0), (-50, 42, 82))
    M.ent('trigger_teleport', brushes=[box((bx - 44, by - 26, 4), (bx + 4, by + 26, 70), TRIG)], target='vault_in')
    trigger_sound((bx + 10, by - 26, 4), (bx + 50, by + 26, 60), 'sound/world/misc/secret_found.ogg', 'barrel_secret', 30, volume=0.7)
    light(bx, by, 40, 90, '1 0.75 0.4')
    KEEP_OUT.append((bx, by, 70))
    spawn(SX - 200, SY - 40, L.WAIST_Z, 0)
    spawn(SX + 250, SY - 10, 0, 180)


# =================================================================================================== Skull Rock
def skull_rock():
    cx, cy = L.SK
    custom('skull_rock', cx, cy, 0, _lightmapscale=1.0)
    clipped(SH.skull_shell()); clipped(SH.skull_hat()); clipped(SH.skull_interior())
    NOGO.append((cx - 540, cy - 540, cx + 540, cy + 540))
    route('skull_mouth', (cx + 20, cy - 620, 0), (cx + 120, cy - 120, 0))
    st0 = L.sk_balc_step(0)
    a0 = math.radians(st0[0] - 12)
    route('skull_stair', (cx + 230 * math.cos(a0), cy + 230 * math.sin(a0), 0), (cx, cy - 330, L.BALC_Z))
    # centre pad up the shaft onto the crown, fling pad from the crown down to the plaza
    jumppad(cx, cy, 0, (cx, cy + 124, L.CROWN_Z), 900, 'pad_crown')
    weapon('betty', cx - 120, cy - 20, L.CROWN_Z, 'purple')
    item('ammo_betty', cx + 120, cy + 10, L.CROWN_Z)
    jumppad(cx + 10, cy - 136, L.CROWN_Z, (cx - 60, cy - 830, 0), 760, 'pad_crown_fling')
    trigger_sound((cx - 80, cy + 64, L.CROWN_Z + 2), (cx + 80, cy + 190, L.CROWN_Z + 70), 'sound/world/human/applause.ogg', 'crown_cheer', 15, volume=0.6)
    # the balcony behind the eyes, the cave floor, the brim
    item('item_armor_padshield', cx - 60, cy - 320, L.BALC_Z); item('ammo_imperius', cx + 130, cy - 300, L.BALC_Z)
    item('ammo_balloony', cx - 160, cy + 120, 0); item('item_armor_shard', cx + 170, cy - 60, 0)
    for (x, y) in ((cx - 380, cy + 150), (cx + 380, cy - 150), (cx, cy + 390)):
        item('item_armor_shard' if y > cy else 'ammo_nipper', x, y, L.BRIM_Z)
    item('item_jumper', cx - 250, cy - 300, L.BRIM_Z)
    # light: torches inside, the red glow behind the eyes
    for k in range(4):
        a = math.radians(45 + 90 * k)
        light(cx + 140 * math.cos(a), cy + 140 * math.sin(a), 140, 200, '1 0.7 0.4')
    for s in (-1, 1):
        a = math.radians(L.SK_FACE + s * math.degrees(118 / L.SK_RR))
        light(cx + 300 * math.cos(a), cy + 300 * math.sin(a), 350, 130, '1 0.45 0.3')
    light(cx, cy, 420, 200, '1 0.8 0.6')
    trigger_sound((cx - 100, cy - 200, 2), (cx + 100, cy - 140, 120), 'sound/world/misc/evil_laughter.ogg', 'skull_laugh', 25, volume=0.6)
    # rocks piled round the base (cover), the mouth left clear
    for k, (a, nm, rr) in enumerate(((210, 'boulder_b', 90), (175, 'boulder_a', 60), (140, 'boulder_c', 130), (100, 'boulder_a', 60), (60, 'boulder_b', 90),
                                     (25, 'boulder_a', 60), (330, 'boulder_b', 90), (-5, 'boulder_c', 130))):
        hh = rr * 0.9
        r0 = max(L.sk_deform(math.radians(a), L.sk_profile(z), z) for z in np.linspace(0, hh, 6)) + rr * 0.72 + 4
        px, py = L.ang_pt(cx, cy, r0, a)
        custom(nm, px, py, 0, 37 * k)
        A(cyl(px, py, rr * 0.7, 0, rr * 0.9 - 6, WCLIP, 10))
    speaker(cx, cy, 200, 'ambient/droplets_echoing', volume=0.4)
    spawn(cx + 200, cy + 100, 0, 225)
    spawn(cx, cy - 300, L.BALC_Z, 270)


# =================================================================================================== slides
def slide_brushes(pts, hw, wall_h, roof=None, floor_t=16, wall_t=8):
    P = [np.array(p, float) for p in pts]
    n = len(P)
    dirs = []
    for i in range(n - 1):
        d = P[i + 1][:2] - P[i][:2]; dirs.append(d / np.linalg.norm(d))
    perps = [np.array([-d[1], d[0]]) for d in dirs]
    jl = []
    for k in range(n):
        if k == 0: m = perps[0]
        elif k == n - 1: m = perps[-1]
        else:
            m = perps[k - 1] + perps[k]; m = m / np.linalg.norm(m)
        ref = perps[min(k, n - 2)]
        f = 1.0 / max(0.5, float(m @ ref))
        jl.append((m, f))
    for i in range(n - 1):
        (ma, fa), (mb, fb) = jl[i], jl[i + 1]
        ca, cb = P[i], P[i + 1]
        za, zb = ca[2], cb[2]
        def edge(c, m, f, off): return c[:2] + m * off * f
        La, Ra = edge(ca, ma, fa, hw), edge(ca, ma, fa, -hw)
        Lb, Rb = edge(cb, mb, fb, hw), edge(cb, mb, fb, -hw)
        for tri in ((La, Ra, Lb, za, za, zb), (Ra, Rb, Lb, za, zb, zb)):
            p1, p2, p3, z1, z2, z3 = tri
            A(hull([(p1[0], p1[1], z1), (p2[0], p2[1], z2), (p3[0], p3[1], z3),
                    (p1[0], p1[1], z1 - floor_t), (p2[0], p2[1], z2 - floor_t), (p3[0], p3[1], z3 - floor_t)], SLICK, round_pts=False))
        for side in (1, -1):
            ia, ib = edge(ca, ma, fa, side * hw), edge(cb, mb, fb, side * hw)
            oa, ob = edge(ca, ma, fa, side * (hw + wall_t)), edge(cb, mb, fb, side * (hw + wall_t))
            pw = []
            for (p, zz) in ((ia, za), (ib, zb), (oa, za), (ob, zb)):
                pw += [(p[0], p[1], zz - floor_t), (p[0], p[1], zz + wall_h)]
            A(hull(pw, WCLIP, round_pts=False))
        if roof:
            oLa, oRa = edge(ca, ma, fa, hw + wall_t), edge(ca, ma, fa, -hw - wall_t)
            oLb, oRb = edge(cb, mb, fb, hw + wall_t), edge(cb, mb, fb, -hw - wall_t)
            for tri in ((oLa, oRa, oLb, za, za, zb), (oRa, oRb, oLb, za, zb, zb)):
                p1, p2, p3, z1, z2, z3 = tri
                A(hull([(p1[0], p1[1], z1 + wall_h), (p2[0], p2[1], z2 + wall_h), (p3[0], p3[1], z3 + wall_h),
                        (p1[0], p1[1], z1 + wall_h + 6), (p2[0], p2[1], z2 + wall_h + 6), (p3[0], p3[1], z3 + wall_h + 6)], WCLIP, round_pts=False))


def on_ground_free(x, y, m=48):
    if abs(x) > L.HX - m or abs(y) > L.HY - m: return False
    for t in TILES:
        if in_rect(x, y, t, m): return False
    if math.hypot(x - L.SK[0], y - L.SK[1]) < L.BRIM_R1 + 60 + m: return False
    if in_rect(x, y, L.FORT, m) or math.hypot(x - L.TOWER[0], y - L.TOWER[1]) < L.TOWER_R + m: return False
    for r in L.SHACKS:
        if in_rect(x, y, r, m + 40): return False
    return True


def supports_for(path, every=5, zmin=110):
    out = []
    for i in range(2, len(path) - 2, every):
        x, y, z = path[i]
        if z >= zmin and on_ground_free(x, y): out.append((x, y, z))
    return out


def slides_place():
    import pp_models as PM
    sp = L.tube_path(); fp = L.flume_path()
    custom('cannon_tube', 0, 0, 0)
    slide_brushes(sp[1:], 40, 96, roof=True)
    for (x, y, z) in PM.SUPPORTS['tube']:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        A(box((round(x) - 34, round(y) - 12, 0), (round(x) + 34, round(y) + 12, round(zt) - 30), WCLIP))
        KEEP_OUT.append((x, y, 70))
    for (x, y, z) in sp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    x0, y0, z0 = sp[1]
    custom('tube_mouth', x0, y0, z0, 180)
    R = L.TUBE_R
    route('tube_mouth', (x0 + 140, y0 - 20, z0), (x0 + 30, y0, z0))
    custom('log_flume', 0, 0, 0)
    slide_brushes(fp[1:], 46, 48)
    for (x, y, z) in PM.SUPPORTS['flume']:
        A(box((round(x) - 36, round(y) - 12, 0), (round(x) + 36, round(y) + 12, round(z) - 40), WCLIP))
        KEEP_OUT.append((x, y, 70))
    for (x, y, z) in fp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    fx, fy, fz = fp[1]
    custom('flume_gate', fx - 6, fy, fz, 0)
    for s in (-1, 1):
        A(cyl(fx - 6, fy + s * 74, 8, fz, fz + 150, WCLIP, 8))
    speaker(sp[-1][0], sp[-1][1], 40, 'ambient/water_shower', volume=0.4)
    speaker(fp[-1][0], fp[-1][1], 40, 'ambient/water_shower', volume=0.4)


# =================================================================================================== Fort San Padro
def fort():
    x0, y0, x1, y1 = L.FORT
    import pp_models as PM
    custom('fort', PM.FORT_O[0], PM.FORT_O[1], 0, _lightmapscale=1.0)
    clipped(SH.fort())
    NOGO.append((x0 - 40, y0 - 60, x1 + 40, y1 + 40))
    NOGO.append((L.TOWER[0] - L.TOWER_R - 40, L.TOWER[1] - L.TOWER_R - 40, L.TOWER[0] + L.TOWER_R + 40, L.TOWER[1] + L.TOWER_R + 40))
    gx = (x0 + x1) / 2
    route('fort_gate', (gx, y0 - 120, 0), (gx, y0 + 220, 0))
    cx0, cy0, cx1, cy1 = SH.fort_courtyard()
    route('fort_stair_e', (cx1 - 140, cy0 + 40, 0), (x1 - 150, y1 - 100, L.FORT_H))
    route('fort_stair_w', (cx0 + 140, cy0 + 40, 0), (x0 + 150, y1 - 100, L.FORT_H))
    md = (L.MAG[0] + L.MAG[2]) / 2
    route('magazine', (md, cy1 - 80, 0), (md, (L.MAG[1] + L.MAG[3]) / 2, 0))
    # magazine: powder kegs, BamBam
    for (dx, dy) in ((-120, 40), (-120, -30), (120, 40), (120, -30), (-70, 50)):
        furn('barrel', md + dx, (L.MAG[1] + L.MAG[3]) / 2 + dy, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    item('holdable_bambam', md, (L.MAG[1] + L.MAG[3]) / 2 + 30, 0); item('ammo_pumper', md + 60, L.MAG[1] + 30, 0)
    light(md, (L.MAG[1] + L.MAG[3]) / 2, 120, 160, '1 0.75 0.45')
    # courtyard: well-stacked cannonballs, barrels, a cart of crates, shield on the wall
    furn('cannonballs', cx0 + 120, cy0 + 120, 0, 0, [((-26, -26, 0), (26, 26, 30))])
    furn('cannonballs', cx1 - 120, cy0 + 120, 0, 0, [((-26, -26, 0), (26, 26, 30))])
    furn('crate_big', gx - 140, cy1 - 110, 0, 15, [((-36, -36, 0), (36, 36, 72))])
    furn('crate', gx - 70, cy1 - 70, 0, -10, [((-24, -24, 0), (24, 24, 48))])
    item('item_armor_padshield', gx + 100, cy0 + 120, 0); item('ammo_bubbleg', gx - 120, cy0 + 60, 0)
    station(gx + 140, cy1 - 70, 0, 0)
    for (lx, ly) in ((cx0 + 130, cy0 + 60), (cx1 - 130, cy0 + 60), (cx0 + 130, cy1 - 60), (cx1 - 130, cy1 - 60)):
        light(lx, ly, 150, 200, '1 0.8 0.55')
    # ramparts: cannons along the south and west walls, ammo
    H = L.FORT_H
    for xx in (x0 + 140, x0 + 300, x1 - 300):
        furn('cannon', xx, y0 + 62, H, 270, [((-46, -22, 0), (40, 22, 40))])
    for yy in (y0 + 260, y1 - 330):
        furn('cannon', x0 + 62, yy, H, 180, [((-46, -22, 0), (40, 22, 40))])
    item('ammo_balloony', x0 + 48, y1 - 120, H); item('ammo_splasher', gx, y1 - 112, H)
    # pad onto the watchtower (Pumper), the mortar launcher onto Skull Rock's brim
    tx, ty = L.TOWER
    jumppad(x1 - 48, y0 + 210, H, (tx - 20, ty + 24, L.TOWER_H), 640, 'pad_tower')
    weapon('pumper', tx + 10, ty - 30, L.TOWER_H, 'green')
    item('ammo_pumper', tx - 50, ty - 60, L.TOWER_H)
    mx_, my_ = L.MORTAR
    custom('mortar', mx_, my_, H)
    for k in range(24):
        a0, a1 = 15 * k, 15 * (k + 1)
        am = (a0 + a1) / 2
        if abs(((am - 180) + 180) % 360 - 180) < 40: continue
        A(SH.ring_seg(mx_, my_, a0, a1, 37, 43, H, H + 38, tex=WCLIP))
    land = L.ang_pt(L.SK[0], L.SK[1], 392, 158)
    jumppad(mx_, my_, H, (land[0], land[1], L.BRIM_Z), 820, 'pad_mortar')
    timer_sound(x0 - 100, y1, 300, 'misc/shot_long', 'fort_gun', 35, 20, volume=0.5)
    spawn(gx, cy0 + 200, 0, 90)
    spawn(x0 + 48, y0 + 160, H, 0)


# =================================================================================================== Shark Pool + dive tower
def shark_pool():
    x0, y0, x1, y1 = L.SHARK
    fz = L.SHARK_FLOOR
    tile = box((SHARK_TILE[0], SHARK_TILE[1], L.SLAB_BOT), (SHARK_TILE[2], SHARK_TILE[3], 0), CAULK)
    for b in carve(tile, [box((x0, y0, fz), (x1, y1, 32), CAULK)]):
        A(edge_faces_caulk(texby(b, pool_tex), SHARK_TILE))
    steps = []
    n = (L.WATER - fz) // 16
    for k in range(n):
        b = box((x0, y0 + 24 * k, fz), (x1, y0 + 24 * (k + 1), -16 - 16 * k), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': CAULK})
        steps.append(b); A(b)
    for b in carve(box((x0, y0, fz), (x1, y1, L.WATER), CAULK), steps):
        A(water_faces(b, True))
    NOGO.append(tuple(SHARK_TILE))
    cxp, cyp = (x0 + x1) / 2, (y0 + 24 * n + y1) / 2
    weapon('splasher', cxp, cyp + 80, fz, 'orange')
    item('ammo_splasher', x0 + 100, y1 - 100, fz); item('ammo_balloony', x1 - 120, y0 + 24 * 6 + 12, -16 - 16 * 6)
    for (x, y) in ((cxp - 160, cyp), (cxp + 160, cyp + 100)):
        light(x, y, fz + 80, 220, '0.5 0.9 1')
    speaker(cxp, cyp, 0, 'ambient/water_bubbling', volume=0.4)
    route('shark_steps', ((x0 + x1) / 2, y0 + 24 * 3 + 12, -64), ((x0 + x1) / 2, y0 - 100, 0))
    # sharks circling under the surface
    zc = -150
    M.ent('func_rotating', brushes=[box((cxp - 8, cyp - 8, zc - 8), (cxp + 8, cyp + 8, zc + 8), ORIGIN),
                                    box((cxp - 4, cyp - 4, zc + 20), (cxp + 4, cyp + 4, zc + 28), NODRAW_NS)],
          model2=pplib.IQM['sharks'], speed=14, spawnflags=0, dmg=0)
    # dive tower
    cx, cy = L.DIVE
    custom('dive_tower', cx, cy, 0)
    blist, steps_, holes = SH.dive_tower()
    clipped(blist)
    NOGO.append((cx - L.DIVE_HALF - 40, cy - L.DIVE_HALF - 40, cx + L.DIVE_HALF + 40, cy + L.DIVE_HALF + 40))
    h = L.DIVE_HALF; top = L.DIVE_TOP
    A(box((cx - h - 224, cy + 64, top - 8), (cx - h, cy + 112, top), WCLIP))           # the plank
    for (a, b) in (((cx - h, cy + h - 8), (cx + h, cy + h)), ((cx + h - 8, cy - h), (cx + h, cy + h - 8)), ((cx, cy - h), (cx + h - 8, cy - h + 8)),
                   ((cx - h, cy + 112), (cx - h + 8, cy + h - 8)), ((cx - h, cy + 48), (cx - h + 8, cy + 64))):
        A(box((a[0], a[1], top), (b[0], b[1], top + 40), CLIP))
    route('dive_stair', (cx - h - 40, cy - h - 40, 0), (cx + 60, cy + 60, top))
    jumppad(cx, cy - h - 190, 0, (cx + 64, cy + 70, top), 620, 'pad_dive')
    weapon('balloony', cx + 70, cy + 20, top, 'black')
    item('ammo_imperius', cx + 40, cy + 96, top)
    trigger_sound((cx - h - 224, cy + 64, top + 2), (cx - h - 150, cy + 112, top + 60), 'sound/world/misc/evil_laughter.ogg', 'plank_laugh', 20, volume=0.5)
    A(sign_box((x0 + 40, y0 - 60, 120), (x0 + 552, y0 - 56, 184), T('sign_shark'), 1024, 128, back=CAULK, facing='s'))
    A(box((x0 + 32, y0 - 56, 0), (x0 + 560, y0 - 40, 192), {'side': T('planks'), 'top': T('planks'), 'bot': CAULK}))
    NOGO.append((x0 + 20, y0 - 80, x0 + 580, y0 - 20))
    spawn(x1 + 60, y0 + 100, 0, 90)


# =================================================================================================== Treasure Cove
def treasure_cove():
    x0, y0, x1, y1 = L.COVE
    hx, hy, hr = L.COVE_HOLE
    tile = box((COVE_TILE[0], COVE_TILE[1], L.SLAB_BOT), (COVE_TILE[2], COVE_TILE[3], 0), CAULK)
    cut = [box((x0, y0, L.SHALLOW), (x1, y1, 32), CAULK), cyl(hx, hy, hr, L.COVE_HOLE_Z, 32, CAULK, 16)]
    def tx(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(c[2]) < 0.5: return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('wet_sand') if c[2] > L.COVE_HOLE_Z + 1 else T('pool_tile')
        return T('rock') if math.hypot(c[0] - hx, c[1] - hy) < hr + 2 else T('pool_band')
    for b in carve(tile, cut):
        A(edge_faces_caulk(texby(b, tx), COVE_TILE))
    solids = []
    bw = L.COVE_BEACH
    beach = hull([(x, y1, L.SHALLOW) for x in (x0, x1)] + [(x, y1, 0) for x in (x0, x1)] + [(x, y1 - bw, L.SHALLOW) for x in (x0, x1)],
                 {'top': T('wet_sand'), 'side': T('pool_band'), 'bot': CAULK}, round_pts=False)
    A(beach); solids.append(beach)
    for j in range(3):
        b = box((x1 - 64 + 21 * j, -1400, L.SHALLOW), (x1 - 64 + 21 * (j + 1), -1180, L.SHALLOW + 16 * (j + 1)), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
        A(b); solids.append(b)
    for b in carve(box((x0, y0, L.SHALLOW), (x1, y1, L.WATER), CAULK), solids):
        A(water_faces(b))
    A(water_faces(cyl(hx, hy, hr, L.COVE_HOLE_Z, L.SHALLOW, CAULK, 16), True))
    NOGO.append(tuple(COVE_TILE))
    item('holdable_floater', hx, hy, L.COVE_HOLE_Z); item('ammo_betty', hx + 90, hy - 60, L.COVE_HOLE_Z)
    item('ammo_splasher', x0 + 90, y0 + 120, L.SHALLOW); item('ammo_boaster', x1 - 140, y1 - 60, 0)
    light(hx, hy, L.COVE_HOLE_Z + 80, 200, '0.5 0.9 1')
    speaker((x0 + x1) / 2, (y0 + y1) / 2, 0, 'ambient/water_rippling', volume=0.4)
    A(sign_box((x0 - 96, y1 + 120, 100), (x0 + 288, y1 + 124, 172), T('sign_cove'), 1024, 192, back=CAULK, facing='s'))
    A(box((x0 - 104, y1 + 124, 0), (x0 + 296, y1 + 140, 180), {'side': T('planks'), 'top': T('planks'), 'bot': CAULK}))
    NOGO.append((x0 - 120, y1 + 100, x0 + 310, y1 + 160))
    # beach shacks (walk in; pads onto their thatched roofs)
    for i, (rx0, ry0, rx1, ry1) in enumerate(L.SHACKS):
        door = 'e'
        custom(f'shack_{i}', (rx0 + rx1) / 2, (ry0 + ry1) / 2, 0)
        clipped(SH.shack((rx0, ry0, rx1, ry1), door))
        NOGO.append((rx0 - 40, ry0 - 40, rx1 + 40, ry1 + 40))
        xc, yc = (rx0 + rx1) / 2, (ry0 + ry1) / 2
        if door == 'e':
            route(f'shack{i}_door', (rx1 + 120, yc, 0), (xc - 30, yc, 0))
            if i == 0: jumppad(rx1 + 130, ry1 - 30, 0, (xc - 40, yc + 30, L.SHACK_H), L.SHACK_H + 140, f'pad_shack{i}')
            else: jumppad(rx1 + 110, ry0 + 40, 0, (xc - 40, yc - 20, L.SHACK_H), L.SHACK_H + 140, f'pad_shack{i}')
        else:
            route(f'shack{i}_door', (xc, ry1 + 120, 0), (xc, yc - 20, 0))
            jumppad(rx1 + 80, ry1 + 80, 0, (xc + 30, yc, L.SHACK_H), L.SHACK_H + 140, f'pad_shack{i}')
        light(xc, yc, L.SHACK_H - 50, 140, '1 0.8 0.55')
    item('ammo_pumper', (L.SHACKS[0][0] + L.SHACKS[0][2]) / 2 + 40, (L.SHACKS[0][1] + L.SHACKS[0][3]) / 2 - 40, L.SHACK_H)
    item('item_speedy', (L.SHACKS[1][0] + L.SHACKS[1][2]) / 2 - 60, (L.SHACKS[1][1] + L.SHACKS[1][3]) / 2, L.SHACK_H)
    item('ammo_boaster', (L.SHACKS[0][0] + L.SHACKS[0][2]) / 2, (L.SHACKS[0][1] + L.SHACKS[0][3]) / 2, 0)
    item('ammo_nipper', (L.SHACKS[1][0] + L.SHACKS[1][2]) / 2 + 60, (L.SHACKS[1][1] + L.SHACKS[1][3]) / 2, 0)
    # beach dressing
    furn('rowboat', -1440, -620, 0, 110, [((-70, -24, 0), (70, 24, 34))])
    furn('rowboat', -2210, -1720, 0, 80, [((-70, -24, 0), (70, 24, 34))])
    furn('chest_open', -1460, -900, 0, 200, [((-30, -18, 0), (30, 18, 24))])
    furn('chest_shut', -2230, -350, 0, 90, [((-30, -18, 0), (30, 18, 40))])
    furn('hammock', -2120, 380, 0, 0, [((-114, -6, 0), (-106, 6, 110)), ((106, -6, 0), (114, 6, 110))])
    spawn(-1450, -300, 0, 270)
    spawn(-2200, -1900, 0, 45)


# =================================================================================================== Tortuga Quay
def tortuga():
    x0, y0, x1, y1 = L.TAV
    custom('tavern', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    clipped(SH.tavern())
    NOGO.append((x0 - 60, y0 - 130, x1 + 40, y1 + 40))
    yc = (y0 + y1) / 2
    route('tavern_door', (x0 - 140, yc, 0), (x0 + 160, yc, 0))
    for s in (-1, 1):                      # porch posts
        A(cyl(x0 - 86, yc + s * 112, 6, 0, 150, WCLIP, 8))
    for (dy) in (-170, 170):
        furn('barrel', x0 - 40, yc + dy, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    route('tavern_stair', (x1 - 400, y0 - 60, 0), (x0 + 200, yc, L.TAV_H))
    weapon('boaster', (x0 + x1) / 2 - 40, yc + 60, 0, 'orange')
    item('ammo_boaster', x0 + 80, y0 + 80, 0); item('ammo_bubbleg', x0 + 80, y1 - 80, 0)
    for (x, y) in ((x0 + 140, yc - 130), (x0 + 140, yc + 150), (x0 + 300, yc - 170)):
        custom('table', x, y, 0, 0); A(cyl(x, y, 28, 0, 36, WCLIP, 10))
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            custom('stool', x + 50 * math.cos(a), y + 50 * math.sin(a), 0, 0)
        mdl_c('pad_ddmix/padship/rumbottle2.md3', x + 8, y - 6, 36, 0.25, 20)
    bx = x1 - 24 - 130
    for k in range(4):
        custom('stool', bx - 50, yc - 120 + k * 80, 0, 0)
    for z in (88, 128):
        custom('bottles', x1 - 24 - 14, yc - 80, z, 0); custom('bottles', x1 - 24 - 14, yc + 80, z, 0)
    for z in (84, 124, 164):
        A(box((x1 - 24 - 30, yc - 180, z), (x1 - 24, yc + 180, z + 4), WCLIP))
    for (dy) in (-200, 200):
        furn('barrel', x1 - 60, yc + dy, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    mdl_c('pad_ddmix/padship/shiplamp.md3', bx, yc + 110, 62, 0.35, 0)
    light((x0 + x1) / 2 - 60, yc, L.TAV_H - 90, 280, '1 0.78 0.5')
    light(x1 - 120, yc, 150, 160, '1 0.78 0.5')
    speaker((x0 + x1) / 2, yc, 100, 'misc/an_session', volume=0.25)
    # roof terrace
    item('item_armor_padshield', x0 + 120, y1 - 120, L.TAV_H); item('ammo_betty', x1 - 120, y1 - 100, L.TAV_H)
    for (x, y) in ((x0 + 160, y0 + 160), (x1 - 200, y1 - 180)):
        custom('parasol_r', x, y, L.TAV_H); A(cyl(x, y, 5, L.TAV_H, L.TAV_H + 180, WCLIP, 6))
    spawn(x0 + 260, yc + 180, L.TAV_H, 180)
    # the gift shop
    sx0, sy0, sx1, sy1 = L.SHOP
    custom('shop', (sx0 + sx1) / 2, (sy0 + sy1) / 2, 0)
    clipped(SH.shop())
    NOGO.append((sx0 - 100, sy0 - 40, sx1 + 40, sy1 + 40))
    syc = (sy0 + sy1) / 2
    route('shop_door', (sx0 - 140, syc, 0), (sx0 + 240, syc, 0))
    jumppad(sx0 - 90, sy0 + 70, 0, (sx0 + 150, sy0 + 150, L.SHOP_H), L.SHOP_H + 230, 'pad_shop')
    item('ammo_balloony', sx1 - 100, sy1 - 90, L.SHOP_H); item('item_climber', sx0 + 260, syc, L.SHOP_H)
    item('ammo_boaster', sx1 - 80, syc, 0); item('ammo_nipper', sx0 + 80, sy0 + 70, 0)
    mdl_c('pad_ddmix/castle/sword.md3', sx0 + 160, syc - 60, 48, 1.0, 90)
    mdl_c('pad_ddmix/castle/shield.md3', sx0 + 160, syc + 40, 48, 1.0, 90)
    mdl_c('pad_ddmix/padship/rumbottle1.md3', sx0 + 160, syc + 80, 48, 0.3, 0)
    furn('chest_open', sx1 - 80, sy0 + 70, 0, 0, [((-30, -18, 0), (30, 18, 24))])
    light((sx0 + sx1) / 2, syc, L.SHOP_H - 60, 220, '1 0.85 0.65')
    # market stalls on the boardwalk
    for (y, nm) in ((-1440, 'stall_fruit'), (-1190, 'stall_fish'), (180, 'stall_rum')):
        furn(nm, 1470, y, 0, 0, [((-40, -80, 0), (40, 80, 50))])
        for (dx, dy) in ((-40, -80), (40, -80), (-40, 80), (40, 80)):
            A(cyl(1470 + dx, y + dy, 4, 50, 128, WCLIP, 6))
        NOGO.append((1400, y - 100, 1540, y + 100))
    # harbour clutter: crate stacks, barrels, the big anchor, lamp posts, a signpost
    for (x, y, a) in ((1700, -1060, 10), (2160, -1130, -20), (1700, 300, 30), (2050, 420, 0)):
        furn('crate_big', x, y, 0, a, [((-36, -36, 0), (36, 36, 72))])
        furn('crate', x + 10, y + 6, 72, a + 25, [((-24, -24, 0), (24, 24, 48))])
        KEEP_OUT.append((x, y, 70))
    for (x, y) in ((1640, -1180), (2180, -280), (1640, 460)):
        furn('barrel', x, y, 0, 0, [((-20, -20, 0), (20, 20, 56))])
        furn('barrel', x + 44, y + 10, 0, 0, [((-20, -20, 0), (20, 20, 56))])
        KEEP_OUT.append((x + 20, y, 60))
    furn('capstan', 1520, -300, 0, 0, [((-22, -22, 0), (22, 22, 46))]); KEEP_OUT.append((1520, -300, 70))
    furn('anchor_big', 1900, -1900, 0, 30, [((-78, -10, 0), (78, 10, 50)), ((-10, -10, 50), (10, 10, 190))])
    KEEP_OUT.append((1900, -1900, 100))
    for (x, y) in ((1420, -1650), (1420, -900), (1420, -400), (1420, 420)):
        custom('lantern_post', x, y, 0, 0); A(box((x - 6, y - 6, 0), (x + 6, y + 6, 150), WCLIP))
        light(x + 34, y, 132, 150, '1 0.8 0.5')
        KEEP_OUT.append((x, y, 30))
    station(2200, -1500, 0, 180)
    spawn(1900, -1150, 0, 180); spawn(2100, 200, 0, 225)


# =================================================================================================== secret: Captain Padbeard's Hoard
def vault():
    F = L.VAULT
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('rock'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('gold_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('rock'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    for (x, y, nm) in ((-480, 300, 'gold_heap'), (480, 300, 'gold_heap'), (-560, -220, 'gold_heap_s'), (560, -220, 'gold_heap_s'), (-250, 420, 'gold_heap_s')):
        custom(nm, x, y, z0)
        rr = 80 if nm == 'gold_heap' else 50
        A(cyl(x, y, rr * 0.85, z0, z0 + rr * 0.45 - 4, WCLIP, 12))
    furn('skeleton_throne', 0, 420, z0, 0, [((-44, -40, 0), (44, 40, 40)), ((-44, 26, 40), (44, 40, 180))])
    for (x, y, a) in ((-200, 330, 160), (200, 330, 20), (380, 60, 90), (-380, 60, 270)):
        furn('chest_open', x, y, z0, a, [((-30, -18, 0), (30, 18, 24))])
    for (x, y) in ((-640, 480), (640, 480), (-640, -480), (640, -480)):
        custom('torch_post', x, y, z0, 0, lit=False); A(cyl(x, y, 6, z0, z0 + 140, WCLIP, 6))
        light(x, y, z0 + 190, 220, '1 0.65 0.3')
    item('item_padpower', 0, 200, z0); item('item_revival', -300, 120, z0); item('holdable_killerducks', 300, 120, z0)
    item('ammo_imperius', -620, 0, z0); item('ammo_betty', 620, 0, z0); item('item_armor_padshield', 0, -100, z0)
    A(sign_box((-320, y1 - 4, z0 + 300), (320, y1, z0 + 380), T('sign_vault'), 1024, 128, facing='s'))
    M.ent('misc_teleporter_dest', (0, -260, z0 + 24), targetname='vault_in', angle=90)
    mdl_c('pad_teleporter/padtp_orange.md3', 0, -480, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -516, z0 + 2), (36, -444, z0 + 90), TRIG)], target='vault_out')
    M.ent('misc_teleporter_dest', (-600, 260, 24), targetname='vault_out', angle=270)
    for (x, y, c) in ((0, 0, '1 0.85 0.5'), (-480, 300, '1 0.8 0.4'), (480, 300, '1 0.8 0.4'), (0, -380, '1 0.9 0.7'), (-480, -300, '1 0.8 0.5'),
                      (480, -300, '1 0.8 0.5'), (0, 380, '1 0.85 0.5')):
        light(x, y, z0 + 260, 420, c)
    speaker(0, 0, z0 + 200, 'ambient/water_drippling', volume=0.4)
    timer_sound(0, 300, z0 + 150, 'misc/evil_laughter', 'vault_laugh', 30, 10, volume=0.5)


# =================================================================================================== movers
def gulls():
    z = L.GULL_Z
    M.ent('func_rotating', brushes=[box((-8, -8, z - 8), (8, 8, z + 8), ORIGIN), box((-4, -4, z + 40), (4, 4, z + 48), NODRAW_NS)],
          model2=pplib.IQM['gulls'], speed=6, spawnflags=0, dmg=0)
    timer_sound(0, -1200, 800, 'animal/bird_gull', 'gull1', 14, 8, volume=0.8)
    timer_sound(-1600, 800, 700, 'animal/bird_gull', 'gull2', 19, 9, volume=0.7)
    timer_sound(1600, 600, 700, 'animal/bird_gull', 'gull3', 23, 10, volume=0.7)


# =================================================================================================== decoration, cover
def decor():
    rng = np.random.default_rng(7)
    # main sign on the south promenade
    A(sign_box((-400, -1996, 100), (400, -1992, 300), T('sign_main'), 1024, 256, back=CAULK, facing='n'))
    A(box((-416, -2024, 0), (416, -1996, 316), {'side': T('fort_stone'), 'top': T('coping'), 'bot': CAULK}))
    NOGO.append((-460, -2048, 460, -1960))
    A(sign_box((L.SK[0] + 200, L.SK[1] - 476, 120), (L.SK[0] + 456, L.SK[1] - 472, 184), T('sign_skull'), 512, 128, back=CAULK, facing='s'))
    A(box((L.SK[0] + 192, L.SK[1] - 472, 0), (L.SK[0] + 464, L.SK[1] - 456, 192), {'side': T('planks'), 'top': T('planks'), 'bot': CAULK}))
    NOGO.append((L.SK[0] + 170, L.SK[1] - 500, L.SK[0] + 490, L.SK[1] - 430))
    def put(name, x, y, r, ang=None, z=0.0, box_=None, lit=True, tries=320, cyl_=None):
        p = near_free(x, y, r, tries)
        if p is None: return None
        a = rng.uniform(0, 360) if ang is None else ang
        custom(name, p[0], p[1], z, a, lit=lit)
        if box_:
            for (mn, mx) in box_:
                lbox(p[0], p[1], z, a, mn, mx)
        if cyl_:
            A(cyl(p[0], p[1], cyl_[0], z, z + cyl_[1], WCLIP, 8))
        KEEP_OUT.append((p[0], p[1], r))
        return p
    # the captain's statue on the plaza
    put('captain_statue', 520, 180, 90, ang=270, box_=[((-60, -60, 0), (60, 60, 96)), ((-40, -30, 96), (40, 30, 330))])
    put('anchor_big', -620, 220, 100, ang=10, box_=[((-78, -10, 0), (78, 10, 50)), ((-10, -10, 50), (10, 10, 190))])
    palms = [(-1300, 300), (-900, 420), (-300, 300), (250, 420), (900, 380), (1250, 260), (-1250, -100), (1250, -120), (-1700, 600),
             (-2150, -1100), (-2200, -600), (-1450, -1700), (-1500, -1200), (1700, 700), (2150, 750), (1300, 1900), (-1250, 1900),
             (-700, 1800), (700, 1800), (-200, -1950), (1000, -1950), (-1000, -1950), (2200, 1500), (-2200, 1700)]
    for i, (x, y) in enumerate(palms):
        p = put(['palm_a', 'palm_b', 'palm_c'][i % 3], x, y, 40, lit=False)
        if p: A(cyl(p[0], p[1], 12, 0, 220, WCLIP, 8))
    for i, (x, y) in enumerate(((-900, 120), (900, 120), (-1700, 1000) if False else (-1250, 650), (1300, 640), (-500, 1800), (500, 1750),
                                (-2000, 800), (1300, 1500), (-1500, -500), (2000, -1700), (-150, -1950), (2150, 1100), (-2100, -800))):
        nm = ['boulder_a', 'boulder_b', 'boulder_c'][i % 3]
        rr = [60, 90, 130][i % 3]
        p = put(nm, x, y, rr * 0.9)
        if p: A(cyl(p[0], p[1], rr * 0.72, 0, rr * 0.9 - 6, WCLIP, 10))
    # beach furniture by the water
    for (x, y, a) in ((-1050, -1930, 90), (-900, -1930, 90), (900, -1930, 90), (1050, -1930, 90), (-1460, -1350, 0), (-2220, -1250, 0),
                      (1600, 1000, 0), (1600, 1200, 0), (2000, 950, 180)):
        put('lounger_r' if x < 0 else 'lounger_b', x, y, 44, ang=a, box_=[((-34, -14, 0), (34, 14, 14))])
    for (x, y, nm) in ((-975, -1890, 'parasol_r'), (975, -1890, 'parasol_b'), (-1450, -1270, 'parasol_b'), (1600, 1100, 'parasol_r'), (-2230, -1150, 'parasol_r')):
        p = put(nm, x, y, 40)
        if p: A(cyl(p[0], p[1], 5, 0, 180, WCLIP, 6))
    for (x, y) in ((-1400, -100), (1380, 20), (1400, 1700), (-1380, -1850), (400, -1900)):
        put('life_ring', x, y, 30, box_=[((-4, 2, 0), (4, 10, 44))])
    # torches round the plaza and the skull, signposts, a parrot
    for (x, y) in ((-200, 380), (200, 380), (-560, 560), (560, 560), (-200, -110), (200, -110), (-1200, -1900), (1200, -1900), (-1400, 1400), (1300, 1250)):
        p = put('torch_post', x, y, 30, ang=0, lit=False, cyl_=(7, 135))
        if p:
            light(p[0], p[1], 210, 140, '1 0.65 0.3')
    speaker(-200, 380, 160, 'ambient/fire_crackling', volume=0.3); speaker(200, -110, 160, 'ambient/fire_crackling', volume=0.3)
    for (x, y) in ((-150, 620), (1280, -300), (-1300, 1000)):
        put('signpost', x, y, 40, box_=[((-5, -5, 0), (5, 5, 150))])
    put('parrot_perch', 1520, -650, 30, ang=0, box_=[((-4, -4, 0), (4, 4, 120))])
    put('cannon', -800, 640, 70, ang=270, box_=[((-46, -22, 0), (40, 22, 40))])
    put('cannon', 760, 650, 70, ang=270, box_=[((-46, -22, 0), (40, 22, 40))])
    put('cannonballs', -900, 600, 40, box_=[((-26, -26, 0), (26, 26, 30))])
    put('chest_open', 300, -60, 40, ang=200, box_=[((-30, -18, 0), (30, 18, 24))])
    # catalog odds and ends for fullness
    for (x, y, s) in ((-1600, 500, 0.3), (1500, -250, 0.3), (-1100, 1500, 0.3), (1150, 1200, 0.3), (2100, -800, 0.3)):
        p = near_free(x, y, 50)
        if p: mdl_box('pad_ddmix/padship/amphora.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 45))
    for (x, y, s) in ((-1000, 1350, 0.3), (1000, 1400, 0.3), (-2000, 1300, 0.35), (2150, -350, 0.3)):
        p = near_free(x, y, 90)
        if p: mdl_c('pad_ddmix/plants/fern.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 80))
    for (x, y) in ((-1300, 1250), (1350, 900), (-2100, 1500), (1900, 1900)):
        p = near_free(x, y, 70)
        if p: mdl_c('pad_ddmix/trashcan/bush.md3', p[0], p[1], 0, 0.45, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 70))
    for (x, y, s) in ((-1480, -1500, 0.3), (1650, 1650, 0.25), (-300, -1900, 0.3)):
        p = near_free(x, y, 50)
        if p: mdl_box('pad_ducks/pad_duck.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 50))
    for (x, y) in ((-60, 680), (60, 690), (-1100, -1900), (1400, -800)):
        p = near_free(x, y, 30, 96)
        if p: mdl_c('pad_ddmix/jail/skull.md3', p[0], p[1], 0, 0.3, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 30))
    for (x, y) in ((-1350, 780), (1100, 1700), (-1800, -200)):
        p = near_free(x, y, 30, 96)
        if p: mdl_c('padfigures/coconut.md3', p[0], p[1], 0, 1.4, rng.uniform(0, 360))


def blockers():
    """mid-field cover where long eye-level lines run (placed after sightlines.py --hot)"""
    for (x, y, a) in ((-700, 30, 0), (700, 30, 0), (-1150, 200, 90), (0, 300, 0)):
        p = near_free(x, y, 70, 200)
        if p:
            custom('crate_big', p[0], p[1], 0, a); lbox(p[0], p[1], 0, a, (-36, -36, 0), (36, 36, 72))
            custom('crate', p[0] + 8, p[1] - 4, 72, a + 20); lbox(p[0] + 8, p[1] - 4, 72, a + 20, (-24, -24, 0), (24, 24, 48))
            KEEP_OUT.append((p[0], p[1], 70))


# =================================================================================================== spawns + loose items
def items_misc():
    item('ammo_nipper', -400, -60, 0); item('ammo_nipper', 600, 1700, 0); item('ammo_nipper', 1800, -1800, 0)
    item('item_armor_shard', -1600, 300, 0); item('item_armor_shard', 1600, 600, 0); item('item_armor_shard', -900, 1700, 0)
    item('ammo_bubbleg', 1000, 500, 0); item('ammo_balloony', -1900, 1850, 0); item('ammo_imperius', 2200, 1800, 0)
    station(-1150, 450, 0, 0)
    for (x, y, a) in ((-900, 260, 270), (900, 280, 270), (-1700, 750, 0), (1700, -300, 180), (-600, 1750, 270), (800, 1650, 270),
                      (-2000, 1900, 315), (2100, 1950, 225), (0, -1900, 90), (-1800, -1150, 0)):
        p = near_free(x, y, 48)
        if p: spawn(p[0], p[1], 0, a)


def lights_and_sound():
    for (x, y) in ((0, 200), (-1000, 1600), (1000, 1600), (-1800, 0), (1800, -600), (0, -1900)):
        light(x, y, 400, 300, '1 0.95 0.85')
    for (x, y) in ((-2250, -1000), (-2250, 1000), (2250, -1200), (2250, 600), (-1200, -2000), (1200, -2000)):
        speaker(x, y, 60, 'ambient/ocean_waves', volume=0.5)
    timer_sound(2200, -1800, 400, 'machine/fog_horn', 'foghorn', 60, 30, volume=0.4)
    timer_sound(-2200, 1900, 400, 'animal/bird_cardinal', 'bird1', 18, 8, volume=0.5)
    timer_sound(1500, 1900, 400, 'animal/bird_vireo', 'bird2', 22, 10, volume=0.5)


def main():
    pplib.STATE['out'] = OUT
    TX.make_textures()
    import pp_models as PM
    import pp_ship as PS
    sp, fp = L.tube_path(), L.flume_path()
    PM.SUPPORTS['tube'] = supports_for(sp[1:], 4, 120)
    PM.SUPPORTS['flume'] = supports_for(fp[1:], 3, 100)
    PS.make()
    PM.make()
    sky_hull(); ground(); sea_and_cliff()
    ship(); wreck_masts(); lagoon(); skull_rock(); slides_place(); fort(); shark_pool(); treasure_cove(); tortuga()
    vault(); gulls()
    items_misc()
    decor(); blockers()
    lights_and_sound()
    if os.environ.get('DEBUG_TRIG'):                 # bot-test probes: AddScore lines in games.log (2 = quarterdeck, 3 = nest)
        for (mn, mx, sc, nm) in (((SX - 480, SY - 70, L.QD_Z + 2), (SX - 370, SY + 70, L.QD_Z + 60), 2, 'dbg_qd'),
                                 ((SX - 100, SY - 100, L.NEST_Z + 2), (SX + 100, SY + 30, L.NEST_Z + 60), 3, 'dbg_nest'),
                                 ((SX - 140, SY - 128, L.WAIST_Z + 2), (SX - 100, SY + 128, L.WAIST_Z + 50), 4, 'dbg_foot'),
                                 ((SX - 280, SY - 128, L.WAIST_Z + 60), (SX - 240, SY + 128, L.WAIST_Z + 130), 5, 'dbg_mid'),
                                 ((SX - 120, SY - 60, L.WAIST_Z + 2), (SX + 60, SY + 60, L.WAIST_Z + 50), 6, 'dbg_waist'),
                                 ((SX - 570, SY - 60, 1), (SX + 300, SY + 60, 60), 7, 'dbg_hold')):
            M.ent('target_score', (round((mn[0] + mx[0]) / 2), round((mn[1] + mx[1]) / 2), round(mx[2] + 40)), targetname=nm, count=sc)
            M.ent('trigger_multiple', brushes=[box(mn, mx, TRIG)], target=nm, wait=3)
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (0, -1700, 700), angles='12 90 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padpirate/build_pirate.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
