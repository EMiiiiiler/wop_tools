"""The Padman's Arms (wop_padpub) - textures (woplib.texlib registry) and custom MD3s.
All art is original and procedural: a Victorian London pub (mahogany back-bar with arched red/gold etched mirrors,
brass hand pumps, encaustic floor tiles, brass chandeliers, green tapestry banquettes, red anaglypta ceiling).

Toy scale ~5u per cm: stool 375, table 380, counter 550, back counter 500, gantry cornice 1360, ceiling 1600.
Model space: z = 0 on the surface the model stands on. Wall pieces have their back at y = 0 and face -y (placed with
angle 0 against a north wall, 90 west wall, 180 south wall, 270 east wall). COLL[name] holds the weapclip collision
(boxes / cylinders / convex hulls in model space) that build_padpub.py places with each model.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from woplib import models as ML, texlib as TL
from meshlib import revolve, disc, rbox, ellipsoid, sphere, tube, prism, rot_z, arc_path

TX = None
M_ = {}
COLL = {}
C = ML.C

# ------------------------------------------------------------------------------------------------- sizes shared with the map
ZC = 1600
COUNTER_Z, COUNTER_D = 550, 300
BAY_W, BAY_D, BACK_Z, CORNICE_Z, SHELF_D = 440, 240, 500, 1360, 110
STOOL_Z = 375
TABLE_Z, TABLE_R = 380, 140
SEAT_Z, BANQ_D, BANQ_BACK = 225, 220, 520
SETTLE_BACK, SETTLE_D = 700, 220
MANTEL_Z, MANTEL_D, FIRE_W, OVERMANTEL_Z, OVERMANTEL_D = 650, 200, 760, 1380, 180
CLOCK = (200, 130, 1050)                        # width, depth, height of the longcase clock
CLOCK_TRUNK = (90, 80, 560)                     # open trunk (secret entry): width, depth, height
PIANO = (700, 280, 650)
PIANO_KEYS_Z = 360
FRUIT = (320, 300, 900)
JUKE = (380, 260, 760)
PHONE = (480, 1250)                             # phone box square size, roof top
PHONE_DOOR = 300
PICNIC_Z = 375
WIN_W = 900


# ================================================================================================= helpers
def pic(M, c, n, w, h, up=(0, 0, 1), u=(0, 1), v=(0, 1)):
    """picture quad centred at c facing n, w x h, never mirrored"""
    c, n, up = (np.asarray(x, float) for x in (c, n, up))
    right = np.cross(-n, up); right /= np.linalg.norm(right)
    up = np.cross(right, -n)
    hw, hh = right * w / 2, up * h / 2
    M.poly([c - hw + hh, c + hw + hh, c + hw - hh, c - hw - hh], n,
           [(u[0], v[0]), (u[1], v[0]), (u[1], v[1]), (u[0], v[1])])


def coll(name, boxes=(), cyls=(), hulls=()):
    COLL[name] = dict(boxes=[(tuple(a), tuple(b)) for a, b in boxes], cyls=list(cyls), hulls=[list(h) for h in hulls])


def m(key, arr, kind='lm', **o):
    M_[key] = TX.material(key, arr, kind, **o)
    return M_[key]


def bx(X, mat, mn, mx, r=3, k=1, tile=128, faces='nsewtb'):
    rbox(X.mesh(M_[mat]), mn, mx, r=r, k=k, tile=tile, faces=faces)


def cylz(X, mat, cx, cy, r, z0, z1, n=16, top=True, bot=False, u=1.0):
    revolve(X.mesh(M_[mat]), [(r, z0), (r, z1)], u_tiles=u, n=n, cx=cx, cy=cy)
    if top: disc(X.mesh(M_[mat]), r, z1, up=True, n=n, cx=cx, cy=cy)
    if bot: disc(X.mesh(M_[mat]), r, z0, up=False, n=n, cx=cx, cy=cy)


def lathe(X, mat, prof, cx=0, cy=0, n=16, u=1.0, cap=True):
    """revolve a profile running bottom -> top (outward normals); closes the top with a cap if it ends off-axis"""
    revolve(X.mesh(M_[mat]), prof, u_tiles=u, n=n, cx=cx, cy=cy)
    if cap and prof[-1][0] > 0.5: disc(X.mesh(M_[mat]), prof[-1][0], prof[-1][1], up=True, n=n, cx=cx, cy=cy)


def draw(a):
    im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    return im, ImageDraw.Draw(im)


def arr(im): return np.asarray(im.convert('RGB'), np.float32)


def fit_font(d, text, max_w, size, serif=True, min_size=10):
    while size > min_size:
        f = ML.font(size, serif=serif)
        if d.textlength(text, font=f) <= max_w: return f
        size -= 2
    return ML.font(min_size, serif=serif)


def ctext(d, cx, cy, text, f, fill, stroke=0, sfill=None):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=sfill)


R_XZ = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]])          # build in the xy plane (y = height) -> stand it up (front -y)


def upright(X, Y, t=(0, 0, 0), R2=np.eye(3)):
    """add model Y built flat (x across, y up, z = thickness toward the viewer) standing in the xz plane facing -y"""
    X.add_model(Y, R=R2 @ R_XZ, t=t)


def arch_poly(w, h, n=12, y0=0.0):
    """rectangle w wide with a semicircular top, total height h (counter-clockwise, x centred)"""
    r = w / 2
    pts = [(-r, y0), (r, y0)]
    for k in range(n + 1):
        a = math.pi * k / n
        pts.append((r * math.cos(a), y0 + h - r + r * math.sin(a)))
    return pts


# ================================================================================================= brush textures
def textures(K):
    global TX
    TX = TL.Textures(K)
    a = TX.add
    a('boards', TL.grime(TL.planks((104, 66, 40), n_planks=6, gap=(52, 32, 20), grain=12), 0.15), scale=1.0, steps='woodsteps')
    a('encaustic', encaustic(), scale=1.0)
    a('wall', saloon_wall(), scale=(1.25, 1.5625), check_tile=False)
    a('wall_snug', saloon_wall(paper=(118, 40, 44), damask=(150, 70, 60), frieze=(40, 60, 40)), scale=(1.25, 1.5625), check_tile=False)
    a('ceiling', anaglypta(), scale=1.0)
    a('mahogany', TL.planks((88, 42, 26), n_planks=4, gap=(56, 26, 16), grain=10, vertical=True), scale=0.75, steps='woodsteps')
    a('jamb', TL.solid((70, 34, 22), 3, 11, 64))
    a('facade', TL.tiles((26, 66, 46), (14, 30, 22), cols=2, rows=4, offset=0, grout_w=0.03, vary=6), scale=1.0)
    a('stallriser', TL.tiles((120, 30, 34), (40, 14, 16), cols=4, rows=2, offset=0.5, grout_w=0.03, vary=8), scale=1.0)
    a('upper', upper_storey(), 'sign', check_tile=False)
    a('stone', TL.solid((190, 184, 170), 4, 16, 128))
    a('pavement', TL.tiles((176, 172, 166), (120, 116, 112), cols=2, rows=2, offset=0, grout_w=0.02, vary=8), scale=1.5)
    a('kerb', TL.solid((160, 158, 154), 5, 15, 128))
    a('road', TL.solid((64, 66, 72), 8, 19, 256) + TL.N3(256, 1, 20, 6), scale=1.0)
    a('flags', TL.stone((150, 140, 124), cells=10), scale=1.5)
    a('gravel', TL.solid((150, 136, 116), 3, 22, 128) + TL.N3(128, 0, 23, 22), scale=0.5)
    a('brick', TL.bricks((150, 108, 70), (196, 186, 166), rows=8, cols=4, vary=20), scale=1.0)
    a('brick_red', TL.bricks((140, 60, 44), (190, 180, 166), rows=8, cols=4, vary=18), scale=1.0)
    a('across', across_street(), 'sign', check_tile=False)
    a('neighbour', neighbour_wall(), 'sign', check_tile=False)
    a('fascia', fascia_sign(), 'sign', check_tile=False)
    a('etched', etched_glass(), 'glass', rgb=(0.32, 0.30, 0.26), check_tile=False)
    a('cellar', TL.bricks((120, 70, 50), (90, 80, 70), rows=8, cols=4, vary=20), scale=1.0)
    a('cellar_floor', TL.stone((110, 104, 96), cells=12), scale=1.0)
    a('black', TL.solid((26, 24, 22), 2, 17, 64))
    a('brass', TL.metal((200, 160, 70)), scale=0.5)
    a('hearth', TL.tiles((40, 90, 70), (20, 30, 26), cols=4, rows=4, offset=0, grout_w=0.04, vary=8), scale=0.5)
    a('oche', TL.metal((200, 160, 70)), scale=0.5)
    for i, fn in enumerate((print_hunt, print_hounds, print_coach, print_river)):
        a(f'print{i}', fn(), 'sign', check_tile=False)
    a('oval_mirror', oval_mirror(), 'sign', check_tile=False)
    a('mirror_big', etched_arch(512, 768, rect=True), 'sign', check_tile=False)
    a('scores', chalk_scores(), 'sign', check_tile=False)
    a('notice', notice_board(), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=(255, 210, 120), rubber=(60, 40, 30), pad=beer_mat())
    materials()
    return TX


def encaustic(n=256):
    """Victorian floor: red diamond tiles on a cream lattice with little black squares at the crossings (tileable)"""
    x, y = TL.xy(n)
    k = 4
    u = (x + y) * k; v = (x - y) * k
    fu, fv = u % 1, v % 1
    line = (np.minimum(fu, 1 - fu) < 0.06) | (np.minimum(fv, 1 - fv) < 0.06)
    gx, gy = (x * k * 2) % 1, (y * k * 2) % 1
    cross = (np.abs(gx - 0.5) < 0.12) & (np.abs(gy - 0.5) < 0.12) & (((np.floor(x * k * 2) + np.floor(y * k * 2)) % 2) == 0)
    red = C((150, 46, 30)) + TL.N3(n, 2, 31, 14)
    out = np.where(line[..., None], C((214, 196, 156)), red)
    out = np.where(cross[..., None], C((24, 22, 22)), out)
    return out + TL.N3(n, 0, 32, 6)


def saloon_wall(w=512, h=1024, paper=(214, 192, 150), damask=(190, 150, 90), frieze=(110, 30, 26)):
    """full-height wall (0..1600): skirting, mahogany dado panels to 800, dado rail, damask wallpaper, picture rail at
    1250, a dark red frieze to the ceiling. Image top = ceiling (Q3 t runs down)."""
    a = np.zeros((h, w, 3), np.float32)
    zr = lambda z: int(h - z / 1600 * h)                    # world z -> image row
    # wallpaper with a damask diamond motif
    x, y = np.meshgrid(np.linspace(0, 1, w, endpoint=False), np.linspace(0, 1, h, endpoint=False))
    px, py = (x * 4) % 1, (y * 6) % 1
    dd = np.abs(px - 0.5) + np.abs(py - 0.5) * 0.8
    motif = ((dd < 0.32) & (dd > 0.24)) | ((np.abs(px - 0.5) < 0.04) & (np.abs(py - 0.5) < 0.18)) | \
            ((np.abs(py - 0.5) < 0.04) & (np.abs(px - 0.5) < 0.14))
    wp = np.where(motif[..., None], C(damask), C(paper)) + ML.N3(h, 1, 35, 5)[:, :1] * 0
    a[:] = wp
    # frieze above the picture rail
    a[:zr(1260)] = C(frieze) + np.where(((x[:zr(1260)] * 16) % 1 < 0.1)[..., None], 30, 0)
    a[zr(1268):zr(1252)] = C((70, 36, 22))                    # picture rail
    # dado panelling
    wood = TL.planks((86, 42, 26), n_planks=8, gap=(60, 28, 18), grain=10, vertical=True, n=512)
    wood = np.vstack([wood, wood])[:h]
    a[zr(820):] = wood[zr(820):]
    pw = w // 2
    for k in range(2):
        x0 = k * pw + 22; x1 = (k + 1) * pw - 22
        y0 = zr(760); y1 = zr(90)
        a[y0:y1, x0:x1] = wood[y0:y1, x0:x1] * 0.82
        a[y0:y0 + 6, x0:x1] = C((40, 20, 12)); a[y1 - 6:y1, x0:x1] = C((130, 76, 48))
        a[y0:y1, x0:x0 + 6] = C((40, 20, 12)); a[y0:y1, x1 - 6:x1] = C((130, 76, 48))
        a[y0 + 30:y1 - 30, x0 + 30:x1 - 30] = wood[y0 + 30:y1 - 30, x0 + 30:x1 - 30] * 0.95
    a[zr(830):zr(800)] = C((64, 30, 18)); a[zr(826):zr(822)] = C((140, 86, 52))   # dado rail
    a[zr(60):] = C((40, 20, 14))                              # skirting
    a[zr(64):zr(58)] = C((120, 70, 44))
    return a


def anaglypta(n=256):
    """embossed red ceiling paper (tileable): rosettes in a diamond lattice, shaded by an emboss"""
    x, y = TL.xy(n)
    hgt = np.zeros((n, n), np.float32)
    for (cx, cy) in ((0.25, 0.25), (0.75, 0.75), (0.25, 0.75), (0.75, 0.25)):
        dx = np.minimum(np.abs(x - cx), 1 - np.abs(x - cx)); dy = np.minimum(np.abs(y - cy), 1 - np.abs(y - cy))
        r = np.hypot(dx, dy); t = np.arctan2(dy, dx)
        hgt += np.clip(1 - r / 0.16, 0, 1) * (0.6 + 0.4 * np.cos(t * 8))
    u, v = ((x + y) * 2) % 1, ((x - y) * 2) % 1
    hgt += ((np.minimum(u, 1 - u) < 0.03) | (np.minimum(v, 1 - v) < 0.03)) * 0.6
    sh = ML.emboss(hgt * 30, 1.0)
    base = C((128, 34, 28))
    return base + sh[..., None] * 0.9 + TL.N3(n, 1, 36, 5)


def upper_storey(w=1024, h=512):
    """London stock brick upper floors with white sash windows (backdrop above the pub front)"""
    a = TL.bricks((150, 120, 84), (200, 190, 170), rows=16, cols=8, vary=20, n=512)
    a = np.hstack([a, a])[:h, :w]
    im, d = draw(a)
    for k in range(5):
        cx = 100 + k * 206
        d.rectangle((cx - 52, 120, cx + 52, 330), fill=(232, 228, 216))
        for (x0, y0, x1, y1) in ((cx - 42, 130, cx + 42, 222), (cx - 42, 232, cx + 42, 320)):
            d.rectangle((x0, y0, x1, y1), fill=(50, 60, 74))
            d.line((cx, y0, cx, y1), fill=(232, 228, 216), width=4)
            d.line((x0, (y0 + y1) // 2, x1, (y0 + y1) // 2), fill=(232, 228, 216), width=3)
        d.rectangle((cx - 60, 330, cx + 60, 342), fill=(210, 204, 190))
        d.rectangle((cx - 60, 104, cx + 60, 118), fill=(210, 204, 190))
    d.rectangle((0, 470, w, 512), fill=(36, 54, 40))           # cornice band over the fascia
    d.rectangle((0, 462, w, 470), fill=(200, 160, 70))
    return arr(im)


def across_street(w=1024, h=512):
    """the terrace across the road: brick houses with bay windows, a corner shop and a bus stop (painted backdrop)"""
    a = np.zeros((h, w, 3), np.float32) + C((150, 190, 226))
    im, d = draw(a)
    cols = [(150, 100, 70), (170, 120, 84), (140, 84, 60), (160, 110, 76), (132, 90, 66)]
    bw = w // 5
    for k in range(5):
        x0 = k * bw
        d.rectangle((x0, 60, x0 + bw, h), fill=cols[k])
        d.polygon([(x0, 60), (x0 + bw // 2, 20), (x0 + bw, 60)], fill=(70, 66, 72))
        d.rectangle((x0 + bw // 2 - 10, 0, x0 + bw // 2 + 10, 40), fill=(120, 80, 60))
        for (wx, wy) in ((x0 + 30, 100), (x0 + bw - 80, 100)):
            d.rectangle((wx, wy, wx + 50, wy + 70), fill=(240, 236, 226)); d.rectangle((wx + 5, wy + 5, wx + 45, wy + 65), fill=(60, 72, 86))
        if k == 2:
            d.rectangle((x0 + 6, 250, x0 + bw - 6, 290), fill=(30, 60, 120))
            f = ML.font(22, serif=False); ctext(d, x0 + bw / 2, 270, 'NEWSAGENT', f, (250, 250, 240))
            d.rectangle((x0 + 12, 296, x0 + bw - 12, h - 30), fill=(60, 70, 80))
        else:
            d.polygon([(x0 + 20, 380), (x0 + 40, 250), (x0 + 120, 250), (x0 + 140, 380)], fill=(236, 232, 222))
            d.rectangle((x0 + 50, 270, x0 + 110, 370), fill=(60, 72, 86))
            d.rectangle((x0 + bw - 60, 300, x0 + bw - 20, h - 30), fill=[(30, 60, 40), (120, 20, 30), (20, 40, 90), (90, 70, 20), (40, 40, 40)][k])
        d.rectangle((x0, h - 30, x0 + bw, h), fill=(130, 126, 120))
    return arr(im)


def neighbour_wall(w=1024, h=512):
    """the tall brick side wall of the next building over the beer garden, with ivy and two blind windows"""
    a = TL.bricks((140, 66, 48), (186, 176, 160), rows=16, cols=8, vary=18, n=512)
    a = np.hstack([a, a])[:h, :w]
    im, d = draw(a)
    for cx in (300, 724):
        d.rectangle((cx - 60, 80, cx + 60, 240), fill=(170, 80, 60)); d.rectangle((cx - 66, 240, cx + 66, 252), fill=(210, 204, 190))
    rng = np.random.default_rng(5)
    for k in range(900):
        x = rng.uniform(0, w); y = h - abs(rng.normal(0, 150))
        r = rng.uniform(4, 10); g = rng.uniform(70, 130)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(30, int(g), 40))
    return arr(im)


def fascia_sign(w=1024, h=128):
    """the pub's name board: gilt serif letters on deep green with a gold line"""
    a = np.zeros((h, w, 3), np.float32) + C((22, 52, 36))
    im, d = draw(a)
    d.rectangle((6, 6, w - 6, h - 6), outline=(210, 170, 80), width=4)
    d.rectangle((16, 16, w - 16, h - 16), outline=(120, 96, 50), width=2)
    f = fit_font(d, "THE PADMAN'S ARMS", w - 120, 84)
    ctext(d, w / 2 + 2, h / 2 + 3, "THE PADMAN'S ARMS", f, (20, 16, 10))
    ctext(d, w / 2, h / 2, "THE PADMAN'S ARMS", f, (236, 196, 96))
    for cx in (40, w - 40):
        d.ellipse((cx - 12, h / 2 - 12, cx + 12, h / 2 + 12), fill=(210, 170, 80))
    return arr(im)


