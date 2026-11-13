#!/usr/bin/env python3
"""Pad Deep Dive (wop_paddive) - a glass dive centre under a wave-shaped shell roof, flanked by cascading pool
terraces, reached over a causeway between two deep moats. Built on woplib.

    OUT=<dir> python3 build_paddive.py          (names come from mapinfo.json next to this file)

Layout (z 0 = plaza): plaza south -> causeway -> lobby (dive shaft, 640 deep) -> gallery (z 256) -> top terraces (z 256)
-> cascade terraces 192 / 128 / 64 back down to the plaza on both sides. Roof by pads from the top terraces or the
bubble at the bottom of the shaft. East/west mirrored.
"""
import os, sys, json, math
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, 'wopmap.py')): ROOT = os.path.dirname(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from wopmap import box, cyl, hull, prism, carve, sub_rects, sign_box
from woplib.kit import MapKit, CAULK, WCLIP, CLIP, TRIG
from woplib import models as ML, shaders as SH, texlib as TL
from pd_shape import (BC, DRUM_RO, DRUM_RI, MEZZ_Z, ROOF_X, ROOF_BOT, FACE_KIND, roof_f, roof_w, roof_top, face_pts,
                      ngon16, lobe)
import pd_models as PM

INFO = json.load(open(os.path.join(HERE, 'mapinfo.json')))
OUT = os.environ.get('OUT', os.path.join(HERE, 'out'))
MAP, NS, LONG = INFO['map'], INFO['ns'], INFO['longname']
X0, Y0, X1, Y1 = INFO['bounds']
ZTOP = 1344; WALL_H = 224; SLAB = -320
K = MapKit(MAP, NS, LONG, (X0, Y0, X1, Y1), worldspawn={'_ambient': '22', '_color': '1 0.86 0.78', 'gridsize': '192 192 256'})
T = K.T
ML.configure(NS, OUT); SH.configure(NS, MAP, LONG)
TX = TL.Textures(K)

# ------------------------------------------------------------------------------------------------ layout constants
MOAT = (160, -896, 680, -128); MOAT_FLOOR = -280; MOAT_TOP = -24            # east basin; the west one is mirrored
EXIT = (300, -1088, 540, -896); SHELF = -48                                   # steps out of the moat (south side)
NICHE = (680, -264, 792, -136); NICHE_FLOOR = -72                             # behind the big waterfall (secret)
SHAFT = (BC[0] - 192, BC[1] - 192, BC[0] + 192, BC[1] + 192); SHAFT_R = 176; SHAFT_FLOOR = -640; SHAFT_TOP = -8
SHAFT_EXIT = (-112, BC[1] - 384, 112, BC[1] - 192)
TUNNEL = (-160, -560, 160, -432); TUNNEL_TOP = -120                           # swim-through under the causeway
LAWN_N = 1312; LAWN_E = 1536
#           name   cx    cy    r   top  flats (east side; mirrored for the west)
TIERS = [('a', 980, 520, 480, 256, [('s', 120)]),
         ('b', 1060, -200, 420, 192, [('s', -550), ('w', 680)]),
         ('c', 1060, -820, 400, 128, [('s', -1160), ('w', 680)]),
         ('d', 1060, -1400, 380, 64, [('w', 740)])]
#            on tier   x0    y0     x1    y1    z0   z1  dir
TSTAIRS = [('b', 920, -8, 1180, 120, 192, 256, 'n'), ('c', 930, -678, 1190, -550, 128, 192, 'n'),
           ('d', 930, -1288, 1190, -1160, 64, 128, 'n'), (None, 612, -1530, 740, -1270, 0, 64, 'e')]
ROOF_PAD = (1180, BC[1]); ROOF_LAND = (896, BC[1])
VAULT = (-256, -856, 256, -344); VAULT_Z = -1200


def mr(r, sx): return r if sx > 0 else (-r[2], r[1], -r[0], r[3])


# ------------------------------------------------------------------------------------------------ textures
def sunset_sky(n=512):
    """procedural sunset cube (env/paddive/sunset_*): peach horizon fading to dusky violet, hazy tree line below"""
    def col(e):                                      # e = tan(elevation): 1 top of a side face, 0 horizon, -1 bottom
        e = np.asarray(e, np.float32)[..., None]
        up = ML.lerp(ML.C((255, 196, 150)), ML.C((232, 168, 160)), np.clip(e / 0.35, 0, 1))
        up = ML.lerp(up, ML.C((168, 150, 190)), np.clip((e - 0.3) / 0.9, 0, 1))
        dn = ML.lerp(ML.C((210, 170, 140)), ML.C((70, 96, 72)), np.clip(-e / 0.10, 0, 1))
        return np.where(e >= 0, up, dn)
    x, y = ML.xy(n)
    d = os.path.join(OUT, 'env', NS); os.makedirs(d, exist_ok=True)
    side = col(1 - 2 * y) + ML.N3(n, 20, 3, 5)
    for f in ('rt', 'lf', 'bk', 'ft'): ML.img(side).convert('RGB').save(os.path.join(d, f'sunset_{f}.jpg'), quality=92)
    r = np.maximum(np.abs(x - 0.5), np.abs(y - 0.5)) * 2
    ML.img(col(1 + (1 - r) * 0.8)).convert('RGB').save(os.path.join(d, 'sunset_up.jpg'), quality=92)
    ML.img(col(-np.ones((n, n)))).convert('RGB').save(os.path.join(d, 'sunset_dn.jpg'), quality=92)


def textures():
    TX.add('paving', TL.tiles((222, 206, 184), (176, 158, 136), cols=4, rows=4, offset=0.5, grout_w=0.02, vary=5))
    TX.add('strata', TL.tiles((214, 188, 156), (146, 124, 98), cols=3, rows=12, offset=0.5, grout_w=0.05, vary=22))
    TX.add('pooltile', TL.tiles((86, 176, 204), (200, 228, 232), cols=8, rows=8, offset=0, grout_w=0.07, vary=10), steps='splashsteps')
    TX.add('deeptile', TL.tiles((28, 74, 128), (16, 44, 84), cols=8, rows=8, offset=0, grout_w=0.07, vary=8))
    TX.add('grass', TL.solid((84, 142, 62), 12, 15, 256), steps='softsteps')
    TX.add('hedge', TL.stone((58, 112, 52), cells=70, edge=(36, 76, 36), edge_w=0.02, vary=20))
    TX.add('white', TL.solid((236, 232, 222), 3, 5))
    TX.add('deck', TL.planks((186, 136, 80), n_planks=8, stagger=True), steps='woodsteps')
    TX.add('water', TL.solid((120, 205, 225), 10, 11, 128), 'water', rgb=(0.55, 0.85, 0.92), alpha=0.45)
    TX.add('water_deep', TL.solid((40, 100, 170), 10, 13, 128), 'water', rgb=(0.2, 0.42, 0.72), alpha=0.6)
    TX.add('sign_dive', TL.label('PAD DEEP DIVE', 512, 128, (24, 60, 110), (250, 236, 200), serif=True, border=(226, 180, 80)), 'sign',
           check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 190, 90))
    sunset_sky()


