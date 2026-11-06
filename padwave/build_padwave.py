#!/usr/bin/env python3
"""Neon Tide (wop_padwave) - a synthwave cruise liner's top decks at sunset, 1984.

    OUT=<dir> python3 build_padwave.py          (or: wopbuild.py padwave preview / check / all)

Four decks (14 interior, 15 pool deck, 16 promenade, 17 sky terraces) + the funnel crown. Mirrored bow (+y, red / hot
pink) onto stern (-y, blue / electric cyan) for CTL; port/starboard differ (Wave Rider port, Sky Pool starboard).
See README.md for the design sheet and layout.py for every coordinate the models share.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from wopmap import box, cyl, hull, carve, sub_rects, sign_box
import wopmap
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG, BOTCLIP
from woplib import models as ML, shaders as SH, texlib as TL, slides as SLD
from woplib.geom import ring_seg, helix, with_z, densify, ang_pt
import layout as L
import pw_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
K = MapKit(MAP, NS, LONG, tuple(INFO['bounds']),
           worldspawn={'_ambient': '22', '_color': '0.85 0.75 1', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
PM.setup(TX)
HALVES = (1, -1)                     # bow (red), stern (blue)
SLICK = T('slide_clip')


def Y(s, y): return s * y


def yr(s, a, b):
    """|y| range a..b of half s as (y0, y1) ascending"""
    return (a, b) if s > 0 else (-b, -a)


def bx(x0, x1, s, ya, yb, z0, z1, tex, detail=True):
    y0, y1 = yr(s, ya, yb)
    return box((x0, y0, z0), (x1, y1, z1), tex, detail)


def toward(s, inner, outer):
    """texture dict for a wall across the ship in half s: the face toward midships gets `inner`... `outer` the other"""
    mid, far = ('s', 'n') if s > 0 else ('n', 's')
    return {mid: inner, far: outer}


def dir_mid(s): return 's' if s > 0 else 'n'          # run direction toward midships
def dir_end(s): return 'n' if s > 0 else 's'          # run direction toward the ship's end


# ================================================================================================= structure
def shell():
    """structural sky hull: sea slab at the bottom (the synthwave sea), sky on the inner faces. The whole ship is
    detail floating inside, so the map compiles to a handful of portals."""
    x0, y0, x1, y1, z0, z1 = L.SKY
    sky = T('sky')
    K.add(box((x0 - 32, y0 - 32, z0 - 32), (x1 + 32, y1 + 32, z0 + 64), {'top': T('sea'), 'side': CAULK, 'bot': CAULK}, detail=False))
    K.add(box((x0 - 32, y0 - 32, z1), (x1 + 32, y1 + 32, z1 + 32), {'bot': sky, 'side': CAULK, 'top': CAULK}, detail=False))
    for mn, mx, f in (((x0 - 32, y0 - 32, z0 + 64), (x0, y1 + 32, z1), 'e'), ((x1, y0 - 32, z0 + 64), (x1 + 32, y1 + 32, z1), 'w'),
                      ((x0, y0 - 32, z0 + 64), (x1, y0, z1), 'n'), ((x0, y1, z0 + 64), (x1, y1 + 32, z1), 's')):
        t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t[f] = sky
        K.add(box(mn, mx, t, detail=False))


def ship_hull():
    """the hull skin MD3 (world coordinates, visual only: nobody can reach it) with the fore and aft decks"""
    K.custom(ML.PLACE['hull'], 0, 0, 0, occupy=False, _lightmapscale=4)


def clip_bounds():
    """player clip round the playable ship (bspc treats it as solid): no falling overboard anywhere"""
    zt = L.SKY[5]
    K.add(box((-L.HX - 16, -L.HY - 16, 0), (-L.HX, L.HY + 16, zt), CLIP))
    for s in HALVES:
        K.add(bx(L.HX, L.HX + 16, s, L.SP['hy'] + 32, L.HY + 16, 0, zt, CLIP))
        K.add(bx(-L.HX, L.HX, s, L.HY, L.HY + 16, 0, zt, CLIP))
        K.add(bx(L.HX, L.SP['x1'] + 32, s, L.SP['hy'] + 16, L.SP['hy'] + 32, L.SP['floor'] - 16, zt, CLIP))
    K.add(box((L.SP['x1'] + 16, -L.SP['hy'] - 16, L.SP['floor'] - 16), (L.SP['x1'] + 32, L.SP['hy'] + 16, zt), CLIP))


# ================================================================================================= deck 14 (interior)
def deck14():
    z = L.D14
    rooms = {1: T('carpet_disco'), -1: T('carpet_arcade')}
    ex0, ex1, ey0, ey1 = L.ELEV
    for s in HALVES:
        yy0, yy1 = yr(s, ey0, ey1)
        ry0, ry1 = yr(s, L.ATRIUM_Y, L.HY)
        for r in sub_rects((-L.HX, ry0, L.HX, ry1), [(ex0, yy0, ex1, yy1)]):
            K.add(box((r[0], r[1], z - 32), (r[2], r[3], z), {'top': rooms[s], 'side': CAULK, 'bot': CAULK}))
        K.add(box((ex0, yy0, z - 32), (ex1, yy1, z - 16), {'top': T('metal_dark'), 'side': T('metal_dark'), 'bot': CAULK}))   # plat pit
    K.add(box((-L.HX, -L.ATRIUM_Y, z - 32), (L.HX, L.ATRIUM_Y, z), {'top': T('marble'), 'side': CAULK, 'bot': CAULK}))
    # hull side walls and end walls
    for sx in (-1, 1):
        x0, x1 = (L.HX - L.WALL, L.HX) if sx > 0 else (-L.HX, -L.HX + L.WALL)
        inner = 'w' if sx > 0 else 'e'
        K.add(box((x0, -L.HY, z), (x1, L.HY, -L.SLAB), {inner: T('wall_navy'), 'side': CAULK, 'top': CAULK, 'bot': CAULK}))
    for s in HALVES:
        K.add(bx(-L.HX + L.WALL, L.HX - L.WALL, s, L.HY - L.WALL, L.HY, z, -L.SLAB, dict(toward(s, T('wall_navy'), CAULK), side=CAULK, top=CAULK, bot=CAULK)))
        # atrium walls with the centre doorway and the stair passages
        dx0, dx1 = L.DN_X
        gaps = sorted([(-L.DOOR_X, L.DOOR_X), (-dx1 - 16, -dx0 + 16), (dx0 - 16, dx1 + 16)])
        xs = [-L.HX + L.WALL]
        for a, b in gaps: xs += [a, b]
        xs.append(L.HX - L.WALL)
        wt = {'n': T('panel_violet'), 's': T('panel_violet'), 'side': T('wall_white'), 'top': CAULK, 'bot': CAULK}
        for a, b in zip(xs[0::2], xs[1::2]):
            K.add(bx(a, b, s, L.ATRIUM_Y, L.ATRIUM_Y + 32, z, -L.SLAB, wt))
        K.add(bx(-L.DOOR_X, L.DOOR_X, s, L.ATRIUM_Y, L.ATRIUM_Y + 32, z + 192, -L.SLAB, wt))       # lintel
        K.keep_clear(-L.DOOR_X, yr(s, L.ATRIUM_Y - 112, L.ATRIUM_Y + 144)[0], L.DOOR_X, yr(s, L.ATRIUM_Y - 112, L.ATRIUM_Y + 144)[1], z)
        K.route(f'atrium_door_{"b" if s > 0 else "s"}', (0, Y(s, L.ATRIUM_Y - 120), z), (0, Y(s, L.ATRIUM_Y + 160), z))
    K.reserve(((-L.HX, -L.HY, z - 32), (L.HX, L.HY, z)))


# ================================================================================================= deck 15 slab + pools
def pool_rect(s):
    x0, ya, x1, yb = L.POOL
    y0, y1 = yr(s, ya, yb)
    return (x0, y0, x1, y1)


def deck15():
    z = L.D15
    holes = []
    ex0, ex1, ey0, ey1 = L.ELEV
    for s in HALVES:
        p = pool_rect(s)
        holes.append((p[0] - 16, p[1] - 16, p[2] + 16, p[3] + 16))
        for sx in (-1, 1):
            a, b = (L.DN_X[0], L.DN_X[1]) if sx > 0 else (-L.DN_X[1], -L.DN_X[0])
            holes.append((a - 16, *yr(s, L.DN_Y[0], L.DN_Y[1])[:1], b + 16, yr(s, L.DN_Y[0], L.DN_Y[1])[1]))
        y0, y1 = yr(s, ey0 - 16, ey1 + 16)
        holes.append((ex0 - 16, y0, ex1 + 16, y1))
    for r in sub_rects((-L.HX, -L.HY, L.HX, L.HY), holes):
        cy = (r[1] + r[3]) / 2
        top = T('marble') if abs(cy) > L.B1_Y else T('teak')
        bot = T('wall_navy') if abs(cy) < L.ATRIUM_Y else T('panel_violet')
        t = {'top': top, 'bot': bot, 'side': T('coping')}
        K.add(box((r[0], r[1], z - L.SLAB), (r[2], r[3], z), t))
    # pools: basin walls round the hole, floor, steps at both short ends, laser-grid decal, water
    for s in HALVES:
        x0, y0, x1, y1 = pool_rect(s)
        tl = T('pool_pink') if s > 0 else T('pool_cyan')
        zf = L.POOL_FLOOR
        bt = {'top': T('coping'), 'side': tl, 'bot': T('panel_violet')}
        K.add(box((x0 - 16, y0 - 16, zf - 16), (x1 + 16, y1 + 16, zf), {'top': tl, 'side': tl, 'bot': T('panel_violet')}))
        K.add(box((x0 - 16, y0 - 16, zf), (x0, y1 + 16, 0), bt), box((x1, y0 - 16, zf), (x1 + 16, y1 + 16, 0), bt),
              box((x0, y0 - 16, zf), (x1, y0, 0), bt), box((x0, y1, zf), (x1, y1 + 16, 0), bt))
        sy0, sy1 = yr(s, L.POOL[1] + 16, L.POOL[1] + 480)          # steps on the midships half of each end (slides land
        steps = (K.stairs16(x0, sy0, x0 + 96, sy1, zf, L.WATER, 'w', {'top': T('coping'), 'side': tl})    # over the other half)
                 + K.stairs16(x1 - 96, sy0, x1, sy1, zf, L.WATER, 'e', {'top': T('coping'), 'side': tl}))
        K.add(box((x0 + 112, y0 + 16, zf), (x1 - 112, y1 - 16, zf + 1), T('laser_grid_p' if s > 0 else 'laser_grid')))
        K.water_box((x0, y0, zf), (x1, y1, L.WATER), T('water'), cutters=steps)
        K.reserve(((x0 - 16, y0 - 16, zf - 16), (x1 + 16, y1 + 16, 0)), pad=8)
        K.speaker(0, (y0 + y1) / 2, 48, 'ambient/water_rippling', volume=0.5)


# ================================================================================================= deck 15 -> 14 stairs
def down_stairs():
    for s in HALVES:
        for sx in (-1, 1):
            a, b = (L.DN_X[0], L.DN_X[1]) if sx > 0 else (-L.DN_X[1], -L.DN_X[0])
            y0, y1 = yr(s, L.DN_Y[0], L.DN_Y[1])
            K.stairs16(a, y0, b, y1, L.D14, L.D15, dir_mid(s), {'top': T('rubber_floor'), 'side': T('wall_white')},
                       route=f'down_{"b" if s > 0 else "s"}{"s" if sx > 0 else "p"}')
            K.reserve(((a, y0, L.D14), (b, y1, L.D15)), pad=4)
            # landing at the bottom (deck 14) and the top (deck 15) stay clear
            K.keep_clear(a, *yr(s, L.DN_Y[1], L.DN_Y[1] + 112)[:1], b, yr(s, L.DN_Y[1], L.DN_Y[1] + 112)[1], L.D14)
            K.keep_clear(a, *yr(s, L.DN_Y[0] - 112, L.DN_Y[0])[:1], b, yr(s, L.DN_Y[0] - 112, L.DN_Y[0])[1], L.D15)


# ================================================================================================= superstructure blocks
def blocks():
    for s in HALVES:
        red = s > 0
        out_w, in_w = T('super_wall'), T('panel_violet')
        # ---- block 1: deck 15 lounge (front wall with three doorways), its roof = deck 16 terrace
        fw = dict(toward(s, out_w, in_w), side=T('wall_white'), top=T('wall_white'), bot=T('wall_white'))
        doors = [(-560, -400), (-160, 160), (400, 560)]
        xs = [-L.HX]
        for a, b in doors: xs += [a, b]
        xs.append(L.HX)
        for a, b in zip(xs[0::2], xs[1::2]):
            K.add(bx(a, b, s, L.B1_Y, L.B1_Y + L.BW, 0, L.D16 - L.SLAB, fw))
        for a, b in doors:
            K.add(bx(a, b, s, L.B1_Y, L.B1_Y + L.BW, 176, L.D16 - L.SLAB, fw))
            K.keep_clear(a - 32, yr(s, L.B1_Y - 112, L.B1_Y + L.BW + 112)[0], b + 32, yr(s, L.B1_Y - 112, L.B1_Y + L.BW + 112)[1], 0)
            K.route(f'lounge_{"b" if s > 0 else "s"}{a}', ((a + b) / 2, Y(s, L.B1_Y - 120), 0), ((a + b) / 2, Y(s, L.B1_Y + 150), 0))
        # side walls (hull sides of the superstructure) and the end wall, deck 15 -> deck 17
        for sx in (-1, 1):
            x0, x1 = (L.HX - L.WALL, L.HX) if sx > 0 else (-L.HX, -L.HX + L.WALL)
            K.add(bx(x0, x1, s, L.B1_Y + L.BW, L.HY - L.WALL, 0, L.D16 - L.SLAB,
                     {('w' if sx > 0 else 'e'): in_w, 'side': out_w, 'top': out_w, 'bot': CAULK}))
            K.add(bx(x0, x1, s, L.B2_Y + L.BW, L.HY - L.WALL, L.D16, L.D17 - L.SLAB,
                     {('w' if sx > 0 else 'e'): in_w, 'side': out_w, 'top': out_w, 'bot': CAULK}))
        K.add(bx(-L.HX, L.HX, s, L.HY - L.WALL, L.HY, 0, L.D17 - L.SLAB, dict(toward(s, in_w, out_w), side=out_w, top=out_w, bot=CAULK)))
        # roofs with the elevator hole
        ex0, ex1, ey0, ey1 = L.ELEV
        for zt, ya, yend in ((L.D16, L.B1_Y, L.HY - L.WALL), (L.D17, L.B2_Y, L.HY)):
            y0, y1 = yr(s, ya, yend)
            hy0, hy1 = yr(s, ey0 - 16, ey1 + 16)
            for r in sub_rects((-L.HX, y0, L.HX, y1), [(ex0 - 16, hy0, ex1 + 16, hy1)]):
                K.add(box((r[0], r[1], zt - L.SLAB), (r[2], r[3], zt), {'top': T('teak'), 'bot': T('wall_white'), 'side': T('wall_white')}))
        # ---- block 2: deck 16 sky lounge, front wall with a centre door
        for a, b in ((-L.HX, -160), (160, L.HX)):
            K.add(bx(a, b, s, L.B2_Y, L.B2_Y + L.BW, L.D16, L.D17 - L.SLAB, fw))
        K.add(bx(-160, 160, s, L.B2_Y, L.B2_Y + L.BW, L.D16 + 176, L.D17 - L.SLAB, fw))
        K.keep_clear(-200, yr(s, L.B2_Y - 112, L.B2_Y + 144)[0], 200, yr(s, L.B2_Y - 112, L.B2_Y + 144)[1], L.D16)
        K.route(f'skylounge_{"b" if s > 0 else "s"}', (0, Y(s, L.B2_Y - 100), L.D16), (0, Y(s, L.B2_Y + 150), L.D16))
        # signs over the doors
        sy0, sy1 = yr(s, L.B1_Y - 4, L.B1_Y)
        K.add(sign_box((-200, sy0, 200), (200, sy1, 296), T('sign_lounge_r' if red else 'sign_lounge_b'), 512, 128,
                       back=T('wall_white'), facing=dir_mid(s), edge=T('metal_dark')))


# ================================================================================================= stairs deck 15 -> 16 -> 17
def up_stairs():
    for s in HALVES:
        tag = 'b' if s > 0 else 's'
        for sx in (-1, 1):
            a, b = (L.UP_X[0], L.UP_X[1]) if sx > 0 else (-L.UP_X[1], -L.UP_X[0])
            y0, y1 = yr(s, L.UP_Y[0], L.UP_Y[1])
            K.stairs16(a, y0, b, y1, L.D15, L.D16, dir_end(s), {'top': T('teak'), 'side': T('wall_white')},
                       route=f'up16_{tag}{"s" if sx > 0 else "p"}')
            K.reserve(((a, y0, 0), (b, y1, L.D16)), pad=4)
            K.keep_clear(a, *yr(s, L.UP_Y[0] - 112, L.UP_Y[0])[:1], b, yr(s, L.UP_Y[0] - 112, L.UP_Y[0])[1], 0)
            # terrace flights deck 16 -> 17, rising outward along the block 2 front wall
            t0, t1 = L.TER_STAIR_X
            a, b = (t0, t1) if sx > 0 else (-t1, -t0)
            y0, y1 = yr(s, *L.TER_STAIR_Y)
            K.stairs16(a, y0, b, y1, L.D16, L.D17, 'e' if sx > 0 else 'w', {'top': T('teak'), 'side': T('wall_white')})
            K.reserve(((a, y0, L.D16), (b, y1, L.D17)), pad=4)
            K.route(f'up17_{tag}{"s" if sx > 0 else "p"}', (sx * (t0 - 60), Y(s, sum(L.TER_STAIR_Y) / 2), L.D16),
                    (sx * (t1 - 16), Y(s, L.B2_Y + 120), L.D17))


# ================================================================================================= deck 16 promenade
def promenade():
    z = L.D16
    t = {'top': T('teak'), 'bot': T('wall_white'), 'side': T('wall_white')}
    K.add(box((L.PROM_X[0], -L.B1_Y, z - L.SLAB), (L.PROM_X[1], L.B1_Y, z), t))
    for s in HALVES:
        K.add(bx(-L.PROM_X[1], -L.PROM_X[0], s, L.PORT_GAP, L.B1_Y, z - L.SLAB, z, t))
    K.add(box((L.WALKWAY_X[0], -L.PORT_GAP, z - L.SLAB), (L.WALKWAY_X[1], L.PORT_GAP, z), t))
    K.route('walkway', (L.WALKWAY_X[0] + 40, -L.PORT_GAP - 200, z), (L.WALKWAY_X[0] + 40, L.PORT_GAP + 200, z))
    K.route('prom_s', (1000, -1400, z), (1000, 1400, z))


# ================================================================================================= funnel, crown, bridges, vortex
CROWN_WEDGES = []


def funnel():
    """collision: tapered wedge rings (doors bow + stern), crown deck of 16 wedges round the lift hole"""
    hw, dh = L.FUN_DOOR
    da = math.degrees(hw / L.FUN_R0)
    prof_z = [0, 200, 500, 800, L.CROWN - 16]
    prof_r = [L.FUN_R0, L.FUN_R0 - 6, L.FUN_R0 - 14, L.FUN_R0 - 22, L.FUN_R1]
    bands = [(0, dh), (dh, 500), (500, 800), (800, L.CROWN - 16)]
    for (z0, z1) in bands:
        ro = float(np.interp(z1, prof_z, prof_r)) - 4
        ri = ro - L.FUN_T + 4
        if z0 == 0:
            spans = [(90 + da, 270 - da), (270 + da, 450 - da)]
        else:
            spans = [(0, 360)]
        for (a0, a1) in spans:
            n = max(1, int(math.ceil((a1 - a0) / 22.5)))
            for k in range(n):
                b0, b1 = a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n
                K.add(ring_seg(0, 0, b0, b1, ri, ro, z0, z1, WCLIP))
    # the lift: pad in the funnel core up through the hole onto the crown (starboard side) - placed before the funnel
    # is reserved, so its launch spot is free
    K.jumppad(0, 0, 0, land=(140, 0, L.CROWN), apex=L.CROWN + 250, name='pad_funnel_lift',
              edges=[(L.CROWN_HOLE, 0, L.CROWN)])
    K.custom(ML.PLACE['funnel'], 0, 0, 0, occupy=False)
    K.occupy(-L.FUN_R0 - 8, -L.FUN_R0 - 8, L.FUN_R0 + 8, L.FUN_R0 + 8, 0, L.CROWN, why='funnel')
    for s in HALVES:
        K.keep_clear(-hw - 16, yr(s, L.FUN_R0 - 40, L.FUN_R0 + 112)[0], hw + 16, yr(s, L.FUN_R0 - 40, L.FUN_R0 + 112)[1], 0)
        K.route(f'funnel_door_{"b" if s > 0 else "s"}', (0, Y(s, L.FUN_R0 + 140), 0), (0, Y(s, 120), 0))
    # crown deck (caulk: the MD3 draws it) round the lift hole
    for k in range(16):
        w = ring_seg(0, 0, k * 22.5, (k + 1) * 22.5, L.CROWN_HOLE, L.CROWN_R, L.CROWN - 16, L.CROWN, WCLIP)
        K.add(w); CROWN_WEDGES.append(w)
    K.custom(ML.PLACE['crown'], 0, 0, L.CROWN, occupy=False)
    K.occupy(-L.CROWN_R, -L.CROWN_R, L.CROWN_R, L.CROWN_R, L.CROWN - 16, L.CROWN + 4, why='crown')
    K.speaker(0, 0, 400, 'machine/ventilation', volume=0.4)
    K.timer_sound(0, 0, L.CROWN - 100, 'machine/fog_horn', 'horn', 75, 20)


def bridges():
    """sky bridges from each deck 17 terrace up to the crown (13 deg, 192 wide), carved where they meet the crown"""
    for s in HALVES:
        ya, za = 270.0, float(L.CROWN)            # crown end
        yb, zb = float(L.B2_Y), float(L.D17)      # terrace end
        pts = []
        for x in (-L.BRIDGE_HW, L.BRIDGE_HW):
            for (y, zt) in ((ya, za), (yb, zb)):
                pts += [(x, s * y, zt), (x, s * y, zt - 24)]
        b = hull(pts, {'top': T('teak'), 'side': T('wall_white'), 'bot': T('wall_white')}, round_pts=False)
        for p in carve(b, CROWN_WEDGES):
            K.add(p)
        K.occupy(-L.BRIDGE_HW, min(s * ya, s * yb), L.BRIDGE_HW, max(s * ya, s * yb), zb - 24, za + 96, why='bridge')
        K.route(f'bridge_{"b" if s > 0 else "s"}', (0, Y(s, L.B2_Y + 120), L.D17), (0, Y(s, 160), L.CROWN))
        # neon edge trims (nonsolid decals along both sides of the bridge)
        for x in (-L.BRIDGE_HW, L.BRIDGE_HW - 4):
            tp = []
            for xx in (x, x + 4):
                for (y, zt) in ((ya + 40, za), (yb - 8, zb)):
                    tp += [(xx, s * y, zt + 2), (xx, s * y, zt + 6)]
            K.add(hull(tp, T('trim_pink' if s > 0 else 'trim_cyan'), round_pts=False))


VORTEX_PATH = []


def vortex():
    """Neon Vortex: one and a half clockwise turns round the funnel from the crown's launch deck to deck 15 (port)"""
    V = L.VORTEX
    R = V['R']
    # launch deck from the crown edge out to the helix (starboard), carved where it meets the crown
    ld = box((L.CROWN_R - 24, 40, L.CROWN - 16), (R + 48, 176, L.CROWN), {'top': T('teak'), 'side': T('wall_white'), 'bot': T('wall_white')})
    for p in carve(ld, CROWN_WEDGES): K.add(p)
    a0 = math.degrees(math.asin(34 / R))
    pts = helix(0, 0, R, a0, V['sweep'], L.CROWN, V['z1'], 72)
    # run-out on deck 15 (port, heading +y)
    end = np.array(pts[-1][:2]); d = np.array([math.sin(math.radians(a0 + V['sweep'])), -math.cos(math.radians(a0 + V['sweep']))])
    for k in (1, 2, 3):
        p = end + d * 64 * k
        pts.append((float(p[0]), float(p[1]), float(V['z1'])))
    VORTEX_PATH[:] = pts
    SLD.collision(K, pts, 44, 88, SLICK, roof=True)
    SLD.reserve_path(K, pts, 52, 104)
    K.custom(ML.PLACE['vortex'], 0, 0, 0, occupy=False)
    K.route('vortex_top', (L.CROWN_R + 40, 150, L.CROWN), (60, 0, L.CROWN))


