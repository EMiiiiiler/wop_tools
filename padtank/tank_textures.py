"""Procedural textures + shader + arena for wop_padtank (Fish Tank Temple).
All art is original and generated here. make_all(out) writes textures/padtank/*, models/padtank/* (fish),
scripts/padtank.shader and scripts/wop_padtank.arena (pk3dir layout). Helpers are shared with playroom/textures.py."""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('playroom_textures', os.path.join(os.path.dirname(HERE), 'playroom', 'textures.py'))
_pt = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_pt)
noise, C, N3, img, fill, font, text_c = _pt.noise, _pt.C, _pt.N3, _pt.img, _pt.fill, _pt.font, _pt.text_c
import fish_models

MAP = 'wop_padtank'
NS = 'padtank'
LONGNAME = 'Fish Tank Temple'
FOG = (0.16, 0.40, 0.56), 4800          # fog colour, distance to opaque


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', NS); os.makedirs(self.dir, exist_ok=True)
        self.sizes = {}; self.alpha = set()

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a.convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga')); self.alpha.add(name)
        else:
            im.save(os.path.join(self.dir, name + '.jpg'), quality=92)
        self.sizes[name] = im.size


def soft(im, r=0.6):
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32)


def A(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def wrap_draw(im, fn):
    """call fn(draw, ox, oy) for the 9 tile offsets so shapes wrap seamlessly"""
    d = ImageDraw.Draw(im); w, h = im.size
    for ox in (-w, 0, w):
        for oy in (-h, 0, h):
            fn(d, ox, oy)
    return im


# ------------------------------------------------------------------------------------------- stone + ground
def gravel(n, seed, palette, size=(5, 11), count=900, base=(120, 108, 92)):
    im = A(fill(n, base, 6, seed))
    rr = random.Random(seed)
    peb = [(rr.randint(0, n), rr.randint(0, n), rr.randint(*size), rr.choice(palette), rr.uniform(0.7, 1.3)) for _ in range(count)]
    def f(d, ox, oy):
        for (x, y, r, c, e) in peb:
            x0, y0 = x + ox, y + oy
            d.ellipse((x0 - r * e, y0 - r, x0 + r * e, y0 + r), fill=tuple(int(v * 0.55) for v in c))
            d.ellipse((x0 - r * e + 1, y0 - r + 1, x0 + r * e - 1, y0 + r - 1), fill=c)
            d.ellipse((x0 - r * e * 0.5, y0 - r * 0.7, x0, y0 - r * 0.2), fill=tuple(min(255, int(v * 1.25) + 18) for v in c))
    wrap_draw(im, f)
    return soft(im, 0.5) + N3(n, 0.6, seed + 3, 4)


def ashlar(n, base, seed, rows=4, cols=(2, 3), mortar=0.62, crack=True):
    """sandstone blocks in staggered courses, chipped edges, a few cracks"""
    a = fill(n, base, 7, seed) + N3(n, 20, seed + 1, 10)
    rr = random.Random(seed)
    h = n // rows
    im = A(a); d = ImageDraw.Draw(im)
    dark = tuple(int(c * mortar) for c in base)
    for r in range(rows):
        y = r * h
        d.line([(0, y), (n, y)], fill=dark, width=3)
        k = rr.choice(cols); off = rr.randint(0, n // k)
        for c in range(k + 1):
            x = (off + c * n // k) % n
            d.line([(x, y), (x, y + h)], fill=dark, width=3)
        if crack and rr.random() < 0.7:
            x = rr.randint(10, n - 10); yy = y + 4
            pts = [(x, yy)]
            for _ in range(5):
                x += rr.randint(-10, 10); yy += rr.randint(4, h // 5); pts.append((x, min(yy, y + h - 2)))
            d.line(pts, fill=tuple(int(c * 0.55) for c in base), width=2)
    a = soft(im, 0.6)
    # bevel light on block tops
    for r in range(rows):
        a[r * h + 2:r * h + 5] += 16
    return a


def flagstones(n, base, seed):
    """irregular cracked paving (like old temple walkways): voronoi cells"""
    rr = np.random.default_rng(seed)
    pts = rr.random((26, 2)) * n
    yy, xx = np.mgrid[0:n, 0:n]
    best = np.full((n, n), 1e9); second = np.full((n, n), 1e9); idx = np.zeros((n, n), int)
    for i, (px, py) in enumerate(pts):
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dd = np.hypot(xx - px - ox, yy - py - oy)
                m = dd < best
                second = np.where(m, best, np.minimum(second, dd)); idx = np.where(m, i, idx); best = np.where(m, dd, best)
    edge = np.clip((second - best) / 5, 0, 1)
    tint = (rr.random(len(pts)) * 0.16 + 0.92)[idx]
    a = (C(base) * tint[..., None]) * (0.55 + 0.45 * edge[..., None])
    return a + N3(n, 0.8, seed + 2, 6) + N3(n, 10, seed + 3, 8)


def rock(n, base, seed, strata=True):
    a = fill(n, base, 8, seed) + N3(n, 30, seed + 1, 16) + N3(n, 4, seed + 2, 10)
    if strata:
        y = np.arange(n)[:, None, None]
        a += 10 * np.sin(y / n * 2 * math.pi * 5 + noise(n, 18, seed + 4)[..., None] * 1.5)
    return a


def key_band(n=256, h=64, base=(214, 192, 150)):
    """greek-key (meander) band carved into sandstone"""
    a = fill(n, base, 5, 61, h) + N3(n, 12, 62, 6, h)
    im = A(a); d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.55) for c in base); lite = tuple(min(255, int(c * 1.12)) for c in base)
    d.line([(0, 4), (n, 4)], fill=dark, width=3); d.line([(0, h - 5), (n, h - 5)], fill=dark, width=3)
    u = 32
    for k in range(n // u):
        x = k * u
        path = [(x + 4, h - 12), (x + 4, 12), (x + 26, 12), (x + 26, 40), (x + 14, 40), (x + 14, 26)]
        d.line(path, fill=dark, width=5); d.line([(p[0] + 1, p[1] - 1) for p in path], fill=lite, width=1)
        d.line([(x + 4, h - 12), (x + 36, h - 12)], fill=dark, width=5)
    return soft(im, 0.5)


def coral(n, col, seed, pores=True):
    """plate coral top: concentric growth rings + pores, darker rim (texture is tiled on the top faces)"""
    a = fill(n, col, 6, seed) + N3(n, 8, seed + 1, 12)
    im = A(a); d = ImageDraw.Draw(im)
    rr = random.Random(seed)
    if pores:
        dots = [(rr.randint(0, n), rr.randint(0, n), rr.randint(2, 4)) for _ in range(420)]
        dk = tuple(int(c * 0.62) for c in col); lt = tuple(min(255, int(c * 1.2) + 10) for c in col)
        def f(dr, ox, oy):
            for (x, y, r) in dots:
                dr.ellipse((x + ox - r - 1, y + oy - r - 1, x + ox + r + 1, y + oy + r + 1), fill=lt)
                dr.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=dk)
        wrap_draw(im, f)
    return soft(im, 0.6)


def kelp(w=128, h=512, seed=81):
    """three swaying kelp strands, each a central stipe with broad overlapping blades on both sides (alpha cut-out)"""
    im = Image.new('RGB', (w, h), (40, 110, 40)); al = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(im); da = ImageDraw.Draw(al)
    rr = random.Random(seed)
    for strand in range(3):
        cx = w * (0.22 + 0.28 * strand) + rr.uniform(-4, 4)
        col = (rr.randint(50, 80), rr.randint(120, 160), rr.randint(35, 60))
        xs = lambda y: cx + 5 * math.sin(y / 38 + strand * 2)
        for y in range(h + 30, -30, -17):
            x = xs(y)
            for sd in (1, -1):
                L = rr.randint(14, 22); up = rr.randint(22, 34)
                leaf = [(x, y + 6), (x + sd * L * 0.7, y - up * 0.25), (x + sd * L, y - up * 0.8), (x + sd * L * 0.35, y - up), (x, y - up * 0.55)]
                for oy in (-h, 0, h):
                    lf = [(px, py + oy) for (px, py) in leaf]
                    da.polygon(lf, fill=255)
                    shade = rr.uniform(0.85, 1.15)
                    d.polygon(lf, fill=tuple(min(255, int(c * shade)) for c in col))
                    d.line([(x, y + oy + 4), (x + sd * L * 0.8, y + oy - up * 0.75)], fill=tuple(int(c * 0.72) for c in col), width=2)
        pts = [(xs(y), y) for y in range(h + 8, -9, -8)]
        da.line(pts, fill=255, width=5); d.line(pts, fill=(70, 96, 34), width=5)
    a = soft(im, 0.4); al = np.asarray(al.filter(ImageFilter.GaussianBlur(0.5)), np.float32)
    return a, al


def bubbles(w=128, h=256, seed=91, n=60):
    im = Image.new('RGB', (w, h), (230, 245, 255)); al = Image.new('L', (w, h), 0)
    da = ImageDraw.Draw(al)
    rr = random.Random(seed)
    for _ in range(n):
        x, y, r = rr.randint(8, w - 8), rr.randint(0, h), rr.randint(3, 11)
        for oy in (-h, 0, h):
            da.ellipse((x - r, y + oy - r, x + r, y + oy + r), outline=210, width=2)
            da.ellipse((x - r * 0.5, y + oy - r * 0.6, x - r * 0.1, y + oy - r * 0.2), fill=255)
    return np.asarray(im, np.float32), np.asarray(al, np.float32)


def caustics(n=256, seed=95):
    """bright wavy cell network (additive)"""
    rr = np.random.default_rng(seed)
    pts = rr.random((40, 2)) * n
    yy, xx = np.mgrid[0:n, 0:n]
    best = np.full((n, n), 1e9); second = np.full((n, n), 1e9)
    for (px, py) in pts:
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dd = np.hypot(xx - px - ox, yy - py - oy)
                second = np.minimum(second, np.maximum(best, dd)); best = np.minimum(best, dd)
    v = np.exp(-((second - best) / 3.5) ** 2)
    v = np.asarray(A(np.stack([v * 255] * 3, -1)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    return v * np.array([0.75, 0.95, 1.0])


def surface_under(n=256):
    """the water surface seen from below: bright rippled sheen"""
    c = caustics(n, 97)
    a = np.zeros((n, n, 3), np.float32) + C((60, 140, 175)) + N3(n, 14, 98, 18)
    return a + c * 0.75


# ------------------------------------------------------------------------------------------- backdrops
def reef_poster(w=2048, h=512):
    """aquarium background poster on the back glass: deep blue gradient, layered reef silhouettes, light rays"""
    y = np.linspace(0, 1, h)[:, None, None]
    top, bot = C((70, 170, 205)), C((10, 50, 92))
    a = np.zeros((h, w, 3), np.float32) + top * (1 - y) + bot * y
    im = A(a)
    # light rays from the top
    ray = Image.new('L', (w, h), 0); dr = ImageDraw.Draw(ray)
    rr = random.Random(5)
    for _ in range(18):
        x = rr.randint(0, w); ww = rr.randint(30, 90)
        dr.polygon([(x, 0), (x + ww, 0), (x + ww * 3 + 200, h), (x + 200, h)], fill=rr.randint(18, 40))
    ray = ray.filter(ImageFilter.GaussianBlur(14))
    im = Image.composite(Image.new('RGB', (w, h), (190, 240, 255)), im, ray)
    d = ImageDraw.Draw(im)
    # three layers of reef: far (pale), mid, near (dark, saturated)
    for layer, (base_y, col, amp) in enumerate(((0.62, (40, 110, 150), 60), (0.74, (36, 90, 120), 80), (0.86, (30, 70, 90), 70))):
        rr = random.Random(10 + layer)
        pts = [(0, h)]
        x = 0
        while x <= w:
            pts.append((x, h * base_y - rr.uniform(0, amp) - amp * 0.5 * math.sin(x / 140 + layer)))
            x += rr.randint(20, 60)
        pts.append((w, h))
        d.polygon(pts, fill=col)
        # coral heads / fans / branches on the ridge
        for _ in range(60 + layer * 30):
            x = rr.randint(0, w); yb = h * base_y + rr.uniform(-amp, 10)
            k = rr.random()
            c2 = tuple(int(v * (0.8 + layer * 0.15)) for v in rr.choice([(220, 90, 140), (240, 150, 60), (120, 200, 150), (150, 110, 210), (230, 210, 90)]))
            c2 = tuple(int(v * (0.55 + 0.2 * layer)) + int(cc * (0.45 - 0.2 * layer)) for v, cc in zip(c2, col))
            if k < 0.35:                                     # fan
                r = rr.randint(14, 34) + layer * 8
                d.pieslice((x - r, yb - r * 1.6, x + r, yb + r * 0.4), 200, 340, fill=c2)
            elif k < 0.7:                                    # branch coral
                for b in range(4):
                    ang = math.radians(rr.uniform(-60, 60) - 90)
                    L = rr.randint(14, 40) + layer * 8
                    d.line([(x, yb), (x + L * math.cos(ang), yb + L * math.sin(ang))], fill=c2, width=4 + layer)
            else:                                            # brain coral blob
                r = rr.randint(10, 26) + layer * 6
                d.ellipse((x - r, yb - r, x + r, yb + r * 0.4), fill=c2)
        # little fish silhouettes in the far water
        if layer == 0:
            for _ in range(40):
                fx, fy = rr.randint(0, w), rr.randint(int(h * 0.1), int(h * 0.55)); s = rr.randint(4, 9)
                d.ellipse((fx - s, fy - s * 0.4, fx + s, fy + s * 0.4), fill=(60, 130, 165))
                d.polygon([(fx - s, fy), (fx - s * 1.7, fy - s * 0.6), (fx - s * 1.7, fy + s * 0.6)], fill=(60, 130, 165))
    return soft(im, 1.0)


def room_wall(w=1024, h=512):
    """the living room outside the tank, blurred as if seen through glass and water"""
    a = np.zeros((h, w, 3), np.float32) + C((112, 92, 80))
    im = A(a); d = ImageDraw.Draw(im)
    for x in range(0, w, 32): d.line([(x, 0), (x, h)], fill=(122, 100, 88), width=10)       # wallpaper stripes
    d.rectangle((0, int(h * 0.78), w, h), fill=(80, 56, 40))                                   # skirting / floor
    d.rectangle((90, 70, 330, 300), fill=(150, 190, 220)); d.rectangle((96, 76, 324, 294), outline=(240, 236, 228), width=8)   # window
    d.line([(210, 76), (210, 294)], fill=(240, 236, 228), width=6); d.line([(96, 185), (324, 185)], fill=(240, 236, 228), width=6)
    d.rounded_rectangle((420, 250, 860, 420), 30, fill=(150, 60, 50))                          # sofa
    d.rounded_rectangle((400, 300, 470, 430), 20, fill=(130, 50, 42)); d.rounded_rectangle((810, 300, 880, 430), 20, fill=(130, 50, 42))
    d.ellipse((900, 120, 980, 200), fill=(250, 230, 160)); d.line([(940, 200), (940, 400)], fill=(60, 50, 40), width=6)       # lamp
    d.rectangle((560, 90, 720, 200), fill=(60, 80, 70)); d.rectangle((566, 96, 714, 194), fill=(200, 160, 90))              # picture
    return soft(im, 4.0)


# ------------------------------------------------------------------------------------------- props
def plastic(n, col, seed, slots=False):
    a = fill(n, col, 3, seed)
    if slots:
        for y in range(24, n - 24, 18):
            a[y:y + 8, 24:n - 24] *= 0.35
    return a


def brass(n, seed, col=(176, 132, 64)):
    a = fill(n, col, 6, seed) + N3(n, 16, seed + 1, 14)
    g = noise(n, 6, seed + 2)
    a[..., 1] += np.clip(g, 0, None)[...] * 14; a[..., 2] += np.clip(g, 0, None) * 20         # verdigris patches
    im = A(a); d = ImageDraw.Draw(im)
    for y in (8, n - 9):
        for x in range(8, n, 24):
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(206, 170, 96)); d.ellipse((x - 2, y - 3, x + 2, y + 1), fill=(240, 214, 150))
    d.line([(0, 16), (n, 16)], fill=(120, 86, 40), width=2); d.line([(0, n - 17), (n, n - 17)], fill=(120, 86, 40), width=2)
    return soft(im, 0.5)


def porthole(n=256):
    a = brass(n, 71)
    im = A(a); d = ImageDraw.Draw(im)
    c = n // 2
    d.ellipse((c - 92, c - 92, c + 92, c + 92), fill=(196, 152, 80), outline=(110, 80, 36), width=6)
    d.ellipse((c - 70, c - 70, c + 70, c + 70), fill=(30, 70, 90))
    d.ellipse((c - 54, c - 60, c - 10, c - 30), fill=(90, 150, 170))
    for k in range(8):
        ang = 2 * math.pi * k / 8; x, y = c + 82 * math.cos(ang), c + 82 * math.sin(ang)
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(236, 206, 140))
    return soft(im, 0.5)


def planks_gold(n=256, seed=33):
    a = fill(n, (120, 72, 36), 6, seed)
    for k in range(4):
        y = k * n // 4
        a[y:y + 3] *= 0.5
        a[y + 3:y + n // 4] *= np.random.default_rng(seed + k).uniform(0.88, 1.08)
    a += N3(n, 1, seed + 9, 4) * np.array([1, 0.8, 0.6]) + (noise(n, 3, seed + 8)[:, :, None] * np.array([10, 6, 3]))
    im = A(a); d = ImageDraw.Draw(im)
    for x in (0, n - 20):                                      # gold straps
        d.rectangle((x, 0, x + 20, n), fill=(214, 172, 60)); d.line([(x + 3, 0), (x + 3, n)], fill=(250, 220, 120), width=2)
        for y in range(16, n, 48): d.ellipse((x + 6, y - 4, x + 14, y + 4), fill=(140, 100, 30))
    return soft(im, 0.5)


def gold(n, seed):
    a = fill(n, (220, 176, 60), 5, seed) + N3(n, 10, seed + 1, 16)
    return a


def coins(n=128, seed=41):
    a = np.zeros((n, n, 3), np.float32) + C((160, 120, 40))
    im = A(a); d = ImageDraw.Draw(im)
    for y in range(0, n, 8):                                   # coin stack edges
        d.line([(0, y), (n, y)], fill=(250, 214, 110), width=5); d.line([(0, y + 6), (n, y + 6)], fill=(120, 86, 24), width=2)
    return soft(im, 0.6)


def chest_lock(w=128, h=128):
    a = gold(w, 45)
    im = A(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((24, 30, 104, 110), 10, fill=(196, 150, 50), outline=(110, 80, 20), width=4)
    d.ellipse((54, 54, 74, 74), fill=(30, 20, 10)); d.polygon([(58, 70), (70, 70), (66, 92), (62, 92)], fill=(30, 20, 10))
    return soft(im, 0.5)


def eye(team):
    n = 128
    col = (255, 60, 40) if team == 'red' else (60, 150, 255)
    a = np.zeros((n, n, 3), np.float32) + C((24, 20, 18))
    im = A(a); d = ImageDraw.Draw(im)
    d.ellipse((12, 30, 116, 98), fill=tuple(int(c * 0.5) for c in col))
    d.ellipse((30, 40, 98, 88), fill=col); d.ellipse((50, 50, 78, 78), fill=(255, 250, 220))
    return soft(im, 2.0)


def banner(team):
    w, h = 128, 256
    col = (200, 40, 36) if team == 'red' else (36, 90, 210)
    a = fill(w, col, 4, 51 if team == 'red' else 52, h)
    im = A(a); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 14), fill=(230, 196, 90)); d.rectangle((0, h - 30, w, h - 18), fill=(230, 196, 90))
    # fish emblem
    d.ellipse((24, 92, 96, 140), fill=(250, 236, 200)); d.polygon([(30, 116), (6, 94), (6, 138)], fill=(250, 236, 200))
    d.ellipse((76, 108, 84, 116), fill=col)
    for k in range(5): d.polygon([(k * 26, h - 18), (k * 26 + 13, h), (k * 26 + 26, h - 18)], fill=col)
    return soft(im, 0.5)


def plaque(text, col):
    w, h = 512, 128
    a = fill(w, (206, 186, 146), 5, 71, h)
    im = A(a); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(120, 100, 70), width=6)
    text_c(d, (w // 2, h // 2 + 2), text, 52, col, maxw=w - 40, stroke=2, stroke_fill=(90, 70, 40))
    return soft(im, 0.4)


def filter_label():
    w, h = 512, 128
    a = np.zeros((h, w, 3), np.float32) + C((30, 32, 36))
    im = A(a); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w - 9, h - 9), 18, outline=(80, 200, 240), width=5)
    text_c(d, (w // 2, h // 2 - 4), 'PADFLOW 3000', 60, (230, 240, 250), maxw=w - 60)
    return soft(im, 0.4)


def jumppad_tex():
    """air stone disc of the bubble lifts"""
    n = 256
    a = rock(n, (120, 130, 140), 21, strata=False)
    im = A(a); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 252, 252), outline=(60, 70, 80), width=10)
    rr = random.Random(22)
    for _ in range(260):
        x, y = rr.randint(30, 226), rr.randint(30, 226)
        if (x - 128) ** 2 + (y - 128) ** 2 < 96 ** 2:
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(50, 56, 64))
    d.ellipse((96, 96, 160, 160), outline=(170, 230, 255), width=6)
    return soft(im, 0.5)