# ------------------------------------------------------------------------------------------------ helpers
def solid_ok(b):
    """drop the zero-thickness slivers carve() leaves when round shapes cut each other"""
    V = b.verts()
    if len(V) < 4 or (V.max(0) - V.min(0)).min() < 1: return False
    try: return ConvexHull(V).volume >= 16
    except Exception: return False


def carved(brush, cutters, tex):
    return [p for p in carve(brush, cutters, tex=tex) if solid_ok(p)]


def water(brush, cutters, tex, top):
    """ONE water brush carved by everything inside it; only the top faces draw"""
    for p in (carved(brush, cutters, tex) if cutters else [brush]):
        for f in p.faces: f.tex = tex if f.n[2] > 0.9 and abs(f.d - top) < 0.5 else tex + '_nd'
        K.add(p)
    mn, mx = brush.bounds()
    K.spots.setdefault('water', []).append(dict(mn=[float(v) for v in mn], mx=[float(v) for v in mx], depth=float(mx[2] - mn[2])))


# ------------------------------------------------------------------------------------------------ ground + hull
def ground():
    """one thick structural slab with rectangular holes (moats, exits, niches, dive shaft); every hole shallower than
    the slab gets a structural filler as its floor, so nothing but the shaft needs its own shell"""
    holes = [(SHAFT, None), (SHAFT_EXIT, SHELF), (TUNNEL, MOAT_FLOOR)]
    for sx in (1, -1):
        holes += [(mr(MOAT, sx), MOAT_FLOOR), (mr(EXIT, sx), SHELF), (mr(NICHE, sx), NICHE_FLOOR)]
    lawns = [(X0 - 32, LAWN_N, X1 + 32, Y1 + 32), (LAWN_E, Y0 - 32, X1 + 32, LAWN_N), (X0 - 32, Y0 - 32, -LAWN_E, LAWN_N)]
    pave = {'top': T('paving'), 'side': T('deeptile'), 'bot': CAULK}
    for r in sub_rects((X0 - 32, Y0 - 32, X1 + 32, Y1 + 32), [h for h, _ in holes] + lawns):
        K.add(box((r[0], r[1], SLAB), (r[2], r[3], 0), pave, detail=False))
    for r in lawns:
        K.add(box((r[0], r[1], SLAB), (r[2], r[3], 0), {'top': T('grass'), 'side': CAULK, 'bot': CAULK}, detail=False))
    for r, fz in holes:
        if fz is None: continue
        ft = T('deeptile') if fz < -100 else T('pooltile')
        K.add(box((r[0], r[1], SLAB), (r[2], r[3], fz), {'top': ft, 'side': T('deeptile'), 'bot': CAULK}, detail=False))
        K.keep_clear(r[0], r[1], r[2], r[3], fz, 96)
    t = TUNNEL                                           # the causeway carries on over the tunnel
    K.add(box((t[0], t[1], TUNNEL_TOP), (t[2], t[3], 0), {'top': T('paving'), 'side': T('deeptile'), 'bot': T('deeptile')}, detail=False))
    # hull: hedge up to WALL_H, sunset sky above and overhead
    def wall(mn, mx, inner):
        for z0, z1, tx in ((0, WALL_H, T('hedge')), (WALL_H, ZTOP, T('sky'))):
            t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}; t[inner] = tx
            K.add(box((mn[0], mn[1], z0), (mx[0], mx[1], z1), t, detail=False))
    wall((X0 - 32, Y0 - 32), (X0, Y1 + 32), 'e'); wall((X1, Y0 - 32), (X1 + 32, Y1 + 32), 'w')
    wall((X0, Y0 - 32), (X1, Y0), 'n'); wall((X0, Y1), (X1, Y1 + 32), 's')
    K.add(box((X0 - 32, Y0 - 32, ZTOP), (X1 + 32, Y1 + 32, ZTOP + 32), {'bot': T('sky'), 'side': CAULK, 'top': CAULK}, detail=False))


