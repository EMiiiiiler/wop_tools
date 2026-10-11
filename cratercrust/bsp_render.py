#!/usr/bin/env python3
"""Tiny software renderer for Q3 BSPs: textures x lightmaps, z-buffer, perspective camera.
usage: bsp_render.py map.bsp gamedir out.png  x y z  yaw pitch  [w h fov]"""
import struct, sys, math, os
import numpy as np
from PIL import Image

bsp, gd, out = sys.argv[1], sys.argv[2], sys.argv[3]
cx, cy, cz, yaw, pitch = map(float, sys.argv[4:9])
W = int(sys.argv[9]) if len(sys.argv) > 9 else 960
H = int(sys.argv[10]) if len(sys.argv) > 10 else 540
FOV = float(sys.argv[11]) if len(sys.argv) > 11 else 90
ZMAX = float(sys.argv[12]) if len(sys.argv) > 12 else 1e9

d = open(bsp, 'rb').read()
lumps = [struct.unpack_from('<ii', d, 8 + i * 8) for i in range(17)]
def L(i, fmt):
    o, n = lumps[i]; s = struct.calcsize(fmt)
    return [struct.unpack_from(fmt, d, o + k * s) for k in range(n // s)]
shaders = [(s[0].split(b'\0')[0].decode(), s[1], s[2]) for s in L(1, '<64sii')]
o, n = lumps[10]
V = np.frombuffer(d, dtype=np.dtype([('xyz', '<f4', 3), ('st', '<f4', 2), ('lm', '<f4', 2), ('n', '<f4', 3), ('c', 'u1', 4)]), count=n // 44, offset=o)
o, n = lumps[11]; IDX = np.frombuffer(d, '<i4', n // 4, o)
surfs = L(13, '<12i3f9f2i')
import re as _re
_ents = d[lumps[0][0]:lumps[0][0] + lumps[0][1]].split(b'\0')[0].decode('latin1')
_mods = L(7, '<6f4i')
SURF_OFF = {}
for _m in _re.finditer(r'\{([^{}]*)\}', _ents):
    _kv = dict(_re.findall(r'"([^"]*)"\s+"([^"]*)"', _m.group(1)))
    if _kv.get('model', '').startswith('*') and 'origin' in _kv:
        _o = [float(v) for v in _kv['origin'].split()]; _md = _mods[int(_kv['model'][1:])]
        for _si in range(_md[6], _md[6] + _md[7]): SURF_OFF[_si] = _o
o, n = lumps[14]; LM = np.frombuffer(d, 'u1', n, o).reshape(-1, 128, 128, 3).astype(np.float32) / 255.0

texcache = {}
FILES = {}
for dp, _, fs in os.walk(gd):
    for fn in fs:
        full = os.path.join(dp, fn); rel = os.path.relpath(full, gd).replace(os.sep, '/')
        base, ext = os.path.splitext(rel)
        if ext.lower() in ('.jpg', '.tga', '.png'): FILES.setdefault(base.lower(), full)
def tex(name):
    if name in texcache: return texcache[name]
    img = None
    p = FILES.get(name.lower())
    if p:
        try:
            img = np.asarray(Image.open(p).convert('RGBA'), np.float32) / 255.0
        except Exception:
            img = None
    texcache[name] = img
    return img

SKY = {'textures/cratercrust/cc_sky'}
SKIPC = ('common/', 'textures/common/')

# camera
yr, pr = math.radians(yaw), math.radians(pitch)
fwd = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])
if abs(pitch) >= 89.9: fwd = np.array([0.0, 0.0, -1.0])
right = np.array([math.sin(yr), -math.cos(yr), 0.0])
up = np.cross(right, fwd)
f = (W / 2) / math.tan(math.radians(FOV) / 2)
cam = np.array([cx, cy, cz])

color = np.zeros((H, W, 3), np.float32); color[:] = (0.04, 0.03, 0.12)
zbuf = np.full((H, W), np.inf, np.float32)
# sky gradient background
grad = np.linspace(0, 1, H)[:, None]
color[:] = (np.array([0.03, 0.02, 0.12]) * (1 - grad) + np.array([0.22, 0.10, 0.32]) * grad)[:, None, :]

XYZ = V['xyz'].astype(np.float64).copy()
for _si, _o in SURF_OFF.items():
    _s = surfs[_si]; XYZ[_s[3]:_s[3] + _s[4]] += _o
P = XYZ - cam
cz_ = P @ fwd; cx_ = P @ right; cy_ = P @ up
NEAR = 4.0

def clip_tri(tri):
    """returns list of triangles as attribute arrays (3, 12): cam x,y,z, st, lm, rgb"""
    A = np.zeros((3, 10))
    for k, i in enumerate(tri):
        A[k, :3] = (cx_[i], cy_[i], cz_[i]); A[k, 3:5] = V['st'][i]; A[k, 5:7] = V['lm'][i]; A[k, 7:10] = V['c'][i, :3] / 255.0
    inside = A[:, 2] >= NEAR
    if inside.all(): return [A]
    if not inside.any(): return []
    poly = []
    for k in range(3):
        P0, P1 = A[k], A[(k + 1) % 3]
        i0, i1 = P0[2] >= NEAR, P1[2] >= NEAR
        if i0: poly.append(P0)
        if i0 != i1:
            t = (NEAR - P0[2]) / (P1[2] - P0[2]); poly.append(P0 + (P1 - P0) * t)
    return [np.array([poly[0], poly[j], poly[j + 1]]) for j in range(1, len(poly) - 1)]


def raster(tri, s):
    sh = shaders[s[0]][0]
    if sh.startswith(SKIPC) or 'trigger' in sh or sh in SKY: return
    for A in clip_tri(tri):
        raster_a(A, sh, s)


def raster_a(A, sh, s):
    zc = A[:, 2]
    xs = W / 2 + f * A[:, 0] / zc
    ys = H / 2 - f * A[:, 1] / zc
    x0, x1 = int(max(0, math.floor(xs.min()))), int(min(W - 1, math.ceil(xs.max())))
    y0, y1 = int(max(0, math.floor(ys.min()))), int(min(H - 1, math.ceil(ys.max())))
    if x0 > x1 or y0 > y1: return
    area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
    if abs(area) < 1e-9: return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
    w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
    w2 = 1 - w0 - w1
    m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not m.any(): return
    iz = w0 / zc[0] + w1 / zc[1] + w2 / zc[2]
    z = 1 / np.where(iz > 0, iz, 1e-9)
    zb = zbuf[y0:y1 + 1, x0:x1 + 1]
    m &= z < zb
    if not m.any(): return
    pw = np.stack([w0 / zc[0], w1 / zc[1], w2 / zc[2]], -1) * z[..., None]
    t = tex(sh)
    if t is not None:
        st = A[:, 3:5]
        u = (pw * st[:, 0]).sum(-1); v = (pw * st[:, 1]).sum(-1)
        th, tw = t.shape[:2]
        col4 = t[(np.floor(v * th).astype(int)) % th, (np.floor(u * tw).astype(int)) % tw]
        col = col4[..., :3]
        if sh.startswith('models/'):
            m &= col4[..., 3] > 0.5
    else:
        col = np.full(gx.shape + (3,), 0.6, np.float32)
    lmn = s[7]
    if lmn >= 0:
        lmc = A[:, 5:7]
        lu = np.clip((pw * lmc[:, 0]).sum(-1) * 128, 0, 127).astype(int); lv = np.clip((pw * lmc[:, 1]).sum(-1) * 128, 0, 127).astype(int)
        light = LM[lmn, lv, lu] * 2.0
    else:
        vc = A[:, 7:10]
        light = (pw[..., None] * vc[None, None]).sum(-2) * 2.0
        if 'neon' in sh or 'screen' in sh or 'sign' in sh or 'jumppad' in sh or 'coals' in sh or 'lamp_light' in sh or 'marquee' in sh:
            light = np.ones_like(light)
    if any(k in sh for k in ('neon', 'screen', 'sign', 'jumppad', 'coals', 'lamp_light', 'marquee', 'pad_side')):
        light = np.maximum(light, 1.0)
    out_c = np.clip(col * light, 0, 1)
    if 'glass' in sh or 'water' in sh or 'ballpit' in sh:
        alpha = 0.35 if 'glass' in sh else (0.9 if 'ballpit' in sh else 0.5)
        dst = color[y0:y1 + 1, x0:x1 + 1]
        dst[m] = dst[m] * (1 - alpha) + out_c[m] * alpha
        return
    zb[m] = z[m]
    color[y0:y1 + 1, x0:x1 + 1][m] = out_c[m]

trans = []
for s in surfs:
    typ, fi, ni, fv = s[2], s[5], s[6], s[3]
    if typ not in (1, 3) or ni == 0: continue
    sh = shaders[s[0]][0]
    tris = IDX[fi:fi + ni].reshape(-1, 3) + fv
    tris = [t for t in tris if XYZ[t, 2].min() <= ZMAX]
    if 'glass' in sh or 'water' in sh or 'ballpit' in sh:
        trans.append((s, tris)); continue
    for t in tris: raster(t, s)
for s, tris in trans:
    for t in tris: raster(t, s)
Image.fromarray((np.clip(color, 0, 1) ** (1 / 1.1) * 255).astype(np.uint8)).save(out)
print('wrote', out)
