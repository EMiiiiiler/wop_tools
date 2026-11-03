"""woplib.kit - MapKit: everything a WoP map generator kept re-implementing (promoted from padbakery/build_bakery.py).

    from woplib.kit import MapKit
    K = MapKit('wop_padfoo', 'padfoo', 'Pretty Name', bounds=(-2304, -2048, 2304, 2048))
    K.add(box(...))                                   # world brushes (wopmap)
    K.reserve(brush_or_bounds)                        # mark architecture as occupied before scattering props
    K.catalog('pad_ducks/pad_duck.md3', x, y, z, 0.3) # catalog model on surface z, nudged to free space, weapclip box
    K.weapon('imperius', x, y, floor, marker='purple'); K.ammo('imperius', x, y, floor)
    K.jumppad(x, y, z, land=(lx, ly, lfloor), apex=900, name='pad_roof')
    K.secret(entry_mn, entry_mx, dest=(x, y, floor), angle=90, name='vault')
    K.route('stair_n', (x0, y0, floor0), (x1, y1, floor1))
    K.write(out_dir)                                  # maps/<map>.map + maps/<map>.spots.json + routes.txt

Every helper encodes a rule that broke an earlier map; the reasons are in the docstrings and in SKILL.md.
"""
import os, sys, math, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import wopmap
from wopmap import Map, box, cyl, hull, prism, stairs, fmt
from . import padmath, wopdata

CAULK = 'common/caulk'; CLIP = 'common/clip'; WCLIP = 'common/weapclip'; BOTCLIP = 'common/botclip'
TRIG = 'common/trigger'; ORIGIN = 'common/origin'; NODRAW = 'common/nodraw'

_BOUNDS = None


def md3bounds():
    global _BOUNDS
    if _BOUNDS is None: _BOUNDS = json.load(open(os.path.join(ROOT, 'md3bounds.json')))
    return _BOUNDS