def etched_glass(w=256, h=256):
    """frosted 'Saloon Bar' etched panel (shows through the additive glass shader as a pale pattern)"""
    a = np.zeros((h, w, 3), np.float32) + 60
    im, d = draw(a)
    d.rectangle((8, 8, w - 8, h - 8), outline=(230, 230, 230), width=3)
    for k in range(6):
        d.arc((w / 2 - 20 - k * 16, h / 2 - 20 - k * 16, w / 2 + 20 + k * 16, h / 2 + 20 + k * 16), 0, 360, fill=(200, 200, 200), width=2)
    f = ML.font(26, serif=True)
    ctext(d, w / 2, h / 2, 'SALOON', f, (250, 250, 250))
    for (x, y) in ((30, 30), (w - 30, 30), (30, h - 30), (w - 30, h - 30)):
        d.ellipse((x - 10, y - 10, x + 10, y + 10), outline=(240, 240, 240), width=2)
    return arr(im)


def _vase_foliage(d, cx, top, bot, half_w, gold=(222, 176, 70), dim=(150, 110, 40), seed=1):
    """gilded vase with symmetric curling stems and leaves (the back-bar mirror etching)"""
    rng = np.random.default_rng(seed)
    H = bot - top
    vy = bot - H * 0.18
    d.polygon([(cx - half_w * 0.22, vy), (cx + half_w * 0.22, vy), (cx + half_w * 0.12, bot - H * 0.04),
               (cx - half_w * 0.12, bot - H * 0.04)], fill=gold)
    d.ellipse((cx - half_w * 0.28, vy - H * 0.05, cx + half_w * 0.28, vy + H * 0.03), fill=gold)
    d.rectangle((cx - half_w * 0.2, bot - H * 0.04, cx + half_w * 0.2, bot - H * 0.01), fill=gold)
    for s in (-1, 1):
        for k in range(7):
            t = k / 6
            y0 = vy - H * 0.06
            y1 = top + H * (0.05 + 0.6 * t)
            x1 = cx + s * half_w * (0.15 + 0.7 * math.sin(t * math.pi * 0.9))
            pts = [(cx + s * half_w * 0.05 * (1 - u) + (x1 - cx) * u ** 1.5, y0 + (y1 - y0) * u) for u in np.linspace(0, 1, 12)]
            d.line(pts, fill=gold, width=3)
            for j in range(3, 12, 3):
                px, py = pts[j]
                r = 6 + rng.uniform(0, 5)
                d.ellipse((px - r * 1.6, py - r, px + r * 1.6, py + r), fill=gold if j % 2 else dim)
            ex, ey = pts[-1]
            for q in range(5):
                ang = q * 2 * math.pi / 5
                d.ellipse((ex + 9 * math.cos(ang) - 5, ey + 9 * math.sin(ang) - 5, ex + 9 * math.cos(ang) + 5, ey + 9 * math.sin(ang) + 5), fill=gold)
    d.line((cx, vy - H * 0.06, cx, top + H * 0.02), fill=gold, width=4)
    for q in range(8):
        ang = q * 2 * math.pi / 8
        d.ellipse((cx + 14 * math.cos(ang) - 7, top + H * 0.04 + 14 * math.sin(ang) - 7,
                   cx + 14 * math.cos(ang) + 7, top + H * 0.04 + 14 * math.sin(ang) + 7), fill=gold)


def etched_arch(w=256, h=512, rect=False, seed=1):
    """the back-bar mirror: deep red glass etched with a gilded vase of foliage and stars, an arched gold border, carved
    mahogany spandrels outside the arch (rect=True: a plain rectangle for the overmantel)"""
    a = np.zeros((h, w, 3), np.float32)
    yy = np.linspace(0, 1, h)[:, None, None]
    a[:] = C((110, 20, 24)) * (0.75 + 0.35 * (1 - yy)) + ML.N3(h, 2, 37 + seed, 6)[:, :w] if h == w else C((110, 20, 24)) * (0.75 + 0.35 * (1 - yy))
    im, d = draw(a)
    rng = np.random.default_rng(seed)
    for k in range(70):
        x, y = rng.uniform(10, w - 10), rng.uniform(10, h - 10)
        r = rng.uniform(1.5, 3.5); d.ellipse((x - r, y - r, x + r, y + r), fill=(236, 200, 110))
    _vase_foliage(d, w / 2, h * 0.12, h * 0.94, w * 0.46, seed=seed)
    if not rect:
        r = w / 2 - 10
        d.arc((10, 10, w - 10, 10 + 2 * r), 180, 360, fill=(230, 186, 80), width=6)
        d.line((10, 10 + r, 10, h - 8), fill=(230, 186, 80), width=6); d.line((w - 10, 10 + r, w - 10, h - 8), fill=(230, 186, 80), width=6)
        # spandrels: mahogany outside the arch
        m_ = Image.new('L', (w, h), 0); md = ImageDraw.Draw(m_)
        md.rectangle((0, 0, w, h), fill=255)
        md.pieslice((7, 7, w - 7, 7 + 2 * (w / 2 - 7)), 180, 360, fill=0)
        md.rectangle((7, 7 + (w / 2 - 7), w - 7, h), fill=0)
        wood = Image.fromarray(np.uint8(TL.planks((86, 40, 24), n_planks=3, gap=(50, 24, 14), grain=10, n=max(w, h))[:h, :w]))
        im.paste(wood, (0, 0), m_)
        d = ImageDraw.Draw(im)
        for cx in (w * 0.12, w * 0.88):
            d.ellipse((cx - 10, 26, cx + 10, 46), fill=(200, 160, 70))
    else:
        d.rectangle((6, 6, w - 6, h - 6), outline=(230, 186, 80), width=6)
    return arr(im)


def _print(draw_fn, w=256, h=192):
    a = np.zeros((h, w, 3), np.float32) + C((226, 214, 180))
    im, d = draw(a)
    d.rectangle((0, 0, w - 1, h - 1), outline=(30, 26, 20), width=14)
    d.rectangle((14, 14, w - 15, h - 15), outline=(240, 232, 210), width=10)
    draw_fn(d, 24, 24, w - 24, h - 24)
    return arr(im)


def _horse(d, x, y, s, col=(90, 50, 30), rider=(170, 30, 30)):
    d.ellipse((x - 26 * s, y - 10 * s, x + 26 * s, y + 10 * s), fill=col)
    d.polygon([(x + 20 * s, y - 6 * s), (x + 38 * s, y - 26 * s), (x + 46 * s, y - 22 * s), (x + 28 * s, y + 2 * s)], fill=col)
    for (lx, dx) in ((-20, -10), (-12, 6), (14, 12), (20, -6)):
        d.line((x + lx * s, y + 6 * s, x + (lx + dx) * s, y + 30 * s), fill=col, width=max(2, int(4 * s)))
    d.line((x - 26 * s, y - 4 * s, x - 40 * s, y + 10 * s), fill=col, width=max(2, int(3 * s)))
    if rider:
        d.rectangle((x - 6 * s, y - 34 * s, x + 6 * s, y - 10 * s), fill=rider)
        d.ellipse((x - 5 * s, y - 44 * s, x + 5 * s, y - 34 * s), fill=(230, 200, 170))
        d.rectangle((x - 6 * s, y - 48 * s, x + 6 * s, y - 42 * s), fill=(20, 20, 20))


def print_hunt():
    def f(d, x0, y0, x1, y1):
        d.rectangle((x0, y0, x1, (y0 + y1) / 2 + 10), fill=(196, 210, 214))
        d.rectangle((x0, (y0 + y1) / 2 + 10, x1, y1), fill=(120, 140, 80))
        d.polygon([(x0, y0 + 70), (x0 + 60, y0 + 50), (x0 + 130, y0 + 66), (x1, y0 + 56), (x1, y0 + 90), (x0, y0 + 90)], fill=(100, 124, 80))
        _horse(d, (x0 + x1) / 2, y1 - 44, 1.1)
        d.ellipse((x1 - 60, y0 + 40, x1 - 20, y0 + 80), fill=(70, 100, 60))
    return _print(f)


def print_hounds():
    def f(d, x0, y0, x1, y1):
        d.rectangle((x0, y0, x1, y1), fill=(200, 210, 196))
        d.rectangle((x0, y1 - 50, x1, y1), fill=(110, 130, 70))
        for k in range(6):
            x = x0 + 24 + k * 34; y = y1 - 34 + (k % 2) * 6
            d.ellipse((x - 12, y - 6, x + 12, y + 6), fill=(220, 210, 190)); d.ellipse((x + 8, y - 12, x + 18, y - 2), fill=(120, 80, 40))
            d.line((x - 8, y + 4, x - 12, y + 16), fill=(120, 80, 40), width=2); d.line((x + 8, y + 4, x + 10, y + 16), fill=(120, 80, 40), width=2)
        _horse(d, x1 - 50, y1 - 60, 0.8, rider=(30, 30, 30))
    return _print(f)


def print_coach():
    def f(d, x0, y0, x1, y1):
        d.rectangle((x0, y0, x1, y1), fill=(220, 200, 160))
        d.rectangle((x0, y1 - 40, x1, y1), fill=(150, 130, 96))
        d.rectangle((x0 + 90, y1 - 90, x0 + 170, y1 - 46), fill=(140, 30, 30)); d.rectangle((x0 + 100, y1 - 84, x0 + 125, y1 - 64), fill=(240, 220, 160))
        for wx in (x0 + 105, x0 + 158):
            d.ellipse((wx - 14, y1 - 58, wx + 14, y1 - 30), outline=(40, 30, 20), width=3)
        _horse(d, x0 + 50, y1 - 56, 0.8, rider=None)
    return _print(f)


def print_river():
    def f(d, x0, y0, x1, y1):
        d.rectangle((x0, y0, x1, y1), fill=(186, 206, 220))
        d.rectangle((x0, (y0 + y1) / 2 + 20, x1, y1), fill=(90, 120, 140))
        d.polygon([(x0, (y0 + y1) / 2 + 20), (x0 + 40, y0 + 60), (x0 + 90, (y0 + y1) / 2 + 20)], fill=(90, 110, 80))
        d.rectangle((x0 + 120, y0 + 40, x0 + 136, (y0 + y1) / 2 + 20), fill=(140, 120, 100))
        d.polygon([(x0 + 112, y0 + 40), (x0 + 128, y0 + 20), (x0 + 144, y0 + 40)], fill=(80, 60, 50))
        d.polygon([(x1 - 80, (y0 + y1) / 2 + 40), (x1 - 30, (y0 + y1) / 2 + 40), (x1 - 40, (y0 + y1) / 2 + 52), (x1 - 70, (y0 + y1) / 2 + 52)], fill=(80, 50, 30))
        d.line((x1 - 55, (y0 + y1) / 2 + 40, x1 - 55, (y0 + y1) / 2 - 10), fill=(60, 40, 30), width=2)
        d.polygon([(x1 - 55, (y0 + y1) / 2 - 10), (x1 - 30, (y0 + y1) / 2 + 30), (x1 - 55, (y0 + y1) / 2 + 30)], fill=(240, 236, 220))
    return _print(f)


def oval_mirror(w=256, h=384):
    """mahogany panel with an oval etched mirror (gold foliage) like the photo's left wall"""
    a = TL.planks((80, 38, 22), n_planks=3, gap=(50, 24, 14), grain=10, n=384)[:h, :w]
    im, d = draw(a)
    d.rectangle((4, 4, w - 4, h - 4), outline=(40, 20, 12), width=8)
    d.ellipse((24, 24, w - 24, h - 24), fill=(200, 160, 70))
    d.ellipse((32, 32, w - 32, h - 32), fill=(60, 52, 50))
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).ellipse((32, 32, w - 32, h - 32), fill=255)
    lay = Image.fromarray(np.uint8(np.zeros((h, w, 3)) + (60, 52, 50))); ld = ImageDraw.Draw(lay)
    _vase_foliage(ld, w / 2, h * 0.18, h * 0.86, w * 0.36, gold=(220, 186, 110), dim=(160, 130, 80), seed=3)
    im.paste(lay, (0, 0), m)
    return arr(im)


def chalk_scores(w=256, h=256):
    a = np.zeros((h, w, 3), np.float32) + C((30, 34, 32)) + TL.N3(256, 1, 41, 6)[:h, :w]
    im, d = draw(a)
    d.rectangle((0, 0, w - 1, h - 1), outline=(90, 56, 30), width=12)
    f = ML.font(22, serif=False)
    d.line((w / 2, 40, w / 2, h - 20), fill=(220, 220, 210), width=2)
    ctext(d, w / 4, 28, 'PAD', f, (230, 230, 220)); ctext(d, 3 * w / 4, 28, 'DUCKS', f, (230, 230, 220))
    rng = np.random.default_rng(4)
    for k in range(7):
        s1 = 501 - int(rng.integers(20, 90)) * (k + 1) // 2; s2 = 501 - int(rng.integers(20, 90)) * (k + 1) // 2
        ctext(d, w / 4, 60 + k * 26, str(max(s1, 0)), f, (220, 220, 210)); ctext(d, 3 * w / 4, 60 + k * 26, str(max(s2, 0)), f, (220, 220, 210))
    return arr(im)


