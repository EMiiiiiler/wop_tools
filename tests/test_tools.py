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
