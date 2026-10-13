#!/usr/bin/env python3
"""Tilt! - World of Padman map generator (map 'wop_padpinball'): Padman inside a giant pinball machine.

    OUT=/path/to/out python3 build_padpinball.py

Writes <OUT>/maps/wop_padpinball.map, textures/padpinball/*, models/padpinball/* (MD3 centrepieces),
scripts/padpinball.shader and scripts/wop_padpinball.arena.

Padman scale (catalog models at 1.0). x east (across the table), y north (up the table toward the backbox),
playfield at z 0, the playfield glass is the ceiling at z 1088. The table is mirror-symmetric about x = 0:
every red-side piece is built by a function taking s = +1 (red, west, coordinates written with negative x)
and mirrored for blue (s = -1, east).

  flipper end   apron with instruction cards, two MD3 flippers (each with a "flipper shot" kicker pad that throws
                you across the table), the drain between them (a hole down to the underworld), slingshots that kick
                you back into play, inlanes/outlanes with kickback pads, plunger lanes along both side walls: the
                MD3 plunger + a launch pad that fires you up the whole lane to the top arch (Balloony)
  midfield      the centrepiece: a giant chrome steel ball (MD3) resting in a saucer, Splasher on top (side
                kickers), standup target banks, a drop-target row, the VUK hole (vertical up-kicker) from below
  ramps         a ramp each side from midfield up to the raised corner mini-playfield (spinner over the entrance)
  corners       team "prize booths" on the mini-playfields (lolly inside, stairs to the roof, Pumper on top),
                Boaster under each mini-playfield; a kicker from the top lanes up to each corner
  upper field   three MD3 pop bumpers ("Bumper City"), top rollover lanes, the golden trophy, and the backbox
                kicker that shoots you up through a hatch into the backbox (Imperius + Pad Power, teleporter out)
  underworld    the cabinet interior below the playfield: drain ramp, coin box (Betty + Speedy inside, crate steps
                to its roof), transformer, speaker, wiring; teleport pads serve you into either plunger lane, the
                VUK kicker shoots you back up onto the playfield
  outside       a dim arcade room seen through the playfield glass: neighbouring cabinets, neon, ceiling panels
"""
import os, sys, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from wopmap import *
import wopmap
import pin_textures as TX
import pin_models as PM

OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAPNAME = 'wop_padpinball'
T = lambda n: 'padpinball/' + n
CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; TRIG = 'common/trigger'
ORIGIN = 'common/origin'; NODRAW_NS = T('nodraw_ns')

for k, v in {'cab_side': (2, 2), 'wood_black': (1, 1), 'steel': (0.5, 0.5), 'steel_dark': (0.5, 0.5), 'chrome': (0.5, 0.5),
             'rubber': (0.5, 0.5), 'apron_side': (1, 1), 'ramp_red': (0.75, 0.75), 'ramp_blue': (0.75, 0.75), 'ramp_side': (0.5, 0.5),
             'booth_red': (0.75, 0.75), 'booth_blue': (0.75, 0.75), 'boardwalk': (0.75, 0.75), 'counter': (0.75, 0.75),
             'underside': (1.5, 1.5), 'plywood': (1, 1), 'plywood_dark': (1, 1), 'galvanised': (0.75, 0.75), 'coins': (0.75, 0.75),
             'transformer': (0.5, 0.5), 'copper': (0.5, 0.5), 'cab_exterior': (2, 2), 'room_ceiling': (2, 2), 'room_wall': (3, 3),
             'cabside_1': (2, 2), 'cabside_2': (2, 2), 'glass': (4, 4)}.items():
    wopmap.TEXSCALE[T(k)] = v
for c in ('red', 'blue', 'yellow', 'green', 'white', 'purple', 'orange', 'black'):
    wopmap.TEXSCALE[T('plastic_' + c)] = (1, 1)

M = Map({'message': TX.LONGNAME, '_ambient': '10', '_color': '1 0.95 0.9', 'gridsize': '96 96 96', '_blocksize': '0'})
A = M.add

# ---------------------------------------------------------------------------------------------------- layout
FX, FY = TX.FX, TX.FY            # playfield interior half sizes (x -1280..1280, y -2432..2432)
WALL = 64                        # cabinet wall thickness
GZ, GT, RAIL = 1088, 1104, 1120  # playfield glass bottom / top, side rail top
BZ, UZ, CBZ = -64, -448, -480    # board bottom, underworld floor, cabinet bottom
UX, UY0, UY1 = 896, -2432, -640  # underworld x half width, y range
BBY0, BBY1, BBZ0, BBZ1 = 2144, 2656, 864, 1632      # backbox outer y, floor bottom / roof top
BBF = 896                        # backbox floor top
BBC = 1600                       # backbox ceiling
LANE_X1, LANE_Y0, LANE_Y1 = -1120, -2112, 1920      # plunger lane inner edge (lane wall x -1120..-1088), wall y range
ARC_C, ARC_RI, ARC_RO = (-768, 1920), 352, 512      # top arch: lane inner wall r 352..384, cabinet corner fill r 512
MPX0, MPX1, MPY0, MPY1, MPZ = -1056, -576, 960, 1696, 320   # mini-playfield (red)
BX0, BX1, BY0, BY1, BWZ, BRZ = -1024, -736, 1168, 1488, 512, 528   # booth (red)
RX0, RX1, RY0, RY1 = -784, -624, -384, 960           # ramp footprint (red)
BALL = (0, -560)
TENT = (0, 400)
BUMPERS = [(-288, 960, 'red'), (288, 960, 'blue'), (0, 1300, 'yellow')]
FLIP_P, FLIP_A = (-560, -1888), -28.0                # red flipper pivot + angle (blue mirrored)
VUK = (0, -1100)                                     # vertical up-kicker hole (field) / pad (underworld)
DRAIN = (-112, -2432, 112, -2080)
ROOM = (-2048, -3072, 2048, 3328, CBZ, 2432)         # arcade room interior
BOUNDS = json.load(open(os.path.join(os.path.dirname(HERE), 'md3bounds.json')))
SPOTS = {'weapon': [], 'ammo': [], 'item': [], 'spawn': []}
JUMPPADS = []


# =================================================================================================== helpers
def rtex(s, tex):
    if s > 0 or not isinstance(tex, dict): return tex
    sw = {'e': 'w', 'w': 'e'}
    return {sw.get(k, k): v for k, v in tex.items()}


def sb(s, x0, y0, z0, x1, y1, z1, tex, detail=True):
    xa, xb = sorted((s * x0, s * x1))
    return box((round(xa), round(y0), z0), (round(xb), round(y1), z1), rtex(s, tex), detail)


def sh(s, pts, tex, rnd=True):
    return hull([(s * x, y, z) for (x, y, z) in pts], rtex(s, tex), round_pts=rnd)


def scyl(s, x, y, r, z0, z1, tex, n=12, phase=None):
    return cyl(s * x, y, r, z0, z1, rtex(s, tex), n, phase=phase)


def frustum(cx, cy, r0, z0, r1, z1, tex, n=16, phase=None):
    return hull([(x, y, z0) for (x, y) in ngon(cx, cy, r0, n, phase)] + [(x, y, z1) for (x, y) in ngon(cx, cy, r1, n, phase)], tex)


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


def smdl(s, path, x, y, zsurf, scale=1.0, angle=0, solid=False, shrink=0.12):
    ang = (180 - angle) % 360 if s < 0 else angle % 360       # mirror about x = 0
    if solid: return solid_mdl(path, s * x, y, zsurf, scale, ang, shrink)
    return mdl_c(path, s * x, y, zsurf, scale, ang)


