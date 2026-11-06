"""Neon Tide (wop_padwave) - textures + custom MD3s. All art is original and generated here.

Brush textures go through TX.add (image + shader in one call), model textures through TX.material. Every model is
built in its own local frame (origin = floor centre) unless the docstring says world coordinates."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from woplib import models as ML, texlib as TL, shaders as SH
from woplib.geom import (tube, cylm, boxm, torus, picture, annulus, frustum_m, sweep, circle_prof, densify, helix,
                         ang_pt)
from woplib import slides as SL
from meshlib import Mesh, revolve, disc, rbox, prism, ellipsoid, sphere, rot_z, frame
import layout as L

C, fill, N3, xy, noise, lerp = ML.C, ML.fill, ML.N3, ML.xy, ML.noise, ML.lerp

PINK = (255, 46, 151); CYAN = (29, 233, 246); VIOLET = (138, 43, 226); ORANGE = (255, 138, 61)
NAVY = (14, 18, 46); WHITE = (232, 234, 240); TEAK = (150, 98, 58); CHROME = (200, 204, 214)
TX = None                      # set by setup()


def setup(tx):
    global TX
    TX = tx


# ================================================================================================= brush textures
def grid_glow(n=256, col=CYAN, lines=4, w=0.03):
    """neon grid lines on black (additive): the synthwave sea and the laser-grid pool floor"""
    x, y = xy(n)
    g = ((x * lines) % 1 < w) | ((y * lines) % 1 < w)
    soft = np.exp(-(((x * lines) % 1 - 0.0) ** 2) / 0.002) + np.exp(-(((y * lines) % 1) ** 2) / 0.002)
    return np.zeros((n, n, 3), np.float32) + C(col) * (g[..., None] * 0.9 + np.clip(soft, 0, 1)[..., None] * 0.4)


def dancefloor_tile(col, n=128):
    x, y = xy(n)
    edge = (x < 0.06) | (x > 0.94) | (y < 0.06) | (y > 0.94)
    glow = np.clip(1 - (np.abs(x - 0.5) + np.abs(y - 0.5)) * 1.1, 0, 1)
    return np.where(edge[..., None], C((20, 20, 26)), C(col) * (0.55 + 0.45 * glow[..., None]))


def cosmic_carpet(n=256, seed=5):
    """arcade carpet: dark navy with neon squiggles, triangles and dots"""
    rng = np.random.default_rng(seed)
    im = Image.new('RGB', (n, n), NAVY)
    d = ImageDraw.Draw(im)
    for _ in range(26):
        c = [PINK, CYAN, ORANGE, VIOLET, (250, 230, 60)][rng.integers(5)]
        x, y = rng.integers(0, n, 2)
        k = rng.integers(3)
        if k == 0: d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=c)
        elif k == 1: d.polygon([(x, y - 9), (x + 9, y + 7), (x - 9, y + 7)], outline=c, width=2)
        else:
            pts = [(x + i * 6, y + 6 * math.sin(i * 1.3)) for i in range(6)]
            d.line(pts, fill=c, width=2)
    a = np.asarray(im, np.float32)
    big = np.concatenate([np.concatenate([a, a], 1)] * 2, 0)
    return big[n // 2:n // 2 + n, n // 2:n // 2 + n] * 0 + a + N3(n, 1, seed, 4)


def make_brush_textures():
    TX.add('teak', TL.planks(TEAK, n_planks=8, gap=(60, 38, 24)), steps='woodsteps', scale=0.75)
    TX.add('deck_white', TL.tiles((214, 218, 226), (180, 184, 194), cols=2, rows=2, offset=0, grout_w=0.012, vary=3), scale=1.0)
    TX.add('wall_white', TL.tiles(WHITE, (196, 200, 210), cols=1, rows=2, offset=0, grout_w=0.01, vary=2))
    TX.add('super_wall', super_wall(), scale=(1.0, 1.375), check_tile=False)
    TX.add('wall_navy', TL.tiles((28, 30, 64), (12, 12, 30), cols=1, rows=2, offset=0, grout_w=0.01, vary=3))
    TX.add('panel_violet', TL.tiles((70, 30, 110), (30, 10, 50), cols=2, rows=1, offset=0, grout_w=0.015, vary=4))
    TX.add('pool_pink', TL.tiles((255, 120, 190), (250, 236, 244), cols=8, rows=8, offset=0, grout_w=0.05, vary=8), steps='splashsteps')
    TX.add('pool_cyan', TL.tiles((60, 210, 236), (236, 250, 252), cols=8, rows=8, offset=0, grout_w=0.05, vary=8), steps='splashsteps')
    TX.add('coping', TL.tiles((240, 240, 236), (200, 200, 196), cols=2, rows=1, offset=0, grout_w=0.02, vary=4))
    TX.add('marble', TL.checker((236, 234, 240), (24, 24, 32), 4, grout=(160, 160, 170)), scale=1.0)
    TX.add('carpet_disco', TL.dots((40, 10, 60), (120, 40, 170), 8, 0.12), steps='carpetsteps')
    TX.add('carpet_arcade', cosmic_carpet(), steps='carpetsteps')
    TX.add('rubber_floor', TL.dots((40, 44, 56), (56, 60, 74), 10, 0.2))
    TX.add('wave_slick', TL.stripes((40, 140, 230), (70, 180, 250), 6, vertical=False, soft=0.6), kind='slick', glint=True)
    TX.add('water', TL.solid((60, 160, 220), 10, 11, 128), 'water', rgb=(0.25, 0.7, 0.85), alpha=0.6)
    TX.add('trim_pink', TL.solid(PINK, 4, 3, 64), 'neon', rgb=(1, 0.18, 0.6), light=120, check_tile=False)
    TX.add('trim_cyan', TL.solid(CYAN, 4, 4, 64), 'neon', rgb=(0.1, 0.9, 1), light=120, check_tile=False)
    TX.add('trim_violet', TL.solid(VIOLET, 4, 5, 64), 'neon', rgb=(0.55, 0.2, 0.9), light=100, check_tile=False)
    TX.add('metal_dark', TL.metal((70, 74, 86)))
    TX.add('hull_red', TL.solid((150, 30, 40), 4, 7, 128))
    for k, col in enumerate((PINK, CYAN, VIOLET, ORANGE)):
        TX.add(f'dance{k}', dancefloor_tile(col), 'pulse', phase=k * 0.25, freq=1.2, check_tile=False)
    TX.add('laser_grid', grid_glow(256, CYAN, 4), 'raw', check_tile=False, shader=laser_shader('laser_grid'))
    TX.add('laser_grid_p', grid_glow(256, PINK, 4), 'raw', check_tile=False, shader=laser_shader('laser_grid_p'))
    TX.add('sea', sea_tex(), 'raw', check_tile=False, shader=sea_shader())
    TX.add('sea_grid', grid_glow(256, (255, 60, 200), 2, 0.02), 'raw', check_tile=False, shader='')
    TX.add('sign_vhs', TL.neon('VIDEO  HUT', CYAN, 512, 128), 'sign', check_tile=False)
    TX.add('sign_arcade', TL.neon('PIXEL ARCADE', ORANGE, 512, 128), 'sign', check_tile=False)
    TX.add('sign_disco', TL.neon('STARLIGHT DISCO', PINK, 512, 128), 'sign', check_tile=False)
    TX.add('sign_lounge_r', TL.neon('SUNSET LOUNGE', PINK, 512, 128), 'sign', check_tile=False)
    TX.add('sign_lounge_b', TL.neon('LASER LOUNGE', CYAN, 512, 128), 'sign', check_tile=False)
    TX.kit_defaults(pad_rgb=PINK, rubber=(30, 28, 44))
    TX.extra.append(SH.slide_clip())


def super_wall(w=256, h=256):
    """superstructure outer wall, one deck (352u) per tile: white plating, a band of dark blue windows with mullions,
    a hot-pink / cyan pin-stripe under the windows"""
    x, y = xy(w, h)
    c = fill(w, WHITE, 3, 61, h)
    win = (y > 0.30) & (y < 0.62)
    mull = (x * 4) % 1 < 0.05
    glass = lerp(C((30, 40, 90)), C((90, 60, 150)), (1 - (y - 0.30) / 0.32)[..., None])
    c = np.where((win & ~mull)[..., None], glass, c)
    c = np.where((win & mull)[..., None], C((210, 214, 224)), c)
    c = np.where(((y > 0.66) & (y < 0.68))[..., None], C(PINK), c)
    c = np.where(((y > 0.69) & (y < 0.70))[..., None], C(CYAN), c)
    return c


def laser_shader(name):
    t = f'textures/padwave/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
            f'\tsurfaceparm nomarks\n\tpolygonOffset\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n'
            f'\t\trgbGen wave sin 0.7 0.3 0 0.4\n\t\ttcMod scroll 0 0.08\n\t}}\n}}\n\n')


def sea_tex(n=256):
    x, y = xy(n)
    base = C((10, 12, 40)) + N3(n, 6, 3, 6)
    sh = np.clip(noise(n, 2, 5) * 0.5 + 0.2, 0, 1)[..., None] * C((40, 30, 90))
    return base + sh


def sea_shader():
    t = 'textures/padwave/sea'
    g = 'textures/padwave/sea_grid'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n\tsurfaceparm noimpact\n'
            f'\tq3map_globalTexture\n\tdeformVertexes wave 512 sin 0 6 0 0.15\n'
            f'\t{{\n\t\tmap {t}\n\t\trgbGen identity\n\t\ttcMod scale 0.25 0.25\n\t\ttcMod scroll 0 -0.02\n\t}}\n'
            f'\t{{\n\t\tmap {g}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.55 0.3 0.6 )\n\t\ttcMod scale 0.125 0.125\n'
            f'\t\ttcMod scroll 0 -0.05\n\t}}\n}}\n\n')


# ================================================================================================= sky cube
SUN_DIR = (90.0, 6.0)          # yaw toward the sun (bow = +y = 90 deg), elevation


def sky_color(D):
    Dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
    z = Dn[..., 2]
    az = np.degrees(np.arctan2(Dn[..., 1], Dn[..., 0]))
    el = np.degrees(np.arcsin(np.clip(z, -1, 1)))
    # synthwave gradient: orange at the horizon -> magenta -> deep violet -> navy overhead
    t = np.clip(el / 60, 0, 1)
    c = lerp(C((255, 120, 70)), C((220, 40, 140)), np.clip(t * 3, 0, 1)[..., None])
    c = lerp(c, C((70, 20, 110)), np.clip((t - 0.33) * 2.5, 0, 1)[..., None])
    c = lerp(c, C((10, 8, 34)), np.clip((t - 0.7) * 3.3, 0, 1)[..., None])
    # warmer toward the sun's side
    sy = math.radians(SUN_DIR[0])
    facing = np.clip(np.cos(np.radians(az) - sy), 0, 1)
    c = c + (facing ** 2 * np.clip(1 - t * 2, 0, 1))[..., None] * C((40, 20, 0))
    # below the horizon: dark sea with a sun streak
    below = el < 0
    sea = C((12, 10, 36)) + (np.exp(-((az - SUN_DIR[0]) / 4) ** 2) * np.clip(1 + el / 30, 0, 1))[..., None] * C((200, 60, 120))
    c = np.where(below[..., None], sea, c)
    # the striped sun: disc of 13 deg radius centred just above the horizon, bars cut through its lower half
    da = (az - SUN_DIR[0]); de = el - SUN_DIR[1]
    r = np.hypot(da, de)
    inside = (r < 13) & (el > 0)
    sun_col = lerp(C((255, 236, 90)), C((255, 60, 150)), np.clip((SUN_DIR[1] + 13 - el) / 26, 0, 1)[..., None])
    bars = (de < 4) & (np.sin((de + 30) * (1.2 + np.clip(-de, 0, 20) * 0.08)) > 0.55)
    c = np.where((inside & ~bars)[..., None], sun_col, c)
    glow = np.clip(1 - (r - 13) / 18, 0, 1) * (el > -1)
    c = c + (glow ** 2)[..., None] * C((120, 30, 80)) * (~inside)[..., None]
    return c, el, az


def make_sky(out, n=512):
    d = os.path.join(out, 'env', 'padwave'); os.makedirs(d, exist_ok=True)
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    s = 2 * U - 1; t = 1 - 2 * V
    one = np.ones_like(s)
    faces = {'rt': (one, -s, t), 'lf': (-one, s, t), 'bk': (s, one, t), 'ft': (-s, -one, t), 'up': (-t, -s, one), 'dn': (t, -s, -one)}
    rng = np.random.default_rng(9)
    A = np.linspace(-180, 180, 4097)
    # skyline (port, az ~180) and palm islands (starboard-ish), as elevation profiles
    city = np.zeros_like(A)
    x = -150.0
    while x < -100:
        w = rng.uniform(0.6, 2.4); h = rng.uniform(1.0, 4.5) * (1 - abs(x + 125) / 30)
        city = np.where((A > x) & (A < x + w), np.maximum(city, h), city)
        x += w + rng.uniform(0, 0.4)
    isl = np.zeros_like(A)
    for ca in (20, 35, -40, -60, 150, 165):
        isl = np.maximum(isl, 1.2 * np.clip(1 - ((A - ca) / 6) ** 2, 0, 1))
    stars = rng.random((n * 2, n * 2))
    for k, (X, Y, Z) in faces.items():
        D = np.stack([X, Y, Z], -1)
        c, el, az = sky_color(D)
        # stars overhead
        si = (np.clip(((az + 180) / 360) * (2 * n - 1), 0, 2 * n - 1)).astype(int)
        sj = (np.clip((el / 90) * (2 * n - 1), 0, 2 * n - 1)).astype(int)
        st = (stars[sj, si] > 0.9985) & (el > 20)
        c = np.where(st[..., None], C((255, 240, 255)), c)
        # skyline silhouettes with lit windows, palm islands
        ch = np.interp(az, A, city); ih = np.interp(az, A, isl)
        sil = (el >= 0) & (el < np.maximum(ch, ih))
        win = (el < ch) & ((np.floor(az * 9) + np.floor(el * 7)) % 5 == 0)
        c = np.where(sil[..., None], C((16, 8, 30)), c)
        c = np.where((sil & win)[..., None], lerp(C(CYAN), C(PINK), (np.sin(az) * 0.5 + 0.5)[..., None]) * 0.8, c)
        # neon horizon line
        hz = np.exp(-(el / 0.25) ** 2)
        c = c + hz[..., None] * C((255, 80, 200)) * 0.6
        Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(os.path.join(d, f'sunset_{k}.jpg'), quality=90)
    return 'env/padwave/sunset'


# ================================================================================================= model materials
MAT = {}


def mats():
    M = MAT
    M['white'] = TX.material('white', TL.solid(WHITE, 3, 21, 128), shade=40)
    M['white_s'] = TX.material('white_s', TL.solid(WHITE, 3, 22, 128), 'lms', v=0.12, shade=40)
    M['navy'] = TX.material('navy', TL.solid((22, 26, 70), 3, 23, 128), shade=40)
    M['chrome'] = TX.material('chrome', TL.metal(CHROME), 'lms', v=0.35, shade=50)
    M['teak'] = TX.material('teak_m', TL.planks(TEAK, n_planks=4), shade=30)
    M['orange'] = TX.material('orange', TL.solid((255, 110, 30), 4, 24, 128), shade=40)
    M['pink_g'] = TX.material('pink_g', TL.solid(PINK, 2, 25, 64), 'glow')
    M['cyan_g'] = TX.material('cyan_g', TL.solid(CYAN, 2, 26, 64), 'glow')
    M['violet_g'] = TX.material('violet_g', TL.solid(VIOLET, 2, 27, 64), 'glow')
    M['orange_g'] = TX.material('orange_g', TL.solid(ORANGE, 2, 28, 64), 'glow')
    M['pink_p'] = TX.material('pink_p', TL.solid((230, 70, 160), 4, 29, 128), shade=50)
    M['cyan_p'] = TX.material('cyan_p', TL.solid((40, 200, 220), 4, 30, 128), shade=50)
    M['black'] = TX.material('black', TL.solid((18, 18, 24), 3, 31, 128), shade=40)
    M['cushion_p'] = TX.material('cushion_p', TL.stripes((250, 250, 250), (240, 80, 170), 6), shade=60)
    M['cushion_c'] = TX.material('cushion_c', TL.stripes((250, 250, 250), (40, 200, 230), 6), shade=60)
    M['glass'] = TX.material('glass_m', TL.solid((170, 210, 230), 2, 32, 64), 'glass', c='0.08 0.12 0.16')
    M['water_flow'] = TX.material('water_flow', TL.solid((150, 230, 255), 6, 33, 64), 'add', tcmod='scroll 0 -1.2')
    M['slide_in_p'] = TX.material('slide_in_p', TL.stripes((255, 90, 180), (255, 150, 210), 8), shade=60)
    M['slide_in_c'] = TX.material('slide_in_c', TL.stripes((40, 30, 80), (20, 15, 40), 10), shade=60)
    M['tube_body'] = TX.material('tube_body', TL.solid((40, 200, 230), 3, 34, 128), 'lms', v=0.15, shade=60)
    M['flume_body'] = TX.material('flume_body', TL.solid((250, 250, 250), 3, 35, 128), shade=60)
    M['hull'] = TX.material('hull', hull_tex(), shade=40, sample=48)
    M['funnel'] = TX.material('funnel', funnel_tex(), lathe=True, shade=60)
    M['funnel_in'] = TX.material('funnel_in', TL.metal((60, 60, 74)), shade=60)
    M['leaf'] = TX.material('neon_leaf', leaf_tex(), 'glow', two=True)
    M['trunk'] = TX.material('trunk', TL.stripes((90, 60, 120), (130, 90, 170), 10, vertical=False), shade=60)
    M['screen'] = [TX.material(f'screen{k}', arcade_screen(k), 'glow') for k in range(4)]
    M['cab_side'] = TX.material('cab_side', cab_side_tex(), shade=40)
    M['speaker'] = TX.material('speaker', speaker_tex(), shade=40)
    M['lifeboat'] = TX.material('lifeboat', TL.solid((255, 110, 20), 4, 36, 128), shade=50)
    M['logo'] = TX.material('padwave_logo', TL.neon('PADWAVE', PINK, 1024, 256, serif=True), 'glow')
    M['logo_c'] = TX.material('padwave_logo_c', TL.neon('PADWAVE', CYAN, 1024, 256, serif=True), 'glow')
    M['hull_name'] = TX.material('hull_name', TL.label('SS PADWAVE', 1024, 128, (22, 26, 70), (250, 250, 250)), shade=40)
    return M


def hull_tex(w=64, h=512):
    """height-painted hull band (v = 0 at the sheer line going down 1600u): white topsides, a pink + cyan stripe,
    navy below, red antifouling at the waterline"""
    a = np.zeros((h, w, 3), np.float32)
    v = (np.arange(h) + 0.5) / h * 1600                  # units below the sheer
    col = np.zeros((h, 3), np.float32)
    for i, d in enumerate(v):
        if d < 380: c = WHITE
        elif d < 410: c = PINK
        elif d < 430: c = (240, 240, 250)
        elif d < 460: c = CYAN
        elif d < 1500: c = (22, 26, 70)
        else: c = (150, 30, 40)
        col[i] = c
    a[:] = col[:, None, :]
    return a + N3(w, 1, 5, 3, h)


def funnel_tex(w=256, h=1024):
    """funnel skin, v along the profile (bottom -> top before the lathe flip): white with a navy cap band and the pink /
    cyan / violet stripes; the logo is a separate glow quad"""
    a = np.zeros((h, w, 3), np.float32) + C(WHITE)
    t = (np.arange(h) + 0.5) / h
    for (t0, t1, c) in ((0.0, 0.03, (40, 40, 60)), (0.80, 0.83, PINK), (0.85, 0.88, VIOLET), (0.90, 0.93, CYAN), (0.95, 1.0, NAVY)):
        a[(t >= t0) & (t < t1)] = C(c)
    return a + N3(w, 1, 7, 3, h)


def leaf_tex(n=128):
    x, y = xy(n)
    vein = np.abs(x - 0.5) < 0.04
    edge = np.clip(1 - np.abs(x - 0.5) * 2, 0, 1)
    c = lerp(C((20, 120, 90)), C((60, 255, 180)), edge[..., None]) * (0.6 + 0.4 * (1 - y[..., None]))
    return np.where(vein[..., None], C((200, 255, 240)), c)


def arcade_screen(k, n=128):
    rng = np.random.default_rng(40 + k)
    a = np.zeros((n, n, 3), np.float32) + C((6, 6, 20))
    cols = [PINK, CYAN, ORANGE, (250, 230, 60), (120, 255, 120)]
    for i in range(30):
        x0, y0 = rng.integers(8, n - 16, 2); s = rng.integers(3, 9)
        a[y0:y0 + s, x0:x0 + s] = C(cols[rng.integers(5)])
    a[n - 12:n - 6, 8:n - 8] = C(cols[k % 5])
    return a


def cab_side_tex(n=128):
    x, y = xy(n)
    c = np.zeros((n, n, 3), np.float32) + C((30, 20, 60))
    stripe = (np.abs((x + y * 0.6) % 0.5 - 0.25) < 0.05)
    return np.where(stripe[..., None], C(PINK), c) + N3(n, 1, 8, 3)


def speaker_tex(n=128):
    x, y = xy(n)
    r = np.hypot(x - 0.5, y - 0.5)
    c = np.zeros((n, n, 3), np.float32) + C((24, 24, 30))
    c = np.where((r < 0.42)[..., None], C((40, 40, 48)) - (np.sin(r * 90) > 0.6)[..., None] * 10, c)
    c = np.where((r < 0.14)[..., None], C((70, 70, 80)), c)
    return c


# ================================================================================================= MD3 models
def hull_model(outline, skin_holes=None):
    """the ship's hull skin in world coordinates: outline = plan polygon at the sheer line (z 0) counter-clockwise; the
    sides fall to the sea with a gentle tumblehome. skin_holes(x, y, z) -> True skips a cell (the Sky Pool cut-out)."""
    X = ML.Model()
    m = X.mesh(MAT['hull'])
    P = densify(outline + [outline[0]], 96)
    P = [np.asarray(p, float) for p in P]
    zs = [4, -100, -216, -300, -450, -700, -1000, -1300, -1560]
    cen = np.mean(outline, 0)
    perim = np.concatenate([[0], np.cumsum([np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)])])
    for i in range(len(zs) - 1):
        za, zb = zs[i], zs[i + 1]
        for j in range(len(P) - 1):
            a, b = P[j], P[j + 1]
            mid = (a + b) / 2
            if skin_holes and skin_holes(mid[0], mid[1], (za + zb) / 2): continue
            def sh(p, z):
                k = 1 - 0.035 * max(0.0, -z / 1560) ** 1.5          # slight tumblehome toward the keel
                q = cen + (p - cen) * k
                return np.array([q[0], q[1], z])
            pa, pb, pc, pd = sh(a, za), sh(b, za), sh(b, zb), sh(a, zb)
            e = b - a; n = np.array([e[1], -e[0], 0.0]); n /= max(1e-9, np.linalg.norm(n))
            ua, ub = perim[j] / 256.0, perim[j + 1] / 256.0
            m.poly([pa, pb, pc, pd], n, [(ua, -za / 1600), (ub, -za / 1600), (ub, -zb / 1600), (ua, -zb / 1600)])
    # gunwale cap: a thin white rail strip all round the sheer
    w = X.mesh(MAT['white'])
    for j in range(len(P) - 1):
        a, b = P[j], P[j + 1]
        e = b - a; n = np.array([e[1], -e[0], 0.0]); n /= max(1e-9, np.linalg.norm(n))
        if skin_holes and skin_holes((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 2): continue
        w.poly([(a[0], a[1], 4), (b[0], b[1], 4), (b[0] - n[0] * 12, b[1] - n[1] * 12, 4), (a[0] - n[0] * 12, a[1] - n[1] * 12, 4)],
               (0, 0, 1), [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
    return X


def hull_names(X, s):
    """SS PADWAVE on both sides near this half's end (world coordinates)"""
    for side in (-1, 1):
        y = s * 1500
        picture(X.mesh(MAT['hull_name']), (side * (L.HX + 9), y, -220), 900, 112, (side, 0, 0))
    return X


