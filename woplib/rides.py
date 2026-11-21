"""woplib.rides - fairground rides any map can reuse (first used on wop_padfunfair).

    from woplib import rides
    rides.wheel_gondolas(K, 'wheel', hub=(x, y, z), R=700, n=8, place=ML.PLACE['gondola'], speed=60)
        big-wheel gondolas that stay LEVEL: one func_train per gondola on a shared loop of path_corners round the wheel
        (a func_rotating would tip riders upside down). Each has an origin brush at its hanger pin, a weapclip floor and
        low walls open on the boarding side, and the gondola MD3 as model2. Spin the rims/spokes separately with
        K.rotating_model2(..., axis='y' or 'x').
    rides.carousel_deck(K, 'carousel', c, r_in, r_out, z_base, place, speed=18)
        a rotating ring deck you ride (func_rotating, weapclip wedge sectors + model2 with the horses). Build a static
        base disc under it (z_base - 16 .. z_base) yourself: bspc ignores movers, so bots walk on the base.
    rides.helix(c, r, z0, z1, turns, a0=0, n_per_turn=24) -> points for K.slide (helter-skelter / spiral flumes)

Rules baked in:
  * movers take an origin brush and NO origin key; WoP common/nodraw is nonsolid (collision is weapclip)
  * a blocked func_train pauses (no crush) and a rotating pusher never crushes, so riders are safe; keep every mover's
    sweep free of static solids (check with sweep_points()).
"""
import math
import numpy as np
from wopmap import box, hull
from .kit import WCLIP, ORIGIN


def wheel_gondolas(K, name, hub, R, n, place, speed=60.0, n_corners=32, plane='x', half=(80, 90), drop=150.0,
                   floor_t=12.0, wall_h=36.0, open_side='-y', phase_deg=0.0):
    """n level gondolas round a big wheel. hub = (x, y, z) of the axle; the wheel turns in the vertical plane that
    contains `plane` ('x' or 'y'). The gondola hangs `drop` below its pin: its floor top is at pin - drop.
    half = (half length along the wheel plane, half depth across it). open_side: the side left open for boarding.
    Returns dict(corners=[...], sweep=(r_min, r_max), floor_drop=drop)."""
    hx, hy, hz = hub
    def pin(a):
        a = math.radians(a)
        u, v = R * math.cos(a), hz + R * math.sin(a)
        return (hx + u, hy, v) if plane == 'x' else (hx, hy + u, v)
    names = [f'{name}_c{k}' for k in range(n_corners)]
    for k in range(n_corners):
        a = phase_deg - 360.0 * k / n_corners                     # clockwise seen from -y
        K.M.ent('path_corner', tuple(round(c, 1) for c in pin(a)), targetname=K.uniq(names[k]),
                target=names[(k + 1) % n_corners])
    step = n_corners // n
    hl, hd = half
    for g in range(n):
        k0 = g * step
        p = pin(phase_deg - 360.0 * k0 / n_corners)
        ft = p[2] - drop
        L = (hl, hd) if plane == 'x' else (hd, hl)
        bx = lambda x0, y0, z0, x1, y1, z1: box((p[0] + x0, p[1] + y0, z0), (p[0] + x1, p[1] + y1, z1), WCLIP)
        brushes = [box((p[0] - 8, p[1] - 8, p[2] - 8), (p[0] + 8, p[1] + 8, p[2] + 8), ORIGIN),
                   bx(-L[0], -L[1], ft - floor_t, L[0], L[1], ft)]
        walls = {'+x': bx(L[0] - 6, -L[1], ft, L[0], L[1], ft + wall_h), '-x': bx(-L[0], -L[1], ft, -L[0] + 6, L[1], ft + wall_h),
                 '+y': bx(-L[0] + 6, L[1] - 6, ft, L[0] - 6, L[1], ft + wall_h), '-y': bx(-L[0] + 6, -L[1], ft, L[0] - 6, -L[1] + 6, ft + wall_h)}
        for side, b in walls.items():
            if side != open_side: brushes.append(b)
        K.ent('func_train', brushes=brushes, target=names[k0], speed=speed, model2=place[0], dmg=0)
        K.spots['movers'].append(dict(cls='func_train', centre=[round(v) for v in p], model=place[0], ride=name))
    return dict(corners=names, sweep=(R - max(hl, hd) - drop, R + max(hl, hd) + drop), floor_drop=drop)


def carousel_deck(K, name, c, r_in, r_out, z_base, place, speed=18.0, thick=16.0, n=16, reverse=False):
    """rotating ring deck (top at z_base + thick) as n weapclip wedge sectors on one func_rotating with model2 = place
    (horses, poles, deck boards; origin at the deck centre, z 0 = deck top)."""
    cx, cy = c
    zt = z_base + thick
    brushes = [box((cx - 6, cy - 6, zt - 6), (cx + 6, cy + 6, zt + 6), ORIGIN)]
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        pts = []
        for a in (a0, a1):
            for r in (r_in, r_out):
                pts += [(cx + r * math.cos(a), cy + r * math.sin(a), z_base), (cx + r * math.cos(a), cy + r * math.sin(a), zt)]
        brushes.append(hull(pts, WCLIP, round_pts=False))
    K.ent('func_rotating', brushes=brushes, model2=place[0], speed=speed, spawnflags=2 if reverse else 0, dmg=0)
    K.spots['movers'].append(dict(cls='func_rotating', centre=[round(cx), round(cy), round(zt)], model=place[0], ride=name))
    K.occupy_r(cx, cy, r_out + 8, z_base, zt + 300)


def helix(c, r, z0, z1, turns, a0=0.0, n_per_turn=24, ccw=True):
    """points of a helix descending from z0 (at angle a0) to z1 round centre c - feed to K.slide / ML.flume"""
    n = max(2, int(turns * n_per_turn))
    out = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (1 if ccw else -1) * 360.0 * turns * t)
        out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z0 + (z1 - z0) * t))
    return out


def sweep_points(K, pts, r, z0, z1):
    """static solid brushes that come within r of any point (x, y) between z0 and z1 - for checking a ride's path"""
    hits = []
    for b in K.M.world:
        if not b.is_solid(): continue
        ts = b.textures()
        if all(any(h in (t or '') for h in ('trigger', 'clip', 'nodraw_ns', 'origin', 'water')) for t in ts): continue
        mn, mx = b.bounds()
        if mx[2] <= z0 or mn[2] >= z1: continue
        for (x, y) in pts:
            if mn[0] - r < x < mx[0] + r and mn[1] - r < y < mx[1] + r:
                hits.append((round(x), round(y), tuple(np.round(mn).astype(int)))); break
    return hits
