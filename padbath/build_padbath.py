#!/usr/bin/env python3
"""Battle in the Bathtub - World of Padman Capture the Lolly map generator (map 'wop_padbath').

    OUT=/path/to/out python3 build_padbath.py

Writes <OUT>/maps/wop_padbath.map, textures/padbath/*, scripts/padbath.shader, scripts/wop_padbath.arena.

A giant bathtub in a tiled bath alcove (shower curtain on the open side). x east, y north, water surface z 0.
The map is point-symmetric about (0, 0): every red-side piece is built by a function taking s = +1 (red, west)
and rotated 180 degrees for blue (s = -1, east).
  ends      the two toy battleships (red S.S. Rubber Ruby west, blue H.M.S. Bubble Blue east), anchored broadside:
            bridge house with the team lolly inside (3 doors), outside stairs to the bridge roof, two gun turrets
            (crate steps), funnel, mast + flag, stern boarding ramp out of the water, roof pad up to a wall shelf
  lanes     two toy ferries (func_bobbing along x, 22 s round trip, half a period apart) shuttle between the ships'
            inboard sides: the main way across. Bots ride them (bspc "funcbob" reachabilities).
  centre    floating rainbow ring-stacker: ramps out of the water, pads to the top (Imperius), killer ducks on a ring,
            the neutral lolly (1LC) on the float; under it on the tub floor the drain hides a Betty + Pad Power
  north     a bar of PADSOAP (ramps both ends, pad to the rim); above it the tap spout = sniper perch (Splasher)
  south     a sponge (same shape); above it the rain shower head = the matching perch
  rim       enamel rim around the tub with bath clutter, reached from the soap / sponge pads
Swimming ship to ship works but is slow (about 3200u of water); every water edge has a ramp out.
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import bath_textures as TX

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padbath'
T = lambda n: 'padbath/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'; NODRAW = 'common/nodraw'
NODRAW_NS = T('nodraw_ns'); BOTCLIP = 'common/botclip'

for k, v in {'tile_wall': (1, 1), 'tile_blue': (1, 1), 'ceiling': (2, 2), 'enamel': (2, 2), 'enamel_floor': (1, 1),
             'curtain': (1, 1.5), 'hull_red': (1, 1), 'hull_blue': (1, 1), 'hull_bottom': (1, 1), 'deck': (0.75, 0.75),
             'ship_grey': (1, 1), 'porthole_red': (0.75, 0.75), 'porthole_blue': (0.75, 0.75), 'turret': (1, 1), 'crate': (0.5, 0.5),
             'crate_side': (0.25, 0.25), 'boat_yellow': (0.75, 0.75), 'boat_green': (0.75, 0.75), 'boat_deck': (0.75, 0.75),
             'soap': (1.5, 1.5), 'sponge': (1, 1), 'sponge_green': (1, 1), 'suds': (1, 1), 'water': (2, 2),
             'float_white': (1, 1), 'ring_red': (1, 1), 'ring_orange': (1, 1), 'ring_yellow': (1, 1), 'ring_green': (1, 1),
             'ring_blue': (1, 1), 'ring_purple': (1, 1), 'funnel_red': (0.5, 1), 'funnel_blue': (0.5, 1), 'wood_light': (0.5, 0.5),
             'bottle_teal': (0.5, 0.5), 'bottle_pink': (0.5, 0.5), 'chrome': (0.5, 0.5), 'buoy': (0.5, 0.5)}.items():
    wopmap.TEXSCALE[T(k)] = v

M = Map({'message': 'Battle in the Bathtub', '_ambient': '10', '_color': '0.95 0.97 1', 'gridsize': '96 96 96', '_blocksize': '0'})
A = M.add
# ---------------------------------------------------------------------------------------------------- layout
RX, RYN, RYS = 2720, 1312, -1376          # room: walls at x +-RX, y RYN (north), RYS (south, behind the curtain)
FZ, WZ, RIMZ, CZ = -320, 0, 320, 1664     # tub floor, water surface, rim top, ceiling
TXI, TYI = 2496, 1088                     # tub inner half sizes
CURT = -1312                              # curtain front (south rim walkway is CURT..-TYI)
SX = -1856                                # red ship centre x (blue at -SX)
DECK = 128
HIN, HOUT = SX + 224, SX - 224            # red hull inboard / outboard x
STERN, BOW0, BOWTIP = -640, 640, 896      # red ship: stern y, bow taper start, bow tip (blue = rotated)
LANE = (368, 592)                         # ferry lane |y| range (north lane for red's bow side)
BOAT_HX = 128                             # ferry half length along x (short: bots must cross it within ~1 s at the dock)
PIER = 224                                # landing pier in front of each dock (x HIN..HIN+PIER)
BOB_H = -(HIN + PIER + 2 + BOAT_HX)       # 1278: ferry centre at the red pier (2u gap: nothing to fall through)
BOB_T = 16                                # bob period (s): a ferry leaves each ship every 8 s
# third route: a shuttle from each ship's inboard side to the ring-stacker hub (low boats, deck z 48)
SH_HY, SH_HX, SH_DECK = 112, 128, 48
SH_W = HIN + PIER + 2 + SH_HX                    # shuttle centre at the ship stage (-1278)
SH_E = -(BASE_R_AP := 329.5) - 72 - 2 - SH_HX    # shuttle centre at the hub stage (-530)
SH_MID, SH_H, SH_T = (SH_W + SH_E) / 2, (SH_E - SH_W) / 2, 10
PERCH_Z = 832                             # tap spout / shower head perch top
SHELF_Z = 832                             # wall shelf top
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []


# =================================================================================================== helpers
def rtex(s, tex):
    """rotate directional texture dict keys for the blue side"""
    if s > 0 or not isinstance(tex, dict): return tex
    sw = {'n': 's', 's': 'n', 'e': 'w', 'w': 'e'}
    return {sw.get(k, k): v for k, v in tex.items()}


def sb(s, x0, y0, z0, x1, y1, z1, tex, detail=True):
    xa, xb = sorted((s * x0, s * x1)); ya, yb = sorted((s * y0, s * y1))
    return box((round(xa), round(ya), z0), (round(xb), round(yb), z1), rtex(s, tex), detail)


def sh(s, pts, tex, rnd=True):
    return hull([(s * x, s * y, z) for (x, y, z) in pts], rtex(s, tex), round_pts=rnd)


def scyl(s, x, y, r, z0, z1, tex, n=12, phase=None):
    return cyl(s * x, s * y, r, z0, z1, rtex(s, tex), n, phase=phase)


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


def smdl(s, path, x, y, zsurf, scale=1.0, angle=0, solid=False, shrink=0.12):
    ang = (angle + (180 if s < 0 else 0)) % 360
    if solid: return solid_mdl(path, s * x, s * y, zsurf, scale, ang, shrink)
    return mdl_c(path, s * x, s * y, zsurf, scale, ang)


def solid_mdl(path, x, y, zsurf, scale=1.0, angle=0, shrink=0.12):
    """mdl_c + a weapon-clip box around the model's rotated bounds so players and shots collide"""
    e = mdl_c(path, x, y, zsurf, scale, angle)
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


