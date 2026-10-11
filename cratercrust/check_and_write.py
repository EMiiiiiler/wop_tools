#!/usr/bin/env python3
"""Runs the layout, validates it, and writes maps/wop_cratercrust.map.

Checks:
  * no two solid/clip/liquid brushes interpenetrate (touching is fine)
  * every misc_model rests on a top surface across its whole footprint and doesn't cut into brushes
  * items / spawns are not in solid and have a floor under them
  * every jump pad trajectory clears geometry and lands on a surface
  * 3-6 ammo spots per weapon
"""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
import sys, json, math, collections
sys.path.insert(0, _HERE)
exec(open(_os.path.join(_HERE, 'build_map.py')).read())

OUT = sys.argv[1] if len(sys.argv) > 1 else _os.path.join(_os.environ.get('OUT', 'out'), 'maps/wop_cratercrust.map')
B = json.load(open(_os.path.join(_os.path.dirname(_HERE), 'md3bounds.json')))
problems = []

solids = [b for b in world if b.kind in ('solid', 'clip', 'water')]
hard = [b for b in world if b.kind in ('solid', 'clip')]

# ---------------------------------------------------------------- brush overlaps
for i in range(len(solids)):
    a = solids[i]
    for j in range(i + 1, len(solids)):
        b = solids[j]
        if overlap(a, b):
            problems.append('OVERLAP %s <-> %s' % (a.tag, b.tag))


# ---------------------------------------------------------------- helpers
def top_support(x, y, z, tol=0.6):
    """Is there a brush whose top face at height z covers point (x,y)?"""
    for b in hard:
        if abs(b.maxs[2] - z) > tol: continue
        if b.mins[0] - 0.01 <= x <= b.maxs[0] + 0.01 and b.mins[1] - 0.01 <= y <= b.maxs[1] + 0.01:
            # make sure the top at this point really is at z (box brushes) — slopes not used for model support
            if b.is_box(): return True
    return False


def solid_hits(mins, maxs, pool, skip=()):
    out = []
    for b in pool:
        if b.tag in skip: continue
        if aabb_brush_overlap(mins, maxs, b): out.append(b.tag)
    return out


def rot_bounds(mn, mx, ang, s):
    a = math.radians(ang)
    ca, sa = round(math.cos(a), 6), round(math.sin(a), 6)
    xs, ys = [], []
    for x in (mn[0], mx[0]):
        for y in (mn[1], mx[1]):
            xs.append((x * ca - y * sa) * s); ys.append((x * sa + y * ca) * s)
    return (min(xs), min(ys), mn[2] * s), (max(xs), max(ys), mx[2] * s)


# ---------------------------------------------------------------- models
clip_brushes = []
model_ents = []
for m in models:
    key = m['path']
    if key not in B:
        problems.append('MODEL missing bounds ' + key); continue
    mn, mx = B[key]['min'], B[key]['max']
    rmn, rmx = rot_bounds(mn, mx, m['angle'], m['scale'])
    ox, oy, oz = m['origin']
    # put the lowest vertex exactly on the surface
    oz_adj = oz - rmn[2]
    wmn = (ox + rmn[0], oy + rmn[1], oz)
    wmx = (ox + rmx[0], oy + rmx[1], oz + (rmx[2] - rmn[2]))
    # support: sample the footprint
    bad = 0
    if m['clip'] == 'trunk':
        wmn_s, wmx_s = (ox - 40, oy - 40), (ox + 40, oy + 40)
    else:
        wmn_s, wmx_s = wmn[:2], wmx[:2]
    for fx in (0.02, 0.25, 0.5, 0.75, 0.98):
        for fy in (0.02, 0.25, 0.5, 0.75, 0.98):
            px = wmn_s[0] + (wmx_s[0] - wmn_s[0]) * fx; py = wmn_s[1] + (wmx_s[1] - wmn_s[1]) * fy
            if not top_support(px, py, oz): bad += 1
    if bad:
        problems.append('MODEL %s at %s: %d/25 footprint samples unsupported (fp %s..%s)' % (key.split('/')[-1], m['origin'], bad, [round(v) for v in wmn[:2]], [round(v) for v in wmx[:2]]))
    lift = 0.5
    if m['clip'] == 'trunk':
        wmn, wmx = (ox - 40, oy - 40, oz), (ox + 40, oy + 40, wmx[2])
    hits = solid_hits((wmn[0], wmn[1], wmn[2] + lift), (wmx[0], wmx[1], wmx[2]), hard)
    if hits:
        problems.append('MODEL %s at %s intersects %s' % (key.split('/')[-1], m['origin'], hits[:4]))
    e = Entity('misc_model', model=key, origin=(round(ox, 2), round(oy, 2), round(oz_adj, 2)))
    if m['angle']: e.kv['angle'] = m['angle']
    if m['scale'] != 1.0: e.kv['modelscale'] = m['scale']
    e.kv['spawnflags'] = '0'
    model_ents.append(e)
    m['world_bounds'] = (wmn, wmx)
    if m['clip'] == 'trunk':   # trees: only the trunk counts for overlaps, canopy is overhead
        m['world_bounds'] = ((ox - 40, oy - 40, oz), (ox + 40, oy + 40, oz + 0.55 * (wmx[2] - wmn[2])))
    if m['clip']:
        if m['clip'] == 'trunk':
            w = 40
            cb = box(round(ox) - w, round(oy) - w, oz, round(ox) + w, round(oy) + w, round(oz + 0.55 * (wmx[2] - wmn[2])), CLIP, kind='clip', tag='mclip_' + key.split('/')[-1])
        else:
            cb = box(math.floor(wmn[0]), math.floor(wmn[1]), oz, math.ceil(wmx[0]), math.ceil(wmx[1]), math.ceil(wmx[2]), CLIP, kind='clip', tag='mclip_' + key.split('/')[-1] + '_%d_%d' % (ox, oy))
        for b in solids:
            if overlap(cb, b): problems.append('CLIP for %s overlaps %s' % (key, b.tag))
        clip_brushes.append(cb)