def notice_board(w=256, h=256):
    a = np.zeros((h, w, 3), np.float32) + C((176, 130, 86)) + TL.N3(256, 0, 42, 12)[:h, :w]
    im, d = draw(a)
    d.rectangle((0, 0, w - 1, h - 1), outline=(70, 40, 20), width=12)
    notes = [((30, 30, 120, 120), (250, 240, 180), 'QUIZ\nTUES'), ((140, 24, 230, 110), (250, 250, 250), 'DARTS\nLEAGUE'),
             ((40, 140, 140, 230), (200, 230, 250), 'LIVE\nMUSIC'), ((150, 130, 226, 226), (250, 200, 200), 'PAD\nPOKER')]
    for (bb, col, t) in notes:
        d.rectangle(bb, fill=col); f = ML.font(18, serif=False)
        ctext(d, (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, t, f, (40, 40, 40))
        d.ellipse(((bb[0] + bb[2]) / 2 - 4, bb[1] + 4, (bb[0] + bb[2]) / 2 + 4, bb[1] + 12), fill=(200, 30, 30))
    return arr(im)


def beer_mat(n=256):
    """the jump pads are giant beer mats: round cream card with a red ring and the house ale"""
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    a = np.zeros((n, n, 3), np.float32) + C((236, 226, 196)) + TL.N3(n, 0, 43, 6)
    a = np.where(((r > 0.40) & (r < 0.46))[..., None], C((170, 30, 30)), a)
    a = np.where(((r > 0.36) & (r < 0.38))[..., None], C((200, 160, 70)), a)
    a = np.where((r > 0.48)[..., None], C((60, 40, 30)), a)
    im, d = draw(a)
    f = ML.font(40, serif=True); ctext(d, n / 2, n / 2 - 30, "PADMAN'S", f, (130, 24, 24))
    f = ML.font(52, serif=True); ctext(d, n / 2, n / 2 + 24, 'ALE', f, (30, 30, 30))
    for k in range(5):
        ang = math.pi * (0.2 + 0.15 * k)
        d.polygon([(n / 2 + 70 * math.cos(ang) * 0.9, n / 2 + 80 + 0), (n / 2 + 4, n / 2 + 70), (n / 2 - 4, n / 2 + 70)], fill=None)
    return arr(im)


# ================================================================================================= model textures
def panel_tex(n=256, col=(88, 42, 26), cols=1, rows=1):
    """raised mahogany panel(s): stiles and rails with an inset bevelled panel"""
    a = TL.planks(col, n_planks=4, gap=tuple(int(c * 0.66) for c in col), grain=10, vertical=True, n=n)
    pw, ph = n // cols, n // rows
    for i in range(cols):
        for j in range(rows):
            x0, y0, x1, y1 = i * pw + 22, j * ph + 22, (i + 1) * pw - 22, (j + 1) * ph - 22
            a[y0:y1, x0:x1] *= 0.84
            a[y0:y0 + 5, x0:x1] = C(col) * 0.45; a[y1 - 5:y1, x0:x1] = C(col) * 1.45
            a[y0:y1, x0:x0 + 5] = C(col) * 0.45; a[y0:y1, x1 - 5:x1] = C(col) * 1.45
            a[y0 + 18:y1 - 18, x0 + 18:x1 - 18] /= 0.84
            a[y0 + 18:y0 + 22, x0 + 18:x1 - 18] = C(col) * 1.35; a[y1 - 22:y1 - 18, x0 + 18:x1 - 18] = C(col) * 0.5
    return a


def label_bottle(body, label, text, n=128, foil=None, seed=0):
    a = np.zeros((n, n, 3), np.float32) + C(body) + TL.N3(n, 1, 50 + seed, 6)
    im, d = draw(a)
    d.rectangle((0, int(n * 0.45), n, int(n * 0.78)), fill=label)
    f = fit_font(d, text, n * 0.42, 18, serif=True)
    for cx in (n * 0.25, n * 0.75):
        ctext(d, cx, n * 0.615, text, f, (40, 30, 20) if sum(label) > 380 else (240, 230, 200))
    if foil: d.rectangle((0, 0, n, int(n * 0.16)), fill=foil)
    return arr(im)


def pump_clip(text, bg, fg, w=64, h=128):
    a = np.zeros((h, w, 3), np.float32) + C(bg)
    im, d = draw(a)
    d.ellipse((4, 10, w - 4, h - 10), outline=fg, width=3)
    words = text.split()
    for k, wd in enumerate(words):
        f = fit_font(d, wd, w - 14, 18, serif=True)
        ctext(d, w / 2, h / 2 + (k - (len(words) - 1) / 2) * 20, wd, f, fg)
    return arr(im)


def clock_face(n=256, roman=True):
    x, y = TL.xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    a = np.zeros((n, n, 3), np.float32) + C((240, 232, 210))
    a = np.where((r > 0.47)[..., None], C((200, 160, 70)), a)
    im, d = draw(a)
    nums = ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'] if roman else [str(k or 12) for k in range(12)]
    f = ML.font(20, serif=True)
    for k in range(12):
        ang = math.radians(k * 30 - 90)
        ctext(d, n / 2 + 0.37 * n * math.cos(ang), n / 2 + 0.37 * n * math.sin(ang), nums[k], f, (30, 26, 20))
        d.line((n / 2 + 0.45 * n * math.cos(ang), n / 2 + 0.45 * n * math.sin(ang),
                n / 2 + 0.42 * n * math.cos(ang), n / 2 + 0.42 * n * math.sin(ang)), fill=(30, 26, 20), width=3)
    for (ang, L, wd) in ((math.radians(10 * 30 - 90 + 15), 0.22, 7), (math.radians(2 * 6 * 6 - 90), 0.34, 4)):
        d.line((n / 2, n / 2, n / 2 + L * n * math.cos(ang), n / 2 + L * n * math.sin(ang)), fill=(20, 20, 20), width=wd)
    d.ellipse((n / 2 - 6, n / 2 - 6, n / 2 + 6, n / 2 + 6), fill=(20, 20, 20))
    return arr(im)


def keys_tex(w=512, h=64):
    """piano keyboard seen from above: 52 white keys with the black keys in the 2-3 pattern"""
    a = np.zeros((h, w, 3), np.float32) + C((240, 236, 222))
    im, d = draw(a)
    n = 52; kw = w / n
    for k in range(n + 1): d.line((k * kw, 0, k * kw, h), fill=(120, 116, 110), width=1)
    for k in range(n - 1):
        if k % 7 in (0, 1, 3, 4, 5):
            d.rectangle((k * kw + kw * 0.65, 0, k * kw + kw * 1.35, h * 0.6), fill=(20, 18, 18))
    return arr(im)


def fruit_glass(w=256, h=512):
    """fruit machine front: lit header, three reels, nudge/hold buttons, win table (original 'PAD FRUITS')"""
    a = np.zeros((h, w, 3), np.float32) + C((20, 20, 40))
    im, d = draw(a)
    d.rectangle((0, 0, w, 110), fill=(200, 30, 60))
    f = fit_font(d, 'PAD FRUITS', w - 30, 44, serif=False); ctext(d, w / 2, 40, 'PAD FRUITS', f, (255, 236, 80), 2, (90, 0, 20))
    f2 = ML.font(16, serif=False); ctext(d, w / 2, 88, '£100 JACKPOT', f2, (255, 255, 255))
    for k in range(3):
        x0 = 24 + k * 72
        d.rectangle((x0, 140, x0 + 64, 270), fill=(250, 250, 244), outline=(200, 170, 60), width=4)
        sym = [((220, 30, 30), 'o'), ((250, 210, 30), 'b'), ((60, 160, 40), 'm')][(k + 1) % 3]
        d.ellipse((x0 + 14, 180, x0 + 50, 216), fill=sym[0])
        d.rectangle((x0 + 30, 172, x0 + 34, 182), fill=(40, 120, 30))
    d.rectangle((14, 286, w - 14, 300), fill=(250, 210, 30))
    for k, (t, c) in enumerate((('7 7 7   £100', (255, 80, 80)), ('BAR BAR   £25', (255, 220, 80)),
                                ('PAD PAD   £10', (120, 220, 255)), ('CHERRY   £2', (255, 140, 200)))):
        ctext(d, w / 2, 324 + k * 26, t, f2, c)
    for k in range(3):
        d.rectangle((24 + k * 72, 440, 88 + k * 72, 470), fill=(250, 200, 30), outline=(255, 255, 255), width=2)
        ctext(d, 56 + k * 72, 455, 'HOLD', ML.font(14, serif=False), (40, 20, 0))
    return arr(im)


def juke_tex(w=256, h=256):
    """jukebox front: title strips behind a glass window, chrome grille below"""
    a = np.zeros((h, w, 3), np.float32) + C((40, 22, 16))
    im, d = draw(a)
    d.rectangle((20, 16, w - 20, 120), fill=(240, 230, 200))
    for k in range(8):
        d.line((24, 24 + k * 12, w - 24, 24 + k * 12), fill=(180, 60, 50), width=1)
        d.line((w / 2, 16, w / 2, 120), fill=(120, 110, 90), width=2)
    for k in range(9):
        d.line((30 + k * 22, 140, 30 + k * 22, h - 16), fill=(200, 196, 190), width=5)
    d.rectangle((20, 132, w - 20, 140), fill=(200, 160, 70))
    return arr(im)


def dartboard(n=256):
    x, y = TL.xy(n)
    dx, dy = x - 0.5, y - 0.5
    r = np.hypot(dx, dy) * 2; t = (np.degrees(np.arctan2(dy, dx)) + 9) % 360
    seg = (t // 18).astype(int) % 2
    a = np.where(seg[..., None] == 0, C((20, 20, 18)), C((236, 220, 180)))
    ring_col = np.where(seg[..., None] == 0, C((190, 30, 30)), C((30, 130, 60)))
    a = np.where(((r > 0.60) & (r < 0.65) | (r > 0.92) & (r < 0.98))[..., None], ring_col, a)
    a = np.where((r < 0.08)[..., None], C((30, 130, 60)), a)
    a = np.where((r < 0.035)[..., None], C((190, 30, 30)), a)
    a = np.where((r > 0.98)[..., None], C((20, 20, 18)), a)
    im, d = draw(a)
    f = ML.font(13, serif=False)
    nums = [6, 13, 4, 18, 1, 20, 5, 12, 9, 14, 11, 8, 16, 7, 19, 3, 17, 2, 15, 10]
    for k, v in enumerate(nums):
        ang = math.radians(-k * 18)
        ctext(d, n / 2 + 0.49 * n * 0.99 * math.cos(ang) * 0.99, n / 2 + 0.49 * n * math.sin(ang) * 0.99, '', f, (240, 240, 240))
    return arr(im)


def sign_board(w=256, h=320):
    """the hanging pub sign: a shield with a duck and three crowns over a scroll"""
    a = np.zeros((h, w, 3), np.float32) + C((22, 52, 36))
    im, d = draw(a)
    d.rectangle((6, 6, w - 6, h - 6), outline=(210, 170, 80), width=6)
    d.polygon([(60, 70), (196, 70), (196, 170), (128, 236), (60, 170)], fill=(170, 30, 30), outline=(230, 190, 90))
    d.ellipse((96, 120, 160, 170), fill=(250, 220, 60)); d.ellipse((140, 104, 170, 134), fill=(250, 220, 60))
    d.polygon([(168, 118), (186, 122), (168, 128)], fill=(240, 130, 30)); d.ellipse((152, 112, 158, 118), fill=(20, 20, 20))
    for cx in (84, 128, 172):
        d.polygon([(cx - 12, 96), (cx - 12, 84), (cx - 6, 90), (cx, 80), (cx + 6, 90), (cx + 12, 84), (cx + 12, 96)], fill=(236, 196, 96))
    f = fit_font(d, "THE PADMAN'S", w - 30, 26); ctext(d, w / 2, 30, "THE PADMAN'S", f, (236, 196, 96))
    d.rectangle((26, 254, w - 26, 296), fill=(236, 220, 180)); f = fit_font(d, 'ARMS', w - 70, 34); ctext(d, w / 2, 275, 'ARMS', f, (130, 24, 24))
    return arr(im)


def aboard(w=256, h=384):
    a = np.zeros((h, w, 3), np.float32) + C((30, 34, 32)) + TL.N3(384, 1, 44, 6)[:h, :w]
    im, d = draw(a)
    lines = [('TODAY', 34, (250, 220, 120)), ('', 10, None), ('Sunday Roast', 22, (240, 240, 230)), ('Fish & Chips', 22, (240, 240, 230)),
             ('Pie & Mash', 22, (240, 240, 230)), ('', 10, None), ('QUIZ NIGHT', 26, (150, 220, 255)), ('Tues 8pm', 20, (240, 240, 230)),
             ('', 10, None), ('ALL WELCOME', 22, (255, 160, 180))]
    y = 30
    for t, s, c in lines:
        if t: ctext(d, w / 2, y, t, ML.font(s, serif=False), c)
        y += s + 12
    return arr(im)


def snacks_board(w=256, h=320):
    a = np.zeros((h, w, 3), np.float32) + C((24, 26, 24)) + TL.N3(320, 1, 45, 5)[:h, :w]
    im, d = draw(a)
    d.rectangle((0, 0, w - 1, h - 1), outline=(120, 76, 40), width=10)
    ctext(d, w / 2, 40, 'Snacks', ML.font(40, serif=True), (250, 250, 240))
    for k, t in enumerate(('Pork Scratchings', 'Salted Peanuts', 'Scotch Egg', 'Crisps', 'Pickled Onions', 'Sausage Roll')):
        d.text((24, 84 + k * 36), '~ ' + t, font=ML.font(20, serif=False), fill=(240, 236, 220))
    return arr(im)


def coffee_board(w=192, h=256):
    a = np.zeros((h, w, 3), np.float32) + C((24, 26, 24))
    im, d = draw(a)
    ctext(d, w / 2, 30, 'COFFEE', ML.font(30, serif=False), (250, 250, 240))
    for k, t in enumerate(('LATTE', 'CAPPUCCINO', 'AMERICANO', 'ESPRESSO', 'FLAT WHITE')):
        ctext(d, w / 2, 76 + k * 34, t, ML.font(18, serif=False), (240, 236, 220))
    return arr(im)


def phone_sign(w=256, h=48):
    a = np.zeros((h, w, 3), np.float32) + C((24, 24, 24))
    im, d = draw(a)
    ctext(d, w / 2, h / 2, 'TELEPHONE', fit_font(d, 'TELEPHONE', w - 20, 36, serif=False), (250, 250, 240))
    return arr(im)


def tapestry(n=256, base=(40, 80, 50)):
    """the banquette upholstery: green with gold stripes and small cream flowers (photo)"""
    a = TL.fabric(base, weave=96, n=n)
    x, y = TL.xy(n)
    st = ((x * 8) % 1 < 0.12)
    a = np.where(st[..., None], C((190, 160, 70)), a)
    fl = (np.hypot((x * 8) % 1 - 0.56, (y * 8) % 1 - 0.5) < 0.16) & (((np.floor(y * 8) + np.floor(x * 8)) % 2) == 0)
    a = np.where(fl[..., None], C((214, 190, 140)), a)
    return a


def parasol_tex(n=256):
    x, y = TL.xy(n)
    return np.where(((x * 8) % 1 < 0.5)[..., None], C((30, 90, 50)), C((236, 228, 206))) + TL.N3(n, 1, 46, 5)


def materials():
    lms = 'lms'
    m('mahog', TL.planks((96, 46, 28), n_planks=4, gap=(60, 28, 18), grain=10, vertical=True), lms, v=0.12, shade=30)
    m('mahog_dark', TL.planks((64, 30, 18), n_planks=4, gap=(40, 18, 10), grain=10, vertical=True), lms, v=0.1, shade=30)
    m('panel', panel_tex(), lms, v=0.1, shade=30)
    m('panel2', panel_tex(cols=2), lms, v=0.1, shade=30)
    m('panel_door', panel_tex(rows=2), lms, v=0.1, shade=30)
    m('bartop', TL.planks((80, 36, 20), n_planks=3, gap=(56, 26, 14), grain=8), lms, v=0.25, shade=40)
    m('marble', TL.solid((226, 220, 210), 3, 47, 128) + TL.N3(128, 1, 48, 14), lms, v=0.15, shade=30)
    m('brass', TL.metal((206, 164, 72)), lms, v=0.35, shade=60)
    m('gold', TL.solid((214, 172, 80), 2, 49, 64), lms, v=0.3, shade=50)
    m('chrome', TL.metal((200, 204, 210)), lms, v=0.4, shade=60)
    m('iron', TL.solid((30, 30, 32), 2, 51, 64), lms, v=0.08, shade=50)
    m('arch', etched_arch(), 'lms', v=0.12, shade=20)
    m('arch2', etched_arch(seed=2), 'lms', v=0.12, shade=20)
    m('mirror', TL.solid((70, 66, 64), 2, 52, 64), lms, v=0.5, shade=20)
    m('glass', TL.solid((180, 200, 200), 2, 53, 64), 'glass', c='0.09 0.10 0.10')
    m('glow_warm', TL.solid((255, 236, 190), 1, 54, 64), 'glow')
    m('glow_shade', alabaster(), 'glow')
    m('fridge_glow', fridge_back(), 'glow')
    for k, (body, lab, txt, foil) in enumerate((((30, 70, 40), (236, 226, 196), 'CLARET', (120, 20, 30)),
                                               ((24, 50, 30), (240, 236, 220), 'CHAMPERS', (220, 180, 70)),
                                               ((150, 80, 20), (30, 30, 30), 'PADDY', None),
                                               ((150, 190, 200), (250, 250, 250), 'PAD GIN', (40, 80, 160)),
                                               ((210, 220, 226), (200, 30, 30), 'VODKA', (220, 220, 230)),
                                               ((110, 50, 16), (236, 200, 100), 'BITTER', None),
                                               ((30, 110, 50), (250, 250, 240), 'LAGER', (220, 220, 220)),
                                               ((60, 20, 10), (240, 180, 40), 'RUM', None),
                                               ((120, 30, 60), (250, 230, 200), 'PORT', (60, 10, 20)))):
        m(f'bottle{k}', label_bottle(body, lab, txt, foil=foil, seed=k), lms, v=0.3, shade=60, lathe=True)
    m('beer', TL.solid((196, 120, 30), 2, 55, 64), lms, v=0.25, shade=60)
    m('stout', TL.solid((24, 14, 10), 2, 56, 64), lms, v=0.2, shade=60)
    m('foam', TL.solid((246, 236, 210), 2, 57, 64), shade=60)
    for k, (t, bg, fg) in enumerate((("PADMAN'S BEST", (150, 30, 30), (250, 220, 120)), ('OLD DUCKY', (30, 50, 100), (250, 250, 250)),
                                     ('GOLD PAD', (230, 190, 60), (60, 30, 10)), ('ROCKET STOUT', (20, 20, 20), (230, 190, 90)))):
        m(f'clip{k}', pump_clip(t, bg, fg), shade=40)
    m('ceramic', TL.solid((20, 18, 18), 2, 58, 64), lms, v=0.3, shade=60)
    m('tapestry', tapestry(), shade=40)
    m('tapestry_red', tapestry(base=(120, 30, 34)), shade=40)
    m('velvet_red', TL.fabric((150, 30, 34), weave=64), shade=40)
    m('velvet_green', TL.fabric((40, 90, 56), weave=64), shade=40)
    m('tiles_green', TL.tiles((40, 100, 74), (20, 40, 30), cols=2, rows=8, offset=0, grout_w=0.04, vary=10), lms, v=0.2, shade=30)
    m('coal', TL.solid((30, 26, 24), 3, 59, 64) + TL.N3(64, 0, 60, 20), shade=60)
    m('ember', ember(), 'glow', wave='wave noise 0.8 0.25 0 3')
    m('flame', flame(), 'add', wave='wave noise 0.7 0.3 0 5', deform='autosprite2')
    m('clockface', clock_face(), shade=30)
    m('black_lacquer', TL.solid((16, 14, 14), 2, 61, 64), lms, v=0.35, shade=40)
    m('keys', keys_tex(), shade=30)
    m('fruit', fruit_glass(), 'glow')
    m('fruit_body', TL.solid((30, 30, 60), 2, 62, 64), lms, v=0.15, shade=30)
    m('juke', juke_tex(), shade=30)
    m('juke_lights', juke_lights(), 'glow', wave='wave sin 0.75 0.25 0 0.4')
    m('dart', dartboard(), shade=30)
    m('cork', TL.solid((150, 110, 70), 3, 63, 64) + TL.N3(64, 0, 64, 10), shade=30)
    m('sign', sign_board(), shade=30)
    m('aboard', aboard(), shade=30)
    m('snacks', snacks_board(), shade=30)
    m('coffee', coffee_board(), shade=30)
    m('phone_red', TL.solid((196, 24, 24), 2, 65, 64), lms, v=0.15, shade=40)
    m('phone_sign', phone_sign(), 'glow')
    m('pillar_red', TL.solid((200, 26, 26), 2, 66, 64), lms, v=0.15, shade=50)
    m('oak', TL.planks((150, 104, 60), n_planks=6, gap=(100, 66, 36), grain=10, vertical=True), shade=40)
    m('weathered', TL.planks((150, 136, 116), n_planks=4, gap=(100, 90, 76), grain=8), shade=30)
    m('parasol', parasol_tex(), two=True, shade=30)
    m('leaf', TL.solid((50, 110, 40), 3, 67, 64) + TL.N3(64, 0, 68, 18), shade=60)
    m('petal_pink', TL.solid((240, 110, 160), 3, 69, 64), shade=60)
    m('petal_red', TL.solid((220, 40, 40), 3, 70, 64), shade=60)
    m('petal_white', TL.solid((246, 244, 236), 3, 71, 64), shade=60)
    m('petal_yellow', TL.solid((250, 210, 50), 3, 72, 64), shade=60)
    m('soil', TL.solid((60, 40, 26), 3, 73, 64), shade=60)
    m('keg', TL.metal((180, 186, 192)), lms, v=0.3, shade=50)
    m('cream', TL.solid((236, 228, 206), 2, 74, 64), shade=40)
    m('white', TL.solid((246, 246, 244), 2, 75, 64), lms, v=0.15, shade=60)
    m('lampglass', TL.solid((255, 240, 200), 1, 76, 64), 'glow')
    m('wine_box', wine_box(), shade=30)
    m('crisps', crisps(), shade=30)
    m('canvas', TL.fabric((200, 184, 150), weave=48), shade=40)
    m('rope', TL.fabric((200, 180, 140), weave=32), shade=60)
    m('green_paint', TL.solid((26, 66, 44), 2, 77, 64), lms, v=0.1, shade=30)
    m('fascia_m', fascia_sign(), shade=30)
    m('till_keys', till_keys(), shade=40)
    m('umbrella_black', TL.fabric((28, 28, 32), weave=48), shade=40)
    m('umbrella_red', TL.stripes((150, 24, 30), (30, 60, 40), n_stripes=6), shade=40)


def alabaster(n=64):
    x, y = TL.xy(n)
    return C((250, 232, 190)) + TL.N3(n, 2, 78, 14) - (np.abs(y - 0.5) * 40)[..., None]


def fridge_back(w=128, h=128):
    a = np.zeros((h, w, 3), np.float32) + C((230, 240, 250))
    a[::32] = C((180, 190, 200))
    return a


def ember(n=64):
    return C((255, 120, 30)) + TL.N3(n, 1, 79, 50) * np.array([1, 0.6, 0.2])


def flame(w=64, h=128):
    x = np.linspace(-1, 1, w)[None, :]; y = np.linspace(1, 0, h)[:, None]
    shape = np.clip(1 - np.abs(x) / (0.15 + 0.85 * (1 - y) ** 0.8 * (y + 0.05) ** 0.3 + 1e-3), 0, 1) * np.clip(1.2 - y, 0, 1)
    col = np.stack([shape * 255, shape ** 1.4 * 170, shape ** 3 * 60], 2)
    return col.astype(np.float32)


def juke_lights(w=64, h=256):
    y = np.linspace(0, 1, h)[:, None]
    r = 0.5 + 0.5 * np.sin(y * 12); g = 0.5 + 0.5 * np.sin(y * 12 + 2); b = 0.5 + 0.5 * np.sin(y * 12 + 4)
    return (np.stack([r, g, b], 2) * np.ones((1, w, 1)) * 230 + 20).astype(np.float32)


def wine_box(w=256, h=128):
    a = TL.planks((150, 100, 56), n_planks=3, gap=(110, 70, 40), grain=8, n=256)[:h]
    im, d = draw(a)
    d.rectangle((0, 0, w - 1, h - 1), outline=(60, 34, 18), width=8)
    ctext(d, w / 2, h / 2, 'WINE', ML.font(54, serif=True), (250, 246, 236))
    return arr(im)


def crisps(w=256, h=256):
    a = np.zeros((h, w, 3), np.float32)
    im, d = draw(a)
    cols = [(220, 30, 30), (30, 90, 200), (40, 160, 60), (240, 170, 30)]
    for i in range(4):
        for j in range(4):
            c = cols[(i + j) % 4]
            d.rectangle((i * 64 + 4, j * 64 + 4, i * 64 + 60, j * 64 + 60), fill=c)
            d.ellipse((i * 64 + 16, j * 64 + 18, i * 64 + 48, j * 64 + 46), fill=(250, 230, 120))
    return arr(im)


def till_keys(n=128):
    a = np.zeros((n, n, 3), np.float32) + C((40, 34, 28))
    im, d = draw(a)
    for i in range(6):
        for j in range(5):
            d.ellipse((8 + i * 20, 8 + j * 24, 22 + i * 20, 22 + j * 24), fill=(240, 236, 220), outline=(200, 160, 70))
    return arr(im)


# ================================================================================================= small shared parts
def bottle_mesh(X, mat, x, y, z, kind=0, s=1.0, inverted=False):
    """a bottle standing on z (or, inverted, hanging neck-down from z for optics): 0 wine, 1 spirit, 2 beer"""
    if kind == 0:   prof = [(0, 0), (16, 0), (16, 74), (13, 86), (6, 98), (6, 124), (7, 126), (0, 128)]
    elif kind == 1: prof = [(0, 0), (19, 0), (19, 64), (15, 72), (7, 78), (7, 100), (8, 102), (0, 104)]
    else:           prof = [(0, 0), (12, 0), (12, 52), (9, 62), (5, 72), (5, 86), (6, 88), (0, 90)]
    if inverted: pts = [(r * s, z - h * s) for (r, h) in prof][::-1]
    else: pts = [(r * s, z + h * s) for (r, h) in prof]
    revolve(X.mesh(M_[mat]), pts, u_tiles=1, n=10, cx=x, cy=y)


def pint(X, x, y, z, full=1.0, stout=False, s=1.0):
    """a pint glass of ale (or stout) with a foam head"""
    h = 80 * s; r0, r1 = 15 * s, 20 * s
    bh = h * full * 0.86
    revolve(X.mesh(M_['stout' if stout else 'beer']), [(r0 - 1, z), (r0 + (r1 - r0) * bh / h - 1, z + bh)], n=10, cx=x, cy=y)
    rf = r0 + (r1 - r0) * min(1, (bh + 10 * s) / h) - 1
    revolve(X.mesh(M_['foam']), [(r0 + (r1 - r0) * bh / h - 1, z + bh), (rf, z + bh + 10 * s), (0, z + bh + 12 * s)], n=10, cx=x, cy=y)
    revolve(X.mesh(M_['glass']), [(r0, z), (r1, z + h)], n=10, cx=x, cy=y)


def flowers(X, x, y, z, col='petal_pink', n=7, R=30, seed=0, H=60):
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, R)
        px, py = x + rr * math.cos(a), y + rr * math.sin(a)
        pz = z + H * rng.uniform(0.6, 1.0)
        tube(X.mesh(M_['leaf']), [(x, y, z), (px, py, pz)], [2, 2], nseg=4, caps=(False, False))
        sphere(X.mesh(M_[col]), (px, py, pz), 9 + rng.uniform(0, 5), nu=8, nv=5)
        ellipsoid(X.mesh(M_['leaf']), (px * 0.6 + x * 0.4, py * 0.6 + y * 0.4, z + (pz - z) * 0.5), 12, 6, 3, nu=6, nv=4)


# ================================================================================================= the bar
def gantry_bay(name, base='cabinet', mat_arch='arch', seed=0):
    """one 440u bay of the back-bar (back at y 0, front at y -BAY_D): base cabinet or lit bottle fridges, marble back
    counter at BACK_Z, a brass optic rail with inverted bottles, two bottle shelves, the arched etched mirror, carved
    pilasters at the edges and the cornice (walkable top at CORNICE_Z)."""
    X = ML.Model()
    W, D = BAY_W / 2, BAY_D
    rng = np.random.default_rng(seed)
    # ---- base
    bx(X, 'mahog_dark', (-W, -D + 10, 0), (W, -40, 40), r=2)                         # plinth (kick)
    if base == 'cabinet':
        bx(X, 'panel_door', (-W, -D + 16, 40), (0, -40, BACK_Z - 24), r=2, tile=256)
        bx(X, 'panel_door', (0, -D + 16, 40), (W, -40, BACK_Z - 24), r=2, tile=256)
        for sx in (-30, 30):
            cylz(X, 'brass', sx, -D + 10, 6, 260, 300, n=8)
    else:   # two glass-door bottle fridges
        bx(X, 'mahog_dark', (-W, -D + 16, 40), (W, -40, BACK_Z - 24), r=2, faces='nsewb')
        G = X.mesh(M_['fridge_glow'])
        for (x0, x1) in ((-W + 16, -8), (8, W - 16)):
            G.quad((x0, -D + 15, 60), (x1, -D + 15, 60), (x1, -D + 15, BACK_Z - 40), (x0, -D + 15, BACK_Z - 40), tile=128, n=(0, -1, 0))
            for zz in (60, 200, 340):
                for k in range(5):
                    bottle_mesh(X, f'bottle{[5, 6, 2][(k + zz // 140) % 3]}', x0 + 20 + k * (x1 - x0 - 40) / 4, -D + 60, zz, kind=2, s=1.1)
            X.mesh(M_['glass']).quad((x0, -D + 10, 60), (x1, -D + 10, 60), (x1, -D + 10, BACK_Z - 40), (x0, -D + 10, BACK_Z - 40), n=(0, -1, 0))
            bx(X, 'chrome', (x1 - 18, -D + 4, 200), (x1 - 12, -D + 10, 360), r=2)
    bx(X, 'marble', (-W, -D, BACK_Z - 24), (W, 0, BACK_Z), r=4, k=2, tile=256)        # back counter top
    # ---- upper back: mirror + shelves (collision y -SHELF_D..0 from BACK_Z to the cornice)
    bx(X, 'mahog', (-W, -24, BACK_Z), (W, 0, CORNICE_Z - 60), r=1, faces='s')
    Y = ML.Model()
    ap = arch_poly(BAY_W - 100, CORNICE_Z - 60 - BACK_Z - 60, n=16)
    Ym = Y.mesh(M_[mat_arch])
    # mirror quad textured as the arch (the texture has the spandrels): one quad over the whole back
    w2, h2 = BAY_W - 60, CORNICE_Z - 60 - BACK_Z - 30
    Ym.poly([(-w2 / 2, 0, 0), (w2 / 2, 0, 0), (w2 / 2, h2, 0), (-w2 / 2, h2, 0)], (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    upright(X, Y, t=(0, -25, BACK_Z + 10))
    # gold arch moulding (a thin tube round the arch)
    r = (BAY_W - 60) / 2
    zt = BACK_Z + 10 + h2 - r
    path = [(-r, -27, BACK_Z + 10)] + [(r * math.cos(a), -27, zt + r * math.sin(a)) for a in np.linspace(math.pi, 0, 17)] + [(r, -27, BACK_Z + 10)]
    tube(X.mesh(M_['gold']), path, [4] * len(path), nseg=6, caps=(False, False))
    # optics: brass rail with 4 inverted spirit bottles + measures
    tube(X.mesh(M_['brass']), [(-W + 40, -60, 650), (W - 40, -60, 650)], [5, 5], nseg=8)
    for k in range(4):
        x = -150 + k * 100
        bottle_mesh(X, f'bottle{[2, 3, 4, 7][(k + seed) % 4]}', x, -SHELF_D + 40, 790, kind=1, s=1.0, inverted=True)
        cylz(X, 'chrome', x, -SHELF_D + 40, 14, 640, 690, n=8, bot=True)
        bx(X, 'brass', (x - 6, -SHELF_D + 30, 690), (x + 6, -SHELF_D + 50, 700), r=1)
    # shelf 1 (z 820) and shelf 2 (z 1080): glass shelves on brass brackets with bottles
    for (zs, kind, mats) in ((820, 0, (0, 1, 8, 3)), (1080, 2, (5, 6, 5, 6, 2))):
        X.mesh(M_['glass']).quad((-W + 30, -SHELF_D, zs), (W - 30, -SHELF_D, zs), (W - 30, -24, zs), (-W + 30, -24, zs), n=(0, 0, 1))
        bx(X, 'brass', (-W + 30, -SHELF_D - 4, zs - 8), (W - 30, -SHELF_D, zs), r=1)
        nb = 6 if kind == 0 else 9
        for k in range(nb):
            x = -W + 50 + k * (BAY_W - 100) / (nb - 1)
            bottle_mesh(X, f'bottle{mats[(k + seed) % len(mats)]}', x, -SHELF_D / 2 - 8 + rng.uniform(-10, 10), zs, kind=kind,
                        s=0.95 + rng.uniform(-0.05, 0.1))
    # bottles standing on the back counter behind the rail
    for k in range(5):
        x = -170 + k * 85
        bottle_mesh(X, f'bottle{(k * 3 + seed) % 9}', x, -SHELF_D + 26, BACK_Z, kind=1 if k % 2 else 0, s=0.9)
    # ---- pilasters (turned columns with capitals) at the bay edges
    for sx in (-W + 20, W - 20):
        bx(X, 'mahog_dark', (sx - 20, -SHELF_D - 20, BACK_Z), (sx + 20, -24, BACK_Z + 40), r=2)
        lathe(X, 'mahog', [(14, BACK_Z + 40), (16, BACK_Z + 60), (11, BACK_Z + 80), (11, CORNICE_Z - 160), (14, CORNICE_Z - 150),
                           (18, CORNICE_Z - 120), (22, CORNICE_Z - 100), (22, CORNICE_Z - 90)], cx=sx, cy=-SHELF_D - 20, n=12, cap=False)
        bx(X, 'gold', (sx - 24, -SHELF_D - 44, CORNICE_Z - 90), (sx + 24, -SHELF_D + 4, CORNICE_Z - 76), r=2)
    # ---- cornice: frieze, dentils, crown moulding; flat walkable top
    bx(X, 'mahog_dark', (-W, -D + 10, CORNICE_Z - 76), (W, 0, CORNICE_Z - 20), r=2, faces='nsewb')
    for k in range(int(BAY_W // 22)):
        x = -W + 6 + k * 22
        bx(X, 'mahog', (x, -D + 2, CORNICE_Z - 70), (x + 12, -D + 10, CORNICE_Z - 54), r=1, faces='swe')
    bx(X, 'gold', (-W, -D + 4, CORNICE_Z - 50), (W, -D + 10, CORNICE_Z - 44), r=1, faces='s')
    bx(X, 'mahog', (-W, -D, CORNICE_Z - 24), (W, 0, CORNICE_Z), r=4, k=2, tile=256)
    # spandrel fretwork: gilt rosettes over the pilasters
    for sx in (-W + 20, W - 20):
        sphere(X.mesh(M_['gold']), (sx, -D + 8, CORNICE_Z - 40), 9, nu=8, nv=5)
    ML.save(name, X)
    coll(name, [((-W, -D, 0), (W, 0, BACK_Z)),                                          # base + back counter
                ((-W, -SHELF_D, BACK_Z), (W, 0, CORNICE_Z - 76)),                       # mirror / shelves
                ((-W, -D, CORNICE_Z - 76), (W, 0, CORNICE_Z))])                         # cornice


def gantry_end(name='gantry_end'):
    """the narrow west end of the back-bar: a glazed cabinet of glasses under a big round station clock, same cornice"""
    X = ML.Model()
    W, D = 200, BAY_D
    bx(X, 'mahog_dark', (-W, -D + 10, 0), (W, -40, 40), r=2)
    bx(X, 'panel_door', (-W, -D + 16, 40), (W, -40, BACK_Z - 24), r=2, tile=256)
    bx(X, 'marble', (-W, -D, BACK_Z - 24), (W, 0, BACK_Z), r=4, k=2, tile=256)
    bx(X, 'mahog', (-W, -SHELF_D, BACK_Z), (W, 0, CORNICE_Z - 76), r=2, faces='nsewb')
    # glazed cabinet with wine glasses
    X.mesh(M_['glass']).quad((-W + 30, -SHELF_D - 2, BACK_Z + 30), (W - 30, -SHELF_D - 2, BACK_Z + 30),
                             (W - 30, -SHELF_D - 2, 880), (-W + 30, -SHELF_D - 2, 880), n=(0, -1, 0))
    for zs in (BACK_Z + 30, 700):
        for k in range(6):
            x = -W + 60 + k * 56
            revolve(X.mesh(M_['glass']), [(14, zs), (2, zs + 4), (2, zs + 50), (18, zs + 70), (20, zs + 110)], n=8, cx=x, cy=-SHELF_D + 40)
    bx(X, 'gold', (-W + 24, -SHELF_D - 8, 880), (W - 24, -SHELF_D, 896), r=2)
    # station clock
    Y = ML.Model()
    revolve(Y.mesh(M_['mahog_dark']), [(0, 0), (150, 0), (150, 30), (130, 36)], n=32)
    disc(Y.mesh(M_['clockface']), 130, 37, up=True, n=32)
    # (clock as a disc on the cabinet front: rotate about x so +z -> -y)
    X.add_model(Y, R=R_XZ, t=(0, -SHELF_D - 2, 1080))           # +z normal -> -y (faces the room)
    # cornice
    bx(X, 'mahog_dark', (-W, -D + 10, CORNICE_Z - 76), (W, 0, CORNICE_Z - 20), r=2, faces='nsewb')
    for k in range(int(2 * W // 22)):
        x = -W + 6 + k * 22
        bx(X, 'mahog', (x, -D + 2, CORNICE_Z - 70), (x + 12, -D + 10, CORNICE_Z - 54), r=1, faces='swe')
    bx(X, 'gold', (-W, -D + 4, CORNICE_Z - 50), (W, -D + 10, CORNICE_Z - 44), r=1, faces='s')
    bx(X, 'mahog', (-W, -D, CORNICE_Z - 24), (W, 0, CORNICE_Z), r=4, k=2, tile=256)
    ML.save(name, X)
    coll(name, [((-W, -D, 0), (W, 0, BACK_Z)), ((-W, -SHELF_D, BACK_Z), (W, 0, CORNICE_Z - 76)),
                ((-W, -D, CORNICE_Z - 76), (W, 0, CORNICE_Z))])


def counter_run(name, L):
    """straight counter module x -L/2..L/2, staff side at y 0, customer front at y -COUNTER_D: raised mahogany panels,
    polished bullnose top overhanging the front, brass foot rail on brackets, coat hooks under the lip"""
    X = ML.Model()
    H, D = COUNTER_Z, COUNTER_D
    h = L / 2
    bx(X, 'mahog_dark', (-h, -D + 14, 0), (h, 0, 50), r=2, faces='nsewt')               # plinth
    bx(X, 'mahog', (-h, -D + 8, 50), (h, 0, H - 40), r=1, faces='nsew')
    n = max(1, int(round(L / 220)))
    pw = L / n
    for k in range(n):
        x0 = -h + k * pw
        bx(X, 'panel', (x0 + 10, -D + 2, 90), (x0 + pw - 10, -D + 10, H - 70), r=2, tile=pw - 20, faces='s')
        bx(X, 'mahog_dark', (x0 - 8, -D, 50), (x0 + 8, -D + 10, H - 40), r=2, faces='swe')      # stile
        # coat hook
        tube(X.mesh(M_['brass']), [(x0 + pw / 2, -D - 2, H - 90), (x0 + pw / 2, -D - 16, H - 96), (x0 + pw / 2, -D - 18, H - 110)], [3, 3, 3], nseg=6)
    # top: bullnose front lip, polished
    bx(X, 'bartop', (-h, -D - 30, H - 40), (h, 10, H), r=14, k=3, tile=256)
    bx(X, 'mahog_dark', (-h, -D - 12, H - 60), (h, -D + 10, H - 40), r=3, faces='nswe')
    # foot rail + brackets
    tube(X.mesh(M_['brass']), [(-h, -D - 44, 70), (h, -D - 44, 70)], [9, 9], nseg=10, caps=(False, False))
    for k in range(n):
        x = -h + (k + 0.5) * pw
        tube(X.mesh(M_['brass']), [(x, -D, 70), (x, -D - 44, 70)], [5, 5], nseg=6)
    # staff side: shelf under the counter with glasses
    bx(X, 'mahog_dark', (-h, -60, 0), (h, 0, H - 40), r=1, faces='n')
    ML.save(name, X)
    coll(name, [((-h, -D, 0), (h, 0, H))])


def counter_corner(name='counter_corner'):
    """quarter-round counter corner: centre (0, 0) on the staff side, front radius COUNTER_D from angle -90 (south) to
    0 (east). Matches counter_run on the west face and the return (counter_run rotated 90) on the north face."""
    X = ML.Model()
    H, R = COUNTER_Z, COUNTER_D
    revolve(X.mesh(M_['mahog_dark']), [(R - 14, 0), (R - 14, 50)], n=12, a0=-90, a1=0)
    revolve(X.mesh(M_['mahog']), [(R - 8, 50), (R - 8, H - 40)], n=12, a0=-90, a1=0, u_tiles=2)
    revolve(X.mesh(M_['panel']), [(R - 2, 90), (R - 2, H - 70)], n=12, a0=-85, a1=-5, u_tiles=1)
    revolve(X.mesh(M_['bartop']), [(R + 16, H - 40), (R + 30, H - 26), (R + 30, H - 14), (R + 16, H)], n=16, a0=-90, a1=0, u_tiles=2)
    Mt = X.mesh(M_['bartop'])
    angs = np.radians(np.linspace(-90, 0, 17))
    for k in range(16):
        a0, a1 = angs[k], angs[k + 1]
        p = [(0, 0, H), ((R + 16) * math.cos(a0), (R + 16) * math.sin(a0), H), ((R + 16) * math.cos(a1), (R + 16) * math.sin(a1), H)]
        Mt.poly(p, (0, 0, 1), [(q[0] / 256, -q[1] / 256) for q in p])
    path = [((R + 44) * math.cos(a), (R + 44) * math.sin(a), 70) for a in angs]
    tube(X.mesh(M_['brass']), path, [9] * len(path), nseg=10, caps=(False, False))
    ML.save(name, X)
    pie = [(0, 0)] + [(R * math.cos(a), R * math.sin(a)) for a in np.radians(np.linspace(-90, 0, 7))]
    coll(name, hulls=[[(x, y, z) for (x, y) in pie for z in (0, H)]])


def beer_pumps(name='beer_pumps', n=4):
    """a row of hand pulls: brass-collared pump bodies on a drip tray, tall black ceramic handles with pump clips"""
    X = ML.Model()
    L = n * 70
    bx(X, 'brass', (-L / 2 - 10, -40, 0), (L / 2 + 10, 40, 10), r=3)
    for k in range(n):
        x = -L / 2 + 35 + k * 70
        lathe(X, 'brass', [(16, 10), (16, 30), (12, 36), (12, 60), (16, 66), (16, 72), (8, 76)], cx=x, cy=0, n=12)
        # handle leaning slightly toward the customer (-y)
        top = (x, -14, 200)
        tube(X.mesh(M_['ceramic']), [(x, 0, 76), (x, -4, 110), (x, -12, 180), top], [6, 9, 10, 8], nseg=10)
        sphere(X.mesh(M_['ceramic']), top, 10, nu=10, nv=6)
        pic(X.mesh(M_[f'clip{k % 4}']), (x, -16, 150), (0, -1, 0.06), 28, 56)
        # spout curling down at the staff side
        tube(X.mesh(M_['chrome']), [(x, 8, 56), (x, 26, 60), (x, 30, 40)], [3, 3, 3], nseg=6)
    ML.save(name, X)
    coll(name, [((-L / 2 - 10, -40, 0), (L / 2 + 10, 40, 180))])


def lager_font(name='lager_font'):
    """T-bar lager font with three illuminated badges and chrome taps"""
    X = ML.Model()
    cylz(X, 'chrome', 0, 0, 16, 0, 160, n=12)
    tube(X.mesh(M_['chrome']), [(-90, 0, 170), (90, 0, 170)], [14, 14], nseg=12)
    for k, x in enumerate((-60, 0, 60)):
        Y = ML.Model()
        disc(Y.mesh(M_[f'clip{(k + 1) % 4}']), 22, 0, n=16)
        X.add_model(Y, R=R_XZ, t=(x, -16, 190))
        tube(X.mesh(M_['chrome']), [(x, -6, 160), (x, -14, 140), (x, -14, 124)], [4, 4, 3], nseg=6)
        tube(X.mesh(M_['ceramic']), [(x, -10, 172), (x, -24, 220)], [4, 3], nseg=6)
    bx(X, 'chrome', (-100, -50, 0), (100, 30, 8), r=3)
    ML.save(name, X)
    coll(name, [((-100, -40, 0), (100, 30, 200))])


def coffee_machine(name='coffee_machine'):
    X = ML.Model()
    W, D, H = 300, 180, 240
    bx(X, 'chrome', (-W / 2, -D / 2, 0), (W / 2, D / 2, H), r=14, k=3)
    bx(X, 'iron', (-W / 2 + 10, -D / 2 - 2, 150), (W / 2 - 10, -D / 2, 210), r=2, faces='s')
    for k, x in enumerate((-70, 70)):
        lathe(X, 'chrome', [(24, 130), (24, 140), (16, 150)], cx=x, cy=-D / 2 - 20, n=10)
        tube(X.mesh(M_['iron']), [(x, -D / 2 - 20, 120), (x, -D / 2 - 60, 116)], [5, 4], nseg=6)
        lathe(X, 'white', [(12, 20), (14, 40), (0, 40)], cx=x, cy=-D / 2 - 20, n=10)
    bx(X, 'chrome', (-W / 2 + 10, -D / 2 - 40, 0), (W / 2 - 10, -D / 2, 16), r=2)
    for k in range(5):     # cups on top
        lathe(X, 'white', [(10, H), (14, H + 26), (0, H + 26)], cx=-100 + k * 50, cy=0, n=10)
    for sx in (-1, 1):
        cylz(X, 'iron', sx * 120, -D / 2 - 8, 8, 170, 186, n=8)
    ML.save(name, X)
    coll(name, [((-W / 2, -D / 2 - 40, 0), (W / 2, D / 2, H + 26))])


def hurricane_vase(name='hurricane'):
    X = ML.Model()
    revolve(X.mesh(M_['glass']), [(30, 0), (8, 10), (8, 40), (30, 60), (60, 120), (66, 200), (60, 250)], n=16)
    revolve(X.mesh(M_['glass']), [(60, 250), (56, 250), (60, 200), (54, 120), (26, 62)], n=16, inward=True)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 50, 0, 250)])


def till(name='till'):
    """antique brass cash register with a rounded crest and keys"""
    X = ML.Model()
    bx(X, 'brass', (-70, -60, 0), (70, 60, 40), r=4)
    Y = ML.Model()
    pts = [(-70, 0), (70, 0), (70, 100), (50, 130), (-50, 130), (-70, 100)]
    prism(Y.mesh(M_['brass']), pts, 0, 100, tile=64)
    upright(X, Y, t=(0, 50, 40))
    pic(X.mesh(M_['till_keys']), (0, -64, 80), (0, -1, 0.5), 120, 70)
    bx(X, 'black', (-40, -58, 40), (40, -50, 60), r=1) if 'black' in M_ else None
    tube(X.mesh(M_['brass']), [(74, 0, 60), (96, 0, 80), (100, 0, 110)], [4, 4, 4], nseg=6)
    sphere(X.mesh(M_['ceramic']), (100, 0, 116), 9)
    ML.save(name, X)
    coll(name, [((-70, -60, 0), (70, 60, 170))])


def wine_display(name='wine_display'):
    X = ML.Model()
    bx(X, 'oak', (-90, -50, 0), (90, 50, 110), r=2, faces='nsewb')
    pic(X.mesh(M_['wine_box']), (0, -51, 55), (0, -1, 0), 170, 90)
    for k in range(3):
        bottle_mesh(X, f'bottle{(0, 1, 8)[k]}', -50 + k * 50, 0, 40, kind=0, s=1.0)
    ML.save(name, X)
    coll(name, [((-90, -50, 0), (90, 50, 140))])


def counter_board(name='snacks_stand', tex='snacks', w=140, h=180):
    """small chalkboard on an easel stand for the counter"""
    X = ML.Model()
    pic(X.mesh(M_[tex]), (0, -10, h / 2 + 10), (0, -1, 0.25), w, h)
    tube(X.mesh(M_['oak']), [(-w / 2 + 10, -6, 0), (-w / 2 + 10, -16, h + 14)], [3, 3], nseg=5)
    tube(X.mesh(M_['oak']), [(w / 2 - 10, -6, 0), (w / 2 - 10, -16, h + 14)], [3, 3], nseg=5)
    tube(X.mesh(M_['oak']), [(0, 30, 0), (0, -8, h)], [3, 3], nseg=5)
    ML.save(name, X)


def flower_vase(name='lilies'):
    X = ML.Model()
    lathe(X, 'glass', [(18, 0), (22, 40), (14, 90), (18, 110)], n=12, cap=False)
    flowers(X, 0, 0, 100, 'petal_white', n=9, R=40, seed=3, H=110)
    ML.save(name, X)


def crisp_card(name='crisp_card'):
    """a hanging card of crisp packets and peanuts"""
    X = ML.Model()
    pic(X.mesh(M_['crisps']), (0, -2, 0), (0, -1, 0), 120, 160)
    ML.save(name, X)


def glass_rack(name='glass_rack'):
    """a tray of upturned pint glasses"""
    X = ML.Model()
    bx(X, 'black', (-80, -60, 0), (80, 60, 8), r=2) if 'black' in M_ else bx(X, 'iron', (-80, -60, 0), (80, 60, 8), r=2)
    for i in range(4):
        for j in range(3):
            revolve(X.mesh(M_['glass']), [(20, 8), (15, 88), (0, 88)], n=8, cx=-60 + i * 40, cy=-40 + j * 40)
    ML.save(name, X)


# ================================================================================================= furniture
def stool(name, seat):
    """bar stool: upholstered round seat with a piped edge, four turned legs with a ring stretcher"""
    X = ML.Model()
    H = STOOL_Z
    lathe(X, seat, [(44, H - 40), (48, H - 26), (46, H - 6), (36, H), (0, H + 2)], n=16)
    lathe(X, 'mahog', [(40, H - 52), (40, H - 40)], n=16)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        top = (30 * math.cos(a), 30 * math.sin(a), H - 50); bot = (42 * math.cos(a), 42 * math.sin(a), 0)
        tube(X.mesh(M_['mahog']), [bot, ((top[0] + bot[0]) / 2, (top[1] + bot[1]) / 2, H / 2), top], [6, 8, 6], nseg=8)
    path = [(37 * math.cos(a), 37 * math.sin(a), 110) for a in np.linspace(0, 2 * math.pi, 17)]
    tube(X.mesh(M_['mahog']), path, [4] * 17, nseg=6, caps=(False, False))
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 40, 0, H)])


def pub_table(name='pub_table', glasses=1):
    """round mahogany table on a cast-iron Britannia tripod base (you can crawl under it)"""
    X = ML.Model()
    R, H = TABLE_R, TABLE_Z
    lathe(X, 'bartop', [(R - 6, H - 22), (R, H - 16), (R, H - 4), (R - 6, H), (0, H)], n=28, u=3)
    disc(X.mesh(M_['mahog_dark']), R - 6, H - 22, up=False, n=28)
    lathe(X, 'iron', [(22, 40), (14, 70), (12, 180), (18, 200), (12, 240), (12, H - 40), (40, H - 26), (40, H - 22)], n=12, cap=False)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        p = [(14 * math.cos(a), 14 * math.sin(a), 60), (60 * math.cos(a), 60 * math.sin(a), 40), (100 * math.cos(a), 100 * math.sin(a), 8),
             (110 * math.cos(a), 110 * math.sin(a), 6)]
        tube(X.mesh(M_['iron']), p, [10, 8, 7, 9], nseg=8)
    if glasses:
        rng = np.random.default_rng(len(name))
        for k in range(glasses):
            a = rng.uniform(0, 2 * math.pi)
            pint(X, 60 * math.cos(a), 60 * math.sin(a), H, full=rng.uniform(0.3, 1.0), stout=k == 1)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, R - 8, H - 22, H), (0, 0, 18, 0, H - 22)])


