#!/usr/bin/env python3
"""Tlaloc's Lagoon - World of Padman FFA map generator (map 'wop_padaztec').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_aztec.py

Writes <OUT>/maps/wop_padaztec.map, textures/padaztec/*, env/padaztec/* (sky), models/padaztec/*,
scripts/padaztec.shader and scripts/wop_padaztec.arena.

An Aztec temple water park in a jungle clearing on a sunny day, human scale (~32u per metre). x east, y north, plaza
z 0, water z -16.

  Great Pyramid   four talud-tablero tiers (every terrace walkable), steep 16u stairs up the south and north faces, Tlaloc's
                  shrine on the summit (walk in; a pad to its roof: Imperius). The Serpent tube starts in a feathered
                  serpent's mouth on the summit and winds down the west side into the lagoon; the Eagle flume runs off
                  the east side into the plunge pool. A tunnel runs through the base past the tomb (Boaster).
  Lagoon          two lakes either side of a causeway, the Sun Stone on the island, a geyser pad from the island to the
                  summit, 16u steps and a beach out of the water, Splasher on the bottom of the west lake.
  Cenote          a sinkhole with a stair spiralling down the wall to the water, a serpent spout, Pumper on the bottom.
                  SECRET: the serpent mouth deep under water -> Moctezuma's treasure (sealed, under the world).
  Jaguar temple   platform, stair, walk-in shrine with jaguars, pad to the roof (Balloony).
  Plunge pool     the flume's splash pool, steps out, Floater on the bottom.
  Tlaloc's head   giant stone head of the rain god pouring water into a splash pool; a pad onto its crown (Betty).
  Eagle hall      colonnade of serpent columns behind the pyramid, stair to the roof.
  Ball court      tlachtli with sloped benches, stone rings, stairs onto both walls.
  Cantina         walk-in snack bar (Bubble G), stair to the roof terrace with palapa parasols.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import az_textures as TX
import azlib
import az_shapes as SH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padaztec'
T = lambda n: 'padaztec/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns'); SLICK = T('slide_clip')

for k, v in {'pavers': (1.0, 1.0), 'red_path': (0.5, 0.5), 'grass': (1.0, 1.0), 'bank': (1.0, 1.0), 'sand': (0.5, 0.5), 'ashlar': (0.5, 0.5),
             'ashlar_moss': (0.5, 0.5), 'ashlar_red': (0.5, 0.5), 'fret': (0.5, 0.5), 'fret_jade': (0.5, 0.5), 'glyph_wall': (0.5, 0.5),
             'stucco': (1.0, 1.0), 'stucco_red': (1.0, 1.0), 'stucco_turq': (1.0, 1.0), 'painted_wall': (0.5, 0.5), 'turq_mosaic': (0.5, 0.5),
             'pool_tile': (0.5, 0.5), 'pool_band': (0.5, 0.5), 'coping': (0.5, 0.5), 'cave_rock': (1.0, 1.0), 'wood': (0.5, 0.5), 'planks': (0.5, 0.5),
             'gold_floor': (0.5, 0.5), 'water': (1.0, 1.0), 'water_deep': (1.0, 1.0), 'obsidian': (0.5, 0.5), 'sky': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '6', '_color': '1 0.95 0.85', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
KEEP_OUT = []          # (x, y, r) circles decoration must keep clear of
NOGO = []              # rects (x0, y0, x1, y1) where nothing stands on the plaza (pools, buildings)


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
    path, sc, zo = azlib.PLACE[name]
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
    """sun-disc pad (r 34) + trigger_push + target_position (the apex, t_up/(t_up+t_down) of the way to `land`)"""
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


def ring_seg(cx, cy, a0, a1, r0, r1, z0, z1, tex):
    pts = []
    for a in (a0, a1):
        for r in (r0, r1):
            px, py = L.ang_pt(cx, cy, r, a)
            pts += [(px, py, z0), (px, py, z1)]
    return hull(pts, tex, round_pts=False)


def face_pts(b, f, V=None):
    V = b.verts() if V is None else V
    on = V[np.abs(V @ np.array(f.n) - f.d) < 0.5]
    return on if len(on) else V


def texby(b, fn):
    """fn(sample points on the face, normal) -> texture"""
    V = b.verts()
    if len(V) < 4: return None
    for f in b.faces:
        on = face_pts(b, f, V); c = on.mean(0)
        smp = [c] + [c + (p - c) * 0.85 for p in on]
        f.tex = fn(smp, np.array(f.n)); f.sc = wopmap.default_scale(f.tex)
    return b


def clipped(brushes, tex=WCLIP):
    """retexture shape brushes (az_shapes) as collision and add them"""
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
    """nudge items / weapons / spawns that ended up inside a solid or clip brush to the nearest free spot (same height)"""
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
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padaztec/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_aztec.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


# =================================================================================================== sky hull, ground, banks
LAG_TILE = (L.LAG[0] - 32, L.LAG[1] - 32, L.LAG[2] + 32, L.LAG[3] + 32)
PP_TILE = (L.POOL_P[0] - 32, L.POOL_P[1] - 32, L.POOL_P[2] + 32, L.POOL_P[3] + 32)
HP_TILE = (L.HEAD_POOL[0] - 32, L.HEAD_POOL[1] - 32, L.HEAD_POOL[2] + 32, L.HEAD_POOL[3] + 32)
TILES = [LAG_TILE, PP_TILE, HP_TILE, L.CEN_TILE]
# floor zones (later entries win): plaza pavers by default
ZONES = [((-2304, -2048, -1280, -1056), 'grass'), ((-2304, 1088, -1100, 2048), 'grass'), ((1100, 1088, 2304, 2048), 'grass'),
         ((1100, -2048, 2304, -1000), 'grass'), ((-2304, -1056, -1280, 1088), 'grass'),
         ((-112, -448, 112, 0), 'red_path'), ((-112, 1408, 112, 1600), 'red_path'), ((704, 560, 1088, 848), 'red_path'),
         ((-1100, 560, -704, 848), 'red_path'), ((-2048, -1344, -1504, -1100), 'pavers'), ((1300, -1100, 2240, -1000), 'red_path')]


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
    """plaza slab (detail) with zone textures; pool tiles are built by their own functions"""
    X1, Y1 = L.HX, L.HY
    cuts = list(TILES) + [z[0] for z in ZONES]
    for r in sub_rects((-X1, -Y1, X1, Y1), cuts):
        A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T('pavers'), 'side': CAULK, 'bot': CAULK}))
    for i, (zr, tex) in enumerate(ZONES):
        later = [z[0] for z in ZONES[i + 1:]]
        for r in sub_rects(zr, later + list(TILES)):
            A(box((r[0], r[1], L.SLAB_BOT), (r[2], r[3], 0), {'top': T(tex), 'side': CAULK, 'bot': CAULK}))


def banks():
    """jungle banks round the clearing: a slope from the plaza edge up to BANK_H, a flat jungle shelf to the sky hull,
    player clip from the bank foot up to the sky (nobody gets out); trees and ruins on the shelf"""
    H = L.SKY; X1, Y1 = L.HX, L.HY; bw, bh = L.BANK_W, L.BANK_H
    bt = {'top': T('bank'), 'side': T('bank'), 'bot': CAULK}
    # shelf (flat jungle floor) beyond the slope
    for r in sub_rects((H['x0'], H['y0'], H['x1'], H['y1']), [(-X1 - bw, -Y1 - bw, X1 + bw, Y1 + bw)]):
        A(box((r[0], r[1], H['z0']), (r[2], r[3], bh), {'top': T('bank'), 'side': CAULK, 'bot': CAULK}))
    # four slopes + corner pieces (mitred)
    for s in (-1, 1):
        y_in, y_out = s * Y1, s * (Y1 + bw)
        pts = [(x, y_in, z) for x in (-X1, X1) for z in (H['z0'], 0)] + [(x, y_out, z) for x in (-X1 - bw, X1 + bw) for z in (H['z0'], bh)]
        A(hull(pts, bt, round_pts=False))
        x_in, x_out = s * X1, s * (X1 + bw)
        pts = [(x_in, y, z) for y in (-Y1, Y1) for z in (H['z0'], 0)] + [(x_out, y, z) for y in (-Y1 - bw, Y1 + bw) for z in (H['z0'], bh)]
        A(hull(pts, bt, round_pts=False))
    # player clip: a wall at the bank foot up to the sky
    for s in (-1, 1):
        A(box((-X1, s * Y1 - (16 if s > 0 else 0), 0), (X1, s * Y1 + (0 if s > 0 else 16), H['z1']), CLIP))
        A(box((s * X1 - (16 if s > 0 else 0), -Y1 + 16, 0), (s * X1 + (0 if s > 0 else 16), Y1 - 16, H['z1']), CLIP))
    # the jungle: catalog trees, custom palms and bushes on the shelf, ruined walls and stelae on the slopes
    rng = np.random.default_rng(42)
    k = 0
    for side in range(4):
        n = 14 if side % 2 == 0 else 12
        for i in range(n):
            t = (i + rng.uniform(0.2, 0.8)) / n
            off = rng.uniform(bw + 40, bw + 420)
            if side == 0: x, y = -X1 + 2 * X1 * t, -Y1 - off
            elif side == 1: x, y = X1 + off, -Y1 + 2 * Y1 * t
            elif side == 2: x, y = -X1 + 2 * X1 * t, Y1 + off
            else: x, y = -X1 - off, -Y1 + 2 * Y1 * t
            if abs(x) > H['x1'] - 240 or abs(y) > H['y1'] - 240: continue
            kind = k % 4; k += 1
            if kind == 0: mdl_c('pad_ddmix/trashcan/tree_summer.md3', x, y, bh, rng.uniform(0.8, 1.1), rng.uniform(0, 360), spawnflags=0)
            elif kind == 1: custom(['palm_a', 'palm_b', 'palm_c'][i % 3], x, y, bh, rng.uniform(0, 360), lit=False)
            elif kind == 2: mdl_c('pad_ddmix/trashcan/tree_spring.md3', x, y, bh, rng.uniform(0.7, 0.95), rng.uniform(0, 360), spawnflags=0)
            else: mdl_c('pad_ddmix/plants/fern.md3', x, y, bh, rng.uniform(0.35, 0.5), rng.uniform(0, 360))
    # bushes and palms along the bank top edge
    for side in range(4):
        for i in range(9):
            t = (i + 0.5) / 9
            off = bw + 60
            if side == 0: x, y = -X1 + 2 * X1 * t, -Y1 - off
            elif side == 1: x, y = X1 + off, -Y1 + 2 * Y1 * t
            elif side == 2: x, y = -X1 + 2 * X1 * t, Y1 + off
            else: x, y = -X1 - off, -Y1 + 2 * Y1 * t
            if i % 2: custom('monstera_b', x, y, bh, 40 * i, lit=False)
            else: mdl_c('pad_ddmix/trashcan/bush.md3', x, y, bh, 0.9, 30 * i)


# =================================================================================================== pool helpers
def pool_tex(lo_top=0.0):
    def f(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(max(p[2] for p in smp) - 0) < 0.5: return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('pool_tile')
        return T('pool_band')
    return f


def water_faces(b, deep=False):
    wt = T('water_deep' if deep else 'water')
    for f in b.faces:
        top = f.n[2] > 0.99 and abs(max(p[2] for p in face_pts(b, f)) - L.WATER) < 0.5
        f.tex = wt if top else wt + '_nodraw'
        f.sc = (1, 1)
    return b


def edge_faces_caulk(b, tile):
    """faces lying on the tile's outer boundary (against the neighbouring slab) are hidden"""
    if b is None: return []
    V = b.verts()
    for f in b.faces:
        if abs(f.n[2]) > 0.01: continue
        on = face_pts(b, f, V)
        if abs(f.n[0]) > 0.99 and (np.all(np.abs(on[:, 0] - tile[0]) < 0.5) or np.all(np.abs(on[:, 0] - tile[2]) < 0.5)): f.tex = CAULK
        if abs(f.n[1]) > 0.99 and (np.all(np.abs(on[:, 1] - tile[1]) < 0.5) or np.all(np.abs(on[:, 1] - tile[3]) < 0.5)): f.tex = CAULK
    return b


