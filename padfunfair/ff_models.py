"""Custom MD3s for wop_padfunfair (Padland Funfair). All art original and procedural.

Scale: 48u per metre (you are a kid-sized figure, as on padville's layout). Local frames: z 0 = the surface a model
stands on. Ride models (wheel rims, gondolas, carousel deck, ghost-train carts) use 'dyn' shaders: they are model2 on
movers and get no lightmap.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from woplib import models as ML, texlib as TL
from meshlib import Mesh, rbox, tube, revolve, disc, prism, ellipsoid, sphere

TX = None
COLL = {}


def setup(tx):
    global TX
    TX = tx


def C(c): return np.array(c, np.float32)
def _img(w, h, bg): return Image.new('RGB', (w, h), tuple(int(v) for v in bg))
def _arr(im): return np.asarray(im, np.float32)
def font(sz, serif=False): return ML.font(sz, serif)
RX90 = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)        # local +z -> -y (det +1)


# ================================================================================================ textures
def stripes_v(c1, c2, n=8, w=256, h=256):
    return TL.stripes(c1, c2, n, True, 0.05, 11, w)


def sign_tex(text, bg, fg, w=1024, h=256, bulbs=True):
    im = _img(w, h, bg); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w - 8, h - 8), 30, outline=fg, width=10)
    if bulbs:
        for k in range(28):
            x = 30 + k * (w - 60) / 27
            for y in (24, h - 24): d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 236, 160))
    d.text((w / 2, h / 2), text, font=font(int(h * 0.42), True), fill=fg, anchor='mm')
    return _arr(im)


def mats():
    M = TX.material
    # rides on movers (dyn)
    M('rim_red', TL.solid((210, 40, 40), 3, 1, 128), 'dyn')
    M('rim_white', TL.solid((236, 236, 230), 3, 2, 128), 'dyn')
    M('bulb_dyn', TL.solid((255, 236, 170), 2, 3, 64), 'glow')
    M('bulb_red', TL.solid((255, 90, 70), 2, 4, 64), 'glow', wave='sin 0.75 0.25 0 0.8')
    M('bulb_blue', TL.solid((90, 170, 255), 2, 5, 64), 'glow', wave='sin 0.75 0.25 0.5 0.8')
    M('gondola_body', gondola_tex(), 'dyn')
    M('gondola_roof', stripes_v((230, 60, 60), (250, 230, 120), 8), 'dyn', two=True)
    M('seat_dyn', TL.fabric((150, 30, 40), 32, 6), 'dyn')
    M('steel_dyn', TL.metal((170, 172, 178), True, 7), 'dyn')
    M('deck_boards', TL.planks((150, 104, 62), 10, (90, 60, 34), 8, False, False, 8), 'dyn')
    M('horse_white', TL.solid((240, 236, 226), 3, 9, 128), 'dyn')
    M('horse_saddle', TL.stripes((200, 40, 60), (240, 200, 60), 6, False, 0.1, 10), 'dyn')
    M('pole_gold', TL.metal((220, 180, 70), False, 11), 'dyn')
    M('cart_body', cart_tex(), 'dyn')
    M('cart_dark', TL.solid((40, 30, 50), 3, 12, 64), 'dyn')
    # static
    M('steel', TL.metal((180, 184, 190), True, 13), 'lms', shade=60, v=0.25)
    M('paint_red', TL.solid((200, 40, 40), 3, 14, 128), shade=40)
    M('paint_white', TL.solid((238, 236, 230), 3, 15, 128), shade=40)
    M('paint_blue', TL.solid((40, 80, 180), 3, 16, 128), shade=40)
    M('paint_yellow', TL.solid((240, 200, 50), 3, 17, 128), shade=40)
    M('paint_green', TL.solid((40, 140, 80), 3, 18, 128), shade=40)
    M('gold', TL.metal((220, 180, 70), False, 19), 'lms', shade=60, v=0.3)
    M('bulb', TL.solid((255, 236, 170), 2, 20, 64), 'glow')
    M('bulb_chase', TL.solid((255, 210, 120), 2, 21, 64), 'glow', wave='square 0.5 0.5 0 1.5')
    M('canvas_ry', stripes_v((210, 40, 40), (250, 236, 200), 12, 512, 512), shade=60, two=True)
    M('canvas_by', stripes_v((40, 80, 180), (250, 220, 90), 12, 512, 512), shade=60, two=True)
    M('canvas_gw', stripes_v((40, 140, 80), (240, 236, 226), 10, 512, 512), shade=60, two=True)
    M('valance', valance_tex(), 'alpha', alpha=valance_alpha())
    M('mirror', TL.metal((200, 210, 220), False, 22), 'lms', shade=60, v=0.5)
    M('helter', TL.stripes((230, 60, 60), (250, 236, 200), 2, False, 0.05, 23), lathe=True, shade=60)
    M('slide_red', TL.solid((220, 50, 40), 3, 24, 128), shade=60)
    M('slide_mat', TL.fabric((150, 110, 70), 24, 25), shade=60)
    M('bouncy', TL.stripes((240, 70, 70), (250, 220, 60), 6, True, 0.2, 26), shade=80)
    M('bouncy_blue', TL.solid((60, 120, 220), 4, 27, 128), shade=80)
    M('tramp_mat', TL.fabric((30, 30, 36), 64, 28), shade=40)
    M('sticker', TL.pad_sticker((255, 210, 40), (220, 40, 60), 'BOING!'), 'alpha', alpha=TL.disc_alpha())
    M('cannon', TL.stripes((40, 80, 180), (240, 200, 50), 8, False, 0.1, 29), lathe=True, shade=60)
    M('wood', TL.planks((150, 104, 62), 4, (90, 60, 34), 8, False, True, 30), shade=40)
    M('wood_dark', TL.planks((100, 66, 40), 4, (60, 40, 24), 8, False, True, 31), shade=40)
    M('rubber', TL.solid((30, 30, 32), 3, 32, 64), shade=60)
    M('dodgem_red', TL.solid((220, 40, 40), 2, 33, 64), 'lms', shade=70, v=0.25)
    M('dodgem_blue', TL.solid((40, 90, 220), 2, 34, 64), 'lms', shade=70, v=0.25)
    M('dodgem_yellow', TL.solid((240, 200, 40), 2, 35, 64), 'lms', shade=70, v=0.25)
    M('coffin', TL.planks((60, 40, 30), 2, (30, 20, 14), 8, False, True, 36), shade=40)
    M('coffin_in', TL.fabric((120, 20, 30), 32, 37), shade=40)
    M('bone', TL.solid((232, 226, 206), 3, 38, 64), shade=60)
    M('ghost', TL.solid((220, 240, 255), 2, 39, 64), 'add', wave='sin 0.6 0.3 0 0.3', two=True)
    M('eyes', TL.solid((255, 60, 30), 2, 40, 32), 'glow', wave='sin 0.7 0.3 0 1.2')
    M('candyfloss', TL.solid((250, 160, 210), 4, 41, 128), shade=80)
    M('coconut', TL.grime(TL.solid((110, 70, 40), 6, 42, 128), 0.3, 43), shade=80)
    M('crate', TL.planks((170, 128, 80), 4, (110, 80, 46), 8, False, False, 44), shade=30)
    M('caravan', caravan_tex(), shade=30)
    M('chrome', TL.metal((210, 214, 220), False, 45), 'lms', shade=60, v=0.45)
    M('window_glow', TL.solid((255, 220, 150), 2, 46, 64), 'glow')
    M('van', van_tex(), shade=30)
    M('fence', fence_tex(), 'alpha', alpha=fence_alpha())
    M('striker', striker_tex(), shade=30)
    M('crystal', TL.solid((160, 120, 255), 2, 47, 64), 'glow', wave='sin 0.7 0.3 0 0.4')
    M('cashbox', TL.metal((60, 110, 70), False, 48), shade=40)


def gondola_tex(w=512, h=256):
    im = _img(w, h, (230, 60, 60)); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.7, w, h), fill=(250, 230, 120))
    for k in range(4): d.ellipse((40 + k * 120, 40, 120 + k * 120, 120), fill=(255, 240, 200), outline=(180, 30, 30), width=6)
    return _arr(im)


def cart_tex(w=512, h=256):
    im = _img(w, h, (50, 30, 70)); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), 'BOO!', font=font(120, True), fill=(120, 255, 120), anchor='mm')
    for k in range(10): d.ellipse((20 + k * 50, h - 40, 40 + k * 50, h - 20), fill=(255, 220, 90))
    return _arr(im)


def valance_tex(w=512, h=128):
    a = TL.stripes((210, 40, 40), (250, 236, 200), 16, True, 0.0, 49, w)[:h]
    return np.ascontiguousarray(a)


def valance_alpha(w=512, h=128):
    x = np.arange(w)[None, :]; y = np.arange(h)[:, None]
    edge = h * (0.62 + 0.3 * np.abs(np.sin(x / w * math.pi * 16)))
    return np.where(y < edge, 255, 0).astype(np.uint8) * np.ones((h, w), np.uint8)


def caravan_tex(w=1024, h=512):
    im = _img(w, h, (240, 232, 214)); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.55, w, h * 0.62), fill=(40, 120, 90))
    d.rectangle((0, h * 0.9, w, h), fill=(40, 120, 90))
    for x0 in (120, 620):
        d.rounded_rectangle((x0, 90, x0 + 260, 230), 30, fill=(255, 220, 150), outline=(150, 110, 60), width=10)
        d.line((x0 + 130, 90, x0 + 130, 230), fill=(150, 110, 60), width=6)
    return _arr(im)


def van_tex(w=1024, h=512):
    im = _img(w, h, (250, 250, 246)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 80), fill=(220, 40, 40))
    d.text((w / 2, 40), "PADDY'S BURGERS", font=font(52, True), fill=(255, 240, 200), anchor='mm')
    for k in range(10): d.rectangle((k * 110, 380, k * 110 + 55, 420), fill=(220, 40, 40))
    d.rectangle((260, 120, 760, 330), fill=(60, 50, 40)); d.rectangle((270, 130, 750, 320), fill=(255, 210, 140))
    return _arr(im)


def fence_tex(n=256):
    a = np.zeros((n, n, 3), np.float32) + C((60, 64, 70))
    return a


def fence_alpha(n=256):
    x, y = np.mgrid[0:n, 0:n]
    bars = (y % 32 < 6) | (x < 10) | (x > n - 10) | (x % 64 < 4)
    return np.where(bars, 255, 0).astype(np.uint8)


def striker_tex(w=128, h=1024):
    im = _img(w, h, (240, 236, 226)); d = ImageDraw.Draw(im)
    labels = ['WIMP', 'WEAKLING', 'NOT BAD', 'STRONG', 'MIGHTY', 'HERO', 'PADMAN!']
    for k, t in enumerate(labels):
        y = h - 60 - k * 140
        d.rectangle((10, y - 50, w - 10, y + 50), fill=[(80, 160, 80), (140, 180, 60), (200, 200, 50), (230, 150, 40),
                                                         (230, 90, 40), (220, 40, 40), (160, 40, 200)][k])
        d.text((w / 2, y), t, font=font(18), fill=(255, 255, 255), anchor='mm')
    return _arr(im)


# ================================================================================================ big wheel
def wheel_rims(R=700.0, gap=105.0, n_spokes=16):
    """the turning part (model2 on a func_rotating round local y): twin rims, spokes, inner ring, bulbs.
    Origin at the hub, wheel in the x-z plane."""
    X = ML.Model()
    for y in (-gap, gap):
        ring = [(R * math.cos(t), y, R * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 65)]
        tube(X.mesh(TX['rim_red']), ring, 12, nseg=8, caps=(False, False))
        ring2 = [(R * 0.55 * math.cos(t), y, R * 0.55 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 49)]
        tube(X.mesh(TX['rim_white']), ring2, 8, nseg=6, caps=(False, False))
        for k in range(n_spokes):
            a = 2 * math.pi * k / n_spokes
            tube(X.mesh(TX['rim_white']), [(0, y * 0.4, 0), (R * math.cos(a), y, R * math.sin(a))], 6, nseg=6)
        for k in range(48):                                                     # bulbs along the rim
            a = 2 * math.pi * k / 48
            sphere(X.mesh(TX['bulb_red' if k % 2 else 'bulb_blue']), (R * math.cos(a), y * 1.12, R * math.sin(a)), 9, nu=6, nv=4)
    for k in range(8):                                                          # gondola pin cross-bars
        a = 2 * math.pi * k / 8
        tube(X.mesh(TX['steel_dyn']), [(R * math.cos(a), -gap, R * math.sin(a)), (R * math.cos(a), gap, R * math.sin(a))], 7, nseg=6)
    ML.save_iqm('wheel_rims', X)           # model2 can't be scaled and the rims reach past MD3's +-512: IQM floats
    return X


def wheel_frame(hz=900.0, foot_x=520.0, foot_y=290.0, top_y=165.0, deck_r=120.0):
    """the static A-frame: four legs from the ground up to the axle, cross braces, axle, hub drum and the little round
    deck on top of the hub (Imperius). Origin = ground under the hub."""
    X = ML.Model()
    st = TX['steel']
    for sy in (-1, 1):
        for sx in (-1, 1):
            tube(X.mesh(TX['paint_white']), [(sx * foot_x, sy * foot_y, 0), (0, sy * top_y, hz)], 22, nseg=10)
        for z in (300, 600):
            f = z / hz; xx = foot_x * (1 - f); yy = foot_y + (top_y - foot_y) * f
            tube(X.mesh(st), [(-xx, sy * yy, z), (xx, sy * yy, z)], 9, nseg=6)
        for s in (-1, 1):
            rbox(X.mesh(TX['paint_white']), (s * foot_x - 50, sy * foot_y - 50, 0), (s * foot_x + 50, sy * foot_y + 50, 24), r=3, k=1, tile=64)
    tube(X.mesh(st), [(0, -top_y - 20, hz), (0, top_y + 20, hz)], 34, nseg=14)                        # axle
    revolve(X.mesh(TX['paint_red']), [(deck_r - 50, hz - 40), (deck_r, hz), (deck_r, hz + 16), (0, hz + 16)], n=24)
    revolve(X.mesh(TX['bulb_chase']), [(deck_r + 1, hz + 2), (deck_r + 1, hz + 12)], n=24)
    ML.save('wheel_frame', X)
    COLL['wheel_frame'] = dict(cyls=[(0, 0, deck_r - 6, hz, hz + 16)])
    return X


def gondola(hl=80.0, hd=90.0, drop=150.0):
    """hangs below its pin (origin): floor top at -drop, low walls, bench seats, hanger bars, a striped canopy roof"""
    X = ML.Model()
    ft = -drop
    rbox(X.mesh(TX['gondola_body']), (-hl, -hd, ft - 12), (hl, hd, ft), r=4, k=1, tile=256)
    for (x0, y0, x1, y1) in ((-hl, -hd, -hl + 6, hd), (hl - 6, -hd, hl, hd), (-hl + 6, hd - 6, hl - 6, hd)):
        rbox(X.mesh(TX['gondola_body']), (x0, y0, ft), (x1, y1, ft + 36), r=2, k=1, tile=256)
    for x in (-hl + 16, hl - 16):
        rbox(X.mesh(TX['seat_dyn']), (x - 12, -hd + 20, ft), (x + 12, hd - 20, ft + 20), r=3, k=1, tile=64)
    for x in (-hl + 4, hl - 4):
        for y in (-hd + 4, hd - 4):
            tube(X.mesh(TX['steel_dyn']), [(x, y, ft + 36), (x * 0.3, y * 0.3, -10)], 3, nseg=5)
    revolve(X.mesh(TX['gondola_roof']), [(hd + 20, -40), (30, -6), (0, 0)], n=12, u_tiles=4)
    tube(X.mesh(TX['steel_dyn']), [(0, 0, -6), (0, 0, 8)], 8, nseg=6)
    ML.save('gondola', X)
    return X


# ================================================================================================ carousel
def horse():
    M = ML.Model()
    w, s = TX['horse_white'], TX['horse_saddle']
    ellipsoid(M.mesh(w), (0, 0, 0), 46, 15, 18, nu=12, nv=8)
    ellipsoid(M.mesh(w), (44, 0, 20), 14, 10, 22, nu=8, nv=6)
    ellipsoid(M.mesh(w), (60, 0, 34), 18, 8, 9, nu=8, nv=6)
    for (x, y) in ((-28, -8), (-28, 8), (30, -8), (30, 8)):
        tube(M.mesh(w), [(x, y, -8), (x + (8 if x > 0 else -8), y, -46)], 4, nseg=5)
    ellipsoid(M.mesh(s), (-4, 0, 14), 20, 16, 6, nu=10, nv=4)
    tube(M.mesh(s), [(-44, 0, 6), (-60, 0, -10), (-62, 0, -26)], 5, nseg=5)
    return M


def carousel_deck(r_in=110.0, r_out=420.0, n_horses=12, pole_top=330.0):
    """the turning deck (model2): boards, gold poles with horses at alternating heights, an inner rounding board.
    Origin at the deck centre, z 0 = deck top."""
    X = ML.Model()
    disc(X.mesh(TX['deck_boards']), r_out, 0, up=True, n=32, r_in=r_in, uvscale=256)
    revolve(X.mesh(TX['rim_red']), [(r_out, -16), (r_out, 0)], n=32, u_tiles=16)
    H = horse()
    for k in range(n_horses):
        a = 2 * math.pi * k / n_horses
        for (rr, dz) in ((r_out - 70, 120 if k % 2 else 150), (r_out - 210, 150 if k % 2 else 120)):
            x, y = rr * math.cos(a), rr * math.sin(a)
            tube(X.mesh(TX['pole_gold']), [(x, y, 0), (x, y, pole_top)], 4, nseg=6)
            c, s_ = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
            Rm = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
            X.add_model(H, Rm, (x, y, dz))
    ML.save('carousel_deck', X)
    return X


def carousel_top(r_col=96.0, h_col=420.0, r_can=480.0, z_can=420.0, z_peak=640.0, crown_r=90.0):
    """static centre: mirrored column, the striped canopy cone, scalloped valance with bulbs, crown deck on top"""
    X = ML.Model()
    revolve(X.mesh(TX['mirror']), [(r_col, 16), (r_col, h_col)], n=16, u_tiles=8)
    revolve(X.mesh(TX['gold']), [(r_col + 10, h_col - 30), (r_col + 10, h_col), (r_col, h_col)], n=16)
    revolve(X.mesh(TX['canvas_ry']), [(r_can, z_can), (crown_r, z_peak)], n=32, u_tiles=16)
    revolve(X.mesh(TX['canvas_ry']), [(crown_r, z_peak - 2), (r_can - 6, z_can - 2)], n=32, u_tiles=16)
    disc(X.mesh(TX['paint_red']), crown_r, z_peak, up=True, n=32)
    revolve(X.mesh(TX['bulb_chase']), [(crown_r + 2, z_peak - 10), (crown_r + 2, z_peak + 2)], n=32)
    ang = np.linspace(0, 2 * math.pi, 49)
    for k in range(48):                                                   # valance + bulbs round the rim
        a0, a1 = ang[k], ang[k + 1]
        q = [np.array([r_can * math.cos(a), r_can * math.sin(a), z]) for a, z in ((a0, z_can), (a1, z_can), (a1, z_can - 70), (a0, z_can - 70))]
        X.mesh(TX['valance']).poly(q, (math.cos(a0), math.sin(a0), 0), [(k / 8, 0), ((k + 1) / 8, 0), ((k + 1) / 8, 1), (k / 8, 1)])
        sphere(X.mesh(TX['bulb']), (r_can * 1.01 * math.cos(a0), r_can * 1.01 * math.sin(a0), z_can + 6), 8, nu=6, nv=4)
    ML.save('carousel_top', X)
    COLL['carousel_top'] = dict(cyls=[(0, 0, r_col - 6, 16, h_col), (0, 0, crown_r - 4, z_peak - 30, z_peak)])
    return X


# ================================================================================================ big top
def bigtop_shell(R=650.0, wall_h=300.0, peak=620.0, door_deg=(-105, -75), n=48):
    """circus tent: striped wall with an entrance gap (south), cone roof up to a crown, king pole, flags of bunting
    round the eaves. Origin at the centre. Collision is built by the caller from the same numbers."""
    X = ML.Model()
    holes = lambda a, z: door_deg[0] <= ((a + 180) % 360) - 180 <= door_deg[1] and z < 240
    ML.lathe(X.mesh(TX['canvas_ry']), [(R, 0), (R, wall_h)], n=n, u_tiles=24, holes=holes)
    ML.lathe(X.mesh(TX['canvas_ry']), [(R - 2, wall_h), (R - 2, 0)], n=n, u_tiles=24, holes=holes)
    crown = 70.0
    revolve(X.mesh(TX['canvas_ry']), [(R + 30, wall_h - 10), (crown, peak)], n=n, u_tiles=24)
    revolve(X.mesh(TX['canvas_ry']), [(crown, peak - 4), (R + 26, wall_h - 14)], n=n, u_tiles=24)
    disc(X.mesh(TX['paint_red']), crown, peak, up=True, n=24)
    revolve(X.mesh(TX['bulb_chase']), [(R + 31, wall_h - 18), (R + 31, wall_h - 6)], n=n)
    tube(X.mesh(TX['wood_dark']), [(0, 0, 0), (0, 0, peak - 2)], 16, nseg=10)
    ML.save('bigtop', X)
    return X


def trapeze_rig(h=360.0, w=160.0):
    """a trapeze platform on a pole with a rope ladder look and a swinging bar hanging nearby (static)"""
    X = ML.Model()
    tube(X.mesh(TX['steel']), [(0, 0, 0), (0, 0, h + 140)], 10, nseg=8)
    rbox(X.mesh(TX['wood']), (-w / 2, -w / 2, h - 14), (w / 2, w / 2, h), r=3, k=1, tile=128)
    for x in (-w / 2 + 6, w / 2 - 6):
        tube(X.mesh(TX['steel']), [(x, -w / 2 + 6, h), (x, -w / 2 + 6, h + 12)], 3, nseg=4)
    ML.save('trapeze', X)
    COLL['trapeze'] = dict(boxes=[((-w / 2 + 2, -w / 2 + 2, h - 14), (w / 2 - 2, w / 2 - 2, h))], cyls=[(0, 0, 10, 0, h - 14)])
    return X


def bleachers(steps=5, rise=32.0, tread=48.0, length=420.0):
    """tiered wooden seating (local: rising toward +y), for collision the caller adds stairs16-like boxes"""
    X = ML.Model()
    for i in range(steps):
        rbox(X.mesh(TX['wood']), (-length / 2, i * tread, 0), (length / 2, (i + 1) * tread, (i + 1) * rise), r=2, k=1, tile=128)
    ML.save('bleachers', X)
    return X


# ================================================================================================ helter-skelter
def helter_tower(r=170.0, h=880.0):
    X = ML.Model()
    holes = lambda a, z: -110 <= ((a + 180) % 360) - 180 <= -70 and z < 150
    ML.lathe(X.mesh(TX['helter']), [(r, 0), (r, h)], n=32, u_tiles=1, vlen=h, holes=holes)
    ML.lathe(X.mesh(TX['paint_white']), [(r - 16, h), (r - 16, 0)], n=32, u_tiles=4, holes=holes)
    disc(X.mesh(TX['paint_red']), r, h, up=True, n=32, r_in=r - 16)
    ML.save('helter_tower', X)
    return X


# ================================================================================================ dodgems
def dodgem_car(key='dodgem_red'):
    X = ML.Model()
    rbox(X.mesh(TX['rubber']), (-90, -60, 6), (90, 60, 34), r=14, k=3, tile=128)
    rbox(X.mesh(TX[key]), (-80, -52, 30), (80, 52, 70), r=16, k=3, tile=128)
    rbox(X.mesh(TX['rubber']), (-50, -36, 60), (10, 36, 100), r=8, k=2, tile=64)
    tube(X.mesh(TX['steel']), [(30, 0, 70), (40, 0, 100)], 3, nseg=6)
    revolve(X.mesh(TX['rubber']), [(20, 100), (20, 104), (0, 104)], n=12, cx=42)
    tube(X.mesh(TX['steel']), [(-70, 0, 70), (-70, 0, 300)], 3, nseg=6)
    sphere(X.mesh(TX['bulb']), (-70, 0, 300), 6, nu=6, nv=4)
    ML.save(f'dodgem_{key}', X)
    COLL[f'dodgem_{key}'] = dict(boxes=[((-88, -58, 0), (88, 58, 66))])
    return X


def pavilion(w=1000.0, d=700.0, h=320.0, post=16.0):
    """dodgem pavilion: posts, ceiling grid with sparks net, chase-bulb fascia (the roof slab is a brush)"""
    X = ML.Model()
    for x in np.linspace(-w / 2 + 20, w / 2 - 20, 5):
        for y in (-d / 2 + 20, d / 2 - 20):
            rbox(X.mesh(TX['paint_red']), (x - post, y - post, 0), (x + post, y + post, h - 16), r=3, k=1, tile=64)
    for x in np.linspace(-w / 2 + 50, w / 2 - 50, 10):
        tube(X.mesh(TX['steel']), [(x, -d / 2 + 30, h - 22), (x, d / 2 - 30, h - 22)], 2, nseg=4)
    ML.save('pavilion', X)
    return X


# ================================================================================================ themed jump pads (skins / dressing)
def bouncy_castle(w=320.0, d=320.0):
    """inflatable castle: puffy floor deck (16u, the pad trigger sits on it), corner turrets, a front opening at -y"""
    X = ML.Model()
    rbox(X.mesh(TX['bouncy_blue']), (-w / 2, -d / 2, 0), (w / 2, d / 2, 16), r=7, k=2, tile=128,
         inflate=lambda x, y, z, n: 2 * max(0, n[2]))
    for (x0, y0, x1, y1) in ((-w / 2, d / 2 - 40, w / 2, d / 2), (-w / 2, -d / 2, -w / 2 + 40, d / 2 - 40), (w / 2 - 40, -d / 2, w / 2, d / 2 - 40)):
        rbox(X.mesh(TX['bouncy']), (x0, y0, 16), (x1, y1, 110), r=16, k=3, tile=128)
    for (x, y) in ((-w / 2 + 30, d / 2 - 30), (w / 2 - 30, d / 2 - 30), (-w / 2 + 30, -d / 2 + 30), (w / 2 - 30, -d / 2 + 30)):
        revolve(X.mesh(TX['bouncy']), [(36, 0), (40, 150), (46, 160), (0, 210)], n=14, u_tiles=3, cx=x, cy=y)
    X.mesh(TX['sticker']).poly([np.array(p, float) for p in ((-40, -40, 17), (40, -40, 17), (40, 40, 17), (-40, 40, 17))], (0, 0, 1),
                               [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save('bouncy_castle', X)
    COLL['bouncy_castle'] = dict(boxes=[((-w / 2 + 2, -d / 2 + 2, 0), (w / 2 - 2, d / 2 - 2, 16)),
                                        ((-w / 2 + 4, d / 2 - 38, 16), (w / 2 - 4, d / 2 - 4, 100)),
                                        ((-w / 2 + 4, -d / 2 + 4, 16), (-w / 2 + 38, d / 2 - 40, 100)),
                                        ((w / 2 - 38, -d / 2 + 4, 16), (w / 2 - 4, d / 2 - 40, 100))])
    return X


def trampoline(r=60.0, h=16.0):
    X = ML.Model()
    revolve(X.mesh(TX['paint_blue']), [(r + 8, h - 4), (r + 8, h), (r, h)], n=24)
    disc(X.mesh(TX['tramp_mat']), r, h - 2, up=True, n=24)
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(X.mesh(TX['steel']), [(r * math.cos(a), r * math.sin(a), 0), (r * math.cos(a), r * math.sin(a), h - 4)], 3, nseg=5)
    X.mesh(TX['sticker']).poly([np.array(p, float) for p in ((-34, -34, h - 1), (34, -34, h - 1), (34, 34, h - 1), (-34, 34, h - 1))],
                               (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save('trampoline', X)
    COLL['trampoline'] = dict(cyls=[(0, 0, r + 2, 0, h)])
    return X


def cannon(r=46.0):
    """circus cannon aimed skywards on a two-wheeled carriage - you stand at its muzzle mouth (dressing, no collision)"""
    X = ML.Model()
    for s in (-1, 1):
        ring = [(s * 64, 90 * math.cos(t) - 40, 90 + 90 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 25)]
        tube(X.mesh(TX['wood_dark']), ring, 7, nseg=6, caps=(False, False))
        tube(X.mesh(TX['gold']), [(s * 50, -40, 90), (s * 70, -40, 90)], 14, nseg=8)
    tmp = Mesh(); revolve(tmp, [(r + 18, 0), (r + 10, 60), (r + 6, 220), (r + 12, 236), (r, 238)], n=20, u_tiles=2)
    a = math.radians(-20)
    Rm = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    X.mesh(TX['cannon']).add(tmp, Rm, (0, -60, 0))
    disc(X.mesh(TX['rubber']), 50, 1, up=True, n=20)
    ML.save('cannon', X)
    return X


def striker_plate():
    """test-your-strength base plate (pad skin, 8u deck) with the tall scale and bell beside it"""
    X = ML.Model()
    rbox(X.mesh(TX['steel']), (-50, -50, 0), (50, 50, 8), r=2, k=1, tile=64)
    X.mesh(TX['sticker']).poly([np.array(p, float) for p in ((-36, -36, 8.6), (36, -36, 8.6), (36, 36, 8.6), (-36, 36, 8.6))],
                               (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    rbox(X.mesh(TX['striker']), (-20, 60, 0), (20, 76, 640), r=2, k=1, tile=640)
    tube(X.mesh(TX['steel']), [(0, 68, 20), (0, 68, 640)], 3, nseg=4)
    revolve(X.mesh(TX['gold']), [(36, 640), (30, 680), (0, 690)], n=16, cy=68)
    ML.save('striker', X)
    COLL['striker'] = dict(boxes=[((-48, -48, 0), (48, 48, 8)), ((-18, 62, 0), (18, 74, 640))])
    return X


def coffin_pad():
    """upright-lidded coffin lying open on the floor: step in and it throws you onto the roof (dressing)"""
    X = ML.Model()
    poly = [(-40, -80), (40, -80), (52, 30), (30, 90), (-30, 90), (-52, 30)]
    prism(X.mesh(TX['coffin']), poly, 0, 6, tile=128)
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); nx, ny = dy / L, -dx / L
        q = [np.array([a[0], a[1], 0.]), np.array([b[0], b[1], 0.]), np.array([b[0], b[1], 40.]), np.array([a[0], a[1], 40.])]
        X.mesh(TX['coffin']).poly(q, (nx, ny, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    disc(X.mesh(TX['coffin_in']), 30, 7, up=True, n=12)
    lid = Mesh(); prism(lid, poly, 0, 8, tile=128)
    X.mesh(TX['coffin']).add(lid, np.eye(3), (70, 150, 0))                 # the lid, slid off onto the floor
    ML.save('coffin_pad', X)
    return X


def springboard(w=90.0, L=140.0):
    """circus springboard: a wooden plank on a hinge and a big coil, low enough to be a step (deck 16)"""
    X = ML.Model()
    rbox(X.mesh(TX['wood']), (-w / 2, -L / 2, 10), (w / 2, L / 2, 16), r=2, k=1, tile=128)
    rbox(X.mesh(TX['paint_red']), (-w / 2, -L / 2, 0), (w / 2, L / 2, 10), r=2, k=1, tile=128)
    X.mesh(TX['sticker']).poly([np.array(p, float) for p in ((-36, -36, 16.6), (36, -36, 16.6), (36, 36, 16.6), (-36, 36, 16.6))],
                               (0, 0, 1), [(0, 1), (1, 1), (1, 0), (0, 0)])
    ML.save('springboard', X)
    COLL['springboard'] = dict(boxes=[((-w / 2, -L / 2, 0), (w / 2, L / 2, 16))])
    return X


# ================================================================================================ props
def fence_panel(L=512.0, h=180.0):
    X = ML.Model()
    X.mesh(TX['fence']).poly([np.array(p, float) for p in ((-L / 2, 0, 0), (L / 2, 0, 0), (L / 2, 0, h), (-L / 2, 0, h))], (0, -1, 0),
                             [(0, 1), (L / 256, 1), (L / 256, 0), (0, 0)])
    for x in (-L / 2, L / 2):
        tube(X.mesh(TX['steel']), [(x, 0, 0), (x, 0, h + 10)], 4, nseg=6)
        rbox(X.mesh(TX['rubber']), (x - 26, -14, 0), (x + 26, 14, 14), r=3, k=1, tile=64)
    ML.save('fence_panel', X)
    return X


def festoon(L, sag=60.0, n=14, name='festoon'):
    """string of bulbs hanging between two poles (each pole 360 tall), local x from 0 to L"""
    X = ML.Model()
    for x in (0, L):
        tube(X.mesh(TX['steel']), [(x, 0, 0), (x, 0, 360)], 5, nseg=6)
        rbox(X.mesh(TX['rubber']), (x - 20, -20, 0), (x + 20, 20, 10), r=2, k=1, tile=64)
    pts = [(L * t, 0, 350 - sag * 4 * t * (1 - t)) for t in np.linspace(0, 1, 25)]
    tube(X.mesh(TX['rubber']), pts, 1.5, nseg=4, caps=(False, False))
    for k in range(1, n):
        t = k / n
        cols = ('bulb', 'bulb_red', 'bulb_blue')
        sphere(X.mesh(TX[cols[k % 3]] if cols[k % 3] != 'bulb' else TX['bulb']), (L * t, 0, 350 - sag * 4 * t * (1 - t) - 10), 7, nu=6, nv=4)
    ML.save(name, X)
    COLL[name] = dict(cyls=[(0, 0, 6, 0, 360), (L, 0, 6, 0, 360)])
    return X


def candyfloss_machine():
    X = ML.Model()
    revolve(X.mesh(TX['chrome']), [(70, 0), (70, 60), (90, 70), (90, 100), (0, 100)], n=20)
    for (x, y) in ((-20, 10), (25, -10), (5, 30)):
        tube(X.mesh(TX['wood']), [(x, y, 100), (x, y, 150)], 2, nseg=4)
        sphere(X.mesh(TX['candyfloss']), (x, y, 175), 30, nu=10, nv=8)
    ML.save('candyfloss', X)
    COLL['candyfloss'] = dict(cyls=[(0, 0, 84, 0, 100)])
    return X


def coconut_stand(n=5):
    X = ML.Model()
    for k in range(n):
        x = -200 + k * 100
        tube(X.mesh(TX['wood_dark']), [(x, 0, 0), (x, 0, 150)], 6, nseg=6)
        revolve(X.mesh(TX['wood_dark']), [(16, 150), (10, 160), (0, 160)], n=10, cx=x)
        sphere(X.mesh(TX['coconut']), (x, 0, 178), 18, nu=10, nv=8)
    ML.save('coconut_stand', X)
    return X


def caravan_wheels(L=420.0):
    X = ML.Model()
    for x in (-L * 0.2, L * 0.2):
        for y in (-100, 100):
            tmp = Mesh(); revolve(tmp, [(0, -6), (36, -6), (36, 6), (0, 6)], n=16)
            X.mesh(TX['rubber']).add(tmp, RX90, (x, y * 1.06, 36))
    tube(X.mesh(TX['steel']), [(L / 2, 0, 40), (L / 2 + 120, 0, 20)], 6, nseg=6)
    rbox(X.mesh(TX['steel']), (L / 2 + 110, -12, 0), (L / 2 + 130, 12, 24), r=2, k=1, tile=32)
    ML.save('caravan_wheels', X)
    return X


def skeleton():
    X = ML.Model()
    b = TX['bone']
    sphere(X.mesh(b), (0, 0, 150), 16, nu=10, nv=8)
    for e in (-6, 6): sphere(X.mesh(TX['eyes']), (e, -14, 154), 4, nu=6, nv=4)
    tube(X.mesh(b), [(0, 0, 134), (0, 0, 70)], 3, nseg=5)
    for z in range(80, 130, 10):
        ring = [(14 * math.cos(t), 8 * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, 13)]
        tube(X.mesh(b), ring, 2, nseg=4, caps=(False, False))
    for s in (-1, 1):
        tube(X.mesh(b), [(s * 16, 0, 126), (s * 30, -10, 90), (s * 34, -24, 60)], 2.5, nseg=4)
        tube(X.mesh(b), [(s * 8, 0, 70), (s * 10, 0, 36), (s * 10, -4, 0.5)], 3, nseg=4)
    ML.save('skeleton', X)
    return X


def ghost_sheet():
    X = ML.Model()
    revolve(X.mesh(TX['ghost']), [(40, 0), (34, 60), (28, 110), (16, 140), (0, 146)], n=16, u_tiles=1,
            rfun=lambda a, r, z: r * (1 + 0.15 * math.sin(a * 5)) if z < 10 else r)
    for e in (-10, 10): sphere(X.mesh(TX['eyes']), (e, -26, 118), 5, nu=6, nv=4)
    ML.save('ghost', X)
    return X


def crystal_ball():
    X = ML.Model()
    revolve(X.mesh(TX['gold']), [(40, 0), (30, 20), (34, 30), (0, 30)], n=16)
    sphere(X.mesh(TX['crystal']), (0, 0, 64), 36, nu=14, nv=10)
    ML.save('crystal_ball', X)
    return X