class MapKit:
    def __init__(self, mapname, ns, longname, bounds, worldspawn=None, seed=1):
        assert mapname == mapname.lower() and ns == ns.lower(), 'keep map/namespace names lower case'
        self.map, self.ns, self.longname = mapname, ns, longname
        self.bounds = bounds                                   # playable (x0, y0, x1, y1) for free()
        ws = {'message': longname, '_ambient': '20', 'gridsize': '128 128 128', '_blocksize': '0', '_lightmapscale': '2'}
        ws.update(worldspawn or {})
        self.M = Map(ws)
        self.rng = np.random.default_rng(seed)
        self.FOOT = []                                         # occupied (x0, y0, x1, y1, z0, z1)
        self.spots = {'weapon': [], 'ammo': [], 'item': [], 'spawn': [], 'pads': [], 'teleports': [], 'secrets': [],
                      'hurt': [], 'crawl': [], 'stairs': [], 'movers': [], 'botclip': []}
        self.routes = []
        self.notes = []                                        # warnings collected while building
        self._names = set()

    # ------------------------------------------------------------------ basics
    def T(self, name): return f'{self.ns}/{name}'

    def add(self, *b, tag=None): return self.M.add(*b, tag=tag)

    def ent(self, cls, origin=None, brushes=None, **kv):
        if cls in wopdata.FORBIDDEN: raise ValueError(f'{cls}: {wopdata.FORBIDDEN[cls]}')
        if cls not in wopdata.KNOWN_CLASSES:
            self.warn(f'{cls} is not in woplib.wopdata.KNOWN_CLASSES: check it in WoP entities.def')
        if brushes and cls in ('func_rotating', 'func_pendulum', 'func_train') and origin is not None:
            raise ValueError(f'{cls} with brushes takes an ORIGIN BRUSH, never an origin key (q3map2 adds them -> leak)')
        return self.M.ent(cls, origin, brushes, **kv)

    def warn(self, msg):
        self.notes.append(msg); print('  WARN', msg)

    def uniq(self, name):
        if name in self._names: raise ValueError(f'duplicate targetname/name {name}')
        self._names.add(name); return name

    # ------------------------------------------------------------------ occupancy (prop placement)
    def occupy(self, x0, y0, x1, y1, z0, z1): self.FOOT.append((x0, y0, x1, y1, z0, z1))

    def occupy_r(self, x, y, r, z0, z1): self.occupy(x - r, y - r, x + r, y + r, z0, z1)

    def reserve(self, *things, pad=0):
        """mark architecture as occupied: brushes, lists of brushes or (mn, mx) bounds. Reserve walls, stairs, pads and
        door approaches BEFORE scattering props ('nearest free spot' otherwise fills doorways). Never reserve a whole
        cabinet/room volume or nothing fits inside it."""
        for t in things:
            if isinstance(t, (list, tuple)) and t and not isinstance(t[0], (int, float)) and not hasattr(t[0], '__len__'):
                self.reserve(*t, pad=pad); continue
            if hasattr(t, 'bounds'): mn, mx = t.bounds()
            elif isinstance(t, (list, tuple)) and len(t) == 2 and hasattr(t[0], '__len__'): mn, mx = t
            elif isinstance(t, (list, tuple)):
                self.reserve(*t, pad=pad); continue
            else: raise TypeError(t)
            self.occupy(mn[0] - pad, mn[1] - pad, mx[0] + pad, mx[1] + pad, mn[2], mx[2])

    def keep_clear(self, x0, y0, x1, y1, z0, z1=None):
        """walk path / door approach / landing that props must never fill (every entrance needs ~96u of clear floor)"""
        self.occupy(x0, y0, x1, y1, z0, z0 + 96 if z1 is None else z1)

    def free(self, x, y, r, z0, z1, margin=4):
        X0, Y0, X1, Y1 = self.bounds
        if x - r < X0 + 8 or x + r > X1 - 8 or y - r < Y0 + 8 or y + r > Y1 - 8: return False
        for (a, b, c, d, e, f) in self.FOOT:
            if z1 <= e + 0.5 or z0 >= f - 0.5: continue
            dx = max(a - x, 0, x - c); dy = max(b - y, 0, y - d)
            if dx * dx + dy * dy < (r + margin) ** 2: return False
        return True

    def near_free(self, x, y, r, z0, z1, search=240, step=24):
        if self.free(x, y, r, z0, z1): return (x, y)
        for d in range(step, search + 1, step):
            for k in range(16):
                a = k * math.pi / 8
                px, py = x + d * math.cos(a), y + d * math.sin(a)
                if self.free(px, py, r, z0, z1): return (round(px), round(py))
        return None

    # ------------------------------------------------------------------ catalog + custom models
    @staticmethod
    def catalog_size(path, scale=1.0):
        b = md3bounds()['models/mapobjects/' + path if not path.startswith('models/') else path]
        return [(b['max'][i] - b['min'][i]) * scale for i in range(3)]

    def model_on(self, path, x, y, zsurf, scale=1.0, angle=0, centred=True, **kw):
        """catalog model resting on surface zsurf (origin z = surface - zmin*scale). centred: (x, y) is the centre of
        its bounds, not its origin (bush, cane4, muffin have origins well off-centre)."""
        p = path if path.startswith('models/') else 'models/mapobjects/' + path
        b = md3bounds().get(p)
        if b is None: raise KeyError(f'{p} not in md3bounds.json (wrong path? custom models go through custom())')
        if centred:
            cx = (b['min'][0] + b['max'][0]) / 2 * scale; cy = (b['min'][1] + b['max'][1]) / 2 * scale
            a = math.radians(angle)
            x -= cx * math.cos(a) - cy * math.sin(a); y -= cx * math.sin(a) + cy * math.cos(a)
        oz = zsurf - b['min'][2] * scale
        if b['min'][2] * scale > 32:
            self.warn(f'{p}: origin {b["min"][2] * scale:.0f}u BELOW its base - on a low floor it ends up in the void '
                      '("Entity leaked")')
        return self.M.model(p, (round(x, 1), round(y, 1), round(oz, 2)), scale=scale, angle=angle, **kw)

    def catalog(self, path, x, y, z, scale=1.0, angle=None, clip=True, lit=False, nudge=True, search=160, shrink=0.15):
        """catalog model centred near (x, y) on surface z, nudged to free space; weapclip box when clip and > 20u tall.
        Returns the (x, y) used or None when there was no room."""
        sx, sy, sz = self.catalog_size(path, scale)
        r = max(sx, sy) / 2
        p = self.near_free(x, y, r, z, z + sz, search) if nudge else (x, y)
        if p is None:
            self.warn(f'no room for {path} near ({x:.0f},{y:.0f},{z:.0f})'); return None
        a = self.rng.uniform(0, 360) if angle is None else angle
        kw = dict(spawnflags=4, _castshadows=1) if lit else {}
        e = self.model_on(path, p[0], p[1], z, scale, a, **kw)
        if clip and sz > 20:
            b = md3bounds()['models/mapobjects/' + path]
            ox, oy, oz = (float(v) for v in e['origin'].split())
            ar = math.radians(a); ca, sa = math.cos(ar), math.sin(ar)
            pts = [(ox + (px * ca - py * sa) * scale, oy + (px * sa + py * ca) * scale)
                   for px in (b['min'][0], b['max'][0]) for py in (b['min'][1], b['max'][1])]
            c = np.mean(pts, 0)
            pts = [tuple(c + (np.array(q) - c) * (1 - shrink)) for q in pts]
            z1 = oz + b['max'][2] * scale - 2
            self.add(hull([(q[0], q[1], z) for q in pts] + [(q[0], q[1], z1) for q in pts], WCLIP, round_pts=False))
        self.occupy_r(p[0], p[1], r, z, z + sz)
        return p

    def custom(self, place, x, y, zbase, angle=0, lit=True, boxes=(), cyls=(), occupy=True, **kw):
        """custom MD3 from woplib.models (place = models.PLACE[name] = (path, scale, zoff)) with its collision:
        boxes [(mn, mx)] and cyls [(cx, cy, r, z0, z1)] in model space -> common/weapclip, so bot routes don't change
        when the visual does. Lightmapped (spawnflags 4) by default; vertex lit (lit=False) for alpha foliage."""
        path, sc, zo = place
        extra = dict(spawnflags=4, _castshadows=1, _receiveshadows=1) if lit else {}
        extra.update(kw)
        e = self.M.model(path, (round(x, 2), round(y, 2), round(zbase + zo, 2)), scale=round(sc, 4), angle=angle, **extra)
        ar = math.radians(angle)
        rmax, hmax = 16.0, 16.0
        for (mn, mx) in boxes:
            self.lbox(x, y, zbase, angle, mn, mx)
            rmax = max(rmax, math.hypot(max(abs(mn[0]), abs(mx[0])), max(abs(mn[1]), abs(mx[1])))); hmax = max(hmax, mx[2])
        for (cx, cy, rr, z0, z1) in cyls:
            wx = x + cx * math.cos(ar) - cy * math.sin(ar); wy = y + cx * math.sin(ar) + cy * math.cos(ar)
            self.add(cyl(round(wx, 1), round(wy, 1), rr, zbase + z0, zbase + z1, WCLIP, 12 if rr > 40 else 8))
            rmax = max(rmax, math.hypot(cx, cy) + rr); hmax = max(hmax, z1)
        if occupy and (boxes or cyls): self.occupy_r(x, y, rmax, zbase, zbase + hmax)
        return e

    def prop(self, place, x, y, z, boxes=(), cyls=(), angle=None, search=160, lit=True, **kw):
        """custom MD3 + its collision, nudged to the nearest free spot (cover pieces, furniture). Returns (x, y) or None."""
        r, h = 16.0, 16.0
        for (mn, mx) in boxes:
            r = max(r, math.hypot(max(abs(mn[0]), abs(mx[0])), max(abs(mn[1]), abs(mx[1])))); h = max(h, mx[2])
        for (cx, cy, rr, z0, z1) in cyls:
            r = max(r, math.hypot(cx, cy) + rr); h = max(h, z1)
        p = self.near_free(x, y, r, z, z + h, search)
        if p is None:
            self.warn(f'no room for {place[0]} near ({x:.0f},{y:.0f},{z:.0f})'); return None
        a = self.rng.uniform(0, 360) if angle is None else angle
        self.custom(place, p[0], p[1], z, a, lit=lit, boxes=boxes, cyls=cyls, **kw)
        return p

    def lbox(self, x, y, z, ang, mn, mx, tex=WCLIP):
        """box given in model space (rotated by ang about z, placed at x, y, z)"""
        a = math.radians(ang); ca, sa = math.cos(a), math.sin(a)
        pts = [(x + px * ca - py * sa, y + px * sa + py * ca, z + pz)
               for px in (mn[0], mx[0]) for py in (mn[1], mx[1]) for pz in (mn[2], mx[2])]
        b = hull(pts, tex, round_pts=False)
        self.add(b)
        return b

    def clipped(self, brushes, tex=WCLIP, occupy=True):
        """re-texture brush shapes as invisible collision (the 'with as_clip()' recipe: old brush art -> MD3 visuals)"""
        for b in brushes:
            for f in b.faces: f.tex = tex; f.sc = (0.5, 0.5)
            self.add(b)
            if occupy:
                mn, mx = b.bounds(); self.occupy(mn[0], mn[1], mx[0], mx[1], mn[2], mx[2])
        return brushes

    # ------------------------------------------------------------------ light + sound
    def light(self, x, y, z, val, color='1 0.92 0.8', **kw):
        return self.M.ent('light', (round(x), round(y), round(z)), light=val, _color=color, **kw)

    def light_grid(self, x0, y0, x1, y1, z, spacing, val, color='1 0.92 0.8', skip=None):
        """point lights on a grid. Measured floor brightness (light_check raw lightmap median; 128 = neutral, 200+ washes
        out; fast light, _ambient 20, no bounce - bounce light adds ~10-30 indoors):
            600u over the floor, 512 grid:  600 -> 58   900 -> 79   1500 -> 124   2200 -> 173
            300u over the floor, 384 grid:  300 -> 64   600 -> 113  900 -> 162    1500 -> 238 (saturated)
        Aim for a median of 90-150 and run wopbuild `lights` (light_check) to confirm."""
        nx = max(1, round((x1 - x0) / spacing)); ny = max(1, round((y1 - y0) / spacing))
        for i in range(nx):
            for j in range(ny):
                x = x0 + (i + 0.5) * (x1 - x0) / nx; y = y0 + (j + 0.5) * (y1 - y0) / ny
                if skip and skip(x, y): continue
                self.light(x, y, z, val, color)

    @staticmethod
    def sound_path(noise):
        p = noise if noise.startswith('sound') else f'sound/world/{noise}'
        if not os.path.splitext(p)[1]: p += '.ogg'
        if os.path.splitext(p)[0] not in wopdata.KNOWN_SOUNDS:
            print(f'  note: {p} is not in wopdata.KNOWN_SOUNDS - pk3_check.py --game verifies it exists')
        return p

    def speaker(self, x, y, z, noise, loop=True, **kw):
        kv = {'noise': self.sound_path(noise)}
        if loop: kv['spawnflags'] = 1
        kv.update(kw)
        return self.M.ent('target_speaker', (round(x), round(y), round(z)), **kv)

    def timer_sound(self, x, y, z, noise, name, wait, rnd, **kw):
        """occasional sound: func_timer -> speaker (dog bark, distant train)"""
        self.speaker(x, y, z, noise, loop=False, targetname=self.uniq(name), **kw)
        self.M.ent('func_timer', (round(x), round(y), round(z + 64)), target=name, wait=wait, random=rnd, spawnflags=1)

    def trigger_sound(self, mn, mx, noise, name, wait=4, **kw):
        """one-shot when walked into (doorbell, applause on a summit)"""
        c = [(a + b) / 2 for a, b in zip(mn, mx)]
        self.speaker(c[0], c[1], c[2] + 40, noise, loop=False, targetname=self.uniq(name), **kw)
        self.M.ent('trigger_multiple', brushes=[box(mn, mx, TRIG)], target=name, wait=wait)

    # ------------------------------------------------------------------ pickups + spawns
    def _pickup(self, cls, x, y, floor, kind, suspended=False, **kw):
        """item origin = floor + 16 (bbox +-15). Items drop at spawn with a MASK_SOLID trace: on a common/clip floor
        (or anything not MASK_SOLID) they fall through, so pass suspended=True there (spawnflags 1)."""
        if suspended: kw['spawnflags'] = 1
        e = self.ent(cls, (round(x), round(y), round(floor) + 16), **kw)
        self.spots[kind].append(dict(cls=cls, x=round(x), y=round(y), floor=round(floor)))
        self.occupy_r(x, y, 30 if kind != 'weapon' else 40, floor, floor + 48)
        return e

    def weapon(self, w, x, y, floor, marker='blue', **kw):
        """put high-weight weapons (Imperius 1600 > Betty/Balloony 1200 > Pumper > Splasher > Boaster > Bubble G 400)
        on the hardest spots: bots ignore low-weight weapons that need a pad or a dead end"""
        assert w in wopdata.WEAPONS, w
        assert marker in wopdata.MARKERS, marker
        return self._pickup('weapon_' + w, x, y, floor, 'weapon', marker=marker, **kw)

    def ammo(self, w, x, y, floor, **kw):
        assert w in wopdata.WEAPONS + ('nipper',), w
        return self._pickup('ammo_' + w, x, y, floor, 'ammo', **kw)

    def item(self, cls, x, y, floor, **kw):
        if cls not in wopdata.PICKUPS and cls != 'station_health':
            raise ValueError(f'{cls} is not a WoP pickup (see wopdata.PICKUPS)')
        return self._pickup(cls, x, y, floor, 'ammo' if cls.startswith('ammo') else 'item', **kw)

    def spawn(self, x, y, floor, ang, cls='info_player_deathmatch', nudge=True):
        p = self.near_free(x, y, 40, floor, floor + 64) if nudge else (x, y)
        if p is None:
            self.warn(f'no room for a spawn near ({x:.0f},{y:.0f},{floor:.0f})'); return None
        self.ent(cls, (round(p[0]), round(p[1]), round(floor) + 25), angle=round(ang) % 360)
        self.spots['spawn'].append(dict(cls=cls, x=round(p[0]), y=round(p[1]), floor=round(floor)))
        self.occupy_r(p[0], p[1], 40, floor, floor + 64)
        return p

    def station(self, x, y, floor, ang=0):
        """station_health: 80x80x64 trigger, origin on the floor, model ~92x97 footprint"""
        self.ent('station_health', (round(x), round(y), round(floor)), angle=ang)
        self.occupy_r(x, y, 64, floor, floor + 80)

    # ------------------------------------------------------------------ jump pads, teleports, secrets
    def jumppad(self, x, y, z, land, apex, name, ceiling=None, edges=(), glow=True, top_tex=None, side_tex=None,
                radius=34, light_rgb='1 0.6 0.8'):
        """pad disc (6u) + trigger_push (48 x 48 x 64) + target_position at the apex, t_up/(t_up+t_down) of the way
        to `land` (x, y, floor). Warns for flights > 2.9 s, apex too close to `ceiling`, < 20u over `edges`.
        Fling pads on small tops go on the FAR side (bspc lands a pad where the arc first touches ground)."""
        x, y = round(x), round(y)
        name = self.uniq(name)
        P = padmath.plan(z, (x, y), land, apex, ceiling=ceiling, edges=edges)
        for w in P['warnings']: self.warn(f'pad {name}: {w}')
        if P['target'] is None: raise ValueError(f'pad {name}: {P["warnings"]}')
        top = top_tex or self.T('jumppad'); side = side_tex or self.T('rubber')
        disc = cyl(x, y, radius, z, z + 6, {'top': top, 'side': side, 'bot': side}, 12)
        for f in disc.faces:
            if f.n[2] > 0.9:
                s = 2 * radius / 256
                f.sc = (s, s); f.off = ((-(x - radius) / s) % 256, ((y + radius) / s) % 256)
        self.add(disc)
        trig = box((x - 24, y - 24, z + 6), (x + 24, y + 24, z + 70), TRIG)
        self.M.ent('trigger_push', brushes=[trig], target=name)
        self.M.ent('target_position', P['target'], targetname=name)
        self.spots['pads'].append(dict(name=name, pad=(x, y, z), origin=P['origin'], target=P['target'],
                                       land=list(land), t=P['t']))
        if glow: self.light(x, y, z + 48, 120, light_rgb)
        self.occupy_r(x, y, 60, z, z + 90)
        self.occupy_r(land[0], land[1], 64, land[2], land[2] + 96)      # props scattered later must not fill the landing
        return P

    def teleporter(self, mn, mx, dest, angle, name, visible_tex=None):
        """trigger_teleport -> misc_teleporter_dest. The dest must NOT be inside a trigger_push: put it just behind a
        pad (the 400 u/s exit speed slides the player on). dest = (x, y, floor)."""
        name = self.uniq(name)
        if not self.free(dest[0], dest[1], 20, dest[2], dest[2] + 56, margin=0):
            self.warn(f'teleporter {name}: destination {dest} is in an occupied spot (place movers/props first or move it)')
        self.M.ent('trigger_teleport', brushes=[box(mn, mx, visible_tex or TRIG)], target=name)
        self.M.ent('misc_teleporter_dest', (round(dest[0]), round(dest[1]), round(dest[2]) + 25), targetname=name,
                   angle=round(angle) % 360)
        self.spots['teleports'].append(dict(name=name, mn=list(mn), mx=list(mx), dest=list(dest)))
        self.occupy_r(dest[0], dest[1], 48, dest[2], dest[2] + 64)

    def secret(self, mn, mx, dest, angle, name, approach='top', sound='misc/secret_found'):
        """the user's secret recipe: walk into something (fireplace, coffin, flour bin, fairy door, drain) ->
        trigger_teleport into a SEALED bonus room (Pad Power, Revival, Killer Ducks) with a teleporter back, and a
        secret_found sound from a trigger_multiple placed where the player comes from (`approach`: 'top' = stacked
        above the teleport, or 'n'/'s'/'e'/'w' = a 48u slab on that side) so the two triggers never overlap.
        Sealed rooms below the world don't leak. Make the entry non-obvious."""
        mn, mx = list(mn), list(mx)
        if approach == 'top': smn, smx = [mn[0], mn[1], mx[2]], [mx[0], mx[1], mx[2] + 48]
        else:
            ax, sg = {'n': (1, 1), 's': (1, -1), 'e': (0, 1), 'w': (0, -1)}[approach]
            smn, smx = list(mn), list(mx)
            if sg > 0: smn[ax], smx[ax] = mx[ax], mx[ax] + 48
            else: smn[ax], smx[ax] = mn[ax] - 48, mn[ax]
        self.trigger_sound(smn, smx, sound, name + '_snd', wait=2)
        self.teleporter(mn, mx, dest, angle, name)
        self.occupy(min(mn[0], smn[0]), min(mn[1], smn[1]), max(mx[0], smx[0]), max(mx[1], smx[1]), mn[2], max(mx[2], smx[2]))
        self.spots['secrets'].append(dict(name=name, mn=mn, mx=mx, dest=list(dest)))

    def hurt(self, mn, mx, dmg=5, **kw):
        """trigger_hurt. bspc makes it lava grown by the player box: keep pad landings > hurt radius + 15 away and use
        botclip strips along deadly edges (bots strafe off them)."""
        self.M.ent('trigger_hurt', brushes=[box(mn, mx, TRIG)], dmg=dmg, **kw)
        self.spots['hurt'].append(dict(mn=list(mn), mx=list(mx), dmg=dmg))

    def botclip_edge(self, x0, y0, x1, y1, z, width=24, height=64):
        """24u botclip strip along a deadly drop (z = walk surface); leave gaps where bridges land"""
        if abs(x1 - x0) >= abs(y1 - y0):
            b = box((min(x0, x1), y0 - width / 2, z), (max(x0, x1), y0 + width / 2, z + height), BOTCLIP)
        else:
            b = box((x0 - width / 2, min(y0, y1), z), (x0 + width / 2, max(y0, y1), z + height), BOTCLIP)
        self.add(b)
        self.spots['botclip'].append([list(v) for v in b.bounds()])
        return b

    # ------------------------------------------------------------------ stairs, crawl spaces, routes
    def stairs16(self, x0, y0, x1, y1, z0, ztop, run_dir, tex, route=None, **kw):
        """16u-riser straight flight (bots skip runs of 32u risers even when the AAS links them). route=name adds an
        aas_check route from the floor in front of the bottom step to the landing past the top. Keep 48u+ between
        neighbouring flights (closer pockets become bot TRAPs) and step top + 56 under any ceiling edge."""
        steps = stairs(x0, y0, x1, y1, z0, ztop, run_dir, tex, step_h=16, **kw)
        n = len(steps)
        L = (y1 - y0) if run_dir in 'ns' else (x1 - x0)
        if L / max(n, 1) < 30:
            self.warn(f'stairs {route or (x0, y0)}: treads {L / n:.0f}u deep < 30u - open any ceiling two steps early')
        self.add(steps)
        self.spots['stairs'].append(dict(rect=[x0, y0, x1, y1], z0=z0, ztop=ztop, dir=run_dir, name=route))
        if route:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[run_dir]
            half = L / 2
            a = (cx - d[0] * (half + 48), cy - d[1] * (half + 48), z0)
            b = (cx + d[0] * (half + 48), cy + d[1] * (half + 48), ztop)
            self.route(route, a, b)
        return steps

    MAX_RAMP_DEG = 40.0          # Q3 MIN_WALK_NORMAL 0.7 = 45.6 deg; bots and players slide near the limit

    def ramp(self, x0, y0, x1, y1, z_low, z_high, rise, tex, base=None, route=None):
        """plain walkable ramp (solid wedge from `base`, default z_low, up to a top sloping z_low -> z_high toward
        `rise` 'n'/'s'/'e'/'w'). Keep it plain: bevelled brushes touching a ramp face left it ungrounded in bspc.
        Refuses slopes over MAX_RAMP_DEG; route=name adds an aas_check route from the foot to the top landing."""
        L = (y1 - y0) if rise in 'ns' else (x1 - x0)
        deg = math.degrees(math.atan2(z_high - z_low, L))
        if deg > self.MAX_RAMP_DEG:
            raise ValueError(f'ramp {route or (x0, y0)}: {deg:.1f} deg is too steep to walk (max {self.MAX_RAMP_DEG:g}; '
                             f'lengthen it to >= {(z_high - z_low) / math.tan(math.radians(self.MAX_RAMP_DEG)):.0f}u)')
        b = wopmap.ramp(x0, y0, x1, y1, z_low if base is None else base, z_low, z_high, rise, tex)
        self.add(b)
        self.spots.setdefault('ramps', []).append(dict(rect=[x0, y0, x1, y1], z_low=z_low, z_high=z_high, dir=rise,
                                                       deg=round(deg, 1), name=route))
        if route:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[rise]
            half = L / 2
            self.route(route, (cx - d[0] * (half + 64), cy - d[1] * (half + 64), z_low),
                       (cx + d[0] * (half + 64), cy + d[1] * (half + 64), z_high))
        return b

    def botclip_rect(self, x0, y0, x1, y1, z, sides='nsew', gaps=(), width=24, height=64):
        """botclip strips along the exposed edges of a raised deck/shelf (x0, y0, x1, y1) with walk surface z, inset so
        they sit ON the deck. gaps = [(side, a, b)]: leave the stretch a..b (x for n/s, y for e/w) open where a bridge,
        ramp or pad landing meets the edge. Bot falls on the kitchen went from 52 to 5 per match with these."""
        out = []
        h = width / 2
        for s in sides:
            horiz = s in 'ns'
            lo, hi = (x0, x1) if horiz else (y0, y1)
            cut = sorted((max(lo, a), min(hi, b)) for (gs, a, b) in gaps if gs == s and b > lo and a < hi)
            segs, p = [], lo
            for a, b in cut:
                if a > p: segs.append((p, a))
                p = max(p, b)
            if p < hi: segs.append((p, hi))
            edge = {'n': y1 - h, 's': y0 + h, 'e': x1 - h, 'w': x0 + h}[s]
            for a, b in segs:
                if b - a < 8: continue
                out.append(self.botclip_edge(a, edge, b, edge, z, width, height) if horiz
                           else self.botclip_edge(edge, a, edge, b, z, width, height))
        return out

    def water_box(self, mn, mx, tex, nodraw_tex=None, cutters=()):
        """the water recipe: ONE water box, CSG-carved by everything inside it (water must not overlap solids), only the
        top surface drawn, every internal face nodraw water (q3map2 only culls exactly coincident faces). Depth <= 48
        does not drown; deeper water needs 16u steps or a ramp out (lint_map 'water'). Returns the pieces."""
        nd = nodraw_tex or tex + '_nd'
        wb = box(mn, mx, tex)
        pieces = wopmap.carve(wb, list(cutters)) if cutters else [wb]
        for p in pieces:
            for f in p.faces: f.tex = tex if f.n[2] > 0.9 and abs(f.d - mx[2]) < 0.5 else nd
            self.add(p)
        self.spots.setdefault('water', []).append(dict(mn=list(mn), mx=list(mx), depth=mx[2] - mn[2]))
        return pieces

    def solid_piece(self, name, brushes, texfn, lit=True, clip=WCLIP, hidden=None):
        """big architecture built ONCE as convex brushes and used twice: the visible faces become a custom MD3
        (woplib.models.solids_mesh) and the same brushes become invisible collision, so bot routes never drift from
        what players see (az_shapes/padaztec recipe). texfn(centre, normal, poly) -> (shader, uvfn) in WORLD space.
        The model is stored centred on the pieces' footprint (MD3 +-512 limit) and placed back there. Returns the
        misc_model entity."""
        from . import models as ML
        mn = np.min([b.bounds()[0] for b in brushes], 0); mx = np.max([b.bounds()[1] for b in brushes], 0)
        o = np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])
        X = ML.Model()

        def tf(c, n, poly):
            r = texfn(c, n, poly)
            if r is None: return None
            sh, uvf = r
            return sh, (lambda p, uvf=uvf: uvf(p))
        ML.solids_mesh(X, brushes, tf, hidden=hidden)
        X.shift(o)
        place = ML.save(name, X)
        e = self.custom(place, float(o[0]), float(o[1]), float(o[2]), lit=lit, occupy=False)
        if clip:
            col = []
            for b in brushes:
                c = wopmap.Brush([wopmap.Face(f.pts, clip, (0.5, 0.5)) for f in b.faces], True)
                col.append(c)
            self.clipped(col, clip)
        else:
            self.reserve(*brushes)
        return e

    def sky_window(self, wall_mn, wall_mx, hole, inner_tex, sky_tex, jamb_tex=None, glass_tex=None, depth=256, face='n'):
        """a window through a STRUCTURAL hull wall with a sealed sky box behind it, so an indoor map shows the night sky
        (and gets q3map_sun/skylight through it) without opening the hull. wall_mn/wall_mx: the wall box (thin along y);
        hole = (x0, x1, z0, z1); face = the side the room is on ('n' for a south wall). Builds the wall pieces round the
        hole, the sky box behind (its inner faces sky_tex), and a detail glass pane in the hole when glass_tex is given.
        Returns the brushes."""
        (wx0, wy0, wz0), (wx1, wy1, wz1) = wall_mn, wall_mx
        hx0, hx1, hz0, hz1 = hole
        assert wx0 < hx0 < hx1 < wx1 and wz0 < hz0 < hz1 < wz1, 'hole must sit inside the wall'
        jt = jamb_tex or inner_tex
        out = []

        def wall_piece(mn, mx, jamb_side):
            t = {k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}
            t[face] = inner_tex
            for js in jamb_side: t[js] = jt
            b = box(mn, mx, t, detail=False); self.add(b); out.append(b)
        wall_piece((wx0, wy0, wz0), (hx0, wy1, wz1), 'e')
        wall_piece((hx1, wy0, wz0), (wx1, wy1, wz1), 'w')
        wall_piece((hx0, wy0, wz0), (hx1, wy1, hz0), ['top'])
        wall_piece((hx0, wy0, hz1), (hx1, wy1, wz1), ['bot'])
        # sealed sky box behind the hole (on the side away from the room)
        if face == 'n': y0, y1 = wy0 - depth, wy0
        else: y0, y1 = wy1, wy1 + depth
        bx0, bx1, bz0, bz1 = hx0 - 32, hx1 + 32, hz0 - 32, hz1 + 32
        sk = lambda inner: dict({k: CAULK for k in ('n', 's', 'e', 'w', 'top', 'bot')}, **{inner: sky_tex})
        far = (y0 - 32, y0) if face == 'n' else (y1, y1 + 32)
        for mn, mx, inner in (((bx0, far[0], bz0), (bx1, far[1], bz1), 'n' if face == 'n' else 's'),
                              ((bx0, y0, bz0), (hx0, y1, bz1), 'e'), ((hx1, y0, bz0), (bx1, y1, bz1), 'w'),
                              ((hx0, y0, bz0), (hx1, y1, hz0), 'top'), ((hx0, y0, hz1), (hx1, y1, bz1), 'bot')):
            b = box(mn, mx, sk(inner), detail=False); self.add(b); out.append(b)
        if glass_tex:
            gy = (wy0 + wy1) / 2
            b = box((hx0, gy - 2, hz0), (hx1, gy + 2, hz1), glass_tex); self.add(b); out.append(b)
        self.reserve(((hx0, wy0, hz0), (hx1, wy1, hz1)))
        return out

    def crawl(self, mn, mx):
        """declare an intended crouch-only space (lint_map's headroom check skips it)"""
        self.spots['crawl'].append([list(mn), list(mx)])

    def route(self, name, a, b):
        """an on-foot route that must work both ways standing (aas_check.py --route). Endpoints on floors, never on a
        pad, never in wadeable water (those are swim areas)."""
        self.routes.append((name, a, b))

    # ------------------------------------------------------------------ movers
    def _origin_brush(self, c, r=8):
        return box((c[0] - r, c[1] - r, c[2] - r), (c[0] + r, c[1] + r, c[2] + r), ORIGIN)

    def rotating_model2(self, model, centre, speed, axis='z', reverse=False, nodraw_tex=None, **kw):
        """spinning/orbiting decoration: func_rotating = origin brush at the centre + a tiny nonsolid brush + model2.
        NO origin key. model2 has no scale. Loops round a whole map (fish, UFOs, spores): put every copy in one IQM
        (MD3 can't hold geometry beyond +-512u of its origin). Riders: add nodraw collision brushes instead."""
        sf = {'z': 0, 'x': 4, 'y': 8}[axis] | (2 if reverse else 0)
        c = [round(v) for v in centre]
        nd = nodraw_tex or self.T('nodraw_ns')
        tiny = box((c[0] - 4, c[1] - 4, c[2] + 12), (c[0] + 4, c[1] + 4, c[2] + 20), nd)
        e = self.ent('func_rotating', brushes=[self._origin_brush(c), tiny], model2=model, speed=speed, spawnflags=sf, **kw)
        self.spots['movers'].append(dict(cls='func_rotating', centre=c, model=model))
        return e

    def pendulum_model2(self, model, pivot, swing_deg, reach, nodraw_tex=None, **kw):
        """gentle rocking decoration (floating ducks, hanging pans). The period comes from how far the brush reaches
        below the pivot (`reach`); speed = swing in degrees. Never func_bobbing for decoration (bots try to ride it)."""
        c = [round(v) for v in pivot]
        nd = nodraw_tex or self.T('nodraw_ns')
        low = box((c[0] - 4, c[1] - 4, c[2] - reach), (c[0] + 4, c[1] + 4, c[2] - reach + 8), nd)
        e = self.ent('func_pendulum', brushes=[self._origin_brush(c), low], model2=model, speed=swing_deg, **kw)
        self.spots['movers'].append(dict(cls='func_pendulum', centre=c, model=model))
        return e

    def elevator(self, x0, y0, x1, y1, z_low, z_high, tex, name=None, speed=150, lip=8, thick=16):
        """bot-usable func_plat. Drawn RAISED (top at z_high); it lowers by `height` so its top rests at z_low. The
        caller must leave a `thick`-deep pit (z_low - thick .. z_low) under the footprint for the lowered disc."""
        b = box((x0, y0, z_high - thick), (x1, y1, z_high), tex)
        kv = dict(height=z_high - z_low, speed=speed, lip=lip)
        if name: kv['targetname'] = self.uniq(name)
        self.M.ent('func_plat', brushes=[b], **kv)
        self.spots['movers'].append(dict(cls='func_plat', rect=[x0, y0, x1, y1], z_low=z_low, z_high=z_high))
        return b

    # ------------------------------------------------------------------ cleanup + output
    NONSOLID_TEX = ('trigger', 'nodraw_ns', 'origin', 'botclip', 'common/clip', 'water', 'fog')

    def fix_items(self):
        """move any pickup/spawn whose box starts in a solid to the nearest free spot with a floor under it"""
        sol = []
        skip = ('trigger_push', 'trigger_multiple', 'trigger_teleport', 'trigger_hurt', 'func_rotating', 'func_pendulum')
        for b in self.M.world + [bb for e in self.M.ents if e['classname'] not in skip for bb in e['_brushes']]:
            ts = b.textures()
            if all(any(h in (t or '') for h in self.NONSOLID_TEX) for t in ts): continue
            mn, mx = b.bounds()
            sol.append((mn, mx, b.planes()))
        if not sol: return []
        smn = np.array([s[0] for s in sol]); smx = np.array([s[1] for s in sol])

        def blocked(o, lo, hi):
            bmn, bmx = o + lo, o + hi
            cand = np.where(np.all(smn < bmx - 0.25, 1) & np.all(smx > bmn + 0.25, 1))[0]
            if len(cand) == 0: return False
            pts = [o + np.array([x, y, z]) for x in (lo[0], 0, hi[0]) for y in (lo[1], 0, hi[1]) for z in (lo[2] + 1, 0, hi[2])]
            return any(any(all(np.dot(n, p) - d < -0.25 for n, d in sol[k][2]) for p in pts) for k in cand)
        moved = []
        for e in self.M.ents:
            c = e['classname']
            if not (c in wopdata.PICKUPS or c in wopdata.SPAWNS): continue
            o = np.array([float(v) for v in e['origin'].split()])
            lo, hi = ((np.array([-16, -16, -24]), np.array([16, 16, 32])) if c in wopdata.SPAWNS
                      else (np.array([-16, -16, -15.5]), np.array([16, 16, 16])))
            if not blocked(o, lo, hi): continue
            done = False
            for d in range(16, 200, 16):
                for k in range(16):
                    a = k * math.pi / 8
                    p = o + np.array([d * math.cos(a), d * math.sin(a), 0])
                    if not blocked(p, lo, hi) and blocked(p + np.array([0, 0, lo[2] - 8]), np.array([-4, -4, -2]), np.array([4, 4, 2])):
                        e['origin'] = ' '.join(fmt([v]) for v in np.round(p))
                        moved.append((c, o.astype(int).tolist(), np.round(p).astype(int).tolist())); done = True; break
                if done: break
            if not done: moved.append((c, o.astype(int).tolist(), 'STUCK'))
        for m in moved: self.warn(f'moved {m[0]} {m[1]} -> {m[2]}')
        return moved

    def summary(self):
        cnt = {}
        for e in self.M.ents: cnt[e['classname']] = cnt.get(e['classname'], 0) + 1
        lines = [f'{self.map}: {len(self.M.world)} world brushes, {len(self.M.ents)} entities, '
                 f'{cnt.get("misc_model", 0)} models, {len(self.spots["pads"])} pads, {len(self.routes)} routes']
        for w in wopdata.WEAPONS:
            nw, na = cnt.get('weapon_' + w, 0), cnt.get('ammo_' + w, 0)
            if nw or na:
                flag = '' if 3 <= na <= 6 else '   <-- rule: 3-6 ammo spots'
                lines.append(f'  {w:9s} weapons {nw} ammo {na}{flag}')
        missing = [w for w in wopdata.WEAPONS if not cnt.get('weapon_' + w)]
        if missing: lines.append(f'  weapons not placed: {" ".join(missing)}')
        lines.append(f'  spawns {sum(cnt.get(c, 0) for c in wopdata.SPAWNS)}, secrets {len(self.spots["secrets"])}, '
                     f'warnings {len(self.notes)}')
        return '\n'.join(lines)

    def write(self, out_dir, routes_path=None, header=''):
        """maps/<map>.map, maps/<map>.spots.json (items, pads, secrets, hurt zones, crawl spaces... for lint_map,
        botreport and wopbuild) and routes.txt (default next to the generator: pass routes_path)"""
        for b in self.M.world + [bb for e in self.M.ents for bb in e['_brushes']]:
            for f in b.faces:
                if not f.tex: raise ValueError(f'brush at {b.bounds()} has a face without a texture (texture dict keys: '
                                               "top, bot, side, n, s, e, w)")
                if f.tex.startswith('textures/'): raise ValueError(f'{f.tex}: no textures/ prefix in .map files')
        os.makedirs(os.path.join(out_dir, 'maps'), exist_ok=True)
        mp = os.path.join(out_dir, 'maps', self.map + '.map')
        open(mp, 'w').write(self.M.text(header or f'// {self.longname} ({self.map}) - generated with wop_tools/woplib\n'))
        sp = dict(self.spots); sp['routes'] = [dict(name=n, a=list(a), b=list(b)) for n, a, b in self.routes]
        sp['bounds'] = list(self.bounds); sp['map'] = self.map; sp['ns'] = self.ns; sp['notes'] = self.notes
        json.dump(sp, open(os.path.join(out_dir, 'maps', self.map + '.spots.json'), 'w'), indent=1, default=float)
        if routes_path:
            with open(routes_path, 'w') as f:
                f.write(f'# On-foot routes that must work both ways while standing (aas_check.py --route @routes.txt)\n'
                        f'# name: from x,y,z > to x,y,z   (z = floor height); generated for {self.map}\n')
                for (n, a, b) in self.routes:
                    f.write(f'{n + ":":20s}{round(a[0])},{round(a[1])},{round(a[2])} > {round(b[0])},{round(b[1])},{round(b[2])}\n')
        print(self.summary())
        return mp