def light(x, y, z, val, color='1 0.95 0.85', **kw):
    M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)


def slight(s, x, y, z, val, color='1 0.95 0.85'):
    light(s * x, y, z, val, color)


def speaker(x, y, z, noise, loop=True, **kw):
    kv = {'noise': noise}
    if loop: kv['spawnflags'] = 1
    kv.update(kw)
    return M.ent('target_speaker', (round(x), round(y), round(z)), **kv)


def item(s, cls, x, y, floor, **kw):
    M.ent(cls, (round(s * x), round(y), floor + 16), **kw)
    SPOTS['ammo' if cls.startswith('ammo') else 'item'].append((cls, s * x, y, floor))


def weapon(s, w, x, y, floor, marker='blue', **kw):
    M.ent('weapon_' + w, (round(s * x), round(y), floor + 16), marker=marker, **kw)
    SPOTS['weapon'].append((w, s * x, y, floor))


def spawn(s, cls, x, y, floor, ang):
    a = ang if s > 0 else (180 - ang) % 360
    M.ent(cls, (round(s * x), round(y), floor + 25), angle=a)
    SPOTS['spawn'].append((s * x, y, floor))


def ssign(s, mn, mx, tex, tw, th, facing, back):
    """sign_box given in red-side coordinates, mirrored for blue (fit_face keeps text readable)"""
    if s > 0: return sign_box(mn, mx, tex, tw, th, back=back, facing=facing)
    sw = {'n': 'n', 's': 's', 'e': 'w', 'w': 'e'}
    return sign_box((-mx[0], mn[1], mn[2]), (-mn[0], mx[1], mx[2]), tex, tw, th, back=back, facing=''.join(sw[c] for c in facing))


def fit_top(b, x0, y0, x1, y1, tw, th, tex=None):
    """fit a tw x th texture exactly onto the rectangle x0..x1, y0..y1 of the brush's top face(s) (north = image top)"""
    for f in b.faces:
        if f.n[2] > 0.9:
            if tex: f.tex = tex
            sx = (x1 - x0) / tw; sy = (y1 - y0) / th
            f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))
    return b


def decal(x0, y0, x1, y1, z, tex, tw=128, th=128):
    """playfield insert: 1u nonsolid brush on a floor; top face shows tex (additive pulsing shader) fitted to the rect"""
    b = box((round(x0), round(y0), z), (round(x1), round(y1), z + 1), NODRAW_NS)
    fit_top(b, round(x0), round(y0), round(x1), round(y1), tw, th, T(tex))
    A(b)


def jumppad(x, y, z, land, apex, name, tex='jumppad'):
    """kicker: disc (r 34, 6 tall) + trigger_push + target_position. Q3 AimAtTarget: target = apex of the flight, measured
    from the trigger centre; the player keeps flying past it, so the target sits t_up/(t_up+t_down) of the way to `land`."""
    x, y = round(x), round(y)
    A(cyl(x, y, 34, z, z + 6, {'top': T(tex), 'side': T('rubber'), 'bot': T('rubber')}, 12))
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
    light(x, y, z + 48, 90, '1 0.85 0.4' if tex == 'jumppad' else '0.5 0.85 1')


def spad(s, x, y, z, land, apex, name, tex='jumppad'):
    jumppad(s * x, y, z, (s * land[0], land[1], land[2]), apex, name, tex)


def ring_segments(cx, cy, r0, r1, z0, z1, tex, n=16, skip=()):
    """annulus as n convex wedge brushes"""
    a = ngon(cx, cy, r0, n); b = ngon(cx, cy, r1, n)
    for k in range(n):
        if k in skip: continue
        q = [a[k], b[k], b[(k + 1) % n], a[(k + 1) % n]]
        A(hull([(x, y, z) for (x, y) in q for z in (z0, z1)], tex))


def wall_seg(p, q, thick, z0, z1, tex, side=1):
    """straight wall along p->q, `thick` to the left (side=1) or right (side=-1) of the direction of travel"""
    dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy)
    nx, ny = -dy / L * side * thick, dx / L * side * thick
    pts = [p, q, (q[0] + nx, q[1] + ny), (p[0] + nx, p[1] + ny)]
    return hull([(x, y, z) for (x, y) in pts for z in (z0, z1)], tex, round_pts=False)


# =================================================================================================== cabinet + room
def room_and_cabinet():
    x0, y0, x1, y1, z0, z1 = ROOM
    W = 16
    rw = {'side': CAULK}
    # arcade room hull (structural): floor, ceiling, four walls
    A(box((x0 - W, y0 - W, z0 - W), (x1 + W, y1 + W, z0), {'top': T('plywood_dark'), 'side': CAULK, 'bot': CAULK}, detail=False))
    A(box((x0 - W, y0 - W, z1), (x1 + W, y1 + W, z1 + W), {'bot': T('room_ceiling'), 'side': CAULK, 'top': CAULK}, detail=False))
    A(box((x0 - W, y1, z0), (x1 + W, y1 + W, z1), {'side': CAULK, 's': T('room_wall')}, detail=False))
    A(box((x0 - W, y0 - W, z0), (x1 + W, y0, z1), {'side': CAULK, 'n': T('room_wall')}, detail=False))
    A(box((x1, y0, z0), (x1 + W, y1, z1), {'side': CAULK, 'w': T('room_wall')}, detail=False))
    A(box((x0 - W, y0, z0), (x0, y1, z1), {'side': CAULK, 'e': T('room_wall')}, detail=False))
    # ceiling light panels (glow) and neon signs on the end walls, posters on the side walls
    for x in (-1536, -512, 512, 1536):
        for y in (-2400, -1200, 0, 1200, 2400):
            A(box((x - 192, y - 96, z1 - 4), (x + 192, y + 96, z1), {'bot': T('light_panel'), 'side': T('steel_dark'), 'top': CAULK}))
    A(sign_box((-512, y1 - 4, 1880), (512, y1, 2136), T('neon_arcade'), 512, 128, back=T('room_wall'), facing='s'))
    A(sign_box((-512, y0, 1880), (512, y0 + 4, 2136), T('neon_hiscore'), 512, 128, back=T('room_wall'), facing='n'))
    for y, p in ((-1500, 'poster_1'), (1300, 'poster_2')):
        A(sign_box((x1 - 4, y - 192, 1500), (x1, y + 192, 2076), T(p), 256, 384, back=T('room_wall'), facing='w'))
        A(sign_box((x0, -y - 192, 1500), (x0 + 4, -y + 192, 2076), T(p), 256, 384, back=T('room_wall'), facing='e'))
    # neighbouring cabinets along the side walls (tops seen through the glass), marquee facing our table
    for s in (1, -1):
        for k, yc in enumerate((-1760, 0, 1760)):
            mq = T('marquee_%d' % (1 + (k + (0 if s > 0 else 1)) % 4))
            A(sb(s, -1984, yc - 320, z0, -1536, yc + 320, 1500, {'side': T('cabside_%d' % (1 + k % 2)), 'top': T('cab_exterior'), 'bot': CAULK}))
            A(ssign(s, (-1536, yc - 300, 1300), (-1532, yc + 300, 1460), mq, 512, 128, 'e', T('wood_black')))
    for (x, y) in ((-1200, -2900), (1200, -2900), (-1200, 3100), (1200, 3100), (0, -2900), (0, 3100)):
        light(x, y, 1900, 1600, '0.9 0.85 1')
    # ---- the cabinet: bottom slab, side walls (inner face = side art), front and back walls, glass, lockdown bar
    side = {'side': T('cab_exterior'), 'top': T('wood_black'), 'bot': CAULK}
    A(box((-FX - WALL, -FY - WALL, CBZ), (FX + WALL, FY + WALL, UZ), {'top': T('plywood_dark'), 'side': T('cab_exterior'), 'bot': CAULK}))
    A(box((-FX - WALL, -FY - WALL, UZ), (-FX, FY + WALL, RAIL), dict(side, e=T('cab_side'))))
    A(box((FX, -FY - WALL, UZ), (FX + WALL, FY + WALL, RAIL), dict(side, w=T('cab_side'))))
    A(box((-FX, -FY - WALL, UZ), (FX, -FY, BZ), dict(side, n=T('plywood'))))
    A(box((-FX, -FY - WALL, BZ), (FX, -FY, RAIL), dict(side, n=T('cab_side'))))
    A(box((-FX, FY, UZ), (FX, FY + WALL, BBZ0), dict(side, s=T('backboard'))))
    for f in M.world[-1].faces:          # backboard art fitted to the visible part (z 0..864)
        if f.n[1] < -0.9: fit_face(f, -FX, FX, 0, BBZ0, 2048, 512)
    A(box((-FX, -FY, GZ), (FX, BBY0, GT), T('glass')))
    A(box((-FX, -FY - WALL, RAIL), (FX, -FY, RAIL + 32), T('chrome')))       # lockdown bar on the front rail