# ------------------------------------------------------------------------------------------- write everything
def make_textures(W):
    n = 256
    W.save('gravel', gravel(n, 1, [(150, 140, 120), (120, 112, 98), (178, 168, 150), (100, 96, 90), (196, 186, 166), (140, 120, 100), (90, 130, 160), (170, 110, 90)]))
    W.save('sand', fill(n, (194, 178, 140), 8, 2) + N3(n, 18, 3, 10) + N3(n, 0.7, 4, 6))
    W.save('rock', rock(n, (118, 112, 104), 5))
    W.save('rock_dark', rock(n, (84, 82, 80), 6))
    W.save('rock_moss', rock(n, (104, 116, 92), 7) + N3(n, 6, 8, 10) * np.array([0.3, 1, 0.2]))
    W.save('sandstone', ashlar(n, (212, 190, 148), 11))
    W.save('sandstone_big', ashlar(n, (204, 182, 140), 12, rows=2, cols=(1, 2)))
    W.save('sandstone_plain', fill(n, (214, 194, 152), 6, 13) + N3(n, 22, 14, 10))
    W.save('flagstone', flagstones(n, (200, 180, 140), 15))
    W.save('face_stone', ashlar(n, (190, 172, 136), 16, rows=3) * 0.97)
    W.save('key_band', key_band())
    W.save('pillar', np.tile(np.asarray(Image.fromarray(np.clip(fill(64, (214, 194, 150), 5, 17), 0, 255).astype(np.uint8)), np.float32), (4, 4, 1))
           * (0.78 + 0.22 * np.abs(np.sin(np.linspace(0, 8 * math.pi, 256))))[None, :, None])
    for nme, col, sd in (('coral_purple', (150, 80, 200), 31), ('coral_magenta', (220, 60, 170), 32), ('coral_green', (90, 200, 130), 33),
                         ('coral_blue', (80, 110, 210), 34), ('coral_red', (200, 60, 50), 35), ('coral_yellow', (230, 200, 70), 36),
                         ('coral_orange', (240, 130, 50), 37)):
        W.save(nme, coral(n, col, sd))
    W.save('coral_stalk', rock(n, (170, 140, 150), 38, strata=False) + N3(n, 2, 39, 8))
    k, ka = kelp(); W.save('kelp', k, ka)
    k, ka = kelp(seed=82); W.save('kelp2', k * np.array([0.8, 1.05, 1.2]), ka)
    b, ba = bubbles(); W.save('bubbles', b, ba)
    W.save('caustics', caustics())
    W.save('surface', surface_under())
    W.save('water', fill(n, (40, 110, 140), 4, 96) + N3(n, 10, 97, 14))
    W.save('glass', fill(64, (160, 210, 220), 2, 98))
    W.save('reef_poster', reef_poster())
    W.save('room_wall', room_wall())
    W.save('room_floor', fill(n, (96, 64, 40), 6, 99) + N3(n, 1, 100, 6))
    W.save('tank_frame', fill(64, (24, 26, 30), 2, 101))
    W.save('filter_body', plastic(n, (40, 44, 50), 102, slots=True))
    W.save('filter_plain', plastic(n, (44, 48, 54), 103))
    W.save('filter_label', filter_label())
    W.save('brass', brass(n, 72))
    W.save('porthole', porthole())
    W.save('bell_roof', fill(n, (150, 120, 70), 6, 73) + N3(n, 12, 74, 12))
    W.save('chest_wood', planks_gold())
    W.save('gold', gold(n, 43))
    W.save('coins', coins())
    W.save('chest_lock', chest_lock())
    W.save('eye_red', eye('red')); W.save('eye_blue', eye('blue'))
    W.save('banner_red', banner('red')); W.save('banner_blue', banner('blue'))
    W.save('plaque_red', plaque('TEMPLE OF THE RED KRAKEN', (150, 30, 24)))
    W.save('plaque_blue', plaque('TEMPLE OF THE BLUE LEVIATHAN', (28, 64, 160)))
    W.save('jumppad', jumppad_tex())
    W.save('rubber', fill(64, (60, 64, 70), 3, 104))
    W.save('nodraw_ns', fill(64, (200, 60, 200), 2, 105))
    W.save('fog', fill(64, (40, 100, 140), 2, 106))