def banquette(name, L):
    """green tapestry banquette along a wall (back at y 0, seat to y -BANQ_D): mahogany plinth and back rail"""
    X = ML.Model()
    h = L / 2; D = BANQ_D
    bx(X, 'mahog_dark', (-h, -D + 10, 0), (h, 0, SEAT_Z - 50), r=3)
    bx(X, 'tapestry', (-h, -D, SEAT_Z - 54), (h, -10, SEAT_Z), r=16, k=3, tile=128)
    bx(X, 'tapestry', (-h + 8, -60, SEAT_Z), (h - 8, -10, BANQ_BACK - 50), r=18, k=3, tile=128)
    for k in range(int(L // 180)):
        x = -h + 90 + k * 180
        sphere(X.mesh(M_['brass']), (x, -62, BANQ_BACK - 140), 5, nu=6, nv=4)
    bx(X, 'mahog', (-h, -40, BANQ_BACK - 50), (h, 0, BANQ_BACK), r=6, k=2)
    for x in (-h, h - 20):
        bx(X, 'mahog', (x, -D, 0), (x + 20, 0, SEAT_Z + 40), r=4)
    ML.save(name, X)
    coll(name, [((-h, -D, 0), (h, 0, SEAT_Z)), ((-h, -60, SEAT_Z), (h, 0, BANQ_BACK))])


def settle(name='settle', L=600):
    """high-backed wooden settle: panelled back to SETTLE_BACK with a carved crest, red velvet seat (back at y 0)"""
    X = ML.Model()
    h = L / 2; D = SETTLE_D
    bx(X, 'panel2', (-h, -50, 0), (h, 0, SETTLE_BACK - 40), r=2, tile=256, faces='nsew')
    bx(X, 'mahog_dark', (-h - 6, -56, SETTLE_BACK - 40), (h + 6, 6, SETTLE_BACK), r=5, k=2)
    Y = ML.Model()
    crest = [(-120, 0), (120, 0), (100, 30), (40, 40), (0, 64), (-40, 40), (-100, 30)]
    prism(Y.mesh(M_['mahog']), crest, -10, 10, tile=128)
    upright(X, Y, t=(0, -25, SETTLE_BACK))
    bx(X, 'mahog_dark', (-h, -D, 0), (h, -50, SEAT_Z - 40), r=2)
    bx(X, 'velvet_red', (-h + 6, -D, SEAT_Z - 40), (h - 6, -50, SEAT_Z), r=12, k=2)
    bx(X, 'velvet_red', (-h + 14, -80, SEAT_Z), (h - 14, -50, 520), r=12, k=2)
    for x in (-h, h - 30):
        bx(X, 'mahog', (x, -D, 0), (x + 30, -50, SEAT_Z + 120), r=6, k=2)
    ML.save(name, X)
    coll(name, [((-h, -50, 0), (h, 0, SETTLE_BACK)), ((-h, -D, 0), (h, -50, SEAT_Z))])


def booth_table(name='booth_table', L=520, W=240):
    """long table for the settle islands (iron trestle)"""
    X = ML.Model()
    H = TABLE_Z
    bx(X, 'bartop', (-L / 2, -W / 2, H - 24), (L / 2, W / 2, H), r=8, k=2, tile=256)
    for sx in (-1, 1):
        x = sx * (L / 2 - 70)
        tube(X.mesh(M_['iron']), [(x, -W / 2 + 30, 0), (x, 0, 60), (x, W / 2 - 30, 0)], [8, 8, 8], nseg=8)
        tube(X.mesh(M_['iron']), [(x, 0, 60), (x, 0, H - 24)], [9, 9], nseg=8)
    tube(X.mesh(M_['iron']), [(-L / 2 + 70, 0, 120), (L / 2 - 70, 0, 120)], [5, 5], nseg=6)
    pint(X, -120, -40, H, 0.8); pint(X, 100, 50, H, 0.5, stout=True); pint(X, 160, -50, H, 0.2)
    ML.save(name, X)
    coll(name, [((-L / 2, -W / 2, H - 24), (L / 2, W / 2, H))], cyls=[(-L / 2 + 70, 0, 12, 0, H - 24), (L / 2 - 70, 0, 12, 0, H - 24)])


def piano(name='piano'):
    """upright piano in black lacquer with brass candle sconces, open keyboard, music stand and a stool"""
    X = ML.Model()
    W, D, H = PIANO
    h = W / 2
    bx(X, 'black_lacquer', (-h, -D + 100, 0), (h, 0, H), r=6, k=2)                    # case
    bx(X, 'black_lacquer', (-h, -D + 10, PIANO_KEYS_Z - 40), (h, -D + 100, PIANO_KEYS_Z), r=4, faces='nsewb')  # key bed
    X.mesh(M_['keys']).quad((-h + 40, -D + 20, PIANO_KEYS_Z + 1), (h - 40, -D + 20, PIANO_KEYS_Z + 1),
                            (h - 40, -D + 90, PIANO_KEYS_Z + 1), (-h + 40, -D + 90, PIANO_KEYS_Z + 1), n=(0, 0, 1))
    for x in (-h, h - 40):
        bx(X, 'black_lacquer', (x, -D, 0), (x + 40, -D + 100, PIANO_KEYS_Z + 30), r=6, k=2)
        lathe(X, 'black_lacquer', [(16, 0), (20, 40), (14, 100), (18, PIANO_KEYS_Z - 40)], cx=x + 20, cy=-D + 30, n=10, cap=False)
    bx(X, 'mahog_dark', (-h + 60, -D + 96, PIANO_KEYS_Z + 60), (h - 60, -D + 104, H - 120), r=2, faces='s')
    Y = ML.Model()
    pic(Y.mesh(M_['cream']), (0, 0, 0), (0, -1, 0.3), 200, 120)
    X.add_model(Y, t=(0, -D + 96, PIANO_KEYS_Z + 140))
    for sx in (-1, 1):
        tube(X.mesh(M_['brass']), [(sx * (h - 80), -D + 100, 560), (sx * (h - 70), -D + 60, 570), (sx * (h - 70), -D + 50, 590)], [3, 3, 3], nseg=6)
        lathe(X, 'cream', [(6, 590), (6, 640), (0, 642)], cx=sx * (h - 70), cy=-D + 50, n=8)
    bx(X, 'black_lacquer', (-h - 6, -D + 94, H - 20), (h + 6, 6, H), r=4, k=2)      # lid
    # things on top: a pint, sheet music, a candelabra
    pint(X, -220, -100, H, 0.6)
    bx(X, 'cream', (80, -150, H), (220, -60, H + 4), r=1)
    lathe(X, 'brass', [(30, H), (8, H + 20), (6, H + 90), (0, H + 92)], cx=-40, cy=-120, n=10)
    for k in range(3):
        lathe(X, 'cream', [(5, H + 90), (5, H + 140), (0, H + 142)], cx=-70 + k * 30, cy=-120, n=6)
    ML.save(name, X)
    coll(name, [((-h, -D + 100, 0), (h, 0, H)), ((-h, -D, 0), (h, -D + 100, PIANO_KEYS_Z))])


def piano_stool(name='piano_stool'):
    X = ML.Model()
    bx(X, 'velvet_red', (-110, -60, 180), (110, 60, 220), r=12, k=2)
    bx(X, 'black_lacquer', (-110, -60, 150), (110, 60, 180), r=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(X, 'black_lacquer', [(10, 0), (14, 40), (10, 100), (12, 150)], cx=sx * 90, cy=sy * 44, n=8, cap=False)
    ML.save(name, X)
    coll(name, [((-110, -60, 0), (110, 60, 220))])


def fireplace(name='fireplace'):
    """Victorian fireplace on a wall (back y 0, front -y): mahogany surround with columns, green tiled slips, cast-iron
    arched insert with a coal grate and live flames, marble mantel shelf, overmantel mirror with a walkable top"""
    X = ML.Model()
    h = FIRE_W / 2
    D = MANTEL_D
    # surround
    for sx in (-1, 1):
        x0, x1 = sorted((sx * h, sx * (h - 120)))
        bx(X, 'mahog', (x0, -D + 30, 0), (x1, 0, MANTEL_Z - 30), r=3, faces='nsewt')
        lathe(X, 'mahog_dark', [(18, 20), (22, 40), (14, 70), (14, MANTEL_Z - 110), (22, MANTEL_Z - 90), (24, MANTEL_Z - 60)],
              cx=sx * (h - 60), cy=-D + 14, n=12)
    bx(X, 'mahog', (-h + 120, -D + 30, 440), (h - 120, 0, MANTEL_Z - 30), r=2)
    # tiled slips and arched cast iron insert
    X.mesh(M_['tiles_green']).quad((-h + 120, -D + 40, 0), (h - 120, -D + 40, 0), (h - 120, -D + 40, 440), (-h + 120, -D + 40, 440), tile=64, n=(0, -1, 0))
    Y = ML.Model()
    outer = arch_poly(280, 380, n=12)
    prism(Y.mesh(M_['iron']), outer, 0, 14, tile=128)
    upright(X, Y, t=(0, -D + 54, 0))
    bx(X, 'iron', (-120, -D + 10, 0), (120, -D + 60, 14), r=2)
    # firebox (dark recess look) + coal + flames
    bx(X, 'coal', (-90, -D + 70, 30), (90, -D + 130, 110), r=8, k=2, faces='t')
    for k in range(5):
        sphere(X.mesh(M_['ember']), (-60 + k * 30, -D + 90, 100), 18, nu=8, nv=5)
    F = X.mesh(M_['flame'])
    for k in range(3):
        x = -50 + k * 50
        F.quad((x - 26, -D + 96, 104), (x + 26, -D + 96, 104), (x + 26, -D + 96, 230), (x - 26, -D + 96, 230), tile=64, n=(0, -1, 0))
    tube(X.mesh(M_['iron']), [(-100, -D + 64, 40), (100, -D + 64, 40)], [5, 5], nseg=6)
    for k in range(5):
        x = -80 + k * 40
        tube(X.mesh(M_['iron']), [(x, -D + 64, 30), (x, -D + 64, 110)], [3, 3], nseg=5)
    # mantel shelf
    bx(X, 'marble', (-h - 30, -D - 20, MANTEL_Z - 30), (h + 30, 0, MANTEL_Z), r=6, k=2, tile=256)
    # overmantel: framed mirror between turned posts, gilt edge; walkable top at OVERMANTEL_Z
    bx(X, 'mahog_dark', (-h + 20, -40, MANTEL_Z), (h - 20, 0, OVERMANTEL_Z - 60), r=2, faces='s')
    X.mesh(M_['mirror']).quad((-h + 70, -42, MANTEL_Z + 50), (h - 70, -42, MANTEL_Z + 50), (h - 70, -42, OVERMANTEL_Z - 110),
                              (-h + 70, -42, OVERMANTEL_Z - 110), tile=256, n=(0, -1, 0))
    path = [(-h + 70, -44, MANTEL_Z + 50), (h - 70, -44, MANTEL_Z + 50), (h - 70, -44, OVERMANTEL_Z - 110), (-h + 70, -44, OVERMANTEL_Z - 110), (-h + 70, -44, MANTEL_Z + 50)]
    tube(X.mesh(M_['gold']), path, [6] * 5, nseg=6, caps=(False, False))
    for sx in (-1, 1):
        lathe(X, 'mahog', [(20, MANTEL_Z), (24, MANTEL_Z + 30), (14, MANTEL_Z + 60), (14, OVERMANTEL_Z - 100), (22, OVERMANTEL_Z - 80),
                           (22, OVERMANTEL_Z - 60)], cx=sx * (h - 40), cy=-OVERMANTEL_D + 30, n=12)
    bx(X, 'mahog_dark', (-h - 10, -OVERMANTEL_D, OVERMANTEL_Z - 60), (h + 10, 0, OVERMANTEL_Z - 20), r=3, faces='nsewb')
    bx(X, 'gold', (-h - 10, -OVERMANTEL_D - 4, OVERMANTEL_Z - 44), (h + 10, -OVERMANTEL_D, OVERMANTEL_Z - 36), r=1, faces='s')
    bx(X, 'mahog', (-h - 20, -OVERMANTEL_D - 10, OVERMANTEL_Z - 20), (h + 20, 0, OVERMANTEL_Z), r=5, k=2, tile=256)
    # mantel dressing: mantel clock, candlesticks, a pipe stand look-alike
    bx(X, 'mahog_dark', (-60, -D + 20, MANTEL_Z), (60, -D + 90, MANTEL_Z + 120), r=12, k=2)
    Y = ML.Model(); disc(Y.mesh(M_['clockface']), 40, 0, n=20)
    X.add_model(Y, R=R_XZ, t=(0, -D + 19, MANTEL_Z + 66))
    for sx in (-1, 1):
        lathe(X, 'brass', [(24, MANTEL_Z), (10, MANTEL_Z + 16), (7, MANTEL_Z + 90), (14, MANTEL_Z + 100), (6, MANTEL_Z + 104)], cx=sx * 220, cy=-D + 60, n=10)
        lathe(X, 'cream', [(6, MANTEL_Z + 104), (6, MANTEL_Z + 160), (0, MANTEL_Z + 162)], cx=sx * 220, cy=-D + 60, n=8)
    ML.save(name, X)
    coll(name, [((-h, -D + 30, 440), (h, 0, MANTEL_Z - 30)),                            # lintel
                ((-h, -D + 30, 0), (-h + 120, 0, 440)), ((h - 120, -D + 30, 0), (h, 0, 440)),
                ((-h + 120, -D + 60, 0), (h - 120, 0, 440)),                            # insert (the fire is decoration)
                ((-h - 30, -D - 20, MANTEL_Z - 30), (h + 30, 0, MANTEL_Z)),
                ((-h + 20, -40, MANTEL_Z), (h - 20, 0, OVERMANTEL_Z - 60)),
                ((-h - 20, -OVERMANTEL_D - 10, OVERMANTEL_Z - 60), (h + 20, 0, OVERMANTEL_Z))])


def longcase_clock(name='longcase'):
    """grandfather clock with the trunk door swung open (the secret entry): hood with a painted dial and swan-neck
    pediment, empty trunk (the pendulum is a separate mover), plinth"""
    X = ML.Model()
    W, D, H = CLOCK
    h = W / 2
    tw, td, th = CLOCK_TRUNK
    z0 = 16
    bx(X, 'mahog_dark', (-h - 10, -D - 10, 0), (h + 10, 0, z0), r=3)                       # plinth sill (step)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * h, sx * tw / 2))
        bx(X, 'mahog', (x0, -D, z0), (x1, 0, th + 40), r=2, tile=128)
    bx(X, 'mahog', (-tw / 2, -D + td, z0), (tw / 2, 0, th + 40), r=1, faces='s')
    bx(X, 'mahog_dark', (-tw / 2, -D + td - 2, z0), (tw / 2, -D + td, th + 40), r=1, faces='s')
    bx(X, 'mahog_dark', (-h - 10, -D - 10, th + 40), (h + 10, 6, th + 80), r=4, k=2)       # waist moulding
    bx(X, 'mahog', (-h, -D, th + 80), (h, 0, H - 120), r=3, faces='nsewt')                 # hood
    Y = ML.Model(); disc(Y.mesh(M_['clockface']), 80, 0, n=28)
    X.add_model(Y, R=R_XZ, t=(0, -D - 1, th + 80 + 120))
    tube(X.mesh(M_['brass']), [(80 * math.cos(a), -D - 3, th + 200 + 80 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)], [5] * 25, nseg=6, caps=(False, False))
    for sx in (-1, 1):
        lathe(X, 'mahog_dark', [(10, th + 80), (10, H - 130), (14, H - 120)], cx=sx * (h - 12), cy=-D - 8, n=8)
    Y = ML.Model()
    ped = [(-h - 10, 0), (h + 10, 0), (h + 10, 50), (40, 110), (20, 96), (0, 120), (-20, 96), (-40, 110), (-h - 10, 50)]
    prism(Y.mesh(M_['mahog_dark']), ped, -D / 2, D / 2, tile=128)
    upright(X, Y, t=(0, -D / 2, H - 120))
    for sx in (-1, 0, 1):
        X.add_model(_finial(), t=(sx * (h - 10), -D / 2, H - 120 + (50 if sx else 120)))
    # trunk door swung open (hinged on the east edge)
    a = math.radians(-110)
    hx, hy = tw / 2, -D
    dw = tw + 10
    q = [(hx, hy, z0 + 20), (hx + dw * math.cos(a + math.pi), hy + dw * math.sin(a + math.pi), z0 + 20),
         (hx + dw * math.cos(a + math.pi), hy + dw * math.sin(a + math.pi), th + 30), (hx, hy, th + 30)]
    n_ = np.cross(np.subtract(q[1], q[0]), np.subtract(q[3], q[0])); n_ = n_ / np.linalg.norm(n_)
    X.mesh(M_['panel_door']).poly(q, n_, [(0, 1), (1, 1), (1, 0), (0, 0)])
    q2 = [np.add(p, n_ * -6) for p in q]
    X.mesh(M_['mahog']).poly(q2[::-1], -n_, [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save(name, X)
    coll(name, [((-h, -D, 0), (-tw / 2, 0, th + 40)), ((tw / 2, -D, 0), (h, 0, th + 40)),
                ((-tw / 2, -D + td, 0), (tw / 2, 0, th + 40)),
                ((-h, -D, th + 40), (h, 0, H - 120))])


def _finial():
    Y = ML.Model()
    lathe(Y, 'brass', [(8, 0), (4, 14), (9, 24), (4, 36), (0, 40)], n=8)
    return Y


def pendulum(name='pendulum', L=340):
    """the clock's brass pendulum (model origin at the pivot, hanging down -z): rod + bob"""
    X = ML.Model()
    tube(X.mesh(M_['brass']), [(0, 0, 0), (0, 0, -L)], [2.5, 2.5], nseg=6)
    Y = ML.Model(); lathe(Y, 'brass', [(0, -12), (36, -6), (36, 6), (0, 12)], n=20, cap=False)
    X.add_model(Y, R=R_XZ, t=(0, 0, -L - 20))
    ML.save(name, X)


def fruit_machine(name='fruit_machine'):
    X = ML.Model()
    W, D, H = FRUIT
    h = W / 2
    bx(X, 'fruit_body', (-h, -D, 0), (h, 0, H - 120), r=10, k=2)
    pic(X.mesh(M_['fruit']), (0, -D - 1, (H - 120) / 2 + 160), (0, -1, 0), W - 30, (H - 120) - 260 + 260)
    bx(X, 'chrome', (-h - 4, -D - 60, 330), (h + 4, -D + 20, 360), r=6, k=2)               # button deck
    for k in range(3):
        sphere(X.mesh(M_['juke_lights']), (-80 + k * 80, -D - 40, 362), 12, nu=8, nv=4)
    bx(X, 'fruit_body', (-h, -D + 30, H - 120), (h, 0, H), r=14, k=2)                      # topper
    pic(X.mesh(M_['juke_lights']), (0, -D + 29, H - 60), (0, -1, 0), W - 40, 80)
    bx(X, 'chrome', (-60, -D - 4, 80), (60, -D, 160), r=2, faces='s')
    ML.save(name, X)
    coll(name, [((-h, -D - 60, 0), (h, 0, H))])


def jukebox(name='jukebox'):
    """arched jukebox: walnut cabinet, bubbling light tubes up the sides and over the arch, title window, chrome grille"""
    X = ML.Model()
    W, D, H = JUKE
    h = W / 2
    Y = ML.Model()
    prism(Y.mesh(M_['mahog']), arch_poly(W, H, n=16), -D, 0, tile=128)
    X.add_model(Y, R=R_XZ, t=(0, 0, 0))
    pic(X.mesh(M_['juke']), (0, -D - 1, 280), (0, -1, 0), W - 80, 380)
    r = h - 24
    path = [(-r, -D - 4, 40)] + [(r * math.cos(a), -D - 4, H - h + r * math.sin(a)) for a in np.linspace(math.pi, 0, 17)] + [(r, -D - 4, 40)]
    tube(X.mesh(M_['juke_lights']), path, [12] * len(path), nseg=8, caps=(False, False))
    X.mesh(M_['glass']).quad((-h + 40, -D - 8, H - h - 60), (h - 40, -D - 8, H - h - 60), (h - 40, -D - 8, H - 80), (-h + 40, -D - 8, H - 80), n=(0, -1, 0))
    sphere(X.mesh(M_['chrome']), (0, -D - 20, H - h + 20), 40, nu=12, nv=6)
    ML.save(name, X)
    coll(name, [((-h, -D, 0), (h, 0, H - 40))])


def dartboard_cab(name='dartboard'):
    """dartboard in a mahogany cabinet with its doors open, three darts in the board (wall mounted, back y 0)"""
    X = ML.Model()
    bx(X, 'mahog', (-130, -30, -130), (130, 0, 130), r=3)
    Y = ML.Model(); disc(Y.mesh(M_['dart']), 110, 0, n=32); revolve(Y.mesh(M_['iron']), [(112, -10), (112, 0)], n=32)
    X.add_model(Y, R=R_XZ, t=(0, -42, 0))
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 130, sx * 260))
        bx(X, 'mahog', (x0, -40, -130), (x1, -28, 130), r=2)
        pic(X.mesh(M_['chalk']) if 'chalk' in M_ else X.mesh(M_['cork']), ((x0 + x1) / 2, -41, 0), (0, -1, 0), 110, 220)
    for (dx, dz) in ((20, 30), (-30, 10), (5, -40)):
        tube(X.mesh(M_['brass']), [(dx, -44, dz), (dx + 4, -70, dz + 6)], [2, 3], nseg=5)
        tube(X.mesh(M_['petal_red']), [(dx + 4, -70, dz + 6), (dx + 6, -86, dz + 9)], [5, 1], nseg=4)
    ML.save(name, X)


def chandelier(name='chandelier', arms=8, R=260):
    """brass gasolier: chain, central column with a ball, curling arms with frosted tulip shades (model origin at the
    ceiling rose, hanging down)"""
    X = ML.Model()
    lathe(X, 'brass', [(40, -14), (26, -4), (0, 0)], n=12, cap=False)
    tube(X.mesh(M_['brass']), [(0, 0, -10), (0, 0, -170)], [4, 4], nseg=6)
    lathe(X, 'brass', [(0, -300), (14, -296), (20, -270), (10, -250), (30, -230), (30, -214), (8, -200), (8, -170), (0, -168)], n=12, cap=False)
    sphere(X.mesh(M_['brass']), (0, 0, -330), 22, nu=10, nv=6)
    for k in range(arms):
        a = 2 * math.pi * k / arms
        ca, sa = math.cos(a), math.sin(a)
        p = [(14 * ca, 14 * sa, -226), (R * 0.4 * ca, R * 0.4 * sa, -260), (R * 0.8 * ca, R * 0.8 * sa, -250), (R * ca, R * sa, -220), (R * ca, R * sa, -200)]
        tube(X.mesh(M_['brass']), p, [5, 5, 5, 5, 6], nseg=6)
        c = (R * ca, R * sa, -200)
        revolve(X.mesh(M_['glow_shade']), [(14, -200), (24, -184), (36, -150), (40, -130), (34, -126)], n=10, cx=c[0], cy=c[1])
        revolve(X.mesh(M_['glow_shade']), [(34, -126), (40, -130), (36, -150), (24, -184), (14, -200)], n=10, cx=c[0], cy=c[1], inward=True)
        lathe(X, 'brass', [(14, -204), (14, -196), (0, -196)], cx=c[0], cy=c[1], n=8)
    ML.save(name, X)


def pendant(name='pendant', drop=300):
    """alabaster bowl pendant on three brass chains (origin at the ceiling)"""
    X = ML.Model()
    lathe(X, 'brass', [(30, -10), (18, -2), (0, 0)], n=10, cap=False)
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(X.mesh(M_['brass']), [(0, 0, -10), (80 * math.cos(a), 80 * math.sin(a), -drop)], [2, 2], nseg=4)
    revolve(X.mesh(M_['glow_shade']), [(0, -drop - 70), (40, -drop - 64), (70, -drop - 40), (86, -drop - 6), (90, -drop)], n=20)
    revolve(X.mesh(M_['glow_shade']), [(90, -drop), (86, -drop - 6), (70, -drop - 40), (40, -drop - 64), (0, -drop - 70)], n=20, inward=True)
    path = [(92 * math.cos(a), 92 * math.sin(a), -drop) for a in np.linspace(0, 2 * math.pi, 21)]
    tube(X.mesh(M_['brass']), path, [4] * 21, nseg=6, caps=(False, False))
    ML.save(name, X)


def sconce(name='sconce'):
    """twin-arm brass wall light with frosted tulip shades (back y 0)"""
    X = ML.Model()
    Y = ML.Model(); lathe(Y, 'brass', [(30, 0), (26, 8), (0, 12)], n=12, cap=False)
    X.add_model(Y, R=R_XZ, t=(0, 0, 0))
    for sx in (-1, 1):
        p = [(0, -10, 0), (sx * 30, -50, -20), (sx * 70, -60, 0), (sx * 80, -60, 30)]
        tube(X.mesh(M_['brass']), p, [4, 4, 4, 5], nseg=6)
        c = (sx * 80, -60)
        revolve(X.mesh(M_['glow_shade']), [(8, 30), (16, 44), (28, 80), (30, 96)], n=10, cx=c[0], cy=c[1])
        revolve(X.mesh(M_['glow_shade']), [(30, 96), (28, 80), (16, 44), (8, 30)], n=10, cx=c[0], cy=c[1], inward=True)
    ML.save(name, X)


def frame(name, w, h, mat='gold'):
    """picture frame moulding round a w x h opening (wall mounted, back y 0; the picture is a brush sign behind it)"""
    X = ML.Model()
    t = 18
    for (mn, mx) in (((-w / 2 - t, -14, -h / 2 - t), (w / 2 + t, 0, -h / 2)), ((-w / 2 - t, -14, h / 2), (w / 2 + t, 0, h / 2 + t)),
                     ((-w / 2 - t, -14, -h / 2), (-w / 2, 0, h / 2)), ((w / 2, -14, -h / 2), (w / 2 + t, 0, h / 2))):
        bx(X, mat, mn, mx, r=4, k=2)
    ML.save(name, X)


def window_frame(name='window_frame', W=WIN_W, H=940):
    """sash-style shop window frame: mahogany mullions and transom (the glass is brushes), front and back the same"""
    X = ML.Model()
    t = 14
    for x in (-W / 2, -W / 6, W / 6, W / 2):
        bx(X, 'mahog', (x - 12, -t, 0), (x + 12, t, H), r=3)
    for z in (0, 560, H):
        bx(X, 'mahog', (-W / 2 - 12, -t, z - 12), (W / 2 + 12, t, z + 12), r=3)
    for x in (-W / 3, 0, W / 3):
        bx(X, 'mahog', (x - 6, -t + 4, 560), (x + 6, t - 4, H), r=2)
    ML.save(name, X)


def door_leaf(name='door_leaf', W=200, H=880, mat='panel_door'):
    """a half-glazed pub door leaf (hinge at x 0, closed it runs to x W; build open by rotating at placement)"""
    X = ML.Model()
    bx(X, mat, (0, -20, 0), (W, 20, H * 0.5), r=3, tile=256)
    for (mn, mx) in (((0, -20, H * 0.5), (30, 20, H)), ((W - 30, -20, H * 0.5), (W, 20, H)), ((0, -20, H - 40), (W, 20, H))):
        bx(X, 'mahog', mn, mx, r=3)
    X.mesh(M_['glass']).quad((30, 0, H * 0.5), (W - 30, 0, H * 0.5), (W - 30, 0, H - 40), (30, 0, H - 40), n=(0, -1, 0))
    tube(X.mesh(M_['brass']), [(W - 50, -20, H * 0.45), (W - 50, -60, H * 0.45), (W - 50, -60, H * 0.6), (W - 50, -20, H * 0.6)], [5] * 4, nseg=6)
    ML.save(name, X)


def facade_pilaster(name='pilaster', H=1260):
    """carved pilaster for the pub front with a scroll console bracket at the fascia"""
    X = ML.Model()
    bx(X, 'green_paint', (-40, -30, 0), (40, 0, 300), r=4, k=2)
    bx(X, 'green_paint', (-30, -24, 300), (30, 0, H - 180), r=3)
    for k in range(3):
        bx(X, 'green_paint', (-20 + k * 16, -28, 340), (-14 + k * 16, -24, H - 220), r=2, faces='s')
    Y = ML.Model()
    cons = [(-40, 0), (40, 0), (40, 180), (20, 160), (24, 120), (-24, 120), (-20, 160), (-40, 180)]
    prism(Y.mesh(M_['green_paint']), cons, 0, 60, tile=128)
    X.add_model(Y, R=R_XZ, t=(0, 0, H - 180))
    bx(X, 'gold', (-42, -62, H - 6), (42, 0, H), r=2)
    ML.save(name, X)


# ================================================================================================= outside + garden
def phone_box(name='phone_box'):
    """red telephone kiosk you can walk into (door side -y, open door swung out), domed roof with a crown and a flat
    walkable top, illuminated TELEPHONE panels, small glazing bars, a phone inside"""
    X = ML.Model()
    S, H = PHONE
    s = S / 2
    door = PHONE_DOOR / 2
    bx(X, 'phone_red', (-s - 10, -s - 10, 0), (s + 10, s + 10, 16), r=4)                     # plinth (a 16u step)
    bx(X, 'black', (-s + 30, -s + 30, 16), (s - 30, s - 30, 17), r=0.5, faces='t')
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(X, 'phone_red', (sx * s - 30, sy * s - 30, 16), (sx * s + 30, sy * s + 30, H - 200), r=6, k=2)   # corner posts
    for side, (ax, sg) in (('n', (1, 1)), ('e', (0, 1)), ('w', (0, -1)), ('s', (1, -1))):
        for k in range(8):                                                         # horizontal glazing bars
            z = 120 + k * 100
            if ax == 1:
                if side == 's': continue
                bx(X, 'phone_red', (-s + 30, sg * s - 8, z), (s - 30, sg * s + 8, z + 12), r=1)
            else:
                bx(X, 'phone_red', (sg * s - 8, -s + 30, z), (sg * s + 8, s - 30, z + 12), r=1)
        if side != 's':
            for f in (-1 / 6, 1 / 6):
                if ax == 1: bx(X, 'phone_red', (f * S * 1.2 - 6, sg * s - 8, 120), (f * S * 1.2 + 6, sg * s + 8, H - 260), r=1)
                else: bx(X, 'phone_red', (sg * s - 8, f * S * 1.2 - 6, 120), (sg * s + 8, f * S * 1.2 + 6, H - 260), r=1)
            G = X.mesh(M_['glass'])
            if ax == 1: G.quad((-s + 30, sg * s, 60), (s - 30, sg * s, 60), (s - 30, sg * s, H - 260), (-s + 30, sg * s, H - 260), n=(0, sg, 0))
            else: G.quad((sg * s, -s + 30, 60), (sg * s, s - 30, 60), (sg * s, s - 30, H - 260), (sg * s, -s + 30, H - 260), n=(sg, 0, 0))
            if ax == 1: bx(X, 'phone_red', (-s + 30, sg * s - 10, 30), (s - 30, sg * s + 10, 60), r=1)
            else: bx(X, 'phone_red', (sg * s - 10, -s + 30, 30), (sg * s + 10, s - 30, 60), r=1)
    # header with TELEPHONE signs on all four sides
    bx(X, 'phone_red', (-s - 10, -s - 10, H - 260), (s + 10, s + 10, H - 140), r=6, k=2)
    for (c, n_) in (((0, -s - 11, H - 200), (0, -1, 0)), ((0, s + 11, H - 200), (0, 1, 0)), ((s + 11, 0, H - 200), (1, 0, 0)), ((-s - 11, 0, H - 200), (-1, 0, 0))):
        pic(X.mesh(M_['phone_sign']), c, n_, S - 120, 60)
    # domed roof: shallow vault on each side up to a flat top square (walkable) + small crown ornaments on the sides
    rp = [(s + 10, H - 140), (s + 20, H - 130), (s + 10, H - 110), (s - 20, H - 60), (s - 60, H - 20), (s - 80, H)]
    for k in range(4):
        R = rot_z(k * math.pi / 2)
        Y = ML.Model(); Ym = Y.mesh(M_['phone_red'])
        for i in range(len(rp) - 1):
            (r0, z0), (r1, z1) = rp[i], rp[i + 1]
            q = [(r0, -r0, z0), (r0, r0, z0), (r1, r1, z1), (r1, -r1, z1)]
            n_ = np.cross(np.subtract(q[1], q[0]), np.subtract(q[3], q[0])); n_ /= np.linalg.norm(n_)
            if n_[0] < 0: n_ = -n_
            Ym.poly(q, n_, [(0, 0), (1, 0), (1, 1), (0, 1)])
        X.add_model(Y, R=R)
    r = s - 80
    X.mesh(M_['phone_red']).poly([(-r, -r, H), (r, -r, H), (r, r, H), (-r, r, H)], (0, 0, 1), [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in range(4):
        a = k * math.pi / 2
        c = (math.cos(a) * (s - 20), math.sin(a) * (s - 20), H - 70)
        sphere(X.mesh(M_['gold']), c, 14, nu=8, nv=5)
    # open door: glazed red door swung out ~110 degrees on the west hinge
    hx, hy = -door, -s
    a = math.radians(-100)
    dw = PHONE_DOOR
    ex, ey = hx + dw * math.cos(math.radians(-110)), hy + dw * math.sin(math.radians(-110))
    d = np.array([ex - hx, ey - hy, 0]) / dw
    nrm = np.array([-d[1], d[0], 0])
    Y = ML.Model()
    for k in range(8):
        z = 120 + k * 100
        p0 = np.array([hx, hy, z]); p1 = p0 + d * dw
        tube(Y.mesh(M_['phone_red']), [p0, p1], [6, 6], nseg=4)
    for t_ in (0, 0.5, 1):
        p = np.array([hx, hy, 0]) + d * (dw * t_ * 0.96 + 6)
        tube(Y.mesh(M_['phone_red']), [p + (0, 0, 40), p + (0, 0, H - 270)], [10, 10], nseg=6)
    Y.mesh(M_['glass']).poly([np.array([hx, hy, 60]), np.array([hx, hy, 60]) + d * dw, np.array([hx, hy, H - 270]) + d * dw, np.array([hx, hy, H - 270])],
                             nrm, [(0, 0), (1, 0), (1, 1), (0, 1)])
    X.add_model(Y)
    # phone inside on the back wall
    bx(X, 'iron', (-70, s - 70, 520), (70, s - 30, 720), r=8, k=2)
    tube(X.mesh(M_['iron']), [(-50, s - 76, 700), (-50, s - 90, 620), (50, s - 90, 620), (50, s - 76, 700)], [10, 10, 10, 10], nseg=6)
    bx(X, 'cream', (-90, s - 50, 380), (90, s - 30, 500), r=2)     # directory shelf
    ML.save(name, X)
    w = 30
    coll(name, [((-s - 10, -s - 10, 0), (s + 10, s + 10, 16)),                                  # plinth step
                ((-s - 10, -s - 10, 16), (-door, -s + 30, H - 140)), ((door, -s - 10, 16), (s + 10, -s + 30, H - 140)),
                ((-s - 10, s - 30, 16), (s + 10, s + 10, H - 140)),
                ((-s - 10, -s + 30, 16), (-s + 30, s - 30, H - 140)), ((s - 30, -s + 30, 16), (s + 10, s - 30, H - 140)),
                ((-door, -s - 10, H - 260), (door, -s + 30, H - 140)),
                ((-s - 10, -s - 10, H - 140), (s + 10, s + 10, H))])


def pillar_box(name='pillar_box'):
    X = ML.Model()
    lathe(X, 'iron', [(80, 0), (80, 40), (70, 50)], n=20, cap=False)
    lathe(X, 'pillar_red', [(70, 50), (70, 560), (80, 580), (84, 600), (60, 640), (30, 660), (0, 664)], n=24, cap=False)
    bx(X, 'iron', (-50, -76, 480), (50, -66, 494), r=2)
    pic(X.mesh(M_['cream']), (0, -71, 400), (0, -1, 0), 70, 50)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 76, 0, 664)])


def street_lamp(name='street_lamp', H=1400):
    """Victorian cast-iron lamp post with a square lantern"""
    X = ML.Model()
    lathe(X, 'iron', [(50, 0), (50, 60), (34, 90), (30, 200), (20, 240), (16, H - 220), (24, H - 200), (24, H - 190)], n=12)
    tube(X.mesh(M_['iron']), [(-70, 0, H - 260), (70, 0, H - 260)], [5, 5], nseg=6)
    Y = ML.Model()
    revolve(Y.mesh(M_['iron']), [(24, 0), (40, 10), (40, 20)], n=4, a0=45, a1=405)
    revolve(Y.mesh(M_['lampglass']), [(40, 20), (64, 160)], n=4, a0=45, a1=405)
    revolve(Y.mesh(M_['iron']), [(70, 160), (70, 176), (30, 230), (6, 260), (0, 262)], n=4, a0=45, a1=405)
    X.add_model(Y, t=(0, 0, H - 190))
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 30, 0, H - 200)])