def board():
    """playfield board z -64..0 with the drain and VUK holes, in 2 x 2 tiles carrying the fitted playfield art"""
    holes = [DRAIN, (VUK[0] - 96, VUK[1] - 96, VUK[0] + 96, VUK[1] + 96)]
    tw, th = TX.PF_W // 2, TX.PF_H // 2
    for i, (xa, xb) in enumerate(((-FX, 0), (0, FX))):
        for j, (ya, yb) in enumerate(((0, FY), (-FY, 0))):
            for (x0, y0, x1, y1) in sub_rects((xa, ya, xb, yb), holes):
                b = box((x0, y0, BZ), (x1, y1, 0), {'top': T('pf_%d%d' % (i, j)), 'bot': T('underside'), 'side': T('plywood')})
                fit_top(b, xa, ya, xb, yb, tw, th)
                A(b)
    # chrome rim round the VUK hole (16 high: a step, so you can walk in and drop)
    vx, vy = VUK
    rim = {'side': T('chrome'), 'top': T('chrome'), 'bot': CAULK}
    A(box((vx - 112, vy - 112, 0), (vx + 112, vy - 96, 16), rim)); A(box((vx - 112, vy + 96, 0), (vx + 112, vy + 112, 16), rim))
    A(box((vx - 112, vy - 96, 0), (vx - 96, vy + 96, 16), rim)); A(box((vx + 96, vy - 96, 0), (vx + 112, vy + 96, 16), rim))


# =================================================================================================== side lanes + flipper end
def plunger_lane(s):
    team = 'red' if s > 0 else 'blue'
    lw = {'side': T('steel'), 'top': T('chrome'), 'bot': CAULK}
    A(sb(s, LANE_X1, LANE_Y0, 0, LANE_X1 + 32, LANE_Y1, 128, lw))
    # top arch: cabinet corner fill (r >= 512 round ARC_C, up to the glass) and the curved inner lane wall (r 352..384)
    cx, cy = ARC_C
    n = 6
    for k in range(n):
        a0 = math.radians(90 + 90 * k / n); a1 = math.radians(90 + 90 * (k + 1) / n)
        P0 = (cx + ARC_RO * math.cos(a0), cy + ARC_RO * math.sin(a0)); P1 = (cx + ARC_RO * math.cos(a1), cy + ARC_RO * math.sin(a1))
        tri = [P0, P1, (-FX, FY)]
        A(sh(s, [(x, y, z) for (x, y) in tri for z in (0, BBZ0)], {'side': T('cab_side'), 'top': CAULK, 'bot': CAULK}))
        low = clip_poly(tri, BBY0 - 2)        # above the backbox floor level only the part south of the backbox front
        if len(low) >= 3:
            A(sh(s, [(x, y, z) for (x, y) in low for z in (BBZ0, GZ)], {'side': T('cab_side'), 'top': CAULK, 'bot': CAULK}, rnd=False))
        q = [(cx + ARC_RI * math.cos(a0), cy + ARC_RI * math.sin(a0)), (cx + (ARC_RI + 32) * math.cos(a0), cy + (ARC_RI + 32) * math.sin(a0)),
             (cx + (ARC_RI + 32) * math.cos(a1), cy + (ARC_RI + 32) * math.sin(a1)), (cx + ARC_RI * math.cos(a1), cy + ARC_RI * math.sin(a1))]
        A(sh(s, [(x, y, z) for (x, y) in q for z in (0, 128)], lw, rnd=False))
    # the plunger (MD3) on the front wall and the launch pad at its tip: fires you up the whole lane to the arch
    M.model('models/padpinball/plunger.md3', (s * -1200, -FY, 0), angle=0)
    spad(s, -1200, -2100, 0, (-1200, 1700, 0), 230, 'plunger_' + team)
    # chasing arrows up the lane
    for k, y in enumerate((-1800, -1000, -200, 600, 1400)):
        decal(s * -1200 - 40, y - 40, s * -1200 + 40, y + 40, 0, 'ins_arrow_white_p%d' % (k % 4))
    weapon(s, 'balloony', -1200, 1780, 0, 'green')
    item(s, 'ammo_balloony', -1200, -1500, 0)
    item(s, 'ammo_balloony', -1200, 400, 0)
    for y in (-1800, -600, 600, 1600):
        slight(s, -1200, y, 220, 220, '1 1 1')