def moats():
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': CAULK}
    for sx in (1, -1):
        m = mr(MOAT, sx); e = mr(EXIT, sx); n = mr(NICHE, sx)
        steps = K.stairs16(e[0], e[1], e[2], e[1] + 96, SHELF, 0, 's', tl)
        water(box((m[0], m[1], MOAT_FLOOR), (m[2], m[3], MOAT_TOP), T('water_deep')), [], T('water_deep'), MOAT_TOP)
        water(box((e[0], e[1], SHELF), (e[2], e[3], MOAT_TOP), T('water_deep')), steps, T('water_deep'), MOAT_TOP)
        water(box((n[0], n[1], NICHE_FLOOR), (n[2], n[3], MOAT_TOP), T('water_deep')), [], T('water_deep'), MOAT_TOP)
        K.keep_clear(e[0], e[1] - 128, e[2], e[1], 0)
        # glass balustrade along the causeway (low: you can still hop into the moat)
        gx = 156 * sx
        K.add(box((min(gx, gx + 4 * sx), MOAT[1], 0), (max(gx, gx + 4 * sx), MOAT[3], 36), T('glass')))
        K.speaker(sx * 420, -500, 40, 'ambient/water_rippling')
        # the secret: swim in behind the big waterfall
        K.secret((min(sx * 712, sx * 784), n[1] + 8, NICHE_FLOOR), (max(sx * 712, sx * 784), n[3] - 8, -8),
                 dest=(sx * 120, (VAULT[1] + VAULT[3]) / 2, VAULT_Z), angle=90 - 90 * sx + 180, name='niche_e' if sx > 0 else 'niche_w',
                 approach='w' if sx > 0 else 'e')
    t = TUNNEL
    water(box((t[0], t[1], MOAT_FLOOR), (t[2], t[3], TUNNEL_TOP), T('water_deep')), [], T('water_deep'), MOAT_TOP)   # fully submerged: no surface
    K.light(0, (t[1] + t[3]) / 2, -200, 200, '0.4 0.8 1')
    K.keep_clear(-160, MOAT[1] - 96, 160, MOAT[3] + 168, 0)                     # the causeway and both ends of it


