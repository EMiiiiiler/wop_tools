#!/usr/bin/env python3
"""Screenshot a bsp2scene.py page from fixed camera positions (headless Chromium, software GL).

    python3 shoot.py <page.html> <outdir> name:x,y,z,yaw,pitch [name:x,y,z,yaw,pitch ...] [--size 1280x720] [--nomarkers]

Coordinates are Quake 3 units; yaw 0 = looking +x (east), 90 = +y (north); pitch negative = look down.
"""
import sys, os, asyncio
from playwright.async_api import async_playwright


async def run(page_path, outdir, shots, size, markers):
    os.makedirs(outdir, exist_ok=True)
    w, h = size
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                          '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': w, 'height': h})
        pg.set_default_timeout(240000)          # software GL is slow on big scenes
        msgs = []
        pg.on('console', lambda m: msgs.append(m.text))
        pg.on('pageerror', lambda e: msgs.append('ERR ' + str(e)))
        await pg.goto('file://' + os.path.abspath(page_path))
        await pg.wait_for_function('window.__ready && window.__ready()', timeout=180000)
        await pg.evaluate(f'window.__markers({str(markers).lower()})')
        await pg.evaluate("document.getElementById('hud').style.display='none'")
        for name, (x, y, z, yaw, pitch) in shots:
            await pg.evaluate(f'window.__setView({x},{y},{z},{yaw},{pitch}); window.__render()')
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=os.path.join(outdir, name + '.png'))
        await b.close()
        for m in msgs[:20]:
            print('console:', m)


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    size = (1280, 720); markers = '--nomarkers' not in sys.argv
    for x in sys.argv:
        if x.startswith('--size'):
            size = tuple(int(v) for v in x.split('=')[1].split('x'))
    page, outdir = args[0], args[1]
    shots = []
    for s in args[2:]:
        n, v = s.split(':')
        shots.append((n, [float(t) for t in v.split(',')]))
    asyncio.run(run(page, outdir, shots, size, markers))


if __name__ == '__main__':
    main()
