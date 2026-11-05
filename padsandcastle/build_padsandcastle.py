#!/usr/bin/env python3
"""Sandcastle Showdown (wop_padsandcastle) - CTL / FFA on a Kiwi summer beach at Padman scale (~8u per cm).

    OUT=<dir> python3 build_padsandcastle.py        (or: wopbuild.py padsandcastle gen / preview / check / all)

Mirror symmetric in x (red west, blue east). Everything is written for the blue (+x) side in layout.py and placed for
both sides with s = +1 (blue) / -1 (red):
  castles    bucket-moulded keep (team lolly inside, lift pad up through the roof hatch + courtyard pad), four turrets,
             crenellated walls with a 16u stair to the wall walk, lolly-stick drawbridge over the moat, posterns
  Mount Sandy  two-tier sand mountain in the middle: 16u stairs E/W to the terrace (Pumper), pads to the summit
             (Imperius), a tunnel north-south through it with the neutral lolly (1LC)
  beach      rock pool in the shallows (Splasher on the bottom, 16u steps both ends), spade, buckets, beach ball, crabs,
             seagulls, driftwood, shells; the sea everywhere south of the beach slope is wading depth
  picnic     giant umbrella over a towel, chilly bins with bodyboard ramps (Betty on top), the giant conch: walk into
             its mouth -> the Mermaid's Grotto (sealed, below the world) -> teleporter back
Collision is common/weapclip just inside every custom MD3; the hull is the only structural part (low portal count).
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path: sys.path.insert(0, p)
from wopmap import box, cyl, hull, carve, sub_rects, sign_box, prism as bprism, ngon
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL
import layout as L
import sc_models as SM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = L.BOUNDS
HX0, HY0, HX1, HY1 = L.HULL
K = MapKit(MAP, NS, LONG, L.BOUNDS, worldspawn={'_ambient': '16', '_color': '1 0.97 0.9', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
SM.init(TX)
SIDES = (1, -1)                                  # blue (+x), red (-x)
TEAM = {1: 'blue', -1: 'red'}
SAND = {'top': None, 'side': None, 'bot': CAULK}


def tx(top, side=None, bot=CAULK):
    return {'top': T(top), 'side': T(side or top), 'bot': bot}


def R(s, x0, y0, x1, y1):
    """blue-side rect mirrored for side s"""
    a, b = s * x0, s * x1
    return (min(a, b), y0, max(a, b), y1)


def mbox(s, mn, mx, tex):
    a, b = s * mn[0], s * mx[0]
    return box((min(a, b), mn[1], mn[2]), (max(a, b), mx[1], mx[2]), tex)


def ang(s, a):
    """a yaw written for the blue side, mirrored for side s"""
    return a % 360 if s > 0 else (180 - a) % 360


def frustum(cx, cy, r0, r1, z0, z1, n=16, tex=WCLIP, phase=None):
    p0 = ngon(cx, cy, r0, n, phase); p1 = ngon(cx, cy, r1, n, phase)
    return hull([(x, y, z0) for x, y in p0] + [(x, y, z1) for x, y in p1], tex)


def place(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, **kw)


# ================================================================================================= shell + ground
def shell():
    """structural base slab and walls (caulk outside, sky inside) and the sky ceiling: the only structural brushes"""
    sk = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: T('sky')})
    K.add(box((HX0 - 32, HY0 - 32, L.ZBASE - 32), (HX1 + 32, HY1 + 32, L.ZBASE), CAULK, detail=False))
    K.add(box((HX0 - 32, HY0 - 32, L.ZBASE), (HX0, HY1 + 32, L.ZTOP), sk('e'), detail=False))
    K.add(box((HX1, HY0 - 32, L.ZBASE), (HX1 + 32, HY1 + 32, L.ZTOP), sk('w'), detail=False))
    K.add(box((HX0, HY0 - 32, L.ZBASE), (HX1, HY0, L.ZTOP), sk('n'), detail=False))
    K.add(box((HX0, HY1, L.ZBASE), (HX1, HY1 + 32, L.ZTOP), sk('s'), detail=False))
    K.add(box((HX0 - 32, HY0 - 32, L.ZTOP), (HX1 + 32, HY1 + 32, L.ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))


WATER_CUT = []          # everything standing in the sea (carved out of the one water box)


def ground():
    """detail sand fill on the structural slab: beach (z 0) with the two moats, the beach slope, the sea floor with the
    rock pool. One water box for the whole sea + pool, one per moat."""
    moats = [R(s, L.MOAT[0], L.MOAT_Y[0], L.MOAT[1], L.MOAT_Y[1]) for s in SIDES]
    for r in sub_rects((HX0, L.BEACH_Y, HX1, HY1), moats):
        K.add(box((r[0], r[1], L.ZBASE), (r[2], r[3], 0), tx('sand', 'sand_packed')))
    # moats: flat bottom + two plain sand banks (37 deg), water 38 deep
    for s in SIDES:
        a, b = L.MOAT
        bx0, bx1 = a + 64, b - 64
        K.add(mbox(s, (bx0, L.MOAT_Y[0], L.ZBASE), (bx1, L.MOAT_Y[1], L.SEA_FLOOR), tx('sand_wet')))
        y0, y1 = L.MOAT_Y
        banks = []
        for (p, q, rise) in ((a, bx0, 'w'), (bx1, b, 'e')):
            rr = R(s, p, y0, q, y1)
            rs = rise if s > 0 else {'w': 'e', 'e': 'w'}[rise]
            banks.append(K.ramp(rr[0], y0, rr[2], y1, L.SEA_FLOOR, 0, rs, tx('sand_wet'), base=L.ZBASE))
        mr = R(s, a, y0, b, y1)
        K.water_box((mr[0], y0, L.SEA_FLOOR), (mr[2], y1, L.WATER_Z), T('water'), cutters=banks)
        K.speaker(s * (a + b) / 2, 300, 40, 'ambient/water_rippling')
    # beach slope (10 deg) into the sea
    slope = K.ramp(HX0, L.SHORE_Y, HX1, L.BEACH_Y, L.SEA_FLOOR, 0, 'n', tx('sand_wet', 'sand_packed'), base=L.ZBASE)
    WATER_CUT.append(slope)
    # sea floor round the rock pool
    px0, py0, px1, py1 = L.POOL
    for r in sub_rects((HX0, HY0, HX1, L.SHORE_Y), [L.POOL]):
        b = box((r[0], r[1], L.ZBASE), (r[2], r[3], L.SEA_FLOOR), tx('sand_sea', 'rock'))
        K.add(b); WATER_CUT.append(b)
    # rock pool: floor, 16u steps down both ends (never a sheer lip)
    K.add(box((px0, py0, L.ZBASE), (px1, py1, L.POOL_FLOOR), tx('sand_sea')))
    run = L.POOL_STEP_RUN
    WATER_CUT.extend(K.stairs16(px1 - run, py0, px1, py1, L.POOL_FLOOR, L.SEA_FLOOR, 'e', tx('sand_sea', 'rock')))
    WATER_CUT.extend(K.stairs16(px0, py0, px0 + run, py1, L.POOL_FLOOR, L.SEA_FLOOR, 'w', tx('sand_sea', 'rock')))
    # surf line: an additive foam decal 1u over the water where it meets the slope
    fy = L.BEACH_Y - 58                                     # the slope is at z -10.7 here: the decal floats over water
    fz = L.WATER_Z + 1
    K.add(box((HX0, fy - 44, fz), (HX1, fy, fz + 1), {'top': T('foam'), 'side': T('nodraw_ns'), 'bot': T('nodraw_ns')}))
    K.speaker(0, -1100, 40, 'ambient/ocean_waves'); K.speaker(-1800, -1100, 40, 'ambient/ocean_waves')
    K.speaker(1800, -1100, 40, 'ambient/ocean_waves')
    K.speaker(0, -1400, -100, 'ambient/water_rippling')


def bounds_clip():
    """player clip round the playable rectangle (bspc treats it as solid); the dunes and the sea carry on behind it"""
    c = CLIP
    walls = [box((HX0, Y1, 0), (HX1, Y1 + 16, L.ZTOP), c), box((HX0, Y0 - 16, L.SEA_FLOOR), (HX1, Y0, L.ZTOP), c),
             box((X1, L.BEACH_Y, 0), (X1 + 16, Y1, L.ZTOP), c), box((X0 - 16, L.BEACH_Y, 0), (X0, Y1, L.ZTOP), c),
             box((X1, Y0, L.SEA_FLOOR), (X1 + 16, L.SHORE_Y, L.ZTOP), c), box((X0 - 16, Y0, L.SEA_FLOOR), (X0, L.SHORE_Y, L.ZTOP), c)]
    # over the beach slope the clip follows the slope (a wedge-topped strip under a box)
    for xa in (X1, X0 - 16):
        walls.append(box((xa, L.SHORE_Y, 0), (xa + 16, L.BEACH_Y, L.ZTOP), c))
    for w in walls: K.add(w)
    WATER_CUT.extend([w for w in walls if w.bounds()[0][2] < L.WATER_Z])


def sea_water():
    """ONE water box for the sea and the rock pool, carved by everything standing in it"""
    K.water_box((HX0, HY0, L.POOL_FLOOR), (HX1, L.BEACH_Y, L.WATER_Z), T('water'),
                cutters=[b for b in WATER_CUT if b.bounds()[0][2] < L.WATER_Z])


# ================================================================================================= castles
def castle(s):
    team = TEAM[s]
    cx0, cy0, cx1, cy1 = L.CX0, L.CY0, L.CX1, L.CY1
    W, H = L.WALL_T, L.WALL_H
    rt = 138                                             # turret collision radius at the foot
    g0, g1 = L.GATE; p0, p1 = L.POSTERN
    # wall pieces (blue-side rects), all 0..WALL_H; teeth along the outer edge
    walls = [((cx0, cy0 + 48 + rt, cx0 + W, g0), 'w'), ((cx0, g1, cx0 + W, cy1 - 48 - rt), 'w'),
             ((cx1 - W, cy0 + 48 + rt, cx1, cy1 - 48 - rt), 'e'),
             ((p1, cy0, cx1 - 48 - rt, cy0 + W), 's'), ((p1, cy1 - W, cx1 - 48 - rt, cy1), 'n')]
    brushes = []
    for (r, side) in walls:
        rr = R(s, *r)
        brushes.append(box((rr[0], rr[1], 0), (rr[2], rr[3], H), WCLIP))
        oside = side if s > 0 or side in 'ns' else {'w': 'e', 'e': 'w'}[side]
        for (tr, z0, z1) in L.wall_teeth(r[0], r[1], r[2], r[3], H, H + 24, side):
            t2 = R(s, *tr)
            brushes.append(box((t2[0], t2[1], z0), (t2[2], t2[3], z1), WCLIP))
    K.solid_piece(f'walls_{team}', brushes, TX.texfn('sand_castle', tile=256))
    # lolly-stick lintels over the gate and the posterns (the wall walk runs on over them)
    lint = [((cx0, g0, cx0 + W, g1), 'stick_gate', 90), ((p0, cy0, p1, cy0 + W), 'stick_postern', 0),
            ((p0, cy1 - W, p1, cy1), 'stick_postern', 0)]
    for (r, name, a) in lint:
        rr = R(s, *r)
        K.add(box((rr[0], rr[1], L.LINTEL_Z), (rr[2], rr[3], H), WCLIP))
        place(name, (rr[0] + rr[2]) / 2, (rr[1] + rr[3]) / 2, L.LINTEL_Z, a, occupy=False)
        K.reserve(((rr[0], rr[1], L.LINTEL_Z), (rr[2], rr[3], H)))
    # turrets: ribbed bucket MD3 on a tapered 16-gon weapclip core, crenellations on the rim
    for (tx_, ty) in L.TURRETS:
        x = s * tx_
        place('turret', x, ty, 0, 0)
        K.add(cyl(x, ty, 130, 0, L.TURRET_H, WCLIP, 16))      # vertical: a tapered core left sliver 'floors' near the top
        for (poly, z0, z1) in L.teeth(x, ty, 120, 136, L.TURRET_H, L.TURRET_H + 24, 12, 0.25):
            K.add(hull([(px, py, z0) for px, py in poly] + [(px, py, z1) for px, py in poly], WCLIP, round_pts=False))
        K.occupy_disc(x, ty, 158, 0, L.TURRET_H + 24, strips=6)
    # keep: shell MD3 (door toward the gate), 32 wedges of weapclip with the door wedges open below the arch
    kx, ky = s * L.KEEP[0], L.KEEP[1]
    door_dir = math.pi if s > 0 else 0.0
    place('keep', kx, ky, 0, 180 if s > 0 else 0)
    n = 32
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        mid = (a0 + a1) / 2
        dd = abs((mid - door_dir + math.pi) % (2 * math.pi) - math.pi)
        z0 = L.DOOR_TOP if dd < math.radians(22.5) else 0
        # inner/outer radii shrink linearly with height: 216->196 inside, 250->230 outside
        P = []
        for a in (a0, a1):
            for z in (z0, L.KEEP_H):
                f = z / L.KEEP_H
                for r in (212, 250 - 20 * f):             # inner face vertical (a leaning wall cut the headroom)
                    P.append((kx + r * math.cos(a), ky + r * math.sin(a), z))
        K.add(hull(P, WCLIP))
    # roof slab with the square hatch, and the crenellations
    roof = frustum(kx, ky, 230, 230, L.KEEP_H, L.KEEP_TOP, 32)
    h = L.KEEP_HOLE / 2
    for piece in carve(roof, [box((kx - h, ky - h, L.KEEP_H - 8), (kx + h, ky + h, L.KEEP_TOP + 8), WCLIP)]):
        K.add(piece)
    for (poly, z0, z1) in L.teeth(kx, ky, 214, 230, L.KEEP_TOP, L.KEEP_TOP + 24, 16, 0.25):
        K.add(hull([(px, py, z0) for px, py in poly] + [(px, py, z1) for px, py in poly], WCLIP, round_pts=False))
    dx0 = kx - s * 262
    K.keep_clear(min(dx0, dx0 - s * 120), ky - 110, max(dx0, dx0 - s * 120), ky + 110, 0)     # in front of the door
    # inside: lift pad under the hatch -> roof; team lolly at the back
    K.jumppad(kx, ky, 0, land=(kx + s * 140, ky + 40, L.KEEP_TOP), apex=L.KEEP_TOP + 190, name=f'pad_keep_{team}',
              ceiling=None, edges=[(kx + s * 80, ky, L.KEEP_TOP)])
    K.ent(f'team_CTL_{team}lolly', (round(kx + s * 130), round(ky - 90), 16))
    K.occupy_r(kx + s * 130, ky - 90, 40, 0, 64)
    K.occupy_disc(kx, ky, 266, 0, L.KEEP_TOP + 24)               # after the pad + lolly inside
    K.light(kx, ky + 120, 300, 260, '1 0.9 0.75'); K.light(kx + s * 120, ky - 120, 300, 220, '1 0.9 0.75')
    # courtyard pad onto the keep roof (east of the keep)
    K.jumppad(s * 2232, ky + 210, 0, land=(kx + s * 120, ky + 150, L.KEEP_TOP), apex=L.KEEP_TOP + 200,
              name=f'pad_keeproof_{team}', edges=[(kx + s * 230, ky + 170, L.KEEP_TOP)])
    # flag on the keep roof + flags on the two front turrets
    place(f'flag_{team}', kx - s * 40, ky - 175, L.KEEP_TOP, 0 if s > 0 else 180, occupy=False)
    K.add(box((kx - s * 40 - 22, ky - 175 - 8, L.KEEP_TOP), (kx - s * 40 + 22, ky - 175 + 8, L.KEEP_TOP + 300), WCLIP))
    for (tx_, ty) in L.TURRETS[:2]:
        place(f'flag_{team}', s * tx_, ty, L.TURRET_H, 0 if s > 0 else 180, occupy=False)
        K.add(box((s * tx_ - 22, ty - 8, L.TURRET_H), (s * tx_ + 22, ty + 8, L.TURRET_H + 300), WCLIP))
    # 16u stairs up to the wall walk (inside the south and north walls, rising toward the back)
    for (r, nm) in ((L.STAIRS_S, 's'), (L.STAIRS_N, 'n')):
        rr = R(s, *r)
        K.stairs16(rr[0], rr[1], rr[2], rr[3], 0, H, 'e' if s > 0 else 'w', tx('sand_packed'), route=f'wallstair_{nm}_{team}')
        K.reserve(((rr[0], rr[1], 0), (rr[2], rr[3], H)))
        foot = rr[0] - 100 if s > 0 else rr[2]
        K.keep_clear(foot, rr[1], foot + 100, rr[3], 0)
    # drawbridge: three ice-block sticks over the moat
    bx0, bx1, by0, by1 = L.BRIDGE
    rr = R(s, bx0, by0, bx1, by1)
    K.add(box((rr[0], by0, 0), (rr[2], by1, 16), WCLIP))
    for y in (by0 + 40, (by0 + by1) / 2, by1 - 40):
        place('stick_bridge', (rr[0] + rr[2]) / 2, y, 0, 0, occupy=False)
    K.reserve(((rr[0], by0, 0), (rr[2], by1, 16)))
    m0, m1 = R(s, L.MOAT[0], by0, L.MOAT[1], by1)[0::2]
    K.crawl((m0, by0, L.SEA_FLOOR), (m1, by1, 0))               # swim under the drawbridge (water, intended)
    K.keep_clear(rr[0] - 120, by0, rr[2] + 160, by1, 0)
    # routes
    K.route(f'gate_{team}', (s * 900, 450, 0), (s * 1580, 450, 0))
    K.route(f'keepdoor_{team}', (s * 1580, 300, 0), (kx, ky - 140, 0))
    K.route(f'postern_s_{team}', (s * 1643, -300, 0), (s * 1643, 20, 0))
    K.route(f'postern_n_{team}', (s * 1643, 1200, 0), (s * 1643, 880, 0))
    K.route(f'wallwalk_{team}', (s * 2100, -102, H), (s * 1448, 600, H))
    for (px_, py_) in ((L.POSTERN[0] + L.POSTERN[1]) / 2, -100), ((L.POSTERN[0] + L.POSTERN[1]) / 2, 1000):
        K.keep_clear(s * px_ - 57, py_ - 150, s * px_ + 57, py_ + 150, 0)
    # courtyard decoration: catalog castle set
    K.catalog('pad_ddmix/castle/padking.md3', s * 2510, 120, 0, scale=2.6, angle=ang(s, 180), lit=True)
    for (x, y) in ((2340, 250), (2340, 650)):
        K.catalog('pad_ddmix/castle/torch.md3', s * x, y, 0, scale=2.5, angle=ang(s, 180), clip=False)
    K.station(s * 1600, 800, 0, ang(s, 0))


# ================================================================================================= Mount Sandy
def mountain():
    mx, my = L.MOUNT
    place('mount', mx, my, 0, 0, occupy=False)
    t1 = bprism(ngon(mx, my, L.T1_R, 24, 7.5), 0, L.T1_H, WCLIP)
    tun = box((mx - L.TUNNEL_W, my - L.T1_R - 32, -1), (mx + L.TUNNEL_W, my + L.T1_R + 32, L.TUNNEL_H), WCLIP)
    for piece in carve(t1, [tun]): K.add(piece)
    K.add(frustum(mx, my, 296, 272, L.T1_H, L.T2_H, 24, phase=7.5))
    K.occupy_disc(mx, my, L.T1_R + 16, 0, L.T1_H)
    K.occupy(mx - 220, my - 220, mx + 220, my + 220, L.T1_H, L.T2_H)       # inside the round summit tier
    face = L.T1_R * math.cos(math.radians(7.5))
    y0, y1 = L.MSTAIR_Y
    for s in SIDES:
        rr = R(s, face, y0, face + L.MSTAIR_RUN, y1)
        K.stairs16(rr[0], y0, rr[2], y1, 0, L.T1_H, 'w' if s > 0 else 'e', tx('sand_packed'), route=f'mount_stair_{TEAM[s]}')
        K.reserve(((rr[0], y0, 0), (rr[2], y1, L.T1_H)))
        K.keep_clear(s * (face + L.MSTAIR_RUN) - 60, y0, s * (face + L.MSTAIR_RUN) + 60, y1, 0)
        # terrace -> summit pads
        K.jumppad(s * 300, my + 330, L.T1_H, land=(s * 70, my + 70, L.T2_H), apex=L.T2_H + 170, name=f'pad_summit_{TEAM[s]}',
                  edges=[(s * 190, my + 190, L.T2_H)])
    # tunnel: clear walk-through, the neutral lolly in the middle
    K.keep_clear(mx - L.TUNNEL_W, my - L.T1_R - 140, mx + L.TUNNEL_W, my - L.T1_R + 40, 0)
    K.keep_clear(mx - L.TUNNEL_W, my + L.T1_R - 40, mx + L.TUNNEL_W, my + L.T1_R + 140, 0)
    K.ent('team_CTL_neutrallolly', (mx, my, 16)); K.occupy_r(mx, my, 40, 0, 64)
    K.route('tunnel', (mx, my - L.T1_R - 100, 0), (mx, my + L.T1_R + 100, 0))
    K.light(mx, my - 300, 120, 200, '1 0.85 0.6'); K.light(mx, my + 300, 120, 200, '1 0.85 0.6')
    # summit flag + applause
    place('flag_yellow', mx, my + 200, L.T2_H, 0, occupy=False)
    K.add(box((mx - 22, my + 192, L.T2_H), (mx + 22, my + 208, L.T2_H + 300), WCLIP))
    K.trigger_sound((mx - 90, my - 90, L.T2_H), (mx + 90, my + 90, L.T2_H + 64), 'human/applause', 'summit_cheer', wait=20)


# ================================================================================================= picnic + secret
def picnic():
    px, py = L.PARASOL
    place('parasol', px, py, 0, 0, occupy=False)
    K.add(cyl(px, py, 26, 0, 1290, WCLIP, 8)); K.occupy_r(px, py, 64, 0, 1300)
    tw = box((L.TOWEL[0], L.TOWEL[1], 0), (L.TOWEL[2], L.TOWEL[3], 4), {'top': T('towel'), 'side': T('towel'), 'bot': CAULK})
    for f in tw.faces:
        if f.n[2] > 0.9:
            sx_, sy_ = (L.TOWEL[2] - L.TOWEL[0]) / 512, (L.TOWEL[3] - L.TOWEL[1]) / 512
            f.sc = (sx_, sy_); f.off = ((-L.TOWEL[0] / sx_) % 512, (L.TOWEL[3] / sy_) % 512)
    K.add(tw); K.reserve(tw)
    place('sunnies', 260, 1110, 4, 20, occupy=False)
    place('sunscreen', -300, 1080, 4, 70, occupy=False)
    K.speaker(px, py, 900, 'misc/wind_chimes')
    for s in SIDES:
        bx, by = s * L.BIN[0], L.BIN[1]
        w, d, h = L.BIN_W / 2, L.BIN_D / 2, L.BIN_H
        place('chilly_bin', bx, by, 0, 0, boxes=[((-w + 4, -d + 4, 0), (w - 4, d - 4, h))])
        # bodyboard ramp up the south side of the bin (rises north)
        L_, rise = 460, h
        x0, x1 = bx - 128, bx + 128
        ya, yb = by - d, by - d - L_
        K.ramp(x0, yb, x1, ya, 0, h, 'n', WCLIP)               # solid wedge under the board (no bot pocket below it)
        place('bodyboard', bx, ya, h, 90, occupy=False)
        K.reserve(((x0, yb, 0), (x1, ya, h)))
        K.keep_clear(x0, yb - 110, x1, yb, 0)
        K.route(f'bin_ramp_{TEAM[s]}', (bx, yb - 80, 0), (bx, by, h))
    K.prop(ML.PLACE['beach_bag'], 380, 1340, 0, boxes=[((-146, -66, 0), (146, 66, 226))], angle=10)
    # the conch: half buried, mouth (east) open; weapclip round the body leaves the mouth tunnel free
    cx, cy = L.CONCH
    place('conch', cx, cy, 0, 0, occupy=False)          # its base is flattened onto the sand (axis 68u up)
    for (xa, xb, r) in ((-260, -100, 70), (-100, 60, 140), (60, 160, 180)):
        K.add(box((cx + xa, cy - r * 0.92, 0), (cx + xb, cy + r * 0.92, 68 + r * 0.9), WCLIP))
    K.add(box((cx + 160, cy - 200, 0), (cx + 280, cy - 66, 230), WCLIP))
    K.add(box((cx + 160, cy + 66, 0), (cx + 280, cy + 200, 230), WCLIP))
    K.add(box((cx + 160, cy - 66, 136), (cx + 280, cy + 66, 230), WCLIP))
    K.occupy(cx - 270, cy - 210, cx + 290, cy + 210, 0, 270)
    K.secret((cx + 176, cy - 60, 0), (cx + 250, cy + 60, 72), dest=(0, -160, L.GROTTO_Z), angle=90, name='conch',
             approach='top')
    K.keep_clear(cx + 280, cy - 70, cx + 400, cy + 70, 0)


def grotto():
    """the Mermaid's Grotto: sealed room under the world, the giant clam with its pearl, treasure, teleporter back"""
    z = L.GROTTO_Z
    x0, y0, x1, y1 = -448, -384, 448, 384
    t = {'side': T('grotto'), 'top': T('sand_sea'), 'bot': T('grotto')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 448), (x1 + 32, y1 + 32, z + 480), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 448), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 448), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 448), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 448), t, detail=False))
    K.add(sign_box((-160, y1 - 4, z + 300), (160, y1, z + 380), T('sign_grotto'), 512, 128, back=CAULK, facing='s', edge=T('stick')))
    place('clam', 0, 40, z, 0, boxes=[((-196, -36, 0), (196, 236, 100))])
    for (x, y, nm) in ((-320, 250, 'rock3'), (320, 240, 'rock3'), (-330, -250, 'rock1'), (330, -250, 'rock1')):
        K.prop(ML.PLACE[nm], x, y, z, boxes=[((-50, -40, 0), (50, 40, 50))], search=120)
    K.item('item_padpower', -200, -120, z); K.item('item_revival', 200, -120, z); K.item('holdable_killerducks', 0, -200, z)
    K.item('item_armor_padshield', -260, -180, z); K.ammo('imperius', 260, -180, z)
    K.teleporter((-48, y0, z), (48, y0 + 48, z + 96), dest=(0, 1100, 4), angle=270, name='grotto_exit')
    K.light(0, 0, z + 380, 520, '0.6 0.85 1'); K.light(0, 180, z + 160, 260, '1 0.9 0.95')
    K.light(-300, -200, z + 200, 200, '0.5 0.9 0.8'); K.light(300, -200, z + 200, 200, '0.5 0.9 0.8')
    K.speaker(0, 0, z + 200, 'ambient/water_bubbling')


