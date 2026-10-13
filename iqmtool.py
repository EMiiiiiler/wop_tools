#!/usr/bin/env python3
"""Minimal static IQM (v2) writer/reader for World of Padman mover models.

Why IQM: MD3 stores vertices as 1/64 fixed point, so nothing can sit more than 512u from the model origin. A
func_rotating carrying a model2 spins it around the entity origin, so a fish that circles 1000u out needs a model
whose geometry sits 1000u from its origin - IQM stores float positions and every WoP renderer (opengl1, opengl2,
vulkan) loads static IQMs (no joints / no frames; bounds are computed from the meshes).

    from iqmtool import save, load
    save('models/padtank/sharks.iqm', [dict(name='body', material='models/padtank/shark', verts=V, normals=N,
                                             st=UV, tris=T)])

verts (N,3) game units, normals (N,3), st (N,2) with t running downward (same as MD3), tris (M,3) wound clockwise seen
from the front (Quake order, like MD3: the renderers copy IQM triangles unchanged). Each mesh must stay under 1000
verts (SHADER_MAX_VERTEXES); save() splits nothing, so build several meshes. opengl2 requires the tangent array; it
is generated here.
"""
import struct
import numpy as np

IQM_POSITION, IQM_TEXCOORD, IQM_NORMAL, IQM_TANGENT = 0, 1, 2, 3
IQM_FLOAT = 7
HDR = '<16s27I'


def _tangents(V, N, ST, T):
    tan = np.zeros_like(V)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    ua, ub, uc = ST[T[:, 0]], ST[T[:, 1]], ST[T[:, 2]]
    e1, e2 = b - a, c - a
    d1, d2 = ub - ua, uc - ua
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) < 1e-9, 1e-9, r)
    t = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    for k in range(3): np.add.at(tan, T[:, k], t)
    tan -= N * (tan * N).sum(1, keepdims=True)
    l = np.linalg.norm(tan, axis=1, keepdims=True)
    fallback = np.cross(N, np.array([0, 0, 1.0]))
    fallback[np.linalg.norm(fallback, axis=1) < 1e-6] = (1, 0, 0)
    tan = np.where(l > 1e-6, tan / np.maximum(l, 1e-9), fallback / np.linalg.norm(fallback, axis=1, keepdims=True))
    return np.concatenate([tan, np.ones((len(V), 1))], 1)


def save(path, meshes, comment='wop_tools iqmtool'):
    text = b'\0'
    names = []
    def addtext(s):
        nonlocal text
        o = len(text); text += s.encode('latin1') + b'\0'; return o
    V, N, ST, TR, mrec = [], [], [], [], []
    nv = nt = 0
    for m in meshes:
        v = np.asarray(m['verts'], np.float64); n = np.asarray(m['normals'], np.float64)
        n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        st = np.asarray(m['st'], np.float64); t = np.asarray(m['tris'], np.int64)
        assert len(v) < 1000, 'IQM mesh over SHADER_MAX_VERTEXES (999): split it'
        mrec.append((addtext(m.get('name', 'mesh')), addtext(m['material']), nv, len(v), nt, len(t)))
        V.append(v); N.append(n); ST.append(st); TR.append(t + nv)
        nv += len(v); nt += len(t)
    V = np.concatenate(V); N = np.concatenate(N); ST = np.concatenate(ST); TR = np.concatenate(TR)
    TAN = _tangents(V, N, ST, TR)
    while len(text) % 4: text += b'\0'
    ofs_text = struct.calcsize(HDR)
    ofs_meshes = ofs_text + len(text)
    ofs_va = ofs_meshes + 24 * len(mrec)
    ofs_data = ofs_va + 20 * 4
    arrays = [(IQM_POSITION, 3, V), (IQM_TEXCOORD, 2, ST), (IQM_NORMAL, 3, N), (IQM_TANGENT, 4, TAN)]
    blobs, vas, o = [], [], ofs_data
    for typ, size, arr in arrays:
        b = np.asarray(arr, '<f4').tobytes(); vas.append((typ, 0, IQM_FLOAT, size, o)); blobs.append(b); o += len(b)
    ofs_tri = o
    tri_b = np.asarray(TR, '<u4').tobytes()
    filesize = ofs_tri + len(tri_b)
    hdr = struct.pack(HDR, b'INTERQUAKEMODEL\0', 2, filesize, 0, len(text), ofs_text, len(mrec), ofs_meshes, 4, nv, ofs_va,
                      nt, ofs_tri, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    out = bytearray(hdr) + text
    for r in mrec: out += struct.pack('<6I', *r)
    for r in vas: out += struct.pack('<5I', *r)
    for b in blobs: out += b
    out += tri_b
    assert len(out) == filesize
    open(path, 'wb').write(out)
    return path


def load(path):
    """-> dict(surfaces=[{name, shader, verts, normals, st, tris}]) like md3tool.load (tris relative to the mesh)"""
    b = open(path, 'rb').read()
    h = struct.unpack_from(HDR, b, 0)
    assert h[0].startswith(b'INTERQUAKEMODEL'), path
    (num_text, ofs_text, num_meshes, ofs_meshes, num_va, num_v, ofs_va, num_t, ofs_t) = h[4:13]
    text = b[ofs_text:ofs_text + num_text]
    def txt(o): return text[o:text.index(b'\0', o)].decode('latin1')
    arr = {}
    for i in range(num_va):
        typ, fl, fmt, size, off = struct.unpack_from('<5I', b, ofs_va + 20 * i)
        if fmt == IQM_FLOAT: arr[typ] = np.frombuffer(b, '<f4', num_v * size, off).reshape(num_v, size)
    tris = np.frombuffer(b, '<u4', num_t * 3, ofs_t).reshape(-1, 3).astype(np.int64)
    out = []
    for i in range(num_meshes):
        nm, mat, fv, nv, ft, ntr = struct.unpack_from('<6I', b, ofs_meshes + 24 * i)
        out.append({'name': txt(nm), 'shader': txt(mat), 'verts': arr[IQM_POSITION][fv:fv + nv].astype(np.float32),
                    'normals': arr.get(IQM_NORMAL, np.zeros((num_v, 3)))[fv:fv + nv], 'st': arr[IQM_TEXCOORD][fv:fv + nv].astype(np.float32),
                    'tris': tris[ft:ft + ntr] - fv})
    return {'surfaces': out}


if __name__ == '__main__':
    import sys
    m = load(sys.argv[1])
    for s in m['surfaces']:
        v = s['verts']
        print(f"{s['name']:16s} {s['shader']:40s} {len(v):4d} verts {len(s['tris']):4d} tris  min {v.min(0).round(1)} max {v.max(0).round(1)}")
