"""Procedural textures + shader + arena for wop_padplayroom (Padman's Playroom).
All art is original and generated here. make_all(out) writes textures/playroom/*, env/playroom/*,
scripts/playroom.shader and scripts/wop_padplayroom.arena (pk3dir layout)."""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

R = random.Random(23)
FONTB = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
if not os.path.exists(FONTB):
    FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MAP = 'wop_padplayroom'


# ----------------------------------------------------------------------------------------------- helpers
def noise(n, blur, seed, m=None):
    m = m or n
    r = np.random.default_rng(seed)
    im = Image.fromarray((r.random((m, n)) * 255).astype(np.uint8), 'L')
    big = Image.new('L', (n * 3, m * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * n, j * m))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(big.crop((n, m, 2 * n, 2 * m)), dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def C(c): return np.array(c, np.float32)
def N3(n, blur, seed, amp, m=None): return noise(n, blur, seed, m)[..., None] * amp
def img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


def fill(n, col, grain=4, seed=0, m=None):
    m = m or n
    return np.zeros((m, n, 3), np.float32) + C(col) + N3(n, 1.2, seed, grain, m) + N3(n, 12, seed + 1, grain, m)


def font(sz): return ImageFont.truetype(FONTB, sz)


def text_c(d, xy, text, sz, fill, maxw=None, anchor='mm', stroke=0, stroke_fill=None):
    f = font(sz)
    while maxw and d.textlength(text, font=f) > maxw and sz > 8:
        sz -= 2; f = font(sz)
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


class TexWriter:
    def __init__(self, out):
        self.dir = os.path.join(out, 'textures', 'playroom'); os.makedirs(self.dir, exist_ok=True)
        self.out = out
        self.sizes = {}

    def save(self, name, a, alpha=None):
        im = img(a) if isinstance(a, np.ndarray) else a.convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA'); im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), 'L'))
            im.save(os.path.join(self.dir, name + '.tga'))
        else:
            im.save(os.path.join(self.dir, name + '.jpg'), quality=92)
        self.sizes[name] = im.size


def planks(n, base, nplank, seed, gap=(60, 40, 25), vertical=False, knots=True):
    """wood planks running along x (rows = planks)"""
    rr = random.Random(seed)
    a = np.zeros((n, n, 3), np.float32)
    ph = n // nplank
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    for p in range(nplank):
        tint = C(base) * rr.uniform(0.86, 1.1)
        s = rr.randint(0, 999)
        g = noise(n, 0.8, seed * 31 + p)  # fine noise
        streak = noise(n, 6, seed * 17 + p)
        # grain: stretched noise along x
        gr = np.asarray(Image.fromarray(((noise(n // 8, 1, s) + 3) * 40).clip(0, 255).astype(np.uint8)).resize((n, n * 4), Image.BICUBIC)
                        .crop((0, 0, n, n)).transpose(Image.Transpose.TRANSPOSE), np.float32) / 40 - 3
        blk = tint + (gr[..., None] * 9) + g[..., None] * 3 + streak[..., None] * 5
        y0, y1 = p * ph, (p + 1) * ph
        a[y0:y1] = blk[y0:y1]
        a[y0:y0 + 1] = C(gap); a[y1 - 1:y1] = a[y1 - 1:y1] * 0.8
        cut = rr.randint(0, n - 1)
        a[y0:y1, cut:cut + 1] = C(gap)
        if knots:
            for _ in range(rr.randint(0, 2)):
                kx, ky = rr.randint(0, n - 1), rr.randint(y0 + 4, y1 - 4)
                d = np.sqrt(((xx - kx) / 2.2) ** 2 + (yy - ky) ** 2)
                m = (d < 6) & (yy >= y0) & (yy < y1)
                a[m] = a[m] * 0.7
    if vertical: a = a.transpose(1, 0, 2)
    return a


# ----------------------------------------------------------------------------------------------- textures
def make_textures(W):
    n = 256
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)

    # floor: honey oak planks (scale 2 -> 512u per tile, 4 planks of 128u)
    W.save('floor_wood', planks(256, (186, 132, 78), 4, 3))
    # small planks for the dollhouse floors and wardrobe floor
    W.save('dh_floor', planks(256, (205, 165, 110), 8, 5))
    W.save('old_boards', planks(256, (120, 92, 66), 4, 9, gap=(30, 22, 15)) * 0.9)
    # pine / birch / walnut solid woods
    W.save('pine', planks(256, (222, 186, 130), 2, 11, gap=(200, 160, 110), knots=True))
    W.save('birch', planks(256, (230, 210, 175), 1, 13, gap=(230, 210, 175), knots=False))
    W.save('walnut', planks(256, (120, 78, 48), 2, 17, gap=(95, 60, 38)))
    W.save('wood_white', fill(n, (236, 234, 228), 3, 19))
    W.save('wood_mint', fill(n, (168, 222, 200), 3, 21))

    # wallpaper: soft sky blue, puffy clouds + tiny stars (scale 2 -> 512u tile)
    a = fill(n, (156, 200, 236), 2, 23)
    im = img(a); d = ImageDraw.Draw(im)
    for (cx, cy, s) in ((60, 70, 1.0), (190, 180, 0.8), (200, 40, 0.55), (70, 210, 0.6)):
        for (dx, dy, r) in ((-18, 4, 14), (0, -6, 18), (18, 2, 14), (6, 8, 13), (-8, 9, 12)):
            for ox in (-256, 0, 256):
                for oy in (-256, 0, 256):
                    x, y, rr = cx + dx * s + ox, cy + dy * s + oy, r * s
                    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(246, 250, 255))
    for (sx, sy) in ((130, 100), (30, 140), (230, 110), (120, 230), (160, 30), (20, 30)):
        pts = [(sx + (7 if k % 2 == 0 else 3) * math.cos(math.pi / 2 + k * math.pi / 5),
                sy - (7 if k % 2 == 0 else 3) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=(255, 220, 90))
    W.save('wallpaper', np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), np.float32) + N3(n, 1, 24, 2))
    # dado (lower wall): white with vertical sky stripes
    a = fill(n, (240, 244, 248), 2, 25)
    for i in range(8):
        a[:, i * 32 + 4:i * 32 + 14] = C((190, 214, 236)) + N3(n, 1, 26, 2)[:, :10]
    W.save('dado', a)
    W.save('dado_rail', fill(n, (250, 250, 248), 2, 27))
    W.save('skirting', fill(n, (248, 248, 244), 2, 28))
    W.save('ceiling', fill(n, (238, 238, 232), 3, 29))
    W.save('plaster_rough', fill(n, (176, 160, 140), 10, 31) + N3(n, 0.5, 32, 8))

    # duvet: navy with yellow stars and moons ------------------------------------------------
    a = fill(n, (46, 70, 140), 3, 33)
    im = img(a); d = ImageDraw.Draw(im)
    for (sx, sy, r) in ((40, 40, 14), (170, 70, 10), (100, 150, 16), (220, 200, 12), (40, 220, 9), (230, 20, 8)):
        pts = [(sx + (r if k % 2 == 0 else r * 0.45) * math.cos(math.pi / 2 + k * math.pi / 5),
                sy - (r if k % 2 == 0 else r * 0.45) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=(255, 214, 80))
    for (mx, my) in ((200, 130), (60, 110)):
        d.ellipse((mx - 14, my - 14, mx + 14, my + 14), fill=(250, 240, 200)); d.ellipse((mx - 6, my - 18, mx + 18, my + 10), fill=(46, 70, 140))
    W.save('duvet', np.asarray(im, np.float32) + N3(n, 0.6, 34, 4))
    # pillowcase: soft white cotton, gentle puckering, faint pale-blue stripes and a stitched seam
    a = fill(n, (248, 248, 244), 2, 35) + N3(n, 10, 135, 7) + N3(n, 0.6, 136, 2)
    for i in range(0, n, 64): a[:, i + 20:i + 44] = a[:, i + 20:i + 44] * C((0.93, 0.96, 1.0))
    for j in range(4, n, 12): a[j:j + 2, 2:4] *= 0.9; a[j:j + 2, n - 4:n - 2] *= 0.9
    W.save('pillow', a)
    a = fill(n, (236, 236, 240), 3, 36)
    for i in range(0, n, 64):
        a[i:i + 2, :] *= 0.85; a[:, i:i + 2] *= 0.85
    W.save('mattress', a)
    W.save('sheet', fill(n, (232, 240, 250), 3, 37))

    # laminate desk top + PC case --------------------------------------------------------------
    W.save('laminate', fill(n, (244, 244, 242), 2, 41))
    a = fill(n, (48, 50, 56), 3, 42)
    for i in range(0, n, 16): a[i:i + 8, 20:236] = C((36, 38, 42))
    a[40:48, 20:236] = C((80, 255, 160))
    W.save('pc_case', a)
    W.save('pc_led', fill(64, (120, 255, 190), 2, 43))
    W.save('plastic_black', fill(n, (34, 34, 38), 3, 44))
    W.save('plastic_grey', fill(n, (150, 154, 160), 3, 45))
    W.save('metal_chrome', fill(n, (196, 200, 206), 6, 46) + N3(n, 30, 47, 10))

    # drawer front (fit 256x128): painted pastel with round knob
    for nme, col in (('drawer_mint', (168, 222, 200)), ('drawer_sky', (160, 204, 238)), ('drawer_sun', (250, 214, 110))):
        a = fill(256, col, 3, 48, 128)
        im = img(a); d = ImageDraw.Draw(im)
        d.rectangle((6, 6, 249, 121), outline=tuple(int(c * 0.8) for c in col), width=4)
        d.ellipse((112, 48, 144, 80), fill=(250, 250, 250), outline=(120, 120, 120), width=2)
        W.save(nme, im)

    # books: covers and page edges
    for nme, col in (('book_red', (200, 50, 46)), ('book_blue', (40, 90, 180)), ('book_green', (50, 150, 80)),
                     ('book_yellow', (240, 190, 40)), ('book_purple', (130, 70, 170)), ('book_orange', (240, 120, 30))):
        a = fill(n, col, 4, hash(nme) % 97)
        a[:, :10] *= 0.8
        W.save(nme, a)
    a = fill(n, (238, 230, 205), 2, 49)
    for i in range(0, n, 3): a[i, :] *= 0.94
    W.save('pages', a)

    # radiator fins / window frame / sill / glass
    a = fill(n, (246, 246, 244), 2, 51)
    for i in range(0, n, 32):
        a[:, i:i + 4] *= 0.78; a[:, i + 4:i + 8] *= 0.9
    W.save('radiator', a)
    W.save('frame_white', fill(n, (250, 250, 250), 2, 52))
    a = fill(n, (232, 230, 226), 4, 53) + N3(n, 3, 54, 6)
    W.save('sill_marble', a)
    W.save('glass', fill(64, (200, 230, 245), 1, 55))

    # dollhouse --------------------------------------------------------------------------------
    a = fill(n, (246, 170, 190), 3, 61)                    # pink clapboard
    for i in range(0, n, 32):
        a[i:i + 3] *= 0.75; a[i + 3:i + 8] *= 1.04
    W.save('dh_clapboard', a)
    W.save('dh_trim', fill(n, (252, 250, 245), 2, 62))
    a = fill(n, (190, 60, 50), 4, 63)                       # roof shingles
    for r in range(0, n, 32):
        off = 16 if (r // 32) % 2 else 0
        a[r:r + 3] *= 0.6
        for c in range(off, n + 32, 32): a[r:r + 32, c % n:c % n + 2] *= 0.7
        a[r + 20:r + 32] *= 0.9
    W.save('roof_tiles', a)
    a = fill(n, (255, 236, 170), 2, 64)                     # yellow flower wallpaper
    im = img(a); d = ImageDraw.Draw(im)
    for (fx, fy) in ((32, 32), (160, 32), (96, 128), (224, 128), (32, 224), (160, 224)):
        for k in range(5):
            ang = k * 2 * math.pi / 5
            px, py = fx + 9 * math.cos(ang), fy + 9 * math.sin(ang)
            d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(250, 140, 150))
        d.ellipse((fx - 4, fy - 4, fx + 4, fy + 4), fill=(250, 200, 60))
    W.save('dh_wall_flower', im)
    a = fill(n, (200, 240, 220), 2, 65)
    for i in range(0, n, 32): a[:, i:i + 12] = C((170, 225, 200)) + N3(n, 1, 66, 2)[:, :12]
    W.save('dh_wall_stripe', a)
    # dollhouse door (fit 128x256): red door, white frame, brass knob, little window
    im = Image.new('RGB', (128, 256), (250, 250, 245)); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, 117, 255), fill=(200, 50, 60))
    d.rectangle((22, 24, 105, 120), outline=(160, 35, 45), width=4)
    d.rectangle((22, 136, 105, 240), outline=(160, 35, 45), width=4)
    d.ellipse((92, 136, 106, 150), fill=(240, 200, 80))
    d.ellipse((44, 40, 84, 80), fill=(170, 220, 250), outline=(250, 250, 245), width=4)
    W.save('dh_door', np.asarray(im, np.float32) + N3(1, 0, 1, 0) if False else im)
    # dollhouse window (fit 128x128): white mullions, shutters
    im = Image.new('RGB', (128, 128), (250, 250, 245)); d = ImageDraw.Draw(im)
    d.rectangle((14, 14, 113, 113), fill=(140, 200, 240))
    for g in range(14, 114, 6): d.line((14, g, 113, g - 30), fill=(170, 220, 250), width=2)
    d.rectangle((60, 14, 67, 113), fill=(250, 250, 245)); d.rectangle((14, 60, 113, 67), fill=(250, 250, 245))
    d.rectangle((0, 0, 127, 127), outline=(250, 250, 245), width=8)
    W.save('dh_window', im)
    im = Image.new('RGB', (256, 64), (252, 250, 245)); d = ImageDraw.Draw(im)
    text_c(d, (128, 32), "PADMAN'S PLACE", 34, (200, 50, 60), maxw=240)
    W.save('dh_sign', im)

    # wardrobe ---------------------------------------------------------------------------------
    W.save('wardrobe', fill(n, (250, 246, 236), 3, 71))
    im = Image.new('RGB', (128, 512), (250, 246, 236)); d = ImageDraw.Draw(im)      # inner door panel (fit)
    for (y0, y1) in ((24, 230), (262, 488)):
        d.rectangle((16, y0, 111, y1), outline=(210, 200, 180), width=5)
    d.rectangle((0, 0, 127, 511), outline=(225, 215, 195), width=6)
    W.save('wardrobe_door', np.asarray(im, np.float32) + N3(128, 1, 72, 2, 512))
    for nme, col in (('fabric_red', (210, 60, 60)), ('fabric_blue', (60, 110, 200)), ('fabric_green', (70, 170, 100)),
                     ('fabric_yellow', (245, 200, 60)), ('fabric_denim', (70, 100, 150)), ('fabric_orange', (240, 130, 50))):
        a = fill(n, col, 5, hash(nme) % 89) + N3(n, 0.5, 73, 6)
        for i in range(0, n, 4): a[i, :] *= 0.95
        W.save(nme, a)
    # patterned fabrics for the wardrobe clothes
    a = fill(n, (245, 245, 240), 4, 140) + N3(n, 0.5, 141, 5)
    for i in range(0, n, 32): a[i:i + 12] = C((40, 70, 150)) + N3(n, 0.5, 142, 5)[i:i + 12]
    W.save('fabric_stripe', a)
    a = fill(n, (200, 40, 40), 4, 143) + N3(n, 0.5, 144, 5)
    for i in range(0, n, 64):
        a[i:i + 20] = a[i:i + 20] * 0.55; a[:, i:i + 20] = a[:, i:i + 20] * 0.55
        a[i + 40:i + 44] = C((240, 220, 120)); a[:, i + 40:i + 44] = C((240, 220, 120))
    W.save('fabric_check', a)
    im = Image.fromarray(np.clip(fill(n, (120, 70, 170), 4, 145), 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for yy in range(0, n, 32):
        for xx in range(0 if (yy // 32) % 2 == 0 else 16, n, 32): d.ellipse((xx + 4, yy + 4, xx + 14, yy + 14), fill=(250, 240, 250))
    W.save('fabric_dots', im)
    im = Image.new('RGB', (256, 128), (230, 120, 40)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, 22), fill=(250, 250, 250)); text_c(d, (128, 76), 'PAD KICKS', 40, (255, 255, 255), maxw=230)
    W.save('shoebox', im)
    W.save('cardboard', fill(n, (196, 160, 112), 6, 74) + N3(n, 0.6, 75, 5))
    W.save('dust', fill(n, (200, 196, 186), 6, 76) + N3(n, 0.5, 77, 10))

    # race track (orange plastic, slight lane marks) --------------------------------------------
    a = fill(n, (250, 120, 20), 3, 81)
    a[:, 124:132] = C((255, 200, 120))
    for i in range(0, n, 64): a[i:i + 32, 124:132] = C((250, 120, 20))
    W.save('track', a)
    W.save('track_side', fill(n, (232, 98, 10), 3, 82))
    W.save('track_support', fill(n, (60, 150, 230), 3, 83))

    # toy blocks with letters (fit 128 per face) ---------------------------------------------------
    for nme, col, ch in (('block_a', (220, 60, 60), 'A'), ('block_b', (60, 120, 220), 'B'), ('block_c', (60, 170, 90), 'C'),
                         ('block_d', (245, 190, 40), 'D'), ('block_p', (160, 90, 200), 'P')):
        im = Image.new('RGB', (128, 128), (232, 200, 150)); d = ImageDraw.Draw(im)
        d.rectangle((8, 8, 119, 119), fill=col)
        text_c(d, (64, 62), ch, 84, (255, 255, 255))
        W.save(nme, np.asarray(im, np.float32) + N3(128, 1, 84, 3))
    # brick toys: top with studs, side with seams (scale 1 -> 256u tile; studs every 32u)
    for nme, col in (('brick_red', (210, 40, 40)), ('brick_blue', (30, 90, 200)), ('brick_yellow', (250, 200, 30)),
                     ('brick_green', (40, 160, 70)), ('brick_white', (240, 240, 236))):
        a = fill(n, col, 2, hash(nme) % 79)
        for cy in range(16, n, 32):
            for cx in range(16, n, 32):
                dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                a[dd < 9] *= 1.12; a[(dd >= 9) & (dd < 11)] *= 0.72
                a[(dd < 9) & (yy < cy - 3)] *= 1.06
        W.save(nme + '_top', a)
        b = fill(n, col, 2, hash(nme) % 79 + 1)
        for i in range(0, n, 64): b[i:i + 2] *= 0.7
        W.save(nme, b)

    # jump pad top (fit 256) + rubber
    im = Image.new('RGB', (256, 256), (40, 40, 44)); d = ImageDraw.Draw(im)
    for r, c in ((124, (250, 200, 30)), (100, (40, 40, 44)), (86, (250, 120, 20)), (60, (40, 40, 44)), (46, (250, 60, 60))):
        d.ellipse((128 - r, 128 - r, 128 + r, 128 + r), fill=c)
    d.polygon([(128, 98), (152, 132), (138, 132), (138, 158), (118, 158), (118, 132), (104, 132)], fill=(255, 255, 255))
    W.save('jumppad', im)
    W.save('rubber', fill(n, (52, 52, 58), 4, 85))

    # aquarium ----------------------------------------------------------------------------------
    a = np.zeros((n, n, 3), np.float32)
    rr = random.Random(86)
    cols = [(80, 140, 230), (240, 110, 160), (250, 240, 240), (60, 200, 220), (250, 200, 80)]
    im = Image.new('RGB', (n, n), (90, 90, 110)); d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = rr.randint(-6, n + 6), rr.randint(-6, n + 6); r = rr.randint(3, 7)
        c = cols[rr.randint(0, 4)]; s = rr.uniform(0.75, 1.1)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.ellipse((x + ox - r, y + oy - r, x + ox + r, y + oy + r), fill=tuple(int(v * s) for v in c))
    W.save('gravel', im)
    a = fill(n, (40, 120, 170), 6, 87)
    W.save('water', a)
    # caustics (tileable)
    w1 = noise(n, 5, 88); w2 = noise(n, 5, 89)
    cst = np.clip(1.0 - np.abs(w1 - w2) * 2.2, 0, 1) ** 3 * 255
    W.save('caustics', np.stack([cst * 0.7, cst * 0.9, cst], -1))
    W.save('tank_frame', fill(n, (28, 30, 34), 2, 90))
    # treasure chest (fit)
    a = fill(n, (130, 80, 40), 4, 91)
    for i in (40, 120, 200): a[:, i:i + 10] = C((220, 180, 60))
    W.save('chest', a)

    # posters (fit 256x384 portrait) --------------------------------------------------------------
    def poster(name, bg, draw):
        im = Image.new('RGB', (256, 384), bg); d = ImageDraw.Draw(im)
        draw(im, d)
        d.rectangle((0, 0, 255, 383), outline=(255, 255, 255), width=8)
        W.save(name, np.asarray(im, np.float32) + N3(256, 1, hash(name) % 50, 2, 384))

    def p_hero(im, d):
        for k in range(24):     # sunburst
            a0, a1 = k * 2 * math.pi / 24, (k + 0.5) * 2 * math.pi / 24
            d.polygon([(128, 170), (128 + 400 * math.cos(a0), 170 + 400 * math.sin(a0)), (128 + 400 * math.cos(a1), 170 + 400 * math.sin(a1))],
                      fill=(255, 200, 40))
        d.ellipse((58, 92, 198, 232), fill=(255, 255, 255), outline=(30, 30, 40), width=6)
        text_c(d, (128, 160), 'P', 110, (220, 40, 50), stroke=4, stroke_fill=(30, 30, 40))
        d.rectangle((16, 268, 239, 360), fill=(30, 30, 40))
        text_c(d, (128, 300), 'PADMAN', 52, (255, 210, 40), maxw=220)
        text_c(d, (128, 342), 'THE TINY HERO', 20, (255, 255, 255), maxw=220)
        text_c(d, (128, 36), 'No. 1', 26, (30, 30, 40))
    poster('poster_hero', (250, 140, 40), p_hero)

    def p_space(im, d):
        rr = random.Random(5)
        for _ in range(120):
            x, y = rr.randint(0, 255), rr.randint(0, 383); d.point((x, y), fill=(255, 255, 255))
        d.ellipse((40, 60, 200, 220), fill=(230, 120, 60)); d.ellipse((10, 120, 230, 160), outline=(240, 210, 150), width=6)
        d.ellipse((170, 240, 230, 300), fill=(120, 190, 250)); d.ellipse((30, 260, 70, 300), fill=(200, 200, 210))
        text_c(d, (128, 345), 'PLANETS', 44, (255, 255, 255), maxw=220)
    poster('poster_space', (20, 24, 60), p_space)

    def p_duck(im, d):
        d.ellipse((50, 140, 210, 280), fill=(255, 220, 40)); d.ellipse((120, 70, 220, 170), fill=(255, 220, 40))
        d.polygon([(214, 112), (250, 124), (214, 136)], fill=(250, 130, 30)); d.ellipse((176, 98, 192, 114), fill=(20, 20, 20))
        for i in range(5): d.arc((-40 + i * 70, 280, 40 + i * 70, 330), 0, 180, fill=(255, 255, 255), width=5)
        text_c(d, (128, 40), 'KILLER DUCK', 34, (255, 255, 255), maxw=230, stroke=2, stroke_fill=(20, 60, 120))
        text_c(d, (128, 355), 'BEWARE!', 30, (255, 255, 255))
    poster('poster_duck', (70, 160, 230), p_duck)

    def p_map(im, d):
        a = np.asarray(im, np.float32) + N3(256, 8, 9, 14, 384)
        im.paste(img(a))
        d.line([(40, 330), (80, 280), (60, 220), (130, 200), (150, 140), (210, 90)], fill=(140, 60, 30), width=4)
        d.line([(196, 76), (224, 104)], fill=(200, 30, 30), width=8); d.line([(224, 76), (196, 104)], fill=(200, 30, 30), width=8)
        d.polygon([(30, 60), (90, 40), (110, 110), (60, 140)], outline=(90, 60, 30), width=4)
        text_c(d, (128, 30), 'TREASURE', 34, (90, 50, 20))
    poster('poster_map', (226, 200, 150), p_map)

    # crayon drawing (fit 256x192): house, sun, stick-padman
    im = Image.new('RGB', (256, 192), (252, 252, 248)); d = ImageDraw.Draw(im)
    d.ellipse((190, 14, 236, 60), fill=(255, 210, 40))
    for k in range(10):
        a0 = k * math.pi / 5; d.line((213 + 28 * math.cos(a0), 37 + 28 * math.sin(a0), 213 + 40 * math.cos(a0), 37 + 40 * math.sin(a0)), fill=(255, 190, 30), width=3)
    d.rectangle((40, 100, 120, 170), outline=(220, 60, 60), width=4); d.polygon([(30, 100), (80, 56), (130, 100)], outline=(60, 120, 220), width=4)
    d.line((0, 172, 256, 176), fill=(60, 180, 80), width=6)
    d.ellipse((160, 96, 184, 120), outline=(30, 30, 30), width=3); d.line((172, 120, 172, 150), fill=(30, 30, 30), width=3)
    d.line((172, 150, 160, 170), fill=(30, 30, 30), width=3); d.line((172, 150, 184, 170), fill=(30, 30, 30), width=3)
    d.line((156, 130, 188, 130), fill=(30, 30, 30), width=3)
    text_c(d, (172, 86), 'ME', 14, (220, 60, 60))
    W.save('drawing', im)

    # clock face, tv screen frames, ruler, chessboard, toy box sign, playmat rug
    im = Image.new('RGB', (128, 128), (255, 255, 250)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 123, 123), fill=(255, 255, 250), outline=(220, 50, 50), width=8)
    for k in range(12):
        a0 = k * math.pi / 6; d.line((64 + 44 * math.cos(a0), 64 + 44 * math.sin(a0), 64 + 52 * math.cos(a0), 64 + 52 * math.sin(a0)), fill=(30, 30, 30), width=4)
    d.line((64, 64, 64, 28), fill=(30, 30, 30), width=5); d.line((64, 64, 92, 72), fill=(30, 30, 30), width=4)
    W.save('clock', im)
    for k in range(3):     # tv frames for the animated screen
        im = Image.new('RGB', (256, 128), (20, 30, 70)); d = ImageDraw.Draw(im)
        d.rectangle((0, 96, 255, 127), fill=(60, 170, 60))
        for i in range(6):
            x = (i * 48 + k * 16) % 256
            d.rectangle((x, 80, x + 20, 96), fill=(160, 90, 40))
        px = 40 + k * 60
        d.ellipse((px, 60 - (k % 2) * 14, px + 22, 82 - (k % 2) * 14), fill=(255, 220, 40))
        d.ellipse((180, 20, 220, 50), fill=(250, 250, 250))
        text_c(d, (128, 14), 'SCORE 0%d50' % (k + 1), 14, (255, 255, 255))
        W.save('tv%d' % k, im)
    im = Image.new('RGB', (512, 64), (250, 220, 120)); d = ImageDraw.Draw(im)
    for i in range(0, 512, 8):
        h = 22 if i % 80 == 0 else (14 if i % 40 == 0 else 8)
        d.line((i, 0, i, h), fill=(40, 30, 20), width=2)
        if i % 80 == 0: text_c(d, (i + 2, 40), str(i // 80), 18, (40, 30, 20), anchor='lm')
    W.save('ruler', im)
    im = Image.new('RGB', (256, 256)); d = ImageDraw.Draw(im)
    for i in range(8):
        for j in range(8):
            d.rectangle((i * 32, j * 32, i * 32 + 31, j * 32 + 31), fill=(240, 230, 210) if (i + j) % 2 == 0 else (90, 60, 40))
    W.save('chessboard', im)
    im = Image.new('RGB', (512, 256), (60, 150, 230)); d = ImageDraw.Draw(im)
    for i, (ch, col) in enumerate(zip('TOYS', ((250, 70, 70), (255, 210, 40), (90, 200, 110), (255, 140, 40)))):
        d.rounded_rectangle((40 + i * 110, 60, 130 + i * 110, 196), 16, fill=(255, 255, 255))
        text_c(d, (85 + i * 110, 128), ch, 100, col)
    W.save('toybox', np.asarray(im, np.float32) + N3(512, 1, 92, 3, 256))
    W.save('toybox_plain', fill(n, (60, 150, 230), 3, 93))
    # playmat rug (fit 1024x768): roads, park, pond, houses
    im = Image.new('RGB', (1024, 768), (120, 196, 110)); d = ImageDraw.Draw(im)
    road = (90, 90, 96)
    for (x0, y0, x1, y1) in ((0, 170, 1024, 250), (0, 520, 1024, 600), (180, 0, 260, 768), (620, 0, 700, 768), (880, 250, 940, 520)):
        d.rectangle((x0, y0, x1, y1), fill=road)
    for x in range(0, 1024, 60):
        d.rectangle((x, 207, x + 30, 213), fill=(255, 255, 255)); d.rectangle((x, 557, x + 30, 563), fill=(255, 255, 255))
    for y in range(0, 768, 60):
        d.rectangle((217, y, 223, y + 30), fill=(255, 255, 255)); d.rectangle((657, y, 663, y + 30), fill=(255, 255, 255))
    d.ellipse((330, 300, 520, 460), fill=(80, 160, 230)); d.ellipse((350, 320, 500, 440), outline=(150, 210, 250), width=4)
    for (hx, hy, c) in ((40, 30, (230, 80, 80)), (300, 40, (250, 200, 60)), (760, 40, (120, 120, 230)), (40, 300, (250, 150, 60)),
                        (760, 300, (230, 90, 160)), (300, 640, (80, 180, 220)), (760, 640, (230, 80, 80)), (40, 640, (250, 220, 90))):
        d.rectangle((hx, hy, hx + 100, hy + 90), fill=c); d.polygon([(hx - 8, hy), (hx + 50, hy - 40), (hx + 108, hy)], fill=(160, 50, 40))
    for (tx, ty) in ((560, 330), (560, 420), (290, 450), (980, 120), (980, 680)):
        d.ellipse((tx - 22, ty - 22, tx + 22, ty + 22), fill=(40, 140, 60))
    d.rectangle((6, 6, 1017, 761), outline=(240, 240, 230), width=12)
    W.save('rug', np.asarray(im, np.float32) + N3(1024, 1.2, 94, 5, 768))
    W.save('rug_edge', fill(n, (240, 240, 230), 4, 95))
    W.save('beanbag', fill(n, (230, 70, 110), 5, 96) + N3(n, 0.5, 97, 5))
    W.save('lampshade', fill(n, (255, 240, 200), 3, 98))
    W.save('lamp_glow', fill(64, (255, 246, 220), 1, 99))
    W.save('star_yellow', fill(n, (255, 214, 60), 3, 100))
    W.save('string', fill(64, (240, 240, 240), 2, 101))
    W.save('cheese', fill(n, (255, 210, 80), 4, 102) + N3(n, 2, 103, 10))
    W.save('rope', fill(n, (200, 170, 120), 6, 104))
    # outdoor garden ground + hedge + fence
    W.save('grass', fill(n, (90, 160, 70), 10, 105) + N3(n, 0.6, 106, 14))
    W.save('hedge', fill(n, (50, 110, 50), 14, 107) + N3(n, 0.7, 108, 18))
    a = fill(n, (240, 236, 226), 3, 109)
    for i in range(0, n, 32): a[:, i:i + 4] *= 0.7
    W.save('fence', a)
    W.save('skylight', fill(8, (205, 222, 255), 0, 110))
    W.save('nodraw_ns', fill(8, (255, 0, 255), 0, 111))
    W.save('secret_sign', _secret_sign())


def _secret_sign():
    im = Image.new('RGB', (256, 128), (90, 60, 40)); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, 249, 121), outline=(220, 190, 120), width=4)
    text_c(d, (128, 46), "PAD'S", 40, (255, 220, 120)); text_c(d, (128, 92), 'HIDEOUT', 32, (255, 220, 120))
    return im


def make_sky(out):
    """fallback sky cube (the shader uses WoP's env/pf-garden512 by default, this is only q3map_lightimage)"""
    pass


# ----------------------------------------------------------------------------------------------- shader
SH = '// playroom.shader - Padman\'s Playroom (generated by wop_tools/playroom/textures.py)\n\n'


def lm(name, steps=None, extra='', editor=None):
    s = f'textures/playroom/{name}\n{{\n\tqer_editorimage textures/playroom/{editor or name}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap textures/playroom/{name}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n}}\n\n')
    return s


STEPS = {'floor_wood': 'woodsteps', 'dh_floor': 'woodsteps', 'old_boards': 'woodsteps', 'pine': 'woodsteps', 'birch': 'woodsteps',
         'walnut': 'woodsteps', 'wood_white': 'woodsteps', 'wood_mint': 'woodsteps', 'wardrobe': 'woodsteps', 'ruler': 'woodsteps',
         'duvet': 'softsteps', 'pillow': 'softsteps', 'mattress': 'softsteps', 'sheet': 'softsteps', 'beanbag': 'softsteps',
         'rug': 'carpetsteps', 'rug_edge': 'carpetsteps', 'gravel': 'sandsteps', 'cardboard': 'softsteps', 'dust': 'softsteps',
         'fabric_red': 'softsteps', 'fabric_blue': 'softsteps', 'fabric_green': 'softsteps', 'fabric_yellow': 'softsteps',
         'fabric_denim': 'softsteps', 'fabric_orange': 'softsteps', 'fabric_stripe': 'softsteps', 'fabric_check': 'softsteps', 'fabric_dots': 'softsteps', 'grass': 'softsteps', 'pages': 'softsteps',
         'chessboard': 'woodsteps', 'shoebox': 'softsteps', 'dh_trim': 'woodsteps', 'chest': 'woodsteps'}
for _c in ('red', 'blue', 'green', 'yellow', 'purple', 'orange'): STEPS['book_' + _c] = 'softsteps'
for _c in ('a', 'b', 'c', 'd', 'p'): STEPS['block_' + _c] = 'woodsteps'


def make_shader(W, out):
    S = SH
    S += '''textures/playroom/sky
{
	qer_editorimage textures/playroom/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage textures/playroom/skylight
	q3map_sun 1 0.92 0.72 420 262 32
	q3map_skylight 60 3
	skyparms env/fort-pad512 - -
}

textures/playroom/glass
{
	qer_editorimage textures/playroom/glass
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	{
		map textures/playroom/glass
		blendFunc GL_DST_COLOR GL_ONE
		rgbGen const ( 0.12 0.14 0.16 )
		tcGen environment
	}
}

textures/playroom/tankglass
{
	qer_editorimage textures/playroom/glass
	qer_trans 0.3
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{
		map textures/playroom/glass
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.06 0.09 0.10 )
		tcGen environment
	}
}

textures/playroom/water
{
	qer_editorimage textures/playroom/water
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	cull disable
	tessSize 64
	deformVertexes wave 128 sin 0 2 0 0.4
	{
		map textures/playroom/water
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.45
		rgbGen identity
		tcMod turb 0 0.03 0 0.2
		tcMod scroll 0.01 0.02
	}
	{
		map textures/playroom/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.25 0.3 0.32 )
		tcMod scale 0.5 0.5
		tcMod scroll -0.02 0.015
	}
}

textures/playroom/gravel
{
	qer_editorimage textures/playroom/gravel
	surfaceparm sandsteps
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/playroom/gravel
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
	{
		map textures/playroom/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.22 0.26 0.28 )
		tcMod scale 0.5 0.5
		tcMod turb 0 0.04 0 0.15
		tcMod scroll 0.02 0.013
	}
}

textures/playroom/lamp_glow
{
	qer_editorimage textures/playroom/lamp_glow
	surfaceparm nolightmap
	q3map_surfacelight 2500
	q3map_lightRGB 1 0.94 0.8
	q3map_lightSubdivide 64
	{
		map textures/playroom/lamp_glow
		rgbGen identity
	}
}

textures/playroom/pc_led
{
	qer_editorimage textures/playroom/pc_led
	surfaceparm nolightmap
	q3map_surfacelight 300
	{
		map textures/playroom/pc_led
		rgbGen wave sin 0.75 0.25 0 0.4
	}
}

textures/playroom/tv
{
	qer_editorimage textures/playroom/tv0
	surfaceparm nolightmap
	q3map_surfacelight 120
	q3map_lightimage textures/playroom/tv0
	{
		animmap 2 textures/playroom/tv0 textures/playroom/tv1 textures/playroom/tv2
		rgbGen identity
	}
}

textures/playroom/nodraw_ns
{
	qer_editorimage textures/playroom/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
}

textures/playroom/fabric_ns
{
	qer_editorimage textures/playroom/fabric_blue
	surfaceparm nonsolid
	surfaceparm trans
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/playroom/fabric_blue
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}

textures/playroom/string
{
	qer_editorimage textures/playroom/string
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm nolightmap
	{
		map textures/playroom/string
		rgbGen vertex
	}
}

textures/playroom/dustmotes
{
	qer_editorimage textures/playroom/skylight
	qer_trans 0.3
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm noimpact
	cull none
	deformVertexes wave 64 sin 0 3 0 0.2
	{
		map textures/playroom/caustics
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.05 0.045 0.03 )
		tcMod scale 0.25 0.25
		tcMod scroll 0.004 -0.01
	}
}

'''
    special = {'sky', 'glass', 'water', 'gravel', 'lamp_glow', 'pc_led', 'nodraw_ns', 'skylight', 'string',
               'tv0', 'tv1', 'tv2', 'caustics'}
    for nme in sorted(W.sizes):
        if nme in special: continue
        S += lm(nme, STEPS.get(nme))
    S += f'''levelshots/{MAP}B
{{
	nomipmaps
	{{
		animmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3
	}}
}}

'''
    os.makedirs(os.path.join(out, 'scripts'), exist_ok=True)
    open(os.path.join(out, 'scripts', 'playroom.shader'), 'w').write(S)


def make_arena(out):
    open(os.path.join(out, 'scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "Padman\'s Playroom"\n\ttype     "ffa lps team ft ctkd"\n}\n' % MAP)


def make_all(out):
    W = TexWriter(out)
    make_textures(W)
    make_shader(W, out)
    make_arena(out)
    return W


if __name__ == '__main__':
    import sys
    W = make_all(sys.argv[1] if len(sys.argv) > 1 else 'out')
    print(len(W.sizes), 'textures')
