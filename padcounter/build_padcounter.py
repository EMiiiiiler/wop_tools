#!/usr/bin/env python3
"""Generates the 'padcounter' World of Padman map project (NetRadiant Custom / q3map2).
Edit GL (global model scale) and re-run to rebuild everything."""
import os, math, random, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.environ.get('OUT', '/mnt/user-data/outputs/padcounter')
for d in ['maps', 'scripts', 'textures/padcounter', 'levelshots', 'sound/padcounter', 'build']:
    os.makedirs(f'{OUT}/{d}', exist_ok=True)

GL = float(os.environ.get("GL", "1.0"))   # GLOBAL MODEL SCALE (1.0 = native model size). Multiplies every misc_model modelscale.
rnd = random.Random(2007)

# ----------------------------------------------------------------- textures
N = 256
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)

def tn(blur, seed):
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((N, N)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (N * 3, N * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * N, j * N))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(big.crop((N, N, 2 * N, 2 * N)), dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6) / 3.0

def col(c): return np.array(c, dtype=np.float32)
def n3(blur, seed, amp): return tn(blur, seed)[..., None] * amp
def toimg(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
def save(name, im):
    if isinstance(im, np.ndarray): im = toimg(im)
    im.save(f'{OUT}/textures/padcounter/{name}.jpg', quality=92)

def font(sz):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def wood(light, dark, k, seed):
    g = ((np.sin(yy * 2 * np.pi * k / N + tn(10, seed) * 10) + 1) / 2)[..., None]
    return col(dark) * (1 - g) + col(light) * g + n3(1.2, seed + 50, 10)

def make_textures():
    # counter top: speckled laminate/granite
    a = col((206, 192, 162)) + n3(40, 3, 8) + n3(1.0, 4, 10)
    sp = tn(0.7, 5)
    a[sp > 1.5] *= 0.55
    a[sp < -1.6] = a[sp < -1.6] * 0.3 + col((255, 250, 235)) * 0.7
    save('counter_top', a)
    # cabinet door
    im = toimg(wood((176, 122, 72), (138, 88, 48), 22, 6)); d = ImageDraw.Draw(im)
    d.rectangle([10, 10, 245, 245], outline=(60, 34, 16), width=4)
    d.rectangle([22, 22, 233, 233], outline=(214, 164, 112), width=2)
    d.ellipse([200, 118, 224, 142], fill=(205, 195, 175), outline=(80, 70, 60), width=2)
    save('cabinet', im)
    save('wood_dark', wood((110, 70, 40), (74, 44, 24), 18, 7))
    # teal tiles
    a = np.zeros((N, N, 3), np.float32)
    for ty in range(4):
        for tx in range(4):
            a[ty * 64:(ty + 1) * 64, tx * 64:(tx + 1) * 64] = col((70, 160, 168)) + rnd.uniform(-10, 10)
    a += n3(1, 8, 6)
    mx, my = xx % 64, yy % 64
    a[(mx >= 3) & (mx < 6) | (my >= 3) & (my < 6)] += 28
    a[(mx >= 58) | (my >= 58)] -= 25
    a[(mx < 3) | (my < 3)] = col((205, 205, 195))
    save('tile_teal', a)
    save('wall_paint', col((236, 200, 160)) + n3(25, 9, 10) + n3(1, 10, 5))
    save('ceiling', col((235, 232, 225)) + n3(1.5, 11, 8))
    # checker floor
    par = (((xx // 64) + (yy // 64)) % 2 == 0)[..., None]
    a = np.where(par, col((232, 220, 190)), col((176, 96, 64))) + n3(2, 12, 8)
    gm = ((xx % 64 < 2) | (yy % 64 < 2))
    a[gm] *= 0.7
    save('floor_checker', a)
    # brushed steel
    r = np.random.default_rng(13).random((N, N)).astype(np.float32)
    s = sum(np.roll(r, k, axis=1) for k in range(-15, 16)) / 31.0
    s = (s - s.mean()) / (s.std() + 1e-6)
    save('steel', col((178, 182, 188)) + s[..., None] * 9 + (np.sin(xx * 2 * np.pi / N) * 6)[..., None])
    # chrome env
    v = 0.5 + 0.5 * np.sin(yy / N * 2 * np.pi * 2 + 0.6)
    save('chrome', (60 + v * 190)[..., None] * np.ones(3) * col((0.96, 0.99, 1.04)) + n3(2, 15, 6))
    # stove top + glow
    a = col((26, 26, 30)) + n3(1, 16, 5); im = toimg(a); d = ImageDraw.Draw(im)
    g = Image.new('RGB', (N, N), (0, 0, 0)); dg = ImageDraw.Draw(g)
    for cx, cy in [(64, 64), (192, 64), (64, 192), (192, 192)]:
        d.ellipse([cx - 52, cy - 52, cx + 52, cy + 52], outline=(70, 70, 76), width=3)
        for rr, w in [(42, 4), (32, 4), (22, 4), (12, 4)]:
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(95, 40, 30), width=w)
            dg.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 90, 20), width=w)
    save('stove_top', im); save('stove_glow', g.filter(ImageFilter.GaussianBlur(1.2)))
    # cutting board
    a = wood((226, 184, 120), (196, 150, 92), 30, 12)
    im = toimg(a); d = ImageDraw.Draw(im)
    for y in (40, 130, 215): d.line([(0, y), (N, y)], fill=(150, 108, 60), width=2)
    save('cutting_board', im)
    # gingham
    a = np.full((N, N, 3), 250.0, np.float32)
    h = (yy // 32) % 2 == 0; vv = (xx // 32) % 2 == 0; red = col((205, 45, 50))
    a[h] = a[h] * 0.62 + red * 0.38
    a[vv] = a[vv] * 0.62 + red * 0.38
    save('gingham', a + n3(0.8, 17, 6))
    # book spines (stairs)
    im = Image.new('RGB', (N, N), (40, 30, 30)); d = ImageDraw.Draw(im)
    pal = [(180, 40, 40), (40, 90, 170), (50, 140, 70), (220, 170, 40), (120, 50, 140), (230, 120, 40), (30, 120, 130)]
    x = 0
    while x < N:
        w = min(rnd.randint(20, 40), N - x); c = rnd.choice(pal)
        d.rectangle([x, 0, x + w - 1, N], fill=c, outline=(20, 15, 15))
        d.rectangle([x, 22, x + w - 1, 30], fill=(235, 225, 190)); d.rectangle([x, 226, x + w - 1, 234], fill=(235, 225, 190))
        x += w
    save('books', im)
    # tins
    def tin(name, base, text, icon):
        im = Image.new('RGB', (N, N), base); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, N, 30], fill=(240, 240, 240)); d.rectangle([0, 226, N, N], fill=(240, 240, 240))
        d.rectangle([0, 30, N, 36], fill=(150, 150, 155)); d.rectangle([0, 220, N, 226], fill=(150, 150, 155))
        for cx in (64, 192): icon(d, cx, 128)
        f = font(30); tw = d.textlength(text, font=f)
        d.text(((N - tw) / 2, 40), text, fill=(255, 245, 220), font=f)
        d.text(((N - tw) / 2, 180), text, fill=(255, 245, 220), font=f)
        save(name, np.asarray(im).astype(np.float32) + n3(1, 18, 5))
    def tomato(d, cx, cy):
        d.ellipse([cx - 34, cy - 30, cx + 34, cy + 34], fill=(235, 60, 50), outline=(120, 20, 20), width=3)
        d.polygon([(cx, cy - 34), (cx - 14, cy - 20), (cx + 14, cy - 20)], fill=(60, 150, 60))
    def pea(d, cx, cy):
        d.rounded_rectangle([cx - 44, cy - 14, cx + 44, cy + 14], 14, fill=(120, 200, 90), outline=(30, 90, 30), width=3)
        for k in (-26, 0, 26): d.ellipse([cx + k - 10, cy - 10, cx + k + 10, cy + 10], fill=(170, 235, 120))
    tin('tin_red', (196, 36, 40), 'TOMATOES', tomato)
    tin('tin_green', (44, 140, 66), 'PEAS', pea)
    # sugar
    a = col((248, 248, 250)) + n3(0.8, 19, 10)
    sp = tn(0.6, 20); a[sp > 1.7] = 255; a[sp < -1.7] *= 0.88
    save('sugar', a)
    # cereal box
    im = Image.new('RGB', (N, N), (250, 200, 40)); d = ImageDraw.Draw(im)
    pts = []
    for i in range(24):
        r_ = 120 if i % 2 == 0 else 78; an = i * math.pi / 12
        pts.append((128 + r_ * math.cos(an), 128 + r_ * math.sin(an)))
    d.polygon(pts, fill=(40, 90, 200), outline=(20, 40, 120))
    f = font(44)
    for t, y in (('CRUNCHY', 70), ('PADS', 130)):
        tw = d.textlength(t, font=f)
        d.text(((N - tw) / 2 + 2, y + 2), t, fill=(120, 20, 20), font=f); d.text(((N - tw) / 2, y), t, fill=(255, 255, 255), font=f)
    save('cereal', im)
    # cheese
    a = col((246, 206, 72)) + n3(6, 21, 8) + n3(1, 22, 5); im = toimg(a); d = ImageDraw.Draw(im)
    for _ in range(9):
        cx, cy, r_ = rnd.randint(0, N), rnd.randint(0, N), rnd.randint(9, 26)
        d.ellipse([cx - r_, cy - r_, cx + r_, cy + r_], fill=(205, 150, 30))
        d.ellipse([cx - r_ + 4, cy - r_ + 4, cx + r_ - 2, cy + r_ - 2], fill=(226, 175, 45))
    save('cheese', im)
    # window (sky)
    t = (yy / N)[..., None]
    a = col((100, 165, 240)) * (1 - t) + col((235, 242, 255)) * t
    sun = Image.new('L', (N, N), 0); ImageDraw.Draw(sun).ellipse([140, 30, 220, 110], fill=255)
    sun = np.asarray(sun.filter(ImageFilter.GaussianBlur(10)), dtype=np.float32)[..., None] / 255
    a = a * (1 - sun) + col((255, 252, 230)) * sun
    cl = np.clip(tn(14, 23) * 1.6 - 0.2, 0, 1)[..., None]
    a = a * (1 - cl * 0.8) + col((255, 255, 255)) * cl * 0.8
    im = toimg(a); d = ImageDraw.Draw(im)
    d.rectangle([123, 0, 133, N], fill=(245, 245, 240)); d.rectangle([0, 123, N, 133], fill=(245, 245, 240))
    d.rectangle([0, 0, N - 1, N - 1], outline=(245, 245, 240), width=6)
    save('window', im)
    save('water', col((105, 170, 230)) + n3(3, 24, 22) + n3(1, 25, 8))
    # jump pad
    im = Image.new('RGB', (N, N), (255, 170, 30)); d = ImageDraw.Draw(im)
    for yk in (0, 64, 128, 192):
        d.line([(32, yk + 52), (128, yk + 12), (224, yk + 52)], fill=(40, 20, 0), width=14)
    d.rectangle([0, 0, N - 1, N - 1], outline=(60, 30, 0), width=8)
    save('jumppad', im)
    # chalkboard
    a = col((34, 56, 44)) + n3(8, 26, 8) + n3(1, 27, 3); im = toimg(a); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, N - 1, N - 1], outline=(150, 100, 60), width=10)
    f = font(28)
    for t, y, c in (("TODAY'S", 24, (228, 228, 218)), ('SPECIAL:', 58, (228, 228, 218)), ('PAD STEW', 100, (250, 220, 120))):
        tw = d.textlength(t, font=f); d.text(((N - tw) / 2, y), t, fill=c, font=f)
    d.line([(40, 150), (216, 150)], fill=(228, 228, 218), width=2)
    d.polygon([(70, 190), (100, 175), (130, 190), (100, 205)], outline=(228, 228, 218)); d.polygon([(130, 190), (150, 178), (150, 202)], outline=(228, 228, 218))
    d.ellipse([85, 184, 91, 190], fill=(228, 228, 218))
    d.polygon([(190, 168), (196, 184), (212, 184), (199, 194), (204, 210), (190, 200), (176, 210), (181, 194), (168, 184), (184, 184)], outline=(250, 220, 120))
    save('chalkboard', im)
    # ceramic
    a = col((240, 240, 245)) + n3(3, 28, 4); im = toimg(a); d = ImageDraw.Draw(im)
    d.rectangle([0, 40, N, 62], fill=(50, 90, 170)); d.rectangle([0, 194, N, 216], fill=(50, 90, 170))
    save('ceramic', im)
    # ceiling light panel
    im = Image.new('RGB', (N, N), (255, 252, 235)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, N - 1, N - 1], outline=(180, 180, 175), width=10)
    for k in (64, 128, 192): d.line([(k, 8), (k, N - 8)], fill=(225, 222, 205), width=2)
    save('lightpanel', im)