def hanging_sign(name='pub_sign_board'):
    """the swinging sign board (origin at the pivot on the bracket, hanging down)"""
    X = ML.Model()
    for sx in (-1, 1):
        tube(X.mesh(M_['iron']), [(sx * 100, 0, 0), (sx * 100, 0, -30)], [3, 3], nseg=4)
    bx(X, 'mahog_dark', (-130, -12, -360), (130, 12, -30), r=4, k=2, faces='tbew')
    pic(X.mesh(M_['sign']), (0, -13, -195), (0, -1, 0), 250, 320)
    pic(X.mesh(M_['sign']), (0, 13, -195), (0, 1, 0), 250, 320)
    ML.save(name, X)


def sign_bracket(name='sign_bracket', L=380):
    """wrought-iron bracket from the facade (back y 0, reaching out -y) with a scroll"""
    X = ML.Model()
    tube(X.mesh(M_['iron']), [(0, 0, 0), (0, -L, 0)], [8, 8], nseg=8)
    tube(X.mesh(M_['iron']), [(0, 0, -200), (0, -L * 0.6, -20), (0, -L * 0.8, 0)], [5, 5, 5], nseg=6)
    path = [(0, -L * 0.35 + 50 * math.cos(a), -110 + 50 * math.sin(a)) for a in np.linspace(0, 1.8 * math.pi, 18)]
    tube(X.mesh(M_['iron']), path, [3] * 18, nseg=5)
    bx(X, 'iron', (-40, -10, -230), (40, 0, 30), r=3)
    sphere(X.mesh(M_['gold']), (0, -L - 10, 0), 14, nu=8, nv=5)
    ML.save(name, X)