def light(x, y, z, val, color='1 0.97 0.92', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def item(s, cls, x, y, floor, **kw):
    M.ent(cls, (round(s * x), round(s * y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, s * x, s * y, floor))


def weapon(s, w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(s * x), round(s * y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, s * x, s * y, floor))


def spawn(s, cls, x, y, floor, ang):
    M.ent(cls, (round(s * x), round(s * y), floor + 25), angle=(ang + (180 if s < 0 else 0)) % 360)
    SPOTS['spawn'].append((s * x, s * y, floor))


def fit_top(b, x0, y0, x1, y1, tw, th, tex=None, flip=False):
    for f in b.faces:
        if f.n[2] > 0.9:
            if tex: f.tex = tex
            sx = (x1 - x0) / tw; sy = (y1 - y0) / th
            if flip:      # rotated 180: texture reads from the other side
                f.sc = (-sx, -sy); f.off = (round((x1 / sx) % tw, 3), round((-y0 / sy) % th, 3))
            else:
                f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def ring_pts(cx, cy, r, z, n=16, ph=None):
    return [(x, y, z) for (x, y) in ngon(cx, cy, r, n, ph)]


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
    if glow: light(x, y, z + 48, 90, '0.5 0.85 1')


def spad(s, x, y, z, land, apex, name):
    jumppad(s * x, s * y, z, (s * land[0], s * land[1], land[2]), apex, name)


def seg_wall(s, p0, p1, thick, z0, z1, tex, side=1):
    """thin wall along the segment p0->p1 (2D), extruded z0..z1, on the left (side=1) or right (-1) of the segment"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy)
    nx, ny = -dy / L * side * thick, dx / L * side * thick
    q = [(x0, y0), (x1, y1), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)]
    return sh(s, [(x, y, z) for (x, y) in q for z in (z0, z1)], tex)


# =================================================================================================== room + tub
def room_shell():
    W = 32
    A(box((-RX - W, RYS - W, FZ - 16), (RX + W, RYN + W, FZ), {'top': T('enamel_floor'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((-RX - W, RYS - W, CZ), (RX + W, RYN + W, CZ + 16), {'bot': T('ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((-RX - W, RYN, FZ), (RX + W, RYN + W, CZ), {'side': CAULK, 's': T('tile_wall')}, detail=False))
    A(box((-RX - W, RYS - W, FZ), (RX + W, RYS, CZ), {'side': CAULK, 'n': T('tile_wall')}, detail=False))
    A(box((RX, RYS, FZ), (RX + W, RYN, CZ), {'side': CAULK, 'w': T('tile_wall')}, detail=False))
    A(box((-RX - W, RYS, FZ), (-RX, RYN, CZ), {'side': CAULK, 'e': T('tile_wall')}, detail=False))
    # blue tile wainscot (4u) + duck border (8u) on the three tiled walls above the rim; the south wall above the curtain
    # rail is plain tile.
    # north wall
    A(box((-RX, RYN - 4, RIMZ), (RX, RYN, 704), {'side': T('tile_blue'), 'top': T('tile_blue'), 'bot': CAULK}))
    A(box((-RX + 8, RYN - 8, 704), (RX - 8, RYN, 768), {'side': T('tile_border'), 'top': T('tile_blue'), 'bot': T('tile_blue')}))
    # west / east walls (from the curtain to the north wall panel)
    for (xa, xb, xc, xd) in ((-RX, -RX + 4, -RX, -RX + 8), (RX - 4, RX, RX - 8, RX)):
        A(box((xa, CURT, RIMZ), (xb, RYN - 4, 704), {'side': T('tile_blue'), 'top': T('tile_blue'), 'bot': CAULK}))
        A(box((xc, CURT, 704), (xd, RYN - 8, 768), {'side': T('tile_border'), 'top': T('tile_blue'), 'bot': T('tile_blue')}))
    # rims (enamel) - north spans the full width, south too (curtain sits on its back strip), west/east between them
    rim = {'top': T('enamel'), 'side': T('enamel'), 'bot': CAULK}
    A(box((-RX, TYI, FZ), (RX, RYN, RIMZ), rim))
    A(box((-RX, RYS, FZ), (RX, -TYI, RIMZ), rim))
    for s in (1, -1):
        A(sb(s, -RX, -TYI, FZ, -TXI, TYI, RIMZ, rim))
    # rounded inner corners (vertical fillets) + a cove along the floor
    for sx in (1, -1):
        for sy in (1, -1):
            c = 224
            pts = [(sx * TXI, sy * TYI), (sx * (TXI - c), sy * TYI), (sx * TXI, sy * (TYI - c))]
            A(hull([(x, y, z) for (x, y) in pts for z in (FZ, RIMZ)], T('enamel')))
    cv = 48
    for s in (1, -1):
        # north / south cove (between the corner fillets)
        A(sh(s, [(x, y, z) for x in (-TXI + 224, TXI - 224) for (y, z) in ((TYI, FZ), (TYI - cv, FZ), (TYI, FZ + cv))], T('enamel')))
        A(sh(s, [(x, y, z) for y in (-TYI + 224, TYI - 224) for (x, z) in ((-TXI, FZ), (-TXI + cv, FZ), (-TXI, FZ + cv))], T('enamel')))
    # rim edge roll (rounded lip along the inner rim edge, 16u proud of the wall, nonsolid feel)
    # water
    A(box((-TXI, -TYI, FZ), (TXI, TYI, WZ), T('water')))


def curtain():
    """pleated shower curtain on the south rim's back strip, chrome rail + rings"""
    zb, zt = RIMZ, CZ                     # pleats run up to the ceiling: nothing to stand on up there
    per, dep = 128, 48
    x = -RX
    k = 0
    while x < RX:
        x1 = min(x + per // 2, RX)
        if k % 2 == 0:
            q = [(x, RYS), (x1, RYS), (x1, RYS + dep)]
        else:
            q = [(x, RYS), (x1, RYS), (x, RYS + dep)]
        A(hull([(px, py, z) for (px, py) in q for z in (zb, zt)], {'side': T('curtain'), 'top': T('curtain'), 'bot': T('curtain')}))
        k += 1; x = x1
    # rail just in front of the curtain top + rings
    A(box((-RX, RYS + 48, CZ - 28), (RX, RYS + 60, CZ - 16), T('rail')))       # rail just under the ceiling
    for xx in range(-RX + 64, RX, 128):
        A(box((xx - 6, RYS + 48, CZ - 16), (xx + 6, RYS + 60, CZ), T('rail')))
    # tiled bulkhead above the rail is the south wall itself


# =================================================================================================== ships
def ship(s):
    team = 'red' if s > 0 else 'blue'
    hull_t = T('hull_' + team); trim = T('trim_' + team)
    up = {'side': hull_t, 'top': T('deck'), 'bot': CAULK}
    lo = {'side': T('hull_bottom'), 'top': CAULK, 'bot': T('hull_bottom')}
    # straight hull: the ships float with a 96u draft, sides tucked in 32u at the keel. Under each ship a botclip block
    # (invisible, players swim through it) keeps bots from routing under the hull, where they would drown.
    KEEL = -96
    A(sh(s, [(SX + sg * bw, y, z) for sg in (-1, 1) for y in (STERN, BOW0) for (bw, z) in ((192, KEEL), (224, 0))], lo))
    A(sh(s, [(SX + sg * 224, y, z) for sg in (-1, 1) for y in (STERN, BOW0) for z in (0, DECK)], up))
    # raked bow
    A(sh(s, [(SX - 192, BOW0, KEEL), (SX + 192, BOW0, KEEL), (SX - 224, BOW0, 0), (SX + 224, BOW0, 0), (SX, 820, KEEL), (SX, 862, 0)], lo))
    A(sh(s, [(SX + sg * 224, y, z) for sg in (-1, 1) for y in (STERN, BOW0) for z in (FZ, KEEL)], BOTCLIP))
    A(sh(s, [(SX - 224, BOW0, FZ), (SX + 224, BOW0, FZ), (SX - 224, BOW0, KEEL), (SX + 224, BOW0, KEEL), (SX, 862, FZ), (SX, 862, KEEL)], BOTCLIP))
    A(sh(s, [(SX - 224, BOW0, 0), (SX + 224, BOW0, 0), (SX - 224, BOW0, DECK), (SX + 224, BOW0, DECK), (SX, 862, 0), (SX, BOWTIP, DECK)], up))
    # bulwarks (16u) with gaps at both ferry docks and the stern ramp
    bt = {'side': trim, 'top': trim, 'bot': CAULK}
    A(sb(s, HOUT, STERN, DECK, HOUT + 8, BOW0, DECK + 16, bt))
    for (y0, y1) in ((STERN, -LANE[1] - 16), (-LANE[0] + 16, -SH_HY - 16), (SH_HY + 16, LANE[0] - 16), (LANE[1] + 16, BOW0)):
        A(sb(s, HIN - 8, y0, DECK, HIN, y1, DECK + 16, bt))
    # bow bulwarks: outer edge on the hull edge, inner edge 8u inside, cut at y = BOW0 and at the centreline
    L = math.hypot(224, BOWTIP - BOW0); off = 8 * L / (BOWTIP - BOW0)      # horizontal inset of the inner edge
    for sg in (-1, 1):
        xo, xi = SX + sg * 224, SX + sg * (224 - off)
        tip_in = BOW0 + (BOWTIP - BOW0) * (224 - off) / 224
        q = [(xo, BOW0), (SX, BOWTIP), (SX, tip_in), (xi, BOW0)]
        A(sh(s, [(x, y, z) for (x, y) in q for z in (DECK, DECK + 16)], bt, rnd=False))
    RX0, RX1 = SX - 64, SX + 96                        # stern ramp x range
    A(sb(s, HOUT + 8, STERN, DECK, RX0, STERN + 8, DECK + 16, bt))
    A(sb(s, RX1, STERN, DECK, HIN - 8, STERN + 8, DECK + 16, bt))
    # stern boarding ramp: out of the water up to the deck
    rb = ramp(RX0, -1040, RX1, STERN, KEEL, -72, DECK, 'n', {'top': T('deck'), 'side': hull_t, 'bot': T('hull_bottom')})
    if s < 0: rb = ramp(-RX1, -STERN, -RX0, 1040, KEEL, -72, DECK, 's', {'top': T('deck'), 'side': hull_t, 'bot': T('hull_bottom')})
    A(rb)
    A(sb(s, RX0, -1040, FZ, RX1, STERN, KEEL, BOTCLIP))
    # landing piers in front of both docks (standing on the tub floor). bspc links the ferry to every grounded area
    # within 192u of its end position; a clean pier keeps those links short so bots step on and off in time.
    # the pier is exactly as wide as the ferry at its dock edge, so a bot walking from anywhere near it to the ferry's
    # centre never steps into a slot of water beside the boat
    pt = {'top': T('boat_deck'), 'side': T('wood_light'), 'bot': CAULK}
    for (ya, yb) in (LANE, (-LANE[1], -LANE[0])):
        A(sb(s, HIN, ya, FZ, HIN + PIER, yb, DECK, pt))
    # ramps out of the water on the piers' outer sides, set back 64u from the dock edge
    RL = 288
    if s > 0:
        A(ramp(HIN, LANE[1], HIN + PIER - 64, LANE[1] + RL, FZ, -72, DECK, 's', pt))
        A(ramp(HIN, -LANE[1] - RL, HIN + PIER - 64, -LANE[1], FZ, -72, DECK, 'n', pt))
    else:
        A(ramp(-HIN - PIER + 64, -LANE[1] - RL, -HIN, -LANE[1], FZ, -72, DECK, 'n', pt))
        A(ramp(-HIN - PIER + 64, LANE[1], -HIN, LANE[1] + RL, FZ, -72, DECK, 's', pt))
    # ship name board on the inboard hull side (between the docks)
    if s > 0:
        A(sign_box((HIN, 140, 40), (HIN + 4, 332, 76), T('name_red'), 512, 96, back=trim, facing='e'))
    else:
        A(sign_box((-HIN - 4, -332, 40), (-HIN, -140, 76), T('name_blue'), 512, 96, back=trim, facing='w'))
    # shuttle stage: low landing exactly as wide as the shuttle, stairs up to the deck at its back
    A(sb(s, HIN, -SH_HY, FZ, HIN + PIER, SH_HY, SH_DECK, pt))
    for b in stairs(HIN, -SH_HY, HIN + 160, SH_HY, SH_DECK, DECK, 'w', pt, base=SH_DECK):
        mn, mx = b.bounds()
        A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], pt))
    # ---- bridge house x SX-128..SX+128, y -128..192, walls 16, interior z 128..288, roof slab 288..304
    hx0, hx1, hy0, hy1, hz1 = SX - 128, SX + 128, -128, 192, 288
    wall = {'side': T('ship_grey'), 'top': T('ship_grey'), 'bot': CAULK}
    port = T('porthole_' + team)
    def hw(x0, y0, z0, x1, y1, z1, outer):
        tex = dict(wall); tex[outer] = port
        b = sb(s, x0, y0, z0, x1, y1, z1, tex)
        for f in b.faces:
            if f.tex == port: f.off = (f.off[0], 136)       # porthole row at z ~210
        A(b)
    # west wall (outboard, solid)
    hw(hx0, hy0, DECK, hx0 + 16, hy1, hz1, 'w')
    # east wall with inboard door y -16..80, z 128..240
    hw(hx1 - 16, hy0, DECK, hx1, -16, hz1, 'e'); hw(hx1 - 16, 80, DECK, hx1, hy1, hz1, 'e')
    hw(hx1 - 16, -16, 240, hx1, 80, hz1, 'e')
    # south (aft) wall with door x SX-48..SX+48
    for (y0, y1, outer) in ((hy0, hy0 + 16, 's'), (hy1 - 16, hy1, 'n')):
        A(sb(s, hx0 + 16, y0, DECK, SX - 48, y1, hz1, wall)); A(sb(s, SX + 48, y0, DECK, hx1 - 16, y1, hz1, wall))
        A(sb(s, SX - 48, y0, 240, SX + 48, y1, hz1, wall))
    # window band on the fore wall above the door is the bridge (texture strip on a 4u proud panel)
    A(sb(s, hx0 + 16, hy1, 248, hx1 - 16, hy1 + 4, 284, {'side': T('ship_grey'), 'n': T('bridge_windows')}))
    # roof
    A(sb(s, hx0, hy0, hz1, hx1, hy1, hz1 + 16, {'top': T('deck'), 'side': trim, 'bot': T('ship_grey')}))
    # interior floor mat + chart table (cover)
    A(sb(s, SX - 112, 120, DECK, SX - 40, 176, DECK + 40, {'side': T('wood_light'), 'top': T('wood_light'), 'bot': CAULK}))
    # ---- outside stairs (outboard walkway) deck -> roof
    for b in stairs(HOUT + 8, -160, hx0, hy1, DECK, hz1 + 16, 'n', {'side': T('ship_grey'), 'top': T('deck')}):
        A(sb(s, *b.bounds()[0][:2], b.bounds()[0][2], *b.bounds()[1], {'side': T('ship_grey'), 'top': T('deck'), 'bot': CAULK}))
    # ---- funnel aft of the house
    A(scyl(s, SX - 94, -240, 56, DECK, 432, {'side': T('funnel_' + team), 'top': T('ship_dark'), 'bot': CAULK}, 12))
    # ---- turrets fore/aft (96 tall) with twin barrels pointing inboard, crate steps outboard
    for ty in (432, -432):
        A(scyl(s, SX - 32, ty, 112, DECK, DECK + 96, {'side': T('turret'), 'top': T('turret'), 'bot': CAULK}, 12))
        for dy in (-36, 36):
            A(sb(s, SX + 78, ty + dy - 10, 192, HIN - 8, ty + dy + 10, 212, T('ship_dark')))
        sg = 1 if ty > 0 else -1
        ya, yb = sorted((ty - sg * 96, ty - sg * 32))
        A(sb(s, HOUT + 8, ya, DECK, HOUT + 72, yb, DECK + 32, {'side': T('crate_side'), 'top': T('crate'), 'bot': CAULK}))
        ya, yb = sorted((ty - sg * 32, ty + sg * 32))
        A(sb(s, HOUT + 8, ya, DECK, HOUT + 72, yb, DECK + 64, {'side': T('crate_side'), 'top': T('crate'), 'bot': CAULK}))
    # ---- mast with yard and flag in front of the house
    A(scyl(s, SX, 260, 10, DECK, 720, T('ship_dark'), 8))
    A(sb(s, SX - 96, 254, 640, SX - 10, 266, 652, T('ship_dark'))); A(sb(s, SX + 10, 254, 640, SX + 96, 266, 652, T('ship_dark')))
    A(sb(s, SX + 10, 258, 560, SX + 170, 262, 650, T('flag_' + team)))
    # lifebuoys on the house's fore wall either side of the door (flat rings)
    for bx in (SX - 90, SX + 90):
        for k in range(8):
            a0, a1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
            q = [(bx + 30 * math.cos(a0), 190 + 30 * math.sin(a0)), (bx + 30 * math.cos(a1), 190 + 30 * math.sin(a1)),
                 (bx + 18 * math.cos(a1), 190 + 18 * math.sin(a1)), (bx + 18 * math.cos(a0), 190 + 18 * math.sin(a0))]
            A(sh(s, [(x, y, z) for (x, z) in q for y in (hy1, hy1 + 6)], T('buoy'), rnd=False))
    # ---- lights
    light(s * SX, 30, 260, 260, '1 0.95 0.85')
    light(s * (SX + 150), s * 0, 300, 400)
    # ---- team entities
    lol = 'team_CTL_%slolly' % team
    M.ent(lol, (s * SX, s * 40, DECK + 16))
    SPOTS['item'].append((lol, s * SX, s * 40, DECK))
    M.ent('station_health', (s * (HIN - 48), s * -240, DECK), angle=(180 if s > 0 else 0))
    # spawns on the fore and aft decks and the roof, none in the lolly room: defenders respawning beside the lolly
    # killed nearly every carrier the moment it was taken (bot tests)
    for (x, y, z, a) in ((SX + 150, -560, DECK, 0), (SX + 150, 560, DECK, 0), (SX - 150, -600, DECK, 0), (SX - 150, 600, DECK, 0)):
        spawn(s, 'team_%splayer' % team, x, y, z, a)
    for (x, y, z, a) in ((SX + 40, -600, DECK, 0), (SX + 40, 600, DECK, 0), (SX + 60, -70, 304, 0), (SX + 60, 50, 304, 0),
                         (HOUT + 40, 540, DECK, 0), (HIN - 42, 250, DECK, 0)):
        spawn(s, 'team_%sspawn' % team, x, y, z, a)
    # ---- loot
    item(s, 'ammo_pumper', HOUT + 50, -250, DECK)
    weapon(s, 'balloony', SX - 20, 110, 304, 'green')
    item(s, 'ammo_balloony', SX - 90, 80, DECK)
    item(s, 'ammo_bubbleg', SX + 140, -600, DECK)
    item(s, 'ammo_nipper', HOUT + 40, 620, DECK)
    item(s, 'item_armor_shard', SX - 32, 432, DECK + 96)
    item(s, 'item_armor_shard', SX - 32, -432, DECK + 96)
    item(s, 'holdable_floater', SX + 70, 120, DECK)
    # ---- roof pad -> wall shelf behind the ship
    spad(s, SX - 70, -70, 304, (-RX + 100, 0, SHELF_Z), 1000, '%s_shelf' % team)      # clear of the stairs' top step
    # horn (func_timer below)
    speaker(s * (SX - 94), s * -240, 470, 'sound/world/machine/fog_horn.ogg', loop=False, targetname='horn')


