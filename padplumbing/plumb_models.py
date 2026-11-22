"""Custom MD3s for wop_padplumbing (6u per cm: toilet seat 252u, bath rim 330u, vanity counter 510u).

Every builder works in model space (origin on the floor at the piece's footprint centre, +y toward the wall it backs
onto) and returns the collision in the same space as {'boxes': [(mn, mx)], 'cyls': [(cx, cy, r, z0, z1)]} so the
generator places visual + weapclip with one K.custom call. Textures are original procedural art (woplib.texlib).
"""
import math
import numpy as np
from meshlib import Mesh, revolve, disc, tube, rbox, ellipsoid, prism
from woplib import models as ML, texlib as TL

M = {}          # material key -> model shader (filled by materials())
COL = {}        # model name -> collision dict


# ------------------------------------------------------------------------------------------------ helpers
def flip(src):
    """copy of a mesh with normals inverted (inner surfaces of tubs and basins)"""
    out = Mesh()
    for v, n, st in zip(src.V, src.N, src.ST): out.add_v(v, -np.asarray(n), st)
    out.T = [(a, c, b) for (a, b, c) in src.T]
    return out


def scaled(build, sc):
    """build(mesh) in a scratch mesh, then add it scaled (sx, sy, sz): elliptical lathes (normals fixed by Mesh.add)"""
    tmp = Mesh(); build(tmp)
    return tmp, np.asarray(sc, float)


def rrect(x0, y0, x1, y1, r, k=6):
    """rounded rectangle outline, counter-clockwise, 4*(k+1) points (same count for any size -> rings line up)"""
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def wall(Mm, pts, z0, z1, outward=True, tile=128.0):
    """vertical band along a closed outline with smooth per-vertex normals"""
    n = len(pts); P = np.array(pts, float)
    L = 0.0
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        na = P[(i + 1) % n] - P[i - 1]; nb = P[(i + 2) % n] - P[i]
        nna = np.array([na[1], -na[0], 0.0]); nnb = np.array([nb[1], -nb[0], 0.0])
        if not outward: nna, nnb = -nna, -nnb
        ln = np.linalg.norm(b - a)
        o = len(Mm.V)
        Mm.add_v((a[0], a[1], z0), nna, (L / tile, -z0 / tile)); Mm.add_v((b[0], b[1], z0), nnb, ((L + ln) / tile, -z0 / tile))
        Mm.add_v((b[0], b[1], z1), nnb, ((L + ln) / tile, -z1 / tile)); Mm.add_v((a[0], a[1], z1), nna, (L / tile, -z1 / tile))
        Mm.tri(o, o + 1, o + 2); Mm.tri(o, o + 2, o + 3)
        L += ln


def ring(Mm, outer, inner, z, up=True, tile=128.0):
    """flat band between two outlines with the same point count"""
    n = len(outer); nz = (0, 0, 1 if up else -1)
    for i in range(n):
        q = [outer[i], outer[(i + 1) % n], inner[(i + 1) % n], inner[i]]
        Mm.poly([(p[0], p[1], z) for p in q], nz, [(p[0] / tile, -p[1] / tile) for p in q])


def cap(Mm, pts, z, up=True, tile=128.0):
    Mm.poly([(p[0], p[1], z) for p in pts], (0, 0, 1 if up else -1), [(p[0] / tile, -p[1] / tile) for p in pts])


def lathe_into(X, sh, prof, sc=(1, 1, 1), t=(0, 0, 0), n=40, inward=False, R=np.eye(3), u_tiles=2.0):
    tmp = Mesh(); revolve(tmp, prof, n=n, inward=inward, u_tiles=u_tiles)
    X.mesh(sh).add(tmp, R, t, sc)


def rot_x(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def circle_path(c, r, n=24, plane='yz'):
    out = []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        if plane == 'yz': out.append((c[0], c[1] + r * math.cos(a), c[2] + r * math.sin(a)))
        elif plane == 'xz': out.append((c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)))
        else: out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
    return out


def save(name, X, boxes=(), cyls=()):
    place = ML.save(name, X)
    COL[name] = dict(boxes=list(boxes), cyls=list(cyls))
    return place