# ================================================================================================= beach props
def beach():
    # centre south: the spade stuck in the sand next to a lying bucket
    place('spade', 0, -620, 0, 90, boxes=[((-30, -66, 0), (30, 66, 110))], cyls=[(40, 0, 18, 110, 470)])
    K.prop(ML.PLACE['bucket_green_lying'], 0, -780, 0, boxes=[((-176, -100, 0), (6, 100, 200))], angle=200)
    # rock pool rim boulders (stand on the sea floor, cover only)
    for (x, y, nm, a) in ((520, -1300, 'rock2', 30), (-520, -1310, 'rock2', 150), (480, -1650, 'rock0', 0),
                          (-480, -1650, 'rock0', 180), (0, -1700, 'rock4', 90)):
        K.prop(ML.PLACE[nm], x, y, L.SEA_FLOOR, boxes=[((-70, -60, 0), (70, 60, 90))], angle=a, search=96)
    for s in SIDES:
        K.prop(ML.PLACE['beach_ball'], s * 760, -420, 0, boxes=[((-130, -130, 0), (130, 130, 290))])
        K.prop(ML.PLACE['bucket_yellow' if s > 0 else 'bucket_pink'], s * 1560, -560, 0, cyls=[(0, 0, 100, 0, 186)])
        K.prop(ML.PLACE['driftwood'], s * 2050, -640, 0, boxes=[((-440, -40, 0), (440, 40, 70))], angle=ang(s, 8))
        K.prop(ML.PLACE['crab'], s * 1050, -760, 0, boxes=[((-80, -110, 60), (90, 110, 160)), ((150, -110, 90), (270, 110, 150))],
               angle=ang(s, 160))
        K.prop(ML.PLACE['jandals_' + TEAM[s]], s * 360, -560, 0, boxes=[((-110, -110, 0), (110, 115, 14))], angle=ang(s, 20))
        K.prop(ML.PLACE['seagull'], s * 520, 870, 0, cyls=[(0, 0, 80, 0, 300)], angle=ang(s, 200))
        K.prop(ML.PLACE['seagull'], s * 2380, -880, 0, cyls=[(0, 0, 80, 0, 300)], angle=ang(s, 150))
        K.prop(ML.PLACE['beach_ball'], s * 1480, 1420, 0, boxes=[((-130, -130, 0), (130, 130, 290))])
        K.prop(ML.PLACE['bucket_pink' if s > 0 else 'bucket_yellow'], s * 2250, 1400, 0, cyls=[(0, 0, 100, 0, 186)])
        K.prop(ML.PLACE['driftwood'], s * 1900, 1630, 0, boxes=[((-440, -40, 0), (440, 40, 70))], angle=ang(s, -4))
        K.prop(ML.PLACE['rock1'], s * 2380, -1500, L.SEA_FLOOR, boxes=[((-70, -60, 0), (70, 60, 70))], angle=40)
        K.prop(ML.PLACE['rock3'], s * 1500, -1420, L.SEA_FLOOR, boxes=[((-110, -90, 0), (110, 90, 100))], angle=100)
        # small shells and starfish (no collision, < 20u)
        for (x, y, nm) in ((1250, -330, 'starfish'), (600, -820, 'scallop'), (1900, -800, 'starfish'), (300, -1000, 'scallop'),
                           (2200, 1200, 'scallop'), (1150, 1500, 'starfish'), (900, -1350, 'starfish')):
            z = 0 if y > L.BEACH_Y else (L.SEA_FLOOR if y < L.SHORE_Y else None)
            if z is None: continue
            p = K.near_free(s * x, y, 120, z, z + 20)
            if p: place(nm, p[0], p[1], z, (37 * x) % 360, occupy=False); K.occupy_r(p[0], p[1], 110, z, z + 20)
    # catalog: crushed drink cans and a lost soccer ball (catalog models, Padman scale 1.0)
    for (x, y, m, sc) in ((-640, -700, 'pad_tins/pad_coke_sd.md3', 1.0), (1700, -350, 'pad_tins/pad_pupsi_cr.md3', 1.0),
                          (-600, -250, 'pad_ball/pad_soccerball.md3', 1.6), (1200, 1650, 'pad_tins/pad_pupsi_sd.md3', 1.0),
                          (-1700, 1420, "pad_ducks/pad_duck.md3", 0.9), (2000, -1300, 'pad_ducks/pad_duck.md3', 0.9)):
        z = 0 if y > L.BEACH_Y else L.SEA_FLOOR
        K.catalog(m, x, y, z, scale=sc, lit=True)