def wall_shelf(s):
    """glass shelf on the end wall behind each ship (reached by the roof pad): Boaster"""
    x0, x1 = -RX + 8, -RX + 176
    A(sb(s, -RX, -320, SHELF_Z - 16, x1, 320, SHELF_Z, T('glass_shelf')))
    for by in (-280, 280):
        A(sh(s, [(x0, by - 6, 768), (x0, by + 6, 768), (x0, by - 6, SHELF_Z - 16), (x0, by + 6, SHELF_Z - 16),
                 (x1 - 24, by - 6, SHELF_Z - 16), (x1 - 24, by + 6, SHELF_Z - 16)], T('chrome')))
    smdl(s, 'pad_bath/deocan1.md3', -RX + 40, -250, SHELF_Z, 1.2)
    smdl(s, 'pad_bath/toothpaste_up.md3', -RX + 40, 250, SHELF_Z, 0.9)
    smdl(s, 'pad_bath/electoothbrush.md3', -RX + 36, -150, SHELF_Z, 1.0)
    smdl(s, 'pad_bath/ointment_flat.md3', -RX + 30, 60, SHELF_Z, 1.2, 0)
    smdl(s, 'pad_items/towelstack.md3', -RX + 44, 180, SHELF_Z, 1.0)
    weapon(s, 'boaster', -RX + 110, 130, SHELF_Z, 'orange')
    item(s, 'ammo_boaster', -RX + 110, -190, SHELF_Z)
    light(s * (-RX + 200), 0, SHELF_Z + 140, 300)


