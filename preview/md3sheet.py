#!/usr/bin/env python3
"""Contact sheet of several MD3 models (all surfaces, real shaders' images), rendered headless to a PNG.

    python3 preview/md3sheet.py out.png --vfs <dir with scripts/ + models/> [--vfs ...] [--three three.min.js]
                                model1.md3 model2.md3 ... [--cols 4] [--size 360] [--yaw 35] [--pitch 22]

Each model gets its own cell, framed on its bounding box, lit by a warm key light + cool fill (no lightmaps), so
the shapes, normals and texture mapping can be judged before the model goes into a map. Uses the same shader
parsing as bsp2scene.py (first image stage of each shader; alpha-tested images keep their cut-outs).
"""
import os, sys, json, argparse, asyncio, base64, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import md3tool
import bsp2scene as B

PAGE = r'''<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#2d3238}canvas{display:block}</style><body></body>
<script>__THREE__</script><script>
const D = __DATA__;
const W = D.cols * D.size, H = Math.ceil(D.models.length / D.cols) * D.size;
const R = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); R.setSize(W, H); R.setScissorTest(true);
document.body.appendChild(R.domElement);
const TL = new THREE.TextureLoader(); const texc = {};
function tex(u){ if(!u) return null; if(!texc[u]){ const t = TL.load(u); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; texc[u] = t;} return texc[u]; }
const scenes = D.models.map((m, i) => {
  const S = new THREE.Scene(); S.background = new THREE.Color(0x2d3238);
  S.add(new THREE.HemisphereLight(0xdfe8ff, 0x403830, 1.2));
  const k = new THREE.DirectionalLight(0xfff0dd, 2.2); k.position.set(-0.6, -1, 1.4); S.add(k);
  const f = new THREE.DirectionalLight(0x9fb8ff, 0.7); f.position.set(1, 0.8, 0.4); S.add(f);
  for (const s of m.surfs) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(s.v, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(s.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(s.uv, 2));
    g.setIndex(s.i);
    const mat = new THREE.MeshStandardMaterial({map: tex(s.img), color: s.img ? 0xffffff : new THREE.Color(s.col), roughness: 0.75,
      metalness: 0.0, side: THREE.DoubleSide, transparent: !!s.blend, opacity: s.blend ? 0.55 : 1, alphaTest: s.alpha ? 0.5 : 0,
      emissive: s.glow ? 0xffffff : 0x000000, emissiveMap: s.glow ? tex(s.img) : null, emissiveIntensity: s.glow ? 0.9 : 0});
    S.add(new THREE.Mesh(g, mat));
  }
  const [mn, mx] = m.bounds; const c = mn.map((v, j) => (v + mx[j]) / 2);
  const rad = Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) / 2;
  const cam = new THREE.PerspectiveCamera(32, 1, rad / 50, rad * 50); cam.up.set(0, 0, 1);
  const yaw = (D.yaw - 90) * Math.PI / 180, pit = D.pitch * Math.PI / 180, dist = rad / Math.sin(16 * Math.PI / 180) * 1.05;
  cam.position.set(c[0] + dist * Math.cos(pit) * Math.cos(yaw), c[1] + dist * Math.cos(pit) * Math.sin(yaw), c[2] + dist * Math.sin(pit));
  cam.lookAt(c[0], c[1], c[2]);
  return {S, cam, i};
});
function draw(){
  for (const {S, cam, i} of scenes) {
    const x = (i % D.cols) * D.size, y = H - (Math.floor(i / D.cols) + 1) * D.size;
    R.setViewport(x, y, D.size, D.size); R.setScissor(x, y, D.size, D.size); R.render(S, cam);
  }
}
let n = 0; (function loop(){ draw(); if (++n < 30) setTimeout(loop, 50); else document.title = 'ready'; })();
</script>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('models', nargs='+')
    ap.add_argument('--vfs', action='append', default=[]); ap.add_argument('--three', default=None)
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--size', type=int, default=360)
    ap.add_argument('--yaw', type=float, default=35); ap.add_argument('--pitch', type=float, default=22)
    a = ap.parse_args()
    sh = B.parse_shaders(a.vfs)
    data = {'cols': min(a.cols, len(a.models)), 'size': a.size, 'yaw': a.yaw, 'pitch': a.pitch, 'models': []}
    for mp in a.models:
        m = md3tool.load(mp)
        surfs = []; allv = []
        for s in m['surfaces']:
            info = sh.get(os.path.splitext(s['shader'])[0].lower(), {})
            img = info.get('img') or info.get('editor') or os.path.splitext(s['shader'])[0]
            f = B.find_image(img, a.vfs) if img else None
            url = B.load_img(f, 256) if f else None
            allv.append(s['verts'])
            surfs.append({'v': s['verts'].ravel().round(2).tolist(), 'n': s['normals'].ravel().round(3).tolist(),
                          'uv': s['st'].ravel().round(4).tolist(), 'i': s['tris'][:, ::-1].ravel().tolist(), 'img': url,
                          'col': '#c08080', 'alpha': bool(info.get('alpha')), 'blend': info.get('blend') == 'add' and False,
                          'glow': bool(info.get('nolm') and info.get('blend') is None and 'bulb' in s['shader'] or 'glow' in s['shader'])})
        V = np.concatenate(allv)
        data['models'].append({'surfs': surfs, 'bounds': [V.min(0).tolist(), V.max(0).tolist()]})
    three = open(a.three).read() if a.three else ''
    html = PAGE.replace('__THREE__', three).replace('__DATA__', json.dumps(data))
    fd, tmp = tempfile.mkstemp(suffix='.html'); os.write(fd, html.encode()); os.close(fd)
    asyncio.run(shoot(tmp, a.out, data['cols'] * a.size, ((len(a.models) + data['cols'] - 1) // data['cols']) * a.size))
    os.unlink(tmp)
    print(a.out)


async def shoot(html, out, w, h):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': w, 'height': h})
        pg.on('console', lambda m: print('console:', m.text) if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: print('pageerror:', e))
        await pg.goto('file://' + html)
        await pg.wait_for_function('document.title == "ready"', timeout=180000)
        await pg.screenshot(path=out)
        await b.close()


if __name__ == '__main__':
    main()
