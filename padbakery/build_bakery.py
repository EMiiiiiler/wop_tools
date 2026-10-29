#!/usr/bin/env python3
"""Sweet Padman's Bakery - World of Padman FFA map generator (map 'wop_padbakery').

    OUT=/path/to/out MD3ROOT=<dir holding models/mapobjects> python3 build_bakery.py

Writes <OUT>/maps/wop_padbakery.map, textures/padbakery/*, models/padbakery/*, scripts/padbakery.shader and
scripts/wop_padbakery.arena.

Padman scale (~8u per cm, catalog models at 1.0): a busy bakery kitchen with its little shop. x east, y north,
floor z 0, ceiling z 2048.

  Show cake      a three-tier celebration cake in the middle of the kitchen: sugar-cube stair up to tier 1, pads up
                 the tiers to the top (Imperius, applause). A slice is missing: walk into the cake (Boaster).
  Deck oven      west wall: walk into the warm proofer (Bubble G), pads into both baking decks (bread, armour) and
                 onto the oven top (Balloony).
  Floor mixer    a 60-litre planetary mixer, its paddle turning: a pad drops you into the bowl (Pumper), a pad out.
  Counters       north + east worktops at z 720 (pads up), tunnels through the open shelving underneath, a wall shelf
                 over the north counter (Betty) and the decorating station with a turning cake on the east counter.
  Cool room      south-east: walk in through the strip curtain; a pad onto its roof (Splasher), one from the counter.
  Shop           the display cabinet (step stools up into it from the kitchen, pads onto its glass shelf and top),
                 cafe tables, sunny windows onto the street.
  Cooling racks  two speed racks full of pastries, pads onto their tops.
  SECRET         climb the step stool of the flour bin and jump into the flour -> the Sugar Vault under the world.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import layout as L
import bk_textures as TX
import bklib
import bk_shapes as SH

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MD3ROOT = os.environ.get('MD3ROOT', os.path.expanduser('~/Games/wop/wop/models.pk3dir'))
MAPNAME = 'wop_padbakery'
T = lambda n: 'padbakery/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; ORIGIN = 'common/origin'
NODRAW_NS = T('nodraw_ns')

for k, v in {'floor': (1.0, 1.0), 'subway': (0.5, 0.5), 'wall_paint': (1.0, 1.0), 'frieze': (1.0, 1.0), 'ceiling': (1.0, 1.0),
             'skirting': (1.0, 0.75), 'wood_white': (0.5, 0.5), 'pavement': (1.0, 1.0), 'choc_wall': (1.0, 1.0), 'gold_tile': (1.0, 1.0),
             'sky': (1, 1), 'glass': (1, 1), 'cool_floor': (1.0, 1.0), 'shop_floor': (1.0, 1.0), 'jumppad': (1, 1), 'rubber': (0.5, 0.5)}.items():
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
    import bk_props as BP
    r, h = 0.0, 0.0
    for (mn, mx) in BP.BOX.get(name, []):
        r = max(r, math.hypot(max(abs(mn[0]), abs(mx[0])), max(abs(mn[1]), abs(mx[1])))); h = max(h, mx[2])
    for (cx, cy, rr, z0, z1) in BP.CYL.get(name, []):
        r = max(r, math.hypot(cx, cy) + rr); h = max(h, z1)
    return r, h


def prop(name, x, y, z, ang=None, search=160, lit=True, clip=True, r=None, h=None, force=False):
    """custom prop (bk_props) with its weapclip collision, nudged to a free spot unless force"""
    import bk_props as BP
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
        f.write('# On-foot routes that must work both ways while standing (aas_check.py --route @padbakery/routes.txt)\n'
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
    zones = [((L.CR[0], -Y - W, X + W, L.CR[3]), 'cool_floor'), ((L.DC[0], -Y - W, L.DC[2], L.DC[1]), 'shop_floor')]
    for r in sub_rects((-X - W, -Y - W, X + W, Y + W), [z[0] for z in zones]):
        A(box((r[0], r[1], -F), (r[2], r[3], 0), {'top': T('floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    for (r, tex) in zones:
        A(box((r[0], r[1], -F), (r[2], r[3], 0), {'top': T(tex), 'side': CAULK, 'bot': CAULK}, detail=False))
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


# =================================================================================================== deck oven
def oven():
    clipped(SH.oven())
    import bk_models as BM
    custom('oven', *BM.CENTRES['oven'], 0, 0)
    custom('flue', L.FLUE[0], L.FLUE[1], 0, 0)
    xf = L.OV_FRONT
    xi0, xi1 = L.OV_X0 + L.OV_SIDE, xf - L.OV_FRONT_T
    # proofer: walk in (Bubble G), dough baskets on the floor
    weapon('bubbleg', -1850, 0, 0, 'green')
    for (x, y) in ((-2150, -420), (-2150, 420), (-2150, 0)):
        prop('banneton', x, y, 0, search=60)
    light(-1950, 0, 260, 380, '1 0.85 0.6')
    route('proofer', (-1300, 0, 0), (-2000, 0, 0))
    # deck 1 (south mouth: pad) and deck 2 (north mouth: pad): bread on the hearths
    for zd, tag in ((L.DECK1, 'd1'), (L.DECK2, 'd2')):
        for (x, y, nm) in ((-2150, -450, 'loaf'), (-2150, -200, 'boule'), (-1950, 450, 'loaf_d'), (-2160, 200, 'loaf'), (-2160, 470, 'boule')):
            prop(nm, x, y, zd, ang=RNG.uniform(0, 360), search=120)
        for (x, y) in ((-2050, -440), (-2050, 300)):
            light(x, y, zd + 130, 220, '1 0.6 0.3')
        speaker(-1950, 0, zd + 80, 'ambient/fire_crackling', volume=0.35)
    item('item_armor_shard', -1850, -380, L.DECK1); item('ammo_balloony', -1800, 420, L.DECK1); item('ammo_imperius', -2150, 0, L.DECK1)
    item('item_armor_padshield', -1850, 380, L.DECK2); item('ammo_bubbleg', -1850, -380, L.DECK2); item('item_jumper', -2150, -60, L.DECK2)
    jumppad(-1340, -320, 0, (-1680, -320, L.DECK1), 570, 'p_deck1')
    jumppad(-1150, 260, 0, (-1820, 320, L.DECK2), 840, 'p_deck2')
    jumppad(-1180, 0, 0, (-1950, -60, L.OV_TOP), 1160, 'p_ovtop')
    # oven top: Balloony, a peel and a stack of trays
    weapon('balloony', -1850, -320, L.OV_TOP, 'orange')
    item('ammo_splasher', -2150, 380, L.OV_TOP)
    prop('peel', -1900, 420, L.OV_TOP, ang=180, clip=False, r=150, h=14)
    prop('loaf', -2200, -520, L.OV_TOP, ang=90, search=60); prop('baguette', -2240, 120, L.OV_TOP, ang=90, search=60)
    timer_sound(-1520, 0, 1000, 'machine/dingdong', 'oven_ding', 75, 30, volume=0.6)


# =================================================================================================== counters + wall shelf
def counters():
    clipped(SH.counters())
    import bk_models as BM
    custom('counters', *BM.CENTRES['counters'], 0, 0)
    W, S_ = L.WORK, L.SHELF
    # pads up from the floor onto the worktops, into the north mid-shelf tunnel and onto the wall shelf
    jumppad(-760, 1180, 0, (-760, 1720, W), 1000, 'p_ntop_w')
    jumppad(1300, 1180, 0, (1300, 1720, W), 1000, 'p_ntop_e')
    jumppad(100, 1150, 0, (100, 1760, S_), 520, 'p_nshelf')
    jumppad(1450, -250, 0, (1950, -250, W), 1000, 'p_etop_s')
    jumppad(1450, 900, 0, (1960, 900, W), 1000, 'p_etop_n')
    jumppad(1460, 120, 0, (2000, -150, S_), 520, 'p_eshelf')
    x0, x1, yf, zt = L.WALL_SHELF
    jumppad(900, 1620, W, (900, 1960, zt), 1400, 'p_wshelf_e')
    jumppad(-150, 1620, W, (-150, 1960, zt), 1400, 'p_wshelf_w')
    # the wall shelf: Betty + canisters, jars and the bakery duck
    occupy(x0, yf, x1, L.HY, zt - 24, zt)
    weapon('betty', 380, 1955, zt, 'purple')
    item('ammo_betty', 1450, 1955, zt); item('ammo_imperius', -380, 1955, zt)
    for (x, nm) in ((-300, 'can_flour'), (-150 + 280, 'can_sugar'), (640, 'can_cocoa'), (1200, 'can_salt'), (1330, 'jar_spr'), (1050, 'jar_jam')):
        prop(nm, x, 1975, zt, ang=270, search=60, clip=False, r=50, h=170)
    cat('pad_ducks/pad_duck.md3', 1540, 1960, zt, 0.35, 250)
    # north worktop: dough, rolling pin, bannetons, cookies, scale, jars, cupcakes and macarons
    item('ammo_pumper', -1200, 1700, W); item('ammo_boaster', 600, 1800, W); item('item_armor_shard', 1800, 1700, W)
    station(-400, 1820, W, 270)
    for (nm, x, y, a) in (('dough', 200, 1820, 0), ('rollpin', 330, 1560, 10), ('cookies', -1050, 1880, 0), ('cookies', 1650, 1880, 0),
                          ('scale', 1100, 1900, 0), ('banneton', -1250, 1880, 0), ('banneton', -1050, 1620, 0), ('jar_choc', 1350, 1960, 0),
                          ('boxes2', 2120, 1880, 20), ('cup_pink', -600, 1650, 0), ('cup_choc', -520, 1600, 0), ('cup_mint', -440, 1680, 0),
                          ('whisk', 560, 1600, 200), ('pipingbag', 1500, 1620, 160)):
        prop(nm, x, y, W, ang=a, search=120)
    for k, nm in enumerate(('mac_pink', 'mac_mint', 'mac_lemon', 'mac_lilac', 'mac_choc', 'mac_pink')):
        prop(nm, 470 + k * 46, 1975, W, ang=0, search=40, clip=False, r=21, h=24)
    cat('pad_plates/plate_hpstack1.md3', -880, 1880, W, 1.0, 0)
    cat('pad_condiments/sugar.md3', 1260, 1640, W, 1.0)
    cat('pad_cups/pad_cup02.md3', 1900, 1560, W, 1.0)
    cat('pad_fruits/apple.md3', -900, 1600, W, 1.0); cat('pad_fruits/orange.md3', -980, 1560, W, 1.0); cat('pad_fruits/citrus.md3', 1800, 1900, W, 1.0)
    cat('pad_ddmix/padkitchen/towel_kitchen.md3', 1950, 1990, W, 0.8, 0, clip=False)
    # east worktop: the decorating station (turning cake), cupcake tower, piping bags, fruit, boxes
    tx, ty = 2000, 300
    prop('turntable', tx, ty, W, ang=0, force=True)
    tz = W + 72
    A(cyl(tx, ty, 128, tz, tz + 110, WCLIP, 16))
    M.ent('func_rotating', brushes=[box((tx - 8, ty - 8, tz + 2), (tx + 8, ty + 8, tz + 18), ORIGIN),
                                    box((tx - 4, ty - 4, tz + 30), (tx + 4, ty + 4, tz + 38), NODRAW_NS)],
          model2=bklib.PLACE['turncake'][0], speed=18, spawnflags=0, dmg=0)
    occupy_r(tx, ty, 150, tz, tz + 120)
    prop('cctower', 2050, 1250, W, ang=0, search=80)
    for (nm, x, y, a) in (('pipingbag_b', 1880, 560, 90), ('pipingbag', 1830, 80, 300), ('boxes3', 2150, -680, 0),
                          ('jar_spr', 1850, 700, 0), ('cup_lemon', 1800, 1200, 0), ('cup_blue', 1860, 1260, 0), ('eclair', 1850, 40, 40),
                          ('donut_pink', 2150, -480, 0), ('donut_choc', 2080, -400, 0)):
        prop(nm, x, y, W, ang=a, search=120)
    item('ammo_splasher', 2050, 560, W); item('holdable_floater', 2050, -60, W); item('ammo_balloony', 1900, 1640, W)
    # under-counter shelving: stock on the floor and mid shelves, tunnels through the dividers
    bays = SH.n_bays()
    stock = [('sack_flour', 0), ('eggs', 0), ('milkcrate', 0), ('boxes2', 0), ('sugar_bag', 0)]
    for i, (xa, xb) in enumerate(bays):
        xm = (xa + xb) / 2
        nm, _ = stock[i % len(stock)]
        prop(nm, xa + 260, 1900, 0, ang=90 if nm.startswith('sack') else 0, search=80)
        prop(['eggs3', 'boxes2', 'milkcrate'][i % 3], xb - 200, 1880, S_, search=80)
        prop(['milkcrate', 'tins', 'eggs'][i % 3], xm + 40, 1728, 0, ang=0, search=60)
        prop(['tins', 'boxes2', 'eggs3'][i % 3], xm + (320 if i == 1 else -60), 1728, S_, ang=0, search=40)
        light(xm, 1560, 260, 300, '1 0.9 0.75'); light(xm, 1560, S_ + 250, 260, '1 0.9 0.75')
        cat('pad_tins/pad_milk_s.md3', xm, 1960, 0, 1.0, 0)
        cat('pad_tins/carrots_tl.md3', xm - 140, 1960, S_, 1.0, 0)
    for (ya, yb) in SH.e_bays():
        ym = (ya + yb) / 2
        prop('sack_sugar', 2120, ym + 200, 0, ang=90, search=80)
        prop('tins', 1968, ym - 160, 0, ang=0, search=60)
        prop('milkcrate', 1968, ym + 300, 0, ang=0, search=60)
        prop('boxes2', 1968, ym + 330, L.SHELF, ang=0, search=60)
        prop('eggs', 2160, ym - 220, S_, search=80)
        light(2000, ym, 260, 260, '1 0.9 0.75'); light(2000, ym, S_ + 250, 220, '1 0.9 0.75')
    item('item_visionless', 40, 1700, S_); item('ammo_pumper', -900, 1650, S_); item('ammo_boaster', 1200, 1650, 0)
    item('item_armor_shard', -800, 1650, 0); item('ammo_imperius', 2000, -500, S_); item('ammo_betty', 2000, 700, 0)
    route('n_tunnel_low', (-1550, 1728, 0), (1500, 1728, 0))
    route('n_tunnel_mid', (-1100, 1520, S_), (1450, 1520, S_))
    route('e_tunnel_low', (1968, -900, 0), (1968, 900, 0))


# =================================================================================================== the show cake
def cake():
    clipped(SH.cake())
    cx, cy = L.CAKE
    custom('cake', cx, cy, 0, 0)
    r1, r2, r3 = (t[0] for t in L.TIERS)
    z1, z2, z3 = (t[2] for t in L.TIERS)
    occupy_r(cx, cy, r1 + 30, 0, z3 + 160)
    yt = cy - L.apothem(r1)
    occupy(cx - 100, yt - 470, cx + 100, yt, 0, z1)
    route('cake_stair', (cx, yt - 560, 0), (cx, cy - 400, z1))
    # the missing slice: walk into the cake (Boaster), the slice stands beside it
    weapon('boaster', cx + 260, cy, 0, 'orange')
    item('ammo_bubbleg', cx + 140, cy + 20, 0)
    light(cx + 300, cy, 170, 230, '1 0.85 0.7')
    route('cake_cave', (cx + 760, cy - 40, 0), (cx + 200, cy, 0))
    sx, sy = cx + 920, cy - 330
    custom('slice', sx, sy, 0, 200)
    r = r1; h = math.radians(22.5)
    a = math.radians(200)
    apex = np.array([sx, sy]) + np.array([math.cos(a), math.sin(a)]) * r * 0.55 * -1
    # slice collision: the wedge prism (apex, two arc corners) in world space
    P = []
    for s in (-1, 1):
        d = np.array([math.cos(a + s * h), math.sin(a + s * h)])
        P.append(apex + d * r)
    pts2 = [apex] + P + [apex + np.array([math.cos(a), math.sin(a)]) * r]
    A(hull([(p[0], p[1], z) for p in pts2 for z in (0, z1 - 2)], WCLIP, round_pts=False))
    occupy(min(p[0] for p in pts2) - 10, min(p[1] for p in pts2) - 10, max(p[0] for p in pts2) + 10, max(p[1] for p in pts2) + 10, 0, z1)
    # pads up the tiers, Imperius on top, applause when you get there
    a1 = math.radians(135)
    jumppad(cx + 410 * math.cos(a1), cy + 410 * math.sin(a1), z1, (cx + 268 * math.cos(a1), cy + 268 * math.sin(a1), z2), 560, 'p_tier2')
    a2 = math.radians(225)
    jumppad(cx + 270 * math.cos(a2), cy + 270 * math.sin(a2), z2, (cx - 40, cy - 60, z3), 820, 'p_tier3')
    jumppad(cx, cy + 640, 0, (cx, cy + 410, z1), 420, 'p_tier1')
    jumppad(cx - 720, cy - 130, 0, (cx - 40, cy - 130, z3), 960, 'p_caketop')
    weapon('imperius', cx + 60, cy - 120, z3, 'purple')
    trigger_sound((cx - 150, cy - 190, z3 + 4), (cx + 150, cy - 80, z3 + 80), 'human/applause', 'cake_top', wait=12, volume=0.6)
    item('ammo_imperius', cx + 300 * math.cos(math.radians(60)), cy + 300 * math.sin(math.radians(60)), z2)
    item('item_armor_shard', cx + 410 * math.cos(math.radians(200)), cy + 410 * math.sin(math.radians(200)), z1)
    item('ammo_boaster', cx + 410 * math.cos(math.radians(60)), cy + 410 * math.sin(math.radians(60)), z1)
    # the ceiling fan turning over the cake
    fx, fy, fz = cx, cy, L.CEIL - 200
    custom('fanrod', fx, fy, L.CEIL, 0, lit=False)
    M.ent('func_rotating', brushes=[box((fx - 8, fy - 8, fz - 8), (fx + 8, fy + 8, fz + 8), ORIGIN),
                                    box((fx - 4, fy - 4, fz - 40), (fx + 4, fy + 4, fz - 32), NODRAW_NS)],
          model2=bklib.PLACE['fanblades'][0], speed=70, spawnflags=0, dmg=0)


# =================================================================================================== floor mixer
def mixer():
    clipped(SH.mixer())
    cx, cy = L.MIX
    custom('mixer', cx, cy, 0, 0)
    occupy_r(cx, cy, L.BOWL_R1 + L.BOWL_T + 10, L.BOWL_Z0 - 20, L.BOWL_Z1 + 10)
    x0, y0, x1, y1 = L.MIX_COL
    occupy(x0 - 40, y0 - 30, x1 + 40, y1 + 20, 0, L.MIX_HEAD[5])
    zc = L.BOWL_Z1
    M.ent('func_rotating', brushes=[box((cx - 8, cy - 8, zc - 8), (cx + 8, cy + 8, zc + 8), ORIGIN),
                                    box((cx - 4, cy - 4, zc + 40), (cx + 4, cy + 4, zc + 48), NODRAW_NS)],
          model2=bklib.PLACE['paddle'][0], speed=40, spawnflags=0, dmg=0)
    weapon('pumper', cx + 70, cy + 70, L.BOWL_Z0, 'blue')
    jumppad(cx, cy - 430, 0, (cx + 30, cy - 20, L.BOWL_Z0), 800, 'p_bowl_in')
    jumppad(cx - 20, cy - 108, L.BOWL_Z0, (cx - 370, cy - 320, 0), 900, 'p_bowl_out')
    light(cx, cy, L.BOWL_Z0 + 200, 200, '1 0.92 0.75')
    speaker(cx, cy, 700, 'machine/mechanics', volume=0.35)


# =================================================================================================== display cabinet + shop
def display_cabinet():
    clipped(SH.display_cabinet())
    import bk_models as BM
    custom('display', *BM.CENTRES['display'], 0, 0)
    x0, y0, x1, y1 = L.DC
    for (xa, xb) in L.DC_STEPS:
        occupy(xa - 10, y1, xb + 10, y1 + 270, 0, L.DC_PLINTH)
        route(f'dc_steps_{int(xa)}', ((xa + xb) / 2, y1 + 360, 0), ((xa + xb) / 2, y1 - 120, L.DC_PLINTH))
    # lower deck: whole cakes; glass shelf: pastries; top: register, cake under a dome, catalog cake stands
    zl, zs, zt = L.DC_PLINTH, L.DC_SHELF, L.DC_TOP
    for (nm, x) in (('cake_berry', -760), ('cake_choc', -380), ('cake_lemon', 260), ('cake_pink', 620)):
        prop(nm, x, -1320, zl, search=60)
    item('ammo_pumper', -80, -1280, zl); item('item_armor_shard', 450, -1160, zl)
    for k in range(10):
        nm = ['cup_pink', 'cup_choc', 'cup_mint', 'cup_lemon', 'cup_blue'][k % 5]
        prop(nm, -980 + k * 190, -1400, zs, search=40, clip=False)
    for k in range(6):
        prop(['eclair', 'croissant', 'donut_white'][k % 3], -900 + k * 330, -1180, zs, ang=90, search=60, clip=False, r=40, h=30)
    item('item_padshield' if False else 'item_armor_padshield', 0, -1180, zs)
    item('ammo_splasher', 700, -1250, zs)
    prop('register', 600, -1250, zt, ang=0, search=60)
    prop('standcake', -500, -1260, zt, search=60)
    cat('pad_cake/pad_cakestand.md3', -150, -1330, zt, 1.4, 0)
    cat('pad_cake/pad_cakestand.md3', 250, -1330, zt, 1.4, 0)
    item('item_speedy', 100, -1160, zt); item('ammo_balloony', -850, -1150, zt)
    jumppad(-300, -620, 0, (-300, -1280, zs), 620, 'p_dcshelf')
    jumppad(400, -640, 0, (400, -1180, zt), 990, 'p_dctop')
    for x in (-700, 0, 600):
        light(x, -1250, zt - 60, 160, '1 0.95 0.85'); light(x, -1250, zs + 120, 180, '1 0.95 0.85')
    # the shop floor
    for (x, y, a) in ((-620, -1830, 0), (520, -1830, 30)):
        p = prop('cafetable', x, y, 0, ang=a, search=80)
        if p:
            for s in (-1, 1):
                prop('cafechair', p[0] + s * 360, p[1] + 30, 0, ang=90 if s < 0 else 270, search=100)
    prop('breadbasket', -1250, -1900, 0, search=120)
    cat('pad_ddmix/padshop/cardboard_standup.md3', 1150, -1950, 0, 1.6, 90)
    cat('pad_ddmix/plants/flower_pink.md3', -1700, -1950, 0, 1.5, 0)
    item('ammo_bubbleg', 0, -1880, 0); item('ammo_nipper', -1100, -1700, 0)
    timer_sound(0, -1900, 400, 'misc/wind_chimes', 'shop_bell', 50, 30, volume=0.4)
    # sign over the windows + chalk menu (wall signs)
    A(sign_box((-760, -L.HY, 1380), (760, -L.HY + 6, 1760), T('sign_bakery'), 1024, 256, facing='n'))
    A(sign_box((-1900, -L.HY, 1000), (-1300, -L.HY + 6, 1600), T('menu'), 512, 512, facing='n'))
    route('shop_e', (0, -1800, 0), (1150, -760, 0))
    route('shop_w', (0, -1800, 0), (-1200, -760, 0))


# =================================================================================================== cool room
def cool_room():
    clipped(SH.cool_room())
    import bk_models as BM
    custom('coolroom', *BM.CENTRES['coolroom'], 0, 0)
    x0, y0, x1, y1 = L.CR
    dx, dhw, dh = L.CR_DOOR
    t = L.CR_T
    # inside: stock on the shelves and floor (Splasher ammo, Pad shield)
    for zz in (240, 480):
        for k, nm in enumerate(('butter', 'butter', 'milkcrate' if zz == 240 else 'eggs3')):
            pass
    sx0, sx1 = x1 - t - 176, x1 - t - 16
    for zz in (240, 480):
        for k in range(4):
            prop('butter', (sx0 + sx1) / 2, -1860 + k * 150, zz, ang=90, search=20, clip=False, r=30, h=30)
    for (nm, x, y) in (('milkcrate', 1500, -1300), ('eggs', 1500, -1650), ('cake_pink', 1750, -1850), ('boxes3', 1450, -1900), ('berrycrate', 1820, -1350)):
        prop(nm, x, y, 0, search=200)
    item('ammo_splasher', 1700, -1600, 0); item('item_armor_padshield', 1950, -1550, 0)
    light(1650, -1400, 800, 500, '0.75 0.9 1'); light(1800, -1800, 800, 450, '0.75 0.9 1')
    speaker(1800, -1600, 400, 'machine/freezer', volume=0.5)
    route('coolroom', (dx, -900, 0), (1650, -1450, 0))
    # roof: Splasher, pads up from the floor and from the east counter
    weapon('splasher', 1950, -1700, L.CR_H, 'green')
    prop('eggs3', 2180, -1930, L.CR_H, ang=0, search=40); prop('boxes2', 1430, -1950, L.CR_H, ang=10, search=40)
    item('ammo_pumper', 1500, -1300, L.CR_H)
    jumppad(1090, -1250, 0, (1500, -1350, L.CR_H), 1150, 'p_crroof')
    jumppad(1850, -660, L.WORK, (1900, -1300, L.CR_H), 1060, 'p_crroof2')


# =================================================================================================== cooling racks
def racks():
    clipped(SH.racks())
    for i, (cx, cy, yaw) in enumerate(L.RACKS):
        custom('rack', cx, cy, 0, yaw)
        x0, y0, x1, y1 = SH.rack_rect(i)
        occupy(x0 - 10, y0 - 10, x1 + 10, y1 + 10, 0, L.RACK_TOP)
        # pastries on the trays (decor, nonsolid)
        for j, zl in enumerate(L.RACK_TRAYS[1:]):
            nm = ['croissant', 'cup_pink', 'loaf', 'donut_choc'][(i + j) % 4]
            sp = {'croissant': 120, 'cup_pink': 90, 'loaf': 230, 'donut_choc': 100}[nm]
            long_x = (x1 - x0) >= (y1 - y0)
            n = int(((x1 - x0) if long_x else (y1 - y0)) - 80) // sp
            for k in range(n):
                for row in (-1, 1):
                    u = -((n - 1) * sp) / 2 + k * sp
                    off = row * ((y1 - y0) if long_x else (x1 - x0)) * 0.25
                    px, py = (cx + u, cy + off) if long_x else (cx + off, cy + u)
                    custom(nm, px, py, zl, 0 if long_x else 90)
        zt = L.RACK_TOP
    custom('cookies', -1980, -1050, L.RACK_TOP, 0); custom('cookies', -1560, -1700, L.RACK_TOP, 90)
    item('item_climber', -2050, -1050, L.RACK_TOP); item('ammo_boaster', -1900, -1000, L.RACK_TOP)
    item('holdable_boomies', -1560, -1600, L.RACK_TOP); item('ammo_imperius', -1560, -1800, L.RACK_TOP)
    item('ammo_nipper', -1960, -1060, 16)
    jumppad(-1440, -1060, 0, (-1980, -1060, L.RACK_TOP), 1120, 'p_rackA')
    jumppad(-1560, -1150, 0, (-1560, -1720, L.RACK_TOP), 1180, 'p_rackB')


# =================================================================================================== flour bin + the secret Sugar Vault
def flour_bin_and_vault():
    clipped(SH.flour_bin())
    import bk_models as BM
    custom('flourbin', *BM.CENTRES['flourbin'], 0, 0)
    x0, y0, x1, y1 = L.BIN
    occupy(x0, y0, x1, y1, 0, L.BIN_H + 40)
    sx0, sy0, sx1, sy1 = L.BIN_STAIR
    occupy(sx0 - 10, sy0 - 10, sx1 + 10, sy1, 0, L.BIN_H)
    route('bin_stair', ((sx0 + sx1) / 2, sy0 - 100, 0), ((sx0 + sx1) / 2, sy1 - 16, L.BIN_H))
    ix0, iy0, ix1, iy1 = x0 + L.BIN_T, y0 + L.BIN_T, x1 - L.BIN_T, y1 - L.BIN_T
    trig = (ix0 + 8, iy0 + 8, L.BIN_FLOOR + 92), (ix1 - 8, iy1 - 8, L.BIN_FLOOR + 140)
    speaker((ix0 + ix1) / 2, (iy0 + iy1) / 2, L.BIN_FLOOR + 140, 'misc/secret_found', loop=False, targetname='secret_snd')
    M.ent('trigger_multiple', brushes=[box(*trig, TRIG)], target='secret_snd', wait=2)
    M.ent('trigger_teleport', brushes=[box((ix0 + 24, iy0 + 24, L.BIN_FLOOR + 2), (ix1 - 24, iy1 - 24, L.BIN_FLOOR + 90), TRIG)], target='vault_in')
    # the vault (sealed, below the world)
    vx0, vy0, vx1, vy1, z0, z1 = L.VAULT
    W = 32
    wl = {'side': T('choc_wall'), 'top': CAULK, 'bot': CAULK}
    A(box((vx0 - W, vy0 - W, z0 - W), (vx1 + W, vy1 + W, z0), {'top': T('gold_tile'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((vx0 - W, vy0 - W, z1), (vx1 + W, vy1 + W, z1 + W), {'bot': T('choc_wall'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((vx0 - W, vy0 - W, z0), (vx0, vy1 + W, z1), dict(wl, w=CAULK), detail=False))
    A(box((vx1, vy0 - W, z0), (vx1 + W, vy1 + W, z1), dict(wl, e=CAULK), detail=False))
    A(box((vx0, vy0 - W, z0), (vx1, vy0, z1), dict(wl, s=CAULK), detail=False))
    A(box((vx0, vy1, z0), (vx1, vy1 + W, z1), dict(wl, n=CAULK), detail=False))
    prop('fountain', 0, 120, z0, ang=0, force=True)
    for (nm, x, y) in (('goldcake', -400, 260), ('rockcandy', 420, 300), ('rockcandy_b', -460, -300), ('rockcandy', 470, -320),
                       ('coins', 230, 330), ('coins', -230, -250), ('cake_choc', 420, -40)):
        prop(nm, x, y, z0, search=80)
    item('item_padpower', 0, -120, z0); item('item_revival', -280, 0, z0); item('holdable_killerducks', 260, 80, z0)
    item('ammo_imperius', -500, 40, z0); item('ammo_splasher', 520, 180, z0); item('ammo_betty', 0, -330, z0)
    A(sign_box((-360, vy1 - 6, z0 + 300), (360, vy1, z0 + 420), T('sign_vault'), 1024, 192, facing='s'))
    M.ent('misc_teleporter_dest', (0, -260, z0 + 24), targetname='vault_in', angle=90)
    mdl_c('pad_teleporter/padtp_pink.md3', 0, vy0 + 50, z0, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((-36, vy0 + 14, z0 + 2), (36, vy0 + 86, z0 + 90), TRIG)], target='vault_out')
    occupy(-60, vy0, 60, vy0 + 110, z0, z0 + 120)
    M.ent('misc_teleporter_dest', (-1900, 1080, 24), targetname='vault_out', angle=270)
    for (x, y, c) in ((0, 0, '1 0.85 0.6'), (-400, 260, '1 0.8 0.4'), (420, 300, '1 0.6 0.9'), (-460, -300, '1 0.6 0.9'), (420, -40, '1 0.85 0.6')):
        light(x, y, z0 + 300, 420, c)
    speaker(0, -380, z0 + 200, 'ambient/water_bubbling', volume=0.4)
    timer_sound(0, 0, z0 + 150, 'human/applause', 'vault_cheer', 40, 10, volume=0.4)


# =================================================================================================== floor cover, lights, sounds
def floor_cover():
    """cover on the kitchen floor: sacks, egg trays, milk crates, cake boxes, an upturned copper bowl, cupcakes"""
    pieces = [('sack_flour', -1600, 900, 30), ('sack_flour', -1580, 900, 30), ('sugar_bag', -1350, 1250, 0), ('eggs', 700, 1100, 0),
              ('milkcrate', -600, -500, 15), ('boxes3', 900, -500, 0), ('bowl_up', 950, 700, 0), ('boxes2', -700, 900, 40),
              ('eggs3', 1450, -900, 0), ('milkcrate', 1100, 1150, 0), ('rollpin', 600, -350, 30), ('sack_sugar', -1300, -500, 60),
              ('sugar_bag', -2100, -500, 0), ('boxes2', -2150, 820, 0), ('eggs', -1750, 1300, 0), ('bowl_up', -400, -820, 0),
              ('sack_flour', 1350, -650, 90)]
    for (nm, x, y, a) in pieces:
        prop(nm, x, y, 0, ang=a, search=200)
    # stacked sacks: a second sack on the first pile
    groups = [(-850, -200), (750, 1300), (-1350, 450), (1400, 420), (-500, 1200), (300, -650), (-1500, -1450), (900, -880)]
    for i, (x, y) in enumerate(groups):
        for k in range(3):
            nm = ['cup_pink', 'cup_choc', 'cup_mint', 'cup_lemon', 'cup_blue'][(i + k) % 5]
            prop(nm, x + 60 * math.cos(k * 2.1 + i), y + 60 * math.sin(k * 2.1 + i), 0, search=120)
    for i, (x, y) in enumerate(((-300, 1000), (1050, 200), (-1100, -300), (500, -900))):
        prop(['donut_pink', 'donut_choc', 'donut_white'][i % 3], x, y, 0, search=120)
    cat('gummybears/redbear.md3', -1300, 150, 0, 1.0); cat('gummybears/greenbear.md3', 1150, -200, 0, 1.0)
    cat('gummybears/ldyellowbear.md3', 600, 1250, 0, 1.0); cat('gummybears/orangebear.md3', -350, -1000, 0, 1.0)
    cat('pad_ddmix/gallery/fire_extinguisher.md3', -1560, -700, 0, 4.0, 0)
    cat('pad_ddmix/diner/muffin_choco.md3', 1300, 1000, 0, 1.0); cat('pad_ddmix/diner/muffin_blueberry.md3', -900, 300, 0, 1.0)
    cat('pad_fruits/banana.md3', 1150, -1050, 0, 1.0); cat('pad_cake/pad_cakesliceup.md3', 480, -400, 0, 1.6)
    cat('pad_cutlery/pad_fork.md3', 700, 150, 0, 1.6, 30, clip=False)


def blockers():
    """floor cover where long eye-level lines run (sightlines.py --hot cells): sack piles, ingredient bins, boxes"""
    for (nm, x, y, a) in (('sackpile', -830, 470, 20), ('ingbin', -1400, 620, 90), ('ingbin_f', -1450, -520, 0), ('sackpile', -600, 760, 70),
                          ('boxes3', 1250, 320, 15), ('ingbin', 1580, 1180, 0), ('sackpile', -1560, 1180, 0), ('tins', -560, -150, 0),
                          ('boxes3', 600, 750, 40), ('ingbin_f', 650, -1000, 90),
                          ('sackpile', 1580, 380, 90), ('boxes2', 1560, -560, 0), ('ingbin', 1560, 1180, 0)):
        prop(nm, x, y, 0, ang=a, search=400)


def items_misc():
    item('ammo_nipper', -400, -300, 0); item('ammo_nipper', 1300, 1300, 0)
    item('item_armor_shard', -1600, 400, 0); item('item_armor_shard', 800, -700, 0)
    item('ammo_balloony', -2100, 1300, 0); item('ammo_betty', -500, 650, 0); item('ammo_bubbleg', 1500, 600, 0)
    item('ammo_splasher', 1300, -1100, 0); item('ammo_boaster', -2000, -1600, 0); item('ammo_pumper', 650, 900, 0)
    station(-1300, -850, 0, 90); station(1450, 650, 0, 180)
    for (x, y, a) in ((-600, -300, 90), (600, 0, 180), (-1350, 700, 0), (1300, -400, 180), (-300, 1050, 270), (1000, 1000, 225),
                      (-1900, -350, 0), (1150, -1700, 135), (-700, -1700, 45), (300, -1750, 90), (-1900, 900, 300), (-1300, -1300, 60)):
        spawn(x, y, 0, a)


def lights_and_sound():
    import bk_props as BP
    drop = 380
    for (x, y) in ((-1250, -250), (-1250, 1000), (-200, 1050), (900, 1050), (900, -300), (-200, -450), (1450, 250), (-550, -1780),
                   (550, -1780), (-1750, -1300), (1600, -1200)):
        p = (x, y)
        custom('pendant', p[0], p[1], L.CEIL, 0, lit=False)
        light(p[0], p[1], L.CEIL - drop + 10, 7000, '1 0.9 0.75')
    for x in (-1700, -570, 570, 1700):
        for y in (-1500, -500, 500, 1500):
            light(x, y, 1250, 2600, '1 0.95 0.86')
    custom('clock', 1150, L.HY, 1600, 0)
    custom('walldeco', 0, 0, 0, 0)
    speaker(1150, 1990, 1600, 'machine/clock_ticking', volume=0.3)
    speaker(0, 300, 1700, 'machine/ventilation', volume=0.2)
    speaker(-1400, 0, 700, 'machine/fan_pc', volume=0.15)


def reserve():
    """occupy every architecture volume before any prop is placed"""
    for f in (SH.oven, SH.counters, SH.cake, SH.mixer, SH.display_cabinet, SH.cool_room, SH.racks, SH.flour_bin):
        for b in f():
            mn, mx = b.bounds()
            occupy(mn[0], mn[1], mx[0], mx[1], mn[2], mx[2])
    occupy_r(L.CAKE[0], L.CAKE[1], L.TIERS[0][0] + 30, 0, L.TIERS[2][2] + 160)
    for i in range(len(L.RACKS)):
        x0, y0, x1, y1 = SH.rack_rect(i)
        occupy(x0 - 10, y0 - 10, x1 + 10, y1 + 10, 0, L.RACK_TOP)


def main():
    bklib.STATE['out'] = OUT
    TX.make_textures()
    import bk_models as BM
    import bk_props as BP
    BM.make(); BP.make()
    import bk_deluxe as DX
    DX.make()
    room()
    reserve()
    oven(); counters(); cake(); mixer(); display_cabinet(); cool_room(); racks(); flour_bin_and_vault()
    DX.place(sys.modules[__name__])
    items_misc(); blockers(); floor_cover(); lights_and_sound()
    moved = fix_items()
    for mv in moved: print('moved', mv)
    write_routes()
    TX.make_shader(); TX.make_arena()
    M.ent('info_player_intermission', (900, -1500, 1300), angles='20 125 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(M.text(f"// {TX.LONGNAME} - generated by wop_tools/padbakery/build_bakery.py\n"))
    nbr = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nbr}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', tuple(round(v) for v in o), 'target', tg, 'land', tuple(round(v) for v in land))
    cnt = {}
    for (c, *_r) in SPOTS['ammo']: cnt[c] = cnt.get(c, 0) + 1
    print('weapons', [w for (w, *_r) in SPOTS['weapon']], 'ammo', cnt, 'spawns', len(SPOTS['spawn']))


if __name__ == '__main__':
    main()
