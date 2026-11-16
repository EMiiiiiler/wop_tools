"""Skull Rock Bay XL: Smuggler's Isle south of the park, built with woplib on top of the original pplib generator.

build_pirate.main() calls pp_xl.setup(G) right after the original island is built and pp_xl.finish(G) instead of its
own .map/routes writer. A woplib MapKit shares the pirate's wopmap.Map (K.M = M), so every woplib helper (water_box,
stairs16, jumppad, current, fake_wall, glass_arch, flume, shopbits ...) writes into the same map, and K.write() emits
the .map plus spots.json/routes with the original island's pads, items and routes merged in. New textures and models
live in their own namespace (`piratexl`, scripts/piratexl.shader) so the pirate's own shader file is left alone.

    y -2048  park's south quay; the Long Pier carries the galleon's south jetty on across the sea
    y -2560  +------------------------ Smuggler's Isle ------------------------+
             | Fish Shack   Map Shop   [harbour square]   Sail Loft   (P4 pool)|  Port Town
             | (stairwell)                                                    |
             |    SHIPWRECK REEF lagoon            SMUGGLER'S RAPIDS          |
             |    (tilted wreck; reef tank +       P3 (cave under it)         |
             |     glass tunnel under it ->        P2                         |
             |     Davy Jones' Locker)             P1                         |
             |                                     hill plateau + LIGHTHOUSE  |
    y -5120  +----------------------------------------------------------------+
            x -2048                                                      x 2048
"""
import os, sys, math
import numpy as np
from wopmap import box, cyl, hull, sub_rects, sign_box, prism, ngon
import wopmap
from woplib.kit import MapKit, CAULK, WCLIP
from woplib import models as ML, shaders as SH, texlib as TL, shopbits as SB, padmath
from meshlib import Mesh, revolve, rbox, tube, ellipsoid, sphere

NS = 'piratexl'
ISLE = (-2048.0, -5120.0, 2048.0, -2560.0)
PIER = (-160.0, -2560.0, 160.0, -2048.0)
SKY_Y0 = -5760
ZB = -896                                    # sea bed / sky floor
WATER = -16
PT = lambda n: 'padpirate/' + n              # the original map's brush textures

# Shipwreck Reef ---------------------------------------------------------------------------------------------------
LAG = (-1600.0, -4500.0, -200.0, -3100.0)    # lagoon; beach ramp on the north from y -3100 (z 0) to -3600 (z -176)
LAG_RAMP_Y = -3600.0
LAG_Z = -176.0
TANK = (-1450.0, -4350.0, -350.0, -3850.0)   # reef tank under the deep part: z -608 .. -192 (the floor above is glass)
TANK_Z = (-608.0, -192.0)
TY = -4100.0                                 # tunnel axis (y); walk floor -432
TFLOOR = -432.0
TW = 64.0                                    # tunnel interior half width
HOLE = (-2000.0, TY - TW, -1744.0, TY + TW)  # stairwell opening in the ground west of the lagoon
LOCKER = (0.0, TY - 200.0, 448.0, TY + 200.0)   # Davy Jones' Locker (z -432 .. -176), east of the tank
WRECK = (-1300.0, -4450.0, -750.0, -4200.0)  # tilted stern section: deck z 0 (east) -> 176 (west)
# Smuggler's Rapids ----------------------------------------------------------------------------------------------------
CH = (900.0, 1180.0)                         # channel x; banks 680..900 and 1180..1400
BX = (680.0, 1400.0)
POOLS = [(-4700.0, -4200.0, 440.0), (-4200.0, -3700.0, 312.0), (-3700.0, -3250.0, 184.0)]   # (y0, y1, water); bank = W+8
P4 = (840.0, -3200.0, 1250.0, -2960.0)       # splash pool at the bottom (water -16, 32 deep)
LEDGE_Y = (-3250.0, -3200.0)                 # ground ledge in front of the cave mouth
CAVE = (820.0, -3550.0, 1260.0, -3250.0)     # smugglers' cave inside the third tier, z 0 .. 120
PLATEAU = (600.0, -5100.0, 1500.0, -4700.0)  # hill top, z 448
LH = (1050.0, -4900.0)                       # lighthouse
LH_R, LH_ROOM, LH_TOP = 112.0, 144.0, 960.0  # tower apothem, ground room height, gallery walk
GAL_R = 208.0
# Port Town ----------------------------------------------------------------------------------------------------------
SQUARE = (-700.0, -3000.0, 700.0, -2560.0)
FISH = (-1300.0, -3000.0, -940.0, -2700.0); FISH_H = 192
MAPS = (-780.0, -3000.0, -440.0, -2700.0); MAPS_H = 192
LOFT = (380.0, -3040.0, 760.0, -2700.0); LOFT_H = 256
CANNON_PERIOD = 45


# ======================================================================================================== textures
def tex_reef(n=256):
    x, y = ML.xy(n)
    c = ML.lerp(ML.C((70, 150, 150)), ML.C((200, 180, 140)), np.clip(ML.noise(n, 18, 5) * 1.5 + 0.5, 0, 1)[..., None])
    spots = np.clip(ML.noise(n, 3, 9) * 3 - 1.2, 0, 1)
    return c * (1 - 0.25 * spots[..., None]) + ML.N3(n, 2, 11, 8)


def tex_fish_hang(n=128):
    x, y = ML.xy(n)
    c = ML.lerp(ML.C((90, 120, 150)), ML.C((210, 220, 225)), y[..., None]) + ML.N3(n, 1, 13, 6)
    c = np.where(((np.abs(x - 0.5) < 0.04) & (y < 0.3))[..., None], ML.C((40, 50, 60)), c)
    return c


def tex_band(c1, c2, n=128):
    """lighthouse paint: c1 below, c2 above the middle (planar v runs down the wall -> bands by world z)"""
    x, y = ML.xy(n)
    return np.where((y < 0.5)[..., None], ML.C(c2), ML.C(c1)) + ML.N3(n, 2, 17, 5)


def tex_smoke(n=64):
    x, y = ML.xy(n)
    d = np.hypot(x - 0.5, y - 0.5) * 2
    v = np.clip(1 - d, 0, 1) ** 1.5 * np.clip(0.6 + ML.noise(n, 6, 19), 0, 1)
    return np.repeat((v * 150)[..., None], 3, 2)


def tex_flash(n=64):
    x, y = ML.xy(n)
    d = np.hypot(x - 0.5, y - 0.5) * 2
    v = np.clip(1 - d, 0, 1) ** 2
    return ML.lerp(ML.C((255, 120, 20)), ML.C((255, 240, 160)), v[..., None]) * v[..., None]


def tex_beam(n=64):
    x, y = ML.xy(n)
    v = np.clip(1 - np.abs(y - 0.5) * 2, 0, 1) ** 2 * np.clip(1 - x, 0, 1)
    return np.repeat((v * 120)[..., None], 3, 2) * np.array([1, 0.95, 0.75])


