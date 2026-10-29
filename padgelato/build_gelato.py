#!/usr/bin/env python3
"""Padman's Gelato Parlour - World of Padman FFA map generator (map 'wop_padgelato').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_gelato.py

Writes <OUT>/maps/wop_padgelato.map, textures/padgelato/*, models/padgelato/*, scripts/padgelato.shader and
scripts/wop_padgelato.arena.

Padman scale (~8u per cm, catalog models at 1.0): a retro 50s ice cream parlour. x east, y north, floor z 0, ceiling 2048.

  The giant cone    a triple-scoop waffle cone in a chrome stand in the middle: the scoop lift (func_plat) and a pad
                    up to the wafer rim (Imperius).
  Gelato counter    north: 8 tubs of gelato to drop into, sugar-cone stairs at both ends, the server aisle behind, a
                    high wall shelf (Betty).
  Soft-serve        west wall: walk into the cabinet (Boaster), stairs up to the drip-tray deck where swirls turn into
                    giant cones, pads onto the top (Balloony).
  Milkshake bar     east wall: bar stools, a blender spinning; the giant milkshake glass you can stand on (Pumper).
  Walk-in freezer   south-east: through the strip curtain; roof (Splasher). SECRET: jump into the Mystery Flavour tub
                    -> the Frozen Vault under the world.
  Chest freezer     south-west: climb the ice-cube steps and drop in (Bubble G).
  Shop              ice cream cart, topping jars, tables, sunny windows onto the street.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import gl_textures as TX
import gllib as bklib
import gl_shapes as SH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padgelato'
T = lambda n: 'padgelato/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floor': (1.0, 1.0), 'subway': (0.5, 0.5), 'wall_paint': (1.0, 1.0), 'frieze': (1.0, 1.0), 'ceiling': (1.0, 1.0),
             'skirting': (1.0, 0.75), 'wood_white': (0.5, 0.5), 'pavement': (1.0, 1.0), 'choc_wall': (1.0, 1.0), 'gold_tile': (1.0, 1.0),
             'sky': (1, 1), 'glass': (1, 1), 'cool_floor': (1.0, 1.0), 'shop_floor': (1.0, 1.0), 'lift': (1, 1), 'jumppad': (1, 1), 'rubber': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': TX.LONGNAME, '_ambient': '22', '_color': '1 0.95 0.9', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'})
A = M.add
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []
ROUTES = []
FOOT = []          # occupied volumes (x0, y0, x1, y1, z0, z1) for placement tests
RNG = np.random.default_rng(11)


# =================================================================================================== helpers
def occupy(x0, y0, x1, y1, z0, z1):
    FOOT.append((x0, y0, x1, y1, z0, z1))


def occupy_r(x, y, r, z0, z1): occupy(x - r, y - r, x + r, y + r, z0, z1)


def free(x, y, r, z0, z1, margin=4):
    if abs(x) > L.HX - r - 8 or abs(y) > L.HY - r - 8: return False
    for (a, b, c, d, e, f) in FOOT:
        if z1 <= e + 0.5 or z0 >= f - 0.5: continue
        dx = max(a - x, 0, x - c); dy = max(b - y, 0, y - d)
        if dx * dx + dy * dy < (r + margin) ** 2: return False
    return True


def near_free(x, y, r, z0, z1, search=240, step=24):
    if free(x, y, r, z0, z1): return (x, y)
    for d in range(step, search + 1, step):
        for k in range(16):
            a = k * math.pi / 8
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if free(px, py, r, z0, z1): return (round(px), round(py))
    return None


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


def cat_size(path, scale):
    b = BOUNDS['models/mapobjects/' + path]
    return [(b['max'][i] - b['min'][i]) * scale for i in range(3)]


def cat(path, x, y, z, scale=1.0, angle=None, clip=True, shrink=0.15, search=160, lit=False):
    """catalog model centred at (x, y) on surface z (nudged to a free spot); weapclip box when clip and big enough"""
    sx, sy, sz = cat_size(path, scale)
    r = max(sx, sy) / 2
    p = near_free(x, y, r, z, z + sz, search)
    if p is None: return None
    a = RNG.uniform(0, 360) if angle is None else angle
    kw = dict(spawnflags=4, _castshadows=1) if lit else {}
    e = mdl_c(path, p[0], p[1], z, scale, a, **kw)
    if clip and sz > 20:
        b = BOUNDS['models/mapobjects/' + path]
        ox, oy, oz = (float(v) for v in e['origin'].split())
        ar = math.radians(a); ca, sa = math.cos(ar), math.sin(ar)
        pts = []
        for px in (b['min'][0], b['max'][0]):
            for py in (b['min'][1], b['max'][1]):
                pts.append((ox + (px * ca - py * sa) * scale, oy + (px * sa + py * ca) * scale))
        c = np.mean(pts, 0)
        pts = [tuple(c + (np.array(q) - c) * (1 - shrink)) for q in pts]
        z1 = oz + b['max'][2] * scale - 2
        A(hull([(q[0], q[1], z) for q in pts] + [(q[0], q[1], z1) for q in pts], WCLIP, round_pts=False))
    occupy_r(p[0], p[1], r, z, z + sz)
    return p


def custom(name, x, y, zbase, angle=0, lit=True, mul=1.0, **kw):
    path, sc, zo = bklib.PLACE[name]
    sc, zo = sc * mul, zo * mul
    extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=1.0) if lit else {}
    extra.update(kw)
    return M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, **extra)


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


def prop_extent(name):
    import gl_props as BP
    r, h = 0.0, 0.0
    for (mn, mx) in BP.BOX.get(name, []):
        r = max(r, math.hypot(max(abs(mn[0]), abs(mx[0])), max(abs(mn[1]), abs(mx[1])))); h = max(h, mx[2])
    for (cx, cy, rr, z0, z1) in BP.CYL.get(name, []):
        r = max(r, math.hypot(cx, cy) + rr); h = max(h, z1)
    return r, h


def prop(name, x, y, z, ang=None, search=160, lit=True, clip=True, r=None, h=None, force=False):
    """custom prop (bk_props) with its weapclip collision, nudged to a free spot unless force"""
    import gl_props as BP
    r0, h0 = prop_extent(name)
    r = r if r is not None else max(r0, 20)
    h = h if h is not None else max(h0, 16)
    p = (x, y) if force else near_free(x, y, r, z, z + h, search)
    if p is None:
        print('no room for', name, (x, y, z)); return None
    a = RNG.uniform(0, 360) if ang is None else ang
    custom(name, p[0], p[1], z, a, lit=lit)
    if clip:
        for (mn, mx) in BP.BOX.get(name, []):
            lbox(p[0], p[1], z, a, mn, mx)
        ar = math.radians(a)
        for (cx, cy, rr, z0, z1) in BP.CYL.get(name, []):
            wx = p[0] + cx * math.cos(ar) - cy * math.sin(ar); wy = p[1] + cx * math.sin(ar) + cy * math.cos(ar)
            A(cyl(round(wx, 1), round(wy, 1), rr, z + z0, z + z1, WCLIP, 12 if rr > 40 else 8))
    occupy_r(p[0], p[1], r, z, z + h)
    return p


def light(x, y, z, val, color='1 0.92 0.8', **kw):
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
    occupy_r(x, y, 30, floor, floor + 40)


def weapon(w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(x), round(y), round(floor) + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, x, y, floor))
    occupy_r(x, y, 40, floor, floor + 48)


def spawn(x, y, floor, ang):
    p = near_free(x, y, 40, floor, floor + 64)
    if p is None: return
    M.ent('info_player_deathmatch', (round(p[0]), round(p[1]), round(floor) + 25), angle=round(ang) % 360)
    SPOTS['spawn'].append((p[0], p[1], floor))
    occupy_r(p[0], p[1], 40, floor, floor + 64)


def station(x, y, z, ang=0):
    M.ent('station_health', (round(x), round(y), round(z)), angle=ang)
    occupy_r(x, y, 64, z, z + 80)


def pad_target(o, land, apex):
    x, y, oz = o
    lx, ly, lz = land
    tu = math.sqrt(2 * (apex - oz) / 800); td = math.sqrt(2 * (apex - (lz + 24)) / 800)
    f = tu / (tu + td)
    return x + (lx - x) * f, y + (ly - y) * f


def jumppad(x, y, z, land, apex, name, glow=True):
    """launch pad (a glazed donut top, r 34) + trigger_push + target_position (the apex, t_up/(t_up+t_down) of the way)"""
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
    if glow: light(x, y, z + 48, 120, '1 0.6 0.8')
    occupy_r(x, y, 60, z, z + 90)


def route(name, a, b):
    ROUTES.append((name, a, b))


def clipped(brushes, tex=WCLIP):
    for b in brushes:
        for f in b.faces:
            f.tex = tex; f.sc = (0.5, 0.5)
        A(b)
        mn, mx = b.bounds()
        occupy(mn[0], mn[1], mx[0], mx[1], mn[2], mx[2])


def write_routes():
    with open(os.path.join(HERE, 'routes.txt'), 'w') as f:
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padgelato/routes.txt)\n'
                '# name: from x,y,z > to x,y,z   (z = floor height); generated by build_bakery.py\n')
        for (n, a, b) in ROUTES:
            f.write(f'{n + ":":18s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')


NONSOLID_TEX = ('trigger', 'nodraw_ns', 'origin', 'botclip', 'common/clip')


def fix_items():
    """move any pickup/spawn whose box starts in a solid to the nearest free spot with a floor under it"""
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
        for d in range(16, 200, 16):
            for k in range(16):
                a = k * math.pi / 8
                p = o + np.array([d * math.cos(a), d * math.sin(a), 0])
                if not blocked(p, lo, hi) and blocked(p + np.array([0, 0, lo[2] - 8]), np.array([-4, -4, -2]), np.array([4, 4, 2])):
                    e['origin'] = ' '.join(fmt([v]) for v in np.round(p)); moved.append((c, o.astype(int).tolist(), np.round(p).astype(int).tolist()))
                    done = True; break
            if done: break
        if not done: moved.append((c, o.astype(int).tolist(), 'STUCK'))
    return moved


# =================================================================================================== room shell
def wall_bands(r0, r1, z_lo, z_hi, axis, coord, side, holes=()):
    """one wall (structural): u span r0..r1 along `axis` ('x' or 'y'), thickness outward from `coord`; vertical bands
    skirting / subway tile / frieze / paint; `side` = the inner face's normal key (n/s/e/w)"""
    W = L.WALL_T
    bands = [(z_lo, 48, 'skirting'), (48, 1000, 'subway'), (1000, 1128, 'frieze'), (1128, z_hi, 'wall_paint')]
    rects = sub_rects((r0, z_lo, r1, z_hi), [(h[0], h[2], h[1], h[3]) for h in holes])
    for (u0, za, u1, zb) in rects:
        for (b0, b1, tex) in bands:
            lo, hi = max(za, b0), min(zb, b1)
            if hi - lo < 0.5: continue
            if axis == 'x':
                y0, y1 = (coord, coord + W) if side == 's' else (coord - W, coord)
                b = box((u0, y0, lo), (u1, y1, hi), {'side': CAULK, 'top': CAULK, 'bot': CAULK, side: T(tex)}, detail=False)
            else:
                x0, x1 = (coord, coord + W) if side == 'w' else (coord - W, coord)
                b = box((x0, u0, lo), (x1, u1, hi), {'side': CAULK, 'top': CAULK, 'bot': CAULK, side: T(tex)}, detail=False)
            for f in b.faces:
                if f.tex == T('frieze'): fit_face(f, 0, 1024, 1000, 1128, 1024, 128)
                if f.tex == T('skirting'): fit_face(f, 0, 256, 0, 48, 256, 64)
            # window jambs: give the faces round a hole the frame colour
            for f in b.faces:
                if f.tex == CAULK and abs(f.n[2]) < 0.1 and abs(f.n[0 if axis == 'x' else 1]) > 0.9:
                    on = b.verts(); on = on[np.abs(on @ np.array(f.n) - f.d) < 0.5]
                    for h in holes:
                        k = 0 if axis == 'x' else 1
                        if np.all(np.abs(on[:, k] - h[0]) < 0.5) or np.all(np.abs(on[:, k] - h[1]) < 0.5):
                            if h[2] - 1 < on[:, 2].mean() < h[3] + 1: f.tex = T('wood_white'); f.sc = (0.5, 0.5)
                if f.tex == CAULK and abs(f.n[2]) > 0.9:
                    on = b.verts(); on = on[np.abs(on @ np.array(f.n) - f.d) < 0.5]
                    for h in holes:
                        if (abs(on[:, 2].mean() - h[2]) < 0.5 or abs(on[:, 2].mean() - h[3]) < 0.5):
                            k = 0 if axis == 'x' else 1
                            if on[:, k].min() >= h[0] - 0.5 and on[:, k].max() <= h[1] + 0.5: f.tex = T('wood_white'); f.sc = (0.5, 0.5)
            A(b)


