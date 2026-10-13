#!/usr/bin/env python3
"""Turn a compiled Quake 3 / WoP .bsp into a self-contained three.js viewer page.

    python3 bsp2scene.py <map.bsp> <out.html> --vfs <dir> [--vfs <dir> ...] [--three three.min.js]
                         [--sky env/ueberdenwolken] [--texsize 256] [--title "name"]
                         [--threeurl https://cdnjs...]   (reference three.js by URL instead of inlining)
                         [--style night.css]   (extra CSS appended to the page style, e.g. a map-specific palette)
                         [--views "Name:x,y,z,yaw,pitch;..."]   (camera buttons, first one is the start view)

--vfs: directories searched (in order) for scripts/*.shader and textures; pass pk3dir folders
       or your map's source folder. Last one wins for duplicate shader names, like the game.
The page renders lightmaps (x2 overbright like r_overBrightBits 1), vertex-lit model surfaces,
alpha-tested and blended shaders, the skybox, and point-entity markers (weapons, ammo, spawns...).
Camera control in the page: drag = look, WASD/arrows = move, Q/E = down/up, shift = fast.
Headless use: window.__setView(x,y,z,yaw,pitch) in Q3 coords, then screenshot (see shoot.py).
"""
import struct, sys, os, re, io, json, base64, argparse, glob
import numpy as np
from PIL import Image

LUMPS = 17