def dunes():
    """dune sheets behind the clip (north, east, west) with marram grass, a lolly-stick dune fence along the clip"""
    def hn(x, y): return (y - Y1 - 30) * 0.55
    p, c = SM.dunes('dunes_n', HX0, HX1, Y1 + 16, HY1 - 8, hn, 5)
    place('dunes_n', c[0], c[1], 0, 0, occupy=False, lit=True)
    for s in SIDES:
        def he(x, y, s=s): return (s * x - X1 - 30) * 0.9 if y > L.BEACH_Y - 100 else -999
        nm = f'dunes_{TEAM[s]}'
        xa, xb = (X1 + 16, HX1 - 8) if s > 0 else (HX0 + 8, X0 - 16)
        p, c = SM.dunes(nm, xa, xb, L.BEACH_Y, Y1 + 16, he, 6 + s)
        place(nm, c[0], c[1], 0, 0, occupy=False, lit=True)
    rng = np.random.default_rng(3)
    for k in range(70):
        x = rng.uniform(HX0 + 260, HX1 - 260); y = rng.uniform(Y1 + 220, HY1 - 260)
        z = max(0.0, hn(x, y))
        place(f'marram{1 + k % 4}', x, y, z, rng.uniform(0, 360), lit=False, occupy=False)
    for s in SIDES:
        for k in range(18):
            x = s * rng.uniform(X1 + 170, HX1 - 170); y = rng.uniform(L.BEACH_Y + 300, Y1 - 100)
            z = max(0.0, (abs(x) - X1 - 30) * 0.9)
            place(f'marram{1 + k % 4}', x, y, z, rng.uniform(0, 360), lit=False, occupy=False)