# ----------------------------------------------------------------- sounds
def wavout(path, data, sr=22050):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype('<i2').tobytes())

def make_sounds():
    sr = 22050; t = np.arange(sr) / sr
    hum = 0.5 * np.sin(2 * np.pi * 60 * t) + 0.25 * np.sin(2 * np.pi * 120 * t) + 0.12 * np.sin(2 * np.pi * 180 * t)
    wavout(f'{OUT}/sound/padcounter/hum.wav', hum * 0.35)
    n = int(sr * 2.5); d = np.zeros(n); tt = np.arange(n) / sr
    for t0, f, a in ((0.2, 1400, 0.6), (1.3, 1100, 0.35)):
        m = tt >= t0; x = tt[m] - t0
        d[m] += a * np.sin(2 * np.pi * f * x) * np.exp(-x * 28)
    wavout(f'{OUT}/sound/padcounter/drip.wav', d)

# ----------------------------------------------------------------- shaders / arena
def basic(n, extra=''):
    return (f'textures/padcounter/{n}\n{{\n    qer_editorimage textures/padcounter/{n}.jpg\n{extra}'
            '    {\n        map $lightmap\n        rgbGen identity\n    }\n'
            f'    {{\n        map textures/padcounter/{n}.jpg\n        blendFunc GL_DST_COLOR GL_ZERO\n        rgbGen identity\n    }}\n}}\n')