def room():
    X, Y, W, F = L.HX, L.HY, L.WALL_T, L.FLOOR_T
    lx, ly = L.lift_xy()
    pit = (lx - 112, ly - 112, lx + 112, ly + 112)
    zones = [((L.FZ[0] + L.FZ_T, L.FZ[1] + L.FZ_T, L.FZ[2] - L.FZ_T, L.FZ[3] - L.FZ_T), 'cool_floor')]
    for r in sub_rects((-X - W, -Y - W, X + W, Y + W), [z[0] for z in zones] + [pit]):
        A(box((r[0], r[1], -F), (r[2], r[3], 0), {'top': T('floor'), 'side': T('rubber'), 'bot': CAULK}, detail=False))
    for (r, tex) in zones:
        A(box((r[0], r[1], -F), (r[2], r[3], 0), {'top': T(tex), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((pit[0], pit[1], -F), (pit[2], pit[3], -16), {'top': T('lift'), 'side': CAULK, 'bot': CAULK}, detail=False))

    A(box((-X - W, -Y - W, L.CEIL), (X + W, Y + W, L.CEIL + F), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    wall_bands(-X - W, X + W, 0, L.CEIL, 'x', Y, 's')
    wall_bands(-Y, Y, 0, L.CEIL, 'y', X, 'w')
    wall_bands(-Y, Y, 0, L.CEIL, 'y', -X, 'e')
    holes = [(x0, x1, z0, z1) for (x0, x1, z0, z1) in L.WINDOWS]
    wall_bands(-X - W, X + W, 0, L.CEIL, 'x', -Y, 'n', holes)
    # glass in the windows (detail, trans) + frames (MD3)
    for i, (x0, x1, z0, z1) in enumerate(L.WINDOWS):
        A(box((x0, -Y - 20, z0), (x1, -Y - 12, z1), T('glass')))
        custom(f'window{i}', (x0 + x1) / 2, -Y, z0, 0)
        occupy(x0 - 62, -Y, x1 + 62, -Y + 62, z0 - 66, z0 - 20); occupy(x0 - 24, -Y, x1 + 24, -Y + 14, z0 - 20, z1 + 24)
    street()


def street():
    """the street seen through the shop windows: a structural annex behind the south wall (pavement, painted shop
    fronts on the far side, sky above)"""
    X0, X1 = -1100, 1100
    yw = -L.HY - L.WALL_T
    yb = yw - L.STREET_D
    W, sk = 32, T('sky')
    ztop = 1700
    A(box((X0 - W, yb - W, -W), (X1 + W, yw, 0), {'top': T('pavement'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((X0 - W, yb - W, ztop), (X1 + W, yw, ztop + W), {'bot': sk, 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((X0 - W, yb, 0), (X0, yw, ztop), {'side': CAULK, 'top': CAULK, 'bot': CAULK, 'e': sk}, detail=False))
    A(box((X1, yb, 0), (X1 + W, yw, ztop), {'side': CAULK, 'top': CAULK, 'bot': CAULK, 'w': sk}, detail=False))
    bd = box((X0, yb - W, 0), (X1, yb, 1100), {'side': CAULK, 'top': CAULK, 'bot': CAULK, 'n': T('street')}, detail=False)
    for f in bd.faces:
        if f.tex == T('street'): fit_face(f, X0, X1, 0, 1100, 1024, 512)
    A(bd)
    A(box((X0, yb - W, 1100), (X1, yb, ztop), {'side': CAULK, 'top': CAULK, 'bot': CAULK, 'n': sk}, detail=False))




# =================================================================================================== the giant cone
def tower():
    clipped(SH.tower())
    cx, cy = L.TOWER
    custom('tower', cx, cy, 0, 0)
    # the scoop lift (func_plat drawn raised; its disc drops into a 16u pit in the floor)
    lx, ly = L.lift_xy()
    disc = cyl(round(lx), round(ly), L.LIFT_R, L.RIM_Z - 16, L.RIM_Z, {'top': T('lift'), 'side': T('rubber'), 'bot': T('rubber')}, 12)
    for f in disc.faces:
        if f.n[2] > 0.9:
            f.sc = (2 * L.LIFT_R / 256, 2 * L.LIFT_R / 256); f.off = ((-(lx - L.LIFT_R) / f.sc[0]) % 256, ((ly + L.LIFT_R) / f.sc[1]) % 256)
    M.ent('func_plat', brushes=[disc], height=int(L.RIM_Z), speed=260, lip=8)
    light(lx, ly, 120, 160, '0.6 1 0.9')
    occupy_r(lx, ly, 120, 0, L.RIM_Z + 80)
    route('scoop_lift_base', (lx + 230, ly, 0), (lx, ly - 220, 0))
    # bot clip ring round the deck edge (gap at the lift)
    for k in range(24):
        a0 = 7.5 + 15 * k; a1 = a0 + 15
        am = (a0 + a1) / 2
        if abs(((am - L.LIFT_A) + 180) % 360 - 180) < 25: continue
        b = SH.ring_seg(cx, cy, a0, a1, L.RIM_R - 26, L.RIM_R - 2, L.RIM_Z, L.RIM_Z + 64)
        for f in b.faces: f.tex = 'common/botclip'; f.sc = (0.5, 0.5)
        A(b)
    # pad from the floor (north) onto the deck; Imperius on the deck; applause up there
    jumppad(cx, cy + 840, 0, (cx, cy + 395, L.RIM_Z), 1240, 'p_deck')
    weapon('imperius', cx + 385 * math.cos(math.radians(40)), cy + 385 * math.sin(math.radians(40)), L.RIM_Z, 'purple')
    item('item_armor_shard', cx + 385 * math.cos(math.radians(150)), cy + 385 * math.sin(math.radians(150)), L.RIM_Z)
    item('ammo_boaster', cx + 385 * math.cos(math.radians(320)), cy + 385 * math.sin(math.radians(320)), L.RIM_Z)
    trigger_sound((cx - 120, cy - 440, L.RIM_Z + 4), (cx + 120, cy - 330, L.RIM_Z + 80), 'human/applause', 'deck_cheer', wait=15, volume=0.5)
    for a in (45, 135, 225, 315):
        light(cx + 520 * math.cos(math.radians(a)), cy + 520 * math.sin(math.radians(a)), 1300, 900, '1 0.95 0.9')
    light(cx, cy, 2000, 1600, '1 0.95 0.9')
    light(cx + 600, cy - 250, 260, 300, '1 0.9 0.8')
    # carton stacks round the stand, under the cone's overhang (cover at eye level)
    for k, a in enumerate((45, 135, 225, 315)):
        prop(['cartons', 'cartons2'][k % 2], cx + 370 * math.cos(math.radians(a)), cy + 370 * math.sin(math.radians(a)), 0, ang=a, force=True)


# =================================================================================================== gelato counter, aisle, wall shelf
def gelato_counter():
    clipped(SH.gelato_counter())
    custom('counter', 0, (L.GC[1] + L.HY) / 2, 0, 0)
    x0, y0, x1, y1 = L.GC
    D = L.GC_DECK
    for x in (-1000, 0, 1000):
        light(x, 1600, 200, 160, '0.8 0.95 1')
    # pads onto the deck ends and from the deck ends up to the wall shelf
    jumppad(-1270, 1130, 0, (-1250, 1530, D), 580, 'p_gc_w')
    jumppad(1270, 1130, 0, (1250, 1530, D), 580, 'p_gc_e')
    hx0, hx1, hy, hz = L.SHELF
    jumppad(-1300, 1670, D, (-1000, 1960, hz), 1330, 'p_shelf_w')
    jumppad(1300, 1670, D, (1000, 1960, hz), 1330, 'p_shelf_e')
    occupy(hx0, hy, hx1, L.HY, hz - 24, hz)
    weapon('betty', 0, 1955, hz, 'purple')
    item('ammo_imperius', -700, 1955, hz); item('ammo_balloony', 700, 1955, hz)
    for (nm, x) in (('ct_choc', -1140), ('conestack', -400), ('cartons2', 400), ('conestack', 1140), ('jar_spr', -200), ('ct_mint', 220)):
        prop(nm, x, 1970, hz, ang=0, search=60)
    # in the tubs: ammo to dig out
    tubs = L.GC_TUBS
    item('ammo_pumper', (tubs[1][0] + tubs[1][1]) / 2, 1600, L.GC_TUB)
    item('ammo_splasher', (tubs[4][0] + tubs[4][1]) / 2, 1600, L.GC_TUB)
    item('ammo_bubbleg', (tubs[6][0] + tubs[6][1]) / 2, 1600, L.GC_TUB)
    # the stairs
    route('gc_stair_w', (L.GC_STAIR_W[0] - 50, 1600, 0), (-1250, 1510, D))
    route('gc_stair_e', (L.GC_STAIR_E[2] + 50, 1600, 0), (1250, 1510, D))
    # the server aisle behind the counter: stock on the shelves, Visionless, ammo
    for zz in (300, 600):
        for x in (-1100, -500, 300, 900):
            prop(['ct_mint', 'ct_choc', 'ct_straw', 'jar_spr'][(x // 300 + zz // 300) % 4], x, 1962, zz, ang=0, search=80)
    for (nm, x) in (('ct_straw', -1150), ('ct_choc', -300), ('ct_mint', 450), ('ct_straw', 1150)):
        prop(nm, x, 1962, 0, ang=0, search=80)
    item('item_visionless', 0, 1830, 0); item('ammo_balloony', -900, 1830, 0); item('ammo_boaster', 900, 1830, 0)
    route('aisle', (-1500, 1840, 0), (1500, 1840, 0))
    for x in (-1100, 0, 1100):
        light(x, 1880, 400, 260, '1 0.92 0.8')


# =================================================================================================== soft-serve machine
def softserve():
    clipped(SH.softserve())
    x0, y0, x1, y1 = L.SS
    custom('softserve', (x0 + x1) / 2, 0, 0, 0)
    dz = L.SS_DECK + 262
    for (y, nm) in ((L.SS_NOZZLES[0], 'swirl_s'), (L.SS_NOZZLES[2], 'swirl_v')):
        M.ent('func_rotating', brushes=[box((-1798, y - 8, dz - 8), (-1782, y + 8, dz + 8), ORIGIN),
                                        box((-1794, y - 4, dz + 30), (-1786, y + 4, dz + 38), NODRAW_NS)],
              model2=bklib.PLACE[nm][0], speed=36, spawnflags=0, dmg=0)
    weapon('boaster', -2000, 0, 0, 'orange')
    item('ammo_pumper', -2150, -300, 0); item('item_armor_shard', -2150, 300, 0)
    light(-2000, -250, 200, 450, '1 0.85 0.75'); light(-2000, 250, 200, 450, '1 0.85 0.75')
    for (nm, x, y) in (('ct_mint', -2180, -400), ('ct_choc', -2180, 400), ('ct_straw', -1880, -380), ('ct_straw', -2180, 120)):
        prop(nm, x, y, 0, search=60)
    route('ss_cabinet', (-1550, 0, 0), (-1880, -160, 0))
    sx0, sy0, sx1, sy1 = L.SS_STAIR
    route('ss_stair', ((sx0 + sx1) / 2, sy1 + 80, 0), (-1640, 250, L.SS_DECK))
    jumppad(-1350, -220, 0, (-1640, -220, L.SS_DECK), 540, 'p_ss_deck')
    jumppad(-1632, 0, L.SS_DECK, (-2100, 0, L.SS_TOP), 1420, 'p_ss_top')
    jumppad(-1250, 260, 0, (-2100, 260, L.SS_TOP), 1430, 'p_ss_top2')
    item('item_jumper', -1640, 230, L.SS_DECK); item('ammo_balloony', -1650, -380, L.SS_DECK)
    weapon('balloony', -2150, -300, L.SS_TOP, 'orange')
    item('ammo_imperius', -2150, 380, L.SS_TOP)
    speaker(-1800, 0, 700, 'machine/mechanics', volume=0.3)
    light(-1700, 0, 900, 500, '1 0.9 0.85')


# =================================================================================================== milkshake bar + the giant glass
def bar():
    clipped(SH.bar())
    x0, y0, x1, y1 = L.BAR
    custom('bar', (x0 + x1) / 2, (y0 + y1) / 2, 0, 0)
    Z = L.BAR_Z
    for y in np.linspace(y0 + 160, y1 - 160, 6):
        prop('barstool', 1690, y, 0, ang=0, force=True)
    bx, by = 2120, 640
    prop('blender', bx, by, Z, ang=0, force=True)
    bz = Z + 160
    M.ent('func_rotating', brushes=[box((bx - 8, by - 8, bz - 8), (bx + 8, by + 8, bz + 8), ORIGIN),
                                    box((bx - 4, by - 4, bz + 30), (bx + 4, by + 4, bz + 38), NODRAW_NS)],
          model2=bklib.PLACE['blade'][0], speed=600, spawnflags=0, dmg=0)
    speaker(bx, by - 150, Z + 120, 'machine/fan_pc', volume=0.3)
    for (nm, x, y, a) in (('syrup_choc', 2180, 900, 0), ('syrup_berry', 2180, 380, 0), ('sundae', 2200, 20, 0), ('cone3', 2160, -100, 0),
                          ('cone2', 2160, -260, 0), ('sundae_b', 2140, -480, 0)):
        prop(nm, x, y, Z, ang=a, search=80)
    cat('pad_ddmix/diner/glass_betty.md3', 1960, 800, Z, 1.0); cat('pad_ddmix/diner/glass_sunrise.md3', 1960, 240, Z, 1.0)
    cat('pad_ddmix/diner/glass_rings.md3', 1960, -20, Z, 1.0)
    item('holdable_floater', 2000, 20, Z); item('ammo_betty', 2000, 470, Z); item('ammo_pumper', 2000, -600, Z)
    jumppad(1440, 160, 0, (2060, 160, Z), 620, 'p_bar_s')
    jumppad(1440, 860, 0, (2060, 860, Z), 620, 'p_bar_n')
    for y in (0, 700):
        light(2050, y, 800, 360, '1 0.9 0.85')
    # the giant milkshake glass: pad from the floor onto the cream (Pumper)
    clipped(SH.glass())
    gx, gy = L.GLASS
    custom('milkshake', gx, gy, 0, 0)
    A(hull([(gx + 130 + dx, gy + 70 + dy, L.GLASS_H + 60) for dx in (-14, 14) for dy in (-14, 14)] +
           [(gx + 220 + dx, gy + 120 + dy, L.GLASS_H + 340) for dx in (-14, 14) for dy in (-14, 14)], WCLIP, round_pts=False))
    occupy_r(gx, gy, L.GLASS_R + 30, 0, L.GLASS_H + 400)
    jumppad(gx - 460, gy, 0, (gx - 60, gy, L.GLASS_H + 48), 1080, 'p_glass')
    weapon('pumper', gx + 20, gy - 100, L.GLASS_H + 48, 'blue')
    light(gx, gy - 330, 300, 260, '1 0.8 0.9'); light(gx, gy, 1300, 500, '1 0.95 0.9')


# =================================================================================================== walk-in freezer + the Frozen Vault
def freezer_and_vault():
    clipped(SH.freezer())
    x0, y0, x1, y1 = L.FZ
    custom('freezer', (x0 + x1) / 2, (y0 + y1) / 2, 0, 0)
    t = L.FZ_T
    sx0, sx1 = x1 - t - 176, x1 - t - 16
    for zz in (240, 480):
        for y in (-1540, -1380):
            prop('ct_mint' if zz == 240 else 'ct_straw', (sx0 + sx1) / 2, y, zz, ang=0, search=30)
    for (nm, x, y) in (('icepile', 1500, -1300), ('iceblock', 1980, -1900), ('cartons', 1960, -1250), ('ct_choc', 1420, -1950), ('ct_straw', 1950, -1700)):
        prop(nm, x, y, 0, search=200)
    item('ammo_splasher', 1900, -1500, 0); item('item_armor_padshield', 2000, -1800, 0)
    for (x, y) in ((1550, -1350), (1950, -1350), (1550, -1800), (1950, -1800)):
        light(x, y, 820, 900, '0.75 0.9 1')
    light(1640, -1760, 220, 300, '0.6 1 0.85')
    speaker(1800, -1600, 400, 'machine/freezer', volume=0.5)
    dx, dhw, dh = L.FZ_DOOR
    route('freezer', (dx, -880, 0), (1650, -1400, 0))
    # roof: Splasher; pads from the floor and from the bar top
    weapon('splasher', 2050, -1700, L.FZ_H, 'green')
    item('ammo_imperius', 1450, -1950, L.FZ_H); item('holdable_boomies', 1500, -1300, L.FZ_H)
    jumppad(1090, -1250, 0, (1520, -1350, L.FZ_H), 1230, 'p_fz_roof')
    jumppad(2070, -560, L.BAR_Z, (2000, -1300, L.FZ_H), 1230, 'p_fz_roof2')
    # the Mystery Flavour tub -> the Frozen Vault
    mx, my, mr, mh = L.MYSTERY
    occupy_r(mx, my, mr + 20, 0, mh + 60)
    ir = 85
    speaker(mx, my, 120, 'misc/secret_found', loop=False, targetname='vault_snd')
    M.ent('trigger_multiple', brushes=[box((mx - ir, my - ir, 40), (mx + ir, my + ir, 90), TRIG)], target='vault_snd', wait=2)
    M.ent('trigger_teleport', brushes=[box((mx - ir + 10, my - ir + 10, 9), (mx + ir - 10, my + ir - 10, 40), TRIG)], target='vault_in')
    light(mx, my, 60, 140, '0.5 1 0.8')
    vx0, vy0, vx1, vy1, z0, z1 = L.VAULT
    W = 32
    wl = {'side': T('choc_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((vx0 - W, vy0 - W, z0 - W), (vx1 + W, vy1 + W, z0), {'top': T('gold_tile'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((vx0 - W, vy0 - W, z1), (vx1 + W, vy1 + W, z1 + W), {'bot': T('choc_wall'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((vx0 - W, vy0 - W, z0), (vx0, vy1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((vx1, vy0 - W, z0), (vx1 + W, vy1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((vx0, vy0 - W, z0), (vx1, vy0, z1), dict(wl, s=CAULK), detail=False))
    A(box((vx0, vy1, z0), (vx1, vy1 + W, z1), dict(wl, n=CAULK), detail=False))
    prop('goldsundae', 0, 200, z0, ang=0, force=True)
    for (nm, x, y) in (('icepadman', -420, 300), ('icepadman', 420, 300), ('rockcandy', -480, -320), ('rockcandy_b', 480, -320),
                       ('coins', 230, -150), ('coins', -230, 380), ('icepile', -380, -120)):
        prop(nm, x, y, z0, search=80)
    item('item_padpower', 0, -100, z0); item('item_revival', -260, 0, z0); item('holdable_killerducks', 260, 40, z0)
    item('ammo_imperius', 480, 40, z0); item('ammo_splasher', -200, -300, z0)
    A(sign_box((-360, vy1 - 6, z0 + 300), (360, vy1, z0 + 420), T('sign_vault'), 1024, 192, facing='s'))
    M.ent('misc_teleporter_dest', (0, -260, z0 + 24), targetname='vault_in', angle=90)
    mdl_c('pad_teleporter/padtp_blue.md3', 0, vy0 + 50, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, vy0 + 14, z0 + 2), (36, vy0 + 86, z0 + 90), TRIG)], target='vault_out')
    occupy(-60, vy0, 60, vy0 + 110, z0, z0 + 120)
    M.ent('misc_teleporter_dest', (dx, -940, 24), targetname='vault_out', angle=90)
    for (x, y, c) in ((0, 0, '0.8 0.9 1'), (-420, 300, '0.6 0.85 1'), (420, 300, '0.6 0.85 1'), (0, 300, '1 0.9 0.6'), (-400, -300, '1 0.7 0.9')):
        light(x, y, z0 + 760, 520, c)
    speaker(0, -380, z0 + 200, 'ambient/wind_icy', volume=0.4)
    timer_sound(0, 0, z0 + 150, 'human/applause', 'vault_cheer', 40, 10, volume=0.4)


# =================================================================================================== chest freezer, cart, jars, shop
def chest():
    clipped(SH.chest())
    x0, y0, x1, y1 = L.CF
    custom('chest', (x0 + x1) / 2, (y0 + y1) / 2, 0, 0)
    weapon('bubbleg', -1880, -1430, L.CF_FLOOR, 'green')
    item('ammo_betty', -1500, -1500, L.CF_FLOOR)
    prop('cartons2', -1450, -1300, L.CF_FLOOR, ang=0, search=60); prop('ct_mint', -1900, -1300, L.CF_FLOOR, ang=0, search=60)
    sx0, sy0, sx1, sy1 = L.CF_STAIR_OUT
    route('chest', ((sx0 + sx1) / 2, sy1 + 80, 0), (-1880, -1500, L.CF_FLOOR))
    light(-1680, -1400, 300, 220, '0.8 0.95 1')


def cart_jars_shop():
    clipped(SH.cart())
    cx, cy = L.CART
    custom('cart', cx, cy, 0, 0)
    occupy(cx - L.CART_W / 2 - 130, cy - L.CART_D / 2 - 30, cx + L.CART_W / 2 + 130, cy + L.CART_D / 2 + 30, 0, 1100)
    jumppad(cx, cy + 470, 0, (cx - 120, cy, L.CART_H), 660, 'p_cart')
    item('item_speedy', cx + 140, cy, L.CART_H); item('ammo_boaster', cx - 180, cy + 60, L.CART_H)
    clipped(SH.jars())
    for (x, y), nm in zip(L.JARS, ('jar_spr', 'jar_choc', 'jar_nuts', 'jar_marsh', 'jar_gummy')):
        custom(nm, x, y, 0, 0)
    # tables + chairs by the windows, cones on stands, a register-free counter top for take-away
    for (x, y, a) in ((-620, -1820, 0), (620, -1820, 30), (-1350, -900, 15)):
        p = prop('cafetable', x, y, 0, ang=a, search=80)
        if p:
            for s in (-1, 1):
                prop('cafechair', p[0] + s * 300, p[1] + 20, 0, ang=90 if s < 0 else 270, search=100)
            prop(['sundae', 'sundae_b', 'cone4'][int(abs(x)) % 3], p[0], p[1], 604, ang=0, force=True, clip=False)
    cat('pad_ddmix/padshop/cardboard_standup.md3', 1150, -1950, 0, 1.6, 90)
    cat('pad_ddmix/plants/flower_pink.md3', -2080, -1950, 0, 1.4, 0)
    item('ammo_bubbleg', 0, -1880, 0); item('ammo_nipper', -1100, -1650, 0)
    timer_sound(0, -1900, 400, 'misc/wind_chimes', 'shop_bell', 50, 30, volume=0.4)
    A(sign_box((-760, -L.HY, 1380), (760, -L.HY + 6, 1760), T('sign_main'), 1024, 256, facing='n'))
    A(sign_box((-1900, -L.HY, 900), (-1300, -L.HY + 6, 1500), T('menu'), 512, 512, facing='n'))


# =================================================================================================== cover, spawns, lights, sound
def floor_cover():
    pieces = [('cone3', -700, 600), ('cone5', 700, 600), ('cone1', -600, -200), ('cone2', 650, -150), ('cone4', 300, -950),
              ('pop_straw', -1100, 250), ('pop_lemon', 1000, 1050), ('pop_choc', -300, -700), ('sundae', 900, 200), ('sundae_b', -950, 1100),
              ('cartons', -1450, 600), ('cartons2', 1500, -650), ('cone1', -520, 1120), ('icepile', 500, -1150), ('spoon', -950, 760),
              ('pop_vanilla', -900, -1500), ('boxes3', 1300, 1250), ('boxes2', -1350, -100), ('conestack', 1550, 1350), ('milkcrate', -2100, 1000)]
    for (nm, x, y) in pieces:
        prop(nm, x, y, 0, search=300)
    for (path, x, y, sc) in (('gummybears/redbear.md3', -1250, 1350, 1.0), ('gummybears/greenbear.md3', 1150, -150, 1.0),
                             ('gummybears/ldyellowbear.md3', 350, 1150, 1.0), ('gummybears/orangebear.md3', -350, -1100, 1.0),
                             ('pad_ddmix/diner/muffin_choco.md3', 1050, 600, 1.0), ('pad_ddmix/diner/glass_midnight.md3', -1150, -250, 1.0),
                             ('pad_ducks/pad_duck.md3', -2050, 1350, 0.4), ('pad_ddmix/gallery/fire_extinguisher.md3', -1580, -700, 4.0),
                             ('pad_ddmix/diner/coffe_pot.md3', 1500, 1100, 1.0)):
        cat(path, x, y, 0, sc)


def blockers():
    """cover where long eye-level lines run (sightlines.py --hot): big display cones, carton stacks, ice piles"""
    for (nm, x, y) in (('cartons', -640, 840), ('bigcone_a', -360, 980), ('bigcone_b', 380, 980), ('icepile', 700, 860),
                       ('cartons2', -330, -440), ('bigcone_a', 460, -470), ('bigcone_b', -900, -150), ('icepile', -1100, -1650),
                       ('cartons', 820, -1300), ('bigcone_a', 1450, -150), ('bigcone_b', -1500, 900), ('cartons2', 150, -1700)):
        prop(nm, x, y, 0, search=260)


def items_misc():
    item('ammo_nipper', -400, -300, 0); item('ammo_nipper', 1300, 1300, 0)
    item('item_armor_shard', -1600, 300, 0); item('item_armor_shard', 800, -700, 0); item('item_armor_shard', -800, -1100, 0)
    item('ammo_splasher', 1300, -1000, 0); item('ammo_betty', -500, 900, 0); item('ammo_bubbleg', 1500, 500, 0)
    station(-1300, -1100, 0, 90); station(1450, 1050, 0, 180)
    for (x, y, a) in ((-600, -300, 90), (600, 0, 180), (-1350, 700, 0), (1300, -400, 180), (-200, 1300, 270), (1000, 1000, 225),
                      (-1450, -400, 0), (1100, -1700, 135), (-700, -1700, 45), (300, -1750, 90), (-1500, 1250, 300), (-1100, -1450, 60), (1000, -1000, 135)):
        spawn(x, y, 0, a)


def lights_and_sound():
    for (x, y) in ((-1250, -300), (-1250, 1000), (-300, 1100), (900, 1100), (900, -400), (-300, -600), (1400, 300), (-550, -1780),
                   (550, -1780), (-1700, -1400), (1600, -800)):
        custom('pendant', x, y, L.CEIL, 0, lit=False)
        light(x, y, L.CEIL - 370, 7000, '1 0.92 0.82')
    for x in (-1700, -570, 570, 1700):
        for y in (-1500, -500, 500, 1500):
            light(x, y, 1250, 2600, '1 0.96 0.9')
    for (fx, fy) in ((-1100, -500), (1000, 700)):
        fz = L.CEIL - 200
        custom('fanrod', fx, fy, L.CEIL, 0, lit=False)
        M.ent('func_rotating', brushes=[box((fx - 8, fy - 8, fz - 8), (fx + 8, fy + 8, fz + 8), ORIGIN),
                                        box((fx - 4, fy - 4, fz - 40), (fx + 4, fy + 4, fz - 32), NODRAW_NS)],
              model2=bklib.PLACE['fanblades'][0], speed=70, spawnflags=0, dmg=0)
    custom('clock', 1150, L.HY, 1600, 0)
    speaker(1150, 1990, 1600, 'machine/clock_ticking', volume=0.3)
    speaker(900, -900, 1700, 'machine/ventilation', volume=0.2)


def reserve():
    for f in (SH.tower, SH.gelato_counter, SH.softserve, SH.bar, SH.glass, SH.freezer, SH.chest, SH.cart, SH.jars):
        for b in f():
            mn, mx = b.bounds()
            occupy(mn[0], mn[1], mx[0], mx[1], mn[2], mx[2])
    occupy_r(L.TOWER[0], L.TOWER[1], L.RIM_R + 30, 0, 2000)


def main():
    bklib.STATE['out'] = OUT
    TX.make_textures()
    import gl_models as GM
    import gl_props as BP
    GM.make(); BP.make()
    room()
    reserve()
    tower(); gelato_counter(); softserve(); bar(); freezer_and_vault(); chest(); cart_jars_shop()
    items_misc(); blockers(); floor_cover(); lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (1500, -1500, 1300), angles='20 135 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padgelato/build_gelato.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