def textures(TX):
    TX.add('reef', tex_reef(), scale=1.0)
    TX.add('reefglass', TL.solid((150, 210, 230), 3, 7, 64), 'glass', rgb='0.08 0.12 0.14', shadow=False)
    TX.add('reeffog', TL.solid((40, 110, 150), 2, 9, 64), 'fog', rgb=(0.08, 0.30, 0.42), dist=1200)
    TX.add('fakewall', TL.solid((140, 120, 96), 2, 1, 64), 'raw', check_tile=False,
           shader=SH.fake_wall('fakewall', 'textures/padpirate/rock'))
    TX.add('slick_nd', TL.solid((200, 120, 220), 2, 5, 64), 'raw', shader=(
        f'textures/{NS}/slick_nd\n{{\n\tqer_editorimage textures/{NS}/slick_nd\n\tqer_trans 0.5\n\tsurfaceparm slick\n'
        '\tsurfaceparm nodraw\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n}\n\n'))
    TX.add('sign_locker', TL.label("DAVY JONES' LOCKER", 1024, 128, (30, 40, 50), (120, 230, 220), border=(120, 230, 220)), 'sign', check_tile=False)
    TX.add('sign_reef', TL.label('SHIPWRECK REEF', 512, 128, (60, 40, 24), (250, 220, 140), border=(250, 220, 140)), 'sign', check_tile=False)
    TX.add('sign_rapids', TL.label("SMUGGLER'S RAPIDS", 1024, 128, (60, 40, 24), (250, 220, 140), border=(250, 220, 140)), 'sign', check_tile=False)
    TX.add('sign_fish', TL.label('FRESH FISH', 512, 128, (40, 110, 160), (250, 250, 240), border=(250, 250, 240)), 'sign', check_tile=False)
    TX.add('sign_maps', TL.label('TREASURE MAPS', 512, 128, (40, 90, 50), (250, 230, 160), border=(250, 230, 160)), 'sign', check_tile=False)
    TX.add('sign_loft', TL.label('SAIL & ROPE', 512, 128, (120, 40, 30), (250, 240, 220), border=(250, 240, 220)), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 200, 90))
    m = TX.material
    m('reef_m', tex_reef(), shade=40)
    m('rock_m', TL.stone((150, 132, 110), cells=10, vary=22), shade=40)
    m('sandrock', TL.stone((200, 176, 132), cells=12, vary=16), shade=40, steps='sandsteps')
    m('planks_m', TL.planks((160, 120, 80)), shade=30, steps='woodsteps')
    m('oldwood', TL.planks((96, 80, 64)), shade=30, steps='woodsteps')
    m('rope', TL.stripes((190, 160, 110), (150, 120, 80), 12, soft=0.5), shade=40)
    m('steel', TL.metal((150, 150, 156)), 'lms', v=0.15)
    m('brass', TL.metal((200, 160, 70)), 'lms', v=0.3)
    m('glass', TL.solid((150, 220, 240), 4, 3, 64), 'glass')
    m('canvas', TL.fabric((236, 226, 200)), two=True, shade=60)
    m('sail_r', TL.stripes((200, 60, 50), (236, 226, 200), 3), two=True, shade=60)
    m('canopy_b', TL.stripes((40, 110, 170), (245, 245, 235), 4), two=True, shade=60)
    m('canopy_g', TL.stripes((40, 120, 60), (245, 240, 215), 4), two=True, shade=60)
    m('canopy_r', TL.stripes((180, 50, 40), (245, 240, 215), 4), two=True, shade=60)
    m('trim_w', TL.solid((240, 236, 226), 3, 31, 64), shade=30)
    m('wall_blue', TL.stripes((90, 140, 170), (80, 126, 156), 14, vertical=False, soft=0.15), shade=30)
    m('wall_green', TL.stripes((110, 150, 110), (96, 136, 98), 14, vertical=False, soft=0.15), shade=30)
    m('wall_ochre', TL.stripes((200, 160, 100), (186, 146, 90), 14, vertical=False, soft=0.15), shade=30)
    m('roof_m', TL.tiles((150, 80, 60), (110, 60, 44), cols=6, rows=10, offset=0.5), shade=30)
    m('lh_red', tex_band((200, 40, 40), (200, 40, 40)), shade=30)
    m('lh_white', tex_band((240, 240, 236), (240, 240, 236)), shade=30)
    m('fish', tex_fish_hang(), shade=60)
    m('shark', TL.stripes((110, 124, 136), (150, 162, 172), 3, vertical=False, soft=0.8), 'dyn')
    fl, fa = _fall(); m('fall', fl, 'flow', alpha=fa)
    m('smoke', tex_smoke(), 'add', wave=SH.timer_pulse(CANNON_PERIOD, 0.2))
    m('flash', tex_flash(), 'add', wave=SH.timer_pulse(CANNON_PERIOD, 0.035))
    m('beam', tex_beam(), 'add')
    m('lamp', TL.solid((255, 236, 170), 2, 42, 32), 'glow')
    m('mapboard', TL.label('X MARKS THE SPOT', 256, 256, (220, 196, 140), (110, 50, 30), border=(110, 50, 30)))
    m('globe', TL.stripes((60, 120, 190), (90, 160, 90), 6, soft=0.9), 'lms', v=0.2)
    m('coins', TL.solid((240, 200, 60), 6, 3, 64), 'lms', v=0.4)


def _fall(n=128):
    x, y = ML.xy(n)
    st = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 9 + np.sin(y * 2 * math.pi * 2) * 1.5)
    c = ML.lerp(ML.C((150, 215, 240)), ML.C((250, 255, 255)), st[..., None])
    a = np.clip(120 + st * 110 + ML.noise(n, 3, 6) * 40, 0, 255).astype(np.uint8)
    return c, a


# ======================================================================================================== setup
def setup(G):
    """woplib kit sharing the pirate map; textures/models in the piratexl namespace"""
    global K, T, TX, M, G_
    G_ = G
    M = G['M']
    K = MapKit(G['MAPNAME'], NS, G['TX'].LONGNAME, (-2304, -5120, 2304, 2048))
    K.M = M
    T = K.T
    out = G['OUT']
    ML.configure(NS, out); SH.configure(NS, G['MAPNAME'], G['TX'].LONGNAME)
    TX = TL.Textures(K)
    # the original island's occupancy (props, items, keep-outs) so nothing new lands on it
    for (x, y, r) in G['KEEP_OUT']: K.occupy_r(x, y, r, -64, 400)
    for r in G['NOGO']: K.occupy(r[0], r[1], r[2], r[3], -64, 400)
    K.reserve(((-2304, -2048, -900), (2304, 2048, -1)))           # the original slab: nothing new goes under it
    textures(TX)
    return K