# =================================================================================================== ferries
def ferry(s):
    """toy ferry: hull entity (flat top = deck, so bspc's funcbob reachability lines up with the ship decks) +
    cabin entity bobbing in sync. North lane for s=+1 (yellow, phase 0), south lane rotated (green, phase 0.5)."""
    col = T('boat_yellow' if s > 0 else 'boat_green')
    y0, y1 = LANE
    c = 24
    def plan(xa, xb, ya, yb, cc):
        return [(xa + cc, ya), (xb - cc, ya), (xb, ya + cc), (xb, yb - cc), (xb - cc, yb), (xa + cc, yb), (xa, yb - cc), (xa, ya + cc)]
    p = plan(-BOAT_HX, BOAT_HX, y0, y1, c)
    lower = sh(s, [(x, y, z) for (x, y) in p for z in (-2, 8)], {'side': T('hull_bottom'), 'top': CAULK, 'bot': T('hull_bottom')})
    upper = sh(s, [(x, y, z) for (x, y) in p for z in (8, DECK)], {'side': col, 'top': T('boat_deck'), 'bot': CAULK})
    kv = dict(spawnflags=1, height=BOB_H, speed=BOB_T, phase=('0' if s > 0 else '0.5'), dmg=0)
    M.ent('func_bobbing', brushes=[lower, upper], **kv)
    # open wheelhouse across the middle (a roof on four posts): players and bots walk straight through it, and the
    # hull's centre - where riding bots stand - stays clear. It is a separate func_bobbing moving in sync, so the hull
    # model's top stays flat at deck height (bspc builds the ferry links from the model's top).
    py0, py1 = y0 + 8, y1 - 8
    posts = [sb(s, px, py, DECK, px + 10, py + 10, DECK + 96, T('boat_roof')) for px in (-50, 40) for py in (py0, py1 - 10)]
    roof = sb(s, -60, py0 - 4, DECK + 96, 60, py1 + 4, DECK + 108, {'top': T('boat_roof'), 'side': T('boat_roof'), 'bot': T('boat_cabin')})
    fun = scyl(s, 0, y1 - 50, 16, DECK + 108, DECK + 164, {'side': T('funnel_red' if s > 0 else 'funnel_blue'), 'top': T('ship_dark'), 'bot': CAULK}, 8)
    wheel = sb(s, -8, (y0 + y1) / 2 + 60, DECK, 8, (y0 + y1) / 2 + 76, DECK + 40, T('wood_light'))
    M.ent('func_bobbing', brushes=posts + [roof, fun, wheel], **kv)


