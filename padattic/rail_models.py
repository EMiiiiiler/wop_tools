"""MD3 / IQM models for wop_padattic ("Attic Express"): a big garden-scale model railway at Padman scale.

    make(out) -> writes models/padattic/*.md3 (+ the train loop IQM via train_loop()) and their textures,
                 returns the shader text

Local frames: x forward (rolling stock) / x outward (portal), z = 0 on the surface the model stands on. Rolling stock
stands with its wheels on the rail top (z 0 = rail top), centred between the rails.

  loco.md3          steam locomotive: frame, red driving wheels with spokes, cylinders + rods, green boiler with
                    brass bands, black smokebox with door + number plate, chimney, brass dome, cab with lined
                    panels and a curved roof, red buffer beams, buffers, cowcatcher, glowing headlamp
  tender.md3        coal tender (lined sides, coal heap, three axles)
  carriage.md3      passenger carriage: maroon/cream panelled body, warm lit windows, clerestory roof, two bogies
  track_arc.md3     45 deg of the R 1000 circle (ties + two rails, gauge 48), origin on the circle at mid-arc
  track_straight.md3  512u straight (sidings)
  pine.md3          garden-railway pine: trunk + four jagged cone tiers (~250u)
  portal.md3        stone tunnel portal facade: arch opening 144 wide, springline 168, pilasters, keystone, cornice
  water_tower.md3   timber tank on four legs, iron hoops, conical roof, swinging spout
  signal.md3        semaphore signal: post, ladder, red/white arm, lamp
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import md3write, iqmtool

MD = 'models/padattic'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB): FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONTS = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'

TRACK_R, GAUGE = 1000.0, 48.0
# rolling stock: (model, x extent min, max, collision top)
STOCK = {'loco': (-182.0, 238.0, 180.0), 'tender': (-130.0, 130.0, 146.0), 'carriage': (-182.0, 182.0, 186.0)}


# ------------------------------------------------------------------------------------------------ mesh builder
class Mesh:
    def __init__(self):
        self.V, self.N, self.ST, self.T = [], [], [], []

    def __len__(self): return len(self.V)

    def add_v(self, p, n, uv):
        n = np.asarray(n, float); l = np.linalg.norm(n)
        self.V.append(np.asarray(p, float)); self.N.append(n / l if l > 1e-9 else np.array([0, 0, 1.0]))
        self.ST.append((float(uv[0]), float(uv[1]))); return len(self.V) - 1

    def tri(self, a, b, c):
        V = self.V
        fn = np.cross(V[c] - V[a], V[b] - V[a])
        if np.linalg.norm(fn) < 1e-9: return
        want = self.N[a] + self.N[b] + self.N[c]
        self.T.append((a, b, c) if fn @ want >= 0 else (a, c, b))

    def poly(self, pts, n, uvs):
        o = len(self.V)
        for p, uv in zip(pts, uvs): self.add_v(p, n, uv)
        for k in range(1, len(pts) - 1): self.tri(o, o + k, o + k + 1)

    def grid(self, P, N, UV):
        rows, cols = P.shape[:2]; o = len(self.V)
        for i in range(rows):
            for j in range(cols): self.add_v(P[i, j], N[i, j], UV[i, j])
        for i in range(rows - 1):
            for j in range(cols - 1):
                a, b, c, d = o + i * cols + j, o + i * cols + j + 1, o + (i + 1) * cols + j, o + (i + 1) * cols + j + 1
                self.tri(a, b, c); self.tri(b, d, c)

    # ---- primitives
    def box(self, mn, mx, sc=64.0, faces='xXyYzZ', tex_fit=None):
        """axis box; planar uv at sc units per texture repeat. tex_fit: dict face -> (u0,v0,u1,v1) fitted uv rect"""
        x0, y0, z0 = mn; x1, y1, z1 = mx
        F = {'x': ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0), (1, 2)),
             'X': ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), (1, 2)),
             'y': ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), (0, 2)),
             'Y': ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0), (0, 2)),
             'z': ([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], (0, 0, -1), (0, 1)),
             'Z': ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), (0, 1))}
        for k in faces:
            pts, n, (a, b) = F[k]
            if tex_fit and k in tex_fit:
                u0, v0, u1, v1 = tex_fit[k]
                uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)] if k not in 'zZ' else [(u0, v1), (u0, v0), (u1, v0), (u1, v1)]
                if k in 'zZ': uvs = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
            else:
                uvs = [(p[a] / sc, -p[b] / sc) for p in pts]
            self.poly(pts, n, uvs)

    def cyl(self, axis, c, r, a0, a1, nseg=16, caps=True, sc=64.0, cap_uv=None, r1=None):
        """cylinder (or cone frustum with r1) along axis 'x'/'y'/'z' from a0 to a1, centre c (the two other coords)"""
        r1 = r if r1 is None else r1
        def P(t, ang, rr):
            u, v = rr * math.cos(ang), rr * math.sin(ang)
            if axis == 'x': return (t, c[0] + u, c[1] + v)
            if axis == 'y': return (c[0] + u, t, c[1] + v)
            return (c[0] + u, c[1] + v, t)
        def Nn(ang, slope=0.0):
            u, v = math.cos(ang), math.sin(ang)
            if axis == 'x': return (slope, u, v)
            if axis == 'y': return (u, slope, v)
            return (u, v, slope)
        L = abs(a1 - a0); slope = (r - r1) / L if L > 1e-9 else 0
        Pp = np.zeros((2, nseg + 1, 3)); Nm = np.zeros_like(Pp); UV = np.zeros((2, nseg + 1, 2))
        for j in range(nseg + 1):
            ang = 2 * math.pi * j / nseg
            for i, (t, rr) in enumerate(((a0, r), (a1, r1))):
                Pp[i, j] = P(t, ang, rr); Nm[i, j] = Nn(ang, slope * (1 if a1 > a0 else -1)); UV[i, j] = (j / nseg * max(1, round(2 * math.pi * r / sc)), -t / sc)
        self.grid(Pp, Nm, UV)
        if caps:
            for t, rr, sg in ((a0, r, -1 if a1 > a0 else 1), (a1, r1, 1 if a1 > a0 else -1)):
                if rr < 0.5: continue
                pts = [P(t, 2 * math.pi * k / nseg, rr) for k in range(nseg)]
                n = (sg, 0, 0) if axis == 'x' else ((0, sg, 0) if axis == 'y' else (0, 0, sg))
                uvs = [(0.5 + 0.5 * math.cos(2 * math.pi * k / nseg), 0.5 - 0.5 * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)] \
                    if cap_uv else [(p[0] / sc, -p[2] / sc) for p in pts]
                self.poly(pts, n, uvs)

    def revolve(self, prof, cx=0.0, cy=0.0, nseg=24, sc=64.0, top_cap=False):
        prof = np.asarray(prof, float)
        tg = np.gradient(prof, axis=0); pn = np.stack([tg[:, 1], -tg[:, 0]], 1)
        pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
        angs = np.linspace(0, 2 * math.pi, nseg + 1)
        P = np.zeros((len(prof), nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), nseg + 1, 2))
        for j, a in enumerate(angs):
            c, s = math.cos(a), math.sin(a)
            P[:, j] = np.stack([cx + prof[:, 0] * c, cy + prof[:, 0] * s, prof[:, 1]], 1)
            N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
            UV[:, j, 0] = j / nseg * max(1, round(2 * math.pi * prof[:, 0].max() / sc)); UV[:, j, 1] = -prof[:, 1] / sc
        self.grid(P, N, UV)
        if top_cap and prof[-1, 0] > 0.5:
            r, z = prof[-1]
            pts = [(cx + r * math.cos(2 * math.pi * k / nseg), cy + r * math.sin(2 * math.pi * k / nseg), z) for k in range(nseg)]
            self.poly(pts, (0, 0, 1), [(p[0] / sc, -p[1] / sc) for p in pts])

    def hull(self, pts, sc=64.0):
        """convex hull of points, flat-shaded faces, planar uv along the dominant axis"""
        P = np.asarray(pts, float); h = ConvexHull(P)
        done = []
        for eq in h.equations:
            n = eq[:3]; d = -eq[3]
            if any(np.allclose(n, q, atol=1e-6) for q in done): continue
            done.append(n)
            on = P[np.abs(P @ n - d) < 1e-4]
            c = on.mean(0); ax = np.argmax(np.abs(n))
            e1 = np.array([1.0, 0, 0]) if ax != 0 else np.array([0, 1.0, 0])
            e1 = e1 - n * (e1 @ n); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
            ang = np.arctan2((on - c) @ e2, (on - c) @ e1); on = on[np.argsort(ang)]
            a, b = [i for i in range(3) if i != ax][:2]
            self.poly(list(on), n, [(p[a] / sc, -p[b] / sc) for p in on])

    def arc_slab(self, x0, x1, half_w, z_edge, z_top, thick=6.0, nseg=10, sc=64.0):
        """curved roof along x: circular arc across y (z_edge at |y| = half_w, z_top at y = 0), top + underside + ends"""
        R = (half_w ** 2 + (z_top - z_edge) ** 2) / (2 * (z_top - z_edge)); zc = z_top - R
        phi = math.asin(half_w / R)
        angs = np.linspace(-phi, phi, nseg + 1)
        for zz, sgn in ((0.0, 1), (-thick, -1)):
            P = np.zeros((2, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, nseg + 1, 2))
            for j, a in enumerate(angs):
                y, z = R * math.sin(a), zc + R * math.cos(a) + zz
                for i, x in enumerate((x0, x1)):
                    P[i, j] = (x, y, z); N[i, j] = (0, sgn * math.sin(a), sgn * math.cos(a)); UV[i, j] = (x / sc, y / sc)
            self.grid(P, N, UV)
        for x, sg in ((x0, -1), (x1, 1)):
            top = [(x, R * math.sin(a), zc + R * math.cos(a)) for a in angs]
            bot = [(x, p[1], p[2] - thick) for p in top]
            for k in range(nseg):
                q = [top[k], top[k + 1], bot[k + 1], bot[k]]
                self.poly(q, (sg, 0, 0), [(p[1] / sc, -p[2] / sc) for p in q])

    def take(self, other):
        o = len(self.V)
        self.V += other.V; self.N += other.N; self.ST += other.ST
        self.T += [(a + o, b + o, c + o) for (a, b, c) in other.T]

    def arrays(self):
        return (np.array(self.V, float).reshape(-1, 3), np.array(self.N, float).reshape(-1, 3),
                np.array(self.ST, float).reshape(-1, 2), np.array(self.T, np.int64).reshape(-1, 3))


class Model:
    """material -> Mesh"""
    def __init__(self): self.m = {}

    def __getitem__(self, k):
        if k not in self.m: self.m[k] = Mesh()
        return self.m[k]

    def surfaces(self):
        out = []
        for mat, mesh in self.m.items():
            V, N, ST, T = mesh.arrays()
            if len(T): out.append(dict(name=mat, shader=MD + '/' + mat, verts=V, normals=N, st=ST, tris=T))
        return out

    def save_md3(self, out, name):
        p = os.path.join(out, MD, name + '.md3'); os.makedirs(os.path.dirname(p), exist_ok=True)
        md3write.save(p, self.surfaces(), name)
        return MD + '/' + name + '.md3'


def xform(surf, ang_deg, off):
    """rotate a surface about z and translate"""
    a = math.radians(ang_deg); c, s = math.cos(a), math.sin(a)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return dict(surf, verts=surf['verts'] @ R.T + np.asarray(off), normals=surf['normals'] @ R.T)


# ------------------------------------------------------------------------------------------------ rolling stock
def wheel(M, x, z, r, y_in, y_out, mat='wheel', nseg=18):
    """wheel disc between |y| = y_in and y_out on both sides; spoked face texture on the outer cap"""
    for sg in (1, -1):
        a0, a1 = (sg * y_in, sg * y_out)
        M[mat].cyl('y', (x, z), r, a0, a1, nseg, caps=True, sc=32, cap_uv=True)
        M['loco_black'].cyl('y', (x, z), r * 0.28, sg * y_out, sg * (y_out + 3), 8, caps=True, sc=16)


def buffers(M, x, dirn):
    for y in (-38, 38):
        M['loco_black'].cyl('x', (y, 42), 6, x, x + dirn * 14, 8, caps=False, sc=16)
        M['metal'].cyl('x', (y, 42), 10, x + dirn * 14, x + dirn * 18, 12, caps=True, sc=16)


def loco():
    M = Model()
    blk, grn = M['loco_black'], M['loco_green']
    blk.box((-150, -40, 20), (196, 40, 44))                                  # frame
    blk.box((-150, -58, 52), (200, 58, 58))                                  # running board
    for x in (-100, -24, 52): wheel(M, x, 32, 32, 40, 48)
    wheel(M, 132, 18, 18, 36, 43, mat='wheel_small', nseg=14)
    for y in (-52, 52):
        blk.cyl('x', (y, 44), 16, 112, 170, 14, sc=32)                       # cylinders
        M['metal'].box((-100, y - 2 if y > 0 else y - 1, 29), (52, y + 1 if y > 0 else y + 2, 35))    # coupling rods
        M['metal'].box((52, y - 1.5, 38), (140, y + 1.5, 44))                # piston rod
    grn.cyl('x', (0, 100), 40, -40, 150, 24, caps=False, sc=64)               # boiler
    for x in (-28, 20, 70, 118):
        M['brass'].cyl('x', (0, 100), 41.5, x, x + 5, 24, caps=False, sc=16)  # bands
    blk.cyl('x', (0, 100), 43, 150, 200, 24, caps=False, sc=64)              # smokebox
    M['smokebox_door'].cyl('x', (0, 100), 43, 200, 201, 24, caps=True, sc=64, cap_uv=True)
    blk.box((150, -34, 58), (196, 34, 70))                                   # saddle
    blk.revolve([(12, 136), (12, 170), (15, 176), (17, 184), (17, 190)], 180, 0, 16, sc=32, top_cap=False)   # chimney
    blk.revolve([(13, 189), (8, 189.5), (0.01, 186)], 180, 0, 16, sc=32)    # chimney mouth (dark)
    M['brass'].revolve([(18, 134), (17, 150), (14, 158), (9, 164), (0.01, 167)], 60, 0, 18, sc=32)             # dome
    grn.revolve([(13, 136), (12, 146), (8, 152), (0.01, 154)], 112, 0, 14, sc=32)                             # sand dome
    M['brass'].revolve([(5, 136), (5, 152), (8, 156), (8, 160), (0.01, 161)], -20, 0, 10, sc=16)              # whistle
    # cab: lined side panels (fitted texture), front/back faces plain, curved roof
    M['cab_side'].box((-152, -54, 58), (-38, 54, 170), faces='yY', tex_fit={'y': (0, 0, 1, 1), 'Y': (0, 0, 1, 1)})
    grn.box((-152, -54, 58), (-38, 54, 170), faces='xX')
    M['loco_black'].arc_slab(-160, -30, 62, 166, 180, 5, 12, sc=64)
    M['cab_dark'].box((-150, -52, 59), (-40, 52, 60), faces='Z')            # cab floor seen through windows
    grn.box((-60, -40, 58), (-38, 40, 120))                                  # firebox in front of the cab
    # buffer beams, buffers, cowcatcher, headlamp
    M['loco_red'].box((196, -58, 26), (208, 58, 56)); M['loco_red'].box((-164, -58, 26), (-152, 58, 56))
    buffers(M, 208, 1); buffers(M, -164, -1)
    blk.hull([(208, -50, 26), (208, 50, 26), (208, -50, 8), (208, 50, 8), (236, -26, 4), (236, 26, 4), (230, -26, 12), (230, 26, 12)], sc=32)
    blk.box((196, -9, 146), (206, 9, 162))
    M['headlamp'].poly([(206.3, -7, 148), (206.3, 7, 148), (206.3, 7, 160), (206.3, -7, 160)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return M


def tender():
    M = Model()
    blk = M['loco_black']
    blk.box((-100, -40, 20), (100, 40, 44))
    M['tender_side'].box((-104, -54, 48), (104, 54, 138), faces='yY', tex_fit={'y': (0, 0, 1, 1), 'Y': (0, 0, 1, 1)})
    M['loco_green'].box((-104, -54, 48), (104, 54, 138), faces='xXz')
    M['loco_black'].box((-108, -56, 136), (108, 56, 140), faces='xXyYz')      # top rim
    coal = M['coal']
    coal.box((-100, -52, 136), (60, 52, 141), faces='Z')
    rr = np.random.default_rng(4)
    for k in range(6):
        cx, cy = -80 + 26 * k, rr.uniform(-18, 18)
        pts = [(cx + rr.uniform(-22, 22), cy + rr.uniform(-26, 26), 141) for _ in range(6)] + [(cx + rr.uniform(-8, 8), cy + rr.uniform(-8, 8), 141 + rr.uniform(10, 18))]
        coal.hull(pts, sc=32)
    M['loco_green'].box((60, -52, 136), (100, 52, 150))                       # water tank top at the rear
    M['brass'].cyl('z', (82, 0), 10, 150, 156, 12, sc=16)                     # filler cap
    for x in (-64, 0, 64): wheel(M, x, 22, 22, 38, 46, mat='wheel_small', nseg=14)
    M['loco_red'].box((104, -58, 26), (112, 58, 52)); M['loco_red'].box((-112, -58, 26), (-104, 58, 52))
    buffers(M, 112, 1); buffers(M, -112, -1)
    return M


def carriage():
    M = Model()
    blk = M['loco_black']
    blk.box((-152, -44, 26), (152, 44, 44))
    M['carriage_side'].box((-156, -54, 44), (156, 54, 160), faces='yY', tex_fit={'y': (0, 0, 1, 1), 'Y': (0, 0, 1, 1)})
    M['carriage_end'].box((-156, -54, 44), (156, 54, 160), faces='xX', tex_fit={'x': (0, 0, 1, 1), 'X': (0, 0, 1, 1)})
    M['carriage_side'].box((-156, -54, 44), (156, 54, 160), faces='z', tex_fit={'z': (0, 0.9, 0.05, 1)})
    M['carriage_roof'].arc_slab(-164, 164, 60, 158, 172, 4, 12, sc=64)
    M['clerestory'].box((-128, -22, 166), (128, 22, 184), faces='yY', tex_fit={'y': (0, 0, 1, 1), 'Y': (0, 0, 1, 1)})
    M['carriage_roof'].box((-128, -22, 166), (128, 22, 184), faces='xX')
    M['carriage_roof'].box((-134, -26, 184), (134, 26, 188))
    for bx in (-100, 100):
        blk.box((bx - 34, -40, 14), (bx + 34, 40, 30))
        for x in (bx - 22, bx + 22): wheel(M, x, 16, 16, 36, 43, mat='wheel_small', nseg=12)
    M['loco_red'].box((156, -50, 28), (164, 50, 50)); M['loco_red'].box((-164, -50, 28), (-156, 50, 50))
    buffers(M, 164, 1); buffers(M, -164, -1)
    return M


# ------------------------------------------------------------------------------------------------ track
def track_arc(deg=45.0, R=TRACK_R, tie_step=38.0):
    """arc of the circle, local origin on the circle at mid-arc: points (r cos p - R, r sin p)"""
    M = Model()
    half = math.radians(deg / 2)
    ntie = int(round(R * 2 * half / tie_step))
    for k in range(ntie):
        p = -half + (k + 0.5) * 2 * half / ntie
        c, s = math.cos(p), math.sin(p)
        t = np.array([-s, c])                                  # tangent
        def W(r, w, z): return (r * c - R + t[0] * w, r * s + t[1] * w, z)
        pts = [W(r, w, z) for r in (R - 48, R + 48) for w in (-7, 7) for z in (0, 6)]
        M['tie'].hull(pts, sc=32)
    nseg = max(8, int(deg / 1.5))
    for rr in (R - GAUGE / 2, R + GAUGE / 2):
        for (r0, r1, z0, z1, mat) in ((rr - 4, rr + 4, 6, 8, 'rail'), (rr - 1.5, rr + 1.5, 8, 13, 'rail'), (rr - 3, rr + 3, 13, 16, 'rail_top')):
            angs = np.linspace(-half, half, nseg + 1)
            ring = lambda r, z: np.array([(r * math.cos(a) - R, r * math.sin(a), z) for a in angs])
            Ptop = np.stack([ring(r0, z1), ring(r1, z1)]); Nt = np.zeros_like(Ptop); Nt[..., 2] = 1
            UVt = np.zeros(Ptop.shape[:2] + (2,)); UVt[..., 0] = np.linspace(0, R * 2 * half / 32, nseg + 1)[None]; UVt[1, :, 1] = 0.2
            M[mat].grid(Ptop, Nt, UVt)
            for r, sg in ((r0, -1), (r1, 1)):
                P = np.stack([ring(r, z0), ring(r, z1)])
                N = np.zeros_like(P); N[..., 0] = sg * np.cos(angs)[None]; N[..., 1] = sg * np.sin(angs)[None]
                UV = np.zeros(P.shape[:2] + (2,)); UV[..., 0] = np.linspace(0, R * 2 * half / 32, nseg + 1)[None]; UV[1, :, 1] = 0.3
                M[mat].grid(P, N, UV)
    return M


def track_straight(L=512.0, tie_step=38.0):
    M = Model()
    n = int(round(L / tie_step))
    for k in range(n):
        x = -L / 2 + (k + 0.5) * L / n
        M['tie'].box((x - 7, -48, 0), (x + 7, 48, 6), sc=32)
    for y in (-GAUGE / 2, GAUGE / 2):
        M['rail'].box((-L / 2, y - 4, 6), (L / 2, y + 4, 8), sc=32, faces='yYZ')
        M['rail'].box((-L / 2, y - 1.5, 8), (L / 2, y + 1.5, 13), sc=32, faces='yY')
        M['rail_top'].box((-L / 2, y - 3, 13), (L / 2, y + 3, 16), sc=32, faces='yYZ')
    return M


# ------------------------------------------------------------------------------------------------ scenery
def pine(seed=0):
    M = Model()
    rr = np.random.default_rng(seed)
    M['bark'].cyl('z', (0, 0), 9, 0, 70, 10, caps=False, sc=32, r1=7)
    tiers = [(30, 78, 120), (80, 64, 110), (130, 50, 96), (176, 34, 80)]
    for (z0, r0, h) in tiers:
        n = 14
        prof_out = []
        for k in range(n):
            a = 2 * math.pi * k / n
            r = r0 * (1.0 if k % 2 == 0 else 0.78) * rr.uniform(0.92, 1.05)
            prof_out.append((r * math.cos(a), r * math.sin(a), z0 + (0 if k % 2 == 0 else 8)))
        top = (rr.uniform(-3, 3), rr.uniform(-3, 3), z0 + h)
        needles = M['needles']
        for k in range(n):
            p, q = prof_out[k], prof_out[(k + 1) % n]
            n_ = np.cross(np.subtract(q, p), np.subtract(top, p)); n_ = -n_ if n_[2] < 0 else n_
            needles.poly([p, q, top], n_, [(k / n * 3, 1), ((k + 1) / n * 3, 1), ((k + 0.5) / n * 3, 0)])
        needles.poly(prof_out[::-1], (0, 0, -1), [(p[0] / 64, p[1] / 64) for p in prof_out[::-1]])
    return M


def portal():
    """tunnel portal facade; local x = outward (0 at the cut face), y across the track, z from the table top"""
    M = Model()
    st = M['portal_stone']
    W, T, H = 124.0, 28.0, 304.0          # half width, thickness, height of the facade
    hw, zb, zs = 72.0, 8.0, 168.0         # opening half width, bottom, springline
    n = 14
    arch = [(-hw, zb), (-hw, zs)] + [(-hw * math.cos(math.pi * k / n), zs + hw * math.sin(math.pi * k / n)) for k in range(1, n)] + [(hw, zs), (hw, zb)]
    # outer boundary points paired with the arch points (same count): along left side, top, right side
    m = len(arch)
    outer = []
    for k, (y, z) in enumerate(arch):
        t = k / (m - 1)
        if t < 0.25: outer.append((-W, zb + (H - zb) * t / 0.25 if False else zb + (H - zb) * (t / 0.25) * 0.999))
        elif t < 0.75: outer.append((-W + 2 * W * (t - 0.25) / 0.5, H))
        else: outer.append((W, H - (H - zb) * (t - 0.75) / 0.25))
    outer[0] = (-W, zb); outer[-1] = (W, zb)
    for k in range(m - 1):
        a, b, c, d = arch[k], arch[k + 1], outer[k + 1], outer[k]
        q = [(T, a[0], a[1]), (T, b[0], b[1]), (T, c[0], c[1]), (T, d[0], d[1])]
        st.poly(q, (1, 0, 0), [(p[1] / 96, -p[2] / 96) for p in q])
    st.poly([(T, -W, 0), (T, W, 0), (T, W, zb), (T, -W, zb)], (1, 0, 0), [(0, 0), (1, 0), (1, 0.05), (0, 0.05)]) if False else None
    for k in range(m - 1):                                    # reveal (intrados)
        a, b = arch[k], arch[k + 1]
        nrm = (0, -(b[1] - a[1]), (b[0] - a[0]))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if nrm[1] * (0 - mid[0]) + nrm[2] * (zs - mid[1]) < 0: nrm = (0, -nrm[1], -nrm[2])
        q = [(0, a[0], a[1]), (T, a[0], a[1]), (T, b[0], b[1]), (0, b[0], b[1])]
        M['portal_dark'].poly(q, nrm, [(0, k / 4), (0.3, k / 4), (0.3, (k + 1) / 4), (0, (k + 1) / 4)])
    st.box((0, -W, 0), (T, W, H), faces='yYZ', sc=96)
    # pilasters, cornice, parapet, keystone, plaque
    for sg in (-1, 1):
        y0, y1 = sorted((sg * (W - 18), sg * (W + 2)))
        st.box((T, y0, 0), (T + 12, y1, H - 8), faces='XyYZ', sc=64)
    M['portal_trim'].box((0, -W - 8, H - 16), (T + 18, W + 8, H), faces='XyYzZ', sc=64)
    M['portal_trim'].box((0, -W - 4, H), (T + 6, W + 4, H + 16), faces='XyYZ', sc=64)
    M['portal_trim'].hull([(T, -14, zs + hw - 6), (T, 14, zs + hw - 6), (T, -18, zs + hw + 30), (T, 18, zs + hw + 30),
                           (T + 8, -12, zs + hw - 4), (T + 8, 12, zs + hw - 4), (T + 8, -16, zs + hw + 28), (T + 8, 16, zs + hw + 28)], sc=32)
    M['portal_plaque'].poly([(T + 0.5, -40, H - 56), (T + 0.5, 40, H - 56), (T + 0.5, 40, H - 26), (T + 0.5, -40, H - 26)], (1, 0, 0),
                            [(0, 1), (1, 1), (1, 0), (0, 0)])
    return M


def water_tower():
    M = Model()
    wood, iron = M['tank_wood'], M['iron']
    for (x, y) in ((-50, -50), (50, -50), (-50, 50), (50, 50)):
        iron.box((x - 6, y - 6, 0), (x + 6, y + 6, 200), sc=32)
    for z in (70, 140):
        iron.box((-56, -48, z), (56, -44, z + 6), sc=32); iron.box((-56, 44, z), (56, 48, z + 6), sc=32)
        iron.box((-48, -56, z), (-44, 56, z + 6), sc=32); iron.box((44, -56, z), (48, 56, z + 6), sc=32)
    iron.box((-74, -74, 200), (74, 74, 208), sc=64)
    wood.cyl('z', (0, 0), 70, 208, 312, 24, caps=False, sc=48)
    for z in (224, 262, 300): iron.cyl('z', (0, 0), 71.5, z, z + 4, 24, caps=False, sc=16)
    M['tank_roof'].revolve([(76, 310), (60, 322), (8, 350), (0.01, 352)], 0, 0, 24, sc=48)
    M['tank_roof'].revolve([(76, 310), (70, 311)], 0, 0, 24, sc=48)
    iron.cyl('x', (0, 240), 7, 70, 120, 10, caps=True, sc=16)                 # spout
    iron.hull([(116, -6, 240), (116, 6, 240), (124, -6, 232), (124, 6, 232), (160, -5, 196), (160, 5, 196), (152, -5, 190), (152, 5, 190)], sc=16)
    return M


def signal():
    M = Model()
    post = M['signal_post']
    post.box((-10, -10, 0), (10, 10, 12), sc=32)
    post.cyl('z', (0, 0), 4, 12, 230, 8, caps=True, sc=32)
    M['iron'].box((-3, 6, 12), (-1, 8, 200), sc=32); M['iron'].box((5, 6, 12), (7, 8, 200), sc=32)
    for z in range(30, 200, 24): M['iron'].box((-3, 6, z), (7, 8, z + 2), sc=32)
    M['signal_arm'].box((-2, -60, 196), (2, 2, 208), faces='xXyYzZ', tex_fit={'x': (0, 0, 1, 1), 'X': (0, 0, 1, 1)})
    M['iron'].box((-6, -6, 192), (6, 6, 210), sc=32)
    M['loco_black'].box((-8, 4, 176), (8, 18, 192), sc=32)
    M['signal_lamp'].poly([(8.3, 7, 180), (8.3, 15, 180), (8.3, 15, 188), (8.3, 7, 188)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    M['iron'].revolve([(5, 230), (5, 234), (0.01, 238)], 0, 0, 8, sc=16)
    return M


def clock_tower(hour=10.0, minute=8.0):
    """town hall clock tower (stands on the roof): stone shaft with corner pilasters, cornices, a clock stage with four
    brass-bezelled faces and modelled hands, slate pyramid roof, brass finial. Footprint +-60, top z 362."""
    M = Model()
    st, tr = M['tower_stone'], M['tower_trim']
    tr.box((-60, -60, 0), (60, 60, 16), faces='xXyYZ', sc=64)
    st.box((-50, -50, 16), (50, 50, 150), faces='xXyY', sc=96)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = sorted((sx * 42, sx * 56)); y0, y1 = sorted((sy * 42, sy * 56))
            tr.box((x0, y0, 16), (x1, y1, 150), faces='xXyY', sc=64)
    tr.box((-60, -60, 150), (60, 60, 164), faces='xXyYzZ', sc=64)
    st.box((-48, -48, 164), (48, 48, 252), faces='xXyY', sc=96)
    tr.box((-58, -58, 252), (58, 58, 264), faces='xXyYzZ', sc=64)
    M['tower_roof'].hull([(-58, -58, 264), (58, -58, 264), (58, 58, 264), (-58, 58, 264), (0, 0, 334)], sc=64)
    M['brass'].cyl('z', (0, 0), 3, 330, 352, 8, caps=False, sc=16)
    M['brass'].revolve([(0.01, 350), (6, 354), (6, 358), (0.01, 362)], 0, 0, 10, sc=16)
    # four clock faces at z 208 (centre), facing +-x and +-y
    zc = 208.0
    for k in range(4):
        a = math.radians(90 * k); n = np.array([math.cos(a), math.sin(a), 0.0]); u = np.array([-math.sin(a), math.cos(a), 0.0])
        def P(d, uu, zz): return tuple(n * d + u * uu + np.array([0, 0, zz]))
        def disc(mesh, r, d, nseg=24, uvfit=True):
            pts = [P(d, r * math.cos(2 * math.pi * j / nseg), zc + r * math.sin(2 * math.pi * j / nseg)) for j in range(nseg)]
            uvs = [(0.5 + 0.5 * math.cos(2 * math.pi * j / nseg), 0.5 - 0.5 * math.sin(2 * math.pi * j / nseg)) for j in range(nseg)]
            mesh.poly(pts, n, uvs if uvfit else [(p[0] / 32, p[2] / 32) for p in pts])
            # rim (side band) so the disc has thickness
            for j in range(nseg):
                c0 = 2 * math.pi * j / nseg; c1 = 2 * math.pi * (j + 1) / nseg
                q = [P(48, r * math.cos(c0), zc + r * math.sin(c0)), P(d, r * math.cos(c0), zc + r * math.sin(c0)),
                     P(d, r * math.cos(c1), zc + r * math.sin(c1)), P(48, r * math.cos(c1), zc + r * math.sin(c1))]
                cm = (c0 + c1) / 2
                mesh.poly(q, tuple(u * math.cos(cm) + np.array([0, 0, math.sin(cm)])), [(j / nseg, 0), (j / nseg, 0.1), ((j + 1) / nseg, 0.1), ((j + 1) / nseg, 0)])
        disc(M['brass'], 42, 52, uvfit=False)
        disc(M['clock_face'], 37, 53.5)
        for (ang_h, L, w) in ((90 - 30 * (hour + minute / 60), 20, 3.0), (90 - 6 * minute, 31, 2.0)):
            t = math.radians(ang_h); dirv = (math.cos(t), math.sin(t)); pv = (-math.sin(t), math.cos(t))
            q = [(-4 * dirv[0] - w * pv[0], -4 * dirv[1] - w * pv[1]), (L * dirv[0] - w * 0.4 * pv[0], L * dirv[1] - w * 0.4 * pv[1]),
                 (L * dirv[0] + w * 0.4 * pv[0], L * dirv[1] + w * 0.4 * pv[1]), (-4 * dirv[0] + w * pv[0], -4 * dirv[1] + w * pv[1])]
            for dd, nn in ((55.5, n), (54.0, -n)):
                M['loco_black'].poly([P(dd, uu, zc + vv) for (uu, vv) in q], tuple(nn), [(0, 0), (1, 0), (1, 1), (0, 1)])
            for j in range(4):
                (u0, v0), (u1, v1) = q[j], q[(j + 1) % 4]
                M['loco_black'].poly([P(54.0, u0, zc + v0), P(55.5, u0, zc + v0), P(55.5, u1, zc + v1), P(54.0, u1, zc + v1)],
                                     tuple(u * (v1 - v0) - np.array([0, 0, u1 - u0])), [(0, 0), (1, 0), (1, 1), (0, 1)])
        hub = [P(56.5, 3 * math.cos(2 * math.pi * j / 8), zc + 3 * math.sin(2 * math.pi * j / 8)) for j in range(8)]
        M['brass'].poly(hub, tuple(n), [(0.5, 0.5)] * 8)
        # arched louvre panel under the clock
        M['tower_dark'].poly([P(50.5, -16, 40), P(50.5, 16, 40), P(50.5, 16, 120), P(50.5, -16, 120)], tuple(n), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return M


def clock_face_tex(n=256):
    im = Image.new('RGB', (n, n), (40, 34, 30)); d = ImageDraw.Draw(im)
    c = n / 2
    d.ellipse((2, 2, n - 2, n - 2), fill=(248, 240, 214))
    d.ellipse((10, 10, n - 10, n - 10), outline=(60, 50, 40), width=3)
    nums = ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI']
    f = font(20, FONTS)
    for k in range(60):
        a = 2 * math.pi * k / 60 - math.pi / 2
        r0 = 112 if k % 5 else 104
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + 118 * math.cos(a), c + 118 * math.sin(a))], fill=(40, 34, 30), width=4 if k % 5 == 0 else 2)
    for k, t in enumerate(nums):
        a = 2 * math.pi * k / 12 - math.pi / 2
        d.text((c + 84 * math.cos(a), c + 84 * math.sin(a)), t, font=f, fill=(30, 26, 22), anchor='mm')
    d.text((c, c + 40), 'PAD & SONS', font=font(12, FONTS), fill=(120, 90, 50), anchor='mm')
    return im


# ------------------------------------------------------------------------------------------------ train loop (IQM)
def train_cars():
    return [('loco', loco()), ('tender', tender()), ('carriage', carriage()), ('carriage', carriage()), ('carriage', carriage())]


def train_layout(front_deg, R=TRACK_R, gap=10.0):
    """(name, centre angle deg, local x centre) for each car, travelling counter-clockwise, front of the loco at front_deg"""
    out = []; s = 0.0
    for name, _ in train_cars():
        x0, x1, _top = STOCK[name]
        L = x1 - x0
        mid_s = s + L / 2
        ang = front_deg - math.degrees(mid_s / R)
        out.append((name, ang, (x0 + x1) / 2, L))
        s += L + gap
    return out


def train_loop(out, front_deg, rail_dz, R=TRACK_R):
    """one IQM holding the whole train on the circle (origin = circle centre, z = rail_dz below the entity origin)"""
    meshes = {}
    for (name, ang, xc, L), (_, M) in zip(train_layout(front_deg, R), train_cars()):
        th = math.radians(ang)
        pos = (R * math.cos(th), R * math.sin(th), rail_dz)
        for s in M.surfaces():
            s2 = xform(dict(s, verts=s['verts'] - np.array([xc, 0, 0])), ang + 90, pos)   # local +x -> CCW tangent
            meshes.setdefault(s2['shader'], []).append(s2)
    iq = []
    for mat, lst in meshes.items():
        cur, nv = [], 0
        def flush():
            if not cur: return
            V = np.concatenate([c['verts'] for c in cur]); N = np.concatenate([c['normals'] for c in cur])
            ST = np.concatenate([c['st'] for c in cur]); T = []; o = 0
            for c in cur: T.append(c['tris'] + o); o += len(c['verts'])
            iq.append(dict(name=mat.split('/')[-1], material=mat, verts=V, normals=N, st=ST, tris=np.concatenate(T)))
        for s in lst:
            if len(s['verts']) > 990:            # split big surfaces by triangles
                T = s['tris']; step = 300
                for k in range(0, len(T), step):
                    sub = T[k:k + step]; idx = np.unique(sub); remap = {v: i for i, v in enumerate(idx)}
                    piece = dict(s, verts=s['verts'][idx], normals=s['normals'][idx], st=s['st'][idx],
                                 tris=np.vectorize(remap.get)(sub))
                    if nv + len(piece['verts']) >= 990: flush(); cur.clear(); nv = 0
                    cur.append(piece); nv += len(piece['verts'])
                continue
            if nv + len(s['verts']) >= 990: flush(); cur.clear(); nv = 0
            cur.append(s); nv += len(s['verts'])
        flush()
    p = os.path.join(out, MD, 'train_loop.iqm'); os.makedirs(os.path.dirname(p), exist_ok=True)
    iqmtool.save(p, iq)
    return MD + '/train_loop.iqm'


# ------------------------------------------------------------------------------------------------ textures
def font(sz, f=None): return ImageFont.truetype(f or FONTB, int(sz))


def noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im, np.float32); return (a - a.mean()) / (a.std() + 1e-6)


def paint(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + np.array(col, np.float32) + noise(n, 1.2, seed, m)[..., None] * grain + noise(n, 10, seed + 1, m)[..., None] * grain


def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def lined_panel(w, h, base, line=(230, 190, 60), text=None, windows=(), seed=0):
    im = img(paint(w, base, 3, seed, h)); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w - 11, h - 11), outline=line, width=4)
    for (x0, y0, x1, y1) in windows:
        d.rounded_rectangle((x0, y0, x1, y1), radius=10, fill=(26, 28, 32), outline=(20, 20, 20), width=3)
    if text:
        d.text((w / 2, h * 0.72), text, font=font(h * 0.14), fill=line, anchor='mm', stroke_width=2, stroke_fill=(30, 20, 10))
    return im


def wheel_tex(n=128, rim=(30, 30, 32), spoke=(190, 40, 34)):
    im = Image.new('RGB', (n, n), rim); d = ImageDraw.Draw(im)
    c = n / 2
    d.ellipse((6, 6, n - 6, n - 6), fill=(18, 18, 20))
    d.ellipse((14, 14, n - 14, n - 14), fill=spoke)
    d.ellipse((24, 24, n - 24, n - 24), fill=(20, 18, 18))
    for k in range(12):
        a = 2 * math.pi * k / 12
        d.line([(c, c), (c + 42 * math.cos(a), c + 42 * math.sin(a))], fill=spoke, width=6)
    d.ellipse((c - 14, c - 14, c + 14, c + 14), fill=spoke)
    d.ellipse((c - 26, c + 8, c - 10, c + 24), fill=spoke)             # crank boss
    return im


def smokebox_door(n=128):
    im = Image.new('RGB', (n, n), (22, 22, 24)); d = ImageDraw.Draw(im)
    d.ellipse((8, 8, n - 8, n - 8), fill=(30, 30, 33), outline=(60, 60, 64), width=3)
    d.rectangle((n / 2 - 22, n * 0.66, n / 2 + 22, n * 0.78), fill=(200, 160, 50))
    d.text((n / 2, n * 0.72), '1927', font=font(11), fill=(20, 20, 20), anchor='mm')
    for y in (n * 0.36, n * 0.56): d.rectangle((14, y - 3, n / 2, y + 3), fill=(80, 80, 86))
    d.ellipse((n / 2 - 6, n / 2 - 6, n / 2 + 6, n / 2 + 6), fill=(190, 190, 196))
    return im


def carriage_side(w=512, h=192, glow=False):
    """maroon lower / cream upper panels with eight windows; glow=True gives only the lit windows (additive mask)"""
    if glow: im = Image.new('RGB', (w, h), (0, 0, 0))
    else:
        im = img(paint(w, (120, 30, 34), 3, 51, h)); dd = ImageDraw.Draw(im)
        dd.rectangle((0, 0, w, h * 0.55), fill=(226, 208, 168))
        dd.rectangle((0, h * 0.53, w, h * 0.57), fill=(200, 160, 60))
    d = ImageDraw.Draw(im)
    for k in range(8):
        x0 = 22 + k * (w - 44) / 8
        box = (x0 + 6, h * 0.12, x0 + (w - 44) / 8 - 6, h * 0.48)
        if glow: d.rounded_rectangle(box, radius=8, fill=(255, 196, 100))
        else: d.rounded_rectangle(box, radius=8, fill=(255, 210, 130), outline=(90, 24, 26), width=4)
    if not glow:
        d.text((w / 2, h * 0.77), 'PAD  MOUNTAIN  RAILWAY', font=font(h * 0.11, FONTS), fill=(220, 180, 70), anchor='mm')
        for x in (6, w - 14):
            d.rectangle((x, h * 0.1, x + 8, h * 0.95), fill=(90, 24, 26))
    return im


def make_textures(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    def S(name, im): (im if isinstance(im, Image.Image) else img(im)).convert('RGB').save(os.path.join(d, name + '.jpg'), quality=90)
    S('loco_green', paint(64, (30, 92, 54), 3, 1))
    S('loco_black', paint(64, (24, 24, 27), 2, 2))
    S('loco_red', paint(64, (170, 34, 30), 3, 3))
    S('brass', paint(64, (196, 156, 66), 6, 4))
    S('metal', paint(64, (150, 152, 160), 6, 5))
    S('cab_dark', paint(64, (40, 32, 26), 3, 6))
    S('coal', paint(128, (22, 22, 24), 10, 7) + noise(128, 0.6, 8)[..., None] * 18)
    S('wheel', wheel_tex()); S('wheel_small', wheel_tex(spoke=(170, 36, 32)))
    S('smokebox_door', smokebox_door())
    S('headlamp', paint(32, (255, 236, 170), 2, 9))
    S('cab_side', lined_panel(256, 256, (30, 92, 54), windows=[(40, 30, 216, 120)], text='PAD 1', seed=10))
    S('tender_side', lined_panel(512, 256, (30, 92, 54), text='PAD  RAILWAYS', seed=11))
    S('carriage_side', carriage_side()); S('carriage_glow', carriage_side(glow=True))
    end = img(paint(128, (120, 30, 34), 3, 12)); ImageDraw.Draw(end).rounded_rectangle((40, 20, 88, 128), radius=6, fill=(90, 24, 26), outline=(200, 160, 60), width=3)
    S('carriage_end', end)
    S('carriage_roof', paint(64, (110, 110, 116), 3, 13))
    cl = img(paint(256, (226, 208, 168), 3, 14, 32)); dc = ImageDraw.Draw(cl)
    for k in range(10): dc.rectangle((8 + k * 25, 8, 26 + k * 25, 24), fill=(255, 210, 130))
    S('clerestory', cl)
    S('tie', paint(64, (92, 66, 44), 6, 15) + noise(64, 0.5, 16)[..., None] * 8)
    S('rail', paint(64, (92, 70, 58), 5, 17))
    S('rail_top', paint(64, (190, 192, 198), 5, 18))
    S('bark', paint(64, (96, 64, 40), 8, 19) * (0.85 + 0.15 * np.sin(np.arange(64) / 2.0))[None, :, None])
    nd = paint(128, (34, 92, 46), 10, 20) + noise(128, 0.6, 21)[..., None] * 14
    S('needles', nd)
    st = img(paint(256, (150, 140, 124), 6, 22)); ds = ImageDraw.Draw(st)
    for row in range(6):
        y = row * 42.7; off = 0 if row % 2 == 0 else 32
        ds.line([(0, y), (256, y)], fill=(90, 84, 74), width=3)
        for x in range(-64 + off, 256, 64): ds.line([(x, y), (x, y + 42)], fill=(90, 84, 74), width=3)
    S('portal_stone', st)
    S('portal_trim', paint(64, (176, 166, 148), 5, 23))
    S('portal_dark', paint(64, (40, 36, 32), 4, 24))
    pl = Image.new('RGB', (256, 96), (60, 54, 46)); dp = ImageDraw.Draw(pl)
    dp.rectangle((4, 4, 251, 91), outline=(200, 170, 90), width=4); dp.text((128, 48), 'PAD TUNNEL 1927', font=font(26, FONTS), fill=(220, 190, 110), anchor='mm')
    S('portal_plaque', pl)
    tw = paint(128, (120, 84, 52), 6, 25); tw[:, ::16] *= 0.6
    S('tank_wood', tw)
    S('tank_roof', paint(64, (70, 74, 80), 4, 26))
    S('iron', paint(64, (46, 46, 50), 3, 27))
    S('signal_post', paint(64, (230, 230, 226), 3, 28))
    arm = Image.new('RGB', (128, 32), (200, 30, 30)); ImageDraw.Draw(arm).rectangle((92, 6, 104, 26), fill=(240, 240, 240)); S('signal_arm', arm)
    S('signal_lamp', paint(32, (255, 70, 50), 2, 29))
    S('clock_face', clock_face_tex())
    ts = img(paint(256, (196, 180, 150), 6, 30)); dt = ImageDraw.Draw(ts)
    for row in range(8):
        y = row * 32; off = 0 if row % 2 == 0 else 24
        dt.line([(0, y), (256, y)], fill=(140, 126, 104), width=2)
        for x in range(-48 + off, 256, 48): dt.line([(x, y), (x, y + 32)], fill=(140, 126, 104), width=2)
    S('tower_stone', ts)
    S('tower_trim', paint(64, (224, 214, 192), 4, 31))
    rf = paint(128, (60, 66, 78), 4, 32); rf[::16] *= 0.7
    S('tower_roof', rf)
    S('tower_dark', paint(32, (36, 30, 26), 3, 33))


def shaders():
    S = '// ---- railway models (rail_models.py)\n'
    lit = ['loco_green', 'loco_black', 'loco_red', 'cab_dark', 'coal', 'wheel', 'wheel_small', 'smokebox_door', 'cab_side', 'tender_side',
           'carriage_end', 'carriage_roof', 'tie', 'rail', 'bark', 'needles', 'portal_stone', 'portal_trim', 'portal_dark', 'portal_plaque',
           'tank_wood', 'tank_roof', 'iron', 'signal_post', 'signal_arm', 'tower_stone', 'tower_trim', 'tower_roof', 'tower_dark']
    for nme in lit:
        S += f'{MD}/{nme}\n{{\n\tqer_editorimage {MD}/{nme}.jpg\n\t{{\n\t\tmap {MD}/{nme}.jpg\n\t\trgbGen vertex\n\t}}\n}}\n\n'
    for nme, k in (('brass', 0.35), ('metal', 0.3), ('rail_top', 0.4)):
        S += (f'{MD}/{nme}\n{{\n\tqer_editorimage {MD}/{nme}.jpg\n\t{{\n\t\tmap {MD}/{nme}.jpg\n\t\trgbGen vertex\n\t}}\n'
              f'\t{{\n\t\tmap {MD}/{nme}.jpg\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {k} {k} {k} )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    for nme in ('headlamp', 'signal_lamp', 'clock_face'):
        S += f'{MD}/{nme}\n{{\n\tqer_editorimage {MD}/{nme}.jpg\n\tsurfaceparm nolightmap\n\t{{\n\t\tmap {MD}/{nme}.jpg\n\t\trgbGen identity\n\t}}\n}}\n\n'
    S += f'''{MD}/carriage_side
{{
	qer_editorimage {MD}/carriage_side.jpg
	{{
		map {MD}/carriage_side.jpg
		rgbGen vertex
	}}
	{{
		map {MD}/carriage_glow.jpg
		blendFunc GL_ONE GL_ONE
		rgbGen identity
	}}
}}

{MD}/clerestory
{{
	qer_editorimage {MD}/clerestory.jpg
	{{
		map {MD}/clerestory.jpg
		rgbGen identity
	}}
}}

'''
    return S


def make(out):
    make_textures(out)
    for name, fn in (('loco', loco), ('tender', tender), ('carriage', carriage), ('track_arc', track_arc), ('track_straight', track_straight),
                     ('portal', portal), ('water_tower', water_tower), ('signal', signal), ('clock_tower', clock_tower)):
        fn().save_md3(out, name)
    for k in range(3): pine(seed=k).save_md3(out, 'pine%d' % (k + 1))
    return shaders()


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    make(o)
    print(train_loop(o, 30.0, -292.0))