def flipper_end(s):
    team = 'red' if s > 0 else 'blue'
    # apron (z 32) with the instruction card
    ap = {'top': T('apron_l' if s > 0 else 'apron_r'), 'side': T('apron_side'), 'bot': CAULK}
    b = sb(s, -1088, -FY, 0, -112, -2240, 32, ap)
    xa, xb = sorted((s * -1088, s * -112))
    fit_top(b, xa, -FY, xb, -2240, 1024, 256)
    A(b)
    item(s, 'ammo_bubbleg', -600, -2336, 32)
    # flipper (MD3) + its weapon-clip collision; the flipper shot kicker in front of it
    px, py = FLIP_P
    ang = FLIP_A if s > 0 else 180 - FLIP_A
    M.model('models/padpinball/flipper.md3', (s * px, py, 0), angle=ang % 360)
    out = PM.flipper_outline(n=12)
    a = math.radians(ang); ca, sa = math.cos(a), math.sin(a)
    pts = [(s * px + x * ca - y * sa, py + x * sa + y * ca) for (x, y) in out]
    A(hull([(x, y, z) for (x, y) in pts for z in (0, 60)], WCLIP, round_pts=False))
    spad(s, -300, -1900, 0, (720, -470, 0), 520, 'flipshot_' + team)
    # slingshot: plastic core with a printed top, rubber skirt along the kicking face, kicker trigger in front of it
    A_, B_, C_ = (-816, -1344), (-816, -1712), (-608, -1776)
    A(sh(s, [(x, y, z) for (x, y) in (A_, B_, C_) for z in (0, 88)], {'top': T('sling_' + team), 'side': T('plastic_white'), 'bot': CAULK}))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9:
            xa, xb = sorted((s * -816, s * -608)); fit_top_face(f, xa, -1776, xb, -1344, 256, 512)
    dx, dy = C_[0] - A_[0], C_[1] - A_[1]; L = math.hypot(dx, dy); nx, ny = dy / L, -dx / L      # outward normal (NE)
    if nx * 1 + ny * 0 < 0: nx, ny = -nx, -ny
    def off(p, d): return (p[0] + nx * d, p[1] + ny * d)
    A(sh(s, [(x, y, z) for (x, y) in (A_, C_, off(C_, 12), off(A_, 12)) for z in (12, 72)], {'side': T('rubber'), 'top': T('rubber'), 'bot': T('rubber')}, rnd=False))
    kick = sh(s, [(x, y, z) for (x, y) in (off(A_, 20), off(C_, 20), off(C_, 44), off(A_, 44)) for z in (0, 72)], TRIG, rnd=False)
    mid = ((A_[0] + C_[0]) / 2 + nx * 230, (A_[1] + C_[1]) / 2 + ny * 230)
    nm = 'sling_' + team
    M.ent('trigger_push', brushes=[kick], target=nm)
    M.ent('target_position', (round(s * mid[0]), round(mid[1]), 150), targetname=nm)
    # outlane / inlane separator with a post, the inlane guide down to the flipper
    A(sb(s, -960, -1984, 0, -936, -1428, 64, {'side': T('steel'), 'top': T('chrome'), 'bot': CAULK}))
    A(scyl(s, -948, -1408, 18, 0, 80, {'side': T('rubber'), 'top': T('chrome'), 'bot': CAULK}, 12))
    A(sh(s, [(x, y, z) for (x, y) in ((-816, -1730), (-640, -1852), (-654, -1872), (-830, -1750)) for z in (0, 64)],
         {'side': T('steel'), 'top': T('chrome'), 'bot': CAULK}, rnd=False))
    # kickback pad at the bottom of the outlane
    spad(s, -1024, -2048, 0, (-1024, -1150, 0), 330, 'kickback_' + team)
    decal(s * -1024 - 60, -1860, s * -1024 + 60, -1815, 0, 'ins_kickback_p%d' % (0 if s > 0 else 2), 256, 96)
    # inserts: triangles above the slingshot
    for k, y in enumerate((-1250, -1180)):
        decal(s * -720 - 32, y - 32, s * -720 + 32, y + 32, 0, 'ins_tri_%s_p%d' % ('red' if s > 0 else 'blue', k))
    item(s, 'ammo_boaster', -1024, -1700, 0)
    item(s, 'item_armor_shard', -880, -1880, 0)
    slight(s, -700, -1600, 300, 600)
    slight(s, -400, -2100, 300, 600)


def clip_poly(poly, ymax):
    """convex polygon clipped to y <= ymax"""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        pin, qin = p[1] <= ymax, q[1] <= ymax
        if pin: out.append(p)
        if pin != qin:
            t = (ymax - p[1]) / (q[1] - p[1]); out.append((p[0] + (q[0] - p[0]) * t, ymax))
    return out


def fit_top_face(f, x0, y0, x1, y1, tw, th):
    sx = (x1 - x0) / tw; sy = (y1 - y0) / th
    f.sc = (sx, sy); f.off = (round((-x0 / sx) % tw, 3), round((y1 / sy) % th, 3))


# =================================================================================================== midfield
def steel_ball():
    """the centrepiece: a chrome steel pinball (MD3, r 144) in a saucer ring; collision = 16-gon frusta (weapclip),
    walkable flat cap on top (Splasher), side kickers up to it"""
    bx, by = BALL
    R = PM.BALL_R
    M.model('models/padpinball/steel_ball.md3', (bx, by, 0), angle=0, _castshadows=1)
    zs = [0, 32, 72, 144, 216, 256, 276]
    def rr(z): return math.sqrt(max(0.0, R * R - (z - R) ** 2))
    rs = [47] + [rr(z) for z in zs[1:]]
    for k in range(len(zs) - 1):
        A(frustum(bx, by, rs[k], zs[k], rs[k + 1], zs[k + 1], WCLIP, 16))
    ring_segments(bx, by, 172, 204, 0, 12, {'top': T('chrome'), 'side': T('plastic_yellow'), 'bot': CAULK}, 16)
    weapon(1, 'splasher', bx, by, 276, 'orange')
    for s in (1, -1):
        spad(s, -264, by, 0, (0, by + 10 * s, 276), 500, 'ball_%s' % ('r' if s > 0 else 'b'))
    # circle inserts round the saucer
    for k in range(8):
        if k in (0, 4): continue
        a = math.radians(45 * k)
        x, y = bx + 250 * math.cos(a), by + 250 * math.sin(a)
        decal(x - 28, y - 28, x + 28, y + 28, 0, 'ins_circle_yellow_p%d' % (k % 4))
    decal(-128, -960, 128, -864, 0, 'ins_extraball_p1', 256, 96)
    light(bx, by, 520, 900, '1 0.95 0.85')
    for a in (45, 135, 225, 315):
        light(bx + 320 * math.cos(math.radians(a)), by + 320 * math.sin(math.radians(a)), 240, 320, '1 0.9 0.7')


def midfield(s):
    team = 'red' if s > 0 else 'blue'
    # standup target bank (cover) facing the middle
    cols = ['red', 'yellow', 'green'] if s > 0 else ['blue', 'yellow', 'green']
    for k, yc in enumerate((-760, -660, -560)):
        A(ssign(s, (-1016, yc - 36, 0), (-1000, yc + 36, 112), T('target_' + cols[k]), 128, 192, 'e', T('plastic_black')))
    A(sb(s, -1032, -812, 0, -1016, -508, 64, {'side': T('steel_dark'), 'top': T('chrome'), 'bot': CAULK}))
    # loot in the open
    weapon(s, 'bubbleg', -560, -1100, 0, 'blue')
    item(s, 'ammo_bubbleg', -400, 300, 0)
    item(s, 'ammo_nipper', -900, 400, 0)
    item(s, 'item_armor_shard', -1000, -400, 0)
    item(s, 'holdable_floater', -960, -660, 0)
    # toys on the playfield (cover): a gummy bear, an RC car, a ball
    smdl(s, 'gummybears/ldredbear.md3' if s > 0 else 'gummybears/ldyellowbear.md3', -440, -820, 0, 1.0, 20, solid=True)
    smdl(s, 'pad_nascars/padcar_%s_rc.md3' % ('orange' if s > 0 else 'black'), -420, -420, 0, 0.8, 0, solid=True)
    smdl(s, 'pad_ball/pad_basketball.md3', -200, -1680, 0, 1.0, 0)
    slight(s, -700, -1100, 300, 600)
    slight(s, -900, -300, 300, 500)


def drop_targets():
    cols = ['red', 'orange', 'blue']
    for k, xc in enumerate((-128, 0, 128)):
        b = box((xc - 64, -112, 0), (xc + 64, -88, 80), {'side': T('plastic_black'), 'top': T('chrome'), 'bot': CAULK})
        for f in b.faces:
            if f.n[1] < -0.9 or f.n[1] > 0.9:
                f.tex = T('target_' + cols[k]); fit_face(f, xc - 64, xc + 64, 0, 80, 128, 192)
        A(b)
    item(1, 'ammo_splasher', 0, 40, 0)
    item(1, 'ammo_betty', 0, -1880, 0)
    item(1, 'ammo_betty', 0, 1520, 0)
    light(0, 200, 300, 600)