def dive_shaft():
    """the 640u deep dive shaft in the lobby: structural shell below the slab, a round tiled liner, steps to a shelf"""
    x0, y0, x1, y1 = SHAFT
    st = {'top': T('deeptile'), 'side': T('deeptile'), 'bot': CAULK}
    K.add(box((x0 - 32, y0 - 32, SHAFT_FLOOR - 32), (x1 + 32, y1 + 32, SHAFT_FLOOR), st, detail=False),
          box((x0 - 32, y0 - 32, SHAFT_FLOOR), (x0, y1 + 32, SLAB), st, detail=False), box((x1, y0 - 32, SHAFT_FLOOR), (x1 + 32, y1 + 32, SLAB), st, detail=False),
          box((x0, y0 - 32, SHAFT_FLOOR), (x1, y0, SLAB), st, detail=False), box((x0, y1, SHAFT_FLOOR), (x1, y1 + 32, SLAB), st, detail=False))
    e = SHAFT_EXIT
    mouth = box((e[0], y0 - 8, SHELF), (e[2], y0 + 64, 8), CAULK)                # cut the liner where the shelf meets the shaft
    liner = carved(box((x0, y0, SHAFT_FLOOR), (x1, y1, 0), CAULK),
                   [cyl(BC[0], BC[1], SHAFT_R, SHAFT_FLOOR - 8, 8, CAULK, 16), mouth], {'top': T('paving'), 'side': T('pooltile'), 'bot': CAULK})
    K.add(liner)
    tl = {'top': T('pooltile'), 'side': T('pooltile'), 'bot': CAULK}
    steps = K.stairs16(e[0], e[1], e[2], e[1] + 96, SHELF, 0, 's', tl)
    water(box((x0, y0, SHAFT_FLOOR), (x1, y1, SHAFT_TOP), T('water_deep')), liner, T('water_deep'), SHAFT_TOP)
    water(box((e[0], e[1], SHELF), (e[2], e[3], SHAFT_TOP), T('water_deep')), steps, T('water_deep'), SHAFT_TOP)
    K.keep_clear(x0, y0, x1, y1, SHAFT_FLOOR, 96); K.keep_clear(e[0], e[1] - 112, e[2], e[1], 0)
    # the bubble at the bottom: straight up to the roof crest
    K.teleporter((BC[0] - 40, BC[1] - 40, SHAFT_FLOOR), (BC[0] + 40, BC[1] + 40, SHAFT_FLOOR + 56), dest=(0, BC[1] + 260, roof_top(0)),
                 angle=270, name='bubble')
    for (m, dx, dy, s) in (('pad_ddmix/padship/amphora.md3', -100, 60, 0.5), ('pad_ddmix/jail/skull.md3', 96, -84, 0.6),
                           ('pad_ddmix/chess/chess_white_king.md3', -70, -110, 1.6), ('pad_ddmix/plants/waterplant1b.md3', 20, 70, 0.5)):
        K.catalog(m, BC[0] + dx, BC[1] + dy, SHAFT_FLOOR, scale=s, clip=False, nudge=False)
    K.speaker(BC[0], BC[1], -200, 'machine/fishtank')