# ================================================================================================= team slides
SLIDE_PATHS = {}


PAD_T = (300, 1530)            # pool deck -> terrace pad (both halves)


def floor_at(x, y):
    """walkable floor height under (x, y) for slide supports (None = no floor / not allowed)"""
    ay = abs(y)
    if math.hypot(x - PAD_T[0], ay - PAD_T[1]) < 130: return None
    x0, ya, x1, yb = L.POOL
    if x0 - 24 <= x <= x1 + 24 and ya - 24 <= ay <= yb + 24: return None
    if L.UP_X[0] - 40 <= abs(x) <= L.UP_X[1] + 40 and L.UP_Y[0] <= ay <= L.UP_Y[1]: return None
    if L.TER_STAIR_Y[0] - 40 <= ay <= L.TER_STAIR_Y[1] and L.TER_STAIR_X[0] <= abs(x) <= L.TER_STAIR_X[1]: return None
    if L.B1_Y - 40 <= ay <= L.B1_Y + 72: return None
    if L.B1_Y + 72 < ay < L.B2_Y - 40: return L.D16
    if ay < L.B1_Y - 40: return L.D15
    return None


def slide_pts(s, xy):
    """team slide centreline: flat start just off the deck 17 edge, slow first stretch (clears the terrace stairs),
    steeper toward the pool"""
    pts = with_z(xy, L.D17, 10, ease=lambda t: np.clip(t, 0, 1) ** 1.4)
    pts = [(x, y, float(z)) for (x, y, z) in pts]
    pts[0] = (pts[0][0], s * (L.B2_Y - 6), float(L.D17))
    return pts