def funnel():
    """the Padwave Funnel: hollow lathe (outer white with stripes, dark inner), door cut-outs bow and stern, neon rings
    and a PADWAVE logo on both sides (port / starboard). Origin = deck centre."""
    X = ML.Model()
    H = L.CROWN - 16
    prof = [(L.FUN_R0, 0), (L.FUN_R0 - 6, 200), (L.FUN_R0 - 14, 500), (L.FUN_R0 - 22, 800), (L.FUN_R1, H)]
    hw, dh = L.FUN_DOOR

    def holes(a_deg, z):
        if z > dh: return False
        for door_a in (90, 270):
            da = (a_deg - door_a + 180) % 360 - 180
            if abs(math.radians(da)) * L.FUN_R0 < hw: return True
        return False
    pz = [p[1] for p in prof]; pr = [p[0] for p in prof]
    zs = sorted(set([round(z, 2) for z in np.linspace(0, dh, 5)] + [round(z, 2) for z in np.linspace(dh, H, 24)]))
    rows = [(float(np.interp(z, pz, pr)), z) for z in zs]
    ML.lathe(X.mesh(MAT['funnel']), rows, n=64, holes=holes, u_tiles=1, vlen=H)
    inner = [(r - L.FUN_T, z) for r, z in rows]
    ML.lathe(X.mesh(MAT['funnel_in']), inner, n=64, holes=holes, inward=True, u_tiles=8, vlen=256)
    # door jambs + lintels
    for door_a in (90, 270):
        for sgn in (-1, 1):
            a = math.radians(door_a) + sgn * hw / L.FUN_R0
            o = np.array([math.cos(a), math.sin(a)])
            p0, p1 = o * L.FUN_R0, o * (L.FUN_R0 - L.FUN_T)
            n = np.array([-math.sin(a), math.cos(a), 0]) * -sgn
            X.mesh(MAT['funnel_in']).poly([(p0[0], p0[1], 0), (p1[0], p1[1], 0), (p1[0], p1[1], dh), (p0[0], p0[1], dh)], n,
                                          [(0, 0), (0.2, 0), (0.2, 1), (0, 1)])
        a0 = math.radians(door_a) - hw / L.FUN_R0; a1 = math.radians(door_a) + hw / L.FUN_R0
        for k in range(6):
            ta, tb = a0 + (a1 - a0) * k / 6, a0 + (a1 - a0) * (k + 1) / 6
            pts = [(r * math.cos(t), r * math.sin(t), dh) for (r, t) in ((L.FUN_R0, ta), (L.FUN_R0, tb), (L.FUN_R0 - L.FUN_T, tb), (L.FUN_R0 - L.FUN_T, ta))]
            X.mesh(MAT['funnel_in']).poly(pts, (0, 0, -1), [(0, 0), (1, 0), (1, 0.2), (0, 0.2)])
        # neon frame round the door
        c = MAT['pink_g'] if door_a == 90 else MAT['cyan_g']
        for sgn in (-1, 1):
            a = math.radians(door_a) + sgn * (hw + 6) / L.FUN_R0
            tube(X.mesh(c), [(L.FUN_R0 * 1.01 * math.cos(a), L.FUN_R0 * 1.01 * math.sin(a), 2),
                             (L.FUN_R0 * 1.01 * math.cos(a), L.FUN_R0 * 1.01 * math.sin(a), dh + 6)], 3, nseg=6)
    # neon rings round the funnel
    for z, key in ((H * 0.62, 'pink_g'), (H * 0.66, 'violet_g'), (H * 0.70, 'cyan_g')):
        r = np.interp(z, [p[1] for p in prof], [p[0] for p in prof]) + 3
        torus(X.mesh(MAT[key]), (0, 0, z), r, 4, n=64, m=6)
    # logos: port reads pink, starboard cyan
    for side, key in ((-1, 'logo'), (1, 'logo_c')):
        z = H * 0.45; r = np.interp(z, [p[1] for p in prof], [p[0] for p in prof]) + 2
        picture(X.mesh(MAT[key]), (side * r, 0, z), 420, 105, (side, 0, 0))
    return ML.save('funnel', X)