def make_shader():
    s = '// padcounter.shader - Giant Kitchen Counter (generated)\n\n'
    for n in ['counter_top', 'cabinet', 'wood_dark', 'tile_teal', 'wall_paint', 'ceiling', 'floor_checker',
              'cutting_board', 'gingham', 'books', 'sugar', 'cereal', 'cheese', 'chalkboard', 'ceramic']:
        s += basic(n) + '\n'
    for n in ['steel', 'tin_red', 'tin_green']:
        s += basic(n, '    surfaceparm metalsteps\n') + '\n'
    s += '''textures/padcounter/chrome
{
    qer_editorimage textures/padcounter/chrome.jpg
    surfaceparm metalsteps
    {
        map textures/padcounter/chrome.jpg
        tcGen environment
        rgbGen identity
    }
    {
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
        rgbGen identity
    }
}

textures/padcounter/stove_top
{
    qer_editorimage textures/padcounter/stove_top.jpg
    surfaceparm metalsteps
    {
        map $lightmap
        rgbGen identity
    }
    {
        map textures/padcounter/stove_top.jpg
        blendFunc GL_DST_COLOR GL_ZERO
        rgbGen identity
    }
    {
        map textures/padcounter/stove_glow.jpg
        blendFunc GL_ONE GL_ONE
        rgbGen wave sin 0.55 0.35 0 0.4
    }
}

textures/padcounter/window
{
    qer_editorimage textures/padcounter/window.jpg
    surfaceparm nomarks
    surfaceparm nolightmap
    q3map_surfacelight 1200
    q3map_lightSubdivide 64
    {
        map textures/padcounter/window.jpg
        rgbGen identity
    }
}

textures/padcounter/lightpanel
{
    qer_editorimage textures/padcounter/lightpanel.jpg
    surfaceparm nomarks
    q3map_surfacelight 500
    q3map_lightSubdivide 64
    {
        map $lightmap
        rgbGen identity
    }
    {
        map textures/padcounter/lightpanel.jpg
        blendFunc GL_DST_COLOR GL_ZERO
        rgbGen identity
    }
}

textures/padcounter/jumppad
{
    qer_editorimage textures/padcounter/jumppad.jpg
    surfaceparm nodamage
    surfaceparm nolightmap
    q3map_surfacelight 150
    {
        map textures/padcounter/jumppad.jpg
        tcMod scroll 0 -1.2
        rgbGen identity
    }
}

textures/padcounter/water
{
    qer_editorimage textures/padcounter/water.jpg
    qer_trans 0.5
    surfaceparm trans
    surfaceparm nonsolid
    surfaceparm water
    surfaceparm fog
    surfaceparm nolightmap
    surfaceparm nomarks
    fogparms ( 0.25 0.5 0.75 ) 400
    cull disable
    deformVertexes wave 64 sin 0 1.5 0 0.4
    {
        map textures/padcounter/water.jpg
        blendFunc GL_DST_COLOR GL_ZERO
        tcMod turb 0 0.12 0 0.08
        tcMod scroll 0.02 0.01
    }
}
'''
    open(f'{OUT}/scripts/padcounter.shader', 'w').write(s)
    open(f'{OUT}/scripts/shaderlist.txt', 'w').write('padcounter\n')
    open(f'{OUT}/scripts/padcounter.arena', 'w').write(
        '{\nmap "padcounter"\nlongname "Giant Kitchen Counter"\ntype "ffa tdm"\nfraglimit "20"\ntimelimit "10"\n}\n')