# ------------------------------------------------------------------------------------------------ materials
def materials(TX):
    m = TX.material
    M['porcelain'] = m('porcelain', TL.solid((236, 238, 240), 3, 5), 'lms', v=0.16, shade=60)
    M['chrome'] = m('chrome', TL.metal((196, 200, 208), seed=3), 'lms', v=0.5)
    M['copper'] = m('copper', TL.grime(TL.metal((192, 112, 64), seed=5), 0.18), 'lms', v=0.25)
    M['brass'] = m('brass', TL.metal((206, 168, 72), seed=7), 'lms', v=0.3)
    M['pvc'] = m('pvc', TL.grime(TL.solid((186, 190, 184), 4, 9), 0.2), shade=70)
    M['pvc_in'] = m('pvc_in', TL.grime(TL.stripes((150, 154, 146), (128, 132, 124), 4, vertical=False, soft=0.4), 0.35))
    M['cabinet'] = m('cabinet', TL.planks((236, 232, 222), n_planks=2, gap=(200, 196, 186), grain=4), shade=30)
    M['cab_in'] = m('cab_in', TL.planks((176, 130, 86), n_planks=4), shade=30)
    M['marble'] = m('marble', TL.stone((228, 224, 216), cells=8, edge=(196, 192, 186), vary=6), 'lms', v=0.12, shade=30)
    M['mirror'] = m('mirror', mirror_tex(), 'lms', v=0.75, shade=20)
    M['rubber'] = m('rubber', TL.solid((252, 206, 30), 3, 11), 'lms', v=0.12)
    M['beak'] = m('beak', TL.solid((240, 120, 30), 3, 13))
    M['eye'] = m('eye', TL.solid((20, 20, 26), 2, 15), 'lms', v=0.4)
    M['sponge'] = m('sponge', TL.dots((250, 220, 70), (210, 170, 40), n_dots=10, r=0.12))
    M['scrub'] = m('scrub', TL.fabric((50, 150, 70), weave=48))
    M['soap'] = m('soap', TL.solid((244, 150, 180), 3, 17), 'lms', v=0.14)
    M['paper'] = m('paper', TL.stripes((246, 244, 236), (232, 230, 222), 16, vertical=False, soft=0.6))
    M['card'] = m('card', TL.solid((150, 118, 80), 4, 19))
    M['wicker'] = m('wicker', TL.fabric((186, 146, 96), weave=24, seed=7))
    M['matfab'] = m('matfab', TL.fabric((70, 130, 190), weave=96, seed=9))
    M['enamel'] = m('enamel', TL.grime(TL.solid((228, 230, 226), 3, 21), 0.12), 'lms', v=0.12, shade=60)
    M['heater_lbl'] = m('heater_lbl', TL.label('PADTHERM 9000', 512, 128, (40, 70, 140), (255, 255, 255),
                                                  border=(255, 210, 40)), lathe=True)
    M['rust'] = m('rust', TL.grime(TL.metal((120, 70, 44), seed=11), 0.4))
    M['steel'] = m('steel', TL.grime(TL.metal((120, 130, 140), seed=13), 0.25), 'lms', v=0.15)
    M['red'] = m('red', TL.solid((200, 40, 36), 3, 23), 'lms', v=0.15)
    M['blue'] = m('blue', TL.solid((40, 90, 190), 3, 25), 'lms', v=0.15)
    M['yellowp'] = m('yellowp', TL.solid((240, 196, 30), 3, 27), shade=40)
    M['blackp'] = m('blackp', TL.solid((34, 34, 38), 3, 29))
    M['plank'] = m('plank', TL.grime(TL.planks((132, 96, 60), n_planks=1, grain=12), 0.25), steps='woodsteps', shade=30)
    M['water_add'] = m('water_add', TL.solid((40, 90, 110), 8, 31), 'add', tcmod='scroll 0.02 0.03')
    M['sewer_add'] = m('sewer_add', TL.solid((40, 70, 36), 8, 33), 'add', tcmod='scroll 0.05 0.0')
    M['glass'] = m('glass', TL.solid((170, 210, 220), 2, 35), 'glass', c='0.10 0.13 0.14')
    M['dark'] = m('dark', TL.solid((14, 14, 16), 2, 37), shade=20)
    M['bulb'] = m('bulb', TL.solid((255, 240, 190), 2, 39), 'glow')
    M['grate'] = m('grate', grate_tex(), 'alpha', alpha=grate_alpha())
    M['falls'] = m('falls', falls_tex(), 'flow', alpha=falls_alpha(), speed=-1.4)
    M['bricks_m'] = m('bricks_m', TL.grime(TL.bricks((120, 64, 50), (110, 104, 96), rows=8, cols=4), 0.3), shade=30)


def mirror_tex(n=128):
    x, y = ML.xy(n)
    c = ML.C((110, 132, 146)) + (np.sin((x + y) * 9) * 10)[..., None]
    return c + ML.N3(n, 2, 41, 3)


def grate_tex(n=128):
    return TL.metal((96, 100, 106), seed=43, n=n)