def shuttle(s):
    """third route: a short low shuttle between the ship's stage and the hub's stage (10 s round trip). Same bot rules
    as the ferries: flat hull entity, canopy on a second func_bobbing in sync, clean stages exactly its width."""
    x0, x1 = SH_MID - SH_HX, SH_MID + SH_HX
    c = 20
    p = [(x0 + c, -SH_HY), (x1 - c, -SH_HY), (x1, -SH_HY + c), (x1, SH_HY - c), (x1 - c, SH_HY), (x0 + c, SH_HY), (x0, SH_HY - c), (x0, -SH_HY + c)]
    lower = sh(s, [(x, y, z) for (x, y) in p for z in (-2, 8)], {'side': T('hull_bottom'), 'top': CAULK, 'bot': T('hull_bottom')})
    upper = sh(s, [(x, y, z) for (x, y) in p for z in (8, SH_DECK)], {'side': T('boat_' + ('red' if s > 0 else 'blue')),
                                                                    'top': T('boat_deck'), 'bot': CAULK})
    kv = dict(spawnflags=1, height=round(SH_H), speed=SH_T, phase=('0' if s > 0 else '0.5'), dmg=0)
    M.ent('func_bobbing', brushes=[lower, upper], **kv)
    m = SH_MID
    posts = [sb(s, m + px, py, SH_DECK, m + px + 10, py + 10, SH_DECK + 96, T('boat_roof')) for px in (-50, 40) for py in (-SH_HY + 8, SH_HY - 18)]
    roof = sb(s, m - 60, -SH_HY + 4, SH_DECK + 96, m + 60, SH_HY - 4, SH_DECK + 108, {'top': T('boat_roof'), 'side': T('boat_roof'), 'bot': T('boat_cabin')})
    flag = sb(s, m - 2, -2, SH_DECK + 108, m + 2, 2, SH_DECK + 180, T('ship_dark'))
    pennant = sb(s, m + 2, -1, SH_DECK + 140, m + 70, 1, SH_DECK + 178, T('flag_' + ('red' if s > 0 else 'blue')))
    M.ent('func_bobbing', brushes=posts + [roof, flag, pennant], **kv)