# ---------------------------------------------------------------------- default kit textures
def write_kit_textures(out_dir, ns, pad_rgb=(90, 200, 255), rubber=(60, 60, 70)):
    """textures/<ns>/jumppad, rubber, nodraw_ns, glass (procedural, original) for the kit's helpers"""
    from . import models as ML
    from PIL import ImageDraw
    n = 256
    x, y = ML.xy(n)
    dx, dy = x - 0.5, y - 0.5
    rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    c = np.zeros((n, n, 3), np.float32) + ML.C(rubber)
    ring = (np.abs(rr - 0.40) < 0.04) | (np.abs(rr - 0.22) < 0.03)
    c = np.where(ring[..., None], ML.C(pad_rgb), c)
    arrows = (np.sin(a * 6) > 0.75) & (rr > 0.26) & (rr < 0.36)
    c = np.where(arrows[..., None], ML.C(pad_rgb) * 0.8 + 50, c)
    c = np.where((rr < 0.1)[..., None], ML.C((250, 250, 250)), c)
    td = os.path.join(out_dir, 'textures', ns)
    ML.save_img(os.path.join(td, 'jumppad'), c + ML.N3(n, 1, 3, 4))
    ML.save_img(os.path.join(td, 'rubber'), ML.fill(64, rubber, 3, 59))
    ML.save_img(os.path.join(td, 'nodraw_ns'), ML.fill(64, (200, 60, 200), 2, 69))
    ML.save_img(os.path.join(td, 'glass'), ML.fill(64, (170, 200, 210), 2, 61))
    return ['jumppad', 'rubber', 'nodraw_ns', 'glass']
