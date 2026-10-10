#!/usr/bin/env python3
"""MD3 reader for World of Padman map objects.

    python3 md3tool.py bounds <models root> [out.json]
        Writes {"<path relative to root>": {"min":[..],"max":[..],"shaders":[..]}} for every .md3
        under the root (case-insensitive). Root is usually a folder holding models/mapobjects/...
    python3 md3tool.py info <file.md3>

As a module: load(path) -> dict(frames, surfaces=[{name, shader, verts(N,3), st(N,2), tris(M,3)}]).
Real MD3s: the WoP GitHub repo stores them in LFS; fetch with
https://media.githubusercontent.com/media/PadWorld-Entertainment/worldofpadman/main/<repo path>
"""
import struct, sys, os, json
import numpy as np


def load(path, frame=0):
    b = open(path, 'rb').read()
    ident, ver = struct.unpack_from('<4si', b, 0)
    if ident != b'IDP3':
        raise ValueError(f'{path}: not an MD3 ({ident!r})')
    (nframes, ntags, nsurf, nskins, ofs_frames, ofs_tags, ofs_surf, ofs_end) = struct.unpack_from("<8i", b, 76)
    frames = []
    for i in range(nframes):
        o = ofs_frames + i * 56
        mn = struct.unpack_from('<3f', b, o); mx = struct.unpack_from('<3f', b, o + 12)
        frames.append({'min': mn, 'max': mx})
    surfaces = []
    o = ofs_surf
    for s in range(nsurf):
        (sid, name, flags, sfr, nsh, nv, ntri, ofs_tri, ofs_sh, ofs_st, ofs_xyz, ofs_send) = struct.unpack_from('<4s64s10i', b, o)
        shader = ''
        if nsh:
            shader = struct.unpack_from('<64s', b, o + ofs_sh)[0].split(b'\0')[0].decode('latin1')
        tris = np.frombuffer(b, '<i4', ntri * 3, o + ofs_tri).reshape(-1, 3)
        st = np.frombuffer(b, '<f4', nv * 2, o + ofs_st).reshape(-1, 2)
        fr = min(frame, sfr - 1)
        xyz = np.frombuffer(b, '<i2', nv * 4, o + ofs_xyz + fr * nv * 8).reshape(-1, 4)
        verts = xyz[:, :3].astype(np.float32) / 64.0
        lat = ((xyz[:, 3].astype(np.int32) >> 8) & 255) * 2 * np.pi / 255
        lng = (xyz[:, 3].astype(np.int32) & 255) * 2 * np.pi / 255
        normals = np.stack([np.cos(lat) * np.sin(lng), np.sin(lat) * np.sin(lng), np.cos(lng)], 1)
        surfaces.append({'name': name.split(b'\0')[0].decode('latin1'), 'shader': shader,
                         'verts': verts, 'normals': normals, 'st': st.copy(), 'tris': tris.copy()})
        o += ofs_send
    return {'frames': frames, 'surfaces': surfaces}


def bounds(path):
    m = load(path)
    v = np.concatenate([s['verts'] for s in m['surfaces']]) if m['surfaces'] else np.zeros((1, 3))
    return {'min': [round(float(x), 2) for x in v.min(0)], 'max': [round(float(x), 2) for x in v.max(0)],
            'shaders': sorted({s['shader'] for s in m['surfaces']})}


def footprint(path, scale=1.0, angle=0.0, z_tol=2.0):
    """XY points of the vertices within z_tol of the model's lowest point (scaled + rotated)."""
    m = load(path)
    v = np.concatenate([s['verts'] for s in m['surfaces']]) * scale
    a = np.radians(angle); c, s_ = np.cos(a), np.sin(a)
    v = v @ np.array([[c, s_, 0], [-s_, c, 0], [0, 0, 1]])
    return v[v[:, 2] <= v[:, 2].min() + z_tol][:, :2], v


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == 'info':
        m = load(sys.argv[2])
        print('frames', len(m['frames']), 'bounds', bounds(sys.argv[2]))
        for s in m['surfaces']:
            print(f"  {s['name']:20s} {s['shader']:50s} verts {len(s['verts'])} tris {len(s['tris'])}")
        return
    root = sys.argv[2]
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith('.md3'):
                p = os.path.join(dp, f)
                try:
                    out[os.path.relpath(p, root).replace(os.sep, '/')] = bounds(p)
                except Exception as e:
                    print('skip', p, e)
    dst = sys.argv[3] if len(sys.argv) > 3 else 'md3bounds.json'
    json.dump(out, open(dst, 'w'), indent=0, sort_keys=True)
    print(len(out), 'models ->', dst)


if __name__ == '__main__':
    main()