# models must not interpenetrate each other either
for i in range(len(models)):
    for j in range(i + 1, len(models)):
        a, b = models[i].get('world_bounds'), models[j].get('world_bounds')
        if not a or not b: continue
        if all(a[0][k] < b[1][k] - 0.5 and b[0][k] < a[1][k] - 0.5 for k in range(3)):
            problems.append('MODELS overlap %s@%s and %s@%s' % (models[i]['path'].split('/')[-1], models[i]['origin'], models[j]['path'].split('/')[-1], models[j]['origin']))
world.extend(clip_brushes)
hard_all = hard + clip_brushes


# ---------------------------------------------------------------- items / spawns
def floor_under(x, y, z, maxdrop=40):
    best = None
    for b in hard_all + [w for w in world if w.kind == 'solid']:
        if b.mins[0] <= x <= b.maxs[0] and b.mins[1] <= y <= b.maxs[1] and b.maxs[2] <= z + 0.1:
            if b.is_box():
                if best is None or b.maxs[2] > best: best = b.maxs[2]
            else:
                # sloped: find top height at x,y
                for p in b.planes:
                    if p.n[2] > 0.3:
                        h = (p.d - p.n[0] * x - p.n[1] * y) / p.n[2]
                        if h <= z + 0.1 and (best is None or h > best): best = h
    return best


def check_point_ent(name, o, mins, maxs, need_floor=True):
    bmn = (o[0] + mins[0], o[1] + mins[1], o[2] + mins[2]); bmx = (o[0] + maxs[0], o[1] + maxs[1], o[2] + maxs[2])
    hits = solid_hits(bmn, bmx, hard_all)
    if hits: problems.append('%s at %s in solid: %s' % (name, o, hits[:3]))
    for mm in models:
        wb = mm.get('world_bounds')
        if wb and all(bmn[k] < wb[1][k] - 1 and wb[0][k] < bmx[k] - 1 for k in range(3)):
            problems.append('%s at %s overlaps model %s' % (name, o, mm['path'].split('/')[-1]))
    if need_floor:
        f = floor_under(o[0], o[1], o[2] + mins[2])
        if f is None or (o[2] + mins[2]) - f > 30:
            problems.append('%s at %s floating (floor %s)' % (name, o, f))


for it in items:
    check_point_ent(it['cls'], it['origin'], (-15, -15, -15), (15, 15, 15))
for sp in spawns:
    check_point_ent(sp['cls'], sp['origin'], (-15, -15, -24), (15, 15, 32))
for e in ents:
    if e.kv['classname'] == 'station_health':
        o = e.kv['origin']; check_point_ent('station_health', (o[0], o[1], o[2] + 1), (-40, -40, 0), (40, 40, 64))
    if e.kv['classname'].startswith('team_CTL'):
        check_point_ent(e.kv['classname'], e.kv['origin'], (-15, -15, -15), (15, 15, 15))