# =================================================================================================== ramps + corners
def ramp(s):
    team = 'red' if s > 0 else 'blue'
    deck = {'top': T('ramp_' + team), 'side': T('ramp_side'), 'bot': T('ramp_side')}
    L = RY1 - RY0
    def zt(y): return MPZ * (y - RY0) / L
    ys = 16
    # solid wedge for the low part, then a 24u deck on posts
    A(sh(s, [(RX0, RY0, 0), (RX1, RY0, 0), (RX0, ys, 0), (RX1, ys, 0), (RX0, ys, zt(ys)), (RX1, ys, zt(ys))], deck, rnd=False))
    A(sh(s, [(x, y, z) for x in (RX0, RX1) for (y, z) in ((ys, zt(ys)), (RY1, MPZ), (ys, zt(ys) - 24), (RY1, MPZ - 24))], deck, rnd=False))
    for yp in (330, 650):
        z1a, z1b = zt(yp - 16) - 24, zt(yp + 16) - 24
        for xp in (RX0 + 24, RX1 - 24):
            A(sh(s, [(xp - 16, yp - 16, 0), (xp + 16, yp - 16, 0), (xp - 16, yp + 16, 0), (xp + 16, yp + 16, 0),
                     (xp - 16, yp - 16, z1a), (xp + 16, yp - 16, z1a), (xp - 16, yp + 16, z1b), (xp + 16, yp + 16, z1b)],
                 {'side': T('chrome'), 'top': T('chrome'), 'bot': CAULK}, rnd=False))
    # spinner over the entrance: plate on an axle (func_rotating about x), posts beside the ramp
    yz, zz = -200, 140
    for (xa, xb) in ((RX0 - 24, RX0 - 8), (RX1 + 8, RX1 + 24)):
        A(sb(s, xa, yz - 8, 0, xb, yz + 8, 152, {'side': T('chrome'), 'top': T('chrome'), 'bot': CAULK}))
    xm = (RX0 + RX1) / 2
    org = sb(s, xm - 8, yz - 8, zz - 8, xm + 8, yz + 8, zz + 8, ORIGIN)
    plate = sb(s, RX0, yz - 2, zz - 60, RX1, yz + 2, zz, {'n': T('spinner'), 's': T('spinner'), 'side': NODRAW_NS, 'top': NODRAW_NS, 'bot': NODRAW_NS})
    for f in plate.faces:
        if abs(f.n[1]) > 0.9: fit_face(f, s * RX0 if s > 0 else -RX1, s * RX1 if s > 0 else -RX0, zz - 60, zz, 256, 128)
    axle = sb(s, RX0 - 8, yz - 2, zz - 2, RX1 + 8, yz + 2, zz + 2, T('spinner'))
    M.ent('func_rotating', brushes=[org, plate, axle], speed=240, spawnflags=4)
    # arrows into the ramp
    for k, y in enumerate((-760, -640, -520)):
        decal(s * xm - 48, y - 48, s * xm + 48, y + 48, 0, 'ins_arrow_yellow_p%d' % k)
    item(s, 'ammo_pumper', -704, 600, 0)
    slight(s, xm, 300, 420, 450)


def mini_playfield(s):
    """raised corner playfield on chrome posts; the team booth on it; Boaster underneath"""
    team = 'red' if s > 0 else 'blue'
    b = sb(s, MPX0, MPY0, MPZ - 32, MPX1, MPY1, MPZ, {'top': T('plastic_purple' if s > 0 else 'plastic_purple'), 'side': T('chrome'), 'bot': T('underside')})
    A(b)
    for (x, y) in ((-1036, 980), (-596, 980), (-1036, 1676), (-596, 1676), (-1036, 1328), (-596, 1328)):
        A(sb(s, x - 20, y - 20, 0, x + 20, y + 20, MPZ - 32, {'side': T('chrome'), 'top': CAULK, 'bot': CAULK}))
    weapon(s, 'boaster', -816, 1328, 0, 'orange')
    item(s, 'ammo_splasher', -640, 1640, MPZ)
    item(s, 'item_armor_padshield', -704, 1040, MPZ)
    decal(s * -704 - 40, 1060, s * -704 + 40, 1140, MPZ, 'ins_arrow_green_p%d' % (1 if s > 0 else 3))
    decal(-1008 if s > 0 else 752, 1060, -752 if s > 0 else 1008, 1108, MPZ, 'ins_lolly_p%d' % (0 if s > 0 else 2), 256, 96)
    slight(s, -816, 1328, 200, 380, '1 0.9 0.75')
    slight(s, -650, 1600, 520, 500)
    # kicker from the top lanes up to the corner
    spad(s, -560, 2040, 0, (-800, 1640, MPZ), 600, 'corner_' + team, 'jumppad_blue')
    # mascot figure on the corner
    smdl(s, 'pad_actionfigures/fig_girl.md3' if s > 0 else 'pad_actionfigures/fig_lilly.md3', -1010, 1040, MPZ, 0.8, 0, solid=True)


def booth(s):
    team = 'red' if s > 0 else 'blue'
    wl = {'side': T('booth_' + team), 'top': T('booth_' + team), 'bot': CAULK}
    z0 = MPZ
    A(sb(s, BX0, BY0, z0, BX0 + 24, BY1, BWZ, wl))                                    # west
    A(sb(s, BX0 + 24, BY1 - 24, z0, BX1 - 24, BY1, BWZ, wl))                          # north
    A(sb(s, BX0 + 24, BY0, z0, -944, BY0 + 24, BWZ, wl)); A(sb(s, -816, BY0, z0, BX1 - 24, BY0 + 24, BWZ, wl))   # south + door
    A(sb(s, -944, BY0, z0 + 128, -816, BY0 + 24, BWZ, wl))
    A(sb(s, BX1 - 24, BY0, z0, BX1, 1264, BWZ, wl)); A(sb(s, BX1 - 24, 1392, z0, BX1, BY1, BWZ, wl))             # east + door
    A(sb(s, BX1 - 24, 1264, z0 + 128, BX1, 1392, BWZ, wl))
    A(sb(s, BX0, BY0, BWZ, BX1, BY1, BRZ, {'top': T('boardwalk'), 'side': T('booth_' + team), 'bot': T('boardwalk')}))
    # sign above the east door and the south door
    A(ssign(s, (BX1, 1240, z0 + 136), (BX1 + 4, 1416, z0 + 184), T('sign_' + team), 512, 128, 'e', T('wood_black')))
    A(sign_box((s * -952 if s > 0 else 808, BY0 - 4, z0 + 136), (s * -808 if s > 0 else 952, BY0, z0 + 184), T('sign_' + team), 512, 128,
               back=T('wood_black'), facing='s'))
    # awnings (nonsolid, alpha-cut scallops) sloping out over the doors
    aw = T('awning_' + team)
    def awn(pts):
        b = hull(pts, NODRAW_NS, round_pts=False)
        for f in b.faces:
            if f.n[2] > 0.3 or f.n[2] < -0.3: f.tex = aw; f.sc = (0.5, 0.5)
        A(b)
    xo = s * BX1
    awn([(xo, 1248, z0 + 196), (xo, 1408, z0 + 196), (xo + s * 72, 1248, z0 + 160), (xo + s * 72, 1408, z0 + 160),
         (xo, 1248, z0 + 194), (xo, 1408, z0 + 194), (xo + s * 72, 1248, z0 + 158), (xo + s * 72, 1408, z0 + 158)])
    # prize shelf along the west wall with prizes, counter at the south door
    A(sb(s, BX0 + 24, 1240, z0, BX0 + 56, 1424, z0 + 64, {'top': T('counter'), 'side': T('plastic_white'), 'bot': CAULK}))
    smdl(s, 'gummybears/greenbear.md3', -980, 1290, z0 + 64, 0.3, 0)
    smdl(s, 'pad_ducks/pad_duck.md3', -980, 1380, z0 + 64, 0.18, 0)
    # lolly + health station inside
    lol = 'team_CTL_%slolly' % team
    M.ent(lol, (s * -880, 1300, z0 + 16))
    SPOTS['item'].append((lol, s * -880, 1300, z0))
    M.ent('station_health', (s * -808, 1414, z0), angle=(180 if s > 0 else 0))
    item(s, 'ammo_pumper', -900, 1220, z0)
    slight(s, -880, 1328, z0 + 150, 260, '1 0.85 0.65')
    # stairs to the roof along the north wall (rising toward the west), Pumper on the roof
    st = {'top': T('boardwalk'), 'side': T('booth_' + team), 'bot': CAULK}
    for b in stairs(-1024, BY1, -608, BY1 + 96, z0, BRZ, 'w', st):
        mn, mx = b.bounds(); A(sb(s, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], st))
    weapon(s, 'pumper', -880, 1328, BRZ, 'green')
    slight(s, -880, 1328, BRZ + 220, 420)