# =================================================================================================== great pyramid
def pyramid():
    cx, cy = L.PC
    custom('pyramid', cx, cy, 0, _lightmapscale=1.0)
    clipped(SH.pyramid_tiers() + SH.pyramid_steps())
    NOGO.append((cx - L.H0 - 80, cy - L.H0 - 160, cx + L.H0 + 80, cy + L.H0 + 160))
    # serpent heads at the foot of both stairs
    for side in (-1, 1):
        yb = cy + side * (L.H0 + 2)
        for sx in (-1, 1):
            x = cx + sx * (L.STAIR_HW + 56)
            ang = 270 if side < 0 else 90
            furn('serpent_head', x, yb, 0, ang, [((0, -44, 0), (156, 44, 92))])
        route(f'pyr_stair_{"s" if side < 0 else "n"}', (cx, cy + side * (L.H0 + 150), 0), (cx, cy + side * (L.TOP_HALF - 60), L.TOP_Z))
    # terrace access from the stairs (a terrace on each tier, both sides of the south stair)
    for k in range(L.NT - 1):
        zt = (k + 1) * L.TIER_H
        yk = cy - L.tier_half(k) + 48
        route(f'terrace_{k}', (cx - 300, yk, zt), (cx, yk, zt + 16))
    # tunnel + tomb: Boaster in the tomb, torches
    route('tunnel_w', (cx - L.H0 - 140, cy, 0), (cx, cy - 120, 0))
    route('tunnel_e', (cx + L.H0 + 140, cy, 0), (cx, cy + 120, 0))
    weapon('bubbleg', cx, cy + 100, 0, 'green')
    custom('chacmool', cx, cy - 60, 0, 0)
    lbox(cx, cy - 60, 0, 0, (-86, -38, 0), (86, 38, 40))
    for (x, y) in ((cx - 150, cy - 150), (cx + 150, cy - 150), (cx - 150, cy + 150), (cx + 150, cy + 150)):
        custom('brazier', x, y, 0)
        A(cyl(x, y, 26, 0, 70, WCLIP, 8))
        light(x, y, 140, 220, '1 0.65 0.3')
    for x in (-560, -320, 320, 560):
        light(cx + x, cy, 90, 120, '1 0.7 0.4')
    item('ammo_bubbleg', cx - 450, cy + 30, 0); item('item_armor_shard', cx + 450, cy - 30, 0)
    speaker(cx, cy, 120, 'ambient/droplets_echoing', volume=0.5)
    speaker(cx - 100, cy - 150, 90, 'ambient/fire_crackling', volume=0.4)
    trigger_sound((cx - 64, cy + 20, 2), (cx + 64, cy + 120, 100), 'sound/world/misc/strange_signal.ogg', 'tomb_sig', 20, volume=0.4)
    # the summit: shrine, idol, chacmool, braziers
    custom('shrine', cx, cy, L.TOP_Z)
    clipped(SH.shrine())
    custom('idol', cx, L.SHRINE[3] - 80, L.TOP_Z, 270)
    lbox(cx, L.SHRINE[3] - 80, L.TOP_Z, 270, (-46, -40, 0), (46, 40, 200))
    light(cx, cy + 160, L.TOP_Z + 140, 260, '0.8 0.9 1')
    for sx in (-1, 1):
        x = cx + sx * 140
        custom('brazier_big', x, L.SHRINE[1] - 70, L.TOP_Z)
        A(cyl(x, L.SHRINE[1] - 70, 42, L.TOP_Z, L.TOP_Z + 106, WCLIP, 8))
        light(x, L.SHRINE[1] - 70, L.TOP_Z + 190, 200, '1 0.65 0.3')
        speaker(x, L.SHRINE[1] - 70, L.TOP_Z + 130, 'ambient/fire_crackling', volume=0.5)
    route('shrine_door', (cx, cy - 200, L.TOP_Z), (cx, cy + 20, L.TOP_Z))
    item('item_armor_padshield', cx + 60, cy + 30, L.TOP_Z)
    item('ammo_imperius', cx + 100, cy + 220, L.TOP_Z)
    # pad from the summit onto the shrine roof (Imperius)
    jumppad(cx + 230, cy - 200, L.TOP_Z, (cx + 60, cy + 90, L.SHRINE_ROOF), L.SHRINE_ROOF + 120, 'pad_shrine')
    weapon('imperius', cx - 60, cy + 100, L.SHRINE_ROOF, 'purple')
    trigger_sound((L.SHRINE[0], L.SHRINE[1], L.SHRINE_ROOF + 2), (L.SHRINE[2], L.SHRINE[3], L.SHRINE_ROOF + 80),
                  'sound/world/human/applause.ogg', 'roof_cheer', 15, volume=0.6)
    # terrace items
    tb = [L.tier_half(k) - 76 for k in range(L.NT)]           # centre line of each terrace band
    item('ammo_betty', cx - tb[0], cy + 300, L.TIER_H); item('ammo_pumper', cx + tb[0], cy - 300, L.TIER_H)
    item('item_armor_shard', cx - tb[1], cy - 260, 2 * L.TIER_H); item('ammo_splasher', cx + tb[1], cy + 260, 2 * L.TIER_H)
    item('item_visionless', cx + 250, cy + tb[2], 3 * L.TIER_H)
    item('ammo_balloony', cx - tb[2], cy - 200, 3 * L.TIER_H)
    for (x, y, z, a) in ((cx + 250, cy - 250, L.TOP_Z, 135), (cx - 250, cy - 250, L.TOP_Z, 45), (cx - tb[0], cy + 200, L.TIER_H, 0)):
        spawn(x, y, z, a)