def team_slides():
    for s in HALVES:
        for kind, xy in (('flume', L.flume_xy()), ('tube', L.tube_xy())):
            xy = [(p[0], s * p[1]) for p in xy]
            # flat start on the deck 17 edge, then the drop (eased so the start isn't a cliff)
            pts = slide_pts(s, xy)
            SLIDE_PATHS[(s, kind)] = pts
            hw, wh, roof = (44, 48, False) if kind == 'flume' else (40, 84, True)
            SLD.collision(K, pts[1:] if False else pts, hw, wh, SLICK, roof=roof)
            SLD.reserve_path(K, pts, hw + 8, 100)
            K.custom(ML.PLACE[f'{kind}_{"b" if s > 0 else "s"}'], 0, 0, 0, occupy=False)
            for (x, y, f, zt) in PM.SUPPORTS.get((s, kind), []):
                K.add(box((round(x) - 8, round(y) - 8, f), (round(x) + 8, round(y) + 8, round(zt)), WCLIP))
                K.occupy(x - 40, y - 16, x + 40, y + 16, f, zt, why='slide support')
            K.keep_clear(xy[0][0] - 60, *yr(s, L.B2_Y, L.B2_Y + 120)[:1], xy[0][0] + 60, yr(s, L.B2_Y, L.B2_Y + 120)[1], L.D17)


