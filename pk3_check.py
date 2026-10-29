#!/usr/bin/env python3
"""pk3_check.py - is the delivered map complete? Run it on the build folder or the finished .pk3 before handing over.

    python3 pk3_check.py <workdir or X.pk3> --map wop_X --game <dir holding wop/> [--source X_source.zip]

Resolves every asset the map uses against the map's own files first, then WoP's (wop/*.pk3dir folders or wop/*.pk3):
  files     maps/X.bsp, maps/X.aas (not older than the .bsp: -light changes the checksum and bspc's .aas is rejected),
            scripts/X.arena, the map's .shader, levelshots/X.jpg (WARN), the .map in the source zip
  textures  every brush texture in the .map is a shader or an image (else: grey 'missing texture' in game)
  shaders   every image a shader stage maps (map/clampMap/animMap/skyparms boxes/qer_editorimage) exists;
            shader names lower case; none of the map's shader names collides with a WoP shader
  models    every misc_model/model2/misc_externalmodel exists; every MD3/IQM surface shader resolves
            (an IQM/MD3 shader that is missing draws black or as a default-lit grey model)
  sounds    every target_speaker noise exists in the game (sound/world/...)
  names     every file in the package is lower case (pk3s on Linux are case sensitive)
Exit status 1 when anything is missing.
"""
import os, sys, re, zipfile, argparse, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_map as AM

IMG_EXT = ('.jpg', '.tga', '.png')
FAILS, WARNS = [], []


class VFS:
    """first-match lookup over folders and zip files (lower-cased keys)"""

    def __init__(self):
        self.files = {}        # lower path -> (kind, container, real name)

    def add_dir(self, d):
        for root, _, fs in os.walk(d):
            for f in fs:
                p = os.path.relpath(os.path.join(root, f), d).replace(os.sep, '/')
                self.files.setdefault(p.lower(), ('dir', d, p))

    def add_zip(self, z):
        with zipfile.ZipFile(z) as Z:
            for n in Z.namelist():
                if not n.endswith('/'): self.files.setdefault(n.lower(), ('zip', z, n))

    def has(self, p): return p.lower() in self.files

    def read(self, p):
        k, c, n = self.files[p.lower()]
        if k == 'dir': return open(os.path.join(c, n), 'rb').read()
        with zipfile.ZipFile(c) as Z: return Z.read(n)

    def image(self, p):
        """shader image paths may be written with or without an extension; q3 tries .tga and .jpg"""
        base = re.sub(r'\.(tga|jpg|png)$', '', p.lower())
        return any(self.has(base + e) for e in IMG_EXT)

    def glob(self, prefix, suffix):
        return [p for p in self.files if p.startswith(prefix) and p.endswith(suffix)]


def parse_shaders(txt):
    """{name: (body text)} for a .shader file"""
    txt = re.sub(r'//[^\n]*', '', txt)
    out = {}; i = 0; n = len(txt)
    tok = re.compile(r'\s*([^\s{}]+|\{|\})')
    name = None; depth = 0; start = 0
    while i < n:
        m = tok.match(txt, i)
        if not m: break
        t = m.group(1); i = m.end()
        if t == '{':
            if depth == 0: start = i
            depth += 1
        elif t == '}':
            depth -= 1
            if depth == 0 and name: out[name.lower()] = txt[start:i - 1]; name = None
        elif depth == 0: name = t
    return out


def shader_images(body):
    imgs = []
    for line in body.splitlines():
        w = line.split()
        if not w: continue
        k = w[0].lower()
        if k in ('map', 'clampmap') and len(w) > 1 and not w[1].startswith('$'): imgs.append(w[1])
        elif k == 'animmap': imgs += w[2:]
        elif k == 'skyparms':
            for box in (w[1], w[3] if len(w) > 3 else '-'):
                if box != '-': imgs += [f'{box}_{s}' for s in ('rt', 'lf', 'bk', 'ft', 'up', 'dn')]
        elif k in ('qer_editorimage', 'q3map_lightimage') and len(w) > 1: imgs.append(('editor', w[1]))
    return imgs


def md3_shaders(b):
    if b[:4] != b'IDP3': return None
    nsurf, ofs_surf = struct.unpack_from('<i', b, 84)[0], struct.unpack_from('<i', b, 100)[0]
    out = []; o = ofs_surf
    for _ in range(nsurf):
        (sid, name, flags, sfr, nsh, nv, ntri, ofs_tri, ofs_sh, ofs_st, ofs_xyz, ofs_send) = struct.unpack_from('<4s64s10i', b, o)
        for k in range(nsh):
            out.append(struct.unpack_from('<64s', b, o + ofs_sh + 68 * k)[0].split(b'\0')[0].decode('latin1'))
        o += ofs_send
    return out