# ================================================================================================= loot + spawns
def items():
    mx, my = L.MOUNT
    K.weapon('imperius', mx, my - 60, L.T2_H, marker='purple')
    K.weapon('splasher', 0, (L.POOL[1] + L.POOL[3]) / 2, L.POOL_FLOOR, marker='blue')
    for s in SIDES:
        kx, ky = s * L.KEEP[0], L.KEEP[1]
        K.weapon('balloony', kx - s * 110, ky + 140, L.KEEP_TOP, marker='orange')
        K.weapon('betty', s * L.BIN[0], L.BIN[1] + 40, L.BIN_H, marker='black')
        K.weapon('pumper', s * 330, my - 300 + 20, L.T1_H, marker='green')
        K.weapon('boaster', s * 2150, 120, 0, marker='orange')
        K.weapon('bubbleg', s * 880, 700, 0, marker='green')
        # ammo (blue side; mirrored)
        K.ammo('balloony', kx + s * 100, ky + 150, 0)                   # inside the keep
        K.ammo('balloony', s * 2352, 1002, L.TURRET_H)                  # back turret top
        K.ammo('betty', s * 1000, 1110, 0)
        K.ammo('betty', s * 2000, 1002, L.WALL_H)                       # north wall walk
        K.ammo('pumper', s * 1420, -1300, L.SEA_FLOOR)
        K.ammo('pumper', s * 1750, 1300, 0)
        K.ammo('boaster', s * 2352, 500, L.WALL_H)                      # east wall walk
        K.ammo('boaster', s * 1250, -560, 0)
        K.ammo('bubbleg', s * 1640, 1300, 0)
        K.ammo('bubbleg', s * 1750, -480, 0)
        K.ammo('splasher', s * 620, -1260, L.SEA_FLOOR)
        K.ammo('imperius', s * 2352, -102, L.TURRET_H)                  # back turret top (south)
        K.ammo('nipper', s * 1100, 1100, 0)
        K.item('item_armor_shard', s * 1448, -102, L.TURRET_H)
        K.item('item_armor_shard', s * 460, 600, L.T1_H)
    K.ammo('splasher', 0, my + L.T1_R + 120, 0)
    K.ammo('imperius', 0, -860, 0)                                     # on the beach in front of the shallows
    K.ammo('betty', 0, -400, 0)
    K.ammo('boaster', 60, my + 200, 0)                                 # in the tunnel
    K.ammo('pumper', -600, 1460, 0)
    K.ammo('bubbleg', 600, 1460, 0)
    K.ammo('nipper', 0, -820, 0)
    K.item('item_speedy', 0, -1640, L.SEA_FLOOR)
    K.item('holdable_floater', 0, -380, 0)
    K.item('item_jumper', -200, 1040, 4)