# ------------------------------------------------------------------------------------------------ cascade terraces
def terraces():
    """round stone pool terraces stepping down from the gallery level to the plaza on both sides. Each lower tier is
    carved by the higher ones and by the drum (no solid inside a solid); a thin sheet of water lies on every top."""
    stone = {'top': T('pooltile'), 'side': T('strata'), 'bot': T('strata')}
    drum_cut = prism(ngon16(DRUM_RO), -8, 600, CAULK)
    for sx in (1, -1):
        cut = [drum_cut]; tops = {}
        for (nm, cx, cy, r, z, flats) in TIERS:
            poly = lobe(cx, cy, r, flats, sx=sx)
            K.add(carved(prism(poly, 0, z, CAULK), cut, stone))
            tops[nm] = (poly, z, list(cut))
            cut.append(prism(poly, -8, 600, CAULK))
            xs_ = [p[0] for p in poly]; ys_ = [p[1] for p in poly]
            K.occupy(min(xs_), min(ys_), max(xs_), max(ys_), 0, z)
        on = {}
        for (nm, x0, y0, x1, y1, z0, z1, d) in TSTAIRS:
            r = mr((x0, y0, x1, y1), sx); d = d if sx > 0 or d in 'ns' else {'e': 'w', 'w': 'e'}[d]
            st = K.stairs16(r[0], r[1], r[2], r[3], z0, z1, d, {'top': T('pooltile'), 'side': T('strata')},
                            route=f'tier_{nm or "plaza"}_{"e" if sx > 0 else "w"}')
            on.setdefault(nm, []).extend(st)
            K.keep_clear(r[0] - 64, r[1] - 64, r[2] + 64, r[3] + 64, z0); K.keep_clear(r[0] - 64, r[1] - 64, r[2] + 64, r[3] + 64, z1)
            # a ribbon of falling water down the flight, and side falls on the big flats
            if nm:
                K.custom(ML.PLACE['fall_side'], (r[0] if sx > 0 else r[2]) - 40 * sx, r[3] - 3, z0 + 8, angle=0, lit=False)
                K.custom(ML.PLACE['fall_side'], (r[2] if sx > 0 else r[0]) + 40 * sx, r[3] - 3, z0 + 8, angle=0, lit=False)
        # roof pad on the top terrace (kept out of the water sheet)
        px, py = sx * ROOF_PAD[0], ROOF_PAD[1]
        on.setdefault('a', []).append(box((px - 40, py - 40, MEZZ_Z - 4), (px + 40, py + 40, MEZZ_Z + 12), CAULK))
        for nm, (poly, z, cutters) in tops.items():
            water(prism(poly, z, z + 8, T('water')), cutters + on.get(nm, []), T('water'), z + 8)
        K.jumppad(px, py, MEZZ_Z, land=(sx * ROOF_LAND[0], ROOF_LAND[1], roof_top(sx * ROOF_LAND[0])), apex=roof_top(sx * ROOF_X) + 190,
                  name='pad_roof_e' if sx > 0 else 'pad_roof_w', edges=[(sx * ROOF_X, BC[1], roof_top(sx * (ROOF_X - 4)))])
        # the big falls into the moat (the east/west one hides the secret niche)
        K.custom(ML.PLACE['fall_big'], sx * 676, -240, MOAT_TOP, angle=90 * sx, lit=False)
        K.custom(ML.PLACE['fall_mid'], sx * 676, -820, MOAT_TOP + (128 + 24 - 156), angle=90 * sx, lit=False)
        K.speaker(sx * 640, -200, 60, 'ambient/water_flowing'); K.speaker(sx * 1060, -560, 200, 'ambient/water_flowing')


# ------------------------------------------------------------------------------------------------ the dive centre
def building():
    cx, cy = BC
    # drum collision (the glass MD3 is the visual): 16 wall segments, openings at the doors
    for i in range(16):
        o0, o1 = face_pts(i, DRUM_RO); i0, i1 = face_pts(i, DRUM_RI)
        kind = FACE_KIND.get(i)
        for z0, z1 in ([(128, ROOF_BOT)] if kind == 'ground' else [(0, MEZZ_Z), (MEZZ_Z + 128, ROOF_BOT)] if kind == 'upper' else [(0, ROOF_BOT)]):
            pts = [(cx + p[0], cy + p[1], z) for p in (o0, o1, i0, i1) for z in (z0, z1)]
            b = hull(pts, WCLIP, round_pts=False); K.add(b); K.reserve(b)
    K.custom(ML.PLACE['drum'], cx, cy, 0, occupy=False)
    for a in (270, 90):                                   # ground doors south and north, 96u clear either side
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        K.keep_clear(cx + dx * 600 - 130, cy + dy * 600 - 130, cx + dx * 600 + 130, cy + dy * 600 + 130, 0)
        K.route('door_s' if a == 270 else 'door_n', (cx + dx * 720, cy + dy * 720, 0), (cx + dx * 552, cy + dy * 552, 0))
    for sx in (1, -1):
        K.keep_clear(cx + sx * 600 - 130, cy - 130, cx + sx * 600 + 130, cy + 130, MEZZ_Z)
        K.route('door_e' if sx > 0 else 'door_w', (cx + sx * 720, cy, MEZZ_Z), (cx + sx * 490, cy, MEZZ_Z))
    # gallery ring (z 256) with the atrium over the dive shaft and a stairwell on the north side
    mz = {'top': T('deck'), 'side': T('white'), 'bot': T('white')}
    ring = carved(prism(ngon16(DRUM_RI), MEZZ_Z - 16, MEZZ_Z, CAULK),
                  [prism(ngon16(400), 200, 300, CAULK), box((-300, cy + 280, 200), (256, cy + 600, 300), CAULK)], mz)
    K.add(ring)
    for b in ring: K.reserve(b)
    wt = {'top': T('deck'), 'side': T('white')}
    K.stairs16(-256, cy + 400, 256, cy + 520, 0, MEZZ_Z, 'e', wt, route='gallery_stairs')
    K.reserve(((-256, cy + 400, 0), (256, cy + 520, MEZZ_Z))); K.keep_clear(-380, cy + 392, -256, cy + 530, 0)
    K.keep_clear(-300, cy + 392, 256, cy + 600, MEZZ_Z - 16, MEZZ_Z + 120)          # nothing may overhang the stairwell
    # diving board from the south gallery out over the shaft
    K.add(box((-36, cy - 392, MEZZ_Z - 8), (36, cy - 130, MEZZ_Z), {'top': T('deck'), 'side': T('white'), 'bot': T('white')}))
    # shell roof: the MD3 is the visual; the walk surface is 32u strips that follow the wave (each step < 16u)
    n = int(2 * ROOF_X / 32)
    for i in range(n):
        xa, xb = -ROOF_X + 32 * i, -ROOF_X + 32 * (i + 1)
        wa, wb = max(roof_w(xa), 48), max(roof_w(xb), 48)
        K.add(prism([(cx + xa, cy - wa), (cx + xb, cy - wb), (cx + xb, cy + wb), (cx + xa, cy + wa)], ROOF_BOT, roof_top((xa + xb) / 2), WCLIP))
    K.custom(ML.PLACE['roof'], cx, cy, 0, occupy=False)
    K.occupy(cx - ROOF_X, cy - 700, cx + ROOF_X, cy + 700, ROOF_BOT, 760)
    # lobby furniture + the pad up to the gallery
    K.custom(ML.PLACE['desk'], cx - 250, cy - 250, 0, angle=315, **PM.CR['desk'])
    K.jumppad(cx + 236, cy - 170, 0, land=(cx + 490, cy - 120, MEZZ_Z), apex=MEZZ_Z + 164, name='pad_gallery', ceiling=ROOF_BOT,
              edges=[(cx + 392, cy - 136, MEZZ_Z)])
    K.trigger_sound((-60, cy + 180, roof_top(0)), (60, cy + 240, roof_top(0) + 64), 'human/applause', 'roof_applause', wait=20)