# =================================================================================================== centre: ring stacker
BASE_R = 336
RINGS = [(256, 48, 144, 'ring_red'), (200, 144, 240, 'ring_orange'), (152, 240, 336, 'ring_yellow'), (112, 336, 432, 'ring_green')]


def ring(r, zb, zt, tex, bev=10):
    return hull(ring_pts(0, 0, r - bev, zb) + ring_pts(0, 0, r, zb + bev) + ring_pts(0, 0, r, zt - bev) + ring_pts(0, 0, r - bev, zt),
                T(tex), round_pts=False)


def centre_tower():
    A(hull(ring_pts(0, 0, BASE_R, FZ) + ring_pts(0, 0, BASE_R, 48), {'side': T('float_white'), 'top': T('float_white'), 'bot': T('float_white')},
           round_pts=False))
    # blue stripe around the float
    for (r, zb, zt, tex) in RINGS:
        A(ring(r, zb, zt, tex))
    ap = BASE_R * math.cos(math.pi / 16)
    ft = {'top': T('float_white'), 'side': T('float_white'), 'bot': T('float_white')}
    u45 = (math.cos(math.radians(45)), math.sin(math.radians(45))); v45 = (-u45[1], u45[0])
    for s in (1, -1):
        # shuttle stage on the face toward each ship
        A(sb(s, -ap - 72, -SH_HY, FZ, -ap - 0.5, SH_HY, 48, ft))
        # ramp out of the water on the diagonal face (45 / 225 deg); it dips below the ferry lanes before reaching them
        pts = []
        for (t, z) in ((ap + 0.5, 48), (ap + 0.5, FZ), (ap + 240, FZ), (ap + 240, -72)):
            for pp in (-64, 64):
                pts.append((-(t * u45[0] + pp * v45[0]), -(t * u45[1] + pp * v45[1]), z))
        A(sh(s, pts, ft, rnd=False))
        spad(s, -208, 208, 48, (0, 0, 432), 560, 'tower_%s' % ('w' if s > 0 else 'e'))
    # loot
    weapon(1, 'imperius', 0, 0, 432, 'purple')
    item(1, 'team_CTL_neutrallolly', 0, 292, 48)
    item(1, 'ammo_betty', 0, -292, 48)
    item(1, 'holdable_killerducks', 0, 218, 144)
    for s in (1, -1):
        item(s, 'ammo_bubbleg', -206, -206, 48)
        item(s, 'item_armor_shard', -ap - 36, 60, 48)
    light(0, 0, 720, 1200, '1 0.95 0.9')


def drain():
    """drain (under the north lane) and plug on its chain (under the south lane) on the tub floor: open water above,
    equally far from both ships. Betty at the drain, Pad Power by the plug."""
    dx, dy = 0, 480
    A(cyl(dx, dy, 64, FZ, FZ + 2, {'top': T('drain'), 'side': T('chrome'), 'bot': CAULK}, 16))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9: f.sc = (1, 1); f.off = ((-(dx - 64)) % 128, (dy + 64) % 128)
    weapon(1, 'betty', dx - 120, dy, FZ, 'black')
    item(1, 'ammo_imperius', dx + 120, dy, FZ)
    light(dx, dy, -200, 500, '0.6 0.85 1')
    speaker(dx, dy, -260, 'sound/world/ambient/water_drain.ogg')
    px, py = 60, -480
    A(cyl(px, py, 40, FZ, FZ + 28, {'side': T('plug'), 'top': T('plug'), 'bot': CAULK}, 12))
    A(cyl(px, py, 8, FZ + 28, FZ + 40, T('chrome'), 6))
    for k in range(7):                                       # chain lying on the floor
        A(box((px - 2, py - 60 - k * 20 - 8, FZ), (px + 2, py - 60 - k * 20 + 8, FZ + 4), T('chrome')))
    item(1, 'item_padpower', px - 130, py, FZ)
    light(px, py, -200, 500, '0.6 0.85 1')


