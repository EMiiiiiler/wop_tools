#!/usr/bin/env python3
"""Replace Git LFS pointer stubs in a shallow WoP checkout with the real files.

    python3 lfs_fetch.py <wop repo root> <path or glob relative to the repo root> [...] [-j 8]

The WoP repo keeps its binary assets in LFS and the cloud session's anonymous git lane does not serve LFS
objects (clone with GIT_LFS_SKIP_SMUDGE=1). Each stub is fetched from
https://media.githubusercontent.com/media/PadWorld-Entertainment/worldofpadman/main/<path>.
Globs may use ** (e.g. 'wop/models.pk3dir/models/mapobjects/pad_ddmix/jail/*').
A model path without extension also pulls its sibling textures (.tga/.jpg/.png in the same folder).

    python3 lfs_fetch.py <wop repo root> --map maps/mymap.map

pulls everything a map needs from WoP: every misc_model / model2 md3, the images its surfaces' shaders use
(resolved through wop/scripts.pk3dir/scripts/*.shader, so textures stored elsewhere are found too) and the
skybox of every skyparms in the map folder's own shaders.
"""
import sys, os, re, glob, argparse, urllib.request, concurrent.futures as cf

BASE = 'https://media.githubusercontent.com/media/PadWorld-Entertainment/worldofpadman/main/'


def is_stub(p):
    try:
        if os.path.getsize(p) > 400: return False
        with open(p, 'rb') as f: return f.read(40).startswith(b'version https://git-lfs')
    except OSError:
        return False


def fetch(root, rel):
    url = BASE + urllib.request.quote(rel)
    dst = os.path.join(root, rel)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: data = r.read()
            if data.startswith(b'version https://git-lfs'): return rel, 'still a stub'
            tmp = dst + '.part'
            open(tmp, 'wb').write(data); os.replace(tmp, dst)
            return rel, len(data)
        except Exception as e:  # noqa
            err = str(e)
    return rel, 'FAILED ' + err


PK3DIRS = ('models.pk3dir', 'textures.pk3dir', 'gfx.pk3dir', 'mappack.pk3dir', 'padpack.pk3dir')


def shader_images(root):
    """shader name (lower) -> list of image paths it references (without extension)"""
    out = {}
    for fn in glob.glob(os.path.join(root, 'wop', 'scripts.pk3dir', 'scripts', '*.shader')):
        txt = re.sub(r'//[^\n]*', '', open(fn, errors='ignore').read())
        depth = 0; name = None
        for m in re.finditer(r'\{|\}|[^\s{}][^\n{}]*', txt):
            t = m.group(0).strip()
            if t == '{': depth += 1; continue
            if t == '}':
                depth -= 1
                if depth == 0: name = None
                continue
            if depth == 0: name = t.lower(); out.setdefault(name, []); continue
            w = t.split()
            if not w or name is None: continue
            k = w[0].lower()
            if k in ('map', 'clampmap', 'qer_editorimage', 'q3map_lightimage') and len(w) > 1 and not w[1].startswith('$'):
                out[name].append(os.path.splitext(w[1])[0])
            elif k == 'animmap':
                out[name] += [os.path.splitext(x)[0] for x in w[2:]]
            elif k == 'skyparms' and w[1] != '-':
                out[name] += [w[1] + '_' + f for f in ('bk', 'dn', 'ft', 'lf', 'rt', 'up')]
    return out


def find_image(root, img):
    for d in PK3DIRS:
        for ext in ('.tga', '.jpg', '.png', '.TGA', '.JPG'):
            p = os.path.join(root, 'wop', d, img + ext)
            if os.path.exists(p): return p
    return None


def map_needs(root, mapfile):
    """files under root that the map needs: md3s, their textures (via shaders), sky boxes"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import md3tool
    txt = open(mapfile, errors='ignore').read()
    models = sorted(set(re.findall(r'"model2?"\s+"([^"*][^"]*\.md3)"', txt, re.I)))
    need = []
    for m in models:
        p = os.path.join(root, 'wop', 'models.pk3dir', m)
        if os.path.exists(p): need.append(p)
    # md3s first (shader names live inside them)
    fetch_all(root, need)
    shaders = shader_images(root)
    imgs = set()
    for m in models:
        p = os.path.join(root, 'wop', 'models.pk3dir', m)
        try:
            for s in md3tool.load(p)['surfaces']:
                sh = os.path.splitext(s['shader'])[0]
                imgs.update(shaders.get(sh.lower(), []) or [sh])
        except Exception as e:  # noqa
            print('cannot read', m, e)
    # skies referenced by the map folder's shaders
    mdir = os.path.dirname(os.path.dirname(os.path.abspath(mapfile)))
    for fn in glob.glob(os.path.join(mdir, 'scripts', '*.shader')):
        for sky in re.findall(r'skyparms\s+(\S+)', open(fn, errors='ignore').read()):
            if sky != '-': imgs.update(sky + '_' + f for f in ('bk', 'dn', 'ft', 'lf', 'rt', 'up'))
    out = []
    for i in imgs:
        f = find_image(root, i)
        if f: out.append(f)
        else: print('image not found:', i)
    return out


def fetch_all(root, files, j=8):
    todo = sorted({os.path.relpath(t, root) for t in files if is_stub(t)})
    print(len(todo), 'stubs to fetch')
    bad = 0
    with cf.ThreadPoolExecutor(j) as ex:
        for rel, res in ex.map(lambda r: fetch(root, r), todo):
            if not isinstance(res, int): bad += 1; print(rel, res)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('paths', nargs='*'); ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--map', help='fetch everything this .map needs')
    a = ap.parse_args()
    if a.map:
        bad = fetch_all(a.root, map_needs(a.root, a.map), a.j)
        print('done,', bad, 'failed'); sys.exit(1 if bad else 0)
    todo = []
    for p in a.paths:
        hits = glob.glob(os.path.join(a.root, p), recursive=True)
        if not hits and not os.path.splitext(p)[1]:
            hits = glob.glob(os.path.join(a.root, p + '.*'))
        for h in hits:
            if os.path.isdir(h): continue
            todo.append(h)
            if h.lower().endswith('.md3'):        # textures next to the model
                d = os.path.dirname(h)
                todo += [x for x in glob.glob(os.path.join(d, '*')) if x.lower().endswith(('.tga', '.jpg', '.png'))]
    todo = sorted({os.path.relpath(t, a.root) for t in todo if is_stub(t)})
    print(len(todo), 'stubs to fetch')
    bad = 0
    with cf.ThreadPoolExecutor(a.j) as ex:
        for rel, res in ex.map(lambda r: fetch(a.root, r), todo):
            if not isinstance(res, int): bad += 1; print(rel, res)
    print('done,', bad, 'failed')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