def vault():
    """sealed bonus room far below the plaza: both waterfall niches lead here; the exit drops you on the plaza"""
    x0, y0, x1, y1 = VAULT; z = VAULT_Z
    t = {'side': T('deeptile'), 'top': T('pooltile'), 'bot': T('white')}
    K.add(box((x0 - 32, y0 - 32, z - 32), (x1 + 32, y1 + 32, z), t, detail=False),
          box((x0 - 32, y0 - 32, z + 224), (x1 + 32, y1 + 32, z + 256), t, detail=False),
          box((x0 - 32, y0 - 32, z), (x0, y1 + 32, z + 224), t, detail=False), box((x1, y0 - 32, z), (x1 + 32, y1 + 32, z + 224), t, detail=False),
          box((x0, y0 - 32, z), (x1, y0, z + 224), t, detail=False), box((x0, y1, z), (x1, y1 + 32, z + 224), t, detail=False))
    cy = (y0 + y1) / 2
    K.item('item_padpower', 0, cy + 60, z); K.item('item_revival', -90, cy + 150, z); K.item('holdable_killerducks', 90, cy + 150, z)
    K.item('item_armor_padshield', 0, cy - 120, z)
    K.teleporter((-48, y1 - 56, z), (48, y1, z + 96), dest=(0, -1180, 0), angle=90, name='vault_exit')
    K.light(0, cy, z + 180, 450, '0.6 0.85 1')
    K.catalog('ente/padstatue_gold.md3', 0, y0 + 70, z, scale=0.6, angle=90, nudge=False)