# ======================================================================================================== the isle
def isle_ground():
    """one big detail block for the isle (sea bed to z 0) carved by the lagoon, the reef tank + tunnel + stairwell,
    Davy Jones' Locker and the splash pool; faces textured by where they are"""
    x0, y0, x1, y1 = ISLE
    dz = 1.0
    cuts = [box((LAG[0], LAG[1], LAG_Z), (LAG[2], LAG[3], 1), CAULK),                                  # lagoon basin
            box((TANK[0], TANK[1], TANK_Z[0]), (TANK[2], TANK[3], TANK_Z[1] + 16), CAULK),           # tank (+ glass slot)
            box((HOLE[0], HOLE[1], TFLOOR), (HOLE[2], HOLE[3], 1), CAULK),                           # stairwell opening
            box((HOLE[2], HOLE[1], TFLOOR), (LAG[0] - 16, HOLE[3], -32), CAULK),                      # stairwell under the ground
            box((LAG[0] - 16, HOLE[1], TFLOOR), (TANK[0] - 80, HOLE[3], -208), CAULK),               # ... and under the lagoon
            box((TANK[0] - 80, HOLE[1], TFLOOR), (TANK[0], HOLE[3], TFLOOR + 128), CAULK),           # its mouth = the tunnel's size
            box((TANK[2], TY - TW, TFLOOR), (LOCKER[0], TY + TW, TFLOOR + 128), CAULK),               # corridor to the locker
            box((LOCKER[0], LOCKER[1], TFLOOR), (LOCKER[2], LOCKER[3], -176), CAULK),
            box((P4[0], P4[1], WATER - 32), (P4[2], P4[3], 1), CAULK)]
    big = box((x0, y0, ZB), (x1, y1, 0), CAULK)
    pieces = wopmap.carve(big, cuts)
    tank_in = lambda p: TANK[0] - 1 <= p[0] <= TANK[2] + 1 and TANK[1] - 1 <= p[1] <= TANK[3] + 1 and p[2] < TANK_Z[1] + 1
    lag_in = lambda p: LAG[0] - 1 <= p[0] <= LAG[2] + 1 and LAG[1] - 1 <= p[1] <= LAG[3] + 1 and p[2] >= LAG_Z - 1
    under = lambda p: p[2] < -40
    for b in pieces:
        V = b.verts()
        for f in b.faces:
            on = G_['face_pts'](b, f, V); c = on.mean(0); n = np.array(f.n)
            if n[2] > 0.9 and abs(c[2]) < 0.5:
                sq = SQUARE[0] <= c[0] <= SQUARE[2] and SQUARE[1] <= c[1] <= SQUARE[3]
                f.tex = PT('cobbles') if sq else PT('sand')
            elif lag_in(c) or (P4[0] - 1 <= c[0] <= P4[2] + 1 and P4[1] - 1 <= c[1] <= P4[3] + 1 and c[2] > -60):
                f.tex = T('reef') if lag_in(c) else PT('pool_tile')
            elif tank_in(c): f.tex = T('reef')
            elif under(c) or n[2] < -0.5: f.tex = PT('rock')
            elif abs(n[2]) < 0.1 and (abs(c[0] - x0) < 1 or abs(c[0] - x1) < 1 or abs(c[1] - y0) < 1 or abs(c[1] - y1) < 1):
                f.tex = PT('quay')
            else: f.tex = PT('rock')
            f.sc = wopmap.default_scale(f.tex)
        K.add(b)
    # glass panel over the tank (the lagoon floor you can see through)
    K.add(box((TANK[0], TANK[1], TANK_Z[1]), (TANK[2], TANK[3], LAG_Z), T('reefglass')))
    # player clip all round the isle and both sides of the pier; the park's south clip gets a gap (build_pirate)
    zt = G_['L'].SKY['z1']
    for r in sub_rects((x0 - 16, y0 - 16, x1 + 16, y1 + 16), [ISLE]):
        if r[1] >= y1 - 1 and r[0] < PIER[2] and r[2] > PIER[0]:                    # the pier gap in the north clip
            for rr in sub_rects(r, [(PIER[0], y1 - 1, PIER[2], y1 + 17)]): K.add(box((rr[0], rr[1], 0), (rr[2], rr[3], zt), G_['CLIP']))
            continue
        K.add(box((r[0], r[1], 0), (r[2], r[3], zt), G_['CLIP']))
    K.reserve(((x0 - 16, y0 - 16, -1000), (x0, y1 + 16, 3000)), ((x1, y0 - 16, -1000), (x1 + 16, y1 + 16, 3000)),
              ((x0, y0 - 16, -1000), (x1, y0, 3000)), ((x0, y1, -1000), (x1, y1 + 16, 3000)))


def pier():
    """the Long Pier: carries the galleon's south jetty on across the sea to the isle; rope rails on posts, lamps"""
    Mt = TX.mats
    x0, y0, x1, y1 = PIER
    K.add(box((x0, y0, -16), (x1, y1, 0), {'top': PT('boardwalk'), 'side': PT('planks'), 'bot': PT('planks')}))
    zt = G_['L'].SKY['z1']
    for x in (x0 - 16, x1):
        K.add(box((x, y0 + 16, 0), (x + 16, y1, zt), G_['CLIP']))
    D = SB.Dress(K, 'pier_dress', (0, (y0 + y1) / 2, -16))
    for y in np.arange(y0 + 16, y1, 96):
        for x in (x0 - 12, x1 + 12):                                            # pilings beside the deck, sea bed up
            tube(D.mesh(Mt['oldwood']), [(x, y, ZB + 1), (x, y, -17)], 9, nseg=8)
        for x in (x0 + 8, x1 - 8):                                              # rail posts standing on the deck
            tube(D.mesh(Mt['oldwood']), [(x, y, 0), (x, y, 44)], 5, nseg=6)
    for x in (x0 + 8, x1 - 8):
        ys = np.arange(y0 + 16, y1, 96)
        for ya, yb in zip(ys[:-1], ys[1:]):
            rope = [(x, ya + (yb - ya) * t, 38 - 9 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 7)]
            tube(D.mesh(Mt['rope']), rope, 2.2, nseg=5, caps=(False, False))
    D.finish()
    for y in (y0 + 120, y0 + 330):
        G_['custom']('lantern_post', x1 - 30, y, 0, 0); K.add(box((x1 - 36, y - 6, 0), (x1 - 24, y + 6, 150), WCLIP))
        K.light(x1 - 40, y, 140, 160, '1 0.8 0.5')
    K.route('long_pier', (0, -1980, 0), (0, y0 - 160, 0))