# ----------------------------------------------------------------- map geometry
P = lambda n: 'padcounter/' + n
TS = {'counter_top': 256, 'cabinet': 256, 'wood_dark': 256, 'tile_teal': 256, 'wall_paint': 512, 'ceiling': 512,
      'floor_checker': 512, 'steel': 256, 'chrome': 256, 'stove_top': (440, 600), 'cutting_board': 256,
      'gingham': 512, 'books': 128, 'tin_red': 256, 'tin_green': 256, 'sugar': 128, 'cereal': 200, 'cheese': 256,
      'window': (600, 600), 'water': 256, 'jumppad': 80, 'chalkboard': (600, 400), 'ceramic': 256, 'lightpanel': 192}
CT, CAB, WD, TILE, PAINT, CEIL, FLOOR = map(P, ['counter_top', 'cabinet', 'wood_dark', 'tile_teal', 'wall_paint', 'ceiling', 'floor_checker'])
STEEL, CHROME, STOVE, BOARD, GING, BOOKS, TINR, TING, SUGAR, CEREAL, CHEESE, WINDOW, WATER, PAD, CHALK, CERAMIC, LPANEL = map(
    P, ['steel', 'chrome', 'stove_top', 'cutting_board', 'gingham', 'books', 'tin_red', 'tin_green', 'sugar', 'cereal',
        'cheese', 'window', 'water', 'jumppad', 'chalkboard', 'ceramic', 'lightpanel'])
TRIG, ORIGIN = 'common/trigger', 'common/origin'
DETAIL = 134217728

def scale_of(tex):
    t = TS.get(tex.split('/')[-1])
    if t is None: return (0.5, 0.5)
    if isinstance(t, int): t = (t, t)
    return (t[0] / 256.0, t[1] / 256.0)

def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def brush(faces, detail=False):
    """faces: list of (tex, [p1,p2,p3]); fixes winding so normals face outward."""
    allp = [p for _, pts in faces for p in pts]
    cen = tuple(sum(p[i] for p in allp) / len(allp) for i in range(3))
    out = []
    for tex, pts in faces:
        a, b, c = [tuple(float(round(v, 1)) for v in p) for p in pts]
        n = cross(sub(a, b), sub(c, b))
        fc = tuple((a[i] + b[i] + c[i]) / 3 for i in range(3))
        if dot(n, sub(fc, cen)) < 0: a, c = c, a
        out.append((tex, (a, b, c)))
    return {'faces': out, 'detail': detail}

def box(x1, y1, z1, x2, y2, z2, tex, faces=None, detail=False):
    f = faces or {}
    T = lambda k: f.get(k, tex)
    return brush([
        (T('top'), [(x1, y1, z2), (x2, y1, z2), (x2, y2, z2)]),
        (T('bot'), [(x1, y1, z1), (x2, y1, z1), (x2, y2, z1)]),
        (T('n'), [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2)]),
        (T('s'), [(x1, y1, z1), (x2, y1, z1), (x2, y1, z2)]),
        (T('e'), [(x2, y1, z1), (x2, y2, z1), (x2, y2, z2)]),
        (T('w'), [(x1, y1, z1), (x1, y2, z1), (x1, y2, z2)])], detail)

def prism(cx, cy, r, z1, z2, n, tex, cap, detail=True):
    ring = [(round(cx + r * math.cos(2 * math.pi * (i + .5) / n)), round(cy + r * math.sin(2 * math.pi * (i + .5) / n))) for i in range(n)]
    fs = [(cap, [(ring[0][0], ring[0][1], z2), (ring[1][0], ring[1][1], z2), (ring[2][0], ring[2][1], z2)]),
          (cap, [(ring[0][0], ring[0][1], z1), (ring[1][0], ring[1][1], z1), (ring[2][0], ring[2][1], z1)])]
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        fs.append((tex, [(a[0], a[1], z1), (b[0], b[1], z1), (a[0], a[1], z2)]))
    return brush(fs, detail)

def wedge(x1, y1, x2, y2, z1, zt, tex, high='n', detail=True):
    if high in 'ns': L, Wd = y2 - y1, x2 - x1
    else: L, Wd = x2 - x1, y2 - y1
    def pt(u, v, z):
        if high == 'n': return (x1 + v, y1 + u, z)
        if high == 's': return (x1 + v, y2 - u, z)
        if high == 'e': return (x1 + u, y1 + v, z)
        return (x2 - u, y1 + v, z)
    A, B, C, D = pt(0, 0, z1), pt(0, Wd, z1), pt(L, Wd, z1), pt(L, 0, z1)
    E, F = pt(L, 0, zt), pt(L, Wd, zt)
    return brush([(tex, [A, B, C]), (tex, [D, C, F]), (tex, [A, D, E]), (tex, [B, C, F]), (tex, [A, B, F])], detail)

def fmt(p): return ' '.join(str(int(v)) if float(v).is_integer() else str(v) for v in p)

def brush_text(b):
    s = '{\n'
    for tex, (a, bb, c) in b['faces']:
        sx, sy = scale_of(tex)
        s += f'( {fmt(a)} ) ( {fmt(bb)} ) ( {fmt(c)} ) {tex} 0 0 0 {sx:g} {sy:g} {DETAIL if b["detail"] else 0} 0 0\n'
    return s + '}\n'

def check(b):
    pl = []
    for _, (a, bb, c) in b['faces']:
        n = cross(sub(a, bb), sub(c, bb)); l = math.sqrt(dot(n, n))
        if l < 1e-6: return False
        n = tuple(v / l for v in n); pl.append((n, dot(n, a)))
    cnt = [0] * len(pl); m = len(pl)
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                M = np.array([pl[i][0], pl[j][0], pl[k][0]])
                if abs(np.linalg.det(M)) < 1e-6: continue
                p = np.linalg.solve(M, np.array([pl[i][1], pl[j][1], pl[k][1]]))
                if all(np.dot(pl[q][0], p) - pl[q][1] <= 0.05 for q in range(m)):
                    for q in (i, j, k): cnt[q] += 1
    return all(c >= 3 for c in cnt)