# ================================================================================================= Wave Rider (port)
def wave_rider():
    W = L.WR
    hy = W['hy']
    K.add(box((W['x0'], -hy, 0), (W['lip_x'], hy, W['lip_z']), {'top': T('rubber_floor'), 'side': T('wall_white'), 'bot': CAULK}))
    K.ramp(W['lip_x'], -hy, W['ramp_x'], hy, 0, W['lip_z'], 'w', {'top': T('wave_slick'), 'side': T('wall_white'), 'bot': CAULK})
    for s in HALVES:
        y0, y1 = yr(s, *W['stair_y'])
        K.stairs16(W['stair_x'][0], y0, W['stair_x'][1], y1, 0, W['lip_z'], dir_mid(s),
                   {'top': T('rubber_floor'), 'side': T('wall_white')},
                   route=f'wr_stair_{"b" if s > 0 else "s"}')
        K.reserve(((W['stair_x'][0], y0, 0), (W['stair_x'][1], y1, W['lip_z'])), pad=4)
    K.reserve(((W['x0'], -hy, 0), (W['ramp_x'], hy, W['lip_z'])), pad=8)
    # the current: pushes down the lower half of the ramp
    xa, xb = W['ramp_x'] - 200, W['ramp_x']
    za = W['lip_z'] * (W['ramp_x'] - xa) / (W['ramp_x'] - W['lip_x'])
    tp = [(x, y, z) for y in (-hy + 32, hy - 32) for (x, z) in ((xa, za + 1), (xb, 1), (xa, za + 120), (xb, 120))]
    K.M.ent('trigger_multiple', brushes=[hull(tp, TRIG, round_pts=False)], target='wr_current', wait=0.3)
    K.M.ent('target_push', (W['ramp_x'] - 100, 0, 100), targetname='wr_current', angles='-10 0 0', speed=260)
    K.custom(ML.PLACE['wave_sheet'], 0, 0, 0, lit=False, occupy=False)
    K.speaker((W['lip_x'] + W['ramp_x']) / 2, 0, 80, 'ambient/water_flowing', volume=0.6)
    # pad from the deck up onto the lip
    K.jumppad(-560, 0, 0, land=(-1096, 120, W['lip_z']), apex=W['lip_z'] + 64, name='pad_wave_lip',
              edges=[(W['lip_x'], 80, W['lip_z'])], ceiling=L.D16 - L.SLAB)