# ---------------------------------------------------------------- jump pad simulation
G = 800.0
pad_report = []
for p in pads:
    t = p['trig']
    org = ((t.mins[0] + t.maxs[0]) / 2, (t.mins[1] + t.maxs[1]) / 2, (t.mins[2] + t.maxs[2]) / 2)
    tgt = p['target']
    height = tgt[2] - org[2]
    tm = math.sqrt(height / (0.5 * G))
    dx, dy = tgt[0] - org[0], tgt[1] - org[1]
    dist = math.hypot(dx, dy)
    vx, vy, vz = dx / tm, dy / tm, tm * G
    # player stands on the pad: origin = pad top + 24
    pos = [org[0], org[1], t.mins[2] + 24.0]
    dt = 1 / 250.0
    landed, hit = None, None
    margin = 99
    for step in range(int(6 / dt)):
        nvz = vz - G * dt
        npos = [pos[0] + vx * dt, pos[1] + vy * dt, pos[2] + (vz + nvz) / 2 * dt]
        bmn = (npos[0] - 15, npos[1] - 15, npos[2] - 24); bmx = (npos[0] + 15, npos[1] + 15, npos[2] + 32)
        hits = [b for b in hard_all if aabb_brush_overlap(bmn, bmx, b, tol=0.01)]
        if hits:
            if nvz < 0 and pos[2] - 24 >= max(b.maxs[2] for b in hits) - 0.5:
                landed = (round(pos[0]), round(pos[1]), round(pos[2] - 24), hits[0].tag)
            else:
                hit = (round(npos[0]), round(npos[1]), round(npos[2]), [b.tag for b in hits][:3])
            break
        if step % 3 == 0 and nvz > -200:   # clearance while rising / near apex
            for mgn in (12, 6, 3):
                e1 = (npos[0] - 15 - mgn, npos[1] - 15 - mgn, npos[2] - 24 - mgn); e2 = (npos[0] + 15 + mgn, npos[1] + 15 + mgn, npos[2] + 32 + mgn)
                near = [b for b in hard_all if aabb_brush_overlap(e1, e2, b, tol=0.01) and b.tag not in ('pad_' + p['name'],)]
                if near and npos[2] - 24 > t.mins[2] + 20:
                    margin = min(margin, mgn)
        pos, vz = npos, nvz
    info = '%-12s speed %4d  apex %s  ' % (p['name'], math.hypot(math.hypot(vx, vy), vz), tgt)
    if landed:
        info += 'lands %s (wanted %s) clearance<=%s' % (landed, p['land'][:2], margin)
        if math.hypot(landed[0] - p['land'][0], landed[1] - p['land'][1]) > 40 or abs(landed[2] - p['land'][2]) > 3:
            problems.append('PAD %s lands at %s, wanted %s' % (p['name'], landed, p['land']))
    else:
        info += 'HIT %s' % (hit,); problems.append('PAD %s collides %s' % (p['name'], hit))
    pad_report.append(info)

# ---------------------------------------------------------------- ammo counts
cnt = collections.Counter(it['cls'] for it in items)
for wpn in ('nipper', 'balloony', 'betty', 'boaster', 'bubbleg', 'pumper', 'splasher', 'imperius'):
    n = cnt['ammo_' + wpn]
    if not (3 <= n <= 6): problems.append('ammo_%s count %d' % (wpn, n))

# ---------------------------------------------------------------- write
import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f:
    f.write('// Crater Crust - World of Padman map (generated)\n')
    wsp = Entity('worldspawn', message='Crater Crust', _ambient='10', _color='0.85 0.85 1',
                 gridsize='128 128 192', _blocksize='0 0 0', _keepLights='1')
    wsp.brushes = world
    wsp.write(f)
    for e in ents + model_ents:
        e.write(f)
    for it in items:
        e = Entity(it['cls'], origin=it['origin'])
        for k, v in it['kv'].items(): e.kv[k] = v
        e.write(f)
    for sp in spawns:
        Entity(sp['cls'], origin=sp['origin'], angle=sp['angle']).write(f)
    for l in lights:
        Entity('light', origin=l['origin'], light=l['light'], _color=l['color']).write(f)

print('brushes: %d world (%d structural), %d entities, %d models, %d items, %d spawns, %d lights' % (
    len(world), sum(1 for b in world if not b.detail), len(ents), len(models), len(items), len(spawns), len(lights)))
print('\n'.join(pad_report))
print('ammo:', {k: v for k, v in sorted(cnt.items()) if k.startswith('ammo')})
print('PROBLEMS (%d):' % len(problems))
print('\n'.join(problems))