def grate_alpha(n=128):
    x, y = ML.xy(n)
    bars = ((x * 8) % 1 < 0.28) | ((y * 8) % 1 < 0.28)
    return np.where(bars, 255, 0).astype(np.uint8)


def falls_tex(n=128):
    x, y = ML.xy(n)
    streak = 0.5 + 0.5 * np.sin(x * 40 + np.sin(y * 6.28) * 2)
    return ML.C((90, 120, 80)) + streak[..., None] * ML.C((60, 70, 40)) + ML.N3(n, 1, 45, 8)


def falls_alpha(n=128):
    x, y = ML.xy(n)
    a = 150 + 70 * np.sin(x * 40 + np.sin(y * 6.28) * 2)
    return np.clip(a, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------------------------------------ bathroom fixtures
SEAT_Z = 252            # toilet seat top (collision top of the bowl ring)
CISTERN_Z = 492         # cistern lid top
HOLE = (60, 90)         # bowl hole half sizes (x, y)
BOWL_FLOOR = 120


def toilet():
    """bowl centre at the origin, cistern toward +y (the wall at y 312). Walk off the seat into the hole = flush."""
    X = ML.Model()
    P, C_ = M['porcelain'], M['chrome']
    sy = 1.45
    lathe_into(X, P, [(58, 0), (62, 8), (50, 50), (48, 120), (66, 176), (100, 214), (118, 232), (118, 236)], sc=(1, sy, 1))
    lathe_into(X, P, [(64, 236), (56, 200), (40, 160), (26, 132), (0, BOWL_FLOOR + 8)], sc=(1, sy, 1), inward=True)
    # seat ring + rim band
    lathe_into(X, M['porcelain'], [(122, 236), (124, 244), (120, SEAT_Z), (66, SEAT_Z), (62, 244), (64, 236)], sc=(1, sy, 1))
    tmp = Mesh(); disc(tmp, 40, 150, n=32); X.mesh(M['water_add']).add(tmp, np.eye(3), (0, 0, 0), (1, sy, 1))
    rbox(X.mesh(P), (-105, 160, SEAT_Z), (105, 180, CISTERN_Z), r=18, k=3)                # lid, up against the cistern
    rbox(X.mesh(P), (-160, 180, 260), (160, 312, 480), r=18, k=3)                   # cistern
    rbox(X.mesh(P), (-166, 174, 480), (166, 312, CISTERN_Z), r=6, k=2)
    lathe_into(X, C_, [(22, CISTERN_Z), (22, CISTERN_Z + 6), (0, CISTERN_Z + 6)], t=(60, 245, 0), n=20)
    rbox(X.mesh(P), (-60, 175, 0), (60, 300, 262), r=14, k=2)                       # back of the pedestal
    tube(X.mesh(C_), [(-120, 290, 300), (-200, 290, 300), (-200, 290, 0)], 12, nseg=10)   # supply pipe into the floor
    boxes = [((-120, -175, 0), (120, -HOLE[1], SEAT_Z)), ((-120, HOLE[1], 0), (120, 178, SEAT_Z)),
             ((-120, -HOLE[1], 0), (-HOLE[0], HOLE[1], SEAT_Z)), ((HOLE[0], -HOLE[1], 0), (120, HOLE[1], SEAT_Z)),
             ((-HOLE[0], -HOLE[1], 0), (HOLE[0], HOLE[1], BOWL_FLOOR)),
             ((-105, 160, SEAT_Z), (105, 178, CISTERN_Z)), ((-160, 178, 260), (160, 312, CISTERN_Z)), ((-60, 178, 0), (60, 312, 260))]
    return save('toilet', X, boxes)


TUB = dict(hx=510, hy=225, rim=330, wall=40, floor=26)


def bathtub():
    """built-in tub, rim 330, inner floor 26; the steps, caddy board and water are brushes added by the generator"""
    X = ML.Model()
    hx, hy, rim, w, fl = TUB['hx'], TUB['hy'], TUB['rim'], TUB['wall'], TUB['floor']
    P = M['porcelain']
    out = rrect(-hx, -hy, hx, hy, 60); inn = rrect(-hx + w, -hy + w, hx - w, hy - w, 30)
    wall(X.mesh(P), out, 0, rim - 10)
    ring(X.mesh(P), out, rrect(-hx - 6, -hy - 6, hx + 6, hy + 6, 66), rim - 10, up=False)
    wall(X.mesh(P), rrect(-hx - 6, -hy - 6, hx + 6, hy + 6, 66), rim - 10, rim)
    ring(X.mesh(P), rrect(-hx - 6, -hy - 6, hx + 6, hy + 6, 66), inn, rim)
    wall(X.mesh(P), inn, fl, rim, outward=False)
    cap(X.mesh(P), inn, fl)
    # plughole + chain, taps on the west rim
    disc(X.mesh(M['chrome']), 26, fl + 1, cx=-hx + 80, n=20)
    disc(X.mesh(M['dark']), 16, fl + 2, cx=-hx + 80, n=16)
    tube(X.mesh(M['chrome']), [(-hx + 20, 0, rim), (-hx + 20, 0, rim + 90), (-hx + 50, 0, rim + 120), (-hx + 100, 0, rim + 108)], 12, nseg=12)
    for yy in (-70, 70):
        lathe_into(X, M['chrome'], [(18, 0), (18, 40), (30, 50), (30, 60), (0, 62)], t=(-hx + 20, yy, rim), n=16)
    b = [((-hx, -hy, 0), (-hx + w, hy, rim)), ((hx - w, -hy, 0), (hx, hy, rim)),
         ((-hx + w, -hy, 0), (hx - w, -hy + w, rim)), ((-hx + w, hy - w, 0), (hx - w, hy, rim)),
         ((-hx + w, -hy + w, 0), (hx - w, hy - w, fl))]
    return save('bathtub', X, b)


VAN = dict(hx=240, hy=180, top=510, slab=462, basin=(100, -92, 88), basin_floor=478,
           mirror=(-180, 40, 660, 180, 180, 1080))


def vanity():
    """open vanity cabinet (walk in under the basin), marble counter with a square basin, mirror cabinet above"""
    X = ML.Model()
    hx, hy = VAN['hx'], VAN['hy']; top, slab = VAN['top'], VAN['slab']
    bx, by0, by1 = VAN['basin']; bf = VAN['basin_floor']
    cab, inn, mar = M['cabinet'], M['cab_in'], M['marble']
    pieces = [((-hx, -hy, 0), (-hx + 24, hy, slab)), ((hx - 24, -hy, 0), (hx, hy, slab)),
              ((-hx + 24, hy - 24, 0), (hx - 24, hy, slab)), ((-hx + 24, -hy, 0), (hx - 24, hy - 24, 18)),
              ((-hx + 24, -hy, slab - 16), (hx - 24, hy - 24, slab))]
    for mn, mx in pieces: rbox(X.mesh(inn), mn, mx, r=3, k=1, tile=96)
    rbox(X.mesh(cab), (-hx, -hy, 0), (-hx + 24, -hy + 4, slab), r=2, k=1)              # painted front stiles
    rbox(X.mesh(cab), (hx - 24, -hy, 0), (hx, -hy + 4, slab), r=2, k=1)
    for sgn in (-1, 1):                                                                 # doors open 90 degrees
        x0 = sgn * hx
        rbox(X.mesh(cab), (min(x0, x0 + sgn * 16), -hy - 216, 8), (max(x0, x0 + sgn * 16), -hy, slab - 12), r=4, k=2)
        lathe_into(X, M['chrome'], [(8, 0), (8, 30), (0, 32)], R=rot_y(90 * sgn), t=(x0 + sgn * 16, -hy - 190, 260), n=10)
    counter = [((-hx - 12, -hy - 16, slab), (hx + 12, by0, top)), ((-hx - 12, by1, slab), (hx + 12, hy, top)),
               ((-hx - 12, by0, slab), (-bx, by1, top)), ((bx, by0, slab), (hx + 12, by1, top))]
    for mn, mx in counter: rbox(X.mesh(mar), mn, mx, r=3, k=1, tile=192)
    binn = rrect(-bx, by0, bx, by1, 24)
    wall(X.mesh(M['porcelain']), binn, bf, top + 1, outward=False)
    cap(X.mesh(M['porcelain']), binn, bf)
    disc(X.mesh(M['chrome']), 18, bf + 1, cy=(by0 + by1) / 2, n=16)
    # tap on the back strip
    ty = (by1 + hy) / 2
    lathe_into(X, M['chrome'], [(22, 0), (22, 20), (12, 26), (12, 90), (0, 92)], t=(0, ty, top), n=16)
    tube(X.mesh(M['chrome']), [(0, ty, top + 80), (0, ty - 40, top + 100), (0, by1 - 30, top + 70)], 9, nseg=10)
    for xx in (-56, 56): lathe_into(X, M['chrome'], [(14, 0), (14, 26), (22, 34), (0, 38)], t=(xx, ty, top), n=12)
    # P-trap inside the cabinet
    cy_ = (by0 + by1) / 2
    tube(X.mesh(M['chrome']), [(0, cy_, bf), (0, cy_, 200), (0, cy_ + 40, 150), (0, cy_ + 80, 200), (0, hy - 30, 200),
                               (0, hy - 24, 0)], 14, nseg=12)
    # mirror cabinet
    mx0, my0, mz0, mx1, my1, mz1 = VAN['mirror']
    rbox(X.mesh(cab), (mx0, my0, mz0), (mx1, my1, mz1), r=8, k=2)
    X.mesh(M['mirror']).quad((mx0 + 18, my0 - 1, mz0 + 18), (mx1 - 18, my0 - 1, mz0 + 18), (mx1 - 18, my0 - 1, mz1 - 18),
                             (mx0 + 18, my0 - 1, mz1 - 18), tile=200, n=np.array([0, -1.0, 0]))
    b = pieces + [((-hx - 12, -hy - 16, slab), (hx + 12, by0, top)), ((-hx - 12, by1, slab), (hx + 12, hy, top)),
                  ((-hx - 12, by0, slab), (-bx, by1, top)), ((bx, by0, slab), (hx + 12, by1, top)),
                  ((-bx, by0, slab), (bx, by1, bf)), ((mx0, my0, mz0), (mx1, my1, mz1))]
    for sgn in (-1, 1):
        x0 = sgn * hx
        b.append(((min(x0, x0 + sgn * 16), -hy - 216, 8), (max(x0, x0 + sgn * 16), -hy, slab - 12)))
    return save('vanity', X, b, cyls=[(0, cy_, 18, 18, slab - 16)])


def hamper():
    X = ML.Model()
    out = rrect(-110, -110, 110, 110, 40)
    wall(X.mesh(M['wicker']), out, 0, 330, tile=96)
    lid = rrect(-118, -118, 118, 118, 44)
    wall(X.mesh(M['wicker']), lid, 330, 352, tile=96)
    cap(X.mesh(M['wicker']), lid, 352); cap(X.mesh(M['wicker']), lid, 330, up=False)
    tube(X.mesh(M['matfab']), [(80, -118, 300), (110, -150, 200), (130, -122, 120)], 14, nseg=10)   # sleeve hanging out
    return save('hamper', X, [((-110, -110, 0), (110, 110, 352))])


def pedal_bin():
    X = ML.Model()
    lathe_into(X, M['chrome'], [(70, 0), (74, 6), (74, 180), (66, 190), (40, 196), (0, 198)], n=32)
    rbox(X.mesh(M['blackp']), (-30, -96, 0), (30, -70, 10), r=4, k=1)
    return save('pedal_bin', X, cyls=[(0, 0, 74, 0, 198)])


def stool():
    X = ML.Model()
    rbox(X.mesh(M['cab_in']), (-110, -80, 120), (110, 80, 144), r=6, k=2)
    for sx in (-1, 1):
        rbox(X.mesh(M['cab_in']), (sx * 110 - (12 if sx > 0 else -12) - 6, -80, 0), (sx * 110 - (12 if sx > 0 else -12) + 6, 80, 120), r=3, k=1)
    rbox(X.mesh(M['cab_in']), (-96, -6, 40), (96, 6, 60), r=2, k=1)
    return save('stool', X, [((-110, -80, 0), (110, 80, 144))])


def mop_bucket():
    X = ML.Model()
    lathe_into(X, M['yellowp'], [(90, 0), (96, 10), (110, 170), (104, 176), (100, 170), (86, 30), (0, 28)], n=32)
    tmp = Mesh(); disc(tmp, 92, 140, n=28); X.mesh(M['sewer_add']).add(tmp)
    tube(X.mesh(M['steel']), [(-104, 0, 170), (-60, 0, 240), (60, 0, 240), (104, 0, 170)], 5, nseg=8)
    rbox(X.mesh(M['red']), (-40, -60, 176), (40, 60, 230), r=8, k=2)                  # wringer
    return save('mop_bucket', X, cyls=[(0, 0, 108, 0, 176)])


def scale_box():
    X = ML.Model()
    rbox(X.mesh(M['porcelain']), (-80, -100, 0), (80, 100, 28), r=12, k=2)
    disc(X.mesh(M['dark']), 26, 28.5, cy=-60, n=20)
    return save('bath_scale', X)


def bathmat():
    X = ML.Model()
    rbox(X.mesh(M['matfab']), (-220, -130, 0), (220, 130, 4), r=2, k=1, tile=128)
    return save('bathmat', X)


def fan_frame():
    """extractor fan housing on the north wall (blades are a separate rotating model)"""
    X = ML.Model()
    rbox(X.mesh(M['porcelain']), (-110, -16, -110), (110, 0, 110), r=10, k=2)
    disc_m = Mesh(); disc(disc_m, 86, 0, n=28)
    X.mesh(M['dark']).add(disc_m, rot_x(90), (0, -17, 0))
    ML.save('fan_frame', X)
    B = ML.Model()
    for k in range(5):
        a = 2 * math.pi * k / 5
        R = np.array([[math.cos(a), 0, -math.sin(a)], [0, 1, 0], [math.sin(a), 0, math.cos(a)]])
        blade = Mesh(); rbox(blade, (8, -3, -14), (80, 3, 14), r=2, k=1)
        B.mesh(M['porcelain']).add(blade, R, (0, 0, 0))
    lathe_into(B, M['chrome'], [(14, -8), (14, 4), (0, 6)], R=rot_x(-90), n=12)
    ML.save('fan_blades', B)


# ------------------------------------------------------------------------------------------------ pipes + plant
def pipe_run(name, pts, r, sh='copper', collide=False, brackets=False):
    """generic pipe along a polyline (local coords = world offsets from pts[0]); returns place"""
    X = ML.Model()
    o = np.array(pts[0], float)
    rel = [np.array(p, float) - o for p in pts]
    tube(X.mesh(M[sh]), rel, r, nseg=14)
    for p in rel[1:-1]:                                               # elbow collars
        lathe_into(X, M[sh], [(r + 5, -8), (r + 5, 8)], t=p, n=14)
    return ML.save(name, X), o


def soil_stack():
    """the toilet's soil pipe: down from the bathroom floor, along to the drain tunnel (local origin at the floor
    hole, z measured from the crawlspace floor)"""
    X = ML.Model()
    path = [(0, 0, 480), (0, 0, 330), (0, -60, 300), (0, -380, 300), (0, -420, 260), (0, -420, 220)]
    tube(X.mesh(M['pvc']), path, 46, nseg=18)
    for p in path[1:-1]: lathe_into(X, M['pvc'], [(54, -12), (54, 12)], t=p, n=18)
    for z in (440, 360): lathe_into(X, M['steel'], [(52, -6), (52, 6)], t=(0, 0, z), n=16)
    return save('soil_stack', X)


def water_heater():
    X = ML.Model()
    H, R = 960, 220
    lathe_into(X, M['enamel'], [(212, 0), (R, 14), (R, H - 30), (214, H - 12), (196, H), (0, H)], n=48, u_tiles=4)
    lathe_into(X, M['steel'], [(R + 4, 0), (R + 4, 40)], n=48)
    lathe_into(X, M['heater_lbl'], [(R + 1, 520), (R + 1, 650)], n=48, u_tiles=2)
    lathe_into(X, M['steel'], [(R + 3, 518), (R + 3, 522)], n=48); lathe_into(X, M['steel'], [(R + 3, 648), (R + 3, 652)], n=48)
    # gauge + relief valve facing -x (the walkway side)
    lathe_into(X, M['chrome'], [(40, 0), (40, 14), (0, 16)], R=rot_y(-90), t=(-R, 0, 760), n=20)
    disc_m = Mesh(); disc(disc_m, 34, 0, n=20); X.mesh(M['porcelain']).add(disc_m, rot_y(-90), (-R - 17, 0, 760))
    tube(X.mesh(M['red']), [(-R - 18, 0, 760), (-R - 18, 18, 784)], 3, nseg=6)
    tube(X.mesh(M['brass']), [(-R + 10, 120, 820), (-R - 40, 120, 820), (-R - 40, 120, 60)], 12, nseg=10)
    # copper pipes to the south wall and up into the ceiling
    for dx in (-90, 90):
        tube(X.mesh(M['copper']), [(dx, -R + 10, 880), (dx, -312, 880), (dx, -312, 1990)], 16, nseg=12)
    return save('water_heater', X, cyls=[(0, 0, R, 0, H)])


def pump():
    """sump pump on a skid; the flywheel is a separate rotating model at local (-190, 0, 140)"""
    X = ML.Model()
    rbox(X.mesh(M['steel']), (-170, -130, 0), (170, 130, 40), r=6, k=2)
    tube(X.mesh(M['blue']), [(-150, 0, 150), (70, 0, 150)], 90, nseg=24)
    for xx in range(-130, 60, 30): lathe_into(X, M['steel'], [(94, -4), (94, 4)], R=rot_y(90), t=(xx, 0, 150), n=24)
    lathe_into(X, M['red'], [(0, -60), (110, -60), (110, 60), (0, 60)], R=rot_y(90), t=(130, 0, 150), n=28)
    tube(X.mesh(M['steel']), [(-180, 0, 150), (-150, 0, 150)], 18, nseg=10)
    tube(X.mesh(M['pvc']), [(130, 0, 260), (130, 0, 420), (130, 120, 520), (130, 120, 1990)], 40, nseg=16)
    tube(X.mesh(M['pvc']), [(240, 0, 150), (320, 0, 150), (360, 0, 100), (360, 0, 0)], 40, nseg=16)
    rbox(X.mesh(M['yellowp']), (-60, -132, 60), (40, -131, 110), r=1, k=1)
    ML.save('pump', X)
    W = ML.Model()
    lathe_into(W, M['red'], [(0, -10), (70, -10), (70, 10), (0, 10)], R=rot_y(90), n=24)
    for k in range(4):
        a = math.pi / 2 * k
        tube(W.mesh(M['steel']), [(-12, 0, 0), (-12, 64 * math.cos(a), 64 * math.sin(a))], 7, nseg=6)
    ML.save('flywheel', W)
    COL['pump'] = dict(boxes=[((-170, -130, 0), (170, 130, 250)), ((240, -40, 0), (400, 40, 190)), ((-266, -76, 70), (-170, 76, 230))], cyls=[(130, 0, 44, 250, 520)])
    return ML.PLACE['pump']


def outflow():
    """big outflow mouth on the west sewer wall (facing +x) with a waterfall sheet down to the canal"""
    X = ML.Model()
    lathe_into(X, M['rust'], [(110, 0), (130, 0), (130, 40), (110, 40), (96, 10)], R=rot_y(90), n=32)
    disc_m = Mesh(); disc(disc_m, 100, 0, n=28); X.mesh(M['dark']).add(disc_m, rot_y(90), (2, 0, 0))
    gx = Mesh(); disc(gx, 100, 0, n=28)
    X.mesh(M['grate']).add(gx, rot_y(90), (30, 0, 0))
    X.mesh(M['falls']).quad((44, -70, -40), (44, 70, -40), (120, 70, -230), (120, -70, -230), tile=140)
    return save('outflow', X)


def bulb():
    """hanging bulb for func_pendulum (geometry hangs below the pivot at the origin)"""
    X = ML.Model()
    tube(X.mesh(M['blackp']), [(0, 0, 0), (0, 0, -150)], 2, nseg=6)
    lathe_into(X, M['blackp'], [(10, -150), (10, -170)], n=12)
    lathe_into(X, M['bulb'], [(10, -170), (20, -182), (22, -196), (14, -210), (0, -214)], n=16)
    ML.save('bulb', X)


def valve_wheel():
    """red hand wheel facing -x (model2 on the func_button)"""
    X = ML.Model()
    tube(X.mesh(M['red']), circle_path((-20, 0, 0), 44, 28, 'yz'), 6, nseg=8, caps=(False, False))
    for k in range(5):
        a = 2 * math.pi * k / 5
        tube(X.mesh(M['red']), [(-20, 0, 0), (-20, 44 * math.cos(a), 44 * math.sin(a))], 4, nseg=6)
    lathe_into(X, M['steel'], [(12, 0), (12, 24), (0, 26)], R=rot_y(-90), n=12)
    ML.save('valve_wheel', X)


def gauge_panel():
    X = ML.Model()
    rbox(X.mesh(M['steel']), (-4, -70, -50), (0, 70, 50), r=2, k=1)
    for yy in (-36, 36):
        d = Mesh(); disc(d, 26, 0, n=18); X.mesh(M['porcelain']).add(d, rot_y(-90), (-6, yy, 0))
        tube(X.mesh(M['red']), [(-7, yy, 0), (-7, yy + 12, 16)], 2, nseg=5)
    ML.save('gauge_panel', X)


# ------------------------------------------------------------------------------------------------ sewer pieces
def plank_bridge(L, W):
    """planks across the canal (local y spans the canal -L/2..L/2, x the width); collision is the deck brush"""
    X = ML.Model()
    y = -L / 2
    i = 0
    while y < L / 2 - 1:
        y1 = min(y + 38, L / 2)
        dz = (i % 3) * 0.7
        rbox(X.mesh(M['plank']), (-W / 2, y + 2, -16 + dz), (W / 2, y1 - 2, dz), r=2, k=1, tile=128)
        y = y1; i += 1
    for sx in (-1, 1):
        rbox(X.mesh(M['plank']), (sx * W / 2 - 10, -L / 2 - 30, -36), (sx * W / 2 + 10, L / 2 + 30, -16), r=2, k=1, tile=256)
    return save('plank_bridge', X)


def pipe_bridge(L, W):
    X = ML.Model()
    tube(X.mesh(M['rust']), [(0, -L / 2 - 40, -90), (0, L / 2 + 40, -90)], 72, nseg=20)
    for y in np.linspace(-L / 2 + 40, L / 2 - 40, 4):
        lathe_into(X, M['steel'], [(78, -8), (78, 8)], R=rot_x(90), t=(0, y, -90), n=20)
        rbox(X.mesh(M['steel']), (-W / 2, y - 6, -24), (W / 2, y + 6, -4), r=1, k=1)
    rbox(X.mesh(M['grate']), (-W / 2, -L / 2, -4), (W / 2, L / 2, 0), r=0.5, k=1, tile=64)
    for sx in (-1, 1):
        rbox(X.mesh(M['steel']), (sx * W / 2 - 6, -L / 2, -24), (sx * W / 2 + 6, L / 2, 0), r=1, k=1)
    return save('pipe_bridge', X)


def crate():
    X = ML.Model()
    rbox(X.mesh(M['card']), (-90, -70, 0), (90, 70, 120), r=4, k=1, tile=128)
    rbox(X.mesh(M['yellowp']), (-91, -30, 118), (91, 30, 121), r=1, k=1)
    rbox(X.mesh(M['card']), (-60, -60, 120), (70, 60, 220), r=4, k=1, tile=128)
    return save('crates', X, [((-90, -70, 0), (90, 70, 120)), ((-60, -60, 120), (70, 60, 220))])


# ------------------------------------------------------------------------------------------------ jump pad dressings
def pad_duck():
    X = ML.Model()
    ellipsoid(X.mesh(M['rubber']), (0, -10, 28), 44, 56, 34, flat_bottom=-28)
    ellipsoid(X.mesh(M['rubber']), (0, 34, 80), 26, 26, 26)
    ellipsoid(X.mesh(M['beak']), (0, 60, 76), 14, 16, 6)
    for sx in (-12, 12): ellipsoid(X.mesh(M['eye']), (sx, 52, 90), 5, 4, 5)
    return ML.save('pad_duck', X)


def pad_looroll():
    X = ML.Model()
    lathe_into(X, M['paper'], [(30, 0), (70, 0), (74, 4), (74, 52), (70, 56), (30, 56), (30, 0)], n=32, u_tiles=3)
    disc(X.mesh(M['card']), 30, 54, n=24, r_in=22)
    X.mesh(M['paper']).quad((-20, -74, 1), (20, -74, 1), (24, -150, 1), (-24, -150, 1), tile=64, n=np.array([0, 0, 1.0]))
    return ML.save('pad_looroll', X)


def pad_soap():
    X = ML.Model()
    rbox(X.mesh(M['soap']), (-64, -42, 0), (64, 42, 30), r=14, k=3)
    for p in [(-70, 30, 10), (66, -36, 12), (40, 50, 8), (-50, -50, 6)]:
        ellipsoid(X.mesh(M['porcelain']), p, 10, 10, 9)                               # suds
    return ML.save('pad_soap', X)


def pad_sponge():
    X = ML.Model()
    rbox(X.mesh(M['sponge']), (-58, -40, 0), (58, 40, 30), r=8, k=2)
    rbox(X.mesh(M['scrub']), (-58, -40, 30), (58, 40, 40), r=3, k=1)
    return ML.save('pad_sponge', X)


def pad_valve():
    X = ML.Model()
    lathe_into(X, M['brass'], [(46, 0), (46, 10), (30, 14), (24, 30), (0, 30)], n=24)
    helix = [(18 * math.cos(t), 18 * math.sin(t), 30 + t * 3) for t in np.linspace(0, 6 * math.pi, 60)]
    tube(X.mesh(M['steel']), helix, 3, nseg=6)
    lathe_into(X, M['red'], [(26, 86), (26, 96), (0, 98)], n=20)
    return ML.save('pad_valve', X)


def pad_plunger():
    X = ML.Model()
    lathe_into(X, M['red'], [(60, 0), (56, 18), (36, 40), (12, 48), (0, 48)], n=28)
    tube(X.mesh(M['cab_in']), [(0, 0, 46), (0, 0, 60)], 8, nseg=8)
    return ML.save('pad_plunger', X)


def build_all(TX, bridge_len, bridge_w):
    materials(TX)
    toilet(); bathtub(); vanity(); hamper(); pedal_bin(); stool(); mop_bucket(); scale_box(); bathmat(); fan_frame()
    soil_stack(); water_heater(); pump(); outflow(); bulb(); valve_wheel(); gauge_panel()
    plank_bridge(bridge_len, bridge_w); pipe_bridge(bridge_len, bridge_w); crate()
    pad_duck(); pad_looroll(); pad_soap(); pad_sponge(); pad_valve(); pad_plunger()
