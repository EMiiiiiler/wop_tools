"""The night balcony of wop_padlounge (Couch Lock), called from build_lounge.main():  balcony_build.build(L)

L is the build_lounge module (its Map M, helpers and item/spawn bookkeeping). Layout constants and the custom MD3s live in
balcony_models.py (BM), so collision here always matches the models.

  outside        the apartment block (facade with neighbours' lit windows, the upstairs neighbour's balcony and door),
                 a sky box with a painted night skyline (env/padlounge/night_*), a street far below, two blocks across it
  deck           4096 x 3200 hardwood deck south of the lounge (sliding door + a pet flap through the wall), glass
                 balustrade (clip above it), bamboo privacy screens at both ends, string lights on posts
  spa platform   east, 256 high (16u stairs from the deck), cedar hot tub (MD3) sunk into it: 268 deep water, steps
                 out on the north side; Imperius at the bottom, the drain is the secret teleport upstairs
  pergola        west, 1600 high with walkable rafters (pad up; Betty on top), rattan L sofa + table, hanging baskets
  other          kettle BBQ, AC unit with a spinning fan, patio heater, hammock on a stand, planter with herbs,
                 loungers, telescope; the upstairs neighbour's balcony (secret) with a gnome and a teleporter back down
"""
import math
import numpy as np
from wopmap import box, hull, cyl, prism, carve, sign_box, fit_face, stairs, ngon
import balcony_models as BM