def crown():
    """crown deck on top of the funnel: teak ring round the lift hole, chrome rim, neon edge. Origin = deck top."""
    X = ML.Model()
    annulus(X.mesh(MAT['teak']), 0, 0, L.CROWN_HOLE, L.CROWN_R, 0, n=64, tile=128)
    revolve(X.mesh(MAT['chrome']), [(L.CROWN_R, 0), (L.CROWN_R, -16)], n=64, vlen=32)
    revolve(X.mesh(MAT['pink_g']), [(L.CROWN_R + 0.5, -4), (L.CROWN_R + 0.5, -10)], n=64, vlen=32)
    revolve(X.mesh(MAT['chrome']), [(L.CROWN_HOLE, -16), (L.CROWN_HOLE, 0)], n=32, vlen=32, inward=True)
    revolve(X.mesh(MAT['cyan_g']), [(L.CROWN_HOLE - 0.5, -2), (L.CROWN_HOLE - 0.5, -8)], n=32, vlen=32, inward=True)
    return ML.save('crown', X)


def lifeboat():
    """orange lifeboat 320 long x 120 wide on two chocks, an open cabin roof and a stern door. Faces +y (bow), origin =
    deck centre. Collision boxes: LIFEBOAT_BOXES."""
    X = ML.Model()
    o = MAT['lifeboat']; w = MAT['white']
    Lh, Wh = 160, 60
    # hull: two half shells (lofted ellipse halves) from the gunwale (z 70) down to the keel (z 16)
    for x0, x1 in ((-Wh, -Wh + 8), (Wh - 8, Wh)):
        boxm(X.mesh(o), (x0, -Lh + 10, 16), (x1, Lh - 30, 72), r=3, tile=64)
    boxm(X.mesh(o), (-Wh, Lh - 30, 16), (Wh, Lh, 72), r=12, tile=64)          # bow
    boxm(X.mesh(o), (-Wh + 8, -Lh + 10, 8), (Wh - 8, Lh - 30, 16), r=2, tile=64)  # floor
    boxm(X.mesh(w), (-Wh - 2, -Lh + 6, 72), (Wh + 2, Lh + 2, 78), r=2, tile=64)   # gunwale
    # cabin roof on posts (open sides)
    boxm(X.mesh(o), (-Wh + 4, -Lh + 40, 150), (Wh - 4, Lh - 50, 160), r=8, tile=64)
    for x in (-Wh + 10, Wh - 10):
        for y in (-Lh + 46, Lh - 56):
            tube(X.mesh(MAT['chrome']), [(x, y, 78), (x, y, 150)], 3, nseg=6)
    # chocks
    for y in (-90, 90):
        boxm(X.mesh(MAT['navy']), (-Wh + 6, y - 14, 0), (Wh - 6, y + 14, 16), r=1, tile=64)
    # stern door frame (the open stern)
    boxm(X.mesh(o), (-Wh, -Lh, 16), (-Wh + 16, -Lh + 10, 72), r=1, tile=64)
    boxm(X.mesh(o), (Wh - 16, -Lh, 16), (Wh, -Lh + 10, 72), r=1, tile=64)
    return ML.save('lifeboat', X)


