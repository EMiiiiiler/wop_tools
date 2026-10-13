#!/usr/bin/env python3
"""Minimal MD3 writer (single frame, no tags) for custom World of Padman map objects.

    from md3write import save
    save('models/mapobjects/playroom/pillow.md3', [
        dict(name='pillow', shader='models/mapobjects/playroom/pillow', verts=V, normals=N, st=UV, tris=T)])

verts (N,3) in game units (stored as 1/64 fixed point, so |coord| < 512), normals (N,3) unit vectors,
st (N,2) texture coords (t runs downward like every Q3 texture), tris (M,3) indices wound clockwise seen from
the front (Quake order). md3tool.load() reads the result back.
"""
import struct
import numpy as np


def _enc_normal(n):
    """Q3 lat/long normal: high byte = atan2(y, x), low byte = acos(z), both scaled 0..255 for 0..2pi"""
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    lat = np.round(np.arctan2(n[:, 1], n[:, 0]) * 255 / (2 * np.pi)).astype(np.int32) & 255
    lng = np.round(np.arccos(np.clip(n[:, 2], -1, 1)) * 255 / (2 * np.pi)).astype(np.int32) & 255
    # straight up / down: Q3 tools use these exact codes
    lat[n[:, 2] > 0.9999] = 0; lng[n[:, 2] > 0.9999] = 0
    lat[n[:, 2] < -0.9999] = 0; lng[n[:, 2] < -0.9999] = 128
    return ((lat << 8) | lng).astype(np.int16)


def _s(txt, n):
    return txt.encode('latin1')[:n - 1].ljust(n, b'\0')


def save(path, surfaces, name='model'):
    allv = np.concatenate([np.asarray(s['verts'], np.float32) for s in surfaces])
    assert np.abs(allv).max() < 511.9, 'MD3 coordinates must stay within +-512 (scale the misc_model instead)'
    mn, mx = allv.min(0), allv.max(0)
    surf_blobs = []
    for s in surfaces:
        V = np.asarray(s['verts'], np.float32); N = np.asarray(s['normals'], np.float32)
        ST = np.asarray(s['st'], np.float32); TR = np.asarray(s['tris'], np.int32)
        nv, nt = len(V), len(TR)
        assert nv < 4096 and nt < 8192, 'MD3 surface limits: 4095 verts, 8191 tris'
        hdr = 4 + 64 + 4 * 10
        ofs_sh = hdr; ofs_tri = ofs_sh + 68; ofs_st = ofs_tri + nt * 12; ofs_xyz = ofs_st + nv * 8; ofs_end = ofs_xyz + nv * 8
        b = bytearray()
        b += struct.pack('<4s64s10i', b'IDP3', _s(s['name'], 64), 0, 1, 1, nv, nt, ofs_tri, ofs_sh, ofs_st, ofs_xyz, ofs_end)
        b += struct.pack('<64si', _s(s['shader'], 64), 0)
        b += TR.astype('<i4').tobytes()
        b += ST.astype('<f4').tobytes()
        xyz = np.round(V * 64).astype('<i2')
        rec = np.zeros((nv, 4), '<i2'); rec[:, :3] = xyz; rec[:, 3] = _enc_normal(N)
        b += rec.tobytes()
        assert len(b) == ofs_end
        surf_blobs.append(bytes(b))
    ofs_frames = 108; ofs_tags = ofs_frames + 56; ofs_surf = ofs_tags
    ofs_end = ofs_surf + sum(len(b) for b in surf_blobs)
    out = bytearray()
    out += struct.pack('<4si64si8i', b'IDP3', 15, _s(name, 64), 0, 1, 0, len(surfaces), 0, ofs_frames, ofs_tags, ofs_surf, ofs_end)
    radius = float(np.linalg.norm(np.maximum(np.abs(mn), np.abs(mx))))
    out += struct.pack('<3f3f3ff16s', *mn, *mx, 0, 0, 0, radius, _s('frame0', 16))
    for b in surf_blobs: out += b
    assert len(out) == ofs_end
    open(path, 'wb').write(out)
    return path


def vertex_normals(V, T):
    """area-weighted vertex normals for triangles wound clockwise seen from outside (Quake order)"""
    V = np.asarray(V, np.float64); N = np.zeros_like(V)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(c - a, b - a)
    for k in range(3): np.add.at(N, T[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