# =================================================================================================== upper field
def upper_field():
    for (x, y, col) in BUMPERS:
        kw = {}
        if col != 'red': kw['_remap'] = 'models/padpinball/bumper_cap_red;models/padpinball/bumper_cap_%s' % col
        M.model('models/padpinball/pop_bumper.md3', (x, y, 0), angle=0, **kw)
        A(cyl(x, y, 104, 0, 176, WCLIP, 16))
        nm = 'bump_%d' % (x + 1000)
        trigs = [box((x - 150, y + 104, 0), (x + 150, y + 150, 96), TRIG), box((x - 150, y - 150, 0), (x + 150, y - 104, 96), TRIG),
                 box((x + 104, y - 104, 0), (x + 150, y + 104, 96), TRIG), box((x - 150, y - 104, 0), (x - 104, y + 104, 96), TRIG)]
        M.ent('trigger_multiple', brushes=trigs, target=nm, wait=1)
        speaker(x, y, 120, 'sound/items/jumper/boing.wav', loop=False, targetname=nm)
        lc = {'red': '1 0.3 0.25', 'blue': '0.35 0.6 1', 'yellow': '1 0.85 0.3'}[col]
        light(x, y, 260, 420, lc)
    # top rollover lanes
    for xg in (-288, -96, 96, 288):
        A(box((xg - 12, 1792, 0), (xg + 12, 1920, 48), {'side': T('steel'), 'top': T('chrome'), 'bot': CAULK}))
    for k, xs in enumerate((-192, 0, 192)):
        decal(xs - 36, 1724, xs + 36, 1796, 0, 'ins_star_purple_p%d' % k)
    decal(-128, 2120, 128, 2216, 0, 'ins_jackpot_p0', 256, 96)
    # the golden trophy between the lanes and the backbox kicker
    solid_mdl('ente/padstatue_gold.md3', 0, 1990, 0, 1.0, 270)
    # backbox kicker: straight up through the hatch in the backbox floor
    jumppad(0, 2304, 0, (0, 2600, BBF), 1250, 'backbox')
    item(1, 'item_jumper', 0, 1600, 0)
    for s in (1, -1):
        item(s, 'ammo_imperius', -192, 1860, 0)
        item(s, 'ammo_boaster', -560, 2300, 0)
        spawn(s, 'info_player_deathmatch', -400, 2150, 0, 270)
    for (x, y) in ((-600, 1150), (600, 1150), (0, 1650), (-640, 2050), (640, 2050), (0, 2250)):
        light(x, y, 520, 700)


# =================================================================================================== backbox
def backbox():
    bw = {'side': T('wood_black'), 'top': T('wood_black'), 'bot': T('wood_black')}
    x0, x1 = -FX, FX
    # floor with the hatch (x -80..80, y 2224..2384)
    for (a, b_, c, d) in sub_rects((x0, BBY0, x1, BBY1), [(-96, 2208, 96, 2432)]):
        A(box((a, b_, BBZ0), (c, d, BBF), {'top': T('plywood_dark'), 'bot': T('underside'), 'side': T('wood_black')}))
    # front wall (speaker panel + DMD below the glass, backglass above it), side walls, back wall, roof
    fw = box((x0, BBY0, BBF), (x1, BBY0 + 32, BBZ1), {'side': T('wood_black'), 'n': T('lampboard'), 'top': T('cab_exterior'), 'bot': CAULK})
    A(fw)
    A(sign_box((x0, BBY0 - 4, GT), (x1, BBY0, BBZ1), T('backglass'), 2048, 512, back=T('wood_black'), facing='s'))
    # the speaker panel is the south face of the floor slab + the front wall below the glass: a 2u skin
    sp = sign_box((x0, BBY0 - 2, BBZ0), (x1, BBY0, GZ), T('speaker_panel'), 2048, 256, back=T('wood_black'), facing='s')
    A(sp)
    A(sign_box((-320, BBY0 - 6, 916), (320, BBY0 - 2, 1076), T('dmd'), 512, 128, back=T('plastic_black'), facing='s'))
    A(box((x0, BBY0 + 32, BBF), (x0 + 32, BBY1 - 32, BBZ1), {'side': T('wood_black'), 'e': T('plywood_dark')}))
    A(box((x1 - 32, BBY0 + 32, BBF), (x1, BBY1 - 32, BBZ1), {'side': T('wood_black'), 'w': T('plywood_dark')}))
    A(box((x0, BBY1 - 32, BBF), (x1, BBY1, BBZ1), {'side': T('cab_exterior'), 's': T('plywood_dark')}))
    A(box((x0 + 32, BBY0 + 32, BBC), (x1 - 32, BBY1 - 32, BBZ1), {'bot': T('plywood_dark'), 'top': T('cab_exterior'), 'side': CAULK}))
    # inside: MPU box and two speaker boxes against the front wall, circuit boards on the back wall
    A(box((-560, BBY0 + 32, BBF), (-304, BBY0 + 128, 1024), {'side': T('steel_dark'), 'top': T('circuit'), 'bot': CAULK}))
    for xc in (-800, 800):
        b = box((xc - 112, BBY0 + 32, BBF), (xc + 112, BBY0 + 128, 1008), {'side': T('wood_black'), 'top': T('wood_black'), 'bot': CAULK})
        for f in b.faces:
            if f.n[1] > 0.9: f.tex = T('speaker_cone'); fit_face(f, xc - 112, xc + 112, BBF, 1008, 256, 256)
        A(b)
    for xc in (-700, 0, 700):
        A(sign_box((xc - 240, BBY1 - 36, 1000), (xc + 240, BBY1 - 32, 1320), T('circuit'), 256, 256, back=T('steel_dark'), facing='s'))
    # loot: the jackpot
    weapon(1, 'imperius', -170, 2540, BBF, 'purple')
    item(1, 'item_padpower', -700, 2480, BBF)
    item(1, 'ammo_imperius', 700, 2400, BBF)
    item(1, 'ammo_splasher', -1000, 2560, BBF)
    item(1, 'ammo_nipper', 1000, 2560, BBF)
    smdl(1, 'pad_lamps/gooseneck.md3', -400, 2560, BBF, 1.0, 200)
    smdl(1, 'pad_pc/keyboard.md3', 400, 2540, BBF, 1.0, 90)
    # teleporter out (to the middle of the upper field)
    tx, ty = 980, 2420
    mdl_c('pad_teleporter/padtp_orange.md3', tx, ty, BBF, 1.0, 180)
    M.ent('trigger_teleport', brushes=[box((tx - 32, ty - 32, BBF), (tx + 32, ty + 32, BBF + 64), TRIG)], target='bb_out')
    M.ent('misc_teleporter_dest', (0, 1640, 24), angle=270, targetname='bb_out')
    # jackpot fanfare when you land
    trig = box((-96, 2448, BBF + 8), (96, 2620, BBF + 72), TRIG)
    M.ent('trigger_multiple', brushes=[trig], target='jackpot', wait=8)
    speaker(0, 2500, 1100, 'sound/world/human/applause.ogg', loop=False, targetname='jackpot')
    speaker(0, 2400, 1000, 'sound/world/machine/fan_pc.ogg')
    for (x, y) in ((-800, 2400), (0, 2420), (800, 2400)):
        light(x, y, 1400, 650, '1 0.85 0.6')
    light(0, 2300, 960, 200, '1 0.6 0.2')