# ================================================================================================= Sky Pool (starboard)
def sky_pool():
    P = L.SP
    x0, x1, hy, zf = P['x0'], P['x1'], P['hy'], P['floor']
    g = T('glass')
    K.add(box((x0, -hy - 16, zf - 16), (x1 + 16, hy + 16, zf), g))
    K.add(box((x1, -hy - 16, zf), (x1 + 16, hy + 16, 48), g))
    for s in HALVES:
        K.add(bx(x0, x1, s, hy, hy + 16, zf, 48, g))
    steps = []
    for s in HALVES:
        y0, y1 = yr(s, *P['step_y'])
        steps += K.stairs16(P['step_x'][0], y0, P['step_x'][1], y1, zf, 0, dir_end(s),
                            {'top': T('coping'), 'side': T('pool_cyan')})
        K.keep_clear(P['step_x'][0] - 112, y0, P['step_x'][0], y1, 0)
    K.water_box((x0, -hy, zf), (x1, hy, P['water']), T('water'), cutters=steps)
    K.custom(ML.PLACE['sky_pool'], 0, 0, 0, lit=False, occupy=False)
    K.speaker((x0 + x1) / 2, 0, 0, 'ambient/water_rippling', volume=0.6)


# ================================================================================================= elevators
def elevators():
    ex0, ex1, ey0, ey1 = L.ELEV
    g = T('glass')
    for s in HALVES:
        y0, y1 = yr(s, ey0, ey1)
        K.elevator(ex0, y0, ex1, y1, L.D14, L.D17, T('metal_dark'), speed=200)
        top = L.D17 + 40
        # glass shaft: east/west walls full height, the midships wall opens at deck 14, the end wall full
        K.add(box((ex0 - 16, y0 - 16, L.D14), (ex0, y1 + 16, top), g), box((ex1, y0 - 16, L.D14), (ex1 + 16, y1 + 16, top), g))
        ym0, ym1 = (y0 - 16, y0) if s > 0 else (y1, y1 + 16)        # midships side
        ye0, ye1 = (y1, y1 + 16) if s > 0 else (y0 - 16, y0)
        K.add(box((ex0, ye0, L.D14), (ex1, ye1, top), g))
        K.add(box((ex0, ym0, L.D14 + 160), (ex1, ym1, L.D17), g))
        K.reserve(((ex0 - 16, y0 - 16, L.D14), (ex1 + 16, y1 + 16, top)), pad=8)
        K.keep_clear(ex0, min(ym0, ym0 - s * 112), ex1, max(ym1, ym0 - s * 112), L.D14)
        K.keep_clear(ex0, min(ym0, ym0 - s * 112), ex1, max(ym1, ym0 - s * 112), L.D17)


# ================================================================================================= railings
def rail(x0, y0, x1, y1, z, h=40, gaps=()):
    """low glass balustrade along a deck edge (thin along x or y) with gaps [(a, b)] along its length"""
    horiz = (x1 - x0) > (y1 - y0)
    lo, hi = (x0, x1) if horiz else (y0, y1)
    segs, p = [], lo
    for a, b in sorted(gaps):
        if a > p: segs.append((p, a))
        p = max(p, b)
    if p < hi: segs.append((p, hi))
    for a, b in segs:
        if b - a < 16: continue
        mn, mx = ((a, y0, z), (b, y1, z + h)) if horiz else ((x0, a, z), (x1, b, z + h))
        K.add(box(mn, mx, T('glass')))
        K.add(box((mn[0], mn[1], z + h), (mx[0], mx[1], z + h + 3), T('trim_violet')))


def railings():
    E = L.HX - 8
    for sx in (-1, 1):
        x0, x1 = (E, E + 4) if sx > 0 else (-E - 4, -E)
        # deck 15 outboard edge (between the blocks), gaps for the Wave Rider (port) and the Sky Pool (starboard)
        g = [(-L.SP['hy'] - 16, L.SP['hy'] + 16)] if sx > 0 else [(-L.WR['stair_y'][1] - 8, L.WR['stair_y'][1] + 8)]
        rail(x0, -L.B1_Y, x1, L.B1_Y, L.D15, gaps=g)
        rail(x0, -L.B2_Y, x1, L.B2_Y, L.D16, gaps=[(-L.PORT_GAP, L.PORT_GAP)] if sx < 0 else [])
        for s in HALVES:
            y0, y1 = yr(s, L.B2_Y, L.HY - 8)
            rail(x0, y0, x1, y1, L.D17)
    for s in HALVES:
        # deck 17 front edge: gaps at the bridge, both slide starts, both stair tops and the pad landings
        yy = (L.B2_Y, L.B2_Y + 4) if s > 0 else (-L.B2_Y - 4, -L.B2_Y)
        g = [(-L.BRIDGE_HW - 8, L.BRIDGE_HW + 8), (-L.SLIDE_X - 64, -L.SLIDE_X + 64), (L.SLIDE_X - 64, L.SLIDE_X + 64), (-480, -360),
             (-L.TER_STAIR_X[1] - 24, -L.TER_STAIR_X[1] + 48), (L.TER_STAIR_X[1] - 48, L.TER_STAIR_X[1] + 24)]
        rail(-E, yy[0], E, yy[1], L.D17, gaps=g)
        ye = (L.HY - 8, L.HY - 4) if s > 0 else (-L.HY + 4, -L.HY + 8)
        rail(-E, ye[0], E, ye[1], L.D17)
        # terrace front edge (deck 16, over the pool deck): gaps at the up-flight tops and the promenade junctions
        yy = (L.B1_Y, L.B1_Y + 4) if s > 0 else (-L.B1_Y - 4, -L.B1_Y)
        g = [(-L.UP_X[1] - 24, -L.UP_X[0] + 24), (L.UP_X[0] - 24, L.UP_X[1] + 24), (-L.HX, -L.PROM_X[0] + 8),
             (L.PROM_X[0] - 8, L.HX), (PAD_T[0] - 60, PAD_T[0] + 60)]
        rail(-L.PROM_X[0], yy[0], L.PROM_X[0], yy[1], L.D16, gaps=g)


# ================================================================================================= props + rooms
def deck15_props():
    for s in HALVES:
        cush = 'cushion_p' if s > 0 else 'cushion_c'
        # loungers along both pool sides
        for sx in (-1, 1):
            for yy in (860, 980, 1100, 1220, 1340):
                K.prop(ML.PLACE[f'lounger_{cush}'], sx * 560, Y(s, yy), 0, boxes=[((-14, -38, 0), (14, 36, 30))],
                       angle=90 if sx > 0 else 270, search=48)
        # cabanas under the promenade (starboard) and beside the Wave Rider stairs (port)
        for (x, yy) in ((1000, 1420), (-1000, 1420)):
            K.prop(ML.PLACE[f'cabana_{"p" if s > 0 else "c"}'], x, Y(s, yy), 0, boxes=PM.CABANA_BOX, cyls=PM.CABANA_CYL, angle=0, search=96)
        K.prop(ML.PLACE['flamingo'], -300, Y(s, 600), 0, boxes=[((-60, -60, 0), (60, 60, 30)), ((-12, 62, 0), (12, 84, 120))],
               angle=0 if s > 0 else 180, search=120)
        K.prop(ML.PLACE['donut_float'], 340, Y(s, 600), 0, boxes=[((-52, -52, 0), (52, 52, 30))], angle=0, search=120)
        for (x, yy) in ((-760, 560), (760, 560), (-420, 1560), (420, 1560)):
            K.prop(ML.PLACE['palm_p'], x, Y(s, yy), 0, cyls=PM.PALM_CYL, angle=0, search=96)