# ------------------------------------------------------------------------------------------------ Shipwreck Reef
def reef():
    Mt = TX.mats
    lx0, ly0, lx1, ly1 = LAG
    # beach ramp on the north, the wreck in the deep part, the water
    ramp = K.ramp(lx0, LAG_RAMP_Y, lx1, ly1, LAG_Z, 0, 'n', {'top': PT('wet_sand'), 'side': T('reef'), 'bot': CAULK}, base=LAG_Z)
    K.reserve(ramp)
    wx0, wy0, wx1, wy1 = WRECK
    wreck = hull([(wx1, wy0, LAG_Z), (wx1, wy1, LAG_Z), (wx0, wy0, LAG_Z), (wx0, wy1, LAG_Z),
                  (wx1, wy0 + 20, 0), (wx1, wy1 - 20, 0), (wx0, wy0 + 20, 176), (wx0, wy1 - 20, 176)], CAULK, round_pts=False)
    K.solid_piece('wreck_stern', [wreck], TX.texfn('oldwood', 'oldwood'))
    X = ML.Model()                                          # ribs, a broken mast and a torn sail on the wreck
    for k in range(5):
        x = wx0 + 60 + k * 100
        zd = 176 * (wx1 - x) / (wx1 - wx0)
        for s in (-1, 1):
            tube(X.mesh(Mt['oldwood']), [(x, (wy0 + wy1) / 2 + s * 105, zd + 2), (x + 10, (wy0 + wy1) / 2 + s * 112, zd + 60 + 10 * k)], 6, nseg=6)
    mx, my = wx0 + 120, (wy0 + wy1) / 2
    mz = 176 * (wx1 - mx) / (wx1 - wx0)
    tube(X.mesh(Mt['oldwood']), [(mx, my, mz + 1), (mx - 40, my, mz + 280)], [14, 10], nseg=10)
    sail = Mt['sail_r']
    X.mesh(sail).poly([(mx - 8, my - 4, mz + 120), (mx - 30, my - 4, mz + 260), (mx - 30, my + 120, mz + 210), (mx - 10, my + 90, mz + 110)],
                      (0, -1, 0), [(0, 1), (0, 0), (1, 0.2), (1, 1)])
    K.custom(ML.save('wreck_bits', X), 0, 0, 0, occupy=False, _structure=1)
    K.weapon('balloony', wx0 + 70, (wy0 + wy1) / 2, 176 * (wx1 - (wx0 + 70)) / (wx1 - wx0) + 4, marker='orange')
    K.route('wreck_deck', (wx1 - 30, (wy0 + wy1) / 2, 2), (wx0 + 150, (wy0 + wy1) / 2, 176 * (wx1 - wx0 - 150) / (wx1 - wx0)))
    K.reserve(((lx0, ly0, LAG_Z), (lx1, ly1, 0)))
    K.water_box((lx0, ly0, LAG_Z), (lx1, ly1, WATER), PT('water'), nodraw_tex=PT('water_nodraw'), cutters=[ramp, wreck])
    for (x, y) in ((lx0 + 60, ly1 - 40), (lx1 - 60, ly1 - 40)):
        G_['custom']('torch_post', x, y + 140, 0, 0); K.add(box((x - 6, y + 134, 0), (x + 6, y + 146, 130), WCLIP))
    K.speaker((lx0 + lx1) / 2, (ly0 + ly1) / 2, 20, 'ambient/water_rippling')
    # the tank: fog round the tunnel, sharks, the sunken bow
    tx0, ty0, tx1, ty1 = TANK; zb, zt = TANK_Z
    AW, ATOP = 84, TFLOOR + 157
    iy0, iy1 = TY - TW, TY + TW
    K.add(box((tx0, TY - AW + 4, TFLOOR - 16), (tx1, TY + AW - 4, TFLOOR), {'top': PT('deck'), 'side': PT('planks'), 'bot': PT('planks')}),
          box((tx0, iy0 - 8, TFLOOR), (tx1, iy0, TFLOOR + 102), WCLIP), box((tx0, iy1, TFLOOR), (tx1, iy1 + 8, TFLOOR + 102), WCLIP),
          box((tx0, TY - 46, ATOP - 22), (tx1, TY + 46, ATOP - 14), WCLIP))
    K.reserve(((tx0, TY - AW, TFLOOR - 16), (tx1, TY + AW, ATOP)))
    mid = (tx0 + tx1) / 2
    for i, (a, b) in enumerate(((tx0, mid), (mid, tx1))):
        X = ML.Model(); c = (a + b) / 2
        ML.glass_arch(X, a - c, b - c, AW, 0, ATOP - TFLOOR, Mt['glass'], Mt['brass'])
        K.custom(ML.save(f'reef_tube{i}', X), c, TY, TFLOOR, lit=False, occupy=False, _structure=1)
    g = 12
    for (mn, mx) in (((tx0, ty0, zb), (tx1, TY - AW - g, zt)), ((tx0, TY + AW + g, zb), (tx1, ty1, zt)),
                     ((tx0, TY - AW - g, ATOP + g), (tx1, TY + AW + g, zt)),
                     ((tx0, TY - AW - g, zb), (tx1, TY + AW + g, TFLOOR - 16 - g))):
        K.add(box(mn, mx, T('reeffog')))
    X = ML.Model(); R0 = 150
    for k in range(3):
        a = 2 * math.pi * k / 3
        t = np.array([0, -math.sin(a), math.cos(a)]); r = np.array([0, math.cos(a), math.sin(a)])
        Rm = np.stack([t, [1.0, 0, 0], r], 1); c = r * R0
        ellipsoid(X.mesh(Mt['shark']), c, 46, 13, 15, nu=12, nv=8, R=Rm)
        for pts in (((8, 0, 10), (-14, 0, 10), (-10, 0, 34)), ((-40, 0, 0), (-62, 0, 20), (-60, 0, -16)),
                    ((10, 6, -6), (-6, 6, -6), (-4, 26, -16)), ((10, -6, -6), (-6, -6, -6), (-4, -26, -16))):
            P = [c + Rm @ np.array(q, float) for q in pts]
            nn = np.cross(P[1] - P[0], P[2] - P[0]); nn /= np.linalg.norm(nn)
            X.mesh(Mt['shark']).poly(P, nn, [(0, 0), (1, 0), (0.5, 1)]); X.mesh(Mt['shark']).poly(P[::-1], -nn, [(0.5, 1), (1, 0), (0, 0)])
    sh = ML.save('reef_sharks', X)
    assert abs(sh[2]) < 1e-6
    for i, x in enumerate((tx0 + 260, tx1 - 260)):
        K.rotating_model2(sh[0], (x, TY, TY * 0 + TFLOOR + 72), speed=15 + 5 * i, axis='x', reverse=bool(i))
    # sunken bow on the tank floor (seen through the glass), plants, light
    X = ML.Model()
    bow = hull([(0, -70, 0), (0, 70, 0), (260, -60, 0), (260, 60, 0), (330, 0, 0), (0, -80, 110), (0, 80, 110), (260, -70, 120),
                (260, 70, 120), (360, 0, 130)], CAULK, round_pts=False)
    ML.solids_mesh(X, [bow], lambda c, n, p: (Mt['oldwood'], ML.planar_uv(n, 128)))
    K.custom(ML.save('sunken_bow', X), tx0 + 90, ty0 + 110, zb, angle=0, occupy=False)
    for x in range(int(tx0) + 140, int(tx1) - 60, 230):
        K.catalog('pad_ddmix/plants/waterplant1a.md3', x, ty1 - 70, zb, scale=0.5, clip=False, nudge=False)
    G_['custom']('chest_open', mid + 120, ty1 - 80, zb, 200)
    for x in range(int(tx0) + 200, int(tx1), 420):
        K.light(x, TY, TFLOOR + 110, 220, '0.6 0.9 1')
        for y in (ty0 + 60, ty1 - 60): K.light(x + 100, y, zb + 120, 240, '0.3 0.7 1')
    K.speaker(mid, TY, TFLOOR + 64, 'machine/fishtank')
    K.route('reef_tunnel', (tx0 + 40, TY, TFLOOR), (LOCKER[0] + 60, TY, TFLOOR))
    # stairwell from the ground west of the lagoon
    hx0, hy0, hx1, hy1 = HOLE
    STAIRS(hx0, hy0, tx0 - 64, hy1, TFLOOR, 0, 'w', {'top': PT('planks'), 'side': PT('rock'), 'bot': PT('rock')})
    K.keep_clear(hx0, hy0 - 112, hx1 + 112, hy0, 0); K.keep_clear(hx0, hy1, hx1 + 112, hy1 + 112, 0)
    K.route('reef_stairs', (tx0 - 40, TY, TFLOOR), (hx0 + 120, hy1 + 60, 0))
    for x in (hx0 + 200, hx0 + 450): K.light(x, TY, -110, 240, '1 0.85 0.6')
    D = SB.Dress(K, 'reef_hut', ((hx0 + hx1) / 2, TY, 0))                # a little thatched kiosk roof over the hole
    for (x, y) in ((hx0 - 20, hy0 - 40), (hx0 - 20, hy1 + 40), (hx1 + 40, hy0 - 40), (hx1 + 40, hy1 + 40)):
        tube(D.mesh(Mt['oldwood']), [(x, y, 0), (x, y, 150)], 6, nseg=8); D.clip_cyl(x, y, 6, 0, 150)
    D.mesh(TX.mats['canvas']).poly([(hx0 - 30, hy0 - 50, 150), (hx1 + 50, hy0 - 50, 150), (hx1 + 50, hy1 + 50, 150), (hx0 - 30, hy1 + 50, 150)],
                                   (0, 0, 1), [(0, 0), (2, 0), (2, 1), (0, 1)])
    D.finish()
    # Davy Jones' Locker: the reward room at the end of the tunnel; teleporter back to the harbour square
    lx0_, ly0_, lx1_, ly1_ = LOCKER
    K.add(sign_box((lx0_ + 1, TY - 60, TFLOOR + 96), (lx0_ + 5, TY + 60, TFLOOR + 124), T('sign_locker'), 1024, 128,
                   back=CAULK, facing='e', edge=PT('planks')))
    K.weapon('betty', lx1_ - 120, TY, TFLOOR, marker='black')
    K.item('item_armor_padshield', lx0_ + 140, TY + 130, TFLOOR)
    K.ammo('imperius', lx0_ + 140, TY - 130, TFLOOR)
    G_['custom']('skeleton_throne', lx1_ - 70, TY + 120, TFLOOR, 180) if 'skeleton_throne' in G_['pplib'].PLACE else None
    G_['custom']('chest_open', lx1_ - 70, TY - 120, TFLOOR, 180)
    K.add(box((lx1_ - 100, TY - 140, TFLOOR), (lx1_ - 40, TY - 100, TFLOOR + 24), WCLIP))
    K.teleporter((lx0_ + 40, ly1_ - 60, TFLOOR), (lx0_ + 120, ly1_ - 8, TFLOOR + 96), dest=(300, -2700, 0), angle=90, name='locker_exit')
    K.light((lx0_ + lx1_) / 2, TY, TFLOOR + 200, 360, '0.5 0.9 0.8')
    K.speaker((lx0_ + lx1_) / 2, TY, TFLOOR + 80, 'ambient/water_drippling')