class MapBuilder:
    def __init__(self): self.world = []; self.ents = []; self.models = 0; self.eid = 1
    def add(self, *bs): self.world.extend(bs)
    def ent(self, kv, brushes=None):
        s = f'// entity {self.eid}\n{{\n'; self.eid += 1
        for k, v in kv.items(): s += f'"{k}" "{v}"\n'
        for b in brushes or []: s += brush_text(b)
        self.ents.append(s + '}\n')
    def light(self, x, y, z, val, c='1 0.96 0.88'): self.ent({'classname': 'light', 'origin': f'{x} {y} {z}', 'light': val, '_color': c})
    def spawn(self, x, y, a): self.ent({'classname': 'info_player_deathmatch', 'origin': f'{x} {y} {int(25)}'.replace(' 25', f' {0}') if False else f'{x} {y} {self.zs}', 'angle': a})
    def item(self, cls, x, y, z): self.ent({'classname': cls, 'origin': f'{x} {y} {z}'})
    def mdl(self, path, x, y, z, ang=None, s=1.0, anim=None):
        ang = rnd.uniform(0, 360) if ang is None else ang
        kv = {'classname': 'misc_model', 'model': 'models/mapobjects/' + path, 'origin': f'{int(x)} {int(y)} {int(z)}',
              'angle': str(int(ang)), 'modelscale': f'{GL * s:g}', '_cs': '1'}
        if anim: kv.update({'animationStart': '0', 'animationEnd': str(anim), 'animationFPS': '30'})
        self.ent(kv); self.models += 1
    def row(self, paths, x, y, dx, dy, z, s=1.0, jit=0):
        for i, p in enumerate(paths):
            self.mdl(p, x + dx * i + rnd.uniform(-jit, jit), y + dy * i + rnd.uniform(-jit, jit), z, s=s)
    def text(self):
        s = '// Giant Kitchen Counter - generated by build_padcounter.py\n// entity 0\n{\n'
        s += '"classname" "worldspawn"\n"message" "Giant Kitchen Counter"\n"_ambient" "22"\n'
        for i, b in enumerate(self.world):
            s += f'// brush {i}\n' + brush_text(b)
        s += '}\n' + ''.join(self.ents)
        return s

M = MapBuilder()