# =================================================================================================== lagoon
def lagoon():
    cut = L.LAG_CUT; sb = L.SHALLOW_BAND
    oct0 = L.octagon(L.LAG, cut); oct1 = L.octagon(L.LAG, cut, sb); oct2 = L.octagon(L.LAG, cut, sb + L.SLOPE_W)
    c1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, 64)], CAULK, round_pts=False)
    c2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, 64)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    ix, iy = L.ISLAND
    keep = [cyl(ix, iy, L.ISLAND_R, -600, 80, CAULK, 24),
            box((ix - L.CAUSE_HW, iy, -600), (ix + L.CAUSE_HW, L.LAG[3] + 64, 80), CAULK),
            box((ix - L.CAUSE_HW, L.LAG[1] - 64, -600), (ix + L.CAUSE_HW, iy, 80), CAULK)] + \
           [cyl(x, y, r, -600, 80, CAULK, 16) for (x, y, r) in L.ISLETS]
    cutters = []
    for c in (c1, c2):
        cutters += carve(c, keep)
    tile = box((LAG_TILE[0], LAG_TILE[1], L.SLAB_BOT), (LAG_TILE[2], LAG_TILE[3], 0), CAULK)

    def tx(smp, n):
        c = smp[0]
        if n[2] > 0.99 and abs(c[2]) < 0.5:
            if math.hypot(c[0] - ix, c[1] - iy) < L.ISLAND_R + 1: return T('pavers')
            if any(math.hypot(c[0] - x, c[1] - y) < r + 1 for (x, y, r) in L.ISLETS): return T('grass')
            if abs(c[0] - ix) < L.CAUSE_HW + 1 and L.LAG[1] - 40 < c[1] < L.LAG[3] + 40: return T('red_path')
            return T('coping')
        if n[2] < -0.7: return CAULK
        if n[2] > 0.3: return T('pool_tile')
        if math.hypot(c[0] - ix, c[1] - iy) < L.ISLAND_R + 2 or abs(abs(c[0] - ix) - L.CAUSE_HW) < 2: return T('ashlar_moss')
        if any(math.hypot(c[0] - x, c[1] - y) < r + 2 for (x, y, r) in L.ISLETS): return T('cave_rock')
        return T('pool_band')
    for b in carve(tile, cutters):
        A(edge_faces_caulk(texby(b, tx), LAG_TILE))
    # steps (16u) out of the shallow ring, and the beach ramp on the east lake
    solids = []
    for (x0, y0, x1, y1, d) in L.LAG_STEPS:
        n = 3
        for j in range(n):
            # rising toward the pool edge: step j = 0 next to the edge is the highest (top -16)
            if d == 's': r = (x0, y0 + (y1 - y0) * j / n, x1, y0 + (y1 - y0) * (j + 1) / n); zt = L.SHALLOW + 16 * (n - j)
            elif d == 'w': r = (x0 + (x1 - x0) * j / n, y0, x0 + (x1 - x0) * (j + 1) / n, y1); zt = L.SHALLOW + 16 * (n - j)
            elif d == 'e': r = (x1 - (x1 - x0) * (j + 1) / n, y0, x1 - (x1 - x0) * j / n, y1); zt = L.SHALLOW + 16 * (n - j)
            b = box((round(r[0]), round(r[1]), L.SHALLOW), (round(r[2]), round(r[3]), zt), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
            A(b); solids.append(b)
    bx0, by0, bx1, by1 = L.BEACH
    beach = hull([(x, by1, L.SHALLOW) for x in (bx0, bx1)] + [(x, by1, 0) for x in (bx0, bx1)] + [(x, by0, L.SHALLOW) for x in (bx0, bx1)],
                 {'top': T('sand'), 'side': T('pool_band'), 'bot': CAULK}, round_pts=False)
    A(beach); solids.append(beach)
    # water: the same shapes up to the surface, minus the island, causeways, steps and beach
    W_ = L.WATER
    w1 = hull([(x, y, z) for (x, y) in oct0 for z in (L.SHALLOW, W_)], CAULK, round_pts=False)
    w2 = hull([(x, y, z) for (x, y) in oct1 for z in (L.SHALLOW, W_)] + [(x, y, L.DEEP) for (x, y) in oct2], CAULK, round_pts=False)
    oct1_box = hull([(x, y, z) for (x, y) in oct1 for z in (L.DEEP - 10, W_ + 10)], CAULK, round_pts=False)
    w1p = [pp for w in carve(w1, keep) for pp in carve(w, solids)]
    w1p = [pp for w in w1p for pp in carve(w, [oct1_box])]
    w2p = [pp for w in carve(w2, keep) for pp in carve(w, solids)]
    for pc in w1p + w2p:
        A(water_faces(pc))
    NOGO.append(tuple(L.LAG))
    # island dais + the Sun Stone (cover in the middle of the lagoon)
    A(cyl(ix, iy, L.ISLAND_R - 40, 0, 16, {'top': T('turq_mosaic'), 'side': T('fret_jade'), 'bot': CAULK}, 24))
    custom('sunstone', ix, iy, 16)
    A(box((ix - L.SUN_R * 0.8, iy - 60, 16), (ix + L.SUN_R * 0.8, iy + 60, 56), WCLIP))
    A(box((ix - L.SUN_R + 10, iy - 22, 56), (ix + L.SUN_R - 10, iy + 22, 64 + L.SUN_R * 2 - 20), WCLIP))
    KEEP_OUT.append((ix, iy, L.ISLAND_R))
    # geyser pad from the island's north side to the summit
    jumppad(ix, iy + 170, 16, (L.PC[0], L.PC[1] - 160, L.TOP_Z), L.TOP_Z + 260, 'pad_geyser')
    # contents: Splasher on the bottom of the west lake, ammo, shards, the climber on the island
    weapon('splasher', -640, -1150, L.DEEP, 'orange')
    item('ammo_splasher', 640, -1150, L.DEEP); item('ammo_pumper', -900, -1700, L.SHALLOW); item('item_armor_shard', 900, -620, L.SHALLOW)
    item('item_climber', ix - 160, iy - 120, 16); item('ammo_bubbleg', ix + 160, iy - 120, 16)
    route('causeway_n', (0, L.LAG[3] + 100, 0), (0, iy + 120, 16))
    route('causeway_s', (0, L.LAG[1] - 100, 0), (0, iy - 120, 16))
    for (x, y) in ((-640, -1150), (640, -1150), (-800, -800), (800, -1500)):
        light(x, y, L.DEEP + 60, 160, '0.5 0.9 1')
    speaker(-600, -1100, 0, 'ambient/water_rippling', volume=0.5); speaker(600, -1100, 0, 'ambient/water_rippling', volume=0.5)
    # floating fun: rubber ducks on the island steps, a beach umbrella pair on the beach
    mdl_c('pad_ducks/pad_duck.md3', ix + 120, iy + 150, 16, 0.35, 200)
    mdl_c('pad_ducks/pad_duck.md3', ix - 140, iy + 140, 16, 0.25, 320)
    for (x, y, z, a) in ((-1100, -2000 + 140, 0, 90), (1100, -2000 + 140, 0, 90), (ix + 120, iy - 200, 16, 90)):
        spawn(x, y, z, a)


# =================================================================================================== slides
def slide_brushes(pts, hw, wall_h, roof=None, floor_t=16, wall_t=8):
    """slick floor + weapon-clip walls (+ roof) along a slide centre line [(x, y, z_floor)] (mitred segments)"""
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


def on_ground_free(x, y, m=40):
    """open plaza (pillar spots under the slides)"""
    if abs(x) > L.HX - m or abs(y) > L.HY - m: return False
    for t in TILES:
        if in_rect(x, y, t, m): return False
    cx, cy = L.PC
    if abs(x - cx) < L.H0 + m and abs(y - cy) < L.H0 + 80 + m: return False
    j = L.JAG; hx, hy, H = L.JAG_PLAT
    if in_rect(x, y, (j[0] - hx, j[1] - hy, j[0] + hx + 260, j[1] + hy), m): return False
    return True


def supports_for(path, every=5, zmin=110):
    out = []
    for i in range(2, len(path) - 2, every):
        x, y, z = path[i]
        if z >= zmin and on_ground_free(x, y): out.append((x, y, z))
    return out


def slides_place():
    import az_models as AM
    sp = L.serpent_path(); fp = L.flume_path()
    custom('serpent_tube', 0, 0, 0)
    slide_brushes(sp[1:], 40, 96, roof=True)
    for (x, y, z) in AM.SUPPORTS['tube']:
        zt = z + L.TUBE_ZC - L.TUBE_R + 6
        A(box((round(x) - 20, round(y) - 20, 0), (round(x) + 20, round(y) + 20, round(zt) - 28), WCLIP))
        KEEP_OUT.append((x, y, 60))
    for (x, y, z) in sp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    # serpent head round the tube mouth on the summit (faces east, players walk in going west)
    x0, y0, z0 = sp[1]
    x0 = -L.TOP_HALF
    custom('tube_head', x0, y0, z0)
    R = L.TUBE_R
    A(box((x0 + 2, y0 - R - 34, z0), (x0 + 150, y0 - 48, z0 + L.TUBE_ZC + R + 40), WCLIP))
    A(box((x0 + 2, y0 + 48, z0), (x0 + 150, y0 + R + 34, z0 + L.TUBE_ZC + R + 40), WCLIP))
    A(box((x0 + 2, y0 - 48, z0 + L.TUBE_ZC + R - 6), (x0 + 150, y0 + 48, z0 + L.TUBE_ZC + R + 40), WCLIP))
    route('tube_mouth', (x0 + 260, y0, z0), (x0 + 60, y0, z0))
    custom('eagle_flume', 0, 0, 0)
    slide_brushes(fp[1:], 46, 48)
    for (x, y, z) in AM.SUPPORTS['flume']:
        A(box((round(x) - 16, round(y) - 16, 0), (round(x) + 16, round(y) + 16, round(z) - 40), WCLIP))
        KEEP_OUT.append((x, y, 60))
    for (x, y, z) in fp[1:]:
        if z > 30: KEEP_OUT.append((x, y, 90))
    fx, fy, fz = fp[1]
    custom('eagle_head', fx + 10, fy, fz)
    for s in (-1, 1):
        A(box((fx - 10, fy + s * 74 - 14, fz), (fx + 30, fy + s * 74 + 14, fz + 150), WCLIP))
    speaker(sp[-1][0], sp[-1][1], 40, 'ambient/water_shower', volume=0.4)
    speaker(fp[-1][0], fp[-1][1], 40, 'ambient/water_shower', volume=0.4)
    speaker(sp[len(sp) // 2][0], sp[len(sp) // 2][1], sp[len(sp) // 2][2] + 60, 'ambient/water_flowing', volume=0.3)


# =================================================================================================== plunge pool (east)
def plunge_pool():
    x0, y0, x1, y1 = L.POOL_P
    fz = L.POOL_P_FLOOR
    tile = box((PP_TILE[0], PP_TILE[1], L.SLAB_BOT), (PP_TILE[2], PP_TILE[3], 0), CAULK)
    for b in carve(tile, [box((x0, y0, fz), (x1, y1, 32), CAULK)]):
        A(edge_faces_caulk(texby(b, pool_tex()), PP_TILE))
    steps = []
    n = (-L.WATER - fz) // 16 + 0                 # tops -16 .. down to the floor
    n = 18
    for k in range(n):
        b = box((x0, y0 + 24 * k, fz), (x1, y0 + 24 * (k + 1), -16 - 16 * k), {'top': T('pool_tile'), 'side': T('pool_band'), 'bot': CAULK})
        steps.append(b); A(b)
    for b in carve(box((x0, y0, fz), (x1, y1, L.WATER), CAULK), steps):
        A(water_faces(b, True))
    NOGO.append(tuple(PP_TILE))
    item('holdable_floater', (x0 + x1) / 2, y1 - 120, fz)
    item('ammo_splasher', x0 + 120, y1 - 200, fz)
    item('ammo_imperius', x1 - 100, y0 + 100, -16 - 16 * 4)
    for (x, y) in ((1300, 900), (1550, 950)):
        light(x, y, fz + 80, 200, '0.5 0.9 1')
    speaker((x0 + x1) / 2, (y0 + y1) / 2, 0, 'ambient/water_bubbling', volume=0.4)
    custom('lifeguard', x1 + 120, y0 + 40, 0, 180)
    A(box((x1 + 90, y0 + 10, 0), (x1 + 150, y0 + 70, 120), WCLIP))
    KEEP_OUT.append((x1 + 120, y0 + 40, 80))
    route('plunge_steps', ((x0 + x1) / 2, y0 + 24 * 3 + 12, -64), ((x0 + x1) / 2, y0 - 100, 0))


# =================================================================================================== cenote (north-west)
def cenote():
    cx, cy = L.CEN
    R = L.CEN_R; n = 32
    tx0, ty0, tx1, ty1 = L.CEN_TILE
    tile = box((tx0, ty0, L.CEN_SLAB), (tx1, ty1, 0), CAULK)
    shaft = cyl(cx, cy, R, L.CEN_FLOOR, 64, CAULK, n, phase=0)
    # secret tunnel into the wall (deep under water)
    a = math.radians(L.CEN_SECRET_A); d = np.array([math.cos(a), math.sin(a)]); s_ = np.array([-d[1], d[0]])
    tz = L.CEN_SECRET_Z
    tun_pts = []
    for r in (R - 40, R + 130):
        for w in (-48, 48):
            p = np.array([cx, cy]) + d * r + s_ * w
            tun_pts += [(p[0], p[1], tz), (p[0], p[1], tz + 96)]
    tunnel = hull(tun_pts, CAULK, round_pts=False)
    rin = R * math.cos(math.pi / n) - 1

    def tx(smp, n_):
        c = smp[0]
        if n_[2] > 0.99 and abs(c[2]) < 0.5:
            rr = math.hypot(c[0] - cx, c[1] - cy)
            return T('coping') if rr < R + 64 else T('grass')
        if n_[2] < -0.7: return T('cave_rock') if c[2] > L.CEN_FLOOR else CAULK
        if n_[2] > 0.3: return T('sand')
        return T('cave_rock')
    for b in carve(tile, [shaft, tunnel]):
        A(edge_faces_caulk(texby(b, tx), L.CEN_TILE))
    # spiral stair down the wall (ledges 64 thick), the last steps under water
    steps = []
    for j in range(L.CEN_STAIR_N):
        a0, a1, zt = L.cen_step(j)
        b = ring_seg(cx, cy, a0, a1, rin - L.CEN_STAIR_W, rin, zt - 64, zt, {'top': T('coping'), 'side': T('cave_rock'), 'bot': T('cave_rock')})
        A(b); steps.append(b)
    a_top = L.CEN_STAIR_A0
    route('cenote_stair', (cx + (R + 120) * math.cos(math.radians(a_top - 8)), cy + (R + 120) * math.sin(math.radians(a_top - 8)), 0),
          (cx + (rin - 52) * math.cos(math.radians(L.cen_step(14)[0] + 5)), cy + (rin - 52) * math.sin(math.radians(L.cen_step(14)[0] + 5)), L.cen_step(14)[2]))
    # rim wall (low, gap at the stair top)
    for k in range(48):
        a0, a1 = 360 * k / 48, 360 * (k + 1) / 48
        am = (a0 + a1) / 2
        if abs(((am - (a_top - 6) + 180) % 360) - 180) < 16: continue
        A(ring_seg(cx, cy, a0, a1, R + 8, R + 40, 0, 28, {'top': T('coping'), 'side': T('ashlar_moss'), 'bot': CAULK}))
    sill = ring_seg(cx, cy, L.CEN_SECRET_A - 15, L.CEN_SECRET_A + 15, R - 90, rin, tz - 40, tz, {'top': T('cave_rock'), 'side': T('cave_rock'), 'bot': T('cave_rock')})
    A(sill); steps.append(sill)
    # water: shaft below the surface minus the steps, plus the tunnel
    for b in carve(cyl(cx, cy, R, L.CEN_FLOOR, L.CEN_WATER, CAULK, n, phase=0), steps):
        for f in b.faces:
            top = f.n[2] > 0.99 and abs(max(p[2] for p in face_pts(b, f)) - L.CEN_WATER) < 0.5
            f.tex = T('water_deep') if top else T('water_deep_nodraw'); f.sc = (1, 1)
        A(b)
    tw = hull([(x, y, z) for (x, y, z0_) in tun_pts[::2] for z in (tz, tz + 96)], CAULK, round_pts=False)
    for b in carve(tw, [shaft]):
        for f in b.faces: f.tex = T('water_deep_nodraw'); f.sc = (1, 1)
        A(b)
    # the secret: a serpent mouth framing the tunnel; teleport at the far end
    pm = np.array([cx, cy]) + d * (R - 4)
    pw = np.array([cx, cy]) + d * (R - 18)
    custom('secret_mouth', pw[0], pw[1], tz, (L.CEN_SECRET_A + 180) % 360)
    pe = np.array([cx, cy]) + d * (R + 110)
    M.ent('trigger_teleport', brushes=[hull([(pp[0], pp[1], z) for w in (-32, 32) for r in (R + 70, R + 120)
                                             for pp in [np.array([cx, cy]) + d * r + s_ * w] for z in (tz + 8, tz + 88)], TRIG, round_pts=False)],
          target='treasure_in')
    pf = np.array([cx, cy]) + d * (R - 140)
    trigger_sound((pf[0] - 32, pf[1] - 32, tz + 2), (pf[0] + 32, pf[1] + 32, tz + 90), 'sound/world/misc/secret_found.ogg', 'cen_secret', 30, volume=0.7)
    light(pe[0], pe[1], tz + 48, 160, '0.3 1 0.6')
    # the waterfall spout high on the wall (opposite the stair) and its splash
    a_sp = 110.0
    ps = np.array(L.ang_pt(cx, cy, R - 2, a_sp))
    custom('waterspout', ps[0], ps[1], -120, (a_sp + 180) % 360)
    speaker(ps[0], ps[1], -200, 'ambient/water_falling', volume=0.6)
    custom('cenote_vines', cx, cy, 0, lit=False)
    # weapon + items down in the water and on the steps
    weapon('pumper', cx - 60, cy + 40, L.CEN_FLOOR, 'green')
    item('ammo_pumper', cx + 120, cy - 100, L.CEN_FLOOR)
    s10 = L.cen_step(10); s5 = L.cen_step(5)
    p10 = L.ang_pt(cx, cy, rin - 52, (s10[0] + s10[1]) / 2); p5 = L.ang_pt(cx, cy, rin - 52, (s5[0] + s5[1]) / 2)
    item('ammo_betty', p10[0], p10[1], s10[2]); item('item_armor_shard', p5[0], p5[1], s5[2])
    for z in (-100, -260):
        for k in range(3):
            p = L.ang_pt(cx, cy, R - 80, 120 * k + 30)
            light(p[0], p[1], z, 180, '0.85 1 0.8')
    light(cx, cy, -500, 240, '0.4 0.9 0.9')
    speaker(cx, cy, -300, 'ambient/droplets_echoing', volume=0.5)
    NOGO.append((cx - R - 60, cy - R - 60, cx + R + 60, cy + R + 60))
    spawn(cx + R + 120, cy - 120, 0, 180)


# =================================================================================================== jaguar temple (west)
def jaguar_temple():
    cx, cy = L.JAG
    hx, hy, H = L.JAG_PLAT
    custom('jaguar_temple', cx, cy, 0)
    clipped(SH.jaguar())
    NOGO.append((cx - hx - 30, cy - hy - 30, cx + hx + 280, cy + hy + 30))
    for sy in (-1, 1):
        furn('jaguar', cx + hx + 120, cy + sy * 150, 0, 0, [((-64, -32, 0), (64, 32, 104))])
    route('jag_stair', (cx + hx + 380, cy, 0), (cx + hx - 80, cy, H))
    route('jag_door', (cx + hx - 80, cy, H), (cx, cy, H))
    bx0 = cx + L.JAG_BLD[0]
    custom('idol', bx0 + 80, cy, H, 0, mul=0.8)
    lbox(bx0 + 80, cy, H, 0, (-37, -32, 0), (37, 32, 165))
    light(cx - 20, cy, H + 110, 200, '1 0.75 0.45')
    item('item_armor_padshield', cx + 30, cy - 60, H); item('ammo_balloony', cx + 30, cy + 60, H)
    jumppad(cx + 240, cy - 188, H, (cx + 40, cy - 60, L.JAG_ROOF), L.JAG_ROOF + 150, 'pad_jaguar')
    weapon('balloony', cx - 60, cy + 20, L.JAG_ROOF, 'black')
    item('ammo_splasher', cx - hx + 80, cy - hy + 70, H)
    for sx in (-1, 1):
        custom('brazier', cx + hx - 64, cy + sx * 128, H)
        A(cyl(cx + hx - 64, cy + sx * 128, 26, H, H + 70, WCLIP, 8))
        light(cx + hx - 64, cy + sx * 128, H + 130, 160, '1 0.65 0.3')
    speaker(cx, cy, H + 60, 'animal/cicada_chirp', volume=0.3)
    spawn(cx + hx + 200, cy - 280, 0, 0)
    spawn(cx - 120, cy + 180, H, 0)


# =================================================================================================== cantina (south-west)
def cantina():
    x0, y0, x1, y1 = L.CAN
    Z = L.CAN_H
    custom('cantina', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    clipped(SH.cantina())
    NOGO.append((x0 - 130, y0 - 80, x1 + 140, y1 + 120))
    A(sign_box((x1 + 8, (y0 + y1) / 2 - 128, 170), (x1 + 12, (y0 + y1) / 2 + 128, 234), T('sign_cantina'), 512, 128, back=CAULK, facing='e'))
    weapon('boaster', (x0 + x1) / 2, (y0 + y1) / 2, 0, 'orange')
    item('ammo_bubbleg', x0 + 80, y0 + 80, 0); item('ammo_boaster', x0 + 80, y1 - 80, 0)
    for k in range(4):
        yy = y0 + 160 + k * 60
        custom('stool', x1 + 40, yy, 0, 30 * k)
    light((x0 + x1) / 2, (y0 + y1) / 2, 150, 220, '1 0.85 0.6')
    route('cantina_door', (x0 + 248, y1 + 140, 0), (x0 + 248, y1 - 120, 0))
    route('cantina_stair', (x0 - 56, y0 - 140, 0), (x0 + 100, y1 - 100, Z))
    # roof terrace: palapa parasols, loungers
    for (x, y) in ((x0 + 160, y0 + 140), (x1 - 160, y1 - 160)):
        custom('parasol', x, y, Z)
        A(cyl(x, y, 6, Z, Z + 180, WCLIP, 6))
    custom('lounger_a', x0 + 300, y0 + 120, Z, 0)
    lbox(x0 + 300, y0 + 120, Z, 0, (-34, -14, 0), (34, 14, 14))
    item('holdable_boomies', x1 - 120, y0 + 100, Z); item('ammo_balloony', x0 + 120, y1 - 80, Z)
    jumppad(x1 + 210, y0 + 60, 0, (x1 - 120, y0 + 220, Z), Z + 120, 'pad_cantina')
    speaker((x0 + x1) / 2, (y0 + y1) / 2, 100, 'machine/coffee_maker', volume=0.3)
    spawn(x1 + 240, y1 + 100, 0, 225)


# =================================================================================================== ball court (south-east)
def ballcourt():
    custom('ballcourt', L.BC[0], L.BC[1], 0)
    clipped(SH.ballcourt())
    ax0, ay0, ax1, ay1 = L.BC_ALLEY
    yb = L.BC_BENCH[0]
    NOGO.append((ax0 - L.BC_END - 40, ay0 - yb - L.BC_TOP_W - 100, ax1 + L.BC_END + 40, ay1 + yb + L.BC_TOP_W + 100))
    # ring collision (torus approximated by four small boxes round the hole)
    for s in (-1, 1):
        yw = (ay1 if s > 0 else ay0) + s * yb
        ya, yz = sorted((yw, yw - s * 20))
        for (a0, a1, z0, z1) in ((-40, -22, 120, 180), (22, 40, 120, 180), (-22, 22, 120, 128), (-22, 22, 172, 180)):
            A(box((L.BC[0] + a0, ya, z0), (L.BC[0] + a1, yz, z1), WCLIP))
    custom('rubber_ball', L.BC[0] + 60, L.BC[1] + 10, 0)
    item('item_speedy', L.BC[0], L.BC[1], 0)
    Z = L.BC_WALL_Z
    for s in (-1, 1):
        ytop = (ay1 if s > 0 else ay0) + s * (yb + L.BC_TOP_W / 2)
        route(f'court_wall_{"n" if s > 0 else "s"}', (L.BC[0] - 400, ytop + s * (L.BC_TOP_W / 2 + 40), 0), (L.BC[0] + 200, ytop, Z))
    item('item_armor_padshield', L.BC[0] + 250, ay1 + yb + L.BC_TOP_W / 2, Z)
    item('ammo_betty', L.BC[0] - 250, ay0 - yb - L.BC_TOP_W / 2, Z)
    item('ammo_bubbleg', ax0 - 60, L.BC[1] + 150, 0); item('ammo_boaster', ax1 + 60, L.BC[1] - 150, 0)
    A(sign_box((ax0 - L.BC_END - 32, L.BC[1] - 128, 64), (ax0 - L.BC_END - 28, L.BC[1] + 128, 128), T('sign_court'), 512, 128, back=CAULK, facing='w'))
    station(ax1 + 40, L.BC[1] + 380, 0, 180)
    for (x, y, a) in ((L.BC[0] - 200, L.BC[1], 0), (L.BC[0] + 260, L.BC[1], 180)):
        spawn(x, y, 0, a)
    timer_sound(L.BC[0], L.BC[1], 120, 'misc/toy_squeeze', 'ball_squeak', 30, 15, volume=0.4)


# =================================================================================================== Tlaloc's head (north-east)
def tlaloc_head():
    hx, hy = L.HEAD
    px, py, ph = L.HEAD_PLINTH
    # pool in front
    x0, y0, x1, y1 = L.HEAD_POOL
    tile = box((HP_TILE[0], HP_TILE[1], L.SLAB_BOT), (HP_TILE[2], HP_TILE[3], 0), CAULK)
    for b in carve(tile, [box((x0, y0, L.SHALLOW), (x1, y1, 32), CAULK)]):
        A(edge_faces_caulk(texby(b, pool_tex()), HP_TILE))
    steps = []
    for j in range(3):
        b = box((x0, y0 + 32 * j, L.SHALLOW), (x1, y0 + 32 * (j + 1), -16 - 16 * j), {'top': T('coping'), 'side': T('pool_band'), 'bot': CAULK})
        A(b); steps.append(b)
    for b in carve(box((x0, y0, L.SHALLOW), (x1, y1, L.WATER), CAULK), steps):
        A(water_faces(b))
    NOGO.append(tuple(HP_TILE))
    # plinth (stepped) + head
    A(box((hx - px, hy - py, 0), (hx + px, hy + py, ph), {'top': T('pavers'), 'side': T('fret'), 'bot': CAULK}))
    custom('tlaloc_head', hx, hy, ph)
    A(box((hx - 166, hy - 138, ph), (hx + 166, hy + 138, L.HEAD_TOP - 120), WCLIP))
    A(box((hx - 182, hy - 154, L.HEAD_TOP - 120), (hx + 182, hy + 154, L.HEAD_TOP - 56), WCLIP))
    A(box((hx - 170, hy - 142, L.HEAD_TOP - 56), (hx + 170, hy + 142, L.HEAD_TOP), WCLIP))
    NOGO.append((hx - px - 60, hy - py - 60, hx + px + 60, hy + py + 120))
    jumppad(hx, hy + py + 150, 0, (hx, hy + 20, L.HEAD_TOP), L.HEAD_TOP + 150, 'pad_head')
    weapon('betty', hx, hy - 30, L.HEAD_TOP, 'purple')
    item('ammo_betty', hx + 200, y0 + 100, L.SHALLOW); item('ammo_imperius', hx - 140, hy + 80, L.HEAD_TOP)
    speaker(hx, y1 - 40, 20, 'ambient/water_falling', volume=0.6)
    light(hx, hy - 260, 300, 260, '1 0.95 0.85')
    route('head_pool', ((x0 + x1) / 2, y0 + 80, -48), ((x0 + x1) / 2, y0 - 120, 0))
    spawn(hx + 380, hy + 100, 0, 200)


# =================================================================================================== hall of the eagle warriors (north)
def hall():
    x0, y0, x1, y1 = L.HALL
    custom('hall', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    clipped(SH.hall())
    for (x, y) in SH.hall_columns():
        custom('serpent_col', x, y, 0)
        A(cyl(x, y, 26, 57, L.HALL_Z - 24, WCLIP, 12))
        lbox(x, y, 0, 270, (0, -36, 0), (118, 36, 56))
    NOGO.append((x0 - 40, y0 - 80, x1 + 140, y1))
    route('hall_stair', (x1 + 48, y0 - 80, 0), (x1 - 100, (y0 + y1) / 2, L.HALL_Z))
    item('item_jumper', 0, (y0 + y1) / 2, L.HALL_Z); item('ammo_pumper', -500, y0 + 200, L.HALL_Z); item('ammo_imperius', 500, y0 + 160, L.HALL_Z)
    item('ammo_boaster', -300, y1 - 160, 0); item('ammo_balloony', 300, y1 - 160, 0); item('item_armor_shard', 0, y1 - 150, 0)
    station(-480, y1 - 170, 0, 270)
    for x in (-500, 0, 500):
        light(x, (y0 + y1) / 2 + 40, 150, 160, '1 0.85 0.65')
    for (x, y, z, a) in ((-200, y0 + 100, 0, 270), (400, y0 + 220, L.HALL_Z, 180)):
        spawn(x, y, z, a)


# =================================================================================================== secret: Moctezuma's treasure
def treasure():
    F = L.TREASURE
    x0, x1, y0, y1, z0, z1 = F['x0'], F['x1'], F['y0'], F['y1'], F['z0'], F['z1']
    W = 32
    wl = {'side': T('glyph_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('gold_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('stucco_turq'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x0, y1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((x1, y0 - W, z0), (x1 + W, y1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((x0, y0 - W, z0), (x1, y0, z1), dict(wl, s=CAULK), detail=False))
    A(box((x0, y1, z0), (x1, y1 + W, z1), dict(wl, n=CAULK), detail=False))
    for (x, y, nm) in ((-450, 300, 'gold_heap'), (450, 300, 'gold_heap'), (0, 340, 'gold_heap_s'), (-520, -200, 'gold_heap_s'), (520, -200, 'gold_heap_s')):
        custom(nm, x, y, z0)
        rr = 74 if nm == 'gold_heap' else 46
        A(cyl(x, y, rr * 0.9, z0, z0 + rr * 0.45 - 4, WCLIP, 12))
    furn('gold_mask', 0, 220, z0, 270, [((-30, -30, 0), (30, 30, 150))])
    custom('sunstone', 0, y1 - 80, z0, 0, mul=0.7)
    A(box((-L.SUN_R * 0.56, y1 - 80 - 42, z0), (L.SUN_R * 0.56, y1 - 80 + 42, z0 + 50), WCLIP))
    for sx in (-1, 1):
        furn('jaguar', sx * 560, 120, z0, 90 if sx < 0 else 90, [((-64, -32, 0), (64, 32, 104))])
        custom('brazier_big', sx * 300, -350, z0)
        A(cyl(sx * 300, -350, 42, z0, z0 + 106, WCLIP, 8))
    item('item_padpower', 0, 100, z0); item('item_revival', -280, 160, z0); item('holdable_killerducks', 280, 160, z0)
    item('ammo_imperius', -600, -60, z0); item('ammo_betty', 600, -60, z0)
    A(sign_box((-300, y1 - 4, z0 + 340), (300, y1, z0 + 400), T('sign_treasure'), 1024, 128, facing='s'))
    M.ent('misc_teleporter_dest', (0, -250, z0 + 24), targetname='treasure_in', angle=90)
    mdl_c('pad_teleporter/padtp_orange.md3', 0, -480, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, -516, z0 + 2), (36, -444, z0 + 90), TRIG)], target='treasure_out')
    M.ent('misc_teleporter_dest', (-1400, 1000, 24), targetname='treasure_out', angle=270)
    for (x, y, c) in ((0, 0, '1 0.85 0.5'), (-480, 300, '1 0.8 0.4'), (480, 300, '1 0.8 0.4'), (0, -380, '1 0.9 0.7'), (-560, -300, '1 0.8 0.5'), (560, -300, '1 0.8 0.5')):
        light(x, y, z0 + 300, 260, c)
    speaker(0, 0, z0 + 200, 'ambient/water_drippling', volume=0.4)


# =================================================================================================== the feathered serpent mover
def quetzalcoatl():
    cx, cy = L.PC; z = L.QUETZ_Z
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, z - 8), (cx + 8, cy + 8, z + 8), ORIGIN),
                                    box((cx - 4, cy - 4, z + 40), (cx + 4, cy + 4, z + 48), NODRAW_NS)],
          model2=azlib.IQM['quetzalcoatl'], speed=7, spawnflags=0, dmg=0)
    timer_sound(cx, cy - 1400, 700, 'animal/bird_eagle', 'eagle_cry', 25, 12, volume=0.8)


# =================================================================================================== decoration, cover, braziers
def decor():
    rng = np.random.default_rng(7)
    cx, cy = L.PC
    # main sign set into the south bank
    A(sign_box((-512, -L.HY + 64, 120), (512, -L.HY + 68, 376), T('sign_main'), 1024, 256, back=CAULK, facing='n'))
    A(box((-544, -L.HY + 16, 0), (544, -L.HY + 64, 400), {'side': T('ashlar_moss'), 'top': T('coping'), 'bot': CAULK}))
    NOGO.append((-600, -L.HY, 600, -L.HY + 120))
    # braziers flanking the stair feet and along the causeway
    for (x, y) in ((cx - 300, cy - L.H0 - 200), (cx + 300, cy - L.H0 - 200), (cx - 300, cy + L.H0 + 160), (cx + 300, cy + L.H0 + 160),
                   (-200, -560), (200, -560), (-200, -1760), (200, -1760)):
        custom('brazier', x, y, 0)
        A(cyl(x, y, 26, 0, 70, WCLIP, 8))
        light(x, y, 130, 140, '1 0.65 0.3')
        KEEP_OUT.append((x, y, 60))
    speaker(-200, -560, 80, 'ambient/fire_crackling', volume=0.35); speaker(200, -1760, 80, 'ambient/fire_crackling', volume=0.35)
    # palms round the plaza, agave + monstera clumps, stelae, boulders, ruins, loungers, umbrellas
    def put(name, x, y, r, ang=None, z=0.0, box_=None, lit=True, tries=320):
        p = near_free(x, y, r, tries)
        if p is None: return None
        a = rng.uniform(0, 360) if ang is None else ang
        custom(name, p[0], p[1], z, a, lit=lit)
        if box_:
            for (mn, mx) in box_:
                lbox(p[0], p[1], z, a, mn, mx)
        KEEP_OUT.append((p[0], p[1], r))
        return p
    palms = [(-1350, -800), (-1300, -300), (-1250, 700), (-900, 1300), (900, 1300), (1300, 300), (1250, -300), (1300, -800),
             (-2100, -900), (-2100, 1000), (2100, 1000), (2150, -400), (-820, -2000 + 150), (820, -2000 + 150), (-2150, 300), (900, -350),
             (-850, -350), (2150, 300), (-1950, -1100)]
    for i, (x, y) in enumerate(palms):
        p = put(['palm_a', 'palm_b', 'palm_c'][i % 3], x, y, 40, lit=False)
        if p:
            A(cyl(p[0], p[1], 12, 0, 220, WCLIP, 8))
    for i, (x, y) in enumerate(((-1050, -650), (-1250, 1000), (1050, -650), (1250, 1150), (-750, 1500), (750, 1500), (-2000, -700), (2000, 700),
                                (-1300, -1600), (1900, -700), (-1900, 600), (1000, 300), (-1000, 1100), (2050, -1950), (-2050, 1950))):
        put(['agave_a', 'agave_b', 'monstera_a', 'monstera_b'][i % 4], x, y, 70 if i % 4 < 2 else 60, box_=[((-34, -34, 0), (34, 34, 48))] if i % 4 < 2 else None,
            lit=i % 4 < 2)
    for (x, y, a) in ((-1350, 0, 90), (1300, 0, 90), (-800, -2000 + 120, 0), (800, -2000 + 120, 0), (-1000, 1800, 0), (1000, 1850, 0),
                      (2100, -900, 90), (-2150, -500, 90)):
        put('stele_a' if a else 'stele_b', x, y, 64, ang=a, box_=[((-46, -18, 0), (46, 18, 200))])
    for i, (x, y) in enumerate(((-1000, -1950), (1000, -1950), (-2150, -1950), (2150, 1900), (-450, 1450), (450, 1450), (-1950, 200),
                                (1950, 100), (1000, 450), (-1100, 300), (2100, -200), (-1700, -900), (1550, -900), (-200, -1950))):
        nm = ['boulder_a', 'boulder_b', 'boulder_c'][i % 3]
        rr = [60, 90, 130][i % 3]
        p = put(nm, x, y, rr * 0.9)
        if p:
            A(cyl(p[0], p[1], rr * 0.72, 0, rr * 0.9 - 6, WCLIP, 10))
    for (x, y) in ((-600, -300), (600, -300), (-1250, 1250), (1700, 300), (-1700, -400)):
        put('ruin_a', x, y, 110, box_=[((-80, -44, 0), (40, 44, 60)), ((-30, -36, 60), (50, 36, 100)), ((40, 10, 0), (110, 70, 60))])
    # waterpark kit: loungers + parasols by the lakes, tube racks, lifeguard chairs, inner tubes, rubber ducks
    for (x, y, a) in ((-1100, -2000 + 200, 90), (-950, -2000 + 200, 90), (950, -2000 + 200, 90), (1100, -2000 + 200, 90),
                      (-1320, -1200, 0), (1320, -1250, 0), (1350, -1400, 0)):
        put('lounger_a' if x < 0 else 'lounger_b', x, y, 44, ang=a, box_=[((-34, -14, 0), (34, 14, 14))])
    for (x, y) in ((-1020, -1980 + 200), (1020, -1980 + 200), (-1340, -1350), (1340, -1100)):
        p = put('parasol', x, y, 40)
        if p: A(cyl(p[0], p[1], 6, 0, 180, WCLIP, 6))
    for (x, y) in ((-1350, -1600), (1350, -600), (1850, 600)):
        put('tube_rack', x, y, 60, box_=[((-38, -38, 0), (38, 38, 96))])
    for (x, y, a) in ((-1300, -650, 45), (1300, -1650, 225)):
        put('lifeguard', x, y, 60, ang=a, box_=[((-34, -34, 0), (34, 34, 120))])
    for (x, y, nm) in ((-1380, -900, 'itube_a'), (1420, -1500, 'itube_b'), (1700, 1000, 'itube_a'), (-900, -2000 + 260, 'itube_b')):
        put(nm, x, y, 36)
    for (x, y, s) in ((-1480, -1100, 0.3), (1480, -800, 0.3), (2000, -1050, 0.25), (-1800, 750, 0.25)):
        p = near_free(x, y, 50)
        if p: mdl_box('pad_ducks/pad_duck.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 50))
    # catalog greenery and pots for fullness
    for (x, y, s) in ((-1600, -700, 0.3), (1650, -650, 0.3), (-1500, 900, 0.25), (1400, 1450, 0.3), (2050, -1200, 0.3), (-2050, 1500, 0.25)):
        p = near_free(x, y, 90)
        if p: mdl_c('pad_ddmix/plants/fern.md3', p[0], p[1], 0, s, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 80))
    for (x, y) in ((-1150, -1450), (1150, -1300), (-1600, 1000), (1100, 1000), (-700, 1300), (700, 1250)):
        p = near_free(x, y, 40)
        if p: mdl_box('pad_ddmix/padship/amphora.md3', p[0], p[1], 0, 0.3, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 40))
    for (x, y) in ((-2000, -300), (2000, -500), (-1400, 1900), (1400, -1950), (-200, 1990), (1900, 1300)):
        p = near_free(x, y, 70)
        if p: mdl_c('pad_ddmix/trashcan/bush.md3', p[0], p[1], 0, 0.45, rng.uniform(0, 360)); KEEP_OUT.append((p[0], p[1], 70))
    # skulls round the tomb door (cartoon style) and a raven on a stele
    for (x, y) in ((cx - L.H0 - 90, cy - 120), (cx - L.H0 - 90, cy + 120), (cx + L.H0 + 90, cy - 120), (cx + L.H0 + 90, cy + 120)):
        p = near_free(x, y, 30, 96)
        if p: mdl_c('pad_ddmix/jail/skull.md3', p[0], p[1], 0, 0.3, 0 if x > 0 else 180); KEEP_OUT.append((p[0], p[1], 30))
    A(sign_box((-1100, 1040, 180), (-840, 1044, 244), T('sign_cenote'), 512, 128, back=CAULK, facing='s'))
    A(box((-1108, 1044, 0), (-832, 1060, 252), {'side': T('ashlar'), 'top': T('coping'), 'bot': CAULK}))
    A(sign_box((L.JAG[0] - 256, L.JAG[1] - L.JAG_PLAT[1] - 4, 70), (L.JAG[0] + 256, L.JAG[1] - L.JAG_PLAT[1], 134), T('sign_jaguar'), 1024, 128,
               back=CAULK, facing='s'))


def blockers():
    """extra mid-field cover where the long eye-level lines run (placed after sightlines.py --hot)"""
    # rock islets in both lakes: a big mossy boulder and a palm on each
    for k, (x, y, r) in enumerate(L.ISLETS):
        custom('boulder_b', x + 10, y - 10, 0, 40 + 90 * k)
        A(cyl(x + 10, y - 10, 64, 0, 75, WCLIP, 10))
        custom('palm_a' if k else 'palm_b', x - 50, y + 46, 0, 120 * k, lit=False)
        A(cyl(x - 50, y + 46, 12, 0, 220, WCLIP, 8))
        mdl_c('pad_ddmix/plants/fern.md3', x + 40, y + 50, 0, 0.12, 30 * k)
    # north shore: carved stelae and serpent heads between the lagoon and the pyramid
    for (x, y, a) in ((-420, -360, 0), (420, -360, 0), (-900, -400, 0), (980, -380, 0)):
        p = near_free(x, y, 64, 160)
        if p:
            custom('stele_b', p[0], p[1], 0, a)
            lbox(p[0], p[1], 0, a, (-56, -18, 0), (56, 18, 260))
            KEEP_OUT.append((p[0], p[1], 64))
    for (x, y, a) in ((-1290, -1100, 0), (1290, -1180, 180), (1250, 720, 180), (-1180, 1350, 0), (1260, -1720, 180)):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        q = near_free(x + dx * 109, y + dy * 109, 120, 200)
        if q:
            p = (q[0] - dx * 109, q[1] - dy * 109)
            custom('serpent_head', p[0], p[1], 0, a, mul=1.4)
            lbox(p[0], p[1], 0, a, (0, -61, 0), (218, 61, 130))
            KEEP_OUT.append((q[0], q[1], 125))


# =================================================================================================== spawns + loose items
def items_misc():
    item('ammo_nipper', -400, -300, 0); item('ammo_nipper', 400, 1500, 0); item('ammo_nipper', 1800, -700, 0)
    item('ammo_imperius', -1900, -200, 0)
    item('item_armor_shard', -1500, 700, 0); item('item_armor_shard', 1500, 200, 0); item('item_armor_shard', 1900, 1900, 0)
    item('ammo_bubbleg', 2000, 400, 0); item('ammo_splasher', -2000, -1800, 0)
    item('ammo_pumper', 1900, -1950, 0); item('ammo_balloony', -1950, 1900, 0)
    station(1300, -350, 0, 90)
    for (x, y, a) in ((-1800, -400, 0), (1900, -300, 180), (-600, -1980 + 100, 90), (600, 1980 - 300, 270), (-1900, 1700, 315), (2000, 1600, 225),
                      (-2100, -1950, 45), (2150, -1950, 135), (0, -350, 270)):
        p = near_free(x, y, 48)
        if p: spawn(p[0], p[1], 0, a)


def lights_and_sound():
    # sunlit outdoors: the sky does most of it; soft fill under the trees and in the shade of the pyramid
    for (x, y) in ((0, -200), (-1000, 1600), (1000, 1600), (-1800, 0), (1800, 0), (0, 1750)):
        light(x, y, 400, 300, '1 0.95 0.85')
    speaker(-2200, 0, 300, 'animal/cicada_chirp', volume=0.3); speaker(2200, 0, 300, 'animal/cicada_chirp', volume=0.3)
    timer_sound(-2200, 1800, 400, 'animal/bird_cardinal', 'bird1', 18, 8, volume=0.6)
    timer_sound(2200, -1800, 400, 'animal/bird_vireo', 'bird2', 22, 10, volume=0.6)
    timer_sound(2200, 1800, 400, 'animal/bird_blackcap', 'bird3', 26, 12, volume=0.5)
    timer_sound(-2200, -1800, 400, 'ambient/shrubbery', 'bush', 30, 15, volume=0.5)


def main():
    azlib.STATE['out'] = OUT
    TX.make_textures()
    import az_models as AM
    sp, fp = L.serpent_path(), L.flume_path()
    AM.SUPPORTS['tube'] = supports_for(sp[1:], 4, 120)
    AM.SUPPORTS['flume'] = supports_for(fp[1:], 3, 100)
    AM.make()
    sky_hull(); ground(); banks()
    pyramid(); lagoon(); slides_place(); plunge_pool(); cenote(); jaguar_temple(); cantina(); ballcourt(); tlaloc_head(); hall()
    treasure(); quetzalcoatl()
    items_misc()
    decor(); blockers()
    lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (0, -1900, 700), angles='12 90 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padaztec/build_aztec.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