LIFEBOAT_BOXES = [((-60, -150, 0), (-52, 130, 78)), ((52, -150, 0), (60, 130, 78)), ((-60, 130, 0), (60, 160, 78)),
                  ((-52, -150, 0), (52, 130, 16)), ((-56, -110, 150), (56, 110, 160))]


def lounger(cush):
    """sun lounger 76 long (chrome frame, striped cushion, raised back). Origin = floor centre, faces +y."""
    X = ML.Model()
    boxm(X.mesh(MAT[cush]), (-14, -38, 12), (14, 18, 17), r=2, tile=32)
    v = Mesh(); boxm(v, (-14, 0, 0), (14, 26, 5), r=2, tile=32)
    a = math.radians(40); R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    X.mesh(MAT[cush]).add(v, R, (0, 18, 15))
    for x in (-12, 12):
        tube(X.mesh(MAT['chrome']), [(x, -36, 0), (x, -36, 12), (x, 16, 12), (x, 16, 0)], 1.2, nseg=6)
    return ML.save(f'lounger_{cush}', X)


def palm(name, leaf=None):
    """neon palm in a chrome planter: violet ringed trunk, glowing fronds (additive look). Origin = floor centre."""
    X = ML.Model()
    revolve(X.mesh(MAT['chrome']), [(0, 0), (40, 0), (46, 48), (40, 52), (0, 52)][:4] + [(0, 52)], n=24, vlen=64)
    disc(X.mesh(MAT['black']), 40, 50, up=True, n=24)
    path = [(0, 0, 50), (6, 2, 120), (14, 4, 190), (24, 6, 250)]
    tube(X.mesh(MAT['trunk']), path, [9, 8, 7, 6], nseg=10)
    top = np.array(path[-1], float)
    lm = X.mesh(MAT[leaf or 'leaf'])
    for k in range(9):
        a = k * 40 + 10
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0])
        side = np.array([-d[1], d[0], 0])
        o = len(lm.V)
        for i in range(7):
            t = i / 6
            p = top + d * 90 * t + np.array([0, 0, 22 * t - 60 * t * t])
            wdt = 14 * math.sin(math.pi * min(1, t * 1.1 + 0.05))
            for sg in (-1, 1):
                lm.add_v(p + side * sg * wdt, (0, 0, 1), ((sg + 1) / 2, t))
        for i in range(6):
            b = o + 2 * i
            lm.tri(b, b + 1, b + 2); lm.tri(b + 1, b + 3, b + 2)
    return ML.save(name, X)