def a_board(name='a_board'):
    X = ML.Model()
    H, W = 500, 280
    for sg in (-1, 1):
        q = [(-W / 2, sg * 110, 0), (W / 2, sg * 110, 0), (W / 2, sg * 8, H), (-W / 2, sg * 8, H)]
        n_ = np.array([0, sg * 1.0, 0.22]); n_ /= np.linalg.norm(n_)
        X.mesh(M_['aboard']).poly(q if sg < 0 else q, n_, [(0, 1), (1, 1), (1, 0), (0, 0)] if sg < 0 else [(1, 1), (0, 1), (0, 0), (1, 0)])
        for x in (-W / 2, W / 2):
            tube(X.mesh(M_['oak']), [(x, sg * 114, 0), (x, sg * 10, H)], [8, 8], nseg=5)
        tube(X.mesh(M_['oak']), [(-W / 2, sg * 12, H - 4), (W / 2, sg * 12, H - 4)], [8, 8], nseg=5)
    ML.save(name, X)
    coll(name, [((-W / 2, -100, 0), (W / 2, 100, H))])


def picnic_table(name='picnic_table'):
    """beer-garden picnic table with attached benches (top PICNIC_Z, benches 220)"""
    X = ML.Model()
    L, W = 700, 280
    for k in range(4):
        y = -W / 2 + k * W / 4
        bx(X, 'weathered', (-L / 2, y + 4, PICNIC_Z - 26), (L / 2, y + W / 4 - 4, PICNIC_Z), r=4, tile=256)
    for sy in (-1, 1):
        for k in range(2):
            y0 = sy * (W / 2 + 80) + (k - 1) * 60 + (60 if sy < 0 else 0)
            bx(X, 'weathered', (-L / 2 - 30, y0 + 4, 194), (L / 2 + 30, y0 + 56, 220), r=4, tile=256)
    for sx in (-1, 1):
        x = sx * (L / 2 - 80)
        for sg in (-1, 1):
            p0 = (x, sg * (W / 2 + 140), 0); p1 = (x, sg * 20, PICNIC_Z - 26)
            tube(X.mesh(M_['weathered']), [p0, p1], [14, 14], nseg=4)
        bx(X, 'weathered', (x - 14, -(W / 2 + 150), 170), (x + 14, W / 2 + 150, 194), r=2)
    pint(X, -200, -40, PICNIC_Z, 0.7); pint(X, 160, 60, PICNIC_Z, 0.4)
    ML.save(name, X)
    coll(name, [((-L / 2, -W / 2, PICNIC_Z - 26), (L / 2, W / 2, PICNIC_Z)),
                ((-L / 2 - 30, W / 2 + 24, 194), (L / 2 + 30, W / 2 + 136, 220)),
                ((-L / 2 - 30, -W / 2 - 136, 194), (L / 2 + 30, -W / 2 - 24, 220))])