def read_bsp(path):
    b = open(path, 'rb').read()
    ident, ver = struct.unpack_from('<4si', b, 0)
    assert ident == b'IBSP', ident
    lumps = [struct.unpack_from('<2i', b, 8 + i * 8) for i in range(LUMPS)]
    L = lambda i: b[lumps[i][0]:lumps[i][0] + lumps[i][1]]
    ents = L(0).split(b'\0')[0].decode('latin1')
    sh = L(1); shaders = []
    for i in range(len(sh) // 72):
        n, sf, cf = struct.unpack_from('<64sii', sh, i * 72)
        shaders.append((n.split(b'\0')[0].decode('latin1'), sf, cf))
    dv = np.frombuffer(L(10), dtype=np.dtype([('xyz', '<f4', 3), ('st', '<f4', 2), ('lm', '<f4', 2),
                                               ('n', '<f4', 3), ('c', 'u1', 4)]))
    di = np.frombuffer(L(11), '<i4')
    sd = np.dtype([('shader', '<i4'), ('fog', '<i4'), ('type', '<i4'), ('fv', '<i4'), ('nv', '<i4'),
                   ('fi', '<i4'), ('ni', '<i4'), ('lm', '<i4'), ('lmx', '<i4'), ('lmy', '<i4'),
                   ('lmw', '<i4'), ('lmh', '<i4'), ('lmo', '<f4', 3), ('lmv', '<f4', 9), ('pw', '<i4'), ('ph', '<i4')])
    surfs = np.frombuffer(L(13), sd)
    md = np.frombuffer(L(7), np.dtype([('mins', '<f4', 3), ('maxs', '<f4', 3), ('fs', '<i4'), ('ns', '<i4'),
                                        ('fb', '<i4'), ('nb', '<i4')]))
    read_bsp.models = md
    lmb = L(14); nlm = len(lmb) // (128 * 128 * 3)
    lms = [np.frombuffer(lmb, 'u1', 128 * 128 * 3, i * 128 * 128 * 3).reshape(128, 128, 3) for i in range(nlm)]
    md = L(7); models = [struct.unpack_from('<6f4i', md, i * 40) for i in range(len(md) // 40)]
    return ents, shaders, dv, di, surfs, lms, models


def parse_entities(s):
    out = []
    for m in re.finditer(r'\{([^{}]*)\}', s):
        out.append(dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', m.group(1))))
    return out


# ------------------------------------------------------------------ shaders / textures
def strip_comments(t):
    return re.sub(r'//[^\n]*', '', t)


def parse_shaders(vfs):
    """returns {name_lower: info} with info = dict(img, blend, alpha, sky, nodraw, skyenv, scroll)"""
    out = {}
    for d in vfs:
        for f in sorted(glob.glob(os.path.join(d, 'scripts', '*.shader'))):
            t = strip_comments(open(f, errors='ignore').read())
            i = 0; n = len(t)
            toks = re.findall(r'\{|\}|"[^"]*"|[^\s{}]+', t)
            k = 0
            while k < len(toks):
                name = toks[k]; k += 1
                if k >= len(toks) or toks[k] != '{':
                    continue
                k += 1; depth = 1; body = []
                while k < len(toks) and depth:
                    if toks[k] == '{': depth += 1
                    elif toks[k] == '}': depth -= 1
                    body.append(toks[k]); k += 1
                out[name.lower()] = shader_info(body)
    return out


def shader_info(body):
    info = {'img': None, 'blend': None, 'alpha': False, 'sky': None, 'nodraw': False, 'editor': None,
            'nolm': False, 'scroll': None}
    # split stages
    depth = 0; stage = None; stages = []; top = []
    for tkn in body:
        if tkn == '{':
            depth += 1; stage = []; continue
        if tkn == '}':
            depth -= 1
            if depth == 0 and stage is not None: stages.append(stage); stage = None
            continue
        (stage if depth == 1 and stage is not None else top).append(tkn)
    tl = [x.lower() for x in top]
    for i, x in enumerate(tl):
        if x == 'surfaceparm' and i + 1 < len(tl):
            p = tl[i + 1]
            if p in ('nodraw', 'fog'): info['nodraw'] = True
            if p == 'sky': info['sky'] = info['sky'] or ''
            if p == 'nolightmap': info['nolm'] = True
        if x == 'skyparms' and i + 1 < len(tl): info['sky'] = top[i + 1]
        if x == 'qer_editorimage' and i + 1 < len(tl): info['editor'] = top[i + 1]
    has_lm = any('$lightmap' in [x.lower() for x in st] for st in stages)
    filter_only = False
    for st in stages:
        sl = [x.lower() for x in st]
        img = None
        for i, x in enumerate(sl):
            if x in ('map', 'clampmap') and i + 1 < len(sl) and not sl[i + 1].startswith('$'): img = st[i + 1]
            if x == 'animmap' and i + 2 < len(sl): img = st[i + 2]
        if img is None:
            continue
        bf = None
        if 'blendfunc' in sl:
            j = sl.index('blendfunc'); a = sl[j + 1]
            if a in ('add', 'gl_one') and (a == 'add' or sl[j + 2] == 'gl_one'): bf = 'add'
            elif a in ('blend', 'gl_src_alpha'): bf = 'blend'
            elif a in ('filter', 'gl_dst_color', 'gl_zero'): bf = 'filter'
            else: bf = 'blend'
        if 'tcmod' in sl:
            j = sl.index('tcmod')
            if sl[j + 1] == 'scroll':
                try: info['scroll'] = [float(st[j + 2]), float(st[j + 3])]
                except Exception: pass
        if info['img'] is None or (bf in (None, 'filter') and info['blend'] not in (None, 'filter')):
            info['img'] = img
            info['blend'] = None if bf == 'filter' else bf
            if 'alphafunc' in sl: info['alpha'] = True
            if bf == 'filter': info['blend'] = None
            filter_only = (bf == 'filter' and not has_lm)
            info['tint'] = None
            if 'rgbgen' in sl:                  # rgbGen const ( r g b ): dims additive glass, spray...
                j = sl.index('rgbgen')
                if sl[j + 1] == 'const':
                    try: info['tint'] = [float(v) for v in st[j + 2:j + 7] if v not in ('(', ')')][:3]
                    except Exception: pass
    if filter_only and info['blend'] is None: info['blend'] = 'blend'      # tinted glass: see through it
    return info


def find_image(name, vfs):
    base = re.sub(r'\.(tga|jpg|jpeg|png)$', '', name, flags=re.I)
    for d in reversed(vfs):
        for ext in ('.png', '.tga', '.jpg', '.jpeg', '.TGA', '.JPG', '.PNG'):
            p = os.path.join(d, base + ext)
            if os.path.exists(p):
                return p
        # case-insensitive fallback
        dd = os.path.join(d, os.path.dirname(base))
        if os.path.isdir(dd):
            bn = os.path.basename(base).lower()
            for f in os.listdir(dd):
                if os.path.splitext(f)[0].lower() == bn and f.lower().endswith(('.png', '.tga', '.jpg', '.jpeg')):
                    return os.path.join(dd, f)
    return None


def load_img(path, size):
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        return None
    alpha = im.mode in ('RGBA', 'LA', 'P') and 'A' in im.convert('RGBA').getbands()
    im = im.convert('RGBA')
    if alpha and np.asarray(im)[..., 3].min() == 255: alpha = False
    w, h = im.size
    s = min(1.0, size / max(w, h))
    if s < 1: im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    if alpha: im.save(buf, 'PNG', optimize=True); mime = 'image/png'
    else: im.convert('RGB').save(buf, 'JPEG', quality=82); mime = 'image/jpeg'
    return f'data:{mime};base64,' + base64.b64encode(buf.getvalue()).decode()


def avg_color(path):
    try:
        im = Image.open(path).convert('RGB').resize((8, 8))
        return [int(v) for v in np.asarray(im).reshape(-1, 3).mean(0)]
    except Exception:
        return [128, 128, 128]


# ------------------------------------------------------------------ patches
def bezier_patch(ctrl, w, h, sub=6):
    """ctrl: (h, w, F) control grid of 3x3 quadratic patches -> verts (N,F), tris"""
    out_rows = []
    pw, ph = (w - 1) // 2, (h - 1) // 2
    t = np.linspace(0, 1, sub + 1)
    B = np.stack([(1 - t) ** 2, 2 * t * (1 - t), t ** 2], 1)  # (sub+1, 3)
    W = pw * sub + 1; H = ph * sub + 1
    grid = np.zeros((H, W, ctrl.shape[2]), np.float32)
    for py in range(ph):
        for px in range(pw):
            c = ctrl[py * 2:py * 2 + 3, px * 2:px * 2 + 3]  # (3,3,F)
            pts = np.einsum('ia,jb,abf->ijf', B, B, c)
            grid[py * sub:py * sub + sub + 1, px * sub:px * sub + sub + 1] = pts
    verts = grid.reshape(-1, ctrl.shape[2])
    tris = []
    for y in range(H - 1):
        for x in range(W - 1):
            a = y * W + x; b = a + 1; c = a + W; d = c + 1
            tris += [a, c, b, b, c, d]
    return verts, np.array(tris, np.int64)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bsp'); ap.add_argument('out')
    ap.add_argument('--vfs', action='append', default=[])
    ap.add_argument('--three', default=None)
    ap.add_argument('--threeurl', default=None)
    ap.add_argument('--sky', default=None)
    ap.add_argument('--texsize', type=int, default=256)
    ap.add_argument('--title', default=None)
    ap.add_argument('--markers', type=int, default=1)
    ap.add_argument('--sub', default='Compiled BSP preview')
    ap.add_argument('--style', default=None, help='CSS file appended after the built-in style (palette/type overrides)')
    ap.add_argument('--views', default='', help='"Name:x,y,z,yaw,pitch;Name2:..." camera buttons (first = start view)')
    ap.add_argument('--fog', default=None, help='"r,g,b,dist": distance fog (Q3 fogparms colour + distance to opaque), e.g. for a map inside a fog volume')
    a = ap.parse_args()

    ents, shaders, dv, di, surfs, lms, bmodels = read_bsp(a.bsp)
    ent_list = parse_entities(ents)
    shinfo = parse_shaders(a.vfs)
    # lightmap atlas
    n = max(1, len(lms)); cols = int(np.ceil(np.sqrt(n))); rows = int(np.ceil(n / cols))
    atlas = np.full((rows * 128, cols * 128, 3), 255, np.uint8)
    for i, lm in enumerate(lms):
        atlas[(i // cols) * 128:(i // cols + 1) * 128, (i % cols) * 128:(i % cols + 1) * 128] = lm
    buf = io.BytesIO(); Image.fromarray(atlas).save(buf, 'PNG', optimize=True)
    atlas_url = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    # brush models (*1, *2 ...) with an origin brush are stored around (0,0,0); place them at the entity origin
    surf_off = np.zeros((len(surfs), 3), np.float32)
    for e in ent_list:
        m = e.get('model', '')
        if m.startswith('*') and e.get('origin'):
            try:
                k = int(m[1:]); o = np.array([float(v) for v in e['origin'].split()], np.float32)
                md = read_bsp.models[k]; surf_off[md['fs']:md['fs'] + md['ns']] = o
            except Exception:
                pass

    # func_bobbing movers: their surfaces get their own groups and bob in the page (Q3 TR_SINE: base + h*sin(2pi(t/T + phase)))
    surf_anim = {}; anims = []
    for e in ent_list:
        m = e.get('model', '')
        if e.get('classname') == 'func_bobbing' and m.startswith('*'):
            try:
                k = int(m[1:]); md = read_bsp.models[k]
            except Exception:
                continue
            sf = int(e.get('spawnflags', 0) or 0)
            ax = 0 if sf & 1 else (1 if sf & 2 else 2)
            anims.append({'axis': ax, 'h': float(e.get('height', 32)), 'T': float(e.get('speed', 4)), 'ph': float(e.get('phase', 0))})
            for si in range(md['fs'], md['fs'] + md['ns']): surf_anim[si] = len(anims) - 1

    groups = {}   # (shader, lit, anim) -> lists
    sky_name = a.sky
    for si, s in enumerate(surfs):
        sname = shaders[s['shader']][0]
        info = shinfo.get(sname.lower(), {})
        if info.get('nodraw') or sname.lower().startswith(('textures/common/', 'noshader')) or s['type'] == 4:
            continue
        if info.get('sky') is not None:
            if not sky_name and info.get('sky'): sky_name = info['sky']
            continue
        if s['type'] == 2:
            fv, nv = s['fv'], s['nv']; w, h = s['pw'], s['ph']
            V = dv[fv:fv + nv]
            ctrl = np.concatenate([V['xyz'], V['st'], V['lm'], V['c'].astype(np.float32)], 1).reshape(h, w, -1)
            verts, tris = bezier_patch(ctrl, w, h)
            xyz, st, lmst, col = verts[:, :3], verts[:, 3:5], verts[:, 5:7], np.clip(verts[:, 7:11], 0, 255)
        else:
            fv, nv, fi, ni = s['fv'], s['nv'], s['fi'], s['ni']
            V = dv[fv:fv + nv]
            xyz, st, lmst, col = V['xyz'], V['st'], V['lm'], V['c'].astype(np.float32)
            tris = di[fi:fi + ni].astype(np.int64)
        if surf_off[si].any(): xyz = np.asarray(xyz, np.float32) + surf_off[si]   # (an ndarray: 'si in surf_off' tested values)
        lmn = int(s['lm'])
        if lmn >= 0:
            li = lmn; ax = (li % cols) * 128; ay = (li // cols) * 128
            u2 = (ax + lmst[:, 0] * 128) / (cols * 128)
            v2 = (ay + lmst[:, 1] * 128) / (rows * 128)
            lm2 = np.stack([u2, v2], 1)
        else:
            lm2 = np.zeros((len(xyz), 2), np.float32)
        key = (sname, lmn >= 0, surf_anim.get(si, -1))
        g = groups.setdefault(key, {'pos': [], 'uv': [], 'uv2': [], 'col': [], 'idx': [], 'n': 0})
        g['pos'].append(np.asarray(xyz, np.float32)); g['uv'].append(np.asarray(st, np.float32))
        g['uv2'].append(np.asarray(lm2, np.float32)); g['col'].append(np.asarray(col, np.float32)[:, :3])
        g['idx'].append(tris + g['n']); g['n'] += len(xyz)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        import md3tool, iqmtool
    except Exception:
        md3tool = iqmtool = None
    nent_models = 0
    for e in ent_list:
        mp = e.get('model2') or (e.get('model') if e.get('classname') == 'misc_externalmodel' else None)
        if not mp or not md3tool or not e.get('origin'): continue
        f = next((os.path.join(d, mp) for d in reversed(a.vfs) if os.path.exists(os.path.join(d, mp))), None)
        if not f: continue
        try: md = iqmtool.load(f) if f.lower().endswith('.iqm') else md3tool.load(f)
        except Exception: continue
        o = np.array([float(v) for v in e['origin'].split()], np.float32)
        if 'angles' in e: yaw = float(e['angles'].split()[1])
        else: yaw = float(e.get('angle', 0))
        c, sn = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        R = np.array([[c, sn, 0], [-sn, c, 0], [0, 0, 1]], np.float32)
        anim = -1
        if e.get('classname') == 'func_rotating':      # spins round its origin (Z axis unless spawnflags say X / Y)
            sf = int(e.get('spawnflags', 0) or 0)
            anims.append({'type': 'rot', 'speed': float(e.get('speed', 100)), 'axis': 0 if sf & 4 else (1 if sf & 8 else 2),
                          'pivot': [float(o[0]), float(o[2]), float(-o[1])]})
            anim = len(anims) - 1
        for srf in md['surfaces']:
            sname = srf['shader'] or ''
            key = (sname, False, anim)
            g = groups.setdefault(key, {'pos': [], 'uv': [], 'uv2': [], 'col': [], 'idx': [], 'n': 0})
            v = srf['verts'] @ R + (o if anim < 0 else 0)
            g['pos'].append(v.astype(np.float32)); g['uv'].append(srf['st'].astype(np.float32))
            g['uv2'].append(np.zeros((len(v), 2), np.float32)); g['col'].append(np.full((len(v), 3), 118, np.float32))
            g['idx'].append(srf['tris'][:, ::-1].astype(np.int64) + g['n']); g['n'] += len(v)
        nent_models += 1

    blob = io.BytesIO(); meta = []; tex_cache = {}; textures = {}
    missing = set()
    for (sname, lit, anim), g in sorted(groups.items()):
        info = shinfo.get(sname.lower(), {})
        img = info.get('img') or sname
        p = find_image(img, a.vfs) or (find_image(info['editor'], a.vfs) if info.get('editor') else None) or find_image(sname, a.vfs)
        tid = None
        if p:
            if p not in tex_cache:
                url = load_img(p, a.texsize)
                tex_cache[p] = None if url is None else f't{len(textures)}'
                if url: textures[tex_cache[p]] = url
            tid = tex_cache[p]
        if tid is None: missing.add(sname)
        pos = np.concatenate(g['pos']); uv = np.concatenate(g['uv']); uv2 = np.concatenate(g['uv2'])
        col = np.concatenate(g['col']); idx = np.concatenate(g['idx']).astype(np.uint32)
        # q3 (x,y,z) -> three (x, z, -y)
        p3 = np.stack([pos[:, 0], pos[:, 2], -pos[:, 1]], 1).astype(np.float32)
        rec = {'shader': sname, 'lit': bool(lit), 'tex': tid, 'blend': info.get('blend'), 'alpha': bool(info.get('alpha')),
               'scroll': info.get('scroll'), 'tint': info.get('tint'), 'nv': int(len(pos)), 'ni': int(len(idx)),
               'anim': (anim if anim >= 0 else None)}
        for k, arr in (('pos', p3), ('uv', uv.astype(np.float32)), ('uv2', uv2.astype(np.float32)),
                       ('col', (np.clip(col, 0, 255)).astype(np.uint8)), ('idx', idx)):
            while blob.tell() % 4: blob.write(b'\0')
            rec[k] = blob.tell(); blob.write(arr.tobytes())
        meta.append(rec)

    # sky
    sky = None
    if sky_name and sky_name != '-':
        faces = {}
        for sfx in ('rt', 'lf', 'up', 'dn', 'ft', 'bk'):
            p = find_image(f'{sky_name}_{sfx}', a.vfs)
            if p:
                im = Image.open(p).convert('RGB').resize((512, 512))
                if sfx == 'up': im = im.rotate(-90)      # Q3 sky face orientation -> three.js cube faces
                if sfx == 'dn': im = im.rotate(90)
                bb = io.BytesIO(); im.save(bb, 'JPEG', quality=85)
                faces[sfx] = 'data:image/jpeg;base64,' + base64.b64encode(bb.getvalue()).decode()
        if len(faces) == 6: sky = faces

    # entity markers
    marks = []
    if a.markers:
        for e in ent_list:
            c = e.get('classname', ''); o = e.get('origin')
            if not o: continue
            try: x, y, z = (float(v) for v in o.split())
            except Exception: continue
            kind = None
            if c.startswith('weapon_'): kind = 'weapon'
            elif c.startswith('ammo_'): kind = 'ammo'
            elif c.startswith(('item_', 'holdable_')): kind = 'item'
            elif c in ('info_player_deathmatch', 'info_player_start') or c.startswith('team_') and 'player' in c: kind = 'spawn'
            elif c == 'station_health': kind = 'health'
            elif c == 'target_position' or c == 'misc_teleporter_dest': kind = 'target'
            if kind: marks.append([kind, c, x, z, -y])

    data_b64 = base64.b64encode(blob.getvalue()).decode()
    three_tag = (f'<script src="{a.threeurl}"></script>' if a.threeurl else
                 '<script>' + open(a.three).read() + '</script>')
    title = a.title or os.path.splitext(os.path.basename(a.bsp))[0]
    views = []
    for v in filter(None, a.views.split(';')):
        n, c = v.split(':'); views.append([n] + [float(t) for t in c.split(',')])
    html = TEMPLATE.replace('%%THREE%%', three_tag).replace('%%TITLE%%', title).replace('%%SUB%%', a.sub)
    html = html.replace('%%STYLE%%', open(a.style).read() if a.style else '')
    html = html.replace('%%VIEWS%%', '<script>window.__VIEWS=' + json.dumps(views) + ';</script>')
    fog = [float(v) for v in a.fog.split(',')] if a.fog else None
    html = html.replace('%%DATA%%', json.dumps({'meta': meta, 'tex': textures, 'atlas': atlas_url, 'sky': sky, 'anims': anims, 'fog': fog,
                                                 'marks': marks, 'blob': data_b64}))
    open(a.out, 'w').write(html)
    tv = sum(m['nv'] for m in meta); ti = sum(m['ni'] for m in meta) // 3
    print(f'{a.out}: {len(meta)} materials, {tv} verts, {ti} tris, {len(lms)} lightmaps, sky={sky_name}, '
          f'{len(marks)} markers, {nent_models} entity models, {os.path.getsize(a.out) / 1e6:.1f} MB')
    if missing: print('no image for:', ', '.join(sorted(missing)[:40]))


TEMPLATE = r'''<title>%%TITLE%%</title>
<style>
/* one-screen 3D viewer: full-bleed canvas, floating control panel */
:root{--bg:#cfe3f2;--panel:rgba(250,252,255,.9);--fg:#13263a;--mut:#4a6077;--line:#b9cde0;--btn:#e7f0f8;--accent:#0f7ac9;--onaccent:#fff;
 --display:"Baloo 2","Trebuchet MS",sans-serif;--body:"Nunito Sans",system-ui,sans-serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0b1622;--panel:rgba(12,24,38,.86);--fg:#e6f0f8;--mut:#9db3c8;--line:#28415a;--btn:#16283b;--accent:#4fb0f0;--onaccent:#06121d;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0b1622;--panel:rgba(12,24,38,.86);--fg:#e6f0f8;--mut:#9db3c8;--line:#28415a;--btn:#16283b;--accent:#4fb0f0;--onaccent:#06121d;color-scheme:dark}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 var(--body);overflow:hidden}
canvas{display:block;width:100%;height:100%;touch-action:none}
#hud{position:fixed;left:16px;top:calc(16px + env(safe-area-inset-top,0px));max-width:min(360px,calc(100vw - 32px));background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;backdrop-filter:blur(6px)}
#hud h1{font:700 22px/1.1 var(--display);margin:0;letter-spacing:.01em;text-wrap:balance}
#hud .sub{margin:2px 0 8px;color:var(--mut);font-size:12px;letter-spacing:.06em;text-transform:uppercase}
#hud p{margin:6px 0;color:var(--mut);font-size:12px}
#hud .row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
#hud button{background:var(--btn);color:var(--fg);border:1px solid var(--line);border-radius:7px;padding:5px 9px;font:600 12px var(--body);cursor:pointer}
#hud button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
#hud button.on{background:var(--accent);border-color:var(--accent);color:var(--onaccent)}
#hide{float:right;margin-left:8px}
#hud.min .body{display:none}
.lg{display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--mut)}.lg i{width:9px;height:9px;border-radius:50%;display:inline-block;border:1px solid var(--line)}
#pad{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));display:grid;grid-template-columns:repeat(3,44px);gap:6px}
#pad button{height:44px;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:9px;font-size:16px}
@media (hover:hover) and (pointer:fine){#pad{display:none}}
%%STYLE%%
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@700&family=Nunito+Sans:wght@400;600&display=swap">
<div id="hud"><button id="hide" aria-label="Hide panel">&minus;</button><h1>%%TITLE%%</h1><div class="body"><div class="sub">%%SUB%%</div>
<p>Drag to look &middot; WASD or arrows to move &middot; Q/E down/up &middot; Shift for speed</p>
<div class="row" id="views"></div>
<div class="row"><button id="mk" class="on">Item markers</button></div>
<div class="row" id="legend"></div></div></div>
<div id="pad"><span></span><button data-k="w" aria-label="Forward">&#9650;</button><span></span><button data-k="a" aria-label="Left">&#9664;</button><button data-k="s" aria-label="Back">&#9660;</button><button data-k="d" aria-label="Right">&#9654;</button><button data-k="q" aria-label="Down">&darr;</button><span></span><button data-k="e" aria-label="Up">&uarr;</button></div>
%%VIEWS%%
%%THREE%%
<script>
const D = %%DATA%%;
const bin = Uint8Array.from(atob(D.blob), c => c.charCodeAt(0)).buffer;
document.getElementById('hide').onclick=(e)=>{const h=document.getElementById('hud');h.classList.toggle('min');e.target.innerHTML=h.classList.contains('min')?'+':'&minus;';};
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio||1));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = D.fog ? new THREE.Color(D.fog[0], D.fog[1], D.fog[2]) : new THREE.Color(0x8fb6e0);
const camera = new THREE.PerspectiveCamera(80, innerWidth/innerHeight, 4, 40000);
camera.rotation.order = 'YXZ';
const loader = new THREE.TextureLoader();
const texs = {}; let pending = 0, loadedAll = false;
function tex(id){ if(!id) return null; if(texs[id]) return texs[id]; pending++;
  const t = loader.load(D.tex[id], ()=>{ pending--; }, undefined, ()=>{ pending--; });
  t.flipY = false; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.NoColorSpace; t.anisotropy = 4; texs[id]=t; return t; }
pending++; const atlas = loader.load(D.atlas, ()=>{pending--;}); atlas.flipY=false; atlas.colorSpace = THREE.NoColorSpace;
atlas.magFilter = THREE.LinearFilter; atlas.minFilter = THREE.LinearFilter; atlas.generateMipmaps=false;
const white = new THREE.DataTexture(new Uint8Array([255,255,255,255]),1,1); white.needsUpdate = true;
const scrollers = []; const movers = [];
const VS = `attribute vec2 lmuv; attribute vec3 vcol; varying vec2 vUv; varying vec2 vUv2; varying vec3 vCol; varying float vDist;
 uniform vec2 scroll; uniform float time;
 void main(){ vUv = uv + scroll*time; vUv2 = lmuv; vCol = vcol; vec4 mv = modelViewMatrix*vec4(position,1.0); vDist = length(mv.xyz);
  gl_Position = projectionMatrix*mv;} `;
const FS = `uniform sampler2D map; uniform sampler2D lm; uniform float lit; uniform float alphaTest; uniform float opacity; uniform float add; uniform vec3 tint;
 uniform vec4 fog; varying float vDist;
 varying vec2 vUv; varying vec2 vUv2; varying vec3 vCol;
 void main(){ vec4 c = texture2D(map, vUv); if(c.a < alphaTest) discard;
  vec3 light = lit > 0.5 ? texture2D(lm, vUv2).rgb : vCol/255.0;
  vec3 col = add > 0.5 ? c.rgb * tint : c.rgb * min(light*2.0, vec3(1.6));
  col = pow(col, vec3(0.9));
  if (fog.w > 0.0) { float f = clamp(vDist / fog.w, 0.0, 1.0); f = sqrt(f); col = add > 0.5 ? col * (1.0 - f) : mix(col, fog.rgb, f); }
  gl_FragColor = vec4(col, add > 0.5 ? 1.0 : (opacity < 1.0 ? opacity : c.a)); }`;
for (const m of D.meta){
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bin, m.pos, m.nv*3), 3));
  g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(bin, m.uv, m.nv*2), 2));
  g.setAttribute('lmuv', new THREE.BufferAttribute(new Float32Array(bin, m.uv2, m.nv*2), 2));
  g.setAttribute('vcol', new THREE.BufferAttribute(new Uint8Array(bin, m.col, m.nv*3), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(bin, m.idx, m.ni), 1));
  const blend = m.blend; const t = tex(m.tex) || white;
  const u = {map:{value:t}, lm:{value:atlas}, lit:{value:m.lit?1:0}, alphaTest:{value:m.alpha?0.5:0.0},
             opacity:{value: blend==='blend'?0.55:1.0}, add:{value: blend==='add'?1:0}, tint:{value:new THREE.Vector3(...(m.tint||[1,1,1]))}, scroll:{value:new THREE.Vector2(...(m.scroll||[0,0]))}, time:{value:0},
             fog:{value: D.fog ? new THREE.Vector4(...D.fog) : new THREE.Vector4(0,0,0,0)}};
  const mat = new THREE.ShaderMaterial({uniforms:u, vertexShader:VS, fragmentShader:FS, side:THREE.DoubleSide,
     transparent: !!blend, depthWrite: !blend});
  if (blend==='add'){ mat.blending = THREE.AdditiveBlending; }
  if (m.scroll) scrollers.push(u.time);
  const mesh = new THREE.Mesh(g, mat); mesh.frustumCulled = false; if (blend) mesh.renderOrder = 2; scene.add(mesh);
  if (m.anim !== null && m.anim !== undefined){ const an = D.anims[m.anim]; if (an.type==='rot') mesh.position.set(...an.pivot); movers.push([mesh, an]); }
}
if (D.sky){ const L = new THREE.CubeTextureLoader(); pending++;
  const order = ['lf','rt','up','dn','ft','bk'];
  scene.background = L.load(order.map(k=>D.sky[k]), (ct)=>{ pending--; });
}
// markers
const COLORS = {weapon:0xff3b3b, ammo:0xffb020, item:0xb04bff, spawn:0x2ee66b, health:0xffffff, target:0x40c4ff};
const markGroup = new THREE.Group(); scene.add(markGroup);
const geoS = new THREE.OctahedronGeometry(10);
for (const [k,c,x,y,z] of D.marks){ const m = new THREE.Mesh(geoS, new THREE.MeshBasicMaterial({color:COLORS[k], depthTest:false, transparent:true, opacity:.85}));
  m.position.set(x,y,z); m.renderOrder = 5; m.userData = c; markGroup.add(m); }
const lg = document.getElementById('legend');
for (const [k,c] of Object.entries(COLORS)) lg.insertAdjacentHTML('beforeend', `<span class="lg"><i style="background:#${c.toString(16).padStart(6,'0')}"></i>${k}</span>`);
document.getElementById('mk').onclick = (e)=>{ markGroup.visible = !markGroup.visible; e.target.classList.toggle('on', markGroup.visible); };
// camera control (q3 coords helper)
let yaw = 0, pitch = 0; const keys = {};
window.__setView = (x,y,z,yw,pt)=>{ camera.position.set(x, z, -y); yaw = yw*Math.PI/180; pitch = pt*Math.PI/180; apply(); };
function apply(){ camera.rotation.set(pitch, yaw - Math.PI/2, 0); }
window.__ready = ()=> pending===0;
window.__render = ()=>{ renderer.render(scene, camera); return true; };
window.__markers = (v)=>{ markGroup.visible = v; };
const VIEWS = window.__VIEWS || [];
const vdiv = document.getElementById('views');
VIEWS.forEach(v=>{ const b=document.createElement('button'); b.textContent=v[0]; b.onclick=()=>window.__setView(...v.slice(1)); vdiv.appendChild(b); });
if (VIEWS.length) window.__setView(...VIEWS[0].slice(1)); else window.__setView(0,0,600,0,-20);
let drag=null;
renderer.domElement.addEventListener('pointerdown', e=>{ drag=[e.clientX,e.clientY]; renderer.domElement.setPointerCapture(e.pointerId); });
renderer.domElement.addEventListener('pointermove', e=>{ if(!drag) return; yaw -= (e.clientX-drag[0])*0.004; pitch -= (e.clientY-drag[1])*0.004;
  pitch = Math.max(-1.5, Math.min(1.5, pitch)); drag=[e.clientX,e.clientY]; apply(); });
renderer.domElement.addEventListener('pointerup', ()=> drag=null);
addEventListener('keydown', e=>{ keys[e.key.toLowerCase()] = true; }); addEventListener('keyup', e=>{ keys[e.key.toLowerCase()] = false; });
document.querySelectorAll('#pad button').forEach(b=>{ const k=b.dataset.k;
  b.addEventListener('pointerdown', ()=>keys[k]=true); b.addEventListener('pointerup', ()=>keys[k]=false); b.addEventListener('pointerleave', ()=>keys[k]=false); });
addEventListener('resize', ()=>{ camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
let last = performance.now();
function loop(now){ const dt = Math.min(0.05, (now-last)/1000); last = now;
  for (const [mesh, a] of movers){
    if (a.type==='rot'){ const ang = a.speed*Math.PI/180*now/1000; if (a.axis===2) mesh.rotation.y = ang; else if (a.axis===0) mesh.rotation.x = ang; else mesh.rotation.z = -ang; continue; }
    const d = a.h*Math.sin(2*Math.PI*(now/1000/a.T + a.ph));
    if (a.axis===0) mesh.position.x = d; else if (a.axis===1) mesh.position.z = -d; else mesh.position.y = d; }
  const sp = (keys['shift']?1600:600)*dt; const f = new THREE.Vector3(); camera.getWorldDirection(f);
  const r = new THREE.Vector3().crossVectors(f, camera.up).normalize();
  if (keys['w']||keys['arrowup']) camera.position.addScaledVector(f, sp);
  if (keys['s']||keys['arrowdown']) camera.position.addScaledVector(f, -sp);
  if (keys['d']||keys['arrowright']) camera.position.addScaledVector(r, sp);
  if (keys['a']||keys['arrowleft']) camera.position.addScaledVector(r, -sp);
  if (keys['e']) camera.position.y += sp; if (keys['q']) camera.position.y -= sp;
  for (const t of scrollers) t.value = now/1000;
  renderer.render(scene, camera); requestAnimationFrame(loop); }
requestAnimationFrame(loop);
</script>'''

if __name__ == '__main__':
    main()
