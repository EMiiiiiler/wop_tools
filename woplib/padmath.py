"""Jump pad maths for WoP / Quake 3 (pure functions, no map state).

Q3 AimAtTarget (g_trigger.c): the pad aims from the CENTRE of the trigger_push brush and the target_position is the
APEX of the arc.  t_up = sqrt(2*(apex - origin_z)/g); horizontal speed = horizontal distance to the target / t_up.
After the apex the player keeps that horizontal speed while falling, so a target placed straight over the landing
spot overshoots: put it at t_up / (t_up + t_down) of the way instead.

Rules learned on ~20 maps (see SKILL.md section 7):
  * total flight time under ~2.9 s, or bspc makes no reachability (bots never use the pad)
  * apex at least ~20u above any edge the arc crosses (bspc is stricter than the game)
  * under a ceiling: apex <= ceiling - 40
  * a landing within (trigger_hurt radius + 15) of a hurt zone is a lava area for bspc
  * pad_check can pass pads bspc does not link; +60-70u of apex usually fixes that
"""
import math

GRAVITY = 800.0
PLAYER_Z = 24.0           # standing player origin above the floor
MAX_FLIGHT = 2.9          # bspc predicts flights up to ~3 s


def t_fall(h):
    """seconds to fall (or rise) h units from/to rest"""
    return math.sqrt(2.0 * max(h, 0.0) / GRAVITY)


def pad_velocity(origin, target):
    """launch velocity of a Q3 trigger_push aimed at target_position `target` from trigger centre `origin`"""
    h = target[2] - origin[2]
    if h <= 0: raise ValueError('target_position must be above the trigger centre')
    t = math.sqrt(h / (0.5 * GRAVITY))
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    dist = math.hypot(dx, dy)
    vh = dist / t
    if dist < 1e-6: return (0.0, 0.0, t * GRAVITY)
    return (dx / dist * vh, dy / dist * vh, t * GRAVITY)


def pad_target(origin, land, apex):
    """(x, y) of the target_position so a pad fired from trigger centre `origin` peaks at `apex` and comes down on the
    floor point `land` (x, y, floor_z)"""
    tu = t_fall(apex - origin[2])
    td = t_fall(apex - (land[2] + PLAYER_Z))
    f = tu / (tu + td)
    return origin[0] + (land[0] - origin[0]) * f, origin[1] + (land[1] - origin[1]) * f


def flight_time(origin_z, apex, land_floor):
    return t_fall(apex - origin_z) + t_fall(apex - (land_floor + PLAYER_Z))


def arc(origin, target, land_floor=None, dt=0.008, tmax=4.0):
    """points of the flight (player origin) until it falls below land_floor + 24 (or tmax)"""
    vx, vy, vz = pad_velocity(origin, target)
    x, y, z = origin
    pts = [(x, y, z)]
    t = 0.0
    zstop = None if land_floor is None else land_floor + PLAYER_Z
    while t < tmax:
        t += dt
        x += vx * dt; y += vy * dt
        vz -= GRAVITY * dt; z += vz * dt
        pts.append((x, y, z))
        if zstop is not None and vz < 0 and z <= zstop: break
    return pts


def plan(pad_floor, pad_xy, land, apex, ceiling=None, edges=(), trigger_h=64):
    """Check a pad design before placing it.  pad_floor/pad_xy: where the pad sits; land = (x, y, floor);
    edges = [(x, y, z_top), ...] ledges the arc must clear.  Returns dict(target, t, origin, warnings)."""
    oz = pad_floor + 6 + trigger_h / 2.0          # trigger centre (pad disc 6u, trigger 64u tall)
    o = (pad_xy[0], pad_xy[1], oz)
    w = []
    if apex <= max(oz, land[2] + PLAYER_Z) + 8:
        w.append('apex must be above both the pad and the landing (+8)')
        return dict(target=None, t=None, origin=o, warnings=w)
    tx, ty = pad_target(o, land, apex)
    t = flight_time(oz, apex, land[2])
    if t > MAX_FLIGHT: w.append(f'flight {t:.2f} s > {MAX_FLIGHT} s: bspc will not link it (lower the apex or shorten the hop)')
    if ceiling is not None and apex > ceiling - 40: w.append(f'apex {apex:g} closer than 40u to the ceiling {ceiling:g}')
    if edges:
        pts = arc(o, (tx, ty, apex), land[2])
        for (ex, ey, ez) in edges:
            best = min(pts, key=lambda p: (p[0] - ex) ** 2 + (p[1] - ey) ** 2)
            if best[2] - 24 < ez + 20:
                w.append(f'arc feet {best[2] - 24:.0f} over edge ({ex:g},{ey:g}) top {ez:g}: want >= 20u clearance')
    return dict(target=(round(tx), round(ty), round(apex)), t=round(t, 2), origin=o, warnings=w)