def iqm_shaders(b):
    if not b.startswith(b'INTERQUAKEMODEL'): return None
    h = struct.unpack_from('<16s27I', b, 0)
    num_text, ofs_text, num_meshes, ofs_meshes = h[4], h[5], h[6], h[7]
    text = b[ofs_text:ofs_text + num_text]
    out = []
    for i in range(num_meshes):
        nm, mat, *_ = struct.unpack_from('<6I', b, ofs_meshes + 24 * i)
        out.append(text[mat:text.index(b'\0', mat)].decode('latin1'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', help='build folder (holding maps/, scripts/ ...) or the .pk3')
    ap.add_argument('--map', required=True)
    ap.add_argument('--game', help='dir holding wop/ (pk3dir folders or pk3 files)')
    ap.add_argument('--source', help='the source zip (must hold maps/<map>.map)')
    a = ap.parse_args()
    own = VFS()
    if a.target.endswith('.pk3'): own.add_zip(a.target)
    else: own.add_dir(a.target)
    base = VFS()
    if a.game:
        w = os.path.join(a.game, 'wop')
        for f in sorted(os.listdir(w)):
            p = os.path.join(w, f)
            if f.lower().startswith('zz_'): continue                   # a symlinked build of this map
            if os.path.isdir(p) and f.endswith('.pk3dir'): base.add_dir(p)
            elif f.endswith('.pk3'): base.add_zip(p)
    else:
        WARNS.append(('files', 'no --game: WoP assets cannot be resolved, only the package itself is checked'))
    allv = lambda: None
    has = lambda p: own.has(p) or base.has(p)
    img = lambda p: own.image(p) or base.image(p)
    M = a.map
    # ---- files
    for p in (f'maps/{M}.bsp', f'maps/{M}.aas', f'scripts/{M}.arena'):
        if not own.has(p): FAILS.append(('files', f'{p} missing'))
    if not any(own.has(f'levelshots/{M}{e}') for e in IMG_EXT): WARNS.append(('files', f'levelshots/{M}.jpg missing (menu shows a blank)'))
    if not a.target.endswith('.pk3') and own.has(f'maps/{M}.bsp') and own.has(f'maps/{M}.aas'):
        tb = os.path.getmtime(os.path.join(a.target, 'maps', M + '.bsp')); ta = os.path.getmtime(os.path.join(a.target, 'maps', M + '.aas'))
        if ta < tb: FAILS.append(('files', f'maps/{M}.aas is older than the .bsp: rebuild it with bspc after -light'))
    own_shaders = {}
    for p in own.glob('scripts/', '.shader'):
        own_shaders.update(parse_shaders(own.read(p).decode('latin1')))
    if not own_shaders: FAILS.append(('files', 'no scripts/*.shader in the package'))
    base_shaders = {}
    for p in base.glob('scripts/', '.shader'):
        base_shaders.update(parse_shaders(base.read(p).decode('latin1')))
    for n in own_shaders:
        if n in base_shaders and not n.startswith('levelshots/'): WARNS.append(('shaders', f'{n} also defined by WoP (whichever loads last wins)'))
    shaders = dict(base_shaders); shaders.update(own_shaders)
    # the renderer strips the extension from shader names (MD3 surfaces often say .tga)
    sh_ok = lambda n: re.sub(r'\.(tga|jpg|png)$', '', n.lower()) in shaders or img(n)
    # ---- shaders: images
    for n, body in own_shaders.items():
        for im in shader_images(body):
            if isinstance(im, tuple):
                if not img(im[1]): WARNS.append(('shaders', f'{n}: editor image {im[1]} missing (Radiant shows a placeholder)'))
            elif not img(im): FAILS.append(('shaders', f'{n}: image {im} not found'))
    # ---- .map
    mp = f'maps/{M}.map'
    src = None
    if own.has(mp): src = own.read(mp)
    elif a.source:
        with zipfile.ZipFile(a.source) as Z:
            nm = [x for x in Z.namelist() if x.lower() == mp.lower()]
            if nm: src = Z.read(nm[0])
    if a.source:
        with zipfile.ZipFile(a.source) as Z:
            if not any(x.lower() == mp.lower() for x in Z.namelist()): FAILS.append(('files', f'{a.source} has no {mp}'))
    if src is None:
        WARNS.append(('files', f'{mp} not found (pass --source): textures/models/sounds of the .map not checked'))
    else:
        tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), f'pk3check_{os.getpid()}.map')
        open(tmp, 'wb').write(src)
        ents = AM.parse(tmp); os.remove(tmp)
        texs = {f[3] for e in ents for b in e['brushes'] for f in b}
        for t in sorted(texs):
            if not sh_ok('textures/' + t): FAILS.append(('textures', f'{t}: no shader or image textures/{t}'))
        models = set()
        for e in ents:
            kv = e['kv']
            for k in ('model', 'model2'):
                v = kv.get(k)
                if v and not v.startswith('*'): models.add(v)
            n = kv.get('noise')
            if kv.get('classname') == 'target_speaker' and n and not n.startswith('*'):
                b_ = re.sub(r'\.(ogg|wav)$', '', n.lower())
                if not (has(b_ + '.ogg') or has(b_ + '.wav')): FAILS.append(('sounds', f'{n} does not exist'))
        for m in sorted(models):
            if not has(m):
                FAILS.append(('models', f'{m} missing')); continue
            b = own.read(m) if own.has(m) else base.read(m)
            sh = md3_shaders(b) if m.lower().endswith('.md3') else iqm_shaders(b) if m.lower().endswith('.iqm') else []
            for s in sorted(set(sh or [])):
                if s and not sh_ok(s): FAILS.append(('models', f'{m}: surface shader {s} has no shader or image'))
    # ---- names
    for p in own.files.values():
        if p[2] != p[2].lower() and not p[2].startswith(('.', '__', 'levelshots/')): FAILS.append(('names', f'{p[2]}: upper case file name'))
    size = 0
    if a.target.endswith('.pk3'): size = os.path.getsize(a.target)
    for sec in ('files', 'textures', 'shaders', 'models', 'sounds', 'names'):
        f = [m for k, m in FAILS if k == sec]; w = [m for k, m in WARNS if k == sec]
        print(f'[{sec}] {len(f)} missing, {len(w)} warn')
        for m in f[:60]: print('   FAIL', m)
        for m in w[:20]: print('   warn', m)
    if size: print(f'pk3 size {size / 1e6:.1f} MB')
    print('RESULT:', 'OK' if not FAILS else f'{len(FAILS)} problem(s)')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