def build_map():
    A = M.add
    CTZ = 640
    # ---- room shell (kitchen)
    A(box(-1856, -1344, -64, 1856, 1344, 0, FLOOR))
    A(box(-1856, -1344, 1792, 1856, 1344, 1856, CEIL))
    A(box(-1856, -1344, 0, 1856, -1280, 1792, PAINT))
    A(box(-1856, 1280, 0, 1856, 1344, 640, PAINT))
    A(box(-1856, 1280, 640, 1856, 1344, 1000, TILE))
    A(box(-1856, 1280, 1000, 1856, 1344, 1792, PAINT))
    A(box(-1856, -1280, 0, -1792, 1280, 1792, PAINT))
    A(box(1792, -1280, 0, 1856, -300, 1792, PAINT)); A(box(1792, 300, 0, 1856, 1280, 1792, PAINT))
    A(box(1792, -300, 0, 1856, 300, 900, PAINT)); A(box(1792, -300, 1500, 1856, 300, 1792, PAINT))
    A(box(1824, -300, 900, 1856, 300, 1500, WINDOW))
    A(box(1760, -330, 880, 1792, 330, 900, WD, detail=True))        # window sill
    # skirting boards
    A(box(-1792, -1280, 0, 1792, -1264, 40, WD, detail=True)); A(box(-1792, -1264, 0, -1776, 1264, 40, WD, detail=True))
    A(box(1776, -1264, 0, 1792, 1264, 40, WD, detail=True))

    # ---- counter with sink cut-out
    SX1, SX2, SY1, SY2, BAS = -1130, -690, 380, 980, 416
    x1, x2, y1, y2 = -1280, 1280, -448, 1280
    A(box(x1, y1, 0, SX1, y2, CTZ, CAB, {'top': CT, 'e': STEEL}))
    A(box(SX2, y1, 0, x2, y2, CTZ, CAB, {'top': CT, 'w': STEEL}))
    A(box(SX1, y1, 0, SX2, SY1, CTZ, CAB, {'top': CT, 'n': STEEL}))
    A(box(SX1, SY2, 0, SX2, y2, CTZ, CAB, {'top': CT, 's': STEEL}))
    A(box(SX1, SY1, 0, SX2, SY2, BAS, STEEL))
    A(box(SX1, SY1, BAS, SX2, SY2, 560, WATER))
    # faucet (chrome)
    A(box(-930, 1200, CTZ, -890, 1240, 880, CHROME, detail=True))
    A(box(-930, 1010, 840, -890, 1240, 880, CHROME, detail=True))
    A(box(-1010, 1205, 860, -810, 1235, 880, CHROME, detail=True))

    # ---- cutting board + cheese ramp
    A(box(-480, 100, CTZ, -80, 640, 680, BOARD, detail=True))
    A(wedge(-480, -160, -80, 100, CTZ, 680, CHEESE, 'n'))
    # ---- sugar cubes
    for (a_, b_, c_, d_, z0) in [(100, 320, 180, 400, 640), (180, 320, 260, 400, 640), (140, 320, 220, 400, 720)]:
        A(box(a_, b_, z0, c_, d_, z0 + 80, SUGAR, detail=True))
    # ---- book-stairs + stove plateau
    A(box(600, 420, CTZ, 680, 780, 680, BOOKS, detail=True))
    A(box(680, 420, CTZ, 760, 780, 720, BOOKS, detail=True))
    A(box(760, 300, CTZ, 1200, 900, 760, STEEL, {'top': STOVE}, detail=True))
    # ---- bread bin (tall, with jump-pad access)
    A(box(-60, 880, CTZ, 360, 1240, 1000, STEEL, {'top': WD}, detail=True))
    # ---- cereal box
    A(box(460, 1120, CTZ, 660, 1200, 980, CEREAL, detail=True))
    # ---- tins + mug (cover)
    A(prism(-620, -120, 90, CTZ, CTZ + 200, 12, TINR, STEEL))
    A(prism(640, -100, 90, CTZ, CTZ + 160, 12, TING, STEEL))
    A(prism(1000, -120, 110, CTZ, CTZ + 240, 12, TINR, STEEL))
    A(prism(1180, 1000, 80, CTZ, CTZ + 180, 12, TING, STEEL))
    A(prism(-1000, -60, 80, CTZ, CTZ + 180, 12, CERAMIC, CERAMIC))
    # ---- gingham picnic mat (counter) + rug (floor)
    A(box(200, -380, CTZ, 560, -100, CTZ + 4, GING, detail=True))
    A(box(-900, -1100, 0, 900, -640, 4, GING, detail=True))
    # ---- upper cabinets, shelf, chalkboard, fridge
    A(box(420, 1100, 1000, 1280, 1280, 1500, CAB, detail=True))
    A(box(-1100, 1130, 1000, -500, 1280, 1032, WD, detail=True))
    A(box(-300, 1264, 1000, 300, 1280, 1400, CERAMIC, {'n': CHALK, 's': CHALK}, detail=True))
    A(box(-1792, 800, 0, -1392, 1280, 1500, STEEL, detail=True))
    A(box(-1392, 1000, 500, -1376, 1030, 900, CHROME, detail=True)); A(box(-1392, 1060, 500, -1376, 1090, 900, CHROME, detail=True))
    # ---- ceiling light panels
    for lx in (-1100, 0, 1100):
        for ly in (-700, 700):
            A(box(lx - 96, ly - 96, 1744, lx + 96, ly + 96, 1792, LPANEL, detail=True))

    # ---- jump pads (visible pad + trigger_push + target_position)
    def jumppad(x, y, z, tx, ty, tz, name):
        A(box(x - 40, y - 40, z, x + 40, y + 40, z + 8, PAD, detail=True))
        M.ent({'classname': 'trigger_push', 'target': name}, [box(x - 40, y - 40, z + 8, x + 40, y + 40, z + 72, TRIG)])
        M.ent({'classname': 'target_position', 'targetname': name, 'origin': f'{tx} {ty} {tz}'})
    jumppad(-1210, 1150, CTZ, -1000, 1180, 1200, 'tp_shelf')
    jumppad(-220, 820, CTZ, 60, 1020, 1180, 'tp_bin')
    jumppad(-500, -900, 0, -500, -400, 780, 'tp_s1')
    jumppad(500, -900, 0, 500, -400, 780, 'tp_s2')
    jumppad(-1560, 100, 0, -1230, 100, 780, 'tp_w')
    jumppad(1560, 100, 0, 1230, 100, 780, 'tp_e')

    # ---- spinning ceiling fan
    fan = [box(-8, -8, 1642, 8, 8, 1658, ORIGIN), box(-300, -16, 1650, 300, 16, 1658, WD), box(-16, -300, 1650, 16, 300, 1658, WD),
           box(-30, -30, 1640, 30, 30, 1664, WD), box(-6, -6, 1658, 6, 6, 1792, WD)]
    M.ent({'classname': 'func_rotating', 'speed': '90', 'origin': '0 0 1650'}, fan)

    # ---- lights
    for lx in (-1100, 0, 1100):
        for ly in (-700, 700): M.light(lx, ly, 1690, 1400)
    M.light(1700, 0, 1200, 1600, '1 0.97 0.82')
    M.light(-1200, -200, 800, 450, '1 0.9 0.7'); M.light(1250, 1150, 800, 450, '1 0.9 0.7')
    M.light(-900, 700, 900, 350, '0.8 0.9 1'); M.light(-800, 1180, 1100, 350, '1 0.9 0.7')
    M.light(-1600, -300, 400, 500); M.light(1600, -300, 400, 500)

    # ---- sound
    M.ent({'classname': 'target_speaker', 'origin': '-1340 1000 700', 'noise': 'sound/padcounter/hum.wav', 'spawnflags': '1'})
    M.ent({'classname': 'target_speaker', 'origin': '-910 1020 830', 'noise': 'sound/padcounter/drip.wav', 'spawnflags': '1'})

    # ---- spawns (counter + kitchen floor)
    M.zs = CTZ + 25
    for x, y, a in [(-1180, -100, 0), (-800, -250, 20), (-300, -300, 90), (50, -100, 90), (400, -200, 135), (800, -250, 180),
                    (1100, -250, 180), (1240, 600, 180), (520, 640, 0), (-300, 800, 270), (-600, 250, 0), (200, 650, 0),
                    (800, 1100, 270), (1050, 200, 180)]:
        M.spawn(x, y, a)
    M.zs = 25
    for x, y, a in [(-1550, -300, 0), (1550, -300, 180), (0, -1100, 90), (-1500, 700, 270)]: M.spawn(x, y, a)
    M.ent({'classname': 'info_player_intermission', 'origin': '-800 -1100 1300', 'target': 'cam_target'})
    M.ent({'classname': 'info_null', 'targetname': 'cam_target', 'origin': '0 500 700'})

    # ---- pickups  (CLASSNAMES: verify against your WoP entities.def)
    W = [('weapon_imperius', -1000, 1180, 1050), ('weapon_splasher', -280, 380, 700), ('weapon_bubbleg', 150, 1060, 1020),
         ('weapon_boaster', 980, 600, 780), ('weapon_betty', -900, 680, 440), ('weapon_pumper', 700, -250, 660),
         ('weapon_pumper', -1200, 500, 660), ('weapon_nipper', 300, 650, 660), ('weapon_nipper', 1200, -300, 660),
         ('weapon_balloony', -600, 900, 660), ('weapon_kma', 1000, 1100, 660), ('weapon_nipper', -1500, -700, 20)]
    for c, x, y, z in W: M.item(c, x, y, z)
    for c, x, y, z in [('item_health_large', -1230, 1000, 1050), ('item_health_large', 1000, -420, 660), ('item_health', -400, -380, 660),
                       ('item_health', 600, 1000, 660), ('item_health', 1000, 800, 780), ('item_health', -1100, 150, 660),
                       ('item_health_small', 0, 0, 660), ('item_health_small', 440, 820, 660), ('item_health_large', 1500, -1000, 20),
                       ('item_health', -1500, 600, 20), ('item_health_small', 0, -800, 20), ('item_health_small', -900, 600, 436)]:
        M.item(c, x, y, z)

    # ---------------------------------------------------------------- models
    m = M.mdl; row = M.row; C = 640
    row(['pad_condiments/pad_ketchup.md3', 'pad_condiments/pad_mustard.md3', 'pad_condiments/salt.md3',
         'pad_condiments/pepper.md3', 'pad_condiments/sugar.md3'], -640, 1235, 70, 0, C)
    for i, c in enumerate(['blue', 'green', 'orange', 'pink', 'purple', 'red', 'yellow']):
        m(f'pad_scouringpad/scouringpad_{c}.md3', -1100 + 55 * (i % 4), 1040 + 80 * (i // 4), C)
    m('pad_ducks/pad_duck.md3', -900, 500, 556); m('ente/ducka.md3', -1000, 700, 556); m('ente/duckb.md3', -800, 820, 556)
    for i in range(4): m(f'pad_plates/plate_hpstack{i + 1}.md3', -620, 430 + i * 100, C)
    for i in range(5): m(f'pad_cups/pad_cup0{i + 1}_upd.md3', -545, 450 + i * 110, C)
    m('pad_ducktape/ducktape.md3', -650, 960, C)
    # board scene
    m('ente/padstatue_gold.md3', -280, 380, 680, 90)
    for p, x, y in [('pad_cutlery/pad_knife_full.md3', -420, 200), ('pad_cutlery/pad_fork.md3', -150, 200),
                    ('pad_tins/tomatoes_ts.md3', -200, 560), ('pad_tins/carrots_ts.md3', -350, 560),
                    ('pad_fruits/apple.md3', -440, 500), ('pad_fruits/orange.md3', -130, 500), ('pad_fruits/banana.md3', -300, 250),
                    ('pad_fruits/citrus.md3', -400, 330), ('pad_fruits/walnut.md3', -160, 330), ('pad_fruits/hazelnut.md3', -130, 380),
                    ('pad_ddmix/bun.md3', -440, 420), ('pad_ddmix/bun.md3', -150, 600)]:
        m(p, x, y, 680)
    # bread bin top
    m('animated/raven_sitting_2.MD3', 150, 1060, 1000, 200, anim=210)
    m('pad_ddmix/bun.md3', 280, 960, 1000); m('pad_ddmix/bun.md3', 20, 1180, 1000)
    # stove plateau
    for p, x, y in [('pad_ddmix/diner/coffe_pot.md3', 850, 760), ('pad_ddmix/diner/muffin_choco.md3', 1100, 420),
                    ('pad_ddmix/diner/muffin_blueberry.md3', 1050, 440), ('pad_ddmix/diner/glass_diner.md3', 900, 840)]:
        m(p, x, y, 760)
    # cake display
    m('pad_cake/pad_cakestand.md3', 830, -330, C)
    for x, y in [(770, -400), (890, -400), (830, -250)]: m('pad_cake/pad_cakeslice.md3', x, y, C)
    for x, y in [(750, -300), (910, -300)]: m('pad_cake/pad_cakesliceup.md3', x, y, C)
    # fruit along east edge
    fr = ['banana', 'apple', 'orange', 'citrus']
    for i in range(12): m(f'pad_fruits/{fr[i % 4]}.md3', 1215 + (i % 2) * 40, -250 + i * 45, C)
    m('pad_fridge/veg_bag.md3', 1130, -360, C)
    bears = ['redbear', 'yellowbear', 'greenbear', 'orangebear', 'ldredbear', 'ldyellowbear', 'ldgreenbear', 'ldorangebear']
    for i, b in enumerate(bears): m(f'gummybears/{b}.md3', 930 + (i % 4) * 55, -420 + (i // 4) * 60, C)
    tins = ['pad_tins/carrots_tbl.md3', 'pad_tins/tomatoes_tbl.md3', 'pad_tins/pad_coke.md3', 'pad_tins/pad_pupsi.md3',
            'pad_tins/pad_milk_tbs.md3', 'pad_tins/carrots_ts.md3', 'pad_tins/tomatoes_tbs.md3', 'pad_tins/pad_coke_cr.md3',
            'pad_tins/pad_pupsi_cr.md3', 'pad_tins/pad_milk_s.md3', 'pad_tins/tomatoes_ts.md3']
    row(tins, -300, -415, 55, 0, C)
    # picnic on gingham
    for i, (x, y) in enumerate([(280, -300), (470, -300), (280, -180), (470, -180)]):
        m(f'pad_plates/plate_coffee{i + 1}.md3', x, y, C + 4)
    for p, x, y in [('pad_cutlery/pad_fork2.md3', 340, -300), ('pad_cutlery/pad_knife2_full.md3', 410, -300),
                    ('pad_cutlery/pad_spoon.md3', 340, -180), ('pad_cutlery/pad_teaspoon.md3', 410, -180),
                    ('pad_ddmix/diner/glass_betty.md3', 520, -340), ('pad_ddmix/diner/glass_sunrise.md3', 230, -340),
                    ('pad_ddmix/diner/sugar_packet.md3', 520, -240), ('pad_ddmix/diner/sugar_packet.md3', 230, -240),
                    ('pad_ddmix/diner/muffin_choco.md3', 375, -240), ('pad_ddmix/diner/muffin_blueberry.md3', 300, -120)]:
        m(p, x, y, C + 4)
    # tech corner (SW)
    for p, x, y in [('padtv/padtv.md3', -1210, -350), ('padtv/padtv2.md3', -1100, -350), ('pad_pc/pad_tft.md3', -980, -350),
                    ('pad_pc/keyboard.md3', -1160, -260), ('pad_pc/mousea.md3', -1060, -260),
                    ('pad_phones/pad_padika1.md3', -900, -380), ('pad_phones/pad_padika2.md3', -840, -380),
                    ('pad_phones/pad_padika3.md3', -780, -380), ('pad_phones/pad_padika4.md3', -720, -380)]:
        m(p, x, y, C)
    m('pad_lamps/gooseneck.md3', -1250, -200, C); m('pad_lamps/gooseneck2.md3', 1250, 1200, C)
    # plants
    pl = ['tulip1', 'tulip2', 'flower_pink', 'flower_yellow', 'fern', 'bonsai']
    for i, p in enumerate(pl): m(f'pad_ddmix/plants/{p}.md3', -1240, 150 + 60 * i, C)
    m('pad_ddmix/anteroom/vase.md3', -1230, 520, C)
    for i in range(3): m('pad_sunflower/pad_sunflower.md3' if i == 0 else f'pad_sunflower/pad_sunflower{i + 1}.md3', -1210, 700 + 100 * i, C)
    # shelf
    sh = 1032
    for p, x in [('pad_ddmix/padship/rumbottle1.md3', -1060), ('pad_ddmix/padship/amphora.md3', -980), ('pad_ddmix/padship/rumbottle2.md3', -900),
                 ('pad_ddmix/padlibrary/bookend.md3', -820), ('pad_books/pad_cb_fl_lg.md3', -740), ('pad_books/pad_ob_fl_md.md3', -660),
                 ('pad_books/pad_openbook.md3', -580), ('pad_lamps/small_gooseneck.md3', -520)]:
        m(p, x, 1200, sh)
    # NE counter corner + misc
    m('pad_items/towelroll.md3', 1180, 1180, C); m('pad_items/towelstack.md3', 1090, 1180, C)
    m('pad_ddmix/mix/matchbook_diner.md3', 700, 1180, C); m('padfigures/coconut.md3', 300, 550, C)
    m('pad_ddmix/padkitchen/towel_kitchen.md3', 400, 1000, C); m('pad_maple/pad_maple.md3', -1000, 1100, C)
    # floor: toys on the rug and around
    for i, b in enumerate(['pad_basketball', 'pad_soccerball', 'pad_softball', 'pad_tennisball', 'pad_softball_sig']):
        m(f'pad_ball/{b}.md3', -300 + i * 140, -900 + rnd.randint(-90, 90), 4)
    for i, c in enumerate(['padcar_black', 'padcar_muster', 'padcar_orange', 'padcar_black_rc', 'padcar_muster_rc', 'padcar_orange_rc']):
        m(f'pad_nascars/{c}.md3', 620 + 80 * (i % 3), -1050 + 70 * (i // 3), 4)
    m('pad_radio_car/radio_control.md3', -800, -1000, 4); m('pad_radio_car/radio_control_fl.md3', -700, -800, 4)
    m('pad_actionfigures/fig_girl.md3', -100, -760, 4); m('pad_actionfigures/fig_lilly.md3', 60, -780, 4)
    for p, x, y in [('pad_books/comics/pad_comic1.md3', -760, -720), ('pad_books/comics/pad_comic1_ang.md3', -690, -740),
                    ('pad_books/kids/mbook_fl_1.md3', -600, -700), ('pad_books/kids/mbook_fl_2.md3', -540, -660),
                    ('pad_books/rhodan/pdr_4books.md3', -620, -640), ('pad_books/comics/pad_oc_lg.md3', -820, -660)]:
        m(p, x, y, 4)
    for i, c in enumerate(['r', 'g', 'lb', 'y', 'o', 'p', 'bl', 'gr']):
        m(f'pad_pencils/pad_pencils{c}_lg.md3', 300 + rnd.randint(0, 200), -1000 + i * 40, 4)
    for i, s_ in enumerate(['sock_grey', 'sock_grey2', 'sock_grey3']): m(f'pad_clothes/{s_}.md3', -1100 + 50 * i, -900 + 60 * i, 0)
    m('padmousetrap/padjumptrap.md3', 1000, -900, 0); m('padmousetrap/padjumptrap.md3', 1100, -800, 0)
    m('pad_ddmix/trashcan/garbage_bag_standing.md3', 1500, -1100, 0); m('pad_ddmix/trashcan/garbage_bag_lying.md3', 1400, -1150, 0)
    m('pad_ddmix/trashcan/garbage_bag_group.md3', 1560, -1000, 0)
    m('spider/spider.md3', -1700, -1100, 0); m('spider/spiders.md3', 1500, 600, 0); m('spider/spider30.md3', -1300, 200, 0)
    # walls
    m('padlogo/padlogo_lg.md3', 1788, -700, 1000, 180); m('padlogo/padlogo_lg.md3', 0, -1276, 1100, 90)

# ----------------------------------------------------------------- levelshot
def levelshot():
    im = Image.new('RGB', (256, 192)); d = ImageDraw.Draw(im)
    for y in range(192): d.line([(0, y), (256, y)], fill=(int(250 - y * .5), int(210 - y * .6), int(150 - y * .4)))
    d.rectangle([0, 120, 256, 192], fill=(206, 192, 162)); d.rectangle([0, 112, 256, 122], fill=(70, 160, 168))
    d.ellipse([40, 90, 90, 130], fill=(196, 36, 40)); d.rectangle([150, 70, 200, 126], fill=(250, 200, 40))
    f = font(20); t = 'GIANT KITCHEN COUNTER'; tw = d.textlength(t, font=f)
    d.text(((256 - tw) / 2, 20), t, fill=(60, 30, 20), font=f)
    d.text((8, 170), 'placeholder - replace with a screenshot', fill=(60, 30, 20), font=font(10))
    im.save(f'{OUT}/levelshots/padcounter.jpg', quality=90)

if __name__ == '__main__':
    make_textures(); make_sounds(); make_shader(); levelshot(); build_map()
    bad = [i for i, b in enumerate(M.world) if not check(b)]
    print('brushes:', len(M.world), 'invalid:', bad, 'models:', M.models, 'entities:', M.eid)
    open(f'{OUT}/maps/padcounter.map', 'w').write(M.text())
