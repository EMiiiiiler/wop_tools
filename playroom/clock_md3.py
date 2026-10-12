#!/usr/bin/env python3
"""Twin-bell wind-up alarm clock as an MD3 (models/mapobjects/playroom/alarmclock.md3) + its textures.

    python3 clock_md3.py <out pk3dir>

Model space: origin at the floor under the centre, z up, dial faces -y (south). About 140 x 70 x 185 units.
Parts: red enamel drum with rolled edges, chrome bezel, printed dial (numerals, minute ticks), black hands at
10:10 with a brass cap, two domed chrome bells on stems with a hammer between them, a carry handle, a winding
key on the back and two splayed legs with ball feet.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from meshkit import Mesh, rot, trans

PREFIX = 'models/mapobjects/playroom/clock_'
FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONT): FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CZ, R, D = 74.0, 56.0, 22.0                  # drum centre height, radius, half depth
FRONT = trans(0, 0, CZ) @ rot('x', 90)       # local z -> world -y (towards the viewer), local y -> world z


def build():
    m = Mesh()
    # drum (local z = -D back .. +D front)
    m.lathe('red', [(0, -D), (R - 6, -D), (R - 6, -D), (R - 2, -D + 1.5), (R, -D + 5), (R, D - 5), (R - 1.5, D - 1.5), (R - 4, D)],
            segs=48, xf=FRONT)
    # chrome bezel ring (cross-section loop, counter-clockwise in r/z)
    m.lathe('chrome', [(R - 7, D - 2), (R + 1, D - 2), (R + 1, D + 1.5), (R - 1, D + 4), (R - 4.5, D + 4),
                       (R - 7, D + 1.5), (R - 7, D - 2)], segs=48, xf=FRONT)
    # dial and glass-free face
    m.disc('face', R - 6, segs=48, xf=FRONT @ trans(0, 0, D - 1))
    # hands at 10:10 (hour to the 10, minute to the 2), sitting just in front of the dial
    for (ang, L, w, t) in ((150, 28, 3.4, 1.2), (30, 41, 2.4, 2.6)):
        m.box('black', (-5, -w, D - 1 + t), (L, w, D + 0.2 + t), xf=FRONT @ rot('z', ang))
    m.lathe('brass', [(0, D - 1), (3.6, D - 1), (3.6, D + 3.2), (2.4, D + 4.6), (0, D + 5)], segs=16, xf=FRONT)
    # bells: domes on stems, tilted outward
    bell = [(0, 3.5), (26, 3.5), (29.5, 0), (31, 2.5), (30, 11), (26, 21), (18, 28.5), (7, 32), (0, 32.6)]
    for sx in (-1, 1):
        base = np.array([sx * 40.0, 0.0, CZ + R + 5])
        xf = trans(*base) @ rot('y', sx * 28)
        m.lathe('chrome', bell, segs=32, xf=xf)
        m.lathe('chrome', [(0, 32.6), (4.5, 32.6), (4.5, 37), (3, 39), (0, 39.5)], segs=12, xf=xf)        # finial
        top_of_drum = np.array([sx * 18.0, 0.0, CZ + R - 3])
        m.sweep('chrome', [top_of_drum, (top_of_drum + base) / 2 + [0, 0, 2], base + [0, 0, 2]], 3.0, sides=10)
    # hammer between the bells
    m.sweep('chrome', [(0, 0, CZ + R - 2), (0, 0, CZ + R + 18)], 2.0, sides=8)
    m.lathe('chrome', [(0, -6), (4, -5), (6, -2), (6, 2), (4, 5), (0, 6)], segs=16, xf=trans(0, 0, CZ + R + 24))
    # carry handle arching behind the bells
    arc = [(-28 * math.cos(a), 10, CZ + R - 4 + 50 * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
    m.sweep('chrome', arc, 3.2, sides=10)
    # winding key on the back
    m.sweep('chrome', [(0, D - 2, CZ - 18), (0, D + 12, CZ - 18)], 3.0, sides=10)
    m.box('chrome', (-12, D + 10, CZ - 26), (12, D + 14, CZ - 10))
    # legs + ball feet
    for sx in (-1, 1):
        a = math.radians(-90 + sx * 38)
        top = (R * 0.92 * math.cos(a), 0, CZ + R * 0.92 * math.sin(a))
        foot = (sx * 50.0, 0, 9.0)
        m.sweep('chrome', [top, ((top[0] + foot[0]) / 2, 0, (top[2] + foot[2]) / 2 + 2), foot], 3.4, sides=10)
        m.lathe('chrome', [(0, -8), (5.5, -6.5), (8, -2), (8, 2), (5.5, 6.5), (0, 8)], segs=16, xf=trans(foot[0], 0, 8))
    return m


def textures(d):
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(5)
    # red enamel (plain: the lathe's u wraps round the flat back, so a painted gloss band would show as a wedge)
    n = 256; yy, xx = np.mgrid[0:n, 0:n] / n
    red = np.zeros((n, n, 3)) + (196, 30, 34)
    red += rng.normal(0, 2.5, (n, n, 1))
    Image.fromarray(np.clip(red, 0, 255).astype(np.uint8)).save(os.path.join(d, 'clock_red.jpg'), quality=92)
    # chrome: fake reflection banded along v (sky, bright horizon, dark floor), slight streaks along u
    v = np.linspace(0, 1, n)
    band = np.interp(v, [0, 0.12, 0.26, 0.34, 0.40, 0.52, 0.68, 0.82, 1], [210, 245, 120, 55, 250, 175, 70, 150, 225])
    chrome = np.stack([band * 0.97, band * 0.99, band * 1.04], -1)[:, None, :].repeat(n, 1)     # rows = t = profile
    chrome = np.clip(chrome + rng.normal(0, 3, (n, n, 1)), 0, 255)
    Image.fromarray(chrome.astype(np.uint8)).save(os.path.join(d, 'clock_chrome.jpg'), quality=92)
    Image.fromarray(np.clip(np.zeros((64, 64, 3)) + (28, 28, 32) + rng.normal(0, 3, (64, 64, 1)), 0, 255).astype(np.uint8)).save(
        os.path.join(d, 'clock_black.jpg'), quality=92)
    br = np.zeros((64, 64, 3)) + (214, 170, 70); br[:20] += 30
    Image.fromarray(np.clip(br, 0, 255).astype(np.uint8)).save(os.path.join(d, 'clock_brass.jpg'), quality=92)
    # dial: cream face, minute ticks, bold numerals, small maker's mark
    S = 512; im = Image.new('RGB', (S, S), (250, 244, 226)); g = ImageDraw.Draw(im)
    c = S / 2; rad = S / 2 - 6
    g.ellipse((c - rad, c - rad, c + rad, c + rad), fill=(252, 247, 232))
    for k in range(60):
        a = math.radians(90 - k * 6); r0 = rad - (34 if k % 5 == 0 else 20); w = 7 if k % 5 == 0 else 3
        g.line((c + r0 * math.cos(a), c - r0 * math.sin(a), c + (rad - 10) * math.cos(a), c - (rad - 10) * math.sin(a)), fill=(40, 36, 40), width=w)
    f = ImageFont.truetype(FONT, 58)
    for h in range(1, 13):
        a = math.radians(90 - h * 30); r0 = rad - 82
        g.text((c + r0 * math.cos(a), c - r0 * math.sin(a)), str(h), font=f, fill=(30, 28, 34), anchor='mm')
    g.text((c, c + 92), 'PADMAN', font=ImageFont.truetype(FONT, 30), fill=(200, 40, 46), anchor='mm')
    g.text((c, c + 124), 'WIND-UP', font=ImageFont.truetype(FONT, 16), fill=(120, 110, 100), anchor='mm')
    im.save(os.path.join(d, 'clock_face.jpg'), quality=94)


def main(out):
    d = os.path.join(out, 'models', 'mapobjects', 'playroom')
    os.makedirs(d, exist_ok=True)
    m = build()
    m.save(os.path.join(d, 'alarmclock.md3'), PREFIX, name='alarmclock')
    textures(d)
    mn, mx = m.bounds()
    nv = sum(len(v) for p in m.parts.values() for (v, _, _, _) in p)
    nt = sum(len(t) for p in m.parts.values() for (_, _, t, _) in p)
    print('alarmclock.md3', nv, 'verts', nt, 'tris', 'bounds', mn.round(1), mx.round(1))
    return mn, mx


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out'))
