"""MD3 centrepieces of wop_padpinball ("Tilt!"): the giant steel pinball, pop bumpers, flippers and the plunger.

    make(out) -> writes models/padpinball/*.md3 + their textures, returns the shader text

Every model's origin is on the floor (z 0) so misc_model placement is origin = (x, y, floor). Collision is separate
common/weapclip brushes in build_padpinball.py (misc_model has none).

  steel_ball.md3   sphere r 144 resting on the floor (z 0..288), chrome: env-mapped reflection of the playfield
                   and the arcade ceiling, filtered by the baked vertex light, plus a sharp highlight stage
  pop_bumper.md3   r 112 black base plate, flared chrome skirt, white printed body ("100"), coloured dome cap with a
                   star (cap shader models/padpinball/bumper_cap; recolour per instance with _remap)
  flipper.md3      pivot at the origin, 448 long along +x, white plastic body, black rubber ring round its sides,
                   logo decal on top, chrome pivot bolt (top z 72)
  plunger.md3      shooter rod lying along +y from the front wall: wall plate, barrel, coil spring, rod, rubber tip,
                   chrome stand down to the floor
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import md3write

MD = 'models/padpinball'
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB):
    FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

BALL_R = 144.0
BUMPER_R = 112.0          # base plate radius (collision cylinder r 104)
BUMPER_H = 176.0
FLIP_L, FLIP_R0, FLIP_R1, FLIP_TOP = 448.0, 44.0, 22.0, 60.0
PLUNGER_L = 232.0


# ------------------------------------------------------------------------------------------------ mesh helpers
class Mesh:
    def __init__(self):
        self.V, self.N, self.ST, self.T = [], [], [], []

    def add_v(self, p, n, uv):
        self.V.append(np.asarray(p, float)); self.N.append(np.asarray(n, float) / max(1e-9, np.linalg.norm(n)))
        self.ST.append(tuple(uv)); return len(self.V) - 1

    def tri(self, a, b, c):
        """front side faces the averaged vertex normals (Quake winding: clockwise seen from the front)"""
        V = self.V
        fn = np.cross(V[c] - V[a], V[b] - V[a])
        want = self.N[a] + self.N[b] + self.N[c]
        self.T.append((a, b, c) if fn @ want >= 0 else (a, c, b))

    def grid(self, P, N, UV):
        rows, cols = P.shape[:2]
        o = len(self.V)
        for i in range(rows):
            for j in range(cols):
                self.add_v(P[i, j], N[i, j], UV[i, j])
        for i in range(rows - 1):
            for j in range(cols - 1):
                a, b, c, d = o + i * cols + j, o + i * cols + j + 1, o + (i + 1) * cols + j, o + (i + 1) * cols + j + 1
                if np.linalg.norm(self.V[a] - self.V[b]) < 1e-6 and np.linalg.norm(self.V[c] - self.V[d]) < 1e-6: continue
                if np.linalg.norm(self.V[a] - self.V[b]) > 1e-6: self.tri(a, b, c)
                if np.linalg.norm(self.V[c] - self.V[d]) > 1e-6: self.tri(b, d, c)

    def poly(self, pts, n, uvs):
        o = len(self.V)
        for p, uv in zip(pts, uvs): self.add_v(p, n, uv)
        for k in range(1, len(pts) - 1): self.tri(o, o + k, o + k + 1)

    def surface(self, name, shader):
        return dict(name=name, shader=shader, verts=np.array(self.V), normals=np.array(self.N), st=np.array(self.ST),
                    tris=np.array(self.T, np.int64))


def revolve(M, prof, nseg=48, u_tiles=1.0, v_of=None, a0=0.0, a1=360.0, cx=0.0, cy=0.0, inward=False):
    """surface of revolution round the z axis through (cx, cy); prof = [(r, z), ...]"""
    prof = np.asarray(prof, float)
    tg = np.gradient(prof, axis=0)
    pn = np.stack([tg[:, 1], -tg[:, 0]], 1)
    pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-9)
    if inward: pn = -pn
    angs = np.radians(np.linspace(a0, a1, nseg + 1))
    P = np.zeros((len(prof), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(prof), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        P[:, j] = np.stack([cx + prof[:, 0] * c, cy + prof[:, 0] * s, prof[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = u_tiles * j / nseg
        UV[:, j, 1] = [v_of(r, z) if v_of else 0.0 for (r, z) in prof]
    M.grid(P, N, UV)


def disc(M, r, z, nseg=48, up=True, uv_scale=None, cx=0.0, cy=0.0):
    """flat disc with planar (top-down) texture coordinates covering the disc"""
    angs = np.radians(np.linspace(0, 360, nseg, endpoint=False))
    s = uv_scale or (2 * r)
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a), z) for a in angs]
    uvs = [(0.5 + (p[0] - cx) / s, 0.5 - (p[1] - cy) / s) for p in pts]
    M.poly(pts, (0, 0, 1 if up else -1), uvs)


# ------------------------------------------------------------------------------------------------ textures
def font(sz): return ImageFont.truetype(FONTB, sz)


def noise(n, blur, seed):
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((n, n)) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im, np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def ball_env(n=512):
    """reflection seen in the steel ball (sphere map look): warm arcade ceiling with light panels at the top,
    the glass rim and the colourful playfield at the bottom"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    a = np.zeros((n, n, 3), np.float32)
    sky = np.array([70, 64, 80], np.float32); floor = np.array([40, 30, 70], np.float32)
    t = np.clip((yy - 0.42) / 0.16, 0, 1)[..., None]
    a[:] = sky * (1 - t) + floor * t
    im = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(im)
    rr = random.Random(5)
    # ceiling light panels (bright, cool white)
    for k in range(7):
        x = rr.uniform(0.0, 0.95) * n; y = rr.uniform(0.04, 0.3) * n
        d.rectangle((x, y, x + n * 0.12, y + n * 0.035), fill=(245, 248, 255))
    # neon strips
    for col in ((255, 60, 200), (60, 220, 255), (255, 200, 60)):
        y = rr.uniform(0.32, 0.4) * n
        d.rectangle((0, y, n, y + 4), fill=col)
    # cabinet rim (dark wood) and the playfield below: blobs of colour
    d.rectangle((0, 0.44 * n, n, 0.5 * n), fill=(60, 34, 20))
    for k in range(70):
        x = rr.uniform(0, 1) * n; y = rr.uniform(0.52, 1.0) * n; r = rr.uniform(6, 30)
        col = rr.choice([(240, 60, 60), (60, 120, 255), (255, 210, 50), (80, 220, 120), (255, 255, 255), (200, 80, 255)])
        d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(3))
    a = np.asarray(im, np.float32) * 0.85 + 30
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def ball_spec(n=256):
    """one sharp window highlight + soft glow (added on top with tcGen environment)"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    g = np.exp(-(((xx - 0.36) / 0.05) ** 2 + ((yy - 0.3) / 0.035) ** 2)) * 255
    g += np.exp(-(((xx - 0.36) / 0.16) ** 2 + ((yy - 0.3) / 0.12) ** 2)) * 70
    g += np.exp(-(((xx - 0.7) / 0.03) ** 2 + ((yy - 0.22) / 0.02) ** 2)) * 160
    g = np.clip(g, 0, 255)
    return Image.fromarray(np.stack([g, g, g * 0.95], -1).astype(np.uint8))


def chrome_tex(n=256):
    """generic chrome env map for skirts, bolts and the plunger"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    base = 120 + 110 * np.cos(yy * 7.0) * np.exp(-((yy - 0.35) ** 2) * 6)
    base = base[..., None] + np.array([0, 0, 8.0]) + noise(n, 6, 3)[..., None] * 8
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for k in range(5):
        x = 30 + k * 45; d.rectangle((x, 30, x + 16, 70), fill=(255, 255, 255))
    return im.filter(ImageFilter.GaussianBlur(2))