PALM_CYL = [(0, 0, 40, 0, 52), (6, 2, 10, 52, 240)]


def arcade_cabinet(k):
    """upright arcade cabinet 48 x 40 x 120 with a glowing screen + marquee. Faces +y, origin floor centre."""
    X = ML.Model()
    s = MAT['cab_side']
    boxm(X.mesh(s), (-24, -20, 0), (24, 20, 62), r=1, tile=64)
    boxm(X.mesh(s), (-24, -20, 62), (24, 6, 104), r=1, tile=64)
    boxm(X.mesh(s), (-24, -20, 104), (24, 14, 120), r=1, tile=64)
    boxm(X.mesh(MAT['black']), (-22, 18, 56), (22, 26, 62), r=1, tile=32)          # control panel
    for x in (-10, 8):
        sphere(X.mesh(MAT['pink_g' if k % 2 else 'cyan_g']), (x, 22, 66), 2.5, nu=8, nv=5)
    picture(X.mesh(MAT['screen'][k % 4]), (0, 6.5, 84), 38, 34, (0, 1, 0.25))
    picture(X.mesh(MAT['orange_g' if k % 2 else 'pink_g']), (0, 14.5, 112), 44, 12, (0, 1, 0))
    return ML.save(f'arcade{k}', X)


CAB_BOX = [((-24, -20, 0), (24, 20, 118))]


