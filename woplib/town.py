"""woplib.town - walk-in, climbable multi-storey buildings as one custom MD3 + matching weapclip (first used on
wop_padville). Every building it makes obeys the user's rules: you can walk in, go upstairs (16u stairs bots climb), look
out of open windows, and stand on the roof (flat roof or a 30-degree gable with a ridge walk), with nothing on the roof
that blocks the line of fire.

    from woplib import town
    B = town.Building(K, 'baker', rect=(x0, y0, x1, y1), z0=0, storeys=(176, 160),
                      mats=dict(ext='brick', int='plaster', trim='trim', floor='boards', roof='slate', ceil='plaster'),
                      doors=[('s', -48, 64)], roof='gable_x', stairs=[(x0 + 16, y1 - 112, x0 + 16 + 320, y1 - 16, 'e')])
    B.build()          # brushes -> K.solid_piece (MD3 + weapclip), stairs, routes, keep_clear in front of doors

mats are TX.material keys (model shaders) the caller registered first. Openings:
  doors   [(side, a, b)]                     ground storey; a..b along x (n/s walls) or y (e/w walls); 112u high
  windows auto: every storey/side gets evenly spaced open windows (win_w wide, sill 56, head h - 40); pass
          windows={side: [(a, b, storey)]} to set them yourself, or no_windows='ne' to skip whole sides
  stairs  one flight per upper storey [(x0, y0, x1, y1, dir)], 16u risers rising toward dir; its slab hole is the
          flight's footprint (no ceiling over any step, so no headroom problems). Leave 48u+ to other flights.
  roof    'flat' (stand on it; roof_stairs=(x0, y0, x1, y1, dir) adds a flight from the top storey up through a
          hatch), 'gable_x' / 'gable_y' (ridge along x / y, 30 degrees, walkable, 4u-proud ridge walk), or None.
Geometry notes (each one broke a shipped map):
  * the gable slopes sit ON the wall tops (their underside meets the outer top edge) so nothing overlaps a wall
  * the ridge walk is a cap whose underside follows both slopes (padhalloween/paddollhouse: flush ridges got no link)
  * the building is stored centred on its footprint: keep it under ~1000u across (MD3 +-512u)
"""
import math
import numpy as np
from wopmap import box, hull
from .kit import CAULK, WCLIP
from . import models as ML

PITCH = 30.0
DOOR_H = 112
SLAB = 16