# ------------------------------------------------------------------------------------------------ props
def props():
    cx, cy = BC
    # plaza: statue on its plinth, the sign wall, planters, loungers facing the building
    K.custom(ML.PLACE['plinth'], 0, -1560, 0, **PM.CR['plinth'])
    K.catalog('ente/padstatue_gold.md3', 0, -1560, 96, scale=0.9, angle=90, nudge=False, clip=False)
    K.add(box((-56, -1600, 96), (56, -1520, 300), WCLIP))
    K.add(box((-240, Y0 + 40, 0), (240, Y0 + 56, 40), {'top': T('strata'), 'side': T('strata'), 'bot': CAULK}),
          sign_box((-240, Y0 + 40, 40), (240, Y0 + 56, 160), T('sign_dive'), 512, 128, back=T('strata'), facing='n', edge=T('strata')))
    K.reserve(((-240, Y0 + 40, 0), (240, Y0 + 56, 160)))
    for (x, y) in ((420, -1380), (-420, -1380), (250, -1800), (-250, -1800), (560, -1700), (-560, -1700), (0, -1250),
                   (330, 120), (-330, 120), (420, 1420), (-420, 1420), (0, 1560)):
        p = K.prop(ML.PLACE['planter'], x, y, 0, angle=0, **PM.CR['planter'])
        if p: K.catalog('pad_ddmix/trashcan/bush.md3', p[0], p[1], 52, scale=0.42, nudge=False, clip=False)
    for sx in (1, -1):
        for k, x in enumerate((230, 350, 470)):
            K.prop(ML.PLACE['lounger'], sx * x, -1290 - 20 * k, 0, angle=270, **PM.CR['lounger'])
        for (x, y) in ((1300, 1050), (1620, 300)):
            K.prop(ML.PLACE['lounger'], sx * x, y, 0, angle=200 if sx > 0 else 340, **PM.CR['lounger'])
    # palms: lawns, plaza corners, the back garden
    for (x, y) in ((1700, -1680), (1780, -900), (1680, -300), (1780, 500), (1650, 1100), (1500, 1500), (900, 1520), (300, 1500),
                   (620, -1720), (1420, -1720), (700, 1380)):
        for sx in (1, -1):
            K.prop(ML.PLACE['palm'], sx * x, y, 0, lit=False, **PM.CR['palm'])
    # catalog greenery and pool toys
    for (x, y, m, s) in ((1780, -1300, 'pad_ddmix/plants/fern.md3', 0.28), (1900, -100, 'pad_ddmix/plants/flower_yellow.md3', 0.5),
                         (1750, 800, 'pad_ddmix/plants/fern.md3', 0.3), (1250, 1500, 'pad_ddmix/plants/flower_pink.md3', 0.6),
                         (1900, 1500, 'pad_ddmix/trashcan/tree_summer.md3', 0.9), (600, 1620, 'pad_ddmix/plants/flower_yellow.md3', 0.5),
                         (1100, 1380, 'pad_ddmix/trashcan/bush.md3', 0.6), (1600, -700, 'pad_ddmix/trashcan/bush.md3', 0.6)):
        for sx in (1, -1):
            K.catalog(m, sx * x, y, 0, scale=s, lit=(m.endswith('tree_summer.md3')), clip=m.endswith(('tree_summer.md3', 'bush.md3')))
    for sx in (1, -1):                                   # rubber ducks and lilies standing in the shallow terraces
        for (x, y, z, m, s) in ((1250, 760, 256, 'pad_ducks/pad_duck.md3', 0.3), (1300, -260, 192, 'ente/ducka.md3', 1.6),
                                (860, -900, 128, 'pad_ducks/pad_duck.md3', 0.22), (1200, -1500, 64, 'ente/duckb.md3', 1.6),
                                (860, 300, 256, 'pad_ddmix/plants/water_lily.md3', 0.4), (1180, -960, 128, 'pad_ddmix/plants/water_lily.md3', 0.4),
                                (960, -1560, 64, 'pad_ddmix/plants/water_lily.md3', 0.35)):
            K.catalog(m, sx * x, y, z, scale=s, clip=False, nudge=False)
    # gallery: loungers and towels with a view
    for sx in (1, -1):
        K.prop(ML.PLACE['lounger'], cx + sx * 330, cy + 370, MEZZ_Z, angle=90 + sx * 40, **PM.CR['lounger'])
        K.catalog('pad_items/towelstack.md3', cx + sx * 480, cy - 250, MEZZ_Z, scale=1.2, clip=False)