def speaker_stack():
    """DJ speaker stack 96 wide x 64 deep x 192 tall, two big woofers facing +y. Origin floor centre."""
    X = ML.Model()
    boxm(X.mesh(MAT['black']), (-48, -32, 0), (48, 32, 192), r=3, tile=64)
    for z in (48, 144):
        picture(X.mesh(MAT['speaker']), (0, 32.5, z), 84, 84, (0, 1, 0))
    torus(X.mesh(MAT['pink_g']), (0, 33, 96), 46, 2, axis=(0, 1, 0), n=32, m=5)
    return ML.save('speaker_stack', X)


SPK_BOX = [((-46, -30, 0), (46, 30, 190))]


def dj_booth():
    """DJ booth 256 wide x 96 deep x 64 tall: chrome front with a neon wave, decks + mixer on top. Faces +y."""
    X = ML.Model()
    boxm(X.mesh(MAT['black']), (-128, -48, 0), (128, 48, 64), r=4, tile=64)
    boxm(X.mesh(MAT['chrome']), (-130, 46, 4), (130, 50, 60), r=1, tile=64)
    pts = [(x, 51, 32 + 14 * math.sin(x / 20)) for x in range(-120, 121, 12)]
    tube(X.mesh(MAT['pink_g']), pts, 2.5, nseg=6)
    for x in (-70, 70):
        revolve(X.mesh(MAT['chrome']), [(0, 64), (26, 64), (26, 68), (0, 68)], n=20, cx=x, cy=0, vlen=32)
        disc(X.mesh(MAT['black']), 24, 68.2, n=20, cx=x, cy=0)
    boxm(X.mesh(MAT['navy']), (-24, -20, 64), (24, 20, 72), r=1, tile=32)
    return ML.save('dj_booth', X)