def lounges():
    for s in HALVES:
        red = s > 0
        # deck 15 lounge: long bar along the end wall, stools, palms
        yb = Y(s, L.HY - L.WALL - 60)
        K.prop(ML.PLACE['bar_lounge'], 0, yb, 0, boxes=[((-322, -34, 0), (322, 38, 70))], angle=180 if s > 0 else 0, search=24)
        for x in range(-260, 261, 104):
            K.prop(ML.PLACE['stool'], x, Y(s, L.HY - L.WALL - 150), 0, cyls=[(0, 0, 14, 0, 46)], angle=0, search=24)
        for (x, yy) in ((-880, 1820), (880, 1820), (-880, 2160), (500, 2160)):
            K.prop(ML.PLACE['palm_p'], x, Y(s, yy), 0, cyls=PM.PALM_CYL, angle=0, search=80)
        K.light(0, Y(s, 1980), 300, 500, '1 0.4 0.75' if red else '0.4 0.9 1')
        K.light(-700, Y(s, 1980), 300, 450, '0.7 0.4 1'); K.light(700, Y(s, 1980), 300, 450, '0.7 0.4 1')
        # deck 16 sky lounge: cabanas + loungers
        for x in (-600, 600):
            K.prop(ML.PLACE[f'cabana_{"p" if red else "c"}'], x, Y(s, 2150), L.D16, boxes=PM.CABANA_BOX, cyls=PM.CABANA_CYL, angle=0, search=80)
        K.light(0, Y(s, 2150), L.D16 + 280, 450, '1 0.5 0.8' if red else '0.5 0.9 1')
        # deck 17 sky terrace: loungers, palms
        cush = 'cushion_p' if red else 'cushion_c'
        for x in (-1000, -900, 940, 1040):
            K.prop(ML.PLACE[f'lounger_{cush}'], x, Y(s, 2200), L.D17, boxes=[((-14, -38, 0), (14, 36, 30))], angle=0 if red else 180, search=48)
        for x in (-320, 320):
            K.prop(ML.PLACE['palm_p'], x, Y(s, 2240), L.D17, cyls=PM.PALM_CYL, angle=0, search=64)


def lifeboats():
    for s in HALVES:
        for sx in (-1, 1):
            x, y = sx * 1080, Y(s, 1080)
            K.custom(ML.PLACE['lifeboat'], x, y, L.D16, angle=0 if s > 0 else 180, boxes=PM.LIFEBOAT_BOXES)
            K.keep_clear(x - 60, *yr(s, 1080 - 150 - 112, 1080 - 150)[:1], x + 60, yr(s, 1080 - 150 - 112, 1080 - 150)[1], L.D16)
            K.route(f'lifeboat_{"b" if s > 0 else "s"}{"s" if sx > 0 else "p"}', (x, Y(s, 1080 - 280), L.D16), (x, Y(s, 1080 + 20), L.D16 + 16))


def interiors():
    z = L.D14
    # bow: Starlight Disco
    s = 1
    for i in range(6):
        for j in range(6):
            x0 = -384 + i * 128; y0 = 1220 + j * 96
            K.add(box((x0 + 4, y0 + 4, z), (x0 + 124, y0 + 92, z + 1), T(f'dance{(i + j) % 4}')))
    K.custom(ML.PLACE['dj_booth'], 0, 2150, z, angle=180, boxes=PM.DJ_BOX)
    for x in (-300, 300):
        K.custom(ML.PLACE['speaker_stack'], x, 2170, z, angle=180, boxes=PM.SPK_BOX)
    K.custom(ML.PLACE['speaker_stack'], -900, 1950, z, angle=150, boxes=PM.SPK_BOX)
    K.custom(ML.PLACE['speaker_stack'], 900, 1950, z, angle=210, boxes=PM.SPK_BOX)
    K.rotating_model2(ML.IQM['mirrorball'], (0, 1500, -120), 20)
    K.add(cyl(0, 1500, 3, -96, -L.SLAB, T('metal_dark'), 6))
    K.light(0, 1500, -160, 500, '1 0.4 0.9'); K.light(-500, 1200, -200, 350, '0.4 0.6 1'); K.light(500, 1200, -200, 350, '1 0.3 0.6')
    K.light(0, 2000, -150, 400, '1 0.5 0.8')
    K.add(sign_box((-220, L.ATRIUM_Y + 32, -224), (220, L.ATRIUM_Y + 36, -128), T('sign_disco'), 512, 128, back=T('panel_violet'), facing='n', edge=T('metal_dark')))
    # stern: Pixel Arcade - rows of cabinets, a prize counter where the DJ booth is
    K.custom(ML.PLACE['bar_c'], 0, -2150, z, angle=0, boxes=[((-194, -34, 0), (194, 38, 70))])
    k = 0
    for row_y in (-1250, -1500, -1750):
        for x in (-500, -380, 380, 500):
            K.custom(ML.PLACE[f'arcade{k % 4}'], x, row_y, z, angle=0, boxes=PM.CAB_BOX); k += 1
    for x in (-900, 900):
        K.custom(ML.PLACE['speaker_stack'], x, -1950, z, angle=-30 if x < 0 else 30, boxes=PM.SPK_BOX)
    for x in (-300, 300):
        K.custom(ML.PLACE['arcade3'], x, -2170, z, angle=0, boxes=PM.CAB_BOX)
    K.light(0, -1500, -150, 450, '0.4 0.9 1'); K.light(-500, -1900, -200, 350, '1 0.6 0.3'); K.light(500, -1200, -200, 350, '0.7 0.4 1')
    K.add(sign_box((-220, -L.ATRIUM_Y - 36, -224), (220, -L.ATRIUM_Y - 32, -128), T('sign_arcade'), 512, 128, back=T('panel_violet'), facing='s', edge=T('metal_dark')))
    # atrium: golden statue on a plinth, the video shop sign, health stations
    K.add(cyl(0, 0, 112, z, z + 16, {'top': T('marble'), 'side': T('trim_violet'), 'bot': CAULK}, 16))
    K.catalog('ente/padstatue_gold.md3', 0, 0, z + 16, scale=0.8, angle=90, lit=True, nudge=False)
    K.add(sign_box((-L.HX + L.WALL, -260, -260), (-L.HX + L.WALL + 4, 260, -140), T('sign_vhs'), 512, 128,
                   back=T('wall_navy'), facing='e', edge=T('metal_dark')))
    for x in (-560, 560):
        K.station(x, 400 if x < 0 else -400, z, ang=90)
    K.light(0, 0, -120, 500, '1 0.9 0.8'); K.light(-700, 0, -200, 350, '0.7 0.4 1'); K.light(700, 0, -200, 350, '0.7 0.4 1')


# ================================================================================================= secret: the Bonus Stage
BONUS = dict(x0=-512, x1=512, y0=-384, y1=384, z0=L.SKY[4] - 1024, h=448)