def buoys():
    """anchored marker buoys between each ship and the tower (cover, breaks the long centre sightline)"""
    for s in (1, -1):
        x, y = -1000, 240
        A(scyl(s, x, y, 4, FZ, -64, T('chrome'), 6))
        A(scyl(s, x, y, 96, -64, 96, {'side': T('buoy'), 'top': T('float_white'), 'bot': T('float_white')}, 12))
        A(sh(s, ring_pts(x, y, 96, 96, 12) + ring_pts(x, y, 16, 220, 12), T('ring_red' if s > 0 else 'ring_blue')))
        A(scyl(s, x, y, 14, 220, 252, T('lamp_rim'), 8))
        light(s * x, s * y, 280, 220, '1 0.4 0.3' if s > 0 else '0.4 0.6 1')


# =================================================================================================== soap / sponge
def bar(s):
    """bar of soap (north, s=+1) / sponge (south, s=-1): chamfered ramps out of the water at both ends"""
    y0, y1 = 688, 1040
    # a prism of the end profile: flat top x -208..208, 30 deg ramps down into the water at both ends
    pts = [(sx * x, y, z) for sx in (-1, 1) for y in (y0, y1) for (x, z) in ((384, -64), (384, -48), (208, 56))]
    if s > 0:
        b = sh(s, pts, {'side': T('soap'), 'top': T('soap_top'), 'bot': T('soap')})
        fit_top(b, -208, y0, 208, y1, 512, 256)
    else:
        b = sh(s, pts, {'side': T('sponge'), 'top': T('sponge_green'), 'bot': T('sponge')})
    A(b)
    spad(s, 0, 896, 56, (0, 1200, RIMZ), 470, 'bar_%s' % ('n' if s > 0 else 's'))
    weapon(s, 'bubbleg', -100, 860, 56, 'blue')
    item(s, 'item_armor_padshield', 120, 760, 56)
    spawn(s, 'info_player_deathmatch', 140, 960, 56, 270)