DJ_BOX = [((-126, -46, 0), (126, 46, 64))]


def bar_counter(name, length, glow):
    """curved-front pool bar: white counter with a neon strip and chrome foot rail, bottles glowing behind. Faces +y,
    origin floor centre; length along x."""
    X = ML.Model()
    h = length / 2
    boxm(X.mesh(MAT['white_s']), (-h, -32, 0), (h, 32, 64), r=10, tile=128)
    boxm(X.mesh(MAT['teak']), (-h - 4, -36, 64), (h + 4, 40, 70), r=3, tile=128)
    tube(X.mesh(MAT[glow]), [(-h + 8, 33, 40), (h - 8, 33, 40)], 2.5, nseg=6)
    tube(X.mesh(MAT['chrome']), [(-h + 8, 44, 10), (h - 8, 44, 10)], 2.5, nseg=6)
    for i, x in enumerate(np.arange(-h + 30, h - 20, 26)):
        sphere(X.mesh(MAT[['pink_g', 'cyan_g', 'orange_g', 'violet_g'][i % 4]]), (x, -20, 76), 5, nu=8, nv=5)
        tube(X.mesh(MAT['glass']), [(x, -20, 70), (x, -20, 92)], 4, nseg=8)
    return ML.save(name, X)


def stool():
    X = ML.Model()
    revolve(X.mesh(MAT['chrome']), [(0, 0), (14, 0), (14, 2), (3, 4), (3, 40), (0, 40)], n=16, vlen=32)
    revolve(X.mesh(MAT['pink_p']), [(0, 40), (12, 40), (12, 46), (0, 46)], n=16, vlen=32)
    return ML.save('stool', X)