def bonus_stage():
    b = BONUS
    z = b['z0']
    t = {'side': T('pixel_wall'), 'top': T('pixel_floor'), 'bot': T('pixel_wall')}
    K.add(box((b['x0'] - 32, b['y0'] - 32, z - 32), (b['x1'] + 32, b['y1'] + 32, z), t, detail=False),
          box((b['x0'] - 32, b['y0'] - 32, z + b['h']), (b['x1'] + 32, b['y1'] + 32, z + b['h'] + 32), t, detail=False),
          box((b['x0'] - 32, b['y0'] - 32, z), (b['x0'], b['y1'] + 32, z + b['h']), t, detail=False),
          box((b['x1'], b['y0'] - 32, z), (b['x1'] + 32, b['y1'] + 32, z + b['h']), t, detail=False),
          box((b['x0'], b['y0'] - 32, z), (b['x1'], b['y0'], z + b['h']), t, detail=False),
          box((b['x0'], b['y1'], z), (b['x1'], b['y1'] + 32, z + b['h']), t, detail=False))
    # blocky platforms on 16u steps
    for (x0, y0, h) in ((-400, -250, 16), (-400, -150, 32), (-300, -150, 48), (200, 100, 16), (300, 100, 32), (300, 200, 48)):
        K.add(box((x0, y0, z), (x0 + 96, y0 + 96, z + h), {'top': T('pixel_block'), 'side': T('pixel_block'), 'bot': CAULK}))
    K.item('item_padpower', -350, -100, z + 48); K.item('item_revival', 350, 250, z + 48)
    K.item('holdable_killerducks', 0, -200, z); K.item('item_armor_padshield', 0, 200, z)
    K.teleporter((-48, b['y1'] - 96, z + 4), (48, b['y1'] - 32, z + 96), dest=(0, 440, L.D14), angle=90, name='bonus_exit')
    K.add(box((-56, b['y1'] - 104, z), (56, b['y1'] - 24, z + 4), {'top': T('jumppad'), 'side': T('rubber'), 'bot': CAULK}))
    for (x, y) in ((-300, 0), (300, 0), (0, 0)):
        K.light(x, y, z + 360, 380, '1 0.85 1')
    K.speaker(0, 0, z + 200, 'machine/electric_sizzle', volume=0.3)
    # entries: the PADMAN '84 cabinet screen (arcade) and the DJ stack's lower woofer (disco)
    K.custom(ML.PLACE['arcade_padman'], 0, -1250, L.D14, angle=0, boxes=[((-24, -20, 0), (24, 0, 118)), ((-24, 0, 0), (24, 20, 56)), ((-24, 0, 104), (24, 20, 118))])
    K.secret((-22, -1250 + 2, L.D14 + 58), (22, -1250 + 18, L.D14 + 102), dest=(0, 0, z), angle=90, name='secret_cab',
             approach='n')
    K.secret((300 - 40, 2170 - 50, L.D14), (300 + 40, 2170 - 34, L.D14 + 96), dest=(-120, 0, z), angle=90, name='secret_woofer',
             approach='s')


# ================================================================================================= items, spawns, pads
def items():
    W = L.WR
    K.weapon('imperius', -180, 0, L.CROWN, marker='purple')
    K.weapon('splasher', 1540, 0, L.SP['floor'], marker='blue')
    K.weapon('pumper', -1096, -60, W['lip_z'], marker='green')
    for s in HALVES:
        K.weapon('balloony', -L.SLIDE_X, Y(s, 2130), L.D17, marker='orange')
        K.weapon('betty', -1080, Y(s, 1080), L.D16 + 16, marker='black')
        K.weapon('boaster', 0, Y(s, 2245), L.D14, marker='orange')
        K.weapon('bubbleg', -220, Y(s, 1590), 0, marker='green')
    A = {'imperius': [(0, 170, L.CROWN), (400, 560, L.D14), (-1000, 1900, 0), (1000, -1900, 0)],
         'splasher': [(1280, 304, -64), (1280, -304, -64), (1000, 0, L.D16), (-200, 0, L.D14)],
         'pumper': [(-1096, 60, W['lip_z']), (-800, 0, L.D16), (900, 1750, L.D16), (-900, -1750, L.D16)],
         'balloony': [(L.SLIDE_X, 2130, L.D17), (L.SLIDE_X, -2130, L.D17), (0, 1100, L.D14), (0, -1100, L.D14), (-600, 0, L.D14)],
         'betty': [(1080, 1080, L.D16 + 16), (1080, -1080, L.D16 + 16), (-560, 1900, 0), (560, -1900, 0)],
         'boaster': [(-800, 1500, L.D14), (800, -1500, L.D14), (0, 700, 0), (0, -700, 0)],
         'bubbleg': [(-600, 1580, 0), (600, -1580, 0), (-760, 0, 0), (760, 1700, L.D16), (-760, -1700, L.D16)]}
    for w, spots in A.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((300, 0, L.D14), (-300, 0, L.D14), (0, 1700, L.D16), (0, -1700, L.D16)):
        K.ammo('nipper', x, y, z)
    K.item('item_speedy', 1000, 0, L.D16)
    K.item('item_jumper', -700, 360, 0)
    K.item('holdable_floater', -840, 0, L.D16)
    for s in HALVES:
        K.item('item_armor_padshield', 500, Y(s, 2160), L.D17)
        for yy in (600, 1400):
            K.item('item_armor_shard', 1000, Y(s, yy), L.D16)
            K.item('item_armor_shard', -1000, Y(s, yy + 100), L.D16)
    # CTL
    K.ent('team_CTL_redlolly', (0, 2150, L.D17 + 16))
    K.ent('team_CTL_bluelolly', (0, -2150, L.D17 + 16))
    K.occupy_r(0, 2150, 48, L.D17, L.D17 + 96); K.occupy_r(0, -2150, 48, L.D17, L.D17 + 96)


def pads():
    for s in HALVES:
        tag = 'b' if s > 0 else 's'
        # pool deck -> terrace (deck 16) beside the up-flights
        K.jumppad(PAD_T[0], Y(s, PAD_T[1]), 0, land=(PAD_T[0], Y(s, 1760), L.D16), apex=L.D16 + 170, name=f'pad_terrace_{tag}',
                  edges=[(PAD_T[0], Y(s, L.B1_Y), L.D16)])
        # terrace -> sky terrace (deck 17)
        K.jumppad(-420, Y(s, 1720), L.D16, land=(-420, Y(s, 2110), L.D17), apex=L.D17 + 160, name=f'pad_sky_{tag}',
                  edges=[(-420, Y(s, L.B2_Y), L.D17)])


def spawns():
    sp = [(0, 400, L.D14, 90), (-600, -300, L.D14, 0), (600, 300, L.D14, 180),
          (-500, 1600, L.D14, 270), (500, -1600, L.D14, 90),
          (-860, 700, 0, 90), (860, -700, 0, 270), (0, 520, 0, 90), (0, -520, 0, 270),
          (-300, 1960, 0, 270), (300, -1960, 0, 90),
          (-1000, 800, L.D16, 270), (1000, -800, L.D16, 90),
          (-600, 1900, L.D16, 0), (600, -1900, L.D16, 180),
          (-900, 2100, L.D17, 0), (900, -2100, L.D17, 180), (-700, 0, 0, 0), (1000, 300, 0, 180)]
    for (x, y, z, a) in sp:
        K.spawn(x, y, z, a)
    for s in HALVES:
        cls = 'team_redspawn' if s > 0 else 'team_bluespawn'
        for (x, yy, z) in ((-300, 1900, 0), (300, 2050, 0), (-700, 2160, 0), (0, 2150, L.D16), (-300, 2200, L.D16), (300, 2200, L.D16)):
            K.spawn(x, Y(s, yy), z, 270 if s > 0 else 90, cls=cls)