class Building:
    def __init__(self, K, name, rect, z0, storeys, mats, doors=(), windows=None, no_windows='', win_w=72, win_gap=None,
                 stairs=(), roof='flat', roof_stairs=None, wall_t=16, overhang=20, floor_mat=True, tile=128.0,
                 ext_by_storey=None, door_h=DOOR_H, hatch=None, gable_ext=(16, 16)):
        self.K, self.name = K, name
        self.rect = tuple(float(v) for v in rect)
        self.z0 = float(z0); self.storeys = list(storeys); self.mats = mats
        self.doors = list(doors); self.windows = windows; self.no_windows = no_windows
        self.win_w = win_w; self.win_gap = win_gap if win_gap is not None else win_w * 1.6
        self.stairs = list(stairs); self.roof = roof; self.roof_stairs = roof_stairs
        self.t = wall_t; self.o = overhang; self.floor_mat = floor_mat; self.tile = tile
        self.ext_by_storey = ext_by_storey or {}
        self.door_h = door_h; self.hatch = hatch; self.gable_ext = gable_ext
        self.brushes = []; self.stair_brushes = []
        self.levels = []                     # floor z of each storey
        z = self.z0
        for h in self.storeys:
            self.levels.append(z); z += h
        self.wall_top = z
        self.roof_top = None; self.ridge = None

    # ------------------------------------------------------------------ geometry
    def _openings(self, side, k):
        """[(a, b, zlo, zhi)] in absolute z for side/storey k"""
        x0, y0, x1, y1 = self.rect; t = self.t
        zb = self.levels[k]; h = self.storeys[k]
        out = []
        if k == 0:
            out += [(a, b, zb, zb + self.door_h) for (s, a, b) in self.doors if s == side]
        if self.windows is not None:
            for w in self.windows.get(side, []):
                if w[2] != k: continue
                zl, zh = (w[3], w[4]) if len(w) >= 5 else (56, h - 40)
                out.append((w[0], w[1], zb + zl, zb + zh))
        elif side not in self.no_windows:
            lo, hi = (x0 + t, x1 - t) if side in 'ns' else (y0 + t, y1 - t)
            L = hi - lo
            n = int((L - self.win_gap) // (self.win_w + self.win_gap))
            if n > 0:
                step = L / n
                for i in range(n):
                    c = lo + step * (i + 0.5)
                    a, b = c - self.win_w / 2, c + self.win_w / 2
                    if any(a < db + 40 and b > da - 40 for (da, db, _, _) in out): continue
                    zl, zh = zb + 56, zb + h - 40
                    if zh - zl >= 64: out.append((a, b, zl, zh))
        return sorted(out)

    def _wall(self, side, lo, hi, zlo, zhi):
        if hi - lo < 1 or zhi - zlo < 1: return
        x0, y0, x1, y1 = self.rect; t = self.t
        if side == 's': mn, mx = (lo, y0, zlo), (hi, y0 + t, zhi)
        elif side == 'n': mn, mx = (lo, y1 - t, zlo), (hi, y1, zhi)
        elif side == 'w': mn, mx = (x0, lo, zlo), (x0 + t, hi, zhi)
        else: mn, mx = (x1 - t, lo, zlo), (x1, hi, zhi)
        self.brushes.append(box(mn, mx, 'x/x'))

    def walls(self):
        x0, y0, x1, y1 = self.rect; t = self.t
        for k, h in enumerate(self.storeys):
            zb = self.levels[k]; zt = zb + h
            for side in 'nsew':
                lo, hi = (x0, x1) if side in 'ns' else (y0 + t, y1 - t)
                p = lo
                for (a, b, zl, zh) in self._openings(side, k):
                    assert lo + 4 <= a < b <= hi - 4, f'{self.name}: opening {(side, a, b)} outside the wall {lo}..{hi}'
                    self._wall(side, p, a, zb, zt)
                    self._wall(side, a, b, zb, zl); self._wall(side, a, b, zh, zt)
                    p = b
                self._wall(side, p, hi, zb, zt)

    def _slab(self, z, holes):
        """interior slab (inside the walls) at top z, minus rectangular holes"""
        from wopmap import sub_rects
        x0, y0, x1, y1 = self.rect; t = self.t
        for r in sub_rects((x0 + t, y0 + t, x1 - t, y1 - t), [tuple(h[:4]) for h in holes]):
            if r[2] - r[0] > 1 and r[3] - r[1] > 1:
                self.brushes.append(box((r[0], r[1], z - SLAB), (r[2], r[3], z), 'x/x'))

    @staticmethod
    def stair_hole(st, side=24, foot=40):
        """slab hole for a flight: its footprint grown `side` units on both long sides and `foot` units at the bottom,
        so no ceiling edge hangs over the edge cells of any step (lint headroom: step top + 56)"""
        x0, y0, x1, y1, d = st
        if d in 'ns':
            x0, x1 = x0 - side, x1 + side
            if d == 'n': y0 -= foot
            else: y1 += foot
        else:
            y0, y1 = y0 - side, y1 + side
            if d == 'e': x0 -= foot
            else: x1 += foot
        return (x0, y0, x1, y1)

    def floors(self):
        for k in range(1, len(self.storeys)):
            st = self.stairs[k - 1] if k - 1 < len(self.stairs) else None
            self._slab(self.levels[k], [self.stair_hole(st)] if st else [])
        if self.floor_mat:                     # 4u floorboards on the ground storey
            x0, y0, x1, y1 = self.rect; t = self.t
            self.brushes.append(box((x0 + t, y0 + t, self.z0), (x1 - t, y1 - t, self.z0 + 4), 'x/x'))

    def flat_roof(self):
        x0, y0, x1, y1 = self.rect
        holes = [self.stair_hole(self.roof_stairs)] if self.roof_stairs else []
        if self.hatch: holes.append(self.hatch)
        from wopmap import sub_rects
        for r in sub_rects((x0, y0, x1, y1), [tuple(h[:4]) for h in holes]):
            self.brushes.append(box((r[0], r[1], self.wall_top), (r[2], r[3], self.wall_top + SLAB), 'x/x'))
        self.roof_top = self.wall_top + SLAB

    def gable_roof(self, axis):
        """two 30-degree slopes resting on the wall tops, gable triangles, and a 4u-proud ridge-walk cap"""
        x0, y0, x1, y1 = self.rect; o = self.o; zt = self.wall_top
        tg = math.tan(math.radians(PITCH)); th = SLAB
        if axis == 'x':
            a0, a1, b0, b1 = x0, x1, y0, y1        # along a, across b
        else:
            a0, a1, b0, b1 = y0, y1, x0, x1
        bc = (b0 + b1) / 2; w = (b1 - b0) / 2
        top = lambda b: zt + th + (w - abs(b - bc)) * tg       # slope top surface at across-coordinate b
        P = lambda a, b, z: (a, b, z) if axis == 'x' else (b, a, z)
        rw = 24
        for s in (-1, 1):
            be = bc + s * (w + o)                  # eave (outer edge)
            bi = bc
            pts = []
            for a in (a0 - self.gable_ext[0], a1 + self.gable_ext[1]):
                pts += [P(a, be, top(be)), P(a, be, top(be) - th), P(a, bi, top(bi)), P(a, bi, top(bi) - th)]
            self.brushes.append(hull(pts, 'x/x', round_pts=False))
        # gable triangles (end walls above the wall top, under the slope undersides)
        for (ga, gb) in ((a0, a0 + self.t), (a1 - self.t, a1)):
            pts = []
            for a in (ga, gb):
                pts += [P(a, b0, zt), P(a, b1, zt), P(a, bc, top(bc) - th)]
            self.brushes.append(hull(pts, 'x/x', round_pts=False))
        # ridge walk: underside follows both slopes, flat top 4u above the peak
        peak = top(bc)
        for sg in (-1, 1):                       # two convex halves (a V-shaped underside is not convex)
            pts = []
            for a in (a0 - self.gable_ext[0], a1 + self.gable_ext[1]):
                pts += [P(a, bc + sg * rw, top(bc + sg * rw)), P(a, bc, peak), P(a, bc + sg * rw, peak + 4), P(a, bc, peak + 4)]
            self.brushes.append(hull(pts, 'x/x', round_pts=False))
        self.roof_top = peak + 4
        self.ridge = (axis, bc, peak + 4)

    # ------------------------------------------------------------------ texturing
    def _is_interior(self, c, n):
        x0, y0, x1, y1 = self.rect; t = self.t
        p = np.asarray(c) + np.asarray(n) * 3.0
        return (x0 + t - 0.5 < p[0] < x1 - t + 0.5 and y0 + t - 0.5 < p[1] < y1 - t + 0.5
                and self.z0 - 1 < p[2] < self.wall_top + 1)

    def _storey_of(self, z):
        k = 0
        for i, zb in enumerate(self.levels):
            if z >= zb - 0.5: k = i
        return k

    def texfn(self):
        x0, y0, x1, y1 = self.rect; t = self.t; M = self.mats; tile = self.tile

        def f(c, n, poly):
            c = np.asarray(c); n = np.asarray(n)
            uv = ML.planar_uv(n, tile)
            if c[2] > self.wall_top + 0.5 and self.roof and self.roof.startswith('gable'):
                if n[2] > 0.3: return M.get('roof', M['ext']), uv
                if n[2] < -0.3: return M.get('ceil', M.get('int', M['ext'])), uv
                return M.get('gable', M['ext']), uv
            if self.roof == 'flat' and c[2] >= self.wall_top - 0.5:
                if n[2] > 0.7: return M.get('roofflat', M.get('roof', M['ext'])), uv
                if n[2] < -0.7: return M.get('ceil', M.get('int', M['ext'])), uv
                return M.get('trim', M['ext']), uv
            inside = self._is_interior(c, n)
            if n[2] > 0.7:
                if c[2] < self.z0 + 5: return M.get('floor', M.get('int', M['ext'])), uv
                if any(abs(c[2] - zb) < 0.6 for zb in self.levels[1:]) and inside:
                    return M.get('floor', M.get('int', M['ext'])), uv
                return M.get('trim', M['ext']), uv           # sills, wall tops in openings
            if n[2] < -0.7:
                return (M.get('ceil', M.get('int', M['ext'])) if inside else M.get('trim', M['ext'])), uv
            # vertical faces: outer wall plane, inner wall plane, or a jamb / slab edge
            on_outer = (abs(c[0] - x0) < 0.6 and n[0] < -0.7) or (abs(c[0] - x1) < 0.6 and n[0] > 0.7) or \
                       (abs(c[1] - y0) < 0.6 and n[1] < -0.7) or (abs(c[1] - y1) < 0.6 and n[1] > 0.7)
            if on_outer:
                k = self._storey_of(c[2])
                return M.get(self.ext_by_storey.get(k, 'ext'), M['ext']), uv
            if inside:
                # slab edges round stair holes and floorboard edges read as trim
                if any(zb - SLAB - 0.5 < c[2] < zb + 0.5 for zb in self.levels[1:]) or c[2] < self.z0 + 5:
                    return M.get('trim', M['ext']), uv
                return M.get('int', M['ext']), uv
            return M.get('trim', M['ext']), uv
        return f

    # ------------------------------------------------------------------ build
    def build(self, stair_tex=None, approach=112, lit=True):
        K = self.K
        self.walls(); self.floors()
        if self.roof == 'flat': self.flat_roof()
        elif self.roof in ('gable_x', 'gable_y'): self.gable_roof(self.roof[-1])
        else: self.roof_top = self.wall_top
        e = K.solid_piece(self.name, self.brushes, self.texfn(), lit=lit)
        # stairs (plain 16u flights; brushes so the AAS sees real steps)
        st_tex = stair_tex or {'top': K.T('stairtread'), 'side': K.T('stairside')}
        for k, st in enumerate(self.stairs):
            x0, y0, x1, y1, d = st
            z0 = self.levels[k] + (4 if (k == 0 and self.floor_mat) else 0)
            self.stair_brushes += K.stairs16(x0, y0, x1, y1, z0, self.levels[k + 1], d, st_tex)
            self._clear_stair(st, z0)
            self._stair_route(f'{self.name}_st{k + 1}', st, z0, self.levels[k + 1])
        if self.roof == 'flat' and self.roof_stairs:
            x0, y0, x1, y1, d = self.roof_stairs
            k = len(self.storeys) - 1
            z0 = self.levels[k] + (4 if (k == 0 and self.floor_mat) else 0)
            self.stair_brushes += K.stairs16(x0, y0, x1, y1, z0, self.roof_top, d, st_tex)
            self._clear_stair(self.roof_stairs, z0)
            self._stair_route(f'{self.name}_roof', self.roof_stairs, z0, self.roof_top, roof=True)
        # door approaches + routes in through every door
        x0, y0, x1, y1 = self.rect
        for (s, a, b) in self.doors:
            m = (a + b) / 2
            if s == 's': o, i = (m, y0 - 96, self.z0), (m, y0 + 96, self.z0 + 4); K.keep_clear(a - 24, y0 - approach, b + 24, y0, self.z0)
            elif s == 'n': o, i = (m, y1 + 96, self.z0), (m, y1 - 96, self.z0 + 4); K.keep_clear(a - 24, y1, b + 24, y1 + approach, self.z0)
            elif s == 'w': o, i = (x0 - 96, m, self.z0), (x0 + 96, m, self.z0 + 4); K.keep_clear(x0 - approach, a - 24, x0, b + 24, self.z0)
            else: o, i = (x1 + 96, m, self.z0), (x1 - 96, m, self.z0 + 4); K.keep_clear(x1, a - 24, x1 + approach, b + 24, self.z0)
            K.route(f'{self.name}_door_{s}{int(m)}', o, i)
        return e

    def _stair_route(self, name, st, z0, z1, roof=False):
        """aas route from the floor in front of the first step to the floor past the top, both points clamped 24u
        inside the walls (or the roof edge) so they never start inside a wall"""
        x0, y0, x1, y1, d = st
        ix0, iy0, ix1, iy1, _ = self.interior(0)
        bx0, by0, bx1, by1 = self.rect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dv = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[d]
        L = (y1 - y0) if d in 'ns' else (x1 - x0)
        a = [cx - dv[0] * (L / 2 + 40), cy - dv[1] * (L / 2 + 40)]
        b = [cx + dv[0] * (L / 2 + 40), cy + dv[1] * (L / 2 + 40)]
        cl = lambda v, lo, hi: max(lo + 24, min(hi - 24, v))
        a = [cl(a[0], ix0, ix1), cl(a[1], iy0, iy1)]
        lim = (bx0, by0, bx1, by1) if roof else (ix0, iy0, ix1, iy1)
        b = [cl(b[0], lim[0], lim[2]), cl(b[1], lim[1], lim[3])]
        self.K.route(name, (a[0], a[1], z0), (b[0], b[1], z1))

    def _clear_stair(self, st, z0):
        x0, y0, x1, y1, d = st
        dv = {'n': (0, 1), 's': (0, -1), 'e': (1, 0), 'w': (-1, 0)}[d]
        # keep the foot (behind the first step) clear
        if d == 'n': self.K.keep_clear(x0, y0 - 64, x1, y0, z0)
        elif d == 's': self.K.keep_clear(x0, y1, x1, y1 + 64, z0)
        elif d == 'e': self.K.keep_clear(x0 - 64, y0, x0, y1, z0)
        else: self.K.keep_clear(x1, y0, x1 + 64, y1, z0)

    # ------------------------------------------------------------------ queries for the caller
    def interior(self, k=0):
        """(x0, y0, x1, y1, floor z) inside the walls of storey k"""
        x0, y0, x1, y1 = self.rect; t = self.t
        return (x0 + t, y0 + t, x1 - t, y1 - t, self.levels[k] + (4 if (k == 0 and self.floor_mat) else 0))

    def roof_spot(self, frac=0.5):
        """(x, y, z) of a standing spot on the roof: flat roof centre, or a point on the ridge walk"""
        x0, y0, x1, y1 = self.rect
        if self.ridge:
            axis, bc, z = self.ridge
            return ((x0 + (x1 - x0) * frac, bc, z) if axis == 'x' else (bc, y0 + (y1 - y0) * frac, z))
        return (x0 + (x1 - x0) * frac, (y0 + y1) / 2, self.roof_top)