# ----------------------------------------------------------------------------------------------- shader
SH = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padtank/tank_textures.py)\n\n"
STEPS = {'gravel': 'sandsteps', 'sand': 'sandsteps', 'chest_wood': 'woodsteps', 'coral_purple': 'softsteps', 'coral_magenta': 'softsteps',
         'coral_green': 'softsteps', 'coral_blue': 'softsteps', 'coral_red': 'softsteps', 'coral_yellow': 'softsteps', 'coral_orange': 'softsteps'}
CAUSTIC = {'gravel', 'sand', 'rock', 'rock_dark', 'rock_moss', 'sandstone', 'sandstone_big', 'sandstone_plain', 'flagstone', 'face_stone',
           'key_band', 'pillar', 'coral_stalk', 'coral_purple', 'coral_magenta', 'coral_green', 'coral_blue', 'coral_red', 'coral_yellow',
           'coral_orange', 'brass', 'porthole', 'bell_roof', 'chest_wood', 'gold', 'coins'}
SHINY = {'brass': 0.18, 'porthole': 0.18, 'gold': 0.35, 'coins': 0.3, 'chest_lock': 0.3, 'glass': 0.2, 'filter_body': 0.08, 'filter_plain': 0.08,
         'tank_frame': 0.1}


def lm(name, steps=None, extra='', caustic=False, shiny=0.0):
    s = f'textures/{NS}/{name}\n{{\n\tqer_editorimage textures/{NS}/{name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    if shiny:
        s += f'\t{{\n\t\tmap textures/{NS}/{name}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {shiny} {shiny} {shiny} )\n\t\ttcGen environment\n\t}}\n'
    if caustic:      # light dancing on everything under the water surface
        s += (f'\t{{\n\t\tmap textures/{NS}/caustics\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.16 0.2 0.22 )\n'
              '\t\ttcMod scale 0.5 0.5\n\t\ttcMod turb 0 0.04 0 0.08\n\t\ttcMod scroll 0.012 0.018\n\t}\n')
    return s + '}\n\n'