def build(L):
    A, M, T, CAULK, CLIP, WCLIP, TRIG, ORIGIN, NODRAW_NS = L.A, L.M, L.T, L.CAULK, L.CLIP, L.WCLIP, L.TRIG, L.ORIGIN, L.NODRAW_NS
    YF = BM.YF
    SC = L.TX.BALCONY_SCALES

    def custom_b(name, lit=True):
        sc, a = SC[name]
        kw = dict(spawnflags=4, _castshadows=1, _receiveshadows=1, _lightmapscale=0.5) if lit else {}
        return M.model(f'models/padlounge/{name}.md3', (round(a[0]), round(a[1]), round(a[2], 2)), scale=sc, angle=0, **kw)

    def poly16(cx, cy, r, z0, z1, tex):
        return prism(BM.ngon16(cx, cy, r), z0, z1, tex)

    def wedge_ring(cx, cy, r0, r1, z0, z1, tex):
        a, b = BM.ngon16(cx, cy, r0), BM.ngon16(cx, cy, r1)
        out = []
        for k in range(16):
            q = [a[k], a[(k + 1) % 16], b[(k + 1) % 16], b[k]]
            out.append(hull([(x, y, z) for (x, y) in q for z in (z0, z1)], tex, round_pts=False))
        return out

    # ============================================================================================== outside world
    X0, X1, Y0, Y1, Z0, Z1 = -5000, 5000, -9000, 2200, -2000, 8000
    sky = T('sky')
    for (mn, mx) in (((X0 - 16, Y0 - 16, Z1), (X1 + 16, Y1 + 16, Z1 + 16)), ((X0 - 16, Y0 - 16, Z0), (X0, Y1 + 16, Z1)),
                     ((X1, Y0 - 16, Z0), (X1 + 16, Y1 + 16, Z1)), ((X0, Y0 - 16, Z0), (X1, Y0, Z1)), ((X0, Y1, Z0), (X1, Y1 + 16, Z1))):
        A(box(mn, mx, {'side': sky, 'top': sky, 'bot': sky}, detail=False))
    A(box((X0 - 16, Y0 - 16, Z0 - 16), (X1 + 16, Y1 + 16, Z0), {'top': T('street'), 'side': CAULK, 'bot': CAULK}, detail=False))
    # the apartment block round the lounge shell (x +-2064, y -1808..1808, z -16..2064)
    fac = {'s': T('facade'), 'side': T('brick'), 'top': T('concrete'), 'bot': CAULK}
    for (mn, mx) in (((X0, YF, Z0), (-2064, Y1, 6000)), ((2064, YF, Z0), (X1, Y1, 6000)), ((-2064, YF, 2064), (2064, Y1, 6000)),
                     ((-2064, YF, Z0), (2064, Y1, -16)), ((-2064, 1808, -16), (2064, Y1, 2064))):
        A(box(mn, mx, fac, detail=False))
    # across the street: two blocks of flats (self-lit windows)
    A(box((-4800, -8000, Z0), (-200, -6800, 1800), T('far_a')))
    A(box((800, -7600, Z0), (4800, -6600, 600), T('far_b')))

    # ============================================================================================== deck + edges
    x0, y0, x1, y1 = BM.DECK
    dk = {'top': T('deck'), 'side': T('concrete'), 'bot': T('concrete')}
    A(box((x0 - 16, -5008, -64), (x1 + 16, YF, -16), dk))
    hx0, hy0, hx1, hy1 = BM.PERG_HATCH
    for r in L.sub_rects((x0 - 16, -5008, x1 + 16, YF), [(hx0 + 4, hy0 + 4, hx1 - 4, hy1 - 4)]):
        A(box((r[0], r[1], -16), (r[2], r[3], 0), dk))
    # door track + mat just outside the door
    dx0, dx1, dh = BM.DOOR
    A(box((dx0, YF - 24, 0), (dx1, YF, 2), T('alu_track')))
    b = box((-260, YF - 300, 0), (260, YF - 40, 2), {'top': T('doormat'), 'side': T('doormat'), 'bot': CAULK})
    L.hfit(b, -260, YF - 300, 260, YF - 40, 512, 256, T('doormat')); A(b)
    # bamboo privacy screens at both ends, clip above them and over the balustrade
    for (xa, xb) in ((x0 - 16, x0), (x1, x1 + 16)):
        A(box((xa, -5008, 0), (xb, YF, 1800), T('bamboo')))
        A(box((xa, -5008, 1800), (xb, YF, 3200), CLIP))
    A(box((x0, -5008, 0), (x1, -5000, 3200), CLIP))
    for k in range(4): custom_b(f'b_rail{k}')
    # wall lanterns either side of the door
    for s in (-1, 1):
        xa, xb = sorted((s * (dx1 + 120), s * (dx1 + 200)))
        A(box((xa, YF - 40, 1080), (xb, YF, 1300), {'side': T('lantern'), 'n': CAULK, 'top': T('black'), 'bot': T('black')}))
        L.light((xa + xb) / 2, YF - 120, 1180, 650, '1 0.78 0.5')
    custom_b('b_slider')

    # ============================================================================================== spa platform + hot tub
    px0, py0, px1, py1, pz = BM.PLAT
    cx, cy = BM.TUB
    hole = poly16(cx, cy, BM.TUB_RO, -1, pz + 1, CAULK)
    for p in carve(box((px0, py0, 0), (px1, py1, pz), T('deck')), [hole], T('deck')):
        for f in p.faces:
            if abs(f.n[2]) > 0.9: f.tex = T('deck')
            else:
                c = np.mean([np.asarray(q) for q in f.pts], 0)
                f.tex = CAULK if math.hypot(c[0] - cx, c[1] - cy) < BM.TUB_RO + 4 else T('deck')
        A(p)
    # stairs from the deck (north side, rising south), 16u risers
    A(stairs(380, py1, 764, py1 + 512, 0, pz, 's', T('deck')))
    # tub: floor (glowing tiles), collision ring, steps inside and outside, water volume (nodraw; the surface is the MD3)
    A(poly16(cx, cy, BM.TUB_RO, 0, BM.TUB_FLOOR, {'top': T('tub_floor'), 'side': CAULK, 'bot': CAULK}))
    A(wedge_ring(cx, cy, BM.TUB_RI, BM.TUB_RO, BM.TUB_FLOOR, BM.TUB_RIM, WCLIP))
    steps_in = []
    for k, top in enumerate((288, 304, 320)):
        ya, yb = cy + 354 + 32 * k, cy + 354 + 32 * (k + 1)
        if k == 2: yb = cy + 452
        b = box((cx - 80, ya, BM.TUB_FLOOR), (cx + 80, yb, top), {'top': T('deck'), 'side': T('deck'), 'bot': CAULK})
        A(b); steps_in.append(b)
    for k, top in enumerate((272, 288, 304, 320)):
        ya = cy + 498 + 32 * (3 - k)
        A(box((cx - 80, ya, pz), (cx + 80, ya + 32, top), T('deck')))
    water = poly16(cx, cy, BM.TUB_RI, BM.TUB_FLOOR, BM.TUB_WATER, T('water_inner'))
    for p in carve(water, steps_in, T('water_inner')):
        for f in p.faces: f.tex = T('water_inner')
        A(p)
    custom_b('b_hottub')
    # the drain (secret): a grate on the tub floor at the south side
    A(L.deco((cx - 48, cy - 388, BM.TUB_FLOOR), (cx + 48, cy - 292, BM.TUB_FLOOR + 1), T('alu_track')))
    M.ent('trigger_multiple', brushes=[box((cx - 44, cy - 384, BM.TUB_FLOOR + 60), (cx + 44, cy - 296, BM.TUB_FLOOR + 200), TRIG)], target='nb_snd', wait=6)
    M.ent('trigger_teleport', brushes=[box((cx - 44, cy - 384, BM.TUB_FLOOR + 1), (cx + 44, cy - 296, BM.TUB_FLOOR + 60), TRIG)], target='nb_dest')
    L.speaker(cx, cy - 340, 120, 'sound/world/misc/secret_found.ogg', loop=False, targetname='nb_snd')
    L.speaker(cx, cy, 330, 'sound/world/ambient/water_bubbling.ogg', volume=0.6)
    L.light(cx, cy, 160, 500, '0.4 0.75 1'); L.light(cx, cy, 520, 500, '0.5 0.8 1')
    for (sx, sy) in ((-120, -80), (160, 60), (0, -260)):
        A(L.sprite(cx + sx, cy + sy, BM.TUB_WATER + 10, BM.TUB_WATER + 230, 'steam', 200))   # steam
    L.weapon('imperius', cx, cy + 160, BM.TUB_FLOOR, 'purple')
    L.item('ammo_imperius', cx - 220, cy - 60, BM.TUB_FLOOR)
    # platform dressing: loungers, telescope, potted plants, corner light posts
    for k in range(len(BM.LOUNGERS)):
        custom_b(f'b_lounger{k}')
    for pts in BM.LOUNGER_BOXES:                     # seat slab, legs, back: walk under the seat
        A(hull([tuple(p) for p in pts], WCLIP))
    L.mdl_c('pad_ddmix/cabin/telescope.md3', 1900, -4780, pz, 1.4, 120)
    L.custom('plant_small', 450, -3080, pz + L.LM.PLANT_SMALL_OFS, angle=40)
    A(cyl(450, -3080, round(0.16 * 620), pz, round(pz + 0.25 * 620), WCLIP, 16))
    L.custom('plant_small', 440, -4840, pz + L.LM.PLANT_SMALL_OFS, angle=200)
    A(cyl(440, -4840, round(0.16 * 620), pz, round(pz + 0.25 * 620), WCLIP, 16))
    posts = [(1990, -2940), (1990, -4900)]
    for (x, y) in posts:
        A(box((x - 24, y - 24, pz), (x + 24, y + 24, 1500), T('pine')))
    L.weapon('pumper', 900, -3120, pz, 'green')
    L.item('ammo_splasher', 1900, -4560, pz)
    L.item('item_armor_shard', 640, -4560, pz)
    L.item('ammo_nipper', 1700, -3050, pz)

    # ============================================================================================== pergola + lounge set
    gx0, gy0, gx1, gy1 = BM.PERG
    p = BM.PERG_POST
    custom_b('b_pergola')
    for (x, y) in BM.pergola_posts():
        A(box((round(x - p), round(y - p), 0), (round(x + p), round(y + p), BM.PERG_BEAM_Z), WCLIP))
    for xb in (gx0, gx1 - 2 * p):
        A(box((xb - 8, gy0 - 40, BM.PERG_BEAM_Z), (xb + 2 * p + 8, gy1 + 40, BM.PERG_TOP - 60), WCLIP))
    for (ya, yb, xa, xb) in BM.pergola_rafters():
        A(box((xa, ya, BM.PERG_TOP - 60), (xb, yb, BM.PERG_TOP), WCLIP))
    # lift up through the hatch (func_plat: drawn raised flush with the rafters, lowered into a 16u pit in the deck)
    hx0, hy0, hx1, hy1 = BM.PERG_HATCH
    plat = box((hx0 + 4, hy0 + 4, BM.PERG_TOP - 16), (hx1 - 4, hy1 - 4, BM.PERG_TOP), {'top': T('jumppad'), 'side': T('alu_track'), 'bot': T('alu_track')})
    L.hfit(plat, hx0 + 4, hy0 + 4, hx1 - 4, hy1 - 4, 256, 256, T('jumppad'))
    M.ent('func_plat', brushes=[plat], height=BM.PERG_TOP, speed=320, lip=0, noise='sound/world/plats/start.wav')
    custom_b('b_sofa')
    for (a0, b0, a1, b1, z1) in BM.SOFA_PARTS:
        A(box((round(a0), round(b0), 0), (round(a1), round(b1), z1), WCLIP))
    custom_b('b_table')
    tx0, ty0, tx1, ty1, ttop = BM.TABLE
    A(box((tx0, ty0, ttop - 30), (tx1, ty1, ttop), WCLIP))
    for (fx, fy) in ((tx0 + 30, ty0 + 30), (tx1 - 30, ty0 + 30), (tx0 + 30, ty1 - 30), (tx1 - 30, ty1 - 30)):
        A(box((fx - 18, fy - 18, 0), (fx + 18, fy + 18, ttop - 30), WCLIP))
    L.light((tx0 + tx1) / 2, (ty0 + ty1) / 2, ttop + 200, 260, '1 0.75 0.45')
    L.weapon('betty', -1240, -3500, BM.PERG_TOP, 'black')
    L.item('ammo_betty', -800, -4500, BM.PERG_TOP)
    L.item('item_armor_shard', -1700, -2900, BM.PERG_TOP)
    L.jumppad(-1240, -1920, 0, (-1240, -3420, BM.PERG_TOP), BM.PERG_TOP + 200, 'pergola')
    # more pads round the balcony (navigation): deck -> spa platform, deck -> AC top, platform <-> pergola top
    L.jumppad(100, -4450, 0, (820, -4480, BM.PLAT[4]), BM.PLAT[4] + 260, 'deck_spa')
    L.jumppad(1550, -2600, 0, (1760, -2114, BM.AC[4]), BM.AC[4] + 220, 'ac_top')
    L.item('item_armor_shard', 1320, -2114, BM.AC[4])
    L.jumppad(600, -4620, BM.PLAT[4], (-900, -4450, BM.PERG_TOP), BM.PERG_TOP + 200, 'spa_pergola')
    L.jumppad(-700, -3700, BM.PERG_TOP, (900, -3380, BM.PLAT[4]), BM.PERG_TOP + 150, 'pergola_spa')
    L.item('ammo_bubbleg', -1100, -3200, 0)                    # under the pergola, in front of the sofa
    L.item('item_armor_padshield', -1150, -4250, 0)
    L.speaker((gx0 + gx1) / 2, gy0 - 50, BM.PERG_BEAM_Z - 200, 'sound/world/misc/wind_chimes.ogg', loop=False, targetname='chimes')
    M.ent('func_timer', ((gx0 + gx1) // 2, gy0 - 50, BM.PERG_BEAM_Z - 100), target='chimes', wait=22, random=12, spawnflags=1)
    for (x, y) in ((gx0 + 300, gy0 + 500), (gx1 - 300, gy0 + 500), (gx0 + 300, gy1 - 500), (gx1 - 300, gy1 - 500)):
        L.light(x, y, BM.PERG_BEAM_Z - 220, 380, '1 0.82 0.55')

    # ============================================================================================== BBQ, AC, heater, hammock, planter
    bx, by = BM.BBQ
    custom_b('b_bbq')
    A(cyl(bx, by, 200, 0, 780, WCLIP, 16))
    A(L.sprite(bx, by, 800, 1150, 'smoke', 90))
    L.light(bx, by, 700, 220, '1 0.5 0.2')
    L.speaker(bx, by, 700, 'sound/world/ambient/fire_crackling.ogg', volume=0.5)
    L.weapon('splasher', bx + 300, by - 150, 0, 'orange')
    L.item('ammo_balloony', -1700, -2600, 0)
    ax0, ay0, ax1, ay1, atop = BM.AC
    custom_b('b_ac')
    A(box((ax0, ay0, 0), (ax1, ay1, atop), WCLIP))
    fsc, fc = SC['b_acfan']
    fx, fy, fz = (round(v) for v in fc)
    org = box((fx - 8, fy - 8, fz + 20), (fx + 8, fy + 8, fz + 36), ORIGIN)
    nd = box((fx - 8, fy - 8, fz + 36), (fx + 8, fy + 8, fz + 52), NODRAW_NS)
    M.ent('func_rotating', brushes=[org, nd], model2='models/padlounge/b_acfan.md3', speed=300, spawnflags=0, dmg=0)
    L.speaker((ax0 + ax1) / 2, (ay0 + ay1) / 2, 300, 'sound/world/machine/aircon.ogg', volume=0.5)
    L.item('ammo_pumper', 1550, -1890, 0)                       # behind the AC, where the pet flap comes out
    hx, hy = BM.HEATER
    custom_b('b_heater')
    A(cyl(hx, hy, 140, 0, 620, WCLIP, 16)); A(cyl(hx, hy, 24, 620, 1640, WCLIP, 8)); A(cyl(hx, hy, 300, 1760, 1822, WCLIP, 16))
    L.light(hx, hy, 1600, 700, '1 0.55 0.25')
    L.speaker(hx, hy, 1700, 'sound/world/ambient/fire_sizzling.ogg', volume=0.4)
    L.weapon('bubbleg', hx + 260, hy + 60, 0, 'blue')
    mx, my = BM.HAMMOCK
    custom_b('b_hammock')
    ya, yb = my - 550, my + 550
    A(box((mx - 82, ya - 20, 0), (mx + 82, ya + 80, 940), WCLIP)); A(box((mx - 82, yb - 80, 0), (mx + 82, yb + 20, 940), WCLIP))
    A(box((mx - 30, ya + 80, 0), (mx + 30, yb - 80, 60), WCLIP))
    L.item('ammo_boaster', 200, -3800, 0)
    # cover outside the door: deck box (east), big potted plant (west); a cooler by the heater
    for nm, (bx0, by0, bx1, by1, btop) in (('b_deckbox', BM.DECKBOX), ('b_cooler', BM.COOLER)):
        custom_b(nm)
        A(box((bx0 - 6, by0 - 6, 0), (bx1 + 6, by1 + 6, btop), WCLIP))
    L.custom('plant_big', -480, -2330, L.LM.PLANT_OFS, angle=70)
    A(cyl(-480, -2330, round(0.16 * 880), 0, round(0.25 * 880), WCLIP, 16))
    L.light(-480, -2330, 1300, 450, '0.8 1 0.7')
    L.custom('plant_small', 560, -2130, L.LM.PLANT_SMALL_OFS, angle=150)
    A(cyl(560, -2130, round(0.16 * 620), 0, round(0.25 * 620), WCLIP, 16))
    for k, (qx0, qy0, qx1, qy1) in enumerate(BM.PLANTERS):
        custom_b(f'b_planter{k}')
        A(box((qx0 - 10, qy0 - 10, 0), (qx1 + 10, qy1 + 10, 296), WCLIP))
    L.weapon('balloony', -100, -4690, 0, 'green')
    L.item('ammo_balloony', 1000, -2500, 0)

    # ============================================================================================== string lights
    cols = ['bulb_r', 'bulb_g', 'bulb_b', 'bulb_y', 'bulb_p']
    runs = [((-1880, YF - 10, 1760), (gx0 + 32, gy1 - 40, 1500), 160), ((-300, YF - 10, 1760), (gx1 - 32, gy1 - 40, 1500), 160),
            ((300, YF - 10, 1760), (posts[0][0], posts[0][1], 1480), 220), ((1300, YF - 10, 1760), (posts[0][0], posts[0][1], 1480), 140),
            ((posts[0][0], posts[0][1] - 30, 1480), (posts[1][0], posts[1][1] + 30, 1480), 260),
            ((gx1 - 32, gy0 + 40, 1500), (posts[1][0], posts[1][1], 1480), 300)]
    k = 0
    for (a, b, sag) in runs:
        a = np.asarray(a, float); b = np.asarray(b, float)
        n = int(np.linalg.norm(b - a) // 150)
        for i in range(1, n):
            t = i / n
            q = a + (b - a) * t; q[2] -= sag * math.sin(math.pi * t)
            A(L.deco((round(q[0]) - 8, round(q[1]) - 8, round(q[2]) - 22), (round(q[0]) + 8, round(q[1]) + 8, round(q[2])), T(cols[k % 5])))
            k += 1

    # ============================================================================================== upstairs neighbour (secret)
    nx0, ny0, nx1, ny1, nz = BM.NB
    A(box((nx0, ny0, nz - 64), (nx1, ny1, nz), {'top': T('deck'), 'side': T('concrete'), 'bot': T('concrete')}))
    A(box((nx0, ny0, nz), (nx1, ny0 + 8, 3200), CLIP))
    for (xa, xb) in ((nx0, nx0 + 8), (nx1 - 8, nx1)):
        A(box((xa, ny0 + 8, nz), (xb, ny1, 3200), CLIP))
    for k in range(4, 7): custom_b(f'b_rail{k}')
    A(sign_box((-600, YF - 4, nz), (600, YF, nz + 1200), T('nb_door'), 512, 512, facing='s', back=T('black')))
    custom_b('b_gnome')
    A(cyl(900, -2380, 70, nz, nz + 400, WCLIP, 12))
    L.mdl_c('pad_sunflower/pad_sunflower_l.md3', -1100, -2300, nz, 1.6, 30)
    L.mdl_c('pad_westernset/directors_chair.md3', -500, -2300, nz, 2.2, 250)
    L.mdl_c('pad_ddmix/plants/bonsai.md3', 400, -1990, nz, 1.2, 0)
    M.ent('misc_teleporter_dest', (0, -2350, nz + 24), targetname='nb_dest', angle=270)
    L.item('item_revival', 300, -2350, nz)
    L.item('ammo_imperius', -300, -2500, nz)
    L.item('ammo_splasher', 600, -2550, nz)
    L.item('holdable_floater', -800, -2000, nz)
    # teleporter pad back down to the deck in front of the door
    L.mdl_c('pad_teleporter/padtp_pink.md3', 1100, -2050, nz, 1.0, 90)
    M.ent('trigger_teleport', brushes=[box((1040, -2130, nz), (1160, -1970, nz + 100), TRIG)], target='nb_back')
    M.ent('misc_teleporter_dest', (0, -2650, 24), targetname='nb_back', angle=270)
    L.light(0, -2300, nz + 400, 600, '1 0.82 0.6')

    # ============================================================================================== light, sound, spawns
    for (x, y) in ((-400, -2400), (900, -2300), (-400, -3700), (300, -4500), (1200, -3000), (1500, -4600), (-1100, -3000), (-1600, -4400)):
        L.light(x, y, 1000, 900, '0.6 0.7 1')
    L.speaker(0, -4800, 700, 'sound/world/animal/cricket_chirp1.ogg', volume=0.5)
    L.speaker(0, -4900, 300, 'sound/world/ambient/city_traffic.ogg', volume=0.35)
    L.timer_sound(0, -4900, 600, 'sound/world/ambient/police_pass.ogg', 'police', 75, 40)
    L.timer_sound(-1500, -4800, 900, 'sound/world/animal/dog_bark2.ogg', 'dog', 50, 30)
    L.timer_sound(1500, -4800, 1400, 'sound/world/animal/bird_owl1.ogg', 'owl', 45, 30)
    for (x, y, z, a) in ((-300, -2300, 0, 270), (800, -2600, 0, 200), (-1600, -3050, 0, 300), (-400, -4700, 0, 60),
                         (1600, -3250, BM.PLAT[4], 220), (950, -4700, BM.PLAT[4], 120), (-900, -4300, 0, 30)):
        L.spawn(x, y, z, a)
