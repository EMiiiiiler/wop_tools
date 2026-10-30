"""Regression tests for woplib and the checkers (no compiler needed).

    python3 -m pytest -q tests            (or: tests/run.sh)

Each negative test rebuilds a bug that shipped on an earlier map and asserts the checker catches it, so a change to a
checker can't silently stop catching it again.
"""
import os, sys, json, math, subprocess, struct
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from wopmap import box, carve, stairs
from woplib import padmath, wopdata
from woplib.kit import MapKit, CAULK, CLIP, WCLIP, ORIGIN
from woplib import shaders as SH, models as ML

PY = sys.executable


def run(tool, *args):
    p = subprocess.run([PY, os.path.join(ROOT, tool)] + [str(a) for a in args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ------------------------------------------------------------------------------------------------ padmath
def test_pad_target_lands():
    o = (0.0, 0.0, 38.0); land = (800.0, 0.0, 256.0); apex = 500.0
    tx, ty = padmath.pad_target(o, land, apex)
    pts = padmath.arc(o, (tx, ty, apex), land[2])
    assert abs(pts[-1][0] - 800) < 12 and abs(pts[-1][1]) < 1e-6
    t = padmath.flight_time(o[2], apex, land[2])
    assert abs(t - (len(pts) - 1) * 0.008) < 0.03


def test_pad_plan_warns_long_flight_and_low_ceiling():
    P = padmath.plan(0, (0, 0), (2000, 0, 0), 2200, ceiling=2100)
    assert any('flight' in w for w in P['warnings']) and any('ceiling' in w for w in P['warnings'])


# ------------------------------------------------------------------------------------------------ helpers
def room(tmp, name='wop_t', water=None, extra=None):
    """sealed 2048 x 2048 room with a spawn and a weapon; extra(K) adds the thing under test"""
    K = MapKit(name, 't', 'Test', (-1024, -1024, 1024, 1024))
    w = {'top': 't/floor', 'bot': CAULK, 'side': 't/wall'}
    K.add(box((-1056, -1056, -32), (1056, 1056, 0), w, detail=False))
    K.add(box((-1056, -1056, 1024), (1056, 1056, 1056), w, detail=False))
    for mn, mx in (((-1056, -1056, 0), (-1024, 1056, 1024)), ((1024, -1056, 0), (1056, 1056, 1024)),
                   ((-1024, -1056, 0), (1024, -1024, 1024)), ((-1024, 1024, 0), (1024, 1056, 1024))):
        K.add(box(mn, mx, 't/wall', detail=False))
    K.spawn(0, 0, 0, 90, nudge=False)
    if extra: extra(K)
    out = str(tmp)
    K.write(out)
    SH.configure('t', name, 'Test')
    SH.write_shader(out, [SH.lm('floor'), SH.lm('wall'), SH.water('water'), SH.nodraw_ns()])
    SH.write_arena(out, 'ffa')
    return os.path.join(out, 'maps', name + '.map'), K


def lint(mp, *sections):
    d = os.path.dirname(os.path.dirname(mp))
    return run('lint_map.py', mp, '--shaders', d, '--only', ','.join(sections))


# ------------------------------------------------------------------------------------------------ lint: negative tests
def pool(K, steps):
    """raised pool on the room floor: rim walls to deck z 128, water 0..112 (deep), optional 16u steps inside"""
    x0, y0, x1, y1 = -400, -300, 400, 300
    for mn, mx in (((x0 - 32, y0 - 32, 0), (x0, y1 + 32, 128)), ((x1, y0 - 32, 0), (x1 + 32, y1 + 32, 128)),
                   ((x0, y0 - 32, 0), (x1, y0, 128)), ((x0, y1, 0), (x1, y1 + 32, 128))):
        K.add(box(mn, mx, 't/wall'))
    ss = K.stairs16(x0, y1 - 7 * 32, x1, y1, 0, 112, 'n', 't/floor') if steps else []
    wb = box((x0, y0, 0), (x1, y1, 112), 't/water')
    for p in carve(wb, ss):
        for f in p.faces: f.tex = 't/water' if f.n[2] > 0.9 else 't/water_nd'
        K.add(p)


def test_water_sheer_lip_fails(tmp_path):
    """moosefalls cave pool: floor 16u above the water, no steps -> players trapped (water jump band too narrow)"""
    mp, _ = room(tmp_path, extra=lambda K: pool(K, steps=False))
    rc, o = lint(mp, 'water')
    assert rc == 1 and 'no way out' in o


def test_water_with_steps_passes(tmp_path):
    mp, _ = room(tmp_path, extra=lambda K: pool(K, steps=True))
    rc, o = lint(mp, 'water')
    assert rc == 0, o


def test_rotating_origin_key_and_brush_fails(tmp_path):
    """q3map2 adds the origin key to the origin brush: the mover lands outside the map (leak)"""
    def extra(K):
        K.M.ent('func_rotating', (100, 100, 100), brushes=[box((92, 92, 92), (108, 108, 108), ORIGIN),
                                                           box((96, 96, 120), (104, 104, 128), 't/wall')], speed=30)
    mp, _ = room(tmp_path, extra=extra)
    rc, o = lint(mp, 'entities')
    assert rc == 1 and 'origin brush AND an origin key' in o


def test_kit_refuses_origin_key_on_rotating(tmp_path):
    K = MapKit('wop_t', 't', 'T', (-100, -100, 100, 100))
    with pytest.raises(ValueError):
        K.ent('func_rotating', (0, 0, 0), brushes=[box((-8, -8, -8), (8, 8, 8), ORIGIN)])


def test_berserker_refused():
    K = MapKit('wop_t', 't', 'T', (-100, -100, 100, 100))
    with pytest.raises(ValueError):
        K.item('item_berserker', 0, 0, 0)


def test_item_on_playerclip_floor_fails(tmp_path):
    """padbbq pergola: items drop with MASK_SOLID and fall through common/clip"""
    def extra(K):
        K.add(box((300, 300, 0), (500, 500, 200), CLIP))
        K.item('item_armor_shard', 400, 400, 200)
    mp, _ = room(tmp_path, extra=extra)
    rc, o = lint(mp, 'items')
    assert rc == 1 and 'falls through' in o


def test_item_on_weapclip_floor_ok(tmp_path):
    def extra(K):
        K.add(box((300, 300, 0), (500, 500, 200), WCLIP))
        K.item('item_armor_shard', 400, 400, 200)
    mp, _ = room(tmp_path, extra=extra)
    rc, o = lint(mp, 'items')
    assert rc == 0, o


def test_playerclip_name_fails(tmp_path):
    """padshroom: common/playerclip does not exist in WoP and rendered as a missing-texture grid"""
    mp, _ = room(tmp_path, extra=lambda K: K.add(box((0, 300, 0), (64, 364, 64), 'common/playerclip')))
    rc, o = lint(mp, 'names')
    assert rc == 1 and 'does not exist in WoP' in o


def test_visible_caulk_warns(tmp_path):
    """padcandy play-test: lobby side of a wall was caulk -> see-through"""
    mp, _ = room(tmp_path, extra=lambda K: K.add(box((200, -400, 0), (232, 400, 300), {'side': CAULK, 'top': 't/wall', 'w': 't/wall'})))
    rc, o = lint(mp, 'caulk')
    assert 'caulk visible' in o


def test_stair_headroom_fails(tmp_path):
    """waterpark grotto: the step before a ceiling edge had < 56u clearance"""
    def extra(K):
        K.stairs16(-600, -100, -472, 412, 0, 256, 'n', 't/floor')
        K.add(box((-600, 300, 300), (-472, 600, 332), 't/wall'))       # slab over the top steps: ~48u clearance
    mp, _ = room(tmp_path, extra=extra)
    rc, o = lint(mp, 'headroom')
    assert rc == 1 and 'ON A STAIR' in o


def test_long_pad_flight_fails(tmp_path):
    def extra(K):
        K.add(box((700, 700, 0), (900, 900, 64), 't/wall'))
        K.jumppad(-800, -800, 0, land=(800, 800, 64), apex=1000, name='far')
    mp, K = room(tmp_path, extra=extra)
    assert any('flight' in n for n in K.notes)


def test_arena_needs_lollies(tmp_path):
    SH.configure('t', 'wop_t', 'T')
    with pytest.raises(ValueError):
        SH.write_arena(str(tmp_path), 'ffa ctl', ents={'info_player_deathmatch'})
    with pytest.raises(ValueError):
        SH.write_arena(str(tmp_path), 'ffa deathmatch')


# ------------------------------------------------------------------------------------------------ models + package
def test_model_registry_catches_missing_image(tmp_path):
    ML.configure('t', str(tmp_path))
    ML.S('never_written', 'lm')
    ML.T('leaf', ML.fill(32, (40, 120, 40)))
    ML.S('leaf', 'alpha')                                  # alpha kind on an image without alpha: renders opaque
    probs = ML.check_registry()
    assert any('never written' in p for p in probs) and any('needs an alpha' in p for p in probs)


def test_pk3_check_finds_unregistered_model_shader(tmp_path):
    """padcandy railings: an MD3 surface shader registered after the .shader file was written -> no shader"""
    from meshlib import Mesh, rbox
    out = str(tmp_path)
    ML.configure('t', out)
    ML.T('wood', ML.fill(32, (120, 80, 40)))
    X = ML.Model(); rbox(X.mesh(ML.S('wood', 'lm')), (0, 0, 0), (32, 32, 32), r=2, k=1)
    ML.save('cube', X)
    late = ML.S('wood', 'lm', tag='late')                   # registered after the shader is written
    Y = ML.Model(); rbox(Y.mesh(late), (0, 0, 0), (32, 32, 32), r=2, k=1)
    ML.REG.pop(late)
    ML.save('cube2', Y)

    def extra(K):
        K.custom(ML.PLACE['cube'], 300, 300, 0)
        K.custom(ML.PLACE['cube2'], -300, 300, 0)
    mp, _ = room(tmp_path, extra=extra)
    sh = open(os.path.join(out, 'scripts', 't.shader')).read() + ML.model_shaders()
    open(os.path.join(out, 'scripts', 't.shader'), 'w').write(sh)
    for ext in ('.bsp', '.aas'): open(os.path.join(out, 'maps', 'wop_t' + ext), 'wb').write(b'x')
    rc, o = run('pk3_check.py', out, '--map', 'wop_t')
    assert rc == 1 and 'cube2.md3: surface shader' in o and 'cube.md3: surface' not in o


# ------------------------------------------------------------------------------------------------ the sample map passes the static checks
def test_sample_generator_passes_static_checks(tmp_path):
    out = str(tmp_path)
    p = subprocess.run([PY, '-W', 'error::RuntimeWarning', os.path.join(ROOT, 'templates', 'sample', 'build.py')],
                       env=dict(os.environ, OUT=out), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    mp = os.path.join(out, 'maps', 'wop_padsample.map')
    rc, o = run('audit_map.py', mp, '--shaders', out)
    assert 'RESULT: OK' in o, o[-2000:]
    rc, o = run('pad_check.py', mp, '--shaders', out)
    assert rc == 0, o
    rc, o = run('lint_map.py', mp, '--shaders', out, '--md3root', out)
    assert rc == 0, o[-3000:]
    spots = json.load(open(os.path.join(out, 'maps', 'wop_padsample.spots.json')))
    assert len(spots['pads']) == 2 and spots['secrets'] and len(spots['routes']) >= 4


def test_unknown_pickup_fails(tmp_path):
    """padcandy/padhalloween placed item_floater (the Floater is holdable_floater): it never spawned"""
    mp, _ = room(tmp_path, extra=lambda K: K.M.ent('item_floater', (300, 300, 16)))
    rc, o = lint(mp, 'entities')
    assert rc == 1 and 'not a WoP pickup' in o


def test_nodraw_collision_warns(tmp_path):
    """padattic: the ridable train's collision boxes were common/nodraw, which is NONSOLID in WoP"""
    def extra(K):
        K.M.ent('func_rotating', brushes=[box((-8, -8, 92), (8, 8, 108), ORIGIN), box((200, -40, 0), (400, 40, 80), 'common/nodraw')], speed=9)
    mp, _ = room(tmp_path, extra=extra)
    rc, o = lint(mp, 'names')
    assert 'NONSOLID in WoP' in o


# ------------------------------------------------------------------------------------------------ kit helpers added for padfridge
def test_ramp_too_steep_refused():
    """MIN_WALK_NORMAL 0.7 (45.6 deg): a steeper 'ramp' is a wall to players and bots"""
    K = MapKit('wop_t', 't', 'T', (-1000, -1000, 1000, 1000))
    with pytest.raises(ValueError):
        K.ramp(0, 0, 200, 128, 0, 300, 'e', 't/floor')


def test_ramp_adds_route_and_spot():
    K = MapKit('wop_t', 't', 'T', (-1000, -1000, 1000, 1000))
    b = K.ramp(0, 0, 800, 224, 0, 400, 'e', 't/floor', route='r1')
    mn, mx = b.bounds()
    assert mx[2] == 400 and mn[2] == 0
    (name, a, z), = K.routes
    assert name == 'r1' and a[0] < 0 and z[0] > 800 and a[2] == 0 and z[2] == 400
    assert K.spots['ramps'][0]['deg'] < 30


def test_botclip_rect_leaves_gaps():
    K = MapKit('wop_t', 't', 'T', (-1000, -1000, 1000, 1000))
    strips = K.botclip_rect(-500, -300, 500, 300, 128, sides='s', gaps=[('s', -100, 100)])
    xs = sorted((round(s.bounds()[0][0]), round(s.bounds()[1][0])) for s in strips)
    assert xs == [(-500, -100), (100, 500)]
    y0, y1 = strips[0].bounds()[0][1], strips[0].bounds()[1][1]
    assert y0 >= -300 and y1 <= -300 + 24                   # inset onto the deck, not hanging past its edge
    assert all(t == 'common/botclip' for s in strips for t in s.textures())


def test_water_box_draws_only_the_top(tmp_path):
    """a puddle on a flat floor: carved by a block standing in it, only the top faces visible, and lint's water check
    passes (you can walk out of 24u-deep water)"""
    def extra(K):
        blk = box((-64, -64, 0), (64, 64, 96), 't/wall')
        K.add(blk)
        pieces = K.water_box((-300, -300, 0), (300, 300, 24), 't/water', cutters=[blk])
        assert len(pieces) > 1
        for p in pieces:
            for f in p.faces:
                assert (f.tex == 't/water') == (f.n[2] > 0.9 and abs(f.d - 24) < 0.5)
    mp, K = room(tmp_path, extra=extra)
    assert K.spots['water'][0]['depth'] == 24
    rc, o = lint(mp, 'water')
    assert rc == 0, o


def test_solid_piece_writes_md3_and_matching_collision(tmp_path):
    """solids used twice: visible MD3 (hidden faces culled) + the same brushes as weapclip"""
    import md3tool
    out = str(tmp_path)
    ML.configure('t', out)
    ML.T('cheese', ML.fill(32, (240, 200, 80)))
    sh = ML.S('cheese', 'lm')
    K = MapKit('wop_t', 't', 'T', (-1000, -1000, 1000, 1000))
    a = box((100, 100, 0), (300, 200, 64), 't/x'); b = box((100, 200, 0), (300, 300, 64), 't/x')
    e = K.solid_piece('slab', [a, b], lambda c, n, poly: (sh, ML.planar_uv(n)))
    assert e['origin'].split() == ['200', '200', '0']
    clips = [w for w in K.M.world if w.textures() == {'common/weapclip'}]
    assert len(clips) == 2
    m = md3tool.load(os.path.join(out, 'models', 't', 'slab.md3'))
    V = np.concatenate([np.asarray(sf['verts']) for sf in m['surfaces']])
    assert V[:, 0].min() >= -100.5 and V[:, 0].max() <= 100.5 and V[:, 2].min() >= -0.5   # stored centred, base at 0
    ntri = sum(len(sf['tris']) for sf in m['surfaces'])
    assert ntri == 20, ntri                                 # 12 faces - 2 hidden shared faces = 10 quads
    assert not K.free(200, 200, 10, 0, 64)                  # collision reserved the footprint


def test_slick_and_shadowless_glass_shaders():
    SH.configure('t', 'wop_t', 'T')
    s = SH.slick('ice')
    assert 'surfaceparm slick' in s and '$lightmap' in s and s.startswith('textures/t/ice\n')
    assert 'alphashadow' in SH.glass('g1') and 'alphashadow' not in SH.glass('g2', shadow=False)


# ------------------------------------------------------------------------------------------------ walk-through page (needs the compiler)
@pytest.mark.skipif(not os.environ.get('Q3MAP2') or not os.path.exists(os.environ.get('Q3MAP2', '')),
                    reason='needs Q3MAP2 (source setup_cloud.sh env.sh)')
def test_walkthrough_page_renders(tmp_path):
    """bsp2scene turns the compiled sample map into one self-contained page (geometry, lightmaps, item markers)"""
    out = str(tmp_path)
    p = subprocess.run([PY, os.path.join(ROOT, 'templates', 'sample', 'build.py')], env=dict(os.environ, OUT=out),
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    mp = os.path.join(out, 'maps', 'wop_padsample.map')
    q = os.environ['Q3MAP2']
    game = os.environ.get('GAME', '')
    base = [q, '-game', 'quake3'] + (['-fs_basepath', game + '/', '-fs_game', 'wop'] if game else [])
    for args in (['-meta'], ['-vis'], ['-light', '-fast', '-samples', '1']):
        r = subprocess.run(base + args + [mp], capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stdout[-2000:]
    page = os.path.join(out, 'preview.html')
    rc, o = run('preview/bsp2scene.py', os.path.join(out, 'maps', 'wop_padsample.bsp'), page, '--vfs', out, '--compact')
    assert rc == 0, o[-2000:]
    html = open(page, encoding='utf-8', errors='replace').read()
    assert os.path.getsize(page) > 50_000 and 'three' in html.lower()


def test_sightlines_skips_eye_points_inside_solids(tmp_path):
    """padfridge: grid points on the back wall face / inside a tall block found a 'floor' at zmax and cast long bogus
    rays; such points must not count as eye points"""
    def extra(K):
        K.add(box((-1024, 0, 0), (1024, 1024, 1000), 't/wall'))      # the north half is one tall solid block
    mp, _ = room(tmp_path, extra=extra)
    rc, o = run('sightlines.py', mp, os.path.join(str(tmp_path), 's.png'), '--bounds=-1024,-1024,1024,1024', '--zmax', '512')
    n = int(o.split('eye points ')[1].split(',')[0])
    assert n == 128, o[-800:]                                      # 16 x 8 grid on the open south half only


def test_sky_window_is_sealed_and_lint_clean(tmp_path):
    """padfridge window over the sink: a hole through the structural wall with a sealed sky box behind it; the wall
    pieces, sky box and pane never overlap (audit) and the room still has no leak path in the brush set"""
    def extra(K):
        # replace the north wall of the test room with a windowed one
        K.M.world[:] = [b for b in K.M.world if not (b.bounds()[0][1] >= 1023 and b.bounds()[1][2] >= 1000)]
        out = K.sky_window((-1024, 1024, 0), (1024, 1056, 1024), (-300, 300, 300, 700), 't/wall', 't/sky',
                           glass_tex='t/glass', face='s')
        sky = [b for b in out if 't/sky' in b.textures()]
        assert len(sky) == 5 and all(not b.detail for b in sky)
        panes = [b for b in out if 't/glass' in b.textures()]
        (mn, mx), = [p.bounds() for p in panes]
        assert mn[0] == -300 and mx[0] == 300 and 1024 < mn[1] < mx[1] < 1056
    mp, K = room(tmp_path, extra=extra)
    rc, o = run('audit_map.py', mp, '--shaders', str(tmp_path))
    assert '[overlaps] 0 brush pairs intersect' in o, o[-1500:]


def test_secret_entry_is_reserved():
    """padfridge root cellar: props were nudged onto the secret's trigger; the entry (and its sound trigger) must be
    occupied so nothing is scattered there"""
    K = MapKit('wop_t', 't', 'T', (-1000, -1000, 1000, 1000))
    K.secret((0, 0, 0), (150, 160, 100), dest=(500, 500, 0), angle=0, name='s', approach='e')
    assert not K.free(100, 80, 10, 0, 50) and not K.free(170, 80, 10, 0, 50)        # entry and sound slab
    assert K.free(-200, 80, 10, 0, 50)