def cabana(name, cush):
    """striped cabana 160 x 160: four chrome posts, a peaked canopy, a day bed inside. Origin floor centre."""
    X = ML.Model()
    for x in (-76, 76):
        for y in (-76, 76):
            tube(X.mesh(MAT['chrome']), [(x, y, 0), (x, y, 150)], 3, nseg=6)
    can = X.mesh(MAT[cush])
    apex = (0, 0, 196)
    corners = [(-84, -84, 150), (84, -84, 150), (84, 84, 150), (-84, 84, 150)]
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        nn = np.cross(np.subtract(b, a), np.subtract(apex, a)); nn = nn / np.linalg.norm(nn)
        can.poly([a, b, apex], nn, [(0, 1), (1, 1), (0.5, 0)])
        can.poly([apex, b, a], -nn, [(0.5, 0), (1, 1), (0, 1)])
    boxm(X.mesh(MAT['white']), (-64, -56, 0), (64, 56, 24), r=6, tile=64)
    boxm(X.mesh(MAT[cush]), (-60, -52, 24), (60, 52, 30), r=4, tile=64)
    return ML.save(name, X)


CABANA_BOX = [((-62, -54, 0), (62, 54, 28))]
CABANA_CYL = [(x, y, 6, 0, 150) for x in (-76, 76) for y in (-76, 76)]


def flamingo():
    """giant inflatable flamingo pool float (sits on deck), 140 long. Origin floor centre."""
    X = ML.Model()
    p = MAT['pink_p']
    torus(X.mesh(p), (0, 0, 16), 48, 16, n=24, m=10)
    tube(X.mesh(p), [(0, 48, 20), (0, 56, 60), (0, 52, 100), (0, 66, 110)], [12, 9, 8, 8], nseg=10)
    sphere(X.mesh(p), (0, 70, 112), 12, nu=12, nv=8)
    tube(X.mesh(MAT['black']), [(0, 80, 112), (0, 92, 104)], [5, 2], nseg=8)
    return ML.save('flamingo', X)


def donut_float():
    X = ML.Model()
    torus(X.mesh(MAT['cushion_p']), (0, 0, 16), 40, 16, n=24, m=10)
    return ML.save('donut_float', X)


def neon_sign_board(name, key, w, h):
    """wall sign: black backing board with a glowing text face, faces +y, origin bottom centre"""
    X = ML.Model()
    boxm(X.mesh(MAT['black']), (-w / 2 - 6, -6, 0), (w / 2 + 6, 0, h + 12), r=1, tile=64)
    picture(X.mesh(MAT[key]), (0, 0.5, h / 2 + 6), w, h, (0, 1, 0))
    return ML.save(name, X)


def sky_pool_glass():
    """the Sky Pool's glass tank in world coordinates (bow/stern symmetric): glass floor, outboard wall and ends, chrome
    frame. Collision is separate (weapclip brushes in the builder)."""
    X = ML.Model()
    g = MAT['glass']; ch = MAT['chrome']
    x0, x1, hy, zf = L.SP['x0'], L.SP['x1'], L.SP['hy'], L.SP['floor']
    X.mesh(g).quad((x0, -hy, zf), (x1, -hy, zf), (x1, hy, zf), (x0, hy, zf), tile=128, n=(0, 0, -1))
    X.mesh(g).quad((x1, -hy, zf), (x1, hy, zf), (x1, hy, 48), (x1, -hy, 48), tile=128, n=(1, 0, 0))
    for sy in (-1, 1):
        X.mesh(g).quad((x0, sy * hy, zf), (x1, sy * hy, zf), (x1, sy * hy, 48), (x0, sy * hy, 48), tile=128, n=(0, sy, 0))
    for (a, b) in (((x1, -hy, zf), (x1, hy, zf)), ((x1, -hy, 48), (x1, hy, 48)), ((x1, -hy, zf), (x1, -hy, 48)),
                   ((x1, hy, zf), (x1, hy, 48)), ((x0, -hy, zf), (x1, -hy, zf)), ((x0, hy, zf), (x1, hy, zf)),
                   ((x0, -hy, 48), (x1, -hy, 48)), ((x0, hy, 48), (x1, hy, 48))):
        tube(X.mesh(ch), [a, b], 5, nseg=8)
    for y in np.linspace(-hy, hy, 5)[1:-1]:
        tube(X.mesh(ch), [(x0, y, zf), (x1, y, zf)], 3, nseg=6)
    # under-lights
    for y in np.linspace(-hy + 60, hy - 60, 4):
        sphere(X.mesh(MAT['cyan_g']), ((x0 + x1) / 2, y, zf - 6), 6, nu=8, nv=5)
    return X


def make_all():
    mats()
    funnel(); crown(); lifeboat()
    lounger('cushion_p'); lounger('cushion_c')
    palm('palm_p', 'leaf');
    for k in range(4): arcade_cabinet(k)
    speaker_stack(); dj_booth(); stool()
    bar_counter('bar_p', 384, 'pink_g'); bar_counter('bar_c', 384, 'cyan_g'); bar_counter('bar_lounge', 640, 'violet_g')
    cabana('cabana_p', 'cushion_p'); cabana('cabana_c', 'cushion_c')
    flamingo(); donut_float()