# =================================================================================================== underworld
def underworld():
    pw = {'side': T('plywood'), 'top': CAULK, 'bot': CAULK}
    # solid fill under the board outside the underworld (walls of the cabinet interior)
    for (x0, y0, x1, y1) in sub_rects((-FX, -FY, FX, FY), [(-UX, UY0, UX, UY1)]):
        A(box((x0, y0, UZ), (x1, y1, BZ), pw))
    # drain ramp from under the hole down to the floor (falls of ~250-330u: a medium bump)
    yl = -1792
    A(hull([(x, y, z) for x in (-128, 128) for (y, z) in ((UY0, UZ), (UY0, -144), (yl, UZ))],
           {'top': T('steel'), 'side': T('plywood_dark'), 'bot': CAULK}, round_pts=False))
    # coin box: galvanised, door in the south face, coins on the floor; crate steps up both sides to its roof
    gb = {'side': T('galvanised'), 'top': T('galvanised'), 'bot': CAULK}
    cx0, cy0, cx1, cy1, ch = -192, -1664, 192, -1344, -240
    A(box((cx0, cy0, UZ), (-64, cy0 + 16, ch), gb)); A(box((64, cy0, UZ), (cx1, cy0 + 16, ch), gb))
    A(box((-64, cy0, UZ + 128), (64, cy0 + 16, ch), gb))
    A(box((cx0, cy1 - 16, UZ), (cx1, cy1, ch), gb))
    A(box((cx0, cy0 + 16, UZ), (cx0 + 16, cy1 - 16, ch), gb)); A(box((cx1 - 16, cy0 + 16, UZ), (cx1, cy1 - 16, ch), gb))
    A(box((cx0, cy0, ch), (cx1, cy1, ch + 16), gb))
    A(box((cx0 + 16, cy0 + 16, UZ), (cx1 - 16, cy1 - 16, UZ + 8), {'top': T('coins'), 'side': T('galvanised'), 'bot': CAULK}))
    for (xa, xb) in ((-192, -64), (64, 192)):
        A(sign_box((xa, cy0 - 4, UZ + 16), (xb, cy0, UZ + 144), T('coin_door'), 256, 256, back=T('galvanised'), facing='s'))
    top = ch + 16                                                      # -224
    for s in (1, -1):
        for k in range(7):
            x0 = -528 + 48 * k
            A(sb(s, x0, -1600, UZ, x0 + 48, -1504, UZ + 32 * (k + 1), {'top': T('plywood'), 'side': T('plywood_dark'), 'bot': CAULK}))
    weapon(1, 'betty', 0, -1560, UZ + 8, 'black')
    item(1, 'item_speedy', 0, -1440, UZ + 8)
    item(1, 'ammo_imperius', 0, -1500, top)
    trig = box((-48, cy0 + 16, UZ + 8), (48, cy0 + 64, UZ + 72), TRIG)
    M.ent('trigger_multiple', brushes=[trig], target='coins', wait=10)
    speaker(0, -1500, -300, 'sound/world/misc/secret_found.ogg', loop=False, targetname='coins')
    light(0, -1500, -300, 160, '1 0.85 0.5')
    # VUK kicker back up onto the playfield (lands south of the hole)
    jumppad(VUK[0], VUK[1], UZ, (0, -1310, 0), 320, 'vuk')
    # teleport pads: the "ball trough" serves you straight into either plunger lane's launch pad
    for s in (1, -1):
        team = 'red' if s > 0 else 'blue'
        tx, ty = s * -640, -800
        mdl_c('pad_teleporter/padtp_%s.md3' % ('pink' if s > 0 else 'blue'), tx, ty, UZ, 1.0, 90)
        M.ent('trigger_teleport', brushes=[box((tx - 32, ty - 32, UZ), (tx + 32, ty + 32, UZ + 64), TRIG)], target='serve_' + team)
        M.ent('misc_teleporter_dest', (s * -1200, -2170, 25), angle=90, targetname='serve_' + team)   # slides onto the plunger pad
    # transformer (west) and speaker (east)
    A(box((-720, -2304, UZ), (-464, -2112, -288), {'side': T('transformer'), 'top': T('steel_dark'), 'bot': CAULK}))
    for xc in (-656, -528):
        A(cyl(xc, -2208, 40, -288, -208, {'side': T('copper'), 'top': T('steel_dark'), 'bot': CAULK}, 12))
    b = box((464, -2304, UZ), (720, -2112, -384), {'side': T('wood_black'), 'top': T('speaker_cone'), 'bot': CAULK})
    fit_top(b, 464, -2304, 720, -2112, 256, 256)
    A(b)
    # hanging wiring looms (nonsolid sprites)
    for (x, y, ang) in ((-500, -1200, 20), (420, -1000, 80), (-300, -2000, 0), (600, -1700, 45), (-700, -1500, 60), (250, -800, 10), (-250, -900, 120)):
        a = math.radians(ang); dx, dy = math.cos(a) * 32, math.sin(a) * 32
        nx, ny = -math.sin(a), math.cos(a)
        q = [(x - dx, y - dy), (x + dx, y + dy), (x + dx + nx, y + dy + ny), (x - dx + nx, y - dy + ny)]
        bb = hull([(px, py, z) for (px, py) in q for z in (-240, BZ)], lambda n, nx=nx, ny=ny: T('cables') if abs(n[0] * nx + n[1] * ny) > 0.9 else NODRAW_NS, round_pts=False)
        for f in bb.faces:
            if f.tex == T('cables'): f.sc = (0.5, (BZ + 240) / 256)
        A(bb)
    # loot + junk
    M.ent('station_health', (-700, -1000, UZ), angle=0)
    for s in (1, -1):
        item(s, 'ammo_betty', -700, -1500, UZ)
        spawn(s, 'info_player_deathmatch', -400, -900, UZ, 90)
    item(1, 'item_visionless', 0, -760, UZ)
    item(1, 'ammo_nipper', 400, -700, UZ)
    item(1, 'holdable_killerducks', 600, -1000, UZ)
    item(1, 'holdable_bambam', -400, -1250, UZ)
    item(1, 'item_armor_shard', 700, -1300, UZ)
    mdl_c('pad_ddmix/backyard/screw_nut.md3', 300, -2000, UZ, 2.0, 20)
    mdl_c('pad_ddmix/backyard/screwnut_thin.md3', -360, -1800, UZ, 2.5, 70)
    mdl_c('pad_ddmix/gallery/fire_extinguisher.md3', -820, -760, UZ, 1.6, 0)
    mdl_c('pad_tins/pad_coke_sd.md3', 360, -1200, UZ, 1.0, 30)
    mdl_c('pad_ddmix/trashcan/lamp_sewer_lit.md3', 700, -760, UZ, 1.0, 200)
    mdl_c('spider/spider.md3', -820, -2380, UZ, 2.0, 45)
    mdl_c('pad_ddmix/mix/matchbook_padman.md3', 200, -2300, UZ, 2.0, 15)
    mdl_c('pad_pencils/pad_pencilsr_lg.md3', -560, -1900, UZ, 1.0, 30)
    # light: dim amber work lights, an electric hum
    for (x, y) in ((-560, -2000), (560, -2000), (-560, -1100), (560, -1100), (0, -800), (0, -2200), (-600, -700), (600, -700)):
        light(x, y, -150, 520, '1 0.75 0.45')
    speaker(-590, -2208, -250, 'sound/world/machine/transformer.ogg')
    speaker(0, -1600, -200, 'sound/world/machine/electric_sizzle.ogg', loop=False, targetname='zap')
    M.ent('func_timer', (0, -1600, -120), target='zap', wait=20, random=10, spawnflags=1)


