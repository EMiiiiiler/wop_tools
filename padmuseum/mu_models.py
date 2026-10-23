"""Custom MD3/IQM map objects for wop_padmuseum (Midnight Museum). All geometry and art is original and generated here.
    make() -> writes models/padmuseum/*.md3/*.iqm and their images (shaders are registered in mulib.REG)

Scale 64u per metre. Origin = floor centre unless noted; the T. rex, whale, dome and skylight frame are built in place
(see layout.py) so the weapclip collision in build_museum.py lines up with them.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, prism, grid_normals, rot_z, rot_axis, frame, arc_path
from mulib import *
import mulib
import layout as L


# ================================================================================================= mesh helpers
_tube = tube


def tube(M, path, radii, **kw):
    """meshlib.tube, with a radius list of any length resampled along the path"""
    path = np.asarray(path, float)
    r = np.atleast_1d(np.asarray(radii, float))
    if len(r) > 1 and len(r) != len(path):
        r = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(r)), r)
    _tube(M, path, r, **kw)

def _ball(r, n=10):
    m = Mesh(); sphere(m, (0, 0, 0), r, nu=n, nv=max(4, n // 2)); return m


def turned(M, h, r, z0=0.0, n=12, bulbs=((0.15, 1.35), (0.55, 1.15)), foot=1.25, cx=0.0, cy=0.0):
    """turned wooden leg / spindle"""
    prof = [(0, z0), (r * foot, z0), (r * foot, z0 + h * 0.04), (r * 0.8, z0 + h * 0.07)]
    for (f, k) in bulbs:
        prof += [(r * 0.85, z0 + h * (f - 0.06)), (r * k, z0 + h * f), (r * 0.8, z0 + h * (f + 0.06))]
    prof += [(r, z0 + h * 0.93), (r * 1.2, z0 + h * 0.97), (r * 1.2, z0 + h), (0, z0 + h)]
    revolve(M, prof, n=n, u_tiles=1, vlen=max(64, h), cx=cx, cy=cy)


def cushion(M, mn, mx, puff=10.0, r=14.0, k=4, tile=128.0):
    mn = np.asarray(mn, float); mx = np.asarray(mx, float); c = (mn + mx) / 2; H = (mx - mn) / 2
    def inf(x, y, z, n):
        u = [(x - c[0]) / H[0], (y - c[1]) / H[1], (z - c[2]) / H[2]]
        ax = int(np.argmax(np.abs(n)))
        o = [a for i, a in enumerate(u) if i != ax]
        return puff * max(0.0, (1 - o[0] ** 2)) * max(0.0, (1 - o[1] ** 2))
    rbox(M, mn, mx, r=r, k=k, tile=tile, inflate=inf)


CYC = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]])      # (u, v, w) -> (w, u, v): polygon in (y, z), extruded along x
RX90 = np.array([[1.0, 0, 0], [0, 0, -1], [0, 1, 0]])     # (x, y, z) -> (x, -z, y): rotation about x by +90 degrees


def side_prism(M, poly_xz, y0, y1, tile=128.0):
    """polygon in the (x, z) plane extruded along y from y0 to y1"""
    m = Mesh(); prism(m, [(x, z) for (x, z) in poly_xz], -y1, -y0, tile=tile)
    m.transform(RX90)               # prism z (extrusion) -> -y, prism y (profile) -> z
    M.add(m)


def disc_axis(M, c, r, nrm, n=16, tex_scale=None):
    c = np.asarray(c, float); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm)
    b1, b2 = frame(nrm)
    pts = [c + b1 * r * math.cos(a) + b2 * r * math.sin(a) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    M.poly(pts, nrm, [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def cyl(M, c, r, h, n=16, caps=True, tile=128.0):
    """vertical cylinder from c (bottom centre) up h"""
    c = np.asarray(c, float)
    revolve(M, [(0, c[2]), (r, c[2]), (r, c[2] + h), (0, c[2] + h)] if caps else [(r, c[2]), (r, c[2] + h)], n=n, cx=c[0], cy=c[1], vlen=tile)


def bar(M, a, b, r, n=8):
    tube(M, [a, b], r, nseg=n)


def box(M, mn, mx, r=2.0, tile=64.0, k=2, faces='nsewtb'):
    rbox(M, mn, mx, r=r, k=k, tile=tile, faces=faces)


def quad_uv(M, p0, p1, p2, p3, uvs, n=None):
    P = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
    if n is None:
        n = np.cross(P[1] - P[0], P[3] - P[0]); n /= max(1e-9, np.linalg.norm(n))
    M.poly(P, n, uvs)


def picture_quad(M, cx, cy, cz, w, h, nrm):
    """textured quad (u left->right as seen from the front), normal nrm (axis-aligned in xy)"""
    nrm = np.asarray(nrm, float)
    right = np.array([-nrm[1], nrm[0], 0.0])           # viewer looks along -nrm with z up: right = up x (-n)... = (-ny, nx)
    c = np.array([cx, cy, cz], float)
    p = [c - right * w / 2 - [0, 0, h / 2], c + right * w / 2 - [0, 0, h / 2], c + right * w / 2 + [0, 0, h / 2], c - right * w / 2 + [0, 0, h / 2]]
    M.poly(p, nrm, [(0, 1), (1, 1), (1, 0), (0, 0)])


class Mdl(Model):
    pass


def T(name, a, alpha=None):
    save_img(out(MD, name), a, alpha)
    return name




# ================================================================================================= textures (models)
def tex_wood(n=128, col=(196, 150, 100), seed=1, lines=10):
    x, y = xy(n)
    g = noise(n, 1, seed)
    streak = np.asarray(img(g * 50 + 128).resize((n, max(4, n // 24))).resize((n, n)), np.float32) - 128
    c = np.zeros((n, n, 3), np.float32) + C(col) + streak[..., None] * 0.3
    c += (np.sin(y * lines * 2 * math.pi + noise(n, 14, seed + 1) * 2) * 6)[..., None]
    return c + N3(n, 0.8, seed + 2, 3)


def tex_env(n=128, seed=25):
    x, y = xy(n)
    c = lerp(C((40, 50, 80)), C((200, 210, 240)), np.clip(1 - y * 1.2, 0, 1)[..., None])
    return c + N3(n, 8, seed, 18)


def tex_bone(n=128, seed=3, col=(176, 150, 110)):
    """fossil bone: mottled brown-ochre with darker pores"""
    c = fill(n, col, 10, seed) + N3(n, 0.6, seed + 1, 14) + N3(n, 4, seed + 2, 12)
    pores = np.clip(noise(n, 0.8, seed + 3) - 1.8, 0, 1)[..., None]
    return c * (1 - pores * 0.5)


def tex_fur(n=128, col=(96, 60, 36), seed=7):
    c = fill(n, col, 10, seed) + N3(n, 0.5, seed + 1, 18)
    st = np.asarray(img(noise(n, 0.5, seed + 2) * 40 + 128).resize((n, n // 8)).resize((n, n)), np.float32) - 128
    return c + st[..., None] * 0.35


def tex_label(text, w, h, bg, fg, serif=True):
    return text_img(text, w, h, bg, fg, serif)


def tex_gold(n=64, seed=11):
    return fill(n, (220, 170, 60), 10, seed) + N3(n, 0.6, seed + 1, 10)


def tex_lapis(n=64, seed=13):
    c = fill(n, (30, 50, 130), 6, seed)
    flecks = np.clip(noise(n, 0.5, seed + 1) - 1.6, 0, 1)[..., None]
    return lerp(c, C((230, 200, 90)), flecks)


def tex_nemes(n=128, seed=15):
    """striped royal headcloth: gold and lapis bands"""
    x, y = xy(n)
    m = ((y * 10) % 1.0) < 0.5
    return np.where(m[..., None], tex_gold(n, seed), tex_lapis(n, seed + 1))


def tex_sarc_face(n=256, seed=17):
    """painted anthropoid coffin lid: gold face, collar bands, wings, glyph columns"""
    im = Image.new('RGB', (n, n), (200, 150, 50)); d = ImageDraw.Draw(im)
    for k, col in enumerate(((30, 60, 140), (180, 60, 40), (40, 120, 90), (230, 190, 80))):
        d.rectangle((0, 40 + k * 18, n, 50 + k * 18), fill=col)
    for x in (n * 0.3, n * 0.5, n * 0.7):
        d.rectangle((x - 10, 130, x + 10, n), fill=(230, 210, 150))
        for y in range(140, n, 22):
            d.ellipse((x - 5, y, x + 5, y + 10), outline=(40, 40, 40), width=2)
    return np.asarray(im, np.float32) + N3(n, 1, seed, 5)


def tex_crystal(n=64, col=(170, 90, 230), seed=19):
    x, y = xy(n)
    return fill(n, col, 6, seed) * (0.7 + 0.5 * y)[..., None]


def tex_geode_out(n=128, seed=21):
    return fill(n, (120, 112, 104), 10, seed) + N3(n, 0.5, seed + 1, 20) + N3(n, 4, seed + 2, 14)


def tex_copper(n=128, seed=23):
    c = fill(n, (90, 150, 130), 8, seed)
    x, y = xy(n)
    return c * np.where(((x * 16) % 1.0 < 0.06)[..., None], 0.7, 1.0) + N3(n, 6, seed + 1, 10)


def tex_squid(n=128, seed=27):
    c = fill(n, (190, 70, 60), 8, seed)
    spots = np.clip(noise(n, 1.5, seed + 1) - 1.0, 0, 1)[..., None]
    return lerp(c, C((240, 140, 120)), spots)


def tex_shark(n=128, seed=29):
    x, y = xy(n)
    return lerp(C((100, 112, 124)), C((230, 232, 230)), np.clip((y - 0.55) * 6, 0, 1)[..., None]) + N3(n, 1, seed, 5)


def tex_plush(col, n=64, seed=31):
    return fill(n, col, 6, seed) + N3(n, 0.5, seed + 1, 14)


def tex_monitor(n=128, seed=33):
    """CCTV monitor: four grey camera views"""
    im = Image.new('RGB', (n, n), (10, 14, 12)); d = ImageDraw.Draw(im)
    for (x0, y0) in ((4, 4), (66, 4), (4, 66), (66, 66)):
        g = np.random.default_rng(seed + x0 + y0)
        d.rectangle((x0, y0, x0 + 58, y0 + 58), fill=(60, 80, 70))
        for _ in range(4):
            a, b = g.uniform(x0, x0 + 50), g.uniform(y0 + 20, y0 + 50)
            d.rectangle((a, b, a + g.uniform(6, 14), y0 + 58), fill=(90, 110, 100))
        d.text((x0 + 3, y0 + 2), 'CAM', fill=(160, 200, 160))
    return np.asarray(im, np.float32)


def make_textures():
    T('env', tex_env())
    T('bone', tex_bone()); T('bone_dark', tex_bone(128, 4, (120, 96, 70))); T('steel', fill(64, (90, 94, 100), 4, 5)); T('brass', fill(64, (200, 160, 70), 8, 6))
    T('fur', tex_fur()); T('fur_tan', tex_fur(128, (170, 130, 80), 8)); T('ivory', fill(64, (236, 226, 200), 4, 9)); T('black', fill(64, (20, 20, 24), 2, 10))
    T('gold', tex_gold()); T('lapis', tex_lapis()); T('nemes', tex_nemes()); T('sarc_face', tex_sarc_face()); T('granite', fill(128, (60, 56, 60), 6, 12) + N3(128, 0.5, 13, 16))
    T('sandstone_m', fill(128, (210, 178, 126), 8, 14) + N3(128, 3, 15, 10)); T('red_granite', fill(128, (150, 80, 70), 8, 16) + N3(128, 0.5, 17, 16))
    T('glow_sarc', fill(64, (120, 255, 160), 3, 18)); T('crystal_p', tex_crystal()); T('crystal_b', tex_crystal(64, (90, 160, 250), 20))
    T('crystal_g', tex_crystal(64, (90, 230, 140), 22)); T('crystal_c', tex_crystal(64, (240, 240, 255), 24)); T('geode_out', tex_geode_out())
    T('copper', tex_copper()); T('lens', fill(32, (180, 220, 255), 2, 26)); T('sun', fill(64, (255, 210, 90), 4, 28))
    for k, col in enumerate(((180, 160, 140), (220, 170, 90), (70, 120, 200), (200, 90, 60), (210, 170, 120), (220, 200, 150), (150, 200, 220), (80, 110, 210))):
        T(f'planet_{k}', fill(64, col, 8, 40 + k) + N3(64, 3, 50 + k, 14))
    T('squid', tex_squid()); T('shark', tex_shark()); T('water_t', fill(64, (40, 120, 170), 6, 30)); T('glass_t', fill(64, (200, 230, 240), 3, 31))
    T('coral', fill(64, (240, 120, 110), 8, 32)); T('coral_y', fill(64, (250, 200, 80), 8, 33)); T('sand', fill(128, (220, 200, 150), 8, 34) + N3(128, 0.5, 35, 10))
    T('wood_dark', tex_wood(128, (80, 52, 34), 36)); T('wood', tex_wood(128, (150, 104, 64), 37)); T('velvet', fill(64, (140, 24, 34), 5, 38))
    T('felt_green', fill(64, (40, 90, 60), 4, 39)); T('stone_w', fill(128, (220, 214, 200), 5, 40) + N3(128, 3, 41, 6)); T('monitor', tex_monitor())
    T('plush_g', tex_plush((90, 170, 80))); T('plush_o', tex_plush((240, 140, 50), seed=33)); T('plush_p', tex_plush((170, 100, 200), seed=35))
    T('lamp_glow', fill(32, (255, 230, 170), 2, 42)); T('exit_glow', fill(32, (80, 255, 120), 2, 43)); T('red_glow', fill(32, (255, 60, 50), 2, 44))
    T('snow_m', fill(128, (230, 236, 244), 6, 45)); T('ice', fill(64, (190, 220, 240), 4, 46)); T('rock', fill(128, (110, 104, 98), 10, 47) + N3(128, 3, 48, 14))
    T('feather', fill(64, (90, 70, 50), 8, 49) + N3(64, 0.5, 50, 14)); T('hvac', fill(64, (180, 184, 186), 3, 51)); T('grille', np.asarray(img(fill(64, (70, 72, 76), 2, 52) * (0.6 + 0.4 * (xy(64)[1] * 16 % 1.0 > 0.5))[..., None]), np.float32))
    T('meteorite', fill(64, (60, 56, 54), 8, 53) + N3(64, 0.6, 54, 18)); T('ammonite', fill(64, (170, 140, 100), 8, 55)); T('slate', fill(64, (60, 64, 70), 6, 56))
    T('label_card', tex_label('Tyrannosaurus rex\n68 million years', 256, 128, (240, 236, 224), (40, 36, 30)))
    T('backdrop_ice', np.asarray(img(lerp(C((150, 180, 210)), C((240, 246, 255)), xy(256)[1][..., None]) + N3(256, 6, 57, 8)), np.float32))
    T('sign_tickets', text_img('TICKETS', 256, 64, (30, 40, 70), (240, 220, 150)))
    T('panel_dino', tex_poster('AGE OF DINOSAURS', '', (60, 40, 30), (20, 14, 10), (240, 210, 150), 1, 'dino'))
    T('panel_ice', tex_poster('THE ICE AGE', '', (40, 70, 100), (14, 24, 40), (230, 240, 255), 2, 'ice'))
    T('panel_space', tex_poster('OUR SOLAR SYSTEM', '', (20, 20, 60), (4, 4, 16), (220, 220, 255), 3, 'space'))
    T('geode_in', np.asarray(img(fill(128, (70, 30, 90), 10, 60) + N3(128, 0.6, 61, 26)), np.float32))
    T('cushion_blue', fill(64, (40, 50, 110), 5, 58)); T('rope_red', fill(32, (170, 20, 30), 4, 59))


def tex_poster(title, sub, bg0, bg1, fg, seed=1, kind='dino'):
    """exhibit info panel: gradient, a line-drawn specimen, title and a few lines of 'text'"""
    w, h = 256, 256
    x, y = xy(w, h)
    a = lerp(C(bg0), C(bg1), y[..., None]) + N3(w, 6, seed, 4, h)
    im = img(a).convert('RGB'); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    fgc = tuple(int(v) for v in fg)
    if kind == 'dino':
        pts = [(30, 150), (70, 120), (120, 110), (160, 100), (190, 90), (215, 80), (230, 86)]
        d.line(pts, fill=fgc, width=4)
        for (px, py) in pts[1:5]:
            d.line([(px, py), (px - 4, py + 34)], fill=fgc, width=2)
        d.line([(150, 104), (140, 150), (150, 186)], fill=fgc, width=4); d.line([(170, 98), (176, 148), (166, 186)], fill=fgc, width=4)
        d.ellipse((214, 70, 246, 96), outline=fgc, width=3)
    elif kind == 'ice':
        d.ellipse((60, 90, 200, 160), outline=fgc, width=4); d.ellipse((40, 80, 90, 130), outline=fgc, width=4)
        for lx in (80, 110, 160, 185): d.line([(lx, 150), (lx, 190)], fill=fgc, width=6)
        d.arc((10, 100, 70, 170), 270, 90, fill=fgc, width=4)
    else:
        d.ellipse((100, 90, 160, 150), outline=fgc, width=4)
        for k in range(3): d.ellipse((130 - 40 - 22 * k, 120 - 12 - 8 * k, 130 + 40 + 22 * k, 120 + 12 + 8 * k), outline=fgc, width=1)
        for _ in range(30):
            sx, sy = rng.uniform(0, w), rng.uniform(60, 200); d.point((sx, sy), fill=fgc)
    d.text((14, 12), title, font=font(26), fill=fgc)
    for k in range(5):
        d.rectangle((14, 204 + k * 9, 14 + rng.uniform(150, 228), 207 + k * 9), fill=tuple(int(v * 0.8) for v in fg))
    return np.asarray(im, np.float32)


def info_panel(tex):
    """free-standing exhibit panel (origin floor centre, faces +x and -x, 240 wide along y, 236 tall)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lm', tag='panel')); P = X.mesh(S(tex, 'lm'))
    rbox(W, (-10, -124, 0), (10, -116, 236), r=1, k=1, tile=64); rbox(W, (-10, 116, 0), (10, 124, 236), r=1, k=1, tile=64)
    rbox(W, (-8, -116, 0), (8, 116, 20), r=1, k=1, tile=64); rbox(W, (-8, -116, 226), (8, 116, 236), r=1, k=1, tile=64)
    rbox(W, (-6, -116, 20), (6, 116, 226), r=0.5, k=1, tile=128)
    for s_ in (-1, 1):
        picture_quad(P, s_ * 6.5, 0, 123, 230, 204, (s_, 0, 0))
        rbox(W, (-40, s_ * 120 - 6, 0), (40, s_ * 120 + 6, 8), r=1, k=1, tile=32)
    return X


