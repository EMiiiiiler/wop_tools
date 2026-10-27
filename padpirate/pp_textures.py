"""Procedural brush textures, the tropical sea sky cube, shader + arena for wop_padpirate (Skull Rock Bay).
All art is original and generated here.

make_textures() writes textures/padpirate/* and env/padpirate/* (sky); make_shader() writes scripts/padpirate.shader
(brush textures + every MD3 shader registered in pplib.REG); make_arena() writes scripts/wop_padpirate.arena."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pplib import *
import pplib

MAP = 'wop_padpirate'
LONGNAME = 'Skull Rock Bay'
SIZES = {}
ALPHA = set()
SUN = (95.0, 55.0)                      # yaw (90 = north: the user plays in New Zealand), elevation

SANDC = (230, 210, 160); CORAL = (214, 196, 160); TAR = (40, 32, 28); NAVY = (28, 40, 70); RED = (150, 36, 30)
GOLD = (226, 178, 64); BONE = (232, 224, 200); TEAK = (150, 104, 62); DRIFT = (176, 160, 136)


def W(name, a, alpha=None):
    SIZES[name] = save_img(out(TD, name), a, alpha)
    if alpha is not None: ALPHA.add(name)


# ------------------------------------------------------------------------------------------- stone + ground
def ashlar(w=512, h=512, seed=1, base=CORAL, rows=6, cols=3, jitter=14, mortar=0.7, moss=0.0, salt=0.0):
    r = np.random.default_rng(seed)
    x, y = xy(w, h)
    row = np.floor(y * rows).astype(int)
    off = (row % 2) * 0.5 / cols + r.uniform(-0.08, 0.08, rows + 1)[row % (rows + 1)] / cols
    cx_ = np.floor((x + off) * cols).astype(int)
    tone = r.uniform(-jitter, jitter, (rows + 1, cols + 3))[row % (rows + 1), cx_ % (cols + 3)]
    c = np.zeros((h, w, 3), np.float32) + C(base) + tone[..., None] + N3(w, 1, seed + 1, 6, h) + N3(w, 7, seed + 2, 7, h)
    fu = (x + off) * cols % 1.0; fv = y * rows % 1.0
    d = np.minimum(np.minimum(fu, 1 - fu) / cols * w / h, np.minimum(fv, 1 - fv) / rows)
    edge = np.clip(d * 60, 0, 1)
    c = c * (mortar + (1 - mortar) * edge)[..., None]
    pits = np.clip(noise(w, 0.7, seed + 3, h) - 1.8, 0, 1)[..., None]
    c = c * (1 - pits * 0.4)
    if moss > 0:
        m = np.clip((1 - edge) * 1.2 + noise(w, 5, seed + 4, h) * 0.35 - 0.6, 0, 1) * moss
        c = lerp(c, C((70, 96, 52)) + N3(w, 0.8, seed + 5, 14, h), m[..., None])
    if salt > 0:
        s = np.clip(y * 1.6 - 0.9 + noise(w, 3, seed + 6, h) * 0.2, 0, 1) * salt
        c = lerp(c, C((70, 66, 58)), s[..., None])
    return c


def cobbles(n=512, seed=3, base=(196, 182, 156)):
    """rounded harbour cobbles (Voronoi), sun-bleached, sand in the joints"""
    idx, ed = voronoi(n, 120, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-18, 18, 120)[idx]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None] + N3(n, 1.2, seed + 1, 6) + N3(n, 8, seed + 2, 6)
    dome = np.clip(ed * 70, 0, 1)
    c = c * (0.55 + 0.45 * dome)[..., None]
    return np.where((ed < 0.006)[..., None], C((200, 180, 130)) + N3(n, 0.5, seed + 3, 10), c)


def sand(n=256, seed=27, base=SANDC):
    c = fill(n, base, 6, seed) + N3(n, 0.4, seed + 1, 14) + N3(n, 6, seed + 2, 6)
    x, y = xy(n)
    rip = np.sin((y * 9 + noise(n, 12, seed + 3) * 0.25) * 2 * math.pi) * 5
    return c + rip[..., None]


def wet_sand(n=256, seed=29):
    return sand(n, seed, (196, 170, 120)) * 0.95


def grass(n=512, seed=23):
    c = fill(n, (86, 136, 56), 10, seed) + N3(n, 0.5, seed + 1, 22) + N3(n, 10, seed + 2, 12)
    d = noise(n, 16, seed + 3)
    c = lerp(c, C((116, 158, 64)), np.clip(d * 0.5, 0, 1)[..., None])
    return lerp(c, C((200, 180, 130)), np.clip(-d * 0.4 - 0.3, 0, 1)[..., None])


def bank(n=512, seed=25):
    """jungle cliff: dark volcanic rock, moss and ferns"""
    c = fill(n, (92, 80, 68), 10, seed) + N3(n, 0.6, seed + 1, 16)
    x, y = xy(n)
    strata = np.sin((y + noise(n, 14, seed) * 0.06) * 2 * math.pi * 5) * 10
    c += strata[..., None]
    m = np.clip(noise(n, 9, seed + 2) * 0.6 + 0.2, 0, 1)
    return lerp(c, C((62, 104, 44)) + N3(n, 0.5, seed + 3, 18), m[..., None])


def rock(n=512, seed=31, base=(150, 138, 120)):
    x, y = xy(n)
    strata = np.sin((y + noise(n, 14, seed) * 0.05) * 2 * math.pi * 6) * 9
    c = np.zeros((n, n, 3), np.float32) + C(base) + strata[..., None] + N3(n, 1, seed + 1, 10) + N3(n, 6, seed + 2, 14)
    cr = np.clip(np.abs(noise(n, 3, seed + 3)) < 0.05, 0, 1)
    return c * (1 - cr * 0.35)[..., None]


def planks(n=256, seed=33, base=TEAK, boards=4, seam=(58, 40, 26), weather=0.0):
    """boardwalk / deck planks running along u (x), butt joints staggered"""
    x, y = xy(n)
    row = np.floor(y * boards).astype(int)
    r = np.random.default_rng(seed)
    tone = r.uniform(-16, 16, boards + 1)[row % (boards + 1)]
    c = np.zeros((n, n, 3), np.float32) + C(base) + tone[..., None]
    st = np.asarray(img(noise(n, 1, seed + 1) * 50 + 128).resize((n, n // 24)).resize((n, n)), np.float32) - 128
    c += st[..., None] * 0.35
    v = (y * boards) % 1.0
    off = r.uniform(0, 1, boards + 1)[row % (boards + 1)]
    u = (x + off) % 1.0
    c = np.where(((v < 0.05) | (v > 0.96))[..., None], C(seam), c)
    c = np.where((np.abs(u - 0.5) < 0.006)[..., None], C(seam), c)
    nail = ((np.abs(u - 0.47) < 0.008) | (np.abs(u - 0.53) < 0.008)) & ((np.abs(v - 0.25) < 0.04) | (np.abs(v - 0.75) < 0.04))
    c = np.where(nail[..., None], C((50, 46, 44)), c)
    if weather > 0:
        c = lerp(c, C((150, 146, 136)), (np.clip(noise(n, 10, seed + 2) * 0.4 + 0.3, 0, 1) * weather)[..., None])
    return c


def plaster(n=256, col=(232, 220, 196), seed=11):
    c = fill(n, col, 4, seed) + N3(n, 6, seed + 1, 6)
    chips = np.clip(noise(n, 1.4, seed + 2) - 1.6, 0, 1)[..., None]
    return lerp(c, C((150, 120, 96)), np.clip(chips * 2, 0, 1))


def timber_wall(w=512, h=512, seed=13):
    """tavern wall: whitewashed plaster between dark timber posts and a timber sill band"""
    c = plaster(w, (226, 214, 188), seed)
    x, y = xy(w, h)
    beam = C((70, 48, 32)) + N3(w, 1, seed + 2, 8, h)
    c = np.where((((x * 2) % 1) < 0.07)[..., None], beam, c)
    c = np.where(((y > 0.86) | (y < 0.05))[..., None], beam, c)
    return c


def pool_tile(n=256, seed=17):
    idx, ed = voronoi(n, 160, seed)
    r = np.random.default_rng(seed)
    tone = r.uniform(-1, 1, (160, 3)) * np.array([10, 22, 22])
    c = np.zeros((n, n, 3), np.float32) + C((60, 170, 186)) + tone[idx] + N3(n, 0.8, seed + 1, 5)
    c = c * (0.72 + 0.28 * np.clip(ed * 160, 0, 1))[..., None]
    x, y = xy(n)
    g = ((x * 2 % 1) < 0.02) | ((y * 2 % 1) < 0.02)
    return np.where(g[..., None], C((30, 110, 120)), c)


def pool_band(w=512, h=256, seed=19):
    """pool wall: coral stone with a navy rope-and-wave band at the water line"""
    c = ashlar(w, h, seed, (190, 196, 180), 3, 4, 8, 0.75)
    im = Image.new('RGB', (w, 64), NAVY); d = ImageDraw.Draw(im)
    for k in range(16):
        x0 = k * w / 16
        d.arc((x0, 14, x0 + w / 16, 50), 180, 360, fill=(240, 236, 220), width=5)
    for k in range(64):
        x0 = k * w / 64
        d.line([(x0, 4), (x0 + 6, 10)], fill=(200, 170, 110), width=3)
        d.line([(x0, 54), (x0 + 6, 60)], fill=(200, 170, 110), width=3)
    c[16:80] = np.asarray(im, np.float32)
    return c


def coping(n=256, seed=21):
    return ashlar(n, n, seed, (226, 214, 186), 1, 2, 6, 0.75)


def quay(w=512, h=256, seed=35):
    """sea wall: big dark coral blocks, salt and weed near the bottom"""
    return ashlar(w, h, seed, (150, 140, 120), 3, 2, 14, 0.6, moss=0.3, salt=1.0)


def fort_stone(w=512, h=512, seed=37):
    return ashlar(w, h, seed, (204, 186, 150), 6, 3, 16, 0.65, moss=0.25)


def gold_floor(n=256, seed=39):
    """vault floor: gold coins scattered over stone"""
    c = ashlar(n, n, seed, (110, 96, 80), 3, 3, 10, 0.7)
    im = img(c).convert('RGB'); d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(220):
        x, y, s = r.uniform(0, n), r.uniform(0, n), r.uniform(4, 9)
        col = tuple(int(v) for v in np.array(GOLD) * r.uniform(0.8, 1.15))
        d.ellipse((x - s, y - s * 0.7, x + s, y + s * 0.7), fill=col, outline=(150, 100, 30))
    return np.asarray(im, np.float32)


def jumppad_tex(n=256):
    """compass-rose jump pad: gold star on navy with a red ring"""
    x, y = xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + C(NAVY)
    k8 = np.abs(((a * 8 / (2 * math.pi)) % 1.0) - 0.5) * 2
    k4 = np.abs(((a * 4 / (2 * math.pi) + 0.5) % 1.0) - 0.5) * 2
    star = (rr < 0.42 * (1 - 0.82 * k4)) | (rr < 0.26 * (1 - 0.75 * k8))
    c = np.where(star[..., None], C((250, 210, 90)), c)
    c = np.where((np.abs(rr - 0.44) < 0.025)[..., None], C((190, 40, 30)), c)
    c = np.where((rr > 0.47)[..., None], C((90, 60, 36)), c)
    c = np.where((rr < 0.05)[..., None], C((255, 245, 200)), c)
    return c + N3(n, 1, 35, 4)


def water_tex(n=256, seed=41, col=(40, 150, 170)):
    c = fill(n, col, 6, seed)
    r = np.sin(noise(n, 10, seed + 1) * 3) * 16
    return c + r[..., None]


def sea_tex(n=512, seed=43):
    """open sea: deep blue with wave crests"""
    c = fill(n, (24, 92, 140), 6, seed)
    w = np.sin(noise(n, 8, seed + 1) * 4) * 14 + np.clip(noise(n, 1.5, seed + 2) - 1.7, 0, 1) * 120
    return c + w[..., None] * C((0.9, 1.0, 1.0))


def caustic(n=256, seed=45):
    a = np.abs(noise(n, 5, seed)) + np.abs(noise(n, 5, seed + 1))
    v = np.clip(1.0 - a * 1.1, 0, 1) ** 3
    return np.zeros((n, n, 3), np.float32) + (v * 140)[..., None] * C((0.7, 1.0, 1.0))


def waterfall_tex(w=128, h=256, seed=47):
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.8, seed, h) * 60 + 128).resize((w, h // 16)).resize((w, h)), np.float32) / 255
    a = np.clip(0.35 + (st - 0.5) * 1.6 + noise(w, 2, seed + 1, h) * 0.1, 0, 1)
    c = np.zeros((h, w, 3), np.float32) + C((210, 240, 245)) + (st * 40)[..., None]
    return c, a * 255


def rope_tex(w=64, h=128, seed=49):
    x, y = xy(w, h)
    s = ((x * 3 + y * 6) % 1.0)
    c = np.zeros((h, w, 3), np.float32) + C((176, 146, 96)) * (0.7 + 0.3 * np.sin(s * math.pi))[..., None]
    return c + N3(w, 0.6, seed, 8, h)


SIGNS = {
    'sign_main': ('SKULL ROCK BAY', 1024, 256, (60, 36, 22), (250, 214, 120)),
    'sign_tavern': ('THE RUSTY ANCHOR', 1024, 192, (40, 28, 20), (240, 200, 110)),
    'sign_shop': ('YE OLDE GIFT SHOPPE', 1024, 160, (30, 60, 90), (250, 230, 170)),
    'sign_fort': ('FORT SAN PADRO', 1024, 128, (60, 50, 40), (240, 220, 170)),
    'sign_shark': ('SHARK POOL - DIVE AT YER OWN RISK', 1024, 128, (150, 30, 24), (255, 250, 230)),
    'sign_cove': ('TREASURE COVE', 1024, 192, (40, 70, 80), (250, 226, 150)),
    'sign_vault': ("CAPTAIN PADBEARD'S HOARD", 1024, 128, (50, 26, 10), (255, 214, 100)),
    'sign_ship': ('THE SALTY PADMAN', 1024, 128, (20, 18, 16), (236, 190, 80)),
    'sign_skull': ('SKULL ROCK', 512, 128, (40, 30, 24), (240, 226, 200)),
}


def signboard(text, w, h, bg, fg):
    a = text_img(text, w, h, bg, fg, True, border=fg)
    # wood grain over the board
    gr = np.asarray(img(noise(w, 1, 51, h) * 50 + 128).resize((w, max(1, h // 12))).resize((w, h)), np.float32) - 128
    return a + gr[..., None] * 0.15 + N3(w, 1, 43, 4, h)


def bamboo(w=256, h=256, seed=77):
    x, y = xy(w, h)
    k = np.floor(x * 10).astype(int)
    f = (x * 10) % 1.0
    c = np.zeros((h, w, 3), np.float32) + C((200, 170, 100)) * (0.7 + 0.3 * np.sin(f * math.pi))[..., None]
    off = np.random.default_rng(seed).uniform(0, 1, 10)[k % 10]
    node = np.abs(((y * 3 + off) % 1.0) - 0.5) < 0.02
    c = np.where(node[..., None], C((130, 100, 50)), c)
    return c + N3(w, 1, seed + 1, 6, h)


def thatch(w=256, h=256, seed=79):
    x, y = xy(w, h)
    st = np.asarray(img(noise(w, 0.6, seed, h) * 60 + 128).resize((w, h // 12)).resize((w, h)), np.float32) / 255
    c = lerp(C((150, 120, 66)), C((206, 176, 108)), st[..., None])
    return c * (0.65 + 0.35 * ((y * 6) % 1.0))[..., None] + N3(w, 1, seed + 1, 6, h)


# ------------------------------------------------------------------------------------------- sky
def make_sky(n=512):
    """tropical afternoon: deep blue sky, cumulus, the sea to the horizon with sun glitter, a few green islands, a
    distant sailing ship"""
    d = out('env', NS); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    Uu, Vv = np.meshgrid(u, u)
    s = 2 * Uu - 1; t = 1 - 2 * Vv
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}
    A = np.linspace(-180, 180, 4097)
    isl = np.zeros_like(A)
    for (ca, h, w) in ((20, 2.2, 9), (55, 1.2, 5), (140, 3.0, 11), (-150, 1.6, 7), (-60, 0.9, 4), (100, 4.2, 6)):
        isl = np.maximum(isl, h * np.clip(1 - ((A - ca) / w) ** 2, 0, 1) ** 0.7 * (1 + 0.15 * np.sin(A * 3.1 + ca)))
    sy, se = math.radians(SUN[0]), math.radians(SUN[1])
    sd = np.array([math.cos(se) * math.cos(sy), math.cos(se) * math.sin(sy), math.sin(se)])
    cl = [noise(512, 10, 21 + k) for k in range(3)]
    gl = noise(512, 0.6, 33)
    for k, (x, y, z) in faces.items():
        D = np.stack([x, y, z], -1)
        Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
        zz = Dn[..., 2]
        az = np.degrees(np.arctan2(Dn[..., 1], Dn[..., 0]))
        el = np.degrees(np.arcsin(np.clip(zz, -1, 1)))
        up = np.clip(zz, 0, 1)
        c = lerp(C((176, 216, 238)), C((40, 110, 210)), (up ** 0.55)[..., None])
        cs = np.clip(Dn @ sd, 0, 1)
        c = c + (cs ** 40 * 110 + cs ** 600 * 420)[..., None] * C((1.0, 0.96, 0.82))
        uu = (az + 180) / 360 * 4; vv = el / 40
        ci = (np.floor(uu * 512) % 512).astype(int); cj = (np.floor(np.clip(vv, 0, 0.999) * 511)).astype(int)
        cn = cl[0][cj, ci] * 0.6 + cl[1][(cj * 3) % 512, (ci * 3) % 512] * 0.4
        band = np.exp(-((el - 11) / 8) ** 2)
        cov = np.clip(cn * 0.9 + band * 0.85 - 0.78, 0, 1)
        shade = np.clip(1.15 - (el - 4) / 40, 0.75, 1.15)
        c = lerp(c, C((252, 252, 250)) * shade[..., None], (cov * (el > 0.6))[..., None])
        # islands on the horizon
        ih = np.interp(az, A, isl)
        landc = lerp(C((70, 110, 80)), C((110, 140, 120)), np.clip(el[..., None] / 4, 0, 1))
        c = np.where(((el < ih) & (el >= 0))[..., None], landc, c)
        # a distant ship (two masts, sails) at azimuth -30
        sh = (np.abs(az + 30) < 0.9) & (el >= 0) & (el < 0.35)
        sails = ((np.abs(az + 30.35) < 0.22) | (np.abs(az + 29.65) < 0.22)) & (el >= 0.3) & (el < 1.25)
        c = np.where(sh[..., None], C((60, 50, 44)), c)
        c = np.where(sails[..., None], C((236, 232, 220)), c)
        # the sea below the horizon, sun glitter toward the sun's azimuth
        sea = el < 0
        depth = np.clip(-el / 25, 0, 1)
        seac = lerp(C((90, 160, 196)), C((18, 70, 120)), depth[..., None])
        da = np.abs(((az - SUN[0]) + 180) % 360 - 180)
        glit = np.exp(-(da / (3 + depth * 10)) ** 2) * np.clip(gl[(cj * 7) % 512, ci] - 0.6, 0, 1) * 300 * (1 - depth)
        seac = seac + glit[..., None]
        c = np.where(sea[..., None], seac, c)
        img(c).save(os.path.join(d, f'tropic_{k}.jpg'), quality=94)
    c2 = np.clip(noise(512, 14, 41) * 0.7 + noise(512, 4, 42) * 0.3 - 0.45, 0, 2)
    img(np.zeros((512, 512, 3)) + (c2 * 120)[..., None]).save(os.path.join(d, 'tropic_clouds.jpg'), quality=92)
    W('skylight', fill(64, (176, 206, 236), 2, 45))


# ------------------------------------------------------------------------------------------- all brush textures
def make_textures():
    W('cobbles', cobbles()); W('sand', sand()); W('wet_sand', wet_sand()); W('grass', grass()); W('bank', bank()); W('rock', rock())
    W('planks', planks()); W('deck', planks(256, 61, (176, 140, 96), 5, weather=0.25)); W('boardwalk', planks(256, 63, (150, 120, 84), 4, weather=0.5))
    W('plaster', plaster()); W('timber_wall', timber_wall()); W('pool_tile', pool_tile()); W('pool_band', pool_band()); W('coping', coping())
    W('quay', quay()); W('fort_stone', fort_stone()); W('fort_floor', cobbles(512, 65, (176, 166, 146))); W('gold_floor', gold_floor())
    W('jumppad', jumppad_tex()); W('rubber', fill(64, (90, 60, 36), 3, 59)); W('water', water_tex()); W('water_deep', water_tex(256, 67, (24, 110, 140)))
    W('sea', sea_tex()); W('nodraw_ns', fill(64, (200, 60, 200), 2, 69)); W('clip_ed', fill(64, (200, 120, 40), 2, 71)); W('caustic', caustic())
    W('dark', fill(64, (24, 20, 18), 2, 73)); W('rope', rope_tex())
    W('shop_wall', planks(256, 75, (70, 120, 160), 6, seam=(30, 50, 70), weather=0.3)); W('bamboo_w', bamboo()); W('thatch_t', thatch())
    wf, wa = waterfall_tex(); W('waterfall', wf, wa)
    for nm, (t, w, h, bg, fg) in SIGNS.items():
        W(nm, signboard(t, w, h, bg, fg))
    make_sky()


# ------------------------------------------------------------------------------------------- shader
STEPS = {'cobbles': 'sandsteps', 'sand': 'sandsteps', 'wet_sand': 'sandsteps', 'grass': 'softsteps', 'bank': 'softsteps', 'planks': 'woodsteps',
         'deck': 'woodsteps', 'boardwalk': 'woodsteps', 'pool_tile': 'splashsteps', 'fort_floor': 'sandsteps'}
CAUSTIC_ON = {'pool_tile', 'pool_band', 'rock'}


def lm(name, steps=None, extra='', tex=None, stage=''):
    t = tex or f'{TD}/{name}'
    s = f'{TD}/{name}\n{{\n\tqer_editorimage {t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


CAUSTIC_STAGE = (f'\t{{\n\t\tmap {TD}/caustic\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.35 0.35 0.35 )\n'
                 f'\t\ttcMod scale 0.5 0.5\n\t\ttcMod turb 0 0.05 0 0.12\n\t\ttcMod scroll 0.02 0.015\n\t}}\n')


def model_shaders():
    s = '// ---- MD3 / IQM models (pp_models.py)\n'
    for name, (im, kind, opt) in sorted(REG.items()):
        t = im if im.startswith('textures/') else f'{MD}/{im}'
        two = '\tcull none\n' if opt.get('two') else ''
        if kind in ('lm', 'lms'):
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_nonplanar\n\tq3map_shadeAngle {opt.get("shade", 75)}\n{two}'
            if opt.get('steps'): s += f'\tsurfaceparm {opt["steps"]}\n'
            s += f'\t{{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}}\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n'
            if kind == 'lms':
                v = opt.get('v', 0.2)
                s += f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {v} {v} {v} )\n\t\ttcGen environment\n\t}}\n'
            if opt.get('caustic'): s += CAUSTIC_STAGE
            s += '}\n\n'
        elif kind == 'vl':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tq3map_shadeAngle 70\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'alpha':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tqer_trans 0.7\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n'
                  f'\tcull none\n\tq3map_vertexScale {opt.get("vs", 1.0)}\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen vertex\n\t}}\n}}\n\n'
        elif kind == 'glow':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n{two}'
            s += f'\t{{\n\t\tmap {t}\n\t\trgbGen {opt.get("wave", "identity")}\n\t}}\n}}\n\n'
        elif kind == 'add':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n')
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen {opt.get("wave", "identity")}\n'
            if opt.get('tcmod'): s += f'\t\ttcMod {opt["tcmod"]}\n'
            s += '\t}\n}\n\n'
        elif kind == 'flow':
            s += (f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n'
                  f'\tcull none\n\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen identity\n'
                  f'\t\ttcMod scroll 0 {opt.get("speed", -1.2)}\n\t}}\n'
                  f'\t{{\n\t\tmap {t}.tga\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.14 0.15 )\n\t\ttcMod scroll 0.05 {opt.get("speed", -1.2) * 1.4:g}\n\t}}\n}}\n\n')
        elif kind == 'dyn':
            s += f'{name}\n{{\n\tqer_editorimage {t}\n{two}\t{{\n\t\tmap {t}\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'dynalpha':
            s += f'{name}\n{{\n\tqer_editorimage {t}.tga\n\tcull none\n'
            if opt.get('deform'): s += f'\tdeformVertexes {opt["deform"]}\n'
            s += f'\t{{\n\t\tmap {t}.tga\n\t\talphaFunc GE128\n\t\tdepthWrite\n\t\trgbGen lightingDiffuse\n\t}}\n}}\n\n'
        elif kind == 'flag':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nomarks\n\tsurfaceparm nonsolid\n\tcull none\n'
                  f'\tdeformVertexes wave {opt.get("div", 60)} sin 0 {opt.get("amp", 4)} 0 {opt.get("freq", 1.2)}\n'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen vertex\n\t}}\n}}\n\n')
        elif kind == 'glass':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n\tsurfaceparm nolightmap\n\tcull none\n'
                  f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {opt.get("c", "0.12 0.14 0.15")} )\n\t}}\n'
                  f'\t{{\n\t\tmap {MD}/env\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.2 0.2 0.22 )\n\t\ttcGen environment\n\t}}\n}}\n\n')
        elif kind == 'flicker':
            s += (f'{name}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n{two}'
                  f'\t{{\n\t\tmap {t}\n\t\trgbGen wave noise 0.85 0.15 {opt.get("ph", 0)} 6\n\t}}\n}}\n\n')
    return s


def water_shader(name, img_):
    return f'''{TD}/{name}
{{
	qer_editorimage {TD}/{img_}
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	cull none
	{{
		map {TD}/{img_}
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.62
		rgbGen identity
		tcMod turb 0 0.05 0 0.12
		tcMod scroll 0.01 0.02
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.2 0.22 0.22 )
		tcGen environment
	}}
}}

{TD}/{name}_nodraw
{{
	qer_editorimage {TD}/{img_}
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nodraw
	surfaceparm nolightmap
}}

'''


def make_shader():
    S_ = f"// {NS}.shader - {LONGNAME} (generated by wop_tools/padpirate/pp_textures.py)\n\n"
    special = {'nodraw_ns', 'skylight', 'jumppad', 'water', 'water_deep', 'waterfall', 'caustic', 'clip_ed', 'sea', 'rope'}
    for nm in sorted(SIZES):
        if nm in special: continue
        S_ += lm(nm, STEPS.get(nm), stage=CAUSTIC_STAGE if nm in CAUSTIC_ON else '')
    pad_stage = f'\t{{\n\t\tmap {TD}/jumppad\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.25 0.2 0 0.7\n\t\ttcMod rotate 30\n\t}}\n'
    S_ += lm('jumppad', extra='\tq3map_surfacelight 60\n\tq3map_lightRGB 1 0.8 0.4\n\tq3map_lightSubdivide 128\n', stage=pad_stage)
    S_ += water_shader('water', 'water')
    S_ += water_shader('water_deep', 'water_deep')
    S_ += f'''{TD}/sky
{{
	qer_editorimage {TD}/skylight
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_lightimage {TD}/skylight
	q3map_sun 1 0.95 0.84 250 {SUN[0]:g} {SUN[1]:g}
	q3map_skylight 75 3
	skyparms env/{NS}/tropic 512 -
	{{
		map env/{NS}/tropic_clouds
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.32 0.32 0.32 )
		tcMod scale 3 3
		tcMod scroll 0.006 0.003
	}}
}}

{TD}/sea
{{
	qer_editorimage {TD}/sea
	surfaceparm nolightmap
	surfaceparm nomarks
	q3map_globaltexture
	{{
		map {TD}/sea
		rgbGen identity
		tcMod turb 0 0.03 0 0.08
		tcMod scroll 0.008 0.012
	}}
	{{
		map {TD}/sea
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.18 0.2 0.22 )
		tcMod scale 0.5 0.5
		tcMod scroll -0.01 0.006
	}}
	{{
		map {MD}/env
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.16 0.18 0.2 )
		tcGen environment
	}}
}}

{TD}/rope
{{
	qer_editorimage {TD}/rope
	{{
		map $lightmap
		rgbGen identity
	}}
	{{
		map {TD}/rope
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}}
}}

{TD}/waterfall
{{
	qer_editorimage {TD}/waterfall.tga
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm nomarks
	surfaceparm nolightmap
	cull none
	{{
		map {TD}/waterfall.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbGen identity
		tcMod scroll 0 1.6
	}}
	{{
		map {TD}/waterfall.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.12 0.14 0.15 )
		tcMod scroll 0.03 2.3
	}}
}}

{TD}/slide_clip
{{
	qer_editorimage {TD}/clip_ed
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm slick
	surfaceparm playerclip
	surfaceparm trans
}}

{TD}/nodraw_ns
{{
	qer_editorimage {TD}/nodraw_ns
	qer_trans 0.4
	surfaceparm nodraw
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	surfaceparm nolightmap
}}

'''
    S_ += model_shaders()
    S_ += (f'levelshots/{MAP}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{MAP}B1 levelshots/{MAP}B2 levelshots/{MAP}B3\n\t}}\n}}\n')
    os.makedirs(out('scripts'), exist_ok=True)
    open(out('scripts', NS + '.shader'), 'w').write(S_)


def make_arena():
    open(out('scripts', MAP + '.arena'), 'w').write(
        '{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "ffa lps team ft syc_ffa syc_tp"\n}\n' % (MAP, LONGNAME))