# ------------------------------------------------------------------------------------------------ Smuggler's Rapids
def rapids():
    Mt = TX.mats
    sand = {'top': PT('sand'), 'side': PT('rock'), 'bot': CAULK}
    tl = {'top': PT('pool_tile'), 'side': PT('rock'), 'bot': CAULK}
    st = {'top': PT('planks'), 'side': PT('rock'), 'bot': PT('rock')}
    c0, c1 = CH; b0, b1 = BX
    cave = box((CAVE[0], CAVE[1], 0), (CAVE[2], CAVE[3], 120), CAULK)
    mass = []
    for i, (y0, y1, W) in enumerate(POOLS):
        bed, bank = W - 40, W + 8
        parts = [box((b0, y0, 0), (c0, y1, bank), sand), box((c1, y0, 0), (b1, y1, bank), sand), box((c0, y0, 0), (c1, y1, bed), tl)]
        if i == 2:
            parts = sum((wopmap.carve(p, [cave]) for p in parts), [])
        mass += parts
        cut = STAIRS(c0, y0, c0 + 48, y1, bed, bank, 'w', tl) + STAIRS(c1 - 48, y0, c1, y1, bed, bank, 'e', tl)
        K.reserve(((c0, y0, bed), (c1, y1, W + 200)))
        K.water_box((c0 + 48, y0, bed), (c1 - 48, y1, W), PT('water'), nodraw_tex=PT('water_nodraw'), cutters=cut)
        K.current((c0 + 64, y0 + 150, bed), (c1 - 64, y0 + 350, W), 90, 300, f'smuggle{i}')      # downhill = north (+y)
        K.speaker((c0 + c1) / 2, (y0 + y1) / 2, W + 40, 'ambient/water_flowing')
    # the plateau and the mass are one rocky MD3 (visible) + the same solids as collision
    pl = box((PLATEAU[0], PLATEAU[1], 0), (PLATEAU[2], PLATEAU[3], 448), sand)
    mass.append(pl)
    for b in mass:
        for f in b.faces: f.tex = CAULK
    K.solid_piece('smuggler_hill', mass, lambda c, n, p: (Mt['sandrock'] if n[2] > 0.7 else Mt['rock_m'], ML.planar_uv(n, 256)))
    # bank flights at the drops (16u risers), the two flights up from the ground beside the third tier
    for (x0, x1) in ((b0, b0 + 96), (b1 - 96, b1)):
        STAIRS(x0, -4200, x1, -3944, 320, 448, 's', st)
        STAIRS(x0, -3700, x1, -3444, 192, 320, 's', st)
    STAIRS(b0 - 384, -3346, b0, -3250, 0, 192, 'e', st, route='rapids_w')
    STAIRS(b1, -3346, b1 + 384, -3250, 0, 192, 'w', st, route='rapids_e')
    K.keep_clear(b0 - 496, -3346, b0 - 384, -3250, 0); K.keep_clear(b1 + 384, -3346, b1 + 496, -3250, 0)
    K.route('rapids_up', (b0 + 40, -3300, 192), (b0 + 40, -4600, 448))
    # bottom: ledge in front of the cave, splash pool (the isle ground is carved for it)
    K.reserve(((P4[0], P4[1], WATER - 32), (P4[2], P4[3], 0)))
    pcut = K.stairs16(P4[0], P4[3] - 48, P4[2], P4[3], WATER - 32, 0, 'n', {'top': PT('pool_tile'), 'side': PT('pool_tile'), 'bot': CAULK})
    K.water_box((P4[0], P4[1], WATER - 32), (P4[2], P4[3], WATER), PT('water'), nodraw_tex=PT('water_nodraw'), cutters=pcut)
    K.current((c0 + 64, LEDGE_Y[1] + 4, WATER - 32), (c1 - 64, LEDGE_Y[1] + 120, WATER), 90, 220, 'smuggle_out')
    # waterfalls: every drop + the curtain in front of the cave
    X = ML.Model(); f = X.mesh(Mt['fall'])
    def sheet(y, za, zb_, xa=c0 + 48, xb=c1 - 48):
        f.poly([(xa, y, zb_), (xb, y, zb_), (xb, y, za), (xa, y, za)], (0, 1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        f.poly([(xb, y, zb_), (xa, y, zb_), (xa, y, za), (xb, y, za)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    for (y0, y1, W), (_, _, Wn) in zip(POOLS[:-1], POOLS[1:]): sheet(y1 + 2, W, Wn)
    sheet(POOLS[-1][1] + 3, POOLS[-1][2], 0, c0 - 30, c1 + 30)
    sheet(PLATEAU[3] + 2, 560, POOLS[0][2])
    K.custom(ML.save('rapids_falls', X), 0, 0, 0, lit=False, occupy=False, _structure=1)
    K.speaker((c0 + c1) / 2, LEDGE_Y[0] + 30, 60, 'ambient/water_flowing')
    # the smugglers' cave: Pumper, contraband, lantern
    cx0, cy0, cx1, cy1 = CAVE
    K.weapon('pumper', (cx0 + cx1) / 2, cy0 + 90, 0, marker='green')
    for (x, y) in ((cx0 + 50, cy0 + 50), (cx1 - 60, cy0 + 50)):
        G_['furn']('crate_big', x, y, 0, 15, [((-36, -36, 0), (36, 36, 72))])
    G_['furn']('barrel', cx0 + 60, cy1 - 70, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    G_['furn']('barrel', cx1 - 60, cy1 - 70, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    K.light((cx0 + cx1) / 2, (cy0 + cy1) / 2, 90, 260, '1 0.75 0.45')
    K.ammo('splasher', cx0 + 140, cy1 - 60, 0)
    K.weapon('splasher', (c0 + c1) / 2, -3960, POOLS[1][2] - 40, marker='blue')                 # on the bed of pool 2
    K.jumppad(500, -4300, 0, land=(760, -4850, 448), apex=448 + 170, name='pad_plateau', edges=[(PLATEAU[0], -4740, 448)])
    for (x, y, z) in ((b1 - 60, -4500, 448), (b0 + 60, -3880, 320), (b1 - 60, -3380, 192)):
        G_['custom']('palm_' + 'abc'[int(x) % 3], x, y, z, int(y) % 360, lit=False); K.add(cyl(x, y, 14, z, z + 300, WCLIP, 8))


def lighthouse():
    """octagonal lighthouse on the hill: walk-in keeper's room (door north), solid tower, gallery deck at 960 reached by
    a pad on the plateau, glass lamp room with a rotating beam; Imperius on the gallery"""
    Mt = TX.mats
    cx, cy = LH; z0 = 448
    R = LH_R / math.cos(math.pi / 8)
    br = []
    ring = ngon(cx, cy, R, 8)
    inner = ngon(cx, cy, R - 24 / math.cos(math.pi / 8), 8)
    for k in range(8):
        a, b = ring[k], ring[(k + 1) % 8]; ia, ib = inner[k], inner[(k + 1) % 8]
        mxy = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        door = mxy[1] > cy + LH_R * 0.9                      # the north face
        poly = [a, b, ib, ia]
        if door:
            br.append(prism(poly, z0 + 112, z0 + LH_ROOM, CAULK))
        else:
            br.append(prism(poly, z0, z0 + LH_ROOM, CAULK))
    br.append(prism(ring, z0 + LH_ROOM, z0 + LH_ROOM + 16, CAULK))
    br.append(prism(ngon(cx, cy, (LH_R - 8) / math.cos(math.pi / 8), 8), z0 + LH_ROOM + 16, LH_TOP - 16, CAULK))
    br.append(prism(ngon(cx, cy, GAL_R / math.cos(math.pi / 8), 8), LH_TOP - 16, LH_TOP, CAULK))
    def tf(c, n, p):
        if abs(n[2]) > 0.7: return (Mt['planks_m'], ML.planar_uv(n, 128))
        return (Mt['lh_red'] if int((c[2] - z0) // 128) % 2 else Mt['lh_white'], ML.planar_uv(n, 256))
    K.solid_piece('lighthouse', br, tf)
    K.keep_clear(cx - 60, cy + LH_R, cx + 60, cy + LH_R + 112, z0)
    K.route('lighthouse_door', (cx, cy + LH_R + 90, z0), (cx, cy, z0))
    # lamp room: glass + roof, collision cylinder; the rotating beam
    D = SB.Dress(K, 'lighthouse_lamp', (cx, cy, LH_TOP))
    revolve(D.mesh(Mt['glass']), [(86, LH_TOP + 1), (86, LH_TOP + 120)], n=16, cx=cx, cy=cy)
    for k in range(8):
        a = 2 * math.pi * k / 8
        tube(D.mesh(Mt['steel']), [(cx + 88 * math.cos(a), cy + 88 * math.sin(a), LH_TOP + 1), (cx + 88 * math.cos(a), cy + 88 * math.sin(a), LH_TOP + 120)], 3, nseg=5)
    revolve(D.mesh(Mt['roof_m']), [(100, LH_TOP + 120), (60, LH_TOP + 170), (8, LH_TOP + 196), (0.1, LH_TOP + 197)], n=16, cx=cx, cy=cy, inward=True)
    sphere(D.mesh(Mt['lamp']), (cx, cy, LH_TOP + 60), 26, 12, 8)
    D.clip_cyl(cx, cy, 90, LH_TOP, LH_TOP + 196)
    D.finish()
    X = ML.Model()
    for s in (1, -1):
        for zz in (0, 1):
            q = [(s * 30, -8 + 16 * zz, -10 + 20 * zz), (s * 1500, -160 + 320 * zz, -60 + 120 * zz), (s * 1500, 160 - 320 * zz, -60 + 120 * zz), (s * 30, 8 - 16 * zz, -10 + 20 * zz)]
        X.mesh(Mt['beam']).poly([(s * 30, 0, -12), (s * 1500, 0, -120), (s * 1500, 0, 120), (s * 30, 0, 12)], (0, 1, 0), [(0, 0.5), (1, 0), (1, 1), (0, 0.5)])
        X.mesh(Mt['beam']).poly([(s * 30, -12, 0), (s * 1500, -120, 0), (s * 1500, 120, 0), (s * 30, 12, 0)], (0, 0, 1), [(0, 0.5), (1, 0), (1, 1), (0, 0.5)])
    beam = ML.save_iqm('lh_beam', X)
    K.rotating_model2(beam, (cx, cy, LH_TOP + 60), speed=40)
    top = LH_TOP
    K.jumppad(cx - 300, cy - 90, z0, land=(cx - 150, cy - 20, top), apex=top + 130, name='pad_lighthouse', edges=[(cx - GAL_R, cy, top)])
    K.weapon('imperius', cx + 150, cy, top, marker='purple')
    K.item('item_armor_shard', cx, cy + 150, top); K.item('item_armor_shard', cx, cy - 150, top)
    K.trigger_sound((cx - 200, cy - 200, top + 2), (cx - 100, cy + 200, top + 70), 'human/applause', 'lighthouse_top', wait=20)
    K.timer_sound(cx, cy, top + 260, 'machine/fog_horn', 'foghorn', 60, 20)
    K.light(cx, cy, z0 + 110, 260, '1 0.85 0.6')
    K.item('item_speedy', cx, cy - 40, z0)


# ------------------------------------------------------------------------------------------------ Port Town
def port_town():
    Mt = TX.mats
    P = TX.texfn
    def shop(rect, h, door, wall_mat, name, sign_tex, canopy, hatch=None):
        x0, y0, x1, y1 = rect
        ops = [door] + ([hatch] if hatch else [])
        br = K.building(rect, 0, h, openings=ops, tex=CAULK)
        K.solid_piece(name, br, P('roof_m', wall_mat))
        return br
    # Fish shack: door east, serving hatch north (the harbour), blue awning, hanging fish, crates
    fx0, fy0, fx1, fy1 = FISH
    shop(FISH, FISH_H, ('e', fy0 + 90, fy0 + 202, 0, 120), 'wall_blue', 'fish_shack', 'sign_fish', 'canopy_b', hatch=('n', fx0 + 70, fx1 - 70, 48, 136))
    D = SB.Dress(K, 'fish_dress', ((fx0 + fx1) / 2, (fy0 + fy1) / 2, 0))
    n_ = SB.Wall((0, fy1), 'n')
    SB.awning(D, n_, Mt['canopy_b'], Mt['steel'], n_.uof(fx1 - 50), n_.uof(fx0 + 50), 150, depth=86, drop=24)
    SB.frame(D, n_, Mt['trim_w'], n_.uof(fx1 - 70), n_.uof(fx0 + 70), 48, 136, sill=True)
    SB.frame(D, SB.Wall((fx1, 0), 'e'), Mt['trim_w'], fy0 + 90, fy0 + 202, 0, 120)
    SB.fascia(D, Mt['trim_w'], FISH, FISH_H - 22, FISH_H, sides='new')
    for k, x in enumerate(np.linspace(fx0 + 90, fx1 - 90, 5)):           # fish hanging under the awning
        top = n_.at(66, n_.uof(x), 150 - 24 * 66 / 86 - 1)
        tube(D.mesh(Mt['rope']), [top, top - np.array([0, 0, 14])], 0.8, nseg=4, caps=(False, False))
        ellipsoid(D.mesh(Mt['fish']), top - np.array([0, 0, 34]), 7, 3, 20, nu=8, nv=6)
    for x in (fx0 + 40, fx1 - 40):
        SB.crate(D, Mt['planks_m'], (x - 22, fy1 + 30, 0), (x + 22, fy1 + 74, 30))
    D.finish()
    K.weapon('bubbleg', (fx0 + fx1) / 2, (fy0 + fy1) / 2, 0, marker='green')
    K.keep_clear(fx1, fy0 + 80, fx1 + 112, fy0 + 212, 0)
    K.route('fish_door', (fx1 + 90, fy0 + 146, 0), (fx1 - 100, fy0 + 146, 0))
    K.jumppad(fx0 - 120, fy0 + 150, 0, land=(fx0 + 120, fy0 + 150, FISH_H + 16), apex=FISH_H + 16 + 130, name='pad_fish', edges=[(fx0, fy0 + 150, FISH_H + 16)])
    K.light((fx0 + fx1) / 2, (fy0 + fy1) / 2, 140, 260)
    # Map shop: door north, green awning, a globe, maps, the catalog telescope
    mx0, my0, mx1, my1 = MAPS
    shop(MAPS, MAPS_H, ('n', mx0 + 114, mx1 - 114, 0, 120), 'wall_green', 'map_shop', 'sign_maps', 'canopy_g')
    D = SB.Dress(K, 'maps_dress', ((mx0 + mx1) / 2, (my0 + my1) / 2, 0))
    n_ = SB.Wall((0, my1), 'n')
    SB.awning(D, n_, Mt['canopy_g'], Mt['steel'], n_.uof(mx1 - 30), n_.uof(mx0 + 30), 150, depth=72, drop=22)
    SB.frame(D, n_, Mt['trim_w'], n_.uof(mx1 - 114), n_.uof(mx0 + 114), 0, 120)
    SB.fascia(D, Mt['trim_w'], MAPS, MAPS_H - 22, MAPS_H, sides='sew')
    SB.sandwich_board(D, Mt['mapboard'], Mt['oldwood'], mx0 - 40, my1 + 40, 0, facing=90)
    gx, gy = mx0 + 80, my0 + 80                                            # globe on a stand inside
    tube(D.mesh(Mt['brass']), [(gx, gy, 0), (gx, gy, 44)], 3, nseg=6)
    sphere(D.mesh(Mt['globe']), (gx, gy, 66), 22, 14, 10)
    D.clip_cyl(gx, gy, 22, 0, 88)
    rbox(D.mesh(Mt['oldwood']), (mx1 - 120, my0 + 30, 0), (mx1 - 40, my0 + 110, 40), r=2, k=1, tile=64)      # map table
    D.mesh(Mt['mapboard']).poly([(mx1 - 116, my0 + 34, 40.5), (mx1 - 44, my0 + 34, 40.5), (mx1 - 44, my0 + 106, 40.5), (mx1 - 116, my0 + 106, 40.5)],
                                (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    D.clip_box((mx1 - 120, my0 + 30, 0), (mx1 - 40, my0 + 110, 40))
    D.finish()
    K.keep_clear(mx0 + 104, my1, mx1 - 104, my1 + 112, 0)
    K.route('map_door', ((mx0 + mx1) / 2, my1 + 90, 0), ((mx0 + mx1) / 2, my1 - 100, 0))
    K.jumppad(mx1 + 110, my0 + 60, 0, land=(mx1 - 110, my0 + 150, MAPS_H + 16), apex=MAPS_H + 16 + 130, name='pad_maps', edges=[(mx1, my0 + 150, MAPS_H + 16)])
    K.item('item_jumper', mx0 + 100, my0 + 150, MAPS_H + 16)
    K.light((mx0 + mx1) / 2, (my0 + my1) / 2, 140, 240)
    # Sail & Rope loft: door west, windows, red awning, drying sails on a line, rope coils; Boaster on the roof
    lx0, ly0, lx1, ly1 = LOFT
    br = K.building(LOFT, 0, LOFT_H, openings=[('w', ly0 + 110, ly0 + 230, 0, 128), ('n', lx0 + 80, lx0 + 160, 120, 200),
                                               ('n', lx1 - 160, lx1 - 80, 120, 200)], tex=CAULK)
    K.solid_piece('sail_loft', br, P('roof_m', 'wall_ochre'))
    D = SB.Dress(K, 'loft_dress', ((lx0 + lx1) / 2, (ly0 + ly1) / 2, 0))
    w_ = SB.Wall((lx0, 0), 'w')
    SB.awning(D, w_, Mt['canopy_r'], Mt['steel'], w_.uof(ly0 + 250), w_.uof(ly0 + 90), 160, depth=70, drop=22)
    SB.frame(D, w_, Mt['trim_w'], w_.uof(ly0 + 230), w_.uof(ly0 + 110), 0, 128)
    n_ = SB.Wall((0, ly1), 'n')
    for (a, b) in ((lx0 + 80, lx0 + 160), (lx1 - 160, lx1 - 80)):
        SB.frame(D, n_, Mt['trim_w'], n_.uof(b), n_.uof(a), 120, 200, sill=True)
    SB.fascia(D, Mt['trim_w'], LOFT, LOFT_H - 24, LOFT_H, sides='nsew')
    sx = lx0 - 200                                                         # drying line with two sails
    for y in (ly0 + 20, ly0 + 300):
        tube(D.mesh(Mt['oldwood']), [(sx, y, 0), (sx, y, 170)], 5, nseg=6); D.clip_cyl(sx, y, 6, 0, 170)
    tube(D.mesh(Mt['rope']), [(sx, ly0 + 20, 165), (sx, ly0 + 300, 165)], 1.2, nseg=4, caps=(False, False))
    for (ya, yb, sh) in ((ly0 + 40, ly0 + 150, 'sail_r'), (ly0 + 170, ly0 + 280, 'canvas')):
        for sg in (1, -1):
            q = [(sx, ya, 165), (sx, yb, 165), (sx, yb, 70), (sx, ya, 80)]
            D.mesh(Mt[sh]).poly(q if sg > 0 else q[::-1], (sg, 0, 0), [(0, 0), (1, 0), (1, 1), (0, 1)] if sg > 0 else [(0, 1), (1, 1), (1, 0), (0, 0)])
    D.finish()
    G_['furn']('rope_coil', lx1 - 60, ly1 + 60, 0, 0, [((-24, -24, 0), (24, 24, 16))]) if 'rope_coil' in G_['pplib'].PLACE else None
    G_['furn']('barrel', lx1 + 50, ly0 + 60, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    K.keep_clear(lx0 - 112, ly0 + 100, lx0, ly0 + 240, 0)
    K.route('loft_door', (lx0 - 90, ly0 + 170, 0), (lx0 + 110, ly0 + 170, 0))
    K.jumppad(lx1 + 120, ly0 + 160, 0, land=(lx1 - 130, ly0 + 170, LOFT_H + 16), apex=LOFT_H + 16 + 140, name='pad_loft', edges=[(lx1, ly0 + 170, LOFT_H + 16)])
    K.weapon('boaster', lx0 + 120, ly1 - 120, LOFT_H + 16, marker='orange')
    K.light((lx0 + lx1) / 2, (ly0 + ly1) / 2, 160, 280)
    # harbour square: lamps, barrels, a rowboat, nets
    for (x, y) in ((-220, -2620), (220, -2620), (-320, -2850), (320, -2850)):
        G_['custom']('lantern_post', x, y, 0, 0); K.add(box((x - 6, y - 6, 0), (x + 6, y + 6, 150), WCLIP))
        K.light(x + 34, y, 132, 160, '1 0.8 0.5')
    for (x, y) in ((-300, -2640), (260, -2650), (100, -2900)):
        G_['furn']('barrel', x, y, 0, 0, [((-20, -20, 0), (20, 20, 56))]); G_['furn']('barrel', x + 44, y + 8, 0, 0, [((-20, -20, 0), (20, 20, 56))])
    for (x, y, a) in ((-200, -2950, 20), (300, -2950, -10)):
        G_['furn']('crate_big', x, y, 0, a, [((-36, -36, 0), (36, 36, 72))])
    K.station(0, -3060, 0, ang=90)


def isle_dressing():
    rng = np.random.default_rng(7)
    spots = [(-1900, -2700), (-1800, -3300), (-1880, -4700), (-1700, -5000), (-100, -3300), (-50, -4000), (100, -4700),
             (-400, -5000), (1800, -3000), (1850, -3700), (1880, -4300), (1700, -5050), (300, -3500), (420, -4200)]
    for i, (x, y) in enumerate(spots):
        if K.free(x, y, 30, 0, 300):
            G_['custom']('palm_' + 'abc'[i % 3], x, y, 0, int(rng.uniform(0, 360)), lit=False)
            K.add(cyl(x, y, 14, 0, 300, WCLIP, 8)); K.occupy_r(x, y, 30, 0, 300)
    for (x, y, a) in ((-1950, -3900, 30), (1950, -2700, -20), (-60, -2700, 80)):
        if K.free(x, y, 90, 0, 60):
            G_['furn']('rowboat', x, y, 0, a, [((-80, -30, 0), (80, 30, 30))]); K.occupy_r(x, y, 90, 0, 60)
    for (x, y) in ((-200, -4300), (200, -3900), (-1000, -2840), (1500, -3600), (-1950, -4400), (1800, -4700)):
        if K.free(x, y, 50, 0, 80):
            G_['custom']('torch_post', x, y, 0, 0); K.add(box((x - 6, y - 6, 0), (x + 6, y + 6, 130), WCLIP)); K.occupy_r(x, y, 30, 0, 130)
            K.light(x, y, 150, 140, '1 0.7 0.4')
    for (x, y, z, a) in ((-1980, -2700, 0, 45), (-1900, -5000, 0, 45), (0, -4400, 0, 90), (1900, -3200, 0, 135), (1900, -4900, 0, 180),
                         (-300, -3150, 0, 270)):
        K.spawn(x, y, z, a)
    for w, (x, y, z) in (('pumper', (1900, -4200, 0)), ('balloony', (-1950, -3100, 0)), ('bubbleg', (-150, -3700, 0)),
                         ('boaster', (500, -2640, 0)), ('betty', (-60, -4900, 0))):
        K.ammo(w, x, y, z)
    for (x, y) in ((-1100, -4200), (-700, -3800)):
        K.item('item_armor_shard', x, y, LAG_Z)
    for x in range(-1800, 1801, 600):
        K.light(x, -3900, 520, 900, '1 0.95 0.85')
        K.light(x, -4800, 520, 900, '1 0.95 0.85')


# ------------------------------------------------------------------------------------------------ Cannon Show
def cannon_show(cannons):
    """every CANNON_PERIOD seconds the fort's rampart guns and the galleon's deck guns fire together: a boom at each,
    muzzle flashes and smoke puffs that pulse in step (shader timer_pulse; Q3 can't switch shaders from a trigger)"""
    Mt = TX.mats
    X = ML.Model()
    pts = []
    for (x, y, z, a) in cannons:
        if z < 60: continue
        r = math.radians(a)
        d = np.array([math.cos(r), math.sin(r), 0.0]); s = np.array([-d[1], d[0], 0.0])
        mz = np.array([x, y, z + 26.0]) + d * 50
        pts.append(mz)
        for (sh, size, fwd) in (('flash', 26, 14), ('smoke', 70, 70)):
            c = mz + d * fwd + np.array([0, 0, 0.3 * size if sh == 'smoke' else 0])
            for ax in (s, np.array([0, 0, 1.0])):
                o = np.cross(d, ax); o = o / max(1e-6, np.linalg.norm(o))
                q = [c - ax * size - d * size * 0.6, c + ax * size - d * size * 0.6, c + ax * size + d * size * 0.6, c - ax * size + d * size * 0.6]
                X.mesh(Mt[sh]).poly(q, o, [(0, 1), (1, 1), (1, 0), (0, 0)])
    if not pts: return 0
    c = np.mean(pts, 0)
    X.shift(c * np.array([1, 1, 0]))
    K.custom(ML.save('cannon_fx', X), float(c[0]), float(c[1]), 0, lit=False, occupy=False, _structure=1)
    groups = {}
    for p in pts: groups.setdefault((int(p[0] // 900), int(p[1] // 900)), []).append(p)
    for i, g in enumerate(groups.values()):
        m = np.mean(g, 0)
        K.timer_sound(m[0], m[1], m[2] + 40, 'sound/weapons/betty/explosion.wav', f'cannons{i}', CANNON_PERIOD, 0)
    return len(pts)


# ======================================================================================================== helpers / finish
def STAIRS(*a, **k):
    st = K.stairs16(*a, **k); K.reserve(st); return st


def build(G):
    isle_ground(); pier(); reef(); rapids(); lighthouse(); port_town(); isle_dressing()
    n = cannon_show(G['CANNONS'])
    print(f'XL: {n} cannons in the Cannon Show')


def finish(G, routes_path):
    """merge the original island's pads/items/routes into the kit's spots and write the map with K.write"""
    for (nm, o, tg, land) in G['JUMPPADS']:
        z = o[2] - 38
        try: t = padmath.plan(z, (o[0], o[1]), land, tg[2])['t']
        except Exception: t = 0
        K.spots['pads'].append(dict(name=nm, pad=(o[0], o[1], z), origin=list(o), target=list(tg), land=list(land), t=t))
    for kind in ('weapon', 'ammo', 'item', 'spawn'):
        for t in G['SPOTS'][kind]:
            if len(t) == 3: (x, y, fl), c = t, 'info_player_deathmatch'
            else: c, x, y, fl = t[:4]
            cls = ('weapon_' + c) if kind == 'weapon' else c
            K.spots[kind].append(dict(cls=cls, x=round(x), y=round(y), floor=round(fl)))
    K.routes = [(n, a, b) for (n, a, b) in G['ROUTES']] + K.routes
    TX.write_shader()
    return K.write(G['OUT'], routes_path=routes_path, header=f"// {G['TX'].LONGNAME} XL - generated by wop_tools/padpirate (build_pirate.py + pp_xl.py)\n")