def lights_and_sound():
    # deck lights: coloured festoons over the pool decks, white-ish spots elsewhere
    for s in HALVES:
        col = '1 0.45 0.8' if s > 0 else '0.45 0.9 1'
        for x in (-600, 0, 600):
            for yy in (800, 1250):
                K.light(x, Y(s, yy), 340, 650, col)
        for x in (-700, 0, 700):
            K.light(x, Y(s, 1820), L.D16 + 260, 450, col)
            K.light(x, Y(s, 2150), L.D17 + 280, 500, col)
        for yy in (500, 1000, 1500):
            K.light(-1000, Y(s, yy), L.D16 + 220, 380, '0.75 0.55 1'); K.light(1000, Y(s, yy), L.D16 + 220, 380, '0.75 0.55 1')
            K.light(-940, Y(s, yy), 260, 300, '0.75 0.55 1'); K.light(940, Y(s, yy), 260, 300, '0.75 0.55 1')
        K.light(0, Y(s, 1100), L.D14 + 250, 450, '0.8 0.5 1')
        K.speaker(0, Y(s, 2150), L.D17 + 120, 'ambient/wind_night', volume=0.4)
        K.speaker(0, Y(s, 1600), -200, 'machine/aircon', volume=0.3)
    K.light(0, 0, L.CROWN + 200, 600, '1 0.6 0.9')
    K.light(600, 0, 200, 450, '0.7 0.5 1'); K.light(-600, 0, 200, 450, '0.7 0.5 1')
    K.light(L.SP['x0'] + 260, 0, -60, 400, '0.3 0.9 1')
    K.trigger_sound((-100, -100, L.CROWN + 8), (100, 100, L.CROWN + 72), 'human/applause', 'crown_applause', wait=10)
    K.speaker(0, 1600, -200, 'machine/electric_sizzle', volume=0.2)
    K.speaker(0, -1600, -200, 'machine/fan_pc', volume=0.3)


# ================================================================================================= textures + models
def textures():
    PM.make_brush_textures()
    PM.make_sky(OUT)
    TX.add('pixel_wall', pixel_tex((40, 30, 120), (80, 60, 200)), check_tile=False)
    TX.add('pixel_floor', pixel_tex((30, 120, 40), (60, 200, 70)), check_tile=False)
    TX.add('pixel_block', pixel_tex((200, 110, 40), (250, 170, 60)), check_tile=False)


def pixel_tex(c1, c2, n=128, cells=8):
    x, y = ML.xy(n)
    cx, cy = np.floor(x * cells), np.floor(y * cells)
    edge = ((x * cells) % 1 > 0.9) | ((y * cells) % 1 > 0.9)
    chk = ((cx + cy) % 2)[..., None]
    c = ML.lerp(ML.C(c1), ML.C(c2), chk)
    return np.where(edge[..., None], ML.C((10, 10, 20)), c)


def models():
    PM.make_all()
    # the hull (world coordinates): plan outline at the sheer line, counter-clockwise
    hx = L.HX + 8
    outline = [(-hx, -2700), (-hx + 180, -2860), (hx - 180, -2860), (hx, -2700), (hx, 2304), (hx - 120, 2900), (hx - 520, 3420),
               (0, 3800), (-hx + 520, 3420), (-hx + 120, 2900), (-hx, 2304)]
    X = PM.hull_model(outline, skin_holes=lambda x, y, z: x > 0 and abs(y) < L.SP['hy'] + 24 and z > L.SP['floor'] - 16)
    for s in HALVES: PM.hull_names(X, s)
    # fore and aft decks outside the playable area (visual: teak with a white bulwark)
    fd = X.mesh(PM.MAT['teak'])
    from meshlib import prism as mprism
    mprism(fd, [(-hx + 12, 2304), (hx - 12, 2304), (hx - 130, 2890), (hx - 528, 3404), (0, 3780), (-hx + 528, 3404), (-hx + 130, 2890)],
           -24, 0, tile=128, bot=False)
    mprism(fd, [(-hx + 12, -2304), (-hx + 12, -2696), (-hx + 186, -2846), (hx - 186, -2846), (hx - 12, -2696), (hx - 12, -2304)], -24, 0, tile=128, bot=False)
    ML.save('hull', X)
    ML.save('sky_pool', PM.sky_pool_glass())
    # Wave Rider water sheet (thin additive flow over the ramp)
    X = ML.Model()
    W = L.WR
    X.mesh(PM.MAT['water_flow']).quad((W['ramp_x'], -W['hy'] + 8, 2), (W['ramp_x'], W['hy'] - 8, 2),
                                      (W['lip_x'], W['hy'] - 8, W['lip_z'] + 2), (W['lip_x'], -W['hy'] + 8, W['lip_z'] + 2), tile=128)
    ML.save('wave_sheet', X)
    # the Padman '84 arcade cabinet (secret entry): a deeper screen recess
    PM.arcade_cabinet(1)
    ML.PLACE['arcade_padman'] = ML.PLACE['arcade1']
    # slides (world coordinates)
    vx = ML.Model()
    V = L.VORTEX
    a0 = math.degrees(math.asin(34 / V['R']))
    pts = helix(0, 0, V['R'], a0, V['sweep'], L.CROWN, V['z1'], 72)
    end = np.array(pts[-1][:2]); d = np.array([math.sin(math.radians(a0 + V['sweep'])), -math.cos(math.radians(a0 + V['sweep']))])
    for k in (1, 2, 3):
        p = end + d * 64 * k
        pts.append((float(p[0]), float(p[1]), float(V['z1'])))
    SLD.tube_slide(vx, pts, 46, PM.MAT['tube_body'], PM.MAT['slide_in_c'], bands=PM.MAT['pink_g'], water=PM.MAT['water_flow'], zc=44)
    PM.SUPPORTS = {}
    ML.save('vortex', vx)
    for s in HALVES:
        for kind, xy in (('flume', L.flume_xy()), ('tube', L.tube_xy())):
            xy = [(p[0], s * p[1]) for p in xy]
            pts = slide_pts(s, xy)
            X = ML.Model()
            if kind == 'flume':
                P = SLD.flume(X, pts, PM.MAT['flume_body'], PM.MAT['slide_in_p' if s > 0 else 'slide_in_c'],
                              rim=PM.MAT['pink_g' if s > 0 else 'cyan_g'], water=PM.MAT['water_flow'], r=46, lip=44)
                under = 12
            else:
                P = SLD.tube_slide(X, pts, 44, PM.MAT['tube_body'], PM.MAT['slide_in_c'], bands=PM.MAT['pink_g' if s > 0 else 'cyan_g'],
                                   water=PM.MAT['water_flow'], zc=42)
                under = 6
            PM.SUPPORTS[(s, kind)] = SLD.supports(X, [tuple(p) for p in P], PM.MAT['chrome'], floor_at, every=6, zmin=120, under=under + 16)
            ML.save(f'{kind}_{"b" if s > 0 else "s"}', X)
    # mirror ball (rotating, IQM so it can be a model2)
    X = ML.Model()
    from meshlib import sphere
    sphere(X.mesh(ML.S('mball_m', 'dyn')), (0, 0, 0), 28, nu=20, nv=12)
    ML.T('mball_m', TL.checker((230, 230, 240), (120, 120, 140), 16, grout=(40, 40, 50), grout_w=0.08))
    ML.save_iqm('mirrorball', X)


def shader():
    TX.write_shader(extra=[SH.sky('env/padwave/sunset', sun=(PM.SUN_DIR[0], 8), sun_rgb=(1, 0.55, 0.65), sun_int=70,
                                  skylight=(45, 3), editor='env/padwave/sunset_bk')],
                    arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    textures()
    models()                                     # every MD3 (and its shaders) BEFORE the shader file is written
    shell(); ship_hull(); clip_bounds()
    deck14(); deck15(); down_stairs(); blocks(); up_stairs(); promenade()
    funnel(); bridges(); vortex(); wave_rider(); sky_pool(); elevators(); team_slides()
    railings()
    bonus_stage(); interiors(); lifeboats()
    items(); pads(); spawns()
    deck15_props(); lounges()
    lights_and_sound()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