# =================================================================================================== spawns + ambience
def spawns():
    for s in (1, -1):
        team = 'red' if s > 0 else 'blue'
        for (x, y, z, a) in ((-680, 1640, MPZ, 270), (-640, 1180, MPZ, 180), (-900, 760, 0, 90), (-440, 1720, 0, 270)):
            spawn(s, 'team_%splayer' % team, x, y, z, a)
        for (x, y, z, a) in ((-900, -420, 0, 90), (-600, -1350, 0, 90), (-1000, 250, 0, 90), (-420, 680, 0, 90),
                             (-1200, -1000, 0, 90), (-760, 2150, 0, 0)):
            spawn(s, 'team_%sspawn' % team, x, y, z, a)
        for (x, y, z, a) in ((-400, -1720, 0, 90), (-880, -1180, 0, 45), (-240, -300, 0, 90), (-850, 420, 0, 90),
                             (-640, 1520, 0, 270), (-1200, -100, 0, 90)):
            spawn(s, 'info_player_deathmatch', x, y, z, a)


def tent():
    """fortune-teller tent in the middle of the table: octagon with four doors, the neutral lolly inside, flat striped roof
    reached by toy-block steps (32u) on both sides"""
    cx, cy = TENT
    n = 8
    out = ngon(cx, cy, 176, n); inn = ngon(cx, cy, 160, n)          # vertices at 22.5 + 45k: faces centred on 45k
    wl = {'side': T('tent_wall'), 'top': T('tent_wall'), 'bot': CAULK}
    doors = {1, 5}                           # north and south faces; the E / W faces carry the block steps
    for k in range(n):
        q = [inn[k], out[k], out[(k + 1) % n], inn[(k + 1) % n]]
        z0 = 112 if k in doors else 0
        A(hull([(x, y, z) for (x, y) in q for z in (z0, 160)], wl, round_pts=False))
    A(hull([(x, y, z) for (x, y) in out for z in (160, 176)], {'top': T('tent_top'), 'side': T('tent_wall'), 'bot': T('tent_top')}, round_pts=False))
    for f in M.world[-1].faces:
        if f.n[2] > 0.9: fit_top_face(f, cx - 176, cy - 176, cx + 176, cy + 176, 256, 256)
    # toy-block steps up to the roof, east and west
    for s in (1, -1):
        ap = math.ceil(176 * math.cos(math.radians(22.5))) + 1      # E / W face plane
        for k in range(5):
            x0 = ap + 48 * (4 - k)
            ch = 'abcde'[k]
            A(sb(s, -(x0 + 48), cy - 32, 0, -x0, cy + 32, 32 * (k + 1), T('block_' + ch)))
    item(1, 'team_CTL_neutrallolly', cx, cy, 0)
    item(1, 'holdable_boomies', cx, cy, 176)
    light(cx, cy, 120, 220, '1 0.8 1')
    light(cx, cy, 420, 500)


def toys():
    """extra cover breaking the long sightlines: standing gummy bears, rubber islands"""
    for s in (1, -1):
        smdl(s, 'gummybears/redbear.md3' if s > 0 else 'gummybears/yellowbear.md3', -480, 220, 0, 1.0, 300, solid=True, shrink=0.25)
        smdl(s, 'gummybears/greenbear.md3' if s > 0 else 'gummybears/orangebear.md3', -540, 700, 0, 1.0, 20, solid=True, shrink=0.25)
        smdl(s, 'gummybears/orangebear.md3' if s > 0 else 'gummybears/greenbear.md3', -260, -1460, 0, 1.0, 340, solid=True, shrink=0.25)
        for (pts, tex) in ((((-1010, -240), (-800, -240), (-900, -40)), 'plastic_yellow'), (((-520, 1330), (-380, 1450), (-520, 1530)), 'plastic_green')):
            A(sh(s, [(x, y, z) for (x, y) in pts for z in (0, 72)], {'top': T(tex), 'side': T('rubber'), 'bot': CAULK}, rnd=False))


def corner_props(s):
    """toy blocks under the corner playfield and a trophy north of it (cover on the long north-south lines)"""
    A(sb(s, -900, 1100, 0, -804, 1196, 96, T('block_b')))
    A(sb(s, -760, 1460, 0, -664, 1556, 96, T('block_d')))
    smdl(s, 'ente/padstatue_winner.md3', -850, 1830, 0, 1.0, 270, solid=True)


def ambience():
    # general illumination bulbs under the glass
    for x in (-960, -320, 320, 960):
        for y in range(-2200, 2201, 550):
            light(x, y, 780, 2400)
    speaker(0, -1500, 600, 'sound/world/machine/aircon.ogg')
    # an occasional TILT buzzer and a bell from somewhere in the machine
    speaker(0, 0, 900, 'sound/world/misc/alarm_buzzer.ogg', loop=False, targetname='tilt')
    M.ent('func_timer', (0, 100, 900), target='tilt', wait=70, random=30, spawnflags=1)
    speaker(0, 1200, 600, 'sound/world/misc/bicycle_bell.ogg', loop=False, targetname='ding')
    M.ent('func_timer', (0, 1100, 600), target='ding', wait=17, random=8, spawnflags=1)


# =================================================================================================== main
def main():
    TX.make_all(OUT)
    room_and_cabinet(); board(); steel_ball(); drop_targets(); upper_field(); backbox(); underworld()
    for s in (1, -1):
        plunger_lane(s); flipper_end(s); midfield(s); ramp(s); mini_playfield(s); booth(s); corner_props(s)
    tent(); toys()
    spawns(); ambience()
    M.ent('info_player_intermission', (-1100, -2300, 900), angles='22 60 0')
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    open(os.path.join(OUT, 'maps', MAPNAME + '.map'), 'w').write(
        M.text(f"// {TX.LONGNAME} - generated by wop_tools/padpinball/build_padpinball.py\n"))
    nb = len(M.world) + sum(len(e['_brushes']) for e in M.ents)
    print(f'brushes {nb}, entities {len(M.ents)}, models {len(M.models)}')
    for (nm, o, tg, land) in JUMPPADS:
        print('pad', nm, 'trig', o, 'target', tg, 'land', tuple(round(v) for v in land))


if __name__ == '__main__':
    main()