# ================================================================================================= helpers
def spline(ctrl, n=40):
    """Catmull-Rom spline through control points -> n points"""
    P = [np.asarray(p, float) for p in ctrl]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, max(2, n // (len(P) - 3)), endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


def bone(M, a, b, r, knob=1.35, n=8):
    """long bone: shaft with knobbly ends"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    tube(M, [a, a + (b - a) * 0.15, b - (b - a) * 0.15, b], [r * knob, r * 0.85, r * 0.85, r * knob], nseg=n)


def frame_from(d, up=(0, 0, 1)):
    d = np.asarray(d, float); d /= np.linalg.norm(d)
    s = np.cross(d, up)
    if np.linalg.norm(s) < 1e-6: s = np.cross(d, [1, 0, 0])
    s /= np.linalg.norm(s); u = np.cross(s, d)
    return np.stack([s, d, u], 1)          # columns: side, forward, up


# ================================================================================================= T. rex
def trex():
    """mounted T. rex skeleton (world coords; origin = TREX centre at floor): vertebral column following the walkway,
    neural spines up to the walk surface, ribs, gastralia, pelvis, legs, tiny arms, skull with jaws and teeth, steel
    mount rods. Faces south (-y)."""
    X = Model()
    B = X.mesh(S('bone', 'lm', shade=60)); Bd = X.mesh(S('bone_dark', 'lm', shade=60)); St = X.mesh(S('steel', 'lms', v=0.12)); Iv = X.mesh(S('ivory', 'lm'))
    tx, ty = L.TREX
    path = [(0.0, y - ty, z) for (y, z) in L.TREX_PATH[:-1]]
    # centrum line 30 below the walk surface (the neural spines reach the walk surface)
    pts = spline([(0, y, max(z - 34, 4)) for (_, y, z) in path], 60)
    for k in range(len(pts) - 1):
        p, q = pts[k], pts[k + 1]
        d = q - p; ln = np.linalg.norm(d)
        if ln < 1: continue
        t = k / (len(pts) - 1)
        r = 5 + 13 * min(1.0, t * 2.2) * (1.0 if t < 0.8 else 0.8)
        Rf = frame_from(d)
        m = Mesh(); ellipsoid(m, (0, 0, 0), r * 0.9, ln * 0.45, r, nu=10, nv=6)
        B.add(m, Rf, (p + q) / 2)
        sp = 30 - (4 if t < 0.15 else 0)
        top = (p + q) / 2 + Rf[:, 2] * min(sp, 34)
        m2 = Mesh(); rbox(m2, (-2.5, -ln * 0.3, 0), (2.5, ln * 0.3, min(sp, 34)), r=1.5, k=1, tile=32)
        Bd.add(m2, Rf, (p + q) / 2)
    # ribs from the dorsal vertebrae (y -60..150 in path terms), gastralia under the belly
    for yy in np.linspace(-50 - ty * 0, 150, 11):
        yl = yy - ty
        for s_ in (-1, 1):
            rib = [(s_ * 8, yl, 200), (s_ * 46, yl - 6, 178), (s_ * 58, yl - 10, 130), (s_ * 44, yl - 12, 86), (s_ * 18, yl - 14, 70)]
            tube(B, spline(rib, 10), [3.4, 3.0, 2.6, 2.2, 1.8, 1.6, 1.4, 1.3, 1.2, 1.1, 1.0], nseg=6, caps=(True, True))
    for yy in np.linspace(-40, 110, 8):
        yl = yy - ty
        tube(Bd, spline([(-30, yl, 74), (0, yl - 6, 64), (30, yl, 74)], 8), 1.6, nseg=5)
    # pelvis + legs
    hy = 150 - ty
    m = Mesh(); ellipsoid(m, (0, 0, 0), 14, 70, 40, nu=12, nv=6)
    for s_ in (-1, 1):
        B.add(m, np.eye(3), (s_ * 26, hy, 196))
        bone(B, (s_ * 30, hy + 10, 170), (s_ * 60, hy - 30, 92), 10)                     # femur
        bone(B, (s_ * 60, hy - 30, 92), (s_ * 62, hy + 20, 34), 8)                       # tibia
        bone(B, (s_ * 62, hy + 20, 34), (s_ * 64, hy + 4, 20), 6)                        # metatarsals
        for k in (-1, 0, 1):
            tube(B, [(s_ * 64, hy + 4, 20), (s_ * (64 + 14 * k), hy - 30, 18), (s_ * (64 + 18 * k), hy - 46, L.TREX_PLINTH[4] + 2)], [5, 4, 2], nseg=6)
    # tiny arms
    for s_ in (-1, 1):
        bone(B, (s_ * 30, -40 - ty, 196), (s_ * 40, -64 - ty, 170), 3.4)
        bone(B, (s_ * 40, -64 - ty, 170), (s_ * 36, -84 - ty, 180), 2.6)
    # skull: deep cranium, tall narrow snout, open jaw, eye sockets and the big fenestrae, teeth
    sy0 = -150 - ty; sz = 258
    ellipsoid(B, (0, sy0 - 20, sz + 8), 30, 44, 38, nu=16, nv=10)
    tube(B, [(0, sy0 - 36, sz + 4), (0, sy0 - 90, sz - 2), (0, sy0 - 136, sz - 10)], [24, 18, 11], nseg=12, ry=[30, 24, 15])
    tube(Bd, [(0, sy0 - 4, sz - 30), (0, sy0 - 70, sz - 40), (0, sy0 - 130, sz - 44)], [20, 15, 9], nseg=10, ry=[11, 9, 6])
    for s_ in (-1, 1):
        sphere(X.mesh(S('black', 'lm')), (s_ * 24, sy0 - 34, sz + 18), 9, nu=8, nv=5)
        ellipsoid(X.mesh(S('black', 'lm')), (s_ * 26, sy0 - 4, sz + 4), 5, 16, 12, nu=8, nv=5)
        ellipsoid(X.mesh(S('black', 'lm')), (s_ * 18, sy0 - 76, sz - 4), 4, 18, 8, nu=8, nv=5)
        for k in range(9):
            yy = sy0 - 40 - k * 11
            w_ = 20 - k * 1.1
            m_ = Mesh(); revolve(m_, [(0, 0), (2.6, 0), (0, 12)], n=6)
            Iv.add(m_, np.array([[1, 0, 0], [0, 1, 0], [0, 0, -1.0]]), (s_ * w_ * 0.8, yy, sz - 22 + k * 0.4))
            m_ = Mesh(); revolve(m_, [(0, 0), (2.2, 0), (0, 9)], n=6)
            Iv.add(m_, np.eye(3), (s_ * w_ * 0.6, yy - 4, sz - 40 - k * 0.5))
    # steel mount rods from the plinth up under the hips, shoulders and the tail
    for (y, z) in ((150, 160), (-40, 168), (380, 80)):
        bar(St, (0, y - ty, L.TREX_PLINTH[4]), (0, y - ty, z), 3.5, n=8)
        bar(St, (-14, y - ty, z), (14, y - ty, z), 3, n=6)
    # label card on the plinth edge
    Lb = X.mesh(S('label_card', 'lm'))
    py0 = L.TREX_PLINTH[1] - ty
    Lb.poly([(-60, py0 - 0.5, 2), (60, py0 - 0.5, 2), (60, py0 - 0.5, 14), (-60, py0 - 0.5, 14)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def whale():
    """humpback whale skeleton hanging from the skylight frame on steel cables (origin = centre at WHALE_Z, long axis x)"""
    X = Model()
    B = X.mesh(S('bone', 'lm', shade=60, tag='whale')); St = X.mesh(S('steel', 'lms', v=0.12, tag='cable'))
    pts = spline([(-430, 0, 10), (-200, 0, 30), (100, 0, 20), (300, 0, -10), (440, 0, -40)], 40)
    for k in range(len(pts) - 1):
        p, q = pts[k], pts[k + 1]
        t = k / (len(pts) - 1)
        r = 16 * (1 - t) + 4
        m = Mesh(); ellipsoid(m, (0, 0, 0), np.linalg.norm(q - p) * 0.45, r, r, nu=8, nv=5)
        B.add(m, np.eye(3), (p + q) / 2)
        if k % 2 == 0 and t < 0.75:
            bar(B, (p + q) / 2, (p + q) / 2 + [0, 0, r + 18], 2.5, n=5)
    # ribs
    for x in np.linspace(-260, 40, 12):
        for s_ in (-1, 1):
            rib = [(x, s_ * 10, 26), (x + 10, s_ * 70, 0), (x + 20, s_ * 74, -70), (x + 24, s_ * 30, -110)]
            tube(B, spline(rib, 8), 3.5, nseg=6)
    # skull + jaws (front at -x)
    m = Mesh(); ellipsoid(m, (0, 0, 0), 120, 60, 30, nu=16, nv=8)
    B.add(m, np.eye(3), (-520, 0, 10))
    for s_ in (-1, 1):
        tube(B, spline([(-420, s_ * 40, -10), (-560, s_ * 62, -30), (-660, s_ * 30, -20)], 10), [8, 7, 5], nseg=8)
        # long flippers
        tube(B, spline([(-240, s_ * 60, -20), (-200, s_ * 160, -60), (-140, s_ * 280, -90), (-90, s_ * 330, -96)], 12), [10, 8, 6, 4], nseg=8)
    # cables up to the skylight frame
    top = L.HALL_TOP - L.WHALE_Z
    for x in (-500, -100, 300):
        bar(St, (x, 0, 30), (x, 0, top), 1.5, n=4)
    return X


# ================================================================================================= ice age
def mammoth():
    """woolly mammoth (origin floor centre, faces -y): shaggy body, domed head, curled tusks, trunk"""
    X = Model()
    F = X.mesh(S('fur', 'lm', shade=80)); Iv = X.mesh(S('ivory', 'lm')); Bk = X.mesh(S('black', 'lm'))
    bump = lambda p, t: 1 + 0.05 * math.sin(7 * t + 3 * p) + 0.03 * math.sin(13 * t)
    ellipsoid(F, (0, 20, 170), 82, 150, 66, nu=20, nv=12, bump=bump)
    ellipsoid(F, (0, -70, 178), 74, 70, 56, nu=16, nv=10, bump=bump)                    # shoulder hump
    ellipsoid(F, (0, -150, 220), 52, 50, 60, nu=16, nv=10, bump=bump)                  # head
    for s_ in (-1, 1):
        for (y, x) in ((-60, 46), (110, 44)):
            tube(F, [(s_ * x, y, 150), (s_ * x, y + 4, 60), (s_ * x, y, 0)], [32, 28, 30], nseg=12)
        ellipsoid(F, (s_ * 48, -150, 216), 6, 18, 24, nu=8, nv=5)
        tube(Iv, spline([(s_ * 22, -186, 186), (s_ * 40, -240, 120), (s_ * 60, -300, 120), (s_ * 40, -330, 170), (s_ * 10, -318, 200)], 16),
             [9, 9, 8, 7, 6, 5, 4, 3, 2, 2, 2, 2, 2, 2, 2, 2, 1.5], nseg=8)
        sphere(Bk, (s_ * 26, -192, 236), 4, nu=6, nv=4)
    tube(F, spline([(0, -196, 210), (0, -230, 150), (0, -240, 80), (0, -220, 40), (0, -206, 52)], 16), [18, 16, 13, 10, 8, 7, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4], nseg=10)
    tube(F, [(0, 168, 180), (0, 190, 130)], [6, 3], nseg=6)
    return X


def moa(h=1.0):
    """moa skeleton (origin floor centre, faces -y), ~230 tall at the head"""
    X = Model()
    B = X.mesh(S('bone', 'lm', shade=60, tag='moa')); St = X.mesh(S('steel', 'lms', v=0.12, tag='moa'))
    s = h
    ellipsoid(B, (0, 10 * s, 120 * s), 22 * s, 46 * s, 22 * s, nu=10, nv=6)
    for yy in np.linspace(-20, 40, 6):
        for s_ in (-1, 1):
            tube(B, spline([(s_ * 6 * s, yy * s, 136 * s), (s_ * 26 * s, yy * s, 116 * s), (s_ * 18 * s, yy * s, 96 * s)], 6), 1.4 * s, nseg=5)
    for s_ in (-1, 1):
        bone(B, (s_ * 14 * s, 20 * s, 110 * s), (s_ * 18 * s, -6 * s, 68 * s), 4 * s)
        bone(B, (s_ * 18 * s, -6 * s, 68 * s), (s_ * 16 * s, 20 * s, 24 * s), 3.4 * s)
        bone(B, (s_ * 16 * s, 20 * s, 24 * s), (s_ * 16 * s, 8 * s, 4 * s), 2.6 * s)
        for k in (-1, 0, 1):
            tube(B, [(s_ * 16 * s, 8 * s, 4 * s), (s_ * (16 + 8 * k) * s, -14 * s, 1.5)], 2 * s, nseg=5)
    neck = spline([(0, -24 * s, 132 * s), (0, -40 * s, 170 * s), (0, -34 * s, 205 * s), (0, -46 * s, 226 * s)], 14)
    for p in neck: B.add(_ball(4.5 * s, 6), t=p)
    ellipsoid(B, (0, -58 * s, 228 * s), 6 * s, 14 * s, 6 * s, nu=8, nv=5)
    bar(St, (0, 10 * s, 0), (0, 10 * s, 112 * s), 2.5, n=6)
    revolve(X.mesh(S('granite', 'lm', tag='moa')), [(0, 0), (40 * s, 0), (40 * s, 4), (0, 4)], n=16)
    return X


def sabretooth():
    """sabre-tooth cat crouching on a rock (origin floor centre, faces -y)"""
    X = Model()
    F = X.mesh(S('fur_tan', 'lm', shade=80)); Iv = X.mesh(S('ivory', 'lm', tag='fang')); R = X.mesh(S('rock', 'lm', shade=60)); Bk = X.mesh(S('black', 'lm', tag='cat'))
    ellipsoid(R, (0, 20, 30), 80, 100, 40, nu=14, nv=8, flat_bottom=-30, bump=lambda p, t: 1 + 0.12 * math.sin(5 * t + 2 * p))
    ellipsoid(F, (0, 20, 100), 34, 70, 32, nu=16, nv=8)
    ellipsoid(F, (0, -58, 118), 26, 26, 24, nu=14, nv=8)
    for s_ in (-1, 1):
        tube(F, [(s_ * 22, -30, 96), (s_ * 24, -50, 66), (s_ * 22, -60, 62)], [11, 9, 8], nseg=8)
        tube(F, [(s_ * 22, 66, 100), (s_ * 26, 70, 70), (s_ * 22, 50, 64)], [13, 10, 8], nseg=8)
        tube(Iv, [(s_ * 8, -78, 110), (s_ * 8, -84, 82)], [3.5, 1], nseg=6)
        ellipsoid(F, (s_ * 16, -54, 140), 6, 4, 8, nu=6, nv=4)
        sphere(Bk, (s_ * 12, -80, 126), 3, nu=6, nv=4)
    tube(F, [(0, 88, 100), (0, 110, 96)], [6, 4], nseg=6)
    return X


def eagle():
    """Haast's eagle in flight, hanging from the ceiling (origin = the ceiling hook, model hangs down ~260)"""
    X = Model()
    F = X.mesh(S('feather', 'lm', shade=80, two=True)); Y = X.mesh(S('gold', 'lm', tag='beak')); St = X.mesh(S('steel', 'lms', v=0.12, tag='eagle'))
    c = np.array([0, 0, -260.0])
    ellipsoid(F, c, 18, 50, 16, nu=12, nv=6)
    sphere(F, c + [0, -50, 6], 12, nu=10, nv=6)
    m = Mesh(); revolve(m, [(0.1, 0), (5, 2), (0, 16)], n=8)
    Y.add(m, np.array([[1, 0, 0], [0, 0, -1.0], [0, 1, 0]]), c + [0, -60, 6])
    for s_ in (-1, 1):
        wing = [c + [s_ * 14, -18, 4], c + [s_ * 100, -30, 22], c + [s_ * 190, -10, 30], c + [s_ * 196, 22, 26], c + [s_ * 90, 30, 10], c + [s_ * 14, 20, 0]]
        F.poly(wing, (0, 0, 1), [(0, 0), (0.5, 0), (1, 0), (1, 1), (0.5, 1), (0, 1)])
        tube(Y, [c + [s_ * 8, 30, -10], c + [s_ * 10, 26, -40]], [3, 2], nseg=5)
        bar(St, c + [s_ * 120, -10, 26], (s_ * 120, -10, 0), 0.8, n=4)
    F.poly([c + [-14, 44, 0], c + [14, 44, 0], c + [26, 96, 0], c + [-26, 96, 0]], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    return X


def diorama_rocks(w=600, d=200, seed=3):
    """snowy rock bank for the back of a diorama (origin floor centre, faces -y)"""
    X = Model()
    R = X.mesh(S('rock', 'lm', shade=60, tag='dio')); Sn = X.mesh(S('snow_m', 'lm', tag='dio'))
    rng = np.random.default_rng(seed)
    for k in range(9):
        x = -w / 2 + w * (k + 0.5) / 9; s = rng.uniform(50, 90)
        ellipsoid(R, (x, rng.uniform(-d * 0.2, d * 0.3), s * 0.6), s, s * 0.8, s * 0.9, nu=10, nv=6, flat_bottom=-s * 0.6,
                  bump=lambda p, t: 1 + 0.15 * math.sin(4 * t + 3 * p))
        ellipsoid(Sn, (x, rng.uniform(-d * 0.2, d * 0.3), s * 1.25), s * 0.7, s * 0.6, s * 0.25, nu=10, nv=5)
    return X


# ================================================================================================= egypt
def pharaoh():
    """seated colossus of a pharaoh (origin floor centre, faces +x), 320 tall incl. the base"""
    X = Model()
    G = X.mesh(S('sandstone_m', 'lm', shade=50)); N = X.mesh(S('nemes', 'lm')); Gd = X.mesh(S('gold', 'lms', v=0.2, tag='ph'))
    rbox(G, (-70, -60, 0), (70, 60, 40), r=3, k=2, tile=128)                   # base
    rbox(G, (-64, -52, 40), (10, 52, 150), r=4, k=2, tile=128)                 # throne block
    rbox(G, (-64, -52, 150), (-40, 52, 220), r=4, k=2, tile=128)               # throne back
    ellipsoid(G, (-24, 0, 200), 26, 38, 54, nu=14, nv=8)                       # torso
    for s_ in (-1, 1):
        rbox(G, (-30, s_ * 22 - 14, 140), (54, s_ * 22 + 14, 160), r=6, k=2, tile=64)   # thighs
        rbox(G, (40, s_ * 22 - 13, 40), (60, s_ * 22 + 13, 150), r=6, k=2, tile=64)     # shins
        rbox(G, (40, s_ * 22 - 14, 40), (80, s_ * 22 + 14, 54), r=5, k=2, tile=64)      # feet
        tube(G, [(-20, s_ * 40, 238), (0, s_ * 44, 196), (36, s_ * 26, 166)], [11, 10, 9], nseg=8)   # arms on the knees
    ellipsoid(G, (-16, 0, 278), 22, 20, 26, nu=12, nv=8)                       # head
    revolve(N, [(0.1, 304), (28, 302), (34, 280), (40, 240), (34, 226)], n=12, cx=-24, a0=95, a1=265)
    for s_ in (-1, 1):
        tube(N, [(-14, s_ * 30, 290), (-6, s_ * 34, 262), (2, s_ * 30, 226)], [10, 12, 12], nseg=8)          # lappets        # nemes headcloth
    tube(Gd, [(6, 0, 262), (12, 0, 240)], [4, 3], nseg=6)                       # false beard
    revolve(Gd, [(0, 296), (6, 300), (2, 318), (0, 320)], n=8, cx=-6)           # uraeus
    return X


def anubis():
    """Anubis jackal statue lying on a shrine chest (origin floor centre, faces +x)"""
    X = Model()
    Bk = X.mesh(S('black', 'lms', v=0.25, tag='anubis')); Gd = X.mesh(S('gold', 'lms', v=0.2, tag='an')); W = X.mesh(S('wood_dark', 'lm'))
    rbox(W, (-110, -50, 0), (110, 50, 120), r=3, k=2, tile=128)
    rbox(Gd, (-114, -54, 110), (114, 54, 124), r=2, k=1, tile=64)
    ellipsoid(Bk, (-10, 0, 156), 70, 30, 30, nu=14, nv=8)
    ellipsoid(Bk, (60, 0, 196), 18, 18, 24, nu=10, nv=6)
    tube(Bk, [(64, 0, 196), (100, 0, 190)], [12, 6], nseg=8)
    for s_ in (-1, 1):
        m = Mesh(); revolve(m, [(7, 0), (0.1, 32)], n=6)
        Bk.add(m, np.eye(3), (54, s_ * 10, 212))
        tube(Bk, [(50, s_ * 16, 140), (96, s_ * 16, 128)], [8, 7], nseg=6)
    tube(Gd, arc_path((40, 0, 176), 22, 0, 360, n=17, axis='x'), 3, nseg=5, caps=(False, False))
    return X


def obelisk(h=560):
    X = Model()
    G = X.mesh(S('red_granite', 'lm', shade=30)); Gd = X.mesh(S('gold', 'lms', v=0.2, tag='ob'))
    rbox(G, (-60, -60, 0), (60, 60, 40), r=3, k=2, tile=128)
    m = Mesh()
    pts = [(-36, -36), (36, -36), (36, 36), (-36, 36)]
    top = [(-24, -24), (24, -24), (24, 24), (-24, 24)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]; c, d = top[(i + 1) % 4], top[i]
        G.poly([np.array([*a, 40.0]), np.array([*b, 40.0]), np.array([*c, h - 40.0]), np.array([*d, h - 40.0])],
               np.array([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 2.0]), [(0, 0), (1, 0), (1, 6), (0, 6)])
        Gd.poly([np.array([*d, h - 40.0]), np.array([*c, h - 40.0]), np.array([0, 0, float(h)])], np.array([(c[0] + d[0]) / 2, (c[1] + d[1]) / 2, 20.0]),
                [(0, 0), (1, 0), (0.5, 1)])
    return X


def sarcophagus(open_=False):
    """gilded anthropoid coffin on a stone bier (origin floor centre, long axis x, head at +x). open_: the lid leans
    against the bier and the inside glows (the SECRET)"""
    X = Model()
    St = X.mesh(S('granite', 'lm', shade=40)); Gd = X.mesh(S('gold', 'lms', v=0.2, tag='sarc')); Fc = X.mesh(S('sarc_face', 'lm', shade=60))
    rbox(St, (-130, -56, 0), (130, 56, 40), r=3, k=2, tile=128)
    body = Mesh()
    revolve(body, [(0.1, -100), (26, -96), (34, -40), (40, 30), (38, 70), (30, 100), (0.1, 108)], n=16,
            rfun=lambda a, r, z: r * (0.6 if abs(math.sin(a)) < 0.5 else 1.0))
    Rx = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])           # lathe axis z -> +x
    if not open_:
        Fc.add(body, Rx, (0, 0, 76))
        ellipsoid(Gd, (96, 0, 104), 18, 22, 22, nu=12, nv=8)
    else:
        # open box: walls + glowing inside; the lid stands against the bier
        Gw = X.mesh(S('glow_sarc', 'glow'))
        rbox(Gd, (-110, -44, 40), (110, -36, 100), r=2, k=1, tile=64); rbox(Gd, (-110, 36, 40), (110, 44, 100), r=2, k=1, tile=64)
        rbox(Gd, (-110, -44, 40), (-102, 44, 100), r=2, k=1, tile=64); rbox(Gd, (102, -44, 40), (110, 44, 100), r=2, k=1, tile=64)
        Gw.poly([(-102, -36, 44), (102, -36, 44), (102, 36, 44), (-102, 36, 44)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
        lid = Mesh(); lid.add(body)
        Fc.add(lid, rot_axis((0, 1, 0), math.radians(-70)) @ Rx, (-150, 0, 120))
    return X


def canopic_jars():
    X = Model()
    A_ = X.mesh(S('stone_w', 'lm', tag='jar')); Gd = X.mesh(S('gold', 'lms', v=0.2, tag='jar'))
    for k in range(4):
        x = -45 + k * 30
        revolve(A_, [(0, 0), (10, 0), (13, 18), (12, 36), (8, 42), (0, 42)], n=12, cx=x)
        ellipsoid(Gd, (x, 0, 48), 8, 8, 9, nu=8, nv=5)
    return X


def lotus_column(h=560):
    X = Model()
    S_ = X.mesh(S('sandstone_m', 'lm', shade=40, tag='col')); P = X.mesh(S('lapis', 'lm', tag='col'))
    revolve(S_, [(0, 0), (52, 0), (52, 20), (40, 28), (36, h - 120), (40, h - 110)], n=16, rfun=lambda a, r, z: r * (1 + 0.04 * math.cos(a * 8)))
    revolve(P, [(40, h - 110), (60, h - 70), (64, h - 40), (56, h - 32)], n=16, rfun=lambda a, r, z: r * (1 + 0.1 * abs(math.cos(a * 4))))
    revolve(S_, [(56, h - 32), (60, h - 30), (60, h), (0, h)], n=4, a0=45, a1=405)
    return X


def mummy_case():
    """upright glass case with a mummy (origin floor centre, faces +x)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lm', tag='case')); Gl = X.mesh(S('glass_t', 'glass', tag='case')); Ln = X.mesh(S('stone_w', 'lm', tag='mummy'))
    rbox(W, (-50, -50, 0), (50, 50, 30), r=2, k=1, tile=64)
    rbox(W, (-50, -50, 230), (50, 50, 250), r=2, k=1, tile=64)
    for (x, y) in ((-48, -48), (-48, 48), (48, -48), (48, 48)):
        rbox(W, (x - 3, y - 3, 30), (x + 3, y + 3, 230), r=1, k=1, tile=64)
    for (a, b, n) in (((48, -48), (48, 48), (1, 0, 0)), ((-48, -48), (-48, 48), (-1, 0, 0)), ((-48, 48), (48, 48), (0, 1, 0)), ((-48, -48), (48, -48), (0, -1, 0))):
        Gl.poly([np.array([*a, 30.0]), np.array([*b, 30.0]), np.array([*b, 230.0]), np.array([*a, 230.0])], n, [(0, 1), (1, 1), (1, 0), (0, 0)])
    m = Mesh(); revolve(m, [(0.1, 30), (14, 34), (20, 90), (24, 150), (16, 190), (18, 205), (12, 222), (0.1, 226)], n=14,
                        rfun=lambda a, r, z: r * (1 + 0.05 * math.sin(z / 4)))
    Ln.add(m)
    return X


def pyramid_cap():
    """gold capstone + the stair's carved edging for the step pyramid's top (origin floor centre of the top platform)"""
    X = Model()
    Gd = X.mesh(S('gold', 'lms', v=0.25, tag='cap'))
    h = 70
    pts = [(-48, -48), (48, -48), (48, 48), (-48, 48)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        Gd.poly([np.array([*a, 0.0]), np.array([*b, 0.0]), np.array([0, 0, float(h)])], np.array([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 30.0]), [(0, 0), (1, 0), (0.5, 1)])
    return X


def treasure_pile(seed=1, r=110):
    X = Model()
    Gd = X.mesh(S('gold', 'lms', v=0.3, tag='coins')); Lp = X.mesh(S('lapis', 'lm', tag='gem')); W = X.mesh(S('wood_dark', 'lm', tag='chest'))
    rng = np.random.default_rng(seed)
    revolve(Gd, [(0, 0), (r, 0), (r * 0.6, r * 0.35), (0, r * 0.5)], n=24, rfun=lambda a, rr, z: rr * (1 + 0.1 * math.sin(5 * a)))
    for k in range(30):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, r * 0.9)
        m = Mesh(); revolve(m, [(0, 0), (6, 0), (6, 1.5), (0, 1.5)], n=8)
        Gd.add(m, rot_axis((1, 0, 0), rng.uniform(-0.6, 0.6)), (rr * math.cos(a), rr * math.sin(a), max(1.0, r * 0.5 * (1 - rr / r)) + 1))
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, r * 0.6)
        sphere(Lp, (rr * math.cos(a), rr * math.sin(a), r * 0.5 * (1 - rr / r) + 5), 6, nu=8, nv=5)
    rbox(W, (r * 0.6, -40, 0), (r * 0.6 + 90, 40, 60), r=3, k=2, tile=64)
    rbox(Gd, (r * 0.6 - 2, -42, 50), (r * 0.6 + 92, 42, 66), r=3, k=2, tile=64)
    return X


def death_mask():
    """golden death mask on a pedestal (origin floor centre, faces +x)"""
    X = Model()
    N = X.mesh(S('nemes', 'lm', tag='mask')); Gd = X.mesh(S('gold', 'lms', v=0.3, tag='mask')); P = X.mesh(S('black', 'lms', v=0.2, tag='ped'))
    rbox(P, (-40, -40, 0), (40, 40, 110), r=3, k=2, tile=64)
    ellipsoid(Gd, (6, 0, 150), 22, 22, 30, nu=14, nv=8)
    revolve(N, [(0.1, 186), (26, 184), (32, 160), (38, 122), (32, 110)], n=12, cx=-8, a0=95, a1=265)
    for s_ in (-1, 1):
        tube(N, [(0, s_ * 26, 176), (8, s_ * 30, 146), (14, s_ * 26, 112)], [8, 10, 10], nseg=8)
    tube(Gd, [(26, 0, 132), (30, 0, 114)], [4, 3], nseg=6)
    return X


# ================================================================================================= planetarium
def dome():
    """planetarium dome over the roof: copper ribs + panels outside, the starfield inside, a lantern on top (origin =
    DOME centre at the roof level)"""
    X = Model()
    Cu = X.mesh(S('copper', 'lm', shade=40)); Sf = X.mesh(S(f'{TD}/starfield', 'glow', tag='dome')); Tr = X.mesh(S('stone_w', 'lm', tag='dome'))
    R, H = L.DOME_R, L.DOME_H
    hs = [H * math.sin(a) for a in np.linspace(0, math.pi / 2, 14)]
    prof = [(L.dome_r(h), h) for h in hs]
    revolve(Cu, prof, n=48, u_tiles=8, vlen=256)
    disc(Cu, L.DOME_TOP_R, H, n=24)
    inner = [(max(1.0, L.dome_r(h) - 18), h - 18) for h in hs[::-1]]
    revolve(Sf, [(0.1, H - 18)] + inner, n=48, inward=True, u_tiles=1, vlen=900)
    for k in range(16):
        a = 2 * math.pi * k / 16
        pts = [(math.cos(a) * (r + 3), math.sin(a) * (r + 3), z + 3) for (r, z) in prof]
        tube(Tr, pts, 5, nseg=6, caps=(False, False))
    revolve(Tr, [(R + 30, -16), (R + 30, 10), (R + 6, 14), (R + 2, 0)], n=48)
    # lantern platform rail posts (low, shootable over)
    revolve(Tr, [(L.DOME_TOP_R, H), (L.DOME_TOP_R + 6, H + 6), (L.DOME_TOP_R + 6, H + 14), (L.DOME_TOP_R - 2, H + 14)], n=24)
    return X


def projector():
    """dumbbell star projector on a pedestal (origin floor centre), ~220 tall"""
    X = Model()
    Bk = X.mesh(S('black', 'lms', v=0.3, tag='proj')); Ln = X.mesh(S('lens', 'glow')); St = X.mesh(S('steel', 'lms', v=0.15, tag='proj'))
    revolve(St, [(0, 0), (60, 0), (60, 10), (30, 20), (24, 90), (40, 100), (0, 100)], n=24)
    Ra = rot_axis((1, 0, 0), math.radians(30))
    tube(Bk, [Ra @ np.array([0, -90, 0]) + [0, 0, 150], Ra @ np.array([0, 90, 0]) + [0, 0, 150]], 14, nseg=12)
    for s_ in (-1, 1):
        c = Ra @ np.array([0, s_ * 100, 0]) + [0, 0, 150]
        sphere(Bk, c, 44, nu=20, nv=12)
        for k in range(14):
            a = k * 2 * math.pi / 14; b = 0.6 + (k % 2) * 0.5
            d = Ra @ np.array([math.cos(a) * math.sin(b), s_ * math.cos(b), math.sin(a) * math.sin(b)])
            sphere(Ln, c + d * 44, 6, nu=6, nv=4)
    bar(St, (0, 0, 100), (0, 0, 150), 10, n=10)
    return X


def seat_ring(r=320, n=12, a0=20, a1=340):
    """ring of reclining planetarium seats facing the centre (origin = the ring centre on the floor)"""
    X = Model()
    C_ = X.mesh(S('cushion_blue', 'lm', shade=70)); St = X.mesh(S('steel', 'lms', v=0.12, tag='seat'))
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * k / max(1, n - 1))
        c = np.array([r * math.cos(a), r * math.sin(a), 0])
        Rz = rot_z(a + math.pi)                       # seat faces the centre (+x local -> inward)
        m = Mesh()
        rbox(m, (-22, -24, 24), (22, 24, 34), r=4, k=2, tile=64)
        rbox(m, (-36, -24, 34), (-24, 24, 84), r=4, k=2, tile=64)
        C_.add(m, Rz @ rot_axis((0, 1, 0), math.radians(-18)), c + [0, 0, 6])
        s = Mesh(); bar(s, (0, 0, 0), (0, 0, 28), 4, n=6)
        St.add(s, np.eye(3), c)
    return X


def orrery():
    """orrery hanging in the dome (IQM mover, origin = pivot on the hub): a glowing sun and planets on arms"""
    X = Model()
    Su = X.mesh(S('sun', 'glow', tag='orr')); Br = X.mesh(S('brass', 'dynenv'))
    sphere(Su, (0, 0, 0), 40, nu=20, nv=12)
    bar(Br, (0, 0, 40), (0, 0, L.ROOF + L.DOME_H - 18 - L.ORRERY_Z), 4, n=6)
    rad = [75, 110, 150, 195, 250, 300, 345, 390]
    size = [8, 12, 13, 10, 28, 24, 16, 15]
    for k, (R, s) in enumerate(zip(rad, size)):
        a = k * 2.4
        p = np.array([R * math.cos(a), R * math.sin(a), -20 - k * 6])
        bar(Br, (0, 0, -10 - k * 4), (p[0], p[1], -10 - k * 4), 1.8, n=5)
        bar(Br, (p[0], p[1], -10 - k * 4), p, 1.4, n=4)
        sphere(X.mesh(S(f'planet_{k}', 'dyn')), p, s, nu=14, nv=8)
        if k == 5:
            tube(X.mesh(S('planet_5', 'dyn', tag='ring', two=True)), arc_path(p, s * 1.8, 0, 360, n=25), [3], nseg=4, ry=0.5, caps=(False, False))
    return X


def meteorite():
    X = Model()
    P = X.mesh(S('black', 'lms', v=0.2, tag='ped'))
    rbox(P, (-50, -50, 0), (50, 50, 90), r=3, k=2, tile=64)
    ellipsoid(X.mesh(S('meteorite', 'lms', v=0.15)), (0, 0, 130), 40, 34, 40, nu=14, nv=8, flat_bottom=-38,
              bump=lambda p, t: 1 + 0.15 * math.sin(5 * t + 4 * p) + 0.08 * math.sin(11 * t))
    return X


# ================================================================================================= gems
def geode():
    """walk-in geode: rough grey shell outside, glowing amethyst crystals inside, opening to the north (origin floor
    centre)"""
    X = Model()
    O = X.mesh(S('geode_out', 'lm', shade=70)); Cp = X.mesh(S('crystal_p', 'glow', tag='geo')); Cc = X.mesh(S('crystal_c', 'glow', tag='geo'))
    R, H = L.GEODE_R, L.GEODE_H
    da = L.GEODE_DOOR
    def gap(a):
        return abs(((math.degrees(a) - da + 180) % 360) - 180) < 18
    prof = [(L.geode_r(h), h) for h in [H * math.sin(t) for t in np.linspace(0, math.pi / 2, 10)]] + [(0.1, H)]
    n = 48
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        if gap((a0 + a1) / 2): continue
        revolve(O, prof, n=1, a0=math.degrees(a0), a1=math.degrees(a1), rfun=lambda a, r, z: r * (1 + 0.04 * math.sin(7 * a + z / 30)))
    In = X.mesh(S('geode_in', 'lm', shade=70))
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        if gap((a0 + a1) / 2): continue
        revolve(In, [(L.geode_r(z) * 0.93 - 18, z) for z in np.linspace(0, H - 20, 10)] + [(0.1, H - 20)], n=1,
                a0=math.degrees(a0), a1=math.degrees(a1), inward=True)
    rng = np.random.default_rng(7)
    for k in range(160):
        a = rng.uniform(0, 2 * math.pi)
        if gap(a): continue
        t = rng.uniform(0.05, 1.45)
        z = (H - 30) * math.sin(t) * 0.98; r = L.geode_r(z) * 0.93 - 18
        base = np.array([r * math.cos(a), r * math.sin(a), z])
        d = -base / max(1, np.linalg.norm(base)); d[2] -= 0.2; d /= np.linalg.norm(d)
        L_ = rng.uniform(18, 40); w = rng.uniform(5, 9)
        m = Mesh()
        poly = [(math.cos(j * math.pi / 3) * w, math.sin(j * math.pi / 3) * w) for j in range(6)]
        prism(m, poly, 0, L_ * 0.7, tile=64)
        for j in range(6):
            p0 = np.array([*poly[j], L_ * 0.7]); p1 = np.array([*poly[(j + 1) % 6], L_ * 0.7])
            m.poly([p0, p1, np.array([0, 0, L_])], np.array([p0[0] + p1[0], p0[1] + p1[1], 8]), [(0, 0), (1, 0), (0.5, 1)])
        Rm = np.stack([np.cross(d, [0, 0, 1]) if abs(d[2]) < 0.95 else np.array([1, 0, 0]), np.zeros(3), d], 1)
        Rm[:, 0] /= np.linalg.norm(Rm[:, 0]); Rm[:, 1] = np.cross(d, Rm[:, 0])
        (Cp if k % 7 else Cc).add(m, Rm, base)
    return X


def crystal_cluster(col='crystal_p', n=9, s=1.0, seed=3):
    X = Model()
    Cm = X.mesh(S(col, 'glow', tag='clu')); R = X.mesh(S('rock', 'lm', tag='clu'))
    ellipsoid(R, (0, 0, 0), 40 * s, 34 * s, 22 * s, nu=10, nv=6, flat_bottom=0)
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi); lean = rng.uniform(0, 0.6)
        d = np.array([math.cos(a) * math.sin(lean), math.sin(a) * math.sin(lean), math.cos(lean)])
        L_ = rng.uniform(30, 70) * s; w = rng.uniform(5, 10) * s
        m = Mesh()
        poly = [(math.cos(j * math.pi / 3) * w, math.sin(j * math.pi / 3) * w) for j in range(6)]
        prism(m, poly, 0, L_ * 0.75, tile=64)
        for j in range(6):
            p0 = np.array([*poly[j], L_ * 0.75]); p1 = np.array([*poly[(j + 1) % 6], L_ * 0.75])
            m.poly([p0, p1, np.array([0, 0, L_])], np.array([p0[0] + p1[0], p0[1] + p1[1], 8]), [(0, 0), (1, 0), (0.5, 1)])
        side = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.99 else np.array([1.0, 0, 0])
        side /= np.linalg.norm(side)
        Rm = np.stack([side, np.cross(d, side), d], 1)
        Cm.add(m, Rm, (math.cos(a) * 12 * s, math.sin(a) * 12 * s, 12 * s))
    return X


def display_case(obj='skull', w=120, d=80, h=110):
    """museum vitrine: timber plinth, glass box, brass trim and an exhibit inside (origin floor centre)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lm', tag='vit')); Gl = X.mesh(S('glass_t', 'glass', tag='vit')); Br = X.mesh(S('brass', 'lms', v=0.15, tag='vit'))
    F = X.mesh(S('felt_green', 'lm', tag='vit'))
    hw, hd = w / 2, d / 2
    rbox(W, (-hd, -hw, 0), (hd, hw, h), r=3, k=2, tile=128)
    F.poly([(-hd + 6, -hw + 6, h + 0.5), (hd - 6, -hw + 6, h + 0.5), (hd - 6, hw - 6, h + 0.5), (-hd + 6, hw - 6, h + 0.5)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    top = h + 90
    for (a, b, n) in (((hd, -hw), (hd, hw), (1, 0, 0)), ((-hd, -hw), (-hd, hw), (-1, 0, 0)), ((-hd, hw), (hd, hw), (0, 1, 0)), ((-hd, -hw), (hd, -hw), (0, -1, 0))):
        Gl.poly([np.array([*a, float(h)]), np.array([*b, float(h)]), np.array([*b, float(top)]), np.array([*a, float(top)])], n, [(0, 1), (1, 1), (1, 0), (0, 0)])
    Gl.poly([(-hd, -hw, top), (hd, -hw, top), (hd, hw, top), (-hd, hw, top)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for (x, y) in ((-hd, -hw), (-hd, hw), (hd, -hw), (hd, hw)):
        bar(Br, (x, y, h), (x, y, top), 1.6, n=5)
    for z in (h, top):
        for (a, b) in (((-hd, -hw), (hd, -hw)), ((hd, -hw), (hd, hw)), ((hd, hw), (-hd, hw)), ((-hd, hw), (-hd, -hw))):
            bar(Br, (*a, z), (*b, z), 1.6, n=5)
    z0 = h + 1
    if obj == 'skull':
        Bn = X.mesh(S('bone', 'lm', tag='ex'))
        ellipsoid(Bn, (0, 0, z0 + 22), 18, 34, 20, nu=12, nv=8, flat_bottom=-20)
        for s_ in (-1, 1): sphere(X.mesh(S('black', 'lm', tag='ex')), (s_ * 10, -16, z0 + 30), 5, nu=6, nv=4)
    elif obj == 'ammonite':
        A_ = X.mesh(S('ammonite', 'lms', v=0.1, tag='ex'))
        pts = [(0, 30 * math.exp(-0.18 * t) * math.cos(t), z0 + 34 + 30 * math.exp(-0.18 * t) * math.sin(t)) for t in np.linspace(0, 4 * math.pi, 50)]
        tube(A_, pts, [max(1.0, 11 * math.exp(-0.18 * t)) for t in np.linspace(0, 4 * math.pi, 50)], nseg=8)
    elif obj == 'trilobite':
        Bn = X.mesh(S('slate', 'lm', tag='ex'))
        rbox(Bn, (-30, -40, z0), (30, 40, z0 + 8), r=3, k=2, tile=64)
        ellipsoid(X.mesh(S('bone_dark', 'lm', tag='ex')), (0, 0, z0 + 10), 18, 28, 5, nu=12, nv=6)
    elif obj == 'crystal':
        X.add_model(crystal_cluster('crystal_b', 6, 0.6, 9), t=(0, 0, z0))
    elif obj == 'scarab':
        Gd = X.mesh(S('lapis', 'lms', v=0.2, tag='ex'))
        ellipsoid(Gd, (0, 0, z0 + 8), 16, 22, 9, nu=12, nv=6, flat_bottom=-8)
    elif obj == 'egg':
        ellipsoid(X.mesh(S('ivory', 'lm', tag='egg')), (0, 0, z0 + 30), 22, 22, 30, nu=14, nv=8)
    return X


# ================================================================================================= ocean
def squid_tank():
    """tall glass tank with a giant squid (origin floor centre); the water inside is a glowing translucent volume"""
    X = Model()
    W = X.mesh(S('steel', 'lms', v=0.15, tag='tank')); Gl = X.mesh(S('glass_t', 'glass', tag='tank')); Wt = X.mesh(S('water_t', 'add', tag='tank'))
    Sq = X.mesh(S('squid', 'lm', shade=70)); Sd = X.mesh(S('sand', 'lm', tag='tank'))
    _, _, hx, hy, H = L.TANK
    rbox(W, (-hx, -hy, 0), (hx, hy, 40), r=3, k=2, tile=128)
    rbox(W, (-hx, -hy, H - 30), (hx, hy, H), r=3, k=2, tile=128)
    for (x, y) in ((-hx, -hy), (-hx, hy), (hx, -hy), (hx, hy)):
        rbox(W, (x - 6, y - 6, 40), (x + 6, y + 6, H - 30), r=2, k=1, tile=64)
    for (a, b, n) in (((hx, -hy), (hx, hy), (1, 0, 0)), ((-hx, -hy), (-hx, hy), (-1, 0, 0)), ((-hx, hy), (hx, hy), (0, 1, 0)), ((-hx, -hy), (hx, -hy), (0, -1, 0))):
        Gl.poly([np.array([*a, 40.0]), np.array([*b, 40.0]), np.array([*b, H - 30.0]), np.array([*a, H - 30.0])], n, [(0, 1), (1, 1), (1, 0), (0, 0)])
        Wt.poly([np.array([a[0] * 0.98, a[1] * 0.98, 42.0]), np.array([b[0] * 0.98, b[1] * 0.98, 42.0]), np.array([b[0] * 0.98, b[1] * 0.98, H - 40.0]),
                 np.array([a[0] * 0.98, a[1] * 0.98, H - 40.0])], n, [(0, 1), (1, 1), (1, 0), (0, 0)])
    Sd.poly([(-hx + 6, -hy + 6, 41), (hx - 6, -hy + 6, 41), (hx - 6, hy - 6, 41), (-hx + 6, hy - 6, 41)], (0, 0, 1), [(0, 0), (2, 0), (2, 2), (0, 2)])
    # the squid: mantle pointing up, eight arms and two long tentacles curling down
    c = np.array([0, 0, 300.0])
    ellipsoid(Sq, c + [0, 0, 90], 34, 34, 110, nu=16, nv=10)
    sphere(X.mesh(S('black', 'lm', tag='sq')), c + [30, 0, 10], 9, nu=8, nv=5)
    rng = np.random.default_rng(3)
    for k in range(10):
        a = k * 2 * math.pi / 10
        Lr = 1.0 if k < 8 else 1.6
        pts = [c + [math.cos(a) * 20, math.sin(a) * 20, -10]]
        for j in range(1, 8):
            t = j / 7
            pts.append(c + [math.cos(a) * (20 + 110 * t * Lr) + 30 * math.sin(t * 6 + k), math.sin(a) * (20 + 80 * t * Lr), -10 - 210 * t * Lr * 0.9])
        pts = [np.array([np.clip(p[0], -hx + 20, hx - 20), np.clip(p[1], -hy + 20, hy - 20), max(p[2], 60)]) for p in pts]
        tube(Sq, pts, [9 * (1 - j / 8) + 1.5 for j in range(len(pts))], nseg=8)
    return X


def shark(L_=360):
    """shark model hanging from the ceiling (origin = the ceiling hook)"""
    X = Model()
    Sh = X.mesh(S('shark', 'lm', shade=70)); St = X.mesh(S('steel', 'lms', v=0.12, tag='shark'))
    c = np.array([0, 0, -200.0])
    ellipsoid(Sh, c, L_ / 2, 34, 40, nu=20, nv=10)
    Sh.poly([c + [-10, 0, 36], c + [40, 0, 36], c + [-30, 0, 100]], (0, -1, 0), [(0, 0), (1, 0), (0, 1)])
    Sh.poly([c + [L_ / 2 - 20, 0, 0], c + [L_ / 2 + 70, 0, 70], c + [L_ / 2 + 50, 0, -50]], (0, -1, 0), [(0, 0), (1, 0), (0, 1)])
    for s_ in (-1, 1):
        Sh.poly([c + [-60, s_ * 26, -14], c + [0, s_ * 26, -14], c + [10, s_ * 110, -40]], (0, 0, -1), [(0, 0), (1, 0), (0, 1)])
        sphere(X.mesh(S('black', 'lm', tag='sh')), c + [-L_ / 2 + 40, s_ * 22, 10], 4, nu=6, nv=4)
    for x in (-100, 100):
        bar(St, c + [x, 0, 38], (x, 0, 0), 1, n=4)
    return X


def coral_case():
    X = display_case('none', 200, 100, 80)
    Co = X.mesh(S('coral', 'lm', tag='cor')); Cy = X.mesh(S('coral_y', 'lm', tag='cor'))
    rng = np.random.default_rng(5)
    for k in range(9):
        x = rng.uniform(-30, 30); y = rng.uniform(-80, 80)
        M_ = Co if k % 2 else Cy
        for j in range(4):
            a = rng.uniform(0, 2 * math.pi)
            tube(M_, [(x, y, 81), (x + math.cos(a) * 12, y + math.sin(a) * 12, 110), (x + math.cos(a) * 18, y + math.sin(a) * 18, 140)], [5, 3.5, 2], nseg=6)
    return X


# ================================================================================================= foyer + security + general
def classical_column(h=640, r=40):
    X = Model()
    S_ = X.mesh(S('stone_w', 'lm', shade=40, tag='colm'))
    revolve(S_, [(0, 0), (r + 16, 0), (r + 16, 24), (r + 8, 32), (r, 44), (r * 0.86, h - 60), (r * 0.9, h - 50), (r + 10, h - 30)], n=24,
            rfun=lambda a, rr, z: rr * (1 - 0.05 * abs(math.cos(a * 12)) if 44 < z < h - 60 else 1.0))
    rbox(S_, (-r - 20, -r - 20, h - 30), (r + 20, r + 20, h), r=3, k=2, tile=128)
    return X


def ticket_desk():
    """curved reception desk (origin floor centre, staff side +y)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lms', v=0.08, tag='desk')); M_ = X.mesh(S('stone_w', 'lm', tag='desktop')); Sg = X.mesh(S('sign_tickets', 'glow'))
    revolve(W, [(300, 0), (300, 110), (260, 110), (260, 0)], n=16, a0=200, a1=340, cy=200)
    revolve(M_, [(306, 110), (306, 120), (254, 120), (254, 110)], n=16, a0=200, a1=340, cy=200)
    Sg.poly([(-60, -101, 60), (60, -101, 60), (60, -101, 90), (-60, -101, 90)], (0, -1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def stanchions(n=4, gap=120):
    X = Model()
    Br = X.mesh(S('brass', 'lms', v=0.2, tag='st')); Rp = X.mesh(S('rope_red', 'lm'))
    for k in range(n):
        x = -gap * (n - 1) / 2 + k * gap
        revolve(Br, [(0, 0), (20, 0), (20, 4), (6, 8), (4, 60), (8, 64), (0, 70)], n=12, cx=x)
        if k < n - 1:
            tube(Rp, [(x + 4, 0, 62), (x + gap / 2, 0, 46), (x + gap - 4, 0, 62)], 3, nseg=6)
    return X


def bench(L_=260):
    X = Model()
    W = X.mesh(S('wood', 'lm', tag='bench')); St = X.mesh(S('steel', 'lms', v=0.12, tag='bench'))
    rbox(W, (-L_ / 2, -36, 30), (L_ / 2, 36, 40), r=3, k=2, tile=128)
    for x in (-L_ / 2 + 20, L_ / 2 - 20):
        rbox(St, (x - 4, -32, 0), (x + 4, 32, 30), r=1, k=1, tile=64)
    return X


def gift_shelf(seed=1):
    """gift-shop shelving with plush dinosaurs, books and snow globes (origin floor centre, faces +x)"""
    X = Model()
    W = X.mesh(S('wood', 'lm', tag='gift'))
    rng = np.random.default_rng(seed)
    rbox(W, (-30, -120, 0), (-24, 120, 200), r=1, k=1, tile=128)
    for z in (10, 70, 130, 190):
        rbox(W, (-30, -120, z - 4), (30, 120, z), r=1, k=1, tile=128)
    for y in (-120, 116):
        rbox(W, (-30, y, 0), (30, y + 4, 200), r=1, k=1, tile=128)
    for z in (10, 70, 130):
        for k in range(4):
            y = -90 + k * 60
            col = ['plush_g', 'plush_o', 'plush_p'][rng.integers(3)]
            P = X.mesh(S(col, 'lm', tag='plush'))
            ellipsoid(P, (0, y, z + 14), 14, 18, 14, nu=10, nv=6)
            tube(P, [(0, y - 14, z + 20), (6, y - 26, z + 38)], [7, 5], nseg=6)
            sphere(P, (8, y - 30, z + 42), 7, nu=8, nv=5)
            tube(P, [(0, y + 16, z + 10), (0, y + 30, z + 4)], [6, 2], nseg=6)
    return X


def security_desk():
    """L-shaped security desk with CCTV monitors, a mug and a torch (origin floor centre, guard side -x)"""
    X = Model()
    W = X.mesh(S('wood_dark', 'lm', tag='sec')); Bk = X.mesh(S('black', 'lms', v=0.15, tag='mon')); Mn = X.mesh(S('monitor', 'glow'))
    rbox(W, (-40, -150, 0), (40, 150, 76), r=2, k=1, tile=128)
    for y in (-90, 0, 90):
        rbox(Bk, (10, y - 40, 76), (40, y + 40, 136), r=2, k=1, tile=64)
        Mn.poly([(9.5, y + 36, 80), (9.5, y - 36, 80), (9.5, y - 36, 132), (9.5, y + 36, 132)], (-1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    revolve(X.mesh(S('velvet', 'lm', tag='mug')), [(0, 76), (7, 76), (7, 90), (0, 90)], n=10, cx=-20, cy=120)
    tube(X.mesh(S('black', 'lm', tag='torch')), [(-20, -120, 80), (-20, -90, 80)], 4, nseg=6)
    return X


def lockers(n=4):
    X = Model()
    St = X.mesh(S('slate', 'lms', v=0.12, tag='lock'))
    for k in range(n):
        y = -n * 30 + k * 60
        rbox(St, (-30, y - 29, 0), (30, y + 29, 190), r=2, k=1, tile=64)
        for z in (140, 150, 160):
            rbox(X.mesh(S('black', 'lm', tag='vent')), (30, y - 16, z), (31, y + 16, z + 4), r=0.5, k=1, tile=16)
    return X


def hvac(w=220, d=140, h=150):
    X = Model()
    H_ = X.mesh(S('hvac', 'lms', v=0.1)); G_ = X.mesh(S('grille', 'lm'))
    rbox(H_, (-d / 2, -w / 2, 0), (d / 2, w / 2, h), r=4, k=2, tile=128)
    m = Mesh(); disc(m, min(w, d) * 0.35, h + 1, n=24)
    G_.add(m)
    return X


def water_tank():
    X = Model()
    T_ = X.mesh(S('slate', 'lms', v=0.1, tag='wt')); St = X.mesh(S('steel', 'lms', v=0.12, tag='wt'))
    for (x, y) in ((-60, -60), (-60, 60), (60, -60), (60, 60)):
        bar(St, (x, y, 0), (x, y, 120), 6, n=6)
    revolve(T_, [(0, 120), (100, 120), (100, 300), (60, 330), (0, 336)], n=24)
    return X


def dish():
    X = Model()
    W = X.mesh(S('hvac', 'lms', v=0.15, tag='dish')); St = X.mesh(S('steel', 'lms', v=0.12, tag='dish'))
    bar(St, (0, 0, 0), (0, 0, 120), 6, n=8)
    m = Mesh(); revolve(m, [(0.1, 0), (40, 6), (70, 20)], n=20); revolve(m, [(70, 18), (40, 4), (0.1, -2)], n=20)
    W.add(m, rot_axis((0, 1, 0), math.radians(50)), (0, 0, 140))
    return X


def lion():
    """recumbent stone lion for the portico (origin floor centre, faces -y), on a plinth"""
    X = Model()
    S_ = X.mesh(S('stone_w', 'lm', shade=60, tag='lion'))
    rbox(S_, (-70, -140, 0), (70, 140, 80), r=4, k=2, tile=128)
    ellipsoid(S_, (0, 30, 130), 46, 90, 46, nu=16, nv=8)
    ellipsoid(S_, (0, -60, 180), 52, 44, 56, nu=16, nv=10, bump=lambda p, t: 1 + 0.08 * math.sin(9 * t))   # mane
    ellipsoid(S_, (0, -96, 170), 26, 24, 26, nu=12, nv=8)
    for s_ in (-1, 1):
        tube(S_, [(s_ * 26, -40, 100), (s_ * 26, -120, 92)], [16, 14], nseg=10)
        tube(S_, [(s_ * 30, 90, 100), (s_ * 34, 40, 94)], [20, 14], nseg=10)
    tube(S_, [(0, 120, 110), (30, 150, 86), (40, 120, 84)], [7, 5, 4], nseg=6)
    return X


def exit_sign():
    X = Model()
    Bx = X.mesh(S('steel', 'lm', tag='exit')); Gw = X.mesh(S(f'{TD}/exit_sign', 'glow'))
    rbox(Bx, (0, -40, -20), (10, 40, 20), r=2, k=1, tile=32)
    Gw.poly([(10.5, -34, -14), (10.5, 34, -14), (10.5, 34, 14), (10.5, -34, 14)], (1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def wall_lamp():
    X = Model()
    Br = X.mesh(S('brass', 'lms', v=0.2, tag='lamp')); G_ = X.mesh(S('lamp_glow', 'glow'))
    rbox(Br, (0, -10, -16), (4, 10, 16), r=1, k=1, tile=32)
    bar(Br, (4, 0, 0), (24, 0, 8), 2, n=6)
    revolve(G_, [(0.1, -2), (12, 4), (14, 20), (0.1, 16)], n=12, cx=26)
    return X


def cctv():
    X = Model()
    W = X.mesh(S('hvac', 'lm', tag='cam')); R_ = X.mesh(S('red_glow', 'glow'))
    rbox(W, (0, -6, -6), (6, 6, 6), r=1, k=1, tile=16)
    rbox(W, (6, -10, -16), (40, 10, -2), r=3, k=2, tile=32)
    sphere(R_, (40, 6, -4), 2, nu=6, nv=4)
    return X


def cobweb_skylight_frame():
    """glazing bars over the great hall's skylight (world coords)"""
    X = Model()
    St = X.mesh(S('steel', 'lms', v=0.12, tag='sky'))
    z = L.HALL_TOP
    for x in np.linspace(-1024, 1024, 9):
        rbox(St, (x - 8, -1024, z - 24), (x + 8, 1024, z), r=1, k=1, tile=128)
    for y in np.linspace(-1024, 1024, 9):
        rbox(St, (-1024, y - 8, z - 20), (1024, y + 8, z - 4), r=1, k=1, tile=128)
    return X


# ================================================================================================= make
def make():
    os.makedirs(out(MD), exist_ok=True)
    make_textures()
    save('trex', trex()); save('whale', whale())
    save('mammoth', mammoth()); save('moa', moa()); save('moa_s', moa(0.8)); save('sabretooth', sabretooth()); save('eagle', eagle())
    save('dio_rocks', diorama_rocks())
    save('pharaoh', pharaoh()); save('anubis', anubis()); save('obelisk', obelisk()); save('sarc', sarcophagus()); save('sarc_open', sarcophagus(True))
    save('canopic', canopic_jars()); save('lotus_column', lotus_column()); save('mummy_case', mummy_case()); save('pyr_cap', pyramid_cap())
    save('treasure', treasure_pile()); save('treasure_b', treasure_pile(5, 80)); save('death_mask', death_mask())
    save('dome', dome()); save('projector', projector()); save('seats_a', seat_ring(300, 12)); save('seats_b', seat_ring(440, 16, 10, 350))
    save_iqm('orrery', orrery()); save('meteorite', meteorite())
    save('geode', geode())
    for k, col in enumerate(('crystal_p', 'crystal_b', 'crystal_g', 'crystal_c')):
        save(f'cluster_{k}', crystal_cluster(col, 9, 1.0 + 0.3 * (k % 2), k + 3))
    for o in ('skull', 'ammonite', 'trilobite', 'crystal', 'scarab', 'egg'):
        save(f'case_{o}', display_case(o))
    save('squid_tank', squid_tank()); save('shark', shark()); save('shark_s', shark(240)); save('coral_case', coral_case())
    save('column', classical_column()); save('column_s', classical_column(384, 32)); save('ticket_desk', ticket_desk())
    save('stanchions', stanchions()); save('bench', bench()); save('gift_shelf', gift_shelf()); save('gift_shelf_b', gift_shelf(4))
    save('security_desk', security_desk()); save('lockers', lockers())
    save('hvac', hvac()); save('water_tank', water_tank()); save('dish', dish()); save('lion', lion())
    for t in ('dino', 'ice', 'space'):
        save(f'panel_{t}', info_panel(f'panel_{t}'))
    save('exit_sign', exit_sign()); save('wall_lamp', wall_lamp()); save('cctv', cctv()); save('skylight_frame', cobweb_skylight_frame())