def parasol(name='parasol', R=420, H=1000):
    X = ML.Model()
    tube(X.mesh(M_['white']), [(0, 0, 0), (0, 0, H + 40)], [7, 7], nseg=6)
    n = 8
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = [(0, 0, H + 40), (R * math.cos(a0), R * math.sin(a0), H - 100), (R * math.cos(a1), R * math.sin(a1), H - 100)]
        n_ = np.cross(np.subtract(p[1], p[0]), np.subtract(p[2], p[0])); n_ /= np.linalg.norm(n_)
        if n_[2] < 0: n_ = -n_
        X.mesh(M_['parasol']).poly(p, n_, [(0.5 + 0.0, 0), (k % 2, 1), ((k + 1) % 2, 1)])
        tube(X.mesh(M_['white']), [(0, 0, H - 20), (R * 0.96 * math.cos(a0), R * 0.96 * math.sin(a0), H - 96)], [2, 2], nseg=4)
    ML.save(name, X)


def barrel(name='barrel', H=420, R=150, standing=True):
    """oak barrel with iron hoops (stood on end; a pint on top when standing)"""
    X = ML.Model()
    prof = [(R * (0.84 + 0.16 * math.sin(math.pi * t)), H * t) for t in np.linspace(0, 1, 9)]
    lathe(X, 'oak', prof, n=20, u=4)
    for t in (0.1, 0.3, 0.7, 0.9):
        rr = R * (0.84 + 0.16 * math.sin(math.pi * t)) + 2
        revolve(X.mesh(M_['iron']), [(rr, H * t - 8), (rr, H * t + 8)], n=20)
    disc(X.mesh(M_['oak']), prof[0][0], 0, up=False, n=20)
    if standing:
        pint(X, 40, 30, H, 0.6)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, R * 0.86, 0, H)])