# ------------------------------------------------------------------------------------------------ items
def items():
    cx, cy = BC
    K.weapon('imperius', 0, cy, roof_top(0), marker='purple')                      # roof crest: pads or the shaft bubble
    K.weapon('betty', 96, cy + 40, SHAFT_FLOOR, marker='black')                    # bottom of the dive shaft
    K.weapon('balloony', 0, -496, MOAT_FLOOR, marker='orange')                     # middle of the swim-through tunnel
    K.weapon('pumper', 1250, 420, 256, marker='green')                             # east top terrace
    K.weapon('splasher', -420, -500, MOAT_FLOOR, marker='blue')                    # bottom of the west moat
    K.weapon('boaster', 0, 170, 0, marker='orange')                                # lobby, inside the front door
    K.weapon('bubbleg', 0, -1000, 0, marker='green')                               # plaza end of the causeway
    ammo = {'imperius': [(-700, cy, roof_top(-700)), (0, cy - 330, 0), (1620, 1300, 0)],
            'betty': [(-380, cy + 250, 0), (420, -500, MOAT_FLOOR), (-1700, -1500, 0), (cx + 500, cy + 130, MEZZ_Z)],
            'balloony': [(cx - 500, cy + 60, MEZZ_Z), (1060, -1400, 64), (0, 1450, 0), (-1250, 420, 256)],
            'pumper': [(1060, -200, 192), (0, cy - 500, MEZZ_Z), (760, -1750, 0)],
            'splasher': [(-420, -940, SHELF), (420, -260, MOAT_FLOOR), (-1750, 600, 0), (0, cy - 240, SHELF)],
            'boaster': [(-1060, -1400, 64), (-1060, -820, 128), (1060, -820, 128), (-1000, 1420, 0)],
            'bubbleg': [(0, -400, 0), (-700, -1250, 0), (1750, -1250, 0), (320, cy + 300, 0)]}
    for w, spots in ammo.items():
        for (x, y, z) in spots: K.ammo(w, x, y, z)
    for (x, y, z) in ((0, -700, 0), (cx + 420, cy - 330, 0), (-1400, 1420, 0), (1560, -1560, 0)): K.ammo('nipper', x, y, z)
    K.item('item_armor_padshield', 700, cy, roof_top(700)); K.item('item_speedy', 0, 1700, 0)
    K.item('item_jumper', -1250, 620, 256); K.item('holdable_floater', -300, cy - 420, 0)
    K.item('item_armor_shard', -1060, -200, 192); K.item('item_armor_shard', 1250, -1450, 64); K.item('item_armor_shard', 0, cy + 480, MEZZ_Z)
    K.item('item_climber', 1800, 100, 0); K.item('item_visionless', -1800, 100, 0)
    K.station(-1250, -1880, 0, ang=90); K.station(1250, 1560, 0, ang=270)
    for (x, y, z, a) in ((0, -1820, 0, 90), (-900, -1700, 0, 45), (900, -1700, 0, 135), (-1850, -1850, 0, 45), (1850, -1850, 0, 135),
                         (-1800, 900, 0, 0), (1800, 900, 0, 180), (-800, 1600, 0, 315), (800, 1600, 0, 225), (0, 1350, 0, 270),
                         (-400, cy - 100, 0, 0), (400, cy + 100, 0, 180), (-520, cy - 150, MEZZ_Z, 0), (1100, 300, 256, 180),
                         (-1100, 300, 256, 0), (1060, -900, 128, 90), (-1060, -300, 192, 90)):
        K.spawn(x, y, z, a)


def lights():
    cx, cy = BC
    for a in range(0, 360, 60):                           # warm gold glow inside, like the photo
        K.light(cx + 480 * math.cos(math.radians(a)), cy + 480 * math.sin(math.radians(a)), 470, 460, '1 0.78 0.42')
    for a in range(30, 360, 90): K.light(cx + 380 * math.cos(math.radians(a)), cy + 380 * math.sin(math.radians(a)), 150, 300, '1 0.8 0.5')
    K.light(cx, cy, 380, 500, '1 0.8 0.45')
    for z in (-120, -360, -560): K.light(cx, cy, z, 320, '0.5 0.8 1')
    for sx in (1, -1):
        for y in (-300, -700): K.light(sx * 420, y, -140, 300, '0.45 0.7 1')
        K.light(sx * 736, -200, -30, 120, '0.5 0.8 1')
        for (x, y, z) in ((1060, -480, 230), (1060, -1080, 170), (1060, -1300, 110), (700, -1400, 90), (1000, 150, 300)):
            K.light(sx * x, y, z, 200, '1 0.8 0.55')
    K.timer_sound(0, -1500, 300, 'animal/blackbird', 'birds', 25, 12)


def shader():
    TX.write_shader(extra=[SH.sky(f'env/{NS}/sunset', sun=(140, 24), sun_rgb=(1, 0.74, 0.52), sun_int=150, skylight=(95, 3))],
                    arena_types=INFO.get('arena_types', 'ffa lps team ft syc_ffa'), ents={e['classname'] for e in K.M.ents})


if __name__ == '__main__':
    textures()
    PM.build(TX)                      # every MD3 (and its shaders) BEFORE the shader file is written
    ground(); moats(); dive_shaft(); terraces(); building(); vault()
    props(); items(); lights()
    K.fix_items()
    shader()
    K.write(OUT, routes_path=os.path.join(HERE, 'routes.txt'))