def make_shader(W, out):
    S = SH
    special = {'caustics', 'surface', 'water', 'glass', 'kelp', 'kelp2', 'bubbles', 'nodraw_ns', 'fog', 'eye_red', 'eye_blue',
               'banner_red', 'banner_blue', 'jumppad', 'reef_poster', 'room_wall', 'filter_label'}
    for nme in sorted(W.sizes):
        if nme in special: continue
        S += lm(nme, STEPS.get(nme), caustic=nme in CAUSTIC, shiny=SHINY.get(nme, 0))
    S += lm('jumppad', extra='\tq3map_surfacelight 80\n\tq3map_lightRGB 0.5 0.9 1\n')
    S += lm('reef_poster', extra='\tq3map_nonplanar\n')
    S += lm('room_wall')
    S += lm('filter_label', extra='\tq3map_surfacelight 120\n\tq3map_lightRGB 0.4 0.8 1\n')
    (fr, fg, fb), fd = FOG
    S += f'''textures/{NS}/fog
{{
	qer_editorimage textures/{NS}/fog
	qer_trans 0.3
	surfaceparm fog
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	fogparms ( {fr} {fg} {fb} ) {fd}
}}

textures/{NS}/surface
{{
	qer_editorimage textures/{NS}/surface
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	{{
		map textures/{NS}/surface
		rgbGen identity
		tcMod turb 0 0.02 0 0.1
		tcMod scroll 0.01 0.006
	}}
	{{
		map textures/{NS}/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.45 0.5 )
		tcMod scale 0.7 0.7
		tcMod scroll -0.02 0.015
	}}
}}

textures/{NS}/water
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	tessSize 128
	deformVertexes wave 300 sin 0 2 0 0.3
	{{
		map textures/{NS}/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.5
		rgbGen identity
		tcMod turb 0 0.05 0 0.15
		tcMod scroll 0.01 0.007
	}}
	{{
		map textures/{NS}/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.16 0.18 )
		tcMod scale 0.6 0.6
		tcMod scroll -0.015 0.02
	}}
}}

textures/{NS}/water_inner
{{
	qer_editorimage textures/{NS}/water
	qer_trans 0.3
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nomarks
}}

textures/{NS}/glass
{{
	qer_editorimage textures/{NS}/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	{{
		map textures/{NS}/glass
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
	{{
		map textures/{NS}/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.1 0.12 0.13 )
		tcGen environment
	}}
}}

textures/{NS}/nodraw_ns
{{
	qer_editorimage textures/{NS}/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
}}

textures/{NS}/bubbles
{{
	qer_editorimage textures/{NS}/bubbles
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	deformVertexes autosprite2
	{{
		map textures/{NS}/bubbles.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen const ( 0.85 0.95 1 )
		tcMod scroll 0.03 -0.45
	}}
}}

'''
    for k in ('kelp', 'kelp2'):
        S += f'''textures/{NS}/{k}
{{
	qer_editorimage textures/{NS}/{k}.tga
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm alphashadow
	cull disable
	tessSize 64
	deformVertexes wave 160 sin 0 9 0 0.35
	{{
		map textures/{NS}/{k}.tga
		alphaFunc GE128
		depthWrite
		rgbGen vertex
	}}
}}

'''
    for team in ('red', 'blue'):
        lc = '1 0.25 0.15' if team == 'red' else '0.25 0.55 1'
        S += f'''textures/{NS}/eye_{team}
{{
	qer_editorimage textures/{NS}/eye_{team}
	surfaceparm nolightmap
	q3map_surfacelight 900
	q3map_lightRGB {lc}
	{{
		map textures/{NS}/eye_{team}
		rgbGen wave sin 0.85 0.15 0 0.4
	}}
}}

textures/{NS}/banner_{team}
{{
	qer_editorimage textures/{NS}/banner_{team}
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	cull disable
	tessSize 32
	deformVertexes wave 96 sin 0 5 0 0.45
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map textures/{NS}/banner_{team}
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

'''
    S += fish_models.shaders()
    S += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', NS + '.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ctl 1lc ffa team ft"\n}\n' % (MAP, LONGNAME))


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    fish_models.make_textures(out)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