def keg(name='keg'):
    X = ML.Model()
    lathe(X, 'keg', [(110, 0), (120, 20), (120, 130), (114, 150), (120, 170), (120, 280), (110, 300), (40, 300)], n=16)
    lathe(X, 'chrome', [(30, 300), (30, 330), (0, 330)], n=10)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 112, 0, 300)])


def crate(name='crate'):
    X = ML.Model()
    bx(X, 'oak', (-120, -80, 0), (120, 80, 160), r=3, tile=160)
    for x in (-110, 110):
        bx(X, 'mahog_dark', (x - 8, -82, 0), (x + 8, 82, 160), r=2)
    for k in range(6):
        bottle_mesh(X, f'bottle{5 + k % 2}', -80 + k * 32, 0, 100, kind=2, s=1.0)
    ML.save(name, X)
    coll(name, [((-120, -80, 0), (120, 80, 160))])


def planter(name='planter', L=600, W=400, H=240):
    """raised brick planter for the beer-garden tree (wide coping you can stand on)"""
    X = ML.Model()
    Y = ML.Model()
    bx(X, 'cream', (-L / 2 - 20, -W / 2 - 20, H - 24), (L / 2 + 20, W / 2 + 20, H), r=4, tile=128, faces='nsewb')
    rbox(X.mesh(M_['soil']), (-L / 2 + 20, -W / 2 + 20, H - 30), (L / 2 - 20, W / 2 - 20, H - 20), r=1, k=1, faces='t')
    for (mn, mx) in (((-L / 2 - 20, -W / 2 - 20, H - 24), (L / 2 + 20, -W / 2 + 20, H)), ((-L / 2 - 20, W / 2 - 20, H - 24), (L / 2 + 20, W / 2 + 20, H)),
                     ((-L / 2 - 20, -W / 2 + 20, H - 24), (-L / 2 + 20, W / 2 - 20, H)), ((L / 2 - 20, -W / 2 + 20, H - 24), (L / 2 + 20, W / 2 - 20, H))):
        bx(X, 'cream', mn, mx, r=3, faces='t')
    bricks = TL.bricks((150, 70, 52), (190, 180, 166), rows=4, cols=4)
    if 'planter_brick' not in M_: m('planter_brick', bricks, shade=30)
    bx(X, 'planter_brick', (-L / 2, -W / 2, 0), (L / 2, W / 2, H - 24), r=1, tile=128, faces='nsew')
    ML.save(name, X)
    coll(name, [((-L / 2 - 20, -W / 2 - 20, 0), (L / 2 + 20, W / 2 + 20, H))])


def hanging_basket(name='basket'):
    """a hanging flower basket on its chains (origin at the hook, hanging down)"""
    X = ML.Model()
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(X.mesh(M_['iron']), [(0, 0, 0), (60 * math.cos(a), 60 * math.sin(a), -160)], [1.5, 1.5], nseg=4)
    lathe(X, 'rope', [(0, -260), (40, -250), (62, -200), (66, -160)], n=12)
    ellipsoid(X.mesh(M_['leaf']), (0, 0, -170), 80, 80, 40, nu=12, nv=6)
    flowers(X, 0, 0, -190, 'petal_pink', n=10, R=60, seed=7, H=50)
    flowers(X, 0, 0, -190, 'petal_red', n=6, R=60, seed=8, H=40)
    for k in range(8):
        a = 2 * math.pi * k / 8
        tube(X.mesh(M_['leaf']), [(60 * math.cos(a), 60 * math.sin(a), -180), (80 * math.cos(a), 80 * math.sin(a), -260)], [5, 2], nseg=4)
    ML.save(name, X)


def window_box(name='window_box', L=800):
    X = ML.Model()
    bx(X, 'green_paint', (-L / 2, -110, 0), (L / 2, 0, 90), r=3)
    rng = np.random.default_rng(2)
    for k in range(10):
        x = -L / 2 + 50 + k * (L - 100) / 9
        flowers(X, x, -55, 80, ['petal_red', 'petal_white', 'petal_yellow', 'petal_pink'][k % 4], n=4, R=26, seed=k, H=60)
    ML.save(name, X)


def coat_stand(name='coat_stand'):
    X = ML.Model()
    lathe(X, 'mahog', [(16, 60), (14, 120), (10, 760), (16, 780), (0, 800)], n=10)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        tube(X.mesh(M_['mahog']), [(0, 0, 70), (90 * math.cos(a), 90 * math.sin(a), 0)], [8, 6], nseg=6)
        tube(X.mesh(M_['brass']), [(0, 0, 700), (40 * math.cos(a), 40 * math.sin(a), 740), (50 * math.cos(a), 50 * math.sin(a), 760)], [4, 3, 3], nseg=5)
    ellipsoid(X.mesh(M_['tapestry_red']), (40, 0, 560), 30, 50, 170, nu=10, nv=6)      # a coat
    ML.save(name, X)
    coll(name, cyls=[(0, 0, 30, 0, 780)])


def oche(name='oche', L=300):
    X = ML.Model()
    bx(X, 'brass', (-L / 2, -12, 0), (L / 2, 12, 6), r=2)
    ML.save(name, X)


def chalk_tex_reg():
    m('chalk', chalk_scores(), shade=30)


def umbrella_stand(name='umbrella_stand'):
    """Victorian umbrella stand: a brass-banded mahogany drum with two furled umbrellas and a walking cane"""
    X = ML.Model()
    R, H = 70, 300
    lathe(X, 'mahog', [(R - 4, 0), (R, 10), (R, H - 10), (R + 4, H - 4), (R + 4, H)], n=20, u=2, cap=False)
    revolve(X.mesh(M_['mahog_dark']), [(R + 4, H), (R - 6, H), (R - 6, H - 30)], n=20)            # rim, then into the drum
    disc(X.mesh(M_['soil']), R - 6, H - 30, up=True, n=20)                                         # dark inside
    for z in (40, H - 50):
        revolve(X.mesh(M_['brass']), [(R + 2, z - 8), (R + 2, z + 8)], n=20)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        sphere(X.mesh(M_['brass']), (R * math.cos(a), R * math.sin(a), 6), 8, nu=8, nv=4)
    # furled umbrellas leaning outward: canopy cone + ferrule tip + crook handle
    for (cx, cy, lean, mat, hcol) in ((-20, 10, (-0.18, 0.08), 'umbrella_black', 'mahog'),
                                      (22, -14, (0.16, -0.12), 'umbrella_red', 'mahog_dark')):
        base = np.array([cx, cy, H - 120.0]); d = np.array([lean[0], lean[1], 1.0]); d /= np.linalg.norm(d)
        top = base + d * 420
        tube(X.mesh(M_['chrome']), [base, base + d * 30], [3, 3], nseg=6)                           # ferrule
        tube(X.mesh(M_[mat]), [base + d * 30, base + d * 120, base + d * 300, base + d * 330], [6, 16, 14, 5], nseg=10)
        tube(X.mesh(M_['chrome']), [base + d * 330, top - d * 40], [3, 3], nseg=6)                  # shaft
        h0 = top - d * 40
        side = np.cross(d, [0, 0, 1.0]); side /= max(1e-6, np.linalg.norm(side))
        hook = [h0, h0 + d * 40, h0 + d * 60 + side * 20, h0 + d * 50 + side * 46, h0 + d * 22 + side * 50]
        tube(X.mesh(M_[hcol]), hook, [6, 6, 6, 6, 5], nseg=8)
    # walking cane with a brass knob
    base = np.array([0, 34, H - 120.0]); d = np.array([0.05, 0.2, 1.0]); d /= np.linalg.norm(d)
    tube(X.mesh(M_['mahog_dark']), [base, base + d * 430], [5, 6], nseg=8)
    sphere(X.mesh(M_['brass']), base + d * 438, 11, nu=8, nv=5)
    ML.save(name, X)
    coll(name, cyls=[(0, 0, R, 0, H)])


# ================================================================================================= cellar
def barrel_rack(name='barrel_rack', n=3):
    """three barrels on their sides on a timber cradle (cellar)"""
    X = ML.Model()
    R, L = 140, 360
    for k in range(n):
        x = -(n - 1) * 160 + k * 320
        Y = ML.Model()
        prof = [(R * (0.84 + 0.16 * math.sin(math.pi * t)), L * t - L / 2) for t in np.linspace(0, 1, 9)]
        revolve(Y.mesh(M_['oak']), prof, u_tiles=4, n=18)
        for t in (0.12, 0.88):
            rr = R * (0.84 + 0.16 * math.sin(math.pi * t)) + 2
            revolve(Y.mesh(M_['iron']), [(rr, L * t - L / 2 - 8), (rr, L * t - L / 2 + 8)], n=18)
        disc(Y.mesh(M_['oak']), prof[-1][0], L / 2, up=True, n=18); disc(Y.mesh(M_['oak']), prof[0][0], -L / 2, up=False, n=18)
        X.add_model(Y, R=np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]]), t=(x, 0, R + 60))
        tube(X.mesh(M_['brass']), [(x, -L / 2, R * 0.6 + 60), (x, -L / 2 - 40, R * 0.6 + 60), (x, -L / 2 - 40, R * 0.6 + 30)], [6, 6, 5], nseg=6)
    for sy in (-1, 1):
        bx(X, 'mahog_dark', (-n * 160 - 20, sy * 120 - 20, 0), (n * 160 + 20, sy * 120 + 20, 70), r=3)
    ML.save(name, X)
    coll(name, [((-n * 160 - 20, -L / 2, 0), (n * 160 + 20, L / 2, 2 * R + 60))])


# ================================================================================================= build everything
def all_models():
    chalk_tex_reg()
    m('black', TL.solid((26, 24, 22), 2, 80, 64), shade=40)
    gantry_bay('gantry_a', 'cabinet', 'arch', seed=0)
    gantry_bay('gantry_b', 'fridge', 'arch2', seed=1)
    gantry_bay('gantry_c', 'cabinet', 'arch2', seed=2)
    gantry_end()
    counter_run('counter_run', 2000 / 3)
    counter_run('counter_return', 360)
    counter_corner()
    beer_pumps(); beer_pumps('beer_pumps3', 3)
    lager_font(); coffee_machine(); hurricane_vase(); till(); wine_display()
    counter_board('snacks_stand', 'snacks', 140, 180); counter_board('coffee_stand', 'coffee', 110, 150)
    flower_vase(); crisp_card(); glass_rack()
    stool('stool_red', 'velvet_red'); stool('stool_green', 'tapestry')
    pub_table('pub_table', 2); pub_table('pub_table1', 1); pub_table('pub_table0', 0)
    banquette('banquette', WIN_W); banquette('banquette_long', 700)
    settle(); booth_table()
    piano(); piano_stool(); fireplace(); longcase_clock(); pendulum()
    fruit_machine(); jukebox(); dartboard_cab(); oche()
    chandelier(); pendant(); sconce()
    frame('frame_print', 200, 150); frame('frame_mirror', 220, 330, 'mahog_dark'); frame('frame_scores', 200, 200, 'mahog')
    window_frame(); door_leaf(); door_leaf('door_leaf_snug', 260, 880)
    facade_pilaster()
    phone_box(); pillar_box(); street_lamp(); hanging_sign(); sign_bracket(); a_board()
    picnic_table(); parasol(); barrel(); barrel('barrel_plain', standing=False); keg(); crate(); planter()
    hanging_basket(); window_box(); coat_stand(); umbrella_stand()
    barrel_rack()