def spawns():
    for s in SIDES:
        team = TEAM[s]
        for (x, y, a) in ((1640, 140, 0), (1640, 760, 0), (2200, 160, 90), (2200, 740, 270)):
            K.spawn(s * x, y, 0, ang(s, a), cls=f'team_{team}player')
        for (x, y, a) in ((2500, 450, 180), (2500, -380, 135), (1900, -440, 90), (1900, 1300, 270), (2500, 1300, 225),
                          (1560, 450, 180)):
            K.spawn(s * x, y, 0, ang(s, a), cls=f'team_{team}spawn')
        for (x, y, z, a) in ((1150, -300, 0, 180), (600, -650, 0, 135), (440, 900, 0, 270), (1350, 1500, 0, 225),
                             (2200, 1500, 0, 200), (2150, 300, 0, 180), (900, 120, 0, 180), (2000, 1002, L.WALL_H, 180),
                             (2400, -700, 0, 160)):
            K.spawn(s * x, y, z, ang(s, a))
    K.ent('info_player_intermission', (0, -1500, 900), angles='12 90 0')


def lights():
    K.timer_sound(0, 600, 1000, 'animal/bird_gull', 'gulls', 14, 8)
    K.timer_sound(-1800, 1400, 600, 'animal/bird_gull', 'gulls2', 19, 9)


def shader():
    sky = SM.make_sky(OUT, NS)
    TX.write_shader(extra=[SH.sky(sky, sun=SM.SUN, sun_int=110, skylight=(60, 3), cloud=f'env/{NS}/clouds')],
                    arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    SM.make_textures()
    TX.kit_defaults(pad_rgb=(250, 200, 60))
    SM.make_all()                       # every MD3 (and its shaders) before the shader file is written
    bm = SM.bodyboard(460, L.BIN_H)
    shell(); ground(); bounds_clip()
    for s in SIDES: castle(s)
    mountain(); picnic(); grotto(); beach(); dunes()
    sea_water()
    items(); spawns(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