def bumper_body(w=512, h=128):
    """white printed band round the bumper body: '100' and stars"""
    im = Image.new('RGB', (w, h), (238, 236, 228)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 10), fill=(30, 30, 40)); d.rectangle((0, h - 10, w, h), fill=(30, 30, 40))
    for k in range(4):
        x = k * w / 4 + w / 8
        d.text((x, h / 2), '100', font=font(54), fill=(220, 30, 40), anchor='mm', stroke_width=3, stroke_fill=(30, 30, 40))
        sx = x + w / 8
        _star(d, sx, h / 2, 16, 7, (255, 200, 0))
    return im


def _star(d, x, y, r0, r1, col, n=5, outline=None):
    pts = []
    for k in range(2 * n):
        a = -math.pi / 2 + math.pi * k / n
        r = r0 if k % 2 == 0 else r1
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    d.polygon(pts, fill=col, outline=outline)


def bumper_cap(col, n=256):
    """dome cap seen top-down (planar mapping): translucent plastic colour with a white star in the middle"""
    c = np.array(col, np.float32)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    a = c[None, None] * (0.75 + 0.35 * (1 - r))[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.ellipse((n * 0.04, n * 0.04, n * 0.96, n * 0.96), outline=tuple(int(v * 0.6) for v in col), width=6)
    _star(d, n / 2, n / 2, n * 0.3, n * 0.13, (255, 255, 240), outline=(60, 40, 20))
    return im.filter(ImageFilter.GaussianBlur(0.8))


def black_plastic(n=64):
    a = np.zeros((n, n, 3), np.float32) + 26 + noise(n, 1, 9)[..., None] * 3
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def flipper_top(w=512, h=128):
    """white flipper top (planar mapped along the flipper) with a red logo stripe"""
    im = Image.new('RGB', (w, h), (240, 240, 236)); d = ImageDraw.Draw(im)
    d.rectangle((60, h * 0.36, w - 40, h * 0.64), fill=(220, 30, 40))
    d.text((w * 0.55, h / 2), 'TILT!', font=font(40), fill=(255, 230, 60), anchor='mm', stroke_width=3, stroke_fill=(40, 20, 20))
    return im


def rubber(n=64):
    a = np.zeros((n, n, 3), np.float32) + 22 + noise(n, 2, 11)[..., None] * 4
    a[n // 2 - 1:n // 2 + 1] += 18
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def white_plastic(n=64):
    a = np.zeros((n, n, 3), np.float32) + 234 + noise(n, 3, 12)[..., None] * 3
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def plunger_tip(n=64):
    a = np.zeros((n, n, 3), np.float32) + np.array([200, 30, 34]) + noise(n, 3, 13)[..., None] * 6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def make_textures(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    ball_env().save(os.path.join(d, 'ball_env.jpg'), quality=92)
    ball_spec().save(os.path.join(d, 'ball_spec.jpg'), quality=92)
    chrome_tex().save(os.path.join(d, 'chrome.jpg'), quality=92)
    bumper_body().save(os.path.join(d, 'bumper_body.jpg'), quality=92)
    for nme, col in (('red', (230, 40, 40)), ('yellow', (255, 196, 30)), ('blue', (40, 110, 255)), ('green', (40, 200, 90))):
        bumper_cap(col).save(os.path.join(d, 'bumper_cap_%s.jpg' % nme), quality=92)
    black_plastic().save(os.path.join(d, 'black_plastic.jpg'), quality=92)
    flipper_top().save(os.path.join(d, 'flipper_top.jpg'), quality=92)
    rubber().save(os.path.join(d, 'rubber.jpg'), quality=92)
    white_plastic().save(os.path.join(d, 'white_plastic.jpg'), quality=92)
    plunger_tip().save(os.path.join(d, 'plunger_tip.jpg'), quality=92)


# ------------------------------------------------------------------------------------------------ models
def steel_ball():
    M = Mesh()
    nlat, nlon = 28, 56
    lat = np.linspace(-math.pi / 2, math.pi / 2, nlat + 1)
    prof = [(BALL_R * math.cos(t), BALL_R + BALL_R * math.sin(t)) for t in lat]
    prof[0] = (0.0, prof[0][1]); prof[-1] = (0.0, prof[-1][1])
    revolve(M, prof, nlon, 2.0, lambda r, z: 1 - z / (2 * BALL_R))
    return [M.surface('ball', MD + '/steel_ball')]


def pop_bumper():
    base, skirt, body, cap, post = Mesh(), Mesh(), Mesh(), Mesh(), Mesh()
    # black base plate
    revolve(base, [(BUMPER_R, 0), (BUMPER_R, 6)], 48, 6)
    disc(base, BUMPER_R, 6, 48)
    # flared chrome skirt
    revolve(skirt, [(104, 6), (102, 14), (97, 26), (93, 36), (92, 40)], 48, 2, lambda r, z: z / 48)
    disc(skirt, 92, 40, 48)
    # white printed body
    revolve(body, [(84, 40), (84, 120)], 64, 1.0, lambda r, z: (120 - z) / 80)
    # cap: rim + dome (planar top-down mapping so the star sits on top)
    capprof = [(100, 120), (100, 136)] + [(100 * math.cos(t), 136 + 40 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)[1:]]
    capprof[-1] = (0.0, 176.0)
    nseg = 48
    angs = np.radians(np.linspace(0, 360, nseg + 1))
    pr = np.asarray(capprof, float)
    tg = np.gradient(pr, axis=0); pn = np.stack([tg[:, 1], -tg[:, 0]], 1); pn /= np.linalg.norm(pn, axis=1, keepdims=True)
    P = np.zeros((len(pr), len(angs), 3)); N = np.zeros_like(P); UV = np.zeros((len(pr), len(angs), 2))
    for j, a in enumerate(angs):
        c, s = math.cos(a), math.sin(a)
        P[:, j] = np.stack([pr[:, 0] * c, pr[:, 0] * s, pr[:, 1]], 1)
        N[:, j] = np.stack([pn[:, 0] * c, pn[:, 0] * s, pn[:, 1]], 1)
        UV[:, j, 0] = 0.5 + P[:, j, 0] / 216; UV[:, j, 1] = 0.5 - P[:, j, 1] / 216
    cap.grid(P, N, UV)
    disc(cap, 100, 120, 48, up=False)
    # three chrome mounting posts round the body
    for k in range(3):
        a = math.radians(30 + 120 * k)
        revolve(post, [(6, 40), (6, 120)], 8, 1, lambda r, z: z / 64, cx=94 * math.cos(a), cy=94 * math.sin(a))
    return [base.surface('base', MD + '/black_plastic'), skirt.surface('skirt', MD + '/chrome'),
            body.surface('body', MD + '/bumper_body'), cap.surface('cap', MD + '/bumper_cap_red'),
            post.surface('posts', MD + '/chrome')]


def flipper_outline(r0=FLIP_R0, r1=FLIP_R1, L=FLIP_L, n=24, grow=0.0):
    """tangent hull of the pivot circle (r0 at the origin) and the tip circle (r1 at x = L), counter-clockwise"""
    r0 += grow; r1 += grow
    a = math.asin((r0 - r1) / L)                 # tangent angle
    pts = []
    for t in np.linspace(math.pi / 2 + a, 3 * math.pi / 2 - a, n):      # pivot side (left)
        pts.append((r0 * math.cos(t), r0 * math.sin(t)))
    for t in np.linspace(-math.pi / 2 - a, math.pi / 2 + a, n // 2):     # tip side (right)
        pts.append((L + r1 * math.cos(t), r1 * math.sin(t)))
    return pts


def flipper():
    body, rub, top, bolt = Mesh(), Mesh(), Mesh(), Mesh()
    out = flipper_outline()
    n = len(out)
    cen = np.mean(out, 0)
    # side walls: lower white strip, rubber ring bulging 6u, upper white strip
    def side(mesh, z0, z1, grow0, grow1, vt):
        o2 = flipper_outline(grow=grow0); o3 = flipper_outline(grow=grow1)
        per = 0.0
        for k in range(len(o2)):
            p, q = o2[k], o2[(k + 1) % len(o2)]
            p2, q2 = o3[k], o3[(k + 1) % len(o3)]
            e = np.array(q) - np.array(p); L = np.linalg.norm(e)
            nrm = np.array([e[1], -e[0], 0]) / max(L, 1e-9)
            if nrm[:2] @ (np.array(p) - cen) < 0: nrm = -nrm
            u0, u1 = per / 128, (per + L) / 128; per += L
            mesh.poly([(p[0], p[1], z0), (q[0], q[1], z0), (q2[0], q2[1], z1), (p2[0], p2[1], z1)], nrm,
                      [(u0, vt[0]), (u1, vt[0]), (u1, vt[1]), (u0, vt[1])])
    side(body, 0, 18, 0, 0, (0.95, 0.7))
    side(rub, 18, 32, 0, 6, (0.9, 0.5)); side(rub, 32, 46, 6, 0, (0.5, 0.1))
    side(body, 46, FLIP_TOP, 0, 0, (0.3, 0.1))
    # top face: planar mapping along the flipper (0..L+r1 -> u 0..1)
    span = FLIP_L + FLIP_R0 + FLIP_R1
    top.poly([(x, y, FLIP_TOP) for (x, y) in out], (0, 0, 1),
             [((x + FLIP_R0) / span, 0.5 - y / (2 * FLIP_R0 + 8)) for (x, y) in out])
    # chrome pivot bolt
    revolve(bolt, [(24, FLIP_TOP), (24, FLIP_TOP + 8), (20, FLIP_TOP + 12)], 24, 1, lambda r, z: z / 32)
    disc(bolt, 20, FLIP_TOP + 12, 24)
    revolve(bolt, [(8, FLIP_TOP + 12), (8, FLIP_TOP + 16)], 6, 1, lambda r, z: z / 16)
    disc(bolt, 8, FLIP_TOP + 16, 6)
    return [body.surface('body', MD + '/white_plastic'), rub.surface('rubber', MD + '/rubber'),
            top.surface('top', MD + '/flipper_top'), bolt.surface('bolt', MD + '/chrome')]


def plunger():
    """shooter rod along +y from the wall (y 0) at height 64; chrome stand to the floor"""
    chrome, spring, tip, plate = Mesh(), Mesh(), Mesh(), Mesh()
    zc = 64.0
    def tube(mesh, r, y0, y1, nseg=16, caps=True):
        P = np.zeros((2, nseg + 1, 3)); N = np.zeros_like(P); UV = np.zeros((2, nseg + 1, 2))
        for j in range(nseg + 1):
            a = 2 * math.pi * j / nseg
            for i, y in enumerate((y0, y1)):
                P[i, j] = (r * math.cos(a), y, zc + r * math.sin(a)); N[i, j] = (math.cos(a), 0, math.sin(a))
                UV[i, j] = (j / nseg, y / 64)
        mesh.grid(P, N, UV)
        if caps:
            for y, sg in ((y0, -1), (y1, 1)):
                pts = [(r * math.cos(2 * math.pi * k / nseg), y, zc + r * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]
                mesh.poly(pts, (0, sg, 0), [(0.5 + p[0] / (2 * r), 0.5 + (p[2] - zc) / (2 * r)) for p in pts])
    # wall plate (square, 96 x 96, 6 thick) and barrel
    P = [(-48, 0, zc - 48), (48, 0, zc - 48), (48, 0, zc + 48), (-48, 0, zc + 48)]
    plate.poly([(x, 6, z) for (x, _, z) in P], (0, 1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    for (a, b, nrm) in (((-48, -48), (48, -48), (0, 0, -1)), ((48, -48), (48, 48), (1, 0, 0)), ((48, 48), (-48, 48), (0, 0, 1)), ((-48, 48), (-48, -48), (-1, 0, 0))):
        plate.poly([(a[0], 0, zc + a[1]), (b[0], 0, zc + b[1]), (b[0], 6, zc + b[1]), (a[0], 6, zc + a[1])], nrm, [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
    tube(chrome, 22, 6, 46)
    tube(chrome, 7, 46, PLUNGER_L - 30, 10, caps=False)
    # coil spring: helix tube
    turns, r_coil, r_wire = 7, 20.0, 3.0
    y0s, y1s = 50.0, 150.0
    nu, nv = turns * 24, 6
    Pp = np.zeros((nv + 1, nu + 1, 3)); Nn = np.zeros_like(Pp); UVv = np.zeros((nv + 1, nu + 1, 2))
    for i in range(nu + 1):
        t = i / nu; a = 2 * math.pi * turns * t
        c = np.array([r_coil * math.cos(a), y0s + (y1s - y0s) * t, zc + r_coil * math.sin(a)])
        radial = np.array([math.cos(a), 0, math.sin(a)]); axial = np.array([0, 1.0, 0])
        for j in range(nv + 1):
            b = 2 * math.pi * j / nv
            nrm = radial * math.cos(b) + axial * math.sin(b)
            Pp[j, i] = c + r_wire * nrm; Nn[j, i] = nrm; UVv[j, i] = (t * 8, j / nv)
    spring.grid(Pp, Nn, UVv)
    # rubber tip
    tube(tip, 16, PLUNGER_L - 30, PLUNGER_L, 16)
    # stand: two chrome legs under the barrel down to the floor
    for x in (-30, 30):
        for (y0, y1) in ((14, 30),):
            pts = [(x - 5, y0, 0), (x + 5, y0, 0), (x + 5, y1, 0), (x - 5, y1, 0)]
            for (pa, nrm) in ((((x - 5, y0), (x + 5, y0)), (0, -1, 0)), (((x + 5, y0), (x + 5, y1)), (1, 0, 0)),
                              (((x + 5, y1), (x - 5, y1)), (0, 1, 0)), (((x - 5, y1), (x - 5, y0)), (-1, 0, 0))):
                (ax, ay), (bx, by) = pa
                chrome.poly([(ax, ay, 0), (bx, by, 0), (bx, by, zc - 18), (ax, ay, zc - 18)], nrm, [(0, 1), (0.2, 1), (0.2, 0), (0, 0)])
    return [chrome.surface('chrome', MD + '/chrome'), spring.surface('spring', MD + '/chrome'),
            tip.surface('tip', MD + '/plunger_tip'), plate.surface('plate', MD + '/chrome')]


def make(out):
    d = os.path.join(out, MD); os.makedirs(d, exist_ok=True)
    make_textures(out)
    md3write.save(os.path.join(d, 'steel_ball.md3'), steel_ball(), 'steel_ball')
    md3write.save(os.path.join(d, 'pop_bumper.md3'), pop_bumper(), 'pop_bumper')
    md3write.save(os.path.join(d, 'flipper.md3'), flipper(), 'flipper')
    md3write.save(os.path.join(d, 'plunger.md3'), plunger(), 'plunger')
    return shaders()


def shaders():
    S = '// ---- MD3 models (pin_models.py)\n'
    S += f'''{MD}/steel_ball
{{
	qer_editorimage {MD}/ball_env.jpg
	{{
		map {MD}/ball_env.jpg
		tcGen environment
		rgbGen identity
	}}
	{{
		map $whiteimage
		blendFunc GL_DST_COLOR GL_SRC_COLOR
		rgbGen vertex
	}}
	{{
		map {MD}/ball_spec.jpg
		blendFunc GL_ONE GL_ONE
		tcGen environment
		rgbGen identity
	}}
}}

{MD}/chrome
{{
	qer_editorimage {MD}/chrome.jpg
	{{
		map {MD}/chrome.jpg
		tcGen environment
		rgbGen identity
	}}
	{{
		map $whiteimage
		blendFunc GL_DST_COLOR GL_SRC_COLOR
		rgbGen vertex
	}}
}}

'''
    for nme in ('black_plastic', 'bumper_body', 'white_plastic', 'rubber', 'flipper_top', 'plunger_tip'):
        S += f'''{MD}/{nme}
{{
	qer_editorimage {MD}/{nme}.jpg
	{{
		map {MD}/{nme}.jpg
		rgbGen vertex
	}}
}}

'''
    for col, rgb in (('red', '1 0.3 0.25'), ('yellow', '1 0.85 0.3'), ('blue', '0.35 0.6 1'), ('green', '0.35 1 0.5')):
        S += f'''{MD}/bumper_cap_{col}
{{
	qer_editorimage {MD}/bumper_cap_{col}.jpg
	{{
		map {MD}/bumper_cap_{col}.jpg
		rgbGen vertex
	}}
	{{
		map {MD}/bumper_cap_{col}.jpg
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.35 0.3 0 0.7
	}}
}}

'''
    return S


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else 'out'
    print(make(o)[:200])
