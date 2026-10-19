#!/usr/bin/env python3
"""Area 51: Dreamland - World of Padman FFA map generator (map 'wop_padarea51').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_area51.py

Writes <OUT>/maps/wop_padarea51.map, textures/padarea51/*, env/padarea51/* (night sky), models/padarea51/*,
scripts/padarea51.shader and scripts/wop_padarea51.arena.

Padman sneaks into the most secret airbase on Earth on a moonlit night. ~64u per metre, x east, y north, ground z 0.
The desert floor is one structural slab (z -640..0) with the S-4 underground lab, the stairwell, the vent shaft and the
crash crater carved out of it, so everything underground is sealed by solid rock and the rest of the map is detail.

  Hangar 18        centre north: walk in through the huge south door. A flying saucer stands on its legs inside: walk
                   up the belly ramp into the cockpit (Boaster); a pad in the cockpit pops you through the deck hatch onto
                   the saucer top, a pad on the deck shoots you through a roof skylight onto the arched roof (Splasher).
                   16u stairs on both side walls lead to catwalks and a gantry onto the saucer. A freight elevator in the
                   north-west corner (func_plat) runs down to the S-4 lab; a pad outside the east wall goes to the roof.
                   Moon-landing film set in the north-east corner (catalog camera, spotlight, director's chair).
  S-4 lab          underground: elevator lobby, long corridor, autopsy room, xenobiology hall with specimen tanks,
                   and behind a crawl duct the containment vault (Imperius). Stairs come down from the S-4 bunker; a
                   pad in the vent shaft at the corridor's south end throws you back out to the surface.
  Control tower    east: walk in, square spiral stairs (16u) to the cab (Betty); a pad through the roof hatch to the
                   roof (Floater) with the beacon mast.
  Water tower      north-east: a pad onto the catwalk ring, a second pad onto the roof (Balloony).
  Radar station    west: 16u stairs up to the platform under the turning dish (Bubble G).
  S-4 bunker       south-west: walk in and take the stairs down to the lab; a pad to the roof.
  Quonset huts     south-west: walk through both (bunks, lockers, health); pads to the curved roofs.
  Black triangle   south-east apron: walk under it, climb the boarding stairs onto it (Pumper).
  Crash site       south: a scorched crater with a crashed scout half buried in it. A hovering scout's tractor beam
                   picks you up from the crashed saucer's dome and drops you on the hangar roof (a cow is mid-abduction).
  Secret           the drained specimen tank at the end of the xenobiology hall: walk in -> the mothership (Pad Power,
                   Revival, Killer Ducks); a teleporter takes you back down.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import a51_textures as TX
import a51_models as AM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padarea51'
T = lambda n: 'padarea51/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
BOTCLIP = 'common/botclip'
NODRAW_NS = T('nodraw_ns')

for k, v in {'sand': (1, 1), 'scorched': (1, 1), 'rock': (1, 1), 'tarmac': (1, 1), 'apron': (1, 1), 'concrete': (0.5, 0.5),
             'concrete_dark': (0.5, 0.5), 'lab_floor': (0.5, 0.5), 'lab_wall': (0.5, 0.5), 'lab_ceil': (0.5, 0.5), 'steel': (0.5, 0.5),
             'plate': (0.5, 0.5), 'hazard': (0.25, 0.25), 'rust': (0.5, 0.5), 'crate': (0.25, 0.25), 'alien_panel': (0.5, 0.5),
             'alien_floor': (1, 1), 'chainlink': (0.5, 0.5), 'grate': (0.5, 0.5), 'sky': (4, 4), 'dark': (1, 1)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '6', '_color': '0.7 0.75 1', 'gridsize': '96 96 128', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
XW, YN = 2304, 2048                 # playable ground half extents (bank toes)
BANK_X, BANK_H = 2528, 448          # bank slope reaches z BANK_H here
HX, HY = 2816, 2560                 # sky hull inner half extents
ZSKY, ZBOT = 2560, -640
LAB0, LAB1 = -512, -192             # lab floor / ceiling
MS_Z = -2560                        # mothership floor (separate sealed room below the world)
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
KEEP_OUT = []                       # (x, y, r) discs where scatter decoration must not go


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


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12, top_cut=4):
    e = mdl_c(path, x, y, zsurf, scale, angle)
    b = BOUNDS['models/mapobjects/' + path]
    ox, oy, oz = (float(v) for v in e['origin'].split())
    z1 = oz + b['max'][2] * scale
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for px in (b['min'][0], b['max'][0]):
        for py in (b['min'][1], b['max'][1]):
            xs.append(ox + (px * ca - py * sa) * scale); ys.append(oy + (px * sa + py * ca) * scale)
    dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
    A(box((round(min(xs) + dx), round(min(ys) + dy), round(zsurf)), (round(max(xs) - dx), round(max(ys) - dy), round(z1 - top_cut)), WCLIP))
    return e


def custom(name, x, y, zbase, angle=0, lit=True, mul=1.0, **kw):
    """one of our own MD3s (models/padarea51), base point at (x, y, zbase); mul scales it further"""
    path, sc, zo = AM.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=sc, angle=angle, **extra)


def prop(name, x, y, zbase, angle=0, solid=True, shrink=0.1, top_cut=2, **kw):
    """vertex-lit prop MD3 + a weapon-clip box from its real bounds"""
    e = custom(name, x, y, zbase, angle, lit=False, **kw)
    if solid:
        mn, mx = PROP_BOUNDS[name]
        a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
        xs, ys = [], []
        for px in (mn[0], mx[0]):
            for py in (mn[1], mx[1]):
                xs.append(x + px * ca - py * sa); ys.append(y + px * sa + py * ca)
        dx = (max(xs) - min(xs)) * shrink / 2; dy = (max(ys) - min(ys)) * shrink / 2
        A(box((round(min(xs) + dx), round(min(ys) + dy), round(zbase)), (round(max(xs) - dx), round(max(ys) - dy), round(zbase + mx[2] - top_cut)), WCLIP))
    return e


PROP_BOUNDS = {}


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex)


def light(x, y, z, val, color='1 0.9 0.8', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def timer_sound(x, y, z, noise, name, wait, rnd, **kw):
    speaker(x, y, z, noise, loop=False, targetname=name, **kw)
    M.ent('func_timer', (round(x), round(y), round(z + 40)), target=name, wait=wait, random=rnd, spawnflags=1)


def item(cls, x, y, floor, **kw):
    M.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, x, y, floor))


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))


def spawn(x, y, floor, ang):
    M.ent('info_player_deathmatch', (round(x), round(y), round(floor) + 25), angle=ang % 360)
    SPOTS['spawn'].append((x, y, floor))


def hfit(b, x0, y0, x1, y1, tw, th, tex):
    """top face(s) with `tex`: exactly one copy of a tw x th texture over the rectangle (north = texture top)"""
    for f in b.faces:
        if f.tex != tex or f.n[2] < 0.7: continue
        sx = (x1 - x0) / tw; sy = (y1 - y0) / th
        f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def jumppad(x, y, z, land, apex, name, glow=True):
    """alien landing-glyph pad (r 34 disc) + trigger_push + target_position. Q3 AimAtTarget: the target is the apex of
    the flight measured from the trigger centre; the player keeps flying past it, so the target sits
    t_up/(t_up+t_down) of the way to `land`."""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T('jumppad'), 'side': T('rubber'), 'bot': T('rubber')}, 12))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            f.sc = (68 / 256, 68 / 256); f.off = ((-(x - 34) / (68 / 256)) % 256, ((y + 34) / (68 / 256)) % 256)
    trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
    push(trig, (x, y, z + 38), land, apex, name)
    if glow: light(x, y, z + 48, 110, '0.4 1 0.55')
    KEEP_OUT.append((x, y, 80))


def push(trig, o, land, apex, name):
    ox, oy, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    tx, ty = ox + (lx - ox) * f, oy + (ly - oy) * f
    M.ent('trigger_push', brushes=[trig], target=name)
    M.ent('target_position', (round(tx), round(ty), round(apex)), targetname=name)
    JUMPPADS.append((name, (round(ox), round(oy), round(oz)), (round(tx), round(ty), round(apex)), land))


def deco(mn, mx, tex):
    d = {'side': NODRAW_NS}
    if isinstance(tex, dict): d.update(tex)
    else: d = {'side': tex, 'top': tex, 'bot': tex}
    return box(mn, mx, d)


def ang_pt(cx, cy, r, a_deg):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def sector(cx, cy, k, n, r0, r1, z0a, z1a, z0b, z1b, tex):
    """wedge of a ring band: inner radius r0 spans z0a..z1a, outer r1 spans z0b..z1b, angles k*360/n..(k+1)*360/n"""
    a0, a1 = k * 360.0 / n, (k + 1) * 360.0 / n
    pts = []
    for a in (a0, a1):
        for (r, za, zb) in ((r0, z0a, z1a), (r1, z0b, z1b)):
            if r <= 0.01:
                pts += [(cx, cy, za), (cx, cy, zb)]; continue
            px, py = ang_pt(cx, cy, r, a)
            pts += [(px, py, za), (px, py, zb)]
    return hull(pts, tex, round_pts=False)


def wall_boxes(x0, x1, y0, y1, z0, z1, holes, tex, axis=None):
    """thin wall box split around rectangular holes [(u0, u1, za, zb)] (u = x for walls along x, y for walls along y)"""
    along_x = (x1 - x0) >= (y1 - y0) if axis is None else axis == 'x'
    u0, u1 = (x0, x1) if along_x else (y0, y1)
    out = []
    for (ua, za, ub, zb) in sub_rects((u0, z0, u1, z1), [(a, c, b, d) for (a, b, c, d) in holes]):
        if along_x: out.append(box((ua, y0, za), (ub, y1, zb), tex))
        else: out.append(box((x0, ua, za), (x1, ub, zb), tex))
    return out


def carve_all(brushes, cutters):
    out = []
    for b in brushes:
        bmn, bmx = b.bounds()
        cs = []
        for c in cutters:
            cmn, cmx = c.bounds()
            if np.all(cmn < bmx - 1e-3) and np.all(cmx > bmn + 1e-3): cs.append(c)
        out += carve(b, cs) if cs else [b]
    return out


# =================================================================================================== sky hull, banks, fence
def hull_and_banks():
    W = 16
    sk = {'side': CAULK, 'top': CAULK, 'bot': CAULK}
    A(box((-HX - W, -HY - W, ZBOT - W), (HX + W, HY + W, ZBOT), dict(sk, top=T('sky')), detail=False))
    A(box((-HX - W, -HY - W, ZSKY), (HX + W, HY + W, ZSKY + W), dict(sk, bot=T('sky')), detail=False))
    A(box((-HX - W, HY, ZBOT), (HX + W, HY + W, ZSKY), dict(sk, s=T('sky')), detail=False))
    A(box((-HX - W, -HY - W, ZBOT), (HX + W, -HY, ZSKY), dict(sk, n=T('sky')), detail=False))
    A(box((HX, -HY, ZBOT), (HX + W, HY, ZSKY), dict(sk, w=T('sky')), detail=False))
    A(box((-HX - W, -HY, ZBOT), (-HX, HY, ZSKY), dict(sk, e=T('sky')), detail=False))
    # rock ridges round the base: steep (unwalkable), flat tops, player clip above
    bt = lambda n: T('rock') if 0.2 < n[2] < 0.99 else (T('sand') if n[2] >= 0.99 else CAULK)
    yb = YN + BANK_X - XW
    for sx in (-1, 1):
        A(hull([(sx * x, y, z) for y in (-YN, YN) for (x, z) in ((XW, 0), (BANK_X, BANK_H), (HX, BANK_H), (HX, ZBOT), (XW, ZBOT))], bt, detail=False))
    for sy in (-1, 1):
        A(hull([(x, sy * y, z) for x in (-XW, XW) for (y, z) in ((YN, 0), (yb, BANK_H), (HY, BANK_H), (HY, ZBOT), (YN, ZBOT))], bt, detail=False))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [(XW, YN, 0), (BANK_X, YN, BANK_H), (XW, yb, BANK_H), (BANK_X, yb, BANK_H), (HX, YN, BANK_H), (HX, HY, BANK_H),
                   (XW, HY, BANK_H), (HX, yb, BANK_H), (BANK_X, HY, BANK_H)]
            pts = pts + [(x, y, ZBOT) for (x, y) in ((XW, YN), (HX, YN), (HX, HY), (XW, HY))]
            A(hull([(sx * x, sy * y, z) for (x, y, z) in pts], bt, detail=False))
    for sx in (-1, 1):
        A(box((min(sx * BANK_X, sx * HX), -HY, BANK_H), (max(sx * BANK_X, sx * HX), HY, ZSKY), CLIP))
    for sy in (-1, 1):
        A(box((-BANK_X, min(sy * yb, sy * HY), BANK_H), (BANK_X, max(sy * yb, sy * HY), ZSKY), CLIP))
    # chain-link fence along the bank toes (posts, razor wire), warning signs every so often
    FH = 176
    fence = lambda face: (lambda n: T('chainlink') if abs(n[0] * face[0] + n[1] * face[1]) > 0.9 else NODRAW_NS)
    for sx in (-1, 1):
        A(box((min(sx * (XW - 4), sx * XW), -YN, 0), (max(sx * (XW - 4), sx * XW), YN, FH), fence((1, 0))))
    for sy in (-1, 1):
        A(box((-XW + 4, min(sy * (YN - 4), sy * YN), 0), (XW - 4, max(sy * (YN - 4), sy * YN), FH), fence((0, 1))))
    posts = [(sx * (XW - 10), y) for sx in (-1, 1) for y in range(-YN + 384, YN, 384)] + \
            [(x, sy * (YN - 10)) for sy in (-1, 1) for x in range(-XW + 384, XW, 384)]
    for (px, py) in posts:
        A(box((px - 6, py - 6, 0), (px + 6, py + 6, FH + 24), T('steel')))
    signs = [((-XW + 12, -1088), 'e', 'sign_restricted'), ((-XW + 12, 832), 'e', 'sign_nophoto'), ((XW - 12, 64), 'w', 'sign_restricted'),
             ((XW - 12, 1216), 'w', 'sign_nophoto'), ((-1344, YN - 12), 's', 'sign_restricted'), ((960, YN - 12), 's', 'sign_restricted'),
             ((-192, -YN + 12), 'n', 'sign_nophoto'), ((1344, -YN + 12), 'n', 'sign_cows')]
    for ((x, y), face, tex) in signs:
        w, h = 160, 80
        if face in 'ew':
            x0 = x - (4 if face == 'w' else 0); A(sign_box((x0, y - w / 2, 60), (x0 + 4, y + w / 2, 60 + h), T(tex), 512, 256, back=NODRAW_NS, facing=face))
        else:
            y0 = y - (4 if face == 's' else 0); A(sign_box((x - w / 2, y0, 60), (x + w / 2, y0 + 4, 60 + h), T(tex), 512, 256, back=NODRAW_NS, facing=face))


# =================================================================================================== ground slab, lab cutters, crater
LAB_ROOMS = {
    'lobby':   (-832, -384, 1216, 1664, LAB0, LAB1),
    'corr':    (-832, -640, -416, 1216, LAB0, LAB1),
    'autopsy': (-1472, -896, 640, 1152, LAB0, LAB1),
    'door_a':  (-896, -832, 832, 960, LAB0, LAB0 + 160),
    'spec':    (-1472, -896, -128, 448, LAB0, LAB1),
    'door_s':  (-896, -832, 96, 224, LAB0, LAB0 + 160),
    'vault':   (-2048, -1664, 192, 576, LAB0, LAB1 - 32),
    'duct':    (-1664, -1472, 256, 352, LAB0, LAB0 + 64),
    'pass':    (-1280, -1088, -768, -128, LAB0, LAB1),
    'stairA1': (-1664, -1280, -928, -768, LAB0, 0),
    'stairA2': (-1888, -1664, -928, -768, LAB0, -32),
    'stairB':  (-1888, -1280, -768, -608, LAB0, -32),
    'elev':    (-704, -512, 1344, 1536, LAB1, 0),
    'elev_pit': (-704, -512, 1344, 1536, LAB0 - 16, LAB0),
    'vent':    (-800, -672, -384, -192, LAB1, 0),
}
ROOM_TEX = {'vault': (T('concrete_dark'), T('rust'), T('concrete_dark')), 'stairA1': (T('concrete'), T('concrete'), T('concrete')),
            'stairA2': (T('concrete'), T('concrete'), T('concrete')), 'stairB': (T('concrete'), T('concrete'), T('concrete')),
            'elev': (T('steel'), T('hazard'), T('steel')), 'elev_pit': (T('steel'), T('hazard'), T('steel')), 'vent': (T('steel'), T('steel'), T('steel')), 'duct': (T('steel'), T('steel'), T('steel'))}
CRATER = None


def region_tex(x, y):
    if -960 <= x <= 960 and 576 <= y <= 1728: return T('apron')
    if -1088 <= x <= 1088 and -256 <= y <= 576: return T('apron')
    if -704 <= x and y <= -1728: return 'RUNWAY'
    if 1024 <= x and -1728 <= y <= -512: return T('tarmac')
    if 1088 <= x <= 1344 and -512 <= y <= 640: return T('tarmac')
    if x <= -1088 and -192 <= y <= 64: return T('tarmac')
    return T('sand')


def ground():
    global CRATER
    xs = sorted({-XW, XW, -960, 960, -1088, 1088, -704, 1024, 1344, 2304} | {-XW})
    ys = sorted({-YN, YN, 576, 1728, -256, -1728, -512, 640, -192, 64})
    cells = []
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cells.append((xa, ya, xb, yb, region_tex((xa + xb) / 2, (ya + yb) / 2)))
    # merge along y then x where the texture matches
    merged = True
    while merged:
        merged = False
        for i in range(len(cells)):
            for j in range(len(cells)):
                a, b = cells[i], cells[j]
                if i == j or a[4] != b[4]: continue
                if a[0] == b[0] and a[2] == b[2] and a[3] == b[1]:
                    cells[i] = (a[0], a[1], a[2], b[3], a[4]); cells.pop(j); merged = True; break
                if a[1] == b[1] and a[3] == b[3] and a[2] == b[0]:
                    cells[i] = (a[0], a[1], b[2], a[3], a[4]); cells.pop(j); merged = True; break
            if merged: break
    slabs = []
    for (x0, y0, x1, y1, tex) in cells:
        b = box((x0, y0, ZBOT), (x1, y1, 0), CAULK, detail=False)
        b.region = tex
        slabs.append(b)
    # cutters
    cutters = []
    for nm, (x0, x1, y0, y1, z0, z1) in LAB_ROOMS.items():
        c = box((x0, y0, z0), (x1, y1, z1 + (16 if z1 == 0 else 0)), CAULK); c.room = nm; cutters.append(c)
    cx, cy = AM.CR
    rz = lambda z: AM.CR_R1 + (z + AM.CR_D) * (AM.CR_R0 - AM.CR_R1) / AM.CR_D
    CRATER = hull([(x, y, z) for z in (-AM.CR_D, 16) for (x, y) in ngon(cx, cy, rz(z), 24, 0)], CAULK, round_pts=False)
    CRATER.room = 'crater'; cutters.append(CRATER)
    pieces = []
    for b in slabs:
        bmn, bmx = b.bounds()
        cs = [c for c in cutters if np.all(c.bounds()[0] < bmx - 1e-3) and np.all(c.bounds()[1] > bmn + 1e-3)]
        ps = carve(b, cs) if cs else [b]
        for p in ps:
            p.region = b.region; p.detail = False
        pieces += ps
    # texture every face by what lies just in front of it
    def inside(c, p):
        return all(np.dot(n, p) - d <= 1e-3 for n, d in c.planes())
    runway = (-704, -YN, XW, -1728)
    for p in pieces:
        V = p.verts()
        for f in p.faces:
            on = V[np.abs(V @ np.array(f.n) - f.d) < 1e-2]
            if len(on) < 3: f.tex = CAULK; continue
            c0 = on.mean(0)
            # several probe points just in front of the face (centroid + points pulled in from each corner)
            rng_f = np.random.default_rng(len(on))
            W8 = rng_f.dirichlet(np.ones(len(on)), 48)
            probes = [c0] + [c0 + (v - c0) * 0.8 for v in on] + list(W8 @ on)
            room = None
            for pr in probes:
                q = pr + np.array(f.n) * 0.5
                room = next((c.room for c in cutters if inside(c, q)), None)
                if room: break
            if room is None:
                if f.n[2] > 0.99 and abs(c0[2]) < 0.5:
                    f.tex = T('runway') if p.region == 'RUNWAY' else p.region
                else:
                    f.tex = CAULK
            elif room == 'crater':
                f.tex = T('scorched') if (f.n[2] > 0.2) else CAULK
            else:
                fl, wl, ce = ROOM_TEX.get(room, (T('lab_floor'), T('lab_wall'), T('lab_ceil')))
                f.tex = fl if f.n[2] > 0.7 else (ce if f.n[2] < -0.7 else wl)
                if room in ('corr', 'lobby', 'autopsy', 'spec', 'pass') and abs(f.n[2]) < 0.7:
                    # wall texture: stripe at a fixed height (lab_wall is 256 tall over 128u: scale 0.5 => fit floor..floor+128?)
                    pass
            f.sc = wopmap.default_scale(f.tex)
            if f.tex in (T('lab_wall'),) and abs(f.n[2]) < 0.7:
                f.sc = (0.5, 320 / 256); f.off = (0, round((LAB1 / (320 / 256)) % 256, 3))
        if any(f.tex == T('runway') for f in p.faces):
            hfit(p, runway[0], runway[1], runway[2], runway[3], 2048, 224, T('runway'))
        A(p)


# =================================================================================================== HANGAR 18
def hangar():
    cy = AM.HG_CY
    custom('hangar', 0, cy, 0)
    xw, y0, y1, t, H = AM.HG_X, AM.HG_Y0, AM.HG_Y1, AM.HG_T, AM.HG_H
    W_TOP = 512                                       # collision wall top (the roof slab sits on it)
    dw, dh = AM.HG_DOOR
    s0, s1, sh = AM.HG_SDOOR
    for sx in (-1, 1):
        A(wall_boxes(min(sx * xw, sx * (xw - t)), max(sx * xw, sx * (xw - t)), y0, y1, 0, W_TOP, [(s0, s1, 0, sh)], WCLIP, axis='y'))
    A(wall_boxes(-xw + t, xw - t, y0, y0 + t, 0, W_TOP, [(-dw, dw, 0, dh)], WCLIP, axis='x'))
    A(wall_boxes(-xw + t, xw - t, y1 - t, y1, 0, W_TOP, [(-AM.HG_NDOOR[0], AM.HG_NDOOR[0], 0, AM.HG_NDOOR[1])], WCLIP, axis='x'))
    # roof facets (top = arch chord, 32 thick) + gable pieces under them
    xs = np.linspace(-xw, xw, AM.HG_FACETS + 1)
    rt = lambda x: AM.hg_roof(abs(x))
    for xa, xb in zip(xs, xs[1:]):
        xm = (xa + xb) / 2
        ycuts = [y0, y1]
        for (sx0, sx1, sy0, sy1) in AM.HG_SKY:
            if sx0 < xm < sx1: ycuts = [y0, sy0, sy1, y1]
        for (ya, yb) in zip(ycuts[::2], ycuts[1::2]):
            A(hull([(x, y, z) for (x, zt) in ((xa, rt(xa)), (xb, rt(xb))) for y in (ya, yb) for z in (zt, zt - t)], WCLIP, round_pts=False))
        for (ya, yb) in ((y0, y0 + t), (y1 - t, y1)):
            pts2 = [(xa, W_TOP), (xb, W_TOP), (xb, max(rt(xb) - t, W_TOP)), (xa, max(rt(xa) - t, W_TOP))]
            if max(p[1] for p in pts2) - W_TOP < 2: continue
            uniq = []
            for p in pts2:
                if all(abs(p[0] - q[0]) > 0.1 or abs(p[1] - q[1]) > 0.1 for q in uniq): uniq.append(p)
            if len(uniq) < 3: continue
            A(hull([(x, y, z) for (x, z) in uniq for y in (ya, yb)], WCLIP, round_pts=False))
    # ---- catwalks, stairs, gantry (steel)
    st = {'top': T('plate'), 'side': T('steel'), 'bot': T('steel')}
    C = AM.HG_CAT
    for sx in (-1, 1):
        x0, x1 = (800, 928) if sx > 0 else (-928, -800)
        A(stairs(x0, 640, x1, 1472, 0, C, 'n', st, thick=48))
        A(box((x0, 1472, C - 16), (x1, 1568, C), st))
    A(box((-928, 1568, C - 16), (928, 1696, C), st))
    # catwalk rails: nonsolid deco bars (a low rail never blocks a shot)
    for sx in (-1, 1):
        xr = 796 if sx > 0 else -800
        A(deco((xr, 1472, C + 36), (xr + 4, 1568, C + 40), T('steel')))
    A(deco((-796, 1564, C + 36), (796, 1568, C + 40), T('steel')))
    # ---- freight elevator to S-4 (drawn raised at the hangar floor; it rests at the lab floor)
    ex0, ex1, ey0, ey1 = -704, -512, 1344, 1536
    plat = box((ex0 + 4, ey0 + 4, -16), (ex1 - 4, ey1 - 4, 0), {'top': T('hazard'), 'side': T('steel'), 'bot': T('steel')})
    M.ent('func_plat', brushes=[plat], height=-LAB0, speed=260, lip=0, noise='sound/world/plats/start.wav')
    A(deco((ex0 - 16, ey0 - 16, 0), (ex1 + 16, ey0, 1), T('hazard'))); A(deco((ex0 - 16, ey1, 0), (ex1 + 16, ey1 + 16, 1), T('hazard')))
    A(deco((ex0 - 16, ey0, 0), (ex0, ey1, 1), T('hazard'))); A(deco((ex1, ey0, 0), (ex1 + 16, ey1, 1), T('hazard')))
    # ---- the saucer
    saucer()
    # ---- moon-landing set (north-east corner): grey regolith patch, lander, flag, the film crew's gear (catalog)
    A(deco((240, 1560 - 400, 0), (760, 1530, 2), {'top': T('concrete_dark'), 'side': NODRAW_NS, 'bot': NODRAW_NS}))
    mdl_c('pad_westernset/camera.md3', 560, 930, 0, 0.55, 80)
    A(box((520, 890, 0), (600, 970, 80), WCLIP))
    mdl_c('pad_westernset/directors_chair.md3', 300, 830, 0, 0.45, 60)
    A(box((270, 805, 0), (330, 855, 60), WCLIP))
    mdl_c('pad_ddmix/padshop/cardboard_standup.md3', 720, 1220, 2, 0.6, 200)
    custom('lander', 560, 1380, 2, angle=210)
    A(box((500, 1320, 2), (620, 1440, 120), WCLIP))
    custom('flag', 380, 1420, 2, angle=0, lit=False)
    # ---- props round the hangar floor
    for (x, y, a) in ((-680, 680, 0), (-680, 800, 90), (-570, 680, 20)):
        prop('crate96', x, y, 0, a)
    prop('crate64', -680, 680, 96, 10)
    prop('forklift', -400, 680, 0, 0)
    prop('rack', -880, 1300, 0, 0)
    prop('rack', -880, 1210, 0, 0)
    prop('console', -620, 1130, 0, 200)
    item('item_armor_padshield', 0, 1632, C)
    item('holdable_boomies', 860, 1620, C)
    item('ammo_splasher', -860, 1620, C)
    weapon('boaster', 60, 1250, AM.S_FLOOR, 'orange')
    item('ammo_boaster', -60, 1180, AM.S_FLOOR)
    item('ammo_imperius', 230, 1216, AM.S_DECK)
    item('item_armor_shard', -163, 1053, AM.S_DECK)
    # roof (Splasher), ammo
    weapon('splasher', 0, 880, AM.HG_RIDGE, 'black')
    item('ammo_splasher', -520, 1500, AM.hg_roof(520) + 8)
    item('ammo_betty', 560, 760, AM.hg_roof(560) + 8)
    # pads: east lawn -> roof; deck -> skylight -> roof (inside saucer()); cockpit -> deck hatch (inside saucer())
    jumppad(1150, 1000, 0, (700, 1000, AM.hg_roof(700)), 880, 'hangar_roof')
    # lights: hanging lamps (match the MD3's lamps) + floor fill
    for yy in np.arange(y0 + 96, y1 - 95, 192):
        for x in (-520, 0, 520):
            light(x, yy, AM.hg_roof(abs(x)) - t - 120, 900 if x else 700, '1 0.95 0.85')
    light(0, 680, 380, 900, '1 0.9 0.75')
    light(500, 1300, 300, 900, '0.9 0.95 1')                 # film set spotlight
    speaker(0, cy, 400, 'sound/world/machine/aircon.ogg', volume=0.4)
    speaker(0, AM.SC[1], 300, 'sound/world/machine/portal_idle.ogg', volume=0.5)
    timer_sound(0, 900, 480, 'sound/world/misc/alarm_buzzer.ogg', 'hg_alarm', 70, 30, volume=0.5)
    KEEP_OUT.append((0, cy, 1400))


def saucer():
    cx, cy = AM.SC
    custom('saucer', cx, cy, 0)
    n = 16
    W = WCLIP
    fl = {'top': T('alien_floor'), 'side': W, 'bot': W}
    pcs = []
    for k in range(n):
        pcs.append(sector(cx, cy, k, n, 0, 300, AM.S_BELLY, AM.S_FLOOR, AM.S_BELLY, AM.S_FLOOR, fl))
        pcs.append(sector(cx, cy, k, n, AM.S_IN, 300, AM.S_FLOOR, AM.s_top(AM.S_IN), AM.S_FLOOR, AM.s_top(300), W))
        for (ra, rb) in ((300, 390), (390, AM.S_RIM)):
            pcs.append(sector(cx, cy, k, n, ra, rb, AM.s_bot(ra), AM.s_top(ra), AM.s_bot(rb), AM.s_top(rb), W))
        # deck slab over the cockpit (hatch sectors open between S_HATCH_R)
        pcs.append(sector(cx, cy, k, n, 0, AM.S_HATCH_R[0], AM.S_DECK_BOT, AM.S_DECK, AM.S_DECK_BOT, AM.S_DECK, W))
        if k not in AM.S_HATCH:
            pcs.append(sector(cx, cy, k, n, AM.S_HATCH_R[0], AM.S_IN, AM.S_DECK_BOT, AM.S_DECK, AM.S_DECK_BOT, AM.S_DECK, W))
    # belly opening for the ramp (rectangle, south): carve it out of the floor and the hull above up to z 300
    cut = box((cx - 104, cy - 360, AM.S_BELLY - 1), (cx + 104, cy - 100, 300), CAULK)
    pcs = carve_all(pcs, [cut])
    A(pcs)
    # dome
    A(frustum(cx, cy, AM.S_DOME_R - 4, AM.S_DECK, 120, 500, W))
    A(frustum(cx, cy, 120, 500, 44, 540, W))
    # ramp (wedge, south)
    r0, r1 = AM.S_RAMP_R[0], AM.S_RAMP_END
    prof = [(r0, AM.S_FLOOR), (r1, 0), (r1 - 30, 0), (r0, AM.S_FLOOR - 16)]
    A(hull([(cx + sx, cy - r, z) for (r, z) in prof for sx in (-96, 96)], W, round_pts=False))
    # legs: slanted struts + foot pads
    for a in AM.S_LEGS:
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        tx, ty = cx + 330 * c, cy + 330 * s; fx, fy = cx + 430 * c, cy + 430 * s
        A(hull([(x, y, z) for (x, y) in ngon(tx, ty, 14, 8) for z in (AM.S_BELLY - 2,)] +
               [(x, y, z) for (x, y) in ngon(fx, fy, 14, 8) for z in (20,)], W, round_pts=False))
        A(cyl(round(fx), round(fy), 48, 0, 20, W, 12))
    # cockpit consoles (low weapclip blocks)
    for k in range(16):
        if k in (2, 3, 4, 5, 10, 11, 12, 13): continue
        am = math.radians((k + 0.5) * 22.5)
        c, s = math.cos(am), math.sin(am)
        pts = []
        for (dr, dt) in ((-20, -26), (20, -26), (20, 26), (-20, 26)):
            r = 160 + dr
            pts.append((cx + r * c - dt * s, cy + r * s + dt * c))
        A(hull([(x, y, z) for (x, y) in pts for z in (AM.S_FLOOR, AM.S_FLOOR + 44)], W, round_pts=False))
    # pads: cockpit -> deck hatch, deck -> roof skylight
    hx, hy = ang_pt(cx, cy, 220, 90)
    lx, ly = ang_pt(cx, cy, 228, 140)
    jumppad(hx, hy, AM.S_FLOOR, (lx, ly, AM.S_DECK), 580, 'saucer_hatch', glow=False)
    sx, sy = ang_pt(cx, cy, 224, 180)
    jumppad(sx, sy, AM.S_DECK, (-560, cy, AM.hg_roof(560)), 880, 'saucer_skylight', glow=False)
    light(cx, cy, AM.S_FLOOR + 110, 320, '0.4 1 0.85')
    light(cx, cy, 120, 500, '0.4 1 0.85')
    for a in (30, 150, 270):
        x, y = ang_pt(cx, cy, 420, a); light(x, y, 190, 260, '0.5 1 0.9')


# =================================================================================================== S-4 lab (underground)
def lab():
    R = LAB_ROOMS
    # ceiling light panels (glowing, flush) - thin detail brushes hanging 2u below the ceiling
    def panel(x, y, w=128, h=64, tex='light_panel', z=LAB1):
        A(box((x - w / 2, y - h / 2, z - 2), (x + w / 2, y + h / 2, z), {'bot': T(tex), 'side': T('steel'), 'top': CAULK}))
    for y in range(-64, 1200, 256): panel(-736, y, 64, 128)
    for (x, y) in ((-1300, 900), (-1050, 900), (-1300, 760), (-1050, 760), (-1180, 1040)): panel(x, y)
    for (x, y) in ((-1300, 300), (-1050, 300), (-1300, 40), (-1050, 40)): panel(x, y, tex='light_green')
    for (x, y) in ((-460, 1420), (-760, 1290)): panel(x, y)
    panel(-1184, -400, 64, 128); panel(-1184, -650, 64, 128)
    for (x, y) in ((-1856, 300), (-1856, 470)): panel(x, y, tex='glow_red', w=64, h=64, z=LAB1 - 32)
    # --- lobby: health station, lockers, elevator call sign
    M.ent('station_health', (-430, 1600, LAB0), angle=180)
    prop('lockers', -800, 1540, LAB0, 0)
    sign_at((-640, 1664 - 4, LAB0 + 180), 's', 'sign_s4', 240, 120)
    item('ammo_pumper', -460, 1260, LAB0)
    light(-600, 1440, LAB0 + 250, 500, '0.9 0.95 1')
    # --- corridor: crates, filing cabinets; Visionless in the dark kink
    for (x, y, a) in ((-806, 560, 0), (-806, 230 - 120, 0)):
        prop('filing', x, y, LAB0, a)
    prop('crate64', -684, 700, LAB0, 0)
    prop('crate64', -790, -40, LAB0, 0)
    item('item_visionless', -736, -340, LAB0)
    item('ammo_boaster', -700, 400, LAB0)
    for y in (-200, 300, 800):
        light(-736, y, LAB0 + 260, 380, '0.9 0.95 1')
    # --- autopsy room
    cx, cy = -1184, 896
    prop('autopsy', cx, cy, LAB0, 0)
    mdl_c('pad_ddmix/anteroom/medical_case.md3', -1420, 700, LAB0, 0.6, 90)
    A(box((-1440, 670, LAB0), (-1400, 730, LAB0 + 56), WCLIP))
    mdl_c('ente/deadalienB.md3', -1350, 1080, LAB0, 3.0, 220)
    for (x, y, a) in ((-1428, 1100, 0), (-1428, 1010, 0)): prop('rack', x, y, LAB0, a)
    prop('console', -960, 1080, LAB0, 180)
    item('ammo_imperius', -1000, 700, LAB0)
    item('ammo_balloony', -1300, 1110, LAB0)
    light(cx, cy, LAB0 + 260, 700, '0.95 1 1')
    speaker(cx, cy, LAB0 + 200, 'sound/world/machine/freezer.ogg', volume=0.6)
    # --- xenobiology hall: specimen tanks with greys along both long walls; the drained one at the end is the secret
    tanks = [(-1400, -40), (-1400, 120), (-1400, 280), (-968, -40), (-968, 120), (-968, 340)]
    for (x, y) in tanks:
        prop('spec_tank', x, y, LAB0, 0 if x < -1100 else 180, shrink=0.25)
    sign_at((-1184, 448 - 4, LAB0 + 200), 's', 'sign_lab', 256, 128)
    # the secret tank: same model, no collision, a teleport trigger inside
    sx, sy = -1184, -60
    custom('spec_tank', sx, sy, LAB0, 90, lit=False)
    M.ent('trigger_multiple', brushes=[box((sx - 90, sy + 50, LAB0), (sx + 90, sy + 120, LAB0 + 80), TRIG)], target='secret_snd', wait=6)
    speaker(sx, sy + 60, LAB0 + 80, 'sound/world/misc/secret_found.ogg', loop=False, targetname='secret_snd')
    M.ent('trigger_teleport', brushes=[box((sx - 30, sy - 30, LAB0 + 36), (sx + 30, sy + 30, LAB0 + 140), TRIG)], target='ms_in')
    light(sx, sy, LAB0 + 120, 160, '0.3 1 0.5')
    weapon('pumper', -1184, 220, LAB0, 'green')
    item('ammo_splasher', -1300, 400, LAB0)
    item('ammo_bubbleg', -1060, -90, LAB0)
    light(-1184, 160, LAB0 + 260, 500, '0.6 1 0.7')
    speaker(-1184, 160, LAB0 + 100, 'sound/world/ambient/slime_bubbling.ogg', volume=0.5)
    # --- containment vault behind the crawl duct (Imperius on a plinth)
    vx, vy = -1856, 384
    A(box((vx - 64, vy - 64, LAB0), (vx + 64, vy + 64, LAB0 + 16), {'top': T('hazard'), 'side': T('steel'), 'bot': CAULK}))
    weapon('imperius', vx, vy, LAB0 + 16, 'purple')
    item('ammo_imperius', vx - 120, vy + 140, LAB0)
    item('ammo_betty', vx + 120, vy - 130, LAB0)
    mdl_c('ente/deadalienA.md3', -1730, 300, LAB0, 2.5, 0)
    mdl_c('pad_ddmix/jail/skull.md3', vx - 130, vy - 120, LAB0, 0.35, 60)
    sign_at((vx, 576 - 4, LAB0 + 150), 's', 'sign_vault', 256, 128)
    light(vx, vy, LAB0 + 200, 420, '1 0.3 0.25')
    speaker(vx, vy, LAB0 + 120, 'sound/world/misc/strange_signal.ogg', volume=0.5)
    # duct grille frames (deco) at both ends
    for (xa, xb) in ((-1668, -1664), (-1472, -1468)):
        A(deco((xa, 248, LAB0 + 64), (xb, 360, LAB0 + 72), T('hazard')))
    # --- passage + server racks
    for y in (-700, -560, -420):
        prop('rack', -1236, y, LAB0, 0)
    prop('console', -1132, -260, LAB0, 180)
    item('ammo_nipper', -1150, -600, LAB0)
    speaker(-1184, -500, LAB0 + 120, 'sound/world/machine/harddisk.ogg', volume=0.5)
    speaker(-736, 400, LAB0 + 150, 'sound/world/machine/ventilation.ogg', volume=0.4)
    # --- vent shaft at the corridor end: pad back up to the surface (the shaft is also a way down)
    jumppad(-736, -216, LAB0, (-736, -560, 0), 200, 'vent_out')
    A(deco((-816, -400, 0), (-656, -384, 16), T('hazard'))); A(deco((-816, -192, 0), (-656, -176, 16), T('hazard')))
    A(deco((-816, -384, 0), (-800, -192, 16), T('hazard'))); A(deco((-672, -384, 0), (-656, -192, 16), T('hazard')))
    KEEP_OUT.append((-736, -288, 200))


def sign_at(c, face, tex, w, h):
    x, y, z = c
    if face in 'ns':
        y0 = y - (0 if face == 'n' else 0)
        A(sign_box((x - w / 2, y0, z - h / 2), (x + w / 2, y0 + 4, z + h / 2), T(tex), 512, 256 if h * 2 >= w else 128, back=NODRAW_NS, facing=face))
    else:
        A(sign_box((x, y - w / 2, z - h / 2), (x + 4, y + w / 2, z + h / 2), T(tex), 512, 256 if h * 2 >= w else 128, back=NODRAW_NS, facing=face))


# =================================================================================================== S-4 bunker + stairwell
def bunker():
    x0, x1, y0, y1 = AM.BK
    custom('bunker', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    t = 32
    d0, d1, dh = AM.BK_DOOR
    A(wall_boxes(x1 - t, x1, y0, y1, 0, AM.BK_H - 16, [(d0, d1, 0, dh)], WCLIP, axis='y'))
    A(wall_boxes(x0, x0 + t, y0, y1, 0, AM.BK_H - 16, [], WCLIP, axis='y'))
    A(box((x0 + t, y0, 0), (x1 - t, y0 + t, AM.BK_H - 16), WCLIP)); A(box((x0 + t, y1 - t, 0), (x1 - t, y1, AM.BK_H - 16), WCLIP))
    A(box((x0, y0, AM.BK_H - 16), (x1, y1, AM.BK_H), WCLIP))
    # stairwell: flight A (south half) from the bunker floor west down to -256, landing, flight B (north half) east to -512
    cs = {'top': T('concrete'), 'side': T('concrete'), 'bot': CAULK}
    A(stairs(-1792, -928, -1280, -768, -256, 0, 'e', cs, base=LAB0))
    # stairs() rises toward run_dir from z0: flight A must fall to the west => rises east from -256 at x -1792 to 0 at -1280
    A(box((-1888, -928, LAB0), (-1792, -608, -256), cs))
    A(stairs(-1792, -768, -1280, -608, LAB0, -256, 'w', cs, base=LAB0))
    # rail between the halves above flight B's ceiling is the bunker floor; light the well
    light(-1500, -768, -80, 420, '1 0.85 0.6'); light(-1500, -688, -380, 420, '1 0.85 0.6')
    light((x0 + x1) / 2, (y0 + y1) / 2 + 80, 180, 380, '1 0.85 0.6')
    item('holdable_bambam', -1230, -650, 0)
    # roof (pad from the north), satellite dish dressing
    jumppad(-1408, -440, 0, (-1408, -800, AM.BK_H), 430, 'bunker_roof')
    item('ammo_pumper', -1560, -860, AM.BK_H)
    item('item_armor_shard', -1260, -700, AM.BK_H)
    sign_at((x1 + 1, -620, 120), 'e', 'sign_s4', 160, 80)
    KEEP_OUT.append(((x0 + x1) / 2, (y0 + y1) / 2, 360))


# =================================================================================================== control tower
def tower():
    cx, cy = AM.TW
    custom('tower', cx, cy, 0)
    s, c, t = AM.TW_SHAFT, AM.TW_CAB, 32
    x0, x1, y0, y1 = cx - s, cx + s, cy - s, cy + s
    d0, d1, dh = AM.TW_DOOR
    F = AM.TW_FLOOR
    A(wall_boxes(x0, x0 + t, y0, y1, 0, F - 16, [(d0, d1, 0, dh)], WCLIP, axis='y'))
    A(wall_boxes(x1 - t, x1, y0, y1, 0, F - 16, [], WCLIP, axis='y'))
    A(box((x0 + t, y0, 0), (x1 - t, y0 + t, F - 16), WCLIP)); A(box((x0 + t, y1 - t, 0), (x1 - t, y1, F - 16), WCLIP))
    # cab floor slab (visible) with the stair hole over flight 4
    fl = {'top': T('concrete_dark'), 'bot': T('concrete'), 'side': T('concrete')}
    hole = (x0 + t, y0 + t + 96, x0 + t + 96, y1 - t)        # x 1504..1600, y 768..1120 (over flight 4)
    for (a, b_, cc, d) in sub_rects((cx - c, cy - c, cx + c, cy + c), [hole]):
        A(box((a, b_, F - 16), (cc, d, F), fl))
    # sill walls, roof slab with the hatch
    A(box((cx - c, cy - c, F), (cx + c, cy - c + t, AM.TW_SILL), WCLIP)); A(box((cx - c, cy + c - t, F), (cx + c, cy + c, AM.TW_SILL), WCLIP))
    A(box((cx - c, cy - c + t, F), (cx - c + t, cy + c - t, AM.TW_SILL), WCLIP)); A(box((cx + c - t, cy - c + t, F), (cx + c, cy + c - t, AM.TW_SILL), WCLIP))
    hx0, hx1, hy0, hy1 = AM.TW_HATCH
    ro = c + 22 + 24
    for (a, b_, cc, d) in sub_rects((cx - ro, cy - ro, cx + ro, cy + ro), [(hx0, hy0, hx1, hy1)]):
        A(box((a, b_, AM.TW_ROOF_BOT), (cc, d, AM.TW_ROOF), WCLIP))
    A(box((cx - 16, cy - 16, AM.TW_ROOF), (cx + 16, cy + 16, AM.TW_ROOF + 330), WCLIP))      # antenna mast
    # square spiral stairs (16u) round the core: S wall east, E wall north, N wall west, W wall south
    cs = {'top': T('concrete'), 'side': T('concrete_dark'), 'bot': T('concrete_dark')}
    ix0, ix1, iy0, iy1 = x0 + t, x1 - t, y0 + t, y1 - t         # 1504..1952, 672..1120
    A(stairs(ix0 + 96, iy0, ix1 - 96, iy0 + 96, 0, 128, 'e', cs))
    A(box((ix1 - 96, iy0, 0), (ix1, iy0 + 96, 128), cs))
    A(stairs(ix1 - 96, iy0 + 96, ix1, iy1 - 96, 128, 256, 'n', cs, thick=32))
    A(box((ix1 - 96, iy1 - 96, 224), (ix1, iy1, 256), cs))
    A(stairs(ix0 + 96, iy1 - 96, ix1 - 96, iy1, 256, 384, 'w', cs, thick=32))
    A(box((ix0, iy1 - 96, 352), (ix0 + 96, iy1, 384), cs))
    A(stairs(ix0, iy0 + 96, ix0 + 96, iy1 - 96, 384, F - 16, 's', cs, thick=32))
    # console banks in the cab (match the MD3)
    A(box((cx - c + 40, cy - c + 34, F), (cx + c - 40, cy - c + 90, F + 56), WCLIP))
    A(box((cx + c - 90, cy - c + 120, F), (cx + c - 34, cy + c - 120, F + 56), WCLIP))
    weapon('betty', cx - 100, cy + 150, F, 'black')
    item('ammo_betty', cx + 120, cy + 230, F)
    item('ammo_bubbleg', cx - 230, cy - 200, F)
    # hatch pad -> roof
    jumppad((hx0 + hx1) / 2, (hy0 + hy1) / 2, F, (cx - 60, cy + 60, AM.TW_ROOF), 920, 'tower_roof')
    item('holdable_floater', cx + 150, cy - 150, AM.TW_ROOF)
    item('ammo_splasher', cx - 180, cy + 200, AM.TW_ROOF)
    # base: health in the core, lights
    M.ent('station_health', (cx + 60, cy + 40, 0), angle=180)
    light(cx, cy, 300, 500, '1 0.9 0.75'); light(cx, cy, 120, 300, '1 0.9 0.75')
    light(cx, cy, F + 120, 450, '0.7 1 0.8')
    speaker(cx, cy, F + 80, 'sound/world/human/plane_radio.ogg', volume=0.6)
    timer_sound(cx, cy, AM.TW_ROOF + 300, 'sound/world/machine/dingdong.ogg', 'tw_bell', 50, 20)
    KEEP_OUT.append((cx, cy, 460))


# =================================================================================================== water tower
def watertower():
    cx, cy = AM.WT
    custom('watertower', cx, cy, 0)
    L = AM.WT_LEG
    for (sx, sy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        bx, by = cx + sx * (L + 40), cy + sy * (L + 40)
        tx, ty = cx + sx * L * 0.82, cy + sy * L * 0.82
        A(hull([(x, y, 0) for (x, y) in ngon(bx, by, 14, 8)] + [(x, y, AM.WT_Z0 - 16) for (x, y) in ngon(tx, ty, 14, 8)], WCLIP, round_pts=False))
    R = AM.WT_TANK_R
    A(cyl(cx, cy, R - 4, AM.WT_Z0, AM.WT_Z1, WCLIP, 16, phase=0))
    A(hull([(x, y, AM.WT_Z1) for (x, y) in ngon(cx, cy, R + 12, 16, 0)] + [(x, y, AM.WT_CONE - 8) for (x, y) in ngon(cx, cy, 48, 8)], WCLIP, round_pts=False))
    A(hull([(x, y, z) for (x, y) in ngon(cx, cy, R - 4, 16, 0) for z in (AM.WT_Z0 - 16, AM.WT_Z0)], WCLIP, round_pts=False))
    for k in range(16):
        A(sector(cx, cy, k, 16, R - 4, AM.WT_RING, AM.WT_Z0 - 8, AM.WT_Z0, AM.WT_Z0 - 8, AM.WT_Z0, WCLIP))
    jumppad(cx - 470, cy, 0, (cx - 300, cy, AM.WT_Z0), AM.WT_Z0 + 200, 'tank_ring')
    jumppad(cx - 312, cy, AM.WT_Z0, (cx - 60, cy, AM.WT_CONE - 20), AM.WT_CONE + 300, 'tank_roof', glow=False)
    weapon('balloony', cx, cy, AM.WT_CONE - 8, 'green')
    item('ammo_balloony', cx, cy - 290, AM.WT_Z0)
    item('ammo_imperius', cx + 290, cy, AM.WT_Z0)
    light(cx, cy, AM.WT_Z0 - 60, 400, '1 0.9 0.7'); light(cx, cy, AM.WT_CONE + 140, 300, '0.8 0.85 1')
    speaker(cx, cy, AM.WT_Z1, 'sound/world/ambient/metal_creaking.ogg', volume=0.4)
    KEEP_OUT.append((cx, cy, 520))


# =================================================================================================== radar station
def radar():
    x0, x1, y0, y1, h = AM.RD_PLAT
    cx, cy = AM.RD
    custom('radar_base', cx, cy, 0)
    A(box((x0, y0, 0), (x1, y1, h), {'top': T('plate'), 'side': T('concrete'), 'bot': CAULK}))
    A(stairs(-1984, 576, -1824, 960, 0, h, 'n', {'top': T('concrete'), 'side': T('concrete_dark'), 'bot': CAULK}))
    A(cyl(round(cx), round(cy), AM.RD_PED_R, h, AM.RD_PED_Z - 6, WCLIP, 12))
    A(box((cx + AM.RD_PED_R + 30, cy - 40, h), (cx + AM.RD_PED_R + 110, cy + 40, h + 80), WCLIP))
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, AM.RD_DISH_Z - 8), (cx + 8, cy + 8, AM.RD_DISH_Z + 8), ORIGIN),
                                    box((cx - 4, cy - 4, AM.RD_DISH_Z + 20), (cx + 4, cy + 4, AM.RD_DISH_Z + 28), NODRAW_NS)],
          model2=AM.PLACE['radar_dish'][0], speed=30, spawnflags=0, dmg=0)
    weapon('bubbleg', cx + 150, cy + 150, h, 'blue')
    item('item_jumper', cx - 170, cy - 160, h)
    item('ammo_bubbleg', cx - 160, cy + 170, h)
    light(cx, cy, h + 320, 500, '0.8 0.9 1')
    speaker(cx, cy, h + 200, 'sound/world/machine/transformer.ogg', volume=0.4)
    KEEP_OUT.append((cx, cy, 420)); KEEP_OUT.append((-1904, 760, 140))


# =================================================================================================== quonset huts
def huts():
    R, L, t = AM.HUT_R, AM.HUT_L, AM.HUT_T
    n = 12
    for i, (hx, hy) in enumerate(AM.HUTS):
        custom('quonset', hx, hy, 0)
        angs = np.linspace(0, math.pi, n + 1)
        for k in range(n):
            a0, a1 = angs[k], angs[k + 1]
            pts = [(hx + r * math.cos(a), y, r * math.sin(a)) for a in (a0, a1) for r in (R - t, R) for y in (hy - L, hy + L)]
            A(hull(pts, WCLIP, round_pts=False))
        # end walls under the inner chords with the door + two windows cut out
        for sy in (-1, 1):
            ya, yb = (hy + L - t, hy + L) if sy > 0 else (hy - L, hy - L + t)
            pieces = []
            for k in range(n):
                a0, a1 = angs[k], angs[k + 1]
                xa, za = (R - t) * math.cos(a0), (R - t) * math.sin(a0)
                xb, zb = (R - t) * math.cos(a1), (R - t) * math.sin(a1)
                poly = [(xa, 0), (xb, 0), (xb, zb), (xa, za)]
                uniq = [p for j, p in enumerate(poly) if all(abs(p[0] - q[0]) > 0.1 or abs(p[1] - q[1]) > 0.1 for q in poly[:j])]
                if len(uniq) < 3: continue
                pieces.append(hull([(hx + px, y, pz) for (px, pz) in uniq for y in (ya, yb)], WCLIP, round_pts=False))
            cutters = [box((hx + a, ya - 1, z0), (hx + b, yb + 1, z1), CAULK) for (a, b, z0, z1) in ((-64, 64, 0, 160), (-170, -100, 80, 140), (100, 170, 80, 140))]
            A(carve_all(pieces, cutters))
        # pad to the roof (east side) + items
        jumppad(hx + R + 110, hy - 120, 0, (hx + 50, hy - 120, R), R + 190, f'hut{i}_roof')
        light(hx, hy, R - 60, 380, '1 0.8 0.55')
        KEEP_OUT.append((hx, hy, 420))
    # hut A: bunks + Bubble G; hut B: health + lockers
    ax, ay = AM.HUTS[0]
    for y in (ay - 170, ay + 70):
        prop('bunk', ax - 140, y, 0, 90)
        prop('bunk', ax + 140, y, 0, 90)
    weapon('bubbleg', ax, ay + 160, 0, 'blue')
    item('ammo_bubbleg', ax + 40, ay - 250, 0)
    item('item_speedy', ax, ay + 60, R)
    bx, by = AM.HUTS[1]
    M.ent('station_health', (bx + 140, by + 120, 0), angle=180)
    prop('lockers', bx - 120, by - 140, 0, 0)
    prop('bunk', bx + 140, by - 160, 0, 90)
    item('ammo_pumper', bx - 60, by + 180, 0)
    item('ammo_nipper', bx, by - 60, R)
    speaker(ax, ay, 120, 'sound/world/human/snoring.ogg', volume=0.5)


# =================================================================================================== black triangle + airstairs
def jet():
    cx, cy = AM.JET
    custom('jet', cx, cy, 0)
    A(hull([(cx + x, cy + y, z) for (x, y, z) in AM.jet_collision_points()], WCLIP, round_pts=False))
    for (gx, gy) in ((AM.JET_NOSE + 170, 0), (AM.JET_TAIL - 110, -200), (AM.JET_TAIL - 110, 200)):
        A(box((cx + gx - 16, cy + gy - 28, 0), (cx + gx + 16, cy + gy + 28, 90), WCLIP))
    # boarding stairs at the trailing edge (rising west onto the wing)
    ax, ay = cx + AM.JET_TAIL + 72 + 256, cy - 140
    custom('airstairs', ax, ay, 0)
    cs = {'top': WCLIP, 'side': WCLIP, 'bot': WCLIP}
    A(stairs(ax - 256, ay - 64, ax, ay + 64, 0, 128, 'w', cs))
    A(box((ax - 320, ay - 64, 20), (ax - 256, ay + 64, 128), WCLIP))
    weapon('pumper', cx + 20, cy + 60, AM.JET_APEX - 14, 'green')
    item('ammo_pumper', cx - 180, cy - 40, 170)
    light(cx, cy, 40, 380, '1 0.6 0.35')
    light(cx, cy, AM.JET_APEX + 220, 420, '0.85 0.9 1')
    speaker(cx, cy, 60, 'sound/world/machine/jet_idle.ogg', volume=0.4)
    KEEP_OUT.append((cx, cy, 520)); KEEP_OUT.append((ax - 160, ay, 200))


# =================================================================================================== crash site
def crash():
    cx, cy = AM.CR
    custom('saucer_crash', cx, cy, 0)
    pts = [(cx + p[0], cy + p[1], p[2]) for p in AM.crash_collision_points()]
    b = hull(pts, WCLIP, round_pts=False)
    floor = -AM.CR_D
    P = [(np.asarray(n), d) for (n, d) in b.planes()] + [(np.array([0, 0, -1.0]), -floor)]
    V = planes_verts(P)
    A(brush_from_planes(P, WCLIP))
    top = V[np.argmax(V[:, 2])]
    # tractor beam: trigger round the dome top -> hangar roof
    tx, ty, tz = float(top[0]), float(top[1]), float(top[2])
    AM.BEAM_FOOT_W = tz
    trig = box((tx - 44, ty - 44, tz + 8), (tx + 44, ty + 44, tz + 80), TRIG)
    push(trig, (tx, ty, tz + 32), (0, 760, AM.HG_RIDGE), 1150, 'tractor_beam')
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, AM.SCOUT_Z - 8), (cx + 8, cy + 8, AM.SCOUT_Z + 8), ORIGIN),
                                    box((cx - 4, cy - 4, AM.SCOUT_Z + 40), (cx + 4, cy + 4, AM.SCOUT_Z + 48), NODRAW_NS)],
          model2=AM.IQM['scout'], speed=12, spawnflags=0, dmg=0)
    light(cx, cy, AM.SCOUT_Z - 120, 900, '0.4 1 0.55')
    light(tx, ty, tz + 60, 400, '0.4 1 0.55')
    speaker(tx, ty, tz + 100, 'sound/world/machine/portal_idle.ogg', volume=0.6)
    speaker(cx, cy, 0, 'sound/world/machine/electric_sparks.ogg', volume=0.4)
    # cordon round the rim, evidence crates, floodlight stand, a body bag ... and a grey who did not make it
    for a in range(0, 360, 30):
        x, y = ang_pt(cx, cy, AM.CR_R0 + 60, a)
        if not any(math.hypot(x - kx, y - ky) < kr for (kx, ky, kr) in KEEP_OUT):
            A(box((round(x) - 4, round(y) - 4, 0), (round(x) + 4, round(y) + 4, 80), T('hazard')))
    for (x, y, a, nm) in ((cx - 560, cy - 470, 20, 'crate96'), (cx + 700, cy + 100, 70, 'crate64'), (cx - 720, cy + 160, 10, 'crate64')):
        prop(nm, x, y, 0, a)
    mdl_c('ente/deadalienA.md3', cx + 560, cy - 470, 0, 3.0, 120)
    item('item_jumper', cx - 118, cy - 324, floor)
    item('ammo_imperius', cx + 120, cy + 330, floor)
    item('ammo_bubbleg', cx + 520, cy - 120, 0)
    KEEP_OUT.append((cx, cy, AM.CR_R0 + 80))


# =================================================================================================== mothership (secret)
def mothership():
    z0, z1, R = MS_Z, MS_Z + 448, 640
    W = 32
    ap = T('alien_panel')
    n = 8
    for k in range(n):
        am = (k + 1) * 45
        rx, ry = math.cos(math.radians(am)), math.sin(math.radians(am))
        def tf(nn, rx=rx, ry=ry):
            return ap if (nn[0] * rx + nn[1] * ry) < -0.5 else CAULK
        A(hull([(x, y, z) for a in (k * 45 + 22.5, (k + 1) * 45 + 22.5) for r in (R, R + W) for (x, y) in [ang_pt(0, 0, r, a)] for z in (z0, z1)],
               tf, detail=False, round_pts=False))
    A(hull([(x, y, z) for (x, y) in [ang_pt(0, 0, R + W, k * 45 + 22.5) for k in range(8)] for z in (z0 - W, z0)],
           {'top': T('alien_floor'), 'side': CAULK, 'bot': CAULK}, detail=False, round_pts=False))
    A(hull([(x, y, z) for (x, y) in [ang_pt(0, 0, R + W, k * 45 + 22.5) for k in range(8)] for z in (z1, z1 + W)],
           {'bot': ap, 'side': CAULK, 'top': CAULK}, detail=False, round_pts=False))
    for f in M.world[-2].faces:
        if f.tex == T('alien_floor'): f.sc = (2 * (R + W) / 512, 2 * (R + W) / 512); f.off = (((R + W) / f.sc[0]) % 512, ((R + W) / f.sc[1]) % 512)
    yw = R * math.cos(math.radians(22.5))
    A(sign_box((-260, yw - 30, z0 + 120), (260, yw - 26, z0 + 380), T('earth_window'), 512, 256, back=NODRAW_NS, facing='s'))
    A(sign_box((-200, -yw + 26, z0 + 300), (200, -yw + 30, z0 + 400), T('sign_mothership'), 512, 256, back=NODRAW_NS, facing='n'))
    M.ent('misc_teleporter_dest', (0, -420, z0 + 24), targetname='ms_in', angle=90)
    item('item_padpower', 0, 200, z0)
    item('item_revival', -280, 60, z0)
    item('holdable_killerducks', 280, 60, z0)
    item('ammo_imperius', -220, -220, z0)
    item('ammo_splasher', 220, -220, z0)
    # greys at their consoles, the energy core spinning over the middle
    for (x, y, a) in ((-380, 260, -40), (380, 260, 220)):
        prop('console', x, y, z0, a)
        prop('alien', x + 150 * math.cos(math.radians(a)), y + 150 * math.sin(math.radians(a)), z0, a, solid=True)
    cz = z0 + 300
    M.ent('func_rotating', brushes=[box((-8, -8, cz - 8), (8, 8, cz + 8), ORIGIN), box((-4, -4, cz - 4), (4, 4, cz + 4), NODRAW_NS)],
          model2=AM.PLACE['mother_core'][0], speed=35, spawnflags=0, dmg=0)
    # exit teleporter back to the apron
    mdl_c('pad_teleporter/padtp_yellow.md3', 0, 420, z0, 1.0, 0)
    M.ent('trigger_teleport', brushes=[box((-36, 370, z0 + 2), (36, 470, z0 + 90), TRIG)], target='ms_out')
    M.ent('misc_teleporter_dest', (640, 120, 24), targetname='ms_out', angle=0)
    light(0, 0, z0 + 400, 700, '0.6 1 0.9'); light(0, 0, z0 + 100, 400, '0.8 0.5 1')
    speaker(0, 0, z0 + 300, 'sound/world/machine/portal_idle.ogg', volume=0.8)
    speaker(0, 0, z0 + 300, 'sound/world/misc/strange_signal.ogg', volume=0.5)


# =================================================================================================== yards, gate, scatter
def yards():
    # ---- fuel yard (east): two tanks on saddles, a shipping container with crate steps to its roof
    for (x, y) in ((1792, -352), (1792, -96)):
        custom('fueltank', x, y, 0)
        A(hull([(x + sx, y + 112 * math.cos(a), 144 + 112 * math.sin(a)) for sx in (-250, 250) for a in np.linspace(0, 2 * math.pi, 9)[:-1]],
               WCLIP, round_pts=False))
        for xs in (-150, 150):
            A(box((x + xs - 20, y - 70, 0), (x + xs + 20, y + 70, 32), WCLIP))
        KEEP_OUT.append((x, y, 300))
    cxn, cyn = 1680, 288
    custom('container', cxn, cyn, 0)
    A(box((cxn - 192, cyn - 80, 0), (cxn + 192, cyn - 74, 160), WCLIP)); A(box((cxn - 192, cyn + 74, 0), (cxn + 192, cyn + 80, 160), WCLIP))
    A(box((cxn + 186, cyn - 74, 0), (cxn + 192, cyn + 74, 160), WCLIP)); A(box((cxn - 192, cyn - 74, 154), (cxn + 186, cyn + 74, 160), WCLIP))
    A(box((cxn - 192, cyn - 74, 0), (cxn + 186, cyn + 74, 4), {'top': T('plate'), 'side': CAULK, 'bot': CAULK}))
    for i, h in enumerate((128, 96, 64, 32)):
        y = cyn + 88 + i * 56
        A(box((cxn + 100, y, 0), (cxn + 180, y + 56, h), T('crate')))
    item('ammo_betty', cxn + 40, cyn, 160)
    item('item_armor_shard', cxn - 80, cyn, 4)
    KEEP_OUT.append((cxn, cyn, 320))
    for (x, y, a) in ((1460, -460, 20), (1470, 40, 80)):
        prop('forklift', 1480, -600, 0, 0) if (x, y) == (1460, -460) else prop('crate96', x, y, 0, a)
    for (x, y, nm) in ((1960, 20, 'drum_yellow'), (2010, 60, 'drum_yellow'), (1990, -500, 'drum_rust'), (2040, -460, 'drum_blue'),
                       (1560, 120, 'drum_green')):
        prop(nm, x, y, 0, 0)
    # ---- back lot (north of the hangar): generator, humvees, crates, drums
    custom('generator', -380, 1900, 0)
    A(box((-540, 1830, 0), (-220, 1970, 150), WCLIP))
    prop('humvee', 420, 1880, 0, 10)
    for (x, y, a, nm) in ((-900, 1900, 10, 'crate96'), (-1020, 1860, 40, 'crate64'), (60, 1920, 0, 'crate96'), (-1300, 1880, 0, 'crate96')):
        prop(nm, x, y, 0, a)
    prop('crate64', -900, 1900, 96, 25)
    for (x, y, nm) in ((800, 1900, 'drum_rust'), (850, 1930, 'drum_rust'), (840, 1846, 'drum_green')):
        prop(nm, x, y, 0, 0)
    item('ammo_balloony', 220, 1960, 0)
    item('ammo_nipper', -700, 1960, 0)
    # ---- gate (west): booth with a TV inside, boom barrier over the road, black mailbox, "AREA 51" sign
    bx, by = -2048, 224
    custom('booth', bx, by, 0, angle=180)
    h = 96
    A(wall_boxes(bx - h, bx + h, by - h, by - h + 12, 0, 176, [(bx - 40, bx + 40, 0, 150)], WCLIP, axis='x'))
    A(wall_boxes(bx - h, bx + h, by + h - 12, by + h, 0, 176, [(bx - 64, bx + 64, 80, 150)], WCLIP, axis='x'))
    A(wall_boxes(bx - h, bx - h + 12, by - h + 12, by + h - 12, 0, 176, [(by - 64, by + 64, 80, 150)], WCLIP, axis='y'))
    A(wall_boxes(bx + h - 12, bx + h, by - h + 12, by + h - 12, 0, 176, [(by - 64, by + 64, 80, 150)], WCLIP, axis='y'))
    A(box((bx - h - 24, by - h - 24, 176), (bx + h + 24, by + h + 24, 192), WCLIP))
    mdl_c('padtv/padtv2.md3', bx + 40, by + 60, 0, 0.25, 270)
    jumppad(bx + 220, by + 40, 0, (bx, by + 40, 192), 400, 'booth_roof')
    item('ammo_boaster', bx, by, 192)
    custom('boom', -1880, 64, 0, angle=270)
    A(box((-1904, 40, 0), (-1856, 88, 96), WCLIP))
    custom('mailbox', -2180, -330, 0, lit=False)
    A(box((-2190, -340, 0), (-2170, -320, 90), WCLIP))
    A(sign_box((-1980, -380, 40), (-1700, -376, 180), T('sign_area51'), 512, 256, back=NODRAW_NS, facing='n'))
    A(box((-1980, -380, 0), (-1972, -372, 40), T('steel'))); A(box((-1708, -380, 0), (-1700, -372, 40), T('steel')))
    light(bx, by, 150, 300, '1 0.85 0.6'); light(-1880, 0, 200, 400, '1 0.8 0.5')
    timer_sound(-2100, 0, 120, 'sound/world/animal/dog_bark2.ogg', 'dogs', 40, 20, volume=0.5)
    KEEP_OUT.append((bx, by, 220)); KEEP_OUT.append((-1880, -100, 260)); KEEP_OUT.append((-1840, -380, 160))


def rbox(x, y, ang, lmn, lmx, tex):
    """box given in a local frame (origin x, y, yaw ang in 0/90/180/270) -> world axis-aligned brush"""
    a = math.radians(ang); c, s_ = round(math.cos(a)), round(math.sin(a))
    xs = [x + px * c - py * s_ for px in (lmn[0], lmx[0]) for py in (lmn[1], lmx[1])]
    ys = [y + px * s_ + py * c for px in (lmn[0], lmx[0]) for py in (lmn[1], lmx[1])]
    return box((min(xs), min(ys), lmn[2]), (max(xs), max(ys), lmx[2]), tex)


def container_at(x, y, ang, steps=True, loot=None):
    """walk-in shipping container (open at local -x) with crate steps up its local +y side to the roof"""
    custom('container', x, y, 0, angle=ang)
    for (mn, mx) in (((-192, -80, 0), (192, -74, 160)), ((-192, 74, 0), (192, 80, 160)), ((186, -74, 0), (192, 74, 160)),
                     ((-192, -74, 154), (186, 74, 160))):
        A(rbox(x, y, ang, mn, mx, WCLIP))
    A(rbox(x, y, ang, (-192, -74, 0), (186, 74, 4), {'top': T('plate'), 'side': CAULK, 'bot': CAULK}))
    if steps:
        for i, h in enumerate((128, 96, 64, 32)):
            A(rbox(x, y, ang, (100, 88 + i * 56, 0), (180, 88 + (i + 1) * 56, h), T('crate')))
    if loot:
        a = math.radians(ang)
        item(loot, x + 60 * math.cos(a), y + 60 * math.sin(a), 160)
    KEEP_OUT.append((x, y, 330))


def crate_stack(x, y, ang=0):
    prop('crate96', x, y, 0, ang)
    a = math.radians(ang)
    prop('crate96', x + 96 * math.cos(a), y + 96 * math.sin(a), 0, ang)
    prop('crate64', x, y, 96, ang + 15)
    KEEP_OUT.append((x + 48 * math.cos(a), y + 48 * math.sin(a), 150))


def cover():
    """big cover in the open band between the hangar, the crater and the outbuildings (breaks the long sightlines)"""
    container_at(-430, -330, 0, loot='ammo_balloony')
    container_at(540, -330, 90, loot='item_armor_shard')
    container_at(-1420, 640, 90, loot='ammo_boaster')
    container_at(1200, 1330, 0)
    container_at(-1200, -280, 180, steps=False)
    # fuel bowser + crate stacks
    custom('fueltank', 960, -230, 0, angle=90)
    A(hull([(960 + 112 * math.cos(t), -230 + sy, 144 + 112 * math.sin(t)) for sy in (-250, 250) for t in np.linspace(0, 2 * math.pi, 9)[:-1]],
           WCLIP, round_pts=False))
    for ys in (-150, 150):
        A(box((960 - 70, -230 + ys - 20, 0), (960 + 70, -230 + ys + 20, 32), WCLIP))
    KEEP_OUT.append((960, -230, 300))
    for (x, y, a) in ((-1000, -560, 0), (1230, -100, 90), (-160, 460, 0), (2120, 560, 0), (-2050, 1500 - 950, 90)):
        crate_stack(x, y, a)
    # on the runway: a generator cart and a tug with crates (low cover along the strip)
    for gx in (-150, 1250):
        custom('generator', gx, -1890, 0)
        A(box((gx - 160, -1960, 0), (gx + 160, -1820, 150), WCLIP))
        KEEP_OUT.append((gx, -1890, 220))
    crate_stack(600, -1930, 0)
    crate_stack(1900, -1880, 0)
    # the far lanes (runway, back lot) and the hangar side doors: barriers / crates across them
    for (x, y) in ((-480, -1960), (330, -1880), (950, -1960), (1700, -1960), (-1150, 1940), (130, 1940), (1550, 1940), (-2000, 1940)):
        prop('barrier', x, y, 0, 90); KEEP_OUT.append((x, y, 100))
    prop('crate96', -760, 1640, 0, 10)
    # apron in front of the hangar door: a humvee and crates parked on the taxi line
    prop('humvee', 420, 300, 0, 15); KEEP_OUT.append((420, 300, 180))
    crate_stack(-640, 400, 0)
    prop('humvee', -1650, 330, 0, 80); KEEP_OUT.append((-1650, 330, 180))
    crate_stack(1850, -1450, 0)
    crate_stack(-520, -1600, 0)
    prop('crate96', 700, 1630, 0, 30)


def floodlights():
    spots = [(-1200, 380, 'searchlight_a'), (1240, -620, 'searchlight_b'), (-1700, 1930, None), (2150, 1350, None), (-2160, -1000, None),
             (1060, 1920, None)]
    for (x, y, sl) in spots:
        custom('floodlight', x, y, 0)
        A(box((x - 80, y - 80, 0), (x + 80, y + 80, 24), WCLIP))
        A(box((x - 40, y - 40, 24), (x + 40, y + 40, AM.FL_H), WCLIP))
        light(x, y, AM.FL_H - 40, 1800, '1 0.95 0.8')
        if sl:
            z = AM.FL_H + 160
            M.ent('func_rotating', brushes=[box((x - 8, y - 8, z - 8), (x + 8, y + 8, z + 8), ORIGIN), box((x - 4, y - 4, z + 30), (x + 4, y + 4, z + 38), NODRAW_NS)],
                  model2=AM.IQM[sl], speed=18 if sl.endswith('a') else -14, spawnflags=0, dmg=0)
        KEEP_OUT.append((x, y, 160))


def scatter():
    rng = np.random.default_rng(23)
    def free(x, y, r):
        return all(math.hypot(x - kx, y - ky) >= kr + r for (kx, ky, kr) in KEEP_OUT) and abs(x) < XW - r - 40 and abs(y) < YN - r - 40
    # jersey barriers and sandbag nests along the apron and roads (cover)
    for (x, y, a) in ((-700, 120, 0), (-430, -40, 90), (420, 60, 0), (700, -140, 90), (-150, 380, 0), (250, 380, 0),
                      (900, -360, 30), (-900, -380, 150), (1250, -900, 90), (1200, 260, 90), (-1500, 120, 0), (-1300, -100, 90),
                      (0, -300, 0), (600, -620, 60), (-600, -620, 120)):
        if free(x, y, 90): prop('barrier', x, y, 0, a); KEEP_OUT.append((x, y, 100))
    for (x, y, a) in ((-260, 150, 10), (300, -60, 170), (1000, 380, 90), (-1000, 200, 80), (800, -1500, 0), (-400, -1600, 30)):
        if free(x, y, 170): prop('sandbags', x, y, 0, a); KEEP_OUT.append((x, y, 180))
    for (x, y, a, nm) in ((-100, -60, 30, 'crate96'), (120, 200, 10, 'crate64'), (560, 260, 0, 'crate96'), (-560, 300, 20, 'crate96'),
                          (-600, 230, 50, 'crate64'), (900, -800, 15, 'crate96'), (-850, -950, 35, 'crate96'), (1500, 700 - 950, 0, 'crate64'),
                          (-1600, 500, 25, 'crate96'), (-2000, -700, 10, 'crate96'), (2000, 900 - 1700, 40, 'crate96')):
        if free(x, y, 80): prop(nm, x, y, 0, a); KEEP_OUT.append((x, y, 90))
    for (x, y, nm) in ((-250, -150, 'drum_yellow'), (-210, -190, 'drum_yellow'), (700, 160, 'drum_blue'), (-1000, -300, 'drum_rust'),
                       (1300, -1400, 'drum_rust'), (-200, -1900, 'drum_green'), (500, -1300, 'drum_yellow')):
        if free(x, y, 30): prop(nm, x, y, 0, 0); KEEP_OUT.append((x, y, 40))
    prop('humvee', 860, 30, 0, 100) if free(860, 30, 160) else None
    KEEP_OUT.append((860, 30, 180))
    prop('humvee', -1500, -260, 0, 20) if free(-1500, -260, 160) else None
    KEEP_OUT.append((-1500, -260, 180))
    # desert flora: joshua trees, catalog cactus, tumbleweeds, rocks
    sand_ok = lambda x, y: region_tex(x, y) == T('sand') and math.hypot(x - AM.CR[0], y - AM.CR[1]) > AM.CR_R0 + 60
    n_j = 0
    for (x, y) in ((-2050, 1700), (-1500, 1800), (2100, 400), (-2100, -300), (300, -1550), (1000, -300), (-1000, -1250), (-2100, 700),
                   (1500, 1900), (900, 1300), (-1300, 300), (700, -1100), (2150, -400), (-700, -1300)):
        if free(x, y, 120) and sand_ok(x, y):
            custom(f'joshua{1 + n_j % 3}', x, y, 0, angle=int(rng.uniform(0, 360)), lit=False)
            A(cyl(round(x), round(y), 14, 0, 300, WCLIP, 8))
            KEEP_OUT.append((x, y, 140)); n_j += 1
    for (x, y, s) in ((-1700, 1650, 1.2), (1300, 1750, 1.0), (-650, -1500, 1.1), (1950, -150, 1.2), (600, 1700, 1.0), (-2000, 1200, 1.1),
                      (-1250, 1300, 0.9), (400, -1800, 1.0)):
        if free(x, y, 70) and sand_ok(x, y):
            solid_mdl('pad_westernset/cactus.md3', x, y, 0, s, int(rng.uniform(0, 360)))
            KEEP_OUT.append((x, y, 80))
    for k, (x, y) in enumerate(((-1100, 1500), (1950, 1300 - 900), (-1700, -400), (800, -1650), (-300, -1950 + 200), (1700, 1500 - 1100))):
        if free(x, y, 120) and sand_ok(x, y):
            custom(f'rocks{1 + k % 3}', x, y, 0, angle=int(rng.uniform(0, 360)), lit=False)
            A(cyl(round(x), round(y), 60, 0, 50, WCLIP, 8))
            KEEP_OUT.append((x, y, 130))
    for _ in range(40):
        x, y = rng.uniform(-2150, 2150), rng.uniform(-1900, 1900)
        if free(x, y, 60) and sand_ok(x, y):
            custom('tumbleweed', x, y, 0, angle=int(rng.uniform(0, 360)), lit=False)
            KEEP_OUT.append((x, y, 70))
    # catalog extras: tyres by the motor pool, garbage bags by the huts, a raven on the radar stairs
    for (x, y, a) in ((1050, 520, 30), (1100, 470, 80)):
        if free(x, y, 50): mdl_c('pad_ddmix/backyard/tire.md3', x, y, 0, 0.35, a); KEEP_OUT.append((x, y, 60))
    for (x, y) in ((-1450, -1100), (-750, -1180)):
        if free(x, y, 60): solid_mdl('pad_ddmix/trashcan/garbage_bag_group.md3', x, y, 0, 0.9, 30); KEEP_OUT.append((x, y, 70))


def runway_lights():
    for x in range(-640, XW - 63, 192):
        for y in (-YN + 24, -1728 - 24):
            A(box((x - 6, y - 6, 0), (x + 6, y + 6, 10), {'top': T('glow_amber') if y > -1900 else T('glow_white'), 'side': T('steel'), 'bot': CAULK}))


def items_misc():
    item('ammo_nipper', 200, -200, 0)
    item('ammo_nipper', -1800, 480, 0)
    item('item_armor_shard', 0, 500, 0)
    item('item_armor_shard', -1700, 1700, 0)
    item('item_armor_shard', 2100, -1450, 0)
    item('ammo_boaster', 1420, 1520, 0)
    item('ammo_boaster', -760, -1040, 0)
    item('ammo_balloony', 1500, -1500, 0)
    item('ammo_betty', -2150, -700, 0)
    item('ammo_splasher', 600, 1900, 0)
    item('ammo_bubbleg', 900, -1150, 0)
    item('ammo_pumper', -1000, 1600 - 100, 0)
    item('item_climber', 2000, 1000 - 300, 0)
    item('holdable_bambam', 450, -1850, 0)
    item('item_speedy', 800, -1880, 0)


def spawns():
    for (x, y, a) in ((-600, 0, 30), (600, 100, 150), (-200, 1000, 270), (300, 700, 225), (-1900, -1750, 45), (1950, -1640, 135),
                      (-1250, 980, 0), (1300, 1100, 180), (-1900, 1850, 315), (2000, 0, 180), (-450, -1800, 90), (-650, 1790, 270),
                      (1250, -1300, 160), (-700, -1500, 80), (-1700, -100, 0), (1100, 1700, 230)):
        spawn(x, y, 0, a)


def sky_and_mood():
    # moonlight fill over the open ground; distant chopper, coyotes, crickets, wind
    for (x, y) in ((-1500, -1200), (0, -500), (1500, -700), (-1700, 700), (1600, 1600), (-400, 1900), (900, -1700), (-900, -1800)):
        light(x, y, 900, 900, '0.7 0.78 1')
    speaker(0, 0, 1500, 'sound/world/ambient/wind_night.ogg', volume=0.4)
    speaker(-1500, 1500, 200, 'sound/world/animal/cricket_chirp1.ogg', volume=0.4)
    speaker(1500, -1500, 200, 'sound/world/animal/cricket_chirp2.ogg', volume=0.4)
    timer_sound(-2200, -2000, 600, 'sound/world/animal/coyote_howl.ogg', 'coyote', 45, 25)
    timer_sound(2200, 1800, 900, 'sound/world/ambient/chopper_pass.ogg', 'chopper', 90, 40)
    timer_sound(0, -1900, 900, 'sound/world/ambient/plane_jet.ogg', 'jetpass', 75, 35)
    timer_sound(0, 0, 1900, 'sound/world/misc/strange_signal.ogg', 'ufo_sig', 60, 30, volume=0.4)
    # the UFO circling high over the base (IQM on a func_rotating round the map centre)
    z = AM.ORBIT_Z
    M.ent('func_rotating', brushes=[box((-8, -8, z - 8), (8, 8, z + 8), ORIGIN), box((-4, -4, z + 60), (4, 4, z + 68), NODRAW_NS)],
          model2=AM.IQM['orbiter'], speed=5, spawnflags=0, dmg=0)


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    for nm in AM.PLACE:
        import md3tool
        m = md3tool.load(os.path.join(OUT, AM.PLACE[nm][0]))
        V = np.concatenate([s['verts'] for s in m['surfaces']]) * AM.PLACE[nm][1] + [0, 0, AM.PLACE[nm][2]]
        PROP_BOUNDS[nm] = (V.min(0), V.max(0))
    hull_and_banks(); ground(); hangar(); lab(); bunker(); tower(); watertower(); radar(); huts(); jet(); crash(); mothership()
    yards(); cover(); floodlights(); runway_lights(); scatter(); items_misc(); spawns(); sky_and_mood()
    M.ent('info_player_intermission', (-1800, -1700, 900), angles='18 40 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/area51/build_area51.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
