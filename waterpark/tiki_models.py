"""MD3 models for the waterpark's Infinity Bar (tiki bar on the terrace). All geometry is generated here.

    import tiki_models as TK
    TK.init(OUT)                       # models/waterpark/*.md3 go under OUT
    path, scale = TK.get('totem', h=128)
    TK.shaders()                       # shader text for every model surface (append to waterpark.shader)

Conventions: origin = bottom centre (z 0), the front faces +y (the pool). Textures are textures/waterpark/*
(textures.py). Lightmapped models are placed with misc_model spawnflags 4; 'vtx' and 'glow' surfaces stay
vertex lit / fullbright. Collision is separate weapon-clip brushes in build_waterpark.py.
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshlib import Mesh, revolve, disc, tube, ellipsoid, sphere, rbox, rot_z, rot_axis, save_md3

MD = 'models/waterpark'
OUT = None
REG = {}            # shader name -> (image, kind, options)
CACHE = {}


def init(out):
    global OUT
    OUT = out
    os.makedirs(os.path.join(out, MD), exist_ok=True)


def S(img, kind='lm', **opt):
    """model shader on textures/waterpark/<img>. kinds: lm, shiny (lm + env sheen), vtx (vertex lit, opt alpha),
    glow (fullbright, opt wave), flame (additive flicker)"""
    name = f'{MD}/{img}' if kind == 'lm' else f'{MD}/{img}_{kind}'
    REG[name] = (img, kind, opt)
    return name


class Model:
    def __init__(self): self.m = {}
    def mesh(self, shader):
        if shader not in self.m: self.m[shader] = Mesh()
        return self.m[shader]
    def surfaces(self):
        return [M.surface(f's{i}', sh) for i, (sh, M) in enumerate(self.m.items()) if len(M)]


def get(name, **kw):
    key = name + ''.join(f'_{k}{v}' for k, v in sorted(kw.items()))
    if key not in CACHE:
        X = BUILD[name](**kw)
        path = f'{MD}/{key}.md3'
        CACHE[key] = (path, save_md3(os.path.join(OUT, path), X.surfaces(), key))
    return CACHE[key]


# ------------------------------------------------------------------------------------------------ pieces
def face(X, zc, fwd=13.0, w=1.0, paint='tiki_red'):
    """carved tiki face centred at height zc on a post of radius ~fwd, looking +y"""
    wood, dark, white = X.mesh(S('tiki_wood')), X.mesh(S('tiki_dark')), X.mesh(S('tiki_white'))
    rbox(dark, (-11 * w, fwd - 4, zc + 13), (11 * w, fwd + 4, zc + 20), r=2.5, tile=64)          # brow
    for sx in (-1, 1):
        sphere(white, (sx * 6 * w, fwd + 0.5, zc + 7), 5 * w, nu=12, nv=8)                     # eyes
        sphere(dark, (sx * 6 * w, fwd + 4.6 * w, zc + 7), 2.4 * w, nu=10, nv=6)                # pupils
        rbox(wood, (sx * 13 * w - 3, fwd - 17, zc - 8), (sx * 13 * w + 3, fwd - 8, zc + 10), r=2.5, tile=64)   # ears
    rbox(wood, (-3.5 * w, fwd - 3, zc - 7), (3.5 * w, fwd + 5, zc + 9), r=2, tile=64)          # nose
    rbox(X.mesh(S(paint)), (-10 * w, fwd - 3, zc - 22), (10 * w, fwd + 3.5, zc - 11), r=3, tile=64)   # mouth
    rbox(white, (-7 * w, fwd + 3, zc - 18), (7 * w, fwd + 4.5, zc - 14), r=0.6, tile=64)       # teeth


def totem(h=128):
    """carved post: one tiki face per 64u, painted bands, a crown of leaves on top (exactly h tall)"""
    X = Model()
    revolve(X.mesh(S('tiki_wood')), [(0.01, 0), (13, 0), (13, h - 10), (11, h - 4), (0.01, h - 4)], u_tiles=1, n=20)
    bands = ['tiki_teal', 'tiki_red', 'tiki_yellow']
    nh = max(1, int(h // 64))
    for k in range(nh):
        zc = h - 40 - 64 * k
        z0 = zc + 26
        revolve(X.mesh(S(bands[k % 3])), [(13.0, z0), (14.6, z0 + 1), (14.6, z0 + 5), (13.0, z0 + 6)], n=20)
        face(X, zc, paint=['tiki_red', 'tiki_teal', 'tiki_yellow'][k % 3])
    leaf = X.mesh(S('leaf'))
    for k in range(7):
        a = 2 * math.pi * k / 7
        R = rot_z(a) @ rot_axis((1, 0, 0), math.radians(-35))
        ellipsoid(leaf, (8 * math.cos(a), 8 * math.sin(a), h - 2), 4, 14, 1.5, nu=8, nv=4,
                  R=rot_z(a - math.pi / 2) @ rot_axis((1, 0, 0), math.radians(25)))
    return X


def counter(L=320, D=32, H=40):
    """bamboo-fronted bar: row of poles, dark panel behind, varnished rounded top with a rope trim"""
    X = Model()
    rbox(X.mesh(S('tiki_dark')), (-L / 2, -D / 2, 0), (L / 2, D / 2 - 10, H - 6), r=2, tile=64)
    pole = X.mesh(S('bamboo_pole'))
    for x in np.arange(-L / 2 + 6, L / 2 - 5, 11):
        tube(pole, [(x, D / 2 - 5, 0.5), (x, D / 2 - 5, H - 6)], 5, nseg=10, caps=(False, False), vlen=64)
    for y in np.arange(-D / 2 + 6, D / 2 - 5, 11):
        for sx in (-1, 1):
            tube(pole, [(sx * (L / 2 - 5), y, 0.5), (sx * (L / 2 - 5), y, H - 6)], 5, nseg=10, caps=(False, False), vlen=64)
    rbox(X.mesh(S('varnish', 'shiny')), (-L / 2 - 8, -D / 2 - 2, H - 6), (L / 2 + 8, D / 2 + 8, H + 2), r=3, tile=96)
    rope = X.mesh(S('rope'))
    tube(rope, [(-L / 2 - 8, D / 2 + 8.5, H - 4), (L / 2 + 8, D / 2 + 8.5, H - 4)], 2.2, nseg=8, vlen=32)
    # a carved tiki face on each end
    for sx in (-1, 1):
        Y = Model(); face(Y, 18, fwd=0.5, w=0.9)
        for sh, M in Y.m.items():
            X.mesh(sh).add(M, R=rot_z(-sx * math.pi / 2), t=(sx * (L / 2 + 0.5), 0, 0))
    return X


def bottle(M, lbl, x, y, z, kind):
    if kind == 0:   prof = [(0.01, 0), (4.5, 0), (4.5, 15), (2, 19), (1.6, 25), (0.01, 25)]
    elif kind == 1: prof = [(0.01, 0), (5.5, 0), (5.5, 11), (2.2, 14), (1.8, 19), (0.01, 19)]
    else:           prof = [(0.01, 0), (3.4, 0), (3.4, 19), (1.5, 23), (1.3, 30), (0.01, 30)]
    pts = [(r, zz + z) for r, zz in prof]
    revolve(M, pts, n=12, cx=x, cy=y)
    r0 = prof[1][0] + 0.3
    revolve(lbl, [(r0, z + 4), (r0, z + 10)], n=12, cx=x, cy=y, a0=-60, a1=240)


def back_bar(W=320):
    """shelves of glowing bottles over a varnished cabinet, big tiki mask in the middle (wall face = y 0, wall 96 tall)"""
    X = Model()
    var = X.mesh(S('varnish', 'shiny'))
    rbox(var, (-W / 2, 0, 0), (W / 2, 10, 40), r=2, tile=96)
    for zz, d in ((52, 14), (84, 12)):
        for sx in (-1, 1):                       # shelves either side of the mask
            rbox(var, (min(sx * 40, sx * (W / 2 - 4)), 0, zz), (max(sx * 40, sx * (W / 2 - 4)), d, zz + 4), r=1, tile=96)
            for xb in (sx * (W / 2 - 6), sx * 42):
                rbox(var, (xb - 2, 0, zz - 10), (xb + 2, d, zz), r=0.5, tile=64)
    cols = ['bottle_amber', 'bottle_green', 'bottle_blue', 'bottle_red', 'bottle_clear']
    lbl = X.mesh(S('label'))
    k = 0
    for zz, n_ in ((56, 6), (88, 5)):
        for sx in (-1, 1):
            for x in np.linspace(sx * 54, sx * (W / 2 - 16), n_):
                bottle(X.mesh(S(cols[k % 5], 'glow', dim=0.75)), lbl, float(x), 7.0, zz, k % 3); k += 1
    # cabinet door seams + rope pulls
    dark = X.mesh(S('tiki_dark'))
    for x in np.linspace(-W / 2, W / 2, 6)[1:-1]:
        rbox(dark, (x - 1, 9.5, 4), (x + 1, 11, 36), r=0.4, tile=64)
    # mask on the wall top: painted oval with a big carved face
    ellipsoid(X.mesh(S('tiki_wood')), (0, 8, 76), 28, 8, 32, nu=20, nv=12)
    for k2, (c, z0) in enumerate((('tiki_teal', 100), ('tiki_yellow', 54))):
        ellipsoid(X.mesh(S(c)), (0, 8, z0), 22 - 6 * k2, 6, 5, nu=14, nv=6)
    Y = Model(); face(Y, 78, fwd=15.5, w=1.6, paint='tiki_red')
    for sh, M in Y.m.items(): X.mesh(sh).add(M)
    for sx in (-1, 1):            # feathers
        for j in range(3):
            a = math.radians(sx * (25 + 22 * j))
            ellipsoid(X.mesh(S(['tiki_red', 'tiki_yellow', 'tiki_teal'][j])), (sx * 22 + math.sin(a) * 20, 6, 98 + math.cos(a) * 12),
                      4, 2, 12, nu=8, nv=5, R=rot_axis((0, 1, 0), a))
    return X


def fringe(L=448, D=192):
    """shaggy thatch skirt round a flat roof slab (slab top at z 16, bottom at 0), rolled binding on the edge"""
    X = Model()
    M1 = X.mesh(S('thatch_fringe', 'vtx', alpha=True))
    hx, hy = L / 2, D / 2
    for layer, (out0, out1, ztop, zbot, sh) in enumerate(((1, 30, 16, -34, 0.0), (7, 40, 8, -26, 0.37))):
        for (ax, sgn, half, span) in (('x', 1, hx, hy), ('x', -1, hx, hy), ('y', 1, hy, hx), ('y', -1, hy, hx)):
            def P(u, o, z):
                return (sgn * (half + o), u, z) if ax == 'x' else (u, sgn * (half + o), z)
            n = 0 if ax == 'x' else 1
            nrm = np.zeros(3); nrm[n] = sgn; nrm[2] = 0.6
            seg = 64.0
            us = np.arange(-span - out1, span + out1 + 0.1, seg)
            for u0, u1 in zip(us, us[1:]):
                q = [P(u0, out0, ztop), P(u1, out0, ztop), P(u1, out1, zbot), P(u0, out1, zbot)]
                M1.poly(q, nrm, [(sh + u0 / 128, 0), (sh + u1 / 128, 0), (sh + u1 / 128, 1), (sh + u0 / 128, 1)])
    bind = X.mesh(S('thatch', 'vtx'))
    ring = [(-hx - 3, -hy - 3, 13), (hx + 3, -hy - 3, 13), (hx + 3, hy + 3, 13), (-hx - 3, hy + 3, 13), (-hx - 3, -hy - 3, 13)]
    for a, b in zip(ring, ring[1:]):
        tube(bind, [a, b], 5, nseg=8, vlen=64)
    return X


def torch(h=96):
    X = Model()
    tube(X.mesh(S('bamboo_pole')), [(0, 0, 0), (0, 0, h)], 3, nseg=10, vlen=64)
    revolve(X.mesh(S('rope')), [(3, h - 4), (9, h + 8), (9, h + 14), (7, h + 14), (0.01, h + 10)], n=14)
    fl = X.mesh(S('flame', 'flame'))
    for a in (0, math.pi / 2):
        c, s = math.cos(a), math.sin(a)
        q = [(-10 * c, -10 * s, h + 10), (10 * c, 10 * s, h + 10), (10 * c, 10 * s, h + 44), (-10 * c, -10 * s, h + 44)]
        fl.poly(q, (-s, c, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    return X


def drink(kind=0):
    """coconut cocktail (kind 0) or pineapple (kind 1) with a straw and a paper umbrella"""
    X = Model()
    if kind == 0:
        revolve(X.mesh(S('coconut')), [(0.01, 0), (4, 0.4), (7.5, 2.5), (9.2, 5.5), (9.4, 9)], n=16, vlen=24)
        disc(X.mesh(S('coconut_in')), 8.2, 9, n=14)
        top = 9
    else:
        ellipsoid(X.mesh(S('pineapple')), (0, 0, 10), 7, 7, 10, nu=12, nv=8)
        for k in range(6):
            a = 2 * math.pi * k / 6
            ellipsoid(X.mesh(S('leaf')), (2 * math.cos(a), 2 * math.sin(a), 23), 1.6, 1.2, 6, nu=6, nv=4,
                      R=rot_axis((-math.sin(a), math.cos(a), 0), math.radians(25)))
        top = 18
    tube(X.mesh(S('tiki_red')), [(2, 0, top - 4), (6, 2, top + 14)], 0.8, nseg=6)
    tube(X.mesh(S('tiki_white')), [(-2, 1, top - 4), (-4, 3, top + 16)], 0.5, nseg=5)
    revolve(X.mesh(S('umb_yellow' if kind == 0 else 'umb_red', 'vtx', cull=True)), [(0.01, top + 19), (8, top + 15)], n=12,
            cx=-4, cy=3)
    return X


def swim_stool(h=80):
    X = Model()
    revolve(X.mesh(S('tiki_teal')), [(0.01, 0), (10, 0), (10, 3), (5, 6), (5, h - 8), (12, h - 6), (14, h - 3), (13, h), (0.01, h)], n=20)
    return X


def bar_sign(w=140, h=26, rope=20):
    """driftwood plank on two ropes; hangs from a ceiling at z = h + rope"""
    X = Model()
    rbox(X.mesh(S('driftwood')), (-w / 2 - 4, -3, 0), (w / 2 + 4, 3, h + 2), r=2, tile=128)
    m = X.mesh(S('sign_tiki'))
    # seen from +y the viewer's right is -x, so u runs from +x to -x (otherwise the text reads mirrored)
    m.poly([(-w / 2, 3.3, 2), (w / 2, 3.3, 2), (w / 2, 3.3, h), (-w / 2, 3.3, h)], (0, 1, 0), [(1, 1), (0, 1), (0, 0), (1, 0)])
    for sx in (-1, 1):
        tube(X.mesh(S('rope')), [(sx * (w / 2 - 10), 0, h), (sx * (w / 2 - 10), 0, h + 2 + rope)], 1.2, nseg=6, vlen=32, caps=(False, False))
    return X


def string_lights(L=400, sag=26, n=16):
    """catenary of coloured bulbs from (-L/2, 0, 0) to (L/2, 0, 0)"""
    X = Model()
    xs = np.linspace(-L / 2, L / 2, 41)
    path = [(x, 0, -sag * (1 - (2 * x / L) ** 2)) for x in xs]
    tube(X.mesh(S('tiki_dark')), path, 0.7, nseg=5)
    cols = ['bulb_warm', 'bulb_pink', 'bulb_teal']
    for k, x in enumerate(np.linspace(-L / 2 + 12, L / 2 - 12, n)):
        z = -sag * (1 - (2 * x / L) ** 2)
        sphere(X.mesh(S(cols[k % 3], 'glow')), (x, 0, z - 4), 2.8, nu=8, nv=6)
    return X


BUILD = {'totem': totem, 'counter': counter, 'back_bar': back_bar, 'fringe': fringe, 'torch': torch,
         'drink': drink, 'swim_stool': swim_stool, 'bar_sign': bar_sign, 'string_lights': string_lights}


def shaders():
    s = '// ---- MD3 models (tiki_models.py)\n'
    for name, (img, kind, opt) in sorted(REG.items()):
        t = f'textures/waterpark/{img}'
        if kind in ('lm', 'shiny'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle 75\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'shiny':
                s += f'\t{{\n\t\tmap textures/waterpark/caustics\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.12 0.12 )\n\t\ttcGen environment\n\t}}\n'
            s += '}\n\n'
        elif kind == 'vtx':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nomarks\n'
            if opt.get('alpha'):
                s += ('\tsurfaceparm trans\n\tsurfaceparm alphashadow\n\tcull none\n'
                      f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n')
            else:
                s += ('\tcull none\n' if opt.get('cull') else '') + f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            d = opt.get('dim', 1.0)
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave sin {d * 0.9:.2f} {d * 0.1:.2f} 0 0.4\n\t}}\n}}\n\n')
        elif kind == 'flame':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
                  '\tsurfaceparm nomarks\n\tcull none\n\tdeformVertexes wave 30 sin 0 1.5 0 2.3\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave noise 0.85 0.25 0 6\n\t\ttcMod stretch sin 1 0.04 0 3\n\t}}\n}}\n\n')
    return s
