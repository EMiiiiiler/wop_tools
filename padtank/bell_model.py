"""The diving bell of wop_padtank as an MD3 (misc_model, lightmapped with spawnflags 4).

Riveted brass body with a flared foot, a mid band and a crown band, eight ribs, eight raised portholes with glass,
two framed hatchways (west / south, matching the collision brushes in build_padtank.diving_bell()), a smooth
interior, and a low walkable riveted dome with a hatch wheel. Collision stays brushes (common/weapclip, invisible): the
16-gon walls and roof the map already had, so routes and bot paths are unchanged.

    make(out) -> writes models/padtank/diving_bell.md3 + its textures, returns the shader text

Model origin = bell centre on the gravel. Door openings: 168.75..191.25 and 258.75..281.25 deg, z 0..128.
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import md3write

MD = 'models/padtank'
R_OUT, R_IN, H, DECK = 236.0, 206.0, 256.0, 288.0
DOME_TOP = 316.0
DOORS = [(168.75, 191.25), (258.75, 281.25)]
DOOR_TOP = 128.0
PORTHOLES = [22.5 + 45 * k for k in range(8)]
RIBS = [0, 45, 90, 135, 225, 315]
NSEG = 128                       # segments per full turn


# ------------------------------------------------------------------------------------------------ mesh helpers
class Mesh:
    def __init__(self):
        self.V, self.N, self.ST, self.T = [], [], [], []

    def quad_grid(self, P, N, UV, want=None):
        """P/N/UV: (rows, cols, k) grids; triangles between neighbours, oriented so the Quake front side faces N"""
        rows, cols = P.shape[:2]
        o = len(self.V)
        self.V += list(P.reshape(-1, 3)); self.N += list(N.reshape(-1, 3)); self.ST += list(UV.reshape(-1, 2))
        for i in range(rows - 1):
            for j in range(cols - 1):
                a, b, c, d = o + i * cols + j, o + i * cols + j + 1, o + (i + 1) * cols + j, o + (i + 1) * cols + j + 1
                self.tri(a, b, c); self.tri(b, d, c)

    def tri(self, a, b, c):
        V = self.V
        fn = np.cross(np.asarray(V[c]) - V[a], np.asarray(V[b]) - V[a])
        want = np.asarray(self.N[a]) + self.N[b] + self.N[c]
        self.T.append((a, b, c) if fn @ want >= 0 else (a, c, b))

    def poly(self, pts, n, uvs):
        """convex planar polygon (fan) with one normal"""
        o = len(self.V)
        for p, uv in zip(pts, uvs): self.V.append(np.asarray(p, float)); self.N.append(np.asarray(n, float)); self.ST.append(uv)
        for k in range(1, len(pts) - 1): self.tri(o, o + k, o + k + 1)

    def surface(self, name, shader):
        return dict(name=name, shader=shader, verts=np.array(self.V), normals=np.array(self.N), st=np.array(self.ST),
                    tris=np.array(self.T, np.int64))


def U(r, per=256.0):
    """u per radian so a full turn holds a whole number of texture tiles (no seam where spans meet across 0/360)"""
    return max(1, round(2 * math.pi * r / per)) / (2 * math.pi)


def arc(a0, a1, step=360 / NSEG):
    n = max(1, int(math.ceil((a1 - a0) / step - 1e-6)))
    return np.radians(np.linspace(a0, a1, n + 1))


def revolve(M, prof, a0, a1, u_per_rad, v_of, inward=False):
    """surface of revolution: prof = [(r, z), ...] (from bottom to top); normals perpendicular to the profile"""
    angs = arc(a0, a1)
    prof = np.asarray(prof, float)
    # profile normals (in r-z) from the tangent, pointing away from the axis (or toward it)
    tg = np.gradient(prof, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1)
    pn /= np.linalg.norm(pn, axis=1, keepdims=True)
    if inward: pn = -pn
    P = np.zeros((len(prof), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        P[:, j] = np.stack([prof[:, 0] * c, prof[:, 0] * s, prof[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = a * u_per_rad
        UV[:, j, 1] = [v_of(z) for z in prof[:, 1]]
    M.quad_grid(P, N, UV)


def ring_box(M, a0, a1, z0, z1, r0, r1, u_per_rad, vscale=64.0):
    """closed curved block between angles a0..a1 (deg), heights z0..z1, radii r0..r1 (outer, top, bottom, end faces;
    the inner face sits against the wall and is left out)"""
    revolve(M, [(r1, z0), (r1, z1)], a0, a1, u_per_rad, lambda z: -z / vscale)
    revolve(M, [(r1, z1), (r0, z1)], a0, a1, u_per_rad, lambda z: 0.0)       # top (normal up)
    revolve(M, [(r0, z0), (r1, z0)], a0, a1, u_per_rad, lambda z: 0.5)       # bottom (normal down)
    for a, sgn in ((a0, -1), (a1, 1)):
        t = math.radians(a); c, s = math.cos(t), math.sin(t)
        n = (-s * sgn, c * sgn, 0)
        M.poly([(r0 * c, r0 * s, z0), (r1 * c, r1 * s, z0), (r1 * c, r1 * s, z1), (r0 * c, r0 * s, z1)], n,
               [(0, 0), (0.1, 0), (0.1, 0.5), (0, 0.5)])


def lower_spans():
    """angle intervals of wall below the door tops (between the two hatchways)"""
    (d0a, d0b), (d1a, d1b) = DOORS
    return [(d0b, d1a), (d1b, d0a + 360)]


# ------------------------------------------------------------------------------------------------ the bell
def build():
    plate, band, inner, deck, glass, hatch = Mesh(), Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    U_WALL = U(R_OUT)                    # ~1 texel per unit round the wall
    vwall = lambda z: (H - z) / 256
    # ---- outer wall: below the door tops only between the hatchways, above them all round
    for (a0, a1) in lower_spans():
        revolve(plate, [(R_OUT, 24), (R_OUT, DOOR_TOP)], a0, a1, U_WALL, vwall)
        # flared foot (bronze band)
        revolve(band, [(256, 0), (250, 5), (241, 16), (R_OUT, 24)], a0, a1, U(R_OUT, 128), lambda z: 0.9 - z / 64)
    revolve(plate, [(R_OUT, DOOR_TOP), (R_OUT, H - 24)], 0, 360, U_WALL, vwall)
    # mid band and crown band (proud, riveted)
    revolve(band, [(R_OUT, 134), (241, 136), (241, 150), (R_OUT, 152)], 0, 360, U(R_OUT, 128), lambda z: (152 - z) / 24)
    revolve(band, [(R_OUT, H - 26), (243, H - 22), (243, DECK - 6), (240, DECK)], 0, 360, U(R_OUT, 128), lambda z: (DECK - z) / 64)
    # ribs between the bands (not over hatchways or portholes)
    for a in RIBS:
        ring_box(band, a - 1.7, a + 1.7, 24, 134, R_OUT - 1, R_OUT + 4, U(R_OUT, 128))
        ring_box(band, a - 1.7, a + 1.7, 152, H - 26, R_OUT - 1, R_OUT + 4, U(R_OUT, 128))
    # hatchway frames: two posts and a lintel (proud 7), jambs and soffit through the wall
    for (d0, d1) in DOORS:
        ring_box(band, d0 - 3.2, d0, 0, DOOR_TOP, R_OUT - 1, R_OUT + 7, U(R_OUT, 128))
        ring_box(band, d1, d1 + 3.2, 0, DOOR_TOP, R_OUT - 1, R_OUT + 7, U(R_OUT, 128))
        ring_box(band, d0 - 3.2, d1 + 3.2, DOOR_TOP, DOOR_TOP + 14, R_OUT - 1, R_OUT + 7, U(R_OUT, 128))
        for a, sgn in ((d0, 1), (d1, -1)):           # jamb faces look into the opening
            t = math.radians(a); c, s = math.cos(t), math.sin(t)
            n = (-s * sgn, c * sgn, 0)
            inner.poly([(R_IN * c, R_IN * s, 0), (R_OUT * c, R_OUT * s, 0), (R_OUT * c, R_OUT * s, DOOR_TOP), (R_IN * c, R_IN * s, DOOR_TOP)],
                       n, [(0, 1), (0.12, 1), (0.12, 0.5), (0, 0.5)])
        revolve(inner, [(R_IN, DOOR_TOP), (R_OUT, DOOR_TOP)], d0, d1, 1.0, lambda z: 0.5)    # soffit (normal down)
    # ---- portholes: raised bronze rings with glass, on the band between the mid and crown bands
    for a in PORTHOLES:
        porthole(band, glass, math.radians(a), 192.0)
    # ---- interior: wall (with the hatchway gaps), ceiling
    vin = lambda z: (H - z) / 256
    for (a0, a1) in lower_spans():
        revolve(inner, [(R_IN, 0), (R_IN, DOOR_TOP)], a0, a1, U(R_IN), vin, inward=True)
    revolve(inner, [(R_IN, DOOR_TOP), (R_IN, H)], 0, 360, U(R_IN), vin, inward=True)
    ceil = [(R_IN * math.cos(t), R_IN * math.sin(t), H) for t in arc(0, 360)[:-1]]
    inner.poly(ceil[::-1], (0, 0, -1), [(x / 256, y / 256) for (x, y, z) in ceil[::-1]])
    # ---- low riveted dome (walkable, matches the collision frustum r 240 @ 288 -> r 150 @ 316) and the hatch wheel
    o = len(deck.V)
    revolve(deck, [(240, DECK), (195, DECK + 14), (150, DOME_TOP)], 0, 360, 1.0, lambda z: 0.0)
    for i in range(o, len(deck.V)):
        x, y, z = deck.V[i]; deck.ST[i] = (0.5 + x / 480, 0.5 - y / 480)
    top = [(150 * math.cos(t), 150 * math.sin(t), DOME_TOP) for t in arc(0, 360)[:-1]]
    deck.poly(top, (0, 0, 1), [(0.5 + x / 480, 0.5 - y / 480) for (x, y, z) in top])
    revolve(hatch, [(46, DOME_TOP), (46, DOME_TOP + 6)], 0, 360, 46 / 64, lambda z: 0.95)
    cap = [(46 * math.cos(t), 46 * math.sin(t), DOME_TOP + 6) for t in arc(0, 360, 360 / 48)[:-1]]
    hatch.poly(cap, (0, 0, 1), [(0.5 + x / 92, 0.5 - y / 92) for (x, y, z) in cap])
    return [plate.surface('plate', f'{MD}/bell_plate'), band.surface('band', f'{MD}/bell_band'),
            inner.surface('inner', f'{MD}/bell_inner'), deck.surface('deck', f'{MD}/bell_deck'),
            glass.surface('glass', f'{MD}/bell_glass'), hatch.surface('hatch', f'{MD}/bell_hatch')]


def porthole(ring, glass, a, zc, ro=32, ri=22, proud=9, n=28):
    """raised ring (outer side, front annulus, inner side) and a recessed glass disc, centred on the wall at angle a"""
    rad = np.array([math.cos(a), math.sin(a), 0.0]); tan = np.array([-math.sin(a), math.cos(a), 0.0]); up = np.array([0, 0, 1.0])
    base = rad * (R_OUT - 4)                                  # starts inside the wall so the curved wall never shows a gap
    ph = np.linspace(0, 2 * math.pi, n + 1)
    def pt(r, d, p): return base + rad * d + tan * (r * math.cos(p)) + up * (zc + r * math.sin(p))
    def rn(p): return tan * math.cos(p) + up * math.sin(p)
    # outer side
    P = np.array([[pt(ro, 4, p), pt(ro, 4 + proud, p)] for p in ph]).transpose(1, 0, 2)
    N = np.array([[rn(p), rn(p)] for p in ph]).transpose(1, 0, 2)
    UV = np.array([[(p / 6, 0.2), (p / 6, 0.35)] for p in ph]).transpose(1, 0, 2)
    ring.quad_grid(P, N, UV)
    # front annulus
    P = np.array([[pt(ri, 4 + proud, p), pt(ro, 4 + proud, p)] for p in ph]).transpose(1, 0, 2)
    N = np.tile(rad, (2, n + 1, 1))
    UV = np.array([[(p / 6, 0.4), (p / 6, 0.6)] for p in ph]).transpose(1, 0, 2)
    ring.quad_grid(P, N, UV)
    # inner side, down to the glass
    P = np.array([[pt(ri, 6, p), pt(ri, 4 + proud, p)] for p in ph]).transpose(1, 0, 2)
    N = np.array([[-rn(p), -rn(p)] for p in ph]).transpose(1, 0, 2)
    UV = np.array([[(p / 6, 0.65), (p / 6, 0.75)] for p in ph]).transpose(1, 0, 2)
    ring.quad_grid(P, N, UV)
    # glass (outside) + the same disc seen from inside the bell
    disc = [pt(ri, 6, p) for p in ph[:-1]]
    glass.poly(disc, rad, [(0.5 + 0.5 * math.cos(p), 0.5 - 0.5 * math.sin(p)) for p in ph[:-1]])
    disc_in = [base + rad * (R_IN - R_OUT + 4) + tan * (ri * math.cos(p)) + up * (zc + ri * math.sin(p)) for p in ph[:-1]]
    glass.poly(disc_in[::-1], -rad, [(0.5 + 0.5 * math.cos(p), 0.5 - 0.5 * math.sin(p)) for p in ph[:-1]][::-1])


# ------------------------------------------------------------------------------------------------ textures
def _noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    a = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(a, np.float32); return (a - a.mean()) / (a.std() + 1e-6)


def _img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def metal(n, col, seed, m=None, patina=1.0):
    m = m or n
    a = np.zeros((m, n, 3), np.float32) + np.array(col, np.float32)
    a += _noise(n, 1.0, seed, m)[..., None] * 5 + _noise(n, 14, seed + 1, m)[..., None] * 14
    g = np.clip(_noise(n, 7, seed + 2, m), 0.4, None) - 0.4                    # verdigris
    a += g[..., None] * np.array([-20, 26, 30]) * patina
    streak = np.clip(_noise(n, 2, seed + 3, m), 0, None) * np.linspace(0.2, 1, m)[:, None]
    a += streak[..., None] * np.array([-8, 6, 8]) * patina
    return a


def rivet_row(d, y, x0, x1, step, r=4, hi=(236, 206, 140), lo=(110, 80, 40)):
    x = x0
    while x <= x1:
        d.ellipse((x - r, y - r + 1, x + r, y + r + 1), fill=lo); d.ellipse((x - r, y - r, x + r - 1, y + r - 1), fill=hi)
        x += step


def bell_plate():
    n = 256
    a = metal(n, (172, 122, 62), 81)
    im = _img(a); d = ImageDraw.Draw(im)
    for x in (0, 128):                                     # plate seams (vertical) with rivets
        d.line([(x, 0), (x, n)], fill=(96, 64, 30), width=3)
        for y in range(8, n, 18): d.ellipse((x + 4, y - 3, x + 10, y + 3), fill=(222, 186, 112))
    d.line([(0, 128), (n, 128)], fill=(96, 64, 30), width=3)
    rivet_row(d, 134, 8, n, 18, 3)
    return im.filter(ImageFilter.GaussianBlur(0.5))


def bell_band():
    w, h = 256, 64
    a = metal(w, (140, 96, 46), 82, h, 0.6)
    im = _img(a); d = ImageDraw.Draw(im)
    d.line([(0, 2), (w, 2)], fill=(214, 172, 96), width=2); d.line([(0, h - 3), (w, h - 3)], fill=(80, 52, 24), width=3)
    rivet_row(d, h // 2, 8, w, 16, 4)
    return im.filter(ImageFilter.GaussianBlur(0.5))


def bell_inner():
    n = 256
    a = metal(n, (128, 112, 84), 83, patina=1.2)
    im = _img(a); d = ImageDraw.Draw(im)
    for x in (0, 128):
        d.line([(x, 0), (x, n)], fill=(52, 44, 30), width=4)
    for y in (40, 210):                                    # two pipes round the inside
        d.rectangle((0, y, n, y + 10), fill=(120, 110, 96)); d.line([(0, y + 2), (n, y + 2)], fill=(170, 160, 140), width=2)
    return im.filter(ImageFilter.GaussianBlur(0.5))


def bell_deck():
    n = 512
    a = metal(n, (150, 112, 62), 84, patina=0.7)
    im = _img(a); d = ImageDraw.Draw(im)
    c = n // 2
    for r in (250, 160, 100):
        d.ellipse((c - r, c - r, c + r, c + r), outline=(90, 62, 30), width=4)
    for k in range(16):                                    # radial plate seams + rivets
        t = 2 * math.pi * k / 16
        d.line([(c + 100 * math.cos(t), c + 100 * math.sin(t)), (c + 250 * math.cos(t), c + 250 * math.sin(t))], fill=(90, 62, 30), width=3)
    for r in (244, 154):
        for k in range(48 if r > 200 else 32):
            t = 2 * math.pi * k / (48 if r > 200 else 32); x, y = c + r * math.cos(t), c + r * math.sin(t)
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(230, 196, 120))
    # anti-slip diamond pattern in the walking ring
    for i in range(-12, 13):
        for j in range(-12, 13):
            x, y = c + i * 20 + (10 if j % 2 else 0), c + j * 20
            if 112 ** 2 < (x - c) ** 2 + (y - c) ** 2 < 236 ** 2:
                d.polygon([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)], fill=(186, 146, 84))
    return im.filter(ImageFilter.GaussianBlur(0.5))


def bell_hatch():
    n = 256
    a = metal(n, (128, 96, 54), 85, patina=0.5)
    im = _img(a); d = ImageDraw.Draw(im)
    c = n // 2
    d.ellipse((4, 4, n - 5, n - 5), outline=(70, 48, 22), width=8)
    d.ellipse((c - 80, c - 80, c + 80, c + 80), outline=(196, 40, 30), width=14)      # red hand wheel
    for k in range(4):
        t = math.pi / 4 + k * math.pi / 2
        d.line([(c, c), (c + 80 * math.cos(t), c + 80 * math.sin(t))], fill=(196, 40, 30), width=10)
    d.ellipse((c - 16, c - 16, c + 16, c + 16), fill=(170, 30, 24))
    for k in range(12):
        t = 2 * math.pi * k / 12; x, y = c + 112 * math.cos(t), c + 112 * math.sin(t)
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(226, 190, 116))
    return im.filter(ImageFilter.GaussianBlur(0.5))


def bell_glass():
    n = 128
    y, x = np.mgrid[0:n, 0:n] / n
    a = np.zeros((n, n, 3), np.float32) + np.array([24, 70, 86], np.float32)
    a += (np.clip(1 - np.hypot(x - 0.35, y - 0.3) / 0.25, 0, 1) ** 2)[..., None] * np.array([120, 170, 170])
    a += ((1 - np.hypot(x - 0.5, y - 0.5) * 2).clip(0, 1))[..., None] * np.array([10, 30, 30])
    return _img(a).filter(ImageFilter.GaussianBlur(1))


def shaders():
    S = ''
    for nm, shine in (('bell_plate', 0.14), ('bell_band', 0.2), ('bell_inner', 0.05), ('bell_deck', 0.1), ('bell_hatch', 0.12)):
        S += (f'{MD}/{nm}\n{{\n\tqer_editorimage {MD}/{nm}\n\tq3map_nonplanar\n\tq3map_shadeAngle 60\n'
              f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n'
              f'\t{{\n\t\tmap {MD}/{nm}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
              f'\t{{\n\t\tmap {MD}/{nm}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {shine} {shine} {shine} )\n\t\ttcGen environment\n\t}}\n'
              f'\t{{\n\t\tmap textures/padtank/caustics\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.15 0.16 )\n'
              '\t\ttcMod scale 0.5 0.5\n\t\ttcMod turb 0 0.04 0 0.08\n\t\ttcMod scroll 0.012 0.018\n\t}\n}\n\n')
    S += (f'{MD}/bell_glass\n{{\n\tqer_editorimage {MD}/bell_glass\n\tsurfaceparm nolightmap\n'
          f'\t{{\n\t\tmap {MD}/bell_glass\n\t\trgbGen identity\n\t}}\n'
          f'\t{{\n\t\tmap {MD}/bell_glass\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.35 0.4 0.4 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
    return S


def make(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    bell_plate().save(os.path.join(d, 'bell_plate.jpg'), quality=92)
    bell_band().save(os.path.join(d, 'bell_band.jpg'), quality=92)
    bell_inner().save(os.path.join(d, 'bell_inner.jpg'), quality=92)
    bell_deck().save(os.path.join(d, 'bell_deck.jpg'), quality=92)
    bell_hatch().save(os.path.join(d, 'bell_hatch.jpg'), quality=92)
    bell_glass().save(os.path.join(d, 'bell_glass.jpg'), quality=92)
    surfs = build()
    md3write.save(os.path.join(d, 'diving_bell.md3'), surfs, name='diving_bell')
    return shaders()


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    make(o)
    import md3tool
    m = md3tool.load(os.path.join(o, MD, 'diving_bell.md3'))
    for s in m['surfaces']:
        print(s['name'], s['shader'], len(s['verts']), 'verts', len(s['tris']), 'tris', s['verts'].min(0).round(1), s['verts'].max(0).round(1))