def tap_and_shower():
    # ---- tap on the north wall: spout (perch), collar, outlet, two handles (red = west, blue = east)
    A(box((-64, 976, PERCH_Z - 64), (64, RYN, PERCH_Z), {'top': T('chrome'), 'side': T('chrome'), 'bot': T('chrome')}))
    A(cyl(0, 1000, 30, PERCH_Z - 112, PERCH_Z - 64, T('chrome'), 12))
    A(box((-4, 996, 120), (4, 1004, PERCH_Z - 112), {'e': T('drip'), 'w': T('drip'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS}))
    for (hx, cap) in ((-352, 'trim_red'), (352, 'trim_blue')):
        oct_ = [(hx + 40 * math.cos(a), 560 + 40 * math.sin(a)) for a in [math.pi / 8 + k * math.pi / 4 for k in range(8)]]
        A(hull([(x, y, z) for (x, z) in oct_ for y in (1250, RYN - 8)], T('chrome'), round_pts=False))
        oc2 = [(hx + 24 * math.cos(a), 560 + 24 * math.sin(a)) for a in [math.pi / 8 + k * math.pi / 4 for k in range(8)]]
        A(hull([(x, y, z) for (x, z) in oc2 for y in (1240, 1250)], T(cap), round_pts=False))
    weapon(1, 'splasher', 0, 1080, PERCH_Z, 'orange')
    speaker(0, 1000, 700, 'sound/world/ambient/water_drippling.ogg')
    # ---- rain shower head over the sponge (matching perch)
    cx, cy = 0, -1144
    A(cyl(cx, cy, 160, PERCH_Z - 16, PERCH_Z, {'top': T('chrome'), 'side': T('chrome'), 'bot': T('drain')}, 16))
    A(cyl(cx, cy, 12, PERCH_Z, CZ - 24, T('chrome'), 8))
    A(cyl(cx, cy, 40, CZ - 24, CZ, T('chrome'), 12))
    weapon(-1, 'splasher', 0, 1080, PERCH_Z, 'orange')
    # rim pads up to the perches
    spad(-1, -192, -1200, RIMZ, (0, -1064, PERCH_Z), 980, 'perch_n')      # lands beside the shower pole, not on it
    spad(1, -300, -1200, RIMZ, (-60, -1160, PERCH_Z), 980, 'perch_s')     # starts outside the disc so the arc clears its rim


# =================================================================================================== floating suds + ducks
def suds_islands():
    for s in (1, -1):
        for (x, y, ang) in ((-680, 860, 300), (680, 860, 240)):      # > 192u from the ferry end positions (no bot links)
            A(scyl(s, x, y, 176, -24, 8, {'side': T('suds'), 'top': T('suds'), 'bot': T('suds')}, 16))
            # soft bubble humps around the edge (cover, low)
            smdl(s, 'pad_ducks/pad_duck.md3', x + 20, y + 10, 8, 0.7, ang, solid=True)
        weapon(s, 'pumper', -680 + 110, 860 - 90, 8, 'green')        # mid-field: defenders don't spawn next to it
        item(s, 'ammo_boaster', -680 - 96, 860 - 110, 8)
        item(s, 'ammo_splasher', 680 + 100, 860 - 110, 8)


# =================================================================================================== rim clutter + rim loot
def bottle(s, x, y, r, h, body, label):
    A(scyl(s, x, y, r, RIMZ, RIMZ + h, {'side': T(body), 'top': T(body), 'bot': CAULK}, 8))
    A(scyl(s, x, y, r * 0.55, RIMZ + h, RIMZ + h + 40, {'side': T('bottle_white'), 'top': T('bottle_white'), 'bot': CAULK}, 8))
    # label panel on the side facing the tub
    wx, wy = s * x, s * y
    if wy > 0:
        A(sign_box((wx - r * 0.55, wy - r - 2, RIMZ + h * 0.25), (wx + r * 0.55, wy - r * 0.92, RIMZ + h * 0.85), T(label), 256, 384,
                   back=T(body), facing='s'))
    else:
        A(sign_box((wx - r * 0.55, wy + r * 0.92, RIMZ + h * 0.25), (wx + r * 0.55, wy + r + 2, RIMZ + h * 0.85), T(label), 256, 384,
                   back=T(body), facing='n'))


def rim_stuff(s):
    """red half (x < 0): north rim west, south rim west, west rim. Rotated for blue."""
    # north rim (props against the wall, walkway on the tub side)
    smdl(s, 'pad_ducks/pad_duck.md3', -2420, 1215, RIMZ, 0.55, 300, solid=True)
    bottle(s, -1500, 1236, 56, 300, 'bottle_teal', 'label_shampoo')
    A(scyl(s, -900, 1240, 52, RIMZ, RIMZ + 140, {'side': T('cup_plastic'), 'top': T('cup_plastic'), 'bot': CAULK}, 12))
    for (dx, dy, c) in ((-14, 0, 'blackred'), (16, 12, 'blackblue'), (6, -18, 'blackgreen')):
        smdl(s, 'pad_items/toothbrush_%s.md3' % c, -900 + dx, 1240 + dy, RIMZ + 140, 2.0, 20)
    smdl(s, 'pad_bath/deocan1.md3', -460, 1250, RIMZ, 1.3)
    smdl(s, 'pad_items/towelroll.md3', -2000, 1250, RIMZ, 1.5, 90)
    # south rim west half (in front of the curtain)
    bottle(s, -1100, -1250, 50, 260, 'bottle_pink', 'label_bubble')
    smdl(s, 'pad_bath/toothpaste_flat.md3', -1900, -1240, RIMZ, 0.8, 90)
    smdl(s, 'pad_scouringpad/scouringpad_pink.md3', -600, -1240, RIMZ, 2.5, 15)
    smdl(s, 'pad_bath/razor.md3', -2300, -1240, RIMZ, 0.9, 0)
    # west rim (behind the ship)
    smdl(s, 'pad_items/towelstack.md3', -2630, -600, RIMZ, 1.8, 0, solid=True)
    smdl(s, 'pad_scouringpad/scouringpad_blue.md3', -2620, 760, RIMZ, 2.5, 80)
    smdl(s, 'pad_train/soapdispenser.md3', -2680, 300, RIMZ, 3.0, 0)
    # loot on the rims
    item(s, 'item_speedy', -2600, 1200, RIMZ)
    item(s, 'ammo_splasher', -700, 1160, RIMZ)
    item(s, 'ammo_balloony', -1250, 1160, RIMZ)
    item(s, 'ammo_pumper', -2600, -760, RIMZ)
    item(s, 'ammo_nipper', -2600, 0, RIMZ)
    item(s, 'item_armor_shard', -2600, 480, RIMZ)
    item(s, 'ammo_betty', -1600, -1180, RIMZ)
    spawn(s, 'info_player_deathmatch', -1700, 1190, RIMZ, 0)
    spawn(s, 'info_player_deathmatch', -2600, -300, RIMZ, 0)
    spawn(s, 'info_player_deathmatch', -800, -1190, RIMZ, 90)


def underwater(s):
    # sunken bits: soft ball, a toy fish pair, imperius ammo behind each ship
    smdl(s, 'pad_ball/pad_softball.md3', -1200, -200, FZ, 3.0)
    smdl(s, 'pad_fish/flame_angel.md3', -2300, 500, FZ, 2.0, 30)
    item(s, 'ammo_imperius', -2300, 0, FZ)
    light(s * -2300, 0, -180, 450, '0.6 0.85 1')
    light(s * -900, s * 500, -200, 450, '0.6 0.85 1')
    light(s * -900, s * -500, -200, 450, '0.6 0.85 1')


# =================================================================================================== lights + sounds
def lights_and_sound():
    # ceiling lamps (glowing discs with chrome rims)
    for x in (-1600, 0, 1600):
        A(cyl(x, 0, 120, CZ - 16, CZ, {'bot': T('lamp_rim'), 'side': T('lamp_rim'), 'top': CAULK}, 16))
        A(cyl(x, 0, 96, CZ - 24, CZ - 16, {'bot': T('lamp'), 'side': T('lamp_rim'), 'top': CAULK}, 16))
    for x in range(-2200, 2201, 550):
        for y in (-760, 0, 760):
            light(x, y, 900, 2200)
    for (x, y) in ((-2560, 1200), (2560, -1200), (-2560, -1200), (2560, 1200), (0, 1200), (0, -1200)):
        light(x, y, 640, 700)
    for (x, y) in ((-1000, 600), (1000, -600), (1000, 600), (-1000, -600), (0, 0)):
        speaker(x, y, 60, 'sound/world/ambient/water_rippling.ogg')
    M.ent('func_timer', (0, 0, 1200), target='horn', wait=40, random=15, spawnflags=1)


def carve_water():
    """replace the tub's water box by convex pieces that leave out every solid brush in it (nothing overlaps)"""
    wi = next(i for i, b in enumerate(M.world) if T('water') in b.textures())
    wb = M.world[wi]
    wmn, wmx = wb.bounds()
    cut = []
    for i, b in enumerate(M.world):
        if i == wi or not b.is_solid(): continue
        if b.textures() <= {NODRAW_NS, T('drip'), T('flag_red'), T('flag_blue')}: continue
        mn, mx = b.bounds()
        if np.all(mn < wmx - 0.5) and np.all(mx > wmn + 0.5): cut.append(b)
    pieces = carve(wb, cut, T('water'))
    # only the surface (top faces at z 0) is drawn; faces between pieces / against solids are invisible water
    for b in pieces:
        for f in b.faces:
            f.tex = T('water') if (f.n[2] > 0.99 and abs(f.d - WZ) < 0.01) else T('water_inner')
    M.world[wi:wi + 1] = pieces
    print('water pieces', len(pieces), 'cutters', len(cut))


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    room_shell(); curtain()
    for s in (1, -1):
        ship(s); wall_shelf(s); ferry(s); shuttle(s); bar(s); rim_stuff(s); underwater(s)
    centre_tower(); drain(); buoys(); tap_and_shower(); suds_islands(); lights_and_sound()
    carve_water()
    M.ent('info_player_intermission', (-1400, -900, 900), angles='22 35 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text("// Battle in the Bathtub - generated by wop_tools/padbath/build_padbath.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
