#!/usr/bin/env python3
"""Mini Golf Madness (wop_padminigolf) - FFA in a sunny putt-putt park at toy scale (~4u per cm).

    OUT=<dir> python3 build_padminigolf.py        (or: wopbuild.py padminigolf gen / preview / check / all)

Six holes (felt lanes, painted rails you hop over, tee mats, cups with numbered flags) run between the landmarks:
  windmill    walk through the tunnel in its base (hole 1), 16u stairs + a pad onto the stage under the turning sails,
              a pad from the stage to the lookout on the cap (Imperius)
  lighthouse  on an island in the lake: footbridge, keeper's room, a pad onto the gallery (Betty), the lamp room
  volcano     stairs onto the terrace, pads to the crater rim (Balloony), lava in the crater
  clown       walk in through the mouth and out the back (hole 4), a pad onto the top hat (Pumper)
  clubhouse   counter, putter racks, scoreboard (Boaster), stairs to the roof terrace
  secret      the 19th hole behind the windmill: drop into the cup -> the Lost Ball Cavern -> teleporter back
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
import mg_models as MM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = L.BOUNDS
HX0, HY0, HX1, HY1 = L.HULL
K = MapKit(MAP, NS, LONG, L.BOUNDS, worldspawn={'_ambient': '16', '_color': '1 0.98 0.92', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)
MM.init(TX)


def tx(top, side=None, bot=CAULK):
    return {'top': T(top), 'side': T(side or top), 'bot': bot}


def frustum(cx, cy, r0, r1, z0, z1, n=16, tex=WCLIP, phase=None):
    p0 = ngon(cx, cy, r0, n, phase); p1 = ngon(cx, cy, r1, n, phase)
    return hull([(x, y, z0) for x, y in p0] + [(x, y, z1) for x, y in p1], tex)


def ring_wedges(cx, cy, rin, rout, z0, z1, n=16, skip=None, tex=WCLIP, phase=0.0):
    """ring of n convex wedges; rin/rout = (r at z0, r at z1) or a number; skip(mid_angle_rad) -> True leaves a gap"""
    rin = rin if isinstance(rin, tuple) else (rin, rin)
    rout = rout if isinstance(rout, tuple) else (rout, rout)
    out = []
    for k in range(n):
        a0 = math.radians(phase) + 2 * math.pi * k / n; a1 = a0 + 2 * math.pi / n
        if skip and skip((a0 + a1) / 2): continue
        P = [(cx + r * math.cos(a), cy + r * math.sin(a), z) for a in (a0, a1)
             for (z, r) in ((z0, rin[0]), (z0, rout[0]), (z1, rin[1]), (z1, rout[1]))]
        b = hull(P, tex); K.add(b); out.append(b)
    return out


def near(a, b): return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def place(name, x, y, z, angle=0, **kw):
    return K.custom(ML.PLACE[name], x, y, z, angle, **kw)


# ================================================================================================= shell + ground
def shell():
    sk = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: T('sky')})
    K.add(box((HX0 - 32, HY0 - 32, L.ZBASE - 32), (HX1 + 32, HY1 + 32, L.ZBASE), CAULK, detail=False))
    K.add(box((HX0 - 32, HY0 - 32, L.ZBASE), (HX0, HY1 + 32, L.ZTOP), sk('e'), detail=False))
    K.add(box((HX1, HY0 - 32, L.ZBASE), (HX1 + 32, HY1 + 32, L.ZTOP), sk('w'), detail=False))
    K.add(box((HX0, HY0 - 32, L.ZBASE), (HX1, HY0, L.ZTOP), sk('n'), detail=False))
    K.add(box((HX0, HY1, L.ZBASE), (HX1, HY1 + 32, L.ZTOP), sk('s'), detail=False))
    K.add(box((HX0 - 32, HY0 - 32, L.ZTOP), (HX1 + 32, HY1 + 32, L.ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))
    # clip round the playable rectangle (the hedge and the trees stand behind it)
    for b in (box((HX0, Y1, 0), (HX1, Y1 + 16, L.ZTOP), CLIP), box((HX0, Y0 - 16, 0), (HX1, Y0, L.ZTOP), CLIP),
              box((X1, Y0, 0), (X1 + 16, Y1, L.ZTOP), CLIP), box((X0 - 16, Y0, 0), (X0, Y1, L.ZTOP), CLIP)):
        K.add(b)


SEC = 56                       # half size of the 19th-hole cup


def ground():
    sx, sy = L.SECRET
    holes = [L.LAKE, (sx - SEC, sy - SEC, sx + SEC, sy + SEC)]
    for r in sub_rects((HX0, HY0, HX1, HY1), holes):
        K.add(box((r[0], r[1], L.ZBASE), (r[2], r[3], 0), tx('turf', 'sand')))
    # the 19th hole: a 48u-deep cup
    K.add(box((sx - SEC, sy - SEC, L.ZBASE), (sx + SEC, sy + SEC, -48), tx('cup')))


def lake():
    x0, y0, x1, y1 = L.LAKE
    zf, zw = L.LAKE_FLOOR, L.LAKE_WATER
    K.add(box((x0, y0, L.ZBASE), (x1, y1, zf), tx('sand', 'rock')))
    cut = [K.ramp(x0, y0, x1, y0 + 100, zf, 0, 's', tx('sand', 'rock'), base=zf),           # south shore
           K.ramp(x1 - 100, y0 + 100, x1, y1, zf, 0, 'e', tx('sand', 'rock'), base=zf)]     # east shore
    ix, iy = L.ISLAND
    for (r, z0, z1) in ((340, zf, -24), (300, -24, -8), (260, -8, 0)):
        b = cyl(ix, iy, r, z0, z1, tx('sand' if z1 < 0 else 'turf', 'rock'), 16)
        K.add(b); cut.append(b)
    K.water_box((x0, y0, zf), (x1, y1, zw), T('water'), cutters=cut)
    K.speaker((x0 + x1) / 2, (y0 + y1) / 2, 40, 'ambient/water_rippling')
    # footbridge (planks) from the island to the east bank
    bx0, by0, bx1, by1 = L.BRIDGE
    K.add(box((bx0, by0, 0), (bx1, by1, 12), tx('planks')))
    K.reserve(((bx0, by0, 0), (bx1, by1, 12)))
    K.keep_clear(bx1, by0, bx1 + 120, by1, 0)
    K.crawl((bx0, by0, zf), (bx1, by1, 0))                       # wading under the footbridge
    K.occupy(x0, y0, x1, y1, zf, 0)
    for (x, y) in ((-1900, 300), (-1250, 1050), (-1950, 1000)):
        K.model_on('pad_ducks/pad_duck.md3', x, y, zw, scale=0.6, angle=x % 360)      # bobbing on the water


# ================================================================================================= holes
def holes():
    rail = TX.material('rail_m', TL.planks((40, 90, 180), n_planks=2, grain=4), shade=30)
    cap = TX.material('rail_top', TL.solid((246, 246, 240), 2, 3, 64), shade=30)
    TX.mats['rail_m'] = rail
    zt = L.FELT_Z + L.RAIL_H
    for (num, (x0, y0, x1, y1), d) in L.HOLES:
        K.add(box((x0, y0, 0), (x1, y1, L.FELT_Z), {'top': T('felt'), 'side': T('felt_red'), 'bot': CAULK}))
        t = L.RAIL_T
        if d in 'ns':
            rails = [box((x0 - t, y0, 0), (x0, y1, zt), WCLIP), box((x1, y0, 0), (x1 + t, y1, zt), WCLIP)]
            if d == 'n': rails += [box((x0 - t, y1, 0), (x1 + t, y1 + t, zt), WCLIP)]
            else: rails += [box((x0 - t, y0 - t, 0), (x1 + t, y0, zt), WCLIP)]
        else:
            rails = [box((x0, y0 - t, 0), (x1, y0, zt), WCLIP), box((x0, y1, 0), (x1, y1 + t, zt), WCLIP)]
            if d == 'e': rails += [box((x1, y0 - t, 0), (x1 + t, y1 + t, zt), WCLIP)]
            else: rails += [box((x0 - t, y0 - t, 0), (x0, y1 + t, zt), WCLIP)]
        # the windmill and clown tunnels carry the lane through: no rail pieces inside those solids
        K.solid_piece(f'rails_{num}', rails, TX.texfn('rail_top', 'rail_m', tile=128))
        # tee mat at the tee end, cup + flag at the far end
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dv = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[d]
        Lh = (y1 - y0) if d in 'ns' else (x1 - x0)
        tee = (cx - dv[0] * (Lh / 2 - 110), cy - dv[1] * (Lh / 2 - 110))
        K.add(box((tee[0] - 90, tee[1] - 90, L.FELT_Z), (tee[0] + 90, tee[1] + 90, L.FELT_Z + 2), tx('tee')))
        cup = (cx + dv[0] * (Lh / 2 - 130), cy + dv[1] * (Lh / 2 - 130))
        cb = cyl(cup[0], cup[1], 30, L.FELT_Z, L.FELT_Z + 1, {'top': T('cup'), 'side': T('nodraw_ns'), 'bot': T('nodraw_ns')}, 12)
        K.add(cb)
        place(f'pin_{num}', cup[0], cup[1], L.FELT_Z, (90 * num) % 360, occupy=False)
        K.add(cyl(cup[0], cup[1], 8, L.FELT_Z + 1, L.FELT_Z + 364, WCLIP, 6))
        K.occupy_r(cup[0], cup[1], 40, 0, 400)
        K.occupy(x0 - t, y0 - t, x1 + t, y1 + t, 0, zt)          # props stay off the lanes
    # hole 6: two rolling humps on the felt
    x0, y0, x1, y1 = L.HOLES[5][1]
    for xc in (900, 1400):
        K.ramp(xc - 200, y0, xc, y1, L.FELT_Z, L.FELT_Z + 40, 'e', tx('felt', 'felt_red'), base=L.FELT_Z)
        K.ramp(xc, y0, xc + 200, y1, L.FELT_Z, L.FELT_Z + 40, 'w', tx('felt', 'felt_red'), base=L.FELT_Z)


# ================================================================================================= windmill
def windmill():
    mx, my = L.MILL
    place('windmill', mx, my, 0, 0, occupy=False)
    # tower: octagon (vertex at 0 deg like the model) carved by the tunnel; cap and lookout
    t = frustum(mx, my, L.MILL_R0 - 10, L.MILL_R1 - 6, 0, L.MILL_H, 8, phase=0)
    W, H = L.TUNNEL_W, L.TUNNEL_H
    for p in carve(t, [box((mx - W, my - 400, -1), (mx + W, my + 400, H), WCLIP)]): K.add(p)
    K.add(frustum(mx, my, L.MILL_R1 - 6, 146, L.MILL_H, L.CAP_TOP - 16, 16))      # flush with the tower and the lookout
    K.add(cyl(mx, my, 146, L.CAP_TOP - 16, L.CAP_TOP, WCLIP, 16))
    # stage: an octagon ring round the tower (inner edge = the tower core at that height)
    rt = (L.MILL_R0 - 10) + ((L.MILL_R1 - 6) - (L.MILL_R0 - 10)) * (L.STAGE_Z - 16) / L.MILL_H
    for k in range(8):
        a0 = 2 * math.pi * k / 8; a1 = a0 + 2 * math.pi / 8
        P = [(mx + r * math.cos(a), my + r * math.sin(a), z) for a in (a0, a1) for r in (rt + 0.5, L.STAGE_R - 6)
             for z in (L.STAGE_Z - 16, L.STAGE_Z)]
        K.add(hull(P, WCLIP, round_pts=False))
    K.occupy_disc(mx, my, L.MILL_R0 + 10, 0, L.STAGE_Z - 16)
    K.occupy_disc(mx, my, L.STAGE_R, L.STAGE_Z - 16, L.STAGE_Z)
    K.occupy_disc(mx, my, 300, L.MILL_H, L.CAP_TOP + 40)
    # stairs from the east onto the stage, a pad from the south-west, a pad from the stage to the lookout
    sx0, sy0, sx1, sy1 = L.MSTAIR
    K.stairs16(sx0, sy0, sx1, sy1, 0, L.STAGE_Z, 'w', tx('planks'), route='mill_stairs')
    K.reserve(((sx0, sy0, 0), (sx1, sy1, L.STAGE_Z)))
    K.keep_clear(sx1, sy0, sx1 + 110, sy1, 0)
    K.jumppad(mx - 640, my - 560, 0, land=(mx - 330, my - 250, L.STAGE_Z), apex=L.STAGE_Z + 190, name='pad_stage',
              edges=[(mx - 382, my - 300, L.STAGE_Z)])
    K.jumppad(mx + 300, my + 300, L.STAGE_Z, land=(mx + 40, my + 70, L.CAP_TOP), apex=L.CAP_TOP + 190, name='pad_lookout',
              edges=[(mx + 140, my + 140, L.CAP_TOP), (mx + 230, my + 230, 970)])
    K.trigger_sound((mx - 100, my - 100, L.CAP_TOP), (mx + 100, my + 100, L.CAP_TOP + 64), 'human/applause', 'lookout_cheer', wait=20)
    # sails turning on the front (south) face of the cap
    K.rotating_model2(ML.IQM['sails'], (mx, my - 190, L.HUB_Z), 30, axis='y')
    K.speaker(mx, my, 900, 'ambient/floor_creaking', loop=False, targetname='creak')
    K.M.ent('func_timer', (mx + 400, my + 600, 120), target='creak', wait=14, random=6, spawnflags=1)
    K.route('mill_tunnel', (mx, my - 480, L.FELT_Z), (mx, my + 480, L.FELT_Z))


# ================================================================================================= lighthouse
def lighthouse():
    ix, iy = L.ISLAND
    place('lighthouse', ix, iy, 0, 0, occupy=False)
    g = L.LIGHT_GAL
    K.add(cyl(ix, iy, 146, g - 20, g, WCLIP, 16))
    ring_wedges(ix, iy, 150, L.GAL_R - 4, g - 14, g, 16, phase=0)
    # lamp room glass (door pane at +x open), lamp, dome
    for k in range(8):
        if k == 7: continue
        a0 = 2 * math.pi * (k + 0.5) / 8; a1 = 2 * math.pi * (k + 1.5) / 8
        P = [(ix + r * math.cos(a), iy + r * math.sin(a), z) for a in (a0, a1) for r in (112, 122) for z in (g, 1040)]
        K.add(hull(P, WCLIP, round_pts=False))
    K.add(cyl(ix, iy, 44, g, 1010, WCLIP, 12))
    K.add(cyl(ix, iy, 140, 1040, L.LAMP_TOP, WCLIP, 16))
    K.occupy_disc(ix, iy, 340, -40, L.LAMP_TOP)
    K.light(ix, iy, 980, 500, '1 0.95 0.75')
    K.light(ix + 60, iy, 120, 180, '1 0.9 0.7')
    # pad from the east bank onto the gallery
    K.jumppad(-740, iy + 240, 0, land=(ix + 200, iy + 70, g), apex=g + 160, name='pad_gallery', edges=[(ix + 280, iy + 100, g)])
    K.route('lighthouse_door', (ix + 330, iy, 0), (ix + 40, iy, 0))
    K.route('bridge', (L.BRIDGE[2] + 80, iy, 0), (ix + 280, iy, 0))


def lighthouse_walls():
    """tower collision: 16 wedges in two bands (vertical inner faces), the two facing +x open below the door top"""
    ix, iy = L.ISLAND
    g = L.LIGHT_GAL
    for (za, zb, rin, ra, rb) in ((0, 400, 160, 186, 168), (400, g - 20, 140, 168, 146)):
        for k in range(16):
            a0 = 2 * math.pi * k / 16; a1 = a0 + 2 * math.pi / 16
            z0 = max(za, 206) if near((a0 + a1) / 2, 0) < math.radians(23) else za
            if z0 >= zb: continue
            P = []
            for a in (a0, a1):
                for (z, ro) in ((z0, ra + (rb - ra) * (z0 - za) / (zb - za)), (zb, rb)):
                    for r in (rin, ro):
                        P.append((ix + r * math.cos(a), iy + r * math.sin(a), z))
            K.add(hull(P, WCLIP))


# ================================================================================================= volcano
def volcano():
    vx, vy = L.VOLC
    place('volcano', vx, vy, 0, 0, occupy=False)
    K.add(bprism(ngon(vx, vy, L.V1_R, 24, 7.5), 0, L.V1_H, WCLIP))
    rmid = L.V2_R0 - 8 - (L.V2_R0 - L.V2_R1) * (L.CRATER_Z - L.V1_H) / (L.V2_H - L.V1_H)
    K.add(frustum(vx, vy, L.V2_R0 - 8, rmid, L.V1_H, L.CRATER_Z, 24))
    ring_wedges(vx, vy, L.CRATER_R + 6, (rmid, L.V2_R1 - 4), L.CRATER_Z, L.V2_H, 24)
    ring_wedges(vx, vy, L.CRATER_R + 6, L.CRATER_R + 30, L.V2_H, L.V2_H + 64, 24, tex=BOTCLIP)   # bots keep off the lava
    K.hurt((vx - 118, vy - 118, L.CRATER_Z + 1), (vx + 118, vy + 118, L.CRATER_Z + 40), dmg=10)
    K.occupy_disc(vx, vy, L.V1_R + 20, 0, L.V1_H)
    K.occupy_disc(vx, vy, L.V2_R0 + 10, L.V1_H, L.V2_H + 64)
    sx0, sy0, sx1, sy1 = L.VSTAIR
    K.stairs16(sx0, sy0, sx1, sy1, 0, L.V1_H, 's', tx('rock'), route='volcano_stairs')
    K.reserve(((sx0, sy0, 0), (sx1, sy1, L.V1_H)))
    K.keep_clear(sx0, sy1, sx1, sy1 + 110, 0)
    for (sx, nm) in ((-1, 'w'), (1, 'e')):
        K.jumppad(vx + sx * 530, vy, L.V1_H, land=(vx + sx * 236, vy + 40, L.V2_H), apex=L.V2_H + 180, name=f'pad_rim_{nm}',
                  edges=[(vx + sx * (L.V2_R0 - 8), vy, L.V1_H + 30), (vx + sx * (L.V2_R1 - 4), vy, L.V2_H)])
    K.speaker(vx, vy, L.CRATER_Z + 60, 'ambient/slime_bubbling')
    K.light(vx, vy, L.CRATER_Z + 140, 400, '1 0.5 0.15')


# ================================================================================================= clown
def clown():
    cx, cy = L.CLOWN
    place('clown', cx, cy, 0, 0, occupy=False)
    W, H = L.MOUTH_W, L.MOUTH_H
    low = bprism(ngon(cx, cy, 396, 16), 0, 480, WCLIP)
    for p in carve(low, [box((cx - W, cy - 500, -1), (cx + W, cy + 500, H), WCLIP)]): K.add(p)
    K.add(frustum(cx, cy, 396, 340, 480, 620))
    K.add(frustum(cx, cy, 340, 286, 620, L.HEAD_H))
    K.add(cyl(cx, cy, 196, L.HEAD_H + 20, L.HAT_TOP, WCLIP, 16))
    K.occupy_disc(cx, cy, 440, 0, L.HAT_TOP)
    K.jumppad(cx - 640, cy, 0, land=(cx - 60, cy, L.HAT_TOP), apex=L.HAT_TOP + 170, name='pad_hat',
              edges=[(cx - 300, cy, L.HEAD_H + 20), (cx - 196, cy, L.HAT_TOP)])
    K.route('clown_mouth', (cx, cy + 560, L.FELT_Z), (cx, cy - 520, L.FELT_Z))
    K.light(cx, cy, 160, 220, '1 0.6 0.6')
    K.trigger_sound((cx - 176, cy + 300, L.FELT_Z), (cx + 176, cy + 360, L.FELT_Z + 64), 'misc/bicycle_bell', 'honk', wait=6)


# ================================================================================================= clubhouse
def clubhouse():
    """Putt-Putt Paradise: white weatherboard clubhouse with green trim. Outside: striped awning over the door, framed
    windows with shutters and flower boxes (north and west), a giant putter, a putter barrel, a soda machine, a rooftop
    billboard. Inside: chequered floor, striped wallpaper, counter with a trophy shelf and pendant lamps over it, turning
    ceiling fans, drinks fridge, snack table, ball crates, putter rack, scoreboard and posters. Stairs to the roof
    terrace (umbrella tables)."""
    x0, y0, x1, y1 = L.CLUB
    h = L.CLUB_H; w = 24
    d0, d1 = L.CLUB_DOOR
    NW = ((-1880, -1680), (-1360, -1160))           # north windows (x spans)
    WW = ((-1480, -1360), (-1240, -1120))           # west windows (y spans)
    br = []
    for (a, b) in ((x0, NW[0][0]), (NW[0][1], d0), (d1, NW[1][0]), (NW[1][1], x1)):
        br.append(box((a, y1 - w, 0), (b, y1, h), WCLIP))
    for (a, b) in NW:
        br.append(box((a, y1 - w, 0), (b, y1, 110), WCLIP)); br.append(box((a, y1 - w, 240), (b, y1, h), WCLIP))
    br.append(box((d0, y1 - w, 224), (d1, y1, h), WCLIP))
    br.append(box((x0, y0, 0), (x1, y0 + w, h), WCLIP))
    for (a, b) in ((y0 + w, WW[0][0]), (WW[0][1], WW[1][0]), (WW[1][1], y1 - w)):
        br.append(box((x0, a, 0), (x0 + w, b, h), WCLIP))
    for (a, b) in WW:
        br.append(box((x0, a, 0), (x0 + w, b, 110), WCLIP)); br.append(box((x0, a, 240), (x0 + w, b, h), WCLIP))
    br.append(box((x1 - w, y0 + w, 0), (x1, y1 - w, h), WCLIP))
    br.append(box((x0, y0, h), (x1, y1, h + 16), WCLIP))
    cb = TX.material('clapboard', MM.clapboard(), shade=20)
    wp = TX.material('wallpaper', MM.wallpaper(), shade=20)
    rf = TX.material('roof_m', TL.tiles((120, 120, 124), (100, 100, 104), cols=4, rows=4, grout_w=0.02), shade=20)
    tr = TX.material('club_trim', TL.solid((40, 110, 60), 2, 9, 64), shade=20)
    ce = TX.material('club_ceiling', TL.planks((236, 232, 220), n_planks=6), shade=20)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def texfn(c, n, poly):
        if n[2] > 0.7: return (rf if c[2] > h else tr), ML.planar_uv(n, 256)
        if n[2] < -0.7: return (ce if c[2] > h - 1 else tr), ML.planar_uv(n, 256)
        if c[2] > h - 1: return tr, ML.planar_uv(n, 64)                       # roof fascia
        inner = (cx - c[0]) * n[0] + (cy - c[1]) * n[1] > 0 and x0 + 1 < c[0] < x1 - 1 and y0 + 1 < c[1] < y1 - 1
        jamb = abs(n[0]) > 0.7 and y1 - w - 1 < c[1] < y1 + 1 or abs(n[1]) > 0.7 and x0 - 1 < c[0] < x0 + w + 1
        if jamb: return tr, ML.planar_uv(n, 64)
        return (wp if inner else cb), ML.planar_uv(n, 256)
    K.solid_piece('clubhouse', br, texfn)
    for (a, b) in NW: K.add(box((a, y1 - 14, 110), (b, y1 - 10, 240), T('glass')))
    for (a, b) in WW: K.add(box((x0 + 10, a, 110), (x0 + 14, b, 240), T('glass')))
    K.add(box((x0 + w, y0 + w, 0), (x1 - w, y1 - w, 4), tx('checker')))
    K.reserve(((x0, y0, 0), (x0 + w + 4, y1, h + 16)), ((x1 - w - 4, y0, 0), (x1, y1, h + 16)),
              ((x0, y0, 0), (x1, y0 + w + 4, h + 16)), ((x0, y1 - w - 4, 0), (x1, y1, h + 16)))
    K.keep_clear(d0 - 40, y1 - 140, d1 + 40, y1 + 180, 0)
    # ---- outside
    place('awning', (d0 + d1) / 2, y1, 300, 0, occupy=False)
    for (a, b) in NW: place('window_dress', (a + b) / 2, y1, 110, 0, occupy=False)
    for (a, b) in WW: place('window_dress', x0, (a + b) / 2, 110, 90, occupy=False)
    place('giant_putter', -1925, y1 + 50, 0, 180, boxes=[((-150, -64, 0), (64, 14, 90)), ((40, -6, 90), (68, 34, 380))])
    place('putter_barrel', d0 - 70, y1 + 90, 0, 0, cyls=[(0, 0, 56, 0, 100)])
    place('vending', -2140, -1250, 0, 0, boxes=[((-86, -61, 0), (86, 61, 320))])
    K.speaker(-2120, -1250, 120, 'machine/freezer')
    place('billboard', (x0 + x1) / 2, y0 + 60, h + 16, 0,
          boxes=[((-250, -10, 0), (-230, 10, 330)), ((230, -10, 0), (250, 10, 330)), ((-330, -14, 140), (-250, 0, 330)),
                 ((-230, -14, 140), (230, 0, 330)), ((250, -14, 140), (330, 0, 330))])
    # ---- inside
    place('counter', -1620, y0 + w + 110, 4, 0, boxes=[((-300, -80, 0), (300, 80, 150))])
    place('trophy_shelf', -1620, y0 + w + 20, 210, 180, boxes=[((-280, -20, 0), (280, 20, 10))])
    for x in (-1800, -1440): place('pendant_lamp', x, -1500, h, 0, occupy=False); K.light(x, -1500, h - 100, 160, '1 0.9 0.7')
    for (fx, nm) in ((-1700, 'fan_w'), (-1300, 'fan_e')):
        place('fan_mount', fx, -1260, h, 0, occupy=False)
        K.rotating_model2(ML.IQM['fan'], (fx, -1260, h - 42), 90)
    place('drinks_fridge', x1 - w - 76, y0 + w + 60, 4, 0, boxes=[((-70, -55, 0), (70, 55, 280))])
    place('snack_set', -1700, -1170, 4, 0, cyls=[(0, 0, 70, 0, 112), (-120, 0, 34, 0, 78), (120, 0, 34, 0, 78)])
    place('ball_crate', -1850, -1320, 4, 0, boxes=[((-70, -50, 0), (70, 50, 80))])
    place('putter_rack', x1 - w - 44, -1280, 4, 90, boxes=[((-180, -40, 0), (180, 40, 230))])
    K.add(sign_box((x0 + w, -1600, 110), (x0 + w + 4, -1500, 250), T('poster_rules'), 256, 384, back=CAULK, facing='e', edge=T('rail_white')))
    K.add(sign_box((-1660, y1 - w - 4, 240), (-1380, y1 - w, 300), T('poster_hio'), 512, 128, back=CAULK, facing='s', edge=T('rail_white')))
    K.add(sign_box((x1 - w - 4, -1440, 236), (x1 - w, -1120, 312), T('sign_score'), 512, 256, back=CAULK, facing='w', edge=T('rail_white')))
    K.light(-1700, -1320, 290, 220); K.light(-1340, -1320, 290, 220)
    # ---- stairs up the east side to the roof terrace; umbrella tables up there
    sx0, sy0, sx1, sy1 = L.CSTAIR
    K.stairs16(sx0, sy0, sx1, sy1, 0, h + 16, 's', tx('planks'), route='club_stairs')
    K.reserve(((sx0, sy0, 0), (sx1, sy1, h + 16)))
    K.keep_clear(sx0, sy1, sx1, sy1 + 110, 0)
    for (x, y) in ((-1740, -1200), (-1300, -1300)):
        place('umbrella_table', x, y, h + 16, 0, cyls=[(0, 0, 100, 0, 124), (0, 0, 10, 124, 340)])
    K.route('club_door', ((d0 + d1) / 2, y1 + 140, 0), ((d0 + d1) / 2, -1250, 4))
    K.speaker(-1520, -1450, 120, 'machine/tv_upstairs')


# ================================================================================================= scenery + props
def scenery():
    # giant golf ball on its tee in the middle
    bx, by = L.BALL
    zc = L.TEE_H - 10 + L.BALL_R
    place('golf_ball', bx, by, 0, 0, cyls=[(0, 0, 66, 0, L.TEE_H)])
    for (r, z0, z1) in ((200, zc - 240, zc - 150), (270, zc - 150, zc + 150), (200, zc + 150, zc + 240)):
        K.add(cyl(bx, by, r, z0, z1, WCLIP, 16))
    K.occupy_disc(bx, by, L.BALL_R + 10, 0, zc + L.BALL_R)
    # loop-the-loop over hole 5 (legs stand outside the rails)
    lx, ly = L.LOOP
    place('loop', lx, ly, L.FELT_Z, 0, occupy=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.add(box((lx + sx * 330 - 16, ly + sy * 250 - 16, 0), (lx + sx * 330 + 16, ly + sy * 250 + 16, 60), WCLIP))
    # hedge round the playable area (scenery behind the clip) and trees beyond it
    for x in np.arange(HX0 + 512, HX1 - 511, 1024):
        place('hedge_long', x, Y1 + 100, 0, 0, occupy=False); place('hedge_long', x, Y0 - 100, 0, 0, occupy=False)
    for y in np.arange(Y0 - 200 + 512, Y1 + 200 - 511, 1024):
        place('hedge_long', X1 + 100, y, 0, 90, occupy=False); place('hedge_long', X0 - 100, y, 0, 90, occupy=False)
    rng = np.random.default_rng(4)
    for k in range(22):
        side = k % 4
        if side == 0: x, y = rng.uniform(HX0 + 300, HX1 - 300), Y1 + 420
        elif side == 1: x, y = rng.uniform(HX0 + 300, HX1 - 300), Y0 - 420
        elif side == 2: x, y = X1 + 400, rng.uniform(HY0 + 300, HY1 - 300)
        else: x, y = X0 - 400, rng.uniform(HY0 + 300, HY1 - 300)
        K.model_on('pad_ddmix/trashcan/tree_summer.md3' if k % 3 else 'pad_ddmix/trashcan/tree_spring.md3', x, y, 0,
                   scale=rng.uniform(1.7, 1.9), angle=rng.uniform(0, 360), spawnflags=4, _castshadows=1)
    # benches, buggies, flowerbeds, bins (cover in the open bands)
    for (x, y, a) in ((-700, 300, 0), (700, 250, 180), (-500, -1000, 90), (1300, 700, 90), (-1300, 1600, 0),
                      (1900, 400, 90), (-2100, -800, 0), (300, -900, 90)):
        K.prop(ML.PLACE['bench'], x, y, 0, boxes=[((-200, -60, 0), (200, 60, 86)), ((-200, 50, 86), (200, 64, 186))], angle=a)
    for (x, y, a) in ((-760, -1750, 0), (1900, 900, 0), (420, 1900, 0)):
        K.prop(ML.PLACE['buggy'], x, y, 0, boxes=[((-256, -130, 0), (256, 130, 200)), ((-200, -140, 200), (200, 140, 440))], angle=a)
    for (x, y, m, sc) in ((-1000, -500, 'pad_ddmix/plants/flower_yellow.md3', 1.4), (1000, 700, 'pad_ddmix/plants/flower_pink.md3', 1.8),
                          (-480, 20, 'pad_ddmix/plants/flower_pink.md3', 1.8), (2080, -1080, 'pad_ddmix/plants/flower_yellow.md3', 1.4),
                          (-2050, 1650, 'pad_sunflower/pad_sunflower_l.md3', 1.6), (2050, 1750, 'pad_sunflower/pad_sunflower_l.md3', 1.6),
                          (500, 1800, 'pad_ddmix/trashcan/bush.md3', 1.2), (-2100, 1450, 'pad_ddmix/plants/flower_pink.md3', 1.8),
                          (2100, -1900, 'pad_sunflower/pad_sunflower_l.md3', 1.6), (900, -1050, 'pad_ddmix/trashcan/garbage_bag_group.md3', 1.0),
                          (-800, 1600, 'pad_ball/pad_soccerball.md3', 1.2), (1700, -1150, 'pad_tins/pad_coke.md3', 1.0)):
        K.catalog(m, x, y, 0, scale=sc, lit=True)


def secret():
    sx, sy = L.SECRET
    place('pin_19', sx + SEC + 30, sy, 0, 0, occupy=False)
    K.add(cyl(sx + SEC + 30, sy, 8, 0, 364, WCLIP, 6))
    K.secret((sx - SEC, sy - SEC, -48), (sx + SEC, sy + SEC, -12), dest=(0, -200, L.CAVERN_Z), angle=90, name='hole19',
             approach='top')
    # the Lost Ball Cavern (sealed, below the world)
    z = L.CAVERN_Z
    x0, y0, x1, y1 = -512, -384, 512, 384
    t = {'side': T('cavern'), 'top': T('sand'), 'bot': T('cavern')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 384), (x1 + 32, y1 + 32, z + 416), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 384), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 384), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 384), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 384), t, detail=False))
    K.add(sign_box((-200, y1 - 4, z + 260), (200, y1, z + 340), T('sign_cavern'), 512, 128, back=CAULK, facing='s', edge=T('rail_white')))
    for (x, y, nm, r) in ((-330, 200, 'balls_big', 200), (340, 180, 'balls_big', 200), (0, 260, 'balls_small', 120),
                          (-380, -220, 'balls_small', 120), (380, -220, 'balls_small', 120)):
        K.prop(ML.PLACE[nm], x, y, z, cyls=[(0, 0, r * 0.8, 0, 50)], angle=0, search=60)
    K.item('item_padpower', -150, 40, z); K.item('item_revival', 150, 40, z); K.item('holdable_killerducks', 0, 120, z)
    K.item('item_armor_padshield', 0, -60, z); K.ammo('imperius', -220, -60, z)
    K.teleporter((-48, y0, z), (48, y0 + 48, z + 96), dest=(sx - 160, sy, 0), angle=180, name='cavern_exit')
    K.light(0, 0, z + 300, 500, '1 0.95 0.8'); K.light(-300, 200, z + 160, 200); K.light(300, 200, z + 160, 200)
    K.speaker(0, 0, z + 200, 'ambient/water_drippling')


# ================================================================================================= loot + spawns
def items():
    mx, my = L.MILL
    K.weapon('imperius', mx - 60, my - 60, L.CAP_TOP, marker='purple')
    K.weapon('bubbleg', mx - 300, my + 300, L.STAGE_Z, marker='green')
    ix, iy = L.ISLAND
    K.weapon('betty', ix, iy - 230, L.LIGHT_GAL, marker='black')
    K.weapon('splasher', -1250, 900, L.LAKE_FLOOR, marker='blue')
    vx, vy = L.VOLC
    K.weapon('balloony', vx, vy + 236, L.V2_H, marker='orange')
    cx, cy = L.CLOWN
    K.weapon('pumper', cx - 40, cy + 40, L.HAT_TOP, marker='green')
    K.weapon('boaster', -1300, -1200, 4, marker='orange')
    ammo = {'imperius': [(-760, 1300, 0), (1900, 1700, 0), (vx, vy - 236, L.V2_H)],
            'bubbleg': [(mx + 300, my - 300, L.STAGE_Z), (-400, -400, 0), (1500, 900, 0), (-1700, -700, 0)],
            'betty': [(ix + 80, iy + 60, 0), (-900, 1500, 0), (-1500, -1460, L.CLUB_H + 16)],
            'splasher': [(-2000, 200, L.LAKE_FLOOR), (-1100, -700, 0), (600, 1600, 0)],
            'balloony': [(vx + 520, vy - 200, L.V1_H), (2050, 0, 0), (900, 300, 0)],
            'pumper': [(500, -1150, 0), (-500, -1650, 0), (cx + 120, cy, 4)],
            'boaster': [(-1800, -1150, 4), (-1150, -1800, 0), (1000, -820, 0), (200, 1850, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((-200, -500, 0), (1800, -1900, 0), (-1900, 1800, 0)): K.ammo('nipper', x, y, z)
    K.item('item_armor_shard', mx + 380, my, L.STAGE_Z); K.item('item_armor_shard', vx - 236, vy, L.V2_H)
    K.item('item_armor_padshield', -1600, -1500, L.CLUB_H + 16)
    K.item('item_speedy', 1600, 1700, 0); K.item('holdable_floater', -1000, 300, 0); K.item('item_jumper', 2050, -1600, 0)
    K.station(-1500, -1300, 4, 90); K.station(2150, 650, 0, 180)


def spawns():
    for (x, y, a) in ((-700, 0, 0), (700, -50, 180), (-300, -700, 90), (400, 900, 270), (-1600, -700, 90), (-700, 1200, 0),
                      (1300, 1800, 270), (2000, 600, 180), (2000, -1000, 135), (1100, -1100, 90), (-600, -1200, 45),
                      (-1900, -1800, 45), (-2000, 1700, 315), (-1350, 300, 90), (1200, 300, 180), (300, 1700, 270)):
        K.spawn(x, y, 0, a)
    K.ent('info_player_intermission', (2000, -1900, 1200), angles='22 135 0')


def lights():
    K.timer_sound(0, 0, 900, 'animal/blackbird', 'birds', 18, 9)
    K.timer_sound(-1500, 1500, 700, 'animal/bird_blackcap', 'birds2', 23, 11)


def shader():
    TX.write_shader(extra=[SH.sky('env/fort-pad512', sun=(225, 55), sun_int=110, skylight=(60, 3))],
                    arena_types=INFO.get('arena_types'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    MM.make_textures()
    TX.kit_defaults(pad_rgb=(250, 220, 60))
    MM.make_all()
    shell(); ground(); lake(); holes()
    windmill(); lighthouse_walls(); volcano(); clown(); clubhouse()
    lighthouse(); scenery(); secret()
    items(); spawns(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
